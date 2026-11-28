"""Les sons du jeu (idées 81, 82, 83, 86, validées le 3 novembre) : tout est FABRIQUÉ ici, au moment de jouer.

Aucune banque de sons, aucun fichier son dans le jeu, rien de téléchargé, aucune bibliothèque tierce (pas de numpy) :
la recette de la maquette sonore (outils/ameliorations/sons/fabrique_sons.py) réécrite en Python pur. La même recette
existe en Kotlin (Sons.kt) ; les deux donnent EXACTEMENT les mêmes échantillons (vecteurs communs
donnees/sons/vecteurs.json, pc/outils/vecteurs_sons.py). Pour cela, aucune fonction mathématique du système : le sinus,
l'exponentielle et 2^x sont calculés ici avec seulement + − × ÷ (mêmes résultats sur Linux, Windows, macOS, Android).

  son("<nom>", state)    joue un son si les réglages le permettent (les autres modules n'appellent que ça)
      noms : reussite_petite, reussite_etape, reussite_grande, evolution (= grande réussite), erreur_douce,
             erreur_presque, refus_doux, cri:<espèce>[:<stade>][:shiny][:glitch], gardien_<espèce>, gardien_glitch,
             biome_<feu|eau|…> et gardiens_theme (des boucles : voir musique()).
  musique(cle, state)    la boucle qui joue (vues Monde et Espace seulement ; None = silence)
  commande(args)         tg son …

Les 8 décisions du propriétaire : musique seulement vue Monde / Espace ; 20 s de silence après 3 tours de boucle ;
cri plus aigu chez le bébé (+5 demi-tons, +2 l'ado) ; shiny = étincelle, glitch = le cri bégaie ; un son seulement
quand une étape avance (sinon la petite réussite une fois sur trois au plus) ; thème des gardiens aux rencontres et à
l'écran des boîtes ; tout se tait de 20 h 30 à 7 h 30 (bouton « ce soir seulement ») ; silencieux par défaut, et à la
première éclosion la créature demande une fois « Tu veux m'entendre ? ». Le mode classe coupe tout, toujours.

Lecture, sans rien de tiers : Linux, le lecteur du système (pw-play, sinon paplay, sinon aplay) nourri par l'entrée
standard, sinon silence ; Windows, winmm.dll (fait partie de Windows) par ctypes, sinon winsound ; macOS, afplay sur un
petit .wav dans ~/.terminagotchi/sons/. Jamais la cloche du terminal. Rien n'est jamais affiché si ça ne marche pas.
"""
import hashlib
import os
import struct
import subprocess
import sys
import threading
import time

SR = 22050
N = 1024                                   # taille des tables d'ondes (une période)
PI = 3.141592653589793
DEUX_PI = 6.283185307179586
LN2 = 0.6931471805599453
VERSION = 1


# ------------------------------------------------------------------ calcul exact (sans la bibliothèque mathématique)
def _sin_quart(x):
    """sin(x) pour 0 ≤ x ≤ π/2 (série de Taylor jusqu'à x^21)."""
    x2 = x * x
    terme = x
    s = x
    for k in range(1, 11):
        terme = -terme * x2 / ((2 * k) * (2 * k + 1))
        s = s + terme
    return s


def expo(x):
    """e^x avec seulement + − × ÷ (même résultat en Kotlin, Sons.expo)."""
    if x < -700.0:
        x = -700.0
    if x > 700.0:
        x = 700.0
    k = int(_plancher(x / LN2 + 0.5))
    r = x - k * LN2
    s = 1.0
    terme = 1.0
    for j in range(1, 18):
        terme = terme * r / j
        s = s + terme
    while k > 0:                           # × 2^k exactement (puissances de deux)
        p = min(k, 60)
        s = s * float(1 << p)
        k -= p
    while k < 0:
        p = min(-k, 60)
        s = s / float(1 << p)
        k += p
    return s


def _plancher(x):
    i = int(x)
    return i - 1 if x < i else i


def pow2(x):
    return expo(x * LN2)


def note(n):
    """Numéro MIDI -> fréquence (69 = la 440)."""
    return 440.0 * pow2((n - 69) / 12.0)


def _table_sin():
    q = N // 4
    t = [0.0] * (N + 1)
    for i in range(q + 1):
        t[i] = _sin_quart(DEUX_PI * i / N)
    for i in range(q + 1, 2 * q + 1):
        t[i] = t[2 * q - i]
    for i in range(2 * q + 1, N):
        t[i] = -t[i - 2 * q]
    t[N] = t[0]
    return t


SIN = _table_sin()
_TABLES = {}
PALIERS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 16, 20, 24]     # nombres d'harmoniques possibles (tables gardées)


