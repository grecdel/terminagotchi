"""bande.py image.png sortie_prefixe nom1 nom2 ... : découpe les créatures d'une bande sur fond magenta."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
src, pre, noms = sys.argv[1], sys.argv[2], sys.argv[3:]
a = np.asarray(Image.open(src).convert("RGB")).astype(float)
import os
FOND=list(np.median(a[:5,:].reshape(-1,3),axis=0)) if os.environ.get("VERT") else [255,0,255]
d = np.linalg.norm(a - FOND, axis=-1)
import os
TOL=float(os.environ.get("TOL",110)); TROU=float(os.environ.get("TROU",TOL))
pl, _ = ndimage.label(d < TOL)
bords = set(np.unique(np.concatenate([pl[0], pl[-1], pl[:, 0], pl[:, -1]]))) - {0}
m = ndimage.binary_opening(~(np.isin(pl, list(bords)) | (d < TROU)), iterations=1)
lab, n = ndimage.label(m)
t = ndimage.sum(m, lab, range(1, n + 1))
gros = list(np.argsort(t)[::-1][:len(noms)] + 1)
gros.sort(key=lambda k: ndimage.center_of_mass(m, lab, k)[1])
cx = [ndimage.center_of_mass(m, lab, k)[1] for k in gros]
aff = np.zeros_like(lab)
for k in range(1, n + 1):
    if t[k-1] < 15: continue
    c = ndimage.center_of_mass(m, lab, k)[1]
    aff[lab == k] = gros[int(np.argmin([abs(c - x) for x in cx]))] if k not in gros else k
for nom, k in zip(noms, gros):
    msk = aff == k
    b = a.copy(); bord = msk & ~ndimage.binary_erosion(msk, iterations=2)
    if FOND[1] > 200:
        tout = msk & (b[...,1] > np.maximum(b[...,0], b[...,2]) + 25); b[...,1][tout] = np.maximum(b[...,0], b[...,2])[tout]
        b[..., 1][bord] = np.minimum(b[..., 1][bord], np.maximum(b[..., 0][bord], b[..., 2][bord]) + 30)
    else:
        g = b[..., 1][bord]; b[..., 0][bord] = np.minimum(b[..., 0][bord], g + 60); b[..., 2][bord] = np.minimum(b[..., 2][bord], g + 60)
    img = Image.fromarray(np.dstack([b.clip(0,255).astype("uint8"), (msk*255).astype("uint8")]), "RGBA")
    img = img.crop(img.getbbox()); img.save(f"{pre}_{nom}.png"); print(nom, img.size)
