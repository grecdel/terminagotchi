"""L'introduction du jeu et le déblocage progressif (même règles sur Android : Intro.kt).

Nouvelle partie (une vraie personne au clavier), en 8 cases (maquette validée le 9 novembre :
outils/ameliorations/allegement/planche_intro.png ; images : scenes.py) :
  1. le Terminaworld vivant, avec le nom des biomes ; 2. tout s'endort ; 3. les gardiens dorment aussi (les bébés des
     biomes, Abyssor en silhouette sous le cœur du monde) : 3 écrans illustrés (Entrée = suite, p = passer). Le nom
     n'est PLUS demandé avant de jouer ;
  4. le camp de base endormi : seul l'ordinateur brille ; l'enfant tape `pwd` ;
  5. `pwd` rallume le camp (l'écran de l'ordinateur s'allume, la lumière remonte les câbles et l'arbre) ; il tape `ls` ;
  6. `ls` : SEULEMENT là, l'œuf du type tiré arrive dans le nid, pixel par pixel ; on lui donne un nom avec
     `echo <nom>` (`echo` tout seul, ou un mot qui n'est pas un nom comme `echo bonjour` : « Et mon nom ? ») ;
  7. le nom donné, l'œuf se fêle ; `whoami` ;
  8. il éclot sur le vrai bébé de l'espèce tirée, la créature dit merci, explique ce qu'on vient de faire (les vraies
     commandes), où on est (le camp de base, ce que pwd a montré) et la suite (le chapitre 1).
  Les 4 commandes se tapent dans l'ordre (une commande de la liste tapée trop tôt est juste une commande) ; un petit
  tutoriel de l'invite arrive pas à pas (où taper et Entrée, une erreur n'est pas grave, ↑ rappelle, Tab complète).
  Ensuite, le reste du jeu s'ouvre petit à petit (table « deblocages » de intro.json, la même pour Android) : chaque
     fonction est présentée par la créature en un écran au moment où elle s'ouvre. Avant, ses commandes
     répondent gentiment « pas encore » (jamais une erreur).

Données : intro.json (copie exacte de donnees/intro.json, comme app/src/main/assets/intro.json).
Sauvegarde : state["intro"] = {etat: "oeuf" | "fini", faits: [ids], evt, erreur, eveil (l'heure de la 1re commande),
nomme (le nom a été donné avec echo ; avant, la partie s'appelle « Œuf » : intro.nom.attente)}, state["debloc"] =
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
    """Une nouvelle partie avec l'intro : le camp endormi, la liste de commandes, tout le reste fermé. Le nom viendra
    avec `echo <nom>` (9 nov.) : en attendant, la partie s'appelle « Œuf » (intro.nom.attente)."""
    state["intro"] = {"etat": "oeuf", "faits": [], "evt": None, "erreur": False, "nomme": False}
    state["debloc"] = {"mode": "progressif", "ouverts": [], "presentes": [], "file": []}
    if not (state.get("name") or "").strip():
        state["name"] = t("intro.nom.attente")
    return state


def nomme(state):
    """Vrai quand l'œuf a reçu son nom (echo <nom>), ou pour toute partie qui n'est pas dans l'intro."""
    i = state.get("intro")
    return not isinstance(i, dict) or i.get("etat") != "oeuf" or bool(i.get("nomme")) or len(i.get("faits", [])) >= 3


