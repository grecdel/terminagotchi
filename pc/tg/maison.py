"""La maison : les pièces sont de vrais dossiers du terrain, la carte se dévoile en les visitant.

  ~/terrain_terminagotchi/            la grande salle
      vestibule/                      chapitre 1 (l'œuf)
      nid/                            chapitre 2
      grenier/ cave/ bibliotheque/ salle_des_machines/ dortoir/ atelier/ tour/   chapitres 3 à 9
      coeur/                          chapitre 10 (ouvert quand 5 ailes sont réveillées)
      (plus des sous-pièces, des couloirs et des pièces secrètes « .cachette »)

Où est l'enfant ? Le dossier courant vient de deux sources :
  1. l'invite du shell : le compagnon (tg prompt) tourne DANS le dossier du terminal, os.getcwd()
     donne le vrai dossier courant à chaque invite (compagnon.prompt le passe à app.etape) ;
  2. l'historique : chaque « cd » est rejoué depuis le dernier dossier connu (cd, cd ~, cd .., cd -,
     chemins relatifs ou absolus, « cd a && ls »). Sert entre deux invites, et sans compagnon.
Une pièce est « visitée » quand on y est vraiment entré (cd). La carte ne montre que celles-là.

Terres sauvages : tout ce qui est hors de la maison du jeu (/etc…). On peut y regarder (lecture
seule), le jeu prévient : on ne touche à rien là-bas. Le jeu n'y écrit jamais rien.
"""
import os
import re
import time
from pathlib import Path

from . import core
from .langue import ajuster, largeur, raccourcir, t
from .plateforme import BOLD, DIM, RESET, fg

