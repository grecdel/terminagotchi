"""Les vecteurs communs de l'accueil et de l'aide (Python ↔ Kotlin) : donnees/accueil/vecteurs.json.

    python3 pc/outils/vecteurs_accueil.py              écrit les vecteurs (depuis pc/tg/aide_douce.py)
    python3 pc/outils/vecteurs_accueil.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les règles pures d'aide_douce.py : la flèche « tape ici » (4), le bouton « Perdu ? » jaune vif (6), la touche à
allumer (5), le premier symbole à expliquer (5, PC), `ls ?` / `? ls` (22), les 3 niveaux d'indice (25), la fin grisée
(66), la fin du tronc commun (9), la durée de la cinématique du premier ls (2), le menu (79). tests/jvm/Accueil.kt
vérifie qu'AideDouce.kt donne EXACTEMENT les mêmes réponses.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import aide_douce as A  # noqa: E402

FICHIER = RACINE / "donnees" / "accueil" / "vecteurs.json"

ATTENDUS = ["pwd", "ls", "ls sac | wc -l", "echo pomme > nid/repas.txt", "echo poire >> nid/repas.txt", "cd ~",
            "cd ~/terrain_terminagotchi/nid", "ls -a", "cat *.txt", "echo \"bonjour\"", "echo 'a'", "echo $HOME",
            "sleep 5 &", "mv vieux_nom.txt nouveau_nom.txt", "x=3", "grep -c pomme liste.txt", "cd ..", ""]
TAPES = ["", "l", "ls", "ls ", "ls sac ", "ls sac |", "ls sac | wc", "echo pomme ", "echo pomme >", "echo poire >",
         "cd", "cd ", "xyz", "echo \"", "cat ", "sleep 5 "]
LIGNES = ["ls ?", "? ls", "  ls   ?  ", "?ls", "ls?", "ls -a ?", "? ", "?", "cd ?", "? cd", "explique ls", "wc ?",
          "python3 ?", "? python3", "LS ?", "ls ? ?", "", "echo ?"]


def vecteurs():
    v = {"note": "pc/outils/vecteurs_accueil.py (règles d'aide_douce.py = AideDouce.kt)"}
    v["fleche"] = [{"intro": i, "reussies": r, "depuis": d, "ok": A.fleche(i, r, d)}
                   for i in (True, False) for r in (0, 2, 3, 7) for d in (0, 30, 59.9, 60, 300)]
    v["vif"] = [{"erreurs": e, "depuis": d, "ok": A.perdu_vif(e, d)} for e in (0, 1, 2, 5) for d in (0, 119, 120, 600)]
    v["touche"] = [{"attendu": a, "tape": t_, "touche": A.touche_a_allumer(a, t_)} for a in ATTENDUS for t_ in TAPES]
    v["symbole"] = [{"attendu": a, "vus": vus, "symbole": A.symbole_nouveau(a, vus)} for a in ATTENDUS
                    for vus in ([], ["|"], [">", "~"], [">>", "|", "~", ">", "*", "/", "$", "&", "\"", "'", "_"])]
    v["explique"] = [{"ligne": l, "nom": A.demande_explique(l)} for l in LIGNES]
    v["indice"] = [{"attendu": a, **A.parties_indice(a)} for a in ATTENDUS + ["  ls   -l  -a  nid ", "rm -r -f x", "-a"]]
    noms = ["nid/", "vestibule/", "reserve.txt", "vieux_nom.txt", "vieux_nid/", "grenier/", "LISEZMOI.txt", "ls",
            "lsblk", "less", "nid"]
    v["fantome"] = [{"mot": m, "candidats": c, "fin": A.fantome(m, c)}
                    for m in ("", "n", "ni", "nid", "nid/", "v", "ve", "vest", "vi", "r", "x", "l", "ls", "le", "L")
                    for c in (noms, [x for x in noms if x.startswith("v")], [])]
    tronc = {"note": "…", "n0": ["reveil"], "n1": ["reveil"], "n2": ["nid"], "n3": ["bibliotheque"],
             "n4": ["nid", "bibliotheque"], "n5": [], "n6": ["cave"]}
    v["tronc"] = [{"ailes": a, "tronc": tr, "fini": A.tronc_fini(a, tr)}
                  for a in ([], ["reveil", "nid"], ["reveil", "nid", "bibliotheque", "cave"],
                            ["cave", "bibliotheque", "nid", "reveil", "grenier"])
                  for tr in (tronc, {}, {"n0": []})]
    v["duree_ls"] = [{"camp": c, "s": A.duree_ls(c)} for c in (True, False)]
    v["menu"] = [{"r": r, "action": A.action_menu(r)} for r in ("", "1", "2", "3", "4", "5", "q", "Q", "0", "6", " 2 ", "x")]
    v["rangees"] = {"r1": A.RANGEE1, "r2": A.RANGEE2, "s1": A.SYMBOLES1, "s2": A.SYMBOLES2, "ordre": A.ORDRE_SYMBOLES}
    return v


def texte():
    return json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    if "--verifier" in sys.argv:
        ok = FICHIER.is_file() and FICHIER.read_text(encoding="utf-8") == texte()
        print("vecteurs de l'accueil à jour" if ok else "donnees/accueil/vecteurs.json n'est plus à jour : relancer pc/outils/vecteurs_accueil.py")
        sys.exit(0 if ok else 1)
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte(), encoding="utf-8")
    v = vecteurs()
    print(f"{FICHIER.relative_to(RACINE)} : {sum(len(x) for x in v.values() if isinstance(x, list))} vecteurs")
