"""Signaler un souci (idée 76) : `tg bug` prépare un rapport qu'un ADULTE relit, puis envoie lui-même.

Comment ça marche :
  1. d'abord la question des grands (« Tu es un adulte ? » : une multiplication, comme « Tout afficher ») ;
  2. le rapport s'affiche en entier : version, système, langue, taille de l'écran, la commande qui a planté et la
     fin de l'erreur rangée dans ~/.terminagotchi/erreurs.log (noms de fichiers seulement, jamais de dossiers) ;
  3. l'adulte choisit : [o] ouvrir la page GitHub « nouveau signalement » déjà remplie (rien n'est envoyé tant
     qu'il n'a pas cliqué sur le bouton d'envoi de la page, avec SON compte GitHub), [f] l'écrire dans un fichier
     (~/rapport-terminagotchi.txt, à envoyer par e-mail s'il le veut), [n] annuler.
Jamais dans le rapport : le nom de la créature, le pseudo, les fichiers de l'enfant, le nom d'utilisateur ni le
dossier personnel (remplacés par « ~ » ou « … »). Le jeu n'envoie rien lui-même.

Les morceaux communs avec Signaler.kt (nettoyer, rapport, adresse) ont les mêmes vecteurs :
donnees/bug/vecteurs.json (pc/outils/test_signaler.py, tests/jvm/SignalerSynchro.kt).
"""
import os
import platform
import re
import shutil

from . import core
from .langue import t

PAGE = "https://github.com/grecdel/terminagotchi/issues/new"
FICHIER = "rapport-terminagotchi.txt"
TRACE_MAX = 12          # lignes de la trace gardées (les dernières)
LIGNE_MAX = 160         # caractères par ligne de la trace
TITRE_MAX = 80
_NON_RESERVES = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


# ---------------------------------------------------------------- morceaux communs (mêmes vecteurs que Signaler.kt)
def couper(s, n):
    """Au plus n caractères (points de code), « … » à la fin si on a coupé."""
    return s if len(s) <= n else s[:n - 1] + "…"


def nettoyer(texte, home="", utilisateur="", caches=()):
    """Enlève ce qui dirait qui joue : le dossier personnel (→ ~), le nom de la créature et le pseudo (→ …),
    le nom d'utilisateur (→ ~). Les mots de moins de 3 caractères ne sont pas touchés (trop de faux amis)."""
    if home and len(home) >= 3:
        for h in (home, home.replace("\\", "/"), home.replace("/", "\\")):
            texte = texte.replace(h, "~")
    for mot in caches:
        if mot and len(mot) >= 3:
            texte = texte.replace(mot, "…")
    if utilisateur and len(utilisateur) >= 3:
        texte = texte.replace(utilisateur, "~")
    return texte


def rapport(champs, e):
    """(titre, corps) du signalement. champs : version, appareil, langue, ecran, commande, erreur, trace (liste) ;
    e : les étiquettes déjà traduites (faisais, version, appareil, langue, ecran, commande, erreur, sans, pied)."""
    erreur = champs.get("erreur") or ""
    titre = "[bug] " + couper(erreur or e["sans"], TITRE_MAX)
    lignes = [e["faisais"] + " ", ""]
    for k in ("version", "appareil", "langue", "ecran", "commande", "erreur"):
        if champs.get(k):
            lignes.append(e[k] + " " + champs[k])
    trace = [couper(l, LIGNE_MAX) for l in (champs.get("trace") or [])][-TRACE_MAX:]
    if trace:
        lignes += ["", "```"] + trace + ["```"]
    lignes += ["", e["pied"]]
    return titre, "\n".join(lignes)


def coder(s):
    """Encodage d'adresse (UTF-8, tout sauf A-Z a-z 0-9 - . _ ~ en %XX majuscules)."""
    return "".join(chr(b) if b in _NON_RESERVES else "%%%02X" % b for b in s.encode("utf-8"))


def adresse(titre, corps):
    """La page GitHub « nouveau signalement » déjà remplie (rien n'est envoyé : l'adulte relit et clique)."""
    return PAGE + "?title=" + coder(titre) + "&body=" + coder(corps)


# ---------------------------------------------------------------- PC : ce que le rapport contient
_DEBUT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ", re.M)
_CADRE = re.compile(r'^\s*File "(.*)", line (\d+), in (.*)$')


