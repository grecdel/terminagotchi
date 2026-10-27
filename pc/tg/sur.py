"""Sûreté : le jeu n'écrit jamais hors de ses deux lieux, même à travers un lien symbolique.

Le jeu écrit à deux endroits seulement : la zone d'aventure (~/terrain_terminagotchi) et son dossier de réglages
(~/.terminagotchi). Un enfant curieux (ou un ado farceur) peut y glisser un lien symbolique vers l'extérieur
(`ln -s ~/Documents ~/terrain_terminagotchi`, `nid/repas.txt` → un fichier ailleurs, `carnet` → un vrai projet git) :
le jeu écrirait alors à travers le lien, hors de la zone.

Garde-fou (installer() au démarrage du module) : un « crochet d'audit » Python (sys.addaudithook) voit TOUTES les
écritures du processus (open en écriture, mkdir, rename/replace, remove, chmod, symlink, link, truncate, utime).
Pour un chemin qui est (lexicalement) dans un des deux lieux, chaque élément du chemin, du lieu jusqu'au fichier,
doit être un vrai dossier / fichier, pas un lien (sinon : HorsZone, une PermissionError, et rien n'est écrit) :
  - zone d'aventure : la zone elle-même ne doit pas être un lien ;
  - ~/.terminagotchi : le dossier lui-même peut être un lien (choix de l'adulte : dossier synchronisé),
    mais rien de ce qu'il contient ;
  - le dernier élément peut être un lien seulement pour l'enlever ou le remplacer (unlink, rename : c'est le lien
    qui part, jamais sa cible).
Les écritures refusées sont notées (ALERTES) : la créature explique, une fois, quel lien gêne et comment l'enlever.

ouvrir_nofollow() : l'écriture de la sauvegarde ouvre aussi le fichier avec O_NOFOLLOW (défense en profondeur).
depot_git_sur() : le jeu ne règle git (git config, git init) que dans le carnet de la zone, après avoir vérifié
que c'est vraiment un dépôt À LUI (pas un lien vers un autre projet, pas un fichier .git qui renvoie ailleurs).
"""
import errno
import os
import sys
import time

ALERTES = []            # chemins refusés depuis le dernier tour de jeu (vidé par alertes())
_INSTALLE = [False]
_DANS_CROCHET = [False]


class HorsZone(PermissionError):
    """Écriture refusée : le chemin passe par un lien symbolique, ou sort de la zone."""

    def __init__(self, chemin, lien):
        super().__init__(errno.EPERM, "lien symbolique : le jeu n'écrit pas à travers", str(chemin))
        self.lien = str(lien)


def _lieux():
    """(racine, la racine peut-elle être un lien ?) pour la zone d'aventure et le dossier du jeu."""
    from . import core
    return ((os.path.abspath(str(core.TERRAIN)), False), (os.path.abspath(str(core.SAVE_DIR)), True))


def _sous(p, base):
    return p == base or p.startswith(base.rstrip(os.sep) + os.sep)


def lien_genant(chemin, dernier_lien_ok=False):
    """Le premier lien symbolique sur le chemin (dans un des lieux du jeu), sinon None.
    Un chemin hors des deux lieux n'est pas concerné (None)."""
    p = os.path.abspath(os.fspath(chemin))
    for base, racine_lien_ok in _lieux():
        if not _sous(p, base):
            continue
        cur = base
        rel = os.path.relpath(p, base)
        parts = [] if rel == "." else rel.split(os.sep)
        if not racine_lien_ok and os.path.islink(cur) and (parts or not dernier_lien_ok):
            return cur                                   # (enlever ou remplacer le lien de la zone lui-même : permis)
        for i, part in enumerate(parts):
            cur = os.path.join(cur, part)
            if i == len(parts) - 1 and dernier_lien_ok:
                break
            if os.path.islink(cur):
                return cur
        return None
    return None


def sur(chemin):
    """Vrai si le jeu peut écrire ce chemin (aucun lien sur le chemin, dans les lieux du jeu)."""
    try:
        return lien_genant(chemin) is None
    except (OSError, ValueError):
        return False


def _refuser(chemin, dernier_lien_ok=False):
    lien = lien_genant(chemin, dernier_lien_ok)
    if lien is not None:
        if lien not in ALERTES:
            ALERTES.append(lien)
        raise HorsZone(chemin, lien)


_ECRIT = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def _sans_fd(fd):
    return fd is None or fd == -1                      # -1 : pas de dir_fd (CPython l'écrit ainsi dans l'audit)


