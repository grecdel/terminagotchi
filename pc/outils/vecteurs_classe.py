"""Les vecteurs communs du mode classe (Python ↔ site) : donnees/classe/vecteurs.json.

    python3 pc/outils/vecteurs_classe.py              écrit les vecteurs (depuis pc/tg/classe.py)
    python3 pc/outils/vecteurs_classe.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Tous les codes de séance (chapitres 0 à 18, les 8 combinaisons d'options) et quelques codes faux : la page
/enseignants du site (site/src/enseignants_fr.js) fabrique EXACTEMENT les mêmes codes (site/test/test.mjs).
"""
import itertools
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import classe as C  # noqa: E402
from tg import histoire  # noqa: E402

FICHIER = RACINE / "donnees" / "classe" / "vecteurs.json"


def vecteurs():
    combis = ["".join(x) for k in range(4) for x in itertools.combinations(C.OPTIONS, k)]
    codes = [{"n": n, "options": o, "code": C.fabriquer(n, o)} for n in range(max(c["n"] for c in histoire.CHAPITRES) + 1) for o in combis]
    faux = ["05-GS-X", "05-SG-K", "5-GS-K", "05-GZ-K", "", "AB-C", "05-GGS-K"]
    return {"note": "pc/outils/vecteurs_classe.py", "lettres": C.LETTRES, "codes": codes,
            "faux": [{"code": f, "lu": C.lire(f)} for f in faux]}


def texte():
    return json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    if "--verifier" in sys.argv:
        ok = FICHIER.is_file() and FICHIER.read_text(encoding="utf-8") == texte()
        print("vecteurs du mode classe à jour" if ok else "donnees/classe/vecteurs.json n'est plus à jour : relancer pc/outils/vecteurs_classe.py")
        sys.exit(0 if ok else 1)
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte(), encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : {len(vecteurs()['codes'])} codes")
