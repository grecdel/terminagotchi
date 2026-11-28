"""fumee.py NOM : fumée/brume teintée violet par le fond magenta -> gris."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a and r > g + 25 and b > g + 25 and b > r - 40:
                m = (r + g + b) // 3; p[x, y] = (m, m, m + 4, a)
    im.save(f)
print("fumee ok", n)
