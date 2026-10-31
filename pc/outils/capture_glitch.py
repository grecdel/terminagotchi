"""Captures de l'effet glitch (PC, et la maquette téléphone), pour le propriétaire.

    python3 pc/outils/capture_glitch.py <dossier de sortie> [<dossier des images Android (GlitchTel.kt)>]

Sorties :
  glitch_pc_terminal.png   le terminal (rendu texte : quadrants et demi-blocs) : l'équipe avec un glitch, un shiny + glitch,
                           la carte d'une capture, l'éclair, et les messages (boîte maîtrisée, gardien glitch)
  glitch_pc_kitty.png      la vraie image (Kitty, iTerm2, sixel) : la vie au pixel fin, normale / glitch au repos (A) /
                           éclair (C) / shiny + glitch
  glitch_pc_bureau.png     tg bureau : la créature glitch se promène sur le bureau
  glitch_tel.png           la maquette du téléphone (les images viennent du vrai code Kotlin : GlitchTel.kt)
  glitch_repos_eclair.gif  la respiration au repos (style A) et un éclair (style C) toutes les quelques secondes
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "pc" / "outils"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_glitch_")
os.environ["LANG"] = "fr_FR.UTF-8"

from PIL import Image, ImageDraw  # noqa: E402

from tg import anim_auto, bestiaire as B, equipe, glitch as G, langue, rendu_fin, poses  # noqa: E402
from tg.langue import t  # noqa: E402
from tg.plateforme import BOLD, DIM, RESET, fg  # noqa: E402
from capture_port import ansi_image  # noqa: E402

langue.definir("fr")
GLITCH = {"id": "c0ffee1234", "espece": "Ombrachne", "variante": "classique", "stade": "adulte", "glitch": True,
          "rarete": "rare", "marque": "une tache en forme d'étoile", "humeur": "taquine", "taille": 61.2,
          "potentiel": 74, "stats": {"PV": 44, "ATK": 61, "DEF": 40, "VIT": 52, "INT": 47}, "note": 64.0, "zone": "crypte"}
SHINY_G = dict(GLITCH, id="5eed5eed01", shiny=True, teinte=0.62, rarete="épique")
GARDIEN = dict(GLITCH, id="ab12cd34ef", espece="Ricanombre", stade="enfant", rarete="commune", gardien="enumeration")
NORMAL = dict(GLITCH, id="0000000001", glitch=False, espece="Crânard", stade="ado", rarete="peu commune")


def police(taille, gras=False):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if gras else ""),):
        if os.path.exists(f):
            return ImageFont.truetype(f, taille)
    return ImageFont.load_default()


def cote_a_cote(blocs, ecart=4):
    h = max(len(b) for b in blocs)
    out = []
    for i in range(h):
        s = ""
        for b in blocs:
            w = max(langue.largeur(x) for x in b)
            ligne = b[i] if i < len(b) else ""
            s += ligne + RESET + " " * (w - langue.largeur(ligne) + ecart)
        out.append(s)
    return out


def terminal(sortie):
    os.environ["TG_IMAGES"] = "quadrants"
    st = {"name": "Noisette", "captures": [NORMAL, GARDIEN, SHINY_G, GLITCH], "active": GLITCH["id"], "seen": [],
          "skills": [], "xp": 900, "stats": {}}
    L = [f"{fg(40)}~/terrain_terminagotchi ${RESET} tg equipe"]
    try:
        L += equipe.ecran_equipe(st)
    except Exception:                                     # noqa: BLE001 — repli : les noms seuls
        L += ["  " + B.nom_affiche(B.espece(c["espece"]), c.get("shiny"), c["rarete"], c.get("glitch")) for c in st["captures"]]
    L += ["", f"{fg(40)}~/terrain_terminagotchi ${RESET} tg anime ombrachne      {DIM}(au repos · un éclair · shiny + glitch){RESET}"]
    L.append("")
    L += ["", " " + t("recomp.glitch_gardien", espece="Ricanombre"), " " + t("recomp.glitch", espece="Ombrachne")]
    import textwrap
    L += [" " + x for x in textwrap.wrap(t("recomp.gardien", boite=t("cit.boite.enumeration"), espece="Ricanombre"), 110)]
    texte = ansi_image(L, cols=118, taille=15).convert("RGB")
    # les dessins tels que le terminal les montre en demi-blocs (2 pixels par caractère : 9 × 20 pixels ici)
    om = B.espece("Ombrachne")
    cas = [("normale", B.pixels(om, stade="adulte")), ("glitch · au repos (A)", B.pixels(om, stade="adulte", glitch=GLITCH["id"])),
           ("glitch · éclair (C)", B.pixels(om, stade="adulte", glitch=(GLITCH["id"], "C", 2))),
           ("shiny + glitch", B.pixels(om, True, stade="adulte", teinte=0.62, glitch=SHINY_G["id"]))]
    cw, chh = 9, 10
    larg = max(w for _, (w, h, c) in cas) * cw + 30
    haut = max(h for _, (w, h, c) in cas) * chh + 50
    P = Image.new("RGB", (max(texte.width, larg * 4), texte.height + haut), (12, 14, 18))
    P.paste(texte, (0, 0))
    d = ImageDraw.Draw(P)
    for k, (titre, (w, h, c)) in enumerate(cas):
        x0, y0 = 20 + k * larg, texte.height + 34
        d.text((x0, texte.height + 10), titre, font=police(16, True), fill=(120, 230, 255) if k else (190, 190, 200))
        for y in range(h):
            for x in range(w):
                if c[y * w + x]:
                    d.rectangle((x0 + x * cw, y0 + y * chh, x0 + x * cw + cw - 1, y0 + y * chh + chh - 1), fill=c[y * w + x])
    d.text((20, P.height - 18), "$ tg anime ombrachne : au repos (A) ; toutes les 3 à 5 s, un éclair (C) de 0,26 s",
           font=police(14), fill=(140, 150, 165))
    P.save(sortie / "glitch_pc_terminal.png")
    os.environ.pop("TG_IMAGES")


def vie_px(ind, k, spec):
    e = B.espece(ind["espece"])
    v = anim_auto.vie_de(e, ind["stade"], "classique", ind.get("teinte") if ind.get("shiny") else None)
    W, H, px = rendu_fin.composer_vie(v[0], v[1], k, None, 1, glitch=spec)
    im = Image.new("RGBA", (W, H))
    im.putdata([(0, 0, 0, 0) if p is None else p for p in px])
    return im


def kitty(sortie):
    cases = [("normale", GLITCH, None), ("glitch · au repos (A)", GLITCH, (GLITCH["id"], "A", 0)),
             ("glitch · éclair (C)", GLITCH, (GLITCH["id"], "C", 2)), ("shiny + glitch", SHINY_G, (SHINY_G["id"], "A", 0)),
             ("gardien glitch", GARDIEN, (GARDIEN["id"], "A", 0))]
    ims = [vie_px(ind, 9, sp) for _, ind, sp in cases]
    cw = max(max(i.width for i in ims) + 40, 230)
    ch = max(i.height for i in ims) + 90
    P = Image.new("RGB", (cw * len(ims), ch), (12, 14, 18))
    d = ImageDraw.Draw(P)
    for k, ((titre, _, _), im) in enumerate(zip(cases, ims)):
        P.paste(im, (k * cw + (cw - im.width) // 2, 60 + (ch - 70 - im.height)), im)
        d.text((k * cw + cw // 2, 26), titre, font=police(20, True), fill=(120, 230, 255) if k else (200, 200, 210), anchor="mm")
    P.save(sortie / "glitch_pc_kitty.png")


def gif(sortie):
    """8 images par seconde pendant 9 secondes : la vie (respiration, clignements) et l'horloge des éclairs."""
    ims = []
    t0 = 1761955200000
    for k in range(72):
        tms = t0 + k * 125
        st, ph = G.etat(GLITCH["id"], tms)
        im = vie_px(GLITCH, k % 64, (GLITCH["id"], st, ph))
        ims.append((im, st))
    W = max(i.width for i, _ in ims) + 40
    H = max(i.height for i, _ in ims) + 40
    frames = []
    for im, st in ims:
        f = Image.new("RGB", (W, H), (12, 14, 18))
        f.paste(im, ((W - im.width) // 2, H - 20 - im.height), im)
        frames.append(f)
    frames[0].save(sortie / "glitch_repos_eclair.gif", save_all=True, append_images=frames[1:], duration=125, loop=0)
    return sum(1 for _, s in ims if s == "C")


def bureau(sortie):
    import capture_bureau as CB
    from tg import bureau_scene as S, bureau_vie as V
    import random
    album = poses.album_espece("ricanombre", "enfant", False, GARDIEN["id"])
    regl = dict(V.DEFAUTS)
    im = CB.fond_gnome()
    CB.terminal(im, [("~/terrain_terminagotchi $ tg bureau", (220, 225, 235)),
                     ("Ricanombre ▚ s'installe sur ton bureau.", (255, 40, 120)),
                     ("~/terrain_terminagotchi $ █", (220, 225, 235))])
    for x, etat, kk in ((700, "marche", 1), (1265, "assis", 0)):
        c = V.Creature(CB.L_, regl, x=x, hasard=random.Random(1))
        c.changer(etat)
        c.t = 0.3
        L, _ = S.scene_creature(c, album, S.VueCreature(), regl, CB.L_, 440, 430)
        CB.poser(im, L, 0, CB.H_ - 440, (CB.L_, 440))
    im.convert("RGB").save(sortie / "glitch_pc_bureau.png")


def telephone(sortie, tel):
    k = 2.5
    W, H = int(393 * k), int(852 * k)
    im = Image.new("RGB", (W, H), (10, 12, 16))
    d = ImageDraw.Draw(im)
    d.text((int(24 * k), int(14 * k)), "10:42", font=police(int(14 * k), True), fill=(240, 240, 240), anchor="lm")
    d.rectangle((0, int(30 * k), W, int(200 * k)), fill=(20, 24, 34))
    titre = B.nom_affiche(B.espece("Ombrachne"), False, "rare", True)
    d.text((int(170 * k), int(70 * k)), "Ombrachne ▚", font=police(int(18 * k), True), fill=(255, 40, 120), anchor="lm")
    d.text((int(170 * k), int(98 * k)), "adulte · rare · glitch", font=police(int(12 * k)), fill=(150, 160, 180), anchor="lm")
    d.text((int(170 * k), int(124 * k)), "▚ au repos   ⚡ un éclair toutes", font=police(int(11 * k)), fill=(120, 230, 255), anchor="lm")
    d.text((int(170 * k), int(142 * k)), "   les 3 à 5 secondes", font=police(int(11 * k)), fill=(120, 230, 255), anchor="lm")
    def poser(nom, x, y, h):
        p = Image.open(tel / nom).convert("RGBA")
        e = h / p.height
        p = p.resize((max(1, int(p.width * e)), int(h)), Image.NEAREST)
        im.paste(p, (int(x), int(y)), p)
        return p.width
    poser("vie_A.png", 14 * k, 40 * k, 150 * k)
    y = 220 * k
    d.text((int(16 * k), y), "$ tg equipe", font=police(int(13 * k), True), fill=(95, 215, 135), anchor="lm")
    lignes = [("balise_glitch.png", "Ombrachne ▚", (255, 40, 120), "adulte · rare"),
              ("balise_shiny_glitch.png", "Ombrachne ✨ ▚", (255, 200, 90), "adulte · épique · shiny + glitch"),
              ("balise_gardien.png", "Ricanombre ▚", (255, 40, 120), "enfant · gardien de la cave oubliée"),
              ("balise_gardien_normal.png", "Ricanombre", (220, 220, 230), "enfant · commune")]
    for i, (f, nom, coul, info) in enumerate(lignes):
        yy = y + (24 + i * 62) * k
        poser(f, 16 * k, yy, 54 * k)
        d.text((int(80 * k), yy + 18 * k), nom, font=police(int(14 * k), True), fill=coul, anchor="lm")
        d.text((int(80 * k), yy + 38 * k), info, font=police(int(11 * k)), fill=(150, 160, 180), anchor="lm")
    y2 = y + 280 * k
    d.text((int(16 * k), y2), "L'éclair (style C), quelques dixièmes de seconde :", font=police(int(12 * k)), fill=(200, 200, 210), anchor="lm")
    x = 16 * k
    for f in ("vie_normal.png", "vie_A.png", "vie_C.png", "vie_C2.png", "vie_shiny_A.png"):
        x += poser(f, x, y2 + 14 * k, 110 * k) + 8 * k
    y3 = y2 + 150 * k
    import textwrap
    for j, ligne in enumerate(textwrap.wrap(t("recomp.gardien", boite=t("cit.boite.enumeration"), espece="Ricanombre"), 46)):
        d.text((int(16 * k), y3 + j * 18 * k), ligne, font=police(int(12 * k)), fill=(95, 215, 135), anchor="lm")
    d.text((int(16 * k), y3 + 120 * k), "La bulle :", font=police(int(12 * k)), fill=(200, 200, 210), anchor="lm")
    poser("bulle_pose.png", 120 * k, y3 + 96 * k, 120 * k)
    im.save(sortie / "glitch_tel.png")


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    terminal(sortie)
    kitty(sortie)
    print("images d'éclair dans le GIF :", gif(sortie))
    bureau(sortie)
    if len(sys.argv) > 2:
        telephone(sortie, Path(sys.argv[2]))
    print("captures :", sorted(p.name for p in sortie.iterdir() if p.suffix in (".png", ".gif")))


if __name__ == "__main__":
    main()
