"""Intègre les images générées : détourage du fond uni, recadrage, aperçus.

    python3 donnees/integrer_portraits.py dossier_des_images/

Les images doivent porter le nom donné dans prompts.json (ex. 001_papyrou.png).
Résultat dans donnees/portraits/ : PNG transparents recadrés, plus une planche de contrôle.
(Outil de préparation : il utilise Pillow, numpy et scipy, pas le jeu lui-même.)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ICI = Path(__file__).resolve().parent
SORTIE = ICI / "portraits"
TAILLE_MAX = 512


def couleur(code):
    code = code.lstrip("#")
    return np.array([int(code[i:i + 2], 16) for i in (0, 2, 4)], float)


def detourer(img, fond, tolerance=70, trous=45):
    """Enlève le fond uni : tout ce qui touche le bord et ressemble à la couleur du fond,
    plus les « trous » fermés (dans une boucle de queue…) de la couleur exacte du fond."""
    a = np.asarray(img.convert("RGB")).astype(float)
    dist = np.linalg.norm(a - fond, axis=-1)
    proche = dist < tolerance
    lab, _ = ndimage.label(proche)
    bords = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fond_m = np.isin(lab, list(bords)) | (dist < trous)
    creature = ~fond_m
    creature = ndimage.binary_opening(creature, iterations=1)
    lab, n = ndimage.label(creature)
    if n > 1:      # on garde la créature (et ses morceaux proches), pas les miettes
        tailles = ndimage.sum(creature, lab, range(1, n + 1))
        creature = np.isin(lab, 1 + np.where(tailles > tailles.max() * 0.01)[0])
    # liseré : on retire la teinte du fond qui bave sur les bords
    bord = creature & ~ndimage.binary_erosion(creature, iterations=2)
    dominante = int(np.argmax(fond))
    if fond[1] > 200 and fond[0] < 50:          # fond vert : on limite le vert au max des deux autres
        a[..., 1][bord] = np.minimum(a[..., 1][bord], np.maximum(a[..., 0][bord], a[..., 2][bord]))
    elif fond[0] > 200 and fond[2] > 200:       # fond magenta : on limite rouge et bleu au vert
        g = a[..., 1][bord]
        a[..., 0][bord] = np.minimum(a[..., 0][bord], g + 40)
        a[..., 2][bord] = np.minimum(a[..., 2][bord], g + 40)
    rgba = np.dstack([a.clip(0, 255).astype("uint8"), (creature * 255).astype("uint8")])
    out = Image.fromarray(rgba, "RGBA")
    return out.crop(out.getbbox()), dominante


def carre(img, marge=0.06):
    c = max(img.size)
    c = int(c * (1 + 2 * marge))
    out = Image.new("RGBA", (c, c))
    out.alpha_composite(img, ((c - img.width) // 2, c - img.height - int(c * marge)))
    if c > TAILLE_MAX:
        out = out.resize((TAILLE_MAX, TAILLE_MAX), Image.LANCZOS)
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    entree = Path(sys.argv[1])
    prompts = json.loads((ICI / "prompts.json").read_text(encoding="utf-8"))
    fonds = {}
    for p in prompts["especes"]:
        fonds[p["fichier"]] = p["fond"]
        fonds[p["fichier_evolue"]] = p["fond"]
    for p in prompts["abyssor"]:
        fonds[p["fichier"]] = p["fond"]
    SORTIE.mkdir(exist_ok=True)
    faits = []
    for f in sorted(entree.glob("*.png")):
        code = fonds.get(f.name)
        if not code:
            print(f"  ? {f.name} : nom inconnu (voir prompts.json)")
            continue
        img, _ = detourer(Image.open(f), couleur(code))
        img = carre(img)
        img.save(SORTIE / f.name)
        faits.append((f.name, img))
        print(f"  ✔ {f.name}  {img.size[0]}×{img.size[1]}")
    if faits:
        n = len(faits)
        cols = min(n, 6)
        planche = Image.new("RGB", (cols * 200, ((n + cols - 1) // cols) * 220), (20, 20, 30))
        d = ImageDraw.Draw(planche)
        for i, (nom, img) in enumerate(faits):
            x, y = (i % cols) * 200, (i // cols) * 220
            v = img.copy()
            v.thumbnail((190, 190))
            planche.paste(v, (x + 5, y + 5), v)
            d.text((x + 6, y + 200), nom, fill=(220, 220, 230))
        planche.save(SORTIE / "_planche.png")
    print(f"{len(faits)} image(s) intégrée(s) dans {SORTIE}")


if __name__ == "__main__":
    main()
