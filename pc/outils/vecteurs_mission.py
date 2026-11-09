"""Les vecteurs communs de la ligne 🎯 et de l'humeur (Python ↔ Kotlin) : donnees/mission/vecteurs.json.

    python3 pc/outils/vecteurs_mission.py              écrit les vecteurs (depuis pc/tg/mission.py et envies.py)
    python3 pc/outils/vecteurs_mission.py --verifier   code de sortie 1 si le fichier n'est plus à jour

Allègement du 9 novembre (variante B « terminal + mission ») : mission.formater (la ligne 🎯 au-dessus de la saisie)
et envies.EMOJIS (la seule humeur montrée). tests/jvm/Mission.kt vérifie que Mission.kt et Envies.kt donnent
EXACTEMENT les mêmes réponses, en français.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import envies, langue, mission  # noqa: E402

FICHIER = RACINE / "donnees" / "mission" / "vecteurs.json"

CAS = [
    ("defi", {"cmd": "ls -a", "s": "12", "calme": False}),
    ("defi", {"cmd": "whoami", "s": "0", "calme": True}),
    ("terrain", {"cmd": "mkdir ~/terrain_terminagotchi"}),
    ("lecon", {"titre": "Où suis-je ?", "k": 1, "n": 3, "cmd": "`pwd`"}),
    ("lecon", {"titre": "Le lit", "k": 3, "n": 3, "cmd": "cd ~/terrain_terminagotchi/nid puis `mkdir lit`"}),
    ("lecon", {"titre": "Sans aide", "k": 2, "n": 4, "cmd": "🧩 à toi de trouver la commande ! (`aide` la montre)"}),
    ("niveau", {"n": 4, "xp": 37}),
    ("bandeau", {"titre": "Choisis ta prochaine aile"}),
    ("quete", {"ligne": "👣 Quête suivie : visiter la cave"}),
    ("rien", {}),
]


def vecteurs():
    langue.definir("fr")
    return {"note": "pc/tg/mission.py et envies.py (= Mission.kt et Envies.kt), en français",
            "mission": [{"genre": g, "v": v, "ligne": mission.formater(g, **v)} for g, v in CAS],
            "emojis": dict(sorted(envies.EMOJIS.items())), "inconnu": "😵"}


def texte():
    return json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    if "--verifier" in sys.argv:
        sys.exit(0 if FICHIER.exists() and FICHIER.read_text(encoding="utf-8") == texte() else 1)
    FICHIER.write_text(texte(), encoding="utf-8")
    print(FICHIER)
