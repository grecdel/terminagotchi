"""Les créatures dans le jeu avec le rendu le plus fin du terminal (le même choix que l'intro, scenes.py) :

    kitty, iterm, sixel  une vraie image (pixels nets agrandis ×4, aura avec transparence, décor au demi-pixel)
    quadrants            texte : chaque case = 1 colonne × 2 lignes de pixels, coupée en 2 × 2 ; la créature reste
                         exacte (comme les demi-blocs) et le décor de l'aura gagne le demi-pixel en largeur
    demi                 les demi-blocs d'avant (console linux, fichiers, tests)

Les sextants (2 × 3) servent aux illustrations de l'intro ; pour une créature en gros pixels, ils couperaient chaque
pixel en 2/3 – 1/3 : on prend les quadrants, qui tombent juste. TG_IMAGES force un rendu (comme pour l'intro) ; hors
d'un vrai terminal, toujours les demi-blocs.

Une vraie image occupe une place de texte (des espaces) ; elle est posée depuis la dernière ligne (le curseur
remonte, dessine, puis revient) : les espaces effacent d'abord l'image d'avant (utile en sixel), et la mise en page
de l'écran principal ne bouge pas.
"""
import os
import struct
import sys
import zlib

from . import aura as A

IDENT = 4243                      # le numéro de l'image Kitty de la créature (l'intro utilise 4242)
F_IMAGE = 4                       # une vraie image : chaque pixel de la créature = 4 × 4 pixels
FOND = (12, 14, 18)               # le fond supposé du terminal (sixel : la lueur semi-transparente s'y mélange)
_UTILISE = {"kitty": False}


def mode():
    """Le rendu des créatures : kitty | iterm | sixel | quadrants | demi."""
    force = os.environ.get("TG_IMAGES", "")
    if force in ("kitty", "iterm", "sixel", "demi"):
        return force
    if force in ("sextants", "quadrants"):
        return "quadrants"
    try:
        tty = sys.stdout.isatty() and sys.stdin.isatty()
    except (AttributeError, ValueError, OSError):
        tty = False
    if not tty:
        return "demi"
    try:
        from . import scenes
        if not scenes.mode_couleurs():
            return "demi"
        r = scenes.rendu()
    except Exception:                                    # noqa: BLE001 — jamais d'écran cassé pour un rendu
        return "demi"
    return {"sextants": "quadrants"}.get(r, r) if r in ("kitty", "iterm", "sixel", "sextants", "quadrants") else "demi"


