"""La satiété (validée le 29 octobre) : pourquoi bien nourrir sa créature, sans mort ni corvée.
Les mêmes règles que Satiete.kt sur Android ; les calculs communs sont vérifiés par donnees/satiete/vecteurs.json.

1. Rythme : la faim ne baisse que pendant les heures d'éveil (EVEIL h - COUCHER h, heure locale), 3 fois plus
   lentement qu'avant (SEC_PAR_POINT = 2160 s par point, au lieu de 720) : environ 23 points par jour, donc de
   rassasiée (80) à affamée (40) en ~2 jours. Le talent Gardien double encore, l'Endurance aussi (jusqu'à ×2), le
   talent du lien (« Cœur fidèle ») ajoute ×1.25. Mode vacances (`tg vacances` / `vacances`) : la faim est en pause.
2. Quatre états : rassasiée (≥ 80), en forme (40-80), affamée (15-40), en veille (< 15). Jamais de mort, et
   l'apprentissage n'est jamais bloqué. La veille dure jusqu'à un « repas complet » : REVEIL_PLATS commandes
   différentes ; elle se réveille alors au moins « en forme » (REVEIL_FAIM).
3. Rassasiée : +20 % d'XP sur les commandes et les leçons (XP_PCT, avec les restes gardés : jamais d'arrondi
   perdu), dressage facilité (+DRESSAGE_TEMPS s et l'exemple tout de suite), plus de rencontres (×RENCONTRES),
   aura plus vive. Évolution : pour grandir (Bébé → Ado, Ado → Adulte), il faut aussi JOURS_STADE jours soignés
   (pas forcément d'affilée) ; en attendant, l'XP en trop est mise de côté (« reserve »), jamais perdue, et les
   leçons ne demandent jamais un niveau plus haut que celui atteint (niveau_appris, plafond). Lien : chaque jour
   soigné donne un point de lien (phrases à LIEN_PHRASES, réaction à LIEN_REACTION, talent à LIEN_TALENT).
4. Faim : affamée −20 % d'XP, en veille −40 % ; pas de nouveau dressage ni de bonus de l'épreuve du jour ; le
   guide grogne au lieu de donner son astuce ; l'aura pâlit.
5. Aliments : chaque famille de commandes (FAMILLES) est un aliment. Une commande jamais goûtée (« nouveau goût »)
   nourrit le plus (NOUVEAU) ; ensuite la famille nourrit de moins en moins dans la journée (PAR_FAMILLE) ; une
   commande répétée de suite ou ratée nourrit à peine (REPETEE, RATEE). L'assiette du jour montre les familles
   déjà mangées ; l'assiette complète (les 6) : +ASSIETTE_FAIM de faim et +ASSIETTE_XP XP, une fois par jour.
6. Jour soigné : un jour qui finit au moins « en forme » (même sans jouer : la faim baisse lentement) ; en jouant,
   il compte dès JOUR_PLATS commandes différentes avec la faim au moins en forme. Il sert à la série de soins, au
   lien et à l'évolution. Série : chaque jour qui finit affamée ou en veille retire UN cran, jamais tout ; les jours
   de vacances ne comptent ni pour ni contre ; paliers SERIE_PALIERS : une médaille et un peu d'XP.
7. Longue absence : sans repas depuis ABSENCE_JOURS jours, elle se repose dans son biome ; au retour, rien n'est
   perdu et elle revient en forme (RETOUR_FAIM).

Sauvegarde : state["satiete"] (local, rien n'est envoyé au serveur). Temps en secondes, dates locales AAAA-MM-JJ.
Tests : pc/outils/test_satiete.py (et la simulation de 14 jours), tests/jvm/Satiete.kt.
"""
import datetime
import time

from .langue import au_hasard, t

