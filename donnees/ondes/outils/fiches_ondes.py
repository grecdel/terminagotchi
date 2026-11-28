"""Les fiches notions de la Tour des Ondes (charte de rigueur, docs/programme.md § 7.1) et sa place dans
donnees/programme.json : le monde (prérequis = le tronc du Port + les paliers P7 du Port et M2 de la Salle des
Machines, paliers, ponts, attirance, exploit « onde », variantes réservées du type Ciel), les quatre Ponts des Nombres
de la radio (fréquence, puissances de 10, longueur d'onde, temps d'émission), les maths des étapes et les étapes
rejouées dans bash.

    python3 donnees/ondes/outils/fiches_ondes.py      écrit donnees/programme.json et ses deux copies (et ondes.json)

Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, dans un terrain jetable. Ce qui
dépend de la machine ou du quartier (les réseaux Wi-Fi des voisins, les radios présentes) n'est JAMAIS écrit tel quel :
le cas vérifie une FORME (motif) ou un calcul. Les cas qui demandent du matériel (une carte LoRa, une clé de radio
logicielle) ne se rejouent pas (« rejeu » : « materiel ») ; ceux du téléphone non plus (« telephone »). Rien n'émet,
rien ne sort du terrain, jamais de sudo.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"on.f.{nid}.enfant", "grands": f"on.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"on.f.{nid}.limite", "idees_fausses": [f"on.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


FICHES = dict([
    fiche("ondes", r"(ondes\s+(onde|longueur|murs?|traverse)\b|^echo\s+\"?300000000\b.*\|\s*bc\b|^echo\s+\$\(\(300000000\b)", [
        {"cmd": "echo \"300000000 / 2400000000\" | bc -l", "sortie": ".12500000000000000000", "outil": "bc"},
        {"cmd": "echo $((300000000 * 100 / 868000000))", "sortie": "34"},
        {"cmd": "awk 'BEGIN { printf \"%.1f\\n\", 300000000 / 868000000 * 100 }'", "sortie": "34.6"},
        {"cmd": "awk 'BEGIN { printf \"%.0f %.0f\\n\", 100 * 10^(-6/20), 100 * 10^(-6/10) }'", "sortie": "50 25"}],
        ["BIPM, Le Système international d'unités, 9e édition (2019) : hertz, mètre, vitesse de la lumière (299 792 458 m/s)",
         "UIT-R P.2040 : effets des matériaux de construction sur la propagation (affaiblissement selon la fréquence)",
         "UIT-R P.525 : calcul de l'affaiblissement en espace libre",
         "man 1 bc (GNU bc) : https://www.gnu.org/software/bc/manual/html_mono/bc.html"]),
    fiche("wifi_machine", r"(^iw\s+dev\b|^iwconfig\b|^nmcli\b.*\bwifi\b|ondes\s+(reseaux|canaux|voisins)\b)", [
        {"cmd": "echo $(( (2437 - 2407) / 5 ))", "sortie": "6"},
        {"cmd": "echo $(( (5180 - 5000) / 5 ))", "sortie": "36"},
        {"cmd": "nmcli -t -f FREQ dev wifi list --rescan no | grep -cvE '^[0-9]+ MHz$'", "sortie": "0", "code": "non0",
         "outil": "nmcli", "si": "nmcli -t -f FREQ dev wifi list --rescan no | grep -q MHz"},
        {"cmd": "iw dev", "rejeu": "materiel", "motif": r"^phy#\d+"}],
        ["man 1 nmcli (NetworkManager) : -f, --rescan no : https://networkmanager.dev/docs/api/latest/nmcli.html",
         "man 8 iw : https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html",
         "IEEE 802.11-2020, annexe E : canaux et fréquences (2,4 GHz, 5 GHz, 6 GHz)",
         "CNIL, Wi-Fi et données personnelles (adresses MAC, noms de réseaux) : https://www.cnil.fr/"]),
    fiche("radios", r"(^nmcli\s+(-\w+\s+)*r(adio)?\b|^rfkill\b|bluetoothctl\b|ondes\s+radios?\b)", [
        {"cmd": "test -d /sys/class/rfkill && echo oui || echo non", "motif": r"^(oui|non)$"},
        {"cmd": "rfkill --version", "motif": r"^rfkill from util-linux", "outil": "rfkill"},
        {"cmd": "nmcli radio", "rejeu": "materiel", "motif": r"^WIFI-HW"}],
        ["Documentation du noyau Linux, rfkill : https://docs.kernel.org/driver-api/rfkill.html",
         "man 8 rfkill (util-linux) ; man 1 nmcli (nmcli radio) ; bluetoothctl (BlueZ) : https://www.bluez.org/",
         "Bluetooth Core Specification 5.4 (Bluetooth SIG)"]),
    fiche("spectre", r"ondes\s+(spectre|r[eè]gle|libres?)\b", [
        {"cmd": "echo $((2400 * 1000000))", "sortie": "2400000000"},
        {"cmd": "awk 'BEGIN { printf \"%.2f\\n\", log(5500000000 / 100000000) / log(10) }'", "sortie": "1.74"}],
        ["ANFR, Tableau national de répartition des bandes de fréquences (TNRBF) : https://www.anfr.fr/",
         "Arcep, décision 2014-1263 (appareils de faible portée, bandes libres) ; ERC/REC 70-03 (CEPT)",
         "UIT, Règlement des radiocommunications (2020), article 5",
         "GPS.gov, signal L1 (1575,42 MHz) : https://www.gps.gov/systems/gps/modernization/civilsignals/"]),
    fiche("lora", r"(ondes\s+(lora|temps|vall[eé]e|messages)\b|^echo\s+\"?(2\^12|3600)\b.*\|\s*bc\b|^echo\s+\$\(\((4096|3600)\b)", [
        {"cmd": "echo \"2^12 / 125000\" | bc -l", "sortie": ".03276800000000000000", "outil": "bc"},
        {"cmd": "echo $((4096 * 1000000 / 125000))", "sortie": "32768"},
        {"cmd": "echo \"3600 * 1 / 100\" | bc", "sortie": "36", "outil": "bc"},
        {"cmd": "echo $((36000000 / 577536))", "sortie": "62"}],
        ["Semtech, AN1200.13 LoRa Modem Designer's Guide (temps d'émission) et SX1276 datasheet § 4.1.1.7",
         "ETSI EN 300 220-2 V3.2.1 : appareils à courte portée, 863-870 MHz (25 mW, cycle de 1 %)",
         "LoRa Alliance, RP002-1.0.4 Regional Parameters (EU863-870)"]),
    fiche("lorawan", r"ondes\s+(passerelles?|maillage|choix)\b", [
        {"cmd": "echo $(( (3 + 1) * 577 ))", "sortie": "2308"}],
        ["LoRa Alliance, LoRaWAN 1.0.4 Specification (architecture en étoile d'étoiles, passerelles)",
         "Meshtastic, documentation (routage par inondation gérée) : https://meshtastic.org/docs/overview/mesh-algo/",
         "MeshCore, dépôt du projet : https://github.com/meshcore-dev/MeshCore"]),
    fiche("maillage", r"(mesh-(route|envoie|coupe)\b|ondes\s+d[eé]fi\b)", [
        {"cmd": "printf 'camp racine\\nracine roche\\nroche feu\\n' | wc -l", "sortie": "3"},
        {"cmd": "printf 'camp racine roche feu\\n' | awk '{ print NF - 1 }'", "sortie": "3"}],
        ["Meshtastic, Mesh Broadcast Algorithm (hop limit 3 par défaut, 7 au plus) : https://meshtastic.org/docs/overview/mesh-algo/",
         "RFC 3626, Optimized Link State Routing (OLSR) : réseaux ad hoc maillés",
         "R. Diestel, Graph Theory, 5e éd. (2017), chap. 3 : connexité (Menger)"]),
    fiche("meshtastic", r"(meshtastic\b|ondes\s+(adulte|n(oe|œ)uds?)\b)", [
        {"cmd": "meshtastic --info", "rejeu": "materiel", "motif": r"Owner"},
        {"cmd": "meshtastic --nodes", "rejeu": "materiel", "motif": r"│"}],
        ["Meshtastic Python CLI : https://meshtastic.org/docs/software/python/cli/",
         "ETSI EN 300 220-2 (bande 868 MHz) ; ANFR, appareils de faible portée",
         "Meshtastic, licence GPL-3.0 : https://github.com/meshtastic/firmware"]),
    fiche("sdr", r"(rtl_\w+|dump1090|ondes\s+([eé]coute|avions?|anonymes?)\b|capteurs_exemple|^command\s+-v\s+rtl)", [
        {"prepare": "echo '{\"model\": \"Exemple-Thermo\", \"id\": 4021, \"temperature_C\": 7.4}' > c.json",
         "cmd": "grep -o '\"temperature_C\": [-0-9.]*' c.json", "sortie": "\"temperature_C\": 7.4"},
        {"prepare": "echo '{\"model\": \"Exemple-Thermo\", \"id\": 4021, \"temperature_C\": 7.4}' > c.json",
         "cmd": "grep -c '\"id\"' c.json", "sortie": "1"},
        {"cmd": "timeout 10 rtl_test -t", "rejeu": "materiel", "motif": r"Found \d+ device"}],
        ["rtl-sdr (Osmocom) : https://osmocom.org/projects/rtl-sdr/wiki ; rtl_433 : https://github.com/merbanan/rtl_433",
         "dump1090 (ADS-B, 1090 MHz) : https://github.com/flightaware/dump1090",
         "Code des postes et des communications électroniques, art. L. 33-3 (réception) et CNIL (données personnelles)",
         "ANFR, « Qu'est-ce qu'un récepteur radio ? » : écouter les signaux publics, sans les divulguer"]),
])

ONDES = {"id": "ondes", "types": ["ciel"], "requis": ["n4"], "requis_lecons": ["port7", "sm3"],
         "paliers": [f"on{i}" for i in range(11)], "chapitre": "ondes",
         "attirance": {"cmds": ["nmcli", "iw", "rfkill", "bluetoothctl", "meshtastic", "rtl_test"], "familles": ["Célestes"]},
         "ponts": {"ports": ["port"], "unites": ["machines"], "bc": ["forge"], "graphes": ["port"]},
         "exploits": [{"id": "ondes.onde", "nom": "recomp.ondes.onde", "recompense": "variante"}],
         "maths": ["frequence", "puissances_10", "longueur_onde", "temps_emission", "pourcentages", "division"],
         "variantes_reservees": ["zapiot:orage", "ventouzar:orage", "cyclonaute:orage"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


MATHS = dict([
    maths_fiche("frequence", ["division"], "college", [
        {"cmd": "echo $((120 / 4))", "sortie": "30"}, {"cmd": "echo $((2400 * 1000000))", "sortie": "2400000000"}],
        ["BIPM, Le Système international d'unités, 9e édition (2019) : le hertz (Hz = s⁻¹)",
         "Programme de physique-chimie, cycle 4 (signaux sonores et lumineux) : https://eduscol.education.fr/"]),
    maths_fiche("puissances_10", ["puissances"], "college", [
        {"cmd": "echo $((10**9))", "sortie": "1000000000"}, {"cmd": "echo \"10^-3\" | bc -l", "sortie": ".00100000000000000000",
                                                              "outil": "bc"}],
        ["BIPM, SI 9e édition (2019), tableau 7 : préfixes k, M, G, m, µ, n",
         "Bash, Shell Arithmetic (**) : https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html"]),
    maths_fiche("longueur_onde", ["frequence", "division", "puissances_10"], "lycee", [
        {"cmd": "echo $((300000000 / 100000000))", "sortie": "3"},
        {"cmd": "echo \"300000000 / 2400000000\" | bc -l", "sortie": ".12500000000000000000", "outil": "bc"}],
        ["BIPM, SI 9e édition (2019) : c = 299 792 458 m/s (valeur exacte)",
         "Programme de physique-chimie de seconde : ondes et signaux (λ = v / f) : https://eduscol.education.fr/"]),
    maths_fiche("temps_emission", ["multiplication", "division"], "college", [
        {"cmd": "echo $((23 * 16))", "sortie": "368"}, {"cmd": "echo \"36 / 0.577536\" | bc", "sortie": "62", "outil": "bc"}],
        ["Semtech, AN1200.13 LoRa Modem Designer's Guide (temps d'émission)",
         "ETSI EN 300 220-2 : cycle d'utilisation de 1 % dans la bande 868 MHz"]),
])

ETAPES = {"on1.0": {"maths": ["frequence"]}, "on1.2": {"maths": ["puissances_10"]}, "on1.3": {"maths": ["longueur_onde"]},
          "on4.0": {"maths": ["puissances_10"]}, "on5.2": {"maths": ["temps_emission"]}, "on5.5": {"maths": ["pourcentages"]},
          "on5.6": {"maths": ["division"]}}

REJEU = {
    "on0.1": {"contient": ["plan_de_la_tour.txt", "carnet_de_la_tour.txt"], "pourquoi": "hist.on0.1.bravo : le plan et le carnet"},
    "on1.2": {"sortie": ".12500000000000000000", "outil": "bc", "pourquoi": "hist.on1.2.bravo : 0,125 m = 12,5 cm"},
    "on5.1": {"sortie": ".03276800000000000000", "outil": "bc", "pourquoi": "hist.on5.1.bravo : 0,032768 s, environ 33 ms"},
    "on5.5": {"sortie": "36", "outil": "bc", "pourquoi": "hist.on5.5.bravo : 36 secondes par heure"},
    "on10.4": {"motif": r"\"temperature_C\": 7\.4", "pourquoi": "hist.on10.4.bravo : des lignes JSON de capteurs (fictifs)"},
    "on10.5": {"sortie": "\"temperature_C\": 7.4\n\"temperature_C\": 19.8\n\"temperature_C\": 7.6",
               "pourquoi": "hist.on10.5.bravo : seulement les températures, sans les identifiants"},
}


def main():
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    mondes = [m for m in P["mondes"] if m["id"] != "ondes"]
    i = next((k for k, m in enumerate(mondes) if m["id"] == "machines"), len(mondes) - 1) + 1
    mondes.insert(i, ONDES)
    P["mondes"] = mondes
    for cle in ("etapes", "rejeu"):                   # les étapes de la Tour : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("on") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    P["rejeu"].update(REJEU)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    for c in ("pc/tg/ondes.json", "app/src/main/assets/ondes.json"):
        shutil.copyfile(D / "donnees/ondes.json", D / c)
    print(f"{len(FICHES)} fiches de la Tour des Ondes, {len(MATHS)} ponts des nombres, {len(REJEU)} étapes rejouées")


if __name__ == "__main__":
    main()
