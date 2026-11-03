"""Lecture et confort (maquettes validées le 3 novembre : idées 61, 62, 64, 65) : quatre réglages, PC et Android.

    taille   100 / 125 / 150 (%)     « A normal / A grand / A très grand » : tout l'espace grandit (PC : la mise en
                                     page est refaite sur un écran logique plus petit, puis agrandie ; en « grand »,
                                     les colonnes de gauche passent dans les onglets, en « très grand » la vue déployée
                                     aussi). Ctrl + / Ctrl − dans la fenêtre. Par défaut : la taille du système
                                     (Android : « Taille de police » ; GNOME : « facteur de mise à l'échelle du texte »).
    police   normale / facile        « Lecture facile » : une police aux lettres bien distinctes (Andika, SIL, licence
                                     OFL, si elle est là : pc/tg/polices/ ou installée sur l'ordinateur ; assets/polices
                                     sur Android), un peu plus grande, avec plus d'espace entre les lettres. Le terminal
                                     garde sa police à chasse fixe (les commandes restent alignées).
    formes   oui / non / auto        « Couleurs + formes » : jamais une couleur seule pour dire quelque chose ; chaque
                                     morceau de la vue déployée a sa petite forme (■ commande, ▲ option, ● argument,
                                     ◆ chemin, ━ tuyau…). auto : allumé avec les thèmes Contraste élevé et Daltonien.
    calme    oui / non / auto        « Mode calme » : rien ne clignote, rien ne secoue (bords d'arrivée fixes, vue
                                     déployée pas à pas, pas de pluie de pixels ni de grosses animations dans le monde,
                                     créature sans sursaut, curseur et « tu es ici » fixes, défi éclair sans chrono,
                                     éclairs des créatures glitch remplacés par leur léger effet fixe — exception
                                     accordée par le propriétaire, seulement dans ce mode). auto : allumé si le système
                                     demande déjà moins d'animations (Android « Supprimer les animations », GNOME
                                     « Animations » coupées).

Sauvegarde : state["config"]["confort"] = {taille, police, formes, calme, date} (absents = auto) ; Android :
jeu.module("confort"), mêmes champs. La police, les formes et le calme suivent le recensement comme le thème (le plus
récent gagne : champs confort / confortDate) ; la taille reste propre à chaque appareil (un téléphone et un écran de PC
n'ont pas la même taille). Même calcul en Kotlin (Confort.kt), vecteurs communs donnees/confort/vecteurs.json.
"""
import os
import subprocess
import time

from .langue import t

TAILLES = (100, 125, 150)
POLICES = ("normale", "facile")
FORMES = {"commande": "■", "option": "▲", "argument": "●", "chemin": "◆", "tuyau": "━", "redirection": "▼",
          "lien": "✚"}
THEMES_FORMES = ("contraste", "daltonien")
FACILE_TAILLE = 1.08                 # « Lecture facile » : 8 % plus grand…
FACILE_ESPACE = 0.06                 # … et 6 % d'un cadratin entre les lettres
POLICE_FICHIERS = ("Andika-Regular.ttf", "Andika-Bold.ttf")
SYNCHRO = ("police", "formes", "calme")
MOTS = {"oui": True, "on": True, "yes": True, "1": True, "non": False, "off": False, "no": False, "0": False,
        "auto": None}
NOMS_TAILLE = {"normal": 100, "normale": 100, "grand": 125, "big": 125, "large": 125, "tresgrand": 150,
               "très-grand": 150, "tres-grand": 150, "huge": 150}


# ---------------------------------------------------------------- le calcul (pur : mêmes vecteurs que Confort.kt)
def taille_de(echelle):
    """La taille la plus proche d'une échelle du système (1.0, 1.3…) : 100, 125 ou 150."""
    try:
        e = float(echelle or 1.0)
    except (TypeError, ValueError):
        e = 1.0
    return 100 if e < 1.12 else 125 if e < 1.37 else 150


