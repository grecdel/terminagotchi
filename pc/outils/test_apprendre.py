"""Apprendre en jouant (idées du 3 novembre : 21, 23, 24, 27, 29, 30, 41, 42, 43, 44, 45, 46, 49, 50), sur PC.

    python3 pc/outils/test_apprendre.py            (crée son propre HOME temporaire, hors ligne)
    python3 pc/outils/test_apprendre.py --ecrire   réécrit d'abord donnees/apprendre/vecteurs.json (lu aussi par
                                                   tests/jvm/Apprendre.kt : mêmes résultats en Kotlin)

Chaque idée est jouée comme un enfant : les commandes passent dans un VRAI bash (dans le terrain), puis le tour de jeu
(app.boucle_jeu) les voit avec leur code de sortie et le dossier où l'on se trouve.
"""
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_apprendre_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, histoire, langue, recompenses, satiete  # noqa: E402
from tg import apprendre as A  # noqa: E402

VECTEURS = RACINE / "donnees" / "apprendre" / "vecteurs.json"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(c, m):
    global ok, ko
    if c:
        ok += 1
        print("  ✔", m)
    else:
        ko += 1
        print("  ✖", m)


def nu(lignes):
    return ANSI.sub("", "\n".join(lignes) if isinstance(lignes, list) else str(lignes))


# ---------------------------------------------------------------- 1. les vecteurs communs (Kotlin : tests/jvm/Apprendre.kt)
JOURS = ["2026-11-03", "2026-11-04", "2026-12-25", "2027-01-01", "2026-02-28", "2028-02-29"]
CONNUES = [[], ["pwd"], ["pwd", "ls", "cd"], ["pwd", "ls", "cd", "mkdir", "touch", "cp", "mv", "rm", "cat", "grep", "find", "sort"],
           A.cmds()]
SEMAINES = ["2026-W45", "2026-W46", "2027-W01", "2026-W52", "2026-W01"]


def calculer():
    v = {"fnv": [[s, A.fnv(s)] for s in ["", "a", "2026-11-03", "2026-W45", "2026-W45:mot", "éàü", "pixel ☀"]]}
    v["jours_entre"] = [[a, b, A.jours_entre(a, b)] for a, b in [("2026-11-03", "2026-11-04"), ("2026-11-03", "2026-12-03"),
                                                                 ("2026-12-31", "2027-01-01"), ("2026-11-10", "2026-11-03")]]
    v["intervalle"] = [[k, A.intervalle(k)] for k in range(-1, 8)]
    v["jour"] = [[j, c, A.commande_du_jour(j, set(c))] for j in JOURS for c in CONNUES]
    vus = {"head": ["2026-10-25", 0], "ls": ["2026-11-02", 1], "cd": ["2026-10-01", 4], "rm": ["2026-11-03", 0]}
    v["revision"] = [[vus, j, A.revision_due(vus, j)] for j in ["2026-11-03", "2026-11-04", "2026-10-26", "2026-10-02"]]
    v["revision"].append([{}, "2026-11-03", None])
    v["maitrise"] = [[m, vue, A.niveau_maitrise(m, vue)] for m in ([0, 0, 0], [1, 0, 0], [0, 7, 0], [1, 5, 1], [0, 0, 1])
                     for vue in (False, True)]
    v["enigme"] = [[s, c, list(A.enigme(s, set(c)))] for s in SEMAINES for c in CONNUES]
    v["temps"] = [[s, lim, A.etat_temps(s, lim)] for s in (0, 2399, 2400, 2699, 2700, 3599, 3600, 9000)
                  for lim in (None, 45, 60)]
    return v


print("1. Les vecteurs partagés avec Kotlin (donnees/apprendre/vecteurs.json)")
v = calculer()
if "--ecrire" in sys.argv or not VECTEURS.exists():
    VECTEURS.parent.mkdir(parents=True, exist_ok=True)
    VECTEURS.write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"  (vecteurs écrits : {VECTEURS})")
lu = json.loads(VECTEURS.read_text(encoding="utf-8"))
for k in v:
    verifier(json.loads(json.dumps(v[k])) == lu.get(k), f"vecteurs « {k} » : le calcul Python n'a pas changé")
