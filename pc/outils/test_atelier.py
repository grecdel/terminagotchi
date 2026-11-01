"""L'Atelier (phase 5, docs/programme.md § 2.16 et § 7.13 « L'embarqué et le temps réel »), sur PC.

    python3 pc/outils/test_atelier.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/atelier/vecteurs.json, mêmes résultats en Kotlin) ; les
     arènes (un cerveau qui tourne réussit, un cerveau qui fonce se cogne, un cerveau qui s'arrête reste en dessous) ;
     les variantes réservées EXISTENT (types Machine et Plante), ni gardiens ni réservées ailleurs ; le Pont des Nombres
     « logique » et son exercice égal à bash ($(( a && b ))) ;
  2. l'arbre du Carrefour : fermé tant que le niveau 4 n'est pas fait, puis ouvert et annoncé une fois ; meublé ;
  3. la traversée at0 → at7 comme un enfant (vraies commandes dans bash, le vrai cerveau.sh, la vraie boucle for avec
     `atelier pas`), avec les erreurs d'un enfant (le cerveau d'exemple qui se cogne, un défi raté puis réussi) :
     exploit « le robot qui évite tous les obstacles », variantes réservées, le robot miniature et le titre ;
  4. les indices ; 5. la vue déployée (le robot) ;
  6. sécurité : rien hors du terrain, aucun sudo, aucun réseau, AUCUN accès au matériel (ni /dev, ni port série).
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_ate_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, maths, programme, recompenses  # noqa: E402
from tg import atelier as A, bestiaire as B, guide  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("atelier", "from tg import atelier; sys.exit(atelier.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
for nom in ("sudo", "curl", "wget", "arduino-cli", "esptool.py", "screen", "gpioset", "pinctrl", "minicom"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
    (DOUBLURES / nom).chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd, vrai=None):
    """L'enfant tape cmd (c'est ce que voit le jeu) ; vrai : ce qui est vraiment lancé (Ctrl+C simulé par timeout)."""
    r = subprocess.run(["bash", "-c", (vrai or cmd) + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True,
                       text=True, errors="replace", timeout=240, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
        lignes = lignes[:-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)
    return st, "\n".join(lignes) + r.stderr


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == T or T in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


langue.definir("fr")
D = A.donnees()
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_atelier.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/atelier/vecteurs.json)" + (" " + r.stdout[-300:] if r.returncode else ""))
DR = lambda d: "droite" if d < 10 else "avance"   # noqa: E731
GA = lambda d: "gauche" if d < 10 else "avance"   # noqa: E731


def bilan(cle, cerveau):
    p = A.simuler(cle, cerveau, D["defi"]["pas"])
    vus = {(A.depart(cle)["x"], A.depart(cle)["y"])} | {(r_["x"], r_["y"]) for r_, _e, _d in p}
    return A.verdict(len(vus), sum(1 for _r, e, _d in p if e == "choc"), len(p))


for i in range(len(D["arenes"])):
    verifier((bilan(i, DR), bilan(i, GA), bilan(i, lambda d: "avance"), bilan(i, lambda d: "stop" if d < 10 else "avance"))
             == ("ok", "ok", "choc", "peu"), f"arène {i + 1} : tourner réussit (droite et gauche), foncer se cogne, s'arrêter ne suffit pas")
verifier(A.verdict(12, 0, 20) == "ok" and A.verdict(11, 0, 20) == "peu" and A.verdict(3, 1, 4) == "choc"
         and A.verdict(12, 0, 19) == "en_cours", "le verdict : 12 cases sans choc en 20 pas")
gardiens = set(recompenses.gardiens().values())
m = next(x for x in recompenses.mondes() if x["id"] == "atelier")
autres = {v for x in recompenses.mondes() if x["id"] != "atelier" for v in x.get("variantes_reservees", [])}
ok_var = True
for v in m["variantes_reservees"]:
    eid, vid = v.split(":")
    e = B.espece(eid)
    ok_var &= bool(e) and any(x["id"] == vid for x in e["variantes"]) and guide.type_de(e, vid) in ("machine", "plante") \
        and eid not in gardiens and v not in autres
verifier(ok_var and len(m["variantes_reservees"]) == 3, f"variantes réservées EXISTANTES, Machine ou Plante, ni gardiens ni déjà réservées : {m['variantes_reservees']}")
verifier(m.get("chapitre") == "robots" and histoire.PAR_CHAP["robots"]["piece"] == "robots" and histoire.PAR_CHAP["atelier"]["piece"] == "atelier",
         "le lieu s'appelle robots : l'aile « atelier » (les Constructs) reste à sa place")
L = programme.donnees()["maths"]["logique"]
verifier(L.get("fiche") and L["exercice"]["type"] == "logique", "le Pont des Nombres « logique » a sa fiche (ET, OU, NON)")
ecarts = []
for k in range(12):
    p_, rep_, verif_ = maths.generer("logique", 20261101, k)
    s_ = subprocess.run(["bash", "-c", verif_], capture_output=True, text=True).stdout.strip()
    if s_ != rep_ or rep_ != str(int(p_["a"]) & int(p_["b"])):
        ecarts.append((p_, rep_, s_))
verifier(not ecarts, f"l'exercice « logique » : la réponse du jeu = celle de bash $(( a && b )) {ecarts[:2]}")
for g in ("1:0", "2:1730000000"):
    v_, ms_, cm_ = A.reflexe(g)
    s_ = subprocess.run(["bash", "-c", f"echo $(( {v_} * {ms_} / 1000 ))"], capture_output=True, text=True).stdout.strip()
    verifier(s_ == str(cm_), f"le réflexe : {v_} cm/s × {ms_} ms = {cm_} cm (bash : {s_})")
tb = subprocess.run(["bash", "-c", "for a in 0 1; do for b in 0 1; do echo -n $(( a && b )) $(( a || b )) ''; done; done"],
                    capture_output=True, text=True).stdout.split()
verifier(tb[0::2] == A.table_verite("et") and tb[1::2] == A.table_verite("ou"), f"les tables de vérité ET et OU = bash {tb}")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "robots"), f"fermé au début (il manque {A.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"][:len(chaps) - 1]
    h["chap"] = chaps[-1]
    h.setdefault("mondes_annonces", []).extend(m_ for m_ in histoire.MONDES_MODS if m_ != "robots")
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid")))
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "robots"), f"sans le niveau 3-4 : toujours fermé (il manque {A.manque(st)})")
core.modifier(ouvrir)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "robots"), "le niveau 4 fait : l'Atelier s'ouvre")
st, _ = tape("ls")
verifier("robots" in st["histoire"].get("mondes_annonces", []), "annoncé une fois (une nouvelle à la fois)")
DD = T / "robots"
verifier((DD / "plan_de_l_atelier.txt").is_file() and (DD / A.CARNET).is_file() and (DD / "cerveau_exemple.sh").is_file()
         and all((DD / "robot" / f).is_file() for f in A.FICHIERS), "l'Atelier est meublé (plan, carnet, cerveau d'exemple, robot/)")
verifier((DD / "robot" / "led").read_text() == "0\n" and (DD / "robot" / "capteur_distance").read_text() == "60\n",
         "la LED est éteinte, le capteur voit 60 cm (6 cases libres devant le robot)")

print("3. La traversée de l'Atelier, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/robots")
verifier(lecon(st) == ("at0", 1), f"entrer dans l'Atelier choisit le monde : {lecon(st)}")
sorties = {}
WHILE = "while true; do cat robot/capteur_distance; sleep 1; done"


def g():
    return A._graine(core.load())


def robot():
    return A.a_(core.load())["robot"]


def malin(sens="droite", seuil="10"):
    txt = A.cerveau_malin().replace("droite", sens).replace("-lt 10", f"-lt {seuil}")
    return "printf '%s' " + shlex.quote(txt) + " > cerveau.sh"


PARCOURS = [
    "ls", "cat plan_de_l_atelier.txt",
    "ls robot", "cat robot/led", "echo 1 robot/led", "echo 2 > robot/led", "echo 1 > robot/led", "atelier robot",
    "echo 0 > robot/led", "cat robot/capteur_distance",
    "atelier grille", "echo recule > robot/moteur", "echo avance > robot/moteur", "atelier pas", "atelier ou 1 2",
    lambda: f"atelier ou {robot()['x']} {robot()['y']}", "echo droite > robot/moteur", "atelier pas", "atelier cases 30",
    lambda: f"atelier cases {A.capteur_de(core.load()) // 10}",
    "atelier logique", "[ 5 -lt 10 ] && echo vrai || echo faux",
    'd=$(cat robot/capteur_distance); if [ "$d" -lt 10 ]; then echo obstacle; else echo libre; fi',
    "atelier verite", "atelier verite ? ? ? ?", "atelier verite 1 1 1 1",
    lambda: "atelier verite " + " ".join(A.table_verite(A.porte(g()))),
    "atelier choix", lambda: "atelier choix " + " ".join({"et": "ou", "ou": "non", "non": "et"}[r_] for _n, _i, r_ in A.choix_cartes(g())),
    lambda: "atelier choix " + " ".join(r_ for _n, _i, r_ in A.choix_cartes(g())),
    "for i in 1 2 3; do cat robot/capteur_distance; sleep 1; done", WHILE,
    "cat cerveau_exemple.sh", "cp cerveau_exemple.sh cerveau.sh", "atelier essai",
    "for i in $(seq 10); do sh cerveau.sh; done", "for i in $(seq 10); do sh cerveau.sh; atelier pas; done",
    "atelier aide-cerveau", "nano cerveau.sh",
    "atelier defi", "for i in $(seq 20); do sh cerveau.sh; atelier pas; done",
    "atelier defi", lambda: malin("stop"), "for i in $(seq 20); do sh cerveau.sh; atelier pas; done",
    "atelier defi", lambda: malin("gauche"), "for i in $(seq 20); do sh cerveau.sh; atelier pas; done",
    "atelier pi", "ls /sys/class/leds", "command -v gpioset pinctrl", "atelier gpio", "atelier autonome",
    "tail -5 robot/journal.txt", "crontab -l",
    "atelier embarque", "time sh cerveau.sh", "atelier reflexe", "atelier reflexe 1",
    lambda: f"atelier reflexe {A.reflexe(g())[2]}", "atelier arduino", "command -v arduino-cli esptool.py", "atelier telephone",
]
vus = []
nano_fait = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    vrai = None
    if c == WHILE:
        vrai = "timeout -s INT 2 bash -c " + shlex.quote(c)        # Ctrl+C au bout de 2 secondes (un vrai SIGINT)
    if c == "nano cerveau.sh":                                     # l'enfant écrit son cerveau dans l'éditeur…
        vrai = malin("droite", "0") if not nano_fait else malin()   # (d'abord une condition qui ne tourne jamais à temps)
        nano_fait.append(1)
    st, s = tape(c, vrai)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st), st.get("indice_lecon")))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[-int(os.environ.get('TG_LARGE', '110')):]!r}")
    if histoire.fini(st, "robots"):
        break
if not histoire.fini(st, "robots"):
    for a_, c, b, ind in vus[-8:]:
        print("     ", a_, c, "→", b, ind)
verifier(histoire.fini(st, "robots"), f"l'Atelier est traversé jusqu'au bout (at0 → at7) {lecon(st)}")


def passage(cmd):
    return [(a_, b, ind) for a_, c, b, ind in vus if c == cmd]


verifier(passage("echo 2 > robot/led")[0][0] == passage("echo 2 > robot/led")[0][1] and "0 ou 1" in (passage("echo 2 > robot/led")[0][2] or ""),
         "une LED à 2 : l'étape attend, l'indice dit « 0 ou 1 »")
verifier(passage("echo 1 robot/led")[0][0] == passage("echo 1 robot/led")[0][1], "echo sans > : la LED ne change pas, l'étape attend")
o = ANSI.sub("", sorties.get("atelier robot", ""))
verifier("💡" in o and "allumée" in o, "atelier robot dessine la LED allumée")
verifier(passage("echo recule > robot/moteur")[0][0] == passage("echo recule > robot/moteur")[0][1],
         "le moteur ne comprend pas « recule » : l'étape attend")
o = ANSI.sub("", sorties.get("for i in $(seq 10); do sh cerveau.sh; atelier pas; done", ""))
verifier("CHOC" in o, "le cerveau d'exemple fonce tout droit : 💥 CHOC dans la grille d'essai")
verifier(passage("for i in $(seq 10); do sh cerveau.sh; done")[0][2] and "atelier pas" in passage("for i in $(seq 10); do sh cerveau.sh; done")[0][2],
         "une boucle sans `atelier pas` : l'indice dit qu'il faut le pas du monde")
defis = [ANSI.sub("", s_) for c_, s_ in sorties.items() if c_.startswith("for i in $(seq 20)")]
carnet = A.carnet()
verifier(re.findall(r"^\[defi\] .*\((\w+)\)$", carnet, re.M)[:3] == ["choc", "peu", "ok"],
         f"trois défis : le cerveau « trop tard » se cogne, celui qui s'arrête n'explore pas assez, celui qui tourne réussit {re.findall(r'^\[defi\] .*', carnet, re.M)}")
verifier("atelier.robot" in recompenses.r_(st)["exploits"], "l'exploit « un robot qui évite tous les obstacles »")
verifier(not recompenses.reservee(st, {"id": "tisonnier"}, "mecanique") and recompenses.reservee({}, {"id": "tisonnier"}, "mecanique")
         and recompenses.reservee({}, {"id": "groinfer"}, "rouille") and recompenses.reservee({}, {"id": "lampignon"}, "forêt")
         and not recompenses.reservee({}, {"id": "tisonnier"}, "rouille"),
         "tisonnier:mecanique, groinfer:rouille, lampignon:forêt n'apparaissent qu'après l'exploit ; tisonnier:rouille reste libre")
j = (DD / "robot" / "journal.txt").read_text(encoding="utf-8").splitlines()
verifier(len(j) >= 70 and j[-1].startswith("pas ") and "capteur=" in j[-1], f"le journal du robot : une ligne par pas ({len(j)})")
o = ANSI.sub("", sorties.get("tail -5 robot/journal.txt", ""))
verifier(o.strip().splitlines() == j[-5:] if o.strip() else False, "tail -5 robot/journal.txt : les 5 derniers pas")
verifier("robot_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "roboticien",
         "récompenses : le robot miniature (posé, jamais porté) et le titre de Roboticien")
verifier("1 2 (faux)" in carnet and "1 1 1 1 (faux)" in carnet, "les mauvaises réponses sont notées (faux), sans bloquer")
o = ANSI.sub("", sorties.get("atelier arduino", ""))
verifier("arduino-cli" in o and "/dev/ttyUSB0" in o and "adulte" in o and "RIEN" in o, "atelier arduino raconte (avec un adulte), le jeu ne fait rien")

print("4. Les indices")
pas_ = {s_["cmd"]: s_ for l_ in A.LECONS.values() for s_ in l_["steps"]}
verifier(A.indice(pas_["atelier ou ?"], [("atelier ou ?", None)]) == langue.t("at.indice.trou"), "« ? » recopié : un trou à remplir")
A.noter("ou", "9 9 (faux)")
verifier(A.indice(pas_["atelier ou ?"], [("atelier ou 9 9", None)]) == langue.t("at.indice.ou"), "une mauvaise réponse : l'indice")
verifier(A.indice(pas_["echo 1 > robot/led"], [("sudo gpioset gpiochip0 17=1", None)]) == langue.t("at.indice.materiel"),
         "sudo / gpioset : le jeu ne touche jamais au vrai matériel")
verifier(A.indice(pas_["atelier embarque"], [("screen /dev/ttyUSB0 115200", None)]) == langue.t("at.indice.materiel"),
         "screen /dev/ttyUSB0 : l'indice du vrai matériel")
st2 = core.load()
c2 = A.a_(st2)
c2["faits"] = [x for x in c2["faits"] if x != "garde:materiel"]
verifier(A.surveiller(st2, ["arduino-cli upload -p /dev/ttyACM0"]) and "adulte" in ANSI.sub("", " ".join(map(str, st2.get("terminal", [])))),
         "surveillance : arduino-cli upload → la créature rappelle « avec un adulte »")
verifier(not A.surveiller(st2, ["esptool.py --port /dev/ttyUSB0 write_flash 0 x.bin"]), "… une seule fois")

print("5. La vue déployée : le robot")
l_ = "echo 1 > robot/led"
txt = ANSI.sub("", "\n".join(deploie.ecran(l_, deploie.blocs(l_), 1, None, 0.5, 100)))
verifier("le robot" in txt and "la LED" in txt and "💡" in txt, "echo 1 > robot/led : on écrit un ordre à la LED")
x = deploie.robots("for i in $(seq 20); do sh cerveau.sh; atelier pas; done")
verifier([(y["piece"], y["sens"]) for y in x] == [("cerveau", "pense"), ("roues", "bouge")], f"la boucle : le cerveau décide, les roues bougent {x}")

print("6. Sécurité")
verifier(fichiers_hors_terrain() - AVANT <= {str(HOME / ".bash_history"), str(HOME / ".terminagotchi.json")}
         or all("terminagotchi" in p or p.endswith(".bash_history") for p in fichiers_hors_terrain() - AVANT),
         f"rien d'écrit hors du terrain ({sorted(fichiers_hors_terrain() - AVANT)[:4]})")
verifier(not JOURNAL.exists(), "aucun sudo, aucun réseau, aucun arduino-cli / esptool / screen / gpioset lancé")
src = (RACINE / "pc/tg/atelier.py").read_text(encoding="utf-8")
verifier(not re.search(r"open\([^)]*/dev|serial|subprocess|os\.system|urllib|socket|requests", src.split('"""', 2)[2]),
         "le module ne lance rien, n'ouvre aucun /dev, aucun port série, aucun réseau")
