"""Les vecteurs communs de la Tour des Ondes (Python ↔ Kotlin) : donnees/ondes/vecteurs.json.

    python3 pc/outils/vecteurs_ondes.py              écrit les vecteurs (depuis pc/tg/ondes.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_ondes.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les fréquences tapées, la longueur d'onde et la réponse de l'enfant, le mur (décibels, pour cent), les canaux et les
bandes Wi-Fi, le résumé anonyme d'une liste de réseaux, la règle du spectre, les bandes libres et les choix mélangés
pour chaque partie, la vallée et le plus petit SF, le temps d'émission LoRa, la règle du 1 %, le maillage (chemins,
inondation, envois avec des nœuds coupés), la cible de la tempête, les antennes (lire, chercher, changer, écouter,
émettre, simuler) et la vue déployée : tests/jvm/Ondes.kt vérifie que l'appli Android donne EXACTEMENT les mêmes
résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, ondes as O  # noqa: E402

FICHIER = RACINE / "donnees" / "ondes" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123", "5:5", "8:1762000000"]
    freqs = ["lora", "wifi", "Wi-Fi", "wifi5", "5G", "4g", "fm", "gps", "bluetooth", "868M", "868MHz", "2.4G", "2,4 GHz",
             "100000000", "433.92M", "1k", "abc", "", "0.1", "12x", "wifi6", "BT"]
    frequences = [{"texte": f, "resultat": list(O.frequence_de(f)) if O.frequence_de(f) else None} for f in freqs]
    hzs = [100_000_000, 868_000_000, 1_575_420_000, 2_400_000_000, 5_000_000_000, 1000, 300, 433_920_000]
    longueurs = [{"hz": h, "m": O.longueur_onde(h), "texte": O.texte_longueur(O.longueur_onde(h)), "periodes": O.periodes(h)}
                 for h in hzs]
    reps = ["34.6", "34,6", "35", "34", "0.35", "0,3456", "346 mm", "34.6 cm", "0.35 m", "12.5", "33", "36.5", "abc", "",
            "1", "3456", "35 km", "0.33"]
    longueur_ok = [{"reponse": r, "ok": O.longueur_ok(r, 868_000_000)} for r in reps]
    murs = [{"matiere": m, "tech": t_, "n": n, "db": O.affaiblissement(m, t_, n), "restant": list(O.restant_pc(O.affaiblissement(m, t_, n)))}
            for m in ("bois", "brique", "beton", "verre") for t_ in ("lora", "wifi24", "wifi5") for n in (1, 2, 3)]
    canaux = [{"mhz": f, "canal": O.canal(f), "bande": O.bande(f)} for f in
              (2412, 2417, 2437, 2462, 2472, 2484, 2400, 2413, 5180, 5200, 5500, 5745, 5825, 5955, 6115, 7115, 868, 5000, 5150)]
    listes = [[], [2412, 2437, 2437, 5180], [2412, 2412, 2412, 2462, 5500, 5955, 6115, 868], [2484, 2472, 2417]]
    resumes = [{"freqs": l, **{k: (v if not isinstance(v, dict) else {str(a): b for a, b in v.items()}) for k, v in O.resume_wifi(l).items()}}
               for l in listes]
    reseaux = [{"reponse": r, "vrai": v, "ok": O.reseaux_ok(r, v)} for r, v in
               (("6", 6), ("8", 6), ("9", 6), ("4", 6), ("3", 6), ("0", 0), ("2", 0), ("3", 0), ("24", 20), ("25", 20), ("15", 20),
                ("abc", 6), ("", 6), ("6.5", 6))]
    parties = [{"graine": g, "regle": [[l, i] for l, i in O.regle_cartes(g)], "regle_reponse": O.regle_reponse(g),
                "libre": [[n, i, r] for n, i, r in O.libre_cartes(g)], "choix": [[n, i, r] for n, i, r in O.choix_cartes(g)],
                "vallee": O.vallee_m(g), "sf": O.sf_min(O.vallee_m(g)), "cible": O.defi_cible(g)} for g in graines]
    lora = [{"sf": sf, "octets": oc, "symbole_us": O.duree_symbole_us(sf), "symboles": O.symboles_message(sf, oc),
             "us": O.temps_emission_us(sf, oc), "par_heure": O.messages_heure(sf, oc)}
            for sf in (7, 8, 9, 10, 11, 12) for oc in (1, 10, 51)]
    portees = [{"distance": d, "sf": O.sf_min(d)} for d in (0, 1999, 2000, 2001, 3500, 5000, 7000, 9500, 11000, 11001)]
    messages = [{"reponse": r, "sf": sf, "ok": O.messages_ok(r, sf)} for r, sf in
                (("62", 11), ("61", 11), ("63", 11), ("64", 11), ("36", 12), ("873", 7), ("abc", 9), ("124", 10), ("249", 9))]
    coupures = [[], ["roche"], ["racine"], ["roche", "eau"], ["plante", "eau", "glace"], ["roche", "ciel", "glace"],
                ["machine", "poison", "glace"], ["feu", "glace", "plante"]]
    maillage = [{"coupes": c, "routes": {d: O.route("camp", d, c) for d in O.noeuds()}, "inondation": O.inondation("camp", c),
                 "envois": {d: O.envoi(d, c) for d in O.noeuds() + ["lune"]}, "voisins": {d: O.voisins(d, c) for d in O.noeuds()}}
                for c in coupures]
    lignes = ["nmcli radio", "nmcli r", "nmcli dev wifi list", "nmcli -f CHAN,FREQ,SIGNAL,BARS dev wifi list --rescan no",
              "nmcli device wifi rescan", "nmcli radio wifi off", "nmcli dev wifi connect Box", "iw dev", "iw dev wlan0 scan",
              "iwconfig", "rfkill list", "rfkill", "rfkill block wifi", "rfkill unblock all", "bluetoothctl show",
              "timeout 5 bluetoothctl show | grep -E 'Powered|Discoverable'", "bluetoothctl scan on", "bluetoothctl pair AA",
              "mesh-envoie feu bonjour", "tg ondes mesh-route", "ondes mesh-coupe roche", "meshtastic --info",
              "meshtastic --nodes", "meshtastic --sendtext bonjour", "meshtastic --set lora.region EU_868", "rtl_test -t",
              "timeout 10 rtl_test -t", "rtl_fm -f 100M | aplay", "rtl_433 -F json", "dump1090 --interactive", "ls", "echo nmcli",
              "sudo nmcli radio", "nmcli radio && rfkill list; iw dev", "ondes onde"]
    antennes = [{"ligne": l, "antennes": [list(a) for a in O.antennes_de(l)]} for l in lignes]
    dep = [{"ligne": l, "antennes": [{"seg": x["seg"], "cmd": x["cmd"], "radio": x["radio"], "sens": x["sens"]}
                                     for x in deploie.antennes(l)]} for l in lignes]
    return {"note": "généré par pc/outils/vecteurs_ondes.py ; vérifié par tests/jvm/Ondes.kt",
            "frequences": frequences, "longueurs": longueurs, "longueur_ok": longueur_ok, "murs": murs, "canaux": canaux,
            "resumes": resumes, "reseaux": reseaux, "parties": parties, "lora": lora, "portees": portees,
            "messages": messages, "budget_us": O.budget_us(), "traverse": O.traverse_le_mieux(),
            "maillage": maillage, "antennes": antennes, "deploie": dep}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/ondes/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_ondes.py")
            sys.exit(1)
        print("vecteurs de la Tour des Ondes à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
