"""Le terminal du jeu : la fenêtre où l'enfant tape (Windows ; `tg sh` partout).

L'invite `nom@machine:~/chemin$` comme sous Linux, l'historique (↑ ↓, gardé d'une fois sur l'autre), Tab qui complète
les commandes et les chemins, Ctrl+C qui arrête la commande (ou efface la ligne), Ctrl+L / `clear`, les couleurs,
les accents (UTF-8), `exit` qui ramène au jeu. Après chaque commande, comme le crochet d'invite de bash
(compagnon.py) : la ligne est ajoutée à ~/.terminagotchi/historique_terminal (le jeu la lit, la créature la mange),
puis `tg prompt --statut=N` affiche ce que dit la créature et la commande suivante. Les commandes du jeu (tg, carte,
atelier, port…) sont lancées par le jeu lui-même. Plusieurs fenêtres peuvent tourner en même temps (tg terminal) :
elles écrivent toutes dans le même historique.
"""
import os
import re
import shutil
import subprocess
import sys

from ..langue import t
from ..plateforme import SYS_WIN
from . import interne, outils
from .shell import Entree, Flux, Interrompu, Shell, Sortie
from .vfs import Vfs

VERT = "\033[01;32m"
BLEU = "\033[01;34m"
FIN = "\033[00m"


# ---------------------------------------------------------------- le clavier
class Clavier:
    """Une touche à la fois (mode brut) : Windows (msvcrt) ou Linux / macOS (termios)."""

    def __init__(self):
        self.tty = sys.stdin.isatty()
        self.ancien = None
        self.tampon = b""

    def brut(self):
        if not self.tty or SYS_WIN or self.ancien is not None:
            return
        import termios
        fd = sys.stdin.fileno()
        self.ancien = termios.tcgetattr(fd)
        nouveau = termios.tcgetattr(fd)
        nouveau[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG | termios.IEXTEN)
        nouveau[6][termios.VMIN] = 1
        nouveau[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSADRAIN, nouveau)

    def normal(self):
        if self.ancien is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.ancien)
            self.ancien = None

    def touche(self):
        """Une touche : un caractère, ou un nom ("haut", "bas", "gauche", "droite", "debut", "fin", "suppr")."""
        if SYS_WIN:
            import msvcrt
            c = msvcrt.getwch()
            if c in ("\x00", "\xe0"):
                d = msvcrt.getwch()
                return {"H": "haut", "P": "bas", "K": "gauche", "M": "droite", "G": "debut", "O": "fin",
                        "S": "suppr", "s": "mot_gauche", "t": "mot_droite"}.get(d, "")
            return c
        fd = sys.stdin.fileno()
        b = os.read(fd, 1)
        if not b:
            return "\x04"
        if b == b"\x1b":
            import select
            seq = b""
            while select.select([fd], [], [], 0.03)[0]:
                seq += os.read(fd, 1)
                if seq[-1:].isalpha() or seq[-1:] == b"~":
                    break
            return {b"[A": "haut", b"[B": "bas", b"[C": "droite", b"[D": "gauche", b"[H": "debut", b"[F": "fin",
                    b"OH": "debut", b"OF": "fin", b"[1~": "debut", b"[4~": "fin", b"[3~": "suppr",
                    b"[1;5D": "mot_gauche", b"[1;5C": "mot_droite"}.get(seq, "" if seq else "echap")
        if b[0] >= 0x80:                         # un caractère UTF-8 en plusieurs octets (é, 🐉)
            n = 2 if b[0] >= 0xC0 else 1
            n = 3 if b[0] >= 0xE0 else n
            n = 4 if b[0] >= 0xF0 else n
            while len(b) < n:
                b += os.read(fd, 1)
            return b.decode("utf-8", "replace")
        return b.decode("latin-1")


