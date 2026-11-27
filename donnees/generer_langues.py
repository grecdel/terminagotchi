#!/usr/bin/env python3
"""Fabrique les catalogues de langues de l'appli Android (app/src/main/assets/i18n/<code>.json).

    python3 donnees/generer_langues.py

Catalogue Android = catalogue du PC (pc/tg/i18n/<code>.json, leçons communes) + textes propres au téléphone
(donnees/i18n/<code>_android.json).
"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

SITE = {}
for pc in sorted((RACINE / "pc" / "tg" / "i18n").glob("*.json")):
    code = pc.stem
    d = json.loads(pc.read_text(encoding="utf-8"))
    extra = RACINE / "donnees" / "i18n" / f"{code}_android.json"
    if extra.exists():
        d["textes"].update(json.loads(extra.read_text(encoding="utf-8")))
    sortie = RACINE / "app" / "src" / "main" / "assets" / "i18n" / f"{code}.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{code} : {len(d['textes'])} textes, {len(d['motifs'])} motifs")
    SITE[code] = d["textes"]


# ---------------------------------------------------------------- le site : textes des espèces + interface du site
def site():
    b = json.loads((RACINE / "pc" / "tg" / "bestiaire.json").read_text(encoding="utf-8"))
    especes = set()
    for e in b["especes"]:
        especes.update(e[k] for k in ("description", "comportement", "capacite", "famille"))
    especes.update(f["nom"] for f in b["familles"])
    especes.update(b["lieux"].values())
    paires = {}
    for code, textes in SITE.items():
        t = {k: v for k, v in textes.items() if k in especes}
        f = RACINE / "donnees" / "i18n" / f"{code}_site.json"
        if f.exists():
            t.update(json.loads(f.read_text(encoding="utf-8")))
        paires[code] = sorted(t.items(), key=lambda kv: -len(kv[0]))
    (RACINE / "site" / "src" / "i18n.js").write_text(
        "// Généré par donnees/generer_langues.py — ne pas modifier à la main.\n"
        "// Traductions du site : [texte français, traduction], du plus long au plus court.\nexport default "
        + json.dumps(paires, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("site :", {k: len(v) for k, v in paires.items()})


site()
