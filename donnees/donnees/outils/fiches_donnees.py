"""Les données de la Salle des Données (donnees/donnees.json), ses fiches notions (charte de rigueur,
docs/programme.md § 7.1) et sa place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc,
paliers D1 → D5 et D-SQL, ponts, attirance, exploit « une statistique juste sur sa propre collection », variantes
réservées des types Eau et Glace — des variantes qui EXISTENT déjà dans le bestiaire, ni gardiens ni déjà réservées),
les Ponts des Nombres des statistiques (moyenne, médiane, étendue, pourcentages ; effectifs et fréquences existent
déjà), les maths des étapes et les étapes rejouées dans bash.

    python3 donnees/donnees/outils/fiches_donnees.py   écrit donnees/donnees.json, donnees/programme.json
                                                       et leurs copies (pc/tg, app/src/main/assets)

LES DONNÉES DE L'ENFANT : sa propre collection, exportée par le jeu en CSV (`tg collection --csv`, sur Android
`collection --csv`) dans le terrain (terrain_terminagotchi/donnees). Aucune donnée personnelle : ni pseudo, ni
e-mail, ni adresse, ni identifiant ; seulement l'espèce, le type, la famille, les stats, la rareté, shiny, la
variante, le jour de la capture. Rien n'est envoyé. Une collection minuscule (moins de 5 bestioles) est complétée
par le JEU D'EXEMPLE ci-dessous (colonne « exemple » = 1, annoncé à l'écran) : rien ne bloque, et le rejeu en CI
(collection vide) est déterministe.
"""
import json
import shutil
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------- le jeu d'exemple (espèces du VRAI bestiaire)
# (espèce, variante, qualité des stats, shiny, jour) : stats = stats de l'espèce + round(31 × qualité) // 2
EXEMPLES = [("gloupi", "classique", 0.42, False, "2026-10-01"), ("braisillon", "volcan", 0.55, False, "2026-10-02"),
            ("plumange", "classique", 0.61, False, "2026-10-03"), ("gloupi", "marais", 0.30, False, "2026-10-04"),
            ("cailloute", "montagne", 0.38, False, "2026-10-05"), ("krillou", "glace", 0.50, False, "2026-10-06"),
            ("tritonnet", "lagon", 0.70, False, "2026-10-07"), ("mousselin", "classique", 0.33, False, "2026-10-08"),
            ("flamouche", "lave", 0.64, False, "2026-10-09"), ("pucerise", "prairie", 0.52, True, "2026-10-10")]
MIN_COLLECTION = 5           # en dessous, le jeu complète avec le jeu d'exemple
TAILLE_COMPLETEE = 10        # … jusqu'à 10 lignes

COLONNES = ["nom", "type", "famille", "attaque", "defense", "vitesse", "pv", "intelligence", "rarete", "shiny",
            "variante", "date", "exemple"]
STATS = {"attaque": "ATK", "defense": "DEF", "vitesse": "VIT", "pv": "PV", "intelligence": "INT"}
FAMILLES = {"Démons": "demons", "Élémentaires": "elementaires", "Constructs": "constructs", "Arthropodes": "arthropodes",
            "Abyssaux": "abyssaux", "Sylvestres": "sylvestres", "Célestes": "celestes", "Morts-vivants": "morts_vivants",
            "Aberrations": "aberrations"}
