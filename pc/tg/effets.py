"""Les commandes qui se voient dans le monde des biomes : la SPÉCIFICATION COMMUNE des effets.

Même règle que Effets.kt (Android) et site/src/effets.js (le site) ; vecteurs communs donnees/effets/vecteurs.json
(pc/outils/test_effets.py, tests/jvm/Effets.kt, site/test/test.mjs).

    evenements(ligne, avant, apres, code, sortie="") → [événement]

avant / apres : deux PHOTOS du terrain (photo()), prises juste avant et juste après la commande :
    {"cwd": chemin relatif au terrain ("" = le terrain lui-même, None = ailleurs),
     "f": {chemin relatif: [genre "d"|"f", taille, date de modification en ms, droits (0o777)]}}

Règle d'or : UN EFFET NE MENT JAMAIS. Les effets sur les fichiers et dossiers viennent de la COMPARAISON avant/après
(comme « la carte a poussé », maison.pousse), jamais du seul texte de la commande. Le texte de la commande sert
seulement à donner un NOM à ce qui s'est vraiment passé (un fichier apparu après `cp` est une copie, après `touch`
un objet posé, après `>` un panneau écrit). Si rien n'a changé et que la commande a raté : un signe doux (« refus » :
cadenas, rebond ou « ? »), jamais d'écran rouge. Les commandes qui ne changent rien (ls, cat, pwd, find…) ne montrent
quelque chose que si elles ont réussi, et seulement sur ce qui existe vraiment dans la photo.

Un événement : {"type", "cmd", "prio", …} ; prio 3 = indispensable (★★★, réglage « essentiels »), 2 = utile (★★).
Les rafales (rm *, un script qui crée 100 fichiers) : au-delà de GROUPE événements du même type, un seul
{"type": "groupe", "sorte": type, "n": nombre, "chemins": les premiers}.

Point d'extension (les autres mondes : Poste de Contrôle, Bibliothèque du Temps, Atelier, Sommet…) :
    EXTENSIONS.append(f)   avec f(contexte) → [événement] ; contexte : dict (ligne, cmds, segments, avant, apres,
    code, sortie, plus, moins, changes, deja) ; appelée seulement quand aucune règle de base n'a déjà répondu
    à la commande (deja = les événements déjà trouvés). Même chose dans Effets.kt (Effets.extensions).
"""
import os
import re
import stat

GROUPE = 6              # au-delà : un effet groupé
MAX_PHOTO = 800         # la photo du terrain s'arrête là (un terrain géant ne ralentit pas le jeu)
PROFONDEUR = 6
IGNORES = {".git", "node_modules", "__pycache__", ".cache", "venv", ".venv", ".gradle", "build"}
NIVEAUX = ("tous", "essentiels", "aucun")

# les noms PowerShell (cmdlets et alias) → la commande Linux équivalente (core.PS_CMDLETS, plus les alias)
PS = {"get-location": "pwd", "gl": "pwd", "set-location": "cd", "sl": "cd", "chdir": "cd", "push-location": "cd",
      "pushd": "cd", "get-childitem": "ls", "gci": "ls", "dir": "ls", "ll": "ls", "la": "ls", "get-content": "cat",
      "gc": "cat", "type": "cat", "set-content": "echo", "sc": "echo", "add-content": "echo", "ac": "echo",
      "out-file": "tee", "tee-object": "tee", "copy-item": "cp", "copy": "cp", "cpi": "cp", "move-item": "mv",
      "move": "mv", "mi": "mv", "rename-item": "mv", "ren": "mv", "rni": "mv", "remove-item": "rm", "del": "rm",
      "erase": "rm", "ri": "rm", "rd": "rmdir", "new-item": "touch", "ni": "touch", "md": "mkdir",
      "write-output": "echo", "write-host": "echo", "write": "echo", "select-string": "grep", "get-process": "ps",
      "gps": "ps", "stop-process": "kill", "spps": "kill", "test-connection": "ping", "invoke-webrequest": "curl",
      "iwr": "curl", "invoke-restmethod": "curl", "irm": "curl", "get-filehash": "sha256sum", "sort-object": "sort",
      "measure-object": "wc", "set-acl": "chmod", "get-acl": "ls", "compare-object": "diff", "start-sleep": "sleep"}
