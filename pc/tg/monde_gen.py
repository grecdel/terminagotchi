"""Le monde des biomes : la GÉNÉRATION COMMUNE (le relief, la disposition des régions, les chemins et les ponts).

Porté du prototype web « Monde Terminagotchi » v4 (26 octobre, validé par le propriétaire), rendu déterministe :
même règle dans Monde.kt (Android) et site/src/monde.js (le site), vecteurs communs donnees/monde/vecteurs.json
(pc/outils/test_monde.py, tests/jvm/Monde.kt, site/test/test.mjs). Les hauteurs sont arrondies au millième et les
scores de la disposition au millionième (floor(x + 0,5)) : les trois langages donnent exactement le même monde.

Le monde dessine le VRAI terrain de l'enfant (lecture seule) :
    biome/<type>/                   une région (feu, eau, glace, plante, roche, ciel, ombre, machine, poison)
    biome/<type>/parcelle_<n>/      une parcelle = une « fleur » de 19 hexagones = un dossier
    biome/<type>/parcelle_<n>/x.y   un objet posé sur la parcelle (rose.fleur → des fleurs, chene.arbre → un chêne)
Une créature par parcelle (biomes.json « parcelle ») : l'équipe (le guide d'abord) s'installe dans la région du type
de sa variante ; celles qui n'ont pas de place attendent au refuge (personne n'est perdu).
"""
import math
import os
import re

TYPES = ("feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")
MAX_PARCELLES = 8          # biomes.json « parcelles_max_absolu »
MAX_OBJETS = 18            # objets dessinés par parcelle (au-delà : « + n »)
HR, TILT, HZ = 14, 0.62, 5
SQ3 = math.sqrt(3)
HH = HR * math.sin(math.pi / 3) * TILT
M32 = 0xFFFFFFFF

FLOWER = [(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q) + abs(r) + abs(q + r) <= 4]
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
DIR_EDGE = ((0, 1), (5, 0), (4, 5), (3, 4), (2, 3), (1, 2))
SCEN_BLOCK = {"chene", "sapin", "sapin_neige", "bouleau", "cerisier", "rocher", "rocher_volc", "tombe", "tuyau",
              "engrenage", "cristal", "colonne"}
LIQUIDES = {"eau", "lave", "toxique"}
AQUA_DECO = {"corail", "algues", "bulles", "roseau", "coquillage"}
LA, LB = (5, -2), (2, 3)
MN6 = ((1, 0), (-1, 0), (0, 1), (0, -1), (-1, 1), (1, -1))
ANG = {"roche": 0, "feu": 48, "machine": 100, "ombre": 150, "poison": 192, "eau": 236, "glace": 282, "ciel": 322}
ORDRE = ("plante", "roche", "feu", "machine", "ombre", "poison", "eau", "glace", "ciel")
_PARCELLE = re.compile(r"parcelle[_-]?(\d+)", re.I)


# ---------------------------------------------------------------- hasard reproductible (FNV-1a, mulberry32)
def hachage(s):
    """FNV-1a 32 bits sur les unités UTF-16 (comme String.charCodeAt en JavaScript et Char en Kotlin)."""
    h = 2166136261
    b = str(s).encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 16777619) & M32
    return h


def _imul(a, b):
    return (a * b) & M32


def hasard(graine):
    """mulberry32 : une suite de nombres dans [0, 1[ (la même dans les trois langages)."""
    a = [graine & M32]

    def r():
        a[0] = (a[0] + 0x6D2B79F5) & M32
        x = a[0]
        t = _imul(x ^ (x >> 15), 1 | x)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296
    return r


def rnd(s):
    return hasard(hachage(s))()


def arrondi(x, n=1000):
    """floor(x·n + 0,5)/n : le même arrondi en Python, Kotlin et JavaScript (pas l'arrondi « bancaire »)."""
    return math.floor(x * n + 0.5) / n


