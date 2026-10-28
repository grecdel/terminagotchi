"""violet.py NOM : retire le magenta/violet de fond enfermé (pour les créatures SANS violet)."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a and b > g + 60 and r > g + 30 and g < 110:
                p[x, y] = (0, 0, 0, 0)
    im.save(f)
print("violet ok", n)
