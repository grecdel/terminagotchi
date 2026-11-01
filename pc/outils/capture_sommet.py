"""Captures du Sommet (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_sommet.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), trois mondes sont au palier 3 (le
Port, la Citadelle, la Salle des Rouages), le Sommet est ouvert. Les commandes du jeu (sommet …) passent par le vrai
code ; les autres (bash, sed, grep, find, xargs…) sont lancées pour de vrai, mais SEULEMENT dans le terrain temporaire.
  som_pc_lecon.png     l'écran du jeu (tg) pendant la première leçon du Sommet
  som_pc_repli.png     l'affichage de REPLI tant que l'illustration du Sommet manque (sommet)
  som_pc_fragile.png   le script qui ment (code 0), set -euo pipefail (code 1), les guillemets (la vraie sauvegarde)
  som_pc_bivouac.png   sale.sh oublie son brouillon, bivouac.sh le range (trap, mktemp, getopts)
  som_pc_regex.png     le journal : ancres, grep -o, sed -E et ses captures
  som_pc_eboulis.png   find -print0 | xargs -0, $( ), <( )
  som_pc_debug.png     bash -n, bash -x : la ligne 8 et la variable totl
  som_pc_ctf.png       le CTF combiné : trois fragments, le drapeau, le chrono et l'exploit
  som_pc_defi.png      le défi du jour (salle d'entraînement) et les records
  som_pc_deploie.png   tg deploie "bash -n casse.sh && bash casse.sh" (la cordée)
  som_pc_deploie.gif   la même vue déployée, animée
"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_som_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, sommet as S  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)

    def ouvrir(s):
        h = histoire.h_(s)
        for c in ("reveil", "nid", "bibliotheque", "cave"):
            h["faits"] += [x for x in histoire.PAR_CHAP[c]["lecons"] if x not in h["faits"]]
            if c not in h["ailes"]:
                h["ailes"].append(c)
        for c in ("port", "citadelle", "machinerie"):
            h["faits"] += [x for x in histoire.PAR_CHAP[c]["lecons"][:4] if x not in h["faits"]]
        h["chap"] = "sommet"
        h["ouverts"].append("sommet")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                    "observatoire", "donnees", "sommet"])
        h["faits"] += ["som0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        e = s.setdefault("entrainement", {})
        e["vus"] = ["cd", "ls", "cat", "grep", "mkdir", "head", "find", "echo"]
    core.modifier(ouvrir)
    for c in ("reveil", "nid", "bibliotheque", "cave", "port", "citadelle", "machinerie", "sommet"):
        (core.TERRAIN / histoire.PAR_CHAP[c]["piece"]).mkdir(parents=True, exist_ok=True)
    for rel, txt in S.meubles(core.load()).items():
        (core.TERRAIN / rel).write_text(txt, encoding="utf-8")


def session(cmds, ici="sommet"):
    out = []
    d = core.TERRAIN / ici
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        if c.split()[0] == "sommet":
            import io
            buf = io.StringIO()
            vieux = os.getcwd()
            os.chdir(d)
            try:
                S.commande(shlex.split(c)[1:], buf)
            finally:
                os.chdir(vieux)
            out += buf.getvalue().rstrip("\n").split("\n")
            continue
        r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=120)
        txt = (r.stdout + r.stderr).rstrip("\n")
        if txt:
            out += txt.split("\n")
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
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "som_pc_lecon.png")
    ansi_image(session(["sommet"]), 100, None, 15).convert("RGB").save(sortie / "som_pc_repli.png")
    g = S._graine(core.load())

    lignes = session(["sommet fragile", "cat fragile.sh", 'bash fragile.sh "carnet de bord.txt"', "echo $?",
                      "sed -i '2i set -euo pipefail' fragile.sh", 'bash fragile.sh "carnet de bord.txt"; echo $?',
                      "sed -i 's/cp $carnet/cp \"$carnet\"/' fragile.sh", 'bash fragile.sh "carnet de bord.txt"'])
    ansi_image(lignes, 110, None, 12).convert("RGB").save(sortie / "som_pc_fragile.png")

    lignes = session(["sommet bivouac", "bash sale.sh", "ls brouillon.*", "bash bivouac.sh -n 3", "ls brouillon.* | wc -l",
                      "bash bivouac.sh -x"])
    ansi_image(lignes, 110, None, 13).convert("RGB").save(sortie / "som_pc_bivouac.png")

    lignes = session(["sommet journal", "head -5 journal.log", "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l",
                      f"sommet dates {len(S.dates(g))}", "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt",
                      "sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt"])
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "som_pc_regex.png")

    lignes = session(["sommet eboulis", "find eboulis -type f | xargs wc -c 2>&1 | head -4",
                      "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6",
                      'echo "pierres : $(find eboulis -type f | wc -l)"', "diff <(ls eboulis/nord) <(ls eboulis/sud)"])
    ansi_image(lignes, 110, None, 13).convert("RGB").save(sortie / "som_pc_eboulis.png")

    lignes = session(["sommet casse", "bash -n casse.sh", "sommet ligne 8", "sed -i '6s/$/; then/' casse.sh",
                      "bash -n casse.sh && bash casse.sh", "bash -x boucle.sh", "sommet bug totl"])
    ansi_image(lignes, 110, None, 12).convert("RGB").save(sortie / "som_pc_debug.png")

    lignes = session(["sommet ctf", "grep -oE 'fragment1=[a-z]+' ctf/registre.log", "find ctf -name '*.frag' -print0 | xargs -0 cat",
                      "bash ctf/porte.sh --help", f"bash ctf/porte.sh -k {S.fragments(g)[0]}"])
    time.sleep(1)
    lignes += session([f"sommet drapeau {S.drapeau(g)}"])[1:]
    ansi_image(lignes, 120, None, 12).convert("RGB").save(sortie / "som_pc_ctf.png")

    jour = time.strftime("%Y-%m-%d")
    core.modifier(lambda s: s.setdefault("compte", {}).setdefault("graines", {}).__setitem__(f"{jour}.abcdef123456", "5a" * 32))
    lignes = session(["sommet defi", "sommet records"])
    ansi_image(lignes, 110, None, 14).convert("RGB").save(sortie / "som_pc_defi.png")

    ligne = "bash -n casse.sh && bash casse.sh"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "sommet")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.7, 100, d), 100, None, 15).convert("RGB").save(sortie / "som_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "som_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print(f"captures du Sommet (PC) écrites dans {sortie}")


if __name__ == "__main__":
    main()
