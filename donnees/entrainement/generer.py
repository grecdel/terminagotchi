"""Fabrique donnees/entrainement/vecteurs.json : les exercices tirés par le PC (pc/tg/entrainement.py).

    python3 donnees/entrainement/generer.py

Les mêmes vecteurs sont vérifiés par l'appli (tests/jvm/Entrainement.kt) et le site (site/test/tirage.mjs) :
même tirage, même empreinte, même réponse, mêmes médailles, mêmes échelons (et étoiles), mêmes semaines, et les
mêmes dessins de badges complets (galons, étoiles) : « ecussons », empreinte SHA-256 des pixels (dessin_empreinte).
"""
import hashlib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
from tg import badges as B  # noqa: E402
from tg import entrainement as E  # noqa: E402


def dessin_empreinte(g):
    """SHA-256 d'une grille de pixels : lignes séparées par « / », pixels par « , » (transparent = vide)."""
    return hashlib.sha256("/".join(",".join(c or "" for c in l) for l in g).encode()).hexdigest()


def vecteurs():
    out = {"exercices": [], "medailles": [], "echelons": [], "semaines": [], "ecussons": []}
    for i in range(6):
        valeur = hashlib.sha256(f"vecteur-entrainement-{i}".encode()).hexdigest()
        for typ in E.TYPES:
            for k in (0, 1, 7 * i + 3, 99):
                p, emp = E.generer(typ, valeur, k)
                out["exercices"].append({"type": typ, "valeur": valeur, "k": k, "empreinte": emp,
                                         "reponse": E.reponse(typ, p)})
    for typ in E.TYPES:
        par = E.TYPES[typ][3]
        for s in (0.5, par, par + 0.1, 2 * par, 2 * par + 0.1, 4 * par, 4 * par + 0.1, 900):
            out["medailles"].append({"type": typ, "t": round(s, 1), "medaille": E.medaille(typ, round(s, 1))})
    for n in (0, 1, 2, 3, 4, 5, 8, 12, 13, 14, 15, 19, 23, 27, 29, 30, 35, 45, 49, 50, 62, 63, 75, 88, 99, 100, 149, 150,
              200, 299, 300, 900):
        for ors, dia in ((0, 0), (1, 0), (3, 2), (3, 3)):      # ors : médailles d'or ou de diamant ; dia : de diamant
            k = B.echelon_de(n, ors, dia)
            out["echelons"].append({"n": n, "or": ors, "diamant": dia, "echelon": k, "etoiles": B.etoiles_de(n, k)})
    for i, f in enumerate(B.FAMILLES):
        for e in B.ECHELONS:
            out["ecussons"].append({"famille": f, "echelon": e, "etoiles": (i + len(e)) % 4,
                                    "empreinte": dessin_empreinte(B.ecusson(f, e, (i + len(e)) % 4))})
    out["ecussons"].append({"famille": None, "echelon": None, "etoiles": 0, "empreinte": dessin_empreinte(B.ecusson(None, None))})
    for ts in (0, 1704067200, 1735603200, 1767139200, 1793000000, 1798675200):
        out["semaines"].append({"t": ts, "semaine": E.semaine(ts)})
    return out


if __name__ == "__main__":
    f = Path(__file__).with_name("vecteurs.json")
    f.write_text(json.dumps(vecteurs(), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{f} écrit")
