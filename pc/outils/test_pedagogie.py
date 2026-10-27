"""Tests de non-régression des retours « pédagogie » des simulations d'enfants (PC).

    python3 pc/outils/test_pedagogie.py          (crée son propre HOME temporaire)

Chaque section correspond à un défaut trouvé par les personas (Léa 7 ans, Tom 9 ans, Inès 12 ans, Hugo 15 ans,
Sophie parent débutante) : voir docs/programme.md (§ 3, écarts G-34 et suivants).
De vraies commandes sont lancées avec bash ; leur code de sortie est passé au jeu comme le fait le crochet
d'invite (`tg prompt --statut=$?`).
"""
import builtins
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_peda_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, explo, histoire, langue, lecons, maison  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def propre(x):
    from tg.plateforme import HOMO, NBSP
    inv = {v: k for k, v in HOMO.items()}
    x = langue.sans_marques(ANSI.sub("", x if isinstance(x, str) else "\n".join(x)))
    return "".join(inv.get(c, c) for c in x).replace(NBSP, " ")


(HOME / ".bash_history").touch()
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin(avec_intro=False)
_tick = explo.tick
explo.tick = lambda st, sp, proba=0, jeu=0, lignes=(): _tick(st, sp, proba, 0, lignes)

# ====================================================================== 1. le défi éclair raté ne gèle plus le jeu
print("1. Défi éclair raté (P1-1 : t() caché par une variable locale)")
core.modifier(lambda s: s.__setitem__("defi", {"cmd": "pwd", "start": time.time() - 999}))
try:
    core.modifier(lambda s: core.defi_tick(s, ["ls"], spontaneous=False))
    plante = None
except Exception as e:                              # noqa: BLE001
    plante = e
st = core.load()
verifier(plante is None, f"defi_tick ne plante pas quand le défi expire ({plante!r})")
verifier(st["defi"] is None, "le défi raté est effacé (la partie continue)")
core.modifier(lambda s: s.__setitem__("defi", {"cmd": "pwd", "start": time.time() - 1}))
core.modifier(lambda s: core.defi_tick(s, ["pwd"], spontaneous=False))
verifier(core.load()["defi"] is None and "pwd" in core.load()["records"], "défi réussi : record noté")

# ====================================================================== 2. valider sur le résultat
from tg import compagnon, verif  # noqa: E402
from tg.coquille import Coquille  # noqa: E402

SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8"))
sortie = [""]


def tape(cmd):
    """Une commande dans un vrai shell qui reste ouvert ; son code de sortie est passé au jeu (comme l'invite)."""
    sortie[0], code, d = SH.lancer(cmd)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=d, statut=code)


def lec():
    st = core.load()
    les, _ = histoire.lecon_courante(st)
    return (les["id"] if les else None), st["step"]


def aller(chap, faites, lid, step=0):
    """Place la partie au début d'une leçon (chapitres d'avant finis), comme si l'enfant y était arrivé."""
    def f(s):
        h = histoire.h_(s)
        h["ailes"] = [c for c in ("reveil", "nid") if c != chap]
        h["faits"] = ["t0", "reveil1", "racine", "nid0", "debarras", "nid1", "secrets"] + faites
        h["chap"], h["ouverts"] = chap, list(h["ailes"]) + [chap]
        s["step"], s["xp"] = step, max(s["xp"], 10 * 12 ** 2)
        s["annonce"] = histoire.lecon_def(lid)["titre"]
    core.modifier(f)
    (T / "nid").mkdir(parents=True, exist_ok=True)
    if not (T / "nid" / "repas.txt").exists():
        (T / "nid" / "repas.txt").write_text("pomme\n")
    tape("true")


def indice():
    return propre(core.load().get("indice_lecon") or "")


print("2. Validé sur le résultat, pas sur le texte (G-34)")
core.modifier(lambda s: s.__setitem__("xp", 10 * 1 ** 2 + 5))
verifier(lec() == ("t0", 0), f"la leçon 1 commence ({lec()})")
tape("PWD")
verifier(lec() == ("t0", 0), "`PWD` (command not found) ne valide pas « pwd »")
verifier("minuscules" in propre(core.load().get("terminal", [""])[-1:] or [""]) or "minuscules" in indice(),
         f"… et l'enfant lit que les commandes s'écrivent en minuscules ({indice()!r})")
