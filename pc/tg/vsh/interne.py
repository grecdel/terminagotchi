"""Le terminal du jeu : les commandes internes du shell (cd, echo, export, alias, read, test, jobs, kill…),
et le lancement des scripts (`sh f.sh`, `bash f.sh`, `./f.sh`, `source f.sh`)."""
import posixpath
import re
import time

from . import syntaxe as S
from .shell import Boucle, Entree, Interrompu, Retour, Sortie, motif_shell
from .vfs import ErreurFs

INTERNES = {}


def interne(*noms):
    def deco(f):
        for n in noms:
            INTERNES[n] = f
        return f
    return deco


def _err(ctx, msg, code=1):
    ctx.err(ctx.sh.prefixe() + f"{msg}\n")
    return code


# ---------------------------------------------------------------- dossiers
@interne("cd")
def cd(ctx):
    a = [x for x in ctx.args[1:]]
    if a and a[0] in ("-L", "-P"):
        a = a[1:]
    if a and a[0] == "--":
        a = a[1:]
    if len(a) > 1:
        return _err(ctx, "cd: too many arguments")
    cible = a[0] if a else ctx.sh.vars.get("HOME", ctx.vfs.home)
    montrer = False
    if cible == "-":
        if not ctx.sh.precedent:
            return _err(ctx, "cd: OLDPWD not set")
        cible = ctx.sh.precedent
        montrer = True
    if cible == "":
        return 0
    try:
        vp = ctx.sh.changer_dossier(cible)
    except ErreurFs as e:
        return _err(ctx, f"cd: {cible}: {e.texte}")
    if montrer:
        ctx.out(vp + "\n")
    return 0


@interne("pwd")
def pwd(ctx):
    ctx.out(ctx.sh.cwd + "\n")
    return 0


@interne("pushd")
def pushd(ctx):
    pile = ctx.sh.__dict__.setdefault("pile", [])
    ancien = ctx.sh.cwd
    if len(ctx.args) < 2:
        return _err(ctx, "pushd: no other directory")
    try:
        ctx.sh.changer_dossier(ctx.args[1])
    except ErreurFs as e:
        return _err(ctx, f"pushd: {ctx.args[1]}: {e.texte}")
    pile.insert(0, ancien)
    ctx.out(" ".join([_tilde(ctx, ctx.sh.cwd)] + [_tilde(ctx, p) for p in pile]) + "\n")
    return 0


@interne("popd")
def popd(ctx):
    pile = ctx.sh.__dict__.setdefault("pile", [])
    if not pile:
        return _err(ctx, "popd: directory stack empty")
    p = pile.pop(0)
    try:
        ctx.sh.changer_dossier(p)
    except ErreurFs as e:
        return _err(ctx, f"popd: {p}: {e.texte}")
    ctx.out(" ".join([_tilde(ctx, ctx.sh.cwd)] + [_tilde(ctx, x) for x in pile]) + "\n")
    return 0


def _tilde(ctx, p):
    h = ctx.vfs.home
    return "~" + p[len(h):] if p == h or p.startswith(h + "/") else p


# ---------------------------------------------------------------- écrire
def _octet(v):
    """Un octet écrit par \\303 ou \\xc3 : gardé tel quel (é = \\303\\251), comme bash."""
    v &= 0xff
    return chr(v) if v < 0x80 else chr(0xDC00 + v)