def table(forme, duty, nh):
    """Une période d'onde « chiptune » sans repliement (somme de nh harmoniques), N+1 points."""
    cle = (forme, duty, nh)
    if cle in _TABLES:
        return _TABLES[cle]
    if forme == "sin":
        out = list(SIN)
    else:
        out = [0.0] * N
        if forme == "tri":
            for k in range(1, nh + 1, 2):
                c = (1.0 if ((k - 1) // 2) % 2 == 0 else -1.0) / (k * k)
                out = [o + c * SIN[(k * i) % N] for i, o in enumerate(out)]
            f = 8.0 / (PI * PI)
        elif forme == "carre":
            dd = int(duty * N / 2)
            for k in range(1, nh + 1):
                c = SIN[(k * dd) % N] / k
                q = N // 4
                out = [o + c * SIN[(k * i + q) % N] for i, o in enumerate(out)]
            f = 4.0 / PI * 0.5
        elif forme == "scie":
            for k in range(1, nh + 1):
                c = 1.0 / k
                out = [o + c * SIN[(k * i) % N] for i, o in enumerate(out)]
            f = 2.0 / PI * 0.6
        else:
            raise ValueError(forme)
        out = [o * f for o in out]
        out.append(out[0])
    _TABLES[cle] = out
    return out


def harmoniques(forme, fmax):
    plafond = {"tri": 15, "carre": 24, "scie": 20}.get(forme, 1)
    kmax = max(1, int((SR / 2 - 200) / max(fmax, 20.0)))
    k = min(kmax, plafond)
    return max(p for p in PALIERS if p <= k)


class Alea:
    """Petit hasard reproductible (xorshift 32 bits), le même en Kotlin (Sons.Alea)."""

    def __init__(self, graine):
        x = (int(graine) * 2654435761 + 1) & 0xFFFFFFFF
        self.x = x or 0x9E3779B9

    def suivant(self):
        x = self.x
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.x = x
        return x

    def hasard(self):
        return self.suivant() / 4294967296.0

    def entier(self, a, b):
        """Un entier de a (compris) à b (non compris)."""
        return a + self.suivant() % (b - a)


def md5(texte):
    try:
        return list(hashlib.md5(texte.encode("utf-8"), usedforsecurity=False).digest())
    except TypeError:                      # Python < 3.9
        return list(hashlib.md5(texte.encode("utf-8")).digest())


# ------------------------------------------------------------------ briques (des listes de nombres, 22 050 par seconde)
def bruit(n, graine=1):
    a = Alea(graine)
    return [a.hasard() * 2.0 - 1.0 for _ in range(n)]


def env(n, a=0.005, d=0.08, s=0.6, r=0.08):
    """Enveloppe : attaque linéaire, décroissance exponentielle vers s, relâche linéaire sur la fin."""
    a = max(a, 1e-6)
    d = max(d, 1e-6)
    ir = 1.0 / (max(r, 1e-6) * SR)
    na = a * SR
    out = [0.0] * n
    i0 = 0
    while i0 < n and i0 < na:
        out[i0] = i0 / na
        i0 += 1
    if i0 < n:
        dec = expo(-(i0 / SR - a) / d)
        kd = expo(-1.0 / (SR * d))
        for i in range(i0, n):
            out[i] = s + (1.0 - s) * dec
            dec = dec * kd
    for i in range(n):
        rel = (n - i) * ir
        if rel < 1.0:
            out[i] = out[i] * rel
    return out


def osc(forme, f0, nb, duty=0.5, vib=0.0, glis=0.0, dur=1.0):
    """nb échantillons d'une onde de fréquence f0 (vibrato vib, glissando de glis demi-tons sur dur secondes)."""
    gr = pow2(glis / (12.0 * max(dur, 1e-3) * SR)) if glis else 1.0
    fmax = f0 * (1.0 + vib) * (pow2(glis / 12.0) if glis > 0 else 1.0)
    t = table(forme, duty, harmoniques(forme, fmax)) if forme != "sin" else SIN
    out = [0.0] * nb
    ph = 0.0
    if not vib and not glis:
        inc = f0 / SR
        for i in range(nb):
            ph = ph + inc
            if ph >= 1.0:
                ph = ph - 1.0
            x = ph * N
            j = int(x)
            out[i] = t[j] + (t[j + 1] - t[j]) * (x - j)
        return out
    g = 1.0
    vph = 0.0
    vinc = 5.5 / SR
    for i in range(nb):
        x = vph * N
        j = int(x)
        sv = SIN[j] + (SIN[j + 1] - SIN[j]) * (x - j)
        f = f0 * (1.0 + vib * sv) * g
        g = g * gr
        vph = vph + vinc
        if vph >= 1.0:
            vph = vph - 1.0
        ph = ph + f / SR
        while ph >= 1.0:
            ph = ph - 1.0
        x = ph * N
        j = int(x)
        out[i] = t[j] + (t[j + 1] - t[j]) * (x - j)
    return out


def ton(forme, n, dur, vol=0.3, duty=0.5, a=0.005, d=0.1, s=0.6, r=0.05, vib=0.0, glis=0.0):
    nb = int(dur * SR)
    o = osc(forme, note(n), nb, duty, vib, glis, dur)
    e = env(nb, a, d, s, r)
    return [o[i] * e[i] * vol for i in range(nb)]


def sinus_amorti(freq, nb, tau, vol):
    """Un petit « toc » : sinus de freq Hz qui s'éteint (constante tau en échantillons)."""
    k = expo(-1.0 / tau)
    e = 1.0
    ph = 0.0
    inc = freq / SR
    out = [0.0] * nb
    for i in range(nb):
        x = ph * N
        j = int(x)
        out[i] = (SIN[j] + (SIN[j + 1] - SIN[j]) * (x - j)) * e * vol
        e = e * k
        ph = ph + inc
        if ph >= 1.0:
            ph = ph - 1.0
    return out


def amorti(x, tau, vol):
    k = expo(-1.0 / tau)
    e = 1.0
    out = [0.0] * len(x)
    for i in range(len(x)):
        out[i] = x[i] * e * vol
        e = e * k
    return out


def passe_bas(x, fc):
    """Filtre passe-bas à un pôle (doux : enlève l'agressivité des carrés)."""
    a = expo(-DEUX_PI * fc / SR)
    b = 1.0 - a
    acc = 0.0
    out = [0.0] * len(x)
    for i, v in enumerate(x):
        acc = b * v + a * acc
        out[i] = acc
    return out


def passe_bas_boucle(x, fc):
    """Passe-bas d'une boucle : filtré sur deux tours, on garde le second (l'état du filtre raccorde)."""
    return passe_bas(x + x, fc)[len(x):]


def echo(x, ms=180, fb=0.3, mix=0.25, boucle=False):
    """Petit écho ; en boucle, la queue revient au début (boucle sans couture)."""
    d = int(ms * SR / 1000)
    n = len(x)
    y = list(x)
    g = mix
    for k in range(1, 6):
        sh = d * k
        if boucle:
            sh = sh % n
            dec = x[n - sh:] + x[:n - sh] if sh else x
            y = [a + g * b for a, b in zip(y, dec)]
        elif sh < n:
            y[sh:] = [a + g * b for a, b in zip(y[sh:], x[:n - sh])]
        g = g * fb
    return y


def place(piste, son_, t, boucle=False):
    """Pose un son dans la piste ; en boucle, ce qui dépasse la fin revient au début (pas de clic à la couture)."""
    i = int(t * SR)
    n = len(piste)
    j = min(n, i + len(son_))
    for k in range(i, j):
        piste[k] += son_[k - i]
    if boucle and i + len(son_) > n:
        reste = son_[n - i:] if i < n else son_
        for k in range(min(len(reste), n)):
            piste[k] += reste[k]


def normaliser(x, crete=0.5):
    m = 0.0
    for v in x:
        if v > m:
            m = v
        elif -v > m:
            m = -v
    if m == 0.0:
        m = 1.0
    return [v / m * crete for v in x]


def fondu(x, ms=8):
    n = int(ms * SR / 1000)
    x = list(x)
    for i in range(min(20, len(x))):
        x[i] = x[i] * (i / 19.0)
    L = len(x)
    for j in range(min(n, L)):
        x[L - n + j] = x[L - n + j] * ((n - 1 - j) / (n - 1.0))
    return x


def zeros(n):
    return [0.0] * n


# ------------------------------------------------------------------ 81. musiques des 9 biomes
GAMMES = {
    "majeur_penta": [0, 2, 4, 7, 9], "mineur_penta": [0, 3, 5, 7, 10], "dorien": [0, 2, 3, 5, 7, 9, 10],
    "lydien": [0, 2, 4, 6, 7, 9, 11], "mixo": [0, 2, 4, 5, 7, 9, 10], "majeur": [0, 2, 4, 5, 7, 9, 11],
    "par_tons": [0, 2, 4, 6, 8, 10], "mineur": [0, 2, 3, 5, 7, 8, 10],
}
# tonique, gamme, tempo, accords (degrés), instrument de mélodie, rapport cyclique, ambiance, motif (-1 = silence ;
# le motif est celui de la maquette validée)
BIOMES = {
    "feu": (62, "dorien", 104, [0, 3, 4, 3], "carre", 0.25, "crepit", [1, 1, -1, 3, 1, 3, -1, -1]),
    "eau": (65, "lydien", 88, [0, 1, 4, 3], "tri", 0.5, "bulles", [-1, -1, 3, 4, 5, 7, 8, 6]),
    "glace": (64, "mineur_penta", 72, [0, 3, 2, 4], "sin", 0.5, "cloche", [0, 2, 3, 4, -1, 2, 2, 1]),
    "plante": (67, "majeur_penta", 96, [0, 3, 4, 0], "carre", 0.5, "oiseau", [0, 1, 1, 3, 5, 4, 5, 6]),
    "roche": (57, "mineur_penta", 84, [0, 2, 3, 2], "tri", 0.5, "bois", [1, 2, -1, -1, -1, -1, 0, -1]),
    "ciel": (72, "majeur", 70, [0, 3, 5, 4], "sin", 0.5, "souffle", [1, 1, 0, 2, 0, 1, 2, 3]),
    "ombre": (59, "mineur", 66, [0, 5, 3, 4], "tri", 0.5, "goutte", [0, 1, 3, 4, 5, 4, 5, 4]),
    "machine": (60, "mixo", 112, [0, 6, 3, 4], "carre", 0.125, "tic", [2, -1, -1, 2, 2, 3, 1, -1]),
    "poison": (63, "par_tons", 92, [0, 1, 2, 1], "carre", 0.375, "bloup", [0, -1, 0, 1, 2, 0, 0, 0]),
}


def degre(b, d, octave=0):
    g = GAMMES[b[1]]
    L = len(g)
    return b[0] + 12 * (octave + d // L) + g[d % L]


def musique_biome(cle):
    b = BIOMES[cle]
    tonique, gamme, bpm, accords, mel, duty, amb, motif = b
    al = Alea(int("".join("%02x" % c for c in md5(cle))[:8], 16))
    noire = 60.0 / bpm
    mesures = 4
    dur = mesures * 4 * noire
    piste = zeros(int(dur * SR))
    L = len(GAMMES[gamme])
    for m, acc in enumerate(accords):
        t0 = m * 4 * noire
        for k in (0, 2):                                     # basse (triangle), deux notes par mesure
            n = degre(b, acc + (0 if k == 0 else 4 % L), -2)
            place(piste, ton("tri", n, noire * 1.9, 0.22, d=0.3, s=0.5, r=0.08), t0 + k * noire, True)
        for k in range(8):                                   # arpège d'accompagnement doux (carré fin)
            n = degre(b, acc + [0, 2, 4, 2][k % 4], -1)
            place(piste, ton("carre", n, noire * 0.45, 0.05, duty=0.25, d=0.06, s=0.2), t0 + k * noire / 2, True)
        for k, p in enumerate(motif):                        # mélodie
            if p < 0:
                continue
            p2 = p + (acc if m != 3 else acc - 1)
            if m == 3 and k >= 6:
                continue
            n = degre(b, p2, 0)
            place(piste, ton(mel, n, noire * 0.48, 0.13 if mel != "sin" else 0.18, duty=duty,
                             d=0.12, s=0.45, vib=0.004 if k % 2 else 0.0), t0 + k * noire / 2, True)
    for i in range(mesures * 4):                             # ambiance propre au biome (toujours douce)
        t = i * noire
        if amb == "crepit":
            for _ in range(2):
                g = al.entier(0, 1000000)
                c = amorti(bruit(int(0.015 * SR), g), 60.0, 0.12)
                place(piste, c, t + al.hasard() * noire, True)
        elif amb == "bulles" and i % 2 == 1:
            place(piste, ton("sin", 84 + al.entier(0, 6), 0.07, 0.06, d=0.03, s=0.1, glis=7), t + noire / 2, True)
        elif amb == "cloche" and i % 4 == 2:
            place(piste, ton("sin", degre(b, al.entier(0, 5), 2), 0.9, 0.05, d=0.4, s=0.0), t, True)
        elif amb == "oiseau" and i % 8 == 5:
            for j in range(3):
                place(piste, ton("sin", 91 + j, 0.05, 0.035, glis=4), t + j * 0.07, True)
        elif amb == "bois":
            place(piste, sinus_amorti(380.0, int(0.04 * SR), 120.0, 0.12 if i % 2 == 0 else 0.06), t, True)
        elif amb == "souffle" and i == 0:
            s = passe_bas(bruit(int(dur * SR), 7), 500)
            L2 = len(s)
            for j in range(L2):
                x = (j / L2) * N
                q = int(x)
                sv = SIN[q] + (SIN[q + 1] - SIN[q]) * (x - q)
                s[j] = s[j] * 0.25 * (0.5 + 0.5 * sv * sv)
            place(piste, s, 0, True)
        elif amb == "goutte" and i % 3 == 1:
            g = ton("sin", 88 + al.entier(0, 4), 0.06, 0.05, d=0.02, s=0.0, glis=-5)
            place(piste, g, t + noire * al.hasard(), True)
        elif amb == "tic":
            place(piste, amorti(bruit(int(0.01 * SR), i), 30.0, 0.08), t, True)
            place(piste, amorti(bruit(int(0.01 * SR), i + 99), 30.0, 0.04), t + noire / 2, True)
        elif amb == "bloup" and i % 4 == 3:
            place(piste, ton("sin", 50, 0.12, 0.12, d=0.05, s=0.2, glis=12), t + noire / 2, True)
    piste = passe_bas_boucle(piste, 4200)
    piste = echo(piste, ms=int(noire * 750), fb=0.35, mix=0.22, boucle=True)
    return normaliser(piste, 0.45)


# ------------------------------------------------------------------ 82. un cri par espèce
TIMBRE = {   # famille -> forme d'onde, rapport cyclique, contour, extra
    "Démons": ("carre", 0.25, "pique", "crepit"),
    "Élémentaires": ("tri", 0.5, "vague", None),
    "Morts-vivants": ("sin", 0.5, "ouh", "vibrato"),
    "Bêtes monstrueuses": ("scie", 0.5, "grogne", None),
    "Sylvestres": ("tri", 0.5, "flute", "souffle"),
    "Arthropodes": ("carre", 0.125, "trille", None),
    "Abyssaux": ("sin", 0.5, "bulle", None),
    "Célestes": ("sin", 0.5, "etoile", "cloche"),
    "Constructs": ("carre", 0.5, "bipboup", None),
    "Aberrations": ("tri", 0.5, "bizarre", "wobble"),
}
AGE = {"bebe": 5, "enfant": 3, "ado": 2}     # le bébé crie plus aigu (décision du 3 novembre)
RARES = ("rare", "légendaire", "mythique")


def taille(cm):
    """La hauteur selon la taille finale (colossale = grave, petite = aigu), comme la maquette."""
    cm = float(cm or 90)
    return 5 if cm <= 30 else 0 if cm <= 90 else -5 if cm <= 220 else -12


def cri(eid, famille, taille_cm, rarete, stade="", shiny=False, glitch=False):
    """Le cri d'une espèce : le timbre vient de la famille, la hauteur de la taille (et de l'âge), le reste de l'id."""
    h = md5(eid)
    forme, duty, contour, extra = TIMBRE.get(famille, TIMBRE["Constructs"])
    base = 69 + taille(taille_cm) + (h[0] % 7) - 3 + AGE.get(stade, 0)
    nb_syll = 1 + h[1] % 3
    lg = 0.13 + (h[2] % 6) * 0.025
    sortie = []
    for s in range(nb_syll):
        n0 = base + [0, 3, -2, 5, 7][(h[3] + s) % 5]
        sg = 1 if s % 2 == 0 else -1
        g, v = {"pique": (5 + h[4] % 5, 0.0), "vague": (sg * 4, 0.01), "ouh": (-3, 0.02), "grogne": (2, 0.03),
                "flute": (1, 0.006), "trille": (0, 0.0), "bulle": (9 + h[4] % 5, 0.0), "etoile": (2, 0.0),
                "bipboup": (0, 0.0)}.get(contour, ((1 if (h[4] + s) % 2 == 0 else -1) * 7, 0.0))
        d = lg * (1.5 if contour in ("ouh", "flute") else 1)
        if contour == "trille":
            x = []
            for k in range(int(d / 0.03) + 2):
                x += ton(forme, n0 + (k % 2) * 2, 0.03, 0.3, duty, d=0.01, s=0.6, r=0.008)
        elif contour == "bipboup":
            x = ton(forme, n0 + (s % 2) * 5, d, 0.3, duty, d=0.04, s=0.7, r=0.02)
        else:
            x = ton(forme, n0, d, 0.35, duty, a=0.012, d=0.06, s=0.65, r=0.04, vib=v, glis=g)
        if extra == "wobble":
            ph, inc = 0.0, 14.0 / SR
            for i in range(len(x)):
                q = ph * N
                j = int(q)
                x[i] = x[i] * (0.7 + 0.3 * (SIN[j] + (SIN[j + 1] - SIN[j]) * (q - j)))
                ph = ph + inc
                if ph >= 1.0:
                    ph = ph - 1.0
        if extra == "cloche" and len(x) <= int(d * 1.6 * SR):
            c = ton("sin", n0 + 19, d * 1.6, 0.08, d=0.08, s=0.0)
            x = [a + c[i] for i, a in enumerate(x)]
        if extra == "souffle":
            b_ = passe_bas(bruit(len(x), h[5]), 1500)
            e = env(len(x), 0.02, 0.05, 0.4, 0.03)
            x = [a + b_[i] * e[i] * 0.12 for i, a in enumerate(x)]
        if extra == "crepit":
            n = min(int(0.012 * SR), len(x))
            b_ = bruit(int(0.012 * SR), h[6])
            for i in range(n):
                x[i] = x[i] + b_[i] * 0.15
        if contour == "grogne":
            x = [v_ * 1.6 for v_ in passe_bas(x, 1400)]
        sortie.append(x)
        sortie.append(zeros(int((0.025 + (h[7] % 3) * 0.02) * SR)))
    x = [v_ for part in sortie[:-1] for v_ in part]
    if rarete in RARES or shiny:                     # les rares (et les shiny) ont une petite étincelle à la fin
        x += zeros(int(0.02 * SR))
        place(x, ton("sin", base + 24, 0.12, 0.07, d=0.05, s=0.0), max(0.0, len(x) / SR - 0.14))
        if shiny and rarete in RARES:                # rare ET shiny : deux étincelles
            x += zeros(int(0.06 * SR))
            place(x, ton("sin", base + 31, 0.12, 0.06, d=0.05, s=0.0), max(0.0, len(x) / SR - 0.13))
    x = passe_bas(x, 5000)
    x = fondu(normaliser(echo(x, 70, 0.2, 0.12), 0.42), 5)
    if glitch:
        x = glitcher(x, h[8] + 256 * h[9])
    return x


# ------------------------------------------------------------------ 83. réussite et erreur
def suite(notes, forme="carre", duty=0.5, vol=0.3, ecart=0.08, lg=0.12, **kw):
    x = zeros(int((ecart * len(notes) + lg + 0.4) * SR))
    for i, n in enumerate(notes):
        place(x, ton(forme, n, lg, vol, duty, **kw), i * ecart)
    return x


def son_retour(nom):
    if nom == "reussite_petite":
        x = suite([79, 84], "carre", 0.25, ecart=0.07, lg=0.09, d=0.05, s=0.4)
    elif nom == "reussite_etape":
        x = suite([72, 76, 79, 84], "carre", 0.25, ecart=0.075, lg=0.14, d=0.07, s=0.5)
    elif nom == "reussite_grande":
        x = suite([72, 76, 79, 84, 88, 91], "carre", 0.25, ecart=0.07, lg=0.16, d=0.08, s=0.5)
        place(x, ton("tri", 48, 0.7, 0.25, d=0.3, s=0.4), 0.0)
        place(x, ton("sin", 96, 0.4, 0.08, d=0.2, s=0.0), 0.42)
    elif nom == "erreur_douce":       # jamais agressive : triangle, deux notes qui descendent d'une tierce
        x = suite([71, 67], "tri", ecart=0.12, lg=0.14, vol=0.25, d=0.08, s=0.5)
    elif nom == "erreur_presque":     # une note qui hésite et remonte (encourageant)
        x = suite([69, 67, 69], "sin", ecart=0.09, lg=0.1, vol=0.25, d=0.05, s=0.5)
    elif nom == "refus_doux":         # cadenas, dossier pas vide : un petit toc de bois
        t = sinus_amorti(520.0, int(0.06 * SR), 160.0, 0.35)
        x = t + zeros(int(0.07 * SR)) + [v * 0.6 for v in t] + zeros(int(0.1 * SR))
    else:
        raise KeyError(nom)
    crete = 0.4 if nom.startswith("reussite") else 0.3       # les erreurs : 25 % moins fortes qu'une réussite
    return fondu(normaliser(echo(passe_bas(x, 5000), 90, 0.25, 0.15), crete))


# ------------------------------------------------------------------ 86. thème des gardiens
GARDIENS = [("enumeration", "ricanombre", 0), ("droits", "heaumbre", 2), ("secrets", "cranard", 3),
            ("hangar", "ombrachne", 5), ("scripts", "marionnoire", 7), ("codes", "torsillon", 8),
            ("forensique", "osselet", 10), ("social", "drapouille", 12)]
LEITMOTIV = [0, 3, 7, 6, 3, 2, 0, -2]   # demi-tons, « mystère gentil »


def theme_gardiens():
    noire = 60.0 / 80
    dur = 16 * noire * 2
    x = zeros(int(dur * SR))
    base = 64
    accords = [[0, 3, 7], [-4, 0, 3], [-7, -4, 0], [-1, 3, 6]]
    for m in range(8):
        a = accords[m % 4]
        t0 = m * 4 * noire
        place(x, ton("tri", base - 24 + a[0], 4 * noire * 0.98, 0.25, d=1.0, s=0.6, r=0.2), t0, True)
        for k in range(8):                   # pulsation feutrée façon cœur de forteresse
            place(x, ton("carre", base - 12 + a[k % 3], noire * 0.3, 0.05, 0.125, d=0.05, s=0.2), t0 + k * noire / 2, True)
        if m in (0, 1, 4, 5):
            for k, iv in enumerate(LEITMOTIV):
                if m % 2 == 1 and k >= 4:
                    iv = LEITMOTIV[k] - 2
                place(x, ton("carre", base + iv, noire * 0.45, 0.13, 0.25, d=0.12, s=0.5, vib=0.004), t0 + k * noire / 2, True)
        if m in (2, 3, 6, 7):
            for k, iv in enumerate([7, 6, 3, 0]):
                place(x, ton("sin", base + 12 + iv, noire * 0.95, 0.12, d=0.3, s=0.4, vib=0.006), t0 + k * noire, True)
    x = echo(passe_bas_boucle(x, 3800), int(noire * 750), 0.35, 0.25, boucle=True)
    return normaliser(x, 0.45)


def motif_gardien(i):
    formes = ["carre", "tri", "sin", "scie", "carre", "tri", "sin", "carre"]
    duty = [0.25, 0.5, 0.5, 0.5, 0.125, 0.5, 0.5, 0.375][i]
    base = 60 + GARDIENS[i][2] % 12
    x = zeros(int(2.6 * SR))
    for k, iv in enumerate(LEITMOTIV[:5]):
        place(x, ton(formes[i], base + iv, 0.28, 0.25, duty, d=0.1, s=0.5, vib=0.005), k * 0.22)
    place(x, ton("tri", base - 12, 1.4, 0.25, d=0.6, s=0.3), 0)
    place(x, ton("sin", base + 19, 0.8, 0.08, d=0.3, s=0.0), 1.1)
    return fondu(normaliser(echo(passe_bas(x, 4200), 200, 0.35, 0.25), 0.42))


def glitcher(x, graine=5):
    """Version « glitch » : petites répétitions saccadées (bégaiement de bande), sans grésillement agressif."""
    al = Alea(graine)
    y = list(x)
    n = len(x)
    for _ in range(6):
        i = al.entier(0, max(1, n - 4000))
        lg = al.entier(400, 1400)
        frag = x[i:i + lg]
        for r in range(al.entier(2, 4)):
            j = i + r * lg
            if j + lg < n:
                y[j:j + lg] = frag
    y = [_plancher(v * 24 + 0.5) / 24.0 for v in y]           # bits réduits : léger « vieux jeu »
    return fondu(normaliser(passe_bas(y, 4500), 0.4))


# ------------------------------------------------------------------ le catalogue
RETOURS = ("reussite_petite", "reussite_etape", "reussite_grande", "erreur_douce", "erreur_presque", "refus_doux")
ALIAS = {"evolution": "reussite_grande", "palier": "reussite_grande", "nouvelle_creature": "reussite_grande",
         "etape": "reussite_etape", "exploit": "reussite_grande", "erreur": "erreur_douce", "presque": "erreur_presque",
         "refus": "refus_doux", "reussite": "reussite_petite"}
_ESPECES = None


def especes():
    """{id: (famille, taille_cm, rareté)} lu dans le bestiaire du jeu (rien d'autre)."""
    global _ESPECES
    if _ESPECES is None:
        try:
            from . import bestiaire as B
            _ESPECES = {e["id"]: (e.get("famille", ""), e.get("taille_cm", 90), e.get("rarete", ""))
                        for e in B.especes()}
        except Exception:                  # noqa: BLE001 — sans bestiaire : un cri neutre
            _ESPECES = {}
    return _ESPECES


def categorie(nom):
    nom = ALIAS.get(nom, nom)
    if nom.startswith("biome_") or nom == "gardiens_theme":
        return "musique"
    if nom.startswith(("cri:", "gardien_")):
        return "cris"
    return "retours"


def fabriquer(nom):
    """Les échantillons (nombres de −1 à 1) d'un son du catalogue. KeyError si le nom est inconnu."""
    nom = ALIAS.get(nom, nom)
    if nom in RETOURS:
        return son_retour(nom)
    if nom.startswith("biome_") and nom[6:] in BIOMES:
        return musique_biome(nom[6:])
    if nom == "gardiens_theme":
        return theme_gardiens()
    if nom == "gardien_glitch":
        return glitcher(motif_gardien(0))
    if nom.startswith("gardien_"):
        for i, g in enumerate(GARDIENS):
            if g[1] == nom[8:]:
                return motif_gardien(i)
        raise KeyError(nom)
    if nom.startswith("cri:"):
        p = nom.split(":")
        eid = p[1]
        fam, cm, rar = especes().get(eid, ("", 90, ""))
        stade = next((x for x in p[2:] if x in ("bebe", "enfant", "ado", "adulte", "ancien")), "")
        return cri(eid, fam, cm, rar, stade, "shiny" in p[2:], "glitch" in p[2:])
    raise KeyError(nom)


def pcm(x):
    """Les échantillons en entiers 16 bits (arrondi : plancher de x × 32767 + ½)."""
    out = []
    for v in x:
        s = _plancher(v * 32767.0 + 0.5)
        out.append(32767 if s > 32767 else -32767 if s < -32767 else s)
    return out


def empreinte(ech):
    return hashlib.sha256(struct.pack("<%dh" % len(ech), *ech)).hexdigest()


_CACHE = {}
_CACHE_VERROU = threading.Lock()


def echantillons(nom):
    """pcm(fabriquer(nom)), gardé en mémoire (une boucle se fabrique une fois)."""
    nom = ALIAS.get(nom, nom)
    with _CACHE_VERROU:
        if nom in _CACHE:
            return _CACHE[nom]
    e = pcm(fabriquer(nom))
    with _CACHE_VERROU:
        _CACHE[nom] = e
        if len(_CACHE) > 40:
            for k in [k for k in _CACHE if not k.startswith(("biome_", "gardiens_"))][:10]:
                _CACHE.pop(k, None)
    return e


def nom_cri(eid, stade="", shiny=False, glitch=False):
    return "cri:" + eid + (":" + stade if stade else "") + (":shiny" if shiny else "") + (":glitch" if glitch else "")


# ------------------------------------------------------------------ réglages et permissions (mêmes règles en Kotlin)
DEFAUTS = {"on": False, "musique": False, "v_musique": 30, "v_cris": 60, "v_retours": 50, "soir": "", "demande": False,
           "n": 0}
NUIT_DEBUT = 20 * 60 + 30
NUIT_FIN = 7 * 60 + 30


def reglages(state):
    """Les réglages du son (state["config"]["son"]), complétés par les valeurs par défaut : silencieux."""
    c = state.setdefault("config", {}) if isinstance(state, dict) else {}
    r = c.get("son")
    if not isinstance(r, dict):
        r = {}
        if isinstance(state, dict):
            c["son"] = r
    for k, v in DEFAUTS.items():
        r.setdefault(k, v)
    return r


def soiree(annee, mois, jour, minutes):
    """La soirée en cours (« 2026-11-03 » de 20 h 30 au lendemain 7 h 30), ou "" le jour."""
    if NUIT_FIN <= minutes < NUIT_DEBUT:
        return ""
    if minutes < NUIT_FIN:                          # après minuit : la soirée de la veille
        import datetime
        d = datetime.date(annee, mois, jour) - datetime.timedelta(days=1)
        annee, mois, jour = d.year, d.month, d.day
    return "%04d-%02d-%02d" % (annee, mois, jour)


def _maintenant(quand=None):
    lt = time.localtime(quand if quand is not None else time.time())
    return lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour * 60 + lt.tm_min


def permis(r, cat, annee, mois, jour, minutes, classe=False, dort=False):
    """Ce son peut-il jouer ? r : les réglages ; cat : musique, cris ou retours. Même table de vérité en Kotlin."""
    if not r.get("on") or classe:
        return False
    if cat == "musique" and not r.get("musique"):
        return False
    if int(r.get("v_" + cat, 0) or 0) <= 0:
        return False
    s = soiree(annee, mois, jour, minutes)
    if s and r.get("soir") != s:                    # la nuit : silence, sauf « ce soir seulement »
        return False
    if cat == "cris" and dort:                      # la créature qui dort ne fait jamais de bruit
        return False
    return True


def _classe(state):
    if CLASSE:
        return True
    try:
        from . import classe
        return bool(classe.actif(state))
    except Exception:                       # noqa: BLE001
        return False


def _dort(state):
    try:
        a = state.get("anim") or ()
        return bool(a) and a[0] == "dort" and time.time() - float(a[1]) < 30
    except Exception:                       # noqa: BLE001
        return False


def peut(state, nom, quand=None):
    if not isinstance(state, dict):
        return False
    return permis(reglages(state), categorie(nom), *_maintenant(quand), classe=_classe(state), dort=_dort(state))


def volume(state, nom):
    return max(0, min(100, int(reglages(state).get("v_" + categorie(nom), 0) or 0)))


# ------------------------------------------------------------------ quel son après un tour de jeu (même règle en Kotlin)
def resume(state):
    """Les compteurs du jeu qui décident du son de retour (rien d'autre n'est regardé)."""
    if not isinstance(state, dict):
        return None
    try:
        from . import core
        niv = core.level(state.get("xp", 0))
        stade = core.stage(niv)
    except Exception:                       # noqa: BLE001
        niv = stade = 0
    rec = state.get("recompenses") if isinstance(state.get("recompenses"), dict) else {}
    return {"lecon": state.get("lesson", 0), "etape": state.get("step", 0), "niveau": niv, "stade": stade,
            "exploits": len(rec.get("exploits") or {}), "collection": len(state.get("collection") or {}),
            "total": state.get("total", 0)}


def choisir(avant, apres, marque="", n=0):
    """(nom du son ou "", nouveau compteur) : AU PLUS un son de retour par tour de jeu (une rafale = un seul son).
    marque : erreur_douce, erreur_presque ou refus_doux (posée par le tour quand la commande a buté)."""
    if not avant or not apres:
        return "", n
    if apres["stade"] > avant["stade"]:
        return ("eclosion" if avant["stade"] == 0 else "evolution"), n
    if apres["exploits"] > avant["exploits"] or apres["collection"] > avant["collection"] \
            or apres["niveau"] > avant["niveau"]:
        return "reussite_grande", n
    if (apres["lecon"], apres["etape"]) != (avant["lecon"], avant["etape"]):
        return "reussite_etape", n
    if marque in ("erreur_douce", "erreur_presque", "refus_doux"):
        return marque, n
    if apres["total"] > avant["total"]:              # une commande juste : la petite réussite une fois sur trois
        n += 1
        return ("reussite_petite" if n % 3 == 0 else ""), n % 3
    return "", n


def apres_tour(state, avant, apres):
    """Appelé par app.etape après le tour de jeu : joue le son de retour s'il y en a un (jamais d'erreur)."""
    try:
        r = reglages(state)
        marque = state.pop("_son", "") or ""
        nom, r["n"] = choisir(avant, apres, marque, int(r.get("n", 0) or 0))
        if nom == "eclosion":
            demander(state)
            e = state.get("espece_compagnon") or ""
            son(nom_cri(e, "bebe", bool(state.get("shiny"))) if e else "reussite_grande", state)
        elif nom:
            son(nom, state)
    except Exception:                       # noqa: BLE001 — le son ne gêne jamais le jeu
        pass


def nom_apparition(e_id, ind, nouvelle):
    """Le son d'une bestiole qui apparaît : le motif du gardien (qui bégaie s'il est glitch), sinon son cri si c'est
    une espèce pas encore rencontrée (shiny : étincelle ; glitch : il bégaie), sinon rien. Même règle en Kotlin."""
    ind = ind if isinstance(ind, dict) else {}
    b = ind.get("gardien")
    if b:
        if ind.get("glitch"):
            return "gardien_glitch"
        g = next((x[1] for x in GARDIENS if x[0] == b), None)
        return "gardien_" + g if g else ""
    if nouvelle and e_id:
        return nom_cri(e_id, "", bool(ind.get("shiny")), bool(ind.get("glitch")))
    return ""


def apparition(state, e, ind):
    """explo.spawn : une bestiole vient d'apparaître (rencontre)."""
    try:
        nouvelle = not (state.get("collection") or {}).get(e.get("nom"))
        nom = nom_apparition(e.get("id", ""), ind, nouvelle)
        if nom:
            son(nom, state)
    except Exception:                       # noqa: BLE001
        pass


def marquer(state, nom):
    """Le tour a buté (commande inconnue, presque, refusée) : le son à faire (s'il n'y a pas mieux)."""
    if isinstance(state, dict) and not state.get("_son"):
        state["_son"] = nom


def demander(state):
    """La première éclosion : la créature demande une fois « Tu veux m'entendre ? » (silencieux par défaut)."""
    r = reglages(state)
    if r.get("demande"):
        return
    r["demande"] = True
    try:
        from . import core
        from .langue import t
        core.say(state, t("son.question"), 20)
        core.terminal(state, t("son.question.terminal", cmd="tg son", nom=state.get("name", "")))
    except Exception:                       # noqa: BLE001
        pass


# ------------------------------------------------------------------ jouer (bibliothèque standard seulement)
JOURNAL = []                               # ce qui a été demandé (les tests le lisent ; rien n'est joué sans réglages)
_LECTEUR = None
_DERNIERS = {}                             # nom -> dernière fois qu'il a été joué (pas deux fois en 3 s)
LONG = False                               # une fenêtre qui dure (bureau, espace, monde) : son mélangeur à elle
CLASSE = False                             # l'espace en grand écran pour la classe (tg espace classe) : aucun son


def son(nom, state=None):
    """Le point d'entrée des autres modules : son("evolution", state). Ne lève jamais d'erreur, ne bloque jamais.
    Sans state, les réglages sont relus dans la sauvegarde. Rien ne joue si les réglages ne le permettent pas."""
    try:
        if state is None:
            from . import core
            state = core.load()
        nom = ALIAS.get(nom, nom)
        if not peut(state, nom):
            return False
        maintenant = time.monotonic()
        if maintenant - _DERNIERS.get(nom, -10.0) < 3.0:   # le même son demandé deux fois de suite (le tour de jeu
            return True                                     # et l'animation d'évolution) : on ne l'entend qu'une fois
        _DERNIERS[nom] = maintenant
        vol = volume(state, nom)
        JOURNAL.append(nom)
        del JOURNAL[:-50]
        if os.environ.get("TG_SON_MUET"):          # les tests : on note, on ne joue pas
            return True
        if LONG or (_LECTEUR is not None and _LECTEUR.vivant()):
            lecteur().jouer(nom, vol)
        else:
            jouer_detache(nom, vol)
        return True
    except Exception:                       # noqa: BLE001
        return False


def jouer_detache(nom, vol):
    """Un processus court (l'invite du shell) : le son est joué par un petit processus à part, qui rend la main tout de
    suite (tg son _jouer <nom> <volume>)."""
    try:
        from . import compagnon
        exe, app = compagnon.commande()
    except Exception:                       # noqa: BLE001
        return
    kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x08000000      # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen([exe, app, "son", "_jouer", nom, str(int(vol))], **kw)
    except OSError:
        pass


def wav(ech):
    """Un fichier .wav (mono, 16 bits, 22 050 Hz) en mémoire."""
    data = struct.pack("<%dh" % len(ech), *ech)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16) + b"data" + struct.pack("<I", len(data)) + data)


def _qui(cmd):
    import shutil
    return shutil.which(cmd)


LINUX = [["pw-play", "--raw", "--rate", str(SR), "--channels", "1", "--format", "s16", "-"],
         ["paplay", "--raw", "--rate=%d" % SR, "--channels=1", "--format=s16le"],
         ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(SR), "-c", "1", "-"]]


