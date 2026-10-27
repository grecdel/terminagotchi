"""L'introduction du jeu et le déblocage progressif (même règles sur Android : Intro.kt).

Nouvelle partie (une vraie personne au clavier) :
  1. quelques écrans (scènes en pixels) : le Terminaworld s'est endormi, seules les commandes tapées dans
     l'invite de commande peuvent le réveiller ; Entrée = suite, p = passer, ou tape directement le nom de l'œuf ;
  2. l'œuf seul, l'invite et une petite liste de 4 commandes (pwd, ls, echo, whoami) ; chaque bonne commande
     fait réagir l'œuf (il remue, brille, se fêle : 3 fêlures) ; un petit tutoriel de l'invite arrive pas à pas
     (où taper et Entrée, une erreur n'est pas grave, ↑ rappelle, Tab complète) ;
  3. la 4e commande : l'œuf éclot, la créature dit merci, explique ce qu'on vient de faire (les vraies
     commandes), où on est (le camp de base, ce que pwd a montré) et la suite (le chapitre 1) ;
  4. le reste du jeu s'ouvre petit à petit (table « deblocages » de intro.json, la même pour Android) : chaque
     fonction est présentée par la créature en un écran au moment où elle s'ouvre. Avant, ses commandes
     répondent gentiment « pas encore » (jamais une erreur).

Données : intro.json (copie exacte de donnees/intro.json, comme app/src/main/assets/intro.json).
Sauvegarde : state["intro"] = {etat: "oeuf" | "fini", faits: [ids], evt, erreur}, state["debloc"] =
{mode: "progressif" | "ancien", ouverts, presentes, file (les écrans à montrer : merci, merci2, puis les fonctions)}.
Une ancienne partie (sans « debloc ») : tout reste ouvert (mode « ancien »), rien n'est présenté (pas d'écran
« nouveau » pour ce qu'un joueur connaît déjà) ; ses fonctions sont notées au fur et à mesure.
`tg debloquer tout` (pour les parents et les tests) ouvre tout d'un coup, après confirmation.
Tests : pc/outils/test_intro.py.
"""
import json
import pkgutil
import re
import time

from . import core
from .langue import envelopper, largeur, t
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg

_D = {}


def donnees():
    if not _D:
        _D.update(json.loads(pkgutil.get_data(__package__, "intro.json").decode("utf-8")))
    return _D


def deblocages():
    return donnees()["deblocages"]


def par_id():
    return {f["id"]: f for f in deblocages()}


def checklist():
    return donnees()["checklist"]


def fonction_de(cmd):
    """La fonction du jeu à laquelle appartient une commande (« carte » → « carte »), ou None."""
    c = (cmd or "").lower()
    for f in deblocages():
        if c in f["commandes"]:
            return f["id"]
    return None


# ---------------------------------------------------------------- l'état
def i_(state):
    """L'état de l'intro. Une ancienne partie n'en a pas : l'intro est finie depuis longtemps."""
    i = state.get("intro")
    if not isinstance(i, dict):
        i = state["intro"] = {"etat": "fini"}
    for k, v in {"etat": "fini", "faits": [], "evt": None, "erreur": False}.items():
        i.setdefault(k, v)
    return i


def d_(state):
    """L'état du déblocage. Sans « debloc » (partie d'avant) : tout est ouvert et rien n'est présenté."""
    d = state.get("debloc")
    if not isinstance(d, dict):
        d = state["debloc"] = {"mode": "ancien", "ouverts": [f["id"] for f in deblocages()], "presentes": [], "file": []}
        for f in deblocages():
            if condition(state, f["quand"]):
                d["presentes"].append(f["id"])
    for k, v in {"mode": "ancien", "ouverts": [], "presentes": [], "file": []}.items():
        d.setdefault(k, v)
    return d


def nouvelle_partie(state):
    """Une nouvelle partie avec l'intro : l'œuf, la liste de commandes, tout le reste fermé."""
    state["intro"] = {"etat": "oeuf", "faits": [], "evt": None, "erreur": False}
    state["debloc"] = {"mode": "progressif", "ouverts": [], "presentes": [], "file": []}
    return state


def retient(state):
    """Vrai pendant que l'œuf attend ses commandes : il n'éclot pas avant la fin de la liste (l'XP s'arrête à 9)."""
    i = state.get("intro")
    return isinstance(i, dict) and i.get("etat") == "oeuf"


def en_cours(state):
    return retient(state)


def eclos(state):
    return i_(state)["etat"] == "fini"


