"""Les données de la Forge (donnees/forge.json), ses fiches notions (charte de rigueur, docs/programme.md § 7.1) et sa
place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc, chmod +x en pont du niveau 6 ;
paliers F1 → F5, « Ton site web », « L'atelier multimédia »), ponts, attirance, contenu existant réutilisé (scripts0-2,
Q34-35, createur0-2 sur Android), exploits « premier programme qui marche du premier coup » et « un palier sans indice »,
variantes réservées des types Machine et Feu — des variantes qui EXISTENT déjà dans le bestiaire, ni gardiens ni déjà
réservées par un autre monde —, les Ponts des Nombres des boucles et des priorités, les maths des étapes et les étapes
rejouées dans bash.

    python3 donnees/forge/outils/fiches_forge.py     écrit donnees/forge.json, donnees/programme.json
                                                     et leurs copies (pc/tg, app/src/main/assets)

LA PHOTO D'EXEMPLE : une petite image (128 × 96, une plage, un drapeau) et des métadonnées INVENTÉES (l'appareil
« Terminacam TC-7 », une date, le lieu 0° N 0° E : « l'île Nulle », au croisement de l'équateur et du méridien de
Greenwich, au milieu de l'océan). Le JPEG de base (sans métadonnées) est écrit ci-dessous ; les métadonnées sont
ajoutées ici, au format Exif (TIFF « MM »), et lues par le jeu (forge exif) comme par exiftool (rejeu en CI).
"""
import base64
import json
import shutil
import struct
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------- la photo d'exemple (JPEG de base, sans métadonnées)
JPEG_BASE = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBAUEBAYFBQUGBgYHCQ4JCQgICRINDQoOFRIWFhUSFBQXGiEcFxgfGRQUHScdHyIj"
    "JSUlFhwpLCgkKyEkJST/2wBDAQYGBgkICREJCREkGBQYJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQk"
    "JCQkJCQkJCT/wAARCABgAIADASIAAhEBAxEB/8QAGgABAQEBAQEBAAAAAAAAAAAAAAQGBwUCA//EADgQAAEDAgIECQsFAAAAAAAA"
    "AAAREmEFExVCARQjUQQGBxdjZaKk4hYiJCVBRWKDwtHhQ0SCocH/xAAcAQEAAgMBAQEAAAAAAAAAAAAABQcCBAYDAQj/xAAuEQAA"
    "BgIAAwUIAwAAAAAAAAAAAQIDBBESMQUGIRMUQVGBByIyYXGR0fFyscH/2gAMAwEAAhEDEQA/ANOyQyShkhklj5DgqE7JDJKGSGSM"
    "goTskMkoZIZIyChOyQyShkhkjIKE7JDJKGSGSMgoTskMkoZJ6FKo+J3dvbtplVVWYNWbxBmEyqRIVihNWdGezrwIz2Y9o8ZyQ4TT"
    "RWo/34jx2SGSdIPOq1JxS1trVtcqqqTBwEH2ksuvpRIa7NB3asjVXTyJNnZ9B00jlNxDZqaXkryqr9TMYhkhklDJDJLJyHJ0KGSG"
    "SUNkNk1sx6UJ2SGSUNkNkZhQnZIZJQ2Q2RmFCdkhklDZDZGYUJ2SYSi1rCL2wu3W52oixp3nQ2ycpOT5llOMOMOtHSiy/wALxFlc"
    "gQWJrEuPITkhXZ2VmWjUZao9kN1RKxjN7YWbTc7lVY0bjphw+hULG7/pFm03I5VWdG40NP5NNeuetWMT9uqqvxQcnzE3J4jBalSO"
    "iW8rV0O8jItFRlRlWj8xKo4dwmBxF2K0/gpWPuYqOqTfxGZ3d38tDp4AK2GY8PjNoXVv5/4eGyT1Kjw/X7eztsXMqqn2I2yfoPli"
    "I9C4Y1HkJpZZWXQ9qM/Cy0Yq/jD7ciWt1o7Sdf0RD92SGSUMkMklsxo0J2SGSUMkMkZhQnZIZJQyQyRmFCdkhklDJDJGYUJ2Sc75"
    "Iq7jmLej2LNnO5VfGjcdMZJy/kTpWHYztrj7GVES5MkZKNJzGDPfvV9hMQnnEQJLaT91WF+iug6QyQyShkhkknmIehbjXQdv8EvD"
    "+Ga6zzGMX2qqp9j4ZIZJAw+XOGw3kyI7VLLR2o9lXiZloxJSOLS32zadXaT+RfgTskMkoZIZJPZiNoZbFuh7X4PPAK0l8QkS67dV"
    "1roRb+hCPUs1bAAGmMQKOCcL1V/mOcntQnB7R5DkdwnWjpRfrxH0jMjsh6GLdD2vwegZ8E/E5mkN325Z3rRV9iHql4y2PL5SPd3z"
    "foMUARM+X3p9T9VddN6IiFqQovdmUs3dX19bHaQYvk394/K+s2hZECX3phL9Vd9N6MyHATYvdnlM3dV19LAAG2NQAAAGfABTojwA"
    "AAAAAA82s1nCLOwu3XZ2oiRp3npGIrNZxezsLVp2dyqkaNx9IhM8E4f3uQWabQW+tbI68b35DzQAZiyxbTalh9zZXHpmREWJNOYs"
    "09NqWIXNlbYmZVVYgEOR5kgaktp/kd/Qi6fj1FoAPo5AAAAHbwAQwtwAAAAAAAOW8yHX/c/GdSBmhxSPhAct5kOv+5+McyHX/c/G"
    "dSBn3hzzAct5kOv+5+M1PEjiR5G676w1zWrf6NtrXfFpVXf0akGKnlqKjMAAB5gAAAD/2Q==")
