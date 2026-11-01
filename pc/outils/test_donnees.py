"""La Salle des Données (phase 5, docs/programme.md § 2.14 et § 7.13 « D-SQL »), sur PC.

    python3 pc/outils/test_donnees.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/donnees/vecteurs.json, mêmes résultats en Kotlin) ; le
     jeu d'exemple relu dans le VRAI bestiaire ; l'export CSV (aucune donnée personnelle, une collection minuscule
     complétée) ; chaque statistique du jeu égale à celle de bash (wc, sort, uniq -c, cut, awk) sur le même fichier ;
     le nom mal écrit ; le petit sqlite3 de secours égal au vrai (s'il est installé) ; les variantes réservées EXISTENT
     (types Eau et Glace), ni gardiens ni réservées ailleurs ;
  2. l'arbre du Carrefour : fermé tant que le niveau 4 n'est pas fait, puis ouvert et annoncé une fois ; meublé ;
  3. la traversée dn0 → dn6 comme un enfant (vraies commandes dans bash, hors ligne), sur une VRAIE collection de 7
     bestioles : exploit « une statistique juste », variantes réservées, le boulier et le titre ;
  4. les indices ; 5. la vue déployée (le laboratoire de tri) ;
  6. sécurité et vie privée : rien hors du terrain, rien envoyé, aucun pseudo ni identifiant dans le CSV ni la base.
"""
import json
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_don_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, donnees as DN, recompenses  # noqa: E402
from tg import bestiaire as B, guide  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("donnees", "from tg import donnees; sys.exit(donnees.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
for nom in ("sudo", "curl", "wget"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
    (DOUBLURES / nom).chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")
SQLITE3 = shutil.which("sqlite3")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def bash(cmd, cwd=None):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd or terminal[0], capture_output=True, text=True, errors="replace",
                       timeout=60, env=ENV)
    return r.stdout


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=180, env=ENV)
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
D = DN.donnees()
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_donnees.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/donnees/vecteurs.json)" + (" " + r.stdout[-300:] if r.returncode else ""))
V = json.loads((RACINE / "donnees/donnees/vecteurs.json").read_text(encoding="utf-8"))
for awk_ in [a for a in ("awk", "mawk", "gawk", "busybox", "toybox") if shutil.which(a)]:
    ecarts = []
    for x in V["awk"]:
        cmd_ = ([awk_, "awk"] if awk_ in ("busybox", "toybox") else [awk_]) + x["options"] + [x["programme"]]
        r_ = subprocess.run(cmd_, input=V["awk_entrees"][x["entree"]], capture_output=True, text=True, env=dict(ENV, LC_ALL="C"))
        if r_.stdout != x["sortie"]:
            ecarts.append(x["programme"])
    if awk_ in ("busybox", "toybox"):                    # pour information : le téléphone n'utilise PAS leur awk (le sien)
        print(f"  · awk de {awk_} : {len(V['awk']) - len(ecarts)}/{len(V['awk'])} programmes à l'identique {ecarts[:3]}")
        continue
    verifier(not ecarts, f"les {len(V['awk'])} programmes du petit awk du téléphone : même sortie avec {awk_} {ecarts[:3]}")
verifier(all(B.espece(x["espece"]) and any(v["id"] == x["variante"] for v in B.espece(x["espece"])["variantes"])
             for x in D["exemples"]), f"les {len(D['exemples'])} bestioles d'exemple sont du VRAI bestiaire")
gardiens = set(recompenses.gardiens().values())
verifier(not gardiens & {B.espece(x["espece"])["id"] for x in D["exemples"]}, "aucun gardien glitch dans le jeu d'exemple")
m = next(x for x in recompenses.mondes() if x["id"] == "donnees")
autres = {v for x in recompenses.mondes() if x["id"] != "donnees" for v in x.get("variantes_reservees", [])}
ok_var = True
for v in m["variantes_reservees"]:
    eid, vid = v.split(":")
    e = B.espece(eid)
    ok_var &= bool(e) and any(x["id"] == vid for x in e["variantes"]) and guide.type_de(e, vid) in ("eau", "glace") \
        and eid not in gardiens and v not in autres
