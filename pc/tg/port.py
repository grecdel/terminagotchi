"""⚓ Le Port — réseaux (docs/programme.md § 2.12, paliers P1 à P5, et § 7.2, paliers P6 à P11).

Le premier monde de la phase 5. Il s'ouvre selon l'arbre du Carrefour (§ 2.9) : ses prérequis sont les niveaux 0 à
4 du tronc commun (se repérer, bâtir, lire et chercher, le premier tuyau), c'est-à-dire, dans l'histoire, le
chapitre 2 (le nid) et le chapitre 5 (la bibliothèque, où passe le premier tuyau) finis. Il ne ferme rien : on peut
en sortir et y revenir, l'étape atteinte est gardée (comme les ailes).

LE RÉSEAU SIMULÉ DU TERMINAWORLD (port.json, mêmes données sur Android : Port.kt) : chaque biome est une machine
(feu.terminaworld 127.42.0.2, eau.terminaworld 127.42.0.3…), la Racine est le routeur, le camp de base est localhost
(127.0.0.1). Les adresses sont des adresses de BOUCLE LOCALE (127.0.0.0/8, RFC 1122 § 3.2.1.3) : même une vraie
commande qui les vise (`ping -c 1 127.42.0.2` sous Linux) ne sort jamais de l'ordinateur. Les phares (les liens)
relient les machines ; un messager (un paquet) va de phare en phare avec sa durée de vie (TTL), se perd si un phare
est éteint sans détour possible, revient avec la réponse. Tout est déterministe (vecteurs communs
donnees/port/vecteurs.json, vérifiés en Python et en Kotlin).

LES VRAIES COMMANDES, toujours locales : `hostname`, `ip a`, `ping -c 3 localhost`, `cat /etc/hosts`, `getent hosts
localhost`, `curl` sur le PHARE DU PORT (un petit serveur HTTP lancé par le jeu, seulement sur 127.0.0.1:8042, qui
ne sert que des pages fabriquées par le jeu, jamais un fichier de l'ordinateur ; il s'éteint seul après 30 minutes
sans visite), `ssh -V`, `ssh-keygen` dans le terrain, `python3 -m http.server 8000 --bind 127.0.0.1` (le serveur de
l'enfant, attaché à la boucle locale : personne d'autre sur le Wi-Fi ne le voit), `ss -tln`, `ip route`,
`tracepath -n 127.0.0.1`, `ip neigh`, et `curl https://localhost:8443` (le sceau : un certificat auto-signé fabriqué
par openssl sur cette machine, puis `--cacert` pour le reconnaître). Jamais de scan, jamais une vraie cible
extérieure, aucune donnée personnelle (la clé ssh porte le commentaire « explorateur »).

LES COMMANDES DU JEU (`port …`, alias `port='tg port'` posé par `tg installer`) simulent ce qu'on ne peut pas faire
sans danger : la carte des machines, l'annuaire, la table de routage, le messager, les phares éteints, le guidage
d'un messager (l'exploit « un messager guidé sans perte »), la course TCP / UDP, les couches, le gardien de
l'immeuble (box, DHCP, NAT) et les sceaux (l'exploit « le sceau vérifié »). Ce qu'elles font s'écrit dans le carnet
de bord du port (~/terrain_terminagotchi/port/carnet_de_bord.txt) : la carte que l'enfant dessine lui-même, et ce
que les étapes vérifient (lignes « [guide] … ok », « [sceau] … ok »…).
"""
import json
import os
import pkgutil
import random
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import core
from .langue import t
from .plateforme import BOLD, C, DIM, IS_WIN, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "port.json").decode("utf-8"))
    return _D


def machines():
    return donnees()["machines"]


def machine(mid):
    return next((m for m in machines() if m["id"] == mid), None)


def ids():
    return [m["id"] for m in machines()]


def nom_complet(mid):
    """feu → feu.terminaworld ; camp → localhost."""
    m = machine(mid)
    if not m:
        return mid
    return m.get("nom") or f"{mid}.{donnees()['domaine']}"


def chercher(nom):
    """Un nom tapé (feu, feu.terminaworld, 127.42.0.2, localhost, camp) → l'identifiant de la machine, ou None."""
    n = (nom or "").strip().lower().rstrip(".")
    for m in machines():
        if n in (m["id"], m["adresse"], nom_complet(m["id"]), m.get("nom", "")):
            return m["id"]
    if n == "127.0.0.1":
        return "camp"
    return None


PORT_PHARE = 8042
PORT_SCEAU = 8443


def _ports():
    p = donnees().get("phare", {})
    return p.get("port", PORT_PHARE), p.get("sceau", PORT_SCEAU)


# ================================================================ le réseau simulé (spécification pure)
def voisins(mid, eteints=()):
    """Les machines reliées à mid par un phare allumé, dans l'ordre des liens (déterministe)."""
    out = []
    for a, b in donnees()["liens"]:
        if a == mid and b not in eteints:
            out.append(b)
        elif b == mid and a not in eteints:
            out.append(a)
    return out


def relies(a, b):
    return any({a, b} == {x, y} for x, y in donnees()["liens"])


def route(depart, arrivee, eteints=()):
    """Le chemin le plus court (en sauts) de depart à arrivee, en évitant les phares éteints : [depart, …, arrivee],
    ou None. À égalité, l'ordre des liens décide (comme une table de routage figée)."""
    if depart in eteints or arrivee in eteints:
        return None
    avant = {depart: None}
    file = [depart]
    while file:
        x = file.pop(0)
        if x == arrivee:
            chemin = [x]
            while avant[chemin[-1]] is not None:
                chemin.append(avant[chemin[-1]])
            return chemin[::-1]
        for v in voisins(x, eteints):
            if v not in avant:
                avant[v] = x
                file.append(v)
    return None


