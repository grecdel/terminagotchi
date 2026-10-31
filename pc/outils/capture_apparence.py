"""Captures du VRAI jeu (après le code) : progression, thèmes, rangement (et son GIF), options, bureau et île.

    python3 pc/outils/capture_apparence.py <sortie>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import capture_espace as C  # noqa: E402  (HOME temporaire)
from PIL import Image  # noqa: E402

from tg import app, apparence as A, core, histoire, intro  # noqa: E402
from tg import espace as E  # noqa: E402
import tg.bureau_vie as V  # noqa: E402

H = [1000.0]
V.maintenant = lambda: H[0]


def image(esp):
    return C.dessiner(esp, esp.t).convert("RGB")


def nouveau_esp():
    esp = E.Espace(app.etape)
    esp.lignes = []
    esp.mini.dossier = str(core.TERRAIN)
    return esp


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    C.preparer()
    # ------------------------------------------------ la progression : une partie qui repart de l'œuf
    def depart(s):
        intro.nouvelle_partie(s)
        h = histoire.h_(s)
        h["faits"], h["ailes"] = [], []
        s["captures"] = []
        s.pop("apparence", None)
        s["xp"] = 0
    core.modifier(depart)
    etapes = [("1_oeuf", None),
              ("2_eclosion", lambda s: intro.finir(s)),
              ("3_chapitre1", lambda s: histoire.h_(s)["faits"].append("t0")),
              ("4_carte_vue_deployee", lambda s: (histoire.h_(s)["ailes"].append("reveil"), histoire.h_(s)["faits"].append("nid1"))),
              ("5_equipe_tuyaux", lambda s: (s["captures"].extend([{"id": "c1", "espece": "Gouttelin", "nom": "Plic", "stade": "bebe"},
                                                                     {"id": "c2", "espece": "Zapiot", "nom": "Zap", "stade": "bebe"}]),
                                             histoire.h_(s)["faits"].append("biblio1"))),
              ("6_cerveau", lambda s: histoire.h_(s)["faits"].append("scripts0"))]
    esp = nouveau_esp()
    for nom, f in etapes:
        if f:
            core.modifier(lambda s, f=f: (f(s), intro.verifier(s)))
        esp.state = core.load()
        esp._album()
        esp.arrivees = {}
        esp._annonces()
        for l in {"3_chapitre1": ["ls"], "4_carte_vue_deployee": ["echo pomme > nid/repas.txt"],
                  "5_equipe_tuyaux": ["cd grenier", "cat lianes.txt | grep -i gland"]}.get(nom, []):
            C.taper(esp, l)
        if esp.dep:
            esp.dep["auto"] = True
        C.avancer(esp, 1.2)
        esp.state = core.load()
        image(esp).save(out / f"evol_pc_{nom}.png")
    # ------------------------------------------------ les thèmes (l'espace complet)
    esp.arrivees = {}
    esp.onglet = "carte"
    for cle in A.ordre():
        core.modifier(lambda s, c=cle: A.choisir_theme(s, c))
        esp.state = core.load()
        image(esp).save(out / f"theme_pc_{cle}.png")
    core.modifier(lambda s: A.choisir_theme(s, "sombre"))
    esp.state = core.load()
    # ------------------------------------------------ les options
    esp.options = True
    image(esp).save(out / "options_pc_fenetre.png")
    esp.options = False
    # ------------------------------------------------ le rangement et son GIF : Envies glisse, Équipe cachée, le terminal grandit
    esp.rangement = True
    images = []

    def zones():
        m = esp.modele()
        return E.S.scene(m, esp.t)[1]

    def cliche(n=1):
        im = image(esp).resize((960, 540), Image.LANCZOS)
        images.extend([im] * n)
    cliche(8)
    Z = zones()
    z = next(z for z in Z if z[4] == "rg:cacher:equipe")
    esp.lacher(z[0] + 5, z[1] + 5, Z)
    esp.state = core.load()
    cliche(8)
    Z = zones()
    z = next(z for z in Z if z[4] == "rg:dalle:envies")
    x0, y0 = z[0] + z[2] / 2, z[1] + 12
    esp.appui(x0, y0, Z)
    for k in range(1, 13):
        esp.bouger(x0 + 0 * k, y0 + 22 * k)
        cliche(1)
    image(esp).save(out / "rangement_pc_glisser.png")
    esp.lacher(x0, y0 + 22 * 12, Z)
    esp.state = core.load()
    cliche(6)
    Z = zones()
    z = next(z for z in Z if z[4] == "rg:coin:terminal")
    x0, y0 = z[0] + 17, z[1] + 17
    esp.appui(x0, y0, Z)
    for k in range(1, 9):
        esp.bouger(x0 + 30 * k, y0)
        cliche(1)
    esp.lacher(x0 + 240, y0, Z)
    esp.state = core.load()
    cliche(8)
    image(esp).save(out / "rangement_pc.png")
    images[0].save(out / "rangement.gif", save_all=True, append_images=images[1:], duration=120, loop=0)
    esp.rangement = False
    esp.state = core.load()
    image(esp).save(out / "rangement_pc_resultat.png")
    # dispositions toutes prêtes
    for nom in ("terminal_geant", "creature_centre", "classe"):
        core.modifier(lambda s, n=nom: A.choisir_disposition(s, n))
        esp.state = core.load()
        image(esp).save(out / f"dispo_pc_{nom}.png")
    # ------------------------------------------------ le bureau et l'île dans quelques thèmes
    import random
    import capture_bureau as B
    from tg import bureau_scene as BS, poses
    st = B.partie("glandouille")
    album = poses.album(st)
    info = {"nom": "Noisette", "faim": 38, "xp": 62, "titre": "content", "dans_equipe": 4,
            "texte": "Quelle commande garde seulement les lignes qui contiennent « gland » ?"}
    for cle in ("sombre", "clair", "matrix", "gameboy"):
        th = A.Theme(cle)
        im = B.fond_gnome()
        regl = dict(V.DEFAUTS)
        c = V.Creature(B.L_, regl, x=1265, hasard=random.Random(1))
        vue = BS.VueCreature()
        vue.menu = True
        Lc, _ = BS.scene_creature(c, album, vue, regl, B.L_, 440, 430)
        B.poser(im, A.recolorer(Lc, th), 0, B.H_ - 440, (B.L_, 440))
        ile = V.Ile()
        ile.etat, ile.ouverture = "ouverte", 1.0
        mini = V.MiniTerminal(Path.home())
        mini.saisie = "cat lianes.txt | grep gland"
        Li, _ = BS.scene_ile(ile, info, album, mini, 0.4, (700, 120), [(album, BS.BLEU)])
        B.poser(im, A.recolorer(Li, th), (B.L_ - BS.ILE_L) // 2, 34, (BS.ILE_L, BS.ILE_H))
        im.convert("RGB").save(out / f"bureau_{cle}.png")
    # ------------------------------------------------ les options dans le terminal (le vrai menu, rendu)
    import io
    from contextlib import redirect_stdout
    from tg import plateforme

    class Clav:
        def __init__(self, r):
            self.r = list(r)

        def demander(self, q):
            print(q, end="")
            return self.r.pop(0) if self.r else ""
    plateforme.clear = lambda: None
    app.clear = lambda: None
    b = io.StringIO()
    with redirect_stdout(b):
        app.menu_options(core.load(), Clav([]))
    lignes = b.getvalue().split("\n")
    C.ansi_image(lignes, 100, len(lignes) + 1, 15).convert("RGB").save(out / "options_pc_terminal.png")
    b = io.StringIO()
    with redirect_stdout(b):
        app.menu_theme(Clav([""]))
    lignes = b.getvalue().split("\n")
    C.ansi_image(lignes, 80, len(lignes) + 1, 15).convert("RGB").save(out / "options_pc_terminal_theme.png")
    print("écrit :", len(list(out.iterdir())))


if __name__ == "__main__":
    main()
