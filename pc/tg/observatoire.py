"""🔭 L'Observatoire de l'IA — lancer, vérifier et superviser des outils et des agents ; comprendre comment « apprend »
une IA (docs/programme.md § 2.17 et § 7.4).

Le septième monde de la phase 5 (§ 7.14, étape 8). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 6 du tronc commun (programme.json, « mondes » → observatoire → requis). Le chapitre et le lieu s'appellent
« observatoire » : ~/terrain_terminagotchi/observatoire/. On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, coupole.txt) :
  - AUCUNE VRAIE IA. L'assistant, le devineur de type, le devineur de mots et les agents sont de PETITS PROGRAMMES DU
    JEU : déterministes, hors ligne, sans compte, sans clé, sans réseau. Le jeu le dit à chaque fois : « les vraies IA
    sont bien plus grandes, mais le principe est juste ». Rien n'est envoyé au site, ni ailleurs.
  - Les données sont celles du JEU : les créatures du bestiaire (relues par donnees/observatoire/outils/
    fiches_observatoire.py), les vraies phrases de l'histoire (clés de langue). Jamais de données de l'enfant.
  - Les agents fictifs n'agissent que dans le terrain (terrain_terminagotchi/observatoire). Une action dangereuse
    proposée (« rm -rf », « sudo ») est du TEXTE à refuser : le jeu ne l'exécute JAMAIS, même acceptée. L'arrêt
    d'urgence (agent stop, le fichier STOP) arrête l'agent qui s'emballe ; Ctrl+C arrête celui qui tourne en rond.
  - La seule « clé » est une clé d'EXEMPLE, écrite en clair pour apprendre à la cacher ; jamais de vraie clé.

LES PALIERS (ob0 à ob9) : la porte ; O1 donner une mission (consigne floue, consigne claire, assistant > rapport.txt) ;
O2 vérifier (wc, diff, sh test.sh : l'assistant a oublié une ligne) ; O3 secrets et clés (la clé d'exemple dans un
fichier partagé, .env, chmod 600, .gitignore, export) ; O4 superviser un agent (journal, git diff, refuser rm -rf,
Ctrl+C) ; O5 apprendre avec des exemples (devine-type sur 20 créatures, il se trompe sur la 21e) ; O6 les données font
l'IA (le biais du volcan) ; O7 le devineur de mots (tr | sort | uniq -c, les paires, des phrases qui sonnent juste
mais peuvent être fausses) ; O8 l'esprit critique (5 réponses de l'assistant, 2 fausses ; ce qu'on ne confie pas ;
deepfakes, droits d'auteur, énergie) ; O9 le chef d'équipe d'agents (découper, consigne claire, arrêt d'urgence,
journal, refus, diff, tests, bilan).

Les commandes du jeu (`observatoire …`, `assistant …`, `agent …`, `devine-type …`, `devine-mot …`, alias posés par
`tg installer`) écrivent dans le carnet de l'observatoire (observatoire/carnet_de_l_observatoire.txt) ce que les
étapes vérifient. Mêmes règles sur Android (Observatoire.kt, vecteurs communs donnees/observatoire/vecteurs.json).
"""
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

from . import core
from .langue import brut, courante, t
from . import droits
from .plateforme import BOLD, DIM, RESET, SYS_WIN, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "observatoire.json").decode("utf-8"))
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


def _cjk(c):
    o = ord(c)
    return any(a <= o <= b for a, b in donnees()["cjk"])


def nettoyer(texte):
    """Les mots d'un texte, comme le devineur de mots les voit : en minuscules, la ponctuation, les symboles (et les
    émojis) remplacés par des espaces ; en chinois et en japonais, un caractère = un mot. [mot, …]"""
    out = []
    for c in (texte or "").lower():
        cat = unicodedata.category(c)
        if cat[0] in "PSZC":
            out.append(" ")
        elif _cjk(c):
            out.append(f" {c} ")
        else:
            out.append(c)
    return "".join(out).split()


def sans_champs(texte):
    """Une phrase de l'histoire sans ses {champs} (le vocabulaire du palier) : on garde les mots écrits."""
    return re.sub(r"\{[^{}]*\}", " ", texte or "")


def corpus_lignes(code=None):
    """Le texte du devineur de mots : les vraies phrases de l'histoire du jeu dans la langue, nettoyées, une par ligne."""
    out = []
    for k in donnees()["corpus"]:
        v = brut(k, code or courante())
        if isinstance(v, list):
            v = v[0] if v else ""
        m = nettoyer(sans_champs(v))
        if m:
            out.append(" ".join(m))
    return out


def mots_de(texte):
    """Les mots d'un fichier déjà nettoyé (histoire.txt) : ce que `tr ' ' '\\n'` donne, sans les lignes vides."""
    return [m for m in re.split(r"[ \n]+", texte or "") if m]


def effectifs(mots):
    """[(mot, effectif)] du plus fréquent au moins fréquent (à effectif égal, dans l'ordre des caractères)."""
    c = {}
    for m in mots:
        c[m] = c.get(m, 0) + 1
    return sorted(c.items(), key=lambda x: (-x[1], x[0]))


def paires(mots):
    """{mot: {mot suivant: effectif}} : la table du devineur de mots (le texte entier, d'une ligne à la suivante, comme
    `tail -n +2 mots.txt | paste -d ' ' mots.txt -`)."""
    p = {}
    for a, b in zip(mots, mots[1:]):
        p.setdefault(a, {})
        p[a][b] = p[a].get(b, 0) + 1
    return p


def top_paires(mots):
    """[((a, b), effectif)] des paires, de la plus fréquente à la moins fréquente."""
    out = [((a, b), n) for a, d in paires(mots).items() for b, n in d.items()]
    return sorted(out, key=lambda x: (-x[1], x[0][0], x[0][1]))


def suite(table, mot):
    """[(mot suivant, effectif)] après « mot », du plus fréquent au moins fréquent."""
    return sorted((table.get(mot) or {}).items(), key=lambda x: (-x[1], x[0]))


def phrase(table, debut, graine, n, longueur=None):
    """Une phrase du devineur de mots : à chaque pas, un mot suivant tiré au hasard SELON son effectif (les paires
    fréquentes plus souvent), avec le hasard de la partie (graine) et le numéro de la phrase (n). Elle s'arrête quand
    plus rien ne suit. [mot, …]"""
    longueur = longueur or donnees()["phrase_mots"]
    out = [debut]
    for k in range(longueur - 1):
        s = suite(table, out[-1])
        if not s:
            break
        total = sum(x for _m, x in s)
        r = _tire(graine, f"phrase:{n}:{k}", total)
        for m, x in s:
            if r < x:
                out.append(m)
                break
            r -= x
    return out


# ---------------------------------------------------------------- les données des créatures (O1, O2, O5, O6)
def _mot(cle):
    return t(cle).strip().replace(" ", "_") or cle


def label(feu):
    return _mot("ob.label.feu" if feu else "ob.label.pas_feu")


def ligne_creature(cid, avec_reponse=True):
    """« Nom famille lieu réponse » (O5, O6) : une créature du bestiaire comme le devineur la voit."""
    c = donnees()["creatures"][cid]
    out = [c["nom"], _mot("ob.famille." + c["famille"]), _mot("ob.lieu." + c["lieu"])]
    if avec_reponse:
        out.append(label(c["type"] == "feu"))
    return " ".join(out)


def texte_creatures(liste, avec_reponse=True):
    return "".join(ligne_creature(c, avec_reponse) + "\n" for c in liste)


def texte_types():
    """missions/creatures.txt (O1, O2) : « Nom Type » des 20 créatures des exemples."""
    D = donnees()
    return "".join(f"{D['creatures'][c]['nom']} {_mot('ob.type.' + D['creatures'][c]['type'])}\n" for c in D["exemples"])


def est_feu(mot):
    """Le mot de réponse veut-il dire « Feu » ? True, False, ou None (inconnu) — dans la langue ou en français."""
    m = ascii_bas((mot or "").strip())
    for code in dict.fromkeys([courante(), "fr"]):
        if m == ascii_bas((brut("ob.label.feu", code) or "").replace(" ", "_")):
            return True
        if m == ascii_bas((brut("ob.label.pas_feu", code) or "").replace(" ", "_")):
            return False
    return None


def apprendre(texte):
    """Le devineur de type apprend : il COMPTE, pour chaque famille et chaque lieu, combien d'exemples étaient « Feu »
    et combien « pas Feu ». {"total": [feu, pas], "famille": {v: [feu, pas]}, "lieu": {v: [feu, pas]}, "n": exemples}"""
    m = {"total": [0, 0], "famille": {}, "lieu": {}, "n": 0}
    for ligne in (texte or "").splitlines():
        c = ligne.split()
        if len(c) < 4 or ligne.lstrip().startswith("#"):
            continue
        f = est_feu(c[3])
        if f is None:
            continue
        k = 0 if f else 1
        m["n"] += 1
        m["total"][k] += 1
        for nom, v in (("famille", c[1]), ("lieu", c[2])):
            m[nom].setdefault(v, [0, 0])
            m[nom][v][k] += 1
    return m


def deviner(m, famille, lieu):
    """(Feu ?, votes Feu, votes pas Feu) : chaque famille et chaque lieu déjà vus « votent » avec leurs comptes ; s'ils
    ne disent rien (jamais vus, ou égalité), le devineur répond comme la majorité des exemples (égalité : pas Feu)."""
    vf = m["famille"].get(famille, [0, 0])[0] + m["lieu"].get(lieu, [0, 0])[0]
    vp = m["famille"].get(famille, [0, 0])[1] + m["lieu"].get(lieu, [0, 0])[1]
    if vf != vp:
        return vf > vp, vf, vp
    return m["total"][0] > m["total"][1], vf, vp


def cerveau_lignes(m, fichier):
    out = ["# " + t("ob.cerveau.titre", fichier=fichier, n=m["n"]), "# " + t("ob.cerveau.vraies"), ""]
    lf, lp = label(True), label(False)
    for nom in ("famille", "lieu"):
        for v, (a, b) in sorted(m[nom].items()):
            out.append(f"{_mot('ob.mot.' + nom):<10} {v:<16} {lf} {a:<3} {lp} {b}")
    out += ["", f"{_mot('ob.mot.total'):<10} {'':<16} {lf} {m['total'][0]:<3} {lp} {m['total'][1]}"]
    return out


