"""La salle d'entraînement : de petits exercices chronométrés, des badges à échelons, des titres.

  tg entrainement [famille]   un exercice (au hasard, ou dans une famille : tg entrainement nettoyeur)
  tg entrainement <réponse>   répondre à un exercice de lecture (tg entrainement licorne)
  tg entrainement fin         ranger l'exercice en cours          (alias : tg exercice)
  tg badges                   les badges, les titres            tg badges titre [n|auto]   tg badges records

L'exercice se passe dans la salle d'entraînement du terrain : ~/terrain_terminagotchi/salle_entrainement/
(le jeu la vide et la prépare ; il ne touche jamais rien ailleurs). Il est réussi quand le résultat est là
(fichiers présents ou partis, dossier courant…) ou quand la bonne réponse est donnée. Pas de limite de temps,
pas d'échec : le chrono donne seulement une médaille (💎 diamant ≤ par, 🥇 or ≤ 2 × par, 🥈 argent ≤ 4 × par,
🥉 bronze sinon). Récompense : de l'XP pour la créature (jamais de « reviens ou tu perds »).

Seuls les exercices dont l'enfant a déjà tapé les commandes sont proposés (« vus ») ; les symboles > >> |
sont repérés dans les lignes tapées (state["entrainement"]["sym"]). Une famille sans exercice possible
reste cachée (« ??? »).

Badges (à la PARTIE, pas à la créature) : voir badges.py (grades Bit → Octet → … → Giga → Téra → Péta → Exa, galons et
étoiles ; `tg badges grades` les explique ; au-delà du Giga : Téra, Péta, Exa — voir badges.py). Titres : « Élève de la salle » (1 réussite), « <badge> <grade> »
(« Explorateur Kilo » : Octet et plus, couleur du grade), « Touche-à-tout » (6 familles en Octet),
« Légende de la salle » (8 familles en Méga, arc-en-ciel), et « Star de la semaine » (🏆, la meilleure
partie de la semaine dans une famille d'après le site : gardé UNE semaine, compté en ligne).

Anti-triche (même idée que tirage.py) : l'exercice est tiré de (graine du jour, 1 000 000 + compteur) ; son
« empreinte » (texte) part avec le temps à la synchro ; le site refait le tirage, vérifie l'empreinte, que la
graine est à ce joueur, qu'elle ne sert qu'une fois et que le temps est plausible. Sans graine : graine
locale au hasard, le record reste « non vérifié ». Même spécification : Entrainement.kt, site/src/entrainement.js ;
vecteurs communs : donnees/entrainement/vecteurs.json.

Tirage d'un exercice (h = Hasard(valeur, 1 000 000 + k)) ; choisir(liste, n) = Fisher-Yates partiel :
pour i de 0 à n-1, j = i + entier(len - i), échange, puis les n premiers.

Tests : pc/outils/test_entrainement.py (PC), tests/jvm/Entrainement.kt (appli), site/test/test.mjs et tirage.mjs (site).
"""
import os
import random
import secrets
import shutil
import stat
import time
from pathlib import Path

from . import badges as B
from . import core
from .langue import t
from .plateforme import BOLD, DIM, IS_WIN, RESET, C, est_colle, fg, piege
from .tirage import Hasard

BASE = 1_000_000
MAX_PAR_GRAINE = 100
SALLE = "salle_entrainement"
XP_BASE = 6
XP_MEDAILLE = {"bronze": 0, "argent": 2, "or": 4, "diamant": 6}
XP_RECORD = 3
MEDAILLES = ("bronze", "argent", "or", "diamant")
ICONE_MEDAILLE = {"bronze": "🥉", "argent": "🥈", "or": "🥇", "diamant": "💎"}
MAX_ENVOI = 100

PIECES = ["grotte", "foret", "lagon", "desert", "prairie", "canyon", "glacier", "marais", "clairiere", "colline",
          "plage", "jungle"]
COINS = ["coffre", "terrier", "creux", "tente", "cabane", "rocher", "panier", "boite"]
OBJETS = ["pomme", "balle", "cle", "lampe", "livre", "carte", "plume", "bougie", "boussole", "flute", "tambour",
          "etoile", "coquillage", "gomme", "crayon", "bille"]
MOTS = ["licorne", "dragon", "fusee", "volcan", "pirate", "robot", "comete", "tortue", "cactus", "biscuit", "nuage",
        "sirene"]

# Les commandes : chaque groupe = une commande et ses équivalents (Windows…). « > », « >> », « | » : symboles.
CMD = {"cd": ("cd", "set-location", "sl"), "ls": ("ls", "dir", "gci", "get-childitem"), "pwd": ("pwd", "get-location"),
       "mkdir": ("mkdir", "md", "new-item"), "touch": ("touch", "new-item", "ni"), "cp": ("cp", "copy", "copy-item"),
       "mv": ("mv", "move", "move-item"), "rm": ("rm", "del", "remove-item"), "rmdir": ("rmdir", "rd"),
       "cat": ("cat", "type", "get-content", "gc"), "head": ("head",), "tail": ("tail",),
       "grep": ("grep", "select-string", "sls"), "find": ("find",), "echo": ("echo", "write-output"),
       "wc": ("wc", "measure-object"), "sh": ("sh", "bash"), "chmod": ("chmod",)}
