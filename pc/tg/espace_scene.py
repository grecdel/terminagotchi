"""L'espace de travail de Terminagotchi (`tg espace`), sous forme d'une LISTE DE DESSIN, sans fenêtre.

Même principe que la créature du bureau (bureau_scene.py) : la fenêtre GTK 4, la fenêtre tkinter et les captures
(PIL) dessinent la même liste. En plus des ordres du bureau (img, imgt, rrect, ellipse, rect, texte) :
    ("ligne", x1, y1, x2, y2, couleur, epaisseur, tirets)     tirets : None ou (plein, vide, décalage)
    ("poly", [(x, y)…], couleur)                               un polygone plein (pointes de flèches)
    ("cercle", cx, cy, r, couleur, epaisseur)                  un anneau
    ("lueur", cx, cy, r, couleur)                              un halo rond (couleur au centre, transparent au bord)
    ("photo", nom, x, y, w, h)                                 une illustration (« monde » : la carte du Terminaworld)
Disposition (maquettes validées docs/maquettes/espace_travail_pc.png et espace_travail_cerveau_pc.png) :
    en haut         l'île : la créature, son état, l'équipe en pastilles, niveau, son, réglages
    à gauche        Explorateur (le Terminaworld, le lieu courant), Envies (jauges, assiette du jour), Équipe
    au centre       la vue déployée de la dernière commande, puis le terminal
    à droite        la créature en direct, puis le panneau du moment : Carte, Cerveau, Tuyaux ou Leçon
Mode classe (grand écran) : sans la colonne de gauche, tout 20 % plus grand.
Les coordonnées sont « logiques » (1920 × 1080, ou 1600 × 900 en classe) ; la fenêtre met à l'échelle.
"""
import math

from . import bureau_vie as V
from . import cerveau as CV
from . import deploie as D
from .langue import sans_marques, t

# ---------------------------------------------------------------- couleurs (r, g, b, a)
FOND = (9, 11, 16, 255)
PANNEAU = (15, 17, 24, 255)
PANNEAU2 = (20, 23, 32, 255)
BORD = (255, 255, 255, 22)
BORD_FORT = (255, 255, 255, 44)
TEXTE = (233, 236, 242, 255)
DOUX = (138, 147, 166, 255)
PALE = (92, 100, 118, 255)
VERT = (61, 220, 132, 255)
ORANGE = (255, 159, 67, 255)
JAUNE = (255, 213, 79, 255)
VIOLET = (178, 132, 255, 255)
BLEU = (95, 175, 255, 255)
CYAN = (77, 208, 225, 255)
ROSE = (255, 121, 198, 255)
ROUGE = (255, 95, 109, 255)
TERM = (10, 12, 17, 255)
COUL_ENVIES = {"faim": (255, 168, 92), "jeu": (255, 121, 198), "curiosite": (255, 213, 79),
               "explorer": (61, 220, 132), "sommeil": (178, 132, 255), "proprete": (77, 208, 225)}
COUL_STATUT = {"mange": VERT, "dort": VIOLET, "pret": BLEU, "faim": ORANGE, "veille": PALE}
# la place des lieux sur l'illustration « monde » (fractions de largeur et de hauteur)
LIEUX_CARTE = {"salle_des_machines": (0.16, 0.10), "tour": (0.84, 0.10), "bibliotheque": (0.10, 0.36),
               "coeur": (0.50, 0.29), "atelier": (0.84, 0.36), "cave": (0.86, 0.55), "nid": (0.50, 0.47),
               "vestibule": (0.55, 0.71), "dortoir": (0.85, 0.80), "grenier": (0.27, 0.74)}
ONGLETS = ("carte", "cerveau", "tuyaux", "lecon")


def _a(c, a):
    return tuple(c[:3]) + (a,)


def rgb(c, a=255):
    return tuple(c[:3]) + (a,)


def lt(texte, taille, mono=False):
    """La largeur d'un texte (approchée, comme la créature du bureau ; en chasse fixe : 0,6 cadratin)."""
    if mono:          # 0,602 cadratin : l'avance exacte de DejaVu Sans Mono (1233/2048), la police des terminaux
        return sum(1.204 if ord(c) >= 0x2E80 else 0.602 for c in texte) * taille
    return V.largeur_texte(texte, taille) * 0.98


def couper(texte, largeur, taille, mono=False):
    out = []
    for para in str(texte).split("\n"):
        mots = para.split(" ")
        cour = ""
        for m in mots:
            essai = (cour + " " + m) if cour else m
            if cour and lt(essai, taille, mono) > largeur:
                out.append(cour)
                cour = m
            else:
                cour = essai
        out.append(cour)
    return out


def court(texte, largeur, taille, mono=False):
    """Le texte raccourci (…) pour tenir dans largeur."""
    if lt(texte, taille, mono) <= largeur:
        return texte
    while texte and lt(texte + "…", taille, mono) > largeur:
        texte = texte[:-1]
    return texte + "…"


def panneau(L, x, y, w, h, titre=None, droite=None):
    L.append(("rrect", x, y, w, h, 14, PANNEAU, BORD, 1))
    if titre:
        L.append(("texte", x + 16, y + 22, espace_lettres(titre.upper()), 11, DOUX, True, "g", False))
    if droite:
        L.append(("texte", x + w - 16, y + 22, droite, 11, PALE, False, "d", False))


def espace_lettres(s):
    """Les titres de panneau, lettres un peu espacées (comme la maquette)."""
    return " ".join(s) if all(ord(c) < 0x2E80 for c in s) else s


def chip(L, x, y, texte, couleur, taille=12, fond=None, point=True, ancre="g", bord=None):
    """Une petite étiquette arrondie (● texte) ; renvoie sa largeur. ancre « d » : x = bord droit."""
    w = lt(texte, taille) + (30 if point else 18)
    if ancre == "d":
        x -= w
    L.append(("rrect", x, y - 12, w, 24, 12, fond or _a(couleur, 26), bord if bord is not None else _a(couleur, 90), 1))
    tx = x + 9
    if point:
        L.append(("ellipse", x + 13, y, 3.5, 3.5, couleur))
        tx = x + 21
    L.append(("texte", tx, y, texte, taille, couleur if point else TEXTE, False, "g", False))
    return w


def creature_img(L, album, etat, k, cx, pieds, hauteur, sx=1.0, sy=1.0, miroir=False, alpha=1.0):
    """Une image d'un album, posée par les pieds, haute d'environ hauteur pixels."""
    if not album:
        return
    cad = album.image(etat, k)
    e = hauteur / max(1, album.ref)
    if not album.lisse:
        e = max(1.0, float(int(e)))
    L.append(("imgt", cad, cx, pieds, e, miroir, album.lisse, sx, sy, 0.0, alpha))


def fleche(L, x1, y1, x2, y2, couleur, ep=1.5, tirets=None, pointe=7):
    L.append(("ligne", x1, y1, x2, y2, couleur, ep, tirets))
    a = math.atan2(y2 - y1, x2 - x1)
    p = [(x2, y2), (x2 - pointe * math.cos(a - 0.45), y2 - pointe * math.sin(a - 0.45)),
         (x2 - pointe * math.cos(a + 0.45), y2 - pointe * math.sin(a + 0.45))]
    L.append(("poly", p, couleur))


# ---------------------------------------------------------------- la disposition
class Mise:
    """Les rectangles des panneaux (coordonnées logiques). cases : la disposition de la partie ({dalle: [c, r, w, h]},
    apparence.disposition) ; sans cases : la disposition classique. intro : l'œuf et l'invite seuls, au centre."""

    def __init__(self, classe=False, cases=None, intro=False):
        self.classe = classe
        self.haut = None
        if classe:
            self.W, self.H = 1600, 900
            d0, dw, c0 = 1600 - 16 - 540, 540, 16
            bas = self.H - 16
            self.haut = (0, 0, self.W, 92)
            self.explorateur = self.envies = self.equipe = None
            cw = d0 - 16 - c0
            hd = 332
            self.deploie = (c0, 96, cw, hd)
            self.terminal = (c0, 96 + hd + 16, cw, bas - (96 + hd + 16))
            hc = 340
            self.direct = (d0, 96, dw, hc)
            self.contexte = (d0, 96 + hc + 16, dw, bas - (96 + hc + 16))
            return
        self.W, self.H = 1920, 1080
        self.haut = (0, 0, self.W, 92)
        if intro:
            self.explorateur = self.envies = self.equipe = self.deploie = self.contexte = None
            self.direct = (520, 110, 880, 400)
            self.terminal = (520, 526, 880, 538)
            return
        from . import apparence
        if cases is None:
            cases = apparence.preset("classique")
        for k in ("explorateur", "envies", "equipe", "deploie", "terminal", "direct", "contexte"):
            setattr(self, k, apparence.rect_de(cases[k]) if k in cases else None)

    def rects(self):
        return {k: getattr(self, k) for k in ("explorateur", "envies", "equipe", "deploie", "terminal", "direct",
                                              "contexte") if getattr(self, k)}


