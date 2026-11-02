"""Le terminal du jeu : les commandes de texte (grep, sed, sort, uniq, cut, tr, paste, diff, comm, cmp, fold,
column, expand), comme GNU avec LC_ALL=C (tri par octets, messages en anglais)."""
import functools
import re

from .outils import (Options, erreur_option, guillemets, lignes_de, lire_entree_ou_fichier, option_inconnue, outil,
                     verifier_lettres)
from .vfs import ErreurFs

# ---------------------------------------------------------------- expressions régulières POSIX → Python
_CLASSES_POSIX = {"alpha": "a-zA-Z", "digit": "0-9", "alnum": "a-zA-Z0-9", "upper": "A-Z", "lower": "a-z",
                  "space": r" \t\n\r\f\v", "blank": r" \t", "punct": r"!-/:-@\[-`{-~", "xdigit": "0-9A-Fa-f",
                  "cntrl": r"\x00-\x1f\x7f", "print": r"\x20-\x7e", "graph": r"\x21-\x7e", "word": r"\w"}


def _crochets(p, i):
    """[…] qui commence en p[i] : (classe Python, indice après)."""
    j = i + 1
    neg = False
    if j < len(p) and p[j] == "^":
        neg = True
        j += 1
    out = []
    premier = True
    while j < len(p):
        c = p[j]
        if c == "]" and not premier:
            return "[" + ("^" if neg else "") + "".join(out) + "]", j + 1
        premier = False
        if c == "[" and p[j + 1:j + 2] == ":":
            k = p.find(":]", j + 2)
            if k >= 0:
                out.append(_CLASSES_POSIX.get(p[j + 2:k], ""))
                j = k + 2
                continue
        if c == "[" and p[j + 1:j + 2] in ".=":
            k = p.find(p[j + 1] + "]", j + 2)
            if k >= 0:
                out.append(re.escape(p[j + 2:k]))
                j = k + 2
                continue
        if c in "\\[^":
            out.append("\\" + c)
        elif c == "-" and (j + 1 < len(p) and p[j + 1] == "]" or not out):
            out.append("\\-")
        else:
            out.append(c)
        j += 1
    raise re.error("Unmatched [, [^, [:, [., or [=")


def regex_posix(p, etendue=False):
    """Une expression régulière de grep / sed (BRE, ou ERE avec -E) → Python."""
    out = []
    i = 0
    n = len(p)
    debut = True
    while i < n:
        c = p[i]
        if c == "[":
            cls, i = _crochets(p, i)
            out.append(cls)
            debut = False
            continue
        if c == "\\" and i + 1 < n:
            d = p[i + 1]
            i += 2
            if not etendue and d in "(){}|+?":
                out.append(d)
                debut = d in "(|"
                continue
            if d == "<":
                out.append(r"\b(?=\w)")
            elif d == ">":
                out.append(r"\b(?<=\w)")
            elif d in "wWsSbB" or d.isdigit():
                out.append("\\" + d)
            elif d == "n":
                out.append("\n")
            elif d == "t":
                out.append("\t")
            else:
                out.append(re.escape(d))
            debut = False
            continue
        if not etendue:
            if c in "(){}|+?":
                out.append("\\" + c)
                debut = False
                i += 1
                continue
            if c == "*" and debut:
                out.append(r"\*")
                i += 1
                debut = False
                continue
        else:
            if c == "{" and not re.match(r"\{\d*(,\d*)?\}", p[i:]):
                out.append(r"\{")
                i += 1
                continue
            if c in "*+?" and debut:
                out.append("\\" + c)
                i += 1
                continue
        if c == "^":
            out.append("^" if debut or (out and out[-1] in ("(", "|")) or etendue else r"\^")
            i += 1
            continue
        if c == "$":
            fin = i + 1 >= n or (not etendue and p[i + 1:i + 3] in (r"\)", r"\|")) or (etendue and p[i + 1] in ")|")
            out.append("$" if fin or etendue else r"\$")
            i += 1
            continue
        if c in ".*" or c.isalnum() or c in "()|+?{}":
            out.append(c)
        else:
            out.append(re.escape(c))
        debut = c in "(|" and etendue
        i += 1
    return "".join(out)


def compiler(p, etendue=False, fixe=False, casse=False, mot=False, ligne=False):
    rx = re.escape(p) if fixe else regex_posix(p, etendue)
    if mot:
        rx = r"(?<!\w)(?:" + rx + r")(?!\w)"
    if ligne:
        rx = r"^(?:" + rx + r")$"
    return re.compile(rx, re.I if casse else 0)


# ---------------------------------------------------------------- grep
AIDE_GREP = """Usage: grep [OPTION]... PATTERNS [FILE]...
Search for PATTERNS in each FILE.
Example: grep -i 'hello world' menu.h main.c
PATTERNS can contain multiple patterns separated by newlines.

Pattern selection and interpretation:
  -E, --extended-regexp     PATTERNS are extended regular expressions
  -F, --fixed-strings       PATTERNS are strings
  -G, --basic-regexp        PATTERNS are basic regular expressions
  -P, --perl-regexp         PATTERNS are Perl regular expressions
  -e, --regexp=PATTERNS     use PATTERNS for matching
  -f, --file=FILE           take PATTERNS from FILE
  -i, --ignore-case         ignore case distinctions in patterns and data
      --no-ignore-case      do not ignore case distinctions (default)
  -w, --word-regexp         match only whole words
  -x, --line-regexp         match only whole lines
  -z, --null-data           a data line ends in 0 byte, not newline

Miscellaneous:
  -s, --no-messages         suppress error messages
  -v, --invert-match        select non-matching lines
  -V, --version             display version information and exit
      --help                display this help text and exit

Output control:
  -m, --max-count=NUM       stop after NUM selected lines
  -b, --byte-offset         print the byte offset with output lines
  -n, --line-number         print line number with output lines
      --line-buffered       flush output on every line
  -H, --with-filename       print file name with output lines
  -h, --no-filename         suppress the file name prefix on output
      --label=LABEL         use LABEL as the standard input file name prefix
  -o, --only-matching       show only nonempty parts of lines that match
  -q, --quiet, --silent     suppress all normal output
      --binary-files=TYPE   assume that binary files are TYPE;
                            TYPE is 'binary', 'text', or 'without-match'
  -a, --text                equivalent to --binary-files=text
  -I                        equivalent to --binary-files=without-match
  -d, --directories=ACTION  how to handle directories;
                            ACTION is 'read', 'recurse', or 'skip'
  -D, --devices=ACTION      how to handle devices, FIFOs and sockets;
                            ACTION is 'read' or 'skip'
  -r, --recursive           like --directories=recurse
  -R, --dereference-recursive  likewise, but follow all symlinks
      --include=GLOB        search only files that match GLOB (a file pattern)
      --exclude=GLOB        skip files that match GLOB
      --exclude-from=FILE   skip files that match any file pattern from FILE
      --exclude-dir=GLOB    skip directories that match GLOB
  -L, --files-without-match  print only names of FILEs with no selected lines
  -l, --files-with-matches  print only names of FILEs with selected lines
  -c, --count               print only a count of selected lines per FILE
  -T, --initial-tab         make tabs line up (if needed)
  -Z, --null                print 0 byte after FILE name

Context control:
  -B, --before-context=NUM  print NUM lines of leading context
  -A, --after-context=NUM   print NUM lines of trailing context
  -C, --context=NUM         print NUM lines of output context
  -NUM                      same as --context=NUM
      --group-separator=SEP  print SEP on line between matches with context
      --no-group-separator  do not print separator for matches with context
      --color[=WHEN],
      --colour[=WHEN]       use markers to highlight the matching strings;
                            WHEN is 'always', 'never', or 'auto'
  -U, --binary              do not strip CR characters at EOL (MSDOS/Windows)

When FILE is '-', read standard input.  With no FILE, read '.' if
recursive, '-' otherwise.  With fewer than two FILEs, assume -h.
Exit status is 0 if any line is selected, 1 otherwise;
if any error occurs and -q is not given, the exit status is 2.

Report bugs to: bug-grep@gnu.org
GNU grep home page: <https://www.gnu.org/software/grep/>
General help using GNU software: <https://www.gnu.org/gethelp/>
"""

