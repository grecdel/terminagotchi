"""Dressage : pour gagner la confiance d'une bestiole sauvage, il faut réussir une suite de
vraies commandes avant la fin du temps imparti.

Le jeu vérifie le RÉSULTAT (le dossier existe, le fichier est trié, la bonne réponse a été
donnée avec echo…), pas le texte exact : chacun s'y prend comme il veut. Chercher dans le
lexique est permis ; le copier-coller, non (il ne compte pas).

Déroulé : on trouve la bestiole (ls -a), on la lit (cat) → le dressage commence.
Le premier dressage de chaque famille se fait sans chrono : c'est une leçon.

Difficulté progressive (selon le nombre de bestioles déjà dressées, voir plafond()) :
  - le tout premier dressage : 2 épreuves simples (lire sa fiche, puis une commande d'un seul mot
    ou presque : pas de boucle for, pas de guillemets imbriqués, pas de tuyau) ;
  - puis le nombre d'épreuves et leur niveau montent peu à peu, jusqu'aux règles normales
    (selon la rareté de l'individu) à partir de 12 bestioles dressées.
Quand une épreuve est PRESQUE réussie (faute de frappe, fichier au mauvais endroit, script sans
echo, boucle for sans « ; »…), une bulle donne un indice clair (voir indice()).
Si tu as déjà une troupe, un mini-combat a lieu d'abord (voir combat.py).
"""
import hashlib
import base64
import os
import random
import re
import stat
import textwrap
import time
from datetime import date

from . import bestiaire as B
from . import combat
from . import core
from .langue import ajuster, au_hasard, envelopper, largeur, liste, t
from .mots import palier, terme, termes
from .plateforme import IS_WIN

T = core.TERRAIN
# la difficulté dépend de la rareté de L'INDIVIDU (ses stats, sa variante…), pas de l'espèce
DUREE = {"commune": 90, "peu commune": 120, "rare": 180, "épique": 210, "légendaire": 240, "mythique": 300}
NB_TACHES = {"commune": 2, "peu commune": 3, "rare": 4, "épique": 5, "légendaire": 6, "mythique": 7}
NIVEAU_MAX = {"commune": 1, "peu commune": 2, "rare": 3, "épique": 3, "légendaire": 3, "mythique": 3}
ULTIMES = ("légendaire", "mythique")
LECTURE = {"cat", "less", "more", "head", "tail", "type", "get-content", "bat", "nano", "vim", "vi"}

MOTS = ["octet", "pixel", "bug", "shell", "noyau", "cache", "paquet", "script", "fichier", "chat",
        "nuage", "clef", "boucle", "signal", "tuyau", "racine"]


# ================================================================ outils de vérification

def nom_fichier(nom):
    """Le nom d'une bestiole tel qu'il apparaît dans les fichiers : minuscules, sans accents
    (« Étincelot » → « etincelot »). Le même partout : fiche, repaire, renommage, exemples."""
    return B._simple(nom)


def a_tape(lignes, motif):
    r = re.compile(motif, re.I)
    return any(r.search(l) for l in lignes)


def a_repondu(lignes, reponse):
    """Réponse donnée avec echo (ou Write-Output) : echo 42, echo "42"…"""
    r = re.compile(r"^\s*(echo|write-output|write-host)\s+[\"']?" + re.escape(str(reponse)) + r"[\"']?\s*$", re.I)
    return any(r.match(l) for l in lignes)


