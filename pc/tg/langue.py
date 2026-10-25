"""La langue de l'interface : 14 langues, le français par défaut.

  t(clé, **params)   le texte de la clé dans la langue choisie (repli sur le français si la clé
                     manque) ; les {params} sont remplis ; en français, l'élision se fait toute
                     seule (« de {nom} » + Inodin → « d'Inodin », voir mots.accorder).
  liste(clé)         une liste de phrases (pour en tirer une au hasard).
  definir(code)      change la langue courante (fr, en, es, de, it, pt, zh, ru, ja, hi, ar, bn, id, ur).
  detecter()         la langue du système (LANGUAGE, LC_ALL, LC_MESSAGES, LANG), sinon le français.

Les textes sont dans langues/xx.json (un fichier par langue, embarqué dans le zipapp).
Les noms et descriptions des monstres (bestiaire.json) ne sont PAS traduits.
Le jargon progressif (mots.terme) existe dans chaque langue : clés « terme.xxx », 3 paliers.

Largeur à l'écran : les caractères chinois et japonais prennent 2 colonnes ; largeur(),
ajuster() et envelopper() en tiennent compte pour que les cadres et les bulles restent droits.

Limite connue : l'arabe et l'ourdou s'écrivent de droite à gauche, ce que la plupart des
terminaux ne gèrent pas. Le texte est affiché tel quel (aucun réordonnancement manuel) : selon
le terminal, les mots peuvent apparaître dans le désordre ou alignés à gauche.
"""
import json
import os
import pkgutil
import random
import re
import unicodedata

LANGUES = {
    "fr": "Français", "en": "English", "es": "Español", "de": "Deutsch", "it": "Italiano",
    "pt": "Português", "zh": "中文", "ru": "Русский", "ja": "日本語", "hi": "हिन्दी",
    "ar": "العربية", "bn": "বাংলা", "id": "Bahasa Indonesia", "ur": "اردو",
}
DEFAUT = "fr"
DROITE_A_GAUCHE = ("ar", "ur")

_courante = DEFAUT
_textes = {}


def _charger(code):
    if code not in _textes:
        try:
            _textes[code] = json.loads(pkgutil.get_data(__package__, f"langues/{code}.json").decode("utf-8"))
        except (OSError, TypeError, ValueError):
            _textes[code] = {}
    return _textes[code]


def definir(code):
    """Change la langue courante (code inconnu → français)."""
    global _courante
    _courante = code if code in LANGUES else DEFAUT
    return _courante


def courante():
    return _courante


def code_valide(code):
    code = (code or "").strip().lower().replace("-", "_").split("_")[0]
    return code if code in LANGUES else None


def detecter(env=None):
    """La langue du système, d'après les variables d'environnement (premier lancement)."""
    env = os.environ if env is None else env
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = env.get(var, "")
        if not v:
            continue
        for morceau in v.split(":"):
            code = morceau.split(".")[0].split("@")[0].split("_")[0].lower()
            if code in LANGUES:
                return code
        if var != "LANGUAGE":           # LANGUAGE est une liste de préférences ; les autres décident
            break
    return DEFAUT


def appliquer(state):
    """Prend la langue enregistrée dans la sauvegarde."""
    if state:
        definir(state.get("langue") or DEFAUT)


def brut(cle, code=None):
    """La valeur d'une clé (texte ou liste) dans la langue demandée, sinon en français, sinon None."""
    v = _charger(code or _courante).get(cle)
    if v is None and (code or _courante) != DEFAUT:
        v = _charger(DEFAUT).get(cle)
    return v


class _Sur(dict):
    """Un {param} oublié reste affiché tel quel au lieu de tout casser."""
    def __missing__(self, k):
        return "{" + k + "}"


def remplir(modele, params, code=None):
    if not params:
        return modele.replace("{{", "{").replace("}}", "}") if "{{" in modele or "}}" in modele else modele
    if (code or _courante) == "fr":
        from .mots import elider
        modele = elider(modele, params)
    try:
        return modele.format_map(_Sur(params))
    except (ValueError, IndexError):
        return modele


def t(cle, **params):
    """Le texte d'une clé, traduit et rempli."""
    v = brut(cle)
    if v is None:
        return cle
    if isinstance(v, list):
        v = v[0] if v else ""
    return remplir(v, params)


def liste(cle):
    """Une liste de phrases (non remplies)."""
    v = brut(cle)
    if v is None:
        return [cle]
    return list(v) if isinstance(v, list) else [v]


def au_hasard(cle, **params):
    return remplir(random.choice(liste(cle)), params)


# ---------------------------------------------------------------- largeur d'affichage
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def largeur_car(c):
    if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1


def largeur(texte):
    """Nombre de colonnes occupées à l'écran (sans les couleurs ; CJK = 2 colonnes)."""
    return sum(largeur_car(c) for c in _ANSI.sub("", texte))


def ajuster(texte, n):
    """Complète avec des espaces jusqu'à n colonnes."""
    return texte + " " * max(0, n - largeur(texte))


def raccourcir(texte, n, fin="…"):
    """Coupe un texte (sans couleurs) à n colonnes."""
    if largeur(texte) <= n:
        return texte
    out, w = "", 0
    for c in texte:
        lc = largeur_car(c)
        if w + lc > n - largeur(fin):
            break
        out += c
        w += lc
    return out.rstrip() + fin


def envelopper(texte, n):
    """Comme textwrap.wrap, mais en colonnes d'écran ; coupe aussi entre deux caractères CJK."""
    lignes = []
    for para in texte.split("\n"):
        ligne, w = "", 0
        for mot in re.findall(r"\S+\s*", para) or [""]:
            morceaux = [mot]
            if any(largeur_car(c) == 2 for c in mot):
                morceaux = re.findall(r"[^\s]\s*", mot)       # les idéogrammes se coupent n'importe où
            for m in morceaux:
                lm = largeur(m.rstrip())
                if w and w + lm > n:
                    lignes.append(ligne.rstrip())
                    ligne, w = "", 0
                while lm > n:                              # mot plus long que la ligne
                    coupe = raccourcir(m, n, fin="")
                    lignes.append(coupe)
                    m = m[len(coupe):]
                    lm = largeur(m.rstrip())
                ligne += m
                w += largeur(m)
        lignes.append(ligne.rstrip())
    return [l for l in lignes if l] or [""]
