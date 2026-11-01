"""La Bibliothèque du Temps (phase 5, docs/programme.md § 2.13), sur PC.

    python3 pc/outils/test_temps.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/temps/vecteurs.json, mêmes résultats en Kotlin) ; la
     formule secrète, l'empreinte d'un blob (la même que git hash-object), les réponses, les bornes de conflit ;
  2. le grimoire du jeu fait avec le VRAI git de cette machine : les MÊMES empreintes que les vecteurs (elles ne
     dépendent pas de la version de git) — et les mêmes sorties si la version de git est la même ;
  3. l'arbre du Carrefour : fermée tant que le niveau 4 n'est pas fait, puis ouverte et annoncée une fois ; meublée ;
  4. les indices (--global, push, « ? » recopié, la photo apparue au lieu de disparue, HEAD détachée, master, sed sans -i)
     et la garde (--global à chaque fois, push une fois) ;
  5. sans git : les étapes git cachées, le monde RACONTE (temps album, temps grimoire : les fichiers seuls), rien ne casse ;
  6. sécurité : le jeu ne règle jamais ~/.gitconfig (identités d'EXEMPLE dans les dépôts du terrain, domaine .invalid) ;
     aucun remote hors du terrain ; un dossier « grimoire » à l'enfant n'est jamais écrasé ; un .git qui est un lien
     n'est jamais lu ; aucune étape n'utilise --global, push ni sudo ; 14 langues ; la vue déployée (pellicule).
La traversée complète tp0 → tp5 par trois enfants est dans pc/outils/sim_temps.py.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_tmp_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "pc" / "outils"))
GITCONFIG = "[user]\n\tuseConfigOnly = true\n"
Path(os.environ["HOME"], ".gitconfig").write_text(GITCONFIG)

from tg import app, core, deploie, histoire, langue, programme, temps as T  # noqa: E402

HOME = Path.home()
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                          env=dict(os.environ, LC_ALL="C", LANGUAGE="C")).stdout


import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
langue.definir("fr")
A_GIT = shutil.which("git") is not None

print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_temps.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "donnees/temps/vecteurs.json à jour (partie spec) " + r.stdout.strip())
V = json.loads((RACINE / "donnees/temps/vecteurs.json").read_text(encoding="utf-8"))
verifier(len({T.secret(g) for g in (f"{i}:{i * 7}" for i in range(40))}) == T.donnees()["grimoire"]["secrets"],
         "la formule secrète change d'une partie à l'autre (les 5 sortent)")
if A_GIT:
    d = Path(tempfile.mkdtemp())
    for txt in ("temps\n", "Temps\n", "", "é\n"):
        (d / "f").write_bytes(txt.encode())
        verifier(T.blob_sha(txt.encode()) == git("hash-object", str(d / "f")).strip(), f"blob_sha({txt!r}) = git hash-object")
verifier(T.hash_ok("6b4cd1e", "6b4cd1e0") and T.hash_ok("6B4C~1", "6b4cd1e0") and not T.hash_ok("6b4", "6b4cd1e0")
         and not T.hash_ok("?", "6b4cd1e0"), "les réponses : 4 caractères au moins, majuscules et ~1 acceptés")
verifier(not T.sans_bornes("a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> reve\n") and T.sans_bornes("a\n====== presque\n"),
         "les bornes de conflit")
ph = T.photos("1:0")
verifier(len(ph) == 6 and ph[1]["date"] - ph[0]["date"] == 86400 and "secret : " in ph[1]["fichiers"]["grimoire.txt"]
         and "secret : " not in ph[4]["fichiers"]["grimoire.txt"], "le grimoire : 6 photos, la 2e ajoute le secret, la 5e le perd")

print("2. Le grimoire fait avec le vrai git : les mêmes empreintes que les vecteurs (et que le petit git du téléphone)")
if A_GIT and V.get("git"):
    import vecteurs_temps as VT
    for gx in V["git"]["grimoires"]:
        pas = VT.scenario_grimoire(gx["graine"])
        a = next(p["sortie"] for p in gx["pas"] if p["action"] == "git" and p["args"] == ["rev-list", "HEAD"])
        b = next(p["sortie"] for p in pas if p["action"] == "git" and p["args"] == ["rev-list", "HEAD"])
        verifier(a == b, f"grimoire {gx['graine']} : les 6 empreintes identiques ({b.split()[0][:7]}…)")
    meme = V["git"]["version"] == VT.git_version()
    if meme:
        album = VT.scenario_album()
        diff = [(x["args"], x["sortie"][:80], y["sortie"][:80]) for x, y in zip(V["git"]["album"], album)
                if x.get("sortie") != y.get("sortie") or x.get("code") != y.get("code")]
        verifier(not diff and len(album) == len(V["git"]["album"]), f"l'album de la leçon rejoué : les mêmes sorties ({VT.git_version()}) {diff[:2]}")
    else:
        print(f"  · sorties non comparées : vecteurs faits avec {V['git']['version']}, ici {VT.git_version()}")
else:
    print("  · git absent : sauté")

print("3. L'arbre du Carrefour")
st = core.load()
verifier(not T.ouvert(st), f"fermée au début : il manque {T.manque(st)}")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees", "forge", "robots"])
    s["xp"] = 10 * 30 ** 2


core.modifier(ouvrir)
st = core.load()
verifier(T.ouvert(st), "le niveau 4 fait : la Bibliothèque est ouverte")
a1 = core.modifier(lambda s: T.annonce(s))
st = core.load()
verifier("temps" in histoire.h_(st)["mondes_annonces"] and not T.annonce(st), "annoncée une seule fois")
core.TERRAIN.mkdir(exist_ok=True)
(core.TERRAIN / "temps").mkdir(exist_ok=True)
T.meubler(st, "tp0", 0)
verifier((core.TERRAIN / "temps/registre_du_temps.txt").is_file(), "meublée : le registre")
verifier(histoire.PAR_CHAP["temps"]["n"] == 21 and histoire.PAR_CHAP["temps"]["famille"] == "Constructs", "chapitre 21, famille Constructs (git les attire)")

print("4. Les indices et la garde")
step = {"cmd": "temps perdu ?", "fs": "tp_perdu"}
verifier(T.indice({"cmd": 'git config user.name "Apprenti du Temps"', "fs": "tp_nom"},
                  [('git config --global user.name "x"', None)]) == langue.t("tp.indice.global"), "--global : l'indice")
verifier(T.indice({"cmd": "git remote -v"}, [("git push", None)]) == langue.t("tp.indice.push"), "git push : tout reste dans le terrain")
verifier(T.indice({"cmd": "git show ?"}, [("git show ?", None)]) == langue.t("tp.indice.trou"), "le « ? » recopié")
verifier(T.indice({"cmd": "git checkout ?~1 -- grimoire.txt", "fs": "tp_retrouve"}, [("git checkout 6b4cd1e", None)])
         == langue.t("tp.indice.detache"), "git checkout HASH tout seul : HEAD détachée expliquée")
verifier(T.indice({"cmd": T.SED, "fs": "tp_resolu"}, [("sed '/^[<=>]\\{7\\}/d' chronique.txt", None)]) == langue.t("tp.indice.sed_i"),
         "sed sans -i")
verifier(T.indice({"cmd": "git init -b main album", "fs": "tp_album"}, [("git init", None)]) == langue.t("tp.indice.init_nom"),
         "git init sans nom")
avant = core.load()
dits = []
core.say = (lambda vieux: (lambda s, txt, secs=8: (dits.append(txt), vieux(s, txt, secs))[1]))(core.say)
core.modifier(lambda s: T.surveiller(s, ["git config --global user.name x"]))
core.modifier(lambda s: T.surveiller(s, ["git config --global user.email y"]))
core.modifier(lambda s: T.surveiller(s, ["git push"]))
core.modifier(lambda s: T.surveiller(s, ["git push origin main"]))
verifier(sum(1 for x in dits if "--global" in x) == 2 and sum(1 for x in dits if "pousse" in x) == 1,
         "la garde : --global à chaque fois, push une seule fois")

print("5. Les leçons et les commandes, avec et sans git")
st = core.load()
tous = [s for l in T.LECONS.values() for s in l["steps"]]
verifier(not any("--global" in s["cmd"] or "push" in s["cmd"] or "sudo" in s["cmd"] for s in tous), "aucune étape n'utilise --global, push ni sudo")
verifier(all(s.get("outil") == "git" for s in tous if s["cmd"].startswith("git ")), "chaque étape git déclare son outil (cachée si git manque)")
verifier(sum(1 for s in tous if s.get("exploit") == "temps.version") == 1, "un seul exploit : retrouver une version perdue")
vieux_path = os.environ["PATH"]
sans = Path(tempfile.mkdtemp())
for outil in ("sh", "bash", "ls", "cat", "env"):
    if shutil.which(outil):
        os.symlink(shutil.which(outil), sans / outil)
os.environ["PATH"] = str(sans)
try:
    vus = histoire.etapes_visibles(st, "tp1") if hasattr(histoire, "etapes_visibles") else None
    out = __import__("io").StringIO()
    T.commande(["album"], sortie=out)
    verifier("git n'est pas installé" in out.getvalue(), "sans git : temps album le raconte")
    out = __import__("io").StringIO()
    T.commande(["grimoire"], sortie=out)
    verifier((core.TERRAIN / "temps/grimoire/grimoire.txt").is_file() and not (core.TERRAIN / "temps/grimoire/.git").exists(),
             "sans git : le grimoire d'aujourd'hui seulement (sans photos)")
    vis = [s["cmd"] for s in histoire.lecon_def("tp2")["steps"]] if False else None
    from tg import histoire as H
    caches = [s["cmd"] for s in H.NOUVELLES["tp2"]["steps"] if s.get("outil") and not H._outil(s["outil"])]
    verifier(len(caches) >= 8, f"sans git : {len(caches)} étapes git cachées dans T2 (les commandes du jeu restent)")
finally:
    os.environ["PATH"] = vieux_path
    shutil.rmtree(core.TERRAIN / "temps/grimoire", ignore_errors=True)

if A_GIT:
    out = __import__("io").StringIO()
    T.commande(["grimoire"], sortie=out)
    G = core.TERRAIN / "temps/grimoire"
    verifier(T.est_depot("grimoire") and T.nb_commits("grimoire") == 6, "le grimoire : 6 photos")
    verifier(git("config", "--local", "user.email", cwd=G).strip() == "apprenti@temps.invalid" and
             git("log", "--format=%ae", cwd=G).split() == ["bibliothecaire@temps.invalid"] * 6, "identités d'EXEMPLE (.invalid), dans le dépôt seulement")
    out = __import__("io").StringIO()
    T.commande(["perdu", T.hash_apparition()[:7]], sortie=out)
    verifier("APPARUE" in out.getvalue() and not T.dans_carnet("perdu"), "temps perdu : la photo où la formule est apparue est refusée, expliquée")
    out = __import__("io").StringIO()
    T.commande(["perdu", T.hash_perte()[:5].upper()], sortie=out)
    verifier(T.dans_carnet("perdu") and "~1" in out.getvalue(), "temps perdu : la bonne photo (5 caractères, majuscules) ; la suite ~1")
    # un dossier « grimoire » à l'enfant n'est jamais écrasé
    shutil.rmtree(G)
    G.mkdir()
    (G / "mes_notes.txt").write_text("à moi\n")
    verifier(T.poser_grimoire(core.load()) == "rate" and (G / "mes_notes.txt").read_text() == "à moi\n", "un dossier « grimoire » à l'enfant n'est pas touché")
    out = __import__("io").StringIO()
    T.commande(["grimoire", "neuf"], sortie=out)
    verifier((core.TERRAIN / "temps/grimoire.ancien1/mes_notes.txt").is_file() and T.nb_commits("grimoire") == 6,
             "temps grimoire neuf : l'ancien est mis de côté (grimoire.ancien1), un nouveau grimoire")
    # un .git qui est un lien vers ailleurs n'est jamais lu
    ail = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(ail)], capture_output=True)
    (core.TERRAIN / "temps/album").mkdir(exist_ok=True)
    os.symlink(ail / ".git", core.TERRAIN / "temps/album/.git")
    verifier(not T.est_depot("album") and not T.FS["tp_album"](), "un .git qui est un lien vers un autre projet : ignoré")
    (core.TERRAIN / "temps/album/.git").unlink()
    # master au lieu de main
    subprocess.run(["git", "-c", "init.defaultBranch=master", "init", "-q", "album"], cwd=core.TERRAIN / "temps", capture_output=True)
    A = core.TERRAIN / "temps/album"
    git("config", "user.name", "Apprenti du Temps", cwd=A)
    git("config", "user.email", "apprenti@temps.invalid", cwd=A)
    (A / "chronique.txt").write_text("Jour 1\n")
    git("add", ".", cwd=A)
    git("commit", "-qm", "Jour 1", cwd=A)
    git("switch", "-qc", "reve", cwd=A)
    verifier(T.principale("album") == "master" and not T.FS["tp_sur_main"](), "un album « master » (vieux git) : reconnu")
    verifier(T.indice({"cmd": "git switch main", "fs": "tp_sur_main"}, [("git switch main", None)]) == langue.t("tp.indice.master"),
             "git switch main dans un album master : l'indice dit master")
    git("switch", "-q", "master", cwd=A)
    verifier(T.FS["tp_sur_main"](), "git switch master : l'étape passe")

print("6. Sécurité, langues, vue déployée")
verifier((HOME / ".gitconfig").read_text() == GITCONFIG, "~/.gitconfig jamais touché par le jeu")
if A_GIT:
    depots = [p.parent for p in (core.TERRAIN / "temps").rglob(".git") if p.is_dir()]
    verifier(all(not git("remote", cwd=p).strip() for p in depots), "aucun remote dans les dépôts posés par le jeu")
cles = [k for k in json.loads((RACINE / "pc/tg/langues/fr.json").read_text(encoding="utf-8")) if k.startswith(("tp.", "hist.tp"))]
manque = {}
for code in ("fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"):
    for dos, pc in (("pc/tg/langues", True), ("app/src/main/assets/langues", False)):
        d = json.loads((RACINE / dos / f"{code}.json").read_text(encoding="utf-8"))
        m = [k for k in cles if k not in d]
        if m:
            manque[f"{dos}/{code}"] = m[:3]
verifier(len(cles) > 250 and not manque, f"{len(cles)} textes de la Bibliothèque dans les 14 langues (PC et Android) {manque}")
p = deploie.pellicules("git add chronique.txt && git commit -m x | head -1; git log --oneline")
verifier([x["outil"] for x in p] == ["git add", "git log"] and p[0]["vers"] == "objectif",
         f"la pellicule : git add devant l'objectif, git log la pellicule (git commit reste à l'établi de la Guilde) {p}")
P = programme.donnees()
m = next(x for x in P["mondes"] if x["id"] == "temps")
verifier(m["variantes_reservees"] == ["momiaou:soleil", "galetard:ruines", "follanterne:brume"] and m["requis"] == ["n4"],
         "programme.json : prérequis niveau 4, variantes EXISTANTES réservées (Roche, Ombre)")
autres = {v for x in P["mondes"] if x["id"] != "temps" for v in x.get("variantes_reservees", [])}
gardiens = set(next(x for x in P["mondes"] if x["id"] == "citadelle").get("gardiens", {}).values())
verifier(not (set(m["variantes_reservees"]) & autres) and not any(v.split(":")[0] in gardiens for v in m["variantes_reservees"]),
         "ni gardien de la Citadelle, ni variante déjà réservée par un autre monde")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
