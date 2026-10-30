"""Animations procédurales pour tout le bestiaire (150 espèces × 5 stades × variantes).

Chaque stade n'a qu'une image fixe : on l'anime au moment de l'affichage, sans rien pré-calculer.
L'image est posée (pieds au sol) sur une toile un peu plus grande, puis déformée (écrasement,
étirement, inclinaison, bascule, saut), recolorée (sommeil, colère, K.O., flash) et décorée
d'effets en gros pixels (pomme, étoiles, cœurs, bulle, « z Z », spirales, tête de mort…).

Tout le calcul est en entiers (tables, tramage de Bayer, générateur pseudo-aléatoire maison) pour
que le portage Kotlin (app/…/AnimAuto.kt) donne exactement les mêmes images.

Démo (depuis pc/) : python3 -m tg.anim_auto braisillon adulte content [shiny]
"""
import sys
import time

from . import bestiaire as B
from . import vie

ANIMS = ["statique", "mange", "attaque", "salut", "parle", "dort", "content", "affame", "confus", "colere",
         "victoire", "ko", "evolution"]
IPS = 8                                   # images par seconde (comme le lecteur de tg anime)

BAYER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
# Couleurs ajoutées en fin de palette pour les effets (jamais touchées par le shiny)
CODES = "WKYORPBCVGMSD"
SPECIAUX = (0xFFFFFF,  # W blanc
            0x1B1B25,  # K noir (contours, orbites)
            0xFFD83A,  # Y jaune étoile
            0xFF9A1F,  # O orange
            0xE8333C,  # R rouge (colère, pomme)
            0xFF6B9D,  # P rose cœur
            0x8FC4FF,  # B bleu zzz
            0x4FC3F7,  # C goutte
            0xC58CFF,  # V violet spirale
            0x5CBF4A,  # G vert feuille
            0x8A5A2B,  # M marron queue
            0xD9D6CC,  # S os / vapeur
            0x2D3A6E)  # D bleu nuit

GLYPHES = {
    "pomme": ["...M...",
              "...MGG.",
              ".RRMRR.",
              "RRWRRRR",
              "RWRRRRR",
              "RRRRRRR",
              ".RRRRR."],
    "pomme1": ["...M...",
               "...MGG.",
               "..RMRR.",
               "...RRRR",
               "...RRRR",
               "..RRRRR",
               ".RRRRR."],
    "pomme2": ["...M...",
               "...MGG.",
               "...MRR.",
               "....RRR",
               "....RRR",
               "....RRR",
               "...RRR."],
    "trognon": ["...M...",
                "..RMR..",
                "...S...",
                "...S...",
                "...S...",
                "..RRR..",
                "...R..."],
    "etoile": ["...Y...",
               "...Y...",
               "..YYY..",
               "YYYWYYY",
               ".YYYYY.",
               "..YYY..",
               ".YY.YY.",
               ".Y...Y."],
    "etincelle": ["..W..",
                  "..Y..",
                  "WYYYW",
                  "..Y..",
                  "..W.."],
    "point": [".Y.",
              "YWY",
              ".Y."],
    "coeur": [".PP.PP.",
              "PWPPPPP",
              "PPPPPPP",
              ".PPPPP.",
              "..PPP..",
              "...P..."],
    "petit_coeur": [".P.P.",
                    "PPPPP",
                    "PPPPP",
                    ".PPP.",
                    "..P.."],
    "z": ["BBBB",
          "..B.",
          ".B..",
          "BBBB"],
    "Z": ["BBBBB",
          "...B.",
          "..B..",
          ".B...",
          "BBBBB"],
    "colere": ["...R.R...",
               "...R.R...",
               "..RR.RR..",
               "RRR...RRR",
               ".........",
               "RRR...RRR",
               "..RR.RR..",
               "...R.R...",
               "...R.R..."],
    "spirale": ["..VVVVV..",
                ".V.....V.",
                "V..VVV..V",
                "V.V...V.V",
                "V.V.W.V.V",
                "V.V..V..V",
                "V..VV..V.",
                ".V....V..",
                "..VVVV..."],
    "goutte": [".C.",
               ".C.",
               "CCC",
               "CWC",
               ".C."],
    "vague": [".YY..",
              "Y..YY"],
    "vapeur": [".S.",
               "SSS",
               ".S."],
    "crane": ["....WWWWW....",
              "..WWWWWWWWW..",
              ".WWWWWWWWWWW.",
              "WWWWWWWWWWWWW",
              "WWWWWWWWWWWWW",
              "WWRKRWWWRKRWW",
              "WWKRKWWWKRKWW",
              "WWRKRWWWRKRWW",
              ".WWWWWKWWWWW.",
              "..WWWKKKWWW..",
              "...WWWWWWW...",
              "...WKWKWKW...",
              "...WWWWWWW..."],
    "os": ["SW.............WS",
           "WWW...........WWW",
           "..WWW.......WWW..",
           "....WWW...WWW....",
           "......WWWWW......",
           "....WWW...WWW....",
           "..WWW.......WWW..",
           "WWW...........WWW",
           "SW.............WS"],
}


