"""Le terminal du jeu : le petit git (le même que celui du téléphone, PetitGit.kt, porté en Python).

L'ordinateur n'a pas forcément git (Windows) : le terminal du jeu en a un petit, HONNÊTE et testé. Il range ses photos
à la façon de git (blobs, arbres, commits) et calcule les MÊMES empreintes SHA-1 que le vrai git ; il écrit les mêmes
messages (en anglais, comme git avec LC_ALL=C) pour ce que font les leçons : init, config, status, add, commit, log
(--oneline, --graph, -S, -p), diff (--staged), show, restore, checkout, switch, branch, merge (et ses conflits), clone
et pull entre dossiers du terrain, remote -v, hash-object, cat-file, rev-parse, rev-list, symbolic-ref. Vérifié contre
le VRAI git par pc/outils/test_terminal.py --git (vecteurs donnees/temps/vecteurs.json, faits par
pc/outils/vecteurs_temps.py), comme PetitGit.kt par tests/jvm/Temps.kt.

Ce qu'il ne fait pas (il le dit) : push, remote add, fetch d'un serveur, rebase, stash, tags, sous-modules, éditeur
(il faut -m), --global (chaque album garde son nom d'exemple). Il ne travaille QUE dans le terrain : ses données sont
dans <dépôt>/.git/petit_git.json (le même fichier que sur le téléphone).
"""
import hashlib
import heapq
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

FICHIER = "petit_git.json"
VIDE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"        # l'arbre vide de git
ETAT = {"horloge": None, "afficher": lambda p: p}          # (les tests fixent l'heure et la façon de montrer les chemins)


def t(cle, **p):
    from ..langue import t as tr
    return tr(cle, **p)


class Res:
    def __init__(self, texte, code=0):
        self.texte, self.code = texte, code


