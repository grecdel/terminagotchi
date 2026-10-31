"""Captures de l'espace de travail (PC), comparables aux maquettes, et le GIF de la vue déployée.

    python3 pc/outils/capture_espace.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette, une Glandouille, chapitre 3 « La
forêt du Grenier »), l'espace de travail (espace.Espace) reçoit de vraies commandes tapées dans son terminal, et la
liste de dessin (espace_scene.py, la même que la fenêtre GTK 4 / tkinter) est dessinée avec PIL.
Sorties : espace_pc.png, espace_cerveau_pc.png, espace_classe.png, espace_texte.png (le mode texte, rendu en image),
deploie_terminal.png (tg deploie dans un terminal), deploie.gif (ls | grep a > liste.txt), tuyaux et leçon.
"""
import os
import re
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_espace_")
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")

from PIL import Image, ImageDraw  # noqa: E402

from tg import app, core, histoire, intro, langue  # noqa: E402
from tg import espace as E  # noqa: E402
from tg import espace_scene as S  # noqa: E402

LIANES = ["Des lianes ont tout mélangé dans le grenier.", "Un Gland doré dort sous le vieux chêne.",
          "Attention : les ronces piquent.", "une liane a enroulé un gland tombé."]


def preparer(langue_code="fr"):
    """Une partie au chapitre 3, le terrain du Terminaworld, une équipe de 4."""
    T = core.TERRAIN
    for d in ("vestibule", "nid", "grenier/fouillis", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier",
              "tour", "coeur", ".cache"):
        (T / d).mkdir(parents=True, exist_ok=True)
    (T / "grenier" / "lianes.txt").write_text("\n".join(LIANES) + "\n", encoding="utf-8")
    (T / "grenier" / "fragment_2.txt").write_text("…\n", encoding="utf-8")
    (T / "grenier" / "griffure.txt").write_text("griffe\n", encoding="utf-8")
    st = core.new_state("Noisette")
    core.migrate(st)
    st["config"]["langue"] = langue_code
    st["espece_compagnon"] = "glandouille"
    st["xp"] = 108
    st["hunger"] = 38.0
    intro.tout_debloquer(st)
    h = histoire.h_(st)
    for c in ("reveil", "nid", "cave"):
        if c not in h["ailes"]:
            h["ailes"].append(c)
        h["faits"] = list(set(h.get("faits", [])) | {c + "0"})
    h["faits"] = list(set(h["faits"]) | {"nid0"})
    histoire.choisir(st, "grenier", dit=False)
    st["captures"] = [
        {"id": "c1", "espece": "Gouttelin", "nom": "Plic", "stade": "bebe", "xp": 0},
        {"id": "c2", "espece": "Zapiot", "nom": "Zap", "stade": "bebe", "xp": 0},
        {"id": "c3", "espece": "Cailloute", "nom": "Caillou", "stade": "bebe", "xp": 0}]
    st["sauvages"] = []
    m = st.setdefault("maison", {})
    m["visites"] = ["vestibule", "nid", "cave", "grenier", "grenier/fouillis"]
    m["cwd"] = str(T / "grenier")
    st["envies"] = {"jeu": 64.0, "curiosite": 80.0, "explorer": 72.0, "sommeil": 55.0}
    try:
        from tg import explo
        explo.spawn(st)                       # un vrai monstre sauvage apparaît quelque part
    except Exception:                         # noqa: BLE001
        pass
    core.save(st)
    langue.definir(langue_code)


def taper(esp, ligne):
    esp.mini.saisie = ligne
    esp.entree()
    esp.jeu()


def dessiner(esp, t_, taille=(1920, 1080)):
    L, Z, (W, H) = S.scene(esp.modele(), t_)
    e = min(taille[0] / W, taille[1] / H)
    return S.vers_pil(S.a_l_echelle(L, e), taille)


def avancer(esp, secondes, pas=0.05):
    """Le temps passe pour l'espace (sans attendre vraiment)."""
    import tg.bureau_vie as V
    t0 = esp.t
    n = int(secondes / pas)
    for i in range(n):
        V.maintenant = (lambda v: (lambda: v))(t0 + (i + 1) * pas)
        esp.tick()


