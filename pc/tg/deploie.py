"""La vue déployée d'une commande (`deploie <commande>`, `tg deploie …`, et toute seule dans les leçons).

La ligne se découpe en BLOCS colorés qui s'allument un par un, dans l'ordre où le shell les lit :
    commande     le premier mot d'une commande simple (vert)               cat, grep, ls
    option       ce qui commence par un tiret (orange)                     -i, -l, +x (chmod)
    argument     ce que la commande reçoit (bleu)                          gland (le mot cherché), 3
    chemin       un lieu ou un objet du Terminaworld (cyan)                lianes.txt, grenier/, ~, ..
    tuyau        |   la sortie d'une commande entre dans la suivante (violet)
    redirection  > >> < 2>   la sortie tombe dans un fichier (rose) ; le mot d'après est un chemin (rôle « cible »)
    lien         && || ; &   « puis », « si ça marche », « sinon », « en arrière-plan » (jaune)
Les TUYAUX sont animés : on y voit passer les vraies lignes (calculées seulement pour des commandes qui ne font que
lire : cat, ls, grep, head, wc…) ; les CHEMINS se relient au lieu de la carte ; une REDIRECTION montre les lignes qui
tombent dans le fichier. `deploie` ne lance jamais la commande (il l'explique) : les lignes du flux viennent de
commandes sans danger, sans leurs redirections.

Le découpage est le même sur Android (app/…/Deploie.kt) : vecteurs communs dans donnees/espace/vecteurs.json
(pc/outils/test_espace.py et tests/jvm/Espace.kt).
"""
import os
import re
import sys
import time

from .langue import brut, raccourcir, t
from .plateforme import BOLD, DIM, RESET, fg

GENRES = ("commande", "option", "argument", "chemin", "tuyau", "redirection", "lien")
# couleurs (r, g, b) des fenêtres et du téléphone, et 256 couleurs du terminal
COULEURS = {"commande": (61, 220, 132), "option": (255, 159, 67), "argument": (95, 175, 255),
            "chemin": (77, 208, 225), "tuyau": (178, 132, 255), "redirection": (255, 121, 198),
            "lien": (255, 213, 79)}
ANSI = {"commande": 78, "option": 214, "argument": 75, "chemin": 80, "tuyau": 141, "redirection": 211, "lien": 221}

OPERATEURS = ("2>>", "2>", "&>", ">>", "||", "&&", ">", "<", "|", ";", "&")
REDIRECTIONS = {">": "ecrase", ">>": "ajoute", "<": "entree", "2>": "erreurs", "2>>": "erreurs", "&>": "tout"}
LIENS = {"&&": "et", "||": "ou", ";": "puis", "&": "fond"}
MOTIF = {"grep", "egrep", "fgrep", "sed", "awk"}            # le premier argument est le motif cherché
TEXTE = {"echo", "printf", "dis", "say"}                    # les arguments sont du texte
TR = {"tr"}                                                 # tr a-z A-Z : deux listes de lettres
# une option suivie d'une valeur : la valeur est un argument (head -n 3, find -name "*.txt")
VALEUR_PAR_CMD = {"head": {"-n", "-c"}, "tail": {"-n", "-c"}, "find": {"-name", "-iname", "-size", "-type"},
                  "cut": {"-d", "-f", "-c"}, "sort": {"-k", "-t"}, "git": {"-m"}, "ping": {"-c"}, "grep": {"-e", "-m"},
                  "xargs": {"-n"}}
# les arguments de ces commandes sont des lieux ou des objets (cd grenier : grenier est un chemin)
CHEMINS = {"cd", "ls", "cat", "mkdir", "touch", "rm", "rmdir", "cp", "mv", "tree", "less", "more", "head", "tail",
           "wc", "nano", "du", "file", "stat", "chmod", "sort", "uniq", "rev", "nl", "tac", "pushd", "dir", "type"}
