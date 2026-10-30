"""Les œufs à type : 9 types de biome (ceux de biomes.json) × 3 états (intact, fissuré, éclosion).

Données : oeufs.json (copie exacte de donnees/oeufs/oeufs.json, comme app/src/main/assets/oeufs.json), fabriqué
par donnees/bestiaire2/generer_oeufs.py depuis les dessins donnees/oeufs/oeuf_<type>_<etat>.png.
Nouvelle partie : l'œuf reçoit un type au hasard (state["oeuf_type"]) et le compagnon qui en sort reçoit le MÊME
type (guide : type_c), et une ESPÈCE de départ de ce type (state["espece_compagnon"], liste fixe de depart.json,
copie exacte de donnees/oeufs/depart.json) : le bébé qui sort de l'œuf, puis le compagnon du jeu (sprites.py). Une
partie d'avant (sans « espece_compagnon ») garde sa créature d'origine. Une ancienne partie garde le type de son compagnon ; son œuf (s'il faut le montrer) est
celui de ce type. Même calcul sur Android : Oeufs.kt. Tests : pc/outils/test_intro.py, tests/jvm/Intro.kt.

image(ty, fele, nom, k) : l'œuf de l'intro (lignes de caractères), le même rôle que l'ancien œuf blanc :
  fele 0 intact · 1 intact + une fêlure qui luit · 2 le dessin fissuré · 3 fissuré + une grande fêlure qui luit ;
  nom « remue » (il penche), « brille » (son contour luit, des étincelles), « craque » (la fêlure s'éclaire),
  « eclot » (il tremble, puis le dessin d'éclosion ; None à la fin : la créature prend la place).
"""
import json
import pkgutil
import random

_D = {}
_DEP = {}


def donnees():
    if not _D:
        _D.update(json.loads(pkgutil.get_data(__package__, "oeufs.json").decode("utf-8")))
    return _D


def types():
    return list(donnees()["types"])


def departs():
    """Type → [ids des espèces de départ] (depart.json, le même fichier sur Android)."""
    if not _DEP:
        _DEP.update(json.loads(pkgutil.get_data(__package__, "depart.json").decode("utf-8"))["depart"])
    return _DEP


def espece_depart(ty, rnd=random):
    """Une espèce de départ du type ty (son id), tirée au hasard dans la liste fixe."""
    liste = departs().get(ty) or [x for l in departs().values() for x in l]
    return rnd.choice(liste)


def choisir(state, ty=None):
    """Une nouvelle partie : le type de l'œuf, le même pour le compagnon qui en sortira, et son espèce."""
    ty = ty if ty in types() else random.choice(types())
    state["oeuf_type"] = ty
    state["espece_compagnon"] = espece_depart(ty)
    g = state.get("guide")
    if isinstance(g, dict):
        g["type_c"] = ty
    return ty


def type_de(state):
    """Le type de l'œuf d'une partie : celui du compagnon s'il en a un (anciennes parties), sinon celui tiré."""
    g = state.get("guide") if isinstance(state, dict) else None
    if isinstance(g, dict) and g.get("type_c") in types():
        return g["type_c"]
    if isinstance(state, dict) and state.get("oeuf_type") in types():
        return state["oeuf_type"]
    from . import guide
    return guide.type_compagnon_initial(state or {})


def taille(nom="grand"):
    return tuple(donnees()["tailles"][nom])


def palette(ty):
    """Caractère → couleur « #rrggbb » : les couleurs du dessin, puis les effets (lueur du type, éclair blanc)."""
    x = donnees()["types"][ty]
    chiffres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    pal = {chiffres[k]: c for k, c in enumerate(x["palette"])}
    pal.update({"f": x["lueur"], "h": x["lueur"], "y": x["lueur"]})
    pal.update(donnees()["effets"])
    return pal


def petit(ty, fele=0):
    """L'œuf de l'écran principal, du widget, de la notification (cadre 18×16) : intact, puis fissuré."""
    return list(donnees()["types"][ty]["petit"]["fissure" if fele >= 2 else "intact"])


def image(ty, fele, nom="", k=0):
    """Une image de l'œuf de l'intro (lignes de caractères). Même calcul qu'Oeufs.image (Android)."""
    if ty not in donnees()["types"]:
        ty = types()[0]
    x = donnees()["types"][ty]
    W, H = taille()
    if nom == "eclot" and k >= 6:
        return None
    etat = "eclosion" if nom == "eclot" and k >= 3 else "fissure" if fele >= 2 else "intact"
    dx = 0
    if nom == "remue":
        dx = (0, -1, 0, 1)[k % 4]
    elif nom in ("craque", "eclot") and k < 2:
        dx = (1, -1)[k % 2]
    g = [["."] * W for _ in range(H)]
    for y, r in enumerate(x["grand"][etat]):
        for xx, ch in enumerate(r):
            if ch != "." and 0 <= xx + dx < W:
                g[y][xx + dx] = ch
    eclair = nom == "craque" and k % 2 == 0
    traits = []
    if etat != "eclosion":
        if fele == 1 or (fele == 2 and eclair):
            traits = x["feles"][0]
        elif fele >= 3:
            traits = x["feles"][1]
    for px, py in traits:
        xx = px + dx
        if 0 <= xx < W and g[py][xx] != ".":
            g[py][xx] = "c" if eclair else "f"
    if nom == "brille" and k % 2 == 0:            # le contour luit
        bord = [(xx, y) for y in range(H) for xx in range(W) if g[y][xx] != "." and any(
            not (0 <= xx + a < W and 0 <= y + b < H) or g[y + b][xx + a] == "." for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for xx, y in bord:
            g[y][xx] = "h"
    if nom == "brille" or (nom == "eclot" and k >= 3):     # des étincelles autour
        for px, py in donnees()["etincelles"][k % 2]:
            if g[py][px] == ".":
                g[py][px] = "y"
    return ["".join(r) for r in g]
