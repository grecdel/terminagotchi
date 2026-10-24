"""Dressage : pour gagner la confiance d'une bestiole sauvage, il faut réussir une suite de
vraies commandes avant la fin du temps imparti.

Le jeu vérifie le RÉSULTAT (le dossier existe, le fichier est trié, la bonne réponse a été
donnée avec echo…), pas le texte exact : chacun s'y prend comme il veut. Chercher dans le
lexique est permis ; le copier-coller, non (il ne compte pas).

Déroulé : on trouve la bestiole (ls -a), on la lit (cat) → le dressage commence.
Le premier dressage de chaque famille se fait sans chrono : c'est une leçon.
"""
import hashlib
import base64
import os
import random
import re
import stat
import time
from datetime import date

from . import bestiaire as B
from . import core
from .plateforme import IS_WIN

T = core.TERRAIN
DUREE = {"commune": 90, "peu commune": 120, "rare": 180, "légendaire": 240}
NB_TACHES = {"commune": 2, "peu commune": 3, "rare": 4, "légendaire": 6}
NIVEAU_MAX = {"commune": 1, "peu commune": 2, "rare": 3, "légendaire": 3}
LECTURE = {"cat", "less", "more", "head", "tail", "type", "get-content", "bat", "nano", "vim", "vi"}

MOTS = ["octet", "pixel", "bug", "shell", "noyau", "cache", "paquet", "script", "fichier", "chat",
        "nuage", "clef", "boucle", "signal", "tuyau", "racine"]


# ================================================================ outils de vérification

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
    (c["d"] / "doudou.txt").write_text(f"Le doudou préféré de {c['nom']}.\n", encoding="utf-8")


def _doudou(c, l): return (c["d"] / "doudou.txt").exists() and (c["d"] / "enclos" / "doudou.txt").exists()


def _prep_vieux(c):
    (c["d"] / "vieux_nom.txt").write_text("Renomme-moi !\n", encoding="utf-8")


def _renomme(c, l):
    return not (c["d"] / "vieux_nom.txt").exists() and (c["d"] / f"{c['nom'].lower()}.txt").exists()


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
    lignes = [f"INFO tout va bien {i}" for i in range(6)] + [f"ERROR la bestiole a mordu le câble {i}" for i in range(n)]
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
    phrase = random.choice(["je suis ton ami", "merci pour la gamelle", "le terminal est mon jardin",
                            "on part en exploration"])
    (c["d"] / "corrompu.txt").write_text(phrase[::-1] + "\n", encoding="utf-8")
    c["x"]["phrase"] = phrase


def _repare(c, l):
    t = lire(c["d"] / "repare.txt")
    return t is not None and t.strip() == c["x"]["phrase"]


def _prep_cri(c):
    phrase = random.choice(["JE VEUX JOUER", "OU EST MA GAMELLE", "RACONTE MOI UNE HISTOIRE"])
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
    return t is not None and c["nom"].lower() in t.lower()


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


def _cachette(c, l): return any(p.name.startswith(".") and p.is_file() for p in (c["d"] / "enclos").glob(".*")) \
    if (c["d"] / "enclos").is_dir() else False


E = lambda i, n, but, indice, ok, prep=None, posix=False: \
    {"id": i, "niveau": n, "but": but, "indice": indice, "ok": ok, "prep": prep, "posix": posix}

