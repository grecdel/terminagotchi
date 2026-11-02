"""Le terminal du jeu : awk (POSIX, comme gawk/mawk pour ce que font les leçons), écrit en Python.

Motifs (BEGIN, END, expressions, /motif/, plages), actions (print, printf, if, while, do, for, for-in, next, exit,
delete, getline, fonctions), champs ($0, $1, NF), variables (NR, FNR, NF, FS, OFS, ORS, FILENAME, RSTART, RLENGTH,
SUBSEP), tableaux associatifs, fonctions intégrées (length, substr, index, split, sub, gsub, match, sprintf, tolower,
toupper, int, sqrt, exp, log, sin, cos, atan2, rand, srand), options -F -v -f.
"""
import math
import random
import re

from .outils import outil
from .texte import regex_posix
from .vfs import ErreurFs


class ErreurAwk(Exception):
    pass


class _Suivant(Exception):
    pass


class _Fin(Exception):
    def __init__(self, code):
        self.code = code


class _Retour(Exception):
    def __init__(self, v):
        self.v = v


class _Casse(Exception):
    pass


class _Continue(Exception):
    pass


# ---------------------------------------------------------------- les valeurs
class StrNum(str):
    """Un texte venu de l'entrée (champ, getline, -v) : il compare comme un nombre s'il en a l'air."""


_NUM = re.compile(r"^\s*[-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?|0[xX][0-9a-fA-F]+)\s*$")


def num(v):
    if isinstance(v, (int, float)):
        return v
    m = re.match(r"\s*([-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?))", v)
    if not m:
        return 0
    t = m.group(1)
    try:
        f = float(t)
    except ValueError:
        return 0
    return f


def chaine(v, fmt="%.6g"):
    if isinstance(v, str):
        return v
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e16:
            return str(int(v))
        if math.isnan(v):
            return "nan" if math.copysign(1, v) > 0 else "-nan"
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        return fmt % v
    return str(v)


def vrai(v):
    if isinstance(v, StrNum):
        return num(v) != 0 if _NUM.match(v) else v != ""
    if isinstance(v, str):
        return v != ""
    return v != 0


# ---------------------------------------------------------------- le lexique
MOTS = {"BEGIN", "END", "function", "func", "if", "else", "while", "for", "do", "break", "continue", "next",
        "nextfile", "exit", "return", "delete", "in", "getline", "print", "printf"}
FONCTIONS = {"length", "substr", "index", "split", "sub", "gsub", "match", "sprintf", "tolower", "toupper", "int",
             "sqrt", "exp", "log", "sin", "cos", "atan2", "rand", "srand", "system", "close", "fflush"}


def lexique(s):
    out = []
    i = 0
    n = len(s)

    def precedent_operande():
        if not out:
            return False
        g, v = out[-1]
        return g in ("num", "str", "nom", "fonc", "ere") or v in (")", "]", "$", "++", "--") and g == "op"
    while i < n:
        c = s[i]
        if c in " \t\r":
            i += 1
            continue
        if c == "\\" and i + 1 < n and s[i + 1] == "\n":
            i += 2
            continue
        if c == "\n":
            out.append(("nl", "\n"))
            i += 1
            continue
        if c == "#":
            while i < n and s[i] != "\n":
                i += 1
            continue
        if c == '"':
            j = i + 1
            t = []
            while j < n and s[j] != '"':
                if s[j] == "\\" and j + 1 < n:
                    d = s[j + 1]
                    m = re.match(r"[0-7]{1,3}", s[j + 1:])
                    if m:
                        t.append(chr(int(m.group(), 8)))
                        j += 1 + m.end()
                        continue
                    t.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "/": "/", "a": "\a",
                              "b": "\b", "f": "\f", "v": "\v"}.get(d, "\\" + d))
                    j += 2
                    continue
                t.append(s[j])
                j += 1
            if j >= n:
                raise ErreurAwk("non-terminated string")
            out.append(("str", "".join(t)))
            i = j + 1
            continue
        if c == "/" and not precedent_operande():
            j = i + 1
            t = []
            dans_crochets = False
            while j < n and (s[j] != "/" or dans_crochets):
                if s[j] == "\\" and j + 1 < n:
                    t.append(s[j:j + 2] if s[j + 1] != "/" else "/")
                    j += 2
                    continue
                if s[j] == "[":
                    dans_crochets = True
                elif s[j] == "]":
                    dans_crochets = False
                if s[j] == "\n":
                    raise ErreurAwk("non-terminated regular expression")
                t.append(s[j])
                j += 1
            out.append(("ere", "".join(t)))
            i = j + 1
            continue
        m = re.match(r"(\d+\.?\d*([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?)", s[i:])
        if m:
            out.append(("num", float(m.group(1))))
            i += m.end()
            continue
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", s[i:])
        if m:
            mot = m.group()
            i += m.end()
            if mot in MOTS:
                out.append(("mot", mot))
            elif mot in FONCTIONS:
                out.append(("fonc", mot))
            else:
                out.append(("nom", mot))
                if i < n and s[i] == "(":
                    out[-1] = ("appel", mot)
            continue
        for op in ("+=", "-=", "*=", "/=", "%=", "^=", "**=", "**", "==", "<=", ">=", "!=", "!~", "++", "--", "&&",
                   "||", ">>", "{", "}", "(", ")", "[", "]", ";", ",", "+", "-", "*", "/", "%", "^", "!", ">",
                   "<", "|", "?", ":", "~", "$", "="):
            if s.startswith(op, i):
                out.append(("op", "^" if op == "**" else ("^=" if op == "**=" else op)))
                i += len(op)
                break
        else:
            raise ErreurAwk(f"syntax error at source line 1: unexpected character '{c}'")
    out.append(("fin", None))
    return out


