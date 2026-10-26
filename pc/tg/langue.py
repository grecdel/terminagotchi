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
import sys
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


# ---------------------------------------------------------------- les commandes à taper, en vert
# Dans les textes (langues/xx.json et le code), une commande à taper est entre backticks : `mkdir cabane`.
# Le rendu se fait à un seul endroit : la sortie du terminal (installer_rendu, appelé par app.main) met la
# commande en vert, ou enlève juste les backticks si NO_COLOR est défini ou si la sortie n'est pas un
# terminal. Les caractères de la commande ne changent pas (le copier-coller marche comme avant).
# En arabe et en ourdou, la commande est isolée de gauche à droite (LRI … PDI), avec sa couleur.
# Les fenêtres (bureau.py) et les notifications (notif.py) reçoivent le texte sans backticks (sans_marques).
MARQUE = "`"
_PASSAGE = re.compile(r"`([^`\n]+)`")
VERT = "\x1b[38;5;84m"
FIN_VERT = "\x1b[39m"
LRI, PDI = "\u2066", "\u2069"
RTL = ("ar", "ur")


def couleurs(flux):
    """Vrai si on peut colorer ce flux : un vrai terminal, sans NO_COLOR ni TERM=dumb."""
    if os.environ.get("NO_COLOR") is not None or os.environ.get("TERM") == "dumb":
        return False
    try:
        return flux.isatty()
    except (AttributeError, ValueError, OSError):
        return False


def rendre(texte, couleur=True):
    """`commande` → la commande en vert (ou sans couleur), isolée de gauche à droite en arabe et en ourdou."""
    if MARQUE not in texte:
        return texte
    rtl = courante() in RTL

    def un(m):
        c = LRI + m.group(1) + PDI if rtl else m.group(1)
        return VERT + c + FIN_VERT if couleur else c
    return _PASSAGE.sub(un, texte)


def sans_marques(texte):
    """Le texte sans backticks ni couleur (fenêtres, notifications, fichiers)."""
    return rendre(texte, couleur=False) if isinstance(texte, str) else texte


class _Rendu:
    """Enveloppe sys.stdout : chaque écriture passe par rendre()."""

    def __init__(self, flux):
        self._flux = flux
        self._couleur = couleurs(flux)

    def write(self, s):
        return self._flux.write(rendre(s, self._couleur) if isinstance(s, str) else s)

    def __getattr__(self, nom):
        return getattr(self._flux, nom)


def installer_rendu():
    """À appeler une fois au démarrage : tout ce qui est écrit dans le terminal montre les commandes en vert."""
    if not isinstance(sys.stdout, _Rendu):
        sys.stdout = _Rendu(sys.stdout)


def equilibrer(lignes):
    """Après un découpage en lignes : un passage `…` coupé en deux est refermé puis rouvert."""
    out, ouvert = [], False
    for l in lignes:
        if ouvert:
            l = MARQUE + l
        ouvert = l.count(MARQUE) % 2 == 1
        out.append(l + MARQUE if ouvert else l)
    return out


# ---------------------------------------------------------------- largeur d'affichage
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def largeur_car(c):
    if c == MARQUE:                         # le marqueur des commandes : remplacé par une couleur
        return 0
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
    out = out.rstrip()
    if out.count(MARQUE) % 2:
        out += MARQUE
    return out + fin


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
    return equilibrer([l for l in lignes if l]) or [""]
