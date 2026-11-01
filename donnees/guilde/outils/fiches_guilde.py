"""Les données de la Guilde des Bâtisseurs Libres (donnees/guilde.json), ses fiches notions (charte de rigueur,
docs/programme.md § 7.1) et sa place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc,
paliers, ponts dont la Bibliothèque du Temps pour git, attirance, exploit « artisan », variantes réservées des types
Machine et Plante — des variantes qui EXISTENT déjà dans le bestiaire), les deux Ponts des Nombres de la fabrique
(coordonnées, volume), les maths des étapes et les étapes rejouées dans bash.

    python3 donnees/guilde/outils/fiches_guilde.py    écrit donnees/guilde.json, donnees/programme.json et leurs copies

guilde.json garde aussi, pour le téléphone (qui n'a ni git ni le code du jeu), des EXTRAITS du vrai code du jeu
(pc/tg/satiete.py…) et les vraies phrases du jeu copiées pour l'exercice de contribution (pc/tg/langues/fr.json) :
ils sont relus ici à chaque fois, jamais inventés. Chaque cas « vrai_terminal » est rejoué dans un bash neuf par
pc/outils/rejeu_bash.py, dans un terrain jetable. Rien ne sort du terrain, jamais de sudo, jamais de /dev.
"""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]
ICI = Path(__file__).resolve().parent


