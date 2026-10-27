"""Fabrique les données du jeu à partir du nouveau bestiaire (10 familles × 15 espèces + Abyssor).

    python3 donnees/bestiaire2/generer_jeu.py

Sorties :
  pc/tg/bestiaire.json                      espèces, familles, variantes, règles de rareté (terminal PC)
  pc/tg/sprites.bin                         images en gros pixels (une palette par espèce-variante, 5 stades)
  app/src/main/assets/bestiaire.json        les mêmes données pour l'appli
  app/src/main/assets/sprites.bin           …
  app/src/main/assets/portraits/<id>/<variante>_<stade>.webp   versions détaillées pour les fiches
  site/public/portraits/…                   idem pour le site
  site/src/bestiaire.js                     les données des pages du site (voir generer_site.py)
Les variantes pas encore dessinées sont simplement absentes : le jeu retombe sur la forme classique.
"""
import base64
import hashlib
import json
import random
import shutil
import sys
import unicodedata
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI))
import assembler as A  # noqa: E402

STADES = ["bebe", "enfant", "ado", "adulte", "ancien"]
# hauteur max en pixels (terminal : 2 pixels par caractère) : on voit vraiment la bestiole grandir
TAILLE_STADE = {"bebe": 18, "enfant": 26, "ado": 34, "adulte": 42, "ancien": 48}
NB_COULEURS = 40

FAMILLES = {
    #  nom : icône, stat favorite, commande qui l'attire
    "Démons": ("😈", "Force", "chmod"),
    "Élémentaires": ("🔥", "Endurance", "df"),
    "Morts-vivants": ("💀", "Intelligence", "ps"),
    "Bêtes monstrueuses": ("🐺", "Force", "free"),
    "Sylvestres": ("🌳", "Endurance", "ls"),
    "Arthropodes": ("🪲", "Agilité", "grep"),
    "Abyssaux": ("🐙", "Endurance", "cat"),
    "Célestes": ("✨", "Intelligence", "ping"),
    "Constructs": ("⚙", "Force", "git"),
    "Aberrations": ("👁", "Agilité", "rev"),
}
CAPACITES = {
    "Démons": ["Souffle de braise", "Rire moqueur", "Pacte piégé", "Flammes noires", "Couronne infernale"],
    "Élémentaires": ["Petite étincelle", "Rafale", "Bouclier de pierre", "Déluge", "Colère des éléments"],
    "Morts-vivants": ["Os qui claquent", "Frisson glacé", "Cri d'outre-tombe", "Brume des tombes", "Réveil des morts"],
    "Bêtes monstrueuses": ["Coup de griffe", "Hurlement", "Charge cornue", "Peau d'armure", "Rugissement du roi"],
    "Sylvestres": ["Graine qui roule", "Lianes", "Pluie de spores", "Écorce dure", "Souffle de la forêt"],
    "Arthropodes": ["Morsure", "Fil de soie", "Dard", "Carapace", "Essaim"],
    "Abyssaux": ["Bulle", "Jet d'encre", "Pince", "Lumière des abysses", "Vague géante"],
    "Célestes": ["Petite lueur", "Poussière d'étoile", "Rayon de lune", "Aura sacrée", "Éclat du zénith"],
    "Constructs": ["Clé à molette", "Vapeur", "Engrenage", "Rune gravée", "Marteau de forge"],
    "Aberrations": ["Regard fixe", "Mutation", "Tentacule", "Miroir", "Chaos"],
}
ARTICLES = {
    "glace": "la banquise", "toundra": "la toundra", "eau pétillante": "la source pétillante", "lagon": "le lagon",
    "abyssal": "les abysses", "corail": "le récif de corail", "marais": "le marais", "jungle": "la jungle",
    "forêt": "la forêt", "champignonnière": "la champignonnière", "désert": "le désert", "sable": "les dunes",
    "canyon": "le canyon", "volcan": "le volcan", "cendres": "la plaine de cendres", "lave": "le lac de lave",
    "orage": "le ciel d'orage", "nuage": "la mer de nuages", "aurore": "l'aurore boréale", "cosmique": "l'espace",
    "lune": "la lune", "soleil": "le temple du soleil", "cristal": "la grotte de cristal", "arcane": "la tour arcanique",
    "ruines": "les ruines", "ossuaire": "l'ossuaire", "crypte": "la crypte", "brume": "la brume",
    "ombre": "le royaume des ombres", "toxique": "le marécage toxique", "rouille": "la casse rouillée",
    "mécanique": "l'atelier mécanique", "néon": "la ville néon", "prairie": "la prairie", "montagne": "la montagne",
}
TAILLE_CM = {"petite": 30, "moyenne": 90, "grande": 220, "colossale": 600}
# qualité de l'individu (0-1) puis note de rareté : voir RARETE dans assembler.py
OBJECTIF = [("commune", 0.55), ("peu commune", 0.27), ("rare", 0.12), ("épique", 0.05), ("légendaire", 0.01)]
POIDS_FREQ = {"souvent": 60, "parfois": 28, "rarement": 10, "très rarement": 2}


