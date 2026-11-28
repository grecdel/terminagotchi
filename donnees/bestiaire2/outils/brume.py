"""brume.py NOM : désature la brume teintée par le fond (rose sur magenta, bleue sur bleu)."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if not a: continue
            rose = r > g + 18 and b > g + 18 and b > 120 and abs(r - b) < 90
            bleu = len(sys.argv) > 2 and sys.argv[2] == "b" and b > r + 40 and b > g + 40
            vert = len(sys.argv) > 2 and sys.argv[2] == "v" and g > r + 25 and g > b + 25
            if rose or bleu or vert:
                m = (r + g + b) // 3; k = 0.95
                p[x, y] = (int(r + (m - r) * k), int(g + (m + 8 - g) * k), int(b + (m + 12 - b) * k), a)
    im.save(f)
print("brume ok", n)