ROUGE_GREP = "\033[01;31m\033[K"
VIOLET_GREP = "\033[35m\033[K"
BLEU_GREP = "\033[36m\033[K"
VERT_GREP = "\033[32m\033[K"
FIN_GREP = "\033[m\033[K"


@outil("grep", "egrep", "fgrep")
def grep(ctx):
    a = list(ctx.args[1:])
    if ctx.args[0] == "egrep":
        a = ["-E"] + a
    elif ctx.args[0] == "fgrep":
        a = ["-F"] + a
    o = Options(a, avec_valeur="efmABCd", chiffre="C",
                longues=("extended-regexp", "fixed-strings", "basic-regexp", "ignore-case", "word-regexp",
                         "line-regexp", "no-messages", "invert-match", "version", "help", "byte-offset",
                         "line-number", "with-filename", "no-filename", "only-matching", "quiet", "silent", "text",
                         "recursive", "dereference-recursive", "files-without-match", "files-with-matches", "count",
                         "null", "color", "colour", "perl-regexp", "no-group-separator"),
                longues_valeur=("regexp", "file", "max-count", "after-context", "before-context", "context",
                                "include", "exclude", "exclude-dir", "color=", "colour=", "directories", "label"))
    if o.erreur:
        if o.erreur[1].startswith(("--color", "--colour")):
            pass
        else:
            return erreur_option(ctx, "grep", o)
    if o.a("--help"):
        ctx.out(AIDE_GREP)
        return 0
    r = verifier_lettres(ctx, "grep", o, "EFGPiywxsvVbnHhoqarRLlcZzTUIefmABCd")
    if r is not None:
        return r
    motifs = o.toutes("e", "--regexp")
    for f in o.toutes("f", "--file"):
        d = lire_entree_ou_fichier(ctx, "grep", f)
        if d is None:
            return 2
        motifs += d.decode("utf-8", "replace").split("\n")[:-1] if d.endswith(b"\n") else \
            d.decode("utf-8", "replace").split("\n")
    noms = list(o.reste)
    if not motifs:
        if not noms:
            ctx.err("Usage: grep [OPTION]... PATTERNS [FILE]...\nTry 'grep --help' for more information.\n")
            return 2
        motifs = noms.pop(0).split("\n")
    etendue = o.a("E", "--extended-regexp", "P", "--perl-regexp")
    fixe = o.a("F", "--fixed-strings")
    casse = o.a("i", "y", "--ignore-case")
    try:
        rxs = [compiler(m, etendue, fixe, casse, o.a("w", "--word-regexp"), o.a("x", "--line-regexp")) for m in motifs]
    except re.error as e:
        msg = str(e)
        if "unterminated character set" in msg or "Unmatched [" in msg:
            ctx.err("grep: Unmatched [, [^, [:, [., or [=\n")
        elif "missing )" in msg:
            ctx.err("grep: Unmatched ( or \\(\n")
        elif "unbalanced parenthesis" in msg:
            ctx.err("grep: Unmatched ) or \\)\n")
        else:
            ctx.err(f"grep: {msg}\n")
        return 2
    inverse = o.a("v", "--invert-match")
    rec = o.a("r", "R", "--recursive", "--dereference-recursive") or o.val("d", "--directories") == "recurse"
    if not noms:
        noms = ["."] if rec else ["-"]
    compte = o.a("c", "--count")
    avec_noms = o.a("l", "--files-with-matches")
    sans_noms = o.a("L", "--files-without-match")
    seul = o.a("o", "--only-matching")
    calme = o.a("q", "--quiet", "--silent")
    numero = o.a("n", "--line-number")
    muet = o.a("s", "--no-messages")
    max_n = o.val("m", "--max-count")
    max_n = int(max_n) if max_n is not None else None
    apres = int(o.val("A", "--after-context", "C", "--context", defaut="0") or 0)
    avant = int(o.val("B", "--before-context", "C", "--context", defaut="0") or 0)
    if o.val("A", "--after-context") is not None:
        apres = int(o.val("A", "--after-context"))
    if o.val("B", "--before-context") is not None:
        avant = int(o.val("B", "--before-context"))
    couleur = ctx.sortie.tty and o.val("--color", "--colour", defaut="auto") != "never" and \
        any(x.startswith(("--color", "--colour")) for x in ctx.args) or (
        ctx.sortie.tty and getattr(ctx.sh, "grep_couleur", True))
    inclure = o.toutes("--include")
    exclure = o.toutes("--exclude")
    exclure_d = o.toutes("--exclude-dir")
    fichiers = []
    code = 1
    erreur = False
    for nm in noms:
        if nm == "-":
            fichiers.append(("-", None))
            continue
        vp = ctx.chemin(nm)
        if not ctx.vfs.existe(vp):
            if not muet:
                ctx.err(f"grep: {nm}: No such file or directory\n")
            erreur = True
            continue
        if ctx.vfs.est_dossier(vp):
            if not rec:
                if not muet:
                    ctx.err(f"grep: {nm}: Is a directory\n")
                erreur = True
                continue
            _parcourir(ctx, vp, nm, fichiers, inclure, exclure, exclure_d)
            continue
        fichiers.append((nm, vp))
    prefixer = (len(noms) > 1 or rec) and not o.a("h", "--no-filename") or o.a("H", "--with-filename")
    if rec and len(noms) == 1 and noms[0] != "." and fichiers == [(noms[0], ctx.chemin(noms[0]))]:
        prefixer = o.a("H")
    from .shell import motif_shell  # noqa: F401
    for nm, vp in fichiers:
        ctx.verifier()
        if nm == "-":
            d = ctx.entree.tout()
            nom_aff = o.val("--label") or "(standard input)"
        else:
            try:
                d = ctx.vfs.lire(vp)
            except ErreurFs as e:
                if not muet:
                    ctx.err(f"grep: {nm}: {e.texte}\n")
                erreur = True
                continue
            nom_aff = nm
        binaire = b"\0" in d[:8192] and not o.a("a", "--text")
        texte = d.decode("utf-8", "surrogateescape")
        lignes = texte.split("\n")
        if texte.endswith("\n"):
            lignes.pop()
        n_trouve = 0
        dernier_imprime = -1
        en_attente_apres = 0
        sorties = []
        for k, l in enumerate(lignes):
            trouve = any(rx.search(l) for rx in rxs)
            if trouve != inverse:
                n_trouve += 1
                code = 0
                if calme:
                    return 0
                if compte or avec_noms or sans_noms or binaire:
                    if max_n is not None and n_trouve >= max_n:
                        break
                    continue
                # le contexte avant
                if avant or apres:
                    debut = max(dernier_imprime + 1, k - avant)
                    if dernier_imprime >= 0 and debut > dernier_imprime + 1:
                        sorties.append("--\n")
                    for j in range(debut, k):
                        sorties.append(_prefixe(prefixer, nom_aff, numero, j + 1, "-", couleur) + lignes[j] + "\n")
                pre = _prefixe(prefixer, nom_aff, numero, k + 1, ":", couleur)
                if seul and not inverse:
                    for rx in rxs:
                        for m in rx.finditer(l):
                            if m.group():
                                sorties.append(pre + (ROUGE_GREP + m.group() + FIN_GREP if couleur else m.group()) + "\n")
                elif couleur and not inverse:
                    sorties.append(pre + _surligner(l, rxs) + "\n")
                else:
                    sorties.append(pre + l + "\n")
                dernier_imprime = k
                en_attente_apres = apres
                if max_n is not None and n_trouve >= max_n:
                    break
            elif en_attente_apres > 0:
                sorties.append(_prefixe(prefixer, nom_aff, numero, k + 1, "-", couleur) + l + "\n")
                dernier_imprime = k
                en_attente_apres -= 1
        if compte:
            ctx.out((_nom_c(nom_aff, couleur) + (BLEU_GREP + ":" + FIN_GREP if couleur else ":") if prefixer else "")
                    + f"{n_trouve}\n")
        elif avec_noms:
            if n_trouve:
                ctx.out(_nom_c(nom_aff, couleur) + "\n")
        elif sans_noms:
            if not n_trouve:
                ctx.out(_nom_c(nom_aff, couleur) + "\n")
        elif binaire and n_trouve:
            ctx.out(f"grep: {nom_aff}: binary file matches\n")
        else:
            ctx.out("".join(sorties))
    if sans_noms:
        code = 0 if code == 1 and fichiers else code
    if erreur and not (calme and code == 0):
        return 2
    return code


