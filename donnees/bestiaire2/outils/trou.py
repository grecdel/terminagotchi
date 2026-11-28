"""trou.py NOM [couleur] : rend transparent le fond enfermé (magenta ou bleu) qui n'a pas été détouré."""
import sys, glob, unicodedata
from PIL import Image
n = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
c = {"m": (255, 0, 255), "b": (0, 0, 255), "v": (0, 255, 0)}[sys.argv[2] if len(sys.argv) > 2 else "m"]
for f in glob.glob(f"/home/claude/depot-android/donnees/bestiaire2/images/{n}_*.png"):
    im = Image.open(f).convert("RGBA"); p = im.load(); k = 0
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = p[x, y]
            if a and ((r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2) ** .5 < 95:
                p[x, y] = (0, 0, 0, 0); k += 1
    im.save(f); print(f.rsplit("/", 1)[1], k)
