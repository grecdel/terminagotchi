"""⛰ Le Sommet — Expert++ (docs/programme.md § 2.18, § 7.6, § 7.10, § 7.14).

Le dernier monde de la phase 5. Il s'ouvre quand TROIS mondes du Carrefour ont leur PALIER 3 (sommet.json,
« ouverture ») : le jeu compte sur la liste des mondes de programme.json (« mondes » qui ont « paliers » et « chapitre »),
donc les mondes qui arriveront plus tard (la Forge, le Poste de Contrôle, la Bibliothèque du Temps, l'Atelier…)
comptent dès qu'ils existent, sans rien changer ici. Palier 3 d'un monde = sa leçon paliers[3] faite (paliers[0] est
sa porte). Le chapitre et le lieu s'appellent « sommet » : ~/terrain_terminagotchi/sommet/.

RÈGLES (affichées à l'entrée, refuge.txt) : public plus âgé (palier de vocabulaire 2), mais toujours sans danger.
  - Les scripts fragiles et cassés sont FOURNIS PAR LE JEU, dans le terrain ; aucun ne sort du dossier où on le lance,
    aucun ne demande sudo, aucun n'utilise le réseau. Le jeu ne lance jamais rien lui-même.
  - Ce qui manque à l'ordinateur (shellcheck, man, apropos, strace) est raconté, jamais obligatoire.
  - Rien n'est envoyé : le CTF est hors ligne ; le DÉFI DU JOUR est fait d'exercices de la salle d'entraînement, que le
    site vérifie déjà (graine du jour, compteur, empreinte, temps plausible) comme tous les autres.

LES PALIERS (som0 à som7) : la porte (le refuge) ; S1 la corde de rappel (set -euo pipefail, guillemets, codes de
retour : réécrire le script fragile du jeu) ; S2 le bivouac propre (trap, mktemp, getopts) ; S3 les inscriptions (regex
avancées : grep -E, -o, ancres, classes, alternatives, sed -E et ses captures : les dates du journal) ; S4 l'éboulis
(find -print0 | xargs -0, $( ), <( ), awk sur plusieurs fichiers : les 5 pierres les plus lourdes) ; S5 le guide qui
débogue (bash -n, bash -x, shellcheck si présent, strace en notions) ; S6 la carte et la boussole (man -f, apropos,
--help : apprendre un outil jamais vu) ; S7 le sommet (le CTF combiné, le défi du jour, les grades Péta / Exa, les records).

Récompense (§ 7.6) : l'exploit « trois mondes maîtrisés » (sommet.trois_mondes), au drapeau du CTF combiné : des
rencontres favorisées de LÉGENDAIRES EXISTANTES qu'aucun autre monde ne réserve (programme.json, « legendaires »).
Mêmes règles sur Android (Sommet.kt, sh au lieu de bash) ; vecteurs communs donnees/sommet/vecteurs.json.
"""
import datetime
import hashlib
import json
import os
import pkgutil
import re
import sys
import time
import unicodedata

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

_D = None
O = "sommet"


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "sommet.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