def melanger(xs, r):
    """Fisher-Yates avec r (remplace le « sort(() => r() - .5) » du prototype, qui dépend du moteur)."""
    xs = list(xs)
    for i in range(len(xs) - 1, 0, -1):
        j = int(r() * (i + 1))
        xs[i], xs[j] = xs[j], xs[i]
    return xs


def choisir(xs, r):
    return xs[int(r() * len(xs))]


def anneau(q, r):
    return (abs(q) + abs(r) + abs(q + r)) // 2


# ---------------------------------------------------------------- une parcelle : fleur de 19 hexagones
def gen_parcelle(tid, nom, volcan=False, lave_dir=0):
    """Le relief d'une parcelle : {"q,r": {kind, h, v, d, …}} (q, r : décalage depuis le centre)."""
    r = hasard(hachage(tid + ":" + nom))
    out = {}
    pool = r() < .6
    s1 = r() * 6
    s2 = r() * 6
    ring2, ring1 = [], []
    for q, r_ in FLOWER:
        d = anneau(q, r_)
        k = f"{q},{r_}"
        kind, h, extra = "herbe", 2.0, {}
        if tid == "feu":
            if volcan:
                dq, dr = DIRS[lave_dir]
                ch1 = q == dq and r_ == dr
                ch2 = q == 2 * dq and r_ == 2 * dr
                if d == 0:
                    kind, h, extra = "lave", 8.2, {"crater": 1, "flow": 0}
                elif d == 1:
                    kind = "lave" if ch1 else "cone"
                    h = 8.4 if ch1 else 9.8 + ((q * 3 + r_) & 1) * .8
                    if ch1:
                        extra["flow"] = 1
                else:
                    if ch2:
                        kind = "lave"
                    else:
                        kind = "cendre" if r() < .35 else "cone"
                    h = 6.4 if ch2 else 6.8 + r() * .5
                    if ch2:
                        extra["flow"] = 2
            else:
                if pool and d == 0:
                    kind = "lave"
                else:
                    kind = "cendre" if r() < .25 else "basalte"
                h = 1.5 if kind == "lave" else 2.2 + r() * .6
                if kind == "lave":
                    extra["flow"] = 0
        elif tid == "eau":
            kind = "sable" if (not pool and d == 0) else "eau"
            h = 1.3 if kind == "sable" else .55
        elif tid == "glace":
            cliff = ((q * 2 + r_ * 3 + int(math.floor(s1 + .5))) % 5 + 5) % 5 == 0 and d > 0
            kind = "glace" if (pool and d == 0) else ("glace" if cliff else "neige")
            h = 2.4 if (pool and d == 0) else (4.9 if cliff else 3 + (.4 if d == 1 else 0))
        elif tid == "plante":
            if r() < .25:
                kind = "fleurs"
            elif r() < .4:
                kind = "sombre"
            else:
                kind = "herbe"
            h = 2 + .55 * math.sin(q * 1.3 + s1) + .45 * math.cos(r_ * 1.1 + s2)
        elif tid == "roche":
            trail = (q == 1 and r_ == 0) or (q == 2 and r_ == -1) or (q == 1 and r_ == -1)
            if d == 0:
                kind, h = "neige", 9.8
            elif d == 1:
                h = 7.2 if trail else 6.8 + r() * 1.8
                kind = "neige" if h > 7.9 else "pierre"
            else:
                h = 4.8 if trail else 3.6 + r() * 1.6
                if h > 4.6:
                    kind = "pierre"
                else:
                    kind = "gres" if r() < .5 else "sable"
        elif tid == "ciel":
            if d == 0:
                sector = 0
            else:
                a = math.atan2(r_ + q / 2, q * SQ3 / 2)
                sector = 1 + int(math.floor(arrondi((a + math.pi) / (math.pi * 2), 1e6) * 3)) % 3
            h = (6.2, 4.4, 7.4, 5.4)[sector] + (r() - .5) * .5
            kind = "orage" if r() < .2 else "nuage"
            extra["float"] = 1
        elif tid == "ombre":
            if d == 0:
                kind = "crypte"
            else:
                kind = "violette" if r() < .35 else "dalle"
            h = .7 if d == 0 else 2 + (0 if d == 1 else .3)
        elif tid == "machine":
            if r() < .25:
                kind = "grille"
            elif r() < .15:
                kind = "rouille"
            else:
                kind = "metal"
            h = 3 + (.6 if (d == 1 and r() < .35) else 0)
            extra["machine"] = 1
        elif tid == "poison":
            toxique = (pool and d == 0) or (d == 1 and r() < .25)
            kind = "toxique" if toxique else "vase"
            h = .65 if kind == "toxique" else 1.2 + r() * .3
        cell = {"kind": kind, "h": arrondi(h), "v": int(r() * 4), "d": d}
        cell.update(extra)
        out[k] = cell
        if d == 2:
            ring2.append(k)
        if d == 1:
            ring1.append(k)

    def scen(cands, keys, n):
        for k in melanger(cands, r)[:n]:
            out[k]["scen"] = {"k": choisir(keys, r), "s": arrondi(.85 + r() * .45)}
    if tid == "plante":
        scen(ring2, ["chene", "sapin", "bouleau", "chene", "cerisier"], 5)
    if tid == "glace":
        scen(ring2, ["sapin_neige", "cristal"], 2)
    if tid == "roche":
        scen(ring2, ["rocher"], 2)
    if tid == "machine":
        scen(ring2, ["tuyau", "engrenage"], 2)
    if tid == "poison":
        scen([k for k in ring2 if out[k]["kind"] == "vase"], ["roseau", "champi_tox"], 3)
    if tid == "eau":
        scen(ring1, ["corail", "algues"], 2)
    if tid == "ombre":
        for k in melanger(ring2, r)[:2]:
            out[k]["kind"] = "fleche"
            out[k]["h"] = arrondi(8.5 + r() * 2)
            out[k]["block"] = 1
        scen([k for k in ring2 if out[k]["kind"] != "fleche"], ["tombe"], 1)
    if tid == "feu" and not volcan:
        scen(ring2, ["braises", "rocher_volc"], 2)
    return out


