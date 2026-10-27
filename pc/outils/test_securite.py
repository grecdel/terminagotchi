"""Test de sûreté et de robustesse côté PC (d'après les attaques de « Karim », simulation des personas avancés).

    python3 pc/outils/test_securite.py
    (en root, lancer sous `setpriv --bounding-set -dac_override,-dac_read_search` pour que chmod 000 compte)

  - le jeu n'écrit jamais à travers un lien symbolique : nid/repas.txt → dehors, carnet → un autre dépôt git
    (sa configuration n'est pas touchée), la zone entière → ~/Documents (rien n'y est construit ni effacé),
    ~/.terminagotchi/save.tmp → dehors ; la créature explique quel lien gêne ;
  - git config seulement dans le vrai carnet du jeu (pas un .git « gitdir: » qui renvoie ailleurs) ;
  - chmod 000 (zone, nid, ~/.terminagotchi), disque plein : jamais de trace Python (etape, tg …, veille),
    un message gentil ;
  - save.json abîmé : la copie de secours (save.json.bak) revient, le fichier abîmé est gardé à côté, on le dit ;
    sans copie de secours : gardé à côté, dit, puis seulement un nouvel œuf ;
  - l'horloge qui recule ne fait pas dépasser 100 à la faim.
"""
import builtins
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path(tempfile.mkdtemp(prefix="tg_securite_"))
os.environ["HOME"] = str(HOME)
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["GIT_CONFIG_GLOBAL"] = str(HOME / ".gitconfig_vide")
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    os.environ[k] = "http://127.0.0.1:9"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
from tg import app, core, entrainement, histoire, langue, sur, terrain  # noqa: E402

ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def etape(cwd=None):
    try:
        return app.etape(spontane=False, defis=False, cwd=str(cwd or core.TERRAIN)), None
    except Exception as e:                       # noqa: BLE001
        return None, e


def bulles(st):
    return " | ".join(b if isinstance(b, str) else str(b[0]) for b in [st.get("bubble", "")] + list(st.get("bubbles", [])))


def tout_dit(st):
    return json.dumps(st, ensure_ascii=False)


T = core.TERRAIN
DEHORS = HOME.parent / (HOME.name + "_dehors")
DEHORS.mkdir()
(DEHORS / "important.txt").write_text("ne pas toucher\n")
builtins.input = lambda p="": "Karim"
langue.definir("fr")
app.creer_si_besoin(avec_intro=False)
(T / "nid").mkdir(parents=True, exist_ok=True)
(T / "nid" / "repas.txt").write_text("pomme\n")
st, err = etape()
verifier(st is not None and err is None, "une partie de départ")

print("1. Le jeu n'écrit jamais à travers un lien symbolique")
p = T / "nid" / "repas.txt"
p.unlink()
p.symlink_to(DEHORS / "repas_vole.txt")                 # lien pendant vers l'extérieur
s = core.load()
s["step"] = 0
ancien = terrain._lid
terrain._lid = lambda st: "t3"
try:
    remis, _ = terrain.reparer_lecon(s)
finally:
    terrain._lid = ancien
verifier(not (DEHORS / "repas_vole.txt").exists(), "nid/repas.txt → dehors : la réparation n'écrit pas à travers le lien")
verifier(remis == [], "… et ne dit pas « remis » ce qu'elle n'a pas pu poser")
try:
    p.write_text("x")
    verifier(False, "écriture directe à travers le lien : refusée (HorsZone)")
except sur.HorsZone:
    verifier(True, "écriture directe à travers le lien : refusée (HorsZone)")
st, err = etape()
verifier(err is None and "repas.txt" in tout_dit(st) and "rm " in tout_dit(st), "la créature dit quel lien gêne et comment l'enlever")
p.unlink()
p.write_text("pomme\n")

