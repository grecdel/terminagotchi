"""Le terminal du jeu : sqlite3 (l'outil en ligne de commande), avec le module sqlite3 fourni avec Python (aucun
programme extérieur). Modes list (|), csv, column, line ; .tables, .schema, .headers, .mode, .separator, .quit."""
import os
import re
import sqlite3 as _sql

from .outils import outil
from .vfs import ErreurFs


def _valeur(v, mode):
    if v is None:
        return ""
    if isinstance(v, float):
        t = "%.15g" % v
        if "." not in t and "e" not in t and "inf" not in t and "nan" not in t:
            t += ".0"
        return t
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


class Cli:
    def __init__(self, ctx, chemin_reel):
        self.ctx = ctx
        self.mode = "list"
        self.sep = "|"
        self.entetes = False
        self.chemin = chemin_reel
        self.base = _sql.connect(chemin_reel if chemin_reel else ":memory:", isolation_level=None)

    def sortir(self, t):
        self.ctx.out(t.encode("utf-8", "surrogateescape"))

    def point(self, ligne):
        mots = ligne.strip().split()
        c = mots[0]
        if c in (".quit", ".exit", ".q"):
            return False
        if c == ".tables":
            noms = sorted(r[0] for r in self.base.execute(
                "SELECT name FROM sqlite_schema WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'"))
            if len(mots) > 1:
                from .shell import motif_shell
                noms = [n for n in noms if motif_shell(mots[1].replace("%", "*"), n)]
            if noms:
                large = max(len(n) for n in noms)
                ncol = max(1, 80 // (large + 2))
                nlig = (len(noms) + ncol - 1) // ncol
                for i in range(nlig):
                    l = ""
                    j = i
                    while j < len(noms):
                        l += ("" if j < nlig else "  ") + noms[j].ljust(large)
                        j += nlig
                    self.sortir(l + "\n")
            return True
        if c == ".schema":
            req = "SELECT sql FROM sqlite_schema WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
            args = ()
            if len(mots) > 1:
                req += " AND (tbl_name LIKE ? OR name LIKE ?)"
                args = (mots[1], mots[1])
            for (s,) in self.base.execute(req + " ORDER BY rowid", args):
                self.sortir(s + ";\n")
            return True
        if c in (".headers", ".header"):
            self.entetes = len(mots) > 1 and mots[1] in ("on", "1", "yes", "true")
            return True
        if c == ".mode":
            self.mode = mots[1] if len(mots) > 1 else "list"
            if self.mode == "csv":
                self.sep = ","
            elif self.mode == "list" and self.sep == ",":
                self.sep = "|"
            elif self.mode == "tabs":
                self.mode, self.sep = "list", "\t"
            return True
        if c == ".separator":
            if len(mots) > 1:
                self.sep = mots[1].strip("\"'").replace("\\t", "\t")
            return True
        if c == ".help":
            self.sortir(".headers on|off   Turn display of headers on or off\n.mode MODE        Set output mode\n"
                        ".quit             Exit this program\n.schema ?TABLE?   Show the CREATE statements\n"
                        ".tables ?TABLE?   List names of tables\n")
            return True
        if c == ".import" and len(mots) >= 3:
            try:
                d = self.ctx.vfs.lire(self.ctx.chemin(mots[1])).decode("utf-8", "replace")
            except ErreurFs as e:
                self.ctx.err(f"Error: cannot open \"{mots[1]}\"\n")
                return True
            import csv
            lignes = list(csv.reader(d.splitlines(), delimiter="," if self.mode == "csv" else self.sep))
            table = mots[2]
            existe = self.base.execute("SELECT 1 FROM sqlite_schema WHERE name=?", (table,)).fetchone()
            if not existe and lignes:
                cols = ", ".join(f'"{x}" TEXT' for x in lignes[0])
                self.base.execute(f'CREATE TABLE "{table}"({cols})')
                lignes = lignes[1:]
            for l in lignes:
                self.base.execute(f'INSERT INTO "{table}" VALUES ({",".join("?" * len(l))})', l)
            return True
        self.ctx.err(f'Error: unknown command or invalid arguments:  "{c[1:]}". Enter ".help" for help\n')
        return True

    def sql(self, texte):
        try:
            cur = self.base.cursor()
            for instr in _instructions(texte):
                cur.execute(instr)
                if cur.description is None:
                    continue
                noms = [d[0] for d in cur.description]
                rangs = cur.fetchall()
                self.afficher(noms, rangs)
        except _sql.Error as e:
            msg = str(e)
            genre = "Parse error" if isinstance(e, _sql.OperationalError) and (
                "no such" in msg or "syntax" in msg or "incomplete" in msg) else "Runtime error"
            self.ctx.err(f"{genre}: {msg}\n")
            return False
        return True

    def afficher(self, noms, rangs):
        m = self.mode
        if m in ("list", "csv"):
            def cel(v):
                t = _valeur(v, m)
                if m == "csv" and (self.sep in t or '"' in t or "\n" in t):
                    t = '"' + t.replace('"', '""') + '"'
                return t
            if self.entetes:
                self.sortir(self.sep.join(noms) + ("\r\n" if m == "csv" else "\n"))
            for r in rangs:
                self.sortir(self.sep.join(cel(v) for v in r) + ("\r\n" if m == "csv" else "\n"))
        elif m == "line":
            large = max(len(n) for n in noms)
            for k, r in enumerate(rangs):
                if k:
                    self.sortir("\n")
                for n, v in zip(noms, r):
                    self.sortir(f"{n.rjust(large)} = {_valeur(v, m)}\n")
        else:
            larg = [max([len(n)] + [len(_valeur(r[i], m)) for r in rangs]) for i, n in enumerate(noms)]
            if m in ("box", "table"):
                h, v, coins = ("─", "│", "┌┬┐├┼┤└┴┘") if m == "box" else ("-", "|", "+++++++++")
                self.sortir(coins[0] + coins[1].join(h * (w + 2) for w in larg) + coins[2] + "\n")
                self.sortir(v + v.join(" " + n.ljust(w) + " " for n, w in zip(noms, larg)) + v + "\n")
                self.sortir(coins[3] + coins[4].join(h * (w + 2) for w in larg) + coins[5] + "\n")
                for r in rangs:
                    self.sortir(v + v.join(" " + (_valeur(x, m).rjust(w) if isinstance(x, (int, float)) else
                                                  _valeur(x, m).ljust(w)) + " " for x, w in zip(r, larg)) + v + "\n")
                self.sortir(coins[6] + coins[7].join(h * (w + 2) for w in larg) + coins[8] + "\n")
            else:
                self.sortir("  ".join(n.ljust(w) for n, w in zip(noms, larg)).rstrip() + "\n")
                self.sortir("  ".join("-" * w for w in larg) + "\n")
                for r in rangs:
                    self.sortir("  ".join(_valeur(x, m).ljust(w) for x, w in zip(r, larg)).rstrip() + "\n")


def _instructions(texte):
    """Découpe un texte SQL en instructions complètes."""
    out, cur = [], ""
    for morceau in re.split(r"(;)", texte):
        cur += morceau
        if morceau == ";" and _sql.complete_statement(cur):
            out.append(cur)
            cur = ""
    if cur.strip():
        out.append(cur)
    return out


@outil("sqlite3")
def sqlite3(ctx):
    a = ctx.args[1:]
    cli_opts = []
    while a and a[0].startswith("-"):
        cli_opts.append(a.pop(0))
    if "-version" in cli_opts or "--version" in cli_opts:
        ctx.out(_sql.sqlite_version + " (le module sqlite3 de Python, dans le terminal du jeu)\n")
        return 0
    fichier = a[0] if a else None
    reel = None
    if fichier:
        vp = ctx.chemin(fichier)
        if ctx.vfs.est_dossier(vp):
            ctx.err(f'Error: unable to open database "{fichier}": unable to open database file\n')
            return 1
        r = ctx.vfs.reel(vp) if ctx.vfs.mode == "windows" else vp
        if r is None or (not ctx.vfs.existe(vp) and not ctx.vfs.ecriture_permise(vp)):
            ctx.err(f'Error: unable to open database "{fichier}": unable to open database file\n')
            return 1
        reel = str(r)
        if not os.path.exists(reel) and not (len(a) > 1 and not a[1].startswith(".")):
            reel_cree = True
        else:
            reel_cree = False
    try:
        cli = Cli(ctx, reel)
    except _sql.Error as e:
        ctx.err(f'Error: unable to open database "{fichier}": {e}\n')
        return 1
    for o in cli_opts:
        if o in ("-header", "-headers"):
            cli.entetes = True
        elif o == "-csv":
            cli.mode, cli.sep = "csv", ","
        elif o == "-column":
            cli.mode = "column"
        elif o == "-line":
            cli.mode = "line"
        elif o == "-box":
            cli.mode = "box"
    code = 0
    try:
        if len(a) > 1:
            for cmd in a[1:]:
                if cmd.startswith("."):
                    cli.point(cmd)
                elif not cli.sql(cmd):
                    code = 1
                    break
            return code
        if ctx.entree.tty:
            ctx.out("SQLite version " + _sql.sqlite_version + " (le module sqlite3 de Python)\n"
                    "Enter \".help\" for usage hints.\n")
            tampon = ""
            while True:
                ctx.out("sqlite> " if not tampon else "   ...> ")
                l = ctx.entree.ligne()
                if not l:
                    break
                l = l.decode("utf-8", "replace")
                if not tampon and l.strip().startswith("."):
                    if not cli.point(l):
                        break
                    continue
                tampon += l
                if _sql.complete_statement(tampon):
                    cli.sql(tampon)
                    tampon = ""
            return 0
        texte = ctx.entree.tout().decode("utf-8", "replace")
        tampon = ""
        for l in texte.splitlines(keepends=True):
            if not tampon and l.strip().startswith("."):
                if not cli.point(l):
                    break
                continue
            tampon += l
            if _sql.complete_statement(tampon):
                if not cli.sql(tampon):
                    code = 1
                tampon = ""
        if tampon.strip():
            if not cli.sql(tampon):
                code = 1
        return code
    finally:
        cli.base.close()
        if fichier and reel and reel_cree and os.path.exists(reel) and os.path.getsize(reel) == 0:
            os.unlink(reel)
