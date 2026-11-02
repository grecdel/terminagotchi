"""📡 La Tour des Ondes — la radio, LoRa et les réseaux maillés (docs/programme.md § 7.11), quartier du Port.

Le cinquième monde de la phase 5 (§ 7.14, étape 6). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont le
palier P7 du Port (adresses et ports) et le palier M2 de la Salle des Rouages (les unités), plus le tronc commun du
Port (programme.json, « mondes » → ondes → requis et requis_lecons). Le chapitre et le lieu s'appellent « ondes »
(« tour » est déjà l'aile de la maison) : ~/terrain_terminagotchi/ondes/. On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, plan_de_la_tour.txt) :
  - ÉCOUTER EST LIBRE, ÉMETTRE EST RÉGLEMENTÉ ; LE JEU N'ÉMET JAMAIS LUI-MÊME. Sur la vraie machine, on LIT seulement
    (nmcli radio, rfkill list, iw dev, nmcli … wifi list --rescan no : la liste déjà connue, sans balayage actif) ;
    jamais de sudo, aucune modification de la configuration radio (ni rfkill block, ni connexion, ni appairage).
  - VIE PRIVÉE : les réseaux et appareils affichés par nmcli, iw ou bluetoothctl sont ceux des VOISINS (noms,
    adresses MAC) : ce sont des données d'autres personnes. Le jeu ne les enregistre jamais, ne les envoie jamais au
    site et ne les réaffiche pas dans ses textes. Il ne lit lui-même que des grandeurs anonymes (la fréquence, la
    force du signal, le nombre de réseaux), le temps d'un calcul, sans rien écrire. On apprend à l'enfant à choisir
    les colonnes (nmcli -f CHAN,FREQ,SIGNAL) et pourquoi on ne recopie pas les noms des autres.
  - W5 (un vrai nœud Meshtastic) et W6 (écouter le ciel avec une radio logicielle, en RÉCEPTION seulement) sont
    facultatifs, « avec un adulte », jamais exigés pour avancer : sans le matériel, l'étape se raconte (elle est
    cachée quand l'outil manque). Aucune marque, aucun prix, aucun lien d'achat. `pip install meshtastic` est
    seulement expliqué. W6 : rien de ce qui est capté n'est gardé s'il pourrait identifier quelqu'un (ni
    immatriculation d'avion, ni identifiant de capteur) ; les avions et capteurs du jeu sont FICTIFS.

LES PALIERS (on0 à on10) : la porte ; W1 l'onde dont on règle la fréquence, la longueur d'onde (avec bc), le mur qui
l'affaiblit ; W1 sur ta machine (iw dev, nmcli … --rescan no, le nombre de réseaux, les canaux, pourquoi on ne recopie
pas les noms) ; W2 tes radios (nmcli radio, rfkill list, bluetoothctl show filtré) ; W2 la règle du spectre (bandes
libres et réservées) ; W3 LoRa (l'étalement de spectre, le temps d'émission avec bc, le message qui traverse la vallée,
la règle du 1 %) ; W3 LoRaWAN ou maillage ; W4 le maillage du Terminaworld (mesh-route, mesh-envoie, mesh-coupe) ; W4
la tempête : trois nœuds du chemin coupés et le message passe quand même (exploit « onde ») ; W5 le vrai réseau maillé
(avec un adulte) ; W6 écouter le ciel (réception seulement, anonymiser ce qu'on capte).

LE MAILLAGE reprend le réseau simulé du Port (port.json : les biomes sont des machines) : chaque machine devient un
nœud radio ; un lien = deux nœuds à portée (les liens du Port + ceux des voisins proches, ondes.json). Le message est
répété par chaque nœud qui l'entend (inondation gérée, comme Meshtastic) : le premier arrivé gagne, c'est le chemin le
plus court en sauts. Tout est local : rien ne passe sur une vraie radio.

Les commandes du jeu (`ondes …`, et `mesh-envoie`, `mesh-coupe`, `mesh-route`, alias posés par `tg installer`) écrivent
dans le carnet de la tour (ondes/carnet_de_la_tour.txt) ce que les étapes vérifient — jamais un nom de réseau, jamais
un message tapé. Mêmes règles sur Android (Ondes.kt, vecteurs communs donnees/ondes/vecteurs.json), où les radios de
la vraie machine sont racontées.
"""
import hashlib
import json
import math
import os
import pkgutil
import random
import re
import shutil
import subprocess
import sys
import unicodedata

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, SYS_WIN, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "ondes.json").decode("utf-8"))
    return _D


def _port():
    from . import port
    return port


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c))


NOMS = {"fm": "fm", "radio": "fm", "lora": "lora", "gps": "gps", "wifi": "wifi24", "wi-fi": "wifi24", "wifi24": "wifi24",
        "wifi2": "wifi24", "wifi5": "wifi5", "5g": "cinqg", "cinqg": "cinqg", "4g": "quatreg", "quatreg": "quatreg",
        "bluetooth": "bluetooth", "bt": "bluetooth", "wifi6": "wifi6"}
MULT = {"": 1, "hz": 1, "k": 10 ** 3, "khz": 10 ** 3, "m": 10 ** 6, "mhz": 10 ** 6, "g": 10 ** 9, "ghz": 10 ** 9}


def frequence_de(texte):
    """Une fréquence tapée → (Hz, nom de la technologie ou None) : « lora », « wifi5 », « 868M », « 2.4G », « 2,4 GHz »,
    « 868MHz », « 100000000 ». None si ce n'est pas une fréquence."""
    s = ascii_bas((texte or "").strip().lower()).replace(" ", "")
    if s in NOMS:
        tid = NOMS[s]
        return _hz_tech(tid), tid
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)([a-z]*)", s)
    if not m or m.group(2) not in MULT:
        return None
    v = float(m.group(1).replace(",", ".")) * MULT[m.group(2)]
    if v < 1:
        return None
    return int(round(v)), None


def _hz_tech(tid):
    f = donnees()["onde"]["frequences"]
    if tid in f:
        return f[tid]
    return next((x["hz"] for x in donnees()["spectre"]["techs"] if x["id"] == tid), None)


def longueur_onde(hz):
    """λ = v / f, en mètres (v = 300 000 000 m/s, la vitesse de la lumière arrondie)."""
    return donnees()["vitesse"] / hz


def texte_longueur(m):
    """Une longueur lisible : « 3 m », « 34.6 cm », « 5 mm », « 300 km »."""
    if m >= 1000:
        return f"{m / 1000:.4g} km"
    if m >= 1:
        return f"{m:.3g} m"
    if m >= 0.01:
        return f"{m * 100:.3g} cm"
    return f"{m * 1000:.3g} mm"


def longueur_ok(reponse, hz):
    """La longueur d'onde donnée par l'enfant (« 34.6 », « 34,6 cm », « 0.35 m », « 346 mm ») est-elle juste à 5 % près ?
    Sans unité : en mètres si le nombre est plus petit que 2, sinon en centimètres."""
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]*)\s*$", reponse or "")
    if not m:
        return False
    v = float(m.group(1).replace(",", "."))
    u = m.group(2).lower()
    if u in ("m", "metre", "metres", "meter", "meters"):
        x = v
    elif u in ("cm",):
        x = v / 100
    elif u in ("mm",):
        x = v / 1000
    elif u == "":
        x = v if v < 2 else v / 100
    else:
        return False
    vrai = longueur_onde(hz)
    return abs(x - vrai) <= 0.05 * vrai


def periodes(hz):
    """Combien d'oscillations le dessin montre (à l'échelle des yeux, pas du réel) : plus la fréquence est haute, plus il
    y en a."""
    return max(1.0, 1 + 3 * math.log10(hz / 1e8))


def restant_pc(db):
    """(amplitude, puissance) qui restent après un affaiblissement de db décibels, en pour cent (arrondis)."""
    return round(100 * 10 ** (-db / 20)), round(100 * 10 ** (-db / 10))


def affaiblissement(matiere, tech, n=1):
    """Les décibels perdus en traversant n murs de cette matière (valeurs indicatives d'ondes.json)."""
    return donnees()["onde"]["murs"].get(matiere, {}).get(tech, 0) * n


def traverse_le_mieux(matiere="brique"):
    """La technologie qui perd le moins dans ce mur (la plus basse fréquence)."""
    m = donnees()["onde"]["murs"][matiere]
    return min(m, key=lambda k: (m[k], k))


# ---------------------------------------------------------------- le spectre
def canal(mhz):
    """Le canal Wi-Fi d'une fréquence (MHz) : 2412 → 1, 2484 → 14, 5180 → 36, 5955 → 1 (6 GHz) ; None hors bande."""
    if 2412 <= mhz <= 2472 and (mhz - 2407) % 5 == 0:
        return (mhz - 2407) // 5
    if mhz == 2484:
        return 14
    if 5150 <= mhz <= 5895 and mhz % 5 == 0:
        return (mhz - 5000) // 5
    if 5925 <= mhz <= 7125 and (mhz - 5950) % 5 == 0:
        return (mhz - 5950) // 5
    return None


