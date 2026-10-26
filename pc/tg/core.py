"""Cœur du jeu : état, historique, nourriture, XP, caractère, défis, sauvegarde."""
import json
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path

from .langue import au_hasard, t
from .langue import t as tr
from .plateforme import GEST, IS_WIN, est_colle, piege

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


def first_word(line):
    words = line.split()
    if not words:
        return None
    w = words[0].lower()
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
PRIORITE_ANIM = {"evolution": 9, "victoire": 8, "ko": 7, "colere": 6, "attaque": 6, "dort": 6, "content": 5, "confus": 4,
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
    return {"name": name, "langue": langue_code, "shiny": random.randrange(64) == 0, "born": now, "last_tick": now, "xp": 0, "hunger": 80.0, "total": 0,
            "stats": {v["stat"]: 0 for v in CATEGORIES.values()}, "seen": [], "log": [],
            "offsets": {}, "version": VERSION}


def migrate(state):
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
    for k, v in {"notifs": True, "permanente": True, "compagnon": "ligne", "bulle": True}.items():
        state["config"].setdefault(k, v)
    state["version"] = VERSION
    return state


def add_xp(state, n):
    old = level(state["xp"])
    state["xp"] += n
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
    now = time.time()
    # secondes par point de faim : 2 fois plus lent qu'avant les envies (envies.py) ; Gardien double encore
    rate = 1440 if "Gardien" in state["skills"] else 720
    rate *= 1 + min(1.0, state["stats"].get("Endurance", 0) / 100)   # l'Endurance fait durer le repas
    avant = state["hunger"]
    state["hunger"] = max(0.0, state["hunger"] - (now - state["last_tick"]) / rate)
    if avant >= 30 > state["hunger"]:
        notif(state, t("core.notif.faim"))
    elif avant > 0 == state["hunger"]:
        notif(state, t("core.notif.epuise"))
    state["last_tick"] = now


BUILTINS = {"cd", "echo", "export", "alias", "history", "type", "source", ".", "exit", "for", "if", "while",
            "set", "unset", "read", "test", "[", "pushd", "popd", "jobs", "fg", "bg", "kill", "umask", "ulimit",
            "true", "false", "printf", "wait", "trap", "exec", "eval", "help", "tg", "clear",
            "carte", "quetes", "explique"}          # carte, quetes : les raccourcis du jeu (tg carte, tg quetes)


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


def feed(state, line):
    if est_colle(line):
        state["colles"] += 1
        log(state, t("core.colle.log"))
        say(state, au_hasard("core.colle"), 10)
        animer(state, "colere")
        return
    cmd = first_word(line)
    if not cmd:
        return
    cat = next((k for k, v in CATEGORIES.items() if cmd in v["cmds"]), None)
    if not cat and not cmd.startswith(("termux-", "./", "/")) and not commande_existe(cmd):
        proche = commande_proche(cmd)
        say(state, (t("core.inconnue.proche", cmd=cmd, proche=proche) if proche
                    else t("core.inconnue", cmd=cmd)), 8)
        log(state, t("core.inconnue.log", cmd=cmd))
        animer(state, "confus")
        return
    state["total"] += 1
    gain, msg = 1, t("core.mange", cmd=cmd)
    if not cat and cmd.startswith("termux-"):
        cat = "reseau"
    if cat:
        state["stats"][CATEGORIES[cat]["stat"]] += 1
        gain += 1
        msg += " +" + nom_stat(CATEGORIES[cat]["stat"], court=True)
    if cmd not in state["seen"]:
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
    state["hunger"] = min(100.0, state["hunger"] + 3)
    state["repas_t"] = time.time()
    log(state, msg)
    animer(state, "mange")
    add_xp(state, gain)

# ================================================================ défis éclair

DEFI_POOL = ["pwd", "ls", "whoami", "date"]


def defi_duree(state):
    return 30 if "Chronomancien" in state["skills"] else 20


def defi_start(state):
    cmd = random.choice(DEFI_POOL)
    state["defi"] = {"cmd": cmd, "start": time.time()}
    say(state, t("core.defi.dit", cmd=piege(cmd)), defi_duree(state))
    notif(state, t("core.defi.notif", cmd=piege(cmd), s=defi_duree(state)))


def defi_tick(state, lines, spontaneous, proba=1.5 / 300):
    d = state["defi"]
    if not d:
        if spontaneous and stage(level(state["xp"])) >= 1 and random.random() < proba:
            defi_start(state)
        return
    for line in lines:
        if not est_colle(line) and first_word(line) == d["cmd"]:
            t = time.time() - d["start"]
            best = state["records"].get(d["cmd"])
            state["records"][d["cmd"]] = t if best is None else min(best, t)
            rec = tr("core.defi.record") if best is None or t < best else ""
            log(state, tr("core.defi.reussi.log", cmd=d["cmd"], s=f"{t:.1f}", record=rec))
            say(state, tr("core.defi.reussi.dit", s=f"{t:.1f}", record=rec), 8)
            state["stats"]["Agilité"] += 2
            state["defi"] = None
            animer(state, "victoire")
            add_xp(state, 10)
            from . import envies
            envies.plaisir(state, "jeu", "defi")
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
    """Empêche deux processus (fenêtre, invite, bureau, veille) d'écrire en même temps."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    t0, fd = time.time(), None
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - LOCK_FILE.stat().st_mtime > 10:   # verrou abandonné
                    LOCK_FILE.unlink()
                    continue
            except OSError:
                continue
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


def load():
    try:
        state = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    from . import bestiaire, langue
    langue.appliquer(state)                 # la langue choisie est rangée dans la sauvegarde
    return bestiaire.migrer(state)


def save(state):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SAVE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SAVE_FILE)
