"""Captures de la Guilde des Bâtisseurs Libres (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_guilde.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Guilde est ouverte (tronc commun
fini). Les commandes du jeu (guilde …) passent par le vrai code ; les autres (grep, gcc, git, sha256sum, dd…) sont
lancées pour de vrai, mais SEULEMENT dans le terrain temporaire : rien n'est installé, rien n'est poussé, et `dd` écrit
un fichier (cle_usb.img), jamais un disque. Sorties :
  gu_pc_lecon.png        l'écran du jeu (tg) pendant la leçon « Le libre »
  gu_pc_libertes.png     les 4 libertés, le quiz, puis les licences (petit projet MIT, bash, git…)
  gu_pc_faim.png         la copie du jeu, puis grep « faim » et « def etat_de » dans le vrai code, la bonne réponse
  gu_pc_bonjour.png      bonjour.c, gcc, ./bonjour, file, les 4 premiers octets (ELF)
  gu_pc_diff.png         la contribution : branche, faute corrigée par sed, git diff, commit, git log
  gu_pc_piece.png        le porte-clé : plan OpenSCAD, trou, volume, fichier STL
  gu_pc_cle.png          la fausse image vérifiée par empreinte, le lsblk fictif, dd vers le FICHIER, empreintes égales
  gu_pc_deploie.png      tg deploie "gcc bonjour.c -o bonjour && ./bonjour" : l'établi dans la vue déployée
  gu_pc_deploie.gif      la même vue déployée, animée
  gu_pc_repli.png        l'affichage de REPLI tant que l'illustration de la Guilde manque (tg guilde)
"""
import io
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_gui_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
os.environ["GIT_PAGER"] = "cat"

from tg import app, core, deploie, histoire, langue, guilde as G  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, lecs = G._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["faits"] += [l for l in lecs if l not in h["faits"]]
        h["chap"] = "guilde"
        h["ouverts"].append("guilde")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde"])
        h["faits"] += ["gu0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.gu1.titre"
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "guilde").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in G.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="guilde"):
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c)
        if mots[0] == "guilde":
            buf = io.StringIO()
            G.commande(mots[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            assert "/dev/" not in c.replace("2>/dev/null", ""), c   # jamais un vrai disque
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            txt = (r.stdout + r.stderr).rstrip("\n")
            if txt:
                out += txt.split("\n")
        core.modifier(lambda s, c=c: G.surveiller(s, [c]))
    out.append(invite)
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "gu_pc_lecon.png")

    st = core.load()
    gr = G._graine(st)
    rep = [str(r) for _n, _i, r in G.libertes_cartes(gr)]
    faux = rep[1:] + rep[:1]
    lignes = session(["guilde libertes", "guilde libertes " + " ".join(faux), "guilde libertes " + " ".join(rep),
                      "head -5 petit_projet/LICENSE", "guilde licence bash", "guilde licence git"])
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "gu_pc_libertes.png")

    G.poser_copie()
    att = G.faim_fichiers(G.fichiers_du_code())
    lignes = session(["guilde copie", 'grep -rl "faim" code_du_jeu/pc/tg | head -8',
                      'grep -rn "def ' 'etat_de" code_du_jeu/pc/tg', "guilde faim aura.py",
                      f"guilde faim {att[0] if att else 'satiete.py'}"])
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "gu_pc_faim.png")

    lignes = session(["cat bonjour.c", "gcc bonjour.c -o bonjour && ./bonjour", "file bonjour",
                      "od -An -tx1 -N4 bonjour"], ici="guilde/atelier")
    ansi_image(lignes, 126, None, 12).convert("RGB").save(sortie / "gu_pc_bonjour.png")

    st = core.load()
    f = G.faute(G._graine(st))
    session(["guilde contribution"])
    lignes = session(["git switch -c corrige-une-faute", f"grep -n {f['faux']} langues/fr.txt",
                      f"sed -i 's/{f['faux']}/{f['juste']}/' langues/fr.txt", "git --no-pager diff --color=always",
                      'git commit -qam "Corrige une faute" && git log --oneline'], ici="guilde/contribution")
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "gu_pc_diff.png")

    st = core.load()
    p = G.piece(G._graine(st))
    lignes = session(["cat porte_cle.scad", "guilde piece", f"guilde trou {p['trou_x']} {p['trou_y']}",
                      f"guilde volume {G.volume(G._graine(st))}", "guilde stl", "head -3 porte_cle.stl"],
                     ici="guilde/fabrique")
    ansi_image(lignes, 126, None, 11).convert("RGB").save(sortie / "gu_pc_piece.png")

    st = core.load()
    G.poser_cle(st)
    nom, _go = G.cle_disque(G._graine(st))
    lignes = session([f"sha256sum -c {G.IMAGE}.sha256", "guilde disques", f"guilde disque {nom}",
                      f"dd if={G.IMAGE} of={G.CLE} bs=64k status=none", f"sha256sum {G.IMAGE} {G.CLE}",
                      "guilde certificat"], ici="guilde/vieux_pc")
    ansi_image(lignes, 126, None, 11).convert("RGB").save(sortie / "gu_pc_cle.png")

    ligne = "gcc bonjour.c -o bonjour && ./bonjour"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "guilde" / "atelier")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "gu_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "gu_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    lignes = session(["guilde"])
    ansi_image(lignes, 114, None, 16).convert("RGB").save(sortie / "gu_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de la Guilde écrites dans", sortie)


if __name__ == "__main__":
    main()
