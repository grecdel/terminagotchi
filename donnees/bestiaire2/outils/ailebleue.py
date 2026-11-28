"""ailebleue.py NOM [teinte r g b] : ailes translucides bleuies par le fond bleu -> teinte claire (vert d'eau par défaut)."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
t = tuple(int(v) for v in sys.argv[2:5]) if len(sys.argv) >= 5 else (10, 40, 30)
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a and b > r + 40 and b > g + 30 and b > 150:
                m = (r + g + b) // 3; p[x, y] = (min(255, m + t[0]), min(255, m + t[1]), min(255, m + t[2]), a)
    im.save(f)
print("ailebleue ok", n)
