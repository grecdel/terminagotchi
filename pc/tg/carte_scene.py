"""La carte du Terminaworld dans l'espace de travail (`tg espace`, onglet Carte) : liste de dessin (comme
espace_scene.py), même dessin que la carte du téléphone (EspaceDessin.kt, carteMonde).

Maquettes validées le 3 novembre (outils/reveil/planche_reveil.png, outils/ameliorations/monde/planche_1.png et 2) :
  - la carte mélangée vivant / endormi selon la partie (reveil.py) et le moment de la journée ;
  - le réveil d'un biome : une vague de couleur part de son cœur (2 à 3 s, un clic la passe) ; un lieu qui s'allume
    (1 s) ; un chemin qui se dessine depuis le Carrefour (2 s) ; une seule animation à la fois ;
  - les lieux (rond vert allumé, jaune ouvert, gris pas encore avec « ? »), les chemins, les lieux secrets trouvés (★),
    les habitants (portrait dans un rond, « ! » jaune), l'événement rare du jour, la météo de l'activité, les étoiles
    la nuit, la neige ou les pétales selon la saison ;
  - survol d'un lieu = une bulle, clic = « Y aller » (la commande cd est écrite dans le terminal, l'enfant appuie
    lui-même sur Entrée), clic droit = la fiche « En savoir plus » ; le livre des gardiens et le carnet des
    événements rares.
Le modèle (m["reveil"]) est préparé par espace.py (Controleur._reveil).
Nouvel ordre de dessin : ("photoc", nom, x, y, w, h, cx, cy, r) = une illustration découpée dans un disque.
"""
import math

from . import espace_scene as S
from .langue import t

VERT, JAUNE, PALE, TEXTE, DOUX, CYAN = S.VERT, S.JAUNE, S.PALE, S.TEXTE, S.DOUX, S.CYAN
COUL_ETAT = {"allume": VERT, "ouvert": JAUNE, "ferme": (150, 156, 170, 255)}


def _h(*a):
    """Un petit hasard fixe (le même à chaque image) : 0 ≤ x < 1."""
    x = 0
    for v in a:
        x = (x * 1103515245 + int(v) * 2654435761 + 12345) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 1274126177) & 0xFFFFFFFF
    return (x & 0xFFFFFF) / 0x1000000


class Repere:
    """La carte (960×540, recadrée pour remplir la zone) : fraction de l'image → point de l'écran."""

    def __init__(self, x, y, w, h):
        self.r = max(w / 960, h / 540)
        self.iw, self.ih = 960 * self.r, 540 * self.r
        self.ix, self.iy = x + (w - self.iw) / 2, y + (h - self.ih) / 2
        self.zone = (x, y, w, h)

    def p(self, fx, fy):
        return self.ix + fx * self.iw, self.iy + fy * self.ih

    def dedans(self, px, py, marge=0):
        x, y, w, h = self.zone
        return x + marge <= px <= x + w - marge and y + marge <= py <= y + h - marge


def dessiner(L, Z, m, zone, t_, pied):
    x, y, w, h = zone
    rv = m["reveil"]
    R = Repere(x, y, w, h)
    L.append(("rrect", x - 1, y - 1, w + 2, h + 2, 10, None, S.BORD_FORT, 1))
    an = rv.get("anim")
    if an and an["type"] in ("biome", "resume", "lieu"):
        L.append(("photo", an["avant"], x, y, w, h))
        cx, cy = R.p(*an["c"])
        rmax = math.hypot(max(cx - x, x + w - cx), max(cy - y, y + h - cy))
        rr = (rmax if an["type"] != "lieu" else 90 * R.r) * min(1.0, an["p"] * 1.15)
        L.append(("photoc", an["apres"], x, y, w, h, cx, cy, rr))
    else:
        L.append(("photo", rv["photo"], x, y, w, h))
    sous = []
    decor(sous, rv, R, t_)
    chemins(sous, rv, R, t_)
    evenement(sous, rv, R, t_)
    secrets(sous, rv, R, t_)
    lieux(sous, Z, rv, R, t_, m)
    habitants(sous, Z, rv, R, t_)
    if an:
        animation(sous, an, R, t_)
    L.append(("calque", x, y, w, h, sous))
    if an:
        Z.append((x, y, w, h, "rv:passer"))
    if rv.get("survol") and not an and not rv.get("fiche"):
        bulle(L, rv, R)
    if rv.get("fiche"):
        fiche(L, Z, rv, zone)
    elif rv.get("livre"):
        livre(L, Z, rv, zone)
    elif rv.get("carnet"):
        carnet(L, Z, rv, zone)
    legende(L, Z, rv, pied)


