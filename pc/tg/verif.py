"""Valider une étape sur le RÉSULTAT, pas sur le texte tapé (retours des simulations d'enfants, G-34).

Ce que le jeu sait d'une ligne tapée :
  - son code de sortie, quand le crochet d'invite le donne (`tg prompt --statut=$?`) : 0 = réussi ;
  - le dossier où elle a été tapée (le crochet donne le dossier courant ; les « cd » de la ligne sont rejoués) ;
  - le système de fichiers : un chemin tapé existe-t-il depuis ce dossier ? la commande est-elle installée ?

Une ligne est découpée en morceaux (`cd / && ls`, `cd x; ls` : chaque morceau peut valider une étape) ; un morceau
est comparé au motif de l'étape partie par partie (`cat f | grep mot` contient `grep mot`), après avoir remplacé les
jokers par les noms qu'ils désignent (`cat nid/*.txt` → `cat nid/lit.txt nid/repas.txt`), comme le fait le shell.
Le nom de la commande doit être écrit en minuscules (sauf sous Windows) : `PWD` et `Ls` n'existent pas.

Le lieu attendu par une étape (« 📁 à taper depuis … ») est calculé à partir des chemins relatifs de sa commande :
le dossier de la zone d'aventure d'où ces chemins existent (lieu_attendu).
"""
import difflib
import glob
import os
import re
import shutil
from pathlib import Path

from . import core
from .plateforme import IS_WIN

T = lambda: core.TERRAIN  # noqa: E731

# ---------------------------------------------------------------- découper une ligne


def mots(texte):
    """Les mots d'un morceau de commande : [(mot sans guillemets, cité)] (les guillemets protègent les jokers)."""
    out, cur, cite, q, vide = [], "", False, None, True
    for ch in texte:
        if q:
            if ch == q:
                q = None
            else:
                cur += ch
            continue
        if ch in "'\"":
            q, cite, vide = ch, True, False
            continue
        if ch.isspace():
            if not vide:
                out.append((cur, cite))
            cur, cite, vide = "", False, True
            continue
        cur += ch
        vide = False
    if not vide:
        out.append((cur, cite))
    return out


def _couper(texte, seps):
    """Coupe sur les séparateurs (hors guillemets). Renvoie [(morceau, séparateur qui suit)]."""
    out, cur, q, i = [], "", None, 0
    while i < len(texte):
        ch = texte[i]
        if q:
            cur += ch
            if ch == q:
                q = None
            i += 1
            continue
        if ch in "'\"":
            q = ch
            cur += ch
            i += 1
            continue
        pris = next((s for s in seps if texte.startswith(s, i)), None)
        if pris and not (pris == "|" and texte.startswith("||", i)) and not (pris == "&" and (
                texte.startswith("&&", i) or texte[i - 1:i] in (">", "<") or texte[i + 1:i + 2] == ">")):
            out.append((cur.strip(), pris))
            cur = ""
            i += len(pris)
            continue
        cur += ch
        i += 1
    if cur.strip():
        out.append((cur.strip(), None))
    return out


class Morceau:
    """Un morceau de ligne : son texte, le dossier avant / après, son code de sortie (None = inconnu)."""

    def __init__(self, texte, avant, apres, statut):
        self.texte, self.avant, self.apres, self.statut = texte, avant, apres, statut

    def __repr__(self):
        return f"Morceau({self.texte!r}, {self.avant!r}, statut={self.statut})"


def morceaux(ligne, cwd, statut=None, precedent=None):
    """Les morceaux d'une ligne (`a && b`, `a; b`), avec le dossier de chacun (les « cd » rejoués) et leur code de
    sortie : `a && b` réussi → tous réussis ; sinon seul le dernier morceau a le code de la ligne."""
    from . import maison
    parts = _couper(ligne.strip(), ("&&", ";"))
    tous_ok = statut == 0 and all(s in ("&&", None) for _, s in parts)
    cur = cwd or str(Path.home())
    out = []
    for k, (txt, _sep) in enumerate(parts):
        m = re.match(r"^(cd|set-location|sl|chdir|pushd)(?:\s+(.*))?$", txt, re.I)
        avant = cur
        if m:
            nouveau = maison._resoudre(cur, m.group(2), precedent)
            if nouveau != cur:
                precedent = cur
            cur = nouveau
        st = statut if (k == len(parts) - 1 or tous_ok) else None
        out.append(Morceau(txt, avant, cur, st))
    return out


