"""Trois enfants traversent le Poste de Contrôle (phase 5, ct0 → ct7), dans un VRAI shell resté ouvert —
docs/simulations/rapport_controle.md.

    python3 pc/outils/sim_controle.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_controle.py lea        (un seul : lea, ines ou hugo)

Comme sim_guilde.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. Le Poste est ouvert d'avance (niveaux 0 à 6 faits). Les commandes sont les vraies (ps, /proc, free,
df, du, uptime, journalctl, dmesg, crontab, os-release, dpkg/rpm, systemctl) ; la vague est faite de `sleep` renommés
lancés par le jeu.
  - Léa, 7 ans : se trompe d'abord (une majuscule, une caisse plus légère, le PATH à 1, `export COULEUR = bleu`,
    `bash sac_a_dos.sh` au lieu de source, toutes les lignes du carnet comptées, cron sans guillemets, un réveil
    affiché mais pas ajouté, la distribution « linux », toutes les familles en « d », un nom avec une majuscule, kill 1,
    et elle arrête le veilleur) ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`ps -ef`, `/proc/self`, `sleep 3`, `vmstat`, `df -h ~`, `du -h *`, `lscpu`,
    `printenv`, `type ls`, `sh -c`, `. ./sac_a_dos.sh`, `tail -5`, `grep | wc -l`, `tail -F`, apostrophes, `grep ^ID=`,
    `getent passwd`, `pgrep -a`, `kill -TERM`…).
Pour les trous : la caisse lue dans du -sh *, le PATH compté avec wc -l, les alertes lues dans grep -c, le réveil
déduit de la phrase du Poste, la distribution lue dans os-release (ID=), les familles déduites des noms, les numéros lus
dans ps (sans le veilleur). Vérifie : le Poste fini ; l'exploit « la vague » ; aucune étape validée par une commande
qui a échoué (sauf celles qui ont le droit d'être refusées : dmesg, journalctl, tail -f arrêté) ; chaque faute de Léa
reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain ; aucun processus du jeu ne
reste ; aucun vrai réveil, service, paquet ni compte. Code de sortie 1 en cas d'échec.
"""
import builtins
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
    print(f"\nPoste de Contrôle : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_ctl_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, controle as K  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
(DOUBLURES / "controle").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                    f"from tg import controle; controle.commande(sys.argv[1:])\" \"$@\"\n")
for nom in ("sudo", "useradd"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (simulation) refusé' >&2\nexit 1\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque", "cave"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque", "cave"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                "observatoire", "donnees", "forge", "robots", "temps"])
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
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C"))
# un enfant n'est pas root : `kill 1` et `kill -1` lui sont refusés (ici, la simulation tourne parfois en root : on
# imite le refus au lieu d'envoyer vraiment le signal au tout premier processus de la machine)
SH.lancer('kill() { case " $* " in *" 1 "*|*" -1 "*) echo "bash: kill: (1) - Operation not permitted" >&2; return 1;; esac; '
          'builtin kill "$@"; }')
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
TAPEES = []


def tape(cmd):
    TAPEES.append(cmd)
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=8 if "tail -f" in cmd or "tail -F" in cmd else 120)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    memoire.pop(cmd, None)
    memoire[cmd] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


# ce qu'un enfant déduit en lisant (les phrases du Poste, les familles qu'il vient de lire)
SITUATIONS = {"du lundi au vendredi à 7 h 30": "30 7 * * 1-5", "tous les jours à midi": "0 12 * * *",
              "tous les quarts d'heure": "*/15 * * * *", "le dimanche à 20 h": "0 20 * * 0",
              "le 1er de chaque mois à 9 h": "0 9 1 * *", "le lundi à 8 h": "0 8 * * 1"}
FAMILLES = {"Fedora": "d", "AlmaLinux": "d", "Debian": "a", "Ubuntu": "a", "Arch Linux": "p"}


