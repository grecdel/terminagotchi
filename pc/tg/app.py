"""Écran principal, menus (recherche, arbre, collection) et boucle de jeu."""
import os
import random
import re
import sys
import textwrap
import time

import subprocess

from . import (compagnon, core, dressage, entrainement, envies, equipe, guide, exemples, explique, explo, histoire, intro, lecons, lexique, maths,
               maison, notif, quetes, recense, registre, sprites, terrain)
from .bestiaire import arc_en_ciel
from . import langue, rendu_fin, satiete, sur
from .langue import ajuster, envelopper, largeur, raccourcir, t
from .mots import palier, terme

SYNC_AUTO = False   # synchro en fond, seulement pour les modes qui restent ouverts
from .plateforme import (BOLD, DIM, DISTRO, IS_WIN, OS_NAMES, OSK, RESET, Clavier, clear, fg, piege)


def title_line(text, color=244):
    return fg(color) + "── " + text + " " + "─" * max(3, 44 - largeur(text)) + RESET


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def render(state, frame, interactif, anim=None, tic=None):
    """anim : les lignes d'une image d'animation à afficher à la place du dessin habituel ; tic : l'image de vie de la
    créature au repos (dessin_guide)."""
    d = state.get("dressage")
    if d and not d.get("fenetre"):          # pas de fenêtre possible (pas d'écran graphique) : on l'affiche ici
        return render_dressage(state, interactif, anim)
    if isinstance(anim, intro.Ecran) or intro.en_cours(state):   # le camp, l'œuf qui arrive, la liste (intro.py)
        lignes = intro.lignes_ecran_oeuf(state, frame, anim)
        return "\n".join(lignes + ["", title_line(t("app.journal"))] + [" " + l for l in state["log"][-3:]]) + "\n"
    cid = intro.a_montrer(state) if interactif else None
    if cid and not anim:                    # une nouveauté à présenter (merci, puis chaque fonction qui s'ouvre)
        return "\n".join(intro.lignes_ecran(state, cid)) + "\n"
    lvl = core.level(state["xp"])
    st = core.stage(lvl)
    if anim:
        w = max(len(_ANSI.sub("", l)) for l in anim)
        sprite = list(anim)
    else:
        sprite, w = dessin_guide(state, frame, tic)                    # le guide (+ son aura de rareté, tg aura)
        sprite = ([" " * w] + sprite) if frame % 2 else (sprite + [" " * w])
    lg = max(20, w)
    left = ["  " + line + " " * (lg - w) for line in sprite]

    forme = core.forme(state, lvl)
    lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
    stats = "  ".join(f"{fg(v['color'])}{core.nom_stat(v['stat'], court=True)}{RESET} {BOLD}{state['stats'][v['stat']]}{RESET}"
                      for v in core.CATEGORIES.values())
    nb_sk = len(state["skills"])
    xp_l = t("app.xp")
    jauges = envies.compact(state)                # les 6 envies, en petit (tg envies : le détail)
    m = envies.moment(state)
    right = [
        (arc_en_ciel(state["name"] + " ✨") if state.get("shiny") else f"{BOLD}{state['name']}{RESET}")
        + " · " + t("app.forme_niveau", forme=forme, n=lvl)
        + (" " + entrainement.titre_colore(state) if entrainement.titres(state) else ""),
        f"{DIM}" + t("app.caractere", trait=core.nom_trait(state["trait"])) + RESET,
        f"{xp_l} {sprites.bar(state['xp'] - lo, hi - lo)} {state['xp']}/{hi}",
    ]
    if intro.ouvert(state, "envies"):             # les jauges des envies arrivent avec leur présentation
        right += [f"{jauges[0]}  {DIM}{envies.humeur(state)}{RESET}",
                  jauges[1] + (f"  {fg(214)}💭 {envies.ICONES[m['e']]} {envies.nom(m['e'])}{RESET}" if m else ""),
                  f"{satiete.ligne_etat(state)}  {DIM}🍽{RESET} {satiete.assiette(state)}"]   # l'assiette du jour
    if intro.ouvert(state, "equipe"):             # P2-5 : INT AGI FOR END (du jargon à 7 ans) avec l'équipe seulement
        right += [stats, t("app.competences_bestioles", n=nb_sk, b=sum(state["collection"].values()))]
    if state.get("captures") and intro.ouvert(state, "equipe"):     # le guide (tg guide) : en tête de l'équipe
        gm = guide.actuel(state)
        right.append(f"🧭 {guide.ICONES[gm[2]]} {gm[1]} {DIM}· {t('guide.talent.' + guide.TALENTS[gm[2]])}{RESET}")
    n = max(len(left), len(right))
    left += [" " * (lg + 2)] * (n - len(left))
    right += [""] * (n - len(right))
    lines = [l + r for l, r in zip(left, right)]

    b = core.bulle_courante(state)
    if b:
        wrapped = envelopper(b[0], 52)
        lines.append(f"  {BOLD}» {wrapped[0]}{RESET}")
        lines += [f"    {BOLD}{x}{RESET}" for x in wrapped[1:]]
    else:
        lines.append("")

    d = state["defi"]
    if d:
        reste = max(0, core.defi_duree(state) - (time.time() - d["start"]))
        lines.append(title_line(t("app.defi", cmd=piege(d["cmd"]), s=f"{reste:.0f}"), 226))

    d = state.get("dressage")
    if d:
        lines.append(f" {fg(196)}{BOLD}" + t("app.monstre_fenetre", nom=d["espece"]) + f"{RESET} "
                     f"{DIM}" + t("app.monstre_fenetre.fermee") + RESET)

    perdu = state.get("terrain_perdu")
    if perdu:                                 # le terrain a été effacé : la commande pour le reconstruire
        lines.append(title_line(t("app.terrain.titre"), 196))
        lines.append(f"   {fg(226)}➜ `{piege(perdu['cmd'])}`{RESET}")
        for x in envelopper(t("app.terrain.pourquoi"), 78):
            lines.append(f"   {DIM}{x}{RESET}")
    les, etiquette = lecons.lecon_courante(state)
    from . import placement
    if placement.actif(state):                    # G-13 : le petit test « je connais déjà »
        lines.append(title_line("🧩 " + placement.but(state), 213))
    if les:
        ch = histoire.PAR_CHAP[les["chap"]]
        lines.append(title_line(t("hist.ecran.monde" if ch.get("monde") else "hist.ecran.chapitre",
                                  icone=maison.ICONES.get(ch["piece"], "📖"),
                                  chapitre=histoire.nom_chapitre(ch["id"]), n=ch["n"]), 213))
        if lvl < les["niveau"]:
            lines.append(title_line(t("app.lecon.niveau_requis", etiquette=etiquette, n=les["niveau"])))
            idees, n = core.faim_d_apprendre(state, les["niveau"])
            lines.append(" " + t("app.lecon.faim", cmds=f"{fg(226)}{'   '.join(idees)}{RESET}"))
            lines.append(f" {DIM}" + t("app.lecon.encore", n=n) + RESET)
        else:
            step = les["steps"][state["step"]]
            lines.append(f" {fg(213)}{BOLD}" + t("app.lecon.titre", etiquette=etiquette, titre=lecons.tx(les["titre"]),
                                                n=state["step"] + 1, total=len(les["steps"])) + RESET)
            for x in envelopper(lecons.tx(step["dit"]), 78):
                lines.append(f" {x}")
            lines.append(f"   {fg(226)}➜ {compagnon.commande_montree(state, step)}{RESET}")
            grands = lecons.adulte(step)                          # G-32 : 🧑 la version des grands, toujours là
            if grands:
                for x in envelopper("🧑 " + grands, 76):
                    lines.append(f"   {DIM}{x}{RESET}")
            from . import vrai
            v = vrai.ligne(step)                                  # G-10 : 💻 et dans un vrai terminal ?
            if v:
                for x in envelopper(v, 76):
                    lines.append(f"   {DIM}{x}{RESET}")
            for montre, cle in explique.nouvelles(state, step["cmd"]):      # 💡 Le -r veut dire…
                for k, p in enumerate(explique.phrases(state, montre, cle)):   # (+ pour les grands)
                    for x in envelopper(p, 74 - 2 * k):
                        lines.append(f"   {'  ' * k}{DIM}{x}{RESET}")
            from . import verif
            lieu = verif.lieu_attendu(state, step)               # 📁 d'où la commande marche (calculé, G-34)
            if lieu is not None:
                lines.append(f"   {DIM}" + t("app.lecon.depuis", terrain=histoire.nom_lieu(lieu) if lieu else
                                            terme("terrain", palier(state)), cmd=verif.cd_vers(lieu)) + RESET)
            if step.get("astuce"):
                lines.append(f"   {DIM}{lecons.tx(step['astuce'])}{RESET}")
            if state.get("indice_lecon"):
                for x in envelopper("💡 " + state["indice_lecon"], 76):
                    lines.append(f"   {fg(214)}{x}{RESET}")
    else:
        b = histoire.bandeau(state)
        if b:
            lines.append(title_line(b[0], 213))
            for x in envelopper(b[1], 78):
                lines.append(f" {x}")
    suivie = quetes.ligne_suivie(state) if intro.ouvert(state, "quetes") else None
    if suivie:
        lines.append(f" {fg(214)}{suivie}{RESET}")

    if intro.ouvert(state, "equipe"):             # « Ce que je digère (Ubuntu) : git, curl » : plus tard (P2-5)
        lines.append(title_line(t("app.digere", os=DISTRO or OS_NAMES[OSK])))
        lc = max(largeur(core.nom_stat(v["stat"])) for v in core.CATEGORIES.values()) + 2
        for k, v in core.CATEGORIES.items():
            lines.append(f" {fg(v['color'])}{ajuster(core.nom_stat(v['stat']), lc)}{RESET}{core.EXAMPLES[OSK][k]}")

    lines.append(title_line(t("app.journal")))
    if state["total"] == 0:
        lines.append(" " + t("app.journal.vide"))
        if IS_WIN:
            lines.append(" " + t("app.journal.powershell"))
        elif not compagnon.est_installe():
            lines.append(f" {fg(226)}" + t("app.journal.compagnon") + RESET)
    lines += [" " + l for l in state["log"][-4:]]
    if interactif:
        lines.append(f"{fg(244)} " + touches(state) + RESET)
    else:
        lines.append(f"{DIM} " + t("app.digere_ferme") + RESET)
    return "\n".join(lines) + "\n"


