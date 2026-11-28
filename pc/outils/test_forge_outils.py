"""Les commandes de la Forge comme sur le TÉLÉPHONE (le shell mksh d'Android et les outils toybox), et avec busybox,
comparées au shell et aux outils GNU du PC — docs/programme.md § 2.10 (Android : sh ✅, for/if/while ✅, read par un tuyau).

    python3 pc/outils/test_forge_outils.py [--exiger toybox,busybox,mksh]

Sur le téléphone, l'appli lance chaque ligne dans /system/bin/sh (mksh) avec les outils toybox ; `forge`, `curl` et la
lanterne du site sont intégrés à l'appli (Forge.kt, Port.kt : testés ailleurs). Ici, chaque ligne des paliers F1 → F6
(telle que le téléphone la montre : la boîte remplie et ouverte sur la même ligne, read par un tuyau, le robot de la
devinette) est lancée dans un terrain neuf :
  - avec sh et les outils GNU (la référence, ceux du rejeu) ;
  - avec toybox (et mksh comme shell, quand il est installé : c'est le shell d'Android), puis avec busybox ;
et les sorties ET les fichiers produits doivent être identiques (seul l'alignement peut différer : `wc` met plus ou moins
d'espaces). Le nombre secret de la devinette vient de l'heure : une fausse horloge (`date +%s` fixe) le rend le même.
Une seule différence est attendue et acceptée : le code d'erreur de `ls fantome` (GNU : 2, toybox : 1) ; le jeu ne
demande que « pas 0 » (forge code). Sans toybox, le test le dit et passe (--exiger le rend obligatoire : la CI).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import forge as FO, langue  # noqa: E402

OUTILS = ["ls", "cat", "mkdir", "touch", "seq", "wc", "find", "echo", "head", "sort", "date"]
HEURE = "1793534407"                                   # la fausse horloge (date +%s) : le secret vaut 8


def lignes():
    return [
        "echo '#!/bin/sh' > cabane.sh", "echo 'mkdir -p cabane' >> cabane.sh",
        "echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh", "cat cabane.sh", "sh cabane.sh; ls cabane",
        "nom=Pixel; echo \"Bonjour $nom\"", "echo 'echo \"Bonjour $1 !\"' > salut.sh", "sh salut.sh Léa",
        "echo 'echo \"Tu as donné $# prénoms.\"' >> salut.sh", "sh salut.sh Léa Tom Sam",
        "echo 'read prenom' > question.sh && echo 'echo \"Salut $prenom !\"' >> question.sh", "echo Léa | sh question.sh",
        "ls fantome; echo $?",
        "if [ -f cabane/porte.txt ]; then echo \"La porte est là !\"; fi", "for i in 1 2 3; do echo \"Tour $i\"; done",
        "for i in $(seq 1 10); do mkdir -p village/cabane_$i; done", "ls village | wc -l",
        "n=3; while [ $n -gt 0 ]; do echo $n; n=$((n - 1)); done", "seq 4 9 | wc -l",
        "seq 1 10 | sh mon_jeu/devinette.sh", "printf '3\\n9\\n8\\n' | sh mon_jeu/devinette.sh",
        "echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_$s; done' > donjon.sh", "sh donjon.sh; ls mon_jeu/donjon",
        "echo \"Le trésor est ici !\" > mon_jeu/donjon/salle_3/tresor.txt", "find mon_jeu | sort",
        "echo '<h1>Bienvenue chez Pixel</h1>' > site/index.html",
        "echo '<p>Ici vit ma créature. Elle adore les cabanes.</p>' >> site/index.html",
        "echo 'h1 { color: orange; }' > site/style.css", "echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html",
        "cat site/index.html", "ls multimedia",
    ]


def preparer(d):
    (d / "mon_jeu").mkdir()
    (d / "mon_jeu" / "devinette.sh").write_text(FO.devinette_sh(), encoding="utf-8")
    (d / "site").mkdir()
    (d / "multimedia").mkdir()
    (d / "multimedia" / "photo_exemple.jpg").write_bytes(FO.photo_octets())


def fichiers(d):
    out = {}
    for p in sorted(d.rglob("*")):
        r = str(p.relative_to(d))
        out[r] = (p.read_bytes().decode("utf-8", "replace") if p.is_file() else "/")
    return out


def jouer(liens_dir, shell="sh"):
    d = Path(tempfile.mkdtemp(prefix="tg_forge_outils_"))
    preparer(d)
    env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8")
    env["PATH"] = f"{liens_dir}:{env.get('PATH', '/usr/bin:/bin')}"
    res, avant = [], fichiers(d)
    for l in lignes():
        r = subprocess.run([shell, "-c", l], cwd=str(d), capture_output=True, text=True, env=env, timeout=60)
        f = fichiers(d)
        delta = {k: v for k, v in f.items() if avant.get(k) != v}
        delta.update({k: None for k in avant if k not in f})
        avant = f
        res.append((l, r.stdout, r.returncode, delta, r.stderr))
    shutil.rmtree(d, ignore_errors=True)
    return res


def fausse_horloge(d):
    """date +%s → toujours la même heure (les autres formes de date passent au vrai date)."""
    vrai = shutil.which("date") or "/bin/date"
    (d / "date").write_text(f"#!/bin/sh\n[ \"$1\" = \"+%s\" ] && {{ echo {HEURE}; exit 0; }}\nexec {vrai} \"$@\"\n")
    (d / "date").chmod(0o755)


def liens(boite, shell=None):
    exe = shutil.which(boite)
    d = Path(tempfile.mkdtemp(prefix=f"tg_{boite}_"))
    ok = []
    for o in OUTILS:
        if o == "date":
            continue
        r = subprocess.run([exe, o, "--help"], capture_output=True, text=True)
        texte = (r.stdout + r.stderr).lower()
        if "applet not found" in texte or "unknown command" in texte or "not found" in texte.split("\n")[0]:
            continue
        (d / o).symlink_to(exe)
        ok.append(o)
    if shell:
        (d / "sh").symlink_to(shutil.which(shell))     # sh cabane.sh : le shell du téléphone (mksh)
    fausse_horloge(d)
    return d, ok


def espaces(texte):
    return "\n".join(" ".join(l.split()) for l in texte.split("\n"))


def code_ls(s):
    """« ls fantome; echo $? » : le message d'erreur change d'un outil à l'autre, le jeu ne lit que « pas 0 »."""
    der = (s.strip().split("\n") or [""])[-1]
    return "pas 0" if der.isdigit() and der != "0" else der