EPREUVES = {
    "Fichiers": [
        E("enclos", 1, "Construis-moi un enclos : un dossier « enclos » ici.", "mkdir", _enclos),
        E("gamelle", 1, "Pose une gamelle (un fichier « gamelle ») dans mon enclos.", "touch / New-Item", _gamelle),
        E("doudou", 2, "Copie mon doudou.txt dans l'enclos (je veux le garder aussi ici).", "cp / copy",
          lambda c, l: _enclos(c, l) and _doudou(c, l), _prep_doudou),
        E("renomme", 2, "Renomme vieux_nom.txt avec mon nom (en minuscules) : {nom_min}.txt", "mv / move", _renomme, _prep_vieux),
        E("archive", 3, "Range tout mon enclos dans une archive « enclos.tar.gz » (ou enclos.zip).", "tar", _archive),
    ],
    "Réseau": [
        E("ping", 1, "Envoie-moi un signal sur ta propre machine (localhost).", "ping",
          lambda c, l: a_tape(l, r"^\s*ping\b.*(localhost|127\.0\.0\.1|::1)")),
        E("hote", 1, "Dis-moi comment s'appelle ta machine.", "hostname", lambda c, l: a_tape(l, r"^\s*hostname\b")),
        E("ip", 2, "Montre-moi ton adresse IP.", "ip a / ipconfig",
          lambda c, l: a_tape(l, r"^\s*(ip\s+(a|addr|address)\b|ifconfig\b|ipconfig\b|hostname\s+-I)")),
        E("dns", 2, "Demande à l'annuaire d'internet l'adresse d'un site.", "nslookup",
          lambda c, l: a_tape(l, r"^\s*(nslookup|dig|host)\s+\S+")),
        E("page", 3, "Rapporte-moi une page web dans un fichier « page.html ».", "curl -o",
          lambda c, l: (c["d"] / "page.html").exists() and (c["d"] / "page.html").stat().st_size > 0),
    ],
    "Processus": [
        E("ps", 1, "Montre-moi tous les programmes qui tournent.", "ps / Get-Process",
          lambda c, l: a_tape(l, r"^\s*(ps|top|htop|tasklist|get-process|gps)\b")),
        E("heure", 1, "Quelle heure est-il ? Demande à la machine.", "date / Get-Date",
          lambda c, l: a_tape(l, r"^\s*(date|get-date)\b")),
        E("fond", 2, "Lance un « sleep 120 » en arrière-plan (avec &).", "sleep … &",
          lambda c, l: a_tape(l, r"^\s*sleep\s+\d+\s*&"), posix=True),
        E("jobs", 2, "Retrouve ton programme en arrière-plan.", "jobs", lambda c, l: a_tape(l, r"^\s*jobs\b"), posix=True),
        E("kill", 3, "Arrête le programme en arrière-plan.", "kill %1", lambda c, l: a_tape(l, r"^\s*kill\s+"), posix=True),
    ],
    "Mémoire": [
        E("place", 1, "Combien de place reste-t-il sur ton disque ?", "df -h / Get-PSDrive",
          lambda c, l: a_tape(l, r"^\s*(df|get-psdrive|gdr)\b")),
        E("ram", 1, "Et la mémoire vive, il en reste ?", "free -h",
          lambda c, l: a_tape(l, r"^\s*(free|vmstat)\b"), posix=True),
        E("poids", 2, "Combien pèse mon nid ? (la taille du dossier)", "du -sh",
          lambda c, l: a_tape(l, r"^\s*du\b"), posix=True),
        E("sac", 3, "J'ai caché des objets dans mon sac/. Combien ? Réponds-moi avec echo.", "ls … | wc -l",
          lambda c, l: a_repondu(l, c["x"]["sac"]), _prep_sac),
    ],
    "Sécurité": [
        E("cage", 1, "Fabrique-moi une cage : un fichier « cage » dans mon enclos.", "mkdir + touch",
          lambda c, l: (c["d"] / "enclos" / "cage").exists()),
        E("cachette", 1, "Cache un fichier secret dans mon enclos (un nom qui commence par un point).", "touch .nom",
          _cachette),
        E("prive", 2, "Que personne d'autre que toi ne puisse toucher à ma cage.", "chmod 600 / attrib +r",
          _cage_privee),
        E("empreinte", 3, "Donne-moi l'empreinte de collier.txt (ses 8 premiers caractères, avec echo).", "sha256sum",
          _empreinte, _prep_collier),
    ],
    "Code": [
        E("chant", 1, "Écris mon nom dans un fichier « chant.txt ».", "echo … > fichier", _chant),
        E("script", 2, "Écris-moi un petit script tour.sh qui fait un echo, et rends-le exécutable.", "nano + chmod +x",
          _script),
        E("compte", 3, "Écris les nombres de 1 à 5, un par ligne, dans compte.txt (avec une boucle !).", "for i in …",
          _compte),
    ],
    "Matériel": [
        E("machine", 1, "C'est quoi, comme machine ? (son type de processeur)", "uname -m",
          lambda c, l: a_tape(l, r"^\s*(uname|arch|lscpu|systeminfo)\b")),
        E("coeurs", 2, "Combien de cœurs a ton processeur ? Réponds avec echo.", "nproc",
          lambda c, l: a_repondu(l, os.cpu_count() or 1)),
        E("disques", 2, "Montre-moi tes disques.", "lsblk / df",
          lambda c, l: a_tape(l, r"^\s*(lsblk|df|get-disk|fdisk\s+-l)\b")),
    ],
    "Bugs": [
        E("erreurs", 1, "Trouve les lignes ERROR dans bug.log.", "grep", lambda c, l: a_tape(l, r"grep.*error|select-string.*error"),
          _prep_bug),
        E("combien", 2, "Combien y a-t-il d'erreurs dans bug.log ? Réponds avec echo.", "grep -c",
          lambda c, l: a_repondu(l, c["x"]["bug"]), _prep_bug),
        E("corrige", 3, "Fais-moi un corrige.log avec toutes les lignes SAUF les erreurs.", "grep -v … >", _corrige, _prep_bug),
    ],
    "Nuage": [
        E("nuage", 1, "Fais-moi un nuage : un dossier « nuage ».", "mkdir", lambda c, l: (c["d"] / "nuage").is_dir()),
        E("photos", 2, "Mets trois photos dedans (photo1.jpg, photo2.jpg, photo3.jpg).", "touch", _photos),
        E("copie", 3, "Sauvegarde tout le nuage dans un dossier « nuage_copie ».", "cp -r", _nuage_copie),
    ],
    "Données": [
        E("debut", 1, "Montre-moi juste le début de croquettes.txt.", "head",
          lambda c, l: a_tape(l, r"^\s*(head|get-content.*-head|gc.*-head)\b.*croquettes"), _prep_lignes("croquettes.txt")),
        E("lignes", 2, "Combien de lignes dans croquettes.txt ? Réponds avec echo.", "wc -l",
          lambda c, l: a_repondu(l, len(c["x"]["croquettes.txt"])), _prep_lignes("croquettes.txt")),
        E("trie", 2, "Trie croquettes.txt dans un fichier trie.txt.", "sort … >", _trie, _prep_lignes("croquettes.txt")),
        E("differentes", 3, "Combien de sortes de croquettes différentes ? Réponds avec echo.", "sort | uniq | wc -l",
          lambda c, l: a_repondu(l, len(set(c["x"]["croquettes.txt"]))), _prep_lignes("croquettes.txt")),
    ],
    "Crypto": [
        E("lire", 1, "Lis mon message codé, message.b64.", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|type|get-content|gc|less|more)\b.*message"), _prep_message),
        E("decode", 2, "Décode message.b64 et dis-moi le mot secret avec echo.", "base64 -d",
          lambda c, l: a_repondu(l, c["x"]["secret"]), _prep_message),
        E("empreinte", 3, "Donne-moi l'empreinte de collier.txt (ses 8 premiers caractères, avec echo).", "sha256sum",
          _empreinte, _prep_collier),
    ],
    "IA": [
        E("bonjour", 1, "Dis-moi bonjour avec mon nom (avec echo).", "echo",
          lambda c, l: a_tape(l, r"^\s*(echo|write-output)\b.*" + re.escape(c["nom"]))),
        E("chat", 2, "Combien de lignes contiennent « chat » dans croquettes.txt ? Réponds avec echo.", "grep -c",
          lambda c, l: a_repondu(l, sum(1 for x in c["x"]["croquettes.txt"] if "chat" in x)),
          _prep_lignes("croquettes.txt")),
        E("frequent", 3, "Quel est le mot le plus fréquent dans croquettes.txt ? Réponds avec echo.", "sort | uniq -c | sort -n",
          lambda c, l: any(a_repondu(l, m) for m in _plus_frequents(c["x"]["croquettes.txt"])), _prep_lignes("croquettes.txt")),
    ],
    "Rétro": [
        E("calendrier", 1, "Montre-moi le calendrier du mois.", "cal",
          lambda c, l: a_tape(l, r"^\s*(cal|ncal|get-date)\b")),
        E("record", 2, "Quel est le meilleur score de scores.txt ? Réponds avec echo.", "sort -n | tail -1",
          lambda c, l: a_repondu(l, max(c["x"]["scores"])), _prep_scores),
        E("top3", 3, "Écris les 3 meilleurs scores, du plus grand au plus petit, dans top3.txt.", "sort -nr | head -3 >",
          _top3, _prep_scores),
    ],
    "Glitch": [
        E("voir", 1, "Regarde corrompu.txt… mes mots sont à l'envers !", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|type|get-content|gc|less|more)\b.*corrompu"), _prep_corrompu),
        E("repare", 2, "Remets corrompu.txt à l'endroit dans repare.txt.", "rev … >", _repare, _prep_corrompu, posix=True),
        E("chuchote", 3, "Je crie trop fort (cri.txt) : écris-le en minuscules dans chuchote.txt.", "tr A-Z a-z",
          _minuscules, _prep_cri, posix=True),
    ],
    "Système": [
        E("qui", 1, "Qui es-tu ? Demande ton nom d'utilisateur à la machine.", "whoami",
          lambda c, l: a_tape(l, r"^\s*whoami\b")),
        E("systeme", 1, "Sur quel système vivons-nous ?", "uname -a",
          lambda c, l: a_tape(l, r"^\s*(uname|systeminfo|get-computerinfo)\b")),
        E("alias", 2, "Crée-moi une commande à mon nom avec alias.", "alias nom='…'",
          lambda c, l: a_tape(l, r"^\s*(alias\s+\w+=|set-alias\s+)")),
        E("variable", 3, "Crée une variable d'environnement BESTIOLE qui contient mon nom.", "export",
          lambda c, l: a_tape(l, r"^\s*(export\s+BESTIOLE=|\$env:BESTIOLE\s*=)")),
    ],
}


