"""Le terminal du jeu : `python3` (et `python`), décision du propriétaire du 2 novembre.

Sous Windows, le terminal du jeu n'embarque et ne télécharge aucun programme : `python3` y lance le Python qui fait
DÉJÀ tourner le jeu (sys.executable), pour de vrai, comme le vrai python3 de Linux : `python3 -c "…"`,
`python3 script.py arguments`, `python3 -` / `python3 < script.py`, `./script.py` (#!/usr/bin/env python3, droit x),
`python3 --version`, les tuyaux et les redirections ; au clavier, sans argument, la petite console de Python.

Garde-fous (rien ne sort du terrain) :
  - le dossier courant doit être dans le terrain (~/terrain_terminagotchi), et le script aussi ;
  - pas de `-m` (pas de module lancé : ni pip, ni http.server ; ces étapes restent racontées) ;
  - dans le programme, une « garde » (sys.addaudithook, installée avant la première ligne de l'enfant) refuse
    d'écrire, de créer ou d'effacer hors du terrain, de lire hors du terrain (sauf les fichiers de Python lui-même),
    de lancer un autre programme, d'ouvrir un serveur et toute connexion réseau, sauf le phare du Port
    (127.0.0.1:8042, comme `curl`). Ce n'est pas une prison pour un adulte décidé, c'est un filet pour un enfant qui
    recopie un programme trouvé ailleurs : le message dit clairement ce qui a été refusé.
Les messages de Python (Traceback, SyntaxError…) sont ceux du vrai Python ; les chemins montrés sont ceux du terminal
du jeu (/home/<nom>/terrain_terminagotchi/…). pc/outils/test_terminal.py compare au vrai python3 sous Linux.
"""
import json
import os
import posixpath
import shlex
import subprocess
import sys
import threading

from .outils import outil

