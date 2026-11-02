"""Le terminal du jeu : les commandes de fichiers (comme GNU coreutils), écrites en Python.

Chaque commande reçoit un Contexte (shell.py) : ses arguments, son entrée, ses sorties ; elle lit et écrit les VRAIS
fichiers du terrain par vfs.py, et rend son code de sortie. Les messages imitent GNU coreutils avec LC_ALL=C (en
anglais, comme dans les fiches du jeu). Une commande qui n'existe pas ici le dit clairement (raconter) : l'étape de
la leçon est alors racontée, comme sur un téléphone, sans jamais bloquer.
"""
import datetime
import os
import posixpath
import re
import stat
import time

from .vfs import ErreurFs

TOUS = {}


def outil(*noms):
    def deco(f):
        for n in noms:
            TOUS[n] = f
        return f
    return deco


# ---------------------------------------------------------------- petits outils communs
class Options:
    """Les options façon GNU : -abc, -n 3, -n3, --long, --long=valeur, -- ; avec_valeur = lettres qui prennent une
    valeur (ex. "nc")."""

    def __init__(self, args, avec_valeur="", longues=(), longues_valeur=(), chiffre=None):
        self.drapeaux = []         # [(nom, valeur)]
        self.reste = []
        self.erreur = None
        i = 0
        fini = False
        while i < len(args):
            a = args[i]
            if fini or a == "-" or not a.startswith("-"):
                self.reste.append(a)
                i += 1
                continue
            if a == "--":
                fini = True
                i += 1
                continue
            if a.startswith("--"):
                nom, egal, val = a[2:].partition("=")
                choix = [x for x in list(longues) + list(longues_valeur) if x.startswith(nom)]
                exact = [x for x in choix if x == nom]
                if exact:
                    choix = exact
                if len(choix) != 1:
                    self.erreur = ("ambigue" if len(choix) > 1 else "inconnue", a)
                    return
                nom = choix[0]
                if nom in longues_valeur:
                    if not egal:
                        if i + 1 >= len(args):
                            self.erreur = ("valeur", a)
                            return
                        val = args[i + 1]
                        i += 1
                    self.drapeaux.append(("--" + nom, val))
                else:
                    self.drapeaux.append(("--" + nom, None))
                i += 1
                continue
            if chiffre and re.fullmatch(r"-\d+", a):
                self.drapeaux.append((chiffre, a[1:]))
                i += 1
                continue
            j = 1
            while j < len(a):
                c = a[j]
                if c in avec_valeur:
                    val = a[j + 1:]
                    if not val:
                        if i + 1 >= len(args):
                            self.erreur = ("valeur", c)
                            return
                        val = args[i + 1]
                        i += 1
                    self.drapeaux.append((c, val))
                    break
                self.drapeaux.append((c, None))
                j += 1
            i += 1

    def a(self, *noms):
        return any(n in noms for n, _ in self.drapeaux)

    def val(self, *noms, defaut=None):
        v = defaut
        for n, x in self.drapeaux:
            if n in noms:
                v = x
        return v

    def toutes(self, *noms):
        return [x for n, x in self.drapeaux if n in noms]


def erreur_option(ctx, nom, o):
    genre, quoi = o.erreur
    if genre == "valeur":
        ctx.err(f"{nom}: option requires an argument -- '{quoi.lstrip('-')}'\n" if len(quoi) == 1 else
                f"{nom}: option '{quoi}' requires an argument\n")
    elif genre == "ambigue":
        ctx.err(f"{nom}: option '{quoi}' is ambiguous\n")
    else:
        ctx.err(f"{nom}: unrecognized option '{quoi}'\n")
    ctx.err(f"Try '{nom} --help' for more information.\n")
    return 2 if nom in ("ls", "grep", "diff") else 1


def option_inconnue(ctx, nom, lettre):
    ctx.err(f"{nom}: invalid option -- '{lettre}'\nTry '{nom} --help' for more information.\n")
    return 2 if nom in ("ls", "grep", "diff") else 1


def verifier_lettres(ctx, nom, o, permises):
    for n, _v in o.drapeaux:
        if len(n) == 1 and n not in permises:
            return option_inconnue(ctx, nom, n)
    return None


def lire_entree_ou_fichier(ctx, nom_cmd, f):
    """Les octets de f ('-' = l'entrée) ; None (et le message) si impossible."""
    if f == "-":
        return ctx.entree.tout()
    vp = ctx.chemin(f)
    try:
        if ctx.vfs.est_dossier(vp):
            ctx.err(f"{nom_cmd}: {f}: Is a directory\n")
            return None
        return ctx.vfs.lire(vp)
    except ErreurFs as e:
        ctx.err(f"{nom_cmd}: {f}: {e.texte}\n")
        return None


def lignes_de(donnees):
    """Les lignes (sans \\n) ; une dernière ligne sans \\n compte aussi."""
    if not donnees:
        return []
    l = donnees.split(b"\n")
    if donnees.endswith(b"\n"):
        l.pop()
    return l


def guillemets(nom):
    """Comment GNU cite un nom dans ses messages : 'nom' (et "l'eau" s'il contient une apostrophe)."""
    if "'" in nom:
        return '"' + nom + '"'
    return "'" + nom + "'"


def humain(n, ls=False):
    """1.0K, 4.0K, 12K, 1.5M… comme ls -h / du -h (arrondi vers le haut)."""
    import math
    if n < 1024:
        return str(int(n))
    for u in "KMGTPE":
        n /= 1024
        if n < 10:
            v = math.ceil(n * 10) / 10
            if v >= 10:
                return f"{int(math.ceil(v))}{u}"
            return f"{v:.1f}{u}"
        if n < 1024:
            v = math.ceil(n)
            if v >= 1024:
                continue
            return f"{v}{u}"
    return f"{int(n)}E"


# ---------------------------------------------------------------- ls
MOIS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def droits_texte(dossier, m):
    s = "d" if dossier else "-"
    for k in (6, 3, 0):
        x = (m >> k) & 7
        s += ("r" if x & 4 else "-") + ("w" if x & 2 else "-")
        spec = (k == 6 and m & 0o4000) or (k == 3 and m & 0o2000) or (k == 0 and m & 0o1000)
        if spec:
            s += ("s" if x & 1 else "S") if k else ("t" if x & 1 else "T")
        else:
            s += "x" if x & 1 else "-"
    return s


def date_ls(mtime, maintenant=None):
    maintenant = maintenant or time.time()
    d = datetime.datetime.fromtimestamp(mtime)
    six_mois = 365.2425 * 24 * 3600 / 2
    if maintenant - six_mois < mtime <= maintenant + 60:
        return f"{MOIS[d.month - 1]} {d.day:2d} {d.hour:02d}:{d.minute:02d}"
    return f"{MOIS[d.month - 1]} {d.day:2d}  {d.year}"


def _cle_nom(n):
    return n.encode("utf-8", "surrogateescape")


COULEUR_DOSSIER = "\033[01;34m"
COULEUR_EXEC = "\033[01;32m"
COULEUR_ARCHIVE = "\033[01;31m"
RAZ = "\033[0m"


def _colorer(nom, inf, tty):
    if not tty or inf is None:
        return nom
    if inf.dossier:
        return f"{COULEUR_DOSSIER}{nom}{RAZ}"
    if inf.mode & 0o111:
        return f"{COULEUR_EXEC}{nom}{RAZ}"
    if re.search(r"\.(tar|tgz|gz|zip|bz2|xz|7z)$", nom):
        return f"{COULEUR_ARCHIVE}{nom}{RAZ}"
    return nom


def _citer_ls(nom, tty):
    if not tty:
        return nom
    if re.search(r"[\s'\"$`\\!*?&;|<>(){}\[\]#~]", nom):
        if "'" in nom:
            return '"' + nom + '"'
        return "'" + nom + "'"
    return nom


