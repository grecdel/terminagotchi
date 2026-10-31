"""L'apparence de Terminagotchi : les thèmes, l'interface évolutive et la disposition de l'espace de travail.

Mêmes règles sur Android (Apparence.kt), mêmes données (apparence.json, copie de donnees/apparence.json), vecteurs
communs dans donnees/apparence/vecteurs.json (tests : pc/outils/test_apparence.py, tests/jvm/Apparence.kt).

Thèmes (maquettes validées le 31 octobre) : chaque couleur du thème sombre a un RÔLE. Les neutres (fond, panneaux,
terminal, textes, voiles blancs translucides) suivent une rampe de points du thème ; les 8 accents (vert, orange,
jaune, violet, bleu, cyan, rose, rouge : blocs de la vue déployée, états du cerveau, jauges…) sont remplacés par
l'accent du thème le plus proche en teinte ; les ombres restent des ombres ; les images (créatures) ne changent
jamais. Le dessin reste écrit avec les couleurs du thème sombre : on recolore la liste de dessin (espace, bureau,
île) au moment de la dessiner. Dans un vrai terminal, seules les couleurs du texte changent (le fond est celui du
terminal) : les thèmes clairs y gardent les accents du thème sombre, lisibles sur un fond sombre.

Interface évolutive : au début, l'œuf et l'invite seulement ; chaque panneau apparaît au moment de l'histoire où sa
notion arrive (table « panneaux »), avec une animation d'arrivée et une phrase de la créature. Un panneau mérité
le reste. « Tout afficher » (pour les grands, réversible) montre tout sans changer la progression.

Disposition (PC) : une grille de 24 × 20 cases ; chaque dalle est un rectangle de cases. Dispositions toutes prêtes
(classique, terminal géant, créature au centre, classe), « ma disposition » enregistrée, dalles cachées.
Téléphone : l'ordre des bandes (créature, vue déployée), leur taille P / M / G, l'ordre des onglets.

Sauvegarde : state["config"]["theme"] (+ "theme_date", ms : synchronisé par le recensement) ;
state["apparence"] = {vus, annonces, tout, dispo: {nom, rects, caches}, mienne}.
Une ancienne partie (sans « apparence ») : thème sombre, disposition classique, ses panneaux déjà mérités visibles
(tout, si elle date d'avant le déblocage progressif).
"""
import colorsys
import json
import math
import pkgutil
import time

_D = {}


def donnees():
    if not _D:
        _D.update(json.loads(pkgutil.get_data(__package__, "apparence.json").decode("utf-8")))
    return _D


def ordre():
    return list(donnees()["ordre"])


# ================================================================ les thèmes
SOURCE = {"vert": (61, 220, 132), "orange": (255, 159, 67), "jaune": (255, 213, 79), "violet": (178, 132, 255),
          "bleu": (95, 175, 255), "cyan": (77, 208, 225), "rose": (255, 121, 198), "rouge": (255, 95, 109)}
# la rampe des neutres du thème sombre : (clarté HLS = (max + min) / 510 de FOND, TERM, PANNEAU… ; rôle)
RAMPE = [(0.0, "fond"), (25 / 510, "fond"), (27 / 510, "terminal"), (39 / 510, "panneau"), (52 / 510, "panneau2"),
         (210 / 510, "pale"), (304 / 510, "doux"), (475 / 510, "texte"), (1.0, "encre")]
NEUTRES = ("fond", "panneau", "panneau2", "terminal", "pale", "doux", "texte", "encre")