def table(mid, eteints=()):
    """La table de routage d'une machine : [(destination, passerelle, sauts)] pour chaque autre machine joignable
    (la passerelle = le premier phare du chemin) ; la route par défaut d'une machine qui n'a qu'un voisin passe par lui."""
    out = []
    for d in ids():
        if d == mid:
            continue
        r = route(mid, d, eteints)
        if r:
            out.append((d, r[1], len(r) - 1))
    return out


def guider(chemin, eteints=(), depart="camp", ttl=None):
    """Le messager suit le chemin que l'enfant donne (les machines dans l'ordre, sans le camp). Renvoie
    {ok, sauts: [machines atteintes], raison: arrive|inconnue|pas_relie|eteint|ttl|vide, ou: machine fautive, ttl}."""
    ttl = donnees()["ttl"] if ttl is None else ttl
    pas = [chercher(x) or x for x in chemin]
    if pas and pas[0] == depart:
        pas = pas[1:]
    if not pas:
        return {"ok": False, "sauts": [depart], "raison": "vide", "ou": None, "ttl": ttl}
    ici = depart
    sauts = [depart]
    for x in pas:
        if x not in ids():
            return {"ok": False, "sauts": sauts, "raison": "inconnue", "ou": x, "ttl": ttl}
        if not relies(ici, x):
            return {"ok": False, "sauts": sauts, "raison": "pas_relie", "ou": x, "ttl": ttl}
        if x in eteints:
            return {"ok": False, "sauts": sauts, "raison": "eteint", "ou": x, "ttl": ttl}
        if ttl <= 0:
            return {"ok": False, "sauts": sauts, "raison": "ttl", "ou": x, "ttl": ttl}
        ttl -= 1
        sauts.append(x)
        ici = x
    return {"ok": True, "sauts": sauts, "raison": "arrive", "ou": ici, "ttl": ttl}


def course():
    """La course TCP / UDP (P8) : les mêmes paquets, le même réseau qui en perd deux et en mélange deux.
    TCP : chaque paquet perdu est renvoyé (accusés de réception), tout arrive dans l'ordre, en plus d'allers-retours.
    UDP : rien n'est renvoyé, les paquets arrivent tels quels (perdus, et dans le désordre)."""
    c = donnees()["course"]
    n, perdus, des = c["paquets"], c["perdus"], c["desordre"]
    udp = [i for i in range(1, n + 1) if i not in perdus]
    if all(x in udp for x in des):            # deux paquets échangés en route
        a, b = udp.index(des[0]), udp.index(des[1])
        udp[a], udp[b] = udp[b], udp[a]
    tcp_envois = list(range(1, n + 1)) + list(perdus)        # les renvois après les accusés manquants
    return {"tcp": {"recus": list(range(1, n + 1)), "envois": len(tcp_envois), "renvoyes": list(perdus), "ordre": True},
            "udp": {"recus": udp, "envois": n, "perdus": list(perdus), "ordre": udp == sorted(udp)}}


SANS_ACCENT = str.maketrans("éèêàçôûî", "eeeacoui")


def couches_ok(texte):
    """Les 4 couches dans l'ordre, de la lettre au camion (application, transport, réseau, liaison), accents et
    majuscules sans importance ; les mots du modèle OSI « internet », « lien » et « physique » sont acceptés."""
    mots = re.findall(r"[a-zà-ÿ]+", (texte or "").lower().translate(SANS_ACCENT))
    syn = {"internet": "reseau", "network": "reseau", "lien": "liaison", "link": "liaison", "physique": "liaison",
           "liaisons": "liaison"}
    mots = [syn.get(m, m) for m in mots if syn.get(m, m) in donnees()["couches"]]
    return mots == donnees()["couches"]


def gardien(n=None):
    """Le gardien de l'immeuble (P10) : la box distribue des adresses privées (DHCP) aux nouveaux appareils de la
    maison, et toutes sortent sur Internet avec UNE adresse publique (NAT). Adresses : 192.168.1.0/24 (privée,
    RFC 1918) et 203.0.113.7 (adresse de documentation, RFC 5737 : elle n'appartient à personne)."""
    g = donnees()["gardien"]
    apps = g["appareils"][: n if n is not None else len(g["appareils"])]
    base = g["box"].rsplit(".", 1)[0]
    return {"box": g["box"], "publique": g["publique"],
            "baux": [(a, f"{base}.{g['premier'] + i}") for i, a in enumerate(apps)]}


def sceaux(graine):
    """Les 4 sceaux dans l'ordre de cette partie (le vrai n'est pas toujours au même endroit) : [(n°, sceau)]."""
    s = list(donnees()["sceaux"])
    random.Random(f"sceaux:{graine}").shuffle(s)
    return [(i + 1, x) for i, x in enumerate(s)]


def vrai_sceau(graine):
    return next(i for i, x in sceaux(graine) if x["raison"] == "ok")


def annuaire():
    """L'annuaire du port, au format de /etc/hosts (adresse, nom complet, nom court)."""
    out = []
    for m in machines():
        if m["id"] == "camp":
            out.append(f"{m['adresse']}\tlocalhost camp")
        else:
            out.append(f"{m['adresse']}\t{nom_complet(m['id'])} {m['id']}")
    return out


# ================================================================ le phare du port (le vrai petit serveur HTTP)
def page(chemin, hote=None):
    """La réponse du phare à GET chemin : (code, corps texte). Rien d'autre que des pages fabriquées ici."""
    c = (chemin or "/").split("?", 1)[0].strip("/").lower()
    if not c and hote:                       # une machine visitée à son adresse (127.42.0.2:8042/)
        mid = chercher(hote.split(":")[0])
        if mid and mid != "camp":
            c = mid
    if not c:
        lignes = [t("port.page.accueil")]
        for m in machines():
            lignes.append(f"/{m['id']:<8} {m['icone']} {nom_complet(m['id'])} ({m['adresse']})")
        return 200, "\n".join(lignes) + "\n"
    if c == "courrier":                      # la Citadelle (le faux facteur) : le vrai courrier du capitaine
        return 200, t("cit.page.courrier") + "\n" + t("port.page.pied", port=_ports()[0]) + "\n"
    mid = chercher(c)
    if mid and mid in donnees()["pages"]:
        m = machine(mid)
        return 200, (f"{m['icone']} {nom_complet(mid)} ({m['adresse']})\n" + t(f"port.page.{mid}") + "\n"
                     + t("port.page.pied", port=_ports()[0]) + "\n")
    return 404, t("port.page.404", chemin="/" + c) + "\n"