def slug(t):
    return A.unicodedata_slug(t) if hasattr(A, "unicodedata_slug") else (
        t.lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("ê", "e").replace("â", "a")
        .replace("ç", "c").replace("ï", "i").replace("ô", "o").replace("û", "u").replace("'", ""))


def stats_de_base(e):
    """PV, ATK, DEF, VIT, INT de l'espèce : plus elle est haut placée dans sa famille, plus elle est forte."""
    r = random.Random("stats" + e["id"])
    total = 110 + 9 * e["rang"]
    profil = {"quadrupède": (1.1, 1.2, 1.0, 1.1, 0.6), "bipède": (1.0, 1.1, 1.0, 0.9, 1.0),
              "volant": (0.8, 1.0, 0.7, 1.5, 1.0), "flottant": (0.9, 0.7, 0.8, 1.0, 1.6),
              "serpentin": (1.0, 1.2, 0.9, 1.2, 0.7), "rampant": (1.2, 0.8, 1.3, 0.6, 1.1),
              "multipattes": (0.9, 1.1, 1.2, 1.2, 0.6), "amorphe": (1.5, 0.8, 1.2, 0.5, 1.0)}[e["posture"]]
    p = [x * r.uniform(0.85, 1.15) for x in profil]
    s = sum(p)
    return {k: max(5, round(total * v / s)) for k, v in zip(("PV", "ATK", "DEF", "VIT", "INT"), p)}


def paliers_rarete(especes):
    """Seuils de note calés par simulation pour obtenir ~55/27/12/5/1 %."""
    r = random.Random(7)
    notes = []
    poids = [POIDS_FREQ[e["frequence"]] for e in especes]
    for _ in range(60000):
        e = r.choices(especes, poids)[0]
        v = r.choices(e["variantes"], [x["chance"] for x in e["variantes"]])[0]
        notes.append(note(r.random(), v["score"], e["puissance"], r.random() < 0.01))
    notes.sort()
    seuils, cumul = [[0, "commune"]], 0
    for nom, part in OBJECTIF[:-1]:
        cumul += part
        seuils.append([round(notes[int(cumul * len(notes))], 1), OBJECTIF[len(seuils)][0]])
    return seuils


def note(qualite, score_variante, puissance, shiny):
    """La note sur 100 d'un individu (même calcul dans le jeu PC, l'appli et le serveur)."""
    n = 60 * qualite + 25 * score_variante + 15 * (puissance - 1) / 14 + (10 if shiny else 0)
    return min(100.0, n)


