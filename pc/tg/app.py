"""Écran principal, menus (recherche, arbre, collection) et boucle de jeu."""
import os
import random
import re
import sys
import textwrap
import time

import subprocess

from . import compagnon, core, dressage, equipe, explo, lecons, lexique, notif, recense, registre, sprites
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
        return render_dressage(state, interactif)
    lvl = core.level(state["xp"])
    st = core.stage(lvl)
    if anim:
        w = max(len(_ANSI.sub("", l)) for l in anim)
        sprite = list(anim)
    else:
        sprite, w = sprites.creature(state)
        sprite = ([" " * w] + sprite) if frame % 2 else (sprite + [" " * w])
    lg = max(20, w)
    left = ["  " + line + " " * (lg - w) for line in sprite]

    forme = core.forme(state, lvl)
    lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
    stats = "  ".join(f"{fg(v['color'])}{core.nom_stat(v['stat'], court=True)}{RESET} {BOLD}{state['stats'][v['stat']]}{RESET}"
                      for v in core.CATEGORIES.values())
    nb_sk = len(state["skills"])
    xp_l, faim_l = t("app.xp"), t("app.faim")
    lj = max(largeur(xp_l), largeur(faim_l))
    right = [
        (arc_en_ciel(state["name"] + " ✨") if state.get("shiny") else f"{BOLD}{state['name']}{RESET}")
        + " · " + t("app.forme_niveau", forme=forme, n=lvl),
        f"{DIM}" + t("app.caractere", trait=core.nom_trait(state["trait"])) + RESET,
        f"{ajuster(xp_l, lj)} {sprites.bar(state['xp'] - lo, hi - lo)} {state['xp']}/{hi}",
        f"{ajuster(faim_l, lj)} {dressage.jauge(state['hunger'], 100, 10)} {core.mood(state['hunger'])}",
        stats,
        t("app.competences_bestioles", n=nb_sk, b=sum(state["collection"].values())),
    ]
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

    les, etiquette = lecons.lecon_courante(state)
    if les:
        if lvl < les["niveau"]:
            lines.append(title_line(t("app.lecon.niveau_requis", etiquette=etiquette, n=les["niveau"])))
            idees, n = core.faim_d_apprendre(state, les["niveau"])
            lines.append(" " + t("app.lecon.faim", cmds=f"{fg(226)}{'   '.join(idees)}{RESET}"))
            lines.append(f" {DIM}" + t("app.lecon.encore", n=n) + RESET)
        else:
            step = les["steps"][state["step"]]
            lines.append(title_line(t("app.lecon.titre", etiquette=etiquette, titre=lecons.tx(les["titre"]),
                                      n=state["step"] + 1, total=len(les["steps"])), 213))
            for x in envelopper(lecons.tx(step["dit"]), 78):
                lines.append(f" {x}")
            lines.append(f"   {fg(226)}➜ {piege(step['cmd'])}{RESET}")
            if "nid/" in step["cmd"] or step["cmd"].endswith(" nid") or "reserve.txt" in step["cmd"]:
                lines.append(f"   {DIM}" + t("app.lecon.depuis", terrain=terme("terrain", palier(state)),
                                            cmd=f"cd ~/{core.TERRAIN.name}") + RESET)
            if step.get("astuce"):
                lines.append(f"   {DIM}{lecons.tx(step['astuce'])}{RESET}")
    elif all(state["arbre"].get(b, 0) >= len(v["lecons"]) for b, v in lecons.ARBRE.items() if lecons.branche_dispo(b)):
        lines.append(title_line(t("app.arbre.maitrise"), 213))
        lines.append(f" {DIM}" + t("app.arbre.maitrise.suite") + RESET)
    else:
        lines.append(title_line(t("app.arbre.ouvert"), 213))
        lines.append(" " + t("app.arbre.choisis"))

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
        lines.append(f"{fg(244)} " + t("app.touches") + RESET)
    else:
        lines.append(f"{DIM} " + t("app.digere_ferme") + RESET)
    return "\n".join(lines) + "\n"


def vue_dressage():
    """tg dressage : la fenêtre du face-à-face, qui se met à jour toute seule pendant que tu tapes ailleurs."""
    sys.stdout.write("\033[?25l")
    try:
        fini = None
        vu = None                                 # le dernier face-à-face affiché (pour l'animation de fin)
        while True:
            state = etape(spontane=False, defis=False)
            if state is None:
                return
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


def render_dressage(state, interactif):
    """Pendant un dressage : le face-à-face seulement (plus la bulle et les deux dernières lignes du journal)."""
    lines = dressage.lignes_ecran(state)
    b = core.bulle_courante(state)
    if b:
        lines += ["", f"  {BOLD}» {raccourcir(' '.join(b[0].split()), 90)}{RESET}"]
    lines.append(title_line(t("app.journal")))
    lines += [" " + l for l in state["log"][-2:]]
    if interactif:
        lines.append(f"{fg(244)} " + t("app.dressage.touches") + RESET)
    return "\n".join(lines) + "\n"