# ---------------------------------------------------------------- les objets (fichiers) → décor
FLEURS = {"rose": "#ff3d5a", "tulipe": "#ff8a3d", "tournesol": "#ffd23f", "marguerite": "#ffffff",
          "lavande": "#a77bff", "bleuet": "#4f8cff", "coquelicot": "#ff2a2a", "violette": "#8a4fff", "lys": "#ffe9f2"}
MOTS = (("geyser", "geyser", 1), ("braise", "braises", 0), ("corail", "corail", 0), ("coquill", "coquillage", 0),
        ("algue", "algues", 0), ("bonhomme", "bonhomme", 1), ("colonne", "colonne", 1), ("ruine", "colonne", 1),
        ("paratonnerre", "paratonnerre", 1), ("etoile", "etoile", 0), ("eolienne", "eolienne", 1),
        ("tombe", "tombe", 1), ("rune", "rune", 1), ("engrenage", "engrenage", 1), ("rouage", "engrenage", 1),
        ("tuyau", "tuyau", 1), ("neon", "neon", 1), ("lampe", "neon", 1), ("roseau", "roseau", 0),
        ("bulle", "bulles", 0), ("cristal", "cristal", 1), ("cactus", "cactus", 1))
_ACCENTS = str.maketrans("àâäáãåçéèêëíìîïñóòôöõúùûüýÿœæ", "aaaaaaceeeeiiiinooooouuuuyyoa")


def _norm(s):
    return str(s).lower().translate(_ACCENTS)


