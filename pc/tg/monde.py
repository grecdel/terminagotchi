"""Le monde des biomes dans l'espace de travail (`tg espace`, onglet « Monde », commande `monde` pour l'ouvrir en grand).

Le VRAI terrain de l'enfant (biome/<type>/parcelle_<n>/, lecture seule) dessiné en relief sur des hexagones
(monde_gen.py : la génération commune ; monde_dessin.py : les pixels), avec l'équipe qui s'y promène. À droite, la
liste « Mes créatures » ; un clic sur une créature affiche sa fiche À LA PLACE de la liste (« ← Mes créatures ») ; un
clic à côté ou Échap la referme. Les commandes se voient dans le monde (effets.py : ce qui a VRAIMENT changé) :
1 à 2 secondes, jamais bloquant, réglage « effets : tous / essentiels / aucun » ; l'explication est dite par la
créature dans sa bulle, seulement les 3 premières fois.

Tout passe par une liste de dessin (comme espace_scene) : la fenêtre GTK la peint avec cairo, les captures avec PIL.
Le monde est dessiné dans un « calque » (une zone découpée), à 20 images par seconde ; chaque hexagone est une petite
image calculée une seule fois. La mascotte du site n'apparaît jamais ; les créatures n'ont aucun accessoire ; l'effet
glitch des créatures s'affiche comme partout (poses.album_espece).
"""
import json
import math
import os
import random

from . import monde_dessin as MD
from . import monde_gen as G
from .langue import t

HR, HZ, HH = G.HR, G.HZ, G.HH
STADES_H = {"bebe": 30, "enfant": 36, "ado": 42, "adulte": 50, "ancien": 52, "finale": 52}
COUL_TYPE = {"feu": "#e8562a", "eau": "#2f7fc4", "glace": "#9fd8f2", "plante": "#5aa63a", "roche": "#c9a26a",
             "ciel": "#dfe9ff", "ombre": "#4b3a6b", "machine": "#8a96a3", "poison": "#6a8f2a"}
EMOJI = {"feu": "🔥", "eau": "💧", "glace": "🧊", "plante": "🌿", "roche": "🗻", "ciel": "⚡", "ombre": "🌙",
         "machine": "🔩", "poison": "🧪"}
RARETE = {"peu commune": (74, 222, 128), "rare": (56, 189, 248), "épique": (192, 132, 252),
          "légendaire": (251, 191, 36), "mythique": (255, 121, 198)}
JAUNE, VERT, ROUGE, VIOLET, CYAN = (255, 213, 79, 255), (61, 220, 132, 255), (255, 95, 109, 255), \
    (178, 132, 255, 255), (77, 208, 225, 255)
TEXTE, DOUX, PANNEAU = (233, 236, 242, 255), (138, 147, 166, 255), (15, 17, 24, 255)
DUREE = 1.8               # un effet dure de 1 à 2 secondes
BUDGET_SPRITES = 12       # dessins de prismes calculés au plus par image (la fenêtre ne gèle jamais)


def rgb(c, a=255):
    r, g, b = MD.hexa(c) if isinstance(c, str) else c[:3]
    return (r, g, b, a)


def ease(p):
    return 2 * p * p if p < .5 else 1 - (-2 * p + 2) ** 2 / 2


def ease_back(p):
    c = 1.7
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def clamp(v, a, b):
    return max(a, min(b, v))


class Crea:
    """Une créature de l'équipe dans le monde (sa marche suit le prototype : petits pas d'hexagone en hexagone)."""

    def __init__(self, info):
        self.info = info
        self.at = None            # clé de l'hexagone
        self.seg = None           # (a, b, t) un pas en cours
        self.chemin = []
        self.etat = "idle"
        self.jusqu = 0.0
        self.face = 1
        self.ph = random.random() * 6
        self.vol = None           # (x0, y0, t0, durée) : l'arrivée en vol
        self.pop = 0.0
        self.dit = None           # (texte, fin)


