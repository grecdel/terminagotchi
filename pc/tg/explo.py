"""Exploration : les zones sont de vrais dossiers du terrain de jeu.

Des bestioles sauvages (150 espèces, voir bestiaire.py) s'y cachent en fichiers cachés.
Chaque famille a son habitat (archives, forêt, grotte…) ; plus elle est rare, plus elle se
cache profond (recoin → cachette → sanctuaire). Pour l'apprivoiser : la trouver (ls -a),
la lire (cat), puis réussir son dressage (voir dressage.py). Chaque bestiole est unique.
"""
import random
import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def piege_ansi(t):
    return _ANSI.sub("", t)

from . import bestiaire as B
from . import core
from . import dressage
from .mots import accorder, palier, terme
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg, piege

T = core.TERRAIN
MAX_SAUVAGES = 3


def lieu(zone):
    base = zone.split("/")[0]
    nom = B.HABITATS.get(base, base)
    prof = zone.count("/")
    return nom + ["", " (un recoin)", " (une cachette)", " (le sanctuaire)"][min(prof, 3)]


def debloque(state):
    return "Bâtisseur" in state["skills"] and (T / "nid").is_dir()


def spawn(state):
    if len(state["sauvages"]) >= MAX_SAUVAGES:
        return
    e, shiny, vid = B.tirer()
    legendaires = sum(1 for c in state.get("captures", []) if B.rarete_de(c) == "légendaire")
    if legendaires >= 3 and random.random() < 1 / 15 and not state["collection"].get("Abyssor"):
        e, vid = B.espece("Abyssor"), "classique"   # la mythique secrète #151
    zone = B.variante(e, vid).get("zone", e["zone"])
    dossier = T / zone
    dossier.mkdir(parents=True, exist_ok=True)
    state["explo_n"] += 1
    if state.get("dressage"):
        return
    # l'individu est tiré dès son apparition : stats, rareté et stade sont lisibles sur sa fiche (cat)
    ind = B.individu(e, shiny, zone, vid)
    ind["stade"] = random.choices(B.STADES[:4], [35, 35, 20, 10])[0]
    if shiny:
        ind["teinte"] = round(random.uniform(0.15, 0.85), 3)   # couleur shiny propre à cet individu
    s = {"f": dressage.fiche(e["nom"]).name, "e": e["nom"], "zone": zone, "shiny": shiny, "v": vid, "ind": ind}
    state["sauvages"].append(s)
    core.log(state, accorder("⚔ Un monstre sauvage apparaît : {nom} !", nom=e["nom"]))
    core.animer(state, "attaque")
    dressage.commencer(state, s)
    from . import fenetre
    fenetre.ouvrir_dressage(state)              # le face-à-face s'ouvre dans une nouvelle fenêtre


def check(state):
    nid = T / "nid"
    for s in list(state["sauvages"]):
        p = T / s["f"]
        if p.exists():
            continue
        ailleurs = [x for x in T.rglob(p.name) if x.parent != nid] if T.is_dir() else []
        if ailleurs:
            s["f"] = ailleurs[0].relative_to(T).as_posix()
            s["zone"] = ailleurs[0].parent.relative_to(T).as_posix()
        else:
            state["sauvages"].remove(s)
            if (state.get("dressage") or {}).get("sauvage") == s["f"]:
                dressage.abandonner(state)
            core.log(state, accorder("💨 {nom} a disparu (fiche effacée ?)", nom=s["e"]))
            core.say(state, accorder("Oh non, {nom} a disparu… la broyeuse rm est passée par là ?", nom=s["e"]), 10)
            core.animer(state, "ko")


def tick(state, spontane, proba=1.5 / 480, jeu=0):
    """jeu = nombre de commandes tapées à la main : les monstres n'apparaissent qu'en jouant."""
    if not debloque(state):
        return
    if not state["explo"]:
        state["explo"] = True
        core.log(state, "🌲 Exploration débloquée !")
        spawn(state)
    elif state.get("dressage"):
        pass                                          # pas de nouveau monstre pendant un dressage
    elif jeu and random.random() < min(0.5, 0.04 * jeu):   # ~1 monstre toutes les 25 commandes
        spawn(state)
    check(state)


def _carte_individu(ind):
    e = B.espece(ind["espece"])
    if e is None:
        return []
    r = B.rarete_de(ind)
    sp = B.dessin(e, ind.get("shiny"), grand=True, stade=ind.get("stade", "adulte"), vid=ind.get("variante", "classique"),
                  teinte=ind.get("teinte", 0.5))
    var = ind.get("variante", "classique")
    infos = [
        f"{B.nom_affiche(e, ind.get('shiny'), r)} {DIM}#{e['numero']:03d} · {RESET}{B.libelle_rarete(r)}"
        f"{DIM} · {e['famille']}{' · ' + var if var != 'classique' else ''}{RESET}",
        f"{DIM}signe particulier :{RESET} {ind.get('marque', '?')}",
        f"{DIM}humeur {ind.get('humeur', '?')} · {ind.get('taille', '?')} cm · potentiel {ind.get('potentiel', '?')} %{RESET}",
    ]
    hauteur = max(len(sp), len(infos))
    w = max((len(piege_ansi(x)) for x in sp), default=0)
    lignes = []
    for i in range(hauteur):
        gauche = (sp[i] + " " * (w - len(piege_ansi(sp[i])))) if i < len(sp) else " " * w
        droite = infos[i] if i < len(infos) else ""
        lignes.append("  " + gauche + "  " + droite)
    return lignes


