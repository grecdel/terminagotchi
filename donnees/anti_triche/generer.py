"""Anti-triche : fabrique les fichiers partagés à partir du bestiaire du jeu (pc/tg/bestiaire.json).

    python3 donnees/anti_triche/generer.py

  site/src/tirage_donnees.js         ce dont le serveur a besoin pour refaire les tirages
  donnees/anti_triche/vecteurs.json  tirages de référence (graines factices), vérifiés par
                                     le Python, le Kotlin et le JavaScript

À relancer après chaque changement du bestiaire (espèces, variantes, raretés, marques, humeurs).
La spécification du tirage est dans pc/tg/tirage.py.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import bestiaire as B  # noqa: E402
from tg import tirage as T  # noqa: E402

# graines FACTICES (aucune ne vient du vrai serveur)
GRAINES = [
    "0" * 64,
    "ffffffffffffffff" + "0" * 48,
    "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95",
    "8000000000000001" + "fac71ce" * 6 + "00",
]


def donnees_site():
    d = B.donnees()
    especes = []
    for e in B.especes():
        if e.get("secrete") and e["id"] != "abyssor":
            continue
        especes.append({
            "id": e["id"], "nom": e["nom"], "famille": e["famille"], "frequence": e["frequence"], "puissance": e.get("puissance", 1),
            "taille_cm": e["taille_cm"], "stats": e["stats"], "secrete": bool(e.get("secrete")),
            "variantes": [{"id": v["id"], "chance": v["chance"], "score": v.get("score", 0), "zone": v.get("zone", e["zone"])}
                          for v in e["variantes"]],
        })
    return {
        "version": T.VERSION, "chance_shiny": d["chance_shiny"], "poids_frequence": d["poids_frequence"],
        "rarete": {k: d["rarete"][k] for k in ("poids", "paliers", "speciales")},
        "marques": d["marques"], "humeurs": d["humeurs"], "stades": B.STADES,
        "poids_stades": T.POIDS_STADES, "max_apparitions": T.MAX_APPARITIONS,
        "attirance": T.ATTIRANCE, "familles": B.familles(), "especes": especes,
        "chance_glitch": T.CHANCE_GLITCH, "chance_glitch_gardien": T.CHANCE_GLITCH_GARDIEN,
        "compteur_glitch": T.COMPTEUR_GLITCH, "gardiens": gardiens_codes(),
    }


def gardiens_codes():
    """{boîte: nom de l'espèce gardienne} des boîtes de la Citadelle déjà codées (citadelle.json « boites ») : le
    serveur n'accepte « gardien » que pour elles (programme.json, monde citadelle, « gardiens »)."""
    prog = json.loads((RACINE / "pc/tg/programme.json").read_text(encoding="utf-8"))
    cit = json.loads((RACINE / "pc/tg/citadelle.json").read_text(encoding="utf-8"))
    codees = [b["id"] for b in cit["boites"]]
    g = {}
    for m in prog["mondes"]:
        for b, eid in m.get("gardiens", {}).items():
            if b in codees:
                g[b] = B.espece(eid)["nom"]
    return g


def vecteurs():
    sorties = []
    for g in GRAINES[:2]:
        h = T.Hasard(g, 0)
        sorties.append({"valeur": g, "n": 0, "sorties": [str(h.suivant()) for _ in range(6)]})
    tirages = []
    for g in GRAINES:
        for n in range(60):
            for ab in (False, True):
                e, c = T.tirer(g, n, ab)
                if ab and e["id"] != "abyssor":
                    continue                      # avec Abyssor permis : seulement les cas où il apparaît
                tirages.append({"valeur": g, "n": n, "abyssor": ab, "attendu": c})
    # avec une famille attirée (champ « attire ») : chaque famille, sur deux graines
    familles = list(B.familles())
    for g in GRAINES[1:3]:
        for n in range(40):
            f = familles[n % len(familles)]
            e, c = T.tirer(g, n, False, f)
            tirages.append({"valeur": g, "n": n, "abyssor": False, "attire": f, "attendu": c})
    # quelques cas rares cherchés exprès (shiny, légendaire)
    g = GRAINES[2]
    trouves = {"shiny": 0, "légendaire": 0}
    for n in range(60, 5000):
        e, c = T.tirer(g, n)
        cle = "shiny" if c["shiny"] else c["rarete"] if c["rarete"] == "légendaire" else None
        if cle and trouves[cle] < 3:
            trouves[cle] += 1
            tirages.append({"valeur": g, "n": n, "abyssor": False, "attendu": c})
    # le glitch (tirage 13, à part) : normal et gardien, sur toutes les graines ; puis des glitchs cherchés exprès
    glitchs = [{"valeur": g, "n": n, "gardien": gd, "glitch": T.glitch(g, n, gd)}
               for g in GRAINES for n in range(0, 200, 7) for gd in (False, True)]
    for g in GRAINES:
        vus = 0
        for n in range(200, 40000):
            if T.glitch(g, n):
                glitchs.append({"valeur": g, "n": n, "gardien": False, "glitch": True})
                vus += 1
                if vus == 2:
                    break
    return {"version": T.VERSION, "note": "graines factices ; spécification dans pc/tg/tirage.py",
            "splitmix": sorties, "tirages": tirages, "glitchs": glitchs}


def main():
    site = RACINE / "site" / "src" / "tirage_donnees.js"
    site.write_text("// Généré par donnees/anti_triche/generer.py — ne pas modifier à la main.\n"
                    "export default " + json.dumps(donnees_site(), ensure_ascii=False, separators=(",", ":")) + ";\n",
                    encoding="utf-8")
    v = vecteurs()
    (Path(__file__).parent / "vecteurs.json").write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{site.relative_to(RACINE)} ({site.stat().st_size // 1024} Ko), vecteurs.json : {len(v['tirages'])} tirages")


if __name__ == "__main__":
    main()
