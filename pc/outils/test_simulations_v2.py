"""Non-régression (PC) des problèmes trouvés par les simulations de joueurs, 2e passage (docs/simulations/rapport_v2.md).

    python3 pc/outils/test_simulations_v2.py          (crée son propre HOME temporaire)

  C1. chapitre 2, « Remonte d'un cran : cd .. » : depuis le camp, `aide` ne dit plus « c'est le bon endroit » ; la
      commande montrée et l'indice mènent d'abord au vestibule ; `cd ..` depuis le vestibule valide l'étape ;
  C2. l'indice « … n'existe pas ici » n'a plus de phrase recopiable avec une apostrophe ; l'invite de suite (`>`) dit
      « Ctrl+C » (PS2 du bloc installé dans ~/.bashrc, syntaxe bash valide) ; l'œuf apprend Ctrl+C ;
  I1. `aide` : la leçon seulement (pas la notice), pas « commande inconnue » ; pendant l'œuf, sa prochaine commande ;
  I2. mode sans aide : pas de lignes « 🧑 » ni « 💻 », et un indice ne donne pas la commande cachée ;
  I3. un monstre en cours de dressage a sa ligne sous l'invite ;
  I5/I6. `exit` n'est pas un repas ; un alias créé par l'enfant n'est pas une « commande inconnue » ;
  C3 (PC aussi) : grep qui ne trouve rien → « aucune ligne ne contient… » au lieu de « une erreur ».
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_simv2_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, explo, histoire, intro, langue, placement, tirage  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
GRAINE = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"   # factice
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ENV = dict(os.environ, LC_ALL="C.UTF-8")
ok = ko = 0
terminal = [str(HOME)]


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    """Une vraie commande dans le « terminal » (bash), puis une étape de jeu depuis le nouveau dossier courant."""
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       timeout=30, env=ENV)
    lignes = r.stdout.strip().split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)


def texte(x):
    return langue.sans_marques(ANSI.sub("", "\n".join(x) if isinstance(x, list) else x))


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def niveau(n):
    core.modifier(lambda s: s.__setitem__("xp", max(s["xp"], 10 * (n - 1) ** 2)))


(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()
_tick = explo.tick
explo.tick = lambda st, sp, proba=0, jeu=0, lignes=(): _tick(st, sp, proba, 0, lignes)   # pas de monstre au hasard
core.modifier(lambda s: (s["config"].__setitem__("fenetre_dressage", False),
                         tirage.ranger_graines(s, [{"id": f"{tirage.jour_local()}.abcdef123456", "valeur": GRAINE}])))

print("I1. aide pendant l'œuf, et « aide » n'est pas une commande inconnue")
st = core.load()
st["intro"] = None
intro.nouvelle_partie(st)
core.save(st)
st = core.load()
a = texte(histoire.aide_lecon(st, str(HOME)))
verifier(intro.en_cours(st) and "pwd" in a and "Pas de leçon" not in a, f"pendant l'œuf, aide donne la commande suivante : {a!r}")
r = subprocess.run([sys.executable, str(RACINE / "pc"), "aide"], capture_output=True, text=True, env=dict(os.environ))
verifier("terminagotchi.pyz mini" not in r.stdout and "tg aide tout" in texte(r.stdout),
         "tg aide (avec une partie) : la leçon seulement, la liste du jeu reste dans tg aide tout")
r = subprocess.run([sys.executable, str(RACINE / "pc"), "aide", "tout"], capture_output=True, text=True)
verifier("terminagotchi.pyz mini" in r.stdout, "tg aide tout : la liste complète")
st = core.load()
core.feed(st, "aide", 0)
verifier("inconnue" not in texte(" ".join(st.get("terminal", []))), "« aide » (l'alias) n'est pas une commande inconnue")

print("C2. l'invite « > » et Ctrl+C")
st = core.load()
st["intro"]["faits"] = st["intro"]["faits"][:1] or ["pwd"]
verifier("Ctrl+C" in intro.astuce(st), f"l'œuf apprend Ctrl+C : {intro.astuce(st)!r}")
manque = texte(langue.t("lec.indice.manque", nom="nidsecours.txt"))
verifier("'" not in manque.replace("nidsecours.txt", "") and "`" not in manque, f"indice sans apostrophe : {manque!r}")
for code in ("fr", "en", "it", "es"):
    langue.definir(code)
    blocs = compagnon._blocs()
    bash = next(b for p, b in blocs.items() if p.name == ".bashrc")
    syntaxe = subprocess.run(["bash", "-n"], input=bash, capture_output=True, text=True)
    ps2 = subprocess.run(["bash", "-c", "\n".join(l for l in bash.split("\n") if l.startswith("PS2=")) + '\necho "${PS2@P}"'],
                         capture_output=True, text=True).stdout
    verifier(syntaxe.returncode == 0 and "Ctrl+C" in ps2, f"{code} : bloc bash valide, l'invite de suite dit {ps2.strip()!r}")
langue.definir("fr")
if (HOME / ".bashrc").exists():
    (HOME / ".bashrc").write_text((HOME / ".bashrc").read_text().replace("PS2=", "#"), encoding="utf-8")
(HOME / ".bashrc").write_text(compagnon.DEBUT + "\n__tg_prompt --statut\n" + compagnon.FIN + "\n", encoding="utf-8")
verifier(not compagnon.a_jour(), "un ancien bloc sans PS2 est remis à jour")

print("C1. chapitre 2 : remonter d'un cran vers le carrefour")
st = core.load()
st["intro"] = None
core.save(st)
st = tape("date")
niveau(2)
for c in ("pwd", "ls", "cd ~", "cd terrain_terminagotchi", "ls", "cd vestibule", "ls", "cd /", "ls", "pwd", "cd ~",
          f"cd {T / 'vestibule'}"):
    st = tape(c)
niveau(3)
verifier(lecon(st) == ("nid0", 0), f"chapitre 2, étape « cd .. » : {lecon(st)}")
st = tape("cd")
a = texte(histoire.aide_lecon(st, str(HOME)))
verifier("C'est le bon endroit" not in a and "~/terrain_terminagotchi/vestibule puis" in a,
         f"depuis le camp, aide mène d'abord au vestibule : {a!r}")
verifier("vestibule" in texte(compagnon.commande_montree(st, histoire.lecon_courante(st)[0]["steps"][0], str(HOME))),
         "la commande montrée sous l'invite commence par le cd du vestibule")
st = tape("cd ..")
verifier(lecon(st) == ("nid0", 0) and "cd ~/terrain_terminagotchi/vestibule" in (st.get("indice_lecon") or ""),
         f"cd .. depuis le camp : l'indice dit de partir du vestibule ({st.get('indice_lecon')!r})")
st = tape("cd /")
a = texte(histoire.aide_lecon(st, "/"))
verifier("C'est le bon endroit" not in a, "à la Racine non plus, ce n'est pas « le bon endroit »")
st = tape("cd ~/terrain_terminagotchi/vestibule")
a = texte(histoire.aide_lecon(st, str(T / "vestibule")))
verifier("C'est le bon endroit" in a, "au vestibule : c'est le bon endroit")
st = tape("cd ..")
verifier(lecon(st) == ("nid0", 1), f"cd .. depuis le vestibule : le carrefour, étape suivante ({lecon(st)})")

print("C3. grep qui ne trouve rien")
r = histoire.grep_rien("cat courses.txt | grep pomme")
verifier(r and "pomme" in r and "cat courses.txt" in r, f"grep sans résultat : {r!r}")
verifier(histoire.grep_rien("grep -rn TRESOR .") is None, "grep -r : pas de « cat . »")

print("I5/I6. exit, alias")
st = core.load()
xp = st["xp"]
core.feed(st, "exit", 0)
verifier(st["xp"] == xp and "exit" not in st["seen"], "exit n'est pas un repas (ni nouveau goût)")
core.feed(st, "alias miam='echo Miam'", 0)
st["terminal"] = []
core.feed(st, "miam", 0)
verifier(not any("inconnue" in x or "voulais dire" in x for x in st.get("terminal", [])),
         "un alias créé par l'enfant n'est pas une commande inconnue")
core.save(st)

print("I2. mode sans aide")
st = core.load()
st.setdefault("config", {})["sans_aide"] = True
st["term_etape"] = None
step = histoire.lecon_courante(st)[0]["steps"][st["step"]]
verifier(placement.cache(st, step), f"la commande de l'étape est cachée ({step['cmd']})")
lignes = texte(compagnon.annonces(st))
verifier("🧑" not in lignes and "💻" not in lignes and step["cmd"] not in lignes,
         f"pas de 🧑 ni de 💻 qui donnent la commande : {lignes!r}")
verifier(step["cmd"] not in placement.masquer(st, step, f"essaie `{step['cmd']}`"), "un indice ne donne pas la commande")
st["config"]["sans_aide"] = False
core.save(st)

print("I3. le monstre en cours de dressage, sous l'invite")
st = core.load()
from tg import bestiaire as B, dressage  # noqa: E402
e = next(iter(B.publiques()), None)
if e is not None:
    zone = "grenier"
    ind = B.individu(e, False, zone, "classique")
    s = {"f": dressage.fiche(e["nom"]).name, "e": e["nom"], "zone": zone, "shiny": False, "v": "classique", "ind": ind}
    st["sauvages"].append(s)
    dressage.commencer(st, s)
    st["prompt_vu"] = st.get("nlog", 0)
    l = texte(compagnon.ligne(st))
    verifier(e["nom"] in l and "🐾" in l, f"la ligne sous l'invite montre l'épreuve : {l!r}")
else:
    verifier(False, "pas d'espèce trouvée pour le dressage")

print("I9. les fautes d'enfant")
from tg import verif  # noqa: E402
st = core.load()
st["terminal"] = []
core.feed(st, "pwd,", 127)
verifier(any("« pwd »" in texte(x) for x in st["terminal"]), f"pwd, → tu voulais dire pwd : {st['terminal']}")
st["terminal"] = []
core.feed(st, "bonjour", 127)
verifier(any("echo bonjour" in texte(x) for x in st["terminal"]), f"bonjour → echo bonjour : {st['terminal']}")
verifier(verif.barre_oubliee("nidrepas.txt", str(T)) == "nid/repas.txt" or not (T / "nid" / "repas.txt").exists(),
         "nidrepas.txt → nid/repas.txt")
(T / "nid").mkdir(exist_ok=True)
(T / "nid" / "repas.txt").touch()
verifier(verif.barre_oubliee("nidrepas.txt", str(T)) == "nid/repas.txt", "nidrepas.txt → nid/repas.txt (le nid existe)")
m = verif.morceaux("touch nidlit.txt", str(T), 0)
b = histoire._indice_barre({"cmd": "touch nid/lit.txt"}, m)
verifier(b and "nid/lit.txt" in b, f"touch nidlit.txt : la barre oubliée ({b!r})")

print(f"\n{ok} réussis, {ko} ratés")
sys.exit(1 if ko else 0)
