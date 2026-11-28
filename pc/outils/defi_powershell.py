"""Le défi de l'Atelier joué pour de vrai dans PowerShell (Windows) : la machine Windows de GitHub
(.github/workflows/windows.yml, Windows PowerShell 5.1 et PowerShell 7) lance la vraie boucle de l'enfant,
`1..20 | ForEach-Object { .\\cerveau.ps1; atelier pas }`, et ce script fait le reste du jeu : il prépare une partie
dans un dossier TEMPORAIRE, « voit » chaque ligne tapée (comme l'invite du compagnon, par l'historique de PowerShell)
et vérifie le VRAI résultat (la grille, les chocs, les cases explorées, l'exploit).

    python pc/outils/defi_powershell.py prepare [at3 1]  une partie neuve, l'Atelier ouvert, la leçon at4 à l'étape 3
                                                         (ou la leçon et l'étape demandées)
    python pc/outils/defi_powershell.py saute at4 3      passe à cette leçon et cette étape (les réponses qui changent
                                                         à chaque partie, la boucle infinie : déjà testées ailleurs)
    python pc/outils/defi_powershell.py dossier          affiche le dossier du robot (robots/ du terrain)
    python pc/outils/defi_powershell.py tape "LIGNE"     la ligne que l'enfant vient de taper : le jeu la lit
                                                         (ou sans argument : la ligne est dans TG_LIGNE)
    python pc/outils/defi_powershell.py attend at4 4     code 1 si la leçon n'en est pas là
    python pc/outils/defi_powershell.py indice politique code 1 si l'indice donné n'est pas at.ps.indice.politique
    python pc/outils/defi_powershell.py verifie          le défi réussi : 20 pas, aucun choc, ≥ 12 cases, l'exploit

Sécurité : refuse de tourner si le dossier personnel (USERPROFILE / HOME) et APPDATA ne sont pas des dossiers
temporaires créés pour le test (TG_DEFI_TEMP doit les désigner) : jamais la vraie partie ni le vrai historique.
Ne change jamais la politique d'exécution de Windows.
"""
import os
import re
import sys
from pathlib import Path

TEMP = os.environ.get("TG_DEFI_TEMP", "")
if not TEMP or not all(os.path.abspath(os.environ.get(v, "")).startswith(os.path.abspath(TEMP))
                       for v in ("USERPROFILE" if os.name == "nt" else "HOME", "APPDATA")):
    print("defi_powershell : USERPROFILE (ou HOME) et APPDATA doivent être dans TG_DEFI_TEMP (un dossier de test).")
    sys.exit(2)
