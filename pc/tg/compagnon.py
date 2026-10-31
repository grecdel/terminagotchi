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
    from . import satiete
    e = satiete.etat(state)
    if e == "veille":
        return "(－_－)zᶻ"                            # en veille : yeux mi-clos (un repas complet la réveille)
    if e == "affamee":
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
    from . import satiete
    # v3 : la jauge de faim a son étiquette (🍎), pour ne pas la confondre avec le % d'XP juste à côté
    faim = "🍎" + sprites.bar(state["hunger"], 100, 5).replace("█", "▰").replace("░", "▱")
    e = satiete.etat(state)
    faim_c = {"rassasiee": 78, "forme": 78, "affamee": 221}.get(e, 203)
    tete = (f"{fg(coul)}{visage(state)}{RESET} {BOLD}{state['name']}{RESET} {DIM}{t('dress.niv', n=lvl)} {pct}%{RESET} "
            f"{fg(faim_c)}{faim}{RESET}" + (f" {fg(faim_c)}{satiete.ICONES_ETAT[e]}{RESET}" if e != "forme" else ""))

    try:                                           # I3 : le monstre en cours de dressage, sur sa propre ligne
        from . import dressage
        monstre = dressage.ligne_terminal(state)
    except Exception:                              # noqa: BLE001 (le compagnon ne doit jamais planter)
        monstre = None
    monstre = f"\n   {fg(214)}{monstre}{RESET}" if monstre else ""
    nouveaux = state.get("nlog", 0) - state.get("prompt_vu", 0)
    if nouveaux > 0:
        msgs = [m[6:] for m in state["log"][-min(nouveaux, 2):]]
        # v3 (I16) : presque chaque commande laisse un message (« a mangé… ») : l'épreuve du monstre reste dessous
        return f"{tete}  {' · '.join(msgs)}" + monstre
    if state["defi"]:
        return f"{tete}  {fg(226)}" + t("comp.defi", cmd=piege(state["defi"]["cmd"])) + RESET
    from . import intro
    if intro.en_cours(state):                      # l'œuf : la prochaine commande de sa liste
        p = intro.prochaine(state)
        return f"{tete}  {fg(226)}🥚 " + t("intro.liste.titre", n=len(intro.i_(state)["faits"]), total=len(intro.checklist())) \
            + (f" ➜ `{intro.commande_de(p)}`" if p else "") + RESET
    from . import envies
    r = envies.rappel_recent(state)
    if r:                                          # l'envie du moment (au plus une fois toutes les 12 commandes)
        return f"{tete}  {fg(214)}💭 {r}{RESET}"
    les, _ = lecons.lecon_courante(state)
    if les and lvl >= les["niveau"]:
        return f"{tete}  {DIM}" + t("comp.lecon2", cmd=commande_montree(state, les["steps"][state["step"]])) + RESET + monstre
    try:                                           # I8 : entre deux chapitres, le cd (depuis n'importe où) d'un lieu
        from . import histoire
        if histoire.bandeau(state) and histoire.fini(state, "nid") and not histoire.chapitre_courant(state):
            libre = next((c for c in histoire.AILES if not histoire.fini(state, c)), None)
            if libre:
                piece = histoire.PAR_CHAP[libre]["piece"]
                return f"{tete}  {DIM}🗺 " + t("comp.lecon2", cmd=f"`{piege(f'cd ~/{core.TERRAIN.name}/{piece}')}`") \
                    + RESET + monstre
    except Exception:                              # noqa: BLE001
        pass
    if monstre:
        return tete + monstre
    from . import quetes
    suivie = quetes.ligne_suivie(state)
    if suivie:
        return f"{tete}  {DIM}{suivie}{RESET}"
    return tete


def commande_montree(state, step, cwd=None):
    """La commande de l'étape telle qu'on la montre : précédée du « cd » qui y mène quand l'enfant n'est pas là où elle
    se tape (une seule ligne : « cd ~/terrain_terminagotchi/grenier puis mv … »), avec les lettres sosies."""
    from . import maison, placement, verif
    if placement.cache(state, step):                 # G-13 : mode « défi sans aide » : à toi de trouver !
        return t("sa.cache")
    cmd = piege(step["cmd"])
    try:
        ici = cwd or maison.ici(state)
        if not verif.au_bon_endroit(state, step, ici):
            return t("comp.lecon.puis", cd=piege(verif.cd_vers(verif.lieu_attendu(state, step))), cmd=cmd)
    except Exception:                                # noqa: BLE001 (le compagnon ne doit jamais planter)
        pass
    if step["cmd"].startswith("less "):
        return t("comp.lecon.less", cmd=cmd)
    return f"`{cmd}`"


def maison_ici(state):
    from . import maison
    return maison.ici(state)


