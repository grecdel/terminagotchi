"""Fabrique site/src/bestiaire.js à partir du nouveau bestiaire du jeu (version 2).

    python3 donnees/bestiaire2/generer_site.py

Lancé automatiquement à la fin de generer_jeu.py. Il lit :
  app/src/main/assets/bestiaire.json     les données écrites par generer_jeu.py
  site/public/portraits/<id>/…           les portraits déjà copiés pour le site
et écrit site/src/bestiaire.js : seulement ce dont les pages du site ont besoin (pas les sprites du jeu),
plus la liste des variantes réellement dessinées et la correspondance des anciennes espèces (bestiaire v1),
pour que les vieilles captures restent lisibles.
"""
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
SOURCE = RACINE / "app/src/main/assets/bestiaire.json"
PORTRAITS = RACINE / "site/public/portraits"
SORTIE = RACINE / "site/src/bestiaire.js"

CHAMPS = ("id", "numero", "nom", "famille", "icone", "rarete", "frequence", "puissance", "stat", "description",
          "comportement", "capacite", "habitat", "zone", "attiree_par", "taille_cm", "poids_ko", "stats", "secrete")
# Abyssor (la secrète) n'a pas de portrait : le site garde son petit dessin d'origine
DESSIN = ("sprite", "sprite_shiny", "palette", "palette_shiny")


def dessinees(eid, stades):
    """Les variantes dont les 5 stades existent en portrait sur le site."""
    d = PORTRAITS / eid
    if not d.is_dir():
        return set()
    fichiers = {f.name for f in d.iterdir()}
    variantes = {f.rsplit("_", 1)[0] for f in fichiers if f.endswith(".webp")}
    return {v for v in variantes if all(f"{v}_{s}.webp" in fichiers for s in stades)}


def main():
    d = json.loads(SOURCE.read_text(encoding="utf-8"))
    stades = d["stades"]
    poids = d["poids_frequence"]
    publiques = [e for e in d["especes"] if not e.get("secrete")]
    total = sum(poids[e["frequence"]] for e in publiques)
    especes = []
    for e in d["especes"]:
        x = {k: e[k] for k in CHAMPS if k in e}
        faites = dessinees(e["id"], stades)
        x["variantes"] = [{"id": v["id"], "nom": v["nom"], "chance": v["chance"], "zone": v.get("zone", e["zone"]),
                           "dessinee": v["id"] in faites} for v in e["variantes"]]
        x["portrait"] = "classique" in faites
        if not e.get("secrete"):
            # une apparition sur combien (avant le choix de la variante)
            x["un_sur"] = round(total / poids[e["frequence"]])
        if not x["portrait"]:
            x.update({k: e[k] for k in DESSIN if k in e})
        especes.append(x)
    par_numero = {e["numero"]: e["id"] for e in d["especes"]}
    donnees = {
        "version": d["version"], "raretes": d["raretes"], "frequences": list(poids) + ["presque jamais"],
        "familles": d["familles"], "stades": stades, "marques": d["marques"], "humeurs": d["humeurs"],
        "especes": especes,
        # ancien nom (bestiaire v1) → identifiant de la nouvelle espèce de même numéro
        "anciens": {nom: par_numero[n] for nom, n in d["anciens"].items() if n in par_numero},
    }
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))
    SORTIE.write_text("// Généré par donnees/bestiaire2/generer_site.py — ne pas modifier à la main.\n"
                      f"export default {texte};\n", encoding="utf-8")
    n = sum(v["dessinee"] for e in especes for v in e["variantes"])
    print(f"site/src/bestiaire.js : {len(especes)} espèces, {n} variantes dessinées, {len(texte) // 1024} Ko")


if __name__ == "__main__":
    main()
