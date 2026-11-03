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
from .plateforme import BOLD, DIM, OSK, RESET, SYS_WIN, fg, piege

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
    bac = f"{fg(221)}[" + t("apr.bac.court") + f"]{RESET} " if (state.get("apprendre") or {}).get("bac_ici") else ""
    tete = bac + (f"{fg(coul)}{visage(state)}{RESET} {BOLD}{state['name']}{RESET} {DIM}{t('dress.niv', n=lvl)} {pct}%{RESET} "
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
    for x in state.pop("terminal_info", []) or []:     # apprendre en jouant : pas des erreurs (énigme, tampon, bac…)
        out.append(f"{fg(150)}{x}{RESET}")
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
        ici = os.environ.get("TG_ICI") or os.getcwd()   # le dossier du terminal (TG_ICI : le terminal du jeu, vsh/)
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


def _garde_gpg():
    """Le garde-fou gpg (bash et zsh ; décision du propriétaire, 1er novembre) : l'enfant tape de vraies commandes dans
    son vrai shell. DANS le terrain du jeu, gpg (et gpg2) refuse de partir si son trousseau (--homedir, sinon GNUPGHOME)
    n'est pas lui aussi dans le terrain : le vrai trousseau de la famille (~/.gnupg) n'est jamais touché par une commande
    recopiée d'un tuto. Le message dit gentiment la bonne commande (--homedir .trousseau, dans la Crypte). Hors du
    terrain, rien ne change (`command gpg`) : les parents utilisent gpg comme avant. `gpg --version` / `--help` passent
    toujours. Retiré avec le reste du bloc (tg desinstaller)."""
    def q(x):
        return "'" + x.replace("'", "'\\''") + "'"
    terrain = str(core.TERRAIN)
    return ("function __tg_gpg {\n"
            '  local __p="$1"; shift\n'
            '  local __t __ici __d="${GNUPGHOME-}" __h="" __a __reste="" __r=""\n'
            f'  __t=$(cd {q(terrain)} 2>/dev/null && pwd -P) || {{ command "$__p" "$@"; return; }}\n'
            '  __ici=$(pwd -P 2>/dev/null)\n'
            '  case "$__ici/" in "$__t"/*) ;; *) command "$__p" "$@"; return;; esac\n'
            '  case "$*" in --version|--help|-h) command "$__p" "$@"; return;; esac\n'
            '  for __a in "$@"; do\n'
            '    if [ "$__h" = 1 ]; then __d="$__a"; __h=2; continue; fi\n'
            '    case "$__a" in --homedir) __h=1;; --homedir=*) __d="${__a#--homedir=}"; __h=2;; *) __reste="$__reste $__a";; esac\n'
            '  done\n'
            '  [ "$__h" = 1 ] && __d=""\n'
            '  if [ -n "$__d" ]; then\n'
            '    case "$__d" in "~") __d="$HOME";; "~/"*) __d="$HOME/${__d#"~/"}";; esac\n'
            '    case "$__d" in /*) ;; *) __d="$__ici/$__d";; esac\n'
            '    if [ -d "$__d" ]; then __r=$(cd "$__d" 2>/dev/null && pwd -P)\n'
            '    else __r=$(cd "$(dirname -- "$__d")" 2>/dev/null && pwd -P) && __r="$__r/$(basename -- "$__d")"; fi\n'
            '    case "$__r" in */..|*/.) __r="";; esac\n'
            '    case "$__r/" in "$__t"/*) command "$__p" "$@"; return;; esac\n'
            '  fi\n'
            f"  printf '%s\\n' {q(t('comp.gpg.garde'))} >&2\n"
            f'  [ "$__ici" = "$__t/crypte" ] || printf \'   ➜ %s\\n\' {q("cd ~/" + core.TERRAIN.name + "/crypte")} >&2\n'
            "  printf '   ➜ %s --homedir .trousseau%s\\n' \"$__p\" \"$__reste\" >&2\n"
            "  return 2\n"
            "}\n"
            'function gpg { __tg_gpg gpg "$@"; }\n'
            'function gpg2 { __tg_gpg gpg2 "$@"; }\n')


# `deploie cat x | grep y` : le « # » de l'alias coupe le reste de la ligne (le tuyau n'est pas lancé), et la
# ligne entière est relue dans l'historique (history -a). Avec des guillemets ça marche aussi partout.
DEPLOIE = ("alias deploie='history -a 2>/dev/null; tg deploie --historique #'\n"
           "alias espace='tg espace'; alias cerveau='tg cerveau'; alias port='tg port'; alias citadelle='tg citadelle'; alias crypte='tg crypte'; alias machines='tg machines'\n"
           "alias ondes='tg ondes'; alias mesh-envoie='tg ondes mesh-envoie'; alias mesh-coupe='tg ondes mesh-coupe'; alias mesh-route='tg ondes mesh-route'\n"
           "alias guilde='tg guilde'\n"
           "alias observatoire='tg observatoire'; alias assistant='tg assistant'; alias agent='tg agent'; "
           "alias devine-type='tg devine-type'; alias devine-mot='tg devine-mot'\n"
           "alias donnees='tg donnees'\n"
           "alias forge='tg forge'\n"
           "alias atelier='tg atelier'\n"
           "alias sommet='tg sommet'\n"
           "alias temps='tg temps'\n"
           "alias controle='tg controle'")


def _blocs():
    exe, app = commande()
    home = Path.home()
    blocs = {}
    shell = os.environ.get("SHELL", "")
    bashrc, zshrc = home / ".bashrc", home / ".zshrc"
    if not SYS_WIN and (shell.endswith("bash") or bashrc.exists() or OSK == "android"):
        blocs[bashrc] = (f'__tg_prompt() {{ local s=$?; history -a; "{exe}" "{app}" prompt --statut=$s; }}\n'
                         'PROMPT_COMMAND="__tg_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"\n' + _ps2() +
                         f"alias tg='\"{exe}\" \"{app}\"'\n"
                         "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'\n"
                         "alias entrainement='tg entrainement'; alias exercice='tg entrainement'; alias badges='tg badges'\n"
                         "alias guide='tg guide'; alias types='tg types'; alias equipe='tg equipe'; alias aide='tg aide'\n"
                         + _garde_gpg() + DEPLOIE)
    if not SYS_WIN and (shell.endswith("zsh") or zshrc.exists() or OSK == "mac"):
        blocs[zshrc] = ("setopt INC_APPEND_HISTORY\n"
                        f'__tg_prompt() {{ local s=$?; "{exe}" "{app}" prompt --statut=$s }}\n'
                        "autoload -Uz add-zsh-hook && add-zsh-hook precmd __tg_prompt\n" + _ps2(zsh=True) +
                        f"alias tg='\"{exe}\" \"{app}\"'\n"
                        "alias carte='tg carte'; alias quetes='tg quetes'; alias explique='tg explique'\n"
                        "alias entrainement='tg entrainement'; alias exercice='tg entrainement'; alias badges='tg badges'\n"
                        "alias guide='tg guide'; alias types='tg types'; alias equipe='tg equipe'; alias aide='tg aide'\n"
                        "setopt INTERACTIVE_COMMENTS\n" + _garde_gpg() + DEPLOIE)
    fish = home / ".config" / "fish"
    if not SYS_WIN and fish.is_dir():
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
            'function cerveau\n    tg cerveau $argv\nend\nfunction port\n    tg port $argv\nend\n'
            'function citadelle\n    tg citadelle $argv\nend\n'
            'function crypte\n    tg crypte $argv\nend\n'
            'function machines\n    tg machines $argv\nend\n'
            'function ondes\n    tg ondes $argv\nend\n'
            'function mesh-envoie\n    tg ondes mesh-envoie $argv\nend\nfunction mesh-coupe\n    tg ondes mesh-coupe $argv\nend\n'
            'function mesh-route\n    tg ondes mesh-route $argv\nend\n'
            'function guilde\n    tg guilde $argv\nend\n'
            'function observatoire\n    tg observatoire $argv\nend\nfunction assistant\n    tg assistant $argv\nend\n'
            'function agent\n    tg agent $argv\nend\nfunction devine-type\n    tg devine-type $argv\nend\n'
            'function devine-mot\n    tg devine-mot $argv\nend\n'
            'function donnees\n    tg donnees $argv\nend\n'
            'function forge\n    tg forge $argv\nend\n'
            'function atelier\n    tg atelier $argv\nend\n'
            'function sommet\n    tg sommet $argv\nend\n'
            'function temps\n    tg temps $argv\nend\n'
            'function controle\n    tg controle $argv\nend')
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
        if installe is not None and ("--statut" not in installe or ("PS2=" in bloc and "PS2=" not in installe)
                                     or ("port='tg port'" in bloc and "port='tg port'" not in installe)
                                     or ("citadelle='tg citadelle'" in bloc and "citadelle='tg citadelle'" not in installe)
                                     or ("crypte='tg crypte'" in bloc and "crypte='tg crypte'" not in installe)
                                     or ("machines='tg machines'" in bloc and "machines='tg machines'" not in installe)
                                     or ("mesh-envoie='tg ondes" in bloc and "mesh-envoie='tg ondes" not in installe)
                                     or ("function __tg_gpg" in bloc and "function __tg_gpg" not in installe)
                                     or ("guilde='tg guilde'" in bloc and "guilde='tg guilde'" not in installe)
                                     or ("devine-mot='tg devine-mot'" in bloc and "devine-mot='tg devine-mot'" not in installe)
                                     or ("donnees='tg donnees'" in bloc and "donnees='tg donnees'" not in installe)
                                     or ("forge='tg forge'" in bloc and "forge='tg forge'" not in installe)
                                     or ("atelier='tg atelier'" in bloc and "atelier='tg atelier'" not in installe)
                                     or ("sommet='tg sommet'" in bloc and "sommet='tg sommet'" not in installe)
                                     or ("temps='tg temps'" in bloc and "temps='tg temps'" not in installe)
                                     or ("controle='tg controle'" in bloc and "controle='tg controle'" not in installe)):
            return False
    return True


