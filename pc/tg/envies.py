"""Les 6 envies de la créature (les mêmes règles que Envies.kt sur Android).

  🍎 faim       n'importe quelle commande la nourrit (core.feed) ; elle descend 2 fois moins vite qu'avant
  🎮 jeu        un défi éclair (tg defi), un combat, un dressage réussi
  📚 curiosité  une étape de leçon, une quête finie, une commande jamais goûtée, tg explique, man, --help
  🧭 explorer   entrer dans une pièce jamais visitée, une pièce secrète (quête « cachette »), ls -a ou find
                dans la maison du jeu
  😴 sommeil    elle fatigue en jouant (plus vite le soir) ; `sleep 10` = une vraie sieste (animation « dort ») ;
                elle se repose aussi toute seule quand on ne joue pas
  🧹 propreté   de la « poussière » (poussiere_1.tmp…) tombe avec le temps dans un placard caché du terrain de
                la partie active : ~/terrain_terminagotchi/.cache/ ; la jauge se calcule d'après les VRAIS
                fichiers .tmp présents. On nettoie avec rm .cache/*.tmp (ou rm -r .cache : le jeu recrée le
                placard vide). Rien n'est jamais créé ni supprimé hors du terrain, et rien n'est créé tant
                que le terrain n'existe pas (la leçon 1 le construit).

Chaque jauge va de 0 à 100. Pas de mort ni de punition : une envie à zéro rend la créature triste
(une) ou grognon (plusieurs) ; c'est tout. La faim reste la plus importante : sous FAIM_URGENTE, c'est
toujours elle l'envie du moment.

Seuils choisis (documentés aussi dans `tg envies` et testés par pc/outils/test_envies.py) :
  - usure par commande tapée : jeu 0.7, curiosité 0.6, exploration 0.6, sommeil 0.4 (1.2 le soir, 20 h - 7 h) ;
  - usure avec le temps : jeu 2/h, curiosité et exploration 1.5/h, jamais en dessous de 25 par le temps seul
    (en ton absence, elle ne devient pas triste) ;
  - repos tout seul : après 10 min sans commande, sommeil +25/h ;
  - sieste : sleep N → sommeil +5 par seconde, au plus +50 (sleep 10) ;
  - poussière : un fichier toutes les 45 min de temps réel, au plus 8 (propreté = 100 - 12.5 par fichier) ;
  - envie du moment : la plus basse sous SEUIL (40), tirée au hasard parmi celles à moins de 10 points d'elle ;
    elle reste la même jusqu'à être satisfaite (≥ 60) ou 15 minutes ;
  - rappel dans la bulle : au plus un toutes les 12 commandes ET 5 minutes ; le soir, un bâillement au plus
    toutes les 40 minutes ;
  - récompense : satisfaire une envie basse (< 60) donne +2 XP (+3 de plus si c'était l'envie du moment), au plus
    une fois toutes les 2 minutes par envie ; l'envie du moment qui gagne 15 points ou repasse au-dessus de 60 :
    un merci et l'animation « content ».

Sauvegarde : state["envies"] = {"v": {envie: valeur}, "t": dernier calcul, "cmd_t": dernière commande,
"moment": {"e", "cmd", "t"} | None, "rappel_t", "rappel_n", "soir_t", "vu": {compteurs}, "xp_t": {},
"poussiere_t", "premiere_poussiere"}. Les anciennes sauvegardes reçoivent des valeurs moyennes (MIGRATION).
Tout est local (aucun champ envoyé au serveur : l'anti-triche n'est pas concerné).
"""
import random
import re
import time

from . import core
from .langue import au_hasard, liste, t
from .plateforme import C, IS_WIN

