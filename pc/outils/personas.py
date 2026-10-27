"""Les personas des simulations, rejoués à chaque test (PC) : trois enfants qui ne lisent que ce que l'écran montre.

    python3 pc/outils/personas.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/personas.py lea        (un seul : lea, ines ou hugo)

Chaque persona joue dans un VRAI shell qui reste ouvert (pc/tg/coquille.py : cd, alias, tâches, `cd x && ls`) ; la
ligne est ajoutée à l'historique et le jeu fait son tour avec le code de sortie, comme le crochet d'invite
(`tg prompt --statut=$?`). Il lit la commande montrée (avec le « cd … puis » quand il faut d'abord changer de lieu,
voir compagnon.commande_montree) et les messages écrits dans SON terminal (compagnon.annonces).
  - Inès, 12 ans : recopie la commande verte, c'est tout (même le cd qui la précède).
  - Léa, 7 ans : se trompe d'abord (`cdvestibule`, `ls-a`, `Ls`, une lettre oubliée dans un nom), lit l'indice,
    puis tape la commande montrée.
  - Hugo, 15 ans : essaie d'abord SA variante (`ls -la`, `cat f | grep mot`, `cd x && ls`, `tee -a`, `pkill`…),
    puis la commande montrée si sa variante n'a pas suffi.
Vérifie (docs/programme.md, G-34) : chapitres 1 à 4 finis, aucune étape validée par une commande qui a échoué, aucune
commande montrée qui échoue là où l'enfant est, chaque faute de Léa reçoit un indice dans son terminal, les variantes
justes de Hugo sont acceptées (ou félicitées avec la commande attendue).
Code de sortie 1 en cas d'échec.
"""
import builtins
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve()
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    # les trois, chacun dans un processus (un HOME par enfant)
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\npersonas : {len(PERSONAS) - ko}/{len(PERSONAS)} réussis")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_persona_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"        # hors ligne, comme à l'école
sys.path.insert(0, str(ICI.parents[1]))

from tg import app, compagnon, core, explo, histoire, langue  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None          # pas de monstres : on mesure l'histoire
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


def tape(cmd):
    """L'enfant tape une ligne : vrai shell, historique, tour de jeu avec le code de sortie ; il lit son terminal."""
    etat["sortie"], etat["code"], d = SH.lancer(cmd)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    return st


def montree(st, step):
    """Les commandes que l'écran montre, dans l'ordre (« cd … puis … » → deux commandes)."""
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip() for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip() for p in parts if p]


def faute(cmd):
    """Ce que Léa tape d'abord : une faute d'enfant de 7 ans (ou None si elle n'en fait pas ici)."""
    m = cmd.split()
    if m[0] == "cd" and len(m) == 2 and not m[1].startswith(("~", "/", ".")):
        return "cd" + m[1]                      # cdvestibule
    if m[0] == "ls" and len(m) >= 2 and m[1].startswith("-"):
        return "ls" + m[1]                      # ls-a
    if cmd in ("ls", "pwd"):
        return cmd.capitalize()                 # Ls, Pwd
    for i, w in enumerate(m[1:], 1):
        if "/" in w and not w.startswith(("~", "/", "..")):
            d, _, reste = w.partition("/")
            if len(d) > 4:
                return " ".join(m[:i] + [d[:-1] + "/" + reste] + m[i + 1:])   # fouilli/ours…
    return None