# ---------------------------------------------------------------- l'analyseur
class Analyseur:
    def __init__(self, s):
        self.t = lexique(s)
        self.k = 0
        self.fonctions = {}

    def voir(self, d=0):
        return self.t[min(self.k + d, len(self.t) - 1)]

    def prendre(self):
        x = self.t[self.k]
        self.k += 1
        return x

    def est(self, g, v=None):
        x = self.voir()
        return x[0] == g and (v is None or x[1] == v)

    def attendre(self, g, v=None):
        if not self.est(g, v):
            x = self.voir()
            raise ErreurAwk(f"syntax error at source line 1 near '{x[1] if x[1] is not None else 'end'}'")
        return self.prendre()

    def nls(self):
        while self.est("nl") or self.est("op", ";"):
            self.k += 1

    def nls_seuls(self):
        while self.est("nl"):
            self.k += 1

    def programme(self):
        regles = []
        self.nls()
        while not self.est("fin"):
            if self.est("mot", "BEGIN"):
                self.k += 1
                self.nls_seuls()
                regles.append(("BEGIN", None, self.bloc()))
            elif self.est("mot", "END"):
                self.k += 1
                self.nls_seuls()
                regles.append(("END", None, self.bloc()))
            elif self.est("mot", "function") or self.est("mot", "func"):
                self.k += 1
                x = self.prendre()
                nom = x[1]
                self.attendre("op", "(")
                params = []
                while not self.est("op", ")"):
                    params.append(self.attendre("nom")[1])
                    if self.est("op", ","):
                        self.k += 1
                        self.nls_seuls()
                self.attendre("op", ")")
                self.nls_seuls()
                self.fonctions[nom] = (params, self.bloc())
            else:
                motif = None
                motif2 = None
                if not self.est("op", "{"):
                    motif = self.expr()
                    if self.est("op", ","):
                        self.k += 1
                        self.nls_seuls()
                        motif2 = self.expr()
                if self.est("op", "{"):
                    action = self.bloc()
                else:
                    action = None
                regles.append(("plage" if motif2 is not None else "motif", (motif, motif2), action))
            self.nls()
        return regles

    def bloc(self):
        self.attendre("op", "{")
        stmts = []
        self.nls()
        while not self.est("op", "}"):
            stmts.append(self.instruction())
            self.nls()
        self.attendre("op", "}")
        return ("bloc", stmts)

    def fin_instruction(self):
        if self.est("op", ";") or self.est("nl"):
            self.k += 1
        elif self.est("op", "}") or self.est("fin"):
            pass

    def instruction_simple_ou_bloc(self):
        self.nls_seuls()
        if self.est("op", ";"):
            self.k += 1
            return ("bloc", [])
        return self.instruction()

    def instruction(self):
        x = self.voir()
        if x == ("op", "{"):
            return self.bloc()
        if x[0] == "mot":
            m = x[1]
            if m == "if":
                self.k += 1
                self.attendre("op", "(")
                c = self.expr()
                self.attendre("op", ")")
                alors = self.instruction_simple_ou_bloc()
                k0 = self.k
                self.nls()
                if self.est("mot", "else"):
                    self.k += 1
                    sinon = self.instruction_simple_ou_bloc()
                    return ("si", c, alors, sinon)
                self.k = k0
                return ("si", c, alors, None)
            if m == "while":
                self.k += 1
                self.attendre("op", "(")
                c = self.expr()
                self.attendre("op", ")")
                if self.est("op", ";"):
                    self.k += 1
                    return ("tantque", c, ("bloc", []))
                return ("tantque", c, self.instruction_simple_ou_bloc())
            if m == "do":
                self.k += 1
                corps = self.instruction_simple_ou_bloc()
                self.nls()
                self.attendre("mot", "while")
                self.attendre("op", "(")
                c = self.expr()
                self.attendre("op", ")")
                self.fin_instruction()
                return ("faire", corps, c)
            if m == "for":
                self.k += 1
                self.attendre("op", "(")
                if self.voir()[0] == "nom" and self.voir(1) == ("mot", "in"):
                    k0 = self.k
                    var = self.prendre()[1]
                    self.k += 1
                    tab = self.attendre("nom")[1]
                    if self.est("op", ")"):
                        self.k += 1
                        return ("pourdans", var, tab, self.instruction_simple_ou_bloc())
                    self.k = k0
                init = None if self.est("op", ";") else self.expr_simple_instruction()
                self.attendre("op", ";")
                self.nls_seuls()
                cond = None if self.est("op", ";") else self.expr()
                self.attendre("op", ";")
                self.nls_seuls()
                pas = None if self.est("op", ")") else self.expr_simple_instruction()
                self.attendre("op", ")")
                if self.est("op", ";"):
                    self.k += 1
                    return ("pour", init, cond, pas, ("bloc", []))
                return ("pour", init, cond, pas, self.instruction_simple_ou_bloc())
            if m in ("break", "continue", "next", "nextfile"):
                self.k += 1
                self.fin_instruction()
                return (m,)
            if m in ("exit", "return"):
                self.k += 1
                v = None
                if not (self.est("op", ";") or self.est("nl") or self.est("op", "}") or self.est("fin")):
                    v = self.expr()
                self.fin_instruction()
                return (m, v)
            if m == "delete":
                self.k += 1
                nom = self.attendre("nom")[1]
                if self.est("op", "["):
                    self.k += 1
                    idx = self.liste_expr("]")
                    self.attendre("op", "]")
                    self.fin_instruction()
                    return ("supprimer", nom, idx)
                self.fin_instruction()
                return ("supprimer", nom, None)
            if m in ("print", "printf"):
                self.k += 1
                args = []
                if not (self.est("op", ";") or self.est("nl") or self.est("op", "}") or self.est("op", ">") or
                        self.est("op", ">>") or self.est("op", "|") or self.est("fin")):
                    if self.est("op", "(") :
                        k0 = self.k
                        self.k += 1
                        try:
                            args = self.liste_expr(")", sans_sup=False)
                            self.attendre("op", ")")
                            if not (self.est("op", ";") or self.est("nl") or self.est("op", "}") or
                                    self.est("op", ">") or self.est("op", ">>") or self.est("op", "|") or
                                    self.est("fin")):
                                raise ErreurAwk("suite")
                        except ErreurAwk:
                            self.k = k0
                            args = self.liste_expr(None, sans_sup=True)
                    else:
                        args = self.liste_expr(None, sans_sup=True)
                redir = None
                if self.est("op", ">") or self.est("op", ">>") or self.est("op", "|"):
                    op = self.prendre()[1]
                    redir = (op, self.concat(sans_sup=True))
                self.fin_instruction()
                return (m, args, redir)
        e = self.expr_simple_instruction()
        self.fin_instruction()
        return ("expr", e)

    def expr_simple_instruction(self):
        return self.expr()

    def liste_expr(self, fin, sans_sup=False):
        out = []
        if fin and self.est("op", fin):
            return out
        out.append(self.expr(sans_sup))
        while self.est("op", ","):
            self.k += 1
            self.nls_seuls()
            out.append(self.expr(sans_sup))
        return out

    # expressions, de la priorité la plus faible à la plus forte
    def expr(self, sans_sup=False):
        return self.ternaire(sans_sup)

    def ternaire(self, sans_sup):
        c = self.ou(sans_sup)
        if self.est("op", "?"):
            self.k += 1
            self.nls_seuls()
            a = self.ternaire(sans_sup)
            self.nls_seuls()
            self.attendre("op", ":")
            self.nls_seuls()
            b = self.ternaire(sans_sup)
            return ("tern", c, a, b)
        if self.est("op") and self.voir()[1] in ("=", "+=", "-=", "*=", "/=", "%=", "^=") and \
                c[0] in ("var", "champ", "elem"):
            op = self.prendre()[1]
            self.nls_seuls()
            v = self.ternaire(sans_sup)
            return ("affecte", op, c, v)
        return c

    def ou(self, s):
        a = self.et(s)
        while self.est("op", "||"):
            self.k += 1
            self.nls_seuls()
            a = ("ou", a, self.et(s))
        return a

    def et(self, s):
        a = self.dans(s)
        while self.est("op", "&&"):
            self.k += 1
            self.nls_seuls()
            a = ("et", a, self.dans(s))
        return a

    def dans(self, s):
        a = self.correspond(s)
        while self.est("mot", "in"):
            self.k += 1
            tab = self.attendre("nom")[1]
            a = ("dans", [a], tab)
        return a

    def correspond(self, s):
        a = self.comparaison(s)
        while self.est("op", "~") or self.est("op", "!~"):
            op = self.prendre()[1]
            a = ("re_op", op, a, self.comparaison(s))
        return a

    def comparaison(self, s):
        a = self.concat(s)
        x = self.voir()
        if x[0] == "op" and x[1] in ("<", "<=", "!=", "==", ">=") or (x == ("op", ">") and not s):
            op = self.prendre()[1]
            b = self.concat(s)
            return ("cmp", op, a, b)
        return a

    def concat(self, sans_sup=False):
        a = self.additif()
        while True:
            x = self.voir()
            if x[0] in ("num", "str", "nom", "fonc", "appel", "ere") or (x[0] == "op" and x[1] in ("$", "(")):
                a = ("concat", a, self.additif())
            else:
                break
        return a

    def additif(self):
        a = self.mult()
        while self.est("op", "+") or self.est("op", "-"):
            op = self.prendre()[1]
            a = ("arith", op, a, self.mult())
        return a

    def mult(self):
        a = self.unaire()
        while self.est("op", "*") or self.est("op", "/") or self.est("op", "%"):
            op = self.prendre()[1]
            a = ("arith", op, a, self.unaire())
        return a

    def unaire(self):
        if self.est("op", "!"):
            self.k += 1
            return ("non", self.unaire())
        if self.est("op", "-"):
            self.k += 1
            return ("neg", self.unaire())
        if self.est("op", "+"):
            self.k += 1
            return ("plus", self.unaire())
        return self.puissance()

    def puissance(self):
        a = self.incr()
        if self.est("op", "^"):
            self.k += 1
            b = self.unaire_puissance()
            return ("arith", "^", a, b)
        return a

    def unaire_puissance(self):
        if self.est("op", "-"):
            self.k += 1
            return ("neg", self.unaire_puissance())
        return self.puissance()

    def incr(self):
        if self.est("op", "++") or self.est("op", "--"):
            op = self.prendre()[1]
            cible = self.incr()
            return ("preincr", op, cible)
        a = self.primaire()
        if (self.est("op", "++") or self.est("op", "--")) and a[0] in ("var", "champ", "elem"):
            op = self.prendre()[1]
            return ("postincr", op, a)
        return a

    def primaire(self):
        x = self.prendre()
        g, v = x
        if g == "num":
            return ("num", v)
        if g == "str":
            return ("str", v)
        if g == "ere":
            return ("ere", v)
        if g == "op" and v == "$":
            return ("champ", self.incr_dollar())
        if g == "op" and v == "(":
            e = self.expr()
            if self.est("op", ","):
                liste = [e]
                while self.est("op", ","):
                    self.k += 1
                    liste.append(self.expr())
                self.attendre("op", ")")
                if self.est("mot", "in"):
                    self.k += 1
                    tab = self.attendre("nom")[1]
                    return ("dans", liste, tab)
                raise ErreurAwk("syntax error")
            self.attendre("op", ")")
            return ("groupe", e)
        if g == "nom":
            if self.est("op", "["):
                self.k += 1
                idx = self.liste_expr("]")
                self.attendre("op", "]")
                return ("elem", v, idx)
            return ("var", v)
        if g == "appel":
            self.attendre("op", "(")
            args = self.liste_expr(")")
            self.attendre("op", ")")
            return ("appel", v, args)
        if g == "fonc":
            if self.est("op", "("):
                self.k += 1
                args = self.liste_expr(")")
                self.attendre("op", ")")
            else:
                args = []
            return ("fonc", v, args)
        if g == "mot" and v == "getline":
            cible = None
            if self.voir()[0] == "nom":
                cible = self.primaire()
            fichier = None
            if self.est("op", "<"):
                self.k += 1
                fichier = self.primaire()
            return ("getline", cible, fichier)
        raise ErreurAwk(f"syntax error at source line 1 near '{v}'")

    def incr_dollar(self):
        if self.est("op", "++") or self.est("op", "--"):
            op = self.prendre()[1]
            return ("preincr", op, self.primaire())
        if self.est("op", "-"):
            self.k += 1
            return ("neg", self.primaire())
        return self.primaire()


