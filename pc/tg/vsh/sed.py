"""Le terminal du jeu : sed (GNU), écrit en Python. Adresses (n, $, /motif/, n,m, n~pas, !), commandes s y d p P
q Q a i c = l n N D h H g G x b t T : { }, options -n -e -f -E/-r -i -s."""
import re

from .outils import guillemets, outil
from .texte import regex_posix
from .vfs import ErreurFs


class ErreurSed(Exception):
    pass


class Cmd:
    def __init__(self):
        self.a1 = self.a2 = None
        self.non = False
        self.nom = None
        self.arg = None
        self.etat_plage = False
        self.fin_plage = None


def _lire_re(s, i, delim):
    """Le motif jusqu'au délimiteur (\\délim et les […] compris) : (motif, indice après)."""
    out = []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            if s[i + 1] == delim:
                out.append(delim)
            elif s[i + 1] == "n":
                out.append("\\n")
            else:
                out.append(s[i:i + 2])
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < len(s) and s[j] == "^":
                j += 1
            if j < len(s) and s[j] == "]":
                j += 1
            while j < len(s) and s[j] != "]":
                if s[j] == "[" and j + 1 < len(s) and s[j + 1] in ":.=":
                    k = s.find(s[j + 1] + "]", j + 2)
                    j = k + 2 if k >= 0 else j + 1
                    continue
                j += 1
            out.append(s[i:j + 1])
            i = j + 1
            continue
        if c == delim:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ErreurSed(f"unterminated address regex" if delim else "unterminated `s' command")