# ---------------------------------------------------------------- l'île (barre du haut)
def haut(L, Z, m, mise):
    W = mise.W
    L.append(("rrect", 20, 28, 36, 36, 10, _a(VERT, 30), _a(VERT, 140), 1))
    L.append(("texte", 38, 46, ">_", 14, VERT, True, "c", True))
    L.append(("texte", 68, 37, "Terminagotchi", 17, TEXTE, True, "g", False))
    L.append(("texte", 68, 59, m.get("chapitre", ""), 13, DOUX, False, "g", False))
    # la pilule de l'île
    eq = m.get("equipe", [])[:4]
    nom = m.get("nom", "")
    sous = m.get("espece_stade", "")
    ligne2 = m.get("gains", "")
    w_txt = max(lt(nom, 15) + lt(" · " + sous, 13), lt(m.get("etat_nom", ""), 13) + lt(ligne2, 13) + 30)
    w_eq = 48 * len(eq)
    w_m = lt(m.get("monstre", ""), 12) + 20 if m.get("monstre") else 0
    pw = 88 + w_txt + 28 + w_eq + (24 + w_m if w_m else 0)
    px = W / 2 - pw / 2
    evt = m.get("evenement")
    L.append(("rrect", px, 16, pw, 62, 31, PANNEAU, _a(ROUGE, 160) if evt else BORD_FORT, 1.5 if evt else 1))
    Z.append((px, 16, pw, 62, "ile"))
    L.append(("ellipse", px + 31, 47, 24, 24, PANNEAU2))
    L.append(("cercle", px + 31, 47, 24, _a(VERT, 150), 1.5))
    alb = m.get("album")
    if alb:
        etat, sx, sy = m.get("mini", ("assis", 1.0, 1.0))
        creature_img(L, alb, etat, int(m.get("t", 0) * V.IPS), px + 31, 66, 36, sx, sy)
    tx = px + 70
    if evt:
        L.append(("texte", tx, 47, court(sans_marques(evt), pw - 100, 14), 14, TEXTE, True, "g", False))
        return
    L.append(("texte", tx, 39, nom, 15, TEXTE, True, "g", False))
    L.append(("texte", tx + lt(nom, 15) + 4, 40, "· " + sous, 13, DOUX, False, "g", False))
    ce = m.get("etat_couleur", VERT)
    L.append(("ellipse", tx + 4, 60, 4, 4, ce))
    L.append(("texte", tx + 13, 60, m.get("etat_nom", ""), 13, ce, False, "g", False))
    L.append(("texte", tx + 19 + lt(m.get("etat_nom", ""), 13), 60, ligne2, 13, DOUX, False, "g", False))
    ex = tx + w_txt + 20
    for i, (a2, statut, actif) in enumerate(eq):
        bx = ex + 48 * i
        L.append(("rrect", bx, 27, 40, 40, 11, PANNEAU2, _a(VERT, 150) if actif else BORD, 1.5 if actif else 1))
        if a2:
            creature_img(L, a2, "assis", 0, bx + 20, 62, 30)
        L.append(("ellipse", bx + 37, 29, 4, 4, COUL_STATUT.get(statut, BLEU)))
        Z.append((bx, 27, 40, 40, f"equipe:{i}"))
    if w_m:
        mx = ex + w_eq + 6
        L.append(("ligne", mx, 28, mx, 66, BORD, 1, None))
        for j, l in enumerate(couper(m["monstre"], w_m - 12, 12)[:2]):
            L.append(("texte", mx + 14, 40 + 15 * j, l, 12, DOUX, False, "g", False))
    # à droite : niveau, son, réglages
    x = W - 20 - 38
    L.append(("ellipse", x + 19, 47, 19, 19, PANNEAU))
    L.append(("cercle", x + 19, 47, 19, BORD_FORT, 1))
    L.append(("texte", x + 19, 47, "⚙", 15, DOUX, False, "c", False))
    Z.append((x, 28, 38, 38, "reglages"))
    if m.get("ranger_possible", True) and not mise.classe:
        x -= 48
        rg = m.get("rangement")
        L.append(("ellipse", x + 19, 47, 19, 19, _a(JAUNE, 40) if rg else PANNEAU))
        L.append(("cercle", x + 19, 47, 19, _a(JAUNE, 200) if rg else BORD_FORT, 1))
        L.append(("texte", x + 19, 47, "✎", 15, JAUNE if rg else DOUX, False, "c", False))
        Z.append((x, 28, 38, 38, "ranger"))
    x -= 48
    L.append(("ellipse", x + 19, 47, 19, 19, PANNEAU))
    L.append(("cercle", x + 19, 47, 19, BORD_FORT, 1))
    L.append(("texte", x + 19, 47, "♪" if m.get("son") else "♪̸", 14, DOUX if m.get("son") else PALE, False, "c", False))
    Z.append((x, 28, 38, 38, "son"))
    chip(L, x - 12, 47, t("esp.niveau", n=m.get("niveau", 1)), JAUNE, 12, fond=PANNEAU, ancre="d", bord=BORD_FORT)
    if mise.classe:
        chip(L, x - 130, 47, t("esp.classe"), VERT, 12, ancre="d")


# ---------------------------------------------------------------- la colonne de gauche
def explorateur(L, Z, m, r):
    x, y, w, h = r
    panneau(L, x, y, w, h, t("esp.explorateur"), t("esp.terminaworld"))
    yy = y + 48
    for n in m.get("arbre", []):
        if yy > y + h - 18:
            break
        ind = 14 + 16 * min(n["prof"], 5)
        if n.get("ici"):
            L.append(("rrect", x + 8, yy - 12, w - 16, 24, 7, _a(VERT, 30), _a(VERT, 120), 1))
            L.append(("rect", x + 8, yy - 10, 2, 20, VERT))
        dossier = n["dossier"]
        c_icone = (VERT if n.get("ici") else (124, 132, 150, 255)) if dossier else (110, 118, 135, 255)
        ix = x + ind
        if dossier:
            L.append(("rrect", ix, yy - 6, 13, 10, 2, _a(c_icone, 200), None, 0))
            L.append(("rrect", ix, yy - 8, 6, 4, 1, _a(c_icone, 200), None, 0))
        else:
            L.append(("rrect", ix + 2, yy - 7, 9, 12, 1, None, _a(c_icone, 220), 1))
        nom = n["nom"]
        couleur = VERT if n.get("ici") else (TEXTE if not n.get("brume") else DOUX)
        if n.get("chemin_actif"):
            couleur = CYAN
        L.append(("texte", ix + 20, yy, court(nom, w - ind - 110, 13.5, True), 13.5, couleur, bool(n.get("ici")), "g",
                  True))
        mq = n.get("marque")
        if mq:
            txt, cm = mq
            L.append(("texte", x + w - 14, yy, txt, 11, cm, False, "d", False))
        Z.append((x + 8, yy - 12, w - 16, 24, "lieu:" + n.get("rel", "")))
        yy += 23.5


def envies(L, Z, m, r):
    x, y, w, h = r
    panneau(L, x, y, w, h, t("esp.envies", nom=m.get("nom", "")), t("esp.sur100"))
    yy = y + 48
    for nom_, cle, v, monte in m.get("envies", []):
        L.append(("texte", x + 16, yy, nom_, 13, TEXTE, False, "g", False))
        bx, bw = x + 118, w - 172
        L.append(("rrect", bx, yy - 3, bw, 6, 3, (255, 255, 255, 18), None, 0))
        c = COUL_ENVIES.get(cle, VERT)
        L.append(("rrect", bx, yy - 3, max(6, bw * max(0, min(100, v)) / 100), 6, 3, rgb(c), None, 0))
        L.append(("texte", x + w - 16, yy, f"{int(v)}" + ("↑" if monte else ""), 12, VERT if monte else DOUX, monte,
                  "d", True))
        yy += 26
    # l'assiette du jour (satiété)
    if not m.get("assiette_visible", True):
        return
    yy += 4
    L.append(("ligne", x + 16, yy - 8, x + w - 16, yy - 8, BORD, 1, None))
    L.append(("texte", x + 16, yy + 8, t("esp.assiette"), 12, DOUX, False, "g", False))
    ax = x + 98
    for fam, mangee, coul in m.get("assiette", []):
        L.append(("ellipse", ax + 9, yy + 8, 9, 9, _a(coul, 200) if mangee else (255, 255, 255, 14)))
        if not mangee:
            L.append(("cercle", ax + 9, yy + 8, 9, _a(coul, 110), 1))
        L.append(("texte", ax + 9, yy + 8, fam[:1].upper(), 9.5, (12, 14, 20, 255) if mangee else _a(coul, 200), True,
                  "c", False))
        ax += 23
    se = m.get("satiete", ("", DOUX))
    L.append(("texte", x + w - 16, yy + 8, se[0], 11.5, se[1], False, "d", False))


def equipe(L, Z, m, r):
    x, y, w, h = r
    eq = m.get("equipe_lignes", [])
    panneau(L, x, y, w, h, t("esp.equipe"), f"{len(eq)} / {m.get('equipe_max', 6)}")
    yy = y + 42
    for i, (alb, nom, sous, statut, nom_statut, actif) in enumerate(eq[:5]):
        if yy + 44 > y + h:
            break
        if actif:
            L.append(("rrect", x + 10, yy, w - 20, 44, 9, (255, 255, 255, 12), BORD_FORT, 1))
        if alb:
            creature_img(L, alb, "assis", 0, x + 34, yy + 38, 32)
        L.append(("texte", x + 58, yy + 14, nom, 13, TEXTE, False, "g", False))
        L.append(("texte", x + 58, yy + 31, court(sous, w - 150, 11), 11, PALE, False, "g", False))
        c = COUL_STATUT.get(statut, BLEU)
        L.append(("ellipse", x + w - 26 - lt(nom_statut, 12), yy + 22, 3.5, 3.5, c))
        L.append(("texte", x + w - 16, yy + 22, nom_statut, 12, DOUX, False, "d", False))
        Z.append((x + 10, yy, w - 20, 44, f"equipe:{i}"))
        yy += 48


# ---------------------------------------------------------------- la vue déployée
def vue_deployee(L, Z, m, r):
    x, y, w, h = r
    dp = m.get("deploie")
    panneau(L, x, y, w, h, t("esp.vue_deployee"))
    if not dp or not dp.get("blocs"):
        L.append(("texte", x + w / 2, y + h / 2, t("esp.deploie_vide"), 14, DOUX, False, "c", False))
        return
    bl, actif, phase = dp["blocs"], dp["actif"], dp.get("phase", 0.0)
    # en-tête : étape k / n, pas à pas, auto
    xx = x + w - 16
    auto = dp.get("auto", True)
    xx -= chip(L, xx, y + 22, t("esp.auto"), VERT if auto else PALE, 11.5, ancre="d") + 10
    L.append(("texte", xx, y + 22, t("esp.pas_a_pas"), 12, DOUX, False, "d", False))
    xx -= lt(t("esp.pas_a_pas"), 12) + 8
    e_w = lt(t("esp.entree"), 11) + 12
    L.append(("rrect", xx - e_w, y + 12, e_w, 20, 5, (255, 255, 255, 12), BORD_FORT, 1))
    L.append(("texte", xx - e_w / 2, y + 22, t("esp.entree"), 11, TEXTE, False, "c", True))
    Z.append((xx - e_w, y + 10, e_w + lt(t("esp.pas_a_pas"), 12) + 8, 24, "dep:pas"))
    xx -= e_w + 10
    L.append(("texte", xx, y + 22, t("esp.etape", k=actif, n=len(bl)), 12, DOUX, False, "d", False))
    # les blocs
    taille = 24
    gap = 20
    largeurs = []

    def mesurer(tl):
        out = []
        for b in bl:
            bw = lt(b["t"], tl, True) + 26
            lab = max(lt(D.nom_genre(b["g"]).upper(), 10), min(150, lt(D.courte(b, bl), 11.5)))
            out.append((bw, max(bw, lab)))
        return out
    while taille > 12:
        largeurs = mesurer(taille)
        if sum(c for _b, c in largeurs) + gap * (len(bl) - 1) <= w - 40:
            break
        taille -= 2
        gap = max(8, gap - 3)
    total = sum(c for _b, c in largeurs) + gap * (len(bl) - 1)
    bx = x + 20 + max(0, (w - 40 - total) / 2) if total < w - 40 else x + 20
    cy = y + 72
    rangs = {}
    for b, (bw, cw) in zip(bl, largeurs):
        cx = bx + cw / 2
        rangs[b["i"]] = (cx, bw)
        col = D.COULEURS[b["g"]]
        if b["i"] < actif:
            fond, bord, tc, ep, a_lab = _a(col, 22), _a(col, 170), rgb(col), 1.2, 255
        elif b["i"] == actif:
            for k in range(3):
                L.append(("rrect", cx - bw / 2 - 3 - 2 * k, cy - 25 - 3 - 2 * k, bw + 6 + 4 * k, 50 + 6 + 4 * k,
                          14 + 2 * k, None, _a(col, 60 - 18 * k), 2))
            fond, bord, tc, ep, a_lab = _a(col, 40), rgb(col), rgb(col), 2.5, 255
        else:
            fond, bord, tc, ep, a_lab = (255, 255, 255, 6), _a(col, 60), _a(col, 110), 1, 110
        L.append(("rrect", cx - bw / 2, cy - 23, bw, 46, 10, fond, bord, ep))
        L.append(("texte", cx, cy, b["t"], taille, tc, True, "c", True))
        # le numéro dans un petit rond
        nx, ny = cx - bw / 2 + 2, cy - 25
        L.append(("ellipse", nx, ny, 9.5, 9.5, PANNEAU))
        L.append(("cercle", nx, ny, 9.5, _a(col, 230 if b["i"] <= actif else 90), 1.3))
        L.append(("texte", nx, ny, str(b["i"]), 10, _a(TEXTE, a_lab), True, "c", False))
        L.append(("texte", cx, cy + 37, D.nom_genre(b["g"]).upper(), 10, _a(col, a_lab), True, "c", False))
        for j, ligne in enumerate(couper(D.courte(b, bl), max(110, min(160, cw + 10)), 11.5)[:2]):
            L.append(("texte", cx, cy + 53 + 15 * j, ligne, 11.5, _a(DOUX, 255 if b["i"] <= actif else 120), False, "c",
                      False))
        Z.append((cx - bw / 2, cy - 23, bw, 46, f"dep:bloc:{b['i']}"))
        bx += cw + gap
    # les tuyaux, la redirection, le résultat
    flux_ligne(L, m, dp, x, y + 162, w, 120, rangs)
    # pied : le chemin sur la carte, la légende
    py = y + h - 22
    lieu = dp.get("lieu")
    if lieu:
        txt = t("esp.est_dans", f=lieu[0], lieu=lieu[1])
        L.append(("texte", x + 18, py, txt, 12, CYAN, False, "g", False))
        tx = x + 22 + lt(txt, 12) * 0.95
        L.append(("texte", tx, py, "→", 12, DOUX, False, "g", False))
        L.append(("ellipse", tx + 24, py, 4.5, 4.5, JAUNE))
        L.append(("texte", tx + 33, py, t("esp.sur_la_carte"), 12, JAUNE, False, "g", False))
        Z.append((tx, py - 10, 120, 20, "onglet:carte"))
    lx = x + w - 16
    for g in ("tuyau", "chemin", "argument", "option", "commande"):
        n = D.nom_genre(g)
        L.append(("texte", lx, py, n, 11.5, DOUX, False, "d", False))
        lx -= lt(n, 11.5) * 1.06 + 9
        L.append(("ellipse", lx, py, 4, 4, rgb(D.COULEURS[g])))
        lx -= 16