SEC_PAR_POINT = 2160.0
EVEIL, COUCHER = 7, 21
RASSASIEE, FORME, AFFAMEE = 80.0, 40.0, 15.0
ETATS = ("rassasiee", "forme", "affamee", "veille")
ICONES_ETAT = {"rassasiee": "😋", "forme": "🙂", "affamee": "😟", "veille": "💤", "repos": "🌿"}
REVEIL_PLATS = 3
REVEIL_FAIM = 40.0
XP_PCT = {"rassasiee": 20, "forme": 0, "affamee": -20, "veille": -40, "repos": 0}
DRESSAGE_TEMPS = 15
RENCONTRES = 1.25
NOUVEAU = 8.0
PAR_FAMILLE = (4.0, 3.0, 2.0, 2.0, 1.5)
AUTRE = 2.0
REPETEE = 0.5
RATEE = 0.5
ASSIETTE_FAIM = 10.0
ASSIETTE_XP = 5
JOUR_PLATS = 3
JOUR_FAIM = 40.0
JOURS_STADE = {2: 3, 3: 7}          # stade visé → jours soignés demandés (Bébé → Ado : 3, Ado → Adulte : 7)
SEUIL_STADE = {2: 160, 3: 810}      # XP du premier niveau du stade (niveau 5, niveau 10 : core.level)
MIGRATION_JOURS = 3                 # une partie d'avant la satiété : 3 jours soignés offerts
MIGRATION_FAIM = 50.0               # … et au moins « en forme » (l'ancienne faim descendait très vite)
SERIE_PALIERS = (3, 7, 14, 30)
SERIE_XP = (10, 15, 20, 30)
LIEN_PHRASES, LIEN_REACTION, LIEN_TALENT = 3, 7, 30
TALENT_LENT = 1.25
ABSENCE_JOURS = 21
RETOUR_FAIM = 60.0

FAMILLES = ("reperer", "batir", "lire", "brancher", "proteger", "observer")
ICONES = {"reperer": "🧭", "batir": "🧱", "lire": "🔍", "brancher": "🔌", "proteger": "🔑", "observer": "🔭"}
CMDS = {
    "reperer": {"pwd", "ls", "dir", "cd", "tree", "gci", "get-childitem", "set-location", "pushd", "popd", "carte"},
    "batir": {"mkdir", "touch", "echo", "cp", "mv", "rm", "rmdir", "ln", "new-item", "copy", "move", "del", "ren",
              "copy-item", "move-item", "remove-item", "add-content", "nano", "vim", "vi", "nvim", "edite", "git",
              "python", "python3", "py", "sh", "bash", "zsh", "alias", "make", "printf", "for", "if", "while"},
    "lire": {"cat", "head", "tail", "less", "more", "grep", "find", "wc", "sort", "uniq", "rev", "type", "diff",
             "get-content", "select-string", "man", "explique", "cherche", "awk", "sed", "cut", "file", "which"},
    "brancher": {"ping", "curl", "curl.exe", "wget", "ssh", "scp", "ip", "ifconfig", "ipconfig", "netstat", "nslookup",
                 "dig", "traceroute", "tracert", "tracepath", "mtr", "hostname", "test-connection", "invoke-webrequest",
                 "iwr", "web", "applis", "ouvre", "appelle", "sms", "partage", "lampe", "vibre", "batterie", "dis",
                 "reglages", "am", "pm"},
    "proteger": {"chmod", "chown", "whoami", "id", "groups", "sudo", "umask", "attrib", "icacls", "get-acl", "passwd"},
    "observer": {"date", "cal", "uptime", "df", "du", "free", "ps", "top", "htop", "btop", "uname", "kill", "killall",
                 "history", "getprop", "dumpsys", "sleep", "jobs", "systeminfo", "tasklist", "get-process", "get-date",
                 "stat", "lsblk", "env"},
}
PAR_CMD = {c: f for f, cs in CMDS.items() for c in cs}


# ---------------------------------------------------------------- calculs communs (les mêmes en Kotlin)
def famille(cmd):
    """L'aliment d'une commande (« reperer »…), ou None (commande de la créature, inconnue…)."""
    cmd = (cmd or "").lower()
    if cmd.startswith("termux-"):
        return "brancher"
    return PAR_CMD.get(cmd)


def etat_de(faim, veille=False):
    if veille or faim < AFFAMEE:
        return "veille"
    if faim >= RASSASIEE:
        return "rassasiee"
    return "forme" if faim >= FORME else "affamee"


def _local(ts):
    return datetime.datetime.fromtimestamp(ts)


