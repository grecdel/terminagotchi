"""Le thème « créature » (maquettes validées le 3 novembre ; les mêmes règles dans Creature.kt sur Android).

  11. Humeurs du moment : 8 humeurs gentilles (curieux, fier, câlin, gourmand, enjoué, rêveur, surpris, bavard) et
      « en fête », pendant quelques minutes après un événement simple, puis l'humeur habituelle revient (envies.py).
      Une humeur du moment passe devant « triste » et « grognon » (jamais devant « affamé » ni la veille : la santé).
  12. Goûts : le plat préféré (le champ `attiree_par` du bestiaire), l'aliment préféré (selon le type de l'espèce) et
      un goût secret tiré pour chaque créature. Le plat préféré ou le goût secret compte double pour la faim, sans XP en
      plus (l'anti-répétition reste) ; jamais de commande « détestée ».
  16. Album : la date, le niveau et un souvenir de chaque stade (le compagnon : bébé, ado, adulte ; une bestiole de
      l'équipe : ses 5 stades), et les pages des fêtes. `tg album [nom]`, onglet « Album » de l'espace.
  17. Éclosiversaire : 1, 2, 3 et 6 mois, puis chaque année ; un jour manqué est fêté à la visite suivante.
  18. Envie mystère : la créature décrit une commande déjà vue sans la donner ; `tg indice` (3 au plus, le dernier
      donne la réponse), `tg indice plus-tard` la range. Après le chapitre 1, au plus 2 par jour, pas de minuteur,
      la même joie avec ou sans indice, pas d'XP en plus (un « goût » de plus dans l'album).
  84. Moment d'évolution : les pixels qui arrivent, l'animation d'évolution du jeu, l'éclat, la carte ; on peut
      passer au bout de 2 s (phase_evolution, peut_passer) ; un petit son si le moteur de sons existe (son()).
  85. Promenade : dans la fenêtre « en direct », elle marche sur un sol aux couleurs de son biome (bureau_vie) ;
      réglage « rester sur place » (state["config"]["direct_sur_place"]).

Les calculs purs (choisir_humeur, humeur_active, variete, pause_calin, aliment, gout_secret, ajouter_mois, fete_due,
eligibles, peut_proposer, choisir_devinette, trouve, phase_evolution, peut_passer, pages_migration) ont des vecteurs
communs avec Kotlin : donnees/creature/vecteurs.json (pc/outils/test_creature.py, tests/jvm/Creature.kt).

Sauvegarde : state["creature"] = {"humeur": {"h", "t"} | None, "derniere_t", "derniers": [mots], "soir_jour",
"eclosion", "fetes": [mois], "fete": {"m", "t"} | None, "album": {stade: {"t", "niv", "s": [clé, valeur]}},
"pages": [{"m", "t"}], "graine", "secret", "gouts", "envie": {"id", "k", "t"} | None, "envies_jour": [jour, n],
"depuis", "derniere_dev", "evolution": {"de", "vers", "t"} | None}. Tout est local (rien n'est envoyé).
"""
import datetime
import json
import pkgutil
import random
import re
import time

from . import core
from .langue import au_hasard, t
from .plateforme import IS_WIN

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "creature.json").decode("utf-8"))
    return _D


def _par_id():
    return {d["id"]: d for d in donnees()["devinettes"]}


# ================================================================ calculs purs (les mêmes en Kotlin)
def choisir_humeur(evts):
    """L'humeur du moment parmi les événements (la plus importante d'abord), ou None."""
    return next((h for h in donnees()["priorite"] if h in evts), None)


def humeur_active(h, now):
    """La clé de l'humeur du moment si elle dure encore (3 min ; 10 min pour la fête), sinon None."""
    if not isinstance(h, dict) or h.get("h") not in donnees()["humeurs"]:
        return None
    duree = donnees()["fete_duree"] if h["h"] == "fete" else donnees()["humeur_duree"]
    return h["h"] if 0 <= now - float(h.get("t", 0)) < duree else None


def variete(derniers, n=None):
    """Les n dernières commandes sont toutes différentes (« enjoué »)."""
    n = n or donnees()["variete"]
    return len(derniers) >= n and len(set(derniers[-n:])) == n