def _echappements(s, c_arret=True):
    """Les \\n, \\t… d'echo -e et de printf %b. Renvoie (texte, arrêt demandé par \\c)."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c != "\\" or i + 1 >= len(s):
            out.append(c)
            i += 1
            continue
        d = s[i + 1]
        if d == "c" and c_arret:
            return "".join(out), True
        if d in "abefnrtv\\":
            out.append({"a": "\a", "b": "\b", "e": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v",
                        "\\": "\\"}[d])
            i += 2
            continue
        if d == "0":
            m = re.match(r"[0-7]{0,3}", s[i + 2:])
            out.append(_octet(int(m.group() or "0", 8)))
            i += 2 + m.end()
            continue
        if d == "x":
            m = re.match(r"[0-9a-fA-F]{1,2}", s[i + 2:])
            if m:
                out.append(_octet(int(m.group(), 16)))
                i += 2 + m.end()
                continue
        if d in "uU":
            m = re.match(r"[0-9a-fA-F]{1,%d}" % (4 if d == "u" else 8), s[i + 2:])
            if m:
                out.append(chr(int(m.group(), 16)))
                i += 2 + m.end()
                continue
        out.append(c)
        i += 1
    return "".join(out), False


@interne("echo")
def echo(ctx):
    a = ctx.args[1:]
    nl, esc = True, False
    while a and re.fullmatch(r"-[neE]+", a[0]):
        for f in a[0][1:]:
            if f == "n":
                nl = False
            elif f == "e":
                esc = True
            else:
                esc = False
        a = a[1:]
    texte = " ".join(a)
    if esc:
        texte, arret = _echappements(texte)
        if arret:
            ctx.out(texte)
            return 0
    ctx.out(texte + ("\n" if nl else ""))
    return 0


@interne("printf")
def printf(ctx):
    a = ctx.args[1:]
    if a and a[0] == "--":
        a = a[1:]
    if not a:
        return _err(ctx, "printf: usage: printf [-v var] format [arguments]", 2)
    var = None
    if a[0] == "-v" and len(a) > 2:
        var, a = a[1], a[2:]
    fmt, args = a[0], a[1:]
    out, code = formater(fmt, args, ctx)
    if var:
        ctx.sh.vars[var] = out
    else:
        ctx.out(out)
    return code


def formater(fmt, args, ctx=None):
    """printf : le format est répété tant qu'il reste des arguments."""
    out = []
    code = 0
    k = 0
    premier = True
    while premier or k < len(args):
        premier = False
        avant = k
        i = 0
        while i < len(fmt):
            c = fmt[i]
            if c == "\\":
                m = re.match(r"\\(0?[0-7]{1,3})", fmt[i:])
                if m:
                    out.append(_octet(int(m.group(1)[-3:] if m.group(1).startswith("0") and len(m.group(1)) == 4
                                          else m.group(1), 8)))
                    i += m.end()
                    continue
                if fmt[i + 1:i + 2] == "x":
                    m = re.match(r"\\x[0-9a-fA-F]{1,2}", fmt[i:])
                    if m:
                        out.append(_octet(int(m.group()[2:], 16)))
                        i += m.end()
                        continue
                t, _ = _echappements(fmt[i:i + 2], c_arret=False)
                out.append(t)
                i += 2
                continue
            if c != "%":
                out.append(c)
                i += 1
                continue
            if fmt[i + 1:i + 2] == "%":
                out.append("%")
                i += 2
                continue
            m = re.match(r"%([-+ #0]*)(\*|\d+)?(?:\.(\*|\d+))?([diouxXeEfFgGcsbq])", fmt[i:])
            if not m:
                out.append(c)
                i += 1
                continue
            drap, larg, prec, conv = m.groups()
            if larg == "*":
                larg = args[k] if k < len(args) else "0"
                k += 1
            if prec == "*":
                prec = args[k] if k < len(args) else "0"
                k += 1
            arg = args[k] if k < len(args) else None
            k += 1
            spec = "%" + drap + (larg or "") + ("." + prec if prec is not None else "")
            if conv in "diouxX":
                v, ok = _entier(arg)
                if not ok and ctx is not None:
                    ctx.err(f"{ctx.sh.nom}: printf: {arg}: invalid number\n")
                    code = 1
                if conv == "u" and v < 0:
                    v += 1 << 64
                out.append((spec + ("d" if conv in "iu" else conv)) % v)
            elif conv in "eEfFgG":
                try:
                    v = float(arg) if arg not in (None, "") else 0.0
                except ValueError:
                    v = 0.0
                    if ctx is not None:
                        ctx.err(f"{ctx.sh.nom}: printf: {arg}: invalid number\n")
                    code = 1
                out.append((spec + conv) % v)
            elif conv == "c":
                out.append((spec + "s") % ((arg or "")[:1]))
            elif conv == "b":
                t, arret = _echappements(arg or "")
                out.append((spec + "s") % t)
                if arret:
                    return "".join(out), code
            elif conv == "q":
                out.append((spec + "s") % _citer(arg or ""))
            else:
                out.append((spec + "s") % (arg if arg is not None else ""))
            i += m.end()
        if k == avant or k >= len(args):
            break
    return "".join(out), code


def _citer(s):
    if s == "":
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_./=:,+@%-]+", s):
        return s
    return re.sub(r"([^A-Za-z0-9_./=:,+@%-])", r"\\\1", s)


def _entier(a):
    if a is None or a == "":
        return 0, True
    a = a.strip()
    if a[:1] in "'\"" and len(a) >= 2:
        return ord(a[1]), True
    try:
        if re.fullmatch(r"[-+]?0[xX][0-9a-fA-F]+", a):
            return int(a, 16), True
        if re.fullmatch(r"[-+]?0[0-7]+", a):
            return int(a, 8), True
        return int(a), True
    except ValueError:
        m = re.match(r"[-+]?\d+", a)
        return (int(m.group()) if m else 0), False


# ---------------------------------------------------------------- variables
@interne("export")
def export(ctx):
    a = ctx.args[1:]
    if not a or a == ["-p"]:
        for k in sorted(ctx.sh.exportees):
            if k in ctx.sh.vars:
                ctx.out(f'declare -x {k}="{ctx.sh.vars[k]}"\n')
        return 0
    for x in a:
        if x == "-n":
            continue
        nom, egal, val = x.partition("=")
        if not re.fullmatch(r"[A-Za-z_]\w*", nom):
            _err(ctx, f"export: `{x}': not a valid identifier")
            continue
        if egal:
            ctx.sh.vars[nom] = val
        ctx.sh.exportees.add(nom)
    return 0


@interne("readonly", "declare", "typeset")
def declare(ctx):
    for x in ctx.args[1:]:
        if x.startswith("-"):
            continue
        nom, egal, val = x.partition("=")
        if egal:
            ctx.sh.vars[nom] = val
        elif nom not in ctx.sh.vars:
            ctx.sh.vars[nom] = ""
    return 0


@interne("local")
def local(ctx):
    if not ctx.sh.locales:
        return _err(ctx, "local: can only be used in a function")
    for x in ctx.args[1:]:
        nom, egal, val = x.partition("=")
        if nom not in ctx.sh.locales[-1]:
            ctx.sh.locales[-1][nom] = ctx.sh.vars.get(nom)
        ctx.sh.vars[nom] = val if egal else ctx.sh.vars.get(nom, "")
    return 0


@interne("unset")
def unset(ctx):
    a = ctx.args[1:]
    fonctions = False
    if a and a[0] in ("-v", "-f"):
        fonctions = a[0] == "-f"
        a = a[1:]
    for x in a:
        if fonctions:
            ctx.sh.fonctions.pop(x, None)
        else:
            if x in ctx.sh.vars:
                ctx.sh.vars.pop(x, None)
            else:
                ctx.sh.fonctions.pop(x, None)
            ctx.sh.exportees.discard(x)
    return 0


