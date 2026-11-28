"""Test de la vie dans la créature (pc/tg/vie.py) et du décor des auras (pc/tg/aura.py) :
  1. Python et Kotlin donnent les mêmes images : vecteurs de donnees/vie/vecteurs.json (des images du bestiaire
     recopiées dedans, pour ne pas dépendre de sprites.bin), relus aussi par tests/jvm/Vie.kt ;
  2. sur TOUT le bestiaire (150 espèces × 5 stades × variantes) : aucune image vide ou cassée ;
  3. le rendu fin (rendu_fin.py) et l'éclat de l'aura selon le soin.

    python3 pc/outils/test_vie.py            (vérifie)
    python3 pc/outils/test_vie.py --ecrire   (refait les vecteurs depuis le bestiaire actuel)
"""
import base64
import json
import os
import re
import sys
import tempfile
import time
import zlib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ.setdefault("HOME", tempfile.mkdtemp(prefix="tg_vie_"))

from tg import anim_auto, aura as A, bestiaire as B, rendu_fin, vie  # noqa: E402

VECTEURS = RACINE / "donnees" / "vie" / "vecteurs.json"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
    print(("  ✔ " if c else "  ✖ ") + m)


def fnv(b):
    """Empreinte FNV-1a 32 bits (la même en Kotlin)."""
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def empreinte_decor(pts):
    return fnv("".join(f"{x},{y},{c},{a},{1 if d else 0};" for x, y, c, a, d in pts).encode())


CHOIX = [("ectoplouf", "bebe"), ("brumaleine", "bebe"), ("poulpiot", "ancien"), ("chaosmere", "adulte"),
         ("papillombre", "adulte"), ("lampiotte", "ado"), ("tentaclou", "bebe"), ("pyrodrac", "adulte"),
         ("flamouche", "adulte"), ("noctilune", "enfant"), ("groinfer", "bebe"), ("braisillon", "bebe"),
         ("hibourreau", "bebe"), ("seraphibou", "ado"), ("calmaree", "enfant"), ("tellurion", "ancien")]
PALIERS = ["peu commune", "rare", "épique", "légendaire", "mythique", "shiny"]
PHASES = [0, 3, 7, 13, 21, 30]


def calculer(sp):
    w, h, o, pal = sp["w"], sp["h"], sp["o"], sp["pal"]
    a = vie.analyser(w, h, o, pal)
    r = {"analyse": None if a is None else {"yeux": [[list(p) for p in e.px] for e in a.yeux],
                                          "fins": len(a.fins), "souffle": None if a.souffle is None else list(a.souffle)}}
    r["vie"] = [] if a is None else [fnv(vie.image(a, t)[2]) for t in range(vie.CYCLE)]
    r["fine4"] = [] if a is None else [fnv(vie.image_fine(a, t, 4)[2]) for t in range(0, vie.CYCLE, 3)]
    r["fine3"] = [] if a is None else [fnv(vie.image_fine(a, t, 3)[2]) for t in range(0, 20, 2)]
    r["texte"] = [] if a is None else [fnv(",".join(str(c) for c in vie.couleurs_texte(a, pal, t)).encode())
                                       for t in range(0, 16, 2)]
    W, H, fr, _, _ = anim_auto._calculer(w, h, o, pal, "statique")
    r["statique"] = [W, H, len(fr), fnv(b"".join(fr))]
    W, H, fr, _, _ = anim_auto._calculer(w, h, o, pal, "content")
    r["content"] = [W, H, len(fr), fnv(b"".join(fr))]
    plein = [v != 0 for v in o]
    r["decor"] = {nom: [empreinte_decor(A.decor(w, h, plein, nom, ph, ec)) for ph in PHASES for ec in range(4)]
                  for nom in PALIERS}
    r["reflet"] = {nom: [A.reflet(nom, ph, w + 6, h + 6) for ph in PHASES] for nom in PALIERS}
    return r


def ecrire():
    out = {"sprites": [], "soin": []}
    for nom, st in CHOIX:
        e = B.espece(nom)
        w, h, o, pal = B.image(e, st)
        sp = {"nom": f"{nom}/{st}", "w": w, "h": h, "o": list(o[:w * h]), "pal": [int(c[1:], 16) for c in pal]}
        res = calculer(sp)
        sp["o"] = base64.b64encode(zlib.compress(bytes(sp["o"]), 9)).decode()
        sp["attendu"] = res
        out["sprites"].append(sp)
    out["soin"] = [[f, m, A.niveau_soin(f, m)] for f in (0, 10, 14, 15, 29, 30, 50, 69, 70, 85, 100)
                   for m in (0, 30, 60, 90, 100)]
    VECTEURS.parent.mkdir(parents=True, exist_ok=True)
    VECTEURS.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f" {len(out['sprites'])} images → {VECTEURS}")


