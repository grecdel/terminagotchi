"""Le monde des biomes : les DESSINS en pixels (prismes hexagonaux en relief, objets du décor), sans fenêtre.

Portés du prototype « Monde Terminagotchi » v4 (hexSprite, decoImg) ; même dessin dans MondeDessin.kt (Android) et
site/src/monde_page.js (le site). Chaque dessin est une image RGBA (poses.Cadre) calculée une seule fois puis gardée.
Aucune illustration générée : tout est dessiné ici, pixel par pixel, avec un hasard reproductible (monde_gen.hasard).
"""
import colorsys
import math

from . import monde_gen as G
from .poses import Cadre

HR, HH, HZ = G.HR, G.HH, G.HZ

# kind → (dessus ×3, mur, particularités)
KINDS = {
    "herbe": (("#5aa63a", "#4f9634", "#66b843"), "#6b4a2c", {"grass"}),
    "fleurs": (("#5aa63a", "#4f9634", "#66b843"), "#6b4a2c", {"grass", "flowers"}),
    "sombre": (("#2f6b2c", "#2a6027", "#367a31"), "#5e3f25", {"grass"}),
    "chemin": (("#c9a26a", "#b88f58", "#d4b07a"), "#7b5534", set()),
    "escalier": (("#c9a26a", "#b88f58", "#d4b07a"), "#7b5534", {"steps"}),
    "pont": (("#a8743f", "#9a6a3a", "#b5804a"), "#5a381e", {"planks"}),
    "sable": (("#e6cf8a", "#d9bf78", "#efdb9c"), "#b8945a", set()),
    "eau": (("#2f7fc4", "#2a72b2", "#3a8fd6"), "#1d4a73", {"water"}),
    "neige": (("#eef6ff", "#dbeaf8", "#f8fcff"), "#8fa9c2", set()),
    "glace": (("#a8e1f5", "#94d4ec", "#bdeafa"), "#5f9ab8", {"ice"}),
    "basalte": (("#4a3f4f", "#3f3544", "#554959"), "#2e2531", {"strata"}),
    "cone": (("#5e4646", "#553f40", "#684e4e"), "#4a2c2a", {"strata", "embers"}),
    "cendre": (("#6d6670", "#625b66", "#7a7380"), "#2e2531", {"embers", "strata"}),
    "lave": (("#ff7a1a", "#f25c0f", "#ff9a33"), "#2e2531", {"lava", "strata"}),
    "pierre": (("#8d929a", "#7d828a", "#9ba0a8"), "#5d6168", {"strata"}),
    "gres": (("#d08a4e", "#c27a40", "#dc9a5e"), "#9a5a2e", {"strata"}),
    "nuage": (("#e6defc", "#d9cff7", "#f1ecff"), "#a99be0", {"cloud"}),
    "orage": (("#8f86b8", "#8178ab", "#9d95c4"), "#5f5690", {"cloud", "bolt"}),
    "dalle": (("#4b3a6b", "#43345f", "#544276"), "#251c38", {"flag"}),
    "violette": (("#3d2f52", "#352947", "#47375e"), "#251c38", set()),
    "crypte": (("#2a2040", "#241b38", "#30254a"), "#1b142a", {"flag"}),
    "fleche": (("#3a2d55", "#33284b", "#43345f"), "#2a2140", {"spire"}),
    "metal": (("#8a96a3", "#7f8b98", "#96a2ae"), "#4a525c", {"plate"}),
    "grille": (("#5d6670", "#535b64", "#68717b"), "#3a4149", {"grid"}),
    "rouille": (("#a3562a", "#8f4a24", "#b86a38"), "#5e3018", set()),
    "vase": (("#55702a", "#4b6424", "#617d30"), "#3b4a1c", set()),
    "toxique": (("#8fe03a", "#7fd02c", "#a6f04a"), "#3b4a1c", {"toxic"}),
}
SOLS = tuple(KINDS)
DECORS = ("chene", "cerisier", "sapin", "sapin_neige", "bouleau", "palmier", "fleur:#ff3d5a", "fleur:h200", "rocher",
          "rocher_volc", "galet", "cristal", "champignon", "champi_lum", "champi_tox", "cactus", "buisson", "geyser",
          "braises", "corail", "coquillage", "algues", "bonhomme", "colonne", "paratonnerre", "etoile", "eolienne",
          "tombe", "rune", "engrenage", "tuyau", "neon", "roseau", "bulles", "panneau", "caisse", "parchemin",
          "parchemin_machine")