def jour_de(ts):
    """La date locale AAAA-MM-JJ d'un instant (secondes)."""
    return _local(ts).strftime("%Y-%m-%d")


def secondes_eveil(t0, t1):
    """Les secondes de [t0, t1] passées entre EVEIL h et COUCHER h (heure locale) : la faim ne baisse que là."""
    if t1 <= t0:
        return 0.0
    total = 0.0
    d = _local(t0).date()
    fin = _local(t1).date()
    n = 0
    while d <= fin and n < 400:
        a = time.mktime((d.year, d.month, d.day, EVEIL, 0, 0, 0, 0, -1))
        b = time.mktime((d.year, d.month, d.day, COUCHER, 0, 0, 0, 0, -1))
        lo, hi = max(t0, a), min(t1, b)
        if hi > lo:
            total += hi - lo
        d += datetime.timedelta(days=1)
        n += 1
    return total


def taux(gardien=False, endurance=0, lien=0):
    """Secondes (d'éveil) par point de faim."""
    r = SEC_PAR_POINT * (2 if gardien else 1) * (1 + min(1.0, max(0, endurance) / 100))
    return r * (TALENT_LENT if lien >= LIEN_TALENT else 1)


def valeur_repas(nouvelle, ratee, repetee, n_famille, a_famille=True):
    """Ce que nourrit une commande : nouveau goût > famille pas encore mangée aujourd'hui > … > répétée ou ratée."""
    if ratee:
        return RATEE
    if repetee:
        return REPETEE
    if nouvelle:
        return NOUVEAU
    if not a_famille:
        return AUTRE
    return PAR_FAMILLE[min(n_famille, len(PAR_FAMILLE) - 1)]


def xp_ajuste(gain, etat, reste=0):
    """(xp donnée, nouveau reste en centièmes) : +20 % rassasiée, −20 % affamée… sans rien perdre à l'arrondi."""
    if gain <= 0:
        return gain, reste
    total = gain * (100 + XP_PCT.get(etat, 0)) + reste
    return total // 100, total % 100


def palier_serie(serie):
    """Le nombre de paliers atteints par la série."""
    return sum(1 for p in SERIE_PALIERS if serie >= p)


def serie_manquee(serie):
    """Un jour manqué (fini affamée ou en veille) : la série perd UN cran, jamais tout."""
    return max(0, serie - 1)


def minuit_apres(ts):
    """Le début (00:00, heure locale) du jour qui suit l'instant ts."""
    d = _local(ts).date() + datetime.timedelta(days=1)
    return time.mktime((d.year, d.month, d.day, 0, 0, 0, 0, 0, -1))


def jours_pour(stade):
    return JOURS_STADE.get(stade, 0)


# ---------------------------------------------------------------- l'état dans la sauvegarde
def s_(state):
    """L'état de la satiété, créé à la demande (une ancienne partie : MIGRATION_JOURS jours offerts, au moins en forme)."""
    s = state.get("satiete")
    if not isinstance(s, dict):
        neuve = not state.get("total") and not state.get("xp")
        s = state["satiete"] = {}
        if not neuve:
            s["jours"] = MIGRATION_JOURS
            state["hunger"] = max(float(state.get("hunger", 0)), MIGRATION_FAIM)
            state["last_tick"] = time.time()     # le temps passé avec l'ancienne règle ne compte pas deux fois
    now = time.time()
    for k, v in {"jours": 0, "serie": 0, "meilleure": 0, "medailles": 0, "veille": False, "reveil": [],
                 "vacances": False, "jour": "", "assiette": [], "plats": [], "compte": False, "complete": False,
                 "dernier": "", "clos": "", "reserve": 0, "xp_reste": 0, "prete_dit": 0, "repas_t": now,
                 "reaction": ""}.items():
        s.setdefault(k, v)
    return s


def lien(state):
    return int(s_(state)["jours"])


def absente(state, now=None):
    """Vrai si elle se repose dans son biome (aucun repas depuis ABSENCE_JOURS jours, hors vacances)."""
    s = s_(state)
    now = time.time() if now is None else now
    return not s["vacances"] and now - s["repas_t"] > ABSENCE_JOURS * 86400


