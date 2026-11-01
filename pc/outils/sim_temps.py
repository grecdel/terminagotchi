"""Trois enfants traversent la Bibliothèque du Temps (phase 5, tp0 → tp5), dans un VRAI shell resté ouvert —
docs/simulations/rapport_temps.md.

    python3 pc/outils/sim_temps.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_temps.py lea        (un seul : lea, ines ou hugo)

Comme sim_guilde.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. La Bibliothèque est ouverte d'avance (niveaux 0 à 4 faits). Le HOME de chaque enfant a un
~/.gitconfig SANS identité (user.useConfigOnly) : git refuse de photographier tant que l'album n'a pas son nom d'exemple.
  - Léa, 7 ans : se trompe d'abord (une majuscule, git init sans nom, git config --global, git commit avant d'avoir
    réglé son adresse, la photo où la formule est APPARUE, git checkout HASH sans « -- grimoire.txt » (tout l'album
    voyage dans le passé), sed sans -i, git pull sans dire d'où) ; puis lit l'indice et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`git init album` puis master, `git checkout -b`, `git restore --source=`,
    `git log -S secret --oneline`, `git status -s`, `git log --graph --oneline`, `git config --local`…).
Pour les trous : l'empreinte se lit dans `git log --oneline -S secret` (la ligne du haut : la plus récente).
Vérifie : la Bibliothèque finie ; l'exploit « retrouver une version perdue » ; aucune étape validée par une commande qui
a échoué ; chaque faute de Léa reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain
(le ~/.gitconfig de l'ordinateur jamais changé par le jeu) ; aucun dépôt avec un remote réel ; aucun push.
Code de sortie 1 en cas d'échec.
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
    print(f"\nBibliothèque du Temps : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_tmp_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(RACINE / "pc"))
GITCONFIG = "[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n"
Path(os.environ["HOME"], ".gitconfig").write_text(GITCONFIG)

from tg import app, compagnon, core, explo, histoire, langue, temps as T  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
(DOUBLURES / "temps").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"from tg import temps; temps.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (simulation) refusé' >&2\nexit 1\n")
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
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                 "observatoire", "donnees"])
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
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=120)
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


def empreinte_perdue(st):
    """L'enfant lit `git log --oneline -S secret` : la ligne du HAUT est la photo où le secret a disparu."""
    s = lu("git log --oneline -S") or lu("git log -S")
    if not s:
        st = tape("git log --oneline -S secret")
        s = memoire["git log --oneline -S secret"]
    lignes = [l for l in s.splitlines() if re.match(r"^[0-9a-f]{7} ", l)]
    return st, (lignes[0].split()[0] if lignes else "?"), (lignes[-1].split()[0] if lignes else "?")


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if "?" in cmd.split()[-1] or cmd.endswith(" ?") or "?~1" in cmd:
        st, h, _a = empreinte_perdue(st)
        return st, cmd.replace("?", h, 1)
    return st, cmd


def faute(cmd, st):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd == "temps perdu ?":
        st, _h, a = empreinte_perdue(st)
        return f"temps perdu {a}"                                # la photo où la formule est APPARUE
    if cmd == "git checkout ?~1 -- grimoire.txt":
        st, h, _a = empreinte_perdue(st)
        return f"git checkout {h}"                               # tout l'album voyage dans le passé (HEAD détachée)
    fautes = {"git init -b main album": "git init", 'git config user.name "Apprenti du Temps"':
              'git config --global user.name "Apprenti du Temps"', SED: SED.replace("sed -i ", "sed "),
              "git pull ../copie_de_mon_ami": "git pull", "git status": "git statut", "git switch main": "git switch principal"}
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


SED = T.SED


def variante(cmd):
    regles = [
        (r"^git init -b main album$", "git init album"), (r"^git switch -c reve$", "git checkout -b reve"),
        (r'^git config user\.name', 'git config --local user.name "Apprenti du Temps"'),
        (r"^git status$", "git status -s"), (r"^git log --oneline --graph$", "git log --graph --oneline --all"),
        (r"^git log --oneline -S secret$", "git log -S secret --oneline"), (r"^git log --oneline$", "git log --oneline -n 10"),
        (r"^git restore grimoire\.txt$", "git checkout -- grimoire.txt"), (r"^cat registre", "less registre_du_temps.txt"),
        (r"^temps branches$", "temps branche"), (r"^git commit -am \"Le reve\"$", "git commit -a -m 'Le reve'"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    if cmd == "git checkout ?~1 -- grimoire.txt":
        return "git restore --source=?~1 grimoire.txt"
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "temps"), "la Bibliothèque devrait être ouverte (niveaux 0 à 4 faits)"
st = tape("cd ~/terrain_terminagotchi/temps")
for _ in range(500):
    if histoire.fini(st, "temps"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("tp"):
        st = tape("cd ~/terrain_terminagotchi/temps")
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
            v = variante(derniere)
            if "?" in v:
                st, v = resoudre(v, st)
            essais.append(v)
        if QUI == "ines" and "?" in derniere:
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")) \
                and step.get("fs") != "tp_conflit":
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
            if essai == "git init album" and T.principale("album") != "main":
                print("    (Hugo : son album s'appelle master)")
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "⚠" not in propre(etat["sortie"]):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
        if re.match(r"^git checkout [0-9a-f]{7}$", essai):
            st = tape("git switch main")                           # l'indice : revenir dans le présent
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    st, derniere = resoudre(derniere, st)
    if derniere == "git switch main" and T.principale("album") == "master":
        derniere = "git switch master"                             # l'indice de Hugo : son album s'appelle master
    st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")) \
            and step.get("fs") != "tp_conflit":
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "temps"), f"la Bibliothèque traversée, tp0 → tp5 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("temps.version" in ex, "l'exploit « retrouver une version perdue »")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
verifier((HOME / ".gitconfig").read_text() == GITCONFIG or QUI == "lea",
         "le ~/.gitconfig de l'ordinateur n'a pas bougé (le jeu ne règle que les albums du terrain)")
depots = [p.parent for p in (core.TERRAIN / "temps").rglob(".git") if p.is_dir()]
remotes = {str(p.relative_to(core.TERRAIN)): subprocess.run(["git", "-C", str(p), "remote", "-v"], capture_output=True,
                                                            text=True).stdout for p in depots} if shutil.which("git") else {}
verifier(all(not r.strip() or all("terrain_terminagotchi/temps/" in l for l in r.splitlines()) for r in remotes.values()),
         f"aucun remote hors du terrain ({len(depots)} dépôts)")
verifier(not any(T.POUSSE.search(c) for c in TAPEES), "aucun push tapé")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    lus = " ".join(lu_ for (_l, _s, c, _code, lu_) in journal if c.startswith(("git config --global", "temps perdu", "git checkout ")))
    verifier("--global" in lus and "APPARUE" in lus and "detached HEAD" in lus,
             f"--global, la photo apparue, la HEAD détachée : expliqués ({lus[:200]})")
    verifier("useConfigOnly" in (HOME / ".gitconfig").read_text(), "la garde a prévenu (Léa a tapé --global : l'adulte vérifie)")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 8, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