def _largeur(s):
    from ..langue import largeur
    return largeur(re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", s))


# ---------------------------------------------------------------- le terminal
class Terminal:
    def __init__(self, vfs=None, compagnon=True, ecrire=None):
        self.vfs = vfs or Vfs()
        self.ecrire_brut = ecrire or self._ecrire_stdout
        self.sh = Shell(self.vfs, interactif=True, ecrire_terminal=self.ecrire_brut)
        self.sh.nom = "bash"
        self.sh.colonnes = lambda: shutil.get_terminal_size((80, 24)).columns
        self.sh.pager = self.pager
        self.sh.sur_jeu = self.jeu
        self.sh.clavier = self.ligne_clavier
        self.clavier = Clavier()
        try:
            self.ecran_tty = sys.stdout.isatty()     # (les couleurs et les colonnes de ls seulement sur un vrai écran)
        except (AttributeError, ValueError):
            self.ecran_tty = False
        self.compagnon = compagnon
        self.historique = []
        self.fichier_historique = self.vfs.jeu_reel / "historique_terminal"
        self.charger_historique()
        self.sh.historique = self.historique

    @staticmethod
    def _ecrire_stdout(b):
        try:
            sys.stdout.buffer.write(b)
            sys.stdout.buffer.flush()
        except (OSError, ValueError):
            pass

    def ecrire(self, texte):
        self.ecrire_brut(texte.encode("utf-8", "surrogateescape") if isinstance(texte, str) else texte)

    # ------------------------------------------------ l'historique
    def charger_historique(self):
        try:
            d = self.fichier_historique.read_bytes()[-40000:].decode("utf-8", "replace")
            self.historique = [l for l in d.splitlines() if l.strip()][-500:]
        except OSError:
            self.historique = []

    def noter(self, ligne):
        """La ligne va dans l'historique du jeu (une ligne par commande, comme `history -a` de bash)."""
        une = ligne.strip()
        if not une:
            return
        self.historique.append(une)
        del self.historique[:-500]
        try:
            self.fichier_historique.parent.mkdir(parents=True, exist_ok=True)
            with open(self.fichier_historique, "a", encoding="utf-8") as f:
                f.write(une + "\n")
        except OSError:
            pass

    # ------------------------------------------------ l'invite
    def chemin_court(self):
        c = self.sh.cwd
        h = self.sh.vars.get("HOME", self.vfs.home)
        if c == h:
            return "~"
        if c.startswith(h + "/"):
            return "~" + c[len(h):]
        return c

    def invite(self):
        u = self.sh.vars.get("USER", self.vfs.utilisateur)
        m = self.sh.vars.get("HOSTNAME", "terminagotchi")
        return f"{VERT}{u}@{m}{FIN}:{BLEU}{self.chemin_court()}{FIN}$ "

    def invite_suite(self):
        return t("comp.ps2") + " "

    # ------------------------------------------------ lire une ligne (avec ↑ ↓, Tab, Ctrl+C)
    def lire_ligne(self, invite):
        if not self.clavier.tty:
            self.ecrire(invite)
            l = sys.stdin.readline()
            if not l:
                return None
            self.ecrire(l if l.endswith("\n") else l + "\n")      # (sans clavier : la ligne est recopiée)
            return l.rstrip("\r\n")
        tampon = []
        pos = 0
        h = len(self.historique)
        brouillon = ""
        tab_avant = False
        self.clavier.brut()
        try:
            self.ecrire(invite)
            while True:
                try:
                    k = self.clavier.touche()
                except KeyboardInterrupt:
                    k = "\x03"
                if k in ("\r", "\n"):
                    self.ecrire("\r\n")
                    return "".join(tampon)
                if k == "\x03":                          # Ctrl+C : la ligne est abandonnée
                    self.ecrire("^C\r\n")
                    self.sh.statut = 130
                    return ""
                if k in ("\x04", "\x1a"):                # Ctrl+D (Ctrl+Z sous Windows) sur une ligne vide : exit
                    if not tampon:
                        self.ecrire("\r\n")
                        return None
                    continue
                if k == "\t":
                    texte = "".join(tampon)
                    nouveau, choix = self.completer(texte[:pos])
                    if nouveau != texte[:pos]:
                        tampon = list(nouveau + texte[pos:])
                        pos = len(nouveau)
                    elif choix and tab_avant:
                        self.ecrire("\r\n" + "  ".join(choix[:60]) + "\r\n")
                    tab_avant = True
                    self._redessiner(invite, tampon, pos)
                    continue
                tab_avant = False
                if k in ("\x7f", "\x08"):
                    if pos > 0:
                        del tampon[pos - 1]
                        pos -= 1
                elif k == "suppr":
                    if pos < len(tampon):
                        del tampon[pos]
                elif k == "gauche":
                    pos = max(0, pos - 1)
                elif k == "droite":
                    pos = min(len(tampon), pos + 1)
                elif k in ("debut", "\x01"):
                    pos = 0
                elif k in ("fin", "\x05"):
                    pos = len(tampon)
                elif k == "\x15":                        # Ctrl+U
                    tampon, pos = tampon[pos:], 0
                elif k == "\x0b":                        # Ctrl+K
                    tampon = tampon[:pos]
                elif k == "\x17":                        # Ctrl+W : le mot d'avant
                    j = pos
                    while j > 0 and tampon[j - 1] == " ":
                        j -= 1
                    while j > 0 and tampon[j - 1] != " ":
                        j -= 1
                    tampon, pos = tampon[:j] + tampon[pos:], j
                elif k == "\x0c":                        # Ctrl+L
                    self.ecrire("\033[H\033[2J")
                    self.ecrire(invite)
                elif k == "haut":
                    if h > 0:
                        if h == len(self.historique):
                            brouillon = "".join(tampon)
                        h -= 1
                        tampon = list(self.historique[h])
                        pos = len(tampon)
                elif k == "bas":
                    if h < len(self.historique):
                        h += 1
                        tampon = list(self.historique[h] if h < len(self.historique) else brouillon)
                        pos = len(tampon)
                elif k == "mot_gauche":
                    while pos > 0 and tampon[pos - 1] == " ":
                        pos -= 1
                    while pos > 0 and tampon[pos - 1] != " ":
                        pos -= 1
                elif k == "mot_droite":
                    while pos < len(tampon) and tampon[pos] == " ":
                        pos += 1
                    while pos < len(tampon) and tampon[pos] != " ":
                        pos += 1
                elif len(k) == 1 and (k >= " " or k == "\t") and k != "\x7f":
                    tampon.insert(pos, k)
                    pos += 1
                elif len(k) > 1 and k not in ("echap",) and not k.isalpha():
                    tampon[pos:pos] = list(k)
                    pos += len(k)
                elif len(k) == 1 and ord(k) >= 0x80:
                    tampon.insert(pos, k)
                    pos += 1
                self._redessiner(invite, tampon, pos)
        finally:
            self.clavier.normal()

    def _redessiner(self, invite, tampon, pos):
        texte = "".join(tampon)
        recul = _largeur(texte[pos:])
        self.ecrire("\r" + invite + texte + "\033[K" + (f"\033[{recul}D" if recul else ""))

    def completer(self, avant):
        """Tab : le nom d'une commande (premier mot) ou d'un chemin du terminal. (nouveau début, possibilités)"""
        m = re.search(r"(\S*)$", avant)
        mot = m.group(1)
        debut = avant[:len(avant) - len(mot)]
        premier = not re.search(r"\S", debut) or re.search(r"[|;&]\s*$", debut)
        if premier and "/" not in mot:
            noms = sorted(set(outils.TOUS) | set(interne.INTERNES) | set(self.sh.alias) | set(self.sh.fonctions)
                          | outils.DU_JEU)
            choix = [n for n in noms if n.startswith(mot)]
            ajout = " "
        else:
            base, _, part = mot.rpartition("/")
            dossier = self.vfs.normaliser(self.sh.cwd, (base or "/") if mot.startswith("/") or base else ".")
            if base and mot.startswith("~"):
                dossier = self.vfs.normaliser(self.sh.cwd, base)
            try:
                noms = self.vfs.lister(dossier)
            except Exception:                        # noqa: BLE001
                noms = []
            choix = sorted(n for n in noms if n.startswith(part) and (part.startswith(".") or not n.startswith(".")))
            if len(choix) == 1:
                ajout = "/" if self.vfs.est_dossier(dossier.rstrip("/") + "/" + choix[0]) else " "
            else:
                ajout = ""
            prefixe = (base + "/") if (base or mot.startswith("/")) else ""
            choix_complets = [prefixe + c for c in choix]
            if not choix:
                return avant, []
            commun = os.path.commonprefix(choix)
            return debut + prefixe + _echapper(commun) + (ajout if len(choix) == 1 else ""), choix_complets
        if not choix:
            return avant, []
        commun = os.path.commonprefix(choix)
        return debut + commun + (ajout if len(choix) == 1 else ""), choix

    # ------------------------------------------------ ce que lisent les commandes (read, cat, sqlite3)
    def ligne_clavier(self):
        try:
            l = sys.stdin.readline()
        except (KeyboardInterrupt, EOFError):
            raise Interrompu()
        return l if l else None

    # ------------------------------------------------ less / man : page par page
    def pager(self, texte, nom):
        lignes = texte.split("\n")
        if texte.endswith("\n"):
            lignes.pop()
        haut = shutil.get_terminal_size((80, 24)).lines - 1
        if not self.clavier.tty or len(lignes) <= haut:
            self.ecrire("".join(l + "\n" for l in lignes))
            return
        debut = 0
        self.clavier.brut()
        try:
            while True:
                self.ecrire("\033[H\033[2J" + "".join(l + "\r\n" for l in lignes[debut:debut + haut]))
                fin = min(len(lignes), debut + haut) >= len(lignes)
                self.ecrire("\033[7m" + ("(END)" if fin else f"{nom} — " + t("vsh.less.aide")) + "\033[0m")
                try:
                    k = self.clavier.touche()
                except KeyboardInterrupt:
                    k = "q"
                if k in ("q", "Q", "\x03", "\x1b", "echap"):
                    break
                if k in (" ", "f", "suppr") and not fin:
                    debut = min(len(lignes) - haut, debut + haut)
                elif k in ("\r", "\n", "j", "bas"):
                    debut = min(max(0, len(lignes) - haut), debut + 1)
                elif k in ("b", "haut", "k"):
                    debut = max(0, debut - (haut if k == "b" else 1))
                elif k in ("g", "debut"):
                    debut = 0
                elif k in ("G", "fin"):
                    debut = max(0, len(lignes) - haut)
                elif k == "/":
                    self.clavier.normal()
                    self.ecrire("\r\033[K/")
                    cherche = sys.stdin.readline().strip()
                    self.clavier.brut()
                    if cherche:
                        trouve = next((i for i in range(debut + 1, len(lignes)) if cherche in lignes[i]), None)
                        if trouve is not None:
                            debut = min(trouve, max(0, len(lignes) - haut))
            self.ecrire("\r\033[K")
        finally:
            self.clavier.normal()

    # ------------------------------------------------ les commandes du jeu (tg, carte, atelier…)
    def jeu(self, args, ctx):
        from .. import compagnon
        nom = args[0]
        if nom == "tg":
            reste = args[1:]
        elif nom == "exercice":
            reste = ["entrainement"] + args[1:]
        elif nom.startswith("mesh-"):
            reste = ["ondes", nom] + args[1:]
        else:
            reste = [nom] + args[1:]
        if reste[:1] in (["sh"], ["terminal-ici"]):
            ctx.err(t("vsh.deja") + "\n")
            return 0
        exe, app = compagnon.commande()
        cwd = self.vfs.reel(self.sh.cwd) if self.vfs.mode == "windows" else self.sh.cwd
        if cwd is None or not os.path.isdir(cwd):
            cwd = str(self.vfs.home_reel)
        env = dict(os.environ, TG_DANS_LE_JEU="1", TG_TERMINAL_JEU="1",
                   TG_ICI=self.vfs.pour_le_jeu(self.sh.cwd))
        env.update(outils.variables_exportees(self.sh))
        return outils.lancer_programme([exe, app] + reste, str(cwd), env, ctx,
                                       capture=not (ctx.sortie.tty and ctx.erreur.tty))

    def parler(self, code):
        """La créature : comme le crochet d'invite de bash (tg prompt --statut=$?)."""
        if not self.compagnon:
            return
        from .. import compagnon
        exe, app = compagnon.commande()
        cwd = self.vfs.reel(self.sh.cwd) if self.vfs.mode == "windows" else self.sh.cwd
        if cwd is None or not os.path.isdir(cwd):
            cwd = str(self.vfs.home_reel)
        env = dict(os.environ, TG_DANS_LE_JEU="1", TG_ICI=self.vfs.pour_le_jeu(self.sh.cwd))
        try:
            p = subprocess.run([exe, app, "prompt", f"--statut={code}"], cwd=str(cwd), env=env,
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
            self.ecrire(p.stdout)
        except (OSError, subprocess.SubprocessError, KeyboardInterrupt):
            pass

    # ------------------------------------------------ la boucle
    def executer(self, texte):
        """Une ligne (ou plusieurs, une commande complète) : renvoie le code, ou None pour `exit`."""
        self.vfs.fd.clear()
        self.sh.arret.clear()
        if re.match(r"^\s*deploie(\s|$)", texte):        # comme l'alias de bash : la ligne entière, par l'historique
            texte = "tg deploie --historique"
        sortie = Flux("terminal", self.ecrire_brut)
        sortie.tty = self.ecran_tty
        try:
            return self.sh.executer(texte, Entree(b"", self.ligne_clavier), sortie, sortie)
        except Sortie as s:
            self.sh.statut = s.code
            return None
        except (KeyboardInterrupt, Interrompu):
            self.sh.arret.set()
            self.ecrire("^C\n" if self.clavier.tty else "\n")
            self.sh.statut = 130
            return 130

    def boucle(self, accueil=True):
        if accueil:
            self.ecrire(f"\033[38;5;117m{t('vsh.accueil')}{FIN}\n")
            self.ecrire(f"\033[2m{t('vsh.accueil2')}{FIN}\n")
            self.parler(0)
        while True:
            for l in self.sh.taches_finies():
                self.ecrire(l + "\n")
            ligne = self.lire_ligne(self.invite())
            if ligne is None:
                break
            texte = ligne
            while True:                                  # la suite d'une commande pas finie (guillemet, do… done)
                from . import syntaxe
                try:
                    syntaxe.analyser(texte)
                    break
                except syntaxe.Incomplet:
                    suite = self.lire_ligne(self.invite_suite())
                    if suite is None or (suite == "" and self.sh.statut == 130 and self.clavier.tty):
                        texte = None
                        break
                    texte += "\n" + suite
                except syntaxe.ErreurSyntaxe:
                    break
            if texte is None:
                continue
            if not texte.strip():
                continue
            self.noter(_une_ligne(texte))
            code = self.executer(texte)
            if code is None:
                break
            for l in self.sh.taches_finies():
                self.ecrire(l + "\n")
            self.parler(code)
        for tache in self.sh.taches:
            tache.arret.set()
        self.ecrire(f"{t('vsh.au_revoir')}\n")
        return self.sh.statut


def _echapper(nom):
    return re.sub(r"([ '\"\\$`&|;<>()*?\[\]!#])", r"\\\1", nom)


def _une_ligne(texte):
    """Une commande sur plusieurs lignes devient une seule ligne d'historique (comme bash)."""
    morceaux = [l.strip() for l in texte.split("\n") if l.strip()]
    out = ""
    for m in morceaux:
        if not out:
            out = m
        elif re.search(r"(\bdo|\bthen|\belse|\{|\||&&|\|\||;)$", out) or m.startswith(("then", "do", "done", "fi",
                                                                                         "else", "elif", "}", ";")):
            out += " " + m if not m.startswith(("done", "fi", "}", "else", "elif")) or out.endswith(";") else "; " + m
        else:
            out += "; " + m
    return out


def lancer(compagnon=True):
    """`tg sh` : le terminal du jeu dans cette fenêtre (sous Windows, le terminal des leçons)."""
    os.environ.setdefault("TG_DANS_LE_JEU", "1")
    term = Terminal(compagnon=compagnon)
    try:
        return term.boucle()
    except KeyboardInterrupt:
        return 130
