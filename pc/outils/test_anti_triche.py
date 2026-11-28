"""Test de l'anti-triche côté PC (tirages par graine).

    python3 pc/outils/test_anti_triche.py          (ajouter --rapide pour 20 000 tirages au lieu de 100 000)

  - les tirages refont exactement donnees/anti_triche/vecteurs.json (mêmes vecteurs que Kotlin et JS) ;
  - site/src/tirage_donnees.js est à jour avec le bestiaire du jeu ;
  - la distribution des raretés et des shiny reste celle d'avant (≈ 55/27/12/5/1 %, shiny 1 %) ;
  - une apparition utilise la graine du jour et son compteur ; sans graine, on retombe sur l'ancien tirage ;
  - les anciennes sauvegardes (captures sans graine) restent lisibles.
"""
import collections
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp()
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "donnees" / "anti_triche"))
from tg import bestiaire as B  # noqa: E402
from tg import tirage as T  # noqa: E402

ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


print("Vecteurs communs")
V = json.loads((RACINE / "donnees/anti_triche/vecteurs.json").read_text(encoding="utf-8"))
for s in V["splitmix"]:
    h = T.Hasard(s["valeur"], s["n"])
    verifier([str(h.suivant()) for _ in s["sorties"]] == s["sorties"], f"splitmix64 {s['valeur'][:16]}…")
pareils = sum(1 for t in V["tirages"] if T.tirer(t["valeur"], t["n"], t["abyssor"], t.get("attire"))[1] == t["attendu"])
verifier(pareils == len(V["tirages"]), f"{pareils}/{len(V['tirages'])} tirages identiques")

import generer  # noqa: E402
js = (RACINE / "site/src/tirage_donnees.js").read_text(encoding="utf-8")
attendu = json.loads(js.split("export default ", 1)[1].rstrip().rstrip(";"))
verifier(attendu == generer.donnees_site(), "site/src/tirage_donnees.js à jour (sinon : python3 donnees/anti_triche/generer.py)")
verifier(generer.vecteurs() == V, "vecteurs.json à jour")

print("Distribution avant / après")
N = 20000 if "--rapide" in sys.argv else 100000
rnd = random.Random(7)
random.seed(7)
avant, apres = collections.Counter(), collections.Counter()
for i in range(N):
    e, sh, v = B.tirer(rnd)
    avant[B.rarete(e, v, rnd.random(), sh)] += 1
    avant["shiny"] += sh
    _, c = T.tirer("%064x" % rnd.getrandbits(256), i % T.MAX_APPARITIONS)
    apres[c["rarete"]] += 1
    apres["shiny"] += c["shiny"]
print(f"     {'':12s} {'avant':>7s} {'après':>7s}   ({N} tirages)")
for r in list(B.COULEUR_RARETE)[:5] + ["shiny"]:
    a, b = 100 * avant[r] / N, 100 * apres[r] / N
    print(f"     {r:12s} {a:6.2f}% {b:6.2f}%")
    tol = 1.0 if a > 10 else 0.4
    verifier(abs(a - b) < tol, f"{r} : écart {abs(a - b):.2f} point(s) < {tol}")

print("Attirance : la commande d'une famille la fait venir plus souvent")
fams = B.familles()
verifier(len(fams) == 10 and fams.get("Démons") == "chmod", "10 familles, une commande chacune (Démons : chmod)")
M = 5000 if "--rapide" in sys.argv else 20000
rnd = random.Random(11)
for fam in ("Démons", "Sylvestres", "Célestes"):
    sans = avec = memes = 0
    for i in range(M):
        g = "%064x" % rnd.getrandbits(256)
        _, a = T.tirer(g, i % T.MAX_APPARITIONS)
        e2, b = T.tirer(g, i % T.MAX_APPARITIONS, False, fam)
        sans += B.espece(a["espece"])["famille"] == fam
        avec += e2["famille"] == fam
        memes += (a["shiny"], a["qualite"], a["marque"]) == (b["shiny"], b["qualite"], b["marque"])
    print(f"     {fam:12s} {100 * sans / M:5.1f} % → {100 * avec / M:5.1f} %")
    verifier(avec > 2.5 * sans, f"{fam} : au moins 2,5 fois plus souvent avec l'attirance")
    verifier(memes == M, f"{fam} : shiny, qualité et marque ne changent pas (seule l'espèce est attirée)")

print("Apparitions avec et sans graine")
state = {"captures": [], "collection": {}, "compte": {}}
zone = lambda e, v: B.variante(e, v).get("zone", e["zone"])  # noqa: E731
verifier(T.apparition(state, zone) is None, "pas de graine : pas de tirage vérifiable (l'ancien tirage prend le relais)")
jour = T.jour_local()
vieux = T.jour_local(time.time() - 5 * 86400)
T.ranger_graines(state, [{"id": f"{jour}.abcdef123456", "valeur": "9e3779b97f4a7c15" + "0" * 48},
                         {"id": f"{vieux}.abcdef123456", "valeur": "1" * 64}])
verifier(list(state["compte"]["graines"]) == [f"{jour}.abcdef123456"], "graines rangées, les trop vieilles oubliées")
e1, i1 = T.apparition(state, zone)
e2, i2 = T.apparition(state, zone)
verifier(i1["graine"] == f"{jour}.abcdef123456" and (i1["n"], i2["n"]) == (0, 1), "compteur 0 puis 1 sur la graine du jour")
verifier(T.tirer("9e3779b97f4a7c15" + "0" * 48, 1)[1].items() <= i2.items(), "l'individu contient exactement le tirage")
verifier(i1["id"] != i2["id"] and i1["zone"] == zone(e1, i1["variante"]), "chaque individu garde un identifiant unique et sa zone")
e3, i3 = T.apparition(state, zone, attire="Démons")
verifier(i3.get("attire") == "Démons" and T.tirer("9e3779b97f4a7c15" + "0" * 48, 2, False, "Démons")[1].items() <= i3.items(),
         "apparition attirée : la famille est gardée (« attire ») et le tirage correspond")
verifier("attire" not in i2, "sans attirance : pas de champ « attire »")
state["compte"]["apparitions"][f"{jour}.abcdef123456"] = T.MAX_APPARITIONS
verifier(T.apparition(state, zone) is None, f"au-delà de {T.MAX_APPARITIONS} apparitions par jour : plus de tirage vérifiable")

print("Anciennes sauvegardes")
ancien = {"id": "0123456789", "espece": "Braisillon", "variante": "volcan", "shiny": False, "potentiel": 60}
verifier(B.rarete_de(ancien) in B.COULEUR_RARETE, "une capture sans graine garde une rareté lisible")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
