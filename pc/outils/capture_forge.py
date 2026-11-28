"""Captures de la Forge (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_forge.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Forge est ouverte (tronc commun
fini). Les commandes du jeu (forge …) passent par le vrai code ; les autres (sh, python3, curl, convert…) sont lancées
pour de vrai, mais SEULEMENT dans le terrain temporaire. Le petit serveur web est lié à 127.0.0.1 et arrêté à la fin.
Sorties :
  fo_pc_lecon.png       l'écran du jeu (tg) pendant la première leçon de la Forge
  fo_pc_recette.png     la recette de la cabane écrite ligne à ligne, lue, lancée avec sh
  fo_pc_parchemin.png   tg deploie "sh cabane.sh" : le parchemin qui s'enflamme (vue déployée)
  fo_pc_parchemin.gif   la même vue, animée
  fo_pc_village.png     la boucle qui crée 10 cabanes, puis ls village | wc -l
  fo_pc_manege.gif      tg deploie de la boucle : le manège qui tourne
  fo_pc_python.png      python3 : la priorité des opérations, une boucle, le Traceback, puis serpent.py Pixel 3
  fo_pc_jeu.png         le mini-jeu : un robot joue (seq | sh), le donjon, forge carte, l'arbre du jeu
  fo_pc_carte.png       la carte du Terminaworld (tg carte) : le jeu de l'enfant est un lieu 🎮
  fo_pc_site.png        la page écrite, servie sur 127.0.0.1 et lue avec curl, puis la lanterne éteinte
  fo_pc_multimedia.png  l'atelier multimédia : le GIF animé de la créature, le son coupé
  creature.gif          le GIF animé fabriqué par la commande de l'enfant (convert / magick)
  fo_pc_exif.png        les métadonnées démasquées puis effacées sur la photo d'exemple (forge exif / nettoie)
"""
import io
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
HOME = os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_forge_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, maison, forge as FO  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402

if os.environ["HOME"] != HOME:                   # capture_port prend son propre HOME en s'important : on reprend le nôtre
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    os.environ["HOME"] = HOME


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, _lecs = FO._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "forge"
        h["ouverts"].append("forge")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                    "observatoire", "donnees", "forge"])
        h["faits"] += ["fo0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in FO.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    core.modifier(lambda s: maison.suivre(s, ["cd ~/terrain_terminagotchi/forge"], str(core.TERRAIN / "forge")))


def session(cmds, ici="forge", entrees=None):
    """Les commandes, comme dans un terminal ; entrees = {commande: texte tapé au clavier, montré après}."""
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c)
        if mots[0] == "forge":
            vieux = os.getcwd()
            os.chdir(d)
            try:
                buf = io.StringIO()
                FO.commande(mots[1:], buf)
                out += buf.getvalue().rstrip("\n").split("\n")
            finally:
                os.chdir(vieux)
            continue
        tape = (entrees or {}).get(c)
        r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=120,
                           input=tape)
        txt = (r.stdout + r.stderr).rstrip("\n")
        if txt:
            out += txt.split("\n")
        core.modifier(lambda s: maison.suivre(s, [c], str(d)))
    out.append(invite)
    return out


def image(lignes, largeur, nom, sortie, taille=14):
    ansi_image(lignes, largeur, None, taille).convert("RGB").save(sortie / nom)


