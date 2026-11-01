"""La Guilde des Bâtisseurs Libres (phase 5, docs/programme.md § 7.12), sur PC.

    python3 pc/outils/test_guilde.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/guilde/vecteurs.json, mêmes résultats en Kotlin) ; les
     licences reconnues, la faute volontaire et sa correction, le porte-clé (trou, volume), le STL du jeu relu, la
     fausse image (empreinte, la même que sha256sum), le lsblk fictif ;
  2. l'arbre du Carrefour : fermée tant que le niveau 4 n'est pas fait, puis ouverte et annoncée une fois ; meublée
     (mur des plans, carnet, crédits VIDES, petit projet MIT, atelier, fabrique) ;
  3. la traversée gu0 → gu6 comme un enfant (vraies commandes dans bash, HORS LIGNE : le git clone échoue et la Guilde
     pose sa copie du code ; gcc, make, git ; OpenSCAD absent : le jeu fabrique la plaque) : les 4 libertés, 5
     licences, libre ≠ gratuit, la faim trouvée dans le vrai code, le premier programme compilé, la branche, la
     correction, git diff, le commit (exploit « artisan » et variantes réservées), le porte-clé, la fausse clé copiée
     avec dd et vérifiée, le certificat ; la boîte à outils et le titre ;
  4. les indices (/dev, sudo, push, « ? » recopié, mauvaises réponses, le mauvais disque) et la garde ;
  5. la vue déployée : l'établi de gcc, dd, sha256sum, git commit ;
  6. sécurité : rien hors du terrain ; aucune commande du jeu ne vise /dev ni n'utilise sudo ; le dépôt de la
     contribution n'a AUCUN remote ; les vrais fichiers de langue du jeu ne sont pas touchés ; les crédits sont vides ;
     aucun téléchargement par le jeu ; 14 langues.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_gui_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne : le clone échoue vite, la copie prend le relais
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
Path(os.environ["HOME"], ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n")

from tg import app, core, deploie, histoire, langue, guilde as G, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
LANGUES_AVANT = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (RACINE / "pc/tg/langues").glob("*.json")}

for nom in ("guilde",):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"from tg import guilde; guilde.commande(sys.argv[1:])\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
(DOUBLURES / "sudo").write_text(f"#!/bin/sh\necho \"sudo $*\" >> {JOURNAL}\necho 'sudo: (test) refusé' >&2\nexit 1\n")
(DOUBLURES / "sudo").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")


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
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_guilde.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/guilde/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
verifier(G.licence_de_texte("License: LGPL-2.1+ and GPL-2+") == "lgpl" and G.licence_de_texte("MIT License") == "mit"
         and G.licence_de_texte("submit") is None and G.licence_catalogue("Firefox") == "mpl" and G.licence_catalogue("terminagotchi") is None,
         "les licences : LGPL avant GPL, MIT, rien dans « submit » ; le catalogue ; Terminagotchi n'a pas (encore) de licence")
gr = "7:42"
f = G.faute(gr)
verifier(f["faux"] in G.texte_contribution(gr) and f["faux"] not in G.texte_contribution(gr, juste=True)
         and G.correction_ok(G.texte_contribution(gr, juste=True), gr) and not G.correction_ok(G.texte_contribution(gr), gr),
         f"la faute volontaire ({f['juste']} → {f['faux']}) et sa correction")
fr_jeu = json.loads((RACINE / "pc/tg/langues/fr.json").read_text(encoding="utf-8"))
verifier(all(fr_jeu.get(x["cle"]) == x["texte"] for x in G.donnees()["contribution"]["lignes"]),
         "la copie d'exercice reprend les VRAIES phrases du jeu (la faute n'existe que dans la copie)")
p = G.piece(gr)
verifier(G.trou_ok([str(p["trou_x"]), str(p["trou_y"])], gr) and not G.trou_ok([str(p["trou_y"]), str(p["trou_x"])], gr)
         and G.volume_ok(str(G.volume(gr)), gr) and G.volume(gr) == p["longueur"] * p["largeur"] * p["epaisseur"],
         f"le porte-clé {p['longueur']}×{p['largeur']}×{p['epaisseur']} mm : trou ({p['trou_x']} ; {p['trou_y']}), volume {G.volume(gr)} mm³")
inf = G.stl_infos(G.stl_boite(40, 24, 4).encode())
verifier(inf == {"n": 12, "binaire": False, "dims": [40.0, 24.0, 4.0]}, f"le STL du jeu se relit : {inf}")
tmp = Path(tempfile.mkdtemp())
(tmp / "i.iso").write_bytes(G.image_octets())
verifier(bash("sha256sum i.iso", tmp).split()[0] == G.image_sha() and len(G.image_octets()) == 65536,
         "la fausse image : 64 Kio, sha256sum d'accord avec le jeu")
nom, go = G.cle_disque(gr)
verifier(G.disque_ok(nom, gr) and G.disque_ok("/dev/" + nom, gr) and G.disque_erreur("nvme0n1", gr) == "systeme"
         and G.disque_erreur(nom + "1", gr) == "partition", f"le lsblk fictif : la clé de {go} Go est {nom} ; le disque du système est refusé")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "guilde"), f"fermée au début (il manque {G.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    h["chap"] = "bibliotheque"
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid")))
st = core.load()
verifier(not histoire.ouvert(st, "guilde"), f"sans le niveau 3 (lire et chercher) : toujours fermée (il manque {G.manque(st)})")
core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "guilde"), "le niveau 4 fait : la Guilde s'ouvre")
verifier("guilde" in st["histoire"].get("mondes_annonces", []), "annoncée une fois")
D = T / "guilde"
verifier((D / "mur_des_plans.txt").is_file() and (D / G.CARNET).is_file() and (D / "petit_projet/LICENSE").is_file()
         and (D / "atelier/bonjour.c").is_file() and (D / "fabrique/porte_cle.scad").is_file(),
         "la Guilde est meublée (mur des plans, carnet, petit projet, atelier, fabrique)")
cr = (D / "CREDITS.txt").read_text(encoding="utf-8")
verifier("@" not in cr and "vide" in cr, "les crédits : une structure prête, VIDE (aucun nom, aucune adresse)")

print("3. La traversée de la Guilde, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/guilde")
verifier(lecon(st) == ("gu0", 1), f"entrer dans la Guilde choisit le monde : {lecon(st)}")
gr = G._graine(st)
p = G.piece(gr)
f = G.faute(gr)
nom, go = G.cle_disque(gr)
sorties = {}
LIBS = ["bash", "git", "python3", "gcc", "firefox", "coreutils", "make"]
PARCOURS = [
    "ls", "cat mur_des_plans.txt",
    "guilde libertes", "guilde libertes 0 0 0 0", lambda: "guilde libertes " + " ".join(r_ for _n, _i, r_ in G.libertes_cartes(gr)),
    "cat petit_projet/LICENSE", "ls /usr/share/licenses",
    # rpm -q seulement là où l'étape est montrée (rpm gestionnaire du système) : ailleurs il créerait ~/.rpmdb
    *(["rpm -q --qf '%{LICENSE}\\n' bash"] if histoire._outil("rpm+/usr/lib/sysimage/rpm") else []),
    "guilde licence ?", "guilde licence licornesoft", *[f"guilde licence {x}" for x in LIBS[:5]],
    "guilde gratuit", "guilde gratuit l l l l", lambda: "guilde gratuit " + " ".join(r_ for _n, _i, r_ in G.gratuit_cartes(gr)),
    "guilde depot", "git clone --depth 1 https://github.com/grecdel/terminagotchi.git code_du_jeu", "guilde copie",
    "tree -L 2 code_du_jeu", "find code_du_jeu -maxdepth 2 -type d", 'grep -rl "faim" code_du_jeu/pc/tg',
    'grep -rn "def etat_de" code_du_jeu/pc/tg', "guilde faim aura.py", "guilde faim satiete.py",
    "less code_du_jeu/pc/tg/satiete.py",
    "cd atelier", "guilde compiler", "cat bonjour.c", "guilde gcc", "gcc bonjour.c -o bonjour && ./bonjour", "file bonjour",
    "od -An -tx1 -N4 bonjour", "ldd bonjour", "make etoiles && ./etoiles 5",
    "cd ..", "guilde contribution", "cd contribution", "git status", "git switch -c corrige-une-faute", "cat langues/fr.txt",
    "sed -i 's/?/?/' langues/fr.txt", "sed -i 's/Terminaworld/Terminamonde/' langues/fr.txt",
    "sed -i 's/Terminamonde/Terminaworld/' langues/fr.txt", lambda: f"sed -i 's/{f['faux']}/{f['juste']}/' langues/fr.txt",
    "git diff", 'git commit -am "Corrige une faute"', "git log --oneline", "git push", "guilde fusion",
    "cd ../fabrique", "guilde piece", "cat porte_cle.scad", "guilde trou 1 2", lambda: f"guilde trou {p['trou_x']} {p['trou_y']}",
    "guilde volume 12", lambda: f"guilde volume {G.volume(gr)}", "openscad -o porte_cle.stl porte_cle.scad", "guilde stl",
    "head -3 porte_cle.stl",
    "cd ../vieux_pc", "guilde sauver", "lsblk", "guilde cle", f"sha256sum {G.IMAGE}", f"sha256sum -c {G.IMAGE}.sha256",
    "guilde disques", "guilde disque nvme0n1", "guilde certificat", lambda: f"guilde disque {nom}",
    f"dd if={G.IMAGE} of={G.CLE} bs=64k",
    f"sha256sum {G.IMAGE} {G.CLE}", "guilde certificat",
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    st, s = tape(c)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st)))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:100]!r}")
    if histoire.fini(st, "guilde"):
        break
if not histoire.fini(st, "guilde"):
    for a, c, b in vus[-8:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "guilde"), f"la Guilde est traversée jusqu'au bout (gu0 → gu6) {lecon(st)}")
o = ANSI.sub("", sorties.get("guilde libertes 0 0 0 0", ""))
verifier("✖" in o, "les 4 libertés : une mauvaise réponse refusée")
verifier(len(G.licences_trouvees()) >= 5 and "licornesoft" not in G.licences_trouvees(), f"5 licences trouvées : {G.licences_trouvees()}")
verifier((T / "guilde/code_du_jeu/pc/tg/satiete.py").is_file() and not (T / "guilde/code_du_jeu/.git").exists(),
         "hors ligne : le clone a échoué, la Guilde a posé sa copie du vrai code (sans rien télécharger)")
verifier("✖" in ANSI.sub("", sorties.get("guilde faim aura.py", "")) and "def etat_de" in ANSI.sub("", sorties.get("guilde faim satiete.py", "")),
         "la faim : aura.py refusé, satiete.py accepté (le vrai code de etat_de affiché)")
verifier(ANSI.sub("", sorties.get("gcc bonjour.c -o bonjour && ./bonjour", "")).strip() == langue.t("gu.bonjour.message")
         or not shutil.which("gcc"), "le premier programme compilé dit bonjour")
verifier(sorties.get("od -An -tx1 -N4 bonjour", "").strip() == "7f 45 4c 46" or not shutil.which("gcc"), "7f 45 4c 46 : le nombre magique ELF")
verifier(sorties.get("make etoiles && ./etoiles 5", "").strip().endswith("*****") or not shutil.which("make"), "make etoiles : *****")
o = sorties.get("git diff", "")
verifier((f"-" in o and f["juste"] in o and f["faux"] in o) or not shutil.which("git"), "git diff montre la faute et sa correction")
C = T / "guilde/contribution"
verifier(not shutil.which("git") or (subprocess.run(["git", "-C", str(C), "remote"], capture_output=True, text=True).stdout.strip() == ""
                                     and G.contribution_commitee(st)), "la contribution : un commit sur sa branche, et AUCUN remote")
verifier("guilde.artisan" in recompenses.r_(st)["exploits"], "l'exploit « artisan » (ta première contribution prête)")
verifier(not recompenses.reservee(st, {"id": "engrenaille"}, "mecanique") and recompenses.reservee({}, {"id": "engrenaille"}, "mecanique")
         and recompenses.reservee({}, {"id": "rouillot"}, "rouille") and not recompenses.reservee({}, {"id": "boulonnet"}, "mecanique"),
         "engrenaille:mecanique et rouillot:rouille n'apparaissent qu'après l'exploit ; boulonnet:mecanique reste libre")
verifier("✖" in ANSI.sub("", sorties.get("guilde trou 1 2", "")) and "✖" in ANSI.sub("", sorties.get("guilde volume 12", "")),
         "le trou et le volume : les mauvaises réponses refusées")
stl = T / "guilde/fabrique/porte_cle.stl"
verifier(stl.is_file() and (shutil.which("openscad") or G.stl_infos(stl.read_bytes())["n"] == 12),
         "sans OpenSCAD, la Guilde a fabriqué la plaque (12 triangles)")
verifier(G.cle_copiee() and (T / "guilde/vieux_pc/certificat_pc_sauve.txt").is_file(), "la fausse clé est une copie exacte ; le certificat « un PC sauvé »")
verifier("✖" in ANSI.sub("", sorties.get("guilde disque nvme0n1", "")) and "✖" in ANSI.sub("", sorties.get("guilde certificat", "✖")),
         "le disque du système refusé ; pas de certificat avant la copie")
verifier("boite_a_outils" in st["quetes"]["objets"] and st["quetes"]["titre"] == "batisseur_libre",
         "récompenses : la boîte à outils et le titre de Bâtisseur Libre")

print("4. Les indices et la garde")
pas = {s_["cmd"]: s_ for l_ in G.LECONS.values() for s_ in l_["steps"]}
verifier(G.indice(pas["guilde disque ?"], [("dd if=x of=/dev/sda", None)]) == langue.t("gu.indice.dev"), "/dev : l'alerte la plus forte")
verifier(G.indice(pas["guilde licence ?"], [("sudo dnf install gcc", None)]) == langue.t("gu.indice.sudo"), "sudo : jamais ici")
verifier(G.indice(pas["guilde licence ?"], [("git push", None)]) == langue.t("gu.indice.local"), "git push : tout reste local")
verifier(G.indice(pas["guilde trou ? ?"], [("guilde trou ? ?", None)]) == langue.t("gu.indice.trou"), "« ? » recopié : un trou à remplir")
G.noter("disque", "nvme0n1 (systeme)")
verifier(G.indice(pas["guilde disque ?"], [("guilde disque nvme0n1", None)]) == langue.t("gu.indice.disque.systeme"), "le disque du système")
G.noter("faim", "aura.py (faux)")
verifier(G.indice(pas["guilde faim ?"], [("guilde faim aura.py", None)]) == langue.t("gu.indice.rep.faim"), "la faim : le mauvais fichier")
s0 = core.load()
s0.setdefault("guilde", {})["faits"] = []
verifier(G.surveiller(s0, ["dd if=a of=/dev/sda"]) and G.surveiller(s0, ["dd if=a of=/dev/sda"]),
         "une écriture vers /dev : la créature alerte À CHAQUE FOIS")
verifier(G.surveiller(s0, ["git push origin main"]) and not G.surveiller(s0, ["git push"]), "git push : rappel « tout reste local » (une fois)")
verifier(G.surveiller(s0, ["sudo apt install gcc"]), "une installation : avec un adulte")

print("5. La vue déployée : l'établi")
x = deploie.etablis("gcc bonjour.c -o bonjour && ./bonjour | sha256sum")
verifier([(y["outil"], y["de"], y["vers"]) for y in x] == [("gcc", "texte", "programme"), ("sha256sum", "fichier", "empreinte")], f"{x}")
txt = ANSI.sub("", "\n".join(deploie.ecran("dd if=a.iso of=cle_usb.img", deploie.blocs("dd if=a.iso of=cle_usb.img"), 1, None, 0.5, 100)))
verifier("🛠" in txt and "🧩" in txt and "clé" in txt, "la vue déployée dessine l'établi de dd")
from tg import compagnon  # noqa: E402
verifier(any("guilde='tg guilde'" in b or "function guilde" in b for b in compagnon._blocs().values()), "tg installer pose l'alias guilde")

print("6. Sécurité et langues")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in G.LECONS for s in G.LECONS[lid]["steps"])
verifier("/dev/" not in cmds and "sudo" not in cmds and "push" not in cmds and not re.search(r"\b(dnf|apt|pip)\s+install", cmds),
         "aucune étape ne vise /dev, n'utilise sudo, ne pousse, n'installe")
src = (RACINE / "pc/tg/guilde.py").read_text(encoding="utf-8")
code_seul = "\n".join(l for l in src.split("\n") if not l.strip().startswith(("#", '"', "'")))
verifier(not re.search(r"\[\"(sudo|dd|curl|wget)\"|\"push\"|urlopen|requests\.", code_seul), "le jeu ne lance ni sudo, ni dd, ni téléchargement, ni push")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(appels == "", f"sudo n'a jamais été appelé ({appels[:80]!r})")
LANGUES_APRES = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (RACINE / "pc/tg/langues").glob("*.json")}
verifier(LANGUES_AVANT == LANGUES_APRES, "les vrais fichiers de langue du jeu ne sont pas touchés")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k_ for lid in G.LECONS for s in G.LECONS[lid]["steps"] for k_ in (s["dit"], s["bravo"]) if isinstance(k_, str) and k_ not in dct]
    m += [k_ for k_ in ("hist.guilde.titre", "hist.guilde.debut", "hist.guilde.fin", "gu.ouvert.dit", "dep.etabli") if k_ not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes de la Guilde existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
