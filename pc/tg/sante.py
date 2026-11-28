"""La vérification au démarrage : le jeu regarde ses propres fichiers et répare doucement (comme Sante.kt sur Android).

Quand : au lancement de `tg` (l'écran du jeu, le menu des parties) et avec `tg verifier` ; jamais pour `tg prompt`
(appelé après chaque commande du shell : il doit rester instantané).

Ce qui est regardé, et ce qui est fait (rien n'est jamais effacé ; ce qui est remplacé est gardé à côté) :
  1. La sauvegarde active (~/.terminagotchi/save.json) a disparu ou ne se lit plus, mais une écriture inachevée
     (save.tmp) est bonne et plus récente que les copies de secours : elle est remise en place.
     Elle a disparu (un `rm` de trop) et une copie de secours est bonne : la copie revient (le jeu ne repart pas d'un
     œuf neuf en silence). Une sauvegarde illisible avec une copie bonne est déjà réparée par core.load.
  2. La liste des parties (parties/index.json) est abîmée, ou oublie des parties rangées (partie_<id>.json) :
     elle est refaite à partir des fichiers présents (reparer_index, mêmes vecteurs que Sante.kt).
  3. Les fichiers du jeu lui-même (textes, mondes, langues) : chacun doit se lire. Ils ne changent qu'à une mise à
     jour : la vérification complète n'est refaite que si leur taille ou leur date a changé (empreinte rangée dans
     ~/.terminagotchi/verification.json). Un fichier abîmé ne peut pas être réparé sans retélécharger le jeu (le jeu
     ne télécharge jamais rien) : on le dit à l'adulte, le jeu continue ; une langue abîmée laisse la place au
     français en attendant.
Aucune donnée n'est envoyée ; tout reste dans ~/.terminagotchi.
"""
import json
import os
import pkgutil
import time
from pathlib import Path

from . import core

PAQUET = __package__
EMPREINTE = "verification.json"


# ---------------------------------------------------------------- 2. la liste des parties (vecteurs communs)
def reparer_index(idx, actif_sauvegarde, rangees):
    """La liste des parties, réparée. idx : l'index lu (None s'il est absent ou abîmé) ; actif_sauvegarde : l'id
    rangé dans la sauvegarde active (None s'il n'y en a pas) ; rangees : les ids des partie_<id>.json présents (du
    plus ancien au plus récent). Renvoie (index, repare). Mêmes vecteurs que Sante.kt (donnees/sante/vecteurs.json)."""
    valide = (isinstance(idx, dict) and isinstance(idx.get("active"), str) and idx.get("active")
              and isinstance(idx.get("ordre"), list) and all(isinstance(i, str) for i in idx["ordre"]))
    if not valide:
        active = actif_sauvegarde or "1"
        ordre = [active] if actif_sauvegarde else []
        for i in rangees:
            if i not in ordre:
                ordre.append(i)
        return {"active": active, "ordre": ordre}, idx is not None or bool(rangees)
    active = idx["active"]
    ordre = []
    for i in idx["ordre"]:
        if i not in ordre:
            ordre.append(i)
    # la sauvegarde active dit qui elle est : si l'index nomme une autre partie (et que celle de la sauvegarde n'est
    # pas aussi rangée à côté), c'est l'index qui s'est trompé
    if actif_sauvegarde and actif_sauvegarde != active and actif_sauvegarde not in rangees:
        active = actif_sauvegarde
    # (la partie active absente de l'ordre est normale : la liste l'ajoute toujours ; ce n'est pas une panne)
    for i in rangees:
        if i not in ordre and i != active:
            ordre.append(i)
    nouveau = {"active": active, "ordre": ordre}
    return nouveau, nouveau != {"active": idx["active"], "ordre": idx["ordre"]}


def _lire(f):
    try:
        o = json.loads(f.read_text(encoding="utf-8"))
        return o
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _ecrire(f, o):
    from . import sur
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    fd = sur.ouvrir_nofollow(tmp)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(o, ensure_ascii=False))
    os.replace(tmp, f)


def _garder(f, suffixe="casse"):
    """Range un fichier remplacé à côté (jamais effacé)."""
    if f.exists() or f.is_symlink():
        os.replace(f, f.with_name(f.name + "." + suffixe + "-" + time.strftime("%Y%m%d-%H%M%S")))


def _index():
    from . import parties
    d = parties.dossier()
    f = d / "index.json"
    if not f.exists() and not any(d.glob("partie_*.json")):
        return None                             # rien encore : parties.index() le créera
    brut = _lire(f) if f.exists() else None
    sauv = core._lire_etat(core.SAVE_FILE) if core.SAVE_FILE.exists() else None
    actif = str(sauv.get("partie") or "1") if isinstance(sauv, dict) and sauv.get("name") else None
    fichiers = sorted(d.glob("partie_*.json"), key=lambda p: (p.stat().st_mtime, p.name))
    rangees = [p.name[len("partie_"):-len(".json")] for p in fichiers if isinstance(_lire(p), dict)]
    if f.exists() and brut is None:
        brut = "abime"                          # présent mais illisible (coupé, vide, pas du JSON)
    nouveau, repare = reparer_index(brut, actif, rangees)
    if not repare:
        return None
    if f.exists():
        _garder(f)
    _ecrire(f, nouveau)
    return ("sante.index", {"n": len(set(nouveau["ordre"]) | {nouveau["active"]})})


