"""Pixel art : la créature à chaque stade/forme, et les bestioles sauvages."""
import random

from . import core
from .plateforme import RESET, bg, fg

# l'œuf : celui de son type (oeufs.py, dessins de donnees/oeufs/), intact puis fissuré (couleurs « #rrggbb »)
BABY = [
    "............",
    "....bbbb....",
    "..bbbbbbbb..",
    ".bbbbbbbbbb.",
    ".bbebbbbebb.",
    ".bbebbbbebb.",
    "bbkbbmmbbkbb",
    "bbbbbbbbbbbb",
    ".bbbbbbbbbb.",
    "..bb....bb..",
]
ADO = [
    "..bbbbbbbb..",
    ".bbbbbbbbbb.",
    ".bbebbbbebb.",
    ".bbebbbbebb.",
    "bbkbbbbbbkbb",
    "bbbbbmmbbbbb",
    ".bbbbbbbbbb.",
    ".bbbbbbbbbb.",
    "..bbb..bbb..",
    "..bb....bb..",
]
ADO_HEAD = {
    "Intelligence": ["......l.....", "......a....."],
    "Force":        [".h........h.", ".hh......hh."],
    "Agilité":      ["..h......h..", "..hh....hh.."],
    "Endurance":    ["............", "...cccccc..."],
}
ADO_BODY = {
    "Endurance": {6: "??c?c??c?c??", 7: "???c?cc?c???"},
    "Intelligence": {2: "??l?????l???"},
}
ADULT = [
    "..bbbbbbbbbbbb..",
    "..bbbbbbbbbbbb..",
    ".bbbeebbbbeebbb.",
    ".bbbeebbbbeebbb.",
    ".bbkbbbbbbbbkbb.",
    "..bbbbbmmbbbbb..",
    "..bbbbbbbbbbbb..",
    "..bbbbbbbbbbbb..",
    "..bbbbbbbbbbbb..",
    "...bbbb..bbbb...",
    "...bbb....bbb...",
]
ADULT_HEAD = {
    "Intelligence": [".......ll.......", ".......aa......."],
    "Force":        [".hh..........hh.", ".hhh........hhh."],
    "Agilité":      ["...hh......hh...", "...hhh....hhh..."],
    "Endurance":    ["................", "....cccccccc...."],
}
ADULT_BODY = {
    "Intelligence": {2: "???l??llll??l???"},
    "Force":        {4: "h??????????????h", 5: "hh????????????hh"},
    "Agilité":      {4: "w??????????????w", 5: "ww????????????ww", 6: "ww????????????ww", 7: "w??????????????w"},
    "Endurance":    {6: "???c?c?c?c?c????", 7: "????c?c?c?c?c???", 8: "???c?c?c?c?c????"},
}

# Petites formes pour les bestioles sauvages (8×6 pixels → 3 lignes)
BESTIOLES = [
    ["..bbbb..", ".bbbbbb.", "bebbbbeb", "bbbbbbbb", ".b.bb.b.", "b..bb..b"],
    ["b......b", ".bbbbbb.", "bbebbebb", "bbbbbbbb", ".bbbbbb.", "..b..b.."],
    ["...bb...", "..bbbb..", ".bebbeb.", "bbbbbbbb", "bb.bb.bb", "b......b"],
]


def overlay(base, ovl):
    rows = list(base)
    for i, mask in (ovl or {}).items():
        rows[i] = "".join(m if m != "?" else b for m, b in zip(mask, rows[i]))
    return rows


# Le compagnon d'une partie récente EST une espèce du bestiaire (state["espece_compagnon"], tirée avec l'œuf : oeufs.py).
# Ses stades suivent ceux du jeu (mêmes niveaux, mêmes noms) : Bébé → bebe, Ado → ado, Adulte → adulte.
# Une partie d'avant (sans espèce) garde la petite créature dessinée ci-dessus. Même règle sur Android (Sprites.kt).
STADE_ESPECE = {1: "bebe", 2: "ado", 3: "adulte"}
CARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz!#$%&*+-=@^~"   # un caractère par couleur
_CACHE_ESPECE = {}


def espece_compagnon(state):
    """L'espèce du compagnon (fiche du bestiaire), ou None (une partie d'avant : la créature d'origine)."""
    if not isinstance(state, dict) or not state.get("espece_compagnon"):
        return None
    from . import bestiaire as B
    return B.espece(state["espece_compagnon"])