# les touches de la fenêtre et la fonction du jeu qu'elles ouvrent (intro.json : avant, « pas encore »)
TOUCHES = {"/": "lexique", "r": "lexique", "?": "lexique", "l": "lexique", "a": "quetes", "j": "quetes", "m": "carte",
           "c": "equipe", "u": "extras"}


def touches(state):
    """Le pied de la fenêtre, sans les touches des fonctions pas encore ouvertes ([m] carte…)."""
    morceaux = re.split(r"(?=\[)", t("app.touches.histoire"))
    garde = [x for x in morceaux if not (len(x) > 2 and x[0] == "[" and x[2] == "]"
                                         and x[1] in TOUCHES and not intro.ouvert(state, TOUCHES[x[1]]))]
    return "".join(garde).strip()


_CACHE_GUIDE = {}


VIE_IPS = 8           # la créature de l'écran principal vit à 8 images par seconde (vie.py) ; on saute des images


def dessin_guide(state, frame=0, tic=None):
    """La créature de l'écran principal : le GUIDE actuel (le compagnon, ou la bestiole en tête de l'équipe,
    à son stade, dans sa variante, avec son aura de rareté), sinon le compagnon sorti de l'œuf. Elle vit (yeux qui
    clignent, respiration, ondulations : vie.py) au rendu le plus fin du terminal (rendu_fin.py), et son aura brille
    selon le soin (aura.eclat). tic : le numéro de l'image de vie (la fenêtre le prend sur l'horloge : des images
    sautées, jamais de retard)."""
    from . import aura as A
    from . import rendu_fin
    tic = tic or 0
    ec = A.eclat(state)
    mode = rendu_fin.mode()
    m = guide.actuel(state)
    ind = m[3]
    r = None
    if ind is not None:
        cle = ("ind", ind.get("id"), equipe.stade(ind), ind.get("variante"), ind.get("shiny"),
               bool(aura_ecran(state) is not None), aura_active(state), ec, mode)
        r = _CACHE_GUIDE.get(cle)
        if r is None:
            try:
                r = equipe.animation(ind, "statique", aura=aura_active(state), fin=True, eclat=ec)
            except Exception:
                r = None
            _CACHE_GUIDE.clear()
            _CACHE_GUIDE[cle] = r
    elif sprites.espece_compagnon(state) and core.stage(core.level(state["xp"])) >= 1:
        cle = ("compagnon", state.get("espece_compagnon"), core.stage(core.level(state["xp"])), state.get("shiny"),
               aura_ecran(state), ec, mode)
        r = _CACHE_GUIDE.get(cle)
        if r is None:
            try:
                r = sprites.animation(state, "statique", aura_ecran(state), fin=True, eclat=ec)
            except Exception:
                r = None
            _CACHE_GUIDE.clear()
            _CACHE_GUIDE[cle] = r
    if r and len(r[0]):
        image = r[0][tic % len(r[0])]
        return list(image), max(largeur(l) for l in image if "\x1b7" not in l)
    return sprites.creature(state, aura_ecran(state), frame)


def aura_active(state):
    from . import aura
    return aura.active(state)


def vue_dressage():
    """tg dressage : la fenêtre du face-à-face, qui se met à jour toute seule pendant que tu tapes ailleurs."""
    sys.stdout.write("\033[?25l")
    try:
        fini = None
        vu = None                                 # le dernier face-à-face affiché (pour l'animation de fin)
        vu_troupe = time.time()                   # les animations du combat (attaque, victoire, ko)
        while True:
            state = etape(spontane=False, defis=False)
            if state is None:
                return
            at = state.get("anim_troupe")
            if at and at.get("t", 0) > vu_troupe:
                vu_troupe = at["t"]
                if time.time() - at["t"] < 20:
                    jouer_anim_troupe(state, at)
                    continue
            if state.get("dressage"):
                vu = dict(state["dressage"])
                clear()
                sys.stdout.write(render_dressage(state, False))
                sys.stdout.write(f"{DIM} " + t("app.dressage.pied") + f"{RESET}\n")
                sys.stdout.flush()
            else:
                if fini is None:
                    fini = time.time()
                    clear()
                    b = state.get("bubble")
                    print("\n  " + (b[0] if b else t("app.dressage.fini")))
                    ind = (vu or {}).get("ind")
                    if ind:
                        pris = next((c for c in state.get("captures", []) if c.get("id") == ind.get("id")), None)
                        bete = pris or dict(ind, espece=vu["espece"], shiny=vu.get("shiny"))
                        r = equipe.animation(bete, "victoire" if pris else "ko")
                        if r:
                            equipe.derouler(r[0], r[1], 2)
                if time.time() - fini > 6:
                    return
            time.sleep(0.7)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")


def anim_troupe(state, at):
    """(images, ips) de l'animation d'une bestiole de la troupe demandée par le combat, ou None."""
    ind = next((c for c in state.get("captures", []) if c.get("id") == at.get("id")), None)
    try:
        return equipe.animation(ind, at["nom"]) if ind else None
    except Exception:
        return None