def etat(state):
    """« rassasiee », « forme », « affamee », « veille » (ou « repos » pendant une longue absence)."""
    if absente(state):
        return "repos"
    return etat_de(float(state.get("hunger", 0)), s_(state)["veille"])


def affamee(state):
    return etat(state) in ("affamee", "veille")


def rassasiee(state):
    return etat(state) == "rassasiee"


def nom_etat(e):
    return t("sat.etat." + e)


# ---------------------------------------------------------------- le temps qui passe
def tick(state, now=None):
    """La faim baisse (heures d'éveil seulement, rien en vacances) ; la veille commence sous AFFAMEE. Chaque jour
    fini (même sans jouer, même ordinateur éteint : on le recalcule) est jugé : soigné s'il finit au moins en forme."""
    s = s_(state)
    now = time.time() if now is None else now
    t0 = state.get("last_tick", now)
    if now > t0:
        n = 0
        while jour_de(t0) < jour_de(now) and n < 60:   # les jours finis depuis la dernière fois, un par un
            fin = minuit_apres(t0)
            _baisser(state, s, t0, fin)
            _cloturer(state, s, jour_de(t0))
            t0, n = fin, n + 1
        _baisser(state, s, max(t0, now - 86400), now)
    state["last_tick"] = now
    _nouveau_jour(state, s, now)


def _baisser(state, s, t0, t1):
    from . import core
    avant = float(state["hunger"])
    if not s["vacances"] and t1 > t0:
        r = taux("Gardien" in state.get("skills", []), state.get("stats", {}).get("Endurance", 0), s["jours"])
        state["hunger"] = min(100.0, max(0.0, avant - secondes_eveil(t0, t1) / r))
    h = state["hunger"]
    if h < AFFAMEE and not s["veille"]:
        s["veille"] = True
        s["reveil"] = []
        core.notif(state, t("sat.notif.veille", nom=state.get("name", "")))
    elif avant >= FORME > h:
        core.notif(state, t("core.notif.faim"))


def _cloturer(state, s, j):
    """Le jour j est fini : soigné s'il a fini au moins en forme (sinon la série perd un cran) ; neutre en vacances."""
    if s["clos"] and s["clos"] >= j:
        return
    s["clos"] = j
    if s["vacances"] or (s["jour"] == j and s["compte"]):
        return                                # (déjà compté pendant le jeu, ou en vacances : ni gagné ni manqué)
    if state["hunger"] >= JOUR_FAIM and not s["veille"]:
        _compter(state, s, j)
    else:
        s["serie"] = serie_manquee(s["serie"])


def _nouveau_jour(state, s, now):
    j = jour_de(now)
    if s["jour"] != j:
        s["jour"], s["assiette"], s["plats"], s["compte"], s["complete"] = j, [], [], False, False


# ---------------------------------------------------------------- les repas
def repas(state, cmd, nouvelle=False, ratee=False, repetee=False, now=None):
    """Une commande mangée : la faim monte selon l'aliment ; l'assiette, la veille, le jour soigné. Renvoie le gain."""
    from . import core
    s = s_(state)
    now = time.time() if now is None else now
    _nouveau_jour(state, s, now)
    if not ratee and now - s["repas_t"] > ABSENCE_JOURS * 86400 and not s["vacances"]:
        s["repas_t"] = now                    # 7. longue absence : elle revient de son biome, rien n'est perdu
        s["veille"] = False
        state["hunger"] = max(float(state["hunger"]), RETOUR_FAIM)
        core.say(state, t("sat.retour", nom=state.get("name", "")), 14)
        core.animer(state, "content")
    f = famille(cmd)
    n_f = s["assiette"].count(f) if f else 0
    gain = valeur_repas(nouvelle, ratee, repetee, n_f, f is not None)
    state["hunger"] = min(100.0, float(state["hunger"]) + gain)
    if ratee:
        return gain
    s["repas_t"] = now
    if f and not repetee:
        s["assiette"].append(f)
    if cmd not in s["plats"]:
        s["plats"] = (s["plats"] + [cmd])[-30:]
    if f and not s["complete"] and all(x in s["assiette"] for x in FAMILLES):
        s["complete"] = True                  # l'assiette complète : une fois par jour
        state["hunger"] = min(100.0, state["hunger"] + ASSIETTE_FAIM)
        core.say(state, t("sat.assiette.complete", nom=state.get("name", "")), 10)
        core.add_xp(state, ASSIETTE_XP)
    if s["veille"]:
        if cmd not in s["reveil"]:
            s["reveil"].append(cmd)
        if len(s["reveil"]) >= REVEIL_PLATS:
            s["veille"], s["reveil"] = False, []
            state["hunger"] = max(state["hunger"], REVEIL_FAIM)
            core.say(state, t("sat.reveil", nom=state.get("name", "")), 12)
            core.animer(state, "content")
        else:
            core.say(state, t("sat.veille.encore", n=REVEIL_PLATS - len(s["reveil"])), 8)
    _jour_soigne(state, s, now)
    if s["jours"] >= LIEN_REACTION and s["reaction"] != s["jour"] and not s["veille"]:
        s["reaction"] = s["jour"]             # le lien : un petit cœur au premier repas du jour
        core.say(state, au_hasard("sat.lien.coeur", nom=state.get("name", "")), 8)
    return gain


