"""poses_bureau.py [--planche DOSSIER] : les poses dessinées des bébés -> pc/tg/poses.bin et app/src/main/assets/poses.bin.

Entrée : donnees/bestiaire2/animations/<numero>_<espece>/<pose>.png (12 poses par bébé de départ, PNG transparents).
Ce sont les animations de la créature du bureau (PC) et de la bulle / de l'île (Android), au stade bébé.

Pour chaque pose :
  1. les petits points isolés qui traînent autour de la pose sont enlevés : on garde le corps (le plus grand morceau)
     et les décors proches (« z Z », cœur, gouttes, miettes) ; un morceau loin du corps disparaît (plus de 20 pixels
     pour les poses sans décor : marche, assis ; plus de 40, ou plus de 30 s'il est petit, pour les autres) ;
  2. l'image est recadrée sur ce qui reste ; on note l'ANCRE : le milieu du corps et le bas du corps (les pieds),
     pour que la créature ne saute pas d'une pose à l'autre ;
  3. des poses sont calculées : « cligne » (assis, les yeux fermés, pris dans la pose « coeur ») et la mâchoire,
     « bouche1 » à « bouche3 » (assis, la bouche ouverte au tiers, aux deux tiers, en grand : une fente puis un petit
     ovale sombre avec un peu de rouge, à l'endroit où le bâillement ouvre la bouche, ou relevé à la main) ; la pose
     « dort » perd ses « z » dessinés (la créature du bureau a les siens, animés) ;
  4. les 16 poses d'une espèce partagent une palette de COULEURS (48) couleurs au plus (0 = transparent) : à l'œil,
     on ne voit pas de différence avec 255 couleurs, et le fichier est presque deux fois plus petit ; les petits
     décors (cœur, gouttes, éclats) pèsent DECOR fois plus dans le choix des couleurs, pour garder leurs teintes vives.

Format du fichier (le même pour Python et Kotlin, lu par pc/tg/poses.py et app/…/Poses.kt) :
    "TGPO" | version (1 octet) | longueur de l'en-tête (4 octets, gros-boutiste) | en-tête JSON (UTF-8) | blocs
    en-tête = {"version": 1, "poses": [16 noms], "especes": {"braisillon": {"o": début du bloc (après l'en-tête),
               "n": taille du bloc, "pal": ["#rrggbb", …], "cadres": [[w, h, ax, ay], … 16],
               "bouche": [x, y] sur la pose assise, ou null}}}
    bloc = zlib(les octets indexés des 12 poses, ligne par ligne, mis bout à bout)
Une espèce ne se décompresse que si elle est affichée.

--planche DOSSIER : écrit aussi une planche de contrôle (points enlevés en rouge) dans DOSSIER.
--bouches FICHIER.png : la planche des bouches (fermée, au tiers, aux deux tiers, ouverte) des 27 bébés.
Le fichier produit est déterministe (mêmes images -> mêmes octets).
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ICI = Path(__file__).resolve().parents[1]
DEPOT = ICI.parents[1]
POSES = ["marche1", "marche2", "marche3", "marche4",
         "assis", "dort", "etire", "baille",
         "sursaut", "coeur", "mange", "salut"]
# + des poses calculées : « assis » les yeux fermés (le clignement), et la bouche ouverte au tiers, aux deux tiers et
# en grand (la mâchoire : manger, parler)
SORTIE = POSES + ["cligne", "bouche1", "bouche2", "bouche3"]
NIVEAUX_BOUCHE = (1 / 3, 2 / 3, 1.0)
# la bouche, relevée à la main sur la pose assise quand celle du bâillement tombe mal : (x, y, largeur) en pixels
BOUCHE_MAIN = {"simiosse": (82, 78, 12), "sporichon": (60, 60, 10), "plumange": (66, 60, 10),
               "lunacorne": (118, 86, 12), "fondelin": (43, 84, 12), "lanternix": (58, 108, 16),
               "glandouille": (92, 97, 14), "engrenaille": (40, 60, 8),
               "momiaou": (92, 68, 12)}
SANS_BOUCHE = {"boulonnet", "zyeuton"}          # un robot sans bouche, un grand œil : la mâchoire ne bouge pas
# des « z » collés au corps que l'on retire aussi (y0, y1, x0, x1 sur la pose dort recadrée)
RETOUCHES_DORT = {"fondelin": [(24, 33, 95, 103)]}
SANS_DECOR = {"marche1", "marche2", "marche3", "marche4", "assis"}
SORTIES = [DEPOT / "pc/tg/poses.bin", DEPOT / "app/src/main/assets/poses.bin"]
VERSION = 1
COULEURS = 48
DECOR = 40


def nettoyer(rgba, pose):
    """(rgba recadré, masque des points enlevés dans l'image d'origine, ancre (ax, ay) dans l'image recadrée)."""
    plein = rgba[..., 3] > 0
    lab, n = ndimage.label(plein, structure=np.ones((3, 3)))
    if n == 0:
        raise ValueError("pose vide")
    tailles = ndimage.sum(plein, lab, range(1, n + 1))
    corps = int(np.argmax(tailles)) + 1
    dist = ndimage.distance_transform_edt(lab != corps)
    garde = lab == corps
    enleve = np.zeros_like(plein)
    for i in range(1, n + 1):
        if i == corps:
            continue
        m = lab == i
        d = float(dist[m].min())
        a = int(tailles[i - 1])
        loin = d > 20 if pose in SANS_DECOR else (d > 40 or (a < 80 and d > 30))
        if loin:
            enleve |= m
        else:
            garde |= m
    ys, xs = np.nonzero(garde)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = rgba[y0:y1, x0:x1].copy()
    out[..., 3] = np.where(garde[y0:y1, x0:x1], 255, 0)
    cy, cx = np.nonzero(lab[y0:y1, x0:x1] == corps)
    ancre = (int(round((cx.min() + cx.max()) / 2)), int(cy.max()) + 1)
    decor = garde[y0:y1, x0:x1] & (lab[y0:y1, x0:x1] != corps)
    return out, enleve, ancre, decor


def cligne(A, ancre_a, C, ancre_c, decor_c):
    """« assis » les yeux fermés : on pose « coeur » (sans son cœur) sur « assis » (même posture, yeux fermés), au
    meilleur décalage près, et on reprend seulement les deux taches qui changent le plus dans le haut du corps (les
    yeux). Si rien ne colle (posture trop différente), « assis » reste tel quel : la créature ne cligne pas."""
    C = C.copy()
    C[decor_c] = 0
    H, W = A.shape[:2]
    plein = A[..., 3] > 0
    meilleur = None
    for dx in range(-8, 9):
        for dy in range(-8, 9):
            ox, oy = ancre_a[0] - ancre_c[0] + dx, ancre_a[1] - ancre_c[1] + dy
            Cs = np.zeros_like(A)
            y0, x0 = max(0, oy), max(0, ox)
            y1, x1 = min(H, oy + C.shape[0]), min(W, ox + C.shape[1])
            if y1 <= y0 or x1 <= x0:
                continue
            Cs[y0:y1, x0:x1] = C[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
            m = plein & (Cs[..., 3] > 0)
            if m.sum() < 0.6 * plein.sum():
                continue
            diff = np.abs(A[..., :3].astype(int) - Cs[..., :3].astype(int)).sum(2)
            score = (diff[m] < 60).mean()
            if meilleur is None or score > meilleur[0]:
                meilleur = (score, Cs)
    if meilleur is None or meilleur[0] < 0.3:
        return A.copy(), np.zeros(A.shape[:2], dtype=bool)
    Cs = meilleur[1]
    diff = np.abs(A[..., :3].astype(int) - Cs[..., :3].astype(int)).sum(2)
    m = ndimage.binary_opening(plein & (Cs[..., 3] > 0) & (diff > 90), iterations=1)
    lab, k = ndimage.label(m)
    if not k:
        return A.copy(), np.zeros(A.shape[:2], dtype=bool)
    ys = np.nonzero(plein)[0]
    haut = ys.min() + 0.75 * (ys.max() - ys.min())
    tailles = ndimage.sum(m, lab, range(1, k + 1))
    cand = sorted(((t, i + 1) for i, t in enumerate(tailles)
                   if t > 15 and ndimage.center_of_mass(m, lab, i + 1)[0] < haut), reverse=True)
    yeux = ndimage.binary_dilation(np.isin(lab, [i for _t, i in cand[:2]]), iterations=2) & plein & (Cs[..., 3] > 0)
    B = A.copy()
    B[yeux] = Cs[yeux]
    return B, yeux


def _aligner(A, ancre_a, C, ancre_c, portee=10):
    """C posée sur A au meilleur décalage (ancres alignées, ± portee) : (score, C dans le repère de A) ou None."""
    H, W = A.shape[:2]
    plein = A[..., 3] > 0
    meilleur = None
    for dx in range(-portee, portee + 1):
        for dy in range(-portee, portee + 1):
            ox, oy = ancre_a[0] - ancre_c[0] + dx, ancre_a[1] - ancre_c[1] + dy
            Cs = np.zeros_like(A)
            y0, x0 = max(0, oy), max(0, ox)
            y1, x1 = min(H, oy + C.shape[0]), min(W, ox + C.shape[1])
            if y1 <= y0 or x1 <= x0:
                continue
            Cs[y0:y1, x0:x1] = C[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
            m = plein & (Cs[..., 3] > 0)
            if m.sum() < 0.5 * plein.sum():
                continue
            diff = np.abs(A[..., :3].astype(int) - Cs[..., :3].astype(int)).sum(2)
            score = (diff[m] < 60).mean()
            if meilleur is None or score > meilleur[0]:
                meilleur = (score, Cs)
    return meilleur


def place_bouche(A, ancre_a, B, ancre_b, decor_b, yeux):
    """(x, y, largeur) de la bouche sur la pose assise : là où le bâillement ouvre la bouche (taches rouges ou sombres
    qui changent, sous les yeux), ou None."""
    B = B.copy()
    B[decor_b] = 0
    r = _aligner(A, ancre_a, B, ancre_b)
    if r is None:
        return None
    Bs = r[1]
    plein = A[..., 3] > 0
    ys, xs = np.nonzero(plein)
    top, H = ys.min(), ys.max() - ys.min()
    rgb = Bs[..., :3].astype(int)
    rouge = (rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])) > 25
    sombre = rgb.mean(2) < 95
    diff = np.abs(A[..., :3].astype(int) - rgb).sum(2)
    cand = plein & (Bs[..., 3] > 0) & (diff > 80) & (rouge | sombre)
    if yeux.any():
        ey = np.nonzero(yeux)[0]
        cand &= ~ndimage.binary_dilation(yeux, iterations=4)
        cand[:int(ey.min() + 0.6 * (ey.max() - ey.min()))] = False      # sous le milieu des yeux
    cand = ndimage.binary_opening(ndimage.binary_closing(cand, iterations=2) & plein, iterations=1)
    lab, k = ndimage.label(cand)
    best = None
    for i in range(1, k + 1):
        m = lab == i
        y, x = np.nonzero(m)
        cy = (y.mean() - top) / max(1, H)
        if m.sum() < 20 or not 0.3 <= cy <= 0.95:
            continue
        s = m.sum() * (0.5 + rouge[m].mean())
        if best is None or s > best[0]:
            best = (s, m)
    if best is None:
        return None
    y, x = np.nonzero(best[1])
    w = min((x.max() - x.min() + 1) * 0.75, (xs.max() - xs.min()) * 0.28)
    return (x.min() + x.max()) / 2, y.min() + min(w * 0.3, (y.max() - y.min()) * 0.3), max(6.0, w)


def ouvrir_bouche(A, place, niveau, k=4):
    """La pose assise, la bouche ouverte à niveau (0 à 1) : une fente, puis un petit ovale sombre (le contour du
    dessin) avec l'intérieur foncé et un peu de rouge (la langue). Dessiné 4 fois plus grand puis réduit (bords doux)."""
    if place is None or niveau <= 0:
        return A.copy()
    cx, cy, larg = place
    H, W = A.shape[:2]
    w = larg * 1.25 * (0.55 + 0.45 * niveau)          # assez grande pour se voir à la taille du bureau
    h = max(1.8, larg * 1.25 * 0.78 * niveau)
    plein = A[..., 3] > 0
    corps = A[plein][:, :3].astype(int)
    lums = corps.mean(1)
    contour = corps[lums <= np.percentile(lums, 8)].mean(0)
    calque = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    bx0, by0, bx1, by1 = (cx - w / 2) * k, (cy - h * 0.35) * k, (cx + w / 2) * k, (cy + h * 0.65) * k
    d.ellipse((bx0, by0, bx1, by1), fill=tuple(int(v) for v in contour * 0.55) + (255,))
    ep = max(1, int(k * 0.9))
    if niveau > 0.25:
        d.ellipse((bx0 + ep, by0 + ep, bx1 - ep, by1 - ep), fill=(58, 16, 28, 255))
        tw, th = (bx1 - bx0) * 0.62, (by1 - by0) * 0.42
        tcx = (bx0 + bx1) / 2
        d.ellipse((tcx - tw / 2, by1 - ep - th, tcx + tw / 2, by1 - ep + th * 0.3), fill=(214, 84, 104, 255))
    petit = np.array(calque.resize((W, H), Image.LANCZOS)).astype(float)
    a = petit[..., 3:4] / 255
    out = A.copy().astype(float)
    out[..., :3] = np.where(plein[..., None], out[..., :3] * (1 - a) + petit[..., :3] / np.maximum(a, 1e-6) * a,
                            out[..., :3])
    return out.clip(0, 255).astype(np.uint8)


def sans_zzz(o, espece):
    """La pose dort sans les « z » dessinés (la créature du bureau a les siens, animés) : les petits morceaux détachés
    en haut à droite de la tête, de la même couleur, qui se suivent en chaîne (une flamme, un halo, une bulle ou une
    goutte ne sont pas pris : ailleurs, ou d'une autre couleur). Rend (pose, masque des pixels retirés)."""
    plein = o[..., 3] > 0
    lab, k = ndimage.label(plein, structure=np.ones((3, 3)))
    t = ndimage.sum(plein, lab, range(1, k + 1))
    corps = int(np.argmax(t)) + 1
    ys, xs = np.nonzero(lab == corps)
    top, H, cx = ys.min(), ys.max() - ys.min(), (xs.min() + xs.max()) / 2
    cand = []
    for i in range(1, k + 1):
        if i == corps:
            continue
        y, x = np.nonzero(lab == i)
        if y.mean() < top + 0.45 * H and x.mean() > cx and t[i - 1] < 0.06 * t[corps - 1]:
            cand.append((y.mean() - 0.3 * x.max(), i, o[lab == i][:, :3].mean(0), (y.min(), y.max(), x.min(), x.max())))
    cand.sort(key=lambda c: c[0])
    garde = [cand.pop(0)] if cand else []
    change = True
    while change and cand:
        change = False
        for c in list(cand):
            for g in garde:
                (a0, a1, b0, b1), (c0, c1, d0, d1) = c[3], g[3]
                if max(0, max(a0, c0) - min(a1, c1), max(b0, d0) - min(b1, d1)) <= 22 \
                        and np.abs(c[2] - g[2]).sum() < 90:
                    garde.append(c)
                    cand.remove(c)
                    change = True
                    break
    zz = np.isin(lab, [g[1] for g in garde])
    for y0, y1, x0, x1 in RETOUCHES_DORT.get(espece, []):
        zz[y0:y1, x0:x1] |= plein[y0:y1, x0:x1]
    out = o.copy()
    out[zz] = 0
    return out, zz


def espece_de(dossier):
    return dossier.name.split("_", 1)[1]


def traiter(dossier, bouches=None):
    """{"pal", "cadres", "octets"} d'une espèce, et les images de contrôle. bouches : liste où ranger
    (espèce, [assis, bouche1, bouche2, bouche3]) pour la planche des bouches."""
    espece = espece_de(dossier)
    images, controles = [], []
    for p in POSES:
        rgba = np.array(Image.open(dossier / f"{p}.png").convert("RGBA"))
        rgba[..., 3] = np.where(rgba[..., 3] > 0, 255, 0)
        out, enleve, ancre, decor = nettoyer(rgba, p)
        if p == "dort":
            out, zz = sans_zzz(out, espece)
            decor = decor & ~zz
            ys, xs = np.nonzero(out[..., 3] > 0)                # recadrée sans les « z »
            y0, x0 = ys.min(), xs.min()
            out, decor = out[y0:ys.max() + 1, x0:xs.max() + 1], decor[y0:ys.max() + 1, x0:xs.max() + 1]
            ancre = (ancre[0] - int(x0), ancre[1] - int(y0))
        images.append((out, ancre, decor))
        controles.append((rgba, enleve))
    a, c = images[POSES.index("assis")], images[POSES.index("coeur")]
    yeux_fermes, yeux = cligne(a[0], a[1], c[0], c[1], c[2])
    images.append((yeux_fermes, a[1], np.zeros(a[0].shape[:2], dtype=bool)))
    b = images[POSES.index("baille")]
    if espece in SANS_BOUCHE:
        place = None
    else:
        place = BOUCHE_MAIN.get(espece) or place_bouche(a[0], a[1], b[0], b[1], b[2], yeux)
    ouvertes = [ouvrir_bouche(a[0], place, n) for n in NIVEAUX_BOUCHE]
    for o in ouvertes:                               # la bouche compte comme un décor (ses couleurs sont gardées)
        images.append((o, a[1], np.abs(o.astype(int) - a[0].astype(int)).sum(2) > 30))
    if bouches is not None:
        bouches.append((espece, [a[0]] + ouvertes, place is not None))
    # une palette commune aux 12 poses : on colle les pixels opaques bout à bout ; les petits décors (cœur, « z Z »,
    # gouttes) comptent DECOR fois plus, sinon leurs couleurs vives se perdent dans celles du corps
    pixels = np.concatenate([im[im[..., 3] > 0][:, :3] for im, _a, _d in images]
                            + [np.repeat(im[d][:, :3], DECOR, axis=0) for im, _a, d in images if d.any()])
    bande = Image.fromarray(pixels.reshape(1, -1, 3), "RGB")
    q = bande.quantize(colors=COULEURS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal_plate = q.getpalette()[:3 * COULEURS]
    nb = int(np.array(q).max()) + 1
    pal = ["#%02x%02x%02x" % tuple(pal_plate[3 * k:3 * k + 3]) for k in range(nb)]
    cadres, octets = [], bytearray()
    for im, (ax, ay), _d in images:
        h, w = im.shape[:2]
        rgb = Image.fromarray(np.ascontiguousarray(im[..., :3]), "RGB")
        idx = np.array(rgb.quantize(palette=q, dither=Image.Dither.NONE), dtype=np.uint16) + 1
        idx = np.where(im[..., 3] > 0, idx, 0)
        if idx.max() > nb:                           # (ne doit pas arriver : la palette vient de ces pixels)
            idx = np.minimum(idx, nb)
        octets += idx.astype(np.uint8).tobytes()
        cadres.append([w, h, ax, ay])
    bouche = None if place is None else [round(float(place[0]), 1), round(float(place[1]), 1)]
    return {"pal": pal, "cadres": cadres, "octets": bytes(octets), "bouche": bouche}, controles


def ecrire_planche(controles_par_espece, dossier):
    """Une planche de contrôle : chaque pose sur fond sombre, les points enlevés en rouge vif."""
    dossier.mkdir(parents=True, exist_ok=True)
    C = 200
    noms = sorted(controles_par_espece)
    planche = Image.new("RGB", (C * len(POSES), C * len(noms)), (24, 26, 36))
    for j, nom in enumerate(noms):
        for i, (rgba, enleve) in enumerate(controles_par_espece[nom]):
            im = Image.fromarray(rgba, "RGBA")
            fond = Image.new("RGBA", (C, C), (40, 44, 60, 255) if (i + j) % 2 else (30, 32, 46, 255))
            fond.alpha_composite(im.crop((0, 0, min(C, im.width), min(C, im.height))))
            a = np.array(fond)
            e = enleve[:C, :C]
            ys, xs = np.nonzero(e)
            for y, x in zip(ys, xs):
                a[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = (255, 0, 60, 255)
            planche.paste(Image.fromarray(a).convert("RGB"), (i * C, j * C))
    planche.save(dossier / "poses_nettoyage.png")


def ecrire_bouches(bouches, chemin):
    """La planche des bouches : chaque bébé bouche fermée, au tiers, aux deux tiers, grande ouverte."""
    from PIL import ImageFont
    C = 170
    try:
        police = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        police = ImageFont.load_default()
    col = 3
    planche = Image.new("RGB", (col * (4 * C + 20), ((len(bouches) + col - 1) // col) * (C + 24)), (24, 26, 36))
    d = ImageDraw.Draw(planche)
    for n, (espece, ims, a_bouche) in enumerate(bouches):
        x0, y0 = (n % col) * (4 * C + 20), (n // col) * (C + 24)
        for j, im in enumerate(ims):
            t = Image.fromarray(im, "RGBA")
            e = min(1.0, (C - 6) / max(t.width, t.height))
            t = t.resize((max(1, int(t.width * e)), max(1, int(t.height * e))), Image.LANCZOS)
            fond = Image.new("RGBA", (C, C), (24, 26, 36, 255))
            fond.alpha_composite(t, ((C - t.width) // 2, C - t.height - 2))
            planche.paste(fond.convert("RGB"), (x0 + j * C, y0))
        d.text((x0 + 4, y0 + C + 4), espece + ("" if a_bouche else "  (pas de bouche : la mâchoire ne bouge pas)"),
               font=police, fill=(210, 210, 220))
    planche.save(chemin)


def construire():
    dossiers = sorted(d for d in (ICI / "animations").iterdir() if d.is_dir())
    especes, blocs, controles = {}, bytearray(), {}
    construire.bouches = []
    for d in dossiers:
        nom = espece_de(d)
        e, ctrl = traiter(d, construire.bouches)
        controles[nom] = ctrl
        z = zlib.compress(e["octets"], 9)
        especes[nom] = {"o": len(blocs), "n": len(z), "pal": e["pal"], "cadres": e["cadres"], "bouche": e["bouche"]}
        blocs += z
    tete = json.dumps({"version": VERSION, "poses": SORTIE, "especes": especes}, ensure_ascii=False,
                      separators=(",", ":"), sort_keys=True).encode("utf-8")
    return b"TGPO" + bytes([VERSION]) + struct.pack(">I", len(tete)) + tete + bytes(blocs), controles


def main(args):
    donnees, controles = construire()
    for s in SORTIES:
        s.write_bytes(donnees)
    if "--planche" in args:
        ecrire_planche(controles, Path(args[args.index("--planche") + 1]))
    if "--bouches" in args:
        ecrire_bouches(construire.bouches, Path(args[args.index("--bouches") + 1]))
    print(f"OK {len(controles)} espèces × {len(POSES)} poses, {len(donnees) // 1024} Ko -> "
          + ", ".join(str(s.relative_to(DEPOT)) for s in SORTIES))


if __name__ == "__main__":
    main(sys.argv[1:])
