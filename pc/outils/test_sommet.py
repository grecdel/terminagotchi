"""⛰ Le Sommet (phase 5, docs/programme.md § 2.18), sur PC.

    python3 pc/outils/test_sommet.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/sommet/vecteurs.json, mêmes résultats en Kotlin) ; les
     scripts du jeu dans un VRAI bash (fragile.sh ment puis ne ment plus, sale.sh oublie son brouillon et bivouac.sh le
     range, casse.sh signalé ligne 8, boucle.sh trouve 0 puis 5450) ; le journal (ancres, -o, captures) ; l'éboulis ; la
     boussole ; le CTF (le drapeau se construit avec les vraies commandes) ; les légendaires du Sommet EXISTENT, aucune
     réservée ailleurs ; les textes des scripts et du journal sur une ligne dans les 14 langues ;
  2. l'ouverture : 3 mondes au palier 3, calculée sur la liste des mondes du jeu (un monde qui arrive plus tard compte) ;
     annoncée une fois ; meublée ;
  3. la traversée som0 → som7 comme un enfant (vraies commandes dans bash, avec des erreurs) : exploit « trois mondes
     maîtrisés », faveurs de légendaires, le piolet et le titre ;
  4. le défi du jour (graine du jour, exercices de la salle d'entraînement) et les records ;
  5. les indices ; 6. la vue déployée (la cordée) ;
  7. sécurité : rien hors du terrain, aucun sudo ni réseau, aucun script hors du dossier du Sommet.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_som_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, programme, recompenses, sommet as S  # noqa: E402
from tg import bestiaire as B, entrainement as E  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("sommet", "from tg import sommet; sys.exit(sommet.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
for nom in ("sudo", "curl", "wget", "ssh"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
    (DOUBLURES / nom).chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def bash(cmd, cwd):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True, text=True, errors="replace", timeout=60, env=ENV)
    return r.stdout + r.stderr, r.returncode


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
D = S.donnees()
G = "1:1234"
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_sommet.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/sommet/vecteurs.json)" + (" " + r.stdout[-300:] if r.returncode else ""))
lab = Path(tempfile.mkdtemp(prefix="tg_som_lab_"))
(lab / "coffre").mkdir()
(lab / "carnet de bord.txt").write_text("x\n")
(lab / "fragile.sh").write_text(S.script("fragile"))
o, c = bash('bash fragile.sh "carnet de bord.txt"; echo "code=$?"', lab)
verifier("No such file" in o and "Sauvegarde réussie" in o and "code=0" in o, "fragile.sh : cp échoue, le script annonce « réussi » et rend 0 (il ment)")
bash("sed -i '2i set -euo pipefail' fragile.sh", lab)
o, c = bash('bash fragile.sh "carnet de bord.txt"; echo "code=$?"', lab)
verifier("Sauvegarde réussie" not in o and "code=1" in o, "avec set -euo pipefail : il s'arrête et rend 1")
bash("sed -i 's/cp $carnet/cp \"$carnet\"/' fragile.sh", lab)
o, c = bash("bash fragile.sh", lab)
verifier("unbound variable" in o and c != 0, f"sans argument : -u refuse la variable vide ({o.strip()[:60]})")
o, c = bash('bash fragile.sh "carnet de bord.txt"', lab)
verifier(c == 0 and (lab / "coffre" / "carnet de bord.txt").is_file(), "avec les guillemets : la vraie sauvegarde")
for nom in ("sale", "bivouac", "casse", "boucle"):
    (lab / f"{nom}.sh").write_text(S.script(nom))
o, c = bash("bash sale.sh; echo \"code=$?\"; ls brouillon.* | wc -l", lab)
verifier("code=1" in o and re.search(r"^1$", o, re.M) and "réchaud" in o, "sale.sh plante et oublie son brouillon")
o, c = bash("bash bivouac.sh -n 3; ls brouillon.* | wc -l; wc -l < sac.txt", lab)
verifier(o.split()[-2:] == ["1", "3"], f"bivouac.sh -n 3 : 3 rations, son brouillon rangé par trap ({o.split()[-2:]})")
o, c = bash("bash bivouac.sh -x", lab)
verifier(c == 2 and "illegal option -- x" in o and "Utilisation" in o, "bivouac.sh -x : getopts refuse, mode d'emploi, code 2")
o, c = bash("bash -n casse.sh", lab)
verifier(c != 0 and "line 8: syntax error near unexpected token `fi'" in o, f"casse.sh : bash -n signale la ligne 8 ({o.strip()[:70]!r})")
bash("sed -i '6s/$/; then/' casse.sh", lab)
o, c = bash("bash -n casse.sh && bash casse.sh", lab)
verifier(c == 0 and o.strip().endswith("100"), f"casse.sh réparé : 100 marches ({o.strip()[-20:]!r})")
o, c = bash("bash boucle.sh", lab)
verifier(o.strip().endswith(" 0"), "boucle.sh : 0 (le bug de logique)")
o, c = bash("bash -x boucle.sh", lab)
verifier("+ totl=1200" in o, "bash -x montre totl")
o, c = bash("sed -i 's/totl=/total=/' boucle.sh && bash boucle.sh", lab)
verifier(o.strip().endswith(str(D["boucle"]["juste"])), f"boucle.sh corrigé : {D['boucle']['juste']}")
SH_TEL = "mksh" if shutil.which("mksh") else "busybox sh" if shutil.which("busybox") else None   # (le sh du téléphone : mksh)
if SH_TEL:
    (lab / "b2.sh").write_text(S.script("bivouac", "sh"))
    o, c = bash(f"{SH_TEL} b2.sh -n 2 2>&1; ls brouillon.* | wc -l", lab)
    verifier(o.strip().endswith("1") and "2" in o, f"le bivouac marche aussi dans {SH_TEL} (set -euo pipefail, getopts, trap) : {o.strip()[-40:]!r}")
else:
    print("  · ni mksh ni busybox : le bivouac dans sh est vérifié en CI")
# le journal
(lab / "journal.log").write_text(S.journal_texte(G))
o, _ = bash("grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l", lab)
verifier(int(o) == len(S.lignes_datees(G)), "lignes datées : bash = jeu")
o, _ = bash("grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l", lab)
verifier(int(o) == len(S.dates(G)) > len({l[:10] for l in S.lignes_datees(G)}), f"dates différentes : bash = jeu ({o.strip()}), plus que les débuts de ligne")
o, _ = bash("grep -cE 'ALERTE|ERREUR' journal.log", lab)
verifier(int(o) == len(S.alertes_partout(G)) > len(S.alertes(G)) > 0, "ALERTE|ERREUR partout : plus que les vraies alertes")
o, _ = bash("grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log", lab)
verifier(o.splitlines() == S.alertes(G), "les vraies alertes : bash = jeu")
o, _ = bash("grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log | sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/'", lab)
verifier(o.splitlines() == [S.date_fr(l) for l in S.alertes(G)], "sed -E et ses captures : bash = jeu")
# l'éboulis
for rel, (nom, taille) in S.eboulis(G).items():
    p = lab / "eboulis" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(S.contenu_pierre(nom, taille))
o, _ = bash("find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6", lab)
l = [x.split(None, 1) for x in o.splitlines()]
verifier(l[0] == [str(S.total_eboulis(G)), "total"] and [(int(a), b) for a, b in l[1:]] == S.plus_lourds(G),
         f"les 5 plus lourdes : bash = jeu (la plus lourde : {S.plus_lourde(G)})")
o, c = bash("find eboulis -type f | xargs wc -c", lab)
verifier("No such file" in o and any(" " in n for n, _t in S.eboulis(G).values()), "sans -0 : les espaces cassent les noms")
o, _ = bash("diff <(ls eboulis/nord) <(ls eboulis/sud)", lab)
seul_n = sorted(set(S.noms_dans(G, "nord")) - set(S.noms_dans(G, "sud")))
verifier(sorted(x[2:] for x in o.splitlines() if x.startswith("< ")) == seul_n and len(seul_n) == 2, "diff <( ) <( ) : 2 pierres seulement au nord")
o, _ = bash("awk 'FNR==1 {print FILENAME, $1}' eboulis/nord/*.txt", lab)
verifier(len(o.splitlines()) == 4, "awk FNR==1 sur 4 fichiers : 4 lignes")
# la boussole
(lab / "boussole.sh").write_text(S.script_boussole(G))
o, _ = bash("bash boussole.sh --help", lab)
verifier(o.rstrip("\n") == S.aide_boussole(), "boussole.sh --help : l'aide que le jeu attend")
cap, pas = S.mission(G)
o, c = bash(f"bash boussole.sh -c {cap} -p {pas}", lab)
verifier(c == 0 and o.strip().endswith(S.lieu(G, cap, pas)) and (lab / "arrivee.txt").read_text().strip() == S.lieu(G, cap, pas),
         f"la boussole : {cap} {pas} → {S.lieu(G, cap, pas)}")
# le CTF
for rel, txt in S.fichiers_ctf(G).items():
    p = lab / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)
f1, _ = bash("grep -oE 'fragment1=[a-z]+' ctf/registre.log", lab)
f2, _ = bash("find ctf -name '*.frag' -print0 | xargs -0 cat", lab)
w1 = f1.strip().split("=")[1]
f3, c = bash(f"bash ctf/porte.sh -k {w1}", lab)
fn, cn = bash("bash ctf/porte.sh -k faux", lab)
dr = "TG{" + "-".join(x.strip().split("=")[1] for x in (f1, f2, f3)) + "}"
verifier(f1.count("\n") == 1 and c == 0 and cn != 0 and dr == S.drapeau(G) and S.drapeau_ok(G, dr.lower()),
         f"le CTF : le drapeau se construit avec les vraies commandes ({dr})")
# les légendaires et les textes
P = programme.donnees()
som = next(m for m in P["mondes"] if m["id"] == "sommet")
leg = som["legendaires"]
esp = {e["id"]: e for e in B.donnees()["especes"]}
reserves = {v.split(":")[0] for m in P["mondes"] if m["id"] != "sommet" for v in m.get("variantes_reservees", []) if ":" in v}
reserves |= {g for m in P["mondes"] for g in m.get("gardiens", {}).values()}
verifier(all(esp.get(x, {}).get("rarete") == "légendaire" for x in leg) and not set(leg) & reserves and "abyssor" not in leg,
         f"les {len(leg)} légendaires du Sommet existent, aucune réservée ailleurs ni gardienne")
x = som["exploits"][0]
verifier(x["id"] == "sommet.trois_mondes" and x["recompense"] == "legendaire" and x["bonus"] == 3 and "essais" not in x,
         "l'exploit « trois mondes maîtrisés » : 3 rencontres de légendaires, la fenêtre d'essais du genre (vérifiée par le site)")
mauvais = []
for code in ("fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"):
    data = json.loads((RACINE / f"pc/tg/langues/{code}.json").read_text(encoding="utf-8"))
    for k, v in data.items():
        if k.startswith(("som.sc.", "som.log.", "som.ctf.registre")) and "\n" in v:
            mauvais.append((code, k))
        if k.startswith("som.log.") and k not in ("som.log.suite.fausse", "som.log.suite.releve") and \
                (re.search(r"[0-9]|ALERTE|ERREUR|INFO", v)):
            mauvais.append((code, k))
    if "ALERTE" not in data.get("som.log.suite.fausse", "") or "{date}" not in data.get("som.log.suite.releve", ""):
        mauvais.append((code, "fausse/releve"))
    if "{sh}" not in data.get("som.sc.bivouac.usage", ""):
        mauvais.append((code, "usage"))
verifier(not mauvais, f"14 langues : les textes des scripts et du journal sur une ligne, sans chiffre ni étiquette {mauvais[:4]}")
shutil.rmtree(lab, ignore_errors=True)

print("2. L'ouverture : 3 mondes au palier 3")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()


def palier(s, chap, n=4):
    h = histoire.h_(s)
    for lid in histoire.PAR_CHAP[chap]["lecons"][:n]:
        if lid not in h["faits"]:
            h["faits"].append(lid)


def base(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque", "cave"):
        palier(s, c, 99)
        if c not in h["ailes"]:
            h["ailes"].append(c)
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                "observatoire", "donnees"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(base)
core.modifier(lambda s: (palier(s, "port"), palier(s, "citadelle", 3)))
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "sommet") and S.mondes_au_palier(st) == [("port", "port")],
         f"un monde au palier 3, un autre au palier 2 : fermé ({S.manque(st)})")
core.modifier(lambda s: palier(s, "citadelle"))
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "sommet") and len(S.mondes_au_palier(st)) == 2, "deux mondes : toujours fermé")
o = ANSI.sub("", subprocess.run(["sommet", "fragile"], capture_output=True, text=True, env=ENV, cwd=str(HOME)).stdout)
verifier("pas encore ouvert" in o and "2 monde(s) sur 3" in o and not (T / "sommet" / "fragile.sh").exists(),
         "fermé, `sommet fragile` explique ce qui manque et ne pose rien")
# un monde qui arrivera plus tard (la Forge) compte dès qu'il existe : simulé ici sans rien coder en dur
P_ = programme.donnees()
P_["mondes"].append({"id": "forge_test", "chapitre": "forge_test", "paliers": ["fo0", "fo1", "fo2", "fo3", "fo4"]})
histoire.PAR_CHAP["forge_test"] = {"id": "forge_test", "lecons": ["fo0", "fo1", "fo2", "fo3", "fo4"]}
st_ = core.load()
histoire.h_(st_)["faits"] += ["fo0", "fo1", "fo2", "fo3"]
verifier(S.ouvert(st_) and ("forge_test", "forge_test") in S.mondes_au_palier(st_),
         "un monde ajouté plus tard (paliers + chapitre dans programme.json) compte sans changer le Sommet")
P_["mondes"].pop()
del histoire.PAR_CHAP["forge_test"]
fake = {"id": "atelier", "paliers": ["at0", "at1", "at2", "at3"]}      # un monde sans ses leçons dans le chapitre : ignoré
P_["mondes"].append(fake)
st_ = core.load()
histoire.h_(st_)["ailes"].append("atelier")
verifier(("atelier", "atelier") not in S.mondes_au_palier(st_), "l'aile « atelier » du tronc ne compte pas pour un monde Atelier")
P_["mondes"].pop()
core.modifier(lambda s: palier(s, "machinerie"))
st, _ = tape("ls")
verifier(histoire.ouvert(st, "sommet"), "trois mondes au palier 3 : le Sommet s'ouvre")
verifier(H_ := "machinerie" and S.donnees() and programme.donnees() and
         next(m for m in programme.donnees()["mondes"] if m["id"] == "machines")["paliers"][3] in histoire.lecons_qui_ouvrent(),
         "la fin du palier 3 d'un monde fait partie des leçons qui annoncent un monde")
st = core.modifier(histoire.annoncer_monde)
st, _ = tape("ls")
verifier("sommet" in st["histoire"].get("mondes_annonces", []) and "Sommet" in " ".join(st.get("log", [])[-5:] if isinstance(st.get("log"), list) else []) or
         "sommet" in st["histoire"].get("mondes_annonces", []), "annoncé une fois (une nouvelle à la fois)")
SD = T / "sommet"
verifier((SD / "refuge.txt").is_file() and (SD / S.CARNET).is_file(), "le refuge est meublé (règlement, carnet)")

print("3. La traversée du Sommet, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/sommet")
verifier(lecon(st) == ("som0", 1), f"entrer au Sommet choisit le monde : {lecon(st)}")
sorties = {}
g = S._graine(core.load())
cap, pas = S.mission(g)
PARCOURS = [
    "ls", "cat refuge.txt",
    "sommet fragile", "cat fragile.sh", "./fragile.sh", 'bash fragile.sh "carnet de bord.txt"', "echo $?",
    "sed '2i set -euo pipefail' fragile.sh", "sed -i '2i set -euo pipefail' fragile.sh",
    'bash fragile.sh "carnet de bord.txt"; echo $?', "sed -i 's/cp $carnet/cp \"$carnet\"/' fragile.sh",
    "bash fragile.sh", 'bash fragile.sh "carnet de bord.txt"',
    "sommet bivouac", "bash sale.sh", "ls brouillon.*", "cat bivouac.sh", "bash bivouac.sh -n 3", "ls brouillon.* | wc -l",
    "bash bivouac.sh -x", "rm brouillon.*",
    "sommet journal", "head -5 journal.log", "grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l",
    "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l", "sommet dates ?", "sommet dates 1",
    lambda: f"sommet dates {len(S.dates(g))}", "grep -cE 'ALERTE|ERREUR' journal.log",
    "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt", lambda: f"sommet alertes {len(S.alertes_partout(g))}",
    lambda: f"sommet alertes {len(S.alertes(g))}", "sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt",
    "sommet eboulis", "find eboulis -type f", "find eboulis -type f | xargs wc -c",
    "find eboulis -type f -print0 | xargs wc -c", "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6",
    lambda: f"sommet lourd {S.plus_lourde(g)}.txt", 'echo "pierres : $(find eboulis -type f | wc -l)"',
    "diff <(ls eboulis/nord) <(ls eboulis/sud)", "awk 'FNR==1 {print FILENAME, $1}' eboulis/nord/*.txt",
    "sommet casse", "bash -n casse.sh", "sommet ligne 3", "sommet ligne 8", "sed -i '6s/$/; then/' casse.sh",
    "bash -n casse.sh && bash casse.sh", "bash boucle.sh", "bash -x boucle.sh", "sommet bug total", "sommet bug totl",
    "sed -i 's/totl=/total=/' boucle.sh && bash boucle.sh", "shellcheck fragile.sh", "sommet strace",
    "sommet boussole", "man -f passwd", "apropos -s 1 archive", "bash boussole.sh --help", "bash boussole.sh -c ? -p ?",
    f"bash boussole.sh -c {cap} -p {pas}", lambda: f"sommet arrivee {S.lieu(g, cap, pas)}", "grep --help | grep -- '-o,'",
    "sommet ctf", "grep -oE 'fragment1=[a-z]+' ctf/registre.log", "find ctf -name '*.frag' -print0 | xargs -0 cat",
    "bash ctf/porte.sh --help", lambda: f"bash ctf/porte.sh -k {S.fragments(g)[0]}", "sommet drapeau TG{a-b-c}",
    lambda: f"sommet drapeau {S.drapeau(g)}", "sommet defi", "tg badges grades", "sommet records",
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
    if histoire.fini(st, "sommet"):
        break
if not histoire.fini(st, "sommet"):
    for a_, c, b, ind in vus[-8:]:
        print("     ", a_, c, "→", b, ind)
verifier(histoire.fini(st, "sommet"), f"le Sommet est gravi jusqu'au bout (som0 → som7) {lecon(st)}")
etapes = {c: (a_, b, ind) for a_, c, b, ind in vus}
verifier(etapes["./fragile.sh"][0] == etapes["./fragile.sh"][1], "./fragile.sh (sans droit d'exécution) ne fait pas avancer")
verifier(etapes["sed '2i set -euo pipefail' fragile.sh"][0] == etapes["sed '2i set -euo pipefail' fragile.sh"][1],
         "sed sans -i ne change pas le fichier : l'étape attend")
verifier(etapes["sommet dates 1"][0] == etapes["sommet dates 1"][1] and "Pas tout à fait" in ANSI.sub("", sorties["sommet dates 1"]),
         "une mauvaise réponse : l'étape attend, avec un indice")
verifier(etapes["find eboulis -type f -print0 | xargs wc -c"][0] == etapes["find eboulis -type f -print0 | xargs wc -c"][1],
         "-print0 sans xargs -0 : l'étape attend")
o = ANSI.sub("", sorties[f"sommet drapeau {S.drapeau(g)}"])
verifier("capturé" in o and "Temps :" in o and "Trois mondes maîtrisés" in o, "le drapeau : chrono, record et exploit")
st = core.load()
r_ = recompenses.r_(st)
verifier("sommet.trois_mondes" in r_["exploits"] and any(f["exploit"] == "sommet.trois_mondes" and f["reste"] == 3 for f in r_["faveurs"]),
         "exploit « trois mondes maîtrisés » : 3 rencontres de légendaires à venir")
fav = recompenses.faveur(st)
m_, x_ = recompenses.exploit_def(fav["exploit"]) if fav else (None, None)
verifier(fav and m_["id"] == "sommet", "la faveur active est celle du Sommet")
verifier("piolet" in st["quetes"]["objets"] and st["quetes"]["titre"] == "maitre_du_sommet",
         "récompenses : le piolet de cordée (posé, jamais porté) et le titre de Maître du Sommet")
st_ = json.loads(json.dumps(st))
cands = [(B.espece("Gloupi"), {"espece": "Gloupi", "rarete": "commune", "variante": "classique"})] * 5 + \
        [(esp["tellurion"], {"espece": "Tellurion", "rarete": "rare", "variante": "classique"})] + \
        [(B.espece("Gloupi"), {"espece": "Gloupi", "rarete": "légendaire", "variante": "classique"})]
it = iter(cands[1:])
(e_, ind_), txt = recompenses.apparition(st_, cands[0], lambda: next(it, None))
verifier(e_["id"] == "tellurion" and txt, "la faveur garde d'abord une espèce légendaire du Sommet (avant une simple rareté légendaire)")

print("4. Le défi du jour et les records")
jour = time.strftime("%Y-%m-%d")
core.modifier(lambda s: s.setdefault("compte", {}).setdefault("graines", {}).__setitem__(f"{jour}.abcdef123456", "5a" * 32))
st = core.load()
types, verif_ = S.defi_du_jour(st)
possibles = [x for x in E.TYPES if E.type_possible(st, x)]
verifier(verif_ and len(types) == 3 and all(x in possibles for x in types) and types == S.defi_types("5a" * 32, possibles),
         f"le défi du jour : 3 exercices tirés de la graine du jour ({types})")
st2, s2 = tape("sommet defi 2")
c_ = E.e_(core.load()).get("cours") or {}
verifier(c_.get("type") == types[1] and c_.get("g", "").startswith(jour), f"`sommet defi 2` lance le 2e exercice, sur la graine du jour ({c_.get('type')})")
for typ in types:
    core.modifier(lambda s, typ=typ: S.noter_exercice(s, typ, "or", f"{jour}.abcdef123456"))
st, s = tape("sommet defi")
verifier("Défi du jour réussi" in ANSI.sub("", s) and "le site vérifie" in ANSI.sub("", s), "trois exercices en or : défi du jour réussi (vérifiés par le site)")
st, s = tape("sommet records")
verifier("CTF combiné :" in ANSI.sub("", s) and "min" in ANSI.sub("", s), "les records : le chrono du CTF")
core.modifier(lambda s: s["compte"].pop("graines"))
types_l, verif_l = S.defi_du_jour(core.load())
verifier(not verif_l and len(types_l) == 3, "sans graine du site : un défi local, dit « non vérifié »")

print("5. Les indices")
step = {"cmd": "sommet dates ?", "fs": "som_dates"}
verifier(S.indice(step, [("sudo rm -rf /", 1)]) == langue.t("som.indice.sudo"), "sudo : jamais au Sommet")
verifier(S.indice({"cmd": 'bash fragile.sh "carnet de bord.txt"'}, [("./fragile.sh", 126)]) == langue.t("som.indice.bash"),
         "./script.sh refusé : lancer avec bash")
verifier(S.indice({"cmd": "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6"},
                  [("find eboulis -type f -print0 | xargs wc -c", 1)]) == langue.t("som.indice.zero"), "-print0 va avec -0")
verifier(S.indice({"cmd": "sommet drapeau ?"}, [("sommet drapeau ?", 0)]) == langue.t("som.indice.trou"), "le ? recopié")

print("6. La vue déployée : la cordée")
cs = deploie.cordees("bash -n casse.sh && bash casse.sh")
verifier([x["outil"] for x in cs] == ["bash -n"] and len(deploie.forges("bash -n casse.sh && bash casse.sh")) == 1,
         f"bash -n à la cordée, bash casse.sh au parchemin de la Forge (une seule animation chacun) ({[x['outil'] for x in cs]})")
cs = deploie.cordees("find eboulis -type f -print0 | xargs -0 wc -c")
verifier([x["outil"] for x in cs] == ["find -print0"] and deploie.labos("find eboulis -type f -print0 | xargs -0 wc -c"),
         "find -print0 à la cordée, xargs au laboratoire des Données")
e_ = ANSI.sub("", "\n".join(deploie.ecran("bash -x boucle.sh", deploie.blocs("bash -x boucle.sh"), 1, None, 0.3)))
verifier("la cordée : bash -x (éclaire)" in e_, "l'écran de la vue déployée montre la cordée")

print("7. Sécurité")
apres = fichiers_hors_terrain() - AVANT
apres = {f for f in apres if not f.endswith((".bash_history", "save.json", ".bak", ".bak2", ".bak3", ".lock")) and "/.terminagotchi" not in f
         and "/.config/terminagotchi" not in f and "/.local/share/terminagotchi" not in f}
verifier(not apres, f"rien d'écrit hors du terrain (hors la sauvegarde du jeu) {sorted(apres)[:4]}")
verifier(not JOURNAL.exists(), f"aucun sudo, curl, wget ni ssh lancé ({JOURNAL.read_text()[:80] if JOURNAL.exists() else ''})")
scripts = [p for p in SD.rglob("*.sh")]
verifier(all("sudo" not in p.read_text() and "curl" not in p.read_text() and "../" not in p.read_text() and "/home" not in p.read_text()
             for p in scripts), f"les {len(scripts)} scripts du jeu : ni sudo, ni réseau, ni chemin hors de leur dossier")

print(f"\n{ok} ✔, {ko} ✖")
sys.exit(1 if ko else 0)