def _nom_c(nom, couleur):
    return VIOLET_GREP + nom + FIN_GREP if couleur else nom


def _prefixe(avec_nom, nom, numero, n, sep, couleur):
    s = ""
    if avec_nom:
        s += _nom_c(nom, couleur) + (BLEU_GREP + sep + FIN_GREP if couleur else sep)
    if numero:
        s += (VERT_GREP + str(n) + FIN_GREP + BLEU_GREP + sep + FIN_GREP) if couleur else f"{n}{sep}"
    return s


def _surligner(l, rxs):
    zones = []
    for rx in rxs:
        for m in rx.finditer(l):
            if m.end() > m.start():
                zones.append((m.start(), m.end()))
    zones.sort()
    out, pos = "", 0
    for a, b in zones:
        if a < pos:
            continue
        out += l[pos:a] + ROUGE_GREP + l[a:b] + FIN_GREP
        pos = b
    return out + l[pos:]


def _parcourir(ctx, vp, nm, fichiers, inclure, exclure, exclure_d):
    from .shell import motif_shell
    try:
        noms = sorted(ctx.vfs.lister(vp), key=lambda x: x.encode("utf-8", "surrogateescape"))
    except ErreurFs as e:
        ctx.err(f"grep: {nm}: {e.texte}\n")
        return
    for x in noms:
        sv = vp.rstrip("/") + "/" + x
        sn = (nm.rstrip("/") + "/" + x) if nm != "/" else "/" + x
        if ctx.vfs.est_dossier(sv):
            if any(motif_shell(m, x) for m in exclure_d):
                continue
            _parcourir(ctx, sv, sn, fichiers, inclure, exclure, exclure_d)
        else:
            if inclure and not any(motif_shell(m, x) for m in inclure):
                continue
            if any(motif_shell(m, x) for m in exclure):
                continue
            fichiers.append((sn, sv))


# ---------------------------------------------------------------- sort
def _champs_blancs(l):
    """Les champs de sort sans -t : chaque champ garde les blancs qui le précèdent."""
    out = []
    i = 0
    n = len(l)
    while i < n:
        j = i
        while j < n and l[j] in " \t":
            j += 1
        while j < n and l[j] not in " \t":
            j += 1
        out.append((i, j))
        i = j
    return out


def _cle(l, k, sep):
    """La partie de la ligne pour une clé -k debut[.c][opts][,fin[.c][opts]]."""
    (f1, c1, opt1), fin = k
    if sep is None:
        pos = _champs_blancs(l)
    else:
        pos = []
        i = 0
        for morceau in l.split(sep):
            pos.append((i, i + len(morceau)))
            i += len(morceau) + 1
    if f1 - 1 >= len(pos):
        return ""
    debut = pos[f1 - 1][0]
    if sep is None and "b" in opt1:
        while debut < len(l) and l[debut] in " \t":
            debut += 1
    if c1:
        base = pos[f1 - 1][0]
        if sep is None:
            while base < len(l) and l[base] in " \t" and "b" in opt1:
                base += 1
        debut = min(len(l), base + c1 - 1)
    if fin is None:
        return l[debut:]
    f2, c2, _opt2 = fin
    if f2 - 1 >= len(pos):
        return l[debut:]
    if c2:
        a = pos[f2 - 1][0]
        if sep is None:
            while a < len(l) and l[a] in " \t":
                a += 1
        f = min(len(l), a + c2)
    else:
        f = pos[f2 - 1][1]
    return l[debut:f]