# type : (famille, commandes, symboles, par en secondes, réponse ?)
TYPES = {
    "exp_chemin": ("explorateur", ("cd",), (), 15, False),
    "exp_cle":    ("explorateur", ("cd", "ls"), (), 30, False),
    "bat_pieces": ("batisseur", ("mkdir",), (), 15, False),
    "bat_objets": ("batisseur", ("mkdir", "touch"), (), 25, False),
    "dem_mv":     ("demenageur", ("mv",), (), 20, False),
    "dem_cp":     ("demenageur", ("cp",), (), 20, False),
    "net_rm":     ("nettoyeur", ("rm",), (), 20, False),
    "net_rmdir":  ("nettoyeur", ("rmdir",), (), 20, False),
    "net_rmr":    ("nettoyeur", ("rm", "rmdir"), (), 15, False),
    "lec_cat":    ("lecteur", ("cat",), (), 20, True),
    "lec_head":   ("lecteur", ("head",), (), 20, True),
    "lec_tail":   ("lecteur", ("tail",), (), 20, True),
    "det_grep":   ("detective", ("grep",), (), 25, True),
    "det_find":   ("detective", ("find",), (), 25, True),
    "plo_ecrit":  ("plombier", ("echo",), (">",), 20, False),
    "plo_ajout":  ("plombier", ("echo",), (">>",), 20, False),
    "plo_tuyau":  ("plombier", ("grep", "wc"), ("|",), 30, True),
    "cui_lancer": ("cuisinier", ("sh",), (), 20, True),
    "cui_ecrire": ("cuisinier", ("sh", "chmod", "echo"), (">",), 40, False),
}
FAMILLE_CMDS = {"explorateur": "cd ls pwd", "batisseur": "mkdir touch", "demenageur": "cp mv",
                "nettoyeur": "rm rmdir", "lecteur": "cat head tail", "detective": "grep find",
                "plombier": "| > >>", "cuisinier": "sh chmod"}
COULEUR_TITRE = {"apprenti": "#c8b8a0", "touche": "#ff87ff", "star": "#ffaf00"}


def commande():
    """La commande à taper (PC : tg entrainement ; l'appli : entrainement)."""
    return "tg entrainement"


def salle():
    return core.TERRAIN / SALLE


# ---------------------------------------------------------------- le tirage (commun PC, appli, site)
def choisir(h, liste, n):
    a = list(liste)
    for i in range(n):
        j = i + h.entier(len(a) - i)
        a[i], a[j] = a[j], a[i]
    return a[:n]


def generer(typ, valeur, k):
    """Les paramètres de l'exercice et son empreinte (texte, comparée par le site)."""
    h = Hasard(valeur, BASE + k)
    p = {}
    if typ in ("exp_chemin", "exp_cle", "det_find"):
        p["pieces"] = choisir(h, PIECES, 3)
        p["coins"] = choisir(h, COINS, 2)
        p["i"] = h.entier(3)
        p["j"] = h.entier(2)
        if typ == "det_find":
            p["objet"] = choisir(h, OBJETS, 1)[0]
    elif typ == "bat_pieces":
        p["pieces"] = choisir(h, PIECES, 2)
    elif typ == "bat_objets":
        p["pieces"] = choisir(h, PIECES, 1)
        p["objets"] = choisir(h, OBJETS, 2)
    elif typ in ("dem_mv", "dem_cp"):
        p["pieces"] = choisir(h, PIECES, 2)
        p["objets"] = choisir(h, OBJETS, 1)
    elif typ == "net_rm":
        p["pieces"] = choisir(h, PIECES, 1)
        p["objets"] = choisir(h, OBJETS, 1)
        p["n"] = 2 + h.entier(3)
    elif typ == "net_rmdir":
        p["pieces"] = choisir(h, PIECES, 3)
        p["objets"] = choisir(h, OBJETS, 1)
    elif typ == "net_rmr":
        p["pieces"] = choisir(h, PIECES, 2)
        p["objets"] = choisir(h, OBJETS, 3)
    elif typ == "lec_cat":
        p["mots"] = choisir(h, MOTS, 1)
        p["n"] = 1 + h.entier(3)
    elif typ in ("lec_head", "lec_tail"):
        p["mots"] = choisir(h, MOTS, 8)
        p["n"] = 2 + h.entier(3)
    elif typ == "det_grep":
        p["objets"] = choisir(h, OBJETS, 5)
        p["mots"] = choisir(h, MOTS, 6)
        p["i"] = h.entier(5)
    elif typ in ("plo_ecrit", "cui_lancer", "cui_ecrire"):
        p["mots"] = choisir(h, MOTS, 1)
    elif typ == "plo_ajout":
        p["mots"] = choisir(h, MOTS, 4)
    elif typ == "plo_tuyau":
        p["objets"] = choisir(h, OBJETS, 4)
        n = 8 + h.entier(5)
        p["lignes"] = [h.entier(4) for _ in range(n)]
        if 0 not in p["lignes"]:
            p["lignes"][0] = 0
    else:
        raise ValueError(typ)
    return p, empreinte(typ, p)


def empreinte(typ, p):
    """« type|clé=valeurs|… » dans l'ordre des clés (listes séparées par des virgules)."""
    morceaux = [typ]
    for k in sorted(p):
        v = p[k]
        morceaux.append(k + "=" + (",".join(str(x) for x in v) if isinstance(v, list) else str(v)))
    return "|".join(morceaux)


def reponse(typ, p):
    """La bonne réponse (exercices à réponse), en minuscules."""
    if typ == "lec_cat":
        return p["mots"][0]
    if typ == "lec_head":
        return p["mots"][p["n"] - 1]
    if typ == "lec_tail":
        return p["mots"][7]
    if typ == "det_grep":
        return p["objets"][p["i"]]
    if typ == "det_find":
        return p["pieces"][p["i"]]
    if typ == "plo_tuyau":
        return str(p["lignes"].count(0))
    if typ == "cui_lancer":
        return p["mots"][0]
    return None


