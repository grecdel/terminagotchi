"""Le terrain effacé : si l'enfant fait rm -rf ~/terrain_terminagotchi (ou efface le nid), on le
remarque et on l'aide à reconstruire, puis la leçon reprend au bon endroit.

  1. Détection : la partie a déjà construit son terrain (leçon « Bâtisseur » finie) mais le dossier
     ~/terrain_terminagotchi ou son nid n'existe plus. (Une nouvelle partie démarre sans terrain :
     parties.py range le terrain de chaque partie ; tant que la leçon 1 n'est pas finie, rien ne
     manque.) Même chose pour le carnet git pendant la branche Git.
  2. Une bulle claire donne LA commande à taper (mkdir -p ~/terrain_terminagotchi/nid) ; un bandeau
     reste affiché sur l'écran principal tant que ce n'est pas fait. Si l'enfant n'y arrive pas, le
     jeu reconstruit lui-même après quelques commandes (AIDE_AUTO).
  3. Reprise : les fichiers indispensables à l'étape en cours sont remis (repas.txt pour la leçon
     des droits, miam.sh pour les scripts…), ou bien la leçon revient à l'étape qui les crée.
     Les monstres reviennent dès que le nid existe (explo.debloque).
"""
import os
import shutil
import subprocess
import time

from . import core
from .langue import t
from .plateforme import C, IS_WIN

AIDE_AUTO = 12            # commandes tapées sans réussir : le jeu reconstruit lui-même


def T():
    return core.TERRAIN


def _lecons():
    from . import lecons
    return lecons


def a_construit(state):
    """Vrai si la partie a déjà son terrain et son nid (leçon « Bâtisseur » finie)."""
    return state.get("lesson", 0) >= 2 or "Bâtisseur" in state.get("skills", [])


def _git_en_cours(state):
    """La leçon Git en cours a besoin du carnet (leçons 2 et 3 de la branche)."""
    return state.get("branche") == "Git" and 1 <= state.get("arbre", {}).get("Git", 0) < 3 \
        and _lecons().tronc_fini(state)


def manque(state):
    """Ce qui a disparu et que l'enfant doit reconstruire : sous-ensemble de terrain, nid, carnet."""
    m = []
    if a_construit(state):
        if not T().is_dir():
            m.append("terrain")
        if not (T() / "nid").is_dir():
            m.append("nid")
    if not m and _git_en_cours(state) and not (T() / "carnet" / ".git").is_dir():
        m.append("carnet")
    return m


def commande(m):
    if "terrain" in m or "nid" in m:
        return C(f"mkdir -p ~/{T().name}/nid", f"mkdir ~/{T().name}/nid")
    return f"git init ~/{T().name}/carnet"


def reconstruire(state, m):
    """Le jeu reconstruit lui-même ce qui manque (après AIDE_AUTO commandes sans réussite)."""
    (T() / "nid").mkdir(parents=True, exist_ok=True)
    if "carnet" in m and shutil.which("git"):
        try:
            subprocess.run(["git", "init", "-q", str(T() / "carnet")], timeout=20,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            pass


def _ecrire(p, texte, executable=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")
    if executable and not IS_WIN:
        os.chmod(p, 0o755)


def reparer_lecon(state):
    """Remet les fichiers dont l'étape en cours a besoin, ou recule à l'étape qui les crée.
    Renvoie (fichiers remis, étape reculée ?)."""
    les = _lecons()
    fs = les.FS
    remis, recule = [], False
    nid = T() / "nid"
    step = state.get("step", 0)

    def reculer(vers):
        nonlocal recule
        if state["step"] > vers:
            state["step"] = vers
            recule = True

    if not les.tronc_fini(state):
        n = state.get("lesson", 0)
        if n == 1 and step >= 1 and not fs["terrain"]():
            reculer(0)                                          # cd terrain : il faut d'abord le refaire
        elif n == 2 and step >= 1 and not fs["repas"]():
            reculer(0)                                          # cat / grep : on réécrit le repas
        elif n == 3 and nid.is_dir() and not (nid / "repas.txt").is_file():
            _ecrire(nid / "repas.txt", "pomme\n")                # la leçon des droits a besoin du repas
            remis.append("nid/repas.txt")
        elif n == 4 and nid.is_dir():
            if step == 0 and not (nid / "repas.txt").is_file():
                _ecrire(nid / "repas.txt", "pomme\n")
                remis.append("nid/repas.txt")
            elif step == 1 and not fs["secours"]() and not fs["reserve"]():
                reculer(0)
                if not (nid / "repas.txt").is_file():
                    _ecrire(nid / "repas.txt", "pomme\n")
                    remis.append("nid/repas.txt")
        return remis, recule
    b = state.get("branche")
    i = state.get("arbre", {}).get(b, 0) if b else 0
    if b == "Git":
        if i == 0 and step >= 1 and not fs["carnet"]():
            reculer(0)
        elif i == 1 and step >= 1 and not fs["journal"]():
            reculer(0)
    elif b == "Scripts" and nid.is_dir():
        if i == 0 and step >= 1 and not fs["miam"]():
            reculer(0)
        elif i >= 1 and not fs["miam"]():
            _ecrire(les.MIAM, C('echo "Miam !"\n', 'Write-Output "Miam !"\n'), executable=i >= 2)
            remis.append("nid/" + les.MIAM.name)
    elif b == "Réseau" and i == 1 and step >= 2 and not fs["colis"]():
        reculer(1)
    return remis, recule


def tick(state, lignes):
    """À chaque étape de jeu, avant les leçons."""
    tapees = [l for l in lignes if not core.est_colle(l)]
    m = manque(state)
    perdu = state.get("terrain_perdu")
    if m:
        cmd = commande(m)
        if not perdu or perdu.get("cmd") != cmd:
            state["terrain_perdu"] = {"cmd": cmd, "t": time.time(), "n": 0}
            cle = "lec.terrain.carnet.dit" if m == ["carnet"] else "lec.terrain.perdu.dit"
            core.log(state, t("lec.terrain.perdu.log"))
            core.say(state, t(cle, cmd=cmd), 20)
            core.notif(state, t(cle, cmd=cmd))
            core.animer(state, "confus")
            return
        perdu["n"] += len(tapees)
        if perdu["n"] < AIDE_AUTO:
            return
        reconstruire(state, m)                                   # l'enfant n'y arrive pas : on l'aide
        if manque(state):
            return
        state["terrain_perdu"] = None
        state["annonce"] = None
        remis, _ = reparer_lecon(state)
        core.log(state, t("lec.terrain.repare.log"))
        core.say(state, t("lec.terrain.auto.dit"), 14)
        if remis:
            core.say(state, t("lec.terrain.refait.dit", fichiers=", ".join(remis)), 10)
        core.animer(state, "content")
        return
    remis, recule = reparer_lecon(state)
    if perdu:
        state["terrain_perdu"] = None
        state["annonce"] = None                                  # la leçon se réannonce
        core.log(state, t("lec.terrain.repare.log"))
        core.say(state, t("lec.terrain.repare.dit"), 12)
        core.animer(state, "content")
        core.add_xp(state, 5)
    if remis:
        core.say(state, t("lec.terrain.refait.dit", fichiers=", ".join(remis)), 10)
    elif recule:
        core.say(state, t("lec.terrain.recule.dit"), 10)