verifier(ok_var and len(m["variantes_reservees"]) == 3, f"variantes réservées EXISTANTES, Eau ou Glace, ni gardiens ni déjà réservées : {m['variantes_reservees']}")

rows, ajout = DN.lignes_collection([])
verifier(len(rows) == 10 and ajout == 10 and all(r[-1] == "1" for r in rows), "collection vide : 10 bestioles d'exemple (colonne exemple = 1)")
random.seed(7)
deux = [B.individu(B.espece("Gloupi"), False, "marais"), B.individu(B.espece("Krillou"), True, "lagon", "glace")]
rows, ajout = DN.lignes_collection(deux)
verifier(len(rows) == 10 and ajout == 8 and [r[-1] for r in rows[:2]] == ["0", "0"], "2 bestioles : complétées par 8 d'exemple, jamais bloquant")
verifier(rows[1][1] == "glace" and rows[1][9] == "1" and rows[1][10] == "glace", f"le type suit la variante (Krillou glace, shiny) {rows[1]}")
texte = DN.csv_texte(rows)
verifier(texte.splitlines()[0] == ",".join(D["colonnes"]) and all(len(l.split(",")) == 13 for l in texte.splitlines()),
         "13 colonnes, une ligne d'en-tête")
verifier(not any(x in texte for x in ("Pixel", "@", deux[0]["id"], deux[0]["marque"])),
         "aucune donnée personnelle : ni nom de la créature, ni e-mail, ni identifiant, ni marque")

random.seed(11)
SEPT = [B.individu(B.espece(n), n == "Cailloute", "x") for n in
        ("Gloupi", "Braisillon", "Gloupi", "Krillou", "Cailloute", "Plumange", "Tritonnet")]
rows7 = DN.lire_csv(DN.csv_texte(DN.lignes_collection(SEPT)[0]))
tmp = Path(tempfile.mkdtemp())
(tmp / "collection.csv").write_text(DN.csv_texte(DN.lignes_collection(SEPT)[0]), encoding="utf-8")
verifier(bash("wc -l < collection.csv", tmp).strip() == str(len(rows7) + 1), "wc -l : une ligne par bestiole + l'en-tête")
s_ = bash("awk -F, 'NR>1 {s+=$4; n++} END {print s/n}' collection.csv", tmp).strip()
verifier(s_ == DN.nombre_awk(DN.moyenne(rows7)), f"la moyenne : awk {s_}, le jeu {DN.nombre_awk(DN.moyenne(rows7))}")
s_ = bash("awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv", tmp).strip()
verifier(s_ == str(DN.somme(rows7)), f"la somme : awk {s_}, le jeu {DN.somme(rows7)}")
u = bash("cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c", tmp).split()
verifier(dict(zip(u[1::2], map(int, u[::2]))) == dict(DN.effectifs([r["type"] for r in rows7])), f"les types : uniq -c {u}")
top = [int(x.split()[0]) for x in bash("sort -nr forces.txt | head -3", tmp).splitlines()] if (tmp / "forces.txt").write_text(DN.forces_txt(rows7)) else []
verifier(top == DN.top3(rows7), f"le podium : sort -nr | head -3 {top}, le jeu {DN.top3(rows7)}")
mm = bash("cut -d, -f4 collection.csv | tail -n +2 | sort -n | sed -n '1p;$p'", tmp).split()
verifier(int(mm[1]) - int(mm[0]) == DN.etendue(rows7), f"l'étendue : {mm}")
f, juste, mal, bon = DN.carnet_soigneur(rows7)
verifier(bon == "Gloupi" and mal != bon and mal not in {e["nom"] for e in B.donnees()["especes"]} and f.count(mal) == 4
         and juste.count(bon) >= 4, f"le nom mal écrit : {bon} → {mal} (4 fois, dont 2 sur une ligne)")
(tmp / "c.txt").write_text(f, encoding="utf-8")
verifier(bash(f"sed 's/{mal}/{bon}/g' c.txt", tmp) == juste and bash(f"sed 's/{mal}/{bon}/' c.txt", tmp).count(mal) == 1,
         "sed /g corrige tout ; sans g, une faute reste (la ligne double)")
