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
import textwrap
import time
from datetime import date

from . import bestiaire as B
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
    "Rencontre": [
        E("examiner", 1, "ep.rencontre.examiner", "cat",
          lambda c, l: a_tape(l, r"^\s*(cat|less|more|head|bat|type|get-content|gc)\b.*monstre_" + re.escape(c["nom"].lower()))),
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
        E("page", 3, "ep.reseau.page", "curl -o",
          lambda c, l: (c["d"] / "page.html").exists() and (c["d"] / "page.html").stat().st_size > 0),
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


def choisir_epreuves(e, premiere, rarete="commune"):
    return EPREUVES["Rencontre"] + _epreuves_famille(e, premiere, rarete)


def _epreuves_famille(e, premiere, rarete="commune"):
    fams = e.get("epreuves") or [e["famille"]]           # les commandes que cette famille aime
    pool = [x for f in fams for x in EPREUVES.get(f, []) if not (x["posix"] and IS_WIN)]
    nmax = NIVEAU_MAX[rarete]
    n = NB_TACHES[rarete]
    if rarete in ULTIMES:                     # l'épreuve ultime : sa famille + des épreuves d'ailleurs
        autres = [x for f, v in EPREUVES.items() if f not in fams and f != "Rencontre" for x in v
                  if not (x["posix"] and IS_WIN) and x["niveau"] >= 2]
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
    taches = choisir_epreuves(e, premiere, rar)
    bo = bonus(state)
    fam_de = {id(x): f for f, v in EPREUVES.items() for x in v}
    state["dressage"] = {
        "sauvage": sauvage["f"], "espece": e["nom"], "shiny": sauvage.get("shiny", False), "zone": sauvage["zone"],
        "taches": [f"{fam_de[id(x)]}:{x['id']}" for x in taches], "faites": [], "lignes": [],
        "debut": time.time(), "duree": None if premiere else DUREE[rar] + bo["temps"], "x": {}, "lecon": premiere,
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
        if any(f.endswith(":examiner") for f in d["faites"]):
            d["examine"] = True
        core.say(state, au_hasard("dress.progres", nom=d["espece"], n=n, total=len(d["taches"])), 6)
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
    if d.get("examine"):
        st_m = "  ".join(f"{fg(COUL_STAT.get(k, 250))}{B.nom_stat(k, p)}{RESET} {BOLD}{v}{RESET}"
                         for k, v in (ind.get("stats") or e["stats"]).items())
    else:
        st_m = f"{DIM}" + t("dress.stats_cachees", stats=terme("stats", p)) + RESET
    rar = d.get("rarete") or "commune"
    droite_txt = [f"{BOLD}{B.nom_affiche(e, d['shiny'], rar if d.get('examine') else None)}{RESET} "
                  f"{DIM}#{e['numero']:03d}{RESET} "
                  + (B.libelle_rarete(rar) if d.get("examine") else f"{DIM}" + t("dress.rarete_cachee") + RESET), st_m,
                  f"{fg(213)}{terme('mefiance', p)}{RESET} {jauge(mef, 100, 12, inverse=True)} {mef:3.0f} %"]
    out = ["", f" {fg(196)}{BOLD}⚔ " + t("dress.titre") + RESET, ""]
    out += _cote_a_cote(sp_f, sp_m, LG, milieu=f"{fg(196)}{BOLD}  VS  {RESET}")
    out += _cote_a_cote(gauche_txt, droite_txt, LG, milieu="      ")
    out.append("")
    chrono = (f"{fg(153)}{t('dress.temps')}{RESET} {jauge(r, d['duree'], 30)} {r:3.0f} s" if r is not None
              else f"{fg(153)}{t('dress.temps')}{RESET} {fg(147)}{t('dress.pas_de_chrono')}{RESET}")
    pastilles = " ".join(f"{fg(120)}●{RESET}" if f in d["faites"] else f"{fg(226)}◉{RESET}" if _par_id(f) is tache_courante(state)
                         else f"{fg(240)}○{RESET}" for f in d["taches"])
    out.append(f"  {chrono}    {DIM}" + t("dress.etape", n=min(n_fait + 1, n_total), total=n_total) + f"{RESET} {pastilles}")
    x = tache_courante(state)
    if x is None:
        return out
    fid = next(f for f in d["taches"] if _par_id(f) is x)
    but = t(x["but"], **termes(p), nom_min=d["espece"].lower(), nom=d["espece"])
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
    if ex:
        seuil = d["duree"] * (1 - bonus(state)["exemple"]) if d["duree"] else None
        if r is None or fid.startswith("Rencontre:") or r <= d["duree"] - seuil:
            out.append(f" {fg(120)}{BOLD}{col['tape']}{RESET}{fg(120)}{piege(ex)}{RESET}")
        else:
            out.append(f" {fg(120)}{col['tape']}{RESET}{DIM}"
                       + t("dress.exemple_dans", s=f"{r - (d['duree'] - seuil):.0f}") + RESET)
    if fid.startswith("Rencontre:examiner"):
        ou = "~/terrain_terminagotchi"
    elif fid.startswith("Rencontre:"):
        ou = t("dress.nimporte_ou")
    else:
        ou = f"~/{T.name}/{d['zone']}/{repaire(d['espece'])}"
    if ou.startswith("~/") and not fid.startswith("Rencontre:"):
        out.append(f" {fg(246)}{col['dabord']}{RESET}" + t("dress.passe_porte", cmd=f"{fg(120)}cd {ou}{RESET}"))
    else:
        out.append(f" {fg(246)}{col['ou']}{RESET}{DIM}{ou}{RESET}")
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
    f = dict(termes(p), nom=nom, nom_min=nom.lower())
    ex = ex.format(**f).replace("    puis    ", "    " + t("dress.puis") + "    ")
    return t(expl, **f), ex