def _gestionnaire(etat):
    from http.server import BaseHTTPRequestHandler

    class Phare(BaseHTTPRequestHandler):
        server_version = "PhareDuPort/1.0"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def _repondre(self, corps=True):
            etat["vu"] = time.time()
            if self.path.startswith("/__arret"):
                code, texte = 200, "ok\n"
                threading.Thread(target=etat["arreter"], daemon=True).start()
            else:
                hote = self.server.server_address[0]
                code, texte = page(self.path, None if hote == "127.0.0.1" else hote)
            b = texte.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Connection", "close")
            self.end_headers()
            if corps:
                self.wfile.write(b)

        def do_GET(self):  # noqa: N802
            self._repondre()

        def do_HEAD(self):  # noqa: N802
            self._repondre(False)

        def log_message(self, *a):           # rien sur la sortie : le phare est discret
            pass

        def version_string(self):
            return self.server_version

    return Phare


def dossier_jeu():
    return core.SAVE_DIR / "port"


def fabriquer_sceau():
    """Le certificat auto-signé du phare (openssl, sur cette machine, valable 10 ans, seulement pour localhost et
    127.0.0.1) : (certificat, clé) ou None si openssl manque. La clé ne quitte jamais ~/.terminagotchi/port/ ; le
    certificat public est posé sur le quai par poser_sceau (celui du phare qui tourne vraiment)."""
    d = dossier_jeu()
    cert, cle = d / "sceau.pem", d / "sceau_cle.pem"
    if not (cert.is_file() and cle.is_file()):
        try:
            d.mkdir(parents=True, exist_ok=True)
            tc, tk = d / f".sceau.{os.getpid()}.pem", d / f".cle.{os.getpid()}.pem"
            r = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
                                "-keyout", str(tk), "-out", str(tc), "-subj", "/CN=localhost",
                                "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
                               capture_output=True, timeout=30)
            if r.returncode != 0:
                return None
            os.chmod(tk, 0o600)
            if not (cert.is_file() and cle.is_file()):      # deux processus en même temps : le premier gagne
                os.replace(tk, cle)
                os.replace(tc, cert)
            for f in (tc, tk):
                if f.exists():
                    f.unlink()
        except (OSError, subprocess.SubprocessError):
            return None
    return cert, cle


def phare(attendre=True, repos=None):
    """Allume le phare : HTTP sur 127.0.0.1:8042 (et sur l'adresse de chaque machine du Terminaworld quand le système
    le permet, Linux : toute la boucle locale 127.0.0.0/8 répond), HTTPS sur 127.0.0.1:8443 si openssl a fabriqué le
    sceau. S'éteint seul après repos minutes sans visite. Renvoie les serveurs (attendre=False, pour les tests)."""
    from http.server import ThreadingHTTPServer
    port, port_sceau = _ports()
    repos = donnees()["phare"].get("repos_minutes", 30) if repos is None else repos
    etat = {"vu": time.time()}
    serveurs = []

    def arreter():
        def un(s):
            try:
                s.shutdown()
                s.server_close()
            except Exception:                 # noqa: BLE001
                pass
        fils = [threading.Thread(target=un, args=(s,), daemon=True) for s in serveurs]   # tous ensemble (vite)
        for f in fils:
            f.start()
        for f in fils:
            f.join(5)
    etat["arreter"] = arreter
    G = _gestionnaire(etat)
    if phare_allume(port):
        return None                             # déjà allumé : rien à faire
    sc = fabriquer_sceau()                      # le sceau d'abord : quand le phare répond, il est prêt (pas de course)
    try:
        serveurs.append(ThreadingHTTPServer(("127.0.0.1", port), G))
    except OSError:
        return None                             # le port est pris : rien à faire
    if not IS_WIN and sys.platform.startswith("linux"):
        for m in machines():
            if m["adresse"].startswith("127.42."):
                try:
                    serveurs.append(ThreadingHTTPServer((m["adresse"], port), G))
                except OSError:
                    pass
    if sc:
        try:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(sc[0]), str(sc[1]))
            s = ThreadingHTTPServer(("127.0.0.1", port_sceau), G)
            s.socket = ctx.wrap_socket(s.socket, server_side=True)
            serveurs.append(s)
        except (OSError, ImportError, ValueError):
            pass
    for s in serveurs:
        s.daemon_threads = True
        threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.3}, daemon=True).start()
    if not attendre:
        return serveurs
    try:
        while time.time() - etat["vu"] < repos * 60 and serveurs[0].socket.fileno() >= 0:
            time.sleep(2)
            try:
                with socket.create_connection(("127.0.0.1", port), 0.5):
                    pass
            except OSError:
                break
    except KeyboardInterrupt:
        pass
    arreter()
    return serveurs


def phare_allume(port=None):
    try:
        with socket.create_connection(("127.0.0.1", port or _ports()[0]), 0.4):
            return True
    except OSError:
        return False


def assurer_phare():
    """Allume le phare en arrière-plan s'il est éteint (un processus détaché, qui s'éteint seul). Vrai s'il répond."""
    if phare_allume():
        return True
    paquet = str(Path(__file__).resolve().parent.parent)          # le dossier (ou le .pyz) qui contient « tg »
    code = f"import sys; sys.path.insert(0, {paquet!r}); from tg import port; port.lancer_phare()"
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WIN:
        kw["creationflags"] = 0x00000008 | 0x00000200        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen([sys.executable, "-c", code], **kw)
    except OSError:
        return False
    for _ in range(30):
        if phare_allume():
            return True
        time.sleep(0.1)
    return False


