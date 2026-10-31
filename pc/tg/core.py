"""Cœur du jeu : état, historique, nourriture, XP, caractère, défis, sauvegarde."""
import json
import os
import random
import re
import time
from contextlib import contextmanager
from pathlib import Path

from .langue import au_hasard, t
from .langue import t as tr
from .plateforme import GEST, IS_WIN, est_colle, piege
from . import sur as _sur

_sur.installer()        # le jeu n'écrit jamais à travers un lien symbolique (sur.py)

VERSION = "0.4"
SAVE_DIR = Path.home() / ".terminagotchi"
SAVE_FILE = SAVE_DIR / "save.json"
LOCK_FILE = SAVE_DIR / "verrou"
TERRAIN = Path.home() / "terrain_terminagotchi"   # bac à sable des leçons et de l'exploration

# Chaque famille de commandes nourrit une statistique (et oriente l'évolution)
CATEGORIES = {
    "code": {"stat": "Intelligence", "short": "INT", "color": 39, "cmds": {
        "git", "python", "python3", "py", "node", "npm", "npx", "pip", "pip3", "make", "gcc",
        "g++", "cargo", "go", "java", "javac", "code", "vim", "nvim", "nano", "docker", "notepad",
        "sh", "bash", "zsh", "alias", "function", "source", "powershell", "pwsh"}},
    "reseau": {"stat": "Agilité", "short": "AGI", "color": 78, "cmds": {
        "ping", "curl", "curl.exe", "wget", "ssh", "scp", "ipconfig", "ifconfig", "ip", "netstat",
        "nslookup", "traceroute", "tracert", "tracepath", "mtr", "test-connection",
        "invoke-webrequest", "iwr", "dig", "am", "pm", "ouvre"}},
    "systeme": {"stat": "Force", "short": "FOR", "color": 203, "cmds": {
        "top", "htop", "btop", "ps", "kill", "killall", "sudo", "apt", "apt-get", "dnf", "pacman",
        "brew", "winget", "choco", "zypper", "apk", "systemctl", "tasklist", "taskkill", "get-process",
        "stop-process", "start-process", "df", "du", "free", "uname", "pkg", "shutdown", "reboot",
        "whoami", "date", "get-date", "attrib", "icacls", "get-acl", "jobs", "sleep",
        "get-psdrive", "systeminfo", "history"}},
    "fichiers": {"stat": "Endurance", "short": "END", "color": 221, "cmds": {
        "ls", "dir", "cd", "cp", "mv", "rm", "mkdir", "rmdir", "cat", "type", "touch", "find",
        "grep", "less", "more", "head", "tail", "copy", "move", "del", "ren", "get-childitem",
        "gci", "set-location", "copy-item", "move-item", "remove-item", "new-item",
        "get-content", "select-string", "tree", "chmod", "chown", "pwd", "echo", "stat",
        "add-content"}},
}
STAT_COLOR = {v["stat"]: v["color"] for v in CATEGORIES.values()}

EXAMPLES = {
    # (que des commandes qui rendent la main tout de suite : pas d'éditeur ni de mot de passe)
    "linux":   {"fichiers": "ls  cd  cp  grep", "reseau": "ping -c 3  hostname  curl",
                "code": "git  echo  which", "systeme": "date  whoami  df"},
    "mac":     {"fichiers": "ls  cd  cp  grep", "reseau": "ping -c 3  hostname  curl",
                "code": "git  echo  which", "systeme": "date  whoami  df"},
    "windows": {"fichiers": "dir  cd  copy  Get-ChildItem", "reseau": "ping  ipconfig  Test-Connection",
                "code": "git  python  notepad", "systeme": "tasklist  winget  Get-Process"},
    "android": {"fichiers": "ls  cd  cp  grep", "reseau": "ping -c 3  hostname  curl",
                "code": "git  echo  which", "systeme": "date  whoami  df"},
}

