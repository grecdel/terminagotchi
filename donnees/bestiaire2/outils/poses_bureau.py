"""poses_bureau.py [--planche DOSSIER] : les poses dessinées des bébés -> pc/tg/poses.bin et app/src/main/assets/poses.bin.

Entrée : donnees/bestiaire2/animations/<numero>_<espece>/<pose>.png (12 poses par bébé de départ, PNG transparents).
Ce sont les animations de la créature du bureau (PC) et de la bulle / de l'île (Android), au stade bébé.

Pour chaque pose :
  1. les petits points isolés qui traînent autour de la pose sont enlevés : on garde le corps (le plus grand morceau)
     et les décors proches (« z Z », cœur, gouttes, miettes) ; un morceau loin du corps disparaît (plus de 20 pixels
     pour les poses sans décor : marche, assis ; plus de 40, ou plus de 30 s'il est petit, pour les autres) ;
  2. l'image est recadrée sur ce qui reste ; on note l'ANCRE : le milieu du corps et le bas du corps (les pieds),
     pour que la créature ne saute pas d'une pose à l'autre ;
  3. les 12 poses d'une espèce partagent une palette de COULEURS (48) couleurs au plus (0 = transparent) : à l'œil,
     on ne voit pas de différence avec 255 couleurs, et le fichier est presque deux fois plus petit ; les petits
     décors (cœur, gouttes, éclats) pèsent DECOR fois plus dans le choix des couleurs, pour garder leurs teintes vives.

Format du fichier (le même pour Python et Kotlin, lu par pc/tg/poses.py et app/…/Poses.kt) :
    "TGPO" | version (1 octet) | longueur de l'en-tête (4 octets, gros-boutiste) | en-tête JSON (UTF-8) | blocs
    en-tête = {"version": 1, "poses": [12 noms], "especes": {"braisillon": {"o": début du bloc (après l'en-tête),
               "n": taille du bloc, "pal": ["#rrggbb", …], "cadres": [[w, h, ax, ay], … 12]}}}
    bloc = zlib(les octets indexés des 12 poses, ligne par ligne, mis bout à bout)
Une espèce ne se décompresse que si elle est affichée.

--planche DOSSIER : écrit aussi une planche de contrôle (points enlevés en rouge) dans DOSSIER.
Le fichier produit est déterministe (mêmes images -> mêmes octets).
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ICI = Path(__file__).resolve().parents[1]
DEPOT = ICI.parents[1]
POSES = ["marche1", "marche2", "marche3", "marche4",
         "assis", "dort", "etire", "baille",
         "sursaut", "coeur", "mange", "salut"]
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


def espece_de(dossier):
    return dossier.name.split("_", 1)[1]


def traiter(dossier):
    """{"pal", "cadres", "octets"} d'une espèce, et les images de contrôle."""
    images, controles = [], []
    for p in POSES:
        rgba = np.array(Image.open(dossier / f"{p}.png").convert("RGBA"))
        rgba[..., 3] = np.where(rgba[..., 3] > 0, 255, 0)
        out, enleve, ancre, decor = nettoyer(rgba, p)
        images.append((out, ancre, decor))
        controles.append((rgba, enleve))
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
    return {"pal": pal, "cadres": cadres, "octets": bytes(octets)}, controles


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


def construire():
    dossiers = sorted(d for d in (ICI / "animations").iterdir() if d.is_dir())
    especes, blocs, controles = {}, bytearray(), {}
    for d in dossiers:
        nom = espece_de(d)
        e, ctrl = traiter(d)
        controles[nom] = ctrl
        z = zlib.compress(e["octets"], 9)
        especes[nom] = {"o": len(blocs), "n": len(z), "pal": e["pal"], "cadres": e["cadres"]}
        blocs += z
    tete = json.dumps({"version": VERSION, "poses": POSES, "especes": especes}, ensure_ascii=False,
                      separators=(",", ":"), sort_keys=True).encode("utf-8")
    return b"TGPO" + bytes([VERSION]) + struct.pack(">I", len(tete)) + tete + bytes(blocs), controles


def main(args):
    donnees, controles = construire()
    for s in SORTIES:
        s.write_bytes(donnees)
    if "--planche" in args:
        ecrire_planche(controles, Path(args[args.index("--planche") + 1]))
    print(f"OK {len(controles)} espèces × {len(POSES)} poses, {len(donnees) // 1024} Ko -> "
          + ", ".join(str(s.relative_to(DEPOT)) for s in SORTIES))


if __name__ == "__main__":
    main(sys.argv[1:])
