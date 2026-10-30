"""L'intro en images, dans le terminal (même déroulé qu'Android : Scenes.kt ; maquettes docs/maquettes/intro_*.png).

Les trois illustrations (donnees/illustrations : le Terminaworld vivant, endormi, le camp de base) sont rangées en
384×216 dans illustrations.bin (fabriqué par donnees/illustrations/generer_intro.py). Le dessin choisit le plus
détaillé que le terminal sait montrer (rendu(), détecté une fois : capacites()) :
  - une vraie image : protocole graphique de Kitty (kitty, WezTerm, Ghostty, Konsole), image en ligne d'iTerm2,
    sixel (foot, xterm, mlterm, WezTerm, Konsole, le VTE de GNOME Terminal / Ptyxis s'il les accepte) ;
  - sinon du texte : sextants (2×3 « sous-pixels » par case, Unicode 13), quadrants (2×2), demi-blocs (1×2) ; pour
    chaque case, les deux couleurs qui conviennent le mieux. TG_IMAGES=kitty|iterm|sixel|sextants|quadrants|demi force.

Le camp de base, pendant l'intro (paramètres : intro.json « illustrations ») :
  1. il dort : la même image, désaturée, assombrie, bleuie par le code (endormir) ;
  2. à la 1re commande de la liste, il se réveille : l'écran de l'ordinateur s'allume, la lumière remonte les câbles
     puis les veines de l'arbre (chemins), la couleur revient derrière elle (carte_eveil : l'instant où chaque pixel
     retrouve sa couleur) ;
  3. l'œuf du type tiré arrive dans le nid « en téléchargement » : ligne de pixels par ligne de pixels, la ligne en
     cours scintille en vert, le bas n'est qu'un contour pointillé ; chaque commande de la liste en apporte un
     morceau (cibles : 37 %, 62 %, 87 %, 100 %) ; petit éclat quand il est complet ;
  4. il éclot : il se fêle, la coquille éclate et s'ouvre (ECLOT), puis le vrai bébé de l'espèce tirée apparaît en
     fondu digital (pixels qui arrivent dans un ordre de Bayer mêlé de hasard, lueur verte « matrix », lignes de
     balayage), et seulement ensuite « … est né ! ».
moment(state, t) dit où en est l'intro à l'instant t ; scene(state, W, H, t) en fait les pixels ; dessiner() les
lignes du terminal. Repli : terminal trop petit → l'œuf seul (26×26) ; sans couleurs 24 bits → 256 couleurs ; sans couleurs
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


def reduire(nom, W, H, posx=0.5, pa=1.0):
    """L'illustration nom (« monde », « dort », « camp ») en W×H pixels [(r, g, b)] : recadrée (cover, posx = où on
    coupe en largeur) puis moyennée (chaque pixel = la moyenne des pixels d'origine qu'il couvre). pa = largeur / hauteur
    d'un pixel à l'écran (1 : carré ; sextants 0,75 ; quadrants 0,5)."""
    cle = ("r", nom, W, H, posx, pa)
    if cle in _CACHE:
        return _CACHE[cle]
    _charger()
    w, h, rgb = _IMG[nom]
    e = max(W * pa / w, H / h)                # cover
    cw, ch = W * pa / e, H / e
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


def endormi(nom, W, H, posx=0.5, pa=1.0):
    """reduire puis endormir, gardé en mémoire (le camp endormi revient à chaque image du réveil)."""
    cle = ("d", nom, W, H, posx, pa)
    if cle not in _CACHE:
        _CACHE[cle] = endormir(reduire(nom, W, H, posx, pa))
    return _CACHE[cle]


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


def carte_eveil(W, H, posx=0.5, pa=1.0):
    """[instant (s) où chaque pixel retrouve sa couleur] pour une vue W×H : la couleur part des points où passe la
    lumière (couleur_vitesse px/s) ; tout est revenu à « fin ». Calculée sur une grille de 48×27, puis lissée."""
    cle = ("e", W, H, posx, pa)
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
    e = max(W * pa / tw, H / th)
    x0 = (tw - W * pa / e) * posx
    y0 = (th - H / e) / 2
    out = []
    for y in range(H):
        sy = (y0 + (y + 0.5) / e) / th * GH - 0.5
        ya = min(GH - 1, max(0, int(math.floor(sy))))
        yb = min(GH - 1, ya + 1)
        fy = min(1.0, max(0.0, sy - ya))
        for x in range(W):
            sx = (x0 + (x + 0.5) * pa / e) / tw * GW - 0.5
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
    ecl, eco, fon = tl.get("eclat", 0.7), tl.get("eclot", 1.4), tl.get("fondu", 1.6)
    if x < ecl:
        return {"phase": "eclat", "te": x, "pct": 100, "k": int(x * 10)}
    x -= ecl
    if x < eco:
        return {"phase": "eclot", "te": x, "pct": 100, "k": min(len(ECLOT) - 1, int(x / eco * len(ECLOT)))}
    x -= eco
    if x < fon:
        return {"phase": "fondu", "te": x, "pct": 100, "k": k, "f": x / fon}
    return {"phase": "ne", "te": x - fon, "pct": 100, "k": k}


# l'éclosion, image par image : il se fêle (une, deux, trois fêlures qui éclairent), tremble, la coquille s'ouvre
ECLOT = [(1, "craque", 0), (1, "craque", 1), (2, "craque", 0), (2, "craque", 1), (3, "craque", 0), (3, "craque", 1),
         (3, "craque", 2), (3, "remue", 0), (3, "remue", 2), (3, "eclot", 0), (3, "eclot", 1), (3, "eclot", 3),
         (3, "eclot", 4), (3, "eclot", 5)]
OUVERT = 11          # à partir de cette image, la coquille est ouverte (l'éclair)


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


def _lueur(fond, W, H, cx, cy, r, couleur, force, pa=1.0):
    """Une lueur ronde (ajoutée) centrée en (cx, cy), de rayon r pixels (en hauteur ; r / pa en largeur)."""
    rx = r / pa
    for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1)):
        for x in range(max(0, int(cx - rx)), min(W, int(cx + rx) + 1)):
            d = math.hypot((x + 0.5 - cx) * pa, (y + 0.5 - cy)) / r
            if d < 1:
                f = (1 - d) ** 2 * force
                p = fond[y * W + x]
                fond[y * W + x] = tuple(min(255, int(p[i] + couleur[i] * f)) for i in range(3))


def _vers(W, H, posx=0.5, pa=1.0):
    """(x, y) d'origine → (x, y) dans la vue W×H (même recadrage que reduire)."""
    tw, th = camp().get("taille", [1533, 863])
    e = max(W * pa / tw, H / th)
    x0 = (tw - W * pa / e) * posx
    y0 = (th - H / e) / 2
    return lambda x, y: ((x - x0) * e / pa, (y - y0) * e)