# Compétences : chacune double l'XP de ses commandes (sauf effets spéciaux)
SKILLS = {
    # tronc commun
    "Boussole":    {"cmds": {"cd", "ls", "dir", "pwd", "gci", "get-childitem", "set-location", "tree"}},
    "Bâtisseur":   {"cmds": {"mkdir", "touch", "new-item", "echo"}},
    "Inspecteur":  {"cmds": {"cat", "type", "less", "more", "head", "tail", "grep", "find", "select-string", "get-content"}},
    "Gardien":     {"cmds": {"chmod", "chown", "attrib", "icacls"}},
    "Nettoyeur":   {"cmds": {"cp", "mv", "rm", "copy", "move", "del", "copy-item", "move-item", "remove-item"}},
    # l'histoire « La Maison endormie » (histoire.py)
    "Explorateur": {"cmds": {"tree", "find"}},
    "Héros":       {"cmds": {"rev", "wc", "sort", "uniq"}},
    # branche Réseau
    "Radar":       {"cmds": {"ping", "ip", "ifconfig", "ipconfig", "test-connection"}},
    "Facteur":     {"cmds": {"curl", "curl.exe", "wget", "invoke-webrequest", "iwr"}},
    "Cartographe": {"cmds": {"nslookup", "dig", "traceroute", "tracert", "tracepath", "mtr"}},
    # branche Git
    "Archiviste":  {"cmds": {"git"}},
    "Mémoire":     {"cmds": set()},
    "Chronomancien": {"cmds": set()},
    # branche Scripts
    "Cuistot":     {"cmds": {"sh", "bash", "zsh", "powershell", "pwsh"}},
    "Inventeur":   {"cmds": {"alias", "function"}},
    "Créateur":    {"cmds": set()},
    # branche Système
    "Vigie":       {"cmds": {"ps", "top", "htop", "get-process", "tasklist", "whoami"}},
    "Intendant":   {"cmds": {"df", "du", "free", "get-psdrive"}},
    "Chasseur":    {"cmds": {"kill", "killall", "jobs", "stop-process", "taskkill", "start-process"}},
    # branche Android
    "Télécommande": {"cmds": {"termux-toast", "termux-vibrate", "termux-torch"}},
    "Portier":     {"cmds": {"termux-open-url", "termux-open", "am"}},
    "Lanceur":     {"cmds": {"am", "pm", "ouvre"}},
    "Majordome":   {"cmds": {"termux-battery-status", "termux-tts-speak",
                    "termux-clipboard-get", "termux-clipboard-set", "termux-volume", "termux-brightness"}},
}

NOMS_CONNUS = set()   # rempli par le registre de commandes

# ================================================================ historique

def history_files():
    h = Path.home()
    files = [h / ".bash_history", h / ".zsh_history", h / ".local/share/fish/fish_history"]
    if os.environ.get("HISTFILE"):
        files.append(Path(os.environ["HISTFILE"]))
    if IS_WIN:
        files.append(Path(os.environ.get("APPDATA", "")) /
                     "Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt")
    else:
        files.append(h / ".local/share/powershell/PSReadLine/ConsoleHost_history.txt")
    seen, out = set(), []
    for f in files:
        if str(f) not in seen:
            seen.add(str(f))
            out.append(f)
    return out


def parse_line(line):
    """Renvoie la commande complète, quel que soit le format d'historique."""
    line = line.strip()
    if line.startswith("- cmd: "):                       # fish
        line = line[7:]
    elif line.startswith(": ") and ";" in line:           # zsh format étendu
        line = line.split(";", 1)[1]
    elif not line or line.startswith(("#", "when:", "paths:", "- ")):
        return None
    return line.strip() or None


# le code de sortie de la DERNIÈRE commande lue, quand le crochet d'invite le donne (`tg prompt --statut=$?`) :
# {"ligne": texte, "statut": n}. Les autres lignes ont un code inconnu (None). Voir verif.py.
DERNIER = {"ligne": None, "statut": None}


def statut_de(lignes, i):
    """Le code de sortie de lignes[i] (0 = réussi), ou None s'il est inconnu."""
    if i == len(lignes) - 1 and DERNIER["ligne"] is not None and lignes[i] == DERNIER["ligne"]:
        return DERNIER["statut"]
    return None


def first_word(line):
    words = line.lstrip("( ").split()                 # `(umask 077; touch f)` : la commande de la petite bulle
    if not words:
        return None
    # v3 (I12) : `pwd; ls`, `ls|wc` : le premier mot s'arrête au séparateur du shell collé (pas « pwd; »)
    w = (re.split(r"[;&|<>]", words[0])[0] or words[0]).lower()
    if w.startswith(("./", ".\\")):
        return w
    return os.path.basename(w).removesuffix(".exe") if w != "curl.exe" else "curl.exe"


