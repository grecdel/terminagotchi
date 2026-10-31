"""Vecteurs communs Python / Kotlin / JavaScript de l'effet glitch (pc/tg/glitch.py, Glitch.kt, site/src/glitch.js).

    python3 pc/outils/vecteurs_glitch.py             réécrit donnees/glitch/vecteurs.json
    python3 pc/outils/vecteurs_glitch.py --verifier  code de sortie 1 s'il n'est plus à jour

Chaque cas : une image (pixels ARGB en hexadécimal), une graine, un style, une phase, une taille de pixel s ; attendu :
l'empreinte sha256 des pixels obtenus (« %08x » de chaque pixel, à la suite). Plus l'horloge des éclairs (etat).
"""
import hashlib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import bestiaire as B  # noqa: E402
from tg import glitch as G  # noqa: E402

SORTIE = RACINE / "donnees/glitch/vecteurs.json"


def empreinte(px):
    return hashlib.sha256("".join("%08x" % (p & 0xFFFFFFFF) for p in px).encode()).hexdigest()


def image(nom, stade, shiny=False):
    e = B.espece(nom)
    w, h, o, pal = B.image(e, stade)
    if shiny:
        pal = [B.decaler(c, 0.5) for c in pal]
    return w, h, [0 if not k else 0xFF000000 | int(pal[k - 1][1:], 16) for k in o[:w * h]]


def agrandir(w, h, px, s):
    return w * s, h * s, [px[(y // s) * w + x // s] for y in range(h * s) for x in range(w * s)]


def vecteurs():
    imgs = [("carre", 9, 7, [0xFF000000 | (0x10 * x) << 16 | (0x20 * y) << 8 | 0x80 if 2 <= x <= 6 and 1 <= y <= 5 else 0
                             for y in range(7) for x in range(9)])]
    for nom, stade in (("ricanombre", "bebe"), ("cranard", "enfant"), ("ombrachne", "adulte")):
        w, h, px = image(nom, stade)
        imgs.append((f"{nom}/{stade}", w, h, px))
    cas = []
    for nom, w, h, px in imgs:
        for s in (1, 3) if nom in ("carre", "ricanombre/bebe") else (1,):
            W, H, P = agrandir(w, h, px, s)
            for graine in ("a1b2c3d4e5", "Crânard:1761955200000"):
                for style, phase in (("A", 0), ("C", 0), ("C", 3), ("C", 7)):
                    cas.append({"image": nom, "s": s, "graine": graine, "style": style, "phase": phase,
                                "empreinte": empreinte(G.appliquer(W, H, P, graine, style, phase, s))})
    exemple = G.appliquer(9, 7, imgs[0][3], "a1b2c3d4e5", "C", 1)
    eclairs = [{"graine": g, "t": t, "etat": list(G.etat(g, t))} for g in ("a1b2c3d4e5", "ff00", "Crânard:17")
               for t in list(range(0, 12000, 130)) + [1761955200123, 2 ** 41 + 77]]
    return {"note": "Généré par pc/outils/vecteurs_glitch.py ; spécification dans pc/tg/glitch.py",
            "images": {nom: {"w": w, "h": h, "px": ["%08x" % p for p in px]} for nom, w, h, px in imgs},
            "cas": cas, "exemple": {"image": "carre", "graine": "a1b2c3d4e5", "style": "C", "phase": 1,
                                    "px": ["%08x" % p for p in exemple]},
            "fnv": [{"texte": x, "h": str(G.fnv(x))} for x in ("", "a", "Crânard:A:0", "glitch ▚")],
            "eclairs": eclairs}


def main():
    txt = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        ok = SORTIE.exists() and SORTIE.read_text(encoding="utf-8") == txt
        print(("✔ " if ok else "✖ ") + str(SORTIE.relative_to(RACINE)) + (" à jour" if ok else " n'est plus à jour"))
        sys.exit(0 if ok else 1)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(txt, encoding="utf-8")
    print(f"écrit {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
