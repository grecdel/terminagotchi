"""Captures de l'Atelier (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_atelier.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), l'Atelier est ouvert (tronc commun
fini). Les commandes du jeu (`atelier …`) passent par le vrai code ; les autres (echo, cat, for, sh cerveau.sh…) sont
lancées pour de vrai dans un vrai bash, mais SEULEMENT dans le terrain temporaire (la boucle appelle `atelier pas` par
une petite doublure, comme l'alias de tg installer). Sorties :
  at_pc_lecon.png     l'écran du jeu (tg) pendant la première leçon de l'Atelier
  at_pc_repli.png     l'affichage de REPLI tant que l'illustration de l'Atelier manque (atelier)
  at_pc_led.png       la LED : ls robot, echo 1 > robot/led, atelier robot
  at_pc_grille.png    la grille et un pas du monde (echo avance > robot/moteur ; atelier pas)
  at_pc_logique.png   ET / OU / NON : [ … ] && … || …, le if sur le capteur, la table de vérité
  at_pc_boucle.png    la boucle de l'essai avec le cerveau d'exemple : 💥 le choc
  at_pc_defi.png      le défi réussi avec le cerveau malin (les 3 derniers pas)
  at_pc_embarque.png  microcontrôleur ou ordinateur ; le réflexe
  at_pc_deploie.png   tg deploie "for i in $(seq 20); do sh cerveau.sh; atelier pas; done" (vue déployée)
  at_pc_deploie.gif   la même vue déployée, animée
"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_ate_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, atelier as A  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
_HOME = os.environ["HOME"]
from capture_port import ansi_image  # noqa: E402   (capture_port pose son propre HOME : on garde le nôtre)
os.environ["HOME"] = _HOME

DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_capture_doublures_"))
(DOUBLURES / "atelier").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                   "from tg import atelier; sys.exit(atelier.commande(sys.argv[1:]) or 0)\" \"$@\"\n")
(DOUBLURES / "atelier").chmod(0o755)
ENV = dict(os.environ, PATH=f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}", COLUMNS="100")


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, _lecs = A._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "robots"
        h["ouverts"].append("robots")
        h.setdefault("mondes_annonces", []).extend(m for m in histoire.MONDES_MODS)
        h["faits"] += ["at0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "robots").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in A.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")


def session(cmds, ici="robots", garder=None):
    """Chaque commande, lancée dans un vrai bash (atelier : le vrai code du jeu, par la doublure) ; garder : ne montrer
    que les N dernières lignes de sortie de la dernière commande."""
    out = []
    d = core.TERRAIN / ici
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for k, c in enumerate(cmds):
        out.append(invite + c)
        r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=180, env=ENV)
        txt = (r.stdout + r.stderr).rstrip("\n").split("\n") if (r.stdout + r.stderr).strip() else []
        if garder and k == len(cmds) - 1:
            txt = ["  …"] + txt[-garder:]
        out += txt
    out.append(invite)
    return out


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    app.etape(spontane=False, defis=False)
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "at_pc_lecon.png")
    ansi_image(session(["atelier"]), 100, None, 15).convert("RGB").save(sortie / "at_pc_repli.png")
    ansi_image(session(["ls robot", "cat robot/led", "echo 1 > robot/led", "atelier robot"]), 100, None, 15).convert("RGB") \
        .save(sortie / "at_pc_led.png")
    session(["echo 0 > robot/led"])
    ansi_image(session(["atelier grille", "echo avance > robot/moteur", "atelier pas", "atelier ou 2 1"]), 100, None, 14) \
        .convert("RGB").save(sortie / "at_pc_grille.png")
    session(["echo droite > robot/moteur", "atelier pas"])
    ansi_image(session(["[ 5 -lt 10 ] && echo vrai || echo faux",
                        'd=$(cat robot/capteur_distance); if [ "$d" -lt 10 ]; then echo obstacle; else echo libre; fi',
                        "atelier verite"]), 110, None, 14).convert("RGB").save(sortie / "at_pc_logique.png")
    session(["cp cerveau_exemple.sh cerveau.sh", "atelier essai"])
    ansi_image(session(["cat cerveau.sh", "for i in $(seq 10); do sh cerveau.sh; atelier pas; done"], garder=16), 110, None, 13) \
        .convert("RGB").save(sortie / "at_pc_boucle.png")
    (core.TERRAIN / "robots" / "cerveau.sh").write_text(A.cerveau_malin(), encoding="utf-8")   # l'enfant l'a écrit dans nano
    session(["atelier defi"])
    ansi_image(session(["cat cerveau.sh", "for i in $(seq 20); do sh cerveau.sh; atelier pas; done"], garder=20), 110, None, 13) \
        .convert("RGB").save(sortie / "at_pc_defi.png")
    ansi_image(session(["atelier embarque", "atelier reflexe"]), 120, None, 13).convert("RGB").save(sortie / "at_pc_embarque.png")
    ligne = "for i in $(seq 20); do sh cerveau.sh; atelier pas; done"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "robots")
    ansi_image(deploie.ecran(ligne, bl, 2, None, 0.6, 100, d), 100, None, 15).convert("RGB").save(sortie / "at_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 2, None, i / 20, 96, d), 96, 26, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "at_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    shutil.rmtree(DOUBLURES, ignore_errors=True)
    print(f"captures de l'Atelier (PC) écrites dans {sortie}")


if __name__ == "__main__":
    main()
