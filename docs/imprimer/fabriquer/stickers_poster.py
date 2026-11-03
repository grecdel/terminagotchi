"""Fabrique la planche de stickers A4 et le poster A3 de la carte (sans noms des mondes), en deux versions :
fond sombre et fond blanc (moins d'encre). Lancer :  python3 docs/imprimer/fabriquer/stickers_poster.py [dossier_vue]
Sorties : site/public/imprimer/stickers_A4.pdf, poster_A3.pdf, poster_A3_fond_blanc.pdf et leurs petits aperçus JPEG."""
import json, sys, os, tempfile
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from rendu import rendre, POLICES, DEPOT

IMG = f"{DEPOT}/donnees/bestiaire2/images/"
OEUF = f"{DEPOT}/donnees/oeufs/"
OUT = f"{DEPOT}/site/public/imprimer/"
VUE = sys.argv[1] if len(sys.argv) > 1 else None
TMP = tempfile.mkdtemp()
os.makedirs(OUT, exist_ok=True)
B = {e["id"]: e for e in json.load(open(f"{DEPOT}/donnees/bestiaire2/bestiaire.json"))}
LISTE = [("gouttelin", "enfant"), ("glandouille", "enfant"), ("sporichon", "enfant"), ("poulpiot", "enfant"), ("rugisoleil", "enfant"),
         ("braisillon", "bebe"), ("zapiot", "enfant"), ("plouftin", "enfant"), ("etoilapin", "enfant"), ("lanternix", "enfant"),
         ("gloupi", "enfant"), ("bourdonjon", "enfant"), ("givrichon", "enfant"), ("lumignon", "enfant"), ("scarabouille", "enfant")]


def sticker(src, cible=440, bord=26):
    """Le sprite, un bord blanc tout autour et un trait gris de découpe ; posé sur du blanc (la feuille)."""
    im = Image.open(src).convert("RGBA")
    f = cible / max(im.size)
    im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    W, H = im.width + 2 * bord + 8, im.height + 2 * bord + 8
    fond = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fond.paste(im, (bord + 4, bord + 4), im)
    a = np.array(fond)[..., 3] > 40
    yy, xx = np.mgrid[-bord:bord + 1, -bord:bord + 1]
    m = ndimage.binary_fill_holes(ndimage.binary_dilation(a, structure=xx ** 2 + yy ** 2 <= bord ** 2))
    r, n = ndimage.label(m)
    if n > 1:
        t = np.bincount(r.ravel()); t[0] = 0; m = r == t.argmax()
        fa = np.array(fond); fa[~m] = 0; fond = Image.fromarray(fa)
    trait = m & ~ndimage.binary_erosion(m, iterations=3)
    arr = np.full((H, W, 4), 255, np.uint8)
    arr[trait] = (150, 150, 150, 255)
    out = Image.fromarray(arr)
    out.alpha_composite(fond)
    return out.convert("RGB")


def apercu(png, dest, taille):
    a = Image.open(png).convert("RGB")
    a.thumbnail(taille, Image.LANCZOS)
    a.save(dest, quality=82, optimize=True)


# ---- planche de stickers A4
cartes = []
for id_, st in LISTE:
    e = B[id_]
    p = f"{TMP}/{id_}.jpg"
    sticker(f"{IMG}{e['numero']:03d}_{id_}_classique_{st}.png").save(p, quality=90)
    cartes.append((p, e["nom"]))
for t in ("feu", "eau", "plante"):
    p = f"{TMP}/oeuf_{t}.jpg"
    sticker(f"{OEUF}oeuf_{t}_intact.png", 320).save(p, quality=90)
    cartes.append((p, f"œuf {t}"))
