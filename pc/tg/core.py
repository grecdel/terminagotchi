"""Cœur du jeu : état, historique, nourriture, XP, caractère, défis, sauvegarde."""
import json
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path

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
    "Boussole":    {"desc": "navigation ×2", "cmds": {"cd", "ls", "dir", "pwd", "gci", "get-childitem", "set-location", "tree"}},
    "Bâtisseur":   {"desc": "création ×2 · ouvre l'exploration", "cmds": {"mkdir", "touch", "new-item", "echo"}},
    "Inspecteur":  {"desc": "lecture/recherche ×2", "cmds": {"cat", "type", "less", "more", "head", "tail", "grep", "find", "select-string", "get-content"}},
    "Gardien":     {"desc": "2× moins faim", "cmds": {"chmod", "chown", "attrib", "icacls"}},
    "Nettoyeur":   {"desc": "copie/déplacement ×2", "cmds": {"cp", "mv", "rm", "copy", "move", "del", "copy-item", "move-item", "remove-item"}},
    # branche Réseau
    "Radar":       {"desc": "ping/ip ×2", "cmds": {"ping", "ip", "ifconfig", "ipconfig", "test-connection"}},
    "Facteur":     {"desc": "curl/wget ×2", "cmds": {"curl", "curl.exe", "wget", "invoke-webrequest", "iwr"}},
    "Cartographe": {"desc": "dns/traceroute ×2", "cmds": {"nslookup", "dig", "traceroute", "tracert", "tracepath", "mtr"}},
    # branche Git
    "Archiviste":  {"desc": "git ×2", "cmds": {"git"}},
    "Mémoire":     {"desc": "+1 XP par commande git", "cmds": set()},
    "Chronomancien": {"desc": "défis éclair +50% de temps", "cmds": set()},
    # branche Scripts
    "Cuistot":     {"desc": "scripts ×2", "cmds": {"sh", "bash", "zsh", "powershell", "pwsh"}},
    "Inventeur":   {"desc": "alias/function ×2", "cmds": {"alias", "function"}},
    "Créateur":    {"desc": "TES commandes inventées ×3", "cmds": set()},
    # branche Système
    "Vigie":       {"desc": "processus ×2", "cmds": {"ps", "top", "htop", "get-process", "tasklist", "whoami"}},
    "Intendant":   {"desc": "espace disque ×2", "cmds": {"df", "du", "free", "get-psdrive"}},
    "Chasseur":    {"desc": "kill/jobs ×2", "cmds": {"kill", "killall", "jobs", "stop-process", "taskkill", "start-process"}},
    # branche Android
    "Télécommande": {"desc": "toast/vibreur/lampe ×2", "cmds": {"termux-toast", "termux-vibrate", "termux-torch"}},
    "Portier":     {"desc": "ouvrir sites et liens ×2", "cmds": {"termux-open-url", "termux-open", "am"}},
    "Lanceur":     {"desc": "lancer des applis ×2", "cmds": {"am", "pm", "ouvre"}},
    "Majordome":   {"desc": "outils du quotidien ×2", "cmds": {"termux-battery-status", "termux-tts-speak",
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

TRAITS = {
    "curieux": ["Qu'est-ce qu'il y a dans ce dossier ?", "Apprends-moi une nouvelle commande !",
                "Je me demande ce que fait « sudo »…", "Et si on explorait la grotte ?"],
    "farceur": ["Et si on renommait tous tes fichiers ? Je plaisante !", "rm -rf ? Jamais de la vie, hihi.",
                "Tu tapes vite… pour un humain.", "J'ai caché un fichier quelque part. Ou pas."],
    "gourmand": ["Une petite commande, juste une ?", "Les « git » sont mes préférés, croustillants !",
                 "J'ai un creux de 512 octets.", "Miam, un « ls » bien frais."],
    "philosophe": ["Sommes-nous tous dans le sous-dossier de quelqu'un ?",
                   "Un fichier supprimé existe-t-il encore dans nos cœurs ?",
                   "pwd… mais où suis-je VRAIMENT ?", "Le terminal est noir, mais l'avenir est clair."],
}
HUNGRY = ["J'ai faim… tape quelque chose !", "Mon ventre fait « segmentation fault ».",
          "Même un petit « pwd » me ferait du bien…"]
EGG = ["…", "*toc toc*", "*l'œuf bouge un peu*", "*crac ?*"]
COLLE = ["Hé ! Tu as copié-collé… tape-la toi-même, sinon ça ne rentre pas dans ma tête !",
         "Copier-coller détecté : ça n'a aucun goût. Avec tes doigts, s'il te plaît !",
         "Bien essayé ! Mais je ne mange que les commandes tapées à la main."]


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
PRIORITE_ANIM = {"evolution": 9, "victoire": 8, "ko": 7, "colere": 6, "attaque": 6, "content": 5, "confus": 4,
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

STAGES = ["Œuf", "Bébé", "Ado", "Adulte"]
FORMES = {"Intelligence": "Hacker", "Force": "Titan", "Agilité": "Éclair", "Endurance": "Carapace"}


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


def new_state(name):
    now = time.time()
    return {"name": name, "shiny": random.randrange(64) == 0, "born": now, "last_tick": now, "xp": 0, "hunger": 80.0, "total": 0,
            "stats": {v["stat"]: 0 for v in CATEGORIES.values()}, "seen": [], "log": [],
            "offsets": {}, "version": VERSION}


def migrate(state):
    defaults = {"trait": random.choice(list(TRAITS)), "skills": [], "lesson": 0, "step": 0,
                "bubble": None, "defi": None, "records": {}, "offsets": {}, "arbre": {},
                "branche": None, "cherche": {}, "sauvages": [], "collection": {}, "explo": False, "dressage": None,
                "explo_n": 0, "annonce": None, "colles": 0, "notifs": [], "nlog": 0,
                "prompt_vu": 0, "config": {}, "compte": {}, "repas_t": 0, "captures": [], "shiny": False}
    for k, v in defaults.items():
        state.setdefault(k, v)
    if stage(level(state["xp"])) >= 2 and not state.get("branch"):
        state["branch"] = dominant(state)
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
            log(state, "✨ L'œuf a éclos !")
            say(state, "Bonjour le monde ! … C'est comme ça qu'on dit, non ?", 10)
        else:
            if not state.get("branch"):
                state["branch"] = dominant(state)
            log(state, f"✨ ÉVOLUTION → {STAGES[stage(new)]} {FORMES[state['branch']]} !")
            say(state, "Waouh… je me sens différent !", 10)
    else:
        log(state, f"⬆ Niveau {new} !")


def tick(state):
    now = time.time()
    rate = 720 if "Gardien" in state["skills"] else 360   # secondes par point de faim
    rate *= 1 + min(1.0, state["stats"].get("Endurance", 0) / 100)   # l'Endurance fait durer le repas
    avant = state["hunger"]
    state["hunger"] = max(0.0, state["hunger"] - (now - state["last_tick"]) / rate)
    if avant >= 30 > state["hunger"]:
        notif(state, "🍽 J'ai faim… tape quelques commandes pour me nourrir !")
    elif avant > 0 == state["hunger"]:
        notif(state, "😵 Je suis à bout de forces… nourris-moi vite !")
    state["last_tick"] = now


BUILTINS = {"cd", "echo", "export", "alias", "history", "type", "source", ".", "exit", "for", "if", "while",
            "set", "unset", "read", "test", "[", "pushd", "popd", "jobs", "fg", "bg", "kill", "umask", "ulimit",
            "true", "false", "printf", "wait", "trap", "exec", "eval", "help", "tg", "clear"}


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
        log(state, "✖ copier-coller détecté : pas de nourriture")
        say(state, random.choice(COLLE), 10)
        animer(state, "colere")
        return
    cmd = first_word(line)
    if not cmd:
        return
    cat = next((k for k, v in CATEGORIES.items() if cmd in v["cmds"]), None)
    if not cat and not cmd.startswith(("termux-", "./", "/")) and not commande_existe(cmd):
        proche = commande_proche(cmd)
        say(state, (f"« {cmd} » n'est pas une commande… tu voulais dire « {proche} » ?" if proche
                    else f"« {cmd} » n'est pas une commande. Essaie : ls, pwd, cd"), 8)
        log(state, f"✖ « {cmd} » : commande inconnue, pas de nourriture")
        animer(state, "confus")
        return
    state["total"] += 1
    gain, msg = 1, f"a mangé « {cmd} »"
    if not cat and cmd.startswith("termux-"):
        cat = "reseau"
    if cat:
        state["stats"][CATEGORIES[cat]["stat"]] += 1
        gain += 1
        msg += f" +{CATEGORIES[cat]['short']}"
    if cmd not in state["seen"]:
        state["seen"].append(cmd)
        gain += 5
        msg += " ★ nouveau goût"
    t = state["cherche"].pop(cmd, None)
    if t and time.time() - t < 900:
        gain += 5
        msg += " ★ bien retenu"
    if cmd == "git" and "Mémoire" in state["skills"]:
        gain += 1
    if any(cmd in SKILLS[s]["cmds"] for s in state["skills"] if s in SKILLS):
        gain *= 2
        msg += " ×2"
    elif ("Créateur" in state["skills"] and not cat and cmd not in NOMS_CONNUS
          and not cmd.startswith(("./", ".\\"))):
        gain *= 3
        msg += " ×3 création"
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
    say(state, f"DÉFI ÉCLAIR ! Tape « {piege(cmd)} » vite !", defi_duree(state))
    notif(state, f"⚡ Défi éclair ! Tape « {piege(cmd)} » dans les {defi_duree(state)} s !")


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
            rec = " NOUVEAU RECORD !" if best is None or t < best else ""
            log(state, f"⚡ Défi « {d['cmd']} » réussi en {t:.1f} s{rec}")
            say(state, f"Trop rapide ! {t:.1f} s.{rec}", 8)
            state["stats"]["Agilité"] += 2
            state["defi"] = None
            animer(state, "victoire")
            add_xp(state, 10)
            return
    if time.time() - d["start"] > defi_duree(state):
        log(state, f"⚡ Défi « {d['cmd']} » raté…")
        say(state, "Trop lent ! On réessaiera.", 6)
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
        say(state, random.choice(EGG))
    elif state["hunger"] < 30:
        say(state, random.choice(HUNGRY))
    else:
        say(state, random.choice(TRAITS[state["trait"]]))


def mood(h):
    if h >= 60:
        return "repu"
    if h >= 30:
        return "petit creux"
    if h > 0:
        return "affamé !"
    return "NOURRIS-MOI…"

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
    from . import bestiaire
    return bestiaire.migrer(state)


def save(state):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SAVE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SAVE_FILE)
