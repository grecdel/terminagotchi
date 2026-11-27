"""Le bestiaire commun (150 espèces), partagé avec l'appli Android et le site.

Les données viennent de bestiaire.json (généré par donnees/generer_bestiaire.py à partir des dessins
de donnees/bestiaire2) : 10 familles × 15 espèces, chacune dessinée à chaque stade, plus des variantes.
"""
import colorsys
import json
import pkgutil
import random
import secrets
import time
import unicodedata

from .plateforme import RESET

_DONNEES = None

# Lieux de l'ancien bestiaire (vieilles sauvegardes) ; les nouveaux viennent de bestiaire.json (« lieux »).
HABITATS = {
    "archives": "les archives", "marais": "le marais", "usine": "l'usine", "grenier": "le grenier",
    "forteresse": "la forteresse", "atelier": "l'atelier", "forge": "la forge", "foret": "la forêt",
    "montagne": "la montagne", "bibliotheque": "la bibliothèque", "coffre": "le coffre-fort",
    "laboratoire": "le laboratoire", "arcade": "la salle d'arcade", "faille": "la faille", "grotte": "la grotte",
}
COULEUR_RARETE = {"commune": "#b0b0c0", "peu commune": "#5fd787", "rare": "#5fafff", "légendaire": "#ffaf00"}
XP_RARETE = {"commune": 15, "peu commune": 25, "rare": 40, "légendaire": 100}


def donnees():
    global _DONNEES
    if _DONNEES is None:
        brut = pkgutil.get_data(__package__, "bestiaire.json")
        _DONNEES = json.loads(brut.decode("utf-8"))
        HABITATS.update(_DONNEES.get("lieux", {}))
    return _DONNEES


def nom_lieu(base):
    donnees()
    return HABITATS.get(base, base)


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
    for vieux, nouveau in donnees().get("anciens", {}).items():   # nom de l'ancien bestiaire
        if _simple(vieux) == n:
            return espece(nouveau)
    return None


def migrer(state):
    """Vieilles sauvegardes : les bestioles de l'ancien bestiaire prennent le nom de leur remplaçante
    (même numéro). Les monstres sauvages en cours sont oubliés (ils vivaient dans d'anciens lieux)."""
    anciens = donnees().get("anciens", {})
    if not anciens or state.get("bestiaire_v", 1) >= donnees().get("version", 1):
        return state
    for c in state.get("captures", []):
        c["espece"] = anciens.get(c.get("espece"), c.get("espece"))
    coll = {}
    for n, k in state.get("collection", {}).items():
        n = anciens.get(n, n)
        coll[n] = coll.get(n, 0) + k
    state["collection"] = coll
    if state.get("dressage_essais"):
        state["dressage_essais"] = {anciens.get(n, n): j for n, j in state["dressage_essais"].items()}
    state["sauvages"] = []
    state["dressage"] = None
    state["dressage_familles"] = []
    state["bestiaire_v"] = donnees().get("version", 1)
    return state


def tirer_variante(e, rnd=random):
    """Forme de l'individu (classique, volcan, lave…), selon les chances de chaque variante dessinée."""
    v = e.get("variantes") or [{"id": "classique", "chance": 100}]
    return rnd.choices([x["id"] for x in v], [x["chance"] for x in v])[0]


def nom_variante(e, variante):
    if not variante or variante == "classique":
        return ""
    return next((v["nom"] for v in e.get("variantes", []) if v["id"] == variante), variante)


def tirer(rnd=random):
    d = donnees()
    raretes = d["raretes"]
    rarete = rnd.choices(raretes, [d["poids"][r] for r in raretes])[0]
    e = rnd.choice([x for x in publiques() if x["rarete"] == rarete])
    shiny = rnd.randrange(d["chance_shiny"]) == 0
    return e, shiny


def individu(e, shiny, zone="", variante=None):
    """Une bestiole capturée : unique, avec sa marque, sa forme et son potentiel."""
    d = donnees()
    iv = {k: random.randint(0, 31) for k in e["stats"]}
    return {
        "id": secrets.token_hex(5),
        "espece": e["nom"],
        "shiny": bool(shiny),
        "date": int(time.time() * 1000),
        "marque": random.choice(d["marques"]),
        "humeur": random.choice(d["humeurs"]),
        "taille": round(e["taille_cm"] * random.uniform(0.8, 1.25), 1),
        "potentiel": round(100 * sum(iv.values()) / (31 * len(iv))),
        "stats": {k: v + iv[k] // 4 for k, v in e["stats"].items()},
        "zone": zone,
        "variante": variante or tirer_variante(e),
    }


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


def dessin(e, shiny=False, grand=False, stade=None, variante=None, teinte=None):
    """La bestiole en pixel art pour le terminal (2 pixels verticaux par caractère).
    grand=True : version détaillée (32 px) ; stade (enfant, ado, adulte, finale) et variante choisissent
    le dessin exact quand il existe ; teinte : couleur shiny propre à un individu."""
    ds = (e.get("dessins") or {}).get(variante or "classique") or (e.get("dessins") or {}).get("classique")
    if ds and (stade or variante) and (ds.get(stade or "adulte") if grand else ds.get("petit")):
        x = ds[stade or "adulte"] if grand else ds["petit"]
        pal = x["p"]
        if shiny:
            pal = decaler(pal, teinte if teinte is not None else 0.5)
        return _rendu(x["l"], pal)
    if grand and e.get("sprite_grand"):
        rows = e["sprite_grand"]
        pal = e["palette_grand_shiny"] if shiny else e["palette_grand"]
    else:
        rows = e["sprite_shiny"] if shiny else e["sprite"]
        pal = e["palette_shiny"] if shiny else e["palette"]
    return _rendu(rows, pal)


def decaler(palette, dec):
    """Tourne la teinte d'une palette (shiny)."""
    out = {}
    for k, h in palette.items():
        r, g, b = (v / 255 for v in _rgb(h))
        hh, l, s = colorsys.rgb_to_hls(r, g, b)
        r, g, b = colorsys.hls_to_rgb((hh + dec) % 1, l, s)
        out[k] = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    return out


def dessin_individu(ind, grand=True):
    """Une bestiole de la troupe, à son stade et dans sa forme."""
    e = espece(ind["espece"])
    return dessin(e, ind.get("shiny"), grand, stade=ind.get("stade", "enfant"),
                  variante=ind.get("variante", "classique"), teinte=ind.get("teinte"))


def _rendu(rows, pal):
    w = max((len(r) for r in rows), default=0)
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


def nom_affiche(e, shiny=False):
    """Nom coloré : arc-en-ciel pour les shiny et les légendaires."""
    nom = e["nom"] + (" ✨" if shiny else "")
    if shiny or e["rarete"] == "légendaire":
        return arc_en_ciel(nom)
    return fg24(couleur(e)) + nom + RESET


def couleur(e):
    """Couleur dominante (la plus claire des couleurs fréquentes du petit dessin)."""
    pal, rows = e["palette"], e["sprite"]
    compte = {}
    for r in rows:
        for ch in r:
            if ch in pal:
                compte[ch] = compte.get(ch, 0) + 1
    freq = sorted(compte, key=compte.get, reverse=True)[:4] or list(pal)
    if not freq:
        return "#c0c0c0"
    return pal[max(freq, key=lambda k: sum(_rgb(pal[k])))]
