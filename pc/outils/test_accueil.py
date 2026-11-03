"""Test de l'accueil et de l'aide (PC, idées du 3 novembre, aide_douce.py) : « Qui est avec toi ? » et les conseils
(1), le premier ls (2), la flèche (4), le clavier (5), `perdu` (6), fermer et revenir (9), `ls ?` (22), les 3 niveaux
d'indice (25), la fin grisée du terminal du jeu (66), le menu rond au clavier et `tg menu` (69), le menu du jeu (79),
et les vecteurs communs avec Android (donnees/accueil/vecteurs.json, tests/jvm/Accueil.kt).

    python3 pc/outils/test_accueil.py          (crée son propre HOME temporaire)
"""
import builtins
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_accueil_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["TG_SANS_ANIM"] = "1"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import accueil, aide_douce as A, app, compagnon, core, entrainement, histoire, intro, langue, placement  # noqa: E402
from tg.langue import t  # noqa: E402

HOME = Path.home()
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def plat(x):
    x = "\n".join(x) if isinstance(x, list) else str(x)
    return re.sub(r"\s+", " ", langue.sans_marques(ANSI.sub("", x)))


def tape(*cmds, statut=0):
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        for c in cmds:
            f.write(c + "\n")
    core.DERNIER.update(ligne=None, statut=None)
    sys_argv = sys.argv
    sys.argv = ["tg", "prompt", f"--statut={statut}"]
    try:
        out = io.StringIO()
        with redirect_stdout(out):
            compagnon.prompt(app.etape)
        return out.getvalue()
    finally:
        sys.argv = sys_argv


print("0. Les vecteurs communs (Python = Kotlin)")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_accueil.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "donnees/accueil/vecteurs.json est à jour")
V = json.loads((RACINE / "donnees/accueil/vecteurs.json").read_text(encoding="utf-8"))
verifier(all(A.fleche(v["intro"], v["reussies"], v["depuis"]) == v["ok"] for v in V["fleche"]), "la flèche (idée 4)")
verifier(all(A.touche_a_allumer(v["attendu"], v["tape"]) == v["touche"] for v in V["touche"]), "la touche qui s'allume (idée 5)")
verifier(A.touche_a_allumer("ls sac | wc -l", "ls sac ") == "|" and A.touche_a_allumer("echo a >> b", "echo a ") == "⋯",
         "ls sac | wc -l → | s'allume ; >> est dans la deuxième rangée (⋯)")
verifier(A.demande_explique("ls ?") == "ls" and A.demande_explique("? ls") == "ls" and A.demande_explique("ls -a ?") is None,
         "`ls ?` et `? ls` demandent la fiche (pas `ls -a ?`)")
verifier(A.fantome("vest", ["nid/", "vestibule/", "reserve.txt"]) == "ibule/" and A.fantome("x", ["nid/"]) == "",
         "la fin grisée : seulement un nom qui existe")
verifier(A.parties_indice("grep -c pomme liste.txt") == {"cmd": "grep", "debut": "grep -c", "reponse": "grep -c pomme liste.txt"},
         "les 3 niveaux d'indice tirés de la commande attendue")
verifier(A.action_menu("4") == "options" and A.action_menu("5") == "aide" and A.action_menu("q") == "quitter",
         "le menu : 4 Options, 5 Aide, q Quitter")

print("1. Qui est avec toi ? (le tout premier lancement)")
(HOME / ".bash_history").touch()
reponses = iter(["2", "", "", "", "", "Pixou", ""])
builtins.input = lambda _i="": next(reponses)
out = io.StringIO()
with redirect_stdout(out):
    app.creer_si_besoin(avec_intro=True)
p = plat(out.getvalue())
st = core.load()
verifier(t("ad.parent.question") in p and t("ad.parent.adulte") in p, "la question et les deux choix")
verifier(t("ad.parent.c1.t") in p and t("ad.parent.c4.t") in p and "tg debloquer tout" in p, "avec un adulte : les 4 conseils")
verifier(st["name"] == "Pixou" and st["aide_douce"]["parent"] == "adulte", "puis l'histoire et le nom ; le choix est gardé")
verifier("parent" not in json.dumps(st.get("compte", {})), "rien n'est envoyé (le choix n'est pas dans le compte)")
with redirect_stdout(io.StringIO()) as o:
    sys.argv = ["tg", "aide", "parents"]
    app._main()
verifier(t("ad.parent.c2.t") in plat(o.getvalue()), "`tg aide parents` : les conseils à relire")
from tg import parties  # noqa: E402
verifier(not parties.aucune(), "une partie existe : la question ne sera plus posée (seulement la première fois)")

