"""Outils des passages sur le téléphone virtuel (tests/audit_ecrans.sh) : lecture d'écran (OCR tesseract) et rangement
des captures. Outil de la CI seulement, rien dans le jeu.

  python3 tests/audit_lire.py mot capture.png Mot [n]    → « x y » : le centre du n-ième mot lu qui contient Mot (ou rien)
  python3 tests/audit_lire.py textes dossier             → un .txt par capture .png (tout le texte lu)
  python3 tests/audit_lire.py reduire dossier sortie     → les captures en JPEG réduit, les autres petits fichiers copiés
"""
import os, re, shutil, subprocess, sys, tempfile, unicodedata
from PIL import Image, ImageOps


def simple(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def langues():
    try:
        dispo = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
    except Exception:
        return "eng"
    voulues = [l for l in os.environ.get("OCR_LANGUES", "fra eng").split() if l in dispo]
    return "+".join(voulues) or "eng"


def variantes(image):
    im0 = Image.open(image).convert("L")
    for inverse in (True, False):          # clair sur sombre, puis sombre sur clair
        im = ImageOps.invert(im0) if inverse else im0
        yield im.point(lambda v: 255 if v > 150 else 0)


def lire_mots(image):
    """[(mot, x, y, largeur, hauteur)] dans l'ordre de lecture, pour les deux variantes de l'image."""
    lus = []
    for im in variantes(image):
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        f.close()
        im.save(f.name)
        tsv = subprocess.run(["tesseract", f.name, "-", "-l", langues(), "--psm", "11", "tsv"],
                             capture_output=True, text=True).stdout
        os.unlink(f.name)
        for ligne in tsv.splitlines()[1:]:
            c = ligne.split("\t")
            if len(c) < 12 or not c[11].strip():
                continue
            try:
                x, y, w, h, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
            except ValueError:
                continue
            if conf < 20:
                continue
            lus.append((c[11].strip(), x, y, w, h))
    lus.sort(key=lambda m: (m[2] // 12, m[1]))
    return lus


def lire_texte(image):
    im = next(variantes(image))
    im = im.resize((im.width * 2, im.height * 2))
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.close()
    im.save(f.name)
    t = subprocess.run(["tesseract", f.name, "-", "-l", langues(), "--psm", "6"], capture_output=True, text=True).stdout
    os.unlink(f.name)
    return t


def un_texte(chemin):
    try:
        open(chemin[:-4] + ".txt", "w", encoding="utf-8").write(lire_texte(chemin))
    except Exception as e:
        print("lecture impossible :", chemin, e)


quoi = sys.argv[1]
if quoi == "mot":
    cible, n = simple(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else 1
    vus, trouves = set(), []
    for mot, x, y, w, h in lire_mots(sys.argv[2]):
        if cible in simple(mot):
            cle = (x // 30, y // 30)
            if cle in vus:
                continue
            vus.add(cle)
            trouves.append((x + w // 2, y + h // 2))
    if len(trouves) >= n:
        print(trouves[n - 1][0], trouves[n - 1][1])
elif quoi == "textes":
    from multiprocessing import Pool
    d = sys.argv[2]
    images = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png") and not f.startswith("_"))
    with Pool(4) as p:
        p.map(un_texte, images)
    print(len(images), "captures lues")
elif quoi == "reduire":
    d, sortie = sys.argv[2], sys.argv[3]
    os.makedirs(sortie, exist_ok=True)
    for f in sorted(os.listdir(d)):
        src = os.path.join(d, f)
        if f.startswith("_") or not os.path.isfile(src):
            continue
        if f.endswith(".png"):
            im = Image.open(src).convert("RGB")
            k = min(1.0, 1600.0 / max(im.size), 760.0 / min(im.size))
            if k < 1.0:
                im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
            im.save(os.path.join(sortie, f[:-4] + ".jpg"), quality=78, optimize=True)
            if any(m in f for m in os.environ.get("ENTIERES", "").split()):      # quelques captures gardées entières
                shutil.copy(src, os.path.join(sortie, f))
        elif os.path.getsize(src) < 400_000 and re.search(r"\.(txt|xml|log|json)$", f):
            shutil.copy(src, os.path.join(sortie, f))