def deco(nom, tid):
    """L'objet dessiné pour un fichier : (clé du dessin, bloque le passage)."""
    i = nom.rfind(".")
    base = _norm(nom[:i] if i > 0 else nom)
    ext = _norm(nom[i + 1:] if i > 0 else "")

    def a(*ms):
        return any(m in base for m in ms)
    for m, k, b in MOTS:
        if m in base:
            return k, b
    if ext == "arbre":
        if a("sapin", "pin"):
            return ("sapin_neige" if tid == "glace" else "sapin"), 1
        if a("bouleau"):
            return "bouleau", 1
        if a("cerisier", "sakura"):
            return "cerisier", 1
        if a("palmier", "coco"):
            return "palmier", 1
        return "chene", 1
    if ext == "fleur":
        col = None
        for k, c in FLEURS.items():
            if k in base:
                col = c
        if not col:
            col = "h%d" % (hachage(base) % 360)
        return "fleur:" + col, 0
    if ext in ("pierre", "rocher"):
        if a("galet"):
            return "galet", 0
        return ("rocher_volc" if tid == "feu" else "rocher"), 1
    if ext == "champignon":
        return {"ombre": "champi_lum", "poison": "champi_tox"}.get(tid, "champignon"), 0
    if ext in ("plante", "buisson"):
        return "buisson", 0
    if ext in ("tar", "gz", "tgz", "zip"):
        return "caisse", 0
    if ext in ("sh", "py", "ps1"):
        return "parchemin_machine", 0
    if ext in ("txt", "md", "log", "csv"):
        return "parchemin", 0
    return "panneau", 0


# ---------------------------------------------------------------- lire le vrai terrain (lecture seule)
def _cle_parcelle(nom):
    m = _PARCELLE.fullmatch(nom)
    return (0, int(m.group(1)), nom) if m else (1, 0, nom.lower())


def lire_terrain(racine):
    """Le monde du terrain : {type: [{"nom": parcelle, "objets": [noms], "caches": n, "plus": n}]} (ordre de TYPES).
    Seuls biome/<type>/ et leurs sous-dossiers ; au plus MAX_PARCELLES parcelles (les autres : « plus »)."""
    out = {}
    b = os.path.join(str(racine), "biome")
    for tid in TYPES:
        d = os.path.join(b, tid)
        if not os.path.isdir(d):
            continue
        try:
            noms = [e.name for e in os.scandir(d) if e.is_dir(follow_symlinks=False) and not e.name.startswith(".")]
        except OSError:
            continue
        parcelles = []
        for n in sorted(noms, key=_cle_parcelle)[:MAX_PARCELLES]:
            try:
                fs = sorted(e.name for e in os.scandir(os.path.join(d, n)) if not e.is_dir(follow_symlinks=False))
            except OSError:
                fs = []
            vis = [f for f in fs if not f.startswith(".")]
            parcelles.append({"nom": n, "objets": vis[:MAX_OBJETS], "plus": max(0, len(vis) - MAX_OBJETS),
                              "caches": len(fs) - len(vis)})
        out[tid] = parcelles
    return out


# ---------------------------------------------------------------- la disposition : une tache compacte par région
def _plan(q, r):
    return 1.5 * q, SQ3 * (r + q / 2)


def macro(m, n):
    return m * LA[0] + n * LB[0], m * LA[1] + n * LB[1]


def _ang_diff(a, b):
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def disposition(regions):
    """regions : {type: nombre de parcelles} → {type: [(m, n)]} (une case de la grille de fleurs par parcelle)."""
    occ = {}

    def P(m, n):
        return _plan(*macro(m, n))

    def ang(m, n):
        x, y = P(m, n)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def dist(m, n):
        x, y = P(m, n)
        return math.hypot(x, y) / 5

    def frontiere(cells):
        o = {}
        for x, y in cells:
            for dx, dy in MN6:
                k = (x + dx, y + dy)
                if k not in occ and k not in o:
                    o[k] = k
        return list(o.values())
    out = {}
    for tid in ORDRE:
        n = regions.get(tid, 0)
        if not n:
            continue
        pref = ANG.get(tid, 0)
        cells = []
        if not occ:
            cells.append((0, 0))
        else:
            best, bs = None, None
            for x, y in frontiere(list(occ.values())):
                s = arrondi(_ang_diff(ang(x, y), pref) * .08 + dist(x, y) * .9 + ((x * 7 + y * 13) & 3) * .001, 1e6)
                if bs is None or s < bs:
                    bs, best = s, (x, y)
            cells.append(best)
        occ[cells[0]] = cells[0]
        while len(cells) < n:
            cx = sum(P(*c)[0] for c in cells) / len(cells)
            cy = sum(P(*c)[1] for c in cells) / len(cells)
            best, bs = None, None
            for x, y in frontiere(cells):
                px, py = P(x, y)
                s = arrondi(dist(x, y) * .7 + (0 if tid == "plante" else _ang_diff(ang(x, y), pref) * .03)
                            + math.hypot(px - cx, py - cy) / 5 * 1.3 + ((x * 7 + y * 13) & 3) * .001, 1e6)
                if bs is None or s < bs:
                    bs, best = s, (x, y)
            if best is None:
                break
            cells.append(best)
            occ[best] = best
        out[tid] = cells
    return out


