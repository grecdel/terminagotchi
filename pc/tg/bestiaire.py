"""Le bestiaire commun (150 espèces), partagé avec l'appli Android et le site.

Les données viennent de bestiaire.json (généré par donnees/generer_bestiaire.py).
"""
import colorsys
import json
import pkgutil
import random
import secrets
import time
import unicodedata
import base64
import zlib

from .plateforme import RESET

_DONNEES = None

COULEUR_RARETE = {"commune": "#b0b0c0", "peu commune": "#5fd787", "rare": "#5fafff", "épique": "#c77dff",
                  "légendaire": "#ffaf00", "mythique": "#ff5f87"}
XP_RARETE = {"commune": 15, "peu commune": 25, "rare": 40, "épique": 65, "légendaire": 100, "mythique": 200}
STADES = ["bebe", "enfant", "ado", "adulte", "ancien"]
_SPRITES = None


class _Habitats(dict):
    """Nom des lieux (« le volcan ») à partir du dossier de zone (« volcan »)."""
    def get(self, k, defaut=None):
        return donnees().get("habitats", {}).get(k, defaut)


HABITATS = _Habitats()


def donnees():
    global _DONNEES
    if _DONNEES is None:
        brut = pkgutil.get_data(__package__, "bestiaire.json")
        _DONNEES = json.loads(brut.decode("utf-8"))
    return _DONNEES


def especes():
    return donnees()["especes"]


def publiques():
    """Les 150 espèces du bestiaire (sans les secrètes)."""
    return [e for e in especes() if not e.get("secrete")]


