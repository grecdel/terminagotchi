"""Les vecteurs communs de l'Atelier (Python ↔ Kotlin) : donnees/atelier/vecteurs.json.

    python3 pc/outils/vecteurs_atelier.py              écrit les vecteurs (depuis pc/tg/atelier.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_atelier.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

La physique du robot simulé (distance du capteur, un pas : avancer, se cogner, tourner, s'arrêter) sur chaque arène
avec quatre cerveaux (tourne à droite, tourne à gauche, fonce, s'arrête), le verdict du défi, la grille dessinée, ce que
le moteur et la LED comprennent (UTF-8 et UTF-16 de PowerShell), l'arène, la porte, les situations et le réflexe de
chaque partie, les réponses (table de vérité, coordonnées, et / ou / non), ce que fait une commande au robot et la vue
déployée : tests/jvm/Atelier.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import atelier as A, deploie, langue  # noqa: E402

FICHIER = RACINE / "donnees" / "atelier" / "vecteurs.json"
CERVEAUX = {"droite": lambda d: "droite" if d < 10 else "avance", "gauche": lambda d: "gauche" if d < 10 else "avance",
            "fonce": lambda d: "avance", "stop": lambda d: "stop" if d < 10 else "avance",
            "zigzag": lambda d: "gauche" if d < 20 else "avance"}


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123", "5:5", "8:1762000000"]
    cles = ["e"] + list(range(len(A.donnees()["arenes"])))
    physique = []
    for cle in cles:
        for nom, f in CERVEAUX.items():
            pas = A.simuler(cle, f, 24)
            vus = {(A.depart(cle)["x"], A.depart(cle)["y"])} | {(r["x"], r["y"]) for r, _e, _d in pas[:20]}
            chocs = sum(1 for _r, e, _d in pas[:20] if e == "choc")
            physique.append({"arene": str(cle), "cerveau": nom, "depart_cm": A.distance_cm(A.arene(cle)["grille"], *A.depart(cle).values()),
                             "pas": [[r["x"], r["y"], r["d"], e, d] for r, e, d in pas],
                             "verdict": A.verdict(len(vus), chocs, 20), "cases": len(vus), "chocs": chocs})
    verdicts = [{"cases": c, "chocs": h, "pas": p, "v": A.verdict(c, h, p)} for c, h, p in
                ((12, 0, 20), (11, 0, 20), (19, 0, 20), (5, 1, 7), (12, 0, 19), (0, 0, 0), (12, 2, 20))]
    dessins = []
    for cle, r, vus, choc in (("e", {"x": 1, "y": 1, "d": "E"}, [], False), ("e", {"x": 7, "y": 1, "d": "E"}, [[1, 1], [2, 1]], True),
                              (0, {"x": 3, "y": 2, "d": "N"}, [[3, 2], [4, 2]], False), (2, {"x": 8, "y": 2, "d": "S"}, [], False),
                              (3, {"x": 0, "y": 5, "d": "O"}, [[1, 5]], False)):
        dessins.append({"arene": str(cle), "robot": r, "vus": vus, "choc": choc, "lignes": A.dessin_grille(cle, r, vus, choc=choc)})
    textes = ["avance", "Avance\n", "  droite ", "gauche", "stop", "", "forward", "LEFT", "recule", "1", "avance\nstop", "arrêt"]
    moteurs = [{"texte": x, "moteur": A.moteur_de(x)} for x in textes]
    leds = [{"texte": x, "led": A.led_de(x)} for x in ("1", "0", " 1 ", "2", "", "on", "01")]
    octets = [{"hex": h, "valeur": A.lire_valeur(bytes.fromhex(h))} for h in
              ("310a", "300d0a", "fffe31000d000a00", "efbbbf310a", "6176616e63650a", "", "2020340a")]
    parties = [{"graine": g, "arene": A.arene_defi(g), "porte": A.porte(g), "table": A.table_verite(A.porte(g)),
                "choix": [list(c) for c in A.choix_cartes(g)], "reflexe": list(A.reflexe(g))} for g in graines]
    chiffres = [{"args": a, "chiffres": A.chiffres(a)} for a in
                (["0", "0", "0", "1"], ["0001"], ["0,1,1,1"], ["0", "1"], ["a", "b"], ["0", "0", "0", "2"], ["0 1"], [])]
    portes = [{"mot": m, "porte": A.porte_de(m)} for m in ("et", "ET", "ou", "Non", "and", "or", "not", "oui", "nicht", "или", "")]
    coords = [{"texte": x, "x": 2, "y": 1, "ok": A.coord_ok(x, 2, 1)} for x in ("2 1", "2,1", "(2 ; 1)", "x=2 y=1", "1 2", "2", "2 1 0", "")]
    lignes = ["echo 1 > robot/led", "echo 0 >robot/led", "cat robot/led", "cat robot/capteur_distance", "echo avance > robot/moteur",
              "cat robot/moteur", "atelier pas", "tg atelier pas", "sh cerveau.sh", "bash ./cerveau.sh", "time sh cerveau.sh",
              "for i in $(seq 20); do sh cerveau.sh; atelier pas; done", "for i in 1 2 3; do cat robot/capteur_distance; sleep 1; done",
              'd=$(cat robot/capteur_distance); if [ "$d" -lt 10 ]; then echo obstacle; else echo libre; fi',
              "ls /sys/class/leds", "ls robot", "atelier robot", "echo bonjour", "cat robot/led | head -1 && atelier pas",
              # PowerShell (Windows) : les mêmes pièces du robot (robot\\led, Set-Content, .\\cerveau.ps1, ForEach-Object)
              "echo 1 > robot\\led", "Set-Content robot\\moteur droite", "Get-Content robot\\capteur_distance",
              "1..20 | ForEach-Object { .\\cerveau.ps1; atelier pas }", "Measure-Command { .\\cerveau.ps1 }",
              "powershell -ExecutionPolicy Bypass -File .\\cerveau.ps1", "notepad cerveau.ps1"]
    robots = [{"ligne": l, "robots": [list(a) for a in A.robots_de(l)]} for l in lignes]
    dep = [{"ligne": l, "robots": [{"seg": x["seg"], "cmd": x["cmd"], "piece": x["piece"], "sens": x["sens"]}
                                   for x in deploie.robots(l)]} for l in lignes]
    malins = [{"texte": x, "ok": A.cerveau_malin_ok(x)} for x in (
        A.cerveau_malin(), A.cerveau_exemple(), 'd=$(cat robot/capteur_distance)\nif [ "$d" -le 0 ]; then echo gauche > robot/moteur; else echo avance > robot/moteur; fi',
        "if true; then echo droite; fi", "")]
    return {"note": "généré par pc/outils/vecteurs_atelier.py ; vérifié par tests/jvm/Atelier.kt",
            "physique": physique, "verdicts": verdicts, "dessins": dessins, "moteurs": moteurs, "leds": leds,
            "octets": octets, "parties": parties, "chiffres": chiffres, "portes": portes, "coords": coords,
            "robots": robots, "deploie": dep, "malins": malins}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/atelier/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_atelier.py")
            sys.exit(1)
        print("vecteurs de l'Atelier à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
