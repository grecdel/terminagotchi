"""L'équipe : les bestioles dressées grandissent (enfant → ado → adulte → forme finale) en gardant
leur nom, et s'animent dans le terminal.

La bestiole « active » (tg troupe <nom>) gagne de l'expérience à chaque commande que tu tapes.
Toutes les espèces jouent les 13 animations (moteur anim_auto, à leur stade, dans leur variante,
avec leur teinte shiny) ; Abyssor garde ses animations faites main (dossier anim/).
"""
import base64
import colorsys
import json
import pkgutil
import sys
import time
import zlib

from . import anim_auto
from . import bestiaire as B
from . import core
from .langue import largeur, t
from .plateforme import BOLD, DIM, RESET, fg

STADES = ["bebe", "enfant", "ado", "adulte", "ancien"]

SEUILS = {"bebe": 100, "enfant": 250, "ado": 600, "adulte": 1500}  # XP pour passer au stade suivant
# Abyssor (animations détaillées faites à la main) garde ses noms de stades d'origine
STADES_ABYSSOR = {"bebe": "enfant", "enfant": "enfant", "ado": "ado", "adulte": "adulte", "ancien": "finale"}
ANIMS = anim_auto.ANIMS
_CACHE = {}


# ---------------------------------------------------------------- données d'animation
def donnees(espece):
    cle = B._simple(espece)
    if cle not in _CACHE:
        try:
            _CACHE[cle] = json.loads(pkgutil.get_data(__package__, f"anim/{cle}.json").decode("utf-8"))
        except (OSError, FileNotFoundError, TypeError, ValueError):
            _CACHE[cle] = None
    return _CACHE[cle]


def anime(espece):
    return donnees(espece) is not None


def _rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _palette(pal, teinte):
    out = [None]
    for h in pal:
        r, g, b = _rgb(h)
        if teinte:
            hh, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            r, g, b = (int(v * 255) for v in colorsys.hls_to_rgb((hh + teinte) % 1, l, s))
        out.append((r, g, b))
    return out


def image_terminal(octets, pal, n):
    """Une image (indices de palette) → lignes de demi-blocs colorés (2 pixels par caractère)."""
    out = []
    for y in range(0, n, 2):
        s = ""
        for x in range(n):
            a = pal[octets[y * n + x]]
            b = pal[octets[(y + 1) * n + x]] if y + 1 < n else None
            if a is None and b is None:
                s += " "
            elif b is None:
                s += "\033[38;2;%d;%d;%dm▀\033[0m" % a
            elif a is None:
                s += "\033[38;2;%d;%d;%dm▄\033[0m" % b
            else:
                s += "\033[38;2;%d;%d;%d;48;2;%d;%d;%dm▀\033[0m" % (a + b)
        out.append(s)
    return out


def images(espece, stade, nom, teinte=0.0):
    d = donnees(espece)
    if not d:
        return None
    a = d["anims"].get(STADES_ABYSSOR.get(stade, stade), {}).get(nom) or d["anims"].get(stade, {}).get(nom)
    if not a:
        return None
    pal = _palette(a["palette"], teinte)
    n = d["taille"]
    brut = [base64.b64decode(x) for x in a["images"]]
    if d.get("format") == "zlib":
        brut = [zlib.decompress(x) for x in brut]
    return [image_terminal(x, pal, n) for x in brut], d["ips"]


# ---------------------------------------------------------------- l'équipe
def stade(ind):
    s = ind.get("stade", "bebe")
    return "ancien" if s == "finale" else s


def active(state):
    caps = state.get("captures", [])
    if not caps:
        return None
    i = state.get("active")
    return next((c for c in caps if c.get("id") == i), caps[-1])


def gagner(state, ind, xp):
    """Ajoute de l'expérience à une bestiole ; renvoie le nouveau stade si elle évolue."""
    ind["xp"] = ind.get("xp", 0) + xp
    s = stade(ind)
    if s in SEUILS and ind["xp"] >= SEUILS[s]:
        ind["stade"] = STADES[STADES.index(s) + 1]
        ind["xp"] = 0
        ind["evolue"] = time.time()
        core.log(state, t("eq.evolue.log", nom=ind["espece"], stade=B.nom_stade(ind["stade"])))
        core.notif(state, t("eq.evolue.notif", nom=ind["espece"], stade=B.nom_stade(ind["stade"]), nom_min=ind["espece"].lower()))
        core.say(state, t("eq.evolue.dit", nom=ind["espece"], stade=B.nom_stade(ind["stade"]), nom_min=ind["espece"].lower()), 14)
        return ind["stade"]
    return None


def tick(state, lignes):
    """Chaque commande tapée à la main fait grandir la bestiole active."""
    ind = active(state)
    if not ind:
        return
    tapees = [l for l in lignes if not core.est_colle(l)]
    if tapees:
        gagner(state, ind, 2 * len(tapees))


