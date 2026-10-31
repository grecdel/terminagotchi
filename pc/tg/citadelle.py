"""🛡 La Citadelle — cybersécurité DÉFENSIVE (docs/programme.md § 2.11, paliers C1 à C7, et § 7.5, les boîtes).

Le deuxième monde de la phase 5 (§ 7.14). Il s'ouvre selon l'arbre du Carrefour (§ 2.9) : ses prérequis sont les
niveaux 0 à 6 du tronc commun (programme.json, « mondes » → citadelle → requis), c'est-à-dire, dans l'histoire, le
nid, la bibliothèque et la cave (les cadenas) finis. Il ne ferme rien : on en sort et on y revient, l'étape est gardée.

RÈGLE D'OR (affichée à l'entrée, regle_d_or.txt) : ici, on DÉFEND. Toutes les attaques sont FAUSSES : des fichiers
texte (« virus_fictif_1.glitch », le cheval de Troie cadeau.sh qui ne s'attaque qu'au bac à sable et que le jeu ne
lance jamais), un journal inventé (adresses de documentation, RFC 5737 : elles n'appartiennent à personne), et sur PC
des processus `sleep` renommés (`exec -a miner_fictif sleep 900`) lancés par le jeu, qui s'éteignent seuls. Tout se
passe dans ~/terrain_terminagotchi/citadelle/ ; le jeu n'écrit ailleurs que dans ~/.terminagotchi (la liste des
processus fictifs). Jamais de `sudo` (chown est SIMULÉ : `citadelle chown`), jamais de réseau (le pont `curl` vise le
phare du Port sur 127.0.0.1), jamais d'outil offensif, jamais un vrai mot de passe : seulement des exemples.

LES PALIERS (cit0 à cit16) : la porte ; les cadenas (chmod) ; les habitants et leurs clubs (utilisateurs, groupes,
chown simulé) ; le masque (umask) ; le registre du gardien (C1, journaux, ponts sort/uniq) ; le ver glitch (C2, find,
pont find -newer vers le Temps) ; le cheval de Troie (C3, lire avant de lancer) ; les processus fantômes (C4, ponts
ps/kill) ; les empreintes (sha256sum) ; le Verrouilleur (C5, sauvegarde tar, restauration) ; le coffre à une clé
(openssl enc, en local) ; le faux facteur (C6, diff, pont curl du Port) ; la phrase de passe (exemples seulement) ;
trois boîtes Faciles (Énumération, Droits mal réglés, Secrets oubliés : manche Enquête puis manche Rempart, vérifiée
par l'inspecteur) ; la grande vague (C7, pare-feu en notion, tableau de garde).

LES COMMANDES DU JEU (`citadelle …`, alias posé par `tg installer`) simulent ce qu'on ne peut pas faire sans danger
(chown, les boîtes, l'inspecteur, la vague) et écrivent dans le carnet de garde (citadelle/carnet_de_garde.txt) ce
que les étapes vérifient (lignes « [inspecteur] droits (ok) »…). Mêmes règles sur Android (Citadelle.kt, vecteurs
communs donnees/citadelle/vecteurs.json).
"""
import base64
import hashlib
import io
import json
import math
import os
import pkgutil
import random
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from . import core
from .langue import t
from .plateforme import BOLD, C, DIM, IS_WIN, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "citadelle.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def journal():
    """Le registre du gardien (journaux/acces.log) : « date heure RÉSULTAT adresse porte nom », 90 lignes.
    Champ 4 = l'adresse (cut -d " " -f 4). L'intrus (203.0.113.66) rate 50 fois à la poterne, puis entre."""
    j = donnees()["journal"]
    h, m, s = (int(x) for x in j["debut"].split(":"))
    t0 = h * 3600 + m * 60 + s
    out = []
    for i in range(j["lignes"]):
        ts = t0 + i * j["pas_secondes"]
        heure = f"{ts // 3600:02d}:{ts % 3600 // 60:02d}:{ts % 60:02d}"
        if j["intrus_de"] <= i < j["intrus_a"]:
            res, adr, porte, nom = "ECHEC", j["intrus"], j["intrus_porte"], j["intrus_noms"][i % len(j["intrus_noms"])]
        elif i == j["intrus_a"]:
            res, adr, porte, nom = "OK", j["intrus"], j["intrus_porte"], "invite"
        else:
            k = i % len(j["visiteurs"])
            res = "ECHEC" if i in j["erreurs_visiteurs"] else "OK"
            adr, porte, nom = j["visiteurs"][k], j["portes"][k], j["noms"][k]
        out.append(f"{j['date']} {heure} {res} {adr} {porte} {nom}")
    return out


def echecs():
    """{adresse: nombre d'ECHEC} (ce que donne grep ECHEC | cut -d " " -f 4 | sort | uniq -c)."""
    c = {}
    for l in journal():
        m = l.split(" ")
        if m[2] == "ECHEC":
            c[m[3]] = c.get(m[3], 0) + 1
    return c


def intrus():
    return donnees()["journal"]["intrus"]


def mode_texte(mode):
    """0o640 → « rw-r----- »."""
    out = ""
    for dec in (6, 3, 0):
        b = (mode >> dec) & 7
        out += ("r" if b & 4 else "-") + ("w" if b & 2 else "-") + ("x" if b & 1 else "-")
    return out


def chmod_mode(spec, actuel, masque=0o022):
    """Le mode après `chmod spec` sur un fichier de mode actuel (0o644…), comme chmod de GNU coreutils : octal (600,
    0755) ou symbolique (u+x, go-r, a=r, o-rwx, u+x,g-w ; sans « qui », les bits du masque umask ne bougent pas).
    None si la spécification n'est pas comprise (s, t, X : pas dans le jeu)."""
    spec = (spec or "").strip()
    if re.fullmatch(r"[0-7]{1,4}", spec):
        return int(spec, 8) & 0o777
    mode = actuel & 0o777
    for clause in spec.split(","):
        m = re.fullmatch(r"([ugoa]*)((?:[-+=][rwx]*)+)", clause)
        if not m:
            return None
        qui = m.group(1)
        if not qui:
            filtre = 0o777 & ~masque
            qui = "a"
        else:
            filtre = 0o777
        cibles = 0
        for q in qui:
            cibles |= {"u": 0o700, "g": 0o070, "o": 0o007, "a": 0o777}[q]
        for op, perms in re.findall(r"([-+=])([rwx]*)", m.group(2)):
            bits = 0
            for p in perms:
                bits |= {"r": 0o444, "w": 0o222, "x": 0o111}[p]
            bits &= cibles & filtre
            if op == "+":
                mode |= bits
            elif op == "-":
                mode &= ~bits
            else:
                mode = (mode & ~(cibles & filtre)) | bits
    return mode & 0o777


def umask_mode(masque, dossier=False):
    """Le mode d'un fichier neuf (666) ou d'un dossier neuf (777) sous ce masque."""
    return (0o777 if dossier else 0o666) & ~masque & 0o777


def drapeau(graine, boite, genre):
    """Le drapeau d'une boîte pour cette partie : TG{droits-donjon-3fa2b1c9}."""
    h = hashlib.sha256(f"{graine}:{boite}:{genre}".encode("utf-8")).hexdigest()[:8]
    return f"TG{{{boite}-{genre}-{h}}}"


def facteur(graine):
    """Les 6 affirmations sur la lettre du faux facteur, mélangées pour cette partie : [(n°, id, vrai)]."""
    f = list(donnees()["facteur"])
    random.Random(f"facteur:{graine}").shuffle(f)
    return [(i + 1, x["id"], x["vrai"]) for i, x in enumerate(f)]


def bons_indices(graine):
    return sorted(n for n, _i, v in facteur(graine) if v)


def bits(force):
    """L'entropie d'un exemple (en bits) : mots × log2(taille de la liste), ou la valeur donnée (mot de passe court
    trouvé dans les listes de mots de passe connus)."""
    if "bits" in force:
        return float(force["bits"])
    return force["mots"] * math.log2(force["liste"])


