"""Le terminal du jeu : l'interprète du petit shell POSIX (sh), écrit en Python, sans aucun programme extérieur.

Il exécute l'arbre de syntaxe.py : variables, `$( )`, `$(( ))`, `~`, jokers, guillemets, redirections, tuyaux,
`&&` `||` `;`, `if` / `for` / `while` / `until` / `case`, fonctions, `alias`, scripts (`sh f.sh`, `./f.sh`,
`source`), `export`, tâches de fond (`&`, `jobs`, `kill %1`, `wait`, `fg`) qui sont des tâches du terminal du jeu.
Les commandes elles-mêmes (ls, cat, grep…) sont dans outils.py et texte.py, et agissent sur les VRAIS fichiers du
terrain à travers vfs.py (on n'écrit que dans le terrain et ~/.terminagotchi). Les sorties imitent bash + coreutils
(messages en anglais, comme avec LC_ALL=C) ; pc/outils/test_terminal.py les compare au vrai bash.
"""
import fnmatch
import os
import posixpath
import re
import sys
import threading
import time

from . import syntaxe as S
from .vfs import ErreurFs, Vfs

IFS_DEFAUT = " \t\n"


class Sortie(Exception):
    """`exit n` : le shell s'arrête."""

    def __init__(self, code):
        self.code = code


class Retour(Exception):
    def __init__(self, code):
        self.code = code


class Boucle(Exception):
    def __init__(self, genre, n=1):
        self.genre, self.n = genre, n          # "break" | "continue"


class Interrompu(Exception):
    """Ctrl+C (ou kill d'une tâche de fond)."""


# ---------------------------------------------------------------- les flux
class Flux:
    """Une sortie : le terminal, un tampon (tuyau, $( )), un fichier (>)."""

    def __init__(self, genre="tampon", ecrire=None, vfs=None, chemin=None, ajout=False):
        self.genre = genre
        self.morceaux = []
        self._ecrire = ecrire
        self.vfs, self.chemin, self.ajout = vfs, chemin, ajout
        self.tty = genre == "terminal"

    def write(self, x):
        if isinstance(x, str):
            x = x.encode("utf-8", "surrogateescape")
        if not x:
            return
        if self.genre == "terminal":
            self._ecrire(x)
        elif self.genre == "nul":
            return
        else:
            self.morceaux.append(x)

    def octets(self):
        return b"".join(self.morceaux)

    def vider(self):
        """Fichier : écrit ce qui attend (à la fin de la commande)."""
        if self.genre == "fichier" and self.morceaux:
            d = b"".join(self.morceaux)
            self.morceaux = []
            self.vfs.ecrire(self.chemin, d, ajout=True)


class Entree:
    """Une entrée : des octets (tuyau, fichier <), ou le clavier (lire une ligne au terminal)."""

    def __init__(self, donnees=b"", clavier=None):
        self.donnees = donnees
        self.pos = 0
        self.clavier = clavier            # fonction() -> ligne (str, avec \n) ou None à la fin (Ctrl+D)
        self.tty = clavier is not None

    def tout(self):
        if self.clavier:
            out = []
            while True:
                l = self.clavier()
                if l is None:
                    break
                out.append(l.encode("utf-8"))
            return b"".join(out)
        d = self.donnees[self.pos:]
        self.pos = len(self.donnees)
        return d

    def ligne(self):
        """Une ligne (avec \\n), b"" à la fin."""
        if self.clavier:
            l = self.clavier()
            return b"" if l is None else l.encode("utf-8")
        if self.pos >= len(self.donnees):
            return b""
        j = self.donnees.find(b"\n", self.pos)
        j = len(self.donnees) if j < 0 else j + 1
        l = self.donnees[self.pos:j]
        self.pos = j
        return l


class Contexte:
    """Ce que reçoit une commande : ses arguments, ses flux, le shell."""

    def __init__(self, sh, args, entree, sortie, erreur):
        self.sh, self.args, self.entree, self.sortie, self.erreur = sh, args, entree, sortie, erreur

    @property
    def vfs(self):
        return self.sh.vfs

    def out(self, texte):
        self.sortie.write(texte)

    def err(self, texte):
        self.erreur.write(texte)

    def chemin(self, p):
        return self.sh.vfs.normaliser(self.sh.cwd, p)

    def verifier(self):
        self.sh.verifier_interruption()


# ---------------------------------------------------------------- les tâches de fond
class Tache:
    def __init__(self, n, pid, texte, fil, sh):
        self.n, self.pid, self.texte, self.fil, self.sh = n, pid, texte, fil, sh
        self.arret = threading.Event()
        self.code = None
        self.signal = None
        self.annoncee = False


# toutes les tâches de fond vivantes, par numéro (pid) : `kill PID` trouve aussi celle lancée dans un sous-shell,
# comme `(python3 -m http.server … & echo $! > pid)` puis `kill $(cat pid)` dans bash
import weakref  # noqa: E402

TACHES_PAR_PID = weakref.WeakValueDictionary()


