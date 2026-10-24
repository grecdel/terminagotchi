"""Exploration : les zones sont de vrais dossiers du terrain de jeu.
Des bestioles sauvages s'y cachent (fichiers cachés). Pour les capturer,
il faut les trouver (ls -a), les lire (cat) puis les ramener au nid (mv).
"""
import random

from . import core
from .plateforme import DIM, IS_WIN, RESET, fg, piege

T = core.TERRAIN

ESPECES = [
    # nom, rareté, couleur, description
    ("Glitchou",    "commune",    213, "Petit bug grésillant qui adore les fichiers temporaires."),
    ("Octobit",     "commune",    39,  "Pieuvre à 8 bits, range tout par octets."),
    ("Pixelard",    "commune",    221, "Raconte des blagues en 16 couleurs."),
    ("Segfaulte",   "commune",    203, "Se plante partout, mais toujours avec le sourire."),
    ("Kernelou",    "rare",       78,  "Vit au cœur du système, d'un calme absolu."),
    ("Daemonet",    "rare",       141, "Travaille en arrière-plan sans jamais dormir."),
    ("Bugzilla",    "rare",       160, "Énorme, mais personne n'arrive à le reproduire."),
    ("Cronosaure",  "légendaire", 51,  "N'apparaît qu'à heure fixe, réglé comme une horloge."),
    ("Rootkitsune", "légendaire", 208, "Renarde à neuf queues, maîtresse des droits root."),
]
RARETE = {"commune": (70, 15), "rare": (25, 40), "légendaire": (5, 100)}   # (chance %, XP)
ZONES = {
    "commune":    ["foret", "marais"],
    "rare":       ["grotte", "marais/bourbier"],
    "légendaire": ["grotte/profondeurs/abysses"],
}
NOM_ZONE = {"foret": "la forêt", "marais": "le marais", "grotte": "la grotte",
            "marais/bourbier": "le bourbier du marais", "grotte/profondeurs/abysses": "les abysses de la grotte"}
MAX_SAUVAGES = 3


def le(nom):
    return ("l'" if nom[0] in "AEIOUÉ" else "le ") + nom


def debloque(state):
    return "Bâtisseur" in state["skills"] and (T / "nid").is_dir()


def _espece(nom):
    return next(e for e in ESPECES if e[0] == nom)


def spawn(state):
    if len(state["sauvages"]) >= MAX_SAUVAGES:
        return
    rarete = random.choices(list(RARETE), [v[0] for v in RARETE.values()])[0]
    nom = random.choice([e for e in ESPECES if e[1] == rarete])[0]
    zone = random.choice(ZONES[rarete])
    dossier = T / zone
    dossier.mkdir(parents=True, exist_ok=True)
    state["explo_n"] += 1
    fichier = f".bestiole_{nom.lower()}_{state['explo_n']}"
    retour = "../" * (zone.count("/") + 1) + "nid/"
    desc = _espece(nom)[3]
    (dossier / fichier).write_text(
        f"Un {nom} sauvage se cache ici ! ({rarete})\n"
        f"« {desc} »\n\n"
        f"Pour le capturer, ramène-le dans le nid de {state['name']} :\n"
        f"   {piege(f'mv {fichier} {retour}')}\n\n"
        f"(Tape la commande toi-même : un copier-coller le ferait fuir !)\n",
        encoding="utf-8")
    state["sauvages"].append({"f": f"{zone}/{fichier}", "e": nom, "zone": zone})
    voir = piege("dir -Force" if IS_WIN else "ls -a")
    core.log(state, f"🐾 Quelque chose bouge dans {NOM_ZONE[zone]}…")
    core.say(state, f"Je sens une présence dans {NOM_ZONE[zone]} ({zone}) ! "
                    f"Les bestioles se cachent : essaie « {voir} ».", 15)


def check(state):
    nid = T / "nid"
    # captures : bestiole déposée dans le nid
    if nid.is_dir():
        for f in list(nid.glob(".bestiole_*")):
            sauvage = next((s for s in state["sauvages"] if s["f"].endswith("/" + f.name)), None)
            if not sauvage:
                continue
            nom = sauvage["e"]
            rarete = _espece(nom)[1]
            state["sauvages"].remove(sauvage)
            state["collection"][nom] = state["collection"].get(nom, 0) + 1
            try:
                f.unlink()
            except OSError:
                pass
            core.log(state, f"🎯 {nom} capturé ! ({rarete})")
            core.say(state, f"Bienvenue au nid, {nom} ! Ta collection grandit ([c] pour la voir).", 12)
            state["stats"][random.choice(list(state["stats"]))] += 2
            core.add_xp(state, RARETE[rarete][1])
    # bestioles déplacées ailleurs ou supprimées
    for s in list(state["sauvages"]):
        p = T / s["f"]
        if p.exists():
            continue
        nom_f = p.name
        ailleurs = [x for x in T.rglob(nom_f) if x.parent != nid] if T.is_dir() else []
        if ailleurs:
            s["f"] = ailleurs[0].relative_to(T).as_posix()
            s["zone"] = ailleurs[0].parent.relative_to(T).as_posix()
        else:
            state["sauvages"].remove(s)
            core.log(state, f"💨 {le(s['e'])[0].upper() + le(s['e'])[1:]} s'est enfui (fichier effacé ?)")
            core.say(state, f"Oh non, {le(s['e'])} a disparu… un rm de trop ?", 10)


def tick(state, spontane, proba=1.5 / 480):
    if not debloque(state):
        return
    if not state["explo"]:
        state["explo"] = True
        core.log(state, "🌲 Exploration débloquée !")
        spawn(state)
    elif spontane and random.random() < proba:      # ~1 bestiole toutes les 8 min
        spawn(state)
    check(state)


def ecran_collection(state):
    from .sprites import bestiole
    lignes = [f" {fg(213)}── Collection de {state['name']} ──{RESET}", ""]
    total = sum(state["collection"].values())
    for i, (nom, rarete, coul, desc) in enumerate(ESPECES):
        n = state["collection"].get(nom, 0)
        if n:
            sp = bestiole(i, coul)
            lignes.append(f"  {sp[0]}  {fg(coul)}{nom}{RESET} ×{n}  {DIM}{rarete}{RESET}")
            lignes.append(f"  {sp[1]}  {DIM}{desc}{RESET}")
            lignes.append(f"  {sp[2]}")
        else:
            lignes.append(f"  {DIM}········  ??? ({rarete}){RESET}")
    lignes.append("")
    lignes.append(f" Espèces : {len(state['collection'])}/{len(ESPECES)} · captures : {total}")
    if not state["explo"]:
        lignes.append(f" {DIM}L'exploration s'ouvre avec la leçon « Construire mon nid ».{RESET}")
    else:
        zones = sorted({NOM_ZONE.get(s['zone'], s['zone']) for s in state["sauvages"]})
        lignes.append(" Présences signalées : " + (", ".join(zones) if zones else "aucune pour l'instant"))
        lignes.append(f" {DIM}Zones : dossiers de ~/terrain_terminagotchi · indice : {piege('cat')} sur une bestiole{RESET}")
    return lignes
