"""Fabrique les descriptions (prompts) à donner au générateur d'images, pour chaque espèce.

    python3 donnees/generer_prompts.py      →  donnees/prompts.json  et  donnees/prompts.md

Toutes les images doivent avoir la même pose et un fond uni : c'est ce qui permet de les
détourer et de les découper automatiquement (ailes, tête, bras, corps) pour les animer.
"""
import json
from pathlib import Path

from visuels import VISUELS

ICI = Path(__file__).resolve().parent

STYLE_RARETE = {
    "commune": "a small cute chibi creature, round soft shapes, big expressive eyes, friendly",
    "peu commune": "a medium-sized creature, playful but more detailed, a few distinctive features",
    "rare": "a large impressive creature, detailed, confident powerful stance",
    "légendaire": "a huge epic boss creature, highly detailed, majestic and intimidating, like a final boss",
}

POSE = ("Full body, front view, standing in a symmetrical pose facing the viewer, "
        "arms and legs held slightly away from the body, wings spread wide if it has wings, "
        "head and eyes clearly visible, nothing hiding the body, the whole creature visible with empty margin around it, centered")

FOND = ("Plain solid {fond} background, no scenery, no ground, no shadow, no text, no border, no watermark")

TECHNIQUE = "16-bit pixel art game sprite, SNES style, crisp pixel edges, clean dark outline, rich shading, limited palette"

COULEURS_VERTES = ("green", "lime", "emerald", "olive", "acid")


def fond_pour(visuel):
    """Vert pur pour détourer, sauf si la bestiole est elle-même verte : alors magenta."""
    if any(m in visuel for m in COULEURS_VERTES):
        return "magenta #FF00FF", "#FF00FF"
    return "pure green #00FF00", "#00FF00"


def prompt(visuel, rarete, fond):
    return ". ".join([
        TECHNIQUE,
        STYLE_RARETE[rarete] + ": " + visuel,
        POSE,
        FOND.format(fond=fond),
    ]) + "."


def prompt_evolue(visuel, fond):
    return ". ".join([
        TECHNIQUE,
        "The EVOLVED final form of the creature in the reference image: " + visuel,
        "Keep the same colors, the same head shape and the same recognizable features, "
        "but bigger and more powerful, with new elements: armor plates or crystals, more horns or spikes, "
        "glowing markings, a more elaborate tail and wings",
        POSE,
        FOND.format(fond=fond),
    ]) + "."


# La lignée secrète d'Abyssor (#151) : l'image d'origine fournie par le joueur est le stade 3.
ABYSSOR = [
    ("Abyssou", "bébé", "a tiny baby version of the demon in the reference image: round chubby body, big round yellow eyes, "
     "tiny horn buds instead of horns, two small fangs, very small soft wings, no spikes and no claws, cute but mischievous, crimson red"),
    ("Abyssard", "jeune", "a teenage version of the demon in the reference image: lean body, short curved horns, small fangs, "
     "medium wings, a few shoulder spikes, short claws, cocky expression, crimson red"),
    ("Abyssor", "adulte", "a massive horned red demon with bat wings, curved beige horns, a fanged roaring mouth, "
     "spiked shoulders, long beige claws, a ridged beige belly and a spiked tail (this is the reference image)"),
    ("Abyssor (forme finale)", "finale", "the ultimate form of the demon in the reference image: four horns, molten lava cracks "
     "glowing across its skin, bone shoulder armor, a third cyan eye on its forehead, glowing cyan eyes, giant wings, "
     "a flaming tail tip, a fiery aura"),
]


def main():
    bestiaire = json.loads((ICI / "bestiaire.json").read_text(encoding="utf-8"))
    especes = bestiaire["especes"]
    manque = [e["nom"] for e in especes if e["nom"] not in VISUELS]
    if manque:
        raise SystemExit("Apparence manquante pour : " + ", ".join(manque))
    sortie = []
    for e in especes:
        v = VISUELS[e["nom"]]
        fond, code = fond_pour(v)
        sortie.append({
            "numero": e["numero"], "id": e["id"], "nom": e["nom"], "famille": e["famille"], "rarete": e["rarete"],
            "fichier": f"{e['numero']:03d}_{e['id']}.png", "fichier_evolue": f"{e['numero']:03d}_{e['id']}_evo.png",
            "fond": code, "prompt": prompt(v, e["rarete"], fond), "prompt_evolue": prompt_evolue(v, fond),
        })
    lignee = []
    for nom, stade, v in ABYSSOR:
        fond, code = fond_pour(v)
        lignee.append({"nom": nom, "stade": stade, "fichier": f"151_abyssor_{stade}.png", "fond": code,
                       "prompt": ". ".join([TECHNIQUE, v, POSE, FOND.format(fond=fond)]) + "."})
    (ICI / "prompts.json").write_text(json.dumps({"especes": sortie, "abyssor": lignee}, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    lignes = ["# Descriptions pour le générateur d'images", "",
              "Une image par espèce, nommée comme indiqué (ex. `001_papyrou.png`), pose de face, fond uni.",
              "Pour la forme évoluée : donner l'image de base au générateur comme **image de référence**.", ""]
    famille = None
    for p in sortie:
        if p["famille"] != famille:
            famille = p["famille"]
            lignes += ["", f"## {famille}", ""]
        lignes += [f"### #{p['numero']:03d} {p['nom']} — {p['rarete']}  →  `{p['fichier']}`", "", p["prompt"], "",
                   f"*Forme évoluée* → `{p['fichier_evolue']}`", "", p["prompt_evolue"], ""]
    lignes += ["", "## #151 Abyssor — légendaire secrète (donner l'image d'Abyssor comme référence)", ""]
    for p in lignee:
        lignes += [f"### {p['nom']} ({p['stade']})  →  `{p['fichier']}`", "", p["prompt"], ""]
    (ICI / "prompts.md").write_text("\n".join(lignes), encoding="utf-8")
    print(f"{len(sortie)} espèces + {len(lignee)} stades d'Abyssor → prompts.json, prompts.md")


if __name__ == "__main__":
    main()
