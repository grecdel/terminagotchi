"""Captures de la Crypte des Codes (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_crypte.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Crypte est ouverte (tronc commun
fini). Tout reste dans le terrain ; gpg n'est pas lancé ici. Sorties :
  cry_pc_lecon.png          l'écran du jeu (tg) pendant la leçon « Les vieux codes »
  cry_pc_roue.png           le terminal : base64, la roue de César (tr), les fréquences, crypte roue
  cry_pc_deploie_roue.png   tg deploie "tr a-z d-za-c" : la roue de César tourne de 3 crans
  cry_pc_deploie.gif        la même vue déployée, animée
  cry_pc_chaine_cassee.png  la chaîne de blocs brisée par le joueur (bash verifie_chaine.sh puis crypte chaine)
  cry_pc_chaine_reparee.png la même chaîne réparée (cp archives/bloc_1.txt chaine/)
  cry_pc_minage.png         le minage minuscule (bash mineur.sh 2, time … 3) et la table du mineur
  cry_pc_peintures.png      le mélange de peintures (Diffie-Hellman) et la vitrine (explication technique seulement)
  cry_pc_repli.png          l'affichage de REPLI tant que l'illustration B12 manque (tg crypte : la crypte en caractères)
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_cry_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, crypte as K, deploie, histoire, langue  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)

    def ouvrir(s):
        h = histoire.h_(s)
        for c in K._besoin():
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "crypte"
        h["ouverts"].append("crypte")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte"])
        h["faits"] += ["cr0", "cr1"]
        s["step"] = 0
        s["xp"] = 10 * 16 ** 2
        s["annonce"] = "hist.cr2.titre"
    core.modifier(ouvrir)
    for c in K._besoin():
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in K.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds):
    out = []
    ici = str(core.TERRAIN / "crypte")
    for c in cmds:
        out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/crypte{RESET}$ {c}")
        if c.startswith("crypte"):
            buf = io.StringIO()
            K.commande(c.split()[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=ici, capture_output=True, text=True, timeout=60)
            out += (r.stdout + r.stderr).rstrip("\n").split("\n")
    out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/crypte{RESET}$ ")
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "cry_pc_lecon.png")
    k = K.decalage(K._graine(st))
    lignes = session(["echo bonjour | base64", "cat messages/message_1.txt | base64 -d",
                      'echo bonjour | tr "a-z" "d-za-c"',
                      "grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3",
                      f"crypte roue {k}"])
    ansi_image(lignes, 120, None, 14).convert("RGB").save(sortie / "cry_pc_roue.png")
    ligne = 'tr "a-z" "d-za-c"'
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "crypte")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "cry_pc_deploie_roue.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 20, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "cry_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)
    lignes = session(["head -3 chaine/bloc_1.txt", 'echo "Pixel donne 300 glands à Noisette" >> chaine/bloc_1.txt',
                      "bash verifie_chaine.sh", "crypte chaine"])
    ansi_image(lignes, 120, None, 14).convert("RGB").save(sortie / "cry_pc_chaine_cassee.png")
    lignes = session(["cp archives/bloc_1.txt chaine/", "crypte chaine"])
    ansi_image(lignes, 120, None, 14).convert("RGB").save(sortie / "cry_pc_chaine_reparee.png")
    lignes = session(["cat mineur.sh | head -4", "bash mineur.sh 2", "time bash mineur.sh 3", "crypte mine"])
    ansi_image(lignes, 132, None, 13).convert("RGB").save(sortie / "cry_pc_minage.png")
    lignes = session(["crypte peintures", "echo $((5**6 % 23))", "crypte vitrine"])
    ansi_image(lignes, 140, None, 13).convert("RGB").save(sortie / "cry_pc_peintures.png")
    lignes = session(["crypte"])
    ansi_image(lignes, 104, None, 16).convert("RGB").save(sortie / "cry_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de la Crypte écrites dans", sortie)


if __name__ == "__main__":
    main()
