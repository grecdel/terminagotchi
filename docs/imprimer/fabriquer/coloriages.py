"""Fabrique les 12 coloriages A4 (PDF) à partir des vrais sprites du jeu, et leurs petits aperçus pour le site.
Lancer :  python3 docs/imprimer/fabriquer/coloriages.py [dossier_vue] [id ...]
(outil de fabrication, hors du jeu : Playwright, scikit-learn, scikit-image)
Sorties : site/public/imprimer/coloriages/coloriage_<numéro>_<id>.pdf et .png (petit aperçu pour le site) ;
si on donne un dossier, la page entière y est aussi rangée en PNG 300 ppp, pour la regarder avant de valider."""
import json, sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from contour import contour
from rendu import rendre, POLICES, DEPOT
from choix import CHOIX, BASE

IMG = f"{DEPOT}/donnees/bestiaire2/images/"
OUT = f"{DEPOT}/site/public/imprimer/coloriages/"
VUE = sys.argv[1] if len(sys.argv) > 1 else None
SEULS = set(sys.argv[2:])
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp()
B = {e["id"]: e for e in json.load(open(f"{DEPOT}/donnees/bestiaire2/bestiaire.json"))}

for id_, stade, reglages, niveau in CHOIX:
    if SEULS and id_ not in SEULS:
        continue
    e = B[id_]
    src = f"{IMG}{e['numero']:03d}_{id_}_classique_{stade}.png"
    trait = contour(src, **{**BASE, **reglages})
    tp = f"{TMP}/{id_}_trait.png"
    trait.save(tp)
    html = f"""<!doctype html><meta charset="utf-8"><style>{POLICES}
@page{{size:A4;margin:0}} *{{box-sizing:border-box}}
html,body{{margin:0;background:#fff;color:#000}}
.page{{width:210mm;height:297mm;padding:12mm 13mm 10mm;display:flex;flex-direction:column;position:relative;overflow:hidden}}
.cadre{{position:absolute;inset:7mm;border:1.2mm solid #000;pointer-events:none}}
h1{{font:24pt/1.25 "Press Start 2P";margin:5mm 0 2mm;text-align:center;letter-spacing:.5pt}}
.sous{{font:17pt/1.1 "VT323";text-align:center;margin:0}}
.dessin{{flex:1;display:flex;align-items:center;justify-content:center;min-height:0;padding:3mm 0}}
.dessin img{{max-width:176mm;max-height:100%;object-fit:contain;image-rendering:pixelated}}
.bas{{display:grid;grid-template-columns:44mm 1fr;gap:5mm;align-items:center;border-top:.6mm dashed #000;padding-top:4mm;margin:0 3mm}}
.vraie{{text-align:center;font:13pt/1 "VT323"}} .vraie img{{width:28mm;height:28mm;object-fit:contain;image-rendering:pixelated;display:block;margin:0 auto 1.5mm}}
.txt{{font:15pt/1.15 "VT323"}} .txt b{{font:9pt/1.6 "Press Start 2P"}}
.ligne{{border-bottom:.4mm solid #000;height:9mm;margin-top:1mm}}
.pied{{font:11pt/1.2 "VT323";text-align:center;margin-top:4mm;color:#222}}
</style><div class="page"><div class="cadre"></div>
<h1>Colorie {e['nom']} !</h1>
<p class="sous">#{e['numero']:03d} · famille {e['famille']} · {e['caractere']} · niveau : {niveau}</p>
<div class="dessin"><img src="file://{tp}"></div>
<div class="bas"><div class="vraie"><img src="file://{src}">ses vraies couleurs</div>
<div class="txt"><b>Le savais-tu ?</b><br>{e['fiche']}<br><br>Tu peux aussi inventer ta propre variante. Elle s'appelle :<div class="ligne"></div></div></div>
<p class="pied">Terminagotchi · terminagotchi.com · gratuit, imprime-le autant que tu veux<br>Dessin : les contributeurs de Terminagotchi · licence CC BY-NC-SA 4.0</p>
</div>"""
    hp = f"{TMP}/{id_}.html"
    open(hp, "w").write(html)
    base = f"{OUT}coloriage_{e['numero']:03d}_{id_}"
    grand = f"{VUE or TMP}/coloriage_{e['numero']:03d}_{id_}.png"
    rendre(hp, pdf=base + ".pdf", png=grand, largeur=794, hauteur=1123, fmt="A4", echelle=3.125 if VUE else 1)
    a = Image.open(grand).convert("L")
    a.thumbnail((240, 340), Image.LANCZOS)
    a.save(base + ".png", optimize=True)
    print(base)
