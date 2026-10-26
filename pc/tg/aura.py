"""Les auras de rareté : une lueur qui suit la silhouette d'une bestiole et montre sa rareté.

L'aura est calculée depuis le MASQUE de l'image (les pixels non vides) : chaque pixel vide proche de la
silhouette reçoit une lueur dont la force baisse avec la distance (1 à 3 pixels selon la rareté). Elle
« respire » (une vague part de la silhouette vers l'extérieur), les plus rares ont en plus un reflet qui
passe en diagonale, et les shiny une lueur arc-en-ciel avec quelques étincelles.

L'échelle (les couleurs sont celles de bestiaire.COULEUR_RARETE) :
    commune      aucune (presque invisible sur les dessins, rien dans le terminal)
    peu commune  vert   · 1 pixel
    rare         bleu   · 2 pixels
    épique       violet · 2 pixels + reflet
    légendaire   or     · 3 pixels + reflet
    mythique     rose   · 3 pixels + reflet
    shiny        arc-en-ciel · 3 pixels + reflet + étincelles (prioritaire sur la rareté)

Même calcul sur Android (app/…/Aura.kt). Dans le terminal, les pixels de l'aura deviennent des
demi-blocs colorés (la couleur est assombrie selon la force : on suppose un fond sombre).
"""
import colorsys
import math

from .plateforme import RESET

PHASES = 16                     # une respiration complète = 16 images
PHASE_FIXE = 4                  # image fixe (listes) : la lueur au plus fort
ORDRE = ["commune", "peu commune", "rare", "épique", "légendaire", "mythique", "shiny"]


class Palier:
    def __init__(self, couleur, rayon, force, reflet=False, terminal=True):
        self.couleur, self.rayon, self.force, self.reflet, self.terminal = couleur, rayon, force, reflet, terminal


PALIERS = {
    "commune": Palier("#b0b0c0", 1, 40, terminal=False),
    "peu commune": Palier("#5fd787", 1, 150),
    "rare": Palier("#5fafff", 2, 170),
    "épique": Palier("#c77dff", 2, 195, reflet=True),
    "légendaire": Palier("#ffaf00", 3, 215, reflet=True),
    "mythique": Palier("#ff5f87", 3, 230, reflet=True),
    "shiny": Palier(None, 3, 220, reflet=True),
}


def palier_de(rarete, shiny=False):
    """Le palier d'aura d'une bestiole : shiny d'abord, sinon sa rareté (commune si inconnue)."""
    return "shiny" if shiny else (rarete if rarete in PALIERS else "commune")


def palier_ind(ind):
    """Le palier d'aura d'une bestiole de la troupe (dict d'individu)."""
    from . import bestiaire as B
    return palier_de(B.rarete_de(ind), ind.get("shiny"))


def palier_compagnon(state):
    """La créature principale n'a pas de rareté et ne naît jamais shiny : pas d'aura (None).
    Seul un compagnon shiny d'une ancienne sauvegarde (avant cette règle) garde sa lueur arc-en-ciel."""
    return "shiny" if state.get("shiny") else None


def active(state):
    """L'aura autour de la créature de l'écran principal (réglage de la partie, `tg aura on|off`)."""
    return bool(state.get("config", {}).get("aura", True))


def visible(nom, terminal=False):
    p = PALIERS.get(nom)
    return p is not None and (p.terminal or not terminal)


# ---------------------------------------------------------------- calcul
def _rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


_DIST = {}


