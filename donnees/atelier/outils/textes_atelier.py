"""Les textes de l'Atelier (phase 5) dans les 14 langues.

Une langue par fichier : textes_atelier_fr.py (la référence), textes_atelier_en.py, … ; chacun a EXACTEMENT les mêmes
clés (vérifié ici), et les mêmes {champs} que le français.

    python3 donnees/atelier/outils/textes_atelier.py   ajoute ou met à jour les clés dans pc/tg/langues et
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
    f = ICI / f"textes_atelier_{code}.py"
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


# Windows (PowerShell) : des textes FABRIQUÉS à partir des textes bash de chaque langue, pour qu'ils ne puissent pas
# diverger (cerveau.sh → cerveau.ps1, la boucle for … done → 1..N | ForEach-Object { … }) ; ou les mêmes mots quand
# seul le nom de la clé change (hist.<étape>.ps.dit : la version des grands suit la clé du « dit »). Chaque morceau
# remplacé doit exister dans la langue (sinon le texte resterait en bash : refusé). Les accolades de PowerShell sont
# doublées ({{ … }}) : les textes passent par str.format (langue.remplir), qui les rend simples.
SH = "cerveau.sh"
PS1 = "cerveau.ps1"
BOUCLES = [("for i in $(seq 10); do sh cerveau.sh; atelier pas; done", "1..10 | ForEach-Object {{ .\\cerveau.ps1; atelier pas }}"),
           ("for i in $(seq 20); do sh cerveau.sh; atelier pas; done", "1..20 | ForEach-Object {{ .\\cerveau.ps1; atelier pas }}")]
DERIVES = {
    "at.ps.meuble.plan": ("at.meuble.plan", [("cerveau_exemple.sh", "cerveau_exemple.ps1")]),
    "at.ps.aide.liste": ("at.aide.liste", [(SH, PS1)]),
    "at.ps.essai.texte": ("at.essai.texte", BOUCLES[:1]),
    "at.ps.defi.regles": ("at.defi.regles", BOUCLES[1:] + [(SH, PS1)]),
    "at.ps.defi.recommence": ("at.defi.recommence", [(SH, PS1)]),
    "at.ps.indice.boucle": ("at.indice.boucle", [("sh cerveau.sh", ".\\cerveau.ps1")]),
    "at.ps.indice.malin": ("at.indice.malin", [(SH, PS1)]),
    "hist.at4.3.ps.dit": ("hist.at4.3.dit", [(SH, PS1)]),
    "hist.at4.3.ps.bravo": ("hist.at4.3.bravo", [(SH, PS1)]),
    "hist.at4.6.ps.dit": ("hist.at4.6.dit", [(SH, PS1)]),
    "hist.at5.1.ps.adulte": ("hist.at5.1.adulte", [(SH, PS1)]),
}
for _c in ("at3.1.dit", "at3.2.dit", "at4.0.dit", "at4.1.dit", "at4.1.bravo", "at4.3.adulte", "at4.6.bravo", "at5.1.dit",
           "at5.1.bravo", "at6.5.dit", "at6.5.bravo", "at7.1.dit", "at7.1.adulte"):
    _e, _r = _c.rsplit(".", 1)
    DERIVES[f"hist.{_e}.ps.{_r}"] = (f"hist.{_c}", [])


def derives(textes, code="fr"):
    """Les textes PowerShell fabriqués pour une langue {clé: texte}."""
    out = {}
    for k, (source, remplacements) in DERIVES.items():
        v = textes[source]
        for a, b in remplacements:
            assert a in v, (code, k, "il manque", a)
            v = v.replace(a, b)
        out[k] = v
    return out


def tout():
    """{clé: {code: texte}} pour les 14 langues ; s'arrête si une langue n'a pas les mêmes clés ou champs."""
    fr = langue("fr")
    fr.update(derives(fr))
    d = {k: {"fr": v} for k, v in fr.items()}
    for code in L[1:]:
        if PROVISOIRE and not (ICI / f"textes_atelier_{code}.py").exists():
            for k, v in fr.items():
                d[k][code] = v                  # en cours d'écriture : le français en attendant (jamais livré)
            continue
        k2 = langue(code)
        k2.update(derives(k2, code))
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
                if dossier.startswith("pc") and k.startswith("at.tel."):
                    continue                     # les messages du téléphone : seulement sur Android
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter([a for a in sys.argv[1:] if not a.startswith("--")][0] if [a for a in sys.argv[1:] if not a.startswith("--")] else Path(__file__).resolve().parents[3]))