def hexa(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def teinte(rgb):
    """La teinte (0-1), comme Java (Color.RGBtoHSB) et colorsys."""
    return colorsys.rgb_to_hsv(*(v / 255 for v in rgb[:3]))[0]


_HSRC = {k: teinte(v) for k, v in SOURCE.items()}


def accent_proche(rgb):
    h = teinte(rgb)
    return min(SOURCE, key=lambda k: (min(abs(_HSRC[k] - h), 1 - abs(_HSRC[k] - h)), list(SOURCE).index(k)))


class Theme:
    def __init__(self, cle="sombre"):
        th = donnees()["themes"]
        if cle not in th:
            cle = "sombre"
        d = th[cle]
        self.cle = cle
        self.clair = bool(d["clair"])
        self.r = {k: hexa(d[k]) for k in NEUTRES}
        self.acc = {k: hexa(v) for k, v in d["accents"].items()}
        self.bord = float(d.get("bord", 1.0))
        self.carte = d.get("teinte")
        self._cache = {}

    @property
    def sombre(self):
        return self.cle == "sombre"

    def neutre(self, l_):
        for (a, ra), (b, rb) in zip(RAMPE, RAMPE[1:]):
            if l_ <= b:
                k = 0 if b == a else (l_ - a) / (b - a)
                ca, cb = self.r[ra], self.r[rb]
                return tuple(int(math.floor(ca[i] + (cb[i] - ca[i]) * k + 0.5)) for i in range(3))
        return self.r["encre"]

    def couleur(self, c):
        """Une couleur (r, g, b[, a]) écrite pour le thème sombre → la même couleur dans ce thème."""
        if c is None or self.sombre:
            return c
        c = tuple(int(v) for v in c)
        if c in self._cache:
            return self._cache[c]
        a = c[3] if len(c) > 3 else 255
        rgb = c[:3]
        mx, mn = max(rgb), min(rgb)
        if a < 255 and mx < 6:                         # une ombre
            out = c
        else:
            l_ = (mx + mn) / 2 / 255
            if (mx - mn) / 255 < 0.2:                  # un neutre
                n = self.neutre(l_)
                if a < 255 and l_ > 0.5:               # un voile ou un bord fin (blanc translucide)
                    a = min(255, int(a * self.bord))
                    n = self.r["encre"]
            else:                                      # un accent
                n = self.acc[accent_proche(rgb)]
            out = n + (a,) if len(c) > 3 else n
        self._cache[c] = out
        return out


POS = {"rect": (5,), "rrect": (6, 7), "texte": (5,), "ellipse": (5,), "cercle": (4,), "lueur": (4,), "ligne": (5,),
       "poly": (2,), "arc": (5,)}


def recolorer(L, th):
    """La même liste de dessin (espace_scene, bureau_scene) dans les couleurs du thème (les images ne changent pas)."""
    if th is None or th.sombre:
        return L
    out = []
    for op in L:
        p = POS.get(op[0])
        if p:
            op = list(op)
            for i in p:
                if i < len(op) and isinstance(op[i], tuple):
                    op[i] = th.couleur(op[i])
            op = tuple(op)
        out.append(op)
    return out


GB = [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)]