def lancer_phare():
    """Le processus du phare : la langue de la partie, puis le serveur."""
    from . import langue
    try:
        st = core.load() or {}
        langue.appliquer(st)
    except Exception:                         # noqa: BLE001
        pass
    phare()


def eteindre_phare():
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{_ports()[0]}/__arret", timeout=2).read()
        return True
    except OSError:
        return False


# ================================================================ l'état, le terrain, le carnet de bord
def p_(state):
    p = state.setdefault("port", {})
    p.setdefault("eteints", [])
    p.setdefault("releves", [])
    return p


def dossier():
    return core.TERRAIN / "port"


CARNET = "carnet_de_bord.txt"


def noter(etiquette, texte):
    """Une ligne dans le carnet de bord (« [guide] … ok ») : la carte et le journal que l'enfant garde."""
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\b{mot}\b", carnet(), re.M) is not None


def meubles(state):
    """Ce que le jeu pose dans le port quand il s'ouvre : {chemin relatif au terrain: texte}."""
    return {"port/panneau.txt": t("port.meuble.panneau", nom=state.get("name", "")),
            "port/annuaire.txt": "\n".join(annuaire()),
            f"port/{CARNET}": t("port.meuble.carnet") + "\n",
            "port/quai/LISEZ_MOI.txt": t("port.meuble.quai"),
            "port/teleporteur.txt": t("port.meuble.teleporteur")}


# les leçons dont une étape a besoin du phare allumé (port3, port6, port7, port11), et celles juste avant : histoire.meubler
# passe avec la leçon d'AVANT le tour où l'étape change, et le phare doit déjà répondre à la toute première commande
LECONS_PHARE = ("port2", "port3", "port5", "port6", "port7", "port10", "port11")


def meubler(state, lid, step):
    """Appelé par histoire.meubler : le phare s'allume pour les leçons qui le visitent ; le sceau est posé."""
    if lid in LECONS_PHARE and dossier().is_dir():
        if assurer_phare() and lid == "port11":
            poser_sceau()


def poser_sceau():
    """Le notaire confie le sceau : le certificat PUBLIC que présente le phare qui tourne vraiment (127.0.0.1:8443) est
    posé sur le quai (port/sceau_du_phare.pem) ; c'est lui que `curl --cacert` reconnaîtra. Rien ne sort de la machine."""
    try:
        import ssl
        try:
            pem = ssl.get_server_certificate(("127.0.0.1", _ports()[1]), timeout=3)
        except TypeError:                                   # Python < 3.10 : sans délai
            pem = ssl.get_server_certificate(("127.0.0.1", _ports()[1]))
    except (OSError, ImportError, ValueError):
        return False
    try:
        f = dossier() / "sceau_du_phare.pem"
        if not f.is_file() or f.read_text(encoding="ascii", errors="replace") != pem:
            f.write_text(pem, encoding="ascii")
        return True
    except OSError:
        return False


# ================================================================ les leçons (même format que histoire.NOUVELLES)
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
CURL = r"^(curl|curl\.exe)\b"
PORT = r"^(tg\s+)?port\s+"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


def _fichier(rel):
    return lambda: (core.TERRAIN / rel).is_file()


def _contient(rel, motif):
    def f():
        try:
            return re.search(motif, (core.TERRAIN / rel).read_text(encoding="utf-8", errors="replace"), re.I) is not None
        except OSError:
            return False
    return f


FS = {
    "port_colis": _contient("port/colis.html", r"feu\.terminaworld"),
    "port_cle": _contient("port/cle_du_port.pub", r"^ssh-"),
    "port_quai": _contient("port/quai/index.html", r"\S"),
    "port_couches": lambda: couches_ok((core.TERRAIN / "port" / "couches.txt").read_text(encoding="utf-8", errors="replace")
                                       if (core.TERRAIN / "port" / "couches.txt").is_file() else ""),
    "port_guide": lambda: dans_carnet("guide"),
    "port_sceau": lambda: dans_carnet("sceau"),
}
CREE = {"port_colis": "port/colis.html", "port_cle": "port/cle_du_port.pub", "port_quai": "port/quai/index.html",
        "port_couches": "port/couches.txt"}

