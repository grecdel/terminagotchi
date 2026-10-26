"""Exploration : les zones sont de vrais dossiers du terrain de jeu.

Des bestioles sauvages (150 espèces, voir bestiaire.py) s'y cachent en fichiers cachés.
Chaque famille a son habitat (archives, forêt, grotte…) ; plus elle est rare, plus elle se
cache profond (recoin → cachette → sanctuaire). Pour l'apprivoiser : la trouver (ls -a),
la lire (cat), puis réussir son dressage (voir dressage.py). Chaque bestiole est unique.

Attirance : chaque famille est « attirée par » une commande (chmod pour les Démons, ls pour les
Sylvestres…, champ attiree_par). La taper attire cette famille : la prochaine apparition (dans les
10 minutes) a environ 3 fois plus de chances d'en être une. Pendant un chapitre de l'histoire
(« La Maison endormie », histoire.py), la famille de l'aile en cours est attirée de la même façon
(si sa commande a déjà été goûtée : le serveur le vérifie). La famille entre dans le tirage signé
(voir tirage.py) : le serveur peut toujours le refaire.

Le tout premier monstre (aucune bestiole dressée) est une espèce courante, de rareté commune :
on passe aux compteurs suivants de la graine jusqu'à en trouver une (chaque compteur reste
vérifiable par le serveur ; le tirage lui-même ne change pas).
"""
import random
import re
import time

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def piege_ansi(t):
    return _ANSI.sub("", t)

from . import bestiaire as B
from . import core
from . import dressage
from . import tirage
from .langue import largeur, t
from .mots import palier, terme
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg, piege

T = core.TERRAIN
MAX_SAUVAGES = 3
DUREE_ATTIRANCE = 600            # secondes : la commande attire la prochaine apparition pendant 10 min
ESSAIS_PREMIER = 30              # compteurs essayés au plus pour un premier monstre facile


def _icone(famille):
    return next((e["icone"] for e in B.publiques() if e["famille"] == famille), "")


def attirer(state, lignes):
    """Une commande « attiree_par » tapée à la main attire sa famille (la dernière tapée gagne)."""
    par_cmd = {c: f for f, c in B.familles().items()}
    for l in lignes:
        if core.est_colle(l):
            continue
        cmd = core.first_word(l) or ""
        f = par_cmd.get(cmd)
        if not f or cmd not in state.get("seen", []):     # le serveur exige une commande vraiment goûtée
            continue
        avant = attirance(state)
        state["attirance"] = {"famille": f, "cmd": cmd, "t": time.time()}
        if avant != f and not state.get("dressage"):
            core.log(state, t("exp.attire.log", cmd=cmd, famille=f))
            core.say(state, t("exp.attire.dit", cmd=cmd, famille=f, icone=_icone(f)), 8)


def attirance(state):
    """La famille attirée en ce moment, ou None."""
    a = state.get("attirance") or {}
    if a.get("famille") in B.familles() and time.time() - a.get("t", 0) < DUREE_ATTIRANCE:
        return a["famille"]
    return None


def facile(e, ind):
    """Un premier monstre facile : espèce courante (« souvent ») et individu de rareté commune."""
    return e.get("frequence") == "souvent" and B.rarete_de(ind) == "commune"


def _au_hasard(zone_de, abyssor_permis, attire):
    """Sans graine (pas de compte, hors ligne longtemps) : tirage local, « non vérifié » sur le site."""
    e, shiny, vid = B.tirer(attire=attire)
    if abyssor_permis and random.random() < 1 / 15:
        e, vid = B.espece("Abyssor"), "classique"
    # l'individu est tiré dès son apparition : stats, rareté et stade sont lisibles sur sa fiche (cat)
    ind = B.individu(e, shiny, zone_de(e, vid), vid)
    ind["stade"] = random.choices(B.STADES[:4], [35, 35, 20, 10])[0]
    if shiny:
        ind["teinte"] = round(random.uniform(0.15, 0.85), 3)   # couleur shiny propre à cet individu
    return e, ind


