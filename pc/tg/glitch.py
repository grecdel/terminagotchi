"""L'effet « glitch » : une créature dont l'image se dérègle, comme un vieil écran (effet de l'INDIVIDU, comme le shiny).

Décisions du propriétaire (31 octobre 2026, docs/programme.md § 7.6) :
  - au repos, le style A (léger) : les couches rouge et bleue décalées (un liseré rose d'un côté, cyan de l'autre)
    et 2 tranches horizontales décalées ;
  - toutes les quelques secondes, un éclair bref du style C (fort) : couleurs ternies tirées vers le cyan et le
    magenta, lignes de balayage, pixels morts, 7 tranches décalées, une bande de pixels triés ;
  - fabriqué à partir de l'image de la créature (aucune illustration à part), après la teinte shiny ;
  - par-dessus les animations (respiration, poses du bureau…) : l'effet se pose sur chaque image, il ne les remplace pas ;
  - déterministe : la graine est l'individu (son identifiant), le même rendu sur PC, Android (Glitch.kt) et le site
    (site/src/glitch.js). Vecteurs communs : donnees/glitch/vecteurs.json.

Spécification (tout en entiers, identique en Python, Kotlin et JavaScript)
--------------------------------------------------------------------------
  Pixels : entiers ARGB 0xAARRGGBB, transparent si A = 0. s = la taille d'un pixel de la créature dans l'image
  (1 pour le dessin du jeu, 4 pour l'image fine de la vie…) : tout se mesure en pixels de créature (w0 = w // s,
  h0 = h // s), puis × s. Couleurs : ROSE 0xFF2878, CYAN 0x28E6FF, JAUNE 0xF0FF50, BLANC 0xFFFFFF.

  Hasard : fnv1a-64 des octets UTF-8 de « graine:style:phase » → état de splitmix64 (comme tirage.Hasard) ;
  n(k) = sortie % k.

   1. (C) couleurs : m = (r+g+b)//3 ; chaque canal c → (55c + 45m)//100 ; puis r → min(255, r·105//100 + 18),
      b → min(255, b·110//100 + 28).
   2. liseré : d = s·max(1, w0//24) (A) ou s·max(2, w0//12) (C). Un pixel transparent (de l'image de départ) devient
      CYAN si le pixel d plus à droite est plein, sinon ROSE si le pixel d plus à gauche est plein. En A, seulement
      les pixels transparents du DEHORS (reliés au bord de l'image par des pixels transparents, voisins haut, bas,
      gauche, droite) : les trous de la silhouette restent nets.
   3. tranches (2 en A, 7 en C) : y0 = n(h0) ; hh = 1 + n(max(1, h0//10)) (A) ou h0//7 (C) ;
      sens = +1 si n(2) sinon −1 ; dx = sens·(1 + n(max(2, w0//12))) (A) ou max(3, w0//5) (C), × s ;
      les lignes y0·s … (y0+hh)·s − 1 tournent de dx (nouveau[x] = ancien[(x − dx) mod w]).
   4. (C) balayage : chaque ligne y avec (y // s) % 3 == 0 : canaux × 78 // 100 (pixels pleins).
   5. (C) pixels morts : max(1, w0·h0 // 250) fois : yu = n(h0), xu = n(w0), c = [ROSE, CYAN, JAUNE, BLANC][n(4)] ;
      si le pixel (xu·s, yu·s) est plein, le bloc s × s y est peint de c (opaque).
   6. (C) tri : x0 = w0//4 + n(max(1, w0//2)), ww = 2 + n(2) ; chaque colonne x de x0·s à (x0+ww)·s − 1 (< w) : ses
      pixels pleins, de haut en bas, triés par r+g+b croissant (tri stable), reprennent les mêmes places.

  L'éclair (etat) : h = fnv1a-64(« graine:eclair ») ; période = 3000 + h % 2500 ms ; décalage = (h >> 20) % période ;
  u = (t + décalage) % période ; si u < 260 : style C, phase = ((t + décalage) // période % 4)·2 + (u ≥ 130) ;
  sinon style A, phase 0 (t en millisecondes).
"""
import time

MASQUE = (1 << 64) - 1
ROSE, CYAN, JAUNE, BLANC = 0xFF2878, 0x28E6FF, 0xF0FF50, 0xFFFFFF
MORTS = (ROSE, CYAN, JAUNE, BLANC)
ECLAIR_MS = 260                 # la durée d'un éclair (2 images à 8 par seconde)
REPERE = "▚"                    # le repère du nom (1 colonne dans un terminal), comme le ✨ du shiny