# ---------------------------------------------------------------- la créature et son aura, en pixels fins
def composer_fin(w, h, couleurs, nom, phase, eclat, fx, fy):
    """(W·fx, H·fy, pixels (r, g, b, a) ou None) : la créature (pixels nets), sa lueur, son décor posé au
    demi-pixel (particules derrière, étincelles devant) et le reflet qui passe dessus. nom None : sans aura."""
    if nom and A.visible(nom):
        plein = [c is not None for c in couleurs]
        W, H, r, aur = A.calque(w, h, plein, nom, phase, eclat)
        dec = A.decor(w, h, plein, nom, phase, eclat)
        pos = A.reflet(nom, phase, W, H)
    else:
        W, H, r, aur, dec, pos = w, h, 0, [None] * (w * h), [], None
    WF, HF = W * fx, H * fy
    out = [None] * (WF * HF)
    for y in range(H):
        for x in range(W):
            v = aur[y * W + x]
            if v is not None and v[3]:
                for j in range(fy):
                    b = (y * fy + j) * WF + x * fx
                    out[b:b + fx] = [v] * fx
    px, py = max(1, fx // 2), max(1, fy // 2)

    def point(x2, y2, c, a):
        X, Y = x2 * fx // 2, y2 * fy // 2
        nv = (c >> 16, c >> 8 & 255, c & 255)
        for j in range(py):
            for i in range(px):
                if 0 <= X + i < WF and 0 <= Y + j < HF:
                    k = (Y + j) * WF + X + i
                    v = out[k]
                    if v is None or v[3] < 255:
                        out[k] = nv + (max(a, 0 if v is None else v[3]),)
                    else:
                        out[k] = tuple(v[q] + (nv[q] - v[q]) * a // 255 for q in range(3)) + (255,)
    for x2, y2, c, a, devant in dec:
        if not devant:
            point(x2, y2, c, a)
    for y in range(h):
        for x in range(w):
            c = couleurs[y * w + x]
            if c is None:
                continue
            v = A.lustrer(int(c[1:7], 16), x + r, y + r, pos)
            t = (v >> 16, v >> 8 & 255, v & 255, 255)
            for j in range(fy):
                b = ((y + r) * fy + j) * WF + (x + r) * fx
                out[b:b + fx] = [t] * fx
    for x2, y2, c, a, devant in dec:
        if devant:
            point(x2, y2, c, a)
    return WF, HF, out


def _opaque(v):
    """Un pixel (r, g, b, a) → couleur opaque sur fond sombre, ou None (le terminal n'a pas de transparence)."""
    if v is None or v[3] < A.SEUIL_TERMINAL:
        return None
    if v[3] == 255:
        return v[:3]
    f = min(255, v[3] * 7 // 10)
    return (v[0] * f // 255, v[1] * f // 255, v[2] * f // 255)


# ---------------------------------------------------------------- texte : quadrants
QUADRANTS = " ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█"


def _code(fg_, bg_=None):
    s = f"\x1b[38;2;{fg_[0]};{fg_[1]};{fg_[2]}"
    if bg_ is not None:
        s += f";48;2;{bg_[0]};{bg_[1]};{bg_[2]}"
    return s + "m"


def quadrants(W, H, px):
    """Pixels fins (2 par colonne, 1 par demi-ligne) → lignes de quadrants (transparence : le fond du terminal)."""
    from .scenes import deux_couleurs
    if H % 2:
        px = px + [None] * W
        H += 1
    out = []
    for cy in range(H // 2):
        s = ""
        for cx in range(W // 2):
            cs = [_opaque(px[(2 * cy + j) * W + 2 * cx + i]) for j in range(2) for i in range(2)]
            pleins = [c for c in cs if c is not None]
            if not pleins:
                s += " "
                continue
            if len(pleins) == 4:
                bits, a, b = deux_couleurs(cs)
                s += (_code(a, b) + QUADRANTS[bits] if bits not in (0, 15) else _code(a) + "█") + "\x1b[0m"
                continue
            bits = sum(1 << i for i, c in enumerate(cs) if c is not None)
            m = tuple(sum(c[q] for c in pleins) // len(pleins) for q in range(3))
            s += _code(m) + QUADRANTS[bits] + "\x1b[0m"
        out.append(s)
    return out


# ---------------------------------------------------------------- vraies images
def png_rgba(W, H, px):
    """Pixels (r, g, b, a) ou None → PNG RVBA (transparent là où il n'y a rien)."""
    raw = bytearray()
    vide = b"\x00\x00\x00\x00"
    for y in range(H):
        raw.append(0)
        for v in px[y * W:(y + 1) * W]:
            raw += vide if v is None else bytes(v)

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(bytes(raw), 1)) + bloc(b"IEND", b""))


def sixel_transparent(W, H, px):
    """Pixels (r, g, b, a) ou None → sixel où le vide reste transparent (P2 = 1) ; la lueur se mélange à FOND."""
    import re
    idx = []
    compte = {}
    for v in px:
        if v is None or v[3] < 24:
            idx.append(None)
            continue
        a = v[3]
        c = tuple((v[q] * a + FOND[q] * (255 - a)) // 255 >> 4 for q in range(3))
        idx.append(c)
        compte[c] = compte.get(c, 0) + 1
    pal = sorted(compte, key=lambda k: (-compte[k], k))[:255]
    num = {k: i for i, k in enumerate(pal)}
    for k in compte:
        if k not in num:
            num[k] = min(range(len(pal)), key=lambda i: sum((pal[i][q] - k[q]) ** 2 for q in range(3)))
    out = ["\x1bP0;1;0q", f'"1;1;{W};{H}']
    out += [f"#{i};2;{r * 17 * 100 // 255};{g * 17 * 100 // 255};{b * 17 * 100 // 255}" for i, (r, g, b) in enumerate(pal)]
    trad = bytes(63 + (v & 63) for v in range(256))
    runs = re.compile(r"(.)\1{3,}")
    for y0 in range(0, H, 6):
        couches = {}
        for dy in range(min(6, H - y0)):
            for x in range(W):
                c = idx[(y0 + dy) * W + x]
                if c is None:
                    continue
                ci = num[c]
                a = couches.get(ci)
                if a is None:
                    a = couches[ci] = bytearray(W)
                a[x] |= 1 << dy
        for ci in sorted(couches):
            s = couches[ci].translate(trad).decode().rstrip("?")
            out.append(f"#{ci}" + runs.sub(lambda m: f"!{len(m.group(0))}{m.group(1)}", s) + "$")
        out.append("-")
    return "".join(out) + "\x1b\\"


def _reduire(W, H, px, W2, H2):
    """Agrandissement / réduction au plus proche (le sixel ne s'étire pas tout seul)."""
    return [px[(y * H // H2) * W + x * W // W2] for y in range(H2) for x in range(W2)]


def _poser(img, cols, rangs):
    """La place de l'image (des espaces) et, sur la dernière ligne, l'image posée en remontant le curseur."""
    lignes = [" " * cols for _ in range(rangs)]
    monte = f"\x1b[{rangs - 1}A" if rangs > 1 else ""
    lignes[-1] += "\x1b7" + monte + f"\x1b[{cols}D" + img + "\x1b8"
    return lignes


# ---------------------------------------------------------------- l'entrée
def lignes(w, h, couleurs, nom=None, phase=A.PHASE_FIXE, eclat=A.ECLAT_NORMAL, rendu=None):
    """(lignes, largeur en colonnes) de la créature (couleurs "#rrggbb" ou None, w × h) entourée de son aura nom
    (None : sans aura), au rendu le plus fin du terminal (rendu : forcer kitty | iterm | sixel | quadrants | demi)."""
    r = rendu or mode()
    vis = nom if nom and A.visible(nom, terminal=True) else None
    if r == "demi":
        if vis:
            ls = A.lignes(w, h, couleurs, vis, phase, eclat)
            return ls, w + 2 * A.PALIERS[vis].rayon
        return A.lignes_brutes(w, h, couleurs), w
    if r == "quadrants":
        W, H, px = composer_fin(w, h, couleurs, vis, phase, eclat, 2, 1)
        return quadrants(W, H, px), W // 2
    W, H, px = composer_fin(w, h, couleurs, nom if nom and A.visible(nom) else None, phase, eclat, F_IMAGE, F_IMAGE)
    cols, rangs = W // F_IMAGE, -(-(H // F_IMAGE) // 2)
    if r == "kitty":
        from .scenes import kitty
        _UTILISE["kitty"] = True
        return _poser(kitty(png_rgba(W, H, px), cols, rangs, IDENT), cols, rangs), cols
    if r == "iterm":
        from .scenes import iterm
        return _poser(iterm(png_rgba(W, H, px), cols, rangs), cols, rangs), cols
    try:
        from .scenes import capacites
        cw, ch = capacites()["cellule"]
    except Exception:                                    # noqa: BLE001
        cw, ch = 10, 20
    W2, H2 = cols * cw, rangs * ch // 6 * 6
    return _poser(sixel_transparent(W2, H2, _reduire(W, H, px, W2, H2)), cols, rangs), cols


# ---------------------------------------------------------------- la vie au repos (vie.py), au pixel fin
def composer_vie(a, pal, t, nom, eclat, F=F_IMAGE):
    """(W·F, H·F, pixels (r, g, b, a) ou None) : l'image de vie t agrandie F fois (respiration et ondulations au pixel
    fin : vie.image_fine), sur sa lueur, avec le décor de l'aura (calculés sur le masque au pixel du sprite)."""
    from . import vie
    W2, H2, img = vie.image(a, t)
    WF0, HF0, fine = vie.image_fine(a, t, F)
    plein = [v != 0 for v in img]
    if nom and A.visible(nom):
        W, H, r, aur = A.calque(W2, H2, plein, nom, t, eclat)
        dec = A.decor(W2, H2, plein, nom, t, eclat)
        pos = A.reflet(nom, t, W, H)
    else:
        W, H, r, aur, dec, pos = W2, H2, 0, [None] * (W2 * H2), [], None
    WF, HF = W * F, H * F
    out = [None] * (WF * HF)
    for y in range(H):
        for x in range(W):
            v = aur[y * W + x]
            if v is not None and v[3]:
                for j in range(F):
                    b = (y * F + j) * WF + x * F
                    out[b:b + F] = [v] * F
    cote = max(1, F // 2)

    def point(x2, y2, c, al):
        X, Y = x2 * F // 2, y2 * F // 2
        nv = (c >> 16, c >> 8 & 255, c & 255)
        for j in range(cote):
            for i in range(cote):
                if 0 <= X + i < WF and 0 <= Y + j < HF:
                    k = (Y + j) * WF + X + i
                    q = out[k]
                    if q is None or q[3] < 255:
                        out[k] = nv + (max(al, 0 if q is None else q[3]),)
                    else:
                        out[k] = tuple(q[m] + (nv[m] - q[m]) * al // 255 for m in range(3)) + (255,)
    for x2, y2, c, al, devant in dec:
        if not devant:
            point(x2, y2, c, al)
    o = r * F
    cache = {}
    for y in range(HF0):
        for x in range(WF0):
            v = fine[y * WF0 + x]
            if v:
                sx, sy = x // F + r, y // F + r
                cle = (v, (sx + sy - pos) if pos is not None and abs(sx + sy - pos) <= 2 else None)
                c = cache.get(cle)
                if c is None:
                    q = A.lustrer(pal[v - 1], sx, sy, pos)
                    c = cache[cle] = (q >> 16, q >> 8 & 255, q & 255, 255)
                out[(y + o) * WF + x + o] = c
    for x2, y2, c, al, devant in dec:
        if devant:
            point(x2, y2, c, al)
    return WF, HF, out


def lignes_vie(a, pal, t, nom=None, eclat=A.ECLAT_NORMAL, rendu=None):
    """(lignes, largeur) de l'image de vie t : vraie image au pixel fin (Kitty, iTerm2, sixel), sinon le texte avec la
    respiration en fondu de couleurs (vie.couleurs_texte : pas de saut d'un gros pixel)."""
    from . import vie
    r = rendu or mode()
    if r in ("kitty", "iterm", "sixel"):
        W, H, px = composer_vie(a, pal, t, nom if nom and A.visible(nom) else None, eclat)
        cols, rangs = W // F_IMAGE, -(-(H // F_IMAGE) // 2)
        if r == "kitty":
            from .scenes import kitty
            _UTILISE["kitty"] = True
            return _poser(kitty(png_rgba(W, H, px), cols, rangs, IDENT), cols, rangs), cols
        if r == "iterm":
            from .scenes import iterm
            return _poser(iterm(png_rgba(W, H, px), cols, rangs), cols, rangs), cols
        try:
            from .scenes import capacites
            cw, ch = capacites()["cellule"]
        except Exception:                                # noqa: BLE001
            cw, ch = 10, 20
        W2, H2 = cols * cw, rangs * ch // 6 * 6
        return _poser(sixel_transparent(W2, H2, _reduire(W, H, px, W2, H2)), cols, rangs), cols
    cs = vie.couleurs_texte(a, pal, t)
    W2, H2 = a.w + 2 * vie.PAD, a.h + vie.PAD
    return lignes(W2, H2, [None if c is None else "#%06x" % c for c in cs], nom, t, eclat, r)


def effacer():
    """Retire l'image Kitty de la créature (en quittant l'écran principal : elle ne reste pas sur les menus)."""
    if _UTILISE["kitty"]:
        _UTILISE["kitty"] = False
        sys.stdout.write(f"\x1b_Ga=d,d=i,i={IDENT},q=2\x1b\\")
        sys.stdout.flush()