def proposer(demander=input, lancer=True):
    """G-03 : au premier lancement sur PC, tout se passe dans UNE fenêtre. La créature propose de s'installer dans
    l'invite du terminal (Entrée = oui), puis ouvre ce terminal ici même : l'enfant y tape ses commandes et lit, sous
    chaque invite, ce que dit la créature et la commande à taper. En sortant (exit), on revient au jeu."""
    if SYS_WIN or est_installe() and a_jour():
        faits = True
    else:
        r = demander(f"\n   {fg(226)}🏠 " + t("intro.pc.installer") + f"{RESET} ").strip()
        from .accueil import oui
        if r and not oui(r):
            print("   " + t("intro.pc.plus_tard"))
            return False
        faits = bool(installer())
    if not faits:
        print("   " + t("intro.ou.pc"))
        return False
    print(f"\n   {fg(78)}" + t("intro.pc.lance") + RESET + "\n")
    if not lancer:
        return True
    if not ouvrir_terminal_du_jeu():
        print("   " + t("intro.ou.pc"))
    return True


def commande_terminal_du_jeu():
    """La commande qui ouvre le terminal du jeu : Windows → toujours le terminal du jeu (tg sh) ; ailleurs, le shell."""
    if SYS_WIN:
        exe, app = commande()
        return [exe, app, "sh"]
    return [os.environ.get("SHELL") or shutil.which("bash") or "sh", "-i"]


