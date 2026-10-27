"""Fabrique les œufs du jeu (9 types de biome × 3 états) à partir des dessins de donnees/oeufs/.

    python3 donnees/bestiaire2/generer_oeufs.py [--apercu dossier]

Entrées : donnees/oeufs/oeuf_<type>_<etat>.png (types de donnees/biomes.json ; états intact, fissure, eclosion).
Sorties (UNE source, deux copies identiques, vérifiées par pc/outils/test_intro.py et tests/jvm/Intro.kt) :
  donnees/oeufs/oeufs.json  →  pc/tg/oeufs.json  et  app/src/main/assets/oeufs.json

Chaque dessin est réduit en gros pixels (boîte, alpha franc), aligné sur le bas et le milieu du corps de l'œuf
(mêmes proportions pour les 3 états d'un type), son contour assombri (net même tout petit), puis ses couleurs
réduites à une palette par type (NB_COULEURS, communes aux 3 états). Deux tailles :
  « grand » : l'œuf de l'intro (cadre W×H, corps LARGEUR_GRAND pixels) ;
  « petit » : l'œuf de l'écran principal, du widget, de la notification (cadre 18×16 comme la créature).
Les lignes de caractères : « . » transparent, A…Z puis 0…9 les couleurs de la palette ; les minuscules sont les
effets de l'animation (même rôle qu'avant) : f fêlure qui luit, c éclair blanc, h halo du contour, y étincelle.
« feles » : les pixels de la 1re fêlure (dessinée sur l'œuf intact) et de la 3e (sur l'œuf fissuré), calculés
ici pour chaque type (un trait en zigzag qui ne sort pas de la coquille). « etincelles » : 2 jeux de 5 points.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
SRC = RACINE / "donnees" / "oeufs"
ETATS = ["intact", "fissure", "eclosion"]
NB_COULEURS = 22
CHIFFRES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TAILLES = {"grand": (26, 26, 16), "petit": (18, 16, 12)}      # cadre W, H, largeur du corps
# la lueur des fêlures et du halo, par type (claire sur un œuf sombre, vive sur un œuf clair : on la voit)
LUEUR = {"feu": "#ffd36b", "eau": "#2a6cff", "glace": "#8a5cff", "plante": "#e6ff8a", "roche": "#ffc45a",
         "ciel": "#ffae00", "ombre": "#f0a0ff", "machine": "#7ff6ff", "poison": "#d4ff4a"}
# fêlures en coordonnées du corps (0..1 en x depuis la gauche, 0..1 en y depuis le haut)
FELE1 = [(0.58, 0.18), (0.66, 0.30), (0.56, 0.40), (0.66, 0.52)]
FELE3 = [(0.14, 0.58), (0.28, 0.50), (0.40, 0.60), (0.52, 0.50), (0.64, 0.60), (0.76, 0.50), (0.88, 0.58)]


def types():
    return [t["id"] for t in json.loads((RACINE / "donnees" / "biomes.json").read_text(encoding="utf-8"))["types"]]


def nettoyer(img):
    """Enlève les petits traits sombres détachés (restes du détourage), garde les étincelles colorées."""
    a = np.asarray(img).copy()
    m = a[..., 3] > 0
    lab, n = ndimage.label(m)
    if n > 1:
        tailles = ndimage.sum(m, lab, range(1, n + 1))
        k0 = int(np.argmax(tailles)) + 1
        for k in range(1, n + 1):
            if k == k0:
                continue
            px = a[lab == k][:, :3].astype(int)
            if px.max(axis=1).mean() < 60:
                a[lab == k] = 0
    return Image.fromarray(a, "RGBA")


def corps(a):
    """(largeur, x du milieu, y du bas) du corps de l'œuf : la plus grande tache, mesurée près du bas."""
    m = a[..., 3] > 0
    lab, n = ndimage.label(m)
    k = int(np.argmax(ndimage.sum(m, lab, range(1, n + 1)))) + 1
    ys, xs = np.where(lab == k)
    yb = ys.max()
    bas = ys >= yb - max(4, a.shape[0] // 12)
    largeur = max(xs[ys == y].max() - xs[ys == y].min() + 1 for y in range(yb - a.shape[0] // 2, yb + 1) if (ys == y).any())
    return largeur, xs[bas].mean(), yb


def reduire(img, f):
    w, h = max(1, round(img.width * f)), max(1, round(img.height * f))
    a = np.asarray(img.resize((w, h), Image.BOX)).copy()
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    a[a[..., 3] == 0] = 0
    return a


def contour(a):
    """Le bord de chaque tache assombri : un trait net autour de l'œuf, même en tout petit."""
    m = a[..., 3] > 0
    lab, n = ndimage.label(m)
    tailles = ndimage.sum(m, lab, range(1, n + 1))
    gros = np.isin(lab, [k + 1 for k in range(n) if tailles[k] >= 12])     # les étincelles restent lumineuses
    bord = gros & ~ndimage.binary_erosion(m)
    a = a.copy()
    a[bord, :3] = (a[bord, :3].astype(float) * 0.35).astype(np.uint8)
    return a


def poser(a, W, H, cx, yb, f):
    """Place l'image réduite dans le cadre W×H : corps au milieu, bas du corps 1 pixel au-dessus du bas."""
    out = np.zeros((H, W, 4), np.uint8)
    ox = int(round(W / 2 - cx * f))
    oy = int(H - 2 - round(yb * f))
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            X, Y = x + ox, y + oy
            if 0 <= X < W and 0 <= Y < H and a[y, x, 3]:
                out[Y, X] = a[y, x]
    return out


def palette(cadres):
    pts = np.concatenate([c[c[..., 3] > 0][:, :3] for c in cadres])
    q = Image.fromarray(pts.reshape(1, -1, 3)).quantize(NB_COULEURS, method=Image.MEDIANCUT)
    pal = q.getpalette()[:3 * NB_COULEURS]
    return [tuple(pal[k:k + 3]) for k in range(0, len(pal), 3)], q


def lignes(c, pal_img):
    q = np.asarray(Image.fromarray(c[..., :3]).quantize(palette=pal_img, dither=Image.Dither.NONE))
    return ["".join(CHIFFRES[q[y, x]] if c[y, x, 3] else "." for x in range(c.shape[1])) for y in range(c.shape[0])]


def boite(rows):
    """(x0, y0, x1, y1) du corps de l'œuf intact."""
    ys = [y for y, r in enumerate(rows) if r.strip(".")]
    xs = [x for r in rows for x, ch in enumerate(r) if ch != "."]
    return min(xs), min(ys), max(xs), max(ys)


def trait(rows, pts, b):
    """Les pixels d'un zigzag (coordonnées du corps) qui tombent sur la coquille."""
    x0, y0, x1, y1 = b
    P = [(x0 + u * (x1 - x0), y0 + v * (y1 - y0)) for u, v in pts]
    out = []
    for (ax, ay), (bx, by) in zip(P, P[1:]):
        n = int(max(abs(bx - ax), abs(by - ay)) * 2) + 1
        for s in range(n + 1):
            x, y = round(ax + (bx - ax) * s / n), round(ay + (by - ay) * s / n)
            if 0 <= y < len(rows) and 0 <= x < len(rows[y]) and rows[y][x] != "." and [x, y] not in out:
                out.append([x, y])
    return out


def etincelles(W, H):
    a = [(1, 3), (W - 2, 5), (0, H * 2 // 3), (W - 1, H - 5), (W // 2, 0)]
    b = [(2, H // 2 - 2), (W - 3, 1), (1, H - 3), (W - 2, H // 2 + 1), (W // 2 - 2, 1)]
    return [[list(p) for p in a], [list(p) for p in b]]


def main():
    sortie = {"_doc": __doc__.strip().splitlines()[0] + " Généré par donnees/bestiaire2/generer_oeufs.py : ne pas modifier.",
              "version": 1, "etats": ETATS, "effets": {"c": "#ffffff"}, "tailles": {}, "types": {}}
    for nom, (W, H, LB) in TAILLES.items():
        sortie["tailles"][nom] = [W, H]
    sortie["etincelles"] = etincelles(*TAILLES["grand"][:2])
    for ty in types():
        imgs = [nettoyer(Image.open(SRC / f"oeuf_{ty}_{e}.png").convert("RGBA")) for e in ETATS]
        mesures = [corps(np.asarray(i)) for i in imgs]
        lb0 = mesures[0][0]
        cadres = {}
        for nom, (W, H, LB) in TAILLES.items():
            f = LB / lb0                                   # même échelle pour les 3 états
            cadres[nom] = [contour(poser(reduire(i, f), W, H, m[1], m[2], f)) for i, m in zip(imgs, mesures)]
        pal, pal_img = palette(cadres["grand"] + cadres["petit"])
        d = {"palette": ["#%02x%02x%02x" % c for c in pal], "lueur": LUEUR[ty]}
        for nom in TAILLES:
            d[nom] = {e: lignes(c, pal_img) for e, c in zip(ETATS, cadres[nom])}
        g = d["grand"]
        d["feles"] = [trait(g["intact"], FELE1, boite(g["intact"])), trait(g["fissure"], FELE3, boite(g["intact"]))]
        sortie["types"][ty] = d
    texte = json.dumps(sortie, ensure_ascii=False, indent=1) + "\n"
    for p in (SRC / "oeufs.json", RACINE / "pc/tg/oeufs.json", RACINE / "app/src/main/assets/oeufs.json"):
        p.write_text(texte, encoding="utf-8")
    print(f"{len(sortie['types'])} types × {len(ETATS)} états × {len(TAILLES)} tailles, oeufs.json {len(texte) // 1024} Ko")
    if "--apercu" in sys.argv:
        apercu(sortie, Path(sys.argv[sys.argv.index("--apercu") + 1]))


def apercu(d, dossier, e=8):
    """Une planche PNG : chaque type, les 3 états en grand puis en petit."""
    dossier.mkdir(parents=True, exist_ok=True)
    W, H = d["tailles"]["grand"]
    img = Image.new("RGBA", ((W * 3 + 18 * 2 + 8) * e, (H + 2) * len(d["types"]) * e), (22, 26, 34, 255))
    for j, (ty, x) in enumerate(d["types"].items()):
        pal = {CHIFFRES[k]: c for k, c in enumerate(x["palette"])}
        cases = [(x["grand"][s], k * W) for k, s in enumerate(ETATS)] + [(x["petit"][s], 3 * W + 4 + k * 18) for k, s in enumerate(ETATS[:2])]
        for rows, ox in cases:
            for yy, r in enumerate(rows):
                for xx, ch in enumerate(r):
                    if ch in pal:
                        c = tuple(int(pal[ch][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
                        img.paste(c, ((ox + xx) * e, (j * (H + 2) + yy) * e, (ox + xx + 1) * e, (j * (H + 2) + yy + 1) * e))
    img.save(dossier / "planche_oeufs.png")


if __name__ == "__main__":
    main()