def pause_calin(dernier, now):
    """On revient après une pause (30 min sans commande) : « câlin »."""
    return dernier > 0 and now - dernier >= donnees()["pause_calin"]


def aliment(type_):
    """L'aliment préféré (une famille de l'assiette, satiete.FAMILLES) d'un type d'espèce."""
    return donnees()["aliments"].get(type_)


def gout_secret(graine, plat=None):
    """Le goût secret d'une créature (jamais son plat préféré)."""
    s = [x for x in donnees()["secrets"] if x != plat]
    return s[int(graine) % len(s)]


def jours_du_mois(a, m):
    if m == 2:
        return 29 if a % 4 == 0 and (a % 100 != 0 or a % 400 == 0) else 28
    return 30 if m in (4, 6, 9, 11) else 31


def ajouter_mois(a, m, j, n):
    """(a, m, j) + n mois ; le 31 devient le dernier jour du mois s'il est plus court."""
    k = m - 1 + n
    a2, m2 = a + k // 12, k % 12 + 1
    return a2, m2, min(j, jours_du_mois(a2, m2))


def date_locale(ts):
    d = datetime.datetime.fromtimestamp(ts)
    return d.year, d.month, d.day


def jalons(jusqua=1200):
    """Les fêtes, en mois : 1, 2, 3, 6, puis chaque année."""
    return list(donnees()["fetes_mois"]) + list(range(12, jusqua + 1, 12))


def fete_due(eclosion, now, faites):
    """[mois, en_retard] : la fête à faire maintenant (la plus récente atteinte, pas encore fêtée), sinon None.
    Les fêtes plus anciennes jamais faites (longue absence) ne sont pas rattrapées une par une."""
    if not eclosion or now < eclosion:
        return None
    e = date_locale(eclosion)
    auj = date_locale(now)
    due = None
    for m in jalons():
        d = ajouter_mois(*e, m)
        if d > auj:
            break
        due = (m, d)
    if due is None or due[0] in faites:
        return None
    return [due[0], due[1] < auj]


def eligibles(vus, win=False):
    """Les devinettes possibles : une commande déjà goûtée (jamais une inconnue), sans celles sans équivalent Windows."""
    vus = set(vus)
    return [d["id"] for d in donnees()["devinettes"] if any(v in vus for v in d["vu"]) and (not win or d.get("win"))]


def peut_proposer(chap1, n_jour, active, depuis, moment):
    """Une envie mystère peut arriver : après le chapitre 1, pas déjà une, au plus 2 par jour, après 15 commandes,
    et pas pendant une envie habituelle."""
    d = donnees()
    return bool(chap1) and not active and n_jour < d["envies_par_jour"] and depuis >= d["envie_apres"] and not moment


def choisir_devinette(elig, n, derniere=None):
    if not elig:
        return None
    c = [x for x in elig if x != derniere] or list(elig)
    return c[int(n) % len(c)]


def trouve(dev_id, ligne):
    d = _par_id().get(dev_id)
    return bool(d) and re.search(d["re"], ligne or "", re.I) is not None


def phase_evolution(t_):
    """(phase, avancement 0..1) du moment d'évolution : appel (les pixels arrivent), transformation (l'animation
    du jeu), eclat, puis fete (la nouvelle forme et sa carte)."""
    e = donnees()["evolution"]
    bornes = (("appel", e["appel"]), ("transformation", e["transformation"]), ("eclat", e["eclat"]))
    debut = 0.0
    for nom, duree in bornes:
        if t_ < debut + duree:
            return nom, round(max(0.0, t_ - debut) / duree, 4)
        debut += duree
    return "fete", round(min(1.0, (t_ - debut) / e["carte"]), 4)


def peut_passer(t_):
    return t_ >= donnees()["evolution"]["passer"]


def pages_migration(stades, i_actuel):
    """Une créature déjà grande quand l'album arrive : ses stades passés sont « avant l'album »."""
    return {s: {"avant": True} for k, s in enumerate(stades) if k <= i_actuel}


def numero_jour(ts):
    a, m, j = date_locale(ts)
    return datetime.date(a, m, j).toordinal()


