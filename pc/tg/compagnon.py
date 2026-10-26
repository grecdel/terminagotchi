"""Le compagnon dans le terminal : la créature vit dans ton invite de commande.

Mode « ligne » : une ligne vivante au-dessus de chaque invite (visage, faim, XP, réactions).
Mode « coin »  : en plus, la créature en pixel art incrustée en haut à droite du terminal.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import core, lecons, sprites
from .langue import t
from .plateforme import BOLD, DIM, IS_WIN, OSK, RESET, fg, piege

DEBUT = "# >>> terminagotchi >>>"
FIN = "# <<< terminagotchi <<<"


def visage(state):
    st = core.stage(core.level(state["xp"]))
    if st == 0:
        return "( ◯ )"
    if state.get("_vient_de_manger"):
        return "(^▽^)"
    if state["hunger"] < 30:
        return "(╥_╥)"
    if state["defi"]:
        return "(ʘ_ʘ)"
    return "(•ᴗ•)"


def ligne(state):
    """La ligne affichée au-dessus de l'invite."""
    lvl = core.level(state["xp"])
    lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
    pct = int(100 * (state["xp"] - lo) / max(1, hi - lo))
    coul = sprites.body_color(state)
    faim = sprites.bar(state["hunger"], 100, 5).replace("█", "▰").replace("░", "▱")
    faim_c = 78 if state["hunger"] >= 60 else 221 if state["hunger"] >= 30 else 203
    tete = f"{fg(coul)}{visage(state)}{RESET} {BOLD}{state['name']}{RESET} {DIM}{t('dress.niv', n=lvl)} {pct}%{RESET} {fg(faim_c)}{faim}{RESET}"

    nouveaux = state.get("nlog", 0) - state.get("prompt_vu", 0)
    if nouveaux > 0:
        msgs = [m[6:] for m in state["log"][-min(nouveaux, 2):]]
        return f"{tete}  {' · '.join(msgs)}"
    if state["defi"]:
        return f"{tete}  {fg(226)}" + t("comp.defi", cmd=piege(state["defi"]["cmd"])) + RESET
    from . import envies
    r = envies.rappel_recent(state)
    if r:                                          # l'envie du moment (au plus une fois toutes les 12 commandes)
        return f"{tete}  {fg(214)}💭 {r}{RESET}"
    les, _ = lecons.lecon_courante(state)
    if les and lvl >= les["niveau"]:
        return f"{tete}  {DIM}" + t("comp.lecon", cmd=piege(les["steps"][state["step"]]["cmd"])) + RESET
    from . import quetes
    suivie = quetes.ligne_suivie(state)
    if suivie:
        return f"{tete}  {DIM}{suivie}{RESET}"
    return tete


def coin(state):
    """Dessine la créature en haut à droite sans déplacer le curseur."""
    try:
        cols = shutil.get_terminal_size((80, 24)).columns
    except OSError:
        return ""
    lignes, w = sprites.creature(state)
    if cols < w + 40:
        return ""
    x = cols - w
    out = "\0337"
    for i, l in enumerate(lignes):
        out += f"\033[{i + 1};{x}H{l}"
    return out + "\0338"


def prompt(etape):
    """Appelé par le shell avant chaque invite."""
    sortie = []

    def rendre(state):
        s = ligne(state)
        if state["config"]["compagnon"] == "coin":
            s = coin(state) + s
        sortie.append(s)
        state["prompt_vu"] = state.get("nlog", 0)

    try:
        ici = os.getcwd()                      # le dossier du terminal : la carte de la maison le suit
    except OSError:
        ici = None
    etape(spontane=True, rythme=8, defis=True, avant_save=rendre, cwd=ici)
    if sortie:
        sys.stdout.write(sortie[0] + RESET + "\n")
        sys.stdout.flush()

# ================================================================ installation

def commande():
    exe = sys.executable
    arg0 = os.path.abspath(sys.argv[0])
    if arg0.endswith("__main__.py"):          # lancé depuis les sources
        arg0 = str(Path(arg0).parent.parent)
    return exe, arg0