def medaille(typ, secondes):
    par = TYPES[typ][3]
    if secondes <= par:
        return "diamant"
    if secondes <= 2 * par:
        return "or"
    if secondes <= 4 * par:
        return "argent"
    return "bronze"


def semaine(t_s=None):
    """La semaine ISO (UTC) : « 2026-W43 »."""
    import datetime
    d = datetime.datetime.fromtimestamp(time.time() if t_s is None else t_s, datetime.timezone.utc).date()
    a, s, _ = d.isocalendar()
    return f"{a}-W{s:02d}"


def semaine_precedente(t_s=None):
    return semaine((time.time() if t_s is None else t_s) - 7 * 86400)


# ---------------------------------------------------------------- l'état (state["entrainement"])
def e_(state):
    e = state.get("entrainement")
    if not isinstance(e, dict):
        e = state["entrainement"] = {}
    for k, d in {"cours": None, "compteurs": {}, "familles": {}, "records": {}, "envoyer": [], "sym": [],
                 "titre": None, "hebdo": {}, "hebdo_compte": {}}.items():
        e.setdefault(k, d)
    e["titre"] = migrer_titre(e["titre"])
    return e


def migrer_titre(x):
    """Vieilles sauvegardes : le titre choisi « explorateur:argent » devient « explorateur:kilo » (les compteurs,
    eux, ne changent pas : les grades se recalculent)."""
    if isinstance(x, str) and ":" in x:
        f, _, en = x.partition(":")
        if en in B.ANCIENS:
            return f"{f}:{B.ANCIENS[en]}"
    return x


def fam_(e, f):
    x = e["familles"].setdefault(f, {})
    for k in ("n",) + MEDAILLES:
        x.setdefault(k, 0)
    return x


def connait(state, groupe):
    vus = set(state.get("seen", []))
    return any(c in vus for c in CMD[groupe])


def symbole_connu(state, s):
    sym = set(e_(state)["sym"])
    if s == ">" and (">" in sym or connait(state, "echo")):   # « echo pomme > … » : appris avec echo (leçon du repas)
        return True
    return s in sym


def type_possible(state, typ):
    _f, cmds, syms, _p, _r = TYPES[typ]
    return all(connait(state, c) for c in cmds) and all(symbole_connu(state, s) for s in syms)


def types_de(state, famille):
    return [x for x, v in TYPES.items() if v[0] == famille and type_possible(state, x)]


def familles_ouvertes(state):
    return [f for f in B.FAMILLES if types_de(state, f)]


def types_faits(e, f):
    """(exercices de la famille déjà réussis au moins une fois, exercices de la famille) — pour l'Exa."""
    tous = [x for x, v in TYPES.items() if v[0] == f]
    return sum(1 for x in tous if x in e["records"]), len(tous)


def echelon(e, f):
    x = fam_(e, f)
    a, b = types_faits(e, f)
    return B.echelon_de(x["n"], x["or"] + x["diamant"], x["diamant"], a == b)


def etoiles(e, f):
    return B.etoiles_de(fam_(e, f)["n"], echelon(e, f))


# ---------------------------------------------------------------- la salle (seulement dans le terrain)
def _vider(d):
    for p in list(d.iterdir()):
        try:
            if p.is_symlink() or p.is_file():
                p.unlink()
            else:
                shutil.rmtree(p, onerror=lambda f, x, _i: (os.chmod(x, 0o700), f(x)))
        except OSError:
            pass