# ================================================================ l'état
def stade_compagnon(state):
    """Le stade du compagnon en nom du bestiaire (« bebe », « ado », « adulte »), ou None (l'œuf)."""
    from . import sprites
    st = core.stage(core.level(state.get("xp", 0)))
    return sprites.STADE_ESPECE.get(st) if st >= 1 else None


def c_(state):
    c = state.get("creature")
    if not isinstance(c, dict):
        c = state["creature"] = {}
    for k, v in {"humeur": None, "derniere_t": 0, "derniers": [], "soir_jour": 0, "fetes": [], "fete": None,
                 "album": {}, "pages": [], "secret": False, "gouts": 0, "envie": None, "envies_jour": [0, 0],
                 "depuis": 0, "derniere_dev": None, "evolution": None}.items():
        c.setdefault(k, v)
    if "graine" not in c:
        c["graine"] = random.randrange(1 << 30)
    s = stade_compagnon(state)
    if s and not c.get("eclosion"):
        c["eclosion"] = float(state.get("born") or time.time())   # une créature déjà éclose : sa date de création
    if s and not c["album"]:
        stades = donnees()["album_stades_compagnon"]
        c["album"] = pages_migration(stades, stades.index(s))
    return c


def espece(state):
    from . import sprites
    return sprites.espece_compagnon(state)


def type_espece(state):
    e = espece(state)
    if not e:
        return None
    from . import guide
    return guide.type_de(e)


def plat(state):
    e = espece(state)
    return e.get("attiree_par") if e else None


def secret(state):
    return gout_secret(c_(state)["graine"], plat(state)) if espece(state) else None


def son(nom, state=None):
    """Un petit son par le moteur de sons du jeu (sons.son : il respecte les réglages, silencieux par défaut)."""
    try:
        from . import sons
        sons.son(nom, state)
        return True
    except Exception:               # noqa: BLE001
        return False


def humeur(state, now=None):
    """L'humeur du moment (clé de creature.json) ou None."""
    c = state.get("creature")
    if not isinstance(c, dict):
        return None
    return humeur_active(c.get("humeur"), time.time() if now is None else now)


def couleur(h):
    x = donnees()["humeurs"][h]["couleur"]
    return tuple(int(x[i:i + 2], 16) for i in (1, 3, 5))


def _dire(state, texte, secs=8):
    b = state.get("bubble")
    if b and time.time() < b[1]:
        return                       # elle parle déjà (bravo d'une leçon, envie…) : l'humeur se voit sans phrase
    core.say(state, texte, secs)


def poser_humeur(state, h, now=None, dire=True):
    c = c_(state)
    now = time.time() if now is None else now
    avant = humeur_active(c.get("humeur"), now)
    c["humeur"] = {"h": h, "t": now}
    info = donnees()["humeurs"][h]
    if info.get("anim"):
        core.animer(state, info["anim"])
    if dire and h != avant and h not in ("gourmand", "fete"):
        _dire(state, au_hasard("cr.humeur." + h + ".dit", nom=state.get("name", "")))


# ---------------------------------------------------------------- 12. les repas (appelé par core.feed)
def apres_repas(state, cmd, gain):
    """Une commande bien mangée (ni ratée ni répétée) : le plat préféré ou le goût secret compte double pour la faim.
    Renvoie la petite phrase à ajouter au journal (« ♥ son plat préféré ! »)."""
    if not espece(state) or not stade_compagnon(state):
        return ""
    c = c_(state)
    p, s = plat(state), secret(state)
    if cmd not in (p, s) or gain <= 0:
        return ""
    state["hunger"] = min(100.0, float(state.get("hunger", 0)) + gain)
    c["_gourmand"] = True
    if cmd == p:
        _dire(state, t("cr.plat.dit", cmd=cmd))
        return t("cr.plat.journal")
    if not c["secret"]:
        c["secret"] = True
        core.terminal(state, t("cr.secret.trouve", cmd=cmd, nom=state.get("name", "")))
        _dire(state, t("cr.secret.dit", cmd=cmd))
    return t("cr.secret.journal")


