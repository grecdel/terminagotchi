"""Non-régression (PC) des problèmes trouvés par les simulations de joueurs, 3e passage (docs/simulations/rapport_v3.md).

    python3 pc/outils/test_simulations_v3.py          (crée son propre HOME temporaire)

  I11. pendant l'œuf, l'invite garde l'astuce du moment (« pas grave », Ctrl+C, ↑, Tab) après la 1re commande ;
  I12. pas de faux « n'est pas une commande » : `pwd; ls` (le ; collé) ; `cd/home/…/vestibule` → « cd /home/… » ;
  I13. un lieu d'habitat a un vrai nom (« Atelier des engrenages »), un dossier inconnu garde son nom, jamais la clé ;
  I14. « non » reste reconnu dans les 14 langues ; le nom de l'œuf se donne avec echo (echo bonjour n'est pas un nom) ;
  I15. les écrans du début ne demandent plus de nom (9 nov. : le nom se donne avec `echo <nom>`) ;
  I16. l'épreuve du monstre en cours reste sous l'invite même quand la commande a laissé un message.
"""
import os
import re
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_simv3_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, intro, langue, maison  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def texte(x):
    return langue.sans_marques(ANSI.sub("", "\n".join(x) if isinstance(x, list) else x))


def reponses(*r):
    """Un faux clavier : chaque appel rend la réponse suivante (et note les questions posées)."""
    file, questions = list(r), []

    def demander(q=""):
        questions.append(texte(q))
        return file.pop(0) if file else ""
    return demander, questions


(Path.home() / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()
_tick = explo.tick
explo.tick = lambda st, sp, proba=0, jeu=0, lignes=(): _tick(st, sp, proba, 0, lignes)   # pas de monstre au hasard

print("I14. le nom de l'œuf (9 nov. : il se donne avec echo, plus de question ni de confirmation)")
for r in ("non", "Non", "n", "no", "nein", "いいえ"):
    verifier(intro.non(r), f"« {r} » = non")
for r in ("Krokmou", "oui", "", "nono"):
    verifier(not intro.non(r), f"« {r} » n'est pas non")
verifier(intro.nom_echo("echo non") == "Non" and intro.nom_echo("echo Tom le dragon") == "Tom le dragon"
         and intro.nom_echo("echo bonjour") is None, "echo Tom le dragon : un nom ; echo bonjour : pas un nom")

print("I15. les écrans du début ne demandent plus de nom")
n = len(intro.donnees()["ecrans"])
d, q = reponses(*([""] * (n - 1) + ["Zigzag"]))
verifier(intro.jouer_ecrans(d) is None and not any("appeler ton œuf" in x for x in q),
         "un mot tapé sur le dernier écran n'est pas un nom ; aucune question de nom")
d, q = reponses("p")
verifier(intro.jouer_ecrans(d) is None and len(q) == 1, "« p » passe les écrans")

print("I11. l'astuce de l'œuf reste sous la liste")
st = core.load()
st["intro"] = None
intro.nouvelle_partie(st)
core.save(st)
st = core.load()
i = intro.i_(st)
i["faits"] = ["pwd"]
i["eveil"] = time.time() - 60
i["evt"] = [1, time.time() - 60]
bloc = texte(intro.bloc_prompt(st, time.time()))
verifier("Ctrl+C" in bloc and "💡" in bloc, "après pwd : l'astuce (Ctrl+C) est sous la liste")
i["faits"] = ["pwd", "ls"]
i["evt"] = [2, time.time() - 60]
bloc = texte(intro.bloc_prompt(st, time.time()))
verifier("↑" in bloc, "après ls : l'astuce de la flèche ↑")
i["faits"] = ["pwd", "ls", "echo"]
i["evt"] = [3, time.time() - 60]
verifier("Tab" in texte(intro.bloc_prompt(st, time.time())), "après echo : l'astuce de Tab")
st["intro"] = None
core.save(st)

print("I12. pas de faux « n'est pas une commande »")
st = core.load()
for ligne, statut in (("pwd; ls", 0), ("pwd;ls", 0), ("ls|wc -l", 0)):
    st["terminal"] = []
    core.feed(st, ligne, statut)
    verifier(not any("pas une commande" in texte(x) for x in st["terminal"]), f"{ligne!r} : pas d'erreur ({st['terminal']})")
for ligne, attendu in (("cd/home/lea/terrain_terminagotchi/vestibule", "cd /home/lea/terrain_terminagotchi/vestibule"),
                       ("cd/", "cd /"), ("ls/etc", "ls /etc")):
    st["terminal"] = []
    core.feed(st, ligne, 127)
    m = texte(" ".join(st["terminal"]))
    verifier(attendu in m and "« vestibule »" not in m, f"{ligne!r} → {m!r}")
verifier(core.first_word("pwd;") == "pwd" and core.first_word("ls|wc") == "ls", "first_word coupe au ; et au |")
core.save(st)

print("I13. les lieux sans nom traduit")
# suite du rapport v3 : les lieux d'habitat ont maintenant de vrais noms (14 langues), jamais la clé brute
verifier(maison.nom_piece("mecanique") == "Atelier des engrenages", f"mecanique : {maison.nom_piece('mecanique')!r}")
verifier(maison.nom_piece("eau_petillante") == "Source pétillante", f"eau_petillante : {maison.nom_piece('eau_petillante')!r}")
verifier(maison.nom_piece("dossier_perso") == "dossier perso", "un dossier sans nom garde son nom de dossier")
verifier(maison.nom_piece("grenier") == "Grenier", "grenier : Grenier")
verifier(maison.nom_piece("jeu") == "Salle de jeu", "jeu : Salle de jeu")

print("I16. le monstre reste sous l'invite après un message")
from tg import bestiaire as B, dressage  # noqa: E402
st = core.load()
e = next(iter(B.publiques()), None)
if e is not None:
    zone = "grenier"
    ind = B.individu(e, False, zone, "classique")
    s = {"f": dressage.fiche(e["nom"]).name, "e": e["nom"], "zone": zone, "shiny": False, "v": "classique", "ind": ind}
    st["sauvages"].append(s)
    dressage.commencer(st, s)
    core.feed(st, "ls", 0)                          # « a mangé « ls » » : un message tout neuf
    verifier(st.get("nlog", 0) > st.get("prompt_vu", 0), "la commande a laissé un message")
    l = texte(compagnon.ligne(st))
    verifier(e["nom"] in l and "🐾" in l and "a mangé" in l, f"le message ET l'épreuve : {l!r}")
else:
    verifier(False, "pas d'espèce trouvée pour le dressage")

print(f"\n{ok} réussis, {ko} ratés")
sys.exit(1 if ko else 0)
