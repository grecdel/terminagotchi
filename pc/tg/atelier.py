"""🤖 L'Atelier — Raspberry Pi, robots, électronique, embarqué (docs/programme.md § 2.16 et § 7.13 « L'embarqué et le
temps réel »).

Le neuvième monde de la phase 5 (§ 7.14, étape 9). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → atelier → requis). L'aile « atelier » de la maison (les
Constructs, les scripts) existe déjà : le chapitre et le lieu de ce monde s'appellent donc « robots »
(~/terrain_terminagotchi/robots), le monde garde son nom, l'Atelier. On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, plan_de_l_atelier.txt) :
  - LE ROBOT EST SIMULÉ. Un dossier robot/ dont les fichiers led, moteur et capteur_distance sont lus et écrits comme
    /sys/class/leds ou /sys/class/gpio sur un vrai Raspberry Pi (« tout est fichier »). Le robot vit sur une GRILLE
    avec des obstacles. `atelier pas` est la physique du monde : le jeu lit robot/moteur, fait avancer ou tourner le
    robot d'un cran, puis écrit ce que voit le capteur (en centimètres, 10 cm par case) et une ligne dans le journal.
  - Le CERVEAU du robot est un petit script de l'enfant (cerveau.sh), lancé par SA boucle dans SON shell :
    `for i in $(seq 20); do sh cerveau.sh; atelier pas; done` — comme la fonction loop() d'une carte Arduino. Le jeu
    ne lance jamais ce script lui-même sur PC (sur le téléphone, où le shell ne connaît pas les commandes du jeu,
    l'appli déroule cette même boucle, voir Atelier.kt).
  - AUCUN MATÉRIEL : le jeu ne touche ni /dev/tty*, ni port série, ni GPIO, ne flashe rien. Les vrais Raspberry Pi,
    cartes Arduino ou ESP32 sont facultatifs, racontés, « avec un adulte » (sudo apt, arduino-cli upload, screen
    /dev/ttyUSB0, esptool.py : seulement expliqués), sans marque mise en avant ni lien d'achat. Ce qui ne fait que LIRE
    est proposé (ls /sys/class/leds, command -v gpioset, crontab -l), caché quand l'outil manque.

LES PALIERS (at0 à at7) : la porte ; R1 la LED (tout est fichier) ; les capteurs, le moteur et les coordonnées ; ET / OU
/ NON (conditions, table de vérité) ; R2 la boucle du robot (for, while + Ctrl+C, le cerveau, l'essai qui se cogne) ;
le défi « le robot qui évite tous les obstacles » (exploit) ; R3 + R4 le vrai Raspberry Pi et le robot autonome (avec
un adulte, raconté ; le journal) ; l'embarqué et le temps réel (microcontrôleur ou ordinateur, le réflexe du robot,
Arduino et ESP32 depuis le terminal, le téléphone robot de poche). Mêmes règles sur Android (Atelier.kt), vecteurs
communs donnees/atelier/vecteurs.json.
"""
import hashlib
import json
import pkgutil
import random
import re
import sys
import unicodedata

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "atelier.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def ordre():
    return donnees()["directions"]["ordre"]


def arene(cle):
    """L'arène « e » (l'entraînement) ou celle du défi n° cle : {grille, depart}."""
    if cle in ("e", None):
        return donnees()["entrainement"]
    return donnees()["arenes"][int(cle) % len(donnees()["arenes"])]


def libre(g, x, y):
    return 0 <= y < len(g) and 0 <= x < len(g[0]) and g[y][x] != "#"


def distance_cases(g, x, y, d):
    """Le nombre de cases libres devant le robot (jusqu'au mur ou à l'obstacle)."""
    dx, dy = donnees()["directions"]["pas"][d]
    n = 0
    while libre(g, x + dx * (n + 1), y + dy * (n + 1)):
        n += 1
    return n


def distance_cm(g, x, y, d):
    return distance_cases(g, x, y, d) * donnees()["robot"]["case_cm"]


def tourner(d, sens):
    o = ordre()
    return o[(o.index(d) + (1 if sens == "droite" else -1)) % 4]


SYNONYMES = {"avance": "avance", "avancer": "avance", "forward": "avance", "go": "avance", "gauche": "gauche",
             "left": "gauche", "droite": "droite", "right": "droite", "stop": "stop", "arret": "stop", "halt": "stop"}


def lire_valeur(octets):
    """Le contenu d'un fichier du robot, lisible : UTF-8 ou UTF-16 (PowerShell 5 écrit en UTF-16), sans espaces."""
    if octets is None:
        return None
    if octets[:2] in (b"\xff\xfe", b"\xfe\xff"):
        s = octets.decode("utf-16", "replace")
    else:
        s = octets.decode("utf-8", "replace").replace("\x00", "")
    return s.replace("﻿", "").strip()


def moteur_de(texte):
    """« avance », « gauche », « droite », « stop » ; « ? » pour un mot que le moteur ne comprend pas ; « stop » si vide."""
    s = ascii_bas((texte or "").split("\n")[0] if texte else "")
    if not s:
        return "stop"
    return SYNONYMES.get(s, "?")


def led_de(texte):
    s = (texte or "").strip()
    return s if s in ("0", "1") else "?"