class Vue:
    def __init__(self):
        self.carte = None
        self.signature = None
        self.terrain = {}
        self.equipe = []
        self.maison, self.refuge = {}, []
        self.creas = {}
        self.cam = [0.0, 0.0, 2.0]
        self.but = None
        self.manuel = False
        self.retour = None        # la caméra d'avant un effet (« la caméra va voir, puis revient »)
        self.iso = None
        self.sel = None
        self.liste_ouverte = True
        self.effets = []
        self.parts = []
        self.morph = {}
        self.fantomes = []
        self.cwd = None
        self.t = 0.0
        self.aire = None          # (x, y, w, h) de la vue du monde (coordonnées logiques)
        self.ordre = []
        self.bulle = None
        self.niveau = "tous"
        self.lu = 0.0
        self.mesure = []          # durées de dessin (performance)
        self.a_cadrer = False

    # ------------------------------------------------ lire le jeu
    def relire(self, racine, equipe, cwd=None, forcer=False):
        """Relit le vrai terrain et l'équipe (au plus toutes les 2 s, ou tout de suite après une commande)."""
        if not forcer and self.t - self.lu < 2.0 and self.carte is not None:
            self.cwd = cwd
            return False
        self.lu = self.t
        self.cwd = cwd
        try:
            terrain = G.lire_terrain(racine)
        except OSError:
            terrain = {}
        terr = {k: [{"nom": p["nom"], "objets": p["objets"], "plus": p["plus"], "caches": p["caches"]} for p in v]
                for k, v in terrain.items()}
        sig = json.dumps([terr, [(e["id"], e["type"]) for e in equipe]], sort_keys=True)
        self.equipe = equipe
        if sig == self.signature:
            for e in equipe:
                if e["id"] in self.creas:
                    self.creas[e["id"]].info = e
            return False
        self.signature = sig
        self._reconstruire(terr)
        return True

    def _reconstruire(self, terrain):
        vieille = self.carte
        anciens = {}
        if vieille:
            for h in vieille["hex"].values():
                anciens[h["cle"]] = self.sommet(h)
        self.terrain = terrain
        self.carte = G.construire(terrain)
        c = self.carte
        self.par_cle = {h["cle"]: h for h in c["hex"].values()}
        self.ordre = sorted(c["hex"].values(), key=lambda h: (G.sol_xy(h["q"], h["r"])[1], h["q"]))
        self.bords = {p["id"]: self._bords(p) for p in c["parcelles"]}
        # le relief bouge doucement d'une place à l'autre quand le monde se réorganise
        for h in c["hex"].values():
            o = anciens.get(h["cle"])
            if o:
                n = self.sommet(h)
                if abs(o[0] - n[0]) > .5 or abs(o[1] - n[1]) > .5:
                    self.morph[h["cle"]] = (o, self.t)
        # ce qui a disparu s'écroule (fantômes)
        if vieille:
            for h in vieille["hex"].values():
                if h["cle"] not in self.par_cle:
                    x, y = anciens[h["cle"]]
                    self.fantomes.append({"h": dict(h), "x": x, "y": y, "t0": self.t + h["d"] * .07})
        crs = [(e["id"], e["type"]) for e in self.equipe]
        avant = dict(self.maison)
        self.maison, self.refuge = G.place_creatures(c, crs)
        for e in self.equipe:
            cr = self.creas.get(e["id"]) or Crea(e)
            cr.info = e
            self.creas[e["id"]] = cr
            if e["id"] in self.maison:
                if avant.get(e["id"]) != self.maison[e["id"]] or cr.at not in self.par_cle:
                    self._poser(cr, arrivee=bool(vieille))
            else:
                cr.at = None
        for k in list(self.creas):
            if k not in {e["id"] for e in self.equipe}:
                del self.creas[k]
        if not vieille:
            self.a_cadrer = True
            self.tout_voir(doux=False)

    def _bords(self, p):
        """Les côtés extérieurs d'une parcelle : [(clé hexagone, k1, k2)] (pour la dessiner en pointillés)."""
        out = []
        c = self.carte
        for o in G.FLOWER:
            h = c["hex"][(p["centre"][0] + o[0], p["centre"][1] + o[1])]
            for i, (a, b) in enumerate(G.DIRS):
                n = c["hex"].get((h["q"] + a, h["r"] + b))
                if n and n["parcelle"] == p["id"]:
                    continue
                out.append((h["cle"], *G.DIR_EDGE[i]))
        return out

    # ------------------------------------------------ positions
    def sommet(self, h):
        """Le haut de l'hexagone (coordonnées du monde), en tenant compte d'un relief qui glisse."""
        x, y = G.sol_xy(h["q"], h["r"])
        y -= h["h"] * HZ
        m = self.morph.get(h["cle"]) if hasattr(self, "morph") else None
        if m:
            k = clamp((self.t - m[1]) / .8, 0, 1)
            if k >= 1:
                del self.morph[h["cle"]]
            else:
                e = ease(k)
                x, y = m[0][0] + (x - m[0][0]) * e, m[0][1] + (y - m[0][1]) * e
        return x, y

    def hex_de(self, chemin):
        """L'hexagone d'un chemin du terrain (objet, parcelle ou région), ou None."""
        c = self.carte
        if not c or not chemin:
            return None
        p = chemin.split("/")
        if len(p) < 2 or p[0] != "biome":
            return None
        if len(p) == 2:
            ps = [x for x in c["parcelles"] if x["type"] == p[1]]
            return c["hex"][tuple(ps[0]["centre"])] if ps else None
        par = c["par"].get(p[1] + "/" + p[2])
        if not par:
            return None
        if len(p) >= 4 and p[3] in par["poses"]:
            o = par["poses"][p[3]]["off"]
            return c["hex"][(par["centre"][0] + o[0], par["centre"][1] + o[1])]
        return c["hex"][tuple(par["centre"])]

    def point_de(self, chemin):
        """Un point du monde pour un chemin du terrain : l'objet, sa parcelle, sa région, sinon le milieu."""
        h = self.hex_de(chemin)
        if h:
            return self.sommet(h)
        if chemin:
            for x in self.fantomes:
                if x["h"]["parcelle"] and chemin.startswith("biome/" + x["h"]["parcelle"]):
                    return x["x"], x["y"]
        return self.milieu()

    def milieu(self):
        if not self.carte or not self.carte["hex"]:
            return 0.0, 0.0
        xs = [G.sol_xy(h["q"], h["r"]) for h in self.carte["hex"].values()]
        return sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs) - 20

    def bornes(self, hs):
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for h in hs:
            x, y = G.sol_xy(h["q"], h["r"])
            x0, x1 = min(x0, x - HR), max(x1, x + HR)
            y0 = min(y0, y - h["h"] * HZ - HH - (30 if h["scen"] or h["kind"] == "fleche" else 0))
            y1 = max(y1, y - h["base"] * HZ + HH + h["pilier"])
        return x0, y0 - 20, x1, y1

    def ajuster(self, hs, doux=True, zmax=None):
        if not hs or not self.aire:
            return
        x0, y0, x1, y1 = self.bornes(hs)
        _, _, w, h = self.aire
        z = max(.5, min(w / (x1 - x0 + 16), h / (y1 - y0 + 16)) * .95)
        if zmax:
            z = min(z, zmax)
        but = [(x0 + x1) / 2, (y0 + y1) / 2, z]
        if doux:
            self.but = but
        else:
            self.cam = but
            self.but = None

    def tout_voir(self, doux=True):
        self.manuel = False
        if self.carte:
            self.ajuster(list(self.carte["hex"].values()), doux, zmax=3.2)

    def ecran(self, x, y):
        ax, ay, aw, ah = self.aire
        cx, cy, z = self.cam
        return ax + aw / 2 + (x - cx) * z, ay + ah / 2 + (y - cy) * z

    def monde_xy(self, sx, sy):
        ax, ay, aw, ah = self.aire
        cx, cy, z = self.cam
        return (sx - ax - aw / 2) / z + cx, (sy - ay - ah / 2) / z + cy

    # ------------------------------------------------ les créatures
    def _peut(self, cr, h):
        if not h or h["region"] != cr.info["type"] or h["block"]:
            return False
        p = self.carte["par"].get(h["parcelle"])
        for v in (p["poses"].values() if p else ()):
            if v["bloque"] and (p["centre"][0] + v["off"][0], p["centre"][1] + v["off"][1]) == (h["q"], h["r"]):
                return False
        return True

    def _pas(self, cr, a, b):
        return self._peut(cr, b) and (cr.info.get("volant") or abs(a["h"] - b["h"]) <= 2.9)

    def _poser(self, cr, arrivee=False):
        p = self.carte["par"][self.maison[cr.info["id"]]]
        hs = [self.carte["hex"][(p["centre"][0] + o[0], p["centre"][1] + o[1])] for o in G.FLOWER]
        ok = [h for h in hs if self._peut(cr, h)] or [self.carte["hex"][tuple(p["centre"])]]
        ok.sort(key=lambda h: h["d"])
        h = ok[min(len(ok) - 1, int(random.random() * min(3, len(ok))))]
        cr.at = h["cle"]
        cr.seg, cr.chemin, cr.etat, cr.jusqu = None, [], "idle", self.t + 1
        if arrivee:
            x, y = self.sommet(h)
            cr.vol = (x, y - 170, self.t + .6, 1.0)

    def _voisins(self, h):
        for a, b in G.DIRS:
            n = self.carte["hex"].get((h["q"] + a, h["r"] + b))
            if n:
                yield n

    def _bfs(self, cr, depart, maxd=6):
        prev = {depart["cle"]: None}
        file, out = [(depart, 0)], []
        while file:
            h, d = file.pop(0)
            out.append((h, d))
            if d >= maxd:
                continue
            for n in self._voisins(h):
                if n["cle"] in prev or not self._pas(cr, h, n):
                    continue
                prev[n["cle"]] = h["cle"]
                file.append((n, d + 1))
        return prev, out

    def _penser(self, cr):
        r = random.random()
        if r < .1:
            cr.etat, cr.jusqu = "dort", self.t + 4 + random.random() * 5
            return
        if r < .25:
            cr.etat, cr.jusqu = "saute", self.t + .9
            return
        if r < .38:
            cr.etat, cr.jusqu = "idle", self.t + 1.5 + random.random() * 2.5
            return
        h = self.par_cle.get(cr.at)
        if not h:
            return
        prev, out = self._bfs(cr, h)
        c = [o for o in out if o[1] >= 2]
        chez = [o for o in c if o[0]["parcelle"] == self.maison.get(cr.info["id"])]
        if chez and random.random() < .65:
            c = chez
        if not c:
            cr.etat, cr.jusqu = "idle", self.t + 2
            return
        but = random.choice(c)[0]["cle"]
        ch = []
        while prev.get(but):
            ch.insert(0, but)
            but = prev[but]
        cr.chemin, cr.etat, cr.jusqu = ch, "marche", self.t + 20

    def _avancer(self, cr, dt):
        if cr.at not in self.par_cle:
            if cr.info["id"] in self.maison:
                self._poser(cr)
            return
        if cr.vol and self.t >= cr.vol[2] + cr.vol[3]:
            cr.vol = None
            cr.pop = self.t + .6
            self.eclat(self.pos_crea(cr)[:2], "etoile", 10)
        if cr.vol:
            return
        if cr.seg:
            a, b, k = cr.seg
            ha, hb = self.par_cle[a], self.par_cle[b] if b in self.par_cle else self.par_cle[a]
            k += dt * 1.3 / (1 + abs(hb["h"] - ha["h"]) * .15)
            if k >= 1:
                cr.at, cr.seg = b, None
            else:
                cr.seg = (a, b, k)
        elif cr.etat == "marche":
            if not cr.chemin:
                cr.etat, cr.jusqu = "idle", self.t + 1 + random.random() * 2
                return
            n = cr.chemin.pop(0)
            ha, hb = self.par_cle[cr.at], self.par_cle.get(n)
            if not hb or not self._pas(cr, ha, hb):
                cr.chemin, cr.etat, cr.jusqu = [], "idle", self.t + .5
                return
            xa, xb = G.sol_xy(ha["q"], ha["r"])[0], G.sol_xy(hb["q"], hb["r"])[0]
            if abs(xb - xa) > .1:
                cr.face = 1 if xb > xa else -1
            cr.seg = (cr.at, n, 0.0)
        elif self.t > cr.jusqu:
            self._penser(cr)

    def pos_crea(self, cr):
        """(x, y du sol sous la créature, profondeur)."""
        if cr.seg:
            a, b, k = cr.seg
            ha, hb = self.par_cle[a], self.par_cle.get(b, self.par_cle[a])
            (xa, ya), (xb, yb) = self.sommet(ha), self.sommet(hb)
            s = k * k * (3 - 2 * k)
            x, y = xa + (xb - xa) * k, ya + (yb - ya) * s
            dh = abs(hb["h"] - ha["h"])
            if dh > .4 and not cr.info.get("volant"):
                y -= math.sin(k * math.pi) * min(9, dh * HZ * .6)
            d = max(G.sol_xy(ha["q"], ha["r"])[1], G.sol_xy(hb["q"], hb["r"])[1]) + .5
        else:
            h = self.par_cle[cr.at]
            x, y = self.sommet(h)
            d = G.sol_xy(h["q"], h["r"])[1] + .5
        if cr.vol:
            x0, y0, t0, du = cr.vol
            q = clamp((self.t - t0) / du, 0, 1)
            x, y = x0 + (x - x0) * q * q, y0 + (y - y0) * q * q
            d = 1e6
        return x, y, d

    def dire(self, texte, duree=4.0, qui=None):
        """Une phrase dans la bulle d'une créature du monde (le guide, sinon la première)."""
        cr = self.creas.get(qui) if qui else None
        if not cr:
            cr = next((c for c in self.creas.values() if c.at and c.info.get("guide")), None) or \
                next((c for c in self.creas.values() if c.at), None)
        if cr:
            cr.dit = (texte, self.t + duree)
        else:
            self.bulle = (texte, self.t + duree)

    # ------------------------------------------------ les particules
    def eclat(self, p, sorte, n=14):
        cols = {"pouf": [(255, 255, 255), (230, 230, 230), (207, 216, 220)],
                "coeur": [(255, 92, 138), (255, 143, 176)],
                "confetti": [(255, 95, 109), (255, 213, 79), (61, 220, 132), (95, 175, 255), (178, 132, 255)],
                "braise": [(255, 122, 26), (255, 211, 107)]}.get(sorte, [(255, 224, 102), (255, 246, 176),
                                                                           (255, 255, 255)])
        for _ in range(n):
            a = random.random() * math.pi * 2
            s = 10 + random.random() * 24 if sorte != "coeur" else 6
            self.parts.append({"x": p[0] + (random.random() - .5) * 8, "y": p[1] - 8 - random.random() * 8,
                               "vx": math.cos(a) * s, "vy": math.sin(a) * s * .6 - (30 if sorte == "confetti" else 8),
                               "v": 0.0, "max": .6 + random.random() * .6, "c": random.choice(cols),
                               "s": 2 if random.random() < .5 else 1.4, "g": 60 if sorte == "confetti" else 0})

    # ------------------------------------------------ le temps
    def tick(self, dt):
        self.t += dt
        if self.but:
            k = min(1.0, dt * 4)
            for i in range(3):
                self.cam[i] += (self.but[i] - self.cam[i]) * k
            if abs(self.but[2] - self.cam[2]) < .01 and abs(self.but[0] - self.cam[0]) < .5 \
                    and abs(self.but[1] - self.cam[1]) < .5:
                self.cam, self.but = list(self.but), None
        if self.carte:
            for cr in self.creas.values():
                if cr.at:
                    self._avancer(cr, dt)
        for p in self.parts:
            p["v"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += p["g"] * dt
        self.parts = [p for p in self.parts if p["v"] < p["max"]][-400:]
        self.fantomes = [f for f in self.fantomes if self.t - f["t0"] < 1.0]
        self.effets = [e for e in self.effets if self.t - e["t0"] < e["du"]]
        if self.retour and not self.effets and not self.manuel:
            self.but, self.retour = self.retour, None
        elif self.retour and not self.effets:
            self.retour = None

    # ------------------------------------------------ les effets des commandes
    def preparer(self, evs):
        """Avant de relire le terrain : où étaient les choses qui vont partir (pour qu'elles partent de là)."""
        for e in evs:
            if e["type"] in ("objet-", "dossier-", "deplace", "renomme"):
                e["pts_avant"] = [self.point_de(e.get("chemin") or e.get("de"))]
            elif e["type"] == "groupe" and str(e.get("sorte", "")).endswith("-"):
                e["pts_avant"] = [self.point_de(c) for c in e.get("chemins", [])]
            elif e["type"] == "cd":
                e["pts_avant"] = [self.point_de(e.get("de") or "")]

    def lancer(self, evs):
        """Joue les effets (effets.evenements), les uns après les autres (jokers d'abord), jamais bloquants."""
        if not evs:
            return
        d = 0.0
        premier = None
        for e in evs[:12]:
            ef = dict(e)
            ef["t0"] = self.t + d
            ef["du"] = 1.1 if e["type"] == "jokers" else DUREE
            ef["pts"] = self._points(e)
            self.effets.append(ef)
            if premier is None and ef["pts"]:
                premier = ef["pts"][0]
            d += .55 if e["type"] == "jokers" else .3
            if e["type"] in ("objet-", "dossier-", "groupe") and ef["pts"]:
                pass
        if premier and self.aire and not self.manuel:
            sx, sy = self.ecran(*premier)
            ax, ay, aw, ah = self.aire
            if not (ax + aw * .15 < sx < ax + aw * .85 and ay + ah * .15 < sy < ay + ah * .85):
                self.retour = self.retour or list(self.cam)
                self.but = [premier[0], premier[1], max(self.cam[2], 1.6)]

    def _points(self, e):
        ty = e["type"]
        av = e.get("pts_avant")
        if av and ty in ("objet-", "dossier-", "groupe"):
            return av
        if av and ty in ("deplace", "renomme", "cd"):
            return [av[0], self.point_de(e.get("vers") or "")]
        if ty in ("jokers", "find", "groupe"):
            return [self.point_de(c) for c in e.get("chemins", [])[:20]] or [self.point_de(e.get("chemin"))]
        if ty in ("deplace", "renomme", "copie"):
            return [self.point_de(e["de"]), self.point_de(e["vers"])]
        if ty == "cd":
            return [self.point_de(e.get("de") or ""), self.point_de(e.get("vers") or "")]
        if ty in ("lucioles", "messager", "photo"):
            cr = next((c for c in self.creas.values() if c.at and c.info.get("guide")), None) or \
                next((c for c in self.creas.values() if c.at), None)
            p = self.pos_crea(cr)[:2] if cr else self.milieu()
            if ty == "messager":
                cible = e.get("cible", "")
                q = self.point_de("biome/" + cible) if cible in G.TYPES else (p[0] + 120, p[1] - 90)
                return [p, q]
            return [p]
        if ty == "tuyau":
            return [self.point_de(e.get("source") or ("biome/" + e["region"] if e.get("region") else ""))]
        return [self.point_de(e.get("chemin"))]

    # ================================================ le dessin
    def dessiner(self, L, Z, rect, t_, grand=False):
        """Le monde dans rect (x, y, w, h) : la vue en relief à gauche, la liste ou la fiche à droite."""
        import time as _t
        d0 = _t.perf_counter()
        x, y, w, h = rect
        lw = clamp(w * .34, 230, 400) if w >= 620 else 0
        if not self.liste_ouverte and lw:
            lw = 0
        aire = (x, y, w - lw - (10 if lw else 0), h)
        if self.aire and (abs(self.aire[2] - aire[2]) > 40 or abs(self.aire[3] - aire[3]) > 40) and not self.manuel:
            self.a_cadrer = True                     # la vue a changé de taille (onglet ↔ en grand) : on recadre
        self.aire = aire
        if self.a_cadrer and self.carte:
            self.a_cadrer = False
            self.tout_voir(doux=False)
        if self.carte is None:
            L.append(("rrect", x, y, w, h, 10, (11, 26, 38, 255), (255, 255, 255, 30), 1))
            return
        if not self.carte["parcelles"]:
            self._vide(L, Z, self.aire)
        else:
            sous = []
            self._monde(sous, Z)
            L.append(("calque", *self.aire, sous))
            self._outils(L, Z)
        if lw:
            self._panneau(L, Z, (x + w - lw, y, lw, h))
        else:
            ax, ay, aw, ah = self.aire
            L.append(("rrect", ax + aw - 132, ay + ah - 40, 122, 30, 9, (5, 10, 15, 210), (255, 255, 255, 60), 1))
            L.append(("texte", ax + aw - 71, ay + ah - 25, "🐾 " + str(len(self.equipe)), 13, TEXTE, True, "c", False))
            Z.append((ax + aw - 132, ay + ah - 40, 122, 30, "monde:liste"))
        self.mesure = (self.mesure + [_t.perf_counter() - d0])[-60:]

    def _vide(self, L, Z, r):
        x, y, w, h = r
        L.append(("rrect", x, y, w, h, 10, (11, 26, 38, 255), (255, 255, 255, 30), 1))
        ty = next((e["type"] for e in self.equipe if e.get("guide")), "plante")
        L.append(("texte", x + w / 2, y + h / 2 - 22, t("monde.vide"), 15, TEXTE, True, "c", False))
        L.append(("texte", x + w / 2, y + h / 2 + 6, t("monde.vide_cmd", cmd=""), 13, DOUX, False, "c", False))
        cmd = f"mkdir -p biome/{ty}/parcelle_1"
        L.append(("rrect", x + w / 2 - 150, y + h / 2 + 22, 300, 30, 8, (5, 10, 6, 255), (61, 220, 132, 120), 1))
        L.append(("texte", x + w / 2, y + h / 2 + 37, cmd, 13, VERT, False, "c", True))

    def _ciel(self, L):
        x, y, w, h = self.aire
        haut, bas = (124, 198, 240), (191, 231, 255)
        n = 10
        for i in range(n):
            k = i / (n - 1)
            c = tuple(int(haut[j] + (bas[j] - haut[j]) * k) for j in range(3)) + (255,)
            L.append(("rect", x, y + h * i / n, w, h / n + 1, c))
        for i in range(3):                          # trois nuages qui passent
            cx = x + ((self.t * 6 + i * w * .4) % (w + 300)) - 150
            cy = y + h * (.06 + i * .08)
            for a, b, ww, hh in ((0, 2, 24, 4), (4, 0, 14, 3), (18, 1, 10, 4)):
                L.append(("rect", cx + a * 2, cy + b * 2, ww * 2, hh * 2, (255, 255, 255, 190)))

    def _monde(self, L, Z):
        self._ciel(L)
        ax, ay, aw, ah = self.aire
        Z.append((ax, ay, aw, ah, "monde:vue"))
        cx, cy, z = self.cam
        x0w, y0w = self.monde_xy(ax - 40, ay - 60)
        x1w, y1w = self.monde_xy(ax + aw + 40, ay + ah + 120)
        budget = [BUDGET_SPRITES]
        # ce qui bouge pendant un effet : parcelles qui tombent, objets qui arrivent ou partent
        tombe = {}
        objets_caches = set()
        for e in self.effets:
            age = self.t - e["t0"]
            if e["type"] == "dossier+" and age < 1.4:
                for c in e.get("parcelles") or [e.get("chemin")]:
                    p = (c or "").split("/")
                    if len(p) >= 3:
                        tombe[p[1] + "/" + p[2]] = age
            if e["type"] in ("objet+", "copie", "deplace", "renomme") and age < .9:
                objets_caches.add(e.get("chemin") or e.get("vers"))
        iso = self.iso
        # entités : hexagones (ordre fixe), objets et créatures (triés) — les falaises de devant cachent l'arrière
        mobiles = []
        for p in self.carte["parcelles"]:
            for nom, v in p["poses"].items():
                h = self.carte["hex"][(p["centre"][0] + v["off"][0], p["centre"][1] + v["off"][1])]
                mobiles.append((G.sol_xy(h["q"], h["r"])[1] + .4, 1, (p, nom, v, h)))
        for cr in self.creas.values():
            if cr.at in self.par_cle:
                x, y, d = self.pos_crea(cr)
                mobiles.append((d, 2, cr))
        mobiles.sort(key=lambda m: m[0])
        j = 0
        for h in self.ordre:
            dh = G.sol_xy(h["q"], h["r"])[1]
            while j < len(mobiles) and mobiles[j][0] < dh:
                self._mobile(L, Z, mobiles[j], iso, objets_caches)
                j += 1
            hx, hy = G.sol_xy(h["q"], h["r"])
            if hx < x0w or hx > x1w or hy - h["h"] * HZ > y1w or hy + 40 < y0w:
                continue
            self._hex(L, h, tombe.get(h["parcelle"]), iso, budget)
        while j < len(mobiles):
            self._mobile(L, Z, mobiles[j], iso, objets_caches)
            j += 1
        for f in self.fantomes:
            self._fantome(L, f)
        self._contours(L)
        self._particules(L)
        for e in self.effets:
            if self.t >= e["t0"]:
                try:
                    self._effet(L, e, self.t - e["t0"])
                except (KeyError, IndexError, TypeError, ValueError):
                    pass
        self._etiquettes(L, Z)
        self._bulles(L)

    def _alpha_iso(self, region, between=None):
        if not self.iso:
            return 1.0
        return 1.0 if region == self.iso or (between and self.iso in between) else .32

    def _hex(self, L, h, chute, iso, budget):
        x, y = self.sommet(h)
        oy, a = 0.0, self._alpha_iso(h["region"], h["between"])
        if chute is not None:                        # la parcelle tombe du ciel, tuile par tuile
            k = clamp((chute - h["d"] * .12) / .5, 0, 1)
            if k <= 0:
                return
            oy, a = (1 - ease_back(k)) * -60, min(a, k)
        cle = f"hex|{h['kind']}|{h['v']}|{h['mur']}|{h['pilier']}"
        if cle not in MD._SPRITES:
            if budget[0] <= 0:                       # pas encore dessiné : une tuile toute simple en attendant
                sx, sy = self.ecran(x, y + oy)
                z = self.cam[2]
                top = MD.KINDS.get(h["kind"], MD.KINDS["herbe"])[0][0]
                L.append(("poly", [(sx + math.cos(k * math.pi / 3) * HR * z, sy + math.sin(k * math.pi / 3) * HR * .62 * z)
                                   for k in range(6)], rgb(top, int(255 * a))))
                return
            budget[0] -= 1
        cad = MD.sprite(h["kind"], h["v"], h["mur"], h["pilier"])
        fy = math.sin(self.t * 1.1 + h["q"] * .7 + h["r"]) * 1.2 if h["float"] else 0
        sc = .84 if h["float"] else 1.0
        sx, sy = self.ecran(x, y + oy + fy)
        z = self.cam[2]
        L.append(("imgt", cad, sx, sy, z * sc, False, False, 1.0, 1.0, 0.0, a))
        if a < 1 and chute is None:
            return
        k = h["kind"]
        if k == "lave":
            g = .22 + .22 * math.sin(self.t * 3 - (h["flow"] or 0) * 1.4)
            L.append(("ellipse", sx, sy, HR * .8 * z, HR * .5 * z, (255, 226, 138, int(255 * g * a))))
            if h["crater"]:
                L.append(("lueur", sx, sy - 6 * z, HR * 2 * z, (255, 122, 26, int(60 + 25 * math.sin(self.t * 2.3)))))
                if random.random() < .15:
                    self.parts.append({"x": x + (random.random() - .5) * 10, "y": y - 2, "vx": (random.random() - .5) * 5,
                                       "vy": -20 - random.random() * 8, "v": 0.0, "max": 2.5, "c": (154, 147, 160),
                                       "s": 3, "g": 0, "fumee": True})
        elif k == "eau":
            for i in range(2):
                ph = (self.t * 1.1 + h["q"] * .37 + h["r"] * .61 + i * .5) % 2
                if ph < 1:
                    L.append(("rect", sx + (-6 + (h["q"] * 7 + h["r"] * 3 + i * 9) % 12) * z, sy + (-3 + i * 4 + ph * 2) * z,
                              3 * z, 1 * z, (220, 245, 255, int(215 * (1 - ph)))))
        elif k == "toxique":
            ph = (self.t * .9 + h["q"] * .53 + h["r"] * .29) % 1.6
            if ph < 1:
                L.append(("rect", sx + (-5 + (h["q"] * 11 + h["r"] * 5) % 10) * z, sy - ph * 6 * z, 2 * z, 2 * z,
                          (217, 255, 138, int(255 * (1 - ph)))))
        elif k == "pont":
            for kk in (3, 0):
                vx = sx + math.cos(kk * math.pi / 3) * HR * z
                vy = sy + math.sin(kk * math.pi / 3) * HR * .62 * z
                L.append(("rect", vx - z, vy - 6 * z, 2 * z, 7 * z, (90, 56, 30, 255)))
        if h["scen"]:
            im = MD.decor(h["scen"]["k"])
            s = h["scen"]["s"]
            L.append(("ellipse", sx, sy + z, im.w * .3 * s * z, im.w * .11 * s * z, (0, 0, 0, int(64 * a))))
            L.append(("imgt", im, sx, sy + 2 * z, z * s, False, False, 1.0, 1.0,
                      math.sin(self.t * 1.3 + h["q"] + h["r"]) * 1.2 if h["scen"]["k"] in G.SCEN_BLOCK else 0.0, a))

    def _mobile(self, L, Z, m, iso, caches):
        _d, sorte, o = m
        if sorte == 1:
            p, nom, v, h = o
            chemin = f"biome/{p['id']}/{nom}"
            if chemin in caches:
                return
            x, y = self.sommet(h)
            a = self._alpha_iso(p["type"])
            im = MD.decor(v["k"])
            sx, sy = self.ecran(x, y)
            z = self.cam[2]
            s, oy, rot = 1.0, 0.0, 0.0
            for e in self.effets:                   # l'objet visé frétille, s'allume, rebondit
                age = self.t - e["t0"]
                if 0 <= age < e["du"] and chemin in (e.get("chemin"), *(e.get("chemins") or ())):
                    if e["type"] in ("touche", "modifie", "ecrit", "droits", "jokers", "lire", "empreinte", "refus"):
                        rot = math.sin(age * 30) * 6 * max(0.0, 1 - age / 1.2)
                    if e["type"] in ("jokers", "find"):
                        L.append(("lueur", sx, sy - im.h * z * .5, 26 * z, (255, 236, 128, int(150 * (1 - age / e["du"])))))
            L.append(("ellipse", sx, sy + z, im.w * .32 * z, im.w * .12 * z, (0, 0, 0, int(70 * a))))
            L.append(("imgt", im, sx, sy + (2 + oy) * z, z * s, False, False, 1.0, 1.0, rot, a))
            Z.append((sx - im.w * z / 2, sy - im.h * z, im.w * z, im.h * z + 4, "monde:objet:" + chemin))
            return
        cr = o
        info = cr.info
        al = info.get("album")
        x, y, _d = self.pos_crea(cr)
        a = self._alpha_iso(info["type"])
        z = self.cam[2]
        H0 = STADES_H.get(info.get("stade", "bebe"), 36)
        lift = 10 + math.sin(self.t * 2 + cr.ph) * 2.5 if info.get("volant") else 0
        bob = 0.0
        if cr.seg:
            bob = abs(math.sin(self.t * 9 + cr.ph)) * 2
        if cr.etat == "saute" and not cr.seg:
            q = clamp(1 - (cr.jusqu - self.t) / .9, 0, 1)
            bob = max(0.0, math.sin(min(q * 2, 1) * math.pi) * 9)
        if cr.pop > self.t:
            bob += math.sin((1 - (cr.pop - self.t) / .6) * math.pi) * 10
        if cr.vol:
            bob += math.sin(clamp((self.t - cr.vol[2]) / cr.vol[3], 0, 1) * math.pi) * 30
        sx, sy = self.ecran(x, y)
        on = self.par_cle.get(cr.at)
        eau = on and on["kind"] == "eau" and not info.get("volant")
        L.append(("ellipse", sx, sy + z, max(5, H0 * .36) * z, max(2, H0 * .13) * z, (0, 0, 0, int((46 if lift else 76) * a))))
        if self.sel == info["id"]:
            pul = 1 + math.sin(self.t * 5) * .08
            L.append(("cercle", sx, sy + z, (H0 * .5 + 5) * pul * z, (255, 224, 102, 255), 2))
        coul = RARETE.get(info.get("rarete"))
        top = sy - (lift + bob - (H0 * .28 if eau else 0)) * z
        if coul or info.get("shiny"):
            if info.get("shiny"):
                coul = [(255, 107, 107), (255, 216, 102), (74, 222, 128), (56, 189, 248), (192, 132, 252)][
                    int(self.t * 1.3) % 5]
            L.append(("lueur", sx, top - H0 * .5 * z, H0 * .75 * z,
                      coul + (int((90 + 50 * math.sin(self.t * 2.4 + cr.ph)) * a),)))
        if al:
            etat = "dort" if cr.etat == "dort" else ("marche" if cr.seg else "assis")
            k = int(self.t * 6) if etat == "marche" else 0
            e = H0 * z / max(1, al.ref)
            souffle = .94 + math.sin(self.t * 1.6) * .02 if cr.etat == "dort" else 1 + math.sin(self.t * 2.2 + cr.ph) * .018
            L.append(("imgt", al.image(etat, k), sx, top, e, cr.face < 0, al.lisse, 1.0, souffle, 0.0, a))
        else:
            L.append(("ellipse", sx, top - H0 * .45 * z, H0 * .35 * z, H0 * .4 * z, rgb(COUL_TYPE[info["type"]], int(255 * a))))
        if eau:
            L.append(("cercle", sx, sy, (H0 * .45 + math.sin(self.t * 3) * 1.5) * z, (230, 248, 255, 200), 1))
        if self.sel == info["id"]:
            ay_ = top - (H0 + 6 + math.sin(self.t * 6) * 2) * z
            L.append(("poly", [(sx - 5 * z, ay_), (sx + 5 * z, ay_), (sx, ay_ + 5 * z)], (255, 224, 102, 255)))
        if cr.etat == "dort" and random.random() < .02:
            self.parts.append({"x": x + H0 * .3, "y": y - H0, "vx": 4, "vy": -8, "v": 0.0, "max": 1.6,
                               "c": (255, 255, 255), "s": 0, "g": 0, "z": True})
        Z.append((sx - H0 * .5 * z - 6, top - H0 * z - 6, H0 * z + 12, H0 * z + 12, "monde:crea:" + info["id"]))

    def _fantome(self, L, f):
        """Une tuile qui s'écroule (une parcelle supprimée)."""
        age = self.t - f["t0"]
        if age < 0:
            age = 0
        h = f["h"]
        cad = MD.sprite(h["kind"], h["v"], h["mur"], h["pilier"])
        sx, sy = self.ecran(f["x"], f["y"] + age * age * 160)
        L.append(("imgt", cad, sx, sy, self.cam[2], False, False, 1.0, 1.0, age * 25 * (1 if h["q"] % 2 else -1),
                  max(0.0, 1 - age)))

    def _contours(self, L):
        """La parcelle où l'on est (vert, pointillés qui avancent) et les parcelles libres (pointillés pâles)."""
        z = self.cam[2]
        occupees = set(self.maison.values())
        ici = None
        if self.cwd and self.cwd.startswith("biome/"):
            p = self.cwd.split("/")
            if len(p) >= 3:
                ici = [p[1] + "/" + p[2]]
            elif len(p) == 2:
                ici = [x["id"] for x in self.carte["parcelles"] if x["type"] == p[1]]
        for pid, bords in self.bords.items():
            if ici and pid in ici:
                c, ti, ep = (61, 255, 124, 255), (6 * z, 4 * z, -self.t * 20 * z), 2
            elif pid not in occupees and (not self.iso or pid.startswith(self.iso + "/")):
                c, ti, ep = (255, 248, 220, 150), (2 * z, 3 * z, 0), 1.4
            else:
                continue
            for cle, k1, k2 in bords:
                h = self.par_cle[cle]
                x, y = self.sommet(h)
                sx, sy = self.ecran(x, y)
                a1, a2 = k1 * math.pi / 3, k2 * math.pi / 3
                L.append(("ligne", sx + math.cos(a1) * HR * z, sy + math.sin(a1) * HR * .62 * z,
                          sx + math.cos(a2) * HR * z, sy + math.sin(a2) * HR * .62 * z, c, ep, ti))

    def _particules(self, L):
        z = self.cam[2]
        for p in self.parts:
            al = 1 - p["v"] / p["max"]
            sx, sy = self.ecran(p["x"], p["y"])
            if p.get("z"):
                L.append(("texte", sx, sy, "z", 9 * z / 2, (255, 255, 255, int(255 * al)), False, "c", True))
            elif p.get("fumee"):
                L.append(("ellipse", sx, sy, (3 + p["v"] * 6) * z, (3 + p["v"] * 6) * z, p["c"] + (int(70 * al),)))
            else:
                L.append(("rect", sx, sy, p["s"] * z, p["s"] * z, p["c"] + (int(255 * al),)))

    def _etiquettes(self, L, Z):
        z = self.cam[2]
        places = []
        for tid in G.TYPES:
            ps = [p for p in self.carte["parcelles"] if p["type"] == tid]
            if not ps or (self.iso and self.iso != tid):
                continue
            hs = [self.carte["hex"][(p["centre"][0] + o[0], p["centre"][1] + o[1])] for p in ps for o in G.FLOWER]
            top = min(hs, key=lambda h: G.sol_xy(h["q"], h["r"])[1])
            xw = G.sol_xy(top["q"], top["r"])[0]
            yw = min(self.sommet(h)[1] - (24 if h["scen"] else 0) for h in hs
                     if abs(G.sol_xy(h["q"], h["r"])[0] - xw) < HR * 4) - 10
            sx, sy = self.ecran(xw, yw)
            n = sum(1 for k, v in self.maison.items() if v.startswith(tid + "/"))
            att = sum(1 for e in self.equipe if e["type"] == tid and e["id"] in self.refuge)
            txt = f"{EMOJI[tid]} {tid}/ {n}/{len(ps)}"
            tw = len(txt) * 7.2 + 18 + (26 if att else 0)
            bx, by = sx - tw / 2, sy - 22
            for (px, py, pw, ph) in places:
                if bx < px + pw and bx + tw > px and by < py + ph and by + 22 > py:
                    by = py - 24
            places.append((bx, by, tw, 22))
            actif = bool(self.cwd and self.cwd.startswith(f"biome/{tid}"))
            L.append(("rrect", bx, by, tw, 22, 6, (5, 20, 10, 235) if actif else (5, 10, 15, 200),
                      (61, 255, 124, 255) if actif else rgb(COUL_TYPE[tid], 200), 1.2))
            L.append(("texte", bx + 9, by + 11, txt, 12, (61, 255, 124, 255) if actif else (230, 240, 255, 255),
                      True, "g", False))
            if att:
                L.append(("rrect", bx + tw - 28, by + 3, 22, 16, 5, (255, 216, 102, 255), None, 0))
                L.append(("texte", bx + tw - 17, by + 11, f"+{att}", 10.5, (43, 36, 22, 255), True, "c", False))
            Z.append((bx, by, tw, 22, "monde:region:" + tid))
        if z >= 1.4 or self.iso:
            for p in self.carte["parcelles"]:
                if self.iso and p["type"] != self.iso:
                    continue
                h = self.carte["hex"][tuple(p["centre"])]
                sx, sy = self.ecran(*self.sommet(h))
                libre = p["id"] not in self.maison.values()
                txt = p["nom"] + (" · " + t("monde.libre") if libre else "")
                tw = len(txt) * 6.4 + 10
                L.append(("rrect", sx - tw / 2, sy - 8, tw, 16, 4, (255, 248, 220, 220) if libre else (5, 10, 15, 150),
                          None, 0))
                L.append(("texte", sx, sy, txt, 10.5, (90, 58, 16, 255) if libre else (230, 240, 255, 255), False,
                          "c", True))

    def _bulles(self, L):
        for cr in self.creas.values():
            if not cr.dit or not cr.at:
                continue
            if self.t > cr.dit[1]:
                cr.dit = None
                continue
            x, y, _d = self.pos_crea(cr)
            H0 = STADES_H.get(cr.info.get("stade", "bebe"), 36)
            sx, sy = self.ecran(x, y - H0 - 8)
            self._bulle(L, cr.dit[0], sx, sy)
        if self.bulle and self.t < self.bulle[1]:
            ax, ay, aw, ah = self.aire
            self._bulle(L, self.bulle[0], ax + aw / 2, ay + ah - 20)

    def _bulle(self, L, texte, sx, sy):
        from .espace_scene import couper, lt
        ax, ay, aw, ah = self.aire
        lignes = couper(texte, min(300, aw * .6), 13)[:4]
        tw = max(lt(x, 13) for x in lignes) + 20
        bh = len(lignes) * 17 + 12
        bx = clamp(sx - tw / 2, ax + 6, ax + aw - tw - 6)
        by = clamp(sy - bh - 10, ay + 6, ay + ah - bh - 10)
        L.append(("rrect", bx - 2, by - 2, tw + 4, bh + 4, 8, (0, 0, 0, 255), None, 0))
        L.append(("rrect", bx, by, tw, bh, 7, (255, 251, 232, 255), None, 0))
        tx = clamp(sx, bx + 10, bx + tw - 10)
        L.append(("poly", [(tx - 6, by + bh), (tx + 6, by + bh), (tx, by + bh + 8)], (255, 251, 232, 255)))
        for i, l_ in enumerate(lignes):
            L.append(("texte", bx + 10, by + 14 + i * 17, l_, 13, (43, 36, 22, 255), False, "g", False))

    def _outils(self, L, Z):
        """Les boutons du monde (− + ⌖) et, quand une région est isolée, son en-tête « ← Monde »."""
        ax, ay, aw, ah = self.aire
        x = ax + aw - 10
        for sym, act in (("voir", "monde:voir"), ("+", "monde:plus"), ("−", "monde:moins")):
            x -= 34
            L.append(("rrect", x, ay + 10, 30, 30, 8, (5, 10, 15, 200), (255, 255, 255, 70), 1))
            if sym == "voir":                        # « tout voir » : un viseur dessiné (pas de glyphe rare)
                L.append(("cercle", x + 15, ay + 25, 6, TEXTE, 1.6))
                for a_, b_, c_, d_ in ((x + 6, ay + 25, x + 10, ay + 25), (x + 20, ay + 25, x + 24, ay + 25),
                                       (x + 15, ay + 16, x + 15, ay + 20), (x + 15, ay + 30, x + 15, ay + 34)):
                    L.append(("ligne", a_, b_, c_, d_, TEXTE, 1.6, None))
            else:
                L.append(("texte", x + 15, ay + 25, sym, 16, TEXTE, True, "c", False))
            Z.append((x, ay + 10, 30, 30, act))
        if self.iso:
            tid = self.iso
            ps = [p for p in self.carte["parcelles"] if p["type"] == tid]
            n = sum(1 for v in self.maison.values() if v.startswith(tid + "/"))
            txt = f"{EMOJI[tid]} {t('carte.biome.' + tid)} · " + t("monde.region_n", p=len(ps), c=n)
            from .espace_scene import lt
            tw = lt(txt, 13) + 120
            L.append(("rrect", ax + 10, ay + 10, tw, 34, 10, (5, 10, 15, 215), rgb(COUL_TYPE[tid], 220), 2))
            L.append(("rrect", ax + 16, ay + 15, 86, 24, 6, (15, 36, 22, 255), (61, 255, 124, 255), 1))
            L.append(("texte", ax + 59, ay + 27, t("monde.retour_monde"), 12.5, (61, 255, 124, 255), False, "c", False))
            Z.append((ax + 16, ay + 15, 86, 24, "monde:sortir"))
            L.append(("texte", ax + 112, ay + 27, txt, 13, (230, 240, 255, 255), True, "g", False))
        elif self.mesure and os.environ.get("TG_MONDE_MESURE"):
            ms = sum(self.mesure) / len(self.mesure) * 1000
            L.append(("texte", ax + 12, ay + ah - 12, f"{ms:.1f} ms", 11, (255, 255, 255, 200), False, "g", True))

    # ------------------------------------------------ la liste et la fiche
    def _panneau(self, L, Z, r):
        x, y, w, h = r
        L.append(("rrect", x, y, w, h, 10, (19, 28, 36, 255), (38, 56, 74, 255), 1.5))
        Z.append((x, y, w, h, "monde:panneau"))
        if self.sel and self.sel in self.creas:
            self._fiche(L, Z, r, self.creas[self.sel].info)
        else:
            self._liste(L, Z, r)

    def _liste(self, L, Z, r):
        from .espace_scene import court
        x, y, w, h = r
        L.append(("texte", x + 14, y + 20, t("monde.mes_creatures", n=len(self.equipe)), 13, (255, 216, 102, 255),
                  True, "g", False))
        yy = y + 40
        ref = [e for e in self.equipe if e["id"] in self.refuge]
        if ref:
            hb = 26 + 30 * min(3, len(ref))
            L.append(("rrect", x + 10, yy, w - 20, hb, 8, (40, 36, 20, 255), (168, 140, 60, 200), 1))
            L.append(("texte", x + 20, yy + 13, "🏠 " + t("monde.refuge", n=len(ref)), 11.5, (255, 216, 102, 255), True,
                      "g", False))
            for i, e in enumerate(ref[:3]):
                ly = yy + 26 + 30 * i
                self._vignette(L, e, x + 32, ly + 26, 24)
                L.append(("texte", x + 52, ly + 14, court(e["nom"], w - 190, 12), 12, TEXTE, False, "g", False))
                cmd = self.cmd_agrandir(e["type"])
                L.append(("texte", x + w - 18, ly + 14, court(cmd, 140, 10.5, True), 10.5, VERT, False, "d", True))
                Z.append((x + 10, ly, w - 20, 28, "monde:crea:" + e["id"]))
            yy += hb + 8
        for tid in G.TYPES:
            es = [e for e in self.equipe if e["type"] == tid]
            ps = [p for p in self.carte["parcelles"] if p["type"] == tid]
            if not es and not ps:
                continue
            if yy + 50 > y + h:
                break
            n = sum(1 for e in es if e["id"] in self.maison)
            L.append(("rrect", x + 10, yy, w - 20, 22, 11, rgb(COUL_TYPE[tid], 60), rgb(COUL_TYPE[tid], 170), 1))
            L.append(("texte", x + 20, yy + 11, f"{EMOJI[tid]} {t('carte.biome.' + tid)}", 12, TEXTE, True, "g", False))
            L.append(("texte", x + w - 20, yy + 11, f"{n}/{len(ps)}", 11.5, DOUX, False, "d", False))
            Z.append((x + 10, yy, w - 20, 22, "monde:region:" + tid))
            yy += 28
            col = max(1, int((w - 20) // 64))
            for i, e in enumerate(es):
                cx = x + 10 + (i % col) * 64
                cy = yy + (i // col) * 62
                if cy + 58 > y + h:
                    break
                sel = self.sel == e["id"]
                L.append(("rrect", cx + 2, cy, 58, 58, 8, (61, 220, 132, 40) if sel else (24, 36, 46, 255),
                          (61, 220, 132, 255) if sel else ((168, 140, 60, 200) if e["id"] in self.refuge else
                                                            (38, 56, 74, 255)), 1.3))
                self._vignette(L, e, cx + 31, cy + 40, 32)
                L.append(("texte", cx + 31, cy + 50, court(e["nom"], 54, 10), 10, TEXTE, False, "c", False))
                Z.append((cx + 2, cy, 58, 58, "monde:crea:" + e["id"]))
            yy += ((len(es) + col - 1) // col) * 62 + 6 if es else 0
        if not self.sel and yy + 40 < y + h:
            from .espace_scene import couper
            for i, l_ in enumerate(couper(t("monde.toucher"), w - 30, 11.5)[:3]):
                L.append(("texte", x + 14, yy + 12 + i * 15, l_, 11.5, DOUX, False, "g", False))

    def _vignette(self, L, e, cx, pieds, haut):
        al = e.get("album")
        if al:
            L.append(("imgt", al.image("assis", 0), cx, pieds, haut / max(1, al.ref), False, al.lisse, 1.0, 1.0,
                      0.0, 1.0))
        else:
            L.append(("ellipse", cx, pieds - haut / 2, haut / 3, haut / 2.4, rgb(COUL_TYPE[e["type"]])))

    def cmd_agrandir(self, tid):
        n = len([p for p in self.carte["parcelles"] if p["type"] == tid]) if self.carte else 0
        return f"mkdir biome/{tid}/parcelle_{n + 1}" if n else f"mkdir -p biome/{tid}/parcelle_1"

    def _fiche(self, L, Z, r, e):
        from .espace_scene import couper, court, lt
        x, y, w, h = r
        L.append(("rrect", x + 10, y + 10, 140, 28, 8, (15, 36, 22, 255), (61, 255, 124, 255), 1))
        L.append(("texte", x + 80, y + 24, t("monde.retour_liste"), 12.5, (61, 255, 124, 255), False, "c", False))
        Z.append((x + 10, y + 10, 140, 28, "monde:liste_retour"))
        L.append(("rrect", x + 14, y + 50, 96, 96, 10, (24, 36, 46, 255), (38, 56, 74, 255), 1.5))
        coul = RARETE.get(e.get("rarete"))
        if coul:
            L.append(("lueur", x + 62, y + 98, 46, coul + (90,)))
        self._vignette(L, e, x + 62, y + 136, 78)
        tx = x + 122
        L.append(("texte", tx, y + 64, court(e["nom"], w - 132, 15), 15, TEXTE, True, "g", False))
        L.append(("texte", tx, y + 86, court(e.get("sous", ""), w - 132, 11.5), 11.5, DOUX, False, "g", False))
        if e.get("rarete"):
            rr = e["rarete"].upper() + (" ✦ SHINY" if e.get("shiny") else "")
            c = coul or (154, 163, 173)
            L.append(("rrect", tx, y + 100, lt(rr, 10) + 14, 18, 4, None, c + (255,), 1.5))
            L.append(("texte", tx + 7, y + 109, rr, 10, c + (255,), True, "g", False))
        tid = e["type"]
        L.append(("rrect", tx, y + 124, lt(t("carte.biome." + tid), 11.5) + 34, 20, 10, rgb(COUL_TYPE[tid], 70),
                  rgb(COUL_TYPE[tid], 200), 1))
        L.append(("texte", tx + 8, y + 134, f"{EMOJI[tid]} {t('carte.biome.' + tid)}", 11.5, TEXTE, False, "g", False))
        yy = y + 160
        L.append(("rrect", x + 10, yy, w - 20, 54, 8, (24, 36, 46, 255), (38, 56, 74, 255), 1))
        if e["id"] in self.maison:
            L.append(("texte", x + 20, yy + 16, "✓ " + t("monde.habite", chemin=""), 12, VERT, False, "g", False))
            L.append(("texte", x + 20, yy + 36, f"~/terrain_terminagotchi/biome/{self.maison[e['id']]}/", 11, TEXTE,
                      False, "g", True))
        else:
            n = len([p for p in self.carte["parcelles"] if p["type"] == tid])
            L.append(("texte", x + 20, yy + 16, "⏳ " + court(t("monde.attend", region=t("carte.biome." + tid), n=n),
                                                             w - 44, 11.5), 11.5, (255, 216, 102, 255), False, "g", False))
            L.append(("texte", x + 20, yy + 36, self.cmd_agrandir(tid), 11.5, VERT, False, "g", True))
        yy += 66
        for l_ in couper(e.get("fiche", ""), w - 30, 12)[:max(0, int((y + h - yy - 10) // 16))]:
            L.append(("texte", x + 15, yy + 8, l_, 12, DOUX, False, "g", False))
            yy += 16

    # ------------------------------------------------ les clics
    def clic(self, a, x=None, y=None):
        """Un clic sur une zone du monde (a : l'action de la zone, ou None = à côté). Renvoie True s'il est pris."""
        if a is None or a in ("monde:vue", "monde:panneau"):
            if a == "monde:panneau":
                return True
            if self.sel:                       # un clic à côté : la liste revient
                self.sel = None
                return True
            if self.iso and a == "monde:vue":
                self.sortir()
                return True
            if a == "monde:vue" and x is not None and self.carte:
                h = self.hex_sous(x, y)
                if h and h["region"]:
                    self.isoler(h["region"])
            return a is not None
        if a.startswith("monde:crea:"):
            i = a.split(":", 2)[2]
            self.sel = None if self.sel == i else i
            cr = self.creas.get(i)
            if cr and cr.at and self.sel:
                cr.pop = self.t + .6
                self.eclat(self.pos_crea(cr)[:2], "coeur", 3)
            self.liste_ouverte = True
            return True
        if a == "monde:liste_retour":
            self.sel = None
            return True
        if a == "monde:liste":
            self.liste_ouverte = not self.liste_ouverte
            return True
        if a.startswith("monde:region:"):
            self.isoler(a.split(":", 2)[2])
            return True
        if a == "monde:sortir":
            self.sortir()
            return True
        if a == "monde:voir":
            self.iso = None
            self.tout_voir()
            return True
        if a in ("monde:plus", "monde:moins"):
            self.zoomer(1 if a == "monde:plus" else -1)
            return True
        if a.startswith("monde:objet:"):
            self.lancer([{"type": "touche", "cmd": "", "prio": 3, "chemin": a.split(":", 2)[2], "clic": True}])
            return True
        return False

    def echap(self):
        if self.sel:
            self.sel = None
            return True
        if self.iso:
            self.sortir()
            return True
        return False

    def zoomer(self, sens, x=None, y=None):
        self.but = None
        self.manuel = True
        f = 1.3 if sens > 0 else 1 / 1.3
        z = clamp(self.cam[2] * f, .5, 7)
        if x is not None and self.aire:
            wx, wy = self.monde_xy(x, y)
            self.cam[2] = z
            nx, ny = self.monde_xy(x, y)
            self.cam[0] += wx - nx
            self.cam[1] += wy - ny
        else:
            self.cam[2] = z

    def glisser(self, dx, dy):
        self.but = None
        self.manuel = True
        self.cam[0] -= dx / self.cam[2]
        self.cam[1] -= dy / self.cam[2]

    def isoler(self, tid):
        if not self.carte:
            return
        hs = [h for h in self.carte["hex"].values() if h["region"] == tid]
        if not hs:
            return
        self.iso = tid
        self.manuel = True
        self.ajuster(hs, True, zmax=3.4)
        if self.but:
            self.but[1] -= 26 / self.but[2]

    def sortir(self):
        self.iso = None
        self.tout_voir()

    def hex_sous(self, sx, sy):
        if not self.carte:
            return None
        wx, wy = self.monde_xy(sx, sy)
        for h in reversed(self.ordre):
            x, y = self.sommet(h)
            dx, dy = wx - x, wy - y
            if MD.hex_inside(dx, dy) or (abs(dx) <= HR and 0 < dy <= MD.hex_bottom(dx) + h["mur"]):
                return h
        return None

    # ------------------------------------------------ chaque effet (1 à 2 secondes)
    def _effet(self, L, e, age):
        z = self.cam[2]
        ty = e["type"]
        k = clamp(age / e["du"], 0, 1)
        fin = 1 - k
        pts = e.get("pts") or []
        p0 = self.ecran(*pts[0]) if pts else None

        def etiquette(txt, sx, sy, c=JAUNE, monte=True):
            yy = sy - (age * 26 if monte else 0)
            from .espace_scene import lt
            tw = lt(txt, 12.5) + 16
            L.append(("rrect", sx - tw / 2, yy - 11, tw, 22, 6, (5, 10, 15, int(220 * fin)), c[:3] + (int(255 * fin),), 1))
            L.append(("texte", sx, yy, txt, 12.5, c[:3] + (int(255 * fin),), True, "c", False))

        if ty == "jokers":
            for p in pts:
                sx, sy = self.ecran(*p)
                L.append(("lueur", sx, sy - 10 * z, 30 * z, (255, 236, 128, int(170 * math.sin(k * math.pi)))))
                L.append(("cercle", sx, sy - 10 * z, (12 + 6 * k) * z, (255, 224, 102, int(255 * fin)), 1.6))
            if p0:
                etiquette(f"✱ {e.get('n', len(pts))}", p0[0], p0[1] - 40 * z)
        elif ty == "dossier+":
            if age < .1:
                for x_, y_ in pts:
                    self.eclat((x_, y_ - 40), "pouf", 16)
            nom = (e.get("chemin") or "").split("/")[-1]
            if p0:
                etiquette("+ " + nom + "/", p0[0], p0[1] - 30 * z, VERT)
        elif ty == "dossier-":
            if age < .1 and pts:
                self.eclat(pts[0], "pouf", 20)
            if p0:
                etiquette("− " + (e.get("chemin") or "").split("/")[-1] + "/", p0[0], p0[1] - 30 * z, ROUGE)
        elif ty == "objet+":
            if not p0:
                return
            via = e.get("via")
            im = MD.decor(G.deco(e["chemin"].split("/")[-1], e.get("region") or "plante")[0])
            q = clamp(age / .8, 0, 1)
            if via == "touch" or via == "autre" or via == "mkdir":     # un rayon de lumière, puis l'objet tombe
                L.append(("rect", p0[0] - 5 * z, p0[1] - 140 * z, 10 * z, 140 * z,
                          (255, 246, 176, int(110 * math.sin(min(1, age / .6) * math.pi)))))
                yy = p0[1] - (1 - ease_back(q)) * 70 * z if q < 1 else p0[1]
            elif via == "ecrire":                 # les mots volent de la ligne de commande jusqu'au panneau
                ax, ay, _aw, _ah = self.aire
                for i in range(3):
                    qq = clamp(q * 1.3 - i * .12, 0, 1)
                    L.append(("rect", ax + 20 + (p0[0] - ax - 20) * ease(qq) - 8, ay + 20 + (p0[1] - ay - 50) * ease(qq),
                              16 * z / 2, 4 * z / 2, (95, 175, 255, int(255 * (1 - qq * .7)))))
                yy = p0[1]
            elif via == "messager":               # le pigeon pose ce qu'il rapporte
                bx = p0[0] + (1 - q) * 140 * z
                by = p0[1] - (1 - q) * 110 * z - 20 * z
                self._pigeon(L, bx, by, z, age)
                yy = p0[1] - (1 - q) * 40 * z
            else:                                 # une caisse, une photo… : l'objet arrive
                yy = p0[1] - (1 - ease_back(q)) * 50 * z
            if q > .05:
                L.append(("imgt", im, p0[0], yy + 2 * z, z * clamp(q * 1.5, .3, 1), False, False, 1.0, 1.0, 0.0, 1.0))
            if age > .8:
                etiquette(t("efx.nouveau"), p0[0], p0[1] - (im.h + 8) * z, VERT)
        elif ty == "objet-":
            if age < .1 and pts:
                self.eclat((pts[0][0], pts[0][1] - 8), "confetti", 26)
            if p0:
                etiquette(t("efx.pas_corbeille"), p0[0], p0[1] - 30 * z, ROUGE)
        elif ty in ("touche", "modifie"):
            if p0 and not e.get("clic"):
                etiquette("🕒 " + t("efx.heure") if ty == "touche" else "✎", p0[0], p0[1] - 34 * z, CYAN, False)
        elif ty in ("deplace", "renomme", "copie"):
            if len(pts) < 2:
                return
            (x0, y0), (x1, y1) = self.ecran(*pts[0]), self.ecran(*pts[1])
            q = clamp(age / 1.0, 0, 1)
            for i in range(12):                 # le pointillé jaune du trajet
                a_ = i / 12
                b_ = (i + .5) / 12
                L.append(("ligne", x0 + (x1 - x0) * a_, y0 + (y1 - y0) * a_ - math.sin(a_ * math.pi) * 50 * z,
                          x0 + (x1 - x0) * b_, y0 + (y1 - y0) * b_ - math.sin(b_ * math.pi) * 50 * z,
                          (255, 213, 79, int(220 * fin)), 1.5, None))
            im = MD.decor(G.deco(e["vers"].split("/")[-1], (e["vers"].split("/") + ["", ""])[1])[0])
            bx = x0 + (x1 - x0) * ease(q)
            by = y0 + (y1 - y0) * ease(q) - math.sin(q * math.pi) * 50 * z
            if ty == "copie":
                L.append(("lueur", x0, y0 - 10 * z, 40 * z, (255, 255, 255, int(220 * max(0, 1 - age * 3)))))
                L.append(("imgt", im, x0, y0 + 2 * z, z, False, False, 1.0, 1.0, 0.0, 1.0))
            if q < 1 or ty != "copie":
                L.append(("imgt", im, bx, by + 2 * z, z, False, False, 1.0, 1.0, 0.0, 1.0))
            if ty == "renomme":
                etiquette(e["de"].split("/")[-1] + " → " + e["vers"].split("/")[-1], x1, y1 - 34 * z, JAUNE, False)
            elif ty == "copie":
                etiquette("⧉ " + t("efx.copie"), x1, y1 - 34 * z, CYAN)
        elif ty == "ecrit":
            if not p0:
                return
            ax, ay, _aw, _ah = self.aire
            if e.get("mode") == ">" and age < .6:     # un seul > efface d'abord : les anciennes lignes s'envolent
                for i in range(3):
                    L.append(("rect", p0[0] - 8 * z + i * 3, p0[1] - 20 * z - age * 120 - i * 10, 16 * z / 2, 2.5 * z / 1.5,
                              (255, 95, 109, int(255 * (1 - age / .6)))))
            q = clamp((age - (.4 if e.get("mode") == ">" else 0)) / .7, 0, 1)
            L.append(("rect", ax + 20 + (p0[0] - ax - 20) * ease(q) - 8, ay + 20 + (p0[1] - 20 * z - ay - 20) * ease(q),
                      16, 4, (95, 175, 255, int(255 * (1 - q * .5)))))
            etiquette(("» " + t("efx.ajoute")) if e.get("mode") == ">>" else ("> " + t("efx.efface")), p0[0],
                      p0[1] - 40 * z, (95, 175, 255, 255) if e.get("mode") == ">>" else ROUGE, False)
        elif ty == "droits":
            if not p0:
                return
            av, ap = e.get("avant", 0), e.get("apres", 0)
            q = clamp(age / .5, 0, 1)
            rx, ry = 30 * z, 34 * z
            cy = p0[1] - 16 * z - (1 - ease_back(q)) * 40 * z
            L.append(("ellipse", p0[0], cy, rx, ry, (200, 230, 255, int(50 * fin + 20))))
            L.append(("cercle", p0[0], cy, rx, (220, 240, 255, int(200 * fin + 40)), 1.5))
            for i, (bit, nom) in enumerate(((0o200, "🙂"), (0o020, "👥"), (0o002, "🌍"))):
                ouvert = bool((ap if age > .7 else av) & bit)
                cx = p0[0] + (i - 1) * 22 * z
                self._cadenas(L, cx, p0[1] - 58 * z, 6 * z, VERT if ouvert else ROUGE, ouvert)
                L.append(("texte", cx, p0[1] - 72 * z, nom, 9 * z / 1.4 + 3, TEXTE, False, "c", False))
        elif ty == "refus":
            if not p0:
                ax, ay, aw, ah = self.aire
                p0 = (ax + aw / 2, ay + ah / 2)
            ra = e.get("raison")
            b = abs(math.sin(age * 9)) * 14 * z * fin
            if ra == "droits":
                self._cadenas(L, p0[0], p0[1] - 30 * z - b, 8 * z, ROUGE, False)
                L.append(("cercle", p0[0], p0[1] - 16 * z, 30 * z, (220, 240, 255, int(160 * fin)), 1.5))
            elif ra == "pas_vide":
                etiquette(t("efx.pas_vide"), p0[0] + math.sin(age * 40) * 4 * fin, p0[1] - 30 * z, JAUNE, False)
            elif ra == "existe":
                etiquette(t("efx.existe"), p0[0], p0[1] - 34 * z, JAUNE, False)
            else:
                L.append(("texte", p0[0], p0[1] - 30 * z - b, "?", 26 * z / 1.6 + 8, (255, 95, 109, int(255 * fin)), True,
                          "c", False))
        elif ty == "cd":
            if len(pts) < 2:
                return
            (x0, y0), (x1, y1) = self.ecran(*pts[0]), self.ecran(*pts[1])
            q = ease(clamp(age / .9, 0, 1))
            bx, by = x0 + (x1 - x0) * q, y0 + (y1 - y0) * q - math.sin(q * math.pi) * 60 * z
            L.append(("lueur", bx, by, 22 * z, (255, 213, 79, 120)))
            L.append(("ellipse", bx, by, 5 * z, 5 * z, JAUNE))
            L.append(("cercle", bx, by, (11 + 3 * math.sin(age * 8)) * z, JAUNE, 1.6))
            if age > .9:
                etiquette("◉ " + t("efx.ici"), x1, y1 - 28 * z, JAUNE, False)
        elif ty == "pwd":
            if not p0:
                return
            parts = ["~", "terrain_terminagotchi"] + [x for x in (e.get("chemin") or "").split("/") if x]
            parts = parts[-4:]
            from .espace_scene import lt
            tot = sum(lt(x, 12) + 26 for x in parts)
            xx = p0[0] - tot / 2
            for i, nom in enumerate(parts):
                q = clamp((age - i * .15) / .3, 0, 1)
                if q <= 0:
                    break
                tw = lt(nom, 12) + 14
                L.append(("rrect", xx, p0[1] - 60 * z - 11, tw, 22, 6, (5, 10, 15, int(230 * q * fin + 20)),
                          (77, 208, 225, int(255 * q * fin)), 1))
                L.append(("texte", xx + tw / 2, p0[1] - 60 * z, nom, 12, (77, 208, 225, int(255 * q * fin)), False,
                          "c", True))
                xx += tw
                if i < len(parts) - 1:
                    L.append(("texte", xx + 6, p0[1] - 60 * z, "/", 13, (178, 132, 255, int(255 * q * fin)), True,
                              "c", True))
                    xx += 12
        elif ty == "ls":
            h = self.hex_de(e.get("chemin") or "")
            cible = []
            if h:
                p = self.carte["par"].get(h["parcelle"])
                ch = e.get("chemin") or ""
                if p and ch.count("/") >= 2:
                    cible = [self.sommet(self.carte["hex"][(p["centre"][0] + v["off"][0], p["centre"][1] + v["off"][1])])
                             for v in p["poses"].values()]
                else:
                    ty_ = ch.split("/")[1] if ch.count("/") >= 1 else None
                    cible = [self.sommet(self.carte["hex"][tuple(x["centre"])]) for x in self.carte["parcelles"]
                             if (ty_ is None or x["type"] == ty_)]
            for i, pt in enumerate(cible[:16]):     # un projecteur sur chaque élément, l'un après l'autre
                q = clamp((age - i * .1) / .5, 0, 1)
                if 0 < q < 1:
                    sx, sy = self.ecran(*pt)
                    L.append(("lueur", sx, sy - 6 * z, 28 * z, (255, 250, 210, int(150 * math.sin(q * math.pi)))))
            if e.get("caches") and p0:            # ls -a : le rideau violet s'ouvre sur ce qui est caché
                w_ = 40 * z * (1 - min(1, age / .8))
                L.append(("rect", p0[0] - 40 * z, p0[1] - 60 * z, w_, 50 * z, (120, 70, 200, int(200 * fin))))
                L.append(("rect", p0[0] + 40 * z - w_, p0[1] - 60 * z, w_, 50 * z, (120, 70, 200, int(200 * fin))))
                etiquette("👁 " + t("efx.caches"), p0[0], p0[1] - 70 * z, VIOLET, False)
            elif p0:
                etiquette(f"ls · {e.get('n', len(cible))}", p0[0], p0[1] - 40 * z, (255, 250, 210, 255), False)
        elif ty == "find":
            if not p0:
                return
            c0 = self.ecran(*self.point_de(e.get("chemin") or "biome"))
            rmax = 260 * z
            L.append(("cercle", c0[0], c0[1], rmax * k + 5, (77, 208, 225, int(220 * fin)), 2))
            for p in pts if e.get("n") else []:
                sx, sy = self.ecran(*p)
                if math.hypot(sx - c0[0], sy - c0[1]) <= rmax * k + 5:
                    L.append(("rect", sx - 1.5, sy - 60 * z, 3, 50 * z, (77, 208, 225, int(200 * fin))))
                    L.append(("lueur", sx, sy - 6 * z, 18 * z, (77, 208, 225, int(160 * fin))))
            etiquette(t("efx.trouves", n=e.get("n", 0)) if e.get("n") else t("efx.rien_trouve"), c0[0], c0[1] - 50 * z,
                      CYAN, False)
        elif ty == "lire":                         # le parchemin se déroule
            if not p0:
                return
            q = clamp(age / .6, 0, 1)
            w_, h_ = 150, 18 + 52 * ease(q)
            bx, by = p0[0] - w_ / 2, p0[1] - 50 * z - h_
            L.append(("rrect", bx, by, w_, h_, 4, (243, 226, 184, int(255 * fin + 40) if k < 1 else 0), (123, 85, 52, 255), 1))
            for i, l_ in enumerate(e.get("lignes", [])[:3]):
                if 18 + i * 16 < h_:
                    L.append(("texte", bx + 8, by + 14 + i * 16, l_[:22], 11, (59, 36, 20, int(255 * fin)), False, "g", True))
        elif ty == "groupe":
            if age < .1:
                for p in pts[:6]:
                    self.eclat(p, "confetti" if e.get("sorte", "").endswith("-") else "pouf", 10)
            if p0:
                signe = "−" if e.get("sorte", "").endswith("-") else "+"
                etiquette(f"{signe} {e.get('n', 0)}", p0[0], p0[1] - 40 * z, ROUGE if signe == "−" else VERT)
        elif ty == "lucioles":
            if not p0:
                return
            n = 5
            for i in range(n):
                a_ = self.t * 1.4 + i * 2 * math.pi / n
                fx = p0[0] + math.cos(a_) * 34 * z
                fy = p0[1] - 40 * z + math.sin(a_ * 1.3) * 14 * z
                if e.get("quoi") == "eteint" and i == 0 and e.get("ok"):
                    fy += age * age * 60
                    L.append(("texte", fx + 8, fy - 8, "z Z", 10, (255, 255, 255, int(255 * fin)), False, "g", False))
                if e.get("quoi") == "part" and i == 0:
                    fx += age * 140 * z
                    fy -= age * 80 * z
                L.append(("lueur", fx, fy, 9 * z, (217, 255, 107, int(200 * fin))))
                L.append(("ellipse", fx, fy, 1.6 * z, 1.6 * z, (240, 255, 180, int(255 * fin))))
            if not e.get("ok"):
                etiquette(t("efx.aucune_luciole"), p0[0], p0[1] - 70 * z, JAUNE, False)
        elif ty == "messager":
            if len(pts) < 2:
                return
            (x0, y0), (x1, y1) = self.ecran(*pts[0]), self.ecran(*pts[1])
            q = age / e["du"]
            qq = q * 2 if q < .5 else 2 - q * 2
            bx, by = x0 + (x1 - x0) * ease(qq), y0 - 40 * z + (y1 - y0) * ease(qq) - math.sin(qq * math.pi) * 40 * z
            self._pigeon(L, bx, by, z, age)
            if q > .5:
                etiquette(t("efx.pong") if e.get("ok") else "? ? ?", x0, y0 - 70 * z, VERT if e.get("ok") else ROUGE,
                          False)
        elif ty == "photo":
            ax, ay, aw, ah = self.aire
            if age < .3:
                L.append(("rect", ax, ay, aw, ah, (255, 255, 255, int(220 * (1 - age / .3)))))
            if p0:
                etiquette("📸 " + t("efx.photo"), p0[0], p0[1] - 60 * z, (255, 255, 255, 255), False)
        elif ty == "empreinte":
            if not p0:
                return
            for i in range(5):
                L.append(("cercle", p0[0], p0[1] - 24 * z, (3 + i * 3) * z * min(1, age / .4), (178, 132, 255,
                                                                                               int(220 * fin)), 1.3))
            etiquette("🔏 " + e.get("cmd", ""), p0[0], p0[1] - 54 * z, VIOLET, False)
        elif ty == "tuyau":
            if not p0:
                return
            et = e.get("etapes", [])
            from .espace_scene import lt
            tot = sum(lt(x, 11) + 30 for x in et)
            xx = p0[0] - tot / 2
            yy = p0[1] - 80 * z
            L.append(("rrect", xx - 8, yy - 16, tot + 16, 32, 8, (20, 12, 36, int(230 * fin)), (178, 132, 255, int(255 * fin)), 1))
            for i, c in enumerate(et):
                tw = lt(c, 11) + 14
                on = int(age * 4) % max(1, len(et)) == i
                L.append(("rrect", xx, yy - 10, tw, 20, 6, (178, 132, 255, int((140 if on else 60) * fin)), None, 0))
                L.append(("texte", xx + tw / 2, yy, c, 11, (255, 255, 255, int(255 * fin)), True, "c", True))
                xx += tw
                if i < len(et) - 1:
                    L.append(("texte", xx + 8, yy, "|", 12, (178, 132, 255, int(255 * fin)), True, "c", True))
                    xx += 16

    def _cadenas(self, L, cx, cy, r, c, ouvert):
        a = c[3] if len(c) > 3 else 255
        L.append(("rrect", cx - r, cy - r * .2, r * 2, r * 1.5, r * .3, c[:3] + (a,), None, 0))
        dx = r * .5 if ouvert else 0
        L.append(("cercle", cx + dx, cy - r * .3, r * .6, c[:3] + (a,), max(1.0, r * .3)))

    def _pigeon(self, L, x, y, z, age):
        f = math.sin(age * 18)
        L.append(("ellipse", x, y, 6 * z, 3.5 * z, (240, 240, 245, 255)))
        L.append(("ellipse", x + 5 * z, y - 2 * z, 2.5 * z, 2.5 * z, (220, 220, 230, 255)))
        L.append(("poly", [(x - 2 * z, y - z), (x - 9 * z, y - 7 * z * f), (x + 2 * z, y - 2 * z)], (200, 205, 215, 255)))
        L.append(("rect", x + 7 * z, y - 2.5 * z, 2 * z, z, (255, 160, 60, 255)))
