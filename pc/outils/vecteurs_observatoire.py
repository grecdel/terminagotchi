"""Les vecteurs communs de l'Observatoire de l'IA (Python ↔ Kotlin) : donnees/observatoire/vecteurs.json.

    python3 pc/outils/vecteurs_observatoire.py              écrit les vecteurs (depuis pc/tg/observatoire.py et deploie.py)
    python3 pc/outils/vecteurs_observatoire.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les jeux de données dans les 14 langues (creatures.txt, exemples.txt, nouvelle.txt, volcan.txt, autres.txt), le
devineur de type (ce qu'il apprend, ce qu'il devine, ses votes), le texte du devineur de mots dans les 14 langues
(nettoyé, mots les plus fréquents, paires, phrases tirées), ce que l'assistant comprend d'une consigne, son tri qui
oublie une ligne, les propositions des agents, les 2 réponses fausses sur 5, les quiz mélangés, la lunette (vue
déployée) : tests/jvm/Observatoire.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, observatoire as O  # noqa: E402

FICHIER = RACINE / "donnees" / "observatoire" / "vecteurs.json"
GRAINES = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123", "5:5", "8:1762000000"]


def vecteurs():
    D = O.donnees()
    langues = {}
    for code in langue.LANGUES:
        langue.definir(code)
        lignes = O.corpus_lignes(code)
        mots = O.mots_de("\n".join(lignes))
        table = O.paires(mots)
        debuts = [w for w, _n in O.effectifs(mots)[:3]]
        m = O.apprendre(O.texte_creatures(D["exemples"]))
        mv = O.apprendre(O.texte_creatures(D["volcan"]))
        langues[code] = {
            "types": O.texte_types(), "exemples": O.texte_creatures(D["exemples"]),
            "nouvelle": O.texte_creatures([D["piege"]], avec_reponse=False), "volcan": O.texte_creatures(D["volcan"]),
            "autres": O.texte_creatures(D["autres"]), "modele": m, "modele_volcan": mv,
            "cerveau": O.cerveau_lignes(m, "exemples.txt"),
            "teste_nouvelle": [list(x) for x in O.tester(m, O.texte_creatures([D["piege"]], avec_reponse=False))],
            "teste_autres_volcan": [list(x) for x in O.tester(mv, O.texte_creatures(D["autres"]))],
            "teste_autres": [list(x) for x in O.tester(m, O.texte_creatures(D["autres"]))],
            "corpus": lignes, "effectifs": [list(x) for x in O.effectifs(mots)[:12]],
            "paires": [[a, b, n] for (a, b), n in O.top_paires(mots)[:12]],
            "suites": {w: [list(x) for x in O.suite(table, w)[:10]] for w in debuts},
            "phrases": [{"debut": w, "graine": g, "n": n, "phrase": O.phrase(table, w, g, n)}
                        for w in debuts[:2] for g in GRAINES[:3] for n in (0, 1)],
            "missions": [{"texte": x, "analyse": O.analyser(x, ["creatures.txt", "mission.txt", "tri.txt"],
                                                             lambda f: list(dict.fromkeys(l.split()[-1] for l in O.texte_types().splitlines())))}
                         for x in (langue.t("ob.mission.floue"), langue.t("ob.mission.tri"), langue.t("ob.mission.exemple"),
                                   "Compte dans creatures.txt", "liste les " + O._mot("ob.type.eau") + " de creatures.txt",
                                   "COMPTE les feu dans creatures.txt !", "trie mission.txt", "")],
            "est_feu": {w: O.est_feu(w) for w in (O.label(True), O.label(False), "Feu", "pas_Feu", "feu", "x", "")},
        }
    langue.definir("fr")
    parties = []
    for g in GRAINES:
        tri, oubliee = O.trier_assistant(O.texte_types().splitlines(), g)
        parties.append({"graine": g, "oubli": O.oubli(g), "tri": tri, "oubliee": oubliee,
                        "agent": [list(x) for x in O.propositions(g)], "equipe": [list(x) for x in O.propositions(g, "equipe")],
                        "dangereuse": O.dangereuse(g), "dangereuse_equipe": O.dangereuse(g, "equipe"),
                        "questions": [list(x) for x in O.questions(g)], "confier": [list(x) for x in O.confier_cartes(g)],
                        "nuances": [list(x) for x in O.nuances_cartes(g)], "perroquet": [list(x) for x in O.perroquet_cartes(g)],
                        "biais": [list(x) for x in O.biais_cartes(g)], "consigne": [list(x) for x in O.consigne_cartes(g)],
                        "decoupe": [list(x) for x in O.decoupe_cartes(g)], "decoupe_reponse": O.decoupe_reponse(g)})
    fausses = [{"graine": g, "rep": r, "res": list(O.fausses_ok(r, g))}
               for g in GRAINES[:3] for r in ([str(n) for n, _i, f in O.questions(g) if f], ["1", "2"], ["5", "4", "3"], ["x"], [])]
    quiz = []
    for g in GRAINES[:3]:
        c = O.confier_cartes(g)
        bon = [r for _n, _i, r in c]
        for rep in (bon, ["C"] * 6, ["garde"] * 6, bon[:5], ["x"] * 6):
            ok, justes = O.quiz_justes(c, rep, "cg")
            quiz.append({"graine": g, "lettres": "cg", "rep": rep, "ok": ok, "justes": [list(j) for j in justes]})
    textes = ["", "Le devineur, la créature ! Et « le » monde…", "C'est l'ordinateur : 3 fois.", "Ta créature 🐣 dort",
              "我的生物在睡觉。", "ターミナルワールドは眠っている", "मेरा जीव सो रहा है।", "مخلوقي نائم", "Мой зверёк спит",
              "{dossier} rien qu'à {nous}", "A\tb\nc—d…e"]
    nettoyage = [{"texte": x, "mots": O.nettoyer(O.sans_champs(x))} for x in textes]
    lignes = ["assistant mission.txt > rapport.txt", "sort creatures.txt | diff - tri.txt && sh test.sh", "wc -l a b",
              "awk '{print $4}' exemples.txt | sort | uniq -c", "grep -c Feu creatures.txt", "devine-type apprends exemples.txt",
              "devine-mot suite le", "agent lance", "ls copies | wc -l", "bash tests.sh", "uniq c", "grep Feu x",
              "tg assistant questions", "echo diff", "cat a; diff a b"]
    lunette = [{"ligne": l, "lunettes": [list(a) for a in O.lunettes_de(l)]} for l in lignes]
    dep = [{"ligne": l, "lunettes": [{"seg": x["seg"], "cmd": x["cmd"], "outil": x["outil"], "de": x["de"], "vers": x["vers"]}
                                     for x in deploie.lunettes(l)]} for l in lignes]
    return {"note": "généré par pc/outils/vecteurs_observatoire.py ; vérifié par tests/jvm/Observatoire.kt",
            "langues": langues, "parties": parties, "fausses": fausses, "quiz": quiz, "nettoyage": nettoyage,
            "liste_rangee": O.liste_rangee(D["agent"]["liste"]), "lunette": lunette, "deploie": dep}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/observatoire/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_observatoire.py")
            sys.exit(1)
        print("vecteurs de l'Observatoire à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