def lieu(zone):
    base = zone.split("/")[0]
    nom = B.HABITATS.get(base, base)
    prof = zone.count("/")
    return nom + ["", " " + t("exp.recoin"), " " + t("exp.cachette"), " " + t("exp.sanctuaire")][min(prof, 3)]


def debloque(state):
    return "Bâtisseur" in state["skills"] and (T / "nid").is_dir()


def spawn(state):
    if len(state["sauvages"]) >= MAX_SAUVAGES or state.get("dressage"):
        return                                    # pas de nouveau monstre pendant un dressage
    legendaires = sum(1 for c in state.get("captures", []) if B.rarete_de(c) == "légendaire")
    abyssor_permis = legendaires >= 3 and not state["collection"].get("Abyssor")   # la mythique secrète #151
    zone_de = lambda e_, v_: B.variante(e_, v_).get("zone", e_["zone"])  # noqa: E731
    attire = attirance(state)
    if not attire:                                  # le chapitre en cours attire sa famille (histoire.py)
        from . import histoire
        attire = histoire.famille_attiree(state)
    premier = not state.get("captures")             # le tout premier monstre : facile
    e = ind = None
    for _ in range(ESSAIS_PREMIER if premier else 1):
        # anti-triche : tirage vérifiable par le serveur si une graine du jour est en cache (voir tirage.py)
        r = tirage.apparition(state, zone_de, abyssor_permis and not premier, attire)
        e, ind = r or _au_hasard(zone_de, abyssor_permis and not premier, attire)
        if not premier or facile(e, ind):
            break
    if attire:
        state["attirance"] = None                   # une commande attire UNE apparition
    shiny, vid = ind["shiny"], ind["variante"]
    zone = zone_de(e, vid)
    dossier = T / zone
    dossier.mkdir(parents=True, exist_ok=True)
    state["explo_n"] += 1
    s = {"f": dressage.fiche(e["nom"]).name, "e": e["nom"], "zone": zone, "shiny": shiny, "v": vid, "ind": ind}
    state["sauvages"].append(s)
    core.log(state, t("dress.apparait", nom=e["nom"], eclat=""))
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
            core.log(state, t("exp.disparu.log", nom=s["e"]))
            core.say(state, t("exp.disparu.dit", nom=s["e"]), 10)
            core.animer(state, "ko")


