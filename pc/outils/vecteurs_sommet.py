"""Les vecteurs communs du Sommet (Python ↔ Kotlin) : donnees/sommet/vecteurs.json.

    python3 pc/outils/vecteurs_sommet.py              écrit les vecteurs (depuis pc/tg/sommet.py et deploie.py)
    python3 pc/outils/vecteurs_sommet.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Pour quelques graines de partie : le journal (dans les 14 langues) et ses réponses (lignes datées, dates, alertes),
l'éboulis (chemins, tailles, la plus lourde, les 5 plus lourdes), la mission de la boussole et son lieu, les fragments
et le drapeau du CTF, et les TEXTES EXACTS des scripts du jeu (bash sur PC, sh sur le téléphone) dans les 14 langues ;
le défi du jour (graine, exercices possibles → 3 exercices) ; l'ouverture (mondes au palier 3 pour des parties d'essai) ;
la cordée de la vue déployée. tests/jvm/Sommet.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, sommet as S  # noqa: E402

FICHIER = RACINE / "donnees" / "sommet" / "vecteurs.json"
LANGUES = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]
GRAINES = ["1:1234", "2:1793534400", "7:42", "partie-x:0"]
LIGNES = ["bash -n casse.sh && bash casse.sh", "bash -x boucle.sh", "sh -n casse.sh", "shellcheck fragile.sh",
          "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6", "bash fragile.sh \"carnet de bord.txt\"; echo $?",
          "grep -oE 'fragment1=[a-z]+' ctf/registre.log", "ls -la", "bash ctf/porte.sh -k cairn", "sh bivouac.sh -n 3"]
POSSIBLES = [["exp_chemin", "exp_cle", "bat_pieces", "lec_cat", "det_grep", "plo_tuyau"], ["exp_chemin", "lec_cat"],
             ["exp_chemin", "exp_cle", "bat_pieces", "bat_objets", "dem_mv", "dem_cp", "net_rm", "net_rmdir", "net_rmr", "lec_cat",
              "lec_head", "lec_tail", "det_grep", "det_find", "plo_ecrit", "plo_ajout", "plo_tuyau", "cui_lancer", "cui_ecrire"]]


def vecteurs():
    parties = []
    for g in GRAINES:
        langue.definir("fr")
        cap, pas = S.mission(g)
        p = {"graine": g, "eboulis": {k: list(v) for k, v in S.eboulis(g).items()}, "plus_lourds": S.plus_lourds(g),
             "plus_lourde": S.plus_lourde(g), "total": S.total_eboulis(g), "mission": [cap, pas], "lieu": S.lieu(g, cap, pas),
             "fragments": list(S.fragments(g)), "drapeau": S.drapeau(g), "langues": {}}
        for code in (LANGUES if g == GRAINES[0] else ["fr", "zh"]):      # (toutes les langues pour la 1re partie)
            langue.definir(code)
            p["langues"][code] = {
                "journal": S.journal_texte(g), "lignes_datees": len(S.lignes_datees(g)), "dates": S.dates(g),
                "alertes": S.alertes(g), "alertes_partout": len(S.alertes_partout(g)),
                "boussole": {sh: S.script_boussole(g, sh) for sh in ("bash", "sh")}, "aide_boussole": S.aide_boussole(),
                "ctf": {sh: S.fichiers_ctf(g, sh) for sh in ("bash", "sh")}}
        parties.append(p)
    scripts = {}
    for code in LANGUES:
        langue.definir(code)
        scripts[code] = {sh: {n: S.script(n, sh) for n in S.donnees()["scripts"]} for sh in ("bash", "sh")}
    langue.definir("fr")
    defis = [{"valeur": v, "possibles": ps, "types": S.defi_types(v, ps)}
             for v in ("5a" * 32, "0123456789abcdef" * 4, "f" * 64) for ps in POSSIBLES]
    cordee = [{"ligne": l, "cordees": [{k: x[k] for k in ("seg", "cmd", "outil", "geste", "de", "vers")} for x in deploie.cordees(l)]}
              for l in LIGNES]
    return {"note": "Généré par pc/outils/vecteurs_sommet.py ; vérifié par tests/jvm/Sommet.kt.",
            "parties": parties, "scripts": scripts, "defis": defis, "cordee": cordee}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        ok = FICHIER.exists() and FICHIER.read_text(encoding="utf-8") == texte
        print("vecteurs du Sommet à jour" if ok else "vecteurs du Sommet PAS à jour : python3 pc/outils/vecteurs_sommet.py")
        sys.exit(0 if ok else 1)
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"écrit {FICHIER.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
