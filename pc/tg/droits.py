"""Les droits Linux (r w x) des fichiers du terrain, pareils sur tous les ordinateurs (décision du 2 novembre).

Sous Linux et macOS, ce sont les vrais droits (os.stat, os.chmod, os.access). Sous Windows, les fichiers n'ont pas
de droits Linux : le terminal du jeu (vsh/) et le jeu les gardent ensemble dans ~/.terminagotchi/droits_terminal.json
(chmod 444 → le fichier passe aussi en « lecture seule » de Windows ; chmod +x → un script se lance avec ./).
Ainsi `chmod 444 nid/repas.txt`, `ls -l`, `./miam.sh` et les vérifications des leçons (cadenas, citadelle…) disent la
même chose partout. VIRTUELS vaut True sous Windows (les tests le règlent pour simuler Windows sous Linux).
"""
import json
import os
import stat
from pathlib import Path

VIRTUELS = os.name == "nt"


class Registre:
    """Les droits gardés dans un fichier JSON : {chemin (normcase, absolu) : mode}."""

    def __init__(self, fichier):
        self.fichier = Path(fichier)
        self._mtime = None
        self._d = {}

    def tout(self):
        try:
            m = self.fichier.stat().st_mtime_ns
        except OSError:
            self._mtime, self._d = None, {}
            return self._d
        if m != self._mtime:
            try:
                self._d = json.loads(self.fichier.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._d = {}
            self._mtime = m
        return self._d

    def sauver(self, d):
        try:
            self.fichier.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.fichier.with_suffix(".tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.fichier)
            self._d, self._mtime = d, self.fichier.stat().st_mtime_ns
        except OSError:
            pass

    def mode(self, p, st=None):
        st = st or os.stat(p)
        m = self.tout().get(cle(p))
        if m is not None:
            return m
        if stat.S_ISDIR(st.st_mode):
            return 0o755
        return 0o644 if st.st_mode & stat.S_IWRITE else 0o444

    def poser(self, p, m):
        d = dict(self.tout())
        d[cle(p)] = m & 0o7777
        self.sauver(d)
        try:
            if not os.path.isdir(p):
                _vrai_chmod(p, stat.S_IREAD if not (m & 0o222) else stat.S_IREAD | stat.S_IWRITE)
        except OSError:
            pass

    def oublier(self, p, dossier=False):
        d = self.tout()
        k = cle(p)
        nouveau = {x: v for x, v in d.items() if x != k and not (dossier and x.startswith(k.rstrip("\\/") + os.sep))}
        if len(nouveau) != len(d):
            self.sauver(nouveau)

    def deplacer(self, ancien, nouveau):
        d = self.tout()
        a, n = cle(ancien), cle(nouveau)
        r = {}
        chg = False
        for x, v in d.items():
            if x == a or x.startswith(a.rstrip("\\/") + os.sep):
                r[n + x[len(a):]] = v
                chg = True
            else:
                r[x] = v
        if chg:
            self.sauver(r)

    def acces(self, p, quoi):
        try:
            m = self.mode(p)
        except OSError:
            return False
        ok = True
        if quoi & os.R_OK:
            ok = ok and bool(m & 0o400)
        if quoi & os.W_OK:
            ok = ok and bool(m & 0o200)
        if quoi & os.X_OK:
            ok = ok and bool(m & 0o100)
        return ok


_REGISTRES = {}


def registre():
    from . import core
    f = str(Path(core.SAVE_DIR) / "droits_terminal.json")
    if f not in _REGISTRES:
        _REGISTRES[f] = Registre(f)
    return _REGISTRES[f]


def cle(p):
    try:
        return os.path.normcase(str(Path(p).resolve()))
    except OSError:
        return os.path.normcase(os.path.abspath(str(p)))


def mode(p, st=None):
    """Les droits (0o644…) d'un fichier ou dossier, tels que Linux les montrerait."""
    if not VIRTUELS:
        return stat.S_IMODE((st or os.stat(p)).st_mode)
    return registre().mode(p, st)


def poser(p, m):
    """chmod : les vrais droits sous Linux ; sous Windows, gardés à côté (et « lecture seule » si personne n'écrit)."""
    if not VIRTUELS:
        _vrai_chmod(p, m)
        return
    registre().poser(p, m)


def oublier(p, dossier=False):
    if VIRTUELS:
        registre().oublier(p, dossier)


def deplacer(ancien, nouveau):
    if VIRTUELS:
        registre().deplacer(ancien, nouveau)


def acces(p, quoi):
    """os.access(p, os.R_OK / os.W_OK / os.X_OK) avec les droits de Linux (pour l'utilisateur)."""
    if not VIRTUELS:
        return os.access(p, quoi)
    return registre().acces(p, quoi)


_vrai_chmod = os.chmod
_INSTALLE = [False]


def installer():
    """Sous Windows : chaque os.chmod / Path.chmod du jeu garde aussi les droits Linux (citadelle, crypte, forge…)."""
    if not VIRTUELS or _INSTALLE[0]:
        return
    _INSTALLE[0] = True

    def chmod(chemin, m, *a, **k):
        try:
            from . import core
            p = os.path.abspath(os.fspath(chemin))
            for base in (str(core.TERRAIN), str(core.SAVE_DIR)):
                b = os.path.abspath(base)
                if os.path.normcase(p) == os.path.normcase(b) or os.path.normcase(p).startswith(
                        os.path.normcase(b).rstrip("\\/") + os.sep):
                    if not os.path.normcase(p).endswith("droits_terminal.json"):
                        poser(p, m)
                        return None
        except Exception:                    # noqa: BLE001 — jamais bloquant
            pass
        return _vrai_chmod(chemin, m, *a, **k)
    os.chmod = chmod