# ---------------------------------------------------------------- l'exécution
class Machine:
    def __init__(self, regles, fonctions, ctx, vars_init, fs):
        self.regles, self.fonctions, self.ctx = regles, fonctions, ctx
        self.v = {"FS": fs if fs is not None else " ", "OFS": " ", "ORS": "\n", "RS": "\n", "NR": 0.0, "NF": 0.0,
                  "FNR": 0.0, "FILENAME": "", "SUBSEP": "\x1c", "RSTART": 0.0, "RLENGTH": -1.0, "CONVFMT": "%.6g",
                  "OFMT": "%.6g"}
        self.v.update(vars_init)
        self.tableaux = {"ENVIRON": {k: StrNum(v) for k, v in ctx.sh.vars.items() if k in ctx.sh.exportees}}
        self.champs = [""]
        self.locales = []
        self.sorties = {}
        self.cache_re = {}
        self.plages = {}
        self.entree_lignes = None
        self.graine = 0

    # -- les champs
    def poser_ligne(self, l):
        self.champs = [StrNum(l)]
        self.decouper()

    def decouper(self):
        l = self.champs[0]
        fs = chaine(self.v["FS"])
        if fs == " ":
            parts = l.split()
        elif fs == "":
            parts = list(l)
        elif len(fs) == 1 and fs != "\\":
            parts = l.split(fs) if l else []
        else:
            parts = re.split(regex_posix(fs, True), l) if l else []
        self.champs = [self.champs[0]] + [StrNum(p) for p in parts]
        self.v["NF"] = float(len(parts))

    def reconstruire(self):
        self.champs[0] = StrNum(chaine(self.v["OFS"]).join(chaine(x) for x in self.champs[1:]))

    def champ(self, i):
        i = int(num(i))
        if i < 0:
            raise ErreurAwk(f"trying to access out of range field {i}")
        return self.champs[i] if i < len(self.champs) else StrNum("")

    def poser_champ(self, i, val):
        i = int(num(i))
        if i == 0:
            self.champs = [StrNum(chaine(val))]
            self.decouper()
            return
        while len(self.champs) <= i:
            self.champs.append(StrNum(""))
        self.champs[i] = val
        self.v["NF"] = float(len(self.champs) - 1)
        self.reconstruire()

    # -- variables
    def lire_var(self, nom):
        for loc in reversed(self.locales[-1:]):
            if nom in loc:
                return loc[nom]
        if nom == "NF":
            return self.v["NF"]
        return self.v.get(nom, "")

    def poser_var(self, nom, val):
        if self.locales and nom in self.locales[-1]:
            self.locales[-1][nom] = val
            return
        self.v[nom] = val
        if nom == "NF":
            n = int(num(val))
            self.champs = self.champs[:n + 1] + [StrNum("")] * max(0, n + 1 - len(self.champs))
            self.reconstruire()

    def tableau(self, nom):
        if self.locales and nom in self.locales[-1]:
            t = self.locales[-1][nom]
            if not isinstance(t, dict):
                t = {}
                self.locales[-1][nom] = t
            return t
        return self.tableaux.setdefault(nom, {})

    def cle(self, idx):
        return chaine(self.v["SUBSEP"]).join(self.chaine(self.eval(e)) for e in idx)

    def chaine(self, v):
        return chaine(v, chaine(self.v["CONVFMT"]))

    def regex(self, motif):
        if motif not in self.cache_re:
            try:
                self.cache_re[motif] = re.compile(regex_posix(motif, True))
            except re.error as e:
                raise ErreurAwk(f"regular expression error: {e}")
        return self.cache_re[motif]

    def regex_de(self, e):
        if e[0] == "ere":
            return self.regex(e[1])
        return self.regex(self.chaine(self.eval(e)))

    # -- les expressions
    def eval(self, e):
        g = e[0]
        if g == "num":
            return e[1]
        if g == "str":
            return e[1]
        if g == "ere":
            return 1.0 if self.regex(e[1]).search(self.champs[0]) else 0.0
        if g == "var":
            return self.lire_var(e[1])
        if g == "champ":
            return self.champ(self.eval(e[1]))
        if g == "elem":
            t = self.tableau(e[1])
            k = self.cle(e[2])
            if k not in t:
                t[k] = ""
            return t[k]
        if g == "groupe":
            return self.eval(e[1])
        if g == "concat":
            return self.chaine(self.eval(e[1])) + self.chaine(self.eval(e[2]))
        if g == "arith":
            a, b = num(self.eval(e[2])), num(self.eval(e[3]))
            return self.arith(e[1], a, b)
        if g == "neg":
            return -num(self.eval(e[1])) * 1.0
        if g == "plus":
            return num(self.eval(e[1])) * 1.0
        if g == "non":
            return 0.0 if vrai(self.eval(e[1])) else 1.0
        if g == "et":
            return 1.0 if vrai(self.eval(e[1])) and vrai(self.eval(e[2])) else 0.0
        if g == "ou":
            return 1.0 if vrai(self.eval(e[1])) or vrai(self.eval(e[2])) else 0.0
        if g == "tern":
            return self.eval(e[2]) if vrai(self.eval(e[1])) else self.eval(e[3])
        if g == "cmp":
            return 1.0 if self.comparer(e[1], self.eval(e[2]), self.eval(e[3])) else 0.0
        if g == "re_op":
            r = self.regex_de(e[3]).search(self.chaine(self.eval(e[2]))) is not None
            return 1.0 if r == (e[1] == "~") else 0.0
        if g == "dans":
            k = chaine(self.v["SUBSEP"]).join(self.chaine(self.eval(x)) for x in e[1])
            return 1.0 if k in self.tableau(e[2]) else 0.0
        if g == "affecte":
            op, cible, val = e[1], e[2], self.eval(e[3])
            if op != "=":
                val = self.arith(op[0], num(self.eval(cible)), num(val))
            elif isinstance(val, StrNum):
                val = StrNum(val)
            self.affecter(cible, val)
            return val
        if g == "preincr":
            v = num(self.eval(e[2])) + (1 if e[1] == "++" else -1)
            self.affecter(e[2], float(v))
            return float(v)
        if g == "postincr":
            v = num(self.eval(e[2]))
            self.affecter(e[2], float(v + (1 if e[1] == "++" else -1)))
            return float(v)
        if g == "fonc":
            return self.fonction(e[1], e[2])
        if g == "appel":
            return self.appel(e[1], e[2])
        if g == "getline":
            return self.getline(e[1], e[2])
        raise ErreurAwk(f"expression inconnue {g}")

    @staticmethod
    def arith(op, a, b):
        if op == "+":
            return float(a + b)
        if op == "-":
            return float(a - b)
        if op == "*":
            return float(a * b)
        if op == "/":
            if b == 0:
                raise ErreurAwk("division by zero")
            return float(a) / b
        if op == "%":
            if b == 0:
                raise ErreurAwk("division by zero in %")
            return math.fmod(a, b)
        if op == "^":
            try:
                return float(a) ** b
            except (OverflowError, ZeroDivisionError):
                return float("inf")
        raise ErreurAwk(op)

    def comparer(self, op, a, b):
        def numerique(x):
            return isinstance(x, (int, float)) or (isinstance(x, StrNum) and _NUM.match(x) is not None)
        if numerique(a) and numerique(b):
            x, y = num(a), num(b)
        else:
            x, y = self.chaine(a), self.chaine(b)
        return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y, "==": x == y, "!=": x != y}[op]

    def affecter(self, cible, val):
        if cible[0] == "var":
            self.poser_var(cible[1], val)
        elif cible[0] == "champ":
            self.poser_champ(self.eval(cible[1]), val)
        elif cible[0] == "elem":
            self.tableau(cible[1])[self.cle(cible[2])] = val
        elif cible[0] == "groupe":
            self.affecter(cible[1], val)
        else:
            raise ErreurAwk("assignment to non-variable")

    def fonction(self, nom, args):
        ev = lambda k: self.eval(args[k])  # noqa: E731
        if nom == "length":
            if not args:
                return float(len(self.champs[0]))
            if args[0][0] == "var" and isinstance(self.tableaux.get(args[0][1]), dict):
                return float(len(self.tableaux[args[0][1]]))
            return float(len(self.chaine(ev(0))))
        if nom == "substr":
            s = self.chaine(ev(0))
            m = num(ev(1))
            m = int(math.floor(m + 0.5)) if m == m else 1
            if len(args) > 2:
                n = num(ev(2))
                n = int(math.floor(n + 0.5))
                debut, fin = max(m, 1), m + n
            else:
                debut, fin = max(m, 1), len(s) + 1
            return s[debut - 1:max(debut - 1, fin - 1)]
        if nom == "index":
            return float(self.chaine(ev(0)).find(self.chaine(ev(1))) + 1)
        if nom == "split":
            s = self.chaine(ev(0))
            if len(args) > 2:
                if args[2][0] == "ere":
                    parts = re.split(self.regex(args[2][1]), s) if s else []
                else:
                    fs = self.chaine(ev(2))
                    parts = s.split() if fs == " " else (s.split(fs) if len(fs) == 1 else
                                                         re.split(regex_posix(fs, True), s)) if s else []
            else:
                fs = chaine(self.v["FS"])
                parts = s.split() if fs == " " else (s.split(fs) if len(fs) == 1 else re.split(regex_posix(fs, True), s)) if s else []
            t = self.tableau(args[1][1])
            t.clear()
            for k, p in enumerate(parts, 1):
                t[str(k)] = StrNum(p)
            return float(len(parts))
        if nom in ("sub", "gsub"):
            rx = self.regex_de(args[0])
            rempl = self.chaine(ev(1))
            cible = args[2] if len(args) > 2 else ("champ", ("num", 0.0))
            s = self.chaine(self.eval(cible))
            n = [0]

            def f(m):
                n[0] += 1
                out = []
                i = 0
                while i < len(rempl):
                    c = rempl[i]
                    if c == "\\" and i + 1 < len(rempl) and rempl[i + 1] in "&\\":
                        out.append(rempl[i + 1])
                        i += 2
                        continue
                    out.append(m.group(0) if c == "&" else c)
                    i += 1
                return "".join(out)
            r = rx.sub(f, s, count=0 if nom == "gsub" else 1)
            if n[0]:
                self.affecter(cible, r)
            return float(n[0])
        if nom == "match":
            s = self.chaine(ev(0))
            m = self.regex_de(args[1]).search(s)
            if m:
                self.v["RSTART"], self.v["RLENGTH"] = float(m.start() + 1), float(m.end() - m.start())
            else:
                self.v["RSTART"], self.v["RLENGTH"] = 0.0, -1.0
            return self.v["RSTART"]
        if nom == "sprintf":
            return sprintf(self.chaine(ev(0)), [self.eval(a) for a in args[1:]])
        if nom == "tolower":
            return self.chaine(ev(0)).lower()
        if nom == "toupper":
            return self.chaine(ev(0)).upper()
        if nom == "int":
            v = num(ev(0))
            return float(math.trunc(v)) if not math.isinf(v) else v
        if nom == "sqrt":
            v = num(ev(0))
            return math.sqrt(v) if v >= 0 else float("nan")
        if nom == "exp":
            return math.exp(num(ev(0)))
        if nom == "log":
            v = num(ev(0))
            return math.log(v) if v > 0 else (float("-inf") if v == 0 else float("nan"))
        if nom == "sin":
            return math.sin(num(ev(0)))
        if nom == "cos":
            return math.cos(num(ev(0)))
        if nom == "atan2":
            return math.atan2(num(ev(0)), num(ev(1)))
        if nom == "rand":
            return random.random()
        if nom == "srand":
            ancien = self.graine
            self.graine = num(ev(0)) if args else 0
            random.seed(self.graine)
            return float(ancien)
        if nom in ("close", "fflush"):
            return 0.0
        if nom == "system":
            from .shell import Entree
            return float(self.ctx.sh.executer(self.chaine(ev(0)), Entree(b""), self.ctx.sortie, self.ctx.erreur))
        raise ErreurAwk(f"function {nom} never defined")

    def appel(self, nom, args):
        if nom not in self.fonctions:
            raise ErreurAwk(f"calling undefined function {nom}")
        params, corps = self.fonctions[nom]
        loc = {}
        for k, p in enumerate(params):
            if k < len(args):
                a = args[k]
                if a[0] == "var" and (a[1] in self.tableaux or (self.locales and isinstance(self.locales[-1].get(a[1]), dict))):
                    loc[p] = self.tableau(a[1])
                else:
                    loc[p] = self.eval(a)
            else:
                loc[p] = ""
        self.locales.append(loc)
        try:
            self.executer(corps)
        except _Retour as r:
            return r.v if r.v is not None else ""
        finally:
            self.locales.pop()
        return ""

    def getline(self, cible, fichier):
        if fichier is not None:
            f = self.chaine(self.eval(fichier))
            if f not in self.sorties:
                try:
                    d = self.ctx.vfs.lire(self.ctx.chemin(f)).decode("utf-8", "surrogateescape")
                except ErreurFs:
                    return -1.0
                self.sorties[f] = iter(d.split("\n")[:-1] if d.endswith("\n") else d.split("\n"))
            l = next(self.sorties[f], None)
            if l is None:
                return 0.0
            if cible:
                self.affecter(cible, StrNum(l))
            else:
                self.poser_ligne(l)
            return 1.0
        if self.entree_lignes is None:
            return 0.0
        l = next(self.entree_lignes, None)
        if l is None:
            return 0.0
        self.v["NR"] = float(num(self.v["NR"]) + 1)
        self.v["FNR"] = float(num(self.v["FNR"]) + 1)
        if cible:
            self.affecter(cible, StrNum(l))
        else:
            self.poser_ligne(l)
        return 1.0

    # -- les instructions
    def executer(self, s):
        g = s[0]
        if g == "bloc":
            for x in s[1]:
                self.executer(x)
        elif g == "expr":
            self.eval(s[1])
        elif g in ("print", "printf"):
            args, redir = s[1], s[2]
            if g == "print":
                if not args:
                    texte = self.champs[0]
                else:
                    texte = chaine(self.v["OFS"]).join(chaine(self.eval(a), chaine(self.v["OFMT"])) for a in args)
                texte = chaine(texte) + chaine(self.v["ORS"])
            else:
                if not args:
                    raise ErreurAwk("printf: no format")
                texte = sprintf(self.chaine(self.eval(args[0])), [self.eval(a) for a in args[1:]])
            self.ecrire(texte, redir)
        elif g == "si":
            if vrai(self.eval(s[1])):
                self.executer(s[2])
            elif s[3] is not None:
                self.executer(s[3])
        elif g == "tantque":
            n = 0
            while vrai(self.eval(s[1])):
                n += 1
                if n % 1000 == 0:
                    self.ctx.verifier()
                try:
                    self.executer(s[2])
                except _Casse:
                    break
                except _Continue:
                    continue
        elif g == "faire":
            while True:
                try:
                    self.executer(s[1])
                except _Casse:
                    break
                except _Continue:
                    pass
                if not vrai(self.eval(s[2])):
                    break
        elif g == "pour":
            if s[1] is not None:
                self.eval(s[1])
            n = 0
            while s[2] is None or vrai(self.eval(s[2])):
                n += 1
                if n % 1000 == 0:
                    self.ctx.verifier()
                try:
                    self.executer(s[4])
                except _Casse:
                    break
                except _Continue:
                    pass
                if s[3] is not None:
                    self.eval(s[3])
        elif g == "pourdans":
            t = self.tableau(s[2])
            for k in list(t.keys()):
                if k not in t:
                    continue
                self.poser_var(s[1], StrNum(k))
                try:
                    self.executer(s[3])
                except _Casse:
                    break
                except _Continue:
                    continue
        elif g == "break":
            raise _Casse()
        elif g == "continue":
            raise _Continue()
        elif g in ("next", "nextfile"):
            raise _Suivant()
        elif g == "exit":
            raise _Fin(int(num(self.eval(s[1]))) if s[1] is not None else 0)
        elif g == "return":
            raise _Retour(self.eval(s[1]) if s[1] is not None else None)
        elif g == "supprimer":
            t = self.tableau(s[1])
            if s[2] is None:
                t.clear()
            else:
                t.pop(self.cle(s[2]), None)

    def ecrire(self, texte, redir):
        if redir is None:
            self.ctx.out(texte.encode("utf-8", "surrogateescape"))
            return
        op, cible = redir
        f = self.chaine(self.eval(cible))
        if op == "|":
            from .shell import Entree, Flux
            tampon = self.sorties.setdefault("|" + f, [])
            tampon.append(texte)
            return
        vp = self.ctx.chemin(f)
        try:
            if f not in self.sorties and op == ">":
                self.ctx.vfs.ecrire(vp, b"")
            self.sorties[f] = True
            self.ctx.vfs.ecrire(vp, texte.encode("utf-8", "surrogateescape"), ajout=True)
        except ErreurFs as e:
            raise ErreurAwk(f"can't redirect to {f} ({e.texte})")

    def fermer_tuyaux(self):
        from .shell import Entree
        for k, v in list(self.sorties.items()):
            if k.startswith("|") and isinstance(v, list):
                self.ctx.sh.executer(k[1:], Entree("".join(v).encode("utf-8", "surrogateescape")), self.ctx.sortie,
                                     self.ctx.erreur)

    # -- le programme
    def tourner(self, fichiers):
        code = 0
        try:
            for type_, motif, action in self.regles:
                if type_ == "BEGIN":
                    self.executer(action)
            if any(r[0] in ("motif", "plage", "END") for r in self.regles):
                for nom, donnees in fichiers:
                    self.v["FILENAME"] = nom if nom != "-" else ""
                    self.v["FNR"] = 0.0
                    texte = donnees.decode("utf-8", "surrogateescape")
                    rs = chaine(self.v["RS"])
                    if rs == "":
                        enregs = [x for x in re.split(r"\n\n+", texte.strip("\n"))] if texte.strip("\n") else []
                    elif rs == "\n":
                        enregs = texte.split("\n")
                        if texte.endswith("\n"):
                            enregs.pop()
                        if not texte:
                            enregs = []
                    else:
                        enregs = texte.split(rs[0])
                        if texte.endswith(rs[0]):
                            enregs.pop()
                    self.entree_lignes = iter(enregs)
                    while True:
                        l = next(self.entree_lignes, None)
                        if l is None:
                            break
                        self.v["NR"] = float(num(self.v["NR"]) + 1)
                        self.v["FNR"] = float(num(self.v["FNR"]) + 1)
                        self.poser_ligne(l)
                        try:
                            self.regle_ligne()
                        except _Suivant:
                            continue
                        self.ctx.verifier()
        except _Fin as f:
            code = f.code
        try:
            for type_, motif, action in self.regles:
                if type_ == "END":
                    self.executer(action)
        except _Fin as f:
            code = f.code
        self.fermer_tuyaux()
        return code

    def regle_ligne(self):
        for k, (type_, motif, action) in enumerate(self.regles):
            if type_ in ("BEGIN", "END"):
                continue
            if type_ == "plage":
                dedans = self.plages.get(k, False)
                if not dedans:
                    if vrai(self.eval(motif[0])):
                        dedans = True
                        self.plages[k] = not vrai(self.eval(motif[1]))
                    else:
                        continue
                else:
                    if vrai(self.eval(motif[1])):
                        self.plages[k] = False
            elif motif[0] is not None and not vrai(self.eval(motif[0])):
                continue
            if action is None:
                self.ctx.out((self.champs[0] + chaine(self.v["ORS"])).encode("utf-8", "surrogateescape"))
            else:
                self.executer(action)


