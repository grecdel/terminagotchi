"""rose.py NOM : neutralise le rose laissé par le fond magenta (r et b au-dessus de g) en le ramenant vers l'orange."""
import sys
from PIL import Image
D = '/home/claude/depot-android/donnees/bestiaire2/images/'
for s in ('bebe', 'enfant', 'ado', 'adulte', 'ancien'):
    f = f'{D}{sys.argv[1]}_{s}.png'
    im = Image.open(f).convert('RGBA'); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and r > g + 30 and b > g + 30:
                px[x, y] = (r, g, g + (b - g) // 5, a)
    im.save(f)
print('rose', sys.argv[1])