def ecran_equipe(state):
    caps = state.get("captures", [])
    if not caps:
        return [" " + t("eq.vide")]
    act = active(state)
    lignes = [f" {fg(213)}── 🐾 " + t("eq.titre", nom=state["name"]) + f" ──{RESET}", ""]
    for c in caps[-12:][::-1]:
        e = B.espece(c["espece"])
        if not e:
            continue
        s = stade(c)
        seuil = SEUILS.get(s)
        barre = f"{c.get('xp', 0)}/{seuil} XP" if seuil else t("eq.stade_max")
        mot = t("eq.active")
        lm = largeur(mot) + 3
        marque = f"{fg(226)}★ {mot}{RESET} " if c is act else " " * lm
        var = c.get("variante", "classique")
        dort = c.get("repos", 0) > time.time()            # KO au combat : elle se repose (voir combat.py)
        repos = f" {fg(117)}" + t("eq.repos", min=max(1, round((c["repos"] - time.time()) / 60))) + RESET if dort else ""
        lignes.append(f" {marque}{B.nom_affiche(e, c.get('shiny'), B.rarete_de(c))} {DIM}· {B.nom_stade(s)}"
                      f"{' · ' + var if var != 'classique' else ''} · {B.nom_rarete(B.rarete_de(c))} · {barre}{RESET}{repos}")
    lignes += ["", f" {DIM}" + t("eq.pied") + RESET]
    return lignes


def choisir(state, nom):
    e = B.espece(nom)
    caps = [c for c in state.get("captures", []) if e and c["espece"] == e["nom"]]
    if not caps:
        return " " + t("eq.pas_dans_troupe", nom=nom)
    state["active"] = caps[-1]["id"]
    return " " + t("eq.choisie", nom=caps[-1]["espece"])


# ---------------------------------------------------------------- tg anime
def animation(ind, quoi, aura=False):
    """(images, ips) d'une bestiole de la troupe : à son stade, dans sa variante, avec sa teinte shiny.
    Abyssor garde ses animations faites main ; toutes les autres espèces passent par anim_auto.
    aura=True : son aura de rareté respire autour d'elle (aura.py)."""
    s = stade(ind)
    if anime(ind["espece"]):
        avant = s
        if quoi == "evolution":              # le fichier fait main range l'évolution au stade de départ
            i = STADES.index(s)
            avant = STADES[i - 1] if i else s
        r = images(ind["espece"], avant, quoi, ind.get("teinte", 0.5) if ind.get("shiny") else 0.0)
        if r:
            return r
    e = B.espece(ind["espece"])
    if not e:
        return None
    teinte = ind.get("teinte", 0.5) if ind.get("shiny") else None
    from . import aura as A
    return anim_auto.lignes(e, s, ind.get("variante", "classique"), quoi, teinte, A.palier_ind(ind) if aura else None)


def derouler(frames, ips, tours, titre=None):
    """Joue les images sur place (le curseur remonte à chaque image)."""
    sys.stdout.write("\033[?25l")
    try:
        h = len(frames[0])
        if titre:
            print(titre)
        for t in range(tours * len(frames)):
            if t:
                sys.stdout.write(f"\033[{h}F")
            sys.stdout.write("\n".join(frames[t % len(frames)]) + "\n")
            sys.stdout.flush()
            time.sleep(1 / ips)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")


def jouer(state, args, tours=None):
    nom = args[0] if args else None
    ind = None
    if nom:
        e = B.espece(nom)
        ind = next((c for c in reversed(state.get("captures", [])) if e and c["espece"] == e["nom"]), None)
    else:
        ind = active(state)
    if not ind:
        print(" " + t("eq.aucune"))
        return
    quoi = (args[1] if len(args) > 1 else "statique").lower().replace("é", "e").replace("è", "e")
    if quoi not in ANIMS:
        print(" " + t("eq.animations", liste=", ".join(ANIMS)))
        return
    if quoi == "evolution" and stade(ind) == "bebe":
        print(" " + t("eq.encore_bebe", nom=ind["espece"]))
        return
    r = animation(ind, quoi, aura=True)
    if r is None:
        from . import aura as A
        print("\n".join(B.dessin(B.espece(ind["espece"]), ind.get("shiny"), stade=stade(ind),
                                 vid=ind.get("variante", "classique"), teinte=ind.get("teinte", 0.5),
                                 aura=A.palier_ind(ind))))
        print(f" {DIM}" + t("eq.pas_d_image", nom=ind["espece"]) + RESET)
        return
    frames, ips = r
    if tours is None:
        tours = 1 if quoi == "evolution" else 3
    titre = f" {B.nom_affiche(B.espece(ind['espece']), ind.get('shiny'), B.rarete_de(ind))} {DIM}· {B.nom_stade(stade(ind))} · {quoi}{RESET}"
    derouler(frames, ips, tours, titre)
    if quoi == "evolution":
        print(f" {BOLD}" + t("eq.nouvelle_forme", nom=ind["espece"], stade=B.nom_stade(stade(ind))) + RESET)