html_cartes = "".join(f'<div class="s"><img src="file://{p}"><span>{n}</span></div>' for p, n in cartes)
html = f"""<!doctype html><meta charset="utf-8"><style>{POLICES}
@page{{size:A4;margin:0}} *{{box-sizing:border-box}} html,body{{margin:0;background:#fff}}
.page{{width:210mm;height:297mm;padding:9mm 9mm 7mm;display:flex;flex-direction:column}}
h1{{font:15pt/1.3 "Press Start 2P";margin:0 0 1mm;text-align:center}}
.aide{{font:13pt/1.1 "VT323";text-align:center;margin:0 0 3mm;color:#333}}
.g{{flex:1;display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:1fr;gap:2mm 3mm;align-items:center;justify-items:center}}
.s{{display:flex;flex-direction:column;align-items:center;height:100%;justify-content:center;min-height:0}}
.s img{{max-width:44mm;max-height:38mm;object-fit:contain}}
.s span{{font:11pt/1 "VT323";color:#555;margin-top:.5mm}}
.pr{{background:#06110a;color:#5cff8f;font:11pt/1.4 "Press Start 2P";padding:4mm 5mm;border-radius:2mm;outline:1.2mm solid #fff;box-shadow:0 0 0 1.6mm #969696;white-space:nowrap}}
.pied{{font:10.5pt/1.2 "VT323";text-align:center;color:#333;margin-top:2mm}}
</style><div class="page">
<h1>Stickers Terminagotchi</h1>
<p class="aide">Imprime sur une feuille autocollante A4 (ou sur du papier, avec de la colle). Découpe le long du trait gris.</p>
<div class="g">{html_cartes}<div class="s"><div class="pr">~ $ ls_</div></div><div class="s"><div class="pr">echo bonjour</div></div></div>
<p class="pied">Fichier gratuit · terminagotchi.com · Dessins : les contributeurs de Terminagotchi · licence CC BY-NC-SA 4.0 (pas de revente)</p>
</div>"""
hp = f"{TMP}/stickers.html"; open(hp, "w").write(html)
png = f"{VUE or TMP}/stickers_A4.png"
rendre(hp, pdf=OUT + "stickers_A4.pdf", png=png, largeur=794, hauteur=1123, fmt="A4", echelle=2 if VUE else 1)
apercu(png, OUT + "stickers_A4.jpg", (240, 340))

# ---- poster A3 de la carte, sans noms des mondes ; fond sombre et fond blanc
carte = f"{TMP}/monde.jpg"
Image.open(f"{DEPOT}/donnees/illustrations/monde.png").convert("RGB").save(carte, quality=92)
for nom, fond, titre, texte, doux, cadre in (("poster_A3", "#06110a", "#5cff8f", "#9fd8b0", "#6fa883", "#1f3a28"),
                                              ("poster_A3_fond_blanc", "#ffffff", "#0b6b2e", "#1d3a27", "#3d5a47", "#9fb8a6")):
    html = f"""<!doctype html><meta charset="utf-8"><style>{POLICES}
@page{{size:A3 landscape;margin:0}} *{{box-sizing:border-box}} html,body{{margin:0;background:{fond}}}
.page{{width:420mm;height:297mm;padding:10mm;display:flex;flex-direction:column;align-items:center;justify-content:center;background:{fond}}}
h1{{font:30pt/1.2 "Press Start 2P";color:{titre};margin:2mm 0 2mm;letter-spacing:2pt}}
.sous{{font:22pt/1 "VT323";margin:0 0 5mm;color:{texte}}}
.img{{width:400mm;height:225mm;background:url(file://{carte}) center/cover;box-shadow:0 0 0 1.5mm {cadre};image-rendering:auto}}
.pied{{display:flex;justify-content:space-between;width:400mm;font:15pt/1 "VT323";color:{doux};margin-top:4mm}}
.pied b{{font:11pt/1 "Press Start 2P";color:{titre}}}
</style><div class="page">
<h1>LE TERMINAWORLD</h1>
<p class="sous">~ $ tape une commande, et le monde se réveille_</p>
<div class="img"></div>
<div class="pied"><span><b>Terminagotchi</b> · terminagotchi.com · poster gratuit à imprimer</span><span>Illustration : les contributeurs de Terminagotchi · CC BY-NC-SA 4.0</span></div>
</div>"""
    hp = f"{TMP}/{nom}.html"; open(hp, "w").write(html)
    png = f"{VUE or TMP}/{nom}.png"
    rendre(hp, pdf=OUT + nom + ".pdf", png=png, largeur=1587, hauteur=1123, fmt="A3", paysage=True, echelle=1)
    apercu(png, OUT + nom + ".jpg", (340, 240))
print("ok")