# ---------------------------------------------------------------- jokers, chemins, commandes
JOKER = re.compile(r"[*?\[]")


def _abs(mot, cwd):
    if mot == "~" or mot.startswith("~/") or mot.startswith("~\\"):
        return os.path.expanduser(mot)
    if os.path.isabs(mot):
        return mot
    return os.path.join(cwd or str(Path.home()), mot)


def developper(texte, cwd):
    """Remplace les jokers non cités par les noms qu'ils désignent depuis cwd (comme le shell). Les redirections et
    les tuyaux sont gardés ; un joker qui ne désigne rien reste tel quel."""
    out = []
    for m, cite in mots(texte):
        if not cite and JOKER.search(m) and not m.startswith("-"):
            base = _abs(m, cwd)
            trouves = sorted(glob.glob(base))
            if trouves:
                pre = "" if os.path.isabs(m) or m.startswith("~") else (cwd or "")
                out += [os.path.relpath(x, pre) if pre else x for x in trouves]
                continue
        out.append(f'"{m}"' if cite and (" " in m or not m) else m)
    return " ".join(out)


# commandes qui lisent ou agissent sur des chemins qui doivent EXISTER ; celles qui créent (le parent doit exister)
LIT = {"cat", "less", "more", "head", "tail", "wc", "ls", "stat", "du", "file", "rev", "sort", "uniq", "grep", "chmod",
       "rm", "rmdir", "cp", "mv", "sh", "bash", "source", ".", "find", "tree", "nl", "od", "xxd", "md5sum", "sha256sum",
       "type", "gc", "get-content", "dir", "gci", "get-childitem"}
CREE = {"mkdir", "touch", "tee", "new-item", "ni"}
AVEC_VALEUR = {"head": {"-n", "-c"}, "tail": {"-n", "-c"}, "grep": {"-e", "-m", "-A", "-B", "-C", "-f"},
               "find": set(), "du": {"-d", "--max-depth"}, "ls": {"-I", "--hide", "-w"}, "sort": {"-k", "-t"},
               "cp": {"-t"}, "mv": {"-t"}, "chmod": set(), "wc": set(), "tee": set()}


def _arguments(cmd, args):
    """Les arguments « chemins » d'une commande (sans les options et leurs valeurs, sans le motif de grep, sans le mode
    de chmod) : (à lire, à créer)."""
    vals = AVEC_VALEUR.get(cmd, set())
    libres, saute, fin = [], False, False
    for m, cite in args:
        if saute:
            saute = False
            continue
        if not fin and m == "--":
            fin = True
            continue
        if not fin and m.startswith("-") and len(m) > 1:
            if m in vals:
                saute = True
            if cmd == "find":
                break                        # find . -name … : le chemin de départ est avant l'expression
            continue
        libres.append((m, cite))
    if cmd == "grep" and not any(m in ("-e", "-f") for m, _ in args):
        libres = libres[1:]                  # le motif
    if cmd == "chmod":
        libres = libres[1:]                  # 444, u+w…
    if cmd == "find":
        libres = libres[:1] if libres else []
    if cmd in ("cp", "mv") and len(libres) >= 2:
        return libres[:-1], []               # la destination peut ne pas exister
    if cmd in ("sh", "bash", "source", "."):
        return libres[:1], []
    if cmd in CREE:
        return [], libres
    if cmd in LIT:
        return libres, []
    return [], []


def redirections(texte):
    """Les fichiers visés par > et >> (et 2>, sauf /dev/null)."""
    return [m.group(2) for m in re.finditer(r"(?<![<\d&])(\d?>>?)\s*([^\s|;&<>]+)", texte)
            if m.group(2) not in ("/dev/null", "&1", "&2") and not m.group(2).startswith("&")]


