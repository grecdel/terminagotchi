"""⏳ La Bibliothèque du Temps — git (docs/programme.md § 2.13), un monde du Carrefour.

Le onzième monde de la phase 5 (§ 7.14, étape 9). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → temps → requis). Le chapitre et le lieu s'appellent « temps » :
~/terrain_terminagotchi/temps/. On en sort et on y revient, l'étape est gardée. L'image (§ 2.13) : un album de photos qui
remonte le temps ; un commit = une photo avec sa légende ; une branche = un monde parallèle ; une fusion = réunir deux
histoires.

RÈGLES (affichées à l'entrée, registre_du_temps.txt) :
  - TOUS LES DÉPÔTS GIT SONT DANS LE TERRAIN (terrain_terminagotchi/temps) : l'album de l'enfant, le grimoire du jeu, la
    copie de l'ami. Aucun « remote » réel, aucun push, aucun compte : `git push` est seulement RACONTÉ (`temps bateau`).
  - L'identité (user.name, user.email) est une valeur d'EXEMPLE (« Apprenti du Temps », apprenti@temps.invalid : le
    domaine .invalid n'existe pas), réglée DANS le dépôt (git config sans --global, rangé dans album/.git/config). Le jeu
    ne touche jamais ~/.gitconfig ; il prévient si l'enfant tape --global (la créature explique pourquoi on l'évite).
  - Le grimoire du jeu a des dates fixes : ses empreintes sont les mêmes sur tous les ordinateurs (et dans le petit git
    du téléphone, PetitGit.kt : vecteurs donnees/temps/vecteurs.json faits avec le VRAI git).
  - Quand git manque, ses étapes sont cachées et le monde RACONTE ce que git ferait (les commandes `temps …` restent).

LES PALIERS (tp0 à tp5) : la porte ; T1 l'album (git init, l'identité du dépôt, git status, git add, git commit) ; T2
remonter le temps (git log, git diff, git restore ; la formule perdue retrouvée avec git log -S, git show et
git checkout HASH~1 -- fichier : l'exploit « retrouver une version perdue ») ; T3 les mondes parallèles (git switch -c,
deux histoires, git merge, le conflit résolu, git log --graph) ; T4 partager (git clone, la page de l'ami, git pull,
.gitignore, git remote -v ; git push raconté) ; T5 les empreintes (git hash-object = sha1sum, git cat-file : la chaîne
des photos — pont vers la Crypte, K3 ; find -newer — pont de la Citadelle).
"""
import datetime
import hashlib
import json
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import time
import unicodedata

from . import core
from .langue import t
from .plateforme import BOLD, C, DIM, IS_WIN, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "temps.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


def secret(graine):
    """Le numéro de la formule secrète de cette partie (tp.secret.<n>)."""
    return _tire(graine, "secret", donnees()["grimoire"]["secrets"])


def ligne_secrete(graine):
    return f"{donnees()['grimoire']['mot']} : " + t(f"tp.secret.{secret(graine)}")


def photos(graine):
    """Les photos du grimoire : [{message, date, fichiers: {nom: texte}}] (seulement les fichiers que la photo change,
    leur contenu COMPLET). Les dates sont fixes : les empreintes sont les mêmes partout."""
    G = donnees()["grimoire"]
    out = []
    for i, p in enumerate(G["photos"]):
        fich = {}
        for nom, lignes in p["fichiers"].items():
            fich[nom] = "".join((ligne_secrete(graine) if c == "S" else t(c)) + "\n" for c in lignes)
        out.append({"message": t(p["message"]), "date": G["date0"] + i * G["pas"], "fichiers": fich})
    return out


def grimoire_final(graine):
    """{nom: texte} des fichiers du grimoire après la dernière photo (la formule secrète a disparu)."""
    fin = {}
    for p in photos(graine):
        fin.update(p["fichiers"])
    return fin


def a_le_secret(texte, graine):
    return ligne_secrete(graine) in (texte or "").replace("\r\n", "\n").split("\n")


MARQUES = re.compile(r"^(<{7}|={7}|>{7})( |$)", re.M)


def sans_bornes(texte):
    """Le texte n'a plus aucune borne de conflit (<<<<<<<, =======, >>>>>>>)."""
    return MARQUES.search((texte or "").replace("\r\n", "\n")) is None


def garde_tout(texte, *versions):
    """Chaque ligne (non vide) de chaque version est encore dans le texte : on a gardé les deux histoires."""
    lignes = set((texte or "").replace("\r\n", "\n").split("\n"))
    return all(l in lignes for v in versions for l in (v or "").replace("\r\n", "\n").split("\n") if l.strip())


def hash_ok(reponse, juste, minimum=4):
    """Le début d'une empreinte (au moins 4 caractères hexadécimaux) est-il celui de `juste` ?"""
    r = (reponse or "").strip().lower().split("~")[0].split("^")[0]
    return bool(juste) and len(r) >= minimum and re.fullmatch(r"[0-9a-f]+", r) is not None and juste.startswith(r)


def blob_sha(octets):
    """L'empreinte git d'un fichier : SHA-1 de « blob <taille>\\0 » suivi du contenu (ce que fait git hash-object)."""
    return hashlib.sha1(b"blob %d\0" % len(octets) + octets).hexdigest()


