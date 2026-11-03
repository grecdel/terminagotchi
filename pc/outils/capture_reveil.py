"""Captures de la carte du réveil (idées 31 à 39, 88) dans l'espace de travail PC, et de `tg carte` dans un terminal.

    python3 pc/outils/capture_reveil.py <dossier de sortie>

Une vraie partie dans un HOME temporaire (celle de capture_espace.py) : chapitres 1, 2, grenier, bibliothèque et cave
finis (œuf Feu), les mondes ouverts au niveau 4, le Port joué jusqu'au palier 3, deux lieux secrets trouvés, les
habitants posés. Sorties : reveil_carte_jour.png, reveil_carte_nuit.png, reveil_vague.png (un biome qui se réveille),
reveil_fiche.png (clic droit sur le Port), reveil_habitant.png, reveil_livre.png, reveil_carnet.png,
reveil_meteo_arc.png, reveil_tg_carte.png, reveil_endormi.png (tout dort), reveil_tout.png (tout vivant).
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "pc" / "outils"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_reveil_")
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")

import capture_espace as CE  # noqa: E402

from tg import app, core, histoire, quetes, reveil  # noqa: E402
from tg import espace as E  # noqa: E402
from tg import espace_scene as S  # noqa: E402


def partie(ailes=("reveil", "nid", "grenier", "bibliotheque", "cave"), faits_en_plus=(), oeuf="feu"):
    st = core.load()
    st["oeuf_type"] = oeuf
    st.setdefault("guide", {})["type_c"] = oeuf
    h = histoire.h_(st)
    h["ailes"] = list(ailes)
    from tg import programme
    for c in ailes:
        ch = histoire.PAR_CHAP.get(c)
        if ch:
            h["faits"] = list(dict.fromkeys(h["faits"] + list(ch["lecons"])))
    h["faits"] = list(dict.fromkeys(h["faits"] + list(faits_en_plus)))
    histoire.meubler(st)
    quetes.poser(st)
    core.save(st)
    return st


def espace(onglet="carte"):
    import tg.bureau_vie as V
    horloge = [1000.0]
    V.maintenant = lambda: horloge[0]
    esp = E.Espace(app.etape)
    esp.lignes = []
    esp.mini.dossier = str(core.TERRAIN)
    esp.onglet = onglet
    return esp


def carte(esp, nom, sortie, zone=True):
    im = CE.dessiner(esp, esp.t)
    if zone:                                       # le panneau Carte agrandi, et l'écran entier à côté
        im.convert("RGB").save(sortie / (nom + "_ecran.png"))
        im = im.crop((1300, 520, 1910, 1075))
        im = im.resize((im.width * 2, im.height * 2))
    im.convert("RGB").save(sortie / (nom + ".png"))


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    CE.preparer()
    port = [f"port{i}" for i in range(5)]
    st = partie(faits_en_plus=port)
    q = quetes.q_(st)
    for qid in ("m02", "m10", "m16"):              # deux lieux secrets trouvés, un habitant aidé
        if qid not in q["finies"]:
            q["finies"].append(qid)
    reveil.r_(st)["evts"] = ["aurore", "baleine", "etoile_filante"]
    core.save(st)
    import datetime
    vrai = datetime.datetime

    class Jour(vrai):
        @classmethod
        def now(cls, tz=None):
            return vrai(2026, 7, 14, 14, 0)

    class Nuit(vrai):
        @classmethod
        def now(cls, tz=None):
            return vrai(2026, 12, 20, 22, 30)
    # la carte vue une 1re fois : sans animation
    st = core.load()
    reveil.noter_carte(st, reveil.signature(reveil.etat(st)))
    core.save(st)
    datetime.datetime = Jour
    esp = espace()
    esp.jeu()
    CE.avancer(esp, 0.5)
    carte(esp, "reveil_carte_jour", sortie)
    # survol du Port
    esp.rv["survol"] = "port"
    carte(esp, "reveil_survol", sortie)
    esp.rv["survol"] = None
    # clic droit : la fiche du Port
    esp.rv["fiche"] = "port"
    carte(esp, "reveil_fiche", sortie)
    esp.rv["fiche"] = "hab:m18"
    carte(esp, "reveil_habitant", sortie)
    esp.rv["fiche"] = None
    esp.rv["livre"] = True
    carte(esp, "reveil_livre", sortie)
    esp.rv["livre"] = False
    esp.rv["carnet"] = True
    carte(esp, "reveil_carnet", sortie)
    esp.rv["carnet"] = False
    esp.rv["cmds"] = [("cat lianes.txt | grep gland", __import__("time").time())]
    esp.rv["meteo"] = ("arc", 0)
    esp.rv["cache"] = None
    carte(esp, "reveil_meteo_arc", sortie)
    esp.rv["cmds"] = []
    # « Y aller »
    esp.clic_reveil("rv:lieu:port")
    carte(esp, "reveil_y_aller", sortie, zone=False)
    esp.mini.saisie = ""
    # la nuit, en hiver
    datetime.datetime = Nuit
    esp.rv["cache"] = None
    esp.rv["meteo"] = ("calme", 0)
    carte(esp, "reveil_carte_nuit", sortie)
    # un biome qui se réveille : l'aile 6 (machines → Feu, déjà réveillé par l'œuf → la Glace) finie
    datetime.datetime = Jour
    st = core.load()
    histoire.h_(st)["ailes"].append("machines")
    core.save(st)
    esp = espace()
    esp.jeu()
    for i in range(int(1.3 / 0.05)):
        CE.avancer(esp, 0.05)
    carte(esp, "reveil_vague", sortie)
    # tout endormi et tout vivant (comme la planche du réveil)
    st = core.load()
    h = histoire.h_(st)
    sauve = list(h["ailes"])
    h["ailes"] = []
    core.save(st)
    esp = espace()
    esp.rv["file"], esp.rv["anim"] = [], None
    st = core.load()
    reveil.noter_carte(st, reveil.signature(reveil.etat(st)))
    core.save(st)
    esp.jeu()
    carte(esp, "reveil_endormi", sortie)
    st = core.load()
    histoire.h_(st)["ailes"] = sauve + ["dortoir", "atelier", "tour", "coeur"]
    reveil.noter_carte(st, reveil.signature(reveil.etat(st)))
    core.save(st)
    esp = espace()
    esp.jeu()
    carte(esp, "reveil_tout", sortie)
    # tg carte dans un terminal
    st = core.load()
    lignes = reveil.lignes_carte(st)
    CE.ansi_image(lignes, 90, None, 15).convert("RGB").save(sortie / "reveil_tg_carte.png")
    print("captures :", sorted(p.name for p in sortie.iterdir() if p.name.startswith("reveil_")))


if __name__ == "__main__":
    main()
