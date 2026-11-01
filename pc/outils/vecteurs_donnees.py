"""Les vecteurs communs de la Salle des Données (Python ↔ Kotlin) : donnees/donnees/vecteurs.json.

    python3 pc/outils/vecteurs_donnees.py              écrit les vecteurs (depuis pc/tg/donnees.py, deploie.py et le VRAI awk)
    python3 pc/outils/vecteurs_donnees.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

L'export CSV de collections d'essai (vides, minuscules, normales, avec shiny, accents et variantes), la lecture du
tableau, chaque statistique (effectifs, podium, shiny, somme, moyenne, médianes, étendue, types en tête), l'écriture
des nombres d'awk et de sqlite3, le nom mal écrit (pour TOUTES les espèces du bestiaire) et le carnet du soigneur
dans les 14 langues, les instructions qui fabriquent collection.db, des requêtes et leurs résultats TYPÉS (calculés par
le vrai moteur SQLite de Python), le laboratoire de la vue déployée ; et les programmes du petit awk du téléphone avec la
sortie du VRAI awk de cette machine. tests/jvm/Donnees.kt vérifie que l'appli Android donne EXACTEMENT les mêmes
résultats ; pc/outils/test_donnees.py rejoue les programmes awk avec l'awk installé (mawk, gawk…).
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import bestiaire as B, deploie, langue, donnees as DN  # noqa: E402

FICHIER = RACINE / "donnees" / "donnees" / "vecteurs.json"
MIDI = 1793534400000          # 1er novembre 2026, 12 h UTC : le même jour partout entre UTC-11 et UTC+11


def individu(nom, vid="classique", shiny=False, stats=None, jours=0, rarete=None):
    e = B.espece(nom)
    st = stats or {k: v + 5 for k, v in e["stats"].items()}
    out = {"id": "abcdef0123", "espece": e["nom"], "variante": vid, "shiny": shiny, "date": MIDI + jours * 86400000,
           "marque": "étoile", "humeur": "joyeuse", "stats": st}
    if rarete:
        out["rarete"] = rarete
    return out


COLLECTIONS = {
    "vide": [],
    "une": [individu("Gloupi")],
    "deux_glace": [individu("Gloupi", "marais"), individu("Krillou", "glace", True, jours=-3)],
    "accents": [individu("Écumane"), individu("Séraphibou", "classique", False, jours=-40), individu("Nénuphage", "forêt"),
                individu("Gloupi"), individu("Chêneroc", rarete="épique")],
    "sept": [individu(n, jours=-k, shiny=(n == "Cailloute"), stats={"PV": 20 + k, "ATK": 26 + 3 * k % 13, "DEF": 30,
                                                                       "VIT": 12 + k, "INT": 24})
             for k, n in enumerate(("Gloupi", "Braisillon", "Gloupi", "Krillou", "Cailloute", "Plumange", "Tritonnet"))],
    "paire": [individu(n, stats={"PV": 1, "ATK": a, "DEF": 1, "VIT": 1, "INT": 1})
              for n, a in (("Gloupi", 20), ("Krillou", 31), ("Plumange", 25), ("Tritonnet", 31), ("Gloupi", 40), ("Cailloute", 22))],
}

AWK = [  # (options, programme) : les programmes des leçons et quelques autres du même petit langage
    (["-F,"], "NR<=5 {print $1, $4}"), (["-F,"], "NR>1 {s+=$4} END {print s}"), (["-F,"], "NR>1 {s+=$4; n++} END {print s/n}"),
    (["-F,"], "NR>1 {s+=$4; n++} END {print \"moyenne\", s/n}"), (["-F,"], "{print $2}"), (["-F,"], "$2==\"eau\" {print $1}"),
    (["-F,"], "NR>1 && $4>30 {print $1, $4}"), (["-F,"], "{print NR, $1}"), (["-F,"], "END {print NR}"),
    (["-F,"], "NR>1 {if ($4>m) m=$4} END {print m}"), (["-F,"], "NR>1 {print $4*2, $4/3}"), (["-F,"], "NR==2"),
    (["-F,"], "NR>1 {print $1 \"-\" $2}"), (["-F,"], "NR>1 {s+=$5} END {print s/NR}"), (["-F", ","], "{print NF}"),
    (["-F,"], "NR>1 {n++; if ($10==1) k++} END {print k+0, n, k*100/n}"), (["-F,"], "BEGIN {print \"debut\"} NR==1 {print $3}"),
    (["-F,"], "NR>1 && ($2==\"eau\" || $2==\"glace\") {print}"), (["-F,"], "NR>1 {print $4 % 7, -$4, !$10}"),
    (["-F,"], "NR>1 {s=s $1 \" \"} END {print s}"), (["-F,"], "NR>1 && $1 != \"Gloupi\" {c++} END {print c}"),
    (["-F,"], "NR>1 {t+=$4; u+=$5} END {print t, u, t-u, (t+u)/2}"), (["-F,"], "NR>1 {x=$4; x+=1; x*=2; x-=3; x/=4; print x}"),
    (["-F,"], "NR>1 {print ($4 >= 31) ? \"fort\" : \"doux\"}"), ([], "{s+=$1} END {print s}"), ([], "{print $2, $1}"),
    (["-F,"], "NR>2 {exit} {print $1}"), (["-F,"], "NR>1 {print $NF, $(NF-1)}"),
]


def awk_vrai(opts, prog, entree):
    r = subprocess.run(["awk", *opts, prog], input=entree, capture_output=True, text=True, env=dict(os.environ, LC_ALL="C"))
    return r.stdout


def valeur_typee(v):
    if v is None:
        return ["null", None]
    if isinstance(v, int):
        return ["int", v]
    if isinstance(v, float):
        return ["real", v]
    return ["text", v]


REQUETES = [
    "SELECT nom, attaque FROM creatures ORDER BY attaque DESC, nom LIMIT 3;",
    "SELECT nom, variante FROM creatures WHERE type = 'eau';",
    "SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;",
    "SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom ORDER BY c.nom LIMIT 5;",
    "SELECT AVG(attaque) FROM creatures;", "SELECT AVG(attaque), MIN(attaque), MAX(attaque), SUM(attaque) FROM creatures;",
    "SELECT COUNT(*) FROM creatures WHERE shiny = 1;", "SELECT nom, NULL, 1.0, 2.5, 1e20, 0.1 + 0.2, -3 FROM creatures LIMIT 1;",
    "SELECT 100.0 * SUM(shiny) / COUNT(*) FROM creatures;", "SELECT 1.0/3, 2.0/3, 10.0, 123456789012345.6;",
]


def vecteurs(awk_garde=None):
    """awk_garde : les sorties d'awk déjà enregistrées (--verifier : on ne relance pas l'awk de la CI, qui peut être un autre
    awk ; c'est test_donnees.py qui compare chaque sortie enregistrée à l'awk installé)."""
    langue.definir("fr")
    cols = {}
    for nom, caps in COLLECTIONS.items():
        rows, ajout = DN.lignes_collection(caps)
        texte = DN.csv_texte(rows)
        r = DN.lire_csv(texte)
        fautif, juste, f, bon = DN.carnet_soigneur(r)
        cols[nom] = {"captures": caps, "ajout": ajout, "csv": texte, "lignes": len(r),
                     "effectifs_noms": [list(x) for x in DN.effectifs([x["nom"] for x in r])],
                     "effectifs_types": [list(x) for x in DN.effectifs([x["type"] for x in r])],
                     "forces": DN.forces_txt(r), "especes": DN.especes_txt(r), "top3": DN.top3(r), "shiny": DN.nb_shiny(r),
                     "somme": DN.somme(r), "moyenne": DN.moyenne(r), "moyenne_awk": DN.nombre_awk(DN.moyenne(r)),
                     "medianes": DN.medianes(r), "etendue": DN.etendue(r), "types_majoritaires": DN.types_majoritaires(r),
                     "cible": DN.cible_faute(r), "faute": f, "carnet_faux": fautif, "carnet_juste": juste,
                     "base": [[sql, list(p)] for sql, p in DN.requetes_base(r)]}
    r7 = DN.lire_csv(cols["sept"]["csv"])
    carnets = {}
    for code in langue.LANGUES:
        langue.definir(code)
        a, b, f, bon = DN.carnet_soigneur(r7)
        carnets[code] = {"faux": a, "juste": b}
    langue.definir("fr")
    tous = {e["nom"] for e in B.donnees()["especes"]}
    fautes = {e["nom"]: DN.faute(e["nom"], tous) for e in B.donnees()["especes"]}
    lire = [{"texte": x, "lignes": DN.lire_csv(x)} for x in (
        "", "nom,type\n", cols["une"]["csv"], cols["une"]["csv"].replace(",24,", ",x,"),
        cols["deux_glace"]["csv"] + "Gloupi,eau\n\n", "Krillou,eau,abyssaux,36,37,36,27,20,commune,0,classique,2026-11-01,0\n")]
    nombres = [{"x": x, "awk": DN.nombre_awk(x), "sql": DN.valeur_sql(x)} for x in
               (0.0, 1.0, 33.0, 29.5, 1 / 3, 2 / 3, 100 / 7, 1234567.0, 12345678.9, 0.000123456, -2.5, 1e20, 123456789012345.6)]
    sqlv = [{"v": valeur_typee(v), "sql": DN.valeur_sql(v)} for v in (None, 0, -3, 24, 33.0, 23.454545454545453, 0.1 + 0.2, "eau", "")]
    tables = [{"noms": n, "texte": DN.tables_texte(n)} for n in (["creatures", "especes"], ["especes", "creatures"], ["c", "e"], [], ["a"])]
    # des requêtes sur la base de la collection « sept », avec leurs résultats typés (vrai moteur SQLite)
    tmp = Path(tempfile.mkdtemp()) / "collection.db"
    DN.creer_base(str(tmp), r7)
    cx = sqlite3.connect(str(tmp))
    requetes = []
    for q in REQUETES:
        cur = cx.execute(q)
        res = [[valeur_typee(v) for v in ligne] for ligne in cur.fetchall()]
        requetes.append({"sql": q, "colonnes": [d[0] for d in cur.description], "resultat": res,
                         "texte": "\n".join(DN.lignes_resultat([[v for _t, v in l] for l in res]))})
    schema = {n: s + ";" for n, s in cx.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")}
    cx.close()
    lignes = ["cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c", "sqlite3 collection.db .tables",
              "tg collection --csv > collection.csv", "collection --csv > collection.csv", "awk -F, '{print}' c",
              "grep -c 1 x", "grep -E 'eau|glace' collection.csv", "sed -n '2,4p' c", "paste -d: a b | head -5",
              "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt", "cut -d, -f1 c | xargs echo", "tr ',' '\\n'",
              "tg donnees sqlite3 collection.db .tables", "ls", "echo awk"]
    labo = [{"ligne": l, "labos": [list(a) for a in DN.labos_de(l)],
             "deploie": [{"seg": x["seg"], "cmd": x["cmd"], "outil": x["outil"], "instrument": x["instrument"], "de": x["de"],
                          "vers": x["vers"]} for x in deploie.labos(l)]} for l in lignes]
    entrees = {"sept": cols["sept"]["csv"], "paire": cols["paire"]["csv"], "forces": cols["sept"]["forces"]}
    awk = []
    for opts, prog in AWK:
        nom = "forces" if not opts else ("paire" if "Gloupi" in prog else "sept")
        sortie = (awk_garde or {}).get((tuple(opts), prog))
        awk.append({"options": opts, "programme": prog, "entree": nom,
                    "sortie": sortie if sortie is not None else awk_vrai(opts, prog, entrees[nom])})
    return {"note": "généré par pc/outils/vecteurs_donnees.py ; vérifié par tests/jvm/Donnees.kt (et l'awk installé par "
                    "pc/outils/test_donnees.py)", "collections": cols, "carnets": carnets, "fautes": fautes, "lire": lire,
            "nombres": nombres, "sql_valeurs": sqlv, "tables": tables, "requetes": requetes, "schema": schema,
            "labo": labo, "awk_entrees": entrees, "awk": awk}


def main():
    garde = None
    if "--verifier" in sys.argv and FICHIER.is_file():
        garde = {(tuple(x["options"]), x["programme"]): x["sortie"] for x in json.loads(FICHIER.read_text(encoding="utf-8"))["awk"]}
    texte = json.dumps(vecteurs(garde), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/donnees/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_donnees.py")
            sys.exit(1)
        print("vecteurs de la Salle des Données à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
