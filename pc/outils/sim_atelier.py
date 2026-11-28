"""Trois enfants traversent l'Atelier (phase 5, at0 → at7), dans un VRAI shell resté ouvert —
docs/simulations/rapport_atelier.md.

    python3 pc/outils/sim_atelier.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_atelier.py lea        (un seul : lea, ines ou hugo)

Comme sim_donnees.py : le shell est pc/tg/coquille.py (un vrai bash qui reste ouvert : les variables, la boucle for et
Ctrl+C sont les vrais), l'enfant ne lit que la commande montrée et ce que le jeu écrit dans SON terminal. L'Atelier est
ouvert d'avance (niveaux 0 à 4 faits). sudo, curl, wget, arduino-cli, esptool.py, screen et gpioset sont des
doublures qui refusent (et notent qu'on les a appelées). La boucle infinie est arrêtée par un vrai Ctrl+C (SIGINT).
  - Léa, 7 ans : se trompe d'abord (une majuscule, echo sans >, une LED à 2, un moteur « marche », x et y inversés, les
    centimètres au lieu des cases, une table de vérité au hasard, « et » partout, la boucle sans `atelier pas`, un
    cerveau sans condition, le défi lancé avec le cerveau d'exemple qui se cogne, le réflexe sans diviser par 1000) ;
    puis lit l'écran et corrige. Elle écrit son cerveau en recopiant `atelier aide-cerveau`.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris), puis lit l'écran pour remplir ; son premier
    cerveau s'arrête devant l'obstacle (stop) : le défi dit qu'elle n'explore pas assez, elle le change pour tourner.
  - Hugo, 15 ans : ses variantes (`printf 1 > robot/led`, `cat ./robot/led`, `ls -l robot`, `for i in {1..3}`,
    `while :`, `time bash cerveau.sh`, `which gpioset`…) et SON cerveau (tourne à gauche, `-le 5`).
Vérifie : l'Atelier fini ; l'exploit « le robot qui évite tous les obstacles » ; aucune étape validée par une commande
qui a échoué ; chaque faute de Léa reçoit une explication ; rien hors du terrain ; aucun vrai matériel appelé.
"""
import builtins
import os
import random
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nAtelier : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_ate_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, atelier as A  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("atelier", "from tg import atelier; sys.exit(atelier.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
for nom in ("sudo", "curl", "wget", "arduino-cli", "esptool.py", "screen", "gpioset", "pinctrl", "minicom"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (simulation) refusé' >&2\nexit 1\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")
random.seed({"lea": 1, "ines": 2, "hugo": 3}[QUI])


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(m for m in histoire.MONDES_MODS if m != "robots")
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0
    s["partie"] = {"lea": 1, "ines": 2, "hugo": 3}[QUI]


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == core.TERRAIN or core.TERRAIN in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


core.modifier(ouvrir)
core.TERRAIN.mkdir(exist_ok=True)
AVANT = fichiers_hors_terrain()
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C"))
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
INV = {v: k for k, v in HOMO.items()}
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + f"[{QUI}] " + m)


def propre(x):
    x = langue.sans_marques(ANSI.sub("", x))
    return "".join(INV.get(c, c) for c in x).replace(NBSP, " ")


etat = {"sortie": "", "code": 0, "terminal": []}
journal = []
memoire = {}


def tape(cmd):
    infini = cmd.startswith("while true") or cmd.startswith("while :")
    # la boucle infinie : Ctrl+C au bout de 2 secondes (un vrai SIGINT, à la boucle elle-même : dans un shell non interactif,
    # le SIGINT envoyé seulement au `sleep` ne l'arrêterait pas, alors qu'au clavier Ctrl+C arrête toute la ligne)
    vrai = ("timeout -s INT 2 bash -c " + shlex.quote(cmd)) if infini else cmd
    etat["sortie"], etat["code"], d = SH.lancer(vrai, delai=240)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    if os.environ.get("TG_DEBUG"):
        print("   ", journal[-1][:4], propre(etat["sortie"])[-120:].replace("\n", "⏎"), flush=True)
    memoire.pop(cmd, None)
    memoire[cmd] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def ecrire(texte):
    """L'enfant écrit son fichier dans l'éditeur (ici : printf, la même chose sur le disque)."""
    return "printf '%s' " + shlex.quote(texte) + " > cerveau.sh"


def lignes_aide(st):
    """Les lignes du cerveau, recopiées de l'écran d'`atelier aide-cerveau`."""
    if not lu("atelier aide-cerveau"):
        st = tape("atelier aide-cerveau")
    return st, "\n".join(l[4:] for l in lu("atelier aide-cerveau").splitlines() if l.startswith("    ")) + "\n"


CERVEAU_HUGO = 'd=$(cat robot/capteur_distance)\nif [ "$d" -le 5 ]; then\n  echo gauche > robot/moteur\nelse\n  echo avance > robot/moteur\nfi\n'
CERVEAU_STOP = 'd=$(cat robot/capteur_distance)\nif [ "$d" -lt 10 ]; then\n  echo stop > robot/moteur\nelse\n  echo avance > robot/moteur\nfi\n'


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "atelier ou ?":
        st = tape("atelier grille")
        m = re.search(r"x=(\d+) y=(\d+)", lu("atelier grille"))
        return st, f"atelier ou {m.group(1)} {m.group(2)}" if m else cmd
    if cmd == "atelier cases ?":
        m = re.findall(r"capteur : (\d+) cm", lu("atelier pas"))
        return st, f"atelier cases {int(m[-1]) // 10 if m else '?'}"
    if cmd == "atelier verite ? ? ? ?":
        s = memoire.get("atelier verite", "")
        et = " ET " in s or "porte ET" in s
        return st, "atelier verite " + ("0 0 0 1" if et else "0 1 1 1")
    if cmd == "atelier choix ? ? ?":
        reps = []
        for l in memoire.get("atelier choix", "").splitlines():
            if re.match(r"^\s*\d\.", l):
                reps.append("et" if "les deux" in l else "ou" if "une seule" in l else "non" if "contraire" in l else "?")
        return st, "atelier choix " + " ".join(reps)
    if cmd == "atelier reflexe ?":
        s = memoire.get("atelier reflexe", "")
        v, ms = re.search(r"(\d+) cm par seconde", s), re.search(r"(\d+) millisecondes", s)
        return st, f"atelier reflexe {int(v.group(1)) * int(ms.group(1)) // 1000}" if v and ms else cmd
    if cmd == "nano cerveau.sh":
        if QUI == "hugo":
            return st, ecrire(CERVEAU_HUGO)
        st, texte = lignes_aide(st)
        return st, ecrire(texte)
    return st, cmd


def faute(cmd):
    """Les fautes de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd == "echo 1 > robot/led":
        return ["echo 1 robot/led", "echo 2 > robot/led"]
    if cmd == "echo avance > robot/moteur":
        return ["echo marche > robot/moteur"]
    if cmd == "atelier ou ?":
        r = A.a_(core.load())["robot"]
        return [f"atelier ou {r['y']} {r['x']}"] if r["x"] != r["y"] else None     # x et y inversés
    if cmd == "atelier cases ?":
        m = re.findall(r"capteur : (\d+) cm", lu("atelier pas"))
        return [f"atelier cases {m[-1] if m else 30}"]                              # les centimètres
    if cmd == "atelier verite ? ? ? ?":
        return ["atelier verite 1 1 1 1"]
    if cmd == "atelier choix ? ? ?":
        return ["atelier choix et et et"]
    if cmd.startswith("for i in $(seq 10)"):
        return ["for i in $(seq 10); do sh cerveau.sh; done"]
    if cmd == "nano cerveau.sh":
        return [ecrire("echo droite > robot/moteur\n")]                             # pas de condition
    if cmd.startswith("for i in $(seq 20)"):
        return None
    if cmd == "atelier reflexe ?":
        s = memoire.get("atelier reflexe", "")
        v, ms = re.search(r"(\d+) cm par seconde", s), re.search(r"(\d+) millisecondes", s)
        return [f"atelier reflexe {int(v.group(1)) * int(ms.group(1))}"] if v and ms else None
    if re.match(r"^(cat|ls)\b", cmd):
        return [cmd[0].upper() + cmd[1:]]
    return None


def variante(cmd):
    regles = [
        (r"^ls robot$", "ls -l robot"), (r"^cat robot/led$", "cat ./robot/led"), (r"^echo 1 > robot/led$", "printf 1 > robot/led"),
        (r"^echo 0 > robot/led$", "printf '0\\n' > robot/led"), (r"^cat robot/capteur_distance$", "head -1 robot/capteur_distance"),
        (r"^echo droite > robot/moteur$", "echo right > robot/moteur"),
        (r"^for i in 1 2 3;", "for i in {1..3}; do cat robot/capteur_distance; sleep 1; done"),
        (r"^while true", "while :; do cat robot/capteur_distance; sleep 1; done"),
        (r"^cp cerveau_exemple", "cp -v cerveau_exemple.sh cerveau.sh"),
        (r"^time sh cerveau", "time bash cerveau.sh"), (r"^command -v gpioset", "which gpioset pinctrl"),
        (r"^tail -5 robot/journal", "tail -n 5 robot/journal.txt"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees, defis = [], [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "robots"), "l'Atelier devrait être ouvert (niveaux 0 à 4 faits)"
st = tape("cd ~/terrain_terminagotchi/robots")
cerveau_ines = []
for _ in range(int(os.environ.get("TG_TOURS", "400"))):
    if histoire.fini(st, "robots"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("at"):
        st = tape("cd ~/terrain_terminagotchi/robots")
        continue
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        st = tape(idees[0])
        continue
    step = les["steps"][st["step"]]
    avant = (les["id"], st["step"])
    a_taper = montree(st, step)
    derniere = a_taper[-1]
    premiere_fois = avant not in tentes
    tentes.add(avant)
    essais = []
    if premiere_fois:
        if QUI == "lea" and faute(derniere):
            essais += faute(derniere)
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.split():
            essais.append(derniere)                                # recopie les « ? »
    if derniere.startswith("for i in $(seq 20)"):                 # le défi : le cerveau qu'il a, puis on regarde
        st = tape(derniere)
        v = re.findall(r"^\[defi\] .*\((\w+)\)$", A.carnet(), re.M)
        defis.append(v[-1] if v else "?")
        les2, _ = histoire.lecon_courante(st)
        if ((les2["id"], st["step"]) if les2 else None) == avant:
            st, texte = lignes_aide(st)                            # raté : on relit l'aide, on corrige, on relance
            st = tape(ecrire(texte if QUI != "hugo" else CERVEAU_HUGO))
            st = tape("atelier defi")
        continue
    if derniere == "atelier defi" and QUI == "ines" and not cerveau_ines:     # Inès : son cerveau s'arrête devant l'obstacle
        cerveau_ines.append(1)
        st = tape(ecrire(CERVEAU_STOP))
    if derniere == "atelier defi" and QUI == "lea" and premiere_fois:          # Léa : elle remet le cerveau d'exemple…
        st = tape("cp cerveau_exemple.sh cerveau.sh")
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "✋" not in propre(etat["sortie"]):
            sans_explication.append((avant, essai, propre(etat["sortie"])[:80]))
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    st, derniere = resoudre(derniere, st)
    st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "robots"), f"l'Atelier traversé, at0 → at7 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("atelier.robot" in ex, f"l'exploit « le robot qui évite tous les obstacles » (défis : {defis})")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(not appels, f"aucun sudo, aucun téléchargement, aucun vrai matériel ({appels[:60]!r})")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute de Léa reçoit une explication {sans_explication[:3]}")
    verifier(defis[:1] == ["choc"] and defis[-1] == "ok", f"Léa : le cerveau d'exemple se cogne, puis le sien réussit {defis}")
if QUI == "ines":
    verifier(defis[:1] == ["peu"] and defis[-1] == "ok", f"Inès : son robot s'arrête (pas assez de cases), puis tourne et réussit {defis}")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 10 and not variantes_refusees, f"Hugo : ses variantes justes acceptées ({len(variantes_ok)}) ; refusées {variantes_refusees}")
    verifier(defis == ["ok"], f"Hugo : son cerveau (gauche, -le 5) réussit du premier coup {defis}")
print(f"[{QUI}] {ok} réussis, {ko} échoués — {len(journal)} lignes ; refusées : {variantes_refusees}")
SH.fermer()
sys.exit(1 if ko else 0)
