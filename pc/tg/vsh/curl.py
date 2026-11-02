"""Le terminal du jeu : `curl`, limité au phare du Port (décision du propriétaire du 2 novembre).

Le phare du Port est le petit serveur HTTP du jeu, sur la boucle locale (127.0.0.1:8042 ; pc/tg/port.py). Ce curl lui
parle pour de vrai : une vraie connexion TCP, la vraie requête HTTP/1.1, la vraie réponse, affichées comme le vrai
curl (curl 8 : -I, -i, -s, -S, -v, -o, -O, -X, -d, -H, -A, -f, -L, -w, la barre de progression quand la page ne va pas
à l'écran). Toute autre adresse (Internet, un autre port, https, file://…) est refusée avec un message clair : il n'y
a pas d'Internet dans le terminal du jeu, aucune connexion n'est jamais ouverte ailleurs, et l'étape de la leçon est
racontée (jamais bloquante). pc/outils/test_terminal.py compare au vrai curl sous Linux, sur le même phare.
"""
import posixpath
import re
import socket
import time

from .outils import outil
from .vfs import ErreurFs

AGENT = "curl-terminagotchi/1.0"
AIDE_ESSAI = "curl: try 'curl --help' or 'curl --manual' for more information\n"
# les options : (courte, longue) → nom ; celles qui prennent une valeur
AVEC_VALEUR = {"o": "output", "X": "request", "d": "data", "H": "header", "A": "user-agent", "w": "write-out",
               "m": "max-time", "e": "referer", "u": "user", "b": "cookie", "c": "cookie-jar", "x": "proxy",
               "T": "upload-file", "F": "form", "E": "cert", "K": "config", "r": "range", "z": "time-cond"}
SANS_VALEUR = {"s": "silent", "S": "show-error", "v": "verbose", "I": "head", "i": "include", "O": "remote-name",
               "f": "fail", "L": "location", "k": "insecure", "h": "help", "V": "version", "#": "progress-bar",
               "4": "ipv4", "6": "ipv6", "N": "no-buffer", "G": "get", "j": "junk-session-cookies", "q": "disable"}
LONGUES_VALEUR = set(AVEC_VALEUR.values()) | {"data-raw", "data-binary", "data-ascii", "data-urlencode", "cacert",
                                              "capath", "connect-timeout", "url", "retry", "limit-rate", "resolve",
                                              "max-redirs", "proto", "interface", "local-port", "dns-servers",
                                              "noproxy", "max-filesize"}
LONGUES = set(SANS_VALEUR.values()) | {"compressed", "fail-with-body", "http1.1", "http1.0", "no-progress-meter",
                                       "trace-ascii", "globoff", "raw", "path-as-is", "styled-output", "no-keepalive",
                                       "ssl-no-revoke", "tcp-nodelay", "remote-name-all", "create-dirs", "stderr"}
# ce que ce curl ne fait pas (envoyer un fichier, un proxy, un formulaire…) : refusé poliment
PAS_ICI = {"upload-file", "form", "proxy", "cert", "config", "user", "cookie", "cookie-jar", "resolve",
           "dns-servers", "interface", "local-port", "trace-ascii"}


class _Erreur(Exception):
    def __init__(self, code, texte):
        super().__init__(texte)
        self.code, self.texte = code, texte


def _t(cle, **k):
    from ..langue import t
    return t(cle, **k)


def ports_phare():
    from .python import ports_phare as p
    return p()