ENVIES = ("faim", "jeu", "curiosite", "explorer", "sommeil", "proprete")
ICONES = {"faim": "🍎", "jeu": "🎮", "curiosite": "📚", "explorer": "🧭", "sommeil": "😴", "proprete": "🧹"}
DEPART = {"jeu": 70.0, "curiosite": 70.0, "explorer": 70.0, "sommeil": 90.0}
MIGRATION = 60.0                     # les anciennes parties : des valeurs moyennes
PAR_COMMANDE = {"jeu": 0.7, "curiosite": 0.6, "explorer": 0.6, "sommeil": 0.4}
SOMMEIL_SOIR = 1.2                   # usure du sommeil par commande, le soir
PAR_HEURE = {"jeu": 2.0, "curiosite": 1.5, "explorer": 1.5}
PLANCHER_TEMPS = 25.0                # le temps seul ne descend jamais une envie sous ce plancher
PAUSE = 600                          # secondes sans commande : elle se repose toute seule
REPOS_HEURE = 25.0
SIESTE_PAR_SECONDE = 5.0
SIESTE_MAX = 50.0
SIESTE_CONSEIL = 10                  # sleep 10
SOIR, MATIN = 20, 7
POUSSIERE_INTERVALLE = 45 * 60
POUSSIERE_MAX = 8
SEUIL = 40.0
FAIM_URGENTE = 40.0                  # = « affamée » (satiete.FORME)
SATISFAITE = 60.0
MERCI = 15.0                         # un plaisir d'au moins 15 points sur l'envie du moment : merci (elle repart)
PROCHES = 10.0
MOMENT_DUREE = 15 * 60
RAPPEL_COMMANDES = 12
RAPPEL_MINUTES = 5
SOIR_MINUTES = 40
XP_BAS = 2
XP_MOMENT = 3
XP_DELAI = 120
GAINS = {"nouvelle": 10.0, "explique": 20.0, "lecon": 15.0, "quete": 25.0, "lieu": 15.0, "secret": 40.0,
         "regarde": 8.0, "defi": 35.0, "combat": 30.0, "dressage": 40.0}

CACHE = ".cache"
_SLEEP = re.compile(r"^\s*(sleep|start-sleep)\s+(?:-s(?:econds)?\s+)?(\d+(?:\.\d+)?)s?\s*$", re.I)
_CURIEUX = re.compile(r"^\s*(?:tg\s+)?(explique|man|help|get-help)\b|\s--help\b|^\s*tg\s+(aide|lexique)\b", re.I)
_REGARDE = re.compile(r"^\s*(ls\s+-\w*a|dir\s+-force|gci\s+-force|get-childitem\b.*-force|find\b|tree\b)", re.I)


def terrain():
    return core.TERRAIN


def placard():
    return terrain() / CACHE


def e_(state):
    """L'état des envies, créé (ou complété) à la demande. Une partie neuve part de DEPART, une ancienne de MIGRATION."""
    e = state.get("envies")
    if not isinstance(e, dict):
        neuve = not state.get("total") and not state.get("xp")
        e = state["envies"] = {"v": {k: (v if neuve else MIGRATION) for k, v in DEPART.items()}}
    now = time.time()
    v = e.setdefault("v", {})
    for k in DEPART:
        if not isinstance(v.get(k), (int, float)):
            v[k] = MIGRATION
    for k, d in {"t": now, "cmd_t": 0, "moment": None, "rappel_t": 0, "rappel_n": 0, "soir_t": 0, "vu": None,
                 "xp_t": {}, "poussiere_t": now, "premiere_poussiere": False}.items():
        e.setdefault(k, d)
    return e


def soir(heure=None):
    h = time.localtime().tm_hour if heure is None else heure
    return h >= SOIR or h < MATIN


# ---------------------------------------------------------------- la poussière (seulement dans le terrain)
def poussieres():
    """Les vrais fichiers de poussière présents (*.tmp du placard caché du terrain)."""
    try:
        return sorted(p for p in placard().iterdir() if p.is_file() and p.suffix.lower() == ".tmp")
    except OSError:
        return []


def proprete():
    if not terrain().is_dir():
        return 100.0
    return max(0.0, 100.0 - 100.0 * len(poussieres()) / POUSSIERE_MAX)


def _poser_poussiere():
    """Un fichier de poussière de plus, dans le placard du terrain (jamais ailleurs). Renvoie True si posé."""
    T = terrain()
    if not T.is_dir():
        return False
    d = placard()
    try:
        d.mkdir(exist_ok=True)
        if d.resolve().parent != T.resolve():
            return False                                     # placard remplacé par un lien : on ne touche à rien
        noms = {p.name for p in poussieres()}
        if len(noms) >= POUSSIERE_MAX:
            return False
        i = next(i for i in range(1, 1000) if f"poussiere_{i}.tmp" not in noms)
        (d / f"poussiere_{i}.tmp").write_text(t("env.poussiere.contenu") + "\n", encoding="utf-8")
        return True
    except (OSError, StopIteration):
        return False


