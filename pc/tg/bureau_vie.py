"""La vie de la créature du bureau et de l'île, sans aucune fenêtre : tout ce qui se décide ici se teste sans écran.

- Creature : ce qu'elle fait (marche, s'assoit, dort, s'étire, bâille, sursaute, fait un cœur, mange, salue), où elle
  est (le long du bas de l'écran), et quand elle change d'idée. Elle ne réagit qu'à des SIGNAUX ANONYMES : le temps
  depuis la dernière activité de l'ordinateur, la batterie, et les commandes que le JEU a comptées (jamais ce qui est
  tapé, jamais le titre d'une fenêtre : voir signaux.py et pc/outils/test_bureau.py).
- Clics : un clic, un double-clic, un triple clic ou un glisser, à partir des appuis et des relâchés.
- Menu : le petit menu rond autour d'elle (Jouer, Terminal, S'occuper, Carte, Ranger, Réglages, Équipe).
- Ile : la pilule du haut de l'écran, qui s'ouvre au survol, au clic, ou toute seule sur un événement du jeu.
- MiniTerminal : la ligne de commande de l'île (une vraie commande, lancée dans le terrain de jeu, comptée par le jeu).
Le même comportement existe sur Android (app/…/BureauVie.kt).
"""
import math
import os
import random
import shlex
import subprocess
import time

# ---------------------------------------------------------------- réglages
TAILLES = {"petite": 72, "moyenne": 104, "grande": 144}          # hauteur visée de la créature (pixels logiques)
VITESSES = {"lente": 28, "normale": 48, "rapide": 80}            # pixels par seconde quand elle marche
POSITIONS_ILE = ["haut", "bas", "cote"]
DEFAUTS = {"taille": "moyenne", "son": False, "vitesse": "normale", "sur_place": False, "demarrage": False,
           "ile": True, "ile_pos": "haut", "ile_auto": True, "discrete": True, "espece": None}

SOMMEIL = 300          # secondes sans activité de l'ordinateur : elle s'endort
REVEIL = 4             # activité depuis moins de 4 s : elle se réveille
BATTERIE_BASSE = 15    # % (sans chargeur) : elle bâille de temps en temps et marche moins vite
DUREES = {"etire": 2.4, "baille": 2.6, "sursaut": 1.2, "coeur": 2.6, "mange": 2.6, "salut": 2.4}
IPS_MARCHE = 6         # images par seconde du cycle de marche (4 images dessinées)
IPS = 8                # images par seconde des autres animations
TRANSITION = 0.36      # secondes : tassement de l'ancienne pose, fondu, étirement et rebond de la nouvelle
CLIGNEMENT = 0.14      # secondes : yeux fermés


def reglages(state):
    """Les réglages du bureau d'une partie (state["config"]["bureau"]), complétés des valeurs par défaut."""
    r = dict(DEFAUTS)
    try:
        r.update({k: v for k, v in (state.get("config", {}).get("bureau") or {}).items() if k in DEFAUTS})
    except AttributeError:
        pass
    if r["taille"] not in TAILLES:
        r["taille"] = DEFAUTS["taille"]
    if r["vitesse"] not in VITESSES:
        r["vitesse"] = DEFAUTS["vitesse"]
    if r["ile_pos"] not in POSITIONS_ILE:
        r["ile_pos"] = "haut"
    return r


def suivant(liste, v):
    """La valeur d'après dans une liste (en boucle) : les réglages à plusieurs choix se règlent d'un clic."""
    return liste[(liste.index(v) + 1) % len(liste)] if v in liste else liste[0]


