"""Le terminal du jeu : les calculs $(( … )) comme bash (entiers 64 bits, division qui tronque vers zéro)."""
import re

_JETON = re.compile(r"\s*(?:(0[xX][0-9a-fA-F]+|\d+#[0-9a-zA-Z@_]+|\d+)|([A-Za-z_][A-Za-z0-9_]*)|"
                    r"(\*\*=|<<=|>>=|\+\+|--|\*\*|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&^|]=|[-+*/%<>=!~&^|?:(),]))")
BITS = 1 << 64


def _signe(n):
    n %= BITS
    return n - BITS if n >= 1 << 63 else n


def _nombre(t):
    if t.lower().startswith("0x"):
        return int(t, 16)
    if "#" in t:
        b, v = t.split("#", 1)
        chiffres = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ@_"
        b = int(b)
        n = 0
        for c in v:
            d = chiffres.index(c) if b > 36 else chiffres.index(c.lower())
            if d >= b:
                raise ValueError("value too great for base (error token is \"" + t + "\")")
            n = n * b + d
        return n
    if len(t) > 1 and t.startswith("0"):
        try:
            return int(t, 8)
        except ValueError:
            raise ValueError(f"value too great for base (error token is \"{t}\")")
    return int(t)


class _Eval:
    def __init__(self, texte, sh):
        self.t = []
        self.pos = []
        i = 0
        texte = texte.lstrip()
        while i < len(texte):
            if texte[i].isspace():
                i += 1
                continue
            m = _JETON.match(texte, i)
            if not m or m.end() == i:
                raise ErreurCalcul("syntax error: invalid arithmetic operator", texte[i:].lstrip())
            if m.group(1):
                self.t.append(("n", m.group(1)))
            elif m.group(2):
                self.t.append(("v", m.group(2)))
            else:
                self.t.append(("o", m.group(3)))
            self.pos.append(m.start(m.lastindex))
            i = m.end()
        self.k = 0
        self.sh = sh
        self.texte = texte

    def voir(self):
        return self.t[self.k] if self.k < len(self.t) else (None, None)

    def prendre(self):
        x = self.voir()
        self.k += 1
        return x

    def lire_var(self, nom):
        v = self.sh.var(nom) if self.sh else None
        if v is None or v.strip() == "":
            return 0
        v = v.strip()
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        return evaluer(v, self.sh)

    def ecrire_var(self, nom, val):
        if self.sh is not None:
            self.sh.vars[nom] = str(val)
        return val

    def reste(self, k):
        if k >= len(self.t):
            k = len(self.t) - 1
        return self.texte[self.pos[k]:] if self.t else ""

    def tout(self):
        if not self.t:
            return 0
        v = self.virgule()
        if self.k < len(self.t):
            raise ErreurCalcul("syntax error in expression", self.reste(self.k))
        return v

    def virgule(self):
        v = self.affect()
        while self.voir() == ("o", ","):
            self.k += 1
            v = self.affect()
        return v

    def affect(self):
        x = self.voir()
        if x[0] == "v" and self.k + 1 < len(self.t) and self.t[self.k + 1][0] == "o" and \
                self.t[self.k + 1][1] in ("=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|=", "**="):
            nom = x[1]
            op = self.t[self.k + 1][1]
            self.k += 2
            droite = self.affect()
            if op == "=":
                return self.ecrire_var(nom, droite)
            return self.ecrire_var(nom, self.binaire(op[:-1], self.lire_var(nom), droite))
        return self.ternaire()

    def ternaire(self):
        c = self.ou()
        if self.voir() == ("o", "?"):
            self.k += 1
            a = self.affect()
            if self.prendre() != ("o", ":"):
                raise ValueError("`:' expected for conditional expression")
            b = self.affect()
            return a if c else b
        return c

    NIVEAUX = [("||",), ("&&",), ("|",), ("^",), ("&",), ("==", "!="), ("<", "<=", ">", ">="), ("<<", ">>"),
               ("+", "-"), ("*", "/", "%")]

    def ou(self):
        return self.niveau(0)

    def niveau(self, n):
        if n >= len(self.NIVEAUX):
            return self.puissance()
        v = self.niveau(n + 1)
        while self.voir()[0] == "o" and self.voir()[1] in self.NIVEAUX[n]:
            op = self.prendre()[1]
            k_droite = self.k
            d = self.niveau(n + 1)
            try:
                v = self.binaire(op, v, d)
            except ZeroDivisionError:
                raise ErreurCalcul("division by 0", self.reste(k_droite))
        return v

    def puissance(self):
        b = self.unaire()
        if self.voir() == ("o", "**"):
            self.k += 1
            e = self.puissance()
            if e < 0:
                raise ValueError("exponent less than 0 (error token is \"" + str(e) + "\")")
            return _signe(b ** e)
        return b

    def unaire(self):
        x = self.voir()
        if x[0] == "o" and x[1] in ("+", "-", "!", "~"):
            self.k += 1
            v = self.unaire()
            return {"+": v, "-": _signe(-v), "!": int(not v), "~": _signe(~v)}[x[1]]
        if x[0] == "o" and x[1] in ("++", "--"):
            self.k += 1
            y = self.prendre()
            if y[0] != "v":
                raise ValueError("syntax error: operand expected")
            v = self.lire_var(y[1]) + (1 if x[1] == "++" else -1)
            return self.ecrire_var(y[1], v)
        return self.postfixe()

    def postfixe(self):
        x = self.prendre()
        if x[0] == "n":
            return _signe(_nombre(x[1]))
        if x[0] == "v":
            if self.voir()[0] == "o" and self.voir()[1] in ("++", "--"):
                op = self.prendre()[1]
                v = self.lire_var(x[1])
                self.ecrire_var(x[1], v + (1 if op == "++" else -1))
                return v
            return self.lire_var(x[1])
        if x == ("o", "("):
            v = self.virgule()
            if self.prendre() != ("o", ")"):
                raise ValueError("missing `)'")
            return v
        raise ErreurCalcul("syntax error: operand expected", self.reste(self.k - 2 if x[0] is None else self.k - 1))

    @staticmethod
    def binaire(op, a, b):
        if op in ("/", "%"):
            if b == 0:
                raise ZeroDivisionError()
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            return _signe(q) if op == "/" else _signe(a - q * b)
        r = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b, "**": lambda: a ** b,
             "<<": lambda: a << (b & 63), ">>": lambda: a >> (b & 63), "<": lambda: int(a < b),
             "<=": lambda: int(a <= b), ">": lambda: int(a > b), ">=": lambda: int(a >= b), "==": lambda: int(a == b),
             "!=": lambda: int(a != b), "&": lambda: a & b, "^": lambda: a ^ b, "|": lambda: a | b,
             "&&": lambda: int(bool(a) and bool(b)), "||": lambda: int(bool(a) or bool(b))}[op]()
        return _signe(r)


class ErreurCalcul(ValueError):
    def __init__(self, msg, jeton):
        super().__init__(msg)
        self.msg, self.jeton = msg, jeton


def evaluer(texte, sh=None):
    return _Eval(texte, sh).tout()
