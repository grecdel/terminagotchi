"""Les textes de la Crypte des Codes (cryptographie et blockchain, phase 5) dans les 14 langues.

Une langue par fichier : textes_crypte_fr.py (la référence), textes_crypte_en.py, … ; chacun a EXACTEMENT les mêmes
clés (vérifié ici), et les mêmes {champs} que le français.

    python3 donnees/crypte/outils/textes_crypte.py   ajoute ou met à jour les clés dans pc/tg/langues et
                                                    app/src/main/assets/langues (indentation 1, comme les fichiers)
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]
ICI = Path(__file__).resolve().parent


def langue(code):
    f = ICI / f"textes_crypte_{code}.py"
    spec = importlib.util.spec_from_file_location(f.stem, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.K


def tout():
    """{clé: {code: texte}} pour les 14 langues ; s'arrête si une langue n'a pas les mêmes clés ou champs."""
    fr = langue("fr")
    d = {k: {"fr": v} for k, v in fr.items()}
    for code in L[1:]:
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
                if dossier.startswith("pc") and k.startswith("cr.tel."):
                    continue                     # les messages du téléphone : seulement sur Android
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]))