U = f"http://localhost:{PORT_PHARE}"
LECONS = {
    # P0 — l'arrivée au port
    "port0": {"titre": "hist.port0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "port"}), "cmd": "cd ~/terrain_terminagotchi/port", "ici": "port",
         "bravo": ("hist.entree.bravo", {"piece": "port"})},
        _n("port0", 1, cmd=C("ls", "dir"), re=LS, ou="port"),
        _n("port0", 2, cmd=C("cat panneau.txt", "type panneau.txt"), re=LIRE + r".*panneau"),
    ]},
    # P1 — qui suis-je sur le réseau ?
    "port1": {"titre": "hist.port1.titre", "skill": None, "steps": [
        _n("port1", 0, cmd="hostname", re=r"^hostname\b"),
        _n("port1", 1, cmd=C("ip a", "ipconfig", mac="ifconfig"), re=r"^(ip\s+(-\d\s+)?a(ddr(ess)?)?\b|ifconfig|ipconfig)",
           absent_ok=True),
        _n("port1", 2, cmd=C("ping -c 3 localhost", "ping -n 3 localhost"), re=r"^ping\b.*\b(localhost|127\.0\.0\.1)\b"),
    ]},
    # P2 — l'annuaire (DNS) : le vrai /etc/hosts, la vraie recherche de nom, puis l'annuaire du port
    "port2": {"titre": "hist.port2.titre", "skill": None, "steps": [
        _n("port2", 0, cmd=C("cat /etc/hosts", r"type C:\Windows\System32\drivers\etc\hosts"),
           re=r"^(cat|less|more|head|type|gc|get-content)\b.*hosts\b"),
        _n("port2", 1, cmd=C("getent hosts localhost", "Resolve-DnsName localhost", mac="dscacheutil -q host -a name localhost"),
           re=r"^(getent\s+hosts|resolve-dnsname|dscacheutil)\b.*localhost", absent_ok=True),
        _n("port2", 2, cmd=C("grep feu annuaire.txt", "Select-String feu annuaire.txt"),
           re=r"^(grep|select-string|sls|findstr)\b.*\bfeu\b.*annuaire"),
    ]},
    # P3 — le facteur (HTTP) : le phare du port répond pour de vrai, sur la boucle locale
    "port3": {"titre": "hist.port3.titre", "skill": None, "steps": [
        _n("port3", 0, cmd=f"curl -I {U}/", re=CURL + r".*(\s-\w*I\b|\s--head\b).*(localhost|127\.0\.0\.1):8042"),
        _n("port3", 1, cmd=f"curl -s {U}/eau | head -n 3", re=CURL + r".*(localhost|127\.0\.0\.1):8042/eau\b.*\|\s*head\b"),
        _n("port3", 2, cmd=f"curl -o colis.html {U}/feu", fs="port_colis"),
        _n("port3", 3, cmd=f"curl -I {U}/volcan_perdu", re=CURL + r".*(\s-\w*I\b|\s--head\b).*8042/(?!(eau|feu|glace|plante|roche|ciel|"
           r"ombre|machine|poison|racine|camp)\b)\w"),
    ]},
    # P4 — le téléporteur (ssh, notions) : la paire de clés, fabriquée dans le terrain
    "port4": {"titre": "hist.port4.titre", "skill": None, "steps": [
        _n("port4", 0, cmd="ssh -V", re=r"^ssh\s+-V\b", absent_ok=True),
        _n("port4", 1, cmd='ssh-keygen -t ed25519 -N "" -C explorateur -f cle_du_port', fs="port_cle", outil="ssh-keygen"),
        _n("port4", 2, cmd=C("cat cle_du_port.pub", "type cle_du_port.pub"), re=LIRE + r".*cle_du_port\.pub", outil="ssh-keygen"),
    ]},
    # P5 — mon premier serveur (attaché à la boucle locale : personne d'autre ne le voit)
    "port5": {"titre": "hist.port5.titre", "skill": None, "steps": [
        _n("port5", 0, cmd='echo "Bienvenue sur mon quai" > quai/index.html', fs="port_quai"),
        _n("port5", 1, cmd="python3 -m http.server 8000 --bind 127.0.0.1 --directory quai &",
           re=r"^(python3?|py)\s+-m\s+http\.server\b.*(--bind[=\s]+|\s-b\s+)(127\.0\.0\.1|localhost)\b", win=False),
        _n("port5", 2, cmd="curl http://localhost:8000", re=CURL + r".*(localhost|127\.0\.0\.1):8000"),
        _n("port5", 3, cmd="kill %1", re=r"^kill\b", win=False),
    ]},
    # P6 — les enveloppes dans les enveloppes (le modèle en couches)
    "port6": {"titre": "hist.port6.titre", "skill": None, "steps": [
        _n("port6", 0, cmd=f"curl -v {U}/", re=CURL + r".*\s-\w*v\b.*8042"),
        _n("port6", 1, cmd="port couches", re=PORT + r"couches\b"),
        _n("port6", 2, cmd='echo "application transport reseau liaison" > couches.txt', fs="port_couches"),
    ]},
    # P7 — les quais et les portes (adresse IP + port)
    "port7": {"titre": "hist.port7.titre", "skill": None, "steps": [
        _n("port7", 0, cmd=C("ss -tln", "netstat -an", mac="netstat -an -p tcp"), re=r"^(ss\s+-\w*l|netstat\b)", absent_ok=True),
        _n("port7", 1, cmd=C("ss -tln | grep 8042", "netstat -an | findstr 8042", mac="netstat -an -p tcp | grep 8042"),
           re=r"^(ss|netstat)\b.*\|\s*(grep|findstr|select-string)\s+\S*8042", absent_ok=True),
        _n("port7", 2, cmd="port carte", re=PORT + r"carte\b"),
    ]},
    # P8 — recommandé ou carte postale (TCP et UDP)
    "port8": {"titre": "hist.port8.titre", "skill": None, "steps": [
        _n("port8", 0, cmd=C("ss -t", "netstat -p tcp", mac="netstat -p tcp"), re=r"^(ss\s+-\w*t|netstat\b.*tcp)", absent_ok=True),
        _n("port8", 1, cmd=C("ss -u", "netstat -p udp", mac="netstat -p udp"), re=r"^(ss\s+-\w*u|netstat\b.*udp)", absent_ok=True),
        _n("port8", 2, cmd="port course", re=PORT + r"course\b"),
    ]},
    # P9 — les phares et les relais (routage) ; le messager guidé sans perte (exploit)
    "port9": {"titre": "hist.port9.titre", "skill": None, "steps": [
        _n("port9", 0, cmd=C("ip route", "route print", mac="netstat -rn"), re=r"^(ip\s+(-\d\s+)?r(oute)?\b|route\s+print|netstat\s+-\w*r)",
           absent_ok=True),
        _n("port9", 1, cmd=C("tracepath -n 127.0.0.1", "tracert -d 127.0.0.1", mac="traceroute -n 127.0.0.1"),
           re=r"^(tracepath|traceroute|tracert)\b.*(127\.0\.0\.1|localhost)", absent_ok=True,
           repli=["traceroute -n 127.0.0.1"]),
        _n("port9", 2, cmd="port messager feu", re=PORT + r"messager\s+\S+"),
        _n("port9", 3, cmd="port eteins roche", re=PORT + r"[eé]teins\s+roche\b"),
        _n("port9", 4, cmd="port guide racine … feu", fs="port_guide", exploit="port.messager"),
    ]},
    # P10 — le gardien de l'immeuble (box, DHCP, NAT)
    "port10": {"titre": "hist.port10.titre", "skill": None, "steps": [
        _n("port10", 0, cmd=C("ip route | grep default", "ipconfig | findstr Passerelle", mac="netstat -rn | grep default"),
           re=r"(^ip\s+(-\d\s+)?r(oute)?\b.*\|\s*grep\s+default|^ipconfig\b|^netstat\s+-\w*r)", absent_ok=True),
        _n("port10", 1, cmd=C("ip neigh", "arp -a", mac="arp -a"), re=r"^(ip\s+(-\d\s+)?n(eigh(bour)?)?\b|arp\b)", absent_ok=True),
        _n("port10", 2, cmd="port gardien", re=PORT + r"gardien\b"),
    ]},
    # P11 — l'enveloppe scellée (HTTPS, TLS) ; le sceau vérifié (exploit)
    "port11": {"titre": "hist.port11.titre", "skill": None, "steps": [
        _n("port11", 0, cmd=f"curl https://localhost:{PORT_SCEAU}", re=CURL + r".*https://(localhost|127\.0\.0\.1):8443",
           echoue=True, outil="openssl"),
        _n("port11", 1, cmd=f"curl --cacert sceau_du_phare.pem https://localhost:{PORT_SCEAU}",
           re=CURL + r".*--cacert[=\s]+\S*sceau_du_phare\.pem.*https://(localhost|127\.0\.0\.1):8443", outil="openssl"),
        _n("port11", 2, cmd="port sceau", re=PORT + r"sceau\s*$"),
        _n("port11", 3, cmd="port sceau ?", fs="port_sceau", exploit="port.sceau"),
    ]},
}
CHAPITRE = {"id": "port", "n": 11, "piece": "port", "famille": "Célestes", "monde": True,
            "lecons": [f"port{i}" for i in range(12)], "objet": "phare_miniature", "titre": "capitaine_du_port"}