def sprintf(fmt, args):
    out = []
    k = 0
    i = 0
    while i < len(fmt):
        c = fmt[i]
        if c != "%":
            out.append(c)
            i += 1
            continue
        if fmt[i + 1:i + 2] == "%":
            out.append("%")
            i += 2
            continue
        m = re.match(r"%([-+ #0]*)(\*|\d+)?(?:\.(\*|\d+))?([diouxXeEfFgGcs])", fmt[i:])
        if not m:
            out.append(c)
            i += 1
            continue
        drap, larg, prec, conv = m.groups()
        if larg == "*":
            larg = str(int(num(args[k]))) if k < len(args) else "0"
            k += 1
        if prec == "*":
            prec = str(int(num(args[k]))) if k < len(args) else "0"
            k += 1
        a = args[k] if k < len(args) else ""
        k += 1
        spec = "%" + drap + (larg or "") + ("." + prec if prec is not None else "")
        if conv in "diouxX":
            v = num(a)
            v = int(v) if not math.isinf(v) and not math.isnan(v) else 0
            if conv == "u" and v < 0:
                v += 1 << 64
            out.append((spec + ("d" if conv in "iu" else conv)) % v)
        elif conv in "eEfFgG":
            out.append((spec + conv) % float(num(a)))
        elif conv == "c":
            if isinstance(a, (int, float)):
                ch = chr(int(a)) if 0 <= int(a) < 0x110000 else ""
            else:
                ch = a[:1]
            out.append((spec + "s") % ch)
        else:
            out.append((spec + "s") % chaine(a))
        i += m.end()
    return "".join(out)