class Programme:
    def __init__(self, texte, etendue):
        self.etendue = etendue
        self.cmds = []
        self.labels = {}
        self.analyser(texte)

    def regex(self, motif, drapeaux=""):
        if motif == "":
            return None        # le dernier motif utilisé
        try:
            return re.compile(regex_posix(motif, self.etendue), (re.I if "I" in drapeaux or "i" in drapeaux else 0) |
                              (re.M if "M" in drapeaux else 0))
        except re.error as e:
            raise ErreurSed(f"-e expression #1, char 0: {e}")

    def adresse(self, s, i):
        if i >= len(s):
            return None, i
        c = s[i]
        if c.isdigit():
            m = re.match(r"(\d+)(~(\d+))?", s[i:])
            if m.group(2):
                return ("pas", int(m.group(1)), int(m.group(3))), i + m.end()
            return ("n", int(m.group(1))), i + m.end()
        if c == "$":
            return ("fin",), i + 1
        if c == "/" or c == "\\":
            delim = "/"
            if c == "\\":
                delim = s[i + 1]
                i += 1
            motif, i = _lire_re(s, i + 1, delim)
            drap = ""
            while i < len(s) and s[i] in "IM":
                drap += s[i]
                i += 1
            return ("re", self.regex(motif, drap)), i
        return None, i

    def analyser(self, s):
        i = 0
        pile = []
        n = len(s)
        while i < n:
            while i < n and s[i] in " \t\n;":
                i += 1
            if i >= n:
                break
            if s[i] == "#":
                while i < n and s[i] != "\n":
                    i += 1
                continue
            c = Cmd()
            c.a1, i = self.adresse(s, i)
            if c.a1 is not None and i < n and s[i] == ",":
                i += 1
                if i < n and s[i] == "+":
                    m = re.match(r"\+(\d+)", s[i:])
                    c.a2 = ("plus", int(m.group(1)))
                    i += m.end()
                elif i < n and s[i] == "~":
                    m = re.match(r"~(\d+)", s[i:])
                    c.a2 = ("multiple", int(m.group(1)))
                    i += m.end()
                else:
                    c.a2, i = self.adresse(s, i)
                    if c.a2 is None:
                        raise ErreurSed("unexpected `,'")
            while i < n and s[i] in " \t":
                i += 1
            if i < n and s[i] == "!":
                c.non = True
                i += 1
                while i < n and s[i] in " \t":
                    i += 1
            if i >= n:
                raise ErreurSed("missing command")
            nom = s[i]
            i += 1
            c.nom = nom
            if nom == "{":
                pile.append(len(self.cmds))
                self.cmds.append(c)
                continue
            if nom == "}":
                if not pile:
                    raise ErreurSed("unexpected `}'")
                debut = pile.pop()
                self.cmds[debut].arg = len(self.cmds) + 1
                self.cmds.append(c)
                continue
            if nom == "s":
                delim = s[i]
                motif, i = _lire_re(s, i + 1, delim)
                rempl = []
                while i < n and s[i] != delim:
                    if s[i] == "\\" and i + 1 < n:
                        rempl.append(s[i:i + 2] if s[i + 1] != delim else delim)
                        i += 2
                        continue
                    if s[i] == "\n":
                        rempl.append("\n")
                        i += 1
                        continue
                    rempl.append(s[i])
                    i += 1
                if i >= n:
                    raise ErreurSed("unterminated `s' command")
                i += 1
                drap = ""
                while i < n and s[i] not in ";\n}" and s[i] not in " \t":
                    drap += s[i]
                    i += 1
                fichier_w = None
                if "w" in drap:
                    k = drap.index("w")
                    fichier_w = drap[k + 1:] or s[i:].split("\n")[0].strip()
                    drap = drap[:k]
                c.arg = (self.regex(motif, drap), "".join(rempl), drap, fichier_w)
            elif nom == "y":
                delim = s[i]
                a, i = _lire_re(s, i + 1, delim)
                b, i = _lire_re(s, i, delim)
                a = a.replace("\\n", "\n").replace("\\\\", "\\")
                b = b.replace("\\n", "\n").replace("\\\\", "\\")
                if len(a) != len(b):
                    raise ErreurSed("strings for `y' command are different lengths")
                c.arg = str.maketrans(a, b)
            elif nom in "aic":
                while i < n and s[i] in " \t":
                    i += 1
                if i < n and s[i] == "\\":
                    i += 1
                    if i < n and s[i] == "\n":
                        i += 1
                texte = []
                while i < n and s[i] != "\n":
                    if s[i] == "\\" and i + 1 < n:
                        texte.append(s[i + 1] if s[i + 1] != "n" else "\n")
                        i += 2
                        continue
                    texte.append(s[i])
                    i += 1
                c.arg = "".join(texte)
            elif nom in "bt T":
                m = re.match(r"[ \t]*([^;\n}]*)", s[i:])
                c.arg = m.group(1).strip()
                i += m.end()
            elif nom == ":":
                m = re.match(r"[ \t]*([^;\n]*)", s[i:])
                self.labels[m.group(1).strip()] = len(self.cmds)
                i += m.end()
                continue
            elif nom in "qQ":
                m = re.match(r"[ \t]*(\d*)", s[i:])
                c.arg = int(m.group(1)) if m.group(1) else 0
                i += m.end()
            elif nom in "rRwW":
                m = re.match(r"[ \t]*([^\n]*)", s[i:])
                c.arg = m.group(1)
                i += m.end()
            elif nom in "dDpPnNgGhHxl=zF":
                pass
            else:
                raise ErreurSed(f"-e expression #1, char {i}: unknown command: `{nom}'")
            self.cmds.append(c)
        if pile:
            raise ErreurSed("-e expression #1, char 0: unmatched `{'")


def _remplacement(rempl, m):
    out = []
    casse = None          # \U \L
    un = None             # \u \l
    i = 0
    while i < len(rempl):
        c = rempl[i]
        morceau = None
        if c == "\\" and i + 1 < len(rempl):
            d = rempl[i + 1]
            i += 2
            if d.isdigit():
                morceau = m.group(int(d)) or ""
            elif d == "n":
                morceau = "\n"
            elif d == "t":
                morceau = "\t"
            elif d == "&":
                morceau = "&"
            elif d in "UL":
                casse = d
                continue
            elif d == "E":
                casse = None
                continue
            elif d in "ul":
                un = d
                continue
            else:
                morceau = d
        elif c == "&":
            morceau = m.group(0)
            i += 1
        else:
            morceau = c
            i += 1
        if casse == "U":
            morceau = morceau.upper()
        elif casse == "L":
            morceau = morceau.lower()
        if un and morceau:
            morceau = (morceau[0].upper() if un == "u" else morceau[0].lower()) + morceau[1:]
            un = None
        out.append(morceau)
    return "".join(out)


