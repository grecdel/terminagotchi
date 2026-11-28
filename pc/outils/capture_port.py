"""Captures du Port (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_port.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), le Port est ouvert (nid et
bibliothèque finis), le vrai phare du port tourne sur 127.0.0.1 le temps des captures. Sorties :
  port_pc_lecon.png        l'écran du jeu (tg) pendant la leçon « Les phares et les relais » (P9)
  port_pc_terminal.png     une session dans le vrai terminal : port carte, port eteins, port guide, curl -I, ss
  port_pc_deploie_curl.png tg deploie curl … | head -n 3 : le messager part vers localhost:8042
  port_pc_deploie.gif      tg deploie port messager feu : le messager part puis revient (animation)
  port_pc_reseau.png       proposition : la carte du réseau du Terminaworld dessinée (fenêtre tg espace)
"""
import io
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_port_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from PIL import Image  # noqa: E402

from tg import app, core, deploie, histoire, langue, port  # noqa: E402
from tg import espace as E  # noqa: E402
from tg import espace_scene as S  # noqa: E402
from tg.plateforme import BOLD, DIM, RESET, fg  # noqa: E402


def ansi_image(lignes, cols=110, rangs=None, taille=15):
    rangs = rangs or len(lignes)
    cw, ch = int(taille * 0.6), int(taille * 1.35)
    im = Image.new("RGBA", (cols * cw + 40, rangs * ch + 40), (12, 14, 18, 255))
    L = []
    for i, l in enumerate(lignes[:rangs]):
        x = 20
        for s, c, g in E.spans(l, (210, 214, 222, 255)):
            L.append(("texte", x, 20 + ch * i + ch / 2, s, taille, c, g, "g", True))
            x += S.lt(s, taille, True)
    return S.vers_pil(L, im.size, image=im)


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
        h["faits"] += [f"port{i}" for i in range(9)]
        h["chap"] = "port"
        h["ouverts"].append("port")
        s["step"] = 4
        s["xp"] = 10 * 14 ** 2
        s["port"] = {"eteints": ["roche"], "releves": []}
        s["annonce"] = "hist.port9.titre"
    core.modifier(ouvrir)
    for d in ("vestibule", "nid", "grenier", "cave", "bibliotheque"):
        (core.TERRAIN / d).mkdir(parents=True, exist_ok=True)
    app.etape(spontane=False, defis=False)