def ouvert(state, fid):
    d = d_(state)
    return d["mode"] != "progressif" or fid in d["ouverts"]


def bloque(state, cmd):
    """Le message gentil si la commande appartient à une fonction pas encore ouverte, sinon None."""
    if state is None:
        return None
    fid = fonction_de(cmd)
    if fid and not ouvert(state, fid):
        return t("deb.pas_encore", cmd=cmd)
    return None


def condition(state, q):
    """Toutes les conditions de « quand » sont vraies."""
    from . import histoire
    if q.get("eclos") and not eclos(state):
        return False
    if core.level(state.get("xp", 0)) < q.get("niveau", 0):
        return False
    if q.get("lecons") or q.get("chapitres") or q.get("ailes"):
        h = histoire.h_(state)
        if any(x not in h["faits"] for x in q.get("lecons", [])):
            return False
        if any(x not in h["ailes"] for x in q.get("chapitres", [])):
            return False
        if histoire.nb_ailes(state) < q.get("ailes", 0):
            return False
    if len(state.get("captures", [])) < q.get("captures", 0):
        return False
    return all(ouvert(state, x) for x in q.get("apres", []))


def verifier(state):
    """Ouvre (et met en file pour être présentée) chaque fonction dont la condition est maintenant vraie."""
    d = d_(state)
    for f in deblocages():
        fid = f["id"]
        if fid in d["presentes"] or not condition(state, f["quand"]):
            continue
        d["presentes"].append(fid)
        if fid not in d["ouverts"]:
            d["ouverts"].append(fid)
        if fid == "histoire" or d["mode"] != "progressif":
            continue                             # l'histoire : l'écran « merci » la présente ; une ancienne partie : rien

        d["file"].append(fid)
        core.log(state, t("deb.nouveau.log", nom=f["emoji"] + " " + t(f"deb.{fid}.titre")))
        core.say(state, t("deb.nouveau.dit", nom=t(f"deb.{fid}.titre")), 10)
        core.animer(state, "content")


def tout_debloquer(state):
    """`tg debloquer tout` : toutes les fonctions ouvertes d'un coup, l'œuf éclos (pour les parents et les tests)."""
    if retient(state):
        finir(state)
    d = d_(state)
    for f in deblocages():
        if f["id"] not in d["ouverts"]:
            d["ouverts"].append(f["id"])
        if f["id"] not in d["presentes"]:
            d["presentes"].append(f["id"])
    d["file"] = [x for x in d["file"] if x in ("merci", "merci2")]
    d["mode"] = "tout"


# ---------------------------------------------------------------- la liste de commandes de l'œuf
def tick(state, lignes):
    """Après les repas (core.feed) : chaque commande de la liste fait réagir l'œuf ; la dernière le fait éclore.
    Renvoie les lignes que le reste du jeu doit voir : toutes hors de l'intro, aucune pendant (l'œuf seul), celles
    d'après l'éclosion si elle arrive maintenant (les commandes de l'œuf ne valident pas déjà la leçon 1)."""
    if not retient(state):
        return lignes
    i = i_(state)
    for k, l in enumerate(lignes):
        if core.est_colle(l):
            continue
        cmd = core.first_word(l)
        if not cmd:
            continue
        # G-34 : `pwd; ls` compte pour les deux ; `PWD` (majuscules) ou une commande qui a échoué ne compte pas
        from . import verif
        trouves = []
        for m in verif.morceaux(l, None, core.statut_de(lignes, k)):
            if m.statut not in (None, 0) or not verif.casse_ok(verif.premier(m.texte)):
                continue
            c = next((c for c in checklist() if c["id"] not in i["faits"] and c not in trouves
                      and re.search(c["re"], m.texte.strip(), re.I)), None)
            if c is not None:
                trouves.append(c)
        if not trouves:
            if not core.commande_existe(cmd) and not cmd.startswith(("./", "/")) or core.statut_de(lignes, k):
                i["erreur"] = True                 # une erreur : le petit tutoriel dit que ce n'est pas grave
            continue
        for c in trouves:
            i["faits"].append(c["id"])
            n = len(i["faits"])
            i["evt"] = [n, time.time()]
            if n >= len(checklist()):
                finir(state)
                return list(lignes[k + 1:])
            state["anim"] = [f"oeuf_{n}", time.time()]
            core.say(state, t(f"intro.reagit.{n}"), 8)
        core.log(state, f"🥚 ✔ {l.strip()}")
    return []


