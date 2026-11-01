"""Trois enfants traversent l'Observatoire de l'IA (phase 5, ob0 → ob9), dans un VRAI shell resté ouvert —
docs/simulations/rapport_observatoire.md.

    python3 pc/outils/sim_observatoire.py            (les trois, chacun dans son propre HOME temporaire, HORS LIGNE)
    python3 pc/outils/sim_observatoire.py lea        (un seul : lea, ines ou hugo)

Comme sim_guilde.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit
dans SON terminal. L'Observatoire est ouvert d'avance (niveaux 0 à 6 faits). Aucune vraie IA n'est appelée : tout est
hors ligne ; sudo, curl et wget sont des doublures qui refusent (et notent qu'on les a appelées).
  - Léa, 7 ans : se trompe d'abord (une majuscule, une consigne floue, l'assistant sans >, le mauvais nom oublié,
    chmod 644, ACCEPTER la proposition dangereuse, valider trop tôt, laisser tourner l'agent jusqu'à sa limite, « lieu »
    pour le piège, le devineur « méchant », retester sans réapprendre, un mot qui n'existe pas, les mauvaises réponses
    fausses, tout confier, tout « vrai », le mauvais ordre, la consigne dangereuse, sudo rm -rf copies, le bilan trop tôt) ;
    puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris), puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`diff <(sort …)`, `./test.sh`, `sed -i.bak`, `printf … > .env`, `chmod u=rw,go= .env`,
    `git diff --stat`, `tr -s`, `paste <(tail …)`, `bash tests.sh`, `touch STOP`, `wc -l liste.txt | cut …`…).
Pour les trous : la créature oubliée se lit dans le diff (<), la proposition dangereuse dans le journal (rm -rf, sudo), le
piège dans cerveau.txt, les réponses fausses en comparant avec ses propres vérifications (wc, echo, tr, explique).
Vérifie : l'Observatoire fini ; l'exploit « réponses fausses » ; aucune étape validée par une commande qui a échoué ; chaque
faute de Léa reçoit une explication ; les variantes justes de Hugo acceptées ; rien hors du terrain ; aucune proposition
dangereuse exécutée ; sudo jamais passé. Code de sortie 1 en cas d'échec.
"""
import builtins
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nObservatoire de l'IA : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_obs_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ.pop("CLE_API", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_PAGER"] = "cat"
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(RACINE / "pc"))
Path(os.environ["HOME"], ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n")

from tg import app, compagnon, core, explo, histoire, langue, observatoire as O  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, f in (("observatoire", "commande"), ("assistant", "commande_assistant"), ("agent", "commande_agent"),
               ("devine-type", "commande_devine_type"), ("devine-mot", "commande_devine_mot")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"from tg import observatoire; observatoire.{f}(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "explique").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                    f"from tg import app; sys.argv = ['tg', 'explique'] + sys.argv[1:]; app._main()\" \"$@\"\n")
for nom in ("sudo", "curl", "wget"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (simulation) refusé' >&2\nexit 1\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque", "cave"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque", "cave"]
    h["chap"] = None
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == core.TERRAIN or core.TERRAIN in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


core.modifier(ouvrir)
core.TERRAIN.mkdir(exist_ok=True)
AVANT = fichiers_hors_terrain()
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C"))
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
INV = {v: k for k, v in HOMO.items()}
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + f"[{QUI}] " + m)


def propre(x):
    x = langue.sans_marques(ANSI.sub("", x))
    return "".join(INV.get(c, c) for c in x).replace(NBSP, " ")


etat = {"sortie": "", "code": 0, "terminal": []}
journal = []
memoire = {}
TAPEES = []
SORTIES = []


def tape(cmd, ctrl_c=None):
    """ctrl_c : au bout de combien de secondes l'enfant appuie sur Ctrl+C (agent boucle) ; None : jamais."""
    TAPEES.append(cmd)
    debut = time.time()
    interrompre = (lambda: time.time() - debut > ctrl_c) if ctrl_c is not None else None
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=120, interrompre=interrompre)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:200]))
    memoire.pop(cmd, None)
    memoire[cmd] = propre(etat["sortie"])
    SORTIES.append(memoire[cmd])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip().strip("`") for p in re.split(r"\s+puis\s+", texte)]
    return [p.strip().strip("`") for p in parts if p]


