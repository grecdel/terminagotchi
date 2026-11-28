"""Test rapide : les espèces à accent (Étincelot…) se dressent bien (fiche, examiner, renommage, chant).

    python3 pc/outils/test_noms_accents.py
"""
import os,sys,tempfile
os.environ["HOME"]=tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tg import dressage as D, bestiaire as B
e=B.espece("Étincelot"); assert e, "espèce"
nom=e["nom"]; print(nom, D.fiche(nom).name, D.repaire(nom))
x=next(x for x in D.EPREUVES["Rencontre"] if x["id"]=="examiner")
c={"d":D.T,"nom":nom,"x":{}}
assert x["ok"](c,[f"cat ~/terrain_terminagotchi/{D.fiche(nom).name}"]), "examiner"
from pathlib import Path
d=Path(tempfile.mkdtemp()); c["d"]=d
(d/f"{D.nom_fichier(nom)}.txt").write_text("x")
assert D._renomme(c,[]), "renomme"
(d/"chant.txt").write_text(nom+"\n"); assert D._chant(c,[])
print("aide:", D.aide("Fichiers:renomme", nom)[1], "|", D.aide("Rencontre:examiner", nom)[1])
print("OK accents")
