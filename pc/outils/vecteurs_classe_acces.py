"""Les vecteurs communs Python ↔ Kotlin des idées du 3 novembre (classe et accessibilité) :
donnees/classe/vecteurs_acces.json — lecture et confort (confort.py / Confort.kt), séance guidée et écran projecteur
(seance.py / Classe.kt Seances), place de la classe (place.py / Classe.kt Place), carte de visite (carte_visite.py /
Classe.kt CarteVisite).

    python3 pc/outils/vecteurs_classe_acces.py              écrit les vecteurs
    python3 pc/outils/vecteurs_classe_acces.py --verifier   code de sortie 1 s'ils ne sont plus à jour
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import carte_visite as CV  # noqa: E402
from tg import confort as C  # noqa: E402
from tg import langue  # noqa: E402
from tg import place as P  # noqa: E402
from tg import seance as S  # noqa: E402

FICHIER = RACINE / "donnees" / "classe" / "vecteurs_acces.json"


def vecteurs():
    langue.definir("fr")
    conf = []
    for c in ({}, {"taille": 125}, {"taille": 150, "police": "facile"}, {"taille": 99}, {"taille": "125"},
              {"formes": True}, {"formes": False}, {"calme": True}, {"calme": False}, {"police": "bizarre"},
              {"taille": 125.0, "formes": False, "calme": True, "police": "normale"}):
        for th in ("sombre", "contraste", "daltonien"):
            for sy in ({"echelle": 1.0, "moins_animations": False}, {"echelle": 1.3, "moins_animations": True},
                       {"echelle": 1.6, "moins_animations": False}):
                conf.append({"c": c, "theme": th, "systeme": sy, "attendu": C.resoudre(c, th, sy)})
    tailles = [{"echelle": e, "taille": C.taille_de(e)} for e in (0.85, 1.0, 1.11, 1.12, 1.15, 1.3, 1.36, 1.37, 2.0)]
    suivantes = [{"taille": t_, "sens": s, "suivante": C.taille_suivante(t_, s)} for t_ in (100, 125, 150) for s in (1, -1)]
    ips = ["192.168.1.4", "10.0.0.7", "172.16.0.1", "172.31.255.254", "172.32.0.1", "172.15.0.1", "127.0.0.1",
           "8.8.8.8", "100.64.0.1", "169.254.1.1", "192.169.0.1", "256.1.1.1", "192.168.1", "", "::1", "1.2.3.4.5"]
    from tg import classe
    codes = [classe.fabriquer(0, "V"), classe.fabriquer(1, "V"), classe.fabriquer(10, "AGSV"), "05-GSV-C", "05-GS-K",
             "05-GSV-D", ""]
    profils = [{"espece": "gouttelin", "stade": "bebe", "niveau": 3}, {"espece": "Zap", "stade": "bebe", "niveau": 3},
               {"espece": "gouttelin", "stade": "geant", "niveau": 3}, {"espece": "gouttelin", "stade": "ado", "niveau": 1000},
               {"espece": "gouttelin", "stade": "ado", "niveau": True}, {"espece": "a" * 33, "stade": "ado", "niveau": 2},
               {"espece": "oeuf", "stade": "oeuf", "niveau": 0}, {"espece": "x y", "stade": "ado", "niveau": 2},
               {"stade": "ado", "niveau": 2}]
    prefs = [({"ls": 5, "cd": 5, "pwd": 9, "cat": 1, "grep": 2}, ["pwd", "ls", "cd", "cat", "grep"]),
             ({}, ["pwd", "ls", "cd", "cat", "grep"]), ({"ls": 3}, ["pwd", "ls"]),
             ({"z": 2, "a": 2, "b": 2}, []), ({"ls": 0, "cd": 1}, ["ls", "cd"])]
    seances = []
    for s in S.donnees()["seances"]:
        for k in range(len(s["phases"])):
            for extra in ({}, {"vue": "question"}, {"vue": "trace"}, {"commande": False}, {"commande": True}):
                e = dict({"n": s["n"], "phase": k, "commande": None, "vue": None}, **extra)
                seances.append({"e": e, "modele": S.modele(e)})
    return {"note": "pc/outils/vecteurs_classe_acces.py", "confort": conf, "tailles": tailles, "suivantes": suivantes,
            "privee": [{"ip": ip, "ok": P.privee(ip)} for ip in ips],
            "cle": [{"code": c, "cle": P.cle(c)} for c in codes],
            "profil": [{"p": p, "ok": P.profil_valide(p)} for p in profils],
            "preferes": [{"compteurs": c, "ordre": o, "gouts": CV.preferes(c, o)} for c, o in prefs],
            "jours": [{"ne": ne, "maintenant": m, "jours": CV.jours(ne, m)} for ne, m in
                      ((0, 100), (1000, 1000), (1000, 1000 + 86399), (1000, 1000 + 86400), (1000, 1000 + 10 * 86400 + 5))],
            "seances": seances}


def texte():
    return json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    if "--verifier" in sys.argv:
        ok = FICHIER.is_file() and FICHIER.read_text(encoding="utf-8") == texte()
        print("vecteurs à jour" if ok else "donnees/classe/vecteurs_acces.json n'est plus à jour : relancer pc/outils/vecteurs_classe_acces.py")
        sys.exit(0 if ok else 1)
    FICHIER.write_text(texte(), encoding="utf-8")
    print("écrit :", FICHIER)