# ---------------------------------------------------------------- 1. la sauvegarde active
def _sauvegarde():
    f = core.SAVE_FILE
    tmp = f.with_suffix(".tmp")
    try:
        present = f.exists() or f.is_symlink()
        bonne = present and core._lire_etat(f) is not None
    except OSError:
        return None                             # droits retirés : core l'explique déjà, on ne touche à rien
    if bonne:
        return None
    secours = [b for b in core._secours() if b.exists() and _lire_ok(b)]
    try:
        tmp_ok = tmp.exists() and not tmp.is_symlink() and _lire_ok(tmp)
    except OSError:
        tmp_ok = False
    if tmp_ok and all(tmp.stat().st_mtime >= b.stat().st_mtime for b in secours):
        if present:
            _garder(f)
        os.replace(tmp, f)
        return ("sante.tmp", {})
    if not present and secours:
        f.write_bytes(secours[0].read_bytes())
        return ("sante.manquante", {})
    return None                                 # illisible : core.load prend la copie de secours (et le dit)


def _lire_ok(f):
    try:
        return core._lire_etat(f) is not None
    except OSError:
        return False


# ---------------------------------------------------------------- 3. les fichiers du jeu
def fichiers_du_jeu():
    """Les fichiers de données du jeu (chemins dans le paquet) : textes des mondes, langues, animations."""
    import importlib.resources as R
    out = []
    try:
        racine = R.files(PAQUET)
        for sous in ("", "langues", "anim"):
            d = racine / sous if sous else racine
            if not d.is_dir():
                continue
            for e in d.iterdir():
                if e.name.endswith(".json") and e.is_file():
                    out.append((sous + "/" if sous else "") + e.name)
    except (OSError, TypeError, ValueError):
        pass
    return sorted(out)


def _empreinte_jeu(noms):
    """Taille et date des fichiers du jeu (ou de l'archive .pyz) : elle ne change qu'à une mise à jour."""
    ici = Path(__file__).resolve().parent
    archive = getattr(__loader__, "archive", None)
    try:
        if archive:
            s = os.stat(archive)
            return f"pyz:{archive}:{s.st_size}:{int(s.st_mtime)}"
        morceaux = []
        for n in noms:
            s = os.stat(ici / n)
            morceaux.append(f"{n}:{s.st_size}:{int(s.st_mtime)}")
        return "|".join(morceaux)
    except OSError:
        return None


def abimes(noms=None):
    """Les fichiers du jeu qui ne se lisent pas (JSON abîmé, coupé, vide)."""
    out = []
    for n in noms if noms is not None else fichiers_du_jeu():
        try:
            o = json.loads(pkgutil.get_data(PAQUET, n).decode("utf-8"))
            if not isinstance(o, (dict, list)) or not o:
                out.append(n)
        except Exception:                       # noqa: BLE001 — n'importe quelle erreur = fichier abîmé
            out.append(n)
    return out


def _jeu(forcer):
    noms = fichiers_du_jeu()
    emp = _empreinte_jeu(noms)
    f = core.SAVE_DIR / EMPREINTE
    vu = _lire(f) if f.exists() else None
    if not forcer and emp and isinstance(vu, dict) and vu.get("empreinte") == emp and not vu.get("abimes"):
        return [], len(noms)
    mauvais = abimes(noms)
    try:
        _ecrire(f, {"empreinte": emp, "abimes": mauvais, "date": int(time.time())})
    except OSError:
        pass
    return mauvais, len(noms)


# ---------------------------------------------------------------- au démarrage
def au_demarrage(forcer=False):
    """Vérifie et répare doucement. Renvoie (messages, nombre de fichiers du jeu regardés) : les messages sont des
    (clé de texte, paramètres), à dire à l'enfant et à l'adulte. Ne lève jamais d'erreur (un souci ici ne doit pas
    empêcher de jouer)."""
    messages = []
    for etape in (_sauvegarde, _index):
        try:
            m = etape()
            if m:
                messages.append(m)
        except Exception:                       # noqa: BLE001
            from . import sur
            sur.noter_trace()
    n = 0
    try:
        mauvais, n = _jeu(forcer)
        for nom in mauvais:
            if nom.startswith("langues/"):         # langue.brut prend déjà le français pour chaque texte manquant
                messages.append(("sante.langue", {"fichier": nom, "code": nom[len("langues/"):-len(".json")]}))
            else:
                messages.append(("sante.fichier", {"fichier": nom}))
    except Exception:                           # noqa: BLE001
        from . import sur
        sur.noter_trace()
    return messages, n


def textes(messages):
    from .langue import t
    return [t(k, **p) for k, p in messages]


def commande(args=()):
    """tg verifier : tout regarder maintenant (même si rien n'a changé), et le dire."""
    from .langue import t
    messages, n = au_demarrage(forcer=True)
    lignes = textes(messages)
    if not any(k in ("sante.fichier", "sante.langue") for k, _ in messages):
        lignes.append(t("sante.ok", n=n))
    return "\n".join(lignes)
