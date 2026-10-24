"""Une nouvelle fenêtre de terminal s'ouvre quand un monstre apparaît : le face-à-face en direct,
pendant que tu tapes tes commandes dans ton terminal habituel.

Désactivable : la fenêtre ne s'ouvre pas si config["fenetre_dressage"] vaut False.
"""
import os
import shutil
import subprocess
import sys

from .plateforme import IS_WIN, OSK


def _soi_meme():
    """La commande qui relance Terminagotchi (fichier .pyz ou paquet)."""
    moi = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if moi.endswith(".pyz") and os.path.exists(moi):
        return [sys.executable, moi, "dressage"]
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [sys.executable, "-c", f"import sys; sys.path.insert(0, {racine!r}); sys.argv=['tg','dressage'];"
                                  " from tg.app import main; main()"]


def commande_terminal(cmd):
    """La bonne commande pour ouvrir une nouvelle fenêtre selon le système (None si impossible)."""
    if IS_WIN:
        if shutil.which("wt"):
            return ["wt", "new-tab", "--title", "Terminagotchi"] + cmd
        return ["cmd", "/c", "start", "Terminagotchi"] + cmd
    if OSK == "mac":
        texte = " ".join(f"'{c}'" for c in cmd).replace('"', '\\"')
        return ["osascript", "-e", f'tell application "Terminal" to do script "{texte}"',
                "-e", 'tell application "Terminal" to activate']
    if OSK == "android":
        return None                                  # Termux : pas de fenêtres
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return None
    prefere = os.environ.get("TERMINAL")
    candidats = ([prefere] if prefere else []) + ["ptyxis", "gnome-terminal", "konsole", "xfce4-terminal", "kitty",
                                                    "alacritty", "wezterm", "foot", "tilix", "xterm", "x-terminal-emulator"]
    for t in candidats:
        chemin = shutil.which(t) if t else None
        if not chemin:
            continue
        nom = os.path.basename(t)
        if nom in ("ptyxis",):
            return [chemin, "--new-window", "--"] + cmd
        if nom in ("gnome-terminal", "tilix"):
            return [chemin, "--"] + cmd
        if nom in ("xfce4-terminal",):
            return [chemin, "-x"] + cmd
        if nom in ("kitty", "foot"):
            return [chemin] + cmd
        if nom == "wezterm":
            return [chemin, "start", "--"] + cmd
        return [chemin, "-e"] + cmd                 # konsole, alacritty, xterm, x-terminal-emulator…
    return None


def ouvrir_dressage(state):
    """Ouvre la fenêtre du face-à-face (une seule fois par dressage). Renvoie True si c'est fait."""
    if not state.get("config", {}).get("fenetre_dressage", True):
        return False
    d = state.get("dressage")
    if not d or d.get("fenetre"):
        return False
    cmd = commande_terminal(_soi_meme())
    if not cmd:
        return False
    try:
        options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if IS_WIN:
            options["creationflags"] = 0x00000008 | 0x00000200      # détaché, nouveau groupe
        else:
            options["start_new_session"] = True
        subprocess.Popen(cmd, **options)
        d["fenetre"] = True
        return True
    except OSError:
        return False
