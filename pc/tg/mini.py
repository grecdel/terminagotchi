"""Mini-terminal : la créature toujours visible + une vraie ligne de commande en dessous.

Pensé pour une petite fenêtre flottante (Termux:Float sur Android, ou une petite
fenêtre « toujours au-dessus » sur PC). Chaque commande tapée ici est exécutée
pour de vrai, et la créature la mange immédiatement.
"""
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from . import core, envies, lecons, sprites
from . import langue
from .langue import envelopper, largeur, t
from .plateforme import BOLD, DIM, IS_WIN, RESET, Clavier, clear, fg, piege

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# commandes qui prennent tout l'écran : on leur laisse le terminal le temps qu'elles finissent
PLEIN_ECRAN = {"nano", "vim", "vi", "nvim", "less", "more", "top", "htop", "btop", "man", "ssh",
               "python", "python3", "node", "mc", "notepad"}
DELAI = 30


def visible(s):
    return largeur(s)


def couper(s, n):
    """Coupe une ligne colorée à n colonnes visibles (les caractères chinois/japonais en prennent 2)."""
    out, vu, i = "", 0, 0
    while i < len(s):
        m = ANSI.match(s, i)
        if m:
            out += m.group()
            i = m.end()
            continue
        lc = langue.largeur_car(s[i])
        if vu + lc > n:
            break
        out += s[i]
        vu += lc
        i += 1
    return out + RESET


def argv_shell(cmd):
    if IS_WIN:
        return ["powershell", "-NoProfile", "-Command", cmd]
    bash = shutil.which("bash")
    if bash:   # charge ~/.bashrc pour retrouver tes alias et fonctions (ouvre, miam…)
        return [bash, "-c", "shopt -s expand_aliases; [ -f ~/.bashrc ] && . ~/.bashrc >/dev/null 2>&1\n" + cmd]
    return ["/bin/sh", "-c", cmd]


def completer(tampon):
    """Tab : complète le dernier mot avec les noms de fichiers et dossiers (le plus long début commun)."""
    avant, _, mot = tampon.rpartition(" ")
    tete, _, debut = mot.rpartition("/")
    base = os.path.expanduser(tete) if tete else ("/" if mot.startswith("/") else ".")
    try:
        noms = [n for n in os.listdir(base or "/") if n.startswith(debut) and (debut.startswith(".") or not n.startswith("."))]
    except OSError:
        return tampon
    if not noms:
        return tampon
    commun = os.path.commonprefix(noms)
    if len(noms) == 1 and os.path.isdir(os.path.join(base or "/", commun)):
        commun += "/"
    elif len(noms) == 1:
        commun += " "
    return (avant + " " if avant else "") + (tete + "/" if tete or mot.startswith("/") else "") + commun