# ---------------------------------------------------------------- ce qui tourne DANS le Python de l'enfant
# (passé par -c : rien n'est écrit sur le disque, et ça marche aussi quand le jeu est un .pyz)
AMORCE = "import sys;exec(compile(sys.argv.pop(1),'<tg-python>','exec'))"
GARDE = r'''
import sys, os, json
_cfg = json.loads(sys.argv.pop(1))
sys.argv = _cfg["argv"]
_NT = os.name == "nt"
if _NT:                                       # comme sous Linux : des fins de ligne \n (jamais \r\n dans le terrain)
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(newline="\n")
        except Exception:
            pass
    import io as _io, builtins as _b
    _open0 = _io.open

    def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if "b" not in mode and newline is None and any(c in mode for c in "wax+"):
            newline = "\n"
        return _open0(file, mode, buffering, encoding, errors, newline, closefd, opener)
    _io.open = _b.open = _open


def _norm(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


_ECRIRE = [_norm(z) for z in _cfg["ecrire"]]
_LIRE = _ECRIRE + [_norm(z) for z in _cfg["lire"] if z]
_LIRE += [_norm(z) for z in sys.path if z and os.path.isabs(z)]        # les fichiers de Python lui-même
_PHARE = tuple(_cfg["phare"])
_LANTERNE = _cfg.get("lanterne")             # python3 -m http.server : le seul port qu'on peut ouvrir (127.0.0.1)
_MSG = _cfg["msg"]


def _dans(p, zones):
    if isinstance(p, int):
        return True
    try:
        if isinstance(p, bytes):
            p = os.fsdecode(p)
        p = _norm(os.fspath(p))
    except (TypeError, ValueError, OSError):
        return False
    if os.name != "nt" and p in ("/dev/null", "/dev/zero", "/dev/urandom", "/dev/random", "/dev/tty",
                                 "/dev/stdin", "/dev/stdout", "/dev/stderr"):
        return True
    if _NT and p.lower() in ("nul",):
        return True
    return any(p == z or p.startswith(z.rstrip("\\/") + os.sep) for z in zones)


def _non(quoi, chemin=None):
    if chemin is None:
        raise PermissionError(13, _MSG["refus"].format(quoi=quoi))
    raise PermissionError(13, _MSG["refus"].format(quoi=quoi), chemin)


_ECRIT = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_FICHIERS = {"os.mkdir": 0, "os.rmdir": 0, "os.remove": 0, "os.truncate": 0, "os.chmod": 0, "os.chown": 0,
             "os.utime": 0, "os.chflags": 0, "os.lchflags": 0, "os.mkfifo": 0, "os.mknod": 0, "shutil.rmtree": 0,
             "os.removexattr": 0, "os.setxattr": 0}
_INTERDITS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.startfile", "os.fork",
              "os.forkpty", "pty.spawn", "ctypes.dlopen", "ctypes.dlsym", "ctypes.cdata", "webbrowser.open",
              "socket.sendto", "socket.sendmsg", "os.kill", "os.killpg", "signal.pthread_kill",
              "_winapi.CreateProcess", "_winapi.CreateNamedPipe", "os.add_dll_directory")


def _garde(ev, a):
    if ev == "open":
        chemin, mode, flags = a
        ecrit = (mode is not None and any(c in str(mode) for c in "wax+")) or \
                (mode is None and isinstance(flags, int) and flags & _ECRIT)
        if not _dans(chemin, _ECRIRE if ecrit else _LIRE):
            _non(_MSG["ecrire" if ecrit else "lire"], chemin)
    elif ev in _FICHIERS:
        if not _dans(a[0], _ECRIRE):
            _non(_MSG["ecrire"], a[0])
    elif ev in ("os.rename", "os.link", "os.symlink", "shutil.copyfile", "shutil.copymode", "shutil.copystat",
                "shutil.move", "shutil.copytree"):
        for c in a[:2]:
            if not _dans(c, _ECRIRE):
                _non(_MSG["ecrire"], c)
    elif ev in ("os.listdir", "os.scandir", "glob.glob", "os.chdir"):
        c = a[0] if a and a[0] is not None else "."
        if not _dans(c, _ECRIRE if ev == "os.chdir" else _LIRE):
            _non(_MSG["lire"], c)
    elif ev == "sqlite3.connect":
        if a and a[0] not in (":memory:", "", b":memory:") and not _dans(a[0], _ECRIRE):
            _non(_MSG["ecrire"], a[0])
    elif ev == "socket.bind":
        adr = a[1]
        if not (_LANTERNE and isinstance(adr, tuple) and len(adr) >= 2 and adr[0] == "127.0.0.1"
                and adr[1] == _LANTERNE):
            _non(_MSG["reseau"])
    elif ev == "socket.connect":
        adr = a[1]
        if not (isinstance(adr, tuple) and len(adr) >= 2 and adr[0] in ("127.0.0.1", "localhost") and adr[1] in _PHARE):
            _non(_MSG["reseau"])
    elif ev in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex", "socket.gethostbyaddr"):
        h = a[0] if a else None
        if isinstance(h, bytes):
            h = h.decode("ascii", "replace")
        if h not in ("127.0.0.1", "localhost", None):
            _non(_MSG["reseau"])
    elif ev.startswith(_INTERDITS) or ev.startswith("winreg."):
        if ev in ("os.kill", "os.killpg") and a and a[0] == os.getpid():
            return
        _non(_MSG["programme"])
    elif ev == "sys.addaudithook":
        raise RuntimeError("garde du terminal du jeu")


def _nettoyer(tb, amorce):
    """Un Traceback sans les lignes de la garde (comme si le vrai python3 avait lancé le programme)."""
    if amorce and tb is not None:
        tb = tb.tb_next                       # la ligne -c de l'amorce
    gardes = []
    while tb is not None:
        if tb.tb_frame.f_code.co_filename != "<tg-python>":
            gardes.append(tb)
        tb = tb.tb_next
    for a, b in zip(gardes, gardes[1:] + [None]):
        a.tb_next = b
    return gardes[0] if gardes else None


def _sans_garde(e):
    vus = set()
    x, amorce = e, True
    while x is not None and id(x) not in vus:
        vus.add(id(x))
        x.__traceback__ = _nettoyer(x.__traceback__, amorce)
        amorce = False
        for y in (x.__cause__, x.__context__):
            if y is not None and id(y) not in vus:
                _sans_garde_seul(y, vus)
        x = None
    return e.__traceback__


def _sans_garde_seul(y, vus):
    vus.add(id(y))
    y.__traceback__ = _nettoyer(y.__traceback__, False)
    for z in (y.__cause__, y.__context__):
        if z is not None and id(z) not in vus:
            _sans_garde_seul(z, vus)


def _dire(e, tb):
    sys.excepthook(type(e), e, tb)            # (comme le vrai python3 : la sortie attend la fin si elle est en tuyau)


def _lancer(code, nom, glob):
    try:
        c = compile(code, nom, "exec")
    except (SyntaxError, ValueError) as e:
        e.__traceback__ = None
        _dire(e, None)
        sys.exit(1)
    sys.addaudithook(_garde)
    try:
        exec(c, glob)
    except SystemExit:
        raise
    except BaseException as e:               # noqa: BLE001 — comme le vrai python3 : le Traceback, puis code 1
        _dire(e, _sans_garde(e))
        if isinstance(e, KeyboardInterrupt):
            if _NT:
                sys.exit(130)
            import signal
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            os.kill(os.getpid(), signal.SIGINT)
        sys.exit(1)


def _module():
    import types, builtins
    m = types.ModuleType("__main__")
    m.__dict__["__builtins__"] = builtins
    sys.modules["__main__"] = m
    return m.__dict__


_genre = _cfg["genre"]
if _genre == "fichier":
    import linecache
    with open(_cfg["reel"], "rb") as _f:
        _src = _f.read()
    _g = _module()
    _g["__file__"] = _cfg["reel"]
    sys.path[0] = os.path.dirname(_cfg["reel"])
    if _cfg["montre"] != _cfg["reel"]:        # le Traceback montre le chemin du terminal du jeu, avec ses lignes
        _t = _src.decode("utf-8", "replace")
        linecache.cache[_cfg["montre"]] = (len(_t), None, _t.splitlines(True), _cfg["montre"])
        import traceback as _tb                # (l'affichage par linecache : le vrai fichier a un autre chemin)
        sys.excepthook = lambda t, e, tb: _tb.print_exception(t, e, tb)
    del _f
    _lancer(_src, _cfg["montre"], _g)
elif _genre == "code":
    sys.path[0] = ""
    if sys.version_info >= (3, 13):           # (Python 3.13 montre aussi les lignes de -c dans le Traceback)
        import linecache
        linecache.cache["<string>"] = (len(_cfg["code"]), None, _cfg["code"].splitlines(True), "<string>")
    _lancer(_cfg["code"], _cfg["nom"], _module())
elif _genre == "lanterne":                    # python3 -m http.server … --bind 127.0.0.1 (le dossier : dans le terrain)
    import mimetypes, runpy
    mimetypes.init()                          # (les types de fichiers lus AVANT la garde : ils sont hors du terrain)
    sys.path[0] = ""
    sys.addaudithook(_garde)
    try:
        runpy.run_module("http.server", run_name="__main__", alter_sys=True)
    except SystemExit:
        raise
    except BaseException as _e:              # noqa: BLE001
        _dire(_e, _sans_garde(_e))
        sys.exit(1)
elif _genre == "entree":
    sys.path[0] = ""
    _lancer(sys.stdin.buffer.read(), "<stdin>", _module())
else:                                         # la console de Python (au clavier, sans argument)
    import code as _code
    sys.path[0] = ""
    _g = _module()
    _crochet = sys.excepthook

    def _sans_lignes_de_garde(t, e, tb):
        _crochet(t, e, _nettoyer(tb, False))
    sys.excepthook = _sans_lignes_de_garde
    sys.addaudithook(_garde)
    _code.interact(banner=f"Python {sys.version} on {sys.platform}\n" + _MSG["console"], local=_g, exitmsg="")
'''

