"""Windows (simulé) : le jeu démarre sans termios, reconnaît les alias et cmdlets de PowerShell, et ouvre le même
terminal intégré que sous Linux (un PowerShell avec le compagnon chargé pour la session).

4. L'Atelier en PowerShell : chaque étape montrée est reconnue (if (…) { … }, ForEach-Object, Get-Content robot\\…),
   puis at4 → at5 joués comme sous Windows (cerveau.ps1, fichiers écrits en UTF-16 comme Windows PowerShell 5.1 avec >),
   le script refusé par Windows (le moteur reste sur stop → l'indice de la politique d'exécution), l'exploit, et le
   rattrapage des joueurs Windows d'avant. Les VRAIS PowerShell 5.1 et 7 jouent le défi en CI (pc/outils/defi_powershell.py,
   .github/workflows/windows.yml)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["HOME"] = os.environ["USERPROFILE"] = tempfile.mkdtemp(prefix="tg_win_")   # (USERPROFILE : le dossier perso sous Windows)
os.environ["APPDATA"] = os.path.join(os.environ["HOME"], "AppData")
os.environ["TG_DEFI_TEMP"] = os.environ["HOME"]
os.environ["LANG"] = "fr_FR.UTF-8"
from tg import compagnon, core, scenes, verif  # noqa: E402

ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


# 1. pas de termios sous Windows : interroger() répond sans rien importer
nom = os.name
import builtins  # noqa: E402
vrai_import = builtins.__import__


def sans_termios(n, *a, **k):
    if n in ("termios", "tty", "fcntl"):
        raise ModuleNotFoundError(n)
    return vrai_import(n, *a, **k)


os.name = "nt"
builtins.__import__ = sans_termios
try:
    r = scenes.interroger()
    verifier(r["kitty"] is False and r["sixel"] is False, "interroger() sans termios (Windows) : pas de plantage")
except Exception as e:                       # noqa: BLE001
    verifier(False, f"interroger() a planté : {e!r}")
finally:
    os.name = nom
    builtins.__import__ = vrai_import

# 2. les commandes de PowerShell
core.IS_WIN = verif.IS_WIN = compagnon.IS_WIN = True
verifier(core.first_word("Get-Location") == "pwd" and core.first_word("Get-ChildItem -Force") == "ls",
         "Get-Location nourrit comme pwd, Get-ChildItem comme ls")
verifier(all(core.commande_existe(c) for c in ("pwd", "ls", "dir", "cd", "cat", "echo", "get-location", "new-item")),
         "alias et cmdlets de PowerShell : des commandes qui existent")
verifier(all(verif.commande_installee(c) for c in ("pwd", "dir", "Get-Location", "Select-String")),
         "pas de faux « l'outil n'est pas installé » pour pwd, dir, Get-Location")
verifier(verif.motif_ok({"re": r"^pwd\b"}, "Get-Location", "/tmp") and verif.motif_ok({"re": r"^ls\b"}, "Get-ChildItem", "/tmp"),
         "une leçon qui attend pwd accepte Get-Location")
verifier(not core.commande_existe("blablabla"), "un mot inventé reste inconnu")

# 3. le terminal intégré : un PowerShell, -NoProfile, -ExecutionPolicy Bypass (pour la session), le bloc du compagnon
appels = []
compagnon._powershell = lambda: "powershell"
compagnon._blocs = lambda: {Path("Microsoft.PowerShell_profile.ps1"): "function prompt { 'PS> ' }\n"}
compagnon.subprocess.call = lambda argv, env=None: appels.append((argv, env)) or 0
verifier(compagnon.ouvrir_terminal_du_jeu(), "le terminal du jeu s'ouvre")
argv, env = appels[-1]
verifier(argv[0] == "powershell" and "-NoExit" in argv and "-NoProfile" in argv
         and argv[argv.index("-ExecutionPolicy") + 1] == "Bypass" and argv[-1].endswith("terminal_du_jeu.ps1"),
         f"PowerShell lancé avec le compagnon de la session : {argv[1:-1]}")
verifier(env.get("TG_DANS_LE_JEU") == "1", "TG_DANS_LE_JEU (exit ramène au jeu)")
verifier(Path(argv[-1]).read_text(encoding="utf-8-sig").startswith("function prompt"), "le bloc écrit (UTF-8 avec BOM)")

# 4. L'Atelier en PowerShell
import io  # noqa: E402
import re  # noqa: E402
from tg import app, histoire, langue, recompenses  # noqa: E402
from tg import atelier as A  # noqa: E402
langue.definir("fr")
W = A.lecons_pour(True)
caches = [s_["cmd"] for l_ in W.values() for s_ in l_["steps"] if s_.get("win") is False]
verifier(sorted(caches) == sorted(["ls /sys/class/leds", "command -v gpioset pinctrl", "crontab -l", "command -v arduino-cli esptool.py"]),
         f"sous Windows, seules les étapes propres à Linux restent cachées : {caches}")
pas_w = {s_["cmd"]: s_ for l_ in W.values() for s_ in l_["steps"]}
mal = []
for c_, s_ in pas_w.items():
    if "re" in s_ and not any(verif.motif_ok(s_, m_.texte, "/tmp") for m_ in verif.morceaux(c_, "/tmp")):
        mal.append(c_)
verifier(not mal, f"chaque commande PowerShell montrée est reconnue par son étape {mal}")
FORMES = {"if (5 -lt 10) { \"vrai\" } else { \"faux\" }": ["if (3 -gt 1) { 'oui' }", "If (5 -lt 10) { \"vrai\" }"],
          "$d = [int](Get-Content robot\\capteur_distance); if ($d -lt 10) { \"obstacle\" } else { \"libre\" }":
              ["if ([int](Get-Content robot\\capteur_distance) -lt 10) { \"obstacle\" } else { \"libre\" }",
               "$d = gc robot/capteur_distance; if ([int]$d -le 9) { 'obstacle' }"],
          "1..3 | ForEach-Object { Get-Content robot\\capteur_distance; Start-Sleep 1 }":
              ["foreach ($i in 1..3) { Get-Content robot\\capteur_distance; Start-Sleep 1 }",
               "for ($i=1; $i -le 3; $i++) { gc robot\\capteur_distance; sleep 1 }", "1..3 | % { cat robot/capteur_distance }"],
          "Get-Content robot\\led": ["gc robot\\led", "cat robot/led", "type robot\\led"],
          "Measure-Command { .\\cerveau.ps1 }": ["measure-command {.\\cerveau.ps1}"]}
mal = [(c_, f_) for c_, fs_ in FORMES.items() for f_ in fs_
       if not any(verif.motif_ok(pas_w[c_], m_.texte, "/tmp") for m_ in verif.morceaux(f_, "/tmp"))]
verifier(not mal, f"les autres façons d'écrire en PowerShell sont acceptées aussi {mal}")
_j = Path(tempfile.mkdtemp(prefix="tg_win_j_"))
(_j / "robot").mkdir()
(_j / "robot" / "journal.txt").write_text("pas 1\n")
verifier(verif.chemins_manquants("Get-Content robot/journal.txt -Tail 5", str(_j)) == []
         and verif.chemins_manquants("gc -TotalCount 3 robot/journal.txt", str(_j)) == [],
         "Get-Content … -Tail 5 : le 5 n'est pas pris pour un fichier qui manque")
verifier(not any(verif.motif_ok(pas_w["if (5 -lt 10) { \"vrai\" } else { \"faux\" }"], m_.texte, "/tmp")
                 for m_ in verif.morceaux("[ 5 -lt 10 ] && echo vrai || echo faux", "/tmp")),
         "la forme bash `[ 5 -lt 10 ]` (qui ne marche pas dans PowerShell) n'est pas acceptée sous Windows")
cles = sorted({v for l_ in W.values() for s_ in l_["steps"] for v in (s_["dit"], s_["bravo"]) if isinstance(v, str) and ".ps." in v})
manque = [(c_, k_) for c_ in ("fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur")
          for k_ in cles + [k_.replace(".dit", ".adulte") for k_ in cles if k_.endswith(".dit")] +
          ["at.ps.politique", "at.ps.indice.politique", "at.ps.aidec.texte", "at.ps.essai.texte", "at.ps.defi.regles"]
          if langue.brut(k_, c_) is None or (c_ != "fr" and langue._charger(c_).get(k_) is None)]
verifier(len(cles) >= 18 and not manque, f"les textes PowerShell existent dans les 14 langues ({len(cles)} clés d'étapes) {manque[:3]}")
verifier(all("cerveau.sh" not in langue.t(k_) and "seq" not in langue.t(k_) for k_ in
             ("at.ps.essai.texte", "at.ps.defi.regles", "at.ps.indice.boucle", "at.ps.aide.liste", "at.ps.meuble.plan")),
         "les textes Windows ne parlent plus de cerveau.sh ni de seq")
tous = "".join(open(f_, encoding="utf-8").read() for f_ in Path(__file__).resolve().parents[1].glob("tg/langues/*.json"))
src = "".join(open(f_, encoding="utf-8").read() for f_ in Path(__file__).resolve().parents[1].glob("tg/*.py"))
verifier("Set-ExecutionPolicy" not in tous and not re.search(r"[\"']Set-ExecutionPolicy", src)
         and "-ExecutionPolicy Bypass -File" in langue.t("at.ps.politique"),
         "jamais Set-ExecutionPolicy : seulement `powershell -ExecutionPolicy Bypass -File` (pour une seule fois)")

# … la partie : at4 → at5 comme sous Windows (les effets de PowerShell imités : UTF-16 de >, ANSI de Set-Content)
A.IS_WIN = histoire.IS_WIN = True
for k_, v_ in W.items():
    A.LECONS[k_].clear()
    A.LECONS[k_].update(v_)
histoire._CMDS_ATE |= set(pas_w)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import defi_powershell as DP  # noqa: E402
verifier(DP.prepare() == 0, "la partie Windows est prête : l'Atelier meublé avec cerveau_exemple.ps1 (UTF-8 avec BOM)")
R = A.dossier()
verifier((R / "cerveau_exemple.ps1").read_bytes()[:3] == b"\xef\xbb\xbf" and not (R / "cerveau_exemple.sh").exists(),
         "cerveau_exemple.ps1 a son BOM (Windows PowerShell 5.1 lit les accents), pas de cerveau_exemple.sh sous Windows")


def ps_ecrit(nom, valeur, chevron):
    """Ce que PowerShell 5.1 écrit : > en UTF-16 avec BOM, Set-Content en ANSI ; avec CRLF."""
    (R / "robot" / nom).write_bytes(("﻿" + valeur + "\r\n").encode("utf-16-le") if chevron else (valeur + "\r\n").encode("cp1252"))


def joue(n, cerveau):
    for _ in range(n):
        if cerveau:
            cerveau()
        A.commande(["pas"], sortie=io.StringIO())


def tape(l_):
    return DP.tape(l_, cwd=str(R))


exemple = lambda: ps_ecrit("moteur", "avance", False)                                         # noqa: E731
malin = lambda: ps_ecrit("moteur", "droite" if int(A.lire_robot("capteur_distance")) < 10 else "avance", True)  # noqa: E731
(R / "cerveau.ps1").write_bytes((R / "cerveau_exemple.ps1").read_bytes())
st = tape("copy cerveau_exemple.ps1 cerveau.ps1")
verifier(DP.lecon(st) == ("at4", 4), f"copy cerveau_exemple.ps1 cerveau.ps1 : le cerveau est à l'enfant {DP.lecon(st)}")
A.commande(["essai"], sortie=io.StringIO())
st = tape("atelier essai")
joue(10, exemple)
st = tape("for ($i=1; $i -le 10; $i++) { .\\cerveau.ps1; atelier pas }")
verifier(DP.lecon(st) == ("at4", 6) and "(choc)" in A.carnet(), f"la boucle for (…) de PowerShell : le cerveau d'exemple se cogne {DP.lecon(st)}")
(R / "cerveau.ps1").write_text(A.cerveau_exemple_ps().replace("avance", "Avance"), encoding="utf-8")
st = tape("notepad cerveau.ps1")
verifier(DP.lecon(st) == ("at4", 6) and st.get("indice_lecon") == langue.t("at.ps.indice.malin", cmd="atelier aide-cerveau"),
         "un cerveau.ps1 sans if : l'indice parle de cerveau.ps1")
(R / "cerveau.ps1").write_bytes(("﻿" + A.cerveau_malin_ps()).encode("utf-16-le"))     # écrit avec > dans PowerShell 5.1
st = tape("notepad cerveau.ps1")
verifier(DP.lecon(st) == ("at5", 0), f"le cerveau malin en PowerShell (même en UTF-16) est reconnu {DP.lecon(st)}")
A.commande(["defi"], sortie=io.StringIO())
st = tape("atelier defi")
joue(20, None)                                                                                 # Windows a refusé le script
st = tape("1..20 | ForEach-Object { .\\cerveau.ps1; atelier pas }")
verifier(DP.lecon(st) == ("at5", 1) and st.get("indice_lecon") == langue.t("at.ps.indice.politique"),
         "le script refusé (« l'exécution de scripts est désactivée ») : le moteur reste sur stop, l'indice l'explique")
st = tape("1..20 | ForEach-Object { .\\cerveau.ps1 }")
verifier(st.get("indice_lecon") == langue.t("at.ps.indice.boucle") and ".\\cerveau.ps1" in langue.t("at.ps.indice.boucle"),
         "une boucle ForEach-Object sans `atelier pas` : l'indice PowerShell")
A.commande(["defi"], sortie=io.StringIO())
joue(20, malin)
st = tape("1..20 | ForEach-Object { .\\cerveau.ps1; atelier pas }")
verifier(DP.lecon(st) == ("at6", 0) and "atelier.robot" in recompenses.r_(st)["exploits"],
         f"le défi réussi dans PowerShell : la leçon avance et l'exploit est donné {DP.lecon(st)}")
verifier(DP.verifie() == 0, "le vrai résultat : 20 pas, aucun choc, au moins 12 cases, l'exploit")
core.modifier(lambda s_: recompenses.r_(s_)["exploits"].pop("atelier.robot", None))     # un joueur Windows d'avant
A.commande(["defi"], sortie=io.StringIO())
fin = io.StringIO()
for _ in range(20):
    malin()
    A.commande(["pas"], sortie=fin)
verifier("atelier.robot" in recompenses.r_(core.load())["exploits"],
         "rattrapage : la leçon du défi finie sans l'exploit (Windows d'avant) → le défi réussi le donne")
o = io.StringIO()
A.commande(["aide-cerveau"], sortie=o)
verifier("notepad cerveau.ps1" in o.getvalue() and "Set-Content robot\\moteur droite" in o.getvalue()
         and "-ExecutionPolicy Bypass -File .\\cerveau.ps1" in o.getvalue(), "atelier aide-cerveau : la version PowerShell")
A.IS_WIN = histoire.IS_WIN = False

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