def variante(cmd):
    """La variante de Hugo, juste aussi (ou None)."""
    regles = [
        (r"^ls -l (\S+)$", r"ls -la \1"), (r"^ls -a$", "ls --all"), (r"^ls$", "ls -la"),
        (r"^grep (\S+) (\S+)$", r"cat \2 | grep \1"), (r"^wc -l (\S+)$", r"cat \1 | wc -l"),
        (r"^head -n (\d+) (\S+)$", r"cat \2 | head -n \1"), (r"^echo (\S+) >> (\S+)$", r"echo \1 | tee -a \2"),
        (r"^cat ([^/~\s]\S*)$", r"cat ./\1"), (r"^mkdir (\S+)$", r"mkdir -p \1"), (r"^rm -r (\S+)$", r"rm -rf \1"),
        (r"^cd \.\.$", "cd ../"), (r"^cd ~$", "cd"), (r"^kill %1$", "pkill sleep"), (r"^whoami$", "id -un"),
        (r"^sudo -h$", "sudo --version"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return re.sub(a, b, cmd)
    return None


fausses, echecs, sans_indice, variantes_ok, variantes_refusees = [], [], [], [], []
tentes = set()
CHAPS = ("reveil", "nid", "grenier", "cave")
st = app.etape(spontane=False, defis=False)
for _ in range(500):
    if all(histoire.fini(st, c) for c in CHAPS):
        break
    les, _e = histoire.lecon_courante(st)
    if not les:
        reste = [c for c in ("grenier", "cave") if not histoire.fini(st, c)]
        st = tape(f"cd ~/terrain_terminagotchi/{histoire.PAR_CHAP[reste[0]]['piece']}")
        continue
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        st = tape(idees[0])
        continue
    step = les["steps"][st["step"]]
    avant = (les["id"], st["step"])
    a_taper = montree(st, step)
    if a_taper[-1].startswith("echo ?"):
        a_taper[-1] = a_taper[-1].replace("?", (etat["sortie"].split() or ["0"])[-1], 1)
    if a_taper[-1].startswith("sleep 300"):
        a_taper[-1] = "sleep 30 &"
    if avant not in tentes:                     # la première fois qu'il voit cette étape : sa manière à lui
        tentes.add(avant)
        essai = faute(a_taper[-1]) if QUI == "lea" else variante(a_taper[-1]) if QUI == "hugo" else None
        if essai:
            for c in a_taper[:-1]:
                st = tape(c)
            st = tape(essai)
            les2, _ = histoire.lecon_courante(st)
            apres = (les2["id"], st["step"]) if les2 else None
            if apres != avant and etat["code"] != 0 and not any(step.get(k) for k in ("echoue", "reseau", "absent_ok")):
                fausses.append((avant, essai, etat["code"]))
            if QUI == "lea" and apres == avant and not any(x.strip() for x in etat["terminal"]):
                sans_indice.append((avant, essai))
            if QUI == "hugo":
                if apres != avant:
                    variantes_ok.append(essai)
                else:
                    t = " ".join(etat["terminal"])
                    variantes_refusees.append((essai, "voulait te faire découvrir" in t or "marche aussi" in t))
            continue
    for c in a_taper:
        st = tape(c)
        so = etat["sortie"].lower()
        if c == a_taper[-1] and ("no such file" in so or "cannot access" in so or "cannot open" in so):
            echecs.append((avant, c, SH.cwd))
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] != 0 and not any(step.get(k) for k in ("echoue", "reseau", "absent_ok")) \
            and step.get("fs") != "colis":
        fausses.append((avant, a_taper[-1], etat["code"]))

for c in CHAPS:
    verifier(histoire.fini(st, c), f"chapitre {histoire.PAR_CHAP[c]['n']} ({c}) fini")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
verifier(not echecs, f"aucune commande montrée qui échoue là où l'enfant est {echecs[:4]}")
if QUI == "lea":
    verifier(len(tentes) > 10 and not sans_indice, f"chaque faute reçoit une explication dans son terminal {sans_indice[:4]}")
if QUI == "hugo":
    mal = [v for v, felicite in variantes_refusees if not felicite]
    verifier(len(variantes_ok) >= 8, f"ses variantes justes sont acceptées ({len(variantes_ok)} : {variantes_ok[:8]})")
    verifier(not mal, f"une variante refusée est au moins félicitée avec la commande attendue {mal[:4]}")
print(f"[{QUI}] {ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