def tick(state, spontane, proba=1.5 / 480, jeu=0, lignes=()):
    """jeu = nombre de commandes tapées à la main : les monstres n'apparaissent qu'en jouant."""
    attirer(state, lignes)
    if not debloque(state):
        return
    if not state["explo"]:
        state["explo"] = True
        core.log(state, t("exp.debloquee"))
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
    from . import aura
    sp = B.dessin(e, ind.get("shiny"), grand=True, stade=ind.get("stade", "adulte"), vid=ind.get("variante", "classique"),
                  teinte=ind.get("teinte", 0.5), aura=aura.palier_ind(ind))     # l'aura montre sa rareté
    var = ind.get("variante", "classique")
    infos = [
        f"{B.nom_affiche(e, ind.get('shiny'), r)} {DIM}#{e['numero']:03d} · {RESET}{B.libelle_rarete(r)}"
        f"{DIM} · {e['famille']}{' · ' + var if var != 'classique' else ''}{RESET}",
        f"{DIM}" + t("exp.signe") + f"{RESET} {ind.get('marque', '?')}",
        f"{DIM}" + t("exp.humeur", humeur=ind.get("humeur", "?"), cm=ind.get("taille", "?"), pot=ind.get("potentiel", "?")) + RESET,
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
    lignes = [f" {fg(213)}── 🐾 " + t("exp.collection.titre", nom=state["name"]) + f" ──{RESET}", ""]
    caps = state.get("captures", [])
    especes_vues = {n for n, k in state["collection"].items() if k}
    par_rarete = {}
    for c in caps:
        r = B.rarete_de(c)
        par_rarete[r] = par_rarete.get(r, 0) + 1
    lignes.append(" " + t("exp.especes", n=BOLD + f"{len(especes_vues)}/150" + RESET) + "   " + "  ".join(
        f"{B.libelle_rarete(r)} {par_rarete[r]}" for r in B.COULEUR_RARETE if r in par_rarete))
    shinies = sum(1 for c in caps if c.get("shiny"))
    lignes.append(" " + t("exp.dressees", n=len(caps))
                  + (" · " + t("exp.dont_shiny", shiny=B.arc_en_ciel(f"{shinies} shiny")) if shinies else ""))
    if state["collection"].get("Abyssor"):
        lignes.append(" " + B.arc_en_ciel(t("exp.abyssor")))
    lignes.append("")
    if caps:
        lignes.append(f" {DIM}" + t("exp.dernieres") + RESET)
        for ind in caps[-6:][::-1]:
            lignes += _carte_individu(ind)
            lignes.append("")
        lignes.append(f" {DIM}" + t("aura.legende") + RESET)     # la lueur autour des bestioles (aura.py)
    else:
        lignes.append(f" {DIM}" + t("exp.aucune_dressee") + RESET)
    if not state["explo"]:
        lignes.append(f" {DIM}" + t("exp.s_ouvre", lecon=t("lec.t1.titre")) + RESET)
    else:
        zones = sorted({lieu(s["zone"]) for s in state["sauvages"]})
        lignes.append(" " + t("exp.presences", liste=", ".join(zones) if zones else t("exp.aucune_presence")))
        f = attirance(state)
        lignes.append(" " + (t("exp.attirance", icone=_icone(f), famille=f, cmd=B.familles()[f]) if f
                             else t("exp.attirance.aucune")))
        lignes.append(f" {DIM}" + t("exp.pied") + RESET)
    return lignes


def fiche(state, nom):
    """tg bestiaire <nom> : fiche détaillée (complète seulement si tu l'as déjà capturée)."""
    if not nom:
        vues = sorted((B.espece(n) for n, k in state["collection"].items() if k and B.espece(n)),
                      key=lambda e: e["numero"])
        if not vues:
            return [" " + t("exp.fiche.aucune")]
        return [" " + t("exp.fiche.tes_especes", liste=", ".join(f"#{e['numero']:03d} {e['nom']}" for e in vues)),
                f" {DIM}" + t("exp.fiche.aide") + RESET]
    e = B.espece(nom)
    connue = e is not None and state["collection"].get(e["nom"], 0) > 0
    if e is None or (e.get("secrete") and not connue):
        return [" " + t("exp.fiche.inconnue", nom=nom)]
    entete = f" {BOLD}#{e['numero']:03d}{RESET} {B.nom_affiche(e) if connue else '???'}  " \
             f"{DIM}" + t("exp.fiche.se_montre", frequence=B.nom_frequence(e["frequence"])) + f"{RESET} · {e['icone']} {e['famille']}"
    lignes = [entete, ""]
    if not connue:
        lignes += [f"  {DIM}" + t("exp.fiche.pas_encore") + RESET,
                   "  " + t("exp.fiche.habitat", lieu=lieu(e["zone"])) + f"  ({e['zone']})",
                   "  " + t("exp.fiche.attiree", frequence=B.nom_frequence(e["frequence"]), cmd=e["attiree_par"])]
        return lignes
    sp = B.dessin(e, grand=True)
    vars_ = [v["nom"] for v in e.get("variantes", [])[1:]]
    texte = [e["description"], e["comportement"],
             t("exp.fiche.capacite", capacite=e["capacite"], stat=core.nom_stat(e["stat"])),
             t("exp.fiche.taille", cm=e["taille_cm"], ko=e["poids_ko"]),
             B.texte_stats(e["stats"], palier(state)),
             t("exp.fiche.habitat_attiree", lieu=lieu(e["zone"]), cmd=e["attiree_par"]),
             (t("exp.fiche.variantes", liste=", ".join(vars_)) if vars_ else ""),
             t("exp.fiche.dresses", n=state["collection"][e["nom"]])]
    for i in range(max(len(sp), len(texte))):
        lg = max((len(piege_ansi(x)) for x in sp), default=0)
        g = (sp[i] + " " * (lg - len(piege_ansi(sp[i])))) if i < len(sp) else " " * lg
        d = texte[i] if i < len(texte) else ""
        lignes.append("  " + g + "  " + d)
    return lignes
