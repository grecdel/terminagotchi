"""Trois enfants traversent la Forge (phase 5, fo0 → fo7), dans un VRAI shell resté ouvert — docs/simulations/rapport_forge.md.

    python3 pc/outils/sim_forge.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_forge.py lea        (un seul : lea, ines ou hugo)

Comme sim_donnees.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. La Forge est ouverte d'avance (niveaux 0 à 4 faits). sudo et wget sont des doublures qui refusent (et
notent qu'on les a appelées) ; curl ne passe que vers 127.0.0.1 / localhost.
  - Léa, 7 ans : se trompe d'abord (une majuscule, un > qui efface la recette, ./ avant chmod +x, « nom = Pixel » avec
    des espaces, salut.sh sans prénom, le code 0, un tour de moins, « Traceback » au lieu du nom de l'erreur, le serveur
    sans --bind 127.0.0.1, curl avant d'allumer, le modèle au lieu de la marque, le bilan trop tôt) ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris), puis lit l'écran pour remplir.
  - Hugo, 15 ans : ses variantes (bash au lieu de sh, chmod u+x, ${nom}, {1..3}, seq 10, python3 -V, -b et -d pour
    http.server, curl -s http://127.0.0.1:…, kill %1, ffmpeg -y, exiftool -s…).
Pour les trous : le code dans la sortie d'`echo $?`, les tours dans `forge tours` (seq A Z), l'erreur dans la dernière
ligne du Traceback, la marque dans les métadonnées. Sans clavier ici : la devinette est jouée par un tuyau de réponses
(les essais de l'enfant), et « fg puis Ctrl+C » devient `kill %1`. Vérifie : la Forge finie ; aucune étape validée par
une commande qui a échoué ; chaque faute de Léa reçoit une explication ; les variantes justes de Hugo acceptées ; le
serveur jamais laissé ouvert à tout le réseau ; rien hors du terrain. Code de sortie 1 en cas d'échec.
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
    print(f"\nForge : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_forge_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, forge as FO  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("forge", "from tg import forge; sys.exit(forge.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
for nom in ("sudo", "wget"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (simulation) refusé' >&2\nexit 1\n")
if shutil.which("curl"):
    (DOUBLURES / "curl").write_text("#!/bin/sh\ncase \"$*\" in *localhost*|*127.0.0.1*) exec " + shutil.which("curl") +
                                    f" \"$@\";; esac\necho \"curl $*\" >> {JOURNAL}\nexit 7\n")
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
SORTIES = []
PARTOUT = []                                     # le serveur vu ouvert à tout le réseau (et combien de temps)


def tape(cmd):
    vrai = cmd
    if "http.server" in cmd and cmd.endswith("&"):
        vrai = cmd[:-1].rstrip() + " >/dev/null 2>&1 &"          # (les lignes du serveur n'encombrent pas la suite)
    etat["sortie"], etat["code"], d = SH.lancer(vrai, delai=120)
    if "http.server" in cmd:
        __import__("time").sleep(1.2)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    p, partout = FO.serveur_du_site(st)
    if partout:
        PARTOUT.append(cmd)
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    memoire.pop(cmd, None)
    memoire[cmd] = propre(etat["sortie"])
    SORTIES.append(memoire[cmd])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant) ; sans clavier : les réponses par un tuyau."""
    if cmd == "forge code ?":
        s = next((v for k, v in list(memoire.items())[::-1] if "echo $?" in k), "")
        n = (re.findall(r"^(\d+)$", s, re.M) or ["?"])[-1]
        return st, f"forge code {n}"
    if cmd == "forge tours ?":
        st = tape("forge tours")
        m = re.search(r"seq (\d+) (\d+)", lu("forge tours"))
        return st, f"forge tours {int(m.group(2)) - int(m.group(1)) + 1 if m else '?'}"
    if cmd == "forge erreur ?":
        s = lu("python3 serpent.py") or lu("forge serpent")
        m = re.findall(r"^\s*(\w+Error)\b", s, re.M)
        return st, f"forge erreur {m[-1] if m else '?'}"
    if cmd == "forge appareil ?":
        s = lu("exiftool") or lu("tg forge exif") or lu("forge exif")
        m = re.search(r"(?:Make|Marque de l'appareil)\s*:\s*(\S+)", s)
        return st, f"forge appareil {m.group(1) if m else '?'}"
    if cmd == "sh mon_jeu/devinette.sh":                      # l'enfant joue : ses essais (moitié, puis plus près)
        return st, "printf '5\\n8\\n3\\n7\\n9\\n6\\n4\\n2\\n10\\n1\\n' | sh mon_jeu/devinette.sh"
    if cmd == "sh question.sh":
        return st, "echo " + {"lea": "Léa", "ines": "Inès", "hugo": "Hugo"}[QUI] + " | sh question.sh"
    if cmd == "fg":                                           # fg puis Ctrl+C (sans clavier ici : kill %1)
        return st, "kill %1"
    return st, cmd


