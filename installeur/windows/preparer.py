"""Prépare le dossier de l'installeur Windows (appelé par la CI, sous Windows, avant iscc).

    python installeur/windows/preparer.py <dossier de sortie>

Met dans le dossier : terminagotchi.pyz (le jeu PC, python -m zipapp pc), python\\ (une copie du Python qui exécute ce
script : le Python officiel installé par actions/setup-python, avec tkinter pour la créature du bureau et l'espace de
travail, sans pip ni tests ni documentation), terminagotchi.ico (fabriquée ici à partir de l'icône de l'appli, sans
outil extérieur), LICENSE.txt et LISEZMOI.txt. Rien n'est téléchargé.
"""
import os
import shutil
import struct
import sys
import zipapp
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
# ce qui ne sert pas à jouer (gros, ou des outils de développement)
INUTILES = {"Doc", "include", "libs", "Scripts", "Tools", "test", "tests", "idlelib", "ensurepip", "lib2to3",
            "turtledemo", "site-packages", "__pycache__", "venv", "pydoc_data"}


def ico(png_par_taille, sortie):
    """Un fichier .ico qui contient directement des images PNG (permis depuis Windows Vista)."""
    images = [(t, Path(p).read_bytes()) for t, p in png_par_taille]
    entete = struct.pack("<HHH", 0, 1, len(images))
    pos = 6 + 16 * len(images)
    dir_, data = b"", b""
    for t, b in images:
        dir_ += struct.pack("<BBBBHHII", t % 256, t % 256, 0, 0, 1, 32, len(b), pos + len(data))
        data += b
    Path(sortie).write_bytes(entete + dir_ + data)


def main():
    out = Path(sys.argv[1]).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    zipapp.create_archive(DEPOT / "pc", out / "terminagotchi.pyz", interpreter=None, compressed=True,
                          filter=lambda p: "__pycache__" not in p.parts and p.suffix != ".pyc")
    base = Path(sys.base_prefix)
    def ignorer(d, noms):
        return [n for n in noms if n in INUTILES or n.endswith((".pdb", ".pyc"))]
    shutil.copytree(base, out / "python", ignore=ignorer)
    res = DEPOT / "app" / "src" / "main" / "res"
    ico([(48, res / "drawable-mdpi" / "ic_launcher.png"), (96, res / "drawable-xhdpi" / "ic_launcher.png"),
         (192, res / "drawable-xxxhdpi" / "ic_launcher.png")], out / "terminagotchi.ico")
    shutil.copy(DEPOT / "LICENSE", out / "LICENSE.txt")
    shutil.copy(ICI / "LISEZMOI.txt", out / "LISEZMOI.txt")
    taille = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"prêt : {out} ({taille / 1e6:.0f} Mo avant compression)")


if __name__ == "__main__":
    main()
