#!/usr/bin/env python3
"""Croquis indicatif du cyberdeck Terminagotchi, variante B « Poche Linux » (vue de face + coupe de côté).

Proposition à valider : dimensions en millimètres, indicatives.
Régénérer : python3 croquis_cyberdeck.py   (écrit croquis_cyberdeck.svg et .png à côté du script)
Même style que croquis.py (l'œuf). Licence proposée pour le matériel : CERN-OHL-S-2.0.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "none"

L, H, P = 145.0, 124.0, 28.0   # largeur, hauteur, profondeur (épaisseur) en mm
PAS = 12.0                     # pas du clavier : une touche tous les 12 mm (touche ≈ 10 mm)
PAROI = 2.2
ICI = os.path.dirname(os.path.abspath(__file__))

TRAIT = "#333333"
COQUE = "#fdf3e1"
ECRAN = "#203040"
VERT = "#3a9a45"
VIOLET = "#7a4fc4"
ORANGE = "#d9a400"
BLEU = "#1f6fb2"
ROUGE = "#b05050"


def cote(ax, x1, y1, x2, y2, texte, decal=(0, 0), vertical=False):
    ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                arrowprops=dict(arrowstyle="<->", color="#888888", lw=1))
    ax.text((x1 + x2) / 2 + decal[0], (y1 + y2) / 2 + decal[1], texte, ha="center", va="center",
            fontsize=9, color="#555555", rotation=90 if vertical else 0,
            bbox=dict(fc="white", ec="none", pad=1))


def etiquette(ax, xy, xytexte, texte, couleur=TRAIT, ha="left"):
    ax.annotate(texte, xy=xy, xytext=xytexte, fontsize=9, color=couleur, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=couleur, lw=0.8))


fig, (af, ac) = plt.subplots(1, 2, figsize=(17, 9), gridspec_kw=dict(width_ratios=[1.75, 1]))
fig.suptitle("Cyberdeck Terminagotchi (variante B « Poche Linux ») — croquis indicatif (dimensions en mm, à valider)",
             fontsize=15, fontweight="bold")

# ------------------------------------------------------------------ vue de face
af.add_patch(FancyBboxPatch((-L / 2, -H / 2), L, H, boxstyle="round,pad=0,rounding_size=9",
                            fc=COQUE, ec=TRAIT, lw=2, zorder=1))

# écran 4 pouces 800 x 480 : module ≈ 95 x 60, zone visible ≈ 88 x 53
EY0, EY1 = -3.0, 57.0            # bas / haut du module écran
ecy = (EY0 + EY1) / 2
af.add_patch(FancyBboxPatch((-47.5, EY0), 95, 60, boxstyle="round,pad=0,rounding_size=3",
                            fc="#d8d8d8", ec=TRAIT, lw=1.2, zorder=3))
af.add_patch(FancyBboxPatch((-44, ecy - 26.5), 88, 53, boxstyle="round,pad=0,rounding_size=2",
                            fc=ECRAN, ec="none", zorder=4))
# mini-terminal : la créature en haut, une vraie ligne de commande en bas
pix = ["..XX..XX..", ".XXXXXXXX.", "XX.XXXX.XX", "XXXXXXXXXX", ".XXX..XXX.", "..XXXXXX..", ".X..XX..X."]
for r, ligne in enumerate(pix):
    for c, ch in enumerate(ligne):
        if ch == "X":
            af.add_patch(Rectangle((-39 + c * 1.5, ecy + 18 - r * 1.5), 1.5, 1.5, fc="#7fe08a", ec="none", zorder=5))
af.text(-12, ecy + 17, "Mochi  niv. 7", fontsize=8, color="#cfe8ff", zorder=5, family="DejaVu Sans Mono")
af.text(-12, ecy + 11.5, "faim ■■■□  joie ■■■■", fontsize=7, color="#cfe8ff", zorder=5, family="DejaVu Sans Mono")
af.plot([-42, 42], [ecy + 5, ecy + 5], color="#4a6078", lw=0.8, zorder=5)
lignes = ["~/terrain_terminagotchi $ ls -a", ".  ..  .cachette  foret  grotte",
          "~/terrain_terminagotchi $ cd foret", "~/terrain_terminagotchi/foret $ █"]
for i, txt in enumerate(lignes):
    af.text(-42, ecy + 0.5 - i * 5.2, txt, fontsize=7.2, color="#e8f4ff" if "$" in txt else "#9fd0ff",
            zorder=5, family="DejaVu Sans Mono", va="center")

# voyants (à gauche de l'écran) et haut-parleur (à droite)
af.add_patch(Circle((-60, 44), 1.6, fc="#7fe08a", ec=TRAIT, lw=0.8, zorder=3))
af.add_patch(Circle((-60, 37), 1.6, fc="#ffb347", ec=TRAIT, lw=0.8, zorder=3))
for gx in (57, 61, 65):
    for gy in np.arange(18, 42, 4):
        af.add_patch(Circle((gx - 2, gy), 0.8, fc=TRAIT, ec="none", zorder=3))

# clavier : 4 rangées x 11 colonnes, grille droite, pas 12 mm
rangees = [
    ["A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P", "⌫"],
    ["Q", "S", "D", "F", "G", "H", "J", "K", "L", "M", "↵"],
    ["⇧", "W", "X", "C", "V", "B", "N", "-", ".", "/", "↑"],
    ["Ctrl", "Fn", "Tab", "~", "espace", None, None, "|", "←", "↓", "→"],
]
chiffres = list("1234567890")
KY0 = -8.0                                  # haut du clavier
for r, rang in enumerate(rangees):
    for c, nom in enumerate(rang):
        if nom is None:
            continue
        large = 3 if nom == "espace" else 1
        x0 = -L / 2 + 6.5 + c * PAS
        y0 = KY0 - (r + 1) * PAS
        special = nom in ("⌫", "↵", "⇧", "Ctrl", "Fn", "Tab", "espace", "↑", "←", "↓", "→")
        fond = "#c8efcb" if not special else ("#ffe2a8" if nom == "Fn" else "#e4e4e4")
        if nom in ("-", ".", "/", "~", "|"):
            fond = "#d6e8ff"
        af.add_patch(FancyBboxPatch((x0 + 1, y0 + 1), PAS * large - 2, PAS - 2,
                                    boxstyle="round,pad=0,rounding_size=1.8", fc=fond, ec=TRAIT, lw=1, zorder=3))
        af.text(x0 + PAS * large / 2, y0 + PAS / 2 - 0.4, nom, ha="center", va="center",
                fontsize=8 if len(nom) < 3 else 6.5, color=TRAIT, zorder=4, fontweight="bold")
        if r == 0 and c < 10:
            af.text(x0 + PAS - 2.2, y0 + PAS - 3, chiffres[c], ha="center", va="center", fontsize=5.5,
                    color="#c07000", zorder=4)

# cotes
cote(af, -L / 2, -H / 2 - 7, L / 2, -H / 2 - 7, "largeur ≈ 145")
cote(af, L / 2 + 7, -H / 2, L / 2 + 7, H / 2, "hauteur ≈ 124", decal=(2.8, 0), vertical=True)
af.plot([L / 2 - 6, L / 2 + 9], [H / 2, H / 2], color="#bbbbbb", lw=0.6)
af.plot([L / 2 - 6, L / 2 + 9], [-H / 2, -H / 2], color="#bbbbbb", lw=0.6)
cote(af, -44, EY1 + 2.6, 44, EY1 + 2.6, "écran 4 pouces ≈ 88 × 53 (800 × 480 points)", decal=(0, 0))
x_a, x_b = -L / 2 + 6.5, -L / 2 + 6.5 + PAS
cote(af, x_a, -H / 2 + 2.2, x_b, -H / 2 + 2.2, "", decal=(0, 0))
af.text((x_a + x_b) / 2, -H / 2 - 1.8, "12", ha="center", fontsize=8, color="#555555")

# étiquettes (à gauche)
etiquette(af, (-44, ecy + 18), (-140, 58), "écran couleur 4 pouces\nla créature en haut,\nune vraie ligne de commande en bas")
etiquette(af, (-60, 44), (-140, 30), "voyants : allumé (vert)\net charge (orange)", "#5a8a40")
etiquette(af, (-L / 2 + 7.5, -32), (-140, 8), "clavier 44 touches, AZERTY,\ntouches ≈ 10 mm (doigts d'enfant)", VERT)
etiquette(af, (L / 2 - 30, -40), (85, -22), "symboles du terminal\nen bleu : - . / ~ |\nsans touche spéciale", BLEU)
etiquette(af, (-L / 2 + 7.5, -55), (-140, -42), "Fn + rangée du haut = chiffres\n(petits chiffres orange)", ORANGE)
etiquette(af, (63, 30), (85, 50), "haut-parleur", TRAIT)
af.text(0, -H / 2 - 15, "VUE DE FACE", ha="center", fontsize=12, fontweight="bold")
af.text(0, -H / 2 - 20, "posé à plat sur la table ou tenu à deux mains", ha="center", fontsize=9, color="#666666")
af.set_xlim(-143, 118)
af.set_ylim(-H / 2 - 24, H / 2 + 10)
af.set_aspect("equal")
af.axis("off")

# ------------------------------------------------------------------ coupe de côté
# x = épaisseur (avant = gauche), y = hauteur (haut du cyberdeck en haut)
ac.add_patch(FancyBboxPatch((-P / 2, -H / 2), P, H, boxstyle="round,pad=0,rounding_size=4",
                            fc=COQUE, ec=TRAIT, lw=2, zorder=1))
ac.add_patch(Rectangle((-P / 2 + PAROI, -H / 2 + PAROI), P - 2 * PAROI, H - 2 * PAROI, fc="white", ec="none", zorder=2))
xa = -P / 2 + PAROI                      # face intérieure de l'avant
# plan de jonction avant / arrière (vis) : x = -2
ac.plot([-2, -2], [-H / 2, H / 2], color=ROUGE, lw=1.3, ls="--", zorder=4)
# écran
ac.add_patch(Rectangle((xa, EY0), 4.5, 60, fc="#d8d8d8", ec=TRAIT, lw=1, zorder=5))
ac.add_patch(Rectangle((xa, ecy - 26.5), 1.0, 53, fc=ECRAN, ec="none", zorder=6))
# clavier : touches qui dépassent de la façade + plaque du clavier
for r in range(4):
    y0 = KY0 - (r + 1) * PAS
    ac.add_patch(Rectangle((-P / 2 - 2.0, y0 + 1), 5.5, PAS - 2, fc="#c8efcb", ec=TRAIT, lw=0.9, zorder=5))
ac.add_patch(Rectangle((xa + 3.3, KY0 - 4 * PAS), 1.6, 4 * PAS, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=5))
ac.add_patch(Rectangle((xa + 4.9, -34), 2.2, 9, fc="#b0c8e0", ec=BLEU, lw=0.8, zorder=5))   # puce du clavier
# carte Linux derrière l'écran
ac.add_patch(Rectangle((-1.0, 8), 1.6, 42, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=5))
ac.add_patch(Rectangle((0.6, 18), 3.0, 20, fc="#b0c8e0", ec=BLEU, lw=1, zorder=5))
ac.text(2.1, 28, "Linux", rotation=90, ha="center", va="center", fontsize=6.5, color=BLEU, zorder=6)
ac.add_patch(Rectangle((3.6, 21), 2.0, 14, fc="#c0c0c0", ec=TRAIT, lw=0.8, zorder=5))       # dissipateur
for k in range(4):
    ac.plot([5.6, 7.4], [22.5 + k * 3.5, 22.5 + k * 3.5], color=TRAIT, lw=1, zorder=5)
ac.add_patch(Rectangle((-1.0, 0.5), 1.6, 3.5, fc="#2a2a2a", ec=TRAIT, lw=0.8, zorder=5))    # microSD
# carte d'alimentation (charge + 5 V) en haut
ac.add_patch(Rectangle((-1.0, 51), 9, 1.6, fc="#3c8c4c", ec=TRAIT, lw=1, zorder=5))
ac.add_patch(Rectangle((1.0, H / 2 - PAROI - 0.2), 7, 3.2 + PAROI, fc="#999999", ec=TRAIT, lw=1, zorder=5))  # USB-C
ac.add_patch(Rectangle((-8.5, H / 2 - 0.5), 4.5, 2.5, fc=ROUGE, ec=TRAIT, lw=1, zorder=5))    # bouton marche
# aérations à l'arrière
for k in range(5):
    ac.add_patch(Rectangle((P / 2 - PAROI - 0.1, 18 + k * 4), PAROI + 0.2, 2, fc="white", ec="none", zorder=5))
# deux accus 18650 protégés (couchés dans la largeur : on les voit en rond)
for cy in (-22.0, -43.0):
    ac.add_patch(Circle((3.0, cy), 9.2, fc="#ffd36b", ec=ORANGE, lw=1.4, zorder=5))
    ac.text(3.0, cy, "18650\nprotégé", ha="center", va="center", fontsize=6.5, zorder=6)
ac.add_patch(Rectangle((-6.4, -54), 1.0, 43, fc="#888888", ec="none", zorder=5))           # séparation isolante
# trappe vissée
ac.add_patch(Rectangle((P / 2 - PAROI, -56), PAROI, 46, fc="#f3e2c0", ec=ROUGE, lw=1, ls=":", zorder=6))
ac.add_patch(Rectangle((P / 2 - 0.3, -33.5), 3.0, 3, fc="#cccccc", ec=TRAIT, lw=1, zorder=6))

etiquette(ac, (xa, ecy + 20), (-60, 52), "écran derrière une vitre\nde la façade avant")
etiquette(ac, (-P / 2 - 2, -14), (-60, -6), "touches (course ≈ 2 mm)", VERT)
etiquette(ac, (xa + 4.1, -50), (-60, -26), "plaque du clavier +\nsa petite puce (clavier USB)", "#3c8c4c")
etiquette(ac, (-8.5, H / 2 + 1), (-60, H / 2 + 6), "bouton marche / arrêt propre", ROUGE)
etiquette(ac, (-2, -H / 2 + 6), (-60, -54), "jonction avant / arrière\n(4 vis + inserts)", ROUGE)
etiquette(ac, (4.5, H / 2 + 1), (20, H / 2 + 6), "prise USB-C (charge + PC)", ORANGE)
etiquette(ac, (5.0, 52), (20, 44), "carte charge + 5 V\n(avec protections)", "#3c8c4c")
etiquette(ac, (3.6, 34), (20, 32), "carte Linux + dissipateur", BLEU)
etiquette(ac, (P / 2, 22), (20, 18), "fentes d'aération", TRAIT)
etiquette(ac, (0.0, 2), (20, 6), "carte microSD (le système)", TRAIT)
etiquette(ac, (12.2, -22), (20, -14), "2 accus 18650 protégés\n(≈ 22 Wh au total)", ORANGE)
etiquette(ac, (P / 2 + 2.7, -32), (20, -40), "trappe batterie vissée\n(adulte seulement)", ROUGE)
cote(ac, -P / 2, -H / 2 - 7, P / 2, -H / 2 - 7, "épaisseur ≈ 28")
ac.text(-10, H / 2 + 14, "AVANT", ha="center", fontsize=9, color="#666666")
ac.text(10, H / 2 + 14, "ARRIÈRE", ha="center", fontsize=9, color="#666666")
ac.text(0, -H / 2 - 15, "COUPE DE CÔTÉ", ha="center", fontsize=12, fontweight="bold")
ac.text(0, -H / 2 - 20, "paroi ≈ 2,2 mm (impression 3D, PETG conseillé)", ha="center", fontsize=9, color="#666666")
ac.set_xlim(-64, 64)
ac.set_ylim(-H / 2 - 24, H / 2 + 18)
ac.set_aspect("equal")
ac.axis("off")

fig.text(0.5, 0.015, "Variante A « Micro » : même clavier, écran 2,8 pouces, plus fine (≈ 145 × 100 × 20). "
         "Variante C « Grand confort » : écran 5 pouces, ventilateur (≈ 175 × 140 × 32). "
         "Croquis de principe, pas un plan de fabrication.",
         ha="center", fontsize=9.5, color="#555555")
plt.tight_layout(rect=(0, 0.03, 1, 0.95))
for ext in ("svg", "png"):
    fig.savefig(os.path.join(ICI, f"croquis_cyberdeck.{ext}"), dpi=130, facecolor="white")
print("écrit croquis_cyberdeck.svg et croquis_cyberdeck.png")