# ---------------------------------------------------------------- images
def charger(fichier):
    p = ICI / "images" / fichier
    if not p.exists():  # les fichiers sont nommés sans accent (forêt -> foret)
        p = ICI / "images" / unicodedata.normalize("NFKD", fichier).encode("ascii", "ignore").decode()
    return Image.open(p).convert("RGBA") if p.exists() else None


def reduire(img, h_max):
    """Réduction en gros pixels : boîte, puis alpha franc (pas de bord flou)."""
    f = h_max / max(img.height, img.width * 0.9)
    w, h = max(1, round(img.width * f)), max(1, round(img.height * f))
    petit = img.resize((w, h), Image.BOX)
    a = np.asarray(petit).copy()
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    return Image.fromarray(a, "RGBA")


def palette_commune(imgs):
    """Une seule palette pour les 5 stades d'une espèce-variante (évolution sans changement de couleurs)."""
    larg = sum(i.width for i in imgs)
    haut = max(i.height for i in imgs)
    planche = Image.new("RGBA", (larg, haut))
    x = 0
    for i in imgs:
        planche.alpha_composite(i, (x, 0))
        x += i.width
    rgb = planche.convert("RGB")
    masque = np.asarray(planche)[..., 3] > 0
    pts = np.asarray(rgb)[masque]
    q = Image.fromarray(pts.reshape(1, -1, 3).astype("uint8")).quantize(NB_COULEURS, method=Image.MEDIANCUT)
    pal = q.getpalette()[:3 * NB_COULEURS]
    return [tuple(pal[k:k + 3]) for k in range(0, len(pal), 3)], q


def indexer(img, pal_img):
    """Image → octets (0 = transparent, 1..N = couleur de la palette)."""
    a = np.asarray(img)
    q = np.asarray(img.convert("RGB").quantize(palette=pal_img, dither=Image.Dither.NONE)).astype(np.uint8) + 1
    q[a[..., 3] == 0] = 0
    return q


