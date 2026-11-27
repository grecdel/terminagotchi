#!/usr/bin/env python3
"""Fabrique les catalogues de langues de l'appli Android (app/src/main/assets/i18n/<code>.json).

    python3 donnees/generer_langues.py

Catalogue Android = catalogue du PC (pc/tg/i18n/<code>.json, leçons communes) + textes propres au téléphone
(donnees/i18n/<code>_android.json).
"""
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

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