def _num(s):
    m = re.match(r"\s*([-+]?)(\d*)(\.\d*)?", s)
    if not m or not (m.group(2) or (m.group(3) and len(m.group(3)) > 1)):
        return 0.0
    try:
        v = float((m.group(2) or "0") + (m.group(3) or ""))
    except ValueError:
        return 0.0
    return -v if m.group(1) == "-" else v


def _humain_num(s):
    m = re.match(r"\s*([-+]?\d*\.?\d+)([KMGTPE]?)", s)
    if not m:
        return 0.0
    return float(m.group(1)) * (1024 ** ("KMGTPE".index(m.group(2)) + 1) if m.group(2) else 1)


def _version_cle(s):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]


@outil("sort")
def sort(ctx):
    o = Options(ctx.args[1:], avec_valeur="ktoS", longues=("numeric-sort", "reverse", "unique", "ignore-case",
                                                            "human-numeric-sort", "version-sort", "stable", "help",
                                                            "general-numeric-sort", "random-sort", "check"),
                longues_valeur=("key", "field-separator", "output"))
    if o.erreur:
        return erreur_option(ctx, "sort", o)
    r = verifier_lettres(ctx, "sort", o, "nrufhVsgktobdcSRMzm")
    if r is not None:
        return r
    sep = o.val("t", "--field-separator")
    if sep is not None and len(sep) != 1:
        if sep == "\\t":
            sep = "\t"
        elif sep == "\\0":
            sep = "\0"
        else:
            ctx.err(f"sort: multi-character tab {guillemets(sep)}\n")
            return 2
    cles = []
    for kv in o.toutes("k", "--key"):
        m = re.fullmatch(r"(\d+)(?:\.(\d+))?([bdfgiMhnRrV]*)(?:,(\d+)(?:\.(\d+))?([bdfgiMhnRrV]*))?", kv)
        if not m or int(m.group(1)) == 0:
            ctx.err(f"sort: invalid number at field start: invalid count at start of {guillemets(kv)}\n")
            return 2
        fin = (int(m.group(4)), int(m.group(5) or 0), m.group(6) or "") if m.group(4) else None
        cles.append(((int(m.group(1)), int(m.group(2) or 0), m.group(3) or ""), fin))
    glob_n = o.a("n", "--numeric-sort", "g", "--general-numeric-sort")
    glob_h = o.a("h", "--human-numeric-sort")
    glob_v = o.a("V", "--version-sort")
    glob_f = o.a("f", "--ignore-case")
    glob_r = o.a("r", "--reverse")
    glob_b = o.a("b")
    unique = o.a("u", "--unique")
    stable = o.a("s", "--stable")
    donnees = b""
    noms = o.reste or ["-"]
    for f in noms:
        d = lire_entree_ou_fichier(ctx, "sort", f)
        if d is None:
            return 2
        if d and not d.endswith(b"\n"):
            d += b"\n"
        donnees += d
    lignes = [x.decode("utf-8", "surrogateescape") for x in lignes_de(donnees)]

    def opts_de(cle):
        o1 = cle[0][2] + (cle[1][2] if cle[1] else "")
        if not o1:
            return glob_n, glob_h, glob_v, glob_f, glob_r, glob_b
        return "n" in o1 or "g" in o1, "h" in o1, "V" in o1, "f" in o1, "r" in o1, "b" in o1

    def compare_val(a, b, n, h, v, f, bb):
        if n:
            x, y = _num(a), _num(b)
            return (x > y) - (x < y)
        if h:
            x, y = _humain_num(a), _humain_num(b)
            return (x > y) - (x < y)
        if v:
            x, y = _version_cle(a), _version_cle(b)
            try:
                return (x > y) - (x < y)
            except TypeError:
                pass
        if bb:
            a, b = a.lstrip(" \t"), b.lstrip(" \t")
        if f:
            a, b = a.upper(), b.upper()
        x, y = a.encode("utf-8", "surrogateescape"), b.encode("utf-8", "surrogateescape")
        return (x > y) - (x < y)

    def comparer(a, b):
        if cles:
            for k in cles:
                n, h, v, f, rr, bb = opts_de(k)
                c = compare_val(_cle(a, k, sep), _cle(b, k, sep), n, h, v, f, bb)
                if c:
                    return -c if rr else c
        else:
            c = compare_val(a, b, glob_n, glob_h, glob_v, glob_f, glob_b)
            if c:
                return -c if glob_r else c
        if stable or unique:
            return 0
        x, y = a.encode("utf-8", "surrogateescape"), b.encode("utf-8", "surrogateescape")
        c = (x > y) - (x < y)
        return -c if glob_r else c

    if o.a("c", "--check"):
        for k in range(1, len(lignes)):
            if comparer(lignes[k - 1], lignes[k]) > 0:
                ctx.err(f"sort: {noms[0] if noms[0] != '-' else '-'}:{k + 1}: disorder: {lignes[k]}\n")
                return 1
        return 0
    tri = sorted(lignes, key=functools.cmp_to_key(comparer))
    if unique:
        res = []
        for l in tri:
            if not res or comparer(res[-1], l) != 0:
                res.append(l)
        tri = res
    sortie = "".join(l + "\n" for l in tri)
    dest = o.val("o", "--output")
    if dest:
        try:
            ctx.vfs.ecrire(ctx.chemin(dest), sortie.encode("utf-8", "surrogateescape"))
        except ErreurFs as e:
            ctx.err(f"sort: open failed: {dest}: {e.texte}\n")
            return 2
        return 0
    ctx.out(sortie)
    return 0


# ---------------------------------------------------------------- uniq
@outil("uniq")
def uniq(ctx):
    o = Options(ctx.args[1:], avec_valeur="fsw", longues=("count", "repeated", "unique", "ignore-case", "help"))
    if o.erreur:
        return erreur_option(ctx, "uniq", o)
    r = verifier_lettres(ctx, "uniq", o, "cduifswD")
    if r is not None:
        return r
    entree = o.reste[0] if o.reste else "-"
    d = lire_entree_ou_fichier(ctx, "uniq", entree)
    if d is None:
        return 1
    lignes = lignes_de(d)
    casse = o.a("i", "--ignore-case")
    sauter = int(o.val("f", defaut="0") or 0)
    sauter_c = int(o.val("s", defaut="0") or 0)

    def cle(l):
        t = l
        if sauter:
            t = b"".join(t.split(None, sauter)[sauter:]) if len(t.split()) > sauter else b""
        t = t[sauter_c:]
        return t.lower() if casse else t
    groupes = []
    for l in lignes:
        if groupes and cle(groupes[-1][0]) == cle(l):
            groupes[-1][1] += 1
        else:
            groupes.append([l, 1])
    out = []
    for l, n in groupes:
        if o.a("d", "--repeated") and n < 2:
            continue
        if o.a("u", "--unique") and n > 1:
            continue
        out.append((f"{n:7d} ".encode() if o.a("c", "--count") else b"") + l + b"\n")
    res = b"".join(out)
    if len(o.reste) > 1:
        try:
            ctx.vfs.ecrire(ctx.chemin(o.reste[1]), res)
        except ErreurFs as e:
            ctx.err(f"uniq: {o.reste[1]}: {e.texte}\n")
            return 1
        return 0
    ctx.out(res)
    return 0