verifier((RACINE / "pc/tg/apprendre.json").read_text() == (RACINE / "app/src/main/assets/apprendre.json").read_text(),
         "apprendre.json : les copies PC et Android sont égales")
verifier(len({x[2] for x in v["jour"] if x[0] == "2026-11-03"}) >= 1 and all(x[2] in A.cmds() for x in v["jour"]),
         "la commande du jour est toujours une commande du carnet")
verifier(all(x[2] in x[1] or x[2] == next((c for c in A.cmds() if c not in x[1]), None) or not x[1]
             for x in v["jour"]), "… une commande connue, ou la toute prochaine à découvrir")

# ---------------------------------------------------------------- l'enfant et son terminal (un vrai bash)
st = core.new_state("Pixel")
core.migrate(st)
st["intro"] = {"etat": "fini"}
st["seen"] = ["pwd", "ls", "cd", "cat"]
core.save(st)
T = core.TERRAIN
T.mkdir(parents=True, exist_ok=True)
ici = [str(T)]


def taper(ligne, attendu=None):
    """La ligne dans un vrai bash (dans le dossier courant), puis le tour de jeu avec son code et le nouveau dossier."""
    r = subprocess.run(["bash", "-c", f"cd {json.dumps(ici[0])} && {ligne}\nc=$?; echo; echo \"@@$c@@$PWD\""],
                       capture_output=True, text=True, env=dict(os.environ, LC_ALL="C.UTF-8"))
    m = re.search(r"@@(\d+)@@(.*)$", r.stdout.strip())
    code, ici[0] = (int(m.group(1)), m.group(2)) if m else (1, ici[0])
    s = core.load()
    core.migrate(s)
    core.DERNIER.update(ligne=ligne, statut=code)
    s.pop("terminal_info", None)
    s.pop("terminal", None)
    app.boucle_jeu(s, [ligne], spontane=False, defis=False, cwd=ici[0])
    core.save(s)
    if attendu is not None:
        verifier(code == attendu, f"`{ligne}` → code {code}")
    return s, code, nu(s.get("terminal_info", []) + s.get("terminal", []))


def tg(*args):
    out = subprocess.run([sys.executable, "-m", "tg", *args], capture_output=True, text=True, cwd=str(RACINE / "pc"),
                         env=dict(os.environ, COLUMNS="120"), input="")
    return nu(out.stdout + out.stderr)


# ---------------------------------------------------------------- 27. le bac à sable
print("27. Le bac à sable : rien ne compte, rien ne se perd")
o = tg("bac-a-sable")
verifier("cd ~/terrain_terminagotchi/bac_a_sable" in o and (T / "bac_a_sable" / "chateau" / "donjon.txt").exists(),
         "tg bac-a-sable : le dossier et ses jouets (château, coffre, tunnel…)")
ici[0] = str(T)
x0 = core.load()["xp"]
f0 = core.load()["hunger"]
s, c, msg = taper("cd bac_a_sable")
verifier("Bac à sable" in msg and s["apprendre"]["bac_ici"], "en entrant : le bandeau « bac à sable »")
for l in ("ls", "mkdir -p tour/haute", "touch tresor.txt", "rm coffre.txt", "head recette.txt", "sort recette.txt"):
    s, c, msg = taper(l)
verifier(s["xp"] == x0 and abs(s["hunger"] - f0) < 1.0, f"aucune XP, la faim ne bouge pas ({s['xp']} XP, faim {s['hunger']:.0f})")
verifier("head" in s["seen"] and "sort" in s["seen"], "une commande jamais tapée y devient « découverte » (blanche au carnet)")
verifier(not s["apprendre"]["maitrise"].get("head"), "… mais ne compte pas pour la maîtrise")
lig = nu(__import__("tg.compagnon", fromlist=["x"]).ligne(s))
verifier("[bac à sable]" in lig, f"l'invite montre « [bac à sable] » ({lig[:40]})")
o = tg("bac-a-sable", "neuf")
verifier((T / "bac_a_sable" / "coffre.txt").exists() and not (T / "bac_a_sable" / "tresor.txt").exists(),
         "tg bac-a-sable neuf : tout revient comme au début")
s, c, msg = taper("cd ..")
verifier(not s["apprendre"]["bac_ici"], "en sortant : le jeu compte de nouveau")

