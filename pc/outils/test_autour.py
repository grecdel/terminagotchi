"""Test de ce qui vit « autour » du jeu (site, papier) — rien ne change dans le jeu lui-même.

    python3 pc/outils/test_autour.py            (depuis la racine du dépôt)
    python3 pc/outils/test_autour.py --site     (recopie les textes intro.* du jeu dans site/src/autour_textes.js)

1. Les textes de la page « Essayer » du site : les clés intro.* sont RECOPIÉES du jeu (pc/tg/langues/xx.json), les clés
   site.* sont propres au site ; 14 langues, mêmes clés partout.
2. Les fichiers à imprimer (site/public/imprimer/) : les 12 coloriages de docs/imprimer/fabriquer/choix.py (PDF +
   aperçu), au moins un par famille ; la planche de stickers ; le poster A3 (sombre et fond blanc) ; la liste du site
   (COLORIAGES dans site/src/worker.js) est la même que celle de choix.py.
3. La page « Essayer » : aucun envoi (pas de fetch, de cookie, de stockage) ; la mascotte du site n'y apparaît pas.
4. La page « Soutenir » n'a plus de partie « Faire un don » (aucune langue) ; CONTRIBUTING.md donne les deux licences.
"""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
LANGUES = ["fr", "en", "es", "de", "it", "pt", "ru", "ja", "zh", "ar", "hi", "bn", "ur", "id"]
JS = RACINE / "site/src/autour_textes.js"
ENTETE = ("// Les textes de la page /essayer et des parties « À imprimer » du site (14 langues). Les clés intro.* sont RECOPIÉES\n"
          "// des fichiers du jeu (pc/tg/langues/xx.json) : pc/outils/test_autour.py vérifie qu'elles sont à jour\n"
          "// (python3 pc/outils/test_autour.py --site les recopie) ; les clés site.* sont propres au site.\n")
ok = ko = 0


def verif(c, msg):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
        print("  ✗", msg)


def lire_js():
    t = JS.read_text(encoding="utf-8")
    return t, json.loads(t[t.index("export default ") + 15:].rstrip().rstrip(";"))


def textes_site(d0):
    out = {}
    for code in LANGUES:
        d = json.loads((RACINE / f"pc/tg/langues/{code}.json").read_text(encoding="utf-8"))
        x = {k: d[k] for k in sorted(d) if k.startswith("intro.")}
        for k, v in sorted((d0.get(code) or {}).items()):
            if k.startswith("site."):
                x[k] = v
        out[code] = x
    return ENTETE + "export default " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"


if "--site" in sys.argv:
    JS.write_text(textes_site(lire_js()[1]), encoding="utf-8")
    print("site/src/autour_textes.js recopié")

print("1. Les textes de la page Essayer")
actuel, T = lire_js()
verif(actuel == textes_site(T), "site/src/autour_textes.js à jour (python3 pc/outils/test_autour.py --site)")
verif(sorted(T) == sorted(LANGUES), "14 langues")
cles = set(T["fr"])
verif(all(set(T[l]) == cles for l in LANGUES), "mêmes clés dans les 14 langues")
verif(all(v.strip() for l in LANGUES for v in T[l].values()), "aucun texte vide")
verif(all(set(re.findall(r"\{(\w+)\}", T[l][k])) <= set(re.findall(r"\{(\w+)\}", T["fr"][k])) for l in LANGUES for k in cles),
      "les trous {…} sont les mêmes qu'en français")
for k in ("intro.camp.dort", "intro.recoit", "intro.merci", "intro.l.pwd", "intro.type.plante", "site.nom_defaut", "site.bravo"):
    verif(k in cles, "clé utilisée par la page : " + k)