def hexa(c):
    """« #rrggbb » ou « hNNN » (une teinte) → (r, g, b)."""
    if c.startswith("h"):
        r, g, b = colorsys.hls_to_rgb(int(c[1:]) / 360, .62, .85)
        return int(r * 255), int(g * 255), int(b * 255)
    n = int(c[1:7], 16)
    return n >> 16, (n >> 8) & 255, n & 255


def shade(c, amt):
    r, g, b = c if isinstance(c, tuple) else hexa(c)
    amt = int(amt)
    return (max(0, min(255, r + amt)), max(0, min(255, g + amt)), max(0, min(255, b + amt)))


def _mod(a, b):
    """Le reste comme en JavaScript (du signe de a), pour garder les motifs du prototype."""
    return a % b if a >= 0 else -((-a) % b)


def hex_inside(dx, dy):
    return abs(dy) <= HH and abs(dx) <= HR - abs(dy) * (HR / 2) / HH


def hex_bottom(dx):
    return HH if abs(dx) <= HR / 2 else HH * (HR - abs(dx)) / (HR / 2)


class Pix:
    """Une petite image RGBA où l'on pose des pixels (comme le canvas du prototype)."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.d = bytearray(w * h * 4)

    def px(self, x, y, c, w=1, h=1):
        r, g, b = c if isinstance(c, tuple) else hexa(c)
        a = 255
        x, y = int(math.floor(x)), int(math.floor(y))
        for yy in range(max(0, y), min(self.h, y + int(h))):
            for xx in range(max(0, x), min(self.w, x + int(w))):
                k = 4 * (yy * self.w + xx)
                self.d[k:k + 4] = bytes((r, g, b, a))

    def ombre(self, x, y, a=140):
        """Un pixel sombre à moitié transparent (le contour des formes rondes)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            k = 4 * (y * self.w + x)
            if self.d[k + 3] == 0:
                self.d[k:k + 4] = bytes((20, 30, 15, a))

    def cadre(self, ax, ay, cle):
        return Cadre(self.w, self.h, bytes(self.d), ax, ay, cle)


def blob(g, cx, cy, rx, ry, cols, r):
    cols = [hexa(c) for c in cols]
    for y in range(-ry, ry + 1):
        for x in range(-rx, rx + 1):
            d = (x * x) / (rx * rx) + (y * y) / (ry * ry)
            if d > 1:
                continue
            c = cols[1]
            l_ = (x / rx) * .7 + (y / ry)
            if l_ > .55:
                c = cols[0]
            elif l_ < -.6:
                c = cols[2]
            if d > .82 and l_ > 0:
                c = cols[0]
            if r() < .08:
                c = cols[0 if r() < .5 else 2]
            g.px(cx + x, cy + y, c)
    for y in range(-ry - 1, ry + 2):
        for x in range(-rx - 1, rx + 2):
            d = (x * x) / (rx * rx) + (y * y) / (ry * ry)
            d2 = (x * x) / ((rx + 1) * (rx + 1)) + (y * y) / ((ry + 1) * (ry + 1))
            if d > 1 and d2 <= 1.0:
                g.ombre(cx + x, cy + y)


_SPRITES = {}


