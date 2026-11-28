"""Prépare les illustrations de l'intro pour le jeu (à relancer si une image de donnees/illustrations/ change).

    python3 donnees/illustrations/generer_intro.py        (depuis la racine du dépôt ; demande Pillow)

Sources : donnees/illustrations/monde.png (le Terminaworld vivant), dort.png (endormi), camp2.png (le camp de base).
Produit :
  - app/src/main/assets/intro/{monde,dort,camp}.jpg : Android, réduites proprement (Lanczos), JPEG qualité 80 (couleurs
    en 4:2:2, les lueurs vertes restent nettes) ; le camp en 1152×648 (il est recadré en carré sur le téléphone), le
    monde endormi ou vivant en 960 de large (montrés en entier) ; environ 700 Ko pour les trois ;
  - pc/tg/illustrations.bin : PC, les trois images en 384×216 (assez pour une vraie image dans un terminal qui sait
    les afficher, et réduites à la volée pour les sextants ou les demi-blocs), RVB sur 5 bits par couleur, compressé
    (zlib), lu par pc/tg/scenes.py sans aucune bibliothèque ;
  - pc/tg/carte_monde.png : PC, la carte du Terminaworld (monde.png) en 960 de large, 256 couleurs, pour l'onglet
    « monde » de l'espace de travail (pc/tg/espace_scene.py).
Le monde endormi (3 novembre, idée 31 « le réveil de biome en biome ») : il doit être ALIGNÉ pixel pour pixel sur
monde.png (les biomes se réveillent en mélangeant les deux images). Source : donnees/illustrations/dort_aligne.png si
elle existe (la vraie illustration, faite avec le propriétaire : il suffit de DÉPOSER ce fichier puis de relancer ce
script), sinon donnees/reveil/dort_provisoire.jpg (calculée, provisoire). L'ancienne dort.png (ancienne vue) ne sert
plus. Produit aussi, pour le réveil :
  - pc/tg/carte_dort.png (comme carte_monde.png) et app/src/main/assets/intro/dort.jpg ;
  - les masques des zones (donnees/reveil/zones.json : 10 paysages, 15 lieux, puis les lumières et le feuillage),
    une bande de 480×270 par zone, l'une sous l'autre, en niveaux de gris : pc/tg/reveil_masques.png et
    app/src/main/assets/intro/reveil_masques.png ; et en 192×108 sans compression d'image (zlib seul) pour le
    terminal : pc/tg/reveil_masques.bin (lu sans aucune bibliothèque) ;
  - les copies de donnees/reveil/zones.json : pc/tg/reveil.json et app/src/main/assets/reveil.json. Le camp endormi n'est PAS une image à part : le jeu le calcule (désaturé, assombri, bleui), comme sur les maquettes.
Format de illustrations.bin : b"TGI1", puis pour chaque image : nom (1 octet de longueur + ASCII), largeur, hauteur
(2 octets chacun, gros-boutiste), longueur des données (4 octets), données zlib (RVB, ligne par ligne).
"""
import os
import struct
import zlib

from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
ANDROID = os.path.join(DEPOT, "app", "src", "main", "assets", "intro")
PC = os.path.join(DEPOT, "pc", "tg", "illustrations.bin")

REVEIL = os.path.join(DEPOT, "donnees", "reveil")
DORT = os.path.join(ICI, "dort_aligne.png") if os.path.isfile(os.path.join(ICI, "dort_aligne.png")) else \
    os.path.join(REVEIL, "dort_provisoire.jpg")
IMAGES = {"monde": ("monde.png", 960), "dort": (DORT, 960), "camp": ("camp2.png", 1152)}
MASQUE = (480, 270)
MASQUE_TERM = (192, 108)
PC_TAILLE = (384, 216)
CARTE = os.path.join(DEPOT, "pc", "tg", "carte_monde.png")
CARTE_LARGEUR = 960


def main():
    os.makedirs(ANDROID, exist_ok=True)
    blocs = [b"TGI1"]
    for nom, (src, largeur) in IMAGES.items():
        im = Image.open(os.path.join(ICI, src)).convert("RGB")
        if nom == "dort":
            im = im.resize(Image.open(os.path.join(ICI, "monde.png")).size, Image.LANCZOS)
        h = round(im.height * largeur / im.width / 2) * 2
        a = im.resize((largeur, h), Image.LANCZOS)
        chemin = os.path.join(ANDROID, nom + ".jpg")
        a.save(chemin, "JPEG", quality=80, subsampling=1, optimize=True)
        p = im.resize(PC_TAILLE, Image.LANCZOS)
        z = zlib.compress(bytes(v & 0xF8 for v in p.tobytes()), 9)       # 5 bits par couleur : assez pour un terminal
        blocs.append(bytes([len(nom)]) + nom.encode() + struct.pack(">HHI", PC_TAILLE[0], PC_TAILLE[1], len(z)) + z)
        print(f"{nom}: Android {largeur}×{h} {os.path.getsize(chemin) // 1024} Ko, PC {len(z) // 1024} Ko")
    with open(PC, "wb") as f:
        f.write(b"".join(blocs))
    print(f"{PC}: {os.path.getsize(PC) // 1024} Ko")
    im = Image.open(os.path.join(ICI, "monde.png")).convert("RGB")
    c = im.resize((CARTE_LARGEUR, round(im.height * CARTE_LARGEUR / im.width)), Image.LANCZOS)
    c.quantize(256, method=Image.MEDIANCUT, dither=Image.NONE).save(CARTE, optimize=True)
    print(f"{CARTE}: {c.width}×{c.height} {os.path.getsize(CARTE) // 1024} Ko")
    reveil(im)


