"""Le cerveau de ta créature (`tg cerveau`, et le panneau « Cerveau » de l'espace de travail).

Son cerveau est un VRAI petit programme shell (un `case` sur son état), qui tourne ici, ligne par ligne :
l'interpréteur ci-dessous lit exactement le texte de PROGRAMME (les mêmes règles que bash pour ce petit morceau de
langage : `case … in`, `motif)`, `;;`, `[ $x -lt N ] && …`, `if …; then`, `elif`, `fi`, `x=$((x + y))`, `dire`).
Ce qui s'affiche est ce qui s'exécute : la ligne en cours se surligne, la machine à états (dessinée à partir des
`etat=…` du programme) allume l'état actif et la flèche prise, et la créature prend la pose de son état.

Ses variables :
  faim      la satiété du jeu (0 à 100 : plus c'est bas, plus elle a faim), relue à chaque tour ;
  jeu, sommeil   ses envies du jeu, relues quand le jeu les change (et remontées par `joue` et `dort`) ;
  repas     ce que le dernier repas lui a donné (calculé par le jeu, satiete.py) ;
  commande_tapee / commande_ratee   une commande a été tapée depuis le tour d'avant / elle a échoué.
L'enfant peut FORCER un état : à chaque tour, l'état forcé est remis avant le `case`, et l'on voit sa branche
s'exécuter (la flèche montre où elle irait).

Les noms du code sont traduits (cerv.id.*, des mots simples sans accents ; anglais pour les écritures non latines).
Le même interpréteur tourne sur Android (Cerveau.kt) : vecteurs communs dans donnees/espace/vecteurs.json.
"""
import re
import sys
import time

from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

ETATS = ("content", "faim", "mange", "joue", "dort", "confus")
POSES = {"content": "assis", "faim": "baille", "mange": "mange", "joue": "salut", "dort": "dort", "confus": "sursaut"}
COULEURS = {"content": (233, 236, 242), "faim": (255, 159, 67), "mange": (61, 220, 132), "joue": (255, 121, 198),
            "dort": (178, 132, 255), "confus": (255, 95, 109)}
ANSI = {"content": 255, "faim": 214, "mange": 78, "joue": 211, "dort": 141, "confus": 203}
# la place des états sur le dessin de la machine (fractions de la largeur et de la hauteur)
PLACES = {"faim": (0.27, 0.17), "mange": (0.76, 0.17), "content": (0.5, 0.5), "dort": (0.22, 0.83),
          "joue": (0.8, 0.83), "confus": (0.5, 0.95)}
IDS = ("etat", "faim", "jeu", "sommeil", "repas", "content", "mange", "joue", "dort", "confus", "commande_tapee",
       "commande_ratee", "dire")

PROGRAMME = [
    "# {commentaire}",
    'case "$etat" in',
    "  content)",
    "    [ $faim -lt 30 ] && etat=faim",
    "    [ $sommeil -lt 20 ] && etat=dort",
    "    [ $jeu -lt 30 ] && etat=joue",
    "    if commande_ratee; then etat=confus",
    "    elif commande_tapee; then etat=mange",
    "    fi ;;",
    "  faim)",
    "    if commande_tapee; then",
    "      etat=mange",
    "    fi ;;",
    "  mange)",
    "    faim=$((faim + repas))",
    "    [ $faim -gt 100 ] && faim=100",
    "    etat=content ;;",
    "  joue)",
    "    jeu=$((jeu + 10))",
    "    etat=content ;;",
    "  dort)",
    "    sommeil=$((sommeil + 10))",
    "    [ $sommeil -ge 90 ] && etat=content ;;",
    "  confus)",
    '    dire "{phrase}"',
    "    etat=content ;;",
    "esac",
]

_TEST = re.compile(r"^\[ \$(\w+) -(lt|le|gt|ge|eq|ne) (\d+) \] && (.*)$")
_SI = re.compile(r"^(if|elif) (\w+); then(?: (.*))?$")
_AFF = re.compile(r"^(\w+)=(\w+)$")
_CALC = re.compile(r"^(\w+)=\$\(\((\w+) ([+-]) (\w+)\)\)$")
_DIRE = re.compile(r'^dire "(.*)"$')
_MOTIF = re.compile(r"^(\w+)\)$")


def _comparer(a, op, b):
    return {"lt": a < b, "le": a <= b, "gt": a > b, "ge": a >= b, "eq": a == b, "ne": a != b}[op]


class Trace:
    """Ce qu'a fait un tour : lignes = [(numéro 0…, « fait » | « vrai » | « faux »)] dans l'ordre d'exécution,
    de / vers : l'état avant et après, dit : la phrase dite (ou None)."""
    __slots__ = ("lignes", "de", "vers", "dit")

    def __init__(self, de):
        self.lignes = []
        self.de = de
        self.vers = de
        self.dit = None