MARQUE, MODELE = "Terminacam", "TC-7"
DATE = "2026:10:31 15:42:07"
DESCRIPTION = "Photo d'exemple du jeu Terminagotchi : metadonnees inventees"


def _ifd(entrees, debut):
    """Un IFD TIFF (gros-boutiste) à l'offset debut : entrees = [(tag, type, nombre, valeur octets)] ; (octets, suite)."""
    entrees = sorted(entrees)
    n = len(entrees)
    donnees_ = debut + 2 + 12 * n + 4
    tete, queue = struct.pack(">H", n), b""
    for tag, typ, nb, v in entrees:
        if len(v) <= 4:
            tete += struct.pack(">HHI", tag, typ, nb) + v.ljust(4, b"\0")
        else:
            tete += struct.pack(">HHII", tag, typ, nb, donnees_ + len(queue))
            queue += v + (b"\0" if len(v) % 2 else b"")
    return tete + b"\0\0\0\0" + queue


def _ascii(tag, s):
    v = s.encode("ascii") + b"\0"
    return (tag, 2, len(v), v)


def exif_tiff():
    """Les métadonnées inventées, au format TIFF (MM) : IFD0 (description, marque, modèle, date) → Exif IFD (version,
    date de la prise de vue) et GPS IFD (0° N, 0° E)."""
    rat0 = struct.pack(">IIIIII", 0, 1, 0, 1, 0, 1)
    gps = [(0x0000, 1, 4, bytes([2, 3, 0, 0])), _ascii(0x0001, "N"), (0x0002, 5, 3, rat0), _ascii(0x0003, "E"),
           (0x0004, 5, 3, rat0)]
    exif = [(0x9000, 7, 4, b"0232"), _ascii(0x9003, DATE)]
    ifd0 = [_ascii(0x010E, DESCRIPTION), _ascii(0x010F, MARQUE), _ascii(0x0110, MODELE), _ascii(0x0132, DATE)]
    # deux passes : la taille de l'IFD0 donne l'adresse des deux autres
    taille0 = len(_ifd(ifd0 + [(0x8769, 4, 1, b"\0" * 4), (0x8825, 4, 1, b"\0" * 4)], 8))
    off_exif = 8 + taille0
    b_exif = _ifd(exif, off_exif)
    off_gps = off_exif + len(b_exif)
    b_gps = _ifd(gps, off_gps)
    b0 = _ifd(ifd0 + [(0x8769, 4, 1, struct.pack(">I", off_exif)), (0x8825, 4, 1, struct.pack(">I", off_gps))], 8)
    assert len(b0) == taille0
    return b"MM\0\x2a" + struct.pack(">I", 8) + b0 + b_exif + b_gps