os.environ.setdefault("LANG", "fr_FR.UTF-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tg import app, core, histoire, langue, recompenses  # noqa: E402
from tg import atelier as A  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def historique():
    """Le fichier d'historique que lit le jeu : celui de PowerShell (PSReadLine) sous Windows."""
    f = core.history_files()[-1]
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def placer(s, lid, step):
    h = histoire.h_(s)
    lecons_ = histoire.PAR_CHAP["robots"]["lecons"]
    for l_ in lecons_[:lecons_.index(lid)]:
        if l_ not in h["faits"]:
            h["faits"].append(l_)
    h["chap"] = "robots"
    s["step"] = step


def prepare(lid="at4", step=3):
    import builtins
    builtins.input = lambda p="": "Pixel"
    langue.definir("fr")
    app.creer_si_besoin(avec_intro=False)

    def ouvrir(s):
        h = histoire.h_(s)
        for c in ("reveil", "nid", "bibliotheque"):
            for l_ in histoire.PAR_CHAP[c]["lecons"]:
                if l_ not in h["faits"]:
                    h["faits"].append(l_)
        h["ailes"] = ["reveil", "nid", "bibliotheque"]
        h.setdefault("mondes_annonces", []).extend(histoire.MONDES_MODS)
        s["xp"] = 10 * 30 ** 2
        placer(s, lid, step)                   # par défaut at4 : « copy cerveau_exemple.ps1 cerveau.ps1 »
        s["langue"] = "fr"
    core.TERRAIN.mkdir(parents=True, exist_ok=True)
    core.modifier(ouvrir)
    st = tape("dir", cwd=str(core.TERRAIN))   # le jeu meuble l'Atelier (plan, robot/, cerveau_exemple.ps1)
    d = A.dossier()
    ok = (d / "cerveau_exemple.ps1").is_file() and (d / "robot" / "moteur").is_file()
    print(f"partie prête : {lecon(st)} ; {d} ; cerveau_exemple.ps1 : {'oui' if ok else 'NON'}")
    return 0 if ok and lecon(st) == (lid, step) else 1


def tape(ligne, cwd=None):
    with open(historique(), "a", encoding="utf-8") as f:
        f.write(ligne + "\n")
    st = app.etape(spontane=False, defis=False, cwd=cwd or os.getcwd(), statut=None)
    print(f"  [jeu] « {ligne} » → {lecon(st)}" + (f" · indice : {st['indice_lecon']}" if st.get("indice_lecon") else ""))
    return st


def attend(lid, step):
    st = core.load()
    ici = lecon(st)
    ok = ici == (lid if lid != "-" else None, int(step))
    print(("  ✔ " if ok else "  ✖ ") + f"leçon {ici}, attendu ({lid}, {step})")
    return 0 if ok else 1


def indice(nom):
    st = core.load()
    langue.appliquer(st)
    ok = st.get("indice_lecon") == langue.t("at.ps.indice." + nom)
    print(("  ✔ " if ok else "  ✖ ") + f"indice « {nom} » : {st.get('indice_lecon')!r}")
    return 0 if ok else 1


def verifie():
    st = core.load()
    a = A.a_(st)
    d = a.get("defi") or {}
    carnet = A.carnet()
    defis = re.findall(r"^\[defi\] .*\((\w+)\)$", carnet, re.M)
    journal = (A.dossier_robot() / "journal.txt").read_text(encoding="utf-8").splitlines()
    print("  la grille à la fin du défi :")
    for l in A.dessin_grille(d.get("arene", 0), a["robot"], d.get("vus", [])):
        print("    " + l)
    resultats = [
        (d.get("pas") == 20, f"20 pas joués par la boucle de PowerShell ({d.get('pas')})"),
        (d.get("chocs") == 0, f"aucun choc ({d.get('chocs')})"),
        (len(d.get("vus", [])) >= A.donnees()["defi"]["cases_min"], f"au moins 12 cases explorées ({len(d.get('vus', []))})"),
        (defis[-1:] == ["ok"], f"le carnet : défi réussi ({defis})"),
        ("atelier.robot" in recompenses.r_(st)["exploits"], "l'exploit « le robot qui évite tous les obstacles »"),
        ("at5" in histoire.h_(st)["faits"], f"la leçon du défi est finie ({lecon(st)})"),
        (len(journal) >= 30, f"le journal du robot : une ligne par pas ({len(journal)})"),
    ]
    for ok, msg in resultats:
        print(("  ✔ " if ok else "  ✖ ") + msg)
    return 0 if all(ok for ok, _ in resultats) else 1


def main(argv):
    quoi = argv[0] if argv else ""
    if quoi == "prepare":
        return prepare(argv[1], int(argv[2])) if len(argv) > 2 else prepare()
    if quoi == "saute":
        core.modifier(lambda s: placer(s, argv[1], int(argv[2])))
        return attend(argv[1], argv[2])
    if quoi == "dossier":
        print(A.dossier())
        return 0
    if quoi == "tape":                       # la ligne : en argument, ou dans TG_LIGNE (les guillemets passent intacts,
        tape(" ".join(argv[1:]) or os.environ.get("TG_LIGNE", ""))   # même avec Windows PowerShell 5.1)
        return 0
    if quoi == "attend":
        return attend(argv[1], argv[2])
    if quoi == "indice":
        return indice(argv[1])
    if quoi == "verifie":
        return verifie()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