DN.creer_base(str(tmp / "collection.db"), rows7)
q = "SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;"
mien, code = DN.sqlite_cli(str(tmp / "collection.db"), q)
verifier(code == 0 and mien.splitlines()[0].split("|")[0] in DN.types_majoritaires(rows7), f"GROUP BY : {mien.splitlines()[0]}")
mien, _ = DN.sqlite_cli(str(tmp / "collection.db"), "SELECT AVG(attaque) FROM creatures;")
verifier(abs(float(mien) - DN.moyenne(rows7)) < 1e-9, f"AVG : {mien}")
verifier(DN.sqlite_cli(str(tmp / "collection.db"), ".tables")[0] == "creatures  especes  ",
         ".tables : creatures  especes (chaque nom complété, comme le vrai sqlite3)")
verifier(DN.sqlite_cli(str(tmp / "collection.db"), "DELETE FROM creatures;")[1] == 1,
         "le petit sqlite3 de secours ouvre la base en lecture seule")
if SQLITE3:
    for req in (".tables", ".schema creatures", q, "SELECT AVG(attaque) FROM creatures;",
                "SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom ORDER BY c.nom;",
                "SELECT nom, attaque FROM creatures ORDER BY attaque DESC, nom LIMIT 3;", "SELECT AVG(vitesse), 1.0, 2.5, NULL FROM creatures;"):
        vrai = subprocess.run([SQLITE3, str(tmp / "collection.db"), req], capture_output=True, text=True).stdout.rstrip("\n")
        verifier(vrai == DN.sqlite_cli(str(tmp / "collection.db"), req)[0], f"sqlite3 et le petit sqlite3 du jeu écrivent pareil : {req}")
else:
    print("  · sqlite3 absent : comparaison avec le vrai outil faite en CI")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "donnees"), f"fermée au début (il manque {DN.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"][:len(chaps) - 1]
    h["chap"] = chaps[-1]
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0
    s["captures"] = [dict(x) for x in SEPT]


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid")))
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "donnees"), f"sans le niveau 3-4 (la bibliothèque) : toujours fermée (il manque {DN.manque(st)})")
core.modifier(ouvrir)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "donnees"), "le niveau 4 fait : la Salle des Données s'ouvre")
st, _ = tape("ls")
verifier("donnees" in st["histoire"].get("mondes_annonces", []), "annoncée une fois (une nouvelle à la fois)")
DD = T / "donnees"
verifier((DD / "laboratoire.txt").is_file() and (DD / DN.CARNET).is_file(), "la Salle est meublée (laboratoire, carnet)")

print("3. La traversée de la Salle des Données, comme un enfant (sa vraie collection de 7 bestioles)")
st, _ = tape("cd ~/terrain_terminagotchi/donnees")
verifier(lecon(st) == ("dn0", 1), f"entrer dans la Salle choisit le monde : {lecon(st)}")
sorties = {}


def rows_():
    return DN.lignes_du_fichier() or []


def sq(req):
    return ("sqlite3" if SQLITE3 else "tg donnees sqlite3") + " collection.db " + req


