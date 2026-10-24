"""Écran principal, menus (recherche, arbre, collection) et boucle de jeu."""
import os
import sys
import textwrap
import time

import subprocess

from . import compagnon, core, explo, lecons, lexique, notif, recense, registre, sprites
from .bestiaire import arc_en_ciel

SYNC_AUTO = False   # synchro en fond, seulement pour les modes qui restent ouverts
from .plateforme import (BOLD, DIM, DISTRO, IS_WIN, OS_NAMES, OSK, RESET, Clavier, clear, fg, piege)


def title_line(text, color=244):
    return fg(color) + "── " + text + " " + "─" * max(3, 44 - len(text)) + RESET


def render(state, frame, interactif):
    lvl = core.level(state["xp"])
    st = core.stage(lvl)
    sprite, w = sprites.creature(state)
    sprite = ([" " * w] + sprite) if frame % 2 else (sprite + [" " * w])
    left = ["  " + line + " " * (20 - w) for line in sprite]

    forme = core.STAGES[st] + (f" {core.FORMES[state['branch']]}" if st >= 2 and state.get("branch") else "")
    lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
    stats = "  ".join(f"{v['short']} {state['stats'][v['stat']]}" for v in core.CATEGORIES.values())
    nb_sk = len(state["skills"])
    right = [
        (arc_en_ciel(state["name"] + " ✨") if state.get("shiny") else f"{BOLD}{state['name']}{RESET}") + f" · {forme} · niv. {lvl}",
        f"{DIM}caractère : {state['trait']}{RESET}",
        f"XP   {sprites.bar(state['xp'] - lo, hi - lo)} {state['xp']}/{hi}",
        f"Faim {sprites.bar(state['hunger'], 100)} {core.mood(state['hunger'])}",
        stats,
        f"Compétences {nb_sk} · Bestioles {sum(state['collection'].values())}",
    ]
    n = max(len(left), len(right))
    left += [" " * 22] * (n - len(left))
    right += [""] * (n - len(right))
    lines = [l + r for l, r in zip(left, right)]

    b = state["bubble"]
    if b and time.time() < b[1]:
        wrapped = textwrap.wrap(b[0], 52)
        lines.append(f"  {BOLD}» {wrapped[0]}{RESET}")
        lines += [f"    {BOLD}{x}{RESET}" for x in wrapped[1:]]
    else:
        lines.append("")

    d = state["defi"]
    if d:
        reste = max(0, core.defi_duree(state) - (time.time() - d["start"]))
        lines.append(title_line(f"⚡ DÉFI ÉCLAIR : tape « {piege(d['cmd'])} » — {reste:.0f} s", 226))

    les, etiquette = lecons.lecon_courante(state)
    if les:
        if lvl < les["niveau"]:
            lines.append(title_line(f"{etiquette} : niveau {les['niveau']} requis"))
            lines.append(f" {DIM}Continue à me nourrir, je dois encore grandir…{RESET}")
        else:
            step = les["steps"][state["step"]]
            lines.append(title_line(f"{etiquette} : {les['titre']} ({state['step'] + 1}/{len(les['steps'])})", 213))
            lines.append(f" {step['dit']}")
            lines.append(f"   {fg(226)}➜ {piege(step['cmd'])}{RESET}")
            if step.get("astuce"):
                lines.append(f"   {DIM}{step['astuce']}{RESET}")
    elif all(state["arbre"].get(b, 0) >= len(v["lecons"]) for b, v in lecons.ARBRE.items() if lecons.branche_dispo(b)):
        lines.append(title_line("Arbre entièrement maîtrisé !", 213))
        lines.append(f" {DIM}Tu es un vrai maître du terminal. D'autres branches viendront.{RESET}")
    else:
        lines.append(title_line("Arbre de compétences ouvert", 213))
        lines.append(" Choisis la branche que je vais t'apprendre : touche [a]")

    lines.append(title_line(f"Ce que je digère ({DISTRO or OS_NAMES[OSK]})"))
    for k, v in core.CATEGORIES.items():
        lines.append(f" {fg(v['color'])}{v['stat']:<13}{RESET}{core.EXAMPLES[OSK][k]}")

    lines.append(title_line("Journal"))
    if state["total"] == 0:
        lines.append(" Ouvre un AUTRE terminal et tape des commandes !")
        if IS_WIN:
            lines.append(" (utilise PowerShell : cmd.exe ne garde pas d'historique)")
        elif not compagnon.est_installe():
            lines.append(f" {fg(226)}Astuce : appuie sur [o] puis 3 pour que je voie")
            lines.append(f" tes commandes en direct (sinon, seulement à la fermeture du terminal).{RESET}")
    lines += [" " + l for l in state["log"][-4:]]
    if interactif:
        lines.append(f"{fg(244)} [/] chercher [l] lexique [a] arbre [c] collection [o] options [q] quitter{RESET}")
    else:
        lines.append(f"{DIM} il digère même fermé{RESET}")
    return "\n".join(lines) + "\n"


