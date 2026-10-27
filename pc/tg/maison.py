"""Le monde à explorer : les lieux sont de vrais dossiers du terrain, la carte pousse au fil des découvertes.

  ~/terrain_terminagotchi/            le camp de base
      vestibule/                      chapitre 1 (l'œuf)
      nid/                            chapitre 2
      grenier/ cave/ bibliotheque/ salle_des_machines/ dortoir/ atelier/ tour/   chapitres 3 à 9
      coeur/                          chapitre 10 (ouvert quand 5 ailes sont réveillées)
      biome/<type>/parcelle_<n>/      la porte du monde, ses régions et leurs parcelles
      (plus les lieux inventés par l'enfant, et des passages secrets « .cachette »)

Dossier = lieu, fichier = objet, dossier caché = passage secret, `tree` = la carte du monde.

Où est l'enfant ? Le dossier courant vient de deux sources :
  1. l'invite du shell : le compagnon (tg prompt) tourne DANS le dossier du terminal, os.getcwd()
     donne le vrai dossier courant à chaque invite (compagnon.prompt le passe à app.etape) ;
  2. l'historique : chaque « cd » est rejoué depuis le dernier dossier connu (cd, cd ~, cd .., cd -,
     chemins relatifs ou absolus, « cd a && ls »). Sert entre deux invites, et sans compagnon.
Un lieu est « visité » quand on y est vraiment entré (cd).

La carte qui pousse (carte, tg carte) : le VRAI terrain, dessiné à gauche (une tuile par lieu, un objet par
fichier) et la sortie de `tree` à droite, ligne par ligne. Elle ne montre que ce que l'enfant a découvert :
  - un lieu visité (ou montré par `tree`) dévoile ce qu'il contient ; un lieu jamais visité reste dans la
    brume (░ ???) ; les passages secrets (.cachés) n'apparaissent qu'après `ls -a` ;
  - ce qui apparaît pour la première fois brille (✨ nouveau !) ; ◉ = tu es ici ;
  - sous la carte, la légende ne liste que les commandes déjà rencontrées (en vert).
Après mkdir, touch, rm, mv, cp, une ligne « 🗺 la carte a poussé : + parcelle_3/ » passe dans l'invite.
Le même modèle est porté sur Android (Maison.kt, dessiné par CarteVue.kt).

Le Terminaworld, c'est TOUT l'ordinateur (docs/programme.md § 2.0 bis, décision du propriétaire) :
  /                          la Racine (le pied du grand arbre, d'où partent tous les chemins)
  /home                      le village
  ~ (/home/<nom>)            ton camp de base
  ~/terrain_terminagotchi    la zone d'aventure : le SEUL lieu où le jeu fait bâtir et détruire
  /etc                       la salle des règles du monde
  /bin, /usr                 l'armurerie des commandes
  /tmp                       le terrain vague (il s'efface tout seul)
  /var/log                   les archives
  /dev, /proc                les lieux magiques (portails des machines, miroir des habitants)
La carte (monde) part de la Racine : les lieux du système sont des repères fixes, dans la brume tant qu'on ne les a
pas visités ; le chemin descend jusqu'au camp de base puis à la zone d'aventure. Les lieux du système se visitent en
lecture seule : le jeu n'y écrit jamais et prévient gentiment si l'enfant essaie d'y écrire (prudence).
"""
import os
import re
import shutil
import sys
import time
from pathlib import Path

from . import core
from .langue import ajuster, couleurs, largeur, raccourcir, t
from .plateforme import BOLD, DIM, RESET, fg

