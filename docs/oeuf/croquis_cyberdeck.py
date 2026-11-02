#!/usr/bin/env python3
"""Croquis indicatif du cyberdeck Terminagotchi à CLAPET, variante C « Grand confort » (écran 5 pouces).

Trois vues : (1) ouvert à plat, vu de face ; (2) de côté, ouvert et fermé ; (3) coupe de côté, fermé.
Proposition à valider : dimensions en millimètres, indicatives. Ce n'est pas un plan de fabrication.
Régénérer : python3 croquis_cyberdeck.py   (écrit croquis_cyberdeck.svg et .png à côté du script)
Même style que croquis.py (l'œuf). Licence proposée pour le matériel : CERN-OHL-S-2.0.
"""
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "none"

L = 160.0        # largeur
D = 120.0        # profondeur (de l'avant à la charnière), la même pour le bas et le couvercle
EB = 24.0        # épaisseur du bas (clavier, cartes, accus)
EC = 10.0        # épaisseur du couvercle (écran)
PAS = 12.0       # pas du clavier : une touche tous les 12 mm (touche ≈ 10 mm)
ICI = os.path.dirname(os.path.abspath(__file__))

TRAIT = "#333333"
COQUE = "#fdf3e1"
ECRAN = "#203040"
VERT = "#3a9a45"
ORANGE = "#d9a400"
BLEU = "#1f6fb2"
ROUGE = "#b05050"
GRIS = "#666666"


def cote(ax, x1, y1, x2, y2, texte, decal=(0, 0), vertical=False, taille=9):
    ax.annotate("", xy=(x1, y1), xytext=(x2, y2), arrowprops=dict(arrowstyle="<->", color="#888888", lw=1))
    if texte:
        ax.text((x1 + x2) / 2 + decal[0], (y1 + y2) / 2 + decal[1], texte, ha="center", va="center",
                fontsize=taille, color="#555555", rotation=90 if vertical else 0,
                bbox=dict(fc="white", ec="none", pad=1))


def etiquette(ax, xy, xytexte, texte, couleur=TRAIT, ha="left"):
    ax.annotate(texte, xy=xy, xytext=xytexte, fontsize=9, color=couleur, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=couleur, lw=0.8))


fig = plt.figure(figsize=(19, 12.5))
gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1.05])
af = fig.add_subplot(gs[:, 0])    # vue de face, ouvert à plat
ad = fig.add_subplot(gs[0, 1])    # de côté : ouvert et fermé
ac = fig.add_subplot(gs[1, 1])    # coupe de côté, fermé
fig.suptitle("Cyberdeck Terminagotchi à clapet (variante C « Grand confort ») — croquis indicatif "
             "(dimensions en mm, à valider)", fontsize=15, fontweight="bold")

# ================================================================== 1. ouvert à plat, vu de face
# y = 0 : bord avant du bas ; y = D : charnière ; y = 2D : haut du couvercle
af.add_patch(FancyBboxPatch((-L / 2, 0), L, D, boxstyle="round,pad=0,rounding_size=8",
                            fc=COQUE, ec=TRAIT, lw=2, zorder=1))
af.add_patch(FancyBboxPatch((-L / 2, D + 1.5), L, D - 1.5, boxstyle="round,pad=0,rounding_size=8",
                            fc=COQUE, ec=TRAIT, lw=2, zorder=1))
# charnières (2, à friction : l'écran tient à l'angle choisi)
for hx in (-58, 58):
    af.add_patch(Rectangle((hx - 9, D - 3), 18, 6, fc="#bdbdbd", ec=TRAIT, lw=1, zorder=4))

# --- écran 5 pouces 1280 x 720 : module ≈ 121 x 76, zone visible ≈ 111 x 62
ecy = D + 64.0
af.add_patch(FancyBboxPatch((-60.5, ecy - 38), 121, 76, boxstyle="round,pad=0,rounding_size=3",
                            fc="#d8d8d8", ec=TRAIT, lw=1.2, zorder=3))
af.add_patch(FancyBboxPatch((-55.5, ecy - 31), 111, 62, boxstyle="round,pad=0,rounding_size=2",
                            fc=ECRAN, ec="none", zorder=4))
# le jeu PC tel quel (mini-terminal) : une créature simple, sans accessoire, et une vraie ligne de commande
pix = ["..XX..XX..", ".XXXXXXXX.", "XX.XXXX.XX", "XXXXXXXXXX", ".XXX..XXX.", "..XXXXXX..", ".X..XX..X."]
for r, ligne in enumerate(pix):
    for c, ch in enumerate(ligne):
        if ch == "X":
            af.add_patch(Rectangle((-50 + c * 1.8, ecy + 24 - r * 1.8), 1.8, 1.8, fc="#7fe08a", ec="none", zorder=5))
