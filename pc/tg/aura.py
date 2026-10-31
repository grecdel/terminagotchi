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

Par-dessus la lueur, le DÉCOR (calculé en entiers, identique sur Android, en demi-pixels pour les rendus fins) :
    particules  de petits pixels qui montent autour de la créature (plus nombreux quand c'est plus rare)
    reflet      une bande claire qui passe sur la créature elle-même (légendaire, mythique, shiny)
    étincelles  de petites étoiles qui scintillent au bord de la silhouette (shiny)

L'ÉCLAT suit le soin (satiété et envies, voir eclat()) : l'aura brille davantage quand la créature est bien
soignée ou rassasiée, et pâlit quand elle est négligée — jamais de mort ni de punition, juste une lueur plus douce.
    3 rayonnante (bien soignée) · 2 normale · 1 pâle (affamée) · 0 très pâle, sans particules (en veille)

Même calcul sur Android (app/…/Aura.kt). Dans le terminal, les pixels de l'aura deviennent des
demi-blocs colorés (la couleur est assombrie selon la force : on suppose un fond sombre) ; rendu_fin.py s'en sert
pour les vraies images (Kitty, iTerm2, sixel) et les quadrants.
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


ECLAT_FORCE = (45, 70, 100, 125)          # % de la force de la lueur, selon l'éclat 0 à 3
ECLAT_NORMAL = 2


def eclat(state):
    """L'éclat de l'aura selon le soin (0 à 3) : la faim compte pour 60 %, les envies jeu, curiosité, exploration et
    sommeil pour 40 %. Rassasiée et bien soignée (≥ 80) → 3 ; en forme (≥ 40) → 2 ; affamée (≥ 15) → 1 ; en veille → 0."""
    try:
        faim = float(state.get("hunger", 80))
        v = (state.get("envies") or {}).get("v") or {}
        autres = [float(v[k]) for k in ("jeu", "curiosite", "explorer", "sommeil") if k in v]
        moy = sum(autres) / len(autres) if autres else faim
        veille = bool((state.get("satiete") or {}).get("veille"))
        return niveau_satiete(int(faim), int(moy), veille)
    except (TypeError, ValueError, AttributeError):
        return ECLAT_NORMAL


def niveau_soin(faim, envies):
    """(Avant la satiété, gardé pour les vecteurs de donnees/vie/vecteurs.json.) faim et moyenne des envies → éclat."""
    soin = (faim * 6 + envies * 4) // 10
    if faim < 15:
        return 0
    if soin >= 80 and faim >= 70:
        return 3
    if soin >= 40 and faim >= 30:
        return 2
    return 1


def niveau_satiete(faim, envies, veille=False):
    """L'éclat d'après les 4 états de la satiété (satiete.py ; le même calcul en Kotlin, vérifié par
    donnees/satiete/vecteurs.json) : en veille → 0 ; affamée → 1 ; en forme → 2 ; rassasiée et envies au moins
    moyennes (≥ 50) → 3."""
    from .satiete import AFFAMEE, FORME, RASSASIEE
    if veille or faim < AFFAMEE:
        return 0
    if faim < FORME:
        return 1
    if faim >= RASSASIEE and envies >= 50:
        return 3
    return 2


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


def calque(w, h, plein, nom, phase=PHASE_FIXE, eclat=ECLAT_NORMAL):
    """L'aura seule : (W, H, R, pixels (r, g, b, a) ou None), toile agrandie de R = rayon du palier.
    eclat (0 à 3) : la lueur plus forte (bien soignée) ou plus pâle (négligée)."""
    p = PALIERS.get(nom) or PALIERS["commune"]
    ef = ECLAT_FORCE[max(0, min(3, eclat))]
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
        a = p.force * chute * vague * ef / 100
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
        if eclat == 0:                                               # en veille : une lueur grise et douce
            g = (c[0] + c[1] + c[2]) // 3
            c = ((c[0] + g) // 2, (c[1] + g) // 2, (c[2] + g) // 2)
        out[k] = (c[0], c[1], c[2], max(0, min(255, int(a))))
    return W, H, r, out


# ---------------------------------------------------------------- le décor : particules, étincelles, reflet (entiers)
CYCLE_DECOR = 32                 # particules et reflet : 32 images (4 s à 8 images par seconde)
PARTICULES = {"commune": 0, "peu commune": 4, "rare": 6, "épique": 8, "légendaire": 10, "mythique": 12, "shiny": 12}
ARC = (0xFF7A7A, 0xFFC56B, 0xFFF27A, 0x7DFF9B, 0x7AC8FF, 0xC59BFF)     # les particules d'un shiny
REFLET = ("légendaire", "mythique", "shiny")                             # le reflet qui passe SUR la créature
SIN = (0, 38, 71, 92, 100, 92, 71, 38, 0, -38, -71, -92, -100, -92, -71, -38)
M32 = 0xFFFFFFFF


def _mel(v):
    v &= M32
    v = ((v ^ (v >> 15)) * 0x2C1B3C6D) & M32
    v = ((v ^ (v >> 12)) * 0x297A2D39) & M32
    return v ^ (v >> 15)


def _clair(c, pct):
    r, g, b = c >> 16 & 255, c >> 8 & 255, c & 255
    return ((r + (255 - r) * pct // 100) << 16) | ((g + (255 - g) * pct // 100) << 8) | (b + (255 - b) * pct // 100)


def decor(w, h, plein, nom, phase=PHASE_FIXE, eclat=ECLAT_NORMAL):
    """Les petits points du décor, en DEMI-pixels sur la toile de l'aura (2W × 2H, W = w + 2R) :
    [(x2, y2, 0xRRGGBB, alpha 0..255, devant)] ; devant = False : derrière la créature (particules), True : par-dessus
    (étincelles). Calcul en entiers (Aura.kt donne la même liste)."""
    p = PALIERS.get(nom) or PALIERS["commune"]
    r = p.rayon
    W, H = w + 2 * r, h + 2 * r
    eclat = max(0, min(3, eclat))
    ef = ECLAT_FORCE[eclat]
    out = []
    n = PARTICULES.get(nom, 0) * (0, 1, 2, 3)[eclat] // 2
    ph = phase % CYCLE_DECOR
    graine = (w * 131 + h * 7 + ORDRE.index(nom) * 1013) if nom in ORDRE else w * 131 + h
    base = 0xFFFFFF if p.couleur is None else int(p.couleur[1:], 16)
    a0 = min(255, (p.force + 40) * ef // 100)
    bords = []                                               # les bords gauche et droit de chaque ligne
    for y in range(h):
        xs = [x for x in range(w) if plein[y * w + x]]
        bords.append((xs[0], xs[-1]) if xs else None)
    for i in range(n):
        hs = _mel(graine * 7919 + i * 104729 + 17)
        vie_ = 14 + (hs >> 8) % 12
        age = (ph + (hs >> 16) % CYCLE_DECOR) % CYCLE_DECOR
        if age >= vie_:
            continue
        y0 = h // 3 + (hs >> 3) % max(1, h - h // 3)          # elles partent du bord de la silhouette, en bas
        b = bords[y0]
        if b is None:
            continue
        ecart = (hs >> 24) % (r + 1)
        x0 = 2 * (r + b[0] - 1 - ecart) if hs & 1 else 2 * (r + b[1] + 1 + ecart) + 1
        x2 = x0 + SIN[(age * 2 + i * 3) % 16] // 50
        y2 = 2 * (y0 + r) - age * (h + 2 * r) // vie_
        if not (0 <= x2 < 2 * W and 0 <= y2 < 2 * H):
            continue
        sx, sy = x2 // 2 - r, y2 // 2 - r
        if 0 <= sx < w and 0 <= sy < h and plein[sy * w + sx]:
            continue                                         # derrière la créature : caché
        a = a0 * min(age + 1, 3, vie_ - age) // 3
        c = ARC[i % 6] if p.couleur is None else _clair(base, 45)
        out.append((x2, y2, c, a, False))
    if nom == "shiny" and eclat > 0:                         # les étincelles : de petites étoiles au bord
        bord = []
        for y in range(H):
            for x in range(W):
                sx, sy = x - r, y - r
                if 0 <= sx < w and 0 <= sy < h and plein[sy * w + sx]:
                    continue
                if any(0 <= sx + a < w and 0 <= sy + b < h and plein[(sy + b) * w + sx + a]
                       for b in (-1, 0, 1) for a in (-1, 0, 1)):
                    bord.append((x, y))
        if bord:
            fente = phase // 4
            etape = phase % 4
            bras = (1, 3, 4, 2)[etape]
            for j in range(3):
                hs = _mel(graine * 31 + fente * 977 + j * 1013 + 5)
                x, y = bord[hs % len(bord)]
                cx2, cy2 = 2 * x + 1, 2 * y + 1
                out.append((cx2, cy2, 0xFFFFFF, 255, True))
                for k in range(1, bras + 1):
                    a = 255 - 200 * k // (bras + 1)
                    c = 0xFFF6C8 if k > 1 else 0xFFFFFF
                    for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                        if 0 <= cx2 + dx < 2 * W and 0 <= cy2 + dy < 2 * H:
                            out.append((cx2 + dx, cy2 + dy, c, a, True))
    return out


def reflet(nom, phase, W, H):
    """La position du reflet qui passe en diagonale SUR la créature (x + y sur la toile), ou None (pas de reflet
    pour ce palier, ou entre deux passages)."""
    if nom not in REFLET:
        return None
    ph = phase % CYCLE_DECOR
    if ph >= 20:
        return None
    return ph * (W + H + 8) // 20 - 4


def lustrer(c, x, y, pos):
    """Une couleur de la créature éclaircie par le reflet (c en 0xRRGGBB)."""
    if pos is None:
        return c
    d = abs(x + y - pos)
    if d > 2:
        return c
    return _clair(c, (3 - d) * 18)


def composer(w, h, couleurs, nom, phase=PHASE_FIXE, eclat=ECLAT_NORMAL):
    """La bestiole posée sur son aura : (W, H, pixels (r, g, b, a) ou None). couleurs : "#rrggbb" ou None.
    Le décor est posé au pixel près (demi-pixels arrondis) : particules derrière, étincelles devant, reflet dessus."""
    plein = [c is not None for c in couleurs]
    W, H, r, aur = calque(w, h, plein, nom, phase, eclat)
    out = list(aur)
    dec = decor(w, h, plein, nom, phase, eclat)
    for x2, y2, c, a, devant in dec:
        if not devant:
            _poser_point(out, W, x2 // 2, y2 // 2, c, a)
    pos = reflet(nom, phase, W, H)
    for y in range(h):
        for x in range(w):
            c = couleurs[y * w + x]
            if c is not None:
                v = lustrer(int(c[1:7], 16), x + r, y + r, pos)
                out[(y + r) * W + x + r] = (v >> 16, v >> 8 & 255, v & 255, 255)
    for x2, y2, c, a, devant in dec:
        if devant:
            _poser_point(out, W, x2 // 2, y2 // 2, c, a)
    return W, H, out


def _poser_point(out, W, x, y, c, a):
    """Un point du décor mélangé à ce qui est déjà là (on garde le plus visible)."""
    k = y * W + x
    if k < 0 or k >= len(out) or a <= 0:
        return
    v = out[k]
    nv = (c >> 16, c >> 8 & 255, c & 255)
    if v is None or v[3] < 255:
        a2 = a if v is None else max(a, v[3])
        out[k] = nv + (min(255, a2),)
    else:                                                   # sur la créature (étincelle) : mélange
        out[k] = tuple(v[i] + (nv[i] - v[i]) * a // 255 for i in range(3)) + (255,)


# ---------------------------------------------------------------- terminal (demi-blocs)
SEUIL_TERMINAL = 36             # en dessous, le pixel d'aura reste vide (lisible)
DOUCEUR_TERMINAL = 0.7          # le terminal n'a pas de transparence : l'aura y est plus discrète


def _sur_fond(px):
    """Pixel d'aura → couleur opaque, mélangée à un fond sombre (le terminal n'a pas de transparence)."""
    if px is None or px[3] < SEUIL_TERMINAL:
        return None
    f = min(1.0, px[3] / 255 * DOUCEUR_TERMINAL)
    return "#%02x%02x%02x" % (int(px[0] * f), int(px[1] * f), int(px[2] * f))


def lignes(w, h, couleurs, nom, phase=PHASE_FIXE, eclat=ECLAT_NORMAL):
    """Lignes de demi-blocs de la bestiole entourée de son aura (sans aura si le palier est invisible
    dans le terminal, par exemple « commune »)."""
    from . import bestiaire as B
    if not visible(nom, terminal=True):
        return lignes_brutes(w, h, couleurs)
    W, H, px = composer(w, h, couleurs, nom, phase, eclat)
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
