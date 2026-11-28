"""Trois enfants traversent le Port (phase 5, P0 → P11), dans un VRAI shell resté ouvert — docs/simulations/rapport_port.md.

    python3 pc/outils/sim_port.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/sim_port.py lea        (un seul : lea, ines ou hugo)

Comme pc/outils/personas.py : le shell est pc/tg/coquille.py (tâches, `&`, `kill %1` marchent), la ligne va dans
l'historique, le jeu fait son tour avec le code de sortie, l'enfant ne lit que ce que l'écran montre (la commande
montrée, compagnon.commande_montree) et ce que le jeu écrit dans SON terminal (compagnon.annonces). Le Port est
ouvert d'avance (nid et bibliothèque finis : l'arbre du Carrefour), le vrai phare du port tourne sur 127.0.0.1.
  - Léa, 7 ans : se trompe d'abord (une lettre oubliée dans localhost, `curl-I`, une majuscule, `port cartes`),
    tente le chemin direct quand la Roche est éteinte, choisit d'abord un faux sceau ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte, même `port guide racine … feu` et `port sceau ?` ; puis lit la carte.
  - Hugo, 15 ans : ses variantes (`curl --head`, `ping -c3 127.0.0.1`, `ss -ltn | grep :8042`, `-b 127.0.0.1`…) et
    une lanterne SANS --bind (ouverte à tout le réseau local) : elle ne doit PAS valider l'étape, la créature prévient.
Vérifie : le Port fini (titre, exploits), aucune étape validée par une commande qui a échoué, chaque faute de Léa reçoit
un indice dans son terminal, les variantes justes de Hugo acceptées, la lanterne ouverte refusée et signalée, aucune
adresse hors de la boucle locale, plus aucun serveur de l'enfant qui tourne à la fin. Code de sortie 1 en cas d'échec.
Les outils absents de la machine (ping, ss, ip, tracepath, ssh-keygen…) ont des doublures, comme dans test_port.py.
"""
import builtins
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nPort : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_port_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, port  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
SORTIES = {"ping": "64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.03 ms\n3 packets transmitted, 3 received, 0% packet loss",
           "ss": "State  Recv-Q Send-Q Local Address:Port Peer Address:Port\nLISTEN 0 5 127.0.0.1:8042 0.0.0.0:*",
           "ip": "1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\ndefault via 10.0.0.1 dev eth0",
           "tracepath": " 1:  127.0.0.1    0.05ms reached", "hostname": "machine"}
for outil, sortie in SORTIES.items():
    if not shutil.which(outil):
        (DOUBLURES / outil).write_text(f"#!/bin/sh\ncat <<'FIN'\n{sortie}\nFIN\n")
if not shutil.which("ssh-keygen"):
    (DOUBLURES / "ssh-keygen").write_text('#!/bin/sh\nf=""; while [ $# -gt 0 ]; do [ "$1" = "-f" ] && f="$2"; shift; done\n'
                                         'echo "-----FAUSSE CLE-----" > "$f"; chmod 600 "$f"\n'
                                         'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAdoublure explorateur" > "$f.pub"\n')
if not shutil.which("ssh"):
    (DOUBLURES / "ssh").write_text("#!/bin/sh\necho 'OpenSSH_9.6p1, OpenSSL 3.0.13' >&2\n")
# `port …` comme l'alias port='tg port' posé par tg installer
(DOUBLURES / "port").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                "from tg import port; port.commande(sys.argv[1:])\" \"$@\"\n")
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
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
core.TERRAIN.mkdir(exist_ok=True)
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
journal = []          # (étape, commande, code, lu) : la partie entière, pour le rapport


def tape(cmd):
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=20)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:160]))
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip() for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip() for p in parts if p]


def lire_carte():
    """Ce qu'un enfant lit sur `port carte` : chaque machine et ses phares voisins (⇄)."""
    voisins = {}
    for l in propre(etat["sortie"]).split("\n"):
        m = re.search(r"(\S+?)(?:\.terminaworld)?\s+127\.\S+\s+⇄ (.+)$", l)
        if m:
            nom = "camp" if m.group(1) == "localhost" else m.group(1)
            voisins[nom] = [v.strip() for v in m.group(2).split(",")]
    return voisins


def chemin(voisins, eteints, de="racine", vers="feu"):
    vus, file = {de: None}, deque([de])
    while file:
        x = file.popleft()
        for y in voisins.get(x, []):
            if y not in vus and y not in eteints:
                vus[y] = x
                file.append(y)
    if vers not in vus:
        return None
    out = [vers]
    while out[-1] != de:
        out.append(vus[out[-1]])
    return out[::-1]


def lire_sceaux():
    """Le bon sceau d'après la règle écrite sous la liste (notaire, nom exact, pas périmé) ; et un faux (pour Léa)."""
    bons, faux = [], []
    for l in propre(etat["sortie"]).split("\n"):
        m = re.match(r"\s*(\d)\.\s+pour (\S+) — signé par (.+)$", l.strip())
        if m:
            juste = m.group(2) == "phare.terminaworld" and "notaire" in m.group(3) and "périmé" not in m.group(3)
            (bons if juste else faux).append(m.group(1))
    return bons, faux


