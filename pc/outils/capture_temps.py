"""Captures de la Bibliothèque du Temps (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_temps.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Bibliothèque est ouverte
(tronc commun fini). Les commandes du jeu (temps …) passent par le vrai code ; git est le VRAI git, mais SEULEMENT dans
le terrain temporaire : identité d'exemple réglée dans chaque album (jamais --global ; GIT_CONFIG_GLOBAL=/dev/null),
aucun dépôt distant réel, aucun push. Sorties :
  tp_pc_lecon.png      l'écran du jeu (tg) pendant la leçon « L'album »
  tp_pc_album.png      git init, la signature d'exemple, git status, git add, la première photo
  tp_pc_perdu.png      le grimoire : git log -S secret, git show, temps perdu, git checkout EMPREINTE~1 -- grimoire.txt
  tp_pc_conflit.png    deux mondes parallèles, git merge, le conflit lu par temps conflit
  tp_pc_graph.png      les bornes enlevées, la photo de fusion, git log --oneline --graph
  tp_pc_partage.png    git clone, la page de l'ami, git pull, .gitignore, git remote -v, temps bateau
  tp_pc_empreintes.png git hash-object = printf 'blob 6\\0…' | sha1sum, une majuscule change tout, git cat-file -p
  tp_pc_deploie.png    tg deploie "git merge reve" : la pellicule (deux chemins → un chemin) dans la vue déployée
  tp_pc_deploie.gif    la même vue déployée, animée
  tp_pc_repli.png      l'affichage de REPLI tant que l'illustration de la Bibliothèque manque (tg temps)
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
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_tmp_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_PAGER"] = "cat"

from tg import app, core, deploie, histoire, langue, temps as T  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, lecs = T._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["faits"] += [l for l in lecs if l not in h["faits"]]
        h["chap"] = "temps"
        h["ouverts"].append("temps")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "temps"])
        h["faits"] += ["tp0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.tp1.titre"
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "temps").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in T.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="temps"):
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c)
        if mots[0] == "temps":
            buf = io.StringIO()
            T.commande(mots[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            assert "--global" not in c and " push" not in c, c          # jamais la config de l'ordinateur, jamais d'envoi
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            txt = (r.stdout + r.stderr).rstrip("\n")
            if txt:
                out += txt.split("\n")
        core.modifier(lambda s, c=c: T.surveiller(s, [c]))
    out.append(invite)
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "tp_pc_lecon.png")

    session(["git init -q -b main album"])
    lignes = session(['git config user.name "Apprenti du Temps"', 'git config user.email "apprenti@temps.invalid"',
                      'echo "Jour 1" > chronique.txt', "git status", "git add chronique.txt",
                      'git commit -m "Jour 1"'], ici="temps/album")
    ansi_image(lignes, 110, None, 12).convert("RGB").save(sortie / "tp_pc_album.png")

    st = core.load()
    T.poser_grimoire(st)
    h = T.hash_perte()[:7]
    lignes = session(["temps grimoire", "cd grimoire && git log --oneline", "cd grimoire && git log --oneline -S secret",
                      f"cd grimoire && git -c color.ui=always show {h} | tail -6", f"temps perdu {h}",
                      f"cd grimoire && git checkout {h}~1 -- grimoire.txt && git commit -qam 'Retrouve la formule secrete'"
                      " && git log --oneline -2"])
    ansi_image(lignes, 118, None, 11).convert("RGB").save(sortie / "tp_pc_perdu.png")

    session(["git switch -q -c reve", 'echo "Jour 2 : un reve" >> chronique.txt', 'git commit -qam "Le reve"',
             "git switch -q main", 'echo "Jour 2 : une balade" >> chronique.txt', 'git commit -qam "La balade"'],
            ici="temps/album")
    lignes = session(["git merge reve", "cat chronique.txt", "temps conflit"], ici="temps/album")
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "tp_pc_conflit.png")

    lignes = session([T.SED, "cat chronique.txt", 'git commit -qam "Reunit les deux histoires"',
                      "git -c color.ui=always log --oneline --graph"], ici="temps/album")
    ansi_image(lignes, 110, None, 13).convert("RGB").save(sortie / "tp_pc_graph.png")

    session(["git clone -q . ../copie_de_mon_ami"], ici="temps/album")
    T.poser_ami(core.load())
    lignes = session(["temps ami", "cd album && git pull ../copie_de_mon_ami",
                      "cd album && echo '*.tmp' > .gitignore && touch brouillon.tmp && git status -s",
                      "cd copie_de_mon_ami && git remote -v", "temps bateau"])
    ansi_image(lignes, 120, None, 11).convert("RGB").save(sortie / "tp_pc_partage.png")

    T.poser_empreintes()
    lignes = session(["cat mot.txt", "git hash-object mot.txt", "printf 'blob 6\\0temps\\n' | sha1sum",
                      'echo "Temps" > mot.txt', "git hash-object mot.txt",
                      "cd ../album && git cat-file -p HEAD"], ici="temps/empreintes")
    ansi_image(lignes, 110, None, 12).convert("RGB").save(sortie / "tp_pc_empreintes.png")

    ligne = "git merge reve"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "temps" / "album")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "tp_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "tp_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    lignes = session(["temps"])
    ansi_image(lignes, 114, None, 16).convert("RGB").save(sortie / "tp_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de la Bibliothèque du Temps écrites dans", sortie)


if __name__ == "__main__":
    main()