def pas_robot(cle, robot, moteur):
    """Un pas de la physique : (robot après, événement). robot = {x, y, d}. Événements : « avance », « choc » (un
    obstacle ou le bord juste devant : le robot ne bouge pas), « tourne », « stop », « inconnu »."""
    g = arene(cle)["grille"]
    x, y, d = robot["x"], robot["y"], robot["d"]
    if moteur == "avance":
        dx, dy = donnees()["directions"]["pas"][d]
        if libre(g, x + dx, y + dy):
            return {"x": x + dx, "y": y + dy, "d": d}, "avance"
        return dict(robot), "choc"
    if moteur in ("gauche", "droite"):
        return {"x": x, "y": y, "d": tourner(d, moteur)}, "tourne"
    if moteur == "stop":
        return dict(robot), "stop"
    return dict(robot), "inconnu"


def depart(cle):
    x, y, d = arene(cle)["depart"]
    return {"x": x, "y": y, "d": d}


def verdict(cases, chocs, pas):
    """Le défi : « choc » dès un choc ; au bout des pas, « ok » si assez de cases visitées, sinon « peu »."""
    D = donnees()["defi"]
    if chocs:
        return "choc"
    if pas < D["pas"]:
        return "en_cours"
    return "ok" if cases >= D["cases_min"] else "peu"


def simuler(cle, cerveau, pas):
    """Une suite de moteurs (cerveau : distance en cm → moteur) : [(robot, événement, distance après)]. Sert aux
    vecteurs et aux tests (le vrai cerveau de l'enfant est un script)."""
    g = arene(cle)["grille"]
    r = depart(cle)
    out = []
    for _ in range(pas):
        m = cerveau(distance_cm(g, r["x"], r["y"], r["d"]))
        r, ev = pas_robot(cle, r, m)
        out.append((dict(r), ev, distance_cm(g, r["x"], r["y"], r["d"])))
    return out


def _tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


def melange(graine, sel, liste):
    l2 = list(liste)
    random.Random(f"{sel}:{graine}").shuffle(l2)
    return l2


def arene_defi(graine):
    return _tire(graine, "arene", len(donnees()["arenes"]))


def porte(graine):
    p = donnees()["verite"]["portes"]
    return p[_tire(graine, "porte", len(p))]


def table_verite(p):
    """Les 4 sorties de la porte pour (A, B) = (0, 0), (0, 1), (1, 0), (1, 1)."""
    f = (lambda a, b: a and b) if p == "et" else (lambda a, b: a or b)
    return [str(int(f(a, b))) for a in (0, 1) for b in (0, 1)]


def chiffres(args):
    """« 0 0 0 1 », « 0001 », « 0,0,0,1 » → ['0', '0', '0', '1']."""
    return [c for c in "".join(args) if c in "01"] if all(re.fullmatch(r"[01,;]+", a) for a in args if a) else []


def choix_cartes(graine):
    """Les situations montrées (n°, id, bonne porte), mélangées pour cette partie."""
    s = melange(graine, "choix", donnees()["choix"]["situations"])[:donnees()["choix"]["montrees"]]
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(s)]


MOTS_PORTES = {"et": ("et", "and", "y", "und", "e", "и", "与", "かつ"), "ou": ("ou", "or", "o", "oder", "или", "或", "または"),
               "non": ("non", "not", "no", "nicht", "nao", "не", "非", "でない")}


def porte_de(mot):
    """Un mot tapé → « et », « ou », « non » (en français, en anglais, ou dans la langue du jeu), ou None."""
    m = ascii_bas(mot)
    for p, mots in MOTS_PORTES.items():
        if m in mots or m == ascii_bas(t("at.mot." + p)):
            return p
    return None


def reflexe(graine):
    """(vitesse en cm/s, temps d'un tour de boucle en ms, centimètres parcourus avant de réagir)."""
    R = donnees()["reflexe"]
    v = R["vitesses"][_tire(graine, "vitesse", len(R["vitesses"]))]
    ms = R["temps_ms"][_tire(graine, "temps", len(R["temps_ms"]))]
    return v, ms, v * ms // 1000


def nombres(texte):
    return [int(x) for x in re.findall(r"-?\d+", texte or "")]


def coord_ok(texte, x, y):
    return nombres(texte)[:2] == [x, y] and len(nombres(texte)) == 2


def robot_de(morceau):
    """(pièce, sens) de ce qu'une commande fait au robot (vue déployée), ou None : la première règle qui correspond."""
    m = (morceau or "").strip()
    for r in donnees()["vue"]["regles"]:
        if re.search(r["motif"], m):
            return r["piece"], r["sens"]
    return None


SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def robots_de(ligne):
    out = []
    for m in SEPARATEURS.split(ligne or ""):
        a = robot_de(m)
        if a:
            out.append(a)
    return out


def dessin_grille(cle, robot, vus=(), led="0", choc=False):
    """La grille en caractères (sans couleurs) : les numéros de colonnes et de lignes (x vers la droite, y vers le bas,
    comme les pixels), ▓ un obstacle, · une case déjà visitée, la flèche du robot (💥 s'il vient de se cogner)."""
    g = arene(cle)["grille"]
    fl = donnees()["directions"]["fleches"]
    vus = {tuple(v) for v in vus}
    out = ["    " + " ".join(str(x % 10) for x in range(len(g[0])))]
    for y, l in enumerate(g):
        cases = []
        for x, c in enumerate(l):
            if (x, y) == (robot["x"], robot["y"]):
                cases.append("*" if choc else fl[robot["d"]])
            elif c == "#":
                cases.append("▓")
            elif (x, y) in vus:
                cases.append("·")
            else:
                cases.append(".")
        out.append(f" {y % 10}  " + " ".join(cases))
    return out