af.text(-28, ecy + 23, "Mochi  niv. 7", fontsize=8.5, color="#cfe8ff", zorder=5, family="DejaVu Sans Mono")
af.text(-28, ecy + 16.5, "faim ■■■□  joie ■■■■", fontsize=7.5, color="#cfe8ff", zorder=5, family="DejaVu Sans Mono")
af.plot([-53, 53], [ecy + 10, ecy + 10], color="#4a6078", lw=0.8, zorder=5)
lignes = ["~/terrain_terminagotchi $ ls -a", ".  ..  .cachette  foret  grotte",
          "~/terrain_terminagotchi $ cd foret", "~/terrain_terminagotchi/foret $ cat lettre.txt",
          "Bravo, tu as trouvé la forêt !", "~/terrain_terminagotchi/foret $ █"]
for i, txt in enumerate(lignes):
    af.text(-53, ecy + 5 - i * 5.6, txt, fontsize=7.4, color="#e8f4ff" if "$" in txt else "#9fd0ff",
            zorder=5, family="DejaVu Sans Mono", va="center")
# haut-parleur dans le bas du couvercle (près de la charnière)
for gx in np.arange(-10, 11, 4):
    for gy in (D + 10, D + 14):
        af.add_patch(Circle((gx, gy), 0.9, fc=TRAIT, ec="none", zorder=3))

# --- bas : zone arrière (accus dessous) puis clavier 5 rangées x 11
af.add_patch(Rectangle((-70, 76), 140, 38, fc="none", ec=ORANGE, lw=1.2, ls="--", zorder=2))
af.text(0, 99, "dessous : 4 accus 18650 protégés\n(trappe vissée, sous l'appareil)", ha="center", va="center",
        fontsize=8, color="#a07800", zorder=3)
af.add_patch(Circle((-62, 108), 1.8, fc="#7fe08a", ec=TRAIT, lw=0.8, zorder=3))
af.add_patch(Circle((-56, 108), 1.8, fc="#ffb347", ec=TRAIT, lw=0.8, zorder=3))
af.add_patch(FancyBboxPatch((52, 104), 12, 7, boxstyle="round,pad=0,rounding_size=2",
                            fc=ROUGE, ec=TRAIT, lw=1, zorder=3))
for k in range(6):                               # fentes d'aération sur le dessus
    af.add_patch(Rectangle((-66 + k * 4, 80), 2, 10, fc="#bbbbbb", ec="none", zorder=3))
# prise USB-C sur le côté droit
af.add_patch(Rectangle((L / 2 - 1, 84), 3, 9, fc="#999999", ec=TRAIT, lw=1, zorder=3))

rangees = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "⌫"],
    ["A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P", "↵"],
    ["Q", "S", "D", "F", "G", "H", "J", "K", "L", "M", None],
    ["⇧", "W", "X", "C", "V", "B", "N", "-", ".", "/", "↑"],
    ["Ctrl", "Fn", "Tab", "~", "espace", None, None, "|", "←", "↓", "→"],
]
KY1 = 72.0                                       # haut du clavier
KX0 = -66.0
for r, rang in enumerate(rangees):
    for c, nom in enumerate(rang):
        if nom is None:
            continue
        large = 3 if nom == "espace" else 1
        haut = 2 if nom == "↵" else 1
        x0 = KX0 + c * PAS
        y0 = KY1 - (r + haut) * PAS
        special = nom in ("⌫", "↵", "⇧", "Ctrl", "Fn", "Tab", "espace", "↑", "←", "↓", "→")
        fond = "#c8efcb" if not special else ("#ffe2a8" if nom == "Fn" else "#e4e4e4")
        if nom in ("-", ".", "/", "~", "|"):
            fond = "#d6e8ff"
        if nom.isdigit():
            fond = "#fff3d6"
        af.add_patch(FancyBboxPatch((x0 + 1, y0 + 1), PAS * large - 2, PAS * haut - 2,
                                    boxstyle="round,pad=0,rounding_size=1.8", fc=fond, ec=TRAIT, lw=1, zorder=3))
        af.text(x0 + PAS * large / 2, y0 + PAS * haut / 2 - 0.4, nom, ha="center", va="center",
                fontsize=8.5 if len(nom) < 3 else 6.5, color=TRAIT, zorder=4, fontweight="bold")