def photo():
    """Le JPEG d'exemple : SOI, le segment APP1 « Exif », puis l'image de base sans son en-tête JFIF."""
    base = base64.b64decode(JPEG_BASE)
    assert base[:2] == b"\xff\xd8" and base[2:4] == b"\xff\xe0"
    n = struct.unpack(">H", base[4:6])[0]
    reste = base[4 + n:]                                  # sans le segment APP0 (JFIF)
    app1 = b"Exif\0\0" + exif_tiff()
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + reste


# ---------------------------------------------------------------- la vue déployée : l'atelier de la forge
ATELIER = [
    {"motif": r"^python3?\s+-m\s+http\.server\b", "outil": "http.server", "objet": "lanterne", "de": "dossier", "vers": "pages"},
    {"motif": r"^python3?\b", "outil": "python3", "objet": "serpent", "de": "programme", "vers": "resultat"},
    {"motif": r"^(sh|bash|dash)\s+(?!\S*tests?\.sh\b)\S+\.sh\b|^\./\S+\.sh\b", "outil": "sh", "objet": "parchemin",
     "de": "recette", "vers": "commandes"},
    {"motif": r"^for\b", "outil": "for", "objet": "manege", "de": "liste", "vers": "tours"},
    {"motif": r"^while\b", "outil": "while", "objet": "manege", "de": "condition", "vers": "tours"},
    {"motif": r"^if\b", "outil": "if", "objet": "aiguillage", "de": "condition", "vers": "chemin"},
    {"motif": r"^(magick|convert)\b", "outil": "magick", "objet": "presse", "de": "images", "vers": "animation"},
    {"motif": r"^ffmpeg\b", "outil": "ffmpeg", "objet": "ciseaux_sons", "de": "son", "vers": "morceau"},
    {"motif": r"^sox\b", "outil": "sox", "objet": "diapason", "de": "silence", "vers": "son"},
    {"motif": r"^exiftool\b", "outil": "exiftool", "objet": "loupe", "de": "photo", "vers": "etiquettes"},
]
COULEURS = {"lanterne": 229, "serpent": 78, "parchemin": 214, "manege": 213, "aiguillage": 117, "presse": 141,
            "ciseaux_sons": 203, "diapason": 39, "loupe": 179}
# ce qu'affiche python3 serpent.py sans arguments (Python 3.11 et plus), quand Python manque : raconté
TRACEBACK = ["Traceback (most recent call last):", '  File "serpent.py", line 5, in <module>', "    nom = sys.argv[1]",
             "          ~~~~~~~~^^^", "IndexError: list index out of range"]