# ================================================================ l'état, le terrain, le carnet de l'atelier
def a_(state):
    c = state.setdefault("atelier", {})
    c.setdefault("faits", [])
    c.setdefault("robot", dict(depart("e"), arene="e"))
    return c


def dossier():
    return core.TERRAIN / "robots"


def dossier_robot():
    return dossier() / "robot"


CARNET = "carnet_de_l_atelier.txt"
FICHIERS = ("led", "moteur", "capteur_distance")


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


def dernier(etiquette):
    l = [x for x in carnet().splitlines() if x.startswith(f"[{etiquette}]")]
    return l[-1] if l else None


def pas_depuis(debut):
    """Les pas faits depuis le dernier [debut] du carnet (l'essai, le défi)."""
    txt = carnet()
    i = txt.rfind(f"[{debut}]")
    if i < 0:
        return 0
    return len(re.findall(r"^\[pas\] ", txt[i:], re.M))


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


def lire_robot(nom):
    """Le contenu (nettoyé) d'un fichier du robot, ou None."""
    try:
        return lire_valeur((dossier_robot() / nom).read_bytes())
    except OSError:
        return None


def ecrire_robot(nom, valeur):
    return _ecrire(f"robots/robot/{nom}", f"{valeur}\n")


def capteur_de(state):
    r = a_(state)["robot"]
    return distance_cm(arene(r["arene"])["grille"], r["x"], r["y"], r["d"])


def cerveau_exemple():
    """Le cerveau d'exemple : il lit le capteur… et avance toujours (il se cognera : c'est la leçon)."""
    return "\n".join(["#!/bin/sh", "# " + t("at.cerveau.c1"), "# " + t("at.cerveau.c2"),
                      "d=$(cat robot/capteur_distance)", 'echo "' + t("at.cerveau.vois") + ' $d cm"',
                      "echo avance > robot/moteur", ""])


def cerveau_malin():
    """Les lignes du cerveau qui tourne devant l'obstacle (montrées par `atelier aide-cerveau`, jamais écrites par le jeu)."""
    return "\n".join(["#!/bin/sh", "# " + t("at.cerveau.c1"), "d=$(cat robot/capteur_distance)",
                      'if [ "$d" -lt 10 ]; then', "  echo droite > robot/moteur", "else", "  echo avance > robot/moteur",
                      "fi", ""])


