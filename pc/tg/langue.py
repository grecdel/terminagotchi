"""Les langues du jeu. Le français est la langue d'origine ; les autres viennent des catalogues i18n/<code>.json :
  « textes » : texte français → traduction ; « motifs » : [expression, remplacement] pour les textes variables.
Un texte sans traduction reste en français (rien ne casse quand une traduction manque).

Choix de la langue : tg langue <code>  (sinon la variable TG_LANGUE, sinon la langue du système, sinon le français).
"""
import json
import os
import pkgutil
import re

NOMS = {"fr": "Français", "en": "English", "es": "Español", "de": "Deutsch", "it": "Italiano", "pt": "Português",
        "zh": "中文", "ru": "Русский", "ja": "日本語", "hi": "हिन्दी", "ar": "العربية", "bn": "বাংলা", "id": "Bahasa Indonesia",
        "ur": "اردو"}


def _disponibles():
    """Le français, plus chaque langue dont le catalogue i18n/<code>.json est livré avec le jeu."""
    codes = ["fr"]
    for c in NOMS:
        if c != "fr":
            try:
                if pkgutil.get_data(__package__, f"i18n/{c}.json"):
                    codes.append(c)
            except (OSError, ValueError):
                pass
    return {c: NOMS[c] for c in codes}


LANGUES = _disponibles()
_CATALOGUE = None
_LANGUE = None


def _fichier():
    from . import core
    return core.SAVE_DIR / "langue"


def courante():
    global _LANGUE
    if _LANGUE is None:
        choix = os.environ.get("TG_LANGUE", "").strip().lower()
        if not choix:
            try:
                choix = _fichier().read_text(encoding="utf-8").strip().lower()
            except OSError:
                from . import core
                # nouvelle partie : la langue du système ; partie déjà commencée : le français (rien ne change)
                choix = "fr" if core.SAVE_FILE.exists() else (os.environ.get("LANG") or os.environ.get("LANGUAGE") or "fr")[:2].lower()
        _LANGUE = choix if choix in LANGUES else "fr"
    return _LANGUE


def choisir(code):
    global _LANGUE, _CATALOGUE
    code = (code or "").strip().lower()
    if code not in LANGUES:
        return None
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(code, encoding="utf-8")
    _LANGUE, _CATALOGUE = code, None
    return code


def catalogue():
    global _CATALOGUE
    if _CATALOGUE is None:
        _CATALOGUE = {"textes": {}, "motifs": []}
        if courante() != "fr":
            try:
                brut = pkgutil.get_data(__package__, f"i18n/{courante()}.json")
                _CATALOGUE = json.loads(brut.decode("utf-8"))
                _CATALOGUE["motifs"] = [(re.compile(a), b) for a, b in _CATALOGUE.get("motifs", [])]
            except (OSError, ValueError, TypeError):
                pass
    return _CATALOGUE


def tr(texte):
    """Traduit un texte français dans la langue du joueur (ou le laisse tel quel)."""
    if not isinstance(texte, str) or courante() == "fr":
        return texte
    c = catalogue()
    t = c["textes"].get(texte)
    if t is not None:
        return t
    for motif, rempl in c["motifs"]:           # textes variables : chaque motif qui correspond s'applique
        texte = motif.sub(rempl, texte)
    return texte


def traduire_lecons(*parcours):
    """Traduit en place les textes des leçons (titres, consignes, explications, astuces, descriptions).
    Les noms de compétences restent en français : ce sont aussi les identifiants des sauvegardes."""
    if courante() == "fr":
        return
    for p in parcours:
        for lec in p:
            lec["titre"] = tr(lec["titre"])
            for s in lec["steps"]:
                for k in ("dit", "bravo", "astuce"):
                    if k in s:
                        s[k] = tr(s[k])