CHMOD = re.compile(r"^([ugoa]*[+=-][rwxX]+|[0-7]{3,4})$")
EXTENSION = re.compile(r"^[^-*\s][^\s]*\.[A-Za-z0-9]{1,5}$")
# des commandes qui ne font que lire : on peut calculer ce qui passe dans les tuyaux sans rien changer
SURES = {"cat", "ls", "grep", "egrep", "fgrep", "head", "tail", "wc", "sort", "uniq", "echo", "rev", "tr", "cut",
         "tree", "pwd", "whoami", "date", "find", "nl", "tac", "printf", "basename", "dirname", "seq", "fold",
         "expand", "du", "df", "free", "uname", "id", "hostname"}
DANGER = re.compile(r"\$\(|`|-delete\b|-exec\b|-ok\b|--output|-fprint")
LIGNES_MAX = 40


# ---------------------------------------------------------------- découper
def mots(ligne):
    """Les mots et les opérateurs d'une ligne, dans l'ordre : [(texte, est_operateur)]. Les guillemets sont gardés
    dans le texte (l'enfant voit ce qu'il a tapé) et protègent ce qu'ils entourent (`grep "a | b"` : un seul mot)."""
    out = []
    cour = ""
    q = None
    i = 0
    n = len(ligne)
    while i < n:
        c = ligne[i]
        if q:
            cour += c
            if c == q:
                q = None
            i += 1
            continue
        if c in "\"'":
            q = c
            cour += c
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            cour += ligne[i:i + 2]
            i += 2
            continue
        if c.isspace():
            if cour:
                out.append((cour, False))
                cour = ""
            i += 1
            continue
        op = None
        for o in OPERATEURS:
            if ligne.startswith(o, i):
                # « 2> » seulement au début d'un mot (fichier2>x n'est pas une redirection d'erreurs)
                if o[0] == "2" and cour:
                    continue
                op = o
                break
        if op:
            if cour:
                out.append((cour, False))
                cour = ""
            out.append((op, True))
            i += len(op)
            continue
        cour += c
        i += 1
    if cour:
        out.append((cour, False))
    return out


def _nu(mot):
    """Le mot sans ses guillemets."""
    if len(mot) >= 2 and mot[0] == mot[-1] and mot[0] in "\"'":
        return mot[1:-1]
    return mot


def est_chemin(mot, existe=None):
    """Vrai si le mot désigne un lieu ou un objet : ., .., ~, un chemin avec /, un nom avec une extension
    (lianes.txt), un objet caché (.cache), une étoile (*.txt), ou un nom qui existe là où l'on est."""
    m = _nu(mot)
    if not m:
        return False
    if m in (".", "..", "~", "/", "-") and m != "-":
        return True
    if "/" in m or m.startswith("~"):
        return True
    if m.startswith(".") and len(m) > 1 and not m.startswith("..."):
        return True
    if "*" in m or "?" in m:
        return True
    if EXTENSION.match(m):
        return True
    return bool(existe and existe(m))


def blocs(ligne, existe=None):
    """Les blocs de la ligne : [{t, g, i, seg, role, cmd}] (voir le haut du fichier). i : le numéro d'allumage (1, 2…),
    seg : le numéro de la commande simple (0, 1…), role : « motif », « texte », « valeur », « variable », « cible »,
    « » ; cmd : la commande de son segment (en minuscules)."""
    out = []
    debut = True
    cmd = ""
    seg = -1
    nargs = 0
    cible = False
    valeur = False
    for texte, op in mots(ligne):
        b = {"t": texte, "g": "argument", "i": len(out) + 1, "seg": max(0, seg), "role": "", "cmd": cmd}
        if op:
            if texte == "|":
                b["g"] = "tuyau"
                debut = True
            elif texte in REDIRECTIONS:
                b["g"] = "redirection"
                cible = True
            else:
                b["g"] = "lien"
                debut = True
            valeur = False
            out.append(b)
            continue
        if cible:
            b["g"], b["role"] = "chemin", "cible"
            cible = False
        elif debut:
            if re.match(r"^[A-Za-z_]\w*=", texte):
                b["role"] = "variable"
            else:
                seg += 1
                cmd = os.path.basename(_nu(texte)).lower()
                b.update(g="commande", seg=seg, cmd=cmd)
                debut = False
                nargs = 0
        elif valeur:
            b["role"] = "valeur" if cmd not in ("find", "grep") else "motif"
            valeur = False
        elif (texte.startswith("-") and len(texte) > 1) or (cmd == "chmod" and CHMOD.match(texte)):
            b["g"] = "option"
            if texte in VALEUR_PAR_CMD.get(cmd, ()):
                valeur = True
        else:
            if cmd in MOTIF and nargs == 0:
                b["role"] = "motif"
            elif cmd in TR:
                b["role"] = "motif"
            elif cmd in TEXTE:
                b["role"] = "texte"
            elif cmd in CHEMINS or est_chemin(texte, existe):
                b["g"] = "chemin"
            nargs += 1
        b["seg"] = max(0, seg)
        b["cmd"] = cmd
        out.append(b)
    return out


