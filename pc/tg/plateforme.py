"""Détection du système, couleurs, clavier et piège anti copier-coller."""
import os
import platform
import sys
import time


def detect_os():
    s = platform.system()
    if s == "Windows":
        return "windows"
    if s == "Darwin":
        return "mac"
    if "TERMUX_VERSION" in os.environ or "ANDROID_ROOT" in os.environ:
        return "android"
    return "linux"


OSK = detect_os()


def detect_distro():
    """Famille de distribution Linux : (nom affiché, gestionnaire de paquets)."""
    if OSK != "linux":
        return None, None
    infos = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for l in f:
                if "=" in l:
                    k, v = l.rstrip().split("=", 1)
                    infos[k] = v.strip('"')
    except OSError:
        pass
    nom = infos.get("NAME", "Linux")
    familles = (infos.get("ID", "") + " " + infos.get("ID_LIKE", "")).lower().split()
    for cle, gest in (("fedora", "dnf"), ("rhel", "dnf"), ("centos", "dnf"), ("arch", "pacman"),
                      ("opensuse", "zypper"), ("suse", "zypper"), ("alpine", "apk"),
                      ("debian", "apt"), ("ubuntu", "apt")):
        if cle in familles:
            return nom, gest
    return nom, "apt"


DISTRO, GEST = detect_distro()
INSTALL = {"apt": "sudo apt install", "dnf": "sudo dnf install", "pacman": "sudo pacman -S",
           "zypper": "sudo zypper install", "apk": "sudo apk add"}


def installer(paquet, noms=None):
    """Commande d'installation adaptée au système (noms : paquet différent selon le gestionnaire)."""
    if IS_WIN:
        return f"winget install {paquet}"
    if OSK == "mac":
        return f"brew install {paquet}"
    if OSK == "android":
        return f"pkg install {paquet}"
    p = (noms or {}).get(GEST, paquet)
    return f"{INSTALL.get(GEST, 'sudo apt install')} {p}"
IS_WIN = OSK == "windows"
OS_NAMES = {"linux": "Linux", "mac": "macOS", "windows": "Windows", "android": "Android"}

if IS_WIN:
    os.system("")  # active les couleurs ANSI sous Windows 10+
    for stream in (sys.stdout, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def C(unix, win=None, mac=None, android=None):
    """Choisit la variante d'une commande pour le système courant."""
    if IS_WIN:
        return win if win is not None else unix
    if OSK == "mac" and mac is not None:
        return mac
    if OSK == "android" and android is not None:
        return android
    return unix


def shell_rc():
    return "~/.zshrc" if os.environ.get("SHELL", "").endswith("zsh") or OSK == "mac" else "~/.bashrc"


# ---------------------------------------------------------------- couleurs
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


THEME_ANSI = None       # le thème des couleurs du texte (apparence.activer) ; None = les couleurs d'origine


def fg(n):
    if THEME_ANSI is not None:
        from .apparence import ansi
        return ansi(n, THEME_ANSI)
    return f"\033[38;5;{n}m"


def bg(n):
    return f"\033[48;5;{n}m"


def clear():
    sys.stdout.write("\033[H\033[J")


# ---------------------------------------------------------------- anti copier-coller
# Les commandes affichées contiennent une lettre cyrillique identique à l'œil
# et des espaces insécables. Tapées à la main : aucun souci. Copiées-collées :
# la commande échoue et le Terminagotchi le voit dans l'historique.
HOMO = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
        "i": "і", "s": "ѕ", "d": "ԁ", "h": "һ", "j": "ј"}
NBSP = " "
PIEGES = set(HOMO.values()) | {NBSP}


def piege(cmd):
    out, fait = [], False
    for ch in cmd:
        if not fait and ch in HOMO:
            out.append(HOMO[ch])
            fait = True
        elif ch == " ":
            out.append(NBSP)
        else:
            out.append(ch)
    return "".join(out)


def est_colle(ligne):
    return any(c in PIEGES for c in ligne)


# ---------------------------------------------------------------- clavier
class Clavier:
    """Lecture d'une touche sans bloquer (Linux, macOS, Termux, Windows)."""

    def __init__(self):
        self.ok = sys.stdin.isatty()
        self.old = None

    def __enter__(self):
        self.brut()
        return self

    def __exit__(self, *a):
        self.normal()

    def brut(self):
        if self.ok and not IS_WIN and self.old is None:
            import termios
            import tty
            fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(fd)
            tty.setcbreak(fd)

    def normal(self):
        if self.old is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old)
            self.old = None

    def touche(self, delai):
        if not self.ok:
            time.sleep(delai)
            return None
        if IS_WIN:
            import msvcrt
            fin = time.time() + delai
            while time.time() < fin:
                if msvcrt.kbhit():
                    return msvcrt.getwch()
                time.sleep(0.05)
            return None
        import select
        r, _, _ = select.select([sys.stdin], [], [], delai)
        if not r:
            return None
        data = os.read(sys.stdin.fileno(), 16).decode("utf-8", "ignore")
        return data[:1] or None

    def lire(self, delai):
        """Comme touche(), mais renvoie tout ce qui a été tapé ou collé d'un coup."""
        if not self.ok:
            time.sleep(delai)
            return ""
        if IS_WIN:
            import msvcrt
            fin, out = time.time() + delai, ""
            while time.time() < fin and not out:
                while msvcrt.kbhit():
                    c = msvcrt.getwch()
                    if c in ("\x00", "\xe0"):        # touches spéciales (flèches…)
                        msvcrt.getwch()
                        continue
                    out += c
                if not out:
                    time.sleep(0.03)
            return out
        import select
        r, _, _ = select.select([sys.stdin], [], [], delai)
        if not r:
            return ""
        return os.read(sys.stdin.fileno(), 4096).decode("utf-8", "ignore")

    def demander(self, invite):
        self.normal()
        try:
            return input(invite)
        except EOFError:
            return ""
        finally:
            self.brut()
