"""Accueil et aide (idées validées le 3 novembre, maquettes /home/claude/outils/ameliorations/accueil_aide/) :
les petits coups de pouce des premières minutes, et l'aide quand on est perdu. Même règles sur Android (AideDouce.kt),
vérifiées par les vecteurs communs donnees/accueil/vecteurs.json (pc/outils/vecteurs_accueil.py).

  1. « Qui est avec toi ? » : au tout premier lancement sur cet appareil (aucune autre partie), avant l'histoire ;
     avec un adulte, 4 conseils (à relire : `tg aide parents`, Aide du menu). Le choix reste dans la sauvegarde.
  2. Le premier `ls` réussi : une petite cinématique (les lieux et les objets se dessinent en pixels), une fois ;
     plus courte (2 s) si le camp se rallume au même moment (ls = toute première commande).
  4. La flèche « tape ici » : pendant l'œuf, jusqu'à 3 commandes réussies ; elle revient après 1 minute sans rien
     taper (téléphone : la ligne de saisie s'allume ; PC : une ligne « ▼ » au-dessus de l'invite).
  5. La touche du symbole attendu s'allume (téléphone) ; sur PC, la 1re fois qu'un symbole arrive dans une leçon,
     la créature dit où il est sur le clavier (AZERTY en français, QWERTY sinon ; `tg clavier azerty|qwerty`).
  6. « Je suis perdu » : `perdu` (PC) ou le bouton 🧭 (téléphone) : où es-tu, ta leçon, quoi taper ; le bouton
     devient jaune vif après 2 erreurs de suite ou 2 minutes sans rien taper.
  9. « Fermer et revenir » : à la fin du tronc commun, une fois ; au retour, « Te revoilà ! ». Aucune récompense.
 22. `ls ?` ou `? ls` : la fiche courte de la commande (jamais nourrissante, jamais un reproche).
 25. `indice` (PC) ou le bouton 💡 (téléphone) : 3 niveaux, là où la commande n'est pas donnée (leçon en mode
     « défi sans aide », exercice de la salle d'entraînement, épreuve de dressage, réponse à trou du Sommet ; sur le
     téléphone aussi la chasse au trésor, Ctf.kt). Rien n'est retiré ; seul un
     exploit « sans indice » n'est pas donné pour cette fois (la Forge).
 66. La complétion grisée (téléphone, terminal du jeu vsh/) : seulement des noms qui existent, jamais pendant un
     exercice ou un défi sans aide.
Sauvegarde : state["aide_douce"] (voir a_()).
"""
import re
import time

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

SEUIL_FLECHE = 3          # commandes réussies avant que la flèche s'en aille
RETOUR_FLECHE = 60        # secondes sans rien taper (pendant l'œuf) : elle revient
VIF_ERREURS = 2           # le bouton « Perdu ? » devient jaune vif après 2 erreurs de suite…
VIF_ATTENTE = 120         # … ou 2 minutes sans rien taper
DUREE_LS = 3.0            # la cinématique du premier ls (secondes)
DUREE_LS_COURTE = 2.0     # juste après le camp qui se rallume

# la rangée de touches du téléphone (idée 5) : tout tient sur une ligne, ⋯ ouvre la deuxième
RANGEE1 = ["↑", "⇥", "^C", "-", "/", "~", "|", ".", ">", "⋯"]
RANGEE2 = ["↓", ">>", "*", "\"", "'", "$", "&", "_", "=", "⋯"]
SYMBOLES1 = ["-", "/", "~", "|", ".", ">"]
SYMBOLES2 = [">>", "*", "\"", "'", "$", "&", "_", "="]