def analyser(args):
    """Les arguments → (options {nom: valeur ou liste}, urls) ; _Erreur pour une option inconnue."""
    o = {"header": [], "data": []}
    urls = []
    i = 0
    fini = False
    while i < len(args):
        a = args[i]
        if fini or not a.startswith("-") or a == "-":
            urls.append(a)
            i += 1
            continue
        if a == "--":
            fini = True
            i += 1
            continue
        if a.startswith("--"):
            nom, egal, val = a[2:].partition("=")
            if nom.startswith("no-") and nom[3:] in LONGUES and nom != "no-progress-meter":
                o.pop(nom[3:], None)
                i += 1
                continue
            if nom in LONGUES_VALEUR:
                if not egal:
                    if i + 1 >= len(args):
                        raise _Erreur(2, f"curl: option {a}: requires parameter\n" + AIDE_ESSAI)
                    val = args[i + 1]
                    i += 1
                _poser(o, nom, val)
            elif nom in LONGUES and not egal:
                o[nom] = True
            else:
                raise _Erreur(2, f"curl: option {a}: is unknown\n" + AIDE_ESSAI)
            i += 1
            continue
        j = 1
        while j < len(a):
            c = a[j]
            if c in AVEC_VALEUR:
                val = a[j + 1:]
                if not val:
                    if i + 1 >= len(args):
                        raise _Erreur(2, f"curl: option -{c}: requires parameter\n" + AIDE_ESSAI)
                    val = args[i + 1]
                    i += 1
                _poser(o, AVEC_VALEUR[c], val)
                break
            if c in SANS_VALEUR:
                o[SANS_VALEUR[c]] = True
            else:
                raise _Erreur(2, f"curl: option -{a[j:]}: is unknown\n" + AIDE_ESSAI)
            j += 1
        i += 1
    if o.get("url"):
        urls.insert(0, o.pop("url"))
    return o, urls


def _poser(o, nom, val):
    if nom == "header":
        o["header"].append(val)
    elif nom in ("data", "data-raw", "data-binary", "data-ascii", "data-urlencode"):
        o["data"].append((nom, val))
    else:
        o[nom] = val


def decouper_url(url):
    """« http://localhost:8042/eau », « localhost:8042 » → (schéma, hôte, port, chemin) ; None si illisible."""
    m = re.match(r"^(?:([A-Za-z][A-Za-z0-9+.-]*)://)?(?:[^@/?#]*@)?(\[[^\]]*\]|[^/:?#]*)(?::(\d*))?([/?][^#]*)?(#.*)?$",
                 url.strip())
    if not m:
        return None
    schema = (m.group(1) or "http").lower()
    hote = m.group(2).strip("[]")
    defaut = {"http": 80, "https": 443}.get(schema, 0)
    port = int(m.group(3)) if m.group(3) else defaut
    chemin = m.group(4) or "/"
    if chemin.startswith("?"):
        chemin = "/" + chemin
    return schema, hote, port, chemin


def local(hote):
    h = (hote or "").lower()
    return h in ("localhost", "::1", "0.0.0.0", "") or h.startswith("127.") or h.endswith(".localhost")


def permise(url):
    """Vrai si l'adresse est le phare du Port (http://localhost:8042 ou 127.0.0.1:8042)."""
    d = decouper_url(url)
    return bool(d) and d[0] == "http" and d[1].lower() in ("localhost", "127.0.0.1") and d[2] in ports_phare()


def refus(url):
    """Le message du jeu pour une adresse que ce curl ne visite pas (et son code de sortie, comme le vrai curl)."""
    d = decouper_url(url)
    phare = f"http://localhost:{ports_phare()[0]}/"
    if d and d[0] in ("http", "https") and local(d[1]):
        return 7, _t("vsh.curl.local", url=url, phare=phare)
    return 6, _t("vsh.curl.internet", phare=phare)


def usage_raconte(args):
    """curl vers une autre adresse que le phare (Internet, le quai 8000 de l'enfant, https…) : l'étape est racontée."""
    try:
        o, urls = analyser(list(args[1:]))
    except _Erreur:
        return False
    if o.get("help") or o.get("version"):
        return False
    return any(not permise(u) for u in urls)


# ---------------------------------------------------------------- la barre de progression du vrai curl
def _cinq(n):
    """max5data de curl : 5 caractères (159, 183k, 2.5M…)."""
    n = int(n)
    if n < 100000:
        return f"{n:5d}"
    if n < 10000 * 1024:
        return f"{n // 1024:4d}k"
    if n < 100 * 1024 * 1024:
        return f"{n // (1024 * 1024):2d}.{(n % (1024 * 1024)) // (1024 * 1024 // 10):d}M"
    return f"{n // (1024 * 1024):4d}M"


TETE_PROGRES = ("  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
                "                                 Dload  Upload   Total   Spent    Left  Speed\n")