def chemins_manquants(texte, cwd):
    """Les chemins tapés dans ce morceau qui n'existent pas depuis cwd (ou dont le dossier parent manque, pour ce qui
    est créé). Les jokers et les variables ne sont pas vérifiés (le shell les développe)."""
    manque = []
    for partie, _ in _couper(texte, ("|",)):
        sans = re.sub(r"(?<![<\d&])\d?>>?\s*[^\s|;&<>]+", " ", partie)
        sans = re.sub(r"<\s*([^\s|;&<>]+)", r" \1", sans)          # rev < fichier : le fichier doit exister
        ms = mots(sans)
        if not ms:
            continue
        cmd = ms[0][0].lower()
        if cmd in ("sudo", "time", "nohup"):
            ms = ms[1:]
            cmd = ms[0][0].lower() if ms else ""
        lire, creer = _arguments(cmd, ms[1:])
        if "<" in partie:
            lire += [(m, False) for m in re.findall(r"<\s*([^\s|;&<>]+)", partie)]
        if cmd == "mkdir" and any(m in ("-p", "--parents") for m, _ in ms):
            creer = []
        for m, cite in lire:
            if "$" in m or "`" in m or (JOKER.search(m) and not cite) or m in ("-", ".", ".."):
                continue
            if "://" in m:
                continue
            if not os.path.lexists(_abs(m, cwd)):
                manque.append(m)
        for m, cite in creer:
            if "$" in m or (JOKER.search(m) and not cite):
                continue
            parent = os.path.dirname(_abs(m.rstrip("/\\"), cwd))
            if not os.path.isdir(parent):
                manque.append(m)
    for r in redirections(texte):
        if "$" in r:
            continue
        if not os.path.isdir(os.path.dirname(_abs(r, cwd))):
            manque.append(r)
    return manque


def commande_installee(mot):
    """La commande existe sur cet ordinateur (programme, commande interne du shell, raccourci du jeu)."""
    if not mot:
        return True
    if mot.startswith(("./", "/", "~", ".\\")) or "=" in mot:
        return True
    if mot in core.BUILTINS or mot in BUILTINS_EN_PLUS:
        return True
    return shutil.which(mot) is not None


BUILTINS_EN_PLUS = {"alias", "unalias", "function", "local", "declare", "let", "shopt", "command", "builtin", "times",
                    "disown", "suspend", "logout", "hash", "complete", "compgen", "dirs", "caller", "enable", "mapfile",
                    "readarray", "getopts", "return", "break", "continue", "shift", "until", "case", "select", "{",
                    "(", "!", "[[", "aide", "miam", "ouvre"}


def casse_ok(mot):
    """`PWD`, `Ls` : le nom de la commande en majuscules n'existe pas (Linux, macOS ; Windows s'en moque)."""
    if IS_WIN or not mot or mot == mot.lower():
        return True
    return shutil.which(mot) is not None and os.path.basename(shutil.which(mot)) == mot


def premier(texte):
    ms = mots(texte)
    if not ms:
        return ""
    m = ms[0][0]
    if m in ("sudo", "time", "nohup") and len(ms) > 1:
        m = ms[1][0]
    return m


# ---------------------------------------------------------------- une étape réussie ?
def motif_ok(step, texte, cwd):
    """Le texte (développé) ressemble à la commande de l'étape : le motif sur la ligne entière ou sur une partie d'un
    tuyau, et chaque commande écrite en minuscules."""
    if "re" not in step:
        return False
    dev = developper(texte, cwd)
    tuyau = [p for p, _ in _couper(dev, ("|",))]
    parties = [texte, dev] + tuyau + [p for p, _ in _couper(texte, ("|",))]
    if len(tuyau) > 1:                       # `cat f | grep mot` = `grep mot f` ; `cat f | wc -l` = `wc -l f`
        fichiers = [m for m, _c in mots(tuyau[0])[1:] if not m.startswith("-")]
        parties += [p + " " + " ".join(fichiers) for p in tuyau[1:]]
    for p in parties:
        if re.search(step["re"], p.strip(), re.I):
            if all(casse_ok(premier(x)) for x, _ in _couper(p, ("|",))):
                return True
    return False


