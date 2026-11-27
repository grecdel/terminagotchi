#!/usr/bin/env python3
"""Génère le bestiaire du jeu (150 espèces + les secrètes) pour le PC, l'appli Android et le site.

  python3 donnees/generer_bestiaire.py          (utilise Pillow)

Entrée :
  donnees/bestiaire2/bestiaire.json           les 150 espèces (assemblées par bestiaire2/assembler.py)
  donnees/bestiaire2/NN_famille.json          leurs fiches complètes (rareté, caractère, habitats)
  donnees/bestiaire2/images/                  les dessins : NNN_id_variante_{bebe,enfant,ado,adulte,ancien}.png
  donnees/secretes.json                       les espèces secrètes (#151 Abyssor, voir secretes.py)
  donnees/anciens_noms.json                   les noms de l'ancien bestiaire (pour convertir les vieilles sauvegardes)

Écrit :
  donnees/bestiaire.json                      (référence lisible)
  pc/tg/bestiaire.json                        (version PC)
  app/src/main/assets/bestiaire.json          (appli Android)
  site/src/bestiaire.js                       (site : sans les dessins par stade, pour rester léger)

Chaque espèce garde les champs historiques (sprite 16 px, sprite_grand 32 px, palettes, zone, stats…)
et gagne :
  "epreuves"  : les familles d'épreuves de dressage (commandes à apprendre) ;
  "variantes" : les formes dessinées (classique + habitats) avec leur chance d'apparition ;
  "dessins"   : {variante: {stade: {"l": lignes, "p": palette}}} pour enfant, ado, adulte, finale (= ancien),
                plus "petit" (16 px, adulte) pour les petites vignettes.
Tout est déterministe : relancer le script redonne exactement le même fichier.
"""
import colorsys
import json
import random
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
B2 = RACINE / "donnees" / "bestiaire2"
IMAGES = B2 / "images"

RARETES = ["commune", "peu commune", "rare", "légendaire"]
BASE_STATS = {"commune": 30, "peu commune": 42, "rare": 56, "légendaire": 75}
PROFONDEUR = {"commune": "", "peu commune": "/recoin", "rare": "/recoin/cachette", "légendaire": "/recoin/cachette/sanctuaire"}
FREQUENCE = {"commune": "souvent", "peu commune": "parfois", "rare": "rarement", "légendaire": "presque jamais"}
TAILLE_CM = {"petite": (25, 70), "moyenne": (70, 160), "grande": (160, 380), "colossale": (380, 1200)}
STADES_JEU = {"enfant": "enfant", "ado": "ado", "adulte": "adulte", "finale": "ancien"}   # stade du jeu → image
GRAND, PETIT = 32, 16
SYMBOLES = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+-=?@"

# nom, icône, stat favorite, zone (dossier du terrain de jeu), nom du lieu, commande qui l'attire, capacités
FAMILLES = [
    ("Démons", "😈", "Force", "volcan", "le volcan", "chmod",
     ["Flamme noire", "Pacte de braise", "Griffe infernale", "Regard ardent", "Bouclier de soufre"]),
    ("Élémentaires", "🌪", "Endurance", "sommets", "les sommets", "df",
     ["Tempête", "Mur de roche", "Vague de fond", "Éclair en chaîne", "Gel instantané"]),
    ("Morts-vivants", "💀", "Intelligence", "crypte", "la crypte", "ps",
     ["Cri d'outre-tombe", "Réveil des os", "Voile spectral", "Toucher glacé", "Malédiction"]),
    ("Bêtes monstrueuses", "🐺", "Force", "plaine", "la plaine sauvage", "free",
     ["Charge", "Hurlement", "Morsure d'acier", "Pistage", "Peau de cuir"]),
    ("Sylvestres", "🌳", "Endurance", "foret", "la forêt", "ls",
     ["Racines profondes", "Pollen endormant", "Écorce dure", "Floraison", "Ronces"]),
    ("Arthropodes", "🐞", "Agilité", "termitiere", "la termitière", "grep",
     ["Essaim", "Dard", "Carapace", "Toile collante", "Mue éclair"]),
    ("Abyssaux", "🦑", "Endurance", "abysses", "les abysses", "cat",
     ["Encre noire", "Lueur des profondeurs", "Pression abyssale", "Tourbillon", "Pince géante"]),
    ("Célestes", "☀", "Agilité", "nuages", "les nuages", "ping",
     ["Rayon d'étoile", "Aile de lumière", "Bénédiction", "Pluie d'astres", "Halo protecteur"]),
    ("Constructs", "⚙", "Intelligence", "ruines", "les ruines", "base64",
     ["Rune gravée", "Engrenage", "Poing de pierre", "Surcharge", "Réparation"]),
    ("Aberrations", "👁", "Intelligence", "faille", "la faille", "rev",
     ["Regard multiple", "Mutation", "Tentacule", "Distorsion", "Contagion"]),
]
FAM = {f[0]: f for f in FAMILLES}

