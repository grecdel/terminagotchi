"""Fabrique toutes les animations d'Abyssor, pour ses 4 stades, aux formats du jeu.

    python3 donnees/animation/exporter.py

  pc/tg/anim/abyssor.json                         terminal : 48×48 px, palette par stade
  app/src/main/assets/anim/abyssor/…              appli : bandes d'images WebP (160 px par image)
  site/public/anim/abyssor/…                      site : les mêmes bandes
Le shiny n'est pas pré-calculé : chaque appareil décale les couleurs (teinte tirée au hasard par individu).
"""
import base64
import json
import os
import pickle
import zlib
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))

from PIL import Image  # noqa: E402

import animer as A  # noqa: E402
import lignee as G  # noqa: E402

A.FOND = (0, 0, 0, 0)            # images transparentes
NB = 12                          # images par animation
NB_EVO = 24
TERM = 48
GRAND = 128

# ---------------------------------------------------------------- les 4 stades
#   calques, agrandissement de la tête, taille des ailes, taille finale de la bestiole
COU = A.PIV["tete"]


def jeu_stade(base, tete, ailes):
    out = dict(base)
    if tete != 1:
        out["tete"] = A.mise_echelle(base["tete"], COU, tete)
    for k in ("aile_g", "aile_d"):
        if ailes != 1:
            out[k] = A.mise_echelle(base[k], A.PIV[k], ailes)
    return out


STADES = {
    "enfant": {"calques": jeu_stade(G.B, 1.35, 0.42), "taille": 0.6},
    "ado": {"calques": jeu_stade(G.J, 1.12, 0.66), "taille": 0.8},
    "adulte": {"calques": A.L, "taille": 1.0},
    "finale": {"calques": G.E, "taille": 1.0, "aura": True},
}
ORDRE = ["enfant", "ado", "adulte", "finale"]

_compo = A.compo
COURANT = {"stade": "adulte", "t": 0.0}


def compo_stade(p, effets=None, fond=A.FOND, assombrir=1.0):
    """Toutes les animations passent par ici : on y branche les calques du stade courant."""
    s = STADES[COURANT["stade"]]
    p = dict(p)
    p.setdefault("calques", s["calques"])
    if s.get("aura"):
        t = COURANT["t"]
        post = p.get("post")
        p["post"] = (lambda c, post=post: A.aura(post(c) if post else c, t))
        eff = effets
        effets = (lambda c, eff=eff: (eff(c) if eff else None, G.flamme_queue(c, t)))
    return _compo(p, effets, A.FOND, assombrir)


A.compo = compo_stade

ANIMS = {
    "statique": A.statique, "mange": A.mange, "attaque": A.attaque, "salut": A.salut, "parle": A.parle,
    "dort": A.dort, "content": A.content, "affame": A.affame, "confus": A.confus, "colere": A.colere,
    "victoire": A.victoire, "ko": A.ko,
}