def colonnes(noms_aff, largeurs, largeur_ecran):
    """La disposition en colonnes de GNU ls (rangées verticalement)."""
    n = len(noms_aff)
    if n == 0:
        return []
    meilleur = None
    for ncol in range(min(n, max(1, largeur_ecran // 3)), 0, -1):
        nlig = (n + ncol - 1) // ncol
        ncol_reel = (n + nlig - 1) // nlig
        larg_col = []
        for c in range(ncol_reel):
            bloc = largeurs[c * nlig:(c + 1) * nlig]
            larg_col.append(max(bloc) + (2 if c < ncol_reel - 1 else 0))
        if sum(larg_col) <= largeur_ecran:
            meilleur = (nlig, ncol_reel, larg_col)
            break
    if not meilleur:
        meilleur = (n, 1, [max(largeurs)])
    nlig, ncol, larg_col = meilleur
    out = []
    for l in range(nlig):
        ligne = ""
        for c in range(ncol):
            k = c * nlig + l
            if k >= n:
                break
            dernier = c == ncol - 1 or (c + 1) * nlig + l >= n
            ligne += noms_aff[k] + ("" if dernier else " " * (larg_col[c] - largeurs[k]))
        out.append(ligne)
    return out


@outil("ls", "dir")
def ls(ctx):
    o = Options(ctx.args[1:], longues=("all", "almost-all", "recursive", "human-readable", "color", "directory",
                                       "reverse", "classify", "help", "inode", "size"),
                longues_valeur=("color=", "sort"))
    if o.erreur:
        return erreur_option(ctx, "ls", o)
    r = verifier_lettres(ctx, "ls", o, "aAlRhd1trSFCxiGgonUfsp")
    if r is not None:
        return r
    if o.a("--help"):
        ctx.out("Usage: ls [OPTION]... [FILE]...\nList information about the FILEs (the current directory by default).\n")
        return 0
    tous = o.a("a", "--all", "f")
    presque = o.a("A", "--almost-all") and not tous
    long_ = o.a("l", "g", "o", "n")
    rec = o.a("R", "--recursive")
    hum = o.a("h", "--human-readable")
    dossier_seul = o.a("d", "--directory")
    classer = o.a("F", "--classify")
    tty = ctx.sortie.tty
    un = o.a("1") or not tty
    if o.a("C") and not long_:
        un = False
    tri = "nom"
    for n, _v in o.drapeaux:
        if n == "t":
            tri = "temps"
        elif n == "S":
            tri = "taille"
        elif n in ("U", "f"):
            tri = "aucun"
    inverse = o.a("r", "--reverse")
    noms = o.reste or ["."]
    code = 0
    fichiers, dossiers = [], []
    for nm in noms:
        vp = ctx.chemin(nm)
        if not ctx.vfs.existe(vp):
            ctx.err(f"ls: cannot access {guillemets(nm)}: No such file or directory\n")
            code = 2
            continue
        try:
            inf = ctx.vfs.infos(vp)
        except ErreurFs as e:
            ctx.err(f"ls: cannot access {guillemets(nm)}: {e.texte}\n")
            code = 2
            continue
        if inf.dossier and not dossier_seul:
            dossiers.append((nm, vp))
        else:
            fichiers.append((nm, vp, inf))
    largeur = ctx.sh.colonnes() if hasattr(ctx.sh, "colonnes") else 80

    def trier(elems, nom_de, inf_de):
        if tri == "aucun":
            return elems
        if tri == "temps":
            elems = sorted(elems, key=lambda e: (-inf_de(e).mtime, _cle_nom(nom_de(e))))
        elif tri == "taille":
            elems = sorted(elems, key=lambda e: (-inf_de(e).taille, _cle_nom(nom_de(e))))
        else:
            elems = sorted(elems, key=lambda e: _cle_nom(nom_de(e)))
        return list(reversed(elems)) if inverse else elems

    def suffixe(inf):
        if not classer or inf is None:
            return ""
        if inf.dossier:
            return "/"
        if inf.mode & 0o111:
            return "*"
        return ""

    def afficher(elems):
        """elems : [(nom affiché, infos)]."""
        if long_:
            if not elems:
                return
            lien_l = max(len(str(i.liens)) for _n, i in elems)
            prop_l = max(len(i.proprio) for _n, i in elems)
            grp_l = max(len(i.groupe) for _n, i in elems)
            tailles = [humain(i.taille) if hum else str(i.taille) for _n, i in elems]
            tail_l = max(len(t) for t in tailles)
            for (nm, i), tl in zip(elems, tailles):
                champs = [droits_texte(i.dossier, i.mode), str(i.liens).rjust(lien_l)]
                if not o.a("g"):
                    champs.append(i.proprio.ljust(prop_l))
                if not o.a("o"):
                    champs.append(i.groupe.ljust(grp_l))
                champs += [tl.rjust(tail_l), date_ls(i.mtime),
                           _colorer(_citer_ls(nm, tty), i, tty) + suffixe(i)]
                ctx.out(" ".join(champs) + "\n")
            return
        aff = [_colorer(_citer_ls(nm, tty), i, tty) + suffixe(i) for nm, i in elems]
        if un:
            for a in aff:
                ctx.out(a + "\n")
            return
        from ..langue import largeur as larg
        largs = [larg(_citer_ls(nm, tty)) + len(suffixe(i)) for nm, i in elems]
        if tty and any(_citer_ls(nm, tty) != nm for nm, _i in elems):
            # GNU : quand un nom est cité, les autres gardent une espace devant pour rester alignés
            aff = [(" " if _citer_ls(nm, tty) == nm else "") + a for (nm, _i), a in zip(elems, aff)]
            largs = [w + (1 if _citer_ls(nm, tty) == nm else 0) for (nm, _i), w in zip(elems, largs)]
        for l in colonnes(aff, largs, largeur):
            ctx.out(l + "\n")

    def total(elems):
        blocs = sum(_blocs_1k(i) for _n, i in elems)
        return humain(blocs * 1024) if hum else str(blocs)

    premier = True
    fichiers = trier(fichiers, lambda e: e[0], lambda e: e[2])
    if fichiers:
        afficher([(nm, inf) for nm, _vp, inf in fichiers])
        premier = False
    dossiers = trier(dossiers, lambda e: e[0], lambda e: ctx.vfs.infos(e[1]))
    plusieurs = len(noms) > 1 or rec
    a_faire = list(dossiers)
    while a_faire:
        nm, vp = a_faire.pop(0)
        try:
            contenu = ctx.vfs.lister(vp)
        except ErreurFs as e:
            if not premier:
                ctx.out("\n")
            ctx.err(f"ls: cannot open directory {guillemets(nm)}: {e.texte}\n")
            code = 2
            premier = False
            continue
        if tous:
            contenu = [".", ".."] + contenu
        elif not presque:
            contenu = [x for x in contenu if not x.startswith(".")]
        elems = []
        for x in contenu:
            try:
                elems.append((x, ctx.vfs.infos(posixpath.normpath(vp + "/" + x) if x not in (".", "..") else
                                                (vp if x == "." else posixpath.dirname(vp) or "/"))))
            except ErreurFs:
                elems.append((x, None))
        elems = trier(elems, lambda e: e[0], lambda e: e[1] or _INFOS_VIDES)
        if plusieurs:
            if not premier:
                ctx.out("\n")
            ctx.out(f"{_citer_ls(nm, tty) if not rec else nm}:\n")
        premier = False
        if long_:
            ctx.out(f"total {total([(n_, i) for n_, i in elems if i is not None])}\n")
        afficher([(n_, i) for n_, i in elems if i is not None])
        if rec:
            sous = [(posixpath.join(nm, x) if nm != "/" else "/" + x, posixpath.normpath(vp + "/" + x))
                    for x, i in elems if i is not None and i.dossier and x not in (".", "..")]
            a_faire = sous + a_faire
    return code


class _InfosVides:
    mtime = 0
    taille = 0


_INFOS_VIDES = _InfosVides()


def _blocs_1k(inf):
    if inf.blocs is not None:
        return (inf.blocs + 1) // 2
    return ((inf.taille + 4095) // 4096) * 4


# ---------------------------------------------------------------- cat, tac, rev, nl
@outil("cat")
def cat(ctx):
    o = Options(ctx.args[1:], longues=("number", "show-all", "help"))
    if o.erreur:
        return erreur_option(ctx, "cat", o)
    r = verifier_lettres(ctx, "cat", o, "nAbEsTv")
    if r is not None:
        return r
    noms = o.reste or ["-"]
    code = 0
    numero = [0]
    for f in noms:
        d = lire_entree_ou_fichier(ctx, "cat", f)
        if d is None:
            code = 1
            continue
        if o.a("n", "--number", "b"):
            out = []
            for l in d.split(b"\n")[:-1] if d.endswith(b"\n") else d.split(b"\n"):
                if o.a("b") and not l:
                    out.append(b"")
                    continue
                numero[0] += 1
                out.append(f"{numero[0]:6d}\t".encode() + l)
            d2 = b"\n".join(out) + (b"\n" if d.endswith(b"\n") else b"")
            ctx.out(d2)
        elif o.a("A", "E"):
            ctx.out(d.replace(b"\n", b"$\n"))
        else:
            ctx.out(d)
        ctx.verifier()
    return code


@outil("tac")
def tac(ctx):
    code = 0
    for f in ctx.args[1:] or ["-"]:
        d = lire_entree_ou_fichier(ctx, "tac", f)
        if d is None:
            code = 1
            continue
        for l in reversed(lignes_de(d)):
            ctx.out(l + b"\n")
    return code


@outil("rev")
def rev(ctx):
    code = 0
    for f in ctx.args[1:] or ["-"]:
        d = lire_entree_ou_fichier(ctx, "rev", f)
        if d is None:
            code = 1
            continue
        t = d.decode("utf-8", "surrogateescape")
        lignes = t.split("\n")
        fin = t.endswith("\n")
        if fin:
            lignes.pop()
        for l in lignes:
            ctx.out(l[::-1] + "\n")
    return code


@outil("nl")
def nl(ctx):
    n = 0
    for f in [x for x in ctx.args[1:] if not x.startswith("-")] or ["-"]:
        d = lire_entree_ou_fichier(ctx, "nl", f)
        if d is None:
            return 1
        for l in lignes_de(d):
            if l.strip():
                n += 1
                ctx.out(f"{n:6d}\t".encode() + l + b"\n")
            else:
                ctx.out(b"       \n" if False else l + b"\n")
    return 0


# ---------------------------------------------------------------- head, tail
def _nombre_lignes(v):
    m = re.fullmatch(r"([+-]?)(\d+)([bkKmMgG]?)", v or "")
    if not m:
        return None
    n = int(m.group(2)) * {"": 1, "b": 512, "k": 1024, "K": 1024, "m": 1048576, "M": 1048576, "g": 1 << 30,
                           "G": 1 << 30}[m.group(3)]
    return m.group(1), n


@outil("head")
def head(ctx):
    o = Options(ctx.args[1:], avec_valeur="nc", longues=("quiet", "silent", "verbose", "help"),
                longues_valeur=("lines", "bytes"), chiffre="n")
    if o.erreur:
        return erreur_option(ctx, "head", o)
    r = verifier_lettres(ctx, "head", o, "ncqvz")
    if r is not None:
        return r
    octets = None
    n = ("", 10)
    for k, v in o.drapeaux:
        if k in ("n", "--lines"):
            x = _nombre_lignes(v)
            if x is None:
                ctx.err(f"head: invalid number of lines: {guillemets(v)}\n")
                return 1
            n, octets = x, None
        elif k in ("c", "--bytes"):
            x = _nombre_lignes(v)
            if x is None:
                ctx.err(f"head: invalid number of bytes: {guillemets(v)}\n")
                return 1
            octets = x
    noms = o.reste or ["-"]
    code = 0
    entetes = (len(noms) > 1 or o.a("v")) and not o.a("q", "--quiet")
    for k, f in enumerate(noms):
        d = lire_entree_ou_fichier(ctx, "head", f)
        if d is None:
            code = 1
            continue
        if entetes:
            ctx.out(("\n" if k else "") + f"==> {f if f != '-' else 'standard input'} <==\n")
        if octets:
            s, c = octets
            ctx.out(d[:max(0, len(d) - c)] if s == "-" else d[:c])
            continue
        s, c = n
        morceaux = d.split(b"\n")
        if s == "-":
            l = lignes_de(d)
            garde = l[:max(0, len(l) - c)]
            ctx.out(b"".join(x + b"\n" for x in garde))
        else:
            garde = morceaux[:c]
            texte = b"\n".join(garde)
            if len(morceaux) > c:
                texte += b"\n"
            ctx.out(texte)
    return code


@outil("tail")
def tail(ctx):
    o = Options(ctx.args[1:], avec_valeur="nc", longues=("quiet", "silent", "verbose", "follow", "help"),
                longues_valeur=("lines", "bytes"), chiffre="n")
    if o.erreur:
        return erreur_option(ctx, "tail", o)
    r = verifier_lettres(ctx, "tail", o, "ncqvfF")
    if r is not None:
        return r
    n, octets = ("", 10), None
    for k, v in o.drapeaux:
        if k in ("n", "--lines"):
            x = _nombre_lignes(v)
            if x is None:
                ctx.err(f"tail: invalid number of lines: {guillemets(v)}\n")
                return 1
            n = x
            octets = None
        elif k in ("c", "--bytes"):
            octets = _nombre_lignes(v)
    noms = o.reste or ["-"]
    code = 0
    entetes = (len(noms) > 1 or o.a("v")) and not o.a("q")
    for k, f in enumerate(noms):
        d = lire_entree_ou_fichier(ctx, "tail", f)
        if d is None:
            code = 1
            continue
        if entetes:
            ctx.out(("\n" if k else "") + f"==> {f if f != '-' else 'standard input'} <==\n")
        if octets:
            s, c = octets
            ctx.out(d[c - 1:] if s == "+" else (d[-c:] if c else b""))
            continue
        s, c = n
        l = lignes_de(d)
        fin_nl = d.endswith(b"\n")
        if s == "+":
            garde = l[max(0, c - 1):]
        else:
            garde = l[-c:] if c else []
        if garde:
            ctx.out(b"\n".join(garde) + (b"\n" if fin_nl or len(garde) < len(l) and False else b""))
            if not fin_nl and garde and garde[-1] is not l[-1]:
                ctx.out(b"\n")
    if o.a("f", "F", "--follow") and noms and noms[-1] != "-":
        # tail -f : on suit le fichier jusqu'à Ctrl+C
        vp = ctx.chemin(noms[-1])
        try:
            taille = len(ctx.vfs.lire(vp))
        except ErreurFs:
            return code
        while True:
            ctx.sh.dormir(0.5)
            try:
                d = ctx.vfs.lire(vp)
            except ErreurFs:
                continue
            if len(d) > taille:
                ctx.out(d[taille:])
                taille = len(d)
    return code


# ---------------------------------------------------------------- wc
@outil("wc")
def wc(ctx):
    o = Options(ctx.args[1:], longues=("lines", "words", "bytes", "chars", "max-line-length", "help"))
    if o.erreur:
        return erreur_option(ctx, "wc", o)
    r = verifier_lettres(ctx, "wc", o, "lwcmL")
    if r is not None:
        return r
    voulu = [k for k, x in (("l", ("l", "--lines")), ("w", ("w", "--words")), ("m", ("m", "--chars")),
                            ("c", ("c", "--bytes")), ("L", ("L", "--max-line-length"))) if o.a(*x)]
    if not voulu:
        voulu = ["l", "w", "c"]
    noms = o.reste or ["-"]
    res = []
    code = 0
    for f in noms:
        d = lire_entree_ou_fichier(ctx, "wc", f)
        if d is None:
            code = 1
            continue
        t = d.decode("utf-8", "replace")
        v = {"l": d.count(b"\n"), "w": len(d.split()), "c": len(d), "m": len(t),
             "L": max([len(x) for x in t.split("\n")] or [0])}
        res.append(([v[k] for k in voulu], f))
    if len(res) > 1:
        res.append(([sum(r_[0][i] for r_ in res) for i in range(len(voulu))], "total"))
    if not res:
        return code
    seul = len(voulu) == 1 and len(res) == 1
    if noms == ["-"] and len(voulu) > 1:
        larg = 7
    elif seul:
        larg = 1
    else:
        # GNU : la largeur vient de la taille des fichiers (le plus grand nombre d'octets)
        tout_fichiers = all(f != "-" for f in noms)
        if tout_fichiers:
            tailles = []
            for f in noms:
                try:
                    tailles.append(ctx.vfs.infos(ctx.chemin(f)).taille)
                except ErreurFs:
                    pass
            larg = len(str(sum(tailles))) if tailles else 1
            larg = max(larg, max(len(str(x)) for r_ in res for x in r_[0]))
        else:
            larg = max(7, max(len(str(x)) for r_ in res for x in r_[0]))
    for vals, f in res:
        ligne = " ".join(str(x).rjust(larg) for x in vals)
        ctx.out(ligne + ("" if f == "-" else " " + f) + "\n")
    return code


# ---------------------------------------------------------------- mkdir, rmdir, touch, rm
@outil("mkdir")
def mkdir(ctx):
    o = Options(ctx.args[1:], avec_valeur="m", longues=("parents", "verbose", "help"), longues_valeur=("mode",))
    if o.erreur:
        return erreur_option(ctx, "mkdir", o)
    r = verifier_lettres(ctx, "mkdir", o, "pvm")
    if r is not None:
        return r
    if not o.reste:
        ctx.err("mkdir: missing operand\nTry 'mkdir --help' for more information.\n")
        return 1
    parents = o.a("p", "--parents")
    mode = o.val("m", "--mode")
    code = 0
    for nm in o.reste:
        vp = ctx.chemin(nm)
        try:
            if parents:
                parts = [x for x in vp.split("/") if x]
                cur = ""
                for p in parts:
                    cur += "/" + p
                    if ctx.vfs.existe(cur):
                        if not ctx.vfs.est_dossier(cur):
                            raise ErreurFs(17 if cur == vp else 20)
                        continue
                    ctx.vfs.creer_dossier(cur)
                    if o.a("v"):
                        ctx.out(f"mkdir: created directory {guillemets(_rel(ctx, cur, nm, vp))}\n")
            else:
                parent = posixpath.dirname(vp)
                if not ctx.vfs.existe(parent):
                    raise ErreurFs(2)
                ctx.vfs.creer_dossier(vp)
                if o.a("v"):
                    ctx.out(f"mkdir: created directory {guillemets(nm)}\n")
            if mode:
                ctx.vfs.chmod(vp, int(mode, 8))
            elif ctx.vfs.mode == "windows":
                ctx.vfs.poser_mode(ctx.vfs.reel(vp), 0o777 & ~ctx.sh.umask)
            elif ctx.sh.umask != 0o022:
                ctx.vfs.chmod(vp, 0o777 & ~ctx.sh.umask)
        except ErreurFs as e:
            ctx.err(f"mkdir: cannot create directory {guillemets(nm)}: {e.texte}\n")
            code = 1
    return code


def _rel(ctx, cur, nm, vp):
    if nm.startswith("/"):
        return cur
    base = vp[:len(vp) - len(posixpath.normpath(nm))]
    return cur[len(base):] if cur.startswith(base) else cur


@outil("rmdir")
def rmdir(ctx):
    o = Options(ctx.args[1:], longues=("parents", "verbose", "ignore-fail-on-non-empty", "help"))
    if o.erreur:
        return erreur_option(ctx, "rmdir", o)
    if not o.reste:
        ctx.err("rmdir: missing operand\nTry 'rmdir --help' for more information.\n")
        return 1
    code = 0
    for nm in o.reste:
        vp = ctx.chemin(nm)
        try:
            if not ctx.vfs.existe(vp):
                raise ErreurFs(2)
            if not ctx.vfs.est_dossier(vp):
                raise ErreurFs(20)
            if ctx.vfs.lister(vp):
                raise ErreurFs(39)
            ctx.vfs.supprimer_dossier(vp)
            if o.a("p", "--parents"):
                p = posixpath.dirname(nm.rstrip("/"))
                while p and p not in (".", "/"):
                    ctx.vfs.supprimer_dossier(ctx.chemin(p))
                    p = posixpath.dirname(p)
        except ErreurFs as e:
            if e.errno == 39 and o.a("--ignore-fail-on-non-empty"):
                continue
            ctx.err(f"rmdir: failed to remove {guillemets(nm)}: {e.texte}\n")
            code = 1
    return code


@outil("touch")
def touch(ctx):
    o = Options(ctx.args[1:], avec_valeur="dtr", longues=("no-create", "help"), longues_valeur=("date", "reference"))
    if o.erreur:
        return erreur_option(ctx, "touch", o)
    if not o.reste:
        ctx.err("touch: missing file operand\nTry 'touch --help' for more information.\n")
        return 1
    quand = None
    ref = o.val("r", "--reference")
    if ref:
        try:
            quand = ctx.vfs.infos(ctx.chemin(ref)).mtime
        except ErreurFs as e:
            ctx.err(f"touch: failed to get attributes of {guillemets(ref)}: {e.texte}\n")
            return 1
    d = o.val("d", "--date")
    if d:
        quand = _date_depuis(d)
        if quand is None:
            ctx.err(f"touch: invalid date format {guillemets(d)}\n")
            return 1
    tt = o.val("t")
    if tt:
        m = re.fullmatch(r"(\d{2,4})?(\d{2})(\d{2})(\d{2})(\d{2})(?:\.(\d{2}))?", tt)
        if m:
            an = int(m.group(1)) if m.group(1) else datetime.datetime.now().year
            if m.group(1) and len(m.group(1)) == 2:
                an += 2000 if an < 69 else 1900
            quand = datetime.datetime(an, int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                                      int(m.group(6) or 0)).timestamp()
    code = 0
    for nm in o.reste:
        vp = ctx.chemin(nm)
        try:
            if o.a("c", "--no-create") and not ctx.vfs.existe(vp):
                continue
            nouveau = not ctx.vfs.existe(vp)
            ctx.vfs.toucher(vp)
            if nouveau and ctx.vfs.mode == "windows":
                ctx.vfs.poser_mode(ctx.vfs.reel(vp), 0o666 & ~ctx.sh.umask)
            elif nouveau and ctx.sh.umask != 0o022 and ctx.vfs.mode == "transparent":
                ctx.vfs.chmod(vp, 0o666 & ~ctx.sh.umask)
            if quand is not None:
                ctx.vfs.poser_date(vp, quand)
        except ErreurFs as e:
            ctx.err(f"touch: cannot touch {guillemets(nm)}: {e.texte}\n")
            code = 1
    return code


def _date_depuis(d):
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(d, f).timestamp()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d+) (day|days|hour|hours|minute|minutes) ago", d.strip())
    if m:
        s = {"day": 86400, "hour": 3600, "minute": 60}[m.group(2).rstrip("s")]
        return time.time() - int(m.group(1)) * s
    if d.strip() in ("now", "today"):
        return time.time()
    if d.strip() == "yesterday":
        return time.time() - 86400
    if d.startswith("@") and d[1:].isdigit():
        return float(d[1:])
    return None


@outil("rm")
def rm(ctx):
    o = Options(ctx.args[1:], longues=("recursive", "force", "verbose", "interactive", "dir", "help",
                                       "no-preserve-root"))
    if o.erreur:
        return erreur_option(ctx, "rm", o)
    r = verifier_lettres(ctx, "rm", o, "rRfvidI")
    if r is not None:
        return r
    force = o.a("f", "--force")
    rec = o.a("r", "R", "--recursive")
    if not o.reste:
        if force:
            return 0
        ctx.err("rm: missing operand\nTry 'rm --help' for more information.\n")
        return 1
    code = 0
    for nm in o.reste:
        vp = ctx.chemin(nm)
        if posixpath.basename(nm.rstrip("/")) in (".", ".."):
            ctx.err(f"rm: refusing to remove '.' or '..' directory: skipping {guillemets(nm)}\n")
            code = 1
            continue
        if vp == "/":
            ctx.err("rm: it is dangerous to operate recursively on '/'\nrm: use --no-preserve-root to override this failsafe\n")
            code = 1
            continue
        if not ctx.vfs.existe(vp):
            if not force:
                ctx.err(f"rm: cannot remove {guillemets(nm)}: No such file or directory\n")
                code = 1
            continue
        if ctx.vfs.est_dossier(vp):
            if not rec:
                if o.a("d", "--dir"):
                    try:
                        ctx.vfs.supprimer_dossier(vp)
                    except ErreurFs as e:
                        ctx.err(f"rm: cannot remove {guillemets(nm)}: {e.texte}\n")
                        code = 1
                    continue
                ctx.err(f"rm: cannot remove {guillemets(nm)}: Is a directory\n")
                code = 1
                continue
            if not _rm_rec(ctx, vp, nm, o.a("v")):
                code = 1
            continue
        try:
            ctx.vfs.supprimer_fichier(vp)
            if o.a("v", "--verbose"):
                ctx.out(f"removed {guillemets(nm)}\n")
        except ErreurFs as e:
            ctx.err(f"rm: cannot remove {guillemets(nm)}: {e.texte}\n")
            code = 1
    return code


def _rm_rec(ctx, vp, nm, bavard):
    ok = True
    try:
        noms = ctx.vfs.lister(vp)
    except ErreurFs as e:
        ctx.err(f"rm: cannot remove {guillemets(nm)}: {e.texte}\n")
        return False
    for x in sorted(noms):
        sv = vp.rstrip("/") + "/" + x
        sn = nm.rstrip("/") + "/" + x
        if ctx.vfs.est_dossier(sv):
            ok = _rm_rec(ctx, sv, sn, bavard) and ok
        else:
            try:
                ctx.vfs.supprimer_fichier(sv)
                if bavard:
                    ctx.out(f"removed {guillemets(sn)}\n")
            except ErreurFs as e:
                ctx.err(f"rm: cannot remove {guillemets(sn)}: {e.texte}\n")
                ok = False
    if ok:
        try:
            ctx.vfs.supprimer_dossier(vp)
            if bavard:
                ctx.out(f"removed directory {guillemets(nm)}\n")
        except ErreurFs as e:
            ctx.err(f"rm: cannot remove {guillemets(nm)}: {e.texte}\n")
            ok = False
    return ok


# ---------------------------------------------------------------- cp, mv
def _copier_fichier(ctx, src, dst, garder=False):
    d = ctx.vfs.lire(src)
    existait = ctx.vfs.existe(dst)
    ctx.vfs.ecrire(dst, d)
    inf = ctx.vfs.infos(src)
    if not existait:
        m = inf.mode & ~ctx.sh.umask if not garder else inf.mode
        if ctx.vfs.mode == "windows" or m != (0o666 & ~ctx.sh.umask) or inf.mode & 0o111 or garder:
            try:
                ctx.vfs.chmod(dst, m & 0o7777)
            except ErreurFs:
                pass
    if garder:
        ctx.vfs.poser_date(dst, inf.mtime)


@outil("cp")
def cp(ctx):
    o = Options(ctx.args[1:], avec_valeur="t", longues=("recursive", "force", "verbose", "interactive", "no-clobber",
                                                        "preserve", "archive", "help", "update"),
                longues_valeur=("target-directory",))
    if o.erreur:
        return erreur_option(ctx, "cp", o)
    r = verifier_lettres(ctx, "cp", o, "rRfvinpaut")
    if r is not None:
        return r
    rec = o.a("r", "R", "a", "--recursive", "--archive")
    garder = o.a("p", "a", "--preserve", "--archive")
    noms = o.reste
    cible_dir = o.val("t", "--target-directory")
    if cible_dir:
        noms = noms + [cible_dir]
    if not noms:
        ctx.err("cp: missing file operand\nTry 'cp --help' for more information.\n")
        return 1
    if len(noms) == 1:
        ctx.err(f"cp: missing destination file operand after {guillemets(noms[0])}\nTry 'cp --help' for more information.\n")
        return 1
    *srcs, dest = noms
    vd = ctx.chemin(dest)
    dest_dossier = ctx.vfs.est_dossier(vd)
    if len(srcs) > 1 and not dest_dossier:
        ctx.err(f"cp: target {guillemets(dest)} is not a directory\n")
        return 1
    code = 0
    for s in srcs:
        vs = ctx.chemin(s)
        if not ctx.vfs.existe(vs):
            ctx.err(f"cp: cannot stat {guillemets(s)}: No such file or directory\n")
            code = 1
            continue
        cible = posixpath.join(vd, posixpath.basename(vs.rstrip("/"))) if dest_dossier else vd
        cible_nom = posixpath.join(dest, posixpath.basename(s.rstrip("/"))) if dest_dossier else dest
        if ctx.vfs.est_dossier(vs):
            if not rec:
                ctx.err(f"cp: -r not specified; omitting directory {guillemets(s)}\n")
                code = 1
                continue
            if cible == vs or cible.startswith(vs.rstrip("/") + "/"):
                ctx.err(f"cp: cannot copy a directory, {guillemets(s)}, into itself, {guillemets(cible_nom)}\n")
                code = 1
                continue
            if not _cp_rec(ctx, vs, cible, s, cible_nom, garder, o.a("v")):
                code = 1
            continue
        if ctx.vfs.existe(cible) and ctx.vfs.infos(cible).inode == ctx.vfs.infos(vs).inode and \
                ctx.vfs.mode == "transparent" and posixpath.normpath(cible) == posixpath.normpath(vs):
            ctx.err(f"cp: {guillemets(s)} and {guillemets(cible_nom)} are the same file\n")
            code = 1
            continue
        if ctx.vfs.est_dossier(cible):
            ctx.err(f"cp: cannot overwrite directory {guillemets(cible_nom)} with non-directory\n")
            code = 1
            continue
        if o.a("n", "--no-clobber") and ctx.vfs.existe(cible):
            continue
        try:
            _copier_fichier(ctx, vs, cible, garder)
            if o.a("v"):
                ctx.out(f"{guillemets(s)} -> {guillemets(cible_nom)}\n")
        except ErreurFs as e:
            if e.errno == 13 and not ctx.vfs.ecriture_permise(cible) or (ctx.vfs.existe(cible)):
                ctx.err(f"cp: cannot create regular file {guillemets(cible_nom)}: {e.texte}\n")
            elif not ctx.vfs.existe(posixpath.dirname(cible)):
                ctx.err(f"cp: cannot create regular file {guillemets(cible_nom)}: No such file or directory\n")
            else:
                ctx.err(f"cp: cannot open {guillemets(s)} for reading: {e.texte}\n" if e.errno == 13 and
                        ctx.vfs.ecriture_permise(cible) else
                        f"cp: cannot create regular file {guillemets(cible_nom)}: {e.texte}\n")
            code = 1
    return code


def _cp_rec(ctx, vs, vd, s, d, garder, bavard):
    ok = True
    try:
        if not ctx.vfs.existe(vd):
            ctx.vfs.creer_dossier(vd)
            ctx.vfs.chmod(vd, ctx.vfs.infos(vs).mode)
        elif not ctx.vfs.est_dossier(vd):
            ctx.err(f"cp: cannot overwrite non-directory {guillemets(d)} with directory {guillemets(s)}\n")
            return False
        if bavard:
            ctx.out(f"{guillemets(s)} -> {guillemets(d)}\n")
        for x in sorted(ctx.vfs.lister(vs)):
            a, b = vs.rstrip("/") + "/" + x, vd.rstrip("/") + "/" + x
            if ctx.vfs.est_dossier(a):
                ok = _cp_rec(ctx, a, b, s.rstrip("/") + "/" + x, d.rstrip("/") + "/" + x, garder, bavard) and ok
            else:
                try:
                    _copier_fichier(ctx, a, b, garder)
                    if bavard:
                        ctx.out(f"{guillemets(s.rstrip('/') + '/' + x)} -> {guillemets(d.rstrip('/') + '/' + x)}\n")
                except ErreurFs as e:
                    ctx.err(f"cp: cannot create regular file {guillemets(d.rstrip('/') + '/' + x)}: {e.texte}\n")
                    ok = False
    except ErreurFs as e:
        ctx.err(f"cp: cannot create directory {guillemets(d)}: {e.texte}\n")
        return False
    return ok


@outil("mv")
def mv(ctx):
    o = Options(ctx.args[1:], avec_valeur="t", longues=("force", "verbose", "interactive", "no-clobber", "help"),
                longues_valeur=("target-directory",))
    if o.erreur:
        return erreur_option(ctx, "mv", o)
    r = verifier_lettres(ctx, "mv", o, "fvintu")
    if r is not None:
        return r
    noms = o.reste
    if o.val("t"):
        noms = noms + [o.val("t")]
    if not noms:
        ctx.err("mv: missing file operand\nTry 'mv --help' for more information.\n")
        return 1
    if len(noms) == 1:
        ctx.err(f"mv: missing destination file operand after {guillemets(noms[0])}\nTry 'mv --help' for more information.\n")
        return 1
    *srcs, dest = noms
    vd = ctx.chemin(dest)
    dest_dossier = ctx.vfs.est_dossier(vd)
    if len(srcs) > 1 and not dest_dossier:
        ctx.err(f"mv: target {guillemets(dest)} is not a directory\n")
        return 1
    code = 0
    for s in srcs:
        vs = ctx.chemin(s)
        if not ctx.vfs.existe(vs):
            ctx.err(f"mv: cannot stat {guillemets(s)}: No such file or directory\n")
            code = 1
            continue
        cible = posixpath.join(vd, posixpath.basename(vs)) if dest_dossier else vd
        cible_nom = posixpath.join(dest, posixpath.basename(s.rstrip("/"))) if dest_dossier else dest
        if cible == vs:
            ctx.err(f"mv: {guillemets(s)} and {guillemets(cible_nom)} are the same file\n")
            code = 1
            continue
        if ctx.vfs.est_dossier(vs) and (cible + "/").startswith(vs.rstrip("/") + "/"):
            ctx.err(f"mv: cannot move {guillemets(s)} to a subdirectory of itself, {guillemets(cible_nom)}\n")
            code = 1
            continue
        if ctx.vfs.est_dossier(cible) and not ctx.vfs.est_dossier(vs):
            ctx.err(f"mv: cannot overwrite directory {guillemets(cible_nom)} with non-directory\n")
            code = 1
            continue
        if ctx.vfs.est_dossier(cible) and ctx.vfs.est_dossier(vs) and ctx.vfs.lister(cible):
            ctx.err(f"mv: cannot move {guillemets(s)} to {guillemets(cible_nom)}: Directory not empty\n")
            code = 1
            continue
        if o.a("n") and ctx.vfs.existe(cible):
            continue
        try:
            if not ctx.vfs.existe(posixpath.dirname(cible)):
                raise ErreurFs(2)
            if ctx.vfs.est_dossier(cible) and ctx.vfs.est_dossier(vs):
                ctx.vfs.supprimer_dossier(cible)
            ctx.vfs.renommer(vs, cible)
            if o.a("v"):
                ctx.out(f"renamed {guillemets(s)} -> {guillemets(cible_nom)}\n")
        except ErreurFs as e:
            if not ctx.vfs.ecriture_permise(vs) and e.errno == 13:
                ctx.err(f"mv: cannot move {guillemets(s)} to {guillemets(cible_nom)}: {e.texte}\n")
            else:
                ctx.err(f"mv: cannot move {guillemets(s)} to {guillemets(cible_nom)}: {e.texte}\n")
            code = 1
    return code


# ---------------------------------------------------------------- chmod
def _mode_symbolique(spec, ancien, dossier, umask):
    m = ancien
    for clause in spec.split(","):
        mt = re.fullmatch(r"([ugoa]*)([-+=])([rwxXst]*|[ugo])", clause)
        if not mt:
            return None
        qui, op, quoi = mt.groups()
        sans_qui = not qui
        if not qui or "a" in qui:
            qui = "ugo"
        bits = 0
        if quoi in ("u", "g", "o"):
            src = {"u": (m >> 6) & 7, "g": (m >> 3) & 7, "o": m & 7}[quoi]
            for q in qui:
                bits |= src << {"u": 6, "g": 3, "o": 0}[q]
        else:
            for q in qui:
                dec = {"u": 6, "g": 3, "o": 0}[q]
                for c in quoi:
                    if c == "r":
                        bits |= 4 << dec
                    elif c == "w":
                        bits |= 2 << dec
                    elif c == "x" or (c == "X" and (dossier or ancien & 0o111)):
                        bits |= 1 << dec
                    elif c == "s" and q in "ug":
                        bits |= 0o4000 if q == "u" else 0o2000
                    elif c == "t" and q == "o":
                        bits |= 0o1000
            if sans_qui and op != "=":
                bits &= ~umask | 0o7000
        if op == "+":
            m |= bits
        elif op == "-":
            m &= ~bits
        else:
            masque = 0
            for q in qui:
                masque |= 7 << {"u": 6, "g": 3, "o": 0}[q]
            m = (m & ~masque) | bits
    return m


@outil("chmod")
def chmod(ctx):
    a = ctx.args[1:]
    rec = False
    bavard = False
    while a and re.fullmatch(r"-[Rvcf]+", a[0]):
        rec = rec or "R" in a[0]
        bavard = bavard or "v" in a[0]
        a = a[1:]
    if a and a[0] == "--":
        a = a[1:]
    if not a:
        ctx.err("chmod: missing operand\nTry 'chmod --help' for more information.\n")
        return 1
    spec = a[0]
    if len(a) < 2:
        ctx.err(f"chmod: missing operand after {guillemets(spec)}\nTry 'chmod --help' for more information.\n")
        return 1
    code = 0

    def appliquer(nm, vp):
        nonlocal code
        try:
            inf = ctx.vfs.infos(vp)
        except ErreurFs:
            ctx.err(f"chmod: cannot access {guillemets(nm)}: No such file or directory\n")
            code = 1
            return
        if re.fullmatch(r"[0-7]{1,4}", spec):
            m = int(spec, 8)
            if len(spec) <= 3 and inf.dossier:
                m |= inf.mode & 0o6000
        else:
            m = _mode_symbolique(spec, inf.mode, inf.dossier, ctx.sh.umask)
            if m is None:
                ctx.err(f"chmod: invalid mode: {guillemets(spec)}\nTry 'chmod --help' for more information.\n")
                code = 1
                return
        try:
            ctx.vfs.chmod(vp, m)
            if bavard:
                ctx.out(f"mode of {guillemets(nm)} changed from {inf.mode:04o} ({droits_texte(False, inf.mode)[1:]}) "
                        f"to {m:04o} ({droits_texte(False, m)[1:]})\n")
        except ErreurFs as e:
            ctx.err(f"chmod: changing permissions of {guillemets(nm)}: "
                    f"{'Operation not permitted' if e.errno == 13 else e.texte}\n")
            code = 1
            return
        if rec and inf.dossier:
            try:
                for x in sorted(ctx.vfs.lister(vp)):
                    appliquer(nm.rstrip("/") + "/" + x, vp.rstrip("/") + "/" + x)
            except ErreurFs:
                pass

    for nm in a[1:]:
        appliquer(nm, ctx.chemin(nm))
    return code


# ---------------------------------------------------------------- qui, où, quand
@outil("whoami")
def whoami(ctx):
    if len(ctx.args) > 1:
        ctx.err(f"whoami: extra operand {guillemets(ctx.args[1])}\nTry 'whoami --help' for more information.\n")
        return 1
    ctx.out(ctx.sh.vars.get("USER", ctx.vfs.utilisateur) + "\n" if ctx.vfs.mode == "windows" else _moi() + "\n")
    return 0


def _moi():
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except (ImportError, KeyError, AttributeError):
        from .vfs import nom_utilisateur
        return nom_utilisateur()


@outil("id")
def id_(ctx):
    u = ctx.vfs.utilisateur if ctx.vfs.mode == "windows" else _moi()
    if ctx.vfs.mode == "transparent":
        uid, gid = os.getuid(), os.getgid()
        try:
            import grp
            g = grp.getgrgid(gid).gr_name
        except (ImportError, KeyError):
            g = str(gid)
    else:
        uid, gid, g = 1000, 1000, u
    a = ctx.args[1:]
    if "-u" in a or "-un" in a or "-nu" in a:
        ctx.out((u if "n" in "".join(a) else str(uid)) + "\n")
        return 0
    if "-g" in a or "-gn" in a or "-ng" in a:
        ctx.out((g if "n" in "".join(a) else str(gid)) + "\n")
        return 0
    if "-n" in a:
        ctx.out(u + "\n")
        return 0
    ctx.out(f"uid={uid}({u}) gid={gid}({g}) groups={gid}({g})\n")
    return 0


@outil("hostname")
def hostname(ctx):
    from .vfs import nom_machine
    ctx.out(nom_machine() + "\n")
    return 0


@outil("uname")
def uname(ctx):
    import platform
    a = "".join(x.lstrip("-") for x in ctx.args[1:])
    if ctx.vfs.mode == "transparent":
        u = os.uname()
        vals = {"s": u.sysname, "n": u.nodename, "r": u.release, "v": u.version, "m": u.machine,
                "o": "GNU/Linux" if u.sysname == "Linux" else u.sysname}
    else:
        m = platform.machine().lower() or "x86_64"
        m = {"amd64": "x86_64", "arm64": "aarch64"}.get(m, m)
        from .vfs import nom_machine
        vals = {"s": "Linux", "n": nom_machine(), "r": "6.0.0-terminagotchi", "v": "#1 le terminal du jeu",
                "m": m, "o": "GNU/Linux"}
    if not a:
        a = "s"
    if "a" in a:
        ordre = "snrvmo"
        ctx.out(" ".join(vals[k] for k in "snrvm") + " " + vals["m"] + " " + vals["m"] + " " + vals["o"] + "\n")
        return 0
    ordre = "snrvmo"
    ctx.out(" ".join(vals[k] for k in ordre if k in a) + "\n")
    return 0


@outil("date")
def date(ctx):
    a = ctx.args[1:]
    utc = False
    quand = time.time()
    fmt = None
    i = 0
    while i < len(a):
        x = a[i]
        if x in ("-u", "--utc"):
            utc = True
        elif x.startswith("+"):
            fmt = x[1:]
        elif x in ("-d", "--date") and i + 1 < len(a):
            q = _date_depuis(a[i + 1])
            if q is None:
                ctx.err(f"date: invalid date {guillemets(a[i + 1])}\n")
                return 1
            quand = q
            i += 1
        elif x.startswith("--date="):
            quand = _date_depuis(x[7:]) or quand
        elif x == "-I":
            fmt = "%Y-%m-%d"
        elif x == "-R":
            fmt = "%a, %d %b %Y %H:%M:%S %z"
        i += 1
    d = datetime.datetime.fromtimestamp(quand, datetime.timezone.utc) if utc else \
        datetime.datetime.fromtimestamp(quand).astimezone()
    if fmt is None:
        tz = d.strftime("%Z") if not utc else "UTC"
        if not tz or " " in tz or len(tz) > 5:
            tz = d.strftime("%z")
        ctx.out(f"{_JOURS[d.weekday()]} {MOIS[d.month - 1]} {d.day:2d} {d:%H:%M:%S} {tz} {d.year}\n")
        return 0
    ctx.out(strftime_c(d, fmt) + "\n")
    return 0


_JOURS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_JOURS_L = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MOIS_L = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"]


def strftime_c(d, fmt):
    """strftime en anglais (LC_ALL=C), quelle que soit la langue de Windows."""
    out = []
    i = 0
    while i < len(fmt):
        c = fmt[i]
        if c != "%" or i + 1 >= len(fmt):
            out.append(c)
            i += 1
            continue
        k = fmt[i + 1]
        i += 2
        if k == "a":
            out.append(_JOURS[d.weekday()])
        elif k == "A":
            out.append(_JOURS_L[d.weekday()])
        elif k == "b" or k == "h":
            out.append(MOIS[d.month - 1])
        elif k == "B":
            out.append(_MOIS_L[d.month - 1])
        elif k == "e":
            out.append(f"{d.day:2d}")
        elif k == "s":
            out.append(str(int(d.timestamp())))
        elif k == "N":
            out.append(f"{d.microsecond * 1000:09d}")
        elif k == "n":
            out.append("\n")
        elif k == "t":
            out.append("\t")
        elif k == "%":
            out.append("%")
        elif k == "P":
            out.append("am" if d.hour < 12 else "pm")
        elif k == "p":
            out.append("AM" if d.hour < 12 else "PM")
        elif k == "Z":
            out.append(d.strftime("%Z") or "UTC")
        elif k == "c":
            out.append(f"{_JOURS[d.weekday()]} {MOIS[d.month - 1]} {d.day:2d} {d:%H:%M:%S} {d.year}")
        elif k == "D" or k == "x":
            out.append(d.strftime("%m/%d/%y"))
        else:
            try:
                out.append(d.strftime("%" + k))
            except ValueError:
                out.append("%" + k)
    return "".join(out)


@outil("sleep")
def sleep(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.err("sleep: missing operand\nTry 'sleep --help' for more information.\n")
        return 1
    total = 0.0
    for x in a:
        m = re.fullmatch(r"(\d*\.?\d+)([smhd]?)", x)
        if not m:
            ctx.err(f"sleep: invalid time interval {guillemets(x)}\nTry 'sleep --help' for more information.\n")
            return 1
        total += float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
    ctx.sh.dormir(total)
    return 0


@outil("seq")
def seq(ctx):
    a = ctx.args[1:]
    sep = "\n"
    fmt = None
    largeur_egale = False
    while a and a[0].startswith("-") and not re.fullmatch(r"-\d+(\.\d+)?", a[0]):
        if a[0] == "-s" and len(a) > 1:
            sep = a[1]
            a = a[2:]
        elif a[0].startswith("-s"):
            sep = a[0][2:]
            a = a[1:]
        elif a[0] == "-f" and len(a) > 1:
            fmt = a[1]
            a = a[2:]
        elif a[0] == "-w":
            largeur_egale = True
            a = a[1:]
        else:
            return option_inconnue(ctx, "seq", a[0][1:2])
    if not a:
        ctx.err("seq: missing operand\nTry 'seq --help' for more information.\n")
        return 1
    if len(a) > 3:
        ctx.err(f"seq: extra operand {guillemets(a[3])}\nTry 'seq --help' for more information.\n")
        return 1
    try:
        nums = [float(x) for x in a]
    except ValueError:
        mauvais = next(x for x in a if not re.fullmatch(r"[-+]?\d*\.?\d+", x))
        ctx.err(f"seq: invalid floating point argument: {guillemets(mauvais)}\nTry 'seq --help' for more information.\n")
        return 1
    debut, pas, fin = (1.0, 1.0, nums[0]) if len(nums) == 1 else (
        (nums[0], 1.0, nums[1]) if len(nums) == 2 else (nums[0], nums[1], nums[2]))
    entiers = all(re.fullmatch(r"[-+]?\d+", x) for x in a)
    decimales = max([len(x.split(".")[1]) for x in a if "." in x] or [0])
    vals = []
    v = debut
    k = 0
    while (pas > 0 and v <= fin + 1e-12) or (pas < 0 and v >= fin - 1e-12):
        vals.append(v)
        k += 1
        v = debut + k * pas
        if k > 10_000_000:
            break
        if k % 1000 == 0:
            ctx.verifier()
    if pas == 0:
        ctx.err(f"seq: invalid Zero increment value: {guillemets(a[1])}\nTry 'seq --help' for more information.\n")
        return 1
    if fmt:
        txt = [fmt % x for x in vals]
    elif entiers:
        txt = [str(int(x)) for x in vals]
    else:
        txt = [f"{x:.{decimales}f}" for x in vals]
    if largeur_egale and txt:
        w = max(len(t) for t in txt)
        txt = [t.zfill(w) if not t.startswith("-") else "-" + t[1:].zfill(w - 1) for t in txt]
    if txt:
        ctx.out(sep.join(txt) + "\n")
    return 0


@outil("yes")
def yes(ctx):
    texte = " ".join(ctx.args[1:]) or "y"
    n = 0
    while n < 20000:
        ctx.out(texte + "\n")
        n += 1
        if n % 200 == 0:
            ctx.verifier()
    return 0


@outil("basename")
def basename(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.err("basename: missing operand\nTry 'basename --help' for more information.\n")
        return 1
    tous = a[0] in ("-a", "--multiple")
    if tous:
        a = a[1:]
    suffixe = None
    if a and a[0] == "-s":
        suffixe = a[1]
        a = a[2:]
        tous = True
    if not tous and len(a) == 2:
        suffixe = a[1]
        a = a[:1]
    for x in a:
        b = x.rstrip("/").rsplit("/", 1)[-1] if x.strip("/") else "/"
        if suffixe and b.endswith(suffixe) and b != suffixe:
            b = b[:-len(suffixe)]
        ctx.out(b + "\n")
    return 0


@outil("dirname")
def dirname(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.err("dirname: missing operand\nTry 'dirname --help' for more information.\n")
        return 1
    for x in a:
        s = x.rstrip("/")
        if not s:
            ctx.out("/\n")
            continue
        if "/" not in s:
            ctx.out(".\n")
            continue
        d = s.rsplit("/", 1)[0].rstrip("/")
        ctx.out((d or "/") + "\n")
    return 0


@outil("realpath", "readlink")
def realpath(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    code = 0
    for x in a:
        vp = ctx.chemin(x)
        if ctx.args[0] == "realpath" and not ctx.vfs.existe(posixpath.dirname(vp)):
            ctx.err(f"realpath: {x}: No such file or directory\n")
            code = 1
            continue
        if ctx.args[0] == "readlink" and "-f" not in ctx.args:
            code = 1
            continue
        ctx.out(vp + "\n")
    return code


@outil("pwd")
def pwd_externe(ctx):
    ctx.out(ctx.sh.cwd + "\n")
    return 0


@outil("env", "printenv")
def env(ctx):
    a = ctx.args[1:]
    if ctx.args[0] == "printenv" and a:
        code = 0
        for x in a:
            if x in ctx.sh.exportees and x in ctx.sh.vars:
                ctx.out(ctx.sh.vars[x] + "\n")
            else:
                code = 1
        return code
    affect = []
    while a and "=" in a[0] and not a[0].startswith("="):
        affect.append(a[0].split("=", 1))
        a = a[1:]
    if a:
        return ctx.sh.lancer(a, ctx.entree, ctx.sortie, ctx.erreur, affect)
    vus = {k: ctx.sh.vars[k] for k in ctx.sh.exportees if k in ctx.sh.vars}
    vus["PWD"] = ctx.sh.cwd
    vus.update(dict(affect))
    for k in sorted(vus):
        ctx.out(f"{k}={vus[k]}\n")
    return 0


@outil("which")
def which(ctx):
    code = 0
    for x in [y for y in ctx.args[1:] if not y.startswith("-")]:
        if x in TOUS or (est_du_jeu(x) and ctx.sh.sur_jeu):
            ctx.out(("/usr/bin/" + x if x in TOUS else f"/usr/games/{x}") + "\n")
        else:
            code = 1
    return code


@outil("nproc")
def nproc(ctx):
    ctx.out(f"{os.cpu_count() or 1}\n")
    return 0


@outil("uptime")
def uptime(ctx):
    from .vfs import _DEMARRAGE
    d = datetime.datetime.now()
    s = int(time.time() - _DEMARRAGE)
    if "-p" in ctx.args:
        ctx.out(f"up {s // 60} minutes\n")
        return 0
    ctx.out(f" {d:%H:%M:%S} up {s // 3600}:{(s % 3600) // 60:02d},  1 user,  load average: 0.00, 0.00, 0.00\n")
    return 0


@outil("tty")
def tty(ctx):
    ctx.out("/dev/pts/0\n" if ctx.entree.tty else "not a tty\n")
    return 0 if ctx.entree.tty else 1


# ---------------------------------------------------------------- tee, xargs
@outil("tee")
def tee(ctx):
    o = Options(ctx.args[1:], longues=("append", "help"))
    ajout = o.a("a", "--append")
    d = ctx.entree.tout()
    code = 0
    for f in o.reste:
        vp = ctx.chemin(f)
        try:
            ctx.vfs.ecrire(vp, d, ajout=ajout)
        except ErreurFs as e:
            ctx.err(f"tee: {f}: {e.texte}\n")
            code = 1
    ctx.out(d)
    return code


@outil("xargs")
def xargs(ctx):
    a = ctx.args[1:]
    zero = False
    n_max = None
    remplacer = None
    vide_rien = False
    delim = None
    while a and a[0].startswith("-"):
        x = a[0]
        if x in ("-0", "--null"):
            zero = True
        elif x == "-n" and len(a) > 1:
            n_max = int(a[1])
            a = a[1:]
        elif x.startswith("-n") and x[2:].isdigit():
            n_max = int(x[2:])
        elif x == "-I" and len(a) > 1:
            remplacer = a[1]
            a = a[1:]
        elif x in ("-r", "--no-run-if-empty"):
            vide_rien = True
        elif x == "-d" and len(a) > 1:
            delim = a[1].encode().decode("unicode_escape")
            a = a[1:]
        elif x == "-t":
            pass
        else:
            break
        a = a[1:]
    cmd = a or ["echo"]
    d = ctx.entree.tout().decode("utf-8", "surrogateescape")
    if zero:
        elems = [x for x in d.split("\0") if x]
    elif delim:
        elems = [x for x in d.split(delim) if x]
    elif remplacer:
        elems = [x for x in d.split("\n") if x.strip()]
    else:
        import shlex
        try:
            elems = shlex.split(d)
        except ValueError:
            ctx.err("xargs: unmatched double quote; by default quotes are special to xargs unless you use the -0 option\n")
            return 1
    if not elems and vide_rien:
        return 0
    code = 0
    if remplacer:
        for e in elems:
            r = ctx.sh.lancer([x.replace(remplacer, e) for x in cmd], ctx.entree.__class__(b""), ctx.sortie, ctx.erreur)
            code = code or (123 if r else 0)
        return code
    paquets = [elems[i:i + n_max] for i in range(0, len(elems), n_max)] if n_max else [elems]
    for p in paquets:
        r = ctx.sh.lancer(cmd + p, ctx.entree.__class__(b""), ctx.sortie, ctx.erreur)
        if r == 127:
            return 127
        if r:
            code = 123
    return code


# ---------------------------------------------------------------- du, df, free
def _taille_du(ctx, vp, tout, sortie, base_nom, hum, profondeur, prof_max, octets):
    try:
        inf = ctx.vfs.infos(vp)
    except ErreurFs:
        return 0
    total = inf.taille if octets else _blocs_1k(inf)
    if inf.dossier:
        try:
            noms = sorted(ctx.vfs.lister(vp))
        except ErreurFs as e:
            ctx.err(f"du: cannot read directory {guillemets(base_nom)}: {e.texte}\n")
            noms = []
        for x in noms:
            sv, sn = vp.rstrip("/") + "/" + x, base_nom.rstrip("/") + "/" + x
            try:
                sinf = ctx.vfs.infos(sv)
            except ErreurFs:
                continue
            if sinf.dossier:
                total += _taille_du(ctx, sv, tout, sortie, sn, hum, profondeur + 1, prof_max, octets)
            else:
                t = sinf.taille if octets else _blocs_1k(sinf)
                total += t
                if tout and (prof_max is None or profondeur + 1 <= prof_max):
                    sortie.append((t, sn))
    if prof_max is None or profondeur <= prof_max:
        sortie.append((total, base_nom))
    return total


@outil("du")
def du(ctx):
    o = Options(ctx.args[1:], avec_valeur="d", longues=("summarize", "human-readable", "all", "total", "help",
                                                       "apparent-size", "bytes"),
                longues_valeur=("max-depth",))
    if o.erreur:
        return erreur_option(ctx, "du", o)
    r = verifier_lettres(ctx, "du", o, "shacdbkm")
    if r is not None:
        return r
    hum = o.a("h", "--human-readable")
    resume = o.a("s", "--summarize")
    octets = o.a("b", "--bytes", "--apparent-size")
    prof = o.val("d", "--max-depth")
    prof = 0 if resume else (int(prof) if prof is not None else None)
    noms = o.reste or ["."]
    code = 0
    total_g = 0
    for nm in noms:
        vp = ctx.chemin(nm)
        if not ctx.vfs.existe(vp):
            ctx.err(f"du: cannot access {guillemets(nm)}: No such file or directory\n")
            code = 1
            continue
        lignes = []
        total_g += _taille_du(ctx, vp, o.a("a", "--all"), lignes, nm, hum, 0, prof, octets)
        for t, n in lignes:
            v = humain(t if octets else t * 1024) if hum else str(t)
            ctx.out(f"{v}\t{n}\n")
    if o.a("c", "--total"):
        ctx.out(f"{humain(total_g * (1 if octets else 1024)) if hum else total_g}\ttotal\n")
    return code


@outil("df")
def df(ctx):
    import shutil
    hum = any("h" in x for x in ctx.args[1:] if x.startswith("-") and not x.startswith("--"))
    base = ctx.vfs.terrain_reel if ctx.vfs.terrain_reel.exists() else ctx.vfs.home_reel
    try:
        u = shutil.disk_usage(str(base))
    except OSError:
        return 1
    nom = (ctx.vfs.home_reel.anchor or "/dev/disque").rstrip("\\") or "/dev/disque"
    pct = f"{(u.used * 100 + u.total - 1) // u.total if u.total else 0}%"
    if hum:
        ctx.out("Filesystem      Size  Used Avail Use% Mounted on\n")
        ctx.out(f"{nom:<15} {humain(u.total):>4} {humain(u.used):>5} {humain(u.free):>5} {pct:>4} /\n")
    else:
        ctx.out("Filesystem     1K-blocks      Used Available Use% Mounted on\n")
        ctx.out(f"{nom:<14} {u.total // 1024:>9} {u.used // 1024:>9} {u.free // 1024:>9} {pct:>4} /\n")
    return 0


@outil("free")
def free(ctx):
    from .vfs import _memoire_totale
    total = _memoire_totale()
    libre = _memoire_libre()
    hum = "-h" in ctx.args
    def f(n):
        if not hum:
            return str(n // 1024)
        for u in ("Ki", "Mi", "Gi", "Ti"):
            n /= 1024
            if n < 1024:
                return f"{n:.1f}{u}" if n < 10 else f"{n:.0f}{u}"
        return f"{n:.0f}Ti"
    utilise = max(0, total - libre)
    ctx.out("               total        used        free      shared  buff/cache   available\n")
    ctx.out(f"Mem:    {f(total):>12}{f(utilise):>12}{f(libre):>12}{f(0):>12}{f(0):>12}{f(libre):>12}\n")
    ctx.out(f"Swap:   {f(0):>12}{f(0):>12}{f(0):>12}\n")
    return 0


def _memoire_libre():
    if os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.ullAvailPhys)
        except Exception:                   # noqa: BLE001
            return 0
    try:
        with open("/proc/meminfo") as f:
            for l in f:
                if l.startswith("MemAvailable:"):
                    return int(l.split()[1]) * 1024
    except OSError:
        pass
    return 0


# ---------------------------------------------------------------- ps (les tâches du terminal du jeu)
@outil("ps")
def ps(ctx):
    a = " ".join(ctx.args[1:])
    taches = [t for t in ctx.sh.taches if t.code is None]
    moi = ctx.vfs.utilisateur
    pid_sh = ctx.sh.pid_shell()
    lignes = [(pid_sh, "sh", "Ss", "-sh")] + [(t.pid, t.texte.rstrip(" &").split()[0], "S", t.texte.rstrip(" &"))
                                              for t in taches]
    from .processus import processus_du_jeu
    for pid, cmd in processus_du_jeu():                # les processus simulés du jeu (Citadelle, Poste de Contrôle)
        lignes.append((pid, cmd.split()[0], "S", cmd))
    pid_ps = ctx.sh.prochain_pid + 1
    lignes.append((pid_ps, "ps", "R+", "ps " + a if a else "ps"))
    if "args" in a or "comm" in a or "-o" in a:          # ps -eo args, ps -o comm= -p PID
        titre = not re.search(r"(args|comm|cmd)=", a)
        voulus = None
        if "-p" in ctx.args:
            k = ctx.args.index("-p")
            voulus = {int(x) for x in re.split(r"[ ,]", ctx.args[k + 1]) if x.isdigit()} if k + 1 < len(ctx.args) else set()
        if titre:
            ctx.out(("COMMAND" if "args" in a else "COMMAND") + "\n")
        trouve = False
        for pid, nom, _s, cmd in lignes:
            if voulus is not None and pid not in voulus:
                continue
            trouve = True
            ctx.out((cmd if "args" in a or "cmd" in a else nom) + "\n")
        return 0 if trouve or voulus is None else 1
    if "aux" in a or "-e" in a or "ax" in a or "-ef" in a:
        if "-ef" in a or "-e" in a and "f" in a:
            ctx.out("UID          PID    PPID  C STIME TTY          TIME CMD\n")
            for pid, _n, _s, cmd in lignes:
                ctx.out(f"{moi:<8} {pid:>7} {pid_sh if pid != pid_sh else 1:>7}  0 {time.strftime('%H:%M')} pts/0    "
                        f"00:00:00 {cmd}\n")
            return 0
        ctx.out("USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n")
        for pid, _n, s, cmd in lignes:
            ctx.out(f"{moi:<10} {pid:>5}  0.0  0.0   2600  1200 pts/0    {s:<4} {time.strftime('%H:%M')}   0:00 {cmd}\n")
        return 0
    ctx.out("    PID TTY          TIME CMD\n")
    for pid, nom, _s, _c in lignes:
        ctx.out(f"{pid:>7} pts/0    00:00:00 {nom}\n")
    return 0


@outil("pgrep", "pidof")
def pgrep(ctx):
    from .processus import processus_du_jeu
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    trouve = [t.pid for t in ctx.sh.taches if t.code is None and a and a[0] in t.texte]
    trouve += [pid for pid, cmd in processus_du_jeu() if a and a[0] in cmd]
    for pid in sorted(trouve):
        ctx.out(f"{pid}\n")
    return 0 if trouve else 1


@outil("killall", "pkill")
def killall(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    trouve = [t for t in ctx.sh.taches if t.code is None and a and t.texte.split()[0] == a[0]]
    for t in trouve:
        t.signal = "Terminated"
        t.arret.set()
    if not trouve and ctx.args[0] == "killall" and a:
        ctx.err(f"{a[0]}: no process found\n")
    return 0 if trouve else 1


@outil("timeout")
def timeout(ctx):
    a = ctx.args[1:]
    while a and a[0].startswith("-"):
        if a[0] in ("-s", "-k") and len(a) > 1:
            a = a[2:]
        else:
            a = a[1:]
    if len(a) < 2:
        ctx.err("timeout: missing operand\nTry 'timeout --help' for more information.\n")
        return 125
    m = re.fullmatch(r"(\d*\.?\d+)([smhd]?)", a[0])
    if not m:
        ctx.err(f"timeout: invalid time interval {guillemets(a[0])}\n")
        return 125
    duree = float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
    import threading
    sh = ctx.sh
    ancien = sh.arret
    nouveau = threading.Event()
    sh.arret = nouveau
    minuteur = threading.Timer(duree, nouveau.set)
    relais = threading.Thread(target=lambda: (ancien.wait(duree + 1), nouveau.set() if ancien.is_set() else None),
                              daemon=True)
    minuteur.start()
    relais.start()
    from .shell import Interrompu
    try:
        return sh.lancer(a[1:], ctx.entree, ctx.sortie, ctx.erreur)
    except Interrompu:
        if ancien.is_set():
            raise
        return 124
    finally:
        minuteur.cancel()
        sh.arret = ancien


# ---------------------------------------------------------------- stat, file
@outil("stat")
def stat_(ctx):
    a = ctx.args[1:]
    fmt = None
    if a and a[0] in ("-c", "--format") and len(a) > 1:
        fmt = a[1]
        a = a[2:]
    elif a and a[0].startswith("--format="):
        fmt = a[0][9:]
        a = a[1:]
    elif a and a[0].startswith("-c"):
        fmt = a[0][2:]
        a = a[1:]
    code = 0
    for x in a:
        try:
            inf = ctx.vfs.infos(ctx.chemin(x))
        except ErreurFs as e:
            ctx.err(f"stat: cannot statx {guillemets(x)}: {e.texte}\n")
            code = 1
            continue
        if fmt:
            r = fmt
            r = r.replace("%a", f"{inf.mode:o}").replace("%A", droits_texte(inf.dossier, inf.mode))
            r = r.replace("%s", str(inf.taille)).replace("%n", x).replace("%U", inf.proprio).replace("%G", inf.groupe)
            r = r.replace("%F", "directory" if inf.dossier else ("regular file" if inf.taille else "regular empty file"))
            r = r.replace("%Y", str(int(inf.mtime))).replace("%h", str(inf.liens))
            ctx.out(r + "\n")
            continue
        d = datetime.datetime.fromtimestamp(inf.mtime).astimezone()
        quand = d.strftime("%Y-%m-%d %H:%M:%S.%f000 %z")
        genre = "directory" if inf.dossier else ("regular file" if inf.taille else "regular empty file")
        ctx.out(f"  File: {x}\n  Size: {inf.taille:<15} Blocks: {_blocs_1k(inf) * 2:<10} IO Block: 4096   {genre}\n"
                f"Device: 0,0\tInode: {inf.inode:<11} Links: {inf.liens}\n"
                f"Access: (0{inf.mode:o}/{droits_texte(inf.dossier, inf.mode)})  Uid: ( 1000/{inf.proprio:>8})   "
                f"Gid: ( 1000/{inf.groupe:>8})\nAccess: {quand}\nModify: {quand}\nChange: {quand}\n Birth: -\n")
    return code


@outil("file")
def file_(ctx):
    code = 0
    for x in [y for y in ctx.args[1:] if not y.startswith("-")]:
        vp = ctx.chemin(x)
        if not ctx.vfs.existe(vp):
            ctx.out(f"{x}: cannot open `{x}' (No such file or directory)\n")
            continue
        if ctx.vfs.est_dossier(vp):
            ctx.out(f"{x}: directory\n")
            continue
        try:
            d = ctx.vfs.lire(vp)
        except ErreurFs as e:
            ctx.out(f"{x}: regular file, no read permission\n" if e.errno == 13 else f"{x}: {e.texte}\n")
            continue
        ctx.out(f"{x}: {_genre_fichier(d)}\n")
    return code


def _genre_fichier(d):
    if not d:
        return "empty"
    if d.startswith(b"\x89PNG"):
        return "PNG image data"
    if d.startswith(b"\xff\xd8"):
        return "JPEG image data"
    if d.startswith(b"\x1f\x8b"):
        return "gzip compressed data"
    if d.startswith(b"PK"):
        return "Zip archive data"
    if d.startswith(b"%PDF"):
        return "PDF document"
    if d.startswith(b"\x7fELF"):
        return "ELF 64-bit LSB executable"
    if d.startswith(b"#!"):
        prem = d.split(b"\n", 1)[0].decode("utf-8", "replace")
        prog = prem.split("/")[-1].split()[-1]
        return f"POSIX shell script, ASCII text executable" if prog in ("sh", "bash", "dash") else \
            f"{prog} script, ASCII text executable"
    try:
        t = d.decode("utf-8")
    except UnicodeDecodeError:
        return "data"
    if "\0" in t:
        return "data"
    return ("ASCII text" if t.isascii() else "Unicode text, UTF-8 text") + \
        (", with no line terminators" if not t.endswith("\n") else "")


# ---------------------------------------------------------------- tree
@outil("tree")
def tree(ctx):
    a = ctx.args[1:]
    tous = "-a" in a
    seuls_dossiers = "-d" in a
    niveau = None
    if "-L" in a:
        k = a.index("-L")
        try:
            niveau = int(a[k + 1])
        except (IndexError, ValueError):
            ctx.err("tree: Invalid level, must be greater than 0.\n")
            return 1
        a = a[:k] + a[k + 2:]
    noms = [x for x in a if not x.startswith("-")] or ["."]
    nd = nf = 0
    tty = ctx.sortie.tty
    # les traits : ceux de l'UTF-8 (└──), en ASCII (`--) quand la langue du terminal n'est pas en UTF-8 (LC_ALL=C)
    loc = next((ctx.sh.vars.get(v) for v in ("LC_ALL", "LC_CTYPE", "LANG") if ctx.sh.vars.get(v)), "C.UTF-8")
    utf8 = "utf-8" in loc.lower() or "utf8" in loc.lower()
    T_DER, T_MIL, T_VID, T_BAR = ("└── ", "├── ", "    ", "│   ") if utf8 else ("`-- ", "|-- ", "    ", "|   ")

    def parcourir(vp, prefixe, prof):
        nonlocal nd, nf
        try:
            noms_ = ctx.vfs.lister(vp)
        except ErreurFs:
            return
        if not tous:
            noms_ = [x for x in noms_ if not x.startswith(".")]
        noms_ = sorted(noms_, key=_cle_tree)
        elems = []
        for x in noms_:
            sv = vp.rstrip("/") + "/" + x
            try:
                inf = ctx.vfs.infos(sv)
            except ErreurFs:
                continue
            if seuls_dossiers and not inf.dossier:
                continue
            elems.append((x, sv, inf))
        for k, (x, sv, inf) in enumerate(elems):
            dernier = k == len(elems) - 1
            ctx.out(prefixe + (T_DER if dernier else T_MIL) + _colorer(x, inf, tty) + "\n")
            if inf.dossier:
                nd += 1
                if niveau is None or prof + 1 < niveau:
                    parcourir(sv, prefixe + (T_VID if dernier else T_BAR), prof + 1)
            else:
                nf += 1

    code = 0
    for nm in noms:
        vp = ctx.chemin(nm)
        if not ctx.vfs.est_dossier(vp):
            ctx.out(f"{nm}  [error opening dir]\n")
            code = 2
            continue
        ctx.out(_colorer(nm, ctx.vfs.infos(vp), tty) + "\n")
        nd += 1                                  # (tree 2 compte aussi le dossier de départ)
        parcourir(vp, "", 0)
    ctx.out(f"\n{nd} director{'y' if nd == 1 else 'ies'}" + ("" if seuls_dossiers else f", {nf} file{'' if nf == 1 else 's'}") + "\n")
    return code


def _cle_tree(n):
    """tree trie comme les locales (sans tenir compte des majuscules) ; en C, par octets."""
    return n.encode("utf-8")


# ---------------------------------------------------------------- less, more, man
@outil("less", "more", "most")
def less(ctx):
    noms = [x for x in ctx.args[1:] if not x.startswith("-") and not x.startswith("+")]
    if not noms:
        d = ctx.entree.tout()
        ctx.out(d)
        return 0
    code = 0
    for f in noms:
        vp = ctx.chemin(f)
        if not ctx.vfs.existe(vp):
            ctx.err(f"{f}: No such file or directory\n")
            code = 1
            continue
        if ctx.vfs.est_dossier(vp):
            ctx.err(f"{f} is a directory\n")
            code = 1
            continue
        try:
            d = ctx.vfs.lire(vp)
        except ErreurFs as e:
            ctx.err(f"{f}: {e.texte}\n")
            code = 1
            continue
        if ctx.sortie.tty and hasattr(ctx.sh, "pager") and ctx.sh.pager:
            ctx.sh.pager(d.decode("utf-8", "replace"), f)
        else:
            ctx.out(d)
    return code


@outil("man")
def man(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    if not a:
        ctx.err("What manual page do you want?\nFor example, try 'man man'.\n")
        return 1
    from .aide import page_man
    texte = page_man(a[-1])
    if texte is None:
        ctx.err(f"No manual entry for {a[-1]}\n")
        return 16
    if ctx.sortie.tty and getattr(ctx.sh, "pager", None):
        ctx.sh.pager(texte, f"{a[-1]}(1)")
    else:
        ctx.out(texte)
    return 0


@outil("whatis", "apropos")
def apropos(ctx):
    from .aide import resume
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    code = 0
    for x in a:
        r = resume(x) if ctx.args[0] == "whatis" else None
        if ctx.args[0] == "apropos":
            from .aide import chercher
            lignes = chercher(x)
            if not lignes:
                ctx.out(f"{x}: nothing appropriate.\n")
                code = 16
            for l in lignes:
                ctx.out(l + "\n")
            continue
        if r:
            ctx.out(f"{x:<15} (1)  - {r}\n")
        else:
            ctx.out(f"{x}: nothing appropriate.\n")
            code = 16
    return code


# ---------------------------------------------------------------- les commandes absentes : racontées
# les vraies commandes de Linux qui n'existent pas dans le terminal du jeu (réseau, matériel, système, compilateurs…)
RACONTEES = {
    "ping", "wget", "ssh", "scp", "sftp", "ssh-keygen", "ssh-copy-id", "nslookup", "host", "dig", "traceroute",
    "tracepath", "mtr", "ip", "ifconfig", "ss", "netstat", "nc", "nmap", "iw", "nmcli", "rfkill", "iwconfig",
    "bluetoothctl", "hcitool", "meshtastic", "getent", "arp", "route",
    "sudo", "su", "doas", "systemctl", "journalctl", "service", "dmesg", "lsblk", "lspci", "lsusb", "lsmod", "lscpu",
    "lshw", "mount", "umount", "fdisk", "parted", "mkfs", "blkid", "systemd-analyze", "crontab", "at", "useradd",
    "adduser", "passwd", "usermod", "groupadd", "chown", "chgrp", "top", "htop", "btop", "vmstat", "iostat",
    "apt", "apt-get", "dnf", "yum", "pacman", "zypper", "apk", "snap", "flatpak", "dpkg", "rpm", "pkg", "brew",
    "gcc", "g++", "cc", "clang", "make", "cmake", "ldd", "gdb", "strace", "ltrace", "objdump", "nm", "javac", "java",
    "node", "npm", "npx", "cargo", "rustc", "go", "ruby", "perl", "php", "lua",
    "pip", "pip3", "shellcheck",
    "podman", "docker", "virsh", "qemu-img", "qemu-system-x86_64", "vagrant",
    "magick", "convert", "ffmpeg", "sox", "exiftool", "openscad", "gimp", "inkscape",
    "nano", "vim", "vi", "nvim", "emacs", "code", "gedit", "notepad",
    "termux-toast", "termux-vibrate", "termux-torch", "termux-battery-status", "termux-clipboard-set",
    "termux-clipboard-get", "termux-tts-speak", "termux-open-url", "termux-open", "am", "pm",
    "xdg-open", "open", "firefox", "zsh", "fish", "ksh", "mksh", "screen", "tmux", "watch", "lsof", "fuser",
    "shutdown", "reboot", "poweroff", "halt", "chroot", "ln", "nohup", "setsid", "nice", "renice", "ionice",
    "openssl", "gpg", "gpg2", "gpgconf", "gpg-agent",
}


def raconter(ctx, nom, code=127):
    """Une commande qui n'existe pas ici : on le dit clairement (le jeu raconte l'étape)."""
    from ..langue import t
    ctx.err(t("vsh.absente", cmd=nom) + "\n")
    return code


def inconnue(ctx):
    nom = ctx.args[0]
    if nom in RACONTEES or nom.lower() in RACONTEES:
        return raconter(ctx, nom)
    from .. import core
    if nom.lower() in core.PS_CMDLETS or re.fullmatch(r"[A-Za-z]+-[A-Za-z]+", nom) and nom.lower() in core.PS_CMDLETS:
        from ..langue import t
        ctx.err(ctx.sh.prefixe() + f"{nom}: command not found\n" + t("vsh.cmdlet", cmd=nom,
                                                                 linux=core.PS_CMDLETS[nom.lower()]) + "\n")
        return 127
    if nom.lower() in CMD_WINDOWS:              # une habitude de l'invite de commandes de Windows (cmd.exe)
        from ..langue import t
        ctx.err(ctx.sh.prefixe() + f"{nom}: command not found\n" + t("vsh.cmd", cmd=nom,
                                                                 linux=CMD_WINDOWS[nom.lower()]) + "\n")
        return 127
    ctx.err(ctx.sh.prefixe() + f"{nom}: command not found\n")
    return 127


# les habitudes de l'invite de commandes de Windows : la commande Linux qui fait pareil (seulement un conseil)
CMD_WINDOWS = {"cls": "clear", "cd..": "cd ..", "cd\\": "cd /", "del": "rm", "erase": "rm", "copy": "cp",
               "xcopy": "cp -r", "move": "mv", "md": "mkdir", "rd": "rmdir", "ren": "mv", "rename": "mv",
               "findstr": "grep", "where": "which", "tasklist": "ps", "taskkill": "kill", "explorer": "ls",
               "start": "ls", "ver": "uname -a", "systeminfo": "uname -a", "attrib": "ls -l", "fc": "diff",
               "sort.exe": "sort", "more.com": "less"}


# les commandes du jeu (le compagnon : tg, carte, quetes… ; les mondes : port, crypte, atelier…)
DU_JEU = {"tg", "carte", "quetes", "explique", "entrainement", "exercice", "badges", "guide", "types", "equipe", "aide",
          "deploie", "espace", "cerveau", "port", "citadelle", "crypte", "machines", "ondes", "mesh-envoie",
          "mesh-coupe", "mesh-route", "guilde", "observatoire", "assistant", "agent", "devine-type", "devine-mot",
          "donnees", "forge", "atelier", "sommet", "temps", "controle"}


def est_du_jeu(nom):
    return nom in DU_JEU


def args_du_jeu(args):
    """`carte` → tg carte ; `mesh-coupe x` → tg ondes mesh-coupe x ; `exercice` → tg entrainement ; `tg …` → …"""
    nom = args[0]
    if nom == "tg":
        return list(args[1:])
    if nom == "exercice":
        return ["entrainement"] + list(args[1:])
    if nom.startswith("mesh-"):
        return ["ondes", nom] + list(args[1:])
    return [nom] + list(args[1:])


GARDEES = {"PATH", "HOME", "PWD", "OLDPWD", "SHELL", "USER", "LOGNAME", "TERM", "LANG", "HOSTNAME", "IFS", "PS1", "PS2"}


def variables_exportees(sh):
    """Les variables que l'enfant a exportées (export COULEUR=bleu) : le jeu les voit, comme un programme lancé par bash
    (sauf celles du système : PATH, HOME… restent celles de l'ordinateur)."""
    return {k: v for k, v in sh.vars.items() if k in sh.exportees and k not in GARDEES and v is not None}


def lanceur_du_jeu(vfs, commande=None, env_en_plus=None):
    """Une fonction (args, ctx) → code qui lance une commande du jeu (tg …) dans le vrai dossier du terminal, sa sortie
    vers ctx (pour CoquilleVirtuelle : les tests et les petits terminaux du jeu)."""
    import subprocess
    import sys as _sys

    def lancer(args, ctx):
        if commande is None:
            racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cmd = [_sys.executable, "-c", f"import sys; sys.path.insert(0, {racine!r}); from tg import app; "
                                         "sys.argv = ['tg'] + sys.argv[1:]; app._main()"]
        else:
            cmd = list(commande)
        reste = args_du_jeu(args)
        cwd = vfs.reel(ctx.sh.cwd) if vfs.mode == "windows" else ctx.sh.cwd
        if cwd is None or not os.path.isdir(str(cwd)):
            cwd = str(vfs.home_reel)
        env = dict(os.environ, TG_DANS_LE_JEU="1", TG_ICI=vfs.pour_le_jeu(ctx.sh.cwd), **(env_en_plus or {}))
        env.update(variables_exportees(ctx.sh))
        return lancer_programme(cmd + reste, str(cwd), env, ctx, capture=True)
    return lancer


def lancer_programme(cmd, cwd, env, ctx, capture=True):
    """Lance un programme du jeu (python … tg …) ; Ctrl+C, `timeout` ou `kill` l'interrompent comme un vrai
    programme (SIGINT ; sous Windows, il est arrêté). Sa sortie va vers ctx (capture) ou directement à l'écran."""
    import subprocess
    import signal
    import threading
    arret = None
    if os.name == "nt":                          # pas de SIGINT sous Windows : un petit fichier fait le Ctrl+C
        import tempfile
        fd, arret = tempfile.mkstemp(prefix="tg_arret_", dir=str(ctx.sh.vfs.jeu_reel / "tmp")
                                     if (ctx.sh.vfs.jeu_reel / "tmp").is_dir() else None)
        os.close(fd)
        os.remove(arret)
        env = dict(env, TG_ARRET=arret)
    kw = {"cwd": cwd, "env": env}
    if capture:
        kw.update(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        p = subprocess.Popen(cmd, **kw)
    except OSError as e:
        ctx.err(f"tg: {e}\n")
        return 1
    morceaux = {"out": [], "err": []}
    fils = []
    if capture:
        for nom, flux in (("out", p.stdout), ("err", p.stderr)):
            f = threading.Thread(target=lambda n=nom, x=flux: morceaux[n].append(x.read()), daemon=True)
            f.start()
            fils.append(f)
    interrompu = False
    try:
        while True:
            try:
                p.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                pass
            if ctx.sh.arret.is_set() and not interrompu:
                interrompu = True
                try:
                    if arret:
                        open(arret, "w").close()
                        try:
                            p.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            p.terminate()
                    else:
                        p.send_signal(signal.SIGINT)
                except OSError:
                    pass
    except KeyboardInterrupt:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
        raise
    for f in fils:
        f.join(5)
    if arret:
        try:
            os.remove(arret)
        except OSError:
            pass
    if capture:
        sortie, erreurs = b"".join(morceaux["out"]), b"".join(morceaux["err"])
        if os.name == "nt":                      # print() de Windows écrit \r\n : le terminal du jeu garde \n
            sortie, erreurs = sortie.replace(b"\r\n", b"\n"), erreurs.replace(b"\r\n", b"\n")
        ctx.out(sortie)
        ctx.err(erreurs)
    if interrompu:
        from .shell import Interrompu
        raise Interrompu()
    return p.returncode


# les autres familles de commandes (texte, archives, empreintes, git…) s'inscrivent ici
from . import texte  # noqa: E402,F401
from . import fichiers  # noqa: E402,F401
from . import git as _git  # noqa: E402
from . import python as _python  # noqa: E402,F401  (python3 : le Python du jeu, dans le terrain seulement)
from . import curl as _curl  # noqa: E402,F401      (curl : seulement le phare du Port, 127.0.0.1:8042)

TOUS["git"] = _git._outil


def usage_raconte(texte):
    """La ligne utilise une commande qui EXISTE dans le terminal du jeu, mais d'une façon qu'il raconte : `python3 -m
    http.server` (pas de module), `curl` vers une autre adresse que le phare du Port. Renvoie le nom de la commande
    (le jeu raconte alors l'étape, comme pour une commande absente), sinon None."""
    from ..verif import _couper
    for morceau, _sep in _couper(texte or "", ("||", "&&", "|", ";", "&")):
        mots = _python.mots(morceau.strip())
        while mots and re.match(r"^[A-Za-z_]\w*=", mots[0]):
            mots = mots[1:]
        if mots and mots[0] == "timeout":           # timeout -s INT 2 python3 … : la commande après la durée
            k = 1
            while k < len(mots) and mots[k].startswith("-"):
                k += 2 if mots[k] in ("-s", "-k", "--signal", "--kill-after") else 1
            mots = mots[k + 1:]
        propres, k = [], 0
        while k < len(mots):                     # sans les redirections (2>&1, > f, <f…)
            m = re.match(r"^\d*(>>|>&|<&|>|<)(.*)$", mots[k])
            if m:
                k += 1 if m.group(2) else 2
                continue
            propres.append(mots[k])
            k += 1
        mots = propres
        if not mots:
            continue
        if mots[0] in ("python3", "python") and _python.usage_raconte(mots):
            return mots[0]
        if mots[0] == "curl" and _curl.usage_raconte(mots):
            return "curl"
    return None


# ---------------------------------------------------------------- mktemp, numfmt
@outil("mktemp")
def mktemp(ctx):
    import secrets
    a = ctx.args[1:]
    dossier = "-d" in a or "--directory" in a
    modele = next((x for x in a if not x.startswith("-")), None)
    base_tmp = "-p" in a or "--tmpdir" in a or modele is None
    if modele is None:
        modele = "tmp.XXXXXXXXXX"
    m = re.search(r"X{3,}$", modele)
    if not m:
        ctx.err(f"mktemp: too few X's in template {guillemets(modele)}\n")
        return 1
    lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(100):
        nom = modele[:m.start()] + "".join(secrets.choice(lettres) for _ in range(len(m.group())))
        chemin = ("/tmp/" + nom) if base_tmp and "/" not in modele else nom
        vp = ctx.chemin(chemin)
        if ctx.vfs.existe(vp):
            continue
        try:
            if dossier:
                ctx.vfs.creer_dossier(vp)
                ctx.vfs.chmod(vp, 0o700)
            else:
                ctx.vfs.ecrire(vp, b"")
                ctx.vfs.chmod(vp, 0o600)
        except ErreurFs as e:
            ctx.err(f"mktemp: failed to create {'directory' if dossier else 'file'} via template "
                    f"{guillemets(chemin[:len(chemin) - len(m.group())] + m.group())}: {e.texte}\n")
            return 1
        ctx.out(chemin + "\n")
        return 0
    return 1


@outil("numfmt")
def numfmt(ctx):
    a = ctx.args[1:]
    vers = next((x.split("=", 1)[1] for x in a if x.startswith("--to=")), None)
    depuis = next((x.split("=", 1)[1] for x in a if x.startswith("--from=")), None)
    nombres = [x for x in a if not x.startswith("--")] or [l.decode() for l in lignes_de(ctx.entree.tout())]
    import math
    for n in nombres:
        try:
            if depuis:
                mt = re.fullmatch(r"([\d.]+)([KMGTPE]?)i?", n.strip())
                base = 1024 if depuis in ("iec", "iec-i") else 1000
                v = float(mt.group(1)) * base ** ("KMGTPE".index(mt.group(2)) + 1 if mt.group(2) else 0)
            else:
                v = float(n)
        except (ValueError, AttributeError):
            ctx.err(f"numfmt: invalid number: {guillemets(n)}\n")
            return 2
        if not vers:
            ctx.out(f"{int(v)}\n")
            continue
        base = 1024 if vers in ("iec", "iec-i") else 1000
        k = 0
        while abs(v) >= base and k < 6:
            v /= base
            k += 1
        if k == 0:
            ctx.out(f"{int(v)}\n")
            continue
        u = "KMGTPE"[k - 1] + ("i" if vers == "iec-i" else "")
        if vers == "si":
            u = u.replace("K", "k")
        if v < 10:
            v = math.ceil(v * 10) / 10
            ctx.out(f"{v:.1f}{u}\n" if v < 10 else f"{int(v)}{u}\n")
        else:
            ctx.out(f"{math.ceil(v)}{u}\n")
    return 0