def duree_essais(b, par_seconde=None):
    """Le temps (en secondes) pour essayer la MOITIÉ des possibilités (en moyenne) à par_seconde essais par seconde."""
    ps = par_seconde or donnees()["essais_par_seconde"]
    return (2 ** b) / 2 / ps


def duree_texte(s):
    """1e-3 → « moins d'une seconde » ; 3.2e9 → « 101 ans »… (clés cit.duree.*)."""
    if s < 1:
        return t("cit.duree.instant")
    for unite, n in (("an", 365.25 * 86400), ("jour", 86400), ("heure", 3600), ("minute", 60), ("seconde", 1)):
        if s >= n:
            v = s / n
            if unite == "an" and v >= 1e6:
                return t("cit.duree.millions", n=f"{v / 1e6:,.0f}".replace(",", " "))
            return t(f"cit.duree.{unite}", n=f"{v:,.0f}".replace(",", " "))
    return t("cit.duree.instant")


def inspecter(boite, modes, rotation=False, win=False):
    """La manche Rempart d'une boîte : [(règle, ok)] d'après modes = {chemin relatif: mode, ou None si absent}.
    Sous Windows, les bits rwx ne disent rien (ACL) : les règles de droits passent, avec une explication."""
    out = []
    for r in boite["rempart"]:
        if r.get("rotation"):
            out.append(("rotation", bool(rotation)))
            continue
        m = modes.get(r["chemin"])
        if r.get("absent"):
            out.append((f"absent:{r['chemin']}", m is None))
            continue
        ok = True
        for qui, dec in (("fermer_groupe", 3), ("fermer_autres", 0)):
            for p in r.get(qui, ""):
                bit = {"r": 4, "w": 2, "x": 1}[p] << dec
                if m is not None and not win and m & bit:
                    ok = False
        out.append((f"droits:{r['chemin']}", ok))
    return out


def boite(bid):
    return next((b for b in donnees()["boites"] if b["id"] == bid), None)


def tableau(glitchs, processus, secrets_ouverts):
    """Le tableau de garde : [(indicateur, valeur, vert)]."""
    return [("glitchs", glitchs, glitchs == 0), ("processus", processus, processus == 0),
            ("secrets", secrets_ouverts, secrets_ouverts == 0)]


def mots():
    return donnees()["mots"][: donnees()["mots_nb"]]


# ================================================================ l'état, le terrain, le carnet de garde
def c_(state):
    c = state.setdefault("citadelle", {})
    c.setdefault("faits", [])
    c.setdefault("proprietaires", {})
    c.setdefault("rotation", [])
    return c


def dossier():
    return core.TERRAIN / "citadelle"


CARNET = "carnet_de_garde.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok", sujet=None):
    """Une ligne « [etiquette] sujet … (mot) » dans le carnet de garde."""
    debut = rf"^\[{etiquette}\] {re.escape(sujet)}\b" if sujet else rf"^\[{etiquette}\]"
    return re.search(debut + rf".*\({mot}\)\s*$", carnet(), re.M) is not None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _lire(rel):
    """Le texte d'un fichier du terrain (UTF-8, ou UTF-16 écrit par PowerShell), ou « »."""
    try:
        b = (core.TERRAIN / rel).read_bytes()
    except OSError:
        return ""
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    return b.decode("utf-8", "replace")


def _mode(p):
    try:
        return os.stat(p).st_mode & 0o777
    except OSError:
        return None


HABITANTS = ["gardien:x:1000:1000:Gardien:/citadelle:/bin/sh", "sentinelle:x:1001:2001:Sentinelle:/citadelle/tours:/bin/sh",
             "forgeron:x:1002:1002:Forgeron:/citadelle/cuisines:/bin/sh", "visiteur:x:1003:1003:Visiteur:/citadelle/cour:/bin/false"]


def habitants():
    return list(HABITANTS)


GROUPES = ["gardiens:x:1000:gardien", "veilleurs:x:2001:gardien,sentinelle", "cuisine:x:1002:forgeron",
           "visiteurs:x:1003:visiteur"]


def _sha(texte):
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


ICONES_TRESOR = {"carte": "🗺", "couronne": "👑", "epee": "⚔"}


def tresor():
    """Les objets du trésor (le texte exact écrit, fin de ligne comprise : les empreintes sont prises dessus)."""
    return {f"tresor/{f}": t("cit.tresor", icone=ICONES_TRESOR.get(Path(f).stem, "✨"), nom=Path(f).stem) + "\n"
            for f in donnees()["tresor"]}


def parchemins():
    return {f"parchemins/{f}": t("cit.parchemin", n=i + 1, nom=Path(f).stem) + "\n"
            for i, f in enumerate(donnees()["parchemins"])}


def meubles(state):
    """Ce que le jeu pose dans la Citadelle quand elle s'ouvre : {chemin relatif au terrain: texte}."""
    m = {"citadelle/regle_d_or.txt": t("cit.meuble.regle", nom=state.get("name", "")),
         f"citadelle/{CARNET}": t("cit.meuble.carnet") + "\n",
         "citadelle/coffre.txt": t("cit.meuble.coffre"),
         "citadelle/ronde.sh": "#!/bin/sh\necho \"" + t("cit.meuble.ronde") + "\"\n",
         "citadelle/habitants.txt": "\n".join(habitants()) + "\n",
         "citadelle/groupes.txt": "\n".join(GROUPES) + "\n",
         "citadelle/tour_de_guet.txt": t("cit.meuble.tour"),
         "citadelle/journaux/acces.log": "\n".join(journal()) + "\n",
         "citadelle/cadeau.sh": "#!/bin/sh\n# " + t("cit.meuble.cadeau1") + "\ncd \"$(dirname \"$0\")\" || exit 1\n"
                                "echo \"🎁 !\"\nrm -f bac_a_sable/tresor_*.txt   # " + t("cit.meuble.cadeau3") + "\n",
         "citadelle/bac_a_sable/tresor_1.txt": t("cit.meuble.bac"),
         "citadelle/bac_a_sable/tresor_2.txt": t("cit.meuble.bac"),
         "citadelle/lettre.txt": t("cit.meuble.lettre", nom=state.get("name", "")),
         "citadelle/vraie_lettre.txt": t("cit.meuble.vraie_lettre"),
         "citadelle/lettre_du_facteur.txt": t("cit.meuble.fausse_lettre", lien=donnees()["lien_faux"]),
         "citadelle/mots.txt": "\n".join(mots()) + "\n"}
    for f in donnees()["decor"]:
        m["citadelle/" + f] = t("cit.decor", lieu=str(Path(f).parent))
    for rel, txt in tresor().items():
        m["citadelle/" + rel] = txt
    m["citadelle/empreintes_tresor.sha256"] = "".join(f"{_sha(x)}  {r}\n" for r, x in tresor().items())
    for rel, txt in parchemins().items():
        m["citadelle/" + rel] = txt
    m["citadelle/parchemins.sha256"] = "".join(f"{_sha(x)}  {r}\n" for r, x in parchemins().items())
    return m


# fichiers dont une leçon a besoin : remis s'ils disparaissent (tant que la leçon n'est pas finie)
BESOINS = {"cit0": ["regle_d_or.txt"], "cit1": ["coffre.txt", "ronde.sh"], "cit2": ["groupes.txt", "tour_de_guet.txt"],
           "cit4": ["journaux/acces.log"], "cit6": ["cadeau.sh", "bac_a_sable/tresor_1.txt", "bac_a_sable/tresor_2.txt"],
           "cit8": ["empreintes_tresor.sha256", "tresor/carte.txt", "tresor/epee.txt"],
           "cit10": ["lettre.txt"], "cit11": ["vraie_lettre.txt", "lettre_du_facteur.txt"], "cit12": ["mots.txt"]}


