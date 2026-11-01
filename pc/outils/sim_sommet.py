"""Trois enfants gravissent le Sommet (phase 5, som0 → som7), dans un VRAI shell resté ouvert — docs/simulations/rapport_sommet.md.

    python3 pc/outils/sim_sommet.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_sommet.py lea        (un seul : lea, ines ou hugo)

Comme sim_donnees.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée, la sortie de sa commande
et ce que le jeu écrit dans SON terminal. Le Sommet est ouvert comme dans le jeu : trois mondes au palier 3 (le Port,
la Citadelle, la Salle des Rouages), le tronc commun fait. sudo, curl et wget sont des doublures qui refusent.
  - Léa, 7 ans (le Sommet est pour les grands, mais rien ne l'en empêche) : se trompe d'abord — lance `./fragile.sh`,
    oublie -i à sed, recopie « ? », compte toutes les lignes au lieu des dates différentes, oublie -0 à xargs, donne
    la ligne du if, écrit « total » pour la faute, lance la boussole sans options, donne le drapeau sans TG{} ni tirets ;
    puis lit l'indice et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris), puis lit l'écran pour remplir.
  - Hugo, 15 ans : ses variantes (`sed -i '2a …'`, `grep -Eo`, `grep -E … -c`, `sh -n`, `bash -x ./boucle.sh`,
    `xargs -0 du -b`, `find … -name '*.frag' -print0 | xargs -0 cat`, `--help | less`…).
Les trous se remplissent en LISANT l'écran : le nombre de dates dans wc -l, les alertes dans wc -l alertes.txt, la pierre
la plus lourde dans la 2e ligne du tri, la ligne dans le message de bash -n, la variable dans la trace de bash -x, le cap
et le nombre de pas dans `sommet boussole`, le lieu dans la réponse de la boussole, les fragments dans grep, find et la
porte. Vérifie : le Sommet fini ; l'exploit « trois mondes maîtrisés » ; aucune étape validée par une commande qui a
échoué ; chaque faute de Léa reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain.
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
    print(f"\nLe Sommet : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_som_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, sommet as S  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("sommet", "from tg import sommet; sys.exit(sommet.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
for nom in ("sudo", "curl", "wget"):
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
        h["faits"] += [x for x in histoire.PAR_CHAP[c]["lecons"] if x not in h["faits"]]
        if c not in h["ailes"]:
            h["ailes"].append(c)
    for c in ("port", "citadelle", "machinerie"):               # trois mondes au palier 3 (leurs leçons 0 à 3)
        h["faits"] += [x for x in histoire.PAR_CHAP[c]["lecons"][:4] if x not in h["faits"]]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend([c["id"] for c in histoire.CHAPITRES   # les autres mondes : déjà annoncés
                                                if c.get("monde") and c["id"] != "sommet"])
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
    memoire.pop(cmd, None)
    memoire[cmd] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "sommet dates ?":
        return st, "sommet dates " + (re.findall(r"\d+", lu("grep -oE") or lu("grep -Eo")) or ["?"])[-1]
    if cmd == "sommet alertes ?":
        if not lu("wc -l alertes.txt"):
            st = tape("wc -l alertes.txt")
        return st, "sommet alertes " + (re.findall(r"\d+", lu("wc -l alertes.txt")) or ["?"])[0]
    if cmd == "sommet lourd ?":
        l = [x.split(None, 1) for x in (lu("find eboulis -type f -print0") or "").splitlines() if len(x.split(None, 1)) == 2]
        l = [x for x in l if x[1].strip() != "total"]         # (wc -c écrit un total, du -b non)
        nom = max(l, key=lambda x: int(x[0]))[1].rsplit("/", 1)[1] if l else "?"
        return st, f"sommet lourd {nom}"
    if cmd == "sommet ligne ?":
        m = re.search(r"(?:line |casse\.sh: |\[)(\d+)", lu("bash -n casse.sh") or lu("sh -n casse.sh"))   # bash, dash, mksh
        return st, f"sommet ligne {m.group(1) if m else '?'}"
    if cmd == "sommet bug ?":
        m = re.search(r"^\+ (\w+)=1200$", lu("bash -x") or "", re.M)
        return st, f"sommet bug {m.group(1) if m else '?'}"
    if cmd == "bash boussole.sh -c ? -p ?":
        m = re.search(r"cap (\w+), (\d+) pas", lu("sommet boussole"))
        return st, f"bash boussole.sh -c {m.group(1)} -p {m.group(2)}" if m else cmd
    if cmd == "sommet arrivee ?":
        return st, "sommet arrivee " + (lu("bash boussole.sh -c").split(":")[-1].strip() or "?")
    if cmd == "bash ctf/porte.sh -k ?":
        return st, "bash ctf/porte.sh -k " + (lu("grep -oE 'fragment1") or lu("grep -Eo 'fragment1") or "=?").strip().split("=")[-1]
    if cmd == "sommet drapeau ?":
        f1 = (lu("grep -oE 'fragment1") or lu("grep -Eo 'fragment1")).strip().split("=")[-1]
        f2 = lu("find ctf").strip().split("=")[-1]
        f3 = lu("bash ctf/porte.sh -k").strip().split("=")[-1]
        return st, f"sommet drapeau TG{{{f1}-{f2}-{f3}}}"
    return st, cmd


def faute(cmd):
    """La faute de Léa la première fois qu'elle voit l'étape, ou None."""
    if cmd == 'bash fragile.sh "carnet de bord.txt"':
        return ["./fragile.sh \"carnet de bord.txt\""]
    if cmd == "sed -i '2i set -euo pipefail' fragile.sh":
        return ["sed '2i set -euo pipefail' fragile.sh"]
    if cmd == "sommet dates ?":
        return ["sommet dates ?", "sommet dates " + (re.findall(r"\d+", lu("grep -E '^[0-9]")) or ["0"])[-1]]
    if cmd.startswith("find eboulis -type f -print0"):
        return ["find eboulis -type f -print0 | xargs wc -c"]
    if cmd == "sommet ligne ?":
        return ["sommet ligne 3"]
    if cmd == "sommet bug ?":
        return ["sommet bug total"]
    if cmd == "bash boussole.sh -c ? -p ?":
        return ["bash boussole.sh"]
    if cmd == "sommet drapeau ?":
        f1 = (lu("grep -oE 'fragment1") or "").strip().split("=")[-1]
        return [f"sommet drapeau {f1}"]
    return None


def variante(cmd):
    regles = [
        (r"^sed -i '2i set -euo pipefail'", "sed -i '2a set -euo pipefail' fragile.sh"),
        (r"^grep -oE '\[0-9\]\{4\}", "grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l"),
        (r"^grep -cE 'ALERTE\|ERREUR'", "grep -E 'ALERTE|ERREUR' journal.log -c"),
        (r"^find eboulis -type f -print0", "find eboulis -type f -print0 | xargs -0 du -b | sort -rn | head -6"),
        (r"^bash -n casse\.sh$", "sh -n casse.sh"),
        (r"^bash -x boucle\.sh", "bash -x ./boucle.sh"),
        (r"^grep -oE 'fragment1", "grep -Eo 'fragment1=[a-z]+' ctf/registre.log"),
        (r"^bash boussole\.sh --help", "bash boussole.sh -h"),
        (r"^head -5 journal\.log", "head -n 5 journal.log"),
        (r"^cat refuge\.txt", "less -FX refuge.txt"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "sommet"), f"le Sommet devrait être ouvert (3 mondes au palier 3) : {S.manque(st)}"
st = tape("cd ~/terrain_terminagotchi/sommet")
for _ in range(400):
    if histoire.fini(st, "sommet"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("som"):
        st = tape("cd ~/terrain_terminagotchi/sommet")
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
            essais.append(derniere)                                 # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not step.get("tout_code"):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]):
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
    if apres != avant and etat["code"] not in (0, None) and not step.get("tout_code"):
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "sommet"), f"le Sommet gravi, som0 → som7 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("sommet.trois_mondes" in ex, "l'exploit « trois mondes maîtrisés » (des légendaires à rencontrer)")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(not appels, f"aucun sudo, aucun téléchargement ({appels[:60]!r})")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 7, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
lectures = [j for j in journal if j[4].strip()]
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {len(lectures)} lectures   (HOME={HOME})")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
sys.exit(1 if ko else 0)
