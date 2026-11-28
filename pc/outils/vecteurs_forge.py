"""Les vecteurs communs de la Forge (Python ↔ Kotlin) : donnees/forge/vecteurs.json.

    python3 pc/outils/vecteurs_forge.py              écrit les vecteurs (depuis pc/tg/forge.py et deploie.py)
    python3 pc/outils/vecteurs_forge.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

La recette de la cabane (ce qu'elle contient déjà), la question des tours pour quelques graines, le nom du jeu posé sur
la carte, un texte traduit rendu sûr dans un script sh, la photo d'exemple (ses métadonnées lues, la même sans elles),
des JPEG abîmés, des GIF (le nombre d'images) et des WAV fabriqués ici, l'atelier de la vue déployée, et — dans les 14
langues — serpent.py et devinette.sh tels que le jeu les écrit. tests/jvm/Forge.kt vérifie que l'appli Android donne
EXACTEMENT les mêmes résultats.
"""
import base64
import hashlib
import json
import struct
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, forge as FO  # noqa: E402

FICHIER = RACINE / "donnees" / "forge" / "vecteurs.json"


def gif(n, gct=True, lct=False):
    """Un GIF minimal de n images (la structure des blocs ; les données d'image sont un seul petit bloc)."""
    o = bytearray(b"GIF89a" + struct.pack("<HH", 2, 2) + bytes([0xF0 if gct else 0x00, 0, 0]))
    if gct:
        o += bytes(6)                                       # 2 couleurs
    o += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"     # la boucle sans fin (une extension)
    for _ in range(n):
        o += b"\x21\xf9\x04\x00\x14\x00\x00\x00"             # 20 centièmes de seconde
        o += b"\x2c" + struct.pack("<HHHH", 0, 0, 2, 2) + bytes([0x80 if lct else 0])
        if lct:
            o += bytes(6)
        o += b"\x02\x02\x44\x01\x00"
    return bytes(o + b"\x3b")


def vecteurs():
    langue.definir("fr")
    recettes = ["", "#!/bin/sh\n", "#!/bin/sh\nmkdir -p cabane\n", "#!/bin/sh\nmkdir -p cabane\ntouch cabane/porte.txt cabane/toit.txt\n",
                "mkdir -p cabane\ntouch cabane/porte.txt\n", "#!/usr/bin/env bash\nmkdir cabane\ntouch cabane/a\n",
                "#! /bin/bash\n  mkdir -p cabane\n", "# !/bin/sh\nmkdir -p cabane\ntouch cabane/porte.txt\n",
                "#!/bin/zsh\ntouch cabanes/porte\nmkdir village\n", "#!/bin/sh\r\nmkdir -p cabane\r\ntouch cabane/porte.txt\r\n"]
    graines = ["1:0", "1:1793534400", "2:1700000000", "partie:42", "1:1730000000", "3:9"]
    noms = ["La grotte de Pixel", "  Le   donjon  ", "Mon jeu! <script>", "Été & neige", "x" * 60, "L'île aux 3 trésors", "", "日本のゲーム"]
    surs = ['Bravo ! "Trouvé"', "Plus grand $HOME `id`", "a\\b", "Ça marche !"]
    o = FO.photo_octets()
    jpegs = {"exemple": o, "sans": FO.sans_exif(o), "tronque": o[:300], "pas_jpeg": b"GIF89a....", "vide": b"",
             "soi_seul": b"\xff\xd8\xff\xd9"}
    photos = [{"nom": k, "base64": base64.b64encode(v).decode("ascii"), "segments": len(FO.segments_jpeg(v) or []) if
               FO.segments_jpeg(v) is not None else None, "exif": [list(x) for x in FO.exif_de(v)] if FO.exif_de(v) is not None
               else None, "a_exif": FO.a_exif(v), "sans_sha256": hashlib.sha256(FO.sans_exif(v)).hexdigest()}
              for k, v in jpegs.items()]
    gifs = [{"base64": base64.b64encode(g).decode("ascii"), "images": FO.images_gif(g)} for g in
            (gif(1), gif(4), gif(3, gct=False, lct=True), gif(2)[:-12], b"GIF87a", b"PNG...", gif(0))]
    wavs = [{"base64": base64.b64encode(w).decode("ascii"), "ok": FO.wav_ok(w)} for w in
            (FO.fanfare_octets()[:60], b"RIFF\0\0\0\0WAVEfmt ", b"RIFX" + bytes(60))]
    lignes = ["sh cabane.sh", "./cabane.sh", "bash salut.sh Léa", "sh tests.sh", "for i in $(seq 1 10); do mkdir -p v/c_$i; done",
              "n=3; while [ $n -gt 0 ]; do echo $n; n=$((n - 1)); done", "if [ -f a ]; then echo oui; fi",
              "python3 serpent.py Pixel 3", "python3 -m http.server 8642 --bind 127.0.0.1 --directory site &",
              "magick -delay 20 -loop 0 a.png b.png c.gif", "convert a.png b.gif", "ffmpeg -i f.wav -ss 0.5 -t 0.5 g.wav",
              "sox -n la.wav synth 0.5 sine 440", "exiftool photo.jpg", "seq 1 10 | sh mon_jeu/devinette.sh", "ls", "echo sh"]
    atelier = [{"ligne": l, "forges": [list(a) for a in FO.forges_de(l)],
                "deploie": [{k: x[k] for k in ("seg", "cmd", "outil", "objet", "de", "vers")} for x in deploie.forges(l)]}
               for l in lignes]
    textes = {}
    for code in langue.LANGUES:
        langue.definir(code)
        textes[code] = {"serpent": FO.serpent_py(), "devinette": FO.devinette_sh()}
    langue.definir("fr")
    return {"note": "généré par pc/outils/vecteurs_forge.py ; vérifié par tests/jvm/Forge.kt",
            "recettes": [{"texte": r, "etat": FO.recette_etat(r), "complete": FO.recette_complete(r)} for r in recettes],
            "tours": [{"graine": g, "a": FO.tours_question(g)[0], "z": FO.tours_question(g)[1],
                       "n": FO.tours_reponse(*FO.tours_question(g))} for g in graines],
            "noms": [{"texte": n, "nom": FO.nom_du_jeu(n)} for n in noms],
            "surs": [{"texte": s, "sur": FO.sur(s)} for s in surs],
            "photo_sha256": hashlib.sha256(o).hexdigest(), "photos": photos, "gifs": gifs, "wavs": wavs,
            "atelier": atelier, "textes": textes}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/forge/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_forge.py")
            sys.exit(1)
        print("vecteurs de la Forge à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