tape("pwd")
tape("Ls")
verifier(lec() == ("t0", 1), "`Ls` ne valide pas « ls »")
tape("ls")
tape("cd ~")
verifier(lec()[0] == "reveil1", f"pwd, ls, cd ~ : leçon 1 finie ({lec()})")
tape("cd terrain_terminagotchi && ls")
verifier(lec() == ("reveil1", 2), f"`cd terrain_terminagotchi && ls` valide les deux étapes d'un coup ({lec()})")
tape("cdvestibule")
st = core.load()
verifier(any("cd vestibule" in propre(x) for x in st.get("terminal", [])) or "cd vestibule" in propre(
    (st.get("bubble") or [""])[0] + " ".join(b[0] for b in st.get("bulles", []))),
    "`cdvestibule` → « tu voulais dire cd vestibule ? » (faute collée)")
tape("cd vestibule; ls")
verifier(lec()[0] == "racine", f"`cd vestibule; ls` : chapitre 1, puis la Racine ({lec()})")
tape("cd / && ls")
verifier(lec() == ("racine", 2), f"`cd / && ls` valide 2 étapes ({lec()})")
tape("cd -")
verifier(lec() == ("racine", 2) and "cd -" in indice(), f"`cd -` (au lieu de pwd) : l'indice explique cd - ({indice()!r})")
for c in ("cd /", "pwd", "cd ~", f"cd {T / 'vestibule'}"):
    tape(c)
verifier(lec()[0] == "nid0", f"la Racine finie ({lec()})")

print("3. La cave : le bon lieu calculé, les variantes, le cadenas qui refuse")
aller("cave", ["grenier0", "t4", "cave0"], "t3")
tape("cd ~/terrain_terminagotchi/cave")
step = histoire.lecon_courante(core.load())[0]["steps"][0]
verifier(verif.lieu_attendu(core.load(), step) == "", "« ls -l nid » se tape depuis le carrefour (calculé)")
montre = propre(compagnon.commande_montree(core.load(), step))
verifier(montre.startswith("cd ~/terrain_terminagotchi") and "ls -l nid" in montre,
         f"depuis la cave, la commande montrée commence par le cd qui y mène ({montre!r})")
tape("ls -l nid")
verifier(lec() == ("t3", 0), "`ls -l nid` tapé dans la cave (No such file) ne valide pas")
verifier("Carrefour" in indice() and "cd ~/terrain_terminagotchi" in indice(),
         f"l'indice donne le BON lieu (le carrefour) ({indice()!r})")
tape("ls -la ../nid")
verifier(lec() == ("t3", 1), "`ls -la ../nid` depuis la cave est accepté (l n'importe où dans les options)")
tape("cd ..")
tape("chmod 444 nid/repas.txt")
tape("echo poire | tee -a nid/repas.txt")
verifier(lec()[0] != "t3" or lec()[1] > 2, f"`… | tee -a nid/repas.txt` refusé par le cadenas : l'étape est faite ({lec()})")
chmod_ok = subprocess.run(["chmod", "644", str(T / "nid" / "repas.txt")])

print("4. Le grenier : une faute de frappe, pas un « mauvais endroit »")
aller("grenier", [], "grenier0", 2)
tape("cd ~/terrain_terminagotchi/grenier")
(T / "grenier" / "fouillis").mkdir(parents=True, exist_ok=True)
(T / "grenier" / "fouillis" / "ours_en_peluche.txt").write_text("ours\n")
tape("mv fouilli/ours_en_peluche.txt ../nid/")
verifier("fouillis" in indice() and "terrain_terminagotchi`" not in indice(),
         f"`mv fouilli/…` : « tu voulais dire fouillis ? » ({indice()!r})")

print("5. La bibliothèque : tuyaux acceptés, lieu montré pour head et wc")
aller("bibliotheque", ["biblio0"], "biblio1")
tape("cd ~/terrain_terminagotchi/bibliotheque")
tape("cat ../nid/repas.txt | grep pomme")
verifier(lec() == ("biblio1", 1), f"`cat ../nid/repas.txt | grep pomme` est accepté ({lec()})")
tape("cd ..")
step = histoire.lecon_courante(core.load())[0]["steps"][1]
montre = propre(compagnon.commande_montree(core.load(), step))
verifier(montre.startswith("cd ~/terrain_terminagotchi/bibliotheque"),
         f"head : depuis le carrefour, la commande montrée ramène à la bibliothèque ({montre!r})")
tape("head -n 3 etagere_c/coin_poussiereux/livre_des_abysses.txt")
verifier(lec() == ("biblio1", 1), "head tapé au mauvais endroit (No such file) ne valide pas")
tape("cd bibliotheque")
tape("cat etagere_c/coin_poussiereux/livre_des_abysses.txt | head -n 3")
tape("cat etagere_c/coin_poussiereux/livre_des_abysses.txt | wc -l")
verifier(lec()[0] != "biblio1" or lec()[1] >= 3, f"`cat … | head` et `cat … | wc -l` acceptés ({lec()})")

