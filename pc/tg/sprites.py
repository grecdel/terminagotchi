"""Pixel art : la créature à chaque stade/forme, et les bestioles sauvages."""
import random

from . import core
from .plateforme import RESET, bg, fg

EGG_SPRITE = [
    "....wwww....",
    "...wwwwww...",
    "..wwwswwww..",
    "..wwwwwwsw..",
    ".wwswwwwwww.",
    ".wwwwwwwsww.",
    ".wwwwswwwww.",
    ".wwwwwwwwww.",
    "..wwwwwwww..",
    "...wwwwww...",
]
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


def get_sprite(state):
    st = core.stage(core.level(state["xp"]))
    if st == 0:
        return EGG_SPRITE
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
                s += fg(ca) + "▀" + RESET
            elif ca is None:
                s += fg(cb) + "▄" + RESET
            else:
                s += fg(ca) + bg(cb) + "▀" + RESET
        out.append(s)
    return out, w


def body_color(state):
    if state.get("branch") and core.stage(core.level(state["xp"])) >= 2:
        return core.STAT_COLOR[state["branch"]]
    if not any(state["stats"].values()):
        return 141
    return core.STAT_COLOR[core.dominant(state)]


def palette(state, blink=False):
    body = body_color(state)
    return {"b": body, "e": body if blink else 16, "k": 211, "m": 52 if state["hunger"] >= 30 else 16,
            "h": 180, "w": 230, "s": 180, "c": 136, "a": 250, "l": 51}


def creature(state):
    return render_sprite(get_sprite(state), palette(state, random.random() < 0.15))


def x256(n):
    """Couleur xterm-256 → (r, g, b)."""
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


def bar(value, maximum, width=10):
    n = max(0, min(width, round(width * value / maximum))) if maximum else 0
    return "█" * n + "░" * (width - n)