# ---------------------------------------------------------------- la créature
class Creature:
    """La créature posée au sol. x : le milieu de son corps (pixels de l'écran) ; air : sa hauteur au-dessus du sol."""

    def __init__(self, largeur, regl=None, x=None, hasard=None):
        self.largeur = max(80, largeur)
        self.regl = dict(DEFAUTS, **(regl or {}))
        self.h = hasard or random.Random()
        self.x = float(x if x is not None else self.largeur * 0.7)
        self.air = 0.0
        self.vy = 0.0
        self.dir = -1
        self.etat = "assis"
        self.t_etat = 0.0
        self.duree = 3.0
        self.t = 0.0                    # le temps qui passe (animations)
        self.porte = False              # tenue à la souris / au doigt
        self.force_dodo = False         # « dormir » demandé dans les réglages
        self.batt_t = 0.0
        self.apres = None               # l'état qui suit une réaction
        self.prec = None                # (état, image) d'avant le dernier changement
        self.t_trans = TRANSITION       # temps depuis le dernier changement d'état
        self.cligne = self.h.uniform(1.5, 4.0)       # le prochain clignement (secondes)
        self.parole = None              # (texte, début) : elle parle (la mâchoire suit les syllabes)
        self.bouche = BOUCHE_DEFAUT     # où est sa bouche : fractions du corps depuis les pieds (album)

    # ------------------------------------------------ changer d'état
    def changer(self, etat, duree=None):
        if etat != self.etat or self.t_etat > TRANSITION:
            im = self.image()
            self.prec = (im[0], im[1], im[3])          # l'image d'avant (et son miroir), qui s'efface en fondu
            self.t_trans = 0.0
        self.etat = etat
        self.t_etat = 0.0
        # des durées un peu au hasard : elle ne fait jamais tout au même rythme
        self.duree = DUREES.get(etat, 4.0) * self.h.uniform(0.8, 1.35) if duree is None else duree
        if etat == "marche" and self.regl.get("sur_place"):
            self.etat = "assis"
            self.duree = self.h.uniform(6, 12)

    def reagir(self, quoi):
        """Une réaction tout de suite : « sursaut » (clic), « coeur » (double-clic), « salut » (triple clic),
        « mange » (le jeu a compté une commande), « baille » (batterie faible), « etire »."""
        if quoi not in DUREES:
            return
        if self.etat == "dort" and quoi in ("mange", "baille"):
            return                       # elle dort : les miettes attendront
        self.force_dodo = False
        self.changer(quoi)

    def parler(self, texte):
        """Elle dit texte : la bouche s'ouvre à chaque syllabe (assise ; elle s'arrête de marcher pour parler)."""
        self.parole = (str(texte), self.t)
        if self.etat in ("marche", "dort"):
            self.changer("assis", duree_parole(texte) + 0.6)

    def parle(self):
        """L'ouverture de la bouche (0 à 1) pour la parole en cours, ou None."""
        if self.parole is None:
            return None
        texte, debut = self.parole
        if self.t - debut > duree_parole(texte):
            self.parole = None
            return None
        return parole_niveau(texte, self.t - debut)

    def dormir(self):
        self.force_dodo = True
        self.changer("dort", 600)

    # ------------------------------------------------ le temps qui passe
    def vitesse(self, sig=None):
        v = VITESSES.get(self.regl.get("vitesse"), 48)
        b = (sig or {}).get("batterie")
        if b and b[0] is not None and b[0] <= BATTERIE_BASSE and not b[1]:
            v *= 0.6
        return v

    def tick(self, dt, sig=None):
        """Avance de dt secondes. sig : {"inactif": secondes ou None, "batterie": (pourcent, en_charge) ou None}."""
        sig = sig or {}
        dt = max(0.0, min(dt, 0.5))
        self.t += dt
        self.t_etat += dt
        self.t_trans += dt
        self.cligne -= dt
        if self.cligne < -CLIGNEMENT:
            self.cligne = self.h.uniform(2.2, 6.5) if self.h.random() > 0.2 else 0.35     # parfois deux de suite
        if self.porte:
            return
        # la chute après un glisser
        if self.air > 0:
            self.vy += 1400 * dt
            self.air = max(0.0, self.air - self.vy * dt)
            if self.air == 0:
                self.vy = 0
                self.changer("sursaut")
            return
        inactif = sig.get("inactif")
        if self.etat == "dort":
            if self.force_dodo:
                if self.t_etat > self.duree:
                    self.force_dodo = False
                    self.changer("etire")
            elif inactif is None or inactif < REVEIL:
                self.changer("etire")                      # l'ordinateur se réveille : elle aussi
            return
        if inactif is not None and inactif >= SOMMEIL and self.etat not in DUREES:
            self.changer("dort", 10 ** 6)
            return
        b = sig.get("batterie")
        if b and b[0] is not None and b[0] <= BATTERIE_BASSE and not b[1]:
            self.batt_t += dt
            if self.batt_t > 90 and self.etat in ("assis", "marche"):
                self.batt_t = 0.0
                self.reagir("baille")
                return
        if self.etat == "marche":
            self.x += self.dir * self.vitesse(sig) * dt
            bord = 50
            if self.x < bord:
                self.x, self.dir = bord, 1
            elif self.x > self.largeur - bord:
                self.x, self.dir = self.largeur - bord, -1
        if self.t_etat >= self.duree:
            self._decider(inactif)

    def _decider(self, inactif):
        h = self.h
        if self.etat in DUREES:                            # fin d'une réaction
            self.changer("assis", h.uniform(3, 7))
            return
        if self.etat == "marche":
            if h.random() < 0.15:
                self.changer("etire")
            else:
                self.changer("assis", h.uniform(5, 11))
            return
        # assise : repartir, s'étirer, bâiller (plutôt quand l'ordinateur est calme), ou rester
        p = h.random()
        calme = inactif is not None and inactif > 60
        if p < (0.35 if calme else 0.6) and not self.regl.get("sur_place"):
            self.dir = h.choice((-1, 1))
            self.changer("marche", h.uniform(4, 10))
        elif p < 0.72:
            self.changer("etire")
        elif p < (0.9 if calme else 0.8):
            self.changer("baille")
        else:
            self.changer("assis", h.uniform(4, 9))

    # ------------------------------------------------ glisser
    def prendre(self):
        self.porte = True
        self.force_dodo = False

    def deplacer(self, x, air):
        self.x = float(min(max(30, x), self.largeur - 30))
        self.air = max(0.0, float(air))

    def lacher(self):
        self.porte = False
        self.vy = 0.0
        if self.air <= 2:
            self.air = 0.0
            self.changer("sursaut")

    # ------------------------------------------------ ce qu'on montre
    def image(self):
        """(état à montrer, numéro d'image, décalage vertical en pixels logiques, miroir)."""
        miroir = self.dir < 0                     # les poses dessinées regardent vers la droite
        if self.porte or self.air > 0:
            return "sursaut", 0, 0.0, miroir
        if self.etat == "marche":
            k = int(self.t * IPS_MARCHE)
            return "marche", k, -abs(math.sin(self.t * math.pi * IPS_MARCHE / 2)) * 2.0, miroir
        dy = 0.0
        if self.etat == "sursaut" and self.t_etat < 0.5:
            dy = -math.sin(self.t_etat / 0.5 * math.pi) * 14
        elif self.etat == "salut":
            dy = -abs(math.sin(self.t_etat * 5)) * 3
        return self.etat, int(self.t_etat * IPS), dy, miroir and self.etat != "dort"     # les « z Z » restent à l'endroit