def resultat_ok(step, m):
    """Le morceau a vraiment marché : son code de sortie s'il est connu ; sinon, les commandes existent et les chemins
    tapés existent depuis le dossier où il a été tapé. Une étape « echoue » (le cadenas refuse >>) veut un refus."""
    racine = hasattr(os, "geteuid") and os.geteuid() == 0
    absent = [premier(x) for x, _ in _couper(m.texte, ("|",)) if premier(x) and not commande_installee(premier(x))]
    if (step.get("reseau") or step.get("absent_ok")) and (absent or step.get("reseau")):
        # le réseau peut manquer (école, avion) et l'outil peut ne pas être installé : avoir essayé suffit, le jeu
        # explique alors pourquoi ça n'a pas répondu (voir histoire.tick_lecon) ; une faute de chemin compte encore
        return not chemins_manquants(m.texte, m.avant)
    if step.get("echoue"):
        if m.statut is not None:
            return m.statut != 0 or racine          # root écrit quand même : on ne bloque pas la leçon
        return not chemins_manquants(m.texte, m.avant)
    if m.statut is not None:
        return m.statut == 0
    for x, _ in _couper(m.texte, ("|",)):
        mot = premier(x)
        if mot and not commande_installee(mot) and mot.lower() in core.NOMS_CONNUS | {"tree"}:
            return False
    return not chemins_manquants(m.texte, m.avant)


# ---------------------------------------------------------------- le lieu attendu par une étape
def _chemins_commande(cmd):
    """Les chemins relatifs de la commande affichée : (à lire, à créer)."""
    lire, creer = [], []
    for partie, _ in _couper(cmd, ("|", "&&", ";")):
        sans = re.sub(r"(?<![<\d&])\d?>>?\s*[^\s|;&<>]+", " ", partie)
        ms = mots(sans)
        if not ms:
            continue
        lr, cr = _arguments(ms[0][0].lower(), ms[1:])
        lire += [m for m, c in lr if not (JOKER.search(m) and not c)]
        creer += [m for m, c in cr]
        creer += redirections(partie)
    garder = lambda m: m and not os.path.isabs(m) and not m.startswith(("~", "$", "-")) and m not in (".", "..")  # noqa
    return [m for m in lire if garder(m)], [m for m in creer if garder(m)]