def _jour_soigne(state, s, now):
    """Pendant le jeu, le jour compte tout de suite quand JOUR_PLATS commandes différentes ont été mangées et qu'elle
    est au moins en forme (sinon il sera jugé à sa fin, par tick)."""
    if s["compte"] or s["veille"] or len(s["plats"]) < JOUR_PLATS or state["hunger"] < JOUR_FAIM:
        return
    s["compte"] = True
    _compter(state, s, s["jour"])


def _compter(state, s, j):
    """Un jour soigné de plus : la série, le lien, les médailles, l'évolution qui attendait."""
    from . import core
    s["jours"] += 1
    avant = palier_serie(s["serie"])
    s["serie"] += 1
    s["meilleure"] = max(s["meilleure"], s["serie"])
    s["dernier"] = j
    p = palier_serie(s["serie"])
    if p > avant and p > s["medailles"]:
        s["medailles"] = p
        xp = SERIE_XP[p - 1]
        core.log(state, "🎯 " + t("sat.serie.medaille", n=SERIE_PALIERS[p - 1], xp=xp))
        core.say(state, t("sat.serie.medaille", n=SERIE_PALIERS[p - 1], xp=xp), 12)
        core.add_xp(state, xp)
    if s["jours"] == LIEN_TALENT:
        core.say(state, t("sat.lien.talent", nom=state.get("name", "")), 14)
    liberer(state)


# ---------------------------------------------------------------- l'XP et l'évolution
def gagner_xp(state, n, lecon=False):
    """L'XP d'une commande ou d'une leçon, avec la concentration (rassasiée) ou la fatigue (affamée). Une leçon
    n'en perd jamais (le niveau demandé par les leçons suit l'XP qu'elles ont forcément donnée : histoire.xp_appris)."""
    from . import core, intro
    e = etat(state)
    if n > 0 and not intro.retient(state) and not (lecon and XP_PCT.get(e, 0) < 0):
        s = s_(state)
        n, s["xp_reste"] = xp_ajuste(n, e, s["xp_reste"])
    core.add_xp(state, n)
    return n


def retenir(state, avant):
    """Appelé par core.add_xp : si l'XP franchit le seuil d'un stade sans assez de jours soignés, elle s'arrête juste
    avant et le reste est mis de côté (reserve) — jamais perdu."""
    s = s_(state)
    for st, seuil in SEUIL_STADE.items():
        if avant < seuil <= state["xp"] and s["jours"] < jours_pour(st):
            s["reserve"] += state["xp"] - (seuil - 1)
            state["xp"] = seuil - 1
            if time.time() - s["prete_dit"] > 3600:
                s["prete_dit"] = time.time()
                from . import core
                core.say(state, t("sat.prete", nom=state.get("name", ""), n=jours_pour(st) - s["jours"]), 14)
            return True
    return False