def meubles(state):
    """Ce que le jeu pose dans l'Atelier quand il s'ouvre : {chemin relatif au terrain: contenu}."""
    a_(state)
    return {"robots/plan_de_l_atelier.txt": t("at.meuble.plan", nom=state.get("name", "")) + "\n",
            f"robots/{CARNET}": t("at.meuble.carnet") + "\n",
            "robots/robot/led": "0\n", "robots/robot/moteur": "stop\n",
            "robots/robot/capteur_distance": f"{capteur_de(state)}\n",
            "robots/cerveau_exemple.sh": cerveau_exemple()}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de l'Atelier : les fichiers du robot (remis s'ils ont disparu), le cerveau
    d'exemple, les Ponts des Nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel, contenu in tous.items():
        if rel.startswith("robots/robot/") or rel.endswith("plan_de_l_atelier.txt") or \
                (rel.endswith("cerveau_exemple.sh") and lid in ("at4", "at5")):
            if not (core.TERRAIN / rel).exists():
                _ecrire(rel, contenu)
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = a_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("at.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("at.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- les vérifications des étapes
def _cerveau_texte():
    try:
        return (dossier() / "cerveau.sh").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def cerveau_malin_ok(texte):
    """Le cerveau a une condition sur la distance et deux actions : tourner (droite ou gauche) et avancer."""
    s = texte or ""
    return bool(re.search(r"\bif\b", s) and re.search(r"-(lt|le|eq|gt|ge|ne)\b|[<>]", s) and re.search(r"capteur_distance", s)
                and re.search(r"\b(droite|gauche|right|left)\b", s) and re.search(r"\b(avance|forward)\b", s) and re.search(r"\bfi\b", s))


FS = {
    "at_led1": lambda: led_de(lire_robot("led")) == "1",
    "at_led0": lambda: led_de(lire_robot("led")) == "0" and dans_carnet("led", "1"),
    "at_avance": lambda: moteur_de(lire_robot("moteur")) == "avance",
    "at_pas_avance": lambda: dans_carnet("pas", "avance"),
    "at_ou": lambda: dans_carnet("ou"),
    "at_droite": lambda: moteur_de(lire_robot("moteur")) == "droite",
    "at_pas_tourne": lambda: dans_carnet("pas", "tourne"),
    "at_cases": lambda: dans_carnet("cases"),
    "at_verite": lambda: dans_carnet("verite"),
    "at_choix": lambda: dans_carnet("choix"),
    "at_cerveau": lambda: (dossier() / "cerveau.sh").is_file(),
    "at_essai": lambda: dans_carnet("essai_debut"),
    "at_essai_pas": lambda: pas_depuis("essai_debut") >= donnees()["essai"]["pas_min"],
    "at_malin": lambda: cerveau_malin_ok(_cerveau_texte()),
    "at_defi_debut": lambda: dans_carnet("defi_debut"),
    "at_defi": lambda: dans_carnet("defi"),
    "at_reflexe": lambda: dans_carnet("reflexe"),
}
CREE = {}

LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
AT = r"^(tg\s+)?atelier\s+"
O = "robots"
BOUCLE = r"^for\s+\w+\s+in\b.*\bdo\b.*\bsh\s+\S*cerveau\w*\.sh\b.*\batelier\s+pas\b.*\bdone\b"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LECONS = {
    # la porte de l'Atelier
    "at0": {"titre": "hist.at0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": O}), "cmd": "cd ~/terrain_terminagotchi/robots", "ici": O,
         "bravo": ("hist.entree.bravo", {"piece": O})},
        _n("at0", 1, cmd="ls", re=LS, ou=O),
        _n("at0", 2, cmd="cat plan_de_l_atelier.txt", re=LIRE + r".*plan_de_l_atelier", ou=O),
    ]},
    # R1 allumer une LED (simulée) : tout est fichier
    "at1": {"titre": "hist.at1.titre", "skill": None, "steps": [
        _n("at1", 0, cmd="ls robot", re=LS + r".*\brobot\b", ou=O),
        _n("at1", 1, cmd="cat robot/led", re=LIRE + r".*robot/led\b", ou=O),
        _n("at1", 2, cmd="echo 1 > robot/led", fs="at_led1", ou=O),
        _n("at1", 3, cmd="atelier robot", re=AT + r"robot\s*$"),
        _n("at1", 4, cmd="echo 0 > robot/led", fs="at_led0", ou=O),
        _n("at1", 5, cmd="cat robot/capteur_distance", re=LIRE + r".*robot/capteur_distance", ou=O),
    ]},
    # les capteurs, le moteur et les coordonnées
    "at2": {"titre": "hist.at2.titre", "skill": None, "steps": [
        _n("at2", 0, cmd="atelier grille", re=AT + r"grille\b"),
        _n("at2", 1, cmd="echo avance > robot/moteur", fs="at_avance", ou=O),
        _n("at2", 2, cmd="atelier pas", fs="at_pas_avance"),
        _n("at2", 3, cmd="atelier ou ?", fs="at_ou"),
        _n("at2", 4, cmd="echo droite > robot/moteur", fs="at_droite", ou=O),
        _n("at2", 5, cmd="atelier pas", fs="at_pas_tourne"),
        _n("at2", 6, cmd="atelier cases ?", fs="at_cases"),
    ]},
    # ET / OU / NON : le robot décide
    "at3": {"titre": "hist.at3.titre", "skill": None, "steps": [
        _n("at3", 0, cmd="atelier logique", re=AT + r"logique\b"),
        _n("at3", 1, cmd="[ 5 -lt 10 ] && echo vrai || echo faux",
           re=r"^\[\s+\S+\s+-(lt|gt|le|ge|eq|ne)\s+\S+\s+\]\s*$", win=False),
        _n("at3", 2, cmd='d=$(cat robot/capteur_distance); if [ "$d" -lt 10 ]; then echo obstacle; else echo libre; fi',
           re=r"^if\s+\[\s+\"?\$\w+\"?\s+-(lt|le|gt|ge|eq|ne)\s+\d+\s+\]", ou=O, win=False),
        _n("at3", 3, cmd="atelier verite", re=AT + r"v[eé]rit[eé]\s*$"),
        _n("at3", 4, cmd="atelier verite ? ? ? ?", fs="at_verite"),
        _n("at3", 5, cmd="atelier choix", re=AT + r"choix\s*$"),
        _n("at3", 6, cmd="atelier choix ? ? ?", fs="at_choix"),
    ]},
    # R2 la boucle du robot : for, while + Ctrl+C, le cerveau, l'essai
    "at4": {"titre": "hist.at4.titre", "skill": None, "steps": [
        _n("at4", 0, cmd="for i in 1 2 3; do cat robot/capteur_distance; sleep 1; done",
           re=r"^for\s+\w+\s+in\s+(\d|\{\d|\$\(seq\b)", ou=O, win=False),
        _n("at4", 1, cmd="while true; do cat robot/capteur_distance; sleep 1; done",
           re=r"^while\s+(true|:)", ou=O, win=False, tout_code=True),
        _n("at4", 2, cmd="cat cerveau_exemple.sh", re=LIRE + r".*cerveau_exemple", ou=O),
        _n("at4", 3, cmd="cp cerveau_exemple.sh cerveau.sh", fs="at_cerveau", ou=O),
        _n("at4", 4, cmd="atelier essai", fs="at_essai"),
        _n("at4", 5, cmd="for i in $(seq 10); do sh cerveau.sh; atelier pas; done", fs="at_essai_pas", ou=O, win=False),
        _n("at4", 6, cmd="nano cerveau.sh", fs="at_malin", ou=O),
    ]},
    # le défi : le robot simulé qui évite tous les obstacles (exploit)
    "at5": {"titre": "hist.at5.titre", "skill": None, "steps": [
        _n("at5", 0, cmd="atelier defi", fs="at_defi_debut"),
        _n("at5", 1, cmd="for i in $(seq 20); do sh cerveau.sh; atelier pas; done", fs="at_defi", ou=O, win=False,
           exploit="atelier.robot"),
    ]},
    # R3 + R4 le vrai Raspberry Pi et le robot autonome (avec un adulte, raconté)
    "at6": {"titre": "hist.at6.titre", "skill": None, "steps": [
        _n("at6", 0, cmd="atelier pi", re=AT + r"pi\b"),
        _n("at6", 1, cmd="ls /sys/class/leds", re=r"^ls\b.*/sys/class/leds", outil="/sys/class/leds", win=False,
           tout_code=True),
        _n("at6", 2, cmd="command -v gpioset pinctrl", re=r"^(command\s+-v|which|type)\s+(gpioset|pinctrl)\b", win=False,
           tout_code=True),
        _n("at6", 3, cmd="atelier gpio", re=AT + r"gpio\b"),
        _n("at6", 4, cmd="atelier autonome", re=AT + r"autonome\b"),
        _n("at6", 5, cmd="tail -5 robot/journal.txt", re=LIRE + r".*robot/journal\.txt", ou=O),
        _n("at6", 6, cmd="crontab -l", re=r"^crontab\s+-l\b", outil="crontab", win=False, tout_code=True),
    ]},
    # L'embarqué et le temps réel (§ 7.13)
    "at7": {"titre": "hist.at7.titre", "skill": None, "steps": [
        _n("at7", 0, cmd="atelier embarque", re=AT + r"embarqu[eé]\b"),
        _n("at7", 1, cmd="time sh cerveau.sh", re=r"^time\s+(sh|bash)\s+\S*cerveau\w*\.sh", ou=O, win=False),
        _n("at7", 2, cmd="atelier reflexe", re=AT + r"r[eé]flexe\s*$"),
        _n("at7", 3, cmd="atelier reflexe ?", fs="at_reflexe"),
        _n("at7", 4, cmd="atelier arduino", re=AT + r"arduino\b"),
        _n("at7", 5, cmd="command -v arduino-cli esptool.py", re=r"^(command\s+-v|which|type)\s+(arduino-cli|esptool)", win=False,
           tout_code=True),
        _n("at7", 6, cmd="atelier telephone", re=AT + r"t[eé]l[eé]phone\b"),
    ]},
}
CHAPITRE = {"id": "robots", "n": 20, "piece": "robots", "famille": "Constructs", "monde": True,
            "lecons": [f"at{i}" for i in range(8)], "objet": "robot_miniature", "titre": "roboticien"}