# ---------------------------------------------------------------- cut
def _liste_plages(s):
    out = []
    for part in s.split(","):
        m = re.fullmatch(r"(\d*)-(\d*)|(\d+)", part)
        if not m:
            return None
        if m.group(3):
            n = int(m.group(3))
            if n == 0:
                return None
            out.append((n, n))
        else:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else None
            if a == 0 or (not m.group(1) and not m.group(2)):
                return None
            out.append((a, b))
    return out


def _dans(n, plages):
    return any(a <= n and (b is None or n <= b) for a, b in plages)


@outil("cut")
def cut(ctx):
    o = Options(ctx.args[1:], avec_valeur="dfcb", longues=("complement", "only-delimited", "help"),
                longues_valeur=("delimiter", "fields", "characters", "bytes", "output-delimiter"))
    if o.erreur:
        return erreur_option(ctx, "cut", o)
    r = verifier_lettres(ctx, "cut", o, "dfcbsnz")
    if r is not None:
        return r
    champs = o.val("f", "--fields")
    cars = o.val("c", "--characters") or o.val("b", "--bytes")
    if not champs and not cars:
        ctx.err("cut: you must specify a list of bytes, characters, or fields\nTry 'cut --help' for more information.\n")
        return 1
    plages = _liste_plages(champs or cars)
    if plages is None:
        ctx.err(f"cut: invalid field value {guillemets(champs or cars)}\nTry 'cut --help' for more information.\n" if
                "0" not in (champs or cars) else
                "cut: fields and positions are numbered from 1\nTry 'cut --help' for more information.\n")
        return 1
    sep = o.val("d", "--delimiter", defaut="\t")
    if champs and len(sep.encode()) != 1:
        ctx.err("cut: the delimiter must be a single character\nTry 'cut --help' for more information.\n")
        return 1
    sep_sortie = o.val("--output-delimiter", defaut=sep)
    complement = o.a("--complement")
    code = 0
    for f in o.reste or ["-"]:
        d = lire_entree_ou_fichier(ctx, "cut", f)
        if d is None:
            code = 1
            continue
        for l in lignes_de(d):
            if cars:
                bits = l if o.val("b", "--bytes") else l.decode("utf-8", "surrogateescape")
                garde = [c for k, c in enumerate(bits, 1) if _dans(k, plages) != complement]
                res = (b"".join(bytes([x]) for x in garde) if isinstance(bits, bytes) else
                       "".join(garde).encode("utf-8", "surrogateescape"))
                ctx.out(res + b"\n")
                continue
            t = l.decode("utf-8", "surrogateescape")
            if sep not in t:
                if not o.a("s", "--only-delimited"):
                    ctx.out(l + b"\n")
                continue
            morceaux = t.split(sep)
            garde = [m for k, m in enumerate(morceaux, 1) if _dans(k, plages) != complement]
            ctx.out(sep_sortie.join(garde).encode("utf-8", "surrogateescape") + b"\n")
    return code


# ---------------------------------------------------------------- tr
def _ensemble_tr(s):
    """Un ensemble de tr → liste d'octets (a-z, \\n, [:upper:], [x*n])."""
    out = []
    b = s.encode("utf-8", "surrogateescape")
    i = 0
    while i < len(b):
        c = b[i]
        if c == 0x5c and i + 1 < len(b):           # \
            d = chr(b[i + 1])
            if d in "nrtvfab\\":
                out.append(ord({"n": "\n", "r": "\r", "t": "\t", "v": "\v", "f": "\f", "a": "\a", "b": "\b",
                                "\\": "\\"}[d]))
                i += 2
                continue
            m = re.match(rb"[0-7]{1,3}", b[i + 1:])
            if m:
                out.append(int(m.group(), 8) & 0xff)
                i += 1 + m.end()
                continue
            out.append(b[i + 1])
            i += 2
            continue
        if c == 0x5b and b[i + 1:i + 2] == b":":     # [:classe:]
            k = b.find(b":]", i + 2)
            if k >= 0:
                nom = b[i + 2:k].decode()
                cl = {"upper": range(65, 91), "lower": range(97, 123), "digit": range(48, 58),
                      "alpha": list(range(65, 91)) + list(range(97, 123)),
                      "alnum": list(range(48, 58)) + list(range(65, 91)) + list(range(97, 123)),
                      "space": [9, 10, 11, 12, 13, 32], "blank": [9, 32],
                      "punct": [x for x in range(33, 127) if not chr(x).isalnum()],
                      "xdigit": list(range(48, 58)) + list(range(65, 71)) + list(range(97, 103)),
                      "cntrl": list(range(0, 32)) + [127], "print": range(32, 127), "graph": range(33, 127)}.get(nom)
                if cl is not None:
                    out.extend(cl)
                    i = k + 2
                    continue
        if c == 0x5b and re.match(rb"\[.\*(\d*)\]", b[i:]):      # [x*n]
            m = re.match(rb"\[(.)\*(\d*)\]", b[i:])
            out.append(("rep", m.group(1)[0], int(m.group(2) or 0)))
            i += m.end()
            continue
        if i + 2 < len(b) and b[i + 1] == 0x2d:      # a-z
            fin = b[i + 2]
            if fin == 0x5c and i + 3 < len(b):
                fin = b[i + 3]
                i += 1
            if fin < c:
                raise ValueError(f"range-endpoints of '{chr(c)}-{chr(fin)}' are in reverse collating sequence order")
            out.extend(range(c, fin + 1))
            i += 3
            continue
        out.append(c)
        i += 1
    return out


