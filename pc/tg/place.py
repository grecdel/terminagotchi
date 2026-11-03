"""La place de la classe (idée 56, maquette validée le 3 novembre) : les visites entre les machines d'une salle.

Ce que voit l'enfant : les créatures des autres postes en cartes (« Poste 3 · Zapiot · bébé ») et trois gestes tout
faits : ☺ Coucou, ★ Bravo, ♪ Danse. Un geste reçu fait une bulle sur sa créature. Rien à écrire.

Les sécurités (toutes validées) :
  - FERMÉE PAR DÉFAUT. Seul l'enseignant l'ouvre, depuis son poste : `tg classe place ouvrir [CODE]`, avec un code de
    séance qui contient la lettre V (`tg classe creer 5 grand sanschrono place` → 05-GSV-…). Elle se ferme toute
    seule au bout de 2 heures, avec q ou Ctrl+C dans le terminal de l'enseignant, à `tg classe fin` ou
    `tg classe seance fin` sur son poste. Un élève ne la cherche que pendant une séance dont le code a la lettre V.
  - RÉSEAU LOCAL SEULEMENT. Le poste de l'enseignant sert la place sur son adresse du réseau de l'école ; les postes
    la trouvent par une annonce sur ce réseau (UDP, port 47111), ou par l'adresse écrite au tableau. Toute adresse qui
    n'est pas privée (10.…, 172.16-31.…, 192.168.…, 127.… pour les essais) est refusée, à l'envoi comme à l'arrivée :
    rien ne part sur Internet. Sans réseau local, la place n'existe pas et rien ne casse.
  - AUCUN TEXTE LIBRE. Un geste n'est qu'un numéro (0, 1, 2). Les noms de créatures et les pseudonymes ne circulent
    PAS : on montre « Poste 3 » et l'espèce (dans la langue de chaque poste).
  - AUCUNE DONNÉE PERSONNELLE, RIEN ENREGISTRÉ. Ce qui circule : le numéro de poste, l'espèce, le stade, le niveau.
    La place vit dans la mémoire du poste de l'enseignant ; rien n'est écrit sur un disque (sauf, sur chaque poste,
    son propre numéro de poste pour la séance, oublié à `tg classe fin`).
  - L'ENSEIGNANT VOIT TOUT : la liste des postes et chaque geste, dans son terminal ; il coupe la place d'un coup.
  - PAS DE SURCHARGE, PAS DE CONCOURS : un geste toutes les 3 secondes au plus par poste ; aucun compteur de gestes.

Le protocole : une ligne JSON (600 octets au plus) par connexion TCP (port 47110), une ligne JSON en réponse ;
même protocole sur Android (Place.kt, client seulement). Vecteurs communs : donnees/classe/vecteurs_place.json.
"""
import hashlib
import json
import re
import secrets
import socket
import socketserver
import threading
import time

from . import core
from .langue import t

PORT, PORT_ANNONCE = 47110, 47111
GESTES = ("coucou", "bravo", "danse")
SYMBOLES = ("☺", "★", "♪")
STADES = ("oeuf", "bebe", "ado", "adulte", "ancien")
MAX_POSTES = 40
DUREE_MAX = 2 * 3600                 # elle se ferme toute seule au bout de la séance
PAS_GESTE = 3.0                      # un geste toutes les 3 secondes au plus, par poste
TAILLE_MAX = 600
GARDER = 20                          # les derniers gestes gardés pour chaque poste (en mémoire)
ESPECE = re.compile(r"^[a-z0-9_]{1,32}$")