# ---------------------------------------------------------------- le monde entier
def construire(terrain):
    """Le monde : {"parcelles": [...], "hex": {(q, r): hex}, "cordes": [(clé a, clé b)]} depuis lire_terrain()."""
    lay = disposition({tid: len(ps) for tid, ps in terrain.items()})
    parcelles = []
    volcan_fait = False
    for tid in TYPES:
        for i, p in enumerate(terrain.get(tid, [])):
            volcan = tid == "feu" and not volcan_fait
            volcan_fait = volcan_fait or volcan
            m = lay[tid][i] if i < len(lay.get(tid, [])) else lay[tid][-1]
            parcelles.append({"type": tid, "nom": p["nom"], "id": tid + "/" + p["nom"], "m": m, "centre": macro(*m),
                              "volcan": volcan, "gen": gen_parcelle(tid, p["nom"], volcan, 0),
                              "objets": list(p.get("objets", [])), "plus": p.get("plus", 0),
                              "caches": p.get("caches", 0)})
    hexs = {}
    for p in parcelles:
        cq, cr = p["centre"]
        for dq, dr in FLOWER:
            g = p["gen"][f"{dq},{dr}"]
            h = {"q": cq + dq, "r": cr + dr, "cle": f"{p['id']}:{dq},{dr}", "off": (dq, dr), "parcelle": p["id"],
                 "region": p["type"], "kind": g["kind"], "h": g["h"], "v": g["v"], "d": g["d"],
                 "flow": g.get("flow"), "crater": g.get("crater", 0), "float": g.get("float", 0),
                 "machine": g.get("machine", 0), "block": bool(g.get("block")), "scen": g.get("scen"),
                 "between": None, "bridge": False}
            if h["scen"] and h["scen"]["k"] in SCEN_BLOCK:
                h["block"] = True
            hexs[(h["q"], h["r"])] = h
    par = {p["id"]: p for p in parcelles}
    # les contreforts du volcan
    vp = next((p for p in parcelles if p["volcan"]), None)
    if vp:
        vq, vr = vp["centre"]
        dq, dr = DIRS[0]
        for h in hexs.values():
            if h["region"] != "feu" or h["parcelle"] == vp["id"]:
                continue
            d = anneau(h["q"] - vq, h["r"] - vr)
            pied = arrondi(5.6 - (d - 3) * 1.05)
            if pied > h["h"]:
                h["h"] = pied
                h["kind"] = "cendre" if rnd(h["cle"]) < .35 else "cone"
                h["scen"] = None
                h["block"] = False
            for k in range(3, 8):
                if h["q"] == vq + dq * k and h["r"] == vr + dr * k:
                    h["kind"] = "lave"
                    h["flow"] = k
                    h["h"] = arrondi(max(1.3, h["h"] - .35))
    # les rivages
    for h in hexs.values():
        if h["region"] != "eau" or h["kind"] != "eau" or h["d"] < 2:
            continue
        if rnd(h["cle"] + "s") < .5 and any(
                (hexs.get((h["q"] + a, h["r"] + b)) or {}).get("region") != "eau" for a, b in DIRS):
            h["kind"], h["h"] = "sable", 1.35
    # les chemins, escaliers et ponts entre deux régions voisines
    cordes = []
    fait = set()
    par_m = {p["m"]: p for p in parcelles}

    def ph(p):
        return [hexs[(p["centre"][0] + a, p["centre"][1] + b)] for a, b in FLOWER]

    def hd(h, c):
        return anneau(h["q"] - c[0], h["r"] - c[1])
    for p in parcelles:
        for a, b in MN6:
            o = par_m.get((p["m"][0] + a, p["m"][1] + b))
            if not o or o["type"] == p["type"]:
                continue
            cle = "-".join(sorted((p["id"], o["id"])))
            if cle in fait:
                continue
            fait.add(cle)
            oc, pc = o["centre"], p["centre"]
            cas = sorted((h for h in ph(p) if h["d"] == 2), key=lambda h: (hd(h, oc), abs(h["q"] - h["r"])))
            if not cas:
                continue
            ca = cas[0]
            cbs = sorted((x for x in (hexs.get((ca["q"] + x, ca["r"] + y)) for x, y in DIRS)
                          if x and x["parcelle"] == o["id"]), key=lambda h: hd(h, pc))
            if not cbs:
                continue
            cb = cbs[0]
            ta, tb = p["type"], o["type"]
            pont = ta in ("eau", "ciel") or tb in ("eau", "ciel") or ca["kind"] in LIQUIDES or cb["kind"] in LIQUIDES

            def interieur(c, pp, pcen):
                if pp["volcan"] or pp["type"] in ("eau", "ciel"):
                    return None
                ns = [x for x in (hexs.get((c["q"] + dx, c["r"] + dy)) for dx, dy in DIRS)
                      if x and x["parcelle"] == pp["id"] and x["d"] == 1 and x["region"] and x["kind"] != "fleche"]
                ns.sort(key=lambda x: (anneau(x["q"] - pcen[0], x["r"] - pcen[1]), abs(x["h"] - c["h"])))
                return ns[0] if ns else None
            raide = abs(ca["h"] - cb["h"]) > 1.4
            ia = interieur(ca, p, oc) if raide else None
            ib = interieur(cb, o, pc) if raide else None
            chaine = [x for x in (ia, ca, cb, ib) if x]
            h0 = 2 if (ia or ca)["kind"] == "fleche" else (ia or ca)["h"]
            h1 = 2 if (ib or cb)["kind"] == "fleche" else (ib or cb)["h"]
            ha = 2 if ca["kind"] == "fleche" else ca["h"]
            hb = 2 if cb["kind"] == "fleche" else cb["h"]
            for i, h in enumerate(chaine):
                h["h"] = arrondi(h0 + (h1 - h0) * (i + .5) / len(chaine))
                h["kind"] = "pont" if pont else ("escalier" if abs(ha - hb) > 1.4 else "chemin")
                if h is ca or h is cb:
                    h["region"] = None
                h["block"] = False
                h["scen"] = None
                if pont:
                    h["float"] = 0
                h["machine"] = 0
                h["bridge"] = pont
                h["between"] = [ta, tb]
            if pont:
                for i in range(len(chaine) - 1):
                    cordes.append((chaine[i]["cle"], chaine[i + 1]["cle"]))
    for h in hexs.values():
        h["base"] = arrondi(h["h"] - 1.1 if h["float"] else (h["h"] - .6 if h["machine"] else
                                                             (h["h"] - .35 if h["bridge"] else -1.5)))
        h["mur"] = max(1, int(math.floor((h["h"] - h["base"]) * HZ + .5)))
        h["pilier"] = int(math.floor((h["base"] + 1.5) * HZ + .5)) if h["machine"] else 0
    # les objets : chacun sur un hexagone libre de sa parcelle (le hasard dépend de son nom)
    for p in parcelles:
        pris = set()
        p["poses"] = {}
        for nom in p["objets"]:
            k, bloque = deco(nom, p["type"])
            cands = []
            for o in FLOWER:
                h = hexs[(p["centre"][0] + o[0], p["centre"][1] + o[1])]
                if (not h["region"] or h["block"] or h["scen"] or o in pris or h["crater"] or o == (0, 0)
                        or (h["kind"] in LIQUIDES and k not in AQUA_DECO)):
                    continue
                cands.append(o)
            if not cands:
                continue
            o = choisir(cands, hasard(hachage(p["id"] + "/" + nom)))
            pris.add(o)
            p["poses"][nom] = {"off": o, "k": k, "bloque": bool(bloque)}
    return {"parcelles": parcelles, "par": par, "hex": hexs, "cordes": cordes}


