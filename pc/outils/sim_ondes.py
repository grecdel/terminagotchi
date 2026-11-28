"""Trois enfants traversent la Tour des Ondes (phase 5, on0 → on10), dans un VRAI shell resté ouvert —
docs/simulations/rapport_ondes.md.

    python3 pc/outils/sim_ondes.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/sim_ondes.py lea        (un seul : lea, ines ou hugo)

Comme sim_machines.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. La Tour est ouverte d'avance (le Port P7 et la Salle des Rouages M2 faits). Les outils radio
(nmcli, iw, rfkill, bluetoothctl, meshtastic, rtl_test) sont des DOUBLURES qui affichent un quartier FICTIF, avec le
nom et l'adresse d'un réseau de voisin inventé (pour vérifier que le jeu ne les garde jamais) ; rien n'émet.
  - Léa, 7 ans : se trompe d'abord (une majuscule, la longueur du Wi-Fi au lieu de LoRa, sudo, rfkill block, scan on,
    la règle dans l'ordre A B C D E F, la vallée en SF7 puis en SF12, la tempête en coupant la racine, le « ? »
    recopié, grep sans -o) ; puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`ondes onde 868M`, `bc` avec scale, `iwconfig`, `nmcli -t`, `rfkill`, `printf | bc`,
    `ondes vallee SF10`, `which`, `type`, `less`, `grep -oE`…).
Pour les trous : la longueur d'onde est CALCULÉE avec bc ; l'onde qui traverse est lue dans `ondes mur` ; le nombre de
réseaux est compté dans la liste ; la règle et les bandes sont lues sur la règle du spectre ; le SF dans `ondes vallee` ;
les messages divisés à partir du temps affiché ; la tempête jouée en lisant le chemin affiché après chaque coupure.
Vérifie : la Tour finie ; l'exploit « onde » ; aucune étape validée par une commande qui a échoué ; chaque faute de Léa
reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain ; le nom et l'adresse du réseau
du voisin ne sont gardés nulle part ; aucun message tapé n'est gardé. Code de sortie 1 en cas d'échec.
"""
import builtins
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nTour des Ondes : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
PRENOM = {"lea": "Léa", "ines": "Inès", "hugo": "Hugo"}[QUI]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_ond_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, langue, ondes as O  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
SECRET_SSID, SECRET_MAC = "Box-Famille-Martin-7", "c8:3a:35:aa:bb:cc"


def doublure(nom, corps):
    f = DOUBLURES / nom
    f.write_text(f"#!{sys.executable}\nimport sys\na = sys.argv[1:]\n" + corps)
    f.chmod(0o755)


# les outils radio : des DOUBLURES (un quartier fictif) ; elles n'émettent rien et ne changent rien
doublure("nmcli", (
    "if 'radio' in a or a[-1:] == ['r']:\n    print('WIFI-HW  WIFI     WWAN-HW  WWAN\\nenabled  enabled  missing  enabled'); sys.exit(0)\n"
    "fr = [2412, 2437, 2437, 2462, 2412, 5180, 5500]\n"
    "if '-t' in a:\n    [print(f'{x} MHz') for x in fr]; sys.exit(0)\n"
    "if '-f' in a:\n    print('CHAN  FREQ      SIGNAL  BARS')\n    [print(f'{(x - 2407) // 5 if x < 3000 else (x - 5000) // 5:<5} {x} MHz  64      ▂▄▆_') for x in fr]; sys.exit(0)\n"
    "print('IN-USE  BSSID              SSID                  MODE   CHAN  SIGNAL')\n"
    f"print('        {SECRET_MAC}  {SECRET_SSID}   Infra  6     64')\n"))
