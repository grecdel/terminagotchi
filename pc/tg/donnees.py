"""📊 La Salle des Données — compter, trier, couper des colonnes, corriger, calculer, enchaîner et interroger une base,
sur SA PROPRE COLLECTION de créatures (docs/programme.md § 2.14 et § 7.13 « D-SQL »).

Le huitième monde de la phase 5 (§ 7.14, étape 9). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → donnees → requis). Le chapitre et le lieu s'appellent
« donnees » : ~/terrain_terminagotchi/donnees/. On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, laboratoire.txt) :
  - Les données sont celles de l'ENFANT : sa collection, exportée par le jeu (`tg collection --csv`) dans un fichier
    du terrain. Aucune donnée personnelle (ni pseudo, ni e-mail, ni adresse, ni identifiant) : l'espèce, le type, la
    famille, les stats, la rareté, shiny, la variante, le jour de la capture. Rien n'est envoyé au site, ni ailleurs.
  - Plus de bestioles d'exemple (1er novembre) : chaque exercice qui en a besoin annonce le NOMBRE MINIMUM de
    créatures (donnees.json, « minimum » : D1 3, D4 5, D-SQL 5) et OÙ aller les rencontrer ; son étape attend, sans
    bloquer le reste du jeu (on sort, on dresse, on réexporte, on revient). Le rejeu, les simulations et les tests
    jouent avec une collection de test fixe (« collection_test », jamais en partie).
  - Le jeu calcule chaque bonne réponse sur LE MÊME fichier, au moment de vérifier (la collection change d'une partie
    à l'autre, et l'enfant peut réexporter après une capture).
  - Tout reste dans le terrain (terrain_terminagotchi/donnees) : collection.csv, collection.db, les rapports.

LES PALIERS (dn0 à dn6) : la porte ; D1 compter et trier (wc, sort -n, uniq -c, head : « mes 3 bestioles les plus
fortes », comme l'épreuve « Rétro » du dressage) ; D2 les colonnes (cut -d, -f2, tr, paste : « combien de shiny ? ») ;
D3 le copiste magique (sed s///, s///g, sed -n, sed -i : « corrige le nom mal écrit partout ») ; D4 la calculatrice
(awk -F, : somme, moyenne, puis médiane et étendue) ; D5 les machines en chaîne (grep -E, xargs, tee : le rapport de
collection) ; D-SQL la base de données (sqlite3 : .tables, .schema, SELECT, WHERE, ORDER BY, COUNT, GROUP BY, JOIN,
AVG). Si sqlite3 n'est pas installé, `tg donnees sqlite3 …` fait la même chose avec le moteur SQLite de Python.

Mêmes règles sur Android (Donnees.kt : `collection --csv`, un petit awk et un petit sqlite3 intégrés, ce dernier
sur le SQLite du téléphone) ; vecteurs communs donnees/donnees/vecteurs.json.
"""
import datetime
import json
import os
import pkgutil
import re
import sqlite3
import sys
import unicodedata

from . import core
from .langue import brut, t
from .plateforme import BOLD, DIM, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "donnees.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_id(texte):
    """« Peu commune » → « peu_commune », « forêt » → « foret » : des valeurs simples à taper (grep, SQL)."""
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip().replace(" ", "_").replace("-", "_")


def jour(ms):
    """Le jour (local) d'une capture, AAAA-MM-JJ."""
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return "1970-01-01"


def ligne_individu(ind):
    """Une bestiole de la collection → les 13 valeurs de sa ligne (aucune donnée personnelle)."""
    from . import bestiaire as B, guide
    D = donnees()
    e = B.espece(ind.get("espece")) or {}
    st = ind.get("stats") or {}
    return [ind.get("espece") or "?", guide.type_ind(ind), D["familles"].get(e.get("famille"), "?")] + \
        [str(int(st.get(D["stats"][c], 0))) for c in ("attaque", "defense", "vitesse", "pv", "intelligence")] + \
        [ascii_id(B.rarete_de(ind)), "1" if ind.get("shiny") else "0", ascii_id(ind.get("variante") or "classique"),
         jour(ind.get("date"))]


def lignes_collection(captures):
    """Les lignes du tableau : la collection, telle qu'elle est (plus aucune bestiole d'exemple ajoutée)."""
    return [ligne_individu(c) for c in captures or [] if c.get("espece")]


def collection_test():
    """La collection de TEST (rejeu, simulations, tests) : des captures fixes, jamais données en partie."""
    import copy
    return copy.deepcopy(donnees()["collection_test"])


def minimum(lid):
    """Le nombre minimum de créatures demandé par une leçon (0 : aucun)."""
    return int(donnees()["minimum"].get(lid, 0))


def assez(lid, rows=None):
    """Le tableau collection.csv a assez de lignes pour la leçon."""
    rows = lignes_du_fichier() if rows is None else rows
    return rows is not None and len(rows) >= minimum(lid)


def lignes_minimum(lid, n, cmd="tg collection --csv > collection.csv"):
    """« Il te faut au moins X créatures… » et où aller les rencontrer : l'étape attend, rien n'est bloqué."""
    return [f" {fg(215)}✋ " + t("dn.minimum", min=minimum(lid), n=n) + RESET] + _bloc("dn.minimum.ou", cmd=f"`{cmd}`")


def csv_texte(rows):
    return ",".join(donnees()["colonnes"]) + "\n" + "".join(",".join(r) + "\n" for r in rows)


