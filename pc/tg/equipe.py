"""L'équipe : les bestioles dressées grandissent (enfant → ado → adulte → forme finale) en gardant
leur nom, et s'animent dans le terminal.

La bestiole « active » (tg equipe <nom>) gagne de l'expérience à chaque commande que tu tapes.
Les animations détaillées existent pour les espèces qui ont un dessin complet (Abyssor pour
l'instant) ; les autres gardent leur petit sprite.
"""
import base64
import colorsys
import json
import pkgutil
import sys
import time
import zlib

from . import bestiaire as B
from . import core
from .plateforme import BOLD, DIM, RESET, fg

STADES = ["enfant", "ado", "adulte", "finale"]
NOM_STADE = {"enfant": "enfant", "ado": "ado", "adulte": "adulte", "finale": "forme finale"}
SEUILS = {"enfant": 150, "ado": 500, "adulte": 1500}          # XP pour passer au stade suivant
ANIMS = ["statique", "mange", "attaque", "salut", "parle", "dort", "content", "affame", "confus", "colere",
         "victoire", "ko", "evolution"]
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
    a = d["anims"].get(stade, {}).get(nom)
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
    return ind.get("stade", "enfant")


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
        core.log(state, f"🌟 {ind['espece']} évolue : {NOM_STADE[ind['stade']]} !")
        core.notif(state, f"🌟 {ind['espece']} évolue en {NOM_STADE[ind['stade']]} ! (tg anime {ind['espece']} evolution)")
        core.say(state, f"Oh ! {ind['espece']} brille… il évolue en {NOM_STADE[ind['stade']]} ! "
                        f"Regarde : tg anime {ind['espece'].lower()} evolution", 14)
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
        return [" Ton équipe est vide : dresse ta première bestiole en explorant le terrain de jeu !"]
    act = active(state)
    lignes = [f" {fg(213)}── 🐾 Équipe de {state['name']} ──{RESET}", ""]
    for c in caps[-12:][::-1]:
        e = B.espece(c["espece"])
        if not e:
            continue
        s = stade(c)
        seuil = SEUILS.get(s)
        barre = f"{c.get('xp', 0)}/{seuil} XP" if seuil else "stade maximal"
        marque = f"{fg(226)}★ active{RESET} " if c is act else "         "
        lignes.append(f" {marque}{B.nom_affiche(e, c.get('shiny'))} {DIM}· {NOM_STADE[s]} · {barre}"
                      f"{' · animé' if anime(e['nom']) else ''}{RESET}")
    lignes += ["", f" {DIM}Choisir l'active : tg equipe <nom> · la voir bouger : tg anime <nom> [animation]{RESET}"]
    return lignes


def choisir(state, nom):
    e = B.espece(nom)
    caps = [c for c in state.get("captures", []) if e and c["espece"] == e["nom"]]
    if not caps:
        return f" Tu n'as pas encore dressé de « {nom} »."
    state["active"] = caps[-1]["id"]
    return f" ★ {caps[-1]['espece']} est maintenant ta bestiole active : elle grandit à chaque commande que tu tapes."


# ---------------------------------------------------------------- tg anime
def jouer(state, args):
    nom = args[0] if args else None
    ind = None
    if nom:
        e = B.espece(nom)
        ind = next((c for c in reversed(state.get("captures", [])) if e and c["espece"] == e["nom"]), None)
    else:
        ind = active(state)
    if not ind:
        print(" Aucune bestiole de ce nom dans ton équipe. (tg equipe pour la liste)")
        return
    quoi = (args[1] if len(args) > 1 else "statique").lower().replace("é", "e").replace("è", "e")
    s = stade(ind)
    if quoi == "evolution":                  # on rejoue l'évolution qui a mené au stade actuel
        i = STADES.index(s)
        if i == 0:
            print(f" {ind['espece']} est encore enfant : il n'a pas encore évolué.")
            return
        s = STADES[i - 1]
    teinte = ind.get("teinte", 0.5) if ind.get("shiny") else 0.0
    r = images(ind["espece"], s, quoi, teinte)
    if r is None:
        if not anime(ind["espece"]):
            print("\n".join(B.dessin(B.espece(ind["espece"]), ind.get("shiny"))))
            print(f" {DIM}{ind['espece']} n'a pas encore d'animation détaillée.{RESET}")
        else:
            print(f" Animations : {', '.join(a for a in ANIMS)}")
        return
    frames, ips = r
    tours = 1 if quoi == "evolution" else 3
    titre = f" {B.nom_affiche(B.espece(ind['espece']), ind.get('shiny'))} {DIM}· {NOM_STADE[stade(ind)]} · {quoi}{RESET}"
    sys.stdout.write("\033[?25l")
    try:
        h = len(frames[0])
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
    if quoi == "evolution":
        print(f" {BOLD}{ind['espece']} est devenu {NOM_STADE[stade(ind)]} !{RESET}")