def _ecrire(p, texte, executable=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")
    if executable:
        p.chmod(p.stat().st_mode | stat.S_IXUSR)


def preparer(typ, p):
    """Vide la salle et pose ce dont l'exercice a besoin. Renvoie False si c'est impossible."""
    T = core.TERRAIN
    if not T.is_dir():
        return False
    S = salle()
    try:
        if S.is_symlink() or (S.exists() and not S.is_dir()):
            return False
        S.mkdir(exist_ok=True)
        if S.resolve().parent != T.resolve():
            return False
        _vider(S)
        if typ in ("exp_chemin", "exp_cle", "det_find"):
            for x in p["pieces"]:
                for c in p["coins"]:
                    (S / x / c).mkdir(parents=True, exist_ok=True)
            cible = S / p["pieces"][p["i"]] / p["coins"][p["j"]]
            if typ == "exp_cle":
                _ecrire(cible / "cle.txt", "🔑\n")
            if typ == "det_find":
                _ecrire(cible / (p["objet"] + ".txt"), p["objet"] + "\n")
        elif typ == "bat_objets" or typ == "bat_pieces":
            pass
        elif typ in ("dem_mv", "dem_cp"):
            _ecrire(S / p["pieces"][0] / (p["objets"][0] + ".txt"), p["objets"][0] + "\n")
            (S / p["pieces"][1]).mkdir()
        elif typ == "net_rm":
            d = S / p["pieces"][0]
            for i in range(1, p["n"] + 1):
                _ecrire(d / f"poussiere_{i}.tmp", t("env.poussiere.contenu") + "\n")
            _ecrire(d / (p["objets"][0] + ".txt"), p["objets"][0] + "\n")
        elif typ == "net_rmdir":
            (S / p["pieces"][0]).mkdir()
            (S / p["pieces"][1]).mkdir()
            _ecrire(S / p["pieces"][2] / (p["objets"][0] + ".txt"), p["objets"][0] + "\n")
        elif typ == "net_rmr":
            for o in p["objets"][:2]:
                _ecrire(S / p["pieces"][0] / (o + ".txt"), o + "\n")
            _ecrire(S / p["pieces"][1] / (p["objets"][2] + ".txt"), p["objets"][2] + "\n")
        elif typ == "lec_cat":
            lignes = list(lettre())
            lignes.insert(p["n"], t("ent.lettre.secret", mot=p["mots"][0]))
            _ecrire(S / "lettre.txt", "\n".join(lignes) + "\n")
        elif typ in ("lec_head", "lec_tail"):
            _ecrire(S / "liste.txt", "\n".join(p["mots"]) + "\n")
        elif typ == "det_grep":
            for i, o in enumerate(p["objets"]):
                lignes = [p["mots"][1 + i]] + ([p["mots"][0]] if i == p["i"] else [])
                _ecrire(S / "indices" / (o + ".txt"), "\n".join(lignes) + "\n")
        elif typ == "plo_ajout":
            _ecrire(S / "liste.txt", "\n".join(p["mots"][:3]) + "\n")
        elif typ == "plo_tuyau":
            _ecrire(S / "courses.txt", "\n".join(p["objets"][i] for i in p["lignes"]) + "\n")
        elif typ == "cui_lancer":
            m = p["mots"][0]
            c = len(m) // 2
            _ecrire(S / "recette.sh", f"a={m[:c]}\nb={m[c:]}\necho \"$a$b\"\n")
        return True
    except OSError:
        return False


def lettre():
    from .langue import liste
    return liste("ent.lettre")


def _txt(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        try:
            return p.read_bytes().decode("utf-16", errors="replace")
        except OSError:
            return ""


def _mots(p):
    return [x.strip().lower() for x in _txt(p).replace("\x00", "").splitlines() if x.strip()]


def _meme(a, b):
    try:
        return a is not None and Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def verifier(typ, p, cwd=None):
    """« ok » si l'exercice est réussi, « oups » s'il ne peut plus l'être (objet à garder effacé), sinon None."""
    S = salle()
    if typ in ("exp_chemin", "exp_cle"):
        return "ok" if _meme(cwd, S / p["pieces"][p["i"]] / p["coins"][p["j"]]) else None
    if typ == "bat_pieces":
        return "ok" if all((S / x).is_dir() for x in p["pieces"]) else None
    if typ == "bat_objets":
        d = S / p["pieces"][0]
        return "ok" if all((d / (o + ".txt")).is_file() for o in p["objets"]) else None
    if typ in ("dem_mv", "dem_cp"):
        nom = p["objets"][0] + ".txt"
        a, b = S / p["pieces"][0] / nom, S / p["pieces"][1] / nom
        if typ == "dem_mv":
            return "ok" if b.is_file() and not a.exists() else None
        if not a.exists() and not b.exists():
            return "oups"
        return "ok" if a.is_file() and b.is_file() else None
    if typ == "net_rm":
        d = S / p["pieces"][0]
        garde = d / (p["objets"][0] + ".txt")
        if not garde.is_file():
            return "oups"
        reste = [x for x in d.iterdir() if x.suffix == ".tmp"] if d.is_dir() else []
        return "ok" if not reste else None
    if typ == "net_rmdir":
        if not (S / p["pieces"][2] / (p["objets"][0] + ".txt")).is_file():
            return "oups"
        return "ok" if not (S / p["pieces"][0]).exists() and not (S / p["pieces"][1]).exists() else None
    if typ == "net_rmr":
        if not (S / p["pieces"][1] / (p["objets"][2] + ".txt")).is_file():
            return "oups"
        return "ok" if not (S / p["pieces"][0]).exists() else None
    if typ == "plo_ecrit":
        return "ok" if p["mots"][0] in _txt(S / "note.txt").lower() else None
    if typ == "plo_ajout":
        m = _mots(S / "liste.txt")
        return "ok" if m == p["mots"][:4] else None
    if typ == "cui_ecrire":
        f = S / "miam.sh"
        if not f.is_file():
            return None
        x = _txt(f).lower()
        return "ok" if "echo" in x and p["mots"][0] in x and os.access(f, os.X_OK) else None
    return None


def normaliser(r):
    r = (r or "").strip().strip("\"'«» ").lower()
    for fin in (".txt", "/"):
        if r.endswith(fin):
            r = r[: -len(fin)]
    if r.startswith("./"):
        r = r[2:]
    return r


def bonne_reponse(typ, p, r):
    attendu = reponse(typ, p)
    r = normaliser(r)
    if typ == "det_find":
        return r.split("/")[0] == attendu or r == f"{attendu}/{p['coins'][p['j']]}"
    if typ == "det_grep":
        return r.split("/")[-1] == attendu
    return r == attendu


# ---------------------------------------------------------------- textes
def vert(state, cmd):
    """La commande, en vert (et piégée contre le copier-coller) si l'enfant l'a déjà rencontrée."""
    mot = core.first_word(cmd) or ""
    vus = set(state.get("seen", []))
    return f"`{piege(cmd)}`" if mot in vus or mot == "tg" else piege(cmd)


def idees(typ, p):
    """Les commandes qui aident (depuis la salle)."""
    P, Co, O, M = p.get("pieces", []), p.get("coins", []), p.get("objets", []), p.get("mots", [])
    if typ == "exp_chemin":
        return [f"cd {P[p['i']]}/{Co[p['j']]}"]
    if typ == "exp_cle":
        return [C("ls", "dir"), f"cd {P[0]}"]
    if typ == "bat_pieces":
        return [f"mkdir {P[0]} {P[1]}"]
    if typ == "bat_objets":
        return [f"mkdir {P[0]}", C(f"touch {P[0]}/{O[0]}.txt", f"New-Item {P[0]}/{O[0]}.txt")]
    if typ == "dem_mv":
        return [f"mv {P[0]}/{O[0]}.txt {P[1]}/"]
    if typ == "dem_cp":
        return [f"cp {P[0]}/{O[0]}.txt {P[1]}/"]
    if typ == "net_rm":
        return [f"rm {P[0]}/*.tmp"]
    if typ == "net_rmdir":
        return [f"rmdir {P[0]} {P[1]}"]
    if typ == "net_rmr":
        return [f"rm -r {P[0]}"]
    if typ == "lec_cat":
        return [C("cat lettre.txt", "type lettre.txt")]
    if typ == "lec_head":
        return [C(f"head -n {p['n']} liste.txt", f"Get-Content liste.txt -Head {p['n']}")]
    if typ == "lec_tail":
        return [C("tail -n 1 liste.txt", "Get-Content liste.txt -Tail 1")]
    if typ == "det_grep":
        return [C(f"grep {M[0]} indices/*", f"Select-String {M[0]} indices/*")]
    if typ == "det_find":
        return [C(f"find . -name {p['objet']}.txt", f"Get-ChildItem -Recurse -Filter {p['objet']}.txt")]
    if typ == "plo_ecrit":
        return [f"echo {M[0]} > note.txt"]
    if typ == "plo_ajout":
        return [f"echo {M[3]} >> liste.txt"]
    if typ == "plo_tuyau":
        return [f"grep {O[0]} courses.txt | wc -l"]
    if typ == "cui_lancer":
        return ["sh recette.sh"]
    if typ == "cui_ecrire":
        return [f"echo 'echo {M[0]}' > miam.sh", "chmod +x miam.sh"]
    return []


def consigne(typ, p):
    P, Co, O, M = p.get("pieces", []), p.get("coins", []), p.get("objets", []), p.get("mots", [])
    v = {}
    if typ == "exp_chemin":
        v = {"chemin": f"{P[p['i']]}/{Co[p['j']]}"}
    elif typ == "bat_pieces":
        v = {"a": P[0], "b": P[1]}
    elif typ == "bat_objets":
        v = {"piece": P[0], "a": O[0] + ".txt", "b": O[1] + ".txt"}
    elif typ in ("dem_mv", "dem_cp"):
        v = {"objet": O[0] + ".txt", "de": P[0], "vers": P[1]}
    elif typ == "net_rm":
        v = {"piece": P[0], "objet": O[0] + ".txt"}
    elif typ == "net_rmdir":
        v = {"a": P[0], "b": P[1], "c": P[2]}
    elif typ == "net_rmr":
        v = {"a": P[0], "b": P[1]}
    elif typ == "lec_head":
        v = {"n": p["n"]}
    elif typ == "det_grep":
        v = {"mot": M[0]}
    elif typ == "det_find":
        v = {"objet": p["objet"] + ".txt"}
    elif typ in ("plo_ecrit", "cui_ecrire"):
        v = {"mot": M[0]}
    elif typ == "plo_ajout":
        v = {"mot": M[3]}
    elif typ == "plo_tuyau":
        v = {"objet": O[0]}
    return t(f"ent.type.{typ}.dit", **v)


def nom_famille(f):
    return t("ent.famille." + f)


def nom_echelon(e):
    """Le nom d'un grade (Bit, Octet, Kilo, Méga, Giga)."""
    return t("ent.grade." + e)


def nom_medaille(m):
    return t("ent.medaille." + m)


def colorer(texte, couleur):
    if couleur == "arc":
        from .bestiaire import arc_en_ciel
        return arc_en_ciel(texte)
    r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
    return f"\x1b[38;2;{r};{g};{b}m{texte}{RESET}"


# ---------------------------------------------------------------- titres
def titres(state):
    """Les titres gagnés : [(identifiant, texte, couleur « #rrggbb » ou « arc »)], du plus beau au plus simple."""
    e = e_(state)
    out = []
    ech = {f: echelon(e, f) for f in B.FAMILLES}
    if all(k >= 3 for k in ech.values()):
        out.append(("legende", t("ent.titre.legende"), "arc"))
    h = e.get("hebdo") or {}
    if h.get("semaine") == semaine_precedente():
        for f in h.get("familles", []):
            if f in B.FAMILLES:
                out.append(("star:" + f, t("ent.titre.star", badge=nom_famille(f)), COULEUR_TITRE["star"]))
    if sum(1 for k in ech.values() if k >= 1) >= 6:
        out.append(("touche", t("ent.titre.touche"), COULEUR_TITRE["touche"]))
    for f in sorted(B.FAMILLES, key=lambda f: (-ech[f], -fam_(e, f)["n"], B.FAMILLES.index(f))):
        if ech[f] >= 1:
            en = B.ECHELONS[ech[f]]
            out.append((f"{f}:{en}", t("ent.titre.famille", badge=nom_famille(f), echelon=nom_echelon(en)),
                        B.COULEURS[en][2]))
    if any(fam_(e, f)["n"] for f in B.FAMILLES):
        out.append(("apprenti", t("ent.titre.apprenti"), COULEUR_TITRE["apprenti"]))
    return out


def titre_affiche(state):
    """(texte, couleur) du titre à montrer à côté du nom, ou None. Le titre choisi s'il est encore gagné."""
    tous = titres(state)
    if not tous:
        return None
    choix = e_(state).get("titre")
    for i, x, c in tous:
        if i == choix:
            return x, c
    return tous[0][1], tous[0][2]


def titre_colore(state):
    x = titre_affiche(state)
    return colorer(f"« {x[0]} »", x[1]) if x else ""


# ---------------------------------------------------------------- commencer, réussir
def _graine(state):
    """(identifiant, valeur, compteur) pour un nouvel exercice ; sans graine : une graine locale (« »)."""
    from .tirage import graine_du_jour
    e = e_(state)
    g = graine_du_jour(state)
    if g:
        n = e["compteurs"].get(g[0], 0)
        if n < MAX_PAR_GRAINE:
            e["compteurs"] = {k: v for k, v in e["compteurs"].items() if k.split(".")[0] >= g[0].split(".")[0]}
            e["compteurs"][g[0]] = n + 1
            return g[0], g[1], n
    return "", secrets.token_hex(32), 0


def lignes_exercice(state, c):
    typ = c["type"]
    p, _ = generer(typ, c["v"], c["n"])
    f = TYPES[typ][0]
    par = TYPES[typ][3]
    out = [f"{fg(213)}{BOLD}" + t("ent.debut.titre", famille=nom_famille(f)) + RESET,
           " " + consigne(typ, p),
           f" {DIM}" + t("ent.depart", cmd=vert(state, f"cd ~/{core.TERRAIN.name}/{SALLE}")) + RESET]
    for x in idees(typ, p):
        out.append(f" {DIM}" + t("ent.idee", cmd=vert(state, x)) + RESET)
    if TYPES[typ][4]:
        out.append(" " + t("ent.repondre", cmd=vert(state, commande())))
    else:
        out.append(f" {DIM}" + t("ent.verifier", cmd=vert(state, commande())) + RESET)
    out.append(f" {DIM}" + t("ent.chrono", d=par, o=2 * par, a=4 * par) + RESET)
    return out


def commencer(state, famille=None):
    """Prépare un nouvel exercice. Renvoie les lignes à afficher."""
    e = e_(state)
    if not core.TERRAIN.is_dir():
        return [t("ent.pas_de_terrain")]
    ouvertes = familles_ouvertes(state)
    if not ouvertes:
        return [t("ent.aucune_famille", cmds="cd, ls, mkdir")]
    if famille:
        if famille not in ouvertes:
            return [t("ent.famille_fermee", badge=nom_famille(famille), cmds=FAMILLE_CMDS[famille])]
        f = famille
    else:
        f = random.choice(ouvertes)
    typ = random.choice(types_de(state, f))
    gid, valeur, n = _graine(state)
    p, emp = generer(typ, valeur, n)
    if not preparer(typ, p):
        return [t("ent.salle_impossible")]
    e["cours"] = {"type": typ, "g": gid, "v": valeur, "n": n, "debut": time.time(), "e": emp}
    core.animer(state, "parle")
    return lignes_exercice(state, e["cours"])


def reussir(state, cwd=None):
    """L'exercice en cours est réussi : médaille, records, badges, XP. Renvoie les lignes (déjà dites en bulle)."""
    e = e_(state)
    c = e["cours"]
    typ = c["type"]
    f = TYPES[typ][0]
    s = max(0.1, round(time.time() - c["debut"], 1))
    m = medaille(typ, s)
    avant = echelon(e, f)
    et_avant = etoiles(e, f)
    x = fam_(e, f)
    x["n"] += 1
    x[m] += 1
    rec = e["records"].get(typ)
    nouveau = rec is None or s < rec.get("t", 1e9)
    if nouveau:
        e["records"][typ] = {"t": s, "d": int(time.time() * 1000), "g": c["g"], "n": c["n"], "v": None}
    run = {"id": secrets.token_hex(6), "type": typ, "g": c["g"], "n": c["n"], "t": s, "d": int(time.time() * 1000),
           "e": c["e"], "m": m}
    e["envoyer"] = (e["envoyer"] + [run])[-MAX_ENVOI:]
    e["cours"] = None
    xp = XP_BASE + XP_MEDAILLE[m] + (XP_RECORD if nouveau and rec is not None else 0)
    core.add_xp(state, xp)
    from . import envies
    envies.plaisir(state, "jeu", "defi")
    out = [t("ent.reussi", s=f"{s:.1f}", icone=ICONE_MEDAILLE[m], medaille=nom_medaille(m), xp=xp, nom=state["name"])]
    if nouveau and rec is not None:
        out.append(t("ent.record", avant=f"{rec['t']:.1f}"))
    apres = echelon(e, f)
    if apres > avant:
        en = B.ECHELONS[apres]
        out.append(t("ent.echelon_monte", badge=nom_famille(f), echelon=nom_echelon(en), cmd="`tg badges`"))
        core.log(state, "🏅 " + t("ent.echelon_log", badge=nom_famille(f), echelon=nom_echelon(en)))
    elif apres == avant and etoiles(e, f) > et_avant:
        out.append(t("ent.etoile", badge=nom_famille(f), etoiles=B.texte_etoiles(etoiles(e, f))))
    core.log(state, t("ent.reussi_log", s=f"{s:.1f}", icone=ICONE_MEDAILLE[m]))
    core.say(state, out[0], 12)
    core.animer(state, "victoire")
    return out


def _cours_ok(e):
    c = e.get("cours")
    return isinstance(c, dict) and c.get("type") in TYPES and isinstance(c.get("v"), str) and len(c["v"]) >= 16


def tick(state, lignes, cwd=None):
    """À chaque étape de jeu : repère les symboles tapés, et vérifie l'exercice en cours."""
    e = e_(state)
    for l in lignes:
        if est_colle(l):
            continue
        for s in (">>", "|", ">"):
            if s in l and s not in e["sym"] and not (s == ">" and ">>" in l and l.count(">") == 2):
                e["sym"].append(s)
    if not _cours_ok(e):
        e["cours"] = None
        return None
    c = e["cours"]
    if TYPES[c["type"]][4]:
        return None
    from . import maison
    p, _ = generer(c["type"], c["v"], c["n"])
    r = verifier(c["type"], p, cwd or maison.ici(state))
    if r == "ok":
        return reussir(state)
    if r == "oups" and not c.get("oups"):
        c["oups"] = True
        core.say(state, t("ent.oups", cmd=commande()), 12)
    return None


def commande_texte(state, args, cwd=None):
    """tg entrainement [famille | réponse | fin]. Renvoie les lignes à afficher."""
    e = e_(state)
    if not _cours_ok(e):
        e["cours"] = None
    mot = " ".join(args).strip()
    cle = normaliser(mot)
    fams = {normaliser(nom_famille(f)): f for f in B.FAMILLES}
    fams.update({f: f for f in B.FAMILLES})
    if cle in ("fin", "stop", "range"):
        if not e["cours"]:
            return [t("ent.rien", cmd=commande())]
        e["cours"] = None
        return [t("ent.range", cmd=commande())]
    c = e["cours"]
    if c:
        if est_colle(mot):
            return [t("ent.colle")]
        if not TYPES[c["type"]][4]:
            r = tick(state, [], cwd)               # c'est peut-être déjà fait (sans compagnon dans le terminal)
            if r:
                return r
        elif mot and cle not in fams:
            p, _ = generer(c["type"], c["v"], c["n"])
            if bonne_reponse(c["type"], p, mot):
                return reussir(state)
            core.animer(state, "confus")
            return [t("ent.pas_tout_a_fait")]
        if cle in fams:
            return [t("ent.deja", cmd=commande() + " fin")] + lignes_exercice(state, c)
        return [t("ent.en_cours")] + lignes_exercice(state, c)
    if mot and cle not in fams:
        return [t("ent.famille_inconnue", nom=mot, liste=", ".join(nom_famille(f) for f in familles_ouvertes(state)) or "…")]
    return commencer(state, fams.get(cle))


# ---------------------------------------------------------------- badges, titres, records (écrans)
def progres(e, f):
    """Le texte de progression d'un badge gagné : vers le grade suivant (ou ce qui manque : médailles, exercices),
    ou vers l'étoile suivante à l'Exa."""
    x = fam_(e, f)
    k = echelon(e, f)
    if k + 1 < len(B.ECHELONS):
        s = B.SEUILS[k + 1]
        if k + 1 == 4 and x["n"] >= s:
            return t("ent.badges.manque_or")
        if x["n"] >= s and x["diamant"] < B.DIAMANTS[k + 1]:
            return t("ent.badges.manque_diamant", n=x["diamant"], s=B.DIAMANTS[k + 1])
        if k + 1 == 7 and x["n"] >= s:
            return t("ent.badges.manque_types", n=types_faits(e, f)[0], s=types_faits(e, f)[1])
        return t("ent.badges.progres", n=x["n"], s=s, echelon=nom_echelon(B.ECHELONS[k + 1]))
    s = B.prochaine_etoile(x["n"], k)
    return t("ent.badges.etoile", n=x["n"], s=s) if s else t("ent.badges.max")


def ecran_badges(state):
    e = e_(state)
    ouvertes = set(familles_ouvertes(state))
    cases = []
    for f in B.FAMILLES:
        x = fam_(e, f)
        k = echelon(e, f)
        if f not in ouvertes and not x["n"]:
            cases.append((None, None, 0, [(t("ent.badges.cache"), DIM), ("", ""), ("", "")]))
            continue
        en = B.ECHELONS[k] if k >= 0 else None
        if en:
            n = etoiles(e, f)
            cases.append((f, en, n, [(nom_famille(f), BOLD),
                                     (nom_echelon(en) + " " + B.texte_etoiles(n), B.couleur_ansi(en)),
                                     (progres(e, f), DIM)]))
        else:
            cases.append((None, None, 0, [(nom_famille(f), BOLD), (t("ent.badges.decouvrir"), DIM),
                                          (t("ent.badges.progres", n=x["n"], s=B.SEUILS[0],
                                             echelon=nom_echelon(B.ECHELONS[0])), DIM)]))
    out = [f" {fg(213)}{BOLD}" + t("ent.badges.titre") + f"{RESET}   {DIM}" + t("ent.badges.sous") + RESET, ""]
    out += B.planche(cases)
    ta = titre_affiche(state)
    if ta:
        out.append(f" {BOLD}" + t("ent.titre.ligne") + f"{RESET} " + colorer(f"« {ta[0]} »", ta[1])
                   + f"   {DIM}" + t("ent.titre.changer", cmd="`tg badges titre`") + RESET)
    hc = e.get("hebdo_compte") or {}
    for f in B.FAMILLES:
        if hc.get(f):
            out.append(" " + colorer(t("ent.hebdo.compte", badge=nom_famille(f), n=hc[f]), COULEUR_TITRE["star"]))
    out.append(" " + t("ent.badges.grades", cmd="`tg badges grades`"))
    out.append(f" {DIM}" + t("ent.badges.pied", cmd="`tg entrainement`", rec="`tg badges records`") + RESET)
    return out


def ecran_grades(state):
    """Les 8 grades expliqués (Bit, Octet… : des tailles d'informatique), avec leurs galons et les étoiles."""
    cases = []
    for k, en in enumerate(B.ECHELONS):
        cases.append(("explorateur", en, 0, [(nom_echelon(en), B.couleur_ansi(en) + BOLD),
                                             (t("ent.grades.seuil", n=B.SEUILS[k]), DIM),
                                             (t("ent.badges.manque_or") if k == 4 else
                                              t("ent.grades.diamants", n=B.DIAMANTS[k]) if B.DIAMANTS[k] else "", DIM),
                                             (t("ent.grades.tous_types") if k == 7 else "", DIM)]))
    out = [f" {fg(213)}{BOLD}" + t("ent.grades.titre") + RESET, ""]
    out += B.planche(cases)
    out.append(" " + t("ent.grades.intro"))
    for en in B.ECHELONS:
        out.append(f"   {B.couleur_ansi(en)}{BOLD}{nom_echelon(en)}{RESET} : " + t("ent.grades." + en))
    out.append("")
    out.append(" " + t("ent.grades.galons"))
    out.append(" " + t("ent.grades.etoiles", n=B.ETOILES[-1][2]))
    return out


def ecran_titres(state, choix=None):
    e = e_(state)
    tous = titres(state)
    out = []
    if choix:
        if choix.lower() in ("auto", "0"):
            e["titre"] = None
            out.append(t("ent.titres.auto"))
        elif choix.isdigit() and 1 <= int(choix) <= len(tous):
            e["titre"] = tous[int(choix) - 1][0]
            out.append(t("ent.titres.choisi", titre=colorer(tous[int(choix) - 1][1], tous[int(choix) - 1][2])))
        else:
            out.append(t("ent.titres.numero", n=len(tous)))
        return out
    if not tous:
        return [t("ent.titres.aucun", cmd="`tg entrainement`")]
    out.append(f" {BOLD}" + t("ent.titres.liste") + RESET)
    choisi = titre_affiche(state)
    for i, (_id, x, c) in enumerate(tous, 1):
        marque = "●" if choisi and x == choisi[0] else " "
        out.append(f"  {marque} {i:>2}. " + colorer(x, c))
    out.append(f" {DIM}" + t("ent.titres.aide", cmd="`tg badges titre 2`", auto="`tg badges titre auto`") + RESET)
    return out


def ecran_records(state):
    e = e_(state)
    if not e["records"]:
        return [t("ent.records.aucun", cmd="`tg entrainement`")]
    out = [f" {fg(213)}{BOLD}" + t("ent.records.titre") + RESET]
    for f in B.FAMILLES:
        lignes = [(typ, r) for typ, r in e["records"].items() if typ in TYPES and TYPES[typ][0] == f]
        if not lignes:
            continue
        out.append(f" {BOLD}{nom_famille(f)}{RESET}")
        for typ, r in sorted(lignes):
            m = medaille(typ, r["t"])
            v = r.get("v")
            etat = t("ent.records.verifie") if v else t("ent.records.non_verifie") if v is False else ""
            out.append(f"   {ICONE_MEDAILLE[m]} " + t(f"ent.type.{typ}.titre") + f" : {r['t']:.1f} s"
                       + (f"  {DIM}{etat}{RESET}" if etat else ""))
    return out


def commande_badges(state, args):
    if args and args[0].lower() in ("titre", "titres"):
        return ecran_titres(state, args[1] if len(args) > 1 else None)
    if args and args[0].lower() in ("records", "record"):
        return ecran_records(state)
    if args and args[0].lower() in ("grades", "grade", "echelons", "echelon", "échelons", "échelon", "aide", "etoiles", "étoiles"):
        return ecran_grades(state)
    return ecran_badges(state)


# ---------------------------------------------------------------- synchro (recense.py)
def instantane(state):
    e = e_(state)
    return {f: dict(fam_(e, f)) for f in B.FAMILLES}


def charge(state, base):
    """Ce qui part au site : les compteurs gagnés depuis la dernière synchro, les exercices à vérifier, les records."""
    e = e_(state)
    snap = instantane(state)
    b = base or {}
    deltas = {f: {k: max(0, v - (b.get(f) or {}).get(k, 0)) for k, v in x.items()} for f, x in snap.items()}
    recs = {typ: {"t": r["t"], "g": r.get("g", ""), "n": r.get("n", 0), "d": r.get("d", 0)}
            for typ, r in e["records"].items() if typ in TYPES}
    return {"deltas": deltas, "runs": list(e["envoyer"])[-MAX_ENVOI:], "records": recs}, snap


def appliquer(state, srv, snap, envoyes, extra):
    """Recopie les compteurs communs (en gardant ce qui a été gagné ici pendant la synchro), les records vérifiés,
    et la « Star de la semaine ». Renvoie la nouvelle base."""
    e = e_(state)
    fs = (srv or {}).get("familles") or {}
    for f in B.FAMILLES:
        x = fam_(e, f)
        sx = fs.get(f) or {}
        for k in list(x):
            x[k] = int(sx.get(k, 0)) + (x[k] - (snap.get(f) or {}).get(k, 0))
    for typ, r in ((srv or {}).get("records") or {}).items():
        if typ not in TYPES or not isinstance(r, dict):
            continue
        ici = e["records"].get(typ)
        st = float(r.get("t", 0) or 0)
        if st <= 0:
            continue
        if ici is None or st < ici["t"] - 0.05:
            e["records"][typ] = {"t": st, "d": r.get("d", 0), "g": "", "n": 0, "v": bool(r.get("v"))}
        elif abs(st - ici["t"]) <= 0.05:
            ici["v"] = bool(r.get("v"))
    ids = {r.get("id") for r in envoyes}
    e["envoyer"] = [r for r in e["envoyer"] if r.get("id") not in ids]
    if isinstance(extra, dict):
        if isinstance(extra.get("hebdo"), dict):
            e["hebdo"] = extra["hebdo"]
        if isinstance(extra.get("compte"), dict):
            e["hebdo_compte"] = extra["compte"]
    return {f: {k: int((fs.get(f) or {}).get(k, 0)) for k in ("n",) + MEDAILLES} for f in B.FAMILLES}