@interne("set")
def set_(ctx):
    a = ctx.args[1:]
    if not a:
        for k in sorted(ctx.sh.vars):
            ctx.out(f"{k}={_citer_set(ctx.sh.vars[k])}\n")
        return 0
    while a and a[0][:1] in "-+" and a[0] != "--" and len(a[0]) > 1:
        on = a[0][0] == "-"
        lettres = a[0][1:]
        a = a[1:]
        for f in lettres:
            if f == "o":
                if not a:
                    for k in ("errexit", "nounset", "pipefail", "xtrace"):
                        ctx.out(f"{k:<15}\t{'on' if ctx.sh.options[{'errexit': 'e', 'nounset': 'u', 'xtrace': 'x'}.get(k, k)] else 'off'}\n")
                    return 0
                nom = {"errexit": "e", "xtrace": "x", "nounset": "u", "pipefail": "pipefail"}.get(a[0])
                if nom:
                    ctx.sh.options[nom] = on
                a = a[1:]
            elif f in ctx.sh.options:
                ctx.sh.options[f] = on
    if a and a[0] == "--":
        a = a[1:]
        ctx.sh.args = list(a)
    elif a:
        ctx.sh.args = list(a)
    return 0


def _citer_set(v):
    if re.fullmatch(r"[A-Za-z0-9_./:,+@%=-]*", v):
        return v
    return "'" + v.replace("'", "'\\''") + "'"


@interne("shift")
def shift(ctx):
    n = int(ctx.args[1]) if len(ctx.args) > 1 and ctx.args[1].isdigit() else 1
    if n > len(ctx.sh.args):
        return 1
    ctx.sh.args = ctx.sh.args[n:]
    return 0


@interne("read")
def read(ctx):
    a = ctx.args[1:]
    brut = False
    invite = None
    while a and a[0].startswith("-") and len(a[0]) > 1:
        if a[0] == "-r":
            brut = True
            a = a[1:]
        elif a[0] == "-p" and len(a) > 1:
            invite = a[1]
            a = a[2:]
        elif a[0] in ("-s", "-e"):
            a = a[1:]
        else:
            a = a[1:]
    noms = a or ["REPLY"]
    if invite is not None and ctx.entree.tty:
        ctx.err(invite)
    try:
        ligne = ctx.entree.ligne()
    except (KeyboardInterrupt, Interrompu):
        raise
    if not ligne:
        for n in noms:
            ctx.sh.vars[n] = ""
        return 1
    texte = ligne.decode("utf-8", "replace")
    fin = texte.endswith("\n")
    texte = texte.rstrip("\n")
    if not brut:
        texte = re.sub(r"\\(.)", r"\1", texte)
    ifs = ctx.sh.vars.get("IFS", " \t\n")
    if len(noms) == 1:
        ctx.sh.vars[noms[0]] = texte.strip(ifs) if noms[0] != "REPLY" else texte
        return 0
    morceaux = texte.strip(ifs).split(None, len(noms) - 1) if ifs == " \t\n" else texte.split(ifs[0], len(noms) - 1)
    for i, n in enumerate(noms):
        ctx.sh.vars[n] = morceaux[i] if i < len(morceaux) else ""
    return 0 if fin else 1


# ---------------------------------------------------------------- alias
@interne("alias")
def alias(ctx):
    a = ctx.args[1:]
    if not a or a == ["-p"]:
        for k in sorted(ctx.sh.alias):
            ctx.out(f"alias {k}='{ctx.sh.alias[k]}'\n".replace("'", "'") if "'" not in ctx.sh.alias[k] else
                    f"alias {k}='" + ctx.sh.alias[k].replace("'", "'\\''") + "'\n")
        return 0
    code = 0
    for x in a:
        nom, egal, val = x.partition("=")
        if egal:
            ctx.sh.alias[nom] = val
        elif nom in ctx.sh.alias:
            v = ctx.sh.alias[nom]
            ctx.out(f"alias {nom}='" + v.replace("'", "'\\''") + "'\n")
        else:
            code = _err(ctx, f"alias: {nom}: not found")
    return code


@interne("unalias")
def unalias(ctx):
    a = ctx.args[1:]
    if a == ["-a"]:
        ctx.sh.alias.clear()
        return 0
    code = 0
    for x in a:
        if x in ctx.sh.alias:
            del ctx.sh.alias[x]
        else:
            code = _err(ctx, f"unalias: {x}: not found")
    return code


# ---------------------------------------------------------------- contrôle
@interne("true", ":")
def vrai(ctx):
    return 0


@interne("false")
def faux(ctx):
    return 1


@interne("exit")
def exit_(ctx):
    a = ctx.args[1:]
    code = ctx.sh.statut
    if a:
        try:
            code = int(a[0]) & 255
        except ValueError:
            _err(ctx, f"exit: {a[0]}: numeric argument required")
            code = 2
    raise Sortie(code)


@interne("logout")
def logout(ctx):
    raise Sortie(0)


@interne("return")
def return_(ctx):
    a = ctx.args[1:]
    code = ctx.sh.statut
    if a:
        try:
            code = int(a[0]) & 255
        except ValueError:
            _err(ctx, f"return: {a[0]}: numeric argument required")
            code = 2
    raise Retour(code)


@interne("break", "continue")
def boucle(ctx):
    n = 1
    if len(ctx.args) > 1:
        try:
            n = max(1, int(ctx.args[1]))
        except ValueError:
            pass
    raise Boucle(ctx.args[0], n)


@interne("eval")
def eval_(ctx):
    texte = " ".join(ctx.args[1:])
    if not texte.strip():
        return 0
    try:
        arbre = S.analyser(texte)
    except (S.Incomplet, S.ErreurSyntaxe) as e:
        return _err(ctx, f"eval: {e}" if str(e) else "eval: syntax error", 2)
    return ctx.sh.liste(arbre, ctx.entree, ctx.sortie, ctx.erreur)