# ---------------------------------------------------------------- la vie dans chaque pose (pour le dessin)
class Anime:
    """Ce qu'on dessine à un instant : la pose (etat, k), sa déformation autour des pieds (sx, sy : échelles, rot :
    degrés, dy : pixels logiques), le miroir, son opacité, l'ancienne pose qui s'efface pendant une transition
    (ancien : (etat, k, opacité, miroir) ou None), l'ombre (échelle) et les petits effets :
    [(genre, x, y, taille, opacité)] avec x, y en fractions de la largeur et de la hauteur du corps, depuis les pieds (y négatif = vers le haut) ; genre : « z », « coeur », « miette ».
    Toutes les déformations sont continues : on les applique à la résolution de l'écran (un pas = un pixel d'écran,
    jamais un gros pixel du dessin)."""
    __slots__ = ("etat", "k", "dy", "miroir", "sx", "sy", "rot", "ancien", "ombre", "effets", "opacite")

    def __init__(self, etat, k, dy, miroir):
        self.etat, self.k, self.dy, self.miroir = etat, k, dy, miroir
        self.sx = self.sy = 1.0
        self.rot = 0.0
        self.ancien = None
        self.ombre = 1.0
        self.effets = []
        self.opacite = 1.0


def _doux(x):
    """0 → 1 en douceur (début et fin lents)."""
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _enveloppe(p, monte=0.3, descend=0.7):
    """Monte en douceur, tient, puis redescend en douceur (bâille, s'étire)."""
    if p < monte:
        return _doux(p / monte)
    if p < descend:
        return 1.0
    return 1.0 - _doux((p - descend) / (1 - descend))