def executer(etat, var, signaux, programme=PROGRAMME):
    """Exécute UN tour du programme (le `case` sur etat) : (nouvel état, variables, Trace).
    var : {faim, jeu, sommeil, repas} (entiers) ; signaux : {commande_tapee, commande_ratee} (booléens)."""
    var = dict(var)
    tr = Trace(etat)
    i = 0
    n = len(programme)
    # le `case` : trouver la branche
    while i < n and not programme[i].strip().startswith("case "):
        i += 1
    if i >= n:
        return etat, var, tr
    tr.lignes.append((i, "fait"))
    i += 1
    while i < n:
        s = programme[i].strip()
        m = _MOTIF.match(s)
        if m and m.group(1) == etat:
            tr.lignes.append((i, "fait"))
            i += 1
            break
        if s == "esac":
            tr.lignes.append((i, "fait"))
            return etat, var, tr
        i += 1
    else:
        return etat, var, tr
    pile = []                       # les `if` ouverts : [déjà pris (une branche vraie a été choisie), on exécute]

    def actif():
        return all(x[1] for x in pile)

    def faire(cmd, k):
        nonlocal etat
        cmd = cmd.strip()
        fin = cmd.endswith(";;")
        if fin:
            cmd = cmd[:-2].strip()
        if cmd.endswith("; fi"):
            cmd = cmd[:-4].strip()
        if not cmd:
            return fin
        m = _AFF.match(cmd)
        if m:
            if m.group(1) == "etat":
                etat = m.group(2)
            else:
                var[m.group(1)] = _val(m.group(2), var)
            return fin
        m = _CALC.match(cmd)
        if m:
            a, b = _val(m.group(2), var), _val(m.group(4), var)
            var[m.group(1)] = a + b if m.group(3) == "+" else a - b
            return fin
        m = _DIRE.match(cmd)
        if m:
            tr.dit = m.group(1)
        return fin

    while i < n:
        brute = programme[i]
        s = brute.strip()
        if s == "esac" or (_MOTIF.match(s) and not pile):
            break
        fin_branche = s.endswith(";;")
        coeur = s[:-2].strip() if fin_branche else s
        m = _SI.match(coeur)
        if m and m.group(1) == "if":
            if actif():
                v = bool(signaux.get(m.group(2)))
                tr.lignes.append((i, "vrai" if v else "faux"))
                pile.append([v, v])
                if v and m.group(3):
                    faire(m.group(3), i)
            else:
                pile.append([True, False])
        elif m and m.group(1) == "elif":
            if pile:
                deja = pile[-1][0]
                pile[-1][1] = False
                if not deja and all(x[1] for x in pile[:-1]):
                    v = bool(signaux.get(m.group(2)))
                    tr.lignes.append((i, "vrai" if v else "faux"))
                    pile[-1] = [v, v]
                    if v and m.group(3):
                        faire(m.group(3), i)
        elif coeur == "fi" or coeur.startswith("fi "):
            if pile:
                pile.pop()
            if actif():
                tr.lignes.append((i, "fait"))
        elif s.startswith("#"):
            pass
        elif actif():
            m = _TEST.match(coeur)
            if m:
                v = _comparer(_val(m.group(1), var), m.group(2), int(m.group(3)))
                tr.lignes.append((i, "vrai" if v else "faux"))
                if v:
                    faire(m.group(4), i)
            else:
                tr.lignes.append((i, "fait"))
                faire(coeur, i)
        if fin_branche and not pile:
            break
        i += 1
    tr.vers = etat
    return etat, var, tr


def _val(x, var):
    try:
        return int(x)
    except ValueError:
        return int(var.get(x, 0))


def transitions(programme=PROGRAMME):
    """Les flèches de la machine, lues dans le programme : [(de, vers)] (chaque `etat=X` dans la branche de)."""
    out = []
    cour = None
    for l in programme:
        s = l.strip()
        m = _MOTIF.match(s)
        if m:
            cour = m.group(1)
            continue
        for v in re.findall(r"\betat=(\w+)", s):
            if cour and (cour, v) not in out and v != cour:
                out.append((cour, v))
    return out


# ---------------------------------------------------------------- les mots du code, traduits
def ident(x):
    """Le nom d'un mot du code dans la langue (cerv.id.x)."""
    from .langue import brut
    return t("cerv.id." + x) if brut("cerv.id." + x) is not None else x


def texte_programme(nom="", programme=PROGRAMME):
    """Le programme tel qu'il s'affiche : les noms traduits, le commentaire et la phrase dans la langue."""
    table = {x: ident(x) for x in IDS}
    motif = re.compile(r"\b(" + "|".join(sorted(IDS, key=len, reverse=True)) + r")\b")
    out = []
    for l in programme:
        if l.startswith("# {commentaire}"):
            out.append("# " + t("cerv.commentaire", nom=nom))
            continue
        if "{phrase}" in l:
            out.append(l.replace("dire", table["dire"]).replace("{phrase}", t("cerv.phrase")))
            continue
        out.append(motif.sub(lambda m: table[m.group(1)], l))
    return out


