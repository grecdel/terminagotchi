"""Trois enfants traversent la Salle des Données (phase 5, dn0 → dn6), dans un VRAI shell resté ouvert, sur LEUR
collection — docs/simulations/rapport_donnees.md.

    python3 pc/outils/sim_donnees.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_donnees.py lea        (un seul : lea, ines ou hugo)

Comme sim_observatoire.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu
écrit dans SON terminal. La Salle est ouverte d'avance (niveaux 0 à 4 faits). sudo, curl et wget sont des doublures
qui refusent (et notent qu'on les a appelées).
  - Léa, 7 ans : une collection MINUSCULE (2 bestioles). Depuis le 1er novembre le jeu ne la complète plus : il dit
    « Il te faut au moins X créatures » et où les rencontrer ; Léa part en dresser (ses renforts, fixes), réexporte et
    revient — l'étape l'a attendue. Se trompe d'abord (une
    majuscule, `tg collection` sans --csv puis sans >, compte la ligne des titres, cut sans -d, sed sans g, awk sans -F,
    donne la somme au lieu de la moyenne, la valeur du milieu de la liste NON triée, l'étendue = le maximum, le bilan
    trop tôt, une requête SQL sans guillemets, un type au hasard) ; puis lit et corrige.
  - Inès, 12 ans : 7 bestioles ; recopie la commande verte telle quelle (« ? » compris), puis lit l'écran pour remplir.
  - Hugo, 15 ans : 40 bestioles ; ses variantes (`wc -l < …`, `head -n 3`, `cut -f2 -d,`, `awk -F','`, `sort -t, -k4 -rn`,
    `sed -e`, `grep -cE`, `sqlite3 -header`, SQL en minuscules…).
Pour les trous : le nombre se lit dans wc -l (moins la ligne des titres), les shiny dans grep -c, le mauvais nom dans
`donnees copiste`, la moyenne dans l'awk, la médiane dans `nl attaques.txt`, l'étendue dans `sed -n '1p;$p'`, le type
dans le GROUP BY. Vérifie : la Salle finie ; l'exploit « une statistique juste » ; aucune étape validée par une commande
qui a échoué ; chaque faute de Léa reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain ;
le CSV sans donnée personnelle. Code de sortie 1 en cas d'échec.
"""
import builtins
import os
import random
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
    print(f"\nSalle des Données : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_don_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, bestiaire as B, compagnon, core, explo, histoire, langue, donnees as DN  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("donnees", "from tg import donnees; sys.exit(donnees.commande(sys.argv[1:]) or 0)"),
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
random.seed({"lea": 1, "ines": 2, "hugo": 3}[QUI])
NOMS = {"lea": ["Gloupi", "Krillou"], "ines": ["Gloupi", "Braisillon", "Gloupi", "Krillou", "Cailloute", "Plumange", "Tritonnet"],
        "hugo": [e["nom"] for e in random.sample(B.publiques(), 25)]}[QUI]
if QUI == "hugo":
    NOMS += random.sample(NOMS, 15)
COLLECTION = [B.individu(B.espece(n), random.random() < 0.08, "x") for n in NOMS]
# les créatures que Léa va rencontrer et dresser quand le jeu lui dit qu'il en faut plus (fixes : la simulation reste
# déterministe)
RENFORTS = [B.individu(B.espece(n), False, "x") for n in ("Plumange", "Cailloute", "Tritonnet", "Braisillon", "Gloupi")]
EXPORT = "tg collection --csv > collection.csv"


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0
    s["captures"] = [dict(x) for x in COLLECTION]


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
    SORTIES.append(memoire[cmd])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def nombre(s, k=0):
    m = re.findall(r"-?\d+(?:\.\d+)?", s or "")
    return m[k] if len(m) > k else "?"


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "donnees combien ?":
        s = lu("wc -l") or ""
        n = nombre(s)
        return st, f"donnees combien {int(n) - 1 if n != '?' else '?'}"
    if cmd == "donnees shiny ?":
        return st, f"donnees shiny {nombre(lu('cut -d, -f10') or lu('grep -c'))}"
    if "s/?/?/" in cmd:
        m = re.search(r"« ?(\S+?) ?» au lieu de « ?(\S+?) ?»", lu("donnees copiste"))
        return st, cmd.replace("s/?/?/", f"s/{m.group(1)}/{m.group(2)}/" if m else "s/x/y/")
    if cmd == "donnees moyenne ?":
        s = lu("awk -F, 'NR>1 {s+=$4; n++}") or lu("awk -F',' 'NR>1 {s+=$4; n++}")
        return st, f"donnees moyenne {nombre(s)}"
    if cmd == "donnees mediane ?":
        if not lu("nl attaques.txt"):
            st = tape("nl attaques.txt")
        lignes = [x.split() for x in lu("nl attaques.txt").splitlines() if x.split()]
        milieu = lignes[(len(lignes) - 1) // 2][1] if lignes else "?"
        return st, f"donnees mediane {milieu}"
    if cmd == "donnees etendue ?":
        v = (lu("sed -n '1p;$p'") or lu("head -1 attaques.txt") or "").split()
        return st, f"donnees etendue {int(v[-1]) - int(v[0]) if len(v) >= 2 else '?'}"
    if cmd == "donnees sql ?":
        s = lu("sqlite3 collection.db \"SELECT type, COUNT") or lu("tg donnees sqlite3 collection.db \"SELECT type, COUNT") or \
            lu("sqlite3 -header") or lu("tg donnees sqlite3 -header") or lu("sqlite3 collection.db \"select type") or \
            lu("tg donnees sqlite3 collection.db \"select type")
        l = [x for x in s.splitlines() if "|" in x and not x.startswith("type|")]
        return st, f"donnees sql {l[0].split('|')[0] if l else 'eau'}"
    return st, cmd


def faute(cmd):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd == "tg collection --csv > collection.csv":
        return ["tg collection > collection.csv", "tg collection --csv"]
    if cmd == "donnees combien ?":
        return [f"donnees combien {nombre(lu('wc -l'))}"]                     # elle compte la ligne des titres
    if cmd.startswith("cut -d, -f2 collection.csv"):
        return ["cut -f2 collection.csv | tail -n +2 | sort | uniq -c"]
    if cmd.startswith("sed 's/?/?/g' carnet_du_soigneur.txt >"):
        m = re.search(r"« ?(\S+?) ?» au lieu de « ?(\S+?) ?»", lu("donnees copiste"))
        return [f"sed 's/{m.group(1)}/{m.group(2)}/' carnet_du_soigneur.txt > carnet_corrige.txt"] if m else []
    if cmd.startswith("awk -F, 'NR>1 {s+=$4} END"):
        return ["awk 'NR>1 {s+=$4} END {print s}' collection.csv"]
    if cmd == "donnees moyenne ?":
        return [f"donnees moyenne {nombre(lu('awk -F, ' + chr(39) + 'NR>1 {s+=$4} END'))}"]   # elle donne la somme
    if cmd == "donnees mediane ?":
        a = [r["attaque"] for r in DN.lignes_du_fichier() or []]               # le milieu de la liste NON triée
        return [f"donnees mediane {a[len(a) // 2] if a else 0}"]
    if cmd == "donnees etendue ?":
        v = (lu("sed -n '1p;$p'") or "0").split()
        return [f"donnees etendue {v[-1]}"]
    if cmd.startswith("sort -t, -k4 -nr collection.csv"):
        return ["donnees bilan"]                                               # le bilan trop tôt
    if "GROUP BY" in cmd:
        return [cmd.replace("\"", "")]                                         # sans guillemets
    if cmd == "donnees sql ?":
        return ["donnees sql dragon"]
    if re.match(r"^(cat|head|ls)\b", cmd):
        return [cmd[0].upper() + cmd[1:]]
    return None


def variante(cmd):
    regles = [
        (r"^head -3 collection\.csv$", "head -n 3 collection.csv"), (r"^wc -l collection\.csv$", "wc -l < collection.csv"),
        (r"^sort especes\.txt \| uniq -c", "sort especes.txt | uniq -c | sort -nr | head -n 3"),
        (r"^sort -nr forces\.txt", "sort -rn forces.txt | head -n 3 > top3.txt"),
        (r"^head -1 collection\.csv \| tr", "head -n 1 collection.csv | tr , '\\n'"),
        (r"^cut -d, -f2 collection\.csv", "cut -f2 -d, collection.csv | tail -n +2 | sort | uniq -c | sort -rn"),
        (r"^cut -d, -f10", "cut -d, -f10 collection.csv | grep -cx 1"),
        (r"^paste -d: noms", "paste -d: noms.txt types.txt | head -n 5"),
        (r"^sed -n '2,4p'", "sed -n '2,4p' carnet_corrige.txt"),
        (r"^awk -F, 'NR<=5", "awk -F',' 'NR<=5 {print $1, $4}' collection.csv"),
        (r"^awk -F, 'NR>1 \{s\+=\$4\} END", "awk -F',' 'NR>1 {s+=$4} END {print s}' collection.csv"),
        (r"^awk -F, 'NR>1 \{s\+=\$4; n\+\+\} END \{print s/n\}'", "awk -F',' 'NR>1 {s+=$4; n++} END {print s/n}' collection.csv"),
        (r"^sed -n '1p;\$p'", "head -1 attaques.txt; tail -1 attaques.txt"),
        (r"^grep -E 'eau\|glace'", "grep -cE ',(eau|glace),' collection.csv"),
        (r"^sort -t, -k4 -nr", "sort -t, -k4 -rn collection.csv | head -n 3 | tee rapport.txt"),
        (r".*\.schema creatures", None),
        (r".*ORDER BY attaque DESC LIMIT 3", "LOWER"), (r".*GROUP BY type", "HEADER"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            if b == "LOWER":
                return re.sub(r'"(.*)"', lambda m: '"' + m.group(1).lower() + '"', cmd)
            if b == "HEADER":
                return cmd.replace("sqlite3 collection.db", "sqlite3 -header collection.db")
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees, rencontres = [], [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "donnees"), "la Salle des Données devrait être ouverte (niveaux 0 à 4 faits)"
st = tape("cd ~/terrain_terminagotchi/donnees")
for _ in range(400):
    if histoire.fini(st, "donnees"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("dn"):
        st = tape("cd ~/terrain_terminagotchi/donnees")
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
        if QUI == "ines" and ("?" in derniere.split() or "/?/" in derniere):
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
    ecran = propre(etat["sortie"]) + " " + " ".join(etat["terminal"])
    if apres == avant and re.search(r"au moins \d+ créatures", ecran):     # pas assez de créatures : elle va en dresser
        besoin = DN.minimum(les["id"]) or max(DN.donnees()["minimum"].values())
        n0 = len(st.get("captures", []))
        rencontres.append((les["id"], n0, besoin, "forêt" in ecran))
        core.modifier(lambda s: s["captures"].extend(dict(x) for x in RENFORTS[:max(0, besoin - len(s["captures"]))]))
        st = tape(EXPORT)

verifier(histoire.fini(st, "donnees"), f"la Salle des Données traversée, dn0 → dn6 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("donnees.statistique" in ex, "l'exploit « une statistique juste sur ta collection »")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
rows = DN.lignes_du_fichier() or []
attendu = len(st.get("captures", []))
verifier(len(rows) == attendu and "exemple" not in (rows[0] if rows else {}) and attendu >= len(COLLECTION),
         f"le tableau : ses {attendu} bestioles à lui (au départ {len(COLLECTION)}), aucune d'exemple")
csv_ = (core.TERRAIN / "donnees/collection.csv").read_text(encoding="utf-8")
verifier("Pixel" not in csv_ and "@" not in csv_ and not any(c["id"] in csv_ for c in COLLECTION), "le CSV : aucune donnée personnelle")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(not appels, f"aucun sudo, aucun téléchargement ({appels[:60]!r})")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    tout = " ".join(j[4] for j in journal) + " " + " ".join(SORTIES)
    verifier(rencontres and all(r[3] for r in rencontres) and [r[0] for r in rencontres][-1] == "dn4"
             and "EXEMPLE" not in tout and "exemple = 1" not in tout,
             f"la collection minuscule n'est plus complétée : le jeu dit le minimum et où aller, l'étape attend {rencontres}")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 12, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