def horloge():
    if ETAT["horloge"]:
        return ETAT["horloge"]()
    ts = int(time.time())
    off = int(datetime.now().astimezone().utcoffset().total_seconds() // 60)
    return ts, off


# ================================================================ les empreintes
def _sha1(b):
    return hashlib.sha1(b).hexdigest()


def blob_sha(octets):
    if isinstance(octets, str):
        octets = octets.encode("utf-8")
    return _sha1(b"blob " + str(len(octets)).encode() + b"\0" + octets)


def sha_objet(genre, corps):
    return _sha1(genre.encode() + b" " + str(len(corps)).encode() + b"\0" + corps)


# ================================================================ le dépôt
class Depot:
    def __init__(self, racine):
        self.racine = Path(racine)
        self.git_dir = self.racine / ".git"
        self.j = {}

    def charger(self):
        try:
            self.j = json.loads((self.git_dir / FICHIER).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.j = {}
        for k in ("objets", "branches", "index", "config", "remotes", "amont"):
            if not isinstance(self.j.get(k), dict):
                self.j[k] = {}
        if not isinstance(self.j.get("head"), dict):
            self.j["head"] = {"ref": "master"}
        return self

    def sauver(self):
        self.git_dir.mkdir(parents=True, exist_ok=True)
        (self.git_dir / FICHIER).write_text(json.dumps(self.j, ensure_ascii=False), encoding="utf-8")
        try:       # (pour les curieux qui font cat .git/HEAD, ls .git/refs/heads : la même chose que le vrai git)
            (self.git_dir / "HEAD").write_text(f"ref: refs/heads/{self.ref_head()}\n" if self.ref_head() else
                                              f"{self.head()}\n", encoding="utf-8")
            heads = self.git_dir / "refs" / "heads"
            heads.mkdir(parents=True, exist_ok=True)
            for b, h in self.branches.items():
                if h and "/" not in b:
                    (heads / b).write_text(h + "\n", encoding="utf-8")
            for f in heads.iterdir():
                if f.is_file() and f.name not in self.branches:
                    f.unlink()
            for nom, val in (("MERGE_HEAD", (self.fusion or {}).get("tete")), ("MERGE_MSG", (self.fusion or {}).get("msg"))):
                f = self.git_dir / nom
                if val:
                    f.write_text(val + "\n", encoding="utf-8")
                elif f.exists():
                    f.unlink()
        except OSError:
            pass

    @property
    def objets(self):
        return self.j["objets"]

    @property
    def branches(self):
        return self.j["branches"]

    @property
    def index(self):
        return self.j["index"]

    @property
    def config(self):
        return self.j["config"]

    @property
    def remotes(self):
        return self.j["remotes"]

    @property
    def amont(self):
        return self.j["amont"]

    @property
    def fusion(self):
        f = self.j.get("fusion")
        return f if isinstance(f, dict) else None

    def ref_head(self):
        return self.j["head"].get("ref") or None

    def head(self):
        r = self.ref_head()
        if r is not None:
            return self.branches.get(r) or None
        return self.j["head"].get("detache") or None

    def objet(self, h):
        return self.objets.get(h)

    def blob(self, h):
        o = self.objet(h)
        return o.get("c", "") if o else ""

    def commit(self, h):
        o = self.objet(h) if h else None
        return o if o and o.get("t") == "commit" else None

    def parents(self, h):
        c = self.commit(h)
        return list(c.get("parents", [])) if c else []

    def conflits(self):
        f = self.fusion
        return list(f.get("conflits", [])) if f else []

    def ajouter_blob(self, texte):
        h = blob_sha(texte)
        if h not in self.objets:
            self.objets[h] = {"t": "blob", "c": texte}
        return h

    def ecrire_arbre(self, fichiers):
        ici, sous = {}, {}
        for p, h in fichiers.items():
            k = p.find("/")
            if k < 0:
                ici[p] = h
            else:
                sous.setdefault(p[:k], {})[p[k + 1:]] = h
        entrees = [("100644", n, h) for n, h in ici.items()] + [("40000", n, self.ecrire_arbre(f)) for n, f in sous.items()]
        entrees.sort(key=lambda e: (e[1] + "/" if e[0] == "40000" else e[1]).encode("utf-8"))
        corps = b"".join(f"{m} {n}\0".encode("utf-8") + bytes.fromhex(h) for m, n, h in entrees)
        h = sha_objet("tree", corps)
        if h not in self.objets:
            self.objets[h] = {"t": "tree", "e": [list(e) for e in entrees]}
        return h

    def aplatir(self, arbre, prefixe=""):
        out = {}
        o = self.objet(arbre) if arbre else None
        if not o:
            return out
        for m, n, h in o.get("e", []):
            if m == "40000":
                out.update(self.aplatir(h, prefixe + n + "/"))
            else:
                out[prefixe + n] = h
        return out

    def arbre_de(self, c):
        x = self.commit(c) if c else None
        return x.get("tree") if x else None

    def fichiers_de(self, c):
        return self.aplatir(self.arbre_de(c))

    def ecrire_commit(self, arbre, parents, auteur, committer, msg):
        s = f"tree {arbre}\n" + "".join(f"parent {p}\n" for p in parents) + f"author {auteur}\ncommitter {committer}\n\n" + msg
        h = sha_objet("commit", s.encode("utf-8"))
        if h not in self.objets:
            self.objets[h] = {"t": "commit", "tree": arbre, "parents": list(parents), "author": auteur,
                              "committer": committer, "msg": msg}
        return h

    def corps_commit(self, h):
        c = self.commit(h)
        if not c:
            return ""
        return (f"tree {c.get('tree')}\n" + "".join(f"parent {p}\n" for p in self.parents(h)) +
                f"author {c.get('author')}\ncommitter {c.get('committer')}\n\n" + c.get("msg", ""))

    # -------------------------------------------- la copie de travail (les vrais fichiers du dossier)
    def travail(self):
        out = {}
        for d, ds, fs in os.walk(self.racine):
            ds[:] = sorted(x for x in ds if not (Path(d) == self.racine and x == ".git"))
            for f in fs:
                p = Path(d) / f
                out[p.relative_to(self.racine).as_posix()] = p
        return dict(sorted(out.items()))

    def lire(self, p):
        f = self.racine / p
        if f.is_file():
            try:
                return f.read_bytes().decode("utf-8", "replace")
            except OSError:
                return None
        return None

    def sha_travail(self, p):
        f = self.racine / p
        if f.is_file():
            try:
                return blob_sha(f.read_bytes())
            except OSError:
                return None
        return None

    def poser(self, p, blob):
        f = self.racine / p
        if blob is None:
            try:
                f.unlink()
            except OSError:
                pass
            d = f.parent
            while d != self.racine and d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError:
                    break
                d = d.parent
            return
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "w", encoding="utf-8", newline="") as x:
            x.write(self.blob(blob))

    def ignore(self, p):
        motifs = [l.strip() for l in (self.lire(".gitignore") or "").splitlines()]
        motifs = [m for m in motifs if m and not m.startswith("#") and not m.startswith("!")]
        nom = p.rsplit("/", 1)[-1]
        for m in motifs:
            rx = glob(m.rstrip("/").lstrip("/"))
            if rx.fullmatch(nom) or rx.fullmatch(p) or any(rx.fullmatch(x) for x in p.split("/")[:-1]):
                return True
        return False

    def cfg(self, k):
        return self.config.get(k) or None


def glob(m):
    return re.compile("".join("[^/]*" if c == "*" else "[^/]" if c == "?" else (c if c.isalnum() else "\\" + c) for c in m))


def est_depot(d):
    return (Path(d) / ".git" / FICHIER).is_file()


def trouver(ici, terrain):
    """Le dépôt du dossier ici (ou d'un dossier parent, sans sortir du terrain), ou None."""
    try:
        d = Path(ici).resolve()
        tr = Path(terrain).resolve()
    except OSError:
        return None
    while d == tr or str(d).startswith(str(tr) + os.sep):
        if est_depot(d):
            return Depot(d).charger()
        if d.parent == d:
            break
        d = d.parent
    return None


def ouvrir(d):
    return Depot(d).charger() if est_depot(d) else None


# ================================================================ les révisions : HEAD, HEAD~1, main, 6b4cd1e, X^, origin/main
def resoudre(dep, rev):
    r = rev.strip()
    if r.endswith("^{tree}"):
        h = resoudre(dep, r[:-7])
        return dep.arbre_de(h) if h else None
    if r.endswith("^{commit}"):
        h = resoudre(dep, r[:-9])
        return h if h and dep.commit(h) else None
    if r.startswith("refs/heads/"):
        r = r[11:]
    m = re.match(r"^(.*?)((?:[~^]\d*)*)$", r)
    if not m:
        return None
    base = m.group(1)
    h = None
    if base in ("HEAD", "@"):
        h = dep.head()
    elif base == "MERGE_HEAD":
        h = (dep.fusion or {}).get("tete") or None
    elif base == "FETCH_HEAD":
        h = dep.j.get("fetch_head") or None
    elif base in dep.branches:
        h = dep.branches[base]
    elif "/" in base and base.split("/", 1)[0] in dep.remotes:
        h = (dep.remotes[base.split("/", 1)[0]].get("refs") or {}).get(base.split("/", 1)[1]) or None
    elif len(base) >= 4 and re.fullmatch(r"[0-9a-fA-F]+", base):
        c = [k for k in dep.objets if k.startswith(base.lower())]
        h = c[0] if len(c) == 1 else None
    if h is None:
        return None
    for s in re.finditer(r"[~^]\d*", m.group(2)):
        n = int(s.group()[1:] or "1")
        if s.group()[0] == "~":
            for _ in range(n):
                ps = dep.parents(h) if h else []
                h = ps[0] if ps else None
        elif n != 0:
            ps = dep.parents(h) if h else []
            h = ps[n - 1] if len(ps) >= n else None
        if h is None:
            return None
    return h


# ================================================================ les différences (Myers, comme git)
def lignes(texte):
    if not texte:
        return []
    l = texte.split("\n")
    return l[:-1] if texte.endswith("\n") else l


def communes(a, b):
    n, m = len(a), len(b)
    mx = n + m
    v = [0] * (2 * mx + 2)
    traces = []
    fin = -1
    for d in range(mx + 1):
        traces.append(list(v))
        k = -d
        trouve = False
        while k <= d:
            if k == -d or (k != d and v[mx + k - 1] < v[mx + k + 1]):
                x = v[mx + k + 1]
            else:
                x = v[mx + k - 1] + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[mx + k] = x
            if x >= n and y >= m:
                fin = d
                trouve = True
                break
            k += 2
        if trouve:
            break
    paires = []
    x, y = n, m
    for d in range(fin, 0, -1):
        vv = traces[d]
        k = x - y
        pk = k + 1 if (k == -d or (k != d and vv[mx + k - 1] < vv[mx + k + 1])) else k - 1
        px = vv[mx + pk]
        py = px - pk
        while x > px and y > py:
            x -= 1
            y -= 1
            paires.append((x, y))
        x, y = px, py
    while x > 0 and y > 0:
        x -= 1
        y -= 1
        paires.append((x, y))
    return list(reversed(paires))


def blocs(a, b):
    out = []
    i = j = 0
    for x, y in communes(a, b) + [(len(a), len(b))]:
        if x > i or y > j:
            out.append((i, x, j, y))
        i, j = x + 1, y + 1
    return out


def nb_plus_moins(a, b):
    p = mo = 0
    for c in blocs(lignes(a), lignes(b)):
        mo += c[1] - c[0]
        p += c[3] - c[2]
    return p, mo


def _fonction(a, avant):
    for i in range(avant - 1, -1, -1):
        x = a[i]
        if x and ((x[0].isalpha() and ord(x[0]) < 128) or x[0] in "_$"):
            x = x.rstrip()
            return " " + (x[:80] if len(x) > 80 else x)
    return ""


def unifie(ta, tb):
    a, b = lignes(ta), lignes(tb)
    cs = blocs(a, b)
    if not cs:
        return []
    out = []
    ctx = 3
    g = 0
    while g < len(cs):
        h = g
        while h + 1 < len(cs) and cs[h + 1][0] - cs[h][1] <= 2 * ctx:
            h += 1
        a0 = max(0, cs[g][0] - ctx)
        a1 = min(len(a), cs[h][1] + ctx)
        b0 = cs[g][2] - (cs[g][0] - a0)
        b1 = cs[h][3] + (a1 - cs[h][1])

        def plage(s, n):
            return f"{s + 1}" if n == 1 else (f"{s},0" if n == 0 else f"{s + 1},{n}")
        out.append(f"@@ -{plage(a0, a1 - a0)} +{plage(b0, b1 - b0)} @@" + _fonction(a, a0))
        i = a0
        for k in range(g, h + 1):
            c = cs[k]
            while i < c[0]:
                out.append(" " + a[i])
                i += 1
            for x in range(c[0], c[1]):
                out.append("-" + a[x])
                if x == len(a) - 1 and not ta.endswith("\n"):
                    out.append("\\ No newline at end of file")
            for y in range(c[2], c[3]):
                out.append("+" + b[y])
                if y == len(b) - 1 and not tb.endswith("\n"):
                    out.append("\\ No newline at end of file")
            i = c[1]
        while i < a1:
            out.append(" " + a[i])
            if i == len(a) - 1 and not ta.endswith("\n") and not tb.endswith("\n"):
                out.append("\\ No newline at end of file")
            i += 1
        g = h + 1
    return out


def diff_git(dep, avant, apres, textes_apres=None):
    out = []
    for p in sorted(set(avant) | set(apres), key=lambda s: s.encode("utf-8")):
        ha, hb = avant.get(p), apres.get(p)
        if ha == hb:
            continue
        ta = dep.blob(ha) if ha else ""
        tb = (textes_apres or {}).get(p) if textes_apres and p in textes_apres else (dep.blob(hb) if hb else "")
        out.append(f"diff --git a/{p} b/{p}")
        if ha is None:
            out += ["new file mode 100644", f"index 0000000..{hb[:7]}"]
        elif hb is None:
            out += ["deleted file mode 100644", f"index {ha[:7]}..0000000"]
        else:
            out.append(f"index {ha[:7]}..{hb[:7]} 100644")
        u = unifie(ta, tb)
        if u:
            out.append("--- /dev/null" if ha is None else f"--- a/{p}")
            out.append("+++ /dev/null" if hb is None else f"+++ b/{p}")
            out += u
    return out


def resume(fichiers, plus, moins):
    s = f" {fichiers} file{'' if fichiers == 1 else 's'} changed"
    if plus > 0 or moins == 0:
        s += f", {plus} insertion{'' if plus == 1 else 's'}(+)"
    if moins > 0 or plus == 0:
        s += f", {moins} deletion{'' if moins == 1 else 's'}(-)"
    return s


def diffstat(dep, avant, apres, modes):
    ch = [p for p in sorted(set(avant) | set(apres), key=lambda s: s.encode("utf-8")) if avant.get(p) != apres.get(p)]
    if not ch:
        return []
    nb = {p: nb_plus_moins(dep.blob(avant[p]) if avant.get(p) else "", dep.blob(apres[p]) if apres.get(p) else "")
          for p in ch}
    large = max(len(p) for p in ch)
    max_n = max(a + b for a, b in nb.values())
    lnum = len(str(max_n))
    place = max(1, 79 - (large + 3 + lnum + 1) - 1)
    out = []
    for p in ch:
        pl, mo = nb[p]
        a, b = pl, mo
        if max_n > place:
            a = 0 if pl == 0 else max(1, pl * place // max_n)
            b = 0 if mo == 0 else max(1, mo * place // max_n)
        out.append(f" {p.ljust(large)} | {str(pl + mo).rjust(lnum)}" + (" " + "+" * a + "-" * b if pl + mo > 0 else ""))
    out.append(resume(len(ch), sum(x[0] for x in nb.values()), sum(x[1] for x in nb.values())))
    if modes:
        for p in ch:
            if avant.get(p) is None:
                out.append(f" create mode 100644 {p}")
            if apres.get(p) is None:
                out.append(f" delete mode 100644 {p}")
    return out


# ================================================================ la fusion ligne à ligne (diff3, « zélée » comme git)
def fusionner(base, nous, eux, nom_eux):
    o, a, b = lignes(base), lignes(nous), lignes(eux)

    def changes(x):
        return [(c[0], c[1], x[c[2]:c[3]]) for c in blocs(o, x)]
    ca, cb = changes(a), changes(b)
    tous = sorted([(0, c) for c in ca] + [(1, c) for c in cb], key=lambda e: (e[1][0], e[1][1]))
    out = []
    conflit = False
    i = pos = 0
    while i < len(tous):
        j = i
        fin = tous[i][1][1]
        while j + 1 < len(tous) and tous[j + 1][1][0] <= fin:
            j += 1
            fin = max(fin, tous[j][1][1])
        debut = tous[i][1][0]
        while pos < debut:
            out.append(o[pos])
            pos += 1
        groupe = tous[i:j + 1]

        def cote(c, lst):
            bl = [x[1] for x in groupe if x[0] == c]
            if not bl:
                return o[debut:fin]
            r, p = [], debut
            for x0, x1, xl in bl:
                while p < x0:
                    r.append(o[p])
                    p += 1
                r += xl
                p = x1
            while p < fin:
                r.append(o[p])
                p += 1
            return r
        va, vb = cote(0, a), cote(1, b)
        if va == vb or all(x[0] == 0 for x in groupe):
            out += va
        elif all(x[0] == 1 for x in groupe):
            out += vb
        else:
            d = 0
            while d < len(va) and d < len(vb) and va[d] == vb[d]:
                d += 1
            f = 0
            while f < len(va) - d and f < len(vb) - d and va[len(va) - 1 - f] == vb[len(vb) - 1 - f]:
                f += 1
            out += va[:d]
            out.append("<<<<<<< HEAD")
            out += va[d:len(va) - f]
            out.append("=======")
            out += vb[d:len(vb) - f]
            out.append(f">>>>>>> {nom_eux}")
            out += va[len(va) - f:]
            conflit = True
        pos = fin
        i = j + 1
    while pos < len(o):
        out.append(o[pos])
        pos += 1
    return ("\n".join(out) + "\n" if out else ""), conflit


# ================================================================ les commandes
def court(h):
    return (h or "")[:7]


def sujet(dep, h):
    c = dep.commit(h)
    return (c.get("msg", "").splitlines() or [""])[0] if c else ""


def ident(ts, tz, nom, mail):
    s = "-" if tz < 0 else "+"
    a = abs(tz)
    return f"{nom} <{mail}> {ts} {s}{a // 60:02d}{a % 60:02d}"


JOURS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MOIS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def date_git(idt):
    m = re.search(r"> (\d+) ([+-])(\d\d)(\d\d)$", idt)
    if not m:
        return ""
    off = (int(m.group(3)) * 60 + int(m.group(4))) * (-1 if m.group(2) == "-" else 1)
    d = datetime.fromtimestamp(int(m.group(1)), timezone(timedelta(minutes=off)))
    return f"{JOURS[d.weekday()]} {MOIS[d.month - 1]} {d.day} {d:%H:%M:%S} {d.year} {m.group(2)}{m.group(3)}{m.group(4)}"


def auteur_nom(idt):
    return idt.split(" <", 1)[0]


def auteur_mail(idt):
    return idt.split("<", 1)[1].split(">", 1)[0] if "<" in idt else ""


DECORER = {"oui": True}          # (git : log.decorate=auto — pas de décorations quand la sortie va dans un tuyau)


def decorations(dep, h):
    if not DECORER["oui"]:
        return ""
    noms = [b for b in sorted(dep.branches) if dep.branches[b] == h]
    for r in sorted(dep.remotes):
        o = dep.remotes[r]
        refs = o.get("refs") or {}
        liste = [(k, v) for k, v in refs.items()]
        if o.get("head"):
            liste.append(("HEAD", refs.get(o["head"], "")))
        for b, x in sorted(liste):
            if x == h:
                noms.append(f"{r}/{b}")
    noms.reverse()
    rh = dep.ref_head()
    if dep.head() == h:
        if rh is not None:
            if rh in noms:
                noms.remove(rh)
            noms.insert(0, f"HEAD -> {rh}")
        else:
            noms.insert(0, "HEAD")
    return " (" + ", ".join(noms) + ")" if noms else ""


def _date_commit(dep, h):
    m = re.search(r"> (\d+) ", (dep.commit(h) or {}).get("committer", ""))
    return int(m.group(1)) if m else 0


def ordre(dep, departs):
    """Les photos depuis des points de départ, dans l'ordre de git log (date, puis ordre d'arrivée)."""
    n = 0
    vus = set()
    tas = []
    for d in departs:
        if d not in vus:
            vus.add(d)
            heapq.heappush(tas, (-_date_commit(dep, d), n, d))
            n += 1
    out = []
    while tas:
        _d, _n, h = heapq.heappop(tas)
        out.append(h)
        for p in dep.parents(h):
            if p not in vus:
                vus.add(p)
                heapq.heappush(tas, (-_date_commit(dep, p), n, p))
                n += 1
    return out


def ordre_graphe(dep, departs):
    tous = ordre(dep, departs)
    enfants = {}
    for h in tous:
        for p in dep.parents(h):
            enfants[p] = enfants.get(p, 0) + 1
    pile = []
    vus_d = []
    for d in departs:
        if d not in vus_d:
            vus_d.append(d)
    for d in reversed(vus_d):
        if enfants.get(d, 0) == 0 and d not in pile:
            pile.append(d)
    out = []
    while pile:
        h = pile.pop()
        out.append(h)
        for p in dep.parents(h):
            enfants[p] = enfants.get(p, 1) - 1
            if enfants[p] == 0:
                pile.append(p)
    return out


def graphe(dep, liste, texte):
    out = []
    cols = []
    for h in liste:
        c = cols.index(h) if h in cols else -1
        if c < 0:
            cols.append(h)
            c = len(cols) - 1
        ps = dep.parents(h)
        tete = " ".join("*" if k == c else "|" for k in range(len(cols)))
        ls = texte(h)
        if len(ps) > 1:
            out.append(f"{tete}   " + ls[0])
            cols[c] = ps[0]
            cols.insert(c + 1, ps[1])
            out.append("| " * c + "|\\  ")
            for l in ls[1:]:
                out.append(" ".join("|" for _ in cols) + ("" if not l else " " + l))
            continue
        out.append(f"{tete} " + ls[0])
        for l in ls[1:]:
            out.append(" ".join("|" for _ in cols) + ("" if not l else " " + l))
        if not ps:
            del cols[c]
            continue
        cols[c] = ps[0]
        autre = next((k for k in range(len(cols)) if k != c and cols[k] == ps[0]), None)
        if autre is not None:
            haut = max(c, autre)
            out.append(" ".join("|" for _ in range(haut)) + "/" + "  " + "".join(" /" for _ in range(haut + 1, len(cols))))
            del cols[haut]
    return out


# -------------------------------------------- l'état du dossier (git status)
def etat(dep):
    tete = dep.fichiers_de(dep.head())
    idx = dict(dep.index)
    conf = set(dep.conflits())
    prets = []
    for p in sorted(set(tete) | set(idx), key=lambda s: s.encode("utf-8")):
        if p in conf:
            continue
        a, b = tete.get(p), idx.get(p)
        if a is None and b is not None:
            prets.append(("new file", p))
        elif a is not None and b is None:
            prets.append(("deleted", p))
        elif a != b:
            prets.append(("modified", p))
    pas = []
    for p in sorted(idx, key=lambda s: s.encode("utf-8")):
        if p in conf:
            continue
        s = dep.sha_travail(p)
        if s is None:
            pas.append(("deleted", p))
        elif s != idx[p]:
            pas.append(("modified", p))
    non = set()
    for p in dep.travail():
        if p in idx or dep.ignore(p):
            continue
        k = p.find("/")
        if k > 0 and not any(x.startswith(p[:k + 1]) for x in idx):
            non.add(p[:k + 1])
        else:
            non.add(p)
    return prets, pas, sorted(non, key=lambda s: s.encode("utf-8")), sorted(conf, key=lambda s: s.encode("utf-8"))


def _suivi(dep):
    b = dep.ref_head()
    if b is None:
        return []
    up = dep.amont.get(b)
    if not up:
        return []
    h = resoudre(dep, up)
    moi = dep.head()
    if not h or not moi:
        return []
    chez_moi, chez_eux = set(ordre(dep, [moi])), set(ordre(dep, [h]))
    av, re_ = len(chez_moi - chez_eux), len(chez_eux - chez_moi)
    if av == 0 and re_ == 0:
        return [f"Your branch is up to date with '{up}'."]
    if re_ == 0:
        return [f"Your branch is ahead of '{up}' by {av} commit{'s' if av > 1 else ''}.",
                "  (use \"git push\" to publish your local commits)"]
    if av == 0:
        return [f"Your branch is behind '{up}' by {re_} commit{'s' if re_ > 1 else ''}, and can be fast-forwarded.",
                "  (use \"git pull\" to update your local branch)"]
    return [f"Your branch and '{up}' have diverged,", f"and have {av} and {re_} different commits each, respectively.",
            "  (use \"git pull\" if you want to integrate the remote branch with yours)"]


def status(dep, court_=False, porcelaine=False):
    prets, pas, non, conf = etat(dep)
    if court_ or porcelaine:
        l = {}
        for k, p in prets:
            l[p] = {"new file": "A", "deleted": "D"}.get(k, "M") + " "
        for k, p in pas:
            l[p] = (l.get(p, " ")[:1]) + ("D" if k == "deleted" else "M")
        for p in conf:
            l[p] = "UU"
        return "\n".join([f"{v} {k}" for k, v in sorted(l.items(), key=lambda e: e[0].encode("utf-8"))] +
                         [f"?? {p}" for p in non])
    out = []
    rh = dep.ref_head()
    out.append(f"On branch {rh}" if rh is not None else f"HEAD detached at {court(dep.head())}")
    s = _suivi(dep)
    if s:
        out += s + [""]
    initial = dep.head() is None
    if initial:
        out += ["", "No commits yet", ""]
    if dep.fusion is not None:
        if conf:
            out += ["You have unmerged paths.", "  (fix conflicts and run \"git commit\")",
                    "  (use \"git merge --abort\" to abort the merge)", ""]
        else:
            out += ["All conflicts fixed but you are still merging.", "  (use \"git commit\" to conclude merge)", ""]

    def ent(k, p):
        return "\t" + f"{k}:".ljust(17 if (k.startswith("both") or k.endswith("by us") or k.endswith("by them")) else 12) + p
    if prets:
        out.append("Changes to be committed:")
        out.append("  (use \"git rm --cached <file>...\" to unstage)" if initial else
                   "  (use \"git restore --staged <file>...\" to unstage)")
        out += [ent(k, p) for k, p in prets]
        out.append("")
    if conf:
        out += ["Unmerged paths:", "  (use \"git add <file>...\" to mark resolution)"]
        out += [ent("both modified", p) for p in conf]
        out.append("")
    if pas:
        out.append("Changes not staged for commit:")
        out.append("  (use \"git add/rm <file>...\" to update what will be committed)" if any(k == "deleted" for k, _ in pas)
                   else "  (use \"git add <file>...\" to update what will be committed)")
        out.append("  (use \"git restore <file>...\" to discard changes in working directory)")
        out += [ent(k, p) for k, p in pas]
        out.append("")
    if non:
        out += ["Untracked files:", "  (use \"git add <file>...\" to include in what will be committed)"]
        out += [f"\t{p}" for p in non]
        out.append("")
    if not prets:
        if pas or conf:
            out.append("no changes added to commit (use \"git add\" and/or \"git commit -a\")")
        elif non:
            out.append("nothing added to commit but untracked files present (use \"git add\" to track)")
        elif initial:
            out.append("nothing to commit (create/copy files and use \"git add\" to track)")
        else:
            out.append("nothing to commit, working tree clean")
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


# -------------------------------------------- poser une photo dans le dossier (switch, checkout, merge, pull)
def _ecrases(dep, a, b):
    fa, fb = dep.fichiers_de(a), dep.fichiers_de(b)
    idx = dict(dep.index)
    out = []
    for p in sorted(set(fa) | set(fb) | set(idx), key=lambda s: s.encode("utf-8")):
        if fa.get(p) != fb.get(p) and (idx.get(p) != fa.get(p) or (idx.get(p) is not None and dep.sha_travail(p) != idx.get(p))
                                       or (idx.get(p) is None and dep.sha_travail(p) is not None and fb.get(p) is not None)):
            out.append(p)
    return out


def _aller_a(dep, a, b):
    fa, fb = dep.fichiers_de(a), dep.fichiers_de(b)
    for p in set(fa) | set(fb):
        if fa.get(p) != fb.get(p):
            dep.poser(p, fb.get(p))
            if fb.get(p) is None:
                dep.index.pop(p, None)
            else:
                dep.index[p] = fb[p]


def _modifies_gardes(dep):
    prets, pas, _n, _c = etat(dep)
    return [f"M\t{p}" for p in sorted({p for _k, p in prets} | {p for _k, p in pas}, key=lambda s: s.encode("utf-8"))]


def _basculer(dep, cible, branche, nouvelle, depuis):
    avant = dep.head()
    bloque = _ecrases(dep, avant, cible)
    if bloque:
        return Res("error: Your local changes to the following files would be overwritten by checkout:\n" +
                   "\n".join(f"\t{p}" for p in bloque) + "\nPlease commit your changes or stash them before you switch branches.\nAborting", 1)
    etait_detache = dep.ref_head() is None
    ancien = dep.ref_head() or avant
    gardes = _modifies_gardes(dep)
    _aller_a(dep, avant, cible)
    l = []
    if etait_detache and avant is not None and avant != cible:
        l.append(f"Previous HEAD position was {court(avant)} {sujet(dep, avant)}")
    l += gardes
    if branche is not None:
        if nouvelle:
            if cible is None:
                dep.branches.pop(branche, None)
            else:
                dep.branches[branche] = cible
        l.append(f"Switched to a new branch '{branche}'" if nouvelle else
                 (f"Already on '{branche}'" if dep.ref_head() == branche else f"Switched to branch '{branche}'"))
        dep.j["head"] = {"ref": branche}
    else:
        dep.j["head"] = {"detache": cible}
        l.append(f"Note: switching to '{depuis}'.\n\nYou are in 'detached HEAD' state. You can look around, make experimental\n"
                 "changes and commit them, and you can discard any commits you make in this\n"
                 "state without impacting any branches by switching back to a branch.\n\nIf you want to create a new branch to retain commits you create, you may\n"
                 "do so (now or later) by using -c with the switch command. Example:\n\n  git switch -c <new-branch-name>\n\nOr undo this operation with:\n\n  git switch -\n\n"
                 f"Turn off this advice by setting config variable advice.detachedHead to false\n\nHEAD is now at {court(cible)} {sujet(dep, cible)}")
    if ancien is not None:
        dep.j["precedent"] = ancien
    dep.sauver()
    return Res("\n".join(l))


# -------------------------------------------- la photo (commit)
def _identite(dep):
    if dep.cfg("user.email") is not None and dep.cfg("user.name") is not None:
        return None
    return Res("Author identity unknown\n\n*** Please tell me who you are.\n\nRun\n\n  git config --global user.email \"you@example.com\"\n"
               "  git config --global user.name \"Your Name\"\n\nto set your account's default identity.\nOmit --global to set the identity only in this repository.\n\n"
               f"fatal: no {'email' if dep.cfg('user.email') is None else 'name'} was given and auto-detection is disabled", 128)


def photographier(dep, msg, parents, auteur=None, quand=None, committer=None):
    ts, tz = quand or horloge()
    nom = auteur[0] if auteur else dep.cfg("user.name")
    mail = auteur[1] if auteur else dep.cfg("user.email")
    idt = ident(ts, tz, nom, mail)
    cidt = ident(ts, tz, committer[0], committer[1]) if committer else idt
    arbre = dep.ecrire_arbre(dict(dep.index))
    h = dep.ecrire_commit(arbre, parents, idt, cidt, msg)
    rh = dep.ref_head()
    if rh is not None:
        dep.branches[rh] = h
    else:
        dep.j["head"] = {"detache": h}
    return h


def _nettoyer_message(ms):
    t_ = [l.rstrip() for l in "\n\n".join(ms).splitlines()]
    while t_ and not t_[0]:
        t_.pop(0)
    while t_ and not t_[-1]:
        t_.pop()
    return "\n".join(t_) + "\n" if t_ else ""


def _stage(dep, p):
    f = dep.racine / p
    if f.is_file():
        dep.index[p] = dep.ajouter_blob(f.read_bytes().decode("utf-8", "replace"))
    else:
        dep.index.pop(p, None)
    c = dep.conflits()
    if p in c and dep.fusion is not None:
        dep.fusion["conflits"] = [x for x in c if x != p]


def commit(dep, args, env=None):
    msgs = []
    tout = calme = vide = False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--message", "-m"):
            if i + 1 >= len(args):
                return Res("error: switch `m' requires a value", 129)
            msgs.append(args[i + 1])
            i += 1
        elif a.startswith("--message="):
            msgs.append(a.split("=", 1)[1])
        elif a == "--all":
            tout = True
        elif a == "--quiet":
            calme = True
        elif a == "--allow-empty":
            vide = True
        elif a.startswith("-") and not a.startswith("--") and len(a) > 1:
            k = 1
            while k < len(a):
                c = a[k]
                if c == "a":
                    tout = True
                elif c == "q":
                    calme = True
                elif c == "m":
                    r = a[k + 1:]
                    if r:
                        msgs.append(r)
                    else:
                        if i + 1 >= len(args):
                            return Res("error: switch `m' requires a value", 129)
                        msgs.append(args[i + 1])
                        i += 1
                    k = len(a)
                else:
                    return Res(f"error: unknown switch `{c}'", 129)
                k += 1
        else:
            return Res(t("vsh.git.aide"), 1)
        i += 1
    if tout:
        for p in list(dep.index):
            _stage(dep, p)
        for p in dep.conflits():
            _stage(dep, p)
    if dep.conflits():
        return Res("error: Committing is not possible because you have unmerged files.\nhint: Fix them up in the work tree, and then use 'git add/rm <file>'\n"
                   "hint: as appropriate to mark resolution and make a commit.\nfatal: Exiting because of an unresolved conflict.", 128)
    fusion = dep.fusion
    msg = _nettoyer_message(msgs) or ((fusion.get("msg") + "\n") if fusion and fusion.get("msg") else "")
    if not msg:
        return Res(t("vsh.git.editeur"), 1)
    tete = dep.head()
    arbre = dep.ecrire_arbre(dict(dep.index))
    if fusion is None and not vide and arbre == (dep.arbre_de(tete) or VIDE):
        dep.sauver()
        return Res(status(dep), 1)
    auteur, quand, committer = _env_identite(env)
    if auteur is None:
        r = _identite(dep)
        if r:
            dep.sauver()
            return r
    parents = ([tete] if tete else []) + ([fusion.get("tete")] if fusion and fusion.get("tete") else [])
    avant = dep.fichiers_de(tete)
    h = photographier(dep, msg, parents, auteur, quand, committer)
    dep.j.pop("fusion", None)
    dep.sauver()
    if calme:
        return Res("")
    ou = dep.ref_head() or "detached HEAD"
    l = [f"[{ou}{' (root-commit)' if tete is None else ''} {court(h)}] {msg.splitlines()[0]}"]
    if fusion is None:
        l += [x for x in diffstat(dep, avant, dep.fichiers_de(h), True) if x.startswith(" ") and " | " not in x]
    return Res("\n".join(l))


def _env_identite(env):
    """GIT_AUTHOR_NAME, GIT_AUTHOR_DATE… (le jeu signe ainsi les photos du grimoire, à dates fixes)."""
    if not env:
        return None, None, None
    nom, mail = env.get("GIT_AUTHOR_NAME"), env.get("GIT_AUTHOR_EMAIL")
    quand = None
    d = env.get("GIT_AUTHOR_DATE") or env.get("GIT_COMMITTER_DATE")
    if d:
        m = re.match(r"@?(\d+)(?:\s+([+-])(\d\d)(\d\d))?$", d.strip())
        if m:
            off = (int(m.group(3) or 0) * 60 + int(m.group(4) or 0)) * (-1 if m.group(2) == "-" else 1)
            quand = (int(m.group(1)), off)
    auteur = (nom, mail) if nom and mail else None
    cn, cm = env.get("GIT_COMMITTER_NAME"), env.get("GIT_COMMITTER_EMAIL")
    committer = (cn, cm) if cn and cm else None
    return auteur, quand, committer


# -------------------------------------------- log, show
def _en_tete(dep, h, deco):
    c = dep.commit(h)
    l = [f"commit {h}" + (decorations(dep, h) if deco else "")]
    ps = dep.parents(h)
    if len(ps) > 1:
        l.append("Merge: " + " ".join(court(p) for p in ps))
    a = c.get("author", "")
    l.append(f"Author: {auteur_nom(a)} <{auteur_mail(a)}>")
    l.append(f"Date:   {date_git(a)}")
    l.append("")
    for m in c.get("msg", "").rstrip("\n").split("\n"):
        l.append("" if not m else f"    {m}")
    return l


def _compte(texte, s):
    if not s:
        return 0
    return texte.count(s)


def _format(dep, h, fmt):
    c = dep.commit(h) or {}
    a = c.get("author", "")
    rem = {"%H": h, "%h": court(h), "%s": sujet(dep, h), "%an": auteur_nom(a), "%ae": auteur_mail(a),
           "%ad": date_git(a), "%T": c.get("tree", ""), "%P": " ".join(dep.parents(h)), "%n": "\n", "%%": "%",
           "%B": c.get("msg", "").rstrip("\n"), "%d": decorations(dep, h), "%at": (re.search(r"> (\d+) ", a) or [0, ""])[1]}
    return re.sub(r"%(an|ae|ad|at|[HhsTPnBd%])", lambda m: rem.get(m.group(), m.group()), fmt)


def log(dep, args):
    une_ligne = graphe_ = patch = tous = False
    cherche = None
    mx = None
    fmt = None
    revs = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--oneline":
            une_ligne = True
        elif a == "--graph":
            graphe_ = True
        elif a == "--all":
            tous = True
        elif a in ("-p", "--patch"):
            patch = True
        elif a in ("--decorate", "--no-decorate", "--"):
            pass
        elif a == "-S":
            cherche = args[i + 1] if i + 1 < len(args) else None
            i += 1
        elif a.startswith("-S"):
            cherche = a[2:]
        elif a == "-n":
            try:
                mx = int(args[i + 1])
            except (IndexError, ValueError):
                pass
            i += 1
        elif a.startswith("--max-count="):
            mx = int(a.split("=", 1)[1])
        elif re.fullmatch(r"-\d+", a):
            mx = int(a[1:])
        elif a.startswith("--format=") or a.startswith("--pretty=format:") or a.startswith("--pretty=tformat:"):
            fmt = a.split(":", 1)[1] if a.startswith("--pretty") else a.split("=", 1)[1]
        elif a.startswith("-"):
            return Res(t("vsh.git.inconnu", cmd=f"log {a}"), 1)
        else:
            revs.append(a)
        i += 1
    if tous:
        departs = []
        for x in ([dep.head()] if dep.head() else []) + [dep.branches[b] for b in sorted(dep.branches)]:
            if x not in departs:
                departs.append(x)
    elif not revs:
        departs = [dep.head()] if dep.head() else []
    else:
        departs = []
        for r in revs:
            h = resoudre(dep, r)
            if h is None:
                return Res(f"fatal: ambiguous argument '{r}': unknown revision or path not in the working tree.\n"
                           "Use '--' to separate paths from revisions, like this:\n'git <command> [<revision>...] -- [<file>...]'", 128)
            departs.append(h)
    if not departs:
        return Res(f"fatal: your current branch '{dep.ref_head() or 'master'}' does not have any commits yet", 128)
    liste = ordre_graphe(dep, departs) if graphe_ else ordre(dep, departs)
    if cherche is not None:
        def garde(h):
            ps = dep.parents(h)
            if len(ps) > 1:
                return False
            a = dep.fichiers_de(ps[0] if ps else None)
            b = dep.fichiers_de(h)
            return any(a.get(p) != b.get(p) and _compte(dep.blob(a[p]) if a.get(p) else "", cherche) !=
                       _compte(dep.blob(b[p]) if b.get(p) else "", cherche) for p in set(a) | set(b))
        liste = [h for h in liste if garde(h)]
    if mx is not None:
        liste = liste[:mx]

    def texte(h):
        if fmt is not None:
            l = _format(dep, h, fmt).split("\n")
        elif une_ligne:
            l = [f"{court(h)}{decorations(dep, h)} {sujet(dep, h)}"]
        else:
            l = list(_en_tete(dep, h, True))
        if patch and len(dep.parents(h)) <= 1:
            ps = dep.parents(h)
            d = diff_git(dep, dep.fichiers_de(ps[0] if ps else None), dep.fichiers_de(h))
            if d:
                if not une_ligne:
                    l.append("")
                l += d
        return l
    if graphe_:
        return Res("\n".join(graphe(dep, liste, texte)).rstrip())
    if fmt is not None:
        return Res("\n".join("\n".join(texte(h)) for h in liste))
    return Res(("\n" if une_ligne else "\n\n").join("\n".join(texte(h)) for h in liste))


def show(dep, args):
    stat = "--stat" in args
    revs = [a for a in args if not a.startswith("--")]
    rev = revs[0] if revs else "HEAD"
    if ":" in rev:
        r0, chemin = rev.split(":", 1)
        h = resoudre(dep, r0 or "HEAD")
        if h is None:
            return Res(f"fatal: invalid object name '{r0}'.", 128)
        b = dep.fichiers_de(h).get(chemin)
        if b is None:
            return Res(f"fatal: path '{chemin}' does not exist in '{r0}'", 128)
        return Res(dep.blob(b).rstrip("\n"))
    h = resoudre(dep, rev)
    if h is None:
        return Res(f"fatal: ambiguous argument '{rev}': unknown revision or path not in the working tree.\n"
                   "Use '--' to separate paths from revisions, like this:\n'git <command> [<revision>...] -- [<file>...]'", 128)
    c = dep.commit(h)
    if c is None:
        return Res(dep.blob(h).rstrip("\n"))
    l = list(_en_tete(dep, h, True))
    ps = dep.parents(h)
    if len(ps) <= 1:
        a = dep.fichiers_de(ps[0] if ps else None)
        b = dep.fichiers_de(h)
        d = diffstat(dep, a, b, False) if stat else diff_git(dep, a, b)
        if d:
            l.append("")
            l += d
    return Res("\n".join(l))


def diff(dep, args):
    staged = any(a in ("--staged", "--cached") for a in args)
    chemins = [a for a in args if not a.startswith("-")]
    idx = dict(dep.index)

    def garde(m):
        if not chemins or chemins == ["."]:
            return m
        return {k: v for k, v in m.items() if any(k == c or k.startswith(c.rstrip("/") + "/") for c in chemins)}
    if staged:
        if "--stat" in args:
            return Res("\n".join(diffstat(dep, garde(dep.fichiers_de(dep.head())), garde(idx), False)))
        return Res("\n".join(diff_git(dep, garde(dep.fichiers_de(dep.head())), garde(idx))))
    conf = set(dep.conflits())
    travail, textes = {}, {}
    for p in idx:
        if p in conf:
            continue
        f = dep.racine / p
        if f.is_file():
            tx = f.read_bytes().decode("utf-8", "replace")
            travail[p] = blob_sha(f.read_bytes())
            textes[p] = tx
    if "--stat" in args:
        for p, tx in textes.items():
            dep.ajouter_blob(tx)
        return Res("\n".join(diffstat(dep, garde({k: v for k, v in idx.items() if k not in conf}), garde(travail), False)))
    return Res("\n".join(diff_git(dep, garde({k: v for k, v in idx.items() if k not in conf}), garde(travail), textes)))


# -------------------------------------------- restore, checkout, switch, branch
def _chemins_suivis(dep, chemins, source):
    tous = sorted(set(source) | set(dep.index), key=lambda s: s.encode("utf-8"))
    out = []
    for c in chemins:
        m = tous if c == "." else [x for x in tous if x == c or x.startswith(c.rstrip("/") + "/")]
        if not m:
            return None
        out += m
    vus = []
    for x in out:
        if x not in vus:
            vus.append(x)
    return vus


def restore(dep, args):
    source = None
    staged = travail = False
    chemins = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--source="):
            source = a.split("=", 1)[1]
        elif a in ("--source", "-s"):
            source = args[i + 1] if i + 1 < len(args) else None
            i += 1
        elif a in ("--staged", "-S"):
            staged = True
        elif a in ("--worktree", "-W"):
            travail = True
        elif a == "--":
            pass
        elif a.startswith("-"):
            return Res(t("vsh.git.inconnu", cmd=f"restore {a}"), 1)
        else:
            chemins.append(a)
        i += 1
    if not chemins:
        return Res("fatal: you must specify path(s) to restore", 128)
    if not staged:
        travail = True
    if source is not None:
        h = resoudre(dep, source)
        if h is None:
            return Res(f"fatal: could not resolve {source}", 128)
        src = dep.fichiers_de(h)
    elif staged:
        src = dep.fichiers_de(dep.head())
    else:
        src = dict(dep.index)
    liste = _chemins_suivis(dep, chemins, src)
    if liste is None:
        mauvais = next(c for c in chemins if _chemins_suivis(dep, [c], src) is None)
        return Res(f"error: pathspec '{mauvais}' did not match any file(s) known to git", 1)
    for p in liste:
        if staged:
            if src.get(p) is None:
                dep.index.pop(p, None)
            else:
                dep.index[p] = src[p]
        if travail:
            dep.poser(p, src.get(p))
    dep.sauver()
    return Res("")


def _nom_valide(n):
    return bool(n) and not n.startswith("-") and ".." not in n and not any(c.isspace() or c in "~^:?*[\\" for c in n) \
        and not n.endswith("/") and not n.endswith(".lock")


def switch(dep, args, checkout_=False):
    creer = next((k for k, a in enumerate(args) if a in ("-c", "-b", "--create")), -1)
    if creer >= 0:
        if creer + 1 >= len(args):
            return Res(f"error: switch `{args[creer].lstrip('-')}' requires a value", 129)
        nom = args[creer + 1]
        if nom in dep.branches:
            return Res(f"fatal: a branch named '{nom}' already exists", 128)
        if not _nom_valide(nom):
            return Res(f"fatal: '{nom}' is not a valid branch name", 128)
        depart = next((x for k, x in enumerate(args) if k not in (creer, creer + 1) and not x.startswith("-")), None)
        if depart is not None:
            cible = resoudre(dep, depart)
            if cible is None:
                return Res(f"fatal: invalid reference: {depart}", 128)
        else:
            cible = dep.head()
        if dep.head() is None and depart is None:
            dep.j["head"] = {"ref": nom}
            dep.sauver()
            return Res(f"Switched to a new branch '{nom}'")
        return _basculer(dep, cible, nom, True, nom)
    reste = [a for a in args if a not in ("--detach", "-d")]
    if not reste:
        return Res("fatal: missing branch or commit argument", 128)
    nom = reste[0]
    if nom == "-":
        voulu = dep.j.get("precedent")
        if not voulu:
            return Res("fatal: invalid reference: @{-1}", 128)
    else:
        voulu = nom
    if voulu in dep.branches:
        return _basculer(dep, dep.branches[voulu], voulu, False, voulu)
    for r in dep.remotes:
        ref = (dep.remotes[r].get("refs") or {}).get(voulu)
        if ref:
            dep.amont[voulu] = f"{r}/{voulu}"
            b = _basculer(dep, ref, voulu, True, voulu)
            return Res(f"branch '{voulu}' set up to track '{r}/{voulu}'.\n" + b.texte, b.code)
    h = resoudre(dep, voulu)
    if h is not None and dep.commit(h) is not None:
        if not checkout_ and "--detach" not in args and "-d" not in args:
            return Res(f"fatal: a branch is expected, got commit '{voulu}'\nhint: If you want to detach HEAD at the commit, try again with the --detach option.", 128)
        return _basculer(dep, h, None, False, voulu)
    if checkout_:
        return Res(f"error: pathspec '{voulu}' did not match any file(s) known to git", 1)
    return Res(f"fatal: invalid reference: {voulu}", 128)


def checkout(dep, args):
    if "--" in args:
        k = args.index("--")
        avant = [a for a in args[:k] if not a.startswith("-")]
        chemins = args[k + 1:]
        if not avant:
            return restore(dep, chemins)
        h = resoudre(dep, avant[0])
        if h is None:
            return Res(f"fatal: invalid reference: {avant[0]}", 128)
        src = dep.fichiers_de(h)
        liste = [p for p in (_chemins_suivis(dep, chemins, src) or []) if p in src]
        if not liste:
            return Res(f"error: pathspec '{chemins[0] if chemins else ''}' did not match any file(s) known to git", 1)
        for p in liste:
            dep.index[p] = src[p]
            dep.poser(p, src[p])
        dep.sauver()
        return Res("")
    if any(a in ("-b", "-B") for a in args):
        return switch(dep, ["-b" if a == "-B" else a for a in args], True)
    nom = next((a for a in args if not a.startswith("-") or a == "-"), None)
    if nom is None:
        return Res("", 0)
    if len(args) >= 2 and resoudre(dep, nom) is not None and \
            all((dep.racine / a).exists() or a in dep.index for a in args[1:]):
        return checkout(dep, [nom, "--"] + args[1:])
    if nom not in dep.branches and nom != "-" and resoudre(dep, nom) is None and ((dep.racine / nom).exists() or nom in dep.index):
        return restore(dep, args)
    return switch(dep, args, True)


def branch(dep, args):
    noms = [a for a in args if not a.startswith("-")]
    if any(a in ("-d", "-D", "-m", "-M") for a in args):
        return Res(t("vsh.git.inconnu", cmd="branch " + " ".join(args)), 1)
    if not noms:
        l = []
        if dep.ref_head() is None and dep.head() is not None:
            l.append(f"* (HEAD detached at {court(dep.head())})")
        for b in sorted(dep.branches):
            l.append(("* " if b == dep.ref_head() else "  ") + b)
        return Res("\n".join(l))
    nom = noms[0]
    if nom in dep.branches:
        return Res(f"fatal: a branch named '{nom}' already exists", 128)
    if not _nom_valide(nom):
        return Res(f"fatal: '{nom}' is not a valid branch name", 128)
    if len(noms) > 1:
        h = resoudre(dep, noms[1])
        if h is None:
            return Res(f"fatal: not a valid object name: '{noms[1]}'", 128)
    else:
        h = dep.head()
        if h is None:
            return Res(f"fatal: not a valid object name: '{dep.ref_head() or 'HEAD'}'", 128)
    dep.branches[nom] = h
    dep.sauver()
    return Res("")


# -------------------------------------------- merge, clone, pull
def ancetres(dep, h):
    return set(ordre(dep, [h]))


def base(dep, a, b):
    la = ancetres(dep, a)
    return next((x for x in ordre(dep, [b]) if x in la), None)


def merge(dep, args, autre=None, nom_autre=None, avant_texte="", env=None):
    if "--abort" in args:
        f = dep.fusion
        if f is None:
            return Res("fatal: There is no merge to abort (MERGE_HEAD missing).", 128)
        tete = dep.head()
        ft = dep.fichiers_de(tete)
        for p in [p for p in dep.travail() if p in ft or p in dep.index]:
            dep.poser(p, ft.get(p))
        dep.index.clear()
        for p, x in ft.items():
            dep.index[p] = x
            dep.poser(p, x)
        dep.j.pop("fusion", None)
        dep.sauver()
        return Res("")
    if dep.fusion is not None:
        return Res("error: Merging is not possible because you have unmerged files.\nhint: Fix them up in the work tree, and then use 'git add/rm <file>'\n"
                   "hint: as appropriate to mark resolution and make a commit.\nfatal: Exiting because of an unresolved conflict.", 128)
    nom = nom_autre or next((a for a in args if not a.startswith("-")), None)
    if nom is None:
        return Res("fatal: No remote for the current branch.", 128)
    eux = autre or resoudre(dep, nom)
    if eux is None:
        return Res(f"merge: {nom} - not something we can merge", 1)
    nous = dep.head()
    l = [avant_texte] if avant_texte else []
    if nous is None:
        _aller_a(dep, None, eux)
        dep.branches[dep.ref_head() or "master"] = eux
        dep.sauver()
        return Res("\n".join(l + ["Fast-forward"]))
    if eux in ancetres(dep, nous):
        return Res("\n".join(l + ["Already up to date."]))
    bloque = _ecrases(dep, nous, eux)
    if bloque:
        return Res("\n".join(l + ["error: Your local changes to the following files would be overwritten by merge:\n" +
                                  "\n".join(f"\t{p}" for p in bloque) +
                                  "\nPlease commit your changes or stash them before you merge.\nAborting"]), 1)
    if nous in ancetres(dep, eux):
        a, b = dep.fichiers_de(nous), dep.fichiers_de(eux)
        _aller_a(dep, nous, eux)
        rh = dep.ref_head()
        if rh is not None:
            dep.branches[rh] = eux
        else:
            dep.j["head"] = {"detache": eux}
        dep.sauver()
        l += [f"Updating {court(nous)}..{court(eux)}", "Fast-forward"] + diffstat(dep, a, b, True)
        return Res("\n".join(l))
    if autre is not None and nom_autre is not None and nom_autre.startswith("pull:"):
        return Res("\n".join(l + ["hint: You have divergent branches and need to specify how to reconcile them.",
                                  "hint: You can do so by running one of the following commands sometime before",
                                  "hint: your next pull:", "hint:", "hint:   git config pull.rebase false  # merge",
                                  "hint:   git config pull.rebase true   # rebase", "hint:   git config pull.ff only       # fast-forward only",
                                  "hint:", "hint: You can replace \"git config\" with \"git config --global\" to set a default",
                                  "hint: preference for all repositories. You can also pass --rebase, --no-rebase,",
                                  "hint: or --ff-only on the command line to override the configured default per",
                                  "hint: invocation.", "fatal: Need to specify how to reconcile divergent branches."]), 128)
    b0 = base(dep, nous, eux)
    fb, fa, fe = dep.fichiers_de(b0), dep.fichiers_de(nous), dep.fichiers_de(eux)
    conflits = []
    etiquette = nom_autre[5:] if nom_autre and nom_autre.startswith("pull:") else (nom_autre or nom)
    for p in sorted(set(fb) | set(fa) | set(fe), key=lambda s: s.encode("utf-8")):
        o, a, e = fb.get(p), fa.get(p), fe.get(p)
        if a == e:
            continue
        if o == a:
            dep.poser(p, e)
            if e is None:
                dep.index.pop(p, None)
            else:
                dep.index[p] = e
        elif o == e:
            continue
        elif a is None or e is None:
            l.append(f"CONFLICT (modify/delete): {p} deleted in {'HEAD' if a is None else etiquette} and modified in "
                     f"{etiquette if a is None else 'HEAD'}.  Version {etiquette if a is None else 'HEAD'} of {p} left in tree.")
            if a is None:
                dep.poser(p, e)
            conflits.append(p)
        else:
            l.append(f"Auto-merging {p}")
            texte, conflit = fusionner(dep.blob(o) if o else "", dep.blob(a), dep.blob(e), etiquette)
            f = dep.racine / p
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, "w", encoding="utf-8", newline="") as x:
                x.write(texte)
            if conflit:
                l.append(f"CONFLICT ({'add/add' if o is None else 'content'}): Merge conflict in {p}")
                conflits.append(p)
            else:
                dep.index[p] = dep.ajouter_blob(texte)
    rh = dep.ref_head()
    if nom_autre is not None and nom_autre.startswith("pull:"):
        msg = f"Merge branch '{etiquette}'"
    else:
        msg = f"Merge branch '{etiquette}'" + (f" into {rh}" if rh is not None and rh not in ("main", "master") else "")
    if conflits:
        dep.j["fusion"] = {"tete": eux, "msg": msg, "conflits": conflits}
        dep.sauver()
        l.append("Automatic merge failed; fix conflicts and then commit the result.")
        return Res("\n".join(l), 1)
    r = _identite(dep)
    if r:
        dep.sauver()
        return Res("\n".join(l + [r.texte]), r.code)
    h = photographier(dep, msg + "\n", [nous, eux])
    dep.sauver()
    l = [x for x in l if not x.startswith("Auto-merging")]
    l += ["Merge made by the 'ort' strategy."] + diffstat(dep, fa, dep.fichiers_de(h), True)
    return Res("\n".join(l))


def _dans_terrain(p, terrain):
    try:
        r = str(Path(p).resolve()) + os.sep
        return r.startswith(str(Path(terrain).resolve()) + os.sep)
    except OSError:
        return False


def clone(ici, terrain, args):
    mots = [a for a in args if not a.startswith("-")]
    if not mots:
        return Res("fatal: You must specify a repository to clone.", 129)
    src = mots[0]
    if "://" in src or "@" in src:
        return Res(t("vsh.git.reseau"), 1)
    url = src if os.path.isabs(src) else os.path.join(str(ici), src)      # (git garde « album/. » tel quel)
    fs = Path(url)
    try:
        fs = fs.resolve()
    except OSError:
        pass
    src_dep = ouvrir(fs)
    if src_dep is None:
        return Res(f"fatal: repository '{src}' does not exist", 128)
    nom_dest = mots[1] if len(mots) > 1 else re.sub(r"\.git$", "", fs.name)
    fd = (Path(nom_dest) if os.path.isabs(nom_dest) else Path(ici) / nom_dest).resolve()
    if not _dans_terrain(fd, terrain):
        return Res(t("vsh.git.hors_terrain"), 1)
    if fd.exists() and any(fd.iterdir()):
        return Res(f"fatal: destination path '{nom_dest}' already exists and is not an empty directory.", 128)
    d = Depot(fd).charger()
    d.j["objets"] = json.loads(json.dumps(src_dep.objets))
    refs = dict(src_dep.branches)
    tete = src_dep.ref_head()
    d.remotes["origin"] = {"url": url, "refs": refs, "head": tete or ""}
    if tete is not None and src_dep.head() is not None:
        d.branches[tete] = src_dep.head()
        d.j["head"] = {"ref": tete}
        d.amont[tete] = f"origin/{tete}"
        _aller_a(d, None, src_dep.head())
    d.sauver()
    if "-q" in args or "--quiet" in args:
        return Res("")
    return Res(f"Cloning into '{nom_dest}'...\ndone.")


def pull(dep, ici, args):
    mots = [a for a in args if not a.startswith("-")]
    depot = mots[0] if mots else None
    if depot is None:
        b = dep.ref_head()
        up = dep.amont.get(b) if b else None
        if not up:
            return Res("There is no tracking information for the current branch.\nPlease specify which branch you want to merge with.\n"
                       "See git-pull(1) for details.\n\n    git pull <remote> <branch>\n\nIf you wish to set tracking information for this branch you can do so with:\n\n"
                       f"    git branch --set-upstream-to=<remote>/<branch> {b or 'main'}\n", 1)
        nom_remote = up.split("/", 1)[0]
        url = dep.remotes[nom_remote].get("url", "")
    elif depot in dep.remotes:
        nom_remote = depot
        url = dep.remotes[depot].get("url", "")
    else:
        nom_remote = None
        url = depot
    if "://" in url or "@" in url:
        return Res(t("vsh.git.reseau"), 1)
    f = Path(url) if os.path.isabs(url) else Path(ici) / url
    try:
        f = f.resolve()
    except OSError:
        pass
    autre = ouvrir(f)
    if autre is None:
        return Res(f"fatal: '{url}' does not appear to be a git repository\nfatal: Could not read from remote repository.\n\n"
                   "Please make sure you have the correct access rights\nand the repository exists.", 128)
    ref = mots[1] if len(mots) > 1 else None
    if ref is not None:
        h = autre.branches.get(ref) or None
    elif nom_remote is not None and depot is None:
        h = autre.branches.get(dep.amont.get(dep.ref_head() or "", "").split("/", 1)[-1]) or None
    else:
        h = autre.head()
    if h is None:
        return Res(f"fatal: couldn't find remote ref {ref or 'HEAD'}", 1)
    for k, v in autre.objets.items():
        if k not in dep.objets:
            dep.objets[k] = v
    dep.j["fetch_head"] = h
    montre = ETAT["afficher"](url) if nom_remote is not None else url
    qui = ref or (dep.amont.get(dep.ref_head() or "", "").split("/", 1)[-1] if nom_remote is not None and depot is None else "HEAD")
    if nom_remote is not None:
        o = dep.remotes[nom_remote]
        refs = o.setdefault("refs", {})
        refs.update(autre.branches)
    tete = f"From {montre}\n * branch            {qui.ljust(10)} -> FETCH_HEAD"
    return merge(dep, [], h, f"pull:{qui}", tete)


# -------------------------------------------- config, cat-file, hash-object, remote, rev-list
def config(dep, args):
    if any(a in ("--global", "--system") for a in args):
        return Res(t("vsh.git.global"), 1)
    a = [x for x in args if x != "--local"]
    if dep is None:
        return Res("fatal: not in a git directory", 128)
    if a[:1] in (["--list"], ["-l"]):
        return Res("\n".join(f"{k}={v}" for k, v in dep.config.items()))
    if a[:1] == ["--unset"]:
        if len(a) > 1:
            dep.config.pop(a[1], None)
        dep.sauver()
        return Res("")
    if a and a[0] == "--get" and len(a) > 1:
        a = a[1:]
    if not a:
        return Res("error: no action specified", 2)
    cle = a[0]
    if "." not in cle:
        return Res(f"error: key does not contain a section: {cle}", 2)
    if len(a) == 1:
        v = dep.cfg(cle)
        return Res(v) if v is not None else Res("", 1)
    dep.config[cle] = " ".join(a[1:])
    dep.sauver()
    return Res("")


def cat_file(dep, args):
    opt = next((a for a in args if a.startswith("-")), None)
    rev = next((a for a in args if not a.startswith("-")), None)
    if opt is None or rev is None:
        return Res("usage: git cat-file (-t | -s | -e | -p) <object>", 129)
    h = resoudre(dep, rev)
    o = dep.objet(h) if h else None
    if o is None:
        return Res(f"fatal: Not a valid object name {rev}", 128)
    ty = o.get("t")
    if opt == "-t":
        return Res(ty)
    if opt == "-e":
        return Res("")
    if opt == "-p":
        if ty == "commit":
            return Res(dep.corps_commit(h).rstrip("\n"))
        if ty == "tree":
            return Res("\n".join(("040000 tree " if m == "40000" else "100644 blob ") + x + "\t" + n for m, n, x in o.get("e", [])))
        return Res(o.get("c", "").rstrip("\n"))
    if opt == "-s":
        return Res(str(len(o.get("c", "").encode("utf-8")) if ty == "blob" else 0))
    return Res("usage: git cat-file (-t | -s | -e | -p) <object>", 129)


def remote(dep, args):
    if args and args[0] in ("add", "set-url", "rename", "remove", "rm"):
        return Res(t("vsh.git.reseau"), 1)
    v = "-v" in args or "--verbose" in args
    out = []
    for r in sorted(dep.remotes):
        u = ETAT["afficher"](dep.remotes[r].get("url", ""))
        out += [f"{r}\t{u} (fetch)", f"{r}\t{u} (push)"] if v else [r]
    return Res("\n".join(out))


def rev_list(dep, args):
    inclus, exclus = [], []
    mx = None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-n", "--max-count"):
            try:
                mx = int(args[i + 1])
            except (IndexError, ValueError):
                pass
            i += 1
        elif a.startswith("--max-count="):
            mx = int(a.split("=", 1)[1])
        elif a.startswith("-"):
            pass
        elif ".." in a:
            x, y = a.split("..", 1)
            exclus.append(x or "HEAD")
            inclus.append(y or "HEAD")
        elif a.startswith("^"):
            exclus.append(a[1:])
        else:
            inclus.append(a)
        i += 1
    pos = []
    for r in inclus:
        h = resoudre(dep, r)
        if h is None:
            return Res(f"fatal: ambiguous argument '{r}': unknown revision or path not in the working tree.", 128)
        pos.append(h)
    neg = set()
    for r in exclus:
        h = resoudre(dep, r)
        if h:
            neg |= set(ordre(dep, [h]))
    if "--first-parent" in args:
        liste = []
        x = pos[0] if pos else None
        while x is not None and x not in neg:
            liste.append(x)
            ps = dep.parents(x)
            x = ps[0] if ps else None
    else:
        liste = [h for h in ordre(dep, pos) if h not in neg]
    if mx is not None:
        liste = liste[:mx]
    if "--count" in args:
        return Res(str(len(liste)))
    if "--reverse" in args:
        liste = list(reversed(liste))
    return Res("\n".join(" ".join([h] + dep.parents(h)) if "--parents" in args else h for h in liste))


def init(ici, terrain, args):
    branche = "master"
    calme = False
    mots = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-b", "--initial-branch"):
            if i + 1 >= len(args):
                return Res("error: switch `b' requires a value", 129)
            branche = args[i + 1]
            i += 1
        elif a.startswith("--initial-branch="):
            branche = a.split("=", 1)[1]
        elif a in ("-q", "--quiet"):
            calme = True
        elif a.startswith("-"):
            return Res(t("vsh.git.inconnu", cmd=f"init {a}"), 1)
        else:
            mots.append(a)
        i += 1
    d = Path(ici) / mots[0] if mots and not os.path.isabs(mots[0]) else (Path(mots[0]) if mots else Path(ici))
    d = Path(os.path.abspath(d))
    if not (_dans_terrain(d, terrain) or Path(os.path.abspath(terrain)) == d):
        return Res(t("vsh.git.hors_terrain"), 1)
    deja = est_depot(d)
    d.mkdir(parents=True, exist_ok=True)
    dep = Depot(d).charger()
    if not deja:
        dep.j["head"] = {"ref": branche}
    dep.sauver()
    if calme:
        return Res("")
    return Res(f"{'Reinitialized existing' if deja else 'Initialized empty'} Git repository in "
               f"{ETAT['afficher'](str(d / '.git'))}/")


def add(dep, args):
    chemins = [a for a in args if not a.startswith("-")]
    toutes = any(a in ("-A", "--all") for a in args) or "." in chemins
    if not chemins and not toutes:
        return Res("Nothing specified, nothing added.\nhint: Maybe you wanted to say 'git add .'?\nhint: Turn this message off by running\n"
                   "hint: \"git config advice.addEmptyPathspec false\"", 0)
    travail = list(dep.travail())
    cibles = []
    if toutes:
        cibles += [p for p in travail if not dep.ignore(p) or p in dep.index]
        cibles += list(dep.index)
    for c in [x for x in chemins if x != "."]:
        c = c[2:] if c.startswith("./") else c
        m = [p for p in travail + list(dep.index) if p == c or p.startswith(c.rstrip("/") + "/")]
        if not m:
            return Res(f"fatal: pathspec '{c}' did not match any files", 128)
        ign = [p for p in m if dep.ignore(p) and p not in dep.index]
        if ign and len(set(ign)) == len(set(m)):
            return Res(f"The following paths are ignored by one of your .gitignore files:\n{c}\nhint: Use -f if you really want to add them.\n"
                       "hint: Turn this message off by running\nhint: \"git config advice.addIgnoredFile false\"", 1)
        cibles += [p for p in m if p not in ign]
    vus = set()
    for p in cibles:
        if p not in vus:
            vus.add(p)
            _stage(dep, p)
    dep.sauver()
    return Res("")


def executer(mots, ici, terrain, env=None):
    """git … : la ligne déjà découpée en mots. ici, terrain : de vrais dossiers. Renvoie Res(texte, code)."""
    mots = list(mots)
    env = dict(env or {})
    while mots and mots[0] == "-c" and len(mots) > 1:     # git -c user.name=… : réglages d'un instant
        k, _, v = mots[1].partition("=")
        if k == "user.name":
            env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = v
        elif k == "user.email":
            env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = v
        mots = mots[2:]
    while mots and mots[0] in ("--no-pager", "-P"):
        mots = mots[1:]
    if mots and mots[0] == "-C" and len(mots) > 1:
        ici = Path(ici) / mots[1]
        mots = mots[2:]
    sous = mots[0] if mots else None
    args = mots[1:]
    if sous is None:
        return Res(t("vsh.git.aide"), 1)
    try:
        if sous in ("help", "--help", "-h"):
            return Res(t("vsh.git.aide"))
        if sous in ("version", "--version"):
            return Res("git version 2.43.0 (" + t("vsh.git.version") + ")")
        if sous == "init":
            return init(ici, terrain, args)
        if sous == "clone":
            return clone(ici, terrain, args)
        if sous == "hash-object":
            f = next((a for a in args if not a.startswith("-")), None)
            if f is None:
                return Res("usage: git hash-object [-t <type>] [-w] [--path=<file> | --no-filters]", 129)
            x = Path(f) if os.path.isabs(f) else Path(ici) / f
            if not x.is_file():
                return Res(f"fatal: could not open '{f}' for reading: No such file or directory", 128)
            return Res(blob_sha(x.read_bytes()))
        if sous == "push":
            return Res(t("vsh.git.reseau"), 1)
        if sous in ("fetch", "rebase", "stash", "tag", "reset", "rm", "mv", "revert", "cherry-pick", "blame", "bisect",
                    "submodule", "gc", "reflog", "am", "apply", "grep", "describe", "shortlog", "notes", "worktree"):
            return Res(t("vsh.git.inconnu", cmd=sous), 1)
        if sous in ("switch", "checkout", "merge", "pull", "restore", "add", "branch") and any(
                a in ("-q", "--quiet") or re.fullmatch(r"-q[a-zA-Z]+|-[a-zA-Z]+q", a) for a in args):
            calme = True                              # -q : rien à dire quand ça marche
            args = [x for a in args for x in (["-" + c for c in a[1:] if c != "q"] if re.fullmatch(r"-[a-zA-Z]{2,}", a)
                                              else ([] if a in ("-q", "--quiet") else [a]))]
        else:
            calme = False
        dep = trouver(ici, terrain)
        if sous == "config":
            return config(dep, args)
        if dep is None:
            return Res("fatal: not a git repository (or any of the parent directories): .git", 128)
        if calme:
            r = executer_sans_calme(sous, dep, args, ici, env)
            return Res("", r.code) if r.code == 0 else r
        return executer_sans_calme(sous, dep, args, ici, env)
    except Exception as e:                       # noqa: BLE001 — jamais une trace Python pour l'enfant
        return Res(f"petit git : {e!r}", 1)


def executer_sans_calme(sous, dep, args, ici, env):
    try:
        if sous == "status":
            return Res(status(dep, any(a in ("-s", "--short") for a in args), "--porcelain" in args))
        if sous == "add":
            return add(dep, args)
        if sous == "commit":
            return commit(dep, args, env)
        if sous == "log":
            return log(dep, args)
        if sous == "show":
            return show(dep, args)
        if sous == "diff":
            return diff(dep, args)
        if sous == "restore":
            return restore(dep, args)
        if sous == "checkout":
            return checkout(dep, args)
        if sous == "switch":
            return switch(dep, args, False)
        if sous == "branch":
            return branch(dep, args)
        if sous == "merge":
            return merge(dep, args, env=env)
        if sous == "pull":
            return pull(dep, ici, args)
        if sous == "remote":
            return remote(dep, args)
        if sous == "cat-file":
            return cat_file(dep, args)
        if sous == "rev-list":
            return rev_list(dep, args)
        if sous == "symbolic-ref":
            mots_ = [a for a in args if not a.startswith("-")]
            if len(mots_) >= 2 and mots_[1].startswith("refs/heads/"):
                dep.j["head"] = {"ref": mots_[1][11:]}
                dep.sauver()
                return Res("")
            if not dep.ref_head():
                return Res("" if "-q" in args else "fatal: ref HEAD is not a symbolic ref", 1 if "-q" in args else 128)
            return Res(dep.ref_head() if "--short" in args else f"refs/heads/{dep.ref_head()}")
        if sous == "rev-parse":
            if "--show-toplevel" in args or "--absolute-git-dir" in args:
                out = []
                if "--show-toplevel" in args:
                    out.append(ETAT["afficher"](str(dep.racine)))
                if "--absolute-git-dir" in args:
                    out.append(ETAT["afficher"](str(dep.git_dir)))
                return Res("\n".join(out))
            if "--verify" in args:
                x = [a for a in args if not a.startswith("-")]
                h = resoudre(dep, x[0]) if x else None
                if h is None:
                    return Res("" if "-q" in args else "fatal: Needed a single revision", 1 if "-q" in args else 128)
                return Res(h)
            if "--abbrev-ref" in args:
                return Res(dep.ref_head() or "HEAD")
            out = []
            for a in [x for x in args if not x.startswith("-")]:
                h = resoudre(dep, a)
                if h is None:
                    return Res(f"{a}\nfatal: ambiguous argument '{a}': unknown revision or path not in the working tree.", 128)
                out.append(h)
            return Res("\n".join(out))
        return Res(t("vsh.git.inconnu", cmd=sous), 1)
    except Exception as e:                       # noqa: BLE001 — jamais une trace Python pour l'enfant
        return Res(f"petit git : {e!r}", 1)


# ---------------------------------------------------------------- la commande du terminal du jeu
def _outil(ctx):
    from .outils import outil  # noqa: F401
    vfs = ctx.vfs
    ici = vfs.reel(ctx.sh.cwd) if vfs.mode == "windows" else Path(ctx.sh.cwd)
    terrain = vfs.terrain_reel
    if vfs.mode == "transparent" and vfs.zones:
        terrain = Path(os.path.commonpath([str(z) for z in vfs.zones])) if len(vfs.zones) > 1 else vfs.zones[0]
    if ici is None:
        ici = Path(vfs.sys_reel or "/")
    ancien = ETAT["afficher"]
    if vfs.mode == "windows":
        ETAT["afficher"] = lambda p: vfs.virtuel(p) or str(p)
    env = {k: v for k, v in ctx.sh.vars.items() if k.startswith("GIT_") and k in ctx.sh.exportees}
    DECORER["oui"] = ctx.sortie.tty or "--decorate" in ctx.args
    try:
        r = executer(ctx.args[1:], ici, terrain, env)
    finally:
        ETAT["afficher"] = ancien
        DECORER["oui"] = True
    sortie = r.texte + ("\n" if r.texte and not r.texte.endswith("\n") else "")
    if r.code and r.code != 1 or r.texte.startswith(("fatal:", "error:", "usage:")):
        ctx.err(sortie)
    else:
        ctx.out(sortie)
    return r.code


def git_present():
    """Le jeu peut-il préparer des dépôts ? (le petit git du terminal du jeu, ou le vrai git)."""
    from ..plateforme import terminal_virtuel
    import shutil
    return terminal_virtuel() or shutil.which("git") is not None


def git_du_jeu(args, cwd, extra=None, timeout=20):
    """(code, sortie) d'un git lancé par le JEU dans `cwd` : le petit git quand le terminal des leçons est celui du
    jeu (Windows), sinon le vrai git (LC_ALL=C, jamais d'invite de mot de passe)."""
    from ..plateforme import terminal_virtuel
    if terminal_virtuel():
        from .. import core
        r = executer(list(args), cwd, core.TERRAIN, extra or {})
        return r.code, (r.texte + "\n" if r.texte and r.code == 0 else "")
    import subprocess
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANGUAGE="C")
    env.update(extra or {})
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""