def _duree(s):
    if s < 1:
        return "--:--:--"
    s = int(s)
    return f"{s // 3600:2d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def ligne_progres(total, recu, attendu, envoye, a_envoyer, duree):
    pct = lambda a, b: int(100 * a / b) if b else 0          # noqa: E731
    vit_d = recu / duree if duree > 0 else 0
    vit_u = envoye / duree if duree > 0 else 0
    return (f"{pct(recu + envoye, total):3d} {_cinq(total)}  {pct(recu, attendu):3d} {_cinq(recu)}  "
            f"{pct(envoye, a_envoyer):3d} {_cinq(envoye)}  {_cinq(vit_d)}  {_cinq(vit_u)} --:--:-- "
            f"{_duree(duree)} --:--:-- {_cinq(vit_d)}")


# ---------------------------------------------------------------- une requête, pour de vrai
def requete(hote, port, brut, delai=10):
    """Envoie la requête au phare (127.0.0.1 seulement) et rend la réponse brute ; OSError si personne n'écoute."""
    s = socket.create_connection(("127.0.0.1", port), timeout=min(delai, 10))
    try:
        s.settimeout(delai)
        s.sendall(brut)
        morceaux = []
        while True:
            b = s.recv(65536)
            if not b:
                break
            morceaux.append(b)
        return b"".join(morceaux)
    finally:
        s.close()


def lire_reponse(brut, tete=False):
    """(ligne d'état, en-têtes bruts avec \\r\\n, dict des en-têtes en minuscules, corps)."""
    sep = brut.find(b"\r\n\r\n")
    if sep < 0:
        entetes, corps = brut, b""
    else:
        entetes, corps = brut[:sep + 4], brut[sep + 4:]
    lignes = entetes.split(b"\r\n")
    d = {}
    for l in lignes[1:]:
        if b":" in l:
            k, _, v = l.partition(b":")
            d[k.decode("latin-1").strip().lower()] = v.decode("latin-1").strip()
    if tete:
        corps = b""
    elif d.get("transfer-encoding", "").lower() == "chunked":
        corps = _dechunker(corps)
    elif "content-length" in d:
        try:
            corps = corps[:int(d["content-length"])]
        except ValueError:
            pass
    return lignes[0].decode("latin-1"), entetes, d, corps


def _dechunker(b):
    out = []
    i = 0
    while i < len(b):
        j = b.find(b"\r\n", i)
        if j < 0:
            break
        try:
            n = int(b[i:j].split(b";")[0], 16)
        except ValueError:
            break
        if n == 0:
            break
        out.append(b[j + 2:j + 2 + n])
        i = j + 2 + n + 2
    return b"".join(out)


def _rallumer_phare():
    try:
        from .. import port
        return port.assurer_phare()
    except Exception:                         # noqa: BLE001
        return False


def _code_http(etat):
    m = re.match(r"HTTP/\S+\s+(\d{3})", etat)
    return int(m.group(1)) if m else 0


def _ecrire_out(ctx, o, b):
    ctx.out(b)


def _write_out(fmt, infos):
    def rempl(m):
        k = m.group(1)
        if k in infos:
            return str(infos[k])
        return ""
    fmt = fmt.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    return re.sub(r"%\{([a-z_]+)\}", rempl, fmt)


@outil("curl")
def curl(ctx):
    try:
        o, urls = analyser(ctx.args[1:])
    except _Erreur as e:
        ctx.err(e.texte)
        return e.code
    if o.get("help"):
        ctx.out("Usage: curl [options...] <url>\n"
                " -d, --data <data>          HTTP POST data\n"
                " -f, --fail                 Fail fast with no output on HTTP errors\n"
                " -h, --help <category>      Get help for commands\n"
                " -i, --include              Include protocol response headers in the output\n"
                " -I, --head                 Show document info only\n"
                " -o, --output <file>        Write to file instead of stdout\n"
                " -O, --remote-name          Write output to a file named as the remote file\n"
                " -s, --silent               Silent mode\n"
                " -v, --verbose              Make the operation more talkative\n"
                " -X, --request <method>     Specify request method to use\n"
                + _t("vsh.curl.version", phare=f"http://localhost:{ports_phare()[0]}/") + "\n")
        return 0
    if o.get("version"):
        ctx.out("curl (Terminagotchi) — " + _t("vsh.curl.version", phare=f"http://localhost:{ports_phare()[0]}/")
                + "\nProtocols: http\n")
        return 0
    if not urls:
        if len(ctx.args) > 1:
            ctx.err("curl: (2) no URL specified\n")
        ctx.err(AIDE_ESSAI)
        return 2
    autre = next((k for k in PAS_ICI if k in o), None)
    if autre:
        ctx.err(_t("vsh.curl.option", option="--" + autre) + "\n")
        return 2
    code = 0
    for k, url in enumerate(urls):
        code = _une(ctx, o, url, premiere=(k == 0)) or code
    return code