def _plus_frequents(lignes):
    from collections import Counter
    c = Counter(lignes)
    m = max(c.values())
    return [k for k, v in c.items() if v == m]


# ================================================================ déroulé

def lieu_dossier(sauvage):
    return T / sauvage["zone"]


def choisir_epreuves(e, premiere):
    fam = e["famille"]
    pool = [x for x in EPREUVES.get(fam, []) if not (x["posix"] and IS_WIN)]
    nmax = NIVEAU_MAX[e["rarete"]]
    n = NB_TACHES[e["rarete"]]
    if e["rarete"] == "légendaire":           # l'épreuve ultime : sa famille + des épreuves d'ailleurs
        autres = [x for f, v in EPREUVES.items() if f != fam for x in v if not (x["posix"] and IS_WIN) and x["niveau"] >= 2]
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
    return {"d": T / d["zone"], "nom": d["espece"], "x": d["x"]}


def commencer(state, sauvage):
    e = B.espece(sauvage["e"])
    if e is None:
        return
    jour = date.today().isoformat()
    if e["rarete"] == "légendaire" and state.setdefault("dressage_essais", {}).get(e["nom"]) == jour:
        core.say(state, f"{e['nom']} t'ignore… les légendaires n'acceptent qu'un essai par jour. Reviens demain !", 12)
        return
    familles = state.setdefault("dressage_familles", [])
    premiere = e["famille"] not in familles
    taches = choisir_epreuves(e, premiere)
    fam_de = {id(x): f for f, v in EPREUVES.items() for x in v}
    state["dressage"] = {
        "sauvage": sauvage["f"], "espece": e["nom"], "shiny": sauvage.get("shiny", False), "zone": sauvage["zone"],
        "taches": [f"{fam_de[id(x)]}:{x['id']}" for x in taches], "faites": [], "lignes": [],
        "debut": time.time(), "duree": None if premiere else DUREE[e["rarete"]], "x": {}, "lecon": premiere,
    }
    if e["rarete"] == "légendaire":
        state["dressage_essais"][e["nom"]] = jour
    c = contexte(state)
    c["d"].mkdir(parents=True, exist_ok=True)
    preparees = set()
    for fid in state["dressage"]["taches"]:
        x = _par_id(fid)
        cle = getattr(x["prep"], "__qualname__", None)
        if x["prep"] and cle not in preparees:     # un même fichier n'est préparé qu'une fois
            preparees.add(cle)
            x["prep"](c)
    eclat = " ✨" if sauvage.get("shiny") else ""
    if premiere:
        core.say(state, f"{e['nom']}{eclat} te regarde, curieux. Première rencontre avec la famille {e['famille']} : "
                        f"prends ton temps, je t'explique tout !", 14)
    else:
        core.say(state, f"{e['nom']}{eclat} se méfie… Tu as {DUREE[e['rarete']]} s pour gagner sa confiance !", 12)
    core.log(state, f"🎓 Dressage de {e['nom']} commencé ({len(taches)} épreuves)")


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
        core.say(state, random.choice(["Il remue la queue !", "Il s'approche un peu…", "Il a l'air impressionné !",
                                       "Il ronronne en binaire."]) + f" ({n}/{len(d['taches'])})", 6)
    r = reste(state)
    if r is not None and r <= 0:
        echouer(state)