def read_new_lines(state):
    offsets = state["offsets"]
    lines = []
    for f in history_files():
        key = str(f)
        try:
            size = f.stat().st_size
        except OSError:
            offsets.setdefault(key, 0)   # pas encore créé : on le lira dès le début
            continue
        if key not in offsets or size < offsets[key]:
            offsets[key] = size
            continue
        if size == offsets[key]:
            continue
        with open(f, "rb") as fh:
            fh.seek(offsets[key])
            data = fh.read()
        last_nl = data.rfind(b"\n")
        if last_nl == -1:
            continue
        offsets[key] += last_nl + 1
        for raw in data[:last_nl].decode("utf-8", "replace").splitlines():
            c = parse_line(raw)
            if c:
                lines.append(c)
    return lines

# ================================================================ caractère

TRAITS = ("curieux", "farceur", "gourmand", "philosophe")   # phrases : langues/xx.json, « trait.<nom>.phrases »


def say(state, text, secs=8):
    """La créature parle. Si elle parle déjà, la phrase attend son tour (rien n'est écrasé)."""
    b = state.get("bubble")
    if b and time.time() < b[1] and b[0] != text:
        file = state.setdefault("bulles", [])
        if text not in (x[0] for x in file):
            file.append([text, secs])
            del file[:-4]
        return
    state["bubble"] = [text, time.time() + secs]


def bulle_courante(state):
    """La phrase à afficher maintenant (passe à la suivante de la file quand la précédente est lue)."""
    b = state.get("bubble")
    if (not b or time.time() >= b[1]) and state.get("bulles"):
        texte, secs = state["bulles"].pop(0)
        state["bubble"] = b = [texte, time.time() + secs]
    return b if b and time.time() < b[1] else None


NOTIF_PREFIX = ("✨", "⬆", "🎓", "🌳", "🎯", "🐾", "💨", "🌲", "⚡")


def notif(state, texte):
    """Met un événement en file pour les notifications du système."""
    state["notifs"] = (state.get("notifs", []) + [texte])[-5:]


# Courtes animations de la fenêtre principale : un événement daté, rangé dans la sauvegarde
# (n'importe quel processus — invite, veille, fenêtre — peut le déclencher ; la fenêtre le joue).
PRIORITE_ANIM = {"eclosion": 10, "oeuf_1": 3, "oeuf_2": 3, "oeuf_3": 3, "evolution": 9, "victoire": 8, "ko": 7, "colere": 6, "attaque": 6, "dort": 6, "content": 5, "confus": 4,
                 "mange": 3, "salut": 2, "parle": 1}


def animer(state, nom):
    """Demande une courte animation de la créature (la plus importante gagne si plusieurs arrivent ensemble)."""
    now = time.time()
    a = state.get("anim")
    if a and now - a[1] < 2 and PRIORITE_ANIM.get(a[0], 0) > PRIORITE_ANIM.get(nom, 0):
        return
    state["anim"] = [nom, now]


def log(state, msg):
    state["log"] = (state["log"] + [time.strftime("%H:%M ") + msg])[-6:]
    state["nlog"] = state.get("nlog", 0) + 1
    if msg.startswith(NOTIF_PREFIX):
        notif(state, msg)

# ================================================================ progression

STAGES = ["Œuf", "Bébé", "Ado", "Adulte"]                  # noms internes (affichés : « stade.0 » à « stade.3 »)
FORMES = {"Intelligence": "Hacker", "Force": "Titan", "Agilité": "Éclair", "Endurance": "Carapace"}


def nom_stat(stat, court=False):
    """Intelligence/Force… (ou INT/FOR…) dans la langue choisie."""
    return t(("stat.court." if court else "stat.") + stat)


def nom_skill(skill):
    return t("skill." + skill)


def nom_trait(trait):
    return t("trait." + trait)


def forme(state, lvl=None):
    """« Bébé », « Ado Hacker »… : le stade et la forme de la créature, traduits."""
    lvl = level(state["xp"]) if lvl is None else lvl
    st = stage(lvl)
    nom = t(f"stade.{st}")
    if st >= 1 and state.get("espece_compagnon"):        # une espèce du bestiaire : « Bébé Gouttelin »
        from . import bestiaire as B
        e = B.espece(state["espece_compagnon"])
        if e:
            return t("forme.stade", stade=nom, forme=e["nom"])
    if st >= 2 and state.get("branch"):
        nom = t("forme.stade", stade=nom, forme=t("forme." + state["branch"]))
    return nom


REPAS_FACILES = ["date", "whoami", "pwd", "ls", "echo coucou", "cal", "uptime", "hostname", "uname", "id", "df", "which ls"]