# ================================================================ étape de jeu (partagée par tous les modes)

def boucle_jeu(state, lines, spontane=True, rythme=1.5, defis=True):
    core.tick(state)
    for line in lines:
        core.feed(state, line)
    lecons.tick(state, lines)
    explo.tick(state, spontane, proba=rythme / 480)
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
        print(f" {fg(213)}── 🔎 Demande à {state['name']} ──{RESET}")
        print(f" {DIM}Un nom de commande (grep, mkdir…) ou ce que tu veux faire")
        print(f" (« supprimer un dossier », « voir les fichiers cachés »).{RESET}\n")
        for l in historique:
            print(l)
        q = clav.demander(f" {BOLD}> {RESET}").strip()
        if not q:
            return
        res = registre.chercher(q)
        core.modifier(lambda s: registre.memoriser(s, res))
        historique = [f" {DIM}Tu as demandé : {q}{RESET}", ""] + registre.afficher(res, state["name"])
        if res:
            historique.append(f" {DIM}Tape-la toi-même dans ton terminal (le copier-coller ne nourrit pas) :")
            historique.append(f" bonus « bien retenu » si tu l'utilises dans les 15 min !{RESET}")
        historique.append(f" {DIM}(Entrée vide = retour){RESET}\n")


def menu_arbre(state, clav):
    noms = list(lecons.ARBRE)
    while True:
        clear()
        print(f" {fg(213)}── 🌳 Arbre de compétences ──{RESET}\n")
        if not lecons.tronc_fini(state):
            print(f" Termine d'abord le tronc commun ({state['lesson']}/{len(lecons.TRONC)} leçons).\n")
        for i, b in enumerate(noms, 1):
            br = lecons.ARBRE[b]
            fait = state["arbre"].get(b, 0)
            tot = len(br["lecons"])
            etat = "✔ maîtrisée" if fait >= tot else ("◀ en cours" if state.get("branche") == b else "")
            if not lecons.branche_dispo(b):
                etat = "réservée à Android (Termux)"
            print(f" {BOLD}{i}. {br['icone']} {b}{RESET} ({fait}/{tot}) {fg(78)}{etat}{RESET}")
            print(f"    {DIM}{br['desc']} · nourrit {br['stat']}{RESET}")
            for j, les in enumerate(br["lecons"]):
                marque = "■" if j < fait else "□"
                sk = core.SKILLS[les["skill"]]["desc"]
                print(f"    {marque} {les['titre']} → {les['skill']} {DIM}({sk}, niv. {les['niveau']}){RESET}")
            print()
        print(f" Compétences : {', '.join(state['skills']) or 'aucune'}\n")
        if not lecons.tronc_fini(state):
            clav.demander(f" {DIM}Entrée pour revenir{RESET}")
            return
        r = clav.demander(" Numéro de la branche à suivre (Entrée = retour) : ").strip()
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
    clav.demander(f"\n {DIM}Entrée pour revenir{RESET}")