def sprite(kind, v, mur, pilier=0):
    """Le prisme hexagonal en relief : dessus texturé, trois faces visibles, pilier éventuel (Cadre, ancre au centre
    du dessus)."""
    cle = f"hex|{kind}|{v}|{mur}|{pilier}"
    s = _SPRITES.get(cle)
    if s:
        return s
    top, wall_, K = KINDS.get(kind, KINDS["herbe"])
    top = [hexa(c) for c in top]
    wall = hexa(wall_)
    W2, cx, cy = HR * 2 + 3, HR + 1.5, HH + 1
    g = Pix(W2, int(math.ceil(HH * 2 + mur + pilier + 3)))
    r = G.hasard(G.hachage(f"{kind}|{v}|{mur}|{pilier}|1"))
    fleurs = [hexa(c) for c in ("#ffffff", "#ffd84a", "#ff6fa8", "#b48cff")]
    for sy in range(g.h):
        for sx in range(g.w):
            x, y = sx, sy
            dx, dy = sx + .5 - cx, sy + .5 - cy
            col = None
            if hex_inside(dx, dy):
                n = r()
                col = top[0]
                if n < .3:
                    col = top[1]
                elif n < .42:
                    col = top[2]
                if "water" in K:
                    b = _mod(x + y * 2 + v * 3, 9)
                    col = top[2] if b < 2 else (top[0] if b < 5 else top[1])
                if "lava" in K:
                    b = _mod(x * 2 - y + v * 5, 8)
                    col = (255, 211, 107) if b < 2 else (top[2] if b < 4 else (top[0] if n < .5 else top[1]))
                    if n < .05:
                        col = (58, 42, 42)
                if "toxic" in K:
                    b = _mod(x * 2 + y + v * 4, 9)
                    col = (217, 255, 138) if b < 2 else (top[0] if b < 5 else top[1])
                if "ice" in K and _mod(x - y * 2 + 40, 11) < 2:
                    col = (255, 255, 255)
                if "planks" in K:
                    col = (90, 56, 30) if x % 4 == 0 else (top[0] if (x // 4) % 2 else top[2])
                if "steps" in K and int(math.floor(dy + HH + .5)) % 4 == 0:
                    col = (138, 106, 64)
                if "flag" in K and (_mod(x + 2 * y, 10) == 0 or _mod(x - 2 * y + 60, 10) == 0):
                    col = shade(top[0], -22)
                if "grid" in K and (_mod(x + 2 * y, 5) == 0 or _mod(x - 2 * y + 60, 5) == 0):
                    col = (54, 61, 69)
                if "plate" in K and _mod(x + 2 * y, 13) == 0:
                    col = (95, 106, 117)
                if "cloud" in K:
                    d = math.hypot(dx / HR, dy / HH)
                    if d > .7 and n < .55:
                        col = (255, 255, 255)
                if "bolt" in K:
                    rx = int(math.floor(dx + .5))
                    if (rx == -1 and -5 < dy < 0) or (rx == 0 and -1 <= dy < 1) or (rx == 1 and 0 <= dy < 4):
                        col = (255, 225, 74)
                if "flowers" in K and n > .93:
                    col = fleurs[int(r() * 4)]
                if "embers" in K and n > .95:
                    col = (255, 122, 26) if n > .975 else (255, 179, 71)
                if "spire" in K:
                    col = shade(col, int(math.floor(-dy * 2 + .5)))
                if kind == "neige" and n > .9:
                    col = (198, 220, 240)
                if kind == "rouille" and n > .9:
                    col = (110, 52, 24)
                if kind == "violette" and n > .97:
                    col = (125, 255, 207)
                edge = not hex_inside(dx + 1.2 * (1 if dx >= 0 else -1), dy) or \
                    not hex_inside(dx, dy + (-1.1 if dy < 0 else 1.1))
                if edge:
                    col = shade(col, 30 if dy < 0 else -24)
            elif abs(dx) <= HR and hex_bottom(dx) < dy <= hex_bottom(dx) + mur:
                face = 0 if dx < -HR / 2 else (2 if dx > HR / 2 else 1)
                depth = dy - hex_bottom(dx)
                col = shade(wall, (14, 0, -26)[face] - min(30, depth * .35))
                if depth < 1.2:
                    col = shade(wall, (40, 26, 6)[face])
                if "strata" in K and int(math.floor(depth + .5)) % HZ == 0 and depth > 2:
                    col = shade(col, -18)
                if "cloud" in K and depth > mur - 3:
                    col = (255, 255, 255)
                if "lava" in K and _mod(int(math.floor(dx + .5)) + int(math.floor(depth * .35 + .5)) + v, 5) == 0:
                    col = (255, 122, 26) if depth < mur * .7 else (194, 65, 12)
                if r() < .06:
                    col = shade(col, -12)
            elif pilier and abs(dx) <= 3 and HH + mur < dy <= HH + mur + pilier:
                col = (93, 102, 112) if dx < -1 else ((44, 50, 56) if dx > 1 else (58, 65, 73))
            if col:
                k = 4 * (sy * g.w + sx)
                g.d[k:k + 4] = bytes((col[0], col[1], col[2], 255))
    s = _SPRITES[cle] = g.cadre(cx, cy, cle)
    return s


_DECOS = {}


def decor(k):
    """Un objet du décor (Cadre, ancre au milieu du bas)."""
    s = _DECOS.get(k)
    if s:
        return s
    r = G.hasard(G.hachage(k))
    px = None

    def S(w, h):
        nonlocal px
        px = Pix(w, h)
        return px
    if k in ("chene", "cerisier"):
        g = S(30, 38)
        g.px(13, 22, "#6b4426", 4, 14)
        g.px(13, 22, "#8a5a33", 1, 14)
        g.px(12, 35, "#5a381e", 6, 2)
        cols = ["#d9659a", "#f28bbb", "#ffc2dc"] if k == "cerisier" else ["#2f7a2a", "#3f9a35", "#6cc24e"]
        blob(g, 15, 14, 12, 11, cols, r)
        blob(g, 9, 18, 6, 5, cols, r)
        blob(g, 21, 18, 6, 5, cols, r)
        if k == "cerisier":
            for _ in range(8):
                g.px(5 + int(r() * 20), 6 + int(r() * 14), "#ffffff")
    elif k in ("sapin", "sapin_neige"):
        g = S(24, 40)
        g.px(10, 30, "#6b4426", 4, 9)
        for L in range(4):
            top_, hgt, wb = 2 + L * 7, 12, 4 + L * 2
            for y in range(hgt):
                w = int(math.floor((y / hgt) * wb + .5)) + 1
                for x in range(-w, w + 1):
                    col = "#1f5a2a" if x < -w / 3 else ("#14421f" if x > w / 3 else "#2a7035")
                    if y == hgt - 1:
                        col = "#123a1b"
                    if r() < .07:
                        col = "#3f8a45"
                    if k == "sapin_neige" and (y < 3 or (y == hgt - 2 and r() < .6)):
                        col = "#ffffff" if x < 0 else "#dbeaf8"
                    g.px(12 + x, top_ + y, col)
    elif k == "bouleau":
        g = S(26, 40)
        g.px(11, 18, "#eeeeea", 4, 21)
        for _ in range(6):
            g.px(11 + int(r() * 3), 20 + int(r() * 18), "#2a2a2a", 2, 1)
        g.px(10, 38, "#5a381e", 6, 2)
        blob(g, 13, 12, 10, 10, ["#5c9a2a", "#80c03c", "#b5e46a"], r)
    elif k == "palmier":
        g = S(32, 40)
        for y in range(24):
            g.px(15 + int(round(math.sin(y / 7) * 2)), 14 + y, "#9a6a3a" if y % 3 else "#7a4f28", 3, 1)
        for dx, dy in ((-12, 4), (12, 4), (-9, -3), (9, -3), (0, -6), (-13, 9), (13, 9)):
            tt = 0.0
            while tt <= 1:
                x = 16 + dx * tt
                y = 13 + dy * tt + math.sin(tt * 3) * 3 * (1 if dx else 0)
                g.px(int(round(x)), int(round(y)), "#2f8a2a" if tt > .7 else "#3fae35", 2, 2)
                tt += .08
    elif k.startswith("fleur:"):
        col = k[6:]
        g = S(20, 16)
        for x, y in ((5, 8), (11, 5), (15, 10), (9, 11)):
            g.px(x, y + 1, "#2f7a2a", 1, 4)
            g.px(x + 1, y + 3, "#3f9a35")
            for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                g.px(x + a, y + b, col)
            g.px(x, y, "#ffe066")
    elif k in ("rocher", "rocher_volc"):
        g = S(26, 20)
        if k == "rocher":
            blob(g, 13, 11, 11, 7, ["#5d6168", "#8d929a", "#c3c7cc"], r)
            g.px(8, 9, "#4a4d52", 3, 1)
            g.px(15, 12, "#4a4d52", 4, 1)
        else:
            blob(g, 13, 11, 11, 7, ["#211a24", "#3f3544", "#5c4f62"], r)
            g.px(8, 9, "#ff7a1a", 3, 1)
            g.px(10, 10, "#ff7a1a", 1, 2)
            g.px(15, 12, "#ffb347", 4, 1)
            g.px(18, 11, "#ff7a1a", 1, 1)
    elif k == "galet":
        g = S(22, 12)
        blob(g, 6, 7, 4, 3, ["#6d7178", "#9ba0a8", "#d0d3d7"], r)
        blob(g, 14, 6, 5, 3, ["#6d7178", "#a7abb2", "#d8dbdf"], r)
        blob(g, 11, 9, 3, 2, ["#6d7178", "#9ba0a8", "#d0d3d7"], r)
    elif k == "cristal":
        g = S(22, 30)
        for x, y, w, h in ((11, 2, 4, 26), (6, 10, 3, 18), (16, 8, 3, 20)):
            for i in range(h):
                ww = min(w, int(math.ceil(i / 2)) + 1)
                g.px(x - ww + 1, y + i, "#3fb8e8", ww, 1)
                g.px(x + 1, y + i, "#1f7fb0", ww, 1)
                g.px(x, y + i, "#c9f4ff")
    elif k in ("champignon", "champi_lum", "champi_tox"):
        g = S(18, 18)
        g.px(7, 10, "#f3e7d0", 4, 7)
        g.px(10, 10, "#d8c9ad", 1, 7)
        cols = {"champignon": ["#a3141e", "#e0303a", "#ff6a6a"], "champi_lum": ["#1f8f8a", "#3fe0d0", "#b9fff4"],
                "champi_tox": ["#5a1f80", "#8a3fc0", "#c48aff"]}[k]
        blob(g, 9, 8, 7, 4, cols, r)
        dot = "#b6ff4a" if k == "champi_tox" else "#ffffff"
        g.px(5, 7, dot, 2, 1)
        g.px(10, 5, dot, 2, 2)
        g.px(13, 8, dot)
    elif k == "cactus":
        g = S(20, 30)
        for a in ((8, 4, "#3f9a35", 5, 25), (9, 4, "#6cc24e", 1, 25), (3, 12, "#3f9a35", 3, 8), (3, 17, "#3f9a35", 6, 3),
                  (14, 9, "#3f9a35", 3, 9), (11, 15, "#3f9a35", 4, 3), (10, 3, "#ff6fa8", 2, 2)):
            g.px(*a)
    elif k == "buisson":
        g = S(24, 16)
        blob(g, 12, 9, 10, 6, ["#2f7a2a", "#3f9a35", "#6cc24e"], r)
    elif k == "geyser":
        g = S(24, 26)
        blob(g, 12, 20, 10, 5, ["#211a24", "#3f3544", "#5c4f62"], r)
        g.px(9, 15, "#3f3544", 7, 3)
        g.px(10, 14, "#ff7a1a", 5, 2)
        g.px(11, 13, "#ffd36b", 3, 1)
    elif k == "braises":
        g = S(20, 12)
        blob(g, 10, 7, 8, 3, ["#211a24", "#3f3544", "#554959"], r)
        for _ in range(7):
            g.px(4 + int(r() * 12), 5 + int(r() * 4), "#ff7a1a" if r() < .5 else "#ffd36b")
    elif k == "corail":
        g = S(22, 24)
        cc = ["#ff6f91", "#ff8fab", "#ffb3c6"]
        for x, h in ((6, 14), (11, 20), (16, 12)):
            for y in range(h):
                g.px(x + int(round(math.sin(y / 3))), 23 - y, cc[y % 3], 2, 1)
            g.px(x - 2, 23 - h + 4, cc[0], 2, 1)
            g.px(x + 2, 23 - h + 7, cc[1], 2, 1)
    elif k == "coquillage":
        g = S(16, 12)
        for i in range(5):
            g.px(4 + i * 2 - (1 if i > 2 else 0), 2 + abs(2 - i), "#ffe3c2", 2, 8 - abs(2 - i) * 2)
        g.px(3, 9, "#e8b98a", 10, 2)
        for i in range(4):
            g.px(5 + i * 2, 4, "#e8b98a", 1, 5)
    elif k == "algues":
        g = S(18, 24)
        for x, h, c2 in ((4, 18, "#2f9a5a"), (9, 22, "#3fbf6a"), (14, 15, "#2a7a4a")):
            for y in range(h):
                g.px(x + int(round(math.sin(y / 3 + x) * 1.5)), 23 - y, c2, 2, 1)
    elif k == "bonhomme":
        g = S(20, 30)
        blob(g, 10, 22, 7, 6, ["#b9cde0", "#e9f4ff", "#ffffff"], r)
        blob(g, 10, 11, 5, 5, ["#b9cde0", "#e9f4ff", "#ffffff"], r)
        for a in ((8, 9, "#222222"), (12, 9, "#222222"), (10, 11, "#ff8a3d", 3, 1), (6, 3, "#2b2b2b", 9, 2),
                  (8, 0, "#2b2b2b", 5, 3), (9, 19, "#222222"), (9, 22, "#222222")):
            g.px(*a)
    elif k == "colonne":
        g = S(18, 32)
        for a in ((4, 28, "#b8945a", 10, 3), (5, 8, "#efdb9c", 8, 20), (5, 8, "#f7e9b8", 2, 20),
                  (11, 8, "#c9ab68", 2, 20), (7, 8, "#d9bf78", 1, 20), (4, 6, "#e6cf8a", 10, 2), (6, 4, "#e6cf8a", 4, 2),
                  (10, 5, "#e6cf8a", 2, 1)):
            g.px(*a)
    elif k == "paratonnerre":
        g = S(14, 36)
        for a in ((6, 6, "#8a96a3", 2, 28), (6, 6, "#c9d2db", 1, 28), (3, 33, "#4a525c", 8, 2), (6, 2, "#ffe14a", 2, 4),
                  (5, 4, "#ffe14a", 4, 1)):
            g.px(*a)
    elif k == "etoile":
        g = S(18, 14)
        for a in ((8, 2, "#ffe14a", 2, 3), (3, 5, "#ffe14a", 12, 2), (5, 7, "#ffd23f", 8, 2), (4, 9, "#ffd23f", 3, 2),
                  (11, 9, "#ffd23f", 3, 2), (8, 5, "#fff6b0", 2, 2)):
            g.px(*a)
    elif k == "eolienne":
        g = S(24, 38)
        g.px(11, 12, "#e6ecfb", 3, 25)
        g.px(11, 12, "#ffffff", 1, 25)
        g.px(9, 36, "#a9b2d6", 7, 2)
        for tt in range(9):
            g.px(12 - tt, 11 - int(round(tt * .5)), "#c5cdea", 2, 1)
            g.px(12 + tt, 11 - int(round(tt * .5)), "#c5cdea", 2, 1)
            g.px(12, 11 + tt, "#c5cdea", 2, 1)
        g.px(11, 10, "#8b9ac4", 3, 3)
    elif k == "tombe":
        g = S(18, 24)
        for a in ((3, 8, "#7d828a", 12, 15), (5, 5, "#7d828a", 8, 3), (7, 4, "#8d929a", 4, 1), (3, 8, "#9ba0a8", 2, 15),
                  (8, 10, "#4a4d52", 2, 8), (6, 12, "#4a4d52", 6, 2), (2, 22, "#3d2f52", 14, 2)):
            g.px(*a)
    elif k == "rune":
        g = S(18, 30)
        for a in ((4, 4, "#5d6168", 10, 24), (4, 4, "#8d929a", 2, 24), (5, 2, "#5d6168", 7, 2), (8, 9, "#c48aff", 2, 12),
                  (6, 12, "#c48aff", 6, 2), (6, 17, "#c48aff", 2, 2), (10, 17, "#c48aff", 2, 2), (3, 27, "#251c38", 12, 2)):
            g.px(*a)
    elif k == "engrenage":
        g = S(26, 26)
        for i in range(8):
            a = i * math.pi / 4
            g.px(13 + math.cos(a) * 10 - 2, 13 + math.sin(a) * 10 - 2, "#4a525c", 4, 4)
        blob(g, 13, 13, 9, 9, ["#4a525c", "#8a96a3", "#c9d2db"], r)
        blob(g, 13, 13, 3, 3, ["#2c3238", "#3a4149", "#4a525c"], r)
    elif k == "tuyau":
        g = S(26, 28)
        for a in ((4, 8, "#b86a38", 5, 18), (4, 8, "#d48a55", 1, 18), (4, 6, "#8f4a24", 16, 5), (4, 6, "#d48a55", 16, 1),
                  (17, 6, "#b86a38", 5, 14), (20, 6, "#8f4a24", 2, 14), (2, 24, "#5e3018", 9, 3), (15, 19, "#5e3018", 9, 3),
                  (10, 7, "#3df2ff", 2, 2)):
            g.px(*a)
    elif k == "neon":
        g = S(18, 40)
        for a in ((8, 8, "#4a525c", 2, 30), (8, 8, "#8a96a3", 1, 30), (5, 37, "#3a4149", 8, 2), (4, 4, "#4a525c", 10, 4),
                  (5, 8, "#3df2ff", 8, 2), (6, 10, "#b9fbff", 6, 1)):
            g.px(*a)
    elif k == "roseau":
        g = S(18, 26)
        for x, h in ((4, 18), (8, 22), (12, 16), (15, 20)):
            g.px(x, 25 - h, "#6a8f2a", 1, h)
            g.px(x - 1, 25 - h, "#7a4f28", 3, 4)
    elif k == "bulles":
        g = S(20, 18)
        for x, y, rr in ((6, 12, 3), (13, 9, 4), (10, 4, 2)):
            blob(g, x, y, rr, rr, ["#4b6424", "#8fe03a", "#d9ff8a"], r)
            g.px(x - 1, y - 1, "#ffffff")
    elif k == "caisse":                      # une archive (.tar.gz, .zip) : la caisse en bois du « tar »
        g = S(22, 18)
        g.px(2, 4, "#8a5a33", 18, 13)
        g.px(2, 4, "#b5804a", 18, 2)
        g.px(2, 15, "#5a381e", 18, 2)
        for x in (2, 10, 18):
            g.px(x, 4, "#5a381e", 2, 13)
        g.px(3, 8, "#6b4426", 16, 1)
        g.px(3, 11, "#6b4426", 16, 1)
    elif k in ("parchemin", "parchemin_machine"):    # un texte (.txt) ou un script (.sh) : un parchemin roulé
        g = S(20, 22)
        g.px(4, 4, "#f3e2b8", 12, 15)
        g.px(3, 2, "#d9bf8a", 14, 3)
        g.px(3, 18, "#d9bf8a", 14, 3)
        for i in range(4):
            g.px(6, 7 + i * 3, "#7b5534", 8 - (i % 2) * 3, 1)
        if k == "parchemin_machine":
            g.px(12, 12, "#4a525c", 6, 6)
            g.px(14, 14, "#3df2ff", 2, 2)
    else:                                    # un panneau (objet inconnu)
        g = S(20, 24)
        g.px(9, 10, "#6b4426", 2, 14)
        g.px(2, 3, "#8a5a33", 16, 9)
        g.px(2, 3, "#a8743f", 16, 1)
        g.px(2, 11, "#5a381e", 16, 1)
        g.px(5, 6, "#3a2414", 10, 1)
        g.px(5, 8, "#3a2414", 7, 1)
    s = _DECOS[k] = px.cadre(px.w / 2, px.h, "deco|" + k)
    return s