# ---------------------------------------------------------------- 46. le tableau des rares
print("46. Le tableau des rares")
s = core.load()
s["collection"]["Sylvarque"] = 1
core.save(s)
o = tg("collection", "rares")
verifier("1 / 11" in o and "Sylvarque" in o and "attirée par chmod" in o, "page 1 : 10 légendaires + Abyssor, Sylvarque dressée, indices")
verifier("se montre très rarement" in o, "Abyssor (attirée par sudo) : « se montre très rarement »")
o2 = tg("collection", "rares", "2")
verifier("0 / 40" in o2, "page 2 : les 40 rares")

# ---------------------------------------------------------------- 43. la maîtrise
print("43. La maîtrise : trois ronds, le rond doré ne se perd jamais")
ici[0] = str(T)
taper("mkdir -p maitrise")
for k in range(5):
    s, c, msg = taper("ls -a")
m = s["apprendre"]["maitrise"]["ls"]
verifier(m[0] == 1 and m[2] == 1, f"ls -a cinq fois : option + maîtrisée ({m})")
verifier("◉" in nu(A.lignes_maitrise(s)), "tg badges / maîtrise : le rond doré")
s, c, msg = taper("ls fichier_qui_n_existe_pas")
verifier(s["apprendre"]["maitrise"]["ls"][2] == 1, "une erreur ensuite ne retire rien")
o = tg("badges")
verifier("Maîtrise des commandes" in o, "tg badges montre la maîtrise des commandes")
s = core.load()
for c_ in A.cmds()[:10]:
    s["apprendre"]["maitrise"][c_] = [1, 5, 1]
core.save(s)
from tg import entrainement as E  # noqa: E402
verifier(any(i == "main_sure" for i, _x, _c in E.titres(core.load())), "10 commandes maîtrisées : le titre « Main sûre »")

# ---------------------------------------------------------------- 24. les révisions
print("24. Les révisions espacées, sans pression")
s = core.load()
hier = A.jour_de(time.time() - 9 * 86400)
s["apprendre"]["vus"]["head"] = [hier, 0]
s["apprendre"]["rev"] = {}
s["bubble"] = None
s["bulles"] = []
core.save(s)
s, c, msg = taper("pwd")
verifier(s["apprendre"]["rev"].get("cmd") == "head" and "head" in str(s.get("bubble")) + str(s.get("bulles")),
         "une invitation dans la bulle (« Tu te souviens de head ? »)")
x0 = s["xp"]
(T / "nid.txt").write_text("a\nb\nc\nd\n")
s, c, msg = taper("head -n 2 nid.txt")
verifier(s["xp"] >= x0 + 4 and "Souvenir rafraîchi" in msg, f"refaite : +4 XP, prochain rappel plus loin ({msg[:60]})")
verifier(s["apprendre"]["vus"]["head"][1] == 1, "l'étape monte (1 → 3 jours)")
s, c, msg = taper("pwd")
verifier(s["apprendre"]["rev"].get("fait"), "une seule invitation par jour")
o = tg("souvenirs")
verifier("Souvenirs à rafraîchir" in o and "oublié" not in o, "tg souvenirs : la page, sans le mot « oublié »")

# ---------------------------------------------------------------- 29. la commande du jour
print("29. Le défi du jour d'une commande")
s = core.load()
jour, cmd = A.mission_du_jour(s)
ex = A.donnees()["jour"]["exemples"][cmd]
o = tg("jour")
verifier("La commande du jour" in o and ex in o and "de suite" not in o, f"tg jour : la mission ({cmd}), aucun « de suite »")
ici[0] = str(T)
(T / "jourtest").mkdir(exist_ok=True)
ici[0] = str(T / "jourtest")
for f in ("recette.txt", "pomme.txt", "poire.txt", "vieux.txt"):
    (T / "jourtest" / f).write_text("miel\nfarine\nsel\n")
(T / "jourtest" / "cabane").mkdir(exist_ok=True)
# (une commande tapée plus haut dans ce test peut déjà avoir réussi la mission du jour, selon la date : on repart à zéro)
core.modifier(lambda st: st["apprendre"].update(tampons=[j for j in st["apprendre"]["tampons"] if j != jour]))
x0 = core.load()["xp"]
prepa = {"rm": "rm -i poire.txt < /dev/null; true", "less": "less recette.txt < /dev/null"}
s, c, msg = taper(prepa.get(cmd, ex))
verifier(jour in s["apprendre"]["tampons"] and s["xp"] >= x0 + 8, f"`{ex}` : +8 XP et un tampon soleil ({msg[:50]})")
o = tg("jour")
verifier("☀" in o and "Mission du jour réussie" in o, "le calendrier du mois montre le tampon")