def finir(state):
    """L'œuf éclot : la créature naît (niveau 2), l'histoire s'ouvre, l'écran « merci » attend."""
    i = i_(state)
    i["etat"] = "fini"
    i["evt"] = [len(checklist()), time.time()]
    state["bulles"] = []                     # les réactions de l'œuf en attente : l'éclosion passe avant
    state["bubble"] = None
    core.add_xp(state, max(0, 10 - state["xp"]))
    state["anim"] = ["eclosion", time.time()]
    d = d_(state)
    for x in ("merci", "merci2"):
        if x not in d["file"]:
            d["file"].insert(len([y for y in d["file"] if y in ("merci", "merci2")]), x)
    verifier(state)


def prochaine(state):
    i = i_(state)
    return next((c for c in checklist() if c["id"] not in i["faits"]), None)


def astuce(state):
    """Le petit tutoriel de l'invite, une chose à la fois : Entrée, l'erreur, ↑, Tab."""
    i = i_(state)
    if i.get("erreur") and len(i["faits"]) < 2:
        return t("intro.astuce.erreur")
    return t(f"intro.astuce.{min(len(i['faits']), 3)}")


def lignes_liste(state, couleur=True):
    """La petite liste : ✔ fait, ➜ la prochaine, · les autres (les commandes en vert)."""
    i = i_(state)
    p = prochaine(state)
    out = []
    for c in checklist():
        fait = c["id"] in i["faits"]
        signe = "✔" if fait else "➜" if p and c["id"] == p["id"] else "·"
        texte = t(f"intro.l.{c['id']}")
        if couleur:
            col = fg(78) if fait else fg(226) if signe == "➜" else DIM
            out.append(f"  {col}{signe}{RESET} {texte}")
        else:
            out.append(f"  {signe} {texte}")
    return out


# ---------------------------------------------------------------- les écrans (merci, fonctions)
def a_montrer(state):
    """L'écran « Nouveau : … » à montrer, ou None. P2-6 : pas en pleine étape de leçon (il attend qu'elle soit réussie),
    sauf l'écran « merci » de l'éclosion."""
    d = d_(state)
    if not d["file"]:
        return None
    if d["file"][0] not in ("merci", "merci2"):
        from . import histoire
        if histoire.en_pleine_etape(state):
            return None
    return d["file"][0]


def lu(state):
    """L'écran du dessus de la file a été lu."""
    d = d_(state)
    if d["file"]:
        d["file"].pop(0)


def cmds(fid, tel=False):
    f = par_id().get(fid, {})
    c = list(f.get("cmd_tel" if tel else "cmd_pc", [])) + ["", ""]
    return {"cmd": c[0], "cmd2": c[1]}


def contenu(state, cid, chemin=None, tel=False):
    """(titre, [paragraphes]) d'un écran : merci, merci2, ou une fonction qui s'ouvre."""
    nom = state.get("name", "")
    if cid == "merci":
        return t("intro.merci.titre", nom=nom), [t("intro.merci", nom=nom), t("intro.recap")] + \
            [t(f"intro.r.{c['id']}") for c in checklist()]
    if cid == "merci2":
        from pathlib import Path
        return t("intro.ici.titre"), [t("intro.ici", chemin=chemin or str(Path.home())),
                                      t("intro.suite", chapitre=t("hist.reveil.titre"))]
    f = par_id()[cid]
    return f["emoji"] + " " + t("deb.nouveau", nom=t(f"deb.{cid}.titre")), [t(f"deb.{cid}.texte", **cmds(cid, tel))]


def lignes_ecran(state, cid, largeur_max=64, chemin=None):
    """Un écran de présentation encadré, la créature (ou son guide) à gauche du titre."""
    titre, paras = contenu(state, cid, chemin)
    from . import sprites
    dessin, w = sprites.creature(state)
    out = [""]
    tete = envelopper(titre, largeur_max - w - 4)
    for k in range(max(len(dessin), len(tete))):
        g = dessin[k] if k < len(dessin) else " " * w
        d = tete[k] if k < len(tete) else ""
        out.append("  " + g + "  " + f"{BOLD}{fg(213)}{d}{RESET}")
    out.append(" " + fg(244) + "─" * (largeur_max + 2) + RESET)
    for p in paras:
        for x in envelopper(p, largeur_max):
            out.append("  " + x)
        out.append("")
    out.append(f" {DIM}" + t("intro.ok.pc") + RESET)
    return out


