"""despill.py NOM [vert|magenta|bleu] : retire le liseré de couleur de fond sur les bords des 5 stades
(utile quand les captures sont en JPEG)."""
import sys
from PIL import Image, ImageFilter
D = '/home/claude/depot-android/donnees/bestiaire2/images/'
nom, fond = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else 'vert')
for s in ('bebe', 'enfant', 'ado', 'adulte', 'ancien'):
    f = f'{D}{nom}_{s}.png'
    im = Image.open(f).convert('RGBA')
    a = im.getchannel('A')
    trou = a.point(lambda v: 255 if v == 0 else 0).filter(ImageFilter.MaxFilter(5))   # zone à 2 px du vide
    px, tz = im.load(), trou.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, al = px[x, y]
            if al == 0:
                continue
            bord = tz[x, y]
            if fond == 'vert':
                if bord and g > 170 and r < 150 and b < 150 and g > r + 50 and g > b + 50: px[x, y] = (0, 0, 0, 0)
                elif g > max(r, b) + (0 if bord else 25): px[x, y] = (r, max(r, b), b, al)
            elif fond == 'magenta':
                m = min(r, b)
                if bord and r > 170 and b > 170 and g < 120: px[x, y] = (0, 0, 0, 0)
                elif m > g + (0 if bord else 25): px[x, y] = (r - (m - g) // 2, g, b - (m - g) // 2, al)
            else:
                if bord and b > 170 and r < 110 and g < 110: px[x, y] = (0, 0, 0, 0)
                elif b > max(r, g) + 30: px[x, y] = (r, g, max(r, g) + 30, al)
    im.save(f)
print('despill', nom, fond)