MARQUES = [
    "une tache en forme de @ sur le dos", "un œil qui clignote en binaire", "une queue en forme de tilde ~",
    "des rayures comme un code-barres", "une petite cicatrice en forme de point-virgule", "un ventre qui affiche l'heure",
    "des oreilles légèrement pixelisées", "une étoile sur le front", "un grain de beauté en forme de #",
    "un ronronnement à 440 Hz", "une ombre qui a un pixel de retard", "des pattes de longueur différente",
    "un reflet arc-en-ciel sur le pelage", "une antenne qui capte la radio", "un hoquet en code Morse",
    "des yeux de deux couleurs", "une crête en forme d'accolade {", "des taches disposées comme une constellation",
    "un éternuement qui fait des étincelles", "une marque en forme de flèche →", "un museau qui sent le café",
    "une voix qui résonne comme dans une grotte", "des empreintes en forme de 0 et de 1", "une plume de pixel derrière l'oreille",
]
HUMEURS = ["joyeuse", "timide", "têtue", "curieuse", "paresseuse", "fougueuse", "rêveuse", "taquine", "calme",
           "bavarde", "gourmande", "courageuse"]


# ---------------------------------------------------------------- images → pixel art
def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def pixels(img, taille, couleurs):
    """Image détourée → lignes de symboles + palette (le point « . » = transparent)."""
    im = img.copy()
    im.thumbnail((taille, taille), Image.LANCZOS)
    alpha = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    if not alpha.getbbox():
        return [], {}
    fond = Image.new("RGB", im.size, (0, 0, 0))
    fond.paste(im.convert("RGB"), mask=alpha)
    q = fond.quantize(couleurs, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()
    lignes, utilises = [], {}
    for y in range(im.height):
        l = ""
        for x in range(im.width):
            if not alpha.getpixel((x, y)):
                l += "."
                continue
            i = q.getpixel((x, y))
            utilises.setdefault(i, SYMBOLES[len(utilises)])
            l += utilises[i]
        lignes.append(l)
    lignes = sans_poussieres(lignes)
    utilises = {i: c for i, c in utilises.items() if any(c in l for l in lignes)}
    while lignes and set(lignes[0]) == {"."}:
        lignes.pop(0)
    while lignes and set(lignes[-1]) == {"."}:
        lignes.pop()
    return lignes, {s: _hex(pal[3 * i:3 * i + 3]) for i, s in utilises.items()}


def sans_poussieres(lignes, rogner=True):
    """Efface les petits îlots de pixels détachés du corps (restes du détourage)."""
    h, w = len(lignes), max((len(l) for l in lignes), default=0)
    g = [list(l.ljust(w, ".")) for l in lignes]
    vu, groupes = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] == "." or (y, x) in vu:
                continue
            pile, groupe = [(y, x)], []
            vu.add((y, x))
            while pile:
                cy, cx = pile.pop()
                groupe.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and g[ny][nx] != "." and (ny, nx) not in vu:
                            vu.add((ny, nx))
                            pile.append((ny, nx))
            groupes.append(groupe)
    if not groupes:
        return lignes
    plus_grand = max(len(x) for x in groupes)
    for groupe in groupes:
        if len(groupe) < max(3, plus_grand * 0.04):
            for y, x in groupe:
                g[y][x] = "."
    lignes = ["".join(r) for r in g]
    cols = [x for x in range(w) if any(r[x] != "." for r in lignes)]
    if cols and rogner:
        lignes = [r[cols[0]:cols[-1] + 1] for r in lignes]
    return lignes


def decaler(palette, dec=0.5):
    """Palette shiny : même dessin, teinte tournée."""
    out = {}
    for k, h in palette.items():
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hh, l, s = colorsys.rgb_to_hls(r, g, b)
        r, g, b = colorsys.hls_to_rgb((hh + dec) % 1, l, min(1.0, s * 1.1))
        out[k] = _hex((int(r * 255), int(g * 255), int(b * 255)))
    return out