class SortiePipe:
    """Le lecteur du système, nourri en flux par son entrée standard (Linux)."""

    def __init__(self):
        self.p = None
        for cmd in LINUX:
            if not _qui(cmd[0]):
                continue
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                continue
            time.sleep(0.15)
            if p.poll() is None:            # il tourne : c'est lui
                self.p = p
                break
        if self.p is None:
            raise OSError("aucun lecteur")

    def ecrire(self, octets):
        self.p.stdin.write(octets)
        self.p.stdin.flush()

    def fermer(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except Exception:                   # noqa: BLE001
            try:
                self.p.kill()
            except Exception:               # noqa: BLE001
                pass


class SortieWinmm:
    """Windows : waveOut de winmm.dll (fait partie de Windows), appelé par ctypes, en flux (plusieurs tampons)."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ct = ctypes
        self.w = ctypes.WinDLL("winmm")

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [("wFormatTag", wintypes.WORD), ("nChannels", wintypes.WORD), ("nSamplesPerSec", wintypes.DWORD),
                        ("nAvgBytesPerSec", wintypes.DWORD), ("nBlockAlign", wintypes.WORD),
                        ("wBitsPerSample", wintypes.WORD), ("cbSize", wintypes.WORD)]

        class WAVEHDR(ctypes.Structure):
            pass
        WAVEHDR._fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
                            ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_void_p),
                            ("dwFlags", wintypes.DWORD), ("dwLoops", wintypes.DWORD),
                            ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_void_p)]
        self.WAVEHDR = WAVEHDR
        fmt = WAVEFORMATEX(1, 1, SR, SR * 2, 2, 16, 0)
        self.h = ctypes.c_void_p()
        if self.w.waveOutOpen(ctypes.byref(self.h), ctypes.c_uint(0xFFFFFFFF), ctypes.byref(fmt), None, None, 0) != 0:
            raise OSError("waveOutOpen")
        self.encours = []                  # (en-tête, tampon) pas encore joués

    def _nettoyer(self, attendre=False):
        ct = self.ct
        reste = []
        for hdr, buf in self.encours:
            while attendre and not hdr.dwFlags & 1:          # WHDR_DONE
                time.sleep(0.02)
            if hdr.dwFlags & 1:
                self.w.waveOutUnprepareHeader(self.h, ct.byref(hdr), ct.sizeof(hdr))
            else:
                reste.append((hdr, buf))
        self.encours = reste

    def ecrire(self, octets):
        ct = self.ct
        self._nettoyer()
        buf = ct.create_string_buffer(octets, len(octets))
        hdr = self.WAVEHDR()
        hdr.lpData = ct.cast(buf, ct.c_void_p)
        hdr.dwBufferLength = len(octets)
        if self.w.waveOutPrepareHeader(self.h, ct.byref(hdr), ct.sizeof(hdr)) != 0:
            raise OSError("waveOutPrepareHeader")
        if self.w.waveOutWrite(self.h, ct.byref(hdr), ct.sizeof(hdr)) != 0:
            raise OSError("waveOutWrite")
        self.encours.append((hdr, buf))

    def fermer(self):
        try:
            self._nettoyer(attendre=True)
            self.w.waveOutClose(self.h)
        except Exception:                   # noqa: BLE001
            pass


class SortieFichier:
    """macOS (ou Windows sans winmm) : un petit .wav joué par afplay (macOS) ou winsound (Windows), un à la fois."""

    def __init__(self):
        self.mac = sys.platform == "darwin" and _qui("afplay")
        if not self.mac:
            import winsound  # noqa: F401  (Windows seulement, sinon ImportError -> silence)
        self.tampon = bytearray()
        self.p = None

    def ecrire(self, octets):
        self.tampon += octets
        if len(self.tampon) >= SR * 2:               # par morceaux d'une seconde
            self._vider()

    def _vider(self):
        if not self.tampon:
            return
        data = wav(list(struct.unpack("<%dh" % (len(self.tampon) // 2), bytes(self.tampon))))
        self.tampon = bytearray()
        if self.mac:
            from . import core
            d = core.SAVE_DIR / "sons"
            d.mkdir(parents=True, exist_ok=True)
            f = d / "son.wav"
            if self.p is not None:
                self.p.wait()
            f.write_bytes(data)
            self.p = subprocess.Popen(["afplay", str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                import winsound
                winsound.PlaySound(data, winsound.SND_MEMORY)
            except Exception:               # noqa: BLE001 — pas de carte son : le silence
                pass

    def fermer(self):
        self._vider()
        if self.p is not None:
            try:
                self.p.wait(timeout=30)
            except Exception:               # noqa: BLE001
                pass


def ouvrir_sortie():
    """La sortie du système, ou None (silence, sans message)."""
    essais = []
    if os.name == "nt":
        essais = [SortieWinmm, SortieFichier]
    elif sys.platform == "darwin":
        essais = [SortieFichier]
    else:
        essais = [SortiePipe]
    for k in essais:
        try:
            return k()
        except Exception:                   # noqa: BLE001
            continue
    return None


class Lecteur:
    """Le mélangeur d'une fenêtre qui dure (espace, monde, bureau) : une boucle de musique (fondu de 1 s quand elle
    change, 20 s de silence après 3 tours) + les sons courts, envoyés à la sortie du système par petits blocs, jamais
    plus de 0,15 s d'avance (un cri part tout de suite)."""
    BLOC = 1024

    def __init__(self, demarrer=True):
        self.verrou = threading.Lock()
        self.courts = []                   # [échantillons, position, volume]
        self.boucle = None                 # nom de la boucle voulue
        self.vol_musique = 30
        self.mus = None                    # [nom, échantillons, position, tours, silence restant]
        self.ancienne = None               # [échantillons, position, gain] (fondu de sortie)
        self.gain = 0.0
        self.fin = False
        self.sortie = None
        self.fil = threading.Thread(target=self._tourner, daemon=True)
        if demarrer:
            self.fil.start()

    def vivant(self):
        return not self.fin and self.fil.is_alive()

    def jouer(self, nom, vol):
        def pret():
            try:
                e = echantillons(nom)
            except Exception:               # noqa: BLE001
                return
            with self.verrou:
                self.courts.append([e, 0, max(0, min(100, vol)) / 100.0])
        threading.Thread(target=pret, daemon=True).start()

    def musique(self, nom, vol=30):
        """La boucle qui doit jouer (None : silence). La fabrication d'une boucle prend une seconde : en fond."""
        self.vol_musique = vol
        if nom == self.boucle:
            return
        self.boucle = nom
        if nom:
            def pret():
                try:
                    echantillons(nom)
                except Exception:           # noqa: BLE001
                    pass
            threading.Thread(target=pret, daemon=True).start()

    def arreter(self):
        self.fin = True

    def _bloc(self):
        n = self.BLOC
        out = [0.0] * n
        with self.verrou:
            voulu = self.boucle
            if self.mus is not None and self.mus[0] != voulu:            # la musique change : fondu de sortie
                self.ancienne = [self.mus[1], self.mus[2], 1.0]
                self.mus = None
            if self.mus is None and voulu:
                with _CACHE_VERROU:
                    e = _CACHE.get(voulu)
                if e:
                    self.mus = [voulu, e, 0, 0, 0]
                    self.gain = 0.0
            vm = self.vol_musique / 100.0
            pas = n / (SR * 1.0)                                         # fondu de 1 s
            if self.ancienne:
                e, p, g = self.ancienne
                for i in range(n):
                    out[i] += e[(p + i) % len(e)] / 32767.0 * g * vm
                self.ancienne = [e, (p + n) % len(e), g - pas] if g - pas > 0 else None
            if self.mus:
                nom, e, p, tours, silence = self.mus
                if silence > 0:
                    self.mus[4] = max(0, silence - n)
                else:
                    g = self.gain
                    for i in range(n):
                        out[i] += e[(p + i) % len(e)] / 32767.0 * g * vm
                    self.gain = min(1.0, g + pas)
                    p += n
                    if p >= len(e):
                        p -= len(e)
                        tours += 1
                        if tours >= 3:                                   # 3 tours, puis 20 s de silence
                            tours = 0
                            self.mus[4] = 20 * SR
                            self.gain = 0.0
                    self.mus[2], self.mus[3] = p, tours
            reste = []
            for c in self.courts:
                e, p, v = c
                k = min(n, len(e) - p)
                for i in range(k):
                    out[i] += e[p + i] / 32767.0 * v
                c[1] = p + k
                if c[1] < len(e):
                    reste.append(c)
            self.courts = reste
            actif = bool(self.courts or self.ancienne or (self.mus and self.mus[4] == 0))
        return out, actif

    def _tourner(self):
        debut = None
        ecrits = 0
        vide = 0
        while not self.fin:
            bloc, actif = self._bloc()
            if not actif:
                vide += 1
                if self.sortie is not None and vide > 200:              # longtemps rien : on rend le lecteur du système
                    self.sortie.fermer()
                    self.sortie = None
                debut = None
                time.sleep(0.03)
                continue
            vide = 0
            if self.sortie is None:
                self.sortie = ouvrir_sortie()
                if self.sortie is None:
                    time.sleep(1.0)
                    continue
            if debut is None:
                debut, ecrits = time.time(), 0
            ech = pcm(bloc)
            try:
                self.sortie.ecrire(struct.pack("<%dh" % len(ech), *ech))
            except Exception:               # noqa: BLE001 — le lecteur du système est parti : on réessaiera
                self.sortie = None
                continue
            ecrits += len(ech)
            avance = ecrits / SR - (time.time() - debut)
            if avance > 0.15:
                time.sleep(avance - 0.15)
        if self.sortie is not None:
            self.sortie.fermer()