def ascii_id(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def sh_quote(s):
    """Un texte du jeu entre apostrophes pour le shell (une apostrophe : '\\'')."""
    return "'" + s.replace("'", "'\\''") + "'"


def _une_ligne(s):
    return " ".join((s or "").split())


def remplir(lignes, sh="bash", **p):
    """Un gabarit de script : @@clé@@ → le texte entre apostrophes, ##clé## → le texte brut (commentaire)."""
    def q(m):
        return sh_quote(_une_ligne(t(m.group(1), sh=sh, **p)))

    def b(m):
        return _une_ligne(t(m.group(1), sh=sh, **p))
    out = [re.sub(r"##([\w.]+)##", b, re.sub(r"@@([\w.]+)@@", q, l)) for l in lignes]
    if sh != "bash":
        out[0] = "#!/system/bin/sh"
    return "\n".join(out) + "\n"


def script(nom, sh="bash"):
    return remplir(donnees()["scripts"][nom], sh)


def ordre(graine, sel, liste):
    """La liste mélangée pour cette partie (toujours la même)."""
    return sorted(liste, key=lambda x: (tire(graine, f"{sel}:{x}", 1 << 30), x))


# ---------------------------------------------------------------- S3 : le journal de l'expédition
def _jour(debut, k):
    return (datetime.date.fromisoformat(debut) + datetime.timedelta(days=k)).isoformat()


def journal(graine):
    """Les lignes du journal : (texte, genre) ; genre = INFO / ALERTE / ERREUR (une ligne datée) ou suite (« releve »
    avec une date AU MILIEU, ou « fausse » : le mot ALERTE au milieu d'une ligne qui n'est pas une alerte)."""
    J = donnees()["journal"]
    out = []
    for i in range(J["lignes"]):
        r = tire(graine, f"l{i}", 10)
        jour = _jour(J["debut"], min(J["jours"] - 1, i * J["jours"] // J["lignes"]))
        if i > 0 and r < 2:
            if r == 0:
                d = _jour(J["debut"], tire(graine, f"d{i}", J["jours"] + 3))
                out.append(("  " + t("som.log.suite.releve", date=d), "releve"))
            else:
                out.append(("  " + t("som.log.suite.fausse"), "fausse"))
            continue
        tag = "INFO" if r < 7 else "ALERTE" if r < 9 else "ERREUR"
        ms = J["messages"][tag]
        out.append((f"{jour} [{tag}] " + t(ms[tire(graine, f'm{i}', len(ms))]), tag))
    return out


def journal_texte(graine):
    return "".join(l + "\n" for l, _g in journal(graine))


DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def lignes_datees(graine):
    return [l for l, _g in journal(graine) if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}", l)]


def dates(graine):
    return sorted({d for l, _g in journal(graine) for d in DATE.findall(l)})


def alertes_partout(graine):
    return [l for l, _g in journal(graine) if "ALERTE" in l or "ERREUR" in l]


def alertes(graine):
    return [l for l, g in journal(graine) if g in ("ALERTE", "ERREUR")]


def date_fr(ligne):
    return re.sub(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})", r"\3/\2/\1", ligne)


# ---------------------------------------------------------------- S4 : l'éboulis
TAILLES = [120, 260, 410, 530, 680, 790, 905, 1040, 1180, 1333]


def eboulis(graine):
    """{chemin relatif à eboulis/: (nom de la pierre, taille en octets)} : nord et sud partagent 2 pierres."""
    p = ordre(graine, "pierres", donnees()["pierres"])
    tailles = ordre(graine, "tailles", TAILLES)
    places = [("nord", p[0]), ("nord", p[1]), ("nord", p[2]), ("nord", p[3]), ("sud", p[0]), ("sud", p[1]),
              ("sud", p[4]), ("sud", p[5]), ("grotte", p[6]), ("grotte/profond", p[7])]
    return {f"{d}/{n}.txt": (n, tailles[k]) for k, (d, n) in enumerate(places)}


def contenu_pierre(nom, taille):
    debut = f"{nom}\n".encode()
    return (debut + b"#" * (taille - len(debut) - 1) + b"\n").decode()


def plus_lourds(graine, n=5):
    e = eboulis(graine)
    return sorted(((taille, "eboulis/" + rel) for rel, (_nom, taille) in e.items()), key=lambda x: (-x[0], x[1]))[:n]


def plus_lourde(graine):
    return plus_lourds(graine, 1)[0][1].rsplit("/", 1)[1][:-4]


def total_eboulis(graine):
    return sum(taille for _n, taille in eboulis(graine).values())


def noms_dans(graine, dossier):
    return sorted(rel.split("/")[-1] for rel in eboulis(graine) if rel.rsplit("/", 1)[0] == dossier)


# ---------------------------------------------------------------- S6 : la boussole (un outil jamais vu)
def lieu(graine, cap, pas):
    L = donnees()["lieux"]
    return L[tire(graine, f"lieu:{cap}:{pas}", len(L))]


def mission(graine):
    caps = donnees()["caps"]
    return caps[tire(graine, "mission:cap", len(caps))], 2 + tire(graine, "mission:pas", 7)


def script_boussole(graine, sh="bash"):
    lignes = ["#!/usr/bin/env bash", "# ##som.sc.boussole.role##", "aide() {", "  echo @@som.sc.boussole.usage@@",
              "  echo @@som.sc.boussole.but@@", "  echo '  -c CAP      '@@som.sc.boussole.cap@@",
              "  echo '  -p PAS      '@@som.sc.boussole.pas@@", "  echo '  -h, --help  '@@som.sc.boussole.aide@@", "}",
              'if [ "${1:-}" = "--help" ]; then aide; exit 0; fi', 'cap=""', 'pas=""', 'while getopts "c:p:h" opt; do',
              "  case $opt in", "    c) cap=$OPTARG ;;", "    p) pas=$OPTARG ;;", "    h) aide; exit 0 ;;",
              "    *) aide >&2; exit 2 ;;", "  esac", "done", 'if [ -z "$cap" ] || [ -z "$pas" ]; then aide >&2; exit 2; fi',
              'case "$cap:$pas" in']
    for c in donnees()["caps"]:
        for p in range(1, 10):
            lignes.append(f"  {c}:{p}) lieu={lieu(graine, c, p)} ;;")
    lignes += ["  *) lieu=brume ;;", "esac", 'echo @@som.sc.boussole.arrive@@ "$lieu"', 'echo "$lieu" > arrivee.txt']
    return remplir(lignes, sh)


def aide_boussole(sh="bash"):
    """Ce qu'affiche `bash boussole.sh --help` (cinq lignes)."""
    def x(k):
        return _une_ligne(t(k, sh=sh))
    return "\n".join([x("som.sc.boussole.usage"), x("som.sc.boussole.but"), "  -c CAP      " + x("som.sc.boussole.cap"),
                      "  -p PAS      " + x("som.sc.boussole.pas"), "  -h, --help  " + x("som.sc.boussole.aide")])


# ---------------------------------------------------------------- S7 : le CTF combiné
def fragments(graine):
    m = ordre(graine, "fragments", donnees()["mots"])
    return m[0], m[1], m[2]


def drapeau(graine):
    return "TG{" + "-".join(fragments(graine)) + "}"


def drapeau_ok(graine, rep):
    r = (rep or "").strip().lower().replace(" ", "")
    juste = "-".join(fragments(graine))
    return r in (juste, "tg{" + juste + "}")


def registre(graine):
    """ctf/registre.log : le vrai fragment 1 (minuscules, collé au signe =) et deux leurres."""
    w1, _w2, _w3 = fragments(graine)
    leurres = [x for x in ordre(graine, "leurres", donnees()["mots"]) if x not in fragments(graine)]
    lignes = [t("som.ctf.registre.titre"), f"fragment1 = {leurres[0]}", t("som.ctf.registre.l1"),
              f"fragment1={leurres[1].upper()}", t("som.ctf.registre.l2"), f"{t('som.ctf.registre.l3')} fragment1={w1} ;",
              t("som.ctf.registre.l4")]
    return "".join(_une_ligne(l) + "\n" if not l.startswith("fragment1 =") else l + "\n" for l in lignes)


def script_porte(graine, sh="bash"):
    w1, _w2, w3 = fragments(graine)
    lignes = ["#!/usr/bin/env bash", "# ##som.sc.porte.role##",
              "aide() { echo @@som.sc.porte.usage@@; echo @@som.sc.porte.cle@@; }",
              'if [ "${1:-}" = "--help" ]; then aide; exit 0; fi', 'cle=""', 'while getopts "k:h" opt; do',
              "  case $opt in", "    k) cle=$OPTARG ;;", "    h) aide; exit 0 ;;", "    *) aide >&2; exit 2 ;;", "  esac",
              "done", f'if [ "$cle" = "{w1}" ]; then', f'  echo fragment3={w3} | tee "$(dirname "$0")/porte_ouverte.txt"', "else",
              "  echo @@som.sc.porte.non@@ >&2", "  exit 1", "fi"]
    return remplir(lignes, sh)


def fichiers_ctf(graine, sh="bash"):
    _w1, w2, _w3 = fragments(graine)
    return {"ctf/registre.log": registre(graine), "ctf/porte.sh": script_porte(graine, sh),
            "ctf/eboulis/une pierre creuse/cache.frag": f"fragment2={w2}\n",
            "ctf/eboulis/leurre.txt": "fragment2=" + ordre(graine, "leurre2", donnees()["mots"])[5] + "\n",
            "ctf/eboulis/vieux sac/notes.txt": _une_ligne(t("som.ctf.notes")) + "\n"}


# ---------------------------------------------------------------- l'ouverture : 3 mondes au palier 3
def mondes_au_palier(state, palier=None):
    """Les mondes du Carrefour (programme.json) dont la leçon du palier voulu est faite : [(id du monde, chapitre)].
    Chaque monde qui a « paliers » et « chapitre » compte, ceux qui arriveront aussi ; le Sommet ne se compte pas."""
    from . import histoire, programme
    palier = donnees()["ouverture"]["palier"] if palier is None else palier
    faits = set(histoire.h_(state)["faits"])
    out = []
    for m in programme.donnees().get("mondes", []):
        ps, ch = m.get("paliers") or [], m.get("chapitre") or m.get("id")
        if m.get("id") == "sommet" or len(ps) <= palier or ch not in histoire.PAR_CHAP \
                or ps[0] not in histoire.PAR_CHAP[ch]["lecons"]:       # (les leçons du monde sont bien celles du chapitre)
            continue
        if ps[palier] in faits or histoire.fini(state, ch):
            out.append((m["id"], ch))
    return out


def lecons_qui_ouvrent():
    """Les leçons dont la fin peut ouvrir le Sommet (le palier 3 de chaque monde) : son annonce part tout de suite."""
    from . import programme
    p = donnees()["ouverture"]["palier"]
    return {m["paliers"][p] for m in programme.donnees().get("mondes", [])
            if m.get("id") != "sommet" and len(m.get("paliers") or []) > p}


def ouvert(state):
    return len(mondes_au_palier(state)) >= donnees()["ouverture"]["mondes"]


def manque(state):
    from . import histoire
    o = donnees()["ouverture"]
    faits = mondes_au_palier(state)
    noms = ", ".join(histoire.nom_chapitre(ch) for _m, ch in faits) or "—"
    return [t("som.manque", n=len(faits), total=o["mondes"], palier=o["palier"], mondes=noms)]


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "sommet" in deja or histoire.fini(state, "sommet") or not ouvert(state):
        return False
    deja.append("sommet")
    noms = ", ".join(histoire.nom_chapitre(ch) for _m, ch in mondes_au_palier(state))
    core.log(state, t("som.ouvert.log"))
    core.say(state, histoire.dire(state, "som.ouvert.dit", mondes=noms), 18)
    return True


# ---------------------------------------------------------------- le défi du jour (salle d'entraînement, vérifiée par le site)
def defi_types(valeur, possibles):
    """Les exercices du défi du jour : tirés de la graine du jour (Hasard(valeur, base)), parmi ceux que l'enfant peut
    faire, dans l'ordre de la salle d'entraînement."""
    from .entrainement import choisir
    from .tirage import Hasard
    D = donnees()["defi"]
    return choisir(Hasard(valeur, D["base"]), list(possibles), min(D["n"], len(possibles)))


def _jour_local():
    return time.strftime("%Y-%m-%d")


def graine_defi(state):
    """(valeur, vérifiée par le site ?) : la graine du jour de l'appareil (reçue du site), sinon une graine locale."""
    from .tirage import graine_du_jour
    g = graine_du_jour(state)
    if g:
        return g[1], True
    return hashlib.sha256(f"local:{_jour_local()}:{_graine(state)}".encode()).hexdigest(), False


def defi_du_jour(state):
    from . import entrainement as E
    possibles = [x for x in E.TYPES if E.type_possible(state, x)]
    valeur, verifiee = graine_defi(state)
    return defi_types(valeur, possibles), verifiee


def noter_exercice(state, typ, medaille, gid=""):
    """La salle d'entraînement vient de réussir un exercice : le défi du jour le compte (or ou diamant)."""
    s = s_(state)
    d = s.get("defi") if isinstance(s.get("defi"), dict) else {}
    if d.get("jour") != _jour_local():
        d = {"jour": _jour_local(), "faits": {}}
    if medaille in donnees()["defi"]["medailles"]:
        d["faits"][typ] = {"m": medaille, "v": bool(gid)}
    s["defi"] = d


def defi_faits(state):
    d = s_(state).get("defi") or {}
    return d.get("faits", {}) if d.get("jour") == _jour_local() else {}


# ================================================================ l'état, le terrain, le carnet
def s_(state):
    c = state.setdefault("sommet", {})
    c.setdefault("faits", [])
    return c


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def dossier():
    return core.TERRAIN / "sommet"


CARNET = "carnet_du_sommet.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8", newline="\n") as f:
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


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _lire(rel):
    try:
        return (dossier() / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _ecrire(rel, contenu, executable=False):
    p = dossier() / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenu, encoding="utf-8")
        if executable:
            p.chmod(0o755)
        return True
    except OSError:
        return False


def meubles(state):
    return {"sommet/refuge.txt": t("som.meuble.refuge") + "\n", f"sommet/{CARNET}": t("som.meuble.carnet") + "\n"}


BESOINS = {"som0": ["refuge.txt"]}


def meubler(state, lid, step):
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire(rel, tous["sommet/" + rel])
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = s_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("som.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("som.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- les vérifications des étapes
SET_EUO = re.compile(r"^\s*set\s+(-euo\s+pipefail|-eu\s+-o\s+pipefail|-e\s+-u\s+-o\s+pipefail|-o\s+pipefail\s+-eu)\s*$")


def _lignes(rel):
    return (_lire(rel) or "").splitlines()


def _fragile_set():
    l = _lignes("fragile.sh")
    k = next((i for i, x in enumerate(l) if x.strip().startswith("cp ")), None)
    return k is not None and any(SET_EUO.match(x) for x in l[:k])


def _fragile_guillemets():
    return any(re.match(r'^\s*cp\s+"\$\{?carnet\}?"\s+coffre/?\s*$', x) for x in _lignes("fragile.sh"))


def _coffre():
    return (dossier() / "coffre" / "carnet de bord.txt").is_file() and _fragile_set() and _fragile_guillemets()


def _sac():
    return len([x for x in _lignes("sac.txt") if x.strip()]) == 3


def _brouillons():
    try:
        return sorted(p.name for p in dossier().iterdir() if p.name.startswith("brouillon."))
    except OSError:
        return []


def _propre():
    return dans_carnet("bivouac") and not _brouillons() and (dossier() / "bivouac.sh").is_file()


ALERTE_ANCREE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} \[(ALERTE|ERREUR)\]")


def _alertes_txt():
    """alertes.txt = les lignes de journal.log (celui du terrain) qui COMMENCENT par une date puis [ALERTE] ou [ERREUR]."""
    l = [x for x in _lignes("alertes.txt") if x.strip()]
    return bool(l) and l == [x for x in _lignes("journal.log") if ALERTE_ANCREE.match(x)]


def _casse_ok():
    l = _lignes("casse.sh")
    n = donnees()["casse"]["ligne"]
    return len(l) >= n + 1 and (re.search(r";\s*then\s*$", l[n - 1]) is not None or l[n].strip() == "then")


def _boucle_ok():
    txt = _lire("boucle.sh") or ""
    return "totl" not in txt and "total=$((total + alt))" in txt


def _arrivee_ok():
    """arrivee.txt (écrit par boussole.sh) est le lieu de la mission, noté au carnet quand la boussole a été posée."""
    m = re.match(r"^\[boussole\] \S+ \S+ (\S+) pose \(ok\)", dernier("boussole") or "")
    return m is not None and (_lire("arrivee.txt") or "").strip() == m.group(1)


FS = {
    "som_fragile_set": _fragile_set,
    "som_fragile_guillemets": _fragile_guillemets,
    "som_coffre": _coffre,
    "som_sac": _sac,
    "som_propre": _propre,
    "som_dates": lambda: dans_carnet("dates"),
    "som_alertes_txt": _alertes_txt,
    "som_alertes": lambda: dans_carnet("alertes"),
    "som_lourd": lambda: dans_carnet("lourd"),
    "som_ligne": lambda: dans_carnet("ligne"),
    "som_casse": _casse_ok,
    "som_bug": lambda: dans_carnet("bug"),
    "som_boucle": _boucle_ok,
    "som_arrivee_txt": _arrivee_ok,
    "som_arrivee": lambda: dans_carnet("arrivee"),
    "som_drapeau": lambda: dans_carnet("drapeau"),
    "som_porte": lambda: (_lire("ctf/porte_ouverte.txt") or "").startswith("fragment3="),
}
CREE = {}

# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
SO = r"^(tg\s+)?sommet\s+"
SH = r"^(bash|sh)\s+(\./)?"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LECONS = {
    # la porte : le refuge du Sommet
    "som0": {"titre": "hist.som0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "sommet"}), "cmd": "cd ~/terrain_terminagotchi/sommet",
         "ici": "sommet", "bravo": ("hist.entree.bravo", {"piece": "sommet"})},
        _n("som0", 1, cmd="ls", re=LS, ou=O),
        _n("som0", 2, cmd="cat refuge.txt", re=LIRE + r".*refuge", ou=O),
    ]},
    # S1 la corde de rappel : set -euo pipefail, guillemets, codes de retour
    "som1": {"titre": "hist.som1.titre", "skill": None, "steps": [
        _n("som1", 0, cmd="sommet fragile", re=SO + r"fragile", ou=O),
        _n("som1", 1, cmd="cat fragile.sh", re=LIRE + r".*fragile\.sh", ou=O),
        _n("som1", 2, cmd='bash fragile.sh "carnet de bord.txt"', re=SH + r"fragile\.sh\s+\S", ou=O, tout_code=True, win=False),
        _n("som1", 3, cmd="echo $?", re=r"^echo\s+\$\?\s*$", ou=O, win=False),
        _n("som1", 4, cmd="sed -i '2i set -euo pipefail' fragile.sh", fs="som_fragile_set", ou=O, win=False),
        _n("som1", 5, cmd='bash fragile.sh "carnet de bord.txt"; echo $?', re=SH + r"fragile\.sh\s+\S", ou=O, tout_code=True,
           win=False),
        _n("som1", 6, cmd="sed -i 's/cp $carnet/cp \"$carnet\"/' fragile.sh", fs="som_fragile_guillemets", ou=O, win=False),
        _n("som1", 7, cmd="bash fragile.sh", re=SH + r"fragile\.sh\s*$", ou=O, tout_code=True, win=False),
        _n("som1", 8, cmd='bash fragile.sh "carnet de bord.txt"', fs="som_coffre", ou=O, win=False),
    ]},
    # S2 le bivouac propre : trap, mktemp, getopts
    "som2": {"titre": "hist.som2.titre", "skill": None, "steps": [
        _n("som2", 0, cmd="sommet bivouac", re=SO + r"bivouac", ou=O),
        _n("som2", 1, cmd="bash sale.sh", re=SH + r"sale\.sh", ou=O, tout_code=True, win=False),
        _n("som2", 2, cmd="ls brouillon.*", re=r"^ls\b.*brouillon", ou=O, tout_code=True, win=False),
        _n("som2", 3, cmd="cat bivouac.sh", re=LIRE + r".*bivouac\.sh", ou=O),
        _n("som2", 4, cmd="bash bivouac.sh -n 3", fs="som_sac", ou=O, win=False),
        _n("som2", 5, cmd="ls brouillon.* | wc -l", re=r"^ls\b.*brouillon.*\|\s*wc\s+-l", ou=O, tout_code=True, win=False),
        _n("som2", 6, cmd="bash bivouac.sh -x", re=SH + r"bivouac\.sh\s+-[a-gi-mo-z]", ou=O, tout_code=True, win=False),
        _n("som2", 7, cmd="rm brouillon.*", fs="som_propre", ou=O, win=False),
    ]},
    # S3 les inscriptions : regex avancées
    "som3": {"titre": "hist.som3.titre", "skill": None, "steps": [
        _n("som3", 0, cmd="sommet journal", re=SO + r"journal", ou=O),
        _n("som3", 1, cmd="head -5 journal.log", re=LIRE + r".*journal\.log", ou=O),
        _n("som3", 2, cmd="grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l",
           re=r"^grep\b.*\s-\w*E.*\^\[0-9\].*journal\.log", ou=O, tout_code=True, win=False),
        _n("som3", 3, cmd="grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l",
           re=r"^grep\b.*\s-\w*o.*journal\.log.*\|\s*sort\b", ou=O, win=False),
        _n("som3", 4, cmd="sommet dates ?", fs="som_dates"),
        _n("som3", 5, cmd="grep -cE 'ALERTE|ERREUR' journal.log", re=r"^grep\b.*ALERTE\|ERREUR.*journal\.log", ou=O,
           tout_code=True, win=False),
        _n("som3", 6, cmd="grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt", fs="som_alertes_txt",
           ou=O, win=False),
        _n("som3", 7, cmd="sommet alertes ?", fs="som_alertes"),
        _n("som3", 8, cmd="sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt",
           re=r"^sed\s+(-\w+\s+)*-E\b.*\\[123].*alertes\.txt", ou=O, win=False),
    ]},
    # S4 l'éboulis : find -print0 | xargs -0, $( ), <( ), awk sur plusieurs fichiers
    "som4": {"titre": "hist.som4.titre", "skill": None, "steps": [
        _n("som4", 0, cmd="sommet eboulis", re=SO + r"[eé]boulis", ou=O),
        _n("som4", 1, cmd="find eboulis -type f", re=r"^find\s+eboulis\b(?!.*print0)", ou=O, win=False),
        _n("som4", 2, cmd="find eboulis -type f | xargs wc -c", re=r"^find\s+eboulis\b(?!.*print0).*\|\s*xargs\s+(?!.*-0)",
           ou=O, tout_code=True, win=False),
        _n("som4", 3, cmd="find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6",
           re=r"^find\s+eboulis\b.*-print0.*\|\s*xargs\s+(-\w+\s+)*-0", ou=O, win=False),
        _n("som4", 4, cmd="sommet lourd ?", fs="som_lourd"),
        _n("som4", 5, cmd='echo "pierres : $(find eboulis -type f | wc -l)"', re=r"^echo\b.*\$\(\s*find\b.*eboulis", ou=O,
           win=False),
        _n("som4", 6, cmd="diff <(ls eboulis/nord) <(ls eboulis/sud)", re=r"^diff\s+<\(.*nord.*<\(.*sud|^diff\s+<\(.*sud.*<\(.*nord",
           ou=O, tout_code=True, win=False),
        _n("som4", 7, cmd="awk 'FNR==1 {print FILENAME, $1}' eboulis/nord/*.txt", re=r"^awk\b.*FNR.*FILENAME.*eboulis", ou=O,
           win=False, outil="awk"),
    ]},
    # S5 le guide qui débogue : bash -n, bash -x, shellcheck, strace
    "som5": {"titre": "hist.som5.titre", "skill": None, "steps": [
        _n("som5", 0, cmd="sommet casse", re=SO + r"casse", ou=O),
        _n("som5", 1, cmd="bash -n casse.sh", re=r"^(bash|sh)\s+-n\s+(\./)?casse\.sh", ou=O, tout_code=True, win=False),
        _n("som5", 2, cmd="sommet ligne ?", fs="som_ligne"),
        _n("som5", 3, cmd="sed -i '6s/$/; then/' casse.sh", fs="som_casse", ou=O, win=False),
        _n("som5", 4, cmd="bash -n casse.sh && bash casse.sh", re=SH + r"casse\.sh\s*$", ou=O, win=False),
        _n("som5", 5, cmd="bash boucle.sh", re=SH + r"boucle\.sh\s*$", ou=O, win=False),
        _n("som5", 6, cmd="bash -x boucle.sh", re=r"^(bash|sh)\s+-x\s+(\./)?boucle\.sh", ou=O, win=False),
        _n("som5", 7, cmd="sommet bug ?", fs="som_bug"),
        _n("som5", 8, cmd="sed -i 's/totl=/total=/' boucle.sh && bash boucle.sh", fs="som_boucle", ou=O, win=False),
        _n("som5", 9, cmd="shellcheck fragile.sh", re=r"^shellcheck\b", ou=O, tout_code=True, outil="shellcheck"),
        _n("som5", 10, cmd="sommet strace", re=SO + r"strace"),
    ]},
    # S6 la carte et la boussole : man -f, apropos, --help
    "som6": {"titre": "hist.som6.titre", "skill": None, "steps": [
        _n("som6", 0, cmd="sommet boussole", re=SO + r"boussole", ou=O),
        _n("som6", 1, cmd="man -f passwd", re=r"^(man\s+-f|whatis)\s+\w", tout_code=True, outil="man"),
        _n("som6", 2, cmd="apropos -s 1 archive", re=r"^(apropos|man\s+-k)\b", tout_code=True, outil="apropos"),
        _n("som6", 3, cmd="bash boussole.sh --help", re=SH + r"boussole\.sh\s+(--help|-h)\b", ou=O, win=False),
        _n("som6", 4, cmd="bash boussole.sh -c ? -p ?", fs="som_arrivee_txt", ou=O, win=False),
        _n("som6", 5, cmd="sommet arrivee ?", fs="som_arrivee"),
        _n("som6", 6, cmd="grep --help | grep -- '-o,'", re=r"^grep\s+--help\s*\|", tout_code=True, win=False),
    ]},
    # S7 le sommet : le CTF combiné, le défi du jour, les grades, les records
    "som7": {"titre": "hist.som7.titre", "skill": None, "steps": [
        _n("som7", 0, cmd="sommet ctf", re=SO + r"ctf\s*$", ou=O),
        _n("som7", 1, cmd="grep -oE 'fragment1=[a-z]+' ctf/registre.log", re=r"^grep\b.*\s-\w*o.*registre\.log", ou=O,
           win=False),
        _n("som7", 2, cmd="find ctf -name '*.frag' -print0 | xargs -0 cat", re=r"^find\s+ctf\b.*-print0.*\|\s*xargs\s+(-\w+\s+)*-0",
           ou=O, win=False),
        _n("som7", 3, cmd="bash ctf/porte.sh --help", re=SH + r"ctf/porte\.sh\s+(--help|-h)\b", ou=O, win=False),
        _n("som7", 4, cmd="bash ctf/porte.sh -k ?", fs="som_porte", ou=O, win=False),
        _n("som7", 5, cmd="sommet drapeau ?", fs="som_drapeau"),
        _n("som7", 6, cmd="sommet defi", re=SO + r"d[eé]fi\b"),
        _n("som7", 7, cmd="tg badges grades", re=r"^(tg\s+)?badges\s+grades?\b"),
        _n("som7", 8, cmd="sommet records", re=SO + r"records?\b"),
    ]},
}
CHAPITRE = {"id": "sommet", "n": 23, "piece": "sommet", "famille": None, "monde": True,
            "lecons": [f"som{i}" for i in range(8)], "objet": "piolet", "titre": "maitre_du_sommet"}


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s|/)(\?|…|<[^>]*>)(\s|/|$)")
REPONSES = {"sommet dates ?": "dates", "sommet alertes ?": "alertes", "sommet lourd ?": "lourd",
            "sommet ligne ?": "ligne", "sommet bug ?": "bug", "sommet arrivee ?": "arrivee", "sommet drapeau ?": "drapeau"}


