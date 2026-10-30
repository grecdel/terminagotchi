"""L'intro en images, dans le terminal (même déroulé qu'Android : Scenes.kt ; maquettes docs/maquettes/intro_*.png).

Les trois illustrations (donnees/illustrations : le Terminaworld vivant, endormi, le camp de base) sont rangées en
240×135 dans illustrations.bin (fabriqué par donnees/illustrations/generer_intro.py) et dessinées en demi-blocs :
chaque caractère ▀ montre 2 pixels (le haut en couleur du texte, le bas en couleur du fond).

Le camp de base, pendant l'intro (paramètres : intro.json « illustrations ») :
  1. il dort : la même image, désaturée, assombrie, bleuie par le code (endormir) ;
  2. à la 1re commande de la liste, il se réveille : l'écran de l'ordinateur s'allume, la lumière remonte les câbles
     puis les veines de l'arbre (chemins), la couleur revient derrière elle (carte_eveil : l'instant où chaque pixel
     retrouve sa couleur) ;
  3. l'œuf du type tiré arrive dans le nid « en téléchargement » : ligne de pixels par ligne de pixels, la ligne en
     cours scintille en vert, le bas n'est qu'un contour pointillé ; chaque commande de la liste en apporte un
     morceau (cibles : 37 %, 62 %, 87 %, 100 %) ; petit éclat quand il est complet ;
  4. il éclot : la coquille reste dans le nid, le vrai bébé de l'espèce tirée sort (sprites.get_sprite, stade 1).
moment(state, t) dit où en est l'intro à l'instant t ; scene(state, W, H, t) en fait les pixels ; lignes() les
demi-blocs. Repli : terminal trop petit → l'œuf seul (26×26) ; sans couleurs 24 bits → 256 couleurs ; sans couleurs
du tout (NO_COLOR, TERM=dumb, console linux) → pas d'image, le texte seul.
Tests : pc/outils/test_intro.py.
"""
import math
import os
import pkgutil
import struct
import zlib

_IMG = {}
_CACHE = {}
VERT = (92, 255, 149)
VERT_PALE = (220, 255, 225)


# ---------------------------------------------------------------- les données
def params():
    from . import intro
    return intro.donnees().get("illustrations", {})


def camp():
    return params().get("camp", {})


def _charger():
    if _IMG:
        return
    try:
        data = pkgutil.get_data(__package__, "illustrations.bin")
    except OSError:
        data = None
    if not data or data[:4] != b"TGI1":
        _IMG["_"] = None
        return
    i = 4
    while i < len(data):
        n = data[i]
        nom = data[i + 1:i + 1 + n].decode()
        i += 1 + n
        w, h, lg = struct.unpack(">HHI", data[i:i + 8])
        i += 8
        _IMG[nom] = (w, h, zlib.decompress(data[i:i + lg]))
        i += lg


def disponible(nom="camp"):
    _charger()
    return _IMG.get(nom) is not None