@interne("source", ".")
def source(ctx):
    if len(ctx.args) < 2:
        return _err(ctx, f"{ctx.args[0]}: filename argument required", 2)
    f = ctx.args[1]
    vp = ctx.chemin(f)
    try:
        texte = ctx.vfs.lire(vp).decode("utf-8", "replace")
    except ErreurFs as e:
        return _err(ctx, f"{f}: {e.texte}")
    sauve = ctx.sh.args
    if len(ctx.args) > 2:
        ctx.sh.args = ctx.args[2:]
    try:
        arbre = S.analyser(texte)
    except (S.Incomplet, S.ErreurSyntaxe) as e:
        ctx.sh.args = sauve
        return _err(ctx, f"{f}: {e or 'syntax error: unexpected end of file'}", 2)
    try:
        return ctx.sh.liste(arbre, ctx.entree, ctx.sortie, ctx.erreur)
    except Retour as r:
        return r.code
    finally:
        ctx.sh.args = sauve


@interne("exec")
def exec_(ctx):
    if len(ctx.args) == 1:
        return 0
    code = ctx.sh.lancer(ctx.args[1:], ctx.entree, ctx.sortie, ctx.erreur)
    raise Sortie(code)


# ---------------------------------------------------------------- test / [
@interne("test", "[")
def test(ctx):
    a = ctx.args[1:]
    if ctx.args[0] == "[":
        if not a or a[-1] != "]":
            return _err(ctx, "[: missing `]'", 2)
        a = a[:-1]
    try:
        return 0 if _test(ctx, a) else 1
    except _ErreurTest as e:
        ctx.err(ctx.sh.prefixe() + f"{ctx.args[0]}: {e}\n")
        return 2


class _ErreurTest(Exception):
    pass


def _test(ctx, a):
    if not a:
        return False
    if a[0] == "!" and len(a) > 1:
        return not _test(ctx, a[1:])
    if "-o" in a[1:-1]:
        i = a.index("-o", 1)
        return _test(ctx, a[:i]) or _test(ctx, a[i + 1:])
    if "-a" in a[1:-1]:
        i = a.index("-a", 1)
        return _test(ctx, a[:i]) and _test(ctx, a[i + 1:])
    if a[0] == "(" and a[-1] == ")":
        return _test(ctx, a[1:-1])
    if len(a) == 1:
        return a[0] != ""
    if len(a) == 2:
        op, x = a
        if op == "-n":
            return x != ""
        if op == "-z":
            return x == ""
        vp = ctx.chemin(x) if x else ""
        if op == "-e" or op == "-a":
            return bool(x) and ctx.vfs.existe(vp)
        if op == "-f":
            return bool(x) and ctx.vfs.est_fichier(vp)
        if op == "-d":
            return bool(x) and ctx.vfs.est_dossier(vp)
        if op in ("-r", "-w", "-x", "-s", "-L", "-h", "-p", "-S", "-b", "-c", "-g", "-u", "-k", "-O", "-G", "-N"):
            if not x or not ctx.vfs.existe(vp):
                return False
            inf = ctx.vfs.infos(vp)
            if op == "-r":
                return bool(inf.mode & 0o444)
            if op == "-w":
                return bool(inf.mode & 0o200) and ctx.vfs.ecriture_permise(vp)
            if op == "-x":
                return bool(inf.mode & 0o111)
            if op == "-s":
                return inf.taille > 0 and not inf.dossier or (inf.dossier and inf.taille > 0)
            return False
        if op == "-t":
            return False
        raise _ErreurTest(f"{op}: unary operator expected")
    if len(a) == 3:
        x, op, y = a
        if op in ("=", "=="):
            return x == y
        if op == "!=":
            return x != y
        if op == "<":
            return x < y
        if op == ">":
            return x > y
        if op in ("-eq", "-ne", "-lt", "-le", "-gt", "-ge"):
            try:
                xi, yi = int(x.strip()), int(y.strip())
            except ValueError:
                mauvais = x if not re.fullmatch(r"\s*[-+]?\d+\s*", x) else y
                raise _ErreurTest(f"{mauvais}: integer expression expected")
            return {"-eq": xi == yi, "-ne": xi != yi, "-lt": xi < yi, "-le": xi <= yi, "-gt": xi > yi,
                    "-ge": xi >= yi}[op]
        if op in ("-nt", "-ot", "-ef"):
            try:
                ix, iy = ctx.vfs.infos(ctx.chemin(x)), ctx.vfs.infos(ctx.chemin(y))
            except ErreurFs:
                return False
            return {"-nt": ix.mtime > iy.mtime, "-ot": ix.mtime < iy.mtime, "-ef": ix.inode == iy.inode}[op]
        raise _ErreurTest(f"{op}: binary operator expected")
    raise _ErreurTest("too many arguments")


# ---------------------------------------------------------------- tâches
@interne("jobs")
def jobs(ctx):
    sh = ctx.sh
    a = ctx.args[1:]
    seul_pid = "-p" in a
    avec_pid = "-l" in a
    for t in sh.taches:
        if seul_pid:
            ctx.out(f"{t.pid}\n")
            continue
        if t.code is None:
            etat = "Running"
        elif t.signal:
            etat = t.signal
        else:
            etat = "Done" if t.code in (0,) else f"Exit {t.code}"
        pid = f" {t.pid}" if avec_pid else ""
        texte = t.texte if t.code is None else t.texte.rstrip(" &")
        ctx.out(f"[{t.n}]{sh._marque(t)}{pid}  {etat:<24}{texte}\n")
        if t.code is not None:
            t.annoncee = True
    sh.taches = [t for t in sh.taches if t.code is None or not t.annoncee]
    return 0