def _ecrire(rel, texte, mode=None, mtime=None):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and mode is not None:
            os.chmod(p, 0o600)
        p.write_text(texte, encoding="utf-8")
        if mode is not None:
            os.chmod(p, mode)
        if mtime is not None:
            os.utime(p, (mtime, mtime))
        return True
    except OSError:
        return False


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _glitchs():
    """Les fichiers *.glitch de la Citadelle (chemins relatifs à citadelle/)."""
    d = dossier()
    out = []
    if d.is_dir():
        for racine, _ds, fs in os.walk(d):
            for f in fs:
                if f.endswith(".glitch"):
                    out.append(os.path.relpath(os.path.join(racine, f), d).replace("\\", "/"))
    return sorted(out)


def meubler(state, lid, step):
    """Appelé à chaque tour par histoire.meubler pendant une leçon de la Citadelle : les droits de départ, les fichiers
    nécessaires, puis les « attaques » fictives au bon moment (glitchs, ver, processus, altération, Verrouilleur,
    boîtes, phare du Port pour le pont curl). Tout reste dans citadelle/ (et ~/.terminagotchi/citadelle)."""
    c = c_(state)
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    if not _fait(c, "modes"):
        for rel, mode in (("coffre.txt", 0o644), ("ronde.sh", 0o644), ("cadeau.sh", 0o755)):
            try:
                os.chmod(d / rel, mode)
            except OSError:
                pass
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists() and "citadelle/" + rel in tous:
            _ecrire("citadelle/" + rel, tous["citadelle/" + rel], 0o755 if rel == "cadeau.sh" else None)
    maintenant = time.time()
    if lid == "cit5":
        if not _fait(c, "glitchs"):
            for racine, _ds, fs in os.walk(d):          # tout ce qui existe déjà est « ancien »
                for f in fs:
                    try:
                        os.utime(os.path.join(racine, f), (maintenant - 3600, maintenant - 3600))
                    except OSError:
                        pass
            _ecrire("citadelle/repere.txt", t("cit.meuble.repere"), mtime=maintenant - 1)
            for g in donnees()["glitchs"]:
                _ecrire("citadelle/" + g, t("cit.meuble.glitch"))
        for i, g in enumerate(donnees()["ver"]):           # le ver se copie après chaque étape réussie
            if step >= i + 1 and not _fait(c, f"ver{i + 1}"):
                _ecrire("citadelle/" + g, t("cit.meuble.glitch"))
                core.say(state, t("cit.ver.copie", lieu=str(Path(g).parent)), 12)
    if lid == "cit6" and not (d / "cadeau.sh").exists():
        _ecrire("citadelle/cadeau.sh", tous["citadelle/cadeau.sh"], 0o755)
    if lid == "cit7" and step < 1 and not fictifs_vivants():
        lancer_fictifs(donnees()["processus"])
    if lid == "cit8" and not _fait(c, "altere"):
        _ecrire("citadelle/tresor/" + donnees()["tresor_altere"], t("cit.tresor.altere"))
    if lid == "cit9" and step >= 1 and not _fait(c, "verrou"):
        frapper()
        core.say(state, t("cit.verrou.frappe"), 16)
    if lid == "cit9" and step == 0:
        for rel, txt in parchemins().items():              # avant la sauvegarde, les parchemins sont là
            if not (d / rel).exists():
                _ecrire("citadelle/" + rel, txt)
    if lid in ("cit10", "cit11"):                          # le pont curl : le phare du Port répond sur 127.0.0.1
        from . import port
        port.assurer_phare()
    for b in donnees()["boites"]:
        if lid == "cit" + str(13 + donnees()["boites"].index(b)) and not _fait(c, "boite:" + b["id"]):
            fabriquer_boite(state, b)


def verrouiller():
    """« Le Verrouilleur » : chaque parchemin devient parchemins/<nom>.verrou (base64, mode 000) ; l'original disparaît."""
    p = dossier() / "parchemins"
    for f in donnees()["parchemins"]:
        src = p / f
        if not src.is_file():
            continue
        try:
            dst = p / (src.stem + ".verrou")
            dst.write_bytes(base64.b64encode(src.read_bytes()) + b"\n")
            os.chmod(dst, 0)
            src.unlink()
        except OSError:
            pass


def fabriquer_boite(state, b):
    """Une boîte du jeu (citadelle/boites/<id>/) : ses fichiers, ses drapeaux de cette partie, ses droits."""
    base = f"citadelle/boites/{b['id']}/"
    gr = _graine(state)
    for f in b["fichiers"]:
        dr = drapeau(gr, b["id"], f["drapeau"]) if f.get("drapeau") else ""
        txt = t(f["texte"], drapeau=dr)
        if f.get("script"):
            txt = "#!/bin/sh\n" + "\n".join("# " + l for l in txt.split("\n")) + "\necho \"" + t("cit.meuble.ronde") + "\"\n"
        _ecrire(base + f["chemin"], txt + ("" if txt.endswith("\n") else "\n"), int(f["mode"], 8))
    for rel, mode in b["dossiers"].items():
        try:
            os.chmod(core.TERRAIN / (base + rel), int(mode, 8))
        except OSError:
            pass


def modes_boite(bid):
    b = boite(bid)
    base = dossier() / "boites" / bid
    return {r["chemin"]: _mode(base / r["chemin"]) for r in b["rempart"] if r.get("chemin")}


# ---------------------------------------------------------------- les processus fictifs (PC)
def _fichier_pids():
    return core.SAVE_DIR / "citadelle" / "fictifs.json"