def ansi_image(lignes, cols=160, rangs=None, taille=14):
    """Un terminal (lignes avec couleurs ANSI) dessiné dans une image."""
    rangs = rangs or len(lignes)
    cw, ch = int(taille * 0.6), int(taille * 1.35)
    im = Image.new("RGBA", (cols * cw + 40, rangs * ch + 40), (12, 14, 18, 255))
    L = []
    for i, l in enumerate(lignes[:rangs]):
        x = 20
        for s, c, g in E.spans(l, (210, 214, 222, 255)):
            L.append(("texte", x, 20 + ch * i + ch / 2, s, taille, c, g, "g", True))
            x += S.lt(s, taille, True)
    # l'inverse vidéo (\033[7m) n'est pas rendu : on garde les couleurs
    return S.vers_pil(L, im.size, image=im)


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    preparer()
    import tg.bureau_vie as V
    horloge = [1000.0]
    V.maintenant = lambda: horloge[0]
    esp = E.Espace(app.etape)
    esp.lignes = []
    esp.mini.dossier = str(core.TERRAIN)
    for l in ("ls", "cd grenier", "ls", "cat lianes.txt", "cat lianes.txt | grep -i gland"):
        taper(esp, l)
    avancer(esp, 3.4 + 1.2 * 3 + 2.4 * 0.1)
    # étape 4 (grep) allumée, la 2e ligne dans le tuyau
    esp.dep["actif"], esp.dep["t"], esp.dep["phase"] = 4, 0.5, 0.45
    esp.dep["auto"] = True
    esp.cv.forcer("mange")
    esp.cv.tour({"commande_tapee": True}, esp.t)
    esp.cv.forcer(None)
    esp.cv.etat = "mange"
    esp.c.changer("mange", 3)
    avancer(esp, 1.0)
    esp.dep["actif"], esp.dep["phase"] = 4, 0.62
    dessiner(esp, esp.t).convert("RGB").save(sortie / "espace_pc.png")
    # le cerveau : forcer « mange » et voir sa branche
    esp.onglet = "cerveau"
    esp.cv.forcer("mange")
    esp.cv.tour({"commande_tapee": False}, esp.t)
    esp.cv.t_tour = esp.t - 1.2
    esp.dep["actif"], esp.dep["phase"] = 4, 0.62
    dessiner(esp, esp.t).convert("RGB").save(sortie / "espace_cerveau_pc.png")
    # les tuyaux et la leçon
    esp.onglet = "tuyaux"
    dessiner(esp, esp.t).convert("RGB").save(sortie / "espace_tuyaux_pc.png")
    esp.onglet = "lecon"
    dessiner(esp, esp.t).convert("RGB").save(sortie / "espace_lecon_pc.png")
    # le mode classe (grand écran)
    esp.onglet = "carte"
    esp.classe = True
    dessiner(esp, esp.t).convert("RGB").save(sortie / "espace_classe.png")
    esp.classe = False
    # le mode texte (dans un grand terminal)
    lignes = E.ecran_texte(esp, 170, 48)
    ansi_image(lignes, 170, 48, 13).convert("RGB").save(sortie / "espace_texte.png")
    # tg deploie dans un terminal : l'image à l'étape du tuyau
    from tg import deploie as D
    dossier = str(core.TERRAIN / "grenier")
    ligne = "ls | grep a > liste.txt"
    bl = D.blocs(ligne, D.existe_dans(dossier))
    sorties = D.flux(ligne, D.lanceur(dossier), D.existe_dans(dossier))
    ansi_image(D.ecran(ligne, bl, 2, sorties, 0.45, 100, dossier), 100, None, 15).convert("RGB").save(
        sortie / "deploie_terminal_tuyau.png")
    ansi_image(D.ecran(ligne, bl, 5, sorties, 0.6, 100, dossier), 100, None, 15).convert("RGB").save(
        sortie / "deploie_terminal_redirection.png")
    # le GIF de la vue déployée (fenêtre) sur ls | grep a > liste.txt
    taper(esp, "ls | grep a > liste.txt")
    esp.dep["auto"] = True
    images = []
    for i in range(int(13.0 / 0.1)):
        avancer(esp, 0.1)
        L, Z, (W, H) = S.scene(esp.modele(), esp.t)
        im = S.vers_pil(L, (W, H)).crop((S.Mise().deploie[0] - 8, 88, S.Mise().deploie[0] + S.Mise().deploie[2] + 8,
                                         S.Mise().deploie[1] + S.Mise().deploie[3] + 8))
        images.append(im.convert("RGB").resize((im.width * 3 // 4, im.height * 3 // 4), Image.LANCZOS))
    images[0].save(sortie / "deploie.gif", save_all=True, append_images=images[1:], duration=100, loop=0,
                   optimize=True)
    images[60].save(sortie / "deploie_gif_image60.png")
    print("captures :", sorted(p.name for p in sortie.iterdir()))


if __name__ == "__main__":
    main()
