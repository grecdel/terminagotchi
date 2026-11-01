"""La Tour des Ondes (phase 5, docs/programme.md § 7.11), sur PC.

    python3 pc/outils/test_ondes.py          (crée son propre HOME temporaire)

  1. la spécification pure : vecteurs communs à jour (donnees/ondes/vecteurs.json, mêmes résultats en Kotlin) ;
     λ = v / f (bc d'accord), le temps d'émission LoRa (valeurs connues de la note Semtech), les canaux Wi-Fi, la
     vallée et le plus petit SF, la règle du 1 %, le maillage (chemin le plus court, inondation, coupures) ; la tempête
     est toujours jouable (pour chaque cible, il existe trois coupures du chemin qui laissent passer le message) ;
  2. l'arbre du Carrefour : fermée tant que le Port P7 et la Salle des Machines M2 ne sont pas faits, puis ouverte et
     annoncée une fois ; meublée (plan, carnet, capteurs d'exemple) ;
  3. la traversée on0 → on10 comme un enfant (vraies commandes dans bash, doublures des outils radio ABSENTS ici :
     nmcli, iw, rfkill, bluetoothctl, meshtastic, rtl_test — qui n'émettent rien), commandes du jeu `ondes …` et
     `mesh-…` : l'onde, la longueur d'onde, le mur, les canaux, la règle, la vallée, le maillage, la tempête réussie
     (exploit « onde » et variantes réservées), W5 et W6 ; l'antenne miniature et le titre ;
  4. les indices (sudo, rfkill block, scan, « ? » recopié, mauvaise longueur, mauvais SF, la cible isolée) et la garde
     (les noms des voisins, l'émission) ;
  5. la vue déployée : l'antenne de `nmcli radio`, `rtl_fm`, `mesh-envoie` ;
  6. vie privée et sécurité : les noms et adresses des réseaux des voisins (affichés par la doublure de nmcli) ne sont
     JAMAIS dans le carnet ni dans la sauvegarde ; aucun message tapé n'est gardé ; rien hors du terrain ; aucune
     commande qui change la radio ou qui émet n'est lancée par le jeu ; 14 langues.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_ond_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, ondes as O, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
SECRET_SSID, SECRET_MAC = "Box-Famille-Dupont-42", "a4:2b:b0:12:34:56"
JOURNAL = DOUBLURES / "appels.txt"          # chaque appel aux doublures radio (le jeu n'a jamais le droit d'émettre)


def doublure(nom, corps):
    f = DOUBLURES / nom
    f.write_text(f"#!{sys.executable}\nimport sys\nopen({str(JOURNAL)!r}, 'a').write({nom!r} + ' ' + ' '.join(sys.argv[1:]) + '\\n')\n"
                 "a = sys.argv[1:]\n" + corps)
    f.chmod(0o755)


# des doublures des outils radio : des données FICTIVES, jamais une vraie radio
doublure("nmcli", (
    "if 'radio' in a or 'r' in a:\n    print('WIFI-HW  WIFI     WWAN-HW  WWAN\\nenabled  enabled  missing  enabled'); sys.exit(0)\n"
    "fr = [2412, 2437, 2437, 2462, 5180, 5500]\n"
    "if '-t' in a:\n    [print(f'{x} MHz') for x in fr]; sys.exit(0)\n"
    "if '-f' in a:\n    print('CHAN  FREQ      SIGNAL  BARS')\n    [print(f'{(x - 2407) // 5 if x < 3000 else (x - 5000) // 5:<5} {x} MHz  70      ▂▄▆_') for x in fr]; sys.exit(0)\n"
    f"print('IN-USE  BSSID              SSID                    MODE   CHAN  RATE        SIGNAL')\n"
    f"print('        {SECRET_MAC}  {SECRET_SSID}   Infra  6     130 Mbit/s  70')\n"))
doublure("iw", "print('phy#0\\n\\tInterface wlan0\\n\\t\\ttype managed\\n\\t\\tchannel 6 (2437 MHz), width: 20 MHz\\n\\t\\ttxpower 22.00 dBm')\n")
doublure("rfkill", "print('0: phy0: Wireless LAN\\n\\tSoft blocked: no\\n\\tHard blocked: no')\n")
doublure("bluetoothctl", "print('\\tPowered: yes\\n\\tDiscoverable: no')\n")
doublure("meshtastic", "print('Connected to radio (fictif)') if '--info' in a or '--nodes' in a else print('No Serial Meshtastic device detected (fictif)'); sys.exit(0 if '--info' in a or '--nodes' in a else 1)\n")
doublure("rtl_test", "print('No supported devices found.'); sys.exit(1)\n")
for nom in ("ondes", "mesh-envoie", "mesh-coupe", "mesh-route"):
    pre = "" if nom == "ondes" else f"'{nom}', "
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"from tg import ondes; ondes.commande([{pre}] + sys.argv[1:])\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (test) refusé' >&2\nexit 1\n")
(DOUBLURES / "sudo").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def bash(cmd, cwd=None):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd or terminal[0], capture_output=True, text=True, errors="replace",
                       timeout=60, env=ENV)
    return r.stdout


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=120, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
        lignes = lignes[:-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)
    return st, "\n".join(lignes) + r.stderr


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == T or T in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


def tempete(cible):
    """Trois coupures du chemin (chacune sur le chemin du moment) qui laissent passer le message, ou None."""
    def chercher(coupes):
        if len(coupes) == 3:
            return list(coupes)
        r = O.route("camp", cible, coupes)
        for x in (r or [])[1:-1]:
            if O.route("camp", cible, coupes + [x]):
                s = chercher(coupes + [x])
                if s:
                    return s
        return None
    return chercher([])


langue.definir("fr")
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_ondes.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/ondes/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
verifier(abs(O.longueur_onde(2_400_000_000) - 0.125) < 1e-12 and bash('echo "300000000 / 2400000000" | bc -l').strip() == ".12500000000000000000",
         "λ = v / f : 0,125 m pour 2,4 GHz (bc d'accord)")
verifier(O.longueur_ok("34.6", 868_000_000) and O.longueur_ok("0,35 m", 868_000_000) and O.longueur_ok("346 mm", 868_000_000)
         and not O.longueur_ok("12.5", 868_000_000), "la longueur d'onde de LoRa : 34,6 cm, 0,35 m ou 346 mm (pas 12,5)")
verifier([O.temps_emission_us(sf) for sf in (7, 12)] == [41216, 991232] and O.temps_emission_us(11) == 577536,
         "temps d'émission de 10 octets : SF7 41,2 ms, SF11 577,5 ms, SF12 991,2 ms (note Semtech AN1200.13)")
verifier(O.duree_symbole_us(12) == 32768 and O.budget_us() == 36_000_000 and O.messages_heure(11) == 62,
         "un symbole SF12 = 32 768 µs ; 1 % d'une heure = 36 s ; 62 messages SF11 par heure")
verifier([O.canal(f) for f in (2412, 2437, 2472, 2484, 5180, 5500, 5955, 2400)] == [1, 6, 13, 14, 36, 100, 1, None],
         "les canaux Wi-Fi (2,4 / 5 / 6 GHz)")
verifier([O.sf_min(d) for d in (3500, 5000, 7000, 9500, 20000)] == [9, 10, 11, 12, None], "le plus petit SF qui traverse chaque vallée")
verifier(O.traverse_le_mieux() == "lora" and O.restant_pc(3) == (71, 50) and O.restant_pc(10) == (32, 10),
         "le mur : LoRa passe le mieux ; −3 dB = moitié de la puissance, −10 dB = un dixième")
verifier(O.route("camp", "feu") == ["camp", "racine", "roche", "feu"] and O.route("camp", "feu", ["roche"]) is not None
         and O.route("camp", "feu", ["racine"]) is None, "le maillage : un chemin, un détour, et le camp isolé sans la racine")
verifier(all(tempete(c) for c in O.donnees()["maillage"]["cibles"]), "la tempête est jouable pour chaque cible "
         + str({c: tempete(c) for c in O.donnees()["maillage"]["cibles"]}))
gr = "7:42"
verifier(sorted(O.regle_reponse(gr)) == list("ABCDEF") and len(O.libre_cartes(gr)) == 6 and len(O.choix_cartes(gr)) == 4,
         "la règle, les bandes et les choix : mélangés pour chaque partie")
verifier(O.antennes_de("nmcli radio") == [("wifi", "lit")] and O.antennes_de("sudo rfkill block wifi") == [] and
         O.antennes_de("rfkill block wifi") == [("toutes", "change")] and O.antennes_de("bluetoothctl scan on") == [("bluetooth", "cherche")]
         and O.antennes_de("nmcli dev wifi list") == [("wifi", "cherche")] and O.antennes_de("nmcli -f CHAN dev wifi list --rescan no") == [("wifi", "lit")]
         and O.antennes_de("meshtastic --sendtext hi") == [("lora", "emet")] and O.antennes_de("rtl_fm -f 100M") == [("sdr", "ecoute")],
         "les antennes : lire, chercher, changer, émettre, écouter")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "ondes"), "fermée au début")


def ouvrir(s, avec=("port7", "sm3")):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    for lid in avec:
        if lid not in h["faits"]:
            h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    h["chap"] = "bibliotheque"
    h.setdefault("mondes_annonces", []).extend(["port", "crypte", "machinerie"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, avec=("port7",)))
st = core.load()
verifier(not histoire.ouvert(st, "ondes") and any("Des 0 et des 1" in m for m in O.manque(st)),
         f"le Port P7 sans la Salle des Machines M2 : toujours fermée (il manque {O.manque(st)})")
core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "ondes"), f"P7 et M2 faits : la Tour s'ouvre (il manquait {O.manque(core.load())})")
verifier("ondes" in st["histoire"].get("mondes_annonces", []), "annoncée une fois")
D = T / "ondes"
verifier((D / "plan_de_la_tour.txt").is_file() and (D / "capteurs_exemple.json").is_file() and (D / O.CARNET).is_file(),
         "la Tour est meublée (plan, carnet, capteurs d'exemple)")

print("3. La traversée de la Tour, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/ondes")
verifier(lecon(st) == ("on0", 1), f"entrer dans la Tour choisit le monde : {lecon(st)}")
gr = O._graine(st)
cible = O.defi_cible(gr)
sol = tempete(cible)
sorties = {}
PARCOURS = [
    "ls", "cat plan_de_la_tour.txt",
    "ondes onde", "ondes onde lora", 'echo "300000000 / 2400000000" | bc -l', "ondes longueur 12.5", "ondes longueur 34.6",
    "ondes mur", "ondes traverse wifi5", "ondes traverse lora",
    "iw dev", "nmcli dev wifi list", "nmcli -f CHAN,FREQ,SIGNAL,BARS dev wifi list --rescan no", "ondes reseaux 40", "ondes reseaux 6",
    "ondes canaux", "ondes voisins",
    "nmcli radio", "rfkill block wifi", "rfkill list", "timeout 5 bluetoothctl show | grep -E 'Powered|Discoverable'", "ondes radios",
    "ondes spectre", "ondes regle", "ondes regle A B C D E F", lambda: "ondes regle " + " ".join(O.regle_reponse(gr)),
    "ondes libre", lambda: "ondes libre " + " ".join(r_ for _n, _i, r_ in O.libre_cartes(gr)),
    "ondes lora", 'echo "2^12 / 125000" | bc -l', "ondes temps", "ondes vallee", "ondes vallee 7", "ondes vallee 12",
    lambda: f"ondes vallee {O.sf_min(O.vallee_m(gr))}", 'echo "3600 * 1 / 100" | bc',
    lambda: f"ondes messages {O.messages_heure(O.sf_min(O.vallee_m(gr)))}",
    "ondes passerelle", "ondes maillage", "ondes choix", lambda: "ondes choix " + " ".join(r_ for _n, _i, r_ in O.choix_cartes(gr)),
    "mesh-route", 'mesh-envoie feu "bonjour"', "mesh-coupe roche", 'mesh-envoie feu "bonjour"', "mesh-route feu", "mesh-coupe -r",
    "ondes defi", "mesh-coupe ?", "mesh-coupe racine", "mesh-coupe -r", "ondes defi",
    lambda: f"mesh-coupe {sol[0]}", lambda: f"mesh-coupe {sol[1]}", lambda: f"mesh-coupe {sol[2]}", lambda: f'mesh-envoie {cible} "SOS"',
    "ondes adulte", "command -v meshtastic", "meshtastic --info", "meshtastic --nodes", 'meshtastic --sendtext "bonjour"', "ondes noeud",
    "ondes ecoute", "command -v rtl_test rtl_433 dump1090", "timeout 10 rtl_test -t", "ondes avions", "cat capteurs_exemple.json",
    "grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json", "ondes anonyme",
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    st, s = tape(c)
    sorties[c] = s
    vus.append((avant, c, lecon(st)))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:100]!r}")
    if histoire.fini(st, "ondes"):
        break
if not histoire.fini(st, "ondes"):
    for a, c, b in vus[-8:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "ondes"), f"la Tour est traversée jusqu'au bout (on0 → on10) {lecon(st)}")
verifier(sorties.get('echo "300000000 / 2400000000" | bc -l', "").strip() == ".12500000000000000000", "bc : .125")
verifier("✖" in sorties.get("ondes longueur 12.5", "") and "✔" in sorties.get("ondes longueur 34.6", ""), "la longueur d'onde : 12,5 refusé, 34,6 accepté")
verifier("✔" in sorties.get("ondes reseaux 6", "") and "✖" in sorties.get("ondes reseaux 40", ""), "le nombre de réseaux : 6 (comptés par le jeu, anonymes)")
verifier("✖" in sorties.get("ondes vallee 7", "") and "✖" in sorties.get("ondes vallee 12", "") or O.sf_min(O.vallee_m(gr)) == 12,
         "la vallée : trop court refusé, trop lent refusé")
o = ANSI.sub("", sorties.get('mesh-envoie feu "bonjour"', ""))
verifier("feu" in o and "✔" in o, "mesh-envoie : le message arrive au feu")
verifier(O.dans_carnet("defi") and O.compte_carnet("defi_coupe") >= 3, "la tempête : trois nœuds du chemin coupés, le message passe")
r_ = recompenses.r_(st)
verifier("ondes.onde" in r_["exploits"], "l'exploit « onde » (le message passe malgré 3 nœuds coupés)")
verifier(not recompenses.reservee(st, {"id": "zapiot"}, "orage") and recompenses.reservee({}, {"id": "zapiot"}, "orage")
         and not recompenses.reservee({}, {"id": "plumange"}, "neon"), "zapiot:orage n'apparaît qu'après l'exploit de la Tour")
verifier("antenne_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "maitre_des_ondes",
         "récompenses : l'antenne miniature et le titre de Maître des Ondes")
verifier('"temperature_C": 7.4' in sorties.get("grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json", "") and
         '"id"' not in sorties.get("grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json", ""), "anonymiser : les températures sans les identifiants")

print("4. Les indices et la garde")
pas = {s_["cmd"]: s_ for l_ in O.LECONS.values() for s_ in l_["steps"]}
verifier(O.indice(pas["ondes longueur ?"], [("sudo iw dev wlan0 scan", None)]) == langue.t("on.indice.sudo"), "sudo : jamais ici")
verifier(O.indice(pas["ondes longueur ?"], [("rfkill block wifi", None)]) == langue.t("on.indice.change"), "rfkill block : on ne change pas la radio")
verifier(O.indice(pas["ondes longueur ?"], [("bluetoothctl scan on", None)]) == langue.t("on.indice.cherche"), "scan on : un balayage actif")
verifier(O.indice(pas["ondes longueur ?"], [("ondes longueur ?", None)]) == langue.t("on.indice.trou"), "« ? » recopié : un trou à remplir")
O.noter("longueur", "12 (faux)")
verifier(O.indice(pas["ondes longueur ?"], [("ondes longueur 12", None)]) == langue.t("on.indice.longueur"), "mauvaise longueur d'onde")
O.noter("vallee", "SF7 (court)")
verifier(O.indice(pas["ondes vallee ?"], [("ondes vallee 7", None)]) == langue.t("on.indice.vallee"), "mauvais SF")
O.noter("defi_coupe", "racine (isole)")
verifier(O.indice(pas["mesh-coupe ?"], [("mesh-coupe racine", None)]) == langue.t("on.indice.isole"), "la cible isolée : rallumer et recommencer")
s0 = core.load()
s0.setdefault("ondes", {})["faits"] = []
verifier(O.surveiller(s0, ["nmcli dev wifi list"]) and not O.surveiller(s0, ["nmcli dev wifi list"]),
         "une liste Wi-Fi avec les noms : la créature rappelle qu'ils sont aux voisins (une fois)")
verifier(O.surveiller(s0, ["meshtastic --sendtext salut"]), "meshtastic --sendtext : la règle de l'émission")

print("5. La vue déployée : l'antenne")
x = deploie.antennes("nmcli radio && rtl_fm -f 100M | head -c 10")
verifier([(y["radio"], y["sens"]) for y in x] == [("wifi", "lit"), ("sdr", "ecoute")], f"nmcli radio lit, rtl_fm écoute ({x})")
txt = ANSI.sub("", "\n".join(deploie.ecran("mesh-envoie feu bonjour", deploie.blocs("mesh-envoie feu bonjour"), 1, None, 0.5, 100)))
verifier("📡" in txt and "LoRa" in txt and "•" in txt, "la vue déployée dessine l'antenne et son onde")
out = io.StringIO()
O.commande(["onde", "fm"], out)
verifier("3 m" in ANSI.sub("", out.getvalue()), "ondes onde fm : 3 m de longueur d'onde")
from tg import compagnon  # noqa: E402
verifier(any("mesh-envoie='tg ondes mesh-envoie'" in b or "function mesh-envoie" in b for b in compagnon._blocs().values()),
         "tg installer pose les alias ondes et mesh-…")

print("6. Vie privée, sécurité et langues")
sauve = json.dumps(core.load(), ensure_ascii=False)
carnet = O.carnet()
verifier(SECRET_SSID not in carnet and SECRET_MAC not in carnet and SECRET_SSID not in sauve and SECRET_MAC not in sauve,
         "le nom et l'adresse du réseau du voisin (affichés par nmcli) ne sont ni dans le carnet ni dans la sauvegarde")
verifier("bonjour" not in carnet and "SOS" not in carnet, "les messages tapés ne sont jamais gardés")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
jeu = [l for l in appels.splitlines() if l.startswith("nmcli -t -f FREQ")]
verifier(jeu and all("--rescan no" in l for l in jeu), f"le jeu ne lit que la colonne FREQ, sans balayage ({len(jeu)} appel(s))")
verifier(not re.search(r"(block|connect|pair|scan on|--sendtext|--set\b|off\b)", "\n".join(l for l in appels.splitlines() if l.startswith("nmcli -t")))
         and appels.count("--sendtext") == 1, "le jeu ne change aucune radio et n'émet jamais (le seul --sendtext est celui de l'enfant)")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in O.LECONS for s in O.LECONS[lid]["steps"])
verifier(not re.search(r"https?://", cmds) and "sudo" not in cmds and "block" not in cmds and "pip install" not in cmds
         and not re.search(r"\bscan\b", cmds), "aucune adresse réseau, aucun sudo, aucun rfkill block, aucun pip install, aucun scan dans les leçons")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k_ for lid in O.LECONS for s in O.LECONS[lid]["steps"] for k_ in (s["dit"], s["bravo"]) if isinstance(k_, str) and k_ not in dct]
    m += [k_ for k_ in ("hist.ondes.titre", "hist.ondes.debut", "hist.ondes.fin", "on.ouvert.dit", "dep.antenne") if k_ not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes de la Tour existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
