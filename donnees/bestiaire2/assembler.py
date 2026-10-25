"""Assemble le nouveau bestiaire (10 familles × 15 espèces) : numéros, variantes aléatoires, prompts.

    python3 donnees/bestiaire2/assembler.py

Entrée : donnees/bestiaire2/NN_famille.json (écrits famille par famille).
Sortie : bestiaire.json (données du jeu) et prompts.json / prompts.md (pour le générateur d'images).

Variantes : chaque espèce a sa forme « classique » + entre 2 et 9 variantes liées à ses lieux de vie,
tirées au hasard (graine = id de l'espèce, donc le tirage est stable d'une exécution à l'autre).
Le shiny n'est pas une variante dessinée : n'importe quel individu, de n'importe quelle variante,
peut naître shiny (1 chance sur 100, comme aujourd’hui) avec une teinte unique tirée au hasard + des étoiles.
"""
import json
import random
from pathlib import Path

ICI = Path(__file__).resolve().parent

FAMILLES = [
    # fichier, nom, familles d'épreuves de dressage (commandes à apprendre)
    ("01_demons", "Démons", ["Sécurité", "Système"]),
    ("02_elementaires", "Élémentaires", ["Matériel", "Système"]),
    ("03_morts_vivants", "Morts-vivants", ["Processus"]),
    ("04_betes", "Bêtes monstrueuses", ["Mémoire", "Rétro"]),
    ("05_sylvestres", "Sylvestres", ["Fichiers"]),
    ("06_arthropodes", "Arthropodes", ["Bugs", "Code"]),
    ("07_abyssaux", "Abyssaux", ["Données"]),
    ("08_celestes", "Célestes", ["Réseau", "Nuage"]),
    ("09_constructs", "Constructs", ["Code", "Crypto"]),
    ("10_aberrations", "Aberrations", ["Glitch"]),
]

HABITATS = {
    "glace": "body made of ice and frost, icicles, pale blue and white",
    "toundra": "thick white winter fur or frosted plates, snowy tufts, grey and white",
    "eau pétillante": "translucent sparkling-water body full of fizzy bubbles, aqua and white",
    "lagon": "smooth turquoise skin, shell ornaments, tropical fins, sandy beige accents",
    "abyssal": "deep-sea look, dark navy body, glowing bioluminescent spots and lures",
    "corail": "coral growths, sea anemones and shells all over the body, pink and orange",
    "marais": "muddy skin, moss, reeds and dripping swamp water, olive and brown",
    "jungle": "lush leaves, vines and tropical flowers on the body, vivid greens",
    "forêt": "bark texture, leaves and small branches, moss green and wood brown",
    "champignonnière": "glowing mushrooms growing on the body, spores, earthy tones",
    "désert": "sandstone plates, sun-bleached look, ochre and beige",
    "sable": "body of packed sand with flowing grains, golden beige",
    "canyon": "layered red rock strata, terracotta and rust",
    "volcan": "black volcanic rock with glowing cracks, smoke, red and orange",
    "cendres": "ash-grey body with smouldering embers, charcoal and dull orange",
    "lave": "molten lava flowing over cooled black crust, bright orange",
    "orage": "storm clouds and crackling lightning, dark blue and electric yellow",
    "nuage": "soft fluffy cloud body, white and sky blue, airy wisps",
    "aurore": "shimmering aurora ribbons, green-teal-violet gradients",
    "cosmique": "starry night-sky body with galaxies and tiny planets, deep blue and violet",
    "lune": "pale silver moonlit body, crescent marks, soft glow",
    "soleil": "radiant golden body with sun rays and flares, gold and white",
    "cristal": "faceted crystal growths and gem-like body, prismatic",
    "arcane": "glowing runes and magic sigils, floating crystals, violet glow",
    "ruines": "cracked ancient stone with carved glyphs and ivy",
    "ossuaire": "bone plates and skull ornaments, ivory and grey",
    "crypte": "dusty tomb look, cobwebs, candles, grey and dark purple",
    "brume": "half-transparent misty body fading into fog, pale grey",
    "ombre": "pitch-black shadow body with glowing eyes, dark smoke",
    "toxique": "acid-green slime dripping, poison bubbles, purple spots",
    "rouille": "rusty corroded metal patches, orange-brown",
    "mécanique": "brass gears, pipes and rivets, clockwork parts",
    "néon": "glowing neon outlines, cyber colors pink and cyan",
    "prairie": "soft grass and wildflowers, spring green and yellow",
    "montagne": "granite rock and snowy peaks on the back, grey and white",
}

TAILLES = "Heights compared to the elder: baby 20%, child 35%, teen 55%, adult 80%, elder 100%."
POSES = {
    "volant": "flying stages hover at the same height, wings open",
    "flottant": "all floating slightly above the same ground line",
    "serpentin": "coiled serpentine bodies resting on the ground line",
}
VIOLETS = ("purple", "violet", "magenta", "pink", "lilac", "lavender", "fuchsia", "amethyst")


