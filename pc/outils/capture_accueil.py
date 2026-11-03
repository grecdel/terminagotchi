"""Captures de l'accueil et de l'aide (PC), idées du 3 novembre : le vrai code, dans un HOME temporaire.

    python3 pc/outils/capture_accueil.py <dossier de sortie>

Les sorties du jeu sont celles du crochet d'invite (compagnon.prompt) et des commandes `tg …` ; les commandes de
l'enfant (ls, ls ?) passent par le VRAI bash, seulement dans le terrain temporaire. Sorties :
  pc_1_qui_est_avec_toi.png  pc_2_premier_ls.png  pc_4_fleche.png  pc_5_clavier.png  pc_6_perdu.png
  pc_9_fermer_revenir.png  pc_22_explique_moi.png  pc_25_indices.png  pc_66_fin_grisee.png  pc_69_menu_rond.png
  pc_79_menu.png
"""
import builtins
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402  (avant le HOME : capture_port choisit le sien)
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_acc_")
os.environ.pop("HISTFILE", None)
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["TG_SANS_ANIM"] = "1"

from tg import accueil, aide_douce as A, app, compagnon, core, entrainement, histoire, intro, lecons  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

HOME = Path.home()
INVITE = f"{fg(78)}lea@pc{RESET}:{fg(75)}~{RESET}$ "


def prompt(*cmds, statut=0, bash=True, ici=None):
    """L'enfant tape dans son vrai terminal : la commande, sa vraie sortie (bash), puis ce que dit la créature."""
    out = []
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        for c in cmds:
            f.write(c + "\n")
    for c in cmds:
        out.append(INVITE + c)
        if bash:
            r = subprocess.run(["bash", "-c", c], cwd=str(ici or HOME), capture_output=True, text=True, timeout=30)
            txt = (r.stdout + r.stderr).rstrip("\n")
            statut = r.returncode
            if txt:
                out += txt.split("\n")
    sys.argv = ["tg", "prompt", f"--statut={statut}"]
    os.environ["TG_ICI"] = str(ici or HOME)
    buf = io.StringIO()
    with redirect_stdout(buf):
        compagnon.prompt(app.etape)
    out += buf.getvalue().rstrip("\n").split("\n")
    return out


def tg(*args):
    sys.argv = ["tg", *args]
    buf = io.StringIO()
    with redirect_stdout(buf):
        app._main()
    return buf.getvalue().rstrip("\n").split("\n")