def lire_panne(texte):
    """La dernière panne d'erreurs.log : (commande, erreur, trace). La trace ne garde que des noms de fichiers
    (« monde_dessin.py:212 dessiner »), jamais les dossiers ; l'erreur finit par l'endroit (« (monde_dessin.py:212) »)."""
    debuts = [m.start() for m in _DEBUT.finditer(texte)]
    if not debuts:
        return "", "", []
    bloc = texte[debuts[-1]:].rstrip("\n").split("\n")
    tete = bloc[0][20:]
    commande = ""
    m = re.match(r"\[(.*?)\] ?", tete)
    if m:
        commande, tete = m.group(1), tete[m.end():]
    trace, dernier, erreur = [], "", ""
    for l in [tete] + bloc[1:]:
        c = _CADRE.match(l)
        if c:
            dernier = f"{os.path.basename(c.group(1).replace(chr(92), '/'))}:{c.group(2)}"
            trace.append(f"{dernier} {c.group(3)}")
        elif l.strip() and not l.startswith("    ") and not l.startswith("Traceback"):
            erreur = l.strip()
            trace.append(erreur)
    if erreur and dernier:
        erreur = f"{erreur} ({dernier})"
    return commande, erreur, trace


def _systeme():
    s = platform.system()
    if s == "Windows":
        nom = "Windows " + platform.release()
        if os.environ.get("TG_DANS_LE_JEU"):           # le terminal du jeu (vsh/), pas PowerShell
            nom += " · " + t("bug.terminal_du_jeu")
    elif s == "Darwin":
        nom = "macOS " + platform.mac_ver()[0]
    else:
        nom = s or "?"
    return f"{nom} · Python {platform.python_version()}"


def champs_pc(state=None):
    """Ce que le rapport contiendrait sur ce PC (rien d'autre)."""
    from . import langue
    try:
        log = (core.SAVE_DIR / "erreurs.log").read_text(encoding="utf-8", errors="replace")[-20000:]
    except OSError:
        log = ""
    commande, erreur, trace = lire_panne(log)
    taille = shutil.get_terminal_size((80, 24))
    home = os.path.expanduser("~")
    try:
        import getpass
        util = getpass.getuser()
    except Exception:
        util = ""
    caches = []
    if state:
        caches = [state.get("name") or "", (state.get("compte") or {}).get("pseudo") or ""]

    def n(x):
        return nettoyer(x, home, util, caches)
    return {"version": f"{core.VERSION} · PC", "appareil": _systeme(), "langue": langue.courante(),
            "ecran": f"tg ({taille.columns} × {taille.lines})", "commande": n(commande), "erreur": n(erreur),
            "trace": [n(l) for l in trace]}


def etiquettes():
    return {k: t("bug.l." + k) for k in ("faisais", "version", "appareil", "langue", "ecran", "commande", "erreur",
                                          "sans", "pied")}


# ---------------------------------------------------------------- tg bug
def commande(demander=None, ouvrir=None, dossier=None):
    """tg bug : la question des grands, le rapport, puis [o] la page / [f] le fichier / [n] annuler."""
    from . import apparence
    from .plateforme import BOLD, DIM, RESET, fg
    demander = demander or _demander
    st = None
    try:
        st = core.load()
    except (OSError, core.Probleme):
        st = None
    print(f"{fg(213)}{t('bug.titre')}{RESET}  {fg(214)}{t('bug.adulte')}{RESET}")
    q, rep = apparence.question_adulte()
    if demander(" 🔒 " + t("bug.question", q=q) + " ").strip() != rep:
        return t("bug.non")
    titre, corps = rapport(champs_pc(st), etiquettes())
    print("\n" + BOLD + t("bug.partira") + RESET)
    print(f"{DIM}│{RESET} {titre}")
    for l in corps.split("\n"):
        print(f"{DIM}│{RESET} {l}")
    print("\n" + DIM + t("bug.jamais") + RESET + "\n")
    fichier = os.path.join(dossier or os.path.expanduser("~"), FICHIER)
    print("  " + t("bug.pc.o"))
    print("  " + t("bug.pc.f", fichier=_court(fichier)))
    print("  " + t("bug.pc.n"))
    choix = demander("> ").strip().lower()[:1]
    if choix == "o":
        url = adresse(titre, corps)
        try:
            import webbrowser
            ok = (ouvrir or webbrowser.open)(url)
        except Exception:
            ok = False
        return t("bug.ouverte") if ok else t("bug.pas_navigateur", url=url)
    if choix == "f":
        try:
            with open(fichier, "w", encoding="utf-8", newline="\n") as f:
                f.write(titre + "\n\n" + corps + "\n")
        except OSError as e:
            from . import sur
            return sur.message_os(e)
        return t("bug.ecrit", fichier=_court(fichier))
    return t("bug.annule")


def _court(chemin):
    h = os.path.expanduser("~")
    return "~" + chemin[len(h):] if chemin.startswith(h) else chemin


def _demander(invite):
    try:
        return input(invite)
    except (EOFError, KeyboardInterrupt):
        return ""
