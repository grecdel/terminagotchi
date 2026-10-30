"""La vie DANS la créature, sans aucune nouvelle image : les yeux clignent, le haut du corps respire, les appendices
fins (ailes, queues, tentacules, antennes) ondulent, et les pupilles regardent un peu à gauche et à droite.

Tout part de l'image fixe d'un stade (pixels indexés, palette en entiers 0xRRGGBB) :
  - les YEUX sont cherchés automatiquement : petites taches sombres (ou lumineuses) bien entourées par le corps,
    dans le haut de la silhouette, de préférence par paires à la même hauteur ; leurs reflets clairs vont avec ;
  - l'ÉPAISSEUR de la silhouette (distance au vide) sépare le corps (épais) des parties fines qui en dépassent ;
  - le HAUT DU CORPS (le haut de la partie épaisse) gonfle d'un pixel de chaque côté et se soulève d'un pixel.
Si une détection échoue (pas d'yeux sûrs, pas de partie fine…), on n'anime pas cette partie ; si le résultat
risque d'être cassé (trop de pixels perdus ou ajoutés), analyser() renvoie None et l'appelant garde l'animation
d'avant (anim_auto : écrasement doux de toute l'image). Jamais d'image vide ou cassée.

Tout est calculé en entiers, sans hasard du système : le portage Kotlin (app/…/Vie.kt) donne exactement les mêmes
images (test : pc/outils/test_vie.py et tests/jvm/Vie.kt, sur les vecteurs de donnees/vie/vecteurs.json).

Démo (depuis pc/) : python3 -m tg.vie braisillon bebe
"""

PAD = 2                      # marge ajoutée à gauche, à droite et en haut de l'image (ondulations, respiration)
CYCLE = 64                   # une boucle complète de vie : 64 images (8 s à 8 images par seconde)
BLOC = 32                    # chaque bloc de 32 images a son propre clignement et son regard (rythme irrégulier)
SIN = (0, 38, 71, 92, 100, 92, 71, 38, 0, -38, -71, -92, -100, -92, -71, -38)    # sinus × 100, 16 pas
M32 = 0xFFFFFFFF


def _lum(c):
    return ((c >> 16 & 255) * 299 + (c >> 8 & 255) * 587 + (c & 255) * 114) // 1000


def _melange(v):
    """Brassage d'un entier 32 bits (le même en Kotlin)."""
    v &= M32
    v = ((v ^ (v >> 15)) * 0x2C1B3C6D) & M32
    v = ((v ^ (v >> 12)) * 0x297A2D39) & M32
    return v ^ (v >> 15)


def _div(a, b):
    """Division entière arrondie vers le bas (comme Math.floorDiv)."""
    return a // b


class Oeil:
    def __init__(self, px, couleur_paupiere, couleur_trait):
        self.px = px                                     # [(x, y)] triés (y, x), coordonnées de l'image d'origine
        xs = [p[0] for p in px]
        ys = [p[1] for p in px]
        self.x0, self.x1, self.y0, self.y1 = min(xs), max(xs), min(ys), max(ys)
        self.paupiere = couleur_paupiere                 # indice de palette (la peau autour)
        self.trait = couleur_trait                       # indice de palette (l'œil fermé)


class Analyse:
    pass