def animer(c):
    """L'image animée de la créature c (voir Anime)."""
    etat, k, dy, miroir = c.image()
    a = Anime(etat, k, dy, miroir)
    u, d, t = c.t_etat, max(0.1, c.duree), c.t
    p = min(1.0, u / d)
    if c.porte or c.air > 0:
        a.ombre = max(0.3, 1 - c.air / 300)
        a.sy, a.sx = 1.04, 0.97                       # tenue à bout de bras, un peu étirée
        return a
    souffle = math.sin(2 * math.pi * t / 3.2)
    if etat in ("assis", "coeur", "salut", "mange", "etire", "baille"):
        a.sy, a.sx = 1 + 0.016 * souffle, 1 - 0.007 * souffle
    parole = c.parle() if etat in ("assis", "marche") else None
    if parole is not None and etat == "assis":
        a.etat = pose_bouche(parole)                   # elle parle : la mâchoire suit les syllabes
    elif etat == "assis" and c.cligne < 0:
        a.etat = "cligne"
    elif etat == "dort":
        lent = math.sin(2 * math.pi * t / 4.6)
        a.sy, a.sx = 1 + 0.024 * lent, 1 - 0.01 * lent
        for i in range(3):
            ph = (t / 1.6 + i / 3) % 1
            a.effets.append(("z", 0.28 + 0.22 * ph, -(0.95 + 0.5 * ph), 0.14 + 0.2 * ph, math.sin(math.pi * ph)))
    elif etat in ("etire", "baille"):
        e = _enveloppe(p)
        if etat == "etire":
            a.sy *= 1 + 0.07 * e
            a.sx *= 1 - 0.04 * e
        else:
            a.sy *= 1 + 0.045 * e
            a.sx *= 1 + 0.02 * e
            a.rot = -3.0 * e
    elif etat == "sursaut":
        if u < 0.55:
            h = math.sin(math.pi * u / 0.55)
            a.dy = -h * 18
            a.ombre = 1 - 0.45 * h
            if u < 0.08:
                a.sy, a.sx = 0.9, 1.06                # elle se tasse pour sauter
            else:
                a.sy, a.sx = 1 + 0.05 * h, 1 - 0.03 * h
        elif u < 0.72:
            q = math.sin(math.pi * (u - 0.55) / 0.17)
            a.sy, a.sx = 1 - 0.1 * q, 1 + 0.06 * q    # elle atterrit
    elif etat == "mange":
        # la pose assise (sans la miette dessinée) : la miette arrive devant la bouche, puis trois bouchées ; à chaque
        # bouchée, la bouche s'ouvre, la miette entre (elle rapetisse), la bouche se ferme avec un petit écrasement
        bx, by = c.bouche
        a.etat = "assis"
        if p < 0.25:
            q = _doux(p / 0.25)
            a.effets.append(("miette", bx + 0.55 * (1 - q), by - 0.15 * math.sin(math.pi * q), 0.13, _doux(p / 0.06)))
            a.etat = pose_bouche(0.6 * _doux((p - 0.17) / 0.08))
        elif p < 0.94:
            q = (p - 0.25) / 0.69 * 3
            n = int(q)
            v = q - n
            ouvre = math.sin(math.pi * min(1.0, v / 0.6))          # ouverte, puis fermée à 60 % de la bouchée
            a.etat = pose_bouche(ouvre)
            if v > 0.55:
                bosse = math.sin(math.pi * (v - 0.55) / 0.45)
                a.sy *= 1 - 0.05 * bosse
                a.sx *= 1 + 0.03 * bosse
            # la miette attend devant la bouche ouverte, puis entre quand elle se ferme (elle rapetisse)
            entre = _doux((v - 0.35) / 0.25)
            reste = 1 - (n + entre) / 3
            if reste > 0.04:
                a.effets.append(("miette", bx + 0.12 * (1 - entre), by + 0.02, 0.14 * reste ** 0.5, 1.0))
    elif etat == "coeur":
        a.dy = -abs(math.sin(u * 5.5)) * 2.5 * (1 - p)
        a.effets.append(("coeur", 0.32 + 0.05 * math.sin(u * 4), -(0.95 + 0.6 * p), 0.16 + 0.1 * p, 1 - _doux(p)))
    elif etat == "salut":
        a.rot = 5.0 * math.sin(2 * math.pi * u / 0.55) * (1 - _doux((p - 0.8) / 0.2) if p > 0.8 else 1)
    # la transition (TRANSITION secondes, 4 images à l'écran) : l'ancienne pose se tasse, la nouvelle prend le relais
    # par un court fondu croisé au moment le plus tassé, puis s'étire avec un rebond d'un pixel
    if c.prec is not None and c.t_trans < TRANSITION:
        q = c.t_trans / TRANSITION
        fondu = _doux((q - 0.35) / 0.3)
        if q < 0.5:
            tasse = _doux(q * 2)
            a.sy *= 1 - 0.08 * tasse
            a.sx *= 1 + 0.05 * tasse
        else:
            q2 = (q - 0.5) * 2
            a.sy *= 0.92 + 0.08 * _doux(q2) + 0.05 * math.sin(math.pi * q2)
            a.sx *= 1.05 - 0.05 * _doux(q2) - 0.03 * math.sin(math.pi * q2)
            a.dy -= 1.5 * math.sin(math.pi * q2)
        if c.prec[:2] != (a.etat, a.k) and c.prec[0] != etat and fondu < 1:
            a.ancien = (c.prec[0], c.prec[1], 1 - fondu, c.prec[2])
            a.opacite = fondu
    return a