def _poussiere(state, e, now):
    """Le temps qui passe fait tomber de la poussière ; un placard effacé (rm -r .cache) est recréé vide."""
    T = terrain()
    if not T.is_dir():
        e["poussiere_t"] = now
        return
    if not placard().exists():
        try:
            placard().mkdir()
        except OSError:
            pass
    n = int((now - e["poussiere_t"]) // POUSSIERE_INTERVALLE)
    if n <= 0:
        return
    e["poussiere_t"] += n * POUSSIERE_INTERVALLE
    posees = sum(1 for _ in range(min(n, POUSSIERE_MAX)) if _poser_poussiere())
    if posees and not e["premiere_poussiere"]:
        e["premiere_poussiere"] = True
        core.say(state, t("env.poussiere.premiere", cmd=commande_envies()), 12)


# ---------------------------------------------------------------- ce qui fait plaisir
def commande_envies():
    return "tg envies"


def compteurs(state):
    """Ce qui se voit dans la sauvegarde : commandes goûtées, leçons, quêtes, pièces visitées."""
    from . import histoire, maison, quetes
    h = histoire.h_(state)
    q = quetes.q_(state)
    secrets = [x for x in q["finies"] if quetes.PAR_ID.get(x, {}).get("sorte") == "cachette"]
    lieux = {v for v in maison.m_(state)["visites"] if v.count("/") <= 1 and not v.startswith(CACHE)}
    return {"seen": len(state.get("seen", [])), "lecon": len(h["faits"]) * 50 + int(state.get("step", 0)),
            "quetes": len(q["finies"]) - len(secrets), "secrets": len(secrets), "lieux": len(lieux)}


def valeur(state, nom):
    if nom == "faim":
        return float(state.get("hunger", 0))
    if nom == "proprete":
        return proprete()
    return float(e_(state)["v"][nom])


def valeurs(state):
    return {k: valeur(state, k) for k in ENVIES}


def gagner(state, nom, n):
    """Satisfait une envie (n points). La récompense : un peu d'XP, et un merci si c'était l'envie du moment."""
    e = e_(state)
    if nom == "faim":
        avant = float(state.get("hunger", 0))
        state["hunger"] = min(100.0, avant + n)
    elif nom == "proprete":
        avant = 0.0                                          # la propreté se lit dans les fichiers : déjà à jour
    else:
        avant = e["v"][nom]
        e["v"][nom] = min(100.0, avant + n)
    m = e.get("moment") or {}
    du_moment = m.get("e") == nom
    now = time.time()
    if avant < SATISFAITE and n >= 8 and now - e["xp_t"].get(nom, 0) >= XP_DELAI:
        e["xp_t"][nom] = now
        core.add_xp(state, XP_BAS + (XP_MOMENT if du_moment else 0))
    if du_moment and (valeur(state, nom) >= SATISFAITE or n >= MERCI):
        e["moment"] = None
        core.say(state, au_hasard("env.merci." + nom), 8)
        core.animer(state, "content")


def plaisir(state, nom, cle):
    """Appelé par les jeux (défi, combat, dressage) : l'envie de jouer est satisfaite."""
    gagner(state, nom, GAINS[cle])


def sieste(state, secondes):
    """sleep N : une vraie sieste (déjà faite par le shell). Renvoie les points de sommeil gagnés."""
    n = min(SIESTE_MAX, max(0.0, secondes) * SIESTE_PAR_SECONDE)
    if n <= 0:
        return 0
    core.log(state, t("env.sieste.log", s=f"{secondes:g}", n=int(n)))
    core.animer(state, "dort")
    gagner(state, "sommeil", n)
    return n


def _salle(state):
    """Le dossier courant s'il est la grande salle du terrain (là où « rm .cache/*.tmp » vise le bon placard), sinon None."""
    from . import maison
    ici = maison.ici(state)
    return ici if ici and maison.rel(ici) == "" else None


def _dans_terrain(state):
    from . import maison
    cwd = maison.ici(state)
    return cwd is not None and maison.rel(cwd) is not None


# ---------------------------------------------------------------- le temps qui passe
def _temps(e, now):
    v = e["v"]
    dt = max(0.0, min(now - e["t"], 7 * 24 * 3600))
    if dt <= 0:
        return
    for k, par_h in PAR_HEURE.items():
        if v[k] > PLANCHER_TEMPS:
            v[k] = max(PLANCHER_TEMPS, v[k] - par_h * dt / 3600)
    debut_repos = max(e["t"], e["cmd_t"] + PAUSE)        # le repos commence 10 min après la dernière commande
    if now > debut_repos:
        v["sommeil"] = min(100.0, v["sommeil"] + REPOS_HEURE * (now - debut_repos) / 3600)
    e["t"] = now


# ---------------------------------------------------------------- l'envie du moment et la bulle
def suggestion(state, nom):
    """La commande à proposer pour cette envie (sans danger, depuis là où est l'enfant)."""
    from . import histoire, lecons, maison
    T = f"~/{terrain().name}"
    if nom == "faim":
        idees, _ = core.faim_d_apprendre(state, core.level(state["xp"]) + 1)
        return random.choice(idees[:2])
    if nom == "jeu":
        return "tg defi"
    if nom == "curiosite":
        les, _ = lecons.lecon_courante(state)
        if les and core.level(state["xp"]) >= les["niveau"] and random.random() < 0.5:
            return les["steps"][state["step"]]["cmd"]
        return random.choice(["tg explique " + c for c in ("cp", "mv", "ls", "grep", "rm", "find")] +
                             ([] if IS_WIN else ["man ls", "ls --help"]))
    if nom == "explorer":
        if terrain().is_dir():
            neuves = [p for p in maison.PIECES if histoire.piece_ouverte(state, p) and (terrain() / p).is_dir()
                      and not maison.visitee(state, p)]
            if neuves:
                return f"cd {T}/{random.choice(neuves)}"
            if _dans_terrain(state):
                return C("ls -a", "dir -Force")
        return "tg carte"
    if nom == "sommeil":
        return C(f"sleep {SIESTE_CONSEIL}", f"Start-Sleep {SIESTE_CONSEIL}")
    # propreté : seulement depuis la grande salle du terrain (rm .cache/*.tmp ailleurs viserait un autre placard !)
    if _salle(state):
        return random.choice([C("ls -a", "dir -Force"), "ls .cache", "rm .cache/*.tmp"]) \
            if len(poussieres()) else "ls .cache"
    return f"cd {T}"


def choisir(state, vals=None):
    """L'envie à mettre en avant (ou None si tout va bien) : la faim d'abord si elle est urgente,
    sinon la plus basse sous SEUIL, avec un peu de hasard entre les envies proches."""
    vals = vals or valeurs(state)
    if not terrain().is_dir():
        vals["proprete"] = 100.0
    if vals["faim"] < FAIM_URGENTE:
        return "faim"
    basses = {k: v for k, v in vals.items() if v < SEUIL and k != "faim"}
    if not basses:
        return None
    mini = min(basses.values())
    return random.choice(sorted(k for k, v in basses.items() if v <= mini + PROCHES))


def moment(state):
    """L'envie du moment, gardée stable (même commande) jusqu'à être satisfaite ou MOMENT_DUREE."""
    e = e_(state)
    m = e.get("moment")
    now = time.time()
    if m and m.get("e") in ENVIES and valeur(state, m["e"]) < SATISFAITE and now - m.get("t", 0) < MOMENT_DUREE:
        if not (m["e"] != "faim" and valeur(state, "faim") < FAIM_URGENTE):
            if m["e"] == "proprete" and m["cmd"].startswith("cd ") != (_salle(state) is None):
                m["cmd"] = suggestion(state, "proprete")      # l'enfant est arrivé (ou reparti) : la commande suit
            return m
    nom = choisir(state)
    e["moment"] = {"e": nom, "cmd": suggestion(state, nom), "t": now} if nom else None
    return e["moment"]


def phrase(state, m=None):
    m = m or moment(state)
    if not m:
        return None
    return au_hasard("env.dit." + m["e"], cmd=m["cmd"])


def _rappeler(state, e, tapees, now):
    e["rappel_n"] += tapees
    m = moment(state)
    if m and e["rappel_n"] >= RAPPEL_COMMANDES and now - e["rappel_t"] >= RAPPEL_MINUTES * 60:
        e["rappel_n"] = 0
        e["rappel_t"] = now
        e["rappel_texte"] = phrase(state, m)
        core.say(state, e["rappel_texte"], 12)
        core.animer(state, "dort" if m["e"] == "sommeil" else "parle")
        return
    if tapees and soir() and now - e["soir_t"] >= SOIR_MINUTES * 60 and e["v"]["sommeil"] < 70:
        e["soir_t"] = now
        core.say(state, au_hasard("env.soir"), 12)
        core.animer(state, "dort")


def rappel_recent(state, secondes=120):
    """La dernière bulle d'envie si elle vient d'être dite (pour la ligne du compagnon)."""
    e = e_(state)
    return e.get("rappel_texte") if time.time() - e.get("rappel_t", 0) < secondes else None


# ---------------------------------------------------------------- le tour de jeu
def tick(state, lignes):
    """À la fin de chaque étape de jeu (app.boucle_jeu), après les leçons, les quêtes et les combats."""
    e = e_(state)
    now = time.time()
    _temps(e, now)
    tapees = [l for l in lignes if not core.est_colle(l) and core.first_word(l)]
    v = e["v"]
    for l in tapees:
        e["cmd_t"] = now
        for k, n in PAR_COMMANDE.items():
            if k == "sommeil" and soir():
                n = SOMMEIL_SOIR
            v[k] = max(0.0, v[k] - n)
        m = _SLEEP.match(l)
        if m:
            sieste(state, float(m.group(2)))
        elif _CURIEUX.search(l):
            gagner(state, "curiosite", GAINS["explique"])
        if _REGARDE.match(l) and _dans_terrain(state):
            gagner(state, "explorer", GAINS["regarde"])
    vu, c = e.get("vu"), compteurs(state)
    if isinstance(vu, dict):
        if c["seen"] > vu.get("seen", 0):
            gagner(state, "curiosite", min(2, c["seen"] - vu.get("seen", 0)) * GAINS["nouvelle"])
        if c["lecon"] > vu.get("lecon", 0):
            gagner(state, "curiosite", GAINS["lecon"])
        if c["quetes"] > vu.get("quetes", 0):
            gagner(state, "curiosite", GAINS["quete"])
        if c["secrets"] > vu.get("secrets", 0):
            gagner(state, "explorer", GAINS["secret"])
        if c["lieux"] > vu.get("lieux", 0):
            gagner(state, "explorer", min(2, c["lieux"] - vu.get("lieux", 0)) * GAINS["lieu"])
    e["vu"] = c
    m = e.get("moment") or {}
    if m.get("e") == "faim" and valeur(state, "faim") >= SATISFAITE:      # elle a bien mangé (core.feed)
        e["moment"] = None
        core.say(state, au_hasard("env.merci.faim"), 8)
        core.animer(state, "content")
    avant = e.get("propre_n")
    from . import intro
    ouvert = intro.ouvert(state, "envies")          # avant leur présentation : pas de poussière ni de rappel
    if ouvert:
        _poussiere(state, e, now)
    n = len(poussieres())
    if avant is not None and n < avant and tapees:
        m = e.get("moment") or {}
        if n == 0 or m.get("e") == "proprete":
            gagner(state, "proprete", 100)
            if m.get("e") != "proprete":
                core.say(state, au_hasard("env.merci.proprete"), 8)
                core.animer(state, "content")
    e["propre_n"] = n
    if ouvert:
        _rappeler(state, e, len(tapees), now)


# ---------------------------------------------------------------- humeur et affichage
def humeur_cle(state):
    """L'humeur combine les envies : la faim d'abord (la santé), puis les envies à zéro, puis la moyenne."""
    vals = valeurs(state)
    from . import satiete
    e = satiete.etat(state)
    if e == "veille":
        return "sat.etat.veille"                       # en veille (jamais de mort) : un repas complet la réveille
    if e == "affamee":
        return "humeur.affame"
    zeros = sum(1 for k, x in vals.items() if k != "faim" and x < 1)
    if zeros >= 2:
        return "humeur.grognon"
    if zeros == 1:
        return "humeur.triste"
    if sum(vals.values()) / len(vals) >= 70:
        return "humeur.joyeux"
    return "humeur.repu" if vals["faim"] >= 60 else "humeur.creux"


def humeur(state):
    return t(humeur_cle(state))


def barre(v, n):
    k = max(0, min(n, int(v / 100 * n + 0.5)))
    return "▰" * k + "▱" * (n - k)


def compact(state, n=4, par_ligne=3):
    """Les 6 jauges en petit : « 🍎▰▰▰▱ 🎮▰▰▱▱ 📚▰▰▰▰ » (2 lignes de 3)."""
    vals = valeurs(state)
    morceaux = [ICONES[k] + barre(vals[k], n) for k in ENVIES]
    return [" ".join(morceaux[i:i + par_ligne]) for i in range(0, len(morceaux), par_ligne)]


def nom(envie):
    return t("env.nom." + envie)


def comment(state, envie):
    T = f"~/{terrain().name}"
    p = {"faim": {"cmds": "`date`, `ls`, `whoami`"},
         "jeu": {"cmds": "`tg defi`"},
         "curiosite": {"cmds": "`tg explique cp`" + ("" if IS_WIN else ", `man ls`, `ls --help`")},
         "explorer": {"cmds": "`tg carte`", "lsa": "`" + C("ls -a", "dir -Force") + "`"},
         "sommeil": {"cmd": f"`{C('sleep 10', 'Start-Sleep 10')}`"},
         "proprete": {"aller": f"`cd {T}`", "voir": "`" + C("ls -a", "dir -Force") + "`, `ls .cache`"
                      + ("" if IS_WIN else ", `find . -name \"*.tmp\"`"), "nettoyer": "`rm .cache/*.tmp`"}}[envie]
    return t("env.comment." + envie, **p)


def ecran(state):
    """tg envies : l'état détaillé, et pour chaque envie comment la satisfaire."""
    from .langue import ajuster, envelopper, largeur
    from .plateforme import BOLD, DIM, RESET, fg
    vals = valeurs(state)
    lg = max(largeur(nom(k)) for k in ENVIES)
    out = [f" {fg(213)}{BOLD}" + t("env.ecran.titre", nom=state["name"]) + RESET, ""]
    for k in ENVIES:
        x = vals[k]
        c = 78 if x >= 60 else 221 if x >= SEUIL else 203
        out.append(f" {ICONES[k]} {ajuster(nom(k), lg)} {fg(c)}{barre(x, 10)}{RESET} {int(x):>3}")
        for l in envelopper(comment(state, k), 72):
            out.append(f"      {DIM}{l}{RESET}")
    out.append("")
    m = moment(state)
    out.append(" " + (t("env.ecran.moment", icone=ICONES[m["e"]], envie=nom(m["e"]), cmd=m["cmd"]) if m
                      else t("env.ecran.aucune", nom=state["name"])))
    out.append(" " + t("env.ecran.humeur", humeur=humeur(state)))
    out.append("")
    from . import satiete
    out.append(f" {fg(213)}{BOLD}" + t("sat.ecran.titre") + RESET)      # la satiété : état, assiette, série, vacances
    for x in satiete.lignes(state):
        for l in envelopper(x, 76):
            out.append(f"  {l}")
    out.append("")
    for cle in ("env.cache.enfant", "env.cache.grands"):
        for l in envelopper(t(cle, lsa="`" + C("ls -a", "dir -Force") + "`"), 76):
            out.append(f" {DIM}{l}{RESET}")
    out.append("")
    for l in envelopper(t("env.ecran.pied", nom=state["name"]), 76):
        out.append(f" {DIM}{l}{RESET}")
    return out


def tout_lister():
    """(pour les tests) les clés de phrases de chaque envie."""
    return {k: liste("env.dit." + k) for k in ENVIES}