SCHEMA = {
    "creatures": "CREATE TABLE creatures (nom TEXT, type TEXT, famille TEXT, attaque INTEGER, defense INTEGER, "
                 "vitesse INTEGER, pv INTEGER, intelligence INTEGER, rarete TEXT, shiny INTEGER, variante TEXT, "
                 "date TEXT, exemple INTEGER)",
    "especes": "CREATE TABLE especes (nom TEXT PRIMARY KEY, numero INTEGER, habitat TEXT, puissance INTEGER)",
}
# le laboratoire de tri (vue déployée) : chaque outil a son instrument (§ 2.14)
LABO = [
    {"motif": r"^(tg\s+)?(donnees\s+)?sqlite3\b", "outil": "sqlite3", "instrument": "bibliotheque", "de": "base", "vers": "reponse"},
    {"motif": r"^(tg\s+)?collection\b.*--csv", "outil": "collection --csv", "instrument": "export", "de": "collection", "vers": "tableau"},
    {"motif": r"^sed\b", "outil": "sed", "instrument": "copiste", "de": "texte", "vers": "texte_corrige"},
    {"motif": r"^awk\b", "outil": "awk", "instrument": "calculatrice", "de": "colonnes", "vers": "calcul"},
    {"motif": r"^cut\b", "outil": "cut", "instrument": "ciseaux", "de": "tableau", "vers": "colonne"},
    {"motif": r"^tr\b", "outil": "tr", "instrument": "traducteur", "de": "lettres", "vers": "lettres_changees"},
    {"motif": r"^paste\b", "outil": "paste", "instrument": "colle", "de": "colonnes", "vers": "tableau"},
    {"motif": r"^sort\b", "outil": "sort", "instrument": "moulin", "de": "lignes", "vers": "lignes_rangees"},
    {"motif": r"^tee\b", "outil": "tee", "instrument": "aiguillage", "de": "lignes", "vers": "ecran_et_fichier"},
    {"motif": r"^xargs\b", "outil": "xargs", "instrument": "distributeur", "de": "lignes", "vers": "arguments"},
    {"motif": r"^grep\b(?!.*\s-\w*c)", "outil": "grep", "instrument": "tamis", "de": "lignes", "vers": "lignes_gardees"},
]
COULEURS = {"bibliotheque": 179, "export": 117, "copiste": 141, "calculatrice": 215, "ciseaux": 203, "traducteur": 78,
            "colle": 186, "moulin": 229, "aiguillage": 39, "distributeur": 75, "tamis": 110}


def exemples():
    sys.path.insert(0, str(D / "pc"))
    from tg import bestiaire as B
    out = []
    for eid, vid, q, shiny, jour in EXEMPLES:
        e = B.espece(eid)
        assert e and any(v["id"] == vid for v in e["variantes"]), (eid, vid)
        iv = round(31 * q) // 2
        out.append({"espece": e["nom"], "variante": vid, "shiny": shiny, "qualite": q, "jour": jour,
                    "stats": {k: v + iv for k, v in e["stats"].items()},
                    "rarete": B.rarete(e, vid, q, shiny)})
    return out