@outil("tr")
def tr(ctx):
    a = ctx.args[1:]
    supp = serrer = compl = False
    while a and a[0].startswith("-") and len(a[0]) > 1 and a[0] != "--":
        for f in a[0][1:]:
            if f == "d":
                supp = True
            elif f == "s":
                serrer = True
            elif f in "cC":
                compl = True
            else:
                return option_inconnue(ctx, "tr", f)
        a = a[1:]
    if a and a[0] == "--":
        a = a[1:]
    if not a:
        ctx.err("tr: missing operand\nTry 'tr --help' for more information.\n")
        return 1
    if not supp and not serrer and len(a) < 2:
        ctx.err(f"tr: missing operand after {guillemets(a[0])}\nTwo strings must be given when translating.\n"
                "Try 'tr --help' for more information.\n")
        return 1
    if len(a) > (2 if not supp or serrer else 1):
        ctx.err(f"tr: extra operand {guillemets(a[2 if not supp or serrer else 1])}\nTry 'tr --help' for more information.\n")
        return 1
    try:
        e1 = [x for x in _ensemble_tr(a[0]) if not isinstance(x, tuple)]
        e2 = _ensemble_tr(a[1]) if len(a) > 1 else []
    except ValueError as e:
        ctx.err(f"tr: {e}\n")
        return 1
    if compl:
        e1 = [x for x in range(256) if x not in set(e1)]
    # les [x*] de l'ensemble 2 remplissent la longueur de l'ensemble 1
    e2b = []
    for x in e2:
        if isinstance(x, tuple):
            n = x[2] or max(0, len(e1) - (len(e2) - 1))
            e2b.extend([x[1]] * n)
        else:
            e2b.append(x)
    e2 = e2b
    d = ctx.entree.tout()
    if supp:
        s1 = set(e1)
        d = bytes(x for x in d if x not in s1)
        if serrer and e2:
            s2 = set(e2)
            out = bytearray()
            for x in d:
                if out and x in s2 and out[-1] == x:
                    continue
                out.append(x)
            d = bytes(out)
        ctx.out(d)
        return 0
    if len(e2) > 0:
        if len(e2) < len(e1):
            e2 = e2 + [e2[-1]] * (len(e1) - len(e2))
        table = list(range(256))
        for x, y in zip(e1, e2):
            table[x] = y
        d = d.translate(bytes(table))
        cible = set(e2[:len(e1)]) if not compl else set(e2)
    else:
        cible = set(e1)
    if serrer:
        out = bytearray()
        for x in d:
            if out and x in cible and out[-1] == x:
                continue
            out.append(x)
        d = bytes(out)
    ctx.out(d)
    return 0


# ---------------------------------------------------------------- paste
@outil("paste")
def paste(ctx):
    o = Options(ctx.args[1:], avec_valeur="d", longues=("serial", "help"), longues_valeur=("delimiters",))
    if o.erreur:
        return erreur_option(ctx, "paste", o)
    seps = o.val("d", "--delimiters", defaut="\t")
    seps = seps.replace("\\n", "\n").replace("\\t", "\t").replace("\\0", "") or ""
    noms = o.reste or ["-"]
    contenus = []
    entree_lignes = None
    for f in noms:
        if f == "-":
            if entree_lignes is None:
                entree_lignes = [x.decode("utf-8", "surrogateescape") for x in lignes_de(ctx.entree.tout())]
            contenus.append(("-", None))
            continue
        d = lire_entree_ou_fichier(ctx, "paste", f)
        if d is None:
            return 1
        contenus.append((f, [x.decode("utf-8", "surrogateescape") for x in lignes_de(d)]))
    nb_tirets = sum(1 for f, _ in contenus if f == "-")
    if nb_tirets:
        # plusieurs « - » lisent l'entrée à tour de rôle
        colonnes_t = [[] for _ in range(nb_tirets)]
        for k, l in enumerate(entree_lignes or []):
            colonnes_t[k % nb_tirets].append(l)
        it = iter(colonnes_t)
        contenus = [(f, c if c is not None else next(it)) for f, c in contenus]
    cols = [c for _f, c in contenus]

    def sep(k):
        return seps[k % len(seps)] if seps else ""
    if o.a("s", "--serial"):
        for c in cols:
            ctx.out("".join(x + (sep(k) if k < len(c) - 1 else "") for k, x in enumerate(c)) + "\n")
        return 0
    n = max([len(c) for c in cols] or [0])
    for i in range(n):
        ligne = ""
        for k, c in enumerate(cols):
            ligne += c[i] if i < len(c) else ""
            if k < len(cols) - 1:
                ligne += sep(k)
        ctx.out(ligne.encode("utf-8", "surrogateescape") + b"\n")
    return 0


# ---------------------------------------------------------------- diff
def lcs_paires(a, b):
    """Les paires (i, j) de lignes communes, en cherchant le plus long sous-ensemble commun (comme diff)."""
    import difflib
    n, m = len(a), len(b)
    # les débuts et fins communs d'abord (comme GNU diff)
    d = 0
    while d < n and d < m and a[d] == b[d]:
        d += 1
    f = 0
    while f < n - d and f < m - d and a[n - 1 - f] == b[m - 1 - f]:
        f += 1
    paires = [(i, i) for i in range(d)]
    aa, bb = a[d:n - f], b[d:m - f]
    if aa and bb:
        if len(aa) * len(bb) <= 4_000_000:
            # vraie plus longue sous-suite commune (programmation dynamique), départage comme GNU (Myers) :
            # on garde les suppressions avant les ajouts
            L = [[0] * (len(bb) + 1) for _ in range(len(aa) + 1)]
            for i in range(len(aa) - 1, -1, -1):
                Li, Li1 = L[i], L[i + 1]
                ai = aa[i]
                for j in range(len(bb) - 1, -1, -1):
                    Li[j] = Li1[j + 1] + 1 if ai == bb[j] else (Li1[j] if Li1[j] >= Li[j + 1] else Li[j + 1])
            i = j = 0
            while i < len(aa) and j < len(bb):
                if aa[i] == bb[j]:
                    paires.append((d + i, d + j))
                    i += 1
                    j += 1
                elif L[i + 1][j] >= L[i][j + 1]:
                    i += 1
                else:
                    j += 1
        else:
            sm = difflib.SequenceMatcher(None, aa, bb, autojunk=False)
            for blk in sm.get_matching_blocks():
                for k in range(blk.size):
                    paires.append((d + blk.a + k, d + blk.b + k))
    paires += [(n - f + k, m - f + k) for k in range(f)]
    return paires


def blocs_diff(a, b):
    """Les changements : [(a1, a2, b1, b2)] (lignes a[a1:a2] remplacées par b[b1:b2])."""
    paires = lcs_paires(a, b) + [(len(a), len(b))]
    out = []
    i = j = 0
    for pi, pj in paires:
        if pi > i or pj > j:
            out.append((i, pi, j, pj))
        i, j = pi + 1, pj + 1
    return out


def _plage(a, b):
    """Numéros de lignes de diff (1-based) : « 3 » ou « 3,5 »."""
    if b - a <= 1:
        return str(a + 1 if b > a else a)
    return f"{a + 1},{b}"


