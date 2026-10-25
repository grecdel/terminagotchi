"""planche.py <famille> : planche de contrôle des formes classiques d'une famille (images/)."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ICI = Path(__file__).resolve().parent
fam = sys.argv[1]
b = [e for e in json.loads((ICI / "bestiaire.json").read_text()) if e["famille"] == fam]
S = ["bebe", "enfant", "ado", "adulte", "ancien"]; HT = [50, 80, 115, 150, 180]
try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except OSError: f = None
rows = []
for e in b:
    base = ICI / "images" / f"{e['numero']:03d}_{e['id']}_classique"
    if not Path(f"{base}_bebe.png").exists(): continue
    ims = []
    for s, h in zip(S, HT):
        i = Image.open(f"{base}_{s}.png"); ims.append(i.resize((max(1, int(i.width * h / i.height)), h), Image.LANCZOS))
    rows.append((e, ims))
W = max(sum(i.width for i in r) + 25 * 5 for _, r in rows) + 170
c = Image.new("RGB", (W, len(rows) * 205 + 10), (20, 20, 30)); d = ImageDraw.Draw(c)
for y, (e, r) in enumerate(rows):
    d.text((10, y * 205 + 80), f"#{e['numero']:03d} {e['nom']}", fill=(240, 240, 250), font=f)
    d.text((10, y * 205 + 100), e["rarete"], fill=(255, 175, 0), font=f)
    x = 170
    for i in r: c.paste(i, (x, y * 205 + 195 - i.height), i); x += i.width + 25
out = ICI / "images" / f"_planche_{fam}.png"; c.save(out); print(out, c.size)