LIRE = {"cat", "head", "tail", "less", "more", "wc", "nl", "bat"}
EMPREINTE = {"sha256sum", "sha1sum", "md5sum", "base64", "shasum", "b2sum"}
RESEAU = {"ping", "curl", "wget", "nc", "ssh", "scp", "dig", "nslookup", "host", "traceroute"}
PROCESSUS = {"ps", "kill", "killall", "pkill", "jobs", "top", "htop", "bg", "fg", "sleep"}
CAISSE = {"tar", "zip", "unzip", "gzip", "gunzip"}
RIEN = {"clear", "exit", "alias", "export", "env", "source", ".", "unalias", "set", "history", "reset", "cls"}
# prio de chaque type d'événement (3 : les effets ★★★ ; 2 : ★★)
PRIO = {"jokers": 3, "dossier+": 3, "dossier-": 3, "objet+": 3, "objet-": 3, "touche": 3, "deplace": 3,
        "renomme": 3, "copie": 3, "ecrit": 3, "droits": 3, "refus": 3, "cd": 3, "pwd": 3, "ls": 3, "find": 3,
        "lire": 3, "groupe": 3, "modifie": 2, "lucioles": 2, "messager": 2, "photo": 2, "empreinte": 2,
        "tuyau": 2, "caisse": 2}
_PARCELLE = re.compile(r"parcelle[_-]?\d*")
TYPES = ("feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")
EXTENSIONS = []


