"""Les vecteurs communs de la Citadelle (Python ↔ Kotlin) : donnees/citadelle/vecteurs.json.

    python3 pc/outils/vecteurs_citadelle.py              écrit les vecteurs (depuis pc/tg/citadelle.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_citadelle.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Le journal du gardien, chmod (octal et lettres) et umask, les drapeaux des boîtes, le faux facteur mélangé, l'entropie
des phrases de passe, l'inspecteur des boîtes, le tableau de garde et les cadenas de la vue déployée :
tests/jvm/Citadelle.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import citadelle as C, deploie, langue  # noqa: E402

FICHIER = RACINE / "donnees" / "citadelle" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    specs = ["600", "755", "0644", "7", "u+x", "go-r", "o-rwx", "a=r", "u+x,g-w", "+x", "-x", "+w", "g=rw", "a+w", "o-w",
             "ug+rw", "u=rwx,go=", "=r", "u+s", "abc"]
    departs = [0o644, 0o755, 0o600, 0o777, 0o000]
    chmod = [{"spec": s, "depart": d, "masque": m, "mode": C.chmod_mode(s, d, m)}
             for s in specs for d in departs for m in (0o022, 0o077)]
    umask = [{"masque": m, "fichier": C.umask_mode(m), "dossier": C.umask_mode(m, True)}
             for m in (0o000, 0o002, 0o022, 0o027, 0o077, 0o777)]
    graines = ["1:0", "2:1730000000", "7:42", "partie:3"]
    drapeaux = [{"graine": g, "boite": b, "genre": k, "drapeau": C.drapeau(g, b, k)}
                for g in graines for b in ("enumeration", "droits", "secrets") for k in ("entree", "donjon")]
    facteur = [{"graine": g, "ordre": [[n, i, v] for n, i, v in C.facteur(g)], "bons": C.bons_indices(g)} for g in graines]
    force = [{"id": f["id"], "bits": round(C.bits(f), 6), "duree": C.duree_essais(C.bits(f))} for f in C.donnees()["force"]]
    insp = []
    for b in C.donnees()["boites"]:
        chemins = [r["chemin"] for r in b["rempart"] if r.get("chemin")]
        for modes in ({c: 0o644 for c in chemins}, {c: 0o640 for c in chemins}, {c: 0o600 for c in chemins},
                      {c: 0o757 for c in chemins}, {c: None for c in chemins}, {c: 0o750 for c in chemins}):
            for rot in (False, True):
                insp.append({"boite": b["id"], "modes": modes, "rotation": rot,
                             "regles": [[r, o] for r, o in C.inspecter(b, modes, rot)]})
    lignes = ["chmod 600 coffre.txt", "chmod u+x ronde.sh", "chmod -x cadeau.sh", "chmod o-rwx boites/droits/*",
              "(umask 077; touch carnet_secret.txt)", "umask 022", "chmod -R u+x,g-w a b", "chmod 755", "ls -l",
              "ls -l | grep x && chmod go-r f", "chmod --verbose a=r x.txt", "chmod u+s f", "umask"]
    droits = [{"ligne": l, "droits": [{k: x[k] for k in ("seg", "cmd", "mode", "fichier", "avant", "apres", "octal", "suppose")}
                                      for x in deploie.droits(l)]} for l in lignes]
    tableau = [{"g": g, "p": p, "s": s, "t": [list(x) for x in C.tableau(g, p, s)]} for g in (0, 2) for p in (0, 1) for s in (0, 1)]
    return {"note": "généré par pc/outils/vecteurs_citadelle.py ; vérifié par tests/jvm/Citadelle.kt",
            "journal": C.journal(), "echecs": C.echecs(), "chmod": chmod, "umask": umask, "drapeaux": drapeaux,
            "facteur": facteur, "force": force, "inspecteur": insp, "droits": droits, "tableau": tableau,
            "mots": C.mots()}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/citadelle/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_citadelle.py")
            sys.exit(1)
        print("vecteurs de la Citadelle à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
