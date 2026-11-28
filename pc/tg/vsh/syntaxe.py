"""Le terminal du jeu (Windows, décision du 2 novembre) : lire une ligne de shell POSIX (sh).

Découpe une ligne (ou un script) en arbre : listes (`a; b`, `a & b`), `&&` / `||`, tuyaux `|` (et `!`), commandes
simples (affectations `n=3`, mots, redirections `>` `>>` `<` `2>` `2>&1` `&>` `<<FIN`), sous-shells `( … )`, groupes
`{ …; }`, `if`, `for`, `while` / `until`, `case`, fonctions `nom() { … }`. Les mots gardent leurs guillemets : ils sont
développés au moment de l'exécution (shell.py : variables, `$( )`, `$(( ))`, `~`, jokers, découpage).
Rien n'est exécuté ici.
"""


class Incomplet(Exception):
    """La ligne n'est pas finie (un guillemet, un `do` sans `done`…) : le terminal attend la suite (invite `> `).
    guillemet : le guillemet resté ouvert (bash : « unexpected EOF while looking for matching `'' »)."""

    def __init__(self, guillemet=None):
        super().__init__(guillemet or "")
        self.guillemet = guillemet


class ErreurSyntaxe(Exception):
    """ligne : le numéro de la ligne fautive ; texte : cette ligne (bash la recopie dans les scripts)."""

    def __init__(self, msg, ligne=1, texte=""):
        super().__init__(msg)
        self.ligne, self.texte = ligne, texte


# ---------------------------------------------------------------- les nœuds de l'arbre
class Simple:
    def __init__(self, affect, mots, redirs, ligne=1):
        self.affect, self.mots, self.redirs, self.ligne = affect, mots, redirs, ligne


class Sous:            # ( liste )
    def __init__(self, corps, redirs=None):
        self.corps, self.redirs = corps, redirs or []


class Groupe:          # { liste; }
    def __init__(self, corps, redirs=None):
        self.corps, self.redirs = corps, redirs or []


class Si:
    def __init__(self, branches, sinon, redirs=None):
        self.branches, self.sinon, self.redirs = branches, sinon, redirs or []


class Pour:
    def __init__(self, var, mots, corps, redirs=None):
        self.var, self.mots, self.corps, self.redirs = var, mots, corps, redirs or []


class TantQue:
    def __init__(self, cond, corps, jusqua=False, redirs=None):
        self.cond, self.corps, self.jusqua, self.redirs = cond, corps, jusqua, redirs or []


class Cas:
    def __init__(self, mot, items, redirs=None):
        self.mot, self.items, self.redirs = mot, items, redirs or []


class Fonction:
    def __init__(self, nom, corps):
        self.nom, self.corps = nom, corps
        self.redirs = []


class Tuyau:
    def __init__(self, cmds, non=False):
        self.cmds, self.non = cmds, non


class EtOu:
    def __init__(self, premier, suite):
        self.premier, self.suite = premier, suite       # suite : [("&&" | "||", Tuyau)]


class Liste:
    def __init__(self, elements):
        self.elements = elements                          # [(EtOu, "&" | ";")]
        self.texte = ""


class Redir:
    def __init__(self, fd, op, cible, texte=None):
        self.fd, self.op, self.cible, self.texte = fd, op, cible, texte   # texte : le contenu d'un <<FIN


RESERVES = {"if", "then", "elif", "else", "fi", "for", "in", "do", "done", "while", "until", "case", "esac", "{", "}",
            "!", "function"}
META = set(" \t\n;&|<>()")


# ---------------------------------------------------------------- lire les mots
def _fin_paren(s, i):
    """i est juste après « $( » : l'indice de la « ) » qui ferme (guillemets et parenthèses imbriquées compris)."""
    prof = 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise Incomplet()
            i = j + 1
            continue
        if c == '"':
            i = _fin_guillemets(s, i + 1)
            continue
        if c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                raise Incomplet()
            i = j + 1
            continue
        if c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
            if prof == 0:
                return i
        elif c == "#" and (i == 0 or s[i - 1] in " \t\n;"):
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        i += 1
    raise Incomplet()


def _fin_accolade(s, i):
    """i juste après « ${ » : l'indice de la « } »."""
    prof = 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise Incomplet()
            i = j + 1
            continue
        if c == '"':
            i = _fin_guillemets(s, i + 1)
            continue
        if s.startswith("${", i):
            prof += 1
            i += 2
            continue
        if c == "}":
            prof -= 1
            if prof == 0:
                return i
        i += 1
    raise Incomplet()