def place_creatures(monde, creatures):
    """creatures : [(id, type)] dans l'ordre de l'équipe (le guide d'abord) → ({id: parcelle}, [id au refuge])."""
    libres = {}
    for p in monde["parcelles"]:
        libres.setdefault(p["type"], []).append(p["id"])
    maison, refuge = {}, []
    for i, ty in creatures:
        if libres.get(ty):
            maison[i] = libres[ty].pop(0)
        else:
            refuge.append(i)
    return maison, refuge


def sol_xy(q, r):
    return HR * 1.5 * q, HR * SQ3 * (r + q / 2) * TILT


# ---------------------------------------------------------------- les vecteurs communs
def resume(monde):
    """Ce que les trois langages doivent donner exactement (la liste des hexagones et des cordes)."""
    hs = sorted(monde["hex"].values(), key=lambda h: (h["q"], h["r"]))
    return {"parcelles": [[p["id"], list(p["m"]), p["volcan"], {n: [list(v["off"]), v["k"], v["bloque"]]
                                                                for n, v in sorted(p["poses"].items())}]
                          for p in monde["parcelles"]],
            "hex": [[h["q"], h["r"], h["kind"], h["h"], h["v"], h["region"], h["mur"], h["pilier"],
                     (h["scen"] or {}).get("k"), h["block"]] for h in hs],
            "cordes": [list(c) for c in monde["cordes"]]}