def _blocs():
    exe, app = commande()
    home = Path.home()
    blocs = {}
    shell = os.environ.get("SHELL", "")
    bashrc, zshrc = home / ".bashrc", home / ".zshrc"
    if not IS_WIN and (shell.endswith("bash") or bashrc.exists() or OSK == "android"):
        blocs[bashrc] = (f'__tg_prompt() {{ history -a; "{exe}" "{app}" prompt; }}\n'
                         'PROMPT_COMMAND="__tg_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"\n'
                         f"alias tg='\"{exe}\" \"{app}\"'\n"
                         "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'")
    if not IS_WIN and (shell.endswith("zsh") or zshrc.exists() or OSK == "mac"):
        blocs[zshrc] = ("setopt INC_APPEND_HISTORY\n"
                        f'__tg_prompt() {{ "{exe}" "{app}" prompt }}\n'
                        "autoload -Uz add-zsh-hook && add-zsh-hook precmd __tg_prompt\n"
                        f"alias tg='\"{exe}\" \"{app}\"'\n"
                        "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'")
    fish = home / ".config" / "fish"
    if not IS_WIN and fish.is_dir():
        blocs[fish / "conf.d" / "terminagotchi.fish"] = (
            f'function __tg_prompt --on-event fish_prompt\n    "{exe}" "{app}" prompt\nend\n'
            f'function tg\n    "{exe}" "{app}" $argv\nend\n'
            'function carte\n    tg carte\nend\nfunction quetes\n    tg quetes $argv\nend\n'
            'function explique\n    tg explique $argv\nend')
    for ps in ("powershell", "pwsh"):
        if shutil.which(ps):
            try:
                r = subprocess.run([ps, "-NoProfile", "-Command", "$PROFILE"], capture_output=True,
                                   text=True, timeout=15)
                chemin = r.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                chemin = ""
            if chemin:
                blocs[Path(chemin)] = ("$__tgPrompt = $function:prompt\n"
                                       f'function prompt {{ & "{exe}" "{app}" prompt; & $__tgPrompt }}\n'
                                       f'function tg {{ & "{exe}" "{app}" @args }}\n'
                                       'function carte { tg carte }\nfunction quetes { tg quetes @args }\n'
                                       'function explique { tg explique @args }')
    return blocs


def _retirer_bloc(texte):
    if DEBUT not in texte:
        return texte
    avant, reste = texte.split(DEBUT, 1)
    apres = reste.split(FIN, 1)[1] if FIN in reste else ""
    return avant.rstrip("\n") + ("\n" if avant.strip() else "") + apres.lstrip("\n")


def installer():
    faits = []
    for chemin, bloc in _blocs().items():
        try:
            ancien = chemin.read_text(encoding="utf-8") if chemin.exists() else ""
            nouveau = _retirer_bloc(ancien).rstrip("\n")
            nouveau += ("\n\n" if nouveau else "") + f"{DEBUT}\n{bloc}\n{FIN}\n"
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(nouveau, encoding="utf-8")
            faits.append(str(chemin))
        except OSError:
            pass
    if OSK == "android":
        raccourci = Path.home() / ".shortcuts" / "Terminagotchi"
        try:
            exe, app = commande()
            raccourci.parent.mkdir(exist_ok=True)
            raccourci.write_text(f'#!/data/data/com.termux/files/usr/bin/bash\n"{exe}" "{app}"\n', encoding="utf-8")
            raccourci.chmod(0o755)
            faits.append(str(raccourci) + " (widget Termux)")
        except OSError:
            pass
    return faits


def desinstaller():
    faits = []
    for chemin in list(_blocs()) + [Path.home() / ".bashrc", Path.home() / ".zshrc"]:
        try:
            if chemin.exists():
                t = chemin.read_text(encoding="utf-8")
                if DEBUT in t:
                    chemin.write_text(_retirer_bloc(t), encoding="utf-8")
                    faits.append(str(chemin))
        except OSError:
            pass
    return sorted(set(faits))


def est_installe():
    for chemin in _blocs():
        try:
            if DEBUT in chemin.read_text(encoding="utf-8"):
                return True
        except OSError:
            pass
    return False