# ---------------------------------------------------------------- 16, 84. les stades (appelé par core.add_xp)
def stade_change(state, ancien, nouveau):
    """Le compagnon change de stade (core.stage ancien → nouveau)."""
    from . import sprites
    c = c_(state)
    now = time.time()
    v = sprites.STADE_ESPECE.get(nouveau)
    if not v:
        return
    if ancien == 0:
        c["eclosion"] = now
    seen = state.get("seen", [])
    souv = ["cr.souv.premiere", seen[0]] if v == "bebe" and seen else ["cr.souv.gouts", len(seen)]
    c["album"][v] = {"t": now, "niv": core.level(state.get("xp", 0)), "s": souv}
    if ancien >= 1:
        c["evolution"] = {"de": sprites.STADE_ESPECE.get(ancien), "vers": v, "t": now}


def equipe_evolue(ind):
    """Une bestiole de l'équipe change de stade (equipe.gagner) : la date dans son album."""
    a = ind.setdefault("album", {})
    if isinstance(a, dict):
        a[ind.get("stade", "bebe")] = time.time()


# ---------------------------------------------------------------- le tour de jeu
_SLEEP = re.compile(r"^\s*(sleep|start-sleep)\s+", re.I)
_BAVARD = re.compile(r"^\s*(?:tg\s+)?(explique|man|help|get-help)\b|\s--help\b", re.I)
_CACHE = re.compile(r"^\s*(ls\s+-\w*a|dir\s+-force|gci\s+-force|get-childitem\b.*-force)", re.I)


def avant(state):
    """Ce qu'il faut retenir avant les repas (app.boucle_jeu) pour reconnaître les événements après."""
    from . import envies
    try:
        cpt = envies.compteurs(state)
    except Exception:                                        # noqa: BLE001
        cpt = {}
    return {"seen": len(state.get("seen", [])), "lecon": cpt.get("lecon", 0)}


def _chap1(state):
    from . import histoire
    try:
        return histoire.fini(state, "reveil")
    except Exception:                                        # noqa: BLE001
        return False


def tick(state, lignes, av=None):
    """Après chaque étape de jeu (app.boucle_jeu, après les envies) : humeur, fête, envie mystère."""
    if not stade_compagnon(state):
        return
    from . import envies
    c = c_(state)
    now = time.time()
    tapees = [l for l in lignes if not core.est_colle(l) and core.first_word(l)]
    if not tapees:
        return
    av = av or {}
    evts = set()
    cpt = envies.compteurs(state)
    if len(state.get("seen", [])) > av.get("seen", 1 << 30):
        evts.add("curieux")
    if cpt.get("lecon", 0) > av.get("lecon", 1 << 30):
        evts.add("fier")
    if pause_calin(float(c["derniere_t"]), now):
        evts.add("calin")
    if c.pop("_gourmand", False):
        evts.add("gourmand")
    c["derniers"] = (c["derniers"] + [core.first_word(l) for l in tapees])[-8:]
    if variete(c["derniers"]):
        evts.add("enjoue")
    dans = envies._dans_terrain(state)
    for l in tapees:
        if _SLEEP.match(l):
            evts.add("reveur")
        if _CACHE.match(l) and dans:
            evts.add("surpris")
        if _BAVARD.search(l):
            evts.add("bavard")
    jour = numero_jour(now)
    # 17. l'éclosiversaire (la fête attend la visite suivante : rien n'est raté)
    f = fete_due(c.get("eclosion"), now, c["fetes"])
    if f:
        feter(state, f[0], f[1], now)
        evts.add("fete")
    h = choisir_humeur(evts)
    if h is None and envies.soir() and c["soir_jour"] != jour:     # le soir : rêveur, s'il ne se passe rien d'autre
        c["soir_jour"] = jour
        h = "reveur"
    if h and h != "fete":
        poser_humeur(state, h, now)
    c["derniere_t"] = now
    _envie(state, c, tapees, now)