# ---------------------------------------------------------------- les œufs fins (oeufs_fins.json, comme Oeufs.fin)
_FIN = {}


def _fins():
    if not _FIN:
        import json
        try:
            _FIN.update(json.loads(pkgutil.get_data(__package__, "oeufs_fins.json").decode("utf-8")))
        except (OSError, ValueError):
            _FIN["_"] = None
    return _FIN if _FIN.get("types") else None


def oeuf_fin(ty, fele, nom="", k=0):
    """Une image fine de l'œuf (104×104, quatre fois plus détaillée que oeufs.image, même animation : fele 0 à 3,
    nom remue / brille / craque / eclot) : ([(r, g, b) ou None], W, H), ou None. Même calcul qu'Oeufs.fin (Android)."""
    d = _fins()
    if not d:
        return None
    types = d["types"]
    ty = ty if ty in types else next(iter(types))
    x = types[ty]
    W, H = d.get("taille", [104, 104])
    F = d.get("fin", 4)
    if nom == "eclot" and k >= 6:
        return None
    etat = "eclosion" if nom == "eclot" and k >= 3 else "fissure" if fele >= 2 else "intact"
    cle = ("fin", ty, etat)
    if cle not in _CACHE:
        import base64
        _CACHE[cle] = zlib.decompress(base64.b64decode(x[etat]))
    src = _CACHE[cle]
    pal = [_hex(c) for c in x["palette"]]
    lueur = _hex(x.get("lueur", "#ffd75f"))
    blanc = _hex(d.get("effets", {}).get("c", "#ffffff"))
    dx = F * ((0, -1, 0, 1)[k % 4] if nom == "remue" else (1, -1)[k % 2] if nom in ("craque", "eclot") and k < 2 else 0)
    px = [None] * (W * H)
    for y in range(H):
        for xx in range(W):
            v = src[y * W + xx]
            if v and 0 <= xx + dx < W:
                px[y * W + xx + dx] = pal[v - 1] if v - 1 < len(pal) else None
    eclair = nom == "craque" and k % 2 == 0
    feles = x.get("feles", [])
    traits = None if etat == "eclosion" else feles[0] if (fele == 1 or (fele == 2 and eclair)) and feles else \
        feles[1] if fele >= 3 and len(feles) > 1 else None
    for xx, y in traits or []:
        xx += dx
        if 0 <= xx < W and 0 <= y < H and px[y * W + xx] is not None:
            px[y * W + xx] = blanc if eclair else lueur
    if nom == "brille" or (nom == "eclot" and k >= 3):
        for cx, cy in d.get("etincelles", [[], []])[k % 2]:
            for e in range(-F // 2, F // 2 + 1):
                for a, b in ((e, 0), (0, e)):
                    if 0 <= cx + a < W and 0 <= cy + b < H and px[(cy + b) * W + cx + a] is None:
                        px[(cy + b) * W + cx + a] = blanc if e == 0 else lueur
    return px, W, H


def _oeuf(ty, fele, nom, k, D):
    """L'œuf à dessiner sur D pixels de côté : le fin (104×104) si la place le permet, sinon celui du terminal (26×26).
    Renvoie ([(r, g, b) ou None], W, H, finesse)."""
    from . import oeufs
    if D >= 60:
        f = oeuf_fin(ty, fele, nom, k)
        if f:
            return f + (4,)
    rows = oeufs.image(ty, fele, nom, k)
    if rows is None:
        return None
    g, gw, gh = _grille_oeuf(rows, oeufs.palette(ty))
    return g, gw, gh, 1


def _poser_ech(fond, W, H, calque, cw, ch, x0, y0, dw, dh):
    """Pose un calque [(r, g, b[, a]) ou None] (cw×ch) agrandi ou réduit à dw×dh (plus proche voisin) en (x0, y0)."""
    x0, y0 = int(round(x0)), int(round(y0))
    dw, dh = max(1, int(round(dw))), max(1, int(round(dh)))
    for y in range(dh):
        Y = y0 + y
        if not 0 <= Y < H:
            continue
        sy = min(ch - 1, y * ch // dh)
        for x in range(dw):
            X = x0 + x
            if not 0 <= X < W:
                continue
            q = calque[sy * cw + min(cw - 1, x * cw // dw)]
            if q is None:
                continue
            a = q[3] / 255 if len(q) > 3 else 1
            if a >= 1:
                fond[Y * W + X] = q[:3]
            elif a > 0:
                f = fond[Y * W + X]
                fond[Y * W + X] = (int(f[0] + (q[0] - f[0]) * a), int(f[1] + (q[1] - f[1]) * a), int(f[2] + (q[2] - f[2]) * a))


BAYER = [[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
         [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
         [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]


def ordre(x, y):
    """L'ordre d'arrivée d'un pixel dans le fondu digital, de 0 à 1 : une trame de Bayer 8×8 mêlée de hasard."""
    return (BAYER[y % 8][x % 8] + 0.5) / 64 * 0.55 + _h(x, y, 5) * 0.45


def fondu(cal, w, h, f, k):
    """Le bébé qui apparaît en fondu digital (f de 0 à 1) : chaque pixel arrive à son tour (ordre) ; ceux qui viennent
    d'arriver brillent en vert « matrix » puis prennent leur vraie couleur ; une ligne sur trois un peu plus sombre
    (balayage), et une ligne claire qui descend."""
    p = min(1.0, f * 1.25)
    out = []
    ligne = int(f * 1.1 * h)
    for y in range(h):
        sombre = f < 0.95 and (y + k) % 3 == 0
        for x in range(w):
            q = cal[y * w + x]
            if q is None:
                out.append(None)
                continue
            o = ordre(x, y)
            if o > p:
                out.append(VERT + (40,) if o - p < 0.06 and _h(x, y, k) < 0.5 else None)
                continue
            d = (p - o) / 0.2
            if d < 1:
                c = tuple(int(VERT_PALE[i] * (1 - d) * 0.4 + VERT[i] * (1 - d) * 0.6 + q[i] * d) for i in range(3))
            else:
                c = q[:3]
            if y == ligne or y == ligne - 1:
                c = tuple(min(255, v + 70) for v in c)
            elif sombre:
                c = tuple(int(v * 0.72) for v in c)
            out.append(c + (255,))
    return out


def _bebe(state):
    """Le bébé de l'espèce tirée (sprite du stade 1) : ([(r, g, b, 255) ou None], w, h), ou None."""
    try:
        from . import sprites
        rows = sprites.get_sprite(state, 1)
        pal = sprites.palette(state, st=1)
        w, h = max(len(r) for r in rows), len(rows)
        cal = []
        for r in rows:
            for x in range(w):
                v = pal.get(r[x] if x < len(r) else ".")
                cal.append(None if v is None else (sprites.x256(v) + (255,)))
        return cal, w, h
    except Exception:                                # noqa: BLE001  (une partie bizarre : pas de bébé, pas d'erreur)
        return None


def scene(state, W, H, t, m=None, posx=0.5, pa=1.0):
    """Les pixels [(r, g, b)] du camp de base (W×H, pixels de largeur pa) à l'instant t : endormi, qui se réveille,
    l'œuf qui arrive, qui éclot, le bébé qui apparaît. m : le moment (sinon moment(state, t))."""
    from . import oeufs
    m = m or moment(state, t)
    ph = m["phase"]
    if ph == "dort":
        return list(endormi("camp", W, H, posx, pa))
    base = reduire("camp", W, H, posx, pa)
    vers = _vers(W, H, posx, pa)
    tw = camp().get("taille", [1533, 863])[1]
    e = H / tw                                       # pixels de la vue par pixel d'origine (en hauteur)
    if ph == "eveil":
        dort = endormi("camp", W, H, posx, pa)
        tm = carte_eveil(W, H, posx, pa)
        fd = camp().get("fondu", 0.4)
        te = m["te"]
        px = []
        for i, a in enumerate(base):
            f = (te - tm[i]) / fd
            if f <= 0:
                px.append(dort[i])
            elif f >= 1:
                px.append(a)
            else:
                b = dort[i]
                px.append((int(b[0] + (a[0] - b[0]) * f), int(b[1] + (a[1] - b[1]) * f), int(b[2] + (a[2] - b[2]) * f)))
        for x, y, f in lumieres(te):
            X, Y = vers(x, y)
            _lueur(px, W, H, X, Y, max(2.5, H * 0.055), VERT, 0.9 * f, pa)
            _lueur(px, W, H, X, Y, max(1.2, H * 0.014), (255, 255, 255), 0.8 * f, pa)
        return px
    px = list(base)
    ty = oeufs.type_de(state)
    c = camp()
    o = c.get("oeuf", {"x": 545, "y": 196, "cote": 430})
    D = o["cote"] * e                                # le côté du cadre de l'œuf, en pixels de la vue
    ax, ay = vers(o["x"] + o["cote"] / 2, o["y"] + o["cote"] * 24.5 / 26)     # le bas de l'œuf, au fond du nid

    def poser_oeuf(img, cx, cy, Dm):
        g, gw, gh, F = img
        d = Dm if F > 1 else max(1, int(Dm / gw + 0.2)) * gw      # l'œuf du terminal : un nombre entier de pixels
        rgba = len(next((q for q in g if q is not None), (0, 0, 0, 0))) == 4
        cal = g if rgba else [None if q is None else q + (255,) for q in g]
        _poser_ech(px, W, H, cal, gw, gh, cx - d / pa / 2, cy - d * 24.5 / 26, d / pa, d)

    if ph == "telech":
        img = _oeuf(ty, 0, "", 0, D)
        g, gw, gh, F = img
        cal = telecharge(g, gw, gh, m["pct"], m["k"], F)
        _lueur(px, W, H, ax, ay - D * 0.4, D * 0.75, VERT, 0.18 + 0.1 * (m["k"] % 2), pa)
        poser_oeuf((cal, gw, gh, F), ax, ay, D)
        return px
    if ph in ("eclat", "eclot"):
        fele, nom, k = (0, "brille", m["k"]) if ph == "eclat" else ECLOT[m["k"]]
        img = _oeuf(ty, fele, nom, k, D)
        if ph == "eclot" and m["k"] >= OUVERT - 1:  # la coquille éclate : un éclair blanc
            _lueur(px, W, H, ax, ay - D * 0.45, D * 1.1, (255, 255, 230), 0.9 if m["k"] < OUVERT + 1 else 0.45, pa)
        else:
            _lueur(px, W, H, ax, ay - D * 0.45, D * 0.9, (255, 240, 150), 0.45 if ph == "eclat" else 0.3, pa)
        if img:
            poser_oeuf(img, ax, ay, D)
        return px
    # fondu (le bébé apparaît) puis ne : la coquille ouverte glisse vers le bord du nid, le bébé au centre
    f = m.get("f", 1.0) if ph == "fondu" else 1.0
    cq = c.get("coquille", {"x": 365, "y": 300, "cote": 300})
    qx, qy = vers(cq["x"] + cq["cote"] / 2, cq["y"] + cq["cote"] * 24.5 / 26)
    g = min(1.0, f / 0.35)
    g = g * g * (3 - 2 * g)
    Dq = D + (cq["cote"] * e - D) * g
    bb = c.get("bebe", {"x": 835, "bas": 612, "haut": 330})
    bx, by = vers(bb["x"], bb["bas"])
    bh = bb["haut"] * e
    _lueur(px, W, H, bx, by - bh * 0.55, bh * 1.1, (255, 240, 150), 0.35 * f, pa)
    if ph == "fondu":
        _lueur(px, W, H, bx, by - bh * 0.5, bh * 0.9, VERT, 0.5 * (1 - f) + 0.15, pa)
    coq = _oeuf(ty, 3, "eclot", 5, Dq)
    if coq:
        poser_oeuf(coq, ax + (qx - ax) * g, ay + (qy - ay) * g, Dq)
    b = _bebe(state)
    if b:
        cal, w, h = b
        s = max(1, int(round(bh / h)))
        if ph == "fondu":
            cal = fondu(cal, w, h, f, m["k"])
        _poser_ech(px, W, H, cal, w, h, bx - w * s / pa / 2, by - h * s, w * s / pa, h * s)
    if ph == "ne":
        for j, (dx, dy) in enumerate(((-170, -230), (150, -250), (210, -120), (-230, -90), (60, -300), (-60, -280))):
            if (m["k"] // 3 + j) % 3:
                X, Y = vers(bb["x"] + dx, bb["bas"] - 60 + dy)
                _lueur(px, W, H, X, Y, max(1.5, H * 0.022), (255, 247, 160), 1.2, pa)
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


# ---------------------------------------------------------------- plus de détail en texte : quadrants et sextants
QUADRANTS = " ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█"          # bits : haut-gauche 1, haut-droite 2, bas-gauche 4, bas-droite 8


def sextant(p):
    """Le caractère sextant (2×3 cases ; bits : haut-gauche 1, haut-droite 2, milieu 4 et 8, bas 16 et 32)."""
    if p == 0:
        return " "
    if p == 63:
        return "█"
    if p == 21:
        return "▌"
    if p == 42:
        return "▐"
    return chr(0x1FB00 + p - 1 - (p > 21) - (p > 42))


def _d2(a, b):
    return (a[0] - b[0]) ** 2 * 3 + (a[1] - b[1]) ** 2 * 4 + (a[2] - b[2]) ** 2 * 2


def _moy(cs):
    n = len(cs)
    return (sum(c[0] for c in cs) // n, sum(c[1] for c in cs) // n, sum(c[2] for c in cs) // n)


def deux_couleurs(cs):
    """Les deux couleurs qui représentent le mieux une case (k-moyennes à 2, partant de la plus claire et de la plus
    sombre) : (bits des pixels de la 1re couleur, 1re couleur, 2e couleur)."""
    lum = [c[0] * 299 + c[1] * 587 + c[2] * 114 for c in cs]
    a, b = cs[lum.index(max(lum))], cs[lum.index(min(lum))]
    if _d2(a, b) < 60:
        m = _moy(cs)
        return 0, m, m
    for _ in range(2):
        dans = [_d2(c, a) <= _d2(c, b) for c in cs]
        ga = [c for c, d in zip(cs, dans) if d]
        gb = [c for c, d in zip(cs, dans) if not d]
        a = _moy(ga) if ga else a
        b = _moy(gb) if gb else b
    return sum(1 << i for i, d in enumerate(dans) if d), a, b


def cases(px, W, H, cw, ch, mode="24", marge=""):
    """Pixels (W×H) → lignes de cases de cw×ch pixels : quadrants (2×2) ou sextants (2×3), deux couleurs par case."""
    glyphe = (lambda p: QUADRANTS[p]) if ch == 2 else sextant
    out = []
    for cy in range(H // ch):
        s = marge
        avant = None
        for cx in range(W // cw):
            cs = [px[(cy * ch + j) * W + cx * cw + i] for j in range(ch) for i in range(cw)]
            bits, a, b = deux_couleurs(cs)
            if mode == "24":
                code = f"\x1b[38;2;{a[0]};{a[1]};{a[2]};48;2;{b[0]};{b[1]};{b[2]}m"
            else:
                code = f"\x1b[38;5;{_x256(a)};48;5;{_x256(b)}m"
            if code != avant:
                s += code
                avant = code
            s += glyphe(bits)
        out.append(s + "\x1b[0m")
    return out


# ---------------------------------------------------------------- de vraies images : Kitty, iTerm2, sixel
def png(px, W, H, niveau=1):
    """Pixels [(r, g, b)] → un fichier PNG (RVB 8 bits), sans bibliothèque."""
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += bytes(v for c in px[y * W:(y + 1) * W] for v in c)

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(bytes(raw), niveau)) + bloc(b"IEND", b""))


def kitty(data, cols, rangs, ident=4242):
    """Le protocole graphique de Kitty : l'image PNG posée sur cols×rangs cases, le curseur ne bouge pas (C=1) ; le
    même numéro (i, p) remplace l'image d'avant (animation) ; q=2 : le terminal ne répond rien (pas de parasites)."""
    import base64
    b = base64.standard_b64encode(data).decode()
    morceaux = [b[i:i + 4096] for i in range(0, len(b), 4096)] or [""]
    out = ""
    for k, m in enumerate(morceaux):
        suite = 1 if k < len(morceaux) - 1 else 0
        if k == 0:
            out += f"\x1b_Ga=T,f=100,q=2,C=1,i={ident},p=1,c={cols},r={rangs},m={suite};{m}\x1b\\"
        else:
            out += f"\x1b_Gm={suite};{m}\x1b\\"
    return out


def iterm(data, cols, rangs):
    """L'image en ligne d'iTerm2 (et de WezTerm), étirée sur cols×rangs cases."""
    import base64
    b = base64.standard_b64encode(data).decode()
    return f"\x1b]1337;File=inline=1;width={cols};height={rangs};preserveAspectRatio=0;size={len(data)}:{b}\x07"


def sixel(px, W, H):
    """Pixels [(r, g, b)] → une image sixel (255 couleurs au plus : les plus fréquentes, sur 4 bits par couleur)."""
    import re
    compte = {}
    for c in px:
        k = (c[0] >> 4, c[1] >> 4, c[2] >> 4)
        compte[k] = compte.get(k, 0) + 1
    pal = sorted(compte, key=compte.get, reverse=True)[:255]
    rgb = [(r * 17, g * 17, b * 17) for r, g, b in pal]
    num = {k: i for i, k in enumerate(pal)}
    for k in compte:
        if k not in num:
            c = (k[0] * 17, k[1] * 17, k[2] * 17)
            num[k] = min(range(len(rgb)), key=lambda i: _d2(rgb[i], c))
    idx = [num[(c[0] >> 4, c[1] >> 4, c[2] >> 4)] for c in px]
    out = ["\x1bP0;1;0q", f'"1;1;{W};{H}']
    out += [f"#{i};2;{r * 100 // 255};{g * 100 // 255};{b * 100 // 255}" for i, (r, g, b) in enumerate(rgb)]
    trad = bytes(63 + (v & 63) for v in range(256))
    runs = re.compile(r"(.)\1{3,}")
    for y0 in range(0, H, 6):
        couches = {}
        for dy in range(min(6, H - y0)):
            bit = 1 << dy
            ligne = idx[(y0 + dy) * W:(y0 + dy + 1) * W]
            for x, ci in enumerate(ligne):
                a = couches.get(ci)
                if a is None:
                    a = couches[ci] = bytearray(W)
                a[x] |= bit
        for ci, a in couches.items():
            s = a.translate(trad).decode().rstrip("?")
            out.append(f"#{ci}" + runs.sub(lambda m: f"!{len(m.group(0))}{m.group(1)}", s) + "$")
        out.append("-")
    return "".join(out) + "\x1b\\"


GRAPHIQUES = ("kitty", "iterm", "sixel")
TEXTES = ("sextants", "quadrants", "demi")
_CAP = {}


def _signature():
    return "|".join(os.environ.get(k, "") for k in ("TERM", "TERM_PROGRAM", "TERM_PROGRAM_VERSION", "VTE_VERSION",
                                                     "KONSOLE_VERSION", "KITTY_WINDOW_ID", "WEZTERM_EXECUTABLE",
                                                     "LC_TERMINAL", "TMUX", "STY"))


def texte_selon_env():
    """Le dessin en texte le plus fin que le terminal affiche sûrement : les sextants quand il les dessine lui-même
    (VTE ≥ 0.70 : GNOME Terminal, Ptyxis ; kitty, WezTerm, foot, Ghostty), sinon les quadrants (dans toutes les polices
    à blocs), les demi-blocs sur la console linux."""
    term = os.environ.get("TERM", "")
    if term in ("linux", "vt100", "vt220"):
        return "demi"
    try:
        vte = int(os.environ.get("VTE_VERSION", "0"))
    except ValueError:
        vte = 0
    if vte >= 7000 or any(x in term for x in ("kitty", "foot", "ghostty", "wezterm")) \
            or os.environ.get("TERM_PROGRAM") in ("WezTerm", "ghostty"):
        return "sextants"
    return "quadrants"


def interroger(delai=0.35):
    """Demande au terminal ce qu'il sait faire (une seule fois, réponse gardée : capacites) : le protocole de Kitty
    (une requête a=q), la taille d'une case en pixels (CSI 16 t), la largeur d'un sextant (CSI 6 n), puis DA1 (CSI c),
    auquel presque tous répondent (« 4 » : sixel). On lit jusqu'à la réponse DA1 ou le délai ; sans réponse, on vide
    ce qui arriverait en retard, pour ne laisser aucune séquence parasite dans l'invite."""
    import re
    import select
    import termios
    import time as _t
    rep = {"kitty": False, "sixel": False, "cellule": None, "sextant": None, "da1": False}
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return rep
    try:
        vieux = termios.tcgetattr(fd)
    except termios.error:
        os.close(fd)
        return rep
    buf = b""
    try:
        nv = termios.tcgetattr(fd)
        nv[3] &= ~(termios.ICANON | termios.ECHO)
        nv[6][termios.VMIN], nv[6][termios.VTIME] = 0, 0
        termios.tcsetattr(fd, termios.TCSANOW, nv)
        q = ("\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\" + "\x1b[16t" + "\x1b7\r\U0001FB0F\x1b[6n\r\x1b[K\x1b8" + "\x1b[c")
        os.write(fd, q.encode())
        fin = _t.time() + delai
        while _t.time() < fin:
            r, _, _ = select.select([fd], [], [], max(0.0, fin - _t.time()))
            if not r:
                break
            buf += os.read(fd, 4096)
            if re.search(rb"\x1b\[\?[\d;]*c", buf):
                break
        if not re.search(rb"\x1b\[\?[\d;]*c", buf):          # pas de réponse : on attend un peu, puis on vide
            _t.sleep(0.25)
            termios.tcflush(fd, termios.TCIFLUSH)
    except OSError:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, vieux)
        os.close(fd)
    rep["kitty"] = b"\x1b_Gi=31;OK" in buf
    m = re.search(rb"\x1b\[6;(\d+);(\d+)t", buf)
    if m and int(m.group(1)) > 0 and int(m.group(2)) > 0:
        rep["cellule"] = (int(m.group(2)), int(m.group(1)))
    m = re.search(rb"\x1b\[(\d+);(\d+)R", buf)
    if m:
        rep["sextant"] = int(m.group(2)) == 2               # le sextant tient sur une case
    m = re.search(rb"\x1b\[\?([\d;]*)c", buf)
    if m:
        rep["da1"] = True
        rep["sixel"] = "4" in m.group(1).decode().split(";")
    return rep


def capacites():
    """Ce que le terminal sait montrer : {graphique: kitty | iterm | sixel | None, texte: sextants | quadrants | demi,
    cellule: (largeur, hauteur) d'une case en pixels}. Demandé une fois au terminal (interroger), gardé dans
    ~/.terminagotchi/terminal.json pour ce terminal-là (TERM, VTE_VERSION…). TG_IMAGES force un rendu ; pas de vraie
    image dans tmux ou screen, ni hors d'un vrai terminal (fichier, tests)."""
    force = os.environ.get("TG_IMAGES", "")
    if force in GRAPHIQUES + TEXTES:
        return {"graphique": force if force in GRAPHIQUES else None,
                "texte": force if force in TEXTES else texte_selon_env(), "cellule": (10, 20)}
    sig = _signature()
    if _CAP.get("sig") == sig:
        return _CAP["cap"]
    cap = {"graphique": None, "texte": texte_selon_env(), "cellule": (10, 20)}
    import sys
    try:
        tty = sys.stdout.isatty() and sys.stdin.isatty()
    except (AttributeError, ValueError, OSError):
        tty = False
    if tty and not os.environ.get("TMUX") and not os.environ.get("STY") and mode_couleurs():
        import json
        from . import core
        f = core.SAVE_DIR / "terminal.json"
        try:
            garde = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            garde = {}
        if isinstance(garde, dict) and isinstance(garde.get(sig), dict):
            cap = garde[sig]
            cap["cellule"] = tuple(cap.get("cellule") or (10, 20))
        else:
            r = interroger()
            if os.environ.get("TERM_PROGRAM") == "iTerm.app" or os.environ.get("LC_TERMINAL") == "iTerm2":
                cap["graphique"] = "iterm"
            if r["kitty"]:
                cap["graphique"] = "kitty"
            elif r["sixel"] and not cap["graphique"]:
                cap["graphique"] = "sixel"
            if r["cellule"]:
                cap["cellule"] = r["cellule"]
            if cap["texte"] == "sextants" and r["sextant"] is False:
                cap["texte"] = "quadrants"                   # le sextant prend deux cases : la police ne l'a pas
            try:
                garde = garde if isinstance(garde, dict) else {}
                garde[sig] = dict(cap, cellule=list(cap["cellule"]))
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(garde), encoding="utf-8")
            except OSError:
                pass
    _CAP.update(sig=sig, cap=cap)
    return cap


def rendu():
    """Le rendu choisi : une vraie image si possible, sinon le texte le plus fin."""
    c = capacites()
    return c["graphique"] or c["texte"]


def peindre(fn, C, R, rendu_=None, mode="24", marge=""):
    """Dessine une scène sur C×R cases du terminal avec le rendu choisi. fn(W, H, pa) donne les pixels (W×H, pixels de
    largeur pa). Une vraie image : la 1re ligne porte l'image (posée sans bouger le curseur, après avoir fait la place),
    les R − 1 suivantes sont vides ; sinon des lignes de caractères."""
    r = rendu_ or rendu()
    if r in ("kitty", "iterm"):
        W, H = 384, 216
        data = png(fn(W, H, 1.0), W, H)
        img = kitty(data, C, R) if r == "kitty" else iterm(data, C, R)
        return ["\n" * R + f"\x1b[{R}A\r" + marge + "\x1b7" + img + "\x1b8"] + [""] * (R - 1)
    if r == "sixel":
        cw, chh = capacites()["cellule"]
        W = max(64, min(C * cw, 640))
        H = int(W * 9 / 16) // 6 * 6
        R2 = -(-H // chh)
        return ["\n" * R2 + f"\x1b[{R2}A\r" + marge + "\x1b7" + sixel(fn(W, H, 1.0), W, H) + "\x1b8"] + [""] * (R2 - 1)
    if r == "sextants":
        return cases(fn(2 * C, 3 * R, 0.75), 2 * C, 3 * R, 2, 3, mode, marge)
    if r == "quadrants":
        return cases(fn(2 * C, 2 * R, 0.5), 2 * C, 2 * R, 2, 2, mode, marge)
    return lignes(fn(C, 2 * R, 1.0), C, 2 * R, mode, marge)


def illustration(nom, W, H, mode="24", marge="", rendu_=None):
    """Une illustration entière (« monde », « dort », « camp_dort ») sur W cases × H/2 lignes, ou [] si elle manque."""
    src = "camp" if nom == "camp_dort" else nom
    if not disponible(src):
        return []
    if nom == "camp_dort":
        return peindre(lambda w, h, pa: endormi(src, w, h, 0.5, pa), W, H // 2, rendu_, mode, marge)
    return peindre(lambda w, h, pa: reduire(src, w, h, 0.5, pa), W, H // 2, rendu_, mode, marge)


def oeuf_seul(state, m, mode="24", marge=""):
    """Le repli d'un petit terminal : l'œuf seul (26×26) qui arrive, éclot, puis le bébé, sur le fond du terminal."""
    from . import oeufs
    ty = oeufs.type_de(state)
    ph = m["phase"]
    if ph in ("dort", "eveil"):
        return []
    fond = (12, 14, 18)
    if ph in ("fondu", "ne"):
        b = _bebe(state)
        if b:
            cal, w, h = b
            if ph == "fondu":
                cal = fondu(cal, w, h, m.get("f", 1), m["k"])
            H = max(26, h + h % 2)
            px = [fond] * (w * H)
            _poser(px, w, H, cal, w, h, 0, H - h)
            return lignes(px, w, H, mode, marge)
    if ph == "telech":
        g, gw, gh = _grille_oeuf(oeufs.image(ty, 0), oeufs.palette(ty))
        cal = telecharge(g, gw, gh, m["pct"], m["k"], 1)
    else:
        fele, nom, k = (0, "brille", m["k"]) if ph == "eclat" else ECLOT[m["k"]] if ph == "eclot" else (3, "eclot", 5)
        g, gw, gh = _grille_oeuf(oeufs.image(ty, fele, nom, k), oeufs.palette(ty))
        cal = [None if p is None else p + (255,) for p in g]
    px = [fond] * (gw * gh)
    _poser(px, gw, gh, cal, gw, gh, 0, 0)
    if gh % 2:
        px += [fond] * gw
    return lignes(px, gw, gh + gh % 2, mode, marge)
