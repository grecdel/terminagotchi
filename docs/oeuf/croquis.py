#!/usr/bin/env python3
"""Croquis indicatif de l'œuf physique Terminagotchi (vue de face + coupe de côté).

Proposition à valider : dimensions en millimètres, indicatives.
Régénérer : python3 croquis.py   (écrit croquis_oeuf.svg et croquis_oeuf.png à côté du script)
Licence proposée pour le matériel : CERN-OHL-S-2.0.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "none"

H, W, D = 78.0, 58.0, 40.0   # hauteur, largeur, profondeur (mm)
BASE = 3.0                   # méplat sous l'œuf pour qu'il tienne debout
ICI = os.path.dirname(os.path.abspath(__file__))

TRAIT = "#333333"
COQUE = "#fdf3e1"
ECRAN = "#203040"
VERT = "#3a9a45"
VIOLET = "#7a4fc4"
ORANGE = "#d9a400"
BLEU = "#1f6fb2"


def contour(largeur, hauteur, pointe=0.15):
    """Contour d'œuf : plus étroit en haut, méplat en bas."""
    t = np.linspace(0, 2 * np.pi, 400)
    x = (largeur / 2) * np.cos(t) * (1 - pointe * np.sin(t))
    y = (hauteur / 2) * np.sin(t)
    y = np.maximum(y, -hauteur / 2 + BASE)
    return x, y


def cote(ax, x1, y1, x2, y2, texte, decal=(0, 0), vertical=False):
    ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                arrowprops=dict(arrowstyle="<->", color="#888888", lw=1))
    ax.text((x1 + x2) / 2 + decal[0], (y1 + y2) / 2 + decal[1], texte, ha="center", va="center",
            fontsize=9, color="#555555", rotation=90 if vertical else 0,
            bbox=dict(fc="white", ec="none", pad=1))


def etiquette(ax, xy, xytexte, texte, couleur=TRAIT):
    ax.annotate(texte, xy=xy, xytext=xytexte, fontsize=9, color=couleur, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=couleur, lw=0.8))