def resoudre(c, theme="sombre", systeme=None):
    """Les réglages effectifs : {taille, police, formes, calme}. c : les réglages enregistrés (absents = auto) ;
    systeme : {"echelle": 1.0, "moins_animations": False}."""
    c = c if isinstance(c, dict) else {}
    s = systeme if isinstance(systeme, dict) else {}
    taille = c.get("taille")
    if taille not in TAILLES:
        taille = taille_de(s.get("echelle", 1.0))
    police = c.get("police") if c.get("police") in POLICES else "normale"
    formes = c.get("formes") if isinstance(c.get("formes"), bool) else theme in THEMES_FORMES
    calme = c.get("calme") if isinstance(c.get("calme"), bool) else bool(s.get("moins_animations"))
    return {"taille": taille, "police": police, "formes": formes, "calme": calme}


def taille_suivante(taille, sens):
    """Ctrl + (sens 1) / Ctrl − (sens −1) : la taille d'à côté, sans faire le tour."""
    i = TAILLES.index(taille) if taille in TAILLES else 0
    return TAILLES[max(0, min(len(TAILLES) - 1, i + (1 if sens > 0 else -1)))]


# ---------------------------------------------------------------- le système (ce que l'ordinateur demande déjà)
_SYS = {}


def systeme():
    """{"echelle", "moins_animations"} lus une fois : GNOME (gsettings), sinon rien de spécial. Jamais d'erreur."""
    if _SYS:
        return dict(_SYS)
    echelle, moins = 1.0, False
    env = os.environ.get("TG_CONFORT_SYSTEME")      # pour les tests : « 1.3,calme »
    if env is not None:
        morceaux = env.split(",")
        try:
            echelle = float(morceaux[0] or 1.0)
        except ValueError:
            echelle = 1.0
        moins = "calme" in morceaux[1:]
    elif os.name != "nt" and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        echelle = _gsettings("text-scaling-factor", echelle, float)
        moins = _gsettings("enable-animations", True, lambda v: v.strip() == "true") is False
    _SYS.update(echelle=echelle, moins_animations=moins)
    return dict(_SYS)


def _gsettings(cle, defaut, lire):
    try:
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", cle], capture_output=True, text=True,
                           timeout=1.5)
        return lire(r.stdout) if r.returncode == 0 and r.stdout.strip() else defaut
    except (OSError, ValueError, subprocess.SubprocessError):
        return defaut


# ---------------------------------------------------------------- la partie
def c_(state):
    cfg = state.setdefault("config", {}) if isinstance(state, dict) else {}
    c = cfg.get("confort")
    if not isinstance(c, dict):
        c = cfg["confort"] = {}
    return c


def reglages(state):
    if not isinstance(state, dict):
        return resoudre({}, "sombre", systeme())
    from . import apparence
    return resoudre((state.get("config") or {}).get("confort"), apparence.cle_theme(state), systeme())


def calme(state):
    return reglages(state)["calme"]


def regler(state, cle, valeur):
    """Change un réglage (valeur None : auto). Renvoie False si la valeur n'est pas permise."""
    c = c_(state)
    if cle == "taille":
        if valeur is not None and valeur not in TAILLES:
            return False
    elif cle == "police":
        if valeur is not None and valeur not in POLICES:
            return False
    elif cle in ("formes", "calme"):
        if valeur is not None and not isinstance(valeur, bool):
            return False
    else:
        return False
    if valeur is None:
        c.pop(cle, None)
    else:
        c[cle] = valeur
    if cle in SYNCHRO:
        c["date"] = int(time.time() * 1000)
    activer(state)
    return True


def activer(state):
    """À chaque chargement et changement : ce que lisent les modules qui n'ont pas la partie sous la main."""
    from . import glitch
    r = reglages(state)
    glitch.CALME[0] = r["calme"]
    return r


# ---------------------------------------------------------------- le recensement (le plus récent gagne)
def pour_recensement(state):
    c = (state.get("config") or {}).get("confort") or {}
    morceaux = []
    if c.get("police") == "facile":
        morceaux.append("facile")
    for k in ("formes", "calme"):
        if isinstance(c.get(k), bool):
            morceaux.append(k + ("1" if c[k] else "0"))
    return ",".join(morceaux), int(c.get("date") or 0)