# ================================================================ l'arbre du Carrefour : quand le port s'ouvre
def ouvert(state):
    """Les prérequis du Port (programme.json, « mondes » → port → requis : niveaux du tronc commun), traduits en
    chapitres de l'histoire (programme.json, « tronc »)."""
    from . import histoire, programme
    P = programme.donnees()
    m = next((x for x in P.get("mondes", []) if x["id"] == "port"), {})
    tronc = P.get("tronc", {})
    besoin = []
    for n in m.get("requis", []):
        besoin += tronc.get(n, [])
    return all(histoire.fini(state, c) for c in besoin)


def manque(state):
    """Les chapitres qui manquent encore pour ouvrir le port (leurs noms)."""
    from . import histoire, programme
    P = programme.donnees()
    m = next((x for x in P.get("mondes", []) if x["id"] == "port"), {})
    besoin = []
    for n in m.get("requis", []):
        besoin += [c for c in P.get("tronc", {}).get(n, []) if c not in besoin]
    return [histoire.nom_chapitre(c) for c in besoin if not histoire.fini(state, c)]


def _repond(hote, port_, delai=0.3):
    import socket
    try:
        with socket.create_connection((hote, port_), timeout=delai):
            return True
    except OSError:
        return False


def indice(step, tapees):
    """Un indice du Port (histoire.indice) : un trou « … » ou « ? » recopié tel quel, un messager perdu, un faux
    sceau. Le carnet de bord dit ce qui s'est passé (la dernière ligne [guide] ou [sceau])."""
    fs = step.get("fs")
    cmd = step.get("cmd") or ""
    if cmd.startswith("python3 -m http.server") and any(SANS_BIND.search((l or "").strip()) for l, _c in tapees):
        return t("port.lanterne.ouverte")               # la lanterne ouverte à tout le réseau : jamais « marche aussi »
    if "localhost" in cmd:                              # http://locahost:8042 : le tuyau | head cache l'erreur de curl
        for l, _c in tapees:
            for hote in re.findall(r"https?://([^/:\s]+)", l or ""):
                if hote not in ("localhost", "127.0.0.1") and not re.match(r"^127\.", hote):
                    return t("dress.indice.faute", tape=hote, attendu="localhost")
    quai = donnees()["phare"]["serveur_enfant"]
    if f":{quai}" in cmd and any(f":{quai}" in (l or "") for l, _c in tapees) and not _repond("127.0.0.1", quai):
        return t("port.indice.lanterne", port=quai)     # curl tapé trop vite (ou la lanterne éteinte) : refusé (7)
    if fs not in ("port_guide", "port_sceau"):
        return None
    lignes = [l for l, _cwd in tapees if re.match(r"^\s*(tg\s+)?port\s+(guide|sceau)\b", l or "")]
    if not lignes:
        return None
    if any(re.search(r"(…|\.\.\.|\?|<)", l) for l in lignes):
        return t("port.indice.remplace")
    if all(len(l.split()) <= (3 if l.split()[0] == "tg" else 2) for l in lignes):      # la liste relue : la règle
        return t("port.guide.aide" if fs == "port_guide" else "port.sceau.aide")
    eti = "guide" if fs == "port_guide" else "sceau"
    der = [l for l in carnet().splitlines() if l.startswith(f"[{eti}]")]
    if der and re.search(r"\((perdu|faux)\)\s*$", der[-1]):
        return t(f"port.indice.{eti}")
    return None


SANS_BIND = re.compile(r"^(python3?|py)\s+-m\s+http\.server\b(?!.*(--bind[=\s]+|\s-b\s+)(127\.|localhost|::1))")


def surveiller(state, lignes):
    """Une lanterne allumée SANS --bind 127.0.0.1 écoute sur tout le réseau local (0.0.0.0) : la créature le dit
    tout de suite, avec la commande pour l'éteindre et la bonne façon de la rallumer (jamais bloquant)."""
    for l in lignes or []:
        if SANS_BIND.search((l or "").strip()):
            msg = t("port.lanterne.ouverte")
            core.say(state, msg, 16)
            from . import histoire
            les, _e = histoire.lecon_courante(state)
            if not les or les["id"] != "port5":         # pendant P5, c'est l'indice de l'étape qui le dit
                core.terminal(state, "⚠ " + msg)
            return True
    return False