# où est chaque symbole sur le clavier (idée 5, PC) : des touches (« Maj », « AltGr », « Espace » sont traduites)
CLAVIER = {
    "azerty": {"|": ["AltGr", "6"], "~": ["AltGr", "2", "+Espace"], ">": ["Maj", "<"], ">>": ["Maj", "<"],
               "*": ["*"], "/": ["Maj", ":"], "$": ["$"], "&": ["1"], "\"": ["3"], "'": ["4"], "_": ["8"]},
    "qwerty": {"|": ["Maj", "\\"], "~": ["Maj", "`"], ">": ["Maj", "."], ">>": ["Maj", "."], "*": ["Maj", "8"],
               "/": ["/"], "$": ["Maj", "4"], "&": ["Maj", "7"], "\"": ["Maj", "'"], "'": ["'"], "_": ["Maj", "-"]},
}
ORDRE_SYMBOLES = [">>", "|", "~", ">", "*", "/", "$", "&", "\"", "'", "_"]


def a_(state):
    """L'état de l'accueil et de l'aide dans la sauvegarde."""
    a = state.get("aide_douce")
    if not isinstance(a, dict):
        a = state["aide_douce"] = {}
    for k, v in {"parent": None, "reussies": 0, "erreurs": 0, "derniere": 0, "symboles": [], "premier_ls": False,
                 "fermer": None, "fermer_pid": None, "indice": None}.items():
        a.setdefault(k, v)
    return a


# ================================================================ règles pures (vecteurs communs)
def fleche(intro_en_cours, reussies, depuis):
    """Idée 4 : la flèche « tape ici » se montre-t-elle ? depuis : secondes depuis la dernière commande."""
    return bool(intro_en_cours) and (reussies < SEUIL_FLECHE or depuis >= RETOUR_FLECHE)


def perdu_vif(erreurs, depuis):
    """Idée 6 : le bouton « Perdu ? » est jaune vif (sinon il reste discret)."""
    return erreurs >= VIF_ERREURS or depuis >= VIF_ATTENTE


def touche_a_allumer(attendu, tape):
    """Idée 5 : la touche de la rangée à allumer pour la commande attendue, d'après ce qui est déjà tapé : le
    prochain symbole de la commande après la partie déjà bien tapée (« ⋯ » s'il est dans la deuxième rangée)."""
    attendu, tape = attendu or "", tape or ""
    p = 0
    while p < len(attendu) and p < len(tape) and attendu[p] == tape[p]:
        p += 1
    i = p
    while i < len(attendu):
        if attendu.startswith(">>", i):
            return "⋯"
        c = attendu[i]
        if c in SYMBOLES1:
            return c
        if c in SYMBOLES2:
            return "⋯"
        i += 1
    return None


def symbole_nouveau(attendu, vus):
    """Idée 5 (PC) : le premier symbole « difficile à trouver » de la commande qui n'a pas encore été expliqué."""
    vus = set(vus or [])
    a = attendu or ""
    trouves = []
    i = 0
    while i < len(a):
        s = ">>" if a.startswith(">>", i) else a[i]
        if s in ORDRE_SYMBOLES and s not in trouves:
            trouves.append(s)
        i += len(s)
    return next((s for s in trouves if s not in vus), None)


def demande_explique(ligne):
    """Idée 22 : `ls ?` ou `? ls` → « ls » ; sinon None."""
    m = re.match(r"^\s*([A-Za-z][A-Za-z0-9_.+-]*)\s+\?\s*$", ligne or "") or \
        re.match(r"^\s*\?\s+([A-Za-z][A-Za-z0-9_.+-]*)\s*$", ligne or "")
    return m.group(1).lower() if m else None


def parties_indice(attendu):
    """Idée 25 : ce que montrent les 3 niveaux, tiré de la commande attendue : la commande (niveau 1 : son image),
    son début avec ses options (niveau 2), toute la réponse (niveau 3)."""
    a = re.sub(r"\s+", " ", (attendu or "").strip())
    mots = a.split(" ") if a else []
    cmd = mots[0] if mots else ""
    debut = [cmd] if cmd else []
    for m in mots[1:]:
        if m.startswith("-") and len(m) > 1:
            debut.append(m)
        else:
            break
    return {"cmd": cmd, "debut": " ".join(debut), "reponse": a}