def main():
    if "--ecrire" in sys.argv:
        ecrire()
        return
    print("1. Les vecteurs partagés avec Kotlin (donnees/vie/vecteurs.json)")
    v = json.loads(VECTEURS.read_text(encoding="utf-8"))
    for sp in v["sprites"]:
        sp = dict(sp, o=list(zlib.decompress(base64.b64decode(sp["o"]))))
        res = calculer(sp)
        verifier(res == sp["attendu"], f"{sp['nom']} : mêmes yeux, mêmes images de vie, même décor d'aura")
    verifier(all(A.niveau_soin(f, m) == n for f, m, n in v["soin"]), "l'éclat selon le soin : mêmes paliers")
    yeux = sum(1 for sp in v["sprites"] if sp["attendu"]["analyse"] and sp["attendu"]["analyse"]["yeux"])
    fins = sum(1 for sp in v["sprites"] if sp["attendu"]["analyse"] and sp["attendu"]["analyse"]["fins"])
    verifier(yeux >= 8 and fins >= 8, f"les vecteurs couvrent des yeux ({yeux}) et des parties fines ({fins})")

    print("2. Tout le bestiaire : jamais d'image vide ou cassée")
    t0 = time.time()
    n = vivants = avec_yeux = 0
    casses = []
    saut_fin, fine_casse = [], []
    for e in B.especes():
        for var in e.get("variantes") or [{"id": "classique"}]:
            for st in B.STADES:
                img = B.image(e, st, var["id"])
                if not img:
                    continue
                w, h, o, pal = img
                n += 1
                a = vie.analyser(w, h, o, [int(c[1:], 16) for c in pal])
                if a is None:
                    continue
                vivants += 1
                avec_yeux += bool(a.yeux)
                for F in (3, 4):
                    avant = vie.decalages(a, 0, F)
                    for t in range(1, 17):
                        apres = vie.decalages(a, t, F)
                        if any(abs(x - y) > 1 for x, y in zip(avant[0], apres[0])) or \
                                any(abs(x - y) > 1 for x, y in zip(avant[1], apres[1])):
                            saut_fin.append(f"{e['id']}/{var['id']}/{st} ×{F} @{t}")
                            break
                        avant = apres
                if var["id"] == "classique":
                    WF, HF, fi = vie.image_fine(a, 8, 4)
                    k = sum(1 for x in fi if x)
                    if k * 100 < sum(1 for x in o[:w * h] if x) * 16 * 85 or len(fi) != WF * HF:
                        fine_casse.append(f"{e['id']}/{st}")
                n0 = sum(1 for x in o[:w * h] if x)
                for t in range(vie.CYCLE):
                    W2, H2, im = vie.image(a, t)
                    k = sum(1 for x in im if x)
                    if W2 != w + 2 * vie.PAD or H2 != h + vie.PAD or len(im) != W2 * H2 or k == 0 \
                            or k * 100 < n0 * 88 or max(im) > len(pal):
                        casses.append(f"{e['id']}/{var['id']}/{st}@{t}")
                        break
    verifier(n > 3000, f"{n} images du bestiaire passées en revue ({time.time() - t0:.0f} s)")
    verifier(not saut_fin, "à chaque image, aucune ligne et aucun pixel d'appendice ne bouge de plus d'UN pixel de "
                           "l'image finale (×3 et ×4)" + (f" : {saut_fin[:5]}" if saut_fin else ""))
    verifier(not fine_casse, "image fine (×4, au plus fort du souffle) : jamais vide ni tronquée"
             + (f" : {fine_casse[:5]}" if fine_casse else ""))
    verifier(not casses, "aucune image de vie vide, tronquée ou hors palette" + (f" : {casses[:5]}" if casses else ""))
    verifier(vivants * 100 >= n * 90, f"la vie anime {vivants} images sur {n} (sinon : l'animation d'avant)")
    verifier(avec_yeux * 100 >= n * 25, f"des yeux trouvés sur {avec_yeux} images")
    e = B.espece("ectoplouf")
    W, H, fr, _ = anim_auto.toiles(e, "bebe", "classique", "statique")
    W2_, H2_, fr2, _ = anim_auto.toiles(B.espece("chaosmere"), "adulte", "classique", "statique")
    verifier(len(fr) == vie.CYCLE and len(set(fr)) >= 3 and len(set(fr2)) >= 3,
             f"au pixel du sprite (listes) : 64 images, les yeux clignent ({len(set(fr))} et {len(set(fr2))} images "
             "différentes) ; respiration et ondulations seulement au pixel fin")
    a2 = vie.analyser(*B.image(B.espece("chaosmere"), "adulte")[:3],
                      [int(c[1:], 16) for c in B.image(B.espece("chaosmere"), "adulte")[3]])
    sommet = max(max(vie.decalages(a2, t, 4)[0]) for t in range(16))
    verifier(4 <= sommet <= 6, f"un adulte respire de {sommet} pixels fins au sommet (×4 : environ 1,25 pixel du sprite)")
    a3 = vie.analyser(*B.image(e, "bebe")[:3], [int(c[1:], 16) for c in B.image(e, "bebe")[3]])
    sommet = max(max(vie.decalages(a3, t, 4)[0]) for t in range(16))
    verifier(2 <= sommet <= 3, f"un bébé respire de {sommet} pixels fins au sommet")
    fines = [vie.image_fine(a2, t, 4)[2] for t in range(16)]
    verifier(len(set(fines)) >= 12, f"au pixel fin, la respiration change presque à chaque image ({len(set(fines))} sur 16)")
    tx = [vie.couleurs_texte(a3, [int(c[1:], 16) for c in B.image(e, "bebe")[3]], t) for t in range(16)]
    verifier(len(set(map(tuple, tx))) > 4 and all([c is None for c in x] == [c is None for c in tx[0]] for x in tx),
             "en texte : la lumière glisse (fondu de couleurs) mais la silhouette ne saute jamais")
    vieux = anim_auto._calculer(4, 4, bytes([1] * 16), [0x808080], "statique")
    verifier(len(vieux[2]) == 8, "une image trop petite garde l'animation d'avant (8 images)")
    a = vie.analyser(*B.image(e, "bebe")[:3], [int(c[1:], 16) for c in B.image(e, "bebe")[3]])
    prog = [vie.programme(a, t) for t in range(vie.CYCLE)]
    fermes = [t for t, p in enumerate(prog) if p[0] == 2]
    blocs = [sorted(t % vie.BLOC for t in fermes if t // vie.BLOC == b) for b in range(vie.CYCLE // vie.BLOC)]
    verifier(fermes and blocs[0] != blocs[1], "les clignements ne tombent pas au même moment d'un bloc à l'autre "
                                              f"(rythme irrégulier : {blocs})")
    verifier(any(p[1] for p in prog) and any(p[2] >= 90 for p in prog) and any(p[2] == 0 for p in prog), "petits regards et respiration au programme")

    print("3. Auras : décor, reflet, éclat selon le soin")
    plein = [True] * 100
    for nom in PALIERS:
        veille = sum(len(A.decor(10, 10, plein, nom, ph, 0)) for ph in range(32))
        repue = sum(len(A.decor(10, 10, plein, nom, ph, 3)) for ph in range(32))
        verifier(veille == 0 and repue > 0, f"{nom} : en veille, pas de particules ; rassasiée, elles montent")
    tous = [len(A.decor(10, 10, plein, "légendaire", ph, 3)) for ph in range(32)]
    verifier(sum(tous) > 0, "des particules montent autour d'une légendaire bien soignée")
    verifier(A.reflet("légendaire", 5, 20, 20) is not None and A.reflet("rare", 5, 20, 20) is None,
             "le reflet passe seulement sur les plus rares")
    etoiles = [p for ph in range(8) for p in A.decor(10, 10, plein, "shiny", ph, 2) if p[4]]
    verifier(etoiles and not any(p[4] for ph in range(8) for p in A.decor(10, 10, plein, "mythique", ph, 2)),
             "les étincelles : seulement pour les shiny")
    fort = sum(v[3] for v in A.calque(10, 10, plein, "rare", 4, 3)[3] if v)
    pale = sum(v[3] for v in A.calque(10, 10, plein, "rare", 4, 0)[3] if v)
    verifier(fort > pale * 2, "rassasiée : l'aura brille ; en veille : elle pâlit")
    verifier(A.eclat({"hunger": 95, "envies": {"v": {"jeu": 90, "curiosite": 90, "explorer": 90, "sommeil": 90}}}) == 3
             and A.eclat({"hunger": 5}) == 0 and A.eclat({"hunger": 50}) == 2 and A.eclat({}) == 3,
             "aura.eclat lit la faim et les envies de la partie")

    print("4. Le rendu fin dans le terminal")
    cs = [None if not x else "#88cc44" for x in B.image(e, "bebe")[2]]
    w, h = B.image(e, "bebe")[:2]
    sans_ansi = re.compile(r"\x1b\[[0-9;]*m")
    for mode in ("demi", "quadrants", "kitty", "iterm", "sixel"):
        ls, larg = rendu_fin.lignes(w, h, cs, "rare", 3, 2, mode)
        verifier(ls and larg > 0 and all(len(sans_ansi.sub("", l.split("\x1b7")[0])) == larg for l in ls),
                 f"{mode} : {len(ls)} lignes de {larg} colonnes, bien alignées")
    ls, _ = rendu_fin.lignes(w, h, cs, "rare", 3, 2, "kitty")
    verifier("\x1b_G" in ls[-1] and "a=T" in ls[-1] and "i=4243" in ls[-1], "kitty : une vraie image (numéro 4243)")
    os.environ.pop("TG_IMAGES", None)
    verifier(rendu_fin.mode() == "demi", "hors d'un vrai terminal : les demi-blocs d'avant")
    os.environ["TG_IMAGES"] = "sextants"
    verifier(rendu_fin.mode() == "quadrants", "TG_IMAGES=sextants : les créatures en quadrants (pixels justes)")
    os.environ.pop("TG_IMAGES")
    r = anim_auto.lignes(e, "bebe", "classique", "statique", None, "rare", fin=True)
    verifier(r and len(r[0]) == vie.CYCLE, "tg anime / écran principal : 64 images de vie avec aura")

    print(f"\n{ok} réussis, {ko} échoués")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
