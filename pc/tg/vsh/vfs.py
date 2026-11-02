"""Le terminal du jeu : les chemins qu'il montre (Linux) et les vrais fichiers derrière.

Deux façons de voir l'ordinateur :
  - « transparent » (Linux, macOS, et les tests) : un chemin du terminal EST le vrai chemin ;
  - « windows » : un petit Linux virtuel. / contient bin, dev, etc, home, proc, tmp, usr, var (en lecture seule,
    décrits ici) ; ~ = /home/<nom> ne montre que le terrain du jeu (~/terrain_terminagotchi, le VRAI dossier, où
    qu'il soit), ~/.terminagotchi (le vrai dossier du jeu) et ~/.bash_history (l'historique du terminal du jeu) ;
    /tmp est un vrai dossier rangé dans ~/.terminagotchi/tmp.
Dans les deux cas, on n'écrit QUE dans le terrain, ~/.terminagotchi (et /tmp du jeu) : ailleurs, « Permission denied »
(et l'explication du jeu). Sous Windows, les droits Linux (chmod 444, +x) n'existent pas : ils sont gardés dans
~/.terminagotchi/droits_terminal.json et respectés par le terminal du jeu (un fichier sans « w » ne s'écrit pas,
un script sans « x » ne se lance pas avec ./).
"""
import os
import posixpath
import stat
import time
from pathlib import Path


class ErreurFs(Exception):
    """Une erreur comme celles du vrai système : errno (2 = absent, 13 = refusé, 20 = pas un dossier…)."""

    MESSAGES = {2: "No such file or directory", 13: "Permission denied", 17: "File exists", 20: "Not a directory",
                21: "Is a directory", 39: "Directory not empty", 22: "Invalid argument", 18: "Invalid cross-device link",
                30: "Read-only file system", 1: "Operation not permitted"}

    def __init__(self, errno, texte=None):
        super().__init__(texte or self.MESSAGES.get(errno, "Error"))
        self.errno = errno
        self.texte = texte or self.MESSAGES.get(errno, "Error")


def depuis_oserror(e):
    import errno as E
    n = e.errno or 0
    if isinstance(e, PermissionError):
        n = 13
    elif isinstance(e, FileNotFoundError):
        n = 2
    elif isinstance(e, FileExistsError):
        n = 17
    elif isinstance(e, NotADirectoryError):
        n = 20
    elif isinstance(e, IsADirectoryError):
        n = 21
    elif n in (E.ENOTEMPTY, 41, 145):          # (Windows : ERROR_DIR_NOT_EMPTY = 145)
        n = 39
    return ErreurFs(n)


# ---------------------------------------------------------------- les lieux virtuels (mode windows)
class VDossier:
    def __init__(self, entrees=None, mode=0o755, proprio="root"):
        self.entrees = entrees if entrees is not None else {}
        self.mode, self.proprio = mode, proprio


class VFichier:
    def __init__(self, contenu, mode=0o644, proprio="root"):
        self.contenu, self.mode, self.proprio = contenu, mode, proprio

    def octets(self):
        c = self.contenu() if callable(self.contenu) else self.contenu
        return c.encode("utf-8") if isinstance(c, str) else c


class Montage:
    """Un vrai dossier (ou fichier) montré à cet endroit."""

    def __init__(self, reel, ecriture=True):
        self.reel, self.ecriture = Path(reel), ecriture


