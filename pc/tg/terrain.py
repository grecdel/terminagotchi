"""Le terrain effacé : si l'enfant fait rm -rf ~/terrain_terminagotchi (ou efface le nid), on le
remarque et on l'aide à reconstruire, puis la leçon reprend au bon endroit.

  1. Détection : la partie a déjà construit son terrain (leçon « Construire mon nid » finie) mais le dossier
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


def _h(state):
    from . import histoire
    return histoire.h_(state)


def _lid(state):
    from . import histoire
    return histoire.lecon_id(state)


def a_construit(state):
    """Vrai si la partie a déjà son terrain et son nid (leçon « Construire mon nid » finie)."""
    return "nid0" in _h(state)["faits"] or "Bâtisseur" in state.get("skills", [])


def _git_en_cours(state):
    """La leçon Git en cours a besoin du carnet (leçons 2 et 3 de la branche)."""
    return _lid(state) in ("git1", "git2")


def manque(state):
    """Ce qui a disparu et que l'enfant doit reconstruire : sous-ensemble de terrain, nid, carnet."""
    m = []
    if a_construit(state) or "reveil1" in _h(state)["faits"]:
        if not T().is_dir():
            m.append("terrain")
    if a_construit(state) and not (T() / "nid").is_dir():
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

    lid = _lid(state)
    if lid == "nid0" and step >= 2 and not fs["nid"]():
        reculer(1)                                              # le lit va dans le nid : il faut le refaire
    elif lid == "nid1" and step >= 1 and not fs["repas"]():
        reculer(0)                                              # cat : on réécrit le repas
    elif lid in ("t3", "biblio1") and nid.is_dir() and not (nid / "repas.txt").is_file() and \
            (lid == "t3" or step == 0):
        _ecrire(nid / "repas.txt", "pomme\n")                    # les droits (et la loupe) ont besoin du repas
        remis.append("nid/repas.txt")
    elif lid == "t4" and nid.is_dir():
        if step == 0 and not (nid / "repas.txt").is_file():
            _ecrire(nid / "repas.txt", "pomme\n")
            remis.append("nid/repas.txt")
        elif step == 1 and not fs["secours"]() and not fs["reserve"]():
            reculer(0)
            if not (nid / "repas.txt").is_file():
                _ecrire(nid / "repas.txt", "pomme\n")
                remis.append("nid/repas.txt")
    elif lid == "git0" and step >= 1 and not fs["carnet"]():
        reculer(0)
    elif lid == "git1" and step >= 1 and not fs["journal"]():
        reculer(0)
    elif lid == "scripts0" and nid.is_dir() and step >= 1 and not fs["miam"]():
        reculer(0)
    elif lid == "scripts1" and nid.is_dir() and not fs["miam"]():
        _ecrire(les.MIAM, C('echo "Miam !"\n', 'Write-Output "Miam !"\n'), executable=False)
        remis.append("nid/" + les.MIAM.name)
    elif lid == "reseau1" and step >= 2 and not fs["colis"]():
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
