"""Ce que montrent la créature du bureau et l'île, sous forme d'une LISTE DE DESSIN, sans fenêtre.

Chaque fenêtre (GTK 4, tkinter, ou une capture simulée avec PIL pour les tests et les maquettes) dessine la même liste :
    ("img", cadre, x, y, echelle, miroir, lisse)          une image de poses.py (coin haut gauche)
    ("imgt", cadre, ax, ay, echelle, miroir, lisse, sx, sy, rot, opacite)
                                                          une image posée par son ancre (ax, ay : les pieds), déformée
                                                          autour des pieds (sx, sy, rot en degrés) et plus ou moins
                                                          opaque : la vie et les transitions (bureau_vie.animer)
    ("rrect", x, y, w, h, rayon, fond, bord, epaisseur)   rectangle arrondi (couleurs (r, g, b, a) ou None)
    ("ellipse", cx, cy, rx, ry, fond)                     ombre, pastille
    ("arc", cx, cy, rx, ry, couleur, epaisseur)           le cercle pointillé du menu
    ("texte", x, y, texte, taille, couleur, gras, ancre, mono)   ancre « g » (gauche), « c » (centre), « d » (droite) ;
                                                                  y = milieu de la ligne
    ("rect", x, y, w, h, couleur)                         un pixel de particule
Et des ZONES cliquables : (x, y, w, h, action). Les zones servent aussi de « région de saisie » : ailleurs, les clics
passent à travers (vers les fenêtres de dessous).
Le style suit les maquettes validées (docs/maquettes/bureau_mochi.png et ile_haut.png).
"""
import math

from . import bureau_vie as V
from .langue import sans_marques, t

# couleurs (r, g, b, a)
FOND = (14, 16, 24, 236)
FOND_CARTE = (22, 25, 36, 245)
BORD = (255, 255, 255, 30)
TEXTE = (233, 236, 242, 255)
TEXTE_DOUX = (154, 163, 181, 255)
VERT = (61, 220, 132, 255)
ORANGE = (255, 159, 67, 255)
JAUNE = (255, 213, 79, 255)
VIOLET = (178, 132, 255, 255)
BLEU = (95, 175, 255, 255)
ROUGE = (255, 95, 109, 255)
BULLE = (245, 240, 230, 250)
BULLE_TEXTE = (30, 30, 46, 255)
ICONES = {"jouer": VERT, "terminal": (77, 208, 225, 255), "soccuper": ORANGE, "carte": JAUNE, "ranger": ROUGE,
          "reglages": TEXTE_DOUX, "equipe": VIOLET}


def _a(c, a):
    return c[:3] + (a,)