def bande(mhz):
    """« 2,4 », « 5 » ou « 6 » (GHz) ; None."""
    if 2400 <= mhz <= 2500:
        return "2,4"
    if 5150 <= mhz <= 5895:
        return "5"
    if 5925 <= mhz <= 7125:
        return "6"
    return None


def resume_wifi(freqs):
    """Les grandeurs ANONYMES d'une liste de réseaux : (nombre, par bande, par canal). Aucune autre information."""
    par_bande, par_canal = {}, {}
    for f in freqs:
        b = bande(f)
        if b:
            par_bande[b] = par_bande.get(b, 0) + 1
        c = canal(f)
        if c is not None and b == "2,4":
            par_canal[c] = par_canal.get(c, 0) + 1
    return {"n": len(freqs), "bandes": par_bande, "canaux": dict(sorted(par_canal.items()))}


def reseaux_ok(reponse, vrai):
    """Le nombre de réseaux lu par l'enfant : la liste bouge (un réseau apparaît, un autre s'éteint), à 2 près (ou 20 %)."""
    try:
        n = int(str(reponse).strip())
    except ValueError:
        return False
    return abs(n - vrai) <= max(2, vrai // 5)


def melange(graine, sel, liste):
    l2 = list(liste)
    random.Random(f"{sel}:{graine}").shuffle(l2)
    return l2


def _tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


LETTRES = "ABCDEF"


def regle_cartes(graine):
    """Les six technologies à ranger sur la règle, mélangées pour cette partie : [(lettre, id)]."""
    return list(zip(LETTRES, melange(graine, "regle", donnees()["spectre"]["regle"])))


def regle_reponse(graine):
    """Les lettres, de la plus basse fréquence à la plus haute."""
    pos = {i: l for l, i in regle_cartes(graine)}
    hz = {x["id"]: x["hz"] for x in donnees()["spectre"]["techs"]}
    return [pos[i] for i in sorted(donnees()["spectre"]["regle"], key=lambda i: hz[i])]


def libre_cartes(graine):
    """Les usages à classer (bande libre « l » ou réservée « r »), mélangés : [(n°, id, l|r)]."""
    lib = {x["id"]: x["libre"] for x in donnees()["spectre"]["techs"]}
    return [(i + 1, x, lib[x]) for i, x in enumerate(melange(graine, "libre", donnees()["spectre"]["libre"]))]


def choix_cartes(graine):
    """Les situations (passerelle « p » ou maillage « m »), mélangées : [(n°, id, p|m)]."""
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(melange(graine, "choix", donnees()["choix"]["situations"]))]


# ---------------------------------------------------------------- LoRa
def duree_symbole_us(sf):
    """La durée d'un symbole LoRa en microsecondes : 2^SF / largeur de bande."""
    return (2 ** sf) * 1_000_000 // donnees()["lora"]["bw"]