def nombres_du_cerveau(m):
    return 2 * (len(m["famille"]) + len(m["lieu"]) + 1)


def vrai_type(nom):
    """Le type classique d'une créature du jeu (le bestiaire fait foi), par son nom ; None si inconnue."""
    for c in donnees()["creatures"].values():
        if ascii_bas(c["nom"]) == ascii_bas(nom):
            return c["type"]
    return None


def tester(m, texte):
    """[(nom, famille, lieu, devine Feu ?, vrai Feu ?, votes Feu, votes pas Feu)] pour chaque créature du fichier ; la
    vraie réponse vient de la 4e colonne si elle est là, sinon du bestiaire du jeu."""
    out = []
    for ligne in (texte or "").splitlines():
        c = ligne.split()
        if len(c) < 3 or ligne.lstrip().startswith("#"):
            continue
        d, vf, vp = deviner(m, c[1], c[2])
        v = est_feu(c[3]) if len(c) > 3 else None
        if v is None:
            ty = vrai_type(c[0])
            v = None if ty is None else ty == "feu"
        out.append((c[0], c[1], c[2], d, v, vf, vp))
    return out


# ---------------------------------------------------------------- O1, O2 : l'assistant et ses missions
VERBES = ("compter", "trier", "lister")


def _mots_cle(cle):
    out = []
    for code in dict.fromkeys([courante(), "fr"]):
        out += [ascii_bas(x) for x in (brut(cle, code) or "").split()]
    return out


def analyser(texte, fichiers, valeurs_de):
    """Ce que le petit assistant comprend d'une consigne (il ne comprend RIEN : il reconnaît quelques mots) :
    {"verbe": compter|trier|lister|None, "fichier": nom|None, "filtre": valeur|None, "manque": [quoi, fichier, filtre]}.
    fichiers : les fichiers .txt présents ; valeurs_de(fichier) : les mots de la dernière colonne de ce fichier."""
    toks = nettoyer(ascii_bas(texte))
    colle = "".join(toks)
    verbe = None
    for v in VERBES:
        mots = _mots_cle("ob.mot." + v)
        if any(w in toks or (len(w) > 1 and any(_cjk(c) for c in w) and w in colle) for w in mots):
            verbe = v
            break
    noms = re.findall(r"[A-Za-z0-9_.-]+\.txt", texte or "")
    fichier = next((n for n in noms if n in fichiers and not n.startswith("mission")), None)
    filtre = None
    if fichier:
        for v in valeurs_de(fichier):
            w = ascii_bas(v)
            if w in toks or (any(_cjk(c) for c in w) and w in colle):
                filtre = v
                break
    manque = []
    if not verbe:
        manque.append("quoi")
    if not fichier:
        manque.append("fichier")
    if verbe in ("compter", "lister") and fichier and not filtre:
        manque.append("filtre")
    return {"verbe": verbe, "fichier": fichier, "filtre": filtre, "manque": manque}


def oubli(graine, n=20):
    """La ligne que l'assistant oublie quand il trie (son défaut, exprès, pour apprendre à vérifier)."""
    return _tire(graine, "oubli", n)


def trier_assistant(lignes, graine):
    """Le tri de l'assistant : par ordre des caractères, mais UNE ligne oubliée. (lignes triées, ligne oubliée)"""
    l2 = sorted(x for x in lignes if x.strip())
    if not l2:
        return [], None
    i = oubli(graine, len(l2))
    return l2[:i] + l2[i + 1:], l2[i]


def faire_mission(a, lignes_fichier, graine):
    """(lignes produites, ligne oubliée ou None) : le travail de l'assistant pour une consigne comprise."""
    if a["verbe"] == "trier":
        return trier_assistant(lignes_fichier, graine)
    cible = ascii_bas(a["filtre"] or "")
    trouvees = [x for x in lignes_fichier if x.strip() and cible in [ascii_bas(m) for m in x.split()]]
    if a["verbe"] == "compter":
        return [t("ob.assistant.compte", fichier=a["fichier"], n=len(trouvees), filtre=a["filtre"])], None
    return trouvees, None


# ---------------------------------------------------------------- O4, O9 : les propositions des agents
def propositions(graine, cle="agent"):
    """Les propositions de l'agent, dans l'ordre de cette partie : [(n°, id, sûre ?, texte)]."""
    base = donnees()[cle]["propositions"] if cle == "agent" else donnees()["equipe"]["propositions"]
    return [(i + 1, x["id"], x["sur"], x["texte"]) for i, x in enumerate(melange(graine, "prop:" + cle, base))]


def dangereuse(graine, cle="agent"):
    return next(n for n, _i, s, _t in propositions(graine, cle) if not s)


def liste_rangee(liste):
    return sorted(dict.fromkeys(liste))


# ---------------------------------------------------------------- O5 à O9 : les cartes des quiz
def cartes(graine, sel, liste):
    """[(n°, id, réponse)] mélangées pour cette partie."""
    return [(i + 1, x["id"], str(x["rep"]).lower() if isinstance(x["rep"], bool) else x["rep"])
            for i, x in enumerate(melange(graine, sel, liste))]


def confier_cartes(graine):
    return cartes(graine, "confier", donnees()["confier"])


def nuances_cartes(graine):
    return cartes(graine, "nuances", donnees()["nuances"])


PERROQUET = [{"id": "frequent", "rep": "v"}, {"id": "verifie", "rep": "f"}, {"id": "invente", "rep": "v"}]
BIAIS = [{"id": "exemples", "rep": "o"}, {"id": "mechant", "rep": "n"}, {"id": "puissance", "rep": "n"}]


def perroquet_cartes(graine):
    return cartes(graine, "perroquet", PERROQUET)


def biais_cartes(graine):
    """Les 3 explications du biais : une seule est juste (« o »)."""
    return cartes(graine, "biais", BIAIS)


def consigne_cartes(graine):
    """Les 3 consignes pour l'équipe (a, b, c) : une seule est claire et sûre."""
    return [(chr(96 + n), i, r) for n, i, r in cartes(graine, "consigne", donnees()["equipe"]["consignes"])]


def decoupe_cartes(graine):
    """Les 3 sous-tâches de la fête, mélangées : [(n°, id)] ; la bonne réponse est l'ordre des n° (liste, compte,
    invitations)."""
    return [(i + 1, x) for i, x in enumerate(melange(graine, "decoupe", donnees()["equipe"]["decoupe"]))]


def decoupe_reponse(graine):
    c = {i: n for n, i in decoupe_cartes(graine)}
    return [str(c[i]) for i in donnees()["equipe"]["decoupe"]]


def quiz_justes(cartes_, rep, lettres):
    """(réponse bien formée, [(n°, id) justes]) ; rep : ce que l'enfant a tapé (premières lettres)."""
    r = [ascii_bas(x)[:1] for x in rep]
    if len(r) != len(cartes_) or any(not x or x not in lettres for x in r):
        return False, []
    return True, [(n, i) for (n, i, rr), x in zip(cartes_, r) if x == rr]


def questions(graine):
    """Les 5 réponses de l'assistant (O8), dans l'ordre fixe des questions : [(n°, id, fausse ?)] ; 2 sont fausses."""
    q = donnees()["questions"]
    fausses = set(melange(graine, "fausses", list(range(len(q))))[:donnees()["fausses"]])
    return [(i + 1, x["id"], i in fausses) for i, x in enumerate(q)]


def fausses_ok(rep, graine):
    """L'enfant donne les n° des réponses fausses (dans n'importe quel ordre). (toutes trouvées ?, justes, en trop)"""
    vraies = {n for n, _i, f in questions(graine) if f}
    donnees_ = {int(x) for x in rep if str(x).strip().isdigit()}
    return donnees_ == vraies, len(donnees_ & vraies), len(donnees_ - vraies)


# ---------------------------------------------------------------- la lunette (vue déployée)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def lunette_de(morceau):
    """(outil, de, vers) d'une commande (un morceau de ligne), ou None : la première règle d'observatoire.json."""
    m = (morceau or "").strip()
    for r in donnees()["lunette"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["de"], r["vers"]
    return None


def lunettes_de(ligne):
    out = []
    for m in SEPARATEURS.split(ligne or ""):
        a = lunette_de(m)
        if a:
            out.append(a)
    return out


# ================================================================ l'état, le terrain, le carnet de l'observatoire
def o_(state):
    c = state.setdefault("observatoire", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "observatoire"


CARNET = "carnet_de_l_observatoire.txt"


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


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def dernier(etiquette):
    der = [x for x in carnet().splitlines() if x.startswith(f"[{etiquette}]")]
    return der[-1] if der else None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, contenu, mode=None):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenu, encoding="utf-8")
        if mode:
            p.chmod(mode)
        return True
    except OSError:
        return False