def jouer_anim_troupe(state, at):
    """Dans la fenêtre du face-à-face : l'animation (ko : puis elle s'endort pour se reposer)."""
    r = anim_troupe(state, at)
    if not r:
        return
    ind = next((c for c in state.get("captures", []) if c.get("id") == at.get("id")), {})
    clear()
    b = core.bulle_courante(state)
    titre = f"\n  {BOLD}{b[0] if b else ind.get('espece', '')}{RESET}\n"
    equipe.derouler(r[0], r[1], 1 if at["nom"] == "attaque" else 2, titre)
    if at["nom"] == "ko":
        r = anim_troupe(state, dict(at, nom="dort"))
        if r:
            clear()
            equipe.derouler(r[0], r[1], 1, titre)


def render_dressage(state, interactif, anim=None):
    """Pendant un dressage : le face-à-face seulement (plus la bulle et les deux dernières lignes du journal).
    anim : les lignes d'une image d'animation (combat) à montrer au-dessus."""
    lines = (["", *("  " + l for l in anim), ""] if anim else []) + dressage.lignes_ecran(state)
    b = core.bulle_courante(state)
    if b:
        lines += ["", f"  {BOLD}» {raccourcir(' '.join(b[0].split()), 90)}{RESET}"]
    lines.append(title_line(t("app.journal")))
    lines += [" " + l for l in state["log"][-2:]]
    if interactif:
        lines.append(f"{fg(244)} " + t("app.dressage.touches") + RESET)
    return "\n".join(lines) + "\n"


# ================================================================ étape de jeu (partagée par tous les modes)

def _sans_planter(state, fn, *a, **k):
    """Un module du tour de jeu qui bute sur le système (droits retirés, disque plein, lien refusé) : la créature
    l'explique, et les autres modules continuent (jamais de trace Python à l'écran)."""
    try:
        return fn(*a, **k)
    except OSError as e:
        msg = sur.message_os(e)
        if msg not in state.get("_dit_os", []):
            state.setdefault("_dit_os", []).append(msg)
            core.say(state, msg, 16)
        return None


def boucle_jeu(state, lines, spontane=True, rythme=1.5, defis=True, cwd=None):
    core.tick(state)
    for k, line in enumerate(lines):
        core.feed(state, line, core.statut_de(lines, k))   # une commande ratée ne donne pas de points (G-34)
    if state.get("_restaure"):                # save.json était abîmé : on a repris une copie de secours
        r = state.pop("_restaure")
        core.say(state, t("core.sur.restaure", copie=r.get("de", "?"), casse=r.get("casse", "?")), 20)
    if core.TERRAIN.is_symlink():             # la zone d'aventure est un lien : rien n'y est construit
        sur.ALERTES.append(str(core.TERRAIN))
    _ok = lambda fn, *a, **k: _sans_planter(state, fn, *a, **k)
    r = _ok(intro.tick, state, lines)         # l'œuf : sa liste, ses fêlures, l'éclosion
    lines = lines if r is None else r
    _ok(exemples.tick, state, lines)          # mkdir tout seul… : une bulle avec la commande à taper
    _ok(terrain.tick, state, lines)           # terrain effacé : le reconstruire, reprendre la leçon
    _ok(histoire.tick, state, lines, cwd)     # la Maison endormie : visites, chapitres, quêtes
    _ok(dressage.tick, state, lines)
    _ok(equipe.tick, state, lines)
    if intro.ouvert(state, "combats"):        # les monstres arrivent avec leur présentation (intro.json)
        _ok(explo.tick, state, spontane, proba=rythme / 480, jeu=sum(1 for l in lines if not core.est_colle(l)),
            lignes=lines)
    _ok(core.defi_tick, state, lines, spontaneous=spontane and defis, proba=rythme / 300)
    _ok(envies.tick, state, lines)            # les 6 envies : usure, plaisirs, poussière, rappel espacé
    _ok(entrainement.tick, state, lines)      # salle d'entraînement : l'exercice en cours est-il réussi ?
    _ok(guide.tick, state, lines)             # le guide : talents, fatigue, envie de sortir, régions gardées
    core.idle_talk(state, proba=min(1.0, 0.08 * rythme / 1.5))
    _ok(intro.verifier, state)                # les fonctions qui s'ouvrent maintenant (présentées une par une)
    sur.alertes(state)                        # un lien symbolique a été refusé : la créature dit lequel
    state.pop("_dit_os", None)


def probleme_sauvegarde():
    """La sauvegarde ne peut pas être lue : le message à montrer (droits retirés, fichier abîmé), sinon None."""
    try:
        e = core.etat_sauvegarde()
    except OSError:
        e = "inaccessible"
    d = sur.relatif(core.SAVE_DIR)
    if e == "inaccessible":
        return t("core.sur.inaccessible", chemin=d, cmd=f"chmod -R u+rwX {d}")
    if e == "abimee":
        return t("core.sur.abimee", chemin=d + "/save.json")
    return None


def etape(spontane=True, rythme=1.5, defis=True, avant_save=None, extra=None, cwd=None, statut=None):
    """Charge, fait vivre la créature, sauvegarde, puis envoie les notifications.
    cwd : le dossier courant du terminal (donné par l'invite du shell), pour la carte de la maison.
    statut : le code de sortie de la dernière commande ($?, donné par l'invite) : une étape n'est validée que si la
    commande a marché (verif.py).
    Ne plante jamais sur une erreur du système : une sauvegarde illisible lève core.Probleme (message gentil),
    une sauvegarde impossible (disque plein, droits) est dite par la créature, et la partie continue en mémoire."""
    with core.verrou():
        try:
            state = core.load()
        except OSError as e:
            raise core.Probleme(probleme_sauvegarde() or sur.message_os(e))
        if state is None:
            msg = probleme_sauvegarde()
            if msg:
                raise core.Probleme(msg)
            return None
        core.migrate(state)
        try:
            lines = core.read_new_lines(state) + list(extra or [])
        except OSError:
            lines = list(extra or [])
        avant = state["total"]
        core.DERNIER.update(ligne=lines[-1] if lines and statut is not None else None, statut=statut)
        boucle_jeu(state, lines, spontane, rythme, defis, cwd)
        state["_vient_de_manger"] = state["total"] > avant
        if avant_save:
            avant_save(state)
        a_envoyer, state["notifs"] = state["notifs"], []
        try:
            core.save(state)
        except OSError as e:
            msg = t("core.sur.pas_sauve", raison=sur.message_os(e))
            core.say(state, msg, 20)
            state["_pas_sauve"] = msg
    try:
        if intro.ouvert(state, "extras"):          # les notifications arrivent avec leur présentation (intro.json)
            notif.envoyer(state, a_envoyer)
            notif.permanente(state)
    except Exception:
        pass
    if SYNC_AUTO:
        try:
            recense.synchroniser_en_fond()
        except Exception:
            pass
    return state


# ================================================================ menus

def menu_recherche(state, clav):
    historique = []
    while True:
        clear()
        print(f" {fg(213)}── 🔎 " + t("app.recherche.titre", nom=state["name"]) + f" ──{RESET}")
        print(f" {DIM}" + t("app.recherche.aide1"))
        print(" " + t("app.recherche.aide2") + f"{RESET}\n")
        for l in historique:
            print(l)
        q = clav.demander(f" {BOLD}> {RESET}").strip()
        if not q:
            return
        res = registre.chercher(q)
        core.modifier(lambda s: registre.memoriser(s, res))
        historique = [f" {DIM}" + t("app.recherche.demande", q=q) + RESET, ""] + registre.afficher(res, state["name"])
        if res:
            historique.append(f" {DIM}" + t("app.recherche.tape1"))
            historique.append(" " + t("app.recherche.tape2") + RESET)
        historique.append(f" {DIM}" + t("app.recherche.retour") + f"{RESET}\n")