def reussir(state):
    d, state["dressage"] = state["dressage"], None
    e = B.espece(d["espece"])
    state["sauvages"] = [s for s in state["sauvages"] if s["f"] != d["sauvage"]]
    try:
        (T / d["sauvage"]).unlink()
    except OSError:
        pass
    ind = B.individu(e, d["shiny"], d["zone"])
    ind["dresse"] = round(time.time() - d["debut"])
    state["captures"].append(ind)
    state["collection"][e["nom"]] = state["collection"].get(e["nom"], 0) + 1
    fams = state.setdefault("dressage_familles", [])
    if e["famille"] not in fams:
        fams.append(e["famille"])
    titre = e["nom"] + (" ✨ SHINY" if d["shiny"] else "")
    core.log(state, f"🎓 {titre} dressé en {ind['dresse']} s ! ({e['rarete']})")
    core.say(state, f"{e['nom']}{' ✨' if d['shiny'] else ''} te fait confiance et rejoint ton équipe ! "
                    f"Signe particulier : {ind['marque']}. ([c] pour ta collection)", 14)
    core.notif(state, f"🎓 {titre} a rejoint ton équipe !")
    st = e.get("stat")
    if st not in state["stats"]:
        st = random.choice(list(state["stats"]))
    state["stats"][st] += 2 + len(d["taches"])
    bonus = 2 if d["duree"] and reste_depuis(d) > d["duree"] / 2 else 1
    core.add_xp(state, B.XP_RARETE[e["rarete"]] * (3 if d["shiny"] else 1) * bonus)