AILES = ("grenier", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier", "tour")
PIECES = ("vestibule", "nid") + AILES + ("coeur",)
ICONES = {"vestibule": "🥚", "nid": "🏠", "grenier": "🌿", "cave": "🔒", "bibliotheque": "📚",
          "salle_des_machines": "🔥", "dortoir": "👻", "atelier": "🔧", "tour": "📡", "coeur": "💜",
          "recoins": "🚪", "sauvage": "🌲", "jardin": "📱"}
# le plan : 4 étages de 3 pièces (le grenier et la tour en haut, la cave au sous-sol)
PLAN = (("grenier", "bibliotheque", "tour"),
        ("dortoir", "coeur", "atelier"),
        ("vestibule", "nid", "salle_des_machines"),
        ("recoins", "cave", "sauvage"))
LARGE = 20                       # colonnes d'une case de la carte
PRUDENCE = ("rm", "rmdir", "mv", "chmod", "chown", "del", "remove-item", "move-item", "ren")


def T():
    return core.TERRAIN


def m_(state):
    return state.setdefault("maison", {"visites": [], "cwd": None, "sauvage": [], "averti": 0, "prudence": 0})


def nom_piece(p):
    return t("carte.piece." + p)


def rel(chemin):
    """Le chemin d'un dossier dans la maison (« grenier/fouillis », « » pour la grande salle), ou None."""
    try:
        r = Path(os.path.normpath(str(chemin))).relative_to(T())
    except (ValueError, TypeError):
        return None
    s = r.as_posix()
    return "" if s == "." else s


def dans(cwd, piece):
    """Vrai si le dossier cwd est la pièce (ou une de ses sous-pièces). piece = « » : la grande salle."""
    r = rel(cwd) if cwd else None
    if r is None:
        return False
    return piece == "" or r == piece or r.startswith(piece + "/")


def ici(state):
    """Le dernier dossier courant connu (texte absolu) ou None."""
    return m_(state).get("cwd")


def piece_de(state):
    r = rel(ici(state)) if ici(state) else None
    return None if r is None else (r.split("/")[0] if r else "")


# ---------------------------------------------------------------- suivre les « cd »
_SEP = re.compile(r"\s*(?:&&|\|\||;)\s*")
_CD = re.compile(r"^(cd|set-location|sl|chdir|pushd)(?:\s+(.*))?$", re.I)


def _resoudre(cur, arg, precedent):
    home = Path.home()
    arg = (arg or "").strip()
    if arg.lower().startswith("-path "):
        arg = arg[6:].strip()
    arg = arg.strip("'\"")
    if arg in ("", "~"):
        return str(home)
    if arg == "-":
        return precedent or cur
    if arg.startswith("~/") or arg.startswith("~\\"):
        p = home / arg[2:]
    elif arg.startswith("~"):
        return cur
    elif os.path.isabs(arg):
        p = Path(arg)
    else:
        p = Path(cur) / arg
    p = Path(os.path.normpath(str(p)))
    return str(p) if p.is_dir() else cur          # cd raté : on reste où on est


def rejouer(cur, ligne, precedent=None):
    """Le dossier après cette ligne (en rejouant ses « cd »)."""
    for morceau in _SEP.split(ligne.strip()):
        m = _CD.match(morceau.strip())
        if m:
            cur, precedent = _resoudre(cur, m.group(2), precedent), cur
    return cur


def _visiter(state, cwd):
    m = m_(state)
    r = rel(cwd)
    if r is None:
        if not str(cwd).startswith(str(Path.home())) and str(cwd) not in m["sauvage"]:
            m["sauvage"] = (m["sauvage"] + [str(cwd)])[-20:]
            avertir_sauvage(state)
        return
    if r not in m["visites"]:
        m["visites"].append(r)
        del m["visites"][:-300]


def avertir_sauvage(state):
    m = m_(state)
    if time.time() - m.get("averti", 0) > 600:
        m["averti"] = time.time()
        core.say(state, t("carte.sauvage.dit"), 12)


def _prudence(state, ligne, cwd):
    """Une commande qui casse ou modifie, tapée hors de la maison du jeu : un petit rappel."""
    mots = ligne.split()
    if not mots or mots[0].lower() not in PRUDENCE:
        return
    hors = rel(cwd) is None if cwd else False
    for x in mots[1:]:
        if x.startswith(("/", "~")) and "terrain_terminagotchi" not in x:
            hors = True
    m = m_(state)
    if hors and time.time() - m.get("prudence", 0) > 120:
        m["prudence"] = time.time()
        core.say(state, t("carte.prudence.dit", terrain=f"~/{T().name}"), 12)


def suivre(state, lignes, cwd=None):
    """Rejoue les « cd » de l'historique ; cwd (donné par l'invite) corrige à la fin.
    Renvoie le dossier courant après chaque ligne (même ordre que lignes)."""
    m = m_(state)
    cur = m.get("cwd") or str(Path.home())
    apres = []
    for l in lignes:
        if not core.est_colle(l):
            avant = cur
            cur = rejouer(cur, l, m.get("precedent"))
            if cur != avant:
                m["precedent"] = avant
            _visiter(state, cur)
            _prudence(state, l, cur)
            for x in l.split()[1:]:
                if x.startswith("/") and not x.startswith(str(Path.home())) and os.path.exists(x):
                    avertir_sauvage(state)              # regarder un fichier du système (lecture seule)
                    if "/etc" not in m["sauvage"]:
                        m["sauvage"].append("/etc" if x.startswith("/etc") else os.path.dirname(x) or "/")
                    break
        apres.append(cur)
    if cwd:
        try:
            cur = str(Path(cwd))
        except (TypeError, ValueError):
            pass
        _visiter(state, cur)
    m["cwd"] = cur
    return apres


# ---------------------------------------------------------------- la carte
def visitee(state, p):
    v = m_(state)["visites"]
    return any(x == p or x.startswith(p + "/") for x in v)


def _secrets(state):
    from . import quetes
    return quetes.secrets(state)


def marques(state, p):
    """Les petits signes d'une pièce : ◉ tu es ici, ✓ réveillée, ★ quête, 🐾 monstres."""
    from . import histoire, quetes
    s = ""
    if piece_de(state) == p:
        s += "◉"
    ch = histoire.chapitre_de_piece(p)
    if ch and ch["id"] in histoire.h_(state)["ailes"]:
        s += "✓"
    elif ch and histoire.h_(state).get("chap") == ch["id"]:
        s += "▶"
    if quetes.etoile(state, p):
        s += "★"
    fam = ch.get("famille") if ch else None
    if fam and any(_famille(x) == fam for x in state.get("sauvages", [])):
        s += "🐾"
    return s


def _famille(sauvage):
    from . import bestiaire as B
    e = B.espece(sauvage.get("e"))
    return e["famille"] if e else None


def _autres(state):
    """Les autres dossiers visités (couloirs, repaires des monstres, pièces inventées)."""
    return sorted({v.split("/")[0] for v in m_(state)["visites"] if v and v.split("/")[0] not in PIECES})


def _case(state, p):
    """Deux lignes de texte pour une case du plan."""
    from . import histoire
    if p == "recoins":
        autres = _autres(state)
        if not autres:
            return "░" * (LARGE - 2), ""
        return f"{ICONES[p]} {nom_piece(p)}", t("carte.recoins.n", n=len(autres)) + \
            (" 🐾" if state.get("sauvages") else "")
    if p == "sauvage":
        if not m_(state)["sauvage"]:
            return "░" * (LARGE - 2), ""
        return f"{ICONES[p]} {nom_piece(p)}", "⚠"
    if not histoire.piece_ouverte(state, p):
        return "", ""
    if not visitee(state, p):
        return "░" * (LARGE - 2), "?" + ("★" if p == "vestibule" else "")
    return f"{ICONES.get(p, '')} {nom_piece(p)}", marques(state, p)


def _ajuste(x):
    return ajuster(raccourcir(x, LARGE - 2), LARGE - 2)


def carte(state):
    """Le plan ASCII de la maison, avec le brouillard."""
    from . import histoire
    h = "─" * LARGE
    lignes = [f" {fg(213)}── 🗺  " + t("carte.titre", nom=state["name"]) + f" ──{RESET}", ""]
    lignes.append(" ┌" + "┬".join([h] * 3) + "┐")
    for i, rang in enumerate(PLAN):
        cases = [_case(state, p) for p in rang]
        for k in (0, 1):
            morceaux = []
            for p, c in zip(rang, cases):
                txt = _ajuste(c[k])
                if k == 0 and c[0] and not c[0].startswith("░"):
                    txt = BOLD + txt + RESET
                elif c[0].startswith("░"):
                    txt = DIM + txt + RESET
                morceaux.append(" " + txt + " ")
            lignes.append(" │" + "│".join(morceaux) + "│")
        if i < len(PLAN) - 1:
            lignes.append(" ├" + "┼".join([h] * 3) + "┤")
    lignes.append(" └" + "┴".join([h] * 3) + "┘")
    lignes.append(f" {DIM}" + t("carte.legende") + RESET)
    lignes.append("")
    r = rel(ici(state)) if ici(state) else None
    if r is not None:
        lignes.append(" ◉ " + t("carte.ici", lieu=(f"~/{T().name}/{r}" if r else f"~/{T().name}")))
    elif ici(state):
        lignes.append(" ◉ " + t("carte.dehors", lieu=ici(state)))
    trouves, total = _secrets(state)
    lignes.append(" " + t("carte.secrets", n=trouves, total=total))
    sous = {}
    for v in m_(state)["visites"]:
        if "/" in v and v.split("/")[0] in PIECES:
            p, reste = v.split("/", 1)
            sous.setdefault(p, set()).add(reste.split("/")[0])
    for p in PIECES:
        if p in sous:
            lignes.append(f"   {DIM}{nom_piece(p)} :{RESET} " + raccourcir(", ".join(sorted(sous[p])), 60))
    autres = _autres(state)
    if autres:
        lignes.append(f"   {DIM}{nom_piece('recoins')} :{RESET} " + raccourcir(", ".join(autres), 60))
    if m_(state)["sauvage"]:
        lignes.append(f"   {DIM}{nom_piece('sauvage')} :{RESET} " + raccourcir(", ".join(m_(state)["sauvage"][-4:]), 60)
                      + f" {DIM}" + t("carte.sauvage.lecture") + RESET)
    if not histoire.piece_ouverte(state, "vestibule"):
        lignes.append(" " + t("carte.vide"))
    return lignes


def largeur_carte():
    return 3 * LARGE + 4


def verifier_largeur(lignes):
    """Pour les tests : toutes les lignes du plan ont la même largeur à l'écran."""
    import re as _re
    propres = [_re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", l) for l in lignes if l.startswith((" │", " ┌", " ├", " └"))]
    return {largeur(l) for l in propres}
