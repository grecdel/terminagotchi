"""Le mode classe (docs/programme.md § 7.7), 100 % local, sur PC.

    python3 pc/outils/test_classe.py          (crée son propre HOME temporaire, hors ligne)

  1. le code de séance : vecteurs communs avec le site à jour ; toute faute de frappe d'un seul caractère et toute
     inversion de deux chiffres sont refusées ; les options toujours dans le même ordre ;
  2. rejoindre : mauvais code, « Prénom Nom » et pseudonymes trop courts refusés ; le chapitre visé est choisi ; faim en
     pause, notifications coupées, « sans aide » avec l'option A ;
  3. AUCUN ENVOI pendant la séance : aucune connexion réseau ouverte (socket espionné), la synchro et les requêtes du
     recensement refusent, l'adresse du site n'est même pas cherchée ;
  4. une vraie séance dans bash (chapitre 5, la bibliothèque) : crans A, puis C en mode « sans aide », les blocages
     (3 essais ratés ou plus), un exercice d'entraînement vérifié (cran D) ; le dressage sans chrono (option S) ;
  5. le bilan à l'écran, en .txt et en .csv (pseudonyme seulement, aucun nom de compte, aucun chemin personnel) ;
     rassembler les bilans côté enseignant (trié par date et pseudonyme : jamais de classement) ;
  6. finir rend les réglages d'avant, effacer oublie tout ; rien d'écrit hors du HOME de test ; 14 langues.
"""
import builtins
import csv
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_classe_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

CONNEXIONS = []
_connect = socket.socket.connect


def _espion(self, adresse):
    CONNEXIONS.append(adresse)
    raise OSError("test : réseau interdit")


socket.socket.connect = _espion
socket.create_connection = lambda adresse, *a, **k: (CONNEXIONS.append(adresse), (_ for _ in ()).throw(OSError("test")))[1]

from tg import app, classe as C, core, dressage, entrainement, histoire, langue, recense  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ok = ko = 0
terminal = [str(HOME)]
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=60, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)


def propre(s):
    return ANSI.sub("", s).replace("`", "")


langue.definir("fr")
print("1. Le code de séance")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_classe.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/classe/vecteurs.json, mêmes codes sur le site)")
V = json.loads((RACINE / "donnees/classe/vecteurs.json").read_text(encoding="utf-8"))
verifier(all(C.lire(v["code"]) == {"n": v["n"], "options": v["options"]} for v in V["codes"]) and len(V["codes"]) == 19 * 8,
         "les 152 codes (chapitres 0 à 18 × 8 combinaisons d'options) se relisent")
verifier(C.fabriquer(5, "SG") == "05-GS-K" and C.lire("05 gs k") == {"n": 5, "options": "GS"} and C.lire("05GSK"),
         "05-GS-K (l'exemple de l'aide) : minuscules, espaces et tirets acceptés")
fautes = 0
for v in V["codes"]:
    brut = v["code"].replace("-", "")
    for i, x in enumerate(brut):
        for y in "0123456789AGS" + C.LETTRES:
            if y != x and C.lire(brut[:i] + y + brut[i + 1:]) is not None:
                fautes += 1
    if brut[0] != brut[1] and C.lire(brut[1] + brut[0] + brut[2:]) is not None:
        fautes += 1
verifier(fautes == 0, f"toute faute d'un seul caractère et toute inversion des deux chiffres sont refusées ({fautes} passée(s))")
verifier(all(C.lire(f["code"]) is None for f in V["faux"]), "les codes faux des vecteurs sont refusés (ordre des options, doublons…)")
verifier("Code de séance : 05-GS-K" in propre(C.commande(["creer", "5", "grand", "sanschrono"]))
         and "05-GS-K" in propre(C.commande(["creer", "bibliotheque", "sanschrono", "grand"]))
         and "ne connais pas" in C.commande(["creer", "nimporte"]) and "n'existe pas" in C.commande(["creer", "42"]),
         "tg classe creer : par numéro ou par nom, options dans n'importe quel ordre ; refus clairs")