def fantome(mot, candidats):
    """Idée 66 : la fin grisée du mot en cours (le seul candidat qui commence par lui, ou leur début commun)."""
    if not mot:
        return ""
    ok = sorted({c for c in candidats if c.startswith(mot) and c != mot})
    if not ok:
        return ""
    commun = ok[0]
    for c in ok[1:]:
        k = 0
        while k < len(commun) and k < len(c) and commun[k] == c[k]:
            k += 1
        commun = commun[:k]
    return commun[len(mot):]


def tronc_fini(ailes, tronc):
    """Idée 9 : tous les chapitres du tronc commun (programme.json, « tronc ») sont réveillés."""
    besoin = []
    for k, v in sorted((tronc or {}).items()):
        if k.startswith("n") and isinstance(v, list):
            besoin += [c for c in v if c not in besoin]
    return bool(besoin) and all(c in (ailes or []) for c in besoin)


def duree_ls(camp_en_meme_temps):
    return DUREE_LS_COURTE if camp_en_meme_temps else DUREE_LS


def action_menu(reponse):
    """Idée 79 : le menu du jeu (Jouer, Nouvelle partie, Charger, Options, Aide, Quitter) : chiffre ou lettre.
    Les mots (dans les 14 langues) : accueil.action. None : pas pour le menu."""
    r = (reponse or "").strip().lower()
    return {"": "continuer", "1": "continuer", "2": "nouvelle", "3": "charger", "4": "options", "5": "aide",
            "q": "quitter", "0": "quitter"}.get(r)


# ================================================================ ce qui se passe après chaque commande
def apres_commande(state, ligne, ok, maintenant=None):
    """Compte les commandes réussies (la flèche), les erreurs de suite (le bouton « Perdu ? »), et repère le
    premier `ls` réussi. Renvoie « premier_ls » quand la cinématique doit se jouer, sinon None."""
    a = a_(state)
    a["derniere"] = maintenant or time.time()
    if ok:
        a["reussies"] = min(99, a["reussies"] + 1)
        a["erreurs"] = 0
    else:
        a["erreurs"] = min(99, a["erreurs"] + 1)
    mot = (core.first_word(ligne or "") or "").lower()
    if ok and mot in ("ls", "dir", "gci", "get-childitem") and not a["premier_ls"]:
        a["premier_ls"] = True
        return "premier_ls"
    return None


def tick(state, lignes, statuts=None):
    """Après les repas (app.boucle_jeu). statuts : le code de sortie de chaque ligne (None : inconnu = réussie)."""
    ev = None
    for k, l in enumerate(lignes):
        if core.est_colle(l) or not l.strip():
            continue
        s = statuts[k] if statuts else None
        e = apres_commande(state, l, s in (None, 0))
        ev = ev or e
    if ev == "premier_ls":
        state["_premier_ls"] = True
    proposer_fermer(state)
    return ev


# ================================================================ 1. parent à côté
def conseils_parents():
    """Les 4 conseils pour l'adulte à côté."""
    out = [f"  {fg(221)}{BOLD}🤝 " + t("ad.parent.titre_conseils") + RESET]
    for n in range(1, 5):
        out.append(f"  {fg(78)}▸ {BOLD}" + t(f"ad.parent.c{n}.t") + f"{RESET}{fg(78)} " + t(f"ad.parent.c{n}") + RESET)
    out.append(f"  {fg(78)}▸ " + t("ad.parent.debloquer", cmd="`tg debloquer tout`") + RESET)
    out.append(f"  {DIM}" + t("ad.parent.relire", cmd="`tg aide parents`") + RESET)
    return out