# les options de l'interpréteur qu'on laisse passer (sans danger) ; -m est refusé, -c et -V traités à part
SANS_VALEUR = set("bBdEhiIOqsSuvVxR")
AVEC_VALEUR = set("cmWX")
OPTIONS_PASSEES = {"-u", "-B", "-q", "-O", "-OO", "-b", "-bb", "-d", "-v", "-S", "-s", "-E", "-I", "-R", "-x"}


def interprete():
    """Le Python qui fait tourner le jeu (python.exe plutôt que pythonw.exe, qui n'a pas de console)."""
    exe = sys.executable or "python3"
    b = os.path.basename(exe).lower()
    if b.startswith("pythonw"):
        autre = os.path.join(os.path.dirname(exe), b.replace("pythonw", "python", 1))
        if os.path.exists(autre):
            exe = autre
    return exe


def analyser(args):
    """Les arguments de python3 → dict : options passées, genre (version, aide, module, code, entree, fichier,
    console), et le reste (sys.argv du programme). Comme le vrai : les options s'arrêtent au script, à -c ou -m."""
    r = {"options": [], "genre": None, "reste": [], "erreur": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--version":
            r["genre"] = r["genre"] or "version"
            r["vv"] = r.get("vv", 0) + 1
            i += 1
            continue
        if a == "--help":
            r["genre"] = "aide"
            return r
        if a == "-":
            r["genre"], r["reste"] = "entree", ["-"] + args[i + 1:]
            return r
        if a == "--":
            i += 1
            break
        if a.startswith("--"):
            r["erreur"] = f"unknown option {a}"
            return r
        if not a.startswith("-") or a == "-":
            break
        j = 1
        while j < len(a):
            c = a[j]
            if c in AVEC_VALEUR:
                val = a[j + 1:]
                if not val:
                    if i + 1 >= len(args):
                        r["erreur"] = f"Argument expected for the -{c} option"
                        return r
                    i += 1
                    val = args[i]
                if c == "c":
                    r["genre"], r["code"] = "code", val
                    r["reste"] = ["-c"] + args[i + 1:]
                    return r
                if c == "m":
                    r["genre"], r["module"] = "module", val
                    r["reste"] = args[i + 1:]
                    return r
                r["options"] += [f"-{c}", val]
                break
            if c not in SANS_VALEUR:
                r["erreur"] = f"unknown option -{c}"
                return r
            if c == "V":
                r["genre"] = r["genre"] or "version"
                r["vv"] = r.get("vv", 0) + 1
            elif c == "h":
                r["genre"] = "aide"
                return r
            elif c == "i":
                r["interactif"] = True
            else:
                r["options"].append(f"-{c}")
            j += 1
        i += 1
    if r["genre"] == "version":
        return r
    if i < len(args):
        r["genre"], r["script"], r["reste"] = "fichier", args[i], args[i:]
    else:
        r["genre"], r["reste"] = "console", [""]
    return r


def _t(cle, **k):
    from ..langue import t
    return t(cle, **k)


def _dans(chemin, zone):
    a = os.path.normcase(os.path.realpath(os.path.abspath(str(chemin))))
    z = os.path.normcase(os.path.realpath(os.path.abspath(str(zone))))
    return a == z or a.startswith(z.rstrip("\\/") + os.sep)


def _reel(ctx, vp):
    return ctx.vfs.reel(vp) if ctx.vfs.mode == "windows" else vp


def ports_phare():
    try:
        from .. import port
        return [port._ports()[0]]
    except Exception:                         # noqa: BLE001
        return [8042]


def messages():
    return {"refus": _t("vsh.python.garde"), "ecrire": _t("vsh.python.garde.ecrire"),
            "lire": _t("vsh.python.garde.lire"), "reseau": _t("vsh.python.garde.reseau"),
            "programme": _t("vsh.python.garde.programme"),
            "console": 'Type "help", "copyright", "credits" or "license" for more information.'}


@outil("python3", "python")
def python3(ctx):
    nom = ctx.args[0]
    r = analyser(ctx.args[1:])
    if r["erreur"]:
        ctx.err(f"{r['erreur']}\nusage: {nom} [option] ... [-c cmd | -m mod | file | -] [arg] ...\n"
                f"Try `python -h' for more information.\n")
        return 2
    if r["genre"] == "version":
        ctx.out(f"Python {sys.version if r.get('vv', 1) > 1 else sys.version.split()[0]}\n")
        return 0
    if r["genre"] == "aide":
        return _executer(ctx, [interprete(), "-h"], None, capture_seule=True)
    if r["genre"] == "module" and r["module"] != "http.server":
        ctx.err(_t("vsh.python.module", module=r["module"]) + "\n")
        return 1
    terrain = ctx.vfs.terrain_reel
    ici = _reel(ctx, ctx.sh.cwd)
    if ici is None or not _dans(ici, terrain) or not os.path.isdir(str(ici)):
        ctx.err(_t("vsh.python.dossier") + "\n")
        return 1
    cfg = {"argv": r["reste"], "genre": r["genre"], "ecrire": [str(terrain)], "lire": [str(terrain)],
           "phare": ports_phare() + lanternes(ctx.vfs), "msg": messages()}
    lanterne = None
    if r["genre"] == "module":                # la lanterne de l'enfant : python3 -m http.server
        l = lanterne_args(r["reste"])
        if l.get("erreur"):
            ctx.err(l["erreur"])
            return 2
        if l["bind"] not in ("127.0.0.1", "localhost"):
            ctx.err(_t("vsh.python.lanterne.bind", port=l["port"]) + "\n")
            return 1
        if not 1024 <= l["port"] <= 65535 or l["port"] in ports_phare():
            ctx.err(_t("vsh.python.lanterne.port", phare=ports_phare()[0]) + "\n")
            return 1
        dossier = ici
        if l["dossier"] is not None:
            dossier = _reel(ctx, ctx.chemin(l["dossier"]))
            if dossier is None or not _dans(dossier, terrain):
                ctx.err(_t("vsh.python.hors_terrain", script=l["dossier"]) + "\n")
                return 2
        lanterne = l["port"]
        argv = [str(l["port"]), "--bind", "127.0.0.1", "--directory", str(dossier)] + l["autres"]
        cfg.update(genre="lanterne", lanterne=l["port"], argv=["http.server"] + argv)
    elif r["genre"] == "code":
        cfg.update(code=r["code"], nom="<string>")
    elif r["genre"] == "console" and not (ctx.entree.tty and ctx.sortie.tty):
        cfg["genre"] = "entree"
    elif r["genre"] == "fichier":
        vp = ctx.chemin(r["script"])
        reel = _reel(ctx, vp)
        if reel is None or not _dans(reel, terrain):
            ctx.err(_t("vsh.python.hors_terrain", script=r["script"]) + "\n")
            return 2
        if not os.path.exists(str(reel)):
            ctx.err(f"{nom}: can't open file {vp!r}: [Errno 2] No such file or directory\n")
            return 2
        if os.path.isdir(str(reel)):
            ctx.err(f"{nom}: can't find '__main__' module in {r['script']!r}\n")
            return 1
        try:
            if ctx.vfs.mode == "windows" and not ctx.vfs.mode_reel(str(reel)) & 0o400:
                raise PermissionError
            with open(str(reel), "rb"):
                pass
        except OSError:
            ctx.err(f"{nom}: can't open file {vp!r}: [Errno 13] Permission denied\n")
            return 2
        cfg.update(reel=str(reel), montre=vp if ctx.vfs.mode == "windows" else str(reel))
        cfg["argv"] = [r["script"]] + [_argument(ctx, x) for x in r["reste"][1:]]
    if "PYTHONUNBUFFERED" in ctx.sh.exportees and ctx.sh.vars.get("PYTHONUNBUFFERED") and "-u" not in r["options"]:
        # (export PYTHONUNBUFFERED=1 dans le terminal du jeu : -E ignore les variables PYTHON…, on garde celle-ci)
        r["options"].append("-u")
    cmd = [interprete(), "-X", "utf8", "-E", "-s"] + [o for o in r["options"] if o in OPTIONS_PASSEES or
                                                       o.startswith("-W")] + ["-c", AMORCE, GARDE,
                                                                              json.dumps(cfg, ensure_ascii=False)]
    return _executer(ctx, cmd, str(ici), lanterne=lanterne)


# ---------------------------------------------------------------- la lanterne (python3 -m http.server)
def lanterne_args(reste):
    """Les arguments de http.server : port (8000), --bind/-b, --directory/-d, --protocol/-p."""
    l = {"port": 8000, "bind": None, "dossier": None, "autres": []}
    i = 0
    usage = ("usage: server.py [-h] [--cgi] [-b ADDRESS] [-d DIRECTORY] [-p VERSION] [port]\n"
             "server.py: error: ")
    while i < len(reste):
        a = reste[i]
        nom, egal, val = a.partition("=")
        if nom in ("-b", "--bind", "-d", "--directory", "-p", "--protocol") or (
                len(a) > 2 and a[:2] in ("-b", "-d", "-p") and not a.startswith("--")):
            if not egal and len(a) > 2 and a[:2] in ("-b", "-d", "-p") and not a.startswith("--"):
                nom, val = a[:2], a[2:]
            elif not egal:
                if i + 1 >= len(reste):
                    l["erreur"] = usage + f"argument {nom}: expected one argument\n"
                    return l
                i += 1
                val = reste[i]
            if nom in ("-b", "--bind"):
                l["bind"] = val
            elif nom in ("-d", "--directory"):
                l["dossier"] = val
            else:
                l["autres"] += ["--protocol", val]
        elif a == "--cgi" or (a.startswith("-") and a != "-"):
            l["erreur"] = usage + f"unrecognized arguments: {a}\n"
            return l
        else:
            try:
                l["port"] = int(a)
            except ValueError:
                l["erreur"] = usage + f"argument port: invalid int value: '{a}'\n"
                return l
        i += 1
    return l


_LANTERNES = {}                               # port → Popen (celles de ce terminal : éteintes en le quittant)


def _registre(vfs):
    return os.path.join(str(vfs.jeu_reel), "lanternes.json")


def _lire_registre(vfs):
    try:
        with open(_registre(vfs), encoding="utf-8") as f:
            return {int(k): int(v) for k, v in json.load(f).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def _ecrire_registre(vfs, d):
    try:
        os.makedirs(str(vfs.jeu_reel), exist_ok=True)
        tmp = _registre(vfs) + f".{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in d.items()}, f)
        os.replace(tmp, _registre(vfs))
    except OSError:
        pass


def _vivant(pid):
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            k.CloseHandle(h)
            return bool(ok) and code.value == 259         # STILL_ACTIVE
        except Exception:                     # noqa: BLE001
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def lanternes(vfs):
    """Les ports des lanternes allumées par le terminal du jeu (toutes ses fenêtres) : curl peut les visiter."""
    d = _lire_registre(vfs)
    vivantes = {p: pid for p, pid in d.items() if _vivant(pid)}
    if len(vivantes) != len(d):
        _ecrire_registre(vfs, vivantes)
    return sorted(vivantes)


def _noter_lanterne(vfs, port, pid):
    d = _lire_registre(vfs)
    if pid is None:
        d.pop(port, None)
    else:
        d[port] = pid
    _ecrire_registre(vfs, d)


def arreter_lanternes():
    """En quittant le terminal du jeu (ou à la fin d'un test) : les lanternes encore allumées s'éteignent, comme les
    tâches de fond de bash quand on ferme la fenêtre."""
    for port, (p, vfs) in list(_LANTERNES.items()):
        try:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        _noter_lanterne(vfs, port, None)
        _LANTERNES.pop(port, None)


import atexit  # noqa: E402

atexit.register(arreter_lanternes)


def _argument(ctx, x):
    """Windows : un chemin du terminal (/home/lea/terrain_terminagotchi/a.txt) donné au programme devient le vrai
    chemin du terrain (sinon Python ne le trouverait pas)."""
    if ctx.vfs.mode != "windows" or not x.startswith("/"):
        return x
    r = ctx.vfs.reel(posixpath.normpath(x))
    return str(r) if r is not None and _dans(r, ctx.vfs.terrain_reel) else x


def _environnement(ctx):
    from .outils import variables_exportees
    env = dict(os.environ)
    env.update(variables_exportees(ctx.sh))
    env.pop("TG_ARRET", None)
    return env


def _executer(ctx, cmd, cwd, capture_seule=False, lanterne=None):
    """Lance le vrai Python : à l'écran directement (au clavier : input(), la console, Ctrl+C), ou par des tuyaux
    (un tuyau, une redirection, les tests). Ctrl+C, `timeout` ou `kill` l'arrêtent."""
    direct = not capture_seule and ctx.sortie.tty and ctx.erreur.tty and getattr(ctx.sortie, "genre", "") == "terminal"
    clavier = getattr(ctx.entree, "clavier", None) is not None
    kw = {"cwd": cwd, "env": _environnement(ctx)}
    donnees = None
    if clavier and not capture_seule:
        kw["stdin"] = None                   # le clavier : input() lit ce que tape l'enfant
    else:
        donnees = b"" if capture_seule else ctx.entree.tout()
        kw["stdin"] = subprocess.PIPE
    meme = ctx.sortie is ctx.erreur
    if not direct:
        kw["stdout"] = subprocess.PIPE
        kw["stderr"] = subprocess.STDOUT if meme else subprocess.PIPE
    else:
        try:
            sys.stdout.flush()
        except (OSError, ValueError):
            pass
    if getattr(ctx.sh, "fond", False):       # tâche de fond (&) : comme bash, à part du Ctrl+C du clavier
        if os.name == "nt":
            kw["creationflags"] = 0x00000200     # CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
    try:
        p = subprocess.Popen(cmd, **kw)
    except OSError as e:
        ctx.err(f"{ctx.args[0]}: {e}\n")
        return 127
    if lanterne:                             # curl (et les autres fenêtres) savent qu'elle brille
        _LANTERNES[lanterne] = (p, ctx.vfs)
        _noter_lanterne(ctx.vfs, lanterne, p.pid)
    try:
        return _attendre(ctx, p, donnees, direct, meme)
    finally:
        if lanterne:
            _LANTERNES.pop(lanterne, None)
            _noter_lanterne(ctx.vfs, lanterne, None)


def _attendre(ctx, p, donnees, direct, meme):
    fils = []
    if donnees is not None:
        def nourrir():
            try:
                p.stdin.write(donnees)
            except (OSError, ValueError):
                pass
            try:
                p.stdin.close()
            except (OSError, ValueError):
                pass
        fils.append(threading.Thread(target=nourrir, daemon=True))
    if not direct:
        def lire(flux, ecrire):
            while True:
                try:
                    b = flux.read1(65536)
                except (OSError, ValueError):
                    break
                if not b:
                    break
                try:
                    ecrire(b)
                except Exception:            # noqa: BLE001 — (un | head fermé : on vide quand même)
                    pass
        fils.append(threading.Thread(target=lire, args=(p.stdout, ctx.out), daemon=True))
        if not meme:
            fils.append(threading.Thread(target=lire, args=(p.stderr, ctx.err), daemon=True))
    for f in fils:
        f.start()
    interrompu = False
    try:
        while True:
            try:
                p.wait(timeout=0.05)
                break
            except subprocess.TimeoutExpired:
                pass
            if ctx.sh.arret.is_set() and not interrompu:
                interrompu = True
                try:
                    p.terminate()
                except OSError:
                    pass
    except KeyboardInterrupt:                # Ctrl+C au clavier : Python l'a reçu aussi (son Traceback), on attend
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
        for f in fils:
            f.join(2)
        raise
    for f in fils:
        f.join(5)
    if interrompu:
        from .shell import Interrompu
        raise Interrompu()
    code = p.returncode
    if code < 0:                             # tué par un signal (Linux) : comme bash, 128 + signal
        code = 128 - code
    elif code == 0xC000013A:                  # Ctrl+C sous Windows
        code = 130
    return code


# ---------------------------------------------------------------- les usages racontés (le jeu raconte l'étape)
def usage_raconte(args):
    """python3 -m … (pip…, sauf la lanterne http.server) : pas dans le terminal du jeu ; l'étape est racontée."""
    r = analyser(list(args[1:]))
    return r.get("genre") == "module" and r.get("module") != "http.server"


def mots(texte):
    try:
        return shlex.split(texte)
    except ValueError:
        return texte.split()