# ---------------------------------------------------------------- le décor : météo, nuit, saison
def decor(L, rv, R, t_):
    x, y, w, h = R.zone
    q = rv.get("moment", "jour")
    if q == "nuit":                                        # des étoiles en pixels dans le ciel (la moitié du haut)
        for i in range(70):
            fx, fy = _h(i, 1), _h(i, 2) * 0.42
            px, py = R.p(fx, fy)
            a = int(140 + 115 * (0.5 + 0.5 * math.sin(t_ * (1.3 + _h(i, 3)) + i)))
            s_ = 2 if _h(i, 4) < 0.7 else 3
            L.append(("rect", px, py, s_, s_, (230, 235, 255, a)))
    sa = rv.get("saison")
    if sa == "hiver":                                      # des flocons qui tombent doucement
        for i in range(60):
            fx = (_h(i, 5) + 0.02 * math.sin(t_ * 0.7 + i)) % 1
            fy = (_h(i, 6) + t_ * (0.025 + 0.02 * _h(i, 7))) % 1
            px, py = R.p(fx, fy)
            L.append(("rect", px, py, 3, 3, (240, 245, 255, 210)))
    elif sa == "printemps":                                # quelques pétales roses
        for i in range(26):
            fx = (_h(i, 8) + t_ * 0.012) % 1
            fy = (_h(i, 9) + t_ * (0.018 + 0.01 * _h(i, 10))) % 1
            px, py = R.p(fx, fy)
            L.append(("rect", px, py, 3, 3, (255, 170, 210, 200)))
    elif sa == "automne":
        for i in range(22):
            fx = (_h(i, 11) - t_ * 0.01) % 1
            fy = (_h(i, 12) + t_ * (0.02 + 0.01 * _h(i, 13))) % 1
            px, py = R.p(fx, fy)
            L.append(("rect", px, py, 3, 3, (255, 150, 60, 200)))
    me = rv.get("meteo", "calme")
    if me == "pluie":                                      # la pluie de pixels verts danse
        for i in range(90):
            fx = _h(i, 20)
            fy = (_h(i, 21) + t_ * (0.25 + 0.2 * _h(i, 22))) % 1.1 - 0.1
            px, py = R.p(fx, fy)
            for j in range(4):
                L.append(("rect", px, py + j * 5, 3, 3, (170, 255, 200, 60 + 45 * j)))
    elif me == "eclairs":                                  # des éclairs joyeux autour de la Tour des Ondes
        ox, oy = rv["lieux_pos"].get("ondes", (0.79, 0.09))
        for k in range(2):
            if (t_ * 1.7 + k * 0.5) % 1.6 < 0.35:
                pts = [(ox - 0.03 + 0.06 * k, 0.0)]
                for j in range(1, 6):
                    pts.append((pts[-1][0] + (0.012 if j % 2 else -0.016), j * 0.045))
                for (a1, b1), (a2, b2) in zip(pts, pts[1:]):
                    p1, p2 = R.p(a1, b1), R.p(a2, b2)
                    L.append(("ligne", p1[0], p1[1], p2[0], p2[1], (190, 220, 255, 200), 4, None))
                    L.append(("ligne", p1[0], p1[1], p2[0], p2[1], (255, 255, 255, 255), 1.6, None))
        L.append(("lueur", *R.p(ox, oy), 60 * R.r, (150, 200, 255, 60)))
    elif me == "arc":                                      # un arc-en-ciel au-dessus du Carrefour
        cx, cy = R.p(*rv["lieux_pos"].get("carrefour", (0.5, 0.49)))
        for i, c in enumerate(((255, 95, 109), (255, 159, 67), (255, 213, 79), (61, 220, 132), (95, 175, 255),
                               (178, 132, 255))):
            rr = (200 - i * 7) * R.r
            for a in range(180, 361, 4):
                px = cx + rr * math.cos(math.radians(a))
                py = cy + rr * math.sin(math.radians(a)) * 0.8
                L.append(("rect", px - 2, py - 2, 4, 4, c + (140,)))
    elif me == "brume":                                    # la brume douce : le monde se repose (pas triste)
        for i in range(9):
            fx = (_h(i, 30) + t_ * 0.008) % 1.2 - 0.1
            fy = 0.55 + 0.4 * _h(i, 31)
            px, py = R.p(fx, fy)
            L.append(("ellipse", px, py, 130 * R.r, 26 * R.r, (215, 222, 235, 34)))