PARCOURS = [
    "ls", "cat laboratoire.txt",
    "head -3 collection.csv", "tg collection > collection.csv", "tg collection --csv", "tg collection --csv > collection.csv",
    "head -3 collection.csv", "wc -l collection.csv", "donnees combien 8", lambda: f"donnees combien {len(rows_())}",
    "donnees trier", "sort especes.txt | uniq -c | sort -rn | head -3", "sort -nr forces.txt | head -3",
    "sort -nr forces.txt | head -3 > top3.txt",
    "donnees colonnes", "head -1 collection.csv | tr ',' '\\n'", "cut -f2 collection.csv | head -2",
    "cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c", "cut -d, -f10 collection.csv | grep -c 1",
    "donnees shiny ?", "donnees shiny 5", lambda: f"donnees shiny {DN.nb_shiny(rows_())}",
    "cut -d, -f1 collection.csv > noms.txt && cut -d, -f2 collection.csv > types.txt", "paste -d: noms.txt types.txt | head -5",
    "donnees copiste", "cat carnet_du_soigneur.txt",
    lambda: "sed 's/{}/{}/' carnet_du_soigneur.txt".format(*DN.carnet_soigneur(rows_())[2:]),
    lambda: "sed 's/{}/{}/' carnet_du_soigneur.txt > carnet_corrige.txt".format(*DN.carnet_soigneur(rows_())[2:]),
    lambda: "sed 's/{}/{}/g' carnet_du_soigneur.txt > carnet_corrige.txt".format(*DN.carnet_soigneur(rows_())[2:]),
    "diff carnet_du_soigneur.txt carnet_corrige.txt", "sed -n '2,4p' carnet_corrige.txt",
    lambda: "sed -i 's/{}/{}/g' carnet_du_soigneur.txt".format(*DN.carnet_soigneur(rows_())[2:]),
    "donnees calcul", "awk '{print $1, $4}' collection.csv", "awk -F, 'NR<=5 {print $1, $4}' collection.csv",
    "awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv", "awk -F, 'NR>1 {s+=$4; n++} END {print s/n}' collection.csv",
    "donnees moyenne 1000", lambda: f"donnees moyenne {round(DN.moyenne(rows_()))}",
    "cut -d, -f4 collection.csv | tail -n +2 | sort -n > attaques.txt",
    lambda: f"donnees mediane {DN.medianes(rows_())[0]:g}", "sed -n '1p;$p' attaques.txt", lambda: f"donnees etendue {DN.etendue(rows_())}",
    "donnees chaine", "grep -E 'eau|glace' collection.csv", "cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs echo",
    "mkdir -p enclos && cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs -I{} touch enclos/{}.txt",
    "donnees bilan", "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt",
    "awk -F, 'NR>1 {s+=$4; n++} END {print \"moyenne\", s/n}' collection.csv >> rapport.txt", "donnees bilan",
    "donnees base", lambda: sq(".tables"), lambda: sq("\".schema creatures\""),
    lambda: sq("\"SELECT nom, attaque FROM creatures ORDER BY attaque DESC LIMIT 3;\""),
    lambda: sq("\"SELECT nom, variante FROM creatures WHERE type = 'eau';\""),
    lambda: sq("\"SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;\""),
    "donnees sql zzz", lambda: f"donnees sql {DN.types_majoritaires(rows_())[0]}",
    lambda: sq("\"SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom LIMIT 5;\""),
    lambda: sq("\"select avg(attaque) from creatures;\""),
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    st, s = tape(c)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st), st.get("indice_lecon")))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:int(os.environ.get('TG_LARGE', '110'))]!r}")
    if histoire.fini(st, "donnees"):
        break
if not histoire.fini(st, "donnees"):
    for a_, c, b, ind in vus[-8:]:
        print("     ", a_, c, "→", b, ind)
verifier(histoire.fini(st, "donnees"), f"la Salle des Données est traversée jusqu'au bout (dn0 → dn6) {lecon(st)}")
R = rows_()
verifier(len(R) == 7 and all(r["exemple"] == "0" for r in R), "le tableau est SA collection (7 bestioles, aucune d'exemple)")
o = ANSI.sub("", sorties.get("tg collection --csv", ""))
verifier(o.startswith("nom,type,famille,attaque") and "7 bestioles" in o, "tg collection --csv écrit le tableau (et le message sur la sortie d'erreur)")
verifier([int(l.split()[0]) for l in (DD / "top3.txt").read_text().splitlines()] == DN.top3(R),
         "top3.txt : les 3 plus fortes attaques")
verifier((DD / "carnet_du_soigneur.txt").read_text() == DN.carnet_soigneur(R)[1], "le carnet du soigneur corrigé sur place (sed -i)")
verifier("donnees.statistique" in recompenses.r_(st)["exploits"], "l'exploit « une statistique juste sur ta collection »")
verifier(not recompenses.reservee(st, {"id": "krillou"}, "aurore") and recompenses.reservee({}, {"id": "krillou"}, "aurore")
         and recompenses.reservee({}, {"id": "nautiloque"}, "corail") and recompenses.reservee({}, {"id": "ondulame"}, "glace")
         and not recompenses.reservee({}, {"id": "krillou"}, "glace"),
         "nautiloque:corail, krillou:aurore, ondulame:glace n'apparaissent qu'après l'exploit ; krillou:glace reste libre")
verifier((DD / "certificat_du_savant.txt").is_file() and "✋" in ANSI.sub("", sorties.get("donnees bilan", "")),
         "pas de bilan avant le rapport, puis le certificat")
