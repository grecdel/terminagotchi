"""aile.py NOM : ailes translucides rosies par le fond magenta -> ambre/crème pâle."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if not a: continue
            if r > 180 and b > g + 15 and r > g + 20 and b > 120:   # rose / lilas clair
                m = (r + g + b) // 3; r, g, b = min(255, m + 12), min(255, m + 10), min(255, m + 2)
            if r > 220 and g > 150 and b > 130 and r - g < 80 and r - b > 20:  # saumon
                r, g, b = min(255, r - 6), min(255, g + 18), min(255, b + 4)
            if r > 200 and g < 120 and b < 150 and r - b > 60 and b > g:  # rose vif
                r, g, b = r, min(255, g + 70), max(0, b - 40)
            p[x, y] = (r, g, b, a)
    im.save(f)
print("aile ok", n)
