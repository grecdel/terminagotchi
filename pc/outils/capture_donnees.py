"""Captures de la Salle des Données (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_donnees.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette, 8 bestioles), la Salle des Données est
ouverte (tronc commun fini). Les commandes du jeu (tg collection --csv, donnees …) passent par le vrai code ; les autres
(sort, head, awk, tee, sqlite3…) sont lancées pour de vrai, mais SEULEMENT dans le terrain temporaire. Sorties :
  dn_pc_lecon.png      l'écran du jeu (tg) pendant la première leçon de la Salle
  dn_pc_repli.png      l'affichage de REPLI tant que l'illustration de la Salle manque (donnees)
  dn_pc_tri.png        le laboratoire de tri : le CSV, donnees trier, les espèces les plus nombreuses
  dn_pc_top3.png       les 3 créatures les plus fortes (sort -nr | head -3 > top3.txt)
  dn_pc_moyenne.png    la moyenne avec awk, puis donnees moyenne (le jeu recalcule sur le même fichier)
  dn_pc_rapport.png    le rapport avec tee, la moyenne ajoutée avec >>, le bilan
  dn_pc_sql.png        la base SQLite : .tables, une requête GROUP BY, donnees sql
  dn_pc_deploie.png    tg deploie "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt" (vue déployée)
  dn_pc_deploie.gif    la même vue déployée, animée
"""
import io
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_don_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, bestiaire as B, core, deploie, histoire, langue, donnees as DN  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402

NOMS = ["Gloupi", "Braisillon", "Gloupi", "Krillou", "Cailloute", "Plumange", "Tritonnet", "Krillou"]


def preparer():
    import builtins
    import random
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, _lecs = DN._besoin()
    random.seed(7)
    coll = [B.individu(B.espece(n), i == 3, "x") for i, n in enumerate(NOMS)]

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "donnees"
        h["ouverts"].append("donnees")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                    "observatoire", "donnees"])
        h["faits"] += ["dn0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["captures"] = coll
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "donnees").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in DN.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")


def session(cmds, ici="donnees"):
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c.split(">")[0]) if c.split()[0] in ("tg", "donnees") else [c.split()[0]]
        if mots[:2] == ["tg", "donnees"]:
            mots = mots[1:]
        vieux = os.getcwd()
        os.chdir(d)
        try:
            if mots[:3] == ["tg", "collection", "--csv"]:
                buf, err = io.StringIO(), io.StringIO()
                DN.commande_collection_csv(buf, err)
                (d / c.split(">")[1].strip()).write_text(buf.getvalue(), encoding="utf-8")
                out += err.getvalue().rstrip("\n").split("\n")
                continue
            if mots[0] == "donnees":
                buf = io.StringIO()
                DN.commande(mots[1:], buf)
                out += buf.getvalue().rstrip("\n").split("\n")
                continue
        finally:
            os.chdir(vieux)
        r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=120)
        txt = (r.stdout + r.stderr).rstrip("\n")
        if txt:
            out += txt.split("\n")
    out.append(invite)
    return out


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    app.etape(spontane=False, defis=False)
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "dn_pc_lecon.png")

    ansi_image(session(["donnees"]), 100, None, 15).convert("RGB").save(sortie / "dn_pc_repli.png")

    session(["tg collection --csv > collection.csv"])
    rows = DN.lire_csv((core.TERRAIN / "donnees/collection.csv").read_text(encoding="utf-8"))
    lignes = session(["tg collection --csv > collection.csv", "head -4 collection.csv", "wc -l collection.csv",
                      f"donnees combien {len(rows)}", "donnees trier", "sort especes.txt | uniq -c | sort -rn | head -3"])
    ansi_image(lignes, 120, None, 12).convert("RGB").save(sortie / "dn_pc_tri.png")

    lignes = session(["head -4 forces.txt", "sort -nr forces.txt | head -3 > top3.txt", "cat top3.txt"])
    ansi_image(lignes, 100, None, 15).convert("RGB").save(sortie / "dn_pc_top3.png")

    m = DN.nombre_awk(DN.moyenne(rows))
    lignes = session(["awk -F, 'NR<=5 {print $1, $4}' collection.csv", "awk -F, 'NR>1 {s+=$4} END {print s}' collection.csv",
                      "awk -F, 'NR>1 {s+=$4; n++} END {print s/n}' collection.csv", f"donnees moyenne {m}"])
    ansi_image(lignes, 124, None, 13).convert("RGB").save(sortie / "dn_pc_moyenne.png")

    lignes = session(["sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt",
                      "awk -F, 'NR>1 {s+=$4; n++} END {print \"moyenne\", s/n}' collection.csv >> rapport.txt",
                      "cat rapport.txt", "donnees bilan"])
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "dn_pc_rapport.png")

    sq = "sqlite3" if shutil.which("sqlite3") else "tg donnees sqlite3"
    session(["donnees base"])
    lignes = session([f"{sq} collection.db .tables",
                      f'{sq} collection.db "SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;"',
                      "donnees sql " + DN.types_majoritaires(rows)[0]])
    ansi_image(lignes, 158, None, 12).convert("RGB").save(sortie / "dn_pc_sql.png")

    ligne = "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "donnees")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.7, 100, d), 100, None, 15).convert("RGB").save(sortie / "dn_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "dn_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print(f"captures de la Salle des Données (PC) écrites dans {sortie}")


if __name__ == "__main__":
    main()