# ---------------------------------------------------------------- 44. l'énigme de la semaine
print("44. Les énigmes hebdomadaires (hors ligne)")
o = tg("enigme")
sem = A.semaine()
d = A.dossier_enigme(sem)
verifier(d.is_dir() and (d / "lis-moi.txt").exists(), f"tg enigme : le dossier {d.name} est préparé")
rep = A.reponse_enigme(sem, core.load())
o = tg("enigme", "indice")
verifier("💡" in o, "tg enigme indice : un indice")
o = tg("enigme", "reponse", "pas-ca")
verifier("pas encore" in o, "une mauvaise réponse : « pas encore », rien de perdu")
x0 = core.load()["xp"]
o = tg("enigme", "reponse", rep)
verifier("Bravo" in o and core.load()["xp"] >= x0 + 15, f"la bonne réponse ({rep}) : +15 XP")
o = tg("enigme")
verifier("Déjà résolue" in o, "déjà résolue cette semaine")

# ---------------------------------------------------------------- 23. les erreurs en mini-énigmes
print("23. Les erreurs deviennent des mini-énigmes")
s = core.load()
s["apprendre"]["erreur_t"] = 0
s["apprendre"]["erreur"] = None
core.save(s)
ici[0] = str(T)
(T / "enigmes_erreur").mkdir(exist_ok=True)
vrai_etape = histoire.en_pleine_etape
histoire.en_pleine_etape = lambda state: True
ici[0] = str(T / "enigmes_erreur")
s, c, msg = taper("cat absent.txt", 1)
verifier("Petite énigme" not in msg, "jamais pendant une étape de leçon")
histoire.en_pleine_etape = lambda state: False
ici[0] = str(T / "enigmes_erreur")
(T / "enigmes_erreur" / "cabane").mkdir(exist_ok=True)
(T / "enigmes_erreur" / "cabane" / "lettre.txt").write_text("Bonjour Pixel !\n")
s, c, msg = taper("cat lettre.txt", 1)
verifier("Petite énigme" in msg and "lettre.txt" in msg and "ls" in msg, f"cat d'un fichier absent : l'énigme et un 1er indice")
s, c, msg = taper("pwd")
verifier("💡" in msg, "la commande d'après : le 2e indice")
x0 = s["xp"]
s, c, msg = taper("cat cabane/lettre.txt", 0)
verifier("Énigme résolue" in msg and s["xp"] >= x0 + 3, "résolue : +3 XP")
s, c, msg = taper("cd nulle_part", 1)
verifier("Petite énigme" not in msg, "une seule énigme toutes les 10 minutes")
s = core.load()
s["apprendre"]["erreur_t"] = 0
core.save(s)
s, c, msg = taper("rm cabane", 1)
verifier("broyeuse" in msg, "rm d'un dossier : « la broyeuse refuse… »")
o = tg("passe")
verifier("rien n'est perdu" in o.lower() or "Rien n'est perdu" in o, "tg passe : l'énigme est oubliée, rien de perdu")
for cas, ligne in (("existe", "mkdir cabane"), ("lieu", "cd nulle_part"), ("cat_dossier", "cat cabane"),
                   ("introuvable", "cp absent.txt x.txt")):
    verifier((A.cause_erreur(ligne, ici[0]) or [None])[0] == cas, f"le cas « {cas} » est deviné ({ligne})")
verifier(A.cause_erreur("cat lettre.txt", None) is None, "sans dossier connu : pas d'énigme (on ne devine jamais au hasard)")
histoire.en_pleine_etape = vrai_etape