def lu(prefixe):
    return next((v for k, v in list(memoire.items())[::-1] if k.startswith(prefixe)), "")


def numero_dangereux(journal_txt):
    m = re.search(r"^\[propose (\d+)\] (rm -rf|sudo)", journal_txt, re.M)
    return m.group(1) if m else "?"


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == 'echo "?" > mission.txt':
        dit = langue.t("hist.ob1.3.dit")
        ex = dit.split("par exemple : ")[-1].strip()
        if QUI == "hugo":
            ex = "Liste les créatures Eau de creatures.txt"
        return st, f'echo "{ex}" > mission.txt'
    if cmd == "observatoire oubli ?":
        s = lu("sort creatures.txt | diff") or lu("diff <(sort")
        if not s:
            st = tape("sort creatures.txt | diff - tri.txt")
            s = memoire["sort creatures.txt | diff - tri.txt"]
        m = re.search(r"^< (\S+)", s, re.M)
        return st, f"observatoire oubli {m.group(1) if m else '?'}"
    if cmd == "agent refuse ?":
        s = (lu("cat journal_equipe.txt") if (core.TERRAIN / "observatoire/equipe/journal_equipe.txt").exists()
             else lu("cat journal_agent.txt") or lu("less -FX journal_agent.txt"))
        return st, f"agent refuse {numero_dangereux(s)}"
    if cmd == "observatoire piege ?":
        s = lu("cat cerveau.txt")
        return st, "observatoire piege " + ("famille" if re.search(r"^famille\s+Démons\s+Feu 7", s, re.M) else "lieu")
    if cmd == "observatoire biais ?":
        s = memoire.get("observatoire biais", "")
        m = re.search(r"^\s+(\d)\. Les exemples", s, re.M)
        return st, f"observatoire biais {m.group(1) if m else '1'}"
    if cmd in ("devine-mot suite ?", "devine-mot phrase ?"):
        s = lu("tail -n +2 mots.txt") or lu("paste")
        m = re.search(r"^\s+\d+ (\S+) \S+", s, re.M)
        return st, cmd.replace("?", m.group(1) if m else "le")
    if cmd == "observatoire perroquet ? ? ?":
        cartes = re.findall(r"^\s+\d\. (.*)$", lu("devine-mot phrase"), re.M)
        return st, "observatoire perroquet " + " ".join("f" if "vérifie" in x else "v" for x in cartes)
    if cmd == "assistant fausses ? ?":
        q = lu("assistant questions")
        reps = re.findall(r"^\s+🤖 (.*?)\s+\(sûr", q, re.M)
        wc = re.search(r"(\d+)", lu("wc -l exemples.txt") or "20").group(1)
        mod = (lu("echo $((17 % 5))") or "2").strip()
        top = lu("tr ' ' '\\n' < histoire.txt | sort") or lu("tr -s ' '")      # ce qu'il a compté en O7
        mot = top.split()[1] if len(top.split()) > 1 else ""
        if os.environ.get("TG_DEBUG"):
            print("    ? fausses", reps, wc, mod, repr(top[:40]), repr(mot))
        fausses = []
        for n, r_ in enumerate(reps, 1):
            if (n == 1 and r_ != wc) or (n == 2 and r_ != mod) or (n == 3 and r_ != mot) or (n == 4 and "efface" in r_) \
                    or (n == 5 and "récupérer" in r_):
                fausses.append(str(n))
        return st, "assistant fausses " + " ".join(fausses)
    if cmd == "observatoire confier ? ? ? ? ? ?":
        s = lu("observatoire confier")
        msgs = re.findall(r"^\s+\d\. (.*)$", s, re.M)
        return st, "observatoire confier " + " ".join(
            "g" if re.search(r"(habite|mot de passe|photo|née|m'appelle)", x) else "c" for x in msgs)
    if cmd == "observatoire nuances ? ? ? ? ?":
        s = lu("observatoire nuances")
        msgs = re.findall(r"^\s+\d\. (.*)$", s, re.M)
        return st, "observatoire nuances " + " ".join("f" if re.search(r"(forcément|ne consomme pas|est libre)", x) else "v" for x in msgs)
    if cmd == "observatoire decoupe ? ? ?":
        cartes = dict((x, n) for n, x in re.findall(r"^\s+(\d)\. (.*)$", lu("observatoire equipe"), re.M))
        ordre = [next(n for x, n in cartes.items() if k in x) for k in ("liste", "compter", "invitation")]
        return st, "observatoire decoupe " + " ".join(ordre)
    if cmd == "observatoire consigne ?":
        m = re.search(r"^\s+([abc])\) .*Ne supprime rien", lu("observatoire decoupe"), re.M)
        return st, f"observatoire consigne {m.group(1) if m else 'a'}"
    return st, cmd