def ouvrir(nom):
    """L'image recadrée sur la créature, sans les poussières du détourage (qui fausseraient le cadrage)."""
    img = Image.open(IMAGES / f"{nom}.png").convert("RGBA")
    k = 4                                              # repérage sur une version réduite (rapide)
    a = img.getchannel("A").resize((max(1, img.width // k), max(1, img.height // k)), Image.BOX)
    grille = ["".join("#" if a.getpixel((x, y)) > 60 else "." for x in range(a.width)) for y in range(a.height)]
    propre = sans_poussieres(grille, rogner=False)
    pts = [(x, y) for y, l in enumerate(propre) for x, c in enumerate(l) if c != "."]
    if not pts:
        return img.crop(img.getbbox())
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    boite = (min(xs) * k, min(ys) * k, min(img.width, (max(xs) + 1) * k), min(img.height, (max(ys) + 1) * k))
    img = img.crop(boite)
    return img.crop(img.getbbox())


def variantes_dessinees(base, e):
    """Les variantes dont les 5 stades sont dessinés, chances recalculées pour faire 100 %."""
    ok = [v for v in e["variantes"]
          if all((IMAGES / f"{base}_{v['id']}_{s}.png").exists() for s in ("bebe", "enfant", "ado", "adulte", "ancien"))]
    total = sum(v["chance"] for v in ok) or 1
    return [{"id": v["id"], "nom": v["nom"], "chance": round(100 * v["chance"] / total, 1)} for v in ok]


# ---------------------------------------------------------------- les espèces
def fiches_completes():
    out = {}
    for f in sorted(B2.glob("[0-9][0-9]_*.json")):
        for e in json.loads(f.read_text(encoding="utf-8")):
            out[e["id"]] = e
    return out


def espece(e, complet):
    fam, icone, stat, zone, _, cmd, capacites = FAM[e["famille"]]
    rarete = complet["rarete"]
    base = f"{e['numero']:03d}_{e['id']}"
    r = random.Random(f"{e['numero']}-{e['nom']}")
    b = BASE_STATS[rarete] + e["puissance"] // 3
    stats = {
        "PV": b + r.randint(-4, 8),
        "ATK": b + r.randint(-6, 6) + (6 if stat == "Force" else 0),
        "DEF": b + r.randint(-6, 6) + (6 if stat == "Endurance" else 0),
        "VIT": b + r.randint(-6, 6) + (6 if stat == "Agilité" else 0),
        "INT": b + r.randint(-6, 6) + (6 if stat == "Intelligence" else 0),
    }
    variantes = variantes_dessinees(base, e)
    assert variantes and variantes[0]["id"] == "classique", base
    dessins = {}
    for v in variantes:
        d = {}
        for jeu, img in STADES_JEU.items():
            l, p = pixels(ouvrir(f"{base}_{v['id']}_{img}"), GRAND, 20)
            d[jeu] = {"l": l, "p": p}
        l, p = pixels(ouvrir(f"{base}_{v['id']}_adulte"), PETIT, 12)
        d["petit"] = {"l": l, "p": p}
        dessins[v["id"]] = d
    c = dessins["classique"]
    lo, hi = TAILLE_CM[e["taille_finale"]]
    taille = round(r.uniform(lo, hi), 1)
    caractere = complet["caractere"].strip()
    return {
        "id": e["id"],
        "numero": e["numero"],
        "nom": e["nom"],
        "famille": fam,
        "icone": icone,
        "rarete": rarete,
        "stat": stat,
        "description": e["fiche"],
        "comportement": caractere[0].upper() + caractere[1:] + ".",
        "capacite": capacites[(e["numero"] * 7) % len(capacites)],
        "habitat": zone,
        "zone": zone + PROFONDEUR[rarete],
        "attiree_par": cmd,
        "frequence": FREQUENCE[rarete],
        "taille_cm": taille,
        "poids_ko": int(taille * r.uniform(3, 9) * (1 + RARETES.index(rarete))),
        "stats": stats,
        "puissance": e["puissance"],
        "posture": e["posture"],
        "lieux_de_vie": complet.get("habitats", []),
        "epreuves": e["epreuves"],
        "sprite": c["petit"]["l"],
        "sprite_shiny": c["petit"]["l"],
        "palette": c["petit"]["p"],
        "palette_shiny": decaler(c["petit"]["p"]),
        "sprite_grand": c["adulte"]["l"],
        "palette_grand": c["adulte"]["p"],
        "palette_grand_shiny": decaler(c["adulte"]["p"]),
        "variantes": variantes,
        "dessins": dessins,
    }


def secretes():
    """Les espèces secrètes (#151…) faites à partir de vraies images : voir secretes.py."""
    f = RACINE / "donnees" / "secretes.json"
    if not f.exists():
        return []
    out = json.loads(f.read_text(encoding="utf-8"))
    for e in out:
        if e["id"] == "abyssor":                 # le démon des abysses vit au fond des abysses
            e.update({"famille": "Démons", "icone": FAM["Démons"][1], "rarete": "légendaire", "puissance": 15,
                      "habitat": "abysses", "zone": "abysses/gouffre/fosse/sanctuaire", "epreuves": ["Système", "Sécurité"]})
        e.setdefault("epreuves", ["Système"])
        e.setdefault("variantes", [{"id": "classique", "nom": "classique", "chance": 100.0}])
    return out


# Part visée de chaque rareté d'individu parmi les bestioles qui apparaissent (le reste : commune)
CIBLE_RANGS = [("peu commune", 0.30), ("rare", 0.13), ("épique", 0.045), ("légendaire", 0.01)]
POIDS_APPARITION = {"commune": 60, "peu commune": 28, "rare": 10, "légendaire": 2}


def centiles():
    """Pour chaque potentiel (0-100) : la part des individus qui ont moins (somme de 5 tirages de 0 à 31)."""
    loi = [1]
    for _ in range(5):
        n = [0] * (len(loi) + 31)
        for i, v in enumerate(loi):
            for k in range(32):
                n[i + k] += v
        loi = n
    tot = sum(loi)
    out = []
    for p in range(101):
        s = round(p * 155 / 100)
        out.append(round((sum(loi[:s]) + loi[s] / 2) / tot, 4))
    return out


def rarete_individu(especes):
    """Règles de la rareté d'un individu (bestiaire2/rarete.json) : note = 60 % stats (en centile) + 25 % rareté
    de sa forme + 15 % puissance de l'espèce, +10 si shiny. Les paliers sont recalculés pour que les raretés
    gardent la même part quel que soit le nombre de variantes déjà dessinées."""
    r = json.loads((B2 / "rarete.json").read_text(encoding="utf-8"))
    po, cent = r["poids"], centiles()
    rnd = random.Random(1515)
    publiques = [e for e in especes if not e.get("secrete")]
    poids = [POIDS_APPARITION[e["rarete"]] / sum(1 for x in publiques if x["rarete"] == e["rarete"]) for e in publiques]
    notes = []
    for _ in range(200000):
        e = rnd.choices(publiques, poids)[0]
        vs = e["variantes"]
        m = max(v["chance"] for v in vs)
        v = rnd.choices(vs, [x["chance"] for x in vs])[0]
        pot = round(100 * sum(rnd.randint(0, 31) for _ in range(5)) / 155)
        n = po["stats"] * cent[pot] + po["variante"] * (1 - v["chance"] / m) + po["puissance"] * (e["puissance"] - 1) / 14
        if rnd.randrange(100) == 0:
            n += po["bonus_shiny"]
        notes.append(min(100.0, n))
    notes.sort(reverse=True)
    paliers, cumul = [], 0.0
    for nom, part in reversed(CIBLE_RANGS):
        cumul += part
        paliers.append([round(notes[int(cumul * len(notes))], 1), nom])
    r["paliers"] = [[0, "commune"]] + paliers[::-1]
    r["centiles"] = cent
    return r


def generer():
    liste = json.loads((B2 / "bestiaire.json").read_text(encoding="utf-8"))
    complet = fiches_completes()
    especes = [espece(e, complet[e["id"]]) for e in liste]
    assert len(especes) == 150
    assert len({e["nom"].lower() for e in especes}) == 150, "noms en double"
    especes += secretes()
    anciens = json.loads((RACINE / "donnees" / "anciens_noms.json").read_text(encoding="utf-8"))
    par_numero = {e["numero"]: e["nom"] for e in especes}
    return {
        "version": 2,
        "raretes": RARETES,
        "poids": {"commune": 60, "peu commune": 28, "rare": 10, "légendaire": 2},
        "chance_shiny": 100,
        "familles": [{"nom": f[0], "icone": f[1], "stat": f[2], "habitat": f[3], "attiree_par": f[5]} for f in FAMILLES],
        "lieux": {f[3]: f[4] for f in FAMILLES},
        # rareté d'un INDIVIDU (stats + forme + puissance de l'espèce, + shiny) : voir rarete_individu()
        "rarete_individu": rarete_individu(especes),
        "marques": MARQUES,
        "humeurs": HUMEURS,
        # ancien nom → nouveau nom (même numéro) : les vieilles sauvegardes gardent leurs bestioles
        "anciens": {vieux: par_numero[n] for vieux, n in anciens.items() if n in par_numero},
        "especes": especes,
    }


def ecrire(donnees):
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))
    (RACINE / "donnees" / "bestiaire.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    (RACINE / "pc" / "tg" / "bestiaire.json").write_text(texte, encoding="utf-8")
    assets = RACINE / "app" / "src" / "main" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "bestiaire.json").write_text(texte, encoding="utf-8")
    leger = dict(donnees, especes=[{k: v for k, v in e.items() if k != "dessins"} for e in donnees["especes"]])
    (RACINE / "site" / "src" / "bestiaire.js").write_text(
        "// Généré par donnees/generer_bestiaire.py — ne pas modifier à la main.\nexport default "
        + json.dumps(leger, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    d = generer()
    ecrire(d)
    n = sum(len(e.get("variantes", [])) for e in d["especes"])
    print(f"{len(d['especes'])} espèces, {n} formes dessinées.")