def sauver(lignes, sortie, nom, cols=104):
    lignes = [l.replace("\r", "") for l in lignes]
    ansi_image(lignes + [INVITE + "█"], cols=cols).convert("RGB").save(sortie / nom)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    # 1. le tout premier lancement : « Qui est avec toi ? » (2 : un adulte), puis l'histoire
    rep = iter(["2", "", "p", "Pixel", ""])
    builtins.input = lambda _i="": next(rep)
    buf = io.StringIO()
    with redirect_stdout(buf):
        app.creer_si_besoin(avec_intro=True)
    txt = buf.getvalue()
    debut = txt[:txt.index(A.t("ad.parent.relire", cmd="").split(":")[0])].split("\n")
    sauver([f"{INVITE}tg"] + debut[:-1] + ["  " + A.t("ad.parent.relire", cmd=f"{fg(78)}tg aide parents{RESET}"),
                                           f"  \x1b[2m{A.t('ad.parent.entree')}\x1b[0m"], sortie, "pc_1_qui_est_avec_toi.png")
    (core.TERRAIN).mkdir(exist_ok=True)
    for d in ("nid", "vestibule"):
        (HOME / d).mkdir(exist_ok=True)
    (HOME / "reserve.txt").write_text("pommes\n")
    # 4. la flèche, et 2. le premier ls
    l1 = prompt("pwd")
    sauver(l1, sortie, "pc_4_fleche.png")
    l2 = prompt("ls")
    sauver(l2, sortie, "pc_2_premier_ls.png")
    prompt("echo bonjour")
    prompt("whoami")
    st = core.load()
    # 5. un symbole nouveau (le tuyau) dans une leçon
    st5 = {"config": {}, "aide_douce": {}, "name": "Pixel"}
    l5 = [f"{fg(213)}📖 Compte ce qu'il y a dans le sac.{RESET}", f"   {fg(226)}➜ `ls sac | wc -l`{RESET}"]
    l5 = [compagnon.ligne(st) + "  " + f"\x1b[2mleçon ➜ ls sac | wc -l\x1b[0m"] + l5 + A.astuce_clavier(st5, "ls sac | wc -l")
    from tg import langue
    sauver([langue.rendre(x) for x in l5], sortie, "pc_5_clavier.png")
    # 22. ls ?
    l22 = prompt("ls ?")
    sauver([langue.rendre(x) for x in l22], sortie, "pc_22_explique_moi.png")
    # 6. perdu
    (HOME / "nid" / "coin").mkdir(parents=True, exist_ok=True)
    os.chdir(HOME / "nid" / "coin")
    l6 = [INVITE.replace("~", "~/nid/coin") + "perdu"] + tg("perdu")
    sauver([langue.rendre(x) for x in l6], sortie, "pc_6_perdu.png")
    os.chdir(HOME)
    # 25. trois niveaux d'indice (un exercice de la salle d'entraînement)
    st = core.load()
    st["seen"] = sorted(set(st.get("seen", [])) | {"cd", "ls", "mkdir", "touch", "rm"})
    entrainement.commencer(st, typ="bat_pieces")
    core.save(st)
    l25 = []
    for _ in range(3):
        l25 += [INVITE.replace("~", "~/terrain_terminagotchi/salle_entrainement") + "indice"] + tg("indice")
    sauver([langue.rendre(x) for x in l25], sortie, "pc_25_indices.png")
    core.modifier(lambda s: s["entrainement"].__setitem__("cours", None))
    # 9. fermer et revenir : la fin du tronc commun, exit, un nouveau terminal
    def finir_tronc(s):
        h = histoire.h_(s)
        for c in ("reveil", "nid", "bibliotheque", "cave"):
            if c not in h["ailes"]:
                h["ailes"].append(c)
        intro.d_(s)["file"] = []
    core.modifier(finir_tronc)
    l9 = prompt("pwd")
    l9 += [INVITE + "exit", "", f"{fg(240)}─── un nouveau terminal ──────────────────────────────{RESET}"]
    st = core.load()
    r = A.retour(st, -1)
    core.save(st)
    l9 += [f"{fg(78)}{r}{RESET}", compagnon.ligne(st)]
    sauver([langue.rendre(x) for x in l9], sortie, "pc_9_fermer_revenir.png")
    # 66. la fin grisée dans le terminal du jeu (vsh, celui de Windows)
    from tg.vsh import terminal as T
    term = T.Terminal(compagnon=False)
    term.gris = True
    term.sh.cwd = str(HOME)
    g = term._fantome(list("cd vest"), 7)
    inv = f"{fg(78)}lea@terminagotchi{RESET}:{fg(75)}~{RESET}$ "
    l66 = [f"\x1b[38;5;117m{A.t('vsh.accueil')}\x1b[0m", inv + "ls", "nid  reserve.txt  vestibule",
           inv + "cd vest" + f"\x1b[38;5;240m{g}\x1b[0m", "", f"\x1b[2m      (gris = ce que Tab va écrire · → ou Tab pour l'accepter)\x1b[0m"]
    ansi_image(l66, cols=96).convert("RGB").save(sortie / "pc_66_fin_grisee.png")
    # 79. le menu du jeu
    st = core.load()
    ansi_image(accueil.ecran_menu(st, 0).split("\n") + ["", "> █"], cols=80).convert("RGB").save(sortie / "pc_79_menu.png")
    ansi_image([f"{INVITE}tg"] + accueil.ecran_menu(st, 0).split("\n") + ["> 5", ""] + accueil.texte_aide(st).split("\n"),
               cols=100).convert("RGB").save(sortie / "pc_79_menu_aide.png")
    # 69. le menu rond du bureau au clavier (tg menu)
    try:
        import random
        from capture_bureau import fond_gnome, terminal, poser, L_, H_
        from tg import bureau_scene as S, bureau_vie as V, poses
        st["espece_compagnon"] = st.get("espece_compagnon") or "glandouille"
        album = poses.album(st)
        im = fond_gnome()
        terminal(im, [("~ $ tg menu", (220, 225, 235)), (langue.sans_marques(A.t("ad.menu_bureau")), (95, 215, 135)),
                      ("~ $ █", (220, 225, 235))])
        c = V.Creature(L_, dict(V.DEFAUTS), x=1265, hasard=random.Random(1))
        vue = S.VueCreature()
        vue.menu, vue.choix = True, 1
        L, _ = S.scene_creature(c, album, vue, dict(V.DEFAUTS), L_, 440, 430)
        poser(im, L, 0, H_ - 440, (L_, 440))
        im.convert("RGB").save(sortie / "pc_69_menu_rond.png")
    except Exception as e:                      # noqa: BLE001
        print("menu rond :", repr(e))
    print("captures :", sorted(p.name for p in sortie.glob("pc_*.png")))


if __name__ == "__main__":
    main()