def menu_arbre(state, clav):
    """Les ailes de la maison : choisir celle qu'on réveille (l'ordre est libre après le chapitre 2)."""
    msg = ""
    while True:
        st = core.load() or state
        core.migrate(st)
        clear()
        for l in histoire.lignes_ailes(st):
            print(l)
        print(" " + t("app.arbre.competences", liste=", ".join(core.nom_skill(x) for x in st["skills"])
                      or t("app.arbre.aucune")) + "\n")
        if msg:
            print(f" {msg}\n")
        r = clav.demander(" " + t("hist.menu.numero") + " ").strip()
        if not r:
            return
        cid = histoire.chercher_chapitre(r)
        if not cid:
            msg = t("hist.aile.inconnue", nom=r)
            continue
        res = []
        core.modifier(lambda s: res.append(histoire.choisir(s, cid)))
        msg = res[0] if res else ""


def menu_carte(state, clav):
    clear()
    res = []
    core.modifier(lambda s: res.append(maison.carte(s)))
    for l in res[0] if res else maison.carte(state):
        print(l)
    clav.demander(f"\n {DIM}" + t("app.entree_retour") + RESET)


def menu_quetes(state, clav):
    msg = ""
    while True:
        clear()
        for l in quetes.journal(core.load() or state):
            print(l)
        if msg:
            print(f"\n {msg}")
        r = clav.demander("\n " + t("qu.journal.numero") + " ").strip()
        if not r:
            return
        res = []
        core.modifier(lambda s: res.append(quetes.suivre(s, r)))
        msg = res[0] if res else ""


def menu_collection(state, clav):
    clear()
    for l in explo.ecran_collection(state):
        print(l)
    clav.demander(f"\n {DIM}" + t("app.entree_retour") + RESET)


def menu_lexique(state, clav):
    clear()
    st = core.load() or state
    for l in lexique.lignes(st):
        print(l)
    clav.demander(f"\n {DIM}" + t("app.entree_retour") + RESET)


def lancer_detache(mode):
    exe, app = compagnon.commande()
    kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if IS_WIN:
        kw["creationflags"] = 0x00000008 | 0x08000000      # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen([exe, app, mode], **kw)
        return True
    except OSError:
        return False


def menu_options(state, clav):
    """Les options, rangées en sections : Apparence (thème, disposition, langue), Ma créature partout,
    Notifications, Compte, Pour les grands (« Tout afficher », protégé par une petite question)."""
    from . import apparence
    msg = ""
    while True:
        st = core.load() or state
        core.migrate(st)
        cfg = st["config"]
        moteur = notif.systeme()
        installe = compagnon.est_installe()
        onoff = lambda b: f"{fg(78)}{t('app.on')}{RESET}" if b else f"{fg(203)}{t('app.off')}{RESET}"
        sec = lambda cle: print(f"\n {fg(221)}{BOLD}{t(cle).upper()}{RESET}")
        th = apparence.theme(st)
        _rects, dispo = apparence.disposition(st)
        clear()
        print(f" {fg(213)}── ⚙ " + t("app.options.titre") + f" ──{RESET}")
        sec("app.opt.apparence")
        print("  1. " + t("app.options.theme", nom=f"{BOLD}{t('app.theme.' + th.cle)}{RESET}") + "  " + apercu_theme(th))
        print(f"     {DIM}" + t("app.options.theme.terminal") + RESET)
        print("  2. " + t("app.options.dispo", nom=f"{BOLD}{t('app.dispo.' + dispo)}{RESET}"))
        print("  3. " + t("app.options.langue", langue=f"{BOLD}{langue.LANGUES[langue.courante()]}{RESET}")
              + f" {DIM}(tg langue xx){RESET}")
        print(f"     {DIM}" + t("app.options.ranger") + RESET)
        sec("app.opt.creature")
        print("  4. " + t("app.options.compagnon", etat=onoff(installe)))
        print("  5. " + t("app.options.style", style=f"{BOLD}{t('app.style.' + cfg['compagnon'])}{RESET}")
              + f" {DIM}({t('app.style.ligne')} / {t('app.style.coin')}){RESET}")
        print("  6. " + t("app.options.bureau") + f" {DIM}(PC){RESET}")
        sec("app.opt.notifications")
        print("  7. " + t("app.options.notifs", etat=onoff(cfg["notifs"]))
              + f"  {DIM}({moteur or t('app.options.aucun_systeme')}){RESET}")
        if moteur == "android":
            print("  8. " + t("app.options.permanente", etat=onoff(cfg["permanente"])))
        else:
            print("  8. " + t("app.options.permanente", etat=f"{DIM}{t('app.options.permanente.pc')}{RESET}"))
        print("  9. " + t("app.options.test"))
        sec("app.opt.compte")
        c = st.get("compte", {})
        print(" 10. " + t("app.options.recensement", pseudo=f"{BOLD}{c.get('pseudo') or t('app.options.pas_de_compte')}{RESET}")
              + f" {DIM}" + t("app.options.recensement.meme") + RESET)
        sec("app.opt.grands")
        print(" 11. " + t("app.options.tout", etat=onoff(apparence.a_(st).get("tout"))))
        print(f"     {DIM}" + t("app.opt.tout.aide") + RESET)
        print(f"     {DIM}" + t("app.options.debloquer") + RESET)
        print(f"\n {DIM}" + t("app.options.mini1"))
        print(" " + t("app.options.mini2") + RESET)
        if msg:
            print(f"\n {msg}")
        r = clav.demander("\n " + t("app.choix") + " ").strip()
        msg = ""
        if not r:
            return
        if r == "1":
            msg = menu_theme(clav)
        elif r == "2":
            ordre = apparence.donnees()["ordre_dispositions"]
            mienne = apparence.a_(st).get("mienne")
            ordre = [o for o in ordre if o != "mienne" or mienne]
            suivant = ordre[(ordre.index(dispo) + 1) % len(ordre)] if dispo in ordre else ordre[0]
            core.modifier(lambda s: apparence.choisir_disposition(s, suivant))
        elif r == "3":
            msg = menu_langue(clav)
        elif r == "4":
            faits = compagnon.desinstaller() if installe else compagnon.installer()
            msg = (t("app.retire" if installe else "app.installe", liste=", ".join(faits))
                   + ("" if installe else "\n " + t("app.options.nouveau_terminal"))) if faits \
                else t("app.options.aucun_shell")
        elif r == "5":
            core.modifier(lambda s: s["config"].update(compagnon="coin" if s["config"]["compagnon"] == "ligne" else "ligne"))
        elif r == "6":
            msg = t("app.options.bureau.ok") if lancer_detache("bureau") else t("app.options.bureau.echec")
        elif r == "7":
            core.modifier(lambda s: s["config"].update(notifs=not s["config"]["notifs"]))
        elif r == "8" and moteur == "android":
            core.modifier(lambda s: s["config"].update(permanente=not s["config"]["permanente"]))
            notif.permanente(core.load())
        elif r == "9":
            ok = notif.envoyer(st, [t("app.options.test.texte", nom=st["name"])], forcer=True)
            msg = t("app.options.test.ok") if ok else t("app.options.test.echec")
            if moteur == "android":
                notif.permanente(st)
        elif r == "10":
            menu_recensement(clav)
        elif r == "11":
            msg = basculer_tout_afficher(clav)