# ---------------------------------------------------------------- le réveil (idée 31)
def masques(zones, w, h, vivant):
    """[(nom, image L)] : les 10 paysages (Voronoï des graines, adouci ; la somme vaut 255 partout), les 15 lieux
    (ellipses adoucies), puis les lumières (fenêtres, lanternes, circuits : elles restent allumées la nuit) et le
    feuillage (les saisons). Même calcul que les maquettes (outils/reveil/travail/maquette.py), en Pillow seul."""
    from PIL import ImageDraw, ImageFilter
    W0, H0 = zones["taille"]
    sx, sy = w / W0, h / H0
    ids = list(zones["biomes"])
    graines = [(x * sx, y * sy, i) for i, b in enumerate(ids) for x, y in zones["biomes"][b]["graines"]]
    etiq = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            etiq[y * w + x] = min(graines, key=lambda g: (g[0] - x) ** 2 + (g[1] - y) ** 2)[2]
    flou = 18.0 * w / W0                                # ~20 pixels de bord adouci sur la grande image
    bio = []
    for i, b in enumerate(ids):
        m = Image.frombytes("L", (w, h), bytes(255 if v == i else 0 for v in etiq)).filter(ImageFilter.GaussianBlur(flou))
        bio.append(list(m.getdata()))
    tot = [sum(c) or 1 for c in zip(*bio)]
    out = []
    for i, b in enumerate(ids):                      # la somme vaut 255 partout (rien d'oublié, rien de compté deux fois)
        px = bytearray(w * h)
        for k in range(w * h):
            px[k] = int(bio[i][k] * 255 / tot[k] + 0.5)
        out.append(("b_" + b, px))
    # corrige l'arrondi : la Racine prend le reste
    for k in range(w * h):
        s_ = sum(o[1][k] for o in out)
        if s_ != 255:
            out[0][1][k] = max(0, min(255, out[0][1][k] + 255 - s_))
    out = [(n, Image.frombytes("L", (w, h), bytes(px))) for n, px in out]
    for l, d in zones["lieux"].items():
        cx, cy, rx, ry = d["ellipse"]
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).ellipse(((cx - rx) * sx, (cy - ry) * sy, (cx + rx) * sx, (cy + ry) * sy), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(6.0 * sx)).point(lambda v: min(255, int(v * 1.15)))
        out.append(("l_" + l, m))
    v = vivant.resize((w, h), Image.LANCZOS)
    lum, feu = bytearray(w * h), bytearray(w * h)
    import colorsys
    for k, (r, g, b) in enumerate(v.getdata()):
        chaud = r > 235 and g > 170 and b < 120 and r - b > 140
        neon = g > 190 and r < 140
        froid = b > 210 and g > 200 and r < 190
        lum[k] = 255 if (chaud or neon) else 180 if froid else 0
        hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        feu[k] = 255 if (62 / 360 < hh < 128 / 360 and ss > 0.38 and vv > 0.22 and not neon) else 0
    out.append(("lumieres", Image.frombytes("L", (w, h), bytes(lum)).filter(ImageFilter.GaussianBlur(0.8))))
    out.append(("feuillage", Image.frombytes("L", (w, h), bytes(feu)).filter(ImageFilter.GaussianBlur(0.8))))
    return out


def reveil(vivant):
    import json
    import shutil
    with open(os.path.join(REVEIL, "zones.json"), encoding="utf-8") as f:
        zones = json.load(f)
    for dest in (os.path.join(DEPOT, "pc", "tg", "reveil.json"), os.path.join(DEPOT, "app", "src", "main", "assets", "reveil.json")):
        shutil.copyfile(os.path.join(REVEIL, "zones.json"), dest)
    d = Image.open(DORT).convert("RGB")
    if d.size != vivant.size:
        print(f"⚠ {DORT} : {d.size} au lieu de {vivant.size} (redimensionnée ; vérifier l'alignement : outils/reveil/travail/recalage.py)")
    c = d.resize((CARTE_LARGEUR, round(vivant.height * CARTE_LARGEUR / vivant.width)), Image.LANCZOS)
    dest = os.path.join(DEPOT, "pc", "tg", "carte_dort.png")
    c.quantize(256, method=Image.MEDIANCUT, dither=Image.NONE).save(dest, optimize=True)
    print(f"{dest}: {os.path.getsize(dest) // 1024} Ko (source : {os.path.relpath(DORT, DEPOT)})")
    ms = masques(zones, MASQUE[0], MASQUE[1], vivant)
    bande = Image.new("L", (MASQUE[0], MASQUE[1] * len(ms)), 0)
    for i, (_n, m) in enumerate(ms):
        bande.paste(m, (0, i * MASQUE[1]))
    for dest in (os.path.join(DEPOT, "pc", "tg", "reveil_masques.png"), os.path.join(ANDROID, "reveil_masques.png")):
        bande.save(dest, optimize=True)
        print(f"{dest}: {len(ms)} masques, {os.path.getsize(dest) // 1024} Ko")
    # le terminal : 192×108, zlib seul, format b"TGM1", nombre (1 octet), largeur, hauteur (2 octets), puis pour chaque
    # masque : nom (1 octet de longueur + ASCII), longueur (4 octets), données zlib (un octet par pixel)
    blocs = [b"TGM1", struct.pack(">BHH", len(ms), *MASQUE_TERM)]
    for n, m in ms:
        z = zlib.compress(m.resize(MASQUE_TERM, Image.BILINEAR).tobytes(), 9)
        blocs.append(bytes([len(n)]) + n.encode() + struct.pack(">I", len(z)) + z)
    dest = os.path.join(DEPOT, "pc", "tg", "reveil_masques.bin")
    with open(dest, "wb") as f:
        f.write(b"".join(blocs))
    print(f"{dest}: {os.path.getsize(dest) // 1024} Ko")


if __name__ == "__main__":
    main()
