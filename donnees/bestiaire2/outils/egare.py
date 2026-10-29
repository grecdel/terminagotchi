"""egare.py NOM stade [stade…] : retire les morceaux isolés collés au bord droit (morceau du stade suivant)."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
D = '/home/claude/depot-android/donnees/bestiaire2/images/'
for s in sys.argv[2:]:
    f = f'{D}{sys.argv[1]}_{s}.png'
    im = Image.open(f).convert('RGBA'); px = np.array(im)
    a = px[:, :, 3] > 0
    lab, n = ndimage.label(a, structure=np.ones((3, 3)))
    tailles = ndimage.sum(a, lab, range(1, n + 1)); grand = tailles.max()
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if tailles[i] < grand * 0.15 and sl[1].stop >= a.shape[1] - 2:
            px[lab == i + 1, 3] = 0
    ys, xs = np.nonzero(px[:, :, 3])
    Image.fromarray(px).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).save(f)
    print('egare', s)