def taille_du(x):
    m = re.match(r"([\d.,]+)([KMGT]?)", x.strip())
    return float(m.group(1).replace(",", ".")) * 1024 ** ("KMGT".find(m.group(2)) + 1 if m.group(2) else 0) if m else 0


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "controle entrepot ?":
        s = lu("du ")
        lignes = [l.split("\t") for l in s.splitlines() if "\t" in l]
        gros = os.path.basename(max(lignes, key=lambda x: taille_du(x[0]))[1]) if lignes else "?"
        return st, "controle entrepot " + (gros if QUI == "hugo" else gros.removesuffix(".bin"))
    if cmd == "controle path ?":
        st = tape("echo $PATH | tr ':' '\\n' | wc -l")
        return st, "controle path " + propre(etat["sortie"]).strip()
    if cmd == "controle alertes ?":
        s = lu("grep -c ALERTE") or lu("grep ALERTE")
        n = s.strip().splitlines()[-1].strip() if s.strip() else "?"
        return st, f"controle alertes {n}"
    if cmd.startswith("controle cron"):
        st = tape("controle cron")
        phrase = propre(etat["sortie"])
        rep = next((v for k, v in SITUATIONS.items() if k in phrase), "0 0 * * *")
        return st, (f"controle cron '{rep}'" if QUI == "hugo" else f'controle cron "{rep}"')
    if cmd == "controle distribution ?":
        s = lu("cat /etc/os-release") or lu("grep ^ID=") or lu("grep")
        m = re.search(r"^ID=\"?([\w.-]+)", s, re.M)
        return st, f"controle distribution {m.group(1) if m else 'linux'}"
    if cmd == "controle familles ? ? ? ? ?":
        if "controle familles" not in memoire:
            st = tape("controle familles")
        noms = re.findall(r"^\s+\d\. (.+)$", memoire["controle familles"], re.M)
        return st, "controle familles " + " ".join(FAMILLES.get(n.strip(), "a") for n in noms)
    if cmd == "controle useradd ?":
        return st, "controle useradd " + {"hugo": "hugo-15", "lea": "lea", "ines": "ines"}[QUI]
    if cmd in ("kill ?", "controle arrete ?"):
        st = tape("ps aux | grep fictif")
        alerte = lu("controle alerte")
        veilleur = re.search(r"(\w+_fictif) : .*NE L'ARRÊTE PAS", alerte)
        v = veilleur.group(1) if veilleur else "veilleur_fictif"
        # la colonne COMMAND (la 11e) : le nom de l'habitant ; on ne prend que les suspects (pas le veilleur, pas grep)
        pids = [l.split()[1] for l in propre(etat["sortie"]).splitlines()
                if len(l.split()) > 10 and l.split()[10].endswith("_fictif") and l.split()[10] != v]
        return st, ("kill -TERM " if QUI == "hugo" else "kill ") + " ".join(pids)
    return st, cmd


def faute(cmd):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    fautes = {"controle entrepot ?": "controle entrepot cartes_du_ciel", "controle path ?": "controle path 1",
              "export COULEUR=bleu": "export COULEUR = bleu", "source sac_a_dos.sh": "bash sac_a_dos.sh",
              "controle alertes ?": "controle alertes 24", 'controle cron "? ? ? ? ?"': "controle cron 0 7 * * *",
              'echo "*/15 * * * * echo RONDE >> ronde.log" >> reveils.crontab': 'echo "*/15 * * * * echo RONDE"',
              "controle distribution ?": "controle distribution linux", "controle familles ? ? ? ? ?": "controle familles d d d d d",
              "controle useradd ?": "controle useradd Lea", "kill ?": "kill 1"}
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls|ps)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^ps$", "ps -ef"), (r"^echo \$\$$", "echo $BASHPID"), (r"^ls /proc/\$\$$", "ls /proc/self"),
        (r"^head -3 /proc", "cat /proc/self/status | head -3"), (r"^sleep 5$", "sleep 3"), (r"^sleep 60 &$", "sleep 90 &"),
        (r"^jobs$", "jobs -l"), (r"^kill %1$", "kill -TERM %1"), (r"^top$", "top -b -n 1 | head -5"), (r"^free -h$", "vmstat"),
        (r"^df -h \.$", "df -h ~"), (r"^du -sh entrepot", "du -h entrepot/*"), (r"^uptime$", "uptime -p"), (r"^nproc$", "lscpu | head -5"),
        (r"^echo \$HOME$", "printenv HOME"), (r"^echo \$PATH", "printenv PATH"), (r"^which ls$", "type ls"),
        (r"^export COULEUR=bleu$", 'export COULEUR="bleu"'), (r"^bash -c 'echo \$COULEUR'$", "sh -c 'echo $COULEUR'"),
        (r"^alias salut=", "alias salut='echo Salut !'"), (r"^cat sac_a_dos\.sh$", "less sac_a_dos.sh"),
        (r"^source sac_a_dos\.sh$", ". ./sac_a_dos.sh"), (r"^echo \$POSTE$", 'echo "$POSTE"'),
        (r"^tail -n 5 carnet", "tail -5 carnet_de_bord.log"), (r"^grep -c ALERTE", "grep ALERTE carnet_de_bord.log | wc -l"),
        (r"^tail -f carnet", "tail -F carnet_de_bord.log"), (r"^journalctl", "journalctl --user -n 5 --no-pager"),
        (r"^controle reveils$", "controle réveil"), (r"^cat reveils\.crontab$", "less reveils.crontab"),
        (r"^echo \"\*/15", "printf '*/10 * * * * echo VEILLE >> veille.log\\n' >> reveils.crontab"),
        (r"^cat /etc/os-release$", "grep ^ID= /etc/os-release"), (r"^controle familles$", "controle famille"),
        (r"^dpkg -l", "dpkg-query -l | grep -c '^ii'"), (r"^rpm -qa", "rpm -q -a | wc -l"),
        (r"^systemctl list-units", "systemctl --type=service --state=running --no-pager | head -5"),
        (r"^cut -d: -f1 /etc/passwd", "getent passwd | cut -d: -f1 | head -3"), (r"^tail -2 equipage", "tail -n 2 equipage.txt"),
        (r"^ps aux \| grep fictif$", "pgrep -af fictif"), (r"^controle installer$", "controle installation"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "controle"), "le Poste devrait être ouvert (niveaux 0 à 6 faits)"
