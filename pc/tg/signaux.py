"""Les signaux ANONYMES dont la créature du bureau a besoin, et rien d'autre.

Ce que le bureau a le droit de savoir :
  - inactivite() : depuis combien de secondes personne n'a touché l'ordinateur (un nombre, donné par le système :
    le moniteur d'inactivité de GNOME, l'économiseur d'écran de KDE / freedesktop, l'extension X « MIT-SCREEN-SAVER »,
    GetLastInputInfo sous Windows, HIDIdleTime sous macOS) ;
  - batterie() : le pourcentage et « sur secteur ou non » ;
  - discret() : l'ordinateur demande de ne pas déranger (« Ne pas déranger » de GNOME, mode présentation ou jeu plein
    écran de Windows), pour que l'île ne s'ouvre pas toute seule.
Ce qu'il ne fait JAMAIS : lire le clavier ou la souris (touches, texte tapé, position hors de ses fenêtres), lire le
titre ou le contenu d'une fenêtre, savoir quelle application est ouverte, faire des captures d'écran.
pc/outils/test_bureau.py vérifie dans le code qu'aucune de ces fonctions n'est appelée.

Chaque fonction rend None quand elle ne sait pas (le bureau fait alors comme si l'ordinateur était utilisé).
"""
import ctypes
import glob
import os
import re
import subprocess
import sys

_CACHE = {}


def _sortie(cmd, delai=2.0):
    try:
        r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=delai, check=False)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# ---------------------------------------------------------------- inactivité
def _gdbus(dest, chemin, methode):
    o = _sortie(["gdbus", "call", "--session", "--dest", dest, "--object-path", chemin, "--method", methode])
    if o is None:
        return None
    m = re.search(r"(\d+)", o)
    return int(m.group(1)) if m else None


def _inactivite_gnome():
    ms = _gdbus("org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core",
                "org.gnome.Mutter.IdleMonitor.GetIdletime")
    return None if ms is None else ms / 1000


def _inactivite_freedesktop():
    ms = _gdbus("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver.GetSessionIdleTime")
    return None if ms is None else ms / 1000


class _XSSInfo(ctypes.Structure):
    _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int), ("kind", ctypes.c_int),
                ("til_or_since", ctypes.c_ulong), ("idle", ctypes.c_ulong), ("eventMask", ctypes.c_ulong)]


def _inactivite_x11():
    """Le compteur d'inactivité de l'extension MIT-SCREEN-SAVER (un nombre de millisecondes, rien d'autre)."""
    if not os.environ.get("DISPLAY"):
        return None
    if "x11" not in _CACHE:
        try:
            x = ctypes.cdll.LoadLibrary("libX11.so.6")
            xss = ctypes.cdll.LoadLibrary("libXss.so.1")
            x.XOpenDisplay.restype = ctypes.c_void_p
            x.XDefaultRootWindow.restype = ctypes.c_ulong
            x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XSSInfo)
            xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_XSSInfo)]
            d = x.XOpenDisplay(None)
            _CACHE["x11"] = (x, xss, d, xss.XScreenSaverAllocInfo()) if d else None
        except (OSError, AttributeError):
            _CACHE["x11"] = None
    v = _CACHE["x11"]
    if not v:
        return None
    x, xss, d, info = v
    if not xss.XScreenSaverQueryInfo(d, x.XDefaultRootWindow(d), info):
        return None
    return info.contents.idle / 1000


def _inactivite_windows():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    try:
        li = LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(li)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
            return None
        return ((ctypes.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000
    except (AttributeError, OSError):
        return None


def _inactivite_mac():
    o = _sortie(["ioreg", "-c", "IOHIDSystem", "-d", "4"])
    m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', o or "")
    return int(m.group(1)) / 1e9 if m else None


def inactivite():
    """Secondes depuis la dernière activité de l'ordinateur (n'importe laquelle), ou None."""
    if sys.platform.startswith("win"):
        return _inactivite_windows()
    if sys.platform == "darwin":
        return _inactivite_mac()
    ordre = _CACHE.get("ordre") or [_inactivite_gnome, _inactivite_freedesktop, _inactivite_x11]
    for f in ordre:
        v = f()
        if v is not None:
            _CACHE["ordre"] = [f]                 # la source qui marche, la seule interrogée ensuite
            return v
    return None


# ---------------------------------------------------------------- batterie
def _batterie_linux(racine="/sys/class/power_supply"):
    for d in sorted(glob.glob(os.path.join(racine, "BAT*"))):
        try:
            with open(os.path.join(d, "capacity"), encoding="ascii") as f:
                pct = int(f.read().strip())
            try:
                with open(os.path.join(d, "status"), encoding="ascii") as f:
                    statut = f.read().strip().lower()
            except OSError:
                statut = ""
            return pct, statut in ("charging", "full", "not charging")
        except (OSError, ValueError):
            continue
    return None


def _batterie_windows():
    class SPS(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
    try:
        s = SPS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)) or s.BatteryFlag & 128 \
                or s.BatteryLifePercent > 100:
            return None
        return int(s.BatteryLifePercent), s.ACLineStatus == 1
    except (AttributeError, OSError):
        return None


def _batterie_mac():
    o = _sortie(["pmset", "-g", "batt"])
    m = re.search(r"(\d+)%", o or "")
    return (int(m.group(1)), "AC Power" in o) if m else None


def batterie():
    """(pourcentage, sur secteur) ou None (pas de batterie, ou inconnue)."""
    if sys.platform.startswith("win"):
        return _batterie_windows()
    if sys.platform == "darwin":
        return _batterie_mac()
    return _batterie_linux()


# ---------------------------------------------------------------- ne pas déranger
def discret():
    """True quand l'ordinateur demande le calme : « Ne pas déranger » (GNOME), présentation ou jeu en plein écran
    (Windows). Aucune fenêtre n'est regardée : c'est l'état que le système annonce lui-même."""
    if sys.platform.startswith("win"):
        try:
            etat = ctypes.c_int(0)
            if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(etat)) == 0:
                return etat.value in (2, 3, 4)          # occupé, jeu Direct3D plein écran, présentation
        except (AttributeError, OSError):
            return False
        return False
    o = _sortie(["gsettings", "get", "org.gnome.desktop.notifications", "show-banners"], 1.0)
    return o is not None and o.strip() == "false"


def releve():
    """Les signaux du moment, pour Creature.tick() et l'île."""
    return {"inactif": inactivite(), "batterie": batterie(), "discret": discret()}