@outil("diff")
def diff(ctx):
    o = Options(ctx.args[1:], avec_valeur="U", longues=("unified", "brief", "report-identical-files", "ignore-case",
                                                       "side-by-side", "recursive", "help", "ignore-all-space",
                                                       "text", "color", "new-file", "ignore-blank-lines"),
                longues_valeur=("color=",), chiffre=None)
    if o.erreur:
        return erreur_option(ctx, "diff", o)
    noms = o.reste
    if len(noms) < 2:
        ctx.err(f"diff: missing operand after {guillemets(noms[0])}\n" if noms else "diff: missing operand\n")
        ctx.err("diff: Try 'diff --help' for more information.\n")
        return 2
    if len(noms) > 2:
        ctx.err(f"diff: extra operand {guillemets(noms[2])}\ndiff: Try 'diff --help' for more information.\n")
        return 2
    f1, f2 = noms
    v1, v2 = ctx.chemin(f1) if f1 != "-" else None, ctx.chemin(f2) if f2 != "-" else None
    if v1 and ctx.vfs.est_dossier(v1) and v2 and not ctx.vfs.est_dossier(v2):
        v1 = v1.rstrip("/") + "/" + f2.rsplit("/", 1)[-1]
        f1 = f1.rstrip("/") + "/" + f2.rsplit("/", 1)[-1]
    elif v2 and ctx.vfs.est_dossier(v2) and v1 and not ctx.vfs.est_dossier(v1):
        v2 = v2.rstrip("/") + "/" + f1.rsplit("/", 1)[-1]
        f2 = f2.rstrip("/") + "/" + f1.rsplit("/", 1)[-1]
    contenus = []
    for f, vp in ((f1, v1), (f2, v2)):
        if f == "-":
            contenus.append(ctx.entree.tout())
            continue
        if vp.startswith("/dev/fd/"):
            try:
                contenus.append(ctx.vfs.lire(vp))
            except ErreurFs:
                contenus.append(b"")
            continue
        if not ctx.vfs.existe(vp):
            ctx.err(f"diff: {f}: No such file or directory\n")
            return 2
        if ctx.vfs.est_dossier(vp):
            return _diff_dossiers(ctx, v1, v2, f1, f2, o)
        try:
            contenus.append(ctx.vfs.lire(vp))
        except ErreurFs as e:
            ctx.err(f"diff: {f}: {e.texte}\n")
            return 2
    return diff_textes(ctx, contenus[0], contenus[1], f1, f2, o, v1, v2)


def diff_textes(ctx, d1, d2, f1, f2, o, v1=None, v2=None):
    if d1 == d2:
        if o.a("s", "--report-identical-files"):
            ctx.out(f"Files {f1} and {f2} are identical\n")
        return 0
    if o.a("q", "--brief"):
        ctx.out(f"Files {f1} and {f2} differ\n")
        return 1
    a = d1.decode("utf-8", "surrogateescape").split("\n")
    b = d2.decode("utf-8", "surrogateescape").split("\n")
    fin_a = d1.endswith(b"\n") or not d1
    fin_b = d2.endswith(b"\n") or not d2
    if fin_a:
        a.pop()
    if fin_b:
        b.pop()
    norm = (lambda x: x.lower()) if o.a("i", "--ignore-case") else (lambda x: x)
    if o.a("w", "--ignore-all-space"):
        norm2 = norm
        norm = lambda x: re.sub(r"\s+", "", norm2(x))  # noqa: E731
    ka, kb = [norm(x) for x in a], [norm(x) for x in b]
    # « \ No newline at end of file » : la dernière ligne sans \n n'est pas égale à la même avec \n
    if not fin_a and ka:
        ka[-1] += "\0sans"
    if not fin_b and kb:
        kb[-1] += "\0sans"
    blocs = blocs_diff(ka, kb)
    if not blocs:
        return 0
    if o.a("u", "U", "--unified"):
        ctx_n = int(o.val("U", defaut="3") or 3)
        ctx.out(f"--- {f1}\t{_date_diff(ctx, v1)}\n+++ {f2}\t{_date_diff(ctx, v2)}\n")
        groupes = []
        for blk in blocs:
            if groupes and blk[0] - groupes[-1][-1][1] <= 2 * ctx_n:
                groupes[-1].append(blk)
            else:
                groupes.append([blk])
        for g in groupes:
            a1 = max(0, g[0][0] - ctx_n)
            b1 = max(0, g[0][2] - ctx_n)
            a2 = min(len(a), g[-1][1] + ctx_n)
            b2 = min(len(b), g[-1][3] + ctx_n)
            def u(s, e):
                n = e - s
                if n == 1:
                    return f"{s + 1}"
                if n == 0:
                    return f"{s},0"
                return f"{s + 1},{n}"
            ctx.out(f"@@ -{u(a1, a2)} +{u(b1, b2)} @@\n")
            pos = a1
            for (x1, x2, y1, y2) in g:
                for k in range(pos, x1):
                    ctx.out(" " + a[k] + "\n")
                for k in range(x1, x2):
                    ctx.out("-" + a[k] + "\n")
                    if k == len(a) - 1 and not fin_a:
                        ctx.out("\\ No newline at end of file\n")
                for k in range(y1, y2):
                    ctx.out("+" + b[k] + "\n")
                    if k == len(b) - 1 and not fin_b:
                        ctx.out("\\ No newline at end of file\n")
                pos = x2
            for k in range(pos, a2):
                ctx.out(" " + a[k] + "\n")
        return 1
    for a1, a2, b1, b2 in blocs:
        if a1 == a2:
            ctx.out(f"{a1}a{_plage(b1, b2)}\n")
        elif b1 == b2:
            ctx.out(f"{_plage(a1, a2)}d{b1}\n")
        else:
            ctx.out(f"{_plage(a1, a2)}c{_plage(b1, b2)}\n")
        for k in range(a1, a2):
            ctx.out("< " + a[k] + "\n")
            if k == len(a) - 1 and not fin_a:
                ctx.out("\\ No newline at end of file\n")
        if a1 != a2 and b1 != b2:
            ctx.out("---\n")
        for k in range(b1, b2):
            ctx.out("> " + b[k] + "\n")
            if k == len(b) - 1 and not fin_b:
                ctx.out("\\ No newline at end of file\n")
    return 1


def _date_diff(ctx, vp):
    import datetime
    if not vp:
        return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S.%f000 %z")
    try:
        inf = ctx.vfs.infos(vp)
    except ErreurFs:
        return ""
    return datetime.datetime.fromtimestamp(inf.mtime).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f000 %z")


