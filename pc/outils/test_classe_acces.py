"""Tests des idées du 3 novembre (classe et accessibilité), à côté de test_classe.py :
    1. les vecteurs communs (donnees/classe/vecteurs_acces.json) sont à jour ;
    2. lecture et confort : réglages, Andika livrée (fichier et licence), mode calme (glitch compris) ;
    3. la séance guidée et l'écran projecteur (toutes les phases de toutes les séances se dessinent) ;
    4. la place de la classe sur 127.0.0.1 : entrer, gestes, refus (pas de V, adresse publique, trop vite), un geste
       vu n'est pas réaffiché au lancement suivant, la place se ferme ;
    5. la carte de visite (image, sans nom, goûts).
    python3 pc/outils/test_classe_acces.py
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_classe_acces_")
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import carte_visite as CV  # noqa: E402
from tg import classe, confort, core, glitch, langue  # noqa: E402
from tg import place as P  # noqa: E402
from tg import seance as SE  # noqa: E402

ok = ko = 0


def verifier(c, m):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
    print(("  ✔ " if c else "  ✖ ") + m)


langue.definir("fr")
print("1. Les vecteurs communs")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_classe_acces.py"), "--verifier"],
                   capture_output=True, text=True)
verifier(r.returncode == 0, "donnees/classe/vecteurs_acces.json à jour (mêmes calculs en Kotlin : tests/jvm/Classe.kt)")

print("2. Lecture et confort")
st = core.new_state("Pixel")
core.migrate(st)
verifier(confort.reglages(st)["taille"] in confort.TAILLES, "une partie neuve a une taille de texte permise")
verifier(confort.regler(st, "taille", 150) and confort.reglages(st)["taille"] == 150, "taille 150 %")
verifier(not confort.regler(st, "taille", 175), "une taille non permise est refusée")
for d in (RACINE / "pc/tg/polices", RACINE / "app/src/main/assets/polices"):
    verifier(all((d / n).is_file() and (d / n).stat().st_size > 100_000 for n in confort.POLICE_FICHIERS)
             and "Open Font License" in (d / "OFL-Andika.txt").read_text(encoding="utf-8"),
             f"Andika livrée avec sa licence OFL ({d.relative_to(RACINE)})")
verifier(confort.fichier_police() and confort.fichier_police(True), "« Lecture facile » trouve Andika (normale et grasse)")
try:
    from PIL import ImageFont
    f = ImageFont.truetype(confort.fichier_police(), 20)
    verifier(f.getname()[0] == "Andika", "le fichier est bien la police Andika")
except ImportError:
    pass
verifier("Andika" in (RACINE / "LICENSE-images.md").read_text(encoding="utf-8"), "Andika citée dans LICENSE-images.md")
confort.regler(st, "calme", True)
confort.activer(st)
verifier(glitch.CALME[0], "mode calme : les éclairs des créatures glitch sont calmés")
confort.regler(st, "calme", False)
confort.activer(st)
verifier(not glitch.CALME[0], "hors du mode calme, le glitch est inchangé")
confort.regler(st, "formes", True)
verifier(confort.reglages(st)["formes"], "couleurs + formes")

print("3. La séance guidée et l'écran projecteur")
from tg import espace_scene as ES  # noqa: E402
n_ph = faux = 0
for s in SE.donnees()["seances"]:
    for k in range(len(s["phases"])):
        for vue in (None, "question", "trace"):
            m = SE.modele({"n": s["n"], "phase": k, "commande": None, "vue": vue})
            try:
                L = SE.scene(m, 0.0)[0]
                faux += not any(op[0] == "texte" and m["nom"] in str(op[3]) for op in L) and vue is None
            except Exception as e:                   # noqa: BLE001
                faux += 1
                print("     ", s["n"], k, vue, repr(e))
            n_ph += 1
verifier(faux == 0, f"{n_ph} écrans projecteur dessinés (toutes les séances, toutes les phases)")
img = ES.vers_pil(SE.scene(SE.modele({"n": 5, "phase": 1, "commande": None, "vue": None}), 0.0)[0], (1600, 900))
verifier(img.size == (1600, 900), "l'écran projecteur en image (1600 × 900)")

print("4. La place de la classe (127.0.0.1)")
code = classe.fabriquer(5, "GSV")
verifier(P.cle("05-GS-K") is None and P.cle(code), "la place n'existe qu'avec la lettre V")
verifier(P.demander("8.8.8.8", P.PORT, {}) is None, "jamais d'adresse publique")
pl = P.Place(code)
srv, port = P.servir(pl, "127.0.0.1")
try:
    a = P.Client(code, {"espece": "gouttelin", "stade": "bebe", "niveau": 3}, "127.0.0.1", port)
    b = P.Client(code, {"espece": "zapiot", "stade": "ado", "niveau": 9}, "127.0.0.1", port)
    verifier(a.rejoindre() and b.rejoindre() and {a.poste, b.poste} == {1, 2}, "deux postes entrent (1 et 2)")
    verifier(P.Client(code, {"espece": "x y", "stade": "ado", "niveau": 1}, "127.0.0.1", port).rejoindre() is False,
             "un profil mal formé est refusé")
    verifier(a.geste(b.poste, 1), "un geste « Bravo »")
    verifier(not a.geste(b.poste, 0), "deux gestes trop vite : le second attend")
    b.relire()
    verifier([g for g, _de, _q in b.recus] == [1] and b.recus[0][1] == a.poste, "le geste est reçu, avec le poste")
    memo = P.memo_de(b)
    b2 = P.Client(code, b.profil, memo["hote"], memo["port"], memo["jeton"], memo["vu"])
    verifier(b2.rejoindre() and b2.poste == b.poste and b2.recus == [],
             "relancé avec sa mémoire : même poste, le geste déjà vu n'est pas réaffiché")
    time.sleep(P.PAS_GESTE + 0.1)
    verifier(a.geste(b.poste, 2), "un nouveau geste « Danse »")
    b2.relire()
    verifier([g for g, _de, _q in b2.recus] == [2], "seul le nouveau geste arrive")
    b3 = P.Client(code, b.profil, "127.0.0.1", port, "jeton-inconnu", memo["vu"])
    verifier(b3.rejoindre() and b3.dernier_id <= 2 and b3.poste == 3, "un jeton inconnu : nouveau poste")
    pl.fermer()
    verifier(not a.relire() and a.etat == "fermee", "le prof ferme : la place se ferme pour tous")
finally:
    srv.shutdown()
    srv.server_close()

print("5. La carte de visite")
st = core.new_state("Pixel")
core.migrate(st)
st["born"] = time.time() - 3 * 86400
st["gouts"] = {"ls": 5, "pwd": 2, "cd": 2, "cat": 1}
st["seen"] = ["pwd", "ls", "cd", "cat"]
c = CV.contenu(st)
verifier(c["gouts"] == ["ls", "pwd", "cd", "cat"] and c["jours"] == 4 and c["nom"] == "Pixel", f"contenu : {c}")
verifier(CV.contenu(st, avec_nom=False)["nom"] == "", "« sansnom » cache le nom de la créature")
try:
    im = CV.image(st)
    verifier(im.size == (CV.W, CV.H), "l'image de la carte (750 × 1050)")
except ImportError:
    pass
core.save(st)
sortie = CV.commande(["sansnom"])
verifier((core.TERRAIN / "ma_carte_de_visite.png").is_file() and "pip" not in sortie, "tg carte visite sansnom écrit l'image")

print(f"\n{ok} ✔  {ko} ✖")
sys.exit(1 if ko else 0)
