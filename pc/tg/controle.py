"""📟 Le Poste de Contrôle — l'administration système (docs/programme.md § 2.15 et § 7.13 « Linux de A à Z »).

Le douzième monde de la phase 5 (§ 7.14, étape 9). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 6 du tronc commun (programme.json, « mondes » → controle → requis). Le chapitre et le lieu s'appellent
« controle » : ~/terrain_terminagotchi/controle/. On en sort et on y revient, l'étape est gardée.

L'IMAGE : la salle de contrôle d'un vaisseau. Les processus sont les habitants qui travaillent ou dorment, la mémoire le
garde-manger, le disque l'entrepôt, la charge le souffle des moteurs, les variables d'environnement le sac à dos que
chaque habitant emporte (PATH : le carnet d'adresses des outils), les journaux le carnet de bord, cron le réveil
programmé, les paquets le magasin d'outils, les services les gardiens qui ne dorment jamais, les utilisateurs l'équipage.

RÈGLES (affichées à l'entrée, consignes_du_poste.txt) :
  - LECTURE SEULE sur le vrai système. Le jeu lit /proc, free, df, uptime, /etc/os-release, la base des paquets,
    systemctl (lister), /etc/passwd (les noms) : il ne change rien et ne garde rien (aucun nom de machine, aucun nom
    d'utilisateur, aucune liste de processus enregistrés).
  - Le jeu n'arrête JAMAIS un vrai processus de l'enfant : `kill` ne vise que les processus qu'il a lui-même lancés
    (des `sleep` renommés, comme à la Citadelle : `exec -a glouton_fictif sleep 900`, qui s'éteignent seuls), après avoir
    vérifié leur numéro ET leur nom. Sous Windows et sur le téléphone, la vague est simulée (`controle ps`,
    `controle arrete`).
  - Aucun service arrêté ni redémarré, aucun paquet installé ni mis à jour, aucun utilisateur créé, aucune tâche cron
    posée sur la vraie machine. `sudo dnf install`, `systemctl restart`, `useradd`, `crontab -e` sont EXPLIQUÉS (avec
    un adulte, et pour useradd dans une machine virtuelle) ; dans le jeu, le réveil est un fichier du terrain
    (reveils.crontab) que le jeu lit sans jamais le lancer, et l'équipage un fichier du terrain (equipage.txt).
  - Tout ce qui s'écrit reste dans le terrain (terrain_terminagotchi/controle).

LES PALIERS (ct0 à ct7) : la porte ; K1 les habitants (ps, $$, le lieu magique /proc, avant-plan et arrière-plan,
jobs, kill %1, top) ; K2 les jauges (free, df, du dans l'entrepôt, uptime, nproc, le tableau des jauges) ; K3 le sac à
dos (echo $HOME, PATH, which, export, bash -c, alias, source d'un fichier du terrain) ; K4 le carnet de bord (tail,
grep -c, tail -f, journalctl --user, dmesg) ; K5 les réveils (crontab -l, les 5 champs, un réveil ajouté au fichier du
terrain) ; « Linux de A à Z » (os-release, les familles de distributions, installer d'abord dans une VM, le magasin de
paquets en lecture, les services, l'équipage) ; l'alerte : la vague de processus suspects (exploit « tous les suspects
arrêtés, le veilleur épargné »).

Ponts : la Salle des Rouages (M4 le système d'exploitation, M1 les organes), la Citadelle (C4 les processus fantômes),
la Forge (scripts2 « Pour toujours » : le .bashrc), l'Observatoire (export), la Guilde (les paquets, les licences).
Mêmes règles sur Android (Controle.kt, vecteurs communs donnees/controle/vecteurs.json).
"""
import datetime
import hashlib
import json
import os
import pkgutil
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from . import core
from .langue import t
from .plateforme import BOLD, DIM, IS_WIN, RESET, LINUX_VIRTUEL, SYS_WIN, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "controle.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def melange(graine, sel, liste):
    l2 = list(liste)
    random.Random(f"{sel}:{graine}").shuffle(l2)
    return l2


def _tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


# ---------------------------------------------------------------- K2 l'entrepôt
def caisses(graine):
    """Les caisses de l'entrepôt de cette partie : [(nom, taille en Kio)] dans l'ordre des noms ; les tailles sont
    mélangées (une seule est la plus lourde)."""
    e = donnees()["entrepot"]
    tailles = melange(graine, "entrepot", e["tailles_kio"])
    return sorted(zip(e["caisses"], tailles))


def caisse_lourde(graine):
    return max(caisses(graine), key=lambda x: x[1])[0]


def caisse_octets(graine, nom):
    """Le contenu d'une caisse : des octets tirés d'une empreinte (ils ne se compressent pas : du dit la vraie taille)."""
    kio = dict(caisses(graine))[nom]
    out = bytearray()
    k = 0
    while len(out) < kio * 1024:
        out += hashlib.sha256(f"caisse:{nom}:{k}".encode()).digest()
        k += 1
    return bytes(out[:kio * 1024])


def caisse_ok(reponse, graine):
    r = ascii_bas((reponse or "").strip()).replace("\\", "/").rstrip("/").split("/")[-1]
    if r.endswith(".bin"):
        r = r[:-4]
    return bool(r) and r == caisse_lourde(graine)


def pourcentage(utilise, total):
    """L'entier le plus proche de utilise × 100 / total (0 si total vaut 0)."""
    if not total:
        return 0
    return (utilise * 200 + total) // (2 * total)


def jauge(p, largeur=20):
    """Une jauge en caractères : ▮ pour la part utilisée, ▯ pour le reste (p entre 0 et 100)."""
    p = max(0, min(100, int(p)))
    n = (p * largeur + 50) // 100
    return "▮" * n + "▯" * (largeur - n)


# ---------------------------------------------------------------- K3 le carnet d'adresses (PATH)
def dossiers_path(path, win=False):
    """Les dossiers d'un PATH, dans l'ordre (les vides comptent : « :: » veut dire « ici »)."""
    return (path or "").split(";" if win else ":")


def path_ok(reponse, path, win=False):
    """Le nombre de dossiers du PATH : avec ou sans les doublons (tr ':' '\\n' les montre tous)."""
    try:
        n = int((reponse or "").strip())
    except ValueError:
        return False
    d = dossiers_path(path, win)
    return n in (len(d), len(set(d)), len([x for x in d if x]))


# ---------------------------------------------------------------- K4 le carnet de bord
def journal_lignes(graine):
    """Le carnet de bord du poste (texte du jeu, toujours le même pour une partie) : [ligne] ; les ALERTE sont tirées."""
    j = donnees()["journal"]
    n_alertes = j["alertes"][_tire(graine, "alertes", len(j["alertes"]))]
    places = sorted(melange(graine, "places", list(range(1, j["total"])))[:n_alertes])
    infos = j["infos"]
    alertes = melange(graine, "alertes_txt", j["textes_alerte"])
    out = []
    a = 0
    for i in range(j["total"]):
        h, m = divmod(6 * 60 + 7 * i, 60)
        quand = f"{j['jour']} {h:02d}:{m:02d}:{(13 * i) % 60:02d}"
        if i in places:
            out.append(f"{quand} ALERTE {alertes[a % len(alertes)]}")
            a += 1
        else:
            out.append(f"{quand} INFO {infos[(i * 5 + _tire(graine, 'infos', len(infos))) % len(infos)]}")
    return out


def nb_alertes(graine):
    return sum(1 for l in journal_lignes(graine) if " ALERTE " in l)


# ---------------------------------------------------------------- K5 les réveils (cron)
CHAMPS = [("minute", 0, 59), ("heure", 0, 23), ("jour", 1, 31), ("mois", 1, 12), ("semaine", 0, 7)]


def champ_cron(texte, bas, haut):
    """L'ensemble des valeurs d'un champ cron (« * », « */15 », « 1-5 », « 0,30 », « 8-18/2 »), ou None s'il est faux."""
    vals = set()
    if not texte:
        return None
    for morceau in texte.split(","):
        m = re.fullmatch(r"(\*|\d+(?:-\d+)?)(?:/(\d+))?", morceau)
        if not m:
            return None
        if m.group(1) == "*":
            a, b = bas, haut
        elif "-" in m.group(1):
            a, b = (int(x) for x in m.group(1).split("-"))
        else:
            a = b = int(m.group(1))
            if m.group(2):
                b = haut
        pas = int(m.group(2)) if m.group(2) else 1
        if pas < 1 or a < bas or b > haut or a > b:
            return None
        vals.update(range(a, b + 1, pas))
    return vals