SIGNAUX = {"HUP": 1, "INT": 2, "QUIT": 3, "KILL": 9, "TERM": 15, "STOP": 19, "CONT": 18, "USR1": 10, "USR2": 12}
NOMS_SIGNAUX = {1: "Hangup", 2: "Interrupt", 3: "Quit", 9: "Killed", 15: "Terminated", 10: "User defined signal 1",
                12: "User defined signal 2"}


@interne("kill")
def kill(ctx):
    a = ctx.args[1:]
    sig = 15
    if a and a[0] == "-l":
        ctx.out(" 1) SIGHUP\t 2) SIGINT\t 3) SIGQUIT\t 9) SIGKILL\t15) SIGTERM\n")
        return 0
    if a and a[0].startswith("-") and len(a[0]) > 1:
        s = a[0][1:]
        if s == "s" and len(a) > 1:
            s = a[1]
            a = a[1:]
        s = s.upper().removeprefix("SIG")
        sig = int(s) if s.isdigit() else SIGNAUX.get(s)
        if sig is None:
            return _err(ctx, f"kill: {a[0][1:]}: invalid signal specification")
        a = a[1:]
    if not a:
        return _err(ctx, "kill: usage: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ... or kill -l [sigspec]", 2)
    code = 0
    for x in a:
        t = ctx.sh.tache(x)
        if t is None and x.startswith("%"):
            code = _err(ctx, f"kill: {x}: no such job")
            continue
        if t is None and re.fullmatch(r"\d+", x):
            from .shell import TACHES_PAR_PID
            autre = TACHES_PAR_PID.get(int(x))
            if autre is not None and autre.code is None and autre.sh.vfs is ctx.sh.vfs:
                t = autre                         # (une tâche lancée dans un sous-shell : `( … & echo $! > pid )`)
        if t is None:
            if not re.fullmatch(r"-?\d+", x):
                code = _err(ctx, f"kill: {x}: arguments must be process or job IDs")
                continue
            from .processus import tuer
            if sig not in (0, 18, 19) and tuer(int(x)):     # un processus simulé du jeu (Citadelle, Contrôle)
                continue
            code = _err(ctx, f"kill: ({x}) - No such process")
            continue
        if t.code is not None:
            code = _err(ctx, f"kill: {'(' + str(t.pid) + ') - No such process' if not x.startswith('%') else x + ': no such job'}")
            continue
        if sig in (18, 19, 0):
            continue
        t.signal = NOMS_SIGNAUX.get(sig, f"Signal {sig}")
        t.arret.set()
        t.fil.join(0.5)
        if t.code is None:
            t.code = 128 + sig
    return code


@interne("wait")
def wait(ctx):
    code = 0
    cibles = [ctx.sh.tache(x) for x in ctx.args[1:]] if len(ctx.args) > 1 else list(ctx.sh.taches)
    for t in cibles:
        if t is None:
            code = 127
            continue
        while t.fil.is_alive():
            ctx.verifier()
            t.fil.join(0.05)
        code = t.code or 0
        if len(ctx.args) == 1:
            t.annoncee = True
    if len(ctx.args) == 1:
        ctx.sh.taches = [t for t in ctx.sh.taches if not t.annoncee]
    return code


@interne("fg")
def fg(ctx):
    spec = ctx.args[1] if len(ctx.args) > 1 else "%+"
    t = ctx.sh.tache(spec)
    if t is None or t.code is not None:
        return _err(ctx, f"fg: {spec if len(ctx.args) > 1 else 'current'}: no such job")
    ctx.out(t.texte.rstrip(" &") + "\n")
    try:
        while t.fil.is_alive():
            ctx.verifier()
            t.fil.join(0.05)
    except (KeyboardInterrupt, Interrompu):
        t.signal = None
        t.arret.set()
        t.fil.join(0.5)
        t.annoncee = True
        ctx.sh.taches = [x for x in ctx.sh.taches if x is not t]
        raise
    t.annoncee = True
    ctx.sh.taches = [x for x in ctx.sh.taches if x is not t]
    return t.code or 0


@interne("bg")
def bg(ctx):
    spec = ctx.args[1] if len(ctx.args) > 1 else "%+"
    t = ctx.sh.tache(spec)
    if t is None:
        return _err(ctx, f"bg: {spec if len(ctx.args) > 1 else 'current'}: no such job")
    ctx.out(f"[{t.n}]{ctx.sh._marque(t)} {t.texte}\n")
    return 0


# ---------------------------------------------------------------- savoir ce qu'est une commande
def _quoi(ctx, nom):
    from . import outils
    sh = ctx.sh
    if nom in sh.alias:
        return "alias", sh.alias[nom]
    if nom in S.RESERVES:
        return "mot", None
    if nom in sh.fonctions:
        return "fonction", None
    if nom in INTERNES and nom not in ("[", "test", "echo", "printf", "pwd", "kill", "true", "false") or nom in (
            "cd", "export", "alias"):
        return "interne", None
    if nom in ("echo", "printf", "pwd", "kill", "true", "false", "test", "["):
        return "interne", None
    if outils.est_du_jeu(nom) and sh.sur_jeu:
        return "jeu", None
    if nom in outils.TOUS:
        return "fichier", "/usr/bin/" + nom
    return None, None


@interne("type")
def type_(ctx):
    code = 0
    for nom in [x for x in ctx.args[1:] if not x.startswith("-")]:
        q, v = _quoi(ctx, nom)
        if q == "alias":
            ctx.out(f"{nom} is aliased to `{v}'\n")
        elif q == "mot":
            ctx.out(f"{nom} is a shell keyword\n")
        elif q == "fonction":
            ctx.out(f"{nom} is a function\n")
        elif q == "interne":
            ctx.out(f"{nom} is a shell builtin\n")
        elif q == "jeu":
            ctx.out(f"{nom} is aliased to `tg {nom}'\n" if nom != "tg" else "tg is a command of the game\n")
        elif q == "fichier":
            ctx.out(f"{nom} is {v}\n")
        else:
            code = _err(ctx, f"type: {nom}: not found")
    return code