def composee(ligne):
    """Vrai si la ligne a un tuyau, une redirection ou un lien (la vue déployée vaut le coup d'être montrée)."""
    return any(b["g"] in ("tuyau", "redirection", "lien") for b in blocs(ligne))


# ---------------------------------------------------------------- les tuyaux
def chaines(bl):
    """Les chaînes de tuyaux : [{etapes: [{cmd, debut, fin, texte}], redir: (op, fichier, indice) ou None,
    debut, fin}]. Une chaîne s'arrête à un lien (&&, ;). texte : la commande simple sans ses redirections."""
    out = []
    cour = None
    etape = None
    attente = None
    for k, b in enumerate(bl):
        if cour is None:
            cour = {"etapes": [], "redir": None, "debut": k, "fin": k}
        if b["g"] == "lien":
            if cour["etapes"]:
                out.append(cour)
            cour = None
            etape = None
            continue
        cour["fin"] = k
        if b["g"] == "tuyau":
            etape = None
            continue
        if b["g"] == "redirection":
            attente = (b["t"], k)
            continue
        if attente is not None:
            if attente[0] in (">", ">>", "&>"):
                cour["redir"] = (attente[0], _nu(b["t"]), k, attente[1])
            attente = None
            continue
        if etape is None:
            etape = {"cmd": b["cmd"], "debut": k, "fin": k, "mots": []}
            cour["etapes"].append(etape)
        etape["fin"] = k
        etape["mots"].append(b["t"])
    if cour is not None and cour["etapes"]:
        out.append(cour)
    for c in out:
        for e in c["etapes"]:
            e["texte"] = " ".join(e.pop("mots"))
    return out


def sure(etapes):
    """Vrai si toutes ces commandes ne font que lire (on peut les lancer pour voir ce qui passe dans les tuyaux)."""
    for e in etapes:
        if e["cmd"] not in SURES or DANGER.search(e["texte"]):
            return False
        if e["cmd"] in ("sort", "uniq") and re.search(r"(^|\s)-o\b", e["texte"]):
            return False
    return True


def flux(ligne, lancer, existe=None):
    """Ce qui passe dans chaque tuyau : pour chaque chaîne, la liste des sorties après chaque étape
    ([[lignes après l'étape 1], [lignes après l'étape 2]…], None si on ne peut pas le calculer sans danger).
    lancer(texte) -> (code, lignes) lance une commande sans redirection."""
    out = []
    for c in chaines(blocs(ligne, existe)):
        sorties = None
        if sure(c["etapes"]):
            sorties = []
            for k in range(len(c["etapes"])):
                texte = " | ".join(e["texte"] for e in c["etapes"][:k + 1])
                try:
                    _code, lignes = lancer(texte)
                except Exception:                    # noqa: BLE001 — la vue ne plante jamais pour un flux
                    lignes = []
                sorties.append([l for l in lignes if not l.startswith("@")][:LIGNES_MAX])
        out.append(sorties)
    return out


def lanceur(dossier):
    """Lance une commande sûre dans dossier (sans clavier, 3 secondes au plus)."""
    from .bureau_vie import executer

    def lancer(texte):
        return executer(texte, dossier, 3.0)
    return lancer