def cron(ligne):
    """Les 5 champs d'une ligne cron comme ensembles de valeurs (dimanche : 0 ou 7 → 0), ou None. Ce qui suit les 5
    champs (la commande) est ignoré ; une ligne vide ou un commentaire donne None."""
    mots = (ligne or "").split()
    if len(mots) < 5 or mots[0].startswith("#"):
        return None
    out = []
    for (_n, bas, haut), m in zip(CHAMPS, mots[:5]):
        v = champ_cron(m, bas, haut)
        if v is None:
            return None
        out.append(v)
    if 7 in out[4]:
        out[4] = (out[4] - {7}) | {0}
    return out


def cron_pareil(a, b):
    ca, cb = cron(a), cron(b)
    return ca is not None and ca == cb


def cron_situation(graine):
    s = donnees()["cron"]["situations"]
    return s[_tire(graine, "cron", len(s))]


def cron_ok(reponse, graine):
    return cron_pareil(" ".join((reponse or "").replace('"', " ").replace("'", " ").split()), cron_situation(graine)["rep"])


def _etoiles(ligne):
    """(jour du mois libre, jour de la semaine libre) : comme cron, un champ qui commence par « * » est libre."""
    mots = (ligne or "").split()
    return mots[2].startswith("*"), mots[4].startswith("*")


def jour_ok(c, etoiles, d):
    """Le réveil c (5 ensembles) peut sonner ce jour-là ? Comme cron : si le jour du mois ET le jour de la semaine sont
    restreints tous les deux, il suffit que l'un des deux corresponde."""
    sem = d.isoweekday() % 7
    if etoiles[0] or etoiles[1]:
        return d.day in c[2] and sem in c[4]
    return d.day in c[2] or sem in c[4]


def prochaine(ligne, depuis):
    """La prochaine minute (strictement après depuis, un datetime) où le réveil sonne, ou None (pas dans les 400 jours)."""
    c = cron(ligne)
    if c is None:
        return None
    et = _etoiles(ligne)
    d = depuis.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    fin = d + datetime.timedelta(days=400)
    while d < fin:
        if d.month not in c[3] or not jour_ok(c, et, d):
            d = (d + datetime.timedelta(days=1)).replace(hour=0, minute=0)
            continue
        if d.hour not in c[1]:
            d = (d + datetime.timedelta(hours=1)).replace(minute=0)
            continue
        if d.minute in c[0]:
            return d
        d += datetime.timedelta(minutes=1)
    return None


def lignes_crontab(texte):
    """Les lignes d'un fichier crontab : [(ligne, valide)] sans les commentaires ni les lignes vides."""
    out = []
    for l in (texte or "").splitlines():
        s = l.strip()
        if not s or s.startswith("#"):
            continue
        out.append((s, cron(s) is not None and len(s.split()) > 5))
    return out


# ---------------------------------------------------------------- Linux de A à Z
def familles_cartes(graine):
    """Les distributions à relier à leur magasin (d : dnf, a : apt, p : pacman), mélangées : [(n°, id, lettre)]."""
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(melange(graine, "familles", donnees()["familles"]["distributions"]))]


def quiz_justes(cartes, rep, lettres):
    """(réponse bien formée, [(n°, id) justes]) ; rep : ce que l'enfant a tapé (la première lettre de chaque mot)."""
    r = [ascii_bas(x)[:1] for x in rep]
    if len(r) != len(cartes) or any(not x or x not in lettres for x in r):
        return False, []
    return True, [(n, i) for (n, i, rr), x in zip(cartes, r) if x == rr]


def os_release_de(texte):
    d = {}
    for l in (texte or "").splitlines():
        if "=" in l and not l.lstrip().startswith("#"):
            k, v = l.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def distribution_ok(reponse, osr):
    """Le nom de la distribution : l'ID d'/etc/os-release, un mot d'ID_LIKE ou le premier mot de NAME (sans
    majuscules ni accents)."""
    r = re.sub(r"[^a-z0-9]", "", ascii_bas(reponse or ""))
    if not r or not osr:
        return False
    justes = {re.sub(r"[^a-z0-9]", "", ascii_bas(osr.get("ID", "")))}
    justes |= {re.sub(r"[^a-z0-9]", "", ascii_bas(x)) for x in osr.get("ID_LIKE", "").split()}
    if osr.get("NAME"):
        justes.add(re.sub(r"[^a-z0-9]", "", ascii_bas(osr["NAME"].split()[0])))
    justes.discard("")
    return r in justes


def nom_valide(nom):
    return re.fullmatch(r"[a-z_][a-z0-9_-]{0,15}", nom or "") is not None


def equipage_ajoute(texte, nom):
    """Le registre de l'équipage (comme /etc/passwd, dans le terrain) avec un membre de plus : (texte, uid), ou
    (texte, None) si le nom est déjà là ou n'est pas valide."""
    lignes = [l for l in (texte or "").splitlines() if l.strip()]
    noms = {l.split(":")[0] for l in lignes}
    if not nom_valide(nom) or nom in noms:
        return texte, None
    uids = [int(l.split(":")[2]) for l in lignes if len(l.split(":")) > 2 and l.split(":")[2].isdigit()]
    uid = max([u for u in uids if u >= 1000] + [donnees()["equipage"]["uid_depart"] - 1]) + 1
    lignes.append(f"{nom}:x:{uid}:{uid}::/home/{nom}:/bin/bash")
    return "\n".join(lignes) + "\n", uid


def nouveaux_membres(texte):
    base = {l.split(":")[0] for l in donnees()["equipage"]["base"]}
    return [l.split(":")[0] for l in (texte or "").splitlines() if l.strip() and l.split(":")[0] not in base]


# ---------------------------------------------------------------- l'alerte : la vague de processus suspects
def vague_suspects(graine, n):
    """Les suspects de la vague n° n (3 noms tirés de la liste) ; le veilleur, lui, est toujours le même."""
    v = donnees()["vague"]
    return sorted(melange(graine, f"vague:{n}", v["suspects"])[:v["par_vague"]])


def pids_simules(graine, n):
    """Les numéros SIMULÉS de la vague (Windows, téléphone) : {nom: pid} pour les suspects et le veilleur."""
    v = donnees()["vague"]
    noms = vague_suspects(graine, n) + [v["veilleur"]]
    out = {}
    for k, nom in enumerate(noms):
        p = 2000 + int(hashlib.sha256(f"{graine}:{n}:{nom}".encode()).hexdigest()[:6], 16) % 7000
        while p in out.values():
            p += 1
        out[nom] = p
    return out


def bilan_vague(suspects_vivants, veilleur_vivant):
    """« gagne » (tous les suspects arrêtés, le veilleur épargné), « veilleur » (le veilleur arrêté par erreur),
    « encore » (il reste des suspects)."""
    if not veilleur_vivant:
        return "veilleur"
    return "gagne" if not suspects_vivants else "encore"


# ---------------------------------------------------------------- le tableau de bord (vue déployée)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def tableau_de(morceau):
    """(jauge, sens) d'une commande (un morceau de ligne), ou None : la première règle de controle.json."""
    m = (morceau or "").strip()
    for r in donnees()["tableau"]["regles"]:
        if re.search(r["motif"], m, re.I):
            return r["jauge"], r["sens"]
    return None


def tableaux_de(ligne):
    out = []
    for m in SEPARATEURS.split(ligne or ""):
        a = tableau_de(m)
        if a:
            out.append(a)
    return out


# ================================================================ l'état, le terrain, le registre du poste
def c_(state):
    c = state.setdefault("controle", {})
    c.setdefault("faits", [])
    c.setdefault("vague", 0)
    c.setdefault("arretes", [])
    return c


def dossier():
    return core.TERRAIN / "controle"


