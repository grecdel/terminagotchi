"""frange.py NOM : assombrit en violet les franges magenta vif laissées par le fond."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a and r > 150 and b > 150 and g < 110:
                p[x, y] = (int(r * 0.5), int(g * 0.6 + 10), int(b * 0.75), a)
    im.save(f)
print("frange ok", n)