autre = DEHORS / "mon_projet"
subprocess.run(["git", "init", "-q", str(autre)], check=True)
car = T / "carnet"
car.symlink_to(autre)
core.modifier(lambda s: histoire.h_(s).pop("git_signe", None))
st, err = etape()
r = subprocess.run(["git", "-C", str(autre), "config", "--local", "user.name"], capture_output=True, text=True)
verifier(err is None and not r.stdout.strip(), "carnet = lien vers un autre dépôt : sa configuration git n'est pas modifiée")
s = core.load()
verifier(not histoire.signer_carnet(s), "signer_carnet refuse le lien")
car.unlink()
car.mkdir()
(car / ".git").write_text(f"gitdir: {autre}/.git\n")      # un .git « fichier » qui renvoie vers un autre projet
verifier(not sur.depot_git_sur(car) and not histoire.signer_carnet(core.load()), "carnet/.git qui renvoie ailleurs : refusé")
r = subprocess.run(["git", "-C", str(autre), "config", "--local", "user.name"], capture_output=True, text=True)
verifier(not r.stdout.strip(), "… l'autre dépôt reste intact")
shutil.rmtree(car)
subprocess.run(["git", "init", "-q", str(car)], check=True)
verifier(sur.depot_git_sur(car) and histoire.signer_carnet(core.load()), "le vrai carnet du jeu : signé")
r = subprocess.run(["git", "-C", str(car), "config", "--local", "user.name"], capture_output=True, text=True)
verifier(r.stdout.strip() == "Karim", f"… dans carnet/.git/config seulement ({r.stdout.strip()!r})")
shutil.rmtree(car)

docs = HOME / "Documents"
docs.mkdir()
(docs / "rapport.odt").write_text("mon travail")
sauve = HOME / "terrain_sauve"
T.rename(sauve)
T.symlink_to(docs)
st, err = etape()
r = entrainement.commencer(core.load())
st2, err2 = etape()
verifier(err is None and err2 is None, "zone = lien vers ~/Documents : pas de plantage")
verifier(sorted(x.name for x in docs.iterdir()) == ["rapport.odt"], f"… rien n'est construit dans ~/Documents ({sorted(x.name for x in docs.iterdir())})")
verifier((docs / "rapport.odt").read_text() == "mon travail", "… et rien n'y est effacé ni modifié")
verifier("terrain_terminagotchi" in tout_dit(st2 or st or {}), "… et la créature dit que la zone est un lien")
T.unlink()
sauve.rename(T)

tmp = core.SAVE_DIR / "save.tmp"
tmp.symlink_to(DEHORS / "vole.json")
st, err = etape()
verifier(err is None and not (DEHORS / "vole.json").exists(), "~/.terminagotchi/save.tmp → dehors : la sauvegarde n'écrit pas à travers")
verifier(core.load() is not None and core.load()["name"] == "Karim", "… et elle est bien enregistrée")
if tmp.is_symlink():
    tmp.unlink()
lien_save = HOME / "ailleurs.json"
try:
    os.symlink(DEHORS / "important.txt", core.SAVE_DIR / "creature.key")
    from tg import notif
    try:
        notif.image(core.load())
    except OSError:
        pass
    verifier((DEHORS / "important.txt").read_text() == "ne pas toucher\n", "un lien dans ~/.terminagotchi (creature.key) : jamais suivi")
finally:
    if (core.SAVE_DIR / "creature.key").is_symlink():
        (core.SAVE_DIR / "creature.key").unlink()

print("2. Droits retirés, disque plein : jamais de trace Python")
root_ignore = os.geteuid() == 0 and os.access(str(DEHORS), os.W_OK) and (lambda: (os.chmod(DEHORS, 0), os.access(str(DEHORS), os.R_OK), os.chmod(DEHORS, 0o755))[1])()
if root_ignore:
    print("  (root avec CAP_DAC_OVERRIDE : chmod 000 ne compte pas, lancer sous setpriv ; parties sautées)")
else:
    for cible in (T, T / "nid", core.SAVE_DIR):
        os.chmod(cible, 0)
        try:
            st, err = etape()
            msg = str(err) if isinstance(err, core.Probleme) else ""
            verifier(err is None or isinstance(err, core.Probleme), f"chmod 000 {cible.relative_to(HOME)} : etape() ne plante pas ({type(err).__name__ if err else 'ok'})")
            if cible == core.SAVE_DIR:
                verifier("chmod" in msg and "Traceback" not in msg, f"… le message dit comment rendre la clé ({msg[:80]})")
            env = dict(os.environ, PYTHONPATH=str(RACINE / "pc"))
            for args in (["carte"], ["--une-fois"]):
                r = subprocess.run([sys.executable, "-m", "tg", *args], capture_output=True, text=True, env=env, timeout=60,
                                   stdin=subprocess.DEVNULL)
                verifier("Traceback" not in r.stdout + r.stderr, f"`tg {' '.join(args)}` avec {cible.name} en 000 : pas de trace Python")
            r = subprocess.run([sys.executable, "-c", "import sys,signal; sys.argv=['tg','veille']; signal.alarm(3)\n"
                                "from tg import app\ntry:\n    app.main()\nexcept BaseException as e:\n    print('FIN', type(e).__name__)"],
                               capture_output=True, text=True, env=env, timeout=60)
            verifier("Traceback" not in r.stdout + r.stderr, f"`tg veille` avec {cible.name} en 000 : ne meurt pas sur une trace")
        finally:
            os.chmod(cible, 0o755)
    os.chmod(core.SAVE_FILE, 0)
    try:
        builtins.input = lambda p="": "Nouveau"
        try:
            app.creer_si_besoin(avec_intro=False)
            verifier(False, "save.json en 000 puis `tg` : pas de nouvelle créature")
        except core.Probleme as e:
            verifier("chmod" in str(e), f"save.json en 000 puis `tg` : pas de nouvelle créature, on explique ({str(e)[:60]})")
    finally:
        os.chmod(core.SAVE_FILE, 0o644)
    verifier(core.load()["name"] == "Karim", "… la partie est toujours là")