REGISTRE = "registre_du_poste.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / REGISTRE, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def registre():
    try:
        return (dossier() / REGISTRE).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_registre(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", registre(), re.M) is not None


def dernier(etiquette):
    der = [l for l in registre().splitlines() if l.startswith(f"[{etiquette}]")]
    return der[-1] if der else None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, contenu):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            p.write_bytes(contenu)
        else:
            p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def _lire(rel):
    try:
        return (core.TERRAIN / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def sac_a_dos():
    s = donnees()["sac"]
    return f"# {t('ct.sac.entete')}\n" + "\n".join(s["lignes"]) + "\n"


def reveils_texte():
    c = donnees()["cron"]
    return "\n".join(f"# {l}" for l in t("ct.reveils.entete").split("\n")) + "\n" + "\n".join(c["exemples"]) + "\n"


def equipage_texte():
    return "\n".join(donnees()["equipage"]["base"]) + "\n"


def meubles(state):
    """Ce que le jeu pose dans le Poste quand il s'ouvre : {chemin relatif au terrain: contenu}."""
    gr = _graine(state)
    m = {"controle/consignes_du_poste.txt": t("ct.meuble.consignes", nom=state.get("name", "")) + "\n",
         f"controle/{REGISTRE}": t("ct.meuble.registre") + "\n",
         "controle/sac_a_dos.sh": sac_a_dos(),
         "controle/reveils.crontab": reveils_texte(),
         "controle/equipage.txt": equipage_texte()}
    for nom, _k in caisses(gr):
        m[f"controle/entrepot/{nom}.bin"] = caisse_octets(gr, nom)
    return m


BESOINS = {"ct0": ["consignes_du_poste.txt"], "ct3": ["sac_a_dos.sh"], "ct5": ["reveils.crontab"],
           "ct6": ["equipage.txt"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon du Poste : les fichiers dont la leçon a besoin, les ponts des nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire("controle/" + rel, tous["controle/" + rel])
    if lid == "ct2":
        for rel, x in tous.items():
            if rel.startswith("controle/entrepot/") and not (core.TERRAIN / rel).exists():
                _ecrire(rel, x)
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = c_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("ct.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("ct.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- la vraie machine (lue, jamais modifiée)
def _lire_sys(chemin):
    if LINUX_VIRTUEL and chemin.startswith("/"):        # le terminal du jeu : ses lieux du système (vsh/vfs.py)
        try:
            from .vsh.vfs import vfs_du_jeu
            return vfs_du_jeu().lire(chemin).decode("utf-8", "replace")
        except Exception:                         # noqa: BLE001
            return ""
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def etats_processus():
    """{état: nombre} des processus visibles (R au travail, S endormis, D…, Z fantômes, T arrêtés), lu dans /proc ou
    avec `ps -A -o stat=` ; {} si on ne peut pas lire (Windows). Rien n'est gardé."""
    out = {}
    if os.path.isdir("/proc/self"):
        for p in os.listdir("/proc"):
            if not p.isdigit():
                continue
            txt = _lire_sys(f"/proc/{p}/stat")
            m = re.search(r"\)\s+(\w)", txt)
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + 1
        return out
    if shutil.which("ps") and not IS_WIN:
        try:
            r = subprocess.run(["ps", "-A", "-o", "stat="], capture_output=True, text=True, timeout=10)
            for l in r.stdout.split():
                out[l[0]] = out.get(l[0], 0) + 1
        except (OSError, subprocess.SubprocessError):
            pass
    return out


def memoire():
    """(utilisée, totale) en Kio, lue dans /proc/meminfo (MemTotal − MemAvailable), ou None."""
    txt = _lire_sys("/proc/meminfo")
    tot = re.search(r"^MemTotal:\s+(\d+)", txt, re.M)
    dispo = re.search(r"^MemAvailable:\s+(\d+)", txt, re.M)
    if tot and dispo:
        return int(tot.group(1)) - int(dispo.group(1)), int(tot.group(1))
    return None


def disque():
    """(utilisé, total) en octets du disque où vit le terrain (comme df), ou None."""
    try:
        u = shutil.disk_usage(str(core.TERRAIN if core.TERRAIN.exists() else Path.home()))
        return u.used, u.used + u.free
    except OSError:
        return None


def charge():
    """(charge sur 1 minute, nombre de cœurs) ou None (Windows)."""
    try:
        from . import machines
        return os.getloadavg()[0], machines.coeurs()
    except (OSError, AttributeError):
        return None


def path_actuel():
    if LINUX_VIRTUEL:                                   # le terminal du jeu (Linux virtuel) : son PATH à lui
        return "/usr/local/bin:/usr/bin:/bin"
    return os.environ.get("PATH", "")


def os_release():
    if LINUX_VIRTUEL:                                   # le terminal du jeu : son /etc/os-release (vsh/vfs.py)
        from .vsh.vfs import OS_RELEASE
        return os_release_de(OS_RELEASE)
    for f in ("/etc/os-release", "/usr/lib/os-release"):
        txt = _lire_sys(f)
        if txt:
            return os_release_de(txt)
    return {}


def magasin():
    """Le magasin de paquets de cette machine : (entrée de controle.json, nombre de paquets installés ou None).
    Lecture seule : la base des paquets est LUE (rpm -qa seulement là où rpm est le gestionnaire du système, sinon il
    créerait ~/.rpmdb ; dpkg : le fichier status ; pacman : les dossiers de sa base)."""
    if LINUX_VIRTUEL:
        return None, None
    for m in donnees()["magasins"]:
        if not os.path.exists(m["base"]):
            continue
        return m, compter_paquets(m)
    return None, None


def compter_paquets(m):
    try:
        if m["id"] == "apt":
            return len(re.findall(r"^Status: install ok installed$", _lire_sys(m["base"]), re.M))
        if m["id"] == "pacman":
            return len([x for x in os.listdir(m["base"]) if os.path.isdir(os.path.join(m["base"], x))])
        if m["id"] == "apk":
            return len(re.findall(r"^P:", _lire_sys(m["base"]), re.M))
        if m["id"] in ("dnf", "zypper") and shutil.which("rpm"):
            r = subprocess.run(["rpm", "-qa"], capture_output=True, text=True, timeout=60)
            return len([l for l in r.stdout.splitlines() if l.strip()]) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def services_actifs():
    """Le nombre de services qui tournent (systemctl, lecture seule), ou None."""
    if IS_WIN or not shutil.which("systemctl"):
        return None
    try:
        r = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager",
                            "--plain"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        return len([l for l in r.stdout.splitlines() if l.strip()])
    except (OSError, subprocess.SubprocessError):
        return None


# ---------------------------------------------------------------- les processus de la vague (PC : de vrais `sleep`)
def _fichier_pids():
    return core.SAVE_DIR / "controle" / "vague.json"


def _pids():
    try:
        return json.loads(_fichier_pids().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _ecrire_pids(liste):
    try:
        _fichier_pids().parent.mkdir(parents=True, exist_ok=True)
        _fichier_pids().write_text(json.dumps(liste), encoding="utf-8")
    except OSError:
        pass


def _vivant(pid, nom=None):
    try:
        if os.waitpid(pid, os.WNOHANG)[0] == pid:            # notre enfant, déjà fini : récolté
            return False
    except (ChildProcessError, OSError, AttributeError):
        pass
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    proc = Path(f"/proc/{pid}")
    if proc.is_dir():
        try:
            if "State:\tZ" in (proc / "status").read_text():
                return False
            if nom and nom.encode() not in (proc / "cmdline").read_bytes():
                return False                                  # le numéro a été réutilisé par autre chose
        except OSError:
            return False
    return True


def simulee():
    """Windows (le terminal du jeu) : pas de `exec -a` ; la vague est simulée (ps, kill du terminal du jeu ; controle ps,
    controle arrete)."""
    from .plateforme import terminal_virtuel
    return SYS_WIN or terminal_virtuel()


def vivants(state=None):
    """[(pid, nom)] des processus de la vague encore en vie (PC : les vrais ; Windows : la simulation)."""
    if simulee():
        if state is None:
            state = core.load() or {}
        c = c_(state)
        if not c["vague"]:
            return []
        p = pids_simules(_graine(state), c["vague"])
        return [(pid, nom) for nom, pid in sorted(p.items(), key=lambda x: x[1]) if nom not in c["arretes"]]
    return [(p["pid"], p["nom"]) for p in _pids() if _vivant(p["pid"], p["nom"])]


def suspects_vivants(state=None):
    v = donnees()["vague"]["veilleur"]
    return [(p, n) for p, n in vivants(state) if n != v]


def veilleur_vivant(state=None):
    v = donnees()["vague"]["veilleur"]
    return any(n == v for _p, n in vivants(state))


def lancer(noms):
    """Lance des `sleep` renommés (exec -a NOM sleep 900) : ils ne font RIEN que dormir, puis s'éteignent seuls.
    Renvoie les pid lancés."""
    if simulee():
        return []
    out = []
    liste = _pids()
    for nom in noms:
        try:
            p = subprocess.Popen(["bash", "-c", f"exec -a {nom} sleep {donnees()['vague']['secondes']}"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        except OSError:
            continue
        out.append(p.pid)
        liste.append({"pid": p.pid, "nom": nom})
    # les tout nouveaux sont gardés sans relire leur nom (juste après le fork, /proc/PID/cmdline peut être celui de Python)
    _ecrire_pids([x for x in liste if x["pid"] in out or _vivant(x["pid"], x["nom"])])
    try:
        deja = json.loads(_fichier_lances().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        deja = []
    try:
        _fichier_lances().write_text(json.dumps((deja + out)[-60:]), encoding="utf-8")
    except OSError:
        pass
    return out


def arreter_tout():
    """Éteint les processus de la vague encore en vie (seulement les nôtres : le numéro ET le nom sont vérifiés)."""
    if simulee():
        return
    for pid, _nom in vivants():
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    for _ in range(20):
        if not vivants():
            break
        time.sleep(0.05)
    _ecrire_pids([])


def arreter(state, pid):
    """`controle arrete PID` : arrête UN processus de la vague (simulation sous Windows ; sur PC, seulement s'il est
    à nous). Renvoie le nom arrêté, ou None."""
    for p, nom in vivants(state):
        if p == pid:
            if simulee():
                c_(state)["arretes"].append(nom)
            else:
                try:
                    os.kill(pid, 15)
                except OSError:
                    return None
                for _ in range(20):
                    if not _vivant(pid, nom):
                        break
                    time.sleep(0.05)
            return nom
    return None


def _fichier_lances():
    return core.SAVE_DIR / "controle" / "lances.json"


def pids_a_nous():
    """Les numéros de TOUS les processus que le jeu a lancés (même déjà arrêtés : un kill est vu après coup), ceux de la
    Citadelle compris."""
    try:
        out = set(json.loads(_fichier_lances().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        out = set()
    out |= {p for p, _n in vivants()}
    try:
        from . import citadelle
        out |= {x["pid"] for x in citadelle._pids()}
    except Exception:                                    # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
CT = r"^(tg\s+)?controle\s+"


def _fs_caisse():
    return dans_registre("entrepot")


def _fs_reveil():
    lignes = lignes_crontab(_lire("controle/reveils.crontab"))
    exemples = {" ".join(x.split()) for x in donnees()["cron"]["exemples"]}
    return any(ok and " ".join(l.split()) not in exemples for l, ok in lignes)


def _fs_equipage():
    return bool(nouveaux_membres(_lire("controle/equipage.txt")))


FS = {
    "ct_entrepot": _fs_caisse,
    "ct_path": lambda: dans_registre("path"),
    "ct_alertes": lambda: dans_registre("alertes"),
    "ct_journal": lambda: (dossier() / "carnet_de_bord.log").is_file(),
    "ct_cron": lambda: dans_registre("cron"),
    "ct_reveil": _fs_reveil,
    "ct_distribution": lambda: dans_registre("distribution"),
    "ct_familles": lambda: dans_registre("familles"),
    "ct_equipage": _fs_equipage,
    "ct_arretes": lambda: dans_registre("vague", "lancee") and not suspects_vivants(),
    "ct_tableau": lambda: dans_registre("tableau", "gagne"),
}
CREE = {}


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


def C_(unix, win):
    return win if IS_WIN else unix


LECONS = {
    # la porte du Poste
    "ct0": {"titre": "hist.ct0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "controle"}), "cmd": "cd ~/terrain_terminagotchi/controle", "ici": "controle",
         "bravo": ("hist.entree.bravo", {"piece": "controle"})},
        _n("ct0", 1, cmd="ls", re=LS, ou="controle"),
        _n("ct0", 2, cmd=C_("cat consignes_du_poste.txt", "type consignes_du_poste.txt"), re=LIRE + r".*consignes_du_poste",
           ou="controle"),
    ]},
    # K1 les habitants : processus, PID, /proc, avant-plan et arrière-plan, jobs, kill
    "ct1": {"titre": "hist.ct1.titre", "skill": None, "steps": [
        _n("ct1", 0, cmd=C_("ps", "Get-Process"), re=r"^(ps|get-process|gps)\b", ou="controle"),
        _n("ct1", 1, cmd=C_("echo $$", "$PID"), re=r"^(echo\s+(\$\$|\$pid|\$bashpid)|\$pid)\s*$"),
        _n("ct1", 2, cmd="ls /proc/$$", re=r"^ls\b.*/proc/(\$\$|self|\d+)\s*$", outil="/proc/self", win=False),
        _n("ct1", 3, cmd="head -3 /proc/$$/status", re=LIRE + r".*/proc/(\$\$|self|\d+)/status", outil="/proc/self/status",
           win=False),
        _n("ct1", 4, cmd="controle habitants", re=CT + r"habitants?\b"),
        _n("ct1", 5, cmd=C_("sleep 5", "Start-Sleep 5"), re=r"^(sleep|start-sleep)\s+\d+\s*$"),
        _n("ct1", 6, cmd="sleep 60 &", re=r"^sleep\s+\d+\s*&\s*$", win=False),
        _n("ct1", 7, cmd="jobs", re=r"^jobs\b", win=False),
        _n("ct1", 8, cmd="kill %1", re=r"^kill\s+(-\w+\s+)?%\d?\s*$", win=False),
        _n("ct1", 9, cmd=C_("top", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5"),
           re=r"^(top|htop)\b|^(get-process|gps)\b.*sort", outil=None if IS_WIN else "top", tout_code=True),
    ]},
    # K2 les jauges du vaisseau : mémoire, disque, entrepôt, charge
    "ct2": {"titre": "hist.ct2.titre", "skill": None, "steps": [
        _n("ct2", 0, cmd="free -h", re=r"^(free|cat\s+/proc/meminfo|vmstat)\b", outil="free", win=False, ou="controle"),
        _n("ct2", 1, cmd=C_("df -h .", "Get-PSDrive C"), re=r"^(df|get-psdrive|gdr)\b"),
        _n("ct2", 2, cmd=C_("du -sh entrepot/*", "Get-ChildItem entrepot | Select-Object Name, Length"),
           re=r"^(du\b|(get-childitem|gci|dir|ls)\b.*entrepot)", ou="controle"),
        _n("ct2", 3, cmd="controle entrepot ?", fs="ct_entrepot"),
        _n("ct2", 4, cmd="uptime", re=r"^uptime\b", outil="uptime", win=False),
        _n("ct2", 5, cmd="nproc", re=r"^(nproc|lscpu)\b", outil="nproc", win=False),
        _n("ct2", 6, cmd="controle jauges", re=CT + r"jauges?\b"),
    ]},
    # K3 le sac à dos : variables d'environnement, PATH, which, export, alias, source
    "ct3": {"titre": "hist.ct3.titre", "skill": None, "steps": [
        _n("ct3", 0, cmd="echo $HOME", re=r"^((echo|write-output)\s+.*\$(home|env:userprofile)\b|printenv\s+home\b)", ou="controle"),
        _n("ct3", 1, cmd=C_("echo $PATH | tr ':' '\\n'", "$env:PATH -split ';'"),
           re=r"(^echo\s+\"?\$PATH\b|^printenv\s+PATH\b|^\$env:path\b)"),
        _n("ct3", 2, cmd="controle path ?", fs="ct_path"),
        _n("ct3", 3, cmd=C_("which ls", "Get-Command ls"), re=r"^(which|command\s+-v|type|get-command|gcm)\s+\S"),
        _n("ct3", 4, cmd=C_("export COULEUR=bleu", "$env:COULEUR = 'bleu'"), re=r"^(export\s+[A-Za-z_]\w*=|\$env:\w+\s*=)"),
        _n("ct3", 5, cmd="bash -c 'echo $COULEUR'", re=r"^(bash|sh|zsh)\s+-c\b.*\$[A-Za-z_]", win=False),
        _n("ct3", 6, cmd="alias salut='echo Bonjour !'", re=r"^alias\s+[\w.-]+=", win=False),
        _n("ct3", 7, cmd=C_("cat sac_a_dos.sh", "type sac_a_dos.sh"), re=LIRE + r".*sac_a_dos", ou="controle"),
        _n("ct3", 8, cmd="source sac_a_dos.sh", re=r"^(source|\.)\s+(\./)?\S*sac_a_dos\.sh\s*$", ou="controle", win=False),
        _n("ct3", 9, cmd="echo $POSTE", re=r"^echo\s+.*\$\{?POSTE\b", win=False),
    ]},
    # K4 le carnet de bord : les journaux
    "ct4": {"titre": "hist.ct4.titre", "skill": None, "steps": [
        _n("ct4", 0, cmd="controle journal", fs="ct_journal", ou="controle"),
        _n("ct4", 1, cmd=C_("tail -n 5 carnet_de_bord.log", "Get-Content carnet_de_bord.log -Tail 5"),
           re=r"^(tail\b(?!.*-\w*f)|(get-content|gc)\b.*-tail)", ou="controle"),
        _n("ct4", 2, cmd=C_("grep -c ALERTE carnet_de_bord.log",
                            "(Select-String ALERTE carnet_de_bord.log).Count"),
           re=r"(^grep\b.*-\w*c.*alerte|^\(?(select-string|sls)\b.*alerte|alerte.*\|\s*wc\s+-l)", ou="controle"),
        _n("ct4", 3, cmd="controle alertes ?", fs="ct_alertes"),
        _n("ct4", 4, cmd=C_("tail -f carnet_de_bord.log", "Get-Content carnet_de_bord.log -Wait -Tail 3"),
           re=r"^(timeout\s+(-s\s+\w+\s+)?\d+\s+)?(tail\s+(-\w*\s+)*-\w*[fF]|(get-content|gc)\b.*-wait)", ou="controle", tout_code=True),
        _n("ct4", 5, cmd="journalctl --user -n 20 --no-pager", re=r"^journalctl\b", outil="journalctl", win=False,
           tout_code=True),
        _n("ct4", 6, cmd="dmesg | tail -3", re=r"^dmesg\b", outil="dmesg", win=False, tout_code=True),
    ]},
    # K5 les réveils : cron (un fichier du terrain que le jeu lit sans jamais le lancer)
    "ct5": {"titre": "hist.ct5.titre", "skill": None, "steps": [
        _n("ct5", 0, cmd="controle reveils", re=CT + r"r[eé]veils?\s*$", ou="controle"),
        _n("ct5", 1, cmd="crontab -l", re=r"^crontab\s+-l\b", outil="crontab", win=False, tout_code=True),
        _n("ct5", 2, cmd=C_("cat reveils.crontab", "type reveils.crontab"), re=LIRE + r".*reveils\.crontab", ou="controle"),
        _n("ct5", 3, cmd='controle cron "? ? ? ? ?"', fs="ct_cron"),
        _n("ct5", 4, cmd=C_('echo "*/15 * * * * echo RONDE >> ronde.log" >> reveils.crontab',
                            "Add-Content reveils.crontab '*/15 * * * * echo RONDE >> ronde.log'"),
           fs="ct_reveil", ou="controle"),
        _n("ct5", 5, cmd="controle reveils", re=CT + r"r[eé]veils?\s*$"),
    ]},
    # Linux de A à Z : distributions, installer (en VM d'abord), paquets, mises à jour, services, utilisateurs
    "ct6": {"titre": "hist.ct6.titre", "skill": None, "steps": [
        _n("ct6", 0, cmd=C_("cat /etc/os-release", "Get-CimInstance Win32_OperatingSystem | Select-Object Caption"),
           re=r"^(cat|less|more|head|tail|grep)\b.*/etc/(os|lsb)-release|win32_operatingsystem|^hostnamectl\b",
           outil=None if IS_WIN else "/etc/os-release", ou="controle"),
        _n("ct6", 1, cmd="controle distribution ?", fs="ct_distribution", outil=None if IS_WIN else "/etc/os-release"),
        _n("ct6", 2, cmd="controle familles", re=CT + r"familles?\s*$"),
        _n("ct6", 3, cmd="controle familles ? ? ? ? ?", fs="ct_familles"),
        _n("ct6", 4, cmd="controle installer", re=CT + r"install"),
        _n("ct6", 5, cmd="rpm -qa | wc -l", re=r"^rpm\s+-q", outil="rpm+/usr/lib/sysimage/rpm", win=False),
        _n("ct6", 6, cmd="dpkg -l | grep -c '^ii'", re=r"^dpkg(-query)?\s+-", outil="dpkg+/var/lib/dpkg/status", win=False),
        _n("ct6", 7, cmd="controle magasin", re=CT + r"magasin\b"),
        _n("ct6", 8, cmd=C_("systemctl list-units --type=service --state=running --no-pager | head -5",
                            "Get-Service | Where-Object Status -eq 'Running' | Select-Object -First 5"),
           re=r"^systemctl\s+(--user\s+)?(list-units|status|--type|-t\b)|^(get-service|gsv)\b",
           outil=None if IS_WIN else "systemctl", tout_code=True),
        _n("ct6", 9, cmd="controle services", re=CT + r"services?\b"),
        _n("ct6", 10, cmd=C_("cut -d: -f1 /etc/passwd | head -3", "Get-LocalUser | Select-Object Name"),
           re=r"/etc/passwd|^(get-localuser|getent\s+passwd)\b", outil=None if IS_WIN else "/etc/passwd"),
        _n("ct6", 11, cmd="controle useradd ?", fs="ct_equipage"),
        _n("ct6", 12, cmd=C_("tail -2 equipage.txt", "Get-Content equipage.txt -Tail 2"),
           re=LIRE + r".*equipage", ou="controle"),
    ]},
    # l'alerte : la vague de processus suspects (le veilleur, lui, est un habitant honnête)
    "ct7": {"titre": "hist.ct7.titre", "skill": None, "steps": [
        _n("ct7", 0, cmd="controle alerte", re=CT + r"alerte\b", ou="controle"),
        _n("ct7", 1, cmd=C_("ps aux | grep fictif", "controle ps"),
           re=r"^(ps\b.*\|\s*grep\b.*fictif|pgrep\b.*fictif)|" + CT + r"ps\b"),
        _n("ct7", 2, cmd=C_("kill ?", "controle arrete ?"), fs="ct_arretes"),
        _n("ct7", 3, cmd="controle tableau", fs="ct_tableau"),
    ]},
}
CHAPITRE = {"id": "controle", "n": 22, "piece": "controle", "famille": "Constructs", "monde": True,
            "lecons": [f"ct{i}" for i in range(8)], "objet": "pupitre", "titre": "admin_du_poste"}


# ================================================================ l'arbre du Carrefour : quand le Poste s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "controle"), {})


def _besoin():
    from . import programme
    P = programme.donnees()
    m = _monde()
    chaps = []
    for n in m.get("requis", []):
        chaps += [c for c in P.get("tronc", {}).get(n, []) if c not in chaps]
    return chaps, list(m.get("requis_lecons", []))


def ouvert(state):
    from . import histoire
    chaps, lecs = _besoin()
    if not chaps and not lecs:
        return False
    faits = histoire.h_(state)["faits"]
    return all(histoire.fini(state, c) for c in chaps) and all(l in faits for l in lecs)


def manque(state):
    from . import histoire, lecons
    chaps, lecs = _besoin()
    faits = histoire.h_(state)["faits"]
    out = [histoire.nom_chapitre(c) for c in chaps if not histoire.fini(state, c)]
    for l in lecs:
        if l not in faits:
            ch = histoire.chapitre_de_lecon(l)
            out.append(f"{lecons.tx(histoire.lecon_def(l)['titre'])} ({histoire.nom_chapitre(ch['id']) if ch else '?'})")
    return out


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "controle" in deja or histoire.fini(state, "controle") or not ouvert(state):
        return False
    deja.append("controle")
    core.log(state, t("ct.ouvert.log"))
    core.say(state, histoire.dire(state, "ct.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s|\")(\?|…|<[^>]*>)(\s|$|\")")
REPONSES = {"controle entrepot ?": "entrepot", "controle path ?": "path", "controle alertes ?": "alertes",
            'controle cron "? ? ? ? ?"': "cron", "controle distribution ?": "distribution",
            "controle familles ? ? ? ? ?": "familles", "controle useradd ?": "useradd"}
SUDO = re.compile(r"(^|[;&|]\s*)sudo\b")
CHANGE = re.compile(r"(^|[;&|]\s*)(sudo\s+)?((dnf|yum|apt|apt-get|zypper|pacman|snap|flatpak|brew)\s+(install|remove|erase|"
                    r"upgrade|update|dist-upgrade|-S\w*|-R\w*|-U\w*)\b|systemctl\s+(--user\s+)?(start|stop|restart|reload|"
                    r"enable|disable|mask|kill|poweroff|reboot)\b|(useradd|userdel|usermod|adduser|deluser|passwd|groupadd)\b|"
                    r"crontab\s+(-e|-r)\b|(shutdown|reboot|poweroff|halt)\b|(stop-service|restart-service|set-service|"
                    r"new-localuser|remove-localuser)\b)", re.I)
KILL = re.compile(r"(^|[;&|]\s*)(sudo\s+)?(kill|pkill|killall|stop-process|spps|taskkill)\b(.*)", re.I)


def kill_etrangers(ligne):
    """Ce qu'un `kill` viserait en dehors du jeu : « large » (kill -1, kill 1, killall X, pkill X sans « fictif »), les
    numéros qui ne sont pas des processus lancés par le jeu (ni %1 : les tâches du terminal), ou [] (rien d'étranger)."""
    m = KILL.search((ligne or "").strip())
    if not m:
        return []
    cmd, reste = m.group(3).lower(), m.group(4)
    if cmd in ("pkill", "killall", "taskkill", "stop-process", "spps"):
        return [] if "fictif" in reste else ["large"]
    if re.search(r"(^|\s)(-1|0|1)(\s|$)", reste):
        return ["large"]
    nums = [int(x) for x in re.findall(r"(?<![%\w-])(\d+)\b", reste)]
    a_nous = pids_a_nous()
    return [n for n in nums if n not in a_nous]


def indice(step, tapees):
    """Un indice du Poste : un sudo, une commande qui changerait la vraie machine, un « ? » recopié, une mauvaise
    réponse, un cron sans guillemets (bash a remplacé les * par des noms de fichiers), le veilleur arrêté, un kill d'un
    numéro qui n'est pas au jeu."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(SUDO.search(l) for l in lignes):
        return t("ct.indice.sudo")
    if any(CHANGE.search(l) for l in lignes):
        return t("ct.indice.adulte")
    if "?" in cmd.replace('"', " ").split() and any(TROU.search(l) for l in lignes if re.match(CT, l) or l.startswith("kill")):
        return t("ct.indice.trou")
    if cmd.startswith("controle cron") and any(re.match(CT + r"cron\s+[^\"']", l) for l in lignes):
        return t("ct.indice.guillemets")
    et = REPONSES.get(cmd)
    if et:
        der = dernier(et)
        if der and not der.endswith("(ok)"):
            if et == "cron" and der.endswith("(etoiles)"):
                return t("ct.indice.guillemets")
            return t("ct.indice.rep." + et)
    if cmd.startswith(("export", "$env:")) and any(re.match(r"^export\s+\w+(\s+=|=\s)", l) for l in lignes):
        return t("ct.indice.export_espaces")
    if cmd.startswith("source") and any(re.match(r"^(bash|sh|zsh|\./)\s*\S*sac_a_dos", l) for l in lignes):
        return t("ct.indice.source")
    if step.get("fs") in ("ct_arretes", "ct_tableau"):
        if not veilleur_vivant() and dans_registre("vague", "lancee"):
            return t("ct.indice.veilleur")
        if any(kill_etrangers(l) for l in lignes):
            return t("ct.indice.pas_a_nous")
        if suspects_vivants():
            return t("ct.indice.encore", n=len(suspects_vivants()))
    if step.get("fs") == "ct_reveil" and any(l.startswith(("echo", "add-content")) and ">" not in l and "reveils" not in l
                                             for l in lignes):
        return t("ct.indice.ajoute")
    return None


def _lecon(state):
    from . import histoire
    les, _e = histoire.lecon_courante(state)
    return les["id"] if les else None


def surveiller(state, lignes):
    """À chaque tour : un sudo, une commande qui changerait la vraie machine (installer, arrêter un service, créer un
    utilisateur, poser un vrai cron, éteindre) : la créature rappelle la règle (une fois chacune) ; un kill qui vise
    un numéro qui n'est pas au jeu : à CHAQUE fois (sur sa vraie machine, on n'arrête pas un inconnu)."""
    if not dossier().is_dir():
        return False
    c = c_(state)
    for l in lignes or []:
        l = (l or "").strip()
        k = kill_etrangers(l)
        if k == ["large"]:
            msg = t("ct.garde.kill_large")
        elif k and _lecon(state) == "ct7":
            msg = t("ct.garde.kill")
        elif SUDO.search(l) and not _fait(c, "garde:sudo"):
            msg = t("ct.indice.sudo")
        elif CHANGE.search(l) and not _fait(c, "garde:change"):
            msg = t("ct.garde.adulte")
        else:
            continue
        core.say(state, msg, 16)
        core.terminal(state, "⚠ " + msg)
        return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


POSTE = ['   ┌──────────────────────────────┐', '   │ ▮▮▮▯ ▮▮▯▯ ▮▯▯▯   ◉ ◉ ◉   ⏰  │',
         '   │  ╭──╮ ╭──╮ ╭──╮   ▤▤▤▤▤▤     │', '   │  │◐ │ │◓ │ │◑ │   📟 📟      │',
         '  ▁┴──┴──┴─┴──┴─┴──┴──────────────┴▁']


def banniere(largeur=None):
    """L'entrée du Poste : l'illustration (illustrations.bin, « controle ») si elle existe, sinon le REPLI dessiné en
    caractères (le pupitre, ses jauges, ses voyants et son réveil)."""
    try:
        from . import scenes
        if scenes.disponible("controle"):
            return scenes.illustration("controle", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [117, 78, 229, 215, 141]
    return [f"  {_c(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(POSTE)]


def aide():
    return banniere() + [f" {_c(117)}{BOLD}📟 " + t("ct.aide.titre") + RESET] + ["  " + l for l in t("ct.aide.liste").split("\n")]


def bloc(cle, **k):
    return ["  " + l for l in t(cle, **k).split("\n")]


def lignes_habitants():
    e = etats_processus()
    out = [f" {_c(141)}{BOLD}👻 " + t("ct.habitants.titre") + RESET, ""]
    if e:
        travail = e.get("R", 0)
        dort = e.get("S", 0) + e.get("I", 0) + e.get("D", 0)
        autres = sum(e.values()) - travail - dort
        out += [f"  {_c(78)}🏃 {travail:>4}{RESET}  " + t("ct.habitants.travaillent"),
                f"  {_c(117)}😴 {dort:>4}{RESET}  " + t("ct.habitants.dorment")]
        if autres:
            out.append(f"  {_c(203)}👻 {autres:>4}{RESET}  " + t("ct.habitants.autres"))
        out += ["", "  " + t("ct.habitants.total", n=sum(e.values()))]
    else:
        out.append("  " + t("ct.habitants.raconte"))
    out += [""] + bloc("ct.habitants.texte")
    noter("habitants", "vus (ok)")
    return out


def lignes_entrepot(state, arg):
    gr = _graine(state)
    if not arg:
        return [t("ct.entrepot.aide")]
    if caisse_ok(arg, gr):
        noter("entrepot", f"{caisse_lourde(gr)} (ok)")
        kio = dict(caisses(gr))[caisse_lourde(gr)]
        return [f" {_c(78)}✔ " + t("ct.entrepot.ok", caisse=caisse_lourde(gr), kio=kio) + RESET, "  " + t("ct.entrepot.morale")]
    noter("entrepot", f"{ascii_bas(arg)[:30]} (faux)")
    return [f" {_c(203)}✖ " + t("ct.indice.rep.entrepot") + RESET]


def lignes_jauges():
    out = [f" {_c(117)}{BOLD}🎛 " + t("ct.jauges.titre") + RESET, ""]
    m = memoire()
    if m:
        p = pourcentage(*m)
        out.append(f"  🥫 {t('ct.jauge.memoire'):<14} {_c(78 if p < 80 else 203)}{jauge(p)}{RESET} {p:>3} %  "
                   f"{DIM}({m[0] // 1024} / {m[1] // 1024} Mio){RESET}")
    d = disque()
    if d:
        p = pourcentage(*d)
        out.append(f"  📦 {t('ct.jauge.disque'):<14} {_c(78 if p < 90 else 203)}{jauge(p)}{RESET} {p:>3} %  "
                   f"{DIM}({d[0] // 1024 ** 3} / {d[1] // 1024 ** 3} Gio){RESET}")
    c = charge()
    if c:
        p = min(100, pourcentage(int(c[0] * 100), c[1] * 100))
        out.append(f"  💨 {t('ct.jauge.charge'):<14} {_c(78 if p < 100 else 203)}{jauge(p)}{RESET} {p:>3} %  "
                   f"{DIM}({c[0]:.2f} / {c[1]}){RESET}")
    if len(out) == 2:
        out.append("  " + t("ct.jauges.raconte"))
    out += [""] + bloc("ct.jauges.texte")
    noter("jauges", "vues (ok)")
    return out


def lignes_path(arg):
    p = path_actuel()
    if not arg:
        return [t("ct.path.aide")]
    if path_ok(arg, p, IS_WIN):
        noter("path", f"{arg.strip()} (ok)")
        return [f" {_c(78)}✔ " + t("ct.path.ok", n=arg.strip()) + RESET, "  " + t("ct.path.morale")]
    noter("path", f"{ascii_bas(arg)[:10]} (faux)")
    return [f" {_c(203)}✖ " + t("ct.indice.rep.path") + RESET]


def lignes_journal(state):
    lignes = journal_lignes(_graine(state))
    _ecrire("controle/carnet_de_bord.log", "\n".join(lignes) + "\n")
    noter("journal", "pose (ok)")
    return [f" {_c(229)}{BOLD}📓 " + t("ct.journal.titre") + RESET, ""] + bloc("ct.journal.texte", n=len(lignes))


def lignes_alertes(state, arg):
    n = nb_alertes(_graine(state))
    if not (dossier() / "carnet_de_bord.log").is_file():
        return [t("ct.alertes.sans_journal")]
    if not arg:
        return [t("ct.alertes.aide")]
    if arg.strip() == str(n):
        noter("alertes", f"{n} (ok)")
        return [f" {_c(78)}✔ " + t("ct.alertes.ok", n=n) + RESET, "  " + t("ct.alertes.morale")]
    noter("alertes", f"{ascii_bas(arg)[:10]} (faux)")
    return [f" {_c(203)}✖ " + t("ct.indice.rep.alertes") + RESET]


REVEIL = ["    ⏰", "  ╭─┴─╮", "  │ 7 │", "  ╰───╯"]


def lignes_reveils():
    out = [f" {_c(215)}{BOLD}⏰ " + t("ct.reveils.titre") + RESET, ""]
    out.append(f"  {BOLD}┌──────── minute (0-59){RESET}")
    out.append(f"  {BOLD}│ ┌────── heure (0-23){RESET}")
    out.append(f"  {BOLD}│ │ ┌──── " + t("ct.cron.jour") + f" (1-31){RESET}")
    out.append(f"  {BOLD}│ │ │ ┌── " + t("ct.cron.mois") + f" (1-12){RESET}")
    out.append(f"  {BOLD}│ │ │ │ ┌ " + t("ct.cron.semaine") + f" (0-7, 0 = 7 = " + t("ct.cron.dimanche") + f"){RESET}")
    out.append(f"  {_c(215)}30 7 * * 1-5{RESET}  echo REVEIL >> reveil.log")
    out += [""] + bloc("ct.reveils.texte")
    txt = _lire("controle/reveils.crontab")
    if txt is not None:
        out += ["", f" {_c(117)}{BOLD}📄 reveils.crontab{RESET}"]
        maintenant = datetime.datetime.now()
        for l, ok in lignes_crontab(txt):
            if ok:
                p = prochaine(l, maintenant)
                quand = p.strftime("%Y-%m-%d %H:%M") if p else "—"
                out.append(f"  {_c(78)}✔{RESET} {l}  {DIM}→ " + t("ct.reveils.prochaine", quand=quand) + RESET)
            else:
                out.append(f"  {_c(203)}✖{RESET} {l}  {DIM}→ " + t("ct.reveils.fausse") + RESET)
        out.append(f"  {DIM}" + t("ct.reveils.jamais_lance") + RESET)
    noter("reveils", "vus (ok)")
    return out


def lignes_cron(state, reste):
    s = cron_situation(_graine(state))
    if not reste:
        return [f" {_c(215)}⏰ " + t("ct.cron.question", situation=t("ct.cron.s." + s["id"])) + RESET, "  " + t("ct.cron.aide")]
    arg = " ".join(reste)
    if len(reste) > 1 and any(os.path.exists(x) for x in reste) and "*" not in arg:
        noter("cron", f"{arg[:40]} (etoiles)")         # bash a remplacé les * par les noms des fichiers d'ici
        return [f" {_c(203)}✖ " + t("ct.indice.guillemets") + RESET]
    if cron_ok(arg, _graine(state)):
        noter("cron", f"{' '.join(arg.split())} (ok)")
        return [f" {_c(78)}✔ " + t("ct.cron.ok", ligne=s["rep"], situation=t("ct.cron.s." + s["id"])) + RESET,
                "  " + t("ct.cron.morale")]
    noter("cron", f"{arg[:40]} (faux)")
    out = [f" {_c(203)}✖ " + t("ct.indice.rep.cron") + RESET]
    if cron(arg) is None:
        out.append("  " + t("ct.cron.cinq"))
    return out


def lignes_distribution(arg):
    osr = os_release()
    if IS_WIN:
        osr = {"ID": "windows", "NAME": "Windows"}
    if not arg:
        return [t("ct.distribution.aide")]
    if distribution_ok(arg, osr):
        noter("distribution", f"{osr.get('ID', '?')} (ok)")
        return [f" {_c(78)}✔ " + t("ct.distribution.ok", nom=osr.get("PRETTY_NAME") or osr.get("NAME") or osr.get("ID")) + RESET,
                "  " + t("ct.distribution.morale")]
    noter("distribution", f"{ascii_bas(arg)[:20]} (faux)")
    return [f" {_c(203)}✖ " + t("ct.indice.rep.distribution") + RESET]


def lignes_familles(state, rep):
    c = familles_cartes(_graine(state))
    noms = {x["id"]: x["nom"] for x in donnees()["familles"]["distributions"]}
    if not rep:
        out = [f" {_c(117)}{BOLD}🌳 " + t("ct.familles.titre") + RESET, ""]
        out += ["  " + l for l in t("ct.familles.lettres").split("\n")] + [""]
        out += [f"  {n}. {noms[i]}" for n, i, _r in c]
        return out + ["", "  " + t("ct.familles.aide")]
    bon, justes = quiz_justes(c, rep, donnees()["familles"]["lettres"])
    if not bon:
        return [t("ct.familles.aide")]
    out = []
    if len(justes) == len(c):
        noter("familles", " ".join(rep) + " (ok)")
        out += [f" {_c(78)}✔ " + t("ct.familles.ok") + RESET, "  " + t("ct.familles.morale")]
    else:
        noter("familles", " ".join(rep) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("ct.quiz.faux", n=len(justes), total=len(c)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. {noms[i]} : " + t("ct.famille." + next(r for _n, i2, r in c if i2 == i)))
    return out


def lignes_installer():
    out = [f" {_c(78)}{BOLD}💿 " + t("ct.installer.titre") + RESET, ""] + bloc("ct.installer.texte")
    noter("installer", "lu (ok)")
    return out


def lignes_magasin():
    m, n = magasin()
    out = [f" {_c(229)}{BOLD}🏪 " + t("ct.magasin.titre") + RESET, ""]
    if m:
        out.append("  " + t("ct.magasin.le_tien", magasin=m["id"]))
        if n is not None:
            out.append(f"  {_c(78)}📦 {n}{RESET} " + t("ct.magasin.paquets"))
        out += ["", f"  {DIM}" + t("ct.magasin.compter") + RESET, f"    {_c(117)}{m['compte']}{RESET}"]
        out += ["", "  " + t("ct.magasin.adulte"), f"    {DIM}{m['installer']}{RESET}", f"    {DIM}{m['maj']}{RESET}"]
    else:
        out.append("  " + t("ct.magasin.raconte"))
    out += [""] + bloc("ct.magasin.texte")
    noter("magasin", (m["id"] if m else "raconte") + " (ok)")
    return out


def lignes_services():
    n = services_actifs()
    out = [f" {_c(141)}{BOLD}🛡 " + t("ct.services.titre") + RESET, ""]
    if n is not None:
        out.append(f"  {_c(78)}🟢 {n}{RESET} " + t("ct.services.actifs"))
    else:
        out.append("  " + t("ct.services.raconte"))
    out += [""] + bloc("ct.services.texte")
    noter("services", "lus (ok)")
    return out


def lignes_useradd(arg):
    if not arg:
        return [t("ct.useradd.aide")]
    nom = arg.strip()
    txt = _lire("controle/equipage.txt")
    if txt is None:
        txt = equipage_texte()
    if not nom_valide(nom):
        noter("useradd", f"{ascii_bas(nom)[:16]} (invalide)")
        return [f" {_c(203)}✖ " + t("ct.indice.rep.useradd") + RESET]
    nouveau, uid = equipage_ajoute(txt, nom)
    if uid is None:
        noter("useradd", f"{nom} (deja)")
        return [f" {_c(215)}✖ " + t("ct.useradd.deja", nom=nom) + RESET]
    _ecrire("controle/equipage.txt", nouveau)
    noter("useradd", f"{nom} {uid} (ok)")
    return [f" {_c(78)}✔ " + t("ct.useradd.ok", nom=nom, uid=uid) + RESET, f"  {_c(117)}{nouveau.splitlines()[-1]}{RESET}", ""] + \
        bloc("ct.useradd.texte")


def lignes_ps(state):
    viv = vivants(state)
    out = [f"{'USER':<10} {'PID':>7} {'%CPU':>5}  COMMAND"]
    for pid, nom in viv:
        out.append(f"{'equipage':<10} {pid:>7} {'0.0':>5}  {nom} {donnees()['vague']['secondes']}")
    if not viv:
        out.append(f"  {DIM}" + t("ct.ps.aucun") + RESET)
    if simulee():
        out.append(f"  {DIM}" + t("ct.ps.simule") + RESET)
    return out


def lignes_alerte(state):
    """La vague (une à la fois) : 3 suspects tirés et le veilleur, de vrais `sleep` renommés sur PC (simulés sous
    Windows) ; le carnet de bord dit qui fait quoi."""
    c = c_(state)
    gr = _graine(state)
    if vivants(state) and suspects_vivants(state) and veilleur_vivant(state):
        noms = vague_suspects(gr, c["vague"])
        out = [f" {_c(203)}{BOLD}🚨 " + t("ct.alerte.encore") + RESET, ""]
    else:
        arreter_tout()
        c["vague"] += 1
        c["arretes"] = []
        noms = vague_suspects(gr, c["vague"])
        lancer(noms + [donnees()["vague"]["veilleur"]])
        out = [f" {_c(203)}{BOLD}🚨 " + t("ct.alerte.titre", n=c["vague"]) + RESET, ""]
        quand = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(dossier() / "carnet_de_bord.log", "a", encoding="utf-8") as f:
                for nom in noms:
                    f.write(f"{quand} ALERTE {nom} : {t('ct.suspect.' + nom)}\n")
                f.write(f"{quand} INFO {donnees()['vague']['veilleur']} : {t('ct.veilleur.journal')}\n")
        except OSError:
            pass
        noter("vague", f"{c['vague']} (lancee)")
    for nom in noms:
        out.append(f"  {_c(203)}⚠ {nom}{RESET} : " + t("ct.suspect." + nom))
    out.append(f"  {_c(78)}🛡 {donnees()['vague']['veilleur']}{RESET} : " + t("ct.veilleur.texte"))
    out += [""] + bloc("ct.alerte.texte" if not simulee() else "ct.alerte.simulee")
    return out


def lignes_arrete(state, arg):
    try:
        pid = int((arg or "").strip())
    except ValueError:
        return [t("ct.arrete.aide")]
    nom = arreter(state, pid)
    if not nom:
        return [f" {_c(203)}✖ " + t("ct.arrete.inconnu", pid=pid) + RESET]
    if nom == donnees()["vague"]["veilleur"]:
        return [f" {_c(203)}✖ " + t("ct.indice.veilleur") + RESET]
    reste = len(suspects_vivants(state))
    return [f" {_c(78)}✔ " + t("ct.arrete.ok", nom=nom, pid=pid) + RESET] + \
        (["  " + t("ct.indice.encore", n=reste)] if reste else ["  " + t("ct.arrete.tous")])


def lignes_tableau(state):
    c = c_(state)
    if not c["vague"] or not dans_registre("vague", "lancee"):
        return [t("ct.tableau.pas_de_vague")]
    sv, vv = suspects_vivants(state), veilleur_vivant(state)
    b = bilan_vague(sv, vv)
    out = [f" {_c(117)}{BOLD}🎛 " + t("ct.tableau.titre", n=c["vague"]) + RESET, ""]
    out.append(f"  {(_c(78) + '✔') if not sv else (_c(203) + '✖')}{RESET} " + t("ct.tableau.suspects", n=len(sv)))
    out.append(f"  {(_c(78) + '✔') if vv else (_c(203) + '✖')}{RESET} " + t("ct.tableau.veilleur." + ("oui" if vv else "non")))
    out.append("")
    if b == "gagne":
        if not dans_registre("tableau", "gagne") or not dernier("tableau").startswith(f"[tableau] {c['vague']} "):
            noter("tableau", f"{c['vague']} (gagne)")
        out.append(f"  {_c(78)}" + t("ct.tableau.gagne") + RESET)
        from . import recompenses                       # l'exploit (§ 7.6) : tous les suspects d'une vague, veilleur épargné
        msg = recompenses.exploit(state, "controle.vague")
        if msg:
            core.log(state, msg)
            core.say(state, msg, 16)
            out.append(" " + msg)
    elif b == "veilleur":
        noter("tableau", f"{c['vague']} (veilleur)")
        out.append(f"  {_c(203)}" + t("ct.indice.veilleur") + RESET)
    else:
        out.append("  " + t("ct.indice.encore", n=len(sv)))
    return out


def commande(args, sortie=None):
    """tg controle [consignes|habitants|entrepot NOM|jauges|path N|journal|alertes N|reveils|cron "M H J M S"|
    distribution NOM|familles …|installer|magasin|services|useradd NOM|equipage|alerte|ps|arrete PID|tableau|stop]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide")).replace("-", "_")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        c_(st)
        arg = " ".join(reste) if reste else None
        if sous in ("consignes", "regles", "porte"):
            lignes.extend(banniere() + t("ct.meuble.consignes", nom=st.get("name", "")).split("\n"))
        elif sous in ("habitants", "habitant"):
            lignes.extend(lignes_habitants())
        elif sous in ("entrepot", "caisse"):
            lignes.extend(lignes_entrepot(st, arg))
        elif sous in ("jauges", "jauge"):
            lignes.extend(lignes_jauges())
        elif sous in ("path", "carnet", "adresses"):
            lignes.extend(lignes_path(arg))
        elif sous == "journal":
            lignes.extend(lignes_journal(st))
        elif sous in ("alertes",):
            lignes.extend(lignes_alertes(st, arg))
        elif sous in ("reveils", "reveil"):
            lignes.extend(lignes_reveils())
        elif sous == "cron":
            lignes.extend(lignes_cron(st, a[1:]))
        elif sous in ("distribution", "distrib"):
            lignes.extend(lignes_distribution(arg))
        elif sous in ("familles", "famille"):
            lignes.extend(lignes_familles(st, reste))
        elif sous in ("installer", "installation", "install"):
            lignes.extend(lignes_installer())
        elif sous in ("magasin", "paquets"):
            lignes.extend(lignes_magasin())
        elif sous in ("services", "service"):
            lignes.extend(lignes_services())
        elif sous == "useradd":
            lignes.extend(lignes_useradd(arg))
        elif sous == "equipage":
            lignes.extend([f" {_c(117)}{BOLD}🧑‍🚀 equipage.txt{RESET}"] + ["  " + l for l in (_lire("controle/equipage.txt") or "").splitlines()])
        elif sous == "alerte":
            lignes.extend(lignes_alerte(st))
        elif sous == "ps":
            lignes.extend(lignes_ps(st))
        elif sous in ("arrete", "arreter", "kill"):
            lignes.extend(lignes_arrete(st, arg))
        elif sous == "tableau":
            lignes.extend(lignes_tableau(st))
        elif sous == "stop":                       # tout éteindre (les processus du jeu seulement)
            arreter_tout()
            lignes.append(t("ct.stop"))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