def _pids():
    try:
        return json.loads(_fichier_pids().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


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


def fictifs_vivants():
    """[(pid, nom)] des processus fictifs encore en vie."""
    return [(p["pid"], p["nom"]) for p in _pids() if _vivant(p["pid"], p["nom"])]


def lancer_fictifs(noms):
    """Lance des `sleep` renommés (exec -a NOM sleep 900) : ils ne font RIEN que dormir, puis s'éteignent seuls.
    Jamais sous Windows (pas d'exec -a). Renvoie les pid lancés."""
    if IS_WIN:
        return []
    out = []
    vivants = _pids()
    for nom in noms:
        try:
            p = subprocess.Popen(["bash", "-c", f"exec -a {nom} sleep {donnees()['processus_secondes']}"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        except OSError:
            continue
        out.append(p.pid)
        vivants.append({"pid": p.pid, "nom": nom})
    try:
        _fichier_pids().parent.mkdir(parents=True, exist_ok=True)
        _fichier_pids().write_text(json.dumps([x for x in vivants if _vivant(x["pid"], x["nom"])]), encoding="utf-8")
    except OSError:
        pass
    return out


def arreter_fictifs():
    """Éteint les processus fictifs encore en vie (seulement les nôtres : le nom est vérifié)."""
    for pid, _nom in fictifs_vivants():
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    for _ in range(20):
        if not fictifs_vivants():
            break
        time.sleep(0.05)
    try:
        _fichier_pids().write_text("[]", encoding="utf-8")
    except OSError:
        pass


# ================================================================ les leçons (même format que histoire.NOUVELLES)
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
CIT = r"^(tg\s+)?citadelle\s+"
CURL = r"^(curl|curl\.exe)\b"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


def _mode_rel(rel):
    return _mode(core.TERRAIN / rel)


def _fs_coffre():
    m = _mode_rel("citadelle/coffre.txt")
    return m is not None and (IS_WIN or (m & 0o077 == 0 and m & 0o600 == 0o600))


def _fs_ronde():
    m = _mode_rel("citadelle/ronde.sh")
    return m is not None and (IS_WIN or m & 0o100 != 0)


def _fs_masque():
    m = _mode_rel("citadelle/carnet_secret.txt")
    return m is not None and (IS_WIN or m & 0o077 == 0)


def _fs_intrus():
    return intrus() in _lire("citadelle/intrus.txt")


def _fs_glitch():
    return dossier().is_dir() and not _glitchs()


def _fs_cadeau():
    m = _mode_rel("citadelle/cadeau.sh")
    return m is not None and (IS_WIN or m & 0o111 == 0) and \
        all((dossier() / "bac_a_sable" / f"tresor_{i}.txt").is_file() for i in (1, 2))


def _fs_altere():
    return Path(donnees()["tresor_altere"]).stem in _lire("citadelle/altere.txt")


MARQUE_VERROU = "journaux/verrouilleur.log"


def frapper():
    """« Le Verrouilleur » frappe une seule fois, juste après la sauvegarde (le journal le note). Vrai s'il vient de frapper."""
    m = dossier() / MARQUE_VERROU
    if m.exists():
        return False
    verrouiller()
    _ecrire("citadelle/" + MARQUE_VERROU, t("cit.verrou.frappe") + "\n")
    return True


def _fs_sauvegarde():
    for nom in ("coffre_de_secours.tar.gz", "coffre_de_secours.tgz", "coffre_de_secours.tar"):
        f = dossier() / nom
        if f.is_file():
            try:
                with tarfile.open(f) as tf:
                    noms = [x.lstrip("./") for x in tf.getnames()]
                if all(f"parchemins/{p}" in noms for p in donnees()["parchemins"]):
                    frapper()                    # le Verrouilleur frappe juste après : la sauvegarde arrivait à temps
                    return True
            except (OSError, tarfile.TarError):
                pass
    return False


def _fs_restaure():
    if not (dossier() / MARQUE_VERROU).exists():
        return False
    for rel, txt in parchemins().items():
        if _lire("citadelle/" + rel).replace("\r\n", "\n") != txt:
            return False
    return True


def _fs_verrou():
    p = dossier() / "parchemins"
    return (dossier() / MARQUE_VERROU).exists() and p.is_dir() and not any(x.suffix == ".verrou" for x in p.iterdir())


def _fs_chiffre():
    """lettre.enc est un coffre openssl (« Salted__ ») qui s'ouvre avec la clé d'EXEMPLE (sinon l'étape suivante, qui
    l'ouvre avec cette clé, serait impossible : sim_citadelle.py, Léa)."""
    try:
        if (dossier() / "lettre.enc").read_bytes()[:8] != b"Salted__":
            return False
        r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(dossier() / "lettre.enc"),
                            "-pass", "pass:" + PASSE], capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _fs_processus():
    return not fictifs_vivants()


FS = {
    "cit_coffre": _fs_coffre, "cit_ronde": _fs_ronde, "cit_chown": lambda: dans_carnet("chown"),
    "cit_masque": _fs_masque, "cit_intrus": _fs_intrus, "cit_glitch": _fs_glitch, "cit_cadeau": _fs_cadeau,
    "cit_processus": _fs_processus, "cit_altere": _fs_altere, "cit_sauvegarde": _fs_sauvegarde,
    "cit_restaure": _fs_restaure, "cit_verrou": _fs_verrou, "cit_chiffre": _fs_chiffre,
    "cit_facteur": lambda: dans_carnet("facteur"),
    "cit_drapeaux_enumeration": lambda: dans_carnet("drapeaux", sujet="enumeration"),
    "cit_drapeaux_droits": lambda: dans_carnet("drapeaux", sujet="droits"),
    "cit_drapeaux_secrets": lambda: dans_carnet("drapeaux", sujet="secrets"),
    "cit_rempart_enumeration": lambda: all(ok for _r, ok in inspecter(boite("enumeration"), modes_boite("enumeration"),
                                                                       win=IS_WIN)),
    "cit_rempart_droits": lambda: all(ok for _r, ok in inspecter(boite("droits"), modes_boite("droits"), win=IS_WIN)),
    "cit_historique": lambda: not (dossier() / "boites" / "secrets" / ".historique_fictif").exists(),
    "cit_rotation": lambda: dans_carnet("rotation"),
    "cit_inspecte_enumeration": lambda: dans_carnet("inspecteur", sujet="enumeration"),
    "cit_inspecte_droits": lambda: dans_carnet("inspecteur", sujet="droits"),
    "cit_inspecte_secrets": lambda: dans_carnet("inspecteur", sujet="secrets"),
    "cit_vague": lambda: dans_carnet("vague", "repoussee"),
}
CREE = {"cit_masque": "citadelle/carnet_secret.txt", "cit_intrus": "citadelle/intrus.txt",
        "cit_altere": "citadelle/altere.txt", "cit_sauvegarde": "citadelle/coffre_de_secours.tar.gz",
        "cit_chiffre": "citadelle/lettre.enc"}

PASSE = donnees()["mot_de_passe_exemple"]
MAUVAISE = donnees()["mauvaise_cle_exemple"]
CHIFFRE = f"openssl enc -aes-256-cbc -pbkdf2 -in lettre.txt -out lettre.enc -pass pass:{PASSE}"
DECHIFFRE = "openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:{}"
OPENSSL_D = r"^openssl\s+enc\b(?=.*\s-d\b)(?=.*-aes-256-cbc\b)(?=.*-pbkdf2\b)(?=.*-in\s+\S*lettre\.enc\b)"
BOITE = r"boites/"

LECONS = {
    # la porte de la Citadelle : la règle d'or
    "cit0": {"titre": "hist.cit0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "citadelle"}), "cmd": "cd ~/terrain_terminagotchi/citadelle", "ici": "citadelle",
         "bravo": ("hist.entree.bravo", {"piece": "citadelle"})},
        _n("cit0", 1, cmd=C("ls", "dir"), re=LS, ou="citadelle"),
        _n("cit0", 2, cmd=C("cat regle_d_or.txt", "type regle_d_or.txt"), re=LIRE + r".*regle_d_or"),
    ]},
    # les cadenas : lire les droits, fermer le coffre (600), rendre la ronde exécutable (u+x)
    "cit1": {"titre": "hist.cit1.titre", "skill": None, "steps": [
        _n("cit1", 0, cmd=C("ls -l coffre.txt", "citadelle cadenas coffre.txt"),
           re=r"^(ls\s+(-\w*l\w*\s+)+.*coffre|(tg\s+)?citadelle\s+cadenas\b.*coffre)", ou="citadelle"),
        _n("cit1", 1, cmd="chmod 600 coffre.txt", fs="cit_coffre", win=False),
        _n("cit1", 2, cmd="chmod u+x ronde.sh", fs="cit_ronde", win=False),
    ]},
    # les habitants et leurs clubs (utilisateurs, groupes ; chown simulé : jamais de sudo)
    "cit2": {"titre": "hist.cit2.titre", "skill": None, "steps": [
        _n("cit2", 0, cmd=C("id", "whoami /groups"), re=r"^(id|whoami|groups)\b"),
        _n("cit2", 1, cmd=C("grep veilleurs groupes.txt", "Select-String veilleurs groupes.txt"),
           re=r"^(grep|select-string|sls|findstr)\b.*veilleurs.*groupes"),
        _n("cit2", 2, cmd="citadelle chown sentinelle:veilleurs tour_de_guet.txt", fs="cit_chown"),
    ]},
    # le masque du forgeron (umask)
    "cit3": {"titre": "hist.cit3.titre", "skill": None, "steps": [
        _n("cit3", 0, cmd="umask", re=r"^umask\s*$", win=False),
        _n("cit3", 1, cmd="(umask 077; touch carnet_secret.txt)", fs="cit_masque", win=False, ou="citadelle"),
        _n("cit3", 2, cmd="citadelle masque 077", re=CIT + r"masque\b"),
    ]},
    # C1 le registre du gardien (journaux ; ponts sort et uniq de la Salle des Données)
    "cit4": {"titre": "hist.cit4.titre", "skill": None, "steps": [
        _n("cit4", 0, cmd=C("tail -n 5 journaux/acces.log", "Get-Content journaux/acces.log -Tail 5"),
           re=r"^(tail\b.*acces\.log|(get-content|gc)\b.*acces\.log.*-tail)"),
        _n("cit4", 1, cmd="grep -c ECHEC journaux/acces.log",
           re=r"^grep\s+(-\w*c\w*\s+)+.*ECHEC.*acces\.log|^grep\b.*ECHEC.*acces\.log\s*\|\s*wc\s+-l\b", win=False),
        _n("cit4", 2, cmd='grep ECHEC journaux/acces.log | cut -d " " -f 4 | sort | uniq -c | sort -n',
           re=r"^grep\b.*ECHEC.*\|\s*cut\b.*\|\s*sort\b.*\|\s*uniq\s+-c", win=False),
        _n("cit4", 3, cmd="echo ? > intrus.txt", fs="cit_intrus", ou="citadelle"),
    ]},
    # C2 le ver glitch (find ; pont find -newer vers la Bibliothèque du Temps)
    "cit5": {"titre": "hist.cit5.titre", "skill": None, "steps": [
        _n("cit5", 0, cmd=C('find . -name "*.glitch"', "Get-ChildItem -Recurse -Force -Filter *.glitch"),
           re=r"^(find\b.*-name\s+[\"']?\*\.glitch|(get-childitem|gci|dir)\b.*glitch)", ou="citadelle"),
        _n("cit5", 1, cmd="find . -newer repere.txt", re=r"^find\b.*-newer\s+\S*repere", win=False),
        _n("cit5", 2, cmd=C('find . -name "*.glitch" -delete',
                            "Get-ChildItem -Recurse -Force -Filter *.glitch | Remove-Item -Force"), fs="cit_glitch"),
    ]},
    # C3 le cheval de Troie : lire avant de lancer
    "cit6": {"titre": "hist.cit6.titre", "skill": None, "steps": [
        _n("cit6", 0, cmd=C("cat cadeau.sh", "type cadeau.sh"), re=LIRE + r".*cadeau\.sh", ou="citadelle"),
        _n("cit6", 1, cmd=C("grep rm cadeau.sh", "Select-String rm cadeau.sh"), re=r"^(grep|select-string|sls|findstr)\b.*\brm\b.*cadeau"),
        _n("cit6", 2, cmd="chmod -x cadeau.sh", fs="cit_cadeau", win=False),
    ]},
    # C4 les processus fantômes (ponts ps et kill du Poste de Contrôle)
    "cit7": {"titre": "hist.cit7.titre", "skill": None, "steps": [
        _n("cit7", 0, cmd="ps aux | grep fictif", re=r"^ps\b.*\|\s*grep\b.*fictif", win=False),
        _n("cit7", 1, cmd="kill ?", fs="cit_processus", win=False),
        _n("cit7", 2, cmd="citadelle tableau", re=CIT + r"tableau\b"),
    ]},
    # les empreintes (sha256sum) : le trésor a-t-il été touché ?
    "cit8": {"titre": "hist.cit8.titre", "skill": None, "steps": [
        _n("cit8", 0, cmd=C("sha256sum tresor/carte.txt", "Get-FileHash tresor/carte.txt"),
           re=r"^(sha256sum\b.*tresor|get-filehash\b.*tresor)", ou="citadelle"),
        _n("cit8", 1, cmd="sha256sum -c empreintes_tresor.sha256", re=r"^sha256sum\s+(-c|--check)\b.*empreintes_tresor",
           echoue=True, win=False),
        _n("cit8", 2, cmd="echo ? > altere.txt", fs="cit_altere", ou="citadelle"),
    ]},
    # C5 le Verrouilleur (rançongiciel fictif) : sauvegarder AVANT, restaurer, vérifier
    "cit9": {"titre": "hist.cit9.titre", "skill": None, "steps": [
        _n("cit9", 0, cmd="tar czf coffre_de_secours.tar.gz parchemins", fs="cit_sauvegarde", ou="citadelle"),
        _n("cit9", 1, cmd="tar xzf coffre_de_secours.tar.gz", fs="cit_restaure"),
        _n("cit9", 2, cmd=C("rm -f parchemins/*.verrou", "Remove-Item parchemins/*.verrou -Force"), fs="cit_verrou"),
        _n("cit9", 3, cmd="sha256sum -c parchemins.sha256", re=r"^sha256sum\s+(-c|--check)\b.*parchemins\.sha256", win=False),
    ]},
    # le coffre à une clé (chiffrement symétrique, openssl, en local, une clé d'EXEMPLE)
    "cit10": {"titre": "hist.cit10.titre", "skill": None, "steps": [
        _n("cit10", 0, cmd=C("cat lettre.txt", "type lettre.txt"), re=LIRE + r".*lettre\.txt", ou="citadelle"),
        _n("cit10", 1, cmd=CHIFFRE, fs="cit_chiffre", outil="openssl"),
        _n("cit10", 2, cmd=DECHIFFRE.format(MAUVAISE), re=OPENSSL_D + r"(?!.*pass:" + re.escape(PASSE) + r"\b)",
           tout_code=True, outil="openssl"),
        _n("cit10", 3, cmd=DECHIFFRE.format(PASSE), re=OPENSSL_D + r"(?=.*pass:" + re.escape(PASSE) + r"\b)", outil="openssl"),
    ]},
    # C6 le faux facteur (hameçonnage) ; le pont curl du Port : vérifier par un autre chemin
    "cit11": {"titre": "hist.cit11.titre", "skill": None, "steps": [
        _n("cit11", 0, cmd="diff vraie_lettre.txt lettre_du_facteur.txt", re=r"^diff\b.*vraie_lettre.*lettre_du_facteur|"
           r"^diff\b.*lettre_du_facteur.*vraie_lettre", echoue=True, win=False, ou="citadelle"),
        _n("cit11", 1, cmd="curl -s http://localhost:8042/courrier", re=CURL + r".*(localhost|127\.0\.0\.1):8042/courrier\b"),
        _n("cit11", 2, cmd="citadelle facteur", re=CIT + r"facteur\s*$"),
        _n("cit11", 3, cmd="citadelle facteur ? ? ?", fs="cit_facteur"),
    ]},
    # la phrase de passe (des EXEMPLES seulement ; jamais ton vrai mot de passe)
    "cit12": {"titre": "hist.cit12.titre", "skill": None, "steps": [
        _n("cit12", 0, cmd=C("wc -l mots.txt", "(Get-Content mots.txt).Count"), re=r"^(wc\s+-l\b.*mots|.*get-content.*mots.*count)",
           ou="citadelle"),
        _n("cit12", 1, cmd=C("shuf -n 4 mots.txt", "Get-Content mots.txt | Get-Random -Count 4"),
           re=r"^(shuf\b.*-n\s*4\b.*mots|.*mots.*get-random)"),
        _n("cit12", 2, cmd="citadelle force", re=CIT + r"force\b"),
    ]},
    # boîte 1 (Facile) : Énumération — se cacher n'est pas se protéger
    "cit13": {"titre": "hist.cit13.titre", "skill": None, "steps": [
        _n("cit13", 0, cmd="citadelle boites", re=CIT + r"bo[iî]tes?\s*$", ou="citadelle"),
        _n("cit13", 1, cmd=C("ls -la boites/enumeration", "dir -Force boites/enumeration"),
           re=r"^((ls|dir)\b.*(-\w*a|-force).*enumeration|(ls|dir)\b.*enumeration.*(-\w*a|-force))"),
        _n("cit13", 2, cmd=C('grep -r "TG{" boites/enumeration', 'Get-ChildItem -Recurse -Force boites/enumeration | Select-String "TG{"'),
           re=r"(^grep\s+(-\w*r\w*\s+)+.*TG.*enumeration|select-string.*TG)"),
        _n("cit13", 3, cmd="citadelle drapeau ?", fs="cit_drapeaux_enumeration"),
        _n("cit13", 4, cmd="chmod o-rwx boites/enumeration/.cave_oubliee", fs="cit_rempart_enumeration", win=False),
        _n("cit13", 5, cmd="citadelle inspecteur enumeration", fs="cit_inspecte_enumeration", exploit="citadelle.boite"),
    ]},
    # boîte 2 (Facile) : Droits mal réglés — le moindre privilège
    "cit14": {"titre": "hist.cit14.titre", "skill": None, "steps": [
        _n("cit14", 0, cmd=C("ls -l boites/droits", "dir boites/droits"), re=r"^(ls\s+(-\w*l\w*\s+)+|dir\s+).*droits", ou="citadelle"),
        _n("cit14", 1, cmd="find boites/droits -perm -o+w", re=r"^find\b.*droits.*-perm\s+(\S*o\+?w|-?0?002\b|/0?002\b)", win=False),
        _n("cit14", 2, cmd=C('grep -r "TG{" boites/droits', 'Get-ChildItem -Recurse boites/droits | Select-String "TG{"'),
           re=r"(^grep\s+(-\w*r\w*\s+)+.*TG.*droits|select-string.*TG)"),
        _n("cit14", 3, cmd="citadelle drapeau ?", fs="cit_drapeaux_droits"),
        _n("cit14", 4, cmd="chmod o-rwx boites/droits/*", fs="cit_rempart_droits", win=False),
        _n("cit14", 5, cmd="citadelle inspecteur droits", fs="cit_inspecte_droits"),
    ]},
    # boîte 3 (Facile) : Secrets oubliés — un secret en clair, ça s'efface et ça se change
    "cit15": {"titre": "hist.cit15.titre", "skill": None, "steps": [
        _n("cit15", 0, cmd=C("ls -la boites/secrets", "dir -Force boites/secrets"),
           re=r"^((ls|dir)\b.*(-\w*a|-force).*secrets|(ls|dir)\b.*secrets.*(-\w*a|-force))", ou="citadelle"),
        _n("cit15", 1, cmd=C("grep -r mot_de_passe boites/secrets", "Get-ChildItem -Recurse -Force boites/secrets | Select-String mot_de_passe"),
           re=r"(^grep\s+(-\w*r\w*\s+)+.*mot_de_passe.*secrets|select-string.*mot_de_passe)"),
        _n("cit15", 2, cmd="citadelle drapeau ?", fs="cit_drapeaux_secrets"),
        _n("cit15", 3, cmd=C("rm boites/secrets/.historique_fictif", "Remove-Item -Force boites/secrets/.historique_fictif"),
           fs="cit_historique"),
        _n("cit15", 4, cmd="citadelle rotation secrets", fs="cit_rotation"),
        _n("cit15", 5, cmd="citadelle inspecteur secrets", fs="cit_inspecte_secrets"),
    ]},
    # C7 la grande vague : le pare-feu (notions) et le tableau de garde
    "cit16": {"titre": "hist.cit16.titre", "skill": None, "steps": [
        _n("cit16", 0, cmd=C("ss -tln", "netstat -an", mac="netstat -an -p tcp"), re=r"^(ss\s+-\w*l|netstat\b)", absent_ok=True),
        _n("cit16", 1, cmd="citadelle vague", re=CIT + r"vague\b"),
        _n("cit16", 2, cmd="citadelle tableau", fs="cit_vague", exploit="citadelle.vague"),
    ]},
}
CHAPITRE = {"id": "citadelle", "n": 12, "piece": "citadelle", "famille": "Démons", "monde": True,
            "lecons": [f"cit{i}" for i in range(17)], "objet": "bouclier_miniature", "titre": "gardien_de_la_citadelle"}