# cotes
cote(af, -L / 2, -8, L / 2, -8, "largeur ≈ 160")
cote(af, L / 2 + 8, 0, L / 2 + 8, D, "≈ 120", decal=(3, 0), vertical=True)
cote(af, L / 2 + 8, D, L / 2 + 8, 2 * D, "≈ 120", decal=(3, 0), vertical=True)
cote(af, -55.5, ecy + 34.5, 55.5, ecy + 34.5, "écran 5 pouces ≈ 111 × 62 (1280 × 720 points)")
cote(af, KX0, 3, KX0 + PAS, 3, "")
af.text(KX0 + PAS / 2, -1.5, "12", ha="center", fontsize=8, color="#555555")

# étiquettes
etiquette(af, (-55.5, ecy + 20), (-175, D + 95), "écran couleur 5 pouces :\nle jeu PC tel quel\n(créature en haut,\nvraie ligne de commande)")
etiquette(af, (-58, D), (-175, D + 30), "2 charnières à friction :\nl'écran se replie\nsur le clavier", GRIS)
etiquette(af, (-10, D + 12), (-175, D + 8), "haut-parleur", TRAIT)
etiquette(af, (-62, 108), (-175, 108), "voyants : allumé (vert)\net charge (orange)", "#5a8a40")
etiquette(af, (-66, 85), (-175, 84), "fentes d'aération", GRIS)
etiquette(af, (KX0 + 1, 40), (-175, 50), "clavier 55 touches, AZERTY,\ntouches ≈ 10 mm\n(doigts d'enfant),\nvraie rangée de chiffres", VERT)
etiquette(af, (KX0 + 3 * PAS + 6, 13.2), (-175, 8), "symboles du terminal\nen bleu : - . / ~ |", BLEU)
etiquette(af, (64, 107), (100, 110), "bouton marche /\narrêt propre", ROUGE)
etiquette(af, (L / 2 + 2, 88), (100, 78), "prise USB-C\n(côté droit)", ORANGE)
af.text(0, -17, "1. OUVERT À PLAT, VU DE FACE", ha="center", fontsize=12, fontweight="bold")
af.text(0, -23, "en vrai, l'écran s'arrête vers 110° (comme un petit ordinateur portable)",
        ha="center", fontsize=9, color=GRIS)
af.set_xlim(-178, 130)
af.set_ylim(-27, 2 * D + 6)
af.set_aspect("equal")
af.axis("off")

# ================================================================== 2. de côté : ouvert et fermé
# x = profondeur (avant à gauche, charnière à droite), y = hauteur


def bas(ax, x0):
    ax.add_patch(FancyBboxPatch((x0, 0), D, EB, boxstyle="round,pad=0,rounding_size=3",
                                fc=COQUE, ec=TRAIT, lw=1.8, zorder=2))
    for k in range(4):                           # dessus des touches (en creux)
        ax.add_patch(Rectangle((x0 + 10 + k * 15, EB - 1.8), 10, 1.4, fc="#c8efcb", ec=TRAIT, lw=0.6, zorder=3))


# fermé (à gauche)
X1 = 0.0
bas(ad, X1)
ad.add_patch(FancyBboxPatch((X1, EB + 0.5), D, EC - 0.5, boxstyle="round,pad=0,rounding_size=3",
                            fc="#f6e6c8", ec=TRAIT, lw=1.8, zorder=2))
ad.add_patch(Circle((X1 + D - 3, EB), 3, fc="#bdbdbd", ec=TRAIT, lw=1, zorder=4))
cote(ad, X1, -7, X1 + D, -7, "≈ 120")
cote(ad, X1 - 7, 0, X1 - 7, EB, "24", decal=(-3.5, 0), vertical=True, taille=8)
cote(ad, X1 - 7, EB, X1 - 7, EB + EC, "10", decal=(-3.5, 0), vertical=True, taille=8)
cote(ad, X1 - 18, 0, X1 - 18, EB + EC, "≈ 34", decal=(-4, 0), vertical=True)
ad.text(X1 + D / 2, -17, "FERMÉ : ≈ 160 × 120 × 34 mm", ha="center", fontsize=10, fontweight="bold")
ad.text(X1 + D / 2, -23, "l'écran est protégé dans le sac", ha="center", fontsize=8.5, color=GRIS)

