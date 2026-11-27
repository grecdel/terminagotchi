"""La salle d'entraînement : des séances de 5 commandes chronométrées, par discipline.

Chaque séance réussie rapporte des points ; les points font monter le badge de la discipline :
Bit, Octet, Kilo, Méga, Giga, Téra, Péta, Exa (×1024 à chaque marche, comme les octets !),
chacun avec 3 galons. Une séance très rapide (moins de 3 s par commande en moyenne) gagne une étoile ★.
Les mêmes règles existent dans l'appli Android (Entrainement.kt).
"""
import random
import re
import time

from . import core
from .plateforme import BOLD, DIM, RESET, C, est_colle, fg, piege

T = core.TERRAIN
F = "entrainement"
TEXTE = "le chat dort\nle chien court\nle chat mange\nla souris danse\nle chat dort encore\n"
TX = f"{F}/texte.txt"
AT = f"{F}/atelier"

RANGS = [(0, "Bit"), (20, "Octet"), (50, "Kilo"), (100, "Méga"), (180, "Giga"), (300, "Téra"), (480, "Péta"), (750, "Exa")]
PAR_SEANCE = 5
ABANDON = 600                      # secondes sans réponse : la séance s'arrête

# id : (nom, icône, commandes, dans l'ordre ?)
DISCIPLINES = {
    "reperer": ("Se repérer", "🧭", [
        "pwd", "ls", C("ls -a", "ls -Force"), C("ls -l", "ls | Format-List"), "cd ..", "cd ~", "whoami"], False),
    "fichiers": ("Fichiers", "📁", [
        C(f"mkdir -p {AT}", f"New-Item -ItemType Directory -Force {AT}"),
        C(f"touch {AT}/a.txt", f"New-Item -Force {AT}/a.txt"),
        C(f"cp {AT}/a.txt {AT}/b.txt", f"Copy-Item {AT}/a.txt {AT}/b.txt"),
        C(f"mv {AT}/b.txt {AT}/c.txt", f"Move-Item -Force {AT}/b.txt {AT}/c.txt"),
        C(f"rm {AT}/c.txt", f"Remove-Item {AT}/c.txt")], True),
    "lire": ("Lire et chercher", "🔎", [
        C(f"cat {TX}", f"Get-Content {TX}"), C(f"head -n 3 {TX}", f"Get-Content {TX} -Head 3"),
        C(f"tail -n 2 {TX}", f"Get-Content {TX} -Tail 2"), C(f"wc -l {TX}", f"(Get-Content {TX}).Count"),
        C(f"grep chat {TX}", f"Select-String chat {TX}"), C(f"grep -c chat {TX}", f"(Select-String chat {TX}).Count")], False),
    "tuyaux": ("Tuyaux", "🔧", [
        C("ls | wc -l", "ls | Measure-Object"), C(f"cat {TX} | sort", f"Get-Content {TX} | Sort-Object"),
        C(f"sort {TX} | uniq", f"Get-Content {TX} | Sort-Object -Unique"),
        C(f"grep chat {TX} | wc -l", f"Select-String chat {TX} | Measure-Object"),
        C(f"cat {TX} | head -n 2", f"Get-Content {TX} | Select-Object -First 2")], False),
    "systeme": ("Système", "⚙", [
        C("date", "Get-Date"), "whoami", C("uptime", "hostname"), C("df -h", "Get-PSDrive"), C("ps", "Get-Process"),
        C("uname", "$PSVersionTable")], False),
}


def _norm(l):
    return re.sub(r"\s+", " ", l.strip().rstrip("/")).lower()


def etat(state):
    return state.setdefault("entrainement", {"points": {}, "etoiles": {}, "records": {}, "seance": None})


def rang(points):
    """(nom du rang, galon 1-3, points vers le rang suivant ou None)"""
    i = max(k for k, (seuil, _) in enumerate(RANGS) if points >= seuil)
    bas = RANGS[i][0]
    haut = RANGS[i + 1][0] if i + 1 < len(RANGS) else None
    if haut is None:
        return RANGS[i][1], 3, None
    galon = 1 + min(2, int(3 * (points - bas) / (haut - bas)))
    return RANGS[i][1], galon, haut - points


def badge(points, etoiles=0):
    nom, galon, _ = rang(points)
    return f"{nom} {'▮' * galon}{'▯' * (3 - galon)}" + (f" {'★' * min(etoiles, 5)}{'+' if etoiles > 5 else ''}" if etoiles else "")


