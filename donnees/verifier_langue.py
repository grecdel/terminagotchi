#!/usr/bin/env python3
"""Vérifie un catalogue de langue par rapport au catalogue anglais (référence de structure).

    python3 donnees/verifier_langue.py es

Contrôle pc/tg/i18n/<code>.json, donnees/i18n/<code>_android.json et donnees/i18n/<code>_site.json :
JSON valide, mêmes clés (textes français) que l'anglais, mêmes motifs (expressions identiques), et dans chaque
traduction les mêmes {jetons}, les mêmes \\1 \\2… et les mêmes `commandes entre guillemets inversés`.
"""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
code = sys.argv[1]
problemes = []


def charger(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problemes.append(f"{p} : fichier absent")
    except ValueError as e:
        problemes.append(f"{p} : JSON invalide ({e})")
    return None


def jetons(t):
    return (sorted(re.findall(r"\{[a-z_]*\}", t)), sorted(re.findall(r"\\\d", t)), sorted(re.findall(r"`[^`]+`", t)))


def comparer(ref, cand, nom):
    manquants = [k for k in ref if k not in cand]
    en_trop = [k for k in cand if k not in ref]
    if manquants:
        problemes.append(f"{nom} : {len(manquants)} textes manquants, ex. {manquants[:3]}")
    if en_trop:
        problemes.append(f"{nom} : {len(en_trop)} clés inconnues, ex. {en_trop[:3]}")
    for k, v in cand.items():
        if k in ref:
            if not isinstance(v, str) or not v.strip():
                problemes.append(f"{nom} : traduction vide pour {k[:60]!r}")
            elif jetons(k) != jetons(v):
                problemes.append(f"{nom} : jetons différents pour {k[:60]!r} → {v[:60]!r}")


en = charger(RACINE / "pc/tg/i18n/en.json")
c = charger(RACINE / f"pc/tg/i18n/{code}.json")
if en and c:
    comparer(en["textes"], c.get("textes", {}), f"pc/tg/i18n/{code}.json")
    m_en = [m[0] for m in en["motifs"]]
    m_c = [m[0] for m in c.get("motifs", [])]
    if m_en != m_c:
        problemes.append(f"motifs : les expressions doivent être identiques à en.json, dans le même ordre ({len(m_c)}/{len(m_en)})")
    for (a, r1), (b, r2) in zip(en["motifs"], c.get("motifs", [])):
        if sorted(re.findall(r"\\\d", r1)) != sorted(re.findall(r"\\\d", r2)):
            problemes.append(f"motif {a[:40]!r} : groupes \\1… différents dans le remplacement")
for suffixe in ("android", "site"):
    r = charger(RACINE / f"donnees/i18n/en_{suffixe}.json")
    k = charger(RACINE / f"donnees/i18n/{code}_{suffixe}.json")
    if r and k:
        comparer(r, k, f"donnees/i18n/{code}_{suffixe}.json")
print("\n".join(problemes) if problemes else f"{code} : OK")
sys.exit(1 if problemes else 0)