# ---------------------------------------------------------------- la pellicule (vue déployée)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def pellicule_de(morceau):
    """(outil, de, vers) d'une commande git (un morceau de ligne), ou None : la première règle de temps.json."""
    m = (morceau or "").strip()
    for r in donnees()["pellicule"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["de"], r["vers"]
    return None


def pellicules_de(ligne):
    return [a for a in (pellicule_de(m) for m in SEPARATEURS.split(ligne or "")) if a]


# ================================================================ l'état, le terrain, le carnet du temps
def g_(state):
    c = state.setdefault("temps", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "temps"


ALBUM, GRIMOIRE, COPIE, EMPREINTES = "album", "grimoire", "copie_de_mon_ami", "empreintes"
CARNET = "carnet_du_temps.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _lire(rel):
    try:
        return (dossier() / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def git_present():
    from .plateforme import terminal_virtuel
    return terminal_virtuel() or shutil.which("git") is not None


# ---------------------------------------------------------------- git, toujours DANS un dépôt du terrain
def _env(extra=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANGUAGE="C", GIT_PAGER="cat", PAGER="cat")
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
        env.pop(k, None)
    env.update(extra or {})
    return env


def _git(args, cwd, extra=None, timeout=20):
    """(code, sortie) d'un git lancé dans `cwd` (jamais ailleurs) ; (1, "") si git manque. Le terminal du jeu
    (Windows) : le petit git du terminal (vsh/git.py), le même que celui que tape l'enfant."""
    from .plateforme import terminal_virtuel
    if terminal_virtuel():
        from .vsh import git as petit
        r = petit.executer(list(args), cwd, core.TERRAIN, extra or {})
        return r.code, (r.texte + "\n" if r.texte and r.code == 0 else "")
    if not git_present():
        return 1, ""
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
                           env=_env(extra), stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def est_depot(d):
    """Un vrai dépôt git du jeu, à lui (pas un dossier dans un autre projet, pas de lien) : seulement là, le jeu lit."""
    d = dossier() / d if not os.path.isabs(str(d)) else d
    g = d / ".git"
    return d.is_dir() and g.is_dir() and not g.is_symlink() and not d.is_symlink()


def depot_sur(d):
    from . import sur
    return est_depot(d) and sur.depot_git_sur(dossier() / d if not os.path.isabs(str(d)) else d)


def _lit(d, *args):
    """La sortie d'un git en LECTURE dans le dépôt d du terrain (album, grimoire…), ou None."""
    if not est_depot(d):
        return None
    code, s = _git(list(args), dossier() / d)
    return s if code == 0 else None


def config_locale(d, cle):
    return (_lit(d, "config", "--local", cle) or "").strip()


def branche(d):
    return (_lit(d, "symbolic-ref", "--short", "-q", "HEAD") or "").strip()


def a_commit(d, ref="HEAD"):
    return _lit(d, "rev-parse", "--verify", "-q", ref + "^{commit}") is not None


def nb_commits(d, rev="HEAD"):
    s = (_lit(d, "rev-list", "--count", rev) or "").strip()
    return int(s) if s.isdigit() else 0


def parents(d, rev="HEAD"):
    s = (_lit(d, "rev-list", "--parents", "-n", "1", rev) or "").split()
    return s[1:]


def principale(d):
    """La branche principale de l'album : main (ou master, avec un vieux git ou sans -b)."""
    for b in ("main", "master"):
        if a_commit(d, "refs/heads/" + b):
            return b
    return "main"


def montre(d, rev, chemin):
    return _lit(d, "show", f"{rev}:{chemin}")


def en_fusion(d):
    return est_depot(d) and (dossier() / d / ".git" / "MERGE_HEAD").is_file()


def historique(d):
    """Les empreintes des photos, de la plus ancienne à la plus récente (premier parent)."""
    return (_lit(d, "rev-list", "--reverse", "--first-parent", "HEAD") or "").split()


# ---------------------------------------------------------------- le grimoire du jeu (dates fixes)
def poser_grimoire(state, neuf=False):
    """Le grimoire : un dépôt du terrain avec 6 photos à dates fixes, signées « Bibliothecaire du Temps », et l'identité
    d'EXEMPLE de l'apprenti réglée dans CE dépôt (sans --global). Sans git : seulement les fichiers d'aujourd'hui.
    Renvoie « git », « deja », « fichiers » ou « rate »."""
    d = dossier() / GRIMOIRE
    if neuf and d.exists():
        k = 1
        while (dossier() / f"{GRIMOIRE}.ancien{k}").exists():
            k += 1
        try:
            d.rename(dossier() / f"{GRIMOIRE}.ancien{k}")
        except OSError:
            return "rate"
    if est_depot(GRIMOIRE) and a_commit(GRIMOIRE):
        return "deja"
    gr = _graine(state)
    if not git_present():
        try:
            d.mkdir(parents=True, exist_ok=True)
            for nom, txt in grimoire_final(gr).items():
                (d / nom).write_text(txt, encoding="utf-8")
        except OSError:
            return "rate"
        return "fichiers"
    if d.exists() and any(d.iterdir()):
        return "rate"                                   # un dossier « grimoire » à l'enfant : on n'y touche pas
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return "rate"
    base = ["-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "-c", "core.autocrlf=false"]
    if _git([*base, "init", "-q"], d)[0] != 0 or not depot_sur(GRIMOIRE):
        return "rate"
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], d)          # (un vieux git sans init.defaultBranch)
    ap, bi = donnees()["identites"]["apprenti"], donnees()["identites"]["bibliothecaire"]
    _git(["config", "user.name", ap["nom"]], d)                   # DANS le dépôt seulement (.git/config)
    _git(["config", "user.email", ap["email"]], d)
    _git(["config", "commit.gpgsign", "false"], d)
    fz = donnees()["grimoire"]["fuseau"]
    for p in photos(gr):
        for nom, txt in p["fichiers"].items():
            with open(d / nom, "w", encoding="utf-8", newline="\n") as f:
                f.write(txt)
        _git([*base, "add", "-A"], d)
        quand = f"{p['date']} {fz}"
        code, _s = _git([*base, "commit", "-q", "-m", p["message"]], d,
                        {"GIT_AUTHOR_NAME": bi["nom"], "GIT_AUTHOR_EMAIL": bi["email"], "GIT_COMMITTER_NAME": bi["nom"],
                         "GIT_COMMITTER_EMAIL": bi["email"], "GIT_AUTHOR_DATE": quand, "GIT_COMMITTER_DATE": quand})
        if code != 0:
            return "rate"
    return "git"


def hash_perte():
    """L'empreinte de la photo qui a perdu la formule secrète (la 5e du grimoire), ou ""."""
    h = historique(GRIMOIRE)
    k = donnees()["grimoire"]["perte"]
    return h[k] if len(h) > k else ""


def hash_apparition():
    h = historique(GRIMOIRE)
    k = donnees()["grimoire"]["apparition"]
    return h[k] if len(h) > k else ""


def retrouvee(state):
    return a_le_secret(_lire(f"{GRIMOIRE}/grimoire.txt"), _graine(state))


def sauvee(state):
    """La formule est dans la DERNIÈRE photo du grimoire (une nouvelle photo, après les 6 du jeu)."""
    n = len(donnees()["grimoire"]["photos"])
    return nb_commits(GRIMOIRE) > n and a_le_secret(montre(GRIMOIRE, "HEAD", "grimoire.txt"), _graine(state))


def propre():
    """Le grimoire d'aujourd'hui est exactement sa dernière photo (le gribouillis est effacé)."""
    txt = _lire(f"{GRIMOIRE}/grimoire.txt")
    h = montre(GRIMOIRE, "HEAD", "grimoire.txt")
    return txt is not None and h is not None and txt.replace("\r\n", "\n") == h and "gribouillis" not in txt


# ---------------------------------------------------------------- l'album de l'enfant
def resolu():
    """Le conflit de la chronique est résolu : plus de bornes, et les deux histoires gardées."""
    txt = _lire(f"{ALBUM}/chronique.txt")
    if txt is None or not sans_bornes(txt):
        return False
    if en_fusion(ALBUM):
        return garde_tout(txt, montre(ALBUM, "HEAD", "chronique.txt"), montre(ALBUM, "MERGE_HEAD", "chronique.txt"))
    return len(parents(ALBUM)) == 2


def poser_ami(state):
    """La page de l'ami : une photo dans la copie (son identité d'EXEMPLE, réglée dans la copie seulement)."""
    if not depot_sur(COPIE) or not a_commit(COPIE):
        return "pas_de_copie"
    am = donnees()["identites"]["ami"]
    d = dossier() / COPIE
    if any(l.strip() == am["email"] for l in (_lit(COPIE, "log", "--format=%ae") or "").split("\n")):
        return "deja"
    _git(["config", "user.name", am["nom"]], d)
    _git(["config", "user.email", am["email"]], d)
    try:
        with open(d / "chronique.txt", "a", encoding="utf-8", newline="\n") as f:
            f.write(t("tp.ami.ligne") + "\n")
    except OSError:
        return "rate"
    base = ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    _git([*base, "add", "chronique.txt"], d)
    code, _s = _git([*base, "commit", "-q", "-m", t("tp.ami.message")], d)
    return "ok" if code == 0 else "rate"


def ami_dans(d):
    am = donnees()["identites"]["ami"]["email"]
    return any(l.strip() == am for l in (_lit(d, "log", "--format=%ae") or "").split("\n"))


def poser_empreintes():
    """Le coin des empreintes : mot.txt (« temps ») et trois fichiers datés pour find -newer (il y a 3, 2 et 1 jours)."""
    d = dossier() / EMPREINTES
    E = donnees()["empreintes"]
    try:
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "mot.txt").exists():
            with open(d / "mot.txt", "w", encoding="utf-8", newline="\n") as f:
                f.write(E["mot"])
        maintenant = time.time()
        for nom, jours in E["dates"].items():
            p = d / nom
            if not p.exists():
                p.write_text(t("tp.empreintes.fichier", nom=nom) + "\n", encoding="utf-8")
            os.utime(p, (maintenant - jours * 86400, maintenant - jours * 86400))
        os.utime(d / "mot.txt", (maintenant - 4 * 86400, maintenant - 4 * 86400))
        return True
    except OSError:
        return False


def meubles(state):
    """Ce que le jeu pose dans la Bibliothèque quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    return {"temps/registre_du_temps.txt": t("tp.meuble.registre", nom=state.get("name", "")) + "\n",
            f"temps/{CARNET}": t("tp.meuble.carnet") + "\n"}


BESOINS = {"tp0": ["registre_du_temps.txt"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de la Bibliothèque : les fichiers dont la leçon a besoin, les ponts."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            try:
                (d / rel).write_text(tous["temps/" + rel], encoding="utf-8")
            except OSError:
                pass
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = g_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("tp.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("tp.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ================================================================ les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
TP = r"^(tg\s+)?temps\s+"
GIT = r"^git\s+"
AL, GR, CO, EM = "temps/album", "temps/grimoire", "temps/copie_de_mon_ami", "temps/empreintes"

FS = {
    "tp_album": lambda: est_depot(ALBUM),
    "tp_nom": lambda: bool(config_locale(ALBUM, "user.name")),
    "tp_email": lambda: bool(config_locale(ALBUM, "user.email")),
    "tp_chronique": lambda: bool((_lire(f"{ALBUM}/chronique.txt") or "").strip()),
    "tp_photo1": lambda: a_commit(ALBUM),
    "tp_propre": lambda: propre(),
    "tp_retrouve": lambda: retrouvee(core.load()),
    "tp_sauvee": lambda: sauvee(core.load()),
    "tp_perdu": lambda: dans_carnet("perdu"),
    "tp_branche": lambda: a_commit(ALBUM, "refs/heads/reve"),
    "tp_reve": lambda: a_commit(ALBUM, "refs/heads/reve") and nb_commits(ALBUM, f"{principale(ALBUM)}..reve") >= 1,
    "tp_sur_main": lambda: branche(ALBUM) in ("main", "master"),
    "tp_balade": lambda: branche(ALBUM) in ("main", "master") and nb_commits(ALBUM, "reve..HEAD") >= 1,
    "tp_conflit": lambda: en_fusion(ALBUM) or len(parents(ALBUM)) == 2,
    "tp_resolu": lambda: resolu(),
    "tp_fusion": lambda: len(parents(ALBUM)) == 2 and not en_fusion(ALBUM),
    "tp_clone": lambda: est_depot(COPIE) and a_commit(COPIE),
    "tp_ami": lambda: ami_dans(COPIE),
    "tp_pull": lambda: ami_dans(ALBUM),
    "tp_ignore": lambda: "*.tmp" in [l.strip() for l in (_lire(f"{ALBUM}/.gitignore") or "").split("\n")],
    "tp_empreintes": lambda: (dossier() / EMPREINTES / "mot.txt").is_file(),
    "tp_bilan": lambda: (dossier() / "certificat_archiviste.txt").is_file(),
}
CREE = {}


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


SED = "sed -i '/^[<=>]\\{7\\}/d' chronique.txt"
LECONS = {
    # la porte de la Bibliothèque
    "tp0": {"titre": "hist.tp0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "temps"}), "cmd": "cd ~/terrain_terminagotchi/temps", "ici": "temps",
         "bravo": ("hist.entree.bravo", {"piece": "temps"})},
        _n("tp0", 1, cmd="ls", re=LS, ou="temps"),
        _n("tp0", 2, cmd="cat registre_du_temps.txt", re=LIRE + r".*registre_du_temps", ou="temps"),
    ]},
    # T1 l'album : le dépôt, son identité d'exemple, l'état, la première photo
    "tp1": {"titre": "hist.tp1.titre", "skill": None, "steps": [
        _n("tp1", 0, cmd="temps album", re=TP + r"album\b", ou="temps"),
        _n("tp1", 1, cmd="git init -b main album", fs="tp_album", outil="git", ou="temps"),
        _n("tp1", 2, cmd="cd album", ici=AL, outil="git"),
        _n("tp1", 3, cmd='git config user.name "Apprenti du Temps"', fs="tp_nom", outil="git", ou=AL),
        _n("tp1", 4, cmd='git config user.email "apprenti@temps.invalid"', fs="tp_email", outil="git", ou=AL),
        _n("tp1", 5, cmd=C('echo "Jour 1" > chronique.txt', 'Set-Content chronique.txt "Jour 1"'), fs="tp_chronique",
           outil="git", ou=AL),
        _n("tp1", 6, cmd="git status", re=GIT + r"status\b", outil="git", ou=AL),
        _n("tp1", 7, cmd="git add chronique.txt", re=GIT + r"add\b", outil="git", ou=AL),
        _n("tp1", 8, cmd='git commit -m "Jour 1"', fs="tp_photo1", outil="git", ou=AL),
    ]},
    # T2 remonter le temps : l'historique, les différences, annuler, la version perdue
    "tp2": {"titre": "hist.tp2.titre", "skill": None, "steps": [
        _n("tp2", 0, cmd="temps grimoire", re=TP + r"grimoire\b", ou="temps"),
        _n("tp2", 1, cmd="cd ~/terrain_terminagotchi/temps/grimoire", ici=GR, outil="git"),
        _n("tp2", 2, cmd="git log --oneline", re=GIT + r"log\b", outil="git", ou=GR),
        _n("tp2", 3, cmd=C('echo "gribouillis" >> grimoire.txt', 'Add-Content grimoire.txt "gribouillis"'),
           re=r"(>>\s*|^(add-content|ac)\b.*)grimoire\.txt|grimoire\.txt.*(>>)", outil="git", ou=GR),
        _n("tp2", 4, cmd="git diff", re=GIT + r"diff\b", outil="git", ou=GR),
        _n("tp2", 5, cmd="git restore grimoire.txt", fs="tp_propre", outil="git", ou=GR),
        _n("tp2", 6, cmd="git log --oneline -S secret", re=GIT + r"log\b.*-S\s*\S", outil="git", ou=GR),
        _n("tp2", 7, cmd="git show ?", re=GIT + r"show\s+[0-9a-fA-F]{4,}", outil="git", ou=GR),
        _n("tp2", 8, cmd="temps perdu ?", fs="tp_perdu"),
        _n("tp2", 9, cmd=C("git checkout ?~1 -- grimoire.txt", "git restore --source=?~1 grimoire.txt"), fs="tp_retrouve",
           outil="git", ou=GR),
        _n("tp2", 10, cmd='git commit -am "Retrouve la formule secrete"', fs="tp_sauvee", outil="git", ou=GR,
           exploit="temps.version"),
    ]},
    # T3 les mondes parallèles : une branche, deux histoires, la fusion et son conflit
    "tp3": {"titre": "hist.tp3.titre", "skill": None, "steps": [
        _n("tp3", 0, cmd="temps branches", re=TP + r"branches?\b"),
        _n("tp3", 1, cmd="git switch -c reve", fs="tp_branche", outil="git", ou=AL),
        _n("tp3", 2, cmd=C('echo "Jour 2 : un reve" >> chronique.txt', 'Add-Content chronique.txt "Jour 2 : un reve"'),
           re=r"(>>\s*|^(add-content|ac)\b.*)chronique\.txt", outil="git", ou=AL),
        _n("tp3", 3, cmd='git commit -am "Le reve"', fs="tp_reve", outil="git", ou=AL),
        _n("tp3", 4, cmd="git switch main", fs="tp_sur_main", outil="git", ou=AL),
        _n("tp3", 5, cmd=C('echo "Jour 2 : une balade" >> chronique.txt', 'Add-Content chronique.txt "Jour 2 : une balade"'),
           re=r"(>>\s*|^(add-content|ac)\b.*)chronique\.txt", outil="git", ou=AL),
        _n("tp3", 6, cmd='git commit -am "La balade"', fs="tp_balade", outil="git", ou=AL),
        _n("tp3", 7, cmd="git merge reve", fs="tp_conflit", outil="git", ou=AL),
        _n("tp3", 8, cmd="cat chronique.txt", re=LIRE + r".*chronique\.txt", outil="git", ou=AL),
        _n("tp3", 9, cmd=C(SED, "notepad chronique.txt"), fs="tp_resolu", outil="git", ou=AL),
        _n("tp3", 10, cmd='git commit -am "Reunit les deux histoires"', fs="tp_fusion", outil="git", ou=AL),
        _n("tp3", 11, cmd="git log --oneline --graph", re=GIT + r"log\b.*--graph", outil="git", ou=AL),
    ]},
    # T4 partager : une copie, la page de l'ami, git pull, .gitignore, d'où vient la copie (git push raconté)
    "tp4": {"titre": "hist.tp4.titre", "skill": None, "steps": [
        _n("tp4", 0, cmd="temps partage", re=TP + r"partage\b"),
        _n("tp4", 1, cmd="git clone . ../copie_de_mon_ami", fs="tp_clone", outil="git", ou=AL),
        _n("tp4", 2, cmd="temps ami", fs="tp_ami", outil="git"),
        _n("tp4", 3, cmd="git log --oneline", re=GIT + r"log\b", outil="git", ou=AL),
        _n("tp4", 4, cmd="git pull ../copie_de_mon_ami", fs="tp_pull", outil="git", ou=AL),
        _n("tp4", 5, cmd=C('echo "*.tmp" > .gitignore', 'Set-Content .gitignore "*.tmp"'), fs="tp_ignore", outil="git",
           ou=AL),
        _n("tp4", 6, cmd=C("touch brouillon.tmp", "New-Item brouillon.tmp"), re=r"^(touch|new-item|ni)\b.*brouillon\.tmp",
           outil="git", ou=AL),
        _n("tp4", 7, cmd="git status", re=GIT + r"status\b", outil="git", ou=AL),
        _n("tp4", 8, cmd="cd ../copie_de_mon_ami", ici=CO, outil="git"),
        _n("tp4", 9, cmd="git remote -v", re=GIT + r"remote\s+-v\b", outil="git", ou=CO),
        _n("tp4", 10, cmd="temps bateau", re=TP + r"bateau\b"),
    ]},
    # T5 les empreintes : git hash-object = sha1sum, la chaîne des photos, find -newer (ponts Crypte et Citadelle)
    "tp5": {"titre": "hist.tp5.titre", "skill": None, "steps": [
        _n("tp5", 0, cmd="temps empreintes", fs="tp_empreintes", ou="temps"),
        _n("tp5", 1, cmd="cd ~/terrain_terminagotchi/temps/empreintes", ici=EM),
        _n("tp5", 2, cmd="git hash-object mot.txt", re=GIT + r"hash-object\b.*mot\.txt", outil="git", ou=EM),
        _n("tp5", 3, cmd="printf 'blob 6\\0temps\\n' | sha1sum", re=r"^printf\b.*blob.*\|\s*sha1sum\b", outil="sha1sum",
           ou=EM, win=False),
        _n("tp5", 4, cmd=C('echo "Temps" > mot.txt', 'Set-Content mot.txt "Temps"'),
           re=r"^(echo|printf|set-content|sc)\b.*mot\.txt", ou=EM),
        _n("tp5", 5, cmd="git hash-object mot.txt", re=GIT + r"hash-object\b.*mot\.txt", outil="git", ou=EM),
        _n("tp5", 6, cmd="cd ../album", ici=AL, outil="git"),
        _n("tp5", 7, cmd="git cat-file -p HEAD", re=GIT + r"cat-file\s+-p\b", outil="git", ou=AL),
        _n("tp5", 8, cmd="cd ../empreintes", ici=EM, win=False),
        _n("tp5", 9, cmd="find . -type f -newer repere.txt", re=r"^find\b.*-newer\s+\S*repere", ou=EM, win=False),
        _n("tp5", 10, cmd="temps bilan", fs="tp_bilan"),
    ]},
}
CHAPITRE = {"id": "temps", "n": 21, "piece": "temps", "famille": "Constructs", "monde": True,
            "lecons": [f"tp{i}" for i in range(6)], "objet": "pendule", "titre": "archiviste_du_temps"}


# ================================================================ l'arbre du Carrefour : quand la Bibliothèque s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "temps"), {})


def _besoin():
    from . import programme
    P = programme.donnees()
    m = _monde()
    chaps = []
    for n in m.get("requis", []):
        chaps += [c for c in P.get("tronc", {}).get(n, []) if c not in chaps]
    return chaps, list(m.get("requis_lecons", []))


def ouvert(state):
    from . import histoire
    chaps, lecs = _besoin()
    if not chaps and not lecs:
        return False
    faits = histoire.h_(state)["faits"]
    return all(histoire.fini(state, c) for c in chaps) and all(l in faits for l in lecs)


def manque(state):
    from . import histoire, lecons
    chaps, lecs = _besoin()
    faits = histoire.h_(state)["faits"]
    out = [histoire.nom_chapitre(c) for c in chaps if not histoire.fini(state, c)]
    for l in lecs:
        if l not in faits:
            ch = histoire.chapitre_de_lecon(l)
            out.append(f"{lecons.tx(histoire.lecon_def(l)['titre'])} ({histoire.nom_chapitre(ch['id']) if ch else '?'})")
    return out


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "temps" in deja or histoire.fini(state, "temps") or not ouvert(state):
        return False
    deja.append("temps")
    core.log(state, t("tp.ouvert.log"))
    core.say(state, histoire.dire(state, "tp.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
GLOBAL = re.compile(r"(^|[;&|]\s*)git\s+config\s+(.*\s)?--(global|system)\b")
POUSSE = re.compile(r"(^|[;&|]\s*)(git\s+push\b|gh\s+(pr|repo|auth)\b|git\s+remote\s+(add|set-url)\b)")


def indice(step, tapees):
    """Un indice de la Bibliothèque : --global, un push, un « ? » recopié, la mauvaise photo, un voyage dans le temps
    entier (HEAD détachée), master au lieu de main, sed sans -i, une identité qui manque."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(GLOBAL.search(l) for l in lignes):
        return t("tp.indice.global")
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("tp.indice.sudo")
    if any(POUSSE.search(l) for l in lignes):
        return t("tp.indice.push")
    if "?" in cmd and any(("?" in l or "…" in l) and (re.match(TP, l) or re.match(GIT, l)) for l in lignes):
        return t("tp.indice.trou")
    if step.get("fs") == "tp_perdu":
        der = [l for l in carnet().splitlines() if l.startswith("[perdu]")]
        if der and not der[-1].endswith("(ok)"):
            return t("tp.indice.apparue" if der[-1].endswith("(apparue)") else "tp.indice.perdu")
    if any(re.match(r"^git\s+checkout\s+[0-9a-f]{4,}\S*\s*$", l) for l in lignes):
        return t("tp.indice.detache")
    if step.get("fs") == "tp_album" and any(re.match(r"^git\s+init\s*$", l) for l in lignes):
        return t("tp.indice.init_nom")
    if step.get("fs") in ("tp_nom", "tp_email") and any(re.match(r"^git\s+config\b", l) for l in lignes):
        return t("tp.indice.config")
    if step.get("fs") in ("tp_photo1", "tp_sauvee", "tp_reve", "tp_balade", "tp_fusion") and \
            any(re.match(r"^git\s+commit\b", l) for l in lignes):
        if step.get("fs") == "tp_photo1" and not (config_locale(ALBUM, "user.name") and config_locale(ALBUM, "user.email")):
            return t("tp.indice.identite")
        if step.get("fs") == "tp_sauvee" and not retrouvee(core.load()):
            return t("tp.indice.pas_retrouvee")
        return t("tp.indice.commit")
    if step.get("fs") == "tp_sur_main" and any(re.match(r"^git\s+(switch|checkout)\s+main\b", l) for l in lignes) and \
            principale(ALBUM) == "master":
        return t("tp.indice.master")
    if step.get("fs") == "tp_resolu" and any(re.match(r"^sed\b(?!.*\s-i)", l) for l in lignes):
        return t("tp.indice.sed_i")
    if step.get("fs") == "tp_resolu" and any(l.startswith(("sed", "nano", "notepad", "vi")) for l in lignes):
        return t("tp.indice.bornes")
    if step.get("fs") == "tp_retrouve" and any(re.match(r"^git\s+(checkout|restore)\b", l) for l in lignes):
        return t("tp.indice.retrouve")
    if step.get("fs") == "tp_pull" and any(re.match(r"^git\s+pull\s*$", l) for l in lignes):
        return t("tp.indice.pull")
    if step.get("fs") == "tp_clone" and any(re.match(r"^git\s+clone\b", l) for l in lignes) and \
            (dossier() / COPIE).exists() and not est_depot(COPIE):
        return t("tp.indice.clone_existe")
    return None


def surveiller(state, lignes):
    """À chaque tour : git config --global (à chaque fois : on ne règle que le dépôt du terrain) ; un push, un remote ou
    une demande de fusion : tout reste dans le terrain (une fois)."""
    if not dossier().is_dir():
        return False
    c = g_(state)
    for l in lignes or []:
        l = (l or "").strip()
        if GLOBAL.search(l):
            msg = t("tp.garde.global")
        elif POUSSE.search(l) and not _fait(c, "garde:pousse"):
            msg = t("tp.garde.local")
        else:
            continue
        core.say(state, msg, 16)
        core.terminal(state, "⚠ " + msg)
        return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


BIBLIO = ["      ╭─────────────╮   ⏳", "   ╭──┤ ▥ ▥ ▥ ▥ ▥ ▥ ├──╮", "   │▥▥│ ▥ ▥ ╭─╮ ▥ ▥ │▥▥│",
          "   │▥▥│ ▥ ▥ │◷│ ▥ ▥ │▥▥│", "  ▁│▁▁│▁▁▁▁▁│▒│▁▁▁▁▁│▁▁│▁"]


def banniere(largeur=None):
    """L'entrée de la Bibliothèque : l'illustration (illustrations.bin, « temps ») si elle existe, sinon le REPLI dessiné
    en caractères (les rayonnages et la grande horloge)."""
    try:
        from . import scenes
        if scenes.disponible("temps"):
            return scenes.illustration("temps", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [179, 215, 229, 141, 117]
    return [f"  {_c(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(BIBLIO)]


def aide():
    return banniere() + [f" {_c(179)}{BOLD}⏳ " + t("tp.aide.titre") + RESET] + ["  " + l for l in t("tp.aide.liste").split("\n")]


def _sans_git():
    return [] if git_present() else ["", f"  {DIM}✖ git{RESET}  " + t("tp.sans_git")]


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def lignes_album():
    out = [f" {_c(229)}{BOLD}📷 " + t("tp.album.titre") + RESET, ""]
    out += [f"  {_c(117)}📁 album{RESET} ──{_c(179)}git init{RESET}──▶ 📁 album + {_c(141)}.git{RESET}  "
            f"──{_c(229)}git add · git commit{RESET}──▶ 🖼"]
    out += [""] + _bloc("tp.album.texte")
    out += ["", f"  {_c(215)}🔏 " + t("tp.album.identite") + RESET]
    noter("album", "lu (ok)")
    return out + _sans_git()


def lignes_grimoire(state, neuf=False):
    etat = poser_grimoire(state, neuf)
    out = [f" {_c(179)}{BOLD}📖 " + t("tp.grimoire.titre") + RESET, ""] + _bloc("tp.grimoire.texte")
    out += ["", "  " + t("tp.grimoire." + etat)]
    noter("grimoire", etat + (" (ok)" if etat in ("git", "deja", "fichiers") else " (faux)"))
    return out + _sans_git()


def lignes_perdu(arg):
    if not est_depot(GRIMOIRE):
        return [t("tp.perdu.sans_grimoire")]
    if not arg:
        return [t("tp.perdu.aide")]
    h, a = hash_perte(), hash_apparition()
    if hash_ok(arg, h):
        noter("perdu", f"{h[:7]} (ok)")
        return [f" {_c(78)}✔ " + t("tp.perdu.ok", h=h[:7]) + RESET, "  " + t("tp.perdu.suite", h=h[:7])]
    if hash_ok(arg, a):
        noter("perdu", f"{a[:7]} (apparue)")
        return [f" {_c(215)}✖ " + t("tp.indice.apparue") + RESET]
    noter("perdu", f"{ascii_bas(arg)[:12]} (faux)")
    return [f" {_c(203)}✖ " + t("tp.indice.perdu") + RESET]


def lignes_branches():
    out = [f" {_c(141)}{BOLD}🌿 " + t("tp.branches.titre") + RESET, ""]
    out += [f"  {_c(179)}●──●{RESET}──{_c(78)}● main{RESET}", f"       ╲", f"        {_c(141)}●── reve{RESET}", ""]
    out += _bloc("tp.branches.texte")
    noter("branches", "lu (ok)")
    return out + _sans_git()


def lignes_conflit():
    out = [f" {_c(203)}{BOLD}⚔ " + t("tp.conflit.titre") + RESET, ""]
    out += [f"  {_c(203)}<<<<<<< HEAD{RESET}      " + t("tp.conflit.ici"), "  Jour 2 : une balade",
            f"  {_c(203)}======={RESET}           " + t("tp.conflit.milieu"), "  Jour 2 : un reve",
            f"  {_c(203)}>>>>>>> reve{RESET}      " + t("tp.conflit.la"), ""]
    out += _bloc("tp.conflit.texte")
    return out


def lignes_partage():
    out = [f" {_c(117)}{BOLD}📚 " + t("tp.partage.titre") + RESET, ""]
    out += [f"  📁 album ──{_c(117)}git clone{RESET}──▶ 📁 copie_de_mon_ami ──✎── 🖼 ──{_c(78)}git pull{RESET}──▶ 📁 album", ""]
    out += _bloc("tp.partage.texte")
    noter("partage", "lu (ok)")
    return out + _sans_git()


def lignes_ami(state):
    r = poser_ami(state) if git_present() else "sans_git"
    noter("ami", r + (" (ok)" if r in ("ok", "deja") else " (faux)"))
    if r in ("ok", "deja"):
        return [f" {_c(78)}✔ " + t("tp.ami." + r) + RESET, "  " + t("tp.ami.suite")]
    return [f" {_c(215)}✖ " + t("tp.ami." + r) + RESET]


def lignes_bateau():
    out = [f" {_c(117)}{BOLD}⛵ " + t("tp.bateau.titre") + RESET, ""]
    out += [f"  📁 album ──{_c(117)}git push{RESET}──▶ ⛵ ──▶ 🏛  " + t("tp.bateau.etagere"), ""]
    out += _bloc("tp.bateau.texte")
    noter("bateau", "lu (ok)")
    return out


def lignes_empreintes():
    ok = poser_empreintes()
    out = [f" {_c(110)}{BOLD}🔏 " + t("tp.empreintes.titre") + RESET, ""] + _bloc("tp.empreintes.texte")
    out += ["", "  " + t("tp.empreintes.pose" if ok else "tp.empreintes.rate")]
    noter("empreintes", "posees (ok)" if ok else "rate (faux)")
    return out + _sans_git()


def bilan_ok(state):
    """Les preuves des paliers : la première photo, la formule retrouvée, la fusion, la page de l'ami."""
    if not git_present():
        return all(dans_carnet(x) for x in ("album", "grimoire", "branches", "partage", "empreintes"))
    fusion = any(len(x.split()) == 3 for x in (_lit(ALBUM, "rev-list", "--parents", "HEAD") or "").split("\n"))
    return a_commit(ALBUM) and sauvee(state) and fusion and ami_dans(ALBUM)


def lignes_bilan(state):
    if not bilan_ok(state):
        return [f" {_c(215)}✖ " + t("tp.bilan.pas_encore") + RESET]
    texte = t("tp.bilan.texte", nom=state.get("name", ""), date=datetime.date.today().isoformat(),
              n=nb_commits(ALBUM) if git_present() else 0)
    try:
        (dossier() / "certificat_archiviste.txt").write_text(texte + "\n", encoding="utf-8")
    except OSError:
        pass
    noter("bilan", "archiviste (ok)")
    return [f" {_c(179)}{BOLD}🏅 " + t("tp.bilan.titre") + RESET, ""] + ["  " + l for l in texte.split("\n")] + \
        ["", "  " + t("tp.bilan.morale")]


def commande(args, sortie=None):
    """tg temps [plan|album|grimoire [neuf]|perdu HASH|branches|conflit|partage|ami|bateau|empreintes|bilan]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide")).replace("-", "_")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        g_(st)
        if sous in ("plan", "registre", "regles"):
            lignes.extend(banniere() + t("tp.meuble.registre", nom=st.get("name", "")).split("\n"))
        elif sous == "album":
            lignes.extend(lignes_album())
        elif sous == "grimoire":
            lignes.extend(lignes_grimoire(st, neuf=bool(reste) and ascii_bas(reste[0]) in ("neuf", "new", "nouveau")))
        elif sous in ("perdu", "perdue"):
            lignes.extend(lignes_perdu(reste[0] if reste else None))
        elif sous in ("branches", "branche"):
            lignes.extend(lignes_branches())
        elif sous == "conflit":
            lignes.extend(lignes_conflit())
        elif sous == "partage":
            lignes.extend(lignes_partage())
        elif sous == "ami":
            lignes.extend(lignes_ami(st))
        elif sous in ("bateau", "push"):
            lignes.extend(lignes_bateau())
        elif sous in ("empreintes", "empreinte"):
            lignes.extend(lignes_empreintes())
        elif sous == "bilan":
            lignes.extend(lignes_bilan(st))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
