"""Les vecteurs communs de la Guilde des Bâtisseurs Libres (Python ↔ Kotlin) : donnees/guilde/vecteurs.json.

    python3 pc/outils/vecteurs_guilde.py              écrit les vecteurs (depuis pc/tg/guilde.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_guilde.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les situations des 4 libertés et « libre ou gratuit » mélangées pour chaque partie (et la correction des réponses),
les licences reconnues dans un texte et le catalogue, le fichier où la créature décide qu'elle a faim et la réponse de
l'enfant, la faute volontaire de la contribution (texte faux, texte juste, correction acceptée ou non), les mesures du
porte-clé, son trou et son volume, le STL fait par le jeu et ce qu'on lit d'un STL (texte ou binaire), la fausse image
(empreinte), le lsblk fictif et le bon disque, l'établi (vue déployée) : tests/jvm/Guilde.kt vérifie que l'appli
Android donne EXACTEMENT les mêmes résultats.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, guilde as G  # noqa: E402

FICHIER = RACINE / "donnees" / "guilde" / "vecteurs.json"


def stl_binaire(tris):
    b = bytearray(b"binaire de test".ljust(80, b" "))
    b += struct.pack("<I", len(tris))
    for tri in tris:
        b += struct.pack("<12fH", 0, 0, 1, *[c for v in tri for c in v], 0)
    return bytes(b)


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123", "5:5", "8:1762000000"]
    parties = []
    for g in graines:
        p = G.piece(g)
        parties.append({"graine": g, "libertes": [[n, i, r] for n, i, r in G.libertes_cartes(g)],
                        "gratuit": [[n, i, r] for n, i, r in G.gratuit_cartes(g)], "faute": G.faute(g),
                        "texte_faux": G.texte_contribution(g), "texte_juste": G.texte_contribution(g, juste=True),
                        "piece": p, "volume": G.volume(g), "disques": G.disques(g), "cle": list(G.cle_disque(g))})
    quiz = []
    for g in graines[:3]:
        c = G.libertes_cartes(g)
        bon = [r for _n, _i, r in c]
        for rep in (bon, list(reversed(bon)), ["0", "1"], ["a", "b", "c", "d"], bon[:3] + ["9"], []):
            ok, justes = G.quiz_justes(c, rep, "0123")
            quiz.append({"graine": g, "lettres": "0123", "rep": rep, "ok": ok, "justes": [[n, i] for n, i in justes]})
        c = G.gratuit_cartes(g)
        bon = [r for _n, _i, r in c]
        for rep in (bon, ["L"] * 4, ["libre", "pas", "pas", "libre"], ["x"] * 4):
            ok, justes = G.quiz_justes(c, rep, "lp")
            quiz.append({"graine": g, "lettres": "lp", "rep": rep, "ok": ok, "justes": [[n, i] for n, i in justes]})
    textes = ["MIT License\n\nPermission is hereby granted, free of charge", "GNU GENERAL PUBLIC LICENSE\nVersion 3",
              "GNU LESSER GENERAL PUBLIC LICENSE", "License: GPL-3+", "License: LGPL-2.1+ and GPL-2+", "Apache License 2.0",
              "Mozilla Public License Version 2.0", "Redistribution and use in source and binary forms", "BSD-3-Clause",
              "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2", "The author disclaims copyright. public domain",
              "Creative Commons Attribution 4.0", "CC0 1.0", "zlib License", "GNU AFFERO GENERAL PUBLIC LICENSE",
              "submit your work", "rien du tout", "", "Licensed under the AGPL-3.0", "MPL-2.0"]
    licences = [{"texte": x, "famille": G.licence_de_texte(x)} for x in textes]
    noms = ["bash", "Firefox", "PYTHON3", "terminagotchi", "gimp", "openssl", "sqlite", "  git ", "inconnu", "Blender"]
    catalogue = [{"nom": n, "famille": G.licence_catalogue(n), "genre": G.genre_licence(G.licence_catalogue(n))} for n in noms]
    fichiers = [{"pc/tg/satiete.py": "x = 1\ndef etat_de(faim, veille=False):\n    pass\n", "pc/tg/aura.py": "faim < AFFAMEE\n"},
                {"pc/tg/core.py": "rate = 360   # secondes par point de faim\n", "pc/tg/app.py": "faim"},
                {"a.py": "rien"}, {}]
    faim = [{"fichiers": f, "attendus": G.faim_fichiers(f)} for f in fichiers]
    reps = ["satiete", "satiete.py", "pc/tg/satiete.py", "Satiété", "SATIETE.PY", "aura.py", "", "satiete.py:98",
            "code_du_jeu/pc/tg/satiete.py", "core", "Satiete.kt"]
    faim_rep = [{"reponse": r, "attendus": a, "ok": G.faim_ok(r, a)} for r in reps for a in (["satiete.py"], ["core.py"])]
    corrections = []
    for g in graines[:4]:
        j = G.texte_contribution(g, juste=True)
        for t_ in (j, j.rstrip("\n"), j + "\n\n", G.texte_contribution(g), j.replace("faim", "FAIM"), j.replace("\n", "\r\n"), ""):
            corrections.append({"graine": g, "texte": t_, "ok": G.correction_ok(t_, g)})
    trous = []
    for g in graines[:4]:
        p = G.piece(g)
        for rep in ([str(p["trou_x"]), str(p["trou_y"])], [f"[{p['trou_x']},", f"{p['trou_y']}]"], [str(p["trou_y"]), str(p["trou_x"])],
                    [str(p["trou_x"])], [f"{p['trou_x']}.0", f"{p['trou_y']},0"], ["a", "b"]):
            trous.append({"graine": g, "rep": rep, "ok": G.trou_ok(rep, g)})
    volumes = []
    for g in graines[:4]:
        v = G.volume(g)
        for r in (str(v), f"{v} mm3", f"{v}mm³", f"{v / 1000:g} cm3", f"{v / 1000:g}".replace(".", ",") + " cm³", str(v + 1), "abc", ""):
            volumes.append({"graine": g, "reponse": r, "ok": G.volume_ok(r, g)})
    stl = [{"L": L, "l": l, "h": h, "texte": G.stl_boite(L, l, h), "infos": G.stl_infos(G.stl_boite(L, l, h).encode())}
           for L, l, h in ((40, 24, 4), (36, 16, 3))]
    b = stl_binaire([((0, 0, 0), (10.5, 0, 0), (0, 7.25, 2)), ((1, 1, 1), (3, 3, 3), (2, 2, 2))])
    stl_bin = {"hex": b.hex(), "infos": G.stl_infos(b)}
    stl_mauvais = [{"hex": x.hex(), "infos": G.stl_infos(x)} for x in (b"", b"solid x\nendsolid x\n", b"\0" * 90, b[:100])]
    disques = [{"graine": g, "reponse": r, "ok": G.disque_ok(r, g), "erreur": G.disque_erreur(r, g)}
               for g in graines[:4] for r in ("sda", "sdb", "/dev/sda", "nvme0n1", "nvme0n1p2", "sda1", "sdz", "", "SDA")]
    lignes = ["gcc bonjour.c -o bonjour && ./bonjour", "cc a.c", "make etoiles && ./etoiles 5", "openscad -o p.stl p.scad",
              "dd if=image_linux_exemple.iso of=cle_usb.img bs=64k", "sha256sum a b | sort", "git clone --depth 1 x y",
              "git diff", "git commit -am 'x'", "git status", "ls", "echo gcc", "cp a b", "git log --oneline; git diff --stat",
              "guilde stl"]
    etabli = [{"ligne": l, "etablis": [list(a) for a in G.etablis_de(l)]} for l in lignes]
    dep = [{"ligne": l, "etablis": [{"seg": x["seg"], "cmd": x["cmd"], "outil": x["outil"], "de": x["de"], "vers": x["vers"]}
                                    for x in deploie.etablis(l)]} for l in lignes]
    return {"note": "généré par pc/outils/vecteurs_guilde.py ; vérifié par tests/jvm/Guilde.kt",
            "parties": parties, "quiz": quiz, "licences": licences, "catalogue": catalogue, "faim": faim,
            "faim_reponses": faim_rep, "corrections": corrections, "trous": trous, "volumes": volumes, "stl": stl,
            "stl_binaire": stl_bin, "stl_mauvais": stl_mauvais,
            "image": {"octets": len(G.image_octets()), "sha256": G.image_sha()}, "disques": disques,
            "majmin": {n: G.majmin(n) for n in ("sda", "sda1", "sdb", "sdb1", "nvme0n1", "nvme0n1p1", "nvme0n1p2")},
            "etabli": etabli, "deploie": dep}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/guilde/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_guilde.py")
            sys.exit(1)
        print("vecteurs de la Guilde à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