# ouvert à 110° (à droite)
X2 = 150.0
bas(ad, X2)
hx, hy = X2 + D - 3, EB
ang = math.radians(180 - 110)                    # direction du couvercle depuis la charnière
ux, uy = math.cos(ang), math.sin(ang)
nx, ny = uy, -ux                                 # vers l'intérieur (côté écran)
p = [(hx, hy), (hx + ux * D, hy + uy * D), (hx + ux * D - nx * EC, hy + uy * D - ny * EC), (hx - nx * EC, hy - ny * EC)]
ad.add_patch(Polygon(p, closed=True, fc="#f6e6c8", ec=TRAIT, lw=1.8, zorder=2))
# face de l'écran (côté enfant = côté gauche)
e0, e1 = 22, 98
ad.plot([hx + ux * e0 - nx * 0.8, hx + ux * e1 - nx * 0.8], [hy + uy * e0 - ny * 0.8, hy + uy * e1 - ny * 0.8],
        color=ECRAN, lw=3.2, zorder=3)
ad.add_patch(Circle((hx, hy), 3, fc="#bdbdbd", ec=TRAIT, lw=1, zorder=4))
ad.annotate("", xy=(hx - 26, hy + 6), xytext=(hx - 8, hy + 26),
            arrowprops=dict(arrowstyle="<-", color="#888888", lw=1, connectionstyle="arc3,rad=0.35"))
ad.text(hx - 26, hy + 24, "≈ 110°", fontsize=9, color="#555555", ha="center")
ad.text(X2 + D / 2 - 8, -17, "OUVERT : posé sur la table", ha="center", fontsize=10, fontweight="bold")
ad.text(X2 + D / 2 - 8, -23, "hauteur ≈ 135 mm écran levé", ha="center", fontsize=8.5, color=GRIS)
etiquette(ad, (hx + ux * 60 - nx, hy + uy * 60 - ny), (X2 - 2, 95), "écran", ECRAN, ha="right")
etiquette(ad, (hx, hy + 2), (X2 + D + 30, 60), "charnière", GRIS)
ad.text((X1 + X2 + D) / 2, 150, "2. DE CÔTÉ (avant à gauche, charnière à droite)", ha="center",
        fontsize=12, fontweight="bold")
ad.set_xlim(-30, X2 + D + 55)
ad.set_ylim(-27, 158)
ad.set_aspect("equal")
ad.axis("off")

# ================================================================== 3. coupe de côté, fermé (échelle plus grande)
E = EB + EC
ac.add_patch(FancyBboxPatch((0, 0), D, EB, boxstyle="round,pad=0,rounding_size=3",
                            fc=COQUE, ec=TRAIT, lw=2, zorder=1))
ac.add_patch(Rectangle((2, 2), D - 4, EB - 4, fc="white", ec="none", zorder=2))
ac.add_patch(FancyBboxPatch((0, EB + 0.5), D, EC - 0.5, boxstyle="round,pad=0,rounding_size=3",
                            fc="#f6e6c8", ec=TRAIT, lw=2, zorder=1))
ac.add_patch(Rectangle((2, EB + 0.5), D - 4, EC - 2.5, fc="white", ec="none", zorder=2))
# couvercle : vitre, écran, haut-parleur
ac.add_patch(Rectangle((20, EB + 0.5), 80, 1.0, fc="#cfe6f5", ec=BLEU, lw=0.6, zorder=3))
ac.add_patch(Rectangle((22, EB + 1.5), 76, 4.0, fc="#d8d8d8", ec=TRAIT, lw=1, zorder=3))
ac.add_patch(Rectangle((22, EB + 1.5), 76, 1.0, fc=ECRAN, ec="none", zorder=4))
ac.add_patch(Rectangle((104, EB + 1.5), 12, 4.5, fc="#888888", ec=TRAIT, lw=0.8, zorder=3))
# bas : plaque du dessus, touches en creux, plaque du clavier
for k in range(5):
    x0 = 8 + k * PAS
    ac.add_patch(Rectangle((x0 + 1, 19.5), PAS - 2, 3.8, fc="#c8efcb", ec=TRAIT, lw=0.7, zorder=4))
    ac.add_patch(Rectangle((x0 + 3, 16.2), PAS - 6, 3.3, fc="#eeeeee", ec=TRAIT, lw=0.5, zorder=4))