def _dessin_espece(e, st, shiny=False):
    """(lignes de caractères, palette caractère → « #rrggbb ») de l'espèce e au stade st du jeu (1 à 3)."""
    cle = (e["id"], st, bool(shiny))
    if cle not in _CACHE_ESPECE:
        from . import bestiaire as B
        img = B.image(e, STADE_ESPECE.get(st, "adulte"))
        if not img:
            _CACHE_ESPECE[cle] = None
        else:
            w, h, octets, pal = img
            if shiny:
                pal = [B.decaler(c, 0.5) for c in pal]
            rows = ["".join(CARS[o - 1] if o else "." for o in octets[y * w:(y + 1) * w]) for y in range(h)]
            _CACHE_ESPECE[cle] = (rows, {CARS[k]: c for k, c in enumerate(pal[:len(CARS)])})
    return _CACHE_ESPECE[cle]


def get_sprite(state, st=None):
    """Le dessin de la créature (à son stade actuel, ou au stade st, pour rejouer une évolution)."""
    if st is None:
        st = core.stage(core.level(state["xp"]))
    if st == 0:
        from . import oeufs
        i = state.get("intro")
        return oeufs.petit(oeufs.type_de(state), len(i.get("faits", [])) if isinstance(i, dict) else 0)
    e = espece_compagnon(state)
    d = _dessin_espece(e, st, state.get("shiny")) if e else None
    if d:
        return d[0]
    if st == 1:
        return BABY
    br = state.get("branch") or core.dominant(state)
    if st == 2:
        return ADO_HEAD[br] + overlay(ADO, ADO_BODY.get(br))
    return ADULT_HEAD[br] + overlay(ADULT, ADULT_BODY.get(br))


def render_sprite(rows, pal):
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows]
    if len(rows) % 2:
        rows.append("." * w)
    out = []
    for i in range(0, len(rows), 2):      # 2 pixels verticaux par caractère « ▀ »
        s = ""
        for a, b in zip(rows[i], rows[i + 1]):
            ca, cb = pal.get(a), pal.get(b)
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += _fg(ca) + "▀" + RESET
            elif ca is None:
                s += _fg(cb) + "▄" + RESET
            else:
                s += _fg(ca) + _bg(cb) + "▀" + RESET
        out.append(s)
    return out, w


def _fg(c):
    """Couleur xterm-256 (entier) ou 24 bits (« #rrggbb », les œufs) → séquence du terminal."""
    if isinstance(c, str):
        from .bestiaire import fg24
        return fg24(c)
    return fg(c)


def _bg(c):
    if isinstance(c, str):
        from .bestiaire import bg24
        return bg24(c)
    return bg(c)


def body_color(state):
    if state.get("branch") and core.stage(core.level(state["xp"])) >= 2:
        return core.STAT_COLOR[state["branch"]]
    if not any(state["stats"].values()):
        return 141
    return core.STAT_COLOR[core.dominant(state)]


SHINY = {39: 220, 78: 51, 203: 129, 221: 255, 141: 219}   # couleur normale → couleur shiny


def palette(state, blink=False, st=None):
    """Caractère → couleur de la créature (st : un autre stade que l'actuel, ex. le bébé à la fin de l'éclosion)."""
    body = body_color(state)
    if state.get("shiny"):
        body = SHINY.get(body, 219)
    st = core.stage(core.level(state["xp"])) if st is None else st
    if st == 0:                                            # l'œuf : les couleurs de son dessin
        from . import oeufs
        return oeufs.palette(oeufs.type_de(state))
    e = espece_compagnon(state)
    if e:                                                  # une espèce : les couleurs de ses dessins (tous stades)
        pal = {}
        for s_ in STADE_ESPECE:
            d = _dessin_espece(e, s_, state.get("shiny"))
            if d:
                pal.update(d[1])
        if pal:
            return pal
    return {"b": body, "e": body if blink else 16, "k": 211, "m": 52 if state["hunger"] >= 30 else 16,
            "h": 180, "w": 230, "s": 180, "c": 136, "a": 250, "l": 51}


def creature(state, aura=None, phase=0):
    """(lignes, largeur) de la créature ; aura : palier d'aura (aura.py) dessiné autour de sa silhouette."""
    rows, pal = get_sprite(state), palette(state, random.random() < 0.15)
    if aura:
        from . import aura as A
        if A.visible(aura, terminal=True):
            w = max(len(r) for r in rows)
            couleurs = [None if pal.get(ch) is None else "#%02x%02x%02x" % x256(pal[ch])
                        for r in rows for ch in r.ljust(w, ".")]
            lignes = A.lignes(w, len(rows), couleurs, aura, phase)
            return lignes, w + 2 * A.PALIERS[aura].rayon
    return render_sprite(rows, pal)