def existe_dans(dossier):
    def existe(nom):
        try:
            return os.path.exists(os.path.join(dossier, os.path.expanduser(nom)))
        except (OSError, ValueError):
            return False
    return existe


# ---------------------------------------------------------------- les mots pour le dire
def nom_genre(g):
    return t("dep.genre." + g)


def phrase_commande(cmd):
    """Ce que fait une commande, en une courte phrase (dep.c.<cmd>), ou une phrase générale."""
    return t("dep.c." + cmd) if brut("dep.c." + cmd) is not None else t("dep.c.autre")


def _option(b):
    from . import explique
    table = explique.OPTIONS.get(b["cmd"], {})
    cle = table.get(b["t"])
    if cle is None and b["t"].startswith("-") and len(b["t"]) == 2:
        cle = table.get(b["t"])
    if cle is None and len(b["t"]) > 2 and b["t"][0] == "-" and b["t"][1] != "-":
        cle = table.get("-" + b["t"][1])
    return cle


def courte(b, bl):
    """La courte explication sous le bloc (quelques mots)."""
    g = b["g"]
    if g == "commande":
        return phrase_commande(b["cmd"])
    if g == "option":
        cle = _option(b)
        if cle and brut("dep.o." + cle) is not None:
            return t("dep.o." + cle)
        return t("dep.o.autre", cmd=b["cmd"])
    if g == "argument":
        return t("dep.a." + (b["role"] or "simple"))
    if g == "chemin":
        if b["role"] == "cible":
            return t("dep.ch.cible")
        return t("dep.ch.simple")
    if g == "tuyau":
        a, c = _voisins(b, bl)
        return t("dep.tuyau", a=a, b=c)
    if g == "redirection":
        a, _c = _voisins(b, bl)
        f = _apres(b, bl)
        return t("dep.r." + REDIRECTIONS.get(b["t"], "ecrase"), a=a, f=f)
    a, c = _voisins(b, bl)
    return t("dep.l." + LIENS.get(b["t"], "puis"), a=a, b=c)


def _voisins(b, bl):
    """Les commandes avant et après un opérateur."""
    k = b["i"] - 1
    avant = next((x["cmd"] for x in reversed(bl[:k]) if x["g"] == "commande"), "?")
    apres = next((x["cmd"] for x in bl[k + 1:] if x["g"] == "commande"), "?")
    return avant, apres


def _apres(b, bl):
    k = b["i"]
    return _nu(bl[k]["t"]) if k < len(bl) else "?"


def longue(b, bl):
    """La phrase de la boîte d'explication : « grep (commande) garde seulement les lignes… »."""
    return t("dep.phrase", mot=b["t"], genre=nom_genre(b["g"]), texte=courte(b, bl))


def lieu(b, dossier):
    """Pour un chemin : (chemin relatif dans le terrain, nom du lieu) ou None."""
    from . import maison
    m = os.path.expanduser(_nu(b["t"]))
    try:
        p = os.path.normpath(os.path.join(dossier or os.getcwd(), m))
    except (OSError, ValueError):
        return None
    r = maison.rel(p)
    if r is None:
        return None
    piece = r.split("/")[0] if r else ""
    return r, (maison.nom_piece(piece) if piece else t("dep.terrain"))


# ---------------------------------------------------------------- le dessin en couleurs ANSI (terminal)
RONDS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def rond(i):
    return RONDS[i - 1] if 1 <= i <= len(RONDS) else str(i)


def compacte(bl, actif=None, couleur=True):
    """Une ligne : ①cat ②lianes.txt ③| ④grep ⑤-i ⑥gland (en couleurs ; l'actif en gras, la suite en gris)."""
    morceaux = []
    for b in bl:
        if not couleur:
            morceaux.append(f"{rond(b['i'])}{b['t']}")
            continue
        if actif is not None and b["i"] > actif:
            morceaux.append(f"{fg(240)}{rond(b['i'])}{b['t']}{RESET}")
        elif actif is not None and b["i"] == actif:
            morceaux.append(f"{fg(ANSI[b['g']])}{BOLD}\033[7m{rond(b['i'])}{b['t']}{RESET}")
        else:
            morceaux.append(f"{fg(ANSI[b['g']])}{rond(b['i'])}{BOLD}{b['t']}{RESET}")
    return " ".join(morceaux)


