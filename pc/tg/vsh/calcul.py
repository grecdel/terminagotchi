"""Le terminal du jeu : bc (la calculatrice de précision de Linux) et expr, écrits en Python."""
import re

from .outils import outil
from .vfs import ErreurFs


class N:
    """Un nombre de bc : m / 10**s (s = son « scale », le nombre de chiffres après la virgule)."""

    __slots__ = ("m", "s")

    def __init__(self, m, s=0):
        self.m, self.s = m, s

    @staticmethod
    def de(texte):
        if "." in texte:
            a, b = texte.split(".", 1)
            return N(int((a or "0") + b) if (a or b) else 0, len(b))
        return N(int(texte), 0)

    def vers(self, s):
        if s >= self.s:
            return N(self.m * 10 ** (s - self.s), s)
        d = 10 ** (self.s - s)
        q = abs(self.m) // d
        return N(q if self.m >= 0 else -q, s)

    def texte(self):
        signe = "-" if self.m < 0 else ""
        a = str(abs(self.m)).rjust(self.s + 1, "0")
        ent, dec = (a[:-self.s], a[-self.s:]) if self.s else (a, "")
        if ent == "0" and dec:
            ent = ""
        if self.m == 0:
            return "0"
        return signe + ent + ("." + dec if dec else "")

    def __float__(self):
        return self.m / 10 ** self.s


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


