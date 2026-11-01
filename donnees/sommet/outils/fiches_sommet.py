"""Les données du Sommet (donnees/sommet.json), ses fiches notions (charte de rigueur, docs/programme.md § 7.1) et sa
place dans donnees/programme.json : le monde (ouverture : 3 mondes au palier 3, calculée sur la liste des mondes du jeu,
y compris ceux qui arriveront), les paliers som0 → som7, les ponts, l'attirance, l'exploit « trois mondes maîtrisés »
(des LÉGENDAIRES EXISTANTES, aucune déjà réservée par un autre monde), les maths des étapes et les étapes rejouées
dans bash.

    python3 donnees/sommet/outils/fiches_sommet.py   écrit donnees/sommet.json, donnees/programme.json
                                                     et leurs copies (pc/tg, app/src/main/assets)

LES SCRIPTS DU SOMMET sont fournis par le jeu, dans le terrain (terrain_terminagotchi/sommet) : fragile.sh (une sauvegarde
qui ment), sale.sh et bivouac.sh (le brouillon oublié, puis trap + mktemp + getopts), casse.sh (une erreur de syntaxe),
boucle.sh (une faute de frappe dans une variable), boussole.sh (un outil jamais vu, à apprendre avec --help) et la porte
du CTF. Aucun ne lit ni n'écrit hors du dossier où on le lance ; aucun ne demande sudo ; aucun n'utilise le réseau. Leurs
gabarits sont ici (« scripts ») : @@clé@@ = un texte du jeu entre apostrophes (shell), ##clé## = un texte brut (commentaire),
{sh} = l'interpréteur (bash sur PC, sh sur le téléphone). Le PC et le téléphone fabriquent le MÊME texte (vecteurs).
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]

ENTETE = "#!/usr/bin/env bash"
SCRIPTS = {
    # S1 : la sauvegarde qui ment (pas de set -e, une variable sans guillemets)
    "fragile": [ENTETE, "# ##som.sc.fragile.role##", "carnet=$1", "cp $carnet coffre/",
                'echo @@som.sc.fragile.ok@@ "$carnet"'],
    # S2 : le brouillon oublié
    "sale": [ENTETE, "# ##som.sc.sale.role##", "brouillon=$(mktemp ./brouillon.XXXXXX)",
             'echo @@som.sc.ration@@ 1 >> "$brouillon"', "echo @@som.sc.sale.panne@@ >&2", "exit 1"],
    # S2 : le bivouac propre (set -euo pipefail, getopts, mktemp, trap)
    "bivouac": [ENTETE, "# ##som.sc.bivouac.role##", "set -euo pipefail", "n=2",
                "usage() { echo @@som.sc.bivouac.usage@@ >&2; }",
                'while getopts "n:h" opt; do', "  case $opt in", "    n) n=$OPTARG ;;", "    h) usage; exit 0 ;;",
                "    *) usage; exit 2 ;;", "  esac", "done",
                "brouillon=$(mktemp ./brouillon.XXXXXX)", "trap 'rm -f \"$brouillon\"' EXIT", "i=1",
                'while [ "$i" -le "$n" ]; do', '  echo @@som.sc.ration@@ "$i" >> "$brouillon"', "  i=$((i + 1))", "done",
                'cp "$brouillon" sac.txt', 'echo @@som.sc.bivouac.ok@@ "$n"'],
    # S5 : l'erreur de syntaxe (le « then » oublié à la ligne 6 ; bash la signale à la ligne 8, au « fi »)
    "casse": [ENTETE, "# ##som.sc.casse.role##", "marches=0", "for etage in 1 2 3 4; do",
              "  marches=$((marches + etage * 10))", '  if [ "$marches" -gt 50 ]', '    echo @@som.sc.casse.plus@@ "$etage"',
              "  fi", "done", 'echo @@som.sc.total@@ "$marches"'],
    # S5 : la faute de frappe (totl au lieu de total) : le script tourne, mais faux
    "boucle": [ENTETE, "# ##som.sc.boucle.role##", "total=0", "for alt in 1200 1850 2400; do",
               "  totl=$((total + alt))", "done", 'echo @@som.sc.boucle.cumul@@ "$total"'],
}
CASSE_LIGNE = 6            # la ligne fautive (« if » sans « then ») ; bash -n la signale à la ligne 8 (le « fi »)
CASSE_SIGNALE = [6, 7, 8]  # réponses acceptées à « sommet ligne » (le vrai endroit, et ce que bash ou mksh affichent)
BOUCLE_JUSTE = 1200 + 1850 + 2400

LIEUX = ["lac-gele", "col-du-vent", "grotte-bleue", "pic-noir", "source-chaude", "pont-de-glace", "vieux-refuge",
         "crete-rouge", "cascade", "foret-de-pins", "moraine", "glacier-blanc", "belvedere", "chapelle", "combe-verte",
         "roc-perce"]
CAPS = ["nord", "sud", "est", "ouest"]
PIERRES = ["quartz", "granit", "ardoise", "silex bleu", "pierre ronde", "gneiss", "basalte", "mica", "cristal geant",
           "galet plat", "schiste", "obsidienne"]
MOTS = ["edelweiss", "marmotte", "chamois", "bouquetin", "gentiane", "lagopede", "crampon", "piolet", "cordee",
        "bivouac", "serac", "moraine", "congere", "cairn", "refuge", "rappel", "baudrier", "mousqueton", "glacier",
        "altitude", "corniche", "brocard", "myrtille", "chocard"]
JOURNAL = {"debut": "2026-07-01", "jours": 12, "lignes": 28,
           "messages": {"INFO": ["som.log.info.depart", "som.log.info.pause", "som.log.info.meteo", "som.log.info.cairn"],
                        "ALERTE": ["som.log.alerte.vent", "som.log.alerte.orage"],
                        "ERREUR": ["som.log.erreur.corde", "som.log.erreur.carte"]},
           "suite": ["som.log.suite.releve", "som.log.suite.fausse"]}
DEFI = {"n": 3, "base": 2_000_000, "medailles": ["or", "diamant"]}
# la vue déployée : la cordée (chaque outil a son geste) ; grep, sed et xargs restent au laboratoire des Données
CORDEE = [
    {"motif": r"^(bash|sh)\s+-n\b", "outil": "bash -n", "geste": "relire", "de": "script", "vers": "syntaxe"},
    {"motif": r"^(bash|sh)\s+-x\b", "outil": "bash -x", "geste": "eclairer", "de": "script", "vers": "trace"},
    {"motif": r"^shellcheck\b", "outil": "shellcheck", "geste": "relire", "de": "script", "vers": "conseils"},
    {"motif": r"^find\b.*-print0\b", "outil": "find -print0", "geste": "chercher", "de": "arbre", "vers": "noms_zero"},
    {"motif": r"^(bash|sh)\s+\S+\.sh\b", "outil": "bash", "geste": "grimper", "de": "script", "vers": "resultat"},
]
COULEURS = {"relire": 141, "eclairer": 229, "chercher": 78, "grimper": 203}
# les légendaires que le Sommet attire : des espèces LÉGENDAIRES EXISTANTES (bestiaire.json), aucune réservée ailleurs
# (le Port réserve empyria:nuage, la Crypte lichonarque:crypte ; Abyssor reste la mythique secrète)
LEGENDAIRES = ["infernarque", "tellurion", "rugissire", "sylvarque", "essaimpereur", "noctilune", "forgerain", "chaosmere"]


def donnees_sommet():
    return {
        "note": "Généré par donnees/sommet/outils/fiches_sommet.py ; lu par pc/tg/sommet.py et Sommet.kt. Les scripts du "
                "Sommet sont fournis par le jeu dans le terrain ; aucun ne sort du dossier où on le lance.",
        "ouverture": {"mondes": 3, "palier": 3}, "scripts": SCRIPTS, "casse": {"ligne": CASSE_LIGNE, "signale": CASSE_SIGNALE},
        "boucle": {"juste": BOUCLE_JUSTE, "faute": "totl"}, "lieux": LIEUX, "caps": CAPS, "pierres": PIERRES, "mots": MOTS,
        "journal": JOURNAL, "defi": DEFI, "cordee": {"regles": CORDEE}, "couleurs": COULEURS,
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"som.f.{nid}.enfant", "grands": f"som.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"som.f.{nid}.limite", "idees_fausses": [f"som.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_BASH = "GNU Bash, manuel de référence (set, trap, getopts, $( ), <( ), -n, -x) : https://www.gnu.org/software/bash/manual/"
S_POSIX = "POSIX.1-2024, Shell Command Language (set -e -u, trap, getopts) : https://pubs.opengroup.org/onlinepubs/9799919799/"
S_COREUTILS = "GNU coreutils (mktemp, wc) et findutils (find -print0, xargs -0) : https://www.gnu.org/software/coreutils/manual/ ; https://www.gnu.org/software/findutils/manual/"
S_GREP = "GNU grep et GNU sed, expressions régulières étendues : https://www.gnu.org/software/grep/manual/ ; https://www.gnu.org/software/sed/manual/"
S_REGEX = "POSIX.1-2024, Regular Expressions (ERE) : https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap09.html"
S_SHELLCHECK = "ShellCheck (les avertissements SC2086…) : https://www.shellcheck.net/wiki/"
S_MAN = "man-pages et man-db (sections, man -f, apropos) : https://man7.org/linux/man-pages/man7/man-pages.7.html"
S_STRACE = "strace(1) : https://man7.org/linux/man-pages/man1/strace.1.html"
SCRIPT_S = "cat > s.sh <<'FIN'\nf=$1\ncp $f coffre/\necho fini\nFIN\nmkdir coffre && touch 'a b'"
SCRIPT_E = "cat > s.sh <<'FIN'\nset -euo pipefail\nf=$1\ncp $f coffre/\necho fini\nFIN\nmkdir coffre && touch 'a b'"
SCRIPT_Q = "cat > s.sh <<'FIN'\nset -euo pipefail\nf=$1\ncp \"$f\" coffre/\necho fini\nFIN\nmkdir coffre && touch 'a b'"
TRAP = "cat > t.sh <<'FIN'\nf=$(mktemp ./b.XXXXXX)\ntrap 'rm -f \"$f\"' EXIT\necho x > \"$f\"\nFIN"
SANS_TRAP = "cat > t.sh <<'FIN'\nf=$(mktemp ./b.XXXXXX)\necho x > \"$f\"\nFIN"
GETOPTS = "cat > o.sh <<'FIN'\nn=1\nwhile getopts \"n:\" opt; do\n  case $opt in n) n=$OPTARG ;; *) exit 2 ;; esac\ndone\necho \"n=$n\"\nFIN"
JOURNAL_X = ("printf '%s\\n' '2026-07-01 [INFO] depart' '  releve du 2026-07-02' '2026-07-02 [ALERTE] vent' "
             "'  note : fausse ALERTE' '2026-07-03 [ERREUR] corde' > j.log")
EBOULIS = "mkdir -p e/n && printf 'aaaa' > 'e/n/pierre ronde.txt' && printf 'bb' > e/n/quartz.txt && printf 'cccccc' > e/gros.txt"
CASSE_X = "printf 'if true\\n  echo oui\\nfi\\n' > c.sh"
FICHES = dict([
    fiche("script_robuste", r"(fragile\.sh|set -euo pipefail|^echo\s+\$\?|^(tg\s+)?sommet\s+(fragile|refuge|plan)\b|refuge\.txt|coffre)", [
        {"prepare": SCRIPT_S, "cmd": "bash s.sh 'a b' 2>/dev/null; echo $?", "sortie": "fini\n0"},
        {"prepare": SCRIPT_E, "cmd": "bash s.sh 'a b' 2>/dev/null; echo $?", "sortie": "1"},
        {"prepare": SCRIPT_Q, "cmd": "bash s.sh 'a b' && ls coffre", "sortie": "fini\na b"},
        {"cmd": "bash -c 'set -u; echo \"$x\"' 2>&1", "motif": "x: unbound variable", "code": "non0"},
        {"cmd": "bash -c 'set -o pipefail; false | true'; echo $?", "sortie": "1"}],
        [S_BASH, S_POSIX, S_SHELLCHECK]),
    fiche("bivouac_propre", r"(bivouac\.sh|sale\.sh|brouillon|sac\.txt|\btrap\b|\bmktemp\b|\bgetopts\b|^(tg\s+)?sommet\s+(bivouac|restes)\b)", [
        {"prepare": TRAP, "cmd": "bash t.sh; ls b.* 2>/dev/null | wc -l", "sortie": "0"},
        {"prepare": SANS_TRAP, "cmd": "bash t.sh; ls b.* 2>/dev/null | wc -l", "sortie": "1"},
        {"prepare": GETOPTS, "cmd": "bash o.sh -n 3", "sortie": "n=3"},
        {"prepare": GETOPTS, "cmd": "bash o.sh -z 2>&1", "motif": "illegal option -- z", "code": "non0"},
        {"cmd": "mktemp ./b.XXXXXX | grep -cE '^\\./b\\.[A-Za-z0-9]{6}$'", "sortie": "1"}],
        [S_BASH, S_POSIX, S_COREUTILS]),
    fiche("regex_avancees", r"(journal\.log|alertes\.txt|^grep\b.*\s-\w*[EoP]|^egrep\b|^sed\s+(-\w+\s+)*-E|^(tg\s+)?sommet\s+(journal|dates|alertes)\b)", [
        {"prepare": JOURNAL_X, "cmd": "grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' j.log", "sortie": "3"},
        {"prepare": JOURNAL_X, "cmd": "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' j.log | sort -u | wc -l", "sortie": "3"},
        {"prepare": JOURNAL_X, "cmd": "grep -cE 'ALERTE|ERREUR' j.log", "sortie": "3"},
        {"prepare": JOURNAL_X, "cmd": "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' j.log",
         "sortie": "2026-07-02 [ALERTE] vent\n2026-07-03 [ERREUR] corde"},
        {"cmd": "echo '2026-07-03 corde' | sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/'",
         "sortie": "03/07/2026 corde"}],
        [S_GREP, S_REGEX]),
    fiche("one_liners", r"(eboulis|-print0|xargs\s+(-\w+\s+)*-0|\$\(|<\(|\bFNR\b|FILENAME|^(tg\s+)?sommet\s+(eboulis|lourd)\b)", [
        {"prepare": EBOULIS, "cmd": "find e -type f -print0 | xargs -0 wc -c | sort -nr | head -2",
         "sortie": "12 total\n 6 e/gros.txt"},
        {"prepare": EBOULIS, "cmd": "find e -type f | xargs wc -c 2>&1 | grep -c 'No such file'", "sortie": "2"},
        {"prepare": EBOULIS, "cmd": "echo \"pierres : $(find e -type f | wc -l)\"", "sortie": "pierres : 3"},
        {"cmd": "diff <(printf 'a\\nb\\n') <(printf 'a\\nc\\n')", "sortie": "2c2\n< b\n---\n> c", "code": 1},
        {"prepare": "printf 'un\\ndeux\\n' > a.txt && printf 'trois\\n' > b.txt",
         "cmd": "awk 'FNR==1 {print FILENAME, $1}' a.txt b.txt", "sortie": "a.txt un\nb.txt trois"}],
        [S_BASH, S_COREUTILS, "The AWK Programming Language (FNR, FILENAME) ; GNU awk : https://www.gnu.org/software/gawk/manual/"]),
    fiche("debogage", r"(casse\.sh|boucle\.sh|^(bash|sh)\s+-[nx]\b|shellcheck|strace|^(tg\s+)?sommet\s+(casse|ligne|bug|strace)\b)", [
        {"prepare": CASSE_X, "cmd": "bash -n c.sh", "motif": "c.sh: line 3: syntax error near unexpected token `fi'",
         "code": "non0"},
        {"prepare": "printf 'x=1\\necho $x\\n' > d.sh", "cmd": "bash -x d.sh 2>&1", "sortie": "+ x=1\n+ echo 1\n1"},
        {"prepare": "printf '#!/bin/bash\\nf=$1\\ncp $f /dev/null\\n' > s.sh", "cmd": "shellcheck s.sh",
         "motif": "SC2086", "code": "non0", "outil": "shellcheck"},
        {"cmd": "strace -f -e trace=execve true", "rejeu": "notion (strace peut être interdit dans un conteneur)", "motif": "."}],
        [S_BASH, S_SHELLCHECK, S_STRACE]),
    fiche("documentation", r"(^man\b|^apropos\b|^whatis\b|--help|boussole|arrivee|^(tg\s+)?sommet\s+(boussole|arrivee|sections)\b)", [
        {"cmd": "bash -c 'help getopts' | head -1", "sortie": "getopts: getopts optstring name [arg ...]"},
        {"cmd": "grep --help | grep -cE '^ +-o, --only-matching'", "sortie": "1"},
        {"cmd": "sed --help | grep -cE '^ +-E, -r, --regexp-extended'", "sortie": "1"},
        {"cmd": "man -f passwd", "rejeu": "les pages de manuel installées changent d'une machine à l'autre", "motif": "."}],
        [S_MAN, S_BASH, S_GREP]),
    fiche("defis_sommet", r"(^(tg\s+)?sommet\s+(ctf|drapeau|defi|records)\b|\bctf/|porte\.sh|registre\.log|\.frag\b|^(tg\s+)?badges\s+(grades|records)\b)", [
        {"prepare": "printf 'fragment1 = faux\\nfragment1=FAUX\\nok fragment1=cairn fin\\n' > r.log",
         "cmd": "grep -oE 'fragment1=[a-z]+' r.log", "sortie": "fragment1=cairn"},
        {"prepare": "mkdir -p 'c/une pierre' && echo fragment2=serac > 'c/une pierre/x.frag' && echo leurre > c/y.txt",
         "cmd": "find c -name '*.frag' -print0 | xargs -0 cat", "sortie": "fragment2=serac"},
        {"cmd": "sommet ctf", "rejeu": "commande du jeu", "motif": "."}],
        [S_BASH, S_GREP, S_COREUTILS,
         "Les épreuves « capture the flag » (CTF) : un drapeau à trouver en combinant plusieurs savoir-faire"]),
])

SOMMET = {"id": "sommet", "types": [], "requis": [], "ouverture": {"mondes": 3, "palier": 3}, "chapitre": "sommet",
          "paliers": [f"som{i}" for i in range(8)],
          "attirance": {"cmds": ["shellcheck", "strace", "xargs", "getopts", "trap", "mktemp", "apropos", "man"],
                        "activites": ["ctf", "entrainement"], "familles": []},
          "ponts": {"set_e": ["forge", "controle"], "regex": ["donnees", "citadelle"], "xargs": ["donnees"],
                    "bash_x": ["forge"], "man": ["controle"]},
          "reutilise": {"entrainement": ["records", "grades:peta", "grades:exa", "graine_du_jour"]},
          "exploits": [{"id": "sommet.trois_mondes", "nom": "recomp.sommet.trois_mondes", "recompense": "legendaire",
                        "bonus": 3, "essais": 16}],
          "legendaires": LEGENDAIRES,
          "maths": ["comptage", "logique", "puissances_10"], "variantes_reservees": []}

ETAPES = {"som1.5": {"maths": ["logique"]}, "som3.3": {"maths": ["comptage"]}, "som7.7": {"maths": ["puissances_10"]}}


def rejeu():
    """Ce que le jeu affirme des vraies sorties (bash) ; ce qui dépend de la partie (journal, éboulis, boussole, CTF) est
    comparé à ce que LE JEU calcule (egal_jeu)."""
    return {
        "som0.1": {"contient": ["refuge.txt", "carnet_du_sommet.txt"], "pourquoi": "hist.som0.1.bravo : le refuge"},
        "som1.2": {"motif": r"No such file", "pourquoi": "hist.som1.2.bravo : cp cherche 3 fichiers"},
        "som1.3": {"sortie": "0", "pourquoi": "hist.som1.3.bravo : le script ment, il répond 0"},
        "som1.5": {"motif": r"\n1\Z", "pourquoi": "hist.som1.5.bravo : il s'arrête et répond 1"},
        "som1.7": {"motif": r"unbound variable", "pourquoi": "hist.som1.7.bravo : -u refuse une variable vide"},
        "som2.2": {"lignes": 1, "pourquoi": "hist.som2.2.bravo : un brouillon oublié"},
        "som2.5": {"sortie": "1", "pourquoi": "hist.som2.5.bravo : trap a rangé son brouillon"},
        "som2.6": {"motif": r"illegal option -- x", "pourquoi": "hist.som2.6.bravo : getopts refuse -x"},
        "som3.2": {"egal_jeu": "lignes_datees", "pourquoi": "hist.som3.2.bravo : les lignes qui COMMENCENT par une date"},
        "som3.3": {"egal_jeu": "dates", "pourquoi": "hist.som3.3.bravo : les dates différentes"},
        "som3.5": {"egal_jeu": "alertes_partout", "pourquoi": "hist.som3.5.bravo : ALERTE ou ERREUR n'importe où"},
        "som3.8": {"egal_jeu": "dates_fr", "pourquoi": "hist.som3.8.bravo : les captures \\3/\\2/\\1"},
        "som4.2": {"motif": r"No such file", "pourquoi": "hist.som4.2.bravo : les espaces coupent les noms"},
        "som4.3": {"egal_jeu": "plus_lourds", "pourquoi": "hist.som4.3.bravo : le total puis les 5 plus lourds"},
        "som4.5": {"egal_jeu": "nb_pierres", "pourquoi": "hist.som4.5.bravo : $( ) met la sortie dans la phrase"},
        "som4.6": {"egal_jeu": "diff_nord_sud", "pourquoi": "hist.som4.6.bravo : < seulement au nord, > seulement au sud"},
        "som4.7": {"egal_jeu": "premieres_lignes", "pourquoi": "hist.som4.7.bravo : FNR repart à 1 dans chaque fichier"},
        "som5.1": {"motif": r"line 8: syntax error near unexpected token `fi'", "pourquoi": "hist.som5.1.bravo : ligne 8"},
        "som5.4": {"motif": r"100\Z", "pourquoi": "hist.som5.4.bravo : 100 marches"},
        "som5.5": {"motif": r" 0\Z", "pourquoi": "hist.som5.5.bravo : 0, un résultat faux"},
        "som5.6": {"motif": r"^\+ totl=1200$", "pourquoi": "hist.som5.6.bravo : la trace montre totl"},
        "som5.8": {"motif": str(BOUCLE_JUSTE) + r"\Z", "pourquoi": "hist.som5.8.bravo : le bon total"},
        "som6.3": {"egal_jeu": "aide_boussole", "pourquoi": "hist.som6.3.bravo : l'aide de l'outil"},
        "som6.4": {"egal_jeu": "arrivee", "pourquoi": "hist.som6.4.bravo : l'outil répond"},
        "som6.6": {"motif": r"-o, --only-matching", "pourquoi": "hist.som6.6.bravo : l'option -o de grep"},
        "som7.1": {"egal_jeu": "fragment1", "pourquoi": "hist.som7.1.bravo : seul le vrai fragment correspond"},
        "som7.2": {"egal_jeu": "fragment2", "pourquoi": "hist.som7.2.bravo : -print0 et -0 gardent l'espace"},
        "som7.4": {"egal_jeu": "fragment3", "pourquoi": "hist.som7.4.bravo : la porte s'ouvre avec le fragment 1"},
    }


def main():
    G = donnees_sommet()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/sommet.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/sommet.json", "app/src/main/assets/sommet.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["mondes"] = [SOMMET if m["id"] == "sommet" else m for m in P["mondes"]]
    if not any(m["id"] == "sommet" for m in P["mondes"]):
        P["mondes"].append(SOMMET)
    for cle in ("etapes", "rejeu"):                   # les étapes du Sommet : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("som") and k.split(".")[0][3:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches du Sommet, {len(R)} étapes rejouées ; sommet.json écrit")


if __name__ == "__main__":
    main()
