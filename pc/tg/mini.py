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

from . import core, lecons, sprites
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


class Mini:
    def __init__(self, etape):
        self.etape = etape
        self.clav = Clavier()
        self.tampon = ""
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
        elif premier == "aide":
            self.sortie += [f"{DIM}" + l for l in langue.liste("mini.aide")] + [RESET]
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

    def jouer(self, extra=None):
        avant = self.state["total"] if self.state else None
        st = self.etape(spontane=True, rythme=1.5, defis=True, extra=extra)
        if st:
            if avant is not None and st["total"] > avant:
                self.saut = 3
            self.state = st
        self.dernier_jeu = time.time()

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
                      f"{DIM}{core.mood(st['hunger'])}{RESET}"]
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
                    saisie = re.sub(r"\x1b(\[[0-9;?]*[A-Za-z~]|O.)?", "", self.clav.lire(0.35))
                    for c in saisie:
                        if c in ("\r", "\n"):
                            ligne, self.tampon = self.tampon.strip(), ""
                            if ligne:
                                self.executer(ligne)
                                self.dessiner()
                        elif c in ("\x7f", "\x08"):
                            self.tampon = self.tampon[:-1]
                        elif c == "\x03":
                            raise KeyboardInterrupt
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
