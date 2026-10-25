"""Parcours automatique de Terminagotchi (PC) dans un dossier personnel temporaire.

    HOME=$(mktemp -d) LANG=ja_JP.UTF-8 python3 pc/outils/parcours.py [--court]

Crée une créature (la langue vient de LANG au premier lancement), fait les leçons du tronc
commun en écrivant de vraies commandes dans l'historique, force l'apparition d'un monstre,
affiche le face-à-face du dressage, la recherche, le lexique, l'aide, la troupe, la collection
et une animation. S'arrête avec une erreur si une clé de langue s'affiche au lieu d'un texte,
ou si une ligne de cadre n'a pas la bonne largeur à l'écran.
"""
import builtins
import os
import re
import sys
import tempfile
from pathlib import Path

if Path.home() == Path(os.path.expanduser("~")) and "--force-home" not in sys.argv:
    pass
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tg import app, core, dressage, equipe, explo, langue, lexique, registre, sprites  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
COURT = "--court" in sys.argv
erreurs = []


def montrer(titre, lignes):
    texte = lignes if isinstance(lignes, str) else "\n".join(lignes)
    propre = ANSI.sub("", texte)
    if not COURT:
        print(f"\n===== {titre} =====")
        print(texte)
    fr = langue._charger("fr")
    for k in re.findall(r"\b[a-z_]+(?:\.[\w-]+)+\b", propre):
        if k in fr:
            erreurs.append(f"{titre} : clé affichée telle quelle : {k}")
    for l in propre.split("\n"):
        if l.startswith("── ") and "─" * 3 in l:
            if langue.largeur(l) < 47:
                erreurs.append(f"{titre} : cadre trop court ({langue.largeur(l)} colonnes) : {l}")


def historique(*cmds):
    with open(Path.home() / ".bash_history", "a", encoding="utf-8") as f:
        for c in cmds:
            f.write(c + "\n")
    return app.etape(spontane=False, defis=False)


def main():
    if not str(Path.home()).startswith(tempfile.gettempdir()) and "--force-home" not in sys.argv:
        sys.exit("À lancer avec un HOME temporaire : HOME=$(mktemp -d) python3 pc/outils/parcours.py")
    (Path.home() / ".bash_history").touch()
    builtins.input = lambda invite="": (print(invite + "Test"), "Test")[1]
    app.creer_si_besoin()
    st = core.load()
    print(f"Langue détectée : {st['langue']} ({langue.LANGUES[st['langue']]}) · LANG={os.environ.get('LANG')}")
    montrer("fenêtre (début)", app.render(st, 0, True))
    T = core.TERRAIN
    # tronc commun : de vraies commandes, et les dossiers qu'elles auraient créés
    st = historique("pwd", "ls", "cd ~", "date", "whoami", "uname", "hostname", "df", "id")
    montrer("fenêtre (leçon 1)", app.render(st, 1, True))
    T.mkdir(exist_ok=True)
    (T / "nid").mkdir(exist_ok=True)
    st = historique("mkdir terrain_terminagotchi", "cd terrain_terminagotchi", "mkdir nid", "cal", "uptime")
    (T / "nid" / "repas.txt").write_text("pomme\n", encoding="utf-8")
    st = historique("echo pomme > nid/repas.txt", "cat nid/repas.txt", "grep pomme nid/repas.txt")
    montrer("fenêtre (leçons)", app.render(st, 2, True))
    # copier-coller (piège) et commande inconnue
    st = historique("lѕ", "blablabla")
    montrer("fenêtre (copier-coller)", app.render(st, 3, True))
    # un monstre apparaît : le face-à-face
    core.modifier(lambda s: (s["skills"].append("Bâtisseur") if "Bâtisseur" not in s["skills"] else None))
    st = core.modifier(lambda s: explo.spawn(s) if s.get("explo") else (s.__setitem__("explo", True), explo.spawn(s)))
    st = core.load()
    core.migrate(st)
    if st.get("dressage"):
        st["dressage"]["fenetre"] = True
        montrer("dressage", app.render_dressage(st, True))
        nom = st["dressage"]["espece"]
        st = historique(f"cat ~/terrain_terminagotchi/monstre_{nom.lower()}.txt")
        if st.get("dressage"):
            montrer("dressage (fiche lue)", app.render_dressage(st, True))
        fiche = dressage.fiche(nom)
        if fiche.exists():
            montrer("fiche du monstre (cat)", fiche.read_text(encoding="utf-8"))
        # on réussit le dressage d'office pour voir la suite
        st = core.modifier(dressage.reussir)
        montrer("fenêtre (capture)", app.render(st, 4, True))
    else:
        erreurs.append("aucun monstre n'est apparu")
    montrer("troupe", equipe.ecran_equipe(core.load()))
    montrer("collection", explo.ecran_collection(core.load()))
    caps = core.load().get("captures", [])
    if caps:
        montrer("bestiaire", explo.fiche(core.load(), caps[-1]["espece"]))
        r = equipe.animation(caps[-1], "victoire")
        if not r:
            erreurs.append("animation impossible pour " + caps[-1]["espece"])
    frames, _ips = sprites.animation(core.load(), "mange")
    montrer("animation (mange, image 5)", frames[5])
    montrer("lexique", lexique.lignes(core.load()))
    montrer("aide", app.aide())
    for q in (langue.t("reg.r.creer_dossier_entrer"), "grep", "supprimer un dossier"):
        montrer(f"recherche « {q} »", registre.afficher(registre.chercher(q), "Test"))
        if not registre.chercher(q):
            erreurs.append(f"la recherche « {q} » ne trouve rien")
    montrer("options (langues)", app.liste_langues())
    if erreurs:
        print("\n".join(" ✖ " + e for e in erreurs))
        sys.exit(1)
    print(f"\n✔ parcours terminé sans erreur ({langue.courante()})")


if __name__ == "__main__":
    main()