def faute(cmd):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    fautes = {'echo "?" > mission.txt': 'echo "Fais un truc" > mission.txt',
              "assistant mission.txt > rapport.txt": "assistant mission.txt",
              "observatoire oubli ?": "observatoire oubli Pikachu", "chmod 600 .env": "chmod 644 .env",
              "observatoire piege ?": "observatoire piege lieu",
              "devine-mot suite ?": "devine-mot suite xyz", "assistant fausses ? ?": "assistant fausses 1 2",
              "observatoire confier ? ? ? ? ? ?": "observatoire confier c c c c c c",
              "observatoire nuances ? ? ? ? ?": "observatoire nuances v v v v v",
              "observatoire decoupe ? ? ?": "observatoire decoupe 1 2 3", "agent stop": "sudo rm -rf copies",
              "agent bilan": "agent bilan", "sort creatures.txt > tri.txt && sh test.sh": "sh test.sh"}
    if cmd == "agent refuse ?" and (core.TERRAIN / "observatoire/chantier/journal_agent.txt").exists() \
            and not (core.TERRAIN / "observatoire/equipe").exists():
        return "agent accepte " + numero_dangereux(lu("cat journal_agent.txt"))
    if cmd == "git diff" and QUI == "lea":
        return "agent valide"                                      # valider sans avoir relu ni refusé
    if cmd == "observatoire biais ?":
        m = re.search(r"^\s+(\d)\. Le devineur aime", memoire.get("observatoire biais", ""), re.M)
        return f"observatoire biais {m.group(1) if m else '1'}"
    if cmd == "observatoire consigne ?":
        m = re.search(r"^\s+([abc])\) .*sudo", lu("observatoire decoupe"), re.M)
        return f"observatoire consigne {m.group(1) if m else 'b'}"
    if cmd in fautes:
        return fautes[cmd]
    if re.match(r"^(cat|ls)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^cat coupole\.txt$", "less -FX coupole.txt"), (r"^cat mission_floue", "head mission_floue.txt"),
        (r"^sort creatures\.txt \| diff", "diff <(sort creatures.txt) tri.txt"), (r"^sh test\.sh$", "./test.sh"),
        (r"^wc -l creatures", "wc -l tri.txt creatures.txt"),
        (r"^grep -n CLE", "grep -n CLE_API config_partagee.txt"), (r"^sed -i '/CLE_API/d'", "sed -i.bak '/CLE_API/d' config_partagee.txt"),
        (r'^echo "CLE_API=', "printf 'CLE_API=exemple-pas-une-vraie-cle\\n' > .env"), (r"^chmod 600", "chmod u=rw,go= .env"),
        (r"^echo \.env >>", "printf '.env\\n' >> .gitignore"), (r"^git diff$", "git diff --stat"),
        (r"^head -5 exemples", "head -n 5 exemples.txt"),
        (r"^awk '\{print \$4\}' exemples", "awk '{print $4}' exemples.txt | sort | uniq -c | sort -rn"),
        (r"^cut -d ' ' -f 3 volcan", "cut -d' ' -f3 volcan.txt | sort | uniq -c"),
        (r"^tr ' ' '\\n' < histoire\.txt \| sort", "tr -s ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head"),
        (r"^tail -n \+2 mots", "paste -d' ' mots.txt <(tail -n +2 mots.txt) | sort | uniq -c | sort -nr | head"),
        (r"^sh tests\.sh$", "bash tests.sh"), (r"^agent stop$", "touch STOP"), (r"^ls copies \| wc -l$", "ls copies/ | wc -l"),
        (r"^wc -l < liste\.txt > compte\.txt$", "wc -l liste.txt | cut -d' ' -f1 > compte.txt"),
        (r"^cat journal_agent", "less -FX journal_agent.txt"), (r"^diff invites", "diff -u invites.txt liste.txt"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return b
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "observatoire"), "l'Observatoire devrait être ouvert (niveaux 0 à 6 faits)"
st = tape("cd ~/terrain_terminagotchi/observatoire")
for _ in range(500):
    if histoire.fini(st, "observatoire"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("ob"):
        st = tape("cd ~/terrain_terminagotchi/observatoire")
        continue
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        st = tape(idees[0])
        continue
    step = les["steps"][st["step"]]
    avant = (les["id"], st["step"])
    a_taper = montree(st, step)
    derniere = a_taper[-1]
    premiere_fois = avant not in tentes
    tentes.add(avant)
    essais = []
    if premiere_fois:
        if QUI == "lea" and faute(derniere):
            essais.append(faute(derniere))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.replace('"', " ").split():
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        if essai == "agent boucle":
            st = tape(essai)
        else:
            st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and "✖" not in propre(etat["sortie"]) \
                and "⛔" not in propre(etat["sortie"]) and "✋" not in propre(etat["sortie"]) and "❓" not in propre(etat["sortie"]) \
                and "?" not in propre(etat["sortie"])[:3]:
            sans_explication.append((avant, essai, propre(etat["sortie"])[:80]))
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    st, derniere = resoudre(derniere, st)
    if derniere == "agent boucle":                                 # Ctrl+C : Léa la première fois laisse tourner (la limite)
        st = tape(derniere, ctrl_c=None if (QUI == "lea" and premiere_fois) else 1.5)
        if not histoire.fini(st, "observatoire") and (histoire.lecon_courante(st)[0] or {}).get("id") == "ob4":
            st = tape(derniere, ctrl_c=1.5)
    else:
        st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code", "reseau")) \
            and not derniere.startswith(("agent boucle", "timeout")):
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "observatoire"), f"l'Observatoire traversé, ob0 → ob9 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("observatoire.fausses" in ex, "l'exploit « toutes les réponses fausses démasquées »")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi {nouveaux[:3]}")
verifier(core.TERRAIN.is_dir() and (core.TERRAIN / "observatoire/coupole.txt").is_file(),
         "aucune proposition dangereuse exécutée : le terrain est intact")
appels = JOURNAL.read_text() if JOURNAL.exists() else ""
verifier("curl" not in appels and "wget" not in appels, f"aucun téléchargement tenté ({appels[:60]!r})")
verifier(O.dans_carnet("boucle") and (core.TERRAIN / "observatoire/equipe/STOP").exists(), "Ctrl+C sur l'agent qui tourne en rond ; l'arrêt d'urgence de l'équipe")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    tout = " ".join(j[4] for j in journal) + " " + " ".join(SORTIES)
    verifier("JAMAIS" in tout and "Pas si vite" in tout and "sudo" in appels and ("STOP" in tout or "Stop" in tout),
             "accepter le danger, valider trop tôt, sudo rm -rf : expliqués, et le danger jamais lancé")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 14, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