def legende(couleur=True):
    out = []
    for g in ("commande", "option", "argument", "chemin", "tuyau", "redirection"):
        out.append((f"{fg(ANSI[g])}●{RESET} " if couleur else "● ") + nom_genre(g))
    return "  ".join(out)


def _boites(bl, actif, largeur):
    """Les blocs dessinés en boîtes (5 lignes : numéros, haut, mot, bas, genre), coupés en rangées si besoin."""
    rangees = []
    cour = []
    w = 0
    for b in bl:
        lw = max(len(b["t"]) + 4, len(nom_genre(b["g"])) + 1)
        if cour and w + lw > largeur:
            rangees.append(cour)
            cour, w = [], 0
        cour.append((b, lw))
        w += lw + 1
    if cour:
        rangees.append(cour)
    out = []
    for r in rangees:
        lignes = ["", "", "", "", ""]
        for b, lw in r:
            if b["i"] < actif:
                c, st = fg(ANSI[b["g"]]), ""
            elif b["i"] == actif:
                c, st = fg(ANSI[b["g"]]) + BOLD, BOLD
            else:
                c, st = fg(239), ""
            mot = b["t"]
            inner = len(mot) + 2
            pad = lw - inner - 2
            g, d = pad // 2, pad - pad // 2
            epais = b["i"] == actif
            h, v, coins = ("━", "┃", "┏┓┗┛") if epais else ("─", "│", "╭╮╰╯")
            num = str(b["i"])
            lignes[0] += " " * g + f"{c}{num}{RESET}" + " " * (inner + 2 - len(num) + d) + " "
            lignes[1] += " " * g + f"{c}{coins[0]}{h * inner}{coins[1]}{RESET}" + " " * d + " "
            lignes[2] += " " * g + f"{c}{v}{RESET}" + (f"{c}\033[7m" if epais else c) + f" {mot} {RESET}{c}{v}{RESET}" \
                + " " * d + " "
            lignes[3] += " " * g + f"{c}{coins[2]}{h * inner}{coins[3]}{RESET}" + " " * d + " "
            nom = nom_genre(b["g"]).upper()
            gg = (lw - len(nom)) // 2
            lignes[4] += " " * gg + (f"{c}{st}{nom}{RESET}" if b["i"] <= actif else f"{fg(239)}{nom}{RESET}") \
                + " " * (lw - len(nom) - gg) + " "
        out.extend(lignes)
    return out


def _tuyau_anime(a, b, ligne, phase, largeur):
    """cat ─ ─ ▶[ une liane a enroulé… ]─ ─ ▶ grep : la ligne avance dans le tuyau."""
    lg = max(14, min(largeur - len(a) - len(b) - 10, 50))
    etiquette = "[" + raccourcir(ligne or "…", 18) + "]"
    pos = int(phase * (lg - len(etiquette))) if lg > len(etiquette) else 0
    tuyau = ""
    for x in range(lg):
        if pos <= x < pos + len(etiquette):
            continue
        tuyau += "─" if (x + int(phase * 8)) % 3 else " "
    avant, apres = tuyau[:pos], tuyau[pos:]
    return (f"  {fg(ANSI['commande'])}{BOLD}{a}{RESET} {fg(ANSI['tuyau'])}{avant}{RESET}{BOLD}{fg(255)}\033[48;5;54m"
            f"{etiquette}{RESET}{fg(ANSI['tuyau'])}{apres}▶{RESET} {fg(ANSI['commande'])}{BOLD}{b}{RESET}")