def indice(step, tapees):
    """Un indice du Sommet : sudo (jamais ici), un « ? » recopié, une mauvaise réponse, un script lancé sans bash,
    xargs sans -0, <( ) dans sh, un sed qui ne vise pas la bonne ligne."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("som.indice.sudo")
    if "?" in cmd.split() or "-p ?" in cmd:
        if any(TROU.search(l) for l in lignes if re.match(SO, l) or re.match(SH, l)):
            return t("som.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = dernier(et)
        if der and not der.endswith("(ok)") and any(re.match(SO + et, l) for l in lignes):
            return t("som.indice.rep." + et)
    if re.match(SH, cmd) or " && bash " in cmd:
        if any(re.match(r"^\./\w+\.sh", l) for l in lignes):
            return t("som.indice.bash")
    if step.get("fs") == "som_arrivee_txt" and any(re.match(SH + r"boussole\.sh\s*$", l) for l in lignes):
        return t("som.indice.rep.arrivee")             # la boussole sans -c ni -p : relire la mission et l'aide
    if "-print0" in cmd and any("xargs" in l and "-0" not in l for l in lignes):
        return t("som.indice.zero")
    if "<(" in cmd and any(re.match(r"^sh\s", l) for l in lignes):
        return t("som.indice.bash_seul")
    if step.get("fs") == "som_fragile_set" and any(re.match(r"^sed\b", l) and "pipefail" in l and "-i" not in l for l in lignes):
        return t("som.indice.sed_i")
    return None


# ---------------------------------------------------------------- les 3 niveaux d'indice (idée 25, aide_douce.py)
INDICES = ["dates", "alertes", "lourd", "ligne", "bug", "arrivee", "drapeau", "boussole", "porte"]


def trou_de(cmd):
    """L'étape à trou (« ? ») d'une commande de leçon : dates, alertes, … boussole (-c ? -p ?), porte (-k ?), sinon None."""
    c = re.sub(r"\s+", " ", (cmd or "").strip())
    if c in REPONSES:
        return REPONSES[c]
    if re.match(r"^(bash|sh) boussole\.sh -c \? -p \?$", c):
        return "boussole"
    if re.match(r"^(bash|sh) ctf/porte\.sh -k \?$", c):
        return "porte"
    return None


def reponse_indice(graine, et, sh="bash"):
    """La réponse complète d'une étape à trou (le 3e niveau d'indice), telle que l'enfant la taperait."""
    if et == "dates":
        return f"sommet dates {len(dates(graine))}"
    if et == "alertes":
        return f"sommet alertes {len(alertes(graine))}"
    if et == "lourd":
        return f"sommet lourd {plus_lourde(graine)}"
    if et == "ligne":
        return f"sommet ligne {donnees()['casse']['signale'][-1]}"
    if et == "bug":
        return f"sommet bug {donnees()['boucle']['faute']}"
    cap, pas = mission(graine)
    if et == "arrivee":
        return f"sommet arrivee {lieu(graine, cap, pas)}"
    if et == "drapeau":
        return f"sommet drapeau {drapeau(graine)}"
    if et == "boussole":
        return f"{sh} boussole.sh -c {cap} -p {pas}"
    if et == "porte":
        return f"{sh} ctf/porte.sh -k {fragments(graine)[0]}"
    return None