def mini_vie(c, t):
    """La mini-créature de l'île : elle respire, cligne et parle avec la créature du bureau. (etat, sx, sy)"""
    souffle = math.sin(2 * math.pi * t / 3.2)
    niveau = c.parle() if c is not None else None
    if niveau is not None:
        etat = pose_bouche(niveau)
    else:
        etat = "cligne" if c is not None and c.cligne < 0 else "assis"
    return etat, 1 - 0.007 * souffle, 1 + 0.016 * souffle


# ---------------------------------------------------------------- la mâchoire (manger, parler)
BOUCHE_DEFAUT = (0.12, -0.3)        # sans bouche connue : un peu devant, au tiers de la hauteur
POSES_BOUCHE = ("assis", "bouche1", "bouche2", "bouche3")     # fermée, au tiers, aux deux tiers, grande ouverte


def pose_bouche(niveau):
    """La pose de la mâchoire pour une ouverture de 0 (fermée) à 1 (grande ouverte) : les images de poses.bin (les
    mêmes en Python et en Kotlin : BureauVie.poseBouche)."""
    k = int(max(0.0, min(1.0, niveau)) * 3 + 0.5)
    return POSES_BOUCHE[k]


SYLLABE = 0.16          # secondes par syllabe
VOYELLES = set("aeiouyàâäéèêëîïôöùûüÿœæ")
PAUSES = {".": 0.3, "!": 0.3, "?": 0.3, "…": 0.35, ",": 0.18, ";": 0.2, ":": 0.2, " ": 0.04}


def syllabes(texte):
    """Le texte coupé pour la bouche : [(durée, amplitude)] ; amplitude 0 = une pause. Une syllabe = un groupe de
    voyelles (écritures latines, cyrillique : chaque lettre-voyelle) ; les écritures sans voyelles séparées (chinois,
    japonais, arabe, hindi…) : une ouverture tous les deux caractères. Même découpage en Kotlin."""
    out = []
    dans_voyelle = False
    autres = 0
    k = 0
    for ch in str(texte).lower():
        if ch in PAUSES:
            out.append((PAUSES[ch], 0.0))
            dans_voyelle = False
            continue
        latin = ch.isascii() or ch in VOYELLES or "\u00c0" <= ch <= "\u024f"
        if latin or "\u0400" <= ch <= "\u04ff":
            voyelle = ch in VOYELLES or ch in "аеёиоуыэюя"
            if voyelle and not dans_voyelle:
                out.append((SYLLABE, 0.75 if k % 2 else 1.0))
                k += 1
            dans_voyelle = voyelle
        elif ch.isalpha():
            autres += 1
            if autres % 2 == 1:
                out.append((SYLLABE, 0.75 if k % 2 else 1.0))
                k += 1
    return out


def duree_parole(texte):
    return sum(d for d, _a in syllabes(texte))


def parole_niveau(texte, t):
    """L'ouverture de la bouche (0 à 1) au temps t (secondes) d'une phrase : elle s'ouvre et se ferme à chaque
    syllabe, reste fermée pendant les pauses. 0 après la fin."""
    if t < 0:
        return 0.0
    for d, a in syllabes(texte):
        if t < d:
            return a * math.sin(math.pi * t / d) if a else 0.0
        t -= d
    return 0.0



