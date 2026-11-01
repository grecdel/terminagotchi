"""Captures de la Salle des Rouages (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_machines.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Salle est ouverte (tronc commun
fini). Les commandes sont de VRAIES commandes, lancées sur la machine qui fait les captures (lecture seule, rien hors du
terrain ; podman n'est jamais lancé ici : on montre ce que dit le script et l'histoire racontée). Sorties :
  ma_pc_lecon.png           l'écran du jeu (tg) pendant la leçon « Les organes de la machine »
  ma_pc_ouvre.png           l'ordinateur ouvert : nproc, free -h, lsblk… puis machines ouvre (les pièces allumées)
  ma_pc_deploie.png         tg deploie "nproc; free -h" : l'ordinateur ouvert s'allume dans la vue déployée
  ma_pc_deploie.gif         la même vue déployée, animée
  ma_pc_interrupteurs.png   le prénom en interrupteurs (machines interrupteurs Noé), le défi, machines allume
  ma_pc_reveil.png          le réveil étage par étage (machines reveil, avec les vraies valeurs de la machine)
  ma_pc_monte.png           « Monte ta machine » : l'atelier de l'épreuve, un montage raté puis réussi (machines demarre)
  ma_pc_ferme_321.png       la ferme de serveurs, l'énergie, et la sauvegarde 3-2-1 qui survit à l'incendie
  ma_pc_conteneur.png       le conteneur jetable : le script expliqué (sans rien télécharger) et sa vie racontée
  ma_pc_repli.png           l'affichage de REPLI tant que l'illustration B9 manque (tg machines : la salle en caractères)
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
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_mac_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, machines as M  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)

    def ouvrir(s):
        h = histoire.h_(s)
        for c in M._besoin():
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "machinerie"
        h["ouverts"].append("machinerie")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie"])
        h["faits"] += ["sm0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.sm1.titre"
    core.modifier(ouvrir)
    for c in M._besoin():
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in M.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(txt, bytes):
            p.write_bytes(txt)
        else:
            p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="machines"):
    out = []
    d = core.TERRAIN / ici
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        if c.startswith("machines"):
            buf = io.StringIO()
            M.commande(c.split()[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            out += (r.stdout + r.stderr).rstrip("\n").split("\n")
        core.modifier(lambda s, c=c: M.surveiller(s, [c]))
    out.append(invite)
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "ma_pc_lecon.png")

    cmds = ["nproc", "free -h", "lsblk -d -o NAME,SIZE,TYPE 2>/dev/null || df -h . | tail -1"]
    lignes = session(cmds + ["machines ouvre"])
    ansi_image(lignes, 110, None, 14).convert("RGB").save(sortie / "ma_pc_ouvre.png")

    ligne = "nproc; free -h"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "machines")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "ma_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "ma_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    st = core.load()
    lettre = M.lettre_defi(st.get("name", ""))
    lignes = session(["printf '%x\\n' 65", "machines interrupteurs Noé",
                      "machines allume " + M.bits(ord(lettre))])
    ansi_image(lignes, 110, None, 14).convert("RGB").save(sortie / "ma_pc_interrupteurs.png")

    st = core.load()
    lignes = session(["uname -r", "machines reveil", "machines reveil " + " ".join(M.reveil_reponse(M._graine(st)))])
    ansi_image(lignes, 120, None, 13).convert("RGB").save(sortie / "ma_pc_reveil.png")

    st = core.load()
    besoin = M.besoin_epreuve(M._graine(st))
    bon = {"jouer": "P2 C1 M2 S1 G1 A2", "dessiner": "P2 C1 M2 S2 G0 A1",
           "serveur": "P3 C2 M3 S3 G0 A2", "robot": "P4 C3 M3 S1 G0 A1"}[besoin]
    lignes = session(["machines monte", "machines monte P1 C2 M1 S1 G2 A1", "machines demarre",
                      "machines monte " + bon, "machines demarre"])
    ansi_image(lignes, 120, None, 12).convert("RGB").save(sortie / "ma_pc_monte.png")

    lignes = session(["machines ferme", "machines energie", "tar czf sauvegarde.tar.gz collection.txt",
                      "sha256sum sauvegarde.tar.gz > sauvegarde.sha256",
                      "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/",
                      "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/", "machines panne"])
    lignes += session(["sha256sum -c sauvegarde.sha256", "tar xzf sauvegarde.tar.gz -C ../..",
                       "head -2 ../../collection.txt"], "machines/ferme/loin")
    ansi_image(lignes, 120, None, 12).convert("RGB").save(sortie / "ma_pc_ferme_321.png")

    lignes = session(["head -8 conteneur_jetable.sh", "sh conteneur_jetable.sh", "machines conteneur"])
    ansi_image(lignes, 124, None, 13).convert("RGB").save(sortie / "ma_pc_conteneur.png")

    lignes = session(["machines"])
    ansi_image(lignes, 104, None, 16).convert("RGB").save(sortie / "ma_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de la Salle des Rouages écrites dans", sortie)


if __name__ == "__main__":
    main()