print("4. La flèche « tape ici » (les premières commandes)")
s = tape("ls")
verifier(t("ad.fleche.pc").split(",")[0] in plat(s), "▼ « tape ta commande ici » au-dessus de l'invite pendant l'œuf")
verifier(t("ad.ls.titre") in plat(s) and t("ad.ls.waouh").split("!")[0] in plat(s), "idée 2 : le premier ls, ses cases, « Waouh, j'y vois ! »")
s = tape("pwd")
s = tape("echo bonjour")
st = core.load()
verifier(st["aide_douce"]["reussies"] >= 3 and t("ad.fleche.pc").split(",")[0] not in plat(s), "3 commandes réussies : la flèche s'en va")
st["aide_douce"]["derniere"] = time.time() - 120
verifier(A.ligne_fleche(st) is not None, "1 minute sans rien taper pendant l'œuf : elle revient")
s = tape("ls")
verifier(t("ad.ls.titre") not in plat(s), "le premier ls ne se rejoue jamais")

print("22. ls ? : la fiche courte, jamais un repas")
tape("whoami")                                       # l'œuf éclot
total = core.load()["total"]
s = tape("ls ?", statut=2)
p = plat(s)
verifier(t("ad.q.ordi") in p and "ls, en mots d'enfant" in p and "ls --help" in p and "explique ls" in p,
         "l'erreur de l'ordinateur rassurée, puis la fiche (image, exemple, grands, joker, toute la fiche)")
verifier(core.load()["total"] == total, "`ls ?` ne nourrit pas")
s = tape("? cd")
verifier("cd, en mots d'enfant" in plat(s) and t("ad.q.ordi") not in plat(s), "`? cd` aussi (sans erreur de l'ordinateur)")

print("6. perdu")
lignes = plat(A.lignes_perdu(core.load(), str(HOME)))
verifier(t("ad.perdu.titre") in lignes and t("ad.perdu.ou") in lignes and t("ad.perdu.lecon_titre") in lignes,
         "Pas de panique : où es-tu, ta leçon")
verifier("cd ~" in lignes, "et comment revenir au camp")
with redirect_stdout(io.StringIO()) as o:
    sys.argv = ["tg", "perdu"]
    app._main()
verifier(t("ad.perdu.titre") in plat(o.getvalue()), "`tg perdu` (alias perdu) répond")
verifier("alias perdu='tg perdu'" in Path(compagnon.__file__).read_text(encoding="utf-8"), "alias perdu et indice dans le bloc du shell")
verifier("perdu" in core.BUILTINS and "indice" in core.BUILTINS, "perdu et indice sont des commandes du jeu (pas des fautes)")

print("5. Où est le symbole sur le clavier")
st = core.load()
l1 = plat(A.astuce_clavier(st, "ls sac | wc -l"))
verifier("le tuyau" in l1 and "AltGr + 6" in l1, "AZERTY en français : | = AltGr + 6")
verifier(A.astuce_clavier(st, "cat a | wc") == [], "une seule fois par symbole")
st["config"]["clavier"] = "qwerty"
verifier("Maj + \\" in plat(A.astuce_clavier(st, "echo a > b")) or "Maj + ." in plat(A.astuce_clavier({"config": {"clavier": "qwerty"}, "aide_douce": {}}, "echo a > b")),
         "QWERTY : > = Maj + .")

print("25. Trois niveaux d'indice")
core.modifier(lambda s: placement.p_(s))
verifier(t("ad.ind.rien").split(":")[0] in plat(A.lignes_indice(core.load())), "rien à deviner : la commande est en vert")
st = core.load()
st["entrainement"] = st.get("entrainement") or {}
core.TERRAIN.mkdir(exist_ok=True)
st["seen"] = list(set(st.get("seen", [])) | {"cd", "ls", "mkdir", "touch"})
lignes = entrainement.commencer(st, typ="bat_pieces")
core.save(st)
n1 = A.lignes_indice(st)
n2 = A.lignes_indice(st)
n3 = A.lignes_indice(st)
verifier("(1/3)" in plat(n1) and t("ad.ind.t1") in plat(n1), "1er appui : petit coup de pouce")
verifier("(2/3)" in plat(n2) and "mkdir" in plat(n2), "2e : plus clair (la commande)")
verifier("(3/3)" in plat(n3) and "mkdir " in plat(n3) and t("ad.ind.rien_retire") in plat(n3), "3e : la réponse, rien n'est retiré")
verifier(not A.fantome_permis(st), "pendant l'exercice : pas de fin grisée (elle soufflerait la réponse)")
st["entrainement"]["cours"] = None

