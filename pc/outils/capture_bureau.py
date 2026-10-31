"""Captures simulées de la créature du bureau, du menu rond et de l'île (PC et téléphone), et un GIF animé.

    python3 pc/outils/capture_bureau.py <dossier de sortie> [espèce]

Pas besoin d'écran : on dessine la même liste de dessin que les vraies fenêtres (bureau_scene.py) dans une image
(PIL), posée sur un faux bureau GNOME ou un faux écran de téléphone. Les poses sont les vraies (poses.bin).
"""
import math
import os
import random
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_")

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

from tg import bureau_scene as S, bureau_vie as V, core, poses  # noqa: E402

L_, H_ = 1920, 1080


def police(t, gras=False, mono=False):
    for n in (["DejaVuSansMono.ttf"] if mono else (["Inter-SemiBold.otf"] if gras else ["Inter-Regular.otf"])):
        try:
            return ImageFont.truetype(n, t)
        except OSError:
            pass
    return ImageFont.load_default()


def fond_gnome():
    im = Image.new("RGBA", (L_, H_))
    d = ImageDraw.Draw(im)
    for y in range(H_):
        k = y / H_
        d.line([(0, y), (L_, y)], fill=(int(14 + 12 * k), int(18 + 6 * k), int(38 + 10 * k), 255))
    halo = Image.new("RGBA", (L_, H_), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((1100, 500, 1900, 1100), fill=(90, 40, 120, 70))
    im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, L_, 32), fill=(0, 0, 0, 255))
    d.text((16, 16), "Activités", font=police(15, True), fill=(240, 240, 240), anchor="lm")
    d.text((L_ // 2, 16), "sam. 31 oct. 10:42", font=police(15, True), fill=(240, 240, 240), anchor="mm")
    d.text((L_ - 16, 16), "🔊 78 %", font=police(15, True), fill=(240, 240, 240), anchor="rm")
    return im


def terminal(im, lignes, x=160, y=140, w=820, h=420):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x, y, x + w, y + h), 12, fill=(18, 19, 24, 255), outline=(60, 62, 70))
    d.rounded_rectangle((x, y, x + w, y + 38), 12, fill=(30, 31, 38, 255))
    d.rectangle((x, y + 26, x + w, y + 38), fill=(30, 31, 38, 255))
    d.text((x + w // 2, y + 19), "Terminal — ~/terrain_terminagotchi", font=police(13), fill=(170, 170, 180), anchor="mm")
    for i, (txt, coul) in enumerate(lignes):
        d.text((x + 20, y + 64 + 23 * i), txt, font=police(15, mono=True), fill=coul, anchor="lm")


def partie(espece):
    st = core.new_state("Noisette")
    core.migrate(st)
    st["espece_compagnon"] = espece
    st["xp"] = 20
    st["hunger"] = 38
    return st


def poser(im, liste, x0, y0, taille):
    calque = S.vers_pil(liste, taille)
    im.alpha_composite(calque, (x0, y0))


def agrandir(liste, k):
    """La même liste de dessin, k fois plus grande (captures nettes du téléphone)."""
    out = []
    for op in liste:
        t = op[0]
        if t == "img":
            out.append((t, op[1], op[2] * k, op[3] * k, op[4] * k, op[5], op[6]))
        elif t == "rrect":
            out.append((t, op[1] * k, op[2] * k, op[3] * k, op[4] * k, op[5] * k, op[6], op[7], op[8] * k))
        elif t == "ellipse":
            out.append((t, op[1] * k, op[2] * k, op[3] * k, op[4] * k, op[5]))
        elif t == "arc":
            out.append((t, op[1] * k, op[2] * k, op[3] * k, op[4] * k, op[5], max(1, int(op[6] * k))))
        elif t == "rect":
            out.append((t, op[1] * k, op[2] * k, op[3] * k, op[4] * k, op[5]))
        elif t == "texte":
            out.append((t, op[1] * k, op[2] * k, op[3], op[4] * k, op[5], op[6], op[7], op[8]))
    return out


def captures_pc(sortie, album, info):
    regl = dict(V.DEFAUTS)
    sol = 430
    # 1. le bureau : menu rond ouvert, île au repos
    im = fond_gnome()
    terminal(im, [("~/terrain_terminagotchi $ tg bureau", (220, 225, 235)),
                  ("Noisette s'installe sur ton bureau. Clique sur elle pour ouvrir son menu.", (95, 215, 135)),
                  ("~/terrain_terminagotchi $ █", (220, 225, 235))])
    c = V.Creature(L_, regl, x=1265, hasard=random.Random(1))
    vue = S.VueCreature()
    vue.menu = True
    L, _ = S.scene_creature(c, album, vue, regl, L_, V.ZONE_H if hasattr(V, "ZONE_H") else 440, sol)
    poser(im, L, 0, H_ - 440, (L_, 440))
    ile = V.Ile()
    Li, _ = S.scene_ile(ile, info, album, V.MiniTerminal(Path.home()), 0.4)
    poser(im, Li, (L_ - S.ILE_L) // 2, 34, (S.ILE_L, S.ILE_H))
    im.convert("RGB").save(sortie / "pc_1_menu_rond.png")
    # 2. l'île ouverte (survol) avec la leçon, la créature marche en bas
    im = fond_gnome()
    ile.etat, ile.ouverture = "ouverte", 1.0
    mini = V.MiniTerminal(Path.home() / "terrain_terminagotchi")
    mini.saisie = "cat lianes.txt | grep gland"
    Li, _ = S.scene_ile(ile, dict(info, texte="Quelle commande garde seulement les lignes qui contiennent « gland » ?"),
                        album, mini, 0.4, (700, 120), [(album, S.BLEU)])
    poser(im, Li, (L_ - S.ILE_L) // 2, 34, (S.ILE_L, S.ILE_H))
    c = V.Creature(L_, regl, x=520, hasard=random.Random(2))
    c.changer("marche")
    c.t = 0.3
    L, _ = S.scene_creature(c, album, S.VueCreature(), regl, L_, 440, sol)
    poser(im, L, 0, H_ - 440, (L_, 440))
    im.convert("RGB").save(sortie / "pc_2_ile_ouverte.png")
    # 3. un événement : l'île s'ouvre seule, la créature fait signe ; une autre dort (réglages ouverts)
    im = fond_gnome()
    ile2 = V.Ile()
    ile2.annoncer("Un monstre est apparu dans la forêt !")
    ile2.ouverture = 0.55
    Li, _ = S.scene_ile(ile2, info, album, V.MiniTerminal(Path.home()), 0.4)
    poser(im, Li, (L_ - S.ILE_L) // 2, 34, (S.ILE_L, S.ILE_H))
    c = V.Creature(L_, regl, x=900, hasard=random.Random(3))
    c.changer("salut")
    c.t_etat = 0.25
    L, _ = S.scene_creature(c, album, S.VueCreature(), regl, L_, 440, sol)
    poser(im, L, 0, H_ - 440, (L_, 440))
    c2 = V.Creature(L_, regl, x=1600, hasard=random.Random(4))
    c2.dormir()
    vue = S.VueCreature()
    from tg import bureau
    ctl = type("C", (), {})()
    vue.panneau = ("Réglages", [("Taille : moyenne", "x"), ("Vitesse : normale", "x"), ("Rester sur place : OFF", "x"),
                                ("Son : OFF", "x"), ("Faire dodo maintenant", "x"), ("Au démarrage de l'ordinateur : ON", "x"),
                                ("L'île : ON", "x"), ("Place de l'île : en haut", "x")])
    L, _ = S.scene_creature(c2, album, vue, regl, L_, 440, sol)
    poser(im, L, 0, H_ - 440, (L_, 440))
    im.convert("RGB").save(sortie / "pc_3_evenement_et_dodo.png")
    del bureau, ctl


def telephone(fond=(16, 22, 40)):
    """Un faux écran d'accueil de téléphone (393 × 852 dp, dessiné à × 2,5)."""
    k = 2.5
    W, H = int(393 * k), int(852 * k)
    im = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(fond[0] + 30 * t), int(fond[1] + 10 * t), int(fond[2] + 40 * t), 255))
    d.text((int(24 * k), int(14 * k)), "10:42", font=police(int(14 * k), True), fill=(240, 240, 240), anchor="lm")
    d.text((W - int(24 * k), int(14 * k)), "78 %", font=police(int(13 * k), True), fill=(240, 240, 240), anchor="rm")
    couleurs = [(66, 133, 244), (52, 168, 83), (251, 188, 5), (234, 67, 53), (120, 90, 220), (40, 180, 200),
                (230, 120, 40), (90, 90, 100)]
    for i, coul in enumerate(couleurs):
        x = int((40 + (i % 4) * 82) * k)
        y = int((300 + (i // 4) * 96) * k)
        d.rounded_rectangle((x, y, x + int(56 * k), y + int(56 * k)), int(16 * k), fill=coul + (255,))
    return im, k


def captures_android(sortie, album, info):
    regl = dict(V.DEFAUTS, taille="petite")
    # 1. la bulle se promène en bas de l'écran ; l'île est une pilule en haut
    im, k = telephone()
    W, H = 393, 852
    c = V.Creature(W, regl, x=260, hasard=random.Random(5))
    c.changer("marche")
    c.t = 0.5
    L, _ = S.scene_creature(c, album, S.VueCreature(), regl, W, 300, 296)
    poser(im, agrandir(L, k), 0, int((H - 300) * k), (int(W * k), int(300 * k)))
    Li, _ = S.scene_ile(V.Ile(), info, album, V.MiniTerminal(Path.home()), 0.4)
    poser(im, agrandir(Li, k), int((W - S.ILE_L) / 2 * k), int(6 * k), (int(S.ILE_L * k), int(S.ILE_H * k)))
    im.convert("RGB").save(sortie / "android_1_bulle.png")
    # 2. un appui : le menu rond
    im, k = telephone()
    c = V.Creature(W, regl, x=200, hasard=random.Random(6))
    vue = S.VueCreature()
    vue.menu = True
    L, _ = S.scene_creature(c, album, vue, regl, W, 420, 416)
    poser(im, agrandir(L, k), 0, int((H - 420) * k), (int(W * k), int(420 * k)))
    im.convert("RGB").save(sortie / "android_2_menu_rond.png")
    # 3. l'île ouverte (même dessin que sur PC, à la largeur du téléphone) et la demande de permission
    im, k = telephone()
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = int(28 * k), int(250 * k), int(365 * k), int(640 * k)
    d.rounded_rectangle((x0, y0, x1, y1), int(22 * k), fill=(30, 32, 44, 250))
    d.text((x0 + int(24 * k), y0 + int(34 * k)), "Ta créature sur l'écran", font=police(int(19 * k), True), fill=(240, 240, 245), anchor="lm")
    texte = ("Pour que Noisette se promène par-dessus tes autres applis, le téléphone doit l'autoriser à « s'afficher "
             "par-dessus les autres applications ».\n\nElle ne voit pas ce qu'il y a sur l'écran et ne lit rien de ce "
             "que tu tapes : elle se promène, c'est tout.\n\nSi tu n'es pas sûr, demande à un adulte. Sur la page "
             "suivante, choisis Terminagotchi puis active l'interrupteur.")
    y = y0 + int(70 * k)
    for para in texte.split("\n"):
        for l in S.couper(para, 300, 13.5):
            d.text((x0 + int(24 * k), y), l, font=police(int(13.5 * k)), fill=(200, 205, 215), anchor="lm")
            y += int(19 * k)
    d.text((x1 - int(24 * k), y1 - int(30 * k)), "AUTORISER", font=police(int(14 * k), True), fill=(61, 220, 132), anchor="rm")
    d.text((x1 - int(140 * k), y1 - int(30 * k)), "PAS MAINTENANT", font=police(int(14 * k), True), fill=(150, 160, 175), anchor="rm")
    im.convert("RGB").save(sortie / "android_3_permission.png")
    im, k = telephone()
    ile_android(im, k, album, "Noisette", "content", "J'ai un peu faim… Tape date ou ls pour me nourrir !")
    c = V.Creature(W, regl, x=120, hasard=random.Random(7))
    L, _ = S.scene_creature(c, album, S.VueCreature(), regl, W, 300, 296)
    poser(im, agrandir(L, k), 0, int((H - 300) * k), (int(W * k), int(300 * k)))
    im.convert("RGB").save(sortie / "android_4_ile_ouverte.png")


def ile_android(im, k, album, nom, humeur, dit):
    """L'île ouverte sur le téléphone, avec la même disposition que BulleService.IleDessin (en dp × k)."""
    w, h = 377, 330
    x0, y0 = (393 - w) / 2, 6
    L = [("rrect", x0 + 1, y0 + 1, w - 2, h - 2, 24, (14, 16, 24, 236), (255, 255, 255, 30), 1),
         ("rrect", x0 + 16, y0 + 16, 96, 96, 16, (255, 255, 255, 16), None, 0)]
    cad = album.image("assis", 0)
    e = 80 / album.ref
    L.append(("img", cad, x0 + 64 - cad.ax * e, y0 + 104 - cad.ay * e, e, False, album.lisse))
    L += [("ellipse", x0 + 130, y0 + 28, 4, 4, S.VERT), ("texte", x0 + 140, y0 + 28, nom, 14, S.TEXTE, True, "g", False),
          ("texte", x0 + 148 + V.largeur_texte(nom, 14), y0 + 28, humeur, 12, S.TEXTE_DOUX, False, "g", False),
          ("texte", x0 + w - 22, y0 + 24, "×", 18, S.TEXTE_DOUX, False, "c", False)]
    for i, l in enumerate(S.couper(dit, w - 150, 17 * 0.95)[:4]):
        L.append(("texte", x0 + 130, y0 + 56 + 24 * i, l, 17, S.TEXTE, True, "g", False))
    L.append(("rrect", x0 + 20, y0 + h - 64 - 40, w - 40, 40, 0, (8, 10, 14, 230), None, 0))
    L.append(("texte", x0 + 32, y0 + h - 84, "mini-terminal · Entrée pour lancer", 14, (122, 130, 150, 255), False, "g", True))
    bw = (w - 40 - 6 * 4) / 5
    for i, lib in enumerate(["▶ Jouer", ">_ Terminal", "♥ Nourrir", "◉ Carte", "⚙ Réglages"]):
        bx = x0 + 20 + i * (bw + 6)
        L.append(("rrect", bx, y0 + h - 52, bw, 36, 9, (61, 220, 132, 42) if i == 0 else (255, 255, 255, 10),
                  (61, 220, 132, 192) if i == 0 else (255, 255, 255, 30), 1))
        L.append(("texte", bx + bw / 2, y0 + h - 34, lib, 12, S.VERT if i == 0 else S.TEXTE, False, "c", False))
    poser(im, agrandir(L, k), 0, 0, im.size)


def gif(sortie, album, nom="bureau.gif"):
    """La créature marche, s'assoit, s'étire, mange, fait un cœur, salue et s'endort (bande du bas d'un bureau)."""
    regl = dict(V.DEFAUTS)
    Lz, Hz = 900, 260
    c = V.Creature(Lz, regl, x=640, hasard=random.Random(11))
    c.dir = -1
    plan = [(0, "marche", 4.0), (40, "assis", 1.5), (55, "etire", 2.4), (79, "mange", 2.6), (105, "coeur", 2.6),
            (131, "salut", 2.4), (155, "baille", 2.6), (181, "dort", 3.0)]
    images = []
    vue = S.VueCreature()
    fond = Image.new("RGBA", (Lz, Hz))
    d = ImageDraw.Draw(fond)
    for y in range(Hz):
        d.line([(0, y), (Lz, y)], fill=(20 + y // 20, 22 + y // 30, 44 + y // 15, 255))
    for f in range(212):
        for debut, etat, duree in plan:
            if f == debut:
                if etat == "dort":
                    c.dormir()
                else:
                    c.changer(etat, duree)
                if etat == "mange":
                    vue.flotter("+miam")
                if etat == "coeur":
                    vue.flotter("♥", S.ROUGE)
        c.tick(0.1, {"inactif": 1})
        vue.tick(0.1)
        L, _ = S.scene_creature(c, album, vue, regl, Lz, Hz, Hz - 14)
        im = fond.copy()
        im.alpha_composite(S.vers_pil(L, (Lz, Hz)))
        ImageDraw.Draw(im).text((14, 16), {"marche": "marche", "assis": "assise", "etire": "s'étire", "mange": "mange",
                                           "coeur": "double-clic : un cœur", "salut": "triple clic : coucou",
                                           "baille": "bâille", "dort": "dort"}.get(c.etat, c.etat),
                                 font=police(16, True), fill=(160, 170, 190))
        images.append(im.convert("P", palette=Image.ADAPTIVE, colors=255))
    images[0].save(sortie / nom, save_all=True, append_images=images[1:], duration=100, loop=0, disposal=2)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    espece = sys.argv[2] if len(sys.argv) > 2 else "glandouille"
    st = partie(espece)
    album = poses.album(st)
    info = {"nom": "Noisette", "faim": 38, "xp": 62, "titre": "content", "dans_equipe": 4,
            "texte": "Quelle commande garde seulement les lignes qui contiennent « gland » ?"}
    captures_pc(sortie, album, info)
    captures_android(sortie, album, info)
    gif(sortie, album)
    planche = Image.new("RGB", (12 * 150, 3 * 170), (24, 26, 36))
    d = ImageDraw.Draw(planche)
    for j, esp in enumerate(["braisillon", "zapiot", "lunacorne"]):
        a = poses.album_dessine(esp)
        for i, etat in enumerate(["marche"] * 4 + poses.ETATS[1:]):
            cad = a.image(etat, i if etat == "marche" else 0)
            im = Image.frombytes("RGBA", (cad.w, cad.h), bytes(cad.rgba))
            e = min(1.0, 140 / max(cad.w, cad.h))
            im = im.resize((max(1, int(cad.w * e)), max(1, int(cad.h * e))), Image.LANCZOS)
            planche.paste(im, (i * 150 + (150 - im.width) // 2, j * 170 + 160 - im.height), im)
    planche.save(sortie / "poses_trois_bebes.png")
    print("captures :", sorted(p.name for p in sortie.iterdir() if p.suffix in (".png", ".gif")))


if __name__ == "__main__":
    main()