def _etape_de(dp, k):
    """(chaîne, numéro de l'étape) qui contient le bloc d'indice k (0…), ou (None, None)."""
    for c in dp.get("chaines", []):
        for j, e in enumerate(c["etapes"]):
            if e["debut"] <= k <= e["fin"]:
                return c, j
    return None, None


def flux_ligne(L, m, dp, x, y, w, h, rangs):
    """La rangée du milieu : la sortie de la première commande, le tuyau animé avec la ligne qui passe, ce que la
    deuxième garde (les lignes rejetées barrées), puis le résultat ; ou les lignes qui tombent dans le fichier."""
    bl, actif, phase = dp["blocs"], dp["actif"], dp.get("phase", 0.0)
    chs = dp.get("chaines", [])
    sorties = dp.get("sorties") or [None] * len(chs)
    # la chaîne et le tuyau à montrer : celui de l'étape actuelle (ou le dernier passé)
    ch_i, j = 0, 0
    b_act = bl[actif - 1]
    k = actif - 1
    for ci, c in enumerate(chs):
        if c["debut"] <= k <= c["fin"]:
            ch_i = ci
            for jj, e in enumerate(c["etapes"]):
                if e["debut"] <= k:
                    j = jj
    if not chs:
        return
    c = chs[ch_i]
    s = sorties[ch_i] if ch_i < len(sorties) else None
    et = c["etapes"]
    bx_w = 250
    gx = x + 20
    if len(et) >= 2:
        a_i = max(0, min(j - (1 if b_act["g"] != "tuyau" and j > 0 else 0), len(et) - 2))
        if b_act["g"] == "tuyau":
            a_i = max(0, j)
        ea, eb = et[a_i], et[a_i + 1]
        la = (s[a_i] if s else None) or []
        lb = (s[a_i + 1] if s else None) or []
        vu_a = actif - 1 >= ea["debut"]
        vu_tuyau = actif - 1 > ea["fin"]
        vu_b = actif - 1 >= eb["debut"]
        # boîte A
        boite_sortie(L, gx, y, bx_w, h, ea["texte"], t("esp.lignes_sortent", n=len(la)) if s else "", la, None,
                     vu_a, VERT)
        # le tuyau
        tx1, tx2 = gx + bx_w, gx + bx_w + w - 2 * bx_w - 210
        ty = y + h / 2
        coul = VIOLET if vu_tuyau else _a(VIOLET, 70)
        L.append(("texte", (tx1 + tx2) / 2, ty - 30, t("esp.le_tuyau"), 11.5, coul, False, "c", False))
        L.append(("rrect", tx1 + 4, ty - 16, tx2 - tx1 - 8, 32, 16, _a(VIOLET, 18 if vu_tuyau else 6), coul, 1.5))
        dec = (phase * 60) % 14
        L.append(("ligne", tx1 + 16, ty, tx2 - 16, ty, coul, 1.5, (7, 7, -dec)))
        L.append(("poly", [(tx2 - 8, ty), (tx2 - 18, ty - 7), (tx2 - 18, ty + 7)], coul))
        if vu_tuyau and la:
            if b_act["g"] == "tuyau":
                ligne_ici = la[int(phase * len(la) * 1.0) % len(la)]
                pos = (phase * len(la)) % 1.0
            else:
                ligne_ici = la[-1]
                pos = 0.5
            et_txt = court(ligne_ici, 140, 11.5, True)
            ew = lt(et_txt, 11.5, True) + 18
            ex = tx1 + 18 + pos * (tx2 - tx1 - 36 - ew)
            L.append(("rrect", ex, ty - 11, ew, 22, 11, (16, 14, 30, 255), VIOLET, 1.2))
            L.append(("texte", ex + ew / 2, ty, et_txt, 11.5, TEXTE, True, "c", True))
        # boîte B (les lignes gardées et les lignes rejetées)
        bx = tx2
        rejet = None
        if s and la and lb is not None and eb["cmd"] in ("grep", "egrep", "fgrep"):
            garde = set(lb)
            rejet = [l not in garde for l in la]
        lignes_b = la if rejet is not None else lb
        boite_sortie(L, bx, y, bx_w - 10, h, eb["texte"], t("esp.trie") if rejet is not None else "", lignes_b, rejet,
                     vu_b, VERT, phase=phase if b_act["g"] == "tuyau" else 1.0)
        # le résultat
        rx = bx + bx_w + 10
        L.append(("texte", rx + 6, y + h / 2, "→", 18, DOUX, False, "g", False))
        if c["redir"]:
            fichier(L, rx + 34, y + 6, 150, h - 12, c["redir"][1], lb if s else [], actif, c, phase, b_act)
        else:
            n = len(lb) if s else "?"
            L.append(("rrect", rx + 58, y + 20, 64, 44, 10, _a(VERT, 16), _a(VERT, 110 if vu_b else 40), 1))
            L.append(("texte", rx + 90, y + 42, str(n), 18, VERT if vu_b else PALE, True, "c", True))
            for jj, l in enumerate(couper(t("esp.gardees", n=n), 150, 11.5)[:2]):
                L.append(("texte", rx + 90, y + 82 + 15 * jj, l, 11.5, DOUX, False, "c", False))
        return
    # une seule commande : sa sortie, et la redirection s'il y en a une
    e = et[0]
    la = (s[0] if s else None) or []
    boite_sortie(L, gx, y, bx_w + 120, h, e["texte"], t("esp.lignes_sortent", n=len(la)) if s else t("esp.pas_lancee"),
                 la, None, True, VERT)
    if c["redir"]:
        fichier(L, gx + bx_w + 180, y + 6, 200, h - 12, c["redir"][1], la, actif, c, phase, b_act)


def boite_sortie(L, x, y, w, h, titre, sous, lignes, rejet, vu, couleur, phase=1.0):
    L.append(("rrect", x, y, w, h, 10, (12, 14, 20, 255), _a(couleur, 130) if vu else BORD, 1))
    L.append(("ellipse", x + 14, y + 17, 3.5, 3.5, couleur if vu else PALE))
    tt = court(titre + (" · " + sous if sous else ""), w - 34, 11)
    L.append(("texte", x + 24, y + 17, tt, 11, DOUX, False, "g", False))
    for i, l in enumerate(lignes[:4]):
        yy = y + 40 + 19 * i
        if yy > y + h - 8:
            break
        txt = court(l, w - 26, 12, True)
        if rejet is not None and i < len(rejet):
            visible = phase >= (i + 1) / (len(lignes[:4]) + 1)
            if not visible:
                L.append(("texte", x + 12, yy, "⋯ " + t("esp.en_route", n=i + 1), 11.5, _a(VIOLET, 180), False, "g",
                          True))
                break
            if rejet[i]:
                L.append(("texte", x + 12, yy, txt, 12, PALE, False, "g", True))
                L.append(("ligne", x + 12, yy, x + 12 + lt(txt, 12, True), yy, PALE, 1, None))
                continue
            L.append(("texte", x + 12, yy, txt, 12, TEXTE, False, "g", True))
            continue
        L.append(("texte", x + 12, yy, txt, 12, TEXTE if vu else DOUX, False, "g", True))
    if not lignes and not sous:
        L.append(("texte", x + 12, y + 44, "…", 12, PALE, False, "g", True))


def fichier(L, x, y, w, h, nom, lignes, actif, c, phase, b_act):
    """Le fichier où tombe la redirection : les lignes y tombent une à une."""
    k_redir = c["redir"][3] + 1
    vu = actif >= k_redir
    tombe = b_act["i"] in (k_redir, k_redir + 1)
    coul = ROSE if vu else _a(ROSE, 70)
    L.append(("rrect", x, y + 18, w, h - 18, 8, _a(ROSE, 14 if vu else 4), coul, 1.3))
    L.append(("rrect", x + w - 22, y + 18, 22, 16, 4, _a(ROSE, 50 if vu else 10), None, 0))
    L.append(("texte", x + 10, y + 32, court("📄 " + nom, w - 30, 11.5), 11.5, coul, True, "g", False))
    n_vu = len(lignes) if (vu and not tombe) else (int(phase * (len(lignes) + 1)) if vu else 0)
    for i, l in enumerate(lignes[:min(n_vu, 4)]):
        L.append(("texte", x + 10, y + 52 + 17 * i, court(l, w - 18, 11, True), 11, TEXTE, False, "g", True))
    if vu and tombe and n_vu < len(lignes):
        # la ligne qui tombe dans le fichier
        q = (phase * (len(lignes) + 1)) % 1.0
        yy = y - 34 + q * 44
        L.append(("texte", x + w / 2, yy, court(lignes[n_vu], w - 10, 11, True), 11, _a(ROSE, 230), True, "c", True))
        L.append(("poly", [(x + w / 2, y + 16), (x + w / 2 - 6, y + 8), (x + w / 2 + 6, y + 8)], ROSE))


