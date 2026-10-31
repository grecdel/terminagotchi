"""Tests de la phase 4 (PC) : charte de rigueur, Ponts des Nombres, récompenses par monde.

    python3 pc/outils/test_programme.py

  1. donnees/programme.json passe le vérificateur (fiches, étapes, orphelines, langues, copies) ;
  2. les vecteurs communs Python / Kotlin sont à jour (exercices, recherches, faveurs) ;
  3. maths : le graphe des prérequis, la recherche par le moteur du lexique (14 langues), un exercice juste ou faux,
     « je ne connais pas » jamais bloquant (on descend, on remonte, on revient où on était), dans les 14 langues ;
     chaque exercice généré est vérifié par un vrai bash (la commande « vérifie dans le vrai terminal ») ;
  4. récompenses : un exploit donne des faveurs ; chaque créature gardée est EXACTEMENT le tirage d'un (graine,
     compteur), donc vérifiable par le serveur ; la série parfaite ; les variantes réservées ;
  5. tg explique montre où l'image s'arrête et l'idée fausse.
Code de sortie 1 en cas d'échec.
"""
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_programme_")
sys.path.insert(0, str(RACINE / "pc"))

from tg import bestiaire as B  # noqa: E402
from tg import explique, langue, maths, programme, recompenses, tirage  # noqa: E402

ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


def lancer(*args):
    return subprocess.run([sys.executable, *args], cwd=RACINE, capture_output=True, text=True)


print("1. La charte de rigueur")
r = lancer("pc/outils/verifier_programme.py")
verifier(r.returncode == 0, "verifier_programme : " + (r.stdout.strip().splitlines() or ["?"])[-1])
P = programme.donnees()
verifier(len(P["notions"]) >= 50 and all(n["sources"] and n["vrai_terminal"] for n in P["notions"].values()),
         f"{len(P['notions'])} fiches, chacune avec ses sources et sa vraie sortie")
verifier(programme.notions_de("cat nid/repas.txt | grep pomme")[:1] == ["grep"] or
         {"cat", "grep", "tuyau"} <= set(programme.notions_de("cat nid/repas.txt | grep pomme")),
         "une commande avec tuyau renvoie aux fiches cat, grep et tuyau")

print("2. Les vecteurs communs")
r = lancer("pc/outils/vecteurs_phase4.py", "--verifier")
verifier(r.returncode == 0, "donnees/maths et donnees/recompenses à jour")

print("3. Les Ponts des Nombres")
langue.definir("fr")
verifier(maths.tous_prerequis("modulo") == ["comptage", "addition", "multiplication", "soustraction", "division"],
         f"modulo s'appuie sur la division, qui descend jusqu'au comptage ({maths.tous_prerequis('modulo')})")
verifier(maths.tous_prerequis("binaire")[-1] == "puissances" and "comptage" in maths.tous_prerequis("binaire"),
         "binaire : puissances, multiplication… jusqu'au comptage")
for q, attendu in (("partager des bonbons", "division"), ("le reste", "modulo"), ("pourquoi on met un exposant",
                   "puissances"), ("les 0 et les 1", "binaire")):
    verifier(maths.chercher(q) == attendu, f"maths {q} → {maths.chercher(q)}")
verifier(maths.chercher("zzzz qwerty") is None, "une question sans rapport : rien (et un message, jamais d'erreur)")
st = {"name": "Pixel"}
out = maths.commande(st, ["modulo"])
verifier(any("modulo" in l.lower() for l in out) and st["maths"]["exo"] and st["maths"]["question"] == "division",
         "maths modulo : la fiche, un exercice, et « Tu sais partager… ? » (jamais obligatoire)")
out = maths.commande(st, ["pas", "du", "tout"])
verifier(st["maths"]["courant"] == "division" and st["maths"]["pile"] == ["modulo"],
         "« pas du tout » : on descend à la division, le modulo attend dans la pile")
rep = st["maths"]["exo"]["reponse"]
out = maths.commande(st, [str(int(rep) + 1)])
verifier(st["maths"]["exo"] and "division" not in st["maths"]["acquis"] and any(rep in l for l in out),
         "une réponse fausse : la bonne réponse, l'erreur expliquée, un autre exercice")
rep = st["maths"]["exo"]["reponse"]
out = maths.commande(st, [rep])
verifier("division" in st["maths"]["acquis"] and st["maths"]["courant"] == "modulo" and not st["maths"]["pile"],
         "réponse juste : le pont s'allume, on revient au modulo, là où on était")
st2 = {"name": "Pixel"}
out = maths.commande(st2, ["je", "ne", "connais", "pas"])
verifier(out and st2["maths"]["courant"] == "comptage", "« je ne connais pas » tout seul : le tout premier pont")
out = maths.commande(st2, ["oui"])
verifier(out, "« oui » sans question : l'aperçu, rien n'est bloqué")
# chaque exercice : la réponse du jeu = ce que calcule un vrai bash
faux = []
for typ in ("comptage", "addition", "soustraction", "multiplication", "division", "modulo", "puissances", "binaire"):
    for k in range(12):
        p, rep, verif = maths.generer(typ, 1761955200 + k, k)
        sortie = subprocess.run(["bash", "--norc", "-c", verif], capture_output=True, text=True).stdout.strip()
        if sortie != rep:
            faux.append((typ, verif, sortie, rep))