def nom_etat(e):
    return ident(e)


# ---------------------------------------------------------------- un cerveau qui vit
class Cerveau:
    """La créature et son cerveau : un tour toutes les PAS secondes ; la ligne en cours avance de ligne en ligne
    pendant le tour (pour qu'on la suive des yeux)."""
    PAS = 2.4

    def __init__(self, etat="content"):
        self.etat = etat
        self.var = {"faim": 60, "jeu": 60, "sommeil": 80, "repas": 0}
        self.vu = {}                 # les dernières valeurs lues dans le jeu (jeu, sommeil)
        self.force = None
        self.trace = Trace(etat)
        self.t_tour = -1e9
        self.dit = None
        self.total = None
        self.historique = []         # les derniers (de, vers)
        self.faim_jeu = None         # la dernière satiété lue dans le jeu
        self.attente = False         # un repas attend sa ligne `faim=$((faim + repas))`

    def lire_jeu(self, state):
        """Relit le jeu : la satiété (toujours), les envies (quand le jeu les change), le dernier repas, et si une
        commande a été tapée (ou ratée) depuis le tour d'avant. Renvoie les signaux."""
        sig = {"commande_tapee": False, "commande_ratee": False}
        if not state:
            return sig
        try:
            from . import envies
            vals = envies.valeurs(state)
        except Exception:                            # noqa: BLE001
            vals = {}
        faim_jeu = float(state.get("hunger", self.var["faim"]))
        for cle, nom in (("jeu", "jeu"), ("sommeil", "sommeil")):
            v = vals.get(nom)
            if v is not None and (cle not in self.vu or abs(v - self.vu[cle]) >= 1):
                self.var[cle] = int(round(v))
                self.vu[cle] = v
        total = int(state.get("total", 0) or 0)
        if self.total is not None and total > self.total:
            sig["commande_tapee"] = True
            from . import core
            sig["commande_ratee"] = core.DERNIER.get("statut") not in (None, 0)
            # le repas : ce que la commande a donné ; la faim reste celle d'avant jusqu'à la ligne du repas
            avant = self.faim_jeu if self.faim_jeu is not None else faim_jeu
            self.var["repas"] = max(0, int(round(faim_jeu - avant)))
            self.var["faim"] = int(round(avant))
            self.attente = True
        elif not self.attente:
            self.var["faim"] = int(round(faim_jeu))
        self.faim_jeu = faim_jeu
        self.total = total
        return sig

    def tour(self, signaux, maintenant=None):
        """Un tour du programme (avec l'état forcé s'il y en a un)."""
        if self.force:
            self.etat = self.force
        de = self.etat
        self.etat, self.var, self.trace = executer(self.etat, self.var, signaux)
        if self.trace.dit:
            self.dit = self.trace.dit
        if self.trace.vers != de:
            self.historique = (self.historique + [(de, self.trace.vers)])[-6:]
        if self.attente and self.trace.de != "faim" and self.trace.vers != "mange":
            self.attente = False          # le repas a été compté (ou il n'y en aura pas) : la faim suit le jeu
        if self.force:
            self.etat = self.force        # la flèche est montrée, mais l'état reste celui qu'on a choisi
        self.t_tour = maintenant if maintenant is not None else time.monotonic()
        return self.trace

    def ligne_en_cours(self, maintenant):
        """(numéro de la ligne surlignée, genre) à cet instant du tour, ou (None, None)."""
        if not self.trace.lignes:
            return None, None
        par = self.PAS * 0.8 / len(self.trace.lignes)
        k = int((maintenant - self.t_tour) / max(0.05, par))
        k = min(k, len(self.trace.lignes) - 1)
        return self.trace.lignes[k]

    def pose(self):
        return POSES.get(self.etat, "assis")

    def forcer(self, etat):
        """Force un état (ou None : la créature vit toute seule). Le prochain tour montre sa branche."""
        self.force = etat if etat in ETATS else None
        if self.force:
            self.etat = self.force
            self.t_tour = -1e9


