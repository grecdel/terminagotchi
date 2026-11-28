"""L'Observatoire de l'IA (phase 5, docs/programme.md § 2.17 et § 7.4), sur PC.

    python3 pc/outils/test_observatoire.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/observatoire/vecteurs.json, mêmes résultats en Kotlin) ;
     les jeux de données relus dans le VRAI bestiaire ; le devineur de type (10/10, le piège de la 21e créature, le
     biais du volcan : 1 sur 5 puis 5 sur 5) ; le devineur de mots (comptes égaux à tr | sort | uniq -c dans un vrai
     bash, paires égales à paste, phrases déterministes) ; l'assistant (consigne floue, claire, tri qui oublie une
     ligne) ; les 2 réponses fausses sur 5 ;
  2. l'arbre du Carrefour : fermé tant que les niveaux 4 et 6 ne sont pas faits, puis ouvert et annoncé une fois ;
     meublé (coupole, carnet, missions) ;
  3. la traversée ob0 → ob9 comme un enfant (vraies commandes dans bash, hors ligne ; agent boucle arrêté par un VRAI
     SIGINT, comme Ctrl+C) : exploit « toutes les réponses fausses », variantes réservées, la loupe et le titre ;
  4. les indices (sudo, rm -rf ~, « ? » recopié, consigne floue, redirection oubliée…) et la garde ;
  5. la vue déployée : la lunette de diff, wc, uniq -c, sh tests.sh, assistant, devine-type ;
  6. sécurité : rien hors du terrain ; aucune proposition dangereuse n'est JAMAIS exécutée (même acceptée) ; le jeu
     n'ouvre aucune connexion, n'appelle aucune vraie IA ; la clé est un EXEMPLE ; 14 langues.
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_obs_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ.pop("CLE_API", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
Path(os.environ["HOME"], ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n")

from tg import app, core, deploie, histoire, langue, observatoire as O, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
JEU = {"observatoire": "observatoire.commande", "assistant": "observatoire.commande_assistant",
       "agent": "observatoire.commande_agent", "devine-type": "observatoire.commande_devine_type",
       "devine-mot": "observatoire.commande_devine_mot", "explique": None}
for nom, f in JEU.items():
    if f:
        corps = (f"exec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                 f"from tg import observatoire; {f}(sys.argv[1:])\" \"$@\"\n")
    else:
        corps = f"exec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); from tg import app; " \
                f"sys.argv = ['tg', 'explique'] + sys.argv[1:]; app._main()\" \"$@\"\n"
    (DOUBLURES / nom).write_text("#!/bin/sh\n" + corps)
    (DOUBLURES / nom).chmod(0o755)
for nom in ("sudo", "curl", "wget"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
    (DOUBLURES / nom).chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def bash(cmd, cwd=None):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd or terminal[0], capture_output=True, text=True, errors="replace",
                       timeout=60, env=ENV)
    return r.stdout


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=180, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
        lignes = lignes[:-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)
    return st, "\n".join(lignes) + r.stderr


def ctrl_c(cmd, apres=1.0):
    """Lance une commande au premier plan, puis envoie SIGINT (ce que fait Ctrl+C) au programme."""
    p = subprocess.Popen(["bash", "-c", "exec " + cmd], cwd=terminal[0], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, env=ENV)
    time.sleep(apres)
    p.send_signal(signal.SIGINT)
    s = p.communicate(timeout=30)[0]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=terminal[0], statut=130), s


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == T or T in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


langue.definir("fr")
D = O.donnees()
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_observatoire.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/observatoire/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
from tg import bestiaire as B, guide  # noqa: E402
verifier(all(B.espece(i)["nom"] == c["nom"] and guide.type_de(B.espece(i), "classique") == c["type"] and B.espece(i)["zone"] == c["lieu"]
             for i, c in D["creatures"].items()), f"les {len(D['creatures'])} créatures des jeux de données sont celles du VRAI bestiaire")
gardiens = set(recompenses.gardiens().values())
verifier(not gardiens & set(D["creatures"]), "les jeux de données n'utilisent aucun gardien glitch")
m = O.apprendre(O.texte_creatures(D["exemples"]))
verifier(m["n"] == 20 and m["total"] == [10, 10], f"20 exemples, 10 Feu et 10 pas Feu ({m['total']})")
res = O.tester(m, O.texte_creatures([D["piege"]], avec_reponse=False))
verifier(len(res) == 1 and res[0][3] is True and res[0][4] is False, f"la 21e créature (Cauchemarre) : le devineur dit Feu, le bestiaire dit non {res}")
mv = O.apprendre(O.texte_creatures(D["volcan"]))
s1 = O.tester(mv, O.texte_creatures(D["autres"]))
s2 = O.tester(m, O.texte_creatures(D["autres"]))
verifier(sum(x[3] == x[4] for x in s1) == 1 and all(x[3] for x in s1), "le biais du volcan : tout est Feu, 1 sur 5")
verifier(sum(x[3] == x[4] for x in s2) == 5, "avec des exemples variés : 5 sur 5")
tmp = Path(tempfile.mkdtemp())
lignes = O.corpus_lignes("fr")
(tmp / "histoire.txt").write_text("".join(x + "\n" for x in lignes), encoding="utf-8")
mots = O.mots_de((tmp / "histoire.txt").read_text(encoding="utf-8"))
top = bash("tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -1", tmp).split()
e = O.effectifs(mots)
verifier(top and int(top[0]) == e[0][1] and top[1] in [w for w, n in e if n == e[0][1]],
         f"le mot le plus fréquent : bash {top}, le jeu {e[0]}")
bash("tr ' ' '\\n' < histoire.txt > mots.txt", tmp)
top2 = bash("tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -1", tmp).split()
tp = O.top_paires(mots)
verifier(top2 and int(top2[0]) == tp[0][1] and tuple(top2[1:3]) in [p for p, n in tp if n == tp[0][1]],
         f"la paire la plus fréquente : bash {top2}, le jeu {tp[0]}")
table = O.paires(mots)
p1 = O.phrase(table, "le", "1:0", 0)
verifier(p1 == O.phrase(table, "le", "1:0", 0) and len(p1) >= 2 and all(b in table.get(a, {}) for a, b in zip(p1, p1[1:])),
         f"une phrase déterministe, faite de vraies paires : « {' '.join(p1)} »")
nb = {code: sum(len(x.split()) for x in O.corpus_lignes(code)) for code in langue.LANGUES}
verifier(all(len(O.corpus_lignes(c_)) == len(D["corpus"]) and nb[c_] > 200 for c_ in langue.LANGUES),
         f"le texte du devineur de mots existe dans les 14 langues ({nb})")
a = O.analyser(langue.t("ob.mission.floue"), ["creatures.txt"], lambda f: ["Feu", "Eau"])
verifier(a["manque"] == ["quoi", "fichier"], f"consigne floue : il manque quoi et le fichier {a}")
a = O.analyser(langue.t("ob.mission.exemple"), ["creatures.txt"], lambda f: ["Feu", "Eau"])
verifier(a == {"verbe": "compter", "fichier": "creatures.txt", "filtre": "Feu", "manque": []}, f"consigne claire comprise {a}")
a = O.analyser("Compte dans creatures.txt", ["creatures.txt"], lambda f: ["Feu"])
verifier(a["manque"] == ["filtre"], "compter sans dire quoi chercher : il manque le filtre")
c = O.texte_types().splitlines()
tri, oubliee = O.trier_assistant(c, "1:0")
verifier(len(tri) == 19 and oubliee in c and oubliee not in tri and tri == sorted(set(c) - {oubliee}), f"le tri de l'assistant oublie une ligne ({oubliee})")
(tmp / "creatures.txt").write_text("\n".join(c) + "\n", encoding="utf-8")
(tmp / "tri.txt").write_text("\n".join(tri) + "\n", encoding="utf-8")
d = bash("sort creatures.txt | diff - tri.txt", tmp)
verifier(re.fullmatch(r"\d+d\d+\n< " + re.escape(oubliee) + "\n", d) is not None, f"diff montre exactement la ligne oubliée : {d!r}")
q = O.questions("1:0")
verifier(len(q) == 5 and sum(f for _n, _i, f in q) == 2 and O.fausses_ok([str(n) for n, _i, f in q if f], "1:0")[0]
         and not O.fausses_ok(["1", "2", "3"], "1:0")[0], f"5 réponses, 2 fausses ({[n for n, _i, f in q if f]})")
verifier(O.reponse_assistant("lignes", False) == "20" and O.reponse_assistant("modulo", False) == bash("echo $((17 % 5))").strip(),
         "les bonnes réponses de l'assistant sont celles du terminal")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "observatoire"), f"fermé au début (il manque {O.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque", "cave")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"][:len(chaps) - 1]
    h["chap"] = chaps[-1]
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid", "bibliotheque")))
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "observatoire"), f"sans le niveau 6 (la cave) : toujours fermé (il manque {O.manque(st)})")
core.modifier(ouvrir)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "observatoire"), "les niveaux 4 et 6 faits : l'Observatoire s'ouvre")
verifier("observatoire" in st["histoire"].get("mondes_annonces", []), "annoncé une fois")
DO = T / "observatoire"
verifier((DO / "coupole.txt").is_file() and (DO / O.CARNET).is_file() and (DO / "missions/creatures.txt").is_file(),
         "l'Observatoire est meublé (coupole, carnet, missions)")

print("3. La traversée de l'Observatoire, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/observatoire")
verifier(lecon(st) == ("ob0", 1), f"entrer dans l'Observatoire choisit le monde : {lecon(st)}")
gr = O._graine(st)
sorties = {}
PARCOURS = [
    "ls", "cat coupole.txt",
    "observatoire mission", "cd missions", "cat mission_floue.txt", "assistant mission_floue.txt",
    'echo "?" > mission.txt', 'echo "Fais un truc" > mission.txt', 'echo "Compte les créatures Feu dans creatures.txt" > mission.txt',
    "assistant mission.txt", "assistant mission.txt > rapport.txt", "cat rapport.txt",
    "observatoire verifier", "assistant mission_tri.txt > tri.txt", "wc -l creatures.txt tri.txt",
    "sort creatures.txt | diff - tri.txt", "sh test.sh", "observatoire oubli Pikachu",
    lambda: "observatoire oubli " + O.trier_assistant(O.texte_types().splitlines(), gr)[1].split()[0],
    "sort creatures.txt > tri.txt && sh test.sh",
    "cd ..", "observatoire secrets", "cd secrets", "grep -n CLE config_partagee.txt", "sed -i '/CLE_API/d' config_partagee.txt",
    'echo "CLE_API=exemple-pas-une-vraie-cle" > .env', "chmod 644 .env", "chmod 600 .env", "echo .env >> .gitignore",
    "observatoire cle", "export CLE_API=exemple-pas-une-vraie-cle && observatoire cle",
    "cd ..", "observatoire agent", "cd chantier", "agent lance", "cat journal_agent.txt", "git diff",
    "agent valide", lambda: f"agent accepte {O.dangereuse(gr)}", lambda: f"agent refuse {O.dangereuse(gr) % 3 + 1}",
    lambda: f"agent refuse {O.dangereuse(gr)}", "agent valide", "CTRL_C agent boucle",
    "cd ..", "observatoire apprendre", "cd devineur", "head -5 exemples.txt", "awk '{print $4}' exemples.txt | sort | uniq -c",
    "devine-type apprends exemples.txt", "cat cerveau.txt", "devine-type teste nouvelle.txt", "observatoire piege lieu",
    "observatoire piege famille",
    "cd ..", "observatoire biais", "cd devineur", "cut -d ' ' -f 3 volcan.txt | sort | uniq -c",
    "cut -d ' ' -f 4 volcan.txt | sort | uniq -c", "devine-type apprends volcan.txt", "devine-type teste autres.txt",
    lambda: "observatoire biais " + next(str(n) for n, _i, r_ in O.biais_cartes(gr) if r_ == "n"),
    lambda: "observatoire biais " + next(str(n) for n, _i, r_ in O.biais_cartes(gr) if r_ == "o"),
    "devine-type teste autres.txt", "devine-type apprends exemples.txt", "devine-type teste autres.txt",
    "cd ..", "observatoire mots", "cd mots", "tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -5",
    "tr ' ' '\\n' < histoire.txt > mots.txt",
    "tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -5",
    "devine-mot suite zzzz", "devine-mot suite le", "devine-mot phrase le",
    "observatoire perroquet v v v", lambda: "observatoire perroquet " + " ".join(r_ for _n, _i, r_ in O.perroquet_cartes(gr)),
    "cd ..", "observatoire esprit", "assistant questions", "cd devineur", "wc -l exemples.txt", "cd ..", "echo $((17 % 5))", "explique rm",
    "assistant fausses 1 2 3", lambda: "assistant fausses " + " ".join(str(n) for n, _i, f in O.questions(gr) if f),
    "observatoire confier", lambda: "observatoire confier " + " ".join(r_ for _n, _i, r_ in O.confier_cartes(gr)),
    "observatoire nuances", lambda: "observatoire nuances " + " ".join(r_ for _n, _i, r_ in O.nuances_cartes(gr)),
    "observatoire equipe", lambda: "observatoire decoupe " + " ".join(O.decoupe_reponse(gr)),
    lambda: "observatoire consigne " + next(n for n, _i, r_ in O.consigne_cartes(gr) if r_ == "false"),
    lambda: "observatoire consigne " + next(n for n, _i, r_ in O.consigne_cartes(gr) if r_ == "true"),
    "cd equipe", "agent equipe", "ls", "agent stop", "ls copies | wc -l", "cat journal_equipe.txt",
    lambda: f"agent refuse {O.dangereuse(gr, 'equipe')}", "diff invites.txt liste.txt", "sh tests.sh", "agent bilan",
    "wc -l < liste.txt > compte.txt", "sh tests.sh", "agent bilan",
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    if c.startswith("CTRL_C "):
        c = c[7:]
        st, s = ctrl_c(c)
    else:
        st, s = tape(c)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st)))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:int(os.environ.get('TG_LARGE', '110'))]!r}")
    if histoire.fini(st, "observatoire"):
        break
if not histoire.fini(st, "observatoire"):
    for a_, c, b in vus[-8:]:
        print("     ", a_, c, "→", b)
verifier(histoire.fini(st, "observatoire"), f"l'Observatoire est traversé jusqu'au bout (ob0 → ob9) {lecon(st)}")
o = ANSI.sub("", sorties.get("assistant mission_floue.txt", ""))
verifier("❓" in o and "QUOI" in o, "la consigne floue : l'assistant dit qu'il n'a pas compris (il n'invente pas)")
verifier((DO / "missions/rapport.txt").read_text(encoding="utf-8").strip() == "creatures.txt : 10 lignes contiennent « Feu ».",
         "le rapport : 10 créatures Feu, la sortie redirigée dans rapport.txt")
o = sorties.get("wc -l creatures.txt tri.txt", "")
verifier(re.search(r"20 creatures\.txt\s+19 tri\.txt", o) is not None, f"wc -l : 20 contre 19 {o!r}")
verifier("✖" in sorties.get("sh test.sh", "") and "✔" in sorties.get("sort creatures.txt > tri.txt && sh test.sh", ""),
         "test.sh : ÉCHEC avec le tri de l'assistant, RÉUSSI avec sort")
verifier("CLE_API" not in (DO / "secrets/config_partagee.txt").read_text() and oct((DO / "secrets/.env").stat().st_mode)[-3:] == "600",
         "le secret a quitté le fichier partagé ; .env en 600 ; .gitignore")
o = ANSI.sub("", sorties.get("export CLE_API=exemple-pas-une-vraie-cle && observatoire cle", ""))
verifier("exe…" in o and "exemple-pas-une-vraie-cle" not in o, "observatoire cle voit la clé sans jamais l'afficher en entier")
verifier((DO / "chantier/a_nourrir.txt").read_text().splitlines() == O.liste_rangee(D["agent"]["liste"]), "Robot-Rangeur a rangé la liste")
o = sorties.get("git diff", "")
verifier(not shutil.which("git") or ("-Gloupi" in o or "+Braisillon" in o), "git diff montre ce que l'agent a changé")
o = ANSI.sub("", sorties.get(f"agent accepte {O.dangereuse(gr)}", ""))
verifier("⛔" in o and T.is_dir() and (T / "observatoire").is_dir(), "accepter la proposition dangereuse : le jeu ne la lance JAMAIS")
verifier("✋" in ANSI.sub("", sorties.get("agent valide", "")), "valider avant d'avoir refusé le danger : pas encore")
verifier(O.dans_carnet("boucle"), "agent boucle arrêté par Ctrl+C (un vrai SIGINT)")
o = ANSI.sub("", sorties.get("devine-type teste nouvelle.txt", ""))
verifier("✖" in o and "Cauchemarre" in o, "le devineur se trompe sur la 21e créature")
o = ANSI.sub("", sorties.get("awk '{print $4}' exemples.txt | sort | uniq -c", ""))
verifier(o.split() == ["10", "Feu", "10", "pas_Feu"], f"uniq -c : 10 Feu, 10 pas_Feu {o!r}")
verifier(O.dernier("score") and O.dernier("score").endswith("autres (ok)") and "1/5" in O.carnet(), "le biais : 1 sur 5, puis 5 sur 5")
o = ANSI.sub("", sorties.get("devine-mot suite le", ""))
verifier("%" in o, "devine-mot suite : les mots suivants et leurs chances sur 100")
verifier("observatoire.fausses" in recompenses.r_(st)["exploits"], "l'exploit « toutes les réponses fausses démasquées »")
verifier(not recompenses.reservee(st, {"id": "seraphibou"}, "cosmique") and recompenses.reservee({}, {"id": "seraphibou"}, "cosmique")
         and recompenses.reservee({}, {"id": "zyeuton"}, "brume") and recompenses.reservee({}, {"id": "mutaloupe"}, "cristal")
         and not recompenses.reservee({}, {"id": "etoilapin"}, "cosmique"),
         "seraphibou:cosmique, zyeuton:brume et mutaloupe:cristal n'apparaissent qu'après l'exploit ; etoilapin:cosmique reste libre")
n_copies = O.copies_faites()
verifier(0 < n_copies <= D["equipe"]["copies_max"] and (DO / "equipe/STOP").exists(), f"l'agent Copieur s'est emballé ({n_copies} copies) puis l'arrêt d'urgence")
st, _ = tape("ls")
verifier(O.copies_faites() == n_copies, "après STOP, plus aucune copie")
verifier("✖" in sorties.get("sh tests.sh", "") and (DO / "equipe/rapport_du_chef.txt").is_file(), "tests.sh : ÉCHEC du Compteur, puis tout passe ; le bilan")
verifier("✋" in ANSI.sub("", sorties.get("agent bilan", "")), "pas de bilan avant que les tests passent")
verifier("loupe_de_detective" in st["quetes"]["objets"] and st["quetes"]["titre"] == "chef_des_robots",
         "récompenses : la loupe de détective et le titre de Chef des Robots")

print("4. Les indices et la garde")
pas = {s_["cmd"]: s_ for l_ in O.LECONS.values() for s_ in l_["steps"]}
verifier(O.indice(pas["agent refuse ?"], [("sudo rm -rf /", None)]) == langue.t("ob.indice.danger"), "sudo : l'alerte")
verifier(O.indice(pas["agent refuse ?"], [("rm -rf ~/terrain_terminagotchi", None)]) == langue.t("ob.indice.danger"), "rm -rf ~ : l'alerte")
verifier(O.indice(pas["observatoire piege ?"], [("observatoire piege ?", None)]) == langue.t("ob.indice.trou"), "« ? » recopié : un trou à remplir")
O.noter("piege", "lieu (faux)")
verifier(O.indice(pas["observatoire piege ?"], [("observatoire piege lieu", None)]) == langue.t("ob.indice.rep.piege"), "le piège : la mauvaise réponse")
verifier(O.indice(pas["assistant mission.txt > rapport.txt"], [("assistant mission.txt", None)]) == langue.t("ob.indice.redirection"),
         "le rapport : la redirection oubliée")
s0 = core.load()
s0["histoire"]["chap"] = "observatoire"
verifier(O.surveiller(s0, ["sudo apt install x"]) and O.surveiller(s0, ["rm -rf ~"]), "une commande dangereuse : la créature alerte à chaque fois")
verifier(not O.surveiller(s0, ["rm -r copies"]) and not O.surveiller(s0, ["ls"]), "rm -r copies (dans l'Observatoire) n'est pas une alerte")

print("5. La vue déployée : la lunette")
x = deploie.lunettes("sort creatures.txt | diff - tri.txt && sh test.sh")
verifier([(y["outil"], y["de"], y["vers"]) for y in x] == [("diff", "deux_textes", "differences"), ("tests", "travail", "verdict")], f"{x}")
txt = ANSI.sub("", "\n".join(deploie.ecran("assistant mission.txt > rapport.txt", deploie.blocs("assistant mission.txt > rapport.txt"),
                                           1, None, 0.5, 100)))
verifier("🔭" in txt and "rapport" in txt, "la vue déployée dessine la lunette de l'assistant")
from tg import compagnon  # noqa: E402
verifier(any("devine-mot='tg devine-mot'" in b or "function devine-mot" in b for b in compagnon._blocs().values()),
         "tg installer pose les alias de l'Observatoire")

print("6. Sécurité et langues")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in O.LECONS for s in O.LECONS[lid]["steps"])
verifier("sudo" not in cmds and "rm -rf" not in cmds and not re.search(r"\b(curl|wget|pip|npm)\b", cmds),
         "aucune étape n'utilise sudo, rm -rf, ni téléchargement")
src = (RACINE / "pc/tg/observatoire.py").read_text(encoding="utf-8")
code_seul = "\n".join(l for l in src.split("\n") if not l.strip().startswith(("#", '"', "'")))
verifier(not re.search(r"urlopen|requests\.|socket|http\.client|\[\"(sudo|rm|curl|wget)\"|os\.system|shell=True", code_seul),
         "le jeu n'ouvre aucune connexion, n'appelle aucune IA, ne lance ni sudo ni rm ni shell")
verifier(all(not p_["sur"] for p_ in D["agent"]["propositions"] + D["equipe"]["propositions"] if "rm" in p_["texte"] or "sudo" in p_["texte"])
         and all("…" in p_["texte"] for p_ in D["agent"]["propositions"] + D["equipe"]["propositions"] if not p_["sur"]),
         "les propositions dangereuses sont du texte, avec un chemin « … » qui ne vise rien si on les recopiait")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier(appels == "", f"sudo, curl et wget n'ont jamais été appelés ({appels[:80]!r})")
sauve = json.dumps(core.load(), ensure_ascii=False)
verifier(D["secret"]["cle"] not in sauve and "exe…" not in sauve, "ni la clé du fichier partagé ni ce qu'affiche observatoire cle ne vont dans la sauvegarde")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m_ = [k_ for lid in O.LECONS for s in O.LECONS[lid]["steps"] for k_ in (s["dit"], s["bravo"]) if isinstance(k_, str) and k_ not in dct]
    m_ += [k_ for k_ in ("hist.observatoire.titre", "hist.observatoire.debut", "hist.observatoire.fin", "ob.ouvert.dit", "dep.lunette")
           if k_ not in dct]
    if m_:
        manque[code] = m_[:3]
verifier(not manque, f"les textes de l'Observatoire existent dans les 14 langues {manque}")
mal_compris, sans_suite, pas_un_mot = {}, {}, {}
for code in langue.LANGUES:
    langue.definir(code)
    vals = lambda f: [l.split()[-1] for l in O.texte_types().splitlines() if l.split()]
    a1 = O.analyser(O.t("ob.mission.floue"), ["creatures.txt"], vals)
    a2 = O.analyser(O.t("ob.mission.exemple"), ["creatures.txt"], vals)
    a3 = O.analyser(O.t("ob.mission.tri"), ["creatures.txt"], vals)
    if a1["manque"] != ["quoi", "fichier"] or a2["verbe"] != "compter" or a2["filtre"] != O.t("ob.type.feu") or a3["verbe"] != "trier":
        mal_compris[code] = (a1["manque"], a2["verbe"], a2["filtre"], a3["verbe"])
    mots = O.mots_de("\n".join(O.corpus_lignes()))
    ex = O.t("ob.devinemot.aide_suite").split()[-1]
    if ex not in mots[:-1]:
        sans_suite[code] = ex
    toks = [O.t(k_) for k_ in langue._charger(code) if k_.split(".")[0] == "ob" and k_.split(".")[1] in ("label", "famille", "lieu", "type")]
    if any(not x or " " in x for x in toks):
        pas_un_mot[code] = [x for x in toks if not x or " " in x][:3]
langue.definir("fr")
verifier(not mal_compris, f"dans chaque langue, l'assistant comprend la consigne d'exemple et refuse la floue {mal_compris}")
verifier(not sans_suite, f"dans chaque langue, le mot donné en exemple au devineur de mots a une suite dans l'histoire {sans_suite}")
verifier(not pas_un_mot, f"familles, lieux, types et réponses du devineur : un seul mot dans chaque langue {pas_un_mot}")
sans_esp = {}
for code in langue.LANGUES if hasattr(langue, "LANGUES") else ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]:
    langue.definir(code)
    txt = "\n".join(O.lignes_mots_intro())
    sans_esp[code] = (O.sans_espaces(), O.t("ob.mots.caracteres") in txt)
langue.definir("fr")
verifier({c for c, (a_, b_) in sans_esp.items() if a_} == {"zh", "ja"} and all(a_ == b_ for a_, b_ in sans_esp.values()),
         f"O7 : en chinois et en japonais (sans espaces), le devineur explique qu'il compte les caractères ; pas ailleurs {sans_esp}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} vérifications réussies, {ko} échecs")
sys.exit(1 if ko else 0)