def main():
    src = {}
    for f, fam, ep in A.FAMILLES:
        for e in json.loads((ICI / f"{f}.json").read_text(encoding="utf-8")):
            e["famille"], e["epreuves"] = fam, ep
            src[e["id"]] = e
    plan = json.loads((ICI / "bestiaire.json").read_text(encoding="utf-8"))
    especes, sprites, portraits = [], {}, []
    for p in plan:
        e = src[p["id"]]
        icone, stat, cmd = FAMILLES[e["famille"]]
        hab0 = e["habitats"][0]
        ch0 = p["variantes"][0]["chance"]
        variantes = []
        for v in p["variantes"]:
            hab = hab0 if v["id"] == "classique" else v["nom"]
            score = 0.0 if v["id"] == "classique" else round(1 - v["chance"] / ch0, 3)
            variantes.append({"id": v["id"], "nom": v["nom"], "chance": v["chance"], "score": score,
                              "zone": slug(hab), "habitat": hab})
        d = {
            "id": e["id"], "numero": p["numero"], "nom": e["nom"], "famille": e["famille"], "icone": icone,
            "rarete": e["rarete"],                          # rang dans la famille (ne décide plus la rareté)
            "frequence": p["frequence"], "puissance": e["rang"], "stat": stat,
            "description": e["fiche"], "comportement": f"Caractère : {e['caractere']}.",
            "capacite": CAPACITES[e["famille"]][min(4, (e["rang"] - 1) // 3)],
            "habitat": slug(hab0), "zone": slug(hab0), "attiree_par": cmd, "epreuves": e["epreuves"],
            "posture": e["posture"], "taille_cm": TAILLE_CM[e["taille_finale"]],
            "poids_ko": TAILLE_CM[e["taille_finale"]] * 3, "stats": stats_de_base(e), "variantes": variantes,
            "stades": STADES,
        }
        especes.append(d)
        # --- images de chaque variante dessinée
        for v in variantes:
            imgs = [charger(f"{p['numero']:03d}_{e['id']}_{v['id']}_{s}.png") for s in STADES]
            if any(i is None for i in imgs):
                continue
            petits = [reduire(i, TAILLE_STADE[s]) for i, s in zip(imgs, STADES)]
            pal, pal_img = palette_commune(petits)
            sprites[f"{e['id']}/{v['id']}"] = {
                "palette": ["#%02x%02x%02x" % c for c in pal],
                "stades": {s: [im.width, im.height, base64.b64encode(zlib.compress(indexer(im, pal_img).tobytes(), 9)).decode()]
                           for s, im in zip(STADES, petits)},
            }
            for s, im in zip(STADES, imgs):
                portraits.append((e["id"], v["id"], s, im))
    seuils = paliers_rarete(especes)
    regles = json.loads((ICI / "rarete.json").read_text(encoding="utf-8"))
    regles["paliers"] = seuils
    regles["qualite"] = "tirée au hasard entre 0 et 1 par le serveur à l'apparition ; les stats en découlent"
    # Abyssor, la secrète, garde ses données d'origine (mythique)
    ancien = json.loads((ICI / "ancien_bestiaire_v1.json").read_text(encoding="utf-8"))
    secretes = [x for x in ancien["especes"] if x.get("secrete")]
    for x in secretes:
        x["rarete"], x["frequence"], x["puissance"] = "mythique", "presque jamais", 15
        x.setdefault("variantes", [{"id": "classique", "nom": "classique", "chance": 100, "score": 1.0,
                                    "zone": x["zone"], "habitat": x["habitat"]}])
    donnees = {
        "version": 2, "chance_shiny": 100, "poids_frequence": POIDS_FREQ,
        "raretes": [s[1] for s in seuils] + ["mythique"], "rarete": regles,
        "familles": [{"nom": f, "icone": i, "stat": s, "attiree_par": c, "habitat": None}
                     for f, (i, s, c) in FAMILLES.items()],
        "habitats": {slug(h): ARTICLES.get(h, "le " + h) for h in A.HABITATS},
        "marques": ancien["marques"], "humeurs": ancien["humeurs"],
        "stades": STADES, "especes": especes + secretes,
        # les anciennes espèces (bestiaire v1) deviennent la nouvelle espèce de même numéro
        "anciens": {x["nom"]: x["numero"] for x in ancien["especes"] if not x.get("secrete")},
    }
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))
    bin_ = zlib.compress(json.dumps(sprites, separators=(",", ":")).encode(), 9)
    for dossier in (RACINE / "pc/tg", RACINE / "app/src/main/assets"):
        (dossier / "bestiaire.json").write_text(texte, encoding="utf-8")
        (dossier / "sprites.bin").write_bytes(bin_)
    for base in (RACINE / "app/src/main/assets/portraits", RACINE / "site/public/portraits"):
        shutil.rmtree(base, ignore_errors=True)
    for eid, vid, s, im in portraits:
        im2 = im.copy()
        im2.thumbnail((160, 160), Image.LANCZOS)
        for base in (RACINE / "app/src/main/assets/portraits", RACINE / "site/public/portraits"):
            (base / eid).mkdir(parents=True, exist_ok=True)
            im2.save(base / eid / f"{vid}_{s}.webp", "WEBP", quality=88, method=6)
    print(f"{len(especes)} espèces + {len(secretes)} secrète(s), {len(sprites)} espèces-variantes dessinées")
    print(f"bestiaire.json {len(texte)//1024} Ko, sprites.bin {len(bin_)//1024} Ko, paliers {seuils}")
    # anti-triche : données du tirage pour le site et vecteurs de test communs (Python / Kotlin / JS)
    import subprocess
    import sys
    subprocess.run([sys.executable, str(RACINE / "donnees/anti_triche/generer.py")], check=True)
    # le bestiaire des pages du site (fiches, variantes dessinées, anciennes espèces)
    subprocess.run([sys.executable, str(ICI / "generer_site.py")], check=True)


if __name__ == "__main__":
    main()