def _diff_dossiers(ctx, v1, v2, f1, f2, o):
    try:
        n1, n2 = set(ctx.vfs.lister(v1)), set(ctx.vfs.lister(v2))
    except ErreurFs as e:
        ctx.err(f"diff: {e.texte}\n")
        return 2
    code = 0
    for x in sorted(n1 | n2, key=lambda s: s.encode()):
        if x not in n2:
            ctx.out(f"Only in {f1}: {x}\n")
            code = 1
            continue
        if x not in n1:
            ctx.out(f"Only in {f2}: {x}\n")
            code = 1
            continue
        a, b = v1.rstrip("/") + "/" + x, v2.rstrip("/") + "/" + x
        if ctx.vfs.est_dossier(a) and ctx.vfs.est_dossier(b):
            if o.a("r", "--recursive"):
                code = max(code, _diff_dossiers(ctx, a, b, f1.rstrip("/") + "/" + x, f2.rstrip("/") + "/" + x, o))
            else:
                ctx.out(f"Common subdirectories: {f1.rstrip('/')}/{x} and {f2.rstrip('/')}/{x}\n")
            continue
        d1, d2 = ctx.vfs.lire(a), ctx.vfs.lire(b)
        if d1 != d2:
            if o.a("q", "--brief"):
                ctx.out(f"Files {f1.rstrip('/')}/{x} and {f2.rstrip('/')}/{x} differ\n")
            else:
                ctx.out(f"diff {' '.join(ctx.args[1:-2])}{' ' if len(ctx.args) > 3 else ''}{f1.rstrip('/')}/{x} "
                        f"{f2.rstrip('/')}/{x}\n".replace("diff  ", "diff "))
                diff_textes(ctx, d1, d2, f1.rstrip("/") + "/" + x, f2.rstrip("/") + "/" + x, o, a, b)
            code = 1
    return code


# ---------------------------------------------------------------- comm, cmp, fold, expand, column
@outil("comm")
def comm(ctx):
    a = ctx.args[1:]
    cacher = set()
    while a and re.fullmatch(r"-[123]+", a[0]):
        cacher |= set(a[0][1:])
        a = a[1:]
    if len(a) != 2:
        ctx.err("comm: missing operand\nTry 'comm --help' for more information.\n")
        return 1
    d1, d2 = lire_entree_ou_fichier(ctx, "comm", a[0]), lire_entree_ou_fichier(ctx, "comm", a[1])
    if d1 is None or d2 is None:
        return 1
    l1, l2 = lignes_de(d1), lignes_de(d2)
    i = j = 0
    pre = {1: b"", 2: b"\t" if "1" not in cacher else b"",
           3: (b"\t" if "1" not in cacher else b"") + (b"\t" if "2" not in cacher else b"")}
    while i < len(l1) or j < len(l2):
        if j >= len(l2) or (i < len(l1) and l1[i] < l2[j]):
            if "1" not in cacher:
                ctx.out(pre[1] + l1[i] + b"\n")
            i += 1
        elif i >= len(l1) or l2[j] < l1[i]:
            if "2" not in cacher:
                ctx.out(pre[2] + l2[j] + b"\n")
            j += 1
        else:
            if "3" not in cacher:
                ctx.out(pre[3] + l1[i] + b"\n")
            i += 1
            j += 1
    return 0


@outil("cmp")
def cmp(ctx):
    a = [x for x in ctx.args[1:] if not x.startswith("-") or x == "-"]
    silencieux = "-s" in ctx.args
    if len(a) < 2:
        ctx.err("cmp: missing operand\n")
        return 2
    d1, d2 = lire_entree_ou_fichier(ctx, "cmp", a[0]), lire_entree_ou_fichier(ctx, "cmp", a[1])
    if d1 is None or d2 is None:
        return 2
    if d1 == d2:
        return 0
    n = next((k for k in range(min(len(d1), len(d2))) if d1[k] != d2[k]), None)
    if silencieux:
        return 1
    if n is None:
        court = a[0] if len(d1) < len(d2) else a[1]
        ctx.err(f"cmp: EOF on {court} after byte {min(len(d1), len(d2))}, line {min(d1, d2, key=len).count(b'\n') + 1}\n")
        return 1
    ligne = d1[:n].count(b"\n") + 1
    ctx.out(f"{a[0]} {a[1]} differ: byte {n + 1}, line {ligne}\n")
    return 1


@outil("fold")
def fold(ctx):
    o = Options(ctx.args[1:], avec_valeur="w", chiffre="w")
    larg = int(o.val("w", defaut="80"))
    for f in o.reste or ["-"]:
        d = lire_entree_ou_fichier(ctx, "fold", f)
        if d is None:
            return 1
        for l in d.decode("utf-8", "replace").split("\n")[:-1] if d.endswith(b"\n") else d.decode().split("\n"):
            if not l:
                ctx.out("\n")
            while l:
                coupe = larg
                if o.a("s") and len(l) > larg:
                    k = l.rfind(" ", 0, larg)
                    if k >= 0:
                        coupe = k + 1
                ctx.out(l[:coupe] + "\n")
                l = l[coupe:]
    return 0


@outil("expand")
def expand(ctx):
    for f in [x for x in ctx.args[1:] if not x.startswith("-")] or ["-"]:
        d = lire_entree_ou_fichier(ctx, "expand", f)
        if d is None:
            return 1
        ctx.out(d.decode("utf-8", "replace").expandtabs(8))
    return 0


@outil("column")
def column(ctx):
    a = ctx.args[1:]
    sep = None
    table = False
    noms = []
    i = 0
    while i < len(a):
        if a[i] == "-t":
            table = True
        elif a[i] == "-s" and i + 1 < len(a):
            sep = a[i + 1]
            i += 1
        elif a[i].startswith("-s"):
            sep = a[i][2:]
        else:
            noms.append(a[i])
        i += 1
    texte = b""
    for f in noms or ["-"]:
        d = lire_entree_ou_fichier(ctx, "column", f)
        if d is None:
            return 1
        texte += d
    lignes = [l for l in texte.decode("utf-8", "replace").split("\n") if l.strip()]
    if not table:
        for l in lignes:
            ctx.out(l + "\n")
        return 0
    rangs = [(re.split("[" + re.escape(sep) + "]", l) if sep else l.split()) for l in lignes]
    n = max(len(r) for r in rangs) if rangs else 0
    larg = [max((len(r[k]) for r in rangs if k < len(r)), default=0) for k in range(n)]
    for r in rangs:
        ctx.out("  ".join(c.ljust(larg[k]) if k < len(r) - 1 else c for k, c in enumerate(r)) + "\n")
    return 0


from . import sed as _sed  # noqa: E402,F401
from . import awk as _awk  # noqa: E402,F401
