"""Captures du thème « créature » sur PC (maquettes validées le 3 novembre), sans écran.

    python3 pc/outils/capture_creature.py <dossier de sortie>

Une vraie partie dans un HOME temporaire (Noisette, une Glandouille) ; l'espace de travail (espace.Espace) reçoit de
vraies commandes ; la liste de dessin (espace_scene.py, la même que la fenêtre GTK 4 / tkinter) est dessinée avec PIL.
Sorties : pc_espace.png (tout l'espace), pc_humeurs.png (les 8 humeurs du moment dans la fenêtre « en direct »),
pc_fete.png, pc_envie.png, pc_evolution.png (4 phases), pc_promenade.png, pc_album.png (onglet Album),
pc_options.png (« rester sur place »), et le terminal : pc_terminal_plat.png, pc_terminal_album.png,
pc_terminal_gouts.png, pc_terminal_indice.png, pc_terminal_fete.png.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_creature_")
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")

from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_espace as CE  # noqa: E402
from tg import app, core, creature as CR, histoire, langue  # noqa: E402
from tg import espace as E  # noqa: E402
from tg import espace_scene as S  # noqa: E402


def direct(esp, t_):
    """La fenêtre « en direct » seule."""
    m = esp.modele()
    L, Z, (W, H) = S.scene(m, t_)
    im = S.vers_pil(L, (W, H))
    r = S.Mise(m.get("classe", False), m.get("cases")).direct
    return im.crop((int(r[0]) - 4, int(r[1]) - 4, int(r[0] + r[2]) + 4, int(r[1] + r[3]) + 4)).convert("RGB")


def contexte(esp, t_):
    m = esp.modele()
    L, Z, (W, H) = S.scene(m, t_)
    im = S.vers_pil(L, (W, H))
    r = S.Mise(m.get("classe", False), m.get("cases")).contexte
    return im.crop((int(r[0]) - 4, int(r[1]) - 4, int(r[0] + r[2]) + 4, int(r[1] + r[3]) + 4)).convert("RGB")


def grille(images, colonnes, fond=(9, 11, 16)):
    w, h = images[0].size
    lignes = (len(images) + colonnes - 1) // colonnes
    out = Image.new("RGB", (colonnes * (w + 12) + 12, lignes * (h + 12) + 12), fond)
    for i, im in enumerate(images):
        out.paste(im, (12 + (i % colonnes) * (w + 12), 12 + (i // colonnes) * (h + 12)))
    return out


def modifier(f):
    st = core.load()
    f(st)
    core.save(st)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    CE.preparer()
    modifier(lambda st: (st.update(xp=60, hunger=70.0), CR.c_(st).update(graine=9)))
    import tg.bureau_vie as V
    horloge = [1000.0]
    V.maintenant = lambda: horloge[0]
    esp = E.Espace(app.etape)
    esp.lignes = []
    esp.mini.dossier = str(core.TERRAIN)
    for l in ("ls", "uptime"):
        CE.taper(esp, l)
    CE.avancer(esp, 1.5)
    CE.dessiner(esp, esp.t).convert("RGB").save(sortie / "pc_espace.png")
    # 11 : les 8 humeurs du moment
    ims = []
    for h in ("curieux", "fier", "calin", "gourmand", "enjoue", "reveur", "surpris", "bavard"):
        modifier(lambda st: CR.c_(st).update(humeur={"h": h, "t": time.time()}))
        esp.jeu()
        esp.c.changer(CR.donnees()["humeurs"][h]["reaction"], 3)
        esp.c.x = esp.c.largeur * 0.45
        CE.avancer(esp, 0.6)
        esp.vue.bulle = (langue.liste("cr.humeur." + h + ".dit")[0] if h != "gourmand" else
                         langue.t("cr.plat.dit", cmd="ls"), esp.t + 30)
        ims.append(direct(esp, esp.t).resize((480, 320), Image.LANCZOS))
    grille(ims, 4).save(sortie / "pc_humeurs.png")
    esp.vue.bulle = None
    # 17 : l'éclosiversaire
    modifier(lambda st: CR.c_(st).update(humeur=None, eclosion=time.time() - 31 * 86400))
    CE.taper(esp, "pwd")
    esp.c.x = esp.c.largeur * 0.4
    CE.avancer(esp, 0.8)
    direct(esp, esp.t).save(sortie / "pc_fete.png")
    terminal_fete = list(core.load().get("terminal", []))
    # 18 : l'envie mystère
    modifier(lambda st: (CR.c_(st).update(humeur=None, fete=None, envie={"id": "ls_a", "k": 1, "t": time.time()}),
                         st.update(bubble=None)))
    esp.jeu()
    CE.avancer(esp, 0.5)
    direct(esp, esp.t).save(sortie / "pc_envie.png")
    # 85 : la promenade
    modifier(lambda st: CR.c_(st).update(envie=None))
    esp.jeu()
    esp.vue.bulle = None
    esp.cv.forcer(None)
    esp.cv.etat = "content"
    CE.avancer(esp, 0.2)
    esp.c.changer("marche", 4)
    esp.c.x = esp.c.largeur * 0.3
    CE.avancer(esp, 0.3)
    direct(esp, esp.t).save(sortie / "pc_promenade.png")
    # 84 : le moment d'évolution (de bébé à ado)
    modifier(lambda st: (st.update(xp=165), CR.c_(st).update(evolution={"de": "bebe", "vers": "ado", "t": time.time()}),
                         __import__("tg.satiete", fromlist=["s_"]).s_(st).update(jours=99)))
    esp.evo_vu = 0
    esp.jeu()
    phases = []
    t0 = esp.t
    for tt in (1.0, 2.6, 3.95, 5.2):
        CE.avancer(esp, tt - (esp.t - t0))
        phases.append(direct(esp, esp.t).resize((560, 380), Image.LANCZOS))
    grille(phases, 2).save(sortie / "pc_evolution.png")
    esp.evo = None
    # 16 : l'onglet Album
    esp.onglet = "album"
    esp.album_salut = ("ado", esp.t - 0.15)
    contexte(esp, esp.t).save(sortie / "pc_album.png")
    esp.onglet = "carte"
    # les options : « rester sur place »
    esp.options = True
    CE.dessiner(esp, esp.t).convert("RGB").save(sortie / "pc_options.png")
    esp.options = False
    # le terminal (tg album, tg gouts, tg indice, le plat préféré, la fête)
    from tg.plateforme import RESET, fg
    st = core.load()
    invite = f"{fg(75)}~/terrain_terminagotchi{RESET}$ "
    CE.ansi_image([invite + "tg album"] + CR.album_lignes(st), 110, None, 15).convert("RGB").save(sortie / "pc_terminal_album.png")
    CE.ansi_image([invite + "tg gouts"] + CR.gouts_lignes(st), 110, None, 15).convert("RGB").save(sortie / "pc_terminal_gouts.png")
    modifier(lambda s: CR.c_(s).update(envie={"id": "ls_a", "k": 0, "t": time.time()}))
    st = core.load()
    rep = [invite + "tg indice", " " + CR.indice(st), invite + "tg indice", " " + CR.indice(st), invite + "tg indice",
           " " + CR.indice(st)]
    CE.ansi_image(rep, 110, None, 15).convert("RGB").save(sortie / "pc_terminal_indice.png")
    st = core.load()
    st["derniers"] = []
    st["hunger"] = 40.0
    core.feed(st, "ls", 0)
    CE.ansi_image([invite + "ls", "carnet.txt  coussin/  graines/",
                   f"{fg(78)}(^▽^){RESET} Noisette {fg(245)}niv. 3{RESET}  {st['log'][-1][6:]}"], 110, None, 15
                  ).convert("RGB").save(sortie / "pc_terminal_plat.png")
    CE.ansi_image([invite + "pwd", "/home/moi/terrain_terminagotchi"] + [f"{fg(213)}{x}{RESET}" for x in terminal_fete],
                  110, None, 15).convert("RGB").save(sortie / "pc_terminal_fete.png")
    print("captures :", sorted(p.name for p in sortie.iterdir()))


if __name__ == "__main__":
    main()
