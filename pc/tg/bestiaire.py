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

from .plateforme import RESET

_DONNEES = None

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
    return _DONNEES


def especes():
    return donnees()["especes"]


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


def tirer(rnd=random):
    d = donnees()
    raretes = d["raretes"]
    rarete = rnd.choices(raretes, [d["poids"][r] for r in raretes])[0]
    e = rnd.choice([x for x in especes() if x["rarete"] == rarete])
    shiny = rnd.randrange(d["chance_shiny"]) == 0
    return e, shiny


def individu(e, shiny, zone=""):
    """Une bestiole capturée : unique, avec sa marque et son potentiel."""
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


def dessin(e, shiny=False):
    """La bestiole en pixel art pour le terminal (2 pixels verticaux par caractère)."""
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


def nom_affiche(e, shiny=False):
    """Nom coloré : arc-en-ciel pour les shiny et les légendaires."""
    nom = e["nom"] + (" ✨" if shiny else "")
    if shiny or e["rarete"] == "légendaire":
        return arc_en_ciel(nom)
    return fg24(e["palette"]["a"]) + nom + RESET
