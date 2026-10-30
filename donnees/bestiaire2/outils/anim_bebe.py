"""anim_bebe.py ID capture_haut capture_bas : planche d'animation d'un bébé de départ -> 12 images.

Les deux captures (moitié haute, moitié basse de la planche affichée en pleine largeur) sont recollées,
la planche 3 × 4 est découpée en cases, le fond uni (vert ou magenta) est retiré, chaque pose est
recadrée puis mise à l'échelle du bébé classique (même hauteur pour la pose « assis »).
Sortie : donnees/bestiaire2/animations/<ID>/<pose>.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ICI = Path(__file__).resolve().parents[1]
CAPT = Path("/tmp/claude-chrome-screenshots-t149HL")
POSES = ["marche1", "marche2", "marche3", "marche4",
         "assis", "dort", "etire", "baille",
         "sursaut", "coeur", "mange", "salut"]


def capture(n):
    f = sorted(CAPT.glob(f"screenshot-*-{n}.jpg")) or sorted(CAPT.glob(f"screenshot-*-{n}.png"))
    return Image.open(f[0]).convert("RGB")


def fond_masque(a):
    """vrai = fond. Le fond est la couleur du coin, en tolérant la compression."""
    c = np.median(a[2:12, 200:260].reshape(-1, 3), axis=0)
    d = np.abs(a.astype(int) - c.astype(int)).sum(axis=2)
    vert = c[1] > 150 and c[0] < 140
    if c[2] > 150 and c[0] < 140 and c[1] < 140:          # fond bleu : la distance suffit
        return d < 110, None
    if vert:
        dom = (a[..., 1].astype(int) - np.maximum(a[..., 0], a[..., 2]).astype(int)) > 60
    else:
        dom = (np.minimum(a[..., 0], a[..., 2]).astype(int) - a[..., 1].astype(int)) > 90
    return (d < 110) | dom, vert


def nettoyer(rgba, vert):
    if vert is None:
        return rgba
    a = rgba.astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    if vert:
        g2 = np.minimum(g, np.maximum(r, b) + 10)
        a[..., 1] = np.where(al > 0, g2, g)
    else:
        m = np.maximum(g + 10, 0)
        a[..., 0] = np.where((al > 0) & (r > m) & (b > m), np.minimum(r, (g + r + b) // 3 + 30), r)
        a[..., 2] = np.where((al > 0) & (r > m) & (b > m), np.minimum(b, (g + r + b) // 3 + 30), b)
    return a.clip(0, 255).astype(np.uint8)


def main():
    ident, n0, n1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    h0 = capture(n0)
    h1 = capture(n1)
    W = h0.width
    # hauteur totale de la planche affichée = arg 4 (en pixels de capture) si donnée, sinon 2 × 682 - recouvrement
    total = int(sys.argv[4]) if len(sys.argv) > 4 else None
    if total is None or total <= h0.height:
        planche = h0
    else:
        planche = Image.new("RGB", (W, total))
        planche.paste(h0, (0, 0))
        if len(sys.argv) > 5:          # capture du milieu (planches presque carrées)
            hm = capture(int(sys.argv[5]))
            planche.paste(hm, (0, (total - hm.height) // 2))
        planche.paste(h1, (0, total - h1.height))
    a = np.array(planche)
    fond, vert = fond_masque(a)
    plein = ~fond
    plein = ndimage.binary_opening(plein, iterations=1)
    H = a.shape[0]
    ref = Image.open(next(ICI.glob(f"images/{ident}_classique_bebe.png")))
    out = ICI / "animations" / ident
    out.mkdir(parents=True, exist_ok=True)
    boites = []
    for k, pose in enumerate(POSES):
        li, co = divmod(k, 4)
        y0, y1 = li * H // 3, (li + 1) * H // 3
        x0, x1 = co * W // 4, (co + 1) * W // 4
        m = plein[y0:y1, x0:x1]
        lab, nb = ndimage.label(m)
        if nb == 0:
            boites.append(None)
            continue
        tailles = ndimage.sum(m, lab, range(1, nb + 1))
        garde = np.isin(lab, [i + 1 for i, t in enumerate(tailles) if t > max(25, tailles.max() * 0.004)])
        ys, xs = np.nonzero(garde)
        boites.append((pose, y0, x0, garde, ys.min(), ys.max(), xs.min(), xs.max()))
    # échelle : la pose « assis » prend la hauteur du bébé classique
    assis = boites[4] or next(b for b in boites if b)
    ech = ref.height / (assis[5] - assis[4] + 1)
    for b in boites:
        if not b:
            continue
        pose, y0, x0, garde, ya, yb, xa, xb = b
        bloc = a[y0 + ya:y0 + yb + 1, x0 + xa:x0 + xb + 1]
        alpha = (garde[ya:yb + 1, xa:xb + 1] * 255).astype(np.uint8)
        rgba = np.dstack([bloc, alpha])
        rgba = nettoyer(rgba, vert)
        im = Image.fromarray(rgba, "RGBA")
        w, h = max(1, round(im.width * ech)), max(1, round(im.height * ech))
        im = im.resize((w, h), Image.LANCZOS)
        p = np.array(im)
        p[..., 3] = np.where(p[..., 3] > 110, 255, 0)
        Image.fromarray(p, "RGBA").save(out / f"{pose}.png")
    print("OK", ident, sum(1 for b in boites if b), "poses, échelle", round(ech, 3))


if __name__ == "__main__":
    main()