def _f(c, a):
    """La couleur c rendue plus transparente (a sur 255) : l'île qui s'ouvre apparaît en fondu."""
    return c[:3] + (c[3] * a // 255,)


def echelle(album, taille):
    """L'échelle d'affichage d'un album pour une hauteur visée : un dessin garde la taille relative des espèces
    (grand bébé, petit bébé), une image en gros pixels prend un multiple entier (pixels nets)."""
    if album.lisse:
        e = taille / 120
        return min(max(e, 0.7 * taille / album.ref), 1.35 * taille / album.ref)
    return float(max(1, round(taille / album.ref)))


def couper(texte, largeur, taille):
    """Coupe un texte en lignes d'au plus largeur pixels (mots entiers ; les écritures sans espaces au caractère)."""
    lignes = []
    for para in str(texte).split("\n"):
        mots = para.split(" ") if " " in para else list(para)
        sep = " " if " " in para else ""
        cour = ""
        for m in mots:
            essai = (cour + sep + m) if cour else m
            if cour and V.largeur_texte(essai, taille) > largeur:
                lignes.append(cour)
                cour = m
            else:
                cour = essai
        lignes.append(cour)
    return lignes


def bulle(liste, texte, cx, bas, largeur_max=240, taille=13, zone_l=None):
    """Une bulle de parole dont la pointe touche (cx, bas)."""
    lignes = couper(sans_marques(texte), largeur_max - 24, taille)[:5]
    w = min(largeur_max, max(V.largeur_texte(l, taille) for l in lignes) + 26)
    h = len(lignes) * (taille + 5) + 16
    x = cx - w / 2
    if zone_l is not None:
        x = min(max(6, x), zone_l - w - 6)
    y = bas - h - 10
    liste.append(("rrect", x, y, w, h, 12, BULLE, (200, 191, 174, 255), 1))
    liste.append(("rrect", cx - 6, bas - 12, 12, 8, 3, BULLE, None, 0))
    for i, l in enumerate(lignes):
        liste.append(("texte", x + w / 2, y + 8 + (taille + 5) * i + (taille + 5) / 2, l, taille, BULLE_TEXTE, False,
                      "c", False))
    return x, y, w, h


# ---------------------------------------------------------------- la créature du bureau
class VueCreature:
    """Ce qu'on montre autour de la créature, en plus d'elle : menu, panneau (réglages, équipe, envies), bulle,
    petits textes qui montent (« miam »), cœurs."""

    def __init__(self):
        self.menu = False
        self.panneau = None              # (titre, [(texte, action)])
        self.bulle = None                # (texte, jusqu'à quand)
        self.flottants = []              # [texte, âge en secondes, couleur]
        self.boutons = []

    def dire(self, texte, t, duree=6.0):
        self.bulle = (texte, t + duree)

    def flotter(self, texte, couleur=JAUNE):
        self.flottants.append([texte, 0.0, couleur])

    def tick(self, dt):
        for f in list(self.flottants):
            f[1] += dt
            if f[1] > 1.6:
                self.flottants.remove(f)


def libelles_menu():
    return {cle: t("bur.menu." + cle) for cle, _s, _a in V.MENU}


def effets(L, an, px, py, largeur_corps, haut_corps, derriere):
    """Les petits effets de an (bureau_vie.Anime) : la miette (derrière la créature), les « z », le cœur et
    l'étincelle (devant)."""
    sens = -1 if an.miroir else 1
    for genre, fx, fy, ft, fa in an.effets:
        if (genre == "miette") != derriere:
            continue
        ex, ey = px + sens * fx * largeur_corps, py + fy * haut_corps
        if genre == "miette":                           # un petit biscuit : bord brun, cœur doré (diamètre : largeur)
            et = max(3.0, ft * largeur_corps)
            b = max(1.0, et / 8)
            L.append(("ellipse", ex, ey, et / 2, et / 2.3, (74, 38, 18, int(255 * fa))))
            L.append(("ellipse", ex, ey, et / 2 - b, et / 2.3 - b, (246, 196, 92, int(255 * fa))))
            L.append(("ellipse", ex - et / 7, ey - et / 7, et / 7, et / 8, (255, 236, 170, int(255 * fa))))
            continue
        et = max(6.0, ft * haut_corps)
        if genre == "z":
            L.append(("texte", ex, ey, "z", et, (190, 215, 255, int(230 * fa)), True, "c", False))
        elif genre == "coeur":
            L.append(("texte", ex, ey, "♥", et, (255, 95, 140, int(255 * fa)), True, "c", False))
        elif genre == "etincelle":
            L.append(("texte", ex, ey, "✦", et, (255, 226, 120, int(255 * fa)), True, "c", False))


def scene_creature(c, album, vue, regl, zone_l, zone_h, sol, ox=0, t_=0.0, nom=""):
    """(liste de dessin, zones) de la créature du bureau. Coordonnées de la ZONE (bande du bas de l'écran) moins ox
    (la fenêtre tkinter qui se déplace avec la créature) ; sol : la ligne des pieds."""
    L = []
    zones = []
    taille = V.TAILLES.get(regl.get("taille"), 104)
    e = echelle(album, taille)
    an = V.animer(c)
    cad = album.image(an.etat, an.k)
    ref = album.images("assis")[0]
    largeur_corps = ref.w * e
    haut_corps = ref.h * e
    px, py = c.x - ox, sol - c.air + an.dy                 # les pieds, à l'écran
    # ombre au sol (plus petite quand elle est en l'air ou qu'elle saute)
    f = max(0.3, 1 - c.air / 300) * an.ombre
    L.append(("ellipse", c.x - ox, sol + 2, largeur_corps * 0.36 * f, 5 * f, (0, 0, 0, int(70 * f))))
    if an.ancien is not None:                              # l'ancienne pose s'efface pendant la transition
        vieux = album.image(an.ancien[0], an.ancien[1])
        L.append(("imgt", vieux, px, py, e, an.ancien[3], album.lisse, an.sx, an.sy, an.rot, an.ancien[2]))
    # la miette passe DERRIÈRE : la bouche ouverte (fond), la miette, puis la pose trouée à la bouche par-dessus
    if an.fond is not None:
        L.append(("imgt", album.image(an.fond, an.k), px, py, e, an.miroir, album.lisse, an.sx, an.sy, an.rot,
                  an.opacite))
    effets(L, an, px, py, largeur_corps, haut_corps, derriere=True)
    L.append(("imgt", cad, px, py, e, an.miroir, album.lisse, an.sx, an.sy, an.rot, an.opacite))
    effets(L, an, px, py, largeur_corps, haut_corps, derriere=False)
    zones.append((c.x - ox - largeur_corps / 2, sol - c.air - haut_corps, largeur_corps, haut_corps + 6, "creature"))
    haut = py - cad.ay * e * an.sy                          # le haut de l'image
    # petits textes qui montent
    for txt, age, coul in vue.flottants:
        L.append(("texte", c.x - ox + largeur_corps * 0.45, haut + 12 - age * 30, sans_marques(txt), 14,
                  _a(coul, int(255 * max(0.0, 1 - age / 1.6))), True, "g", False))
    vue.boutons = []
    if vue.menu:
        boutons, (cx, cy, r) = V.menu_positions(c.x - ox, sol - c.air - haut_corps / 2, haut_corps, libelles_menu(),
                                                largeur=zone_l, hauteur=zone_h)
        ry = max(150.0, haut_corps * V.RAYON_MENU) * 0.82
        L.append(("arc", cx, cy, r, ry, (255, 255, 255, 26), 1))
        for cle, sym, lib, bx, by, bw, bh in boutons:
            accent = ICONES[cle]
            if cle == "jouer":
                L.append(("rrect", bx - 3, by - 3, bw + 6, bh + 6, (bh + 6) / 2, None, _a(VERT, 70), 3))
            L.append(("rrect", bx, by, bw, bh, bh / 2, FOND, _a(VERT, 200) if cle == "jouer" else BORD, 1))
            L.append(("ellipse", bx + bh / 2 + 2, by + bh / 2, bh / 2 - 6, bh / 2 - 6, _a(accent, 46)))
            L.append(("texte", bx + bh / 2 + 2, by + bh / 2, sym, 10 if len(sym) > 1 else 11, accent, True, "c", True))
            L.append(("texte", bx + bh + 4, by + bh / 2, lib, 14, TEXTE, True, "g", False))
            zones.append((bx, by, bw, bh, "menu:" + cle))
        vue.boutons = boutons
        haut_menu = min(b[4] for b in boutons)
    else:
        haut_menu = haut
    if vue.panneau:
        titre, lignes = vue.panneau
        w = 300
        h = 44 + 34 * len(lignes)
        px = min(max(8, c.x - ox - w / 2), zone_l - w - 8)
        py = max(6, haut_menu - h - 12)
        L.append(("rrect", px, py, w, h, 14, FOND_CARTE, BORD, 1))
        L.append(("texte", px + 16, py + 22, sans_marques(titre), 15, TEXTE, True, "g", False))
        for i, (txt, action) in enumerate(lignes):
            yy = py + 44 + 34 * i
            L.append(("rrect", px + 10, yy, w - 20, 28, 9, (255, 255, 255, 10), None, 0))
            L.append(("texte", px + 22, yy + 14, sans_marques(txt), 13, TEXTE if action else TEXTE_DOUX, False, "g",
                      False))
            if action:
                zones.append((px + 10, yy, w - 20, 28, action))
        zones.append((px, py, w, h, "panneau"))
    elif vue.bulle and t_ < vue.bulle[1] and not vue.menu:
        bx, by, bw, bh = bulle(L, vue.bulle[0], c.x - ox, haut - 2, zone_l=zone_l)
        zones.append((bx, by, bw, bh, "bulle"))
    return L, zones


# ---------------------------------------------------------------- l'île
ILE_L, ILE_H = 900, 380          # la place réservée à l'île ouverte
PILULE_W, PILULE_H = 230, 40


def rect_ile(ouverture, evenement=False):
    """Le rectangle (x, y, w, h) de l'île dans sa fenêtre, de la pilule (0) au panneau (1)."""
    o = max(0.0, min(1.0, ouverture))
    if evenement:
        w = PILULE_W + (420 - PILULE_W) * min(1.0, o / 0.55)
        h = PILULE_H + 4
    else:
        w = PILULE_W + (ILE_L - 20 - PILULE_W) * o
        h = PILULE_H + (ILE_H - 20 - PILULE_H) * o
    return (ILE_L - w) / 2, 6, w, h


def scene_ile(ile, info, album_mini, mini, t_=0.0, pointeur=None, equipe=(), creature=None):
    """(liste de dessin, zones) de l'île. info : {"nom", "faim", "xp", "texte", "titre", "dans_equipe"} ;
    album_mini : l'album de la créature ; mini : le MiniTerminal ; equipe : [(album, couleur d'état)]."""
    L, zones = [], []
    evt = ile.etat == "evenement"
    x, y, w, h = rect_ile(ile.ouverture, evt)
    rayon = min(h / 2, 26) if ile.ouverture < 0.4 or evt else 26
    L.append(("rrect", x, y, w, h, rayon, FOND, _a(ROUGE, 150) if evt else BORD, 1.5 if evt else 1))
    zones.append((x, y, w, h, "ile"))
    etat_mini, msx, msy = V.mini_vie(creature, t_)
    cad = album_mini.image(etat_mini, int(t_ * V.IPS))
    if ile.ouverture < 0.6 or evt:
        # la pilule : la mini-créature qui respire, et 2-3 pastilles d'état
        e = (h - 10) / max(1, album_mini.ref)
        L.append(("imgt", cad, x + 12 + cad.ax * e, y + h - 4, e, False, album_mini.lisse, msx, msy, 0.0, 1.0))
        xx = x + 18 + cad.w * e
        if evt:
            L.append(("texte", xx + 4, y + h / 2, sans_marques(ile.evenement or ""), 14, TEXTE, False, "g", False))
        else:
            for coul, txt in ((ORANGE, t("bur.ile.faim", n=info.get("faim", 0))), (JAUNE, t("bur.ile.xp", n=info.get("xp", 0)))):
                L.append(("ellipse", xx + 5, y + h / 2, 4, 4, coul))
                L.append(("texte", xx + 13, y + h / 2, txt, 13, TEXTE_DOUX, False, "g", False))
                xx += 22 + V.largeur_texte(txt, 13)
            if info.get("nouveau"):
                L.append(("ellipse", x + w - 14, y + 10, 4, 4, VIOLET))
        return L, zones
    a = int(255 * min(1.0, (ile.ouverture - 0.6) / 0.4))
    # fond : des particules de pixels qui s'écartent du pointeur
    for px, py, pa in V.particules(46, w - 20, h - 20, t_, None if pointeur is None else
                                   (pointeur[0] - x - 10, pointeur[1] - y - 10)):
        L.append(("rect", x + 10 + px, y + 10 + py, 2, 2, (61, 220, 132, pa * a // 255 // 3)))
    # en-tête
    for i, sym in enumerate(("⌂", "◌", "+")):
        bx = x + 18 + 40 * i
        if i == 0:
            L.append(("rrect", bx, y + 16, 32, 28, 9, (255, 255, 255, 16), None, 0))
        L.append(("texte", bx + 16, y + 30, sym, 14, _f(TEXTE_DOUX, a), False, "c", False))
    eq = t("bur.ile.equipe", n=info.get("dans_equipe", 1))
    L.append(("ellipse", x + w - 104 - V.largeur_texte(eq, 13), y + 30, 4, 4, _f(VERT, a)))
    L.append(("texte", x + w - 96, y + 30, eq, 13, _f(TEXTE_DOUX, a), False, "d", False))
    L.append(("texte", x + w - 72, y + 30, "⚙", 14, _f(TEXTE_DOUX, a), False, "c", False))
    zones.append((x + w - 84, y + 16, 26, 28, "menu:reglages"))
    L.append(("texte", x + w - 40, y + 30, "×", 16, _f(TEXTE_DOUX, a), False, "c", False))
    zones.append((x + w - 54, y + 16, 28, 28, "ile:fermer"))
    # la carte : la créature qui parle
    cx, cy, cw, ch = x + 20, y + 56, w - 40, 176
    L.append(("rrect", cx, cy, cw, ch, 16, _f(FOND_CARTE, a), _f(BORD, a), 1))
    L.append(("rrect", cx + 18, cy + 22, 124, 124, 18, (255, 255, 255, a // 24), None, 0))
    e = 104 / max(1, album_mini.ref)
    if not album_mini.lisse:
        e = float(max(1, int(104 / album_mini.ref)))
    hop = -abs(math.sin(t_ * 3)) * 4 if ile.etat == "ouverte" else 0
    regarde = pointeur is not None and pointeur[0] < cx + 80            # elle se tourne vers le pointeur
    L.append(("imgt", cad, cx + 80, cy + 138 + hop, e, regarde, album_mini.lisse, msx, msy, 0.0, 1.0))
    zones.append((cx + 18, cy + 22, 124, 124, "ile:creature"))
    tx = cx + 166
    L.append(("ellipse", tx + 4, cy + 34, 4, 4, _f(VERT, a)))
    L.append(("texte", tx + 14, cy + 34, info.get("nom", ""), 14, _f(TEXTE, a), True, "g", False))
    L.append(("texte", tx + 22 + V.largeur_texte(info.get("nom", ""), 14), cy + 34, sans_marques(info.get("titre", "")),
              12, _f(TEXTE_DOUX, a), False, "g", False))
    if mini.sortie:
        lignes = [t("bur.ile.vrai_terminal") if l == "@vrai_terminal" else t("bur.ile.trop_long") if l == "@trop_long"
                  else l for l in mini.sortie][-5:]
        for i, l in enumerate(lignes):
            L.append(("texte", tx, cy + 64 + 21 * i, l[:70], 14, _f(TEXTE, a), False, "g", True))
    else:
        for i, l in enumerate(couper(sans_marques(info.get("texte", "")), cw - 230, 22)[:3]):
            L.append(("texte", tx, cy + 70 + 30 * i, l, 22, _f(TEXTE, a), True, "g", False))
    # les pastilles de l'équipe, à droite
    for i, (alb, coul) in enumerate(list(equipe)[:3]):
        px, py = cx + cw - 56, cy + 14 + 52 * i
        L.append(("rrect", px, py, 42, 42, 10, (255, 255, 255, a // 18), None, 0))
        im = alb.image("assis", 0)
        ee = 34 / max(1, alb.ref) if alb.lisse else float(max(1, int(34 / alb.ref)))
        L.append(("img", im, px + 21 - im.ax * ee, py + 39 - im.ay * ee, ee, False, alb.lisse))
        L.append(("ellipse", px + 38, py + 4, 4, 4, _f(coul, a)))
    # le mini-terminal
    my = cy + ch + 12
    L.append(("rrect", cx, my, cw, 38, 10, (8, 10, 14, a * 9 // 10), _f(BORD, a), 1))
    invite = mini.invite()
    if len(invite) > 34:
        invite = "…" + invite[-33:]
    L.append(("texte", cx + 14, my + 19, invite, 14, _f(BLEU, a), False, "g", True))
    sx = cx + 22 + V.largeur_texte(invite, 14) * 1.04
    L.append(("texte", sx, my + 19, mini.saisie[-60:], 14, _f(TEXTE, a), False, "g", True))
    if int(t_ * 2) % 2 == 0:
        L.append(("rect", sx + V.largeur_texte(mini.saisie[-60:], 14) * 1.04 + 3, my + 10, 8, 18, _f(VERT, a)))
    L.append(("texte", cx + cw - 14, my + 19, t("bur.ile.terminal"), 12, _f(TEXTE_DOUX, a), False, "d", False))
    zones.append((cx, my, cw, 38, "ile:saisie"))
    # les boutons d'action
    by = my + 50
    actions = [("jouer", "▶ " + t("bur.menu.jouer")), ("terminal", ">_ " + t("bur.menu.terminal")),
               ("soccuper", "♥ " + t("bur.ile.nourrir")), ("carte", "◉ " + t("bur.menu.carte")),
               ("reglages", "⚙ " + t("bur.menu.reglages"))]
    bw = (cw - 8 * 4) / 5
    for i, (cle, lib) in enumerate(actions):
        bx = cx + i * (bw + 8)
        L.append(("rrect", bx, by, bw, 36, 9, _f(VERT, a // 6) if cle == "jouer" else (255, 255, 255, a // 30),
                  _f(VERT, a * 3 // 4) if cle == "jouer" else _f(BORD, a), 1))
        L.append(("texte", bx + bw / 2, by + 18, lib, 13, _f(VERT if cle == "jouer" else TEXTE, a), False, "c",
                  False))
        zones.append((bx, by, bw, 36, "menu:" + cle))
    return L, zones


# ---------------------------------------------------------------- capture simulée (PIL : tests, maquettes)
def vers_pil(liste, taille, fond=None, police=None, police_mono=None, image=None, decalage=(0, 0)):
    """Dessine une liste dans une image PIL (RGBA). Sert aux captures simulées (pas d'écran ici) et aux tests :
    les vraies fenêtres (GTK 4, tkinter) dessinent la même liste."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = taille
    img = image if image is not None else Image.new("RGBA", (W, H), fond or (0, 0, 0, 0))
    ox, oy = decalage
    polices = {}

    def p(sz, gras, mono, texte=""):
        ecriture = "cjk" if any(0x2E80 <= ord(ch) <= 0xFFEF for ch in texte) else \
            ("sym" if any(0x2000 <= ord(ch) < 0x2E80 for ch in texte) else "")
        cle = (sz, gras, mono, ecriture)
        if cle not in polices:
            noms = (police_mono or ["DejaVuSansMono.ttf"]) if mono else \
                (police or (["Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"] if gras else ["Inter-Regular.otf", "DejaVuSans.ttf"]))
            if ecriture == "cjk":
                noms = ["NotoSansCJK-Bold.ttc" if gras else "NotoSansCJK-Regular.ttc", "NotoSerifCJK-Bold.ttc"] + noms
            elif ecriture == "sym":
                noms = ["DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf"] + noms
            f = None
            for n in noms:
                try:
                    f = ImageFont.truetype(n, int(sz))
                    break
                except OSError:
                    continue
            polices[cle] = f or ImageFont.load_default()
        return polices[cle]

    def calque():
        return Image.new("RGBA", img.size, (0, 0, 0, 0))

    for op in liste:
        k = op[0]
        if k == "img":
            _, cad, x, y, e, miroir, lisse = op
            im = Image.frombytes("RGBA", (cad.w, cad.h), bytes(cad.rgba))
            if miroir:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            nw, nh = max(1, round(cad.w * e)), max(1, round(cad.h * e))
            im = im.resize((nw, nh), Image.LANCZOS if lisse and e < 1 else Image.BILINEAR if lisse else Image.NEAREST)
            if lisse:
                a = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)
                im.putalpha(a)
            img.alpha_composite(im, (int(round(x + ox)), int(round(y + oy))))
            continue
        if k == "imgt":
            _, cad, ax, ay, e, miroir, lisse, sx, sy, rot, alpha = op
            if alpha <= 0.01:
                continue
            im = Image.frombytes("RGBA", (cad.w, cad.h), bytes(cad.rgba))
            cx_ = cad.ax
            if miroir:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
                cx_ = cad.w - cad.ax
            ex, ey = e * sx, e * sy
            # tout le calcul à la taille de l'écran : déformation continue, rééchantillonnée une seule fois
            nw, nh = max(1, round(cad.w * ex)), max(1, round(cad.h * ey))
            im = im.resize((nw, nh), Image.LANCZOS if lisse and ex < 1 else Image.BILINEAR if lisse else Image.NEAREST)
            pax, pay = cx_ * ex, cad.ay * ey                     # les pieds dans l'image redimensionnée
            if abs(rot) > 0.05:
                marge = int(max(nw, nh) * 0.3) + 2
                grand = Image.new("RGBA", (nw + 2 * marge, nh + 2 * marge))
                grand.paste(im, (marge, marge))
                im = grand.rotate(rot, resample=Image.BICUBIC if lisse else Image.NEAREST,
                                  center=(pax + marge, pay + marge))
                pax, pay = pax + marge, pay + marge
            a = im.getchannel("A")
            a = a.point(lambda v: (255 if v > 110 else 0) if lisse else v)
            if alpha < 1:
                a = a.point(lambda v: int(v * alpha))
            im.putalpha(a)
            img.alpha_composite(im, (int(round(ax + ox - pax)), int(round(ay + oy - pay))))
            continue
        c = calque()
        d = ImageDraw.Draw(c)
        if k == "rrect":
            _, x, y, w, h, r, f, b, ep = op
            d.rounded_rectangle((x + ox, y + oy, x + ox + w, y + oy + h), radius=r, fill=f,
                                outline=b, width=max(1, int(round(ep))) if b else 0)
        elif k == "ellipse":
            _, cx, cy, rx, ry, f = op
            d.ellipse((cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry), fill=f)
        elif k == "arc":
            _, cx, cy, rx, ry, coul, ep = op
            for i in range(0, 360, 6):
                d.arc((cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry), i, i + 3, fill=coul, width=ep)
        elif k == "rect":
            _, x, y, w, h, coul = op
            d.rectangle((x + ox, y + oy, x + ox + w - 1, y + oy + h - 1), fill=coul)
        elif k == "texte":
            _, x, y, texte, sz, coul, gras, ancre, mono = op
            d.text((x + ox, y + oy), texte, font=p(sz, gras, mono, texte), fill=coul,
                   anchor={"g": "lm", "c": "mm", "d": "rm"}[ancre])
        img.alpha_composite(c)
    return img