def depuis_recensement(state, texte, date):
    """Le serveur a des réglages plus récents : on les prend (seulement des mots connus)."""
    c = c_(state)
    if int(date or 0) <= int(c.get("date") or 0) or not isinstance(texte, str) or len(texte) > 40:
        return False
    mots = set(texte.split(",")) - {""}
    if not mots <= {"facile", "formes0", "formes1", "calme0", "calme1"}:
        return False
    c.pop("police", None)
    if "facile" in mots:
        c["police"] = "facile"
    for k in ("formes", "calme"):
        c.pop(k, None)
        if k + "1" in mots:
            c[k] = True
        elif k + "0" in mots:
            c[k] = False
    c["date"] = int(date)
    activer(state)
    return True


# ---------------------------------------------------------------- la police « Lecture facile »
_POLICE = {}


def fichier_police(gras=False):
    """Le fichier d'Andika (pc/tg/polices/ ou installé sur l'ordinateur), ou None : sans lui, « Lecture facile »
    garde la police habituelle, un peu plus grande et plus espacée."""
    cle = bool(gras)
    if cle in _POLICE:
        return _POLICE[cle]
    nom = POLICE_FICHIERS[1 if gras else 0]
    ici = os.path.join(os.path.dirname(os.path.abspath(__file__)), "polices", nom)
    trouve = ici if os.path.isfile(ici) else None
    if trouve is None:
        for d in ("/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.local/share/fonts"),
                  os.path.expanduser("~/.fonts"), "C:\\Windows\\Fonts", "/Library/Fonts"):
            for racine, _ds, fs in os.walk(d) if os.path.isdir(d) else ():
                if nom in fs:
                    trouve = os.path.join(racine, nom)
                    break
            if trouve:
                break
    _POLICE[cle] = trouve
    return trouve


# ---------------------------------------------------------------- tg confort
def lignes(state):
    r = reglages(state)
    c = (state.get("config") or {}).get("confort") or {}
    auto = lambda k: "" if k in c else " (" + t("conf.auto") + ")"        # noqa: E731
    oui = lambda b: t("app.on") if b else t("app.off")                     # noqa: E731
    out = ["── " + t("conf.titre") + " ──",
           "  " + t("conf.taille") + " : " + t(f"conf.taille.{r['taille']}") + auto("taille"),
           "  " + t("conf.police") + " : " + t("conf.police." + r["police"]) + auto("police"),
           "  " + t("conf.formes") + " : " + oui(r["formes"]) + auto("formes"),
           "  " + t("conf.calme") + " : " + oui(r["calme"]) + auto("calme")]
    if r["police"] == "facile" and not fichier_police():
        out.append("  " + t("conf.police.absente"))
    out.append(t("conf.aide"))
    return out


def commande(state, args):
    """tg confort [taille 100|125|150|grand | police normale|facile | formes oui|non|auto | calme oui|non|auto]."""
    if len(args) >= 2:
        cle, v = args[0].lower(), args[1].lower()
        val, ok = None, False
        if cle in ("taille", "size", "texte"):
            cle = "taille"
            if v == "auto":
                ok = True
            elif v.rstrip("%").isdigit() and int(v.rstrip("%")) in TAILLES:
                val, ok = int(v.rstrip("%")), True
            elif v.replace(" ", "") in NOMS_TAILLE:
                val, ok = NOMS_TAILLE[v.replace(" ", "")], True
        elif cle in ("police", "font"):
            cle = "police"
            val = {"normale": "normale", "normal": "normale", "facile": "facile", "easy": "facile",
                   "auto": None}.get(v, "?")
            ok = val != "?"
        elif cle in ("formes", "shapes", "calme", "calm"):
            cle = "formes" if cle in ("formes", "shapes") else "calme"
            ok = v in MOTS
            val = MOTS.get(v)
        if not ok or not regler(state, cle, val):
            return [t("conf.faux")] + lignes(state)
        return ["✓ " + t("conf.ok")] + lignes(state)
    return lignes(state)
