"""bande.py image.png sortie_prefixe nom1 nom2 ... : découpe les créatures d'une bande sur fond magenta."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
src, pre, noms = sys.argv[1], sys.argv[2], sys.argv[3:]
a = np.asarray(Image.open(src).convert("RGB")).astype(float)
import os
FOND=[float(x) for x in os.environ["FOND"].split(",")] if os.environ.get("FOND") else (list(np.median(a[:5,:].reshape(-1,3),axis=0)) if os.environ.get("VERT") else [255,0,255])
d = np.linalg.norm(a - FOND, axis=-1)
import os
TOL=float(os.environ.get("TOL",110)); TROU=float(os.environ.get("TROU",TOL))
pl, _ = ndimage.label(d < TOL)
bords = set(np.unique(np.concatenate([pl[0], pl[-1], pl[:, 0], pl[:, -1]]))) - {0}
m = ndimage.binary_opening(~(np.isin(pl, list(bords)) | (d < TROU)), iterations=1)
lab, n = ndimage.label(m)
t = ndimage.sum(m, lab, range(1, n + 1))
garde = np.isin(lab, 1 + np.where(t >= 15)[0])
# découpe par colonnes vides : les morceaux détachés (fumée, crânes flottants…) restent avec leur créature
col = garde.any(axis=0)
segs, x = [], 0
while x < len(col):
    if col[x]:
        x0 = x
        while x < len(col) and col[x]: x += 1
        segs.append([x0, x])
    else:
        x += 1
while len(segs) > len(noms):            # on recolle les trous les plus étroits
    i = min(range(len(segs) - 1), key=lambda i: segs[i + 1][0] - segs[i][1])
    segs[i:i + 2] = [[segs[i][0], segs[i + 1][1]]]
occ = garde.sum(axis=0)
while 0 < len(segs) < len(noms):         # deux créatures qui se touchent : on coupe la plus large à sa colonne la plus creuse
    i = max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])
    x0, x1 = segs[i]; ga, gb = x0 + (x1 - x0) * 3 // 10, x0 + (x1 - x0) * 7 // 10
    xc = ga + int(np.argmin(occ[ga:gb]))
    segs[i:i + 1] = [[x0, xc], [xc, x1]]
aff = np.zeros_like(lab)
if len(segs) == len(noms):
    gros = list(range(1, len(noms) + 1))
    for k, (x0, x1) in enumerate(segs, 1):
        z = np.zeros_like(garde); z[:, x0:x1] = True
        aff[garde & z] = k
else:                                    # créatures qui se chevauchent : on revient aux plus gros morceaux
    print("  (chevauchement : découpe par morceaux)")
    gros = list(np.argsort(t)[::-1][:len(noms)] + 1)
    gros.sort(key=lambda k: ndimage.center_of_mass(m, lab, k)[1])
    cx = [ndimage.center_of_mass(m, lab, k)[1] for k in gros]
    for k in range(1, n + 1):
        if t[k-1] < 15: continue
        c = ndimage.center_of_mass(m, lab, k)[1]
        aff[lab == k] = gros[int(np.argmin([abs(c - x) for x in cx]))] if k not in gros else k
for nom, k in zip(noms, gros):
    msk = aff == k
    b = a.copy(); bord = msk & ~ndimage.binary_erosion(msk, iterations=2)
    if FOND[1] > 200:
        if os.environ.get("DESPILL"):
            tout = msk & (b[...,1] > np.maximum(b[...,0], b[...,2]) + 25); b[...,1][tout] = np.maximum(b[...,0], b[...,2])[tout]
        b[..., 1][bord] = np.minimum(b[..., 1][bord], np.maximum(b[..., 0][bord], b[..., 2][bord]) + 30)
    elif FOND[0] > 200:
        g = b[..., 1][bord]; b[..., 0][bord] = np.minimum(b[..., 0][bord], g + 60); b[..., 2][bord] = np.minimum(b[..., 2][bord], g + 60)
    img = Image.fromarray(np.dstack([b.clip(0,255).astype("uint8"), (msk*255).astype("uint8")]), "RGBA")
    img = img.crop(img.getbbox()); img.save(f"{pre}_{nom}.png"); print(nom, img.size)