def lire_csv(texte):
    """[{colonne: valeur}] des lignes bien formées (la ligne des titres et les lignes abîmées sont ignorées)."""
    cols = donnees()["colonnes"]
    out = []
    for i, l in enumerate((texte or "").splitlines()):
        v = l.split(",")
        if i == 0 and v and v[0] == cols[0]:
            continue
        if len(v) != len(cols) or not v[3].strip().lstrip("-").isdigit():
            continue
        out.append(dict(zip(cols, v)))
    return out


def effectifs(valeurs):
    c = {}
    for v in valeurs:
        c[v] = c.get(v, 0) + 1
    return sorted(c.items(), key=lambda x: (-x[1], x[0]))


def attaques(rows):
    return [int(r["attaque"]) for r in rows]


def forces_txt(rows):
    return "".join(f"{r['attaque']} {r['nom']}\n" for r in rows)


def especes_txt(rows):
    return "".join(r["nom"] + "\n" for r in rows)


def top3(rows):
    """Les 3 plus grandes attaques (avec leurs ex aequo, n'importe lequel convient)."""
    return sorted(attaques(rows), reverse=True)[:3]


def nb_shiny(rows):
    return sum(1 for r in rows if r["shiny"] == "1")


def somme(rows):
    return sum(attaques(rows))


def moyenne(rows):
    a = attaques(rows)
    return sum(a) / len(a) if a else 0.0