def main():
    langue.definir("fr")
    exiger = sys.argv[sys.argv.index("--exiger") + 1].split(",") if "--exiger" in sys.argv else []
    ref_dir = Path(tempfile.mkdtemp(prefix="tg_gnu_"))
    fausse_horloge(ref_dir)
    ref = jouer(ref_dir)
    ko = 0
    if not any("Bravo" in s for l, s, *_ in ref if "devinette" in l):
        print("  ✖ la devinette ne se termine pas avec les outils GNU")
        ko += 1
    mksh = shutil.which("mksh")
    if not mksh:
        print("  · mksh (le shell d'Android) n'est pas installé : toybox est essayé avec sh" + (" ✖ (exigé)" if "mksh" in exiger else ""))
        ko += "mksh" in exiger
    for boite in ("toybox", "busybox"):
        strict = boite == "toybox"
        if not shutil.which(boite):
            print(f"  · {boite} n'est pas installé : pas comparé" + (" ✖ (exigé)" if boite in exiger else ""))
            ko += boite in exiger
            continue
        shell = "mksh" if boite == "toybox" and mksh else None
        d, ok = liens(boite, shell)
        print(f"{boite}{' + mksh' if shell else ''} : {len(ok)} outils ({' '.join(ok)})")
        res = jouer(d, shell or "sh")
        for (l, s0, c0, f0, _e0), (_l, s1, c1, f1, e1) in zip(ref, res):
            if (s0, c0, f0) == (s1, c1, f1):
                print(f"  ✔ {l}")
            elif (espaces(s0), c0, f0) == (espaces(s1), c1, f1):
                print(f"  ≈ {l}   (mêmes valeurs, espaces différents)")
            elif l.startswith("ls fantome") and (code_ls(s0), c0, f0) == (code_ls(s1), c1, f1):
                print(f"  ≈ {l}   (un autre code d'erreur que 0 : le jeu demande seulement « pas 0 »)")
            else:
                ko += strict
                print(f"  {'✖' if strict else '·'} {l}" + ("" if strict else "   (pour information : busybox n'est pas le téléphone)"))
                print(f"      GNU    : {s0[:160]!r} code {c0} {sorted(f0)[:4]}")
                print(f"      {boite:<7}: {s1[:160]!r} code {c1} {sorted(f1)[:4]} {e1[:160]!r}")
    print(f"\n{'✔' if not ko else '✖'} {ko} écart(s) sur le téléphone")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
