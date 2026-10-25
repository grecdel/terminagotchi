"""Les espèces secrètes, faites à partir d'une vraie image (outil de préparation, utilise Pillow).

    python3 donnees/secretes.py   →  donnees/secretes.json  (lu ensuite par generer_bestiaire.py)
"""
import colorsys
import json
from pathlib import Path

from PIL import Image

ICI = Path(__file__).resolve().parent
SYMBOLES = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+-=?@"


def pixels(img, taille, couleurs):
    """Image → lignes de symboles + palette (le point « . » = transparent)."""
    im = img.copy()
    im.thumbnail((taille, taille), Image.LANCZOS)
    alpha = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    q = im.convert("RGB").quantize(couleurs, method=Image.MEDIANCUT)
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
    palette = {s: "#%02x%02x%02x" % tuple(pal[3 * i:3 * i + 3]) for i, s in utilises.items()}
    return lignes, palette


def decaler(palette, dec):
    out = {}
    for k, h in palette.items():
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hh, l, s = colorsys.rgb_to_hls(r, g, b)
        r, g, b = colorsys.hls_to_rgb((hh + dec) % 1, l, s)
        out[k] = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    return out


def abyssor():
    img = Image.open(ICI / "portraits" / "151_abyssor_adulte.png").convert("RGBA")
    img = img.crop(img.getbbox())
    petit, pal_p = pixels(img, 16, 14)
    grand, pal_g = pixels(img, 48, 48)
    return {
        "id": "abyssor", "numero": 151, "nom": "Abyssor", "famille": "Système", "icone": "⚙", "rarete": "mythique",
        "secrete": True, "stat": "Force",
        "description": "Le démon des abysses du système. On dit qu'il est né d'un rm -rf / tapé à minuit.",
        "comportement": "Il dort tout au fond de la grotte et ne se montre qu'aux maîtres qui ont déjà dressé trois légendaires.",
        "capacite": "Rugissement noyau : fige tous les processus autour de lui",
        "habitat": "grotte", "zone": "grotte/abysses/gouffre/sanctuaire", "attiree_par": "sudo",
        "frequence": "presque jamais", "taille_cm": 240.0, "poids_ko": 6666,
        "stats": {"PV": 95, "ATK": 92, "DEF": 78, "VIT": 60, "INT": 85},
        "sprite": petit, "sprite_shiny": petit, "palette": pal_p, "palette_shiny": decaler(pal_p, 0.5),
        "sprite_grand": grand, "palette_grand": pal_g, "palette_grand_shiny": decaler(pal_g, 0.5),
        "stades": ["enfant", "ado", "adulte", "forme finale"],   # il garde son nom à tous les âges
    }


if __name__ == "__main__":
    (ICI / "secretes.json").write_text(json.dumps([abyssor()], ensure_ascii=False, indent=1), encoding="utf-8")
    print("secretes.json : Abyssor")