doublure("iw", "print('phy#0\\n\\tInterface wlan0\\n\\t\\ttype managed\\n\\t\\tchannel 11 (2462 MHz), width: 20 MHz\\n\\t\\ttxpower 20.00 dBm')\n")
doublure("iwconfig", "print('wlan0     IEEE 802.11  ESSID:off/any\\n          Mode:Managed  Frequency:2.462 GHz')\n")
doublure("rfkill", "print('0: phy0: Wireless LAN\\n\\tSoft blocked: no\\n\\tHard blocked: no\\n1: hci0: Bluetooth\\n\\tSoft blocked: no\\n\\tHard blocked: no')\n")
doublure("bluetoothctl", "print('Discovery started (fictif)') if 'scan' in a else print('\\tPowered: yes\\n\\tDiscoverable: no')\n")
doublure("meshtastic", "print('No Serial Meshtastic device detected (fictif)'); sys.exit(1)\n")
doublure("rtl_test", "print('No supported devices found.'); sys.exit(1)\n")
for nom in ("ondes", "mesh-envoie", "mesh-coupe", "mesh-route"):     # les alias posés par tg installer
    pre = "" if nom == "ondes" else f"'{nom}', "
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"from tg import ondes; ondes.commande([{pre}] + sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (simulation) refusé' >&2\nexit 1\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["faits"] += ["port7", "sm3"]
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "crypte", "machinerie"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == core.TERRAIN or core.TERRAIN in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


core.modifier(ouvrir)
core.TERRAIN.mkdir(exist_ok=True)
AVANT = fichiers_hors_terrain()
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8"))
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
INV = {v: k for k, v in HOMO.items()}
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + f"[{QUI}] " + m)


def propre(x):
    x = langue.sans_marques(ANSI.sub("", x))
    return "".join(INV.get(c, c) for c in x).replace(NBSP, " ")


etat = {"sortie": "", "code": 0, "terminal": []}
journal = []          # (leçon, étape, commande, code, lu) : la partie entière, pour le rapport
memoire = {}


def tape(cmd):
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=120)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    memoire.pop(cmd, None)                 # la plus récente en dernier
    memoire[cmd] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip().strip("`") for p in parts if p]


def lu(prefixe):
    """La dernière sortie lue d'une commande qui commence par prefixe."""
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def dernier_chemin():
    """Le dernier chemin affiché (« ⛺ camp ─✉→ 🌳 racine ─✉→ … ») : ce que l'enfant lit après une coupure."""
    for k, v in list(memoire.items())[::-1]:
        if k.startswith(("mesh-", "ondes defi", "ondes mesh")):
            l = [x for x in v.splitlines() if "─✉→" in x]
            if l:
                return re.findall(r"([a-z]+)(?=\s*(?:─|$))", l[-1])
    return []


NOMS_TECH = {"radio FM": "fm", "LoRa": "lora", "GPS": "gps", "4G": "quatreg", "Bluetooth": "bluetooth", "Wi-Fi 2,4 GHz": "wifi24",
             "5G": "cinqg", "Wi-Fi 5 GHz": "wifi5", "Wi-Fi 6 GHz": "wifi6"}


def spectre_lu(st):
    """La règle du spectre lue à l'écran : {nom : (colonne du ▲, libre ?)}."""
    s = lu("ondes spectre")
    if not s:
        st = tape("ondes spectre")
        s = memoire["ondes spectre"]
    out = {}
    for l in s.splitlines():
        m = re.match(r"^(\s*)▲ (.+?) \(.*\) ([✓✗])$", l)
        if m:
            out[m.group(2)] = (len(m.group(1)), m.group(3) == "✓")
    return st, out