def commande_indice(et, sh="bash"):
    """La commande montrée au 2e niveau (celle qui donne la réponse)."""
    return {"dates": "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l", "alertes": "wc -l alertes.txt",
            "lourd": "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6", "ligne": f"{sh} -n casse.sh",
            "bug": f"{sh} -x boucle.sh", "arrivee": "cat arrivee.txt", "drapeau": "sommet drapeau TG{fragment1-fragment2-fragment3}",
            "boussole": f"{sh} boussole.sh -c CAP -p PAS", "porte": "grep -oE 'fragment1=[a-z]+' ctf/registre.log"}[et]


def cible_indice(state):
    """(clé, réponse, « sommet:<étape> ») quand la leçon du Sommet attend une réponse à trou, sinon None."""
    from . import lecons
    les, _ = lecons.lecon_courante(state)
    if not les or not str(les.get("id", "")).startswith("som") or core.level(state.get("xp", 0)) < les["niveau"]:
        return None
    step = les["steps"][state["step"]]
    et = trou_de(step.get("cmd"))
    if not et:
        return None
    return f"som:{les['id']}:{state['step']}", reponse_indice(_graine(state), et), "sommet:" + et


def texte_indice(et, n, reponse, sh="bash"):
    """Le texte du niveau n : 1 = petit coup de pouce, 2 = la commande qui donne la réponse, 3 = la réponse."""
    if n == 1:
        return t(f"ad.ind.som.{et}.1")
    if n == 2:
        return t(f"ad.ind.som.{et}.2", cmd=f"`{commande_indice(et, sh)}`")
    return t("ad.ind.n3", cmd=f"`{reponse}`")


