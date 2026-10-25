"""Le Terminagotchi professeur : tronc commun puis arbre de compétences à 4 branches.

Les textes (titres, « dit », « bravo », « astuce », descriptions) sont des clés des fichiers de
langue (langues/xx.json) ; tx() les traduit. Une clé peut venir avec ses paramètres : (clé, {…}).
"""
import os
import re

from . import core
from .langue import t
from .plateforme import OSK, C, IS_WIN, est_colle, installer, shell_rc

T = core.TERRAIN
S = "\\" if IS_WIN else "/"


def _protected(p):
    try:
        return (p.stat().st_mode & 0o222) == 0
    except OSError:
        return False


def _commit_fait():
    git = T / "carnet" / ".git"
    heads = git / "refs" / "heads"
    try:
        return any(heads.iterdir()) or (git / "packed-refs").exists()
    except OSError:
        return False


MIAM = T / "nid" / ("miam.ps1" if IS_WIN else "miam.sh")


def _contient(p, mot):
    """Le fichier contient ce mot (UTF-8, ou UTF-16 comme l'écrit echo … > dans Windows PowerShell)."""
    try:
        brut = p.read_bytes()
    except OSError:
        return False
    for enc in ("utf-16", "utf-8") if brut[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8",):
        try:
            return mot in brut.decode(enc, errors="replace").lower()
        except LookupError:
            pass
    return False

FS = {
    "terrain":  lambda: T.is_dir(),
    "nid":      lambda: (T / "nid").is_dir(),
    "repas":    lambda: (T / "nid" / "repas.txt").is_file() and _contient(T / "nid" / "repas.txt", "pomme"),
    "protege":  lambda: _protected(T / "nid" / "repas.txt"),
    "secours":  lambda: (T / "nid" / "secours.txt").is_file(),
    "reserve":  lambda: (T / "reserve.txt").is_file(),
    "supprime": lambda: not (T / "reserve.txt").exists(),
    "colis":    lambda: (T / "colis.html").is_file(),
    "carnet":   lambda: (T / "carnet" / ".git").is_dir(),
    "journal":  lambda: (T / "carnet" / "journal.txt").is_file(),
    "commit":   _commit_fait,
    "miam":     lambda: MIAM.is_file(),
    "miam_x":   lambda: MIAM.is_file() and os.access(MIAM, os.X_OK),
}

CD = r"^(cd|set-location|sl)\s+"

# ---------------------------------------------------------------- tronc commun
TRONC = [
    {"titre": "lec.t0.titre", "skill": "Boussole", "niveau": 2, "steps": [
        {"dit": "lec.t0.0.dit", "cmd": "pwd",
         "re": r"^(pwd|get-location|gl)\b",
         "bravo": "lec.t0.0.bravo"},
        {"dit": "lec.t0.1.dit", "cmd": C("ls", "dir"),
         "re": r"^(ls|dir|gci|get-childitem)\b", "bravo": "lec.t0.1.bravo"},
        {"dit": "lec.t0.2.dit", "cmd": "cd ~",
         "re": r"^(cd|set-location|sl)(\s+~[/\\]?)?\s*$",
         "bravo": "lec.t0.2.bravo"},
    ]},
    {"titre": "lec.t1.titre", "skill": "Bâtisseur", "niveau": 3, "steps": [
        {"dit": "lec.t1.0.dit",
         "cmd": "mkdir terrain_terminagotchi", "fs": "terrain",
         "bravo": "lec.t1.0.bravo"},
        {"dit": "lec.t1.1.dit", "cmd": "cd terrain_terminagotchi", "re": CD + r".*terrain_terminagotchi",
         "bravo": "lec.t1.1.bravo"},
        {"dit": "lec.t1.2.dit", "cmd": "mkdir nid", "fs": "nid",
         "bravo": "lec.t1.2.bravo"},
    ]},
    {"titre": "lec.t2.titre", "skill": "Inspecteur", "niveau": 4, "steps": [
        {"dit": "lec.t2.0.dit",
         "cmd": f"echo pomme > nid{S}repas.txt", "fs": "repas",
         "bravo": "lec.t2.0.bravo"},
        {"dit": "lec.t2.1.dit", "cmd": f"cat nid{S}repas.txt",
         "re": r"^(cat|type|gc|get-content|less|more|head)\b.*repas",
         "bravo": "lec.t2.1.bravo"},
        {"dit": "lec.t2.2.dit",
         "cmd": C(f"grep pomme nid{S}repas.txt", f"Select-String pomme nid{S}repas.txt"),
         "re": r"^(grep|select-string|sls|findstr)\b.*pomme",
         "bravo": "lec.t2.2.bravo"},
    ]},
    {"titre": "lec.t3.titre", "skill": "Gardien", "niveau": 5, "steps": [
        {"dit": "lec.t3.0.dit",
         "cmd": C("ls -l nid", f"attrib nid{S}repas.txt"),
         "re": r"^(ls\s+-\w*l|attrib|get-acl|icacls|stat)\b",
         "bravo": C("lec.t3.0.bravo", "lec.t3.0.bravo.win")},
        {"dit": "lec.t3.1.dit",
         "cmd": C(f"chmod 444 nid{S}repas.txt", f"attrib +r nid{S}repas.txt"), "fs": "protege",
         "bravo": "lec.t3.1.bravo"},
        {"dit": "lec.t3.2.dit",
         "cmd": f"echo poire >> nid{S}repas.txt", "re": r">>.*repas",
         "bravo": "lec.t3.2.bravo"},
    ]},
    {"titre": "lec.t4.titre", "skill": "Nettoyeur", "niveau": 6, "steps": [
        {"dit": "lec.t4.0.dit",
         "cmd": f"cp nid{S}repas.txt nid{S}secours.txt", "fs": "secours",
         "bravo": "lec.t4.0.bravo"},
        {"dit": "lec.t4.1.dit",
         "cmd": f"mv nid{S}secours.txt reserve.txt", "fs": "reserve",
         "bravo": "lec.t4.1.bravo"},
        {"dit": "lec.t4.2.dit",
         "cmd": C("rm reserve.txt", "rm reserve.txt -Force"), "fs": "supprime",
         "astuce": C("lec.t4.2.astuce", "lec.t4.2.astuce.win"),
         "bravo": "lec.t4.2.bravo"},
    ]},
]

# ---------------------------------------------------------------- arbre de compétences
RC = shell_rc()
ARBRE = {
    "Réseau": {"stat": "Agilité", "icone": "📡", "desc": "lec.reseau.desc", "lecons": [
        {"titre": "lec.reseau0.titre", "skill": "Radar", "steps": [
            {"dit": "lec.reseau0.0.dit",
             "cmd": C("ping -c 3 example.com", "ping -n 3 example.com"), "re": r"^ping\b",
             "bravo": "lec.reseau0.0.bravo"},
            {"dit": "lec.reseau0.1.dit", "cmd": C("ip a", "ipconfig", mac="ifconfig", android="ifconfig"),
             "re": r"^(ip|ifconfig|ipconfig)\b",
             "bravo": "lec.reseau0.1.bravo"},
        ]},
        {"titre": "lec.reseau1.titre", "skill": "Facteur", "steps": [
            {"dit": "lec.reseau1.0.dit",
             "cmd": C("curl -I https://example.com", "curl.exe -I https://example.com"), "re": r"^curl(\.exe)?\b",
             "bravo": "lec.reseau1.0.bravo"},
            {"dit": "lec.reseau1.1.dit",
             "cmd": C("curl -o colis.html https://example.com", "curl.exe -o colis.html https://example.com"),
             "fs": "colis", "astuce": "lec.reseau1.1.astuce",
             "bravo": "lec.reseau1.1.bravo"},
            {"dit": "lec.reseau1.2.dit",
             "cmd": C("head -n 5 colis.html", "Get-Content colis.html -Head 5"),
             "re": r"^(head|get-content|gc|cat|type)\b.*colis", "bravo": "lec.reseau1.2.bravo"},
        ]},
        {"titre": "lec.reseau2.titre", "skill": "Cartographe", "steps": [
            {"dit": "lec.reseau2.0.dit", "cmd": "nslookup example.com",
             "re": r"^(nslookup|dig|resolve-dnsname)\b",
             "bravo": "lec.reseau2.0.bravo"},
            {"dit": "lec.reseau2.1.dit",
             "cmd": C("traceroute example.com", "tracert example.com"), "re": r"^(traceroute|tracert|tracepath|mtr)\b",
             "astuce": C(("lec.reseau2.1.astuce", {"cmd": installer("traceroute")}), None),
             "bravo": "lec.reseau2.1.bravo"},
        ]},
    ]},
    "Git": {"stat": "Intelligence", "icone": "🌿", "desc": "lec.git.desc", "lecons": [
        {"titre": "lec.git0.titre", "skill": "Archiviste", "steps": [
            {"dit": "lec.git0.0.dit",
             "cmd": "git init carnet", "fs": "carnet",
             "bravo": "lec.git0.0.bravo"},
            {"dit": "lec.git0.1.dit", "cmd": "cd carnet", "re": CD + r".*carnet", "bravo": "lec.git0.1.bravo"},
            {"dit": "lec.git0.2.dit", "cmd": "git status", "re": r"^git\s+status",
             "bravo": "lec.git0.2.bravo"},
        ]},
        {"titre": "lec.git1.titre", "skill": "Mémoire", "steps": [
            {"dit": "lec.git1.0.dit", "cmd": 'echo "jour 1" > journal.txt', "fs": "journal",
             "bravo": "lec.git1.0.bravo"},
            {"dit": "lec.git1.1.dit", "cmd": "git add journal.txt", "re": r"^git\s+add\b",
             "bravo": "lec.git1.1.bravo"},
            {"dit": "lec.git1.2.dit", "cmd": 'git commit -m "premier souvenir"', "fs": "commit",
             "astuce": "lec.git1.2.astuce",
             "bravo": "lec.git1.2.bravo"},
        ]},
        {"titre": "lec.git2.titre", "skill": "Chronomancien", "steps": [
            {"dit": "lec.git2.0.dit", "cmd": 'echo "jour 2" >> journal.txt',
             "re": r">>\s*journal", "bravo": "lec.git2.0.bravo"},
            {"dit": "lec.git2.1.dit", "cmd": "git diff", "re": r"^git\s+diff",
             "bravo": "lec.git2.1.bravo"},
            {"dit": "lec.git2.2.dit", "cmd": "git log", "re": r"^git\s+log",
             "astuce": "lec.git2.2.astuce", "bravo": "lec.git2.2.bravo"},
        ]},
    ]},
    "Scripts": {"stat": "Intelligence", "icone": "🧪", "desc": "lec.scripts.desc", "lecons": [
        {"titre": "lec.scripts0.titre", "skill": "Cuistot", "steps": [
            {"dit": "lec.scripts0.0.dit",
             "cmd": C(f"echo 'echo \"Miam !\"' > nid{S}miam.sh", f"echo 'Write-Output \"Miam !\"' > nid{S}miam.ps1"),
             "fs": "miam", "bravo": "lec.scripts0.0.bravo"},
            {"dit": "lec.scripts0.1.dit",
             "cmd": C(f"sh nid{S}miam.sh", f"powershell -ExecutionPolicy Bypass -File nid{S}miam.ps1"),
             "re": r"miam\.(sh|ps1)", "bravo": "lec.scripts0.1.bravo"},
        ]},
        {"titre": "lec.scripts1.titre", "skill": "Inventeur", "steps": (
            [{"dit": "lec.scripts1.0.dit", "cmd": f"chmod +x nid{S}miam.sh", "fs": "miam_x",
              "bravo": "lec.scripts1.0.bravo"}] if not IS_WIN else []) + [
            {"dit": "lec.scripts1.1.dit",
             "cmd": C("alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'", 'function miam { Write-Output "Miam !" }'),
             "re": r"^(alias\s+miam|function\s+miam)", "bravo": "lec.scripts1.1.bravo"},
            {"dit": "lec.scripts1.2.dit", "cmd": "miam", "re": r"^miam\s*$", "bravo": "lec.scripts1.2.bravo"},
        ]},
        {"titre": "lec.scripts2.titre", "skill": "Créateur", "steps": [
            {"dit": "lec.scripts2.0.dit",
             "cmd": C(f"echo \"alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'\" >> {RC}",
                      "Add-Content $PROFILE 'function miam { Write-Output \"Miam !\" }'"),
             "re": r"(alias\s+miam.*>>\s*\S*(rc|profile)|^add-content\s+\$profile)",
             "astuce": C(("lec.scripts2.0.astuce", {"rc": RC}),
                         "lec.scripts2.0.astuce.win"),
             "bravo": "lec.scripts2.0.bravo"},
            {"dit": "lec.scripts2.1.dit", "cmd": C(f"source {RC}", ". $PROFILE"),
             "re": r"^(source|\.)\s+\S*(rc|profile)",
             "bravo": "lec.scripts2.1.bravo"},
        ]},
    ]},
    "Système": {"stat": "Force", "icone": "⚙", "desc": "lec.systeme.desc", "lecons": [
        {"titre": "lec.systeme0.titre", "skill": "Vigie", "steps": [
            {"dit": "lec.systeme0.0.dit", "cmd": "whoami", "re": r"^whoami\b",
             "bravo": "lec.systeme0.0.bravo"},
            {"dit": "lec.systeme0.1.dit", "cmd": C("ps aux", "Get-Process", android="ps"),
             "re": r"^(ps|get-process|gps|tasklist|top|htop)\b",
             "bravo": "lec.systeme0.1.bravo"},
        ]},
        {"titre": "lec.systeme1.titre", "skill": "Intendant", "steps": [
            {"dit": "lec.systeme1.0.dit", "cmd": C("df -h", "Get-PSDrive"),
             "re": r"^(df|get-psdrive|gdr)\b", "bravo": "lec.systeme1.0.bravo"},
            {"dit": "lec.systeme1.1.dit",
             "cmd": C("du -sh ~/terrain_terminagotchi", "Get-ChildItem ~/terrain_terminagotchi -Recurse | Measure-Object Length -Sum"),
             "re": r"^(du|get-childitem|gci|dir|ls)\b.*terrain", "bravo": "lec.systeme1.1.bravo"},
        ]},
        {"titre": "lec.systeme2.titre", "skill": "Chasseur", "steps": [
            {"dit": "lec.systeme2.0.dit",
             "cmd": C("sleep 300 &", "Start-Process notepad"), "re": r"^(sleep\b.*&|(start-process|saps|start)\b)",
             "bravo": C("lec.systeme2.0.bravo", "lec.systeme2.0.bravo.win")},
            {"dit": "lec.systeme2.1.dit", "cmd": C("jobs", "Get-Process notepad"), "re": r"^(jobs|get-process|gps|ps)\b",
             "bravo": "lec.systeme2.1.bravo"},
            {"dit": "lec.systeme2.2.dit", "cmd": C("kill %1", "Stop-Process -Name notepad"),
             "re": r"^(kill|stop-process|spps|taskkill)\b", "bravo": "lec.systeme2.2.bravo"},
        ]},
    ]},
}

LAUNCHER = "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
ARBRE["Android"] = {"stat": "Agilité", "icone": "📱", "desc": "lec.android.desc",
                    "android": True, "lecons": [
    {"titre": "lec.android0.titre", "skill": "Télécommande", "steps": [
        {"dit": "lec.android0.0.dit", "cmd": 'termux-toast "Coucou !"',
         "re": r"^termux-toast\b", "astuce": "lec.android0.0.astuce",
         "bravo": "lec.android0.0.bravo"},
        {"dit": "lec.android0.1.dit", "cmd": "termux-vibrate -d 400", "re": r"^termux-vibrate\b",
         "bravo": "lec.android0.1.bravo"},
        {"dit": "lec.android0.2.dit", "cmd": "termux-torch on", "re": r"^termux-torch\s+on",
         "bravo": "lec.android0.2.bravo"},
        {"dit": "lec.android0.3.dit", "cmd": "termux-torch off", "re": r"^termux-torch\s+off",
         "bravo": "lec.android0.3.bravo"},
    ]},
    {"titre": "lec.android1.titre", "skill": "Portier", "steps": [
        {"dit": "lec.android1.0.dit", "cmd": "termux-open-url https://fr.wikipedia.org",
         "re": r"^termux-open-url\b", "bravo": "lec.android1.0.bravo"},
        {"dit": "lec.android1.1.dit",
         "cmd": 'am start -a android.intent.action.VIEW -d "geo:0,0?q=Tour Eiffel"',
         "re": r"^am\s+start\b.*geo:", "bravo": "lec.android1.1.bravo"},
        {"dit": "lec.android1.2.dit", "cmd": "am start -a android.intent.action.DIAL -d tel:0123456789",
         "re": r"^am\s+start\b.*DIAL", "bravo": "lec.android1.2.bravo"},
    ]},
    {"titre": "lec.android2.titre", "skill": "Lanceur", "steps": [
        {"dit": "lec.android2.0.dit",
         "cmd": "pm list packages | grep settings", "re": r"^pm\s+list\s+packages",
         "bravo": "lec.android2.0.bravo"},
        {"dit": "lec.android2.1.dit",
         "cmd": f"{LAUNCHER} com.android.settings", "re": r"^am\s+start\b.*LAUNCHER",
         "astuce": "lec.android2.1.astuce",
         "bravo": "lec.android2.1.bravo"},
        {"dit": "lec.android2.2.dit",
         "cmd": f"echo 'ouvre() {{ {LAUNCHER} \"$1\"; }}' >> ~/.bashrc",
         "re": r"ouvre\s*\(\).*>>\s*\S*bashrc", "bravo": "lec.android2.2.bravo"},
        {"dit": "lec.android2.3.dit", "cmd": "source ~/.bashrc", "re": r"^(source|\.)\s+\S*bashrc",
         "bravo": "lec.android2.3.bravo"},
        {"dit": "lec.android2.4.dit", "cmd": "ouvre com.android.settings",
         "re": r"^ouvre\s+\S+", "bravo": "lec.android2.4.bravo"},
    ]},
    {"titre": "lec.android3.titre", "skill": "Majordome", "steps": [
        {"dit": "lec.android3.0.dit", "cmd": "termux-battery-status", "re": r"^termux-battery-status\b",
         "bravo": "lec.android3.0.bravo"},
        {"dit": "lec.android3.1.dit", "cmd": 'termux-tts-speak "Bonjour, je suis ton Terminagotchi"',
         "re": r"^termux-tts-speak\b", "bravo": "lec.android3.1.bravo"},
        {"dit": "lec.android3.2.dit", "cmd": 'termux-clipboard-set "Coucou"',
         "re": r"^termux-clipboard-set\b", "bravo": "lec.android3.2.bravo"},
    ]},
]}


def tx(v):
    """Traduit un texte de leçon : une clé, ou (clé, paramètres)."""
    if isinstance(v, (tuple, list)):
        return t(v[0], **v[1])
    return t(v) if v else ""


def nom_branche(b):
    return t("branche." + b)


def branche_dispo(b):
    return not ARBRE[b].get("android") or OSK == "android"


for _b in ARBRE.values():
    for _i, _l in enumerate(_b["lecons"]):
        _l["niveau"] = 6 + 2 * _i


def tronc_fini(state):
    return state["lesson"] >= len(TRONC)


def lecon_courante(state):
    """(leçon, étiquette) ou (None, None)."""
    if not tronc_fini(state):
        return TRONC[state["lesson"]], t("lec.etiquette.tronc", n=state["lesson"] + 1, total=len(TRONC))
    b = state.get("branche")
    if b:
        i = state["arbre"].get(b, 0)
        les = ARBRE[b]["lecons"]
        if i < len(les):
            return les[i], t("lec.etiquette.branche", branche=nom_branche(b), n=i + 1, total=len(les))
    return None, None


def choisir_branche(state, b):
    if state.get("branche") != b:
        state["branche"] = b
        state["step"] = 0
        state["annonce"] = None
        core.say(state, t("lec.branche.choisie", branche=nom_branche(b)), 8)


def avancer(state, les):
    step = les["steps"][state["step"]]
    core.log(state, f"✔ {step['cmd']}")
    core.say(state, tx(step["bravo"]), 12)
    state["step"] += 1
    core.animer(state, "content")
    if state["step"] < len(les["steps"]):
        core.add_xp(state, 5)
        return True
    state["step"] = 0
    if les["skill"] not in state["skills"]:
        state["skills"].append(les["skill"])
    core.log(state, t("lec.finie.log", titre=tx(les["titre"]), skill=core.nom_skill(les["skill"])))
    msg = t("lec.finie.dit", skill=core.nom_skill(les["skill"]))
    if not tronc_fini(state):
        state["lesson"] += 1
        if tronc_fini(state):
            msg += " " + t("lec.arbre_ouvert")
    else:
        b = state["branche"]
        state["arbre"][b] = state["arbre"].get(b, 0) + 1
        state["stats"][ARBRE[b]["stat"]] += 5
        if state["arbre"][b] >= len(ARBRE[b]["lecons"]):
            core.log(state, t("lec.branche.maitrisee.log", branche=nom_branche(b)))
            msg += " " + t("lec.branche.maitrisee.dit", branche=nom_branche(b))
            state["branche"] = None
    core.add_xp(state, 20)
    core.say(state, msg, 14)
    return False


# ---------------------------------------------------------------- « presque ! »
# Ce que crée une étape « fs » (pour repérer une bonne commande tapée au mauvais endroit).
CREE = {"nid": "nid", "repas": "nid/repas.txt", "secours": "nid/secours.txt", "reserve": "reserve.txt",
        "colis": "colis.html", "carnet": "carnet", "journal": "carnet/journal.txt"}


def indice(step, lignes):
    """Une étape PRESQUE réussie : le texte d'un indice clair, ou None."""
    from . import dressage
    from pathlib import Path
    cmd = step["cmd"]
    ff = dressage.faute_de_frappe(lignes, cmd, chiffres=True)
    if ff:
        return t("dress.indice.faute", tape=ff[0], attendu=ff[1])
    premier = cmd.split()[0].lower()
    tapee = any(l.split() and l.split()[0].lower() == premier for l in lignes)
    if step.get("fs") == "repas" and (T / "nid" / "repas.txt").is_file():
        return t("lec.indice.pomme", cmd=cmd)
    rel = CREE.get(step.get("fs"))
    if tapee and rel and not FS[step["fs"]]():
        nom = rel.split("/")[-1]
        if (Path.home() / nom).exists() or (Path.home() / rel).exists() or (T.is_dir() and any(
                p for p in T.rglob(nom) if p != T / rel)):
            return t("lec.indice.endroit", cmd=f"cd ~/{T.name}")
    return None


def tick(state, lines):
    les, _ = lecon_courante(state)
    if not les or core.level(state["xp"]) < les["niveau"]:
        return
    if state.get("annonce") != les["titre"]:
        state["annonce"] = les["titre"]
        core.say(state, t("lec.annonce"), 10)
        core.animer(state, "parle")
    tapees = [l for l in lines if not est_colle(l)]
    avant = (state["lesson"], state["step"], state.get("branche"), dict(state.get("arbre", {})))
    for line in tapees:
        step = les["steps"][state["step"]]
        if "re" in step and re.search(step["re"], line, re.I):
            if not avancer(state, les):
                state["indice_lecon"] = None
                return
    step = les["steps"][state["step"]]
    if "fs" in step and FS[step["fs"]]():
        avancer(state, les)
    if avant != (state["lesson"], state["step"], state.get("branche"), dict(state.get("arbre", {}))):
        state["indice_lecon"] = None
    elif tapees:
        conseil = indice(step, tapees)
        if conseil and conseil != state.get("indice_lecon"):
            state["indice_lecon"] = conseil
            core.say(state, "💡 " + conseil, 12)