def lieu_attendu(state, step):
    """Le lieu de la zone d'aventure (chemin relatif, « » = le carrefour) d'où la commande de l'étape marche, ou None
    (n'importe où, ou un lieu hors de la zone : la Racine…)."""
    if "ou" in step:
        return step["ou"]
    if "depuis" in step:                     # `cd ..` : le lieu d'où l'on remonte (C1)
        return step["depuis"]
    if any(k in step for k in ("ici", "ici_abs", "ou_abs")):
        return None
    lire, creer = _chemins_commande(step.get("cmd") or "")
    lire = [m for m in lire if m != "?"]
    if not lire and not creer:
        return None
    if not T().is_dir():
        return None
    from . import histoire, maison
    c = histoire.chapitre_courant(state)
    candidats = []
    if any("/" in m or "\\" in m for m in lire + creer):
        candidats.append("")
    if c and c.get("piece") and c["piece"] not in ("vestibule", "nid", "jardin"):
        candidats.append(c["piece"])
    candidats += ["", "nid"]
    try:
        for d in sorted(T().iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                candidats.append(d.name)
    except OSError:
        pass
    vus = []
    for cand in candidats:
        if cand in vus:
            continue
        vus.append(cand)
        base = T() / cand if cand else T()
        if all(os.path.lexists(base / m) for m in lire) and all((base / m).parent.is_dir() for m in creer):
            if lire or any("/" in m or "\\" in m for m in creer):
                return cand
    # rien ne marche encore (l'objet à lire n'existe pas encore) : pour des chemins « a/b », le carrefour
    if any("/" in m or "\\" in m for m in lire + creer):
        return ""
    return None


def au_bon_endroit(state, step, cwd):
    """Vrai si l'enfant est déjà là où l'étape se tape (ou si l'étape se tape n'importe où)."""
    from . import maison
    lieu = lieu_attendu(state, step)
    if lieu is None:
        return True
    if "ou" in step:
        return maison.dans(cwd, lieu)
    if "depuis" in step:                     # `cd ..` mène au carrefour depuis n'importe lequel de ses lieux
        r = maison.rel(cwd) if cwd else None
        return r is not None and r != "" and os.path.dirname(r.replace("\\", "/")) == step.get("ici", "")
    return maison.rel(cwd) == lieu if cwd else False


def cd_vers(lieu):
    """La commande pour aller à ce lieu de la zone d'aventure, valable depuis n'importe où."""
    return f"cd ~/{T().name}/{lieu}".rstrip("/")


# ---------------------------------------------------------------- les fautes collées, la casse, les noms proches
def collee(mot, connues=None):
    """`cdvestibule` → `cd vestibule`, `ls-a` → `ls -a`, `cd/` → `cd /`, `cd..` → `cd ..` (ou None)."""
    if not mot or commande_installee(mot):
        return None
    connues = connues or ("mkdir", "rmdir", "touch", "chmod", "whoami", "grep", "find", "head", "tail", "less",
                          "echo", "cat", "pwd", "cd", "ls", "cp", "mv", "rm", "wc", "du", "df", "ps", "tree")
    for c in sorted(connues, key=len, reverse=True):
        if mot.lower().startswith(c) and len(mot) > len(c):
            reste = mot[len(c):]
            if reste[0] in "-/~." or reste.isalnum() or "_" in reste:
                if not commande_installee(c):
                    continue
                return f"{c} {reste}"
    return None


def ponctuation(mot):
    """I9 : `pwd,` `ls.` → la commande sans la ponctuation collée (ou None)."""
    net = (mot or "").rstrip(",.;:!?")
    return net if net and net != mot and commande_installee(net) and casse_ok(net) else None


def mot_de_l_oeuf(mot):
    """I9 : `bonjour` tout seul → `echo bonjour` quand c'est une commande de la liste de l'œuf (ou None)."""
    try:
        from . import intro
        for c in intro.checklist():
            cmd = intro.commande_de(c)
            if cmd.split()[0] == "echo" and cmd.split()[1:2] == [mot]:
                return cmd
    except Exception:                                # noqa: BLE001
        pass
    return None


def barre_oubliee(mot, cwd):
    """I9 : `nidrepas.txt` → `nid/repas.txt` : un lieu d'ici collé au nom d'un objet qu'il contient (ou None)."""
    if not mot or "/" in mot or "\\" in mot or os.path.lexists(_abs(mot, cwd)):
        return None
    base = cwd or str(Path.home())
    try:
        dossiers = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    except OSError:
        return None
    for d in sorted(dossiers, key=len, reverse=True):
        reste = mot[len(d):]
        if mot.startswith(d) and reste and os.path.lexists(os.path.join(base, d, reste)):
            return f"{d}/{reste}"
    return None


def nom_proche(mot, cwd):
    """Un nom qui existe là où l'enfant est et qui ressemble au mot tapé (faute de frappe, majuscules) : (proche,
    casse) ou None. casse = True si seule la casse diffère (« Nid » / « nid »)."""
    parts = [x for x in re.split(r"[/\\]", mot.rstrip("/\\")) if x]
    base = str(Path.home()) if mot.startswith("~") else ("/" if mot.startswith("/") else (cwd or str(Path.home())))
    if mot.startswith("~"):
        parts = parts[1:]
    tete = []
    for x in parts:                           # le premier morceau du chemin qui n'existe pas (fouilli/ours…)
        if not os.path.lexists(os.path.join(base, *tete, x)):
            break
        tete.append(x)
    else:
        return None
    nom = parts[len(tete)] if len(tete) < len(parts) else ""
    tete_txt = "/".join(([parts[0]] if mot.startswith("~") else []) + tete) if tete or mot.startswith("~") else ""
    if mot.startswith("/"):
        tete_txt = "/" + tete_txt
    base = os.path.join(base, *tete)
    reste = parts[len(tete) + 1:]
    try:
        noms = os.listdir(base)
    except OSError:
        return None
    def joindre(n):
        return "/".join([y for y in [tete_txt.rstrip("/") if tete_txt != "/" else "", n] + reste if y != ""]) \
            if tete_txt != "/" else "/" + "/".join([n] + reste)
    for n in noms:
        if n != nom and n.lower() == nom.lower():
            return joindre(n), True
    p = difflib.get_close_matches(nom, noms, n=1, cutoff=0.75)
    if p and p[0] != nom:
        return joindre(p[0]), False
    return None


# ---------------------------------------------------------------- les erreurs du shell, expliquées en français
LECTEURS = {"cat", "less", "more", "head", "tail", "wc", "rev", "sort", "nl", "od", "xxd", "file"}


def expliquer(ligne, statut, cwd):
    """Une commande a échoué (statut ≠ 0) : la phrase en français qui explique l'erreur anglaise du shell (« No such
    file or directory », « Permission denied », « Is a directory », « Not a directory »), d'après ce que la ligne
    visait sur le disque. None si on ne sait pas (ou si la commande est inconnue : feed le dit déjà)."""
    from .langue import t
    if statut in (None, 0) or not ligne:
        return None
    for m in morceaux(ligne, cwd, statut):
        for x, _ in _couper(m.texte, ("|",)):
            mot = premier(x)
            if not mot or not commande_installee(mot) or not casse_ok(mot):
                return None
            if statut == 126:
                return t("core.err.pas_lance", nom=mot)
            ms = mots(re.sub(r"(?<![<\d&])\d?>>?\s*[^\s|;&<>]+", " ", x))
            args = [w for w, c in ms[1:] if not w.startswith("-")]
            if mot == "cd" and args:
                p = _abs(args[0], m.avant)
                if os.path.isfile(p):
                    return t("core.err.pas_dossier", nom=args[0])
                if os.path.isdir(p) and not os.access(p, os.X_OK):
                    return t("core.err.refuse", nom=args[0])
            if mot in LECTEURS | {"grep"}:
                for w in (args[1:] if mot == "grep" else args):
                    p = _abs(w, m.avant)
                    if os.path.isdir(p) and not (mot == "grep" and re.search(r"\s-\w*[rR]", x)):
                        return t("core.err.est_dossier", nom=w)
                    if os.path.isfile(p) and not os.access(p, os.R_OK):
                        return t("core.err.refuse", nom=w)
            for r in redirections(x):
                p = _abs(r, m.avant)
                if os.path.isdir(p):
                    return t("core.err.est_dossier", nom=r)
                if (os.path.exists(p) and not os.access(p, os.W_OK)) or (
                        not os.path.exists(p) and os.path.isdir(os.path.dirname(p))
                        and not os.access(os.path.dirname(p), os.W_OK)):
                    return t("core.err.refuse", nom=r)
            if mot in ("touch", "mkdir", "rm", "rmdir", "mv", "cp", "chmod"):
                for w in args:
                    p = _abs(w, m.avant)
                    d = os.path.dirname(p.rstrip("/"))
                    if os.path.isdir(d) and not os.access(d, os.W_OK):
                        # le cadenas est sur le dossier (/etc), pas sur l'objet qu'on voulait créer (coucou.txt)
                        return t("core.err.refuse", nom=os.path.dirname(w.rstrip("/")) or m.avant or w)
        manque = chemins_manquants(m.texte, m.avant)
        if manque:
            from . import maison
            ici = maison.rel(m.avant)
            lieu = (maison.nom_piece(ici.split("/")[0] if ici else "grande_salle") if ici is not None
                    else m.avant.replace(str(Path.home()), "~", 1))
            return t("core.err.introuvable", nom=manque[0], ici=lieu)
    return None
