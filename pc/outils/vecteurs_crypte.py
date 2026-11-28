"""Les vecteurs communs de la Crypte des Codes (Python ↔ Kotlin) : donnees/crypte/vecteurs.json.

    python3 pc/outils/vecteurs_crypte.py              écrit les vecteurs (depuis pc/tg/crypte.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_crypte.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

César et ROT13, les fréquences, le décalage secret de chaque partie, la roue lue dans `tr`, les messages cachés de K1,
l'avalanche, la base fictive et l'attaque par dictionnaire, SHA-crypt (openssl passwd -6), les peintures, le dé pipé,
le quiz mélangé, la chaîne et sa vérification, le biome tricheur, la preuve de travail, la roue de la vue déployée :
tests/jvm/Crypte.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import crypte as K, deploie, langue  # noqa: E402

FICHIER = RACINE / "donnees" / "crypte" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000"]
    textes = ["bonjour", "le sphinx de givre, 2026 !", "Zèbre & œuf", "abcdefghijklmnopqrstuvwxyz"]
    cesar = [{"texte": x, "k": k, "code": K.cesar(K.ascii_bas(x), k), "ascii": K.ascii_bas(x)} for x in textes for k in (1, 3, 13, 25)]
    tr = [["a-z", "d-za-c"], ["d-za-c", "a-z"], ["a-z", "n-za-m"], ["a-zA-Z", "n-za-mN-ZA-M"], ["'a-z'", "'b-za'"], ["a-z", "A-Z"],
          ["abc", "def"], ["a-z", "z-a"], ["0-9", "1-90"], ["a-y", "b-z"]]
    roue = [{"de": a, "vers": b, "k": K.rotation(a, b)} for a, b in tr]
    freq = [{"texte": x, "f": [[n, l] for n, l in K.frequences(x)]} for x in ("eeeab", "le sphinx garde la crypte", "zzyyx")]
    dec = [{"graine": g, "k": K.decalage(g), "tricheur": K.tricheur(g), "de": K.de_suite(g, 6),
            "quiz": [[n, i, r] for n, i, r in K.quiz(g)]} for g in graines]
    messages = [{"n": x["n"], "texte": langue.t(f"cr.msg.{x['n']}"), "code": K.message_code(x["n"], langue.t(f"cr.msg.{x['n']}"))}
                for x in K.donnees()["messages"]]
    av = [{"a": a, "b": b, "lettres": K.lettres_differentes(K.sha(a), K.sha(b)), "bits": K.bits_differents(K.sha(a), K.sha(b))}
          for a, b in (("chat", "chas"), ("a", "b"), ("bonjour", "Bonjour"))]
    lignes = ["début", "Pixel donne 3 glands à Noisette", "Noisette donne 1 plume à Lune"]
    ch = K.chaine(lignes)
    blocs = [ch[f"bloc_{k}.txt"] for k in range(3)]
    casse = [blocs[0] + "x\n", blocs[1], blocs[2]]
    verif = [{"blocs": b, "etats": [[k, e] for k, e in K.verifier_chaine(b)]} for b in (blocs, casse, [blocs[0], blocs[2]])]
    mine = [{"donnees": d, "zeros": z, "nonce": K.miner(d, z)} for d in ("bloc5", "crypte-bloc-5") for z in (1, 2, 3)]
    crypt = [{"mot": m, "sel": s, "hache": K.sha512crypt(m, s)} for m, s in
             (("licorne", "abcdefgh"), ("soleil", "sel2026"), ("plumange-braisillon-givrarde-empyria", "0123456789abcdefXYZ"), ("", "x"))]
    lignes_dep = ["echo bonjour | tr 'a-z' 'd-za-c'", "tr 'd-za-c' 'a-z' < grimoire/cesar.txt", "tr a-z n-za-m < x | tr n-za-m a-z",
                  "tr 'a-z' 'A-Z'", "cat f | tr -d x", "ls"]
    dep = [{"ligne": l, "roues": [{k: x[k] for k in ("seg", "de", "vers", "decalage")} for x in deploie.roue(l)]} for l in lignes_dep]
    return {"note": "généré par pc/outils/vecteurs_crypte.py ; vérifié par tests/jvm/Crypte.kt",
            "cesar": cesar, "rotation": roue, "frequences": freq, "graines": dec, "messages": messages, "avalanche": av,
            "base": K.base_fictive(), "dico": [[n, m] for n, m in K.trouves_par_dico()], "peintures": K.peintures(),
            "chaine": {"lignes": lignes, "blocs": blocs}, "verifier": verif, "mine": mine, "sha512crypt": crypt,
            "roue_deploie": dep}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/crypte/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_crypte.py")
            sys.exit(1)
        print("vecteurs de la Crypte à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