def lecteur():
    """Le mélangeur de ce processus (créé au premier appel) : pour les fenêtres qui durent."""
    global _LECTEUR
    if _LECTEUR is None or not _LECTEUR.vivant():
        _LECTEUR = Lecteur()
    return _LECTEUR


def jouer_maintenant(nom, vol):
    """tg son _jouer : joue un son en entier puis rend la main (le petit processus à part)."""
    try:
        e = echantillons(nom)
    except Exception:                       # noqa: BLE001
        return
    s = ouvrir_sortie()
    if s is None:
        return
    v = max(0, min(100, vol)) / 100.0
    e = [int(x * v) for x in e]
    try:
        for i in range(0, len(e), 4096):
            m = e[i:i + 4096]
            s.ecrire(struct.pack("<%dh" % len(m), *m))
    finally:
        s.fermer()


def musique(state, cle):
    """La boucle que doit jouer une vue Monde / Espace (cle : biome, « gardiens », ou None) si les réglages le
    permettent ; renvoie le nom de la boucle (ou None)."""
    nom = None if not cle else "gardiens_theme" if cle == "gardiens" else "biome_" + cle
    if nom and (not nom.startswith("biome_") or nom[6:] in BIOMES) and peut(state, nom):
        return nom
    return None


def cle_musique(vue, gardien, biome):
    """Quelle boucle pour une vue : None hors des vues Monde / Espace ; le thème des gardiens pendant une rencontre de
    gardien ; sinon la musique du biome. Même règle en Kotlin."""
    if not vue:
        return None
    return "gardiens" if gardien else (biome or None)