# ---------------------------------------------------------------- le shell
class Shell:
    def __init__(self, vfs=None, cwd=None, interactif=False, ecrire_terminal=None, clavier=None, parent=None,
                 nom="sh", args=None, env=None):
        self.vfs = vfs or Vfs()
        self.interactif = interactif
        self.ecrire_terminal = ecrire_terminal or (lambda b: (sys.stdout.buffer.write(b), sys.stdout.buffer.flush()))
        self.clavier = clavier
        self.nom = nom
        self.args = list(args or [])
        if parent is None:
            self.vars = {}
            self.exportees = set()
            self._env_initial(env)
            self.fonctions, self.alias = {}, {}
            self.taches = []
            self.prochain_pid = 4200 + (os.getpid() % 300)
            self.umask = 0o022
            self.cwd = cwd or self.vfs.home
            self.vars["PWD"] = self.cwd
            self.precedent = None
            self.arret = threading.Event()        # Ctrl+C / kill d'une tâche
        else:
            self.vars = dict(parent.vars)
            self.exportees = set(parent.exportees)
            self.fonctions, self.alias = dict(parent.fonctions), dict(parent.alias)
            self.taches = []
            self.prochain_pid = parent.prochain_pid + 1
            self.umask = parent.umask
            self.cwd = parent.cwd
            self.precedent = parent.precedent
            self.arret = parent.arret
        self.statut = 0
        self.est_c = False
        self.dernier_fond = None
        self.historique = []
        self.locales = []
        self.options = {"e": False, "x": False, "u": False, "pipefail": False}
        self.pieges = {}
        self.condition = 0
        self.sur_jeu = None                       # fonction(ligne, args, ctx) -> code : les commandes du jeu (tg…)
        self.profondeur = 0
        from . import interne, outils
        self.outils = outils.TOUS
        self.vfs.commandes = lambda: sorted(outils.TOUS)
        if parent is None:
            self.vfs.preparer_systeme(sorted(set(outils.TOUS) | {n for n in interne.INTERNES if n.isalnum()}),
                                      pid=4100 + (os.getpid() % 100))

    def _env_initial(self, env):
        v = self.vars
        u = self.vfs.utilisateur
        v.update({"HOME": self.vfs.home, "USER": u, "LOGNAME": u, "SHELL": "/bin/sh",
                  "PATH": os.environ.get("PATH", "/usr/bin:/bin") if self.vfs.mode == "transparent" else
                  "/usr/local/bin:/usr/bin:/bin", "IFS": IFS_DEFAUT, "PS1": "$ ", "PS2": "> ",
                  "LANG": os.environ.get("LANG", "C.UTF-8") if os.name != "nt" else "C.UTF-8",
                  "TERM": "xterm-256color", "HOSTNAME": _machine()})
        if env:
            v.update(env)
        self.exportees.update({"HOME", "USER", "LOGNAME", "SHELL", "PATH", "LANG", "TERM", "PWD", "HOSTNAME"})

    def prefixe(self):
        """Le début des messages d'erreur, comme bash : « bash: » au clavier, « f.sh: line 3: » dans un script,
        « bash: line 1: » avec bash -c."""
        if self.interactif:
            return f"{self.nom}: "
        return f"{self.nom}: line {getattr(self, 'ligne', 1)}: "

    def pid_shell(self):
        """Le numéro du shell ($$) : le vrai sous Linux (transparent), un numéro du Linux virtuel sous Windows."""
        return os.getpid() if self.vfs.mode == "transparent" else 4100 + (os.getpid() % 100)

    # ------------------------------------------------ copies (sous-shell, script)
    def enfant(self, script=False, nom=None, args=None):
        e = Shell.__new__(Shell)
        e.__dict__.update({k: v for k, v in self.__dict__.items()})
        e.vars = dict(self.vars) if not script else {k: v for k, v in self.vars.items() if k in self.exportees or k in
                                                     ("IFS", "PS1", "PS2", "HOSTNAME")}
        e.exportees = set(self.exportees)
        e.fonctions = dict(self.fonctions) if not script else {}
        e.alias = dict(self.alias) if not script else {}
        e.taches = []
        e.locales = []
        e.options = dict(self.options)
        e.pieges = {} if script else dict(getattr(self, "pieges", {}))
        e.condition = 0
        e.interactif = False
        e.profondeur = self.profondeur + 1
        if script:
            e.nom = nom or self.nom
            e.args = list(args or [])
        return e

    # ------------------------------------------------ interruption
    def verifier_interruption(self):
        if self.arret.is_set():
            raise Interrompu()

    def dormir(self, secondes):
        fin = time.monotonic() + secondes
        while True:
            self.verifier_interruption()
            reste = fin - time.monotonic()
            if reste <= 0:
                return
            time.sleep(min(0.05, reste))

    # ------------------------------------------------ exécuter du texte
    def executer(self, texte, entree=None, sortie=None, erreur=None):
        """Exécute une ligne (ou un script). Renvoie le code de sortie."""
        sortie = sortie or Flux("terminal", self.ecrire_terminal)
        erreur = erreur or sortie
        entree = entree or Entree(b"", self.clavier)
        try:
            arbre = S.analyser(texte)
        except S.Incomplet as e:
            if e.guillemet:
                erreur.write(f"{self.nom}: unexpected EOF while looking for matching `{e.guillemet}'\n")
            else:
                erreur.write(f"{self.nom}: syntax error: unexpected end of file\n")
            self.statut = 2
            return 2
        except S.ErreurSyntaxe as e:
            if self.interactif:
                erreur.write(f"{self.nom}: {e}\n")
            else:
                pre = f"{self.nom}: -c: line {e.ligne}" if self.est_c else f"{self.nom}: line {e.ligne}"
                erreur.write(f"{pre}: {e}\n{pre}: `{e.texte}'\n")
            self.statut = 2
            return 2
        try:
            self.statut = self.liste(arbre, entree, sortie, erreur)
        except Retour as r:
            self.statut = r.code
        except Boucle:
            pass
        except ErreurExpansion as x:          # $(( 1 + )), ${x/} : bash abandonne toute la ligne
            erreur.write(self.prefixe() + f"{x}\n")
            self.statut = 127 if str(x).endswith("unbound variable") and not self.interactif else 1
        return self.statut

    # ------------------------------------------------ les nœuds
    def liste(self, l, ent, out, err):
        code = 0
        for eo, sep in l.elements:
            self.verifier_interruption()
            if sep == "&":
                code = self.en_fond(eo, out, err)
            else:
                code = self.et_ou(eo, ent, out, err)
            self.statut = code
        return code

    def et_ou(self, eo, ent, out, err):
        self.condition += bool(eo.suite)
        try:
            code = self.tuyau(eo.premier, ent, out, err)
        finally:
            self.condition -= bool(eo.suite)
        dernier = eo.premier
        for k, (op, t) in enumerate(eo.suite):
            if (op == "&&" and code == 0) or (op == "||" and code != 0):
                self.statut = code
                fin = k == len(eo.suite) - 1
                self.condition += not fin
                try:
                    code = self.tuyau(t, ent, out, err)
                finally:
                    self.condition -= not fin
                dernier = t
        self.statut = code
        # set -e : une commande qui échoue arrête le script (pas dans un if, un while, avant && ou ||, ni avec !)
        if code and self.options["e"] and not self.condition and dernier is (eo.suite[-1][1] if eo.suite else eo.premier) \
                and not dernier.non:
            raise Sortie(code)
        return code

    def tuyau(self, t, ent, out, err, dans_condition=False):
        if len(t.cmds) == 1:
            code = self.commande(t.cmds[0], ent, out, err)
        else:
            donnees = None
            code = 0
            echecs = []
            for i, c in enumerate(t.cmds):
                e = ent if i == 0 else Entree(donnees)
                if i == len(t.cmds) - 1:
                    code = self.commande(c, e, out, err)
                else:
                    tampon = Flux("tampon")
                    tampon.tty = False
                    sous = self.enfant()          # chaque morceau d'un tuyau tourne dans un sous-shell (comme bash)
                    sous.statut = self.statut
                    try:
                        r = sous.commande(c, e, tampon, err)
                    except Sortie as s:
                        r = s.code
                    if r:
                        echecs.append(r)
                    donnees = tampon.octets()
            if self.options.get("pipefail") and not code and echecs:
                code = echecs[-1]
        if t.non:
            code = 0 if code else 1
        return code

    def commande(self, c, ent, out, err):
        self.verifier_interruption()
        if isinstance(c, S.Simple):
            return self.simple(c, ent, out, err)
        if isinstance(c, S.Fonction):
            self.fonctions[c.nom] = c.corps
            return 0
        flux = self.rediriger(c.redirs, ent, out, err)
        if flux is None:
            return 1
        e, o, r, fichiers = flux
        try:
            if isinstance(c, S.Sous):
                sous = self.enfant()
                try:
                    return sous.liste(c.corps, e, o, r)
                except Sortie as x:
                    return x.code
            if isinstance(c, S.Groupe):
                return self.liste(c.corps, e, o, r)
            if isinstance(c, S.Si):
                for cond, corps in c.branches:
                    if self._cond(cond, e, o, r) == 0:
                        return self.liste(corps, e, o, r)
                return self.liste(c.sinon, e, o, r) if c.sinon else 0
            if isinstance(c, S.Pour):
                mots = []
                if c.mots is None:
                    mots = list(self.args)
                else:
                    for m in c.mots:
                        mots += self.developper(m)
                code = 0
                for m in mots:
                    self.verifier_interruption()
                    self.vars[c.var] = m
                    try:
                        code = self.liste(c.corps, e, o, r)
                    except Boucle as b:
                        if b.n > 1:
                            b.n -= 1
                            raise
                        if b.genre == "break":
                            break
                        continue
                return code
            if isinstance(c, S.TantQue):
                code = 0
                while True:
                    self.verifier_interruption()
                    ok = self._cond(c.cond, e, o, r) == 0
                    if ok == c.jusqua:
                        break
                    try:
                        code = self.liste(c.corps, e, o, r)
                    except Boucle as b:
                        if b.n > 1:
                            b.n -= 1
                            raise
                        if b.genre == "break":
                            break
                        continue
                return code
            if isinstance(c, S.Cas):
                mot = "".join(self.developper(c.mot, decouper=False, jokers=False))
                for motifs, corps in c.items:
                    for m in motifs:
                        if motif_shell(self.developper_motif(m), mot):
                            return self.liste(corps, e, o, r)
                return 0
        finally:
            for f in fichiers:
                try:
                    f.vider()
                except ErreurFs:
                    pass
        return 0

    def _cond(self, l, e, o, r):
        self.condition += 1
        try:
            return self.liste(l, e, o, r)
        finally:
            self.condition -= 1

    # ------------------------------------------------ redirections
    def rediriger(self, redirs, ent, out, err):
        e, o, r = ent, out, err
        fichiers = []
        for rd in redirs:
            fd = rd.fd if rd.fd is not None else (0 if rd.op in ("<", "<<", "<<-", "<&", "<>") else 1)
            if rd.op in ("<<", "<<-"):
                texte = rd.texte or ""
                if not getattr(rd, "cite", False):
                    texte = self.developper_heredoc(texte)
                e = Entree(texte.encode("utf-8"))
                continue
            cible = self.developper(rd.cible, decouper=False, jokers=False)
            cible = cible[0] if cible else ""
            if cible == "" and rd.op not in (">&", "<&"):
                err.write(self.prefixe() + f": No such file or directory\n")
                return None
            if rd.op in (">&", "<&"):
                if cible in ("1", "2"):
                    src = o if cible == "1" else r
                    if fd == 1:
                        o = src
                    elif fd == 2:
                        r = src
                    continue
                if cible == "-":
                    continue
                if rd.op == ">&" and fd == 1:          # >& fichier : les deux sorties
                    rd = S.Redir(None, "&>", rd.cible)
                else:
                    err.write(self.prefixe() + f"{cible}: ambiguous redirect\n")
                    return None
            vp = self.vfs.normaliser(self.cwd, cible)
            if rd.op == "<":
                try:
                    if self.vfs.est_dossier(vp):
                        e = Entree(b"")
                        e.erreur_dossier = True
                    else:
                        e = Entree(self.vfs.lire(vp))
                except ErreurFs as x:
                    err.write(self.prefixe() + f"{cible}: {x.texte}\n")
                    return None
                continue
            if vp in ("/dev/null",):
                f = Flux("nul")
            elif vp in ("/dev/stdout", "/dev/tty"):
                f = out
            elif vp == "/dev/stderr":
                f = err
            else:
                ajout = rd.op == ">>"
                try:
                    if self.vfs.est_dossier(vp):
                        raise ErreurFs(21)
                    if not ajout:
                        self.vfs.ecrire(vp, b"")
                    else:
                        self.vfs.ecrire(vp, b"", ajout=True)
                except ErreurFs as x:
                    err.write(self.prefixe() + f"{cible}: {x.texte}\n")
                    return None
                f = Flux("fichier", vfs=self.vfs, chemin=vp, ajout=True)
                fichiers.append(f)
            if rd.op == "&>":
                o = r = f
            elif fd == 1:
                o = f
            elif fd == 2:
                r = f
        return e, o, r, fichiers

    # ------------------------------------------------ la commande simple
    def simple(self, c, ent, out, err):
        self.ligne = getattr(c, "ligne", 1)
        mots_bruts = list(c.mots)
        # les alias (le premier mot seulement, puis le suivant si l'alias finit par une espace)
        if mots_bruts and mots_bruts[0] in self.alias:
            vus = set()
            while mots_bruts and mots_bruts[0] in self.alias and mots_bruts[0] not in vus:
                vus.add(mots_bruts[0])
                texte = self.alias[mots_bruts[0]] + " " + " ".join(mots_bruts[1:])
                try:
                    arbre = S.analyser(texte)
                except (S.Incomplet, S.ErreurSyntaxe) as x:
                    err.write(f"{self.nom}: {x}\n")
                    return 2
                if len(arbre.elements) == 1 and not arbre.elements[0][0].suite and \
                        len(arbre.elements[0][0].premier.cmds) == 1 and \
                        isinstance(arbre.elements[0][0].premier.cmds[0], S.Simple) and arbre.elements[0][1] != "&":
                    s2 = arbre.elements[0][0].premier.cmds[0]
                    c = S.Simple(c.affect + s2.affect, s2.mots, s2.redirs + c.redirs)
                    mots_bruts = list(s2.mots)
                    if not self.alias.get(next(iter(vus)), "").endswith(" "):
                        break
                else:
                    flux = self.rediriger(c.redirs, ent, out, err)
                    if flux is None:
                        return 1
                    e, o, r, fichiers = flux
                    try:
                        return self.liste(arbre, e, o, r)
                    finally:
                        for f in fichiers:
                            f.vider()
        try:
            args = []
            for m in mots_bruts:
                args += self.developper(m)
            affect = [(a.split("=", 1)[0], "".join(self.developper(a.split("=", 1)[1], decouper=False, jokers=False)))
                      for a in c.affect]
        except _Statut as x:
            return x.code
        if self.options["x"]:
            for k, v in affect if not args else []:
                err.write(f"+ {k}={_citer_trace(v)}\n")
            if args:
                err.write("+ " + " ".join(_citer_trace(a) for a in args) + "\n")
        if not args:
            for k, v in affect:
                self.vars[k] = v
            flux = self.rediriger(c.redirs, ent, out, err)
            if flux:
                for f in flux[3]:
                    f.vider()
            return self.statut if c.affect and _a_substitution(c.affect) else (0 if flux else 1)
        flux = self.rediriger(c.redirs, ent, out, err)
        if flux is None:
            return 1
        e, o, r, fichiers = flux
        try:
            if getattr(e, "erreur_dossier", False):
                e = Entree(b"")
            return self.lancer(args, e, o, r, affect)
        finally:
            for f in fichiers:
                try:
                    f.vider()
                except ErreurFs as x:
                    err.write(self.prefixe() + f"{f.chemin}: {x.texte}\n")

    def lancer(self, args, e, o, r, affect=()):
        nom = args[0]
        from . import interne, outils
        if nom in self.fonctions:
            sauve = self.args
            self.args = args[1:]
            anciens = {k: self.vars.get(k) for k, _ in affect}
            for k, v in affect:
                self.vars[k] = v
            self.locales.append({})
            try:
                return self.commande(self.fonctions[nom], e, o, r)
            except Retour as x:
                return x.code
            finally:
                self.args = sauve
                for k, v in self.locales.pop().items():
                    if v is None:
                        self.vars.pop(k, None)
                    else:
                        self.vars[k] = v
                for k, v in anciens.items():
                    if v is None:
                        self.vars.pop(k, None)
                    else:
                        self.vars[k] = v
        if nom in interne.INTERNES:
            anciens = {k: self.vars.get(k) for k, _ in affect}
            for k, v in affect:
                self.vars[k] = v
            ctx = Contexte(self, args, e, o, r)
            try:
                return interne.INTERNES[nom](ctx)
            finally:
                if nom not in ("export", "readonly", "local", "eval", "source", ".", "read"):
                    for k, v in anciens.items():
                        if v is None:
                            self.vars.pop(k, None)
                        else:
                            self.vars[k] = v
        env_avant = None
        if affect:
            env_avant = {k: self.vars.get(k) for k, _ in affect}
            for k, v in affect:
                self.vars[k] = v
        try:
            ctx = Contexte(self, args, e, o, r)
            if "/" in nom:
                return interne.lancer_fichier(ctx)
            if self.sur_jeu and outils.est_du_jeu(nom):
                return self.sur_jeu(args, ctx)
            if nom in outils.TOUS:
                try:
                    return outils.TOUS[nom](ctx) or 0
                except ErreurFs as x:
                    r.write(f"{nom}: {x.texte}\n")
                    return 1
                except BrokenPipeError:
                    return 141
            return outils.inconnue(ctx)
        finally:
            if env_avant:
                for k, v in env_avant.items():
                    if v is None:
                        self.vars.pop(k, None)
                    else:
                        self.vars[k] = v

    # ------------------------------------------------ tâches de fond
    def en_fond(self, eo, out, err):
        self.prochain_pid += 1
        pid = self.prochain_pid
        n = 1 + max([t.n for t in self.taches if t.code is None] + [0])
        texte = _texte_de(eo)
        sous = self.enfant()
        sous.arret = threading.Event()
        sous.fond = True                          # (un programme lancé ici ne reçoit pas le Ctrl+C du clavier)
        tache = Tache(n, pid, texte, None, sous)
        tache.arret = sous.arret
        TACHES_PAR_PID[pid] = tache

        def tourner():
            try:
                tache.code = sous.et_ou(eo, Entree(b""), out, err)
            except Interrompu:
                tache.code = 143
                tache.signal = tache.signal or "Terminated"
            except Sortie as x:
                tache.code = x.code
            except Exception as x:                # noqa: BLE001 — une tâche ne casse jamais le terminal
                err.write(f"{self.nom}: {x}\n")
                tache.code = 1

        fil = threading.Thread(target=tourner, daemon=True)
        tache.fil = fil
        self.taches.append(tache)
        self.dernier_fond = pid
        if self.interactif:
            err.write(f"[{n}] {pid}\n")
        fil.start()
        return 0

    def taches_finies(self):
        """Les tâches finies depuis la dernière invite (bash les annonce : « [1]+  Done  … »)."""
        out = []
        for t in list(self.taches):
            if t.code is not None and not t.annoncee:
                t.annoncee = True
                etat = (f"Exit {t.code}" if t.code not in (0, 143) else "Done") if not t.signal else t.signal
                out.append(f"[{t.n}]{self._marque(t)}  {etat:<24}{t.texte.rstrip(' &')}")
                self.taches.remove(t)
        return out

    def _marque(self, t):
        vivantes = [x for x in self.taches if x.code is None or not x.annoncee]
        if vivantes and t is vivantes[-1]:
            return "+"
        if len(vivantes) > 1 and t is vivantes[-2]:
            return "-"
        return " "

    def tache(self, spec):
        """%1, %%, %+, %-, %sleep, ou un numéro de tâche (pid)."""
        vivantes = [t for t in self.taches if t.code is None]
        if spec in ("%%", "%+", "%"):
            return vivantes[-1] if vivantes else None
        if spec == "%-":
            return vivantes[-2] if len(vivantes) > 1 else None
        if spec.startswith("%"):
            s = spec[1:]
            if s.isdigit():
                # (la plus récente : une ancienne tâche finie, pas encore annoncée, peut porter le même numéro)
                return next((t for t in reversed(self.taches) if t.n == int(s)), None)
            return next((t for t in vivantes if t.texte.startswith(s)), None)
        if spec.isdigit():
            return next((t for t in self.taches if t.pid == int(spec)), None)
        return None

    # ------------------------------------------------ développer les mots
    def var(self, nom):
        if nom == "?":
            return str(self.statut)
        if nom == "$":
            return str(self.pid_shell())
        if nom == "!":
            return str(self.dernier_fond) if self.dernier_fond else ""
        if nom == "#":
            return str(len(self.args))
        if nom == "0":
            return self.nom
        if nom.isdigit():
            i = int(nom)
            return self.args[i - 1] if 0 < i <= len(self.args) else None
        if nom in ("@", "*"):
            return " ".join(self.args)
        if nom == "RANDOM":
            import random
            return str(random.randint(0, 32767))
        if nom == "PWD":
            return self.cwd
        if nom == "OLDPWD":
            return self.precedent
        if nom == "SECONDS":
            return str(int(time.monotonic() - _DEBUT))
        return self.vars.get(nom)

    def developper(self, mot, decouper=True, jokers=True):
        """Un mot du shell → ses champs (après ~, $, $( ), $(( )), découpage et jokers)."""
        morceaux = self._morceaux(mot)
        champs = _decouper(morceaux, self.vars.get("IFS", IFS_DEFAUT) if decouper else None)
        out = []
        for ch in champs:
            if ch is _VIDE:
                continue
            texte = "".join(t for t, _q in ch)
            if jokers and any(not q and re.search(r"[*?\[]", t) for t, q in ch):
                motif = "".join(t if not q else _echapper_motif(t) for t, q in ch)
                trouves = self.joker(motif)
                if trouves:
                    out += trouves
                    continue
            out.append(texte)
        return out

    def developper_motif(self, mot):
        """Un motif de `case` : les parties citées restent littérales."""
        return "".join(t if not q else _echapper_motif(t) for t, q in
                       [x for ch in _decouper(self._morceaux(mot), None) if ch is not _VIDE for x in ch])

    def developper_heredoc(self, texte):
        out = []
        i = 0
        while i < len(texte):
            c = texte[i]
            if c == "\\" and i + 1 < len(texte) and texte[i + 1] in "$`\\\n":
                out.append(texte[i + 1] if texte[i + 1] != "\n" else "")
                i += 2
                continue
            if c == "$" or c == "`":
                v, i = self._dollar(texte, i, True)
                out.append(v)
                continue
            out.append(c)
            i += 1
        return "".join(out)

    def _morceaux(self, mot):
        """[(texte, cité, découpable)] : découpable = résultat d'un $ non cité."""
        out = []
        i, n = 0, len(mot)
        if (mot.startswith("<(") or mot.startswith(">(")) and mot.endswith(")"):
            return [(self.processus(mot[2:-1], mot[0] == ">"), True, False)]
        if mot.startswith("~"):
            j = mot.find("/")
            j = n if j < 0 else j
            qui = mot[1:j]
            if qui == "":
                out.append((self.vars.get("HOME", self.vfs.home), True, False))
                i = j
            elif qui == self.vfs.utilisateur:
                out.append((self.vfs.home, True, False))
                i = j
        while i < n:
            c = mot[i]
            if c == "'":
                j = mot.index("'", i + 1)
                out.append((mot[i + 1:j], True, False))
                i = j + 1
            elif c == '"':
                j = S._fin_guillemets(mot, i + 1)
                interieur = mot[i + 1:j - 1]
                if interieur in ("$@", "${@}"):
                    out.append((_ARGS, True, False))
                else:
                    out.append((self._dans_guillemets(interieur), True, False))
                i = j
            elif c == "\\":
                if i + 1 < n:
                    out.append((mot[i + 1], True, False))
                i += 2
            elif c == "$" or c == "`":
                v, i = self._dollar(mot, i, False)
                if v is _ARGS:
                    out.append((_ARGS, False, True))
                else:
                    out.append((v, False, True))
            else:
                j = i
                while j < n and mot[j] not in "'\"\\$`":
                    j += 1
                out.append((mot[i:j], False, False))
                i = j
        return out

    def _dans_guillemets(self, s):
        out = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == "\\" and i + 1 < len(s) and s[i + 1] in '$`"\\\n':
                out.append(s[i + 1] if s[i + 1] != "\n" else "")
                i += 2
                continue
            if c == "$" or c == "`":
                v, i = self._dollar(s, i, True)
                out.append(" ".join(self.args) if v is _ARGS else v)
                continue
            out.append(c)
            i += 1
        return "".join(out)

    def _dollar(self, s, i, cite):
        """Le $… (ou `…`) qui commence en i : (valeur, indice après)."""
        if s[i] == "`":
            j = s.index("`", i + 1)
            return self.substitution(s[i + 1:j].replace("\\`", "`")), j + 1
        if s.startswith("$((", i):
            try:
                j = S._fin_paren(s, i + 2)
                if s[j - 1:j] == ")" or s[j + 1:j + 2] == ")":
                    pass
            except S.Incomplet:
                return "$", i + 1
            # $(( expr )) : la fin est « )) »
            k = _fin_arith(s, i + 3)
            if k is not None:
                expr = s[i + 3:k]
                return str(self.arith(self._dans_guillemets(expr))), k + 2
        if s.startswith("$(", i):
            j = S._fin_paren(s, i + 2)
            return self.substitution(s[i + 2:j]), j + 1
        if s.startswith("${", i):
            j = S._fin_accolade(s, i + 2)
            return self.parametre(s[i + 2:j]), j + 1
        m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*|[0-9]|[?$!#@*\-])", s[i:])
        if not m:
            return "$", i + 1
        nom = m.group(1)
        if nom == "@" and not cite:
            return _ARGS, i + m.end()
        if nom == "-":
            return "".join(k for k, v in self.options.items() if v) + ("i" if self.interactif else ""), i + m.end()
        v = self.var(nom)
        if v is None and self.options["u"]:
            raise ErreurExpansion(f"{'$' + nom if nom.isdigit() else nom}: unbound variable")
        return (v or ""), i + m.end()

    def parametre(self, x):
        if x.startswith("#") and len(x) > 1:
            v = self.var(x[1:]) or ""
            return str(len(v))
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*|[0-9]+|[?$!#@*])(.*)$", x, re.S)
        if not m:
            raise ErreurExpansion(f"${{{x}}}: bad substitution")
        nom, op = m.group(1), m.group(2)
        v = self.var(nom)
        if not op:
            if v is None and self.options["u"]:
                raise ErreurExpansion(f"{nom}: unbound variable")
            return v or ""
        for sym in (":-", ":=", ":+", ":?", "-", "=", "+", "?"):
            if op.startswith(sym):
                mot = self._dans_guillemets(op[len(sym):]) if True else ""
                vide = v is None or (sym.startswith(":") and v == "")
                if sym.endswith("-"):
                    return mot if vide else v
                if sym.endswith("="):
                    if vide:
                        self.vars[nom] = mot
                        return mot
                    return v
                if sym.endswith("+"):
                    return "" if vide else mot
                if sym.endswith("?"):
                    if vide:
                        raise ErreurExpansion(f"{nom}: {mot or 'parameter null or not set'}")
                    return v
        v = v or ""
        for sym in ("##", "#", "%%", "%"):
            if op.startswith(sym):
                motif = self._dans_guillemets(op[len(sym):])
                if sym.startswith("#"):
                    rng = range(0, len(v) + 1) if sym == "#" else range(len(v), -1, -1)
                    for k in rng:
                        if motif_shell(motif, v[:k]):
                            return v[k:]
                    return v
                rng = range(len(v), -1, -1) if sym == "%" else range(0, len(v) + 1)
                for k in rng:
                    if motif_shell(motif, v[k:]):
                        return v[:k]
                return v
        if op.startswith("/"):
            tout = op.startswith("//")
            reste = op[2:] if tout else op[1:]
            a, _, b = reste.partition("/")
            a, b = self._dans_guillemets(a), self._dans_guillemets(b)
            rx = _motif_regex(a)
            return re.sub(rx, lambda _m: b, v, count=0 if tout else 1) if a else v
        if op.startswith(":"):
            try:
                parts = op[1:].split(":")
                debut = self.arith(parts[0])
                if debut < 0:
                    debut = max(0, len(v) + debut)
                if len(parts) > 1:
                    lg = self.arith(parts[1])
                    return v[debut:debut + lg] if lg >= 0 else v[debut:len(v) + lg]
                return v[debut:]
            except Exception:                      # noqa: BLE001
                raise ErreurExpansion(f"${{{x}}}: bad substitution")
        raise ErreurExpansion(f"${{{x}}}: bad substitution")

    def processus(self, texte, ecriture=False):
        """<( commande ) : sa sortie devient un fichier /dev/fd/63 (puis 62…) que lit la commande."""
        n = 63 - len(self.vfs.fd)
        chemin = f"/dev/fd/{n}"
        if ecriture:
            self.vfs.fd[chemin] = b""
            return chemin
        sous = self.enfant()
        tampon = Flux("tampon")
        tampon.tty = False
        try:
            sous.executer(texte, Entree(b""), tampon, _ErreurParent(self))
        except Sortie:
            pass
        self.vfs.fd[chemin] = tampon.octets()
        return chemin

    def substitution(self, texte):
        sous = self.enfant()
        tampon = Flux("tampon")
        tampon.tty = False
        try:
            code = sous.executer(texte, Entree(b""), tampon, _ErreurParent(self))
        except Sortie as x:
            code = x.code
        self.statut = code
        self._dernier_substitution = code
        return tampon.octets().decode("utf-8", "surrogateescape").rstrip("\n")

    def arith(self, expr):
        from .arith import ErreurCalcul, evaluer
        try:
            return evaluer(expr, self)
        except ErreurCalcul as e:
            raise ErreurExpansion(f"{expr.lstrip()}: {e.msg} (error token is \"{e.jeton}\")")
        except ZeroDivisionError:
            raise ErreurExpansion(f"{expr.lstrip()}: division by 0")
        except ValueError as e:
            raise ErreurExpansion(f"{expr.lstrip()}: {e}")

    def joker(self, motif):
        """Les chemins qui correspondent au motif (triés comme bash en LC_ALL=C), [] si aucun."""
        absolu = motif.startswith("/")
        parts = [p for p in motif.split("/")]
        if absolu:
            bases = ["/"]
            parts = parts[1:]
        else:
            bases = [""]
        for k, p in enumerate(parts):
            dernier = k == len(parts) - 1
            nouv = []
            if p == "":
                if dernier:          # « */ » : seulement les dossiers, avec leur /
                    bases = [b + "/" for b in bases if b and self.vfs.est_dossier(self.vfs.normaliser(self.cwd, b))]
                continue
            if not re.search(r"[*?\[]", p):
                for b in bases:
                    chemin = (b.rstrip("/") + "/" + _desechapper(p)) if b else _desechapper(p)
                    if b == "/":
                        chemin = "/" + _desechapper(p)
                    if self.vfs.existe(self.vfs.normaliser(self.cwd, chemin)):
                        nouv.append(chemin)
                bases = nouv
                continue
            for b in bases:
                dossier = self.vfs.normaliser(self.cwd, b or ".")
                try:
                    noms = self.vfs.lister(dossier)
                except ErreurFs:
                    continue
                for nm in sorted(noms):
                    if nm.startswith(".") and not p.startswith(".") and not p.startswith("\\."):
                        continue
                    if motif_shell(p, nm):
                        chemin = (b.rstrip("/") + "/" + nm) if b and b != "/" else ("/" + nm if b == "/" else nm)
                        if not dernier and not self.vfs.est_dossier(self.vfs.normaliser(self.cwd, chemin)):
                            continue
                        nouv.append(chemin)
            bases = nouv
        return sorted(bases, key=lambda x: x.encode("utf-8")) if bases and bases != [""] else []

    # ------------------------------------------------ cd
    def changer_dossier(self, cible):
        vp = self.vfs.normaliser(self.cwd, cible)
        if not self.vfs.existe(vp):
            raise ErreurFs(2)
        if not self.vfs.est_dossier(vp):
            raise ErreurFs(20)
        try:
            self.vfs.lister(vp)
        except ErreurFs as e:
            if e.errno == 13:
                raise
        self.precedent = self.cwd
        self.cwd = vp
        self.vars["PWD"] = vp
        self.vars["OLDPWD"] = self.precedent
        return vp


class _ErreurParent(Flux):
    """$( ) : les erreurs vont là où vont celles du shell parent (le terminal)."""

    def __init__(self, sh):
        super().__init__("terminal", sh.ecrire_terminal)


class ErreurExpansion(Exception):
    pass


class _Statut(Exception):
    def __init__(self, code):
        self.code = code


_ARGS = object()
_VIDE = object()
_DEBUT = time.monotonic()


def _citer_trace(a):
    if a == "":
        return "''"
    if re.search(r"[\s'\"$`\\|&;<>(){}*?\[\]!#~]", a):
        return "'" + a.replace("'", "'\\''") + "'"
    return a


def _machine():
    from .vfs import nom_machine
    return nom_machine()


def _a_substitution(affect):
    return any("$(" in a or "`" in a for a in affect)


def _fin_arith(s, i):
    prof = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            prof += 1
        elif c == ")":
            if prof == 0:
                return i if s[i + 1:i + 2] == ")" else None
            prof -= 1
        i += 1
    return None


def _decouper(morceaux, ifs):
    """Les champs : [[(texte, cité)]] (le découpage ne touche que les $ non cités ; "$@" donne un champ par argument).
    Un champ qui ne contient rien (un $vide non cité) vaut _VIDE ; "" cité donne un champ vide."""
    champs = []
    cur, commence = [], False

    def pousser():
        nonlocal cur, commence
        champs.append(cur if commence else _VIDE)
        cur, commence = [], False

    for texte, cite, decoupable in morceaux:
        if texte is _ARGS:
            args = _ARGS_COURANTS.get()
            if cite:
                for k, a in enumerate(args):
                    if k > 0:
                        pousser()
                    cur.append((a, True))
                    commence = True
                continue
            texte, cite, decoupable = " ".join(args), False, True
        if cite or not decoupable or ifs is None:
            if texte or cite:
                cur.append((texte, cite))
                commence = True
            continue
        for c in texte:
            if c in ifs:
                if c in " \t\n":
                    if commence:
                        pousser()
                else:
                    commence = True
                    pousser()
                continue
            cur.append((c, False))
            commence = True
    if commence:
        pousser()
    out = []
    for ch in champs:
        if ch is _VIDE:
            out.append(_VIDE)
            continue
        fus = []
        for t, q in ch:
            if fus and fus[-1][1] == q:
                fus[-1] = (fus[-1][0] + t, q)
            else:
                fus.append((t, q))
        out.append(fus)
    return out


class _ArgsCourants:
    """"$@" a besoin des arguments du shell en cours de développement (posé par Shell.developper)."""

    def __init__(self):
        self.local = threading.local()

    def get(self):
        return getattr(self.local, "args", [])

    def set(self, a):
        self.local.args = a


_ARGS_COURANTS = _ArgsCourants()
_vrai_developper = Shell.developper


def _developper_avec_args(self, mot, decouper=True, jokers=True):
    ancien = _ARGS_COURANTS.get()
    _ARGS_COURANTS.set(self.args)
    try:
        return _vrai_developper(self, mot, decouper, jokers)
    finally:
        _ARGS_COURANTS.set(ancien)


Shell.developper = _developper_avec_args


def _echapper_motif(t):
    return re.sub(r"([*?\[\]\\])", r"\\\1", t)


def _desechapper(t):
    return re.sub(r"\\(.)", r"\1", t)


def _motif_regex(motif):
    """Un motif du shell (*, ?, [a-z], [!a], \\x) → une expression régulière."""
    out = []
    i = 0
    while i < len(motif):
        c = motif[i]
        if c == "\\" and i + 1 < len(motif):
            out.append(re.escape(motif[i + 1]))
            i += 2
            continue
        if c == "*":
            out.append(".*")
        elif c == "?":
            out.append(".")
        elif c == "[":
            j = i + 1
            if j < len(motif) and motif[j] in "!^":
                j += 1
            if j < len(motif) and motif[j] == "]":
                j += 1
            while j < len(motif) and motif[j] != "]":
                j += 1
            if j >= len(motif):
                out.append(re.escape(c))
            else:
                cls = motif[i + 1:j]
                if cls.startswith(("!", "^")):
                    cls = "^" + cls[1:]
                cls = cls.replace("\\", "\\\\")
                cls = re.sub(r"\[:(\w+):\]", lambda m: _CLASSES.get(m.group(1), ""), cls)
                out.append("[" + cls + "]")
                i = j
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


_CLASSES = {"alpha": "a-zA-Z", "digit": "0-9", "alnum": "a-zA-Z0-9", "upper": "A-Z", "lower": "a-z",
            "space": " \\t\\n\\r\\f\\v", "punct": "!-/:-@\\[-`{-~", "xdigit": "0-9A-Fa-f"}


def motif_shell(motif, texte):
    try:
        return re.fullmatch(_motif_regex(motif), texte, re.S) is not None
    except re.error:
        return fnmatch.fnmatchcase(texte, motif)


def _texte_de(eo):
    """Le texte d'une commande lancée en fond (pour `jobs`)."""
    def mots(t):
        out = []
        for c in t.cmds:
            if isinstance(c, S.Simple):
                out.append(" ".join(c.affect + c.mots + [_redir_txt(r) for r in c.redirs]))
            else:
                out.append("…")
        return " | ".join(out)
    s = mots(eo.premier)
    for op, t in eo.suite:
        s += f" {op} " + mots(t)
    return s + " &"


def _redir_txt(r):
    return f"{r.fd if r.fd is not None else ''}{r.op} {r.cible}" if r.op not in (">&", "<&") else f"{r.fd or ''}{r.op}{r.cible}"


def posix(p):
    return posixpath.normpath(p)