# ---------------------------------------------------------------- le terminal
def terminal(L, Z, m, r, t_):
    x, y, w, h = r
    L.append(("rrect", x, y, w, h, 14, TERM, BORD, 1))
    L.append(("rrect", x + 10, y + 12, lt(t("esp.terminal"), 13) + 36, 28, 8, (255, 255, 255, 12), BORD, 1))
    L.append(("ellipse", x + 24, y + 26, 4, 4, VERT))
    L.append(("texte", x + 34, y + 26, t("esp.terminal"), 13, TEXTE, False, "g", False))
    L.append(("texte", x + lt(t("esp.terminal"), 13) + 64, y + 26, m.get("cwd", ""), 13, DOUX, False, "g", False))
    L.append(("ligne", x, y + 48, x + w, y + 48, BORD, 1, None))
    taille = m.get("taille_term", 15.5)
    pas = taille * 1.52
    zone_h = h - 48 - 44
    n = int((zone_h - 16) // pas)
    lignes = list(m.get("lignes", []))
    invite = m.get("invite", [])
    saisie = m.get("saisie", "")
    tout = lignes[-(n - 1):] if n > 1 else []
    yy = y + 48 + 20
    largeur_max = w - 40
    for spans in tout:
        xx = x + 20
        for txt, coul, gras in spans:
            if xx > x + w - 20:
                break
            reste = court(txt, x + w - 20 - xx, taille, True) if lt(txt, taille, True) > x + w - 20 - xx else txt
            L.append(("texte", xx, yy, reste, taille, coul, gras, "g", True))
            xx += lt(reste, taille, True)
        yy += pas
    xx = x + 20
    for txt, coul, gras in invite:
        L.append(("texte", xx, yy, txt, taille, coul, gras, "g", True))
        xx += lt(txt, taille, True)
    vis = saisie if lt(saisie, taille, True) < largeur_max - (xx - x) else "…" + saisie[-int((largeur_max - (xx - x)) /
                                                                                           (taille * 0.6)) + 2:]
    L.append(("texte", xx, yy, vis, taille, TEXTE, True, "g", True))
    if int(t_ * 2) % 2 == 0 or m.get("tape_recent"):
        cx = xx + lt(vis, taille, True) + 1
        L.append(("rect", cx, yy - taille * 0.62, taille * 0.55, taille * 1.24, VERT))
    Z.append((x, y + 48, w, h - 48, "terminal"))
    # le pied : les touches, la leçon en cours
    py = y + h - 22
    L.append(("ligne", x, y + h - 44, x + w, y + h - 44, BORD, 1, None))
    xx = x + 18
    for touches, quoi in ((["Tab"], t("esp.t.complete")), (["↑"], t("esp.t.rappelle")), (["Ctrl", "C"],
                                                                                       t("esp.t.arrete"))):
        for k_i, tch in enumerate(touches):
            tw = lt(tch, 11) + 12
            L.append(("rrect", xx, py - 10, tw, 20, 5, (255, 255, 255, 10), BORD_FORT, 1))
            L.append(("texte", xx + tw / 2, py, tch, 11, TEXTE, False, "c", False))
            xx += tw + 4
            if k_i < len(touches) - 1:
                L.append(("texte", xx, py, "+", 11, DOUX, False, "g", False))
                xx += 12
        L.append(("texte", xx + 2, py, quoi, 12, DOUX, False, "g", False))
        xx += lt(quoi, 12) + 22
    lec = m.get("lecon")
    if lec:
        a = t("esp.lecon_en_cours") + " "
        b = lec["titre"]
        c = " · " + t("esp.etape", k=lec["k"], n=lec["n"])
        fin = x + w - 18
        L.append(("texte", fin, py, c, 12, DOUX, False, "d", False))
        fin -= lt(c, 12) * 0.92
        L.append(("texte", fin, py, b, 12, TEXTE, True, "d", False))
        fin -= lt(b, 12) * 0.95 + 2
        L.append(("texte", fin, py, a, 12, DOUX, False, "d", False))


# ---------------------------------------------------------------- la créature en direct
def direct(L, Z, m, r, t_):
    x, y, w, h = r
    panneau(L, x, y, w, h, t("esp.en_direct", nom=m.get("nom", "")))
    ce = m.get("etat_couleur", VERT)
    chip(L, x + w - 16, y + 25, m.get("etat_nom", ""), ce, 12.5, ancre="d")
    sx, sy, sw, sh = x + 16, y + 52, w - 32, h - 68
    L.append(("rrect", sx, sy, sw, sh, 12, (13, 16, 22, 255), BORD, 1))
    cx, pieds = sx + sw * 0.46, sy + sh - 62
    L.append(("lueur", cx, pieds - sh * 0.3, sh * 0.48, _a(ce, 36)))
    # les mots des dernières commandes qui flottent autour d'elle
    for i, (mot, coul) in enumerate(m.get("mots", [])[:4]):
        ph = (t_ * 0.07 + i * 0.27) % 1.0
        mx = sx + 70 + (i % 2) * 40 + 30 * math.sin(t_ * 0.6 + i * 2)
        my = sy + sh * (0.75 - 0.5 * ph)
        L.append(("texte", mx, my, mot, 12, _a(coul, int(220 * math.sin(math.pi * ph))), True, "c", True))
    an = m.get("anime")
    alb = m.get("album")
    if alb and an:
        haut_c = min(sh * 0.5, 230) if not m.get("classe") else min(sh * 0.5, 190)
        e = haut_c / max(1, alb.ref)
        if not alb.lisse:
            e = max(1.0, float(int(e)))
        ref = alb.images("assis")[0]
        L.append(("ellipse", cx, pieds + 3, ref.w * e * 0.32 * an.ombre, 7 * an.ombre, (0, 0, 0, 90)))
        if an.ancien is not None:
            vieux = alb.image(an.ancien[0], an.ancien[1])
            L.append(("imgt", vieux, cx, pieds + an.dy * e / 2, e, an.ancien[3], alb.lisse, an.sx, an.sy, an.rot,
                      an.ancien[2]))
        cad = alb.image(an.etat, an.k)
        L.append(("imgt", cad, cx, pieds + an.dy * e / 2, e, an.miroir, alb.lisse, an.sx, an.sy, an.rot, an.opacite))
        largeur_corps, haut_corps = ref.w * e, ref.h * e
        for genre, fx, fy, ft, fa in an.effets:
            sens = -1 if an.miroir else 1
            ex, ey, et = cx + sens * fx * largeur_corps, pieds + fy * haut_corps, max(8.0, ft * haut_corps)
            if genre == "z":
                L.append(("texte", ex, ey, "z", et, (190, 215, 255, int(230 * fa)), True, "c", False))
            elif genre == "coeur":
                L.append(("texte", ex, ey, "♥", et, (255, 95, 140, int(255 * fa)), True, "c", False))
            elif genre == "miette":
                L.append(("ellipse", ex, ey, et / 2, et / 2.4, (232, 176, 74, int(255 * fa))))
        Z.append((cx - largeur_corps / 2, pieds - haut_corps, largeur_corps, haut_corps, "creature"))
    # la bulle
    bulle = m.get("bulle")
    if bulle:
        bw = min(230, sw * 0.42)
        lignes = couper(sans_marques(bulle), bw - 28, 13.5)
        if len(lignes) > 4:
            lignes = lignes[:3] + [court(lignes[3] + " …", bw - 28, 13.5)]
        bh = 22 + 20 * len(lignes)
        bx, by = sx + sw - bw - 18, sy + 22
        L.append(("rrect", bx, by, bw, bh, 12, (22, 26, 36, 250), BORD_FORT, 1))
        L.append(("poly", [(bx + 8, by + bh - 26), (bx - 8, by + bh - 14), (bx + 10, by + bh - 12)], (22, 26, 36, 250)))
        for i, l in enumerate(lignes):
            L.append(("texte", bx + 14, by + 21 + 20 * i, l, 13.5, TEXTE, False, "g", False))
    # le pied : espèce · stade, type, XP
    py = sy + sh - 24
    xx = sx + 16
    xx += chip(L, xx, py, m.get("espece_stade", ""), TEXTE, 12.5, fond=(255, 255, 255, 8), point=False,
               bord=BORD_FORT) + 8
    if m.get("type_nom"):
        chip(L, xx, py, m["type_nom"], VERT, 12.5)
    xp = m.get("xp", 0)
    L.append(("texte", sx + sw - 16, py, f"{xp} %", 12.5, DOUX, False, "d", False))
    bw = 110
    bx = sx + sw - 60 - bw
    L.append(("rrect", bx, py - 3, bw, 6, 3, (255, 255, 255, 20), None, 0))
    L.append(("rrect", bx, py - 3, max(6, bw * xp / 100), 6, 3, JAUNE, None, 0))
    L.append(("texte", bx - 10, py, "XP", 12.5, DOUX, False, "d", False))


# ---------------------------------------------------------------- le panneau du moment
def contexte(L, Z, m, r, t_):
    x, y, w, h = r
    L.append(("rrect", x, y, w, h, 14, PANNEAU, BORD, 1))
    ongs = m.get("onglets") or ONGLETS
    ong = m.get("onglet", "carte")
    if ong not in ongs:
        ong = ongs[0]
    xx = x + 14
    for o in ongs:
        lib = t("esp.onglet." + o)
        ow = lt(lib, 13.5) + 30
        if o == ong:
            L.append(("rrect", xx, y + 12, ow, 32, 9, (255, 255, 255, 16), BORD_FORT, 1))
        L.append(("texte", xx + ow / 2, y + 28, lib, 13.5, TEXTE if o == ong else DOUX, False, "c", False))
        Z.append((xx, y + 12, ow, 32, "onglet:" + o))
        xx += ow + 4
    L.append(("texte", x + w - 16, y + 28, {"carte": "tree", "cerveau": "cerveau.sh", "tuyaux": "|",
                                              "lecon": "aide"}[ong], 12, PALE, False, "d", True))
    zone = (x + 14, y + 54, w - 28, h - 54 - 40)
    if ong == "carte":
        carte(L, Z, m, zone, t_, (x, y + h - 22, w))
    elif ong == "cerveau":
        cerveau(L, Z, m, zone, t_, (x, y + h - 22, w))
    elif ong == "tuyaux":
        tuyaux(L, Z, m, zone, t_)
    else:
        lecon(L, Z, m, zone)


def carte(L, Z, m, zone, t_, pied):
    x, y, w, h = zone
    L.append(("rrect", x - 1, y - 1, w + 2, h + 2, 10, None, BORD_FORT, 1))
    L.append(("photo", m.get("photo", "monde"), x, y, w, h))
    ici = m.get("ici_piece")
    lieux = m.get("lieux", {})
    chemin = (m.get("deploie") or {}).get("lieu_piece")
    for p, (fx, fy) in LIEUX_CARTE.items():
        if p not in lieux:
            continue
        nom, etat = lieux[p]
        px, py = x + fx * w, y + fy * h
        if p == ici:
            continue
        sym = {"reveille": "✓ ", "en_cours": "▶ ", "brume": ""}.get(etat, "")
        txt = sym + nom
        tw = lt(txt, 11.5) + 16
        c_b = CYAN if p == chemin else BORD_FORT
        L.append(("rrect", px - tw / 2, py - 11, tw, 22, 11, (10, 12, 18, 215), c_b, 1.3 if p == chemin else 1))
        L.append(("texte", px, py, txt, 11.5, (VERT if etat == "reveille" else TEXTE if etat != "brume" else DOUX),
                  False, "c", False))
        Z.append((px - tw / 2, py - 11, tw, 22, "lieu:" + p))
    if ici in LIEUX_CARTE:
        fx, fy = LIEUX_CARTE[ici]
        px, py = x + fx * w, y + fy * h
        pul = 0.5 + 0.5 * math.sin(t_ * 3)
        L.append(("lueur", px, py, 40 + 8 * pul, (255, 213, 79, 70)))
        L.append(("cercle", px, py, 22 + 3 * pul, JAUNE, 1.6))
        L.append(("ellipse", px, py, 6, 6, JAUNE))
        info = t("esp.tu_es_ici", lieu=m.get("ici_nom", ""))
        bw = max(lt(info, 13) + 40, lt(m.get("cwd", ""), 11, True) + 30)
        bx = min(max(x + 8, px - 30), x + w - bw - 8)
        by = min(py + 34, y + h - 58)
        L.append(("rrect", bx, by, bw, 48, 9, (10, 12, 18, 230), _a(JAUNE, 120), 1))
        L.append(("ellipse", bx + 14, by + 16, 4.5, 4.5, JAUNE))
        L.append(("texte", bx + 24, by + 16, info, 13, TEXTE, True, "g", False))
        L.append(("texte", bx + 14, by + 34, court(m.get("cwd", ""), bw - 24, 11, True), 11, DOUX, False, "g", True))
    px_, py_, pw_ = pied
    xx = px_ + 16
    for sym, txt, c in (("◉", t("esp.l.ici"), DOUX), ("▶", t("esp.l.en_cours"), DOUX), ("✓", t("esp.l.reveille"), VERT),
                        ("□", t("esp.l.pas_visite"), PALE)):
        L.append(("texte", xx, py_, sym + " " + txt, 11.5, c, False, "g", False))
        xx += lt(sym + " " + txt, 11.5) + 16
    L.append(("texte", px_ + pw_ - 16, py_, t("esp.l.lieux"), 11.5, DOUX, False, "d", False))


def cerveau(L, Z, m, zone, t_, pied):
    x, y, w, h = zone
    cv = m.get("cerveau")
    if not cv:
        return
    code = cv["code"]
    cw = w * 0.52
    L.append(("rrect", x, y, cw, h, 10, (11, 13, 19, 255), BORD, 1))
    k, genre = cv["ligne"]
    faites = cv["faites"]
    pas = min(20.0, (h - 20) / max(1, len(code)))
    taille = min(12.0, pas * 0.62)
    for i, l in enumerate(code):
        yy = y + 14 + pas * i
        if i == k:
            c = VERT if genre in ("fait", "vrai") else ROUGE
            L.append(("rect", x + 1, yy - pas / 2, cw - 2, pas, _a(c, 34)))
            L.append(("rect", x + 1, yy - pas / 2, 3, pas, c))
        elif i in faites:
            L.append(("rect", x + 1, yy - pas / 2, cw - 2, pas, (255, 255, 255, 7)))
        L.append(("texte", x + 26, yy, str(i + 1), taille * 0.92, PALE if i != k else TEXTE, False, "d", True))
        col = (120, 130, 150, 255) if l.strip().startswith("#") else TEXTE if (i in faites or i == k) else DOUX
        xx = x + 34
        for mot, cm in colorer_code(l, col):
            vis = court(mot, x + cw - 6 - xx, taille, True) if lt(mot, taille, True) > x + cw - 6 - xx else mot
            L.append(("texte", xx, yy, vis, taille, cm, i == k, "g", True))
            xx += lt(vis, taille, True)
            if xx > x + cw - 8:
                break
    # la machine à états
    mx, mw = x + cw + 10, w - cw - 10
    L.append(("rrect", mx, y, mw, h, 10, (11, 13, 19, 255), BORD, 1))
    L.append(("texte", mx + 12, y + 16, t("cerv.machine", n=len(CV.ETATS)), 11, DOUX, False, "g", False))
    places = {e: (mx + 18 + fx * (mw - 36), y + 50 + fy * (h - 90)) for e, (fx, fy) in CV.PLACES.items()}
    actif = cv["etat"]
    de, vers = cv["de"], cv["vers"]
    for a, b in CV.transitions():
        (x1, y1), (x2, y2) = places[a], places[b]
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1
        nx, ny = -dy / dist * 5, dx / dist * 5           # deux flèches côte à côte (aller et retour)
        x1, y1, x2, y2 = x1 + nx, y1 + ny, x2 + nx, y2 + ny
        r1, r2 = 16 / dist, 18 / dist
        ax1, ay1, ax2, ay2 = x1 + dx * r1, y1 + dy * r1, x2 - dx * r2, y2 - dy * r2
        prise = (a, b) == (de, vers) and de != vers
        if prise:
            dec = (t_ * 40) % 12
            fleche(L, ax1, ay1, ax2, ay2, VERT, 2.2, (6, 6, -dec), 9)
        else:
            fleche(L, ax1, ay1, ax2, ay2, (120, 130, 150, 130), 1.2, None, 6)
    for e, (px, py) in places.items():
        nom = CV.nom_etat(e)
        tw = lt(nom, 12) + 30
        c = rgb(CV.COULEURS[e])
        if e == actif:
            L.append(("lueur", px, py, tw * 0.75, _a(VERT, 60)))
            L.append(("rrect", px - tw / 2, py - 13, tw, 26, 13, _a(VERT, 40), VERT, 2))
        else:
            L.append(("rrect", px - tw / 2, py - 13, tw, 26, 13, (14, 16, 22, 255), BORD_FORT, 1))
        L.append(("ellipse", px - tw / 2 + 13, py, 4, 4, c))
        L.append(("texte", px - tw / 2 + 22, py, nom, 12, TEXTE if e == actif else DOUX, e == actif, "g", True))
        Z.append((px - tw / 2, py - 13, tw, 26, "forcer:" + e))
    # les variables
    vy = y + h - 14
    xx = mx + 12
    for nom_, v in cv["vars"]:
        s = f"{nom_}={v}"
        L.append(("texte", xx, vy, s, 10.5, CYAN, False, "g", True))
        xx += lt(s, 10.5, True) + 10
    # forcer un état
    px_, py_, pw_ = pied
    lib = t("cerv.forcer")
    L.append(("texte", px_ + 16, py_, lib, 12, DOUX, False, "g", False))
    xx = px_ + 22 + lt(lib, 12)
    place = px_ + pw_ - 12 - xx
    besoin = sum(lt(CV.nom_etat(e), 12) + 40 for e in CV.ETATS) + 6 * len(CV.ETATS)
    serre = min(1.0, place / max(1, besoin))
    for e in CV.ETATS:
        nom = CV.nom_etat(e)
        on = cv["force"] == e
        bw = (lt(nom, 12) + 40) * serre
        L.append(("rrect", xx, py_ - 11, bw, 22, 11, _a(VERT, 30) if on else (255, 255, 255, 6),
                  VERT if on else BORD_FORT, 1))
        L.append(("rrect", xx + 7, py_ - 5, 18, 10, 5, VERT if on else (255, 255, 255, 30), None, 0))
        L.append(("ellipse", xx + (20 if on else 12), py_, 4, 4, TEXTE))
        L.append(("texte", xx + 30, py_, nom, 12 * max(0.85, serre), TEXTE if on else DOUX, on, "g", False))
        Z.append((xx, py_ - 11, bw, 22, "forcer:" + e))
        xx += bw + 6 * serre


MOTS_CLES = {"case", "in", "esac", "if", "then", "elif", "fi", "else"}


def colorer_code(ligne, defaut):
    """Les morceaux d'une ligne du cerveau avec leur couleur (mots-clés en rose, nombres en orange, variables en
    cyan, textes en jaune)."""
    import re
    if ligne.strip().startswith("#"):
        return [(ligne, (120, 130, 150, 255))]
    out = []
    for tok in re.findall(r'"[^"]*"|\$\(\(|\)\)|\$\w+|\w+|\s+|[^\w\s]', ligne):
        if tok in MOTS_CLES:
            out.append((tok, ROSE))
        elif tok.startswith('"'):
            out.append((tok, JAUNE))
        elif tok.startswith("$") and len(tok) > 1 and tok[1].isalpha():
            out.append((tok, CYAN))
        elif tok.isdigit():
            out.append((tok, ORANGE))
        else:
            out.append((tok, defaut))
    return out


def tuyaux(L, Z, m, zone, t_):
    """Le graphe des tuyaux de la dernière commande : chaque commande est une boîte, chaque tuyau une flèche avec le
    nombre de lignes qui y passent ; une redirection finit dans un fichier."""
    x, y, w, h = zone
    dp = m.get("deploie")
    L.append(("rrect", x, y, w, h, 10, (11, 13, 19, 255), BORD, 1))
    if not dp or not dp.get("chaines"):
        L.append(("texte", x + w / 2, y + h / 2, t("esp.deploie_vide"), 13, DOUX, False, "c", False))
        return
    yy = y + 40
    for ci, c in enumerate(dp["chaines"][:3]):
        s = (dp.get("sorties") or [None] * 9)[ci]
        n = len(c["etapes"]) + (1 if c["redir"] else 0)
        pas = (h - 40) / max(1, n)
        for j, e in enumerate(c["etapes"]):
            by = yy + pas * j
            bw = min(w - 60, lt(e["texte"], 13, True) + 30)
            bx = x + w / 2 - bw / 2
            L.append(("rrect", bx, by, bw, 36, 9, _a(VERT, 20), _a(VERT, 140), 1.2))
            L.append(("texte", x + w / 2, by + 18, e["texte"], 13, TEXTE, True, "c", True))
            if j < len(c["etapes"]) - 1 or c["redir"]:
                a_y, b_y = by + 38, by + pas - 2
                coul = VIOLET if j < len(c["etapes"]) - 1 else ROSE
                dec = (t_ * 30) % 12
                fleche(L, x + w / 2, a_y, x + w / 2, b_y, coul, 2, (6, 6, -dec), 9)
                nb = len(s[j]) if s else "?"
                L.append(("texte", x + w / 2 + 14, (a_y + b_y) / 2, t("esp.n_lignes", n=nb), 12, coul, False, "g",
                          False))
                sym = "|" if j < len(c["etapes"]) - 1 else c["redir"][0]
                L.append(("texte", x + w / 2 - 14, (a_y + b_y) / 2, sym, 14, coul, True, "d", True))
        if not c["redir"] and s:
            by = yy + pas * (len(c["etapes"]) - 1) + 58
            L.append(("texte", x + w / 2, by, "↓  " + t("esp.gardees", n=len(s[-1])), 12.5, VERT, False, "c", False))
        if c["redir"]:
            by = yy + pas * len(c["etapes"])
            nom = "📄 " + c["redir"][1]
            bw = lt(nom, 13) + 30
            L.append(("rrect", x + w / 2 - bw / 2, by, bw, 36, 9, _a(ROSE, 20), ROSE, 1.2))
            L.append(("texte", x + w / 2, by + 18, nom, 13, ROSE, True, "c", False))
        yy += pas * n
        break


def lecon(L, Z, m, zone):
    x, y, w, h = zone
    L.append(("rrect", x, y, w, h, 10, (11, 13, 19, 255), BORD, 1))
    lec = m.get("lecon")
    if not lec:
        L.append(("texte", x + w / 2, y + h / 2, t("esp.pas_de_lecon"), 13, DOUX, False, "c", False))
        return
    L.append(("texte", x + 18, y + 26, lec["titre"], 17, TEXTE, True, "g", False))
    # les étapes : des petits ronds
    for i in range(lec["n"]):
        c = VERT if i < lec["k"] - 1 else (JAUNE if i == lec["k"] - 1 else (255, 255, 255, 30))
        L.append(("ellipse", x + 24 + 22 * i, y + 54, 6, 6, c))
    L.append(("texte", x + 30 + 22 * lec["n"], y + 54, t("esp.etape", k=lec["k"], n=lec["n"]), 12, DOUX, False, "g",
              False))
    yy = y + 90
    for l in couper(sans_marques(lec.get("dit", "")), w - 36, 14)[:7]:
        L.append(("texte", x + 18, yy, l, 14, TEXTE, False, "g", False))
        yy += 22
    if lec.get("cmd"):
        yy += 10
        L.append(("rrect", x + 14, yy, w - 28, 38, 9, (8, 10, 14, 255), _a(VERT, 120), 1))
        L.append(("texte", x + 28, yy + 19, "$ " + court(lec["cmd"], w - 70, 14, True), 14, VERT, True, "g", True))
        yy += 54
        if D.composee(lec["cmd"]):
            bl = D.blocs(lec["cmd"])
            xx = x + 18
            for b in bl:
                c = rgb(D.COULEURS[b["g"]])
                bw = lt(b["t"], 13, True) + 16
                if xx + bw > x + w - 14:
                    break
                L.append(("rrect", xx, yy, bw, 26, 7, _a(c, 26), c, 1))
                L.append(("texte", xx + bw / 2, yy + 13, b["t"], 13, c, True, "c", True))
                xx += bw + 6
            Z.append((x + 14, yy, w - 28, 26, "dep:lecon"))
    if lec.get("grand"):
        L.append(("texte", x + 18, y + h - 20, court(sans_marques(lec["grand"]), w - 36, 12), 12, PALE, False, "g",
                  False))


# ---------------------------------------------------------------- tout
DESSINS = {"explorateur": lambda L, Z, m, r, t_: explorateur(L, Z, m, r),
           "envies": lambda L, Z, m, r, t_: envies(L, Z, m, r),
           "equipe": lambda L, Z, m, r, t_: equipe(L, Z, m, r),
           "deploie": lambda L, Z, m, r, t_: vue_deployee(L, Z, m, r),
           "terminal": terminal, "direct": direct, "contexte": contexte}
ARRIVEE = 4.0          # secondes : l'animation d'arrivée d'un panneau


def fantome(L, r):
    """Une place encore endormie : un fin pointillé discret."""
    x, y, w, h = r
    c, ti = (255, 255, 255, 26), (6, 8, 0)
    for x1, y1, x2, y2 in ((x, y, x + w, y), (x, y + h, x + w, y + h), (x, y, x, y + h), (x + w, y, x + w, y + h)):
        L.append(("ligne", x1, y1, x2, y2, c, 1, ti))


def arrivee(L, r, age, texte):
    """Un panneau qui vient d'apparaître : un bord doré qui pulse puis s'efface, la pastille « nouveau »."""
    x, y, w, h = r
    k = max(0.0, 1.0 - age / ARRIVEE)
    if k <= 0:
        return
    pul = 0.6 + 0.4 * math.sin(age * 6)
    L.append(("rrect", x - 6, y - 6, w + 12, h + 12, 19, None, _a(JAUNE, int(70 * k * pul)), 7))
    L.append(("rrect", x - 1, y - 1, w + 2, h + 2, 15, None, _a(JAUNE, int(235 * k)), 2.2))
    if age < ARRIVEE * 0.8:
        chip(L, x + w - 14, y, "✦ " + texte, JAUNE, 11.5, fond=(30, 26, 12, 255), ancre="d")


def dalle_visible(m, k):
    v = m.get("visibles")
    if v is None:
        return True
    if k == "contexte":
        return bool(m.get("onglets"))
    return k in v


def scene(m, t_=0.0):
    """(liste de dessin, zones, (W, H) logiques) de tout l'espace de travail, dans les couleurs du thème."""
    v = m.get("visibles")
    intro = v is not None and "ile" not in v and not m.get("classe")
    mise = Mise(m.get("classe", False), m.get("cases"), intro)
    L = [("rect", 0, 0, mise.W, mise.H, FOND)]
    Z = []
    if intro:
        L.append(("rrect", 20, 28, 36, 36, 10, _a(VERT, 30), _a(VERT, 140), 1))
        L.append(("texte", 38, 46, ">_", 14, VERT, True, "c", True))
        L.append(("texte", 68, 37, "Terminagotchi", 17, TEXTE, True, "g", False))
        L.append(("texte", 68, 59, m.get("chapitre", ""), 13, DOUX, False, "g", False))
    else:
        haut(L, Z, m, mise)
    rg = m.get("rangement") and not mise.classe and not intro
    rects = mise.rects()
    for k, r in rects.items():
        if dalle_visible(m, k):
            DESSINS[k](L, Z, m, r, t_)
        elif not rg and not intro:
            fantome(L, r)
    arr = m.get("arrivees") or {}
    pan_de = {"explorateur": ("explorateur",), "envies": ("envies", "assiette"), "equipe": ("equipe",),
              "deploie": ("deploie",), "direct": ("direct",), "contexte": ("carte", "cerveau", "tuyaux")}
    for k, r in rects.items():
        if not dalle_visible(m, k):
            continue
        ages = [arr[p] for p in pan_de.get(k, ()) if p in arr]
        if ages:
            neuf = [p for p in pan_de[k] if p in arr]
            arrivee(L, r, min(ages), t("esp.nouvel_onglet") if k == "contexte" and "carte" not in neuf
                    else t("esp.nouveau"))
    if "ile" in arr and not intro:
        pil = next((op for op in L if op[0] == "rrect" and op[2] == 16 and op[4] == 62), None)
        if pil:
            arrivee(L, (pil[1], 16, pil[3], 62), arr["ile"], t("esp.nouveau"))
    if rg:
        rangement(L, Z, m, mise)
    ile = m.get("ile_ouverte")
    if ile:                                   # l'île de la créature du bureau, ouverte sous la barre
        Li, Zi = ile
        dx = mise.W / 2 - 450
        L.extend(decaler(Li, dx, 70))
        Z.extend((zx + dx, zy + 70, zw, zh, a) for zx, zy, zw, zh, a in Zi)
    th = m.get("theme")
    from . import apparence
    L = apparence.recolorer(L, th)
    if m.get("options"):                      # les vignettes des thèmes sont déjà dans leurs propres couleurs
        O, vignettes = [], []
        options(O, Z, m, mise, vignettes)
        L += apparence.recolorer(O, th) + vignettes
    return L, Z, (mise.W, mise.H)


# ---------------------------------------------------------------- les options (roue dentée)
def apercu_theme(L, x, y, w, h, cle):  # noqa: E302
    """La vignette d'un thème : un petit espace (panneaux, terminal, blocs de la vue déployée) dans ses couleurs."""
    from . import apparence
    th = apparence.Theme(cle)
    P = []
    P.append(("rrect", x, y, w, h, 8, FOND, BORD_FORT, 1))
    P.append(("rrect", x + 6, y + 6, w * 0.22, h - 12, 5, PANNEAU, BORD, 1))
    P.append(("rrect", x + 10 + w * 0.22, y + 6, w * 0.5, h * 0.36, 5, PANNEAU, BORD, 1))
    P.append(("rrect", x + 10 + w * 0.22, y + 10 + h * 0.36, w * 0.5, h * 0.64 - 16, 5, TERM, BORD, 1))
    P.append(("rrect", x + 14 + w * 0.72, y + 6, w * 0.28 - 20, h - 12, 5, PANNEAU, BORD, 1))
    bx = x + 16 + w * 0.22
    for c, lw in ((VERT, 16), (CYAN, 26), (VIOLET, 6), (VERT, 18), (BLEU, 18)):
        P.append(("rrect", bx, y + 14, lw, 10, 3, _a(c, 50), c, 1))
        bx += lw + 4
    for i, c in enumerate((TEXTE, DOUX, VERT, TEXTE)):
        P.append(("rrect", x + 16 + w * 0.22, y + 18 + h * 0.36 + 9 * i, w * (0.4 - 0.07 * (i % 2)), 3, 1, c, None, 0))
    for i, c in enumerate((ORANGE, ROSE, JAUNE, VERT, VIOLET)):
        P.append(("rrect", x + 12, y + 14 + 8 * i, w * 0.22 - 12, 3, 1, _a(c, 220), None, 0))
    L.extend(apparence.recolorer(P, th))


def options(L, Z, m, mise, vignettes=None):
    """Le panneau des options de l'espace : Apparence (thème, disposition, ranger), créature, pour les grands."""
    from . import apparence
    o = m["options"]
    Z.clear()
    L.append(("rect", 0, 0, mise.W, mise.H, (3, 4, 7, 170)))
    x, y, w, h = mise.W / 2 - 640, 70, 1280, mise.H - 110
    L.append(("rrect", x, y, w, h, 20, PANNEAU, BORD_FORT, 1))
    Z.append((x, y, w, h, "opt:panneau"))
    L.append(("texte", x + 30, y + 38, "⚙  " + t("app.options.titre"), 22, TEXTE, True, "g", False))
    L.append(("texte", x + w - 30, y + 38, "✕", 18, DOUX, False, "d", False))
    Z.append((x + w - 60, y + 14, 50, 50, "opt:fermer"))
    cx = x + 30
    yy = y + 86
    L.append(("texte", cx, yy, t("app.opt.apparence").upper(), 12, JAUNE, True, "g", False))
    yy += 28
    L.append(("texte", cx, yy, t("app.opt.theme"), 14.5, TEXTE, True, "g", False))
    L.append(("texte", cx + 90, yy, t("app.opt.theme.aide"), 12.5, PALE, False, "g", False))
    tw, th_ = 214, 120
    for i, cle in enumerate(apparence.ordre()):
        col, lig = i % 5, i // 5
        vx, vy = cx + col * (tw + 24), yy + 22 + lig * (th_ + 44)
        sel = cle == o["theme"]
        apercu_theme(vignettes if vignettes is not None else L, vx, vy, tw, th_, cle)
        L.append(("rrect", vx - 4, vy - 4, tw + 8, th_ + 8, 11, None, _a(JAUNE, 230) if sel else BORD, 2 if sel else 1))
        L.append(("texte", vx + 2, vy + th_ + 17, ("● " if sel else "") + t("app.theme." + cle), 13,
                  JAUNE if sel else TEXTE, sel, "g", False))
        Z.append((vx - 4, vy - 4, tw + 8, th_ + 30, "opt:theme:" + cle))
    yy += 22 + 2 * (th_ + 44) + 14
    L.append(("texte", cx, yy, t("app.opt.dispo"), 14.5, TEXTE, True, "g", False))
    xx = cx
    for nom in apparence.donnees()["ordre_dispositions"]:
        sel = nom == o["dispo"]
        xx += bouton(L, Z, xx, yy + 16, t("app.dispo." + nom), "opt:dispo:" + nom, JAUNE if sel else TEXTE,
                     _a(JAUNE, 30) if sel else None, _a(JAUNE, 200) if sel else None) + 10
    bouton(L, Z, xx + 10, yy + 16, "✎ " + t("esp.rg.titre") + "…", "opt:ranger", VERT, _a(VERT, 26), _a(VERT, 140))
    yy += 76
    L.append(("texte", cx, yy, t("app.opt.creature").upper(), 12, JAUNE, True, "g", False))
    yy += 18
    bw = bouton(L, Z, cx, yy, t("app.options.bureau"), "opt:bureau")
    bouton(L, Z, cx + bw + 12, yy, t("app.options.notifs", etat=t("app.on") if o["notifs"] else t("app.off")),
           "opt:notifs")
    L.append(("texte", x + w - 30, yy + 17, t("app.options.langue", langue=o["langue"]) + "  (tg langue xx)", 13,
              DOUX, False, "d", False))
    yy += 62
    L.append(("rrect", cx - 10, yy - 14, w - 40, 104, 14, _a(JAUNE, 12), _a(JAUNE, 110), 1))
    L.append(("texte", cx + 6, yy + 6, t("app.opt.grands").upper(), 12, JAUNE, True, "g", False))
    L.append(("texte", cx + 6, yy + 36, t("app.opt.tout"), 15, TEXTE, True, "g", False))
    L.append(("texte", cx + 6, yy + 62, t("app.opt.tout.aide"), 12.5, DOUX, False, "g", False))
    on = o["tout"]
    tx = x + w - 96
    L.append(("rrect", tx, yy + 23, 52, 26, 13, _a(JAUNE, 70) if on else (255, 255, 255, 20),
              _a(JAUNE, 200) if on else BORD_FORT, 1))
    L.append(("ellipse", tx + (39 if on else 13), yy + 36, 9, 9, JAUNE if on else DOUX))
    Z.append((tx - 10, yy + 14, 72, 44, "opt:tout"))


# ---------------------------------------------------------------- ranger son espace (mode rangement)
NOMS_DALLES = ("explorateur", "envies", "equipe", "deploie", "terminal", "direct", "contexte")


def poignees(L, Z, k, r, actif=False):
    x, y, w, h = r
    c = JAUNE if actif else (255, 255, 255, 170)
    L.append(("rrect", x, y, w, h, 14, None, _a(c, 200) if actif else (255, 255, 255, 90), 1.5))
    nom = t("esp.dalle." + k)
    pw = lt(nom, 12) + 46
    L.append(("rrect", x + w / 2 - pw / 2, y - 12, pw, 26, 13, (24, 27, 36, 255), _a(c, 220), 1))
    L.append(("texte", x + w / 2, y + 1, "⠿  " + nom, 12, c if actif else TEXTE, True, "c", False))
    Z.append((x + w / 2 - pw / 2, y - 14, pw, 30, "rg:dalle:" + k))
    if k != "terminal":                        # le terminal ne se cache jamais
        L.append(("ellipse", x + w - 4, y + 4, 13, 13, (40, 22, 26, 255)))
        L.append(("cercle", x + w - 4, y + 4, 13, _a(ROUGE, 200), 1.2))
        L.append(("texte", x + w - 4, y + 4, "✕", 12, ROUGE, True, "c", False))
        Z.append((x + w - 17, y - 9, 26, 26, "rg:cacher:" + k))
    L.append(("poly", [(x + w - 4, y + h - 30), (x + w - 4, y + h - 4), (x + w - 30, y + h - 4)], _a(c, 230)))
    Z.append((x + w - 34, y + h - 34, 34, 34, "rg:coin:" + k))


def bouton(L, Z, x, y, texte, action, c=TEXTE, fond=None, bord=None, taille=13.5, gras=False):
    w = lt(texte, taille) + 30
    L.append(("rrect", x, y, w, 34, 10, fond or (255, 255, 255, 14), bord or BORD_FORT, 1))
    L.append(("texte", x + w / 2, y + 17, texte, taille, c, gras, "c", False))
    Z.append((x, y, w, 34, action))
    return w


def rangement(L, Z, m, mise):
    """Le mode « ranger mon espace » : la grille, les poignées, le coin pour agrandir, ✕ pour cacher, le tiroir des
    dalles cachées et le bandeau (Disposition d'origine, Enregistrer comme « Ma disposition », Terminé).
    Les dalles pas encore découvertes n'apparaissent pas (ni dans l'espace, ni dans le tiroir)."""
    from . import apparence
    g = apparence.grille()
    Z.clear()
    L.append(("rect", 0, 0, mise.W, mise.H, (5, 7, 10, 120)))
    for c in range(g["colonnes"] + 1):
        for r in range(g["rangees"] + 1):
            x, y, _w, _h = apparence.rect_de([c, r, 1, 1])
            L.append(("ellipse", x - g["ecart"] / 2, y - g["ecart"] / 2, 1.3, 1.3, (255, 255, 255, 40)))
    gl = m.get("glisse")                       # (dalle, mode « dalle » | « coin », (x, y, w, h) sous la souris, case visée)
    if gl and gl[3]:
        x, y, w, h = apparence.rect_de(gl[3])
        L.append(("rrect", x, y, w, h, 14, _a(JAUNE, 22), _a(JAUNE, 200), 2))
    for k, r in mise.rects().items():
        if not dalle_visible(m, k) or (gl and gl[0] == k):
            continue
        poignees(L, Z, k, r)
    if gl:
        k, _mode, r, _case = gl
        x, y, w, h = r
        L.append(("rrect", x + 10, y + 14, w, h, 16, (0, 0, 0, 120), None, 0))
        DESSINS[k](L, [], m, r, m.get("t", 0.0))
        poignees(L, [], k, r, actif=True)
    # le bandeau, à la place de l'île
    L.append(("rect", 0, 0, mise.W, 92, FOND))
    L.append(("rrect", 16, 14, mise.W - 32, 64, 18, _a(JAUNE, 18), _a(JAUNE, 160), 1.5))
    L.append(("texte", 40, 36, "✎  " + t("esp.rg.titre"), 18, JAUNE, True, "g", False))
    L.append(("texte", 40, 60, t("esp.rg.aide"), 13, DOUX, False, "g", False))
    x = mise.W - 36
    for txt, a, c, f in ((t("esp.rg.fini"), "rg:fini", VERT, _a(VERT, 40)),
                         (t("esp.rg.mienne"), "rg:mienne", TEXTE, None),
                         (t("esp.rg.origine"), "rg:origine", TEXTE, None)):
        x -= lt(txt, 13.5) + 30
        bouton(L, Z, x, 29, txt, a, c, f, _a(c, 150) if f else None, gras=bool(f))
        x -= 12
    caches = [k for k in m.get("caches", []) if k in NOMS_DALLES and dalle_visible(m, k)]
    if caches:
        noms = [t("esp.dalle." + k) for k in caches]
        tw = max(404, 32 + sum(lt("+ " + n, 12.5) + 38 for n in noms))
        tx, ty = mise.W - 16 - tw, mise.H - 130
        L.append(("rrect", tx, ty, tw, 114, 14, PANNEAU2, _a(JAUNE, 120), 1.5))
        L.append(("texte", tx + 16, ty + 20, t("esp.rg.cachees").upper(), 11, DOUX, True, "g", False))
        xx = tx + 16
        for k, n in zip(caches, noms):
            xx += bouton(L, Z, xx, ty + 38, "+ " + n, "rg:remettre:" + k, VERT, _a(VERT, 22), _a(VERT, 120), 12.5) + 8
        L.append(("texte", tx + 16, ty + 94, t("esp.rg.remettre"), 12, PALE, False, "g", False))


def decaler(liste, dx, dy):
    """La même liste de dessin, déplacée de (dx, dy)."""
    out = []
    for op in liste:
        k = op[0]
        if k in ("rrect", "rect", "texte", "ellipse", "arc", "cercle", "lueur"):
            out.append((k, op[1] + dx, op[2] + dy) + tuple(op[3:]))
        elif k in ("img", "imgt"):
            out.append((k, op[1], op[2] + dx, op[3] + dy) + tuple(op[4:]))
        elif k == "ligne":
            out.append((k, op[1] + dx, op[2] + dy, op[3] + dx, op[4] + dy) + tuple(op[5:]))
        elif k == "poly":
            out.append((k, [(a + dx, b + dy) for a, b in op[1]], op[2]))
        elif k == "photo":
            out.append((k, op[1], op[2] + dx, op[3] + dy) + tuple(op[4:]))
        else:
            out.append(op)
    return out


def a_l_echelle(liste, e, ox=0.0, oy=0.0):
    """La liste de dessin agrandie e fois (et décalée) : la fenêtre a la taille qu'elle veut, le dessin suit."""
    if e == 1 and not ox and not oy:
        return liste
    out = []
    for op in liste:
        k = op[0]
        if k == "rrect":
            _, x, y, w, h, r, f, b, ep = op
            out.append((k, x * e + ox, y * e + oy, w * e, h * e, r * e, f, b, ep * e))
        elif k == "rect":
            _, x, y, w, h, c = op
            out.append((k, x * e + ox, y * e + oy, w * e, h * e, c))
        elif k == "texte":
            _, x, y, s, sz, c, g, an, mono = op
            out.append((k, x * e + ox, y * e + oy, s, sz * e, c, g, an, mono))
        elif k == "ellipse":
            _, cx, cy, rx, ry, c = op
            out.append((k, cx * e + ox, cy * e + oy, rx * e, ry * e, c))
        elif k == "cercle":
            _, cx, cy, r, c, ep = op
            out.append((k, cx * e + ox, cy * e + oy, r * e, c, ep * e))
        elif k == "lueur":
            _, cx, cy, r, c = op
            out.append((k, cx * e + ox, cy * e + oy, r * e, c))
        elif k == "img":
            _, cad, x, y, ee, mi, li = op
            out.append((k, cad, x * e + ox, y * e + oy, ee * e, mi, li))
        elif k == "imgt":
            _, cad, ax, ay, ee, mi, li, sx, sy, rot, al = op
            out.append((k, cad, ax * e + ox, ay * e + oy, ee * e, mi, li, sx, sy, rot, al))
        elif k == "ligne":
            _, x1, y1, x2, y2, c, ep, ti = op
            ti = None if ti is None else (ti[0] * e, ti[1] * e, ti[2] * e)
            out.append((k, x1 * e + ox, y1 * e + oy, x2 * e + ox, y2 * e + oy, c, ep * e, ti))
        elif k == "poly":
            out.append((k, [(a * e + ox, b * e + oy) for a, b in op[1]], op[2]))
        elif k == "photo":
            _, nom, x, y, w, h = op
            out.append((k, nom, x * e + ox, y * e + oy, w * e, h * e))
        elif k == "arc":
            _, cx, cy, rx, ry, c, ep = op
            out.append((k, cx * e + ox, cy * e + oy, rx * e, ry * e, c, ep))
        else:
            out.append(op)
    return out


# ---------------------------------------------------------------- capture (PIL : tests, captures pour le propriétaire)
_POLICES = {}
import re as _re  # noqa: E402
_SANS_EMOJI = _re.compile("[\U0001F000-\U0001FFFF\uFE0F\u200d]")


def _police(sz, gras, mono, texte):
    from PIL import ImageFont
    ecriture = "cjk" if any(0x2E80 <= ord(ch) <= 0xFFEF for ch in texte) else \
        ("sym" if any(0x2190 <= ord(ch) < 0x2E80 for ch in texte) else "")
    cle = (round(sz, 2), gras, mono, ecriture)        # la taille exacte (la mise en page compte au centième)
    if cle not in _POLICES:
        if mono:
            noms = ["DejaVuSansMono-Bold.ttf" if gras else "DejaVuSansMono.ttf"]
        else:
            noms = ["Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"] if gras else ["Inter-Regular.otf", "DejaVuSans.ttf"]
        if ecriture == "cjk":
            noms = ["NotoSansCJK-Bold.ttc" if gras else "NotoSansCJK-Regular.ttc"] + noms
        elif ecriture == "sym":
            noms = (["DejaVuSansMono-Bold.ttf" if gras else "DejaVuSansMono.ttf"] if mono else
                    ["DejaVuSans-Bold.ttf" if gras else "DejaVuSans.ttf"]) + noms
        f = None
        for n in noms:
            try:
                # taille fractionnaire (15,5 px), comme la mise en page : arrondie à 16 px, chaque morceau coloré était
                # 3 % plus large que prévu et le suivant le recouvrait (« découvrirls -R », « …terminagotchipu… »)
                f = ImageFont.truetype(n, max(4.0, float(sz)))
                break
            except OSError:
                continue
        from PIL import ImageFont as IF
        _POLICES[cle] = f or IF.load_default()
    return _POLICES[cle]


def photo_pil(nom):
    """L'illustration nom (PIL, RGBA) : « monde » = la carte du Terminaworld (carte_monde.png)."""
    import io
    import pkgutil
    from PIL import Image
    base, _, th = nom.partition(":")             # « monde:matrix » : la carte teintée du thème
    data = pkgutil.get_data(__package__, "carte_monde.png") if base == "monde" else None
    if not data:
        return None
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    if th:
        from . import apparence
        im = apparence.teinter_image(im, apparence.Theme(th))
    return im


def photo_png(nom):
    """L'illustration en PNG (fenêtre GTK) : la carte teintée si PIL est là, sinon la carte d'origine."""
    import io
    import pkgutil
    if ":" in nom:
        try:
            im = photo_pil(nom)
            b = io.BytesIO()
            im.save(b, "PNG")
            return b.getvalue()
        except Exception:                        # noqa: BLE001 — sans PIL : la carte d'origine
            pass
    return pkgutil.get_data(__package__, "carte_monde.png") if nom.partition(":")[0] == "monde" else None


def vers_pil(liste, taille, image=None):
    """Dessine une liste dans une image PIL (RGBA), rapidement (chaque forme dans son petit calque)."""
    from PIL import Image, ImageDraw
    from . import bureau_scene as S
    W, H = taille
    img = image if image is not None else Image.new("RGBA", (W, H), (0, 0, 0, 255))
    photos = {}
    SS = 3                                   # sur-échantillonnage des formes (bords doux)

    def calque(x0, y0, x1, y1):
        x0, y0 = int(math.floor(x0)) - 2, int(math.floor(y0)) - 2
        x1, y1 = int(math.ceil(x1)) + 2, int(math.ceil(y1)) + 2
        return x0, y0, max(1, x1 - x0), max(1, y1 - y0)

    def poser(c, x0, y0):
        if x0 + c.width < 0 or y0 + c.height < 0 or x0 >= W or y0 >= H:
            return
        img.alpha_composite(c, (max(0, x0), max(0, y0)), (max(0, -x0), max(0, -y0)))

    def forme(x0, y0, x1, y1, dessin):
        cx0, cy0, cw, ch = calque(x0, y0, x1, y1)
        c = Image.new("RGBA", (cw * SS, ch * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        dessin(d, lambda v, o: (v - o) * SS, cx0, cy0)
        c = c.resize((cw, ch), Image.LANCZOS)
        poser(c, cx0, cy0)

    for op in liste:
        k = op[0]
        if k in ("img", "imgt"):
            S.vers_pil([op], (W, H), image=img)
            continue
        if k == "rect":
            _, x, y, w, h, c = op
            if c[3] == 255:
                ImageDraw.Draw(img).rectangle((round(x), round(y), round(x + w) - 1, round(y + h) - 1), fill=c)
            elif w >= 1 and h >= 1:
                lay = Image.new("RGBA", (max(1, round(w)), max(1, round(h))), c)
                poser(lay, round(x), round(y))
        elif k == "rrect":
            _, x, y, w, h, r, f, b, ep = op
            if w < 1 or h < 1:
                continue

            def des(d, s, cx0, cy0, x=x, y=y, w=w, h=h, r=r, f=f, b=b, ep=ep):
                box = (s(x, cx0), s(y, cy0), s(x + w, cx0), s(y + h, cy0))
                d.rounded_rectangle(box, radius=max(0, min(r, w / 2, h / 2)) * SS, fill=f,
                                    outline=b if (b and ep) else None, width=max(1, int(round(ep * SS))) if b else 0)
            forme(x, y, x + w, y + h, des)
        elif k == "ellipse":
            _, cx, cy, rx, ry, f = op

            def des(d, s, cx0, cy0, cx=cx, cy=cy, rx=rx, ry=ry, f=f):
                d.ellipse((s(cx - rx, cx0), s(cy - ry, cy0), s(cx + rx, cx0), s(cy + ry, cy0)), fill=f)
            forme(cx - rx, cy - ry, cx + rx, cy + ry, des)
        elif k == "cercle":
            _, cx, cy, r, c, ep = op

            def des(d, s, cx0, cy0, cx=cx, cy=cy, r=r, c=c, ep=ep):
                d.ellipse((s(cx - r, cx0), s(cy - r, cy0), s(cx + r, cx0), s(cy + r, cy0)), outline=c,
                          width=max(1, int(round(ep * SS))))
            forme(cx - r, cy - r, cx + r, cy + r, des)
        elif k == "arc":
            _, cx, cy, rx, ry, c, ep = op

            def des(d, s, cx0, cy0, cx=cx, cy=cy, rx=rx, ry=ry, c=c, ep=ep):
                for i in range(0, 360, 6):
                    d.arc((s(cx - rx, cx0), s(cy - ry, cy0), s(cx + rx, cx0), s(cy + ry, cy0)), i, i + 3, fill=c,
                          width=ep * SS)
            forme(cx - rx, cy - ry, cx + rx, cy + ry, des)
        elif k == "lueur":
            _, cx, cy, r, c = op
            cx0, cy0, cw, ch = calque(cx - r, cy - r, cx + r, cy + r)
            n = 24
            lay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            dl = ImageDraw.Draw(lay)
            for i in range(n, 0, -1):
                rr = r * i / n
                a = int(c[3] * (1 - i / n) ** 1.5 * 2.2)
                dl.ellipse((cx - cx0 - rr, cy - cy0 - rr, cx - cx0 + rr, cy - cy0 + rr), fill=c[:3] + (min(255, a),))
            from PIL import ImageFilter
            lay = lay.filter(ImageFilter.GaussianBlur(r / 10))
            poser(lay, cx0, cy0)
        elif k == "ligne":
            _, x1, y1, x2, y2, c, ep, ti = op

            def des(d, s, cx0, cy0, x1=x1, y1=y1, x2=x2, y2=y2, c=c, ep=ep, ti=ti):
                lg = math.hypot(x2 - x1, y2 - y1)
                if ti is None or lg < 1:
                    d.line((s(x1, cx0), s(y1, cy0), s(x2, cx0), s(y2, cy0)), fill=c, width=max(1, int(ep * SS)))
                    return
                on, off, dec = ti
                p = -(dec % (on + off))
                while p < lg:
                    a, b = max(0, p), min(lg, p + on)
                    if b > a:
                        d.line((s(x1 + (x2 - x1) * a / lg, cx0), s(y1 + (y2 - y1) * a / lg, cy0),
                                s(x1 + (x2 - x1) * b / lg, cx0), s(y1 + (y2 - y1) * b / lg, cy0)), fill=c,
                               width=max(1, int(ep * SS)))
                    p += on + off
            forme(min(x1, x2) - ep, min(y1, y2) - ep, max(x1, x2) + ep, max(y1, y2) + ep, des)
        elif k == "poly":
            _, pts, c = op
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]

            def des(d, s, cx0, cy0, pts=pts, c=c):
                d.polygon([(s(a, cx0), s(b, cy0)) for a, b in pts], fill=c)
            forme(min(xs), min(ys), max(xs), max(ys), des)
        elif k == "texte":
            _, x, y, s, sz, c, gras, ancre, mono = op
            if not s or c[3] == 0:
                continue
            # (captures : pas de police d'emoji ici ; les fenêtres les dessinent) : un blanc de la même largeur, pour
            # que les morceaux suivants de la ligne restent à leur place
            s = _SANS_EMOJI.sub(lambda m: "" if m.group() in "\ufe0f\u200d" else "  " if mono else " ", s)
            if not s.strip():
                continue
            f = _police(sz, gras, mono, s)
            an = {"g": "lm", "c": "mm", "d": "rm"}[ancre]
            if c[3] == 255:
                ImageDraw.Draw(img).text((x, y), s, font=f, fill=c, anchor=an)
            else:                                    # un texte transparent : dans son petit calque
                b0 = f.getbbox(s, anchor=an)
                lay = Image.new("RGBA", (b0[2] - b0[0] + 4, b0[3] - b0[1] + 4), (0, 0, 0, 0))
                ImageDraw.Draw(lay).text((2 - b0[0], 2 - b0[1]), s, font=f, fill=c, anchor=an)
                poser(lay, int(round(x)) + b0[0] - 2, int(round(y)) + b0[1] - 2)
        elif k == "photo":
            _, nom, x, y, w, h = op
            if nom not in photos:
                photos[nom] = photo_pil(nom)
            p = photos[nom]
            if p is None:
                continue
            # recadrée pour remplir (cover), coins arrondis
            r_ = max(w / p.width, h / p.height)
            pw, ph = int(math.ceil(p.width * r_)), int(math.ceil(p.height * r_))
            q = p.resize((pw, ph), Image.LANCZOS).crop((int((pw - w) / 2), int((ph - h) / 2),
                                                         int((pw - w) / 2) + int(w), int((ph - h) / 2) + int(h)))
            masque = Image.new("L", q.size, 0)
            ImageDraw.Draw(masque).rounded_rectangle((0, 0, q.width - 1, q.height - 1), radius=9, fill=255)
            q.putalpha(masque)
            poser(q, int(x), int(y))
    return img
