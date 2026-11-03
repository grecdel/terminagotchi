"""Test du démarrage du cyberdeck sur le jeu (installeur/cyberdeck/installer.sh, idée 80), dans un HOME jetable.

    python3 pc/outils/test_cyberdeck.py

1. Installer : le jeu, la commande `terminagotchi`, le bloc dans le profil de connexion (une seule fois, même relancé).
2. Une connexion sur la console du cyberdeck lance le jeu ; quand on le quitte, on reste dans le vrai shell ; une autre
   console (ou une fenêtre de terminal ordinaire) ne lance rien ; le jeu ne se relance pas lui-même.
3. --bureau : le lancement plein écran d'un bureau graphique ; --retirer enlève tout, sauf la créature.
4. Rien d'écrit hors du HOME ; refuse de tourner en administrateur ; jamais de sudo dans le script.
Le vrai matériel n'existe pas encore : le « jeu » est ici un petit faux .pyz qui dit qu'il démarre.
"""
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
SCRIPT = DEPOT / "installeur" / "cyberdeck" / "installer.sh"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


home = Path(tempfile.mkdtemp(prefix="tg_cyberdeck_"))
(home / ".bash_profile").write_text("# le profil d'avant\nexport AVANT=1\n", encoding="utf-8")
(home / ".terminagotchi").mkdir()
(home / ".terminagotchi" / "save.json").write_text('{"name": "Pixel", "xp": 5}', encoding="utf-8")
faux = home.parent / (home.name + "_jeu.pyz")
with zipfile.ZipFile(faux, "w") as z:
    z.writestr("__main__.py", "import sys; print('LE JEU DÉMARRE', *sys.argv[1:])\n")
env = dict(os.environ, HOME=str(home), PATH="/usr/bin:/bin")