# ---------------------------------------------------------------- analyse (une fois par image)
def _yeux(w, h, o, lum):
    """Les yeux : [Oeil] (0, 1 ou 2), ou [] si rien de sûr."""
    def op(x, y):
        return 0 <= x < w and 0 <= y < h and o[y * w + x] != 0

    R = 2 if max(w, h) < 36 else 3
    smax = 4 + (w * h) // 40
    cote = 2 + max(w, h) // 8
    anneau = [(dx, dy) for dy in range(-R, R + 1) for dx in range(-R, R + 1) if max(abs(dx), abs(dy)) == R]
    moy = [-1] * (w * h)
    for y in range(h):
        for x in range(w):
            if not o[y * w + x]:
                continue
            s = n = 0
            for dx, dy in anneau:
                if op(x + dx, y + dy):
                    s += lum[o[(y + dy) * w + x + dx]]
                    n += 1
            if 4 * n >= 3 * len(anneau):                 # bien entouré par le corps (le bord peut frôler)
                moy[y * w + x] = s // n
    for sorte in ("sombre", "clair"):
        cand = [False] * (w * h)
        for k in range(w * h):
            m = moy[k]
            if m < 0:
                continue
            L = lum[o[k]]
            if sorte == "sombre":
                cand[k] = m - L >= 35 and L * 100 <= m * 62
            else:
                cand[k] = L - m >= 60 and L >= 150
        vu = [False] * (w * h)
        comps = []
        for k in range(w * h):                           # composantes (8 voisins), parcours dans l'ordre de lecture
            if not cand[k] or vu[k]:
                continue
            pile, comp = [k], []
            vu[k] = True
            while pile:
                q = pile.pop()
                comp.append(q)
                qx, qy = q % w, q // w
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        X, Y = qx + dx, qy + dy
                        if 0 <= X < w and 0 <= Y < h and cand[Y * w + X] and not vu[Y * w + X]:
                            vu[Y * w + X] = True
                            pile.append(Y * w + X)
            comps.append(sorted(comp))
        bons = []
        for comp in comps:
            xs = [q % w for q in comp]
            ys = [q // w for q in comp]
            bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            cy2 = min(ys) + max(ys)                      # 2 × centre
            if len(comp) > smax or bw > cote or bh > cote or cy2 > (h * 4) // 3:
                continue
            force = sum(abs(moy[q] - lum[o[q]]) for q in comp)
            bons.append((comp, min(xs) + max(xs), cy2, force, len(comp), min(lum[o[q]] for q in comp)))
        if not bons or len(comps) > 6:
            continue
        meilleur, score = None, -1
        for i in range(len(bons)):
            for j in range(i + 1, len(bons)):
                a, b = bons[i], bons[j]
                dy2 = abs(a[2] - b[2])
                dx2 = abs(a[1] - b[1])
                if dy2 > 2 + h // 8 or dx2 < 4 or dx2 > w or max(a[4], b[4]) > 2 * min(a[4], b[4]) + 1 \
                        or abs(a[5] - b[5]) > 40:
                    continue
                s = a[3] + b[3] - 10 * dy2
                if s > score:
                    meilleur, score = (a, b), s
        if meilleur is None:
            if len(bons) == 1 and len(comps) <= 2 and bons[0][2] <= h:     # un seul œil (de profil), dans le haut
                meilleur = (bons[0],)
            else:
                continue
        yeux = []
        for b in meilleur:
            comp = set(b[0])
            # les reflets clairs collés à un œil sombre en font partie (ils se ferment avec lui)
            if sorte == "sombre":
                ajout = set()
                for q in sorted(comp):
                    qx, qy = q % w, q // w
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            X, Y = qx + dx, qy + dy
                            k = Y * w + X
                            if 0 <= X < w and 0 <= Y < h and o[k] and k not in comp and moy[k] >= 0 \
                                    and lum[o[k]] - moy[k] >= 60 and lum[o[k]] >= 150:
                                ajout.add(k)
                if len(ajout) <= len(comp) // 2 + 1:
                    comp |= ajout
            compte = {}
            for q in comp:
                qx, qy = q % w, q // w
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        X, Y = qx + dx, qy + dy
                        k = Y * w + X
                        if 0 <= X < w and 0 <= Y < h and o[k] and k not in comp:
                            compte[o[k]] = compte.get(o[k], 0) + 1
            if not compte:
                continue
            peau = min(compte, key=lambda c: (-compte[c], c))
            trait = min(list(compte) + [o[q] for q in comp], key=lambda c: (lum[c], c))
            if lum[peau] - lum[trait] < 25:
                trait = peau
            yeux.append(Oeil(sorted(((q % w, q // w) for q in comp), key=lambda p: (p[1], p[0])), peau, trait))
        if yeux:
            return yeux
    return []


def _epaisseur(w, h, o):
    """Distance de chaque pixel plein au vide (ou au bord), en pas de roi (8 voisins) : 1 = au bord."""
    INF = 1 << 20
    d = [0 if not o[k] else INF for k in range(w * h)]

    def v(x, y):
        return d[y * w + x] if 0 <= x < w and 0 <= y < h else 0
    for y in range(h):
        for x in range(w):
            k = y * w + x
            if d[k]:
                d[k] = min(d[k], v(x - 1, y) + 1, v(x - 1, y - 1) + 1, v(x, y - 1) + 1, v(x + 1, y - 1) + 1)
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            k = y * w + x
            if d[k]:
                d[k] = min(d[k], v(x + 1, y) + 1, v(x + 1, y + 1) + 1, v(x, y + 1) + 1, v(x - 1, y + 1) + 1)
    return d


def _fins(w, h, o, ep):
    """Le corps (épais) et les parties fines qui en dépassent : (k, centre x2, centre y2, haut, bas du corps,
    {indice: (rang depuis le corps, sens)}) ; sens 1 = appendice plutôt horizontal (ondule en hauteur), 0 = vertical."""
    k = 2 if max(w, h) < 30 else 3
    coeur = [q for q in range(w * h) if ep[q] >= k]
    if len(coeur) < 4:
        k -= 1
        coeur = [q for q in range(w * h) if ep[q] >= k]
    if len(coeur) < 4:
        return None
    INF = 1 << 20
    g = [INF] * (w * h)
    front = coeur
    for q in coeur:
        g[q] = 0
    n = 0
    while front:                                       # distance au corps, en restant dans la silhouette
        n += 1
        suite = []
        for q in front:
            qx, qy = q % w, q // w
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    X, Y = qx + dx, qy + dy
                    if 0 <= X < w and 0 <= Y < h:
                        r = Y * w + X
                        if o[r] and g[r] == INF:
                            g[r] = n
                            suite.append(r)
        front = suite
    cx2 = 2 * sum(q % w for q in coeur) // len(coeur)
    cy2 = 2 * sum(q // w for q in coeur) // len(coeur)
    haut = min(q // w for q in coeur)
    bas = max(q // w for q in coeur)
    fins = {}
    for q in range(w * h):
        if o[q] and k < g[q] < INF and q // w < (h * 3) // 4:
            dx2, dy2 = abs(2 * (q % w) - cx2), abs(2 * (q // w) - cy2)
            fins[q] = (g[q] - k, 1 if dx2 >= dy2 else 0)
    if len(fins) < 4:
        fins = {}
    return k, cx2, cy2, haut, bas, fins


def analyser(w, h, o, pal):
    """Ce qui peut bouger dans l'image (w × h, octets 0 = vide, palette en entiers), ou None si rien de sûr."""
    try:
        if w < 6 or h < 6 or len(o) < w * h:
            return None
        o = list(o[:w * h])
        n0 = sum(1 for v in o if v)
        if n0 < 12:
            return None
        lum = [0] + [_lum(c) for c in pal]
        if max(o) >= len(lum):
            return None
        a = Analyse()
        a.w, a.h, a.o, a.n0 = w, h, o, n0
        g = (w * 31 + h) & 0x7FFFFFFF
        for v in o:
            g = (g * 131 + v) & 0x7FFFFFFF
        a.graine = g
        a.yeux = _yeux(w, h, o, lum)
        ep = _epaisseur(w, h, o)
        f = _fins(w, h, o, ep)
        if f is None:
            a.fins, a.souffle = {}, None
        else:
            k, cx2, cy2, haut, bas, fins = f
            a.fins = fins
            a.gmax = max([v[0] for v in fins.values()] + [1])
            a.amp = 1 if max(w, h) < 36 else 2
            fin_souffle = haut + (bas - haut) * 3 // 5
            a.souffle = (haut, fin_souffle, cx2 // 2) if fin_souffle - haut >= 3 else None
        if not a.yeux and not a.fins and a.souffle is None:
            return None
        bande = 0 if a.souffle is None else a.souffle[1] - a.souffle[0] + 1
        haut_max = n0 + n0 // 8 + 2 * bande + 4          # la respiration ajoute au plus 2 pixels par ligne
        for t in range(CYCLE):                         # garde-fou : aucune image cassée
            W2, H2, img = image(a, t)
            n = sum(1 for v in img if v)
            if n * 100 < n0 * 88 or n > haut_max:
                return None
        return a
    except (ValueError, IndexError, ZeroDivisionError):
        return None


_GARDEES = {}


def analyse_gardee(w, h, o, pal):
    """analyser(), gardée en mémoire (quelques dizaines d'images : l'équipe, le guide, le combat)."""
    cle = (w, h, bytes(o[:w * h]), tuple(pal))
    if cle not in _GARDEES:
        if len(_GARDEES) > 48:
            _GARDEES.clear()
        _GARDEES[cle] = analyser(w, h, o, pal)
    return _GARDEES[cle]


# ---------------------------------------------------------------- le temps qui passe
def programme(a, t):
    """Ce que fait la créature à l'image t : (paupière 0 ouverte | 1 mi-close | 2 fermée, regard -1 | 0 | 1,
    souffle 0 | 1 | 2, phase de l'ondulation)."""
    b = t // BLOC
    i = t % BLOC
    hsh = _melange(a.graine ^ ((b * 0x9E3779B1) & M32))
    paup = 0
    regard = 0
    if (hsh >> 8) % 5:                                 # un bloc sur cinq environ : pas de clignement
        o_ = 3 + hsh % 18
        for debut in ((o_, o_ + 4) if (hsh >> 5) % 4 == 0 else (o_,)):
            if i == debut or i == debut + 2:
                paup = max(paup, 1)
            elif i == debut + 1:
                paup = 2
        if (hsh >> 11) % 3:
            g0 = (o_ + 7 + (hsh >> 14) % 5) % BLOC
            if g0 <= i < g0 + 6 and not (o_ - 1 <= i <= o_ + 7):
                regard = 1 if (hsh >> 17) % 2 else -1
    else:
        if (hsh >> 11) % 2:
            g0 = 6 + (hsh >> 14) % 12
            if g0 <= i < g0 + 7:
                regard = 1 if (hsh >> 17) % 2 else -1
    s = SIN[(t // 2) % 16]
    souffle = 2 if s >= 60 else (1 if s >= 10 else 0)
    return paup, regard, souffle, t % 16


def image(a, t):
    """L'image de vie numéro t : (largeur, hauteur, octets) — l'image d'origine agrandie de PAD à gauche, à droite et
    en haut (les pieds restent sur la dernière ligne)."""
    w, h = a.w, a.h
    W2, H2 = w + 2 * PAD, h + PAD
    paup, regard, souffle, ph = programme(a, t)
    src = list(a.o)
    # 1. les yeux (dans l'image d'origine)
    for oe in a.yeux:
        dec = 0
        if regard and all(0 <= x + regard < w and a.o[y * w + x + regard] for x, y in oe.px):
            dec = regard                                 # les pupilles glissent d'un pixel, la peau comble derrière
            vals = [a.o[y * w + x] for x, y in oe.px]
            for x, y in oe.px:
                src[y * w + x] = oe.paupiere
            for (x, y), v in zip(oe.px, vals):
                src[y * w + x + dec] = v
        if paup:
            hh = oe.y1 - oe.y0 + 1
            for x, y in oe.px:
                if paup == 2 or y - oe.y0 < (hh + 1) // 2:
                    src[y * w + x + dec] = oe.paupiere
            if paup == 2 and hh >= 2:
                for x, y in oe.px:
                    if y == oe.y1:
                        src[y * w + x + dec] = oe.trait
    # 2. posé sur la toile agrandie, les parties fines qui ondulent
    out = [0] * (W2 * H2)
    for y in range(h):
        for x in range(w):
            q = y * w + x
            if src[q] and q not in a.fins:
                out[(y + PAD) * W2 + x + PAD] = src[q]
    fins = sorted(a.fins.items(), key=lambda e: (e[1][0], e[0]))
    for q, (rang, sens) in fins:
        r = min(rang, 4)
        dep = _div(a.amp * r * SIN[(ph - rang) % 16], 400)
        x, y = q % w + PAD, q // w + PAD
        if sens:
            y += dep
        else:
            x += dep
        if 0 <= x < W2 and 0 <= y < H2:
            out[y * W2 + x] = src[q]
    # 3. le haut du corps respire : il s'élargit d'un pixel de chaque côté, puis se soulève d'un pixel
    if a.souffle is not None and souffle:
        haut, fin, xc = a.souffle
        haut += PAD
        fin += PAD
        xc += PAD
        if souffle == 1:
            q4 = (fin - haut) // 4
            y0, y1 = haut + q4, fin - q4
        else:
            y0, y1 = haut, fin
        for y in range(y0, y1 + 1):
            ligne = out[y * W2:(y + 1) * W2]
            nv = list(ligne)
            for x in range(1, xc + 1):
                nv[x - 1] = ligne[x]
            for x in range(W2 - 2, xc - 1, -1):
                nv[x + 1] = ligne[x]
            out[y * W2:(y + 1) * W2] = nv
        if souffle == 2:
            lev = haut + (fin - haut) // 2
            for y in range(1, lev + 1):
                out[(y - 1) * W2:y * W2] = out[y * W2:(y + 1) * W2]
    return W2, H2, bytes(out)


def images(a, n=CYCLE, debut=0):
    return [image(a, debut + t)[2] for t in range(n)]


# ---------------------------------------------------------------- démo
def _demo(args):
    import sys
    import time
    from . import bestiaire as B
    e = B.espece(args[0]) if args else None
    if not e:
        print("usage : python3 -m tg.vie <espèce> [stade]")
        return
    w, h, o, pal = B.image(e, args[1] if len(args) > 1 else "bebe")
    p = [int(c[1:], 16) for c in pal]
    a = analyser(w, h, o, p)
    if a is None:
        print(" Rien de sûr à animer : on garde l'animation d'avant.")
        return
    print(f" yeux : {len(a.yeux)} · parties fines : {len(a.fins)} px · souffle : {a.souffle}")
    sys.stdout.write("\033[?25l")
    try:
        for t in range(2 * CYCLE):
            W2, H2, img = image(a, t)
            ls = B.lignes_image(W2, H2, img, pal)
            if t:
                sys.stdout.write(f"\033[{len(ls)}F")
            sys.stdout.write("\n".join(ls) + "\n")
            sys.stdout.flush()
            time.sleep(1 / 8)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")


if __name__ == "__main__":
    import sys
    _demo(sys.argv[1:])