print("9. Fermer et revenir (fin du tronc commun)")
st = core.load()
h = histoire.h_(st)
for c in ("reveil", "nid", "bibliotheque", "cave"):
    if c not in h["ailes"]:
        h["ailes"].append(c)
A.proposer_fermer(st)
verifier("fermer" in intro.d_(st)["file"], "l'écran « Tu peux fermer quand tu veux » attend son tour")
st["intro"]["vu_prompt"] = (st["intro"].get("evt") or [0, 0])[1]
lignes = intro.pour_prompt(st) if intro.a_montrer(st) == "fermer" else []
while intro.a_montrer(st) and intro.a_montrer(st) != "fermer":
    intro.lu(st)
    lignes = intro.pour_prompt(st)
verifier(t("ad.fermer.titre") in plat(lignes) and "exit" in plat(lignes), "PC : « tape exit, puis rouvre un terminal »")
verifier(A.retour(st, os.getppid()) is None, "dans le même terminal : rien")
r = A.retour(st, os.getppid() + 1)
verifier(r == t("ad.fermer.retour"), "un nouveau terminal : « Te revoilà ! »")
verifier(A.retour(st, 12345) is None and st["xp"] == core.load()["xp"], "une seule fois, sans récompense")

print("66. La fin grisée dans le terminal du jeu (vsh)")
from tg.vsh import terminal as T  # noqa: E402
term = T.Terminal(compagnon=False)
term.gris = True
(core.TERRAIN / "vestibule").mkdir(parents=True, exist_ok=True)
term.sh.cwd = term.vfs.pour_le_jeu(str(core.TERRAIN)) if hasattr(term.vfs, "pour_le_jeu") else str(core.TERRAIN)
g = term._fantome(list("cd vest"), 7)
verifier(g.startswith("ibule"), f"`cd vest` → « ibule » en gris ({g!r})")
verifier(term._fantome(list("cd vest"), 3) == "", "seulement au bout de la ligne")

print("69. Le menu rond du bureau, au clavier")
from tg import bureau, bureau_scene as S, bureau_vie as BV  # noqa: E402
c = bureau.Controleur.__new__(bureau.Controleur)
c.vue = S.VueCreature()
c.saisie_active = False
c.t = c.derniere_action = 0
faits = []
c.action = lambda a: faits.append(a)
verifier(c.touche_menu("entree") and c.vue.menu and c.vue.choix == 0, "Entrée ouvre le menu rond, le 1er bouton choisi")
c.touche_menu("droite")
c.touche_menu("droite")
c.touche_menu("entree")
verifier(faits == ["menu:" + BV.MENU[2][0]], "→ → Entrée : le 3e bouton")
c.touche_menu("echap")
verifier(not c.vue.menu and c.vue.choix is None, "Échap ferme")
with redirect_stdout(io.StringIO()) as o:
    sys.argv = ["tg", "menu"]
    app._main()
verifier(core.load().get("bureau_menu", 0) > 0 and "←" in o.getvalue(), "`tg menu` : le bureau ouvre son menu rond")

print("79. Le menu du jeu")
st = core.load()
m = plat(accueil.ecran_menu(st))
verifier(all(t(k).lower() in m.lower() for k in ("part.m.jouer", "part.m.nouvelle", "part.m.charger", "part.m.options", "part.m.aide_menu",
                                  "part.m.quitter")), "Jouer, Nouvelle partie, Charger, Options, Aide, Quitter")
verifier("▀█▀" in m and "Pixou" in m, "le titre en gros blocs, et la créature avec son nom")
verifier(accueil.action("4") == "options" and accueil.action("options") == "options" and accueil.action("") == "continuer",
         "4 / « options » ; Entrée = Jouer")
verifier(t("rec.sans_compte").split(".")[0] in plat(accueil.texte_options(st)), "le compte est dans les Options")
verifier(t("ad.parent.c1.t") in plat(accueil.texte_aide(st)) and t("ad.fermer.titre") in plat(accueil.texte_aide(st)),
         "l'Aide : les conseils pour les parents, fermer et revenir")
reps = iter(["5", "q"])
with redirect_stdout(io.StringIO()):
    verifier(accueil.menu(lambda _i="": next(reps)) is False, "5 puis q : l'aide, puis quitter")

print("Langues : toutes les clés existent dans les 14 langues")
D = {c: json.load(open(RACINE / f"pc/tg/langues/{c}.json", encoding="utf-8")) for c in langue.LANGUES}
cles = [k for k in D["fr"] if k.startswith("ad.")]
verifier(len(cles) > 60 and all(k in D[c] for c in D for k in cles), f"{len(cles)} clés « ad. » × 14 langues")

print(f"\n{ok} réussis, {ko} ratés")
sys.exit(0 if ko == 0 else 1)