def annonces(state):
    """Ce que l'enfant doit lire dans SON terminal (G-34) : le bravo, puis la nouvelle étape (son texte, la commande,
    la version des grands, le vrai terminal) quand elle change, et les messages importants (indices, mises en garde,
    erreurs expliquées). Une seule fois chacun."""
    from .langue import sans_marques  # noqa: F401
    out = []
    try:
        from . import verif
        e = verif.expliquer(core.DERNIER["ligne"], core.DERNIER["statut"], maison_ici(state))
    except Exception:                                # noqa: BLE001
        e = None
    if e:
        out.append(f"{fg(214)}{e}{RESET}")
    term = state.pop("terminal", []) or []
    for x in term:
        out.append(f"{fg(214)}{x}{RESET}")
    erreur = bool(e) or core.DERNIER["statut"] not in (None, 0) or any(not x.startswith("✔") for x in term)
    les, _ = lecons.lecon_courante(state)
    if les and core.level(state["xp"]) >= les["niveau"]:
        cle = f"{les['id']}:{state['step']}"
        if state.get("term_etape") == cle and erreur:
            # v3 : après une erreur, la commande attendue est réaffichée (plus besoin de taper `aide` à chaque fois)
            step = les["steps"][state["step"]]
            out.append(f"   {fg(226)}➜ " + t("comp.rappel", cmd=commande_montree(state, step)) + RESET)
        if state.get("term_etape") != cle:
            if state.get("term_etape") and not erreur:      # l'étape d'avant vient d'être réussie
                try:
                    from . import deploie
                    out.extend(deploie.recap_lecon(core.DERNIER.get("ligne")))
                except Exception:                    # noqa: BLE001
                    pass
            state["term_etape"] = cle
            step = les["steps"][state["step"]]
            from . import placement
            if les["id"] == "t0" and state["step"] == 0 and not placement.p_(state).get("etat"):
                out.append(f"{DIM}🧩 " + t("plac.propose") + RESET)       # G-13 : « je connais déjà un peu »
            out.append(f"{fg(213)}📖 {lecons.tx(step['dit'])}{RESET}")
            out.append(f"   {fg(226)}➜ {commande_montree(state, step)}{RESET}")
            if not placement.cache(state, step):        # I2 : le mode sans aide ne donne pas la commande ici non plus
                g = lecons.adulte(step)
                if g:
                    out.append(f"   {DIM}🧑 {g}{RESET}")
                from . import vrai
                v = vrai.ligne(step)
                if v:
                    out.append(f"   {DIM}{v}{RESET}")
    return out


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
        dire = annonces(state)
        if dire:
            s = "\n".join(dire) + RESET + "\n" + s
        if state["config"]["compagnon"] == "coin":
            s = coin(state) + s
        from . import intro
        avant = intro.pour_prompt(state)          # l'œuf qui réagit, l'écran « merci », une nouveauté (une fois)
        if avant:
            s = "\n".join(avant) + RESET + "\n" + s
        sortie.append(s)
        state["prompt_vu"] = state.get("nlog", 0)

    try:
        ici = os.getcwd()                      # le dossier du terminal : la carte de la maison le suit
    except OSError:
        ici = None
    statut = None
    if not any(a.startswith("--statut") for a in sys.argv) and est_installe() and not a_jour():
        try:
            installer()                         # un ancien bloc : remis à jour (il passera le code de sortie)
        except OSError:
            pass
    for a in sys.argv:                         # --statut=$? : le code de sortie de la commande (crochet d'invite)
        if a.startswith("--statut="):
            try:
                statut = int(a.split("=", 1)[1])
            except ValueError:
                pass
    etape(spontane=True, rythme=8, defis=True, avant_save=rendre, cwd=ici, statut=statut)
    if sortie:
        from . import intro
        intro.jouer_prompt(sys.stdout)          # le camp qui se réveille, l'œuf qui arrive (puis l'image finale)
        sys.stdout.write(sortie[0] + RESET + "\n")
        sys.stdout.flush()

# ================================================================ installation

def commande():
    exe = sys.executable
    arg0 = os.path.abspath(sys.argv[0])
    if arg0.endswith("__main__.py"):          # lancé depuis les sources
        arg0 = str(Path(arg0).parent.parent)
    return exe, arg0


def _ps2(zsh=False):
    """C2 : l'invite de suite (`>`, une apostrophe ou un guillemet pas fermé) dit comment en sortir (Ctrl+C)."""
    txt = t("comp.ps2").replace("!", ".")
    for a, b in (("\\", "\\\\"), ('"', '\\"'), ("$", "\\$"), ("`", "\\`")):
        txt = txt.replace(a, b)
    if zsh:
        txt = txt.replace("%", "%%")
    return f'PS2="{txt}"\n'


# `deploie cat x | grep y` : le « # » de l'alias coupe le reste de la ligne (le tuyau n'est pas lancé), et la
# ligne entière est relue dans l'historique (history -a). Avec des guillemets ça marche aussi partout.
DEPLOIE = ("alias deploie='history -a 2>/dev/null; tg deploie --historique #'\n"
           "alias espace='tg espace'; alias cerveau='tg cerveau'")