verifier(sorted(p.stem for p in (DD / "enclos").iterdir()) == sorted({r["nom"] for r in R}), "xargs : un fichier par espèce dans enclos/")
cx = sqlite3.connect(str(DD / "collection.db"))
noms_db = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
cols = [r[1] for r in cx.execute("PRAGMA table_info(creatures)")]
cx.close()
verifier(noms_db == {"creatures", "especes"} and cols == D["colonnes"], "collection.db : creatures (13 colonnes) et especes")
verifier("boulier" in st["quetes"]["objets"] and st["quetes"]["titre"] == "savant_des_donnees",
         "récompenses : le boulier de savant (posé, jamais porté) et le titre de Savant des Données")
verifier("1000" in DN.carnet() and "(faux)" in DN.carnet(), "les mauvaises réponses sont notées (faux), sans bloquer")

print("4. Les indices")
pas = {s_["cmd"]: s_ for l_ in DN.LECONS.values() for s_ in l_["steps"]}
verifier(DN.indice(pas["donnees shiny ?"], [("donnees shiny ?", None)]) == langue.t("dn.indice.trou"), "« ? » recopié : un trou à remplir")
DN.noter("shiny", "9 (faux)")
verifier(DN.indice(pas["donnees shiny ?"], [("donnees shiny 9", None)]) == langue.t("dn.indice.rep.shiny"), "une mauvaise réponse : l'indice")
verifier(DN.indice(pas["sed 's/?/?/g' carnet_du_soigneur.txt > carnet_corrige.txt"], [("sed 's/a/b/' carnet_du_soigneur.txt > x", None)])
         == langue.t("dn.indice.sed_g"), "sed sans g : il manque le g")
verifier(DN.indice(pas["awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv"], [("awk '{s+=$4} END {print s}' collection.csv", None)])
         == langue.t("dn.indice.awk_f"), "awk sans -F, : le séparateur")
verifier(DN.indice(pas["tg collection --csv > collection.csv"], [("tg collection --csv", None)]) == langue.t("dn.indice.redirection"),
         "tg collection --csv sans > : la redirection")
k = next(c for c in pas if "GROUP BY" in c)
verifier(DN.indice(pas[k], [("sqlite3 collection.db SELECT type FROM creatures", None)]) in (langue.t("dn.indice.guillemets"),
                                                                                           langue.t("dn.indice.sqlite_absent")),
         "une requête sans guillemets (ou sqlite3 absent) : l'indice")

print("5. La vue déployée : le laboratoire de tri")
x = deploie.labos("cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c")
verifier([(y["outil"], y["instrument"]) for y in x] == [("cut", "ciseaux"), ("sort", "moulin")], f"{x}")
l_ = "awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv"
txt = ANSI.sub("", "\n".join(deploie.ecran(l_, deploie.blocs(l_), 1, None, 0.5, 100)))
verifier("🧮" in txt and "calculatrice" in txt, "la vue déployée dessine la calculatrice des savants")

print("6. Sécurité et vie privée")
verifier(fichiers_hors_terrain() - AVANT <= {str(HOME / ".bash_history"), str(HOME / ".terminagotchi.json")}
         or all("terminagotchi" in p or p.endswith(".bash_history") for p in fichiers_hors_terrain() - AVANT),
         f"rien d'écrit hors du terrain ({sorted(fichiers_hors_terrain() - AVANT)[:4]})")
verifier(not JOURNAL.exists(), "aucun appel réseau (curl, wget) ni sudo")
csv_ = (DD / "collection.csv").read_text(encoding="utf-8")
verifier(not any(x in csv_ for x in [st.get("name", "Pixel"), "@"] + [c["id"] for c in st["captures"]]),
         "le CSV ne contient ni le nom de la créature, ni e-mail, ni identifiant")
src = (RACINE / "pc/tg/donnees.py").read_text(encoding="utf-8")
verifier("urllib" not in src and "requests" not in src and "socket" not in src and "recense" not in src,
         "le module n'envoie rien (ni réseau, ni site)")
for code in langue.LANGUES:
    langue.definir(code)
    verifier(langue.t("dn.carnet.double", nom="Gloupi").count("Gloupi") == 2, f"{code} : la ligne double du carnet a DEUX fois le nom")
langue.definir("fr")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