# ---------------------------------------------------------------- les chemins (idée 39)
def chemins(L, rv, R, t_):
    an = rv.get("anim") or {}
    for l, pts, et in rv["chemins"]:
        ps = [R.p(a, b) for a, b in pts]
        if an.get("type") == "chemin" and an.get("lieu") == l:
            continue
        if et == "allume":
            for (a, b), (c, d) in zip(ps, ps[1:]):
                L.append(("ligne", a, b, c, d, (61, 220, 132, 150), 2.4, None))
            lg = sum(math.hypot(c - a, d - b) for (a, b), (c, d) in zip(ps, ps[1:]))
            for k in range(3):                             # des pixels de données qui circulent
                pos = ((t_ * 40 + k * lg / 3) % max(1, lg))
                for (a, b), (c, d) in zip(ps, ps[1:]):
                    s_ = math.hypot(c - a, d - b)
                    if pos <= s_:
                        f = pos / max(1, s_)
                        L.append(("rect", a + (c - a) * f - 2, b + (d - b) * f - 2, 4, 4, (200, 255, 220, 255)))
                        break
                    pos -= s_
        elif et == "ouvert":
            for (a, b), (c, d) in zip(ps, ps[1:]):
                L.append(("ligne", a, b, c, d, (255, 213, 79, 170), 2, (6, 6, 0)))
        else:
            for i, (a, b) in enumerate(ps[1:-1] if len(ps) > 2 else ps):
                L.append(("rect", a - 1.5, b - 1.5, 3, 3, (150, 156, 170, 120)))