def annonce(state):
    """Le Port vient de s'ouvrir (un chapitre du tronc commun fini) : la créature le dit une fois."""
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "port" in deja or histoire.fini(state, "port") or not ouvert(state):
        return False
    deja.append("port")
    core.log(state, t("port.ouvert.log"))
    core.say(state, histoire.dire(state, "port.ouvert.dit"), 18)
    return True


# ================================================================ les commandes du jeu : tg port …
def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _c(n):
    return fg(n)


def ligne_machine(mid, eteints=()):
    m = machine(mid)
    if mid in eteints:
        return f"{DIM}{m['icone']} {nom_complet(mid):<20} {m['adresse']:<12} ✖ {t('port.eteint')}{RESET}"
    return f"{m['icone']} {_c(80)}{nom_complet(mid):<20}{RESET} {_c(75)}{m['adresse']:<12}{RESET}"


def carte(state):
    """La carte des machines du Terminaworld, leurs adresses et leurs phares (ce que l'enfant relève)."""
    p = p_(state)
    out = [f" {_c(80)}{BOLD}⚓ " + t("port.carte.titre") + RESET, ""]
    for m in machines():
        vois = ", ".join(v for v in voisins(m["id"]))
        out.append("  " + ligne_machine(m["id"], p["eteints"]) + f" {DIM}⇄ {vois}{RESET}")
    out += ["", f"  {DIM}" + t("port.carte.aide") + RESET]
    noter("carte", t("port.carnet.carte", n=len(machines())))
    return out


def _anim_saut(chemin, ok, raison=None, ou=None, retour=True):
    """Le messager en texte : ⛺ camp ─✉→ 🌳 racine ─✉→ … (et le retour)."""
    morceaux = []
    for x in chemin:
        m = machine(x)
        morceaux.append(f"{m['icone']} {x}" if m else x)
    fl = f" {_c(141)}─✉→{RESET} "
    ligne = "  " + fl.join(morceaux)
    if not ok and ou:
        ligne += f" {_c(203)}─✖ {ou}{RESET}"
    out = [ligne]
    if ok and retour:
        out.append("  " + f" {_c(141)}←✉─{RESET} ".join(reversed(morceaux)) + f"  {DIM}↩ " + t("port.retour") + RESET)
    return out


def messager(state, dest):
    p = p_(state)
    mid = chercher(dest)
    if not mid:
        return [t("port.inconnue", nom=dest), t("port.carte.aide")]
    r = route("camp", mid, p["eteints"])
    if mid == "camp":
        r = ["camp"]
    if not r:
        noter("messager", f"camp → {mid} : {t('port.perdu')} (perdu)")
        return [f" {_c(203)}✉ " + t("port.messager.perdu", dest=nom_complet(mid)) + RESET,
                "  " + t("port.messager.pas_de_route")]
    ttl = donnees()["ttl"]
    out = [f" {_c(141)}✉ " + t("port.messager.part", dest=nom_complet(mid), adresse=machine(mid)["adresse"], ttl=ttl) + RESET]
    out += _anim_saut(r, True)
    out.append("  " + t("port.messager.arrive", n=len(r) - 1, ttl=ttl - (len(r) - 1)))
    noter("messager", f"{' → '.join(r)} : {len(r) - 1} {t('port.sauts')} (ok)")
    p["releves"] = sorted(set(p["releves"]) | set(r))
    return out


def eteindre(state, mid, allumer=False):
    p = p_(state)
    if allumer and not mid:
        p["eteints"] = []
        noter("phare", t("port.tous_allumes") + " (ok)")
        return ["💡 " + t("port.tous_allumes")]
    x = chercher(mid or "")
    if not x or x == "camp":
        return [t("port.inconnue", nom=mid or "?")]
    if allumer:
        p["eteints"] = [e for e in p["eteints"] if e != x]
        noter("phare", f"{x} : {t('port.allume')} (ok)")
        return ["💡 " + t("port.phare.allume", nom=x)]
    if x not in p["eteints"]:
        p["eteints"].append(x)
    noter("eteint", f"{x} (ok)")
    autre = route("camp", "feu", p["eteints"])
    return [f"🌑 " + t("port.phare.eteint", nom=x), "  " + t("port.phare.detour" if autre else "port.phare.coupe")]


def guide(state, chemin):
    p = p_(state)
    if not p["eteints"]:                       # l'épreuve se joue avec un phare en panne (celui du programme)
        p["eteints"] = [donnees()["panne"]]
    r = guider(chemin, p["eteints"])
    out = _anim_saut(r["sauts"], r["ok"], r["raison"], r["ou"])
    if r["ok"]:
        dest = r["sauts"][-1]
        out.insert(0, f" {_c(78)}✉ " + t("port.guide.ok", dest=nom_complet(dest), n=len(r["sauts"]) - 1, ttl=r["ttl"]) + RESET)
        noter("guide", f"{' → '.join(r['sauts'])} : {t('port.sans_perte')} (ok)")
    else:
        out.insert(0, f" {_c(203)}✉ " + t(f"port.guide.{r['raison']}", ou=r["ou"] or "", ici=r["sauts"][-1]) + RESET)
        noter("guide", f"{' → '.join(r['sauts'])} ✖ {r['ou'] or ''} (perdu)")
    return out


def lignes_course():
    c = course()
    out = [f" {_c(80)}{BOLD}🏁 " + t("port.course.titre") + RESET, ""]
    tcp, udp = c["tcp"], c["udp"]
    out.append(f"  {_c(78)}📨 TCP{RESET}  " + " ".join(f"[{i}]" for i in tcp["recus"]) + "   " +
               t("port.course.tcp", envois=tcp["envois"], renvoyes=", ".join(map(str, tcp["renvoyes"]))))
    out.append(f"  {_c(214)}📮 UDP{RESET}  " + " ".join(f"[{i}]" for i in udp["recus"]) + "   " +
               t("port.course.udp", perdus=", ".join(map(str, udp["perdus"]))))
    out += ["", "  " + t("port.course.morale")]
    noter("course", "TCP " + " ".join(map(str, tcp["recus"])) + " | UDP " + " ".join(map(str, udp["recus"])) + " (ok)")
    return out


