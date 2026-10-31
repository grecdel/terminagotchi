"""Test de l'effet glitch côté PC (pc/tg/glitch.py, le tirage du glitch, les gardiens de la Citadelle).

    python3 pc/outils/test_glitch.py

  1. l'effet sur l'image : donnees/glitch/vecteurs.json à jour (mêmes vecteurs que Kotlin et JavaScript) ;
  2. le tirage du glitch (à part : compteur + 2^20) : vecteurs, taux (1 sur 4096 ; 1 sur 8 pour un gardien), et les
     tirages déjà enregistrés ne changent pas ;
  3. les gardiens : 8 boîtes, 8 espèces différentes des familles d'affinité Ombre et Poison ; maîtriser une boîte rend
     son gardien rencontrable glitch (faveur « gardien ») ; les 4 variantes Démons au tirage normal ; une apparition
     avec graine déclare « gardien » et décide le glitch (le serveur refait le même tirage) ;
  4. l'image dans toutes les sorties du terminal (Kitty, iTerm2, sixel, quadrants, demi-blocs), le bureau et l'île :
     l'effet se pose sur chaque image (respiration, animations, poses), éclair C selon l'horloge, shiny d'abord ;
  5. le nom : le repère ▚ tient en 1 colonne (langue.largeur), comme le ✨ du shiny en tient 2.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp()
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
from tg import bestiaire as B  # noqa: E402
from tg import glitch as G  # noqa: E402
from tg import guide, langue, recompenses, tirage as T  # noqa: E402

ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


langue.definir("fr")
print("1. L'effet sur l'image")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_glitch.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "donnees/glitch/vecteurs.json à jour " + r.stdout.strip())
V = json.loads((RACINE / "donnees/glitch/vecteurs.json").read_text(encoding="utf-8"))
verifier(all(str(G.fnv(x["texte"])) == x["h"] for x in V["fnv"]), "fnv1a-64")
carre = [int(x, 16) for x in V["images"]["carre"]["px"]]
ex = V["exemple"]
verifier(["%08x" % p for p in G.appliquer(9, 7, carre, ex["graine"], ex["style"], ex["phase"])] == ex["px"], "l'exemple pixel par pixel")
verifier(G.appliquer(9, 7, carre, "x", "A") == G.appliquer(9, 7, carre, "x", "A"), "déterministe")
verifier(G.appliquer(9, 7, carre, "x", "A") != G.appliquer(9, 7, carre, "y", "A"), "chaque individu a le sien (la graine)")
c = sum(G.etat("a1b2c3d4e5", t)[0] == "C" for t in range(0, 60000, 10))
verifier(200 <= c <= 800, f"un éclair de temps en temps : {c * 10} ms de style C par minute (≈ 4 %)")
eclairs = [t for t in range(0, 20000, 10) if G.etat("a1b2c3d4e5", t)[0] == "C"]
debuts = [t for t in eclairs if t - 10 not in eclairs]
verifier(len(debuts) >= 3 and all(3000 <= b - a <= 5500 for a, b in zip(debuts, debuts[1:])),
         f"toutes les 3 à 5,5 secondes : {debuts}")
plein = [p for p in carre if p >> 24]
verifier(len([p for p in G.appliquer(9, 7, carre, "x", "A") if p >> 24]) > len(plein), "le style A ajoute le liseré rose / cyan")

print("2. Le tirage du glitch")
AT = json.loads((RACINE / "donnees/anti_triche/vecteurs.json").read_text(encoding="utf-8"))
verifier(all(T.glitch(x["valeur"], x["n"], x["gardien"]) == x["glitch"] for x in AT["glitchs"]), f"{len(AT['glitchs'])} vecteurs")
verifier(all(T.tirer(x["valeur"], x["n"], x["abyssor"], x.get("attire"))[1] == x["attendu"] for x in AT["tirages"]),
         "les tirages déjà enregistrés ne changent pas (le glitch se tire à part)")
g0 = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"
n1 = sum(T.glitch(g0, n) for n in range(100000))
n8 = sum(T.glitch(g0, n, True) for n in range(8000))
verifier(10 <= n1 <= 45, f"partout : {n1} sur 100 000 (1 chance sur {T.CHANCE_GLITCH})")
verifier(850 <= n8 <= 1150, f"gardien d'une boîte maîtrisée : {n8} sur 8000 (1 chance sur {T.CHANCE_GLITCH_GARDIEN})")
verifier(T.CHANCE_GLITCH >= 4096 and B.donnees()["chance_shiny"] * T.CHANCE_GLITCH >= 400000,
         f"shiny + glitch : 1 chance sur {B.donnees()['chance_shiny'] * T.CHANCE_GLITCH}")
js = (RACINE / "site/src/tirage_donnees.js").read_text(encoding="utf-8")
verifier('"chance_glitch":4096' in js and '"enumeration":"Ricanombre"' in js and '"hangar"' not in js,
         "le serveur connaît les chances et les gardiens des boîtes codées seulement")

print("3. Les gardiens des boîtes de la Citadelle")
gd = recompenses.gardiens()
cit = json.loads((RACINE / "pc/tg/citadelle.json").read_text(encoding="utf-8"))
verifier(set(gd) == {b["id"] for b in cit["boites"]} | set(cit["a_venir"]) and len(set(gd.values())) == 8,
         f"8 boîtes, 8 gardiens différents : {gd}")
verifier(all(guide.type_de(B.espece(x), "classique") in ("ombre", "poison") for x in gd.values()),
         "tous des familles d'affinité Ombre et Poison")
verifier(not any(m.get("variantes_reservees") for m in recompenses.mondes() if m["id"] == "citadelle"),
         "les 4 variantes Démons retournent au tirage normal")
st = {}
verifier(recompenses.gardien_de(st, {"id": "ricanombre"}) is None, "avant la boîte : pas de gardien")
msg = recompenses.exploit(st, "citadelle.boite")
verifier(msg and "Ricanombre" in msg and recompenses.faveur(st)["reste"] == 5, f"boîte maîtrisée : {msg}")
verifier(recompenses.gardien_de(st, {"id": "ricanombre"}) == "enumeration"
         and recompenses.gardien_de(st, {"id": "heaumbre"}) is None, "son gardien (et pas celui d'une autre boîte)")
# une apparition favorisée : la première gardienne parmi les compteurs essayés, tirage exact (vérifiable)
st2 = {"compte": {"graines": {T.jour_local() + ".abcdefabcdef": g0}}}
recompenses.exploit(st2, "citadelle.boite")
vus = []
for _ in range(10):
    premiere = T.apparition(st2, lambda e, v: "")
    (e, ind), _t = recompenses.apparition(st2, premiere, lambda: T.apparition(st2, lambda e, v: ""))
    recompenses.marquer_glitch(st2, e, ind)
    vus.append((e["id"], ind.get("gardien"), ind.get("glitch", False), ind["n"]))
    verifier(T.tirer(g0, ind["n"])[1]["espece"] == ind["espece"], f"apparition #{ind['n']} : un tirage exact ({ind['espece']})") \
        if len(vus) <= 2 else None
verifier(any(x[0] == "ricanombre" for x in vus), f"la faveur fait venir Ricanombre plus souvent : {[x[0] for x in vus]}")
verifier(all((x[1] == "enumeration") == (x[0] == "ricanombre") for x in vus), "seul le gardien déclare « gardien »")
verifier(all(x[2] == T.glitch(g0, x[3], x[1] is not None) for x in vus), "le glitch : celui que le serveur refera")
n, m_ = 0, 0
for _ in range(1600):
    ind = {"espece": "Ricanombre"}
    n += bool(recompenses.marquer_glitch(st, {"id": "ricanombre"}, ind))
    m_ += bool(recompenses.marquer_glitch(st, {"id": "braisillon"}, {"espece": "Braisillon"}))
verifier(130 <= n <= 280 and m_ <= 4, f"sans graine aussi : gardien {n}/1600 (≈ 200), ailleurs {m_}/1600")

print("4. L'image dans toutes les sorties")
from tg import equipe, poses  # noqa: E402
ind = {"id": "a1b2c3d4e5", "espece": "Ombrachne", "variante": "classique", "stade": "adulte", "glitch": True,
       "rarete": "rare"}
normal = dict(ind, glitch=False)
for mode in ("kitty", "iterm", "sixel", "quadrants", "demi"):
    os.environ["TG_IMAGES"] = mode
    for quoi in ("statique", "mange"):
        fg, _ = equipe.animation(ind, quoi, aura=True, fin=True)
        fn, _ = equipe.animation(normal, quoi, aura=True, fin=True)
        a = fg[2]
        etat0 = G.etat
        G.etat = lambda g, t=None: ("C", 3)
        try:
            cc = fg[2]
        finally:
            G.etat = etat0
        verifier(len(fg) == len(fn) and a != fn[2] and cc != a, f"{mode} · {quoi} : {len(fg)} images, glitch A ≠ normal, éclair C ≠ A")
os.environ.pop("TG_IMAGES")
d0 = B.dessin(B.espece("Ombrachne"), stade="adulte")
d1 = B.dessin(B.espece("Ombrachne"), stade="adulte", glitch="a1b2c3d4e5")
d2 = B.dessin(B.espece("Ombrachne"), True, stade="adulte", glitch="a1b2c3d4e5")
verifier(d0 != d1 and d1 != d2, "une image fixe (carte, face-à-face) : style A, et shiny + glitch")
al = poses.album_espece("ombrachne", "adulte", False, "a1b2c3d4e5")
al0 = poses.album_espece("ombrachne", "adulte", False)
c1, c0 = al.image("assis", 0), al0.image("assis", 0)
verifier(c1.w == c0.w + 4 and c1.ax == c0.ax + 2 and c1.rgba != c0.rgba, "bureau et île : l'effet sur chaque pose")
alb = poses.album_espece("braisillon", "bebe", True, "ff00")
verifier(alb.image("marche", 1).cle.endswith("A0") and alb.image("marche", 1).w == alb.images("marche")[1].w + 4,
         "les poses dessinées d'un bébé aussi (shiny + glitch)")

print("5. Le nom")
nom = B.nom_affiche(B.espece("Ombrachne"), False, "rare", True)
verifier(langue.largeur(G.REPERE) == 1 and langue.largeur(nom) == langue.largeur("Ombrachne ▚") == 11,
         "le repère ▚ tient en 1 colonne (le ✨ du shiny : 2)")
verifier(langue.largeur(B.nom_affiche(B.espece("Ombrachne"), True, None, True)) == len("Ombrachne") + 3 + 2,
         "shiny + glitch : « Ombrachne ✨ ▚ »")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
