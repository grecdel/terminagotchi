"""Trois enfants traversent la Salle des Rouages (phase 5, sm0 → sm10), dans un VRAI shell resté ouvert —
docs/simulations/rapport_machines.md.

    python3 pc/outils/sim_machines.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/sim_machines.py lea        (un seul : lea, ines ou hugo)

Comme sim_crypte.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. La Salle est ouverte d'avance (niveaux 0 à 3 du tronc commun finis).
  - Léa, 7 ans : se trompe d'abord (une majuscule, `sudo dmesg`, le « ? » recopié, une virgule dans la mémoire, de
    mauvais interrupteurs, les cartes du réveil dans l'ordre A B C D E, tar à l'envers, la copie au mauvais endroit, la
    panne déclenchée trop tôt, une machine dont la prise ne va pas au premier démarrage) ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`lscpu`, `cat /proc/meminfo`, `df -h`, `printf A | od`, `wc -c`, `uname -a`,
    `command -v ls`, `bash …`, `tar -czf`, `cp sauvegarde.* …`, `sha256sum --check`…).
Pour les trous : les cœurs et la mémoire sont LUS dans la sortie de nproc et free -h ; la lettre du défi dans l'écran
des interrupteurs ; les cartes du réveil, l'orchestre et les boîtes d'après leurs textes (puis les ✔) ; la machine
montée d'après le catalogue et les règles affichées ; le drapeau dans l'écran du démarrage.
Vérifie : la Salle finie ; l'exploit « premier démarrage » seulement si le premier démarrage a réussi ; aucune étape
validée par une commande qui a échoué ; chaque faute de Léa reçoit une explication ; les variantes justes de Hugo
acceptées ; rien hors du terrain ; le prénom tapé n'est gardé nulle part. Code de sortie 1 en cas d'échec.
"""
import builtins
import itertools
import json
import os
import re
import shutil
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
    print(f"\nSalle des Rouages : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
PRENOM = {"lea": "Léa", "ines": "Inès", "hugo": "Hugo"}[QUI]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_mac_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, machines as M  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
# `machines …` : l'alias machines='tg machines' posé par tg installer (le jeu le connaît comme commande, core.BUILTINS)
(DOUBLURES / "machines").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                    "from tg import machines; machines.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (simulation) refusé' >&2\nexit 1\n")
if not shutil.which("xxd"):
    (DOUBLURES / "xxd").write_text(
        f"#!{sys.executable}\nimport sys\na = [x for x in sys.argv[1:] if not x.startswith('-')]\n"
        "d = open(a[0], 'rb').read() if a else sys.stdin.buffer.read()\n"
        "if '-b' in sys.argv:\n"
        "    for i in range(0, len(d), 6):\n"
        "        x = d[i:i + 6]; s = ' '.join(format(b, '08b') for b in x)\n"
        "        print('%08x: ' % i + s.ljust(54) + ' ' + ''.join(chr(b) if 32 <= b < 127 else '.' for b in x))\n"
        "else:\n    [print('%08x: ' % i + d[i:i + 16].hex(' ', 2)) for i in range(0, len(d), 16)]\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = "bibliotheque"
    h.setdefault("mondes_annonces", []).extend(["port", "crypte"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


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
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8"))
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
journal = []          # (leçon, étape, commande, code, lu) : la partie entière, pour le rapport
memoire = {}


def tape(cmd):
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=120)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    memoire[cmd] = propre(etat["sortie"])
    memoire[cmd.split()[0] if cmd.split() else ""] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip() for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip() for p in parts if p]


def lu(prefixe):
    """La dernière sortie lue d'une commande qui commence par prefixe."""
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


MOTS_REVEIL = [("micrologiciel", 1), ("chargeur", 2), ("noyau prend", 3), ("premier programme", 4), ("session", 5)]
MOTS_ORCH = [("écran", "pilotes"), ("partager", "ordonnanceur"), ("place", "gardien de la mémoire"), ("retrouver", "système de fichiers"),
             ("empêcher", "gardien des droits")]
MOTS_RANGE = [("noyau", "v"), ("copies", "c"), ("douteux", "v"), ("emporter", "c")]


def solveur(besoin):
    """La machine que l'enfant compose d'après le catalogue et les règles affichées (essais patients, sans tricher :
    les règles sont celles de l'écran ; la vérification est celle que fera le démarrage)."""
    cat = M.donnees()["catalogue"]
    for combo in itertools.product(*[[x["id"] for x in cat[c]] for c in M.donnees()["categories"]]):
        if not M.montage(list(combo), besoin)["problemes"]:
            return list(combo)
    return None


def besoin_lu():
    s = memoire.get("machines monte") or lu("machines demarre") or lu("machines monte P")
    for b, mot in (("jouer", "JOUER"), ("dessiner", "DESSINER"), ("serveur", "SERVEUR"), ("robot", "ROBOT"), ("ecole", "école")):
        if mot in s:
            return b
    return "ecole"


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "machines coeurs ?":
        s = lu("nproc") or lu("lscpu")
        if not re.search(r"\d", s):
            st = tape("nproc")
            s = propre(etat["sortie"])
        m = re.search(r"^CPU\(s\):\s*(\d+)", s, re.M)     # lscpu : la ligne « CPU(s): » (pas le dernier nombre de
        n = m.group(1) if m else (re.findall(r"(\d+)", s) or ["1"])[-1]   # l'écran : sur la CI, « … 112 » plus bas)
        return st, f"machines coeurs {n}"
    if cmd == "machines memoire ?":
        s = lu("free")
        m = re.search(r"^Mem:\s+(\S+)", s, re.M)
        if not m:
            st = tape("free -h")
            m = re.search(r"^Mem:\s+(\S+)", propre(etat["sortie"]), re.M)
        v = m.group(1) if m else "1"
        return st, f"machines memoire {v.replace('.', ',') if QUI == 'lea' else v}"
    if cmd == "machines interrupteurs ?":
        return st, f"machines interrupteurs {PRENOM}"
    if cmd == "machines allume ?":
        m = re.search(r"lettre ([A-Z])", lu("machines interrupteurs"))
        return st, "machines allume " + format(ord(m.group(1) if m else "A"), "08b")
    if cmd == "machines reveil ? ? ? ? ?":
        if "machines reveil" not in memoire:
            st = tape("machines reveil")
        cartes = re.findall(r"^\s+([A-E])\s+(.*)$", memoire["machines reveil"], re.M)
        rang = {l: next((r for mot, r in MOTS_REVEIL if mot in txt), 9) for l, txt in cartes}
        return st, "machines reveil " + " ".join(sorted(rang, key=rang.get))
    if cmd == "machines orchestre ? ? ? ? ?":
        if "machines orchestre" not in memoire:
            st = tape("machines orchestre")
        s = memoire["machines orchestre"]
        mus = dict((txt, l) for l, txt in re.findall(r"^\s+([A-E]) (.*)$", s, re.M))
        taches = re.findall(r"^\s+\d\. (.*)$", s, re.M)
        rep = []
        for tache in taches:
            cle = next((m for mot, m in MOTS_ORCH if mot in tache.lower()), "")
            rep.append(next((l for txt, l in mus.items() if cle in txt), "A"))
        return st, "machines orchestre " + " ".join(rep)
    if cmd == "machines range ? ? ? ?":
        if "machines range" not in memoire:
            st = tape("machines range")
        apps = re.findall(r"^\s+\d\. (.*)$", memoire["machines range"], re.M)
        return st, "machines range " + " ".join(next((r for mot, r in MOTS_RANGE if mot in a.lower()), "c") for a in apps)
    if cmd in ("machines monte 1 ? ? ? ? ? ?", "machines monte ? ? ? ? ? ?"):
        un = "1" in cmd.split()
        if not lu("machines monte" + (" 1" if un else "")):
            st = tape("machines monte 1" if un else "machines monte")
        sol = solveur("ecole" if un else besoin_lu())
        return st, "machines monte " + ("1 " if un else "") + " ".join(sol)
    if cmd == "machines drapeau ?":
        m = re.search(r"(TG\{[^}]+\})", lu("machines demarre"))
        return st, f"machines drapeau {m.group(1) if m else 'TG{?}'}"
    return st, cmd


def faute(cmd, st):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    fautes = {"nproc": "Nproc", "free -h": "Free -h", "dmesg | head -5": "sudo dmesg | head -5",
              "machines coeurs ?": "machines coeurs ?", "machines allume ?": "machines allume 11110000",
              "machines reveil ? ? ? ? ?": "machines reveil A B C D E", "machines orchestre ? ? ? ? ?": "machines orchestre A B C D E",
              "machines range ? ? ? ?": "machines range c c c c",
              "tar czf sauvegarde.tar.gz collection.txt": "tar czf collection.txt sauvegarde.tar.gz",
              "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/": "cp sauvegarde.tar.gz ferme/",
              "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/": "machines panne",
              "machines monte 1 ? ? ? ? ? ?": "machines monte 1 P3 C1 M1 S1 G0 A1",
              "machines monte ? ? ? ? ? ?": "machines monte P3 C1 M2 S1 G2 A1"}
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^nproc$", "lscpu | grep '^CPU(s)'"), (r"^free -h$", "cat /proc/meminfo | head -3"), (r"^lsblk$", "df -h"),
        (r"^head -5 /proc/cpuinfo$", "cat /proc/cpuinfo | head -n 5"), (r"^grep -c \^processor /proc/cpuinfo$", "grep -c processor /proc/cpuinfo"),
        (r"^printf '%x\\n' 65$", 'printf "%x\\n" 65'), (r"^echo -n A \| xxd -b$", "printf A | xxd -b"),
        (r"^wc -c photo\.bin$", "stat -c %s photo.bin"), (r"^uname -r$", "uname -sr"),
        (r"^dmesg \| head -5$", "dmesg | tail -3"), (r"^uname -srmo$", "uname -a"), (r"^cat /etc/os-release$", "head -3 /etc/os-release"),
        (r"^ps$", "ps -e"), (r"^which ls$", "command -v ls"), (r"^cat /proc/1/cgroup$", "cat /proc/self/cgroup"),
        (r"^command -v podman qemu-img virsh$", "which podman qemu-img virsh"), (r"^cat conteneur_jetable\.sh$", "less conteneur_jetable.sh"),
        (r"^sh conteneur_jetable\.sh$", "bash conteneur_jetable.sh"), (r"^df -h \.$", "df -h"), (r"^du -sh \.$", "du -h --max-depth=0 ."),
        (r"^ls ferme$", "ls -l ferme"), (r"^tar czf sauvegarde\.tar\.gz collection\.txt$", "tar -czf sauvegarde.tar.gz collection.txt"),
        (r"^cp sauvegarde\.tar\.gz sauvegarde\.sha256 ferme/disque_2/$", "cp sauvegarde.* ferme/disque_2/"),
        (r"^cp sauvegarde\.tar\.gz sauvegarde\.sha256 ferme/loin/$", "cp sauvegarde.* ferme/loin"),
        (r"^sha256sum -c sauvegarde\.sha256$", "sha256sum --check sauvegarde.sha256"),
        (r"^tar xzf sauvegarde\.tar\.gz -C \.\./\.\.$", "tar -xzf sauvegarde.tar.gz -C ../.."),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "machinerie"), "la Salle devrait être ouverte (niveaux 0 à 3 finis)"
