"""Les textes de l'Observatoire de l'IA (phase 5) dans les 14 langues.

Une langue par fichier : textes_observatoire_fr.py (la référence), textes_observatoire_en.py, … ; chacun a EXACTEMENT les mêmes
clés (vérifié ici), et les mêmes {champs} que le français.

    python3 donnees/observatoire/outils/textes_observatoire.py   ajoute ou met à jour les clés dans pc/tg/langues et
                                                    app/src/main/assets/langues (indentation 1, comme les fichiers)
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]
ICI = Path(__file__).resolve().parent
PROVISOIRE = "--provisoire" in sys.argv


def langue(code):
    """{clé: texte} d'une langue. Le français donne K ; les autres langues donnent V : les textes DANS L'ORDRE des clés
    du français, avec des repères ("@", "clé") qui vérifient l'alignement (une traduction décalée est refusée)."""
    f = ICI / f"textes_observatoire_{code}.py"
    spec = importlib.util.spec_from_file_location(f.stem, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if hasattr(m, "K"):
        return m.K
    cles = list(langue("fr"))
    out, i = {}, 0
    for v in m.V:
        if isinstance(v, tuple):
            assert v[0] == "@" and i < len(cles) and cles[i] == v[1], (code, "repère", v, cles[i] if i < len(cles) else None)
            continue
        assert i < len(cles), (code, "trop de textes", v[:40])
        out[cles[i]] = v
        i += 1
    assert i == len(cles), (code, "il manque des textes à partir de", cles[i] if i < len(cles) else None)
    return out


def tout():
    """{clé: {code: texte}} pour les 14 langues ; s'arrête si une langue n'a pas les mêmes clés ou champs."""
    fr = langue("fr")
    d = {k: {"fr": v} for k, v in fr.items()}
    for code in L[1:]:
        if PROVISOIRE and not (ICI / f"textes_observatoire_{code}.py").exists():
            for k, v in fr.items():
                d[k][code] = v                  # en cours d'écriture : le français en attendant (jamais livré)
            continue
        k2 = langue(code)
        manque, trop = set(fr) - set(k2), set(k2) - set(fr)
        assert not manque and not trop, (code, sorted(manque)[:5], sorted(trop)[:5])
        for k, v in k2.items():
            champs = set(re.findall(r"\{(\w+)\}", fr[k]))
            assert set(re.findall(r"\{(\w+)\}", v)) == champs, (code, k)
            d[k][code] = v
    return d


def ajouter(racine):
    racine = Path(racine)
    n = 0
    K2 = tout()
    for dossier in ("pc/tg/langues", "app/src/main/assets/langues"):
        for code in L:
            f = racine / dossier / f"{code}.json"
            data = json.loads(f.read_text(encoding="utf-8"))
            for k, v in K2.items():
                if dossier.startswith("pc") and k.startswith("ob.tel."):
                    continue                     # les messages du téléphone : seulement sur Android
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter([a for a in sys.argv[1:] if not a.startswith("--")][0] if [a for a in sys.argv[1:] if not a.startswith("--")] else Path(__file__).resolve().parents[3]))