def _fin_guillemets(s, i):
    """i juste après « " » : l'indice juste après le « " » qui ferme."""
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        if s.startswith("$((", i):
            i = _fin_paren(s, i + 2) + 1
            continue
        if s.startswith("$(", i):
            i = _fin_paren(s, i + 2) + 1
            continue
        if s.startswith("${", i):
            i = _fin_accolade(s, i + 2) + 1
            continue
        if c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                raise Incomplet()
            i = j + 1
            continue
        i += 1
    raise Incomplet('"')


def lire_mot(s, i):
    """Le mot qui commence en i (avec ses guillemets) : (mot, indice après)."""
    n = len(s)
    j = i
    while j < n:
        c = s[j]
        if c in META:
            break
        if c == "\\":
            if j + 1 >= n:
                raise Incomplet()
            j += 2
            continue
        if c == "'":
            k = s.find("'", j + 1)
            if k < 0:
                raise Incomplet("'")
            j = k + 1
            continue
        if c == '"':
            j = _fin_guillemets(s, j + 1)
            continue
        if c == "`":
            k = s.find("`", j + 1)
            if k < 0:
                raise Incomplet("`")
            j = k + 1
            continue
        if c == "$" and j + 1 < n and s[j + 1] == "(":
            j = _fin_paren(s, j + 2) + 1
            continue
        if c == "$" and j + 1 < n and s[j + 1] == "{":
            j = _fin_accolade(s, j + 2) + 1
            continue
        j += 1
    return s[i:j], j


# ---------------------------------------------------------------- les jetons
class Jeton:
    def __init__(self, genre, val, pos):
        self.genre, self.val, self.pos = genre, val, pos     # genre : "mot", "op", "nl", "fin"

    def __repr__(self):
        return f"{self.genre}:{self.val!r}"


OPS = ("&&", "||", ";;", "<<-", "<<", ">>", ">&", "<&", "&>", ">|", "<>", "|", "&", ";", "<", ">", "(", ")")


def jetons(s):
    out = []
    i, n = 0, len(s)
    heredocs = []                 # [(Jeton du délimiteur, sans tabulations)] en attente de la fin de ligne
    while i < n:
        c = s[i]
        if c in " \t":
            i += 1
            continue
        if c == "\\" and i + 1 < n and s[i + 1] == "\n":
            i += 2
            continue
        if c == "#":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "\n":
            out.append(Jeton("nl", "\n", i))
            i += 1
            if heredocs:
                for jet, tabs in heredocs:
                    delim = jet.val
                    cite = any(q in delim for q in "'\"\\")
                    d = delim.replace("'", "").replace('"', "").replace("\\", "")
                    lignes = []
                    while True:
                        if i >= n:
                            raise Incomplet()
                        j = s.find("\n", i)
                        ligne = s[i:] if j < 0 else s[i:j]
                        i = n if j < 0 else j + 1
                        if (ligne.lstrip("\t") if tabs else ligne) == d:
                            break
                        lignes.append(ligne.lstrip("\t") if tabs else ligne)
                        if j < 0:
                            raise Incomplet()
                    jet.texte = ("\n".join(lignes) + "\n") if lignes else ""
                    jet.cite = cite
                heredocs = []
            continue
        # un numéro de descripteur collé à une redirection : 2>, 2>>, 1>&2
        if c.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            if j < n and s[j] in "<>" and (not out or out[-1].genre != "mot" or i == 0 or s[i - 1] in " \t;|&("):
                out.append(Jeton("fd", int(s[i:j]), i))
                i = j
                continue
        if s.startswith("<(", i) or s.startswith(">(", i):       # <( ls ) : la substitution de processus
            j = _fin_paren(s, i + 2)
            out.append(Jeton("mot", s[i:j + 1], i))
            i = j + 1
            continue
        op = next((o for o in OPS if s.startswith(o, i)), None)
        if op:
            out.append(Jeton("op", op, i))
            i += len(op)
            if op in ("<<", "<<-"):
                while i < n and s[i] in " \t":
                    i += 1
                mot, i = lire_mot(s, i)
                if not mot:
                    raise ErreurSyntaxe("syntax error near unexpected token `newline'")
                jet = Jeton("mot", mot, i)
                jet.texte = None
                out.append(jet)
                heredocs.append((jet, op == "<<-"))
            continue
        mot, j = lire_mot(s, i)
        out.append(Jeton("mot", mot, i))
        i = j
    if heredocs:
        raise Incomplet()
    out.append(Jeton("fin", None, n))
    return out