def nom_echo(texte):
    """Le nom donné à l'œuf par `echo Noisette` (texte : la commande entière), ou None si ce n'est pas un nom :
    `echo` tout seul, une redirection ou une variable (`echo a > f`, `echo $HOME`), une option seule, plus de 3 mots, un
    salut (`echo bonjour` : intro.json « pas_un_nom »), rien qui ressemble à des lettres. Les guillemets autour sont
    enlevés, la 1re lettre mise en majuscule, 16 caractères au plus. Même règle sur Android (Intro.nomEcho), vecteurs
    communs : donnees/intro_noms.json."""
    m = re.match(r"^\s*(echo|write-output)\b(.*)$", texte or "", re.I | re.S)
    if not m:
        return None
    reste = m.group(2).strip()
    if len(reste) >= 2 and reste[0] == reste[-1] and reste[0] in "'\"":
        reste = reste[1:-1].strip()
    if not reste or any(c in reste for c in "$><|&;`*?[]{}()=/\\\"'\n\t"):
        return None
    pas_nom = {x.lower() for x in donnees().get("pas_un_nom", [])}
    mots = [x for x in reste.split() if not x.startswith("-")]
    mots = [x for x in mots if x.lower().strip(".,!?¡¿。、！？") not in pas_nom]
    if not mots or len(mots) > 3:
        return None
    nom = nom_propre(" ".join(mots))
    if sum(1 for c in nom if c.isalpha()) < 2:
        return None
    return nom[:1].upper() + nom[1:]


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
    from . import satiete
    if satiete.niveau_appris(state) < q.get("niveau", 0):   # l'XP mise de côté avant une évolution compte aussi
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
    from . import apparence                  # les panneaux de l'espace de travail qui apparaissent maintenant
    apparence.a_(state)
    apparence.verifier(state)


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
        trouves = []                               # [(ligne de la liste, nom donné ou None)]
        sans_nom = False
        for m in verif.morceaux(l, None, core.statut_de(lignes, k)):
            if m.statut not in (None, 0) or not verif.casse_ok(verif.premier(m.texte)):
                continue
            n0 = len(i["faits"]) + len(trouves)  # 9 nov. : dans l'ordre (pwd, ls, echo <nom>, whoami)
            if n0 >= len(checklist()):
                break
            c = checklist()[n0]
            if not re.search(c["re"], m.texte.strip(), re.I):
                continue
            nom = None
            if c["id"] == "echo":
                nom = nom_echo(m.texte)
                if nom is None:                    # `echo` tout seul, `echo bonjour` : « Et mon nom ? »
                    sans_nom = True
                    break
            trouves.append((c, nom))
        if sans_nom and not trouves:
            core.say(state, t("intro.nom.encore"), 12)
            continue
        if not trouves:
            if not core.commande_existe(cmd) and not cmd.startswith(("./", "/")) or core.statut_de(lignes, k):
                i["erreur"] = True                 # une erreur : le petit tutoriel dit que ce n'est pas grave
            continue
        for c, nom in trouves:
            i["faits"].append(c["id"])
            n = len(i["faits"])
            i["evt"] = [n, time.time()]
            if n == 1 and not i.get("eveil"):
                i["eveil"] = i["evt"][1]          # pwd rallume le camp (scenes.py)
            if nom:                                # echo <nom> : l'œuf a son nom
                state["name"] = nom
                i["nomme"] = True
            if n >= len(checklist()):
                finir(state)
                return list(lignes[k + 1:])
            state["anim"] = [f"oeuf_{n}", time.time()]
            if n == 2:                             # ls : l'œuf arrive dans le nid
                core.log(state, t("app.oeuf_apparu", trait=core.nom_trait(state["trait"])))
                core.say(state, t("intro.c6.titre"), 8)
            elif n == 3:
                core.say(state, t("intro.nomme", nom=state["name"]), 10)
        if sans_nom:
            core.say(state, t("intro.nom.encore"), 12)
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
        return t("intro.astuce.erreur") + " " + t("intro.astuce.ctrlc")
    if len(i["faits"]) == 1:                 # C2 : l'invite « > » (une apostrophe pas fermée) se quitte avec Ctrl+C
        return t("intro.astuce.1") + " " + t("intro.astuce.ctrlc")
    return t(f"intro.astuce.{min(len(i['faits']), 3)}")