fig, (af, ac) = plt.subplots(1, 2, figsize=(15, 8.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
fig.suptitle("Œuf physique Terminagotchi — croquis indicatif (dimensions en mm, à valider)",
             fontsize=15, fontweight="bold")

# ------------------------------------------------------------------ vue de face
x, y = contour(W, H)
af.fill(x, y, color=COQUE, zorder=1)
af.plot(x, y, color=TRAIT, lw=2, zorder=2)
# façade décorative interchangeable (motif d'un des 9 œufs) : contour intérieur pointillé
xi, yi = contour(W - 7, H - 7)
af.plot(xi, yi + 0.5, color="#c9a46a", lw=1, ls=(0, (4, 3)), zorder=2)

# écran 1,69 pouce : zone visible ~28 x 33 mm, module ~31 x 37 mm
ey = 9.0
af.add_patch(FancyBboxPatch((-15.5, ey - 18.5), 31, 37, boxstyle="round,pad=0,rounding_size=3",
                            fc="#d8d8d8", ec=TRAIT, lw=1.2, zorder=3))
af.add_patch(FancyBboxPatch((-14, ey - 16.5), 28, 33, boxstyle="round,pad=0,rounding_size=2.5",
                            fc=ECRAN, ec="none", zorder=4))
# petite créature pixelisée sur l'écran
pix = ["..XX..XX..", ".XXXXXXXX.", "XX.XXXX.XX", "XXXXXXXXXX", ".XXX..XXX.", "..XXXXXX..", ".X..XX..X."]
for r, ligne in enumerate(pix):
    for c, ch in enumerate(ligne):
        if ch == "X":
            af.add_patch(Rectangle((-6 + c * 1.2, ey + 4 - r * 1.2), 1.2, 1.2, fc="#7fe08a", ec="none", zorder=5))
af.text(0, ey - 11.5, "~ Mochi ~", ha="center", fontsize=7, color="#cfe8ff", zorder=5)
af.text(0, ey - 14.2, "faim ■■■□  joie ■■■■", ha="center", fontsize=5.5, color="#cfe8ff", zorder=5)

# 3 boutons
for bx, nom in [(-13, "gauche"), (0, "valider"), (13, "droite")]:
    af.add_patch(Circle((bx, -20), 4, fc="#c8efcb" if bx else "#9fdca5", ec=TRAIT, lw=1.3, zorder=3))
    af.text(bx, -26.5, nom, ha="center", fontsize=7.5, color=TRAIT)
# grille haut-parleur
for gx in np.arange(-6, 7, 3):
    af.add_patch(Circle((gx, -31), 0.8, fc=TRAIT, ec="none", zorder=3))
# USB-C en bas
af.add_patch(FancyBboxPatch((-4.5, -H / 2 + BASE - 0.2), 9, 3.2, boxstyle="round,pad=0,rounding_size=1.4",
                            fc="#999999", ec=TRAIT, lw=1, zorder=4))
# antenne LoRa optionnelle (sortie en haut)
af.plot([0, 0], [H / 2, H / 2 + 9], color=VIOLET, lw=3, ls=(0, (1, 1.5)), zorder=1)
af.add_patch(Circle((0, H / 2 + 10), 1.6, fc="white", ec=VIOLET, lw=1.5, ls=":", zorder=2))

# cotes
cote(af, -W / 2, -H / 2 - 7, W / 2, -H / 2 - 7, "largeur ≈ 58")
cote(af, W / 2 + 7, -H / 2 + BASE, W / 2 + 7, H / 2, "hauteur ≈ 78", decal=(2.8, 0), vertical=True)
af.plot([W / 2 - 1, W / 2 + 9], [H / 2, H / 2], color="#bbbbbb", lw=0.6)
af.plot([4.5, W / 2 + 9], [-H / 2 + BASE, -H / 2 + BASE], color="#bbbbbb", lw=0.6)
cote(af, -14, ey + 20.5, 14, ey + 20.5, "écran ≈ 28 × 33", decal=(0, 2.4))

# étiquettes
etiquette(af, (-15.5, ey + 6), (-62, ey + 20), "écran couleur 1,69 pouce\n(la créature vit ici)")
etiquette(af, (-17, -20), (-62, -6), "3 gros boutons\n(doigts d'enfant)", VERT)
etiquette(af, (-6, -31), (-62, -26), "grille du haut-parleur", TRAIT)
etiquette(af, (-4.5, -H / 2 + BASE + 1.5), (-62, -44), "prise USB-C\n(charge + câble PC)", ORANGE)
etiquette(af, (-W / 2 + 6, H / 2 - 22), (-62, 45), "façade décorée amovible\n(motif d'un des 9 œufs)", "#a07a30")
etiquette(af, (1.6, H / 2 + 10), (14, H / 2 + 12), "antenne LoRa (option)", VIOLET)
af.text(0, -H / 2 - 15, "VUE DE FACE", ha="center", fontsize=12, fontweight="bold")
af.text(0, -H / 2 - 19.5, "posé debout sur son méplat", ha="center", fontsize=9, color="#666666")
af.set_xlim(-66, 48)
af.set_ylim(-H / 2 - 23, H / 2 + 18)
af.set_aspect("equal")
af.axis("off")

# ------------------------------------------------------------------ coupe de côté
xs, ys = contour(D, H, pointe=0.10)        # profil de côté (avant = gauche, -x)
ac.fill(xs, ys, color=COQUE, zorder=1)
ac.plot(xs, ys, color=TRAIT, lw=2, zorder=3)
xin, yin = contour(D - 4.4, H - 4.4, pointe=0.10)
ac.fill(xin, yin + 0.3, color="white", zorder=2)
# plan de jonction avant / arrière (clic) : x = -4
ac.plot([-4, -4], [-H / 2 + BASE, H / 2], color="#b05050", lw=1.3, ls="--", zorder=4)
# éléments internes (de l'avant vers l'arrière)
ac.add_patch(Rectangle((-17.8, ey - 18.5), 4.0, 37, fc="#d8d8d8", ec=TRAIT, lw=1, zorder=5))   # écran
ac.add_patch(Rectangle((-17.8, ey - 16.5), 1.0, 33, fc=ECRAN, ec="none", zorder=6))
ac.add_patch(Rectangle((-13.3, -27), 1.6, 50, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=5))        # carte
ac.add_patch(Rectangle((-11.7, -10), 5.5, 18, fc="#b0c8e0", ec=BLEU, lw=1, zorder=5))         # ESP32
ac.text(-8.95, -1, "ESP32", rotation=90, ha="center", va="center", fontsize=6.5, color=BLEU, zorder=6)
ac.add_patch(Rectangle((-18.2, -24), 3.8, 7, fc="#c8efcb", ec=TRAIT, lw=1, zorder=5))          # bouton
ac.add_patch(Rectangle((-3.4, -22), 8.0, 42, fc="#ffd36b", ec=ORANGE, lw=1.2, zorder=5))       # batterie
ac.text(0.6, -1, "batterie LiPo\n~ 8 × 30 × 45", rotation=90, ha="center", va="center", fontsize=7, zorder=6)
ac.add_patch(Rectangle((6.5, -30), 6, 9, fc="#dddddd", ec=TRAIT, lw=1, zorder=5))              # haut-parleur
ac.add_patch(Rectangle((-6, -H / 2 + BASE + 0.5), 7, 3.2, fc="#999999", ec=TRAIT, lw=1, zorder=5))  # USB-C
ac.add_patch(Rectangle((6.8, -6), 3.2, 8, fc="#cccccc", ec=TRAIT, lw=1, zorder=5))             # vis trappe
ac.plot([10, 17.6], [-2, -2], color=TRAIT, lw=2.2, zorder=6)
ac.add_patch(Rectangle((-1, 22), 9, 6, fc="#e2d4ff", ec=VIOLET, lw=1.2, ls=":", zorder=5))     # LoRa
ac.plot([3.5, 3.5], [28, H / 2 + 9], color=VIOLET, lw=3, ls=(0, (1, 1.5)), zorder=4)
# clips
for cy in (24, -24):
    ac.add_patch(Rectangle((-5.5, cy - 1.5), 3, 3, fc="#b05050", ec="none", zorder=5))

etiquette(ac, (-17.8, ey + 12), (-58, ey + 24), "écran derrière une vitre\nde la façade avant")
etiquette(ac, (-12.5, 18), (-58, 26), "carte électronique", "#3c8c4c")
etiquette(ac, (-11.7, -6), (-58, 2), "microcontrôleur ESP32-S3", BLEU)
etiquette(ac, (-18.2, -21), (-58, -16), "bouton (course 1 mm)", VERT)
etiquette(ac, (-6, -H / 2 + BASE + 2), (-58, -34), "prise USB-C", ORANGE)
etiquette(ac, (-4, H / 2 - 4), (-58, 47), "jonction « clic » avant / arrière\n(2 clips de chaque côté)", "#b05050")
etiquette(ac, (4, 26), (24, 40), "module LoRa (option)\n+ antenne", VIOLET)
etiquette(ac, (4.6, 10), (24, 18), "batterie à plat\ncontre le dos", ORANGE)
etiquette(ac, (16, -2), (24, 2), "vis de la trappe\nbatterie (sécurité)", TRAIT)
etiquette(ac, (12.5, -26), (24, -20), "haut-parleur\n(variante complète)", TRAIT)
cote(ac, -D / 2, -H / 2 - 7, D / 2, -H / 2 - 7, "profondeur ≈ 40")
ac.text(-16, H / 2 + 2, "AVANT", ha="center", fontsize=9, color="#666666")
ac.text(16, H / 2 + 2, "ARRIÈRE", ha="center", fontsize=9, color="#666666")
ac.text(0, -H / 2 - 15, "COUPE DE CÔTÉ", ha="center", fontsize=12, fontweight="bold")
ac.text(0, -H / 2 - 19.5, "paroi ≈ 2,2 mm (impression 3D, PLA ou PETG)", ha="center", fontsize=9, color="#666666")
ac.set_xlim(-62, 50)
ac.set_ylim(-H / 2 - 23, H / 2 + 18)
ac.set_aspect("equal")
ac.axis("off")

fig.text(0.5, 0.015, "Variante LoRa : œuf un peu plus grand (≈ 85 × 62 × 44) pour loger le module et une batterie "
         "de 1500 mAh. Croquis de principe, pas un plan de fabrication.",
         ha="center", fontsize=9.5, color="#555555")
plt.tight_layout(rect=(0, 0.03, 1, 0.95))
for ext in ("svg", "png"):
    fig.savefig(os.path.join(ICI, f"croquis_oeuf.{ext}"), dpi=130, facecolor="white")
print("écrit croquis_oeuf.svg et croquis_oeuf.png")
