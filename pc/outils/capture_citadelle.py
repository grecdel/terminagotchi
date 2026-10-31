"""Captures de la Citadelle (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_citadelle.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Citadelle est ouverte (nid,
bibliothèque et cave finis). Sorties :
  cit_pc_lecon.png          l'écran du jeu (tg) pendant la leçon « Les cadenas » (chmod 600)
  cit_pc_terminal.png       une session dans le vrai terminal : ls -l, chmod, citadelle cadenas, le registre, le tableau
  cit_pc_deploie_chmod.png  tg deploie chmod 600 coffre.txt : les cadenas r w x s'allument ou s'éteignent
  cit_pc_deploie.gif        la même vue déployée, animée (avant → après)
  cit_pc_boite.png          une boîte : enquête (grep -r TG{), drapeaux, rempart, l'inspecteur
  cit_pc_repli.png          l'affichage de REPLI tant que l'illustration B3 manque (tg citadelle : la forteresse en caractères)
"""
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_cit_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, citadelle as C, core, deploie, histoire, langue  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402

ICI = None


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)

    def ouvrir(s):
        h = histoire.h_(s)
        for c in ("reveil", "nid", "bibliotheque", "grenier", "cave"):
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
        h["ailes"] = ["reveil", "nid", "bibliotheque", "grenier", "cave"]
        h["chap"] = "citadelle"
        h["ouverts"].append("citadelle")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle"])
        h["faits"].append("cit0")
        s["step"] = 1
        s["xp"] = 10 * 14 ** 2
        s["annonce"] = "hist.cit1.titre"
    core.modifier(ouvrir)
    for d in ("vestibule", "nid", "grenier", "cave", "bibliotheque"):
        (core.TERRAIN / d).mkdir(parents=True, exist_ok=True)
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds):
    out = []
    ici = str(core.TERRAIN / "citadelle")
    for c in cmds:
        out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/citadelle{RESET}$ {c}")
        if c.startswith("citadelle "):
            buf = io.StringIO()
            C.commande(c.split()[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=ici, capture_output=True, text=True, timeout=20)
            out += (r.stdout + r.stderr).rstrip("\n").split("\n")
    out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/citadelle{RESET}$ ")
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "cit_pc_lecon.png")
    lignes = session(["ls -l coffre.txt", "chmod 600 coffre.txt", "citadelle cadenas coffre.txt",
                      'grep ECHEC journaux/acces.log | cut -d " " -f 4 | sort | uniq -c | sort -n', "citadelle tableau"])
    ansi_image(lignes, 120, None, 14).convert("RGB").save(sortie / "cit_pc_terminal.png")
    (core.TERRAIN / "citadelle" / "coffre.txt").chmod(0o644)
    ligne = "chmod 600 coffre.txt"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "citadelle")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "cit_pc_deploie_chmod.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 18, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "cit_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)
    b = C.boite("droits")
    C.fabriquer_boite(st, b)
    gr = C._graine(st)
    lignes = session(["citadelle boites", "ls -l boites/droits", "find boites/droits -perm -o+w", 'grep -r "TG{" boites/droits',
                      "citadelle drapeau " + C.drapeau(gr, "droits", "entree"), "citadelle drapeau " + C.drapeau(gr, "droits", "donjon"),
                      "chmod o-rwx boites/droits/*", "citadelle inspecteur droits"])
    ansi_image(lignes, 120, None, 13).convert("RGB").save(sortie / "cit_pc_boite.png")
    lignes = session(["citadelle"])
    ansi_image(lignes, 104, None, 16).convert("RGB").save(sortie / "cit_pc_repli.png")
    print("captures de la Citadelle écrites dans", sortie)


if __name__ == "__main__":
    main()