def distances(w, h, plein, r):
    """Distance (en pixels) de chaque pixel vide à la silhouette, sur une toile agrandie de r de chaque côté.
    plein : liste de w*h booléens. Renvoie (W, H, liste de distances ou None au-delà de r + 0.5)."""
    cle = (w, h, r, bytes(1 if p else 0 for p in plein))
    if cle in _DIST:
        return _DIST[cle]
    W, H = w + 2 * r, h + 2 * r
    d = [None] * (W * H)
    voisins = [(dx, dy, math.hypot(dx, dy)) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
               if (dx or dy) and math.hypot(dx, dy) <= r + 0.5]
    for y in range(h):
        for x in range(w):
            if not plein[y * w + x]:
                continue
            bord = any(not (0 <= x + a < w and 0 <= y + b < h) or not plein[(y + b) * w + x + a]
                       for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)))
            if not bord:
                continue
            for dx, dy, l in voisins:
                X, Y = x + r + dx, y + r + dy
                sx, sy = x + dx, y + dy
                if 0 <= sx < w and 0 <= sy < h and plein[sy * w + sx]:
                    continue
                k = Y * W + X
                if d[k] is None or l < d[k]:
                    d[k] = l
    # seulement DEHORS : les trous fermés à l'intérieur de la silhouette restent vides (BFS depuis le bord)
    dehors = [False] * (W * H)
    pile = [k for k in range(W * H) if k % W in (0, W - 1) or k // W in (0, H - 1)]
    for k in pile:
        dehors[k] = True
    while pile:
        k = pile.pop()
        x, y = k % W, k // W
        for X, Y in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= X < W and 0 <= Y < H and not dehors[Y * W + X]:
                sx, sy = X - r, Y - r
                if 0 <= sx < w and 0 <= sy < h and plein[sy * w + sx]:
                    continue
                dehors[Y * W + X] = True
                pile.append(Y * W + X)
    d = [v if dehors[k] else None for k, v in enumerate(d)]
    if len(_DIST) > 256:
        _DIST.clear()
    _DIST[cle] = (W, H, d)
    return _DIST[cle]


def _hasard(x, y, n):
    v = (x * 73856093) ^ (y * 19349663) ^ (n * 83492791)
    v = (v ^ (v >> 13)) * 1274126177
    return (v ^ (v >> 16)) & 0xFFFF


def calque(w, h, plein, nom, phase=PHASE_FIXE):
    """L'aura seule : (W, H, R, pixels (r, g, b, a) ou None), toile agrandie de R = rayon du palier."""
    p = PALIERS.get(nom) or PALIERS["commune"]
    r = p.rayon
    W, H, dist = distances(w, h, plein, r)
    out = [None] * (W * H)
    base = None if p.couleur is None else _rgb(p.couleur)
    tour = 2 * math.pi * (phase % PHASES) / PHASES
    for k, d in enumerate(dist):
        if d is None:
            continue
        x, y = k % W, k // W
        chute = max(0.0, min(1.0, (r + 0.75 - d) / (r - 0.25)))
        if chute <= 0:
            continue
        vague = 0.78 + 0.22 * math.sin(tour - 0.9 * (d - 1))       # la lueur respire, de la silhouette vers l'extérieur
        a = p.force * chute * vague
        if base is None:                                             # shiny : arc-en-ciel qui glisse
            t = ((x + y) / max(8, W + H) * 1.6 + (phase % PHASES) / PHASES) % 1.0
            c = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(t, 0.55, 1.0))
        else:
            c = base
        if p.reflet:                                                 # un reflet clair passe en diagonale
            pos = (phase % PHASES) / PHASES * (W + H + 8) - 4
            e = max(0.0, 1.0 - abs((x + y) - pos) / 3.0)
            if e:
                c = tuple(int(v + (255 - v) * 0.55 * e) for v in c)
                a += 60 * e * chute
        if nom == "shiny" and d <= 2.2 and _hasard(x, y, phase // 2) % 23 == 0:
            c, a = (255, 255, 255), 255                              # étincelle
        out[k] = (c[0], c[1], c[2], max(0, min(255, int(a))))
    return W, H, r, out


def composer(w, h, couleurs, nom, phase=PHASE_FIXE):
    """La bestiole posée sur son aura : (W, H, pixels (r, g, b, a) ou None). couleurs : "#rrggbb" ou None."""
    plein = [c is not None for c in couleurs]
    W, H, r, aur = calque(w, h, plein, nom, phase)
    out = list(aur)
    for y in range(h):
        for x in range(w):
            c = couleurs[y * w + x]
            if c is not None:
                out[(y + r) * W + x + r] = _rgb(c) + (255,)
    return W, H, out


# ---------------------------------------------------------------- terminal (demi-blocs)
SEUIL_TERMINAL = 36             # en dessous, le pixel d'aura reste vide (lisible)
DOUCEUR_TERMINAL = 0.7          # le terminal n'a pas de transparence : l'aura y est plus discrète


def _sur_fond(px):
    """Pixel d'aura → couleur opaque, mélangée à un fond sombre (le terminal n'a pas de transparence)."""
    if px is None or px[3] < SEUIL_TERMINAL:
        return None
    f = min(1.0, px[3] / 255 * DOUCEUR_TERMINAL)
    return "#%02x%02x%02x" % (int(px[0] * f), int(px[1] * f), int(px[2] * f))


def lignes(w, h, couleurs, nom, phase=PHASE_FIXE):
    """Lignes de demi-blocs de la bestiole entourée de son aura (sans aura si le palier est invisible
    dans le terminal, par exemple « commune »)."""
    from . import bestiaire as B
    if not visible(nom, terminal=True):
        return lignes_brutes(w, h, couleurs)
    W, H, px = composer(w, h, couleurs, nom, phase)
    if H % 2:
        px += [None] * W
        H += 1
    hexa = []
    for v in px:
        if v is None:
            hexa.append(None)
        elif v[3] == 255:
            hexa.append("#%02x%02x%02x" % v[:3])
        else:
            hexa.append(_sur_fond(v))
    return _demi_blocs(W, H, hexa, B)


def lignes_brutes(w, h, couleurs):
    from . import bestiaire as B
    return _demi_blocs(w, h, list(couleurs) + ([None] * w if h % 2 else []), B)


def _demi_blocs(W, H, hexa, B):
    out = []
    for y in range(0, H, 2):
        s = ""
        for x in range(W):
            ca = hexa[y * W + x]
            cb = hexa[(y + 1) * W + x] if y + 1 < H else None
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += B.fg24(ca) + "▀" + RESET
            elif ca is None:
                s += B.fg24(cb) + "▄" + RESET
            else:
                s += B.fg24(ca) + B.bg24(cb) + "▀" + RESET
        out.append(s)
    return out


def depuis_octets(w, h, octets, pal):
    """Image indexée (octets, palette "#rrggbb", 0 = vide) → liste de couleurs ou None."""
    return [pal[o - 1] if o else None for o in octets[:w * h]]


# ---------------------------------------------------------------- PNG (démos, tests)
def png(chemin, W, H, px, echelle=6, fond=None):
    """Écrit des pixels (r, g, b, a) ou None en PNG agrandi (sans bibliothèque). fond : (r, g, b) ou None."""
    import struct
    import zlib
    brut = bytearray()
    for y in range(H * echelle):
        brut.append(0)
        for x in range(W * echelle):
            v = px[(y // echelle) * W + x // echelle]
            if fond is not None:
                if v is None:
                    brut += bytes(fond) + b"\xff"
                else:
                    a = v[3] / 255
                    brut += bytes(int(v[i] * a + fond[i] * (1 - a)) for i in range(3)) + b"\xff"
            else:
                brut += (bytes(v) if v is not None else b"\x00\x00\x00\x00")

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", W * echelle, H * echelle, 8, 6, 0, 0, 0))
                + bloc(b"IDAT", zlib.compress(bytes(brut), 6)) + bloc(b"IEND", b""))