def executer(prog, lignes, silencieux, sortie, lire_fichier=None, ecrire_fichier=None, dernier_fichier=True):
    """Exécute le programme sur des lignes ; écrit dans sortie(texte). Renvoie (code, quitter)."""
    cmds = prog.cmds
    n = len(lignes)
    k = 0
    tenue = ""
    dernier_re = [None]
    quitter = None
    while k < n:
        espace = lignes[k]
        k += 1
        num = k
        apres = []
        sub_fait = False
        pc = 0
        supprime = False
        relancer = False

        def correspond(adr, num_):
            if adr[0] == "n":
                return num_ == adr[1]
            if adr[0] == "fin":
                return num_ == n and dernier_fichier
            if adr[0] == "pas":
                return (num_ - adr[1]) % adr[2] == 0 and num_ >= adr[1] if adr[2] else num_ == adr[1]
            if adr[0] == "re":
                rx = adr[1] or dernier_re[0]
                if rx is None:
                    raise ErreurSed("no previous regular expression")
                dernier_re[0] = rx
                return rx.search(espace) is not None
            return False

        while pc < len(cmds):
            c = cmds[pc]
            pc += 1
            if c.nom == "}":
                continue
            ok = True
            if c.a1 is not None:
                if c.a2 is None:
                    ok = correspond(c.a1, num)
                else:
                    if c.etat_plage:
                        a2 = c.a2
                        if a2[0] == "n":
                            if num >= a2[1]:
                                c.etat_plage = False
                            ok = True
                            if num > a2[1]:
                                ok = False
                        elif a2[0] in ("plus",):
                            ok = True
                            if num >= c.fin_plage:
                                c.etat_plage = False
                        elif a2[0] == "multiple":
                            ok = True
                            if a2[1] and num % a2[1] == 0:
                                c.etat_plage = False
                        else:
                            ok = True
                            if correspond(a2, num):
                                c.etat_plage = False
                    elif correspond(c.a1, num):
                        ok = True
                        a2 = c.a2
                        if a2[0] == "n":
                            c.etat_plage = a2[1] > num
                        elif a2[0] == "plus":
                            c.fin_plage = num + a2[1]
                            c.etat_plage = a2[1] > 0
                        elif a2[0] == "multiple":
                            c.etat_plage = not (a2[1] and num % a2[1] == 0)
                        elif a2[0] == "fin":
                            c.etat_plage = num != n
                        else:
                            c.etat_plage = True
                    else:
                        ok = False
            if c.non:
                ok = not ok
            if not ok:
                if c.nom == "{":
                    pc = c.arg
                continue
            nom = c.nom
            if nom == "{":
                continue
            if nom == "s":
                rx, rempl, drap, fw = c.arg
                rx = rx or dernier_re[0]
                if rx is None:
                    raise ErreurSed("no previous regular expression")
                dernier_re[0] = rx
                nieme = int(re.sub(r"\D", "", drap) or 0)
                tout = "g" in drap
                compte = [0]

                def f(m):
                    compte[0] += 1
                    if nieme and compte[0] < nieme:
                        return m.group(0)
                    if nieme and not tout and compte[0] > nieme:
                        return m.group(0)
                    return _remplacement(rempl, m)
                nouveau, nb = rx.subn(f, espace, count=0 if (tout or nieme) else 1)
                if nb and (not nieme or compte[0] >= nieme):
                    espace = nouveau
                    sub_fait = True
                    if "p" in drap:
                        sortie(espace + "\n")
                    if fw and ecrire_fichier:
                        ecrire_fichier(fw, espace + "\n")
            elif nom == "y":
                espace = espace.translate(c.arg)
            elif nom == "d":
                supprime = True
                break
            elif nom == "D":
                if "\n" in espace:
                    espace = espace.split("\n", 1)[1]
                    relancer = True
                    supprime = True
                    break
                supprime = True
                break
            elif nom == "p":
                sortie(espace + "\n")
            elif nom == "P":
                sortie(espace.split("\n", 1)[0] + "\n")
            elif nom == "=":
                sortie(f"{num}\n")
            elif nom == "l":
                sortie("".join(ch if 32 <= ord(ch) < 127 and ch != "\\" else
                               ("\\\\" if ch == "\\" else ("\\t" if ch == "\t" else ("\\n" if ch == "\n" else
                                                                                 f"\\{ord(ch):03o}")))
                               for ch in espace) + "$\n")
            elif nom == "a":
                apres.append(c.arg + "\n")
            elif nom == "i":
                sortie(c.arg + "\n")
            elif nom == "c":
                if c.a2 is None or not c.etat_plage:
                    sortie(c.arg + "\n")
                supprime = True
                break
            elif nom == "q":
                quitter = c.arg
                break
            elif nom == "Q":
                return c.arg, True
            elif nom == "n":
                if not silencieux:
                    sortie(espace + "\n")
                for x in apres:
                    sortie(x)
                apres = []
                if k >= n:
                    supprime = True
                    quitter = quitter if quitter is not None else None
                    break
                espace = lignes[k]
                k += 1
                num = k
            elif nom == "N":
                if k >= n:
                    break
                espace += "\n" + lignes[k]
                k += 1
                num = k
            elif nom == "h":
                tenue = espace
            elif nom == "H":
                tenue += "\n" + espace
            elif nom == "g":
                espace = tenue
            elif nom == "G":
                espace += "\n" + tenue
            elif nom == "x":
                espace, tenue = tenue, espace
            elif nom == "z":
                espace = ""
            elif nom == "b":
                if c.arg:
                    pc = prog.labels.get(c.arg, len(cmds))
                else:
                    pc = len(cmds)
            elif nom in "tT":
                if (nom == "t") == sub_fait:
                    sub_fait = False
                    pc = prog.labels.get(c.arg, len(cmds)) if c.arg else len(cmds)
            elif nom == "r" and lire_fichier:
                d = lire_fichier(c.arg)
                if d:
                    apres.append(d if d.endswith("\n") else d + "\n")
            elif nom == "w" and ecrire_fichier:
                ecrire_fichier(c.arg, espace + "\n")
        if not supprime and not silencieux:
            sortie(espace + "\n")
        for x in apres:
            sortie(x)
        if relancer:
            lignes.insert(k, espace)
            n += 1
        if quitter is not None:
            return quitter, True
    return 0, False