print("2. Rejoindre la séance")
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin(avec_intro=False)


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0
    s["config"]["notifs"] = True
    s.setdefault("compte", {}).update(cle="cle-de-test", serveur="https://exemple.invalid", pseudo="VraiCompte")


core.modifier(ouvrir)
verifier("ne marche pas" in C.commande(["code", "05-GS-X", "Lynx42"]), "un code mal recopié : refusé, rien ne change")
verifier(all("pseudonyme" in C.commande(["code", "05-GS-K", p]) for p in ("Jean Dupont", "J", "x" * 17, "élève")),
         "pseudonymes refusés : avec espace (« Prénom Nom »), trop court, trop long, accents")
verifier(not C.actif(core.load()), "toujours pas de séance après les refus")
msg = propre(C.commande(["code", "05-GS-K", "Lynx42"]))
st = core.load()
verifier(C.actif(st) and "Lynx42" in msg and "La bibliothèque engloutie" in msg and "Rien n'est envoyé" in msg,
         "05-GS-K Lynx42 : la séance commence, au chapitre 5")
verifier(histoire.h_(st)["chap"] == "bibliotheque" and st["config"]["notifs"] is False
         and st["satiete"]["vacances"] is True and not st["config"].get("sans_aide"),
         "chapitre choisi, notifications coupées, faim en pause, pas de « sans aide » sans l'option A")
verifier("tg espace classe" in msg and "sans chrono" in msg, "options G et S annoncées (grand écran : tg espace classe)")

print("3. Aucun envoi pendant la séance")
avant = len(CONNEXIONS)
r1 = recense.requete("https://exemple.invalid/api/sync", "POST", {"x": 1}, "cle")
r2 = recense.synchroniser(forcer=True)
r3 = recense.serveur(core.load())
r4 = recense.commande(["code"])
verifier("rien n'est envoyé" in r1.get("erreur", "") and "rien n'est envoyé" in (r2 or "") and r3 == "",
         "requête, synchro forcée et adresse du site : refusées en séance")
verifier(len(CONNEXIONS) == avant, f"aucune connexion réseau ouverte (tentatives : {CONNEXIONS[avant:]})")
verifier(core.load()["compte"].get("dernier", 0) == 0, "le compte n'est pas touché (pas de « dernière synchro »)")
_ = r4

print("4. Une vraie séance dans bash")
T.mkdir(exist_ok=True)
tape("ls")
st = core.load()
les, _ = histoire.lecon_courante(st)
verifier(les and les["chap"] == "bibliotheque", f"leçon en cours : {les and les['id']}")
for x in ("lss", "cd nulle_part", "pwdd"):
    tape(x)
st = core.load()
cle = f"{les['id']}:{st['step']}"
verifier(st["classe"]["rates"].get(cle, 0) >= 3, f"3 essais ratés comptés sur l'étape {cle}")
etapes = histoire.etapes(st, les["id"])
tape(etapes[0]["cmd"])
st = core.load()
verifier(st["classe"]["etapes"] and st["classe"]["etapes"][-1]["cran"] == "A", "étape réussie avec la commande montrée : cran A")
core.modifier(lambda s: s["config"].update(sans_aide=True))
st = core.load()
step = histoire.etapes(st, les["id"])[st["step"]]
tape(step["cmd"])
st = core.load()
verifier(st["classe"]["etapes"][-1]["cran"] == "C" and st["classe"]["etapes"][-1]["cmd"] == step["cmd"],
         f"en mode sans aide, commande cachée trouvée : cran C ({step['cmd']})")
core.modifier(lambda s: s["config"].update(sans_aide=False))
lignes = []
core.modifier(lambda s: lignes.extend(entrainement.commencer(s)))
st = core.load()
if st["entrainement"].get("cours"):
    core.modifier(lambda s: entrainement.reussir(s))
st = core.load()
verifier(len(st["classe"]["ex"]) == 1, "un exercice d'entraînement réussi (résultat vérifié) : cran D")
from tg import bestiaire as B  # noqa: E402
e = next(iter(B.publiques()), None)
st = core.load()
st.setdefault("dressage_familles", []).append(e["famille"])     # pas la première fois : d'habitude, un chrono
s = {"f": dressage.fiche(e["nom"]).name, "e": e["nom"], "zone": "grenier", "shiny": False, "v": "classique",
     "ind": B.individu(e, False, "grenier", "classique")}