# ---------------------------------------------------------------- clic, double-clic, triple clic, glisser
class Clics:
    """Démêle les gestes : appuyer() / bouger() / relacher() avec l'heure, puis attendre() rend « clic »,
    « double » ou « triple » quand le geste est fini (un clic attend DELAI secondes un éventuel deuxième)."""
    DELAI = 0.32
    SEUIL = 6           # pixels : au-delà, c'est un glisser

    def __init__(self):
        self.n = 0
        self.dernier = None
        self.appui = None
        self.glisse = False

    def appuyer(self, x, y, t):
        self.appui = (x, y)
        self.glisse = False

    def bouger(self, x, y, t):
        """True quand c'est un glisser (la créature suit le pointeur)."""
        if self.appui is None:
            return False
        if not self.glisse and math.hypot(x - self.appui[0], y - self.appui[1]) > self.SEUIL:
            self.glisse = True
            self.n = 0
        return self.glisse

    def relacher(self, x, y, t):
        """« glisse_fin » à la fin d'un glisser, « triple » au troisième clic, sinon None (attendre())."""
        if self.appui is None:
            return None
        self.appui = None
        if self.glisse:
            self.glisse = False
            return "glisse_fin"
        if self.dernier is not None and t - self.dernier > self.DELAI:
            self.n = 0
        self.n += 1
        self.dernier = t
        if self.n >= 3:
            self.n = 0
            self.dernier = None
            return "triple"
        return None

    def attendre(self, t):
        """Le geste fini (« clic » ou « double »), ou None."""
        if self.n and self.appui is None and self.dernier is not None and t - self.dernier > self.DELAI:
            n, self.n, self.dernier = self.n, 0, None
            return "clic" if n == 1 else "double"
        return None


# ---------------------------------------------------------------- le petit menu rond
# (clé de texte, symbole, angle en degrés : 0 à droite, 90 en haut) — Jouer en haut, comme sur la maquette
MENU = [("jouer", "▶", 90), ("terminal", ">_", 42), ("soccuper", "♥", 4), ("carte", "◉", -36),
        ("ranger", "⌄", 216), ("reglages", "⚙", 176), ("equipe", "●●", 138)]
RAYON_MENU = 1.9        # × la hauteur de la créature (au moins 150 pixels)


def largeur_texte(texte, taille):
    """Largeur approchée d'un texte (pixels) : les caractères larges (chinois, japonais…) comptent double."""
    n = 0.0
    for c in texte:
        o = ord(c)
        n += 1.0 if (0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3
                     or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFF60) else 0.58
    return n * taille


def menu_positions(cx, cy_corps, haut_creature, libelles, taille_texte=14, largeur=None, hauteur=None):
    """Les boutons du menu rond : [(clé, symbole, libellé, x, y, w, h)] (x, y : coin haut gauche), et le cercle
    (cx, cy, r). La créature est en bas du cercle ; le cercle reste dans la zone (largeur × hauteur) si on la donne.
    Sur un écran étroit (téléphone), l'ovale se resserre en largeur et garde sa hauteur."""
    r = max(150.0, haut_creature * RAYON_MENU)
    h = taille_texte + 22
    larg = [largeur_texte(libelles.get(cle, cle), taille_texte) + h + 18 for cle, _s, _a in MENU]
    demi = max(larg) / 2
    rx, ry = r, r * 0.82
    if largeur is not None:
        rx = max(60.0, min(rx, (largeur - 2 * demi - 16) / 2))
        cx = min(max(cx, rx + demi + 8), largeur - rx - demi - 8)
    cy = cy_corps - r * 0.5
    if hauteur is not None:
        cy = max(cy, ry + h / 2 + 8)
    out = []
    for (cle, sym, ang), w in zip(MENU, larg):
        a = math.radians(ang)
        bx, by = cx + rx * math.cos(a), cy - ry * math.sin(a)
        out.append((cle, sym, libelles.get(cle, cle), bx - w / 2, by - h / 2, w, h))
    return out, (cx, cy, rx)


def touche(boutons, x, y):
    """La clé du bouton sous (x, y), ou None."""
    for b in boutons:
        if b[3] <= x <= b[3] + b[5] and b[4] <= y <= b[4] + b[6]:
            return b[0]
    return None