class Bc:
    def __init__(self, maths):
        self.vars = {}
        self.scale = 20 if maths else 0
        self.maths = maths
        self.sortie = []
        self.dernier = N(0)

    # -- le lexique
    def jetons(self, s):
        out = []
        i = 0
        while i < len(s):
            c = s[i]
            if c in " \t\r":
                i += 1
                continue
            if c == "\\" and s[i + 1:i + 2] == "\n":
                i += 2
                continue
            if s.startswith("/*", i):
                j = s.find("*/", i + 2)
                i = len(s) if j < 0 else j + 2
                continue
            if c == "#":
                j = s.find("\n", i)
                i = len(s) if j < 0 else j
                continue
            if c == '"':
                j = s.find('"', i + 1)
                out.append(("str", s[i + 1:j if j >= 0 else len(s)]))
                i = len(s) if j < 0 else j + 1
                continue
            m = re.match(r"[0-9A-F]*\.?[0-9A-F]+|[0-9A-F]+\.", s[i:])
            if m and (c.isdigit() or c == "." or c in "ABCDEF"):
                out.append(("num", m.group()))
                i += m.end()
                continue
            m = re.match(r"[a-z][a-z0-9_]*", s[i:])
            if m:
                out.append(("nom", m.group()))
                i += m.end()
                continue
            for op in ("++", "--", "+=", "-=", "*=", "/=", "%=", "^=", "==", "<=", ">=", "!=", "&&", "||",
                       "+", "-", "*", "/", "%", "^", "(", ")", "=", "<", ">", "!", ";", "\n", ",", "{", "}"):
                if s.startswith(op, i):
                    out.append(("op", op))
                    i += len(op)
                    break
            else:
                raise SyntaxError(f"illegal character: {c}")
        out.append(("fin", None))
        return out

    def executer(self, texte):
        self.t = self.jetons(texte)
        self.k = 0
        while self.t[self.k][0] != "fin":
            if self.t[self.k] in (("op", "\n"), ("op", ";")):
                self.k += 1
                continue
            self.instruction()

    def voir(self):
        return self.t[self.k]

    def prendre(self):
        x = self.t[self.k]
        self.k += 1
        return x

    def instruction(self):
        x = self.voir()
        if x == ("nom", "quit") or x == ("nom", "halt"):
            raise StopIteration()
        if x == ("nom", "print"):
            self.k += 1
            while True:
                y = self.voir()
                if y[0] == "str":
                    self.k += 1
                    self.sortie.append(y[1].replace("\\n", "\n").replace("\\t", "\t"))
                else:
                    self.sortie.append(self.formater(self.expr()))
                if self.voir() == ("op", ","):
                    self.k += 1
                    continue
                break
            return
        if x[0] == "str":
            self.k += 1
            self.sortie.append(x[1])
            return
        affecte = x[0] == "nom" and self.t[self.k + 1][0] == "op" and self.t[self.k + 1][1] in (
            "=", "+=", "-=", "*=", "/=", "%=", "^=")
        v = self.expr()
        if not affecte:
            self.dernier = v
            self.sortie.append(self.formater(v) + "\n")

    def formater(self, n):
        t = n.texte()
        if n.m == 0:
            t = "0"
        lignes = []
        while len(t) > 70:
            lignes.append(t[:69] + "\\")
            t = t[69:]
        lignes.append(t)
        return "\n".join(lignes)

    # -- les expressions
    def expr(self):
        x = self.voir()
        if x[0] == "nom" and self.t[self.k + 1][0] == "op" and self.t[self.k + 1][1] in (
                "=", "+=", "-=", "*=", "/=", "%=", "^="):
            nom = x[1]
            op = self.t[self.k + 1][1]
            self.k += 2
            v = self.expr()
            if op != "=":
                v = self.binaire(op[0], self.lire(nom), v)
            self.ecrire(nom, v)
            return v
        return self.ou()

    def lire(self, nom):
        if nom == "scale":
            return N(self.scale)
        if nom in ("ibase", "obase"):
            return N(10)
        if nom == "last":
            return self.dernier
        return self.vars.get(nom, N(0))

    def ecrire(self, nom, v):
        if nom == "scale":
            self.scale = max(0, v.vers(0).m)
        elif nom in ("ibase", "obase"):
            pass
        else:
            self.vars[nom] = v

    def ou(self):
        a = self.et()
        while self.voir() == ("op", "||"):
            self.k += 1
            b = self.et()
            a = N(1 if a.m or b.m else 0)
        return a

    def et(self):
        a = self.comp()
        while self.voir() == ("op", "&&"):
            self.k += 1
            b = self.comp()
            a = N(1 if a.m and b.m else 0)
        return a

    def comp(self):
        a = self.add()
        x = self.voir()
        if x[0] == "op" and x[1] in ("<", "<=", ">", ">=", "==", "!="):
            self.k += 1
            b = self.add()
            s = max(a.s, b.s)
            x1, y1 = a.vers(s).m, b.vers(s).m
            return N(int({"<": x1 < y1, "<=": x1 <= y1, ">": x1 > y1, ">=": x1 >= y1, "==": x1 == y1,
                          "!=": x1 != y1}[x[1]]))
        return a

    def add(self):
        a = self.mul()
        while self.voir() in (("op", "+"), ("op", "-")):
            op = self.prendre()[1]
            a = self.binaire(op, a, self.mul())
        return a

    def mul(self):
        a = self.puis()
        while self.voir() in (("op", "*"), ("op", "/"), ("op", "%")):
            op = self.prendre()[1]
            a = self.binaire(op, a, self.puis())
        return a

    def puis(self):
        a = self.unaire()
        if self.voir() == ("op", "^"):
            self.k += 1
            b = self.puis_droite()
            return self.binaire("^", a, b)
        return a

    def puis_droite(self):
        a = self.unaire()
        if self.voir() == ("op", "^"):
            self.k += 1
            return self.binaire("^", a, self.puis_droite())
        return a

    def unaire(self):
        if self.voir() == ("op", "-"):
            self.k += 1
            v = self.unaire()
            return N(-v.m, v.s)
        if self.voir() == ("op", "!"):
            self.k += 1
            v = self.unaire()
            return N(0 if v.m else 1)
        if self.voir() in (("op", "++"), ("op", "--")):
            op = self.prendre()[1]
            nom = self.prendre()[1]
            v = self.binaire(op[0], self.lire(nom), N(1))
            self.ecrire(nom, v)
            return v
        return self.primaire()

    def primaire(self):
        x = self.prendre()
        if x[0] == "num":
            return N.de(x[1])
        if x == ("op", "("):
            v = self.expr()
            if self.prendre() != ("op", ")"):
                raise SyntaxError("syntax error")
            return v
        if x[0] == "nom":
            nom = x[1]
            if self.voir() == ("op", "("):
                self.k += 1
                args = []
                while self.voir() != ("op", ")"):
                    args.append(self.expr())
                    if self.voir() == ("op", ","):
                        self.k += 1
                self.k += 1
                return self.fonction(nom, args)
            if self.voir() in (("op", "++"), ("op", "--")):
                op = self.prendre()[1]
                v = self.lire(nom)
                self.ecrire(nom, self.binaire(op[0], v, N(1)))
                return v
            return self.lire(nom)
        if x == ("op", "."):
            return self.dernier
        raise SyntaxError("syntax error")

    def binaire(self, op, a, b):
        if op in "+-":
            s = max(a.s, b.s)
            x, y = a.vers(s).m, b.vers(s).m
            return N(x + y if op == "+" else x - y, s)
        if op == "*":
            s = min(a.s + b.s, max(self.scale, a.s, b.s))
            return N(a.m * b.m, a.s + b.s).vers(s)
        if op == "/":
            if b.m == 0:
                raise ZeroDivisionError()
            s = self.scale
            num = a.m * 10 ** (s + b.s)
            den = b.m * 10 ** a.s
            return N(_trunc_div(num, den), s)
        if op == "%":
            if b.m == 0:
                raise ZeroDivisionError()
            q = self.binaire("/", a, b)
            s = max(self.scale + b.s, a.s)
            prod = N(q.m * b.m, q.s + b.s)
            return self.binaire("-", a.vers(max(a.s, s)), prod).vers(s)
        if op == "^":
            e = b.vers(0).m
            if e >= 0:
                s = min(a.s * e, max(self.scale, a.s))
                return N(a.m ** e, a.s * e).vers(s)
            p = N(a.m ** -e, a.s * -e)
            return self.binaire("/", N(1), p)
        raise SyntaxError(op)

    def fonction(self, nom, args):
        import decimal
        if nom == "sqrt":
            v = args[0]
            if v.m < 0:
                raise ValueError("square root of a negative number")
            s = max(self.scale, v.s)
            racine = _isqrt(v.vers(2 * s).m)
            return N(racine, s)
        if nom == "length":
            return N(len(str(abs(args[0].m)).lstrip("0")) or 1)
        if nom == "scale":
            return N(args[0].s)
        if self.maths and nom in ("s", "c", "a", "l", "e", "j"):
            ctx = decimal.Context(prec=self.scale + 20)
            x = decimal.Decimal(args[0].m) / (decimal.Decimal(10) ** args[0].s)
            with decimal.localcontext(ctx):
                if nom == "e":
                    r = x.exp()
                elif nom == "l":
                    r = x.ln()
                else:
                    r = _trigo(nom, x)
            texte = format(r, "f")
            v = N.de(texte if "." in texte else texte + ".0")
            return v.vers(self.scale)
        raise SyntaxError(f"function {nom} not defined")