class Infos:
    """Ce que montre `ls -l` / `stat` : type, droits, liens, propriétaire, taille, date."""

    def __init__(self, dossier, mode, taille, mtime, proprio, groupe, liens=1, inode=0, blocs=None):
        self.dossier, self.mode, self.taille, self.mtime = dossier, mode, taille, mtime
        self.proprio, self.groupe, self.liens, self.inode = proprio, groupe, liens, inode
        self.blocs = blocs if blocs is not None else ((taille + 4095) // 4096) * 8

    @property
    def st_mode(self):
        return (stat.S_IFDIR if self.dossier else stat.S_IFREG) | self.mode


class Vfs:
    def __init__(self, mode=None, home=None, terrain=None, jeu=None, utilisateur=None, zones=None):
        from .. import core
        self.mode = mode or os.environ.get("TG_VSH_MODE") or ("windows" if os.name == "nt" else "transparent")
        self.home_reel = Path(home or Path.home())
        self.terrain_reel = Path(terrain or core.TERRAIN)
        self.jeu_reel = Path(jeu or core.SAVE_DIR)
        self.utilisateur = utilisateur or nom_utilisateur()
        if self.mode == "windows":
            self.home = f"/home/{self.utilisateur}"
            self.tmp_reel = self.jeu_reel / "tmp"
            self.sys_reel = self.jeu_reel / "systeme"     # /, /etc, /bin… : de vrais fichiers, en lecture seule
            try:
                self.tmp_reel.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        else:
            self.home = self.home_reel.as_posix()
            self.tmp_reel = None
            self.sys_reel = None
        # les vrais dossiers où le terminal peut écrire
        self.zones = [Path(z) for z in (zones or [self.terrain_reel, self.jeu_reel])]
        if self.tmp_reel:
            self.zones.append(self.tmp_reel)
        self._droits = None
        self._racine = None
        self.fd = {}                         # /dev/fd/63… : les <( ) (substitution de processus)
        self.commandes = lambda: []          # rempli par le shell (pour /bin)

    # ------------------------------------------------ les droits gardés (Windows) : droits.py
    def registre(self):
        if self._droits is None:
            from ..droits import Registre
            self._droits = Registre(self.jeu_reel / "droits_terminal.json")
        return self._droits

    def poser_mode(self, reel, m):
        if self.mode == "transparent":
            os.chmod(reel, m)
            return
        self.registre().poser(reel, m)

    def oublier_mode(self, reel, dossier=False):
        if self.mode != "transparent":
            self.registre().oublier(reel, dossier)

    def deplacer_mode(self, ancien, nouveau):
        if self.mode != "transparent":
            self.registre().deplacer(ancien, nouveau)

    def mode_reel(self, reel, st=None):
        """Les droits (sans le type) d'un vrai fichier, tels que le terminal les montre."""
        st = st or os.stat(reel)
        if self.mode == "transparent":
            return stat.S_IMODE(st.st_mode)
        return self.registre().mode(reel, st)

    # ------------------------------------------------ chemins
    def normaliser(self, cwd, chemin):
        """Le chemin absolu du terminal (/…) pour `chemin` tapé depuis `cwd` (~ remplacé)."""
        if chemin == "~" or chemin.startswith("~/"):
            chemin = self.home + chemin[1:]
        if not chemin.startswith("/"):
            chemin = posixpath.join(cwd, chemin)
        p = posixpath.normpath(chemin)
        if p.startswith("//"):
            p = "/" + p.lstrip("/")
        return p

    def preparer_systeme(self, commandes=(), pid=None):
        """Windows : les lieux du système (/bin, /etc, /proc, /var/log…) deviennent de vrais petits fichiers rangés
        dans ~/.terminagotchi/systeme (le terminal les montre en lecture seule ; le jeu peut les vérifier comme sous
        Linux : cd /, ls /bin, cat /etc/hostname, ls -l /etc/hostname)."""
        if self.mode != "windows":
            return
        u = self.utilisateur
        b = self.sys_reel
        fichiers = {
            "etc/hostname": nom_machine() + "\n", "etc/os-release": OS_RELEASE,
            "etc/passwd": f"root:x:0:0:root:/root:/bin/sh\n{u}:x:1000:1000:{u}:/home/{u}:/bin/sh\n",
            "etc/group": f"root:x:0:\n{u}:x:1000:\n", "etc/shells": "/bin/sh\n/bin/bash\n",
            "proc/version": PROC_VERSION, "proc/cpuinfo": _cpuinfo(), "proc/meminfo": _meminfo(),
            "proc/uptime": _uptime(), "proc/self/status": "Name:\tsh\nState:\tR (running)\n",
            "dev/null": "", "dev/zero": "", "dev/tty": "", "dev/urandom": "", "dev/random": "",
            "var/log/syslog": "(le journal du système : seul root, le gardien, peut le lire)\n",
            "var/log/terminal_du_jeu.log": _journal_jeu(),
        }
        if pid:                                       # /proc/$$ : le shell du terminal du jeu
            fichiers[f"proc/{pid}/status"] = f"Name:\tbash\nState:\tS (sleeping)\nPid:\t{pid}\nPPid:\t1\nUid:\t1000\n"
            fichiers[f"proc/{pid}/cmdline"] = "bash\0"
            fichiers[f"proc/{pid}/comm"] = "bash\n"
        try:
            for d in ("bin", "usr/bin", "usr/share", "root", "home", "tmp", "var/log", "proc/self"):
                (b / d).mkdir(parents=True, exist_ok=True)
            for rel, texte in fichiers.items():
                p = b / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if p.read_text(encoding="utf-8") == texte:
                        continue
                except OSError:
                    pass
                p.write_text(texte, encoding="utf-8", newline="\n")
            for d in ("bin", "usr/bin"):
                deja = set(os.listdir(b / d))
                for n in commandes:
                    if n not in deja and "/" not in n and n not in (".", ".."):
                        (b / d / n).write_bytes(b"")
        except OSError:
            pass

    def _rel_systeme(self, reel):
        """Le chemin relatif dans le système (etc/hostname), ou None si reel n'y est pas."""
        if self.sys_reel is None:
            return None
        r = os.path.normcase(os.path.abspath(str(reel)))
        b = os.path.normcase(os.path.abspath(str(self.sys_reel)))
        if r == b:
            return ""
        if r.startswith(b.rstrip("\\/") + os.sep):
            return os.path.abspath(str(reel))[len(b.rstrip("\\/")) + 1:].replace("\\", "/")
        return None

    @staticmethod
    def _mode_systeme(rel, dossier):
        if rel == "root":
            return 0o700
        if rel == "tmp":
            return 0o1777
        if dossier:
            return 0o755
        if rel.startswith(("bin/", "usr/bin/")):
            return 0o755
        if rel == "var/log/syslog":
            return 0o640
        if rel.startswith("dev/"):
            return 0o666
        return 0o644

    def _maison(self):
        return VDossier({"terrain_terminagotchi": Montage(self.terrain_reel),
                         ".terminagotchi": Montage(self.jeu_reel),
                         ".bash_history": Montage(self.jeu_reel / "historique_terminal")}, proprio=self.utilisateur)

    def trouver(self, vp):
        """("reel", Path) | ("virt", nœud) | None pour un chemin absolu du terminal."""
        if vp in self.fd:
            return ("virt", VFichier(self.fd[vp], 0o600))
        if self.mode == "transparent":
            return ("reel", Path(vp))
        parts = [x for x in vp.split("/") if x]
        if not parts:
            return ("reel", self.sys_reel)
        if parts[0] == "tmp":
            return ("reel", self.tmp_reel.joinpath(*parts[1:]))
        if parts[0] == "home" and len(parts) > 1:
            if parts[1] != self.utilisateur:
                return None
            maison = self._maison()
            if len(parts) == 2:
                return ("virt", maison)
            m = maison.entrees.get(parts[2])
            if m is None:
                return None
            return ("reel", m.reel.joinpath(*parts[3:]))
        return ("reel", self.sys_reel.joinpath(*parts))

    def reel(self, vp):
        r = self.trouver(vp)
        return r[1] if r and r[0] == "reel" else None

    def virtuel(self, reel):
        """Le chemin du terminal d'un vrai chemin (None s'il n'est pas visible)."""
        if self.mode == "transparent":
            return Path(reel).as_posix()
        r = os.path.normcase(os.path.abspath(str(reel)))
        rs = self._rel_systeme(reel)
        if rs is not None:
            return "/" + rs if rs else "/"
        for base, v in ((self.terrain_reel, self.home + "/terrain_terminagotchi"),
                        (self.tmp_reel, "/tmp"),
                        (self.jeu_reel, self.home + "/.terminagotchi")):
            if base is None:
                continue
            b = os.path.normcase(os.path.abspath(str(base)))
            if r == b:
                return v
            if r.startswith(b.rstrip("\\/") + os.sep):
                reste = os.path.abspath(str(reel))[len(b.rstrip("\\/")) + 1:]
                return v + "/" + reste.replace("\\", "/")
        if os.path.normcase(os.path.abspath(str(self.home_reel))) == r:
            return self.home
        return None

    def pour_le_jeu(self, vp):
        """Le dossier tel que le jeu le comprend (ses vérifications travaillent sur les vrais chemins) : le vrai
        dossier ; ~ = le vrai dossier personnel ; /, /etc… = les vrais petits fichiers de ~/.terminagotchi/systeme."""
        if self.mode == "transparent":
            return vp
        if vp == self.home:
            return str(self.home_reel)
        r = self.reel(vp)
        if r is not None:
            return str(r)
        return str(self.sys_reel.joinpath(*[x for x in vp.split("/") if x]))

    def ecriture_permise(self, vp):
        if self.mode == "windows":
            t = self.trouver(vp)
            if t is None:
                parent = posixpath.dirname(vp)
                t = self.trouver(parent)
                if t is None:
                    return False
                if t[0] == "reel":
                    t = ("reel", t[1] / posixpath.basename(vp))
            if t[0] != "reel":
                return False
            r = t[1]
        else:
            r = Path(vp)
        try:
            rr = os.path.normcase(os.path.abspath(str(r)))
        except OSError:
            return False
        if self._rel_systeme(r) is not None:          # les lieux du système : en lecture seule
            return False
        for z in self.zones:
            zz = os.path.normcase(os.path.abspath(str(z)))
            if rr == zz or rr.startswith(zz.rstrip("\\/") + os.sep):
                return True
        return False

    # ------------------------------------------------ lire l'arborescence
    def existe(self, vp):
        t = self.trouver(vp)
        if t is None:
            return False
        if t[0] == "reel":
            return os.path.lexists(t[1])
        return True

    def est_dossier(self, vp):
        t = self.trouver(vp)
        if t is None:
            return False
        if t[0] == "reel":
            return os.path.isdir(t[1])
        return isinstance(t[1], VDossier)

    def est_fichier(self, vp):
        t = self.trouver(vp)
        if t is None:
            return False
        if t[0] == "reel":
            return os.path.isfile(t[1])
        return isinstance(t[1], VFichier)

    def infos(self, vp):
        t = self.trouver(vp)
        if t is None:
            raise ErreurFs(2)
        if t[0] == "reel":
            try:
                st = os.stat(t[1])
            except OSError as e:
                raise depuis_oserror(e)
            d = stat.S_ISDIR(st.st_mode)
            if self.mode == "transparent":
                return Infos(d, stat.S_IMODE(st.st_mode), st.st_size, st.st_mtime, _nom_uid(st.st_uid),
                             _nom_gid(st.st_gid), st.st_nlink, st.st_ino, getattr(st, "st_blocks", None))
            liens = 1
            if d:
                try:
                    liens = 2 + sum(1 for e in os.scandir(t[1]) if e.is_dir(follow_symlinks=False))
                except OSError:
                    liens = 2
            rs = self._rel_systeme(t[1])
            if rs is not None:
                if rs == "home":
                    liens = 3
                return Infos(d, self._mode_systeme(rs, d), 4096 if d else st.st_size, st.st_mtime, "root", "root",
                             liens, st.st_ino)
            return Infos(d, self.mode_reel(t[1], st), 4096 if d else st.st_size, st.st_mtime, self.utilisateur,
                         self.utilisateur, liens, st.st_ino)
        n = t[1]
        if isinstance(n, VDossier):
            nb = sum(1 for x in n.entrees.values() if isinstance(x, VDossier) or
                     (isinstance(x, Montage) and x.reel.is_dir()))
            return Infos(True, n.mode, 4096, _DEMARRAGE, n.proprio, n.proprio, 2 + nb)
        o = n.octets()
        return Infos(False, n.mode, len(o), _DEMARRAGE, n.proprio, n.proprio, 1)

    def lister(self, vp):
        """Les noms d'un dossier (sans . ni ..)."""
        t = self.trouver(vp)
        if t is None:
            raise ErreurFs(2)
        if t[0] == "reel":
            if not os.path.isdir(t[1]):
                raise ErreurFs(20 if os.path.exists(t[1]) else 2)
            rs = self._rel_systeme(t[1])
            if rs is not None:
                if not self._mode_systeme(rs, True) & 0o004:
                    raise ErreurFs(13)
                if rs == "home":
                    return [self.utilisateur]
            elif self.mode == "windows" and not self.mode_reel(t[1]) & 0o400:
                raise ErreurFs(13)
            try:
                return os.listdir(t[1])
            except OSError as e:
                raise depuis_oserror(e)
        if not isinstance(t[1], VDossier):
            raise ErreurFs(20)
        if not t[1].mode & 0o004 and t[1].proprio != self.utilisateur:
            raise ErreurFs(13)
        return [k for k, v in t[1].entrees.items() if not (isinstance(v, Montage) and not os.path.exists(v.reel))]

    def lire(self, vp):
        t = self.trouver(vp)
        if t is None:
            raise ErreurFs(2)
        if vp in ("/dev/urandom", "/dev/random"):
            return os.urandom(1 << 16)
        if vp == "/dev/zero":
            return bytes(1 << 16)
        if t[0] == "reel":
            if os.path.isdir(t[1]):
                raise ErreurFs(21)
            rs = self._rel_systeme(t[1])
            if rs is not None and not self._mode_systeme(rs, False) & 0o004:
                raise ErreurFs(13)
            if rs is None and self.mode == "windows" and os.path.exists(t[1]) and not self.mode_reel(t[1]) & 0o400:
                raise ErreurFs(13)
            try:
                with open(t[1], "rb") as f:
                    if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                        return f.read(1 << 20)          # un fichier spécial (/dev/…, /proc/…) : un morceau
                    return f.read()
            except OSError as e:
                raise depuis_oserror(e)
        if isinstance(t[1], VDossier):
            raise ErreurFs(21)
        if not t[1].mode & 0o004 and t[1].proprio != self.utilisateur:
            raise ErreurFs(13)
        return t[1].octets()

    # ------------------------------------------------ écrire (seulement dans les zones du jeu)
    def _reel_ecrivable(self, vp, creer=True):
        if vp in ("/dev/null", "/dev/tty", "/dev/stdout", "/dev/stderr"):
            return None
        if not self.ecriture_permise(vp):
            raise ErreurFs(13)
        t = self.trouver(vp)
        if t is None:
            p = self.trouver(posixpath.dirname(vp))
            if p is None or p[0] != "reel":
                raise ErreurFs(2)
            return p[1] / posixpath.basename(vp)
        return t[1]

    def _verifier_ecriture_fichier(self, r):
        if self.mode == "windows" and os.path.exists(r) and not self.mode_reel(r) & 0o200:
            raise ErreurFs(13)

    def _verifier_dossier_parent(self, r):
        if self.mode == "windows":
            p = Path(r).parent
            if p.exists() and not self.mode_reel(p) & 0o200:
                raise ErreurFs(13)

    def ecrire(self, vp, donnees, ajout=False):
        if vp in ("/dev/null", "/dev/zero"):
            return
        r = self._reel_ecrivable(vp)
        if r is None:
            return
        if os.path.isdir(r):
            raise ErreurFs(21)
        self._verifier_ecriture_fichier(r)
        if not os.path.exists(r):
            self._verifier_dossier_parent(r)
        try:
            with open(r, "ab" if ajout else "wb") as f:
                f.write(donnees)
        except OSError as e:
            raise depuis_oserror(e)

    def toucher(self, vp):
        r = self._reel_ecrivable(vp)
        if r is None:
            return
        if os.path.exists(r):
            try:
                os.utime(r, None)
            except OSError as e:
                raise depuis_oserror(e)
            return
        self._verifier_dossier_parent(r)
        try:
            with open(r, "ab"):
                pass
        except OSError as e:
            raise depuis_oserror(e)

    def creer_dossier(self, vp):
        if self.existe(vp):
            raise ErreurFs(17)
        r = self._reel_ecrivable(vp)
        self._verifier_dossier_parent(r)
        try:
            os.mkdir(r)
        except OSError as e:
            raise depuis_oserror(e)

    def supprimer_fichier(self, vp):
        r = self._reel_ecrivable(vp, creer=False)
        if r is None:
            raise ErreurFs(13)
        if os.path.isdir(r) and not os.path.islink(r):
            raise ErreurFs(21)
        self._verifier_dossier_parent(r)
        try:
            if os.name == "nt":
                try:
                    os.chmod(r, stat.S_IREAD | stat.S_IWRITE)      # rm d'un fichier en lecture seule : permis sous Linux
                except OSError:
                    pass
            os.unlink(r)
        except OSError as e:
            raise depuis_oserror(e)
        self.oublier_mode(r)

    def supprimer_dossier(self, vp):
        r = self._reel_ecrivable(vp, creer=False)
        if r is None:
            raise ErreurFs(13)
        if not os.path.isdir(r):
            raise ErreurFs(20)
        self._verifier_dossier_parent(r)
        try:
            os.rmdir(r)
        except OSError as e:
            raise depuis_oserror(e)
        self.oublier_mode(r, dossier=True)

    def renommer(self, vp_a, vp_b):
        a = self._reel_ecrivable(vp_a)
        b = self._reel_ecrivable(vp_b)
        self._verifier_dossier_parent(a)
        self._verifier_dossier_parent(b)
        try:
            if os.name == "nt" and os.path.exists(b) and not os.path.isdir(b):
                os.chmod(b, stat.S_IREAD | stat.S_IWRITE)
                os.replace(a, b)
            else:
                os.replace(a, b) if not os.path.isdir(b) else os.rename(a, b)
        except OSError as e:
            raise depuis_oserror(e)
        self.deplacer_mode(a, b)

    def chmod(self, vp, m):
        r = self._reel_ecrivable(vp, creer=False)
        if r is None or not os.path.exists(r):
            raise ErreurFs(2)
        try:
            self.poser_mode(r, m)
        except OSError as e:
            raise depuis_oserror(e)

    def poser_date(self, vp, quand):
        r = self._reel_ecrivable(vp)
        try:
            os.utime(r, (quand, quand))
        except OSError as e:
            raise depuis_oserror(e)


_DEMARRAGE = time.time()
OS_RELEASE = ('NAME="Terminagotchi"\nPRETTY_NAME="Le terminal du jeu Terminagotchi (Linux virtuel)"\nID=terminagotchi\n'
              'ID_LIKE=linux\nVERSION_ID="1"\nHOME_URL="https://terminagotchi.fr"\n')
PROC_VERSION = "Linux version 6.0.0-terminagotchi (le terminal du jeu, un Linux virtuel écrit en Python)\n"


def nom_utilisateur():
    import getpass
    try:
        u = getpass.getuser()
    except Exception:                       # noqa: BLE001
        u = "explorateur"
    u = (u or "explorateur").strip().lower().replace(" ", "_")
    return u or "explorateur"


def nom_machine():
    import platform
    return (platform.node() or "terminagotchi").split(".")[0].lower()


def _cpuinfo():
    n = os.cpu_count() or 1
    return "".join(f"processor\t: {i}\nmodel name\t: {_processeur()}\n\n" for i in range(n))


def _processeur():
    import platform
    return platform.processor() or "processeur"


def _meminfo():
    total = _memoire_totale()
    return f"MemTotal:       {total // 1024} kB\n" if total else ""


def _memoire_totale():
    if os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.ullTotalPhys)
        except Exception:                   # noqa: BLE001
            return 0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return 0