def ecran(ligne, bl, actif, sorties, phase=0.0, largeur=80, dossier=None, pas=False):
    """Les lignes de la vue déployée à l'étape actif (1…N) ; phase (0-1) : l'animation du tuyau ou de la chute."""
    n = len(bl)
    out = [f" {fg(213)}{BOLD}" + t("dep.titre") + f"{RESET}  {DIM}" + t("dep.etape", k=actif, n=n) +
           ("  · " + t("dep.pas_a_pas") if pas else "") + RESET, ""]
    out += ["  " + x for x in _boites(bl, actif, largeur - 4)]
    out.append("")
    b = bl[actif - 1]
    out.append(f"  {fg(ANSI[b['g']])}▌{RESET} " + longue(b, bl))
    chs = chaines(bl)
    # le tuyau ou la redirection de l'étape (avec ce qui passe dedans)
    if b["g"] == "tuyau":
        k = b["i"] - 1
        for c, s in zip(chs, sorties or [None] * len(chs)):
            for j, e in enumerate(c["etapes"][:-1]):
                if e["fin"] < k < c["etapes"][j + 1]["debut"]:
                    lignes = (s[j] if s else None) or []
                    ici = lignes[int(phase * max(1, len(lignes))) % len(lignes)] if lignes else None
                    out.append("")
                    out.append(_tuyau_anime(e["cmd"], c["etapes"][j + 1]["cmd"], ici, phase % 1.0, largeur))
                    if s:
                        out.append(f"  {DIM}" + t("dep.lignes_passent", n=len(lignes), a=e["cmd"]) + RESET)
    elif b["g"] == "redirection" or (b["g"] == "chemin" and b["role"] == "cible"):
        for c, s in zip(chs, sorties or [None] * len(chs)):
            if c["redir"] and (c["redir"][2] == b["i"] - 1 or c["redir"][3] == b["i"] - 1):
                lignes = (s[-1] if s else None) or []
                tombees = lignes[:max(0, int(phase * (len(lignes) + 1)))]
                out.append("")
                out.append(f"  {fg(ANSI['commande'])}{BOLD}{c['etapes'][-1]['cmd']}{RESET} {fg(ANSI['redirection'])}"
                           f"══▶ ▼{RESET}")
                out.append(f"  {fg(ANSI['redirection'])}      ╭─ 📄 {c['redir'][1]} ─{RESET}")
                for x in tombees[-4:]:
                    out.append(f"  {fg(ANSI['redirection'])}      │{RESET} {raccourcir(x, largeur - 12)}")
                if s:
                    out.append(f"  {fg(ANSI['redirection'])}      ╰─{RESET} {DIM}" +
                               t("dep.tombe", n=len(lignes), f=c["redir"][1]) + RESET)
                else:
                    out.append(f"  {fg(ANSI['redirection'])}      ╰─{RESET}")
    elif b["g"] == "chemin":
        lie = lieu(b, dossier)
        if lie:
            out.append(f"  {fg(ANSI['chemin'])}📍 " + t("dep.sur_carte", f=_nu(b["t"]), lieu=lie[1]) + RESET)
    if actif == n and sorties:
        for c, s in zip(chs, sorties):
            if s and len(c["etapes"]) > 1:
                out.append("")
                out.append(f"  {fg(ANSI['commande'])}➜ " + t("dep.resultat", n=len(s[-1]), a=len(s[0]),
                                                             cmd=c["etapes"][0]["cmd"]) + RESET)
    out.append("")
    out.append("  " + legende())
    return out