# ---------------------------------------------------------------- l'analyseur
class Analyseur:
    def __init__(self, texte):
        self.s = texte
        self.j = jetons(texte)
        self.k = 0

    def voir(self):
        return self.j[self.k]

    def prendre(self):
        x = self.j[self.k]
        self.k += 1
        return x

    def est_mot(self, *vals):
        x = self.voir()
        return x.genre == "mot" and (not vals or x.val in vals)

    def est_op(self, *vals):
        x = self.voir()
        return x.genre == "op" and x.val in vals

    def sauter_nl(self):
        while self.voir().genre == "nl":
            self.k += 1

    def erreur(self, x=None):
        x = x or self.voir()
        if x.genre == "fin":
            raise Incomplet()
        v = "newline" if x.genre == "nl" else x.val
        n = self.s.count("\n", 0, x.pos) + 1
        lignes = self.s.split("\n")
        raise ErreurSyntaxe(f"syntax error near unexpected token `{v}'", n, lignes[n - 1].strip() if n <= len(lignes) else "")

    def attendre_mot(self, val):
        self.sauter_nl()
        x = self.voir()
        if x.genre == "mot" and x.val == val:
            self.k += 1
            return
        self.erreur(x)

    # programme : une suite de listes séparées par des fins de ligne
    def programme(self):
        self.sauter_nl()
        l = self.liste(fin=("fin",))
        self.sauter_nl()
        if self.voir().genre != "fin":
            self.erreur()
        return l

    def liste(self, fin=(), arrets=()):
        """Une liste de commandes jusqu'à un mot d'arrêt (then, fi, done…) ou une « ) »."""
        elems = []
        while True:
            self.sauter_nl()
            x = self.voir()
            if x.genre == "fin":
                break
            if x.genre == "mot" and x.val in arrets:
                break
            if x.genre == "op" and x.val in (")", ";;"):
                break
            eo = self.et_ou()
            sep = ";"
            x = self.voir()
            if x.genre == "op" and x.val in (";", "&"):
                sep = x.val
                self.k += 1
            elif x.genre == "nl":
                self.k += 1
            elems.append((eo, sep))
        return Liste(elems)

    def et_ou(self):
        premier = self.tuyau()
        suite = []
        while self.est_op("&&", "||"):
            op = self.prendre().val
            self.sauter_nl()
            suite.append((op, self.tuyau()))
        return EtOu(premier, suite)

    def tuyau(self):
        non = False
        if self.est_mot("!"):
            self.k += 1
            non = True
        cmds = [self.commande()]
        while self.est_op("|"):
            self.k += 1
            self.sauter_nl()
            cmds.append(self.commande())
        return Tuyau(cmds, non)

    def redirs(self):
        out = []
        while True:
            x = self.voir()
            fd = None
            if x.genre == "fd":
                fd = x.val
                self.k += 1
                x = self.voir()
            if x.genre == "op" and x.val in ("<", ">", ">>", ">&", "<&", "&>", ">|", "<>", "<<", "<<-"):
                self.k += 1
                y = self.voir()
                if y.genre != "mot":
                    self.erreur(y)
                self.k += 1
                out.append(Redir(fd, x.val, y.val, getattr(y, "texte", None)))
                if x.val in ("<<", "<<-"):
                    out[-1].cite = getattr(y, "cite", False)
                continue
            if fd is not None:
                self.erreur(x)
            return out

    def commande(self):
        x = self.voir()
        if x.genre == "op" and x.val == "(":
            self.k += 1
            corps = self.liste()
            if not self.est_op(")"):
                self.erreur()
            self.k += 1
            return Sous(corps, self.redirs())
        if x.genre == "mot":
            v = x.val
            if v == "{":
                self.k += 1
                corps = self.liste(arrets=("}",))
                self.attendre_mot("}")
                return Groupe(corps, self.redirs())
            if v == "if":
                return self.si()
            if v in ("while", "until"):
                self.k += 1
                cond = self.liste(arrets=("do",))
                self.attendre_mot("do")
                corps = self.liste(arrets=("done",))
                self.attendre_mot("done")
                return TantQue(cond, corps, v == "until", self.redirs())
            if v == "for":
                return self.pour()
            if v == "case":
                return self.cas()
            if v == "function":
                self.k += 1
                nom = self.prendre()
                if self.est_op("("):
                    self.k += 1
                    if not self.est_op(")"):
                        self.erreur()
                    self.k += 1
                self.sauter_nl()
                return Fonction(nom.val, self.commande())
            if v in ("then", "elif", "else", "fi", "do", "done", "esac", "}", "in"):
                self.erreur()
            # nom() { … }
            if self.j[self.k + 1].genre == "op" and self.j[self.k + 1].val == "(" and \
                    self.j[self.k + 2].genre == "op" and self.j[self.k + 2].val == ")":
                self.k += 3
                self.sauter_nl()
                return Fonction(v, self.commande())
        return self.simple()

    def simple(self):
        affect, mots, redirs = [], [], []
        ligne = self.s.count("\n", 0, self.voir().pos) + 1
        while True:
            x = self.voir()
            if x.genre in ("fd",) or (x.genre == "op" and x.val in ("<", ">", ">>", ">&", "<&", "&>", ">|", "<>", "<<", "<<-")):
                redirs += self.redirs()
                continue
            if x.genre != "mot":
                break
            if not mots and _est_affectation(x.val):
                affect.append(x.val)
                self.k += 1
                continue
            mots.append(x.val)
            self.k += 1
        if not affect and not mots and not redirs:
            self.erreur()
        return Simple(affect, mots, redirs, ligne)

    def si(self):
        self.k += 1
        branches = []
        cond = self.liste(arrets=("then",))
        self.attendre_mot("then")
        corps = self.liste(arrets=("elif", "else", "fi"))
        branches.append((cond, corps))
        sinon = None
        while True:
            self.sauter_nl()
            if self.est_mot("elif"):
                self.k += 1
                c = self.liste(arrets=("then",))
                self.attendre_mot("then")
                b = self.liste(arrets=("elif", "else", "fi"))
                branches.append((c, b))
                continue
            if self.est_mot("else"):
                self.k += 1
                sinon = self.liste(arrets=("fi",))
            self.attendre_mot("fi")
            break
        return Si(branches, sinon, self.redirs())

    def pour(self):
        self.k += 1
        x = self.prendre()
        if x.genre != "mot":
            self.erreur(x)
        var = x.val
        mots = None
        if self.est_op(";"):
            self.k += 1
        self.sauter_nl()
        if self.est_mot("in"):
            self.k += 1
            mots = []
            while self.voir().genre == "mot":
                mots.append(self.prendre().val)
            if self.est_op(";"):
                self.k += 1
            elif self.voir().genre == "nl":
                pass
            else:
                self.erreur()
        self.attendre_mot("do")
        corps = self.liste(arrets=("done",))
        self.attendre_mot("done")
        return Pour(var, mots, corps, self.redirs())

    def cas(self):
        self.k += 1
        x = self.prendre()
        if x.genre != "mot":
            self.erreur(x)
        mot = x.val
        self.attendre_mot("in")
        items = []
        while True:
            self.sauter_nl()
            if self.est_mot("esac"):
                self.k += 1
                break
            if self.est_op("("):
                self.k += 1
            motifs = []
            while True:
                y = self.prendre()
                if y.genre != "mot":
                    self.erreur(y)
                motifs.append(y.val)
                if self.est_op("|"):
                    self.k += 1
                    continue
                break
            if not self.est_op(")"):
                self.erreur()
            self.k += 1
            corps = self.liste(arrets=("esac",))
            items.append((motifs, corps))
            if self.est_op(";;"):
                self.k += 1
                continue
            self.sauter_nl()
            if self.est_mot("esac"):
                self.k += 1
                break
            self.erreur()
        return Cas(mot, items, self.redirs())


def _est_affectation(m):
    if "=" not in m:
        return False
    nom = m.split("=", 1)[0]
    return bool(nom) and (nom[0].isalpha() or nom[0] == "_") and all(c.isalnum() or c == "_" for c in nom)


def analyser(texte):
    """L'arbre d'un texte de shell. Incomplet si la suite manque, ErreurSyntaxe sinon."""
    a = Analyseur(texte)
    return a.programme()