class Mini:
    def __init__(self, etape):
        self.etape = etape
        self.clav = Clavier()
        self.tampon = ""
        self.histo, self.pos = [], None           # ↑ ↓ : les commandes d'avant
        self.sh = None                             # un shell qui reste ouvert (alias, tâches, cd -, &&) : coquille.py
        if not IS_WIN and shutil.which("bash"):
            from .coquille import Coquille
            self.sh = Coquille(os.getcwd(), env=dict(os.environ, PAGER="cat", GIT_PAGER="cat"), rc=True)
        self.sortie = [f"{DIM}" + t("mini.accueil1"), t("mini.accueil2") + RESET]
        self.frame = 0
        self.state = None
        self.dernier_jeu = 0
        self.saut = 0

    # ------------------------------------------------------------ exécution
    def executer(self, ligne):
        self.sortie.append(f"{fg(244)}{self.invite_txt()}{RESET}{ligne}")
        mots = ligne.split()
        premier = mots[0].lower() if mots else ""
        if premier in ("quitter", "exit", "quit"):
            raise KeyboardInterrupt
        if premier in ("clear", "cls"):
            self.sortie = []
        elif premier in ("aide", "help"):
            self.sortie += [f"{DIM}" + l for l in langue.liste("mini.aide")] + [RESET]
        elif self.sh and premier not in PLEIN_ECRAN:
            # le même shell d'une ligne à l'autre : `cd x && ls`, `cd -`, `alias miam=…` puis `miam`, `sleep 9 &` puis
            # `jobs` et `kill %1` ; Ctrl+C arrête la commande en cours (pas tg mini) ; le code de sortie va au jeu
            texte, code, d = self.sh.lancer(ligne, DELAI, interrompre=lambda: "\x03" in self.clav.lire(0))
            try:
                os.chdir(d)
            except OSError:
                pass
            for l in texte.rstrip("\n").splitlines():
                self.sortie.append(ANSI.sub("", l.expandtabs(4)))
            self.sortie = self.sortie[-300:]
            self.jouer(extra=[ligne], statut=code)
            return
        elif premier in ("cd", "set-location", "sl"):
            cible = os.path.expandvars(os.path.expanduser(" ".join(mots[1:]) or "~"))
            try:
                os.chdir(Path(cible))
            except OSError:
                self.sortie.append(f"{fg(203)}" + t("mini.cd_introuvable", cible=cible) + RESET)
        elif premier in PLEIN_ECRAN:
            self.clav.normal()
            clear()
            try:
                subprocess.run(argv_shell(ligne))
            except OSError as e:
                self.sortie.append(str(e))
            self.clav.brut()
        else:
            env = dict(os.environ, PAGER="cat", GIT_PAGER="cat", COLUMNS=str(self.cols()))
            try:
                r = subprocess.run(argv_shell(ligne), capture_output=True, text=True, timeout=DELAI,
                                   env=env, errors="replace")
                texte = (r.stdout or "") + (r.stderr or "")
            except subprocess.TimeoutExpired as e:
                texte = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
                texte += "\n" + t("mini.arrete", s=DELAI)
            except OSError as e:
                texte = str(e)
            for l in texte.rstrip("\n").splitlines():
                self.sortie.append(ANSI.sub("", l.expandtabs(4)))
        self.sortie = self.sortie[-300:]
        self.jouer(extra=[ligne])

    def jouer(self, extra=None, statut=None):
        avant = self.state["total"] if self.state else None
        try:
            st = self.etape(spontane=True, rythme=1.5, defis=True, extra=extra, statut=statut, cwd=os.getcwd())
        except (core.Probleme, OSError) as e:      # sauvegarde inaccessible : on le dit, tg mini reste ouvert
            from . import sur
            msg = str(e) if isinstance(e, core.Probleme) else sur.message_os(e)
            if not self.sortie or self.sortie[-1] != msg:
                self.sortie.append(msg)
            st = None
        if st:
            if avant is not None and st["total"] > avant:
                self.saut = 3
            self.state = st
        self.dernier_jeu = time.time()

    def histoire(self, sens):
        if not self.histo:
            return
        self.pos = (len(self.histo) if self.pos is None else self.pos) + sens
        self.pos = max(0, min(len(self.histo), self.pos))
        self.tampon = self.histo[self.pos] if self.pos < len(self.histo) else ""

    # ------------------------------------------------------------ affichage
    def cols(self):
        return shutil.get_terminal_size((50, 24)).columns

    def invite_txt(self):
        cwd = os.getcwd()
        home = str(Path.home())
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        if len(cwd) > 22:
            cwd = "…" + cwd[-21:]
        return f"{cwd} $ "

    def dessiner(self):
        st = self.state
        cols, rows = shutil.get_terminal_size((50, 24))
        haut = []
        if st:
            sp, w = sprites.creature(st)
            if self.saut:
                self.saut -= 1
                sp = sp + [" " * w]
            elif self.frame % 4 < 2:
                sp = [" " * w] + sp
            else:
                sp = sp + [" " * w]
            lvl = core.level(st["xp"])
            lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
            faim_c = 78 if st["hunger"] >= 60 else 221 if st["hunger"] >= 30 else 203
            lf, lx = t("app.faim").lower(), t("app.xp").lower()
            lj = max(largeur(lf), largeur(lx))
            droite = [f"{BOLD}{st['name']}{RESET} " + t("dress.niv", n=lvl),
                      f"{fg(faim_c)}{langue.ajuster(lf, lj)} {sprites.bar(st['hunger'], 100, 6)}{RESET}",
                      f"{DIM}{langue.ajuster(lx, lj)} {sprites.bar(st['xp'] - lo, hi - lo, 6)}{RESET}",
                      f"{DIM}{envies.humeur(st)}{RESET}"]
            if cols >= w + 18:
                droite = [""] + droite
                n = max(len(sp), len(droite))
                sp += [" " * w] * (n - len(sp))
                droite += [""] * (n - len(droite))
                haut = [" " + a + "  " + b for a, b in zip(sp, droite)]
            else:
                haut = [" " + a for a in sp] + [" " + droite[0]]
            b = st.get("bubble")
            if st["defi"]:
                haut.append(f" {fg(226)}" + t("comp.defi", cmd=piege(st["defi"]["cmd"])) + RESET)
            elif b and time.time() < b[1]:
                for l in envelopper(b[0], max(20, cols - 4))[:3]:
                    haut.append(f" {BOLD}» {l}{RESET}")
            les, _ = lecons.lecon_courante(st)
            if les and lvl >= les["niveau"]:
                haut.append(f" {fg(213)}" + t("comp.lecon", cmd=piege(les["steps"][st["step"]]["cmd"])) + RESET)
        else:
            haut = [" " + t("mini.pas_de_creature")]
        haut.append(fg(238) + "─" * cols + RESET)

        place = max(1, rows - len(haut) - 1)
        corps = []
        for l in self.sortie:
            corps += textwrap.wrap(l, cols - 1, replace_whitespace=False, drop_whitespace=False) or [""]
        corps = corps[-place:]
        corps += [""] * (place - len(corps))
        curseur = "█" if self.frame % 2 == 0 else " "
        invite = f"{fg(78)}{self.invite_txt()}{RESET}{self.tampon}{curseur}"
        ecran = [couper(l, cols) for l in haut + corps] + [couper(invite, cols)]
        sys.stdout.write("\033[H" + "\n".join(l + "\033[K" for l in ecran) + "\033[J")
        sys.stdout.flush()

    # ------------------------------------------------------------ boucle
    def boucle(self):
        clear()
        self.jouer()
        try:
            with self.clav:
                while True:
                    self.frame += 1
                    if time.time() - self.dernier_jeu > 1.5:
                        self.jouer()
                    self.dessiner()
                    brut = self.clav.lire(0.35)
                    for fl, sens in (("\x1b[A", -1), ("\x1bOA", -1), ("\x1b[B", 1), ("\x1bOB", 1)):
                        if fl in brut:                       # ↑ ↓ : l'historique (comme un vrai terminal)
                            self.histoire(sens)
                    saisie = re.sub(r"\x1b(\[[0-9;?]*[A-Za-z~]|O.)?", "", brut)
                    for c in saisie:
                        if c in ("\r", "\n"):
                            ligne, self.tampon = self.tampon.strip(), ""
                            self.pos = None
                            if ligne:
                                if not self.histo or self.histo[-1] != ligne:
                                    self.histo = (self.histo + [ligne])[-200:]
                                self.executer(ligne)
                                self.dessiner()
                        elif c in ("\x7f", "\x08"):
                            self.tampon = self.tampon[:-1]
                        elif c == "\x03":               # Ctrl+C : efface la ligne (exit pour quitter)
                            if not self.tampon:
                                self.sortie.append(f"{DIM}^C · " + t("mini.quitter") + RESET)
                            self.tampon = ""
                        elif c == "\t":                 # Tab : complète le nom (comme un vrai terminal)
                            self.tampon = completer(self.tampon)
                        elif c == "\x15":                    # Ctrl+U : effacer la ligne
                            self.tampon = ""
                        elif c.isprintable() or c == " ":
                            self.tampon += c
        except KeyboardInterrupt:
            pass
        clear()
        print(t("mini.a_plus_tard"))


def lancer(etape):
    if not sys.stdin.isatty():
        print(t("mini.pas_de_terminal"))
        return
    Mini(etape).boucle()