dressage.commencer(st, s)
verifier(st["dressage"] and st["dressage"]["duree"] is None and dressage.reste(st) is None, "option S : le dressage n'a pas de chrono")
st["classe"]["options"] = "G"
st["dressage"] = None
dressage.commencer(st, dict(s))
verifier(st["dressage"] and st["dressage"]["duree"], "sans l'option S : le chrono revient")

print("5. Le bilan")
st = core.load()
txt = "\n".join(propre(x) for x in C.lignes_bilan(st))
verifier("Lynx42" in txt and "05-GS-K" in txt and "cran A" in txt and "cran C" in txt and "(cran D) : 1" in txt,
         "le bilan à l'écran : pseudonyme, code, crans A, C, D")
verifier(step["cmd"] in txt and re.search(r"(lss|cd nulle_part|pwdd|cd ~/terrain_terminagotchi/bibliotheque) \([3-9]\)", txt), "le bilan cite la commande trouvée seul et le blocage")
verifier("Pixel" not in txt and "VraiCompte" not in txt and str(HOME) not in txt,
         "ni le nom de la créature, ni le pseudo du compte, ni un chemin personnel")
out = C.commande(["bilan", "fichier"])
fichiers = sorted(HOME.glob("terminagotchi_bilan_Lynx42_*"))
verifier([p.suffix for p in fichiers] == [".csv", ".txt"], f"bilan fichier : .txt et .csv dans le dossier personnel ({len(fichiers)})")
ligne = next(csv.DictReader(io.StringIO(fichiers[0].read_text(encoding="utf-8-sig")), delimiter=";"))
print(ligne) if "--montrer" in sys.argv else None
verifier(ligne["pseudo"] == "Lynx42" and ligne["code"] == "05-GS-K" and int(ligne["etapes_cran_A"]) >= 1
         and ligne["exercices_cran_D"] == "1" and list(ligne) == C.COLONNES and int(ligne["commandes"]) >= 2
         and ligne["blocages"].startswith("cd ~/terrain_terminagotchi/bibliotheque (") and ligne["chapitre_vise"].startswith("5 · "), "le .csv : une ligne, les colonnes prévues")
verifier("VraiCompte" not in fichiers[0].read_text(encoding="utf-8-sig") + fichiers[1].read_text(encoding="utf-8"),
         "rien du compte en ligne dans les fichiers")
remis = Path(tempfile.mkdtemp(prefix="tg_remis_"))
(remis / fichiers[0].name).write_bytes(fichiers[0].read_bytes())
autre = dict(ligne, pseudo="Aigle7", blocages="ls -a (5)", chapitre_en_cours="3 · La forêt du Grenier")
f = io.StringIO()
w = csv.DictWriter(f, fieldnames=C.COLONNES, delimiter=";", lineterminator="\n")
w.writeheader()
w.writerow(autre)
(remis / "terminagotchi_bilan_Aigle7_2026-11-01.csv").write_text(f.getvalue(), encoding="utf-8")
(remis / "terminagotchi_bilan_casse.csv").write_text("n'importe quoi\n", encoding="utf-8")
lignes, sortie = C.rassembler(remis)
tout = propre("\n".join(lignes))
rangs = list(csv.DictReader(io.StringIO(sortie.read_text(encoding="utf-8-sig")), delimiter=";"))
verifier([x["pseudo"] for x in rangs] == ["Aigle7", "Lynx42"], "rassembler : 2 bilans (le fichier abîmé est ignoré), triés par pseudonyme")
verifier("2 bilans" in tout and "ls -a (1)" in tout and "jamais de classement" in tout, "où la classe bloque ; jamais de classement")
verifier("Aucun bilan" in C.commande(["rassembler", tempfile.mkdtemp()]), "un dossier vide : dit clairement qu'il n'y a rien")

print("6. Finir, effacer")
msg = C.commande(["fin"])
st = core.load()
verifier(not C.actif(st) and st["config"]["notifs"] is True and st["satiete"]["vacances"] is False
         and not st["config"].get("sans_aide"), "fin : notifications, faim et « sans aide » comme avant")