def donnees_salle():
    return {
        "note": "Généré par donnees/donnees/outils/fiches_donnees.py ; lu par pc/tg/donnees.py et Donnees.kt. La "
                "collection de l'enfant, exportée en CSV dans le terrain : aucune donnée personnelle, rien d'envoyé.",
        "colonnes": COLONNES, "stats": STATS, "familles": FAMILLES, "exemples": exemples(),
        "min_collection": MIN_COLLECTION, "taille_completee": TAILLE_COMPLETEE, "schema": SCHEMA,
        "labo": {"regles": LABO}, "couleurs": COULEURS,
        "chaine": {"rapport_lignes": 3},
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"dn.f.{nid}.enfant", "grands": f"dn.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"dn.f.{nid}.limite", "idees_fausses": [f"dn.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_COREUTILS = "GNU coreutils, manuel (wc, sort, uniq, cut, tr, paste, tee, head, tail) : https://www.gnu.org/software/coreutils/manual/"
S_POSIX = "POSIX.1-2024, Shell & Utilities (sort, uniq, cut, paste, sed, awk, xargs, tee, grep) : https://pubs.opengroup.org/onlinepubs/9799919799/"
S_RFC4180 = "RFC 4180, Common Format and MIME Type for CSV Files : https://www.rfc-editor.org/rfc/rfc4180"
S_STATS = "Programmes de mathématiques des cycles 3 et 4 (organisation et gestion de données : effectifs, moyenne, médiane, étendue) : https://eduscol.education.fr/"
CSV = "printf 'nom,type,attaque\\nGloupi,poison,24\\nBraisillon,feu,33\\nKrillou,glace,39\\nGloupi,poison,22\\n' > c.csv"
FICHES = dict([
    fiche("collection_csv", r"(^(tg\s+)?collection\b.*--csv|^(tg\s+)?donnees\s+(plan|labo|regles|combien|trier)\b|collection\.csv|forces\.txt|especes\.txt|top3\.txt|laboratoire\.txt)", [
        {"prepare": CSV, "cmd": "head -2 c.csv", "sortie": "nom,type,attaque\nGloupi,poison,24"},
        {"prepare": CSV, "cmd": "wc -l c.csv", "sortie": "5 c.csv"},
        {"prepare": "printf '24 Gloupi\\n33 Braisillon\\n39 Krillou\\n22 Gloupi\\n' > f.txt",
         "cmd": "sort -nr f.txt | head -3", "sortie": "39 Krillou\n33 Braisillon\n24 Gloupi"},
        {"prepare": "printf 'Gloupi\\nKrillou\\nGloupi\\n' > e.txt", "cmd": "sort e.txt | uniq -c | sort -rn | head -1",
         "sortie": "      2 Gloupi"},
        {"cmd": "tg collection --csv > collection.csv", "rejeu": "commande du jeu", "motif": "."}],
        [S_RFC4180, S_COREUTILS, S_POSIX, S_STATS]),
    fiche("colonnes", r"(^cut\b|^paste\b|^tr\b.*,|^(tg\s+)?donnees\s+(colonnes|shiny)\b|colonnes\.txt|noms\.txt|types\.txt)", [
        {"prepare": CSV, "cmd": "cut -d, -f2 c.csv", "sortie": "type\npoison\nfeu\nglace\npoison"},
        {"prepare": CSV, "cmd": "head -1 c.csv | tr ',' '\\n'", "sortie": "nom\ntype\nattaque"},
        {"prepare": CSV, "cmd": "cut -d, -f2 c.csv | tail -n +2 | sort | uniq -c",
         "sortie": "      1 feu\n      1 glace\n      2 poison"},
        {"prepare": "printf 'a\\nb\\n' > n.txt && printf '1\\n2\\n' > t.txt", "cmd": "paste -d: n.txt t.txt",
         "sortie": "a:1\nb:2"}],
        [S_RFC4180, S_COREUTILS, S_POSIX]),
    fiche("copiste", r"(^sed\b|^(tg\s+)?donnees\s+copiste\b|carnet_du_soigneur|carnet_corrige)", [
        {"cmd": "echo 'Glupoi et Glupoi' | sed 's/Glupoi/Gloupi/'", "sortie": "Gloupi et Glupoi"},
        {"cmd": "echo 'Glupoi et Glupoi' | sed 's/Glupoi/Gloupi/g'", "sortie": "Gloupi et Gloupi"},
        {"cmd": "printf 'a\\nb\\nc\\nd\\n' | sed -n '2,3p'", "sortie": "b\nc"},
        {"prepare": "echo 'Glupoi dort' > c.txt", "cmd": "sed -i 's/Glupoi/Gloupi/g' c.txt && cat c.txt",
         "sortie": "Gloupi dort"}],
        ["GNU sed, manuel : https://www.gnu.org/software/sed/manual/", S_POSIX]),
    fiche("calculatrice", r"(^awk\b|^(tg\s+)?donnees\s+(calcul|moyenne|mediane|etendue)\b|attaques\.txt)", [
        {"prepare": CSV, "cmd": "awk -F, 'NR>1 {s+=$3} END {print s}' c.csv", "sortie": "118"},
        {"prepare": CSV, "cmd": "awk -F, 'NR>1 {s+=$3; n++} END {print s/n}' c.csv", "sortie": "29.5"},
        {"prepare": CSV, "cmd": "awk -F, '{print $1, $3}' c.csv | head -2", "sortie": "nom attaque\nGloupi 24"},
        {"prepare": CSV, "cmd": "cut -d, -f3 c.csv | tail -n +2 | sort -n | sed -n '1p;$p'", "sortie": "22\n39"}],
        ["The AWK Programming Language (Aho, Kernighan, Weinberger) ; GNU awk, manuel : https://www.gnu.org/software/gawk/manual/",
         S_POSIX, S_STATS]),
    fiche("chaine", r"(^grep\b.*-\w*E|^xargs\b|\|\s*xargs\b|\btee\b|^(tg\s+)?donnees\s+(chaine|bilan)\b|rapport\.txt|enclos)", [
        {"prepare": CSV, "cmd": "grep -E 'feu|glace' c.csv", "sortie": "Braisillon,feu,33\nKrillou,glace,39"},
        {"prepare": CSV, "cmd": "cut -d, -f1 c.csv | tail -n +2 | sort -u | xargs echo", "sortie": "Braisillon Gloupi Krillou"},
        {"prepare": CSV, "cmd": "mkdir -p enclos && cut -d, -f1 c.csv | tail -n +2 | sort -u | sed 's|.*|enclos/&.txt|' | xargs touch && ls enclos",
         "sortie": "Braisillon.txt\nGloupi.txt\nKrillou.txt"},
        {"prepare": CSV, "cmd": "sort -t, -k3 -nr c.csv | head -1 | tee r.txt && cat r.txt",
         "sortie": "Krillou,glace,39\nKrillou,glace,39"}],
        [S_POSIX, S_COREUTILS, "GNU findutils, xargs : https://www.gnu.org/software/findutils/manual/html_node/find_html/Invoking-xargs.html",
         "GNU grep, expressions régulières étendues : https://www.gnu.org/software/grep/manual/"]),
    fiche("sql", r"(sqlite3\b|^(tg\s+)?donnees\s+(base|sql)\b|collection\.db)", [
        {"prepare": "sqlite3 b.db \"CREATE TABLE c (nom TEXT, type TEXT, attaque INTEGER); INSERT INTO c VALUES "
                    "('Gloupi','poison',24),('Braisillon','feu',33),('Krillou','glace',39),('Gloupi','poison',22);\"",
         "cmd": "sqlite3 b.db \"SELECT type, COUNT(*) FROM c GROUP BY type ORDER BY COUNT(*) DESC, type;\"",
         "sortie": "poison|2\nfeu|1\nglace|1", "outil": "sqlite3"},
        {"prepare": "sqlite3 b.db \"CREATE TABLE c (nom TEXT, attaque INTEGER); INSERT INTO c VALUES ('A',24),('B',33),('C',39),('D',22);\"",
         "cmd": "sqlite3 b.db \"SELECT nom FROM c WHERE attaque > 30 ORDER BY attaque DESC;\"", "sortie": "C\nB", "outil": "sqlite3"},
        {"prepare": "sqlite3 b.db \"CREATE TABLE c (nom TEXT, attaque INTEGER); INSERT INTO c VALUES ('A',24),('B',33),('C',39),('D',22);\"",
         "cmd": "sqlite3 b.db \"SELECT AVG(attaque) FROM c;\"", "sortie": "29.5", "outil": "sqlite3"},
        {"prepare": "sqlite3 b.db \"CREATE TABLE c (nom TEXT); CREATE TABLE e (nom TEXT, habitat TEXT); INSERT INTO c VALUES ('A'),('B'); "
                    "INSERT INTO e VALUES ('A','lagon'),('B','volcan');\"",
         "cmd": "sqlite3 b.db \"SELECT c.nom, e.habitat FROM c JOIN e ON c.nom = e.nom ORDER BY c.nom;\"",
         "sortie": "A|lagon\nB|volcan", "outil": "sqlite3"},
        {"prepare": "sqlite3 b.db \"CREATE TABLE c (nom TEXT); CREATE TABLE e (nom TEXT);\"", "cmd": "sqlite3 b.db .tables",
         "sortie": "c  e", "outil": "sqlite3"}],
        ["SQLite, documentation (SELECT, GROUP BY, JOIN, l'outil sqlite3) : https://www.sqlite.org/lang_select.html ; https://www.sqlite.org/cli.html",
         "ISO/IEC 9075 (le langage SQL)", S_STATS]),
])

DONNEES = {"id": "donnees", "types": ["eau", "glace"], "requis": ["n4"], "chapitre": "donnees",
           "paliers": [f"dn{i}" for i in range(7)],
           "attirance": {"cmds": ["sort", "uniq", "wc", "awk", "sed", "cut", "sqlite3"], "activites": ["collection"],
                         "familles": ["Abyssaux"], "epreuves": ["Données", "IA", "Rétro"]},
           "ponts": {"sort_uniq": ["citadelle", "observatoire"], "frequences": ["crypte", "observatoire"],
                     "grep": ["observatoire"], "sha256sum": ["crypte"]},
           "reutilise": {"epreuves": ["Rétro:top3", "Rétro:record", "Données:differentes", "IA:frequent"], "quetes": ["q21"]},
           "exploits": [{"id": "donnees.statistique", "nom": "recomp.donnees.statistique", "recompense": "variante"}],
           "maths": ["effectifs", "frequences", "pourcentages", "moyenne", "mediane", "etendue"],
           "variantes_reservees": ["nautiloque:corail", "krillou:aurore", "ondulame:glace"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources, titre_existant=False):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


S_BASH = "Bash, Shell Arithmetic : https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html"
MATHS = dict([
    maths_fiche("moyenne", ["addition", "division"], "primaire", [
        {"cmd": "echo $(( (12 + 15 + 18) / 3 ))", "sortie": "15"},
        {"cmd": "printf '12\\n15\\n18\\n' | awk '{s+=$1} END {print s/NR}'", "sortie": "15"}], [S_STATS, S_BASH]),
    maths_fiche("mediane", ["comptage"], "college", [
        {"cmd": "printf '18\\n12\\n30\\n15\\n21\\n' | sort -n | sed -n '3p'", "sortie": "18"},
        {"cmd": "printf '18\\n12\\n30\\n15\\n21\\n' | sort -n | tr '\\n' ' '", "sortie": "12 15 18 21 30 "}], [S_STATS, S_COREUTILS]),
    maths_fiche("etendue", ["soustraction"], "college", [
        {"cmd": "printf '18\\n12\\n30\\n' | sort -n | sed -n '1p;$p'", "sortie": "12\n30"},
        {"cmd": "echo $((30 - 12))", "sortie": "18"}], [S_STATS, S_BASH]),
    maths_fiche("pourcentages", ["multiplication", "division"], "college", [
        {"cmd": "echo $((3 * 100 / 12))", "sortie": "25"}, {"cmd": "echo $((1 * 100 / 4))", "sortie": "25"}],
        [S_STATS, S_BASH]),
])

ETAPES = {"dn1.2": {"maths": ["comptage"]}, "dn1.5": {"maths": ["effectifs"]}, "dn2.2": {"maths": ["effectifs"]},
          "dn2.4": {"maths": ["pourcentages"]}, "dn4.3": {"maths": ["moyenne"]}, "dn4.6": {"maths": ["mediane"]},
          "dn4.8": {"maths": ["etendue"]}, "dn6.5": {"maths": ["frequences"]}}


def rejeu():
    """Ce que le jeu affirme des vraies sorties : la collection change d'une partie à l'autre, alors le rejeu compare la
    sortie de bash à ce que LE JEU calcule sur le même fichier (egal_jeu)."""
    return {
        "dn0.1": {"contient": ["laboratoire.txt", "carnet_des_donnees.txt"], "pourquoi": "hist.dn0.1.bravo : le laboratoire"},
        "dn1.1": {"motif": r"\Anom,type,famille,attaque,defense,vitesse,pv,intelligence,rarete,shiny,variante,date,exemple\n",
                  "pourquoi": "hist.dn1.1.bravo : la première ligne nomme les colonnes"},
        "dn1.2": {"egal_jeu": "lignes", "pourquoi": "hist.dn1.2.bravo : une ligne par bestiole, plus la ligne des titres"},
        "dn1.5": {"egal_jeu": "espece_frequente", "pourquoi": "hist.dn1.5.bravo : l'espèce que tu as le plus"},
        "dn1.6": {"egal_jeu": "top3", "pourquoi": "hist.dn1.6.bravo : tes 3 bestioles les plus fortes"},
        "dn2.1": {"motif": r"\Anom\ntype\nfamille\nattaque\n", "pourquoi": "hist.dn2.1.bravo : une colonne par ligne"},
        "dn2.2": {"egal_jeu": "types", "pourquoi": "hist.dn2.2.bravo : combien de chaque type"},
        "dn2.3": {"egal_jeu": "shiny", "pourquoi": "hist.dn2.3.bravo : le nombre de shiny"},
        "dn3.2": {"egal_jeu": "une_faute_reste", "pourquoi": "hist.dn3.2.bravo : sans g, une faute reste sur la ligne double"},
        "dn3.4": {"motif": r"^[<>] ", "pourquoi": "hist.dn3.4.bravo : diff montre les lignes corrigées"},
        "dn4.2": {"egal_jeu": "somme", "pourquoi": "hist.dn4.2.bravo : la somme des attaques"},
        "dn4.3": {"egal_jeu": "moyenne_awk", "pourquoi": "hist.dn4.3.bravo : la moyenne d'attaque"},
        "dn4.7": {"egal_jeu": "min_max", "pourquoi": "hist.dn4.7.bravo : la plus petite et la plus grande attaque"},
        "dn5.2": {"egal_jeu": "especes_xargs", "pourquoi": "hist.dn5.2.bravo : xargs met les lignes à la suite"},
        "dn5.4": {"egal_jeu": "rapport_top", "pourquoi": "hist.dn5.4.bravo : tee montre ET écrit"},
        "dn6.1": {"sortie": "creatures  especes  ", "outil": "sqlite3", "pourquoi": "hist.dn6.1.bravo : deux tables"},
        "dn6.2": {"egal_jeu": "schema", "outil": "sqlite3", "pourquoi": "hist.dn6.2.bravo : les colonnes de la table"},
        "dn6.3": {"egal_jeu": "sql_top3", "outil": "sqlite3", "pourquoi": "hist.dn6.3.bravo : ORDER BY … DESC LIMIT 3"},
        "dn6.5": {"egal_jeu": "sql_group", "outil": "sqlite3", "pourquoi": "hist.dn6.5.bravo : GROUP BY compte par type"},
        "dn6.7": {"egal_jeu": "sql_join", "outil": "sqlite3", "pourquoi": "hist.dn6.7.bravo : JOIN relie deux tables"},
        "dn6.8": {"egal_jeu": "sql_moyenne", "outil": "sqlite3", "pourquoi": "hist.dn6.8.bravo : la même moyenne qu'awk"},
    }


def main():
    G = donnees_salle()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/donnees.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/donnees.json", "app/src/main/assets/donnees.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    P["mondes"] = [DONNEES if m["id"] == "donnees" else m for m in P["mondes"]]
    for cle in ("etapes", "rejeu"):                   # les étapes de la Salle des Données : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("dn") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Salle des Données, {len(MATHS)} ponts des nombres, {len(R)} étapes rejouées ; "
          "donnees.json écrit")


if __name__ == "__main__":
    main()
