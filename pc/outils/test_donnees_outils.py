"""Les commandes de la Salle des Données avec les outils du TÉLÉPHONE (toybox), et ceux de busybox, comparées aux outils
GNU du PC — docs/programme.md § 2.14 (Android : sed, sort, uniq, cut, tr, paste, grep, xargs, tee, head, tail, wc).

    python3 pc/outils/test_donnees_outils.py [--exiger toybox,busybox]

Sur le téléphone, l'appli lance ces commandes dans le shell du téléphone (/system/bin/sh et les outils toybox) ; seuls
`awk` et `sqlite3` sont intégrés à l'appli (DonneesAwk.kt, DonneesSql.kt, testés ailleurs : vecteurs communs). Ici,
chaque ligne de la Salle (sans awk ni sqlite3) est lancée sur le MÊME tableau de test (donnees.json, collection_test) :
  - avec les outils GNU (la référence, ceux du rejeu) ;
  - avec toybox, puis busybox, quand ils sont installés : un dossier de liens (sed → toybox…) passe devant le PATH ;
et les sorties ET les fichiers produits doivent être identiques (seul l'alignement peut différer : `uniq -c` et `wc`
mettent plus ou moins d'espaces devant les nombres, le jeu ne lit que les valeurs). Sans toybox ni busybox, le test le dit et passe
(--exiger les rend obligatoires : c'est ce que fait la CI, qui compile toybox depuis ses sources, avec tr comme sur
Android ; diff n'est pas comparé pour toybox : l'appli a le sien). Seul toybox fait échouer le test ; les écarts de busybox sont affichés pour information.
Ce que ce test a trouvé (1er novembre) : toybox n'a ni `cat -n` (le jeu dit `nl`) ni `xargs -I` (le jeu fabrique les
noms avec sed : `sed 's|.*|enclos/&.txt|' | xargs touch`) ; busybox `diff` écrit le format unifié.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "donnees" / "donnees" / "outils"))

from tg import donnees as DN, langue  # noqa: E402
import fiches_donnees as F  # noqa: E402

OUTILS = ["sed", "sort", "uniq", "cut", "tr", "paste", "grep", "xargs", "tee", "head", "tail", "wc", "cat", "diff", "nl",
          "mkdir", "touch", "ls", "echo"]

# Les lignes de la Salle (dn1 → dn5) qui passent par le shell du téléphone, « ? » remplacés comme le ferait l'enfant.
def lignes(mal, bien):
    return [
        "head -3 collection.csv", "wc -l collection.csv", "wc -l < collection.csv",
        "sort especes.txt | uniq -c | sort -rn | head -3", "sort -nr forces.txt | head -3 > top3.txt; cat top3.txt",
        "head -1 collection.csv | tr ',' '\\n'", "cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c",
        "cut -d, -f10 collection.csv | grep -c 1",
        "cut -d, -f1 collection.csv > noms.txt && cut -d, -f2 collection.csv > types.txt; cat noms.txt types.txt",
        "paste -d: noms.txt types.txt | head -5",
        f"sed 's/{mal}/{bien}/' carnet_du_soigneur.txt",
        f"sed 's/{mal}/{bien}/g' carnet_du_soigneur.txt > carnet_corrige.txt; cat carnet_corrige.txt",
        "diff carnet_du_soigneur.txt carnet_corrige.txt",
        "sed -n '2,4p' carnet_corrige.txt",
        f"sed -i 's/{mal}/{bien}/g' carnet_du_soigneur.txt; cat carnet_du_soigneur.txt",
        "cut -d, -f4 collection.csv | tail -n +2 | sort -n > attaques.txt; cat attaques.txt",
        "sed -n '1p;$p' attaques.txt", "head -1 attaques.txt; tail -1 attaques.txt", "nl attaques.txt",
        "grep -E 'eau|glace' collection.csv", "grep -cE ',(eau|glace),' collection.csv",
        "cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs echo",
        "mkdir -p enclos && cut -d, -f1 collection.csv | tail -n +2 | sort -u | sed 's|.*|enclos/&.txt|' | xargs touch; ls enclos",
        "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt",
        "echo 'moyenne 33.1' >> rapport.txt; cat rapport.txt",
        # les variantes de Hugo (sim_donnees.py)
        "head -n 3 collection.csv", "sort -rn forces.txt | head -n 3", "cut -f2 -d, collection.csv | tail -n +2 | sort | uniq -c | sort -rn",
        "cut -d, -f10 collection.csv | grep -cx 1", "sort -t, -k4 -rn collection.csv | head -n 3",
    ]


def preparer(d):
    rows = DN.lignes_collection(DN.collection_test())       # la collection de test (10 captures fixes)
    (d / "collection.csv").write_text(DN.csv_texte(rows), encoding="utf-8")
    lus = DN.lire_csv(DN.csv_texte(rows))
    (d / "especes.txt").write_text(DN.especes_txt(lus), encoding="utf-8")
    (d / "forces.txt").write_text(DN.forces_txt(lus), encoding="utf-8")
    fautif, _juste, mal, bien = DN.carnet_soigneur(lus)
    (d / "carnet_du_soigneur.txt").write_text(fautif, encoding="utf-8")
    return mal, bien


def jouer(boite, liens_dir):
    """Toutes les lignes dans un terrain neuf, avec la boîte à outils donnée (None = GNU) : [(ligne, sortie, code, fichiers)]."""
    d = Path(tempfile.mkdtemp(prefix="tg_outils_"))
    mal, bien = preparer(d)
    env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8")
    if boite:
        env["PATH"] = f"{liens_dir}:{env.get('PATH', '/usr/bin:/bin')}"
    res = []
    avant = {}
    for l in lignes(mal, bien):
        r = subprocess.run(["sh", "-c", l], cwd=str(d), capture_output=True, text=True, env=env, timeout=60)
        fichiers = {str(p.relative_to(d)): (p.read_text(encoding="utf-8") if p.is_file() else "/")
                    for p in sorted(d.rglob("*"))}
        delta = {k: v for k, v in fichiers.items() if avant.get(k) != v}   # seulement ce que CETTE ligne a changé
        delta.update({k: None for k in avant if k not in fichiers})
        avant = fichiers
        res.append((l, r.stdout, r.returncode, delta, r.stderr))
    shutil.rmtree(d, ignore_errors=True)
    return res


def espaces(texte):
    """Le texte sans l'alignement : chaque ligne sans espaces au bord, les suites d'espaces et de tabulations en un seul."""
    return "\n".join(" ".join(l.split()) for l in texte.split("\n"))


# Sur le téléphone, diff est INTÉGRÉ à l'appli (Citadelle.diff, format « normal » comme GNU) : pas celui de toybox.
INTEGRES = {"toybox": {"diff"}}


def liens(boite):
    exe = shutil.which(boite)
    d = Path(tempfile.mkdtemp(prefix=f"tg_{boite}_"))
    ok = []
    for o in OUTILS:
        if o in INTEGRES.get(boite, ()):
            continue
        r = subprocess.run([exe, o, "--help"], capture_output=True, text=True)
        texte = (r.stdout + r.stderr).lower()
        if "applet not found" in texte or "unknown command" in texte or "not found" in texte.split("\n")[0]:
            continue                                       # l'outil manque dans cette boîte : le shell prendra celui du PC
        (d / o).symlink_to(exe)
        ok.append(o)
    return d, ok


def main():
    langue.definir("fr")
    exiger = []
    if "--exiger" in sys.argv:
        exiger = sys.argv[sys.argv.index("--exiger") + 1].split(",")
    ref = jouer(None, None)
    ko = 0
    vus = 0
    for boite in ("toybox", "busybox"):
        strict = boite == "toybox"                     # toybox : le téléphone ; busybox : pour information (PC Alpine…)
        if not shutil.which(boite):
            print(f"  · {boite} n'est pas installé : pas comparé" + (" ✖ (exigé)" if boite in exiger else ""))
            ko += boite in exiger
            continue
        vus += 1
        d, ok = liens(boite)
        manque = [o for o in OUTILS if o not in ok and o not in INTEGRES.get(boite, ())]
        version = subprocess.run([shutil.which(boite), "--version"], capture_output=True, text=True).stdout.strip()[:40]
        print(f"{boite} ({version or '?'}) : {len(ok)} outils" + (f", absents : {' '.join(manque)}" if manque else ""))
        res = jouer(boite, d)
        for (l, s0, c0, f0, _e0), (_l, s1, c1, f1, e1) in zip(ref, res):
            if (s0, c0, f0) == (s1, c1, f1):
                print(f"  ✔ {l}")
                continue
            if (espaces(s0), c0, f0) == (espaces(s1), c1, f1):  # seulement l'alignement (uniq -c, wc…) : le jeu lit les valeurs
                print(f"  ≈ {l}   (mêmes valeurs, espaces différents)")
                continue
            ko += strict
            print(f"  {'✖' if strict else '·'} {l}" + ("" if strict else "   (pour information : busybox n'est pas le téléphone)"))
            if s0 != s1:
                print(f"      GNU    : {s0!r}\n      {boite:7}: {s1!r}")
            if c0 != c1:
                print(f"      code de sortie {c0} ≠ {c1}  {e1.strip()[:120]}")
            if f0 != f1:
                print(f"      fichiers différents : {sorted(k for k in set(f0) | set(f1) if f0.get(k) != f1.get(k))}")
        shutil.rmtree(d, ignore_errors=True)
    n = len(ref)
    print(f"\n{n} lignes de la Salle ; {vus} boîte(s) à outils comparée(s) ; {ko} différence(s)")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