# ---------------------------------------------------------------- l'île du haut de l'écran
class Ile:
    """etat : « repos » (pilule), « ouverte » (survol ou clic), « evenement » (ouverte toute seule quelques secondes).
    ouverture : 0 (pilule) → 1 (panneau), animée en douceur par tick()."""
    DUREE_EVENEMENT = 6.0
    FERMETURE = 0.8          # secondes après la sortie du pointeur

    def __init__(self, auto=True):
        self.etat = "repos"
        self.ouverture = 0.0
        self.auto = auto
        self.t_evt = 0.0
        self.evenement = None
        self.dehors = None
        self.epingle = False     # ouverte d'un clic : reste ouverte jusqu'à un clic ailleurs
        self.discrete = False

    def survol(self, dedans, t):
        if dedans:
            self.dehors = None
            if self.etat == "repos":
                self.etat = "ouverte"
        elif self.etat == "ouverte" and not self.epingle and self.dehors is None:
            self.dehors = t

    def clic(self):
        if self.etat == "repos":
            self.etat = "ouverte"
            self.epingle = True
        else:
            self.epingle = not self.epingle or self.etat == "evenement"
            self.etat = "ouverte"

    def fermer(self):
        self.etat = "repos"
        self.epingle = False
        self.evenement = None

    def annoncer(self, texte, t=0.0):
        """Un événement du jeu (monstre apparu, étape réussie, badge, envie urgente) : l'île s'ouvre toute seule,
        sauf si l'ouverture automatique est coupée ou si l'ordinateur est en mode discret (ne pas déranger)."""
        self.evenement = texte
        if not self.auto or self.discrete or self.etat == "ouverte":
            return False
        self.etat = "evenement"
        self.t_evt = 0.0
        return True

    def tick(self, dt, t):
        if self.etat == "evenement":
            self.t_evt += dt
            if self.t_evt > self.DUREE_EVENEMENT:
                self.etat = "repos"
                self.evenement = None
        if self.etat == "ouverte" and self.dehors is not None and t - self.dehors > self.FERMETURE:
            self.etat = "repos"
            self.dehors = None
        but = 0.0 if self.etat == "repos" else (0.55 if self.etat == "evenement" else 1.0)
        self.ouverture += (but - self.ouverture) * min(1.0, dt * 9)
        if abs(but - self.ouverture) < 0.01:
            self.ouverture = but


def resume(state):
    """Les seuls compteurs du jeu que le bureau compare d'une fois sur l'autre (pour les événements de l'île)."""
    if not state:
        return None
    return {"sauvages": len(state.get("sauvages") or []), "lesson": state.get("lesson", 0),
            "step": state.get("step", 0), "hunger": state.get("hunger", 100), "total": state.get("total", 0)}


def evenements(avant, apres, notifs=()):
    """Les événements à annoncer entre deux résumés du jeu : [(clé de texte, texte tout fait ou None)].
    Seulement des compteurs du jeu (bestioles apparues, étapes, faim) et ses propres notifications (badge, évolution…) :
    rien d'autre n'est regardé."""
    if not avant or not apres:
        return []
    out = []
    if apres["sauvages"] > avant["sauvages"]:
        out.append(("bur.ile.monstre", None))
    if (apres["lesson"], apres["step"]) > (avant["lesson"], avant["step"]):
        out.append(("bur.ile.etape", None))
    if apres["hunger"] < 25 <= avant["hunger"]:
        out.append(("bur.ile.envie_faim", None))
    for n in notifs or ():
        texte = n[0] if isinstance(n, (list, tuple)) and n else n
        if isinstance(texte, str) and texte.strip():
            out.append(("", texte.strip()))
    return out


# ---------------------------------------------------------------- le mini-terminal de l'île
# commandes plein écran ou qui attendent le clavier : elles se tapent dans le vrai terminal
INTERACTIVES = {"vi", "vim", "nvim", "nano", "emacs", "less", "more", "man", "top", "htop", "btop", "ssh", "python",
                "python3", "bash", "sh", "zsh", "fish", "tg", "watch", "tail -f", "ftp", "telnet", "mc", "ranger",
                "sudo", "su", "passwd", "edite"}