print("6. Les erreurs du shell expliquées en français, dans le terminal")
d = T / "bibliotheque"
for ligne, mot in (("cat livre_absent.txt", "No such file"), ("cat etagere_c", "Is a directory"),
                   ("cd etagere_a/livre_des_recettes.txt", "Not a directory")):
    e = propre(verif.expliquer(ligne, 1, str(d)) or "")
    verifier(mot in e and len(e) > 40, f"« {ligne} » → {e[:70]!r}")
verifier(verif.collee("ls-a") == "ls -a" and verif.collee("cd/") == "cd /" and verif.collee("cdvestibule") == "cd vestibule",
         "fautes collées : ls-a → ls -a, cd/ → cd /, cdvestibule → cd vestibule")
verifier(verif.nom_proche("Nid", str(T)) == ("nid", True), "« Nid » : seule la casse diffère de « nid »")

print("7. Hugo : le test « je connais déjà » et le mode défi sans aide (G-13)")
from tg import placement  # noqa: E402
core.modifier(lambda s: (s["histoire"].update(faits=[], ailes=[], chap="reveil"), s.__setitem__("step", 0),
                         s.__setitem__("placement", {}), s["config"].pop("sans_aide", None)))
SH.lancer("cd ~")
msg = []
core.modifier(lambda s: msg.append(placement.commande(s, [])))
verifier("4" in propre(msg[0]) and placement.actif(core.load()), f"tg placement : le test commence ({propre(msg[0])[:60]!r})")
for c in ("pwd", "cd /", "cd", "ls -la"):
    tape(c)
st = core.load()
verifier(histoire.fini(st, "reveil") and st["config"].get("sans_aide"), "4 défis réussis : chapitre 1 validé, mode sans aide")
les, _ = histoire.lecon_courante(st)
step = les["steps"][st["step"]]
verifier("trouver" in propre(compagnon.commande_montree(st, step)), "sans aide : la commande est cachée, seulement le but")
with core.verrou():
    s2 = core.load()
    texte = propre(histoire.aide_lecon(s2, str(HOME)))
    core.save(s2)
verifier(step["cmd"].split()[0] in texte and "trouver" not in propre(compagnon.commande_montree(core.load(), step)),
         "`aide` montre la commande (et elle reste visible)")
core.modifier(lambda s: s.__setitem__("placement", {}))
core.modifier(lambda s: placement.commande(s, ["off"]))
verifier(not core.load()["config"].get("sans_aide"), "tg sansaide off : retour au mode normal")
core.modifier(lambda s: (s["histoire"].update(faits=[], ailes=[], chap="reveil"), s.__setitem__("placement", {})))
core.modifier(lambda s: placement.commande(s, []))
for c in ("ls", "ls", "ls", "ls", "ls", "ls", "ls", "ls", "ls", "ls", "ls"):
    tape(c)
verifier(p := core.load()["placement"].get("etat") == "rate", "10 lignes sans réussir : le test s'arrête, on fait le chapitre 1 avec l'aide")

print("8. Pas de jargon au début, aide, quêtes")
st = core.load()
from tg import intro  # noqa: E402
_ouvert = intro.ouvert
intro.ouvert = lambda s, f: False if f == "equipe" else _ouvert(s, f)      # l'équipe pas encore présentée
ecran = propre(app.render(st, 0, False))
intro.ouvert = _ouvert
verifier("INT " not in ecran and "Ce que je digère" not in ecran, "écran du début : ni « INT AGI FOR END » ni « Ce que je digère »")
from tg import quetes  # noqa: E402
verifier("copie" not in quetes.modeles(20, {"histoire": {"faits": ["t0"]}}) and "copie" in quetes.modeles(20, {"histoire": {"faits": ["t4"]}}),
         "pas de quête « Photocopie » avant la leçon de cp")
verifier("Pour les grands" in ecran or "💻" in ecran, "le panneau de la leçon a sa version des grands / vrai terminal")

print("9. tg mini : un vrai shell (Tab, Ctrl+C qui arrête la commande et pas le jeu, alias gardés)")
from tg import mini  # noqa: E402
(T / "grenier" / "fouillis").mkdir(parents=True, exist_ok=True)
verifier(mini.completer(f"cd {T}/gren") == f"cd {T}/grenier/", "Tab complète « gren » en « grenier/ »")
c = Coquille(HOME)
c.lancer('alias zz="echo ZZ"')
t0 = time.time()
_s, code, _d = c.lancer("sleep 20", 30, interrompre=lambda: time.time() - t0 > 1)
verifier(code != 0 and time.time() - t0 < 5, f"Ctrl+C arrête la commande en cours (code {code})")
verifier(c.lancer("zz")[0].strip() == "ZZ", "… et le shell reste là : l'alias marche encore")
c.fermer()

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