# ---------------------------------------------------------------- dessins en pixels (mêmes dessins qu'Android)
def _demi_blocs(rows, pal, fond=None):
    """Lignes de caractères → demi-blocs en couleurs 24 bits (2 pixels verticaux par caractère)."""
    from .bestiaire import bg24, fg24
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows] + (["." * w] if len(rows) % 2 else [])
    out = []
    for y in range(0, len(rows), 2):
        s = ""
        for a, b in zip(rows[y], rows[y + 1]):
            ca, cb = pal.get(a, fond), pal.get(b, fond)
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += fg24(ca) + "▀" + RESET
            elif ca is None:
                s += fg24(cb) + "▄" + RESET
            else:
                s += fg24(ca) + bg24(cb) + "▀" + RESET
        out.append(s)
    return out


def scene(nom):
    return _demi_blocs(donnees()["scenes"][nom], donnees()["palette"], donnees()["palette"]["k"])


def ecran_intro(n, total=None):
    """Un écran de l'intro : la scène, le titre, le texte (PC)."""
    e = donnees()["ecrans"][n - 1]
    total = total or len(donnees()["ecrans"])
    out = [""] + ["   " + l for l in scene(e["scene"])] + [""]
    out.append(f"   {BOLD}{fg(213)}" + t(f"intro.e.titre.{n}") + RESET + f"  {DIM}{n}/{total}{RESET}")
    for x in envelopper(t(f"intro.e.texte.{n}"), 60):
        out.append("   " + x)
    out.append("")
    return out


W_OEUF, H_OEUF = 26, 26                 # le cadre de l'œuf de l'intro (oeufs.json, taille « grand »)


def image_oeuf(fele, nom="", k=0, ty="feu"):
    """Une image de l'œuf de type ty (26×26 pixels, lignes de caractères) : fele = nombre de fêlures (0 à 3 :
    intact, une fêlure qui luit, le dessin fissuré, une grande fêlure) ; nom = « remue » (il penche), « brille »
    (son contour luit, des étincelles), « craque » (la fêlure éclaire), « eclot » (il tremble puis s'ouvre ; None à
    la fin : la créature prend la place). Les dessins : oeufs.py. Même calcul qu'Intro.kt / Oeufs.kt."""
    from . import oeufs
    return oeufs.image(ty, fele, nom, k)


def reaction(n):
    """Les images d'une réaction de l'œuf à la n-ième bonne commande : [(fêlures, nom, k)]."""
    if n == 1:
        seq = [(0, "remue", k) for k in range(8)] + [(1, "craque", k) for k in range(4)]
    elif n == 2:
        seq = [(1, "brille", k) for k in range(6)] + [(2, "craque", k) for k in range(4)]
    elif n == 3:
        seq = [(2, "remue", k) for k in range(4)] + [(2, "brille", k) for k in range(4)] + [(3, "craque", k) for k in range(4)]
    else:
        seq = [(3, "eclot", k) for k in range(8)]
    return seq


def lignes_oeuf(fele, nom="", k=0, state=None):
    """L'œuf en demi-blocs ; à la fin de l'éclosion, la créature (si state est donné)."""
    from . import oeufs
    ty = oeufs.type_de(state or {})
    rows = image_oeuf(fele, nom, k, ty)
    if rows is None:
        if state is not None:
            from . import sprites
            return sprites.render_sprite(sprites.get_sprite(state, 1), sprites.palette(state))[0]
        rows = image_oeuf(3, ty=ty)
    return _demi_blocs(rows, oeufs.palette(ty))


def animation(nom, state):
    """(images, ips) d'une animation de l'intro (« oeuf_1 » à « oeuf_3 », « eclosion ») pour la fenêtre."""
    n = 4 if nom == "eclosion" else int(nom.split("_")[1])
    return [lignes_oeuf(f, x, k, state) for f, x, k in reaction(n)], 6


