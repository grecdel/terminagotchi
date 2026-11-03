"""Un vrai sprite -> dessin à colorier (noir sur blanc). Les traits sombres du dessin d'origine restent des traits,
les grandes zones de couleur différentes sont séparées par un trait fin, la silhouette a un trait épais."""
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from sklearn.cluster import KMeans
from skimage.color import rgb2lab

def contour(src, haut=110, k=5, mini=40, E=16, seuil=70, garder_sombre=True, trait_min=5, sombres=True, aplats=True, gros_k=4, squelette=True, pupille=0, noir=False):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    petit = im.resize((round(w * haut / h), haut), Image.BOX)
    a = np.array(petit).astype(float)
    op = a[..., 3] > 120
    op = ndimage.binary_opening(op) | op
    rgb = a[..., :3] / 255
    lab3 = rgb2lab(rgb)
    sombre = op & (lab3[..., 0] < seuil)
    clair = op & ~sombre
    lab = np.zeros(op.shape, int)
    X = lab3[clair][:, 1:] * 1.0  # teinte seulement (a, b) + un peu de clarté
    X = np.c_[X, lab3[clair][:, 0] * 0.35]
    km = KMeans(n_clusters=k, n_init=4, random_state=1).fit(X)
    lab[clair] = km.labels_ + 1
    lab[sombre] = -1
    # le liseré sombre du sprite (le tour de la bestiole) n'est pas une zone : il est rempli par l'intérieur
    anneau = op & ~ndimage.binary_erosion(op, iterations=2) & (lab3[..., 0] < 45)
    lab[anneau] = -1
    # les grands aplats sombres (capuche, visage dans l'ombre…) deviennent une zone à colorier
    gros_aplats = ndimage.binary_opening(sombre & ~anneau, structure=np.ones((4, 4)))
    ra, na = ndimage.label(gros_aplats)
    ta = np.bincount(ra.ravel())
    pupilles = np.zeros_like(gros_aplats)  # les petits ronds sombres (pupilles, narines) restent noirs
    for i in range(1, na + 1):
        if ta[i] <= pupille: pupilles |= ra == i; gros_aplats[ra == i] = False
    if noir: pupilles |= gros_aplats  # les grands aplats très sombres restent noirs (comme l'encre d'un album)
    elif aplats: lab[gros_aplats] = k + 1
    while (lab == -1).any():
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            v = np.roll(lab, (dy, dx), (0, 1)); m = (lab == -1) & (v > 0); lab[m] = v[m]
        if not ((lab == -1) & ndimage.binary_dilation(lab > 0)).any(): lab[lab == -1] = 1
    reg = np.zeros_like(lab); n = 0
    for c in range(1, k + 2):
        r, nc = ndimage.label(lab == c); reg[r > 0] = r[r > 0] + n; n += nc
    for _ in range(8):
        t = np.bincount(reg.ravel(), minlength=n + 1)
        petits = [i for i in range(1, len(t)) if 0 < t[i] < mini]
        if not petits: break
        for i in petits:
            m = reg == i
            bord = ndimage.binary_dilation(m) & ~m & (reg > 0)
            if bord.any(): reg[m] = np.bincount(reg[bord]).argmax()
    for _ in range(2):
        Hh, Ww = reg.shape; pp = np.pad(reg, 1)
        st = np.stack([pp[y:y+Hh, x:x+Ww] for y in range(3) for x in range(3)])
        new = reg.copy()
        for yy, xx in zip(*np.nonzero(reg)):
            v = st[:, yy, xx]; v = v[v > 0]; vals, cnt = np.unique(v, return_counts=True)
            if cnt.max() >= 6: new[yy, xx] = vals[cnt.argmax()]
        reg = new
    # traits sombres du dessin : on garde les lignes fines (pas les grands aplats sombres)
    trait = sombre & ~anneau
    gros = ndimage.binary_opening(sombre, structure=np.ones((gros_k, gros_k)))
    if garder_sombre: trait &= ~gros
    r, nr = ndimage.label(trait, structure=np.ones((3, 3)))
    tl = np.bincount(r.ravel())
    for i in range(1, nr + 1):
        if tl[i] < trait_min: trait[r == i] = False
    if squelette:  # les traits sombres deviennent des lignes d'un pixel (pas de taches)
        from skimage.morphology import skeletonize
        trait = skeletonize(trait)
        r, nr = ndimage.label(trait, structure=np.ones((3, 3)))
        tl = np.bincount(r.ravel())
        for i in range(1, nr + 1):
            if tl[i] < max(3, trait_min // 2): trait[r == i] = False
    if not sombres: trait[:] = False
    trait |= pupilles
    H, W = reg.shape
    M = E * 3
    img = Image.new("L", (W * E + 2 * M, H * E + 2 * M), 255)
    d = ImageDraw.Draw(img)
    for y, x in zip(*np.nonzero(trait)):
        d.rectangle([M + x * E, M + y * E, M + x * E + E - 1, M + y * E + E - 1], fill=0)
    fin, epais = max(2, E // 5), max(4, E // 2)
    p = np.pad(reg, 1)
    for y in range(H + 1):
        for x in range(W + 1):
            a0 = p[y, x]
            if y >= 1:
                b = p[y, x + 1]
                if a0 != b:
                    ep = epais if 0 in (a0, b) else fin
                    X0 = M + x * E; Y0 = M + (y - 1) * E
                    d.rectangle([X0 - ep // 2, Y0 - ep // 2, X0 + ep // 2, Y0 + E + ep // 2], fill=0)
            if x >= 1:
                c = p[y + 1, x]
                if a0 != c:
                    ep = epais if 0 in (a0, c) else fin
                    X0 = M + (x - 1) * E; Y0 = M + y * E
                    d.rectangle([X0 - ep // 2, Y0 - ep // 2, X0 + E + ep // 2, Y0 + ep // 2], fill=0)
    return img

if __name__ == "__main__":
    a = sys.argv
    img = contour(a[1], haut=int(a[3]), k=int(a[4]), mini=int(a[5]), seuil=int(a[6]))
    img.save(a[2]); print(img.size)