st = tape("cd ~/terrain_terminagotchi/machines")
for _ in range(400):
    if histoire.fini(st, "machinerie"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("sm"):
        st = tape("cd ~/terrain_terminagotchi/machines")
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
        if QUI == "lea" and faute(derniere, st):
            essais.append(faute(derniere, st))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.split():
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and not essai.startswith("machines"):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
        elif apres == avant and essai.startswith("machines") and "✖" not in propre(etat["sortie"]) and \
                not any(x.strip() for x in etat["terminal"]):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
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
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
        fausses.append((avant, derniere, etat["code"]))
    if apres == avant and derniere == "machines demarre":       # elle ne démarre pas : l'enfant lit les ✖ et remonte
        st = tape("machines monte " + " ".join(solveur(besoin_lu())))
    if apres == avant and derniere.startswith(("machines orchestre ", "machines range ", "machines reveil ")):
        bons = {int(n) for n in re.findall(r"✔\s+(\d)\.", propre(etat["sortie"]))}
        verifier(True, f"{derniere} : {len(bons)} juste(s) affichés, l'enfant corrige")

verifier(histoire.fini(st, "machinerie"), f"la Salle traversée, sm0 → sm10 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
premier = next((c for _l, _s, c, _code, _lu in journal if c == "machines demarre"), None)
rate = "[demarre]" in M.carnet() and M.carnet().split("[demarre]")[1].split("\n")[0].endswith("(faux)")
verifier(("machines.premier_demarrage" in ex) == (not rate),
         f"l'exploit seulement si le PREMIER démarrage a réussi (raté d'abord : {rate}, exploits {sorted(ex)})")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
sauve = json.dumps(core.load(), ensure_ascii=False)
verifier(PRENOM not in M.carnet() and PRENOM not in sauve, f"le prénom tapé ({PRENOM}) n'est gardé ni dans le carnet ni dans la sauvegarde")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    lus = " ".join(lu_ for _l, _s, c, _code, lu_ in journal if c.startswith("sudo"))
    verifier("sudo" in lus.lower(), f"sudo : la créature explique la règle ({lus[:80]})")
    verifier(M.carnet().count("[panne]") >= 2 and "(perdu)" in M.carnet(), "la panne trop tôt : « tout serait perdu », sans rien effacer")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 18, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
elif not histoire.fini(st, "machinerie"):                # bloqué (vu une fois en CI, 1er novembre) : les dernières lignes,
    print("    bloqué ; machine :", f"nproc={M.coeurs()} justes={sorted(M.coeurs_justes())}")   # pour comprendre
    for j in journal[-8:]:
        print("    ·", str(j)[:300])
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