def lancer(*args, uid=None):
    return subprocess.run(["sh", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=str(home))


def connexion(console, commandes="echo DANS-LE-SHELL; exit"):
    """Une connexion (shell de connexion bash) : TG_CYBERDECK_TTY fait passer stdin (pas un vrai terminal ici)
    pour la console du cyberdeck."""
    e = dict(env, TG_CYBERDECK_TTY=console)
    return subprocess.run(["bash", "--login"], input=commandes, capture_output=True, text=True, env=e, cwd=str(home))


print("1. Installer")
avant = set(p for p in home.parent.iterdir())
if os.geteuid() == 0:
    # en administrateur, le script refuse ; pour la suite on fait comme un compte ordinaire (id -u imité)
    r = lancer(str(faux))
    verifier(r.returncode == 2 and "pas en administrateur" in r.stdout, "en administrateur (root) : refusé, il faut le compte de l'enfant")
    fbin = home.parent / (home.name + "_bin")
    fbin.mkdir()
    (fbin / "id").write_text("#!/bin/sh\necho 1000\n")
    os.chmod(fbin / "id", 0o755)
    env["PATH"] = f"{fbin}:/usr/bin:/bin"
r = lancer(str(faux))
verifier(r.returncode == 0 and "C'est prêt" in r.stdout, f"installé : « {r.stdout.strip().splitlines()[0] if r.stdout else r.stderr} »")
jeu = home / ".local/share/terminagotchi/terminagotchi.pyz"
verifier(jeu.is_file() and os.access(home / ".local/bin/terminagotchi", os.X_OK), "le jeu et la commande `terminagotchi` sont dans le dossier de l'enfant")
profil = (home / ".bash_profile").read_text(encoding="utf-8")
verifier(profil.startswith("# le profil d'avant\nexport AVANT=1\n") and profil.count(">>> terminagotchi cyberdeck >>>") == 1,
         "le profil d'avant est gardé, le bloc ajouté une fois")
lancer(str(faux))
verifier((home / ".bash_profile").read_text(encoding="utf-8").count(">>> terminagotchi cyberdeck >>>") == 1, "relancé : toujours un seul bloc")

print("2. La connexion sur la console du cyberdeck")
r = connexion("not a tty")
sortie = r.stdout
verifier("LE JEU DÉMARRE" in sortie, "à la connexion sur la console du cyberdeck, le jeu se lance tout seul")
verifier(sortie.index("LE JEU DÉMARRE") < sortie.index("DANS-LE-SHELL") and "Pour revenir au jeu : terminagotchi" in sortie,
         "quand on quitte le jeu, on reste dans le vrai shell (et on sait comment y revenir)")
r = connexion("/dev/tty2")
verifier("LE JEU DÉMARRE" not in r.stdout and "DANS-LE-SHELL" in r.stdout, "une autre console (ou une fenêtre de terminal) : rien ne se lance")
r = connexion("not a tty", "terminagotchi aide; exit")
verifier(r.stdout.count("LE JEU DÉMARRE") == 2 and "LE JEU DÉMARRE aide" in r.stdout, "`terminagotchi` relance le jeu depuis le shell")
r = subprocess.run(["bash", "--login"], input="echo $TG_DANS_LE_JEU; bash --login -c 'echo dedans'; exit", capture_output=True, text=True,
                   env=dict(env, TG_CYBERDECK_TTY="not a tty"), cwd=str(home))
verifier(r.stdout.count("LE JEU DÉMARRE") == 1, "un shell ouvert depuis le jeu ne relance pas le jeu une deuxième fois")
# sans .bash_profile : ~/.profile
h2 = Path(tempfile.mkdtemp(prefix="tg_cyberdeck2_"))
r = subprocess.run(["sh", str(SCRIPT), str(faux)], capture_output=True, text=True, env=dict(env, HOME=str(h2)))
verifier(r.returncode == 0 and ">>> terminagotchi cyberdeck >>>" in (h2 / ".profile").read_text(), "sans ~/.bash_profile : le bloc va dans ~/.profile")

print("3. --bureau, --retirer")
r = lancer(str(faux), "--bureau")
auto = home / ".config/autostart/terminagotchi.desktop"
verifier(auto.is_file() and "plein-ecran.sh" in auto.read_text() and os.access(home / ".local/share/terminagotchi/plein-ecran.sh", os.X_OK),
         "--bureau : un terminal plein écran avec le jeu au démarrage du bureau graphique")
r = lancer("--retirer")
profil = (home / ".bash_profile").read_text(encoding="utf-8")
verifier(r.returncode == 0 and profil == "# le profil d'avant\nexport AVANT=1\n", "--retirer : le profil redevient exactement celui d'avant")
verifier(not auto.exists() and not jeu.exists() and not (home / ".local/bin/terminagotchi").exists(), "… le jeu, la commande et le démarrage du bureau sont enlevés")
verifier((home / ".terminagotchi" / "save.json").read_text() == '{"name": "Pixel", "xp": 5}', "… et la créature est toujours là")
r = connexion("not a tty")
verifier("LE JEU DÉMARRE" not in r.stdout, "après --retirer, la connexion ne lance plus rien")

print("4. Sûreté")
apres = set(p for p in home.parent.iterdir())
nouveaux = {p.name for p in apres - avant}
verifier(all(n.startswith("tg_cyberdeck") for n in nouveaux), f"rien d'écrit hors des HOME d'essai ({sorted(nouveaux)})")
texte = SCRIPT.read_text(encoding="utf-8")
lignes_code = [l for l in texte.splitlines() if not l.lstrip().startswith("#")]
import re
verifier(not any(re.search(r"(^|[;&|(]|then|do)\s*sudo\b", re.sub(r'"[^"]*"', '""', l)) for l in lignes_code), "le script n'appelle jamais sudo (il le conseille seulement à l'adulte, dans un message)")
r = subprocess.run(["sh", str(SCRIPT)], capture_output=True, text=True, env=env)
verifier(r.returncode == 2 and "Utilisation" in r.stdout, "sans le fichier du jeu : explique comment l'utiliser")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