def _isqrt(n):
    import math
    return math.isqrt(n)


def _trigo(nom, x):
    import decimal
    if nom == "a":
        # atan par la série (x petit après réduction)
        inverse = abs(x) > 1
        y = 1 / x if inverse else x
        somme, terme, k = decimal.Decimal(0), y, 0
        while True:
            t = terme / (2 * k + 1) * (1 if k % 2 == 0 else -1)
            if abs(t) < decimal.Decimal(10) ** -(decimal.getcontext().prec - 2):
                break
            somme += t
            terme *= y * y
            k += 1
        if inverse:
            pi = _pi()
            somme = (pi / 2 if x > 0 else -pi / 2) - somme
        return somme
    somme, k = decimal.Decimal(0), 0
    terme = x if nom == "s" else decimal.Decimal(1)
    while True:
        if abs(terme) < decimal.Decimal(10) ** -(decimal.getcontext().prec - 2):
            break
        somme += terme
        k += 1
        n = 2 * k + (1 if nom == "s" else 0)
        terme = -terme * x * x / ((n - 1) * n)
    return somme


def _pi():
    import decimal
    decimal.getcontext().prec += 5
    a = 4 * (4 * _trigo("a", decimal.Decimal(1) / 5) - _trigo("a", decimal.Decimal(1) / 239))
    decimal.getcontext().prec -= 5
    return +a


@outil("bc")
def bc(ctx):
    a = ctx.args[1:]
    maths = any(x in ("-l", "--mathlib") or (x.startswith("-") and "l" in x and not x.startswith("--")) for x in a)
    noms = [x for x in a if not x.startswith("-")]
    texte = ""
    for f in noms:
        try:
            texte += ctx.vfs.lire(ctx.chemin(f)).decode("utf-8", "replace") + "\n"
        except ErreurFs as e:
            ctx.err(f"File {f} is unavailable.\n" if e.errno == 2 else f"bc: {f}: {e.texte}\n")
            return 1
    if not noms or not ctx.entree.tty:
        texte += ctx.entree.tout().decode("utf-8", "replace")
    calc = Bc(maths)
    code = 0
    for ligne in texte.split("\n"):
        try:
            calc.executer(ligne + "\n")
        except StopIteration:
            break
        except ZeroDivisionError:
            ctx.err("Runtime error (func=(main), adr=0): Divide by zero\n")
        except (SyntaxError, IndexError, ValueError) as e:
            ctx.err(f"(standard_in) {texte.split(chr(10)).index(ligne) + 1}: syntax error\n"
                    if not isinstance(e, ValueError) else f"Runtime error: {e}\n")
        ctx.out("".join(calc.sortie))
        calc.sortie = []
    return code