def _simple(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def espece(nom):
    """Retrouve une espèce par son nom (sans tenir compte des majuscules/accents), ou son numéro."""
    if nom is None:
        return None
    n = _simple(str(nom).strip().lstrip("#"))
    for e in especes():
        if _simple(e["nom"]) == n or e["id"] == n or str(e["numero"]) == n.lstrip("0"):
            return e
    for e in especes():
        if _simple(e["nom"]).startswith(n) and len(n) >= 3:
            return e
    return None


def migrer(state):
    """Sauvegardes d'avant le nouveau bestiaire : chaque ancienne espèce devient la nouvelle de même numéro."""
    anciens = donnees().get("anciens", {})
    if not state or not anciens:
        return state

    def nouveau(nom):
        if nom is None or espece(nom):
            return nom
        n = anciens.get(nom)
        e = next((x for x in especes() if x["numero"] == n), None)
        return e["nom"] if e else nom
    for c in state.get("captures", []):
        c["espece"] = nouveau(c.get("espece"))
        if c.get("stade") == "finale":
            c["stade"] = "ancien"
    col = {}
    for n, k in state.get("collection", {}).items():
        col[nouveau(n)] = col.get(nouveau(n), 0) + k
    if "collection" in state:
        state["collection"] = col
    for s_ in state.get("sauvages", []):
        s_["e"] = nouveau(s_.get("e"))
    if state.get("dressage"):
        state["dressage"]["espece"] = nouveau(state["dressage"].get("espece"))
    return state


def tirer(rnd=random):
    """Une apparition : l'espèce (selon sa fréquence), sa variante (selon son habitat), shiny ou pas."""
    d = donnees()
    pub = publiques()
    e = rnd.choices(pub, [d["poids_frequence"][x["frequence"]] for x in pub])[0]
    v = rnd.choices(e["variantes"], [x["chance"] for x in e["variantes"]])[0]
    shiny = rnd.randrange(d["chance_shiny"]) == 0
    return e, shiny, v["id"]


def variante(e, vid):
    return next((v for v in e.get("variantes", []) if v["id"] == vid), (e.get("variantes") or [{}])[0])


def note(e, vid, qualite, shiny):
    """Note sur 100 : 60 % qualité des stats, 25 % variante, 15 % puissance de l'espèce, +10 shiny."""
    p = donnees()["rarete"]["poids"]
    n = (p["stats"] * qualite + p["variante"] * variante(e, vid).get("score", 0)
         + p["puissance"] * (e.get("puissance", 1) - 1) / 14 + (p["bonus_shiny"] if shiny else 0))
    return round(min(100.0, n), 1)


def rarete(e, vid, qualite, shiny):
    """La rareté d'un individu (et plus de l'espèce) ; Abyssor est toujours mythique."""
    r = donnees()["rarete"]
    if e["id"] in r.get("speciales", {}):
        return r["speciales"][e["id"]]
    n = note(e, vid, qualite, shiny)
    nom = "commune"
    for seuil, palier in r["paliers"]:
        if n >= seuil:
            nom = palier
    return nom


def rarete_de(ind):
    """Rareté d'une bestiole de la troupe (les anciennes captures n'en ont pas : on la recalcule)."""
    if ind.get("rarete"):
        return ind["rarete"]
    e = espece(ind.get("espece"))
    if not e:
        return "commune"
    return rarete(e, ind.get("variante", "classique"), ind.get("potentiel", 50) / 100, ind.get("shiny"))


def individu(e, shiny, zone="", vid="classique", qualite=None):
    """Une bestiole dressée : unique, avec sa marque, ses stats tirées et sa rareté."""
    d = donnees()
    q = random.random() if qualite is None else qualite
    iv = {k: max(0, min(31, round(31 * (q + random.gauss(0, 0.08))))) for k in e["stats"]}
    return {
        "id": secrets.token_hex(5),
        "espece": e["nom"],
        "variante": vid,
        "shiny": bool(shiny),
        "date": int(time.time() * 1000),
        "marque": random.choice(d["marques"]),
        "humeur": random.choice(d["humeurs"]),
        "taille": round(e["taille_cm"] * random.uniform(0.8, 1.25), 1),
        "qualite": round(q, 3),
        "potentiel": round(100 * sum(iv.values()) / (31 * len(iv))),
        "stats": {k: v + iv[k] // 2 for k, v in e["stats"].items()},
        "note": note(e, vid, q, shiny),
        "rarete": rarete(e, vid, q, shiny),
        "zone": zone,
    }


# ---------------------------------------------------------------- images en gros pixels (5 stades)
def sprites():
    global _SPRITES
    if _SPRITES is None:
        try:
            _SPRITES = json.loads(zlib.decompress(pkgutil.get_data(__package__, "sprites.bin")))
        except (OSError, TypeError, ValueError, zlib.error):
            _SPRITES = {}
    return _SPRITES


def image(e, stade="adulte", vid="classique"):
    """(largeur, hauteur, octets, palette) d'un stade ; la forme classique si la variante n'est pas dessinée."""
    s = sprites()
    jeu = s.get(f"{e['id']}/{vid}") or s.get(f"{e['id']}/classique")
    if not jeu:
        return None
    st = jeu["stades"].get(stade) or jeu["stades"]["adulte"]
    return st[0], st[1], zlib.decompress(base64.b64decode(st[2])), jeu["palette"]


def decaler(hexa, teinte):
    """Décale la teinte d'une couleur (shiny : chaque individu a la sienne)."""
    r, g, b = _rgb(hexa)
    h, l, s_ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    r, g, b = colorsys.hls_to_rgb((h + teinte) % 1, l, min(1, s_ * 1.1))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def lignes_image(w, h, octets, pal):
    """Octets indexés → lignes de demi-blocs colorés (2 pixels par caractère)."""
    out = []
    for y in range(0, h, 2):
        s = ""
        for x in range(w):
            a = octets[y * w + x]
            b = octets[(y + 1) * w + x] if y + 1 < h else 0
            ca, cb = (pal[a - 1] if a else None), (pal[b - 1] if b else None)
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += fg24(ca) + "▀" + RESET
            elif ca is None:
                s += fg24(cb) + "▄" + RESET
            else:
                s += fg24(ca) + bg24(cb) + "▀" + RESET
        out.append(s)
    return out


# ---------------------------------------------------------------- couleurs « vraies » (24 bits)
def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def fg24(h):
    r, g, b = _rgb(h)
    return f"\033[38;2;{r};{g};{b}m"


def bg24(h):
    r, g, b = _rgb(h)
    return f"\033[48;2;{r};{g};{b}m"


def dessin(e, shiny=False, grand=False, stade="adulte", vid="classique", teinte=0.5):
    """La bestiole en pixel art pour le terminal (2 pixels verticaux par caractère).
    Les espèces du nouveau bestiaire ont une image par stade et par variante ; Abyssor garde son dessin."""
    img = image(e, stade, vid)
    if img:
        w, h, octets, pal = img
        if shiny:
            pal = [decaler(c, teinte) for c in pal]
        return lignes_image(w, h, octets, pal)
    return _dessin_ancien(e, shiny, grand)


def _dessin_ancien(e, shiny=False, grand=False):
    """La bestiole en pixel art pour le terminal (2 pixels verticaux par caractère).
    grand=True : version détaillée (48 px) pour les espèces qui en ont une."""
    if grand and e.get("sprite_grand"):
        rows = e["sprite_grand"]
        pal = e["palette_grand_shiny"] if shiny else e["palette_grand"]
    else:
        rows = e["sprite_shiny"] if shiny else e["sprite"]
        pal = e["palette_shiny"] if shiny else e["palette"]
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows]
    if len(rows) % 2:
        rows.append("." * w)
    out = []
    for i in range(0, len(rows), 2):
        s = ""
        for a, b in zip(rows[i], rows[i + 1]):
            ca, cb = pal.get(a), pal.get(b)
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += fg24(ca) + "▀" + RESET
            elif ca is None:
                s += fg24(cb) + "▄" + RESET
            else:
                s += fg24(ca) + bg24(cb) + "▀" + RESET
        out.append(s)
    return out


def arc_en_ciel(texte, decalage=0.0):
    """Écriture RGB : chaque lettre d'une couleur différente."""
    out = ""
    n = max(1, len(texte))
    for i, c in enumerate(texte):
        r, g, b = colorsys.hsv_to_rgb((decalage + i / (n + 4)) % 1.0, 0.75, 1.0)
        out += f"\033[38;2;{int(r * 255)};{int(g * 255)};{int(b * 255)}m{c}"
    return out + RESET


def nom_affiche(e, shiny=False, rarete_ind=None):
    """Nom coloré : arc-en-ciel pour les shiny, les légendaires et les mythiques ; couleur de rareté sinon."""
    nom = e["nom"] + (" ✨" if shiny else "")
    r = rarete_ind or ("mythique" if e.get("rarete") == "mythique" else None)
    if shiny or r in ("légendaire", "mythique"):
        return arc_en_ciel(nom)
    if r:
        return fg24(COULEUR_RARETE[r]) + nom + RESET
    if "palette" in e:
        return fg24(e["palette"]["a"]) + nom + RESET
    img = image(e)
    return (fg24(img[3][len(img[3]) // 2]) if img else "") + nom + RESET


def libelle_rarete(r):
    return fg24(COULEUR_RARETE.get(r, "#ffffff")) + r + RESET
