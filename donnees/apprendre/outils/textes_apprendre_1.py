"""Morceau 1 : les textes d'« Apprendre en jouant », une langue par fichier (langues/xx.py, dictionnaire D),
assemblés ici clé par clé (le français est la référence : toutes les langues ont exactement ses clés)."""
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]


def _lire(code):
    ns = {}
    exec((Path(__file__).parent / "langues" / f"{code}.py").read_text(encoding="utf-8"), ns)
    return ns["D"]


_D = {c: _lire(c) for c in L}
for _c in L:
    _manque = set(_D["fr"]) ^ set(_D[_c])
    assert not _manque, (_c, sorted(_manque))
K = {k: {c: _D[c][k] for c in L} for k in _D["fr"]}