def demander_parent(demander):
    """« Qui est avec toi ? » (1 : je joue seul, 2 : un adulte est à côté) ; avec un adulte, les conseils, puis
    Entrée. Renvoie « seul » ou « adulte »."""
    print(f"\n  {fg(213)}{BOLD}Terminagotchi{RESET}")
    print(f"  {BOLD}" + t("ad.parent.question") + RESET)
    print(f"  {BOLD}1{RESET}  " + t("ad.parent.seul"))
    print(f"  {BOLD}2{RESET}  " + t("ad.parent.adulte"))
    print(f"  {DIM}" + t("ad.parent.note") + RESET)
    try:
        r = demander(f"  {DIM}>{RESET} ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        raise
    from .accueil import mots
    adulte = r == "2" or r in mots("ad.parent.mots_adulte")
    if adulte:
        print("")
        print("\n".join(conseils_parents()))
        demander(f"  {DIM}" + t("ad.parent.entree") + f"{RESET} ")
    return "adulte" if adulte else "seul"


# ================================================================ 2. le premier ls
def lignes_premier_ls(noms, dossiers, k=None):
    """Le dessin du premier ls, en blocs (k : le nombre de cases déjà dessinées ; None : toutes)."""
    noms = list(noms)[:4]
    k = len(noms) if k is None else k
    vert, clair = fg(84), fg(114)
    lignes = [f"   {fg(23)}░▒▓ {vert}▓▒░ {fg(221)}{BOLD}" + t("ad.ls.titre") + f"{RESET} {vert}░▒▓{RESET}"]
    haut, mil, bas, nom = "    ", "    ", "    ", "    "
    for i, n in enumerate(noms):
        larg = max(8, min(14, len(n) + 2))
        if i < k:
            motif = ("▀" if n in dossiers else "≡") * (larg - 4)
            haut += f"{vert}┌{'─' * (larg - 2)}┐{RESET} "
            mil += f"{vert}│{clair} {motif} {vert}│{RESET} "
            bas += f"{vert}└{'─' * (larg - 2)}┘{RESET} "
        elif i == k:
            bruit = "".join("░▒▓█"[(i * 7 + j * 3) % 4] for j in range(larg))
            haut += f"{fg(23)}{bruit}{RESET} "
            mil += f"{vert}{bruit[::-1]}{RESET} "
            bas += f"{fg(23)}{bruit}{RESET} "
        else:
            haut += " " * (larg + 1)
            mil += " " * (larg + 1)
            bas += " " * (larg + 1)
        coul = fg(75) if n in dossiers else ""
        nom += f"{coul}{n[:larg].center(larg)}{RESET} " if i < k else " " * (larg + 1)
    lignes += [haut, mil, bas, nom]
    nd = sum(1 for n in noms if n in dossiers)
    lignes.append(f"    {DIM}" + t("ad.ls.compte", lieux=nd, objets=len(noms) - nd) + RESET)
    return lignes


def jouer_premier_ls(flux, state, ici, court=False):
    """Joue la cinématique du premier ls dans le terminal (2 à 3 s ; une touche tapée la passe)."""
    import os
    import select
    import sys
    try:
        noms = sorted(n for n in os.listdir(ici or ".") if not n.startswith("."))
        dossiers = {n for n in noms if os.path.isdir(os.path.join(ici or ".", n))}
    except OSError:
        noms, dossiers = [], set()
    noms = (sorted(dossiers) + [n for n in noms if n not in dossiers])[:4]
    duree = duree_ls(court)
    etapes = max(1, len(noms))
    tty = getattr(flux, "isatty", lambda: False)()
    if tty and noms:
        hauteur = 0
        for k in range(etapes + 1):
            if hauteur:
                flux.write(f"\x1b[{hauteur}A\r\x1b[J")
            l = lignes_premier_ls(noms, dossiers, k)
            flux.write("\n".join(l) + "\n")
            flux.flush()
            hauteur = len(l)
            try:
                if select.select([sys.stdin], [], [], duree / (etapes + 1))[0]:
                    break
            except (OSError, ValueError):
                time.sleep(duree / (etapes + 1))
        flux.write(f"\x1b[{hauteur}A\r\x1b[J")
    if noms:
        flux.write("\n".join(lignes_premier_ls(noms, dossiers)) + "\n")
    flux.write(f"{fg(208)}(•ᴗ•){RESET} {BOLD}{state.get('name', '')}{RESET} {fg(78)}" + t("ad.ls.waouh") + RESET + "\n")
    flux.flush()


# ================================================================ 4 et 5. la flèche, le clavier
def ligne_fleche(state, maintenant=None):
    """La ligne « ▼ tape ta commande ici… » au-dessus de l'invite (PC), ou None."""
    from . import intro
    a = a_(state)
    depuis = (maintenant or time.time()) - (a["derniere"] or 0)
    if not fleche(intro.en_cours(state), a["reussies"], depuis):
        return None
    return f"        {fg(84)}{BOLD}▼ {RESET}{fg(78)}" + t("ad.fleche.pc") + RESET


def attente_fleche(state, maintenant=None):
    """Pendant l'œuf, quand la flèche est partie (3 commandes réussies) : dans combien de secondes elle revient si
    l'enfant ne tape plus rien (0 : maintenant). None : pas d'œuf, ou la flèche est déjà là (elle est dans l'invite)."""
    from . import intro
    a = a_(state)
    if not intro.en_cours(state) or a["reussies"] < SEUIL_FLECHE:
        return None
    return max(0.0, (a["derniere"] or 0) + RETOUR_FLECHE - (maintenant or time.time()))


def place_fleche(state):
    """La ligne vide gardée au-dessus de l'invite (PC, vrai shell) : la flèche peut y revenir pendant que l'enfant
    attend devant l'invite, sans attendre la commande suivante (guet_fleche). Seulement pendant l'œuf."""
    return attente_fleche(state) is not None


def lancer_guet(state):
    """Vrai shell (bash, zsh, fish ; pas Windows ni le terminal du jeu, qui le font eux-mêmes) : un petit processus à
    part attend la minute sans rien taper, puis remet la flèche à sa place au-dessus de l'invite (tg prompt-fleche).
    Il s'en va tout seul dès qu'une autre commande arrive."""
    import os
    import subprocess
    import sys
    if os.name == "nt" or os.environ.get("TG_DANS_LE_JEU") or os.environ.get("TG_SANS_GUET"):
        return False
    if attente_fleche(state) is None:
        return False
    try:
        if not sys.stdout.isatty():
            return False
        shell = os.getppid()
        from . import compagnon
        exe, app = compagnon.commande()
        subprocess.Popen([exe, app, "prompt-fleche", str(shell)], stdin=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)       # stdout : le terminal
        return True
    except (OSError, ValueError):
        return False


def guet_fleche(shell_pid, dormir=time.sleep, flux=None):
    """Le petit processus de lancer_guet : attend que la minute passe ; si aucune commande n'est arrivée (la sauvegarde
    n'a pas bougé) et que le shell attend bien à l'invite (pas `nano` ou `less` au premier plan), il écrit la flèche sur
    la ligne gardée juste au-dessus de l'invite, sans toucher à ce que l'enfant est en train de taper."""
    import os
    import sys
    flux = flux or sys.stdout
    f = core.SAVE_DIR / "save.json"
    try:
        avant = f.stat().st_mtime_ns
    except OSError:
        return False
    for _ in range(int(RETOUR_FLECHE / 2) + 5):
        try:
            if f.stat().st_mtime_ns != avant:         # une commande (ou une autre invite) : un autre guet a pris le relais
                return False
        except OSError:
            return False
        st = core.load()
        if st is None:
            return False
        reste = attente_fleche(st)
        if reste is None:
            return False
        if reste <= 0:
            break
        dormir(min(2.0, reste))
    else:
        return False
    ligne = ligne_fleche(st)
    if not ligne:
        return False
    try:
        if flux is sys.stdout:
            fd = sys.stdout.fileno()
            if not os.isatty(fd) or os.tcgetpgrp(fd) != os.getpgid(int(shell_pid)):
                return False                      # un programme plein écran est au premier plan : on ne l'abîme pas
        # le curseur est sur la ligne de l'invite : on écrit sur la ligne gardée juste au-dessus, puis on revient
        flux.write("\0337\033[1A\r" + ligne + "\033[K" + RESET + "\0338")
        flux.flush()
        return True
    except (OSError, ValueError):
        return False


def disposition(state):
    d = (state.get("config") or {}).get("clavier")
    if d in CLAVIER:
        return d
    from . import langue
    return "azerty" if langue.courante() == "fr" else "qwerty"


def texte_touches(disp, sym):
    noms = {"Maj": t("ad.clav.maj"), "AltGr": "AltGr", "+Espace": t("ad.clav.puis_espace")}
    out = []
    for x in CLAVIER[disp].get(sym, []):
        if x == "+Espace":
            out[-1] = out[-1] + " " + noms[x]
        else:
            out.append(noms.get(x, x))
    return " + ".join(out)


def astuce_clavier(state, attendu):
    """La 1re fois qu'un symbole arrive dans une leçon : où il est sur le clavier (lignes), sinon []."""
    a = a_(state)
    s = symbole_nouveau(attendu, a["symboles"])
    if not s:
        return []
    a["symboles"].append(s)
    disp = disposition(state)
    nom = t("ad.clav.nom." + {">>": "ajoute", "|": "tuyau", "~": "tilde", ">": "fleche", "*": "etoile", "/": "barre",
                              "$": "dollar", "&": "et", "\"": "guillemet", "'": "apostrophe", "_": "souligne"}[s])
    return [f"  {fg(221)}{BOLD}" + t("ad.clav.nouveau", sym=s, nom=nom) + RESET,
            "     " + t("ad.clav.ou." + disp, touches=f"{fg(221)}{BOLD}{texte_touches(disp, s)}{RESET}"),
            f"     {DIM}" + t("ad.clav.regler", cmd="`tg clavier azerty`", cmd2="`tg clavier qwerty`") + RESET]


def commande_clavier(args):
    """tg clavier [azerty|qwerty] : la disposition dont parle la créature."""
    choix = (args[0].lower() if args else "")
    if choix in CLAVIER:
        core.modifier(lambda s: s["config"].__setitem__("clavier", choix))
    st = core.load() or {"config": {}}
    return t("ad.clav.actuel", disp=disposition(st).upper(), cmd="`tg clavier azerty`", cmd2="`tg clavier qwerty`")


# ================================================================ 6. perdu
def infos_perdu(state, cwd=None):
    """(où es-tu, ta leçon, quoi taper) pour la carte « Pas de panique » : les mêmes renseignements que `aide`."""
    from . import compagnon, histoire, intro, lecons, maison
    from pathlib import Path
    ici = cwd or maison.ici(state)
    r = maison.rel(ici) if ici else None
    if r is not None:
        ou = histoire.nom_lieu(r) + "  (" + str(ici).replace(str(Path.home()), "~", 1) + ")"
    else:
        ou = str(ici).replace(str(Path.home()), "~", 1) if ici else "?"
    if intro.en_cours(state):
        p = intro.prochaine(state)
        lecon = intro.titre_liste(state)
        tape = f"`{intro.commande_de(p)}`" if p else ""
        return ou, lecon, tape
    les, _ = lecons.lecon_courante(state)
    if not les or core.level(state.get("xp", 0)) < les["niveau"]:
        return ou, t("aide.lecon.aucune"), ""
    step = les["steps"][state["step"]]
    lecon = t("ad.perdu.lecon", titre=lecons.tx(les["titre"]), n=state["step"] + 1, total=len(les["steps"])) \
        + " · " + lecons.tx(step["dit"])
    from . import placement
    placement.montrer(state, step)
    return ou, lecon, compagnon.commande_montree(state, step, ici)


def lignes_perdu(state, cwd=None):
    ou, lecon, tape = infos_perdu(state, cwd)
    b = BOLD
    out = [f" {fg(221)}{BOLD}🧭 " + t("ad.perdu.titre") + RESET,
           f"  {b}1 " + t("ad.perdu.ou") + f"{RESET}  {fg(189)}{ou}{RESET}",
           f"  {b}2 " + t("ad.perdu.lecon_titre") + f"{RESET}  {fg(213)}{lecon}{RESET}"]
    if tape:
        out.append(f"  {b}3 " + t("ad.perdu.tape") + f"{RESET}  {fg(78)}{tape}{RESET}")
    out.append(f"  {DIM}" + t("ad.perdu.rien", cmd="`cd ~`") + RESET)
    return out


# ================================================================ 9. fermer et revenir
def proposer_fermer(state):
    """À la fin du tronc commun (une fois) : l'écran « Tu peux fermer quand tu veux » attend son tour."""
    a = a_(state)
    if a["fermer"]:
        return
    from . import histoire, intro, programme
    try:
        if not intro.eclos(state) or not tronc_fini(histoire.h_(state)["ailes"], programme.donnees().get("tronc")):
            return
    except Exception:                                   # noqa: BLE001
        return
    a["fermer"] = "file"
    d = intro.d_(state)
    if "fermer" not in d["file"]:
        d["file"].append("fermer")


def marquer_fermer(state, pid=None):
    """L'écran « fermer et revenir » vient d'être montré : au prochain terminal (un autre shell que celui-ci), ou à
    la prochaine ouverture de l'appli, la créature dira « Te revoilà ! »."""
    import os
    a = a_(state)
    a["fermer"] = "attend"
    a["fermer_pid"] = os.getppid() if pid is None else pid


def retour(state, pid=None):
    """Au retour (un nouveau terminal, l'appli rouverte) : « Te revoilà ! », une fois. Renvoie le texte ou None."""
    a = a_(state)
    if a["fermer"] != "attend":
        return None
    if pid is not None and a.get("fermer_pid") == pid:
        return None
    a["fermer"] = "fait"
    return t("ad.fermer.retour")


# ================================================================ 22. ls ?
def image_de(nom):
    from . import lexique
    for _titre, _u, commandes in lexique._entrees():
        for c, image, technique in commandes:
            if c.split()[0].lower() == nom:
                return c, image, technique
    return None


def fiche_courte(state, nom, pc=True):
    """La petite fiche de `ls ?` : l'image, un exemple, une option, la ligne des grands, le joker, toute la fiche."""
    from . import exemples, explique
    e = image_de(nom)
    opts = explique.OPTIONS.get(nom, {})
    if not e and not opts:
        return [t("explique.inconnue", cmd=nom, ex="tg explique rm")]
    out = [f" {fg(213)}{BOLD}📖 " + t("ad.q.titre", cmd=nom) + RESET]
    if e:
        out.append("  " + e[1])
    ex = exemples.lexique(e[0] if e else nom)
    opt = next(iter(opts.items()), None)
    if ex:
        out.append(f"  {DIM}" + t("ad.q.essaie", ex=f"`{ex}`") + RESET)
    if opt:
        out.append(f"  {DIM}(`{opt[0]}` : " + t("opt." + opt[1]) + f"){RESET}")
    g = explique.grand_commande(nom, e[2] if e else None)
    if g:
        out.append(f"  {DIM}🧑 {g}{RESET}")
    out.append(f"  {DIM}🧑 " + t("ad.q.joker", aide=f"`{nom} --help`", man=f"`man {nom}`") + RESET)
    out.append(f"  {DIM}" + t("ad.q.tout", cmd=f"`{'tg ' if pc else ''}explique {nom}`") + RESET)
    return out


# ================================================================ 25. trois niveaux d'indice
def cible(state):
    """(clé, commande attendue, d'où) de ce qui se cherche en ce moment sans que la commande soit donnée, ou None."""
    from . import dressage, entrainement, lecons, placement
    d = state.get("dressage")
    if d:
        try:
            x = dressage.tache_courante(state)
            if x is not None:
                fid = next(f for f in d["taches"] if dressage._par_id(f) is x)
                from . import mots
                _e, ex = dressage.aide(fid, d["espece"], mots.palier(state))
                if ex:
                    return f"dress:{d['espece']}:{fid}", re.sub(r"\s{2,}", "  ", ex.strip()), "dressage"
        except Exception:                               # noqa: BLE001
            pass
    e = (state.get("entrainement") or {}).get("cours")
    if isinstance(e, dict) and e.get("type") in entrainement.TYPES:
        p, _ = entrainement.generer(e["type"], e["v"], e["n"])
        idees = entrainement.idees(e["type"], p)
        if idees:
            return f"ent:{e.get('g')}:{e.get('n')}", "  ".join(idees), "exercice"
    try:                                                # le Sommet : une réponse à trou (sommet dates ?, -k ?…)
        from . import sommet
        x = sommet.cible_indice(state)
        if x:
            return x
    except Exception:                                   # noqa: BLE001
        pass
    les, _ = lecons.lecon_courante(state)
    if les and core.level(state.get("xp", 0)) >= les["niveau"]:
        step = les["steps"][state["step"]]
        if placement.cache(state, step):
            return f"lecon:{les['id']}:{state['step']}", step["cmd"], "lecon"
    return None


def textes_indice(attendu, n):
    """Le texte du niveau n (1 à 3) pour une commande attendue."""
    p = parties_indice(attendu.split("  ")[0])
    if n == 1:
        e = image_de(p["cmd"].lower())
        return t("ad.ind.n1", image=e[1]) if e else t("ad.ind.n1_sans", n=len(p["cmd"]))
    if n == 2:
        return t("ad.ind.n2", cmd=f"`{p['debut']}`")
    return t("ad.ind.n3", cmd="  ".join(f"`{x}`" for x in attendu.split("  ")))


def demander_indice(state):
    """`indice` : le niveau suivant (1, 2 puis 3) pour ce qu'on cherche. Renvoie (n, titre, texte) ou None."""
    c = cible(state)
    if not c:
        return None
    cle, attendu, quoi = c
    a = a_(state)
    i = a.get("indice") if isinstance(a.get("indice"), dict) else {}
    n = min(3, i.get("n", 0) + 1) if i.get("cle") == cle else 1
    a["indice"] = {"cle": cle, "n": n}
    if n == 3:
        reponse_vue(state, quoi)
    if quoi.startswith("sommet:"):                      # le Sommet : ses propres coups de pouce, puis la réponse
        from . import sommet
        return n, t(f"ad.ind.t{n}"), sommet.texte_indice(quoi.split(":", 1)[1], n, attendu)
    return n, t(f"ad.ind.t{n}"), textes_indice(attendu, n)


def reponse_vue(state, quoi):
    """La réponse a été montrée : la commande d'une leçon sans aide devient visible, et l'exploit « sans indice » de
    ce palier de la Forge n'est pas donné cette fois (rien d'autre n'est retiré)."""
    from . import lecons, placement
    les, _ = lecons.lecon_courante(state)
    if not les:
        return
    if quoi == "lecon":
        placement.montrer(state, les["steps"][state["step"]])
    from . import forge
    if les["id"] in getattr(forge, "SANS_INDICE", ()):
        c = forge.f_(state)
        if f"indice:{les['id']}" not in c["faits"]:
            c["faits"].append(f"indice:{les['id']}")


def lignes_indice(state):
    r = demander_indice(state)
    if not r:
        return [f" {DIM}💡 " + t("ad.ind.rien") + RESET]
    n, titre, texte = r
    coul = {1: 221, 2: 215, 3: 78}[n]
    out = [f" {fg(coul)}{BOLD}" + "💡" * n + " " + titre + f" ({n}/3){RESET}", "   " + texte]
    out.append(f"   {DIM}" + (t("ad.ind.encore", cmd="`indice`") if n < 3 else t("ad.ind.rien_retire")) + RESET)
    return out


def fantome_permis(state):
    """Idée 66 : pas de fin grisée pendant un exercice, une épreuve ou un défi sans aide (pour ne pas souffler)."""
    try:
        return cible(state) is None
    except Exception:                                   # noqa: BLE001
        return True