def _lire(rel):
    try:
        return (core.TERRAIN / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def test_sh():
    """missions/test.sh (O2) : le test qui vérifie le travail de l'assistant (vrai shell, aucune commande du jeu)."""
    return ("#!/bin/sh\n# " + t("ob.test.titre") + "\n"
            "attendu=$(wc -l < creatures.txt | tr -d ' ')\nobtenu=$(wc -l < tri.txt | tr -d ' ')\n"
            "if [ \"$attendu\" = \"$obtenu\" ] && [ \"$(sort creatures.txt)\" = \"$(cat tri.txt)\" ]; then\n"
            f"  echo \"✔ {t('ob.test.reussi')}\"\nelse\n"
            f"  echo \"✖ {t('ob.test.echec', obtenu='$obtenu', attendu='$attendu')}\"\n  exit 1\nfi\n")


def tests_sh():
    """equipe/tests.sh (O9) : les tests du chef d'équipe (vrai shell)."""
    return ("#!/bin/sh\n# " + t("ob.tests.titre") + "\nr=0\n"
            "n=$(wc -l < liste.txt | tr -d ' ')\n"
            f"if [ \"$(cat compte.txt 2>/dev/null)\" = \"$n\" ]; then echo \"✔ {t('ob.tests.compte_ok')}\"; "
            f"else echo \"✖ {t('ob.tests.compte_ko', n='$n')}\"; r=1; fi\n"
            f"if [ \"$(ls invitations | wc -l | tr -d ' ')\" = \"$n\" ]; then echo \"✔ {t('ob.tests.invitations_ok')}\"; "
            f"else echo \"✖ {t('ob.tests.invitations_ko')}\"; r=1; fi\n"
            f"if [ -e STOP ]; then echo \"✔ {t('ob.tests.stop_ok')}\"; else echo \"✖ {t('ob.tests.stop_ko')}\"; r=1; fi\n"
            "exit $r\n")


def config_partagee():
    s = donnees()["secret"]
    return "\n".join(["# " + t("ob.config.titre"), "ville=Terminaville", "langue=" + courante(),
                      f"{s['variable']}={s['cle']}", "couleur=bleu"]) + "\n"


def meubles(state):
    """Ce que le jeu pose dans l'Observatoire quand il s'ouvre : {chemin relatif au terrain: contenu}."""
    return {"observatoire/coupole.txt": t("ob.meuble.coupole", nom=state.get("name", "")) + "\n",
            f"observatoire/{CARNET}": t("ob.meuble.carnet") + "\n",
            "observatoire/missions/creatures.txt": texte_types(),
            "observatoire/missions/mission_floue.txt": t("ob.mission.floue") + "\n"}


def poser_verifier():
    _ecrire("observatoire/missions/mission_tri.txt", t("ob.mission.tri") + "\n")
    _ecrire("observatoire/missions/test.sh", test_sh(), 0o755)


def poser_secrets():
    _ecrire("observatoire/secrets/config_partagee.txt", config_partagee())
    _ecrire("observatoire/secrets/LISEZMOI.txt", t("ob.meuble.secrets") + "\n")


def _git_la():
    from .vsh.git import git_present
    return git_present()


def _git(args, cwd, timeout=20):
    from .plateforme import terminal_virtuel
    if terminal_virtuel():                     # le petit git du terminal du jeu (Windows)
        from .vsh.git import git_du_jeu
        return git_du_jeu(args, cwd, timeout=timeout)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANGUAGE="C")
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def poser_chantier():
    """Le chantier de l'agent (O4) : la liste à ranger, sa copie d'avant (.avant/, pour diff), et — si git est là — un
    petit dépôt LOCAL (sans remote) avec la liste enregistrée, pour que `git diff` montre ce que l'agent a changé."""
    d = dossier() / "chantier"
    if (d / "a_nourrir.txt").exists():
        return
    liste = "".join(x + "\n" for x in donnees()["agent"]["liste"])
    _ecrire("observatoire/chantier/a_nourrir.txt", liste)
    _ecrire("observatoire/chantier/.avant/a_nourrir.txt", liste)
    _ecrire("observatoire/chantier/LISEZMOI.txt", t("ob.meuble.chantier") + "\n")
    if _git_la():
        base = ["-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
        if _git([*base, "init", "-q"], d)[0] == 0:
            _git(["config", "user.name", "L'Observatoire"], d)
            _git(["config", "user.email", "observatoire@terminagotchi.invalid"], d)
            _git(["config", "commit.gpgsign", "false"], d)
            (d / ".gitignore").write_text(".avant/\n", encoding="utf-8")
            _git(["add", "."], d)
            _git([*base, "commit", "-q", "-m", t("ob.chantier.commit")], d)


def poser_devineur():
    D = donnees()
    _ecrire("observatoire/devineur/exemples.txt", texte_creatures(D["exemples"]))
    _ecrire("observatoire/devineur/nouvelle.txt", texte_creatures([D["piege"]], avec_reponse=False))


def poser_biais():
    D = donnees()
    _ecrire("observatoire/devineur/volcan.txt", texte_creatures(D["volcan"]))
    _ecrire("observatoire/devineur/autres.txt", texte_creatures(D["autres"]))


def poser_mots():
    _ecrire("observatoire/mots/histoire.txt", "".join(x + "\n" for x in corpus_lignes()))
    _ecrire("observatoire/mots/LISEZMOI.txt", t("ob.meuble.mots") + "\n")


def poser_equipe():
    E = donnees()["equipe"]
    _ecrire("observatoire/equipe/grande_tache.txt", t("ob.meuble.tache") + "\n")
    _ecrire("observatoire/equipe/invites.txt", "".join(x + "\n" for x in E["invites"]))
    _ecrire("observatoire/equipe/tests.sh", tests_sh(), 0o755)


BESOINS = {"ob0": ["coupole.txt"], "ob1": ["missions/creatures.txt", "missions/mission_floue.txt"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de l'Observatoire : les fichiers dont la leçon a besoin (posés dès sa
    première étape, ou par sa commande d'introduction), l'agent Copieur qui s'emballe (O9), les ponts des nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire("observatoire/" + rel, tous["observatoire/" + rel])
    if lid in ("ob6", "ob8") and not (d / "devineur" / "exemples.txt").exists():
        poser_devineur()
    if lid == "ob8" and not (d / "mots" / "histoire.txt").exists():
        poser_mots()
    emballe(state)
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = o_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("ob.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("ob.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- O9 : l'agent Copieur qui s'emballe
def copies_faites():
    try:
        return sum(1 for _ in (dossier() / "equipe" / "copies").iterdir())
    except OSError:
        return 0


def emballe(state, n=None):
    """Tant que l'équipe tourne et que STOP n'est pas posé, l'agent Copieur ajoute des copies (dans equipe/copies/
    SEULEMENT, au plus copies_max) à chaque tour : c'est l'urgence d'O9. Renvoie le nombre ajouté."""
    o = o_(state)
    E = donnees()["equipe"]
    d = dossier() / "equipe"
    if not o.get("equipe_lancee") or (d / "STOP").exists():
        return 0
    deja = copies_faites()
    k = 0
    for i in range(deja, min(E["copies_max"], deja + (n or E["copies_par_tour"]))):
        if _ecrire(f"observatoire/equipe/copies/copie_{i + 1:03d}.txt", t("ob.copie.texte", n=i + 1) + "\n"):
            k += 1
    return k


# ---------------------------------------------------------------- les vérifications des étapes
def _mission_ok():
    txt = _lire("observatoire/missions/mission.txt")
    if not txt:
        return False
    a = analyser(txt, _txt_presents(dossier() / "missions"), _valeurs(dossier() / "missions"))
    return not a["manque"]


def _rapport_ok():
    txt = _lire("observatoire/missions/rapport.txt") or ""
    return bool(txt.strip()) and dans_carnet("rapport")


def _tri_ok():
    a = _lire("observatoire/missions/tri.txt")
    c = _lire("observatoire/missions/creatures.txt")
    return a is not None and c is not None and sorted(x for x in c.splitlines() if x) == \
        [x for x in a.splitlines() if x] and len([x for x in a.splitlines() if x]) == len([x for x in c.splitlines() if x])


def _secret_parti():
    txt = _lire("observatoire/secrets/config_partagee.txt")
    return txt is not None and donnees()["secret"]["variable"] not in txt and "ville=" in txt


def _env_ok():
    txt = _lire("observatoire/secrets/.env") or ""
    return re.search(rf"^{donnees()['secret']['variable']}=\S+", txt, re.M) is not None


def _env_600():
    p = dossier() / "secrets" / ".env"
    try:
        return p.is_file() and (droits.mode(p) & 0o077) == 0
    except OSError:
        return False


def _gitignore_ok():
    txt = _lire("observatoire/secrets/.gitignore") or ""
    return any(x.strip() in (".env", "/.env", "*.env") for x in txt.splitlines())


def _equipe_tests_ok():
    d = dossier() / "equipe"
    try:
        liste = [x for x in (d / "liste.txt").read_text(encoding="utf-8").splitlines() if x]
        compte = (d / "compte.txt").read_text(encoding="utf-8").strip()
        inv = sum(1 for _ in (d / "invitations").iterdir())
    except OSError:
        return False
    return compte == str(len(liste)) and inv == len(liste) and (d / "STOP").exists()


def _txt_presents(d):
    try:
        return sorted(p.name for p in d.iterdir() if p.is_file() and p.name.endswith(".txt"))
    except OSError:
        return []


def _valeurs(d):
    def v(fichier):
        try:
            txt = (d / fichier).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return list(dict.fromkeys(x.split()[-1] for x in txt.splitlines() if x.split()))
    return v


FS = {
    "ob_mission": _mission_ok,
    "ob_rapport": _rapport_ok,
    "ob_tri_fait": lambda: (dossier() / "missions" / "tri.txt").is_file() and dans_carnet("tri"),
    "ob_oubli": lambda: dans_carnet("oubli"),
    "ob_tri_ok": _tri_ok,
    "ob_secret_parti": _secret_parti,
    "ob_env": _env_ok,
    "ob_env_600": _env_600,
    "ob_gitignore": _gitignore_ok,
    "ob_cle": lambda: dans_carnet("cle"),
    "ob_agent_lance": lambda: (dossier() / "chantier" / "journal_agent.txt").is_file(),
    "ob_refus": lambda: dans_carnet("refus"),
    "ob_valide": lambda: dans_carnet("valide"),
    "ob_boucle": lambda: dans_carnet("boucle"),
    "ob_appris": lambda: re.search(r"^\[apprends\] exemples\b.*\(ok\)\s*$", carnet(), re.M) is not None,
    "ob_piege": lambda: dans_carnet("piege"),
    "ob_biais": lambda: dans_carnet("biais"),
    "ob_score_autres": lambda: (dernier("score") or "").endswith("autres (ok)"),
    "ob_mots_txt": lambda: (dossier() / "mots" / "mots.txt").is_file(),
    "ob_suite": lambda: dans_carnet("suite"),
    "ob_phrase": lambda: dans_carnet("phrase"),
    "ob_perroquet": lambda: dans_carnet("perroquet"),
    "ob_fausses": lambda: dans_carnet("fausses"),
    "ob_confier": lambda: dans_carnet("confier"),
    "ob_nuances": lambda: dans_carnet("nuances"),
    "ob_decoupe": lambda: dans_carnet("decoupe"),
    "ob_consigne": lambda: dans_carnet("consigne"),
    "ob_equipe": lambda: (dossier() / "equipe" / "journal_equipe.txt").is_file(),
    "ob_stop": lambda: (dossier() / "equipe" / "STOP").exists(),
    "ob_refus_equipe": lambda: dans_carnet("refus_equipe"),
    "ob_compte": lambda: (_lire("observatoire/equipe/compte.txt") or "").strip() == str(
        len([x for x in (_lire("observatoire/equipe/liste.txt") or "").splitlines() if x])),
    "ob_tests_ok": _equipe_tests_ok,
    "ob_bilan": lambda: (dossier() / "equipe" / "rapport_du_chef.txt").is_file(),
}
CREE = {}

# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
OB = r"^(tg\s+)?observatoire\s+"
AS = r"^(tg\s+)?assistant\s+"
AG = r"^(tg\s+)?agent\s+"
DT = r"^(tg\s+)?devine-type\s+"
DM = r"^(tg\s+)?devine-mot\s+"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


O, M, S, CH, DV, MO, EQ = ("observatoire", "observatoire/missions", "observatoire/secrets", "observatoire/chantier",
                           "observatoire/devineur", "observatoire/mots", "observatoire/equipe")
LECONS = {
    # la porte de l'Observatoire
    "ob0": {"titre": "hist.ob0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "observatoire"}), "cmd": "cd ~/terrain_terminagotchi/observatoire",
         "ici": "observatoire", "bravo": ("hist.entree.bravo", {"piece": "observatoire"})},
        _n("ob0", 1, cmd="ls", re=LS, ou=O),
        _n("ob0", 2, cmd="cat coupole.txt", re=LIRE + r".*coupole", ou=O),
    ]},
    # O1 donner une mission : une consigne est un texte ; un outil lit un fichier et écrit un fichier
    "ob1": {"titre": "hist.ob1.titre", "skill": None, "steps": [
        _n("ob1", 0, cmd="observatoire mission", re=OB + r"missions?\s*$", ou=O),
        _n("ob1", 1, cmd="cat mission_floue.txt", re=LIRE + r".*mission_floue", ou=M),
        _n("ob1", 2, cmd="assistant mission_floue.txt", re=AS + r".*mission_floue", ou=M),
        _n("ob1", 3, cmd='echo "?" > mission.txt', fs="ob_mission", ou=M),
        _n("ob1", 4, cmd="assistant mission.txt > rapport.txt", fs="ob_rapport", ou=M),
        _n("ob1", 5, cmd="cat rapport.txt", re=LIRE + r".*rapport\.txt", ou=M),
    ]},
    # O2 vérifier le travail : relire, compter, comparer, tester
    "ob2": {"titre": "hist.ob2.titre", "skill": None, "steps": [
        _n("ob2", 0, cmd="observatoire verifier", re=OB + r"v[eé]rifi", ou=M),
        _n("ob2", 1, cmd="assistant mission_tri.txt > tri.txt", fs="ob_tri_fait", ou=M),
        _n("ob2", 2, cmd="wc -l creatures.txt tri.txt", re=r"^wc\b.*creatures\.txt.*tri\.txt|^wc\b.*tri\.txt.*creatures", ou=M),
        _n("ob2", 3, cmd="sort creatures.txt | diff - tri.txt", re=r"^sort\b.*creatures.*\|\s*diff\b.*tri|^diff\b.*tri", ou=M,
           tout_code=True),
        _n("ob2", 4, cmd="sh test.sh", re=r"^(sh|bash|\./)\s*test\.sh", ou=M, tout_code=True, win=False),
        _n("ob2", 5, cmd="observatoire oubli ?", fs="ob_oubli"),
        _n("ob2", 6, cmd="sort creatures.txt > tri.txt && sh test.sh", fs="ob_tri_ok", ou=M),
    ]},
    # O3 secrets et clés : une clé d'API est un mot de passe ; jamais dans un fichier partagé
    "ob3": {"titre": "hist.ob3.titre", "skill": None, "steps": [
        _n("ob3", 0, cmd="observatoire secrets", re=OB + r"secrets?\s*$", ou=O),
        _n("ob3", 1, cmd="grep -n CLE config_partagee.txt", re=r"^grep\b.*CLE.*config_partagee", ou=S),
        _n("ob3", 2, cmd="sed -i '/CLE_API/d' config_partagee.txt", fs="ob_secret_parti", ou=S),
        _n("ob3", 3, cmd='echo "CLE_API=exemple-pas-une-vraie-cle" > .env', fs="ob_env", ou=S),
        _n("ob3", 4, cmd="chmod 600 .env", fs="ob_env_600", ou=S, win=False),
        _n("ob3", 5, cmd="echo .env >> .gitignore", fs="ob_gitignore", ou=S),
        _n("ob3", 6, cmd="export CLE_API=exemple-pas-une-vraie-cle", re=r"^export\s+CLE_API=\S", win=False),
        _n("ob3", 7, cmd="observatoire cle", fs="ob_cle", win=False),
    ]},
    # O4 superviser un agent : son journal, ce qu'il a changé, refuser le danger, Ctrl+C
    "ob4": {"titre": "hist.ob4.titre", "skill": None, "steps": [
        _n("ob4", 0, cmd="observatoire agent", re=OB + r"agents?\s*$", ou=O),
        _n("ob4", 1, cmd="agent lance", fs="ob_agent_lance", ou=CH),
        _n("ob4", 2, cmd="cat journal_agent.txt", re=LIRE + r".*journal_agent", ou=CH),
        _n("ob4", 3, cmd="git diff", re=r"^(git\s+diff\b|diff\b.*a_nourrir)", ou=CH, tout_code=True,
           repli=["diff .avant/a_nourrir.txt a_nourrir.txt"]),
        _n("ob4", 4, cmd="agent refuse ?", fs="ob_refus"),
        _n("ob4", 5, cmd="agent valide", fs="ob_valide"),
        _n("ob4", 6, cmd="agent boucle", fs="ob_boucle"),
    ]},
    # O5 apprendre avec des exemples : le devineur de type
    "ob5": {"titre": "hist.ob5.titre", "skill": None, "steps": [
        _n("ob5", 0, cmd="observatoire apprendre", re=OB + r"apprend", ou=O),
        _n("ob5", 1, cmd="head -5 exemples.txt", re=LIRE + r".*exemples\.txt", ou=DV),
        _n("ob5", 2, cmd="awk '{print $4}' exemples.txt | sort | uniq -c", re=r"^(awk|cut)\b.*exemples\.txt.*\|\s*sort\b.*\|\s*uniq\s+-c",
           ou=DV, win=False, repli=["cut -d ' ' -f 4 exemples.txt | sort | uniq -c"]),
        _n("ob5", 3, cmd="devine-type apprends exemples.txt", fs="ob_appris", ou=DV),
        _n("ob5", 4, cmd="cat cerveau.txt", re=LIRE + r".*cerveau\.txt", ou=DV),
        _n("ob5", 5, cmd="devine-type teste nouvelle.txt", re=DT + r"teste?\b.*nouvelle", ou=DV),
        _n("ob5", 6, cmd="observatoire piege ?", fs="ob_piege"),
    ]},
    # O6 les données font l'IA : le biais du volcan
    "ob6": {"titre": "hist.ob6.titre", "skill": None, "steps": [
        _n("ob6", 0, cmd="observatoire biais", re=OB + r"biais\s*$", ou=O),
        _n("ob6", 1, cmd="cut -d ' ' -f 3 volcan.txt | sort | uniq -c", re=r"^(cut|awk)\b.*volcan\.txt.*\|\s*sort\b.*\|\s*uniq\s+-c",
           ou=DV, win=False),
        _n("ob6", 2, cmd="cut -d ' ' -f 4 volcan.txt | sort | uniq -c", re=r"^(cut|awk)\b.*(-f\s*4|\$4).*volcan\.txt.*\|\s*uniq\s+-c|^(cut|awk)\b.*volcan\.txt.*(-f\s*4|\$4)",
           ou=DV, win=False),
        _n("ob6", 3, cmd="devine-type apprends volcan.txt", re=DT + r"apprend\w*\s+volcan", ou=DV),
        _n("ob6", 4, cmd="devine-type teste autres.txt", re=DT + r"teste?\b.*autres", ou=DV),
        _n("ob6", 5, cmd="observatoire biais ?", fs="ob_biais"),
        _n("ob6", 6, cmd="devine-type apprends exemples.txt", re=DT + r"apprend\w*\s+exemples", ou=DV),
        _n("ob6", 7, cmd="devine-type teste autres.txt", fs="ob_score_autres", ou=DV),
    ]},
    # O7 le devineur de mots : compter les mots et les paires de l'histoire du jeu, deviner la suite
    "ob7": {"titre": "hist.ob7.titre", "skill": None, "steps": [
        _n("ob7", 0, cmd="observatoire mots", re=OB + r"mots?\s*$", ou=O),
        _n("ob7", 1, cmd="tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -5",
           re=r"^tr\b.*histoire\.txt.*\|\s*sort\b.*\|\s*uniq\s+-c|^(cat\s+histoire\.txt\s*\|\s*)tr\b.*\|\s*uniq\s+-c", ou=MO, win=False),
        _n("ob7", 2, cmd="tr ' ' '\\n' < histoire.txt > mots.txt", fs="ob_mots_txt", ou=MO, win=False),
        _n("ob7", 3, cmd="tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -5",
           re=r"\bpaste\b.*mots\.txt.*\|\s*sort\b.*\|\s*uniq\s+-c", ou=MO, win=False),
        _n("ob7", 4, cmd="devine-mot suite ?", fs="ob_suite"),
        _n("ob7", 5, cmd="devine-mot phrase ?", fs="ob_phrase"),
        _n("ob7", 6, cmd="observatoire perroquet ? ? ?", fs="ob_perroquet"),
    ]},
    # O8 l'esprit critique : vérifier, ne pas tout confier, les nuances
    "ob8": {"titre": "hist.ob8.titre", "skill": None, "steps": [
        _n("ob8", 0, cmd="observatoire esprit", re=OB + r"esprit", ou=O),
        _n("ob8", 1, cmd="assistant questions", re=AS + r"questions?\s*$", ou=O),
        _n("ob8", 2, cmd="wc -l exemples.txt", re=r"^wc\b.*exemples\.txt", ou=DV),
        _n("ob8", 3, cmd="echo $((17 % 5))", re=r"^echo\s+\$\(\(\s*17\s*%\s*5\s*\)\)"),
        _n("ob8", 4, cmd="explique rm", re=r"^(tg\s+)?explique\s+rm\b"),
        _n("ob8", 5, cmd="assistant fausses ? ?", fs="ob_fausses", exploit="observatoire.fausses"),
        _n("ob8", 6, cmd="observatoire confier", re=OB + r"confier\s*$"),
        _n("ob8", 7, cmd="observatoire confier ? ? ? ? ? ?", fs="ob_confier"),
        _n("ob8", 8, cmd="observatoire nuances", re=OB + r"nuances?\s*$"),
        _n("ob8", 9, cmd="observatoire nuances ? ? ? ? ?", fs="ob_nuances"),
    ]},
    # O9 le chef d'équipe d'agents : découper, consigne claire, arrêt d'urgence, journal, refus, diff, tests, bilan
    "ob9": {"titre": "hist.ob9.titre", "skill": None, "steps": [
        _n("ob9", 0, cmd="observatoire equipe", re=OB + r"[eé]quipe\s*$", ou=O),
        _n("ob9", 1, cmd="observatoire decoupe ? ? ?", fs="ob_decoupe"),
        _n("ob9", 2, cmd="observatoire consigne ?", fs="ob_consigne"),
        _n("ob9", 3, cmd="agent equipe", fs="ob_equipe", ou=EQ),
        _n("ob9", 4, cmd="agent stop", fs="ob_stop", ou=EQ),
        _n("ob9", 5, cmd="ls copies | wc -l", re=r"^ls\b.*copies.*\|\s*wc\b", ou=EQ),
        _n("ob9", 6, cmd="cat journal_equipe.txt", re=LIRE + r".*journal_equipe", ou=EQ),
        _n("ob9", 7, cmd="agent refuse ?", fs="ob_refus_equipe"),
        _n("ob9", 8, cmd="diff invites.txt liste.txt", re=r"^diff\b.*invites.*liste|^diff\b.*liste.*invites", ou=EQ,
           tout_code=True),
        _n("ob9", 9, cmd="sh tests.sh", re=r"^(sh|bash|\./)\s*tests\.sh", ou=EQ, tout_code=True, win=False),
        _n("ob9", 10, cmd="wc -l < liste.txt > compte.txt", fs="ob_compte", ou=EQ),
        _n("ob9", 11, cmd="sh tests.sh", re=r"^(sh|bash|\./)\s*tests\.sh", ou=EQ, win=False),   # code 0 : tout passe
        _n("ob9", 12, cmd="agent bilan", fs="ob_bilan"),
    ]},
}
CHAPITRE = {"id": "observatoire", "n": 17, "piece": "observatoire", "famille": "Célestes", "monde": True,
            "lecons": [f"ob{i}" for i in range(10)], "objet": "loupe_de_detective", "titre": "chef_des_robots"}


# ================================================================ l'arbre du Carrefour : quand l'Observatoire s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "observatoire"), {})


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
    if "observatoire" in deja or histoire.fini(state, "observatoire") or not ouvert(state):
        return False
    deja.append("observatoire")
    core.log(state, t("ob.ouvert.log"))
    core.say(state, histoire.dire(state, "ob.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"observatoire oubli ?": "oubli", "observatoire piege ?": "piege", "observatoire biais ?": "biais",
            "observatoire perroquet ? ? ?": "perroquet", "assistant fausses ? ?": "fausses",
            "observatoire confier ? ? ? ? ? ?": "confier", "observatoire nuances ? ? ? ? ?": "nuances",
            "observatoire decoupe ? ? ?": "decoupe", "observatoire consigne ?": "consigne",
            "agent refuse ?": "refus", "devine-mot suite ?": "suite", "devine-mot phrase ?": "phrase"}
DANGER = re.compile(r"(^|[;&|]\s*)(sudo\b|rm\s+(-\w+\s+)*-\w*[rR]\w*\s+(-\w+\s+)*[\"']?(~|/|\$HOME|\*|\.\.?/?\s*$)|"
                    r"chmod\s+-R\s+777|mkfs\b|dd\s+.*of=/dev/)")


def indice(step, tapees):
    """Un indice de l'Observatoire : un sudo ou un rm -rf, un trou « ? » recopié, une mauvaise réponse, une consigne
    pas encore claire, un rapport pas redirigé, une clé copiée au mauvais endroit, un tri pas encore juste."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(DANGER.search(l) for l in lignes):
        return t("ob.indice.danger")
    if "?" in cmd.split() and any(TROU.search(l) for l in lignes if re.match(OB + "|" + AS + "|" + AG + "|" + DM, l)
                                  or l.startswith("echo ")):
        return t("ob.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = dernier(et)
        if der and not der.endswith("(ok)"):
            return t("ob.indice.rep." + et)
    fs = step.get("fs")
    if fs in ("ob_refus", "ob_refus_equipe") and any(re.match(AG + r"accepte\b", l) for l in lignes):
        return t("ob.indice.accepte")
    if fs == "ob_mission" and (_lire("observatoire/missions/mission.txt") or "").strip().strip('"') in ("?", "…"):
        return t("ob.indice.trou")
    if fs == "ob_mission" and any(re.search(r"mission\.txt", l) for l in lignes):
        a = analyser(_lire("observatoire/missions/mission.txt") or "", _txt_presents(dossier() / "missions"),
                     _valeurs(dossier() / "missions"))
        if a["manque"]:
            return t("ob.indice.mission." + a["manque"][0])
    if fs == "ob_rapport" and any(re.match(AS, l) and ">" not in l for l in lignes):
        return t("ob.indice.redirection")
    if fs == "ob_tri_fait" and any(re.match(AS, l) and ">" not in l for l in lignes):
        return t("ob.indice.redirection")
    if fs == "ob_tri_ok" and any(l.startswith("sort") or re.match(r"^(sh\s+|bash\s+|\./)test\.sh", l) for l in lignes):
        return t("ob.indice.tri")
    if fs == "ob_env_600" and any(l.startswith("chmod") for l in lignes):
        return t("ob.indice.chmod")
    if fs == "ob_boucle" and any(re.match(AG + r"boucle", l) for l in lignes):
        return t("ob.indice.ctrl_c")
    if fs == "ob_score_autres" and any(re.match(DT + r"teste?", l) for l in lignes):
        return t("ob.indice.reapprendre")
    if fs == "ob_compte" and any("compte.txt" in l for l in lignes):
        return t("ob.indice.compte")
    if fs == "ob_tests_ok" and any(re.match(r"^(sh|bash)\s+tests\.sh", l) for l in lignes):
        return t("ob.indice.tests")
    return None


def surveiller(state, lignes):
    """À chaque tour, quand l'enfant est dans l'Observatoire : une commande dangereuse tapée pour de vrai (sudo,
    rm -rf ~, chmod -R 777…) — l'alerte, à chaque fois. (Les autres mondes ont leurs propres gardes.)"""
    if not dossier().is_dir():
        return False
    from . import histoire
    if histoire.h_(state).get("chap") != "observatoire":
        return False
    for l in lignes or []:
        if DANGER.search((l or "").strip()):
            msg = t("ob.garde.danger")
            core.say(state, msg, 16)
            core.terminal(state, "⚠ " + msg)
            return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


DOME = ["        ▁▄▆██▆▄▁   ✦", "      ▄██▀▔🔭▔▀██▄", "     ▕██  ◐ ◓ ◑ ██▏  ✧", "     ▕▉▔▔▔▔▔▔▔▔▔▔▉▏",
        "    ▁▕▉ ▤ ╭──╮ ▤▉▏▁"]


def banniere(largeur=None):
    """L'entrée de l'Observatoire : l'illustration (illustrations.bin, « observatoire ») si elle existe, sinon le REPLI
    dessiné en caractères (la coupole, sa lunette, les robots-assistants qui tournent)."""
    try:
        from . import scenes
        if scenes.disponible("observatoire"):
            return scenes.illustration("observatoire", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [141, 117, 229, 78, 215]
    return [f"  {_c(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(DOME)]


def aide():
    return banniere() + [f" {_c(141)}{BOLD}🔭 " + t("ob.aide.titre") + RESET] + \
        ["  " + l for l in t("ob.aide.liste").split("\n")] + ["", f"  {DIM}" + t("ob.pas_vraie_ia") + RESET]


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def _quiz(state, rep, cartes_, lettres, etiquette, cle_titre, cle_carte, cle_aide, cle_ok, morale=None):
    """Un petit quiz (mêmes règles partout) : sans réponse, les cartes ; sinon la correction."""
    if not rep:
        out = [f" {_c(141)}{BOLD}" + t(cle_titre) + RESET, ""]
        out += [f"  {n}. " + t(f"{cle_carte}.{i}") for n, i, _r in cartes_]
        return out + ["", "  " + t(cle_aide)]
    bon, justes = quiz_justes(cartes_, rep, lettres)
    if not bon:
        return [t(cle_aide)]
    out = []
    if len(justes) == len(cartes_):
        noter(etiquette, " ".join(rep) + " (ok)")
        out.append(f" {_c(78)}✔ " + t(cle_ok) + RESET)
        if morale:
            out.append("  " + t(morale))
    else:
        noter(etiquette, " ".join(rep) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("ob.quiz.faux", n=len(justes), total=len(cartes_)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t(f"{cle_carte}.{i}.pourquoi"))
    return out


def lignes_mission():
    noter("mission", "lue (ok)")
    return [f" {_c(117)}{BOLD}📜 " + t("ob.mission.titre") + RESET, ""] + _bloc("ob.mission.texte", exemple=t("ob.mission.exemple"))


def lignes_assistant(state, args, ici):
    """assistant FICHIER : le petit assistant du jeu lit une consigne et fait le travail. Ce qu'il DIT va sur la sortie
    d'erreur (le terminal) ; ce qu'il PRODUIT va sur la sortie (qu'on peut rediriger : > rapport.txt). (dit, produit)"""
    gr = _graine(state)
    dit = [f"🤖 {t('ob.assistant.nom')}  ({t('ob.pas_vraie_ia_court')})"]
    if not args:
        return dit + ["  " + t("ob.assistant.aide")], []
    f = ici / args[0]
    try:
        consigne = f.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return dit + ["  " + t("ob.assistant.introuvable", fichier=args[0])], []
    dit.append("  " + t("ob.assistant.lu", consigne=consigne[:120]))
    a = analyser(consigne, _txt_presents(ici), _valeurs(ici))
    if a["manque"]:
        noter("assistant", f"{args[0]} floue (faux)")
        return dit + ["  ❓ " + t("ob.assistant.pas_compris")] + ["     • " + t("ob.assistant.manque." + m) for m in a["manque"]] + \
            ["  " + t("ob.assistant.conseil")], []
    try:
        lignes_f = (ici / a["fichier"]).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lignes_f = []
    produit, oubliee = faire_mission(a, lignes_f, gr)
    dit.append("  " + t("ob.assistant.compris." + a["verbe"], fichier=a["fichier"], filtre=a["filtre"] or ""))
    if a["verbe"] == "trier":
        dit.append("  ✔ " + t("ob.assistant.tri_fini", n=len(lignes_f)))
        noter("tri", f"{a['fichier']} {len(produit)} (ok)")
    else:
        dit.append("  ✔ " + t("ob.assistant.fini"))
    if args[0] == "mission.txt" or a["verbe"] != "trier":
        noter("rapport", f"{a['verbe']} {a['fichier']} (ok)")
    return dit, produit


def lignes_verifier():
    poser_verifier()
    noter("verifier", "lu (ok)")
    return [f" {_c(229)}{BOLD}🔍 " + t("ob.verifier.titre") + RESET, ""] + _bloc("ob.verifier.texte")


def lignes_oubli(state, arg):
    if not arg:
        return [t("ob.oubli.aide")]
    c = _lire("observatoire/missions/creatures.txt") or texte_types()
    _l, oubliee = trier_assistant(c.splitlines(), _graine(state))
    nom = (oubliee or "").split()[0] if oubliee else ""
    if ascii_bas(arg.strip()) == ascii_bas(nom):
        noter("oubli", f"{nom} (ok)")
        return [f" {_c(78)}✔ " + t("ob.oubli.ok", nom=nom) + RESET, "  " + t("ob.oubli.morale")]
    noter("oubli", f"{ascii_bas(arg)[:30]} (faux)")
    return [f" {_c(203)}✖ " + t("ob.indice.rep.oubli") + RESET]


def lignes_secrets():
    poser_secrets()
    noter("secrets", "lu (ok)")
    return [f" {_c(215)}{BOLD}🔑 " + t("ob.secrets.titre") + RESET, ""] + _bloc("ob.secrets.texte")


def lignes_cle():
    """observatoire cle : la clé est-elle dans l'environnement (export) ? Le jeu ne l'affiche jamais en entier."""
    v = os.environ.get(donnees()["secret"]["variable"])
    if not v:
        noter("cle", "absente (faux)")
        return [f" {_c(215)}✖ " + t("ob.cle.absente") + RESET]
    noter("cle", "environnement (ok)")
    return [f" {_c(78)}✔ " + t("ob.cle.ok", debut=v[:3], n=len(v)) + RESET, "  " + t("ob.cle.morale")]


def lignes_agent_intro():
    poser_chantier()
    noter("agent", "lu (ok)")
    return [f" {_c(78)}{BOLD}🤖 " + t("ob.agent.titre") + RESET, ""] + _bloc("ob.agent.texte")


def journal_agent(state):
    D = donnees()["agent"]
    liste = D["liste"]
    rangee = liste_rangee(liste)
    out = ["# " + t("ob.journal.titre"), "",
           "[" + t("ob.journal.fait") + "] " + t("ob.journal.lu", n=len(liste)),
           "[" + t("ob.journal.fait") + "] " + t("ob.journal.trie"),
           "[" + t("ob.journal.fait") + "] " + t("ob.journal.doublons", n=len(liste) - len(rangee))]
    for n, i, _s, txt in propositions(_graine(state)):
        out.append(f"[{t('ob.journal.propose')} {n}] {txt}    ({t('ob.prop.' + i)})")
    out += ["", "[" + t("ob.journal.attend") + "] " + t("ob.journal.comment")]
    return out


def lignes_agent_lance(state):
    poser_chantier()
    d = dossier() / "chantier"
    liste = donnees()["agent"]["liste"]
    _ecrire("observatoire/chantier/a_nourrir.txt", "".join(x + "\n" for x in liste_rangee(liste)))
    _ecrire("observatoire/chantier/journal_agent.txt", "\n".join(journal_agent(state)) + "\n")
    noter("lance", "chantier (ok)")
    return [f" {_c(78)}🤖 " + t("ob.agent.lance") + RESET] + ["  " + l for l in journal_agent(state)[2:]] + \
        ["", "  " + t("ob.agent.relis", git="git diff" if (d / ".git").is_dir() else "diff .avant/a_nourrir.txt a_nourrir.txt")]


def _prop_par_numero(state, arg, cle):
    try:
        k = int(str(arg).strip())
    except (TypeError, ValueError):
        return None
    return next((p for p in propositions(_graine(state), cle) if p[0] == k), None)


def lignes_refuse(state, arg, cle="agent"):
    eti = "refus" if cle == "agent" else "refus_equipe"
    if not arg:
        return [t("ob.refuse.aide")]
    p = _prop_par_numero(state, arg, cle)
    if not p:
        return [t("ob.refuse.aide")]
    n, i, sur, _txt = p
    if sur:
        noter(eti, f"{n} {i} (faux)")
        return [f" {_c(215)}↺ " + t("ob.refuse.sure", n=n) + RESET]
    noter(eti, f"{n} {i} (ok)")
    return [f" {_c(78)}✔ " + t("ob.refuse.ok", n=n) + RESET, "  " + t("ob.refuse.morale")]


def lignes_accepte(state, arg, cle="agent"):
    p = _prop_par_numero(state, arg, cle)
    if not p:
        return [t("ob.accepte.aide")]
    n, i, sur, _txt = p
    if not sur:
        noter("accepte_danger", f"{n} {i} (faux)")
        return [f" {_c(203)}⛔ " + t("ob.accepte.jamais", n=n) + RESET, "  " + t("ob.accepte.jamais2")]
    base = "chantier" if cle == "agent" else "equipe"
    if i == "copie":
        _ecrire(f"observatoire/{base}/sauvegarde.txt", _lire(f"observatoire/{base}/a_nourrir.txt") or "")
    elif i == "note":
        _ecrire(f"observatoire/{base}/note.txt", "ok\n")
    elif i == "resume":
        _ecrire(f"observatoire/{base}/resume.txt", "fete\n")
    elif i == "sauvegarde":
        _ecrire(f"observatoire/{base}/sauvegarde_liste.txt", _lire(f"observatoire/{base}/liste.txt") or "")
    noter("accepte", f"{n} {i} (ok)")
    return [f" {_c(78)}✔ " + t("ob.accepte.ok", n=n) + RESET]


def lignes_valide():
    if not dans_carnet("refus"):
        noter("valide", "trop tot (faux)")
        return [f" {_c(215)}✋ " + t("ob.valide.pas_encore") + RESET]
    noter("valide", "chantier (ok)")
    return [f" {_c(78)}✔ " + t("ob.valide.ok") + RESET, "  " + t("ob.valide.morale")]


def boucle(sortie, pause=None):
    """agent boucle : un agent qui tourne en rond (sur PC, un vrai programme au premier plan). Ctrl+C l'arrête : c'est
    la bonne réponse. Il s'arrête seul après boucle_tours (sa limite). Hors du verrou de la sauvegarde."""
    D = donnees()["agent"]
    pause = D["boucle_pause"] if pause is None else pause
    sortie.write(f"🤖 {t('ob.boucle.debut')}\n")
    sortie.flush()
    try:
        for k in range(D["boucle_tours"]):
            sortie.write(f"  🔁 {t('ob.boucle.tour', n=k + 1)}\n")
            sortie.flush()
            time.sleep(pause)
    except KeyboardInterrupt:
        noter("boucle", "ctrl_c (ok)")
        sortie.write(f"\n⏹ {t('ob.boucle.arrete')}\n")
        return True
    noter("boucle", "limite (fin)")
    sortie.write(f"⏱ {t('ob.boucle.limite')}\n")
    return False


# ---------------------------------------------------------------- O5, O6 : le devineur de type
def lignes_apprendre():
    poser_devineur()
    noter("apprendre", "lu (ok)")
    return [f" {_c(215)}{BOLD}🧠 " + t("ob.apprendre.titre") + RESET, ""] + _bloc("ob.apprendre.texte")


def lignes_devine_type(state, args, ici):
    o = o_(state)
    if not args:
        return [f" {_c(215)}{BOLD}🧠 devine-type{RESET}  ({t('ob.pas_vraie_ia_court')})"] + _bloc("ob.devine.aide")
    sous = ascii_bas(args[0])
    if sous.startswith("apprend") or sous in ("learn", "entraine"):
        if len(args) < 2:
            return [t("ob.devine.aide_apprends")]
        try:
            txt = (ici / args[1]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [t("ob.assistant.introuvable", fichier=args[1])]
        m = apprendre(txt)
        if not m["n"]:
            return [t("ob.devine.vide", fichier=args[1])]
        o["modele"] = m
        o["modele_de"] = args[1]
        try:
            (ici / "cerveau.txt").write_text("\n".join(cerveau_lignes(m, args[1])) + "\n", encoding="utf-8")
        except OSError:
            pass
        noter("apprends", f"{os.path.splitext(args[1])[0]} {m['n']} (ok)")
        return [f" {_c(78)}✔ " + t("ob.devine.appris", n=m["n"], fichier=args[1], k=nombres_du_cerveau(m)) + RESET,
                "  " + t("ob.devine.cerveau")]
    if sous.startswith("test"):
        m = o.get("modele")
        if not m:
            return [t("ob.devine.pas_appris")]
        if len(args) < 2:
            return [t("ob.devine.aide_teste")]
        try:
            txt = (ici / args[1]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [t("ob.assistant.introuvable", fichier=args[1])]
        res = tester(m, txt)
        out = [f" {_c(215)}{BOLD}🧠 " + t("ob.devine.teste", fichier=args[1], de=o.get("modele_de", "?")) + RESET, ""]
        justes = 0
        for nom, fam, lieu, d, v, vf, vp in res:
            ok = v is not None and d == v
            justes += ok
            marque = f"{_c(78)}✔{RESET}" if ok else (f"{_c(203)}✖{RESET}" if v is not None else "?")
            out.append(f"  {marque} {nom:<14} → {label(d):<9} " + DIM + t("ob.devine.votes", f=vf, p=vp) + RESET +
                       ("" if v is None or ok else "  " + t("ob.devine.vrai", rep=label(v))))
        out.append("")
        base = os.path.splitext(args[1])[0]
        if res:
            pc = justes * 100 // len(res)
            out.append("  " + t("ob.devine.score", j=justes, n=len(res), pc=pc))
            if base == "nouvelle" and justes < len(res):
                out += ["  " + t("ob.devine.trompe"), "  " + t("ob.devine.piege_question")]
            if base == "autres":
                bon = justes == len(res)
                noter("score", f"{justes}/{len(res)} autres ({'ok' if bon else 'faux'})")
                out.append("  " + t("ob.devine.autres_ok" if bon else "ob.devine.autres_biais"))
        noter("teste", f"{base} {justes}/{len(res)} (ok)")
        return out
    # devine-type NOM : une seule créature, par son nom
    m = o.get("modele")
    if not m:
        return [t("ob.devine.pas_appris")]
    nom = args[0]
    c = next((x for x in donnees()["creatures"].values() if ascii_bas(x["nom"]) == ascii_bas(nom)), None)
    if not c:
        return [t("ob.devine.inconnue", nom=nom)]
    d, vf, vp = deviner(m, _mot("ob.famille." + c["famille"]), _mot("ob.lieu." + c["lieu"]))
    return [f"  🧠 {c['nom']} → {label(d)}  " + DIM + t("ob.devine.votes", f=vf, p=vp) + RESET]


def lignes_piege(arg):
    if not arg:
        return [t("ob.piege.aide")]
    a = ascii_bas(arg.strip())
    bonnes = {"1", ascii_bas(t("ob.mot.famille")), ascii_bas(brut("ob.mot.famille", "fr") or "famille")}
    if a in bonnes:
        noter("piege", "famille (ok)")
        return [f" {_c(78)}✔ " + t("ob.piege.ok") + RESET, "  " + t("ob.piege.morale")]
    noter("piege", f"{a[:20]} (faux)")
    return [f" {_c(203)}✖ " + t("ob.indice.rep.piege") + RESET]


def lignes_biais_intro():
    poser_biais()
    noter("biais_lu", "lu (ok)")
    return [f" {_c(215)}{BOLD}🔦 " + t("ob.biais.titre") + RESET, ""] + _bloc("ob.biais.texte")


def lignes_biais(state, arg):
    c = biais_cartes(_graine(state))
    if not arg:
        return [f" {_c(141)}{BOLD}" + t("ob.biais.question") + RESET] + [f"  {n}. " + t("ob.biais." + i) for n, i, _r in c] + \
            ["", "  " + t("ob.biais.aide")]
    bon = next((n for n, _i, r in c if r == "o"), None)
    if arg.strip() == str(bon):
        noter("biais", f"{bon} (ok)")
        return [f" {_c(78)}✔ " + t("ob.biais.ok") + RESET] + _bloc("ob.biais.morale")
    noter("biais", f"{arg.strip()[:5]} (faux)")
    return [f" {_c(203)}✖ " + t("ob.indice.rep.biais") + RESET, ""] + lignes_biais(state, None)


# ---------------------------------------------------------------- O7 : le devineur de mots
def _table_mots(ici=None):
    """Les mots sur lesquels le devineur s'entraîne : mots/histoire.txt s'il est là (le texte que l'enfant voit), sinon
    les phrases de l'histoire du jeu."""
    txt = None
    for p in ([ici / "histoire.txt"] if ici else []) + [dossier() / "mots" / "histoire.txt"]:
        try:
            txt = p.read_text(encoding="utf-8")
            break
        except OSError:
            continue
    if txt is None:
        txt = "\n".join(corpus_lignes())
    return mots_de(txt)


def sans_espaces(code=None):
    """Vrai pour une langue écrite sans espaces entre les mots (chinois, japonais) : le devineur y compte les caractères."""
    return any(_cjk(c) for l in corpus_lignes(code) for c in l)


def lignes_mots_intro():
    poser_mots()
    noter("mots", "lu (ok)")
    return [f" {_c(141)}{BOLD}🦜 " + t("ob.mots.titre") + RESET, ""] + _bloc("ob.mots.texte") + \
        (["", "  " + t("ob.mots.caracteres")] if sans_espaces() else [])


def lignes_devine_mot(state, args, ici):
    o = o_(state)
    if not args:
        return [f" {_c(141)}{BOLD}🦜 devine-mot{RESET}  ({t('ob.pas_vraie_ia_court')})"] + _bloc("ob.devinemot.aide")
    sous = ascii_bas(args[0])
    mots = _table_mots(ici)
    table = paires(mots)
    if sous in ("suite", "next", "suivant"):
        if len(args) < 2:
            return [t("ob.devinemot.aide_suite")]
        mot = args[1].lower()
        s = suite(table, mot)
        if not s:
            noter("suite", f"{mot[:20]} (inconnu)")
            return [f" {_c(215)}? " + t("ob.devinemot.inconnu", mot=mot) + RESET]
        total = sum(n for _m, n in s)
        out = [f" {_c(141)}{BOLD}🦜 " + t("ob.devinemot.apres", mot=mot, total=total) + RESET]
        for m2, n in s[:8]:
            out.append(f"  {m2:<14} {n:>3}  " + "█" * max(1, n * 20 // total) + f"  {n * 100 // total} %")
        out += ["", "  " + t("ob.devinemot.proba", mot=mot, suivant=s[0][0], n=s[0][1], total=total,
                               pc=s[0][1] * 100 // total)]
        noter("suite", f"{mot} (ok)")
        return out
    if sous in ("phrase", "sentence"):
        if len(args) < 2:
            return [t("ob.devinemot.aide_phrase")]
        mot = args[1].lower()
        if mot not in table:
            noter("phrase", f"{mot[:20]} (inconnu)")
            return [f" {_c(215)}? " + t("ob.devinemot.inconnu", mot=mot) + RESET]
        n = o.get("phrases", 0)
        o["phrases"] = n + 1
        p = phrase(table, mot, _graine(state), n)
        noter("phrase", f"{' '.join(p)} (ok)")
        return [f" {_c(141)}🦜 « {' '.join(p)} … »{RESET}", "", "  " + t("ob.devinemot.sonne"),
                f"  {DIM}" + t("ob.devinemot.encore", mot=mot) + RESET, ""] + \
            _quiz(state, [], perroquet_cartes(_graine(state)), "vf", "perroquet", "ob.perroquet.titre", "ob.perroquet",
                  "ob.perroquet.aide", "ob.perroquet.ok")
    return [t("ob.devinemot.aide_suite")]


# ---------------------------------------------------------------- O8 : l'esprit critique
def reponse_assistant(qid, fausse, mots=None):
    """La réponse (vraie ou fausse) de l'assistant à une question. Les nombres sont CALCULÉS sur les fichiers du jeu."""
    D = donnees()
    if qid == "lignes":
        n = len(D["exemples"])
        return str(n + 4 if fausse else n)
    if qid == "modulo":
        return "3" if fausse else "2"
    if qid == "mot":
        e = effectifs(mots if mots is not None else mots_de("\n".join(corpus_lignes())))
        if not e:
            return "?"
        return e[3][0] if fausse and len(e) > 3 else e[0][0]
    return t(f"ob.q.{qid}.{'faux' if fausse else 'vrai'}")


def lignes_questions(state):
    out = [f" {_c(117)}{BOLD}🤖 " + t("ob.questions.titre") + RESET, f"  {DIM}" + t("ob.pas_vraie_ia") + RESET, ""]
    mots = _table_mots()
    for n, qid, fausse in questions(_graine(state)):
        out.append(f"  {BOLD}{n}.{RESET} " + t(f"ob.q.{qid}"))
        out.append(f"     🤖 {reponse_assistant(qid, fausse, mots)}  " + DIM + t("ob.questions.sur") + RESET)
    noter("questions", "lues (ok)")
    return out + ["", "  " + t("ob.questions.aide")]


def lignes_fausses(state, rep):
    if len([x for x in rep if str(x).strip().isdigit()]) < 1:
        return [t("ob.fausses.aide")]
    tout, justes, trop = fausses_ok(rep, _graine(state))
    if tout:
        noter("fausses", " ".join(rep) + " (ok)")
        out = [f" {_c(78)}✔ " + t("ob.fausses.ok") + RESET]
        for n, qid, fausse in questions(_graine(state)):
            if fausse:
                out.append(f"  {n}. " + t(f"ob.q.{qid}.pourquoi"))
        return out + ["  " + t("ob.fausses.morale")]
    noter("fausses", " ".join(rep) + " (faux)")
    return [f" {_c(203)}✖ " + t("ob.fausses.faux", j=justes, total=donnees()["fausses"], trop=trop) + RESET]


def lignes_esprit():
    noter("esprit", "lu (ok)")
    return [f" {_c(117)}{BOLD}🕵 " + t("ob.esprit.titre") + RESET, ""] + _bloc("ob.esprit.texte")


# ---------------------------------------------------------------- O9 : le chef d'équipe
def lignes_equipe_intro(state):
    poser_equipe()
    noter("equipe_lu", "lu (ok)")
    return [f" {_c(78)}{BOLD}👩‍✈️ " + t("ob.equipe.titre") + RESET, ""] + _bloc("ob.equipe.texte") + [""] + lignes_decoupe(state, [])


def lignes_decoupe(state, rep):
    gr = _graine(state)
    c = decoupe_cartes(gr)
    if not rep:
        return [f" {_c(141)}{BOLD}" + t("ob.decoupe.titre") + RESET, ""] + [f"  {n}. " + t("ob.decoupe." + i) for n, i in c] + \
            ["", "  " + t("ob.decoupe.aide")]
    if [x.strip() for x in rep] == decoupe_reponse(gr):
        noter("decoupe", " ".join(rep) + " (ok)")
        return [f" {_c(78)}✔ " + t("ob.decoupe.ok") + RESET, "  " + t("ob.decoupe.morale"), ""] + lignes_consigne(state, None)
    noter("decoupe", " ".join(rep) + " (faux)")
    return [f" {_c(203)}✖ " + t("ob.indice.rep.decoupe") + RESET]


def lignes_consigne(state, arg):
    c = consigne_cartes(_graine(state))
    if not arg:
        return [f" {_c(141)}{BOLD}" + t("ob.consigne.titre") + RESET, ""] + [f"  {n}) " + t("ob.consigne." + i) for n, i, _r in c] + \
            ["", "  " + t("ob.consigne.aide")]
    a = ascii_bas(arg.strip())[:1]
    bon = next(n for n, _i, r in c if r == "true")
    if a == bon:
        noter("consigne", f"{bon} (ok)")
        return [f" {_c(78)}✔ " + t("ob.consigne.ok") + RESET, "  " + t("ob.consigne.morale")]
    i = next((x for n, x, _r in c if n == a), None)
    noter("consigne", f"{a} (faux)")
    return [f" {_c(203)}✖ " + t("ob.consigne.non." + i if i else "ob.indice.rep.consigne") + RESET]


def journal_equipe(state):
    E = donnees()["equipe"]
    rangee = liste_rangee(E["invites"])
    out = ["# " + t("ob.jequipe.titre"), "",
           "[Trieur] " + t("ob.jequipe.trieur", n=len(E["invites"]), k=len(rangee)),
           "[Compteur] " + t("ob.jequipe.compteur", n=len(E["invites"])),
           "[Plume] " + t("ob.jequipe.plume", n=len(rangee)),
           "[Copieur] " + t("ob.jequipe.copieur")]
    for n, i, _s, txt in propositions(_graine(state), "equipe"):
        out.append(f"[{t('ob.journal.propose')} {n}] {txt}    ({t('ob.prop.' + i)})")
    out += ["", "[" + t("ob.journal.attend") + "] " + t("ob.journal.comment")]
    return out


def lignes_agent_equipe(state):
    poser_equipe()
    E = donnees()["equipe"]
    rangee = liste_rangee(E["invites"])
    _ecrire("observatoire/equipe/liste.txt", "".join(x + "\n" for x in rangee))
    _ecrire("observatoire/equipe/compte.txt", f"{len(E['invites'])}\n")          # le défaut du Compteur (exprès)
    for x in rangee:
        _ecrire(f"observatoire/equipe/invitations/{x}.txt", t("ob.invitation", nom=x) + "\n")
    _ecrire("observatoire/equipe/journal_equipe.txt", "\n".join(journal_equipe(state)) + "\n")
    o_(state)["equipe_lancee"] = True
    k = emballe(state)
    noter("equipe", "lancee (ok)")
    return [f" {_c(78)}🤖🤖🤖 " + t("ob.equipe.lancee") + RESET, "",
            f"  {_c(203)}⚠ " + t("ob.equipe.emballe", n=copies_faites() or k) + RESET, "  " + t("ob.equipe.stop")]


def lignes_stop(state):
    d = dossier() / "equipe"
    o = o_(state)
    if o.get("boucle_tel"):
        o["boucle_tel"] = False
        noter("boucle", "stop (ok)")
        return [f" {_c(78)}⏹ " + t("ob.boucle.arrete") + RESET]
    if not d.is_dir():
        return [t("ob.stop.rien")]
    _ecrire("observatoire/equipe/STOP", t("ob.stop.fichier") + "\n")
    noter("stop", f"{copies_faites()} copies (ok)")
    return [f" {_c(78)}⏹ " + t("ob.stop.ok", n=copies_faites()) + RESET, "  " + t("ob.stop.morale")]


def lignes_bilan(state):
    if not _equipe_tests_ok() or not all(dans_carnet(x) for x in ("refus_equipe", "decoupe", "consigne")):
        return [f" {_c(215)}✋ " + t("ob.bilan.pas_encore") + RESET]
    E = donnees()["equipe"]
    texte = t("ob.bilan.texte", nom=state.get("name", ""), n=len(liste_rangee(E["invites"])), copies=copies_faites())
    _ecrire("observatoire/equipe/rapport_du_chef.txt", texte + "\n")
    noter("bilan", "fete (ok)")
    return [f" {_c(78)}{BOLD}🏅 " + t("ob.bilan.titre") + RESET, ""] + ["  " + l for l in texte.split("\n")] + \
        ["", "  " + t("ob.bilan.morale")]


# ---------------------------------------------------------------- les commandes
def _ecrire_sortie(out, lignes, couleur=True):
    if lignes:
        out.write("\n".join(lignes) + (RESET if couleur else "") + "\n")


def commande(args, sortie=None):
    """tg observatoire [plan|mission|verifier|oubli NOM|secrets|cle|agent|apprendre|piege X|biais [N]|mots|
    perroquet …|esprit|confier …|nuances …|equipe|decoupe …|consigne X]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide")).replace("-", "_")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        o_(st)
        g = _graine(st)
        arg = " ".join(reste) if reste else None
        if sous in ("plan", "coupole", "regles"):
            lignes.extend(banniere() + t("ob.meuble.coupole", nom=st.get("name", "")).split("\n"))
        elif sous in ("mission", "missions"):
            lignes.extend(lignes_mission())
        elif sous in ("verifier", "verifie"):
            lignes.extend(lignes_verifier())
        elif sous == "oubli":
            lignes.extend(lignes_oubli(st, arg))
        elif sous in ("secrets", "secret"):
            lignes.extend(lignes_secrets())
        elif sous in ("cle", "cles"):
            lignes.extend(lignes_cle())
        elif sous in ("agent", "agents"):
            lignes.extend(lignes_agent_intro())
        elif sous in ("apprendre", "apprends"):
            lignes.extend(lignes_apprendre())
        elif sous == "piege":
            lignes.extend(lignes_piege(arg))
        elif sous == "biais":
            lignes.extend(lignes_biais(st, arg) if arg else lignes_biais_intro() + [""] + lignes_biais(st, None))
        elif sous in ("mots", "mot"):
            lignes.extend(lignes_mots_intro())
        elif sous == "perroquet":
            lignes.extend(_quiz(st, reste, perroquet_cartes(g), "vf", "perroquet", "ob.perroquet.titre", "ob.perroquet",
                                "ob.perroquet.aide", "ob.perroquet.ok", "ob.perroquet.morale"))
        elif sous == "esprit":
            lignes.extend(lignes_esprit())
        elif sous == "confier":
            lignes.extend(_quiz(st, reste, confier_cartes(g), "cg", "confier", "ob.confier.titre", "ob.confier",
                                "ob.confier.aide", "ob.confier.ok", "ob.confier.morale"))
        elif sous in ("nuances", "nuance"):
            lignes.extend(_quiz(st, reste, nuances_cartes(g), "vf", "nuances", "ob.nuances.titre", "ob.nuances",
                                "ob.nuances.aide", "ob.nuances.ok", "ob.nuances.morale"))
        elif sous in ("equipe", "equipage"):
            lignes.extend(lignes_equipe_intro(st))
        elif sous == "decoupe":
            lignes.extend(lignes_decoupe(st, reste))
        elif sous == "consigne":
            lignes.extend(lignes_consigne(st, arg))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    _ecrire_sortie(out, lignes)


def commande_assistant(args, sortie=None, erreur=None):
    """assistant FICHIER | assistant questions | assistant fausses N N : le petit assistant FICTIF du jeu."""
    out = sortie if sortie is not None else sys.stdout
    err = erreur if erreur is not None else sys.stderr
    a = [x for x in args if x not in ("?", "…")]
    sous = ascii_bas(a[0]) if a else ""
    dit, produit = [], []
    from pathlib import Path
    ici = Path(os.getcwd())

    def f(st):
        o_(st)
        if sous in ("questions", "question"):
            dit.extend(lignes_questions(st))
        elif sous in ("fausses", "fausse", "faux"):
            dit.extend(lignes_fausses(st, a[1:]))
        else:
            d, p = lignes_assistant(st, a, ici)
            dit.extend(d)
            produit.extend(p)
    if core.modifier(f) is None:
        f({})
    if sous in ("questions", "question", "fausses", "fausse", "faux"):
        _ecrire_sortie(out, dit)
        return
    _ecrire_sortie(err, dit, couleur=False)
    if produit:
        out.write("\n".join(produit) + "\n")


def commande_agent(args, sortie=None):
    """agent lance|refuse N|accepte N|valide|boucle|stop|equipe|bilan : les agents FICTIFS du jeu (dans le terrain)."""
    out = sortie if sortie is not None else sys.stdout
    a = [x for x in args if x not in ("?", "…")]
    sous = ascii_bas(a[0]) if a else "aide"
    if sous == "boucle":
        boucle(out)
        return
    lignes = []

    def f(st):
        les = None
        try:
            from . import histoire
            les = (histoire.lecon_courante(st)[0] or {}).get("id")
        except Exception:                   # noqa: BLE001
            les = None
        if les in ("ob4", "ob9"):
            cle = "agent" if les == "ob4" else "equipe"
        else:
            cle = "equipe" if (dossier() / "equipe" / "journal_equipe.txt").exists() else "agent"
        if sous == "lance":
            lignes.extend(lignes_agent_lance(st))
        elif sous == "refuse":
            lignes.extend(lignes_refuse(st, a[1] if len(a) > 1 else None, cle))
        elif sous == "accepte":
            lignes.extend(lignes_accepte(st, a[1] if len(a) > 1 else None, cle))
        elif sous == "valide":
            lignes.extend(lignes_valide())
        elif sous == "stop":
            lignes.extend(lignes_stop(st))
        elif sous in ("equipe", "equipage"):
            lignes.extend(lignes_agent_equipe(st))
        elif sous == "bilan":
            lignes.extend(lignes_bilan(st))
        else:
            lignes.extend([f" {_c(78)}{BOLD}🤖 agent{RESET}  ({t('ob.pas_vraie_ia_court')})"] + _bloc("ob.agent.aide"))
    if core.modifier(f) is None:
        f({})
    _ecrire_sortie(out, lignes)


def commande_devine_type(args, sortie=None):
    out = sortie if sortie is not None else sys.stdout
    from pathlib import Path
    lignes = []
    a = [x for x in args if x not in ("?", "…")]

    def f(st):
        lignes.extend(lignes_devine_type(st, a, Path(os.getcwd())))
    if core.modifier(f) is None:
        f({})
    _ecrire_sortie(out, lignes)


def commande_devine_mot(args, sortie=None):
    out = sortie if sortie is not None else sys.stdout
    from pathlib import Path
    lignes = []
    a = [x for x in args if x not in ("?", "…")]

    def f(st):
        lignes.extend(lignes_devine_mot(st, a, Path(os.getcwd())))
    if core.modifier(f) is None:
        f({})
    _ecrire_sortie(out, lignes)
