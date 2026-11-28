"""integrer.py gauche.png droite.png NNN_id_variante : recolle les deux moitiés capturées et découpe les 5 stades.
Résultat : donnees/bestiaire2/images/NNN_id_variante_{bebe,enfant,ado,adulte,ancien}.png"""
import os, subprocess, sys
from pathlib import Path
from PIL import Image
ICI = Path(__file__).resolve().parent
g, d, nom = sys.argv[1:4]
a, b = [Image.open(x).convert("RGB") for x in (g, d)]
a, b = [x.crop((0, 4, x.width, x.height - 4)) for x in (a, b)]   # bords : la bande grise du cadre
from PIL import ImageDraw
for x in (a, b):                     # efface le curseur de souris éventuel (coin haut)
    ImageDraw.Draw(x).rectangle((0, 0, x.width, 28), fill=x.getpixel((x.width // 2, 2)))
c = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), a.getpixel((2, 2)))
c.paste(a, (0, 0)); c.paste(b, (a.width, 0))
(ICI / "images").mkdir(exist_ok=True)
tmp = ICI / "images" / f"_{nom}.png"; c.save(tmp)
env = dict(os.environ, TOL="80", TROU="40")
fond = c.getpixel((2, 2))
if fond[1] > 150: env["VERT"] = "1"
elif fond[2] > 150 and fond[0] < 100: env["FOND"] = ",".join(map(str, fond))
subprocess.run([sys.executable, str(ICI.parent / "animation" / "decoupe_bande.py"), str(tmp), str(ICI / "images" / nom),
                "bebe", "enfant", "ado", "adulte", "ancien"], env=env, check=True)
tmp.unlink()