def faute(cmd, st):
    """Les fautes de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd == "echo 'mkdir -p cabane' >> cabane.sh":
        return ["echo 'mkdir -p cabane' > cabane.sh", "echo '#!/bin/sh' > cabane.sh"]          # > efface, elle refait
    if cmd == "chmod +x cabane.sh":
        return ["./cabane.sh"]
    if cmd == "nom=Pixel":
        return ["nom = Pixel"]
    if cmd == "sh salut.sh Léa":
        return ["sh salut.sh"]
    if cmd == "forge code ?":
        return ["forge code 0"]
    if cmd == "forge tours ?":
        a, z = FO.tours_question(FO._graine(st))
        return [f"forge tours {z - a}"]                                                          # un de moins
    if cmd == "forge erreur ?":
        return ["forge erreur Traceback"]
    if cmd == FO.SERVEUR:
        return ["curl localhost:8642", "python3 -m http.server 8642 --directory site &", "kill %1"]   # trop tôt, sans --bind
    if cmd == "forge appareil ?":
        return ["forge appareil TC-7"]
    if cmd == "forge publier":
        return ["forge bilan"]
    if cmd.startswith("forge carte"):
        return ["forge carte"]
    if re.match(r"^(cat|ls)\b", cmd):
        return [cmd[0].upper() + cmd[1:]]
    return None


def variante(cmd):
    regles = [
        (r"^echo '#!/bin/sh' > cabane\.sh$", "printf '#!/bin/sh\\n' > cabane.sh"),
        (r"^sh cabane\.sh$", "bash cabane.sh"), (r"^chmod \+x cabane\.sh$", "chmod u+x cabane.sh"),
        (r"^nom=Pixel$", "nom=Hugo"), (r'^echo "Bonjour \$nom"$', 'echo "Bonjour ${nom} !"'),
        (r"^sh salut\.sh Léa$", "bash salut.sh Hugo"), (r"^sh salut\.sh Léa Tom Sam$", "sh salut.sh Hugo Ana Bob Zoé"),
        (r"^for i in 1 2 3;", 'for n in {1..3}; do echo "Tour $n"; done'),
        (r"^for i in \$\(seq 1 10\)", "for i in $(seq 10); do mkdir -p village/cabane_$i; done"),
        (r"^ls village \| wc -l$", "ls -1 village | wc -l"),
        (r"^n=3; while", 'i=3; while [ "$i" -gt 0 ]; do echo "$i"; i=$((i-1)); done'),
        (r"^python3 --version$", "python3 -V"), (r'^python3 -c "print\(2 \+ 3 \* 4\)"$', "python3 -c 'print(2+3*4)'"),
        (r"^python3 serpent\.py Pixel 3$", "python3 serpent.py Hugo 5"),
        (r"^seq 1 10 \| sh mon_jeu", "seq 10 | bash mon_jeu/devinette.sh"),
        (r"^python3 -m http\.server 8642 --bind", "python3 -m http.server 8642 -b 127.0.0.1 -d site &"),
        (r"^curl localhost:8642$", "curl -s http://127.0.0.1:8642/"),
        (r"^ffmpeg ", "ffmpeg -y -loglevel error -i multimedia/fanfare.wav -ss 0.5 -t 0.5 multimedia/fin.wav"),
        (r"^exiftool multimedia", "exiftool -s multimedia/photo_exemple.jpg"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "forge"), "la Forge devrait être ouverte (niveaux 0 à 4 faits)"
st = tape("cd ~/terrain_terminagotchi/forge")
for _ in range(500):
    if histoire.fini(st, "forge"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("fo"):
        st = tape("cd ~/terrain_terminagotchi/forge")
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
            essais += faute(derniere, st)
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
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "✋" not in propre(etat["sortie"]) and essai not in ("kill %1", "echo '#!/bin/sh' > cabane.sh"):
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

if not histoire.fini(st, "forge"):
    for j in journal[-10:]:
        print("    ·", j)
verifier(histoire.fini(st, "forge"), f"la Forge traversée, fo0 → fo7 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("forge.premier_coup" in ex, "l'exploit « un programme qui marche du premier coup » (la recette complète, lancée une fois)")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(not appels, f"aucun sudo, aucun réseau hors de 127.0.0.1 ({appels[:60]!r})")
verifier(FO._page(8642) is None, "la lanterne est éteinte à la fin")
verifier((core.TERRAIN / "forge/mon_jeu/.lieu").is_file(), "son jeu est posé sur la carte")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    verifier(len(PARTOUT) <= 1, f"le serveur sans --bind : vu, dit tout de suite, éteint au tour suivant ({PARTOUT})")
    verifier("indice:fo1" in FO.f_(st)["faits"], "le palier des recettes, fini avec des indices, ne compte pas pour « sans indice »")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 14, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    verifier("forge.sans_indice" in ex, "un palier sans indice : l'exploit « sans indice »")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.lancer("kill %1 2>/dev/null; true")
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