def menu_lexique(state, clav):
    clear()
    st = core.load() or state
    for l in lexique.lignes(st):
        print(l)
    clav.demander(f"\n {DIM}Entrée pour revenir{RESET}")


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
        onoff = lambda b: f"{fg(78)}ON{RESET}" if b else f"{fg(203)}OFF{RESET}"
        clear()
        print(f" {fg(213)}── ⚙ Options ──{RESET}\n")
        print(f" 1. Notifications : {onoff(cfg['notifs'])}  {DIM}({moteur or 'aucun système détecté'}){RESET}")
        if moteur == "android":
            print(f" 2. Notification permanente : {onoff(cfg['permanente'])}")
        else:
            print(f" 2. Notification permanente : {DIM}Android uniquement (sur PC : compagnon de bureau){RESET}")
        print(f" 3. Compagnon dans le terminal : {onoff(installe)}")
        print(f" 4. Style du compagnon : {BOLD}{cfg['compagnon']}{RESET} {DIM}(ligne / coin){RESET}")
        print(" 5. Envoyer une notification de test")
        print(f" 6. Ouvrir le compagnon de bureau {DIM}(PC){RESET}")
        c = st.get("compte", {})
        print(f" 7. Recensement en ligne : {BOLD}{c.get('pseudo') or 'pas de compte'}{RESET} "
              f"{DIM}(même créature sur PC et téléphone){RESET}")
        print(f"\n {DIM}Mini-terminal toujours visible : lance « … terminagotchi.pyz mini »")
        print(f" (sur Android, dans Termux:Float){RESET}")
        if msg:
            print(f"\n {msg}")
        r = clav.demander("\n Choix (Entrée = retour) : ").strip()
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
            verbe = "Retiré de" if installe else "Installé dans"
            msg = (f"{verbe} : " + ", ".join(faits) + ("" if installe else
                   "\n Ouvre un NOUVEAU terminal pour voir ta créature dans l'invite.")) if faits \
                else "Aucun fichier de configuration de shell trouvé."
        elif r == "4":
            core.modifier(lambda s: s["config"].update(compagnon="coin" if s["config"]["compagnon"] == "ligne" else "ligne"))
        elif r == "5":
            ok = notif.envoyer(st, [f"Coucou ! Ceci est une notification de test de {st['name']}."], forcer=True)
            msg = "Notification envoyée !" if ok else "Échec : aucun système de notification disponible."
            if moteur == "android":
                notif.permanente(st)
        elif r == "6":
            msg = "Compagnon de bureau lancé !" if lancer_detache("bureau") else "Impossible de le lancer."
        elif r == "7":
            menu_recensement(clav)


def menu_recensement(clav):
    msg = recense.commande([])
    while True:
        clear()
        print(f" {fg(213)}── 🌍 Recensement ──{RESET}\n")
        print(" " + msg.replace("\n", "\n ") + "\n")
        st = core.load()
        a_compte = bool(st and st.get("compte", {}).get("cle"))
        if a_compte:
            print(" 1. Obtenir un code pour relier un autre appareil\n 2. Synchroniser maintenant\n 3. Valider un drapeau du CTF web")
        else:
            print(" 1. Créer mon compte\n 2. Relier ce PC au compte de mon téléphone (code)")
        r = clav.demander("\n Choix (Entrée = retour) : ").strip()
        if not r:
            return
        if a_compte:
            if r == "1":
                msg = recense.commande(["code"])
            elif r == "2":
                msg = recense.synchroniser(forcer=True) or "Rien à synchroniser."
            elif r == "3":
                msg = recense.drapeau(clav.demander(" Drapeau (TG{…}) : "))
        elif r == "1":
            msg = recense.commande(["creer", clav.demander(" Pseudo (3 à 20 lettres, chiffres, - ou _) : ").strip()])
        elif r == "2":
            msg = recense.commande(["lier", clav.demander(" Code affiché sur ton téléphone : ").strip()])


# ================================================================ modes

def creer_si_besoin():
    with core.verrou():
        state = core.load()
        if state is None:
            name = input("Comment s'appelle ta créature ? ").strip() or "Pixel"
            state = core.migrate(core.new_state(name))
            core.read_new_lines(state)   # mémorise où on en est, sans manger l'ancien historique
            core.log(state, f"Un œuf est apparu… il a l'air {state['trait']}.")
            state["notifs"] = []
            core.save(state)