def lignes_couches():
    port = _ports()[0]
    co = donnees()["couches"]
    contenu = {"application": f"GET / HTTP/1.1 · Host: localhost:{port}", "transport": f"TCP · port {port}",
               "reseau": "IP · 127.0.0.1 → 127.0.0.1", "liaison": "lo (" + t("port.couches.boucle") + ")"}
    out = [f" {_c(80)}{BOLD}✉ " + t("port.couches.titre") + RESET, ""]
    for i, c in enumerate(co):
        pad = "  " * i
        out.append(f"  {pad}{_c(141)}┌{'─' * (46 - 2 * i)}┐{RESET}")
        out.append(f"  {pad}{_c(141)}│{RESET} {BOLD}{t('port.couche.' + c)}{RESET} {DIM}{contenu[c]}{RESET}")
    out += ["", "  " + t("port.couches.aide")]
    noter("couches", " > ".join(co) + " (ok)")
    return out


def lignes_gardien():
    g = gardien()
    out = [f" {_c(80)}{BOLD}🏢 " + t("port.gardien.titre") + RESET, "",
           "  " + t("port.gardien.box", box=g["box"])]
    for app, adr in g["baux"]:
        out.append(f"  📱 {t('port.appareil.' + app):<12} → {_c(75)}{adr}{RESET}  {DIM}(DHCP){RESET}")
    out.append("  " + t("port.gardien.nat", publique=g["publique"]))
    out += ["", f"  {DIM}" + t("port.gardien.limite") + RESET]
    noter("gardien", f"{g['box']} : " + ", ".join(a for _, a in g["baux"]) + f" → {g['publique']} (ok)")
    return out


def lignes_sceau(state, choix=None):
    gr = _graine(state)
    s = sceaux(gr)
    if choix is None:
        out = [f" {_c(80)}{BOLD}🔏 " + t("port.sceau.titre") + RESET, ""]
        for i, x in s:
            out.append(f"  {BOLD}{i}.{RESET} " + t("port.sceau.ligne", nom=x["nom"],
                                                    par=t("port.sceau.par." + ("notaire" if x["signe_par"] == "notaire" else "lui")),
                                                    perime=t("port.sceau.perime") if x["raison"] == "perime" else ""))
        out += ["", "  " + t("port.sceau.aide")]
        return out
    try:
        n = int(str(choix).strip())
    except ValueError:
        return [t("port.sceau.aide")]
    x = dict(s).get(n)
    if not x:
        return [t("port.sceau.aide")]
    if x["raison"] == "ok":
        noter("sceau", f"{n} : {t('port.sceau.verifie')} (ok)")
        return [f" {_c(78)}✔ " + t("port.sceau.ok") + RESET]
    noter("sceau", f"{n} : {x['raison']} (faux)")
    return [f" {_c(203)}✖ " + t("port.sceau.faux." + x["raison"]) + RESET]


def lignes_annuaire(nom=None):
    if not nom:
        return [f" {_c(80)}{BOLD}📖 " + t("port.annuaire.titre") + RESET] + ["  " + l for l in annuaire()]
    mid = chercher(nom)
    if not mid:
        return [t("port.annuaire.inconnu", nom=nom)]
    return [f"  {nom_complet(mid)} → {machine(mid)['adresse']}"]


def lignes_route(state, mid="camp"):
    p = p_(state)
    x = chercher(mid) or "camp"
    out = [f" {_c(80)}{BOLD}🗺 " + t("port.route.titre", nom=nom_complet(x)) + RESET]
    for d, via, n in table(x, p["eteints"]):
        out.append(f"  {machine(d)['adresse']:<12} via {machine(via)['adresse']:<12} ({via}) {DIM}{n} {t('port.sauts')}{RESET}")
    return out


def aide():
    return [f" {_c(80)}{BOLD}⚓ " + t("port.aide.titre") + RESET] + ["  " + l for l in t("port.aide.liste").split("\n")]


def commande(args, sortie=None):
    """tg port [carte|annuaire|route|messager|eteins|rallume|guide|course|couches|gardien|sceau|teleporteur|phare|stop]."""
    out = sortie if sortie is not None else sys.stdout
    a = [x for x in args]
    sous = (a[0].lower() if a else "aide").replace("é", "e")
    reste = a[1:]
    if sous == "phare":                        # le serveur (au premier plan ; le jeu le lance seul en arrière-plan)
        lancer_phare()
        return
    if sous in ("stop", "arret"):
        out.write(("💡 " + t("port.phare.stop")) if eteindre_phare() else t("port.phare.deja_eteint"))
        out.write("\n")
        return
    lignes = []

    def f(st):
        p_(st)
        if sous == "carte":
            lignes.extend(carte(st))
        elif sous == "annuaire":
            lignes.extend(lignes_annuaire(reste[0] if reste else None))
        elif sous == "route":
            lignes.extend(lignes_route(st, reste[0] if reste else "camp"))
        elif sous == "messager":
            lignes.extend(messager(st, reste[0]) if reste else [t("port.messager.aide")])
        elif sous in ("eteins", "eteindre"):
            lignes.extend(eteindre(st, reste[0] if reste else None))
        elif sous in ("rallume", "allume"):
            lignes.extend(eteindre(st, reste[0] if reste else None, allumer=True))
        elif sous == "guide":
            lignes.extend(guide(st, [x for x in reste if x not in ("…", "...")]) if reste else [t("port.guide.aide")])
        elif sous == "course":
            lignes.extend(lignes_course())
        elif sous == "couches":
            lignes.extend(lignes_couches())
        elif sous == "gardien":
            lignes.extend(lignes_gardien())
        elif sous == "sceau":
            lignes.extend(lignes_sceau(st, reste[0] if reste else None))
        elif sous in ("teleporteur", "téléporteur"):
            lignes.append(t("port.meuble.teleporteur"))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