# ================================================================ l'arbre du Carrefour : quand la Citadelle s'ouvre
def _besoin():
    from . import programme
    P = programme.donnees()
    m = next((x for x in P.get("mondes", []) if x["id"] == "citadelle"), {})
    besoin = []
    for n in m.get("requis", []):
        besoin += [c for c in P.get("tronc", {}).get(n, []) if c not in besoin]
    return besoin


def ouvert(state):
    from . import histoire
    return all(histoire.fini(state, c) for c in _besoin())


def manque(state):
    from . import histoire
    return [histoire.nom_chapitre(c) for c in _besoin() if not histoire.fini(state, c)]


def annonce(state):
    """La Citadelle vient de s'ouvrir : la créature le dit une fois."""
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "citadelle" in deja or histoire.fini(state, "citadelle") or not ouvert(state):
        return False
    deja.append("citadelle")
    core.log(state, t("cit.ouvert.log"))
    core.say(state, histoire.dire(state, "cit.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
LANCE = re.compile(r"(^|[;&|]\s*)(\./|sh\s+|bash\s+|source\s+|\.\s+)\S*cadeau\.sh\b")


def indice(step, tapees):
    """Un indice de la Citadelle (histoire.indice) : un trou « ? » recopié, une clé d'exemple oubliée, un drapeau faux,
    une boîte pas encore réparée, un sudo tenté (jamais dans le jeu)."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("cit.indice.sudo")
    if cmd.startswith("chmod -x cadeau") and any(LANCE.search(l) for l in lignes):
        return t("cit.cadeau.lance")                     # le cheval lancé : jamais « ta commande marche aussi »
    if "?" in cmd.split():
        if any(re.search(r"(^|\s)\?(\s|$)|…|<", l) for l in lignes):
            return t("cit.indice.trou")
    if cmd == "kill ?" and lignes and fictifs_vivants():
        return t("cit.indice.kill")
    if cmd.startswith("citadelle drapeau"):
        der = [l for l in carnet().splitlines() if l.startswith("[drapeau]")]
        if der and der[-1].endswith("(faux)"):
            return t("cit.indice.drapeau")
        if der and der[-1].endswith("(perime)"):
            return t("cit.drapeau.perime")
        if der and der[-1].endswith("(ok)"):                # un drapeau sur deux : jamais « ta commande marche aussi »
            return t("cit.drapeau.encore")
        return None
    if cmd == "citadelle tableau" and step.get("fs") == "cit_vague":     # la vague : réparer, puis regarder le tableau
        if lignes and re.match(CIT + r"tableau\b", lignes[-1]):
            return t("cit.vague.encore")
        return t("hist.cit16.2.dit")
    if cmd.startswith("citadelle inspecteur") or str(step.get("fs", "")).startswith("cit_rempart"):
        der = [l for l in carnet().splitlines() if l.startswith("[inspecteur]")]
        if der and der[-1].endswith("(refus)"):
            return t("cit.indice.rempart")
    if cmd.startswith("citadelle facteur ?") and lignes and re.match(CIT + r"facteur\s*$", lignes[-1]):
        return t("cit.facteur.aide")                     # la liste relue : la règle (jamais « marche aussi »)
    if cmd.startswith("citadelle facteur ?"):
        der = [l for l in carnet().splitlines() if l.startswith("[facteur]")]
        if der and der[-1].endswith("(faux)"):
            return t("cit.indice.facteur")
    if cmd.startswith("openssl") and any("pass:" in l and PASSE not in l and "-d" not in l.split() for l in lignes):
        return t("cit.indice.cle")
    if "glitch" in cmd and dossier().is_dir() and _glitchs():
        return t("cit.indice.glitch", n=len(_glitchs()))
    return None


def surveiller(state, lignes):
    """À chaque tour : le cheval de Troie lancé (la créature explique, les trésors du bac à sable reviennent) ;
    un sudo tenté (jamais dans le jeu)."""
    for l in lignes or []:
        l = (l or "").strip()
        if LANCE.search(l) and dossier().is_dir():
            core.say(state, t("cit.cadeau.lance"), 16)
            from . import histoire
            les, _e = histoire.lecon_courante(state)
            if not les or les["id"] != "cit6":            # pendant cit6, c'est l'indice de l'étape qui le dit
                core.terminal(state, "⚠ " + t("cit.cadeau.lance"))
            for i in (1, 2):
                f = dossier() / "bac_a_sable" / f"tresor_{i}.txt"
                if not f.exists():
                    _ecrire(f"citadelle/bac_a_sable/tresor_{i}.txt", t("cit.meuble.bac"))
            return True
    return False


# ================================================================ les commandes du jeu : tg citadelle …
def _c(n):
    return fg(n)


QUI = ("moi", "club", "autres")


def grille(mode, avant=None, couleur=True):
    """Les trois cadenas (r w x) pour moi, mon club, les autres : allumés (la clé est donnée) ou éteints ;
    un cadenas qui change (avant → mode) est entouré."""
    out = []
    for k, q in enumerate(QUI):
        dec = 6 - 3 * k
        cases = []
        for j, p in enumerate("rwx"):
            on = bool(mode >> dec & (4 >> j))
            change = avant is not None and bool(avant >> dec & (4 >> j)) != on
            lettre = p if on else "·"
            if couleur:
                coul = _c(78) if on else DIM
                cases.append(f"{BOLD if change else ''}{coul}{'[' if change else ' '}{lettre}{']' if change else ' '}{RESET}")
            else:
                cases.append(f"{'[' if change else ' '}{lettre}{']' if change else ' '}")
        icone = ("🙂", "👥", "🌍")[k]
        out.append(f"  {icone} {t('cit.qui.' + q):<12} " + "".join(cases))
    return out


def cadenas(nom):
    p = (dossier() / nom) if not os.path.isabs(nom) else Path(nom)
    if not p.exists():
        p = Path(os.getcwd()) / nom
    m = _mode(p)
    if m is None:
        return [t("cit.inconnu", nom=nom)]
    out = [f" {_c(213)}{BOLD}🔒 " + t("cit.cadenas.titre", nom=p.name) + RESET, f"  {DIM}{mode_texte(m)}  ({m:03o}){RESET}"]
    out += grille(m)
    if IS_WIN:
        out.append(f"  {DIM}" + t("cit.cadenas.windows") + RESET)
    out.append(f"  {DIM}" + t("cit.cadenas.aide") + RESET)
    return out


def masque(arg=None):
    actuel = os.umask(0)
    os.umask(actuel)
    try:
        m = int(arg, 8) if arg else actuel
    except ValueError:
        return [t("cit.masque.aide")]
    out = [f" {_c(213)}{BOLD}🎭 " + t("cit.masque.titre", masque=f"{m:03o}") + RESET,
           "  " + t("cit.masque.calcul", masque=f"{m:03o}", mode=f"{umask_mode(m):03o}", texte=mode_texte(umask_mode(m)))]
    out += grille(umask_mode(m), 0o666)
    out.append("  " + t("cit.masque.dossier", mode=f"{umask_mode(m, True):03o}", texte=mode_texte(umask_mode(m, True))))
    out.append(f"  {DIM}" + t("cit.masque.actuel", masque=f"{actuel:04o}") + RESET)
    p = dossier() / "carnet_secret.txt"
    if p.exists():
        out.append("  " + t("cit.masque.carnet", texte=mode_texte(_mode(p) or 0)))
    noter("masque", f"{m:03o} → {umask_mode(m):03o} (ok)")
    return out


def chown(state, args):
    """chown SIMULÉ (un vrai chown demande root : jamais de sudo dans le jeu)."""
    if len(args) < 2:
        return [t("cit.chown.aide")]
    qui, fichier = args[0], args[-1]
    user, _, groupe = qui.partition(":")
    users = [h.split(":")[0] for h in habitants()]
    groupes = [g.split(":")[0] for g in GROUPES]
    if user not in users:
        return [t("cit.chown.inconnu", nom=user, liste=", ".join(users))]
    if groupe and groupe not in groupes:
        return [t("cit.chown.groupe_inconnu", nom=groupe, liste=", ".join(groupes))]
    p = dossier() / fichier
    if not p.is_file():
        return [t("cit.inconnu", nom=fichier)]
    c = c_(state)
    ancien = c["proprietaires"].get(fichier, "gardien:gardiens")
    groupe = groupe or ancien.split(":")[1]
    c["proprietaires"][fichier] = f"{user}:{groupe}"
    m = _mode(p) or 0o644
    noter("chown", f"{fichier} {user}:{groupe} (ok)")
    return [f" {_c(213)}{BOLD}🏰 " + t("cit.chown.titre") + RESET,
            f"  {DIM}{t('cit.chown.avant')}{RESET} -{mode_texte(m)} 1 {ancien.replace(':', ' ')} {p.stat().st_size} {fichier}",
            f"  {_c(78)}{t('cit.chown.apres')}{RESET} -{mode_texte(m)} 1 {user} {groupe} {p.stat().st_size} {fichier}",
            "", f"  {DIM}" + t("cit.chown.simule") + RESET]


def lignes_ps(state=None):
    viv = fictifs_vivants()
    out = [f"{'USER':<10} {'PID':>7} {'%CPU':>5}  COMMAND"]
    moi = "explorateur"
    for pid, nom in viv:
        out.append(f"{moi:<10} {pid:>7} {'0.0':>5}  {nom} {donnees()['processus_secondes']}")
    if not viv:
        out.append(f"  {DIM}" + t("cit.ps.aucun") + RESET)
    return out


def lignes_tableau(state):
    g = len(_glitchs())
    p = len(fictifs_vivants())
    sec = dossier() / donnees()["vague"]["secret"]
    m = _mode(sec)
    ouverts = 1 if (m is not None and not IS_WIN and m & 0o077) else 0
    out = [f" {_c(213)}{BOLD}🛡 " + t("cit.tableau.titre") + RESET, ""]
    for ind, val, vert in tableau(g, p, ouverts):
        out.append(f"  {(_c(78) + '✔') if vert else (_c(203) + '✖')}{RESET} {t('cit.tableau.' + ind):<34} {val}")
    c = c_(state)
    if "vague" in c["faits"]:
        if g == 0 and p == 0 and ouverts == 0:
            if not dans_carnet("vague", "repoussee"):
                noter("vague", t("cit.vague.repoussee") + " (repoussee)")
            out += ["", f"  {_c(78)}" + t("cit.vague.gagne") + RESET]
        else:
            out += ["", "  " + t("cit.vague.encore")]
    return out


def vague(state):
    """La grande vague (C7) : des glitchs, un secret lisible par tous, un processus fictif (PC). Tout est faux."""
    c = c_(state)
    v = donnees()["vague"]
    for g in v["glitchs"]:
        _ecrire("citadelle/" + g, t("cit.meuble.glitch"))
    _ecrire("citadelle/" + v["secret"], t("cit.meuble.secret_vague", exemple=PASSE), 0o644)
    if not any(n == v["processus"] for _p, n in fictifs_vivants()):     # une seule vague à la fois
        lancer_fictifs([v["processus"]])
    if "vague" not in c["faits"]:
        c["faits"].append("vague")
    noter("vague", "lancee")
    return [f" {_c(203)}{BOLD}🌊 " + t("cit.vague.titre") + RESET, "", "  " + t("cit.vague.texte"), ""] + lignes_tableau(state)


def lignes_facteur(state, choix):
    gr = _graine(state)
    f = facteur(gr)
    if not choix:
        out = [f" {_c(213)}{BOLD}✉ " + t("cit.facteur.titre") + RESET, ""]
        for n, i, _v in f:
            out.append(f"  {BOLD}{n}.{RESET} " + t("cit.facteur." + i))
        return out + ["", "  " + t("cit.facteur.aide")]
    try:
        nums = sorted({int(x) for x in choix})
    except ValueError:
        return [t("cit.facteur.aide")]
    if nums == bons_indices(gr):
        noter("facteur", " ".join(map(str, nums)) + " (ok)")
        return [f" {_c(78)}✔ " + t("cit.facteur.ok") + RESET]
    noter("facteur", " ".join(map(str, nums)) + " (faux)")
    justes = len(set(nums) & set(bons_indices(gr)))
    return [f" {_c(203)}✖ " + t("cit.facteur.faux", n=justes) + RESET]


def lignes_force():
    out = [f" {_c(213)}{BOLD}🔑 " + t("cit.force.titre") + RESET, ""]
    for f in donnees()["force"]:
        b = bits(f)
        out.append(f"  {BOLD}{t('cit.force.' + f['id'], exemple=f['exemple'])}{RESET}")
        calc = f"{f['liste']}^{f['mots']} ≈ 2^{b:.0f}" if "mots" in f else f"≈ 2^{b:.0f}"
        out.append(f"     {DIM}{calc}{RESET} → " + t("cit.force.temps", duree=duree_texte(duree_essais(b))))
    out += ["", "  " + t("cit.force.morale"), f"  {_c(203)}" + t("cit.force.jamais") + RESET]
    noter("force", "exemples (ok)")
    return out


def lignes_boites(state):
    out = [f" {_c(213)}{BOLD}📦 " + t("cit.boites.titre") + RESET, "", "  " + t("cit.boites.regle"), ""]
    for b in donnees()["boites"]:
        etat = t("cit.boites.maitrisee") if dans_carnet("inspecteur", sujet=b["id"]) else (
            t("cit.boites.rempart") if dans_carnet("drapeaux", sujet=b["id"]) else t("cit.boites.enquete"))
        out.append(f"  📦 {BOLD}{t('cit.boite.' + b['id'])}{RESET} ({t('cit.niveau.' + b['niveau'])}) — {etat}")
    for a in donnees()["a_venir"]:
        out.append(f"  {DIM}📦 {t('cit.boite.' + a)} — {t('cit.boites.bientot')}{RESET}")
    out += ["", f"  {DIM}" + t("cit.boites.loi") + RESET]
    return out


def lignes_drapeau(state, valeur):
    if not valeur:
        return [t("cit.drapeau.aide")]
    gr = _graine(state)
    v = valeur.strip()
    for b in donnees()["boites"]:
        for genre in ("entree", "donjon"):
            if v == drapeau(gr, b["id"], genre):
                if "secrets" == b["id"] and genre == "donjon" and b["id"] in c_(state)["rotation"]:
                    noter("drapeau", f"{b['id']} {genre} (perime)")
                    return [t("cit.drapeau.perime")]
                noter("drapeau", f"{b['id']} {genre} (ok)")
                out = [f" {_c(78)}🚩 " + t("cit.drapeau.ok", boite=t("cit.boite." + b["id"]), genre=t("cit.genre." + genre)) + RESET]
                faits = re.findall(rf"^\[drapeau\] {b['id']} (\w+) \(ok\)", carnet(), re.M)
                if {"entree", "donjon"} <= set(faits):
                    if not dans_carnet("drapeaux", sujet=b["id"]):
                        noter("drapeaux", f"{b['id']} (ok)")
                    out.append("  " + t("cit.drapeau.deux", boite=t("cit.boite." + b["id"])))
                else:
                    out.append("  " + t("cit.drapeau.encore"))
                return out
    noter("drapeau", f"{v[:40]} (faux)")
    return [f" {_c(203)}✖ " + t("cit.drapeau.faux") + RESET]


def lignes_inspecteur(state, bid):
    b = boite(bid or "")
    if not b:
        return [t("cit.inspecteur.aide")]
    if not dans_carnet("drapeaux", sujet=bid):
        return [t("cit.inspecteur.enquete")]
    regles = inspecter(b, modes_boite(bid), bid in c_(state)["rotation"], win=IS_WIN)
    out = [f" {_c(213)}{BOLD}🕵 " + t("cit.inspecteur.titre", boite=t("cit.boite." + bid)) + RESET, ""]
    for r, ok in regles:
        genre, _, chemin = r.partition(":")
        out.append(f"  {(_c(78) + '✔') if ok else (_c(203) + '✖')}{RESET} " +
                   t("cit.inspecteur." + genre + (".ok" if ok else ".ko"), chemin=chemin))
    if all(ok for _r, ok in regles):
        if not dans_carnet("inspecteur", sujet=bid):
            noter("inspecteur", f"{bid} (ok)")
        out += ["", f"  {_c(78)}" + t("cit.inspecteur.maitrisee", boite=t("cit.boite." + bid)) + RESET]
    else:
        noter("inspecteur", f"{bid} (refus)")
        out += ["", "  " + t("cit.inspecteur.encore")]
    return out


def rotation(state, bid):
    if bid != "secrets":
        return [t("cit.rotation.aide")]
    c = c_(state)
    if bid not in c["rotation"]:
        c["rotation"].append(bid)
    f = dossier() / "boites" / "secrets" / "config.ini"
    nouveau = "exemple-" + hashlib.sha256(f"{_graine(state)}:rotation".encode()).hexdigest()[:6]
    if f.exists():
        _ecrire("citadelle/boites/secrets/config.ini", t("cit.boite.config_neuf", exemple=nouveau), 0o600)
    noter("rotation", f"{bid} (ok)")
    return [f" {_c(78)}🔄 " + t("cit.rotation.ok") + RESET]


def phrase():
    r = random.SystemRandom()
    return [" " + "-".join(r.sample(mots(), 4)), f"  {_c(203)}" + t("cit.force.jamais") + RESET]


FORTERESSE = ['      ▲                        ▲', '     ▟█▙   ▗▄ ▗▄ ▗▄ ▗▄ ▗▄    ▟█▙', '     █▓█▄▄▄█████████████▄▄▄▄█▓█', '     █▓██████▀▀▀🛡▀▀▀███████▓█', '  ░░░████████▌     ▐████████░░░', '  👾 ░░░░░░░░▌     ▐░░░░░░░░ 👾']


def banniere(largeur=None):
    """L'entrée de la Citadelle : l'illustration B3 si elle existe (illustrations.bin, « citadelle »), sinon le REPLI
    dessiné en caractères (remparts, tours, porte, glitchs qui rôdent) : rien ne manque tant que l'image n'est pas là."""
    try:
        from . import scenes
        if scenes.disponible("citadelle"):
            return scenes.illustration("citadelle", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    return [f"  {_c(250)}{l}{RESET}" for l in FORTERESSE]


def aide():
    return banniere() + [f" {_c(213)}{BOLD}🛡 " + t("cit.aide.titre") + RESET] + ["  " + l for l in t("cit.aide.liste").split("\n")]


def commande(args, sortie=None):
    """tg citadelle [regle|cadenas|chown|masque|ps|tableau|facteur|force|phrase|boites|drapeau|inspecteur|rotation|
    vague|stop]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = (a[0].lower() if a else "aide").replace("î", "i")
    reste = a[1:]
    if sous == "stop":
        arreter_fictifs()
        out.write(t("cit.stop") + "\n")
        return
    lignes = []

    def f(st):
        c_(st)
        if sous == "regle":
            lignes.extend(banniere() + t("cit.meuble.regle", nom=st.get("name", "")).split("\n"))
        elif sous == "cadenas":
            lignes.extend(cadenas(reste[0]) if reste else [t("cit.cadenas.aide")])
        elif sous == "chown":
            lignes.extend(chown(st, reste))
        elif sous == "masque":
            lignes.extend(masque(reste[0] if reste else None))
        elif sous == "ps":
            lignes.extend(lignes_ps(st))
        elif sous == "tableau":
            lignes.extend(lignes_tableau(st))
        elif sous == "facteur":
            lignes.extend(lignes_facteur(st, [x for x in reste if x not in ("?", "…")]))
        elif sous == "force":
            lignes.extend(lignes_force())
        elif sous == "phrase":
            lignes.extend(phrase())
        elif sous in ("boites", "boite"):
            lignes.extend(lignes_boites(st))
        elif sous == "drapeau":
            lignes.extend(lignes_drapeau(st, " ".join(reste) if reste and reste != ["?"] else None))
        elif sous == "inspecteur":
            lignes.extend(lignes_inspecteur(st, reste[0] if reste else None))
        elif sous == "rotation":
            lignes.extend(rotation(st, reste[0] if reste else None))
        elif sous == "vague":
            lignes.extend(vague(st))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