def fond(texte):
    """Le fond le plus éloigné des couleurs de la créature (magenta par défaut, vert si elle est violette/rose)."""
    t = texte.lower()
    if any(v in t for v in VIOLETS):
        return "green", "#00FF00"
    return "magenta", "#FF00FF"


def prompt_classique(e):
    pose = POSES.get(e["posture"], "all standing on the same ground line")
    s = e["stades"]
    nom_fond, code = fond(e["apparence"] + " " + " ".join(s.values()))
    return code, (
        f"Generate an image. 16-bit SNES pixel art sprite sheet, crisp pixels, dark outline: ONE single row of 5 "
        f"evolution stages of the same original creature, left to right: baby, child, teen, adult, elder. 3/4 side view, "
        f"{pose}, LOTS of empty space between creatures, nothing touching the edges, very wide landscape image, "
        f"plain solid {nom_fond} {code} background, no text, no shadow. {TAILLES} The anatomy must really CHANGE at "
        f"each stage like a real evolution, not a resized copy. Base look: {e['apparence']} "
        f"Baby: {s['bebe']} Child: {s['enfant']} Teen: {s['ado']} Adult: {s['adulte']} Elder: {s['ancien']}"
    )


def prompt_variante(e, hab):
    desc = HABITATS[hab]
    nom_fond, code = fond(desc + " " + e["apparence"])
    return code, (
        f"Same row of 5 stages as your last image (same evolution logic, same anatomy and silhouette changes at each "
        f"stage, same 3/4 side view, LOTS of empty space between creatures, nothing touching the edges, very wide "
        f"landscape image, plain solid {nom_fond} {code} background, no text). {TAILLES} Now the {hab.upper()} variant: "
        f"the body material, colors and details change to fit this habitat: {desc}. The habitat details grow "
        f"stronger with each stage, the elder is fully transformed by it."
    )


def chances(n):
    """Chances d'apparition : la classique est la plus fréquente, puis de plus en plus rare."""
    poids = [30] + [round(24 / (k + 1.6), 1) for k in range(n)]
    total = sum(poids)
    return [round(100 * p / total, 1) for p in poids]


def main():
    especes, prompts, noms = [], [], set()
    numero = 0
    for fichier, famille, epreuves in FAMILLES:
        chemin = ICI / f"{fichier}.json"
        if not chemin.exists():
            print(f"  (manque {chemin.name})")
            numero += 15
            continue
        for e in sorted(json.loads(chemin.read_text(encoding="utf-8")), key=lambda x: x["rang"]):
            numero += 1
            assert e["nom"] not in noms, f"nom en double : {e['nom']}"
            noms.add(e["nom"])
            habs = [h for h in e["habitats"] if h in HABITATS]
            rnd = random.Random(e["id"])
            n = rnd.randint(2, min(9, len(habs)))
            choix = habs[:1] + rnd.sample(habs[1:], n - 1)          # le lieu de vie évident + un tirage
            ch = chances(len(choix))
            variantes = [{"id": "classique", "nom": "classique", "chance": ch[0]}]
            variantes += [{"id": h.replace(" ", "_").replace("é", "e").replace("è", "e"), "nom": h, "chance": c}
                          for h, c in zip(choix, ch[1:])]
            fiche = {k: e[k] for k in ("nom", "id", "rarete", "posture", "taille_finale", "fiche", "caractere")}
            fiche.update(numero=numero, famille=famille, epreuves=epreuves, variantes=variantes)
            especes.append(fiche)
            base = f"{numero:03d}_{e['id']}"
            code, p = prompt_classique(e)
            prompts.append({"fichier": f"{base}_classique", "fond": code, "prompt": p, "nouvelle_conversation": True})
            for v in variantes[1:]:
                code, p = prompt_variante(e, v["nom"])
                prompts.append({"fichier": f"{base}_{v['id']}", "fond": code, "prompt": p, "nouvelle_conversation": False})
    (ICI / "bestiaire.json").write_text(json.dumps(especes, ensure_ascii=False, indent=1), encoding="utf-8")
    (ICI / "prompts.json").write_text(json.dumps(prompts, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# Prompts du nouveau bestiaire", ""]
    for p in prompts:
        md += [f"## {p['fichier']}  (fond {p['fond']})", "", p["prompt"], ""]
    (ICI / "prompts.md").write_text("\n".join(md), encoding="utf-8")
    nv = sum(len(e["variantes"]) for e in especes)
    print(f"{len(especes)} espèces, {nv} images à générer (classiques + variantes)")


if __name__ == "__main__":
    main()