def _fr():
    spec = importlib.util.spec_from_file_location("textes_guilde_fr", ICI / "textes_guilde_fr.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.K


BONJOUR_C = '#include <stdio.h>\n\nint main(void) {\n    printf("@MESSAGE@\\n");\n    return 0;\n}\n'
ETOILES_C = ('#include <stdio.h>\n#include <stdlib.h>\n\n/* ./etoiles 5 : 5 etoiles */\nint main(int argc, char *argv[]) {\n'
             '    int n = argc > 1 ? atoi(argv[1]) : 3;\n    if (n > 80) n = 80;\n'
             "    for (int i = 0; i < n; i++) putchar('*');\n    putchar('\\n');\n    return 0;\n}\n")
LICENCE_MIT = """MIT License

Copyright (c) 2026 La Guilde des Bâtisseurs Libres (projet d'exemple)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# les phrases du jeu copiées pour l'exercice (relues dans pc/tg/langues/fr.json) et la faute volontaire possible
PHRASES = ["core.notif.faim", "qu.journal.rien", "hist.racine.1.dit", "qu.cachette.dit", "lec.t2.2.bravo", "hist.sm9.7.bravo"]
FAUTES = [{"ligne": 0, "juste": "faim", "faux": "fain"}, {"ligne": 1, "juste": "continue", "faux": "contiune"},
          {"ligne": 2, "juste": "autour", "faux": "autoure"}, {"ligne": 3, "juste": "secret", "faux": "secrai"},
          {"ligne": 4, "juste": "trouvé", "faux": "trouver"}, {"ligne": 5, "juste": "exactement", "faux": "exactemment"}]

# les extraits du vrai code du jeu, pour la copie du téléphone : (fichier, première ligne, dernière ligne)
EXTRAITS = [("pc/tg/satiete.py", 1, 112), ("pc/tg/aura.py", 1, 120), ("pc/tg/envies.py", 1, 40)]


def familles():
    F = [("agpl", "GNU AGPL", "copyleft", r"GNU AFFERO GENERAL PUBLIC LICENSE|\bAGPL"),
         ("lgpl", "GNU LGPL", "copyleft", r"GNU (LESSER|LIBRARY) GENERAL PUBLIC LICENSE|\bLGPL"),
         ("gpl", "GNU GPL", "copyleft", r"GNU GENERAL PUBLIC LICENSE|\bGPL"),
         ("mpl", "Mozilla Public License", "copyleft", r"Mozilla Public License|\bMPL-?\d"),
         ("apache", "Apache License", "permissive", r"Apache License|\bApache-2"),
         ("mit", "MIT", "permissive", r"\bMIT\b|Permission is hereby granted, free of charge"),
         ("bsd", "BSD", "permissive", r"\bBSD\b|Redistribution and use in source and binary forms"),
         ("psf", "Python Software Foundation License", "permissive", r"Python Software Foundation|\bPSF-"),
         ("zlib", "zlib", "permissive", r"\bzlib License\b|\bZlib\b|provided 'as-is', without any express"),
         ("cc", "Creative Commons", "cc", r"Creative Commons|\bCC-BY|\bCC0"),
         ("domaine_public", "Public domain", "domaine", r"public domain|\bUnlicense\b")]
    return [{"id": i, "nom": n, "genre": g, "motif": m} for i, n, g, m in F]


CATALOGUE = {"bash": "gpl", "coreutils": "gpl", "grep": "gpl", "sed": "gpl", "gawk": "gpl", "gcc": "gpl", "make": "gpl",
             "git": "gpl", "nano": "gpl", "linux": "gpl", "gimp": "gpl", "inkscape": "gpl", "openscad": "gpl", "vlc": "gpl",
             "blender": "gpl", "krita": "gpl", "audacity": "gpl", "tar": "gpl", "glibc": "lgpl", "ffmpeg": "lgpl",
             "libreoffice": "mpl", "firefox": "mpl", "thunderbird": "mpl", "python3": "psf", "python": "psf",
             "curl": "mit", "nodejs": "mit", "openssl": "apache", "zlib": "zlib", "sqlite": "domaine_public",
             "sqlite3": "domaine_public"}


def donnees_guilde():
    fr_jeu = json.loads((D / "pc/tg/langues/fr.json").read_text(encoding="utf-8"))
    extraits = {}
    for f, a, b in EXTRAITS:
        lignes = (D / f).read_text(encoding="utf-8").split("\n")
        extraits[f] = "\n".join(lignes[a - 1:b]) + "\n"
    lignes = [{"cle": k, "texte": fr_jeu[k]} for k in PHRASES]
    for x in FAUTES:
        txt = lignes[x["ligne"]]["texte"]
        assert x["juste"] in txt and all(x["faux"] not in l["texte"] for l in lignes), x
    return {
        "note": "Généré par donnees/guilde/outils/fiches_guilde.py ; lu par pc/tg/guilde.py et Guilde.kt",
        "libertes": {"situations": [{"id": "jouer", "rep": 0}, {"id": "lire", "rep": 1}, {"id": "donner", "rep": 2},
                                    {"id": "ameliorer", "rep": 3}]},
        "gratuit": [{"id": "jeu_ferme", "rep": "p"}, {"id": "libre_payant", "rep": "l"}, {"id": "appli_pubs", "rep": "p"},
                    {"id": "blender", "rep": "l"}],
        "licences": {"a_trouver": 5, "familles": familles(), "catalogue": CATALOGUE},
        "faim": {"marques": [r"^def etat_de\(", r"point de faim"], "fichier_tel": "satiete.py"},
        "extraits": extraits,
        "code": {"bonjour_c": BONJOUR_C, "etoiles_c": ETOILES_C, "licence_mit": LICENCE_MIT},
        "contribution": {"entete": ["# Terminagotchi : langues/fr.txt (copie d'exercice de la Guilde)", ""],
                         "lignes": lignes, "fautes": FAUTES,
                         "apprenti_nom": "Apprenti de la Guilde", "apprenti_email": "apprenti@terminagotchi.invalid",
                         "guilde_nom": "La Guilde", "guilde_email": "guilde@terminagotchi.invalid",
                         "premier_commit": "Textes du jeu (copie pour s'entrainer)"},
        "piece": {"longueurs": [36, 40, 44, 48], "largeurs": [16, 20, 24, 28], "epaisseurs": [3, 4, 5], "trou_x": 6,
                  "trou_d": 5},
        "image": {"octets": 65536, "cle_octets": 131072,
                  "entete": "TERMINAGOTCHI - FAUSSE IMAGE D'EXEMPLE : ce n'est pas un vrai systeme, "
                            "elle sert a apprendre dd et sha256sum.\n"},
        "disques": {"noms": ["sda", "sdb"], "sauvegarde": "1.8T", "systeme": "476.9G", "systeme_racine": "476.3G",
                    "cles": [{"go": 8, "lsblk": "7.5G"}, {"go": 16, "lsblk": "14.6G"}, {"go": 32, "lsblk": "28.9G"},
                             {"go": 64, "lsblk": "57.7G"}]},
        "etabli": {"regles": [
            {"motif": r"^(gcc|cc|clang)\b", "outil": "gcc", "de": "texte", "vers": "programme"},
            {"motif": r"^make\b", "outil": "make", "de": "recette", "vers": "programme"},
            {"motif": r"^openscad\b", "outil": "openscad", "de": "code", "vers": "piece"},
            {"motif": r"^dd\b", "outil": "dd", "de": "image", "vers": "cle"},
            {"motif": r"^sha256sum\b", "outil": "sha256sum", "de": "fichier", "vers": "empreinte"},
            {"motif": r"^git\s+clone\b", "outil": "git clone", "de": "depot", "vers": "copie"},
            {"motif": r"^git\s+diff\b", "outil": "git diff", "de": "version", "vers": "difference"},
            {"motif": r"^git\s+commit\b", "outil": "git commit", "de": "changement", "vers": "version"}]},
        "credits": {"contributeurs": []},
        "couleurs": {"gcc": 215, "make": 215, "openscad": 229, "dd": 117, "sha256sum": 78, "git clone": 141,
                     "git diff": 141, "git commit": 141},
    }


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"gu.f.{nid}.enfant", "grands": f"gu.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"gu.f.{nid}.limite", "idees_fausses": [f"gu.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


C_MINI = "printf '#include <stdio.h>\\nint main(void) { puts(\"ok\"); return 0; }\\n' > b.c && gcc b.c -o b"
FICHES = dict([
    fiche("libre", r"(guilde\s+(libert\w*|gratuit\w*|licences?)\b|LICENSE\b|/usr/share/licenses|^rpm\s+-q\b)", [
        {"prepare": "printf 'MIT License\\n\\nPermission is hereby granted, free of charge\\n' > LICENSE",
         "cmd": "head -1 LICENSE", "sortie": "MIT License"},
        {"cmd": "ls /usr/share/licenses | head -1", "motif": r"\S", "outil": "/usr/share/licenses"},
        {"cmd": "rpm -q --qf '%{LICENSE}\\n' bash", "motif": "GPL", "outil": "rpm", "si": "rpm -q bash"}],
        ["Free Software Foundation, « Qu'est-ce que le logiciel libre ? » : https://www.gnu.org/philosophy/free-sw.fr.html",
         "Open Source Initiative, The Open Source Definition : https://opensource.org/osd",
         "SPDX License List (identifiants des licences) : https://spdx.org/licenses/",
         "Creative Commons, les licences : https://creativecommons.org/licenses/?lang=fr",
         "Fedora Packaging Guidelines, Licensing (%license, /usr/share/licenses) ; Debian Policy § 12.5 (copyright)"]),
    fiche("lire_code", r"(guilde\s+(d[eé]p[oô]t|copie|faim)\b|^git\s+clone\b|code_du_jeu)", [
        {"prepare": "mkdir -p jeu/pc/tg && printf 'def etat_de(faim):\\n    return faim\\n' > jeu/pc/tg/satiete.py",
         "cmd": "grep -rn \"def etat_de\" jeu/pc/tg", "sortie": "jeu/pc/tg/satiete.py:1:def etat_de(faim):"},
        {"prepare": "mkdir -p jeu/pc/tg && touch jeu/pc/tg/a.py jeu/pc/tg/b.py && echo faim > jeu/pc/tg/b.py",
         "cmd": "grep -rl faim jeu", "sortie": "jeu/pc/tg/b.py"},
        {"prepare": "mkdir -p jeu/pc/tg", "cmd": "tree -L 2 jeu", "motif": r"── tg$", "outil": "tree"},
        {"cmd": "git clone --depth 1 https://github.com/grecdel/terminagotchi.git code_du_jeu", "rejeu": "reseau",
         "motif": "Cloning into"}],
        ["git-clone(1) : https://git-scm.com/docs/git-clone (--depth)",
         "GNU grep, manuel (-r, -l, -n) : https://www.gnu.org/software/grep/manual/grep.html",
         "tree(1) : https://oldmanprogrammer.net/source.php?dir=projects/tree ; less(1)",
         "Free Software Foundation, liberté 1 (étudier le fonctionnement du programme)"]),
    fiche("compiler", r"(guilde\s+(compil\w*|gcc)\b|^(gcc|cc|clang|make|file|ldd|od)\b.*(bonjour|etoiles)|bonjour\.c|etoiles\.c)", [
        {"prepare": "printf '#include <stdio.h>\\nint main(void) { puts(\"ok\"); return 0; }\\n' > b.c",
         "cmd": "gcc b.c -o b && ./b", "sortie": "ok", "outil": "gcc"},
        {"prepare": C_MINI, "cmd": "od -An -tx1 -N4 b", "sortie": " 7f 45 4c 46", "outil": "gcc"},
        {"prepare": C_MINI, "cmd": "file b", "motif": "ELF", "outil": "file", "si": "command -v gcc"},
        {"prepare": "printf '#include <stdio.h>\\nint main(void) { puts(\"e\"); return 0; }\\n' > e.c",
         "cmd": "make e >/dev/null && ./e", "sortie": "e", "outil": "make", "si": "command -v gcc"}],
        ["GCC, manuel (options -o, étapes de la compilation) : https://gcc.gnu.org/onlinedocs/gcc/Overall-Options.html",
         "GNU make, règles implicites : https://www.gnu.org/software/make/manual/html_node/Implicit-Rules.html",
         "elf(5) (nombre magique 0x7f 'E' 'L' 'F') : https://man7.org/linux/man-pages/man5/elf.5.html",
         "ldd(1) : https://man7.org/linux/man-pages/man1/ldd.1.html"]),
    fiche("contribuer", r"(guilde\s+(contribu|fusion|credits)\w*|^git\s+(switch|checkout|diff|commit|log|status)\b|langues/fr\.txt)", [
        {"prepare": "git init -q -b main d && cd d && git config user.name A && git config user.email a@a.invalid && "
                    "echo fain > t && git add t && git commit -qm 1",
         "cmd": "cd d && git switch -q -c corrige && sed -i s/fain/faim/ t && git diff --stat | tail -1",
         "sortie": " 1 file changed, 1 insertion(+), 1 deletion(-)", "outil": "git"},
        {"prepare": "git init -q -b main d && cd d && git config user.name A && git config user.email a@a.invalid && "
                    "echo fain > t && git add t && git commit -qm 1 && git switch -q -c corrige && echo faim > t",
         "cmd": "cd d && git commit -qam 'Corrige une faute' && git log --oneline | wc -l", "sortie": "2", "outil": "git"}],
        ["Pro Git, 5.2 Contribuer à un projet : https://git-scm.com/book/fr/v2/Git-distribu%C3%A9-Contribution-%C3%A0-un-projet",
         "git-switch(1), git-diff(1), git-commit(1) : https://git-scm.com/docs",
         "Open Source Guides, « How to Contribute to Open Source » : https://opensource.guide/how-to-contribute/"]),
    fiche("fabriquer", r"(guilde\s+(pi[eè]ce|trou|volume|stl)\b|^openscad\b|porte_cle\.(scad|stl))", [
        {"cmd": "echo $((40 * 24 * 4))", "sortie": "3840"},
        {"prepare": "printf 'solid p\\n  facet normal 0 0 1\\n' > p.stl", "cmd": "head -1 p.stl", "sortie": "solid p"},
        {"cmd": "openscad --version", "motif": "OpenSCAD", "outil": "openscad"}],
        ["OpenSCAD User Manual (cube, cylinder, translate, difference ; export STL) : https://en.wikibooks.org/wiki/OpenSCAD_User_Manual",
         "3D Systems, StereoLithography Interface Specification (format STL, 1989)",
         "ISO/ASTM 52900:2021, fabrication additive : principes généraux et vocabulaire"]),
    fiche("redonner_vie", r"(guilde\s+(sauver|vieux|cl[eé]|disques?|certificat)\w*|^lsblk\b|^sha256sum\b.*(image_linux|cle_usb)|^dd\b|cle_usb)", [
        {"prepare": "printf abc > i.iso", "cmd": "sha256sum i.iso",
         "sortie": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  i.iso"},
        {"prepare": "printf abc > i.iso && sha256sum i.iso > i.iso.sha256", "cmd": "sha256sum -c i.iso.sha256",
         "sortie": "i.iso: OK"},
        {"prepare": "printf abc > i.iso && : > c.img", "cmd": "dd if=i.iso of=c.img bs=64k 2>/dev/null && cmp i.iso c.img && echo pareil",
         "sortie": "pareil"},
        {"cmd": "lsblk -d -o NAME,RM,TYPE | head -1", "motif": r"^NAME\s+RM\s+TYPE", "outil": "lsblk"}],
        ["lsblk(8), util-linux : https://man7.org/linux/man-pages/man8/lsblk.8.html",
         "dd(1) et sha256sum(1), GNU coreutils : https://www.gnu.org/software/coreutils/manual/",
         "Fedora, préparer un support de démarrage (vérifier l'image) : https://docs.fedoraproject.org/en-US/fedora/latest/preparing-boot-media/",
         "ADEME et Arcep, Évaluation de l'impact environnemental du numérique en France (2022) : la fabrication des terminaux domine l'empreinte"]),
])

GUILDE = {"id": "guilde", "types": ["machine", "plante"], "requis": ["n4"], "paliers": [f"gu{i}" for i in range(7)],
          "chapitre": "guilde",
          "attirance": {"cmds": ["gcc", "make", "git", "openscad", "dd"], "familles": ["Constructs", "Sylvestres"]},
          "ponts": {"git": ["temps"], "gcc": ["forge"], "sha256sum": ["crypte"], "lsblk": ["machines"]},
          "exploits": [{"id": "guilde.artisan", "nom": "recomp.guilde.artisan", "recompense": "variante"}],
          "maths": ["coordonnees", "volume", "hexadecimal"],
          "variantes_reservees": ["engrenaille:mecanique", "rouillot:rouille", "lampignon:champignonniere"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


MATHS = dict([
    maths_fiche("coordonnees", ["soustraction"], "college", [
        {"cmd": "echo $((10 - 3))", "sortie": "7"}, {"cmd": "echo $((24 / 2))", "sortie": "12"}],
        ["Programme de mathématiques du cycle 3 et du cycle 4 (se repérer dans le plan, repère orthogonal) : https://eduscol.education.fr/",
         "OpenSCAD User Manual, Transformations (translate) : https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Transformations"]),
    maths_fiche("volume", ["multiplication"], "primaire", [
        {"cmd": "echo $((40 * 24 * 4))", "sortie": "3840"}, {"cmd": "echo $((3840 / 1000))", "sortie": "3"}],
        ["Programme de mathématiques du cycle 3 (volume d'un pavé droit) : https://eduscol.education.fr/",
         "BIPM, Le Système international d'unités, 9e édition (2019) : le mètre cube et ses sous-multiples"]),
])

ETAPES = {"gu3.5": {"maths": ["hexadecimal"]}, "gu5.2": {"maths": ["coordonnees"]}, "gu5.3": {"maths": ["volume"]},
          "gu6.3": {"maths": ["hexadecimal"]}}


def rejeu():
    K = _fr()
    sys_path = str(D / "pc")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    im = donnees_guilde()["image"]
    tete = im["entete"].encode("ascii")
    out = bytearray(tete)
    k = 0
    while len(out) < im["octets"]:
        out += hashlib.sha256(f"guilde-image:{k}".encode()).digest()
        k += 1
    sha = hashlib.sha256(bytes(out[:im["octets"]])).hexdigest()
    return {
        "gu0.1": {"contient": ["mur_des_plans.txt", "carnet_de_la_guilde.txt", "petit_projet", "atelier"],
                  "pourquoi": "hist.gu0.1.bravo : un mur de plans, un carnet, un petit projet, un atelier"},
        "gu1.2": {"motif": r"^MIT License$", "pourquoi": "hist.gu1.2.bravo : la licence MIT"},
        "gu2.3": {"motif": r"── tg$", "outil": "tree", "pourquoi": "hist.gu2.3.bravo : pc/tg"},
        "gu2.4": {"motif": r"satiete\.py$", "pourquoi": "hist.gu2.4.bravo : beaucoup de fichiers parlent de faim"},
        "gu2.5": {"motif": r"satiete\.py:\d+:def etat_de\(", "pourquoi": "hist.gu2.5.bravo : le nom du fichier avant les deux-points"},
        "gu3.3": {"sortie": K["gu.bonjour.message"], "outil": "gcc", "pourquoi": "hist.gu3.3.bravo : le premier programme parle"},
        "gu3.4": {"motif": "ELF", "outil": "file", "pourquoi": "hist.gu3.4.bravo : ELF"},
        "gu3.5": {"sortie": " 7f 45 4c 46", "outil": "gcc", "pourquoi": "hist.gu3.5.bravo : 7f 45 4c 46"},
        "gu3.6": {"motif": "libc", "outil": "ldd", "pourquoi": "hist.gu3.6.bravo : libc"},
        "gu3.7": {"motif": r"^\*\*\*\*\*$", "outil": "make", "pourquoi": "hist.gu3.7.bravo : make a trouvé la règle"},
        "gu4.1": {"motif": "nothing to commit", "outil": "git", "pourquoi": "hist.gu4.1.bravo : rien à signaler"},
        "gu4.5": {"motif": r"^@@", "outil": "git", "pourquoi": "hist.gu4.5.bravo : - l'ancienne ligne, + la nouvelle"},
        "gu4.7": {"lignes": 2, "outil": "git", "pourquoi": "hist.gu4.7.bravo : deux versions"},
        "gu5.6": {"motif": r"^solid", "pourquoi": "hist.gu5.6.bravo : solid, facet, vertex"},
        "gu6.3": {"sortie": f"{sha}  image_linux_exemple.iso", "pourquoi": "hist.gu6.3.bravo : 64 caractères"},
        "gu6.4": {"sortie": "image_linux_exemple.iso: OK", "pourquoi": "hist.gu6.4.bravo : OK"},
        "gu6.8": {"sortie": f"{sha}  image_linux_exemple.iso\n{sha}  cle_usb.img",
                  "pourquoi": "hist.gu6.8.bravo : deux empreintes identiques"},
    }


def main():
    G = donnees_guilde()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/guilde.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/guilde.json", "app/src/main/assets/guilde.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    mondes = [m for m in P["mondes"] if m["id"] != "guilde"]
    i = next((k for k, m in enumerate(mondes) if m["id"] == "ondes"), len(mondes) - 1) + 1
    mondes.insert(i, GUILDE)
    P["mondes"] = mondes
    for cle in ("etapes", "rejeu"):                   # les étapes de la Guilde : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("gu") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Guilde, {len(MATHS)} ponts des nombres, {len(R)} étapes rejouées ; guilde.json écrit")


if __name__ == "__main__":
    main()