def nouvelle_fenetre():
    """`tg terminal` (la touche [t] de la fenêtre du jeu, `terminal` dans l'espace) : une fenêtre de plus avec le MÊME
    terminal du jeu (Windows : le terminal du jeu ; Linux, macOS : le shell avec le compagnon). Toutes écrivent
    dans un historique que le jeu lit : la créature mange les commandes de chacune. Renvoie (ok, message)."""
    from . import fenetre
    if OSK == "android":
        return False, t("vsh.fenetre.android")
    cmd = fenetre.commande_terminal(commande_terminal_du_jeu())
    if not cmd:
        return False, t("vsh.fenetre.impossible")
    kw = {"cwd": str(Path.home()), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL}
    if SYS_WIN:
        kw["creationflags"] = 0x00000008 | 0x00000200
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(cmd, env=dict(os.environ, TG_DANS_LE_JEU="1"), **kw)
    except OSError as e:
        return False, t("vsh.fenetre.impossible") + f" ({e})"
    return True, t("vsh.fenetre.ok")


def ouvrir_terminal_du_jeu():
    """Le terminal dans la fenêtre du jeu, le même partout : bash, zsh… (avec le compagnon de ~/.bashrc) ; sous
    Windows, toujours le terminal du jeu (vsh/ : un Linux virtuel écrit en Python, décisions du 2 novembre ; aucun
    autre terminal n'est cherché ni proposé). En sortant (exit), on revient au jeu."""
    env = dict(os.environ, TG_DANS_LE_JEU="1")
    try:
        if SYS_WIN:
            from .vsh import terminal
            terminal.lancer()
            return True
        shell = os.environ.get("SHELL") or shutil.which("bash") or "sh"
        subprocess.call([shell, "-i"], env=env)
        return True
    except OSError:
        return False


def est_installe():
    for chemin in _blocs():
        try:
            if DEBUT in chemin.read_text(encoding="utf-8"):
                return True
        except OSError:
            pass
    return False