print("2. Les fichiers à imprimer")
sys.path.insert(0, str(RACINE / "docs/imprimer/fabriquer"))
from choix import CHOIX  # noqa: E402
B = {e["id"]: e for e in json.loads((RACINE / "donnees/bestiaire2/bestiaire.json").read_text(encoding="utf-8"))}
IMP = RACINE / "site/public/imprimer"
verif(len(CHOIX) == 12, "12 coloriages")
verif({B[i]["famille"] for i, *_ in CHOIX} == {e["famille"] for e in B.values()}, "au moins un coloriage par famille")
for i, stade, _, niveau in CHOIX:
    base = IMP / f"coloriages/coloriage_{B[i]['numero']:03d}_{i}"
    verif(base.with_suffix(".pdf").is_file() and base.with_suffix(".pdf").read_bytes()[:5] == b"%PDF-", f"{i} : PDF")
    verif(base.with_suffix(".png").is_file(), f"{i} : aperçu")
    verif(niveau in ("facile", "moyen", "un peu plus dur"), f"{i} : niveau")
en_trop = {p.stem.split("_", 2)[2] for p in (IMP / "coloriages").glob("*.pdf")} - {i for i, *_ in CHOIX}
verif(not en_trop, "aucun coloriage non validé dans le site" + (f" : {sorted(en_trop)}" if en_trop else ""))
for f in ("stickers_A4", "poster_A3", "poster_A3_fond_blanc"):
    verif((IMP / f"{f}.pdf").is_file() and (IMP / f"{f}.jpg").is_file(), f"{f} : PDF + aperçu")
    verif((IMP / f"{f}.pdf").stat().st_size < 3_000_000, f"{f} : moins de 3 Mo (le site le sert tel quel)")
worker = (RACINE / "site/src/worker.js").read_text(encoding="utf-8")
m = re.search(r"const COLORIAGES = \[([^\]]*)\]", worker)
site = re.findall(r'"([a-z0-9]+)"', m.group(1)) if m else []
verif(site == [i for i, *_ in CHOIX], "worker.js COLORIAGES = choix.py")

print("3. La page Essayer ne garde ni n'envoie rien")
js = (RACINE / "site/public/js/essayer.js").read_text(encoding="utf-8")
code = re.sub(r"//.*", "", js)
for mot in ("fetch(", "XMLHttpRequest", "sendBeacon", "document.cookie", "localStorage", "sessionStorage", "indexedDB", "WebSocket"):
    verif(mot not in code, "essayer.js n'utilise pas " + mot)
verif(not re.search(r"mascotte\w*\.png|icone\.png|favicon", js), "la mascotte du site n'apparaît pas dans la démo")
verif("Math.random" in js, "l'œuf est tiré au hasard")
depart = json.loads((RACINE / "donnees/oeufs/depart.json").read_text(encoding="utf-8"))["depart"]
verif(json.dumps(depart, ensure_ascii=False, separators=(",", ":")) in worker, "les œufs et bébés de la démo = donnees/oeufs/depart.json")
for ty in depart:
    for etat in ("intact", "fissure", "eclosion"):
        verif((RACINE / f"site/public/essayer/oeuf_{ty}_{etat}.png").is_file(), f"image de l'œuf {ty} {etat}")
verif((RACINE / "site/public/essayer/camp.jpg").is_file() and (RACINE / "site/public/essayer/camp_dort.jpg").is_file(), "images du camp")

print("4. Soutenir sans dons ; CONTRIBUTING.md")
pages = (RACINE / "site/src/i18n_pages.js").read_text(encoding="utf-8")
verif("donsTitre" not in pages and "donsTexte" not in pages and "bientot:" not in pages, "plus de partie « Faire un don » (14 langues)")
verif("DONS" not in worker and "liberapay" not in worker.lower() and "ko-fi" not in worker.lower(), "plus de liens de don dans le site")
verif("autresTitre" in pages, "« d'autres manières d'aider » est gardé")
c = (RACINE / "CONTRIBUTING.md").read_text(encoding="utf-8")
verif("GPL" in c and "CC BY-NC-SA" in c, "CONTRIBUTING.md : GPL pour le code, CC BY-NC-SA pour l'art, les textes et les sons")
verif("CONTRIBUTING.md" in (RACINE / "README.md").read_text(encoding="utf-8"), "le README renvoie vers CONTRIBUTING.md")

print(f"\n{ok} vérifications réussies, {ko} échouées")
sys.exit(1 if ko else 0)
