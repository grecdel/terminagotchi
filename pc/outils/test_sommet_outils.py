"""Les commandes du Sommet avec les outils du TÉLÉPHONE (toybox), et ceux de busybox, comparées aux outils GNU du PC —
docs/programme.md § 2.18 (sur Android : sed -i '2i …', sed -E et ses captures, grep -E/-o/-c, find -print0, xargs -0,
mktemp ./modele.XXXXXX, wc, sort, head, tee, dirname dans les scripts du jeu).

    python3 pc/outils/test_sommet_outils.py [--exiger toybox,busybox]

Comme test_donnees_outils.py : chaque ligne de la traversée du téléphone est lancée dans un terrain neuf préparé par le
jeu (scripts, journal, éboulis, CTF), avec les outils GNU (la référence), puis toybox et busybox (un dossier de liens
passe devant le PATH). Les sorties, les codes et les fichiers produits doivent être identiques (à l'alignement près). Le
shell est bash des deux côtés (sur le téléphone : mksh, testé à part par test_sommet.py avec busybox sh) : ici on
compare les OUTILS. Les noms des brouillons de mktemp (au hasard) sont remplacés par « brouillon.* ». Seul toybox fait
échouer le test ; busybox est affiché pour information. Sans toybox, le test le dit et passe (sauf --exiger, en CI).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import langue, sommet as S  # noqa: E402

G = "1:1234"
OUTILS = ["sed", "grep", "sort", "head", "wc", "find", "xargs", "mktemp", "cp", "rm", "cat", "tee", "dirname", "ls"]


def lignes():
    cap, pas = S.mission(G)
    return ["sed -i '2i set -euo pipefail' fragile.sh && head -3 fragile.sh",
            'bash fragile.sh "carnet de bord.txt"; echo $?',
            "sed -i 's/cp $carnet/cp \"$carnet\"/' fragile.sh",
            'bash fragile.sh "carnet de bord.txt"; ls coffre',
            "bash sale.sh; ls brouillon.* | wc -l",
            "bash bivouac.sh -n 3; ls brouillon.* | wc -l; cat sac.txt",
            "rm brouillon.*; ls",
            "head -5 journal.log",
            "grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l",
            "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l",
            "grep -cE 'ALERTE|ERREUR' journal.log",
            "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt",
            "sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt",
            "find eboulis -type f | sort",
            "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6",
            'echo "pierres : $(find eboulis -type f | wc -l)"',
            "sed -i '6s/$/; then/' casse.sh && bash -n casse.sh && bash casse.sh",
            "sed -i 's/totl=/total=/' boucle.sh && bash boucle.sh",
            f"bash boussole.sh -c {cap} -p {pas}; cat arrivee.txt",
            "grep -oE 'fragment1=[a-z]+' ctf/registre.log",
            "find ctf -name '*.frag' -print0 | xargs -0 cat",
            f"bash ctf/porte.sh -k {S.fragments(G)[0]}; cat ctf/porte_ouverte.txt"]


def preparer(d):
    (d / "coffre").mkdir()
    (d / "carnet de bord.txt").write_text(langue.t("som.carnet_de_bord") + "\n", encoding="utf-8")
    for n in ("fragile", "sale", "bivouac", "casse", "boucle"):
        (d / f"{n}.sh").write_text(S.script(n), encoding="utf-8")
    (d / "journal.log").write_text(S.journal_texte(G), encoding="utf-8")
    for rel, (nom, taille) in S.eboulis(G).items():
        p = d / "eboulis" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(S.contenu_pierre(nom, taille), encoding="utf-8")
    (d / "boussole.sh").write_text(S.script_boussole(G), encoding="utf-8")
    for rel, txt in S.fichiers_ctf(G).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")


BROUILLON = re.compile(r"brouillon\.[A-Za-z0-9]{6}")


def jouer(liens_dir):
    d = Path(tempfile.mkdtemp(prefix="tg_som_outils_"))
    preparer(d)
    env = dict(os.environ, LC_ALL="C.UTF-8", LANG="C.UTF-8")
    if liens_dir:
        env["PATH"] = f"{liens_dir}:{env.get('PATH', '/usr/bin:/bin')}"
    res, avant = [], {}
    for l in lignes():
        r = subprocess.run(["bash", "-c", l], cwd=str(d), capture_output=True, text=True, env=env, timeout=60)
        fichiers = {BROUILLON.sub("brouillon.*", str(p.relative_to(d))): (p.read_text(encoding="utf-8") if p.is_file() else "/")
                    for p in sorted(d.rglob("*"))}
        delta = {k: v for k, v in fichiers.items() if avant.get(k) != v}
        delta.update({k: None for k in avant if k not in fichiers})
        avant = fichiers
        res.append((l, BROUILLON.sub("brouillon.*", r.stdout), r.returncode, delta, r.stderr))
    shutil.rmtree(d, ignore_errors=True)
    return res


def espaces(texte):
    return "\n".join(" ".join(l.split()) for l in texte.split("\n"))


def liens(boite):
    exe = shutil.which(boite)
    d = Path(tempfile.mkdtemp(prefix=f"tg_{boite}_"))
    ok = []
    for o in OUTILS:
        r = subprocess.run([exe, o, "--help"], capture_output=True, text=True)
        texte = (r.stdout + r.stderr).lower()
        if "applet not found" in texte or "unknown command" in texte or "not found" in texte.split("\n")[0]:
            continue
        (d / o).symlink_to(exe)
        ok.append(o)
    return d, ok


def main():
    langue.definir("fr")
    exiger = sys.argv[sys.argv.index("--exiger") + 1].split(",") if "--exiger" in sys.argv else []
    ref = jouer(None)
    ko = vus = 0
    for boite in ("toybox", "busybox"):
        strict = boite == "toybox"
        if not shutil.which(boite):
            print(f"  · {boite} n'est pas installé : pas comparé" + (" ✖ (exigé)" if boite in exiger else ""))
            ko += boite in exiger
            continue
        vus += 1
        d, ok = liens(boite)
        manque = [o for o in OUTILS if o not in ok]
        print(f"{boite} : {len(ok)} outils" + (f", absents : {' '.join(manque)}" if manque else ""))
        if strict and manque:
            ko += 1
            print(f"  ✖ outils absents de {boite} (le téléphone en a besoin) : {manque}")
        for (l, s0, c0, f0, _e0), (_l, s1, c1, f1, e1) in zip(ref, jouer(d)):
            if (s0, c0, f0) == (s1, c1, f1):
                print(f"  ✔ {l}")
            elif (espaces(s0), c0, f0) == (espaces(s1), c1, f1):
                print(f"  ≈ {l}   (mêmes valeurs, espaces différents)")
            else:
                ko += strict
                print(f"  {'✖' if strict else '·'} {l}")
                if s0 != s1:
                    print(f"      GNU    : {s0!r}\n      {boite:7}: {s1!r}")
                if c0 != c1:
                    print(f"      code de sortie {c0} ≠ {c1}  {e1.strip()[:120]}")
                if f0 != f1:
                    print(f"      fichiers différents : {sorted(k for k in set(f0) | set(f1) if f0.get(k) != f1.get(k))}")
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n{len(ref)} lignes du Sommet ; {vus} boîte(s) à outils comparée(s) ; {ko} différence(s)")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