# ---------------------------------------------------------------- 21. le dictionnaire illustré
print("21. Le dictionnaire illustré")
o = tg("carnet")
verifier("Carnet d'aventure de Pixel" in o and "page 1/4" in o and "je marche jusqu'à un lieu" in o, "tg carnet : page 1/4, l'image en mots")
verifier("▀" in o or "▄" in o, "… avec l'image 16 × 16 en demi-blocs")
o = tg("carnet", "4")
verifier("à découvrir" in o, "une commande jamais tapée : la silhouette grise et « à découvrir »")
P = A.donnees()["pictos"]
verifier(len(P["images"]) == 20 and all(len(r) == 16 and all(len(x) == 16 for x in r) for r in P["images"].values()),
         "20 images 16 × 16 dessinées en code")
verifier(set(P["images"]) == set(A.cmds()), "une image pour chacune des 20 premières commandes")
o = tg("lexique")
verifier("tg carnet" in o, "tg lexique renvoie au carnet illustré")

# ---------------------------------------------------------------- 41 / 42. mini-jeux et course
print("41. Les mini-jeux dans le terminal ; 42. la course (optionnelle)")
o = tg("jeux")
verifier(all(n in o for n in ("Labyrinthe", "Taupes", "Pêche", "facteur")), "tg jeux : les 4 jeux")
o = tg("jeux", "labyrinthe")
dj = T / "jeux" / "labyrinthe"
ici[0] = str(dj)
x0 = core.load()["xp"]
taper("cd grotte", 0)
taper("ls")
taper("cd salle_humide/impasse", 0)
taper("cd ../..", 0)
s, c, msg = taper("cd salle_seche/tunnel/salle_du_tresor", 0)
verifier("Gagné" in msg and s["xp"] >= x0 + 5, f"labyrinthe : la salle du trésor → gagné +5 XP ({msg[:50]})")
verifier("◆" in nu(A.carte_labyrinthe(s)) or "✓" in nu(A.carte_labyrinthe(s)), "la carte des salles visitées")
o = tg("course", "oui")
verifier("OUI" in o, "tg course oui")
o = tg("jeux", "taupes")
verifier("fantôme" in o or "chrono" in o, "avec la course : le chrono et le fantôme sont annoncés")
ici[0] = str(T / "jeux" / "taupes")
s, c, msg = taper("rm fleur_1.txt")
verifier("fleur" in msg.lower(), "une fleur broyée : un mot gentil et `tg jeux taupes` replante (pas d'échec)")
tg("jeux", "taupes")
s, c, msg = taper("rm taupe_*")
verifier("Gagné" in msg and "⏱" in msg, f"taupes : gagné, avec le temps ({msg[:80]})")
s = core.load()
verifier("taupes" in s["apprendre"]["jeux"].get("records", {}), "le record devient le fantôme (jamais les autres)")
o = tg("jeux", "peche")
o = tg("jeux", "reponse", "2")
verifier("Pas tout à fait" in o, "pêche : mauvais compte → « pas tout à fait », ls -a proposé")
o = tg("jeux", "reponse", "4")
verifier("Gagné" in o, "pêche : 4 poissons cachés → gagné")
tg("jeux", "facteur")
ici[0] = str(T / "jeux" / "facteur")
s, c, msg = taper("mv lettre_1.txt lettre_4.txt chateau/ && mv lettre_2.txt moulin/ && mv lettre_3.txt phare/")
verifier("Gagné" in msg, "facteur : chaque lettre dans sa maison → gagné")
s = core.load()
verifier(s["apprendre"]["jeux"]["xp_jour"][1] <= A.donnees()["jeux"]["plafond"], "l'XP des mini-jeux a un plafond par jour")
o = tg("course", "eclairs", "non")
verifier("NON" in o and not A.eclairs(core.load()), "tg course eclairs non : plus de défis éclair surprises")
s = core.load()
for _ in range(400):
    core.defi_tick(s, [], spontaneous=app.apprendre.eclairs(s), proba=1.0)
verifier(not s.get("defi"), "… et aucun ne se lance tout seul")
tg("course", "eclairs", "oui")
tg("course", "non")

# ---------------------------------------------------------------- 49. la limite de temps douce
print("49. La limite de temps douce")
o = subprocess.run([sys.executable, "-m", "tg", "parent", "temps", "45"], capture_output=True, text=True,
                   cwd=str(RACINE / "pc"), input="non merci\n").stdout
verifier("Rien n'a changé" in nu(o), "sans la phrase d'un adulte : rien ne change")
o = subprocess.run([sys.executable, "-m", "tg", "parent", "temps", "45"], capture_output=True, text=True,
                   cwd=str(RACINE / "pc"), input="oui je suis un adulte\n").stdout