# ================================================================ étape de jeu (partagée par tous les modes)

def boucle_jeu(state, lines, spontane=True, rythme=1.5, defis=True):
    core.tick(state)
    for line in lines:
        core.feed(state, line)
    lecons.tick(state, lines)
    dressage.tick(state, lines)
    equipe.tick(state, lines)
    explo.tick(state, spontane, proba=rythme / 480, jeu=sum(1 for l in lines if not core.est_colle(l)))
    core.defi_tick(state, lines, spontaneous=spontane and defis, proba=rythme / 300)
    core.idle_talk(state, proba=min(1.0, 0.08 * rythme / 1.5))


def etape(spontane=True, rythme=1.5, defis=True, avant_save=None, extra=None):
    """Charge, fait vivre la créature, sauvegarde, puis envoie les notifications."""
    with core.verrou():
        state = core.load()
        if state is None:
            return None
        core.migrate(state)
        lines = core.read_new_lines(state) + list(extra or [])
        avant = state["total"]
        boucle_jeu(state, lines, spontane, rythme, defis)
        state["_vient_de_manger"] = state["total"] > avant
        if avant_save:
            avant_save(state)
        a_envoyer, state["notifs"] = state["notifs"], []
        core.save(state)
    try:
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
    noms = list(lecons.ARBRE)
    while True:
        clear()
        print(f" {fg(213)}── 🌳 " + t("app.arbre.titre") + f" ──{RESET}\n")
        if not lecons.tronc_fini(state):
            print(" " + t("app.arbre.tronc_dabord", n=state["lesson"], total=len(lecons.TRONC)) + "\n")
        for i, b in enumerate(noms, 1):
            br = lecons.ARBRE[b]
            fait = state["arbre"].get(b, 0)
            tot = len(br["lecons"])
            etat = t("app.arbre.maitrisee") if fait >= tot else (t("app.arbre.en_cours") if state.get("branche") == b else "")
            if not lecons.branche_dispo(b):
                etat = t("app.arbre.android")
            print(f" {BOLD}{i}. {br['icone']} {lecons.nom_branche(b)}{RESET} ({fait}/{tot}) {fg(78)}{etat}{RESET}")
            print(f"    {DIM}" + t("app.arbre.desc", desc=lecons.tx(br["desc"]), stat=core.nom_stat(br["stat"])) + RESET)
            for j, les in enumerate(br["lecons"]):
                marque = "■" if j < fait else "□"
                print(f"    {marque} {lecons.tx(les['titre'])} → {core.nom_skill(les['skill'])} {DIM}("
                      + t("app.arbre.skill", desc=t("skill." + les["skill"] + ".desc"), n=les["niveau"]) + f"){RESET}")
            print()
        print(" " + t("app.arbre.competences", liste=", ".join(core.nom_skill(x) for x in state["skills"])
                      or t("app.arbre.aucune")) + "\n")
        if not lecons.tronc_fini(state):
            clav.demander(f" {DIM}" + t("app.entree_retour") + RESET)
            return
        r = clav.demander(" " + t("app.arbre.numero") + " ").strip()
        if not r:
            return
        if r.isdigit() and 1 <= int(r) <= len(noms):
            b = noms[int(r) - 1]
            if state["arbre"].get(b, 0) >= len(lecons.ARBRE[b]["lecons"]) or not lecons.branche_dispo(b):
                continue
            core.modifier(lambda s: lecons.choisir_branche(s, b))
            return


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

def creer_si_besoin():
    with core.verrou():
        state = core.load()
        if state is None:
            try:
                code = langue.detecter()          # premier lancement : la langue du système
                langue.definir(code)
                name = input(t("app.nom_creature") + " ").strip()[:16] or "Pixel"
            except (KeyboardInterrupt, EOFError):
                print("\n" + t("app.a_bientot"))
                raise SystemExit(0)
            state = core.migrate(core.new_state(name, code))
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


def _preparer_anim(state, nom):
    """[images, ips, image courante, nombre d'images à jouer] : court (≈ 3 s), jamais bloquant."""
    try:
        frames, ips = sprites.animation(state, nom)
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
                    if not once and evt and evt[1] > vu_anim:
                        vu_anim = evt[1]
                        if now - evt[1] < 15:
                            anim = _preparer_anim(state, evt[0]) or anim
                    elif not once and anim is None and now >= ambiance:
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
                k = k.lower()
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
    return "\n".join(langue.remplir(l, {}) for l in langue.liste("app.aide"))


def main():
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