def duree(m):
    if m < 12:
        return t("cr.duree.mois", n=m)
    return t("cr.duree.an" if m == 12 else "cr.duree.ans", n=m // 12)


def date_texte(ts):
    a, m, j = date_locale(ts)
    return t("cr.date", j=j, m=m, a=a)


def feter(state, m, retard, now=None):
    c = c_(state)
    now = time.time() if now is None else now
    c["fetes"] = sorted(set(c["fetes"]) | {x for x in jalons() if x <= m})     # les plus anciennes : passées
    c["fete"] = {"m": m, "t": now}
    c["pages"].append({"m": m, "t": now})
    c["humeur"] = {"h": "fete", "t": now}
    nom = state.get("name", "")
    core.terminal(state, t("cr.fete.terminal.retard" if retard else "cr.fete.terminal", nom=nom, duree=duree(m), date=date_texte(c["eclosion"])))
    core.terminal(state, t("cr.fete.album", duree=duree(m)))
    core.say(state, t("cr.fete.retard" if retard else "cr.fete.dit", duree=duree(m)), 12)
    core.animer(state, "victoire")
    core.log(state, t("cr.fete.log", nom=nom, duree=duree(m)))


def fete_active(state, now=None):
    c = state.get("creature") or {}
    f = c.get("fete")
    now = time.time() if now is None else now
    return f if isinstance(f, dict) and 0 <= now - f.get("t", 0) < donnees()["fete_duree"] else None


# ---------------------------------------------------------------- 18. l'envie mystère
def texte_devinette(dev_id, k):
    """Le texte montré après k indices (0 : la description ; 1, 2 : les indices ; 3 : la réponse)."""
    if k <= 0:
        return t(f"cr.dev.{dev_id}.d")
    if k < 3:
        return t(f"cr.dev.{dev_id}.i{k}")
    d = _par_id()[dev_id]
    return t("cr.envie.reponse", cmd=(d.get("win") or d["cmd"]) if IS_WIN else d["cmd"])


def envie(state):
    c = state.get("creature") or {}
    e = c.get("envie")
    return e if isinstance(e, dict) and e.get("id") in _par_id() else None


def _envie(state, c, tapees, now):
    from . import envies
    e = envie(state)
    if e:
        for l in tapees:
            if trouve(e["id"], l):
                c["envie"] = None
                c["gouts"] += 1
                c["depuis"] = 0
                core.say(state, t("cr.envie.trouve_seul" if e.get("k", 0) == 0 else "cr.envie.trouve"), 10)
                core.terminal(state, t("cr.envie.trouve.terminal", nom=state.get("name", "")))
                core.animer(state, "content")
                return
        return
    c["depuis"] += len(tapees)
    jour = numero_jour(now)
    if c["envies_jour"][0] != jour:
        c["envies_jour"] = [jour, 0]
    moment = (envies.e_(state).get("moment") or None) is not None
    if not peut_proposer(_chap1(state), c["envies_jour"][1], False, c["depuis"], moment):
        return
    d = choisir_devinette(eligibles(state.get("seen", []), IS_WIN), jour + c["gouts"], c.get("derniere_dev"))
    if not d:
        return
    c["envie"] = {"id": d, "k": 0, "t": now}
    c["envies_jour"][1] += 1
    c["depuis"] = 0
    c["derniere_dev"] = d
    core.say(state, t("cr.envie.annonce", texte=texte_devinette(d, 0)), 14)
    core.terminal(state, t("cr.envie.terminal", texte=texte_devinette(d, 0)))
    core.animer(state, "parle")


def indice(state, args=()):
    """tg indice [plus-tard] : un indice de plus (3 au plus), ou ranger l'envie mystère."""
    e = envie(state)
    nom = state.get("name", "")
    if not e:
        return t("cr.indice.aucune", nom=nom)
    if args and args[0].lower().replace("_", "-") in ("plus-tard", "plustard", "later", "range", "ranger"):
        c_(state)["envie"] = None
        return t("cr.indice.plus_tard", nom=nom)
    e["k"] = min(3, int(e.get("k", 0)) + 1)
    return t("cr.indice.n", k=e["k"], texte=texte_devinette(e["id"], e["k"]))


def ligne_envie(state):
    """Pour `tg envies` : l'envie mystère en cours, ou None."""
    e = envie(state)
    if not e:
        return None
    return t("cr.envie.ecran", texte=texte_devinette(e["id"], 0), k=e.get("k", 0))


# ---------------------------------------------------------------- 12, 16. les écrans du terminal
def gouts_lignes(state):
    from . import satiete
    from .plateforme import BOLD, DIM, RESET, fg
    nom = state.get("name", "")
    e = espece(state)
    out = [f" {fg(213)}{BOLD}" + t("cr.gouts.titre", nom=nom) + RESET, ""]
    if not e:
        return out + [" " + t("cr.gouts.aucun", nom=nom)]
    p = plat(state)
    al = aliment(type_espece(state))
    out.append(f" {fg(205)}♥{RESET} " + t("cr.gouts.plat", cmd=p, espece=e["nom"]))
    if al:
        out.append(f" {fg(221)}★{RESET} " + t("cr.gouts.aliment", aliment=satiete.ICONES.get(al, "") + " "
                                                + t("sat.famille." + al)))
    c = c_(state)
    out.append(f" {fg(117)}?{RESET} " + (t("cr.gouts.secret_trouve", cmd=secret(state)) if c["secret"]
                                         else t("cr.gouts.secret")))
    out.append("")
    out.append(f" {DIM}" + t("cr.gouts.pied") + RESET)
    return out


def _date_ou(p):
    if not isinstance(p, dict) or p.get("avant") or not p.get("t"):
        return t("cr.album.avant")
    return date_texte(p["t"])


def souvenir(p):
    s = (p or {}).get("s")
    if not s:
        return ""
    return t(s[0], cmd=s[1], n=s[1]) if s[0] == "cr.souv.premiere" else t(s[0], n=s[1])


def album_lignes(state, qui=None):
    """tg album [nom] : les stades (date, niveau, souvenir), « bientôt » pour les suivants, puis les fêtes."""
    from . import bestiaire as B
    from . import equipe
    from .plateforme import BOLD, DIM, RESET, fg
    c = c_(state)
    if qui:
        q = qui.lower()
        ind = next((x for x in state.get("captures", []) if q in (str(x.get("nom", "")).lower(),
                                                                   str(x.get("espece", "")).lower())), None)
        if not ind:
            return [" " + t("cr.album.inconnu", nom=qui)]
        nom = ind.get("nom") or ind.get("espece")
        actuel = equipe.stade(ind)
        stades = donnees()["album_stades_equipe"]
        dates = ind.get("album") if isinstance(ind.get("album"), dict) else {}
        out = [f" {fg(213)}{BOLD}" + t("cr.album.titre", nom=nom) + RESET, ""]
        for k, s in enumerate(stades):
            if k <= stades.index(actuel):
                d = date_texte(dates[s]) if isinstance(dates.get(s), (int, float)) else t("cr.album.avant")
                out.append(f"  {fg(78)}●{RESET} {B.nom_stade(s).capitalize()}  {DIM}{d}{RESET}")
            else:
                out.append(f"  {DIM}○ {B.nom_stade(s).capitalize()} · {t('cr.album.bientot')}{RESET}")
        return out
    nom = state.get("name", "")
    stades = donnees()["album_stades_compagnon"]
    actuel = stade_compagnon(state)
    out = [f" {fg(213)}{BOLD}" + t("cr.album.titre", nom=nom) + RESET]
    if c.get("eclosion"):
        out.append(f" {DIM}" + t("cr.album.eclos", date=date_texte(c["eclosion"])) + RESET)
    out.append("")
    if not actuel:
        return out + [" " + t("cr.album.oeuf")]
    from . import bestiaire as B
    for k, s in enumerate(stades):
        nom_s = B.nom_stade(s).capitalize()
        if k <= stades.index(actuel):
            p = c["album"].get(s) or {"avant": True}
            niv = t("cr.album.niveau", n=p["niv"]) if p.get("niv") else ""
            sv = souvenir(p)
            out.append(f"  {fg(78)}●{RESET} {BOLD}{nom_s}{RESET}  {DIM}{_date_ou(p)}"
                       f"{' · ' + niv if niv else ''}{' · ' + sv if sv else ''}{RESET}")
        else:
            out.append(f"  {DIM}○ {nom_s} · {t('cr.album.bientot')}{RESET}")
    if c["pages"]:
        out.append("")
        out.append(" " + t("cr.album.fetes") + " " + " · ".join(
            f"★ {duree(p['m'])} ({date_texte(p['t'])})" for p in c["pages"][-6:]))
    if c["gouts"]:
        out.append(" " + t("cr.album.gouts", n=c["gouts"]))
    out.append("")
    out.append(f" {DIM}" + t("cr.album.pied") + RESET)
    return out