def lignes_ecran_oeuf(state, frame=0, image=None):
    """L'écran de l'œuf (fenêtre PC) : l'œuf (ou image : une image de son animation), son nom, la liste,
    l'astuce du moment, où taper."""
    i = i_(state)
    fele = min(3, len(i["faits"]))
    oeuf = list(image) if image else lignes_oeuf(fele, "remue" if frame % 6 == 0 and fele else "", 1, state)
    droite = [f"{BOLD}{state['name']}{RESET} · 🥚 " + t("intro.oeuf.titre"),
              f"{DIM}" + t("app.caractere", trait=core.nom_trait(state["trait"])) + RESET]
    from . import oeufs
    droite += [f"{fg(214)}{x}{RESET}" for x in envelopper(t("intro.type." + oeufs.type_de(state)), 40)] + [""]
    b = core.bulle_courante(state)
    if b:
        droite += [f"{BOLD}» {x}{RESET}" for x in envelopper(b[0], 40)]
    out = []
    for k in range(max(len(oeuf), len(droite))):
        g = oeuf[k] if k < len(oeuf) else " " * W_OEUF
        g += " " * max(0, W_OEUF - largeur(g))
        out.append("  " + g + "   " + (droite[k] if k < len(droite) else ""))
    out.append("")
    titre = t("intro.liste.titre", n=len(i["faits"]), total=len(checklist()))
    out.append(fg(226) + "── 🥚 " + titre + " " + "─" * max(3, 44 - largeur(titre)) + RESET)
    out += lignes_liste(state)
    out.append("")
    for x in envelopper("💡 " + astuce(state), 74):
        out.append(f"  {fg(214)}{x}{RESET}")
    for x in envelopper(t("intro.ou.pc"), 74):
        out.append(f"  {DIM}{x}{RESET}")
    return out


def lignes_prompt(state):
    """Dans l'invite du shell, juste après une bonne commande : le petit œuf qui réagit et la liste."""
    i = i_(state)
    fele = min(3, len(i["faits"]))
    oeuf = lignes_oeuf(fele, "brille" if fele else "", 0, state)
    while oeuf and not oeuf[0].strip():          # le haut du cadre (la place de l'éclosion) : rien à montrer ici
        oeuf.pop(0)
    liste = lignes_liste(state)
    out = []
    for k in range(max(len(oeuf), len(liste))):
        out.append((oeuf[k] if k < len(oeuf) else " " * W_OEUF) + "  " + (liste[k] if k < len(liste) else ""))
    return out


def commande_de(c):
    """La commande à taper d'une ligne de la liste (le passage `…` de son texte : `echo bonjour`…)."""
    m = re.search(r"`([^`]+)`", t(f"intro.l.{c['id']}"))
    return m.group(1) if m else c["id"]


def pour_prompt(state):
    """Ce que l'invite du shell montre au-dessus de sa ligne, une seule fois : la liste au début, l'œuf qui
    réagit après une bonne commande, puis chaque écran à présenter (merci, nouveautés). Marque ce qui est montré."""
    i = i_(state)
    evt = i.get("evt")
    if retient(state) and not i.get("liste_vue"):
        i["liste_vue"] = True
        from . import oeufs
        return [""] + lignes_prompt(state) + ["  " + fg(214) + t("intro.type." + oeufs.type_de(state)) + RESET,
                                              "  " + DIM + t("intro.ou.pc") + RESET]
    if evt and i.get("vu_prompt") != evt[1]:
        i["vu_prompt"] = evt[1]
        if retient(state):
            return [""] + lignes_prompt(state)
    cid = a_montrer(state)
    if cid and not retient(state):
        lignes = lignes_ecran(state, cid)[:-1]
        lu(state)
        return lignes
    return []


# ---------------------------------------------------------------- les écrans du début (PC)
MOTS_PASSER = ("p", "passer", "skip", "q")


def jouer_ecrans(demander, effacer=None):
    """Montre les écrans de l'intro, puis demande le nom de l'œuf (avec confirmation). Un mot tapé sur un écran ne
    devient JAMAIS le nom (« Je m'appelle jouer », simulation de Tom) : il fait juste passer à l'écran suivant."""
    n = len(donnees()["ecrans"])
    for k in range(1, n + 1):
        if effacer:
            effacer()
        print("\n".join(ecran_intro(k, n)))
        r = demander(f"   {DIM}" + t("intro.touches.pc2") + f"{RESET} ").strip()
        if r.lower() in MOTS_PASSER:
            break
    return demander_nom(demander)


def nom_propre(nom):
    """Le nom de l'œuf, sans caractères de contrôle (séquences d'échappement, retournement du texte), 16 au plus."""
    import unicodedata
    return "".join(c for c in (nom or "") if unicodedata.category(c) not in ("Cc", "Cf")).strip()[:16]


def demander_nom(demander):
    """« Comment veux-tu appeler ton œuf ? » puis « Ton œuf s'appellera « X ». C'est bien ça ? » (Entrée = oui, un
    autre mot = ce nom-là à la place)."""
    nom = ""
    while not nom:
        nom = nom_propre(demander(f"   {fg(226)}🥚 " + t("intro.nom.question") + f"{RESET} "))
    while True:
        r = nom_propre(demander(f"   {fg(213)}" + t("intro.nom.confirme", nom=nom) + f"{RESET} "))
        from .accueil import oui
        if not r or oui(r):
            return nom
        nom = r
