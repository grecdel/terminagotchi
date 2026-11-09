"""Allègement du 9 novembre, variante B « terminal + mission » (PC).

    python3 pc/outils/test_mission.py          (crée son propre HOME temporaire)

  1. les vecteurs communs (la ligne 🎯 et l'humeur : Python = Kotlin) ;
  2. la ligne 🎯 suit la partie : défi éclair, terrain effacé, leçon, niveau qui manque ;
  3. la fenêtre `tg` : le nom, UNE humeur, UNE barre, la bulle, la ligne 🎯, le journal ; le reste derrière [+] et [f]
     (rien n'est perdu : la leçon en détail et la fiche de la créature ont tout ce que l'écran montrait avant) ;
  4. le terminal de l'enfant : 2 lignes du jeu au plus après une commande ; le reste dans `tg detail` ;
  5. le réglage « terminal pur » (variante A) ;
  6. les textes existent dans les 14 langues.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_mission_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["COLUMNS"] = "100"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, envies, histoire, intro, langue, mission  # noqa: E402
from tg.langue import t  # noqa: E402
from tg.plateforme import piege  # noqa: E402

langue.definir("fr")
HOME = Path.home()
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def plat(x):
    """Sans couleurs ni marques, et sans les lettres sosies (anti copier-coller : plateforme.piege)."""
    x = "\n".join(x) if isinstance(x, list) else str(x)
    x = langue.sans_marques(ANSI.sub("", x))
    from tg.plateforme import HOMO
    for a, b in HOMO.items():
        x = x.replace(b, a)
    return x


print("1. Les vecteurs communs (Python = Kotlin)")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_mission.py"), "--verifier"], capture_output=True)
verifier(r.returncode == 0, "donnees/mission/vecteurs.json est à jour")
V = json.loads((RACINE / "donnees/mission/vecteurs.json").read_text(encoding="utf-8"))
verifier(all(mission.formater(c["genre"], **c["v"]) == c["ligne"] for c in V["mission"]), "mission.formater")
verifier(V["mission"][3]["ligne"] == "🎯 Où suis-je ? (1/3) · tape `pwd`", "la ligne 🎯 d'une leçon : « 🎯 Où suis-je ? (1/3) · tape `pwd` »")

print("2. La ligne 🎯 suit la partie")
st = core.new_state("Pixel")
core.migrate(st)
st["config"]["langue"] = "fr"
intro.nouvelle_partie(st)
for c in ["pwd", "ls", "echo", "whoami"]:
    intro.i_(st)["faits"].append(c)
intro.finir(st)
intro.d_(st)["file"] = []
st["total"] = 4
st["log"] = ["12:00 pwd · ls · echo bonjour · whoami", "12:01 🐣 Pixel est né !"]
les, _ = histoire.lecon_courante(st)
verifier(les is not None and mission.choisir(st)[0] in ("lecon", "niveau"), f"après l'éclosion : une leçon ({les and les['id']})")
m = mission.ligne(st)
step = les["steps"][st["step"]]
verifier(m.startswith("🎯") and step["cmd"][:2] in plat(m), f"la ligne : {plat(m)}")
st2 = json.loads(json.dumps(st))
st2["terrain_perdu"] = {"cmd": "mkdir -p ~/terrain_terminagotchi/nid"}
verifier(mission.choisir(st2)[0] == "terrain" and t("app.terrain.titre") in mission.ligne(st2), "le terrain effacé passe devant")
st2["defi"] = {"cmd": "whoami", "start": __import__("time").time()}
verifier(mission.choisir(st2)[0] == "defi" and "whoami" in plat(mission.ligne(st2)), "le défi éclair passe devant tout")

print("3. La fenêtre tg (variante B)")
ecran = plat(app.render(st, 0, True))
verifier("Pixel" in ecran and envies.emoji(st) in ecran, "le nom et UNE humeur (emoji)")
verifier("🎯" in ecran and step["dit"] if isinstance(step["dit"], str) else True, "la ligne 🎯")
verifier("🧑" not in ecran and t("app.caractere", trait="")[:5] not in ecran, "« Pour les grands » et le caractère ne sont plus à l'écran")
verifier(t("app.touches.b", nom="Pixel") in ecran, "les touches [+] et [f] au pied")
detail = plat(app.lignes_lecon(st))
verifier("🧑" in detail and "➜" in detail, "[+] la leçon en détail : la commande et 🧑 pour les grands")
fiche = plat(app.lignes_fiche(st))
verifier(t("app.caractere", trait=core.nom_trait(st["trait"])) in fiche and "XP" in fiche, "[f] la fiche : caractère et XP")
tout = plat(app.render_tout(st, 0, True))
verifier(all(x in tout for x in (ecran.split("\n")[-1], "🧑")), "render_tout : l'écran, puis [+] et [f]")

print("4. Le terminal de l'enfant : 2 lignes au plus")
core.save(st)
(HOME / ".bash_history").write_text("")


def tape(*cmds, statut=0):
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        for c in cmds:
            f.write(c + "\n")
    core.DERNIER.update(ligne=None, statut=None)
    argv = sys.argv
    sys.argv = ["tg", "prompt", f"--statut={statut}"]
    try:
        out = io.StringIO()
        with redirect_stdout(out):
            compagnon.prompt(app.etape)
        return out.getvalue()
    finally:
        sys.argv = argv


for c in ("date", "date"):
    s = tape(c)
    lignes = [x for x in plat(s).split("\n") if x.strip()]
    verifier(len(lignes) <= 2, f"après « {c} » : {len(lignes)} ligne(s) du jeu")
s = plat(tape(step["cmd"]))
lignes = [x for x in s.split("\n") if x.strip()]
st = core.load()
verifier(len(lignes) <= 2 and lignes and "➜" in lignes[-1], f"une étape réussie : 2 lignes, « ➜ » en dernier ({lignes[-1:]})")
verifier(any("🧑" in plat(x) or "📖" in plat(x) for x in st.get("annonces_detail", [])), "le texte de l'étape et 🧑 : dans `tg detail`")
o = io.StringIO()
with redirect_stdout(o):
    sys.argv = ["tg", "detail"]
    app._main()
verifier(t("ui.detail.dit") in plat(o.getvalue()), "`tg detail` montre ce que le terminal n'a pas montré")
o = io.StringIO()
with redirect_stdout(o):
    sys.argv = ["tg", "fiche"]
    app._main()
verifier("XP" in plat(o.getvalue()), "`tg fiche` : la fiche de la créature")
s = plat(tape("commande_qui_nexiste_pas", statut=127))
lignes = [x for x in s.split("\n") if x.strip()]
verifier(len(lignes) <= 2, "une erreur : toujours 2 lignes au plus (l'explication, puis « ➜ »)")

print("5. Terminal pur (variante A)")
st = core.load()
st["config"]["affichage"] = "pur"
pur = plat(app.render(st, 0, True))
verifier("🎯" in pur and "▀" not in pur and "▄" not in pur, "la fenêtre : le journal et la consigne, sans le dessin")
st["config"]["affichage"] = None
verifier("▀" in plat(app.render(st, 0, True)) or "▄" in plat(app.render(st, 0, True)), "et de retour : la créature")

print("6. Les textes dans les 14 langues")
cles = ["mis.tape", "mis.niveau", "mis.a_toi", "mis.plus", "ui.fiche.titre", "ui.lecon.titre", "ui.lecon.vide",
        "ui.detail.dit", "ui.fiche.album_pc", "app.touches.b", "ui.reg.pur.pc", "ui.reg.pur.aide", "ui.pur.on.pc",
        "ui.pur.off.pc"]
manque = []
for f in sorted((RACINE / "pc/tg/langues").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    manque += [f"{f.stem}:{c}" for c in cles if not d.get(c)]
verifier(not manque, "toutes les clés existent" + (f" (manque : {manque[:5]})" if manque else ""))

print(f"\n{ok} réussis, {ko} ratés")
sys.exit(1 if ko else 0)