def _montrer_erreurs(o):
    return not o.get("silent") or o.get("show-error")


def _une(ctx, o, url, premiere=True, sauts=0):
    silencieux = bool(o.get("silent"))
    bavard = bool(o.get("verbose"))
    if not permise(url):
        code, msg = refus(url)
        ctx.err(msg + "\n")
        return code
    schema, hote, port, chemin = decouper_url(url)
    sortie_fichier = None
    if premiere and o.get("output") and o["output"] != "-":
        sortie_fichier = o["output"]
    elif premiere and o.get("remote-name"):
        sortie_fichier = posixpath.basename(chemin.split("?")[0])
        if not sortie_fichier:
            if _montrer_erreurs(o):
                ctx.err("curl: Remote file name has no length\n"
                        "curl: (23) Failed writing received data to disk/application\n")
            return 23
    vers_ecran = sortie_fichier is None and ctx.sortie.tty
    progres = not silencieux and not o.get("no-progress-meter") and not vers_ecran
    tete = bool(o.get("head"))
    methode = o.get("request") or ("HEAD" if tete else ("POST" if o["data"] else "GET"))
    corps_envoi = b""
    if o["data"]:
        parts = []
        for genre, v in o["data"]:
            if v.startswith("@") and genre != "data-raw":
                vp = ctx.chemin(v[1:])
                try:
                    v = ctx.vfs.lire(vp).decode("utf-8", "replace")
                except ErreurFs:
                    ctx.err(f"Warning: Couldn't read data from file \"{v[1:]}\", this makes an empty POST.\n")
                    v = ""
                if genre != "data-binary":
                    v = v.replace("\r", "").replace("\n", "")
            parts.append(v)
        corps_envoi = "&".join(parts).encode("utf-8")
    agent = o.get("user-agent", AGENT)
    entetes = [f"{methode} {chemin} HTTP/1.1", f"Host: {hote}:{port}"]
    perso = {}
    for h in o["header"]:
        k, _, v = h.partition(":")
        perso[k.strip().lower()] = (k.strip(), v.strip())
    if "user-agent" not in perso and agent:
        entetes.append(f"User-Agent: {agent}")
    if "accept" not in perso:
        entetes.append("Accept: */*")
    if o.get("referer"):
        entetes.append(f"Referer: {o['referer']}")
    for k, (nom, v) in perso.items():
        if k == "host":
            entetes[1] = f"Host: {v}"
        elif v:
            entetes.append(f"{nom}: {v}")
    if corps_envoi or o["data"]:
        entetes.append(f"Content-Length: {len(corps_envoi)}")
        if "content-type" not in perso:
            entetes.append("Content-Type: application/x-www-form-urlencoded")
    brut = ("\r\n".join(entetes) + "\r\n\r\n").encode("latin-1", "replace") + corps_envoi
    if bavard:
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", hote):
            ctx.err(f"* Host {hote}:{port} was resolved.\n* IPv6: ::1\n* IPv4: 127.0.0.1\n")
    if progres:
        ctx.err(TETE_PROGRES + "\r" + ligne_progres(0, 0, 0, 0, 0, 0))
    ecrivable = True
    if sortie_fichier:                       # comme le vrai curl : le fichier est ouvert avant la réponse
        vp_f = ctx.chemin(sortie_fichier)
        parent = posixpath.dirname(vp_f)
        ecrivable = vp_f == "/dev/null" or (ctx.vfs.est_dossier(parent) and ctx.vfs.ecriture_permise(vp_f)
                                            and not ctx.vfs.est_dossier(vp_f))
        if not ecrivable and _montrer_erreurs(o):
            pourquoi = "No such file or directory" if not ctx.vfs.est_dossier(parent) else (
                "Is a directory" if ctx.vfs.est_dossier(vp_f) else "Permission denied")
            ctx.err(f"Warning: Failed to open the file {sortie_fichier}: {pourquoi}\n")
    if bavard:
        ctx.err(f"*   Trying 127.0.0.1:{port}...\n")
    debut = time.monotonic()
    try:
        delai = float(o.get("max-time") or 10)
    except ValueError:
        delai = 10
    try:
        try:
            reponse = requete(hote, port, brut, delai=delai)
        except ConnectionRefusedError:
            # le phare du Port dort (il s'éteint seul après 30 minutes sans visite) : comme sur le téléphone, le jeu
            # le rallume, puis curl frappe encore une fois
            if not _rallumer_phare():
                raise
            reponse = requete(hote, port, brut, delai=delai)
    except OSError:
        ms = int((time.monotonic() - debut) * 1000)
        if progres:
            ctx.err("\n")
        if bavard:
            ctx.err(f"* connect to 127.0.0.1 port {port} from 127.0.0.1 port 0 failed: Connection refused\n"
                    f"* Failed to connect to {hote} port {port} after {ms} ms: Couldn't connect to server\n"
                    "* Closing connection\n")
        if _montrer_erreurs(o):
            ctx.err(f"curl: (7) Failed to connect to {hote} port {port} after {ms} ms: Couldn't connect to server\n")
        return 7
    duree = time.monotonic() - debut
    etat, entetes_brutes, d, corps = lire_reponse(reponse, tete=(methode == "HEAD"))
    code_http = _code_http(etat)
    if bavard:
        ctx.err(f"* Connected to {hote} (127.0.0.1) port {port}\n")
        for l in entetes:
            ctx.err(f"> {l}\r\n")
        ctx.err(">\x20\r\n")
        for l in entetes_brutes.split(b"\r\n")[:-2]:
            ctx.err(b"< " + l + b"\r\n")
        ctx.err("<\x20\r\n")
        if corps and not vers_ecran:
            ctx.err(f"{{ [{len(corps)} bytes data]\n")
    attendu = int(d.get("content-length", len(corps)) or 0) if d.get("content-length", "").isdigit() else len(corps)
    echec = bool(o.get("fail") and code_http >= 400)
    recu = 0 if (echec or not ecrivable) else len(corps)
    if progres:
        ctx.err("\r" + ligne_progres(attendu + len(corps_envoi), recu, attendu, len(corps_envoi),
                                     len(corps_envoi), duree) + "\n")
    if bavard:
        ctx.err("* Closing connection\n")
    # suivre une redirection (-L), seulement vers le phare
    if o.get("location") and 300 <= code_http < 400 and d.get("location") and sauts < 10:
        suite = d["location"]
        if suite.startswith("/"):
            suite = f"http://{hote}:{port}{suite}"
        return _une(ctx, o, suite, premiere, sauts + 1)
    if echec:
        if _montrer_erreurs(o):
            ctx.err(f"curl: (22) The requested URL returned error: {code_http}\n")
        return 22
    sortie = b""
    if tete or o.get("include"):
        sortie += entetes_brutes
    if not tete:
        sortie += corps
    if sortie_fichier:
        try:
            if not ecrivable:
                raise ErreurFs(13)
            ctx.vfs.ecrire(ctx.chemin(sortie_fichier), sortie)
        except ErreurFs:
            if _montrer_erreurs(o):
                ctx.err("curl: (23) Failure writing output to destination\n")
            return 23
    else:
        ctx.out(sortie)
    if o.get("write-out"):
        ctx.out(_write_out(o["write-out"], {
            "http_code": f"{code_http:03d}", "response_code": f"{code_http:03d}",
            "content_type": d.get("content-type", ""), "size_download": len(corps),
            "size_header": len(entetes_brutes), "size_upload": len(corps_envoi), "url_effective": url,
            "url": url, "method": methode, "num_redirects": sauts, "scheme": "HTTP",
            "remote_ip": "127.0.0.1", "remote_port": port, "time_total": f"{duree:.6f}",
            "exitcode": 0, "http_version": etat.split()[0].split("/")[-1] if etat else ""}))
    return 0