def fenetre(once):
    if "--defi" in sys.argv:
        core.modifier(core.defi_start)
    frame = 0
    clav = Clavier()
    interactif = clav.ok and not once
    try:
        with clav:
            while True:
                state = etape(spontane=not once)
                clear()
                sys.stdout.write(render(state, frame, interactif))
                sys.stdout.flush()
                if once:
                    break
                frame += 1
                k = clav.touche(1.5)
                if not k:
                    continue
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
    print(RESET + "\nÀ plus tard ! (je continue de digérer ton historique)")


def veille():
    """Fait vivre la créature en arrière-plan : faim, bestioles, notifications."""
    print("Terminagotchi en veille (Ctrl+C pour arrêter)…")
    try:
        while True:
            st = etape(spontane=True, rythme=30, defis=False)
            if st:
                print(f"\r{time.strftime('%H:%M')} {st['name']} · niv. {core.level(st['xp'])} · "
                      f"faim {int(st['hunger'])}%   ", end="", flush=True)
            time.sleep(30)
    except KeyboardInterrupt:
        print()


AIDE = """Terminagotchi — utilisation :
  terminagotchi.pyz            fenêtre principale
  terminagotchi.pyz mini       mini-terminal : créature + ligne de commande (Termux:Float)
  terminagotchi.pyz bureau     compagnon de bureau flottant (PC)
  terminagotchi.pyz veille     vit en arrière-plan (notifications)
  terminagotchi.pyz installer  ajoute la créature à l'invite de ton terminal (+ le raccourci « tg »)
  terminagotchi.pyz desinstaller
  tg lexique                   toutes les commandes, par chapitres
  tg compte                    recensement en ligne : compte creer Pseudo · compte code · compte lier CODE
  tg sync                      synchronise ta créature (PC ↔ téléphone)
  tg site [bestiaire|captures] ouvre le site du recensement (ton profil par défaut)
  tg collection · tg bestiaire <nom>   tes bestioles · la fiche d'une espèce
  tg compte partage on|off     montrer (ou non) tes captures dans la galerie du site
  tg drapeau TG{…}             valide un drapeau du CTF web
  Options : --une-fois (affiche et quitte) · --defi (défi immédiat)"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0].lower() if args else ""
    if mode == "prompt":                       # appelé par le shell : ne doit jamais gêner
        try:
            compagnon.prompt(etape)
        except Exception:
            pass
        return
    if mode in ("aide", "help", "-h"):
        print(AIDE)
        return
    if mode == "installer":
        faits = compagnon.installer()
        print("Installé dans :\n  " + "\n  ".join(faits) if faits else "Aucun shell trouvé.")
        print("Ouvre un nouveau terminal pour voir ta créature.")
        return
    if mode == "desinstaller":
        faits = compagnon.desinstaller()
        print("Retiré de :\n  " + "\n  ".join(faits) if faits else "Rien à retirer.")
        return
    if mode in ("compte", "sync", "drapeau", "lexique", "site", "bestiaire", "collection"):
        creer_si_besoin()
        if mode == "site":
            print(recense.site(args[1:]))
        elif mode == "bestiaire":
            print("\n".join(explo.fiche(core.load(), " ".join(args[1:]))))
        elif mode == "collection":
            print("\n".join(explo.ecran_collection(core.load())))
        elif mode == "compte":
            print(recense.commande(args[1:]))
        elif mode == "sync":
            print(recense.synchroniser(forcer=True) or "Rien à synchroniser.")
        elif mode == "drapeau":
            print(recense.drapeau(" ".join(args[1:])) if len(args) > 1 else "Exemple : tg drapeau TG{abc123}")
        else:
            print("\n".join(lexique.lignes(core.load())))
        return
    global SYNC_AUTO
    SYNC_AUTO = True
    creer_si_besoin()
    if mode == "mini":
        from . import mini
        mini.lancer(etape)
    elif mode == "bureau":
        from . import bureau
        bureau.lancer(etape)
    elif mode == "veille":
        veille()
    else:
        fenetre("--une-fois" in sys.argv)