def faute(cmd):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if "localhost" in cmd and not cmd.startswith("cd"):
        return cmd.replace("localhost", "locahost", 1)
    if cmd.startswith("curl -I"):
        return cmd.replace("curl -I", "curl-I", 1)
    if cmd == "port carte":
        return "port cartes"
    if re.match(r"^(cat|ls|hostname)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    """La variante de Hugo (15 ans), juste aussi, ou None."""
    regles = [
        (r"^ping -c 3 localhost$", "ping -c3 127.0.0.1"),
        (r"^curl -I (\S+)$", r"curl --head \1"),
        (r"^curl -s (\S+) \| head -n 3$", r"curl -s \1 | head -3"),
        (r"^curl -o (\S+) (\S+)$", r"curl \2 -o \1"),
        (r"^cat /etc/hosts$", "grep localhost /etc/hosts"),
        (r"^ss -tln \| grep 8042$", "ss -ltn | grep :8042"),
        (r"^ss -tln$", "ss -ltn"),
        (r"^curl --cacert (\S+) (\S+)$", r"curl -s --cacert \1 \2/feu"),
        (r"^curl -v (\S+)$", r"curl -sv \1 -o /dev/null"),
        (r"^ip a$", "ip addr"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return re.sub(a, b, cmd)
    return None


fausses, sans_indice, variantes_ok, variantes_refusees = [], [], [], []
lanterne = {}
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "port"), "le Port devrait être ouvert (nid et bibliothèque finis)"
st = tape("cd ~/terrain_terminagotchi/port")
voisins, eteints = {}, set()
for _ in range(400):
    if histoire.fini(st, "port"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("port"):
        st = tape("cd ~/terrain_terminagotchi/port")
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
    # --- ce que chacun tape d'abord, la première fois qu'il voit l'étape
    if premiere_fois:
        if QUI == "lea" and faute(derniere):
            essais.append(faute(derniere))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "hugo" and derniere.startswith("python3 -m http.server"):
            essais.append("python3 -m http.server 8000 --directory quai &")      # SANS --bind : ouverte à tout le réseau
        if derniere.startswith("port guide"):
            if QUI == "ines":
                essais.append(derniere)                         # recopie « … » tel quel
            if QUI == "lea":
                essais.append("port guide racine roche feu")      # le chemin qu'elle connaît (la Roche est éteinte)
        if derniere.startswith("port sceau ") and QUI in ("ines", "lea"):
            essais.append(derniere if QUI == "ines" else None)
    for essai in essais:
        if essai is None:                                       # Léa : un faux sceau d'abord
            st = tape("port sceau")
            bons, faux = lire_sceaux()
            essai = f"port sceau {faux[0]}"
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] != 0 and not any(step.get(k) for k in ("echoue", "absent_ok")):
            fausses.append((avant, essai, etat["code"]))
        if "--directory quai &" in essai and "--bind" not in essai:
            lanterne = {"valide": apres != avant, "prevenu": "--bind 127.0.0.1" in " ".join(etat["terminal"])}
            st = tape("kill %1")
            continue
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and not etat["sortie"].strip():
            sans_indice.append((avant, essai))
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    # --- la commande montrée (les « … » et « ? » résolus en lisant l'écran)
    if derniere.startswith("port guide"):
        if not voisins:
            st = tape("port carte")
            voisins = lire_carte()
        ch = chemin(voisins, {"roche"})
        derniere = "port guide " + " ".join(ch)
    elif derniere.startswith("port sceau "):
        st = tape("port sceau")
        bons, _f = lire_sceaux()
        derniere = f"port sceau {bons[0]}"
    elif derniere == "port carte":
        pass
    for c in a_taper[:-1]:
        st = tape(c)
    st = tape(derniere)
    if derniere == "port carte":
        voisins = lire_carte()
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] != 0 and not any(step.get(k) for k in ("echoue", "absent_ok")):
        fausses.append((avant, derniere, etat["code"]))

SH.lancer("kill %1 %2 2>/dev/null; true")
verifier(histoire.fini(st, "port"), f"le Port fini, P0 → P11 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier({"port.messager", "port.sceau"} <= set(ex), f"les deux exploits du Port {sorted(ex)}")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
hotes = set()
for _l, _s, c, _code, _lu in journal:
    hotes |= set(re.findall(r"https?://([^/:\s]+)", c))
verifier(hotes <= {"localhost", "127.0.0.1", "locahost"}, f"seulement la boucle locale {sorted(hotes)}")
r = subprocess.run(["bash", "-c", "ps -eo args | grep -c '[h]ttp.server 8000'"], capture_output=True, text=True)
verifier(r.stdout.strip() == "0", "plus aucune lanterne (http.server) qui tourne à la fin")
if QUI == "lea":
    verifier(not sans_indice, f"chaque faute reçoit une explication {sans_indice[:4]}")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 6, f"ses variantes justes sont acceptées ({len(variantes_ok)} : {variantes_ok})")
    print(f"    variantes refusées : {variantes_refusees}")
    verifier(lanterne and not lanterne["valide"], "la lanterne SANS --bind ne valide pas l'étape")
    verifier(lanterne.get("prevenu"), "la créature prévient : la lanterne éclaire tout le réseau (--bind 127.0.0.1)")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
port.eteindre_phare()
for _ in range(30):
    if not port.phare_allume():
        break
    time.sleep(0.2)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes   (HOME={HOME})")
sys.exit(1 if ko else 0)
