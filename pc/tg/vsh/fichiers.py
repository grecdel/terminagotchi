"""Le terminal du jeu : find, les empreintes (sha256sum, sha1sum, md5sum), base64, xxd, od, shuf, tar et gzip,
bc, sqlite3 (le module sqlite3 de Python, sans programme extérieur), split."""
import base64 as b64
import datetime
import gzip
import hashlib
import io
import os
import posixpath
import random
import re
import tarfile
import time

from .outils import (Options, erreur_option, guillemets, lignes_de, lire_entree_ou_fichier, option_inconnue, outil,
                     verifier_lettres)
from .vfs import ErreurFs

# ---------------------------------------------------------------- find


class _ErreurFind(Exception):
    pass


def _analyser_find(jetons):
    """L'expression de find → arbre ; renvoie (arbre, a_une_action, options globales)."""
    pos = [0]
    globales = {}
    action = [False]

    def voir():
        return jetons[pos[0]] if pos[0] < len(jetons) else None

    def prendre():
        x = voir()
        pos[0] += 1
        return x

    def ou():
        a = et()
        while voir() in ("-o", "-or"):
            prendre()
            a = ("ou", a, et())
        return a

    def et():
        a = non()
        while voir() is not None and voir() not in ("-o", "-or", ")", ","):
            if voir() in ("-a", "-and"):
                prendre()
            a = ("et", a, non())
        return a

    def non():
        if voir() in ("!", "-not"):
            prendre()
            return ("non", non())
        return primaire()

    def arg(nom):
        x = prendre()
        if x is None:
            raise _ErreurFind(f"missing argument to `{nom}'")
        return x

    def primaire():
        x = prendre()
        if x == "(":
            e = ou()
            if prendre() != ")":
                raise _ErreurFind("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            return e
        if x in ("-maxdepth", "-mindepth"):
            v = arg(x)
            if not v.isdigit():
                raise _ErreurFind(f"Expected a positive decimal integer argument to {x}, but got {guillemets(v)}")
            globales[x] = int(v)
            return ("vrai",)
        if x in ("-depth", "-xdev", "-mount", "-follow", "-noleaf", "-ignore_readdir_race"):
            globales[x] = True
            return ("vrai",)
        if x in ("-name", "-iname", "-path", "-ipath", "-wholename", "-lname", "-regex", "-iregex"):
            return (x, arg(x))
        if x == "-type":
            t = arg(x)
            if any(c not in "fdlbcps," for c in t):
                raise _ErreurFind(f"Unknown argument to -type: {t}")
            return (x, t)
        if x in ("-size", "-mtime", "-mmin", "-atime", "-amin", "-ctime", "-cmin", "-newer", "-perm", "-user",
                 "-group", "-uid", "-gid", "-links", "-inum", "-samefile"):
            return (x, arg(x))
        if x in ("-empty", "-true", "-false", "-readable", "-writable", "-executable", "-nouser", "-nogroup"):
            return (x,)
        if x in ("-print", "-print0", "-delete", "-ls", "-prune", "-quit"):
            if x != "-prune":
                action[0] = True
            if x == "-delete":
                globales["-depth"] = True
            return (x,)
        if x in ("-printf", "-fprint"):
            action[0] = True
            return (x, arg(x))
        if x in ("-exec", "-execdir", "-ok", "-okdir"):
            action[0] = True
            cmd = []
            while True:
                y = prendre()
                if y is None:
                    raise _ErreurFind(f"missing argument to `{x}'")
                if y == ";":
                    return (x, cmd, False)
                if y == "+" and cmd and cmd[-1] == "{}":
                    return (x, cmd, True)
                cmd.append(y)
        if x is None:
            raise _ErreurFind("expected an expression after '(' " if False else "invalid expression")
        if x.startswith("-"):
            raise _ErreurFind(f"unknown predicate `{x}'")
        raise _ErreurFind(f"paths must precede expression: `{x}'")

    if not jetons:
        return ("vrai",), False, globales
    e = ou()
    if pos[0] < len(jetons):
        x = jetons[pos[0]]
        if x == ")":
            raise _ErreurFind("invalid expression; you have too many ')'")
        raise _ErreurFind(f"paths must precede expression: `{x}'")
    return e, action[0], globales


def _taille_find(spec, octets):
    m = re.fullmatch(r"([+-]?)(\d+)([bckwMG]?)", spec)
    if not m:
        raise _ErreurFind(f"invalid -size argument `{spec}'")
    unite = {"": 512, "b": 512, "c": 1, "k": 1024, "w": 2, "M": 1048576, "G": 1 << 30}[m.group(3)]
    n = int(m.group(2))
    v = -(-octets // unite)
    if m.group(1) == "+":
        return v > n
    if m.group(1) == "-":
        return v < n
    return v == n


def _nombre_find(spec, valeur):
    m = re.fullmatch(r"([+-]?)(\d+)", spec)
    if not m:
        raise _ErreurFind(f"invalid argument `{spec}'")
    n = int(m.group(2))
    return valeur > n if m.group(1) == "+" else (valeur < n if m.group(1) == "-" else valeur == n)


def _perm_find(spec, mode, dossier, umask):
    from .outils import _mode_symbolique
    genre = ""
    if spec[:1] in "-/+":
        genre, spec = spec[0], spec[1:]
    if re.fullmatch(r"[0-7]+", spec):
        voulu = int(spec, 8)
    else:
        voulu = _mode_symbolique(spec, 0, dossier, 0)
        if voulu is None:
            raise _ErreurFind(f"invalid mode `{spec}'")
    if genre == "-":
        return mode & voulu == voulu
    if genre in "/+" and genre:
        return voulu == 0 or bool(mode & voulu)
    return (mode & 0o7777) == voulu


@outil("find")
def find(ctx):
    a = ctx.args[1:]
    chemins = []
    while a and (not a[0].startswith("-") or a[0] == "-") and a[0] not in ("(", "!", ")"):
        chemins.append(a.pop(0))
    chemins = chemins or ["."]
    try:
        expr, action, glob = _analyser_find(a)
    except _ErreurFind as e:
        ctx.err(f"find: {e}\n")
        return 1
    maintenant = time.time()
    code = [0]
    tas = {}             # -exec … + : les fichiers en attente
    stop = [False]
    refs = {}

    def evaluer(e, vp, nom_aff, inf, prof):
        g = e[0]
        if g == "vrai" or g == "-true":
            return True
        if g == "-false":
            return False
        if g == "et":
            return evaluer(e[1], vp, nom_aff, inf, prof) and evaluer(e[2], vp, nom_aff, inf, prof)
        if g == "ou":
            return evaluer(e[1], vp, nom_aff, inf, prof) or evaluer(e[2], vp, nom_aff, inf, prof)
        if g == "non":
            return not evaluer(e[1], vp, nom_aff, inf, prof)
        base = posixpath.basename(nom_aff.rstrip("/")) or nom_aff
        from .shell import motif_shell
        if g == "-name":
            return motif_shell(e[1], base)
        if g == "-iname":
            return motif_shell(e[1].lower(), base.lower())
        if g in ("-path", "-wholename"):
            return motif_shell(e[1], nom_aff)
        if g == "-ipath":
            return motif_shell(e[1].lower(), nom_aff.lower())
        if g == "-regex":
            return re.fullmatch(e[1], nom_aff) is not None
        if g == "-iregex":
            return re.fullmatch(e[1], nom_aff, re.I) is not None
        if g == "-type":
            return ("d" in e[1] and inf.dossier) or ("f" in e[1] and not inf.dossier)
        if g == "-size":
            return _taille_find(e[1], inf.taille)
        if g == "-empty":
            if inf.dossier:
                try:
                    return not ctx.vfs.lister(vp)
                except ErreurFs:
                    return False
            return inf.taille == 0
        if g in ("-mtime", "-atime", "-ctime"):
            return _nombre_find(e[1], int((maintenant - inf.mtime) // 86400))
        if g in ("-mmin", "-amin", "-cmin"):
            return _nombre_find(e[1], int(-(-(maintenant - inf.mtime) // 60)))
        if g == "-newer":
            if e[1] not in refs:
                try:
                    refs[e[1]] = ctx.vfs.infos(ctx.chemin(e[1])).mtime
                except ErreurFs:
                    raise _ErreurFind(f"{guillemets(e[1])}: No such file or directory")
            return inf.mtime > refs[e[1]]
        if g == "-perm":
            return _perm_find(e[1], inf.mode, inf.dossier, ctx.sh.umask)
        if g == "-user" or g == "-group":
            return (inf.proprio if g == "-user" else inf.groupe) == e[1]
        if g == "-links":
            return _nombre_find(e[1], inf.liens)
        if g in ("-readable",):
            return bool(inf.mode & 0o400)
        if g == "-writable":
            return bool(inf.mode & 0o200) and ctx.vfs.ecriture_permise(vp)
        if g == "-executable":
            return bool(inf.mode & 0o100)
        if g in ("-nouser", "-nogroup", "-uid", "-gid", "-inum", "-samefile"):
            return False
        if g == "-print":
            ctx.out(nom_aff + "\n")
            return True
        if g == "-print0":
            ctx.out(nom_aff + "\0")
            return True
        if g == "-printf":
            ctx.out(_printf_find(e[1], nom_aff, inf, chemin_depart[0]))
            return True
        if g == "-ls":
            from .outils import date_ls, droits_texte
            ctx.out(f"{inf.inode:>9} {(_blocs(inf)):>6} {droits_texte(inf.dossier, inf.mode)} {inf.liens:>3} "
                    f"{inf.proprio:<8} {inf.groupe:<8} {inf.taille:>8} {date_ls(inf.mtime)} {nom_aff}\n")
            return True
        if g == "-prune":
            elague[0] = True
            return True
        if g == "-quit":
            stop[0] = True
            return True
        if g == "-delete":
            try:
                if inf.dossier:
                    ctx.vfs.supprimer_dossier(vp)
                else:
                    ctx.vfs.supprimer_fichier(vp)
            except ErreurFs as x:
                ctx.err(f"find: cannot delete {guillemets(nom_aff)}: {x.texte}\n")
                code[0] = 1
                return False
            return True
        if g in ("-exec", "-execdir", "-ok", "-okdir"):
            cmd, plus = e[1], e[2]
            cible = nom_aff if g in ("-exec", "-ok") else "./" + base
            if plus:
                tas.setdefault(id(e), (cmd, []))[1].append(cible)
                return True
            from .shell import Entree
            args = [x.replace("{}", cible) for x in cmd]
            sauve = ctx.sh.cwd
            if g == "-execdir":
                ctx.sh.cwd = posixpath.dirname(vp)
            try:
                r = ctx.sh.lancer(args, Entree(b""), ctx.sortie, ctx.erreur)
            finally:
                ctx.sh.cwd = sauve
            return r == 0
        raise _ErreurFind(f"unknown predicate `{g}'")

    elague = [False]
    chemin_depart = [""]
    maxp = glob.get("-maxdepth")
    minp = glob.get("-mindepth", 0)
    profondeur_d = glob.get("-depth", False)

    def visiter(vp, nom_aff, prof):
        if stop[0]:
            return
        ctx.verifier()
        try:
            inf = ctx.vfs.infos(vp)
        except ErreurFs as e:
            ctx.err(f"find: {guillemets(nom_aff)}: {e.texte}\n")
            code[0] = 1
            return
        elague[0] = False

        def juger():
            if prof >= minp:
                try:
                    r = evaluer(expr, vp, nom_aff, inf, prof)
                except _ErreurFind:
                    raise
                if r and not action:
                    ctx.out(nom_aff + "\n")
        if not profondeur_d:
            juger()
        if inf.dossier and not elague[0] and (maxp is None or prof < maxp):
            try:
                noms = sorted(ctx.vfs.lister(vp), key=lambda x: x.encode("utf-8", "surrogateescape"))
            except ErreurFs as e:
                ctx.err(f"find: {guillemets(nom_aff)}: {e.texte}\n")
                code[0] = 1
                noms = []
            for x in noms:
                sv = vp.rstrip("/") + "/" + x if vp != "/" else "/" + x
                sn = nom_aff.rstrip("/") + "/" + x if nom_aff not in ("/",) else "/" + x
                if nom_aff.endswith("/") and nom_aff != "/":
                    sn = nom_aff + x
                visiter(sv, sn, prof + 1)
        if profondeur_d:
            juger()

    try:
        for c in chemins:
            vp = ctx.chemin(c)
            chemin_depart[0] = c
            if not ctx.vfs.existe(vp):
                ctx.err(f"find: {guillemets(c)}: No such file or directory\n")
                code[0] = 1
                continue
            visiter(vp, c, 0)
    except _ErreurFind as e:
        ctx.err(f"find: {e}\n")
        return 1
    from .shell import Entree
    for cmd, fichiers in tas.values():
        k = cmd.index("{}")
        r = ctx.sh.lancer(cmd[:k] + fichiers + cmd[k + 1:], Entree(b""), ctx.sortie, ctx.erreur)
        if r:
            code[0] = 1
    return code[0]


def _blocs(inf):
    from .outils import _blocs_1k
    return _blocs_1k(inf)


def _printf_find(fmt, nom, inf, depart):
    out = []
    i = 0
    while i < len(fmt):
        c = fmt[i]
        if c == "\\" and i + 1 < len(fmt):
            out.append({"n": "\n", "t": "\t", "0": "\0", "\\": "\\"}.get(fmt[i + 1], fmt[i + 1]))
            i += 2
            continue
        if c == "%" and i + 1 < len(fmt):
            m = re.match(r"%(-?\d*)([a-zA-Z%])", fmt[i:])
            if m:
                k = m.group(2)
                v = {"p": nom, "f": posixpath.basename(nom), "s": str(inf.taille), "h": posixpath.dirname(nom) or ".",
                     "m": f"{inf.mode:o}", "u": inf.proprio, "g": inf.groupe, "%": "%",
                     "P": nom[len(depart):].lstrip("/") if nom.startswith(depart) else nom,
                     "y": "d" if inf.dossier else "f", "T": "", "t": time.ctime(inf.mtime)}.get(k, "")
                if m.group(1):
                    w = int(m.group(1))
                    v = v.ljust(-w) if w < 0 else v.rjust(w)
                out.append(v)
                i += m.end()
                continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------- empreintes
def _empreinte(nom_algo):
    def cmd(ctx):
        o = Options(ctx.args[1:], longues=("check", "binary", "text", "quiet", "status", "tag", "help", "strict",
                                           "warn"))
        if o.erreur:
            return erreur_option(ctx, ctx.args[0], o)
        noms = o.reste or ["-"]
        prog = ctx.args[0]
        if o.a("c", "--check"):
            return _verifier_empreintes(ctx, prog, nom_algo, noms, o.a("--quiet"), o.a("--status"))
        code = 0
        for f in noms:
            d = lire_entree_ou_fichier(ctx, prog, f)
            if d is None:
                code = 1
                continue
            h = hashlib.new(nom_algo, d).hexdigest()
            nom = f
            pre = ""
            if "\\" in nom or "\n" in nom:
                pre = "\\"
                nom = nom.replace("\\", "\\\\").replace("\n", "\\n")
            if o.a("--tag"):
                ctx.out(f"{nom_algo.upper().replace('SHA', 'SHA')} ({nom}) = {h}\n")
            else:
                ctx.out(f"{pre}{h}  {nom}\n")
        return code
    return cmd


def _verifier_empreintes(ctx, prog, algo, noms, calme, statut):
    code = 0
    mauvais = lus = absents = mal_formes = 0
    long_h = {"sha256": 64, "sha1": 40, "md5": 32, "sha512": 128, "sha224": 56, "sha384": 96}[algo]
    for f in noms:
        d = lire_entree_ou_fichier(ctx, prog, f)
        if d is None:
            code = 1
            continue
        for l in lignes_de(d):
            t = l.decode("utf-8", "surrogateescape")
            m = re.fullmatch(r"\\?([0-9a-fA-F]{%d}) [ *](.+)" % long_h, t)
            if not m:
                mal_formes += 1
                continue
            h, nom = m.group(1).lower(), m.group(2)
            try:
                contenu = ctx.vfs.lire(ctx.chemin(nom))
            except ErreurFs as e:
                if not statut:
                    ctx.err(f"{prog}: {nom}: {e.texte}\n")
                    ctx.out(f"{nom}: FAILED open or read\n")
                absents += 1
                continue
            lus += 1
            if hashlib.new(algo, contenu).hexdigest() == h:
                if not calme and not statut:
                    ctx.out(f"{nom}: OK\n")
            else:
                mauvais += 1
                if not statut:
                    ctx.out(f"{nom}: FAILED\n")
    if not lus and not absents:
        if not statut:
            ctx.err(f"{prog}: {noms[0] if noms[0] != '-' else 'standard input'}: no properly formatted checksum lines found\n")
        return 1
    if not statut:
        if mal_formes:
            ctx.err(f"{prog}: WARNING: {mal_formes} line{'s are' if mal_formes > 1 else ' is'} improperly formatted\n")
        if absents:
            ctx.err(f"{prog}: WARNING: {absents} listed file{'s' if absents > 1 else ''} could not be read\n")
        if mauvais:
            ctx.err(f"{prog}: WARNING: {mauvais} computed checksum{'s' if mauvais > 1 else ''} did NOT match\n")
    return 1 if (mauvais or absents or code) else 0


for _n, _a in (("sha256sum", "sha256"), ("sha1sum", "sha1"), ("md5sum", "md5"), ("sha512sum", "sha512"),
               ("sha224sum", "sha224"), ("sha384sum", "sha384")):
    outil(_n)(_empreinte(_a))


# ---------------------------------------------------------------- base64
@outil("base64")
def base64(ctx):
    o = Options(ctx.args[1:], avec_valeur="w", longues=("decode", "ignore-garbage", "help"), longues_valeur=("wrap",))
    if o.erreur:
        return erreur_option(ctx, "base64", o)
    r = verifier_lettres(ctx, "base64", o, "diw")
    if r is not None:
        return r
    f = o.reste[0] if o.reste else "-"
    d = lire_entree_ou_fichier(ctx, "base64", f)
    if d is None:
        return 1
    if o.a("d", "--decode"):
        propre = re.sub(rb"\s", b"", d)
        if o.a("i", "--ignore-garbage"):
            propre = re.sub(rb"[^A-Za-z0-9+/=]", b"", propre)
        try:
            ctx.out(b64.b64decode(propre + b"=" * (-len(propre) % 4), validate=True))
        except Exception:                    # noqa: BLE001
            try:
                bon = re.match(rb"[A-Za-z0-9+/]*", propre).group()
                ctx.out(b64.b64decode(bon[:len(bon) - len(bon) % 4]))
            except Exception:                # noqa: BLE001
                pass
            ctx.err("base64: invalid input\n")
            return 1
        return 0
    largeur = int(o.val("w", "--wrap", defaut="76"))
    t = b64.b64encode(d).decode()
    if largeur:
        t = "\n".join(t[i:i + largeur] for i in range(0, len(t), largeur))
    ctx.out(t + ("\n" if t or True else ""))
    return 0


# ---------------------------------------------------------------- xxd, od
@outil("xxd")
def xxd(ctx):
    a = ctx.args[1:]
    bits = rev = plain = False
    cols = None
    longueur = None
    noms = []
    i = 0
    while i < len(a):
        x = a[i]
        if x in ("-b", "-bits"):
            bits = True
        elif x in ("-r", "-revert"):
            rev = True
        elif x in ("-p", "-ps", "-plain", "-postscript"):
            plain = True
        elif x in ("-rp", "-pr"):
            rev = plain = True
        elif x in ("-c", "-cols") and i + 1 < len(a):
            cols = int(a[i + 1], 0)
            i += 1
        elif x in ("-l", "-len") and i + 1 < len(a):
            longueur = int(a[i + 1], 0)
            i += 1
        elif x.startswith("-") and len(x) > 1:
            ctx.err(f"xxd: unknown option {x}\n" if False else "Usage:\n       xxd [options] [infile [outfile]]\n")
            return 1
        else:
            noms.append(x)
        i += 1
    d = lire_entree_ou_fichier(ctx, "xxd", noms[0] if noms else "-")
    if d is None:
        return 2
    if rev:
        if plain:
            h = re.sub(rb"[^0-9a-fA-F]", b"", d)
            sortie = bytes.fromhex(h[:len(h) - len(h) % 2].decode())
        else:
            out = bytearray()
            for l in lignes_de(d):
                m = re.match(rb"[0-9a-fA-F]+:\s*((?:[0-9a-fA-F]{2,4}\s?)+)", l)
                if m:
                    hx = re.sub(rb"\s", b"", m.group(1))
                    out += bytes.fromhex(hx.decode())
            sortie = bytes(out)
        if len(noms) > 1:
            ctx.vfs.ecrire(ctx.chemin(noms[1]), sortie)
        else:
            ctx.out(sortie)
        return 0
    if longueur is not None:
        d = d[:longueur]
    if plain:
        c = cols or 30
        h = d.hex()
        lignes = [h[k:k + 2 * c] for k in range(0, len(h), 2 * c)]
        ctx.out("".join(l + "\n" for l in lignes))
        return 0
    c = cols or (6 if bits else 16)
    out = []
    for off in range(0, len(d), c):
        bloc = d[off:off + c]
        if bits:
            groupes = " ".join(f"{b:08b}" for b in bloc)
            largeur = c * 9 - 1
        else:
            paires = [bloc[k:k + 2].hex() for k in range(0, len(bloc), 2)]
            groupes = " ".join(paires)
            largeur = (c // 2) * 5 - 1 + (c % 2) * 3
        texte = "".join(chr(b) if 32 <= b < 127 else "." for b in bloc)
        out.append(f"{off:08x}: {groupes.ljust(largeur)}  {texte}\n")
    ctx.out("".join(out))
    return 0


@outil("od")
def od(ctx):
    a = ctx.args[1:]
    adresse = "o"
    types = []
    nmax = None
    saut = 0
    noms = []
    i = 0
    while i < len(a):
        x = a[i]
        if x.startswith("-A"):
            adresse = x[2:] or a[i + 1]
            if not x[2:]:
                i += 1
        elif x.startswith("-t"):
            types.append(x[2:] or a[i + 1])
            if not x[2:]:
                i += 1
        elif x.startswith("-N"):
            nmax = int(x[2:] or a[i + 1], 0)
            if not x[2:]:
                i += 1
        elif x.startswith("-j"):
            saut = int(x[2:] or a[i + 1], 0)
            if not x[2:]:
                i += 1
        elif x == "-c":
            types.append("c")
        elif x == "-x":
            types.append("x2")
        elif x == "-b":
            types.append("o1")
        elif x == "-An":
            adresse = "n"
        else:
            noms.append(x)
        i += 1
    d = b""
    for f in noms or ["-"]:
        x = lire_entree_ou_fichier(ctx, "od", f)
        if x is None:
            return 1
        d += x
    d = d[saut:]
    if nmax is not None:
        d = d[:nmax]
    types = types or ["o2"]
    out = []
    for off in range(0, len(d), 16):
        bloc = d[off:off + 16]
        for k, t in enumerate(types):
            pre = "" if adresse == "n" else (_adr(off + saut, adresse) if k == 0 else " " * len(_adr(0, adresse)))
            out.append(pre + _od_ligne(bloc, t) + "\n")
    if adresse != "n":
        out.append(_adr(len(d) + saut, adresse) + "\n")
    ctx.out("".join(out))
    return 0


def _adr(n, base):
    return {"o": f"{n:07o}", "d": f"{n:07d}", "x": f"{n:06x}"}.get(base, f"{n:07o}")


def _od_ligne(bloc, t):
    if t.startswith("x") or t.startswith("o") or t.startswith("d") or t.startswith("u"):
        taille = int(t[1:] or 4) if t[1:].isdigit() else {"C": 1, "S": 2, "I": 4, "L": 8}.get(t[1:], 4)
        if t[0] == "o" and not t[1:]:
            taille = 2
        largeur = {("x", 1): 2, ("x", 2): 4, ("x", 4): 8, ("o", 1): 3, ("o", 2): 6, ("o", 4): 11, ("d", 1): 4,
                   ("d", 2): 6, ("d", 4): 11, ("u", 1): 3, ("u", 2): 5, ("u", 4): 10}.get((t[0], taille), 8)
        vals = []
        for k in range(0, len(bloc), taille):
            morceau = bloc[k:k + taille].ljust(taille, b"\0")
            v = int.from_bytes(morceau, "little", signed=t[0] == "d")
            f = {"x": f"{v:0{largeur}x}", "o": f"{v:0{largeur}o}", "d": f"{v:{largeur}d}", "u": f"{v:{largeur}d}"}[t[0]]
            vals.append(f)
        return "".join(" " + v for v in vals)
    if t.startswith("c") or t == "a":
        out = []
        for b in bloc:
            esc = {0: "\\0", 7: "\\a", 8: "\\b", 9: "\\t", 10: "\\n", 11: "\\v", 12: "\\f", 13: "\\r"}
            if b in esc:
                out.append(f"{esc[b]:>4}")
            elif 32 <= b < 127:
                out.append(f"{chr(b):>4}")
            else:
                out.append(f"{b:>4o}")
        return "".join(out)
    return ""


# ---------------------------------------------------------------- shuf
@outil("shuf")
def shuf(ctx):
    o = Options(ctx.args[1:], avec_valeur="niro", longues=("echo", "repeat", "help"),
                longues_valeur=("head-count", "input-range", "random-source", "output"))
    if o.erreur:
        return erreur_option(ctx, "shuf", o)
    if o.a("e", "--echo"):
        elems = [x.encode("utf-8", "surrogateescape") for x in o.reste]
    elif o.val("i", "--input-range"):
        m = re.fullmatch(r"(\d+)-(\d+)", o.val("i", "--input-range"))
        if not m:
            ctx.err(f"shuf: invalid input range: {guillemets(o.val('i'))}\n")
            return 1
        elems = [str(k).encode() for k in range(int(m.group(1)), int(m.group(2)) + 1)]
    else:
        d = lire_entree_ou_fichier(ctx, "shuf", o.reste[0] if o.reste else "-")
        if d is None:
            return 1
        elems = lignes_de(d)
    n = o.val("n", "--head-count")
    random.shuffle(elems)
    if n is not None:
        elems = elems[:int(n)]
    ctx.out(b"".join(e + b"\n" for e in elems))
    return 0


# ---------------------------------------------------------------- tar, gzip
def _dans_zone(ctx, vp):
    return ctx.vfs.ecriture_permise(vp)


@outil("tar")
def tar(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.err("tar: You must specify one of the '-Acdtrux', '--delete' or '--test-label' options\n"
                "Try 'tar --help' or 'tar --usage' for more information.\n")
        return 2
    lettres = ""
    reste = []
    fichier = None
    dossier = None
    i = 0
    if not a[0].startswith("-"):
        lettres = a[0]
        a = a[1:]
        if "f" in lettres:
            if not a:
                ctx.err("tar: option requires an argument -- 'f'\n")
                return 2
            fichier = a[0]
            a = a[1:]
    while i < len(a):
        x = a[i]
        if x == "-C" and i + 1 < len(a):
            dossier = a[i + 1]
            i += 2
            continue
        if x.startswith("--directory="):
            dossier = x.split("=", 1)[1]
        elif x.startswith("--file="):
            fichier = x.split("=", 1)[1]
        elif x.startswith("--"):
            lettres += {"--create": "c", "--extract": "x", "--list": "t", "--gzip": "z", "--verbose": "v"}.get(x, "")
        elif x.startswith("-") and len(x) > 1:
            for k, c in enumerate(x[1:]):
                lettres += c
                if c == "f":
                    v = x[k + 2:] or (a[i + 1] if i + 1 < len(a) else None)
                    if not x[k + 2:]:
                        i += 1
                    fichier = v
                    break
                if c == "C":
                    v = x[k + 2:] or (a[i + 1] if i + 1 < len(a) else None)
                    if not x[k + 2:]:
                        i += 1
                    dossier = v
                    break
        else:
            reste.append(x)
        i += 1
    mode = next((c for c in lettres if c in "cxt"), None)
    if mode is None:
        ctx.err("tar: You must specify one of the '-Acdtrux', '--delete' or '--test-label' options\n"
                "Try 'tar --help' or 'tar --usage' for more information.\n")
        return 2
    bavard = "v" in lettres
    gz = "z" in lettres
    base = ctx.sh.cwd if not dossier else ctx.chemin(dossier)
    if dossier and not ctx.vfs.est_dossier(base):
        ctx.err(f"tar: {dossier}: Cannot open: No such file or directory\ntar: Error is not recoverable: exiting now\n")
        return 2
    if mode == "c":
        if not reste:
            ctx.err("tar: Cowardly refusing to create an empty archive\nTry 'tar --help' or 'tar --usage' for more information.\n")
            return 2
        tampon = io.BytesIO()
        code = 0
        with tarfile.open(fileobj=tampon, mode="w", format=tarfile.GNU_FORMAT) as tf:
            def ajouter(nom_arch, vp):
                nonlocal code
                try:
                    inf = ctx.vfs.infos(vp)
                except ErreurFs as e:
                    ctx.err(f"tar: {nom_arch}: Cannot stat: {e.texte}\n")
                    code = 2
                    return
                ti = tarfile.TarInfo(nom_arch + ("/" if inf.dossier else ""))
                ti.mtime = int(inf.mtime)
                ti.mode = inf.mode
                ti.uname = ti.gname = inf.proprio
                if bavard:
                    ctx.out(nom_arch + ("/" if inf.dossier else "") + "\n")
                if inf.dossier:
                    ti.type = tarfile.DIRTYPE
                    tf.addfile(ti)
                    for x in sorted(ctx.vfs.lister(vp)):
                        ajouter(nom_arch.rstrip("/") + "/" + x, vp.rstrip("/") + "/" + x)
                else:
                    d = ctx.vfs.lire(vp)
                    ti.size = len(d)
                    tf.addfile(ti, io.BytesIO(d))
            for nm in reste:
                vp = posixpath.normpath(posixpath.join(base, nm)) if not nm.startswith("/") else nm
                nom_arch = nm.lstrip("/")
                if nm.startswith("/"):
                    ctx.err("tar: Removing leading `/' from member names\n")
                ajouter(nom_arch, vp)
        donnees = tampon.getvalue()
        if gz:
            donnees = gzip.compress(donnees, mtime=0)
        if fichier and fichier != "-":
            try:
                ctx.vfs.ecrire(ctx.chemin(fichier), donnees)
            except ErreurFs as e:
                ctx.err(f"tar: {fichier}: Cannot open: {e.texte}\ntar: Error is not recoverable: exiting now\n")
                return 2
        else:
            ctx.out(donnees)
        return code
    # extraire ou lister
    if fichier and fichier != "-":
        try:
            donnees = ctx.vfs.lire(ctx.chemin(fichier))
        except ErreurFs as e:
            ctx.err(f"tar: {fichier}: Cannot open: {e.texte}\ntar: Error is not recoverable: exiting now\n")
            return 2
    else:
        donnees = ctx.entree.tout()
    if donnees[:2] == b"\x1f\x8b":
        try:
            donnees = gzip.decompress(donnees)
        except OSError:
            ctx.err("gzip: stdin: not in gzip format\ntar: Child returned status 1\ntar: Error is not recoverable: exiting now\n")
            return 2
    try:
        tf = tarfile.open(fileobj=io.BytesIO(donnees), mode="r:")
    except tarfile.TarError:
        ctx.err("tar: This does not look like a tar archive\ntar: Exiting with failure status due to previous errors\n")
        return 2
    code = 0
    with tf:
        for m in tf.getmembers():
            nom = m.name
            if mode == "t":
                if bavard:
                    from .outils import droits_texte
                    d = datetime.datetime.fromtimestamp(m.mtime)
                    ctx.out(f"{droits_texte(m.isdir(), m.mode)} {m.uname or 'root'}/{m.gname or 'root'} "
                            f"{m.size:>8} {d:%Y-%m-%d %H:%M} {nom}\n")
                else:
                    ctx.out(nom + ("/" if m.isdir() and not nom.endswith("/") else "") + "\n")
                continue
            propre = posixpath.normpath(nom.lstrip("/"))
            if propre.startswith("..") or nom.startswith("/"):
                ctx.err(f"tar: {nom}: Member name contains '..'\n" if ".." in nom else
                        "tar: Removing leading `/' from member names\n")
                if ".." in propre:
                    code = 2
                    continue
            cible = posixpath.join(base, propre)
            if bavard:
                ctx.out(nom + "\n")
            try:
                if m.isdir():
                    if not ctx.vfs.existe(cible):
                        _creer_parents(ctx, cible)
                    continue
                if not m.isfile():
                    continue
                _creer_parents(ctx, posixpath.dirname(cible))
                ctx.vfs.ecrire(cible, tf.extractfile(m).read())
                try:
                    ctx.vfs.chmod(cible, m.mode & 0o777)
                    ctx.vfs.poser_date(cible, m.mtime)
                except ErreurFs:
                    pass
            except ErreurFs as e:
                ctx.err(f"tar: {nom}: Cannot open: {e.texte}\n")
                code = 2
    if code:
        ctx.err("tar: Exiting with failure status due to previous errors\n")
    return code


def _creer_parents(ctx, vp):
    parts = [x for x in vp.split("/") if x]
    cur = ""
    for p in parts:
        cur += "/" + p
        if not ctx.vfs.existe(cur):
            ctx.vfs.creer_dossier(cur)


@outil("gzip", "gunzip", "zcat")
def gzip_(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    decomp = ctx.args[0] in ("gunzip", "zcat") or "-d" in ctx.args
    vers_sortie = ctx.args[0] == "zcat" or "-c" in ctx.args
    garder = "-k" in ctx.args
    code = 0
    for f in a or ["-"]:
        d = lire_entree_ou_fichier(ctx, ctx.args[0], f)
        if d is None:
            code = 1
            continue
        try:
            r = gzip.decompress(d) if decomp else gzip.compress(d, mtime=0)
        except OSError:
            ctx.err(f"gzip: {f}: not in gzip format\n")
            code = 1
            continue
        if f == "-" or vers_sortie:
            ctx.out(r)
            continue
        cible = (f[:-3] if f.endswith(".gz") else f + ".out") if decomp else f + ".gz"
        try:
            ctx.vfs.ecrire(ctx.chemin(cible), r)
            if not garder:
                ctx.vfs.supprimer_fichier(ctx.chemin(f))
        except ErreurFs as e:
            ctx.err(f"gzip: {cible}: {e.texte}\n")
            code = 1
    return code


# ---------------------------------------------------------------- split
@outil("split")
def split(ctx):
    o = Options(ctx.args[1:], avec_valeur="lbna", longues=("help",), longues_valeur=("lines", "bytes"))
    noms = o.reste
    d = lire_entree_ou_fichier(ctx, "split", noms[0] if noms else "-")
    if d is None:
        return 1
    prefixe = noms[1] if len(noms) > 1 else "x"
    n = int(o.val("l", "--lines", defaut="1000"))
    lignes = d.splitlines(keepends=True)
    morceaux = [b"".join(lignes[k:k + n]) for k in range(0, len(lignes), n)]
    if o.val("b", "--bytes"):
        t = int(o.val("b", "--bytes").rstrip("kKmM")) * (1024 if o.val("b").endswith(("k", "K")) else 1)
        morceaux = [d[k:k + t] for k in range(0, len(d), t)]
    for k, m in enumerate(morceaux):
        suff = chr(97 + k // 26) + chr(97 + k % 26)
        ctx.vfs.ecrire(ctx.chemin(prefixe + suff), m)
    return 0


from . import calcul  # noqa: E402,F401
from . import base_sql  # noqa: E402,F401
_ = option_inconnue, os


# ---------------------------------------------------------------- dd (entre fichiers seulement)
def _taille_dd(v):
    m = re.fullmatch(r"(\d+)([cwbkKMG]?|kB|MB|GB)?", v or "")
    if not m:
        return None
    return int(m.group(1)) * {"": 1, None: 1, "c": 1, "w": 2, "b": 512, "k": 1024, "K": 1024, "M": 1 << 20,
                              "G": 1 << 30, "kB": 1000, "MB": 10 ** 6, "GB": 10 ** 9}[m.group(2)]


def _debit(n, s):
    s = max(s, 1e-6)
    for u, d in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if n / s >= d:
            return f"{n / s / d:.{0 if n / s / d >= 100 else 1}f} {u}/s"
    return f"{n / s:.0f} B/s"


@outil("dd")
def dd(ctx):
    """dd if=… of=… bs=… count=… skip=… seek=… status=none : copier des octets, entre fichiers du terrain (une
    « clé USB » du jeu est un fichier : on n'écrit JAMAIS sur un vrai disque)."""
    opts = {}
    for a in ctx.args[1:]:
        k, egal, v = a.partition("=")
        if not egal:
            ctx.err(f"dd: unrecognized operand {guillemets(a)}\nTry 'dd --help' for more information.\n")
            return 1
        opts[k] = v
    bs = _taille_dd(opts.get("bs", "512"))
    if bs is None or bs == 0:
        ctx.err(f"dd: invalid number: {guillemets(opts.get('bs'))}\n")
        return 1
    debut = time.time()
    if "if" in opts:
        d = lire_entree_ou_fichier(ctx, "dd", opts["if"])
        if d is None:
            ctx.err("")
            return 1
    else:
        d = ctx.entree.tout()
    skip = int(opts.get("skip", "0") or 0) * bs
    d = d[skip:]
    if "count" in opts:
        d = d[:int(opts["count"]) * bs]
    if "of" in opts:
        vp = ctx.chemin(opts["of"])
        if vp.startswith("/dev/") and vp not in ("/dev/null",):
            ctx.err(f"dd: failed to open {guillemets(opts['of'])}: Permission denied\n")
            return 1
        try:
            if "seek" in opts:
                ancien = ctx.vfs.lire(vp) if ctx.vfs.existe(vp) else b""
                pos = int(opts["seek"]) * bs
                d2 = ancien[:pos].ljust(pos, b"\0") + d
                d2 += ancien[len(d2):] if "notrunc" in opts.get("conv", "") else b""
                ctx.vfs.ecrire(vp, d2)
            else:
                ctx.vfs.ecrire(vp, d)
        except ErreurFs as e:
            ctx.err(f"dd: failed to open {guillemets(opts['of'])}: {e.texte}\n")
            return 1
    else:
        ctx.out(d)
    if opts.get("status") != "none":
        pleins, reste = divmod(len(d), bs)
        n = len(d)
        duree = time.time() - debut
        def h(x):
            if x < 1000:
                return None
            for u, dv in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
                if x >= dv:
                    return f"{x / dv:.1f} {u}"
        def hi(x):
            for u, dv in (("GiB", 1 << 30), ("MiB", 1 << 20), ("KiB", 1 << 10)):
                if x >= dv:
                    return f"{x / dv:.1f} {u}"
        ctx.err(f"{pleins}+{1 if reste else 0} records in\n{pleins}+{1 if reste else 0} records out\n")
        detail = f" ({h(n)}, {hi(n)})" if h(n) else ""
        ctx.err(f"{n} byte{'s' if n != 1 else ''}{detail} copied, {duree:.5f} s, {_debit(n, duree)}\n")
    return 0