def reduire(nom, W, H, posx=0.5):
    """L'illustration nom (« monde », « dort », « camp ») en W×H pixels [(r, g, b)] : recadrée (cover, posx = où on
    coupe en largeur) puis moyennée (chaque pixel = la moyenne des pixels d'origine qu'il couvre)."""
    cle = ("r", nom, W, H, posx)
    if cle in _CACHE:
        return _CACHE[cle]
    _charger()
    w, h, rgb = _IMG[nom]
    e = max(W / w, H / h)                     # cover
    cw, ch = W / e, H / e
    x0 = (w - cw) * posx
    y0 = (h - ch) / 2
    out = []
    for y in range(H):
        sy0 = y0 + y * ch / H
        sy1 = y0 + (y + 1) * ch / H
        ya, yb = int(sy0), max(int(sy0) + 1, int(math.ceil(sy1)))
        for x in range(W):
            sx0 = x0 + x * cw / W
            sx1 = x0 + (x + 1) * cw / W
            xa, xb = int(sx0), max(int(sx0) + 1, int(math.ceil(sx1)))
            r = g = b = n = 0
            for yy in range(ya, min(yb, h)):
                base = yy * w
                for xx in range(xa, min(xb, w)):
                    k = (base + xx) * 3
                    r += rgb[k]
                    g += rgb[k + 1]
                    b += rgb[k + 2]
                    n += 1
            n = max(1, n)
            out.append((r // n, g // n, b // n))
    if len(_CACHE) > 24:
        _CACHE.clear()
    _CACHE[cle] = out
    return out


def endormir(px):
    """Le camp endormi : la même image, presque sans couleur, sombre et bleutée (intro.json camp.dort)."""
    d = camp().get("dort", {})
    sat, lum = d.get("couleur", 0.15), d.get("lumiere", 0.38)
    bl, m = d.get("bleu", [20, 28, 60]), d.get("melange", 0.25)
    out = []
    for r, g, b in px:
        gris = 0.299 * r + 0.587 * g + 0.114 * b
        c = [(gris + (v - gris) * sat) * lum for v in (r, g, b)]
        out.append(tuple(int(c[i] * (1 - m) + bl[i] * m) for i in range(3)))
    return out


# ---------------------------------------------------------------- le réveil du camp
def _echantillons():
    """Les points des chemins de lumière (coordonnées de l'image d'origine) et l'instant où la lumière y passe."""
    c = camp()
    v = c.get("vitesse", 620)
    pts = [(c.get("ordi", [312, 408])[0], c.get("ordi", [312, 408])[1], 0.15)]
    for ch in c.get("chemins", []):
        t0, p = ch["t"], ch["pts"]
        s = 0.0
        for (xa, ya), (xb, yb) in zip(p, p[1:]):
            lg = math.hypot(xb - xa, yb - ya)
            n = max(1, int(lg // 14))
            for k in range(n):
                f = k / n
                pts.append((xa + (xb - xa) * f, ya + (yb - ya) * f, t0 + (s + lg * f) / v))
            s += lg
        pts.append((p[-1][0], p[-1][1], t0 + s / v))
    return pts


def carte_eveil(W, H, posx=0.5):
    """[instant (s) où chaque pixel retrouve sa couleur] pour une vue W×H : la couleur part des points où passe la
    lumière (couleur_vitesse px/s) ; tout est revenu à « fin ». Calculée sur une grille de 48×27, puis lissée."""
    cle = ("e", W, H, posx)
    if cle in _CACHE:
        return _CACHE[cle]
    c = camp()
    tw, th = c.get("taille", [1533, 863])
    cv, fin = c.get("couleur_vitesse", 360), c.get("fin", 2.9)
    pts = _echantillons()
    GW, GH = 48, 27
    grille = []
    for gy in range(GH):
        y = (gy + 0.5) * th / GH
        for gx in range(GW):
            x = (gx + 0.5) * tw / GW
            grille.append(min(fin, min(t + math.hypot(x - px, y - py) / cv for px, py, t in pts)))
    e = max(W / tw, H / th)
    x0 = (tw - W / e) * posx
    y0 = (th - H / e) / 2
    out = []
    for y in range(H):
        sy = (y0 + (y + 0.5) / e) / th * GH - 0.5
        ya = min(GH - 1, max(0, int(math.floor(sy))))
        yb = min(GH - 1, ya + 1)
        fy = min(1.0, max(0.0, sy - ya))
        for x in range(W):
            sx = (x0 + (x + 0.5) / e) / tw * GW - 0.5
            xa = min(GW - 1, max(0, int(math.floor(sx))))
            xb = min(GW - 1, xa + 1)
            fx = min(1.0, max(0.0, sx - xa))
            a = grille[ya * GW + xa] * (1 - fx) + grille[ya * GW + xb] * fx
            b = grille[yb * GW + xa] * (1 - fx) + grille[yb * GW + xb] * fx
            out.append(a * (1 - fy) + b * fy)
    _CACHE[cle] = out
    return out


def lumieres(t):
    """Les lumières du réveil à l'instant t (s) : [(x, y, intensité)] en coordonnées de l'image d'origine — l'écran de
    l'ordinateur qui s'allume, puis la tête de chaque chemin de lumière (et un reste qui s'éteint au bout)."""
    c = camp()
    v = c.get("vitesse", 620)
    ox, oy = c.get("ordi", [312, 408])
    out = []
    if t >= 0:
        out.append((ox, oy, min(1.0, t / 0.5) * (1.0 if t < c.get("duree", 3.4) - 0.6 else 0.6)))
    for ch in c.get("chemins", []):
        p = ch["pts"]
        s = (t - ch["t"]) * v
        if s < 0:
            continue
        for (xa, ya), (xb, yb) in zip(p, p[1:]):
            lg = math.hypot(xb - xa, yb - ya)
            if s <= lg:
                f = s / max(1.0, lg)
                out.append((xa + (xb - xa) * f, ya + (yb - ya) * f, 1.0))
                break
            s -= lg
        else:
            reste = 1 - s / (v * 0.5)
            if reste > 0:
                out.append((p[-1][0], p[-1][1], reste))
    return out


# ---------------------------------------------------------------- le déroulé (où en est l'intro à l'instant t)
def cible(n):
    """Le pourcentage de l'œuf reçu après n commandes de la liste (0 : pas encore commencé)."""
    c = params().get("telechargement", {}).get("cibles", [0, 37, 62, 87, 100])
    return c[max(0, min(n, len(c) - 1))]


def moment(state, t):
    """Où en est l'intro de cette partie à l'instant t (secondes, comme time.time()) :
    {phase: dort | eveil | telech | eclat | eclot | ne, te: secondes depuis le début de la phase, pct, k: image}."""
    from . import intro
    i = intro.i_(state)
    faits = len(i.get("faits", []))
    fini = i.get("etat") == "fini"
    c = camp()
    tl = params().get("telechargement", {})
    duree, vit = c.get("duree", 3.4), tl.get("vitesse", 24)
    evt = i.get("evt") or [faits, 0]
    tv = evt[1] if isinstance(evt, (list, tuple)) and len(evt) > 1 and evt[1] else 0
    te = i.get("eveil") or (tv if faits == 1 else 0)
    if faits == 0 and not fini:
        return {"phase": "dort", "te": 0, "pct": 0, "k": 0}
    if te and t - te < duree:
        return {"phase": "eveil", "te": t - te, "pct": 0, "k": int((t - te) * 10)}
    n = len(intro.checklist()) if fini else faits
    if n <= 1:
        depart, de = te + duree, 0
    else:
        depart, de = max(tv, te + duree) if te else tv, cible(n - 1)
    a = cible(n)
    pct = a if not depart else min(a, de + max(0.0, t - depart) * vit)
    k = int(t * 12)
    if not fini or pct < 100:
        return {"phase": "telech", "te": t - depart, "pct": pct, "k": k}
    t100 = (depart or t) + (100 - de) / vit
    x = t - t100 if depart else 99
    if x < tl.get("eclat", 0.7):
        return {"phase": "eclat", "te": x, "pct": 100, "k": int(x * 10)}
    x -= tl.get("eclat", 0.7)
    if x < tl.get("eclot", 1.0):
        return {"phase": "eclot", "te": x, "pct": 100, "k": int(x * 6 / tl.get("eclot", 1.0))}
    return {"phase": "ne", "te": x, "pct": 100, "k": k}


# ---------------------------------------------------------------- l'œuf « en téléchargement »
def _h(x, y, k):
    """Un nombre pseudo-aléatoire de [0, 1) qui ne dépend que de (x, y, k) : le scintillement est le même à chaque
    rendu d'une même image."""
    v = (x * 73856093 ^ y * 19349663 ^ k * 83492791) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 65536


def coupe(opaque, H, W, pct):
    """La ligne en cours de réception : la première ligne où les pixels reçus atteignent pct % de l'œuf."""
    par_ligne = [sum(1 for x in range(W) if opaque(x, y)) for y in range(H)]
    tot = max(1, sum(par_ligne))
    acc = 0
    for y in range(H):
        acc += par_ligne[y]
        if par_ligne[y] and acc / tot >= pct / 100:
            return y
    return H


def telecharge(px, W, H, pct, k, F=1):
    """L'œuf reçu à pct % : px = [(r, g, b) ou None] (W×H) → [(r, g, b, a) ou None]. Le haut est reçu ; la ligne en
    cours (épaisseur F//2 au moins 1) scintille en vert ; juste au-dessus, quelques pixels clignent ; le bas n'est
    qu'un contour fantôme en pointillés (et un voile très léger). F = finesse (1 : l'œuf du terminal, 4 : l'œuf fin)."""
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[y * W + x] is not None   # noqa: E731
    if pct >= 100:
        return [None if p is None else (p[0], p[1], p[2], 255) for p in px]
    cut = coupe(op, H, W, pct) if pct > 0 else -1
    ep = max(1, F // 2)
    out = [None] * (W * H)
    for y in range(H):
        for x in range(W):
            p = px[y * W + x]
            if p is None:
                continue
            if y < cut - ep + 1:
                q = (p[0], p[1], p[2], 255)
                if y >= cut - 6 * ep and _h(x, y, k) < 0.10 * (6 * ep - (cut - y)) / (6 * ep):
                    q = (150, 255, 170, 255)
                out[y * W + x] = q
            elif cut - ep + 1 <= y <= cut and pct > 0:
                r = _h(x, y, k + 7)
                out[y * W + x] = VERT + (255,) if r < 0.55 else VERT_PALE + (255,) if r < 0.75 else (p[0], p[1], p[2], 255)
            else:
                bord = any(not op(x + a, y + b) for a, b in ((ep, 0), (-ep, 0), (0, ep), (0, -ep)))
                if bord and ((y // ep) % 2 == 0 if F > 1 else (x + y) % 2 == 0):
                    out[y * W + x] = (60, 190, 110, 230) if F == 1 else VERT + (230,)
                elif not bord and F == 1:
                    out[y * W + x] = (0, 0, 0, 120)          # terminal : le bas de l'œuf, un voile sombre
                elif not bord and ((x // ep + y // ep) % 9 == 0):
                    out[y * W + x] = VERT + (28,)
    if 0 <= cut < H and pct > 0:                     # quelques pixels verts qui sautent hors de la ligne
        for x in range(W):
            if op(x, cut) and _h(x, cut, k + 3) < 0.12:
                yy = cut + (-3, -2, 2, 3, 4)[int(_h(x, 0, k) * 5)] * ep
                if 0 <= yy < H:
                    out[yy * W + x] = VERT + ((120, 200, 255)[int(_h(x, 1, k) * 3)],)
    return out


# ---------------------------------------------------------------- composer une scène
def _hex(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _grille_oeuf(rows, pal):
    """Lignes de caractères (oeufs.py) → [(r, g, b) ou None], W, H."""
    W = max(len(r) for r in rows)
    H = len(rows)
    out = []
    for r in rows:
        for x in range(W):
            ch = r[x] if x < len(r) else "."
            c = pal.get(ch)
            out.append(_hex(c) if isinstance(c, str) else None)
    return out, W, H


def _poser(fond, W, H, calque, cw, ch, x0, y0):
    """Pose un calque [(r, g, b, a) ou None] (cw×ch) sur fond (W×H) au point (x0, y0)."""
    for y in range(ch):
        Y = y0 + y
        if not 0 <= Y < H:
            continue
        for x in range(cw):
            X = x0 + x
            q = calque[y * cw + x]
            if q is None or not 0 <= X < W:
                continue
            a = q[3] / 255 if len(q) > 3 else 1
            f = fond[Y * W + X]
            fond[Y * W + X] = tuple(int(f[i] * (1 - a) + q[i] * a) for i in range(3))


def _lueur(fond, W, H, cx, cy, r, couleur, force):
    """Une lueur ronde (ajoutée) centrée en (cx, cy), de rayon r pixels."""
    for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1)):
        for x in range(max(0, int(cx - r)), min(W, int(cx + r) + 1)):
            d = math.hypot(x + 0.5 - cx, (y + 0.5 - cy)) / r
            if d < 1:
                f = (1 - d) ** 2 * force
                p = fond[y * W + x]
                fond[y * W + x] = tuple(min(255, int(p[i] + couleur[i] * f)) for i in range(3))


def _vers(W, H, posx=0.5):
    """(x, y) d'origine → (x, y) dans la vue W×H (même recadrage que reduire)."""
    tw, th = camp().get("taille", [1533, 863])
    e = max(W / tw, H / th)
    x0 = (tw - W / e) * posx
    y0 = (th - H / e) / 2
    return lambda x, y: ((x - x0) * e, (y - y0) * e)


def scene(state, W, H, t, m=None, posx=0.5):
    """Les pixels [(r, g, b)] du camp de base (W×H) à l'instant t : endormi, qui se réveille, l'œuf qui arrive, qui
    éclot, le bébé. m : le moment (sinon moment(state, t))."""
    from . import oeufs
    m = m or moment(state, t)
    base = reduire("camp", W, H, posx)
    ph = m["phase"]
    if ph == "dort":
        return endormir(base)
    vers = _vers(W, H, posx)
    if ph == "eveil":
        dort = endormir(base)
        tm = carte_eveil(W, H, posx)
        fd = camp().get("fondu", 0.4)
        te = m["te"]
        px = []
        for i, (a, b) in enumerate(zip(base, dort)):
            f = (te - tm[i]) / fd
            if f <= 0:
                px.append(b)
            elif f >= 1:
                px.append(a)
            else:
                px.append(tuple(int(b[j] + (a[j] - b[j]) * f) for j in range(3)))
        for x, y, f in lumieres(te):
            X, Y = vers(x, y)
            _lueur(px, W, H, X, Y, max(2.5, W * 0.03), VERT, 0.9 * f)
            _lueur(px, W, H, X, Y, max(1.2, W * 0.008), (255, 255, 255), 0.8 * f)
        return px
    px = list(base)
    ty = oeufs.type_de(state)
    c = camp()
    o = c.get("oeuf", {"x": 545, "y": 196, "cote": 430})
    ax, ay = vers(o["x"] + o["cote"] / 2, o["y"] + o["cote"] * 24.5 / 26)     # le bas de l'œuf, au fond du nid
    if ph in ("telech", "eclat", "eclot"):
        if ph == "telech":
            rows = oeufs.image(ty, 0)
            g, gw, gh = _grille_oeuf(rows, oeufs.palette(ty))
            cal = telecharge(g, gw, gh, m["pct"], m["k"], 1)
            _lueur(px, W, H, ax, ay - gh * 0.45, gw * 0.9, VERT, 0.18 + 0.1 * (m["k"] % 2))
        else:
            rows = oeufs.image(ty, 0, "brille", m["k"]) if ph == "eclat" else oeufs.image(ty, 3, "eclot", min(5, m["k"]))
            g, gw, gh = _grille_oeuf(rows, oeufs.palette(ty))
            cal = [None if p is None else p + (255,) for p in g]
            _lueur(px, W, H, ax, ay - gh * 0.45, gw * 1.1, (255, 240, 150), 0.45 if ph == "eclat" else 0.3)
        _poser(px, W, H, cal, gw, gh, int(round(ax - gw / 2)), int(round(ay - 24.5)))
        return px
    # ne : la coquille dans le nid, le bébé à côté, des étincelles
    cq = c.get("coquille", {"x": 390, "y": 300, "cote": 300})
    qx, qy = vers(cq["x"] + cq["cote"] / 2, cq["y"] + cq["cote"] * 24.5 / 26)
    bb = c.get("bebe", {"x": 800, "bas": 610, "haut": 320})
    bx, by = vers(bb["x"], bb["bas"])
    _lueur(px, W, H, bx, by - W * 0.12, W * 0.2, (255, 240, 150), 0.35)
    g, gw, gh = _grille_oeuf(oeufs.image(ty, 3, "eclot", 5), oeufs.palette(ty))
    _poser(px, W, H, [None if p is None else p + (255,) for p in g], gw, gh, int(round(qx - gw / 2)), int(round(qy - 24.5)))
    try:
        from . import sprites
        rows = sprites.get_sprite(state, 1)
        pal = sprites.palette(state, st=1)
        cal, bw, bh = [], max(len(r) for r in rows), len(rows)
        for r in rows:
            for x in range(bw):
                ch = r[x] if x < len(r) else "."
                v = pal.get(ch)
                cal.append(None if v is None else (sprites.x256(v) + (255,)))
        _poser(px, W, H, cal, bw, bh, int(round(bx - bw / 2)), int(round(by - bh)))
    except Exception:                                # noqa: BLE001  (une partie bizarre : pas de bébé, pas d'erreur)
        pass
    for j, (dx, dy) in enumerate(((-170, -230), (150, -250), (210, -120), (-230, -90), (60, -300), (-60, -280))):
        if (m["k"] + j) % 3:
            X, Y = vers(bb["x"] + dx, bb["bas"] - 60 + dy)
            _lueur(px, W, H, X, Y, max(1.5, W * 0.012), (255, 247, 160), 1.2)
    return px


# ---------------------------------------------------------------- les couleurs du terminal
def mode_couleurs(flux=None):
    """« 24 » (couleurs vraies), « 256 », ou None (pas de couleurs : NO_COLOR, TERM=dumb, la console linux).
    TG_COULEURS=24|256|0 force le choix."""
    force = os.environ.get("TG_COULEURS")
    if force in ("24", "256"):
        return force
    if force == "0" or os.environ.get("NO_COLOR") is not None:
        return None
    term = os.environ.get("TERM", "")
    if term in ("dumb", "linux", "vt100", "vt220"):
        return None
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit") or os.environ.get("WT_SESSION") \
            or os.environ.get("KONSOLE_VERSION") or os.environ.get("VTE_VERSION", "0").isdigit() and int(os.environ.get("VTE_VERSION", "0")) >= 3600 \
            or os.environ.get("TERM_PROGRAM") in ("iTerm.app", "WezTerm", "vscode", "Hyper", "ghostty") \
            or any(x in term for x in ("kitty", "alacritty", "wezterm", "ghostty", "foot", "direct", "truecolor")):
        return "24"
    try:
        tty = (flux or __import__("sys").stdout).isatty()
    except (AttributeError, ValueError, OSError):
        tty = False
    return "256" if tty else "24"          # dans un fichier (tests, captures) : les vraies couleurs


_NIV = (0, 95, 135, 175, 215, 255)


def _x256(c):
    """(r, g, b) → la couleur xterm-256 la plus proche (le cube 6×6×6 ou les gris)."""
    q = [min(range(6), key=lambda i: abs(_NIV[i] - v)) for v in c]
    cube = tuple(_NIV[i] for i in q)
    gris = sum(c) // 3
    gi = max(0, min(23, round((gris - 8) / 10)))
    gv = 8 + gi * 10
    if sum((a - gv) ** 2 for a in c) < sum((a - b) ** 2 for a, b in zip(c, cube)):
        return 232 + gi
    return 16 + 36 * q[0] + 6 * q[1] + q[2]


def lignes(px, W, H, mode="24", marge=""):
    """Pixels (W×H, H pair) → lignes de demi-blocs ▀ (haut = texte, bas = fond)."""
    out = []
    for y in range(0, H - 1, 2):
        s = marge
        avant = None
        for x in range(W):
            a, b = px[y * W + x], px[(y + 1) * W + x]
            if mode == "24":
                code = f"\x1b[38;2;{a[0]};{a[1]};{a[2]};48;2;{b[0]};{b[1]};{b[2]}m"
            else:
                code = f"\x1b[38;5;{_x256(a)};48;5;{_x256(b)}m"
            if code != avant:
                s += code
                avant = code
            s += "▀"
        out.append(s + "\x1b[0m")
    return out


def taille(cols, rangs, reserve, maxi=120):
    """(W, H) en pixels de la plus grande scène 16:9 qui tient (cols colonnes, rangs lignes dont reserve pour le
    texte), ou None si elle serait trop petite pour se lire (moins de 48 colonnes)."""
    W = min(maxi, cols - 4)
    H = int(W * 9 / 16) // 2 * 2
    if H // 2 > rangs - reserve:
        H = max(0, (rangs - reserve) * 2)
        W = int(H * 16 / 9)
    if W < 48 or H < 26:
        return None
    return W, H


def illustration(nom, W, H, mode="24", marge=""):
    """Une illustration entière (« monde », « dort », « camp_dort ») en demi-blocs, ou [] si elle manque."""
    if not disponible("camp" if nom == "camp_dort" else nom):
        return []
    px = reduire("camp" if nom == "camp_dort" else nom, W, H)
    if nom == "camp_dort":
        px = endormir(px)
    return lignes(px, W, H, mode, marge)


def oeuf_seul(state, m, mode="24", marge=""):
    """Le repli d'un petit terminal : l'œuf seul (26×26) qui arrive, sur le fond du terminal."""
    from . import oeufs
    ty = oeufs.type_de(state)
    ph = m["phase"]
    if ph in ("dort", "eveil"):
        return []
    if ph == "telech":
        g, gw, gh = _grille_oeuf(oeufs.image(ty, 0), oeufs.palette(ty))
        cal = telecharge(g, gw, gh, m["pct"], m["k"], 1)
    else:
        rows = oeufs.image(ty, 0, "brille", m["k"]) if ph == "eclat" else oeufs.image(ty, 3, "eclot", min(5, m["k"]))
        g, gw, gh = _grille_oeuf(rows, oeufs.palette(ty))
        cal = [None if p is None else p + (255,) for p in g]
    fond = (12, 14, 18)
    px = [fond] * (gw * gh)
    _poser(px, gw, gh, cal, gw, gh, 0, 0)
    if gh % 2:
        px += [fond] * gw
    return lignes(px, gw, gh + gh % 2, mode, marge)
