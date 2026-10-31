"""Vecteurs communs Python / Kotlin (/ JavaScript) des Ponts des Nombres et des récompenses par monde.

    python3 pc/outils/vecteurs_phase4.py            réécrit donnees/maths/vecteurs.json et donnees/recompenses/vecteurs.json
    python3 pc/outils/vecteurs_phase4.py --verifier code de sortie 1 si les fichiers ne sont plus à jour

Les vecteurs sont relus par pc/outils/test_programme.py, tests/jvm/Programme.kt et site/test/tirage.mjs (le serveur
refait chaque tirage gardé par une faveur : il doit l'accepter comme les autres).
"""
import json
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import langue, maths, programme, recompenses  # noqa: E402

GRAINES = [
    "0" * 64,
    "ffffffffffffffff" + "0" * 48,
    "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95",
    "8000000000000001" + "fac71ce" * 6 + "00",
]
QUESTIONS = {
    "fr": ["partager des bonbons", "pourquoi on met un exposant", "le reste d'une division", "les 0 et les 1",
           "compter les étoiles", "combien font 3 fois 4", "enlever des billes", "horloge", "ajouter", "binaire",
           "modulo", "hexadécimal", "moyenne", "pourcentage", "nombres premiers", "puissance"],
    "en": ["share sweets", "remainder", "power", "binary", "multiply", "count"],
}


def maths_vecteurs():
    exos = []
    for mid, n in programme.donnees()["maths"].items():
        if not n.get("fiche"):
            continue
        typ = n["exercice"]["type"]
        for graine in (0, 1761955200, 2 ** 40 + 7):
            for k in range(8):
                p, rep, verif = maths.generer(typ, graine, k)
                exos.append({"type": typ, "graine": graine, "k": k, "params": {a: str(b) for a, b in p.items()},
                             "reponse": rep, "verif": verif})
    recherches = []
    for code, qs in QUESTIONS.items():
        langue.definir(code)
        maths._INDEX.clear()
        for q in qs:
            recherches.append({"langue": code, "question": q, "attendu": maths.chercher(q)})
    langue.definir("fr")
    prereq = {mid: maths.tous_prerequis(mid) for mid in programme.donnees()["maths"]}
    return {"note": "Généré par pc/outils/vecteurs_phase4.py", "exercices": exos, "recherches": recherches,
            "tous_prerequis": prereq}


def recompenses_vecteurs():
    cas = []
    for m in programme.donnees()["mondes"]:
        for x in m["exploits"]:
            genre = x["recompense"]
            cible = m.get("gardiens", {}).get(x.get("boite")) if genre == "gardien" else None
            for g in GRAINES:
                for n0 in (0, 17, 60, 123):
                    n, champs = recompenses.favoriser(g, n0, genre, m["types"], cible=cible)
                    cas.append({"monde": m["id"], "exploit": x["id"], "genre": genre, "types": m["types"],
                                **({"cible": cible} if cible else {}),
                                "valeur": g, "n0": n0, "attendu": {"n": n, "champs": champs}})
    return {"note": "Généré par pc/outils/vecteurs_phase4.py ; chaque tirage gardé est un tirage exact de "
                    "(valeur, n) : le serveur le vérifie comme les autres (site/test/tirage.mjs).",
            "conf": programme.donnees()["recompenses"], "cas": cas}


def main():
    langue.definir("fr")
    sorties = {RACINE / "donnees/maths/vecteurs.json": maths_vecteurs(),
               RACINE / "donnees/recompenses/vecteurs.json": recompenses_vecteurs()}
    verifier = "--verifier" in sys.argv
    ko = 0
    for chemin, d in sorties.items():
        txt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
        if verifier:
            if not chemin.exists() or chemin.read_text(encoding="utf-8") != txt:
                print(f"✖ {chemin.relative_to(RACINE)} n'est plus à jour : python3 pc/outils/vecteurs_phase4.py")
                ko += 1
            else:
                print(f"✔ {chemin.relative_to(RACINE)} à jour")
        else:
            os.makedirs(chemin.parent, exist_ok=True)
            chemin.write_text(txt, encoding="utf-8")
            print(f"écrit {chemin.relative_to(RACINE)}")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