@interne("command")
def command(ctx):
    a = ctx.args[1:]
    if a and a[0] in ("-v", "-V"):
        code = 0
        for nom in a[1:]:
            q, v = _quoi(ctx, nom)
            if q is None or (q == "alias" and False):
                code = 1
                if a[0] == "-V":
                    _err(ctx, f"command: {nom}: not found")
                continue
            if a[0] == "-V":
                type_(type("C", (), {"args": ["type", nom], "sh": ctx.sh, "out": ctx.out, "err": ctx.err})())
            elif q == "alias":
                ctx.out(f"alias {nom}='{v}'\n")
            elif q == "fichier":
                ctx.out(v + "\n")
            else:
                ctx.out(nom + "\n")
        return code
    if not a:
        return 0
    sauve = ctx.sh.fonctions
    ctx.sh.fonctions = {}
    try:
        return ctx.sh.lancer(a, ctx.entree, ctx.sortie, ctx.erreur)
    finally:
        ctx.sh.fonctions = sauve


@interne("builtin")
def builtin(ctx):
    a = ctx.args[1:]
    if not a:
        return 0
    if a[0] not in INTERNES:
        return _err(ctx, f"builtin: {a[0]}: not a shell builtin")
    return INTERNES[a[0]](type(ctx)(ctx.sh, a, ctx.entree, ctx.sortie, ctx.erreur))


@interne("shopt", "hash", "set+o")
def hash_(ctx):
    return 0