def donnees_forge():
    return {
        "note": "Généré par donnees/forge/outils/fiches_forge.py ; lu par pc/tg/forge.py et Forge.kt. Tout reste dans le "
                "terrain (forge/) ; le site est servi sur 127.0.0.1 seulement ; la photo d'exemple a des métadonnées "
                "INVENTÉES (jamais les photos de l'enfant).",
        "site": {"port": 8642, "plage": 20},
        "atelier": {"regles": ATELIER}, "couleurs": COULEURS,
        "photo": {"base64": base64.b64encode(photo()).decode("ascii"), "marque": MARQUE, "modele": MODELE, "date": DATE,
                  "gps": [0, 0]},
        "multimedia": {"sauts": [0, 2, 4, 2], "fanfare_hz": [523.25, 659.25, 783.99, 1046.5], "note_s": 0.25},
        "traceback": TRACEBACK,
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"fo.f.{nid}.enfant", "grands": f"fo.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"fo.f.{nid}.limite", "idees_fausses": [f"fo.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_POSIX = "POSIX.1-2024, Shell Command Language (paramètres, $?, if, for, while, read) : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html"
S_BASH = "GNU Bash, manuel de référence : https://www.gnu.org/software/bash/manual/bash.html"
S_COREUTILS = "GNU coreutils, manuel (chmod, seq, ls) : https://www.gnu.org/software/coreutils/manual/"
S_PYTHON = "Python, documentation (ligne de commande, sys.argv, erreurs et Traceback) : https://docs.python.org/3/using/cmdline.html ; https://docs.python.org/3/tutorial/errors.html"
S_HTML = "MDN Web Docs, HTML et CSS (premiers pas) : https://developer.mozilla.org/fr/docs/Learn"
S_HTTP = "Python, http.server (« not recommended for production », --bind) : https://docs.python.org/3/library/http.server.html"
S_IM = "ImageMagick, documentation (animations, -delay, -loop) : https://imagemagick.org/script/command-line-options.php"
S_FFMPEG = "FFmpeg, documentation (-ss, -t) : https://ffmpeg.org/ffmpeg.html"
S_SOX = "SoX, documentation (synth) : https://sourceforge.net/projects/sox/"
S_EXIF = "ExifTool (Phil Harvey), documentation : https://exiftool.org/ ; CNIL, « Photos : attention aux métadonnées » : https://www.cnil.fr/"
B64 = base64.b64encode(photo()).decode("ascii")
RECETTE = "printf '#!/bin/sh\\nmkdir -p cabane\\ntouch cabane/porte.txt\\n' > c.sh"
SITE = ("mkdir site && echo '<h1>Bonjour</h1>' > site/index.html && echo 'h1 {{ color: orange; }}' > site/style.css && "
        "(python3 -m http.server {p} --bind 127.0.0.1 --directory site >/dev/null 2>&1 & echo $! > pid) && sleep 1")
PNG2 = "convert -size 4x4 xc:red a.png && convert -size 4x4 xc:blue b.png"
FICHES = dict([
    fiche("recette", r"(^(tg\s+)?forge\s+(recettes?|plan|enclume|regles|bilan)\b|cabane\.sh|#!/bin/sh|^\./\S+\.sh|enclume\.txt)", [
        {"prepare": RECETTE, "cmd": "sh c.sh && ls cabane", "sortie": "porte.txt"},
        {"prepare": RECETTE, "cmd": "head -1 c.sh", "sortie": "#!/bin/sh"},
        {"prepare": RECETTE, "cmd": "./c.sh", "motif": "Permission denied", "code": "non0"},
        {"prepare": RECETTE, "cmd": "chmod +x c.sh && ./c.sh && ls cabane", "sortie": "porte.txt"}],
        [S_POSIX, S_BASH, S_COREUTILS]),
    fiche("parametres", r"(^[A-Za-z_]\w*=|\$\{?[1#]|\$\{?nom\b|salut\.sh|question\.sh|(^|\s)read\b|^(tg\s+)?forge\s+bo[iî]tes?\b)", [
        {"cmd": "nom=Pixel; echo \"Bonjour $nom\"", "sortie": "Bonjour Pixel"},
        {"prepare": "echo 'echo \"Bonjour $1 !\"' > s.sh", "cmd": "sh s.sh Léa", "sortie": "Bonjour Léa !"},
        {"prepare": "echo 'echo \"$# mots\"' > s.sh", "cmd": "sh s.sh un deux trois", "sortie": "3 mots"},
        {"prepare": "echo 'read p; echo \"Salut $p !\"' > q.sh", "cmd": "echo Léa | sh q.sh", "sortie": "Salut Léa !"}],
        [S_POSIX, S_BASH]),
    fiche("aiguillage", r"(\$\?|^if\b|^for\b|^while\b|village|^(tg\s+)?forge\s+(aiguillages?|code|tours)\b)", [
        {"cmd": "ls fantome; echo $?", "motif": "^2$"},
        {"cmd": "if [ -f absent ]; then echo oui; else echo non; fi", "sortie": "non"},
        {"cmd": "for i in $(seq 1 3); do echo \"Tour $i\"; done", "sortie": "Tour 1\nTour 2\nTour 3"},
        {"cmd": "for i in $(seq 1 10); do mkdir -p v/c_$i; done; ls v | wc -l", "sortie": "10"},
        {"cmd": "n=3; while [ $n -gt 0 ]; do echo $n; n=$((n - 1)); done", "sortie": "3\n2\n1"}],
        [S_POSIX, S_BASH, S_COREUTILS]),
    fiche("python", r"(^python3?\b|serpent\.py|^(tg\s+)?forge\s+(serpents?|erreur|python)\b)", [
        {"cmd": "python3 -c \"print(2 + 3 * 4)\"", "sortie": "14", "outil": "python3"},
        {"cmd": "python3 -c \"for i in range(3): print('Pixel')\"", "sortie": "Pixel\nPixel\nPixel", "outil": "python3"},
        {"prepare": "printf 'import sys\\nnom = sys.argv[1]\\nprint(nom)\\n' > s.py", "cmd": "python3 s.py",
         "motif": "^IndexError: list index out of range$", "code": "non0", "outil": "python3"},
        {"prepare": "printf 'import sys\\nnom = sys.argv[1]\\nprint(nom)\\n' > s.py", "cmd": "python3 s.py Pixel",
         "sortie": "Pixel", "outil": "python3"}],
        [S_PYTHON]),
    fiche("mini_jeu", r"(mon_jeu|devinette|donjon|^(tg\s+)?forge\s+(jeu|carte)\b)", [
        {"prepare": "printf 'secret=7\\nreponse=0\\nwhile [ \"$reponse\" != \"$secret\" ]; do\\n  read reponse || exit 1\\n"
                    "done\\necho Bravo\\n' > d.sh", "cmd": "seq 1 10 | sh d.sh", "sortie": "Bravo"},
        {"cmd": "for s in 1 2 3; do mkdir -p donjon/salle_$s; done && ls donjon", "sortie": "salle_1\nsalle_2\nsalle_3"},
        {"cmd": "printf '1\\n2\\n' | while read n; do echo \"essai $n\"; done", "sortie": "essai 1\nessai 2"}],
        [S_POSIX, S_BASH]),
    fiche("site_web", r"(site/|^(tg\s+)?forge\s+(site|serveur|publi\w*)\b|:8642\b|^fg\b|localhost:\d+)", [
        {"prepare": SITE.format(p=8790), "cmd": "curl -s http://127.0.0.1:8790/; kill $(cat pid)", "sortie": "<h1>Bonjour</h1>",
         "outil": "python3"},
        {"prepare": SITE.format(p=8791), "cmd": "curl -s -o /dev/null -w '%{content_type}\\n' http://127.0.0.1:8791/style.css; "
                                               "kill $(cat pid)", "sortie": "text/css", "outil": "python3"},
        {"prepare": SITE.format(p=8792), "cmd": "curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8792/rien.html; "
                                               "kill $(cat pid)", "sortie": "404", "outil": "python3"}],
        [S_HTML, S_HTTP, "RFC 9110, HTTP Semantics : https://www.rfc-editor.org/rfc/rfc9110"]),
    fiche("multimedia", r"(^(magick|convert|ffmpeg|sox|exiftool)\b|multimedia|photo_exemple|^(tg\s+)?forge\s+(multim[eé]dia\w*|exif|appareil|nettoie)\b)", [
        {"prepare": PNG2, "cmd": "convert -delay 20 -loop 0 a.png b.png anim.gif && identify anim.gif | wc -l", "sortie": "2",
         "outil": "convert"},
        {"prepare": PNG2, "cmd": "convert -delay 20 -loop 0 a.png b.png anim.gif && head -c 6 anim.gif", "sortie": "GIF89a",
         "outil": "convert"},
        {"cmd": "sox -n la.wav synth 0.5 sine 440 && soxi -D la.wav", "sortie": "0.500000", "outil": "sox"},
        {"prepare": "ffmpeg -loglevel error -f lavfi -i sine=frequency=440:duration=1 f.wav",
         "cmd": "ffmpeg -loglevel error -i f.wav -ss 0.5 -t 0.25 g.wav && ffprobe -v error -show_entries format=duration "
                "-of csv=p=0 g.wav", "sortie": "0.250000", "outil": "ffmpeg"},
        {"prepare": f"echo {B64} | base64 -d > p.jpg", "cmd": "exiftool -s3 -Make -Model p.jpg", "sortie": "Terminacam\nTC-7",
         "outil": "exiftool"},
        {"prepare": f"echo {B64} | base64 -d > p.jpg", "cmd": "exiftool -s3 -GPSLatitude -GPSLongitude p.jpg",
         "motif": "^0 deg 0' 0\\.00\"( N)?$", "outil": "exiftool"},
        {"prepare": f"echo {B64} | base64 -d > p.jpg",
         "cmd": "exiftool -all= -overwrite_original p.jpg >/dev/null && exiftool -s3 -Make p.jpg | wc -l", "sortie": "0",
         "outil": "exiftool"}],
        [S_IM, S_FFMPEG, S_SOX, S_EXIF]),
])

FORGE = {"id": "forge", "types": ["machine", "feu"], "requis": ["n4"], "chapitre": "forge",
         "paliers": [f"fo{i}" for i in range(8)],
         "attirance": {"cmds": ["sh", "bash", "python3", "nano", "chmod", "seq"], "activites": ["donjon", "doom", "edite"],
                       "familles": ["Constructs"]},
         "ponts": {"chmod_x": ["n6"], "http_server": ["port"], "compiler": ["guilde"], "git": ["temps"],
                   "variables": ["controle", "observatoire"], "boucles": ["donnees"]},
         "reutilise": {"lecons": ["atelier0", "scripts0", "scripts1", "scripts2"], "quetes": ["q34", "q35"],
                       "android": ["createur0", "createur1", "createur2"], "defis": ["code"]},
         "exploits": [{"id": "forge.sans_indice", "nom": "recomp.forge.sans_indice", "recompense": "variante"},
                      {"id": "forge.premier_coup", "nom": "recomp.forge.premier_coup", "recompense": "variante"}],
         "maths": ["logique", "boucles", "priorites"],
         "variantes_reservees": ["fondelin:lave", "boulonnet:neon", "tisonnier:mecanique"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


S_ARITH = "Bash, Shell Arithmetic (priorités des opérateurs) : https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html"
S_CYCLES = "Programmes de mathématiques des cycles 3 et 4 (priorités opératoires, algorithmique et programmation) : https://eduscol.education.fr/"
MATHS = dict([
    maths_fiche("boucles", ["comptage", "soustraction"], "primaire", [
        {"cmd": "seq 3 7 | wc -l", "sortie": "5"},
        {"cmd": "for i in $(seq 3 7); do echo $i; done | wc -l", "sortie": "5"}], [S_CYCLES, S_COREUTILS]),
    maths_fiche("priorites", ["addition", "multiplication"], "college", [
        {"cmd": "echo $((2 + 3 * 4))", "sortie": "14"}, {"cmd": "echo $(( (2 + 3) * 4 ))", "sortie": "20"}],
        [S_CYCLES, S_ARITH]),
])

ETAPES = {"fo3.4": {"maths": ["boucles"]}, "fo3.5": {"maths": ["boucles"]}, "fo3.8": {"maths": ["boucles"]},
          "fo3.7": {"maths": ["soustraction"]}, "fo4.2": {"maths": ["priorites"]}}


def rejeu():
    """Ce que le jeu affirme des vraies sorties de la Forge (histoire du PC rejouée dans un vrai bash)."""
    return {
        "fo0.1": {"contient": ["enclume.txt", "carnet_de_la_forge.txt"], "pourquoi": "hist.fo0.1.bravo : l'enclume et le carnet"},
        "fo1.4": {"sortie": "#!/bin/sh\nmkdir -p cabane\ntouch cabane/porte.txt cabane/toit.txt",
                  "pourquoi": "hist.fo1.4.bravo : la recette, ligne par ligne"},
        "fo1.5": {"apres": "ls cabane", "sortie": "porte.txt\ntoit.txt", "pourquoi": "hist.fo1.5.bravo : la cabane est bâtie"},
        "fo1.7": {"code": 0, "pourquoi": "hist.fo1.7.bravo : ./ lance la recette devenue exécutable"},
        "fo2.2": {"sortie": "Bonjour Pixel", "pourquoi": "hist.fo2.2.bravo : $nom est remplacé par ce qu'il y a dans la boîte"},
        "fo2.4": {"sortie": "Bonjour Léa !", "pourquoi": "hist.fo2.4.bravo : $1 est le premier mot après le nom du script"},
        "fo2.6": {"sortie": "Bonjour Léa !\nTu as donné 3 prénoms.", "pourquoi": "hist.fo2.6.bravo : $# compte les mots"},
        "fo2.8": {"sortie": "Salut Léa !", "pourquoi": "hist.fo2.8.bravo : read range la réponse dans une boîte"},
        "fo3.1": {"motif": r"^[1-9]\d*$", "pourquoi": "hist.fo3.1.bravo : pas 0 = ça n'a pas marché"},
        "fo3.3": {"sortie": "La porte est là !", "pourquoi": "hist.fo3.3.bravo : la condition est vraie"},
        "fo3.4": {"sortie": "Tour 1\nTour 2\nTour 3", "pourquoi": "hist.fo3.4.bravo : un tour par élément de la liste"},
        "fo3.6": {"sortie": "10", "pourquoi": "hist.fo3.6.bravo : 10 cabanes"},
        "fo3.7": {"sortie": "3\n2\n1", "pourquoi": "hist.fo3.7.bravo : le compte à rebours"},
        "fo4.1": {"motif": r"^Python 3\.", "outil": "python3", "pourquoi": "hist.fo4.1.bravo : la version de Python"},
        "fo4.2": {"sortie": "14", "outil": "python3", "pourquoi": "hist.fo4.2.bravo : la multiplication d'abord"},
        "fo4.3": {"sortie": "Pixel\nPixel\nPixel", "outil": "python3", "pourquoi": "hist.fo4.3.bravo : trois fois"},
        "fo4.5": {"motif": r"^IndexError: list index out of range$", "code": "non0", "outil": "python3",
                  "pourquoi": "hist.fo4.5.bravo : la dernière ligne du Traceback"},
        "fo4.7": {"motif": r"\A1\. .*Pixel.*\n2\. .*\n3\. .*Pixel", "outil": "python3", "pourquoi": "hist.fo4.7.bravo : 3 fois Pixel"},
        "fo5.3": {"code": 0, "motif": r"\d", "pourquoi": "hist.fo5.3.bravo : le robot essaie 1, 2, 3… et trouve"},
        "fo5.5": {"apres": "ls mon_jeu/donjon", "sortie": "salle_1\nsalle_2\nsalle_3", "pourquoi": "hist.fo5.5.bravo : trois salles"},
        "fo6.5": {"sortie": "<h1>Bienvenue chez Pixel</h1>\n<p>Ici vit ma créature. Elle adore les cabanes.</p>\n"
                            "<link rel=\"stylesheet\" href=\"style.css\">", "pourquoi": "hist.fo6.5.bravo : ta page"},
        "fo6.7": {"motif": r"^<h1>Bienvenue chez Pixel</h1>\n<p>Ici vit ma créature\. Elle adore les cabanes\.</p>\n"
                           r"<link rel=\"stylesheet\" href=\"style\.css\">$", "outil": "python3",
                  "pourquoi": "hist.fo6.7.bravo : curl reçoit exactement ta page"},
        "fo7.2": {"apres": "identify multimedia/creature.gif | wc -l", "sortie": "4", "outil": "identify",
                  "pourquoi": "hist.fo7.2.bravo : 4 images dans le GIF"},
        "fo7.3": {"apres": "soxi -D multimedia/la.wav", "sortie": "0.500000", "outil": "sox",
                  "pourquoi": "hist.fo7.3.bravo : un la d'une demi-seconde"},
        "fo7.4": {"apres": "ffprobe -v error -show_entries format=duration -of csv=p=0 multimedia/fin.wav", "sortie": "0.500000",
                  "outil": "ffmpeg", "pourquoi": "hist.fo7.4.bravo : le morceau coupé dure 0,5 s"},
        "fo7.5": {"motif": "Terminacam", "pourquoi": "hist.fo7.5.bravo : la marque de l'appareil"},
        "fo7.7": {"apres": "grep -c Exif multimedia/photo_exemple.jpg", "sortie": "0",
                  "pourquoi": "hist.fo7.7.bravo : plus aucune métadonnée Exif"},
    }


def main():
    G = donnees_forge()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    for c in ("donnees/forge.json", "pc/tg/forge.json", "app/src/main/assets/forge.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    P["mondes"] = [FORGE if m["id"] == "forge" else m for m in P["mondes"]]
    for cle in ("etapes", "rejeu"):                   # les étapes de la Forge : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("fo") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Forge, {len(MATHS)} ponts des nombres, {len(R)} étapes rejouées ; forge.json écrit")


if __name__ == "__main__":
    if "--photo" in sys.argv:                          # (pour regarder la photo d'exemple)
        sys.stdout.buffer.write(photo())
    else:
        main()