def fnv(texte):
    h = 0xCBF29CE484222325
    for o in texte.encode("utf-8"):
        h = ((h ^ o) * 0x100000001B3) & MASQUE
    return h


class Hasard:
    """splitmix64 (comme tirage.Hasard), état de départ : fnv1a-64 du texte."""

    def __init__(self, texte):
        self.etat = fnv(texte)

    def suivant(self):
        self.etat = (self.etat + 0x9E3779B97F4A7C15) & MASQUE
        z = self.etat
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASQUE
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASQUE
        return z ^ (z >> 31)

    def n(self, k):
        return self.suivant() % k


def _plein(p):
    return (p >> 24) & 255 != 0


def exterieur(w, h, plein):
    """Les pixels transparents reliés au bord de l'image (4 voisins) : le dehors de la silhouette."""
    dehors = [False] * (w * h)
    pile = [i for i in range(w * h) if not plein[i] and (i < w or i >= w * (h - 1) or i % w in (0, w - 1))]
    for i in pile:
        dehors[i] = True
    while pile:
        i = pile.pop()
        x = i % w
        for j in ((i - w) if i >= w else -1, (i + w) if i + w < w * h else -1, (i - 1) if x > 0 else -1,
                  (i + 1) if x < w - 1 else -1):
            if j >= 0 and not plein[j] and not dehors[j]:
                dehors[j] = True
                pile.append(j)
    return dehors