# ================================================================ la photo du terrain
def photo(racine, cwd=None, voir_caches=True):
    """La photo du terrain (racine : son dossier) : chaque chemin avec son genre, sa taille, sa date (ms), ses droits.
    Limitée à MAX_PHOTO entrées et PROFONDEUR niveaux ; cwd : le dossier courant (absolu) → relatif ou None."""
    racine = str(racine)
    f = {}

    def tour(d, r, n):
        if n > PROFONDEUR or len(f) >= MAX_PHOTO:
            return
        try:
            with os.scandir(d) as it:
                entrees = sorted(it, key=lambda e: e.name)
        except OSError:
            return
        for e in entrees:
            if len(f) >= MAX_PHOTO:
                return
            if e.name.startswith(".") and not voir_caches:
                continue
            c = f"{r}/{e.name}" if r else e.name
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                g = "l"
            elif stat.S_ISDIR(st.st_mode):
                g = "d"
            else:
                g = "f"
            f[c] = [g, 0 if g == "d" else int(st.st_size), int(st.st_mtime_ns // 1_000_000), st.st_mode & 0o777]
            if g == "d" and e.name not in IGNORES:
                tour(e.path, c, n + 1)
    if os.path.isdir(racine):
        tour(racine, "", 1)
    return {"cwd": relatif(racine, cwd), "f": f}


def relatif(racine, chemin):
    """Le chemin relatif au terrain ("" = le terrain), ou None s'il est ailleurs."""
    if not chemin:
        return None
    try:
        r = os.path.relpath(os.path.realpath(str(chemin)), os.path.realpath(str(racine)))
    except ValueError:
        return None
    if r == ".":
        return ""
    if r.startswith(".."):
        return None
    return r.replace(os.sep, "/")


# ================================================================ lire la ligne
def _jetons(seg):
    """Les mots d'un morceau de ligne : [(texte, cité)] (cité : avec des guillemets, donc pas un joker).
    Un découpage simple, le même dans les trois langages : espaces hors guillemets, \\ échappe hors '…'."""
    out, cour, cite, dans, q, esc = [], "", False, False, None, False
    for c in seg:
        if esc:
            cour += c
            esc = False
            dans = True
        elif q:
            if c == q:
                q = None
            elif c == "\\" and q == '"':
                esc = True
            else:
                cour += c
        elif c in "\"'":
            q, cite, dans = c, True, True
        elif c == "\\":
            esc = True
        elif c in " \t":
            if dans:
                out.append((cour, cite))
            cour, cite, dans = "", False, False
        else:
            cour += c
            dans = True
    if dans:
        out.append((cour, cite))
    return out


def correspond(nom, motif):
    """Un nom correspond-il à un motif de jokers (* ? [abc] [!abc]) ? Même règle que fnmatchcase."""
    rx, i = "", 0
    while i < len(motif):
        c = motif[i]
        i += 1
        if c == "*":
            rx += ".*"
        elif c == "?":
            rx += "."
        elif c == "[":
            j = motif.find("]", i + 1 if i < len(motif) and motif[i] in "!^" else i)
            if j < 0:
                rx += "\\["
            else:
                cl = motif[i:j]
                i = j + 1
                if cl[:1] in ("!", "^"):
                    cl = "^" + cl[1:]
                rx += "[" + cl.replace("\\", "\\\\") + "]"
        else:
            rx += "\\" + c if c in ".^$+{}()|\\" else c
    try:
        return re.fullmatch(rx, nom, re.S) is not None
    except re.error:
        return False


def canon(cmd):
    """Le nom canonique d'une commande (PowerShell compris, sans chemin : /bin/ls → ls)."""
    c = (cmd or "").split("/")[-1].lower()
    return PS.get(c, c)


def segments(ligne):
    """La ligne découpée en commandes : [{"cmd", "args": [(texte, cité)], "redir": [(">"|">>", cible)], "fond": &,
    "tuyau": vient après un |}]."""
    out = []
    texte = ligne.strip()
    # on coupe sur && || ; | & (hors guillemets)
    morceaux, cour, q, i = [], "", None, 0
    while i < len(texte):
        c = texte[i]
        if q:
            cour += c
            if c == q:
                q = None
            i += 1
            continue
        if c in "\"'":
            q = c
            cour += c
            i += 1
            continue
        deux = texte[i:i + 2]
        if deux in ("&&", "||"):
            morceaux.append((cour, deux))
            cour = ""
            i += 2
            continue
        if c in ";|&" and not (c == "&" and texte[i - 1:i] == ">"):
            morceaux.append((cour, c))
            cour = ""
            i += 1
            continue
        cour += c
        i += 1
    morceaux.append((cour, ""))
    prec = ""
    for seg, sep in morceaux:
        s = seg.strip()
        if not s:
            prec = sep
            continue
        redir = []
        for m in re.finditer(r"(\d?>>?|&>)\s*(\"[^\"]*\"|'[^']*'|[^\s<>|;&]+)", s):
            op = ">>" if ">>" in m.group(1) else ">"
            if not m.group(1).startswith("2"):
                redir.append((op, m.group(2).strip("\"'")))
        s2 = re.sub(r"(\d?>>?|&>)\s*(\"[^\"]*\"|'[^']*'|[^\s<>|;&]+)", " ", s)
        s2 = re.sub(r"<\s*\S+", " ", s2)
        jet = _jetons(s2)
        if not jet:
            prec = sep
            continue
        while len(jet) > 1 and jet[0][0] in ("do", "then", "else", "{", "!", "time"):
            jet = jet[1:]
        cmd = canon(jet[0][0])
        args = jet[1:]
        if cmd == "sudo" and args:
            cmd, args = canon(args[0][0]), args[1:]
        out.append({"cmd": cmd, "args": args, "redir": redir, "fond": sep == "&", "tuyau": prec == "|"})
        prec = sep
    return out


def _options(args):
    return "".join(a[1:] for a, c in args if a.startswith("-") and not a.startswith("--") and not c) + \
        " ".join(a for a, c in args if a.startswith("--"))


def _chemins(args):
    return [a for a, c in args if not (a.startswith("-") and not c)]


def _joindre(cwd, arg):
    """Un argument → chemin relatif au terrain (depuis cwd), ou None s'il sort du terrain."""
    if cwd is None:
        return None
    a = arg.replace("\\", "/")
    if a.startswith(("/", "~")):
        m = re.search(r"terrain_terminagotchi(?:/(.*))?$", a)
        return (m.group(1) or "").strip("/") if m else None
    parts = [p for p in (cwd.split("/") if cwd else [])]
    for p in a.split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(p)
    return "/".join(parts)


def _parent(c):
    return c.rsplit("/", 1)[0] if "/" in c else ""


def _nom(c):
    return c.rsplit("/", 1)[-1]


def _joker(a, cite):
    return not cite and any(x in a for x in "*?[")


def _haut(xs):
    """Seulement le haut de ce qui a changé : un dossier apparu avec ce qu'il contient = un seul événement."""
    s = set(xs)
    return sorted(x for x in s if not any(y != x and x.startswith(y + "/") for y in s))


def _sous(xs, d):
    return sum(1 for x in xs if x.startswith(d + "/"))


def region(chemin):
    """(type, parcelle) d'un chemin du terrain : biome/feu/parcelle_2/rose.fleur → ("feu", "parcelle_2")."""
    p = (chemin or "").split("/")
    if len(p) >= 2 and p[0] == "biome" and p[1] in TYPES:
        return p[1], (p[2] if len(p) >= 3 else None)
    return None, None


def _est_parcelle(c):
    ty, parc = region(c)
    return bool(ty and parc and _nom(c) == parc and _PARCELLE.fullmatch(parc.lower()))


def _ev(t, cmd, **k):
    e = {"type": t, "cmd": cmd, "prio": PRIO.get(t, 2)}
    e.update(k)
    return e


# ================================================================ la règle commune
def evenements(ligne, avant, apres, code, sortie=""):
    """Les effets d'une ligne de commande (voir l'en-tête). Ne lève jamais d'exception."""
    try:
        return _evenements(ligne or "", avant or {}, apres or {}, code, sortie or "")
    except Exception:                                    # noqa: BLE001 — un effet ne casse jamais le jeu
        return []


def _evenements(ligne, avant, apres, code, sortie):
    segs = segments(ligne)
    if not segs:
        return []
    cmds = [s["cmd"] for s in segs]
    fa, fb = avant.get("f") or {}, apres.get("f") or {}
    cwd0, cwd1 = avant.get("cwd"), apres.get("cwd")
    moins_tout = [c for c in fa if c not in fb]
    plus_tout = [c for c in fb if c not in fa]
    plus, moins = _haut(plus_tout), _haut(moins_tout)
    changes = sorted(c for c in fa if c in fb and fa[c] != fb[c] and fa[c][0] == "f")
    droits = sorted(c for c in fa if c in fb and fa[c][3] != fb[c][3])
    ev = []
    principal = next((s for s in segs if s["cmd"] not in RIEN), segs[0])
    cmd0 = principal["cmd"]

    # ---- les jokers : tous les objets visés s'allument ensemble (avant l'effet)
    vises = []
    for s in segs:
        for a, cite in s["args"]:
            if _joker(a, cite):
                base = _joindre(cwd0, _parent(a) if "/" in a else ".")
                if base is None:
                    continue
                motif = _nom(a)
                vises += sorted(c for c in fa if _parent(c) == base and correspond(_nom(c), motif)
                                and (motif.startswith(".") or not _nom(c).startswith(".")))
    if vises:
        ev.append(_ev("jokers", cmd0, chemins=vises[:40], n=len(vises)))

    # ---- déplacements et copies (mv, cp) : un objet parti et un objet apparu, de même genre et même taille
    utilises_p, utilises_m = set(), set()
    if "mv" in cmds:
        for m in moins:
            g, taille = fa[m][0], fa[m][1]
            cands = [p for p in plus if p not in utilises_p and fb[p][0] == g and (g == "d" or fb[p][1] == taille)]
            cands.sort(key=lambda p: (_nom(p) != _nom(m), p))
            if cands:
                p = cands[0]
                utilises_p.add(p)
                utilises_m.add(m)
                t_ = "renomme" if _parent(p) == _parent(m) else "deplace"
                ev.append(_ev(t_, "mv", de=m, vers=p, genre=g, n=_sous(moins_tout, m) + 1))
    if "cp" in cmds or "copy" in cmds:
        sources = []
        for s in segs:
            if s["cmd"] == "cp":
                ch = _chemins(s["args"])
                for a in ch[:-1]:
                    r = _joindre(cwd0, a)
                    if r is not None and r in fa:
                        sources.append(r)
                if any(_joker(a, c) for a, c in s["args"]):
                    sources += vises
        for p in plus:
            if p in utilises_p:
                continue
            g = fb[p][0]
            cands = [s for s in sources if fa[s][0] == g and (g == "d" or fa[s][1] == fb[p][1])]
            cands.sort(key=lambda s: (_nom(s) != _nom(p), s))
            if cands:
                utilises_p.add(p)
                ev.append(_ev("copie", "cp", de=cands[0], vers=p, genre=g, n=_sous(plus_tout, p) + 1))
    # écrasés par mv/cp : un fichier qui existait et dont le contenu a été remplacé
    # ---- ce qui est apparu
    redirs = [(op, _joindre(cwd0, c)) for s in segs for op, c in s["redir"]]
    via = "touch" if "touch" in cmds else "ecrire" if redirs or "tee" in cmds else "messager" if \
        set(cmds) & {"curl", "wget"} else "caisse" if set(cmds) & CAISSE else "photo" if "git" in cmds else \
        "mkdir" if "mkdir" in cmds else "autre"
    for p in plus:
        if p in utilises_p:
            continue
        g = fb[p][0]
        if g == "d":
            ty, parc = region(p)
            parcs = sorted(x for x in [p] + [y for y in plus_tout if y.startswith(p + "/")]
                           if fb[x][0] == "d" and _est_parcelle(x))
            ev.append(_ev("dossier+", cmd0 if cmd0 != "cd" else "mkdir", chemin=p, n=_sous(plus_tout, p) + 1,
                          parcelle=bool(parcs), parcelles=parcs[:8], region=ty))
        else:
            ev.append(_ev("objet+", cmd0, chemin=p, via=via, region=region(p)[0]))
    # ---- ce qui a disparu
    for m in moins:
        if m in utilises_m:
            continue
        g = fa[m][0]
        if g == "d":
            ev.append(_ev("dossier-", cmd0, chemin=m, n=_sous(moins_tout, m) + 1, region=region(m)[0]))
        else:
            ev.append(_ev("objet-", cmd0, chemin=m, region=region(m)[0]))
    # ---- ce qui a changé
    for c in changes:
        if fa[c][1] == fb[c][1] and fa[c][2] == fb[c][2]:
            continue
        cible = next((op for op, r in redirs if r == c), None)
        if cible:
            ev.append(_ev("ecrit", "echo" if cmd0 in ("echo", "printf") else cmd0, chemin=c, mode=cible,
                          avant=fa[c][1], apres=fb[c][1]))
        elif "touch" in cmds and fa[c][1] == fb[c][1]:
            ev.append(_ev("touche", "touch", chemin=c))
        elif "tee" in cmds:
            ev.append(_ev("ecrit", "tee", chemin=c, mode=">>" if "a" in _options(
                next(s for s in segs if s["cmd"] == "tee")["args"]) else ">", avant=fa[c][1], apres=fb[c][1]))
        else:
            ev.append(_ev("modifie", cmd0, chemin=c))
    for c in droits:
        ev.append(_ev("droits", "chmod" if "chmod" in cmds else cmd0, chemin=c, avant=fa[c][3], apres=fb[c][3],
                      genre=fa[c][0]))

    # ---- se déplacer
    if cwd0 != cwd1 and ("cd" in cmds or "pushd" in cmds or "popd" in cmds):
        ev.append(_ev("cd", "cd", de=cwd0, vers=cwd1))
    fichiers = [e for e in ev if e["type"] != "jokers"]

    # ---- les commandes qui ne changent rien : seulement si elles ont réussi, sur ce qui existe vraiment
    tuyaux = len(segs) > 1 and any(s["tuyau"] for s in segs)
    if not fichiers and code == 0 and tuyaux:
        src = next((_joindre(cwd1, a) for a in _chemins(segs[0]["args"]) if _joindre(cwd1, a) in fb), None)
        ev.append(_ev("tuyau", segs[0]["cmd"], etapes=[s["cmd"] for s in segs][:6], source=src,
                      region=region(src or cwd1 or "")[0]))
    elif not fichiers and code == 0:
        for s in segs:
            c, args = s["cmd"], s["args"]
            ch = _chemins(args)
            if c == "pwd":
                ev.append(_ev("pwd", c, chemin=cwd1))
            elif c in ("ls", "tree") and not s["tuyau"]:
                cible = _joindre(cwd1, ch[0]) if ch and not _joker(*args[-1]) else cwd1
                if cible is not None and (cible == "" or (cible in fb and fb[cible][0] == "d")):
                    o = _options(args)
                    ev.append(_ev("ls", c, chemin=cible, caches="a" in o or "force" in o.lower(), long="l" in o,
                                  n=sum(1 for x in fb if _parent(x) == cible
                                        and ("a" in o or not _nom(x).startswith(".")))))
            elif c == "find":
                base = _joindre(cwd1, ch[0]) if ch and not ch[0].startswith("-") else cwd1
                motif = None
                for i, (a, _cite) in enumerate(args):
                    if a in ("-name", "-iname") and i + 1 < len(args):
                        motif = args[i + 1][0]
                if base is None:
                    continue
                trouves = sorted(x for x in fb if (base == "" or x.startswith(base + "/"))
                                 and (motif is None or correspond(
                                     _nom(x).lower() if "-iname" in [a for a, _ in args] else _nom(x),
                                     motif.lower() if "-iname" in [a for a, _ in args] else motif)))
                ev.append(_ev("find", c, chemin=base, motif=motif, chemins=trouves[:40], n=len(trouves)))
            elif c in LIRE and not s["tuyau"]:
                for a in ch[:3]:
                    r = _joindre(cwd1, a)
                    if r is not None and r in fb and fb[r][0] == "f":
                        ev.append(_ev("lire", c, chemin=r, taille=fb[r][1]))
            elif c in EMPREINTE:
                for a in ch[:3]:
                    r = _joindre(cwd1, a)
                    if r is not None and r in fb and fb[r][0] == "f":
                        ev.append(_ev("empreinte", c, chemin=r))
            elif c == "git" and ch[:1] == ["commit"]:
                ev.append(_ev("photo", "git", quoi="commit"))
            if c in RESEAU:
                ev.append(_ev("messager", c, cible=_cible_reseau(args), ok=True))
            if c in PROCESSUS or s["fond"]:
                ev.append(_ev("lucioles", c, quoi="part" if s["fond"] else "eteint" if c in (
                    "kill", "killall", "pkill") else "voir", ok=True))
    # les messagers et les processus qui ont raté : le pigeon revient avec « ? ? ? », la luciole ne bouge pas
    if not fichiers and code not in (0, None):
        if cmd0 in RESEAU:
            ev.append(_ev("messager", cmd0, cible=_cible_reseau(principal["args"]), ok=False))
        elif cmd0 in ("kill", "killall", "pkill"):
            ev.append(_ev("lucioles", cmd0, quoi="eteint", ok=False))
        elif cmd0 not in RIEN:
            ev.append(_refus(principal, cwd0, fa, sortie))
    # ---- le point d'extension (les autres mondes)
    if EXTENSIONS:
        ctx = {"ligne": ligne, "cmds": cmds, "segments": segs, "avant": avant, "apres": apres, "code": code,
               "sortie": sortie, "plus": plus, "moins": moins, "changes": changes, "deja": list(ev)}
        for f in EXTENSIONS:
            try:
                ev += list(f(ctx) or [])
            except Exception:                                # noqa: BLE001
                pass
    return grouper(ev)


def _cible_reseau(args):
    """La machine visée par ping/curl : le dernier mot qui n'est ni une option ni la valeur d'une option."""
    out, saute = "", False
    for a, _c in args:
        if saute:
            saute = False
            continue
        if a.startswith("-"):
            saute = a in ("-c", "-o", "-O", "-w", "-W", "-i", "-p", "-H", "-d", "-X", "-m", "--output", "-Count")
            continue
        out = a
    m = re.match(r"^[a-z]+://([^/:]+)", out)
    return m.group(1) if m else out


def _refus(seg, cwd, fa, sortie):
    """Le signe doux d'une commande qui a raté : cadenas (droits), « ? » (n'existe pas), tremblement (pas vide)…"""
    s = sortie.lower()
    if any(x in s for x in ("permission", "non accordée", "denied", "refusé", "accès", "unauthorizedaccess",
                            "operation not permitted", "opération non permise")):
        raison = "droits"
    elif any(x in s for x in ("not empty", "pas vide", "non vide", "directory not empty")):
        raison = "pas_vide"
    elif any(x in s for x in ("file exists", "existe déjà", "already exists", "le fichier existe")):
        raison = "existe"
    elif any(x in s for x in ("no such", "aucun fichier", "introuvable", "cannot find", "not found",
                              "n'existe pas", "does not exist", "itemnotfound")):
        raison = "introuvable"
    elif any(x in s for x in ("is a directory", "est un dossier", "est un répertoire")):
        raison = "dossier"
    elif any(x in s for x in ("command not found", "commande introuvable", "not recognized", "n'est pas reconnu")):
        raison = "commande"
    else:
        raison = "autre"
    ch = _chemins(seg["args"])
    cible = _joindre(cwd, ch[-1]) if ch else None
    if raison == "commande":
        cible = None
    return _ev("refus", seg["cmd"], raison=raison, chemin=cible, existe=bool(cible is not None and cible in fa))


def grouper(ev):
    """Les rafales : au-delà de GROUPE événements du même type, un seul effet groupé (à la place du premier)."""
    compte = {}
    for e in ev:
        compte[e["type"]] = compte.get(e["type"], 0) + 1
    out, fait = [], set()
    for e in ev:
        t_ = e["type"]
        if compte[t_] > GROUPE and t_ not in ("jokers",):
            if t_ in fait:
                continue
            fait.add(t_)
            tous = [x for x in ev if x["type"] == t_]
            ch = [x.get("chemin") or x.get("vers") for x in tous]
            regs = {x.get("region") for x in tous}
            out.append({"type": "groupe", "cmd": e["cmd"], "prio": 3, "sorte": t_, "n": len(tous),
                        "chemins": [c for c in ch if c is not None][:GROUPE],
                        "region": regs.pop() if len(regs) == 1 else None})
        else:
            out.append(e)
    return out


def filtrer(ev, niveau):
    """Le réglage « effets : tous / essentiels / aucun »."""
    if niveau == "aucun":
        return []
    if niveau == "essentiels":
        return [e for e in ev if e.get("prio", 2) >= 3]
    return list(ev)


# ================================================================ l'explication dans la bulle (2 ou 3 premières fois)
DITS_MAX = 3


def cle_dit(e):
    """La clé de langue de l'explication d'un événement (efx.dit.<sorte>), ou None."""
    t_ = e["type"] if e["type"] != "groupe" else e.get("sorte", "")
    if t_ == "refus":
        return "efx.dit.refus." + e.get("raison", "autre")
    if t_ == "ecrit":
        return "efx.dit.ecrit" + (".ajoute" if e.get("mode") == ">>" else ".efface")
    if t_ == "ls" and e.get("caches"):
        return "efx.dit.ls_a"
    if t_ in ("objet+",) and e.get("via") in ("touch", "ecrire", "messager", "caisse"):
        return "efx.dit.objet." + e["via"]
    if t_ == "dossier+" and e.get("parcelle"):
        return "efx.dit.parcelle"
    if t_ == "lucioles":
        return "efx.dit.lucioles." + e.get("quoi", "voir")
    if t_ == "messager":
        return "efx.dit.messager" + ("" if e.get("ok") else ".rate")
    return "efx.dit." + t_.replace("+", "_plus").replace("-", "_moins")


def a_dire(compteurs, ev):
    """La phrase à dire (une seule par commande) et la clé, si la créature ne l'a pas déjà dite DITS_MAX fois."""
    for e in ev:
        k = cle_dit(e)
        if k and compteurs.get(k, 0) < DITS_MAX:
            return k
    return None


# ================================================================ les vecteurs communs (Python = Kotlin = JavaScript)
def _f(*xs):
    """Une photo minuscule pour les vecteurs : ("biome/feu", "d") … → {"chemin": [genre, taille, date, droits]}."""
    out = {}
    for x in xs:
        c, g = x[0], x[1]
        out[c] = [g, x[2] if len(x) > 2 else (0 if g == "d" else 10), x[3] if len(x) > 3 else 1000,
                  x[4] if len(x) > 4 else (0o755 if g == "d" else 0o644)]
    return out


def cas_vecteurs():
    """Les cas des vecteurs communs : [(ligne, avant, apres, code, sortie)]."""
    base = _f(("biome", "d"), ("biome/feu", "d"), ("biome/feu/parcelle_1", "d"), ("biome/feu/parcelle_2", "d"),
              ("biome/plante", "d"), ("biome/plante/parcelle_1", "d"), ("biome/plante/parcelle_1/rose.fleur", "f", 4),
              ("biome/plante/parcelle_1/chene.arbre", "f", 7), ("biome/plante/parcelle_1/sapin.arbre", "f", 0),
              ("biome/plante/parcelle_2", "d"), ("biome/plante/parcelle_1/.secret", "f", 3),
              ("biome/plante/parcelle_1/mot.txt", "f", 12), ("nid", "d"))

    def avec(*xs, sans=()):
        f = dict(base)
        f.update(_f(*xs))
        for s in sans:
            for k in list(f):
                if k == s or k.startswith(s + "/"):
                    del f[k]
        return f

    P1 = "biome/plante/parcelle_1"
    C = []

    def cas(ligne, fb, code=0, sortie="", cwd0="biome", cwd1=None, fa=None):
        C.append((ligne, {"cwd": cwd0, "f": fa if fa is not None else base},
                  {"cwd": cwd0 if cwd1 is None else cwd1, "f": fb}, code, sortie))
    cas("mkdir feu/parcelle_3", avec(("biome/feu/parcelle_3", "d")))
    cas("mkdir -p glace/parcelle_1", avec(("biome/glace", "d"), ("biome/glace/parcelle_1", "d")))
    cas("mkdir feu/parcelle_3", base, 1, "mkdir: impossible de créer le répertoire « feu/parcelle_3 »: Permission non accordée")
    cas("mkdir lune/parcelle_1", base, 1, "mkdir: cannot create directory 'lune/parcelle_1': No such file or directory")
    cas("rmdir plante/parcelle_2", avec(sans=("biome/plante/parcelle_2",)))
    cas("rmdir plante/parcelle_1", base, 1, "rmdir: failed to remove 'plante/parcelle_1': Directory not empty")
    cas("rm plante/parcelle_1/rose.fleur", avec(sans=(P1 + "/rose.fleur",)))
    cas("rm -r plante", avec(sans=("biome/plante",)))
    cas("touch plante/parcelle_2/sapin.arbre", avec(("biome/plante/parcelle_2/sapin.arbre", "f", 0)))
    cas("touch sapin.arbre", avec((P1 + "/sapin.arbre", "f", 0, 5000)), cwd0=P1)
    cas("mv chene.arbre ../parcelle_2/", avec(("biome/plante/parcelle_2/chene.arbre", "f", 7),
                                             sans=(P1 + "/chene.arbre",)), cwd0=P1)
    cas("mv rose.fleur tulipe.fleur", avec((P1 + "/tulipe.fleur", "f", 4), sans=(P1 + "/rose.fleur",)), cwd0=P1)
    cas("cp chene.arbre ../parcelle_2/", avec(("biome/plante/parcelle_2/chene.arbre", "f", 7)), cwd0=P1)
    cas("rm *.fleur", avec(sans=(P1 + "/rose.fleur",)), cwd0=P1)
    cas("rm *.arbre", avec(sans=(P1 + "/chene.arbre", P1 + "/sapin.arbre")), cwd0=P1)
    cas("cd feu", base, cwd1="biome/feu")
    cas("cd ..", base, cwd0="biome/feu", cwd1="biome")
    cas("cd lune", base, 1, "bash: cd: lune: Aucun fichier ou dossier de ce type")
    cas("pwd", base, cwd0=P1)
    cas("ls", base, cwd0=P1)
    cas("ls -a", base, cwd0=P1)
    cas("ls -la plante/parcelle_1", base)
    cas('find . -name "*.arbre"', base)
    cas("cat mot.txt", base, cwd0=P1)
    cas("cat absent.txt", base, 1, "cat: absent.txt: No such file or directory", cwd0=P1)
    cas("echo Bonjour > mot.txt", avec((P1 + "/mot.txt", "f", 8, 2000)), cwd0=P1)
    cas("echo Encore >> mot.txt", avec((P1 + "/mot.txt", "f", 19, 2000)), cwd0=P1)
    cas("echo Salut > neuf.txt", avec((P1 + "/neuf.txt", "f", 6)), cwd0=P1)
    cas("chmod a-w ../parcelle_2", avec(("biome/plante/parcelle_2", "d", 0, 1000, 0o555)), cwd0=P1)
    cas("touch ../parcelle_2/x.fleur", base, 1, "touch: cannot touch '../parcelle_2/x.fleur': Permission denied",
        cwd0=P1)
    cas("chmod u+x mot.txt", avec((P1 + "/mot.txt", "f", 12, 1000, 0o744)), cwd0=P1)
    cas("Remove-Item rose.fleur", avec(sans=(P1 + "/rose.fleur",)), cwd0=P1)
    cas("New-Item -ItemType Directory feu/parcelle_3", avec(("biome/feu/parcelle_3", "d")))
    cas("Set-Location feu", base, cwd1="biome/feu")
    cas("for i in 1 2 3 4 5 6 7 8; do touch f$i.fleur; done",
        avec(*[(f"{P1}/f{i}.fleur", "f", 0) for i in range(1, 9)]), cwd0=P1)
    cas("clear", base)
    cas("ps", base)
    cas("sleep 300 &", base)
    cas("kill 9999", base, 1, "kill: (9999) - No such process")
    cas("ping -c 1 eau", base)
    cas("ping -c 1 lune", base, 2, "ping: lune: Name or service not known")
    cas("curl -o meteo.txt http://ciel/meteo.txt", avec((P1 + "/meteo.txt", "f", 30)), cwd0=P1)
    cas("sha256sum rose.fleur", base, cwd0=P1)
    cas("git commit -m jardin", base)
    cas("cat mot.txt | grep a | sort | wc -l", base, cwd0=P1)
    cas("tar -czf sac.tar.gz rose.fleur", avec((P1 + "/sac.tar.gz", "f", 50)), cwd0=P1)
    cas("cd ~/terrain_terminagotchi/nid", base, cwd1="nid")
    cas("ls /etc", base, cwd0=None, cwd1=None)
    return C


def vecteurs():
    return [{"ligne": l, "avant": a, "apres": b, "code": c, "sortie": s, "attendu": evenements(l, a, b, c, s),
             "dit": [cle_dit(e) for e in evenements(l, a, b, c, s)]}
            for l, a, b, c, s in cas_vecteurs()]