@outil("awk", "gawk", "mawk", "nawk")
def awk(ctx):
    a = ctx.args[1:]
    fs = None
    vars_init = {}
    prog = None
    i = 0
    while i < len(a):
        x = a[i]
        if x == "--":
            i += 1
            break
        if x == "-F" and i + 1 < len(a):
            fs = a[i + 1]
            i += 2
            continue
        if x.startswith("-F") and len(x) > 2:
            fs = x[2:]
            i += 1
            continue
        if x == "-v" and i + 1 < len(a):
            k, _, v = a[i + 1].partition("=")
            vars_init[k] = StrNum(_echap(v))
            i += 2
            continue
        if x.startswith("-v") and len(x) > 2:
            k, _, v = x[2:].partition("=")
            vars_init[k] = StrNum(_echap(v))
            i += 1
            continue
        if x == "-f" and i + 1 < len(a):
            try:
                prog = (prog or "") + ctx.vfs.lire(ctx.chemin(a[i + 1])).decode("utf-8", "replace")
            except ErreurFs as e:
                ctx.err(f"awk: fatal: can't open source file `{a[i + 1]}' for reading: {e.texte}\n")
                return 2
            i += 2
            continue
        if x == "--version":
            ctx.out("awk (le terminal du jeu Terminagotchi : un petit awk écrit en Python)\n")
            return 0
        break
    if prog is None:
        if i >= len(a):
            ctx.err("usage: awk [-F fs][-v var=value][prog | -f progfile][file ...]\n")
            return 2
        prog = a[i]
        i += 1
    if fs == "t":
        fs = "\t"
    elif fs is not None:
        fs = _echap(fs)
    reste = a[i:]
    try:
        an = Analyseur(prog)
        regles = an.programme()
    except ErreurAwk as e:
        ctx.err(f"awk: cmd. line:1: {prog}\nawk: cmd. line:1: {e}\n")
        return 2
    machine = Machine(regles, an.fonctions, ctx, vars_init, fs)
    fichiers = []
    for f in reste:
        if re.fullmatch(r"[A-Za-z_]\w*=.*", f):
            k, _, v = f.partition("=")
            machine.v[k] = StrNum(_echap(v))
            continue
        if f == "-":
            fichiers.append(("-", ctx.entree.tout()))
            continue
        try:
            fichiers.append((f, ctx.vfs.lire(ctx.chemin(f))))
        except ErreurFs as e:
            ctx.err(f"awk: fatal: cannot open file `{f}' for reading: {e.texte}\n")
            if e.errno == 21:
                ctx.err("")
            return 2
    if not reste or not fichiers and all(re.fullmatch(r"[A-Za-z_]\w*=.*", f) for f in reste):
        if any(r[0] != "BEGIN" for r in regles):
            fichiers = [("-", ctx.entree.tout())]
    try:
        return machine.tourner(fichiers)
    except ErreurAwk as e:
        ctx.err(f"awk: cmd. line:1: fatal: {e}\n")
        return 2


def _echap(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            d = s[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"', "/": "/", "r": "\r"}.get(d, "\\" + d))
            i += 2
            continue
        out.append(s[i])
        i += 1
    return "".join(out)