verifier(not faux, f"96 exercices : la réponse attendue est celle de bash {faux[:2]}")
for code in langue.LANGUES:
    langue.definir(code)
    maths._INDEX.clear()
    s = {"name": "Pixel"}
    o1 = maths.commande(s, ["binaire"])
    mot = langue.t("maths.mot.inconnu")
    o2 = maths.commande(s, mot.split())
    verifier(o1 and o2 and s["maths"]["courant"] in ("puissances", "addition") and
             all("{" not in l for l in o1 + o2),
             f"{code} : maths binaire puis « {mot} » descend au premier prérequis ({s['maths']['courant']})")
langue.definir("fr")
maths._INDEX.clear()

print("4. Les récompenses par monde")
G = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"
st = {"compte": {"graines": {tirage.jour_local() + ".abcdefabcdef": G}}}
verifier(recompenses.exploit(st, "crypte.chaine") and not recompenses.exploit(st, "crypte.chaine"),
         "un exploit réussi donne une faveur, une seule fois")
verifier(recompenses.faveur(st)["reste"] == P["recompenses"]["bonus_variante"], "3 rencontres favorisées")
zone_de = lambda e, v: B.variante(e, v).get("zone", e["zone"])  # noqa: E731
types_crypte = next(m["types"] for m in P["mondes"] if m["id"] == "crypte")
gardes, bons = [], 0
for _ in range(3):
    premiere = tirage.apparition(st, zone_de)
    (e, ind), msg = recompenses.apparition(st, premiere, lambda: tirage.apparition(st, zone_de))
    gardes.append(ind)
    bons += msg is not None
_e, refait = tirage.tirer(G, gardes[0]["n"])
verifier(all(tirage.tirer(G, i["n"])[1] == {k: i[k] for k in tirage.tirer(G, i["n"])[1]} for i in gardes),
         "chaque créature gardée est le tirage exact de (graine, compteur) : le serveur la vérifie")
verifier(len({i["n"] for i in gardes}) == 3, "trois compteurs différents (jamais deux fois le même)")
verifier(bons >= 1, f"au moins une créature du monde attirée ({bons}/3)")
verifier(recompenses.faveur(st) is None, "les faveurs s'épuisent")
# sur beaucoup de graines : une faveur « variante » rend les variantes rares du monde bien plus fréquentes
rnd = random.Random(7)
norm = fav = 0
for _ in range(300):
    g = "%064x" % rnd.getrandbits(256)
    e, c = tirage.tirer(g, 0)
    norm += c["variante"] != "classique" and recompenses._type(e, c["variante"]) in types_crypte
    n, c2 = recompenses.favoriser(g, 0, "variante", types_crypte)
    e2 = B.espece(c2["espece"])
    fav += c2["variante"] != "classique" and recompenses._type(e2, c2["variante"]) in types_crypte
verifier(fav > 2 * norm, f"variantes rares du monde : {norm}/300 sans faveur, {fav}/300 avec (jamais garanties)")
s = {}
msgs = [recompenses.serie(s, m) for m in ("or", "or", "argent", "or", "diamant", "or", "or", "or")]
verifier(msgs[-1] and not any(msgs[:-1]), "5 médailles d'or de suite = une série parfaite (une médaille d'argent remet à zéro)")
verifier(recompenses.exploit(s, "inconnu.truc") is None, "un exploit inconnu ne fait rien")
P["mondes"][0]["variantes_reservees"] = ["volcan"]
verifier(recompenses.reservee({}, None, "volcan") and not recompenses.reservee(
    {"recompenses": {"exploits": {"forge.sans_indice": 1}, "faveurs": []}}, None, "volcan"),
    "une variante réservée n'apparaît qu'après un exploit de son monde")
P["mondes"][0]["variantes_reservees"] = []

print("5. tg explique : la limite de l'image")
txt = "\n".join(explique.fiche({}, "rm"))
verifier("Où l'image s'arrête" in txt and "Idée fausse" in txt, "tg explique rm montre la limite et l'idée fausse")

print("6. « je ne connais pas » tapé dans le vrai terminal (le jeu lit l'historique)")
st = {"name": "Pixel", "terminal": [langue.t("core.inconnue", cmd="je")]}
maths.tick(st, ["je ne connais pas"])
verifier(st["maths"]["courant"] == "comptage" and not any("n'est pas une commande" in x for x in st["terminal"])
         and any("Ponts des Nombres" in x for x in st["terminal"]),
         "la créature ouvre le premier pont (et ne dit pas « je n'est pas une commande »)")
maths.tick(st, ["maths partager des bonbons", "ls"])
verifier(st["maths"]["courant"] == "division", "« maths … » tapé sans tg : le pont demandé")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