def apercu_theme(th):
    """Un aperçu d'une ligne : la vue déployée de « cat lianes.txt | grep gland » dans les couleurs du thème."""
    from . import apparence
    out = ""
    for mot, g in (("cat", "vert"), ("lianes.txt", "cyan"), ("|", "violet"), ("grep", "vert"), ("gland", "bleu")):
        c = (th if not th.clair else apparence.Theme("sombre")).acc[g]
        out += f"\033[38;2;{c[0]};{c[1]};{c[2]}m{BOLD}{mot}{RESET} "
    return out


def menu_theme(clav):
    from . import apparence
    clear()
    print(f" {fg(213)}── 🎨 " + t("app.opt.theme") + f" ──{RESET}\n")
    print(f" {DIM}" + t("app.opt.theme.aide") + RESET + "\n")
    st = core.load() or {}
    actuel = apparence.cle_theme(st)
    cles = apparence.ordre()
    for i, cle in enumerate(cles, 1):
        marque = f"{fg(78)}●{RESET}" if cle == actuel else " "
        nom = t("app.theme." + cle)
        print(f" {marque} {i}. {nom}{' ' * max(1, 26 - len(nom))}{apercu_theme(apparence.Theme(cle))}")
    r = clav.demander("\n " + t("app.choix") + " ").strip().lower()
    if not r:
        return ""
    if r.isdigit() and 1 <= int(r) <= len(cles):
        r = cles[int(r) - 1]
    if r not in cles:
        return t("app.theme.liste", liste=" ".join(cles))
    core.modifier(lambda s: apparence.choisir_theme(s, r))
    apparence.activer(core.load())
    return t("app.theme.ok", nom=t("app.theme." + r))


def basculer_tout_afficher(clav, question=None):
    """« Tout afficher » : l'éteindre tout de suite ; l'allumer après une petite question pour les grands."""
    from . import apparence
    st = core.load() or {}
    if apparence.a_(st).get("tout"):
        core.modifier(lambda s: apparence.tout_afficher(s, False))
        return t("app.options.tout", etat=t("app.off"))
    q, rep = question or apparence.question_adulte()
    r = clav.demander(" 🔒 " + t("app.tout.question", q=q) + " ").strip()
    if r != rep:
        return t("app.tout.non")
    core.modifier(lambda s: apparence.tout_afficher(s, True))
    return "🔓 " + t("app.tout.ok")


def commande_theme(args):
    """tg theme [nom] : choisir le thème (sans nom : la liste)."""
    from . import apparence
    cles = apparence.ordre()
    if args and args[0] in cles:
        core.modifier(lambda s: apparence.choisir_theme(s, args[0]))
        return t("app.theme.ok", nom=t("app.theme." + args[0]))
    return t("app.theme.liste", liste=" ".join(cles))


def changer_langue(code):
    """tg langue xx : enregistre la langue dans la sauvegarde. Renvoie le message à afficher."""
    c = langue.code_valide(code)
    if not c:
        return t("app.langue.inconnue", code=code) + "\n" + liste_langues()
    core.modifier(lambda s: s.__setitem__("langue", c))
    langue.definir(c)
    return t("app.langue.ok", langue=langue.LANGUES[c])


def liste_langues():
    return "\n".join(f"  {code}  {nom}" for code, nom in langue.LANGUES.items())


def menu_langue(clav):
    clear()
    print(f" {fg(213)}── 🌐 " + t("app.langue.titre") + f" ──{RESET}\n")
    codes = list(langue.LANGUES)
    for i, code in enumerate(codes, 1):
        marque = f"{fg(78)}●{RESET}" if code == langue.courante() else " "
        print(f" {marque} {i:>2}. {code}  {langue.LANGUES[code]}")
    print(f"\n {DIM}" + t("app.langue.rtl") + RESET)
    r = clav.demander("\n " + t("app.choix") + " ").strip().lower()
    if not r:
        return ""
    if r.isdigit() and 1 <= int(r) <= len(codes):
        r = codes[int(r) - 1]
    return changer_langue(r)


def menu_recensement(clav):
    msg = recense.commande([])
    while True:
        clear()
        print(f" {fg(213)}── 🌍 " + t("app.rec.titre") + f" ──{RESET}\n")
        print(" " + msg.replace("\n", "\n ") + "\n")
        st = core.load()
        a_compte = bool(st and st.get("compte", {}).get("cle"))
        if a_compte:
            print(" 1. " + t("app.rec.code") + "\n 2. " + t("app.rec.sync") + "\n 3. "
                  + t("app.rec.drapeau", ctf=terme("ctf", palier(st))))
        else:
            print(" 1. " + t("app.rec.creer") + "\n 2. " + t("app.rec.lier"))
        r = clav.demander("\n " + t("app.choix") + " ").strip()
        if not r:
            return
        if a_compte:
            if r == "1":
                msg = recense.commande(["code"])
            elif r == "2":
                msg = recense.synchroniser(forcer=True) or t("app.rien_a_synchroniser")
            elif r == "3":
                msg = recense.drapeau(clav.demander(" " + t("app.rec.drapeau.invite") + " "))
        elif r == "1":
            msg = recense.commande(["creer", clav.demander(" " + t("app.rec.pseudo.invite") + " ").strip()])
        elif r == "2":
            msg = recense.commande(["lier", clav.demander(" " + t("app.rec.code.invite") + " ").strip()])


# ================================================================ modes