pid = os.fork()
if pid == 0:
    import signal
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (64, 64))
    try:
        s = app.etape(spontane=False, defis=False, cwd=str(T))
        os._exit(0 if s and s.get("_pas_sauve") else 4)
    except BaseException:
        os._exit(3)
_, code = os.waitpid(pid, 0)
verifier(code >> 8 == 0, f"disque plein pendant la sauvegarde : etape() continue et le dit (code {code >> 8})")
verifier(core.load() is not None and core.load()["name"] == "Karim", "… la sauvegarde reste lisible")
try:
    with core.verrou():
        pass
    verifier(True, "verrou : pas d'attente infinie")
except Exception as e:                           # noqa: BLE001
    verifier(False, f"verrou : {e}")

print("3. Sauvegarde abîmée : copie de secours, jamais de remplacement en silence")
for b in core._secours():
    if b.exists():
        b.unlink()
s = core.load()
s["xp"] = 4242
core.save(s)
verifier(core._secours()[0].exists(), "save.json.bak existe après une sauvegarde")
bon = json.loads(core._secours()[0].read_text())
core.SAVE_FILE.write_text("{ pas du json")
st = core.load()
verifier(st is not None and st["name"] == "Karim" and st["xp"] == bon["xp"], f"save.json abîmé : la copie de secours revient (xp {st and st['xp']})")
casses = [x.name for x in core.SAVE_DIR.iterdir() if x.name.startswith("save.json.casse-")]
verifier(len(casses) == 1, f"… le fichier abîmé est gardé à côté ({casses})")
builtins.input = lambda p="": "Nouveau"
app.creer_si_besoin(avec_intro=False)
verifier(core.load()["name"] == "Karim", "`tg` après : la créature n'est pas remplacée")
st, err = etape()
verifier(err is None and "copie" in tout_dit(st), "la créature dit qu'elle a repris sa copie de secours")
for b in core._secours():
    if b.exists():
        b.unlink()
core.SAVE_FILE.write_text("{ pas du json")
verifier(core.etat_sauvegarde() == "abimee", "sans copie de secours : « abîmée » (pas « absente »)")
try:
    etape_err = app.etape(spontane=False, defis=False)
    verifier(False, "etape() avec une sauvegarde abîmée : Probleme expliqué")
except core.Probleme as e:
    verifier("tg" in str(e), f"etape() avec une sauvegarde abîmée : expliqué ({str(e)[:60]})")
avant = set(x.name for x in core.SAVE_DIR.iterdir())
from io import StringIO  # noqa: E402
vrai_stdout, sys.stdout = sys.stdout, StringIO()
try:
    app.creer_si_besoin(avec_intro=False)
    dit = sys.stdout.getvalue()
finally:
    sys.stdout = vrai_stdout
gardes = [x for x in core.SAVE_DIR.iterdir() if x.name.startswith("save.json.casse-") and x.read_text() == "{ pas du json"]
verifier(gardes and "casse" in dit, f"… `tg` la range à côté et le dit avant de faire éclore un nouvel œuf ({dit.strip()[:70]})")
verifier(core.load()["name"] == "Nouveau", "… puis un nouvel œuf")

print("4. Divers")
s = core.load()
s["hunger"] = 90
s["last_tick"] = time.time() + 3 * 86400
core.tick(s)
verifier(0 <= s["hunger"] <= 100, f"l'horloge recule de 3 jours : faim {s['hunger']:.0f} (entre 0 et 100)")
verifier((DEHORS / "important.txt").read_text() == "ne pas toucher\n" and sorted(x.name for x in DEHORS.iterdir()) == ["important.txt", "mon_projet"],
         f"à la fin : rien n'a été écrit hors des lieux du jeu ({sorted(x.name for x in DEHORS.iterdir())})")

shutil.rmtree(DEHORS, ignore_errors=True)
shutil.rmtree(HOME, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