def commencer(state, disc=None):
    e = etat(state)
    disc = disc if disc in DISCIPLINES else random.choice(list(DISCIPLINES))
    nom, icone, pool, ordre = DISCIPLINES[disc]
    cmds = list(pool[:PAR_SEANCE]) if ordre else random.sample(pool, min(PAR_SEANCE, len(pool)))
    try:
        (T / F).mkdir(parents=True, exist_ok=True)
        if not (T / TX).exists():
            (T / TX).write_text(TEXTE, encoding="utf-8")
    except OSError:
        pass
    now = time.time()
    e["seance"] = {"disc": disc, "cmds": cmds, "i": 0, "debut": now, "t": now, "temps": []}
    core.say(state, f"{icone} Entraînement « {nom} » ! Depuis le terrain de jeu, tape « {piege(cmds[0])} »", 15)
    return f" {icone} Séance « {nom} » : {len(cmds)} commandes à taper le plus vite possible (depuis ~/terrain_terminagotchi)."


def arreter(state):
    etat(state)["seance"] = None
    return " Séance arrêtée."


def courante(state):
    s = etat(state).get("seance")
    return s["cmds"][s["i"]] if s else None


def tick(state, lines):
    e = etat(state)
    s = e.get("seance")
    if not s:
        return
    now = time.time()
    for line in lines:
        if est_colle(line) or s["i"] >= len(s["cmds"]):
            continue
        if _norm(line) == _norm(s["cmds"][s["i"]]):
            s["temps"].append(round(now - s["t"], 1))
            s["t"] = now
            s["i"] += 1
            if s["i"] < len(s["cmds"]):
                core.say(state, f"✔ {s['temps'][-1]} s ! Suivante : « {piege(s['cmds'][s['i']])} »", 15)
    if s["i"] >= len(s["cmds"]):
        _finir(state, s)
    elif now - s["t"] > ABANDON:
        e["seance"] = None
        core.log(state, "🏋 Séance abandonnée (trop longue pause)")


def _finir(state, s):
    e = etat(state)
    e["seance"] = None
    disc = s["disc"]
    nom, icone, _, _ = DISCIPLINES[disc]
    total = round(sum(s["temps"]), 1)
    moy = total / max(1, len(s["temps"]))
    points = 10 + (5 if moy <= 5 else 0) + (5 if moy <= 3 else 0)
    avant = rang(e["points"].get(disc, 0))[:2]
    e["points"][disc] = e["points"].get(disc, 0) + points
    etoile = moy <= 3
    if etoile:
        e["etoiles"][disc] = e["etoiles"].get(disc, 0) + 1
    rec = e["records"].get(disc)
    nouveau = rec is None or total < rec
    if nouveau:
        e["records"][disc] = total
    apres = rang(e["points"][disc])[:2]
    msg = f"{icone} Séance « {nom} » finie en {total} s (+{points} pts){' ★' if etoile else ''}{' — RECORD !' if nouveau else ''}"
    core.log(state, msg)
    if apres != avant:
        core.notif(state, f"🏅 Badge {nom} : {badge(e['points'][disc], e['etoiles'].get(disc, 0))} !")
        msg += f" Nouveau badge : {apres[0]} {'▮' * apres[1]} !"
    core.say(state, msg, 14)
    core.add_xp(state, points)


def ligne_ecran(state):
    """La ligne du défi en cours, pour l'écran principal (ou None)."""
    s = etat(state).get("seance")
    if not s:
        return None
    nom, icone, _, _ = DISCIPLINES[s["disc"]]
    return f"{icone} ENTRAÎNEMENT {nom} {s['i'] + 1}/{len(s['cmds'])} : tape « {piege(s['cmds'][s['i']])} »"


def ecran(state):
    e = etat(state)
    lignes = [f" {fg(213)}── 🏋 Salle d'entraînement ──{RESET}", "",
              f" {DIM}5 commandes à taper à la main, le plus vite possible. Badges : "
              f"{' → '.join(n for _, n in RANGS)}, 3 galons chacun ; ★ = séance éclair (< 3 s par commande).{RESET}", ""]
    for d, (nom, icone, pool, _) in DISCIPLINES.items():
        p = e["points"].get(d, 0)
        _, _, manque = rang(p)
        rec = e["records"].get(d)
        lignes.append(f" {icone} {BOLD}{nom:<17}{RESET} {fg(220)}{badge(p, e['etoiles'].get(d, 0)):<16}{RESET} "
                      f"{DIM}{p} pts{f' · encore {manque} pour monter' if manque else ' · rang maximal !'}"
                      f"{f' · record {rec} s' if rec else ''}{RESET}")
    s = e.get("seance")
    lignes += ["", f" {fg(226)}{ligne_ecran(state)}{RESET}" if s else
               f" {DIM}Commencer : tg entrainement <{'|'.join(DISCIPLINES)}> · arrêter : tg entrainement stop{RESET}"]
    return lignes