def _uptime():
    return f"{time.time() - _DEMARRAGE:.2f} 0.00\n"


def _journal_jeu():
    from .. import core
    try:
        st = core.load() or {}
        return "".join(l + "\n" for l in st.get("log", [])[-20:])
    except Exception:                       # noqa: BLE001
        return ""


def _nom_uid(uid):
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return str(uid)


def _nom_gid(gid):
    try:
        import grp
        return grp.getgrgid(gid).gr_name
    except (ImportError, KeyError):
        return str(gid)


# ---------------------------------------------------------------- le jeu et les chemins du terminal (Windows)
_VFS_JEU = {}


def vfs_du_jeu():
    """Le Linux virtuel tel que le voit le terminal du jeu (même terrain, même dossier du jeu)."""
    from .. import core
    cle = (str(core.TERRAIN), str(core.SAVE_DIR), str(Path.home()))
    if cle not in _VFS_JEU:
        _VFS_JEU.clear()
        _VFS_JEU[cle] = Vfs(mode="windows")
    return _VFS_JEU[cle]


def reel_depuis_terminal(cur_reel, arg):
    """Windows : le vrai dossier où mène `cd arg` tapé dans le terminal du jeu depuis cur_reel (un vrai chemin)."""
    v = vfs_du_jeu()
    cv = v.virtuel(cur_reel) if cur_reel else None
    vp = v.normaliser(cv or v.home, arg)
    return v.pour_le_jeu(vp)


def vers_terminal(reel):
    """Windows : comment le terminal du jeu écrit ce vrai chemin (/home/lea/terrain_terminagotchi/…)."""
    return vfs_du_jeu().virtuel(reel) or str(reel)