@interne("umask")
def umask(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.out(f"{ctx.sh.umask:04o}\n")
        return 0
    if a[0] == "-S":
        m = ~ctx.sh.umask & 0o777
        ctx.out("u=" + _rwx(m >> 6) + ",g=" + _rwx(m >> 3) + ",o=" + _rwx(m) + "\n")
        return 0
    try:
        ctx.sh.umask = int(a[0], 8) & 0o777
    except ValueError:
        return _err(ctx, f"umask: {a[0]}: octal number out of range")
    return 0


def _rwx(m):
    return ("r" if m & 4 else "") + ("w" if m & 2 else "") + ("x" if m & 1 else "")


@interne("history")
def history(ctx):
    h = ctx.sh.historique
    a = ctx.args[1:]
    if a and a[0] == "-c":
        h.clear()
        return 0
    if a and a[0] in ("-a", "-w", "-r", "-n"):
        return 0
    n = len(h)
    debut = 0
    if a and a[0].isdigit():
        debut = max(0, n - int(a[0]))
    for i in range(debut, n):
        ctx.out(f"{i + 1:5d}  {h[i]}\n")
    return 0


@interne("trap")
def trap(ctx):
    a = ctx.args[1:]
    if not a or a == ["-p"]:
        for sig, cmd in ctx.sh.pieges.items():
            ctx.out(f"trap -- '{cmd}' {sig}\n")
        return 0
    if a[0] == "-l":
        ctx.out(" 1) SIGHUP\t 2) SIGINT\t 3) SIGQUIT\t 9) SIGKILL\t15) SIGTERM\n")
        return 0
    cmd, sigs = a[0], a[1:]
    if not sigs:
        sigs, cmd = [cmd], "-"
    for s in sigs:
        s = s.upper().removeprefix("SIG")
        s = {"0": "EXIT", "2": "INT", "15": "TERM", "1": "HUP"}.get(s, s)
        if cmd == "-":
            ctx.sh.pieges.pop(s, None)
        else:
            ctx.sh.pieges[s] = cmd
    return 0


def lancer_piege(sh, nom, entree, sortie, erreur):
    cmd = sh.pieges.pop(nom, None) if hasattr(sh, "pieges") else None
    if cmd:
        try:
            sh.liste(S.analyser(cmd), entree, sortie, erreur)
        except (Sortie, Retour, S.Incomplet, S.ErreurSyntaxe):
            pass


AIDE_INTERNES = {
    "getopts": "getopts: getopts optstring name [arg ...]", "cd": "cd: cd [-L|[-P [-e]] [-@]] [dir]",
    "echo": "echo: echo [-neE] [arg ...]", "export": "export: export [-fn] [name[=value] ...] or export -p",
    "alias": "alias: alias [-p] [name[=value] ... ]", "read": "read: read [-ers] [-a array] [-d delim] [-i text] [-n nchars] [-N nchars] [-p prompt] [-t timeout] [-u fd] [name ...]",
    "test": "test: test [expr]", "jobs": "jobs: jobs [-lnprs] [jobspec ...] or jobs -x command [args]",
    "kill": "kill: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ... or kill -l [sigspec]",
    "pwd": "pwd: pwd [-LP]", "exit": "exit: exit [n]", "source": "source: source filename [arguments]",
    "set": "set: set [-abefhkmnptuvxBCEHPT] [-o option-name] [--] [-] [arg ...]", "trap": "trap: trap [-lp] [[arg] signal_spec ...]",
    "type": "type: type [-afptP] name [name ...]", "umask": "umask: umask [-p] [-S] [mode]",
    "printf": "printf: printf [-v var] format [arguments]", "history": "history: history [-c] [-d offset] [n] or history -anrw [filename] or history -ps arg [arg...]",
    "wait": "wait: wait [-fn] [-p var] [id ...]", "fg": "fg: fg [job_spec]", "bg": "bg: bg [job_spec ...]",
    "unset": "unset: unset [-f] [-v] [-n] [name ...]", "local": "local: local [option] name[=value] ...",
    "return": "return: return [n]", "shift": "shift: shift [n]", "eval": "eval: eval [arg ...]",
    "time": "time: time [-p] pipeline", "help": "help: help [-dms] [pattern ...]",
}


@interne("help")
def help_(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-")]
    if not a:
        ctx.out("Le terminal du jeu Terminagotchi (un petit shell POSIX écrit en Python).\n"
                "Ces commandes sont internes au shell. Tape `help nom` pour en savoir plus.\n\n")
        for k in sorted(AIDE_INTERNES):
            ctx.out(f" {AIDE_INTERNES[k]}\n")
        return 0
    code = 0
    for x in a:
        if x in AIDE_INTERNES:
            ctx.out(AIDE_INTERNES[x] + "\n")
        else:
            code = _err(ctx, f"help: no help topics match `{x}'.  Try `help help' or `man -k {x}' or `info {x}'.")
    return code


@interne("times")
def times(ctx):
    ctx.out("0m0.000s 0m0.000s\n0m0.000s 0m0.000s\n")
    return 0


@interne("let")
def let(ctx):
    v = 0
    for x in ctx.args[1:]:
        try:
            v = ctx.sh.arith(x)
        except Exception as e:                  # noqa: BLE001
            return _err(ctx, f"let: {e}")
    return 0 if v else 1


@interne("getopts")
def getopts(ctx):
    a = ctx.args[1:]
    if len(a) < 2:
        return _err(ctx, "getopts: usage: getopts optstring name [arg ...]", 2)
    optstring, nom = a[0], a[1]
    args = a[2:] if len(a) > 2 else ctx.sh.args
    sh = ctx.sh
    ind = int(sh.vars.get("OPTIND", "1") or 1)
    pos = int(sh.vars.get("_OPTPOS", "1") or 1)
    if ind > len(args) or not args[ind - 1].startswith("-") or args[ind - 1] == "-":
        sh.vars[nom] = "?"
        return 1
    if args[ind - 1] == "--":
        sh.vars["OPTIND"] = str(ind + 1)
        sh.vars[nom] = "?"
        return 1
    arg = args[ind - 1]
    c = arg[pos]
    pos += 1
    if pos >= len(arg):
        ind, pos = ind + 1, 1
    k = optstring.find(c)
    if k < 0:
        sh.vars[nom] = "?"
        if not optstring.startswith(":"):
            ctx.err(f"{sh.nom}: illegal option -- {c}\n")
    else:
        sh.vars[nom] = c
        if optstring[k + 1:k + 2] == ":":
            if pos > 1:
                sh.vars["OPTARG"] = arg[pos:]
                ind, pos = ind + 1, 1
            elif ind <= len(args):
                sh.vars["OPTARG"] = args[ind - 1]
                ind += 1
            else:
                sh.vars[nom] = "?"
                ctx.err(f"{sh.nom}: option requires an argument -- {c}\n")
    sh.vars["OPTIND"] = str(ind)
    sh.vars["_OPTPOS"] = str(pos)
    return 0


@interne("time")
def time_(ctx):
    a = ctx.args[1:]
    if a and a[0] == "-p":
        a = a[1:]
    t0 = time.perf_counter()
    c0 = time.process_time()
    code = ctx.sh.lancer(a, ctx.entree, ctx.sortie, ctx.erreur) if a else 0
    dt = time.perf_counter() - t0
    dc = time.process_time() - c0
    ctx.err(f"\nreal\t{_mins(dt)}\nuser\t{_mins(dc)}\nsys\t{_mins(0)}\n")
    return code


def _mins(s):
    return f"{int(s // 60)}m{s % 60:.3f}s"


# ---------------------------------------------------------------- les scripts
def lire_script(ctx, vp, nom_aff):
    try:
        if ctx.vfs.est_dossier(vp):
            raise ErreurFs(21)
        return ctx.vfs.lire(vp).decode("utf-8", "replace"), 0
    except ErreurFs as e:
        return None, e


def executer_script(ctx, texte, nom, args):
    """Un script dans un shell enfant (ses variables ne reviennent pas, comme un vrai `sh f.sh`)."""
    sh = ctx.sh.enfant(script=True, nom=nom, args=args)
    try:
        arbre = S.analyser(texte)
    except S.Incomplet as e:
        n = texte.count("\n") + (0 if texte.endswith("\n") else 1)
        if e.guillemet:
            ctx.err(f"{nom}: line {n}: unexpected EOF while looking for matching `{e.guillemet}'\n")
        else:
            ctx.err(f"{nom}: line {n + 1}: syntax error: unexpected end of file\n")
        return 2
    except S.ErreurSyntaxe as e:
        ctx.err(f"{nom}: line {e.ligne}: {e}\n{nom}: line {e.ligne}: `{e.texte}'\n")
        return 2
    sh.nom = nom
    return tourner_script(sh, arbre, ctx)


def tourner_script(sh, arbre, ctx):
    from .shell import ErreurExpansion
    code = 0
    try:
        code = sh.liste(arbre, ctx.entree, ctx.sortie, ctx.erreur)
    except Sortie as s:
        code = s.code
    except Retour as r:
        code = r.code
    except Boucle:
        code = 0
    except ErreurExpansion as x:
        ctx.err(sh.prefixe() + f"{x}\n")
        code = 127 if str(x).endswith("unbound variable") and sh.est_c else 1
    sh.statut = code
    lancer_piege(sh, "EXIT", ctx.entree, ctx.sortie, ctx.erreur)
    return code


SHEBANGS_SHELL = re.compile(r"^#!\s*(/usr/bin/env\s+)?(/bin/|/usr/bin/)?(sh|bash|dash|zsh|ksh|mksh)\b")


@interne("sh", "bash", "dash")
def sh_(ctx):
    a = ctx.args[1:]
    opts = {"n": False, "x": False, "e": False}
    commande = None
    while a and a[0].startswith("-") and len(a[0]) > 1 and a[0] != "--":
        if a[0] == "-c":
            if len(a) < 2:
                return _err(ctx, "-c: option requires an argument", 2)
            commande = a[1]
            a = a[2:]
            break
        if a[0] in ("--version",):
            ctx.out("GNU bash, version 5.2 (le terminal du jeu Terminagotchi : un petit shell POSIX écrit en Python)\n")
            return 0
        for f in a[0][1:]:
            if f in opts:
                opts[f] = True
        a = a[1:]
    if a and a[0] == "--":
        a = a[1:]
    if commande is not None:
        sous = ctx.sh.enfant(script=True, nom=a[0] if a else ctx.args[0], args=a[1:])
        sous.options.update({"x": opts["x"], "e": opts["e"]})
        sous.est_c = True
        try:
            arbre = S.analyser(commande)
        except S.Incomplet as e:
            ctx.err(f"{sous.nom}: -c: line 1: " + (f"unexpected EOF while looking for matching `{e.guillemet}'\n"
                                                    if e.guillemet else "syntax error: unexpected end of file\n"))
            return 2
        except S.ErreurSyntaxe as e:
            ctx.err(f"{sous.nom}: -c: line {e.ligne}: {e}\n{sous.nom}: -c: line {e.ligne}: `{e.texte}'\n")
            return 2
        return tourner_script(sous, arbre, ctx)
    if not a:
        if ctx.entree.tty:
            ctx.err(f"{ctx.args[0]}: le terminal du jeu est déjà un shell : tape tes commandes ici.\n")
            return 0
        texte = ctx.entree.tout().decode("utf-8", "replace")
        return executer_script(ctx, texte, ctx.args[0], [])
    f = a[0]
    vp = ctx.chemin(f)
    texte, e = lire_script(ctx, vp, f)
    if texte is None:
        if e.errno == 2:
            ctx.err(f"{ctx.args[0]}: {f}: No such file or directory\n")
            return 127
        ctx.err(f"{ctx.args[0]}: {f}: {e.texte}\n")
        return 126
    if opts["n"]:
        try:
            S.analyser(texte)
            return 0
        except S.Incomplet as e:
            n = texte.count("\n") + (0 if texte.endswith("\n") else 1)
            ctx.err(f"{f}: line {n + 1}: syntax error: unexpected end of file\n" if not e.guillemet else
                    f"{f}: line {n}: unexpected EOF while looking for matching `{e.guillemet}'\n")
            return 2
        except S.ErreurSyntaxe as x:
            ctx.err(f"{f}: line {x.ligne}: {x}\n{f}: line {x.ligne}: `{x.texte}'\n")
            return 2
    if opts["x"] or opts["e"]:
        sh = ctx.sh.enfant(script=True, nom=f, args=a[1:])
        sh.options.update({"x": opts["x"], "e": opts["e"]})
        try:
            arbre = S.analyser(texte)
        except S.Incomplet:
            ctx.err(f"{f}: line {texte.count(chr(10)) + 1}: syntax error: unexpected end of file\n")
            return 2
        except S.ErreurSyntaxe as x:
            ctx.err(f"{f}: line {x.ligne}: {x}\n{f}: line {x.ligne}: `{x.texte}'\n")
            return 2
        return tourner_script(sh, arbre, ctx)
    return executer_script(ctx, texte, f, a[1:])


def lancer_fichier(ctx):
    """`./f.sh`, `/chemin/f.sh` : il faut le droit d'exécuter (x) ; un script de shell tourne ici ; un programme
    compilé ou un autre langage n'existe pas dans le terminal du jeu."""
    nom = ctx.args[0]
    vp = ctx.chemin(nom)
    if not ctx.vfs.existe(vp):
        ctx.err(ctx.sh.prefixe() + f"{nom}: No such file or directory\n")
        return 127
    if ctx.vfs.est_dossier(vp):
        ctx.err(ctx.sh.prefixe() + f"{nom}: Is a directory\n")
        return 126
    inf = ctx.vfs.infos(vp)
    if posixpath.dirname(vp) in ("/bin", "/usr/bin"):
        return ctx.sh.lancer([posixpath.basename(vp)] + ctx.args[1:], ctx.entree, ctx.sortie, ctx.erreur)
    if not inf.mode & 0o100:
        ctx.err(ctx.sh.prefixe() + f"{nom}: Permission denied\n")
        return 126
    try:
        donnees = ctx.vfs.lire(vp)
    except ErreurFs as e:
        ctx.err(ctx.sh.prefixe() + f"{nom}: {e.texte}\n")
        return 126
    premiere = donnees.split(b"\n", 1)[0].decode("utf-8", "replace")
    if donnees[:4] == b"\x7fELF" or (premiere.startswith("#!") and not SHEBANGS_SHELL.match(premiere)):
        from . import outils
        prog = "programme" if donnees[:4] == b"\x7fELF" else premiere[2:].strip().split("/")[-1].split()[-1]
        if prog in ("python3", "python"):        # #!/usr/bin/env python3 : le Python du jeu (python.py)
            return ctx.sh.lancer([prog, nom] + ctx.args[1:], ctx.entree, ctx.sortie, ctx.erreur)
        return outils.raconter(ctx, prog, code=126)
    return executer_script(ctx, donnees.decode("utf-8", "replace"), nom, ctx.args[1:])


@interne("clear", "reset")
def clear(ctx):
    if ctx.sortie.tty:
        ctx.out("\033[H\033[2J\033[3J")
    else:
        ctx.out("\033[H\033[2J\033[3J")
    return 0


def motif(m, t):
    return motif_shell(m, t)


_ = Entree, Interrompu