AIDE_SED = """Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...

  -n, --quiet, --silent
                 suppress automatic printing of pattern space
      --debug
                 annotate program execution
  -e script, --expression=script
                 add the script to the commands to be executed
  -f script-file, --file=script-file
                 add the contents of script-file to the commands to be executed
  --follow-symlinks
                 follow symlinks when processing in place
  -i[SUFFIX], --in-place[=SUFFIX]
                 edit files in place (makes backup if SUFFIX supplied)
  -l N, --line-length=N
                 specify the desired line-wrap length for the `l' command
  --posix
                 disable all GNU extensions.
  -E, -r, --regexp-extended
                 use extended regular expressions in the script
                 (for portability use POSIX -E).
  -s, --separate
                 consider files as separate rather than as a single
                 continuous long stream.
      --sandbox
                 operate in sandbox mode (disable e/r/w commands).
  -u, --unbuffered
                 load minimal amounts of data from the input files and flush
                 the output buffers more often
  -z, --null-data
                 separate lines by NUL characters
      --help     display this help and exit
      --version  output version information and exit

If no -e, --expression, -f, or --file option is given, then the first
non-option argument is taken as the sed script to interpret.  All
remaining arguments are names of input files; if no input files are
specified, then the standard input is read.

GNU sed home page: <https://www.gnu.org/software/sed/>.
General help using GNU software: <https://www.gnu.org/gethelp/>.
"""