def cas_vecteurs():
    return [
        {"plante": [{"nom": "parcelle_1", "objets": ["chene.arbre", "rose.fleur", "mot.txt"]}]},
        {"feu": [{"nom": "parcelle_1", "objets": ["geyser.pierre"]}, {"nom": "parcelle_2", "objets": []}],
         "eau": [{"nom": "parcelle_1", "objets": ["corail.plante", "coquillage.pierre"]}]},
        {t: [{"nom": f"parcelle_{i}", "objets": ["sapin.arbre", "cristal.pierre", f"truc{i}.txt"]}
             for i in range(1, 3)] for t in TYPES},
        {"ombre": [{"nom": "parcelle_1", "objets": ["tombe.pierre"]}, {"nom": "grotte", "objets": []}],
         "ciel": [{"nom": "parcelle_1", "objets": ["eolienne.metal", "étoile.pierre"]}],
         "roche": [{"nom": f"parcelle_{i}", "objets": []} for i in range(1, 6)]},
    ]


def vecteurs():
    out = {"hachage": [[s, hachage(s)] for s in ("", "feu:parcelle_1", "é✓", "plante/parcelle_1/rose.fleur")],
           "hasard": (lambda r: [r() for _ in range(5)])(hasard(42)),
           "deco": [[n, t, list(deco(n, t))] for n, t in (("rose.fleur", "plante"), ("sapin.arbre", "glace"),
                                                          ("Sapin.arbre", "plante"), ("galet.pierre", "eau"),
                                                          ("x.champignon", "ombre"), ("sac.tar.gz", "feu"),
                                                          ("geyser.pierre", "feu"), ("inconnu", "machine"),
                                                          ("ÉTOILE.pierre", "ciel"), ("jardin.sh", "plante"),
                                                          ("mot.txt", "plante"), ("bizarre.fleur", "plante"))],
           "mondes": []}
    for terrain in cas_vecteurs():
        m = construire(terrain)
        crs = [(f"c{i}", t) for i, t in enumerate(["plante", "feu", "feu", "feu", "eau", "glace", "ombre"])]
        maison, refuge = place_creatures(m, crs)
        out["mondes"].append({"terrain": terrain, "monde": resume(m), "maison": maison, "refuge": refuge})
    return out
