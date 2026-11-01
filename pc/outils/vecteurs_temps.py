"""Les vecteurs communs de la Bibliothèque du Temps (Python ↔ Kotlin, et VRAI git ↔ petit git du téléphone) :
donnees/temps/vecteurs.json.

    python3 pc/outils/vecteurs_temps.py              écrit les vecteurs (pc/tg/temps.py, pc/tg/deploie.py et le VRAI git)
    python3 pc/outils/vecteurs_temps.py --verifier   code de sortie 1 si la partie « spec » n'est plus à jour (CI)

1. « spec » : la formule secrète de chaque partie, les photos du grimoire (messages, dates, contenus), la ligne secrète,
   les bornes de conflit, « garder les deux histoires », les réponses (empreintes), l'empreinte d'un blob, la pellicule
   (vue déployée) : tests/jvm/Temps.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
2. « git » : des scénarios joués avec le VRAI git (LC_ALL=C, dates fixes, aucune configuration de l'ordinateur : HOME
   jetable, GIT_CONFIG_NOSYSTEM) — l'album de la leçon (init, status, add, commit, log, diff, restore, switch, merge et
   son conflit, clone, pull, remote, hash-object, cat-file, show, le voyage dans le temps entier…) et le grimoire du jeu
   pour plusieurs parties. Le petit git du téléphone (PetitGit.kt) doit écrire EXACTEMENT la même chose et trouver les
   mêmes empreintes (tests/jvm/Temps.kt). Les messages de git peuvent changer d'une version à l'autre : la version
   utilisée est notée ; --verifier ne compare pas cette partie (les empreintes, elles, ne dépendent pas de la version :
   pc/outils/test_temps.py les revérifie avec le git de la machine).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import core, deploie, langue, temps as T  # noqa: E402

FICHIER = RACINE / "donnees" / "temps" / "vecteurs.json"
GRAINES = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123"]
D0 = 1767600000                                   # les dates des commandes de l'album (une minute de plus à chaque fois)


def spec():
    langue.definir("fr")
    parties = []
    for g in GRAINES:
        parties.append({"graine": g, "secret": T.secret(g), "ligne": T.ligne_secrete(g),
                        "photos": T.photos(g), "final": T.grimoire_final(g)})
    textes = ["a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> reve\n", "a\nb\nc\n", "======= pas une borne\n", "x\n=======\n",
              "<<<<<<<HEAD\n", ">>>>>>> \n", "a\r\n<<<<<<< HEAD\r\n"]
    gardes = [{"texte": "Jour 1\nJour 2 : une balade\nJour 2 : un reve\n", "versions": ["Jour 1\nJour 2 : une balade\n", "Jour 1\nJour 2 : un reve\n"]},
              {"texte": "Jour 1\nJour 2 : une balade\n", "versions": ["Jour 1\nJour 2 : une balade\n", "Jour 1\nJour 2 : un reve\n"]},
              {"texte": "Jour 1\r\nJour 2 : un reve\r\nJour 2 : une balade\r\n", "versions": ["Jour 1\nJour 2 : une balade\n", "Jour 1\nJour 2 : un reve\n"]},
              {"texte": "", "versions": ["", "\n"]}]
    hashes = [{"rep": r, "juste": j, "ok": T.hash_ok(r, j)} for r, j in [
        ("6b4cd1e", "6b4cd1e0a9f1"), ("6B4C", "6b4cd1e0a9f1"), ("6b4", "6b4cd1e0a9f1"), ("6b4cd1e~1", "6b4cd1e0a9f1"),
        ("6b4cd1f", "6b4cd1e0a9f1"), ("", "6b4cd1e0a9f1"), ("zzzz", "6b4cd1e0a9f1"), ("6b4cd1e", ""), (" 6b4cd1e ", "6b4cd1e0a9f1"),
        ("6b4cd1e^", "6b4cd1e0a9f1")]]
    blobs = [{"texte": x, "sha": T.blob_sha(x.encode("utf-8"))} for x in ("temps\n", "Temps\n", "", "Jour 1\n", "é\n")]
    lignes = ["git init -b main album", "git status", "git add chronique.txt && git commit -m 'Jour 1'", "git log --oneline -S secret",
              "git diff | head", "git checkout 6b4cd1e~1 -- grimoire.txt", "git checkout -b reve", "git switch main", "git merge reve",
              "git clone . ../copie", "git pull ../copie", "git hash-object mot.txt; git cat-file -p HEAD", "git restore x",
              "git show HEAD", "git branch", "git config user.name x", "ls | wc -l", "git push", "gitk"]
    return {"parties": parties,
            "bornes": [{"texte": x, "sans": T.sans_bornes(x)} for x in textes],
            "garde": [dict(x, ok=T.garde_tout(x["texte"], *x["versions"])) for x in gardes],
            "hashes": hashes, "blobs": blobs,
            "pellicule": [{"ligne": l, "pellicules": [list(a) for a in T.pellicules_de(l)]} for l in lignes],
            "deploie": [{"ligne": l, "pellicules": deploie.pellicules(l)} for l in lignes]}


# ================================================================ les scénarios du VRAI git
class Scenario:
    def __init__(self):
        self.racine = Path(tempfile.mkdtemp(prefix="tg_vec_temps_"))
        self.home = self.racine / "maison"
        self.home.mkdir()
        (self.home / ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n")
        self.t = self.racine / "t"
        (self.t / "temps").mkdir(parents=True)
        self.pas = []
        self.date = D0

    def env(self):
        e = {"HOME": str(self.home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C", "LANGUAGE": "C",
             "TERM": "dumb", "GIT_CONFIG_NOSYSTEM": "1", "GIT_PAGER": "cat", "PAGER": "cat",
             "GIT_AUTHOR_DATE": f"{self.date} +0000", "GIT_COMMITTER_DATE": f"{self.date} +0000"}
        return e

    def git(self, ou, *args):
        r = subprocess.run(["git", "-c", "log.decorate=short", "-c", "advice.defaultBranchName=false", *args],
                           cwd=self.t / ou, env=self.env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        s = r.stdout.decode("utf-8").replace(str(self.t), "{R}")
        self.pas.append({"ou": ou, "action": "git", "args": list(args), "date": self.date, "sortie": s, "code": r.returncode})
        self.date += 60
        return s

    def ecrire(self, ou, fichier, texte, ajout=False):
        p = self.t / ou / fichier
        with open(p, "a" if ajout else "w", encoding="utf-8", newline="\n") as f:
            f.write(texte)
        self.pas.append({"ou": ou, "action": "ecrire", "fichier": fichier, "texte": texte, "ajout": ajout})

    def lire(self, ou, fichier):
        txt = (self.t / ou / fichier).read_text(encoding="utf-8")
        self.pas.append({"ou": ou, "action": "lire", "fichier": fichier, "texte": txt})
        return txt

    def fin(self):
        shutil.rmtree(self.racine, ignore_errors=True)
        return self.pas


def scenario_album():
    """L'album de la leçon, du premier git init jusqu'aux empreintes, plus les erreurs que font les enfants."""
    S = Scenario()
    A, C = "temps/album", "temps/copie_de_mon_ami"
    S.git("temps", "init", "-b", "main", "album")
    S.git(A, "status")
    S.ecrire(A, "chronique.txt", "Jour 1\n")
    S.git(A, "status")
    S.git(A, "add", "chronique.txt")
    S.git(A, "status")
    S.git(A, "commit", "-m", "Jour 1")                                  # pas d'identité : git refuse
    S.git(A, "config", "user.name", "Apprenti du Temps")
    S.git(A, "config", "user.email", "apprenti@temps.invalid")
    S.git(A, "config", "user.name")
    S.git(A, "config", "user.signingkey")
    S.git(A, "status", "--short")
    S.git(A, "commit", "-m", "Jour 1")
    S.git(A, "status")
    S.git(A, "commit", "-m", "rien")
    S.git(A, "log", "--oneline")
    S.git(A, "log")
    S.ecrire(A, "chronique.txt", "tache\n", ajout=True)
    S.git(A, "status")
    S.git(A, "status", "-s")
    S.git(A, "diff")
    S.git(A, "commit", "-m", "rien")
    S.git(A, "restore", "chronique.txt")
    S.git(A, "status")
    S.git(A, "switch", "-c", "reve")
    S.git(A, "branch")
    S.ecrire(A, "chronique.txt", "Jour 2 : un reve\n", ajout=True)
    S.git(A, "commit", "-am", "Le reve")
    S.git(A, "switch", "main")
    S.lire(A, "chronique.txt")
    S.ecrire(A, "chronique.txt", "Jour 2 : une balade\n", ajout=True)
    S.git(A, "commit", "-am", "La balade")
    S.git(A, "merge", "reve")
    S.git(A, "status")
    S.lire(A, "chronique.txt")
    S.ecrire(A, "chronique.txt", "Jour 1\nJour 2 : une balade\nJour 2 : un reve\n")
    S.git(A, "status")
    S.git(A, "commit", "-am", "Reunit les deux histoires")
    S.git(A, "log", "--oneline", "--graph")
    S.git(A, "log", "--oneline")
    S.git(A, "status")
    S.git(A, "clone", ".", "../copie_de_mon_ami")
    S.git(C, "config", "user.name", "Ami du Temps")
    S.git(C, "config", "user.email", "ami@temps.invalid")
    S.ecrire(C, "chronique.txt", "Jour 3 : ton ami dessine ta créature\n", ajout=True)
    S.git(C, "add", "chronique.txt")
    S.git(C, "commit", "-q", "-m", "Ajoute un dessin")
    S.git(C, "status")
    S.git(C, "log", "--oneline")
    S.git(A, "log", "--oneline")
    S.git(A, "pull", "../copie_de_mon_ami")
    S.git(A, "log", "--oneline", "--graph")
    S.ecrire(A, ".gitignore", "*.tmp\n")
    S.ecrire(A, "brouillon.tmp", "")
    S.git(A, "status")
    S.git(A, "status", "-s")
    S.git(C, "remote", "-v")
    S.git(A, "remote", "-v")
    S.git(A, "cat-file", "-p", "HEAD")
    S.git(A, "cat-file", "-p", "HEAD~1")
    S.git(A, "cat-file", "-t", "HEAD")
    S.git(A, "cat-file", "-p", "HEAD^{tree}")
    S.git(A, "show", "HEAD")
    S.git(A, "hash-object", "chronique.txt")
    S.git(A, "rev-parse", "HEAD")
    S.git(A, "checkout", "-b", "essai")
    S.git(A, "switch", "-")
    S.git(A, "branch")
    S.git(A, "switch", "nulle_part")
    S.git(A, "add", "fantome.txt")
    S.git(A, "show", "HEAD~2", "--stat")
    return S.fin()


def scenario_grimoire(g):
    """Le grimoire d'une partie, posé comme le fait le jeu (temps.poser_grimoire), puis ce que fait l'enfant."""
    S = Scenario()
    vieux = core.TERRAIN
    core.TERRAIN = S.t
    try:
        etat = T.poser_grimoire({"partie": g.split(":")[0], "born": int(g.split(":")[1])})
    finally:
        core.TERRAIN = vieux
    assert etat == "git", etat
    G = "temps/grimoire"
    S.pas.append({"ou": "temps", "action": "grimoire", "graine": g})
    S.git(G, "rev-list", "HEAD")
    S.git(G, "log", "--oneline")
    S.git(G, "log", "-n", "2")
    S.git(G, "log", "--oneline", "-S", "secret")
    perte = S.git(G, "rev-list", "--reverse", "HEAD").split()[T.donnees()["grimoire"]["perte"]]
    S.git(G, "show", perte[:7])
    S.ecrire(G, "grimoire.txt", "gribouillis\n", ajout=True)
    S.git(G, "diff")
    S.git(G, "restore", "grimoire.txt")
    S.git(G, "checkout", perte[:7])
    S.git(G, "status")
    S.git(G, "switch", "main")
    S.git(G, "checkout", perte[:7] + "~1", "--", "grimoire.txt")
    S.git(G, "status")
    S.lire(G, "grimoire.txt")
    S.git(G, "commit", "-am", "Retrouve la formule secrete")
    S.git(G, "log", "--oneline", "-S", "secret")
    S.git(G, "restore", "--source=HEAD~3", "grimoire.txt")
    S.git(G, "status", "--short")
    S.git(G, "diff", "--staged")
    S.git(G, "show", "HEAD~6")
    return S.fin()


def git_version():
    return subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()


def vecteurs():
    v = {"spec": spec()}
    if shutil.which("git"):
        langue.definir("fr")
        v["git"] = {"version": git_version(), "album": scenario_album(),
                    "grimoires": [{"graine": g, "pas": scenario_grimoire(g)} for g in GRAINES[:3]]}
    return v


def main():
    if "--verifier" in sys.argv:
        ancien = json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.is_file() else {}
        if ancien.get("spec") != json.loads(json.dumps(spec(), ensure_ascii=False)):
            print("donnees/temps/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_temps.py")
            sys.exit(1)
        print("vecteurs de la Bibliothèque du Temps à jour (spec)")
        return
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit ({git_version()})")


if __name__ == "__main__":
    main()