ac.add_patch(Rectangle((6, 14.6), 64, 1.6, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=4))
# carte Linux + dissipateur + petit ventilateur
ac.add_patch(Rectangle((8, 3.0), 50, 1.6, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=4))
ac.add_patch(Rectangle((22, 4.6), 22, 3.5, fc="#c0c0c0", ec=TRAIT, lw=0.8, zorder=4))
ac.add_patch(Rectangle((24, 8.1), 18, 5.5, fc="#a8c4dd", ec=BLEU, lw=0.8, zorder=4))
ac.text(33, 10.85, "ventilo", ha="center", va="center", fontsize=6.5, color=BLEU, zorder=5)
ac.add_patch(Rectangle((8, 4.6), 3, 1.2, fc="#2a2a2a", ec="none", zorder=4))     # microSD
for k in range(4):                                                                   # fentes sous le ventilateur
    ac.add_patch(Rectangle((25 + k * 4.5, -0.1), 2.2, 2.2, fc="white", ec="none", zorder=3))
# carte charge + 5 V
ac.add_patch(Rectangle((60, 3.0), 14, 1.6, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=4))
# paroi isolante + 4 accus 18650 (2 rangées de 2, couchés dans la largeur : on les voit en rond)
ac.add_patch(Rectangle((76, 2), 1.2, 19, fc="#888888", ec="none", zorder=4))
for cx in (88.0, 107.5):
    ac.add_patch(Circle((cx, 12.0), 9.25, fc="#ffd36b", ec=ORANGE, lw=1.4, zorder=4))
    ac.text(cx, 12.0, "18650\nprotégé", ha="center", va="center", fontsize=6.5, zorder=5)
# trappe vissée sous les accus
ac.add_patch(Rectangle((78, 0), 40, 2, fc="#f3e2c0", ec=ROUGE, lw=1, ls=":", zorder=5))
ac.add_patch(Rectangle((97, -2.4), 3, 2.4, fc="#cccccc", ec=TRAIT, lw=1, zorder=5))
# charnière
ac.add_patch(Circle((D - 3, EB), 3, fc="#bdbdbd", ec=TRAIT, lw=1, zorder=6))

etiquette(ac, (60, EB + 4.5), (30, 52), "écran 5 pouces derrière une vitre", TRAIT)
etiquette(ac, (110, EB + 4), (112, 48), "haut-parleur", TRAIT)
etiquette(ac, (D - 3, EB + 2), (128, 36), "charnière", GRIS)
etiquette(ac, (8 + 1.5 * PAS, 23), (-55, 44), "touches en creux :\nfermé, l'écran ne les touche pas", VERT)
etiquette(ac, (6, 15.4), (-55, 20), "plaque du clavier\n+ sa petite puce", "#3c8c4c")
etiquette(ac, (24, 10), (-55, 8), "carte Linux + dissipateur\n+ petit ventilateur", BLEU)
etiquette(ac, (9, 5.2), (-55, -6), "carte microSD (le système)", TRAIT)
etiquette(ac, (30, 0), (20, -14), "aération dessous", GRIS)
etiquette(ac, (67, 3.8), (55, -14), "carte charge + 5 V\n(protections)", "#3c8c4c")
etiquette(ac, (76.6, 18), (128, 18), "paroi isolante", GRIS)
etiquette(ac, (116, 12), (128, 6), "4 accus 18650 protégés\n(2 rangées de 2 ; ≈ 44 Wh)", ORANGE)
etiquette(ac, (100, -1.2), (128, -8), "trappe vissée\n(adulte seulement)", ROUGE)
cote(ac, 0, -22, D, -22, "≈ 120")
ac.text(D / 2, 62, "3. COUPE DE CÔTÉ, FERMÉ (échelle plus grande)", ha="center", fontsize=12, fontweight="bold")
ac.text(D / 2, -30, "avant à gauche · paroi ≈ 2 mm · PETG conseillé (supporte mieux la chaleur)",
        ha="center", fontsize=9, color=GRIS)
ac.set_xlim(-58, 172)
ac.set_ylim(-34, 68)
ac.set_aspect("equal")
ac.axis("off")

fig.text(0.5, 0.012, "Option plus petite et moins chère (« Clapet compact ») : écran 4 pouces, 44 touches (chiffres avec Fn), "
         "2 accus, pas de ventilateur — fermé ≈ 145 × 100 × 31 mm. Croquis de principe, pas un plan de fabrication.",
         ha="center", fontsize=9.5, color="#555555")
plt.tight_layout(rect=(0, 0.025, 1, 0.955))
for ext in ("svg", "png"):
    fig.savefig(os.path.join(ICI, f"croquis_cyberdeck.{ext}"), dpi=120, facecolor="white")
print("écrit croquis_cyberdeck.svg et croquis_cyberdeck.png")