st = tape("cd ~/terrain_terminagotchi/controle")
for _ in range(500):
    if histoire.fini(st, "controle"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("ct"):
        st = tape("cd ~/terrain_terminagotchi/controle")
        continue
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        st = tape(idees[0])
        continue
    step = les["steps"][st["step"]]
    avant = (les["id"], st["step"])
    a_taper = montree(st, step)
    derniere = a_taper[-1]
    if derniere == "top":                                         # (pas de vrai clavier ici : top une fois, puis q)
        derniere = "top -bn1 | head -5"
    if derniere.startswith("tail -f"):                            # Ctrl+C au bout d'une seconde
        derniere = "timeout -s INT 1 " + derniere
    premiere_fois = avant not in tentes
    tentes.add(avant)
    essais = []
    if premiere_fois:
        if QUI == "lea" and faute(derniere):
            essais.append(faute(derniere))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.replace('"', " ").split():
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        if QUI == "hugo" and essai.startswith("tail -F"):
            essai = "timeout -s INT 1 " + essai
        for c in a_taper[:-1]:
            st = tape(c)
        if essai == "kill 1" and QUI == "lea":                     # Léa : kill 1 (refusé par le système), puis le veilleur
            st = tape("kill 1")
            sorti = " ".join(etat["terminal"])
            (sans_explication if "beaucoup" not in sorti else []).append((avant, essai, sorti[:60]))
            st = tape("ps aux | grep fictif")
            v = next((l.split()[1] for l in propre(etat["sortie"]).splitlines()
                      if len(l.split()) > 10 and l.split()[10] == "veilleur_fictif"), None)
            if v:
                st = tape(f"kill {v}")
                st = tape("controle tableau")
                if "veilleur" not in propre(etat["sortie"]):
                    sans_explication.append((avant, f"kill {v}", etat["sortie"][:60]))
                st = tape("controle alerte")
            continue
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "⚠" not in propre(etat["sortie"]):
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
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
        fausses.append((avant, derniere, etat["code"]))
    if apres == avant and journal[-2:] and all(j[2] == derniere for j in journal[-2:]):
        print(f"    · bloqué sur {avant} : {derniere!r} → {propre(etat['sortie'])[:200]!r} {etat['terminal']}")
        break

verifier(histoire.fini(st, "controle"), f"le Poste traversé, ct0 → ct7 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("controle.vague" in ex, "l'exploit « la vague » : tous les suspects arrêtés, le veilleur épargné")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
K.arreter_tout()
SH.lancer("kill %1 %2 2>/dev/null; true")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
verifier(not K.vivants(), "aucun processus du jeu ne reste")
verifier(not (JOURNAL.exists() and JOURNAL.read_text()), "ni sudo ni useradd n'ont été appelés")
verifier(not (core.TERRAIN / "controle/ronde.log").exists() and not (core.TERRAIN / "controle/veille.log").exists(),
         "aucun réveil du fichier n'a été lancé par le jeu")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 25, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
