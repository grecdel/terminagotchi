"""planche_variantes.py <famille> : planche de contrôle des VARIANTES d'une famille (images/).
Une ligne par variante dessinée (classique en premier), 5 stades côte à côte, bandeau par espèce."""
import json, sys, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ICI = Path(__file__).resolve().parent
fam = sys.argv[1]
b = [e for e in json.loads((ICI / "bestiaire.json").read_text()) if e["famille"] == fam]
S = ["bebe", "enfant", "ado", "adulte", "ancien"]; HT = [36, 56, 80, 104, 124]
try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
except OSError: f = None
rows = []
for e in b:
    for v in e["variantes"]:
        base = ICI / "images" / f"{e['numero']:03d}_{e['id']}_{v['id']}"
        base = Path(unicodedata.normalize("NFKD", str(base)).encode("ascii", "ignore").decode())
        if not Path(f"{base}_bebe.png").exists():
            continue
        ims = []
        for s, h in zip(S, HT):
            i = Image.open(f"{base}_{s}.png").convert("RGBA")
            ims.append(i.resize((max(1, int(i.width * h / i.height)), h), Image.LANCZOS))
        rows.append((e, v, ims))
if not rows:
    sys.exit("aucune variante")
LH = 140
W = max(sum(i.width for i in r) + 18 * 5 for _, _, r in rows) + 200
c = Image.new("RGB", (W, len(rows) * LH + 10), (20, 20, 30)); d = ImageDraw.Draw(c)
for y, (e, v, r) in enumerate(rows):
    if v["id"] == "classique" and y:
        d.line((0, y * LH + 2, W, y * LH + 2), fill=(70, 70, 90), width=2)
    d.text((10, y * LH + 50), f"#{e['numero']:03d} {e['nom']}", fill=(240, 240, 250), font=f)
    d.text((10, y * LH + 68), v["nom"], fill=(255, 175, 0) if v["id"] != "classique" else (150, 150, 170), font=f)
    x = 200
    for i in r:
        c.paste(i, (x, y * LH + 132 - i.height), i); x += i.width + 18
out = ICI / "images" / f"_planche_variantes_{fam}.png"; c.save(out); print(out, c.size, len(rows))
