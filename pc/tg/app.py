"""Écran principal, menus (recherche, arbre, collection) et boucle de jeu."""
import os
import random
import re
import sys
import textwrap
import time

import subprocess

from . import (compagnon, core, dressage, entrainement, envies, equipe, guide, exemples, explique, explo, histoire, intro, lecons, lexique,
               maison, notif, quetes, recense, registre, sprites, terrain)
from .bestiaire import arc_en_ciel
from . import langue
from .langue import ajuster, envelopper, largeur, raccourcir, t
from .mots import palier, terme

SYNC_AUTO = False   # synchro en fond, seulement pour les modes qui restent ouverts
from .plateforme import (BOLD, DIM, DISTRO, IS_WIN, OS_NAMES, OSK, RESET, Clavier, clear, fg, piege)


def title_line(text, color=244):
    return fg(color) + "── " + text + " " + "─" * max(3, 44 - largeur(text)) + RESET


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def render(state, frame, interactif, anim=None):
    """anim : les lignes d'une image d'animation à afficher à la place du dessin habituel."""
    d = state.get("dressage")
    if d and not d.get("fenetre"):          # pas de fenêtre possible (pas d'écran graphique) : on l'affiche ici
        return render_dressage(state, interactif, anim)
    if intro.en_cours(state):               # l'œuf seul, sa liste de commandes et l'invite (intro.py)
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
        sprite, w = dessin_guide(state, frame)                         # le guide (+ son aura de rareté, tg aura)
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
                  jauges[1] + (f"  {fg(214)}💭 {envies.ICONES[m['e']]} {envies.nom(m['e'])}{RESET}" if m else "")]
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
    if les:
        ch = histoire.PAR_CHAP[les["chap"]]
        lines.append(title_line(t("hist.ecran.chapitre", icone=maison.ICONES.get(ch["piece"], "📖"),
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
            lines.append(f"   {fg(226)}➜ `{piege(step['cmd'])}`{RESET}")
            for montre, cle in explique.nouvelles(state, step["cmd"]):      # 💡 Le -r veut dire…
                for k, p in enumerate(explique.phrases(state, montre, cle)):   # (+ pour les grands, palier ≥ 1)
                    for x in envelopper(p, 74 - 2 * k):
                        lines.append(f"   {'  ' * k}{DIM}{x}{RESET}")
            if " nid/" in " " + step["cmd"] or step["cmd"].endswith(" nid") or "reserve.txt" in step["cmd"] \
                    or step["cmd"].startswith(("cat coeur", "chmod 444 coeur", "echo ? > coeur", "cp -r grenier", "rm -r vieille_cabane")):
                lines.append(f"   {DIM}" + t("app.lecon.depuis", terrain=terme("terrain", palier(state)),
                                            cmd=f"cd ~/{core.TERRAIN.name}") + RESET)
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


def dessin_guide(state, frame=0):
    """La créature de l'écran principal : le GUIDE actuel (le compagnon, ou la bestiole en tête de l'équipe,
    à son stade, dans sa variante, avec son aura de rareté), sinon le compagnon sorti de l'œuf."""
    m = guide.actuel(state)
    ind = m[3]
    if ind is not None:
        cle = (ind.get("id"), equipe.stade(ind), ind.get("variante"), ind.get("shiny"), bool(aura_ecran(state) is not None))
        r = _CACHE_GUIDE.get(cle)
        if r is None:
            try:
                r = equipe.animation(ind, "statique", aura=aura_active(state))
            except Exception:
                r = None
            _CACHE_GUIDE.clear()
            _CACHE_GUIDE[cle] = r
        if r and r[0]:
            image = r[0][frame % len(r[0])]
            return list(image), max(largeur(l) for l in image)
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

def boucle_jeu(state, lines, spontane=True, rythme=1.5, defis=True, cwd=None):
    core.tick(state)
    for line in lines:
        core.feed(state, line)
    lines = intro.tick(state, lines)          # l'œuf : sa liste, ses fêlures, l'éclosion (la suite : après l'éclosion)
    exemples.tick(state, lines)               # mkdir tout seul… : une bulle avec la commande à taper
    terrain.tick(state, lines)                # terrain effacé : le reconstruire, reprendre la leçon
    histoire.tick(state, lines, cwd)          # la Maison endormie : visites, chapitres, quêtes
    dressage.tick(state, lines)
    equipe.tick(state, lines)
    if intro.ouvert(state, "combats"):        # les monstres arrivent avec leur présentation (intro.json)
        explo.tick(state, spontane, proba=rythme / 480, jeu=sum(1 for l in lines if not core.est_colle(l)), lignes=lines)
    core.defi_tick(state, lines, spontaneous=spontane and defis, proba=rythme / 300)
    envies.tick(state, lines)                 # les 6 envies : usure, plaisirs, poussière, rappel espacé
    entrainement.tick(state, lines)           # salle d'entraînement : l'exercice en cours est-il réussi ?
    guide.tick(state, lines)                  # le guide : talents, fatigue, envie de sortir, régions gardées
    core.idle_talk(state, proba=min(1.0, 0.08 * rythme / 1.5))
    intro.verifier(state)                     # les fonctions qui s'ouvrent maintenant (présentées une par une)


def etape(spontane=True, rythme=1.5, defis=True, avant_save=None, extra=None, cwd=None):
    """Charge, fait vivre la créature, sauvegarde, puis envoie les notifications.
    cwd : le dossier courant du terminal (donné par l'invite du shell), pour la carte de la maison."""
    with core.verrou():
        state = core.load()
        if state is None:
            return None
        core.migrate(state)
        lines = core.read_new_lines(state) + list(extra or [])
        avant = state["total"]
        boucle_jeu(state, lines, spontane, rythme, defis, cwd)
        state["_vient_de_manger"] = state["total"] > avant
        if avant_save:
            avant_save(state)
        a_envoyer, state["notifs"] = state["notifs"], []
        core.save(state)
    try:
        if intro.ouvert(state, "extras"):          # les notifications arrivent avec leur présentation (intro.json)
            notif.envoyer(state, a_envoyer)
            notif.permanente(state)
    except Exception:
        pass
    if SYNC_AUTO:
        recense.synchroniser_en_fond()
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
    msg = ""
    while True:
        st = core.load() or state
        core.migrate(st)
        cfg = st["config"]
        moteur = notif.systeme()
        installe = compagnon.est_installe()
        onoff = lambda b: f"{fg(78)}{t('app.on')}{RESET}" if b else f"{fg(203)}{t('app.off')}{RESET}"
        clear()
        print(f" {fg(213)}── ⚙ " + t("app.options.titre") + f" ──{RESET}\n")
        print(" 1. " + t("app.options.notifs", etat=onoff(cfg["notifs"]))
              + f"  {DIM}({moteur or t('app.options.aucun_systeme')}){RESET}")
        if moteur == "android":
            print(" 2. " + t("app.options.permanente", etat=onoff(cfg["permanente"])))
        else:
            print(" 2. " + t("app.options.permanente", etat=f"{DIM}{t('app.options.permanente.pc')}{RESET}"))
        print(" 3. " + t("app.options.compagnon", etat=onoff(installe)))
        print(" 4. " + t("app.options.style", style=f"{BOLD}{t('app.style.' + cfg['compagnon'])}{RESET}")
              + f" {DIM}({t('app.style.ligne')} / {t('app.style.coin')}){RESET}")
        print(" 5. " + t("app.options.test"))
        print(" 6. " + t("app.options.bureau") + f" {DIM}(PC){RESET}")
        c = st.get("compte", {})
        print(" 7. " + t("app.options.recensement", pseudo=f"{BOLD}{c.get('pseudo') or t('app.options.pas_de_compte')}{RESET}")
              + f" {DIM}" + t("app.options.recensement.meme") + RESET)
        print(" 8. " + t("app.options.langue", langue=f"{BOLD}{langue.LANGUES[langue.courante()]}{RESET}")
              + f" {DIM}(tg langue xx){RESET}")
        print(f"\n {DIM}" + t("app.options.mini1"))
        print(" " + t("app.options.mini2") + RESET)
        if msg:
            print(f"\n {msg}")
        r = clav.demander("\n " + t("app.choix") + " ").strip()
        msg = ""
        if not r:
            return
        if r == "1":
            core.modifier(lambda s: s["config"].update(notifs=not s["config"]["notifs"]))
        elif r == "2" and moteur == "android":
            core.modifier(lambda s: s["config"].update(permanente=not s["config"]["permanente"]))
            notif.permanente(core.load())
        elif r == "3":
            faits = compagnon.desinstaller() if installe else compagnon.installer()
            msg = (t("app.retire" if installe else "app.installe", liste=", ".join(faits))
                   + ("" if installe else "\n " + t("app.options.nouveau_terminal"))) if faits \
                else t("app.options.aucun_shell")
        elif r == "4":
            core.modifier(lambda s: s["config"].update(compagnon="coin" if s["config"]["compagnon"] == "ligne" else "ligne"))
        elif r == "5":
            ok = notif.envoyer(st, [t("app.options.test.texte", nom=st["name"])], forcer=True)
            msg = t("app.options.test.ok") if ok else t("app.options.test.echec")
            if moteur == "android":
                notif.permanente(st)
        elif r == "6":
            msg = t("app.options.bureau.ok") if lancer_detache("bureau") else t("app.options.bureau.echec")
        elif r == "7":
            menu_recensement(clav)
        elif r == "8":
            msg = menu_langue(clav)


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

def creer_si_besoin(avec_intro=None):
    """Premier lancement : la créature est créée. avec_intro (par défaut : une vraie personne au clavier) :
    les écrans de l'intro, puis l'œuf et sa liste de commandes, et le jeu qui s'ouvre petit à petit (intro.py).
    Sans personne au clavier (scripts, tests), tout est ouvert tout de suite."""
    if core.load() is not None:
        return
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
    return " " + t("aura.etat", etat=etat) + f"\n {DIM}" + t("aura.legende") + RESET


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
                    state = etape(spontane=not once)
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
                        if _nuit():
                            anim = _preparer_anim(state, "dort")
                        elif state["hunger"] < 30:
                            anim = _preparer_anim(state, "affame")
                        elif random.random() < 0.3:
                            anim = _preparer_anim(state, random.choice(["statique", "salut", "content"]))
                image = anim[0][anim[2] % len(anim[0])] if anim else None
                _ecran(render(state, frame, interactif, image))
                if once:
                    break
                if anim:
                    k = clav.touche(1 / anim[1])
                    anim[2] += 1
                    if anim[2] >= anim[3]:
                        anim = None
                else:
                    k = clav.touche(max(0.05, RYTHME - (time.time() - dernier)))
                if not k:
                    continue
                anim = None
                clear()
                if intro.a_montrer(state) and not intro.en_cours(state) and k.lower() != "q":
                    if k in ("\r", "\n", " "):          # Entrée : l'écran de présentation est lu
                        state = core.modifier(intro.lu) or state
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
    except KeyboardInterrupt:
        pass
    print(RESET + "\n" + t("app.a_plus_tard"))


def veille():
    """Fait vivre la créature en arrière-plan : faim, bestioles, notifications."""
    print(t("app.veille"))
    try:
        while True:
            st = etape(spontane=True, rythme=30, defis=False)
            if st:
                print(f"\r{time.strftime('%H:%M')} " + t("app.veille.ligne", nom=st["name"], n=core.level(st["xp"]),
                                                         faim=int(st["hunger"])) + "   ", end="", flush=True)
            time.sleep(30)
    except KeyboardInterrupt:
        print()


def aide():
    return "\n".join(langue.remplir(l, {}) for l in langue.liste("app.aide") + langue.liste("app.aide.histoire")
                     + [t("env.aide"), t("aura.aide"), t("ent.aide")])


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
    langue.installer_rendu()                   # les commandes à taper en vert (`…` dans les textes)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0].lower() if args else ""
    if core.load() is None:                    # pas encore de sauvegarde : la langue du système
        langue.definir(langue.detecter())
    if mode == "prompt":                       # appelé par le shell : ne doit jamais gêner
        try:
            compagnon.prompt(etape)
        except Exception:
            pass
        return
    if mode in ("aide", "help", "-h"):
        print(aide())
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
    if mode == "explique":                     # tg explique rm : la fiche d'une commande et de ses options
        st = core.load() or {}
        print("\n".join(explique.fiche(st, " ".join(args[1:]))))
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
        bureau.lancer(etape)
    elif mode == "veille":
        veille()
    elif mode in ("combat", "monstre", "monstres"):
        vue_dressage()
    elif mode:
        print(t("app.mode_inconnu", mode=mode))
    else:
        fenetre(once)