def reste_depuis(d):
    return max(0.0, d["duree"] - (time.time() - d["debut"]))


def echouer(state):
    d, state["dressage"] = state["dressage"], None
    core.log(state, f"💨 {d['espece']} a perdu patience et s'est caché plus loin…")
    core.say(state, f"Trop tard ! {d['espece']} s'est enfui. Il se cache encore dans {d['zone']} : relis-le pour réessayer.", 12)


def abandonner(state):
    if state.get("dressage"):
        d, state["dressage"] = state["dressage"], None
        core.log(state, f"🏳 Dressage de {d['espece']} abandonné")


def lignes_ecran(state, largeur=60):
    """Le panneau de dressage affiché sous la créature."""
    from .plateforme import BOLD, DIM, RESET, fg, piege
    d = state.get("dressage")
    if not d:
        return []
    e = B.espece(d["espece"])
    r = reste(state)
    if r is None:
        chrono = f"{fg(147)}leçon : pas de chrono{RESET}"
    else:
        plein = int(20 * r / d["duree"])
        coul = 120 if r > d["duree"] / 2 else 214 if r > d["duree"] / 5 else 196
        chrono = f"{fg(coul)}{'█' * plein}{'░' * (20 - plein)}{RESET} {r:.0f} s"
    nom = B.nom_affiche(e, d["shiny"]) if e else d["espece"]
    out = [fg(213) + "── 🎓 DRESSAGE " + RESET + nom + f"  {chrono}"]
    c = contexte(state)
    for fid in d["taches"]:
        x = _par_id(fid)
        but = x["but"].format(nom_min=d["espece"].lower(), nom=d["espece"])
        if fid in d["faites"]:
            out.append(f"  {fg(120)}✔{RESET} {DIM}{but}{RESET}")
        elif x is tache_courante(state):
            out.append(f"  {fg(226)}➜{RESET} {BOLD}{but}{RESET}")
            out.append(f"     {DIM}où : cd ~/{T.name}/{d['zone']}  ·  indice : {piege(x['indice'])} (cherche dans le lexique [l]){RESET}")
        else:
            out.append(f"  {DIM}○ …{RESET}")
    return out