tentatives_defi = [0]
isolants = set()


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "ondes longueur ?":
        st = tape('echo "300000000 / 868000000" | bc -l')
        x = float(propre(etat["sortie"]).strip() or "0")
        return st, f"ondes longueur {x * 100:.1f}"
    if cmd == "ondes traverse ?":
        s = lu("ondes mur") or ""
        pertes = re.findall(r"^\s*(LoRa|Wi-Fi 2,4 GHz|Wi-Fi 5 GHz)\s+−(\d+) dB", s, re.M)
        meilleur = min(pertes, key=lambda p: int(p[1]))[0] if pertes else "LoRa"
        return st, "ondes traverse " + {"LoRa": "lora", "Wi-Fi 2,4 GHz": "wifi24", "Wi-Fi 5 GHz": "wifi5"}[meilleur]
    if cmd == "ondes reseaux ?":
        s = lu("nmcli")
        lignes = [l for l in s.splitlines() if re.search(r"\d+ MHz", l)]
        return st, f"ondes reseaux {len(lignes)}"
    if cmd == "ondes regle ? ? ? ? ? ?":
        st, sp = spectre_lu(st)
        if "ondes regle" not in memoire:
            st = tape("ondes regle")
        cartes = re.findall(r"^\s+([A-F])\s+(.+?) — ", memoire["ondes regle"], re.M)
        return st, "ondes regle " + " ".join(l for l, _n in sorted(cartes, key=lambda c: sp.get(c[1], (99, 0))[0]))
    if cmd == "ondes libre ? ? ? ? ? ?":
        st, sp = spectre_lu(st)
        if "ondes libre" not in memoire:
            st = tape("ondes libre")
        usages = re.findall(r"^\s+\d\. (.+?) — ", memoire["ondes libre"], re.M)
        return st, "ondes libre " + " ".join("l" if sp.get(u, (0, False))[1] else "r" for u in usages)
    if cmd == "ondes vallee ?":
        if "ondes vallee" not in memoire:
            st = tape("ondes vallee")
        s = memoire["ondes vallee"]
        d = float(re.search(r"fait ([\d.]+) km", s).group(1))
        sf = next(int(n) for n, p in re.findall(r"SF(\d+)\s+portée ([\d.]+) km", s) if float(p) >= d)
        return st, f"ondes vallee {'SF' if QUI == 'hugo' else ''}{sf}"
    if cmd == "ondes messages ?":
        st = tape("ondes messages")
        m = re.search(r"dure ([\d.]+) ms", propre(etat["sortie"]))
        msg = float(m.group(1)) if m else 1000.0
        st = tape(f'echo "36000 / {msg}" | bc')
        return st, f"ondes messages {propre(etat['sortie']).strip() or int(36000 // msg)}"
    if cmd == "ondes choix ? ? ? ?":
        if "ondes choix" not in memoire:
            st = tape("ondes choix")
        sit = re.findall(r"^\s+\d\. (.*)$", memoire["ondes choix"], re.M)
        return st, "ondes choix " + " ".join("p" if re.search(r"(Internet|mairie|service)", x) and "coupé" not in x else "m" for x in sit)
    if cmd == "mesh-coupe ?":
        ch = dernier_chemin()
        milieu = ch[1:-1]
        if not milieu:
            return st, "mesh-coupe racine"
        if QUI == "lea" and tentatives_defi[0] == 0 and "racine" in milieu and "défi:racine" not in memoire:
            memoire["défi:racine"] = "1"
            return st, "mesh-coupe racine"
        # l'enfant évite le nœud d'à côté du camp (une leçon de la tempête : tout dépend de lui) et les nœuds qui ont
        # isolé la cible aux essais d'avant ; il coupe le plus loin possible sur le chemin
        bons = [x for x in milieu if x != "racine" and x not in isolants] or milieu
        return st, f"mesh-coupe {bons[-1] if tentatives_defi[0] % 2 == 0 else bons[0]}"
    if cmd == 'mesh-envoie ? "SOS"':
        m = re.search(r"Ta cible : (\w+)", lu("ondes defi"))
        return st, f'mesh-envoie {m.group(1) if m else "feu"} "SOS"'
    return st, cmd