def vue(ligne, sortie, nom_png, nom_gif, phase=0.55, largeur=100):
    d = str(core.TERRAIN / "forge")
    bl = deploie.blocs(ligne)
    actif = 1                                  # le premier bloc : la commande (sh, for…)
    image(deploie.ecran(ligne, bl, actif, None, phase, largeur, d), largeur, nom_png, sortie, 15)
    images = [ansi_image(deploie.ecran(ligne, bl, actif, None, i / 24, largeur - 4, d), largeur - 4, 26, 15).convert("RGB")
              for i in range(24)]
    images[0].save(sortie / nom_gif, save_all=True, append_images=images[1:], duration=120, loop=0)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    F = core.TERRAIN / "forge"

    # 1. la leçon (l'écran du jeu)
    app.etape(spontane=False, defis=False)
    st = core.load()
    image(app.render(st, 0, False).rstrip("\n").split("\n"), 110, "fo_pc_lecon.png", sortie, 15)

    # 2. la recette de la cabane, et le parchemin qui s'enflamme
    lignes = session(["echo '#!/bin/sh' > cabane.sh", "echo 'mkdir -p cabane' >> cabane.sh",
                      "echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh", "cat cabane.sh", "sh cabane.sh",
                      "ls cabane", "chmod +x cabane.sh", "./cabane.sh && echo ok"])
    image(lignes, 100, "fo_pc_recette.png", sortie)
    vue("sh cabane.sh", sortie, "fo_pc_parchemin.png", "fo_pc_parchemin.gif")

    # 3. la boucle qui crée 10 cabanes
    boucle = "for i in $(seq 1 10); do mkdir -p village/cabane_$i; done"
    lignes = session(["ls fantome; echo $?", "forge code 2", boucle, "ls village", "ls village | wc -l"])
    image(lignes, 110, "fo_pc_village.png", sortie)
    vue(boucle, sortie, "fo_pc_manege.png", "fo_pc_manege.gif")

    # 4. Python
    session(["forge serpent"])
    if not (F / "serpent.py").exists():
        (F / "serpent.py").write_text(FO.serpent_py(), encoding="utf-8")
    lignes = session(["python3 --version", 'python3 -c "print(2 + 3 * 4)"',
                      "python3 -c \"for i in range(3): print('Pixel')\"", "python3 serpent.py", "forge erreur IndexError",
                      "python3 serpent.py Pixel 3"])
    image(lignes, 110, "fo_pc_python.png", sortie)

    # 5. le mini-jeu, posé sur la carte
    session(["forge jeu"])
    lignes = session(["seq 1 10 | sh mon_jeu/devinette.sh",
                      "echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_$s; done' > donjon.sh", "sh donjon.sh",
                      'echo "Le trésor est ici !" > mon_jeu/donjon/salle_3/tresor.txt',
                      'forge carte "La grotte de Pixel"',
                      "tree mon_jeu" if shutil.which("tree") else "find mon_jeu | sort"])
    image(lignes, 122, "fo_pc_jeu.png", sortie)
    core.modifier(lambda s: maison.suivre(s, ["cd mon_jeu", "ls", "cd donjon", "ls"], str(F)))
    res = []
    core.modifier(lambda s: res.append(maison.carte(s)))
    image(res[0], 120, "fo_pc_carte.png", sortie, 14)

    # 6. le site web, servi sur 127.0.0.1 et lu avec curl
    session(["forge site"])
    port = FO.port_libre(FO.donnees()["site"]["port"])
    ecrire = ["echo '<h1>Le site de Pixel</h1>' > site/index.html",
              "echo '<p>Pixel adore les commandes.</p>' >> site/index.html",
              "echo 'h1 { color: orange; }' > site/style.css",
              "echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html", "cat site/index.html"]
    lignes = session(ecrire)
    serveur = f"python3 -m http.server {port} --bind 127.0.0.1 --directory site &"
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/forge{RESET}$ "
    proc = subprocess.Popen(["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", "site"],
                            cwd=str(F), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        for _ in range(50):
            if FO._page(port):
                break
            time.sleep(0.1)
        lignes = lignes[:-1] + [invite + serveur, "[1] " + str(proc.pid)]
        r = subprocess.run(["curl", "-s", f"localhost:{port}"], capture_output=True, text=True, timeout=20)
        lignes += [invite + f"curl localhost:{port}"] + r.stdout.rstrip("\n").split("\n")
        r = subprocess.run(["curl", "-s", f"localhost:{port}/style.css"], capture_output=True, text=True, timeout=20)
        lignes += [invite + f"curl localhost:{port}/style.css"] + r.stdout.rstrip("\n").split("\n")
        lignes += [invite + "fg", serveur.rstrip(" &"), "^C", "Keyboard interrupt received, exiting."]
    finally:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    lignes += [invite + f"curl localhost:{port}"]
    r = subprocess.run(["curl", "-s", f"localhost:{port}"], capture_output=True, text=True, timeout=20)
    lignes += (r.stdout + r.stderr).rstrip("\n").split("\n") if (r.stdout + r.stderr).strip() else []
    lignes += [f"{fg(203)}(curl: la lanterne est éteinte, code {r.returncode}){RESET}", invite]
    image(lignes, 118, "fo_pc_site.png", sortie)

    # 7. l'atelier multimédia : le GIF de la créature, le son coupé
    session(["forge multimedia"])
    gif = "magick" if shutil.which("magick") else "convert"
    cmds = ["ls multimedia", f"{gif} -delay 20 -loop 0 multimedia/creature_*.png multimedia/creature.gif",
            "identify multimedia/creature.gif" if shutil.which("identify") else "file multimedia/creature.gif"]
    if shutil.which("sox"):
        cmds.append("sox -n multimedia/la.wav synth 0.5 sine 440")
    if shutil.which("ffmpeg"):
        cmds += ["ffmpeg -loglevel error -i multimedia/fanfare.wav -ss 0.5 -t 0.5 multimedia/fin.wav",
                 "ffprobe -v error -show_entries format=duration -of csv=p=0 multimedia/fin.wav"]
    image(session(cmds), 122, "fo_pc_multimedia.png", sortie)
    if (F / "multimedia" / "creature.gif").exists():
        shutil.copy(F / "multimedia" / "creature.gif", sortie / "creature.gif")

    # 8. les métadonnées démasquées puis effacées (photo d'exemple aux métadonnées inventées)
    ex = "exiftool" if shutil.which("exiftool") else "forge exif"
    lignes = session([f"{ex} multimedia/photo_exemple.jpg", "forge appareil Terminacam",
                      "forge nettoie multimedia/photo_exemple.jpg", "forge exif multimedia/photo_exemple.jpg"])
    image(lignes, 150, "fo_pc_exif.png", sortie)
    image(session(["forge bilan"]), 100, "fo_pc_bilan.png", sortie)
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print(f"captures de la Forge (PC) écrites dans {sortie}")


if __name__ == "__main__":
    main()