# ---------------------------------------------------------------- l'événement rare du jour (idée 38)
def evenement(L, rv, R, t_):
    ev = rv.get("evt")
    if not ev:
        return
    _eid, e = ev
    W, H = rv["taille"]
    cx, cy = R.p(e["x"] / W, e["y"] / H)
    c = tuple(e.get("couleur", (61, 220, 132)))
    k = e["effet"]
    if k == "aurore":
        for j, (coul, dy) in enumerate((((61, 220, 132), 0), ((77, 208, 225), 10), ((178, 132, 255), 22))):
            for i in range(0, 46):
                px = cx - 120 * R.r + i * 5.2 * R.r
                py = cy - 40 * R.r + dy * R.r + 12 * R.r * math.sin(i / 5 + j + t_ * 0.8)
                hh = (50 + 20 * math.sin(i / 3 + j + t_)) * R.r
                env = math.sin(math.pi * i / 46)
                L.append(("rect", px, py, 4 * R.r, hh, coul + (int(70 * env),)))
    elif k == "trainee":
        x2, y2 = R.p(e["x2"] / W, e["y2"] / H)
        f = (t_ * 0.35) % 1.0
        hx, hy = cx + (x2 - cx) * f, cy + (y2 - cy) * f
        for i in range(18):
            g = i / 18
            px, py = hx - (x2 - cx) * 0.25 * g, hy - (y2 - cy) * 0.25 * g
            q = (6 - 5 * g) * R.r
            L.append(("rect", px - q / 2, py - q / 2, q, q, c + (int(255 * (1 - g)),)))
        L.append(("lueur", hx, hy, 26 * R.r, c + (160,)))
    elif k == "baleine":
        bx = cx + 40 * R.r * math.sin(t_ * 0.4)
        by = cy + 5 * R.r * math.sin(t_ * 1.3)
        motif = ["..XXXXX....", ".XXXXXXXX.X", "XXOXXXXXXXX", "XXXXXXXXX.X", ".XXXXXXX..."]
        q = 4 * R.r
        for j, ligne in enumerate(motif):
            for i, ch in enumerate(ligne):
                if ch != ".":
                    L.append(("rect", bx + (i - 5) * q, by + (j - 2) * q, q, q,
                              (20, 30, 60, 255) if ch == "O" else (95, 175, 255, 235)))
        if (t_ % 3) < 1.2:                                 # elle souffle des pixels
            for i in range(6):
                L.append(("rect", bx - 2 * q + (i % 3 - 1) * q, by - (4 + i // 3 + (t_ % 1.2) * 3) * q, q * 0.8,
                          q * 0.8, (200, 240, 255, 200)))
    elif k == "ballon":
        bx = cx + 30 * R.r * math.sin(t_ * 0.3)
        by = cy - 10 * R.r * math.sin(t_ * 0.5)
        L.append(("ellipse", bx, by, 16 * R.r, 19 * R.r, c + (240,)))
        L.append(("ellipse", bx - 5 * R.r, by - 6 * R.r, 4 * R.r, 5 * R.r, (255, 245, 200, 200)))
        L.append(("rect", bx - 5 * R.r, by + 24 * R.r, 10 * R.r, 7 * R.r, (160, 110, 60, 255)))
        L.append(("ligne", bx - 10 * R.r, by + 12 * R.r, bx - 5 * R.r, by + 24 * R.r, (90, 70, 50, 255), 1, None))
        L.append(("ligne", bx + 10 * R.r, by + 12 * R.r, bx + 5 * R.r, by + 24 * R.r, (90, 70, 50, 255), 1, None))
    else:                                                  # des particules : monte, descend, flotte, scintille
        for i in range(30):
            if k == "monte":
                dx, dy = (_h(i, 40) - 0.5) * 90, -((_h(i, 41) * 80 + t_ * 30) % 80)
            elif k == "descend":
                dx, dy = (_h(i, 40) - 0.5) * 140 + 8 * math.sin(t_ + i), (_h(i, 41) * 90 + t_ * 18) % 90 - 30
            elif k == "scintille":
                dx, dy = (_h(i, 40) - 0.5) * 120, (_h(i, 41) - 0.5) * 70
            else:
                dx = (_h(i, 40) - 0.5) * 120 + 10 * math.sin(t_ * 0.8 + i)
                dy = (_h(i, 41) - 0.5) * 70 + 8 * math.cos(t_ * 0.6 + i * 1.7)
            a = int(120 + 135 * (0.5 + 0.5 * math.sin(t_ * 3 + i)))
            q = 3 * R.r if k != "scintille" or (t_ * 2 + i) % 2 > 1 else 5 * R.r
            L.append(("rect", cx + dx * R.r, cy + dy * R.r, q, q, c + (a,)))
        L.append(("lueur", cx, cy, 50 * R.r, c + (40,)))


# ---------------------------------------------------------------- les lieux secrets trouvés (idée 33)
def secrets(L, rv, R, t_):
    W, H = rv["taille"]
    for _qid, sx, sy in rv["secrets"][0]:
        px, py = R.p(sx / W, sy / H)
        for i in range(5):
            a = t_ * 1.5 + i * 1.256
            L.append(("rect", px + 9 * math.cos(a) - 1.5, py + 9 * math.sin(a) - 1.5, 3, 3, (61, 220, 132, 200)))
        L.append(("texte", px, py, "★", 13, JAUNE, True, "c", False))


# ---------------------------------------------------------------- les lieux (idée 32)
def lieux(L, Z, rv, R, t_, m):
    for x in rv["lieux"]:
        px, py = R.p(x["x"], x["y"])
        if not R.dedans(px, py, 4):
            continue
        c = COUL_ETAT[x["etat"]]
        if x["id"] == rv.get("ici_lieu"):
            pul = 0.5 + 0.5 * math.sin(t_ * 3)
            L.append(("lueur", px, py, 34 + 8 * pul, (255, 213, 79, 70)))
            L.append(("cercle", px, py, 18 + 3 * pul, JAUNE, 1.6))
        if x["etat"] == "ouvert":
            L.append(("lueur", px, py, 18, (255, 213, 79, int(50 + 30 * math.sin(t_ * 2.2)))))
        L.append(("ellipse", px, py, 7, 7, (10, 12, 18, 230)))
        L.append(("ellipse", px, py, 5, 5, c))
        nom = x["nom"] if x["etat"] != "ferme" else "?"
        txt = ("✓ " if x["etat"] == "allume" and x["id"] not in ("camp", "carrefour") else "") + nom + (" ★" if x["etoile"] else "")
        tw = S.lt(txt, 11) + 14
        ty = py - 17
        L.append(("rrect", px - tw / 2, ty - 10, tw, 20, 10, (10, 12, 18, 205),
                  S._a(c, 150) if x["id"] == rv.get("survol") else S.BORD_FORT, 1))
        L.append(("texte", px, ty, txt, 11, VERT if x["etat"] == "allume" else TEXTE if x["etat"] == "ouvert" else DOUX,
                  False, "c", False))
        Z.append((px - max(tw / 2, 14), ty - 10, max(tw, 28), 36, "rv:lieu:" + x["id"]))
    p = rv.get("ici_piece")                              # « tu es ici » dans une pièce de la maison (un chapitre)
    if p:
        px, py = R.p(*p)
        pul = 0.5 + 0.5 * math.sin(t_ * 3)
        L.append(("lueur", px, py, 36 + 8 * pul, (255, 213, 79, 70)))
        L.append(("cercle", px, py, 20 + 3 * pul, JAUNE, 1.6))
        L.append(("ellipse", px, py, 6, 6, JAUNE))
        info = t("esp.tu_es_ici", lieu=m.get("ici_nom", ""))
        bw = S.lt(info, 12) + 30
        x0, y0, w0, h0 = R.zone
        bx = min(max(x0 + 8, px - bw / 2), x0 + w0 - bw - 8)
        by = min(py + 26, y0 + h0 - 30)
        L.append(("rrect", bx, by, bw, 24, 9, (10, 12, 18, 230), S._a(JAUNE, 120), 1))
        L.append(("texte", bx + 15, by + 12, info, 12, TEXTE, True, "g", False))
    if rv.get("en_cours"):
        nom, (fx, fy) = rv["en_cours"]
        px, py = R.p(fx, fy)
        txt = "▶ " + nom
        tw = S.lt(txt, 11.5) + 16
        L.append(("rrect", px - tw / 2, py - 11, tw, 22, 11, (10, 12, 18, 215), S._a(VERT, 120), 1))
        L.append(("texte", px, py, txt, 11.5, VERT, False, "c", False))


# ---------------------------------------------------------------- les habitants (idée 35)
def habitants(L, Z, rv, R, t_):
    W, H = rv["taille"]
    for hb in rv["habitants"]:
        px, py = R.p(hb["x"] / W, hb["y"] / H)
        if not R.dedans(px, py, 10):
            continue
        rr = 15
        L.append(("ellipse", px, py, rr, rr, (12, 15, 24, 235)))
        L.append(("cercle", px, py, rr, JAUNE if hb["besoin"] else S._a(VERT, 160), 1.6))
        if hb.get("album"):
            S.creature_img(L, hb["album"], "assis", 0, px, py + rr - 3, 24)
        if hb["besoin"]:
            b = 3 * math.sin(t_ * 4)
            L.append(("ellipse", px + rr - 2, py - rr + 1 + b, 7, 7, JAUNE))
            L.append(("texte", px + rr - 2, py - rr + 1 + b, "!", 11, (20, 16, 0, 255), True, "c", False))
        Z.append((px - rr, py - rr, 2 * rr, 2 * rr, "rv:hab:" + hb["id"]))


# ---------------------------------------------------------------- les animations du réveil (idées 31 et 39)
def animation(L, an, R, t_):
    p = an["p"]
    x, y, w, h = R.zone
    if an["type"] in ("biome", "resume"):
        cx, cy = R.p(*an["c"])
        rmax = math.hypot(max(cx - x, x + w - cx), max(cy - y, y + h - cy))
        rr = rmax * min(1.0, p * 1.15)
        for i in range(40):                                # des pixels verts scintillent sur le front de la vague
            a = i * 0.157 + t_
            px, py = cx + rr * math.cos(a), cy + rr * math.sin(a)
            if R.dedans(px, py):
                L.append(("rect", px - 2, py - 2, 4, 4, (120, 255, 170, int(220 * (1 - p)))))
    elif an["type"] == "lieu":
        cx, cy = R.p(*an["c"])
        L.append(("lueur", cx, cy, 70 * R.r * (0.6 + p), (255, 230, 150, int(200 * (1 - p)))))
    elif an["type"] == "chemin":
        ps = [R.p(a, b) for a, b in an["pts"]]
        lg = sum(math.hypot(c - a, d - b) for (a, b), (c, d) in zip(ps, ps[1:]))
        reste = lg * min(1.0, p * 1.1)
        for (a, b), (c, d) in zip(ps, ps[1:]):           # la route se dessine pixel par pixel depuis le Carrefour
            s_ = math.hypot(c - a, d - b)
            f = min(1.0, reste / max(1, s_))
            n = int(s_ * f / 6)
            for k in range(n):
                g = k * 6 / max(1, s_)
                L.append(("rect", a + (c - a) * g - 2, b + (d - b) * g - 2, 4, 4, (61, 220, 132, 230)))
            reste -= s_
            if reste <= 0:
                break
    # la phrase, en bas de la carte
    txt = an.get("texte", "")
    if txt:
        tw = min(w - 24, S.lt(txt, 15) + 40)
        bx, by = x + (w - tw) / 2, y + h - 64
        L.append(("rrect", bx, by, tw, 46, 12, (10, 12, 18, 225), S._a(VERT, 150), 1.4))
        L.append(("texte", x + w / 2, by + 16, S.court(txt, tw - 24, 15), 15, TEXTE, True, "c", False))
        L.append(("texte", x + w / 2, by + 34, an.get("sous") or t("reveil.anim.passer"), 11, DOUX, False, "c", False))


# ---------------------------------------------------------------- bulle, fiche, livre, carnet
def _lieu(rv, lid):
    return next((x for x in rv["lieux"] if x["id"] == lid), None)


def _etat_txt(x):
    e = t("reveil.etat." + x["etat"])
    if x["paliers"] and x["etat"] != "ferme":
        e += " · " + t("reveil.palier", i=x["palier"], n=x["paliers"])
    return e


def bulle(L, rv, R):
    x = _lieu(rv, rv["survol"])
    if not x:
        return
    px, py = R.p(x["x"], x["y"])
    l1 = (x["titre"] if x["etat"] != "ferme" else "?") + " · " + _etat_txt(x)
    l2 = t("reveil.fiche.biome", biome=t("reveil.biome." + x["biome"]))
    l3 = t("reveil.survol") if x["cmd"] else (t("reveil.fiche.ferme", manque=x["manque"]) if x["manque"] else "")
    bw = max(S.lt(l1, 13), S.lt(l2, 11), S.lt(l3, 11)) + 28
    x0, y0, w0, h0 = R.zone
    bx = min(max(x0 + 6, px + 14), x0 + w0 - bw - 6)
    by = min(max(y0 + 6, py + 12), y0 + h0 - 80)
    L.append(("rrect", bx, by, bw, 72, 10, (10, 12, 18, 238), S._a(COUL_ETAT[x["etat"]], 140), 1))
    L.append(("texte", bx + 14, by + 18, l1, 13, TEXTE, True, "g", False))
    L.append(("texte", bx + 14, by + 38, l2, 11, DOUX, False, "g", False))
    L.append(("texte", bx + 14, by + 56, l3, 11, CYAN if x["cmd"] else DOUX, False, "g", False))


def _panneau(L, Z, zone, hauteur):
    x, y, w, h = zone
    hh = min(h - 16, hauteur)
    bx, by, bw = x + 10, y + h - hh - 8, w - 20
    L.append(("rrect", bx, by, bw, hh, 12, (12, 14, 21, 245), S._a(CYAN, 120), 1.2))
    L.append(("texte", bx + bw - 18, by + 16, "✕", 14, DOUX, True, "c", False))
    Z.append((bx, by, bw, hh, "rv:rien"))
    Z.append((bx + bw - 34, by, 34, 32, "rv:fermer"))
    return bx, by, bw, hh


def fiche(L, Z, rv, zone):
    f = rv["fiche"]
    if f.startswith("hab:"):
        return fiche_habitant(L, Z, rv, zone, f[4:])
    x = _lieu(rv, f)
    if not x:
        return
    bx, by, bw, hh = _panneau(L, Z, zone, 196)
    c = COUL_ETAT[x["etat"]]
    L.append(("texte", bx + 16, by + 22, x["titre"] if x["etat"] != "ferme" else "?", 16, TEXTE, True, "g", False))
    S.chip(L, bx + 16, by + 50, _etat_txt(x), c, 11)
    L.append(("texte", bx + 16, by + 76, t("reveil.fiche.biome", biome=t("reveil.biome." + x["biome"])), 11.5, DOUX,
              False, "g", False))
    yy = by + 98
    texte = x["debut"] if x["etat"] != "ferme" else t("reveil.fiche.ferme", manque=x["manque"] or "…")
    for ligne in S.couper(S.sans_marques(texte), bw - 32, 12)[:3]:
        L.append(("texte", bx + 16, yy, ligne, 12, TEXTE, False, "g", False))
        yy += 17
    bits = []
    if x["habitants"]:
        bits.append(t("reveil.fiche.habitants", n=x["habitants"]))
    if x["secrets"][1]:
        bits.append(t("reveil.fiche.secrets", n=x["secrets"][0], total=x["secrets"][1]))
    if bits:
        L.append(("texte", bx + 16, yy + 2, "  ·  ".join(bits), 11.5, JAUNE, False, "g", False))
    if x["cmd"]:
        L.append(("rrect", bx + 16, by + hh - 40, 150, 30, 9, S._a(VERT, 50), VERT, 1.4))
        L.append(("texte", bx + 91, by + hh - 25, t("reveil.aller"), 13, VERT, True, "c", False))
        Z.append((bx + 16, by + hh - 40, 150, 30, "rv:aller:" + x["id"]))
        L.append(("texte", bx + 180, by + hh - 25, x["cmd"], 12, DOUX, False, "g", True))
    if x["id"] == "temps":
        L.append(("rrect", bx + bw - 200, by + hh - 40, 184, 30, 9, (14, 16, 24, 255), S.BORD_FORT, 1))
        L.append(("texte", bx + bw - 108, by + hh - 25, t("reveil.livre.bouton"), 12, TEXTE, False, "c", False))
        Z.append((bx + bw - 200, by + hh - 40, 184, 30, "rv:livre"))


def fiche_habitant(L, Z, rv, zone, qid):
    hb = next((h for h in rv["habitants"] if h["id"] == qid), None)
    if not hb:
        return
    bx, by, bw, hh = _panneau(L, Z, zone, 200)
    if hb.get("album"):
        L.append(("ellipse", bx + 44, by + 46, 28, 28, (20, 24, 36, 255)))
        S.creature_img(L, hb["album"], "assis", 0, bx + 44, by + 70, 44)
    L.append(("texte", bx + 84, by + 24, hb["nom"], 15, TEXTE, True, "g", False))
    S.chip(L, bx + 84, by + 50, t("reveil.hab.besoin") if hb["besoin"] else t("reveil.hab.merci", nom=hb["nom"]),
           JAUNE if hb["besoin"] else VERT, 11)
    yy = by + 86
    for ligne in S.couper(S.sans_marques(hb["texte"]), bw - 32, 12)[:4]:
        L.append(("texte", bx + 16, yy, ligne, 12, TEXTE, False, "g", False))
        yy += 17
    if hb["besoin"]:
        L.append(("texte", bx + 16, by + hh - 34, (t("reveil.hab.en_cours") if hb["active"] else
                                                   t("reveil.hab.lire", fichier=hb["fichier"])), 11.5, CYAN, False, "g", False))
        L.append(("texte", bx + 16, by + hh - 16, t("reveil.hab.recompense", xp=hb["xp"]) + " · " + t("reveil.hab.attend"),
                  10.5, DOUX, False, "g", False))


def livre(L, Z, rv, zone):
    bx, by, bw, hh = _panneau(L, Z, zone, 260)
    lv = rv["livre_donnees"]
    L.append(("texte", bx + 16, by + 20, "📖 " + t("reveil.livre.titre") + " · " + t("reveil.livre.compte", n=len(lv["ouverts"]),
              total=len(lv["gardiens"])), 13, TEXTE, True, "g", False))
    n = rv.get("livre_page")
    if n and n in lv["ouverts"]:
        L.append(("texte", bx + 16, by + 46, t("reveil.livre.chapitre", n=n, total=len(lv["gardiens"])) + " · "
                  + t(f"reveil.gardien.{n}.titre"), 13, JAUNE, True, "g", False))
        yy = by + 70
        for ligne in S.couper(t(f"reveil.gardien.{n}.texte"), bw - 32, 12)[:8]:
            L.append(("texte", bx + 16, yy, ligne, 12, TEXTE, False, "g", False))
            yy += 17
        if lv.get("fichier"):
            L.append(("texte", bx + 16, by + hh - 18, t("reveil.livre.lire", chemin=lv["fichier"](n)), 11, CYAN, False, "g", True))
        L.append(("texte", bx + bw - 60, by + hh - 18, "◀", 13, DOUX, True, "c", False))
        Z.append((bx + bw - 80, by + hh - 34, 40, 30, "rv:livre:0"))
        return
    cw = (bw - 32) / 4
    for i, (boite, esp) in enumerate(lv["gardiens"]):
        k = i + 1
        cx_, cy_ = bx + 16 + (i % 4) * cw, by + 44 + (i // 4) * 92
        ouvert = k in lv["ouverts"]
        L.append(("rrect", cx_, cy_, cw - 10, 82, 10, (18, 21, 30, 255), S._a(JAUNE, 120) if ouvert else S.BORD, 1))
        al = lv["albums"].get(esp)
        if ouvert and al:
            S.creature_img(L, al, "assis", 0, cx_ + 30, cy_ + 64, 46)
        else:
            L.append(("ellipse", cx_ + 30, cy_ + 42, 18, 22, (40, 44, 56, 255)))
            L.append(("texte", cx_ + 30, cy_ + 42, "?", 16, PALE, True, "c", False))
        L.append(("texte", cx_ + 58, cy_ + 30, t("reveil.livre.ch", n=k), 11, TEXTE if ouvert else PALE, True, "g", False))
        if ouvert:
            L.append(("texte", cx_ + 58, cy_ + 50, S.court(t(f"reveil.gardien.{k}.court"), cw - 72, 10.5), 10.5, DOUX, False, "g", False))
            Z.append((cx_, cy_, cw - 10, 82, f"rv:livre:{k}"))
    L.append(("texte", bx + 16, by + hh - 18, t("reveil.livre.silhouette"), 11, DOUX, False, "g", False))


def carnet(L, Z, rv, zone):
    bx, by, bw, hh = _panneau(L, Z, zone, 240)
    evs, vus = rv["carnet_donnees"]
    L.append(("texte", bx + 16, by + 20, t("reveil.evt.carnet", n=len(vus), total=len(evs)), 13, TEXTE, True, "g", False))
    cw = (bw - 32) / 4
    for i, e in enumerate(evs):
        cx_, cy_ = bx + 16 + (i % 4) * cw, by + 40 + (i // 4) * 56
        vu = e["id"] in vus
        L.append(("rrect", cx_, cy_, cw - 8, 48, 9, (18, 21, 30, 255), S._a(VERT, 120) if vu else S.BORD, 1))
        L.append(("texte", cx_ + 10, cy_ + 16, S.court(("★ " + t("reveil.evt." + e["id"])) if vu else "?", cw - 26, 11.5),
                  11.5, TEXTE if vu else PALE, True, "g", False))
        L.append(("texte", cx_ + 10, cy_ + 34, t("reveil.fiche.biome", biome=t("reveil.biome." + e["biome"])), 10.5, DOUX,
                  False, "g", False))
    L.append(("texte", bx + 16, by + hh - 16, t("reveil.evt.jamais_rate"), 11, DOUX, False, "g", False))


def legende(L, Z, rv, pied):
    px_, py_, pw_ = pied
    xx = px_ + 16
    for et in ("allume", "ouvert", "ferme"):
        L.append(("ellipse", xx + 4, py_, 4, 4, COUL_ETAT[et]))
        L.append(("texte", xx + 12, py_, t("reveil.etat." + et), 11.5, DOUX, False, "g", False))
        xx += S.lt(t("reveil.etat." + et), 11.5) + 28
    (_tr, (n, tot)) = rv["secrets"]
    for txt, a in (("★ " + t("reveil.secrets.court", n=n, total=tot), None),
                   ("📖 " + t("reveil.livre.court", n=len(rv["livre_donnees"]["ouverts"]), total=8), "rv:livre"),
                   ("✦ " + t("reveil.evt.court", n=len(rv["carnet_donnees"][1]), total=len(rv["carnet_donnees"][0])), "rv:carnet")):
        w = S.lt(txt, 11.5) + 6                       # (+6 : l'emoji, souvent plus large que mesuré)
        if xx + w > px_ + pw_ - 16:
            break
        L.append(("texte", xx, py_, txt, 11.5, JAUNE if a is None else CYAN, False, "g", False))
        if a:
            Z.append((xx - 4, py_ - 11, w + 8, 22, a))
        xx += w + 18
    aide = t("reveil.survol.court")
    if xx + S.lt(aide, 11.5) + 8 <= px_ + pw_ - 16:     # l'aide seulement s'il reste la place (jamais par-dessus)
        L.append(("texte", px_ + pw_ - 16, py_, aide, 11.5, DOUX, False, "d", False))
