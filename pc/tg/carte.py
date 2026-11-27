"""La carte qui pousse : le vrai terrain de jeu, dessiné au fil de tes découvertes.

Chaque dossier où tu entres (cd) se dévoile sur la carte ; ses sous-dossiers encore inconnus restent dans
le brouillard (░ ???). Les monstres sauvages repérés y apparaissent. Même règle dans l'appli (Carte.kt).
"""
import os

from .langue import tr
from . import core
from .plateforme import BOLD, DIM, RESET, fg

T = core.TERRAIN
PROFONDEUR = 5
ICONES = {
    "nid": "🪺", "monde": "🌍", "citadelle": "🏰", "crypte": "🗝", "ondes": "📡", "forge": "🔨", "guilde": "🛠",
    "ia": "🔭", "donnees": "📊", "atelier": "🤖", "entrainement": "🏋", "donjon": "🏯", "carnet": "📓", "jeu": "🎮",
    "volcan": "🌋", "sommets": "🏔", "plaine": "🌾", "foret": "🌲", "termitiere": "🐜", "abysses": "🌊",
    "nuages": "☁", "ruines": "🏛", "faille": "🌀", "recoin": "🕳", "cachette": "🕳", "sanctuaire": "✨",
}


def etat(state):
    return state.setdefault("carte", {"vus": [], "ici": ""})


def relatif(chemin):
    """Chemin relatif au terrain (« volcan/recoin »), ou None s'il est en dehors."""
    try:
        r = os.path.relpath(os.path.realpath(chemin), os.path.realpath(T))
    except ValueError:
        return None
    if r == ".":
        return ""
    if r.startswith(".."):
        return None
    return r.replace(os.sep, "/")


def visiter(state, chemin):
    """Le joueur est dans ce dossier : il se dévoile (avec tous ses parents)."""
    r = relatif(chemin)
    if r is None:
        return
    e = etat(state)
    e["ici"] = r
    morceaux = r.split("/") if r else []
    nouveaux = []
    for i in range(len(morceaux) + 1):
        p = "/".join(morceaux[:i])
        if p not in e["vus"]:
            e["vus"].append(p)
            if p:
                nouveaux.append(p)
    for p in nouveaux:
        core.log(state, f"🗺 Nouveau lieu sur la carte : {p.split('/')[-1]}")
        core.add_xp(state, 3)


def _dossiers(d):
    try:
        return sorted(x for x in d.iterdir() if x.is_dir() and not x.name.startswith("."))
    except OSError:
        return []


def _total():
    n = 0
    for racine, dirs, _ in os.walk(T):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        if os.path.relpath(racine, T).count(os.sep) < PROFONDEUR:
            n += len(dirs)
    return n


def ecran(state):
    e = etat(state)
    vus = set(e["vus"])
    monstres = {s["zone"] for s in state.get("sauvages", [])}
    if not T.is_dir():
        return [" " + tr("La carte est vide : le terrain de jeu n'existe pas encore (leçon « Construire mon nid »).")]
    lignes = [f" {fg(213)}── 🗺 {tr('La carte du Terminaworld')} ──{RESET}", ""]
    toi = "" in vus and e.get("ici") == ""
    lignes.append(f" 🌳 {BOLD}terrain_terminagotchi{RESET} {DIM}{tr('(la Racine du camp)')}{RESET}" + (f"  {fg(226)}{tr('◀ tu es ici')}{RESET}" if toi else ""))
    connus = 0

    def dessiner(d, rel, prefixe, prof):
        nonlocal connus
        enfants = _dossiers(d)
        for i, c in enumerate(enfants):
            r = f"{rel}/{c.name}" if rel else c.name
            dernier = i == len(enfants) - 1
            branche = "└─ " if dernier else "├─ "
            if r in vus:
                connus += 1
                ico = ICONES.get(c.name, "📁")
                ici = f"  {fg(226)}{tr('◀ tu es ici')}{RESET}" if e.get("ici") == r else ""
                m = f"  {fg(196)}{tr('⚔ un monstre !')}{RESET}" if r in monstres else ""
                lignes.append(f" {prefixe}{branche}{ico} {c.name}{m}{ici}")
                if prof < PROFONDEUR:
                    dessiner(c, r, prefixe + ("   " if dernier else "│  "), prof + 1)
            else:
                lignes.append(f" {prefixe}{branche}{DIM}░░ ???{RESET}")

    if "" in vus:
        dessiner(T, "", "", 1)
    total = _total()
    pct = round(100 * connus / total) if total else 0
    lignes += ["", " " + tr("Carte dévoilée : {c}/{t} lieux ({p} %)").format(c=connus, t=total, p=pct),
               f" {DIM}{tr('Entre dans un lieu (cd) pour le dévoiler. ░░ ??? = un lieu encore dans le brouillard.')}{RESET}"]
    return lignes