def _blocs():
    exe, app = commande()
    home = Path.home()
    blocs = {}
    shell = os.environ.get("SHELL", "")
    bashrc, zshrc = home / ".bashrc", home / ".zshrc"
    if not IS_WIN and (shell.endswith("bash") or bashrc.exists() or OSK == "android"):
        blocs[bashrc] = (f'__tg_prompt() {{ local s=$?; history -a; "{exe}" "{app}" prompt --statut=$s; }}\n'
                         'PROMPT_COMMAND="__tg_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"\n' + _ps2() +
                         f"alias tg='\"{exe}\" \"{app}\"'\n"
                         "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'\n"
                         "alias entrainement='tg entrainement'; alias exercice='tg entrainement'; alias badges='tg badges'\n"
                         "alias guide='tg guide'; alias types='tg types'; alias equipe='tg equipe'; alias aide='tg aide'\n"
                         + DEPLOIE)
    if not IS_WIN and (shell.endswith("zsh") or zshrc.exists() or OSK == "mac"):
        blocs[zshrc] = ("setopt INC_APPEND_HISTORY\n"
                        f'__tg_prompt() {{ local s=$?; "{exe}" "{app}" prompt --statut=$s }}\n'
                        "autoload -Uz add-zsh-hook && add-zsh-hook precmd __tg_prompt\n" + _ps2(zsh=True) +
                        f"alias tg='\"{exe}\" \"{app}\"'\n"
                        "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'\n"
                        "alias entrainement='tg entrainement'; alias exercice='tg entrainement'; alias badges='tg badges'\n"
                        "alias guide='tg guide'; alias types='tg types'; alias equipe='tg equipe'; alias aide='tg aide'\n"
                        "setopt INTERACTIVE_COMMENTS\n" + DEPLOIE)
    fish = home / ".config" / "fish"
    if not IS_WIN and fish.is_dir():
        blocs[fish / "conf.d" / "terminagotchi.fish"] = (
            f'function __tg_prompt --on-event fish_prompt\n    "{exe}" "{app}" prompt --statut=$status\nend\n'
            f'function tg\n    "{exe}" "{app}" $argv\nend\n'
            'function carte\n    tg carte\nend\nfunction quetes\n    tg quetes $argv\nend\n'
            'function explique\n    tg explique $argv\nend\n'
            'function entrainement\n    tg entrainement $argv\nend\nfunction exercice\n    tg entrainement $argv\nend\n'
            'function badges\n    tg badges $argv\nend\n'
            'function guide\n    tg guide $argv\nend\nfunction types\n    tg types\nend\n'
            'function equipe\n    tg equipe $argv\nend\nfunction aide\n    tg aide $argv\nend\n'
            'function deploie\n    tg deploie $argv\nend\nfunction espace\n    tg espace $argv\nend\n'
            'function cerveau\n    tg cerveau $argv\nend')
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
                                       'function explique { tg explique @args }\n'
                                       'function entrainement { tg entrainement @args }\n'
                                       'function exercice { tg entrainement @args }\nfunction badges { tg badges @args }\n'
                                       'function guide { tg guide @args }\nfunction types { tg types }\n'
                                       'function equipe { tg equipe @args }\n'
                                       'function deploie { tg deploie @args }\nfunction espace { tg espace @args }\n'
                                       'function cerveau { tg cerveau @args }')
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


def a_jour():
    """Le bloc installé passe bien le code de sortie à l'invite (versions d'avant : non)."""
    for chemin, bloc in _blocs().items():
        try:
            txt = chemin.read_text(encoding="utf-8")
        except OSError:
            continue
        installe = txt.split(DEBUT, 1)[1].split(FIN, 1)[0] if DEBUT in txt else None
        if installe is not None and ("--statut" not in installe or ("PS2=" in bloc and "PS2=" not in installe)):
            return False
    return True


def proposer(demander=input, lancer=True):
    """G-03 : au premier lancement sur PC, tout se passe dans UNE fenêtre. La créature propose de s'installer dans
    l'invite du terminal (Entrée = oui), puis ouvre ce terminal ici même : l'enfant y tape ses commandes et lit, sous
    chaque invite, ce que dit la créature et la commande à taper. En sortant (exit), on revient au jeu."""
    if IS_WIN or est_installe() and a_jour():
        faits = True
    else:
        r = demander(f"\n   {fg(226)}🏠 " + t("intro.pc.installer") + f"{RESET} ").strip()
        from .accueil import oui
        if r and not oui(r):
            print("   " + t("intro.pc.plus_tard"))
            return False
        faits = bool(installer())
    if not faits or IS_WIN:
        print("   " + t("intro.ou.pc"))
        return False
    print(f"\n   {fg(78)}" + t("intro.pc.lance") + RESET + "\n")
    if not lancer:
        return True
    shell = os.environ.get("SHELL") or shutil.which("bash") or "sh"
    try:
        subprocess.call([shell, "-i"], env=dict(os.environ, TG_DANS_LE_JEU="1"))
    except OSError:
        print("   " + t("intro.ou.pc"))
    return True


def est_installe():
    for chemin in _blocs():
        try:
            if DEBUT in chemin.read_text(encoding="utf-8"):
                return True
        except OSError:
            pass
    return False