# ---------------------------------------------------------------- couleurs (entiers 0xRRGGBB)
def _hex(c):
    return "#%06x" % c


def _int(h):
    return int(h.lstrip("#")[:6], 16)


def _sombre(c):
    r, g, b = c >> 16 & 255, c >> 8 & 255, c & 255
    return (r * 50 // 100) << 16 | (g * 55 // 100) << 8 | min(255, b * 70 // 100 + 24)


def _gris(c):
    r, g, b = c >> 16 & 255, c >> 8 & 255, c & 255
    l = (r * 30 + g * 59 + b * 11) // 100 * 75 // 100 + 60
    return l << 16 | l << 8 | min(255, l + 14)


def _rouge(c):
    r, g, b = c >> 16 & 255, c >> 8 & 255, c & 255
    return ((r + 3 * 235) // 4) << 16 | (g * 40 // 100) << 8 | (b * 35 // 100)


# ---------------------------------------------------------------- outils
class _Hasard:
    """Générateur congruentiel (identique côté Kotlin)."""
    def __init__(self, graine):
        self.s = graine & 0x7FFFFFFF

    def n(self, k):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.s >> 8) % k


def _dim(n, pct):
    return max(1, (n * pct + 50) // 100)


def _rogner(w, h, o):
    """Coupe les bords transparents (les effets se placent sur la vraie silhouette)."""
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if o[y * w + x]:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    if x1 < 0:
        return 1, 1, bytes(1)
    nw, nh = x1 - x0 + 1, y1 - y0 + 1
    return nw, nh, bytes(o[(y0 + y) * w + x0 + x] for y in range(nh) for x in range(nw))


class _Toile:
    def __init__(self, w, h, sp):
        self.w, self.h, self.sp = w, h, sp
        self.px = bytearray(w * h)

    def c(self, code):
        return self.sp + 1 + CODES.index(code)

    def pt(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = v

    def glyphe(self, nom, x, y, quart=0, contour=True, ech=1):
        """Dessine un motif (tourné de quart × 90°, agrandi ech fois), cerné de noir si contour."""
        g = GLYPHES[nom]
        gh, gw = len(g), len(g[0])
        for passe in ((0, 1) if contour else (1,)):
            for r in range(gh):
                for q in range(gw):
                    ch = g[r][q]
                    if ch == ".":
                        continue
                    if quart == 1:
                        X, Y = gh - 1 - r, q
                    elif quart == 2:
                        X, Y = gw - 1 - q, gh - 1 - r
                    elif quart == 3:
                        X, Y = r, gw - 1 - q
                    else:
                        X, Y = q, r
                    for ey in range(-1, ech + 1) if passe == 0 else range(ech):
                        for ex in range(-1, ech + 1) if passe == 0 else range(ech):
                            self.pt(x + X * ech + ex, y + Y * ech + ey, self.c("K" if passe == 0 else ch))

    def sprite(self, spr, cx, base, nw, nh, dx=0, dy=0, pench=0, off=0, alt=0, mix=0, blanc=0, rot=0, sil=0,
               trame=0):
        """Pose le sprite redimensionné (nw×nh, échantillonnage au centre des pixels), pieds en (cx, base).
        pench : inclinaison (décalage du haut en % de la hauteur) ; rot 1 = couché (haut vers la droite),
        rot 2 = à l'envers ; off/alt/mix : palette de base ou variante, mélangées par tramage ;
        blanc : part de pixels blanchis (0..16) ; sil : silhouette d'une seule couleur ;
        trame > 0 : ne dessine que les pixels où Bayer < trame, < 0 : que ceux où Bayer >= -trame."""
        w, h, o = spr
        dw, dh = (nh, nw) if rot == 1 else (nw, nh)
        x0, y0 = cx - dw // 2 + dx, base - dh + dy
        blanc_i = self.c("W")
        for j in range(dh):
            y = y0 + j
            if y < 0 or y >= self.h:
                continue
            dec = (pench * (dh - 1 - j)) // 100
            for i in range(dw):
                x = x0 + i + dec
                if x < 0 or x >= self.w:
                    continue
                if rot == 1:
                    u, v = j, nh - 1 - i
                elif rot == 2:
                    u, v = i, nh - 1 - j
                else:
                    u, v = i, j
                val = o[((2 * v + 1) * h) // (2 * nh) * w + ((2 * u + 1) * w) // (2 * nw)]
                if not val:
                    continue
                b = BAYER[(y & 3) * 4 + (x & 3)]
                if (trame > 0 and b >= trame) or (trame < 0 and b < -trame):
                    continue
                if sil:
                    val = sil
                else:
                    val += alt if b < mix else off
                if b < blanc:
                    val = blanc_i
                self.px[y * self.w + x] = val


def _eclat(t, x, y, L, creux=False):
    """Éclat d'impact : 8 rayons blanc → jaune → orange."""
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    for k in range(8):
        ux, uy = dirs[k]
        n = L if k < 4 else (L * 2) // 3
        for r in range(1, n + 1):
            if creux and r <= n // 2:
                continue
            t.pt(x + ux * r, y + uy * r, t.c("W" if r <= n // 3 else ("Y" if r < n else "O")))
    if not creux:
        t.pt(x, y, t.c("W"))


def _bulle(t, x, y, points, e=1):
    """Bulle de dialogue 14×8 (agrandie e fois) avec 0 à 3 points."""
    def pb(i, j, code):
        for b in range(e):
            for a in range(e):
                t.pt(x + i * e + a, y + j * e + b, t.c(code))
    for j in range(6):
        for i in range(14):
            if (j == 0 or j == 5) and (i == 0 or i == 13):
                continue
            bord = j == 0 or j == 5 or i == 0 or i == 13
            pb(i, j, "K" if bord else "W")
    for k in range(points):
        for a in range(2):
            for b in range(2):
                pb(2 + 4 * k + a, 2 + b, "K")
    pb(3, 5, "W")
    pb(2, 6, "K")
    pb(3, 6, "W")
    pb(4, 6, "K")
    pb(1, 7, "K")
    pb(2, 7, "K")


# ---------------------------------------------------------------- les animations
class _Ctx:
    def __init__(self, spr, W, H, sp):
        self.spr = spr
        self.w, self.h = spr[0], spr[1]
        self.W, self.H, self.sp = W, H, sp
        self.cx, self.base = W // 2, H - 2
        self.top = self.base - self.h
        self.left = self.cx - self.w // 2
        self.right = self.left + self.w
        self.e = 2 if max(self.w, self.h) >= 40 else 1     # gros symboles pour les grands stades
        self.frames = []

    def toile(self):
        return _Toile(self.W, self.H, self.sp)

    def pose(self, t, sx=100, sy=100, **kw):
        t.sprite(self.spr, self.cx, self.base, _dim(self.w, sx), _dim(self.h, sy), **kw)

    def garder(self, t):
        self.frames.append(bytes(t.px))


def _statique(c):
    """Au repos : la vie dans la créature (vie.py : yeux qui clignent, haut du corps qui respire, parties fines qui
    ondulent, petits regards), 64 images ; si rien n'est sûr sur cette image, l'écrasement doux d'avant (8 images)."""
    a = vie.analyse_gardee(c.w, c.h, c.spr[2], c.pal)
    if a is not None:
        for k in range(vie.CYCLE):
            W2, H2, img = vie.image(a, k)
            t = c.toile()
            t.sprite((W2, H2, img), c.cx, c.base, W2, H2)
            c.garder(t)
        return
    sy = (100, 99, 97, 96, 96, 97, 99, 100)
    sx = (100, 100, 101, 102, 102, 101, 100, 100)
    for f in range(8):
        t = c.toile()
        c.pose(t, sx[f], sy[f])
        c.garder(t)


def _miettes(t, x, y, debut, f):
    a = f - debut
    if a < 0 or a > 3:
        return
    r = _Hasard(debut * 31 + 7)
    for _ in range(6):
        px, py = x + r.n(5) - 2, y + r.n(4) - 1
        vx = r.n(5) - 2
        col = "RSW"[r.n(3)]
        t.pt(px + vx * a, py + a * (a + 1) // 2 + a, t.c(col))


def _mange(c):
    ax = c.right - 2
    ay = c.top + c.h * 40 // 100 - 3
    sx0, sy0 = c.W - 8, max(0, c.top - 8)
    vol = (0, 35, 70, 100)
    arc = (0, 3, 2, 0)
    croc = {4: "pomme1", 6: "pomme2", 8: "trognon"}
    pench = (0, 0, 4, 8, 12, 6, 12, 6, 12, 4, 0, 0)
    sx = (100, 100, 100, 101, 104, 100, 104, 100, 104, 100, 100, 101)
    sy = (100, 100, 100, 99, 94, 100, 94, 100, 94, 100, 97, 100)
    dx = (0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0)
    for f in range(12):
        t = c.toile()
        c.pose(t, sx[f], sy[f], dx=dx[f], pench=pench[f])
        if f < 4:
            x = sx0 + (ax - sx0) * vol[f] // 100
            y = sy0 + (ay - sy0) * vol[f] // 100 - arc[f]
            t.glyphe("pomme", x, y)
        elif f < 9:
            g = croc.get(f) or croc.get(f - 1)
            t.glyphe(g, ax, ay)
        elif f == 9:
            t.glyphe("trognon", ax, ay + 3)
        for d in (4, 6, 8):
            _miettes(t, ax + 2, ay + 4, d, f)
        if f >= 10:
            t.glyphe("point", c.right, c.top - 3 - (f - 10) * 2)
        c.garder(t)


def _attaque(c):
    elan = max(4, c.w // 5)
    p = (0, -25, -60, -80, 70, 100, 90, 60, 30, 10)
    sx = (100, 104, 108, 110, 112, 104, 100, 100, 100, 100)
    sy = (100, 97, 94, 92, 94, 100, 102, 100, 100, 100)
    pench = (0, -5, -10, -12, 15, 10, 0, 0, 0, 0)
    secousse = (0, 0, 0, 0, 0, -1, 1, 0, 0, 0)
    L = max(4, c.h // 5)
    for f in range(10):
        t = c.toile()
        dx = (elan * p[f]) // 100
        c.pose(t, sx[f], sy[f], dx=dx, dy=secousse[f], pench=pench[f])
        ex, ey = min(c.right + dx + L // 2 + 1, c.W - 2 - L), c.top + c.h // 2
        if f == 4:
            for k in range(3):
                t.pt(c.left + dx - 2 - 3 * k, c.top + c.h // 3 + 3 * k, t.c("S"))
                t.pt(c.left + dx - 3 - 3 * k, c.top + c.h // 3 + 3 * k, t.c("S"))
        if f == 5:
            _eclat(t, ex, ey, L * 2 // 3)
        elif f == 6:
            _eclat(t, ex, ey, L)
        elif f == 7:
            _eclat(t, ex, ey, L + 1, creux=True)
        c.garder(t)


def _salut(c):
    saut = max(3, c.h // 6)
    p = (0, 0, 40, 80, 100, 80, 40, 0, 0, 0)
    sy = (100, 92, 104, 104, 100, 104, 104, 94, 100, 100)
    sx = (100, 106, 97, 97, 100, 97, 97, 106, 100, 100)
    for f in range(10):
        t = c.toile()
        c.pose(t, sx[f], sy[f], dy=-(saut * p[f] // 100))
        if 3 <= f <= 8:
            t.glyphe("etoile", c.right - 3, c.top - 10 - (f - 3))
            if f % 2:
                t.glyphe("point", c.right + 4, c.top - 6 - (f - 3))
        elif f == 9:
            t.glyphe("etincelle", c.right - 2, c.top - 16)
        c.garder(t)


def _parle(c):
    points = (1, 1, 2, 2, 3, 3, 3, 0, 3, 0, 3, 3)
    sy = (100, 97, 100, 97, 100, 97, 100, 100, 100, 100, 97, 100)
    bx = min(c.W - 1 - 14 * c.e, c.right - 3 * c.e)
    by = max(0, c.top - 10 * c.e)
    for f in range(12):
        t = c.toile()
        c.pose(t, 100, sy[f])
        _bulle(t, bx, by, points[f], c.e)
        c.garder(t)


def _dort(c):
    sy = (90, 90, 89, 88, 88, 87, 87, 88, 88, 89, 90, 90)
    sx = (105, 105, 105, 106, 106, 107, 107, 106, 106, 105, 105, 105)
    n = c.sp // 2
    for f in range(12):
        t = c.toile()
        c.pose(t, sx[f], sy[f], off=n)
        haut = c.base - _dim(c.h, sy[f])
        for i in range(3):
            p = (f + 4 * i) % 12
            if p > 10:
                continue
            x = c.right - 3 + p // 2 + (i % 2)
            y = haut - 3 - p
            if p < 5:
                t.glyphe("z", x, y)
            else:
                t.glyphe("Z", x, y - 1)
        c.garder(t)


def _content(c):
    saut = max(3, c.h // 4)
    b = (0, 55, 90, 90, 55, 0, 0, 55, 90, 90, 55, 0)
    sy = (92, 104, 100, 100, 104, 94, 92, 104, 100, 100, 104, 94)
    sx = (108, 96, 100, 100, 96, 106, 108, 96, 100, 100, 96, 106)
    houle = (0, 1, 1, 0, -1, -1)
    for f in range(12):
        t = c.toile()
        c.pose(t, sx[f], sy[f], dy=-(saut * b[f] // 100))
        for i in range(3):
            p = (f + 4 * i) % 12
            if p > 9:
                continue
            x = c.left - 3 + (i * (c.w + 2)) // 2 + houle[p % 6]
            y = c.top - 4 - p
            t.glyphe("coeur" if p < 6 else "petit_coeur", x, y)
        c.garder(t)


def _affame(c):
    tremble = (0, 1, 0, -1)
    sy = (98, 97, 98, 97, 98, 97, 98, 97, 98, 97, 98, 97)
    for f in range(12):
        t = c.toile()
        gargouille = f % 4 >= 2
        c.pose(t, 103 if gargouille else 100, sy[f], dx=tremble[f % 4])
        p = f % 6
        t.glyphe("goutte", c.left - 2, c.top + 1 + p)
        q = (f + 3) % 6
        t.glyphe("goutte", c.right - 1, c.top + q)
        if gargouille:
            yb = c.top + c.h * 65 // 100
            t.glyphe("vague", c.right + 2, yb, contour=False)
            t.glyphe("vague", c.right + 3 + (f % 2), yb + 3, contour=False)
        c.garder(t)


def _confus(c):
    pench = (0, 8, 14, 16, 14, 8, 0, -8, -14, -16, -14, -8)
    for f in range(12):
        t = c.toile()
        c.pose(t, pench=pench[f])
        hx = c.cx + (pench[f] * c.h) // 100
        e = c.e
        y = max(1, c.top - 11 * e)
        t.glyphe("spirale", hx - 11 * e, y + (f % 2) * e, quart=f % 4, ech=e)
        t.glyphe("spirale", hx + 2 * e, y + (1 - f % 2) * e, quart=(f + 2) % 4, ech=e)
        c.garder(t)


def _colere(c):
    mix = (10, 16, 16, 16, 16, 12, 16, 16, 16, 16)
    dx = (0, 2, -2, 1, -1, 2, -2, 1, -1, 0)
    dy = (0, 0, 1, 0, 1, 0, 0, 1, 0, 0)
    sy = (100, 102, 103, 103, 102, 103, 103, 102, 101, 100)
    n = c.sp // 2
    for f in range(10):
        t = c.toile()
        c.pose(t, 100, sy[f], dx=dx[f], dy=dy[f], alt=n, mix=mix[f])
        if f % 5 != 4:
            g = c.e if f % 2 else 0
            t.glyphe("colere", c.right - 5 * c.e - g, max(1, c.top - 7 * c.e) - g, ech=c.e)
        p = f % 5
        t.glyphe("vapeur", c.left - 1 - p // 2, c.top - 1 - p, contour=False)
        q = (f + 2) % 5
        t.glyphe("vapeur", c.left + 2 - q // 2, c.top - 3 - q, contour=False)
        c.garder(t)


def _victoire(c):
    saut = max(5, (c.top * 2) // 3)
    p = (0, 0, 45, 75, 95, 100, 95, 75, 45, 0, 0, 0, 0, 0)
    sy = (100, 88, 108, 106, 104, 100, 100, 104, 106, 90, 96, 100, 100, 100)
    sx = (100, 110, 94, 96, 98, 100, 100, 98, 96, 110, 104, 100, 100, 100)
    places = ((c.left - 8, c.top + c.h // 4), (c.right + 1, c.top + c.h // 5), (c.left - 4, c.top - 6),
              (c.right - 3, c.top - 9), (c.cx - 3, c.top - 14), (c.left - 9, c.top + c.h // 2),
              (c.right + 2, c.top + c.h // 2))
    for f in range(14):
        t = c.toile()
        for k in range(len(places)):
            if f < 3 + k // 2:
                continue
            x, y = places[k]
            ph = (f + 2 * k) % 4
            if ph == 0:
                t.glyphe("etoile", x, y)
            elif ph == 1 or ph == 3:
                t.glyphe("etincelle", x + 1, y + 1)
            else:
                t.glyphe("point", x + 2, y + 2)
        c.pose(t, sx[f], sy[f], dy=-(saut * p[f] // 100))
        c.garder(t)


def _ko(c):
    n = c.sp // 2
    couche = c.h >= c.w
    for f in range(16):
        t = c.toile()
        kw = {"alt": n}
        if f == 0:
            c.pose(t, 108, 92, dx=-1, blanc=8)
        elif f <= 3:
            kw["mix"] = 4 * f
            if couche:
                c.pose(t, pench=(15, 35, 60)[f - 1], **kw)
            else:
                c.pose(t, 100, (70, 35, 35)[f - 1], rot=2 if f == 3 else 0, **kw)
        else:
            kw["mix"] = 16
            rebond = -2 if f == 4 else 0
            if couche:
                c.pose(t, rot=1, dy=rebond, **kw)
            else:
                c.pose(t, 100, 80 if f == 4 else 100, rot=2, dy=rebond, **kw)
        if f >= 6:
            haut = c.w if couche else c.h
            e = _ech_crane(max(c.w, c.h))
            flotte = (5, 2, -1, 0, 0, -1, -1, 0, 0, -1)[f - 6] * e
            y = max(1, c.base - haut - 16 * e) + flotte
            if f >= 8:
                t.glyphe("os", c.cx - 8 * e - e // 2, y + 6 * e, ech=e)
            t.glyphe("crane", c.cx - 6 * e - e // 2, y, ech=e)
        c.garder(t)


def _ech_crane(D):
    """La tête de mort est doublée pour les grands stades (adulte, ancien)."""
    return 2 if D >= 40 else 1


def _evolution(c, ancien, n_nouv):
    r = _Hasard(4242)
    t_blanc = c.c_blanc
    ow, oh = ancien[0], ancien[1]
    for f in range(16):
        t = c.toile()
        if f < 4:
            t.sprite(ancien, c.cx, c.base, ow, oh, off=n_nouv, blanc=4 * f)
        elif f < 6:
            k = 104 if f == 4 else 96
            t.sprite(ancien, c.cx, c.base, _dim(ow, k), _dim(oh, k), sil=t_blanc)
        elif f < 10:
            m = 4 * (f - 5)
            tw = ow + (c.w - ow) * m // 16
            th = oh + (c.h - oh) * m // 16
            t.sprite(ancien, c.cx, c.base, max(1, tw), max(1, th), sil=t_blanc, trame=-m)
            nw = c.w + (ow - c.w) * (16 - m) // 16
            nh = c.h + (oh - c.h) * (16 - m) // 16
            t.sprite(c.spr, c.cx, c.base, max(1, nw), max(1, nh), sil=t_blanc, trame=m)
        elif f < 12:
            c.pose(t, sil=t_blanc)
            L = (c.h * 2) // 3 if f == 10 else c.h // 2
            _eclat(t, c.cx, c.base - c.h // 2, L, creux=f == 11)
        else:
            c.pose(t, blanc=4 * (15 - f))
        if f >= 2:
            for _ in range(5):
                x = c.left - 4 + r.n(c.w + 8)
                y = c.top - 4 + r.n(c.h + 4)
                t.glyphe("point" if r.n(2) else "etincelle", x, y)
        c.garder(t)


# ---------------------------------------------------------------- API
def _calculer(w, h, octets, palette, nom, de=None):
    """Cœur du calcul, palettes en entiers : (W, H, images, palette, nb de couleurs « shiny »)."""
    spr = _rogner(w, h, octets)
    pal = list(palette)
    N = len(pal)
    ancien = None
    if nom == "evolution":
        if de is not None:
            ancien = _rogner(de[0], de[1], de[2])
            pal_a = list(de[3])
        else:
            ancien, pal_a = spr, list(pal)
        pal = pal + pal_a
        n_teinte = len(pal)
        lw, lh = max(spr[0], ancien[0]), max(spr[1], ancien[1])
    else:
        if nom == "dort":
            pal = pal + [_sombre(x) for x in pal]
            n_teinte = 2 * N
        elif nom == "colere":
            pal = pal + [_rouge(x) for x in pal]
            n_teinte = N
        elif nom == "ko":
            pal = pal + [_gris(x) for x in pal]
            n_teinte = N
        else:
            n_teinte = N
        lw, lh = spr[0], spr[1]
    sp = len(pal)
    pal = pal + list(SPECIAUX)
    D = max(lw, lh)
    mx = 8 + D // 8
    mt = 12 + D // 4
    if nom == "ko":                       # place pour la tête de mort au-dessus de la bestiole couchée
        mt = max(mt, 16 * _ech_crane(D) + 2 - (lh - min(lw, lh)))
    W = D + 2 * mx
    H = lh + mt + 2
    if H % 2:
        H += 1
    c = _Ctx(spr, W, H, sp)
    c.top = c.base - spr[1]
    c.pal = pal[:N]
    f = {"statique": _statique, "mange": _mange, "attaque": _attaque, "salut": _salut, "parle": _parle,
         "dort": _dort, "content": _content, "affame": _affame, "confus": _confus, "colere": _colere,
         "victoire": _victoire, "ko": _ko}.get(nom)
    if nom == "evolution":
        c.c_blanc = sp + 1
        _evolution(c, ancien, N)
    elif f:
        f(c)
    else:
        raise ValueError(f"animation inconnue : {nom} (au choix : {', '.join(ANIMS)})")
    return W, H, c.frames, pal, n_teinte


def images(w, h, octets, palette, nom, de=None):
    """(largeur_toile, hauteur_toile, [octets par image], palette étendue en "#rrggbb").
    palette : liste de "#rrggbb" ; de : (w, h, octets, palette) du stade précédent (pour « evolution »)."""
    pal = [_int(x) for x in palette]
    if de is not None:
        de = (de[0], de[1], de[2], [_int(x) for x in de[3]])
    W, H, fr, pal, _ = _calculer(w, h, octets, pal, nom, de)
    return W, H, fr, [_hex(x) for x in pal]


def toiles(e, stade, vid, nom, teinte=None):
    """(W, H, [octets par image], palette "#rrggbb" teintée) d'une animation d'une espèce du bestiaire, ou None."""
    img = B.image(e, stade, vid)
    if not img:
        return None
    de = None
    if nom == "evolution" and stade in B.STADES and B.STADES.index(stade) > 0:
        de = B.image(e, B.STADES[B.STADES.index(stade) - 1], vid)
        if de:
            de = (de[0], de[1], de[2], [_int(x) for x in de[3]])
    w, h, o, pal = img
    W, H, fr, pal, n_teinte = _calculer(w, h, o, [_int(x) for x in pal], nom, de)
    pal = [_hex(x) for x in pal]
    if teinte is not None:
        pal = [B.decaler(x, teinte) if k < n_teinte else x for k, x in enumerate(pal)]
    return W, H, fr, pal


class Paresseux:
    """Une liste d'images calculées seulement quand on les montre (et gardées) : les rendus fins coûtent plus cher,
    et une animation en temps réel saute des images plutôt que de tout calculer d'avance."""
    def __init__(self, n, faire):
        self.n, self.faire, self.vu = n, faire, {}

    def __len__(self):
        return self.n

    def __getitem__(self, k):
        if isinstance(k, slice):
            return [self[i] for i in range(*k.indices(self.n))]
        if k < 0:
            k += self.n
        if not 0 <= k < self.n:
            raise IndexError(k)
        if k not in self.vu:
            self.vu[k] = self.faire(k)
        return self.vu[k]

    def __iter__(self):
        return (self[k] for k in range(self.n))


def lignes(e, stade, vid, nom, teinte=None, aura=None, fin=False, eclat=None):
    """(images en lignes de terminal, images par seconde) pour une espèce du bestiaire, ou None.
    Pour « evolution », stade est le stade d'arrivée : on part du stade précédent.
    aura : palier d'aura de rareté (aura.py) qui respire autour de la silhouette, image après image ;
    fin : le rendu le plus fin du terminal (rendu_fin.py : vraie image ou quadrants), calculé image par image ;
    eclat : l'éclat de l'aura selon le soin (aura.eclat), normal si None."""
    r = toiles(e, stade, vid, nom, teinte)
    if r is None:
        return None
    W, H, fr, pal = r
    if fin:                                   # sans les marges vides communes à toutes les images
        from .sprites import _recadrer
        W, H, fr = _recadrer(W, H, fr)
    from . import aura as A
    ec = A.ECLAT_NORMAL if eclat is None else eclat
    if fin:
        from . import rendu_fin
        mode = rendu_fin.mode()
        if mode != "demi":
            return Paresseux(len(fr), lambda k: rendu_fin.lignes(W, H, A.depuis_octets(W, H, fr[k], pal), aura, k,
                                                                 ec, mode)[0]), IPS
    if aura and A.visible(aura, terminal=True):
        return Paresseux(len(fr), lambda k: A.lignes(W, H, A.depuis_octets(W, H, fr[k], pal), aura, k, ec)), IPS
    return [B.lignes_image(W, H, x, pal) for x in fr], IPS


def _demo(args):
    if not args:
        print("usage : python3 -m tg.anim_auto <espèce> [stade] [animation|tout] [shiny]")
        return
    e = B.espece(args[0])
    if not e:
        print(f" Espèce inconnue : {args[0]}")
        return
    stade = args[1] if len(args) > 1 else "adulte"
    quoi = args[2] if len(args) > 2 else "tout"
    teinte = 0.5 if len(args) > 3 else None
    noms = ANIMS if quoi == "tout" else [quoi]
    sys.stdout.write("\033[?25l")
    try:
        for nom in noms:
            r = lignes(e, stade, e["variantes"][0]["id"] if e.get("variantes") else "classique", nom, teinte)
            if r is None:
                print(" Pas d'image pour cette espèce.")
                return
            frames, ips = r
            print(f" {e['nom']} · {stade} · {nom}")
            hh = len(frames[0])
            tours = 1 if nom == "evolution" else 2
            for k in range(tours * len(frames)):
                if k:
                    sys.stdout.write(f"\033[{hh}F")
                sys.stdout.write("\n".join(frames[k % len(frames)]) + "\n")
                sys.stdout.flush()
                time.sleep(1 / ips)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")


if __name__ == "__main__":
    _demo(sys.argv[1:])
