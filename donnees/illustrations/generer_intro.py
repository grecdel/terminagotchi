"""Prépare les illustrations de l'intro pour le jeu (à relancer si une image de donnees/illustrations/ change).

    python3 donnees/illustrations/generer_intro.py        (depuis la racine du dépôt ; demande Pillow)

Sources : donnees/illustrations/monde.png (le Terminaworld vivant), dort.png (endormi), camp2.png (le camp de base).
Produit :
  - app/src/main/assets/intro/{monde,dort,camp}.jpg : Android, réduites proprement (Lanczos), JPEG qualité 80 (couleurs
    en 4:2:2, les lueurs vertes restent nettes) ; le camp en 1152×648 (il est recadré en carré sur le téléphone), le
    monde endormi ou vivant en 960 de large (montrés en entier) ; environ 700 Ko pour les trois ;
  - pc/tg/illustrations.bin : PC, les trois images en 240×135 (deux fois la résolution d'un terminal de 120 colonnes en
    demi-blocs), RVB sur 5 bits par couleur, compressé (zlib), lu par pc/tg/scenes.py sans aucune bibliothèque.
Le camp endormi n'est PAS une image à part : le jeu le calcule (désaturé, assombri, bleui), comme sur les maquettes.
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

IMAGES = {"monde": ("monde.png", 960), "dort": ("dort.png", 960), "camp": ("camp2.png", 1152)}
PC_TAILLE = (240, 135)


def main():
    os.makedirs(ANDROID, exist_ok=True)
    blocs = [b"TGI1"]
    for nom, (src, largeur) in IMAGES.items():
        im = Image.open(os.path.join(ICI, src)).convert("RGB")
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


if __name__ == "__main__":
    main()