AILES = ("grenier", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier", "tour")
PIECES = ("vestibule", "nid") + AILES + ("coeur",)
ICONES = {"vestibule": "🥚", "nid": "🏠", "grenier": "🌿", "cave": "🔒", "bibliotheque": "📚",
          "salle_des_machines": "🔥", "dortoir": "👻", "atelier": "🔧", "tour": "📡", "coeur": "💜",
          "recoins": "🚪", "sauvage": "🌲", "jardin": "📱"}
PRUDENCE = ("rm", "rmdir", "mv", "chmod", "chown", "del", "remove-item", "move-item", "ren")
# les commandes qui écrivent (prudence) : tous leurs chemins comptent, sauf pour cp (seulement la destination)
ECRIT = PRUDENCE + ("mkdir", "md", "touch", "new-item", "ni", "cp", "copy", "copy-item", "ln", "tee", "truncate",
                    "set-content", "add-content", "out-file")

# ---------------------------------------------------------------- le Terminaworld = tout le système de fichiers
# Les lieux du système, repères fixes sous la Racine (nom du dossier, lieu) ; textes lieu.<lieu>.nom / .i / .t.
LIEUX_SYSTEME = (("bin", "armurerie"), ("dev", "portails"), ("etc", "regles"), ("proc", "miroir"), ("tmp", "vague"),
                 ("usr", "armurerie"), ("var/log", "archives"))
# leurs icônes (emojis larges de 2 colonnes : cases alignées)
ICONES_LIEUX = {"racine": "🌳", "village": "🏡", "camp": "⛺", "zone": "🎒", "chemin": "🌿", "armurerie": "🧰",
                "portails": "🔌", "regles": "📋", "miroir": "🔮", "vague": "🍂", "archives": "📓", "systeme": "📁"}
# le carnet des lieux (lexique) : chemin, lieu
LIEUX_CARNET = (("/", "racine"), ("/home", "village"), ("~", "camp"), ("~/terrain_terminagotchi", "zone"),
                ("/etc", "regles"), ("/bin, /usr", "armurerie"), ("/tmp", "vague"), ("/var/log", "archives"),
                ("/dev", "portails"), ("/proc", "miroir"))
# les écritures permises hors de la zone d'aventure : les réglages du camp que les leçons font écrire
REGLAGES = (".bashrc", ".zshrc", ".bash_aliases", ".profile", ".tgrc", ".gitconfig")

# ---------------------------------------------------------------- le monde dessiné
# Les régions du monde (donnees/biomes.json : id → emoji, couleur principale, sombre, claire ; vérifié par
# pc/outils/test_carte.py). Emojis larges de 2 colonnes (❄ ⛰ ⚙ n'en font qu'une : 🧊 🗻 🔩 à la place).
BIOMES = {
    "feu": ("🔥", "#e8562a", "#3a2a30", "#ffb347"),
    "eau": ("💧", "#2f7fc4", "#1d4f7a", "#7cc7ff"),
    "glace": ("🧊", "#9fd8f2", "#5689a3", "#f5fbff"),
    "plante": ("🌿", "#5aa63a", "#2f6b2c", "#86d45a"),
    "roche": ("🗻", "#c9a26a", "#7d828a", "#efdb9c"),
    "ciel": ("⚡", "#dfe9ff", "#8b9ac4", "#ffffff"),
    "ombre": ("🌙", "#4b3a6b", "#251c38", "#8f7bc0"),
    "machine": ("🔩", "#8a96a3", "#4a525c", "#c9d2db"),
    "poison": ("🧪", "#6a8f2a", "#3b4a1c", "#b6ff4a"),
}
# les lieux de l'histoire : (dessus, côté) de leur tuile
SOLS_PIECES = {
    "vestibule": ("#d9b47a", "#7b5534"), "nid": ("#c9a26a", "#6b4a2c"), "grenier": ("#5aa63a", "#2f6b2c"),
    "cave": ("#8d929a", "#5d6168"), "bibliotheque": ("#a8743f", "#5a381e"), "salle_des_machines": ("#e8562a", "#3a2a30"),
    "dortoir": ("#4b3a6b", "#251c38"), "atelier": ("#c9a26a", "#7d828a"), "tour": ("#dfe9ff", "#8b9ac4"),
    "coeur": ("#ff6fa8", "#7a2a55"), "jardin": ("#66b843", "#6b4a2c"),
}
SOLS = {"camp": ("#d9b47a", "#7b5534"), "lieu": ("#5aa63a", "#6b4a2c"), "porte": ("#8fa9c2", "#3d5a73"),
        "secret": ("#4b3a6b", "#251c38"), "brume": ("#6a6f78", "#3a3d44"),
        # la Racine (bois), le village, ton camp de base, la zone d'aventure, les lieux du système (pierre)
        "racine": ("#8a5a30", "#4a2e18"), "village": ("#e0c48a", "#8a6a3a"), "camp_base": ("#d9b47a", "#7b5534"),
        "zone": ("#86d45a", "#2f6b2c"), "chemin": ("#9cc4aa", "#4c6a58"), "systeme": ("#a7acb4", "#5d6168")}
EMOJIS = {"camp": "⛺", "porte": "🌀", "lieu": "🌳", "note": "📜", "recette": "📝", "image": "🌅", "coffre": "📦",
          "secret": "🔑", "secret_objet": "🔑", "brume": "░░", "suite": "··"}
TEXTES = {".txt", ".md", ".log", ".csv", ".json", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".html", ".xml", ""}
SCRIPTS = {".sh", ".ps1", ".py", ".bat", ".cmd", ".bash", ".zsh", ".fish", ".js", ".rb", ".pl"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tif", ".tiff"}
PROFONDEUR = 5            # niveaux montrés sous le camp de base
MAX_PAR_DOSSIER = 16      # au-delà : une ligne « + n autres… »
MAX_LIGNES = 150
TROP_GRAND = 200          # un dossier plus grand n'est pas exploré (on ne lit pas un dossier géant)
IGNORES = {".git", "node_modules", "__pycache__", ".cache", "venv", ".venv", ".gradle", "build"}
SEP = "┃"                 # entre le dessin et `tree` (mode colonnes)
LARGE_DESSIN = 34         # colonnes du dessin, au plus
# la légende : les commandes du monde, dans l'ordre où on les apprend, avec leurs synonymes (Windows, alias)
LEGENDE = (("pwd", ("pwd", "get-location", "gl")), ("ls", ("ls", "dir", "gci", "get-childitem", "ll", "la")),
           ("cd", ("cd", "set-location", "sl", "chdir", "pushd")), ("mkdir", ("mkdir", "md")),
           ("touch", ("touch", "new-item", "ni")), ("cp", ("cp", "copy", "copy-item")),
           ("mv", ("mv", "move", "move-item", "ren", "rename-item")),
           ("rm", ("rm", "rmdir", "rd", "del", "remove-item")), ("tree", ("tree",)), ("ls_a", ()))
CHANGE = {"mkdir", "md", "touch", "new-item", "ni", "rm", "rmdir", "rd", "del", "remove-item", "mv", "move",
          "move-item", "ren", "rename-item", "cp", "copy", "copy-item", "tar", "unzip", "git"}


def T():
    return core.TERRAIN


def m_(state):
    m = state.setdefault("maison", {"visites": [], "cwd": None, "sauvage": [], "averti": 0, "prudence": 0})
    for k in ("montres", "arbres"):
        m.setdefault(k, [])
    m.setdefault("ls_a", False)
    return m


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
_LS = ("ls", "dir", "gci", "get-childitem", "ll", "la")


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


def voit_caches(morceau):
    """`ls -a`, `ls -la`, `ls -A`, `dir /a`, `gci -force` : une commande qui montre les fichiers cachés."""
    mots = morceau.split()
    if not mots or mots[0].lower() not in _LS:
        return False
    for w in mots[1:]:
        lw = w.lower()
        if lw in ("--all", "--almost-all", "-force", "/a") or lw.startswith("/a:"):
            return True
        if w.startswith("-") and not w.startswith("--") and ("a" in w[1:] or "A" in w[1:]) and w[1:].isalpha() \
                and len(w) <= 6:
            return True
    return False


def _noter(state, ligne, cur, precedent):
    """Ce que la ligne apprend à la carte : `ls -a` (les passages secrets), `tree` (la carte d'un coin)."""
    m = m_(state)
    for morceau in _SEP.split(ligne.strip()):
        mc = _CD.match(morceau.strip())
        if mc:
            cur, precedent = _resoudre(cur, mc.group(2), precedent), cur
            continue
        if voit_caches(morceau):
            m["ls_a"] = True
        mots = morceau.split()
        if mots and mots[0].lower() == "tree":
            cible = next((w for w in mots[1:] if not w.startswith("-")), None)
            d = _resoudre(cur, cible, precedent) if cible else cur
            r = rel(d)
            if r is not None and r not in m["arbres"]:
                m["arbres"] = (m["arbres"] + [r])[-40:]
            if any(w.startswith("-") and "a" in w[1:] for w in mots[1:]):
                m["ls_a"] = True


def racine():
    """La Racine du système de fichiers : / (ou C:\\ sous Windows)."""
    return Path(Path.home().anchor or "/")


def chaine():
    """Le chemin de la Racine jusqu'au camp de base : [(dossier, lieu)], lieu = racine, chemin (un dossier de
    passage, comme /var dans /var/home/lou), village (le parent du camp, /home) ou camp (~)."""
    home = Path.home()
    parts = home.parts
    out = [(Path(parts[0]), "racine")]
    p = Path(parts[0])
    for i, x in enumerate(parts[1:], 1):
        p = p / x
        out.append((p, "camp" if i == len(parts) - 1 else "village" if i == len(parts) - 2 else "chemin"))
    return out


def _sous(chemin, dossier):
    c, d = os.path.normpath(str(chemin)), os.path.normpath(str(dossier))
    return c == d or c.startswith(d.rstrip(os.sep) + os.sep)


def lieu_de(chemin):
    """Le lieu du Terminaworld d'un chemin absolu : « zone » (et ce qu'elle contient), camp, village, racine, un lieu
    du système (regles, armurerie…), « chemin » (un dossier de passage vers le camp) ou « systeme » (ailleurs)."""
    if chemin is None:
        return None
    c = os.path.normpath(str(chemin))
    if rel(c) is not None:
        return "zone"
    for p, lieu in reversed(chaine()):
        if c == os.path.normpath(str(p)):
            return lieu
    if _sous(c, Path.home()):
        return "camp"
    for nom, lieu in LIEUX_SYSTEME:
        if _sous(c, racine() / nom):
            return lieu
    return "systeme"


def nom_lieu(lieu):
    return t(f"lieu.{lieu}.nom")


def hors_zone(chemin):
    """« camp » : dans le camp de base mais pas dans la zone d'aventure ; « systeme » : hors du camp ; None : dans la
    zone (ou /dev/null, le trou noir où l'on peut tout jeter)."""
    c = os.path.normpath(str(chemin))
    if rel(c) is not None or c in (os.devnull, "/dev/null"):
        return None
    return "camp" if _sous(c, Path.home()) else "systeme"


def _visiter(state, cwd):
    m = m_(state)
    r = rel(cwd)
    if r is None:
        if not _sous(cwd, Path.home()) or os.path.normpath(str(cwd)) == os.path.normpath(str(Path.home().parent)):
            nouveau = str(cwd) not in m["sauvage"]
            if nouveau:
                m["sauvage"] = (m["sauvage"] + [str(cwd)])[-20:]
            visiter_systeme(state, cwd, nouveau)
        return
    if r not in m["visites"]:
        m["visites"].append(r)
        del m["visites"][:-300]


def visiter_systeme(state, chemin, nouveau=True):  # noqa: ARG001 (nouveau : gardé pour les appels)
    """Un lieu du système visité : la 1re fois, la créature le présente (enfant + grands) ; ensuite, un rappel
    « on regarde, on ne touche pas » de temps en temps."""
    m = m_(state)
    lieu = lieu_de(chemin)
    deja = m.setdefault("lieux", [])
    if lieu and lieu not in deja and lieu not in ("zone", "camp", "chemin"):
        deja.append(lieu)
        m["averti"] = time.time()
        core.say(state, t("carte.lieu.decouvert", icone=ICONES_LIEUX.get(lieu, "📁"), nom=nom_lieu(lieu),
                          image=t(f"lieu.{lieu}.i")), 14)
        core.say(state, t("grand.ligne", texte=t(f"lieu.{lieu}.t")), 16)
        return
    avertir_sauvage(state)                      # (une fois toutes les 10 minutes au plus)


def avertir_sauvage(state):
    m = m_(state)
    if time.time() - m.get("averti", 0) > 600:
        m["averti"] = time.time()
        core.say(state, t("carte.sauvage.dit"), 12)


def _cibles(ligne, cwd):
    """Les chemins qu'une commande va écrire : (mot tapé, chemin absolu) ; les > et >> comptent aussi."""
    out = []
    base = Path(cwd) if cwd else Path.home()

    def absolu(x):
        x = x.strip("'\"")
        if x.startswith("~"):
            return Path(os.path.expanduser(x))
        return Path(x) if os.path.isabs(x) else base / x
    for morceau in _SEP.split(ligne.strip()):
        for m in re.finditer(r"(?<![0-9&])>>?\s*([^\s|;&<>]+)", morceau):
            out.append((m.group(1), absolu(m.group(1))))
        mots = re.sub(r"\d?>>?\s*[^\s|;&<>]+", " ", morceau.split("|")[0]).split()
        if not mots or mots[0].lower() not in ECRIT:
            continue
        args = [x for x in mots[1:] if not x.startswith("-") and not re.fullmatch(r"[0-7]{3,4}|[ugoa]*[+=-][rwxst]+", x)]
        if mots[0].lower() in ("cp", "copy", "copy-item", "ln"):
            args = args[-1:]
        out += [(x, absolu(x)) for x in args]
    return out


def _prudence(state, ligne, cwd):
    """Une commande qui écrit hors de la zone d'aventure : un rappel gentil. Dans un lieu du système, « on regarde,
    on ne touche pas » (et le gardien dirait non de toute façon) ; dans le camp de base, « seulement dans la zone
    d'aventure ». Les réglages du camp que les leçons font écrire (~/.bashrc…) ne comptent pas."""
    pire = None
    for mot, chemin in _cibles(ligne, cwd):
        h = hors_zone(chemin)
        if h == "camp" and (chemin.name in REGLAGES and chemin.parent == Path.home() or ".config" in chemin.parts):
            continue
        if h == "systeme" or (h == "camp" and pire is None):
            pire = (h, mot, chemin)
    if not pire:
        return None
    m = m_(state)
    if time.time() - m.get("prudence", 0) <= 120:
        return pire[0]
    m["prudence"] = time.time()
    if pire[0] == "systeme":
        core.say(state, t("carte.prudence.systeme", lieu=nom_lieu(lieu_de(pire[2])), chemin=str(pire[2])), 14)
        core.terminal(state, t("carte.prudence.systeme", lieu=nom_lieu(lieu_de(pire[2])), chemin=str(pire[2])))
        core.say(state, t("grand.ligne", texte=t("carte.prudence.adulte")), 16)
    else:
        core.say(state, t("carte.prudence.dit", terrain=f"~/{T().name}"), 12)
        core.terminal(state, t("carte.prudence.dit", terrain=f"~/{T().name}"))     # tout de suite, sous la commande (P1-4)
    return pire[0]


def suivre(state, lignes, cwd=None):
    """Rejoue les « cd » de l'historique ; cwd (donné par l'invite) corrige à la fin.
    Renvoie le dossier courant après chaque ligne (même ordre que lignes)."""
    m = m_(state)
    cur = m.get("cwd") or str(Path.home())
    apres = []
    change = False
    for l in lignes:
        if not core.est_colle(l):
            avant = cur
            _noter(state, l, cur, m.get("precedent"))
            cur = rejouer(cur, l, m.get("precedent"))
            if cur != avant:
                m["precedent"] = avant
            _visiter(state, cur)
            _prudence(state, l, cur)
            change = change or any((core.first_word(x) or "") in CHANGE for x in _SEP.split(l.strip()))
            for x in l.split()[1:]:
                x = x.strip("'\"")
                if os.path.isabs(x) and not _sous(x, Path.home()) and os.path.exists(x):
                    d = x if os.path.isdir(x) else os.path.dirname(x) or "/"
                    nouveau = d not in m["sauvage"]       # regarder un lieu du système (lecture seule)
                    if nouveau:
                        m["sauvage"] = (m["sauvage"] + [d])[-20:]
                    visiter_systeme(state, d, nouveau)
                    break
        apres.append(cur)
    if cwd:
        try:
            cur = str(Path(cwd))
        except (TypeError, ValueError):
            pass
        _visiter(state, cur)
    m["cwd"] = cur
    if change or "empreinte" not in m:
        pousse(state)
    return apres


# ---------------------------------------------------------------- la carte a poussé
def empreinte(state):
    """Les chemins du terrain (sans les cachés tant que `ls -a` n'est pas connu), sur PROFONDEUR niveaux."""
    vus = set()
    voir_caches = m_(state)["ls_a"]

    def tour(d, r, n):
        if n > PROFONDEUR or len(vus) > 600:
            return
        try:
            with os.scandir(d) as it:
                entrees = list(it)
        except OSError:
            return
        if len(entrees) > TROP_GRAND:
            return
        for e in entrees:
            if e.name.startswith(".") and not voir_caches:
                continue
            try:
                dossier = e.is_dir(follow_symlinks=False)
            except OSError:
                dossier = False
            c = f"{r}/{e.name}" if r else e.name
            vus.add(c + ("/" if dossier else ""))
            if dossier and e.name not in IGNORES:
                tour(e.path, c, n + 1)
    if T().is_dir():
        tour(str(T()), "", 1)
    return vus


def pousse(state):
    """Compare le terrain à la dernière empreinte : « 🗺 la carte a poussé : + parcelle_3/ » (dans l'invite)."""
    m = m_(state)
    neuve = empreinte(state)
    vieille = m.get("empreinte")
    m["empreinte"] = sorted(neuve)[:400]
    if vieille is None:
        return None
    vieille = set(vieille)
    plus = sorted(x for x in neuve - vieille if not any(y != x and x.startswith(y) for y in neuve - vieille))
    moins = sorted(x for x in vieille - neuve if not any(y != x and x.startswith(y) for y in vieille - neuve))
    if not plus and not moins:
        return None

    def court(xs, signe):
        noms = [signe + " " + x.rstrip("/").split("/")[-1] + ("/" if x.endswith("/") else "") for x in xs[:3]]
        return noms + (["…"] if len(xs) > 3 else [])
    quoi = " ".join(court(plus, "+") + court(moins, "−"))
    msg = t("carte.monde.pousse" if plus else "carte.monde.retrecit", quoi=quoi)
    core.log(state, msg)
    return msg


# ---------------------------------------------------------------- ce que l'enfant a découvert
def visitee(state, p):
    v = m_(state)["visites"]
    return any(x == p or x.startswith(p + "/") for x in v)


def _secrets(state):
    from . import quetes
    return quetes.secrets(state)


def marques(state, p):
    """Les petits signes d'un lieu de l'histoire : ✓ réveillé, ▶ en cours, ★ quête, 🐾 monstres."""
    from . import histoire, quetes
    s = ""
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


def genre(r, dossier):
    """(genre, biome ou lieu de l'histoire) d'une entrée du terrain (r = chemin relatif)."""
    parts = r.split("/") if r else []
    nom = parts[-1] if parts else ""
    if not r:
        return "zone", None
    if nom.startswith("."):
        return ("secret" if dossier else "secret_objet"), None
    region = next((p for i, p in enumerate(parts) if i > 0 and parts[i - 1] == "biome" and p in BIOMES), None)
    if dossier:
        if r in PIECES or r == "jardin":
            return "piece", r
        if r == "biome":
            return "porte", None
        if len(parts) >= 2 and parts[-2] == "biome" and nom in BIOMES:
            return "region", nom
        if re.fullmatch(r"parcelle[_-]?\d*", nom.lower()):
            return "parcelle", region
        bas = nom.lower()
        if bas in ("camp", "nid", "base", "campement", "camp_de_base") or bas.startswith("camp"):
            return "camp", None
        return "lieu", region or next((b for b in BIOMES if b in bas), None)
    ext = os.path.splitext(nom)[1].lower()
    if ext in SCRIPTS:
        return "recette", region
    if ext in IMAGES:
        return "image", region
    if ext in TEXTES:
        return "note", region
    return "coffre", region


def etiquette(state, n):
    """Le nom dessiné à côté de la tuile."""
    g, b = n["genre"], n["biome"]
    if n["brume"]:
        return "???"
    if g == "suite":
        return t("carte.monde.autres", n=n["suite"])
    if g == "zone":
        return nom_lieu("zone")
    if n.get("lieu"):                                   # la Racine, le village, ton camp, les lieux du système
        return nom_lieu(n["lieu"]) if n["lieu"] != "chemin" else n["nom"]
    if g == "camp":
        return t("carte.monde.campement")
    if g == "piece":
        return nom_piece(b)
    if g == "region":
        return t("carte.monde.region", nom=t("carte.biome." + b))
    if g in ("porte", "lieu", "parcelle", "secret", "note", "recette", "image", "coffre"):
        return t("carte.monde." + g)
    if g == "secret_objet":
        return t("carte.monde.secret_objet")
    return n["nom"]


def garde(state, n):
    """Une région gardée (biome/<type>/ et ce qu'elle contient) : « fermee » si aucune bestiole de son type n'est dans
    l'équipe (guide.region_ouverte), « visite » si on peut y entrer mais pas l'agrandir (guide.peut_agrandir), sinon ""."""
    b = n["biome"]
    if not n["rel"].startswith("biome/") or b not in BIOMES or n["genre"] not in ("region", "parcelle", "lieu"):
        return ""
    from . import guide
    if not guide.region_ouverte(state, b):
        return "fermee"
    return "" if guide.peut_agrandir(state, b) else "visite"


def ouverts(state):
    """Les lieux dont on voit l'intérieur : visités (et leurs parents), montrés par `tree`, le camp de base."""
    m = m_(state)
    o = {""}
    for v in m["visites"]:
        parts = v.split("/") if v else []
        for i in range(len(parts) + 1):
            o.add("/".join(parts[:i]))
    return o, list(m["arbres"])


def noeuds(state, marquer=False):
    """Le monde découvert, ligne par ligne, dans l'ordre de `tree` (dict par ligne) :
    rel, nom, prof, dossier, genre, biome, brume, nouveau, ici, marques, branches (le début de la ligne de tree),
    etiquette. marquer=True : ce qui est montré n'est plus « nouveau » la fois suivante."""
    from . import histoire, quetes
    m = m_(state)
    o, arbres = ouverts(state)
    montres = set(m["montres"])
    voir_caches = m["ls_a"]
    vis = set(m["visites"])
    r_ici = rel(ici(state)) if ici(state) else None
    out = []

    def ouvert(r):
        return r in o or any(a == "" or r == a or r.startswith(a + "/") for a in arbres)

    def ligne(r, nom, prof, dossier, branches, brume, suite=0):
        g, b = ("suite", None) if suite else genre(r, dossier)
        cle = ("~" if brume else "") + r + ("/" if dossier else "")
        n = {"rel": r, "nom": nom, "prof": prof, "dossier": dossier, "genre": g, "biome": b, "brume": brume,
             "nouveau": bool(not suite and cle not in montres), "ici": False, "marques": "", "branches": branches,
             "suite": suite, "cle": cle}
        if g == "piece" and b in PIECES:
            n["marques"] = ("★" if quetes.etoile(state, b) else "") if brume else marques(state, b)
        n["garde"] = garde(state, n)
        n["etiquette"] = etiquette(state, n)
        out.append(n)
        return n

    def entrees(d):
        try:
            with os.scandir(d) as it:
                es = list(it)
        except OSError:
            return None
        if len(es) > TROP_GRAND:
            return None
        return sorted(es, key=lambda e: (e.name.lstrip(".").casefold(), e.name))

    def tour(d, r, prof, avant):
        es = entrees(d)
        if es is None:
            return
        garde = []
        for e in es:
            try:
                dossier = e.is_dir(follow_symlinks=False)
            except OSError:
                dossier = False
            c = f"{r}/{e.name}" if r else e.name
            if e.name.startswith(".") and not voir_caches and c not in vis:
                continue                              # un passage secret : il faut `ls -a`
            if prof == 1 and dossier and e.name in PIECES and not histoire.piece_ouverte(state, e.name):
                continue                              # pas encore posé par l'histoire
            garde.append((e, c, dossier))
        reste = 0
        if len(garde) > MAX_PAR_DOSSIER:              # trop de choses : d'abord ce qu'on connaît, la brume ensuite
            def rang(x):                              # lieux de l'histoire et lieux ouverts, passages, objets, brume
                e, c, dossier = x
                if dossier and (ouvert(c) or (prof == 1 and e.name in PIECES)):
                    return 0
                return 1 if e.name.startswith(".") else 2 if not dossier else 3
            choix = sorted(range(len(garde)), key=lambda i: (rang(garde[i]), i))[:MAX_PAR_DOSSIER - 1]
            reste = len(garde) - len(choix)
            garde = [garde[i] for i in sorted(choix)]
        for i, (e, c, dossier) in enumerate(garde):
            if len(out) >= MAX_LIGNES:
                return
            dernier = i == len(garde) - 1 and not reste
            dedans = dossier and ouvert(c)
            brume = dossier and not dedans and not e.name.startswith(".")    # un passage secret trouvé se voit
            ligne(c, e.name, prof, dossier, avant + ("└── " if dernier else "├── "), brume)
            if dedans and prof < PROFONDEUR and e.name not in IGNORES:
                tour(e.path, c, prof + 1, avant + ("    " if dernier else "│   "))
        if reste:
            ligne(r + "/…", "…", prof, False, avant + "└── ", False, suite=reste)

    ligne("", ".", 0, True, "", False)
    if T().is_dir():
        tour(str(T()), "", 1, "")
    # ◉ : la ligne du dossier courant (ou de son parent le plus proche qui est sur la carte)
    if r_ici is not None:
        par = {n["rel"]: n for n in out if n["dossier"]}
        x = r_ici
        while x not in par and x:
            x = x.rsplit("/", 1)[0] if "/" in x else ""
        if x in par:
            par[x]["ici"] = True
    if marquer:
        m["montres"] = (m["montres"] + [n["cle"] for n in out if n["nouveau"]])[-800:]
    return out


def monde(state, marquer=False):
    """Toute la carte du Terminaworld, depuis la Racine : la Racine, les lieux du système (repères fixes, dans la
    brume tant qu'ils ne sont pas visités), le chemin jusqu'au village et au camp de base, puis la zone d'aventure
    (les lignes de noeuds, décalées). Mêmes clés que noeuds() + « abs » (le chemin absolu) et « lieu »."""
    m = m_(state)
    zone = noeuds(state, marquer=marquer)
    vus = [os.path.normpath(v) for v in m["sauvage"]]
    montres = set(m["montres"])
    ch = chaine()
    out = []

    def ajouter(chemin, nom, prof, branches, genre, lieu, brume):
        cle = "@" + ("~" if brume else "") + str(chemin)
        n = {"rel": str(chemin), "abs": str(chemin), "nom": nom, "prof": prof, "dossier": True, "genre": genre, "biome": None,
             "lieu": lieu, "brume": brume, "nouveau": cle not in montres, "ici": False, "marques": "", "garde": "",
             "branches": branches, "suite": 0, "cle": cle}
        n["etiquette"] = "???" if brume else etiquette(state, n)
        out.append(n)
        return n

    ajouter(ch[0][0], str(ch[0][0]), 0, "", "racine", "racine", False)
    premier = ch[1][0].name if len(ch) > 1 else None
    for nom, lieu in LIEUX_SYSTEME:
        d = racine() / nom
        if nom.split("/")[0] == premier or not d.is_dir():
            continue
        vu = any(_sous(v, d) for v in vus)
        ajouter(d, nom, 1, "├── ", "systeme", lieu, not vu)
    avant = ""
    for k, (d, lieu) in enumerate(ch[1:], 1):
        ajouter(d, d.name, k, avant + "└── ", "camp_base" if lieu == "camp" else lieu, lieu, False)
        avant += "    "
    base = len(ch)
    for n in zone:
        n = dict(n)
        n["abs"] = str(T() / n["rel"]) if n["rel"] and n["genre"] != "suite" else str(T())
        if n["prof"] == 0:
            n["nom"], n["branches"] = T().name, avant + "└── "
        else:
            n["branches"] = avant + "    " + n["branches"]
        n["prof"] += base
        out.append(n)
    # ◉ hors de la zone : le lieu le plus proche sur la carte (la Racine au pire)
    ici_ = ici(state)
    if ici_ and rel(ici_) is None:
        proches = [n for n in out if n.get("lieu") and _sous(ici_, n["abs"])]
        if proches:
            max(proches, key=lambda n: len(n["abs"]))["ici"] = True
    if marquer:
        m["montres"] = (m["montres"] + [n["cle"] for n in out[:len(out) - len(zone)] if n["nouveau"]])[-800:]
    return out


def chemin_lieux(chemin):
    """« la Racine → le village → ton camp de base → la zone d'aventure → Grenier » : un chemin absolu lu lieu par
    lieu, comme une ligne de métro (le panneau de pwd)."""
    if not chemin:
        return ""
    c = Path(os.path.normpath(str(chemin)))
    morceaux = []
    p = None
    for x in c.parts:
        p = Path(x) if p is None else p / x
        lieu = lieu_de(p)
        r = rel(p)
        if r == "":
            morceaux.append(nom_lieu("zone"))
        elif r is not None:
            morceaux.append(nom_piece(r) if r in PIECES or r == "jardin" else x)
        elif lieu in ("racine", "village", "camp") and os.path.normpath(str(p)) in [os.path.normpath(str(d)) for d, _ in chaine()]:
            morceaux.append(nom_lieu(lieu))
        elif lieu not in ("chemin", "systeme", "camp") and any(os.path.normpath(str(racine() / n)) == os.path.normpath(str(p)) for n, _ in LIEUX_SYSTEME):
            morceaux.append(nom_lieu(lieu))
        elif not (p.name == "var" and lieu == "systeme" and len(c.parts) > 2 and c.parts[2] == "log"):
            morceaux.append(x)
    return " → ".join(morceaux)


def legende(state):
    """Les commandes du monde déjà rencontrées (dans l'ordre où on les apprend) : textes avec `…` en vert."""
    vues = {str(c).lower() for c in state.get("seen", [])}
    out = []
    for k, syn in LEGENDE:
        if (k == "ls_a" and m_(state)["ls_a"]) or any(s in vues for s in syn):
            out.append(t("carte.monde.cmd." + k))
    return out


# ---------------------------------------------------------------- l'affichage dans le terminal
def _rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _fg24(h):
    return "\033[38;2;%d;%d;%dm" % _rgb(h)


def _bg24(h):
    return "\033[48;2;%d;%d;%dm" % _rgb(h)


def sol(n, parent=None):
    """(dessus, côté) de la tuile d'une ligne."""
    g, b = n["genre"], n["biome"]
    if n["brume"] or n.get("garde") == "fermee":     # une région fermée est grise (comme la brume)
        return SOLS["brume"]
    if g == "piece":
        return SOLS_PIECES.get(b, SOLS["lieu"])
    if n.get("lieu") and g in ("systeme",):
        return SOLS["systeme"]
    if g in ("region", "parcelle", "lieu") and b in BIOMES:
        return BIOMES[b][1], BIOMES[b][2]
    if g in ("note", "recette", "image", "coffre", "secret_objet"):
        return parent or SOLS["lieu"]
    return SOLS.get(g, SOLS["lieu"])


def emoji(n):
    g, b = n["genre"], n["biome"]
    if n["brume"]:
        return EMOJIS["brume"]
    if n.get("lieu") or g == "zone":
        return ICONES_LIEUX.get(n.get("lieu") or "zone", "📁")
    if g == "piece":
        return ICONES.get(b, "🌳")
    if g in ("region", "parcelle") and b in BIOMES:
        return BIOMES[b][0]
    return EMOJIS.get(g, "🌳")


def _tuile(n, parents, couleur=True):
    """3 colonnes de demi-blocs : le dessus de la tuile sur son côté (un objet : posé sur le sol du lieu)."""
    if not couleur:
        return ""
    if n["brume"]:
        return DIM + "░░░" + RESET
    if not n["dossier"]:
        dessus, _ = sol(n, parents.get(n["prof"] - 1))
        return _fg24(dessus) + " ▄▄" + RESET
    dessus, cote = sol(n)
    return _fg24(dessus) + _bg24(cote) + "▀▀▀" + RESET


def _texte_tree(n, couleur=True):
    """La ligne de `tree` (avec / après les dossiers, comme `tree -F`)."""
    nom = n["nom"] + ("/" if n["dossier"] and n["nom"] not in (".", "/") and not n["nom"].endswith(("/", "\\")) else "")
    if n["genre"] == "suite":
        nom = "… " + t("carte.monde.autres", n=n["suite"])
    if couleur:
        c = DIM if n["brume"] or n["genre"] == "suite" or n.get("garde") == "fermee" else \
            fg(141) if n["genre"] in ("secret", "secret_objet") else \
            _fg24(BIOMES[n["biome"]][3]) if n["dossier"] and n["biome"] in BIOMES else \
            fg(214) if n["dossier"] else fg(252)
        nom = (BOLD if n["ici"] else "") + c + nom + RESET
    return DIM * couleur + n["branches"] + RESET * couleur + nom


def _signes(n, couleur=True):
    s = ""
    if n["marques"]:
        s += " " + n["marques"]
    if n.get("garde"):                       # 🔒 fermée / 👣 visite seulement (guide.py)
        from . import guide
        texte = t("carte.garde." + n["garde"], type=guide.etiquette(n["biome"]))
        s += " " + ((DIM if n["garde"] == "fermee" else fg(214)) + texte + RESET if couleur else texte)
    if n["ici"]:
        s += " " + (fg(84) if couleur else "") + "◉ " + t("carte.monde.ici") + (RESET if couleur else "")
    if n["nouveau"]:
        s += " " + (fg(226) if couleur else "") + "✨ " + t("carte.monde.nouveau") + (RESET if couleur else "")
    return s


def mode_auto():
    """« colonnes » (dessin + tree côte à côte) dans un vrai terminal en couleur assez large, sinon « texte »."""
    try:
        cols = shutil.get_terminal_size((80, 24)).columns
    except OSError:
        cols = 80
    return "colonnes" if couleurs(sys.stdout) and cols >= 76 else "texte"


def carte(state, mode=None):
    """La carte qui pousse : le dessin et `tree` côte à côte (mode « colonnes »), ou `tree` annoté (« texte »).
    Ce qui est montré ici n'est plus « nouveau » la fois suivante (l'appelant sauvegarde)."""
    from . import histoire
    mode = mode or mode_auto()
    couleur = mode == "colonnes"
    ns = monde(state, marquer=True)
    lignes = [f" {fg(213)}── 🗺  " + t("carte.monde.titre", nom=state["name"]) + f" ──{RESET}", ""]
    if couleur:
        parents = {}
        dessins = []
        for n in ns:
            if n["dossier"]:
                parents[n["prof"]] = sol(n)
            gauche = "  " * n["prof"] + _tuile(n, parents) + emoji(n) + " "
            reste = LARGE_DESSIN - largeur(gauche)
            lab = (DIM if n["brume"] or n.get("garde") == "fermee" else BOLD if n["dossier"] else "") \
                + raccourcir(n["etiquette"], max(4, reste)) + RESET
            dessins.append(gauche + lab)
        w = min(LARGE_DESSIN, max(largeur(d) for d in dessins))
        for n, d in zip(ns, dessins):
            lignes.append(" " + ajuster(d, w) + f" {DIM}{SEP}{RESET} " + _texte_tree(n) + _signes(n))
    else:
        for n in ns:
            lab = "░░░░ ???" if n["brume"] else emoji(n) + " " + n["etiquette"]
            if n["genre"] == "suite":
                lignes.append(" " + _texte_tree(n, False))
            else:
                lignes.append(" " + _texte_tree(n, False) + "  " + lab + _signes(n, False))
    lignes.append("")
    if ici(state):                    # le panneau de pwd : le chemin complet depuis la Racine, lu lieu par lieu
        lignes.append(" ◉ " + t("carte.ici", lieu=os.path.normpath(ici(state))))
        lignes.append(f"   {fg(84) if couleur else ''}🚇 " + chemin_lieux(ici(state)) + (RESET if couleur else ""))
    lignes.append(f" {DIM}" + t("carte.absolu") + RESET)
    lignes.append(f" {DIM}" + t("carte.legende") + RESET)
    leg = legende(state) or [t("carte.monde.legende.rien")]
    cur = " " + t("carte.monde.legende")
    for x in leg:                                 # la légende, coupée entre deux commandes (72 colonnes)
        if largeur(cur) + largeur(x) + 3 > 72 and cur.strip() != t("carte.monde.legende").strip():
            lignes.append(cur)
            cur = "  "
        cur += (" · " if not cur.endswith((" ", ":")) and cur.strip() else " ") + x
    lignes.append(cur)
    trouves, total = _secrets(state)
    lignes.append(" " + t("carte.secrets", n=trouves, total=total))
    lignes.append(f" {DIM}" + t("carte.sauvage.lecture") + RESET)
    if not histoire.piece_ouverte(state, "vestibule"):
        lignes.append(" " + t("carte.vide"))
    return lignes


def largeur_carte():
    return LARGE_DESSIN + 3 + 40


def verifier_largeur(lignes):
    """Pour les tests : en mode colonnes, `tree` commence à la même colonne sur toutes les lignes de la carte
    (renvoie l'ensemble des colonnes du séparateur ; en mode texte, il n'y a pas de colonnes : {0})."""
    propres = [re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", l) for l in lignes]
    pos = {largeur(l.split(SEP)[0]) for l in propres if SEP in l}
    return pos or {0}