def ecran_collection(state):
    lignes = [f" {fg(213)}── 🐾 Collection de {state['name']} ──{RESET}", ""]
    caps = state.get("captures", [])
    especes_vues = {n for n, k in state["collection"].items() if k}
    par_rarete = {}
    for c in caps:
        r = B.rarete_de(c)
        par_rarete[r] = par_rarete.get(r, 0) + 1
    lignes.append(" Espèces découvertes : " + BOLD + f"{len(especes_vues)}/150" + RESET + "   " + "  ".join(
        f"{B.libelle_rarete(r)} {par_rarete[r]}" for r in B.COULEUR_RARETE if r in par_rarete))
    shinies = sum(1 for c in caps if c.get("shiny"))
    lignes.append(f" Bestioles dressées : {len(caps)}" + (f" · dont {B.arc_en_ciel(f'{shinies} shiny')}" if shinies else ""))
    if state["collection"].get("Abyssor"):
        lignes.append(" " + B.arc_en_ciel("★ Espèce secrète #151 découverte : Abyssor"))
    lignes.append("")
    if caps:
        lignes.append(f" {DIM}Tes dernières captures :{RESET}")
        for ind in caps[-6:][::-1]:
            lignes += _carte_individu(ind)
            lignes.append("")
    else:
        lignes.append(f" {DIM}Aucune bestiole dressée pour l'instant.{RESET}")
    if not state["explo"]:
        lignes.append(f" {DIM}L'exploration s'ouvre avec la leçon « Construire mon nid ».{RESET}")
    else:
        zones = sorted({lieu(s["zone"]) for s in state["sauvages"]})
        lignes.append(" Présences signalées : " + (", ".join(zones) if zones else "aucune pour l'instant"))
        lignes.append(f" {DIM}Fiche d'une espèce : tg bestiaire <nom> · tout le bestiaire : tg site bestiaire{RESET}")
    return lignes


def fiche(state, nom):
    """tg bestiaire <nom> : fiche détaillée (complète seulement si tu l'as déjà capturée)."""
    if not nom:
        vues = sorted((B.espece(n) for n, k in state["collection"].items() if k and B.espece(n)),
                      key=lambda e: e["numero"])
        if not vues:
            return [" Tu n'as encore capturé aucune bestiole. Exemple : tg bestiaire Glitchou"]
        return [" Tes espèces : " + ", ".join(f"#{e['numero']:03d} {e['nom']}" for e in vues),
                f" {DIM}Fiche : tg bestiaire <nom>{RESET}"]
    e = B.espece(nom)
    connue = e is not None and state["collection"].get(e["nom"], 0) > 0
    if e is None or (e.get("secrete") and not connue):
        return [f" Aucune espèce ne s'appelle « {nom} ». Les 150 sont sur le site : tg site bestiaire"]
    entete = f" {BOLD}#{e['numero']:03d}{RESET} {B.nom_affiche(e) if connue else '???'}  " \
             f"{DIM}se montre {e['frequence']}{RESET} · {e['icone']} {e['famille']}"
    lignes = [entete, ""]
    if not connue:
        lignes += [f"  {DIM}Pas encore dans ta troupe.{RESET}",
                   f"  Habitat : {lieu(e['zone'])}  ({e['zone']})",
                   f"  Cette espèce se montre {e['frequence']}, attirée par la commande « {e['attiree_par']} »."]
        return lignes
    sp = B.dessin(e, grand=True)
    vars_ = [v["nom"] for v in e.get("variantes", [])[1:]]
    texte = [e["description"], e["comportement"],
             f"Capacité : {e['capacite']} · point fort : {e['stat']}",
             f"Taille ~{e['taille_cm']} cm · poids ~{e['poids_ko']} Ko",
             B.texte_stats(e["stats"], palier(state)),
             f"Habitat : {lieu(e['zone'])} · attirée par « {e['attiree_par']} »",
             (f"Variantes : {', '.join(vars_)}" if vars_ else ""),
             f"Tu en as dressé {state['collection'][e['nom']]}."]
    for i in range(max(len(sp), len(texte))):
        lg = max((len(piege_ansi(x)) for x in sp), default=0)
        g = (sp[i] + " " * (lg - len(piege_ansi(sp[i])))) if i < len(sp) else " " * lg
        d = texte[i] if i < len(texte) else ""
        lignes.append("  " + g + "  " + d)
    return lignes