verifier("Lynx42" in propre(C.commande(["bilan"])), "après la fin, le bilan de la dernière séance reste lisible")
verifier("rien n'est envoyé" not in recense.requete("http://127.0.0.1:9/", delai=1).get("erreur", ""),
         "après la fin, le recensement redevient possible (l'enfant l'a choisi avant)")
verifier("effacées" in C.commande(["effacer"]) and "classe" not in core.load(), "effacer : la séance est oubliée")
d2 = C.commande(["code", "00-AGS-" + C.fabriquer(0, "AGS")[-1], "Lynx42"])
st = core.load()
verifier(C.actif(st) and st["config"].get("sans_aide") and histoire.h_(st)["chap"] == "bibliotheque",
         "00-AGS : pas de chapitre imposé (on reste où on était), « sans aide » activé")
C.commande(["fin"])
verifier(not core.load()["config"].get("sans_aide"), "et la fin le retire")

hors = []
for racine, dossiers, fichiers_ in os.walk(HOME):
    p = Path(racine)
    if p == T or T in p.parents or p == core.SAVE_DIR or core.SAVE_DIR in p.parents:
        dossiers[:] = []
        continue
    hors += [os.path.join(racine, x) for x in fichiers_ if not x.startswith("terminagotchi_bilan_") and x != ".bash_history"]
verifier(not hors, f"rien d'écrit hors du terrain, de la sauvegarde et des bilans ({hors[:3]})")
print("7. Les fiches et la page du site disent la même chose que le jeu")
fiches = (RACINE / "docs/classe/fiches_enseignant.md").read_text(encoding="utf-8")
codes_fiches = re.findall(r"`(\d\d-[AGS]*-?[A-Z])`", fiches)
verifier(len(codes_fiches) >= 40 and all(C.lire(x) for x in codes_fiches), f"les {len(codes_fiches)} codes des fiches sont justes")
mauvais = []
for bloc in re.split(r"\n# Fiche ", fiches)[1:]:
    bloc = bloc.split("\n# ", 1)[0]
    n = int(bloc.split(" ", 1)[0])
    mauvais += [x for x in re.findall(r"`(\d\d-[AGS]*-?[A-Z])`", bloc) if C.lire(x)["n"] != n]
    les = [histoire.lecon_def(l) for l in histoire.PAR_CHAP[next(c["id"] for c in histoire.CHAPITRES if c["n"] == n)]["lecons"]]
    from tg import lecons  # noqa: E402
    mauvais += [lecons.tx(d["titre"]) for d in les if f"« {lecons.tx(d['titre'])} »" not in bloc]
verifier(not mauvais, f"chaque fiche : codes de son chapitre, toutes ses leçons citées par leur nom ({mauvais[:4]})")
js = (RACINE / "site/src/enseignants_fr.js").read_text(encoding="utf-8")
noms = dict((int(n), nom.replace("\\'", "'")) for n, nom in re.findall(r'\[(\d+), "([^"]+)", "', js))
verifier(len(noms) == 18 and all(noms[c["n"]] == histoire.nom_chapitre(c["id"]) for c in histoire.CHAPITRES if 1 <= c["n"] <= 18),
         "la page /enseignants : les 18 noms de chapitres et de mondes sont ceux du jeu")
verifier((RACINE / "docs/classe/fiches_enseignant.pdf").is_file(), "le PDF des fiches existe (pc/outils/fiches_classe.py)")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/verifier_langues.py")], capture_output=True, text=True)
verifier(r.returncode == 0 and all(json.loads((RACINE / f"pc/tg/langues/{l}.json").read_text(encoding="utf-8")).get("classe.bilan.titre")
                                   for l in langue.LANGUES), "14 langues (verifier_langues.py)")
verifier(len(CONNEXIONS) <= 1, f"une seule connexion tentée de tout le test (le recensement, après la fin) : {CONNEXIONS}")

print("\n".join(C.lignes_bilan(core.load())) if "--montrer" in sys.argv else "")
print(f"\n{ok} ✔  {ko} ✖")
sys.exit(1 if ko else 0)