def teinter_image(im, th):
    """La carte du monde dans la teinte du thème (Matrix, ambre, Game Boy) ; sinon intacte (PIL)."""
    if th is None or not th.carte:
        return im
    from PIL import Image, ImageOps
    a = im.getchannel("A") if im.mode == "RGBA" else None
    g = ImageOps.grayscale(im.convert("RGB"))
    if th.carte == "gameboy":
        out = Image.new("RGB", g.size)
        out.putdata([GB[min(3, v * 4 // 256)] for v in g.getdata()])
    else:
        out = ImageOps.colorize(g, (0, 0, 0), tuple(th.carte))
    out = out.convert("RGBA")
    if a is not None:
        out.putalpha(a)
    return out


def luminance(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def contraste(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- le thème de la partie
_actif = [None]


def cle_theme(state):
    c = ((state or {}).get("config") or {}).get("theme") or "sombre"
    return c if c in donnees()["themes"] else "sombre"


def theme(state=None):
    """Le thème de la partie (ou le dernier activé)."""
    if state is not None:
        cle = cle_theme(state)
        if _actif[0] is None or _actif[0].cle != cle:
            _actif[0] = Theme(cle)
    return _actif[0] or Theme("sombre")


def activer(state):
    """Au chargement de la partie : le thème des couleurs du terminal (plateforme.fg)."""
    th = theme(state)
    from . import plateforme
    plateforme.THEME_ANSI = None if (th.sombre or th.clair) else th
    return th


def choisir_theme(state, cle):
    if cle not in donnees()["themes"]:
        return False
    cfg = state.setdefault("config", {})
    cfg["theme"] = cle
    cfg["theme_date"] = int(time.time() * 1000)
    activer(state)
    return True


XTERM16 = [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200), (188, 63, 188), (17, 168, 205),
           (229, 229, 229), (102, 102, 102), (241, 76, 76), (35, 209, 139), (245, 245, 67), (59, 142, 234),
           (214, 112, 214), (41, 184, 219), (255, 255, 255)]


def xterm(n):
    if n < 16:
        return XTERM16[n]
    if n < 232:
        n -= 16
        v = [0, 95, 135, 175, 215, 255]
        return (v[n // 36], v[n // 6 % 6], v[n % 6])
    g = 8 + 10 * (n - 232)
    return (g, g, g)


def ansi(n, th):
    """\\033[38;… pour la couleur 256 n dans le thème (couleurs vives : l'accent du thème ; gris : inchangés)."""
    rgb = xterm(n)
    if (max(rgb) - min(rgb)) / 255 < 0.2:
        return f"\033[38;5;{n}m"
    c = th.acc[accent_proche(rgb)]
    return f"\033[38;2;{c[0]};{c[1]};{c[2]}m"


# ================================================================ l'interface évolutive
def a_(state):
    """state["apparence"], créé à la première lecture (migration : les panneaux déjà mérités, sans annonce)."""
    a = state.get("apparence")
    if not isinstance(a, dict):
        a = state["apparence"] = {"vus": [], "annonces": [], "tout": False, "dispo": None, "mienne": None}
        verifier(state, annoncer=False)
    for k, v in (("vus", []), ("annonces", []), ("tout", False), ("dispo", None), ("mienne", None)):
        a.setdefault(k, v)
    return a


def ids():
    return [p["id"] for p in donnees()["panneaux"]]


def _ancienne(state):
    """Une partie d'avant le déblocage progressif (ou tout débloquée) : tout est déjà là."""
    d = state.get("debloc")
    return not isinstance(d, dict) or d.get("mode") != "progressif"


def condition(state, q):
    from . import histoire, intro
    q = dict(q)
    une = q.pop("une_lecon", None)
    if not intro.condition(state, q):
        return False
    if une:
        faits = histoire.h_(state).get("faits", [])
        if not any(x in faits for x in une):
            return False
    return True


def verifier(state, annoncer=True):
    """Les panneaux dont le moment est venu : notés (pour toujours) et, s'il le faut, annoncés. Renvoie les nouveaux."""
    a = state["apparence"]
    neufs = []
    anc = _ancienne(state)
    for p in donnees()["panneaux"]:
        if p["id"] in a["vus"]:
            continue
        if anc or condition(state, p["quand"]):
            a["vus"].append(p["id"])
            neufs.append(p["id"])
    if annoncer and not anc:
        for n in neufs:
            if n not in a["annonces"]:
                a["annonces"].append(n)
                from . import core
                from .langue import t
                core.say(state, t(f"app.pan.{n}.dit"), 10)
    return neufs


def visibles(state):
    """Les panneaux visibles : ceux mérités (ou tous avec « Tout afficher »), plus le terminal, toujours là."""
    if state is None:
        return set(ids()) | set(donnees()["toujours"])
    a = a_(state)
    if a.get("tout"):
        return set(ids()) | set(donnees()["toujours"])
    return set(a["vus"]) | set(donnees()["toujours"])


def onglets(state):
    """Les onglets du panneau du moment, déjà apparus (PC : carte, cerveau, tuyaux, leçon)."""
    v = visibles(state)
    out = [o for o in ("carte", "cerveau", "tuyaux") if o in v]
    if "carte" in v:
        out.append("lecon")
    return out


def tout_afficher(state, oui):
    a_(state)["tout"] = bool(oui)


def question_adulte(n=None):
    """La petite question pour les grands avant « Tout afficher » : (question, réponse)."""
    import random
    r = random.Random(n)
    a, b = r.randint(12, 19), r.randint(13, 19)
    return f"{a} × {b}", str(a * b)


# ================================================================ la disposition (PC)
def grille():
    return donnees()["grille"]


def rect_de(case):
    """[colonne, rangée, largeur, hauteur] en cases → (x, y, w, h) logiques (1920 × 1080)."""
    g = grille()
    sx = (g["w"] + g["ecart"]) / g["colonnes"]
    sy = (g["h"] + g["ecart"]) / g["rangees"]
    c, r, w, h = case

    def r2(v):
        return math.floor(v * 100 + 0.5) / 100
    return (r2(g["x"] + c * sx), r2(g["y"] + r * sy), r2(w * sx - g["ecart"]), r2(h * sy - g["ecart"]))


def case_de(x, y):
    """Le point logique (x, y) → la case [colonne, rangée] la plus proche (aimantation)."""
    g = grille()
    sx = (g["w"] + g["ecart"]) / g["colonnes"]
    sy = (g["h"] + g["ecart"]) / g["rangees"]
    return [int(round((x - g["x"]) / sx)), int(round((y - g["y"]) / sy))]


def borner(case):
    g = grille()
    c, r, w, h = (int(v) for v in case)
    w = max(g["min"][0], min(g["colonnes"], w))
    h = max(g["min"][1], min(g["rangees"], h))
    c = max(0, min(g["colonnes"] - w, c))
    r = max(0, min(g["rangees"] - h, r))
    return [c, r, w, h]


def chevauche(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def preset(nom):
    d = donnees()["dispositions"]
    return {k: list(v) for k, v in d.get(nom, d["classique"]).items()}


def disposition(state):
    """{dalle: [c, r, w, h]} de la partie (sans les dalles cachées), le nom (« classique », « mienne »…)."""
    a = a_(state) if state is not None else {}
    d = a.get("dispo") or {}
    nom = d.get("nom") or "classique"
    if nom == "classe":
        return {}, "classe"
    rects = d.get("rects") or preset(nom)
    caches = set(d.get("caches") or [])
    return {k: borner(v) for k, v in rects.items() if k not in caches}, nom


def choisir_disposition(state, nom):
    a = a_(state)
    if nom == "mienne" and a.get("mienne"):
        a["dispo"] = json.loads(json.dumps(a["mienne"]))
        a["dispo"]["nom"] = "mienne"
    elif nom in donnees()["dispositions"] or nom == "classe":
        a["dispo"] = {"nom": nom, "rects": None if nom == "classe" else preset(nom), "caches": []}
    else:
        return False
    return True


def enregistrer_mienne(state):
    a = a_(state)
    rects, nom = disposition(state)
    caches = list((a.get("dispo") or {}).get("caches") or [])
    a["mienne"] = {"nom": "mienne", "rects": {k: list(v) for k, v in rects.items()}, "caches": caches}
    a["dispo"] = json.loads(json.dumps(a["mienne"]))


def modifier(state, dalle, case=None, cacher=None):
    """Déplacer / agrandir (case) ou cacher / remettre une dalle ; la disposition devient « personnalisée »."""
    a = a_(state)
    rects, nom = disposition(state)
    d = a.get("dispo") or {}
    caches = set(d.get("caches") or [])
    tout = {k: list(v) for k, v in (d.get("rects") or preset(nom if nom != "classe" else "classique")).items()}
    if case is not None:
        tout[dalle] = borner(case)
    if cacher is True:
        caches.add(dalle)
    elif cacher is False:
        caches.discard(dalle)
        if dalle not in tout:
            tout[dalle] = preset("classique").get(dalle, [0, 0, 6, 6])
    a["dispo"] = {"nom": "perso", "rects": tout, "caches": sorted(caches)}


def origine(state):
    a_(state)["dispo"] = {"nom": "classique", "rects": preset("classique"), "caches": []}


def caches(state):
    d = a_(state).get("dispo") or {}
    return list(d.get("caches") or [])


# ================================================================ le téléphone (même règles qu'Apparence.kt)
def bandes_telephone(nom):
    d = donnees()["telephone"]["dispositions"]
    return [list(b) for b in d.get(nom, d["classique"])["bandes"]]


def onglets_telephone(vus, ordre_choisi=()):
    """Les onglets du téléphone déjà apparus (même règle qu'Apparence.onglets)."""
    t = donnees()["telephone"]
    base = list(t["onglets"])
    ordre_ = [o for o in ordre_choisi if o in base] + [o for o in base if o not in ordre_choisi]
    v = set(vus) | set(donnees()["toujours"])
    return [o for o in ordre_ if o == "terminal" or t["onglet_de"].get(o, o) in v]


def vecteurs():
    """Les vecteurs communs (donnees/apparence/vecteurs.json) : Python et Kotlin doivent donner exactement ceci."""
    echant = [list(c) + [255] for c in SOURCE.values()] + [
        [9, 11, 16, 255], [15, 17, 24, 255], [20, 23, 32, 255], [10, 12, 17, 255], [233, 236, 242, 255],
        [138, 147, 166, 255], [92, 100, 118, 255], [255, 255, 255, 22], [255, 255, 255, 44], [0, 0, 0, 90],
        [255, 168, 92, 255], [208, 208, 208, 255], [95, 215, 135, 255], [190, 215, 255, 200], [3, 4, 7, 170]]
    out = {"couleurs": {}, "rects": {}, "telephone": {}, "onglets": []}
    for cle in ordre():
        th = Theme(cle)
        out["couleurs"][cle] = [[c, list(th.couleur(tuple(c)))] for c in echant]
    for nom in donnees()["dispositions"]:
        out["rects"][nom] = {k: list(rect_de(v)) for k, v in preset(nom).items()}
    for nom in donnees()["telephone"]["dispositions"]:
        out["telephone"][nom] = bandes_telephone(nom)
    for vus, ordre_ in ([[], []], [["carte"], []], [["carte", "equipe"], ["equipe", "terminal"]],
                        [["carte", "cerveau", "equipe", "tuyaux"], ["cerveau"]]):
        out["onglets"].append({"vus": vus, "ordre": ordre_, "onglets": onglets_telephone(vus, ordre_)})
    return out
