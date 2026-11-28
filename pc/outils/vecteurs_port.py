"""Les vecteurs communs du Port (Python ↔ Kotlin) : donnees/port/vecteurs.json.

    python3 pc/outils/vecteurs_port.py              écrit les vecteurs (depuis pc/tg/port.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_port.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Le réseau simulé du Terminaworld (routes, tables, guidage d'un messager, course TCP / UDP, couches, gardien, sceaux,
annuaire, noms, codes des pages du phare) et le messager de la vue déployée : tests/jvm/Port.kt vérifie que l'appli
Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, port  # noqa: E402

FICHIER = RACINE / "donnees" / "port" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    ids = port.ids()
    pannes = [[], ["roche"], ["roche", "plante"], ["racine"], ["roche", "ciel", "plante"]]
    routes = [{"de": a, "vers": b, "eteints": e, "chemin": port.route(a, b, e)}
              for e in pannes for a in ("camp", "glace") for b in ids if a != b]
    tables = [{"machine": m, "eteints": e, "table": [list(x) for x in port.table(m, e)]}
              for m in ("camp", "racine", "feu") for e in pannes[:3]]
    chemins = [["racine", "plante", "poison", "ombre", "machine", "feu"], ["racine", "roche", "feu"], ["camp", "racine", "eau"],
               ["racine", "feu"], ["racine", "volcan"], [], ["feu.terminaworld"], ["127.42.0.1", "127.42.0.3", "127.42.0.4"],
               ["racine", "eau", "plante", "eau", "plante", "eau", "plante", "eau", "plante"]]
    guides = []
    for c in chemins:
        for e in ([], ["roche"]):
            g = port.guider(c, e)
            guides.append({"chemin": c, "eteints": e, **g})
    noms = ["feu", "FEU", "feu.terminaworld", "127.42.0.2", "localhost", "127.0.0.1", "camp", "volcan", "eau.terminaworld.",
            "racine"]
    couches = ["application transport reseau liaison", "Application Transport Réseau Liaison", "liaison reseau transport application",
               "application transport internet lien", "lettre enveloppe colis camion", "application, transport, réseau, liaison !",
               "application transport reseau"]
    pages = ["/", "/feu", "/FEU/", "/volcan_perdu", "/eau?x=1", "/camp", "/127.42.0.3"]
    lignes = ["ping -c 3 localhost", "curl -I http://localhost:8042/", "curl -s http://localhost:8042/eau | head -n 3",
              "curl -o colis.html http://localhost:8042/feu", "port messager feu", "port guide racine plante poison ombre machine feu",
              "port carte", "ssh moi@example.com", "getent hosts localhost", "tracepath -n 127.0.0.1", "nslookup example.com",
              "ls -l", "cat x | grep y", "curl --cacert sceau_du_phare.pem https://localhost:8443", "ping -c 1 127.42.0.2 && ls",
              "host feu.terminaworld", "curl http://[::1]:8000/"]
    return {
        "note": "Généré par pc/outils/vecteurs_port.py (pc/tg/port.py, pc/tg/deploie.py) ; vérifié par tests/jvm/Port.kt.",
        "routes": routes, "tables": tables, "guides": guides,
        "course": port.course(),
        "noms": [{"nom": n, "id": port.chercher(n)} for n in noms],
        "couches": [{"texte": x, "ok": port.couches_ok(x)} for x in couches],
        "gardien": {**port.gardien(), "baux": [list(b) for b in port.gardien()["baux"]]},
        "sceaux": [{"graine": g, "ordre": [x["raison"] for _i, x in port.sceaux(g)], "vrai": port.vrai_sceau(g)}
                   for g in ("1:0", "1:1761900000", "2:1730000000", "3:42", "1:1700000000")],
        "annuaire": port.annuaire(),
        "pages": [{"chemin": c, "code": port.page(c)[0], "premiere": port.page(c)[1].split("\n")[0]} for c in pages],
        "messagers": [{"ligne": l, "messagers": deploie.messager(l)} for l in lignes],
    }


def texte():
    return json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"


def main():
    t = texte()
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != t:
            print("✖ donnees/port/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_port.py")
            sys.exit(1)
        print("✔ vecteurs du Port à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(t, encoding="utf-8")
    print(f"✔ {FICHIER.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