# ================================================================ l'arbre du Carrefour : quand l'Atelier s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "atelier"), {})


def _besoin():
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
    if "robots" in deja or histoire.fini(state, "robots") or not ouvert(state):
        return False
    deja.append("robots")
    core.log(state, t("at.ouvert.log"))
    core.say(state, histoire.dire(state, "at.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"atelier ou ?": "ou", "atelier cases ?": "cases", "atelier verite ? ? ? ?": "verite",
            "atelier choix ? ? ?": "choix", "atelier reflexe ?": "reflexe"}
MATERIEL = re.compile(r"(^|[;&|]\s*)(sudo\s+\S|\S*arduino-cli\s+(upload|burn)|\S*esptool(\.py)?\b.*\b(write_flash|erase_flash|write-flash|erase-flash)\b|"
                      r"gpioset\b|pinctrl\s+set\b|screen\s+/dev/|minicom\b|picocom\b|\S*(cat|echo|stty)\b.*\s/dev/tty(USB|ACM|S)\w*)")


def indice(step, tapees):
    """Un indice de l'Atelier : un sudo ou un vrai matériel, un « ? » recopié, une mauvaise réponse, une LED qui n'est
    ni 0 ni 1, un mot que le moteur ne comprend pas, la boucle sans `atelier pas`, le cerveau sans condition, le défi raté."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(MATERIEL.search(l) for l in lignes):
        return t("at.indice.materiel")
    if "?" in cmd.split() and any(TROU.search(l) for l in lignes if re.match(AT, l)):
        return t("at.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = dernier(et)
        if der and not der.endswith("(ok)") and any(re.match(AT + et, l) for l in lignes):
            return t("at.indice." + et)
    fs = step.get("fs") or ""
    if fs in ("at_led1", "at_led0") and led_de(lire_robot("led")) == "?":
        return t("at.indice.led")
    if fs in ("at_avance", "at_droite") and moteur_de(lire_robot("moteur")) == "?":
        return t("at.indice.moteur")
    if fs in ("at_led1", "at_led0", "at_avance", "at_droite") and any(re.match(r"^echo\b", l) and ">" not in l for l in lignes):
        return t("at.indice.redirection")
    if fs in ("at_essai_pas", "at_defi") and any(re.match(r"^for\b", l) and "atelier" not in l for l in lignes):
        return t("at.indice.boucle")
    if fs == "at_malin" and (dossier() / "cerveau.sh").is_file() and not cerveau_malin_ok(_cerveau_texte()):
        return t("at.indice.malin", cmd="atelier aide-cerveau")
    if fs == "at_defi":
        der = dernier("defi")
        if der and der.endswith("(choc)"):
            return t("at.indice.choc")
        if der and der.endswith("(peu)"):
            return t("at.indice.peu")
    return None


def surveiller(state, lignes):
    """À chaque tour : une commande qui toucherait un vrai matériel (un port série, un flashage, une broche GPIO) ou un
    sudo : la créature rappelle que le jeu n'y touche jamais, et que le vrai matériel se fait avec un adulte (une fois)."""
    if not dossier().is_dir():
        return False
    c = a_(state)
    for l in lignes or []:
        if MATERIEL.search((l or "").strip()) and not _fait(c, "garde:materiel"):
            msg = t("at.garde.materiel")
            core.say(state, msg, 16)
            core.terminal(state, "🔌 " + msg)
            return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
ETABLI = ["      ┌─┐   ┌───┐", "  💡 ─┤ ├───┤ ⚙ ├─ 🔋", "      └─┘   └─┬─┘", "   ╔══════════╧══╗  🤖", "   ║ ▓▓ ░░ ▓▓ ░░ ║",
          "  ═╩══════════════╩═"]


def banniere(largeur=None):
    """L'entrée de l'Atelier : l'illustration (illustrations.bin, « robots ») si elle existe, sinon le REPLI dessiné en
    caractères (l'établi, une LED, une carte, un petit robot)."""
    try:
        from . import scenes
        if scenes.disponible("robots"):
            return scenes.illustration("robots", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [220, 215, 117, 78, 213, 245]
    return [f"  {fg(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(ETABLI)]


def aide():
    return banniere() + [f" {fg(215)}{BOLD}🤖 " + t("at.aide.titre") + RESET] + _bloc("at.aide.liste")


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def _couleur_grille(lignes, choc=False):
    out = [f"  {DIM}{lignes[0]}{RESET}"]
    for l in lignes[1:]:
        l = f"{DIM}{l[:4]}{RESET}" + l[4:].replace("▓", f"{fg(245)}▓{RESET}").replace("·", f"{fg(78)}·{RESET}")
        for f_ in "▲▶▼◀":
            l = l.replace(f_, f"{fg(220)}{BOLD}{f_}{RESET}")
        if choc:
            l = l.replace("*", f"{fg(203)}{BOLD}✸{RESET}")
        out.append("  " + l)
    return out


def _etat_ligne(state):
    r = a_(state)["robot"]
    led = led_de(lire_robot("led"))
    return t("at.robot.etat", x=r["x"], y=r["y"], fleche=donnees()["directions"]["fleches"][r["d"]],
             led="💡" if led == "1" else "⚫", cm=capteur_de(state), moteur=moteur_de(lire_robot("moteur")))


def _ecrire_capteur(state):
    ecrire_robot("capteur_distance", capteur_de(state))


def lignes_robot(state):
    led = led_de(lire_robot("led"))
    noter("led", f"{led} ({led})")
    corps = ["   ┌─────┐", f"   │ {'💡' if led == '1' else '⚫'}  │ ← led", "   │ ◉ ◉ │ ← capteur_distance", "   └┬───┬┘",
             "    ◯   ◯  ← moteur"]
    out = [f" {fg(215)}{BOLD}🤖 " + t("at.robot.titre") + RESET, ""] + [f"  {fg(117)}{l}{RESET}" for l in corps] + [""]
    if led == "?":
        out.append("  " + t("at.robot.led_inconnue"))
    else:
        out.append("  " + t("at.robot.led_" + led))
    out += ["  " + _etat_ligne(state), f"  {DIM}" + t("at.robot.fichiers") + RESET]
    return out


def lignes_grille(state):
    r = a_(state)["robot"]
    out = [f" {fg(117)}{BOLD}🗺 " + t("at.grille.titre") + RESET, ""]
    out += _couleur_grille(dessin_grille(r["arene"], r, a_(state).get("vus", [])))
    out += ["", "  " + _etat_ligne(state)] + _bloc("at.grille.texte")
    noter("grille", "vue (ok)")
    return out


def _defi(state):
    return a_(state).get("defi") or {}


def lignes_pas(state):
    """Un pas de la physique : lire le moteur, bouger ou tourner, écrire le capteur et le journal."""
    a = a_(state)
    r = a["robot"]
    m = moteur_de(lire_robot("moteur"))
    nouveau, ev = pas_robot(r["arene"], r, m)
    a["robot"] = dict(nouveau, arene=r["arene"])
    vus = a.setdefault("vus", [[r["x"], r["y"]]])
    if [nouveau["x"], nouveau["y"]] not in vus:
        vus.append([nouveau["x"], nouveau["y"]])
    cm = capteur_de(state)
    _ecrire_capteur(state)
    noter("pas", f"{m} → ({nouveau['x']} ; {nouveau['y']}) {nouveau['d']} {cm} cm ({'avance' if ev == 'avance' else 'tourne' if ev == 'tourne' else ev})")
    n_journal = a["journal"] = a.get("journal", 0) + 1
    try:
        dossier_robot().mkdir(parents=True, exist_ok=True)
        with open(dossier_robot() / "journal.txt", "a", encoding="utf-8") as f:
            f.write(t("at.journal.ligne", n=n_journal, moteur=m, x=nouveau["x"], y=nouveau["y"], d=nouveau["d"], cm=cm) + "\n")
    except OSError:
        pass
    d = _defi(state)
    titre = ""
    fin = []
    if d and not d.get("fini"):
        d["pas"] = d.get("pas", 0) + 1
        if ev == "choc":
            d["chocs"] = d.get("chocs", 0) + 1
        if [nouveau["x"], nouveau["y"]] not in d.setdefault("vus", []):
            d["vus"].append([nouveau["x"], nouveau["y"]])
        v = verdict(len(d["vus"]), d.get("chocs", 0), d["pas"])
        titre = t("at.pas.defi", n=d["pas"], total=donnees()["defi"]["pas"], cases=len(d["vus"]),
                  min=donnees()["defi"]["cases_min"]) + " · "
        if v != "en_cours":
            d["fini"] = True
            noter("defi", f"{len(d['vus'])} {t('at.cases_mot')}, {d.get('chocs', 0)} {t('at.chocs_mot')} ({v})")
            couleur = 78 if v == "ok" else 203
            fin = ["", f" {fg(couleur)}{BOLD}" + ("🏆 " if v == "ok" else "✋ ") + t("at.defi." + v, cases=len(d["vus"]),
                                                                                       min=donnees()["defi"]["cases_min"]) + RESET]
            if v != "ok":
                fin.append("  " + t("at.defi.recommence"))
    vus_dessin = d.get("vus", []) if d and d.get("arene") == r["arene"] else vus
    out = [f" {fg(117)}🤖 " + titre + t("at.pas.ev." + ev, moteur=m) + f"  {DIM}· " + t("at.pas.capteur", cm=cm) + RESET]
    out += _couleur_grille(dessin_grille(r["arene"], a["robot"], vus_dessin, choc=ev == "choc"), choc=ev == "choc")
    return out + fin


def lignes_ou(state, rep):
    r = a_(state)["robot"]
    if not rep:
        return [t("at.ou.aide")]
    if coord_ok(" ".join(rep), r["x"], r["y"]):
        noter("ou", f"{r['x']} {r['y']} (ok)")
        return [f" {fg(78)}✔ " + t("at.ou.ok", x=r["x"], y=r["y"]) + RESET]
    noter("ou", " ".join(rep) + " (faux)")
    return [f" {fg(203)}✖ " + t("at.ou.faux") + RESET]


def lignes_cases(state, rep):
    cm = capteur_de(state)
    if not rep:
        return [t("at.cases.aide", cm=cm)]
    n = nombres(" ".join(rep))
    juste = cm // donnees()["robot"]["case_cm"]
    if n[:1] == [juste]:
        noter("cases", f"{juste} (ok)")
        return [f" {fg(78)}✔ " + t("at.cases.ok", cm=cm, n=juste) + RESET]
    noter("cases", " ".join(rep) + " (faux)")
    return [f" {fg(203)}✖ " + t("at.cases.faux", cm=cm) + RESET]


def lignes_logique():
    out = [f" {fg(213)}{BOLD}🔀 " + t("at.logique.titre") + RESET, ""] + _bloc("at.logique.texte")
    noter("logique", "lu (ok)")
    return out


def lignes_verite(state, rep):
    p = porte(_graine(state))
    juste = table_verite(p)
    if not rep:
        out = [f" {fg(213)}{BOLD}🔀 " + t("at.verite.titre", porte=t("at.mot." + p).upper()) + RESET, ""]
        out += _bloc("at.verite.texte", porte=t("at.mot." + p).upper())
        out += ["", f"   A B │ A {t('at.mot.' + p).upper()} B", "   ────┼──────"]
        out += [f"   {a} {b} │   ?" for a in (0, 1) for b in (0, 1)]
        out += ["", "  " + t("at.verite.repondre")]
        return out
    r = chiffres(rep)
    if r == juste:
        noter("verite", f"{p} {''.join(r)} (ok)")
        return [f" {fg(78)}✔ " + t("at.verite.ok", porte=t("at.mot." + p).upper()) + RESET]
    noter("verite", f"{p} {' '.join(rep)} (faux)")
    return [f" {fg(203)}✖ " + t("at.verite.faux") + RESET]


def lignes_choix(state, rep):
    cartes = choix_cartes(_graine(state))
    if not rep:
        out = [f" {fg(213)}{BOLD}🔀 " + t("at.choix.titre") + RESET, ""]
        out += [f"  {n}. " + t("at.choix." + i) for n, i, _r in cartes]
        out += ["", "  " + t("at.choix.repondre", et=t("at.mot.et"), ou=t("at.mot.ou"), non=t("at.mot.non"))]
        return out
    donne = [porte_de(x) for x in rep]
    if donne == [r_ for _n, _i, r_ in cartes]:
        noter("choix", " ".join(donne) + " (ok)")
        return [f" {fg(78)}✔ " + t("at.choix.ok") + RESET]
    faux = [str(n) for (n, _i, r_), d in zip(cartes, donne + [None] * 3) if d != r_]
    noter("choix", " ".join(rep) + " (faux)")
    return [f" {fg(203)}✖ " + t("at.choix.faux", liste=", ".join(faux)) + RESET]


def lignes_essai(state):
    a = a_(state)
    a["robot"] = dict(depart("e"), arene="e")
    a["vus"] = [[a["robot"]["x"], a["robot"]["y"]]]
    a["defi"] = {}
    _ecrire_capteur(state)
    ecrire_robot("moteur", "stop")
    noter("essai_debut", "entrainement (ok)")
    out = [f" {fg(117)}{BOLD}🧪 " + t("at.essai.titre") + RESET, ""]
    out += _couleur_grille(dessin_grille("e", a["robot"], a["vus"]))
    return out + [""] + _bloc("at.essai.texte")


def lignes_defi(state):
    a = a_(state)
    i = arene_defi(_graine(state))
    a["robot"] = dict(depart(i), arene=i)
    a["vus"] = [[a["robot"]["x"], a["robot"]["y"]]]
    a["defi"] = {"arene": i, "pas": 0, "chocs": 0, "vus": [[a["robot"]["x"], a["robot"]["y"]]]}
    _ecrire_capteur(state)
    ecrire_robot("moteur", "stop")
    noter("defi_debut", f"{i + 1} (ok)")
    D = donnees()["defi"]
    out = [f" {fg(213)}{BOLD}🏁 " + t("at.defi.titre", n=i + 1) + RESET, ""]
    out += _couleur_grille(dessin_grille(i, a["robot"], a["vus"]))
    return out + [""] + _bloc("at.defi.regles", pas=D["pas"], min=D["cases_min"])


def lignes_aide_cerveau():
    return [f" {fg(213)}{BOLD}🧠 " + t("at.aidec.titre") + RESET, ""] + _bloc("at.aidec.texte") + [""] + \
        [f"    {fg(117)}{l}{RESET}" for l in cerveau_malin().rstrip("\n").split("\n")] + [""] + _bloc("at.aidec.fin")


def _raconte(cle, emoji, couleur=215, **p):
    out = [f" {fg(couleur)}{BOLD}{emoji} " + t(f"at.{cle}.titre") + RESET, ""] + _bloc(f"at.{cle}.texte", **p)
    noter(cle, "lu (ok)")
    return out


GPIO = ["   3V3 (1) (2) 5V", " GPIO2 (3) (4) 5V", " GPIO3 (5) (6) GND", " GPIO4 (7) (8) GPIO14", "   GND (9) (10) GPIO15",
        "GPIO17 (11) (12) GPIO18", "   …    …    …"]


def lignes_gpio():
    out = _raconte("gpio", "📍", 220)
    return out[:2] + [f"   {fg(220)}{l}{RESET}" for l in GPIO] + [""] + out[2:]


def lignes_reflexe(state, rep):
    v, ms, cm = reflexe(_graine(state))
    if not rep:
        return [f" {fg(229)}{BOLD}⏱ " + t("at.reflexe.titre") + RESET, ""] + _bloc("at.reflexe.texte", v=v, ms=ms)
    if nombres(" ".join(rep))[:1] == [cm]:
        noter("reflexe", f"{cm} (ok)")
        return [f" {fg(78)}✔ " + t("at.reflexe.ok", cm=cm, v=v, ms=ms) + RESET]
    noter("reflexe", " ".join(rep) + " (faux)")
    return [f" {fg(203)}✖ " + t("at.reflexe.faux", v=v, ms=ms) + RESET]


def commande(args, sortie=None):
    """tg atelier [plan|robot|grille|pas|ou X Y|cases N|logique|verite [A B C D]|choix [m1 m2 m3]|essai|defi|aide-cerveau|
    pi|gpio|autonome|embarque|reflexe [cm]|arduino|telephone]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas(a[0] if a else "aide")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        if not dossier().is_dir():
            lignes.extend(aide() + ["", "  " + t("at.pas_ouvert")])
            return
        a_(st)
        if sous in ("plan", "regles"):
            lignes.extend(banniere() + t("at.meuble.plan", nom=st.get("name", "")).split("\n"))
        elif sous == "robot":
            lignes.extend(lignes_robot(st))
        elif sous == "grille":
            lignes.extend(lignes_grille(st))
        elif sous == "pas":
            lignes.extend(lignes_pas(st))
        elif sous == "ou":
            lignes.extend(lignes_ou(st, reste))
        elif sous == "cases":
            lignes.extend(lignes_cases(st, reste))
        elif sous == "logique":
            lignes.extend(lignes_logique())
        elif sous == "verite":
            lignes.extend(lignes_verite(st, reste))
        elif sous == "choix":
            lignes.extend(lignes_choix(st, reste))
        elif sous == "essai":
            lignes.extend(lignes_essai(st))
        elif sous == "defi":
            lignes.extend(lignes_defi(st))
        elif sous in ("aide-cerveau", "aide_cerveau"):
            lignes.extend(lignes_aide_cerveau())
        elif sous == "pi":
            lignes.extend(_raconte("pi", "🍓", 203))
        elif sous == "gpio":
            lignes.extend(lignes_gpio())
        elif sous == "autonome":
            lignes.extend(_raconte("autonome", "🔁", 78))
        elif sous == "embarque":
            lignes.extend(_raconte("embarque", "🔌", 117))
        elif sous == "reflexe":
            lignes.extend(lignes_reflexe(st, reste))
        elif sous == "arduino":
            lignes.extend(_raconte("arduino", "🧑‍🔧", 215))
        elif sous == "telephone":
            lignes.extend(_raconte("telephone", "📱", 141))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
    return 0