class MiniTerminal:
    """Une ligne de commande dans l'île : la commande est lancée pour de vrai dans le terrain de jeu (comme dans le
    terminal), sa sortie s'affiche (quelques lignes), et le jeu la compte (nourrir, leçons) par compter(ligne, code).
    Les commandes plein écran ou interactives ne sont pas lancées : on explique d'ouvrir le vrai terminal."""
    DELAI = 8.0
    LIGNES = 6

    def __init__(self, dossier, compter=None, shell=None):
        self.dossier = str(dossier)
        self.compter = compter
        self.shell = shell
        self.saisie = ""
        self.historique = []
        self.sortie = []

    def invite(self):
        home = os.path.expanduser("~")
        d = self.dossier
        return ("~" + d[len(home):] if d.startswith(home) else d) + " $"

    def taper(self, texte):
        self.saisie += texte

    def effacer(self):
        self.saisie = self.saisie[:-1]

    def lancer(self, ligne=None):
        """Lance la saisie (ou ligne) : (code, lignes de sortie). code None : pas lancée (interactive, vide)."""
        ligne = (self.saisie if ligne is None else ligne).strip()
        self.saisie = ""
        if not ligne:
            return None, []
        self.historique.append(ligne)
        try:
            mots = shlex.split(ligne)
        except ValueError:
            mots = ligne.split()
        premier = mots[0] if mots else ""
        if premier in INTERACTIVES or ligne.startswith("tail -f"):
            self.sortie = ["@vrai_terminal"]
            return None, self.sortie
        if premier == "cd":
            return self._cd(mots[1:] if len(mots) > 1 else ["~"], ligne)
        code, sortie = executer(ligne, self.dossier, self.DELAI, self.shell)
        self.sortie = sortie[-self.LIGNES:]
        if self.compter:
            self.compter(ligne, code)
        return code, self.sortie

    def _cd(self, args, ligne):
        cible = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
        cible = os.path.normpath(os.path.join(self.dossier, cible))
        if os.path.isdir(cible):
            self.dossier = cible
            code, self.sortie = 0, []
        else:
            code, self.sortie = 1, [f"cd: {args[0]}: ?"]
        if self.compter:
            self.compter(ligne, code)
        return code, self.sortie


def executer(ligne, dossier, delai=8.0, shell=None):
    """Lance une ligne de commande dans dossier (le shell de l'ordinateur, sans clavier) : (code, lignes).
    Au-delà de delai secondes, la commande est arrêtée (code 124)."""
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command", ligne]
    else:
        cmd = [shell or os.environ.get("SHELL") or "/bin/sh", "-c", ligne]
    kw = {"cwd": dossier, "stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
    if os.name != "nt":
        kw["start_new_session"] = True
    try:
        p = subprocess.Popen(cmd, **kw)
    except OSError as e:
        return 127, [str(e)]
    try:
        out, _ = p.communicate(timeout=delai)
        code = p.returncode
    except subprocess.TimeoutExpired:
        try:
            if os.name != "nt":
                os.killpg(p.pid, 9)
            else:
                p.kill()
        except OSError:
            pass
        out, _ = p.communicate()
        code = 124
    texte = out.decode("utf-8", "replace").replace("\r", "")
    lignes = [l.expandtabs(4)[:160] for l in texte.split("\n")]
    while lignes and not lignes[-1].strip():
        lignes.pop()
    if code == 124:
        lignes.append("@trop_long")
    return code, lignes


# ---------------------------------------------------------------- petites choses du dessin
def particules(n, largeur, hauteur, t, pointeur=None, graine=7):
    """Des pixels qui flottent dans le fond de l'île et s'écartent du pointeur : [(x, y, alpha 0-255)]."""
    r = random.Random(graine)
    out = []
    for _ in range(n):
        x0, y0 = r.uniform(0, largeur), r.uniform(0, hauteur)
        v, ph = r.uniform(4, 12), r.uniform(0, 6.3)
        x = (x0 + math.sin(t * 0.4 + ph) * 6) % largeur
        y = (y0 - t * v) % hauteur
        if pointeur is not None:
            dx, dy = x - pointeur[0], y - pointeur[1]
            d = math.hypot(dx, dy)
            if 0.1 < d < 70:
                f = (70 - d) / 70 * 26
                x += dx / d * f
                y += dy / d * f
        a = int(90 + 120 * (0.5 + 0.5 * math.sin(t * 2 + ph)))
        out.append((x, y, a))
    return out


def maintenant():
    return time.monotonic()