def appliquer(w, h, px, graine, style="A", phase=0, s=1):
    """Les pixels (liste d'entiers ARGB, w × h) avec l'effet : une NOUVELLE liste (voir la spécification)."""
    s = max(1, int(s))
    w0, h0 = max(1, w // s), max(1, h // s)
    r = Hasard(f"{graine}:{style}:{phase}")
    fort = style == "C"
    plein = [_plein(p) for p in px]
    out = list(px)
    if fort:                                                    # 1. couleurs ternies, tirées vers cyan / magenta
        for i, p in enumerate(out):
            if plein[i]:
                a, rr, gg, bb = p >> 24 & 255, p >> 16 & 255, p >> 8 & 255, p & 255
                m = (rr + gg + bb) // 3
                rr, gg, bb = (55 * rr + 45 * m) // 100, (55 * gg + 45 * m) // 100, (55 * bb + 45 * m) // 100
                rr, bb = min(255, rr * 105 // 100 + 18), min(255, bb * 110 // 100 + 28)
                out[i] = a << 24 | rr << 16 | gg << 8 | bb
    d = s * (max(2, w0 // 12) if fort else max(1, w0 // 24))  # 2. le liseré rose / cyan
    dehors = None if fort else exterieur(w, h, plein)
    for y in range(h):
        b = y * w
        for x in range(w):
            if not plein[b + x] and (dehors is None or dehors[b + x]):
                if x + d < w and plein[b + x + d]:
                    out[b + x] = 0xFF000000 | CYAN
                elif x - d >= 0 and plein[b + x - d]:
                    out[b + x] = 0xFF000000 | ROSE
    for _ in range(7 if fort else 2):                           # 3. les tranches décalées
        y0 = r.n(h0)
        hh = 1 + r.n(max(1, h0 // (7 if fort else 10)))
        sens = 1 if r.n(2) else -1
        dx = sens * (1 + r.n(max(3, w0 // 5) if fort else max(2, w0 // 12))) * s
        for y in range(y0 * s, min(h, (y0 + hh) * s)):
            ligne = out[y * w:(y + 1) * w]
            out[y * w:(y + 1) * w] = [ligne[(x - dx) % w] for x in range(w)]
    if fort:
        for y in range(h):                                      # 4. les lignes de balayage
            if (y // s) % 3 == 0:
                for i in range(y * w, (y + 1) * w):
                    p = out[i]
                    if _plein(p):
                        out[i] = (p & 0xFF000000 | (p >> 16 & 255) * 78 // 100 << 16
                                  | (p >> 8 & 255) * 78 // 100 << 8 | (p & 255) * 78 // 100)
        for _ in range(max(1, w0 * h0 // 250)):                 # 5. les pixels morts
            yu, xu, c = r.n(h0), r.n(w0), MORTS[r.n(4)]
            if yu * s < h and xu * s < w and _plein(out[yu * s * w + xu * s]):
                for y in range(yu * s, min(h, yu * s + s)):
                    for x in range(xu * s, min(w, xu * s + s)):
                        out[y * w + x] = 0xFF000000 | c
        x0 = w0 // 4 + r.n(max(1, w0 // 2))                     # 6. la bande de pixels triés
        ww = 2 + r.n(2)
        for x in range(x0 * s, min(w, (x0 + ww) * s)):
            ys = [y for y in range(h) if _plein(out[y * w + x])]
            vals = sorted((out[y * w + x] for y in ys), key=lambda p: (p >> 16 & 255) + (p >> 8 & 255) + (p & 255))
            for y, v in zip(ys, vals):
                out[y * w + x] = v
    return out


def etat(graine, t_ms=None):
    """(style, phase) à l'instant t (millisecondes ; maintenant si None) : A au repos, C pendant un éclair."""
    if t_ms is None:
        t_ms = int(time.time() * 1000)
    hh = fnv(f"{graine}:eclair")
    periode = 3000 + hh % 2500
    t2 = t_ms + (hh >> 20) % periode
    u = t2 % periode
    if u < ECLAIR_MS:
        return "C", (t2 // periode % 4) * 2 + (1 if u >= ECLAIR_MS // 2 else 0)
    return "A", 0


# ---------------------------------------------------------------- l'individu
def graine(ind):
    """La graine de l'effet d'un individu : son identifiant (toujours le même, sur chaque appareil et sur le site)."""
    return str(ind.get("id") or f"{ind.get('espece', '')}:{ind.get('date', 0)}")


def de(ind):
    """La graine si l'individu est glitch, sinon None."""
    return graine(ind) if isinstance(ind, dict) and ind.get("glitch") else None


def maintenant(ind):
    """(graine, style, phase) à cet instant pour un individu glitch, sinon None (pour les écrans qui se redessinent)."""
    g = de(ind)
    return None if g is None else (g,) + etat(g)


def _spec(glitch):
    """(graine, style, phase) depuis une graine seule (style A, au repos) ou un triplet, ou None."""
    if not glitch:
        return None
    if isinstance(glitch, tuple):
        return glitch
    return str(glitch), "A", 0


# ---------------------------------------------------------------- conversions
def depuis_hexa(couleurs):
    return [0 if c is None else 0xFF000000 | int(c[1:7], 16) for c in couleurs]


def vers_hexa(px):
    return [None if not _plein(p) else "#%06x" % (p & 0xFFFFFF) for p in px]


def hexa(w, h, couleurs, glitch, s=1):
    """Couleurs "#rrggbb" ou None (w × h) avec l'effet glitch (graine, ou (graine, style, phase)) ; inchangées sans."""
    g = _spec(glitch)
    if g is None:
        return couleurs
    return vers_hexa(appliquer(w, h, depuis_hexa(couleurs), g[0], g[1], g[2], s))


def rgba(w, h, octets, glitch, s=1):
    """Pixels RGBA (4 octets par pixel) avec l'effet (pour les images du bureau et de l'île) : un bytes."""
    g = _spec(glitch)
    if g is None:
        return octets
    px = [octets[4 * i + 3] << 24 | octets[4 * i] << 16 | octets[4 * i + 1] << 8 | octets[4 * i + 2] for i in range(w * h)]
    out = bytearray(4 * w * h)
    for i, p in enumerate(appliquer(w, h, px, g[0], g[1], g[2], s)):
        out[4 * i:4 * i + 4] = bytes((p >> 16 & 255, p >> 8 & 255, p & 255, p >> 24 & 255))
    return bytes(out)


class Images:
    """Une liste d'images (comme anim_auto.Paresseux) qui suit l'horloge : chaque image k est montrée au style A, ou au
    style C pendant un éclair ; calculées quand on les montre et gardées (au plus 4 éclairs différents par image)."""

    def __init__(self, n, faire, graine_):
        self.n, self.faire, self.graine, self.vu = n, faire, graine_, {}

    def __len__(self):
        return self.n

    def __getitem__(self, k):
        if isinstance(k, slice):
            return [self[i] for i in range(*k.indices(self.n))]
        if k < 0:
            k += self.n
        if not 0 <= k < self.n:
            raise IndexError(k)
        st, ph = etat(self.graine)
        cle = (k, st, ph)
        if cle not in self.vu:
            self.vu[cle] = self.faire(k, (self.graine, st, ph))
        return self.vu[cle]

    def __iter__(self):
        return (self[k] for k in range(self.n))