verifier(all(not re.search(r"(^|\s)sudo\s", s_["cmd"]) for s_ in pas_.values()), "aucune étape ne demande sudo")

print("7. Les commandes du téléphone : les shells (dash, mksh, busybox sh) et les outils (toybox, busybox) écrivent comme bash")
import shutil  # noqa: E402
tmp = Path(tempfile.mkdtemp(prefix="tg_ate_tel_"))
(tmp / "robot").mkdir()
(tmp / "robot" / "led").write_text("1\n")
(tmp / "robot" / "capteur_distance").write_text("30\n")
(tmp / "robot" / "journal.txt").write_text("".join(f"pas {k}\n" for k in range(1, 9)))
(tmp / "cerveau.sh").write_text(A.cerveau_malin())
SHELL_CMDS = ["cat robot/led", "[ 5 -lt 10 ] && echo vrai || echo faux",
              'd=$(cat robot/capteur_distance); if [ "$d" -lt 10 ]; then echo obstacle; else echo libre; fi',
              "for i in 1 2 3; do cat robot/capteur_distance; done", "sh cerveau.sh && cat robot/moteur",
              "echo 0 > robot/capteur_distance && sh cerveau.sh && cat robot/moteur && echo 30 > robot/capteur_distance",
              "echo $(( 1 && 0 )) $(( 1 || 0 )) $(( !1 ))"]