def taille_finale(img, f):
    """Rend la bestiole plus petite (enfant, ado) en gardant les pieds au même endroit."""
    if f == 1:
        return img
    p = img.resize((int(img.width * f), int(img.height * f)), Image.LANCZOS)
    out = Image.new("RGBA", img.size)
    out.alpha_composite(p, ((img.width - p.width) // 2, img.height - p.height - int(A.PAD * 0.5 * (1 - f))))
    return out


def rendre(stade, fn, n):
    COURANT["stade"] = stade
    images = []
    for i in range(n):
        COURANT["t"] = i / n
        images.append(taille_finale(fn(i / n), STADES[stade]["taille"]))
    return images


def evolution(de, vers):
    """Flash blanc de plus en plus rapide, puis la nouvelle forme apparaît dans une explosion de lumière."""
    images = []
    for i in range(NB_EVO):
        t = i / NB_EVO
        if t < 0.55:
            COURANT["stade"], COURANT["t"] = de, t
            f = (math.sin(t ** 2 * 70) * 0.5 + 0.5) * min(1, t / 0.35)
            im = A.compo({"post": lambda c, f=f: A.teinte(c, (255, 255, 255), f), "secousse": (math.sin(t * 90) * 4 * min(1, t / 0.4), 0)})
            im = taille_finale(im, STADES[de]["taille"])
        else:
            u = (t - 0.55) / 0.45
            COURANT["stade"], COURANT["t"] = vers, t
            f = max(0, 1 - u * 2.2)

            def eclat(c, u=u):
                if u < 0.5:
                    from PIL import ImageDraw
                    d = ImageDraw.Draw(c)
                    cx, cy = c.width / 2, c.height * 0.5
                    for k in range(28):
                        a = k / 28 * 2 * math.pi
                        r = 60 + u * 900
                        d.ellipse([cx + math.cos(a) * r - 7, cy + math.sin(a) * r - 7, cx + math.cos(a) * r + 7, cy + math.sin(a) * r + 7],
                                  fill=(255, 240, 200, int(255 * (1 - u * 2))))
            im = A.compo({"post": lambda c, f=f: A.teinte(c, (255, 255, 255), f)}, eclat)
            im = taille_finale(im, STADES[vers]["taille"])
        images.append(im)
    return images


# ---------------------------------------------------------------- export
def cadre_commun(toutes):
    boites = [im.getbbox() for im in toutes if im.getbbox()]
    x0 = min(b[0] for b in boites); y0 = min(b[1] for b in boites)
    x1 = max(b[2] for b in boites); y1 = max(b[3] for b in boites)
    c = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (int(cx - c / 2), int(cy - c / 2), int(cx + c / 2), int(cy + c / 2))


def terminal(images, palette_imgs=None):
    """Images 48×48 en indices de palette (0 = transparent), palette commune à l'animation."""
    petites = [im.resize((TERM, TERM), Image.LANCZOS) for im in images]
    bande = Image.new("RGBA", (TERM * len(petites), TERM))
    for i, p in enumerate(petites):
        bande.paste(p, (i * TERM, 0))
    alpha = bande.getchannel("A").point(lambda v: 255 if v > 200 else 0)   # l'aura lumineuse ne compte pas
    q = bande.convert("RGB").quantize(63, method=Image.MEDIANCUT)
    pal = q.getpalette()[:63 * 3]
    octets = bytearray()
    for y in range(TERM):
        pass
    frames = []
    for i in range(len(petites)):
        b = bytearray()
        for y in range(TERM):
            for x in range(TERM):
                X = i * TERM + x
                b.append(q.getpixel((X, y)) + 1 if alpha.getpixel((X, y)) else 0)
        frames.append(base64.b64encode(zlib.compress(bytes(b), 9)).decode())
    couleurs = ["#%02x%02x%02x" % tuple(pal[3 * k:3 * k + 3]) for k in range(63)]
    return {"palette": couleurs, "images": frames}


def bande_webp(images, chemin):
    bande = Image.new("RGBA", (GRAND * len(images), GRAND))
    for i, im in enumerate(images):
        bande.alpha_composite(im.resize((GRAND, GRAND), Image.LANCZOS), (i * GRAND, 0))
    chemin.parent.mkdir(parents=True, exist_ok=True)
    bande.save(chemin, "WEBP", quality=88, alpha_quality=90, method=6)
    return chemin.stat().st_size


def main():
    cache = os.environ.get("CACHE_ANIM")
    if cache and os.path.exists(cache):
        rendus = pickle.load(open(cache, "rb"))
        return exporter(rendus)
    rendus = {}
    for s in ORDRE:
        for nom, fn in ANIMS.items():
            rendus[(s, nom)] = rendre(s, fn, NB)
            print(f"  {s:7} {nom}")
    for de, vers in zip(ORDRE, ORDRE[1:]):
        rendus[(de, "evolution")] = evolution(de, vers)
        print(f"  {de:7} evolution → {vers}")
    if cache:
        pickle.dump(rendus, open(cache, "wb"))
    exporter(rendus)


def exporter(rendus):
    bruts = rendus
    cadre = cadre_commun([im for v in rendus.values() for im in v])
    rendus = {k: [im.crop(cadre) for im in v] for k, v in rendus.items()}
    # terminal : chaque stade est cadré sur lui-même (un enfant tout petit serait illisible en 48 px)
    cadres = {s: cadre_commun([im for (s2, _), v in bruts.items() if s2 == s for im in v]) for s in ORDRE}

    pc = {"espece": "Abyssor", "taille": TERM, "ips": 8, "format": "zlib", "stades": ORDRE, "anims": {}}
    poids = 0
    for (s, nom), imgs in rendus.items():
        pc["anims"].setdefault(s, {})[nom] = terminal([im.crop(cadres[s]) for im in bruts[(s, nom)]])
        for dossier in (RACINE / "app/src/main/assets/anim/abyssor", RACINE / "site/public/anim/abyssor"):
            poids += bande_webp(imgs, dossier / s / f"{nom}.webp")
    index = {"espece": "Abyssor", "taille": GRAND, "ips": 10, "stades": ORDRE,
             "anims": {s: {nom: len(v) for (s2, nom), v in rendus.items() if s2 == s} for s in ORDRE},
             "evolution_vers": dict(zip(ORDRE, ORDRE[1:]))}
    for dossier in (RACINE / "app/src/main/assets/anim/abyssor", RACINE / "site/public/anim/abyssor"):
        (dossier / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    pc["evolution_vers"] = index["evolution_vers"]
    (RACINE / "pc/tg/anim").mkdir(parents=True, exist_ok=True)
    (RACINE / "pc/tg/anim/abyssor.json").write_text(json.dumps(pc, separators=(",", ":")), encoding="utf-8")
    print(f"PC : {(RACINE / 'pc/tg/anim/abyssor.json').stat().st_size // 1024} Ko · bandes WebP : {poids // 2048} Ko par plateforme")


if __name__ == "__main__":
    main()