verifier("45 minutes" in nu(o) and core.load()["apprendre"]["temps"]["limite"] == 45, "avec « oui je suis un adulte » : 45 min réglées")
s = core.load()
now = time.time()
tp = s["apprendre"]["temps"]
tp.update(jour=A.jour_de(now), s=41 * 60, t=now - 10)
core.save(s)
ici[0] = str(T)
s, c, msg = taper("pwd")
verifier("bâille" in msg, "à 5 minutes de la fin : elle bâille")
s = core.load()
s["apprendre"]["temps"]["s"] = 45 * 60
s["apprendre"]["temps"]["t"] = time.time() - 5
core.save(s)
s, c, msg = taper("pwd")
verifier(A.endormie(s) and "s'endort" in msg, "à 45 minutes : elle s'endort jusqu'à 7 h")
x0, f0 = s["xp"], s["hunger"]
s, c, msg = taper("whoami")
verifier(s["xp"] == x0 and "chut" in msg, "pendant le sommeil : le terminal marche, mais rien ne nourrit ni ne donne d'XP")
fin = s["apprendre"]["temps"]["dort"]
deb = s["apprendre"]["temps"]["dort_debut"]
verifier(satiete.sommeil(s) == (deb, fin) and A.prochain_reveil(deb) == fin, "réveil au prochain 7 h")
t2 = dict(s)
t2["last_tick"] = deb
t2["hunger"] = 70.0
satiete.tick(t2, min(fin, deb + 3600))
verifier(abs(t2["hunger"] - 70.0) < 0.01, f"la faim ne baisse pas pendant le sommeil ({t2['hunger']:.2f})")
o = subprocess.run([sys.executable, "-m", "tg", "parent", "temps", "non", "--oui"], capture_output=True, text=True,
                   cwd=str(RACINE / "pc")).stdout
verifier("enlevée" in nu(o) and not A.endormie(core.load()), "tg parent temps non : plus de limite, elle se réveille")
s = core.load()
s["apprendre"]["temps"].update(s=61 * 60, t=time.time() - 5, pause_dite=None)
core.save(s)
s, c, msg = taper("pwd")
verifier("pause" in msg.lower(), "sans réglage : une seule proposition « On fait une pause ? » après une heure")
s, c, msg = taper("pwd")
verifier("pause" not in msg.lower(), "… une seule fois")

# ---------------------------------------------------------------- 45. le sentier des marmottes
print("45. Le Sommet pour tous : le sentier des marmottes")
from tg import sommet as SO  # noqa: E402
o = tg("sommet", "sentier")
verifier("palier 3" in o, "fermé tant qu'aucun monde n'est au palier 3")
vrai_palier = SO.mondes_au_palier
SO.mondes_au_palier = lambda state, p=None: ["port"]
s = core.load()
verifier(A.sentier_ouvert(s), "un monde au palier 3 : le sentier s'ouvre (la voie Expert++ garde ses 3 mondes)")
out = A.commande_sentier(s)
core.save(s)
verifier("S7" in nu(out) and A.dossier_sentier().is_dir(), "tg sommet sentier : les 7 étapes, le sentier est préparé")
ici[0] = str(A.dossier_sentier())
for l in ('echo "Bonjour le sommet"', "mkdir bivouac", "grep marmotte inscriptions.txt", 'find . -name "*.caillou"',
          "ls -l", "ls --help > /dev/null", "cat sommet.txt"):
    s, c, msg = taper(l, 0)
verifier(len(s["apprendre"]["sentier"]) == 7, f"les 7 étapes franchies ({s['apprendre']['sentier']})")
verifier("sommet.sentier" in s.get("recompenses", {}).get("exploits", {}), "l'exploit du sentier (pas la récompense légendaire)")
verifier(recompenses.exploit_def("sommet.sentier")[1]["recompense"] == "variante", "… une variante existante, pas un légendaire")
SO.mondes_au_palier = vrai_palier