def sortie_de(argv, cmd):
    return subprocess.run(argv + [cmd], cwd=tmp, capture_output=True, text=True, timeout=30, env=ENV).stdout


ref = {c: sortie_de(["bash", "-c"], c) for c in SHELL_CMDS}
vus_sh = 0
for nom, argv in (("dash", ["dash", "-c"]), ("mksh", ["mksh", "-c"]), ("busybox sh", ["busybox", "sh", "-c"])):
    if not shutil.which(argv[0]):
        print(f"  · {nom} absent (comparé en CI quand il est installé)")
        continue
    vus_sh += 1
    ecarts = [c for c in SHELL_CMDS if sortie_de(argv, c) != ref[c]]
    verifier(not ecarts, f"{nom} : les {len(SHELL_CMDS)} lignes du téléphone écrivent comme bash {ecarts[:2]}")
OUTILS = [("tail", "tail -5 robot/journal.txt"), ("seq", "seq 3"), ("cat", "cat robot/capteur_distance")]
for boite in ("toybox", "busybox"):
    if not shutil.which(boite):
        print(f"  · {boite} absent (comparé en CI)")
        continue
    ecarts = [c for _o, c in OUTILS if sortie_de(["sh", "-c"], f"{boite} {c}") != sortie_de(["sh", "-c"], c)]
    verifier(not ecarts, f"{boite} : tail, seq, cat écrivent comme les outils GNU {ecarts}")
verifier(ref["sh cerveau.sh && cat robot/moteur"].strip() == "avance" and
         "droite" in ref["echo 0 > robot/capteur_distance && sh cerveau.sh && cat robot/moteur && echo 30 > robot/capteur_distance"],
         "le cerveau malin : avance à 30 cm, tourne à 0 cm (un vrai sh)")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
