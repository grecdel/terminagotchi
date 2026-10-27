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
    return langue.sans_marques(ANSI.sub("", x if isinstance(x, str) else "\n".join(x)))


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

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