def liberer(state):
    """Assez de jours soignés : l'XP mise de côté revient (et l'évolution a lieu)."""
    from . import core
    s = s_(state)
    if s["reserve"] <= 0:
        return
    st = next((x for x, seuil in SEUIL_STADE.items() if state["xp"] == seuil - 1), None)
    if st is not None and s["jours"] < jours_pour(st):
        return
    r, s["reserve"] = s["reserve"], 0
    core.add_xp(state, r)


def niveau_appris(state):
    """Le niveau en comptant l'XP mise de côté (les fonctions qui s'ouvrent, l'apprentissage : jamais bloqués)."""
    from . import core
    return core.level(state.get("xp", 0) + s_(state)["reserve"])


def plafond(state):
    """Le niveau demandé par une leçon ne dépasse jamais celui-ci (l'XP retenue avant une évolution)."""
    from . import core
    return core.level(state.get("xp", 0)) if s_(state)["reserve"] > 0 else 99


def prochaine_evolution(state):
    """(stade visé, jours manquants) si une évolution attend des jours soignés, sinon None."""
    from . import core
    s = s_(state)
    st = core.stage(core.level(state.get("xp", 0)))
    vise = st + 1
    if vise not in JOURS_STADE:
        return None
    return vise, max(0, JOURS_STADE[vise] - s["jours"])


# ---------------------------------------------------------------- vacances
def vacances(state, on=None):
    """Bascule (ou règle) le mode vacances. Renvoie le texte à montrer."""
    s = s_(state)
    s["vacances"] = (not s["vacances"]) if on is None else bool(on)
    if not s["vacances"]:
        s["repas_t"] = max(s["repas_t"], time.time())   # le retour de vacances n'est pas une longue absence
    return t("sat.vacances.on" if s["vacances"] else "sat.vacances.off", nom=state.get("name", ""), cmd=commande_vacances())


# ---------------------------------------------------------------- l'affichage
def assiette(state):
    """« 🧭 🧱 · · · · » : les familles mangées aujourd'hui."""
    s = s_(state)
    if s["jour"] != jour_de(time.time()):
        return " ".join("·" for _ in FAMILLES)
    return " ".join(ICONES[f] if f in s["assiette"] else "·" for f in FAMILLES)


def nb_assiette(state):
    s = s_(state)
    return len({f for f in s["assiette"] if f in FAMILLES}) if s["jour"] == jour_de(time.time()) else 0


def ligne_assiette(state):
    return t("sat.assiette", assiette=assiette(state), n=nb_assiette(state), total=len(FAMILLES))


def ligne_etat(state):
    e = etat(state)
    return f"{ICONES_ETAT[e]} {nom_etat(e)}"


def suggestion(state):
    """Une famille pas encore mangée aujourd'hui et une commande sûre pour la goûter."""
    s = s_(state)
    sures = {"reperer": "pwd", "batir": "echo miam", "lire": "cat --help", "brancher": "hostname",
             "proteger": "whoami", "observer": "date"}
    for f in FAMILLES:
        if f not in s["assiette"] or s["jour"] != jour_de(time.time()):
            return f, sures[f]
    return None, None


def lignes(state):
    """Le détail (dans `tg envies`, et `tg satiete`)."""
    s = s_(state)
    e = etat(state)
    out = [t("sat.ecran.etat", etat=ligne_etat(state), faim=int(state.get("hunger", 0))),
           t("sat.ecran.effet." + e),
           ligne_assiette(state)]
    f, cmd = suggestion(state)
    if f:
        out.append(t("sat.ecran.gouter", icone=ICONES[f], famille=t("sat.famille." + f), cmd=cmd))
    if s["veille"]:
        out.append(t("sat.veille.encore", n=REVEIL_PLATS - len(s["reveil"])))
    out.append(t("sat.ecran.serie", n=s["serie"], meilleure=s["meilleure"], jours=s["jours"]))
    p = prochaine_evolution(state)
    if p and p[1] > 0:
        out.append(t("sat.ecran.grandir", n=p[1]))
    out.append(t("sat.ecran.biome." + ("fleuri" if e == "rassasiee" else "fane" if e in ("affamee", "veille") else "normal")))
    out.append(t("sat.ecran.vacances." + ("on" if s["vacances"] else "off"), cmd=commande_vacances()))
    return out


def commande_vacances():
    return "tg vacances"