def suivre(state, vue=True):
    """Appelé régulièrement par une vue Monde / Espace : met la bonne boucle dans le mélangeur (ou le silence)."""
    try:
        st = state if isinstance(state, dict) else {}
        d = st.get("dressage") if isinstance(st.get("dressage"), dict) else {}
        gardien = bool((d.get("ind") or {}).get("gardien"))
        nom = musique(st, cle_musique(vue, gardien, biome_de(st.get("espece_compagnon") or "")))
        if nom or _LECTEUR is not None:
            lecteur().musique(nom, int(reglages(st).get("v_musique", 30) or 0))
        return nom
    except Exception:                       # noqa: BLE001
        return None


def biome_de(espece_id):
    """Le biome d'une espèce (pour la musique de l'Espace), ou None : biomes.json (son biome à elle, sinon celui de
    sa famille)."""
    try:
        import json
        import pkgutil
        b = json.loads(pkgutil.get_data(__package__, "biomes.json").decode("utf-8"))
        if espece_id in b.get("classique_par_espece", {}):
            return b["classique_par_espece"][espece_id]
        fam = especes().get(espece_id, ("",))[0]
        return b.get("classique_par_famille", {}).get(fam)
    except Exception:                       # noqa: BLE001
        return None


# ------------------------------------------------------------------ tg son …
def _oui_non(mot):
    m = (mot or "").lower()
    return True if m in ("oui", "on", "yes", "o", "y", "1") else False if m in ("non", "off", "no", "n", "0") else None