@outil("sed")
def sed(ctx):
    a = ctx.args[1:]
    if "--help" in a:
        ctx.out(AIDE_SED)
        return 0
    scripts = []
    silencieux = etendue = sur_place = separes = False
    suffixe = ""
    noms = []
    i = 0
    while i < len(a):
        x = a[i]
        if x == "--":
            noms += a[i + 1:]
            break
        if x in ("-n", "--quiet", "--silent"):
            silencieux = True
        elif x in ("-E", "-r", "--regexp-extended"):
            etendue = True
        elif x == "-s" or x == "--separate":
            separes = True
        elif x == "-e" or x == "--expression":
            if i + 1 >= len(a):
                ctx.err("sed: option requires an argument -- 'e'\n")
                return 1
            scripts.append(a[i + 1])
            i += 1
        elif x.startswith("--expression="):
            scripts.append(x[13:])
        elif x == "-f":
            d = ctx.vfs.lire(ctx.chemin(a[i + 1])) if i + 1 < len(a) else b""
            scripts.append(d.decode("utf-8", "replace"))
            i += 1
        elif x.startswith("-i") or x.startswith("--in-place"):
            sur_place = True
            separes = True
            suffixe = x[2:] if x.startswith("-i") else x.partition("=")[2]
        elif x.startswith("-") and len(x) > 1 and not x.startswith("--"):
            lettres = x[1:]
            ok = True
            for k, l in enumerate(lettres):
                if l == "n":
                    silencieux = True
                elif l in "Er":
                    etendue = True
                elif l == "s":
                    separes = True
                elif l == "i":
                    sur_place = separes = True
                    suffixe = lettres[k + 1:]
                    break
                elif l == "e":
                    reste = lettres[k + 1:]
                    if reste:
                        scripts.append(reste)
                    else:
                        scripts.append(a[i + 1])
                        i += 1
                    break
                else:
                    ctx.err(f"sed: invalid option -- '{l}'\n")
                    ok = False
                    break
            if not ok:
                return 1
        else:
            noms.append(x)
        i += 1
    if not scripts:
        if not noms:
            ctx.err("Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...\n")
            return 1
        scripts.append(noms.pop(0))
    try:
        prog = Programme("\n".join(scripts), etendue)
    except ErreurSed as e:
        ctx.err(f"sed: {e}\n" if str(e).startswith("-e") else f"sed: -e expression #1, char {len(scripts[0])}: {e}\n")
        return 1
    if sur_place and not noms:
        ctx.err("sed: no input files\n")
        return 1

    def lire(f):
        try:
            return ctx.vfs.lire(ctx.chemin(f)).decode("utf-8", "surrogateescape")
        except ErreurFs:
            return ""

    def ecrire(f, t):
        try:
            ctx.vfs.ecrire(ctx.chemin(f), t.encode("utf-8", "surrogateescape"), ajout=True)
        except ErreurFs:
            pass

    code = 0
    if not sur_place and not separes:
        lignes = []
        fin_nl = True
        for f in noms or ["-"]:
            if f == "-":
                d = ctx.entree.tout()
            else:
                vp = ctx.chemin(f)
                try:
                    if ctx.vfs.est_dossier(vp):
                        ctx.err(f"sed: couldn't edit {f}: not a regular file\n" if False else
                                f"sed: read error on {f}: Is a directory\n")
                        code = 4
                        continue
                    d = ctx.vfs.lire(vp)
                except ErreurFs as e:
                    ctx.err(f"sed: can't read {f}: {e.texte}\n")
                    code = 2
                    continue
            t = d.decode("utf-8", "surrogateescape")
            if not t:
                continue
            fin_nl = t.endswith("\n")
            lignes += t[:-1].split("\n") if fin_nl else t.split("\n")
        morceaux = []
        try:
            q, _ = executer(prog, lignes, silencieux, morceaux.append, lire, ecrire)
        except ErreurSed as e:
            ctx.err(f"sed: {e}\n")
            return 1
        sortie = "".join(morceaux)
        if not fin_nl and sortie.endswith("\n"):
            sortie = sortie[:-1]
        ctx.out(sortie.encode("utf-8", "surrogateescape"))
        return q or code
    for f in noms or ["-"]:
        vp = ctx.chemin(f)
        try:
            if not ctx.vfs.existe(vp):
                raise ErreurFs(2)
            if ctx.vfs.est_dossier(vp):
                ctx.err(f"sed: couldn't edit {f}: not a regular file\n")
                code = 4
                continue
            d = ctx.vfs.lire(vp)
        except ErreurFs as e:
            ctx.err(f"sed: can't read {f}: {e.texte}\n")
            code = 2
            continue
        t = d.decode("utf-8", "surrogateescape")
        fin_nl = t.endswith("\n")
        lignes = (t[:-1].split("\n") if fin_nl else t.split("\n")) if t else []
        morceaux = []
        for c in prog.cmds:
            c.etat_plage = False
        try:
            q, _ = executer(prog, lignes, silencieux, morceaux.append, lire, ecrire)
        except ErreurSed as e:
            ctx.err(f"sed: {e}\n")
            return 1
        sortie = "".join(morceaux)
        if not fin_nl and sortie.endswith("\n"):
            sortie = sortie[:-1]
        if sur_place:
            try:
                if suffixe:
                    nom_s = suffixe.replace("*", f.rsplit("/", 1)[-1]) if "*" in suffixe else f + suffixe
                    ctx.vfs.ecrire(ctx.chemin(nom_s), d)
                ctx.vfs.ecrire(vp, sortie.encode("utf-8", "surrogateescape"))
            except ErreurFs as e:
                ctx.err(f"sed: couldn't open temporary file {guillemets(f)}: {e.texte}\n")
                code = 4
        else:
            ctx.out(sortie.encode("utf-8", "surrogateescape"))
        if q:
            return q
    return code
