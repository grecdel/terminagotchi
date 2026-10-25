"""Notifications natives + notification permanente (Android) avec l'image de la créature."""
import os
import shutil
import subprocess

from . import core, lecons, sprites
from .langue import t
from .plateforme import IS_WIN, OSK

IMAGE = core.SAVE_DIR / "creature.png"
CACHE_PERM = core.SAVE_DIR / "permanente.txt"
CACHE_IMG = core.SAVE_DIR / "creature.key"
PS_APPID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def systeme():
    """Nom du moteur de notification disponible, ou None."""
    if shutil.which("termux-notification"):
        return "android"
    if IS_WIN:
        return "windows"
    if OSK == "mac" and shutil.which("osascript"):
        return "mac"
    if shutil.which("notify-send"):
        return "linux"
    return None


def _lancer(args):
    """Lance sans attendre ni afficher quoi que ce soit."""
    try:
        kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
        if IS_WIN:
            kw["creationflags"] = 0x08000000   # CREATE_NO_WINDOW
        subprocess.Popen(args, **kw)
        return True
    except OSError:
        return False


def image(state):
    """Régénère l'image PNG seulement quand l'apparence change."""
    pal = sprites.palette(state)
    cle = repr((sprites.get_sprite(state), sorted(pal.items())))
    try:
        if CACHE_IMG.read_text(encoding="utf-8") == cle and IMAGE.exists():
            return IMAGE
    except OSError:
        pass
    core.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    sprites.png(IMAGE, sprites.get_sprite(state), pal)
    CACHE_IMG.write_text(cle, encoding="utf-8")
    return IMAGE


def envoyer(state, textes, forcer=False):
    if not textes or not (forcer or state["config"]["notifs"]):
        return False
    titre = f"{state['name']} · Terminagotchi"
    texte = textes[-1] if len(textes) == 1 else "\n".join(textes[-3:])
    sys_ = systeme()
    if sys_ == "android":
        return _lancer(["termux-notification", "--id", "terminagotchi-evt", "--group", "terminagotchi",
                        "--icon", "pets", "--title", titre, "--content", texte])
    if sys_ == "linux":
        try:
            img = str(image(state))
        except OSError:
            img = "dialog-information"
        return _lancer(["notify-send", "-a", "Terminagotchi", "-i", img, titre, texte])
    if sys_ == "mac":
        esc = lambda x: x.replace("\\", "\\\\").replace('"', '\\"')
        return _lancer(["osascript", "-e", f'display notification "{esc(texte)}" with title "{esc(titre)}"'])
    if sys_ == "windows":
        esc = lambda x: x.replace("'", "''")
        script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
            "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
            "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
            "$x = $t.GetElementsByTagName('text');"
            f"$x.Item(0).AppendChild($t.CreateTextNode('{esc(titre)}')) > $null;"
            f"$x.Item(1).AppendChild($t.CreateTextNode('{esc(texte)}')) > $null;"
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{PS_APPID}')"
            ".Show([Windows.UI.Notifications.ToastNotification]::new($t))")
        return _lancer(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script])
    return False


def resume(state):
    """Texte de la notification permanente."""
    lvl = core.level(state["xp"])
    st = core.stage(lvl)
    titre = f"{state['name']} · " + t("app.forme_niveau", forme=core.forme(state, lvl), n=lvl)
    lignes = [f"{t('app.faim')} {sprites.bar(state['hunger'], 100, 8)}  {core.mood(state['hunger'])}"]
    les, etiq = lecons.lecon_courante(state)
    if les and lvl >= les["niveau"]:
        lignes.append(t("notif.lecon", titre=lecons.tx(les["titre"])))
    if state["sauvages"]:
        lignes.append(t("notif.sauvages", n=len(state["sauvages"])))
    if state["log"]:
        lignes.append(state["log"][-1][6:])
    return titre, "\n".join(lignes)


def permanente(state):
    """Notification permanente (Android/Termux) mise à jour seulement si elle change."""
    if systeme() != "android":
        return
    if not state["config"]["permanente"]:
        if CACHE_PERM.exists():
            _lancer(["termux-notification-remove", "terminagotchi"])
            CACHE_PERM.unlink()
        return
    titre, texte = resume(state)
    try:
        img = str(image(state))
    except OSError:
        img = None
    cle = titre + texte + (img or "") + str(os.path.getmtime(img) if img else "")
    try:
        if CACHE_PERM.read_text(encoding="utf-8") == cle:
            return
    except OSError:
        pass
    args = ["termux-notification", "--id", "terminagotchi", "--ongoing", "--alert-once",
            "--priority", "low", "--icon", "pets", "--title", titre, "--content", texte]
    if img:
        args += ["--image-path", img]
    if _lancer(args):
        CACHE_PERM.write_text(cle, encoding="utf-8")