# ---------------------------------------------------------------- 30. l'examen-aventure et le diplôme
print("30. L'examen-aventure et le diplôme")
s = core.load()
histoire.h_(s)["ailes"].append("grenier")
s["espece_compagnon"] = s.get("espece_compagnon") or "braisillon"
core.save(s)
o = tg("examen")
verifier("salle 1 sur 5" in o and "La forêt du Grenier" in o, "tg examen : la forêt du Grenier, salle 1 sur 5")
ici[0] = str(A.dossier_examen() / "salle_1")
s, c, msg = taper("ls")
s, c, msg = taper("pwd")
verifier("guide te montre" in msg and "tree" in msg, "après 2 essais : le guide montre la commande")
s, c, msg = taper("ls -R", 0)
verifier("Salle 1 franchie" in msg, "salle 1 (tree ou ls -R) franchie")
ici[0] = str(A.dossier_examen() / "salle_2")
taper("mv ours.txt coffre/", 0)
ici[0] = str(A.dossier_examen() / "salle_3")
taper("cp carte.txt carte_copie.txt", 0)
ici[0] = str(A.dossier_examen() / "salle_4")
taper("rm caillou.txt", 0)
ici[0] = str(A.dossier_examen() / "salle_5")
s = core.load()
x0 = s["xp"] + satiete.s_(s)["reserve"]
s, c, msg = taper("ls", 0)
verifier("Examen réussi" in msg and s["xp"] + satiete.s_(s)["reserve"] >= x0 + 20 and "grenier" in s["apprendre"]["diplomes"], "5 salles : examen réussi, +20 XP")
p = T / "diplome_grenier.png"
b = p.read_bytes() if p.exists() else b""
verifier(b[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", b[16:24]) == (900, 630), "le diplôme PNG (900 × 630) est dans le terrain")
verifier((T / "diplome_grenier.svg").exists(), "… et sa version SVG (toutes les écritures)")
raw = zlib.decompress(b[b.index(b"IDAT") + 4:b.index(b"IEND") - 8]) if b else b""
verifier(len(raw) == 630 * (1 + 900 * 3), "le PNG se décode (RVB, sans transparence)")
verifier(s.get("name", "") and "prenom" not in json.dumps(s["apprendre"]).lower(), "aucun prénom enregistré (une ligne à écrire à la main)")
o = tg("examen")
verifier("Pas d'examen" in o, "l'examen passé ne revient pas")

# ---------------------------------------------------------------- 50. pas de série à perdre
print("50. Pas de série à perdre (rappel : test_satiete.py, test_programme.py)")
s = core.load()
verifier("de suite" not in nu(satiete.lignes(s)) and "jamais perdus" in nu(satiete.lignes(s)),
         "tg satiete : « Jours bien nourrie : N au total… (jamais perdus) »")
verifier(langue.brut("core.defi.rate.dit") == "Le défi s'est envolé… on rejouera !", "défi éclair : « Le défi s'est envolé… on rejouera ! »")

# ---------------------------------------------------------------- les 14 langues
print("Les 14 langues : chaque écran s'affiche")
for code in langue.LANGUES:
    langue.definir(code)
    s = core.load()
    try:
        for f, a in ((A.ecran_carnet, []), (A.ecran_jour, None), (A.ecran_rares, []), (A.lignes_souvenirs, None),
                     (A.commande_jeux, []), (A.commande_course, []), (A.lignes_maitrise, None), (A.commande_examen, [])):
            (f(s, a) if a is not None else f(s))
        A.contenu_diplome(s, "grenier")
        bon = True
    except Exception as e:  # noqa: BLE001
        bon = False
        print("   ", code, repr(e))
    verifier(bon, f"{code} : carnet, jour, rares, souvenirs, jeux, course, maîtrise, examen")
langue.definir("fr")

# ---------------------------------------------------------------- sécurité
print("Sécurité : rien hors du terrain")
verifier(not A._vider(Path.home()) and not A._vider(T), "le jeu n'efface jamais le HOME ni le terrain entier")
lien = T / "jeux" / "lien"
try:
    lien.symlink_to(Path.home())
    verifier(not A._vider(lien) and Path.home().exists(), "un lien symbolique n'est jamais suivi pour effacer")
finally:
    if lien.is_symlink():
        lien.unlink()

print(f"\n{ok} réussis, {ko} échoués   (HOME={os.environ['HOME']})")
if not ko and "--garder" not in sys.argv:
    import shutil
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)      # (le disque est partagé : on range son HOME de test)
sys.exit(1 if ko else 0)