def symboles_message(sf, octets=None):
    """Le nombre de symboles de la charge utile (Semtech AN1200.13 : CRC, en-tête explicite, codage 4/5 ; optimisation
    bas débit à partir de SF11 en 125 kHz)."""
    L = donnees()["lora"]
    pl = L["octets"] if octets is None else octets
    de = 1 if sf >= 11 else 0
    num = 8 * pl - 4 * sf + 28 + 16
    den = 4 * (sf - 2 * de)
    return 8 + max(-(-num // den) * (L["cr"] + 4), 0)


def temps_emission_us(sf, octets=None):
    """Le temps d'émission (« time on air ») d'un message, en microsecondes, calcul entier exact :
    (préambule + 4,25 + symboles) × 2^SF / BW."""
    L = donnees()["lora"]
    n = symboles_message(sf, octets)
    return (4 * L["preambule"] + 17 + 4 * n) * (2 ** sf) * 1_000_000 // (4 * L["bw"])


def portee_m(sf):
    return donnees()["lora"]["portee_m"][str(sf)]


def vallee_m(graine):
    """La largeur de la vallée à traverser dans cette partie (mètres)."""
    v = donnees()["lora"]["vallees_m"]
    return v[_tire(graine, "vallee", len(v))]


def sf_min(distance):
    """Le plus petit facteur d'étalement (SF) dont la portée suffit, ou None."""
    return next((sf for sf in donnees()["lora"]["facteurs"] if portee_m(sf) >= distance), None)


def budget_us():
    """Le temps d'émission permis par heure dans la bande 868 MHz (cycle de 1 %) : 36 s = 36 000 000 µs."""
    L = donnees()["lora"]
    return L["heure_s"] * 1_000_000 * L["cycle_pour_mille"] // 1000


def messages_heure(sf, octets=None):
    """Combien de messages de ce SF on peut envoyer en une heure sans dépasser 1 % du temps."""
    return budget_us() // temps_emission_us(sf, octets)


def messages_ok(reponse, sf):
    try:
        n = int(str(reponse).strip())
    except ValueError:
        return False
    return abs(n - messages_heure(sf)) <= 1


# ---------------------------------------------------------------- le maillage du Terminaworld
def noeuds():
    return _port().ids()


def liens():
    return [list(x) for x in _port().donnees()["liens"]] + [list(x) for x in donnees()["maillage"]["liens_radio"]]


def voisins(mid, coupes=()):
    """Les nœuds à portée de mid (allumés), dans l'ordre des liens (déterministe)."""
    out = []
    for a, b in liens():
        if a == mid and b not in coupes and b not in out:
            out.append(b)
        elif b == mid and a not in coupes and a not in out:
            out.append(a)
    return out


def route(depart, arrivee, coupes=()):
    """Le chemin que gagne le message (le premier arrivé de l'inondation = le plus court en sauts ; à égalité, l'ordre
    des liens) : [depart, …, arrivee], ou None si l'arrivée est isolée."""
    if depart in coupes or arrivee in coupes:
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
        for v in voisins(x, coupes):
            if v not in avant:
                avant[v] = x
                file.append(v)
    return None


def inondation(depart, coupes=()):
    """Les vagues de l'inondation : [[depart], [nœuds qui l'entendent au 1er saut], [au 2e saut], …]."""
    vus = {depart}
    vagues = [[depart]]
    while True:
        suite = []
        for x in vagues[-1]:
            for v in voisins(x, coupes):
                if v not in vus:
                    vus.add(v)
                    suite.append(v)
        if not suite:
            return vagues
        vagues.append(suite)


def defi_cible(graine):
    c = donnees()["maillage"]["cibles"]
    return c[_tire(graine, "cible", len(c))]


def envoi(dest, coupes=(), sauts_max=None):
    """Spécification d'un envoi : {ok, chemin, raison: arrive|isole|loin|coupe|inconnu|camp, sauts}."""
    sm = donnees()["maillage"]["sauts_max"] if sauts_max is None else sauts_max
    if dest not in noeuds():
        return {"ok": False, "chemin": [], "raison": "inconnu", "sauts": 0}
    if dest == "camp":
        return {"ok": False, "chemin": ["camp"], "raison": "camp", "sauts": 0}
    if dest in coupes:
        return {"ok": False, "chemin": [], "raison": "coupe", "sauts": 0}
    r = route("camp", dest, coupes)
    if not r:
        return {"ok": False, "chemin": [], "raison": "isole", "sauts": 0}
    if len(r) - 1 > sm:
        return {"ok": False, "chemin": r, "raison": "loin", "sauts": len(r) - 1}
    return {"ok": True, "chemin": r, "raison": "arrive", "sauts": len(r) - 1}


# ---------------------------------------------------------------- les antennes (vue déployée, surveillance)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def antenne_de(morceau):
    """(radio, sens) d'une commande (un morceau de ligne), ou None : la première règle d'ondes.json qui correspond."""
    m = (morceau or "").strip()
    m = re.sub(r"^(timeout\s+\S+\s+)", "", m)
    for r in donnees()["antennes"]["regles"]:
        if re.search(r["motif"], m):
            return r["radio"], r["sens"]
    return None


def antennes_de(ligne):
    """[(radio, sens)] pour chaque morceau d'une ligne qui touche une radio."""
    out = []
    for m in SEPARATEURS.split(ligne or ""):
        a = antenne_de(m)
        if a:
            out.append(a)
    return out


# ================================================================ la vraie machine (lue, jamais modifiée)
def _lire_sys(chemin):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def wifi_freqs():
    """Les fréquences (MHz) des réseaux déjà connus de la carte Wi-Fi, SANS balayage actif (--rescan no) et en ne
    demandant QUE la colonne FREQ : aucun nom, aucune adresse. None si nmcli manque ou échoue. Rien n'est écrit."""
    if SYS_WIN or not shutil.which("nmcli"):
        return None
    try:
        r = subprocess.run(["nmcli", "-t", "-f", "FREQ", "device", "wifi", "list", "--rescan", "no"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    out = []
    for l in r.stdout.splitlines():
        m = re.match(r"^\s*(\d+)", l)
        if m:
            out.append(int(m.group(1)))
    return out


def radios():
    """Les radios de la machine d'après le noyau (/sys/class/rfkill) : [(type, bloquée par logiciel, interrupteur)].
    Anonyme : seulement le genre de radio et son état."""
    base = "/sys/class/rfkill"
    out = []
    try:
        noms = sorted(os.listdir(base), key=lambda x: (len(x), x))
    except OSError:
        return []
    for n in noms:
        ty = _lire_sys(f"{base}/{n}/type").strip()
        if not ty:
            continue
        out.append((ty, _lire_sys(f"{base}/{n}/soft").strip() == "1", _lire_sys(f"{base}/{n}/hard").strip() == "1"))
    return out


# ================================================================ l'état, le terrain, le carnet de la tour
def o_(state):
    c = state.setdefault("ondes", {})
    c.setdefault("faits", [])
    c.setdefault("coupes", [])
    return c


def dossier():
    return core.TERRAIN / "ondes"


CARNET = "carnet_de_la_tour.txt"


def noter(etiquette, texte):
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
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def compte_carnet(etiquette, mot="ok"):
    return len(re.findall(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M))


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, contenu):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def capteurs_texte():
    """Le fichier d'exemple de W6 : des lignes JSON comme celles de rtl_433 -F json, toutes FICTIVES."""
    return "".join(json.dumps(x, ensure_ascii=False, separators=(", ", ": ")) + "\n" for x in donnees()["ciel"]["capteurs"])


def meubles(state):
    """Ce que le jeu pose dans la Tour quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    return {"ondes/plan_de_la_tour.txt": t("on.meuble.plan", nom=state.get("name", "")) + "\n",
            f"ondes/{CARNET}": t("on.meuble.carnet") + "\n",
            "ondes/capteurs_exemple.json": capteurs_texte()}


BESOINS = {"on0": ["plan_de_la_tour.txt"], "on10": ["capteurs_exemple.json"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de la Tour : les fichiers dont la leçon a besoin, les ponts des nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire("ondes/" + rel, tous["ondes/" + rel])
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = o_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("on.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("on.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
ON = r"^(tg\s+)?ondes\s+"
MESH = r"^(tg\s+)?(ondes\s+)?mesh-"
BC = r"^(echo|printf)\b.*\|\s*bc\b"

FS = {
    "on_longueur": lambda: dans_carnet("longueur"),
    "on_traverse": lambda: dans_carnet("traverse"),
    "on_reseaux": lambda: dans_carnet("reseaux"),
    "on_regle": lambda: dans_carnet("regle"),
    "on_libre": lambda: dans_carnet("libre"),
    "on_vallee": lambda: dans_carnet("vallee"),
    "on_messages": lambda: dans_carnet("messages"),
    "on_choix": lambda: dans_carnet("choix"),
    "on_envoie": lambda: dans_carnet("envoie"),
    "on_coupe": lambda: dans_carnet("coupe"),
    "on_detour": lambda: dans_carnet("detour"),
    "on_rallume": lambda: dans_carnet("rallume"),
    "on_defi1": lambda: _defi_coupes() >= 1,
    "on_defi2": lambda: _defi_coupes() >= 2,
    "on_defi3": lambda: _defi_coupes() >= 3,
    "on_defi": lambda: dans_carnet("defi"),
}
CREE = {}


def _defi_coupes():
    """Les nœuds du chemin coupés depuis le dernier « ondes defi » (le carnet le dit : [defi_coupe] … (ok))."""
    txt = carnet()
    dernier = txt.rfind("[defi_debut]")
    if dernier < 0:
        return 0
    return len(re.findall(r"^\[defi_coupe\].*\(ok\)\s*$", txt[dernier:], re.M))


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LECONS = {
    # la porte de la Tour
    "on0": {"titre": "hist.on0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "ondes"}), "cmd": "cd ~/terrain_terminagotchi/ondes", "ici": "ondes",
         "bravo": ("hist.entree.bravo", {"piece": "ondes"})},
        _n("on0", 1, cmd="ls", re=LS, ou="ondes"),
        _n("on0", 2, cmd="cat plan_de_la_tour.txt", re=LIRE + r".*plan_de_la_tour"),
    ]},
    # W1 les ondes : l'onde dont on règle la fréquence, la longueur d'onde, le mur
    "on1": {"titre": "hist.on1.titre", "skill": None, "steps": [
        _n("on1", 0, cmd="ondes onde", re=ON + r"onde\s*$", ou="ondes"),
        _n("on1", 1, cmd="ondes onde lora", re=ON + r"onde\s+\S"),
        _n("on1", 2, cmd='echo "300000000 / 2400000000" | bc -l', re=BC, outil="bc", win=False),
        _n("on1", 3, cmd="ondes longueur ?", fs="on_longueur"),
        _n("on1", 4, cmd="ondes mur", re=ON + r"murs?\b"),
        _n("on1", 5, cmd="ondes traverse ?", fs="on_traverse"),
    ]},
    # W1 sur ta machine : en lecture seule, sans recopier les noms des voisins
    "on2": {"titre": "hist.on2.titre", "skill": None, "steps": [
        _n("on2", 0, cmd="iw dev", re=r"^(iw\s+dev|iwconfig)\b", outil="iw", win=False, tout_code=True, ou="ondes"),
        _n("on2", 1, cmd="nmcli -f CHAN,FREQ,SIGNAL,BARS dev wifi list --rescan no",
           re=r"^nmcli\b.*\bwifi\b.*\blist\b", outil="nmcli", win=False, tout_code=True),
        _n("on2", 2, cmd="ondes reseaux ?", fs="on_reseaux", outil="nmcli"),
        _n("on2", 3, cmd="ondes canaux", re=ON + r"canaux\b"),
        _n("on2", 4, cmd="ondes voisins", re=ON + r"voisins\b"),
    ]},
    # W2 tes radios : nmcli radio, rfkill list, bluetoothctl (filtré)
    "on3": {"titre": "hist.on3.titre", "skill": None, "steps": [
        _n("on3", 0, cmd="nmcli radio", re=r"^nmcli\s+(-\w+\s+)*r(adio)?\s*(all)?\s*$", outil="nmcli", win=False,
           tout_code=True, ou="ondes"),
        _n("on3", 1, cmd="rfkill list", re=r"^rfkill(\s+list)?\s*$", outil="rfkill", win=False, tout_code=True),
        _n("on3", 2, cmd="timeout 5 bluetoothctl show | grep -E 'Powered|Discoverable'",
           re=r"^(timeout\s+\d+\s+)?bluetoothctl\s+(--timeout\s+\d+\s+)?(show|list)\b", outil="bluetoothctl", win=False,
           tout_code=True),
        _n("on3", 3, cmd="ondes radios", re=ON + r"radios?\b"),
    ]},
    # W2 la règle du spectre ; bandes libres et réservées
    "on4": {"titre": "hist.on4.titre", "skill": None, "steps": [
        _n("on4", 0, cmd="ondes spectre", re=ON + r"spectre\b", ou="ondes"),
        _n("on4", 1, cmd="ondes regle", re=ON + r"r[eè]gle\s*$"),
        _n("on4", 2, cmd="ondes regle ? ? ? ? ? ?", fs="on_regle"),
        _n("on4", 3, cmd="ondes libre", re=ON + r"libres?\s*$"),
        _n("on4", 4, cmd="ondes libre ? ? ? ? ? ?", fs="on_libre"),
    ]},
    # W3 parler loin avec peu : LoRa, le temps d'émission, la vallée, la règle du 1 %
    "on5": {"titre": "hist.on5.titre", "skill": None, "steps": [
        _n("on5", 0, cmd="ondes lora", re=ON + r"lora\b", ou="ondes"),
        _n("on5", 1, cmd='echo "2^12 / 125000" | bc -l', re=BC, outil="bc", win=False),
        _n("on5", 2, cmd="ondes temps", re=ON + r"temps\b"),
        _n("on5", 3, cmd="ondes vallee", re=ON + r"vall[eé]e\s*$"),
        _n("on5", 4, cmd="ondes vallee ?", fs="on_vallee"),
        _n("on5", 5, cmd='echo "3600 * 1 / 100" | bc', re=BC, outil="bc", win=False),
        _n("on5", 6, cmd="ondes messages ?", fs="on_messages"),
    ]},
    # W3 LoRaWAN (passerelles) ou maillage direct
    "on6": {"titre": "hist.on6.titre", "skill": None, "steps": [
        _n("on6", 0, cmd="ondes passerelle", re=ON + r"passerelles?\b", ou="ondes"),
        _n("on6", 1, cmd="ondes maillage", re=ON + r"maillage\b"),
        _n("on6", 2, cmd="ondes choix", re=ON + r"choix\s*$"),
        _n("on6", 3, cmd="ondes choix ? ? ? ?", fs="on_choix"),
    ]},
    # W4 le maillage du Terminaworld : mesh-route, mesh-envoie, mesh-coupe
    "on7": {"titre": "hist.on7.titre", "skill": None, "steps": [
        _n("on7", 0, cmd="mesh-route", re=MESH + r"route\b", ou="ondes"),
        _n("on7", 1, cmd='mesh-envoie feu "bonjour"', fs="on_envoie"),
        _n("on7", 2, cmd="mesh-coupe roche", fs="on_coupe"),
        _n("on7", 3, cmd='mesh-envoie feu "bonjour"', fs="on_detour"),
        _n("on7", 4, cmd="mesh-route feu", re=MESH + r"route\s+\S"),
        _n("on7", 5, cmd="mesh-coupe -r", fs="on_rallume"),
    ]},
    # W4 la tempête : trois nœuds du chemin coupés, le message passe quand même (exploit « onde »)
    "on8": {"titre": "hist.on8.titre", "skill": None, "steps": [
        _n("on8", 0, cmd="ondes defi", re=ON + r"d[eé]fi\b", ou="ondes"),
        _n("on8", 1, cmd="mesh-coupe ?", fs="on_defi3"),
        _n("on8", 2, cmd='mesh-envoie ? "SOS"', fs="on_defi", exploit="ondes.onde"),
    ]},
    # W5 le vrai réseau maillé (AVEC UN ADULTE, facultatif : sans la petite carte radio, il se raconte)
    "on9": {"titre": "hist.on9.titre", "skill": None, "steps": [
        _n("on9", 0, cmd="ondes adulte", re=ON + r"adulte\b", ou="ondes"),
        _n("on9", 1, cmd="command -v meshtastic", re=r"^(command\s+-v|which|type)\s+meshtastic\b", win=False, tout_code=True),
        _n("on9", 2, cmd="meshtastic --info", re=r"^meshtastic\b.*--info\b", outil="meshtastic", win=False, tout_code=True),
        _n("on9", 3, cmd="meshtastic --nodes", re=r"^meshtastic\b.*--nodes\b", outil="meshtastic", win=False, tout_code=True),
        _n("on9", 4, cmd='meshtastic --sendtext "bonjour"', re=r"^meshtastic\b.*--sendtext\b", outil="meshtastic",
           win=False, tout_code=True),
        _n("on9", 5, cmd="ondes noeud", re=ON + r"n(oe|œ)uds?\b"),
    ]},
    # W6 écouter le ciel : radio logicielle, RÉCEPTION seulement, rien de ce qui identifie quelqu'un n'est gardé
    "on10": {"titre": "hist.on10.titre", "skill": None, "steps": [
        _n("on10", 0, cmd="ondes ecoute", re=ON + r"[eé]coute\b", ou="ondes"),
        _n("on10", 1, cmd="command -v rtl_test rtl_433 dump1090", re=r"^(command\s+-v|which|type)\s+\S", win=False,
           tout_code=True),
        _n("on10", 2, cmd="timeout 10 rtl_test -t", re=r"^(timeout\s+\d+\s+)?rtl_test\b", outil="rtl_test", win=False,
           tout_code=True),
        _n("on10", 3, cmd="ondes avions", re=ON + r"avions?\b"),
        _n("on10", 4, cmd="cat capteurs_exemple.json", re=LIRE + r".*capteurs_exemple"),
        _n("on10", 5, cmd="grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json",
           re=r"^grep\b.*temperature_C.*capteurs_exemple", win=False),
        _n("on10", 6, cmd="ondes anonyme", re=ON + r"anonymes?\b"),
    ]},
}
CHAPITRE = {"id": "ondes", "n": 15, "piece": "ondes", "famille": "Célestes", "monde": True,
            "lecons": [f"on{i}" for i in range(11)], "objet": "antenne_miniature", "titre": "maitre_des_ondes"}


# ================================================================ l'arbre du Carrefour : quand la Tour s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "ondes"), {})


def _besoin():
    """(chapitres du tronc commun, leçons d'autres mondes) qu'il faut avoir finis."""
    from . import programme
    P = programme.donnees()
    m = _monde()
    chaps = []
    for n in m.get("requis", []):
        chaps += [c for c in P.get("tronc", {}).get(n, []) if c not in chaps]
    return chaps, list(m.get("requis_lecons", []))


def ouvert(state):
    from . import histoire
    chaps, lecs = _besoin()
    if not chaps and not lecs:
        return False
    faits = histoire.h_(state)["faits"]
    return all(histoire.fini(state, c) for c in chaps) and all(l in faits for l in lecs)


def manque(state):
    from . import histoire, lecons
    chaps, lecs = _besoin()
    faits = histoire.h_(state)["faits"]
    out = [histoire.nom_chapitre(c) for c in chaps if not histoire.fini(state, c)]
    for l in lecs:
        if l not in faits:
            ch = histoire.chapitre_de_lecon(l)
            out.append(f"{lecons.tx(histoire.lecon_def(l)['titre'])} ({histoire.nom_chapitre(ch['id']) if ch else '?'})")
    return out


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "ondes" in deja or histoire.fini(state, "ondes") or not ouvert(state):
        return False
    deja.append("ondes")
    core.log(state, t("on.ouvert.log"))
    core.say(state, histoire.dire(state, "on.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"ondes longueur ?": "longueur", "ondes traverse ?": "traverse", "ondes reseaux ?": "reseaux",
            "ondes regle ? ? ? ? ? ?": "regle", "ondes libre ? ? ? ? ? ?": "libre", "ondes vallee ?": "vallee",
            "ondes messages ?": "messages", "ondes choix ? ? ? ?": "choix"}
CHANGE = re.compile(r"(^|[;&|]\s*)(sudo\s+\S|rfkill\s+(block|unblock|toggle)\b|nmcli\b.*\b(connect|disconnect|off|delete|modify|"
                    r"hotspot)\b|bluetoothctl\b.*\b(pair|connect|trust|power\s+o(n|ff)|discoverable|pairable|remove)\b)")
CHERCHE = re.compile(r"(^|[;&|]\s*)(iw\b.*\bscan\b|bluetoothctl\b.*\bscan\b|nmcli\b.*\brescan\b(?!\s+no\b))")
NOMS_VOISINS = re.compile(r"^nmcli\b(?!.*\s-f\s)(?!.*--fields\b).*\bwifi\b.*\blist\b")
EMET = re.compile(r"^meshtastic\b.*--sendtext\b")


def indice(step, tapees):
    """Un indice de la Tour : un sudo, une commande qui changerait la radio, un trou « ? » recopié, une mauvaise réponse
    (longueur d'onde, mur, nombre de réseaux, règle, bandes, vallée, messages, choix), la tempête mal coupée."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("on.indice.sudo")
    if any(CHANGE.search(l) for l in lignes):
        return t("on.indice.change")
    if any(CHERCHE.search(l) for l in lignes):
        return t("on.indice.cherche")
    if "?" in cmd.split() and any(TROU.search(l) for l in lignes if re.match(ON, l) or re.match(MESH, l)):
        return t("on.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = [l for l in carnet().splitlines() if l.startswith(f"[{et}]")]
        if der and not der[-1].endswith("(ok)"):
            return t("on.indice." + et)
    if step.get("fs", "").startswith("on_defi"):
        der = [l for l in carnet().splitlines() if l.startswith(("[defi_coupe]", "[defi]", "[defi_debut]"))]
        if der and der[-1].endswith("(isole)"):
            return t("on.indice.isole")
        if der and der[-1].endswith("(hors)"):
            return t("on.indice.hors_chemin")
        if step.get("fs") == "on_defi" and _defi_coupes() < donnees()["maillage"]["coupes_defi"]:
            return t("on.indice.recoupe")
        if der and der[-1].endswith("(peu)"):
            return t("on.indice.recoupe")
        if der and der[-1].startswith(("[defi_coupe]", "[defi_debut]")) and step.get("fs") == "on_defi3":
            return t("on.indice.encore", n=_defi_coupes(), total=donnees()["maillage"]["coupes_defi"])
    return None


def surveiller(state, lignes):
    """À chaque tour : une commande qui changerait la radio (rfkill block, nmcli … connect, bluetoothctl pair…), un sudo
    sur la radio, un balayage actif : la créature rappelle la règle (une fois). Une liste Wi-Fi AVEC les noms : la
    créature rappelle que ce sont ceux des voisins (une fois, même pendant une leçon). meshtastic --sendtext : la règle
    de l'émission (une fois)."""
    if not dossier().is_dir():
        return False
    c = o_(state)
    for l in lignes or []:
        l = (l or "").strip()
        if NOMS_VOISINS.search(l) and not _fait(c, "garde:noms"):
            msg = t("on.garde.noms")
            core.say(state, msg, 16)
            core.terminal(state, "🔒 " + msg)
            return True
        if EMET.search(l) and not _fait(c, "garde:emet"):
            msg = t("on.garde.emet")
            core.say(state, msg, 16)
            core.terminal(state, "📡 " + msg)
            return True
    from . import histoire
    les, _e = histoire.lecon_courante(state)
    if les and les["id"] in LECONS:
        return False
    for l in lignes or []:
        l = (l or "").strip()
        sudo_radio = re.search(r"(^|[;&|]\s*)sudo\s+(nmcli|iw|iwconfig|rfkill|bluetoothctl|meshtastic|rtl_\w+|dump1090)\b", l)
        if sudo_radio and not _fait(c, "garde:sudo"):
            msg = t("on.indice.sudo")
        elif CHANGE.search(l) and not sudo_radio and not re.match(r"^sudo\b", l) and not _fait(c, "garde:change"):
            msg = t("on.indice.change")
        elif CHERCHE.search(l) and not _fait(c, "garde:cherche"):
            msg = t("on.indice.cherche")
        else:
            continue
        core.say(state, msg, 16)
        core.terminal(state, "⚠ " + msg)
        return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


def couleur(tid):
    return donnees()["couleurs"].get(tid, 117)


def grille_onde(per, largeur=56, hauteur=9, phase=0.0, mur=None, reste=100):
    """L'onde en caractères : [ligne] ; per oscillations sur la largeur ; mur : la colonne d'un mur (l'amplitude tombe
    à reste % derrière lui)."""
    A = (hauteur - 1) / 2
    g = [[" "] * largeur for _ in range(hauteur)]
    avant = None
    for x in range(largeur):
        a = A if mur is None or x < mur else A * reste / 100
        y = A - a * math.sin(2 * math.pi * (per * x / largeur) - phase)
        r = max(0, min(hauteur - 1, int(round(y))))
        de, a_ = (r, r) if avant is None or (mur is not None and x == mur) else (min(avant, r), max(avant, r))
        for k in range(de, a_ + 1):          # la vague reste continue : on relie les points d'une colonne à l'autre
            if k == r or (k != avant):
                g[k][x] = "•"
        avant = r
    if mur is not None:
        for r in range(hauteur):
            g[r][mur] = "▓"
            if mur + 1 < largeur:
                g[r][mur + 1] = "▓"
    return ["".join(l) for l in g]


def lignes_onde(state, arg=None, phase=0.0):
    f = frequence_de(arg) if arg else (_hz_tech("wifi24"), "wifi24")
    if not f:
        return [t("on.onde.aide")]
    hz, tid = f
    lam = longueur_onde(hz)
    col = couleur(tid) if tid else 117
    nom = t("on.tech." + tid) if tid else _hz_texte(hz)
    out = [f" {_c(col)}{BOLD}〰 " + t("on.onde.titre", nom=nom) + RESET, ""]
    out += [f"  {_c(col)}{l}{RESET}" for l in grille_onde(periodes(hz), phase=phase)]
    out += ["", "  " + t("on.onde.frequence", f=_hz_texte(hz), n=_grand(hz)),
            "  " + t("on.onde.longueur", l=texte_longueur(lam)),
            f"  {DIM}" + t("on.onde.calcul", v="300 000 000", f=_grand(hz), l=f"{lam:.4g}") + RESET,
            "  " + t("on.onde.morale"), f"  {DIM}" + t("on.onde.aide") + RESET]
    noter("onde", f"{tid or hz} (ok)")
    return out


def _grand(n):
    return f"{n:,}".replace(",", " ")


def _hz_texte(hz):
    for div, u in ((10 ** 9, "GHz"), (10 ** 6, "MHz"), (10 ** 3, "kHz")):
        if hz >= div:
            return f"{hz / div:.6g} {u}"
    return f"{hz} Hz"


def lignes_longueur(arg):
    hz = _hz_tech("lora")
    if not arg:
        return [t("on.longueur.aide", f=_hz_texte(hz))]
    if longueur_ok(arg, hz):
        noter("longueur", f"{arg} (ok)")
        return [f" {_c(78)}✔ " + t("on.longueur.ok", l=texte_longueur(longueur_onde(hz))) + RESET,
                "  " + t("on.longueur.morale")]
    noter("longueur", f"{arg} (faux)")
    return [f" {_c(203)}✖ " + t("on.longueur.faux", f=_hz_texte(hz)) + RESET]


def lignes_mur(matiere=None, n=1, phase=0.0):
    matiere = matiere if matiere in donnees()["onde"]["murs"] else "brique"
    n = max(1, min(3, n))
    out = [f" {_c(250)}{BOLD}🧱 " + t("on.mur.titre", matiere=t("on.matiere." + matiere), n=n) + RESET, ""]
    for tid in ("lora", "wifi24", "wifi5"):
        db = affaiblissement(matiere, tid, n)
        amp, pui = restant_pc(db)
        out.append(f"  {_c(couleur(tid))}{BOLD}{t('on.tech.' + tid)}{RESET}  " + t("on.mur.perte", db=db, amp=amp, pui=pui))
        out += [f"  {_c(couleur(tid))}{l}{RESET}" for l in grille_onde(periodes(_hz_tech(tid)), 44, 7, phase, 22, amp)]
    out += ["", "  " + t("on.mur.morale"), f"  {DIM}" + t("on.mur.grands") + RESET, f"  {DIM}" + t("on.mur.aide") + RESET]
    noter("mur", f"{matiere} {n} (ok)")
    return out


def lignes_traverse(arg):
    if not arg:
        return [t("on.traverse.aide")]
    f = frequence_de(arg)
    tid = f[1] if f else None
    bon = traverse_le_mieux()
    if tid == bon:
        noter("traverse", f"{tid} (ok)")
        return [f" {_c(78)}✔ " + t("on.traverse.ok") + RESET, "  " + t("on.traverse.morale")]
    noter("traverse", f"{tid or '?'} (faux)")
    return [f" {_c(203)}✖ " + t("on.traverse.faux") + RESET]


def lignes_reseaux(arg):
    fr = wifi_freqs()
    if fr is None:
        noter("reseaux", "raconte (ok)")
        return [t("on.reseaux.sans")]
    if arg is None:
        return [t("on.reseaux.aide")]
    n = len(fr)
    if reseaux_ok(arg, n):
        noter("reseaux", "juste (ok)")       # jamais la liste, jamais un nom : seulement que la réponse était juste
        return [f" {_c(78)}✔ " + t("on.reseaux.ok", n=n) + RESET, "  " + t("on.reseaux.morale")]
    noter("reseaux", "loin (faux)")
    return [f" {_c(203)}✖ " + t("on.reseaux.faux") + RESET]


def lignes_canaux():
    fr = wifi_freqs()
    exemple = fr is None
    if exemple:
        fr = donnees().get("exemple_canaux", [])
    r = resume_wifi(fr)
    out = [f" {_c(78)}{BOLD}📶 " + t("on.canaux.titre") + RESET, ""]
    if exemple:
        out.append(f"  {DIM}" + t("on.canaux.exemple") + RESET)
    out.append("  " + t("on.canaux.bandes", n=r["n"], b24=r["bandes"].get("2,4", 0), b5=r["bandes"].get("5", 0),
                        b6=r["bandes"].get("6", 0)))
    out.append("")
    haut = max([1] + list(r["canaux"].values()))
    for niv in range(haut, 0, -1):
        out.append("  " + "".join((f"{_c(78)}██{RESET} " if r["canaux"].get(c, 0) >= niv else "   ") for c in range(1, 14)))
    out.append("  " + "".join(f"{c:<3}" for c in range(1, 14)))
    out += ["  " + DIM + t("on.canaux.axe") + RESET, "", "  " + t("on.canaux.morale"), f"  {DIM}" + t("on.canaux.grands") + RESET]
    noter("canaux", ("exemple" if exemple else "anonyme") + " (ok)")
    return out


def lignes_voisins():
    out = [f" {_c(141)}{BOLD}🔒 " + t("on.voisins.titre") + RESET, ""]
    out += ["  " + l for l in t("on.voisins.texte").split("\n")]
    noter("voisins", "lu (ok)")
    return out


NOMS_RADIOS = {"wlan": "Wi-Fi", "bluetooth": "Bluetooth", "wwan": "4G / 5G", "gps": "GPS", "fm": "FM", "nfc": "NFC",
               "uwb": "UWB", "wimax": "WiMAX", "wigig": "WiGig"}


def lignes_radios():
    rs = radios()
    out = [f" {_c(75)}{BOLD}📻 " + t("on.radios.titre") + RESET, ""]
    if not rs:
        out.append("  " + t("on.radios.aucune"))
    for ty, soft, hard in rs:
        etat = t("on.radios.coupee_inter") if hard else (t("on.radios.coupee") if soft else t("on.radios.allumee"))
        out.append(f"  📡 {NOMS_RADIOS.get(ty, ty):<10} {etat}")
    out += ["", "  " + t("on.radios.telephone"), f"  {DIM}" + t("on.radios.grands") + RESET]
    noter("radios", f"{len(rs)} (ok)")
    return out


def position_regle(hz, largeur):
    """La colonne d'une fréquence sur la règle logarithmique (de 10 MHz à 10 GHz)."""
    x = (math.log10(hz) - 7) / 3
    return max(0, min(largeur - 1, int(round(x * (largeur - 1)))))


def lignes_spectre():
    L = 60
    out = [f" {_c(229)}{BOLD}🌈 " + t("on.spectre.titre") + RESET, ""]
    regle = ["─"] * L
    for k, txt in ((7, "10 MHz"), (8, "100 MHz"), (9, "1 GHz"), (10, "10 GHz")):
        regle[position_regle(10 ** k, L)] = "┼"
    out.append("  " + "".join(regle))
    lab = [" "] * (L + 8)
    for k, txt in ((7, "10M"), (8, "100M"), (9, "1G"), (10, "10G")):
        p = position_regle(10 ** k, L)
        for i, ch in enumerate(txt):
            if p + i < len(lab):
                lab[p + i] = ch
    out.append("  " + "".join(lab).rstrip())
    out.append("")
    for x in sorted(donnees()["spectre"]["techs"], key=lambda x: (x["hz"], x["id"])):
        p = position_regle(x["hz"], L)
        marque = "✓" if x["libre"] == "l" else "✗"
        out.append("  " + " " * p + f"{_c(couleur(x['id']))}▲{RESET} " + f"{t('on.tech.' + x['id'])} ({x['bande']}) {marque}")
    out += ["", "  " + t("on.spectre.legende"), "  " + t("on.spectre.morale"), f"  {DIM}" + t("on.spectre.grands") + RESET]
    noter("spectre", "vu (ok)")
    return out


def lignes_regle(state, rep):
    gr = _graine(state)
    cartes = regle_cartes(gr)
    if not rep:
        out = [f" {_c(229)}{BOLD}📏 " + t("on.regle.titre") + RESET, ""]
        out += [f"  {BOLD}{l}{RESET}  {t('on.tech.' + i)} — {t('on.usage.' + i)}" for l, i in cartes]
        return out + ["", "  " + t("on.regle.aide")]
    r = [x.upper()[:1] for x in rep]
    bon = regle_reponse(gr)
    if r != bon:
        justes = sum(1 for x, y in zip(r, bon) if x == y)
        noter("regle", " ".join(r) + " (faux)")
        return [f" {_c(203)}✖ " + t("on.regle.faux", n=justes, total=len(bon)) + RESET]
    noter("regle", " ".join(r) + " (ok)")
    hz = {x["id"]: x for x in donnees()["spectre"]["techs"]}
    pos = dict(cartes)
    out = [f" {_c(78)}✔ " + t("on.regle.ok") + RESET, ""]
    for l in bon:
        out.append(f"  {_c(couleur(pos[l]))}▲{RESET} {l} {t('on.tech.' + pos[l])} : {hz[pos[l]]['bande']}")
    return out + ["", "  " + t("on.regle.morale")]


def lignes_libre(state, rep):
    gr = _graine(state)
    c = libre_cartes(gr)
    if not rep:
        out = [f" {_c(78)}{BOLD}🔓 " + t("on.libre.titre") + RESET, ""]
        out += ["  " + l for l in t("on.libre.regle").split("\n")] + [""]
        out += [f"  {n}. {t('on.tech.' + i)} — {t('on.usage.' + i)}" for n, i, _r in c]
        return out + ["", "  " + t("on.libre.aide")]
    r = [x.lower()[:1] for x in rep]
    if len(r) != len(c) or any(x not in "lr" for x in r):
        return [t("on.libre.aide")]
    justes = [(n, i) for (n, i, rr), x in zip(c, r) if x == rr]
    out = []
    if len(justes) == len(c):
        noter("libre", " ".join(r) + " (ok)")
        out.append(f" {_c(78)}✔ " + t("on.libre.ok") + RESET)
    else:
        noter("libre", " ".join(r) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("on.libre.faux", n=len(justes), total=len(c)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("on.libre." + i + ".pourquoi"))
    return out


CHIRP = ["      ╱│    ╱│    ╱│    ╱│", "    ╱  │  ╱  │  ╱  │  ╱  │", "  ╱    │╱    │╱    │╱    │"]


def lignes_lora():
    out = [f" {_c(141)}{BOLD}🛰 " + t("on.lora.titre") + RESET, ""] + [f"  {_c(141)}{l}{RESET}" for l in CHIRP] + [""]
    for k in ("chirp", "portee", "debit", "energie", "bande"):
        out.append("  • " + t("on.lora." + k))
    out += ["", f"  {DIM}" + t("on.lora.grands") + RESET]
    noter("lora", "vu (ok)")
    return out


def lignes_temps():
    L = donnees()["lora"]
    out = [f" {_c(141)}{BOLD}⏱ " + t("on.temps.titre", octets=L["octets"]) + RESET, "",
           f"  {DIM}{'SF':<4}{t('on.temps.symbole'):>14}{t('on.temps.symboles'):>10}{t('on.temps.message'):>14}{t('on.temps.portee'):>12}{RESET}"]
    for sf in L["facteurs"]:
        us = temps_emission_us(sf)
        out.append(f"  {sf:<4}{duree_symbole_us(sf) / 1000:>11.3f} ms{symboles_message(sf) + L['preambule']:>10}"
                   f"{us / 1000:>11.1f} ms{portee_m(sf) / 1000:>9.1f} km")
    out += ["", "  " + t("on.temps.morale"), f"  {DIM}" + t("on.temps.grands") + RESET]
    noter("temps", "vu (ok)")
    return out


def dessin_vallee(sf, distance, phase=1.0):
    """La vallée en caractères : la tour à gauche, la tour d'en face à droite ; le message (✉) avance jusqu'à sa portée."""
    L = 50
    po = portee_m(sf)
    arrive = po >= distance
    bout = L - 1 if arrive else int(L * po / distance)
    pos = int(min(bout, phase * bout))
    ciel = [" "] * L
    for x in range(0, pos):
        ciel[x] = "·"
    ciel[min(pos, L - 1)] = "✉" if (arrive or phase < 1) else "✖"
    return ["  📡" + "".join(ciel) + "📡",
            "  ▲" + "▁▂▃▄▅▆▇▆▅▄▃▂▁" * 3 + "▁" * (L - 39) + "▲",
            "  " + t("on.vallee.mesure", d=f"{distance / 1000:g}", p=f"{po / 1000:g}")]


def lignes_vallee(state, arg, phase=1.0):
    gr = _graine(state)
    d = vallee_m(gr)
    if arg is None:
        out = [f" {_c(141)}{BOLD}⛰ " + t("on.vallee.titre", d=f"{d / 1000:g}") + RESET, ""]
        for sf in donnees()["lora"]["facteurs"]:
            out.append(f"  SF{sf:<3} " + t("on.vallee.ligne", p=f"{portee_m(sf) / 1000:g}", ms=f"{temps_emission_us(sf) / 1000:.0f}"))
        return out + ["", "  " + t("on.vallee.aide")]
    try:
        sf = int(re.sub(r"(?i)^sf", "", arg.strip()))
    except ValueError:
        return [t("on.vallee.aide")]
    if sf not in donnees()["lora"]["facteurs"]:
        return [t("on.vallee.aide")]
    out = [f" {_c(141)}{BOLD}⛰ " + t("on.vallee.envoi", sf=sf) + RESET, ""] + dessin_vallee(sf, d, phase) + [""]
    bon = sf_min(d)
    o = o_(state)
    if portee_m(sf) < d:
        noter("vallee", f"SF{sf} (court)")
        return out + [f" {_c(203)}✖ " + t("on.vallee.court") + RESET]
    if sf != bon:
        noter("vallee", f"SF{sf} (lent)")
        return out + [f" {_c(215)}✖ " + t("on.vallee.lent", ms=f"{temps_emission_us(sf) / 1000:.0f}",
                                            ms2=f"{temps_emission_us(bon) / 1000:.0f}") + RESET]
    o["sf"] = sf
    noter("vallee", f"SF{sf} (ok)")
    return out + [f" {_c(78)}✔ " + t("on.vallee.ok", sf=sf, ms=f"{temps_emission_us(sf) / 1000:.0f}") + RESET]


def lignes_messages(state, arg):
    o = o_(state)
    sf = o.get("sf") or sf_min(vallee_m(_graine(state)))
    us = temps_emission_us(sf)
    if arg is None:
        return [t("on.messages.aide", sf=sf, ms=f"{us / 1000:.1f}")]
    if messages_ok(arg, sf):
        noter("messages", f"SF{sf} (ok)")
        return [f" {_c(78)}✔ " + t("on.messages.ok", n=messages_heure(sf), sf=sf) + RESET, "  " + t("on.messages.morale"),
                f"  {DIM}" + t("on.messages.grands") + RESET]
    noter("messages", f"SF{sf} (faux)")
    return [f" {_c(203)}✖ " + t("on.messages.faux", ms=f"{us / 1000:.1f}") + RESET]


ETOILE = ["   📟   📟   📟", "    ╲   │   ╱", "      🗼 ─── 🌐 ─── 🖥", "    ╱   │   ╲", "   📟   📟   📟"]
TOILE = ["   📟 ─── 📟 ─── 📟", "   │  ╲   │   ╱  │", "   📟 ─── 📟 ─── 📟", "   │  ╱   │   ╲  │", "   📟 ─── 📟 ─── 📟"]


def lignes_passerelle():
    out = [f" {_c(117)}{BOLD}🗼 " + t("on.passerelle.titre") + RESET, ""] + [f"  {_c(117)}{l}{RESET}" for l in ETOILE] + [""]
    out += ["  " + l for l in t("on.passerelle.texte").split("\n")] + [f"  {DIM}" + t("on.passerelle.grands") + RESET]
    noter("passerelle", "vue (ok)")
    return out


def lignes_maillage():
    out = [f" {_c(141)}{BOLD}🕸 " + t("on.maillage.titre") + RESET, ""] + [f"  {_c(141)}{l}{RESET}" for l in TOILE] + [""]
    out += ["  " + l for l in t("on.maillage.texte").split("\n")] + [f"  {DIM}" + t("on.maillage.grands") + RESET]
    noter("maillage", "vu (ok)")
    return out


def lignes_choix(state, rep):
    c = choix_cartes(_graine(state))
    if not rep:
        out = [f" {_c(117)}{BOLD}🤔 " + t("on.choix.titre") + RESET, ""]
        out += [f"  {n}. " + t("on.choix." + i) for n, i, _r in c]
        return out + ["", "  " + t("on.choix.aide")]
    r = [x.lower()[:1] for x in rep]
    if len(r) != len(c) or any(x not in "pm" for x in r):
        return [t("on.choix.aide")]
    justes = [(n, i) for (n, i, rr), x in zip(c, r) if x == rr]
    out = []
    if len(justes) == len(c):
        noter("choix", " ".join(r) + " (ok)")
        out.append(f" {_c(78)}✔ " + t("on.choix.ok") + RESET)
    else:
        noter("choix", " ".join(r) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("on.choix.faux", n=len(justes), total=len(c)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("on.choix." + i + ".pourquoi"))
    return out


# ---------------------------------------------------------------- le maillage : mesh-route, mesh-envoie, mesh-coupe
def _icone(mid):
    m = _port().machine(mid)
    return m["icone"] if m else "?"


def ligne_chemin(chemin, coupe=None):
    fl = f" {_c(141)}─✉→{RESET} "
    s = "  " + fl.join(f"{_icone(x)} {x}" for x in chemin)
    if coupe:
        s += f" {_c(203)}─✖ {coupe}{RESET}"
    return s


def carte_maillage(coupes=(), chemin=()):
    """Les nœuds sur la carte du Terminaworld (positions du Port) : ● allumé, ✖ coupé, ✉ sur le chemin."""
    W, H = 52, 11
    g = [[" "] * W for _ in range(H)]
    pos = _port().donnees()["carte"]

    def xy(mid):
        x, y = pos[mid]
        return int(round(x * (W - 8))), int(round(y * (H - 1)))
    for a, b in liens():
        if a in coupes or b in coupes:
            continue
        (x0, y0), (x1, y1) = xy(a), xy(b)
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(1, n):
            x, y = x0 + (x1 - x0) * k // n, y0 + (y1 - y0) * k // n
            if g[y][x] == " ":
                g[y][x] = "·"
    lignes = ["".join(l) for l in g]
    for mid in noeuds():
        x, y = xy(mid)
        marque = "✖" if mid in coupes else ("✉" if mid in chemin else "●")
        lab = f"{marque}{mid}"
        l = lignes[y]
        lignes[y] = (l[:x] + lab + l[x + len(lab):])[:W + 8]
    return lignes


def lignes_route(state, dest=None):
    o = o_(state)
    coupes = o["coupes"]
    dest = (dest or o.get("cible") or "").strip().lower() or None
    if dest and dest not in noeuds():
        return [t("on.mesh.inconnu", nom=dest), t("on.mesh.noeuds", liste=", ".join(noeuds()))]
    vagues = inondation("camp", coupes)
    sauts = {m: i for i, v in enumerate(vagues) for m in v}
    chemin = route("camp", dest, coupes) if dest else []
    out = [f" {_c(141)}{BOLD}🕸 " + t("on.mesh.route.titre") + RESET, ""]
    out += [f"  {_c(141)}{l}{RESET}" for l in carte_maillage(coupes, chemin or [])] + [""]
    for m in noeuds():
        if m == "camp":
            continue
        if m in coupes:
            out.append(f"  {DIM}{_icone(m)} {m:<8} ✖ {t('on.mesh.coupe_court')}{RESET}")
        elif m in sauts:
            r = route("camp", m, coupes)
            out.append(f"  {_icone(m)} {m:<8} {t('on.mesh.sauts', n=sauts[m])}  {DIM}{t('on.mesh.par', par=r[-2])}{RESET}")
        else:
            out.append(f"  {_c(203)}{_icone(m)} {m:<8} {t('on.mesh.isole_court')}{RESET}")
    if dest:
        out.append("")
        if chemin:
            out += [f"  {BOLD}" + t("on.mesh.chemin", dest=dest, n=len(chemin) - 1) + RESET, ligne_chemin(chemin)]
        else:
            out.append(f"  {_c(203)}" + t("on.mesh.isole", dest=dest) + RESET)
    out += ["", f"  {DIM}" + t("on.mesh.aide") + RESET]
    noter("route", f"{dest or '-'} (ok)")
    return out


def lignes_envoie(state, args):
    o = o_(state)
    coupes = o["coupes"]
    if not args:
        return [t("on.mesh.envoie.aide")]
    dest = args[0].strip().lower()
    message = " ".join(args[1:]).strip().strip("\"'") or "…"
    r = envoi(dest, coupes)
    out = []
    if r["raison"] == "inconnu":
        return [t("on.mesh.inconnu", nom=dest), t("on.mesh.noeuds", liste=", ".join(noeuds()))]
    if r["raison"] == "camp":
        return [t("on.mesh.camp")]
    vagues = inondation("camp", coupes)
    out.append(f" {_c(141)}{BOLD}✉ " + t("on.mesh.envoie.titre", dest=dest, msg=message[:40]) + RESET)
    out.append("")
    for i, v in enumerate(vagues[1:], 1):
        out.append(f"  {DIM}" + t("on.mesh.vague", n=i) + RESET + " " + ", ".join(f"{_icone(x)} {x}" for x in v))
        if r["ok"] and dest in v:
            break
    out.append("")
    defi = o.get("cible") and dest == o.get("cible")
    if not r["ok"]:
        out.append(f" {_c(203)}✖ " + t("on.mesh.rate." + r["raison"], dest=dest, n=r["sauts"],
                                        max=donnees()["maillage"]["sauts_max"]) + RESET)
        noter("envoie", f"{dest} : {r['raison']} (perdu)")
        if defi:
            noter("defi", f"{dest} (isole)")
        return out
    out += [ligne_chemin(r["chemin"]), "",
            f" {_c(78)}✔ " + t("on.mesh.arrive", dest=dest, n=r["sauts"], reste=donnees()["maillage"]["sauts_max"] - r["sauts"]) + RESET]
    noter("envoie", f"{' → '.join(r['chemin'])} (ok)")         # le chemin seulement, jamais le message
    if coupes:
        out.append("  " + t("on.mesh.detour", n=len(coupes)))
        noter("detour", f"{len(coupes)} {t('on.mesh.coupes_mot')} (ok)")
    if defi:
        n = _defi_coupes()
        if n >= donnees()["maillage"]["coupes_defi"]:
            noter("defi", f"{dest} {n} (ok)")
            out += ["", f" {_c(213)}{BOLD}🌩 " + t("on.defi.reussi", n=n) + RESET]
        else:
            noter("defi", f"{dest} {n} (peu)")
            out.append("  " + t("on.defi.pas_assez", n=n, total=donnees()["maillage"]["coupes_defi"]))
    return out


def lignes_coupe(state, args):
    o = o_(state)
    coupes = o["coupes"]
    a = [x.lower() for x in args]
    if a and a[0] in ("-r", "--rallume", "rallume", "allume"):
        qui = a[1] if len(a) > 1 else None
        if qui:
            o["coupes"] = [x for x in coupes if x != qui]
            noter("rallume", f"{qui} (ok)")
            return [f"💡 " + t("on.mesh.rallume", nom=qui)]
        o["coupes"] = []
        noter("rallume", "tous (ok)")
        return ["💡 " + t("on.mesh.rallume_tout")]
    if not a:
        if not coupes:
            return [t("on.mesh.coupe.aide")]
        return [t("on.mesh.coupes", liste=", ".join(coupes)), t("on.mesh.coupe.aide")]
    qui = a[0]
    if qui not in noeuds():
        return [t("on.mesh.inconnu", nom=qui), t("on.mesh.noeuds", liste=", ".join(noeuds()))]
    if qui == "camp":
        return [t("on.mesh.camp_coupe")]
    cible = o.get("cible")
    if cible and qui == cible:
        return [t("on.defi.pas_cible", cible=cible)]
    if qui in coupes:
        return [t("on.mesh.deja", nom=qui)]
    avant = route("camp", cible, coupes) if cible else None
    coupes.append(qui)
    out = [f"🌑 " + t("on.mesh.coupe", nom=qui)]
    noter("coupe", f"{qui} (ok)")
    if cible:
        apres = route("camp", cible, coupes)
        if avant and qui in avant:
            if apres:
                noter("defi_coupe", f"{qui} (ok)")
                n = _defi_coupes()
                out += ["  " + t("on.defi.coupe_ok", n=n, total=donnees()["maillage"]["coupes_defi"]),
                        "  " + t("on.mesh.nouveau", dest=cible, n=len(apres) - 1), ligne_chemin(apres)]
            else:
                noter("defi_coupe", f"{qui} (isole)")
                out += [f" {_c(203)}⚠ " + t("on.defi.isole", dest=cible) + RESET]
        else:
            noter("defi_coupe", f"{qui} (hors)")
            out.append("  " + t("on.defi.hors_chemin", nom=qui, dest=cible))
            if avant:
                out.append(ligne_chemin(avant))
    else:
        r = route("camp", "feu", coupes)
        out.append("  " + (t("on.mesh.autre_chemin") if r else t("on.mesh.plus_de_chemin")))
    return out


def lignes_defi(state):
    o = o_(state)
    cible = defi_cible(_graine(state))
    o["cible"] = cible
    o["coupes"] = []
    noter("defi_debut", f"{cible} (ok)")
    r = route("camp", cible)
    out = [f" {_c(213)}{BOLD}🌩 " + t("on.defi.titre") + RESET, ""]
    out += ["  " + l for l in t("on.defi.regles", dest=cible, n=donnees()["maillage"]["coupes_defi"]).split("\n")]
    out += ["", "  " + t("on.mesh.chemin", dest=cible, n=len(r) - 1), ligne_chemin(r)]
    return out


# ---------------------------------------------------------------- W5, W6
def lignes_adulte():
    L = donnees()["lora"]
    out = [f" {_c(215)}{BOLD}🧑‍🔧 " + t("on.adulte.titre") + RESET, ""]
    out += ["  " + l for l in t("on.adulte.regles", mw=L["puissance_mw"], pc=f"{L['cycle_pour_mille'] / 10:g}").split("\n")]
    la = shutil.which("meshtastic") is not None
    out += ["", "  " + (f"{_c(78)}✔ meshtastic{RESET}  " + t("on.adulte.present") if la else f"{DIM}✖ meshtastic{RESET}  " + t("on.adulte.absent"))]
    noter("adulte", "lu (ok)")
    return out


def lignes_noeud():
    out = [f" {_c(141)}{BOLD}📟 " + t("on.noeud.titre") + RESET, ""]
    for k in range(1, 6):
        out.append(f"  {k}. " + t(f"on.noeud.etape{k}"))
    out += ["", "  " + t("on.noeud.classe"), f"  {DIM}" + t("on.noeud.grands") + RESET]
    noter("noeud", "raconte (ok)")
    return out


def lignes_ecoute():
    out = [f" {_c(229)}{BOLD}👂 " + t("on.ecoute.titre") + RESET, ""]
    out += ["  " + l for l in t("on.ecoute.regles").split("\n")]
    for k in ("fm", "meteo", "avions"):
        out.append("  • " + t("on.ecoute." + k))
    noter("ecoute", "lu (ok)")
    return out


def lignes_avions(phase=1.0):
    """Les avions FICTIFS sur la carte du Terminaworld : altitude, vitesse et cap seulement (aucune immatriculation)."""
    W, H = 52, 11
    g = [[" "] * W for _ in range(H)]
    av = donnees()["ciel"]["avions"]
    for a in av:
        dx, dy = math.sin(math.radians(a["cap"])), -math.cos(math.radians(a["cap"]))
        x = int(round((a["x"] + 0.08 * phase * dx) * (W - 2))) % (W - 1)
        y = int(round((a["y"] + 0.08 * phase * dy) * (H - 1))) % H
        g[y][x] = "✈"
    out = [f" {_c(229)}{BOLD}✈ " + t("on.avions.titre") + RESET, ""]
    out += [f"  {_c(117)}" + "".join(l) + RESET for l in g] + [""]
    for i, a in enumerate(av, 1):
        out.append("  " + t("on.avions.ligne", n=i, alt=_grand(a["altitude"]), v=a["vitesse"], cap=a["cap"]))
    out += ["", "  " + t("on.avions.prive"), f"  {DIM}" + t("on.avions.grands") + RESET]
    noter("avions", "fictifs (ok)")
    return out


def lignes_anonyme():
    out = [f" {_c(78)}{BOLD}🕶 " + t("on.anonyme.titre") + RESET, ""]
    out += ["  " + l for l in t("on.anonyme.texte").split("\n")]
    noter("anonyme", "lu (ok)")
    return out


TOUR = ["        ╱╲  )))", "       ╱╲╱╲   )))", "        ││  ~~~", "       ╱██╲", "      ╱████╲", "  ▁▂▃▅██████▅▃▂▁ ⚓"]


def banniere(largeur=None):
    """L'entrée de la Tour : l'illustration B5 si elle existe (illustrations.bin, « ondes »), sinon le REPLI dessiné en
    caractères (la tour sur la falaise au-dessus du port, ses antennes qui vibrent)."""
    try:
        from . import scenes
        if scenes.disponible("ondes"):
            return scenes.illustration("ondes", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [213, 141, 117, 78, 229, 215]
    return [f"  {_c(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(TOUR)]


def aide():
    return banniere() + [f" {_c(141)}{BOLD}📡 " + t("on.aide.titre") + RESET] + ["  " + l for l in t("on.aide.liste").split("\n")]


def commande(args, sortie=None):
    """tg ondes [plan|onde [F]|longueur L|mur [matière] [n]|traverse T|reseaux N|canaux|voisins|radios|spectre|regle …|
    libre …|lora|temps|vallee [SF]|messages N|passerelle|maillage|choix …|defi|adulte|noeud|ecoute|avions|anonyme|
    mesh-route [nœud]|mesh-envoie nœud "message"|mesh-coupe nœud|-r [nœud]]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide").lower()).replace("œ", "oe")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        o_(st)
        arg = reste[0] if reste else None
        if sous in ("plan", "regles"):
            lignes.extend(banniere() + t("on.meuble.plan", nom=st.get("name", "")).split("\n"))
        elif sous == "onde":
            lignes.extend(lignes_onde(st, " ".join(reste) if reste else None))
        elif sous == "longueur":
            lignes.extend(lignes_longueur(" ".join(reste) if reste else None))
        elif sous in ("mur", "murs"):
            n = next((int(x) for x in reste if x.isdigit()), 1)
            m = next((ascii_bas(x.lower()) for x in reste if not x.isdigit()), None)
            lignes.extend(lignes_mur(m, n))
        elif sous == "traverse":
            lignes.extend(lignes_traverse(arg))
        elif sous == "reseaux":
            lignes.extend(lignes_reseaux(arg))
        elif sous == "canaux":
            lignes.extend(lignes_canaux())
        elif sous == "voisins":
            lignes.extend(lignes_voisins())
        elif sous in ("radios", "radio"):
            lignes.extend(lignes_radios())
        elif sous == "spectre":
            lignes.extend(lignes_spectre())
        elif sous == "regle":
            lignes.extend(lignes_regle(st, reste))
        elif sous in ("libre", "libres"):
            lignes.extend(lignes_libre(st, reste))
        elif sous == "lora":
            lignes.extend(lignes_lora())
        elif sous == "temps":
            lignes.extend(lignes_temps())
        elif sous == "vallee":
            lignes.extend(lignes_vallee(st, arg))
        elif sous == "messages":
            lignes.extend(lignes_messages(st, arg))
        elif sous in ("passerelle", "passerelles"):
            lignes.extend(lignes_passerelle())
        elif sous == "maillage":
            lignes.extend(lignes_maillage())
        elif sous == "choix":
            lignes.extend(lignes_choix(st, reste))
        elif sous == "defi":
            lignes.extend(lignes_defi(st))
        elif sous == "mesh-route":
            lignes.extend(lignes_route(st, arg))
        elif sous == "mesh-envoie":
            lignes.extend(lignes_envoie(st, reste))
        elif sous == "mesh-coupe":
            lignes.extend(lignes_coupe(st, reste))
        elif sous == "adulte":
            lignes.extend(lignes_adulte())
        elif sous in ("noeud", "noeuds"):
            lignes.extend(lignes_noeud())
        elif sous == "ecoute":
            lignes.extend(lignes_ecoute())
        elif sous in ("avions", "avion"):
            lignes.extend(lignes_avions())
        elif sous in ("anonyme", "anonymes"):
            lignes.extend(lignes_anonyme())
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