def lire(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def lignes_de(p):
    t = lire(p)
    return None if t is None else [l.rstrip("\r") for l in t.splitlines() if l.strip()]


# ================================================================ les épreuves, par famille
# Chaque épreuve : id, niveau (1 à 3), but (ce que la bestiole demande), indice (la commande à
# chercher dans le lexique), posix (si elle n'existe pas sous Windows), prep (fichiers à poser),
# ok (vérification). Les fonctions reçoivent le contexte c : c["d"] = dossier de la zone,
# c["nom"] = nom de la bestiole, c["x"] = données tirées au hasard.

def _enclos(c, l): return (c["d"] / "enclos").is_dir()
def _gamelle(c, l): return (c["d"] / "enclos" / "gamelle").exists()


def _prep_doudou(c):
    (c["d"] / "doudou.txt").write_text(t("dress.fichier.doudou", nom=c["nom"]) + "\n", encoding="utf-8")


def _doudou(c, l): return (c["d"] / "doudou.txt").exists() and (c["d"] / "enclos" / "doudou.txt").exists()


def _prep_vieux(c):
    (c["d"] / "vieux_nom.txt").write_text(t("dress.fichier.renomme") + "\n", encoding="utf-8")


def _renomme(c, l):
    return not (c["d"] / "vieux_nom.txt").exists() and (c["d"] / f"{nom_fichier(c['nom'])}.txt").exists()


def _archive(c, l):
    return any((c["d"] / n).exists() for n in ("enclos.tar.gz", "enclos.tgz", "enclos.tar", "enclos.zip"))


def _prep_sac(c):
    n = random.randint(4, 9)
    sac = c["d"] / "sac"
    sac.mkdir(exist_ok=True)
    for i in range(n):
        (sac / f"objet_{i + 1}").write_text("…", encoding="utf-8")
    c["x"]["sac"] = n


def _prep_lignes(nom, n_min=8, n_max=15, doublons=True):
    def prep(c):
        mots = random.sample(MOTS, k=6)
        lignes = [random.choice(mots) for _ in range(random.randint(n_min, n_max))] if doublons else \
            random.sample(MOTS, k=random.randint(5, 9))
        (c["d"] / nom).write_text("\n".join(lignes) + "\n", encoding="utf-8")
        c["x"][nom] = lignes
    return prep


def _prep_bug(c):
    n = random.randint(2, 5)
    lignes = ["INFO " + t("dress.fichier.bug.info", i=i) for i in range(6)] + \
             ["ERROR " + t("dress.fichier.bug.erreur", i=i) for i in range(n)]
    random.shuffle(lignes)
    (c["d"] / "bug.log").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    c["x"]["bug"] = n


def _corrige(c, l):
    t = lignes_de(c["d"] / "corrige.log")
    return t is not None and len(t) > 0 and not any("ERROR" in x for x in t)


def _prep_collier(c):
    mot = random.choice(MOTS) + str(random.randint(10, 99))
    (c["d"] / "collier.txt").write_text(mot, encoding="utf-8")
    c["x"]["empreinte"] = hashlib.sha256(mot.encode()).hexdigest()[:8]


def _empreinte(c, l):
    r = re.compile(r"^\s*(echo|write-output)\s+[\"']?([0-9a-f]{8,64})[\"']?\s*$", re.I)
    return any((m := r.match(x)) and m.group(2).lower().startswith(c["x"]["empreinte"]) for x in l)


def _prep_message(c):
    mot = random.choice(MOTS)
    (c["d"] / "message.b64").write_text(base64.b64encode(mot.encode()).decode() + "\n", encoding="utf-8")
    c["x"]["secret"] = mot


def _prep_corrompu(c):
    phrase = random.choice(liste("dress.fichier.corrompu"))
    (c["d"] / "corrompu.txt").write_text(phrase[::-1] + "\n", encoding="utf-8")
    c["x"]["phrase"] = phrase


def _repare(c, l):
    t = lire(c["d"] / "repare.txt")
    return t is not None and t.strip() == c["x"]["phrase"]


def _prep_cri(c):
    # tr A-Z a-z ne connaît que les lettres latines sans accent : ces phrases restent en MAJUSCULES ASCII
    phrase = random.choice([x for x in liste("dress.fichier.cri") if x.isascii()] or ["JE VEUX JOUER"])
    (c["d"] / "cri.txt").write_text(phrase + "\n", encoding="utf-8")
    c["x"]["cri"] = phrase


def _minuscules(c, l):
    t = lire(c["d"] / "chuchote.txt")
    return t is not None and t.strip() == c["x"]["cri"].lower()


def _prep_scores(c):
    s = random.sample(range(100, 9999), k=8)
    (c["d"] / "scores.txt").write_text("\n".join(map(str, s)) + "\n", encoding="utf-8")
    c["x"]["scores"] = s


def _top3(c, l):
    t = lignes_de(c["d"] / "top3.txt")
    return t is not None and [x.strip() for x in t] == [str(v) for v in sorted(c["x"]["scores"], reverse=True)[:3]]


def _trie(c, l):
    t = lignes_de(c["d"] / "trie.txt")
    return t is not None and t == sorted(c["x"]["croquettes.txt"])


def _cage_privee(c, l):
    p = c["d"] / "enclos" / "cage"
    if not p.exists():
        return False
    if IS_WIN:
        return not os.access(p, os.W_OK)            # attrib +r : lecture seule
    return p.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0


def _chant(c, l):
    t = lire(c["d"] / "chant.txt")
    return t is not None and nom_fichier(c["nom"]) in B._simple(t)


def _compte(c, l):
    t = lignes_de(c["d"] / "compte.txt")
    return t is not None and [x.strip() for x in t] == ["1", "2", "3", "4", "5"]


def _script(c, l):
    p = c["d"] / ("tour.ps1" if IS_WIN else "tour.sh")
    t = lire(p)
    if t is None or "echo" not in t.lower() and "write-" not in t.lower():
        return False
    return IS_WIN or os.access(p, os.X_OK)


def _photos(c, l):
    d = c["d"] / "nuage"
    return d.is_dir() and len(list(d.glob("photo*"))) >= 3


def _nuage_copie(c, l):
    d = c["d"] / "nuage_copie"
    return d.is_dir() and len(list(d.glob("photo*"))) >= 3


def _page(c, l):
    """La page est téléchargée ; sans Internet (G-08), l'essai `curl -o page.html …` suffit : le jeu pose une page
    locale à la place, jamais d'épreuve impossible."""
    p = c["d"] / "page.html"
    if p.exists() and p.stat().st_size > 0:
        return True
    if not a_tape(l, r"^\s*curl(\.exe)?\b.*-o\s*\S*page\.html"):
        return False
    from . import histoire
    try:
        p.write_text(histoire.page_secours(t("hist.colis.titre"), t("hist.colis.texte", nom=c["nom"])), encoding="utf-8")
    except OSError:
        pass
    return True


def _cachette(c, l): return any(p.name.startswith(".") and p.is_file() for p in (c["d"] / "enclos").glob(".*")) \
    if (c["d"] / "enclos").is_dir() else False


E = lambda i, n, but, indice, ok, prep=None, posix=False: \
    {"id": i, "niveau": n, "but": but, "indice": indice, "ok": ok, "prep": prep, "posix": posix}

EPREUVES = {
    "Rencontre": [
        E("examiner", 1, "ep.rencontre.examiner", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|less|more|head|bat|type|get-content|gc)\b.*monstre_" + re.escape(nom_fichier(c["nom"])))),
        E("repaire", 1, "ep.rencontre.repaire", "find",
          lambda c, l: a_tape(l, r"^\s*(find|get-childitem|gci|dir|ls)\b.*repaire")),
    ],
    "Fichiers": [
        E("enclos", 1, "ep.fichiers.enclos", "mkdir", _enclos),
        E("gamelle", 1, "ep.fichiers.gamelle", "touch / New-Item", _gamelle),
        E("doudou", 2, "ep.fichiers.doudou", "cp / copy",
          lambda c, l: _enclos(c, l) and _doudou(c, l), _prep_doudou),
        E("renomme", 2, "ep.fichiers.renomme", "mv / move", _renomme, _prep_vieux),
        E("archive", 3, "ep.fichiers.archive", "tar", _archive),
    ],
    "Réseau": [
        E("ping", 1, "ep.reseau.ping", "ping",
          lambda c, l: a_tape(l, r"^\s*ping\b.*(localhost|127\.0\.0\.1|::1)")),
        E("hote", 1, "ep.reseau.hote", "hostname", lambda c, l: a_tape(l, r"^\s*hostname\b")),
        E("ip", 2, "ep.reseau.ip", "ip a / ipconfig",
          lambda c, l: a_tape(l, r"^\s*(ip\s+(a|addr|address)\b|ifconfig\b|ipconfig\b|hostname\s+-I)")),
        E("dns", 2, "ep.reseau.dns", "nslookup",
          lambda c, l: a_tape(l, r"^\s*(nslookup|dig|host)\s+\S+")),
        E("page", 3, "ep.reseau.page", "curl -o", _page),
    ],
    "Processus": [
        E("ps", 1, "ep.processus.ps", "ps / Get-Process",
          lambda c, l: a_tape(l, r"^\s*(ps|top|htop|tasklist|get-process|gps)\b")),
        E("heure", 1, "ep.processus.heure", "date / Get-Date",
          lambda c, l: a_tape(l, r"^\s*(date|get-date)\b")),
        E("fond", 2, "ep.processus.fond", "sleep … &",
          lambda c, l: a_tape(l, r"^\s*sleep\s+\d+\s*&"), posix=True),
        E("jobs", 2, "ep.processus.jobs", "jobs", lambda c, l: a_tape(l, r"^\s*jobs\b"), posix=True),
        E("kill", 3, "ep.processus.kill", "kill %1", lambda c, l: a_tape(l, r"^\s*kill\s+"), posix=True),
    ],
    "Mémoire": [
        E("place", 1, "ep.memoire.place", "df -h / Get-PSDrive",
          lambda c, l: a_tape(l, r"^\s*(df|get-psdrive|gdr)\b")),
        E("ram", 1, "ep.memoire.ram", "free -h",
          lambda c, l: a_tape(l, r"^\s*(free|vmstat)\b"), posix=True),
        E("poids", 2, "ep.memoire.poids", "du -sh",
          lambda c, l: a_tape(l, r"^\s*du\b"), posix=True),
        E("sac", 3, "ep.memoire.sac", "ls … | wc -l",
          lambda c, l: a_repondu(l, c["x"]["sac"]), _prep_sac),
    ],
    "Sécurité": [
        E("cage", 1, "ep.securite.cage", "mkdir + touch",
          lambda c, l: (c["d"] / "enclos" / "cage").exists()),
        E("cachette", 1, "ep.securite.cachette", "touch .nom",
          _cachette),
        E("prive", 2, "ep.securite.prive", "chmod 600 / attrib +r",
          _cage_privee),
        E("empreinte", 3, "ep.securite.empreinte", "sha256sum",
          _empreinte, _prep_collier),
    ],
    "Code": [
        E("chant", 1, "ep.code.chant", "echo … > fichier", _chant),
        E("script", 2, "ep.code.script", "nano + chmod +x",
          _script),
        E("compte", 3, "ep.code.compte", "for i in …",
          _compte),
    ],
    "Matériel": [
        E("machine", 1, "ep.materiel.machine", "uname -m",
          lambda c, l: a_tape(l, r"^\s*(uname|arch|lscpu|systeminfo)\b")),
        E("coeurs", 2, "ep.materiel.coeurs", "nproc",
          lambda c, l: a_repondu(l, os.cpu_count() or 1)),
        E("disques", 2, "ep.materiel.disques", "lsblk / df",
          lambda c, l: a_tape(l, r"^\s*(lsblk|df|get-disk|fdisk\s+-l)\b")),
    ],
    "Bugs": [
        E("erreurs", 1, "ep.bugs.erreurs", "grep", lambda c, l: a_tape(l, r"grep.*error|select-string.*error"),
          _prep_bug),
        E("combien", 2, "ep.bugs.combien", "grep -c",
          lambda c, l: a_repondu(l, c["x"]["bug"]), _prep_bug),
        E("corrige", 3, "ep.bugs.corrige", "grep -v … >", _corrige, _prep_bug),
    ],
    "Nuage": [
        E("nuage", 1, "ep.nuage.nuage", "mkdir", lambda c, l: (c["d"] / "nuage").is_dir()),
        E("photos", 2, "ep.nuage.photos", "touch", _photos),
        E("copie", 3, "ep.nuage.copie", "cp -r", _nuage_copie),
    ],
    "Données": [
        E("debut", 1, "ep.donnees.debut", "head",
          lambda c, l: a_tape(l, r"^\s*(head|get-content.*-head|gc.*-head)\b.*croquettes"), _prep_lignes("croquettes.txt")),
        E("lignes", 2, "ep.donnees.lignes", "wc -l",
          lambda c, l: a_repondu(l, len(c["x"]["croquettes.txt"])), _prep_lignes("croquettes.txt")),
        E("trie", 2, "ep.donnees.trie", "sort … >", _trie, _prep_lignes("croquettes.txt")),
        E("differentes", 3, "ep.donnees.differentes", "sort | uniq | wc -l",
          lambda c, l: a_repondu(l, len(set(c["x"]["croquettes.txt"]))), _prep_lignes("croquettes.txt")),
    ],
    "Crypto": [
        E("lire", 1, "ep.crypto.lire", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|type|get-content|gc|less|more)\b.*message"), _prep_message),
        E("decode", 2, "ep.crypto.decode", "base64 -d",
          lambda c, l: a_repondu(l, c["x"]["secret"]), _prep_message),
        E("empreinte", 3, "ep.crypto.empreinte", "sha256sum",
          _empreinte, _prep_collier),
    ],
    "IA": [
        E("bonjour", 1, "ep.ia.bonjour", "echo",
          lambda c, l: a_tape(l, r"^\s*(echo|write-output)\b.*" + re.escape(c["nom"]))),
        E("chat", 2, "ep.ia.chat", "grep -c",
          lambda c, l: a_repondu(l, sum(1 for x in c["x"]["croquettes.txt"] if "chat" in x)),
          _prep_lignes("croquettes.txt")),
        E("frequent", 3, "ep.ia.frequent", "sort | uniq -c | sort -n",
          lambda c, l: any(a_repondu(l, m) for m in _plus_frequents(c["x"]["croquettes.txt"])), _prep_lignes("croquettes.txt")),
    ],
    "Rétro": [
        E("calendrier", 1, "ep.retro.calendrier", "cal",
          lambda c, l: a_tape(l, r"^\s*(cal|ncal|get-date)\b")),
        E("record", 2, "ep.retro.record", "sort -n | tail -1",
          lambda c, l: a_repondu(l, max(c["x"]["scores"])), _prep_scores),
        E("top3", 3, "ep.retro.top3", "sort -nr | head -3 >",
          _top3, _prep_scores),
    ],
    "Glitch": [
        E("voir", 1, "ep.glitch.voir", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|type|get-content|gc|less|more)\b.*corrompu"), _prep_corrompu),
        E("repare", 2, "ep.glitch.repare", "rev … >", _repare, _prep_corrompu, posix=True),
        E("chuchote", 3, "ep.glitch.chuchote", "tr A-Z a-z",
          _minuscules, _prep_cri, posix=True),
    ],
    "Système": [
        E("qui", 1, "ep.systeme.qui", "whoami",
          lambda c, l: a_tape(l, r"^\s*whoami\b")),
        E("systeme", 1, "ep.systeme.systeme", "uname -a",
          lambda c, l: a_tape(l, r"^\s*(uname|systeminfo|get-computerinfo)\b")),
        E("alias", 2, "ep.systeme.alias", "alias nom='…'",
          lambda c, l: a_tape(l, r"^\s*(alias\s+\w+=|set-alias\s+)")),
        E("variable", 3, "ep.systeme.variable", "export",
          lambda c, l: a_tape(l, r"^\s*(export\s+BESTIOLE=|\$env:BESTIOLE\s*=)")),
    ],
}


# G-06 : les notions qu'une épreuve demande. Une épreuve n'est tirée que si l'enfant les a déjà rencontrées : chaque
# commande goûtée (state["seen"], premier mot), ou « opt:<clé> » = une option ou un symbole expliqué après une leçon
# (state["options_vues"] : opt:tuyau = |, opt:ecrase = >, opt:inverse = grep -v…). « a/b » : l'une ou l'autre.
# Sans notion connue, une autre épreuve est choisie (jamais tar, base64, sha256sum, tr, export… sans les avoir vus).
REQUIS = {
    "Rencontre:examiner": ["cat"], "Rencontre:repaire": ["find"],
    "Fichiers:enclos": ["mkdir"], "Fichiers:gamelle": ["touch"], "Fichiers:doudou": ["cp"], "Fichiers:renomme": ["mv"],
    "Fichiers:archive": ["tar"],
    "Réseau:ping": ["ping"], "Réseau:hote": ["hostname"], "Réseau:ip": ["ip"], "Réseau:dns": ["nslookup/dig/host"],
    "Réseau:page": ["curl", "opt:output"],
    "Processus:ps": ["ps"], "Processus:heure": ["date"], "Processus:fond": ["sleep", "jobs"], "Processus:jobs": ["jobs"],
    "Processus:kill": ["kill"],
    "Mémoire:place": ["df"], "Mémoire:ram": ["free"], "Mémoire:poids": ["du"], "Mémoire:sac": ["ls", "wc", "opt:tuyau"],
    "Sécurité:cage": ["mkdir", "touch"], "Sécurité:cachette": ["touch", "opt:all"], "Sécurité:prive": ["chmod"],
    "Sécurité:empreinte": ["sha256sum"],
    "Code:chant": ["echo", "opt:ecrase"], "Code:script": ["echo", "chmod", "opt:plusx"], "Code:compte": ["for"],
    "Matériel:machine": ["uname"], "Matériel:coeurs": ["nproc"], "Matériel:disques": ["lsblk/df"],
    "Bugs:erreurs": ["grep"], "Bugs:combien": ["grep"], "Bugs:corrige": ["grep", "opt:inverse", "opt:ecrase"],
    "Nuage:nuage": ["mkdir"], "Nuage:photos": ["touch"], "Nuage:copie": ["cp", "opt:recursif_cp"],
    "Données:debut": ["head"], "Données:lignes": ["wc"], "Données:trie": ["sort", "opt:ecrase"],
    "Données:differentes": ["sort", "uniq", "opt:tuyau"],
    "Crypto:lire": ["cat"], "Crypto:decode": ["base64"], "Crypto:empreinte": ["sha256sum"],
    "IA:bonjour": ["echo"], "IA:chat": ["grep"], "IA:frequent": ["sort", "uniq", "opt:tuyau"],
    "Rétro:calendrier": ["cal"], "Rétro:record": ["sort", "tail", "opt:tuyau"],
    "Rétro:top3": ["sort", "head", "opt:tuyau", "opt:ecrase"],
    "Glitch:voir": ["cat"], "Glitch:repare": ["rev", "opt:ecrase"], "Glitch:chuchote": ["tr"],
    "Système:qui": ["whoami"], "Système:systeme": ["uname"], "Système:alias": ["alias"], "Système:variable": ["export"],
}
# les noms Windows / voisins comptent pour la commande Linux du tableau
SYNONYMES = {"type": "cat", "get-content": "cat", "gc": "cat", "less": "cat", "more": "cat", "new-item": "touch",
             "copy": "cp", "copy-item": "cp", "move": "mv", "move-item": "mv", "get-process": "ps", "gps": "ps",
             "tasklist": "ps", "top": "ps", "get-date": "date", "get-psdrive": "df", "select-string": "grep",
             "sls": "grep", "dir": "ls", "gci": "ls", "get-childitem": "ls", "ipconfig": "ip", "ifconfig": "ip",
             "write-output": "echo", "attrib": "chmod", "icacls": "chmod", "systeminfo": "uname", "set-alias": "alias",
             "md": "mkdir", "measure-object": "wc", "test-connection": "ping", "stop-process": "kill",
             "curl.exe": "curl", "invoke-webrequest": "curl", "iwr": "curl"}


def rencontrees(state):
    """Les notions déjà rencontrées par l'enfant : commandes goûtées (+ leurs noms Linux) et options expliquées."""
    vues = set(state.get("seen", []))
    vues |= {SYNONYMES[c] for c in vues if c in SYNONYMES}
    return vues | {"opt:" + o for o in state.get("options_vues", [])}


def connue(fid, notions):
    """L'épreuve ne demande que des notions déjà rencontrées (notions = rencontrees(state), ou None : pas de filtre)."""
    if notions is None:
        return True
    return all(any(a in notions for a in tok.split("/")) for tok in REQUIS.get(fid, []))


def _plus_frequents(lignes):
    from collections import Counter
    c = Counter(lignes)
    m = max(c.values())
    return [k for k, v in c.items() if v == m]


# ================================================================ déroulé

def repaire(nom):
    return f"repaire_{B._simple(nom)}"


def fiche(nom):
    return T / f"monstre_{B._simple(nom)}.txt"


# ---------------------------------------------------------------- les stats du familier servent au dressage
def bonus(state):
    st = state.get("stats", {})
    i, a, f, e = (st.get(k, 0) for k in ("Intelligence", "Agilité", "Force", "Endurance"))
    return {
        "exemple": 0.5 + min(0.4, i / 100),        # Intelligence : l'exemple apparaît plus tôt
        "temps": min(60, a // 2),                  # Agilité : secondes en plus
        "mefiance": min(30, f // 2),               # Force : le monstre se méfie moins au départ
        "seconde_chance": e >= 20,                 # Endurance : +60 s une fois au lieu de s'enfuir
    }


def ecrire_fiche(e, shiny, zone, ind=None, p=0):
    ind = ind or B.individu(e, shiny, zone)
    st = B.texte_stats(ind["stats"], p)
    var = ind.get("variante", "classique")
    champs = [(t("dress.fiche.nom"), e["nom"] + (" ✨ " + t("dress.fiche.shiny") if shiny else "")),
              (t("dress.fiche.numero"), f"#{e['numero']:03d}"),
              (t("dress.fiche.rarete"), t("dress.fiche.rarete.val", rarete=B.nom_rarete(ind["rarete"]), note=ind["note"])),
              (t("dress.fiche.variante"), var),
              (t("dress.fiche.age"), B.nom_stade(ind.get("stade", "bebe"))),
              (t("dress.fiche.famille"), e["famille"]),
              (terme("stats", p, majuscule=True), st),
              (t("dress.fiche.taille"), t("dress.fiche.taille.val", cm=e["taille_cm"], ko=e["poids_ko"]))]
    lc = max(largeur(k) for k, _ in champs)
    fiche(e["nom"]).write_text(
        "══════════ " + t("dress.fiche.titre") + " ══════════\n"
        + "".join(f"  {ajuster(k, lc)} : {v}\n" for k, v in champs) + "\n"
        f"  « {e['description']} »\n"
        f"  {e['comportement']}\n\n"
        "  " + t("dress.fiche.repaire", repaire=repaire(e["nom"]), terrain=terme("terrain", p)) + "\n",
        encoding="utf-8")


# Le tout premier dressage : des épreuves d'une seule commande courte, dans cet ordre de préférence
# (pas de boucle for, pas de guillemets imbriqués, pas de tuyau |, pas de « ; »).
SIMPLES = ["Système:qui", "Réseau:hote", "Processus:heure", "Matériel:machine", "Rétro:calendrier",
           "Système:systeme", "Mémoire:place", "Fichiers:enclos", "Nuage:nuage", "Crypto:lire", "Glitch:voir",
           "Données:debut", "Bugs:erreurs", "IA:bonjour", "Code:chant"]
# (nombre de bestioles dressées en dessous duquel s'applique le plafond, (épreuves de famille, niveau max))
PALIERS = [(3, (1, 1)), (5, (2, 1)), (8, (3, 2)), (12, (4, 3))]
TEMPS_DEBUTANT = 60            # secondes en plus tant que tu as moins de 5 bestioles


def plafond(n_captures):
    """(épreuves de famille au plus, niveau au plus) selon le nombre de bestioles dressées, ou None."""
    if n_captures is None:
        return None
    for seuil, cap in PALIERS:
        if n_captures < seuil:
            return cap
    return None


def choisir_epreuves(e, premiere, rarete="commune", n_captures=None, notions=None):
    """Les épreuves d'un dressage. n_captures = bestioles déjà dressées (None : pas de plafond).
    notions = rencontrees(state) : seules les épreuves dont les notions sont connues (G-06 ; None : toutes)."""
    if n_captures == 0:                       # le tout premier dressage : lire sa fiche + 1 épreuve simple
        return [EPREUVES["Rencontre"][0]] + _premiere_epreuve(e, notions)
    rencontre = [x for x in EPREUVES["Rencontre"] if x is EPREUVES["Rencontre"][0] or connue(_fid(x), notions)]
    return rencontre + (_epreuves_famille(e, premiere, rarete, plafond(n_captures), notions) or _premiere_epreuve(e, notions))


def _fid(x):
    return next(f"{f}:{y['id']}" for f, v in EPREUVES.items() for y in v if y is x)


def _premiere_epreuve(e, notions=None):
    fams = e.get("epreuves") or [e["famille"]]
    pool = {_fid(x): x for f in fams for x in EPREUVES.get(f, []) if not (x["posix"] and IS_WIN)}
    for fid in SIMPLES:
        if fid in pool and connue(fid, notions):
            return [pool[fid]]
    if connue("Rencontre:repaire", notions):
        return [EPREUVES["Rencontre"][1]]
    for fid in SIMPLES:                       # rien de connu dans sa famille : une épreuve simple d'ailleurs
        if connue(fid, notions):
            return [_par_id(fid)]
    return []


def _epreuves_famille(e, premiere, rarete="commune", cap=None, notions=None):
    fams = e.get("epreuves") or [e["famille"]]           # les commandes que cette famille aime
    pool = [x for f in fams for x in EPREUVES.get(f, []) if not (x["posix"] and IS_WIN) and connue(_fid(x), notions)]
    nmax = NIVEAU_MAX[rarete]
    n = NB_TACHES[rarete]
    if cap:                                   # débutant : moins d'épreuves, plus faciles
        n, nmax = min(n, cap[0]), min(nmax, cap[1])
    if rarete in ULTIMES and not cap:         # l'épreuve ultime : sa famille + des épreuves d'ailleurs
        autres = [x for f, v in EPREUVES.items() if f not in fams and f != "Rencontre" for x in v
                  if not (x["posix"] and IS_WIN) and x["niveau"] >= 2 and connue(f"{f}:{x['id']}", notions)]
        random.shuffle(autres)
        choix = sorted(pool, key=lambda x: x["niveau"])[-3:] + autres[:3]
    else:
        ok = sorted([x for x in pool if x["niveau"] <= nmax], key=lambda x: x["niveau"])
        choix = ok[:n] if premiere else sorted(random.sample(ok, min(n, len(ok))), key=lambda x: x["niveau"])
    vus, res = set(), []
    for x in choix:                            # pas deux fois la même épreuve
        if x["id"] not in vus:
            vus.add(x["id"])
            res.append(x)
    return res


def _par_id(fid):
    fam, i = fid.split(":", 1)
    return next(x for x in EPREUVES[fam] if x["id"] == i)


def contexte(state):
    d = state["dressage"]
    return {"d": T / d["zone"] / repaire(d["espece"]), "nom": d["espece"], "x": d["x"]}


def commencer(state, sauvage):
    """Un monstre vient d'apparaître : le dressage commence tout de suite."""
    e = B.espece(sauvage["e"])
    if e is None:
        return
    if not sauvage.get("ind"):                          # (anciennes sauvegardes)
        sauvage["ind"] = B.individu(e, sauvage.get("shiny"), sauvage["zone"], sauvage.get("v", "classique"))
        sauvage["ind"]["stade"] = "bebe"
    ind = sauvage["ind"]
    rar = ind["rarete"]
    jour = date.today().isoformat()
    if rar in ULTIMES and state.setdefault("dressage_essais", {}).get(e["nom"]) == jour:
        core.say(state, t("dress.un_essai", nom=e["nom"]), 12)
        return
    familles = state.setdefault("dressage_familles", [])
    premiere = e["famille"] not in familles
    n_caps = len(state.get("captures", []))
    taches = choisir_epreuves(e, premiere, rar, n_caps, rencontrees(state))
    bo = bonus(state)
    debutant = TEMPS_DEBUTANT if n_caps < 5 else 0
    fam_de = {id(x): f for f, v in EPREUVES.items() for x in v}
    state["dressage"] = {
        "sauvage": sauvage["f"], "espece": e["nom"], "shiny": sauvage.get("shiny", False), "zone": sauvage["zone"],
        "taches": [f"{fam_de[id(x)]}:{x['id']}" for x in taches], "faites": [], "lignes": [],
        "debut": time.time(), "duree": None if premiere else DUREE[rar] + bo["temps"] + debutant, "x": {}, "lecon": premiere,
        "ind": ind, "rarete": rar, "variante": ind.get("variante", "classique"),
        "mefiance": 100 - bo["mefiance"], "seconde": bo["seconde_chance"], "examine": False,
    }
    if rar in ULTIMES:
        state.setdefault("dressage_essais", {})[e["nom"]] = jour
    c = contexte(state)
    c["d"].mkdir(parents=True, exist_ok=True)
    ecrire_fiche(e, sauvage.get("shiny"), sauvage["zone"], ind, palier(state))
    preparees = set()
    for fid in state["dressage"]["taches"]:
        x = _par_id(fid)
        cle = getattr(x["prep"], "__qualname__", None)
        if x["prep"] and cle not in preparees:     # un même fichier n'est préparé qu'une fois
            preparees.add(cle)
            x["prep"](c)
    eclat = " ✨" if sauvage.get("shiny") else ""
    core.notif(state, t("dress.apparait", nom=e["nom"], eclat=eclat))
    if premiere:
        core.say(state, t("dress.premiere", nom=e["nom"], eclat=eclat, famille=e["famille"]), 14)
    else:
        core.say(state, t("dress.debut", nom=e["nom"], eclat=eclat), 12)
    core.log(state, t("dress.commence.log", nom=e["nom"], n=len(taches)))
    combat.preparer(state)                     # ta troupe affronte d'abord le monstre (si tu en as une)


def tache_courante(state):
    d = state.get("dressage")
    if not d:
        return None
    for fid in d["taches"]:
        if fid not in d["faites"]:
            return _par_id(fid)
    return None


def reste(state):
    d = state["dressage"]
    if d["duree"] is None:
        return None
    return max(0.0, d["duree"] - (time.time() - d["debut"]))


def tick(state, lignes):
    """À chaque étape de jeu : démarrer un dressage, vérifier les épreuves, gérer le chrono."""
    tapees = [l for l in lignes if not core.est_colle(l)]
    d = state.get("dressage")
    if not d:
        for s in list(state["sauvages"]):
            fichier = s["f"].split("/")[-1]
            for l in tapees:
                mots = l.split()
                if mots and core.first_word(l) in LECTURE and any(m.endswith(fichier) for m in mots[1:]):
                    commencer(state, s)
                    return
        return
    if combat.en_cours(state):                  # le combat d'abord : chaque commande tapée est un coup
        for l in tapees:
            if combat.coup(state, l):
                break
        return
    # G-34 : une commande qui a échoué (code de sortie ≠ 0, ou un chemin qui n'existe pas là où elle a été tapée) ne
    # compte pas pour une épreuve (`cat corrompu.txt` hors du repaire, `mkdir enclos` dans le grenier…)
    from . import maison, verif
    ok_l = []
    for k, l in enumerate(lignes):
        if core.est_colle(l):
            continue
        st = core.statut_de(lignes, k)
        if st not in (None, 0):
            continue
        if k == len(lignes) - 1 and st is None and verif.chemins_manquants(l, maison.ici(state)):
            continue
        ok_l.append(l)
    toutes, tapees = tapees, ok_l
    d["lignes"] = (d["lignes"] + tapees)[-200:]
    c = contexte(state)
    progres = False
    while True:
        x = tache_courante(state)
        if x is None:
            break
        try:
            ok = x["ok"](c, d["lignes"])
        except (OSError, KeyError, ValueError):
            ok = False
        if not ok:
            break
        d["faites"].append(next(f for f in d["taches"] if _par_id(f) is x))
        progres = True
    if tache_courante(state) is None:
        reussir(state)
        return
    if progres:
        n = len(d["faites"])
        d["indice"] = None
        if any(f.endswith(":examiner") for f in d["faites"]):
            d["examine"] = True
        core.say(state, au_hasard("dress.progres", nom=d["espece"], n=n, total=len(d["taches"])), 6)
    elif toutes:
        conseil = indice(state, c, toutes)
        if conseil and conseil != d.get("indice"):
            d["indice"] = conseil
            core.say(state, "💡 " + conseil, 12)
            core.terminal(state, "💡 " + conseil)          # aussi dans le terminal de l'enfant
            core.animer(state, "parle")
    r = reste(state)
    if r is not None and r <= 0:
        if d.get("seconde"):
            d["seconde"] = False
            d["duree"] += 60
            core.say(state, t("dress.seconde_chance", nom=d["espece"]), 10)
        else:
            echouer(state)


def reussir(state):
    d, state["dressage"] = state["dressage"], None
    e = B.espece(d["espece"])
    state["sauvages"] = [s for s in state["sauvages"] if s["f"] != d["sauvage"]]
    try:
        fiche(d["espece"]).unlink()
    except OSError:
        pass
    ind = d.get("ind") or B.individu(e, d["shiny"], d["zone"])
    ind["dresse"] = round(time.time() - d["debut"])
    ind.setdefault("stade", "bebe")
    ind["xp"] = 0                                       # il grandira en gardant son nom
    if d["shiny"]:
        ind.setdefault("teinte", round(random.uniform(0.15, 0.85), 3))   # couleur shiny propre à cet individu
    state["active"] = ind["id"]
    state["captures"].append(ind)
    state["collection"][e["nom"]] = state["collection"].get(e["nom"], 0) + 1
    fams = state.setdefault("dressage_familles", [])
    if e["famille"] not in fams:
        fams.append(e["famille"])
    titre = e["nom"] + (" ✨ SHINY" if d["shiny"] else "")
    core.log(state, t("dress.reussi.log", titre=titre, s=ind["dresse"], rarete=B.nom_rarete(ind["rarete"])))
    core.say(state, t("dress.reussi.dit", nom=e["nom"], eclat=" ✨" if d["shiny"] else "", marque=ind["marque"]), 14)
    core.notif(state, t("dress.reussi.notif", titre=titre))
    core.animer(state, "victoire")
    st = e.get("stat")
    if st not in state["stats"]:
        st = random.choice(list(state["stats"]))
    state["stats"][st] += 2 + len(d["taches"])
    bonus = 2 if d["duree"] and reste_depuis(d) > d["duree"] / 2 else 1
    core.add_xp(state, B.XP_RARETE[ind["rarete"]] * (3 if d["shiny"] else 1) * bonus)
    from . import envies
    envies.plaisir(state, "jeu", "dressage")


def reste_depuis(d):
    return max(0.0, d["duree"] - (time.time() - d["debut"]))


def echouer(state):
    d, state["dressage"] = state["dressage"], None
    state["sauvages"] = [s for s in state["sauvages"] if s["f"] != d["sauvage"]]
    try:
        fiche(d["espece"]).unlink()
    except OSError:
        pass
    core.log(state, t("dress.echec.log", nom=d["espece"]))
    core.say(state, t("dress.echec.dit", nom=d["espece"]), 12)
    core.animer(state, "ko")


def abandonner(state):
    if state.get("dressage"):
        d, state["dressage"] = state["dressage"], None
        core.log(state, t("dress.abandon.log", nom=d["espece"]))


COUL_STAT = {"PV": 203, "ATK": 208, "DEF": 75, "VIT": 120, "INT": 141}


def jauge(valeur, maxi, largeur, inverse=False):
    """Barre colorée : verte quand ça va bien, puis jaune, orange, rouge."""
    from .plateforme import RESET, fg
    f = max(0.0, min(1.0, valeur / maxi)) if maxi else 0
    bien = 1 - f if inverse else f
    coul = 120 if bien > 0.66 else 226 if bien > 0.4 else 208 if bien > 0.2 else 196
    n = round(largeur * f)
    return f"{fg(coul)}{'█' * n}{fg(238)}{'░' * (largeur - n)}{RESET}"


def petit_dessin(e, shiny, ind=None):
    """Le monstre en gros pixels (son vrai stade et sa variante) ; Abyssor : version détaillée réduite."""
    if ind and B.image(e):
        return B.dessin(e, shiny, stade=ind.get("stade", "adulte"), vid=ind.get("variante", "classique"),
                        teinte=ind.get("teinte", 0.5))
    if e.get("sprite_grand"):
        g = dict(e)
        g["sprite_grand"] = [r[::2] for r in e["sprite_grand"][::2]]
        return B.dessin(g, shiny, grand=True)
    return B.dessin(e, shiny)


def _largeur(texte):
    return largeur(texte)


def _pad(texte, n):
    return ajuster(texte, n)


def _cote_a_cote(gauche, droite, lg, milieu=None):
    h = max(len(gauche), len(droite))
    gauche = [""] * ((h - len(gauche)) // 2) + gauche
    droite = [""] * ((h - len(droite)) // 2) + droite
    out = []
    for k in range(h):
        m = milieu if (milieu and k == h // 2) else " " * _largeur(milieu or "")
        out.append("  " + _pad(gauche[k] if k < len(gauche) else "", lg) + m + (droite[k] if k < len(droite) else ""))
    return out


def lignes_ecran(state, largeur_txt=62):
    """Face-à-face : ton familier à gauche, le monstre à droite, les stats sous chacun ; puis une seule étape."""
    from . import core as C
    from . import sprites
    from .plateforme import BOLD, DIM, RESET, fg, piege
    d = state.get("dressage")
    if not d:
        return []
    e = B.espece(d["espece"])
    if not e:
        return []
    n_total = len(d["taches"])
    n_fait = len(d["faites"])
    mef = d.get("mefiance", 100) * (1 - n_fait / n_total)
    r = reste(state)
    p = palier(state)
    LG = 34                                     # largeur de la colonne de gauche
    cb = d.get("combat") if combat.en_cours(state) else None
    bete = combat._ind(state) if cb else None
    if bete and B.espece(bete["espece"]):
        # ---- la bestiole de ta troupe qui combat
        eb = B.espece(bete["espece"])
        sp_f = petit_dessin(eb, bete.get("shiny"), bete)
        pc = 0 if p < 2 else 2                  # colonne étroite : l'image seule, ou le vrai mot court
        sb = bete.get("stats") or eb["stats"]
        st_f = "  ".join(f"{fg(COUL_STAT.get(k, 250))}{B.nom_stat(k, pc)}{RESET} {BOLD}{sb[k]}{RESET}"
                         for k in ("ATK", "DEF", "VIT") if k in sb)
        gauche_txt = [f"{BOLD}{B.nom_affiche(eb, bete.get('shiny'), B.rarete_de(bete))}{RESET} {DIM}· "
                      + B.nom_stade(bete.get("stade", "bebe")) + RESET, st_f,
                      f"{fg(250)}{ajuster(terme('pv', pc, majuscule=True), 8)}{RESET} " + combat.coeurs(*cb["moi"])]
    else:
        # ---- le familier
        sp_f, _ = sprites.creature(state)
        lvl = C.level(state["xp"])
        st_f = "  ".join(f"{fg(v['color'])}{C.nom_stat(v['stat'], court=True)}{RESET} {BOLD}{state['stats'][v['stat']]}{RESET}"
                         for v in C.CATEGORIES.values())
        nom_f = B.arc_en_ciel(state["name"]) if state.get("shiny") else f"{BOLD}{state['name']}{RESET}"
        gauche_txt = [f"{nom_f} {DIM}· " + t("dress.niv", n=lvl) + RESET, st_f,
                      f"{fg(250)}{ajuster(t('app.faim'), 8)}{RESET} {jauge(state['hunger'], 100, 12)}"]
    # ---- le monstre
    ind = d.get("ind") or {}
    sp_m = petit_dessin(e, d["shiny"], ind)
    if d.get("examine") or (cb and cb.get("vu")):
        st_m = "  ".join(f"{fg(COUL_STAT.get(k, 250))}{B.nom_stat(k, p)}{RESET} {BOLD}{v}{RESET}"
                         for k, v in (ind.get("stats") or e["stats"]).items())
    else:
        st_m = f"{DIM}" + t("dress.stats_cachees", stats=terme("stats", p)) + RESET
    rar = d.get("rarete") or "commune"
    droite_txt = [f"{BOLD}{B.nom_affiche(e, d['shiny'], rar if d.get('examine') else None)}{RESET} "
                  f"{DIM}#{e['numero']:03d}{RESET} "
                  + (B.libelle_rarete(rar) if d.get("examine") else f"{DIM}" + t("dress.rarete_cachee") + RESET), st_m,
                  f"{fg(213)}{terme('mefiance', p)}{RESET} {jauge(mef, 100, 12, inverse=True)} {mef:3.0f} %"]
    if cb:
        droite_txt.append(f"{fg(250)}{ajuster(terme('pv', 0 if p < 2 else 2, majuscule=True), 8)}{RESET} "
                          + combat.coeurs(*cb["lui"]))
    out = ["", f" {fg(196)}{BOLD}⚔ " + t("dress.titre") + RESET, ""]
    out += _cote_a_cote(sp_f, sp_m, LG, milieu=f"{fg(196)}{BOLD}  VS  {RESET}")
    out += _cote_a_cote(gauche_txt, droite_txt, LG, milieu="      ")
    out.append("")
    if cb:
        return out + _lignes_combat(cb, largeur_txt)
    chrono = (f"{fg(153)}{t('dress.temps')}{RESET} {jauge(r, d['duree'], 30)} {r:3.0f} s" if r is not None
              else f"{fg(153)}{t('dress.temps')}{RESET} {fg(147)}{t('dress.pas_de_chrono')}{RESET}")
    pastilles = " ".join(f"{fg(120)}●{RESET}" if f in d["faites"] else f"{fg(226)}◉{RESET}" if _par_id(f) is tache_courante(state)
                         else f"{fg(240)}○{RESET}" for f in d["taches"])
    out.append(f"  {chrono}    {DIM}" + t("dress.etape", n=min(n_fait + 1, n_total), total=n_total) + f"{RESET} {pastilles}")
    x = tache_courante(state)
    if x is None:
        return out
    fid = next(f for f in d["taches"] if _par_id(f) is x)
    but = t(x["but"], **termes(p), nom_min=nom_fichier(d["espece"]), nom=d["espece"])
    expl, ex = aide(fid, d["espece"], p)
    etiq = {k: t("dress.col." + k) for k in ("mission", "comment", "tape", "dabord", "ou")}
    lc = max(largeur(v) for v in etiq.values()) + 1
    col = {k: ajuster(v, lc) for k, v in etiq.items()}
    vide = " " * lc
    out += [""]
    for k, l in enumerate(envelopper(but, largeur_txt)):
        out.append(f" {fg(226)}{BOLD}{col['mission'] if k == 0 else vide}{RESET}{BOLD}{l}{RESET}")
    if expl:
        for k, l in enumerate(envelopper(expl, largeur_txt)):
            out.append(f" {fg(117)}{col['comment'] if k == 0 else vide}{RESET}{l}")
    dedans = au_repaire(state)
    if ex:
        seuil = d["duree"] * (1 - bonus(state)["exemple"]) if d["duree"] else None
        if r is None or fid.startswith("Rencontre:") or d.get("exemple_tout_de_suite") or r <= d["duree"] - seuil:
            # P2-2 : le lieu et la commande sur la MÊME ligne (« cd ~/…/repaire_x puis mkdir enclos »)
            out.append(f" {fg(120)}{BOLD}{col['tape']}{RESET}{fg(120)}{commande_epreuve(state, fid, ex)}{RESET}")
        else:
            out.append(f" {fg(120)}{col['tape']}{RESET}{DIM}"
                       + t("dress.exemple_dans", s=f"{r - (d['duree'] - seuil):.0f}") + RESET)
    if d.get("indice"):
        for k, l in enumerate(envelopper(d["indice"], largeur_txt)):
            out.append(f" {fg(214)}{BOLD}{ajuster('💡 ' + t('dress.col.indice'), lc) if k == 0 else vide}{RESET}{fg(214)}{l}{RESET}")
    if fid.startswith("Rencontre:examiner"):
        ou = "~/terrain_terminagotchi"
    elif fid.startswith("Rencontre:"):
        ou = t("dress.nimporte_ou")
    else:
        ou = f"~/{T.name}/{d['zone']}/{repaire(d['espece'])}"
    if ou.startswith("~/") and not fid.startswith("Rencontre:"):
        if not dedans and not ex:
            out.append(f" {fg(246)}{col['dabord']}{RESET}" + t("dress.passe_porte", cmd=f"{fg(120)}cd {ou}{RESET}"))
    else:
        out.append(f" {fg(246)}{col['ou']}{RESET}{DIM}{ou}{RESET}")
    return out


def au_repaire(state):
    """L'enfant est déjà dans le repaire du monstre en cours de dressage."""
    from . import maison
    d = state.get("dressage")
    if not d:
        return False
    return maison.dans(maison.ici(state), f"{d['zone']}/{repaire(d['espece'])}")


def commande_epreuve(state, fid, ex):
    """La commande de l'épreuve telle qu'on la montre : précédée du cd vers le repaire si l'enfant n'y est pas."""
    from .plateforme import piege
    d = state["dressage"]
    if fid.startswith("Rencontre:") or au_repaire(state):
        return f"`{piege(ex)}`"
    return t("comp.lecon.puis", cd=piege(f"cd ~/{T.name}/{d['zone']}/{repaire(d['espece'])}"), cmd=piege(ex))


def _lignes_combat(cb, largeur_txt=62):
    """Le panneau du mini-combat : le tour, ce qui vient de se passer, les trois coups possibles."""
    from .plateforme import BOLD, DIM, RESET, fg, piege
    out = [f" {fg(196)}{BOLD}⚔ " + t("dress.combat.titre", n=min(cb["tour"] + 1, combat.TOURS_MAX), total=combat.TOURS_MAX) + RESET]
    for j in cb.get("journal", [])[-3:]:
        for k, l in enumerate(envelopper(j, largeur_txt)):
            out.append(f"   {DIM}{'»' if k == 0 else ' '}{RESET} {l}")
    out += ["", " " + t("dress.combat.coups")]
    coups = [(cb["special"], t("dress.combat.special.aide"), 213)] if cb["special"] and cb["special"] not in combat.OBSERVER else []
    coups += [("ls", t("dress.combat.observer.aide") + (" · " + t("dress.combat.special.aide") if cb["special"] in combat.OBSERVER else ""), 117),
              (t("dress.combat.autre"), t("dress.combat.attaque.aide"), 250)]
    lc = max(largeur(c) for c, _, _ in coups) + 2
    for c, expl, coul in coups:
        cmd = piege(c) if c != coups[-1][0] else c                    # « autre commande » : pas une commande à taper
        cmd = f"`{cmd}`" if c != coups[-1][0] else cmd
        out.append(f"   {fg(coul)}{BOLD}{ajuster(cmd, lc)}{RESET}→ {expl}")
    out.append(f" {DIM}" + t("dress.combat.ensuite") + RESET)
    return out


# ================================================================ explications pour débutants
# Pour chaque épreuve : ce que fait la commande (en clair) et un exemple complet à adapter.
# (exemple PC/Mac/Linux, exemple Windows PowerShell si différent)
AIDES = {
    "Rencontre:examiner": ("aide.rencontre.examiner",
                           "cat ~/terrain_terminagotchi/monstre_{nom_min}.txt", "cat ~/terrain_terminagotchi/monstre_{nom_min}.txt"),
    "Rencontre:repaire": ("aide.rencontre.repaire",
                          "find ~/terrain_terminagotchi -name repaire_{nom_min}",
                          "Get-ChildItem ~/terrain_terminagotchi -Recurse -Filter repaire_{nom_min}"),
    "Fichiers:enclos": ("aide.fichiers.enclos", "mkdir enclos", "mkdir enclos"),
    "Fichiers:gamelle": ("aide.fichiers.gamelle",
                         "touch enclos/gamelle", "New-Item enclos/gamelle"),
    "Fichiers:doudou": ("aide.fichiers.doudou",
                        "cp doudou.txt enclos/", "copy doudou.txt enclos/"),
    "Fichiers:renomme": ("aide.fichiers.renomme",
                         "mv vieux_nom.txt {nom_min}.txt", "move vieux_nom.txt {nom_min}.txt"),
    "Fichiers:archive": ("aide.fichiers.archive",
                         "tar -czf enclos.tar.gz enclos", "Compress-Archive enclos enclos.zip"),
    "Réseau:ping": ("aide.reseau.ping", "ping -c 3 localhost", "ping localhost"),
    "Réseau:hote": ("aide.reseau.hote", "hostname", "hostname"),
    "Réseau:ip": ("aide.reseau.ip",
                  "ip a", "ipconfig"),
    "Réseau:dns": ("aide.reseau.dns",
                   "nslookup example.com", "nslookup example.com"),
    "Réseau:page": ("aide.reseau.page",
                    "curl -o page.html https://example.com", "curl.exe -o page.html https://example.com"),
    "Processus:ps": ("aide.processus.ps",
                     "ps aux", "Get-Process"),
    "Processus:heure": ("aide.processus.heure", "date", "Get-Date"),
    "Processus:fond": ("aide.processus.fond", "sleep 120 &", None),
    "Processus:jobs": ("aide.processus.jobs", "jobs", None),
    "Processus:kill": ("aide.processus.kill",
                       "kill %1", None),
    "Mémoire:place": ("aide.memoire.place",
                      "df -h", "Get-PSDrive"),
    "Mémoire:ram": ("aide.memoire.ram", "free -h", None),
    "Mémoire:poids": ("aide.memoire.poids",
                      "du -sh ~/terrain_terminagotchi/nid", None),
    "Mémoire:sac": ("aide.memoire.sac", "ls sac | wc -l    puis    echo 7",
                    "(ls sac).Count    puis    echo 7"),
    "Sécurité:cage": ("aide.securite.cage",
                      "mkdir -p enclos ; touch enclos/cage", "New-Item enclos/cage"),
    "Sécurité:cachette": ("aide.securite.cachette",
                          "touch enclos/.secret", "New-Item enclos/.secret"),
    "Sécurité:prive": ("aide.securite.prive",
                       "chmod 600 enclos/cage", "attrib +r enclos/cage"),
    "Sécurité:empreinte": ("aide.securite.empreinte",
                           "sha256sum collier.txt    puis    echo 1a2b3c4d", "Get-FileHash collier.txt    puis    echo 1a2b3c4d"),
    "Code:chant": ("aide.code.chant",
                   "echo {nom} > chant.txt", "echo {nom} > chant.txt"),
    "Code:script": ("aide.code.script",
                    "echo 'echo hop' > tour.sh ; chmod +x tour.sh", "echo 'echo hop' > tour.ps1"),
    "Code:compte": ("aide.code.compte", "for i in 1 2 3 4 5; do echo $i; done > compte.txt", "1..5 > compte.txt"),
    "Matériel:machine": ("aide.materiel.machine",
                         "uname -m", "systeminfo"),
    "Matériel:coeurs": ("aide.materiel.coeurs", "nproc    puis    echo 8", "$env:NUMBER_OF_PROCESSORS    puis    echo 8"),
    "Matériel:disques": ("aide.materiel.disques", "lsblk", "Get-Disk"),
    "Bugs:erreurs": ("aide.bugs.erreurs",
                     "grep ERROR bug.log", "Select-String ERROR bug.log"),
    "Bugs:combien": ("aide.bugs.combien",
                     "grep -c ERROR bug.log    puis    echo 3", "(Select-String ERROR bug.log).Count    puis    echo 3"),
    "Bugs:corrige": ("aide.bugs.corrige",
                     "grep -v ERROR bug.log > corrige.log", "Select-String -NotMatch ERROR bug.log > corrige.log"),
    "Nuage:nuage": ("aide.nuage.nuage", "mkdir nuage", "mkdir nuage"),
    "Nuage:photos": ("aide.nuage.photos",
                     "touch nuage/photo1.jpg nuage/photo2.jpg nuage/photo3.jpg", "New-Item nuage/photo1.jpg, nuage/photo2.jpg, nuage/photo3.jpg"),
    "Nuage:copie": ("aide.nuage.copie",
                    "cp -r nuage nuage_copie", "Copy-Item -Recurse nuage nuage_copie"),
    "Données:debut": ("aide.donnees.debut",
                      "head croquettes.txt", "Get-Content croquettes.txt -Head 10"),
    "Données:lignes": ("aide.donnees.lignes",
                       "wc -l croquettes.txt    puis    echo 12", "(Get-Content croquettes.txt).Count    puis    echo 12"),
    "Données:trie": ("aide.donnees.trie",
                     "sort croquettes.txt > trie.txt", "Get-Content croquettes.txt | Sort-Object > trie.txt"),
    "Données:differentes": ("aide.donnees.differentes",
                            "sort croquettes.txt | uniq | wc -l    puis    echo 5",
                            "(Get-Content croquettes.txt | Sort-Object -Unique).Count    puis    echo 5"),
    "Crypto:lire": ("aide.crypto.lire", "cat message.b64", "Get-Content message.b64"),
    "Crypto:decode": ("aide.crypto.decode", "base64 -d message.b64    puis    echo motsecret", None),
    "Crypto:empreinte": ("aide.crypto.empreinte",
                         "sha256sum collier.txt    puis    echo 1a2b3c4d", "Get-FileHash collier.txt    puis    echo 1a2b3c4d"),
    "IA:bonjour": ("aide.ia.bonjour", "echo bonjour {nom}", "echo bonjour {nom}"),
    "IA:chat": ("aide.ia.chat", "grep -c chat croquettes.txt    puis    echo 2",
                "(Select-String chat croquettes.txt).Count    puis    echo 2"),
    "IA:frequent": ("aide.ia.frequent",
                    "sort croquettes.txt | uniq -c | sort -n", None),
    "Rétro:calendrier": ("aide.retro.calendrier", "cal", "Get-Date"),
    "Rétro:record": ("aide.retro.record",
                     "sort -n scores.txt | tail -1    puis    echo 9876", None),
    "Rétro:top3": ("aide.retro.top3", "sort -nr scores.txt | head -3 > top3.txt", None),
    "Glitch:voir": ("aide.glitch.voir", "cat corrompu.txt", "Get-Content corrompu.txt"),
    "Glitch:repare": ("aide.glitch.repare",
                      "rev corrompu.txt > repare.txt", None),
    "Glitch:chuchote": ("aide.glitch.chuchote", "tr A-Z a-z < cri.txt > chuchote.txt", None),
    "Système:qui": ("aide.systeme.qui", "whoami", "whoami"),
    "Système:systeme": ("aide.systeme.systeme", "uname -a", "systeminfo"),
    "Système:alias": ("aide.systeme.alias", "alias {nom_min}='echo GRRR'", "Set-Alias {nom_min} Get-Date"),
    "Système:variable": ("aide.systeme.variable", "export BESTIOLE={nom}", "$env:BESTIOLE = '{nom}'"),
}


def aide(fid, nom, p=0):
    """(explication, exemple) d'une épreuve ; p = palier de vocabulaire (voir mots.py)."""
    a = AIDES.get(fid)
    if not a:
        return None, None
    expl, ex, ex_win = a
    ex = ex_win if IS_WIN and ex_win else ex
    f = dict(termes(p), nom=nom, nom_min=nom_fichier(nom))
    ex = ex.format(**f).replace("    puis    ", "    " + t("dress.puis") + "    ")
    return t(expl, **f), ex


# ================================================================ « presque ! » : des indices clairs
# Quand l'épreuve en cours n'est pas réussie après une commande, on cherche si elle l'est PRESQUE :
# un indice propre à l'épreuve, un fichier créé au mauvais endroit, ou une faute de frappe par
# rapport à l'exemple. Le texte est traduit (clés « dress.indice.* »).

def _fichier_script():
    return "tour.ps1" if IS_WIN else "tour.sh"


def _i_script(c, l):
    p = c["d"] / _fichier_script()
    texte = lire(p)
    if texte is None:
        return None
    if "echo" not in texte.lower() and "write-" not in texte.lower():
        return t("dress.indice.script_echo", fichier=p.name)
    if not IS_WIN and not os.access(p, os.X_OK):
        return t("dress.indice.script_chmod", fichier=p.name)
    return None


def _i_compte(c, l):
    for x in l:
        m = x.strip()
        if re.match(r"^for\s", m) and (";" not in m or not re.search(r"\bdo\b", m) or not re.search(r"\bdone\b", m)):
            return t("dress.indice.for")
    if lignes_de(c["d"] / "compte.txt") is not None:
        return t("dress.indice.compte")
    return None


def _i_chant(c, l):
    if lire(c["d"] / "chant.txt") is not None:
        return t("dress.indice.chant", nom=nom_fichier(c["nom"]))
    return None


def _i_gamelle(c, l):
    if (c["d"] / "gamelle").exists():
        return t("dress.indice.dans_enclos", fichier="gamelle")
    if not (c["d"] / "enclos").is_dir() and a_tape(l, r"enclos[/\\]gamelle"):
        return t("dress.indice.enclos_dabord")
    return None


def _i_doudou(c, l):
    if (c["d"] / "enclos" / "doudou.txt").exists() and not (c["d"] / "doudou.txt").exists():
        return t("dress.indice.cp_pas_mv")
    if not (c["d"] / "enclos").is_dir() and a_tape(l, r"^\s*(cp|copy)\b"):
        return t("dress.indice.enclos_dabord")
    return None


def _i_renomme(c, l):
    if not (c["d"] / "vieux_nom.txt").exists() and not (c["d"] / f"{nom_fichier(c['nom'])}.txt").exists():
        return t("dress.indice.nom_min", nom_min=nom_fichier(c["nom"]))
    return None


def _i_dans_enclos(nom):
    def f(c, l):
        if (c["d"] / nom).exists() and not (c["d"] / "enclos" / nom).exists():
            return t("dress.indice.dans_enclos", fichier=nom)
        if not (c["d"] / "enclos").is_dir() and a_tape(l, r"enclos[/\\]"):
            return t("dress.indice.enclos_dabord")
        return None
    return f


def _i_cachette(c, l):
    if not (c["d"] / "enclos").is_dir():
        return t("dress.indice.enclos_dabord") if a_tape(l, r"enclos[/\\]") else None
    if any(p.is_file() and not p.name.startswith(".") for p in (c["d"] / "enclos").iterdir()) and a_tape(l, r"^\s*(touch|new-item)\b"):
        return t("dress.indice.point")
    return None


def _i_prive(c, l):
    return t("dress.indice.prive") if (c["d"] / "enclos" / "cage").exists() else None


def _i_nombre(c, l):
    if any(re.match(r"^\s*(echo|write-output)\s+[\"']?\d+[\"']?\s*$", x, re.I) for x in l):
        return t("dress.indice.nombre")
    return None


def _i_reponse(c, l):
    if any(re.match(r"^\s*(echo|write-output)\s+\S", x, re.I) for x in l):
        return t("dress.indice.reponse")
    return None


def _i_contenu(nom):
    def f(c, l):
        return t("dress.indice.fichier", fichier=nom) if (c["d"] / nom).exists() else None
    return f


def _i_photos(c, l):
    d = c["d"] / "nuage"
    if d.is_dir() and 0 < len(list(d.glob("photo*"))) < 3:
        return t("dress.indice.photos", n=len(list(d.glob("photo*"))))
    return None


INDICES = {
    "Code:script": _i_script, "Code:compte": _i_compte, "Code:chant": _i_chant,
    "Fichiers:gamelle": _i_gamelle, "Fichiers:doudou": _i_doudou, "Fichiers:renomme": _i_renomme,
    "Sécurité:cage": _i_dans_enclos("cage"), "Sécurité:cachette": _i_cachette, "Sécurité:prive": _i_prive,
    "Mémoire:sac": _i_nombre, "Matériel:coeurs": _i_nombre, "Bugs:combien": _i_nombre, "Données:lignes": _i_nombre,
    "Données:differentes": _i_nombre, "IA:chat": _i_nombre, "Rétro:record": _i_nombre,
    "Crypto:decode": _i_reponse, "Sécurité:empreinte": _i_reponse, "Crypto:empreinte": _i_reponse,
    "IA:frequent": _i_reponse,
    "Données:trie": _i_contenu("trie.txt"), "Rétro:top3": _i_contenu("top3.txt"), "Bugs:corrige": _i_contenu("corrige.log"),
    "Glitch:repare": _i_contenu("repare.txt"), "Glitch:chuchote": _i_contenu("chuchote.txt"),
    "Nuage:photos": _i_photos,
}

# ce que l'épreuve doit créer dans le repaire (pour repérer un fichier créé ailleurs)
ATTENDUS = {"Fichiers:enclos": "enclos", "Code:chant": "chant.txt", "Code:script": _fichier_script(),
            "Code:compte": "compte.txt", "Nuage:nuage": "nuage", "Données:trie": "trie.txt", "Rétro:top3": "top3.txt",
            "Glitch:repare": "repare.txt", "Glitch:chuchote": "chuchote.txt", "Bugs:corrige": "corrige.log",
            "Réseau:page": "page.html", "Fichiers:archive": "enclos.tar.gz", "Sécurité:cage": "enclos"}


def _ailleurs(c, nom):
    """Le fichier attendu, trouvé hors du repaire (dans le dossier personnel ou le terrain), ou None."""
    ici = c["d"] / nom
    if ici.exists():
        return None
    from pathlib import Path
    for base in (Path.home(), T, c["d"].parent):
        p = base / nom
        if p.exists():
            return p
    if T.is_dir():
        for p in T.rglob(nom.split("/")[-1]):
            if p != ici and c["d"] not in p.parents:
                return p
    return None


def _mots(ligne):
    """Les mots d'une commande, chemins réduits à leur dernier morceau (~/x/monstre_a.txt → monstre_a.txt)."""
    out = []
    for m in ligne.replace("'", " ").replace('"', " ").split():
        m = m.rstrip("/\\")
        out.append(re.split(r"[/\\]", m)[-1] if ("/" in m or "\\" in m) else m)
    return [m for m in out if m]


def faute_de_frappe(lignes, modele, chiffres=False):
    """(mot tapé, mot attendu) si une ligne ressemble à la commande modèle avec un mot mal écrit.
    chiffres=True : les nombres comptent aussi (chmod 44 au lieu de chmod 444)."""
    import difflib
    attendus = _mots(modele.split("    ")[0])
    if not attendus:
        return None
    for l in lignes:
        mots = _mots(l)
        if not mots or mots[0].lower() != attendus[0].lower():
            continue
        for m in mots[1:]:
            if chiffres and m.isdigit() and m not in attendus:
                nombres = [a for a in attendus[1:] if a.isdigit()]
                proche = difflib.get_close_matches(m, nombres, n=1, cutoff=0.6)
                if proche:
                    return m, proche[0]
            if m in attendus or m.startswith("-") or m.isdigit() or len(m) < 3:
                continue
            cibles = [a for a in attendus[1:] if not a.startswith("-") and not a.isdigit() and len(a) >= 3]
            proche = difflib.get_close_matches(m, cibles, n=1, cutoff=0.75)
            if proche and proche[0] != m:
                return m, proche[0]
    return None


def indice(state, c, lignes):
    """L'indice pour l'épreuve en cours quand elle est presque réussie, ou None."""
    d = state["dressage"]
    x = tache_courante(state)
    if x is None:
        return None
    fid = next(f for f in d["taches"] if _par_id(f) is x)
    try:
        f = INDICES.get(fid)
        r = f(c, lignes) if f else None
        if r:
            return r
        nom = ATTENDUS.get(fid)
        if nom and _ailleurs(c, nom) is not None:
            return t("dress.indice.mauvais_endroit", fichier=nom,
                     cmd=f"cd ~/{T.name}/{d['zone']}/{repaire(d['espece'])}")
    except (OSError, KeyError, ValueError):
        pass
    _expl, ex = aide(fid, d["espece"], palier(state))
    if ex:
        ff = faute_de_frappe(lignes, ex)
        if ff:
            return t("dress.indice.faute", tape=ff[0], attendu=ff[1])
    return None