# ---------------------------------------------------------------- ce qui est permis (pur : mêmes vecteurs que Place.kt)
def privee(ip):
    """Une adresse IPv4 du réseau local (ou de l'ordinateur lui-même) ; tout le reste est refusé."""
    m = re.fullmatch(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", str(ip or ""))
    if not m:
        return False
    a, b, c, d = (int(x) for x in m.groups())
    if max(a, b, c, d) > 255:
        return False
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or a == 127


def cle(code):
    """La clé d'une place : 8 lettres tirées du code de séance (l'annonce ne contient pas le code lui-même)."""
    from . import classe
    d = classe.lire(code)
    if d is None or "V" not in d["options"]:
        return None
    return hashlib.sha256(("terminagotchi-place:" + classe.fabriquer(d["n"], d["options"])).encode()).hexdigest()[:8]


def profil_valide(p):
    """Le profil d'un poste : {espece, stade, niveau}, sinon None (rien d'autre ne passe)."""
    if not isinstance(p, dict):
        return None
    e, s, n = p.get("espece"), p.get("stade"), p.get("niveau")
    if not isinstance(e, str) or not ESPECE.match(e) or s not in STADES:
        return None
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 999:
        return None
    return {"espece": e, "stade": s, "niveau": n}


# ---------------------------------------------------------------- la place (dans la mémoire du poste de l'enseignant)
class Place:
    def __init__(self, code, maintenant=None):
        self.cle = cle(code)
        if self.cle is None:
            raise ValueError(code)
        self.debut = maintenant if maintenant is not None else time.time()
        self.postes = {}             # jeton → {poste, espece, stade, niveau, vu, dernier_geste}
        self.recus = {}              # poste → [{de, g, id}]
        self.journal = []            # ce que voit l'enseignant : (heure, texte)
        self.n_geste = 0
        self.ouverte = True
        self.verrou = threading.Lock()

    def numero_libre(self):
        pris = {p["poste"] for p in self.postes.values()}
        return next((i for i in range(1, MAX_POSTES + 1) if i not in pris), None)

    def traiter(self, req, ip, maintenant=None):
        """Une demande (dict) venue de ip : la réponse (dict). Jamais d'exception."""
        now = maintenant if maintenant is not None else time.time()
        with self.verrou:
            if not self.ouverte or now - self.debut > DUREE_MAX:
                self.ouverte = False
                return {"ok": False, "erreur": "fermee"}
            if not privee(ip):
                return {"ok": False, "erreur": "adresse"}
            if not isinstance(req, dict) or req.get("cle") != self.cle:
                return {"ok": False, "erreur": "cle"}
            quoi = req.get("quoi")
            if quoi == "entrer":
                p = profil_valide(req.get("profil"))
                if p is None:
                    return {"ok": False, "erreur": "profil"}
                j = req.get("jeton")
                if isinstance(j, str) and j in self.postes:          # le même poste revient (relance du jeu)
                    self.postes[j].update(p, vu=now)
                    return {"ok": True, "poste": self.postes[j]["poste"], "jeton": j}
                n = self.numero_libre()
                if n is None:
                    return {"ok": False, "erreur": "pleine"}
                j = secrets.token_hex(8)
                self.postes[j] = dict(p, poste=n, vu=now, dernier=0.0)
                self.journal.append((now, f"+ {n}"))
                return {"ok": True, "poste": n, "jeton": j}
            moi = self.postes.get(req.get("jeton")) if isinstance(req.get("jeton"), str) else None
            if moi is None:
                return {"ok": False, "erreur": "jeton"}
            moi["vu"] = now
            if quoi == "place":
                postes = sorted(({k: p[k] for k in ("poste", "espece", "stade", "niveau")}
                                 for p in self.postes.values()), key=lambda p: p["poste"])
                depuis = req.get("depuis") if isinstance(req.get("depuis"), int) else 0
                recus = [r for r in self.recus.get(moi["poste"], []) if r["id"] > depuis]
                return {"ok": True, "poste": moi["poste"], "postes": postes, "recus": recus}
            if quoi == "geste":
                g, a = req.get("g"), req.get("a")
                if g not in (0, 1, 2) or isinstance(g, bool) or not isinstance(a, int) or isinstance(a, bool):
                    return {"ok": False, "erreur": "geste"}
                if not any(p["poste"] == a for p in self.postes.values()) or a == moi["poste"]:
                    return {"ok": False, "erreur": "poste"}
                if now - moi["dernier"] < PAS_GESTE:
                    return {"ok": False, "erreur": "attends"}
                moi["dernier"] = now
                self.n_geste += 1
                self.recus.setdefault(a, []).append({"de": moi["poste"], "g": g, "id": self.n_geste})
                del self.recus[a][:-GARDER]
                self.journal.append((now, f"{moi['poste']} {SYMBOLES[g]} {a}"))
                return {"ok": True}
            return {"ok": False, "erreur": "quoi"}

    def fermer(self):
        with self.verrou:
            self.ouverte = False


# ---------------------------------------------------------------- le serveur (poste de l'enseignant)
def adresse_locale():
    """L'adresse de ce poste sur le réseau de l'école (privée), ou None. Aucun paquet n'est envoyé."""
    for cible in ("10.255.255.255", "192.168.255.255", "172.31.255.255"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((cible, 1))
                ip = s.getsockname()[0]
            if privee(ip) and not ip.startswith("127."):
                return ip
        except OSError:
            continue
    return None


def lire_ligne(sock, limite=TAILLE_MAX + 2):
    data = b""
    while b"\n" not in data and len(data) <= limite:
        bout = sock.recv(256)
        if not bout:
            break
        data += bout
    if len(data) > limite or b"\n" not in data:
        return None
    try:
        return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


class _Gestion(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(3.0)
        ip = self.client_address[0]
        try:
            req = lire_ligne(self.request)
            rep = self.server.place.traiter(req, ip) if req is not None else {"ok": False, "erreur": "format"}
            self.request.sendall((json.dumps(rep, separators=(",", ":")) + "\n").encode("utf-8"))
        except OSError:
            pass


class _Serveur(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def verify_request(self, request, client_address):     # réseau local seulement, dès l'arrivée
        return privee(client_address[0])


def servir(place, ip, port=PORT):
    """Le serveur de la place sur ip (son adresse du réseau local) ; renvoie (serveur, port réel)."""
    if not privee(ip):
        raise OSError("adresse non privée")
    srv = None
    for p in range(port, port + 10):
        try:
            srv = _Serveur((ip, p), _Gestion)
            break
        except OSError:
            continue
    if srv is None:
        raise OSError("aucun port libre")
    srv.place = place
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def annoncer(place, ip, port, arret):
    """Toutes les 2 s, sur le réseau local seulement : « une place est ici » (la clé, pas le code)."""
    msg = json.dumps({"tg": "place", "v": 1, "cle": place.cle, "ip": ip, "port": port}).encode()
    morceaux = ip.split(".")
    diffusions = ["255.255.255.255", ".".join(morceaux[:3] + ["255"])]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.bind((ip, 0))
        except OSError:
            pass
        while not arret.is_set() and place.ouverte:
            for d in diffusions:
                try:
                    s.sendto(msg, (d, PORT_ANNONCE))
                except OSError:
                    pass
            arret.wait(2.0)


def _code_du_prof(args):
    from . import classe, seance
    if args:
        return args[0]
    e = seance.s_(core.load() or {})
    if e:
        d = classe.lire(seance.seance(e["n"])["code"])
        return classe.fabriquer(d["n"], d["options"] + "V")
    return None


def ouvrir(args):
    """tg classe place ouvrir [CODE] : la place, ouverte par l'enseignant dans son terminal, jusqu'à q / Ctrl+C."""
    from . import classe
    from .plateforme import BOLD, DIM, RESET, Clavier, clear, fg
    code = _code_du_prof(args)
    d = classe.lire(code) if code else None
    if d is None or "V" not in d["options"]:
        return t("classe.place.code_v")
    code = classe.fabriquer(d["n"], d["options"])
    ip = adresse_locale()
    if ip is None:
        return t("classe.place.pas_de_reseau")
    place = Place(code)
    try:
        srv, port = servir(place, ip)
    except OSError:
        return t("classe.place.pas_de_reseau")
    arret = threading.Event()
    threading.Thread(target=annoncer, args=(place, ip, port, arret), daemon=True).start()
    core.modifier(lambda s: s.__setitem__("classe_place", {"ouverte": True, "debut": int(time.time())}))
    try:
        with Clavier() as clav:
            while place.ouverte:
                if time.time() - place.debut > DUREE_MAX:
                    break
                st = core.load() or {}
                if not (st.get("classe_place") or {}).get("ouverte"):
                    break                                        # tg classe fin / tg classe seance fin
                clear()
                print(f"{BOLD}{fg(78)}⌂ " + t("classe.place.titre") + f"{RESET}   {DIM}" + code + RESET)
                print(t("classe.place.ouverte", ip=ip, port=port))
                print(f"{DIM}" + t("classe.place.prof.aide") + RESET + "\n")
                with place.verrou:
                    postes = sorted(place.postes.values(), key=lambda p: p["poste"])
                    journal = list(place.journal[-12:])
                print(t("classe.place.postes", n=len(postes)))
                for p in postes:
                    print(f"  {t('classe.place.poste', n=p['poste'])} · {nom_espece(p['espece'])} · "
                          f"{nom_stade(p['stade'])} · {t('esp.niveau', n=p['niveau'])}")
                print("\n" + t("classe.place.journal"))
                for h, txt in journal:
                    print(f"  {time.strftime('%H:%M:%S', time.localtime(h))}  {txt}")
                k = clav.touche(1.0)
                if k and k.lower() in ("q", "\x03", "\x1b", "\x04"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        place.fermer()
        arret.set()
        srv.shutdown()
        srv.server_close()
        core.modifier(lambda s: s.pop("classe_place", None))
    return t("classe.place.fermee")


# ---------------------------------------------------------------- le client (chaque poste)
def demander(hote, port, req, delai=3.0):
    """Une demande à la place ; None si elle ne répond pas. Refuse toute adresse qui n'est pas privée."""
    if not privee(hote):
        return None
    try:
        with socket.create_connection((hote, int(port)), timeout=delai) as s:
            s.sendall((json.dumps(req, separators=(",", ":")) + "\n").encode("utf-8"))
            rep = lire_ligne(s, 64 * 1024)
        return rep if isinstance(rep, dict) else None
    except (OSError, ValueError):
        return None


def decouvrir(cle_, delai=5.0):
    """Écoute l'annonce d'une place de cette clé sur le réseau local : (ip, port) ou None."""
    fin = time.time() + delai
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", PORT_ANNONCE))
            while time.time() < fin:
                s.settimeout(max(0.1, fin - time.time()))
                try:
                    data, (ip, _p) = s.recvfrom(1024)
                except socket.timeout:
                    break
                try:
                    a = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    continue
                if isinstance(a, dict) and a.get("tg") == "place" and a.get("cle") == cle_ and privee(ip) \
                        and isinstance(a.get("port"), int):
                    return ip, a["port"]
    except OSError:
        return None
    return None


def profil(state):
    from . import sprites
    st = core.stage(core.level(state.get("xp", 0)))
    return {"espece": str(state.get("espece_compagnon") or "oeuf")[:32] if st else "oeuf",
            "stade": "oeuf" if st == 0 else sprites.STADE_ESPECE.get(st, "adulte"),
            "niveau": min(999, core.level(state.get("xp", 0)))}


def nom_espece(e):
    from . import bestiaire
    x = bestiaire.espece(e) if e != "oeuf" else None
    return x["nom"] if x else t("classe.place.oeuf") if e == "oeuf" else "?"


def nom_stade(s):
    return t({"oeuf": "stade.0", "bebe": "stade.1", "ado": "stade.2", "adulte": "stade.3",
              "ancien": "stade_bestiole.ancien"}.get(s, "stade.1"))


class Client:
    """La place vue d'un poste : trouvée, rejointe, relue toutes les 2 s (dans un fil à part : rien ne bloque)."""

    def __init__(self, code, profil_, hote=None, port=PORT, jeton=None):
        self.cle = cle(code)
        self.profil = profil_
        self.hote, self.port, self.jeton = hote, port, jeton
        self.poste = None
        self.postes = []
        self.recus = []              # [(g, de, quand)] : les bulles des gestes reçus
        self.dernier_id = 0
        self.etat = "cherche"        # cherche, ici, absente, fermee
        self.attends = 0.0

    def rejoindre(self):
        if self.cle is None:
            self.etat = "absente"
            return False
        if self.hote is None:
            trouve = decouvrir(self.cle)
            if trouve is None:
                self.etat = "absente"
                return False
            self.hote, self.port = trouve
        rep = demander(self.hote, self.port, {"cle": self.cle, "quoi": "entrer", "profil": self.profil,
                                              "jeton": self.jeton})
        if not rep or not rep.get("ok"):
            self.etat = "fermee" if rep and rep.get("erreur") == "fermee" else "absente"
            return False
        self.poste, self.jeton, self.etat = rep["poste"], rep["jeton"], "ici"
        return self.relire()

    def relire(self):
        rep = demander(self.hote, self.port, {"cle": self.cle, "quoi": "place", "jeton": self.jeton,
                                              "depuis": self.dernier_id}) if self.hote else None
        if not rep or not rep.get("ok"):
            self.etat = "fermee" if rep and rep.get("erreur") == "fermee" else "absente"
            return False
        self.etat = "ici"
        self.poste = rep.get("poste", self.poste)
        self.postes = [dict(profil_valide(x), poste=x["poste"]) for x in rep.get("postes", [])
                       if isinstance(x, dict) and isinstance(x.get("poste"), int) and profil_valide(x)]
        for r in rep.get("recus", []):
            if isinstance(r, dict) and r.get("g") in (0, 1, 2) and isinstance(r.get("id"), int):
                self.recus.append((r["g"], r.get("de"), time.time()))
                self.dernier_id = max(self.dernier_id, r["id"])
        self.recus = self.recus[-6:]
        return True

    def geste(self, a, g):
        if self.etat != "ici" or g not in (0, 1, 2):
            return False
        if time.time() - self.attends < PAS_GESTE:
            return False
        self.attends = time.time()
        rep = demander(self.hote, self.port, {"cle": self.cle, "quoi": "geste", "jeton": self.jeton, "a": int(a),
                                              "g": g})
        return bool(rep and rep.get("ok"))


# ---------------------------------------------------------------- tg classe place (côté élève, dans un terminal)
def _seance_eleve(state):
    from . import classe
    c = classe.c_(state)
    if c is None or "V" not in c.get("options", ""):
        return None
    return c


def commande(args):
    """tg classe place [ouvrir [CODE] | ADRESSE] · tg classe geste POSTE coucou|bravo|danse."""
    sous = args[0].lower() if args else "place"
    reste = args[1:]
    if sous == "place" and reste and reste[0].lower() in ("ouvrir", "open"):
        return ouvrir(reste[1:])
    if sous == "place" and reste and reste[0].lower() in ("fermer", "close"):
        core.modifier(lambda s: s.pop("classe_place", None))
        return t("classe.place.fermee")
    st = core.load() or {}
    c = _seance_eleve(st)
    if c is None:
        return t("classe.place.pas_ouverte")
    memo = c.get("place") or {}
    hote = reste[0] if sous == "place" and reste and privee(reste[0]) else memo.get("hote")
    cl = Client(c["code"], profil(st), hote, memo.get("port", PORT), memo.get("jeton"))
    if not cl.rejoindre():
        return t("classe.place.absente")
    core.modifier(lambda s: (_seance_eleve(s) or {}).__setitem__(
        "place", {"hote": cl.hote, "port": cl.port, "jeton": cl.jeton, "poste": cl.poste}))
    out = []
    if sous in ("geste", "gestes"):
        if len(reste) < 2 or not reste[0].isdigit():
            return t("classe.place.geste.usage")
        mot = reste[1].lower()
        g = next((i for i, m in enumerate(GESTES) if mot in (m, t("classe.geste." + m).lower())), None)
        if g is None:
            return t("classe.place.geste.usage")
        ok = cl.geste(int(reste[0]), g)
        out.append(t("classe.place.geste.ok", geste=SYMBOLES[g] + " " + t("classe.geste." + GESTES[g]),
                     n=reste[0]) if ok else t("classe.place.geste.non"))
    out.append(t("classe.place.titre") + " · " + t("classe.place.moi", n=cl.poste))
    for p in cl.postes:
        moi = " ← " + t("classe.place.cest_toi") if p["poste"] == cl.poste else ""
        out.append(f"  {t('classe.place.poste', n=p['poste'])} · {nom_espece(p['espece'])} · {nom_stade(p['stade'])}{moi}")
    for g, de, _q in cl.recus:
        out.append("  " + t("classe.place.recu", geste=SYMBOLES[g] + " " + t("classe.geste." + GESTES[g]), n=de))
    out.append(t("classe.place.aide"))
    return "\n".join(out)


# ---------------------------------------------------------------- dans l'espace de travail (tg espace)
class Vue:
    """La place dans l'espace : un fil relit toutes les 2 s ; les clics envoient les gestes (dans un fil aussi)."""

    def __init__(self, state):
        c = _seance_eleve(state) or {}
        memo = c.get("place") or {}
        self.client = Client(c.get("code", ""), profil(state), memo.get("hote"), memo.get("port", PORT),
                             memo.get("jeton"))
        self.actif = True
        self.message = ""
        threading.Thread(target=self._boucle, daemon=True).start()

    def _boucle(self):
        while self.actif:
            try:
                if self.client.etat in ("cherche", "absente") and self.client.poste is None:
                    self.client.rejoindre()
                else:
                    self.client.relire()
            except Exception:                        # noqa: BLE001 — la place ne casse jamais l'espace
                self.client.etat = "absente"
            for _ in range(20):
                if not self.actif:
                    return
                time.sleep(0.1)

    def geste(self, a, g):
        threading.Thread(target=lambda: setattr(self, "message", "ok" if self.client.geste(a, g) else "attends"),
                         daemon=True).start()

    def fermer(self):
        self.actif = False