def x256(n):
    """Couleur xterm-256 → (r, g, b) (une couleur « #rrggbb » des œufs passe telle quelle)."""
    if isinstance(n, str):
        return tuple(int(n[i:i + 2], 16) for i in (1, 3, 5))
    base = [(0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0), (0, 0, 128), (128, 0, 128), (0, 128, 128),
            (192, 192, 192), (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255),
            (255, 0, 255), (0, 255, 255), (255, 255, 255)]
    if n < 16:
        return base[n]
    if n < 232:
        n -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return lv[n // 36], lv[(n // 6) % 6], lv[n % 6]
    g = 8 + (n - 232) * 10
    return g, g, g


def png(path, rows, pal, echelle=12, marge=2):
    """Écrit la créature en PNG (transparent), sans aucune bibliothèque."""
    import struct
    import zlib
    w = max(len(r) for r in rows) + 2 * marge
    h = len(rows) + 2 * marge
    grille = ["." * w] * marge + ["." * marge + r.ljust(w - 2 * marge, ".") + "." * marge for r in rows] + ["." * w] * marge
    raw = bytearray()
    for y in range(h * echelle):
        raw.append(0)
        ligne = grille[y // echelle]
        for x in range(w * echelle):
            c = pal.get(ligne[x // echelle])
            raw += bytes(x256(c)) + b"\xff" if c is not None else b"\x00\x00\x00\x00"

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w * echelle, h * echelle, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def bestiole(index, couleur):
    return render_sprite(BESTIOLES[index % len(BESTIOLES)], {"b": couleur, "e": 16})[0]


def _indexer(rows, pal):
    """Lignes de caractères + palette xterm → (largeur, hauteur, octets, palette en entiers 0xRRGGBB)."""
    w = max(len(r) for r in rows)
    codes, octets = [], bytearray()
    for r in rows:
        for ch in r.ljust(w, "."):
            c = pal.get(ch)
            if c is None:
                octets.append(0)
                continue
            if c not in codes:
                codes.append(c)
            octets.append(codes.index(c) + 1)
    rgb = [(lambda t: (t[0] << 16) | (t[1] << 8) | t[2])(x256(c)) for c in codes]
    return w, len(rows), bytes(octets), rgb


def _recadrer(W, H, frames):
    """Coupe les bords vides communs à toutes les images (hauteur gardée paire pour les demi-blocs)."""
    x0, y0, x1, y1 = W, H, -1, -1
    for f in frames:
        for y in range(H):
            ligne = f[y * W:(y + 1) * W]
            if any(ligne):
                y0, y1 = min(y0, y), max(y1, y)
                for x in range(W):
                    if ligne[x]:
                        x0, x1 = min(x0, x), max(x1, x)
    if x1 < 0:
        return W, H, frames
    y0 -= y0 % 2
    nw, nh = x1 - x0 + 1, y1 - y0 + 1
    nh += nh % 2
    out = []
    for f in frames:
        b = bytearray(nw * nh)
        for y in range(nh):
            if y0 + y < H:
                b[y * nw:(y + 1) * nw] = f[(y0 + y) * W + x0:(y0 + y) * W + x0 + nw]
        out.append(bytes(b))
    return nw, nh, out


def animation(state, nom, aura=None):
    """La créature principale joue une animation automatique (moteur anim_auto) : (lignes par image, ips).
    aura : palier d'aura (aura.py) qui respire autour d'elle pendant l'animation."""
    from . import anim_auto
    from .bestiaire import lignes_image
    pal = palette(state)
    st = core.stage(core.level(state["xp"]))
    w, h, o, p = _indexer(get_sprite(state, st), pal)
    de = None
    if nom == "evolution" and st > 0:
        de = _indexer(get_sprite(state, st - 1), palette(state, st=st - 1))    # l'image d'avant, ses couleurs
    W, H, frames, pal2, _ = anim_auto._calculer(w, h, o, p, nom, de)
    W, H, frames = _recadrer(W, H, frames)
    hexa = ["#%06x" % c for c in pal2]
    if aura:
        from . import aura as A
        if A.visible(aura, terminal=True):
            return [A.lignes(W, H, A.depuis_octets(W, H, f, hexa), aura, k) for k, f in enumerate(frames)], anim_auto.IPS
    return [lignes_image(W, H, f, hexa) for f in frames], anim_auto.IPS


def bar(value, maximum, width=10):
    n = max(0, min(width, round(width * value / maximum))) if maximum else 0
    return "█" * n + "░" * (width - n)
