"""Les fiches notions de la charte de rigueur (docs/programme.md § 7.1 et § 6.1).

donnees/programme.json (copié dans pc/tg/programme.json et dans les assets Android) décrit chaque notion du jeu :
  enfant         la phrase imagée (clé de langue)
  grands         la phrase exacte (clé de langue)
  vrai_terminal  la commande réelle et ce qu'elle affiche vraiment (rejoué dans bash : pc/outils/rejeu_bash.py)
  limite_image   où l'image s'arrête (clé de langue)
  idees_fausses  les erreurs fréquentes à démonter (clés de langue)
  sources        la référence qui fait foi (page man, POSIX, manuel de bash, RFC…)
  relu_par       qui a validé la fiche (rôle, date), null tant que personne ne l'a relue
Une étape de leçon renvoie à ses fiches par le motif de chaque notion (« motif », appliqué à la commande de
l'étape) ; pc/outils/verifier_programme.py vérifie que chaque étape en a au moins une et qu'aucune fiche n'est
orpheline. Même lecture sur Android (Programme.kt).
"""
import json
import pkgutil
import re

_P = None


def donnees():
    global _P
    if _P is None:
        try:
            _P = json.loads(pkgutil.get_data(__package__, "programme.json").decode("utf-8"))
        except (OSError, TypeError, ValueError):
            _P = {"notions": {}, "maths": {}, "mondes": [], "etapes": {}, "recompenses": {}}
    return _P


def notions_de(cmd):
    """Les fiches d'une commande (dans l'ordre du fichier) : [id]."""
    cmd = (cmd or "").strip()
    return [nid for nid, n in donnees()["notions"].items() if re.search(n["motif"], cmd)]


def fiche(nid):
    return donnees()["notions"].get(nid)


def lignes_fiche(cmd):
    """Les lignes « où l'image s'arrête » et « idée fausse » de la première fiche d'une commande (tg explique)."""
    from .langue import t
    ids = notions_de(cmd) or notions_de(cmd.strip() + " x")       # « rm » tout seul : la fiche de « rm x »
    if not ids:
        return []
    f = fiche(ids[0])
    out = [t("prog.limite", texte=t(f["limite_image"]))]
    out += [t("prog.idee", texte=t(k)) for k in f.get("idees_fausses", [])]
    return out