def titre_liste(state):
    """« Réveille le camp : 1/4 » tant que l'œuf n'est pas là (avant ls), puis « Nourris l'œuf : 2/4 »."""
    n = len(i_(state)["faits"])
    return t("intro.liste.camp" if n < 2 else "intro.liste.titre", n=n, total=len(checklist()))


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
def _file(state, fenetre=False):
    """La file des écrans ; fenetre : celle de la fenêtre du jeu (tg), sans « fermer et revenir » (idée 9 : il parle
    du terminal, il est montré par l'invite du shell)."""
    f = d_(state)["file"]
    return [x for x in f if x != "fermer"] if fenetre else f


def a_montrer(state, fenetre=False):
    """L'écran « Nouveau : … » à montrer, ou None. P2-6 : pas en pleine étape de leçon (il attend qu'elle soit réussie),
    sauf l'écran « merci » de l'éclosion."""
    f = _file(state, fenetre)
    if not f:
        return None
    if f[0] not in ("merci", "merci2"):
        from . import histoire
        if histoire.en_pleine_etape(state):
            return None
    return f[0]


def lu(state, fenetre=False):
    """L'écran du dessus de la file a été lu."""
    d = d_(state)
    f = _file(state, fenetre)
    if f:
        d["file"].remove(f[0])


def cmds(fid, tel=False):
    f = par_id().get(fid, {})
    c = list(f.get("cmd_tel" if tel else "cmd_pc", [])) + ["", ""]
    return {"cmd": c[0], "cmd2": c[1]}


def contenu(state, cid, chemin=None, tel=False):
    """(titre, [paragraphes]) d'un écran : merci, merci2, ou une fonction qui s'ouvre."""
    nom = state.get("name", "")
    if cid == "merci":
        titre = t("intro.merci.titre", nom=nom)
        try:                                     # l'espèce du bébé, nommée comme sur Android (« Bébé Engrenaille »)
            from . import bestiaire as B
            e = B.espece(state.get("espece_compagnon")) if state.get("espece_compagnon") else None
            if e:
                titre += " · " + t("forme.stade", stade=t("stade.1"), forme=e["nom"])
        except Exception:                        # noqa: BLE001
            pass
        return titre, [t("intro.merci", nom=nom), t("intro.recap")] + \
            [t(f"intro.r.{c['id']}") for c in checklist()]
    if cid == "merci2":
        from pathlib import Path
        return t("intro.ici.titre"), [t("intro.ici", chemin=chemin or str(Path.home())),
                                      t("intro.suite", chapitre=t("hist.reveil.titre"))]
    if cid == "fermer":                          # idée 9 : fermer et revenir (aide_douce.py), à la fin du tronc commun
        return "💤 " + t("ad.fermer.titre"), [t("ad.fermer.texte"), t("ad.fermer.tel" if tel else "ad.fermer.pc", cmd="`exit`")]
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


def _terminal():
    import shutil
    try:
        return shutil.get_terminal_size((100, 40))
    except (OSError, ValueError):
        return 100, 40


NB_CASES = 8          # les 8 cases de l'intro (planche du 9 novembre) : 3 écrans, puis 5 au camp


def texte_ecran(n):
    """Le texte d'un écran du début (le monde, endormi, les gardiens)."""
    return t(f"intro.e.texte.{n}")


def points(n, total=NB_CASES):
    """Les 8 cases de l'intro, comme les points du téléphone : ● la case du moment."""
    return " ".join((fg(84) + "●" if k == n else fg(240) + "•") for k in range(1, total + 1)) + RESET


def etiquettes_monde():
    """Le nom des biomes posé sur l'image du monde (case 1) : [(texte, x, y)] (x, y : fractions de l'image)."""
    from . import guide
    out = []
    for ty, x, y in donnees().get("illustrations", {}).get("monde", {}).get("etiquettes", []):
        out.append((t("intro.monde.arbre") if ty == "arbre" else guide.nom_type(ty), x, y))
    return out