def jouer(ligne, dossier=None, pas=False, sortie=None, clavier=None, ips=12):
    """Joue la vue déployée dans le terminal : automatique (chaque bloc ~1,3 s, les tuyaux animés), ou pas à pas
    (Entrée : bloc suivant, q : finir). Hors d'un vrai terminal : l'image finale, sans animation."""
    out = sortie or sys.stdout
    dossier = dossier or os.getcwd()
    bl = blocs(ligne, existe_dans(dossier))
    if not bl:
        out.write(t("dep.vide") + "\n")
        return
    sorties = flux(ligne, lanceur(dossier), existe_dans(dossier))
    try:
        import shutil
        largeur = shutil.get_terminal_size((90, 24)).columns
    except OSError:
        largeur = 90
    if not (hasattr(out, "isatty") and out.isatty()):
        out.write("\n".join(ecran(ligne, bl, len(bl), sorties, 1.0, largeur, dossier)) + RESET + "\n")
        return
    hauteur = [0]

    def dessiner(lignes):
        if hauteur[0]:
            out.write(f"\033[{hauteur[0]}F")
        out.write("".join(x + "\033[K\n" for x in lignes) + "\033[J")
        out.flush()
        hauteur[0] = len(lignes)

    if pas:
        from .app import Clavier
        clav = clavier or Clavier()
        with clav:
            k = 1
            while k <= len(bl):
                dessiner(ecran(ligne, bl, k, sorties, 1.0, largeur, dossier, pas=True) +
                         [f"  {DIM}" + t("dep.touches") + RESET])
                phase = 0.0
                touche = None
                while touche is None:                    # le tuyau bouge en attendant Entrée
                    touche = clav.touche(1 / ips)
                    phase += 1 / (ips * 1.6)
                    if touche is None and bl[k - 1]["g"] in ("tuyau", "redirection"):
                        dessiner(ecran(ligne, bl, k, sorties, phase % 1.0 if bl[k - 1]["g"] == "tuyau" else
                                       min(1.0, phase), largeur, dossier, pas=True) +
                                 [f"  {DIM}" + t("dep.touches") + RESET])
                if touche.lower() == "q":
                    break
                k += 1
        return
    for k in range(1, len(bl) + 1):
        anime = bl[k - 1]["g"] in ("tuyau", "redirection")
        n_images = int(ips * (2.4 if anime else 1.1))
        for f in range(n_images):
            phase = f / max(1, n_images - 1)
            dessiner(ecran(ligne, bl, k, sorties, phase, largeur, dossier))
            time.sleep(1 / ips)


def commande(args, dossier=None, sortie=None):
    """tg deploie [--pas] <commande> ; sans commande : la dernière commande tapée dans le terminal."""
    pas = any(a in ("--pas", "-p", "pas") for a in args[:1])
    reste = [a for a in args if a not in ("--pas", "-p")] if pas else list(args)
    if reste and reste[0] == "pas":
        reste = reste[1:]
    depuis_historique = "--historique" in reste
    reste = [a for a in reste if a != "--historique"]
    ligne = " ".join(reste).strip()
    if depuis_historique or not ligne:
        ligne = derniere_ligne(ligne)
    if not ligne:
        (sortie or sys.stdout).write(t("dep.aide") + "\n")
        return
    jouer(ligne, dossier, pas=pas, sortie=sortie)


def derniere_ligne(deja=""):
    """La ligne à déployer quand l'alias `deploie` coupe le reste (bash : `deploie cat x | grep y` arrive entière
    par l'historique) ; sinon la dernière commande tapée avant `deploie`."""
    try:
        lignes = _historique()
    except Exception:                                # noqa: BLE001
        lignes = []
    for l in reversed(lignes):
        m = l.split()
        if not m:
            continue
        n = 1 if m[0] == "deploie" else 2 if m[:2] == ["tg", "deploie"] else 0
        if n:
            reste = l.split(None, n)[n] if len(m) > n else ""
            reste = reste.replace("--historique", "").replace("--pas", "").strip()
            if reste:
                return reste
            continue
        return deja or l
    return deja


def _historique():
    """Les dernières lignes des historiques du shell (le plus récent en dernier)."""
    from . import core
    meilleur, date = [], -1
    for f in core.history_files():
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime > date:
            try:
                brut_ = f.read_bytes()[-20000:].decode("utf-8", "replace").splitlines()
            except OSError:
                continue
            lignes = [x for x in (core.parse_line(l) for l in brut_) if x]
            meilleur, date = lignes, st.st_mtime
    return meilleur[-30:]


def recap_lecon(ligne):
    """Après une étape de leçon réussie avec une commande composée : la ligne des blocs et l'astuce (2 lignes)."""
    if not ligne or not composee(ligne):
        return []
    bl = blocs(ligne)
    return [f"   {fg(141)}▸{RESET} " + t("dep.recap") + " " + compacte(bl),
            f"   {fg(141)}▸{RESET} {DIM}" + t("dep.astuce", cmd="deploie " + ligne) + RESET]