def _crochet(evt, args):
    if _DANS_CROCHET[0]:
        return
    try:
        if evt == "open":
            chemin, mode, flags = args
            if isinstance(chemin, int) or chemin is None:
                return
            if mode is not None and any(c in str(mode) for c in "wax+"):
                ecrit = True
            else:
                ecrit = bool((flags or 0) & _ECRIT)
            if not ecrit:
                return
            verif = [(chemin, False)]
        elif evt == "os.truncate":
            if isinstance(args[0], int):
                return
            verif = [(args[0], False)]
        elif evt in ("os.mkdir", "os.chmod", "os.utime", "os.chown"):
            if isinstance(args[0], int) or not _sans_fd(args[-1]):
                return
            verif = [(args[0], False)]
        elif evt in ("os.remove", "os.rmdir"):
            if not _sans_fd(args[-1]):
                return                                   # shutil.rmtree (par dossier ouvert) : ne suit pas les liens
            verif = [(args[0], True)]
        elif evt == "os.rename":
            if not (_sans_fd(args[2]) and _sans_fd(args[3])):
                return
            verif = [(args[0], True), (args[1], True)]
        elif evt in ("os.symlink", "os.link"):
            verif = [(args[1], False)]
        else:
            return
    except (TypeError, ValueError, IndexError):
        return
    _DANS_CROCHET[0] = True
    try:
        for c, dernier in verif:
            try:
                c = os.fsdecode(c)
            except TypeError:
                continue
            _refuser(c, dernier)
    finally:
        _DANS_CROCHET[0] = False


def installer():
    """Pose le crochet (une fois par processus ; il ne peut pas être retiré, c'est voulu)."""
    if not _INSTALLE[0]:
        sys.addaudithook(_crochet)
        _INSTALLE[0] = True


def ouvrir_nofollow(chemin, flags=os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o600):
    """os.open sans suivre un lien au dernier élément (O_NOFOLLOW quand le système l'a)."""
    _refuser(chemin)
    return os.open(chemin, flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), mode)


def depot_git_sur(depot):
    """Vrai si `depot` est un dépôt git du jeu : dans la zone, sans lien sur le chemin, avec un VRAI dossier .git
    (pas un fichier « gitdir: … » qui renverrait vers un autre projet), et git le voit bien comme sa propre racine."""
    import subprocess
    depot = os.path.abspath(os.fspath(depot))
    g = os.path.join(depot, ".git")
    if not sur(depot) or not os.path.isdir(depot) or os.path.islink(g) or not os.path.isdir(g):
        return False
    try:
        for f in ("config", "HEAD"):
            if os.path.islink(os.path.join(g, f)):
                return False
        r = subprocess.run(["git", "-C", depot, "rev-parse", "--show-toplevel", "--absolute-git-dir"],
                           capture_output=True, text=True, timeout=10)
        lignes = r.stdout.strip().splitlines()
        if r.returncode != 0 or len(lignes) != 2:
            return False
        return os.path.realpath(lignes[0]) == os.path.realpath(depot) and \
            os.path.realpath(lignes[1]) == os.path.realpath(g)
    except (OSError, subprocess.SubprocessError):
        return False


def relatif(chemin):
    """Le chemin pour l'enfant : ~/… quand il est dans le HOME."""
    from pathlib import Path
    h = str(Path.home())
    c = str(chemin)
    return "~" + c[len(h):] if _sous(c, h) else c


def alertes(state):
    """Après un tour de jeu : la créature explique (une fois toutes les 10 min par lien) les écritures refusées."""
    from . import core
    from .langue import t
    vus = state.setdefault("sur_dit", {})
    now = time.time()
    for k in [k for k, v in vus.items() if now - v > 3600]:
        del vus[k]
    while ALERTES:
        lien = ALERTES.pop(0)
        if now - vus.get(lien, 0) < 600:
            continue
        vus[lien] = now
        try:
            cible = os.readlink(lien)
        except OSError:
            cible = "?"
        r = relatif(lien)
        core.say(state, t("core.sur.lien", lien=r, cible=cible, cmd=f"rm {r}"), 16)
        core.say(state, t("core.sur.lien.adulte", lien=r), 16)


def message_os(e):
    """Une erreur du système (droits retirés, disque plein…) dite gentiment, sans trace Python."""
    from .langue import t
    chemin = relatif(getattr(e, "filename", None) or "?")
    if isinstance(e, HorsZone):
        return t("core.sur.lien.court", lien=relatif(e.lien))
    if isinstance(e, PermissionError) or getattr(e, "errno", None) in (errno.EACCES, errno.EPERM):
        brut = getattr(e, "filename", None)
        droits = "u+rwx" if brut and os.path.isdir(brut) else "u+rw"
        return t("core.sur.droits", chemin=chemin, cmd=f"chmod {droits} {chemin}")
    if getattr(e, "errno", None) in (errno.ENOSPC, errno.EFBIG, errno.EDQUOT if hasattr(errno, "EDQUOT") else -1):
        return t("core.sur.plein", chemin=chemin)
    return t("core.sur.systeme", chemin=chemin, erreur=getattr(e, "strerror", None) or str(e))


def noter_trace():
    """Une erreur imprévue : la trace va dans ~/.terminagotchi/erreurs.log (pour un adulte), pas à l'écran."""
    import traceback
    from . import core
    try:
        core.SAVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(core.SAVE_DIR / "erreurs.log", "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
        return str(core.SAVE_DIR / "erreurs.log")
    except OSError:
        return None