def _dire_une_fois(msg, delai=3600):
    """Le crochet d'invite ne doit jamais gêner : un souci est dit une fois par heure au plus (sur stderr)."""
    import tempfile
    marque = os.path.join(tempfile.gettempdir(), f"tg_prompt_{os.getuid() if hasattr(os, 'getuid') else 0}")
    try:
        if time.time() - os.path.getmtime(marque) < delai:
            return
    except OSError:
        pass
    try:                                       # jamais à travers un lien (/tmp est partagé) : O_NOFOLLOW, sans vider
        fd = os.open(marque, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.utime(fd) if os.utime in os.supports_fd else None
        finally:
            os.close(fd)
    except OSError:
        pass
    print(msg, file=sys.stderr)


def creer_si_besoin(avec_intro=None):
    """Premier lancement : la créature est créée. avec_intro (par défaut : une vraie personne au clavier) :
    les écrans de l'intro, puis l'œuf et sa liste de commandes, et le jeu qui s'ouvre petit à petit (intro.py).
    Sans personne au clavier (scripts, tests), tout est ouvert tout de suite.
    Une sauvegarde qui existe mais ne se lit pas n'est JAMAIS remplacée en silence : droits retirés → on explique et
    on s'arrête ; fichier abîmé sans copie de secours → on le range à côté (save.json.casse-…), on le dit, puis
    seulement on fait éclore un nouvel œuf."""
    try:
        if core.load() is not None:
            return
    except OSError:
        pass
    etat = core.etat_sauvegarde()
    if etat == "inaccessible":
        raise core.Probleme(probleme_sauvegarde())
    if etat == "abimee":
        casse = core.SAVE_DIR / ("save.json.casse-" + time.strftime("%Y%m%d-%H%M%S"))
        try:
            os.replace(core.SAVE_FILE, casse)
        except OSError:
            raise core.Probleme(probleme_sauvegarde())
        print(t("core.sur.abimee.nouvelle", casse=sur.relatif(casse)))
    if avec_intro is None:
        avec_intro = sys.stdin.isatty() and sys.stdout.isatty()
    try:
        code = langue.detecter()                  # premier lancement : la langue du système
        langue.definir(code)
        name = intro.jouer_ecrans(input, clear) if avec_intro else None
        if not name:
            name = input(t("app.nom_creature") + " ")
        name = name.strip()[:16] or "Pixel"
    except (KeyboardInterrupt, EOFError):
        print("\n" + t("app.a_bientot"))
        raise SystemExit(0)
    with core.verrou():
        state = core.load()
        if state is None:
            state = core.migrate(core.new_state(name, code))
            if avec_intro:
                intro.nouvelle_partie(state)
            core.read_new_lines(state)   # mémorise où on en est, sans manger l'ancien historique
            core.log(state, t("app.oeuf_apparu", trait=core.nom_trait(state["trait"])))
            core.animer(state, "salut")
            state["notifs"] = []
            core.save(state)
    if avec_intro and sys.stdin.isatty() and "--une-fois" not in sys.argv:
        compagnon.proposer()                  # G-03 : une seule fenêtre, le vrai terminal avec la créature dedans


RYTHME = 1.5          # secondes entre deux étapes de jeu
AMBIANCE = 25         # secondes entre deux petites animations d'ambiance (sommeil la nuit, faim)


def _nuit():
    h = time.localtime().tm_hour
    return h >= 21 or h < 7


def aura_ecran(state):
    """Le palier d'aura de la créature de l'écran principal, ou None si le réglage est coupé (tg aura off)."""
    from . import aura
    return aura.palier_compagnon(state) if aura.active(state) else None


def commande_aura(args):
    """tg aura [on|off] : l'aura de rareté autour de la créature de l'écran principal (réglage de la partie)."""
    from . import aura
    choix = args[0].lower() if args else ""
    if choix in ("on", "off"):
        core.modifier(lambda s: s["config"].update(aura=choix == "on"))
    etat = f"{fg(78)}{t('app.on')}{RESET}" if aura.active(core.load()) else f"{fg(203)}{t('app.off')}{RESET}"
    return " " + t("aura.etat", etat=etat) + f"\n {DIM}" + t("aura.legende") + "\n " + t("aura.soin") + RESET


def _preparer_anim(state, nom):
    """[images, ips, image courante, nombre d'images à jouer] : court (≈ 3 s), jamais bloquant."""
    try:
        frames, ips = sprites.animation(state, nom, aura_ecran(state))
    except Exception:
        return None
    n = len(frames) if nom == "evolution" else min(2 * len(frames), max(len(frames), int(3 * ips)))
    return [frames, ips, 0, n]


def _ecran(texte):
    """Redessine sans tout effacer d'abord (pas de clignotement pendant les animations)."""
    sys.stdout.write("\033[H" + texte.replace("\n", "\033[K\n") + "\033[J")
    sys.stdout.flush()


def _terminal_possible():
    """Entrée peut ramener l'enfant dans son terminal (le compagnon y est installé, hors Windows)."""
    try:
        return not IS_WIN and sys.stdin.isatty() and compagnon.est_installe()
    except Exception:                                # noqa: BLE001
        return False


def _retour_terminal(clav):
    """I5 : après `exit`, la fenêtre du jeu n'écoute que ses touches ; Entrée rouvre le terminal (ou, si la fenêtre a
    été ouverte depuis le terminal du jeu, la ferme pour y revenir). Renvoie True, « sortir » ou False."""
    if not _terminal_possible():
        return False
    if os.environ.get("TG_DANS_LE_JEU"):
        return "sortir"
    import shutil
    import subprocess
    clav.normal()
    try:
        clear()
        print(f"\n   {fg(78)}" + t("intro.pc.lance") + RESET + "\n")
        shell = os.environ.get("SHELL") or shutil.which("bash") or "sh"
        subprocess.call([shell, "-i"], env=dict(os.environ, TG_DANS_LE_JEU="1"))
    except OSError:
        return False
    finally:
        clav.brut()
    return True


def fenetre(once):
    if "--defi" in sys.argv:
        core.modifier(core.defi_start)
    frame = 0
    clav = Clavier()
    interactif = clav.ok and not once
    anim = None
    vu_anim = time.time()                 # on ne rejoue pas les événements d'avant l'ouverture
    vu_troupe = vu_anim
    ambiance = time.time() + AMBIANCE
    dernier = 0
    state = None
    try:
        with clav:
            clear()
            while True:
                now = time.time()
                if state is None or now - dernier >= RYTHME:
                    try:
                        nouveau = etape(spontane=not once)
                    except (core.Probleme, OSError) as e:
                        # sauvegarde inaccessible (chmod 000…) : la fenêtre reste ouverte, explique et réessaie
                        _ecran(str(e) if isinstance(e, core.Probleme) else sur.message_os(e))
                        if once:
                            break
                        k = clav.touche(RYTHME * 2)
                        if k and k.lower() == "q":
                            break
                        dernier = time.time()
                        continue
                    if nouveau is None:
                        _ecran(t("core.sur.plus_de_sauvegarde"))
                        if once or (clav.touche(RYTHME * 2) or "").lower() == "q":
                            break
                        continue
                    state = nouveau
                    dernier = now
                    frame += 1
                    evt = state.get("anim")
                    at = state.get("anim_troupe")
                    d_ici = state.get("dressage") and not state["dressage"].get("fenetre")
                    if not once and d_ici and at and at.get("t", 0) > vu_troupe:
                        vu_troupe = at["t"]                    # combat affiché ici (pas de fenêtre à part)
                        r = anim_troupe(state, at)
                        if r and now - at["t"] < 15:
                            anim = [r[0], r[1], 0, min(2 * len(r[0]), max(len(r[0]), int(3 * r[1])))]
                    elif not once and evt and evt[1] > vu_anim:
                        vu_anim = evt[1]
                        if now - evt[1] < 15 and evt[0].startswith(("oeuf_", "eclosion")):
                            try:                       # l'œuf remue, brille, se fêle, éclot (intro.py)
                                f, ips = intro.animation(evt[0], state)
                                anim = [f, ips, 0, len(f)]
                            except Exception:
                                pass
                        elif now - evt[1] < 15:
                            anim = _preparer_anim(state, evt[0]) or anim
                    elif not once and anim is None and now >= ambiance and not intro.en_cours(state):
                        ambiance = now + AMBIANCE
                        if _nuit() or satiete.etat(state) == "veille":      # la nuit, ou en veille : elle dort
                            anim = _preparer_anim(state, "dort")
                        elif satiete.affamee(state):
                            anim = _preparer_anim(state, "affame")
                        elif random.random() < 0.3:
                            anim = _preparer_anim(state, random.choice(["statique", "salut", "content"]))
                image = anim[0][anim[2] % len(anim[0])] if anim else None
                _ecran(render(state, frame, interactif, image, int(time.time() * VIE_IPS)))
                if once:
                    break
                if anim:
                    k = clav.touche(1 / anim[1])
                    anim[2] += 1
                    if anim[2] >= anim[3]:
                        anim = None
                else:                                  # au repos : la créature vit (8 images/s, sautées si lent)
                    k = clav.touche(max(0.05, min(1 / VIE_IPS, RYTHME - (time.time() - dernier))))
                if not k:
                    continue
                anim = None
                rendu_fin.effacer()
                clear()
                if intro.a_montrer(state) and not intro.en_cours(state) and k.lower() != "q":
                    if k in ("\r", "\n", " "):          # Entrée : l'écran de présentation est lu
                        state = core.modifier(intro.lu) or state
                    continue
                if k in ("\r", "\n"):                    # I5 : Entrée = retourner dans le terminal (après `exit`)
                    r = _retour_terminal(clav)
                    if r == "sortir":
                        break
                    if r:
                        clear()
                        continue
                k = k.lower()
                fid = TOUCHES.get(k)
                if fid and not intro.ouvert(state, fid):
                    state = core.modifier(lambda s: core.say(s, t("deb.pas_encore", cmd=k), 6)) or state
                    continue
                if k in ("/", "r", "?"):
                    menu_recherche(state, clav)
                elif k == "a":
                    menu_arbre(state, clav)
                elif k == "c":
                    menu_collection(state, clav)
                elif k == "o":
                    menu_options(state, clav)
                elif k == "l":
                    menu_lexique(state, clav)
                elif k == "m":
                    menu_carte(state, clav)
                elif k == "j":
                    menu_quetes(state, clav)
                elif k == "u":                    # l'aura de rareté autour de la créature
                    state = core.modifier(lambda s: s["config"].update(aura=not s["config"].get("aura", True)))
                elif k == "q":
                    break
                elif k and len(k) == 1 and k.isalnum():   # P1-5 : des lettres tapées ici ne sont pas des commandes
                    msg = t("app.pas_ici.entree") if _terminal_possible() else t("app.pas_ici")
                    state = core.modifier(lambda s: core.say(s, msg, 10)) or state
    except KeyboardInterrupt:
        pass
    rendu_fin.effacer()
    print(RESET + "\n" + t("app.a_plus_tard"))


def veille():
    """Fait vivre la créature en arrière-plan : faim, bestioles, notifications."""
    print(t("app.veille"))
    try:
        while True:
            try:
                st = etape(spontane=True, rythme=30, defis=False)
            except (core.Probleme, OSError) as e:          # la veille ne meurt jamais : elle explique et attend
                st = None
                print("\r" + time.strftime("%H:%M ") + (str(e) if isinstance(e, core.Probleme) else sur.message_os(e)),
                      flush=True)
            except Exception:
                st = None
                sur.noter_trace()
            if st and st.get("_pas_sauve"):
                print("\r" + time.strftime("%H:%M ") + st["_pas_sauve"], flush=True)
            if st:
                print(f"\r{time.strftime('%H:%M')} " + t("app.veille.ligne", nom=st["name"], n=core.level(st["xp"]),
                                                         faim=int(st["hunger"])) + "   ", end="", flush=True)
            time.sleep(30)
    except KeyboardInterrupt:
        print()


def aide():
    return "\n".join(langue.remplir(l, {}) for l in langue.liste("app.aide") + langue.liste("app.aide.histoire")
                     + [t("env.aide"), t("sat.aide"), t("aura.aide"), t("ent.aide"), t("esp.aide")])


def commande_histoire(mode, args):
    """tg carte · tg quetes [suivre N] · tg aile [nom] : sans ouvrir la fenêtre."""
    if mode == "carte":                        # la carte qui pousse : ce qui est montré n'est plus « nouveau » ensuite
        res = []
        core.modifier(lambda s: (histoire.h_(s), res.append(maison.carte(s))))
        return "\n".join(res[0]) if res else ""
    if mode in ("quetes", "quete", "journal"):
        if len(args) >= 2 and args[0].lower() in ("suivre", "follow", "s"):
            res = []
            core.modifier(lambda s: res.append(quetes.suivre(s, args[1])))
            return res[0] if res else ""
        st = core.modifier(lambda s: histoire.h_(s))
        return "\n".join(quetes.journal(st))
    if args:
        cid = histoire.chercher_chapitre(" ".join(args))
        if not cid:
            return t("hist.aile.inconnue", nom=" ".join(args)) + "\n" + "\n".join(histoire.lignes_ailes(core.load()))
        res = []
        core.modifier(lambda s: res.append(histoire.choisir(s, cid, dit=False)))
        return res[0] if res else ""
    return "\n".join(histoire.lignes_ailes(core.modifier(lambda s: histoire.h_(s))))


def commande_debloquer(args, demander=None):
    """tg debloquer tout [--oui] : ouvre tout le jeu d'un coup (après confirmation)."""
    from . import accueil
    if not args or args[0].lower() not in ("tout", "all"):
        return t("deb.tout.non")
    if "--oui" not in sys.argv:
        try:
            if not accueil.oui((demander or input)(t("deb.tout.question") + " ")):
                return t("deb.tout.non")
        except (KeyboardInterrupt, EOFError):
            return t("deb.tout.non")
    core.modifier(intro.tout_debloquer)
    return t("deb.tout.ok")


def commande_guide(mode, args):
    """tg guide : le guide ; tg guide <nom> ou tg equipe guide <nom> : changer de guide ; tg types : la table des types."""
    if mode == "types":
        return "\n".join(guide.ecran_types(core.load()))
    if mode == "equipe":
        args = args[1:]
    if not args:
        return "\n".join(guide.ecran(core.modifier(lambda s: guide.tick(s, []))))
    res = []
    core.modifier(lambda s: res.append(guide.choisir(s, " ".join(args))))
    texte, ind = res[0] if res else ("", None)
    if ind is not None or texte.startswith("🔄"):
        guide.animation_changement(ind, core.load())
    return texte


def main():
    """Le point d'entrée : jamais de trace Python à l'enfant. Une erreur du système (droits, disque plein) est
    expliquée ; une erreur imprévue est rangée dans ~/.terminagotchi/erreurs.log pour un adulte."""
    try:
        _main()
    except KeyboardInterrupt:
        print(RESET)
    except core.Probleme as e:
        print(RESET + str(e))
        raise SystemExit(1)
    except OSError as e:
        print(RESET + sur.message_os(e))
        raise SystemExit(1)
    except Exception:
        f = sur.noter_trace()
        print(RESET + t("core.sur.bug", fichier=sur.relatif(f) if f else "?"))
        raise SystemExit(1)


def _main():
    langue.installer_rendu()                   # les commandes à taper en vert (`…` dans les textes)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0].lower() if args else ""
    try:
        rien = core.load() is None
    except OSError:
        rien = False
    if rien:                                   # pas encore de sauvegarde : la langue du système
        langue.definir(langue.detecter())
    if mode == "prompt":                       # appelé par le shell : ne doit jamais gêner
        try:
            compagnon.prompt(etape)
        except core.Probleme as e:             # la créature ne se tait pas sans dire pourquoi (une fois par heure)
            _dire_une_fois(str(e))
        except OSError as e:
            _dire_une_fois(sur.message_os(e))
        except Exception:
            sur.noter_trace()
        return
    if mode in ("aide", "help", "-h"):
        st = core.load()
        if st is not None and not (len(args) > 1 and args[1].lower() in ("tout", "all")):
            core.migrate(st)                   # P2-7 : coincé ? d'abord la leçon en cours, où la taper, et pourquoi
            try:
                ici = os.getcwd()
            except OSError:
                ici = None
            with core.verrou():
                st = core.load() or st
                core.migrate(st)
                texte = histoire.aide_lecon(st, ici)
                core.save(st)
            print("\n".join(texte) + "\n")    # I1 : seulement la leçon en cours (la liste du jeu : tg aide tout)
            return
        print(aide())
        return
    if mode in ("placement", "sansaide"):      # G-13 : le test « je connais déjà », le mode défi sans aide
        creer_si_besoin()
        from . import placement
        sortie = []
        core.modifier(lambda s: sortie.append(placement.commande(s, args[1:] if mode == "sansaide" else [])))
        print(sortie[0] if sortie else "")
        return
    if mode == "debloquer":                    # tg debloquer tout : pour les parents et les tests (confirmation)
        creer_si_besoin()
        print(commande_debloquer(args[1:]))
        return
    st = core.load()
    if st is not None and mode:                # une fonction pas encore ouverte : « pas encore » (intro.json)
        core.migrate(st)
        nom = "guide" if mode == "equipe" and len(args) > 1 and args[1].lower() == "guide" else mode
        msg = intro.bloque(st, nom)
        if msg:
            print(msg)
            return
    if mode == "notifs":                       # tg notifs on|off : les notifications de la créature
        creer_si_besoin()
        choix = args[1].lower() if len(args) > 1 else ""
        if choix in ("on", "off"):
            core.modifier(lambda s: s["config"].update(notifs=choix == "on"))
        on = core.load()["config"].get("notifs", True)
        print(t("app.options.notifs", etat=f"{fg(78)}{t('app.on')}{RESET}" if on else f"{fg(203)}{t('app.off')}{RESET}"))
        return
    if mode == "port":                         # tg port … : le réseau simulé du Terminaworld (le monde du Port)
        from . import port
        port.commande(args[1:])
        return
    if mode == "citadelle":                    # tg citadelle … : la Citadelle (cadenas, boîtes, inspecteur, vague)
        from . import citadelle
        citadelle.commande(args[1:])
        return
    if mode in ("deploie", "déploie"):         # tg deploie <commande> : la vue déployée (sans la lancer)
        from . import deploie
        brut_args = [a for a in sys.argv[2:]]      # garder --pas et --historique (args a retiré les « -- »)
        deploie.commande(brut_args)
        return
    if mode == "maths" or (mode == "je" and maths.mots_reponse(" ".join(args)) == "non"):
        creer_si_besoin()                      # tg maths … : les Ponts des Nombres (« tg je ne connais pas » aussi)
        sortie = []
        reste = args[1:] if mode == "maths" else args
        core.modifier(lambda s: sortie.extend(maths.commande(s, reste)))
        print("\n".join(sortie))
        return
    if mode == "explique":                     # tg explique rm : la fiche d'une commande et de ses options
        st = core.load() or {}
        print("\n".join(explique.fiche(st, " ".join(args[1:]))))
        return
    if mode in ("theme", "thème"):             # tg theme [nom] : le thème (couleurs du terminal, espace, bureau)
        creer_si_besoin()
        print(commande_theme([a.lower() for a in args[1:]]))
        return
    if mode == "langue":
        if len(args) > 1:
            if core.load() is None:
                creer_si_besoin()
            print(changer_langue(args[1]))
        else:
            print(t("app.langue.actuelle", langue=langue.LANGUES[langue.courante()]) + "\n" + liste_langues())
        return
    if mode == "installer":
        faits = compagnon.installer()
        print(t("app.installe", liste="\n  " + "\n  ".join(faits)) if faits else t("app.aucun_shell"))
        print(t("app.nouveau_terminal"))
        return
    if mode == "desinstaller":
        faits = compagnon.desinstaller()
        print(t("app.retire", liste="\n  " + "\n  ".join(faits)) if faits else t("app.rien_a_retirer"))
        return
    if mode == "partie":                       # tg partie nouvelle | charger [n]
        from . import accueil
        if core.load() is None:
            creer_si_besoin()
        else:
            print(accueil.commande(args[1:]))
        return
    if mode in ("entrainement", "exercice", "badges"):    # la salle d'entraînement, les badges et les titres
        creer_si_besoin()
        sortie = []
        try:
            ici = os.getcwd()
        except OSError:
            ici = None
        if mode == "badges":
            core.modifier(lambda s: sortie.extend(entrainement.commande_badges(s, args[1:])))
        else:
            etape(spontane=False, defis=False, cwd=ici)        # les dernières commandes tapées d'abord
            core.modifier(lambda s: sortie.extend(entrainement.commande_texte(s, args[1:], ici)))
        print("\n".join(sortie))
        return
    if mode == "vacances":                     # tg vacances [oui|non] : la faim en pause (vacances, école)
        creer_si_besoin()
        choix = args[1].lower() if len(args) > 1 else ""
        on = True if choix in ("on", "oui", "yes") else False if choix in ("off", "non", "no") else None
        sortie = []
        core.modifier(lambda s: sortie.append(satiete.vacances(s, on)))
        print(sortie[0] if sortie else "")
        return
    if mode == "satiete":                      # tg satiete : l'état, l'assiette du jour, la série de soins
        creer_si_besoin()
        st = core.modifier(lambda s: core.tick(s))
        print("\n".join([f" {fg(213)}{BOLD}" + t("sat.ecran.titre") + RESET] + ["  " + x for x in satiete.lignes(st)]))
        return
    if mode == "envies":                       # tg envies : les 6 envies, et comment faire plaisir à chacune
        creer_si_besoin()
        print("\n".join(envies.ecran(core.modifier(lambda s: envies.tick(s, [])))))
        return
    if mode == "defi":                         # tg defi : un défi éclair tout de suite (l'envie de jouer)
        creer_si_besoin()
        st = core.modifier(lambda s: core.defi_start(s) if not s.get("defi") else None)
        print(t("core.defi.dit", cmd=piege(st["defi"]["cmd"])) if st and st.get("defi") else "")
        return
    if mode == "aura":                         # tg aura on|off : l'aura de rareté autour de la créature
        creer_si_besoin()
        print(commande_aura(args[1:]))
        return
    if mode in ("carte", "quetes", "quete", "journal", "aile", "ailes", "histoire"):
        creer_si_besoin()
        print(commande_histoire(mode, args[1:]))
        return
    if mode in ("guide", "types") or (mode == "equipe" and len(args) > 1 and args[1].lower() == "guide"):
        creer_si_besoin()                      # le guide (guide.py) : tg guide [nom], tg equipe guide <nom>, tg types
        print(commande_guide(mode, args[1:]))
        return
    if mode == "equipe":
        mode = "troupe"
    if mode in ("compte", "sync", "drapeau", "lexique", "site", "bestiaire", "collection", "troupe", "anime"):
        creer_si_besoin()
        if mode == "troupe":
            if len(args) > 1:
                with core.verrou():
                    st = core.load(); print(equipe.choisir(st, " ".join(args[1:]))); core.save(st)
            else:
                print("\n".join(equipe.ecran_equipe(core.load())))
        elif mode == "anime":
            equipe.jouer(core.load(), args[1:])
        elif mode == "site":
            print(recense.site(args[1:]))
        elif mode == "bestiaire":
            print("\n".join(explo.fiche(core.load(), " ".join(args[1:]))))
        elif mode == "collection":
            print("\n".join(explo.ecran_collection(core.load())))
        elif mode == "compte":
            print(recense.commande(args[1:]))
        elif mode == "sync":
            print(recense.synchroniser(forcer=True) or t("app.rien_a_synchroniser"))
        elif mode == "drapeau":
            print(recense.drapeau(" ".join(args[1:])) if len(args) > 1 else t("app.drapeau.exemple"))
        else:
            print("\n".join(lexique.lignes(core.load())))
        return
    global SYNC_AUTO
    SYNC_AUTO = True
    from . import accueil, parties
    once = "--une-fois" in sys.argv
    # le menu des parties : seulement au lancement interactif de `tg` (ou `tg parties`), jamais au premier
    # lancement (on va directement à « nouvelle partie »), ni pour --une-fois, le prompt ou les sous-commandes
    if (mode == "parties" or (not mode and not once and sys.stdin.isatty() and sys.stdout.isatty())) \
            and not parties.aucune():
        if not accueil.menu():
            print(t("app.a_bientot"))
            return
        mode = ""
    if mode == "parties":
        mode = ""
    creer_si_besoin()
    if mode == "dressage":
        vue_dressage()
        return
    if mode == "mini":
        from . import mini
        mini.lancer(etape)
    elif mode == "bureau":
        from . import bureau
        bureau.lancer(etape, args[1:])
    elif mode == "espace":                     # l'espace de travail (fenêtre dédiée, classe, ou texte)
        from . import espace
        espace.lancer(etape, args[1:])
    elif mode == "cerveau":                    # le cerveau de ta créature (son code d'états qui vit)
        from . import cerveau
        cerveau.lancer(etape, args[1:])
    elif mode == "veille":
        veille()
    elif mode in ("combat", "monstre", "monstres"):
        vue_dressage()
    elif mode:
        print(t("app.mode_inconnu", mode=mode))
    else:
        fenetre(once)