def legende_monde():
    """Les noms des biomes sur une ligne (quand l'image ne peut pas porter d'étiquettes : une vraie image, sixel…)."""
    return " · ".join(x for x, _, _ in etiquettes_monde())


def ecran_intro(n, total=None, cols=None, rangs=None):
    """Un écran de l'intro : l'illustration (sinon la petite scène en pixels), le titre, le texte (PC). Écran 1 : le nom
    des biomes sur l'image ; écran 3 : les gardiens endormis, dessinés par le code (scenes.gardiens)."""
    from . import scenes
    e = donnees()["ecrans"][n - 1]
    total = total or NB_CASES
    c, r = _terminal()
    cols, rangs = cols or c, rangs or r
    larg = max(30, min(cols - 6, 76))
    texte = envelopper(texte_ecran(n), larg)
    dessin = []
    legende = []
    mode = scenes.mode_couleurs()
    tl = scenes.taille(cols, rangs, len(texte) + 7)
    img = e.get("image")
    if mode and tl and img == "gardiens":
        dessin = scenes.peindre(lambda w, h, pa: scenes.gardiens(w, h, pa), tl[0], tl[1] // 2, None, mode, " ")
        if scenes.rendu() not in scenes.GRAPHIQUES:
            dessin = scenes.etiqueter(dessin, [(t("intro.gardiens.coeur"), 0.56, 0.62),
                                               (t("intro.gardiens.abyssor"), 0.62, 0.9)], tl[0], 1)
        else:
            legende = ["   " + DIM + t("intro.gardiens.abyssor") + RESET]
    elif mode and tl and img and scenes.disponible("camp" if img == "camp_dort" else img):
        dessin = scenes.illustration(img, tl[0], tl[1], mode, " ")       # image, sextants… (scenes.rendu)
        if img == "monde":
            if scenes.rendu() not in scenes.GRAPHIQUES:
                dessin = scenes.etiqueter(dessin, etiquettes_monde(), tl[0], 1)
            else:
                legende = ["   " + DIM + legende_monde() + RESET]
    elif mode:
        dessin = ["   " + l for l in scene(e["scene"])]
    out = [""] + dessin + legende + [""]
    out.append(f"   {BOLD}{fg(213)}" + t(f"intro.e.titre.{n}") + RESET + f"   {points(n)}  {DIM}{n}/{total}{RESET}")
    for x in texte:
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
            return sprites.render_sprite(sprites.get_sprite(state, 1), sprites.palette(state, st=1))[0]
        rows = image_oeuf(3, ty=ty)
    return _demi_blocs(rows, oeufs.palette(ty))


class Ecran(list):
    """Une image d'animation de l'intro : l'écran entier (la scène et ses textes), pas seulement l'œuf."""


def titre_type(ty):
    """« Un œuf Plante ! Il sent bon l'herbe… » → (« Un œuf Plante ! », « Il sent bon l'herbe… ») : le titre de
    l'étape 4 et son texte (la 1re phrase de intro.type.<ty>, dans toutes les langues)."""
    from . import guide
    x = t("intro.type." + ty)
    m = re.search(r"[!！]\s*", x)
    if not m or m.end() >= len(x):
        return t("intro.oeuf.titre", type=guide.nom_type(ty)), x
    return x[:m.end()].strip(), x[m.end():].strip()


def barre_reception(pct, larg=30):
    """« réception de l'œuf… 37 % ███████░░░░ » (façon terminal)."""
    n = max(0, min(larg, round(larg * pct / 100)))
    return f"{BOLD}{fg(221)}" + t("intro.recoit", pct=int(pct)) + f"{RESET} {fg(84)}" + "█" * n + fg(22) + "░" * (larg - n) + RESET


def liste_courte(state, larg=200):
    """« Nourris l'œuf : 1/4   ✔ pwd   ○ ls   ○ echo bonjour   ○ whoami » (sur une ligne, comme la maquette ; sur
    deux si elle ne tient pas en larg colonnes). Renvoie une liste de lignes."""
    i = i_(state)
    morceaux = [(fg(78) + "✔ " if c["id"] in i["faits"] else DIM + "○ ") + commande_de(c) + RESET for c in checklist()]
    titre = DIM + titre_liste(state) + RESET
    une = titre + "   " + "   ".join(morceaux)
    if largeur(une) <= larg:
        return [une]
    return [titre, "  ".join(morceaux)]


def ligne_reception(state, pct, larg=200):
    """La barre de réception, plus courte (et sans « œuf Plante ») dans un terminal étroit."""
    from . import guide, oeufs
    suite = f"  {DIM}🥚 " + t("intro.oeuf.titre", type=guide.nom_type(oeufs.type_de(state))) + RESET
    lab = largeur(t("intro.recoit", pct=int(pct))) + 1
    if lab + 30 + largeur(suite) <= larg:
        return barre_reception(pct) + suite
    return barre_reception(pct, max(6, min(30, larg - lab)))


def etape(state, m):
    """(case, titre, texte) de l'intro au camp, au moment m (scenes.moment) : 4 le camp endormi (pwd) ; 5 il se rallume
    (ls) ; 6 l'œuf arrive (echo <nom>) ; 7 il a son nom et se fêle (whoami) ; 8 il éclot, puis « … est né ! ».
    Même découpage sur Android (Intro.etape)."""
    from . import oeufs
    ph = m["phase"]
    nf = len(i_(state)["faits"])
    nom = state.get("name", "")
    if ph == "dort":
        return 4, t("intro.c4.titre"), t("intro.c4.texte")
    if ph == "ne":                           # « … est né ! » seulement quand le bébé est là (après le fondu)
        return 8, t("intro.merci.titre", nom=nom), t("intro.merci", nom=nom)
    if ph in ("eclat", "eclot", "fondu"):
        n = len(checklist())
        return 8, titre_type(oeufs.type_de(state))[0], "✓ " + t("intro.eclot", n=n, total=n)
    if nf <= 1:
        return 5, t("intro.c5.titre"), t("intro.c5.texte")
    if nf == 2:
        return 6, t("intro.c6.titre"), t("intro.c6.texte")
    return 7, t("intro.c7.titre"), t("intro.c7.texte", nom=nom)


def textes_etape(state, m, larg):
    """Le titre (et les points des 8 cases) et le texte de la case du moment ; la barre de réception pendant que
    l'œuf arrive."""
    n, titre, texte = etape(state, m)
    out = [f"{BOLD}{fg(213)}{titre}{RESET}   " + points(n)]
    coul = fg(78) if m["phase"] in ("eveil", "eclat", "eclot", "fondu") else ""
    out += [coul + x + RESET for x in envelopper(texte, larg)]
    if m["phase"] == "telech" and 0 < m["pct"] < 100:
        out.append(ligne_reception(state, m["pct"], larg))
    return out


def dessin_scene(state, quand, cols, rangs, reserve, marge=" "):
    """Le camp de base en demi-blocs à l'instant quand (la plus grande scène qui laisse reserve lignes au texte) ;
    repli : l'œuf seul (petit terminal), ou rien (pas de couleurs, pas de place)."""
    from . import scenes
    mode = scenes.mode_couleurs()
    if not mode or not scenes.disponible():
        return []
    m = scenes.moment(state, quand)
    tl = scenes.taille(cols, rangs, reserve)
    if tl:
        return scenes.peindre(lambda w, h, pa: scenes.scene(state, w, h, quand, m, 0.5, pa), tl[0], tl[1] // 2, None,
                              mode, marge)
    if rangs - reserve >= 13 and cols >= 32:
        return scenes.oeuf_seul(state, m, mode, "  ")
    return []


def duree_anim(nom):
    """Combien de temps dure l'animation d'une commande de la liste (« oeuf_1 » : le réveil puis le début de l'œuf)."""
    from . import scenes
    tl = scenes.params().get("telechargement", {})
    vit = tl.get("vitesse", 24)
    n = 4 if nom == "eclosion" else int(nom.split("_")[1])
    if n == 1:
        return scenes.camp().get("duree", 3.4) + scenes.cible(1) / vit + 0.3
    if n >= len(checklist()):
        return (100 - scenes.cible(n - 1)) / vit + tl.get("eclat", 0.7) + tl.get("eclot", 1.4) + tl.get("fondu", 1.6) + 0.8
    if n == 3:                                   # echo <nom> : l'œuf se fêle (scenes.FELE)
        return scenes.FELE + 0.3
    return (scenes.cible(n) - scenes.cible(n - 1)) / vit + 0.3


def debut_anim(state, nom):
    i = i_(state)
    evt = i.get("evt") or [0, time.time()]
    if nom == "oeuf_1" and i.get("eveil"):
        return i["eveil"]
    return evt[1] if len(evt) > 1 and evt[1] else time.time()


class Images:
    """Les images d'une animation, calculées seulement quand on les montre (une vraie image coûte plus cher)."""

    def __init__(self, n, fn):
        self.n, self.fn, self.vu = n, fn, {}

    def __len__(self):
        return self.n

    def __getitem__(self, k):
        if k < 0:
            k += self.n
        if not 0 <= k < self.n:
            raise IndexError(k)
        if k not in self.vu:
            self.vu = {k: self.fn(k)}
        return self.vu[k]

    def __iter__(self):
        return (self[k] for k in range(self.n))


def animation(nom, state, ips=None):
    """(images, ips) d'une animation de l'intro (« oeuf_1 » à « oeuf_3 », « eclosion ») pour la fenêtre : l'écran
    entier (Ecran) à chaque instant, depuis la commande (le camp qui se réveille, l'œuf qui arrive, qui éclot, le bébé
    qui apparaît). Moins d'images par seconde quand ce sont de vraies images."""
    from . import scenes
    ips = ips or (4 if scenes.rendu() in scenes.GRAPHIQUES else 8)
    t0 = debut_anim(state, nom)
    c, r = _terminal()
    n = max(8, int(duree_anim(nom) * ips) + 1)
    return Images(n, lambda k: Ecran(lignes_ecran_oeuf(state, 0, None, t0 + k / ips, c, r))), ips


def lignes_ecran_oeuf(state, frame=0, image=None, quand=None, cols=None, rangs=None):
    """L'écran de l'œuf (fenêtre PC) : le camp de base (endormi, qui se réveille, l'œuf qui arrive), le titre et le
    texte de l'étape, la liste, l'astuce du moment, où taper. image : une image d'animation (Ecran) déjà prête."""
    if isinstance(image, Ecran):
        return list(image)
    from . import guide, oeufs, scenes
    quand = quand or time.time()
    c, r = _terminal()
    cols, rangs = cols or c, rangs or r
    larg = max(30, min(74, cols - 6))
    i = i_(state)
    m = scenes.moment(state, quand)
    # 9 nov. : pas de nom tant que l'œuf n'en a pas reçu un (echo <nom>), pas d'œuf avant ls
    tete = f"  {BOLD}" + (state["name"] if nomme(state) else "") + RESET
    if m["phase"] not in ("dort", "eveil") and len(i["faits"]) >= 2:
        tete += (" · " if nomme(state) else "") + "🥚 " + t("intro.oeuf.titre", type=guide.nom_type(oeufs.type_de(state)))
    tete += f"  {DIM}" + t("app.caractere", trait=core.nom_trait(state["trait"])) + RESET
    textes = ["  " + x for x in textes_etape(state, m, larg)]
    titre = titre_liste(state)
    bas = ["", fg(226) + "── 🥚 " + titre + " " + "─" * max(3, 44 - largeur(titre)) + RESET] + lignes_liste(state) + [""]
    for x in envelopper("💡 " + astuce(state), larg):
        bas.append(f"  {fg(214)}{x}{RESET}")
    for x in envelopper(t("intro.ou.pc"), larg):
        bas.append(f"  {DIM}{x}{RESET}")
    reserve = 2 + len(textes) + len(bas) + 6            # + le journal de la fenêtre
    dessin = dessin_scene(state, quand, cols, rangs, reserve)
    return dessin + [tete] + textes + bas


def bloc_prompt(state, quand, cols=None, rangs=None):
    """Ce que l'invite du shell montre pendant l'intro (comme intro_pc_terminal.png) : le camp en demi-blocs, puis le
    texte de la case (« Une petite lumière… tape pwd », « Le camp se rallume ! … tape ls », « Quelque chose arrive… »
    avec la barre de réception de l'œuf, « Il t'écoute… tape whoami »), la liste sur une ligne, l'astuce."""
    from . import scenes
    c, r = _terminal()
    cols, rangs = cols or c, rangs or r
    larg = max(30, cols - 6)
    m = scenes.moment(state, quand)
    ph = m["phase"]
    _n, _titre, texte = etape(state, m)
    out = []
    if ph != "ne":
        coul = fg(78) if ph in ("dort", "eveil", "eclat", "eclot", "fondu") else fg(214)
        out += [f"  {coul}{x}{RESET}" for x in envelopper(texte, larg)]
    if ph == "telech" and 0 < m["pct"] < 100:
        out.append("  " + ligne_reception(state, m["pct"], cols - 4))
    if ph != "ne":
        out += ["  " + x for x in liste_courte(state, cols - 4)]
    if ph not in ("ne", "eclat", "eclot", "fondu"):
        # v3 (I11) : l'astuce du moment reste sous la liste pendant tout l'œuf (« pas grave », Ctrl+C, ↑, Tab),
        # pas seulement avant la première commande
        out += [f"  {fg(214)}{x}{RESET}" for x in envelopper("💡 " + astuce(state), larg)]
    if ph == "dort":
        out += [f"  {DIM}{x}{RESET}" for x in envelopper(t("intro.ou.pc"), larg)]
    return [""] + dessin_scene(state, quand, cols, rangs, len(out) + 4) + out


ANIM_PROMPT = []          # les images à jouer dans le terminal avant la dernière (compagnon.prompt → jouer_prompt)


def animer_ici():
    """Vrai si l'invite peut jouer une animation (un vrai terminal, pas les tests ni TG_SANS_ANIM)."""
    import os
    import sys
    try:
        return sys.stdout.isatty() and not os.environ.get("TG_SANS_ANIM")
    except (AttributeError, ValueError, OSError):
        return False


def images_prompt(state, nom):
    """L'image finale de l'invite pour une commande de la liste ; l'animation qui y mène (si l'invite peut animer)
    est notée dans ANIM_PROMPT et jouée par jouer_prompt."""
    t0 = debut_anim(state, nom)
    d = duree_anim(nom)
    del ANIM_PROMPT[:]
    if animer_ici():
        ANIM_PROMPT.append((state, t0, d))
    return bloc_prompt(state, t0 + d)


def jouer_prompt(flux, ips=12):
    """Joue l'animation en attente au même endroit du terminal, en temps réel (chaque image montre l'instant où elle
    est prête : une vraie image, plus lente à fabriquer, saute des instants au lieu de ralentir). Le curseur revient
    au début ; l'image finale est écrite ensuite par l'invite. Ctrl+C l'arrête."""
    if not ANIM_PROMPT:
        return
    state, t0, d = ANIM_PROMPT[0]
    c, r = _terminal()
    debut = time.time()
    try:
        while True:
            x = time.time() - debut
            if x >= d:
                break
            img = bloc_prompt(state, t0 + x, c, r)
            flux.write("\x1b[J" + "\n".join(img) + RESET + "\n" + f"\x1b[{len(img)}A\r")
            flux.flush()
            time.sleep(max(0.0, 1 / ips - (time.time() - debut - x)))
    except KeyboardInterrupt:
        pass
    finally:
        del ANIM_PROMPT[:]
        try:
            flux.write("\x1b[J")
            flux.flush()
        except (OSError, ValueError):
            pass


def lignes_prompt(state):
    """Dans l'invite du shell, juste après une bonne commande : le camp, l'œuf qui arrive et la liste."""
    return bloc_prompt(state, time.time())


def commande_de(c):
    """La commande à taper d'une ligne de la liste (le passage `…` de son texte : `echo bonjour`…)."""
    m = re.search(r"`([^`]+)`", t(f"intro.l.{c['id']}"))
    return m.group(1) if m else c["id"]


def pour_prompt(state):
    """Ce que l'invite du shell montre au-dessus de sa ligne, une seule fois : le camp endormi et la liste au début,
    puis après chaque bonne commande le camp qui se réveille / l'œuf qui arrive (animé : ANIM_PROMPT), l'éclosion,
    puis chaque écran à présenter (merci, nouveautés). Marque ce qui est montré."""
    i = i_(state)
    evt = i.get("evt")
    if retient(state) and not i.get("liste_vue"):
        i["liste_vue"] = True
        return bloc_prompt(state, time.time())
    if evt and i.get("vu_prompt") != evt[1]:
        i["vu_prompt"] = evt[1]
        nom = "eclosion" if not retient(state) else f"oeuf_{max(1, min(3, evt[0]))}"
        out = list(images_prompt(state, nom))
        if retient(state):
            return out
        cid = a_montrer(state)
        if cid:
            out += lignes_ecran(state, cid)[:-1]
            _lu_prompt(state, cid)
        return out
    cid = a_montrer(state)
    if cid and not retient(state):
        lignes = lignes_ecran(state, cid)[:-1]
        _lu_prompt(state, cid)
        return lignes
    return []


def _lu_prompt(state, cid):
    lu(state)
    if cid == "fermer":                          # idée 9 : on attend un nouveau terminal pour dire « Te revoilà ! »
        from . import aide_douce
        aide_douce.marquer_fermer(state)


# ---------------------------------------------------------------- les écrans du début (PC)
MOTS_PASSER = ("p", "passer", "skip", "q")


def jouer_ecrans(demander, effacer=None):
    """Montre les 3 écrans du début (le monde, tout s'endort, les gardiens) ; Entrée = suite, p = passer. Le nom n'est
    plus demandé ici (9 nov.) : l'enfant le donnera à l'œuf avec `echo <nom>`, quand l'œuf sera arrivé. Un mot tapé
    sur un écran fait juste passer au suivant. Renvoie None."""
    n = len(donnees()["ecrans"])
    for k in range(1, n + 1):
        if effacer:
            effacer()
        print("\n".join(ecran_intro(k)))
        r = demander(f"   {DIM}" + t("intro.touches.pc2") + f"{RESET} ").strip()
        if r.lower() in MOTS_PASSER:
            break
    return None


def non(reponse):
    """Vrai si la réponse est « non » dans l'une des 14 langues (part.non)."""
    from . import langue
    from .accueil import _norm
    r = _norm(reponse)
    return bool(r) and any(r in {_norm(x) for x in (langue._charger(c).get("part.non") or [])} for c in langue.LANGUES)


def nom_propre(nom):
    """Le nom de l'œuf, sans caractères de contrôle (séquences d'échappement, retournement du texte), 16 au plus."""
    import unicodedata
    return "".join(c for c in (nom or "") if unicodedata.category(c) not in ("Cc", "Cf")).strip()[:16]