@outil("expr")
def expr(ctx):
    a = ctx.args[1:]
    if not a:
        ctx.err("expr: missing operand\nTry 'expr --help' for more information.\n")
        return 2
    try:
        v, k = _expr_ou(a, 0)
        if k != len(a):
            ctx.err(f"expr: syntax error: unexpected argument {_q(a[k])}\n")
            return 2
    except ZeroDivisionError:
        ctx.err("expr: division by zero\n")
        return 2
    except ValueError:
        ctx.err("expr: non-integer argument\n")
        return 2
    except IndexError:
        ctx.err(f"expr: syntax error: missing argument after {_q(a[-1])}\n")
        return 2
    ctx.out(str(v) + "\n")
    return 1 if v in ("", 0, "0") else 0


def _q(s):
    return "‘" + s + "’" if False else "'" + s + "'"


def _vrai(v):
    return v not in ("", 0, "0")


def _expr_ou(a, k):
    v, k = _expr_et(a, k)
    while k < len(a) and a[k] == "|":
        w, k = _expr_et(a, k + 1)
        v = v if _vrai(v) else (w if _vrai(w) else 0)
    return v, k


def _expr_et(a, k):
    v, k = _expr_cmp(a, k)
    while k < len(a) and a[k] == "&":
        w, k = _expr_cmp(a, k + 1)
        v = v if _vrai(v) and _vrai(w) else 0
    return v, k


def _int(v):
    if isinstance(v, int):
        return v
    if re.fullmatch(r"[-+]?\d+", v.strip()):
        return int(v)
    raise ValueError()


def _expr_cmp(a, k):
    v, k = _expr_add(a, k)
    while k < len(a) and a[k] in ("<", "<=", "=", "==", "!=", ">=", ">"):
        op = a[k]
        w, k = _expr_add(a, k + 1)
        try:
            x, y = _int(v), _int(w)
        except ValueError:
            x, y = str(v), str(w)
        v = int({"<": x < y, "<=": x <= y, "=": x == y, "==": x == y, "!=": x != y, ">=": x >= y, ">": x > y}[op])
    return v, k


def _expr_add(a, k):
    v, k = _expr_mul(a, k)
    while k < len(a) and a[k] in ("+", "-"):
        op = a[k]
        w, k = _expr_mul(a, k + 1)
        v = _int(v) + _int(w) if op == "+" else _int(v) - _int(w)
    return v, k


def _expr_mul(a, k):
    v, k = _expr_match(a, k)
    while k < len(a) and a[k] in ("*", "/", "%"):
        op = a[k]
        w, k = _expr_match(a, k + 1)
        x, y = _int(v), _int(w)
        if op == "*":
            v = x * y
        else:
            if y == 0:
                raise ZeroDivisionError()
            q = abs(x) // abs(y) * (1 if (x >= 0) == (y >= 0) else -1)
            v = q if op == "/" else x - q * y
    return v, k


def _expr_match(a, k):
    v, k = _expr_prim(a, k)
    while k < len(a) and a[k] == ":":
        motif, k = _expr_prim(a, k + 1)
        from .texte import regex_posix
        m = re.match(regex_posix(str(motif)), str(v))
        if m and m.groups():
            v = m.group(1) or ""
        else:
            v = len(m.group()) if m else (0 if not re.compile(regex_posix(str(motif))).groups else "")
    return v, k


def _expr_prim(a, k):
    x = a[k]
    if x == "(":
        v, k = _expr_ou(a, k + 1)
        return v, k + 1
    if x == "length":
        return len(a[k + 1]), k + 2
    if x == "substr":
        s, p, n = a[k + 1], int(a[k + 2]), int(a[k + 3])
        return s[p - 1:p - 1 + n] if p > 0 and n > 0 else "", k + 4
    if x == "index":
        s, c = a[k + 1], a[k + 2]
        return min([s.find(ch) + 1 for ch in c if ch in s] or [0]), k + 3
    if x == "match":
        from .texte import regex_posix
        m = re.match(regex_posix(a[k + 2]), a[k + 1])
        return (m.group(1) if m and m.groups() else (len(m.group()) if m else 0)), k + 3
    if x == "+":
        return a[k + 1], k + 2
    if re.fullmatch(r"[-+]?\d+", x):
        return int(x), k + 1
    return x, k + 1
