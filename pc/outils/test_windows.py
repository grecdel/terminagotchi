"""Windows (simulé) : le jeu démarre sans termios, reconnaît les alias et cmdlets de PowerShell, et ouvre le même
terminal intégré que sous Linux (un PowerShell avec le compagnon chargé pour la session)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["HOME"] = tempfile.mkdtemp()
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

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
