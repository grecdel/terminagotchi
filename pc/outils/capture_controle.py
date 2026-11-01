"""Captures du Poste de Contrôle (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_controle.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), le Poste est ouvert (tronc commun
fini). Les commandes du jeu (controle …) passent par le vrai code ; les autres (ps, free, df, du, grep, kill…) sont
lancées pour de vrai, en LECTURE, dans le terrain temporaire. Les seuls processus arrêtés sont ceux de la vague (des
`sleep` renommés lancés par le jeu) : leurs numéros sont pris dans `controle ps`, jamais devinés. Sorties :
  ct_pc_lecon.png      l'écran du jeu (tg) pendant la leçon « Les habitants »
  ct_pc_habitants.png  ps, echo $$, /proc/$$/status, controle habitants
  ct_pc_jauges.png     free -h, df -h ., du -sh entrepot/*, la caisse la plus lourde, les jauges
  ct_pc_sac.png        export, bash -c, source sac_a_dos.sh, echo $POSTE
  ct_pc_cron.png       les réveils lus et expliqués, le réveil demandé, la prochaine sonnerie
  ct_pc_linux.png      /etc/os-release, la distribution, les familles, le magasin (lecture seule)
  ct_pc_vague.png      l'alerte, ps aux | grep fictif, kill des 3 suspects, le tableau de bord (veilleur épargné)
  ct_pc_deploie.png    tg deploie "ps aux | grep fictif ; kill …" : le tableau de bord dans la vue déployée
  ct_pc_deploie.gif    la même vue déployée, animée
  ct_pc_repli.png      l'affichage de REPLI tant que l'illustration du Poste manque (tg controle)
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
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_ctl_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, controle as C  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, lecs = C._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["faits"] += [l for l in lecs if l not in h["faits"]]
        h["chap"] = "controle"
        h["ouverts"].append("controle")
        h.setdefault("mondes_annonces", []).extend(["forge", "robots", "temps", "controle"])
        h["faits"] += ["ct0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.ct1.titre"
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "controle").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in C.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(txt, bytes):
            p.write_bytes(txt)
        else:
            p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="controle"):
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c)
        if mots[0] == "controle":
            buf = io.StringIO()
            C.commande(mots[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            assert not C.kill_etrangers(c), c  # jamais un processus qui n'est pas au jeu
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            txt = (r.stdout + r.stderr).rstrip("\n")
            if txt:
                out += txt.split("\n")
        core.modifier(lambda s, c=c: C.surveiller(s, [c]))
    out.append(invite)
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    try:
        _captures(sortie)
    finally:
        C.arreter_tout()
        shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures du Poste de Contrôle écrites dans", sortie)


def _captures(sortie):
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "ct_pc_lecon.png")

    lignes = session(["ps", "echo $$", "head -3 /proc/$$/status", "controle habitants"])
    ansi_image(lignes, 110, None, 14).convert("RGB").save(sortie / "ct_pc_habitants.png")

    st = core.load()
    gr = C._graine(st)
    lignes = session(["free -h", "df -h . | cut -c1-70", "du -sh entrepot/*",
                      f"controle entrepot {C.caisse_lourde(gr).removesuffix('.bin')}", "nproc", "controle jauges"])
    ansi_image(lignes, 110, None, 12).convert("RGB").save(sortie / "ct_pc_jauges.png")

    lignes = session(["export COULEUR=bleu; bash -c 'echo $COULEUR'", "cat sac_a_dos.sh",
                      "source sac_a_dos.sh; echo $POSTE"])
    ansi_image(lignes, 110, None, 14).convert("RGB").save(sortie / "ct_pc_sac.png")

    st = core.load()
    rep = C.cron_situation(C._graine(st))["rep"]
    lignes = session(["controle reveils", f'controle cron "{rep}"',
                      f'echo "{rep} echo coucou" >> reveils.crontab', "controle reveils"])
    ansi_image(lignes, 110, None, 11).convert("RGB").save(sortie / "ct_pc_cron.png")

    st = core.load()
    cartes = C.familles_cartes(C._graine(st))
    os_id = (C.os_release() or {}).get("ID", "linux")
    lignes = session(["grep -E '^(NAME|VERSION|ID)=' /etc/os-release", f"controle distribution {os_id}",
                      "controle familles", "controle familles " + " ".join(r for _n, _i, r in cartes), "controle magasin"])
    ansi_image(lignes, 110, None, 11).convert("RGB").save(sortie / "ct_pc_linux.png")

    session(["controle alerte"])
    st = core.load()
    pids = " ".join(str(p) for p, _n in C.suspects_vivants(st))
    lignes = session(["controle alerte", "ps aux | grep '[_]fictif [0-9]' | cut -c1-30,65-120", f"kill {pids}", "controle tableau"])
    ansi_image(lignes, 132, None, 12).convert("RGB").save(sortie / "ct_pc_vague.png")

    ligne = "ps aux | grep fictif ; free -h ; kill 4242"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "controle")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "ct_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "ct_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    lignes = session(["controle"])
    ansi_image(lignes, 110, None, 16).convert("RGB").save(sortie / "ct_pc_repli.png")


if __name__ == "__main__":
    main()