# ---------------------------------------------------------------- tg cerveau (dans le terminal)
def ecran(cv, nom, maintenant, largeur=100):
    """Le cerveau en couleurs : le code (ligne en cours surlignée), la machine à états, les variables et les
    interrupteurs (touches 1 à 6, 0 : la laisser vivre)."""
    code = texte_programme(nom)
    k, genre = cv.ligne_en_cours(maintenant)
    faites = {i for i, _g in cv.trace.lignes}
    out = [f" {fg(213)}{BOLD}" + t("cerv.titre", nom=nom) + f"{RESET}   {DIM}cerveau.sh{RESET}", ""]
    gauche = []
    for i, l in enumerate(code):
        num = f"{DIM}{i + 1:>2}{RESET} "
        if i == k:
            c = 78 if genre in ("fait", "vrai") else 203
            gauche.append(f"{fg(c)}▌{RESET}{num}\033[48;5;236m{fg(c)}{BOLD}{l:<44}{RESET}")
        elif i in faites:
            gauche.append(f" {num}{fg(250)}{l}{RESET}")
        else:
            gauche.append(f" {num}{fg(244)}{l}{RESET}")
    droite = _machine_texte(cv)
    for j in range(max(len(gauche), len(droite))):
        g = gauche[j] if j < len(gauche) else ""
        d = droite[j] if j < len(droite) else ""
        from .langue import largeur as lg
        vis = lg(re.sub(r"\033\[[0-9;]*m", "", g))
        out.append(g + " " * max(1, 52 - vis) + d)
    out.append("")
    out.append("  " + "  ".join(f"{fg(117)}{ident(x)}{RESET}={cv.var.get(x, 0)}" for x in ("faim", "jeu", "sommeil",
                                                                                            "repas")))
    if cv.dit:
        out.append(f"  {fg(203)}💬 {cv.dit}{RESET}")
    choix = []
    for n, e in enumerate(ETATS, 1):
        on = cv.force == e
        choix.append(f"{fg(ANSI[e])}[{n}]{RESET} " + (f"{BOLD}\033[7m {nom_etat(e)} {RESET}" if on else nom_etat(e)))
    out.append("  " + t("cerv.forcer") + "  " + "  ".join(choix) + f"   {DIM}[0] " + t("cerv.libre") + RESET)
    out.append(f"  {DIM}" + t("cerv.touches") + RESET)
    return out


def _machine_texte(cv):
    """La machine à états en texte (6 états sur une petite grille), l'actif en couleur vive."""
    def boite(e):
        nom = nom_etat(e)
        if e == cv.etat:
            return f"{fg(ANSI[e])}{BOLD}\033[7m ● {nom} {RESET}"
        return f"{fg(ANSI[e])}●{RESET} {fg(250)}{nom}{RESET}"
    fl = {}
    for de, vers in transitions():
        fl[(de, vers)] = (de, vers) == (cv.trace.de, cv.trace.vers) and de != vers
    def f(de, vers, sym):
        return f"{fg(226)}{BOLD}{sym}{RESET}" if fl.get((de, vers)) else f"{fg(240)}{sym}{RESET}"
    return [f"{DIM}" + t("cerv.machine", n=len(ETATS)) + RESET, "",
            f"   {boite('faim')}  {f('faim', 'mange', '───▶')}  {boite('mange')}",
            f"       {f('content', 'faim', '▲')}              {f('mange', 'content', '╲')}",
            f"       {f('content', 'faim', '│')}               {f('mange', 'content', '▼')}",
            f"            {boite('content')}",
            f"     {f('content', 'dort', '╱')}{f('dort', 'content', '╲')}      {f('content', 'confus', '│')}"
            f"{f('confus', 'content', '▲')}      {f('content', 'joue', '╲')}{f('joue', 'content', '╱')}",
            f"   {boite('dort')}   {boite('confus')}   {boite('joue')}"]


def lancer(etape, args=()):
    """tg cerveau : le cerveau qui vit dans le terminal (q pour quitter)."""
    from . import core
    from .app import Clavier, clear
    cv = Cerveau()
    st = core.load() or {}
    nom = st.get("name", "")
    cv.lire_jeu(st)
    if args and args[0] in ETATS:
        cv.forcer(args[0])
    if not sys.stdout.isatty():
        cv.tour({})
        print("\n".join(ecran(cv, nom, cv.t_tour + 99)) + RESET)
        return
    clav = Clavier()
    dernier = 0.0
    with clav:
        clear()
        while True:
            now = time.monotonic()
            if now - dernier >= cv.PAS:
                try:
                    st = etape(spontane=True, rythme=cv.PAS, defis=False) or st
                except Exception:                    # noqa: BLE001
                    pass
                cv.tour(cv.lire_jeu(st), now)
                dernier = now
            sys.stdout.write("\033[H" + "\n".join(x + "\033[K" for x in ecran(cv, nom, now)) + "\033[J")
            sys.stdout.flush()
            k = clav.touche(0.12)
            if not k:
                continue
            if k.lower() == "q" or k == "\x1b":
                break
            if k == "0":
                cv.forcer(None)
            elif k.isdigit() and 1 <= int(k) <= len(ETATS):
                cv.forcer(ETATS[int(k) - 1])
                dernier = 0.0
    print(RESET)