def faute(cmd, st):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    fautes = {"ondes onde": "Ondes onde", "ondes longueur ?": "ondes longueur 12.5", "ondes traverse ?": "ondes traverse wifi5",
              "nmcli radio": "sudo nmcli radio", "rfkill list": "rfkill block wifi",
              "timeout 5 bluetoothctl show | grep -E 'Powered|Discoverable'": "bluetoothctl scan on",
              "ondes regle ? ? ? ? ? ?": "ondes regle A B C D E F", "ondes libre ? ? ? ? ? ?": "ondes libre l l l l l l",
              "ondes vallee ?": "ondes vallee 7", "ondes messages ?": "ondes messages 36", "ondes choix ? ? ? ?": "ondes choix p p p p",
              'mesh-envoie feu "bonjour"': "mesh-envoie fue bonjour", "mesh-coupe roche": "mesh-coupe camp",
              'mesh-envoie ? "SOS"': 'mesh-envoie ? "SOS"', "cat capteurs_exemple.json": "cat capteurs.json",
              "grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json": "grep temperature capteurs_exemple.json"}
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^ondes onde lora$", "ondes onde 868M"), (r'^echo "300000000 / 2400000000" \| bc -l$', 'echo "scale=3; 300000000/2400000000" | bc'),
        (r"^iw dev$", "iwconfig"), (r"^nmcli -f CHAN", "nmcli -t -f FREQ dev wifi list --rescan no"), (r"^nmcli radio$", "nmcli r"),
        (r"^rfkill list$", "rfkill"), (r"^timeout 5 bluetoothctl", "bluetoothctl show"),
        (r'^echo "2\^12 / 125000" \| bc -l$', "printf '2^12 / 125000\\n' | bc -l"), (r'^echo "3600 \* 1 / 100" \| bc$', 'echo "3600 / 100" | bc'),
        (r"^mesh-route$", "ondes mesh-route"), (r"^mesh-route feu$", "mesh-route ombre"), (r"^ondes mur$", "ondes mur beton 2"),
        (r"^command -v meshtastic$", "which meshtastic"), (r"^command -v rtl_test", "type rtl_test"),
        (r"^timeout 10 rtl_test -t$", "rtl_test -t"), (r"^cat capteurs_exemple\.json$", "less capteurs_exemple.json"),
        (r"^grep -o", "grep -oE '\"temperature_C\": [0-9.-]+' capteurs_exemple.json"), (r"^ondes passerelle$", "ondes passerelles"),
        (r"^ondes noeud$", "ondes nœud"), (r"^ondes ecoute$", "ondes écoute"), (r"^ondes avions$", "ondes avion"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "ondes"), "la Tour devrait être ouverte (Port P7 et Machines M2 faits)"
st = tape("cd ~/terrain_terminagotchi/ondes")
for _ in range(500):
    if histoire.fini(st, "ondes"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("on"):
        st = tape("cd ~/terrain_terminagotchi/ondes")
        continue
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        st = tape(idees[0])
        continue
    step = les["steps"][st["step"]]
    avant = (les["id"], st["step"])
    a_taper = montree(st, step)
    derniere = a_taper[-1]
    premiere_fois = avant not in tentes
    tentes.add(avant)
    essais = []
    if premiere_fois:
        if QUI == "lea" and faute(derniere, st):
            essais.append(faute(derniere, st))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.split():
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "⚠" not in propre(etat["sortie"]):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    st, derniere = resoudre(derniere, st)
    st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
        fausses.append((avant, derniere, etat["code"]))
    sortie = propre(etat["sortie"])
    if apres == avant and derniere.startswith(("mesh-coupe", "mesh-envoie")) and ("isolé" in sortie or "isolée" in " ".join(etat["terminal"])
                                                                                or "Rallume" in sortie):
        tentatives_defi[0] += 1                                   # la cible est isolée : l'enfant lit, rallume et recommence
        if derniere.startswith("mesh-coupe "):
            isolants.add(derniere.split()[-1])
        st = tape("mesh-coupe -r")
        st = tape("ondes defi")
    elif apres == avant and derniere.startswith(("ondes regle ", "ondes libre ", "ondes choix ")):
        bons = re.findall(r"✔\s+(\d)\.", sortie)
        verifier(True, f"{derniere} : {len(bons)} juste(s) affichés, l'enfant corrige")

verifier(histoire.fini(st, "ondes"), f"la Tour traversée, on0 → on10 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("ondes.onde" in ex, f"l'exploit « onde » : le message passe malgré 3 nœuds coupés ({tentatives_defi[0]} tempête(s) recommencée(s))")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
sauve = json.dumps(core.load(), ensure_ascii=False)
carnet = O.carnet()
verifier(SECRET_SSID not in carnet + sauve and SECRET_MAC not in carnet + sauve,
         "le nom et l'adresse du réseau du voisin ne sont gardés ni dans le carnet ni dans la sauvegarde")
verifier("bonjour" not in carnet and "SOS" not in carnet, "aucun message tapé n'est gardé")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    lus = " ".join(lu_ for _l, _s, c, _code, lu_ in journal if c.startswith(("sudo", "rfkill block", "bluetoothctl scan")))
    verifier("sudo" in lus.lower() and "change" in lus.lower() and "balayage" in lus.lower(),
             f"sudo, rfkill block, scan on : la créature explique la règle ({lus[:120]})")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 15, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