def surveiller(state, lignes):
    """Le Sommet n'a pas de danger à guetter : les scripts du jeu restent dans le terrain."""
    return False


# ================================================================ la vue déployée : la cordée
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def cordee_de(morceau):
    """(outil, geste, de, vers) d'une commande, ou None : la première règle de sommet.json (« cordee »)."""
    m = (morceau or "").strip()
    for r in donnees()["cordee"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["geste"], r["de"], r["vers"]
    return None


# ================================================================ les dessins (caractères) et les commandes du jeu
MONTAGNE = ["          /\\        ⛰", "         /  \\  /\\", "    /\\  / ▲▲ \\/  \\", "   /  \\/ ▲▲▲▲ \\   \\",
            "  /  ▲▲▲▲▲▲▲▲▲▲   \\  🚩"]


def banniere(largeur=None):
    """L'entrée du Sommet : l'illustration (illustrations.bin, « sommet ») si elle existe, sinon le REPLI dessiné en
    caractères (la montagne, la cordée et le drapeau)."""
    try:
        from . import scenes
        if scenes.disponible("sommet"):
            return scenes.illustration("sommet", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [255, 252, 117, 39, 78]
    return [f"  {fg(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(MONTAGNE)]


def aide():
    return banniere() + [f" {fg(117)}{BOLD}⛰ " + t("som.aide.titre") + RESET] + \
        ["  " + l for l in t("som.aide.liste").split("\n")]


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def _ok(cle, **p):
    return [f" {fg(78)}✔ " + t(cle, **p) + RESET]


def _non(et):
    return [f" {fg(203)}✖ " + t("som.indice.rep." + et) + RESET]


def _rep(arg):
    return (arg or "").strip()


def lignes_fragile():
    if not (dossier() / "fragile.sh").exists() or not dans_carnet("fragile"):
        _ecrire("fragile.sh", script("fragile"))
        _ecrire("carnet de bord.txt", t("som.carnet_de_bord") + "\n")
        (dossier() / "coffre").mkdir(parents=True, exist_ok=True)
    noter("fragile", "pose (ok)")
    return [f" {fg(203)}{BOLD}🪢 " + t("som.fragile.titre") + RESET, ""] + _bloc("som.fragile.texte")


def lignes_bivouac():
    for nom in ("sale", "bivouac"):
        _ecrire(f"{nom}.sh", script(nom))
    noter("bivouac", "pose (ok)")
    return [f" {fg(229)}{BOLD}⛺ " + t("som.bivouac.titre") + RESET, ""] + _bloc("som.bivouac.texte")


def lignes_journal(state):
    _ecrire("journal.log", journal_texte(_graine(state)))
    noter("journal", "pose (ok)")
    return [f" {fg(110)}{BOLD}📜 " + t("som.journal.titre") + RESET, ""] + _bloc("som.journal.texte")


def _reponse(et, arg, justes, cle_ok, **p):
    if not arg:
        return [t(f"som.{et}.aide")]
    r = ascii_id(_rep(arg))
    if r in [ascii_id(str(j)) for j in justes]:
        noter(et, f"{r[:24]} (ok)")
        return _ok(cle_ok, **p)
    noter(et, f"{r[:24]} (faux)")
    return _non(et)


def lignes_eboulis(state):
    g = _graine(state)
    import shutil
    shutil.rmtree(dossier() / "eboulis", ignore_errors=True)
    for rel, (nom, taille) in eboulis(g).items():
        _ecrire("eboulis/" + rel, contenu_pierre(nom, taille))
    noter("eboulis", "pose (ok)")
    return [f" {fg(250)}{BOLD}🪨 " + t("som.eboulis.titre") + RESET, ""] + _bloc("som.eboulis.texte")


def lignes_casse():
    for nom in ("casse", "boucle"):
        _ecrire(f"{nom}.sh", script(nom))
    noter("casse", "pose (ok)")
    return [f" {fg(141)}{BOLD}🩹 " + t("som.casse.titre") + RESET, ""] + _bloc("som.casse.texte")


def lignes_boussole(state):
    g = _graine(state)
    cap, pas = mission(g)
    _ecrire("boussole.sh", script_boussole(g))
    try:
        (dossier() / "arrivee.txt").unlink()
    except OSError:
        pass
    noter("boussole", f"{cap} {pas} {lieu(g, cap, pas)} pose (ok)")
    return [f" {fg(39)}{BOLD}🧭 " + t("som.boussole.titre") + RESET, ""] + _bloc("som.boussole.texte", cap=cap, pas=pas)


def lignes_ctf(state):
    g = _graine(state)
    import shutil
    shutil.rmtree(dossier() / "ctf", ignore_errors=True)
    for rel, txt in fichiers_ctf(g).items():
        _ecrire(rel, txt)
    s_(state)["ctf_debut"] = time.time()
    noter("ctf", "pose (ok)")
    from . import histoire
    mondes = ", ".join(histoire.nom_chapitre(ch) for _m, ch in mondes_au_palier(state)) or "—"
    return [f" {fg(203)}{BOLD}🚩 " + t("som.ctf.titre") + RESET, ""] + _bloc("som.ctf.texte", mondes=mondes)


def _duree(s):
    s = int(round(s))
    return f"{s // 60} min {s % 60:02d} s"


def lignes_drapeau(state, arg):
    if not arg:
        return [t("som.drapeau.aide")]
    g = _graine(state)
    if not drapeau_ok(g, arg):
        noter("drapeau", f"{_rep(arg)[:40]} (faux)")
        return _non("drapeau")
    s = s_(state)
    out = []
    debut = s.get("ctf_debut")
    if debut:
        d = max(1.0, time.time() - debut)
        avant = s.get("record_ctf")
        if not avant or d < avant:
            s["record_ctf"] = round(d, 1)
        out.append("  " + t("som.drapeau.chrono", temps=_duree(d), record=_duree(s["record_ctf"])))
        s.pop("ctf_debut", None)
    noter("drapeau", f"{drapeau(g)} (ok)")
    out = _ok("som.drapeau.ok", drapeau=drapeau(g)) + out
    if ouvert(state):                                     # l'exploit (§ 7.6) : trois mondes maîtrisés
        from . import recompenses
        msg = recompenses.exploit(state, "sommet.trois_mondes")
        if msg:
            core.log(state, msg)
            core.say(state, msg, 16)
            out.append(" " + msg)
    return out


def lignes_defi(state, arg=None):
    from . import entrainement as E
    types, verifiee = defi_du_jour(state)
    if not types:
        return [t("som.defi.aucun", cmd="`tg entrainement`")]
    if arg and arg.strip().isdigit() and 1 <= int(arg) <= len(types):
        return E.commencer(state, typ=types[int(arg) - 1])
    faits = defi_faits(state)
    out = [f" {fg(213)}{BOLD}🏔 " + t("som.defi.titre", jour=_jour_local()) + RESET, ""]
    for i, typ in enumerate(types, 1):
        f = faits.get(typ)
        marque = f"{fg(78)}✔ {E.ICONE_MEDAILLE[f['m']]}{RESET}" if f else f"{DIM}…{RESET}"
        out.append(f"  {i}. {marque} " + t(f"ent.type.{typ}.titre") + f"  {DIM}(sommet defi {i}){RESET}")
    out.append("")
    out.append("  " + t("som.defi.regle"))
    out.append("  " + t("som.defi.verifie" if verifiee else "som.defi.local"))
    if all(x in faits for x in types):
        if not dans_carnet("defi_" + _jour_local()):
            noter("defi_" + _jour_local(), "reussi (ok)")
        out.append(f" {fg(78)}🏅 " + t("som.defi.reussi") + RESET)
    return out


def lignes_records(state):
    from . import entrainement as E
    s = s_(state)
    e = E.e_(state)
    out = [f" {fg(229)}{BOLD}⏱ " + t("som.records.titre") + RESET, ""]
    out.append("  " + (t("som.records.ctf", temps=_duree(s["record_ctf"])) if s.get("record_ctf") else t("som.records.ctf_aucun")))
    v = sum(1 for r in e.get("records", {}).values() if isinstance(r, dict) and r.get("v"))
    out.append("  " + t("som.records.salle", n=len(e.get("records", {})), v=v, cmd="`tg badges records`"))
    out.append("  " + t("som.records.grades", cmd="`tg badges grades`"))
    noter("records", "lu (ok)")
    return out


def commande(args, sortie=None):
    """tg sommet [plan|fragile|bivouac|journal|dates N|alertes N|eboulis|lourd NOM|casse|ligne N|bug MOT|strace|
    boussole|arrivee LIEU|ctf|drapeau TG{…}|defi [n]|records]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_id(a[0] if a else "aide")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        s_(st)
        arg = " ".join(reste) if reste else None
        g = _graine(st)
        if sous in ("plan", "refuge", "regles"):
            lignes.extend(banniere() + t("som.meuble.refuge").split("\n") + [""] + manque(st))
        elif not ouvert(st) and sous != "aide":
            lignes.extend([f" {fg(215)}✋ " + t("som.ferme") + RESET] + manque(st))
        elif sous == "fragile":
            lignes.extend(lignes_fragile())
        elif sous == "bivouac":
            lignes.extend(lignes_bivouac())
        elif sous == "journal":
            lignes.extend(lignes_journal(st))
        elif sous == "dates":
            lignes.extend(_reponse("dates", arg, [len(dates(g))], "som.dates.ok", n=len(dates(g)), lignes=len(lignes_datees(g))))
        elif sous == "alertes":
            lignes.extend(_reponse("alertes", arg, [len(alertes(g))], "som.alertes.ok", n=len(alertes(g)),
                                   partout=len(alertes_partout(g))))
        elif sous == "eboulis":
            lignes.extend(lignes_eboulis(st))
        elif sous == "lourd":
            p = plus_lourde(g)
            lignes.extend(_reponse("lourd", arg, [p, p + ".txt"], "som.lourd.ok", nom=p, taille=plus_lourds(g, 1)[0][0]))
        elif sous == "casse":
            lignes.extend(lignes_casse())
        elif sous == "ligne":
            C = donnees()["casse"]
            lignes.extend(_reponse("ligne", arg, C["signale"], "som.ligne.ok", ligne=C["ligne"]))
        elif sous == "bug":
            lignes.extend(_reponse("bug", arg, [donnees()["boucle"]["faute"], "$" + donnees()["boucle"]["faute"]],
                                   "som.bug.ok", juste=donnees()["boucle"]["juste"]))
        elif sous == "strace":
            noter("strace", "lu (ok)")
            lignes.extend([f" {fg(250)}{BOLD}🔬 " + t("som.strace.titre") + RESET, ""] + _bloc("som.strace.texte"))
        elif sous == "boussole":
            lignes.extend(lignes_boussole(st))
        elif sous == "sections":
            lignes.extend(_bloc("som.sections.texte"))
        elif sous == "arrivee":
            cap, pas = mission(g)
            lignes.extend(_reponse("arrivee", arg, [lieu(g, cap, pas)], "som.arrivee.ok", lieu=lieu(g, cap, pas)))
        elif sous == "ctf":
            lignes.extend(lignes_ctf(st))
        elif sous == "drapeau":
            lignes.extend(lignes_drapeau(st, arg))
        elif sous in ("defi", "defis"):
            lignes.extend(lignes_defi(st, arg))
        elif sous in ("records", "record"):
            lignes.extend(lignes_records(st))
        else:
            lignes.extend(aide() + ([""] + manque(st) if not ouvert(st) else []))
    if core.modifier(f) is None:
        f({})
    if lignes:
        out.write("\n".join(lignes) + RESET + "\n")
    return 0


# ---------------------------------------------------------------- le rejeu et les simulations : l'enfant lit l'écran
def reponse_rejeu(state, cmd):
    """La commande avec les réponses que l'enfant lit à l'écran (rejeu CI, simulations, tests)."""
    g = _graine(state)
    cap, pas = mission(g)
    w1 = fragments(g)[0]
    rep = {"sommet dates ?": f"sommet dates {len(dates(g))}", "sommet alertes ?": f"sommet alertes {len(alertes(g))}",
           "sommet lourd ?": f"sommet lourd {plus_lourde(g)}", "sommet ligne ?": "sommet ligne 8",
           "sommet bug ?": "sommet bug totl", "sommet arrivee ?": f"sommet arrivee {lieu(g, cap, pas)}",
           "sommet drapeau ?": f"sommet drapeau {drapeau(g)}", "bash boussole.sh -c ? -p ?": f"bash boussole.sh -c {cap} -p {pas}",
           "bash ctf/porte.sh -k ?": f"bash ctf/porte.sh -k {w1}"}
    return rep.get(cmd, cmd)


def egal_rejeu(nom, s, graine):
    """Le rejeu en CI : la vraie sortie de bash est-elle ce que le jeu calcule pour cette partie ? (« egal_jeu »)"""
    s = (s or "").rstrip("\n")
    l = s.splitlines()
    w1, w2, w3 = fragments(graine)
    e = eboulis(graine)
    if nom == "lignes_datees":
        return s.strip() == str(len(lignes_datees(graine)))
    if nom == "dates":
        return s.strip() == str(len(dates(graine)))
    if nom == "alertes_partout":
        return s.strip() == str(len(alertes_partout(graine)))
    if nom == "dates_fr":
        return l == [date_fr(x) for x in alertes(graine)]
    if nom == "plus_lourds":
        m = [x.split(None, 1) for x in l]
        return m[0] == [str(total_eboulis(graine)), "total"] and [(int(a), b) for a, b in m[1:6]] == plus_lourds(graine)
    if nom == "nb_pierres":
        return s.strip() == f"pierres : {len(e)}"
    if nom == "diff_nord_sud":
        n_, s_ = set(noms_dans(graine, "nord")), set(noms_dans(graine, "sud"))
        return sorted(x[2:] for x in l if x.startswith("< ")) == sorted(n_ - s_) and \
            sorted(x[2:] for x in l if x.startswith("> ")) == sorted(s_ - n_)
    if nom == "premieres_lignes":
        return sorted(l) == sorted(f"eboulis/{rel} {nom_.split()[0]}" for rel, (nom_, _t) in e.items() if rel.startswith("nord/"))
    if nom == "aide_boussole":
        return s == aide_boussole()
    if nom == "arrivee":
        return s.strip() == _une_ligne(t("som.sc.boussole.arrive")) + " " + lieu(graine, *mission(graine))
    if nom == "fragment1":
        return s.strip() == f"fragment1={w1}"
    if nom == "fragment2":
        return s.strip() == f"fragment2={w2}"
    if nom == "fragment3":
        return s.strip() == f"fragment3={w3}"
    return False


def _test_os():                                         # (utilisé par les tests : le terrain du Sommet existe ?)
    return os.path.isdir(dossier())