def faim_d_apprendre(state, niveau):
    """« J'ai encore faim » + 4 commandes sûres pas encore goûtées + combien il en faut environ."""
    manque = max(0, 10 * (niveau - 1) ** 2 - state["xp"])
    vues = set(state.get("seen", []))
    idees = [c for c in REPAS_FACILES if c.split()[0] not in vues][:4] or REPAS_FACILES[:4]
    return idees, max(1, -(-manque // 6))


def level(xp):
    return int((xp / 10) ** 0.5) + 1


def stage(lvl):
    return 0 if lvl < 2 else 1 if lvl < 5 else 2 if lvl < 10 else 3


def dominant(state):
    st = state["stats"]
    if not any(st.values()):
        return random.choice(list(st))
    return max(st, key=st.get)


def new_state(name, langue_code="fr"):
    now = time.time()
    from . import oeufs
    ty = random.choice(oeufs.types())             # le type de l'œuf et du compagnon, puis son espèce (oeufs.py)
    return {"name": name, "langue": langue_code, "shiny": False, "born": now, "last_tick": now, "xp": 0, "hunger": 80.0, "total": 0,
            "stats": {v["stat"]: 0 for v in CATEGORIES.values()}, "seen": [], "log": [],
            "offsets": {}, "version": VERSION,
            "oeuf_type": ty, "espece_compagnon": oeufs.espece_depart(ty)}   # l'œuf : son type, l'espèce qui en sort


def nom_propre(nom):
    """Le nom de la créature sans caractères de contrôle ni de mise en forme (ESC, NUL, RLO…) : ils iraient tels quels
    au terminal (effacer l'écran, retourner le texte) et sur le site, où d'autres joueurs le voient."""
    import unicodedata
    return "".join(c for c in str(nom or "") if unicodedata.category(c) not in ("Cc", "Cf", "Cs")).strip()[:16]


def migrate(state):
    if isinstance(state.get("name"), str) and nom_propre(state["name"]) != state["name"].strip()[:16]:
        state["name"] = nom_propre(state["name"]) or "Pixel"
    defaults = {"trait": random.choice(TRAITS), "langue": "fr", "skills": [], "lesson": 0, "step": 0,
                "bubble": None, "defi": None, "records": {}, "offsets": {}, "arbre": {},
                "branche": None, "cherche": {}, "sauvages": [], "collection": {}, "explo": False, "dressage": None,
                "explo_n": 0, "annonce": None, "colles": 0, "notifs": [], "nlog": 0,
                "prompt_vu": 0, "config": {}, "compte": {}, "repas_t": 0, "captures": [], "shiny": False}
    for k, v in defaults.items():
        state.setdefault(k, v)
    if stage(level(state["xp"])) >= 2 and not state.get("branch"):
        state["branch"] = dominant(state)
    from . import envies
    envies.e_(state)                       # les 6 envies (une ancienne partie reçoit des valeurs moyennes)
    from . import guide
    guide.g_(state)                        # le guide (une ancienne partie : le compagnon est le guide)
    from . import intro
    intro.i_(state)                        # l'intro et le déblocage (une ancienne partie : tout reste ouvert)
    intro.d_(state)
    from . import satiete
    satiete.s_(state)                      # la satiété (une ancienne partie : 3 jours soignés offerts, en forme)
    for k, v in {"notifs": True, "permanente": True, "compagnon": "ligne", "bulle": True}.items():
        state["config"].setdefault(k, v)
    state["version"] = VERSION
    return state


def add_xp(state, n):
    xp_avant = state["xp"]
    old = level(state["xp"])
    state["xp"] += n
    if isinstance(state.get("intro"), dict) and state["intro"].get("etat") == "oeuf":
        state["xp"] = min(state["xp"], 9)    # l'œuf n'éclot qu'à la fin de sa liste de commandes (intro.py)
    from . import satiete
    satiete.retenir(state, xp_avant)   # grandir demande aussi des jours soignés (l'XP en trop est gardée)
    new = level(state["xp"])
    if new <= old:
        return
    animer(state, "evolution" if stage(new) > stage(old) else "content")
    if stage(new) > stage(old):
        if stage(new) == 1:
            log(state, t("core.eclot.log"))
            say(state, t("core.eclot.dit"), 10)
        else:
            if not state.get("branch"):
                state["branch"] = dominant(state)
            log(state, t("core.evolution.log", forme=forme(state, new)))
            say(state, t("core.evolution.dit"), 10)
    else:
        log(state, t("core.niveau.log", n=new))


def tick(state):
    """La faim baisse avec le temps : seulement de 7 h à 21 h, 3 fois plus lentement qu'avant, rien en vacances
    (satiete.py : les 4 états, la veille, les jours soignés)."""
    from . import satiete
    satiete.tick(state)


BUILTINS = {"cd", "echo", "export", "alias", "history", "type", "source", ".", "exit", "for", "if", "while",
            "set", "unset", "read", "test", "[", "pushd", "popd", "jobs", "fg", "bg", "kill", "umask", "ulimit",
            "true", "false", "printf", "wait", "trap", "exec", "eval", "help", "tg", "clear",
            "carte", "quetes", "explique",          # carte, quetes : les raccourcis du jeu (tg carte, tg quetes)
            "entrainement", "exercice", "badges",   # la salle d'entraînement (tg entrainement, tg badges)
            "guide", "types", "equipe",             # le guide (tg guide, tg types, tg equipe)
            "aide",                                 # I1 : alias aide='tg aide' (installé avec le compagnon)
            # les alias du jeu posés par tg installer (le compagnon) : ce sont des commandes, pas des fautes
            "deploie", "espace", "cerveau", "port", "citadelle", "crypte",
            # les mots-clés du shell (time sh mineur.sh 3 : « time » n'est pas un programme, mais il existe)
            "time", "case", "until", "function", "select", "command", "builtin", "local", "declare", "times"}


def commande_existe(cmd):
    import shutil
    return cmd in BUILTINS or shutil.which(cmd) is not None


def commande_proche(cmd):
    import difflib
    if cmd.startswith("cd") and len(cmd) > 2:                      # cd~ → cd ~
        return "cd " + cmd[2:]
    for c in ("ls", "cd", "pwd", "cat", "cp", "mv", "rm", "free", "grep", "mkdir", "touch"):
        if sorted(cmd) == sorted(c):                                # lettres inversées : sl → ls, pdw → pwd
            return c
    connues = sorted(BUILTINS | {c for v in CATEGORIES.values() for c in v["cmds"]})
    m = difflib.get_close_matches(cmd, connues, n=1, cutoff=0.65)
    return m[0] if m else None


FENETRE_REPAS = 10      # une commande répétée dans les 10 dernières ne donne plus d'XP (anti-remplissage)


def terminal(state, texte):
    """Un message à montrer AUSSI dans le terminal de l'enfant, sous sa commande (le compagnon de l'invite l'affiche
    une fois, puis l'oublie) : indices, mises en garde, erreurs expliquées (G-34, comme sur Android)."""
    file = state.setdefault("terminal", [])
    if texte and texte not in file:
        file.append(texte)
        del file[:-6]


def feed(state, line, statut=None):
    if est_colle(line):
        state["colles"] += 1
        log(state, t("core.colle.log"))
        say(state, au_hasard("core.colle"), 10)
        terminal(state, t("core.colle.doigts"))     # P2-8 : dans le terminal, ce qu'il faut faire (taper au clavier)
        animer(state, "colere")
        return
    if not line.split():
        return
    if not line.lstrip("( ").split():
        return
    tete = re.split(r"[;&|<>]", line.lstrip("( ").split()[0])[0] or line.lstrip("( ").split()[0]
    if "/" in tete and not tete.startswith(("/", ".", "~")) and not commande_existe(tete):
        # v3 (I12) : `cd/home/lea/…/vestibule`, `ls/etc` : l'espace oubliée (et pas « vestibule n'est pas une commande »)
        from . import verif
        proche = verif.collee(tete)
        if proche:
            msg = t("core.inconnue.proche", cmd=tete, proche=proche)
            say(state, msg, 8)
            terminal(state, msg)
            log(state, t("core.inconnue.log", cmd=tete))
            animer(state, "confus")
            return
    cmd = first_word(line)
    if not cmd or cmd in ("exit", "logout"):       # I5 : quitter le terminal n'est pas un repas
        return
    brut = os.path.basename(tete)
    if not IS_WIN and brut != brut.lower() and commande_existe(cmd) and not commande_existe(brut):
        msg = t("core.inconnue.casse", cmd=brut, proche=cmd)        # PWD, Ls : les commandes s'écrivent en minuscules
        say(state, msg, 8)
        terminal(state, msg)
        log(state, t("core.inconnue.log", cmd=brut))
        animer(state, "confus")
        return
    # I6 : un alias ou une fonction créés par l'enfant (alias miam=…, miam() {…}) sont de vraies commandes
    persos = state.setdefault("alias_shell", [])
    for nom in re.findall(r"(?:^|[;&|]\s*)(?:alias\s+([\w.:-]+)=|function\s+([\w.:-]+)|([\w.:-]+)\s*\(\)\s*\{)", line):
        nom = next((x for x in nom if x), None)
        if nom and nom not in persos:
            persos.append(nom)
            del persos[:-30]
    cat = next((k for k, v in CATEGORIES.items() if cmd in v["cmds"]), None)
    if not cat and not cmd.startswith(("termux-", "./", "/")) and not commande_existe(cmd) and cmd not in persos:
        from . import verif
        proche = verif.collee(brut) or verif.ponctuation(brut) or verif.mot_de_l_oeuf(cmd) or commande_proche(cmd)
        # cdvestibule → cd vestibule, ls-a → ls -a, pwd, → pwd (I9), bonjour → echo bonjour (la liste de l'œuf, I9)
        msg = (t("core.inconnue.proche", cmd=cmd, proche=proche) if proche else t("core.inconnue", cmd=cmd))
        say(state, msg, 8)
        terminal(state, msg)
        log(state, t("core.inconnue.log", cmd=cmd))
        animer(state, "confus")
        return
    from . import satiete
    if cmd == "tg" or cmd in BUILTINS:          # v3 : une fonction du jeu « pas encore » ouverte ne nourrit pas
        from . import intro
        mots = line.split()
        sous = mots[1].lower() if cmd == "tg" and len(mots) > 1 else cmd
        if intro.bloque(state, sous):
            return
    if statut not in (None, 0):                 # la commande a échoué : elle nourrit à peine, sans XP ni nouveau goût
        satiete.repas(state, cmd, ratee=True)
        log(state, t("core.rate.log", cmd=cmd))
        animer(state, "confus")
        return
    state["total"] += 1
    # anti-remplissage (G-04) : une commande déjà goûtée parmi les FENETRE_REPAS dernières nourrit, mais ne donne
    # ni XP ni stat (les niveaux viennent des leçons, des chapitres, des exercices et des commandes nouvelles)
    derniers = state.setdefault("derniers", [])
    repetee = cmd in derniers and cmd in state["seen"]
    state["derniers"] = (derniers + [cmd])[-FENETRE_REPAS:]
    if repetee:
        satiete.repas(state, cmd, repetee=True)    # la même commande de suite : elle nourrit à peine
        state["repas_t"] = time.time()
        log(state, t("core.mange", cmd=cmd))
        animer(state, "mange")
        return
    gain, msg = 1, t("core.mange", cmd=cmd)
    if not cat and cmd.startswith("termux-"):
        cat = "reseau"
    if cat:
        state["stats"][CATEGORIES[cat]["stat"]] += 1
        gain += 1
        from .mots import palier
        if palier(state) >= 1:                   # « +END » : du jargon pour un enfant qui débute (P2-5)
            msg += " +" + nom_stat(CATEGORIES[cat]["stat"], court=True)
    nouvelle = cmd not in state["seen"]
    if nouvelle:
        state["seen"].append(cmd)
        gain += 5
        msg += t("core.mange.nouveau")
    vu_t = state["cherche"].pop(cmd, None)
    if vu_t and time.time() - vu_t < 900:
        gain += 5
        msg += t("core.mange.retenu")
    if cmd == "git" and "Mémoire" in state["skills"]:
        gain += 1
    if any(cmd in SKILLS[s]["cmds"] for s in state["skills"] if s in SKILLS):
        gain *= 2
        msg += " ×2"
    elif ("Créateur" in state["skills"] and not cat and cmd not in NOMS_CONNUS
          and not cmd.startswith(("./", ".\\"))):
        gain *= 3
        msg += t("core.mange.creation")
    satiete.repas(state, cmd, nouvelle=nouvelle)  # l'aliment de sa famille (nouveau goût, assiette, veille)
    state["repas_t"] = time.time()
    log(state, msg)
    animer(state, "mange")
    satiete.gagner_xp(state, gain)              # +20 % rassasiée, −20 % affamée (satiete.py)

# ================================================================ défis éclair

DEFI_POOL = ["pwd", "ls", "whoami", "date"]


def defi_duree(state):
    return 30 if "Chronomancien" in state["skills"] else 20


def defi_start(state):
    cmd = random.choice(DEFI_POOL)
    state["defi"] = {"cmd": cmd, "start": time.time()}
    say(state, t("core.defi.dit", cmd=piege(cmd)), defi_duree(state))
    notif(state, t("core.defi.notif", cmd=piege(cmd), s=defi_duree(state)))
    from . import guide
    guide.annonce_defi(state)                       # l'épreuve du jour annonce un type (guide.py)


def defi_tick(state, lines, spontaneous, proba=1.5 / 300):
    d = state["defi"]
    if not d:
        if spontaneous and stage(level(state["xp"])) >= 1 and random.random() < proba:
            from . import histoire, intro
            # les défis éclair arrivent avec les monstres (intro.json), jamais en pleine étape de leçon (P2-3)
            if intro.ouvert(state, "combats") and not histoire.en_pleine_etape(state):
                defi_start(state)
        return
    for line in lines:
        if not est_colle(line) and first_word(line) == d["cmd"]:
            dt = time.time() - d["start"]        # (pas « t » : ce nom cache la traduction t() plus bas)
            best = state["records"].get(d["cmd"])
            state["records"][d["cmd"]] = dt if best is None else min(best, dt)
            rec = tr("core.defi.record") if best is None or dt < best else ""
            log(state, tr("core.defi.reussi.log", cmd=d["cmd"], s=f"{dt:.1f}", record=rec))
            say(state, tr("core.defi.reussi.dit", s=f"{dt:.1f}", record=rec), 8)
            state["stats"]["Agilité"] += 2
            state["defi"] = None
            animer(state, "victoire")
            add_xp(state, 10)
            from . import envies, guide
            envies.plaisir(state, "jeu", "defi")
            guide.apres_defi(state)                 # guide fort contre le type du jour : +5 XP
            return
    if time.time() - d["start"] > defi_duree(state):
        log(state, t("core.defi.rate.log", cmd=d["cmd"]))
        say(state, t("core.defi.rate.dit"), 6)
        animer(state, "confus")
        state["defi"] = None


def idle_talk(state, proba=0.08):
    b = state["bubble"]
    if b and time.time() < b[1]:
        return
    state["bubble"] = None
    if random.random() > proba:
        return
    st = stage(level(state["xp"]))
    if st == 0:
        say(state, au_hasard("core.oeuf"))
    else:                      # la faim et les autres envies passent par envies.py (rappels espacés)
        from . import satiete
        if satiete.lien(state) >= satiete.LIEN_PHRASES and random.random() < 0.3:
            say(state, au_hasard("sat.lien.phrases", nom=state["name"]))     # le lien : ses phrases à elle
            return
        say(state, au_hasard("trait." + state["trait"] + ".phrases"))


def mood(h):
    if h >= 60:
        return t("humeur.repu")
    if h >= 30:
        return t("humeur.creux")
    if h > 0:
        return t("humeur.affame")
    return t("humeur.vide")

# ================================================================ sauvegarde

@contextmanager
def verrou(delai=3.0):
    """Empêche deux processus (fenêtre, invite, bureau, veille) d'écrire en même temps.
    Si le verrou ne peut pas être posé (droits retirés, disque plein), on continue sans : l'écriture dira pourquoi."""
    t0, fd = time.time(), None
    try:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        t0 = None
    while t0 is not None:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
            break
        except FileExistsError:
            pass
        except OSError:
            break                                         # droits retirés, disque plein : pas de verrou possible
        try:
            if time.time() - LOCK_FILE.lstat().st_mtime > 10:   # verrou abandonné
                LOCK_FILE.unlink()
                continue
        except FileNotFoundError:
            continue
        except OSError:
            break
        if time.time() - t0 > delai:
            break
        time.sleep(0.03)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
            try:
                LOCK_FILE.unlink()
            except OSError:
                pass


def modifier(fn):
    """Recharge l'état, applique fn, sauvegarde — le tout sous verrou."""
    with verrou():
        state = load()
        if state is None:
            return None
        migrate(state)
        fn(state)
        save(state)
    return state


# copies de secours de la sauvegarde (la plus récente d'abord) : save.json.bak, .bak2, .bak3
SECOURS = [SAVE_DIR / "save.json.bak", SAVE_DIR / "save.json.bak2", SAVE_DIR / "save.json.bak3"]
SECOURS_DELAI = 300       # secondes entre deux rotations des copies de secours


class Probleme(Exception):
    """Un souci que l'on explique à l'enfant (et à l'adulte) au lieu d'une trace Python."""


def _secours():
    return [SAVE_DIR / f.name for f in SECOURS]


def _lire_etat(f):
    """L'état rangé dans f (un dict), ou None s'il est illisible ; OSError si le fichier ne peut pas être ouvert."""
    try:
        o = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return o if isinstance(o, dict) and "xp" in o and "name" in o else None


def etat_sauvegarde():
    """« absente », « ok », « inaccessible » (droits) ou « abimee » (illisible, aucune copie de secours bonne)."""
    f = SAVE_DIR / "save.json"
    try:
        if not f.exists() and not f.is_symlink():
            return "absente"
        if _lire_etat(f) is not None:
            return "ok"
    except OSError:
        return "inaccessible"
    for b in _secours():
        try:
            if _lire_etat(b) is not None:
                return "ok"
        except OSError:
            pass
    return "abimee"


def _restaurer():
    """save.json est illisible : la plus récente copie de secours bonne le remplace ; le fichier abîmé est gardé à
    côté (save.json.casse-<date>), jamais effacé. Renvoie l'état restauré (avec la note pour la créature) ou None."""
    f = SAVE_DIR / "save.json"
    for b in _secours():
        try:
            st = _lire_etat(b)
        except OSError:
            continue
        if st is None:
            continue
        casse = SAVE_DIR / ("save.json.casse-" + time.strftime("%Y%m%d-%H%M%S"))
        try:
            if f.exists() or f.is_symlink():
                os.replace(f, casse)
            st["_restaure"] = {"de": b.name, "casse": casse.name}
            _ecrire_sauvegarde(st)
        except OSError:
            pass                              # lecture seule : on joue quand même avec la copie
        return st
    return None


def load():
    """L'état du jeu, ou None s'il n'y a pas (encore) de sauvegarde, ou si elle est abîmée sans copie de secours
    (etat_sauvegarde() dit lequel). OSError (droits retirés…) : remonte, l'appelant l'explique."""
    f = SAVE_DIR / "save.json"
    try:
        state = _lire_etat(f)
    except FileNotFoundError:
        return None
    if state is None:
        state = _restaurer()
        if state is None:
            return None
    if isinstance(state.get("name"), str) and nom_propre(state["name"]) != state["name"].strip()[:16]:
        state["name"] = nom_propre(state["name"]) or "Pixel"          # ESC, RLO, NUL : jamais jusqu'au terminal
    from . import bestiaire, langue
    langue.appliquer(state)                 # la langue choisie est rangée dans la sauvegarde
    try:
        from . import apparence
        apparence.activer(state)            # le thème : les couleurs du texte dans le terminal
    except Exception:                       # noqa: BLE001 — une apparence abîmée ne bloque jamais le jeu
        pass
    return bestiaire.migrer(state)


def _ecrire_sauvegarde(state, avec_secours=False):
    from . import sur
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    f = SAVE_DIR / "save.json"
    tmp = f.with_suffix(".tmp")
    data = json.dumps(state, ensure_ascii=False).encode("utf-8")
    try:
        if tmp.is_symlink():
            tmp.unlink()
        fd = sur.ouvrir_nofollow(tmp)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    if avec_secours:
        _tourner_secours(f)
    os.replace(tmp, f)                       # atomique : la sauvegarde n'est jamais à moitié écrite


def _tourner_secours(f):
    """La sauvegarde actuelle (si elle est bonne) devient save.json.bak ; les anciennes reculent d'un cran.
    Au plus une fois toutes les SECOURS_DELAI secondes (pas à chaque tour de jeu)."""
    sec = _secours()
    try:
        if sec[0].exists() and time.time() - sec[0].stat().st_mtime < SECOURS_DELAI:
            return
        if _lire_etat(f) is None:
            return                           # jamais une copie abîmée dans les secours
        for a, b in zip(reversed(sec[:-1]), reversed(sec[1:])):
            if a.exists() and not a.is_symlink():
                os.replace(a, b)
        from . import sur
        fd = sur.ouvrir_nofollow(sec[0])
        with os.fdopen(fd, "wb") as fh:
            fh.write(f.read_bytes())
    except OSError:
        pass                                 # les secours sont un bonus : jamais bloquants


def save(state):
    _ecrire_sauvegarde(state, avec_secours=True)
