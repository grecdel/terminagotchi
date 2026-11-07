"""Lit une capture du téléphone virtuel (OCR tesseract, outil de la CI seulement, rien dans le jeu) : tests/vitrine.sh.

  python3 tests/lire_ecran.py question capture.png [texte.txt]  → le résultat de la multiplication des grands (ou rien)
  python3 tests/lire_ecran.py carte capture.png [texte.txt]     → « oui » si la carte « Signaler un souci » est ouverte

uiautomator ne lit pas l'écran du terminal : la créature bouge tout le temps, l'écran n'est jamais « au repos ».
"""
import os, re, subprocess, sys, tempfile
from PIL import Image, ImageOps

quoi, image = sys.argv[1], sys.argv[2]
im = ImageOps.invert(Image.open(image).convert("L")).point(lambda v: 255 if v > 150 else 0)   # clair sur sombre → noir sur blanc
im = im.resize((im.width * 2, im.height * 2))
f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
f.close()
im.save(f.name)
texte = subprocess.run(["tesseract", f.name, "-", "--psm", "6"], capture_output=True, text=True).stdout
os.unlink(f.name)
if len(sys.argv) > 3:
    open(sys.argv[3], "w", encoding="utf-8").write(texte)
if quoi == "question":     # « combien font 16 × 17 ? » (Apparence.questionAdulte : 12 à 19 × 13 à 19)
    q = [(int(a), int(b)) for a, b in re.findall(r"font\s*(\d{2})\s*\S{0,2}\s*(\d{2})", texte)
         if 12 <= int(a) <= 19 and 13 <= int(b) <= 19]
    print(q[-1][0] * q[-1][1] if q else "")
else:                      # les boutons de la carte : « Ouvrir la page », « Enregistrer », « Annuler »
    print("oui" if re.search(r"Ouvrir|Enregistr|Annuler", texte) else "non")