def session(cmds):
    """Une session dans le vrai terminal : l'invite, la commande, sa sortie (commandes du jeu et vraies commandes)."""
    import subprocess
    out = []
    ici = str(core.TERRAIN / "port")
    for c in cmds:
        out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/port{RESET}$ {c}")
        if c.startswith("port "):
            buf = io.StringIO()
            port.commande(c.split()[1:], buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=ici, capture_output=True, text=True, timeout=20)
            out += r.stdout.rstrip("\n").split("\n")      # (dans un vrai terminal, curl n'affiche pas sa progression)
    out.append(f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/port{RESET}$ ")
    return out


def reseau_image(eteints, chemin, phase, taille=(1280, 720)):
    """La carte du réseau (même dessin que PortDessin.reseau sur Android), en liste de dessin espace_scene."""
    W, H = taille
    L = [("rect", 0, 0, W, H, (12, 14, 18, 255)),
         ("rrect", 20, 20, W - 40, H - 40, 18, (15, 17, 24, 255), (255, 255, 255, 30), 1.2),
         ("texte", 44, 52, "⚓ " + langue.t("port.carte.titre"), 22, (77, 208, 225, 255), True, "g", False)]
    x0, y0, w, h = 40, 90, W - 80, H - 150
    mx, my = 60, 30
    pos = port.donnees()["carte"]

    def px(i):
        return x0 + mx + pos[i][0] * (w - 2 * mx)

    def py(i):
        return y0 + my + pos[i][1] * (h - 2 * my)
    sur = {frozenset(p) for p in zip(chemin, chemin[1:])} if chemin else set()
    for a, b in port.donnees()["liens"]:
        off = a in eteints or b in eteints
        route = frozenset((a, b)) in sur
        c = (178, 132, 255, 255) if route else (138, 147, 166, 90) if off else (77, 208, 225, 140)
        L.append(("ligne", px(a), py(a), px(b), py(b), c, 4.5 if route else 2, (8, 8, 0) if off else None))
    for m in port.machines():
        off = m["id"] in eteints
        coul = (61, 220, 132, 255) if m["role"] == "camp" else (255, 213, 79, 255) if m["role"] == "routeur" else \
            (138, 147, 166, 255) if off else (77, 208, 225, 255)
        cx, cy = px(m["id"]), py(m["id"])
        if not off:
            L.append(("lueur", cx, cy, 34, coul[:3] + (80,)))
        nom = m["id"]
        bw = S.lt(nom, 17) + 30
        L.append(("rrect", cx - bw / 2, cy - 17, bw, 34, 17, (26, 28, 36, 255) if off else (20, 24, 38, 255),
                  coul[:3] + ((110,) if off else (230,)), 2))
        L.append(("texte", cx, cy, nom, 17, (138, 147, 166, 255) if off else (233, 236, 242, 255), True, "c", False))
        L.append(("texte", cx, cy + 28, ("✖ " if off else "") + m["adresse"], 13, coul[:3] + ((150,) if off else (220,)),
                  False, "c", True))
    if chemin and len(chemin) > 1:
        import math
        pts = [(px(i), py(i)) for i in chemin]
        seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        f = phase * 2 if phase < 0.5 else (1 - phase) * 2
        reste, k = f * sum(seg), 0
        while k < len(seg) - 1 and reste > seg[k]:
            reste -= seg[k]
            k += 1
        t_ = reste / seg[k] if seg[k] else 0
        ex = pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t_
        ey = pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t_
        L.append(("rrect", ex - 18, ey - 44, 36, 24, 4, (244, 241, 232, 255), (178, 132, 255, 255), 2.2))
        L.append(("ligne", ex - 15, ey - 41, ex, ey - 30, (178, 132, 255, 255), 2, None))
        L.append(("ligne", ex + 15, ey - 41, ex, ey - 30, (178, 132, 255, 255), 2, None))
    L.append(("texte", 44, H - 40, langue.t("port.carte.aide").replace("`", ""), 15, (138, 147, 166, 255), False, "g", False))
    return S.vers_pil(L, taille)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    serveurs = port.phare(attendre=False)
    try:
        st = core.load()
        lignes = app.render(st, 0, False).rstrip("\n").split("\n")
        ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "port_pc_lecon.png")
        lignes = session(["port carte", "port eteins roche", "port guide racine plante poison ombre machine feu",
                          "curl -I http://localhost:8042/", "curl -s http://localhost:8042/eau | head -n 3"])
        ansi_image(lignes, 132, None, 14).convert("RGB").save(sortie / "port_pc_terminal.png")
        ligne = "curl -s http://localhost:8042/eau | head -n 3"
        bl = deploie.blocs(ligne)
        ansi_image(deploie.ecran(ligne, bl, 1, None, 0.3, 104), 104, None, 15).convert("RGB").save(
            sortie / "port_pc_deploie_curl.png")
        ligne = "port messager feu"
        bl = deploie.blocs(ligne)
        images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 24, 96), 96, 16, 15).convert("RGB") for i in range(24)]
        images[0].save(sortie / "port_pc_deploie.gif", save_all=True, append_images=images[1:], duration=110, loop=0)
        chemin = ["camp", "racine", "plante", "poison", "ombre", "machine", "feu"]
        reseau_image(["roche"], chemin, 0.3).convert("RGB").save(sortie / "port_pc_reseau.png")
    finally:
        for s in serveurs or []:
            s.shutdown()
            s.server_close()
    print("captures du Port écrites dans", sortie)


if __name__ == "__main__":
    main()