def medianes(rows):
    """Les réponses justes pour la médiane : la valeur du milieu ; avec un nombre pair, les deux du milieu et leur
    moyenne (les trois sont acceptées, la leçon explique)."""
    a = sorted(attaques(rows))
    if not a:
        return []
    n = len(a)
    if n % 2:
        return [float(a[n // 2])]
    x, y = a[n // 2 - 1], a[n // 2]
    return sorted({float(x), float(y), (x + y) / 2})


def etendue(rows):
    a = attaques(rows)
    return max(a) - min(a) if a else 0


def types_majoritaires(rows):
    e = effectifs([r["type"] for r in rows])
    return [ty for ty, n in e if n == e[0][1]] if e else []


def nombre_awk(x):
    """Comment awk écrit un nombre avec print (OFMT %.6g ; un entier s'écrit sans virgule)."""
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    s = "%.6g" % x
    return s


def nombre_ok(rep, juste, tolerance=0.5):
    try:
        x = float(str(rep).strip().replace(",", "."))
    except ValueError:
        return False
    return abs(x - juste) <= tolerance


# ---------------------------------------------------------------- D3 : le carnet du soigneur et son nom mal écrit
def cible_faute(rows):
    """Le nom que le soigneur écrit mal : l'espèce que l'enfant a le plus (à égalité, la première dans l'ordre)."""
    e = effectifs([r["nom"] for r in rows])
    return e[0][0] if e else None


def faute(nom, interdits=()):
    """Le nom mal écrit : deux lettres voisines échangées au milieu (Gloupi → Gluopi), jamais la première lettre, jamais
    un autre vrai nom ; repli : la dernière lettre doublée."""
    n = len(nom)
    ordre = sorted(range(1, n - 1), key=lambda i: (abs(i - (n - 1) // 2), i))
    for i in ordre:
        a, b = nom[i], nom[i + 1]
        if a != b and a.isalpha() and b.isalpha() and a.lower() == a and b.lower() == b:
            f = nom[:i] + b + a + nom[i + 2:]
            if f not in interdits and f != nom:
                return f
    return nom + nom[-1]


def carnet_soigneur(rows):
    """(texte mal écrit, texte juste, nom mal écrit, bon nom) : 7 lignes de la collection de l'enfant ; le nom visé
    apparaît sur 3 lignes, dont une DEUX fois (pour voir pourquoi il faut /g)."""
    from . import bestiaire as B
    cible = cible_faute(rows)
    if not cible:
        return "", "", "", ""
    autres = [n for n in dict.fromkeys(r["nom"] for r in rows) if n != cible] or [cible]
    o = [autres[i % len(autres)] for i in range(3)]
    gabarits = [("dn.carnet.l1", cible), ("dn.carnet.l2", o[0]), ("dn.carnet.l3", cible), ("dn.carnet.l4", o[1]),
                ("dn.carnet.double", cible), ("dn.carnet.l5", o[2])]
    juste = ["# " + t("dn.carnet.titre")] + [t(k, nom=n) for k, n in gabarits]
    f = faute(cible, {e["nom"] for e in B.donnees()["especes"]})
    fautif = [juste[0]] + [l.replace(cible, f) if k in ("dn.carnet.l1", "dn.carnet.l3", "dn.carnet.double") else l
                           for (k, _n), l in zip(gabarits, juste[1:])]
    return "\n".join(fautif) + "\n", "\n".join(juste) + "\n", f, cible


# ---------------------------------------------------------------- D-SQL : la base et le petit sqlite3 de secours
def valeur_sql(v):
    """Une valeur comme l'outil sqlite3 l'écrit (mode « list ») : un nombre réel avec 15 chiffres significatifs et
    toujours un point (24.0), un entier tel quel, NULL vide."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = "%.15g" % v
        if "inf" in s or "nan" in s:
            return s
        m, e, x = s.partition("e")
        if "." not in m:                        # le drapeau « ! » de sqlite3 : toujours un point (24.0, 1.0e+20)
            m += ".0"
        return m + e + x
    return str(v)


def lignes_resultat(rows_resultat, sep="|"):
    return [sep.join(valeur_sql(v) for v in r) for r in rows_resultat]


def tables_texte(noms):
    """.tables : les noms rangés, en colonnes séparées de 2 espaces (sur une ligne pour quelques tables). Comme le vrai
    outil sqlite3, CHAQUE nom est complété à la largeur de la colonne, le dernier aussi (espaces en fin de ligne : vu
    par le rejeu en CI, sqlite3 3.45)."""
    noms = sorted(noms)
    if not noms:
        return ""
    w = max(len(n) for n in noms)
    return "  ".join(n.ljust(w) for n in noms)


def requetes_base(rows):
    """Les instructions SQL qui fabriquent collection.db (les mêmes sur Android) : [(sql, paramètres)]."""
    from . import bestiaire as B
    S = donnees()["schema"]
    out = [(S["creatures"], ()), (S["especes"], ())]
    for r in rows:
        out.append(("INSERT INTO creatures VALUES (" + ",".join("?" * len(donnees()["colonnes"])) + ")",
                    tuple(int(r[c]) if c in ("attaque", "defense", "vitesse", "pv", "intelligence", "shiny")
                          else r[c] for c in donnees()["colonnes"])))
    for nom in dict.fromkeys(r["nom"] for r in rows):
        e = B.espece(nom)
        if e:
            out.append(("INSERT INTO especes VALUES (?,?,?,?)", (e["nom"], e["numero"], ascii_id(e["habitat"]),
                                                                 e.get("puissance", 1))))
    return out


def creer_base(chemin, rows):
    try:
        if os.path.exists(chemin):
            os.remove(chemin)
        c = sqlite3.connect(chemin)
        with c:
            for sql, p in requetes_base(rows):
                c.execute(sql, p)
        c.close()
        return True
    except (OSError, sqlite3.Error):
        return False


def sqlite_cli(chemin, sql, entete=False):
    """Le petit sqlite3 de secours (moteur SQLite de Python) : (texte, code). .tables, .schema [table], SELECT …"""
    if not os.path.isfile(chemin):
        return t("dn.sql.pas_de_base", fichier=os.path.basename(chemin)), 1
    try:
        c = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    except sqlite3.Error as e:
        return f"Error: {e}", 1
    try:
        s = (sql or "").strip()
        if s.startswith(".tables"):
            noms = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            return tables_texte(noms), 0
        if s.startswith(".schema"):
            a = s.split()[1:]
            q = "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL" + (" AND name = ?" if a else "") + " ORDER BY name"
            return "\n".join(r[0] + ";" for r in c.execute(q, tuple(a[:1]))), 0
        if s.startswith("."):
            return t("dn.sql.point_inconnu", cmd=s.split()[0]), 1
        out = []
        for instr in [x for x in s.split(";") if x.strip()]:
            cur = c.execute(instr)
            if entete and cur.description:
                out.append("|".join(d[0] for d in cur.description))
            out += lignes_resultat(cur.fetchall())
        return "\n".join(out), 0
    except sqlite3.Error as e:
        return f"Error: {e}", 1
    finally:
        c.close()


# ---------------------------------------------------------------- le laboratoire de tri (vue déployée)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def labo_de(morceau):
    """(outil, instrument, de, vers) d'une commande (un morceau de ligne), ou None : la première règle de donnees.json."""
    m = (morceau or "").strip()
    for r in donnees()["labo"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["instrument"], r["de"], r["vers"]
    return None


def labos_de(ligne):
    return [a for a in (labo_de(m) for m in SEPARATEURS.split(ligne or "")) if a]


# ================================================================ l'état, le terrain, le carnet de la salle
def d_(state):
    c = state.setdefault("donnees", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "donnees"


CARNET = "carnet_des_donnees.txt"
CSV = "collection.csv"


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


def _ecrire(rel, contenu):
    p = dossier() / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def lignes_du_fichier():
    """Les lignes de collection.csv (celui du terrain, tel que l'enfant l'a exporté), ou None s'il n'existe pas."""
    txt = _lire(CSV)
    return None if txt is None else lire_csv(txt)


def meubles(state):
    """Ce que le jeu pose dans la Salle des Données quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    return {"donnees/laboratoire.txt": t("dn.meuble.laboratoire") + "\n",
            f"donnees/{CARNET}": t("dn.meuble.carnet") + "\n"}


BESOINS = {"dn0": ["laboratoire.txt"]}


def meubler(state, lid, step):
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire(rel, tous["donnees/" + rel])
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = d_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("dn.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("dn.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- les vérifications des étapes
def _csv_ok():
    r = lignes_du_fichier()
    txt = _lire(CSV) or ""
    return r is not None and bool(r) and txt.startswith(",".join(donnees()["colonnes"])) and assez("dn1", r)


def _top3_ok():
    rows = lignes_du_fichier()
    txt = _lire("top3.txt")
    if not rows or txt is None:
        return False
    l = [x.split() for x in txt.splitlines() if x.strip()]
    try:
        vals = [int(x[0]) for x in l]
    except (ValueError, IndexError):
        return False
    return len(l) == 3 and vals == top3(rows)


def _noms_types_ok():
    """noms.txt et types.txt : la colonne 1 et la colonne 2 (avec ou sans la ligne des titres)."""
    rows = lignes_du_fichier()
    n, ty = _lire("noms.txt"), _lire("types.txt")
    if not rows or n is None or ty is None:
        return False
    sans = lambda t_, titre: [x for x in t_.splitlines() if x.strip() and x != titre]   # noqa: E731
    return sans(n, "nom") == [r["nom"] for r in rows] and sans(ty, "type") == [r["type"] for r in rows]


def _texte_juste(rel):
    rows = lignes_du_fichier()
    txt = _lire(rel)
    if not rows or txt is None:
        return False
    _f, juste, _m, _b = carnet_soigneur(rows)
    return txt.strip("\n") == juste.strip("\n")


def _attaques_ok():
    rows = lignes_du_fichier()
    txt = _lire("attaques.txt")
    if not rows or txt is None:
        return False
    try:
        return [int(x) for x in txt.split()] == sorted(attaques(rows))
    except ValueError:
        return False


def _enclos_ok():
    rows = lignes_du_fichier()
    try:
        fichiers = {p.name for p in (dossier() / "enclos").iterdir()}
    except OSError:
        return False
    return bool(rows) and all(f"{n}.txt" in fichiers for n in {r["nom"] for r in rows})


def _rapport():
    return [x for x in (_lire("rapport.txt") or "").splitlines() if x.strip()]


def _rapport_top_ok():
    rows = lignes_du_fichier()
    l = _rapport()
    if not rows or len(l) < 3:
        return False
    try:
        return [int(x.split(",")[3]) for x in l[:3]] == top3(rows)
    except (ValueError, IndexError):
        return False


def _rapport_moyenne_ok():
    rows = lignes_du_fichier()
    if not rows or not _rapport_top_ok():
        return False
    for x in _rapport()[3:]:
        m = x.split()
        if len(m) == 2 and nombre_ok(m[1], moyenne(rows), 0.01):
            return True
    return False


FS = {
    "dn_csv": _csv_ok,
    "dn_combien": lambda: dans_carnet("combien"),
    "dn_top3": _top3_ok,
    "dn_shiny": lambda: dans_carnet("shiny"),
    "dn_noms_types": _noms_types_ok,
    "dn_corrige": lambda: _texte_juste("carnet_corrige.txt"),
    "dn_sed_i": lambda: _texte_juste("carnet_du_soigneur.txt"),
    "dn_calcul": lambda: dans_carnet("calcul") and assez("dn4"),
    "dn_moyenne": lambda: dans_carnet("moyenne"),
    "dn_attaques": _attaques_ok,
    "dn_mediane": lambda: dans_carnet("mediane"),
    "dn_etendue": lambda: dans_carnet("etendue"),
    "dn_enclos": _enclos_ok,
    "dn_rapport_top": _rapport_top_ok,
    "dn_rapport_moyenne": _rapport_moyenne_ok,
    "dn_bilan": lambda: dans_carnet("bilan"),
    "dn_base": lambda: (dossier() / "collection.db").is_file() and dans_carnet("base") and assez("dn6"),
    "dn_sql": lambda: dans_carnet("sql"),
}
CREE = {}

# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
DN = r"^(tg\s+)?donnees\s+"
CUT_D = r"^cut\b(?=.*-d\s*['\"]?,)"           # le séparateur virgule est obligatoire (sans lui, cut coupe aux tabulations)
AWK_F = r"^awk\b(?=.*-F\s*['\"]?,)"           # (sans -F, awk coupe aux espaces : le calcul serait faux)
SQ = r"^(tg\s+)?(donnees\s+)?sqlite3\s+(-\w+\s+)*collection\.db\s+"
O = "donnees"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


def _sq(lid, i, requete, re_, **k):
    """Une étape sqlite3 : la vraie commande, et sans sqlite3 installé, la même requête par le petit sqlite3 du jeu."""
    cmd = f"sqlite3 collection.db {requete}"
    return _n(lid, i, cmd=cmd, re=SQ + re_, ou=O, repli=["tg donnees " + cmd], **k)


LECONS = {
    # la porte de la Salle des Données
    "dn0": {"titre": "hist.dn0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "donnees"}), "cmd": "cd ~/terrain_terminagotchi/donnees",
         "ici": "donnees", "bravo": ("hist.entree.bravo", {"piece": "donnees"})},
        _n("dn0", 1, cmd="ls", re=LS, ou=O),
        _n("dn0", 2, cmd="cat laboratoire.txt", re=LIRE + r".*laboratoire", ou=O),
    ]},
    # D1 compter et trier : wc, sort -n, uniq -c, head
    "dn1": {"titre": "hist.dn1.titre", "skill": None, "steps": [
        _n("dn1", 0, cmd="tg collection --csv > collection.csv", fs="dn_csv", ou=O),
        _n("dn1", 1, cmd="head -3 collection.csv", re=LIRE + r".*collection\.csv", ou=O),
        _n("dn1", 2, cmd="wc -l collection.csv", re=r"^wc\b.*-l.*collection\.csv|^wc\b.*collection\.csv", ou=O),
        _n("dn1", 3, cmd="donnees combien ?", fs="dn_combien"),
        _n("dn1", 4, cmd="donnees trier", re=DN + r"tri", ou=O),
        _n("dn1", 5, cmd="sort especes.txt | uniq -c | sort -rn | head -3",
           re=r"^sort\b.*especes\.txt.*\|\s*uniq\s+-c|^(cat\s+especes\.txt\s*\|\s*)sort\b.*\|\s*uniq\s+-c", ou=O),
        _n("dn1", 6, cmd="sort -nr forces.txt | head -3 > top3.txt", fs="dn_top3", ou=O),
    ]},
    # D2 les colonnes : cut, tr, paste
    "dn2": {"titre": "hist.dn2.titre", "skill": None, "steps": [
        _n("dn2", 0, cmd="donnees colonnes", re=DN + r"colonnes?\s*$", ou=O),
        _n("dn2", 1, cmd="head -1 collection.csv | tr ',' '\\n'", re=r"^head\b.*collection\.csv.*\|\s*tr\b", ou=O),
        _n("dn2", 2, cmd="cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c",
           re=CUT_D + r"(?=.*-f\s*2\b).*collection\.csv.*\|.*uniq\s+-c", ou=O),
        _n("dn2", 3, cmd="cut -d, -f10 collection.csv | grep -c 1", re=CUT_D + r"(?=.*-f\s*10\b).*\|\s*grep\b",
           ou=O, tout_code=True),
        _n("dn2", 4, cmd="donnees shiny ?", fs="dn_shiny"),
        _n("dn2", 5, cmd="cut -d, -f1 collection.csv > noms.txt && cut -d, -f2 collection.csv > types.txt",
           fs="dn_noms_types", ou=O),
        _n("dn2", 6, cmd="paste -d: noms.txt types.txt | head -5", re=r"^paste\b.*noms\.txt.*types\.txt|^paste\b.*types\.txt.*noms", ou=O),
    ]},
    # D3 le copiste magique : sed
    "dn3": {"titre": "hist.dn3.titre", "skill": None, "steps": [
        _n("dn3", 0, cmd="donnees copiste", re=DN + r"copiste", ou=O),
        _n("dn3", 1, cmd="cat carnet_du_soigneur.txt", re=LIRE + r".*carnet_du_soigneur", ou=O),
        _n("dn3", 2, cmd="sed 's/?/?/' carnet_du_soigneur.txt",
           re=r"^sed\s+(-\w+\s+)*(['\"])s/[^/?]+/[^/?]+/\2\s+carnet_du_soigneur", ou=O),
        _n("dn3", 3, cmd="sed 's/?/?/g' carnet_du_soigneur.txt > carnet_corrige.txt", fs="dn_corrige", ou=O),
        _n("dn3", 4, cmd="diff carnet_du_soigneur.txt carnet_corrige.txt", re=r"^diff\b.*carnet_du_soigneur.*carnet_corrige|^diff\b.*carnet_corrige.*carnet_du",
           ou=O, tout_code=True),
        _n("dn3", 5, cmd="sed -n '2,4p' carnet_corrige.txt", re=r"^sed\s+-n\s+['\"]?\d+,\d+p['\"]?\s+carnet_corrige", ou=O),
        _n("dn3", 6, cmd="sed -i 's/?/?/g' carnet_du_soigneur.txt", fs="dn_sed_i", ou=O, win=False),
    ]},
    # D4 la calculatrice des savants : awk
    "dn4": {"titre": "hist.dn4.titre", "skill": None, "steps": [
        _n("dn4", 0, cmd="donnees calcul", fs="dn_calcul", ou=O),
        _n("dn4", 1, cmd="awk -F, 'NR<=5 {print $1, $4}' collection.csv", re=AWK_F + r".*\$1.*\$4.*collection\.csv", ou=O,
           win=False),
        _n("dn4", 2, cmd="awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv", re=AWK_F + r".*\+=\s*\$4.*END.*collection\.csv", ou=O,
           win=False),
        _n("dn4", 3, cmd="awk -F, 'NR>1 {s+=$4; n++} END {print s/n}' collection.csv", re=AWK_F + r".*\+=\s*\$4.*END.*/.*collection\.csv",
           ou=O, win=False),
        _n("dn4", 4, cmd="donnees moyenne ?", fs="dn_moyenne"),   # (l'exploit : seulement sur SA vraie collection)
        _n("dn4", 5, cmd="cut -d, -f4 collection.csv | tail -n +2 | sort -n > attaques.txt", fs="dn_attaques", ou=O),
        _n("dn4", 6, cmd="donnees mediane ?", fs="dn_mediane"),
        _n("dn4", 7, cmd="sed -n '1p;$p' attaques.txt", re=r"^(sed\b.*attaques\.txt|head\b.*attaques\.txt|tail\b.*attaques\.txt)", ou=O),
        _n("dn4", 8, cmd="donnees etendue ?", fs="dn_etendue"),
    ]},
    # D5 les machines en chaîne : grep -E, xargs, tee
    "dn5": {"titre": "hist.dn5.titre", "skill": None, "steps": [
        _n("dn5", 0, cmd="donnees chaine", re=DN + r"cha[iî]ne", ou=O),
        _n("dn5", 1, cmd="grep -E 'eau|glace' collection.csv", re=r"^grep\b.*-\w*E.*\|.*collection\.csv|^egrep\b.*collection\.csv", ou=O,
           tout_code=True),
        _n("dn5", 2, cmd="cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs echo", re=CUT_D + r".*\|\s*xargs\b", ou=O, win=False),
        _n("dn5", 3, cmd="mkdir -p enclos && cut -d, -f1 collection.csv | tail -n +2 | sort -u | sed 's|.*|enclos/&.txt|' | xargs touch",
           fs="dn_enclos", ou=O, win=False),
        _n("dn5", 4, cmd="sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt", fs="dn_rapport_top", ou=O),
        _n("dn5", 5, cmd="awk -F, 'NR>1 {s+=$4; n++} END {print \"moyenne\", s/n}' collection.csv >> rapport.txt",
           fs="dn_rapport_moyenne", ou=O, win=False),
        _n("dn5", 6, cmd="donnees bilan", fs="dn_bilan"),
    ]},
    # D-SQL la base de données : sqlite3
    "dn6": {"titre": "hist.dn6.titre", "skill": None, "steps": [
        _n("dn6", 0, cmd="donnees base", fs="dn_base", ou=O),
        _sq("dn6", 1, ".tables", r"['\"]?\.tables"),
        _sq("dn6", 2, "\".schema creatures\"", r"['\"]?\.schema"),
        _sq("dn6", 3, "\"SELECT nom, attaque FROM creatures ORDER BY attaque DESC LIMIT 3;\"",
            r"['\"]\s*select\b.*\border\s+by\b"),
        _sq("dn6", 4, "\"SELECT nom, variante FROM creatures WHERE type = 'eau';\"", r"['\"]\s*select\b.*\bwhere\b"),
        _sq("dn6", 5, "\"SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;\"",
            r"['\"]\s*select\b.*\bcount\s*\(.*\bgroup\s+by\b"),
        _n("dn6", 6, cmd="donnees sql ?", fs="dn_sql"),
        _sq("dn6", 7, "\"SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom LIMIT 5;\"",
            r"['\"]\s*select\b.*\bjoin\b"),
        _sq("dn6", 8, "\"SELECT AVG(attaque) FROM creatures;\"", r"['\"]\s*select\b.*\bavg\s*\("),
    ]},
}
CHAPITRE = {"id": "donnees", "n": 18, "piece": "donnees", "famille": "Abyssaux", "monde": True,
            "lecons": [f"dn{i}" for i in range(7)], "objet": "boulier", "titre": "savant_des_donnees"}


# ================================================================ l'arbre du Carrefour : quand la Salle s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "donnees"), {})


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
    if "donnees" in deja or histoire.fini(state, "donnees") or not ouvert(state):
        return False
    deja.append("donnees")
    core.log(state, t("dn.ouvert.log"))
    core.say(state, histoire.dire(state, "dn.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s|/)(\?|…|<[^>]*>)(\s|/|$)")
REPONSES = {"donnees combien ?": "combien", "donnees shiny ?": "shiny", "donnees moyenne ?": "moyenne",
            "donnees mediane ?": "mediane", "donnees etendue ?": "etendue", "donnees sql ?": "sql"}


def indice(step, tapees):
    """Un indice de la Salle des Données : le tableau pas encore exporté, un « ? » recopié, une mauvaise réponse, le
    séparateur oublié (-F, ou -d,), un sed sans /g, une redirection oubliée, sqlite3 absent ou une requête sans
    guillemets."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if not (dossier() / CSV).is_file() and step.get("fs") != "dn_csv" and any("collection.csv" in l for l in lignes):
        return t("dn.indice.pas_de_csv")
    fs = step.get("fs")
    for f_, lid in (("dn_csv", "dn1"), ("dn_calcul", "dn4"), ("dn_base", "dn6")):   # pas assez de créatures : où aller
        rows = lignes_du_fichier()
        if fs == f_ and rows is not None and not assez(lid, rows):
            return t("dn.minimum", min=minimum(lid), n=len(rows))
    if fs == "dn_csv":
        if any(re.match(r"^(tg\s+)?collection\b", l) and "--csv" not in l for l in lignes):
            return t("dn.indice.csv_option")
        if any(re.match(r"^(tg\s+)?collection\b.*--csv", l) and ">" not in l for l in lignes):
            return t("dn.indice.redirection")
    if "?" in cmd.split() or "/?/" in cmd:
        if any(TROU.search(l) or "/?/" in l for l in lignes if re.match(DN, l) or l.startswith("sed")):
            return t("dn.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = dernier(et)                                # seulement juste après une réponse (pas après nl…)
        if der and not der.endswith("(ok)") and any(re.match(DN + et, l) for l in lignes):
            return t("dn.indice.rep." + et)
    if fs == "dn_top3" and any(l.startswith("sort") and ">" not in l for l in lignes):
        return t("dn.indice.redirection")
    if fs in ("dn_corrige", "dn_sed_i") and any(re.match(r"^sed\b", l) and not re.search(r"/g['\"]", l) for l in lignes):
        return t("dn.indice.sed_g")
    if fs == "dn_corrige" and any(re.match(r"^sed\b.*/g", l) and ">" not in l for l in lignes):
        return t("dn.indice.redirection")
    if (cmd.startswith("awk") or fs == "dn_rapport_moyenne") and any(l.startswith("awk") and "-F" not in l for l in lignes):
        return t("dn.indice.awk_f")
    if cmd.startswith("cut") and any(l.startswith("cut") and "-d" not in l for l in lignes):
        return t("dn.indice.cut_d")
    if "sqlite3" in cmd:
        import shutil
        if any(re.match(r"^sqlite3\b", l) for l in lignes) and not shutil.which("sqlite3"):
            return t("dn.indice.sqlite_absent")
        if any(re.match(r"^(tg\s+)?(donnees\s+)?sqlite3\b.*\bselect\b", l, re.I) and not re.search(r"['\"]", l) for l in lignes):
            return t("dn.indice.guillemets")
    return None


def surveiller(state, lignes):
    """La Salle des Données n'a pas de danger à guetter : tout est lu et écrit dans le terrain."""
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
LABO = ["   ╔═══╦═══╦═══╗  📊", "   ║ ⚗ ║ ✂ ║ ⚙ ║  ▁▃▅▇", "   ╠═══╬═══╬═══╣", "   ║ 🔍║ ✎ ║ 🧮║  ▇▅▃▁",
        "   ╚═══╩═══╩═══╝"]


def banniere(largeur=None):
    """L'entrée de la Salle des Données : l'illustration (illustrations.bin, « donnees ») si elle existe, sinon le REPLI
    dessiné en caractères (le laboratoire de tri et ses instruments)."""
    try:
        from . import scenes
        if scenes.disponible("donnees"):
            return scenes.illustration("donnees", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [39, 117, 229, 215, 78]
    return [f"  {fg(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(LABO)]


def aide():
    return banniere() + [f" {fg(39)}{BOLD}📊 " + t("dn.aide.titre") + RESET] + \
        ["  " + l for l in t("dn.aide.liste").split("\n")]


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def _sans_csv():
    return [f" {fg(215)}✋ " + t("dn.pas_de_csv") + RESET]


def export_csv(state):
    """`tg collection --csv` : (le tableau, le message pour l'écran). Le message (sur la sortie d'erreur) dit, pour une
    petite collection, combien de créatures demandent les exercices et où aller les rencontrer."""
    rows = lignes_collection(state.get("captures", []))
    besoin = max(donnees()["minimum"].values())
    msg = t("dn.csv.ok", n=len(rows))
    if len(rows) < besoin:
        msg += "\n" + t("dn.csv.peu", min=besoin) + "\n" + t("dn.minimum.ou", cmd="`tg collection --csv > collection.csv`")
    return csv_texte(rows), msg


def commande_collection_csv(sortie=None, erreur=None):
    out = sortie if sortie is not None else sys.stdout
    err = erreur if erreur is not None else sys.stderr
    st = core.load()
    texte, msg = export_csv(st)
    out.write(texte)
    err.write("📊 " + msg + "\n")


def _rep(arg):
    return (arg or "").strip()


def lignes_combien(arg):
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not arg:
        return [t("dn.combien.aide")]
    if _rep(arg) == str(len(rows)):
        noter("combien", f"{len(rows)} (ok)")
        return [f" {fg(78)}✔ " + t("dn.combien.ok", n=len(rows), l=len(rows) + 1) + RESET]
    noter("combien", f"{_rep(arg)[:12]} (faux)")
    return [f" {fg(203)}✖ " + t("dn.indice.rep.combien") + RESET]


def lignes_trier():
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    _ecrire("especes.txt", especes_txt(rows))
    _ecrire("forces.txt", forces_txt(rows))
    noter("trier", "especes forces (ok)")
    return [f" {fg(229)}{BOLD}⚙ " + t("dn.trier.titre") + RESET, ""] + _bloc("dn.trier.texte")


def lignes_colonnes():
    cols = donnees()["colonnes"]
    texte = "\n".join(f"{i + 1:>2}  {c:<13} " + t("dn.col." + c) for i, c in enumerate(cols))
    _ecrire("colonnes.txt", texte + "\n")
    noter("colonnes", "lu (ok)")
    return [f" {fg(203)}{BOLD}✂ " + t("dn.colonnes.titre") + RESET, ""] + ["  " + l for l in texte.split("\n")] + \
        [""] + _bloc("dn.colonnes.texte")


def lignes_shiny(arg):
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not arg:
        return [t("dn.shiny.aide")]
    n = nb_shiny(rows)
    if _rep(arg) == str(n):
        noter("shiny", f"{n} (ok)")
        pc = n * 100 // len(rows) if rows else 0
        return [f" {fg(78)}✔ " + t("dn.shiny.ok", n=n, total=len(rows), pc=pc) + RESET]
    noter("shiny", f"{_rep(arg)[:12]} (faux)")
    return [f" {fg(203)}✖ " + t("dn.indice.rep.shiny") + RESET]


def lignes_copiste():
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    fautif, _juste, f, bon = carnet_soigneur(rows)
    if not (dossier() / "carnet_du_soigneur.txt").exists() or not dans_carnet("copiste"):
        _ecrire("carnet_du_soigneur.txt", fautif)
    noter("copiste", f"{f} {bon} (ok)")
    return [f" {fg(141)}{BOLD}✎ " + t("dn.copiste.titre") + RESET, ""] + _bloc("dn.copiste.texte", faute=f, bon=bon)


def lignes_calcul():
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not assez("dn4", rows):
        noter("calcul", f"{len(rows)} (pas assez)")
        return lignes_minimum("dn4", len(rows))
    noter("calcul", "lu (ok)")
    return [f" {fg(215)}{BOLD}🧮 " + t("dn.calcul.titre") + RESET, ""] + _bloc("dn.calcul.texte")


def _reponse_nombre(etiquette, arg, justes, cle_ok, **p):
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not arg:
        return [t(f"dn.{etiquette}.aide")]
    if any(nombre_ok(arg, j) for j in justes):
        noter(etiquette, f"{_rep(arg)[:12]} (ok)")
        return [f" {fg(78)}✔ " + t(cle_ok, **p) + RESET]
    noter(etiquette, f"{_rep(arg)[:12]} (faux)")
    return [f" {fg(203)}✖ " + t(f"dn.indice.rep.{etiquette}") + RESET]


def sa_collection(state, rows):
    """Le tableau est bien SA collection (celle de la partie, telle que `tg collection --csv` l'exporte), pas un
    fichier écrit à la main : l'exploit « une statistique juste » ne se gagne que là."""
    vraie = [dict(zip(donnees()["colonnes"], r)) for r in lignes_collection(state.get("captures", []))]
    cle = lambda r: tuple(r.get(c, "") for c in donnees()["colonnes"])   # noqa: E731
    return bool(rows) and sorted(map(cle, rows)) == sorted(map(cle, vraie))


def lignes_moyenne(state, arg):
    rows = lignes_du_fichier() or []
    m = moyenne(rows)
    out = _reponse_nombre("moyenne", arg, [m], "dn.moyenne.ok", m=nombre_awk(m), s=somme(rows), n=len(rows))
    if dans_carnet("moyenne"):
        out.append("  " + t("dn.moyenne.morale"))
    if arg and (dernier("moyenne") or "").endswith("(ok)") and sa_collection(state, rows):
        from . import recompenses                         # l'exploit (§ 7.6) : une statistique juste sur SA collection
        msg = recompenses.exploit(state, "donnees.statistique")
        if msg:
            core.log(state, msg)
            core.say(state, msg, 16)
            out.append(" " + msg)
    return out


def lignes_mediane(arg):
    rows = lignes_du_fichier() or []
    ms = medianes(rows)
    return _reponse_nombre("mediane", arg, ms, "dn.mediane.ok", m=" / ".join(nombre_awk(x) for x in ms), n=len(rows),
                           moy=nombre_awk(moyenne(rows)))


def lignes_etendue(arg):
    rows = lignes_du_fichier() or []
    a = attaques(rows) or [0]
    return _reponse_nombre("etendue", arg, [etendue(rows)], "dn.etendue.ok", e=etendue(rows), max=max(a), min=min(a))


def lignes_chaine():
    noter("chaine", "lu (ok)")
    return [f" {fg(39)}{BOLD}🔗 " + t("dn.chaine.titre") + RESET, ""] + _bloc("dn.chaine.texte")


def lignes_bilan(state):
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not (_rapport_top_ok() and _rapport_moyenne_ok()):
        noter("bilan", "pas encore (faux)")
        return [f" {fg(215)}✋ " + t("dn.bilan.pas_encore") + RESET]
    especes = len({r["nom"] for r in rows})
    certif = t("dn.bilan.texte", n=len(rows), especes=especes, top=top3(rows)[0], m=nombre_awk(moyenne(rows)),
               shiny=nb_shiny(rows))
    _ecrire("certificat_du_savant.txt", certif + "\n")
    noter("bilan", "rapport (ok)")
    return [f" {fg(78)}{BOLD}🏅 " + t("dn.bilan.titre") + RESET, ""] + ["  " + l for l in certif.split("\n")]


def lignes_base():
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not assez("dn6", rows):
        noter("base", f"{len(rows)} (pas assez)")
        return lignes_minimum("dn6", len(rows))
    if not creer_base(str(dossier() / "collection.db"), rows):
        return [f" {fg(203)}✖ " + t("dn.base.rate") + RESET]
    noter("base", f"{len(rows)} (ok)")
    import shutil
    out = [f" {fg(179)}{BOLD}🗄 " + t("dn.base.titre") + RESET, ""] + _bloc("dn.base.texte", n=len(rows))
    if not shutil.which("sqlite3"):
        out += ["", "  " + t("dn.base.sans_sqlite3")]
    return out


def lignes_sql(arg):
    rows = lignes_du_fichier()
    if rows is None:
        return _sans_csv()
    if not arg:
        return [t("dn.sql.aide")]
    bons = types_majoritaires(rows)
    if ascii_id(arg) in bons:
        noter("sql", f"{ascii_id(arg)} (ok)")
        e = effectifs([r["type"] for r in rows])
        return [f" {fg(78)}✔ " + t("dn.sql.ok", type=ascii_id(arg), n=e[0][1], total=len(rows)) + RESET]
    noter("sql", f"{ascii_id(arg)[:12]} (faux)")
    return [f" {fg(203)}✖ " + t("dn.indice.rep.sql") + RESET]


def commande(args, sortie=None):
    """tg donnees [plan|combien N|trier|colonnes|shiny N|copiste|calcul|moyenne X|mediane X|etendue X|chaine|bilan|
    base|sql TYPE|sqlite3 collection.db "REQUÊTE"]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_id(a[0] if a else "aide")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    if sous == "sqlite3":                               # le petit sqlite3 de secours (moteur SQLite de Python)
        entete = "-header" in reste
        r = [x for x in reste if not x.startswith("-")]
        if len(r) < 2:
            out.write(t("dn.sql.aide_cli") + "\n")
            return 1
        from pathlib import Path
        chemin = Path(r[0]) if os.path.isabs(r[0]) else Path(os.getcwd()) / r[0]
        texte, code = sqlite_cli(str(chemin), " ".join(r[1:]), entete)
        if texte:
            out.write(texte + "\n")
        return code
    lignes = []

    def f(st):
        d_(st)
        arg = " ".join(reste) if reste else None
        if sous in ("plan", "labo", "laboratoire", "regles"):
            lignes.extend(banniere() + t("dn.meuble.laboratoire").split("\n"))
        elif sous == "combien":
            lignes.extend(lignes_combien(arg))
        elif sous in ("trier", "tri", "trie"):
            lignes.extend(lignes_trier())
        elif sous in ("colonnes", "colonne"):
            lignes.extend(lignes_colonnes())
        elif sous == "shiny":
            lignes.extend(lignes_shiny(arg))
        elif sous == "copiste":
            lignes.extend(lignes_copiste())
        elif sous in ("calcul", "calculatrice"):
            lignes.extend(lignes_calcul())
        elif sous == "moyenne":
            lignes.extend(lignes_moyenne(st, arg))
        elif sous == "mediane":
            lignes.extend(lignes_mediane(arg))
        elif sous == "etendue":
            lignes.extend(lignes_etendue(arg))
        elif sous in ("chaine", "chaines"):
            lignes.extend(lignes_chaine())
        elif sous == "bilan":
            lignes.extend(lignes_bilan(st))
        elif sous == "base":
            lignes.extend(lignes_base())
        elif sous == "sql":
            lignes.extend(lignes_sql(arg))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    if lignes:
        out.write("\n".join(lignes) + RESET + "\n")
    return 0


def brut_fr(cle):
    return brut(cle, "fr")
