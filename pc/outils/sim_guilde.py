"""Trois enfants traversent la Guilde des Bâtisseurs Libres (phase 5, gu0 → gu6), dans un VRAI shell resté ouvert —
docs/simulations/rapport_guilde.md.

    python3 pc/outils/sim_guilde.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_guilde.py lea        (un seul : lea, ines ou hugo)

Comme sim_ondes.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. La Guilde est ouverte d'avance (niveaux 0 à 4 faits). Hors ligne : le git clone échoue, la Guilde
pose sa copie du code ; gcc, make et git sont les vrais (s'ils sont installés) ; OpenSCAD est absent ici (la Guilde
fabrique la plaque).
  - Léa, 7 ans : se trompe d'abord (une majuscule, les libertés dans l'ordre, un logiciel inventé, tout « libre », le
    mauvais fichier pour la faim, gcc qui écraserait sa source, sed sans -i, git commit sans -a, le trou à y = largeur,
    un volume « 40*24*4 », le disque du système, dd À L'ENVERS qui écrase l'image) ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`git checkout -b`, `cc`, `od -c`, `grep -rln`, `find -maxdepth`, `sha256sum --check`,
    `cp` au lieu de dd, `guilde disque /dev/sdb`, `guilde volume … cm3`, `guilde trou [6, 12]`, accents…).
Pour les trous : les libertés et « libre ou gratuit » se lisent dans les situations ; les licences : les noms proposés à
l'écran ; la faim : le nom du fichier avant les deux-points de grep -rn ; la faute : le mot inconnu de la phrase ; le
trou et le volume : les nombres du plan porte_cle.scad ; le disque : la colonne RM et la taille dans le lsblk fictif.
Vérifie : la Guilde finie ; l'exploit « artisan » ; aucune étape validée par une commande qui a échoué ; chaque faute de
Léa reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain ; aucune écriture vers /dev ;
le dépôt de la contribution sans remote. Code de sortie 1 en cas d'échec.
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
    print(f"\nGuilde des Bâtisseurs Libres : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_gui_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(RACINE / "pc"))
Path(os.environ["HOME"], ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n")

from tg import app, compagnon, core, explo, histoire, langue, guilde as G  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
(DOUBLURES / "guilde").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                  f"from tg import guilde; guilde.commande(sys.argv[1:])\" \"$@\"\n")
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
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes"])
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


# ce qu'un enfant sait d'un mot mal écrit (il connaît le bon mot en lisant la phrase)
JUSTES = {"fain": "faim", "contiune": "continue", "autoure": "autour", "secrai": "secret", "exactemment": "exactement"}
DEJA = set()


def faute_lue():
    """(mot faux, mot juste) lus dans langues/fr.txt : le mot que l'enfant ne connaît pas, ou « l'a trouver »."""
    s = lu("cat langues/fr.txt") or lu("less langues/fr.txt") or lu("head")
    for mot, juste in JUSTES.items():
        if re.search(rf"\b{mot}\b", s):
            return mot, juste
    if "l'a trouver" in s:
        return "trouver", "trouvé"
    return "?", "?"


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "guilde libertes ? ? ? ?":
        if "guilde libertes" not in memoire:
            st = tape("guilde libertes")
        sit = re.findall(r"^\s+\d\. (.*)$", memoire["guilde libertes"], re.M)
        rep = []
        for x in sit:
            rep.append("3" if "corriges" in x else "2" if "copie" in x else "1" if "code" in x else "0")
        return st, "guilde libertes " + " ".join(rep)
    if cmd == "guilde gratuit ? ? ? ?":
        if "guilde gratuit" not in memoire:
            st = tape("guilde gratuit")
        sit = re.findall(r"^\s+\d\. (.*)$", memoire["guilde gratuit"], re.M)
        return st, "guilde gratuit " + " ".join("p" if re.search(r"(secret|personne n'a le droit)", x) else "l" for x in sit)
    if cmd == "guilde licence ?":
        noms = ["bash", "git", "python3", "gcc", "firefox", "vlc", "gimp"]
        n = next(x for x in noms if x not in DEJA)
        DEJA.add(n)
        return st, f"guilde licence {n}"
    if cmd == "guilde faim ?":
        s = lu("grep -rn") or lu("grep -rln")
        m = re.search(r"([\w./-]+\.py):\d+:def etat_de", s)
        return st, f"guilde faim {os.path.basename(m.group(1)) if m else 'satiete.py'}"
    if cmd == "sed -i 's/?/?/' langues/fr.txt":
        if not lu("cat langues/fr.txt"):
            st = tape("cat langues/fr.txt")
        faux, juste = faute_lue()
        return st, f"sed -i 's/{faux}/{juste}/' langues/fr.txt"
    if cmd in ("guilde trou ? ?", "guilde volume ?"):
        s = lu("cat porte_cle.scad")
        if not s:
            st = tape("cat porte_cle.scad")
            s = memoire["cat porte_cle.scad"]
        n = {k: int(v) for k, v in re.findall(r"^(longueur|largeur|epaisseur) = (\d+);", s, re.M)}
        x = int(re.search(r"translate\(\[(\d+),", s).group(1))
        if cmd == "guilde trou ? ?":
            return st, ("guilde trou [{}, {}]" if QUI == "hugo" else "guilde trou {} {}").format(x, n["largeur"] // 2)
        st = tape(f"echo $(({n['longueur']} * {n['largeur']} * {n['epaisseur']}))")
        v = propre(etat["sortie"]).strip()
        return st, f"guilde volume {int(v) / 1000:g} cm3" if QUI == "hugo" else f"guilde volume {v}"
    if cmd == "guilde disque ?":
        s = lu("guilde disques")
        go = int(re.search(r"« (\d+) Go »", s).group(1))
        for l in s.splitlines():
            m = re.match(r"^\s+(sd[a-z])\s+\S+\s+1\s+([\d.]+)([GT])\s+0 disk", l)
            if m:
                taille = float(m.group(2)) * (1024 if m.group(3) == "T" else 1)
                if 0.85 * go <= taille <= go:
                    return st, f"guilde disque {'/dev/' if QUI == 'hugo' else ''}{m.group(1)}"
        return st, "guilde disque ?"
    return st, cmd


def faute(cmd):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    fautes = {"guilde libertes ? ? ? ?": "guilde libertes 0 1 2 3", "guilde licence ?": "guilde licence licornesoft",
              "guilde gratuit ? ? ? ?": "guilde gratuit l l l l", "guilde faim ?": "guilde faim aura.py",
              "gcc bonjour.c -o bonjour && ./bonjour": "gcc bonjour.c -o bonjour.c",
              "sed -i 's/?/?/' langues/fr.txt": None, 'git commit -am "Corrige une faute"': 'git commit -m "Corrige une faute"',
              "guilde trou ? ?": None, "guilde volume ?": "guilde volume 40*24*4", "guilde disque ?": "guilde disque nvme0n1",
              f"dd if={G.IMAGE} of={G.CLE} bs=64k": f"dd if={G.CLE} of={G.IMAGE} bs=64k", "git status": "git statut"}
    if cmd == "sed -i 's/?/?/' langues/fr.txt":
        faux, juste = faute_lue()
        return f"sed 's/{faux}/{juste}/' langues/fr.txt"
    if cmd == "guilde trou ? ?":
        s = lu("cat porte_cle.scad")
        m = re.search(r"^largeur = (\d+);", s, re.M)
        return f"guilde trou 6 {m.group(1) if m else 20}"
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^guilde libertes$", "guilde libertés"), (r"^cat petit_projet/LICENSE$", "head -5 petit_projet/LICENSE"),
        (r"^tree -L 2 code_du_jeu$", "find code_du_jeu -maxdepth 2 -type d"), (r'^grep -rl "faim"', "grep -rln faim code_du_jeu"),
        (r'^grep -rn "def etat_de"', "grep -rn 'def etat_de' code_du_jeu"), (r"^less code_du_jeu", "head -40 code_du_jeu/pc/tg/satiete.py"),
        (r"^gcc bonjour\.c", "cc bonjour.c -o bonjour && ./bonjour"), (r"^od -An", "od -c -N4 bonjour"),
        (r"^git switch -c", "git checkout -b corrige-faute"), (r"^git diff$", "git diff --word-diff"),
        (r"^git log --oneline$", "git log --oneline --graph"), (r"^guilde piece$", "guilde pièce"),
        (r"^head -3 porte_cle\.stl$", "head -n 3 porte_cle.stl"), (r"^sha256sum -c", f"sha256sum --check {G.IMAGE}.sha256"),
        (r"^dd if=", f"cp {G.IMAGE} {G.CLE}"), (r"^guilde sauver$", "guilde vieux-pc"), (r"^guilde cle$", "guilde clé"),
        (r"^make etoiles", "make etoiles; ./etoiles 5"), (r"^cat mur_des_plans", "less mur_des_plans.txt"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "guilde"), "la Guilde devrait être ouverte (niveaux 0 à 4 faits)"
st = tape("cd ~/terrain_terminagotchi/guilde")
for _ in range(400):
    if histoire.fini(st, "guilde"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("gu"):
        st = tape("cd ~/terrain_terminagotchi/guilde")
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
            essais.append(faute(derniere))
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
                and "⚠" not in propre(etat["sortie"]):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
        if essai.startswith(f"dd if={G.CLE}"):
            st = tape("guilde cle")                                # l'image écrasée : l'enfant lit l'indice et remet tout
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

verifier(histoire.fini(st, "guilde"), f"la Guilde traversée, gu0 → gu6 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("guilde.artisan" in ex, "l'exploit « artisan » : la première contribution prête")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
verifier(not any(G.DEV.search(c) for c in TAPEES), "aucune commande tapée n'écrit vers /dev")
C = core.TERRAIN / "guilde/contribution"
if shutil.which("git") and (C / ".git").is_dir():
    verifier(subprocess.run(["git", "-C", str(C), "remote"], capture_output=True, text=True).stdout.strip() == "",
             "le dépôt de la contribution n'a aucun remote (rien ne peut être poussé)")
verifier(G.cle_copiee() and (core.TERRAIN / "guilde/vieux_pc/certificat_pc_sauve.txt").is_file(), "la fausse clé est une copie exacte ; le certificat")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    lus = " ".join(lu_ + " " + propre_ for (_l, _s, c, _code, lu_), propre_ in
                   zip(journal, [""] * len(journal)) if c.startswith(("dd if=" + G.CLE, "guilde disque nvme", "sed 's/", "gcc bonjour.c -o bonjour.c")))
    verifier("sens" in lus and "système" in lus and "-i" in lus and ("PROGRAMME" in lus or not shutil.which("gcc")),
             f"dd à l'envers, le disque du système, sed sans -i, gcc -o bonjour.c : expliqués ({lus[:160]})")
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