def lignes_etat(state):
    from .langue import t as t_

    def t(cle, **kw):
        return t_(cle, cmd="tg son", **kw)
    r = reglages(state)
    oui, non = t("son.allume"), t("son.eteint")
    # « la musique » est féminin en français (allumée / éteinte) : ses propres mots (son.allumee / son.eteinte)
    out = [t("son.etat.titre", etat=oui if r["on"] else non),
           t("son.etat.musique", v=r["v_musique"], etat=t("son.allumee") if r["musique"] else t("son.eteinte")),
           t("son.etat.cris", v=r["v_cris"]),
           t("son.etat.retours", v=r["v_retours"])]
    y, mo, j, mi = _maintenant()
    s = soiree(y, mo, j, mi)
    out.append(t("son.etat.nuit.soir") if s and r.get("soir") == s else t("son.etat.nuit"))
    if _classe(state):
        out.append(t("son.etat.classe"))
    out.append(t("son.etat.aide"))
    return out


def regler(state, args):
    """Applique `tg son …` à la partie ; renvoie les lignes à afficher."""
    from .langue import t as t_

    def t(cle, **kw):
        return t_(cle, cmd="tg son", **kw)
    r = reglages(state)
    a = [x.lower() for x in args]
    if not a:
        return lignes_etat(state)
    mot = a[0]
    on = _oui_non(mot)
    if on is not None:
        r["on"] = on
        r["demande"] = True
        if on:
            son("reussite_petite", state)
        return [t("son.ok.on") if on else t("son.ok.off")]
    cats = {"musique": "musique", "music": "musique", "cris": "cris", "cri": "cris", "voix": "cris",
            "retours": "retours", "reussites": "retours", "réussites": "retours", "effets": "retours",
            "cries": "cris", "feedback": "retours"}
    if mot in cats:
        cat = cats[mot]
        v = a[1] if len(a) > 1 else ""
        o = _oui_non(v)
        if cat == "musique" and o is not None:
            r["musique"] = o
            if o:
                r["on"] = True
            return [t("son.ok.musique.on") if o else t("son.ok.musique.off")]
        v = v.rstrip("%")
        if v.isdigit():
            r["v_" + cat] = max(0, min(100, int(v)))
            if cat == "musique" and r["v_musique"] > 0:
                r["musique"] = True
            return [t("son.ok.volume", cat=t("son.cat." + cat), v=r["v_" + cat])]
        if o is not None:
            r["v_" + cat] = DEFAUTS["v_" + cat] if o else 0
            return [t("son.ok.volume", cat=t("son.cat." + cat), v=r["v_" + cat])]
        return [t("son.aide." + cat)]
    if mot in ("soir", "ce-soir", "cesoir", "tonight"):
        y, mo, j, mi = _maintenant()
        s = soiree(y, mo, j, mi)
        if not s:
            return [t("son.soir.jour")]
        r["soir"] = s
        r["on"] = True
        return [t("son.soir.ok")]
    if mot in ("essai", "essaie", "test"):
        quoi = a[1] if len(a) > 1 else "reussite_etape"
        if quoi == "cri":
            e = state.get("espece_compagnon") or ""
            quoi = nom_cri(e) if e else "reussite_etape"
        if not r["on"]:
            return [t("son.essai.eteint")]
        return [t("son.essai.ok")] if son(quoi, state) else [t("son.essai.pas_maintenant")]
    return lignes_etat(state)


def commande(args):
    """tg son [oui|non|musique N|cris N|retours N|soir|essai] ; tg son _jouer <nom> <volume> (interne)."""
    if args and args[0] == "_jouer":
        try:
            jouer_maintenant(args[1], int(args[2]) if len(args) > 2 else 50)
        except Exception:                   # noqa: BLE001
            pass
        return ""
    from . import core
    sortie = []
    core.modifier(lambda s: sortie.extend(regler(s, args)))
    return "\n".join(sortie)
