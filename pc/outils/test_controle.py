"""Le Poste de Contrôle (phase 5, docs/programme.md § 2.15 et § 7.13 « Linux de A à Z »), sur PC.

    python3 pc/outils/test_controle.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/controle/vecteurs.json, mêmes résultats en Kotlin) ; les
     caisses de l'entrepôt (du est d'accord avec le jeu), le carnet de bord et ses alertes, les réveils cron (champs,
     équivalences, prochaine sonnerie), la distribution reconnue, l'équipage, la vague ;
  2. l'arbre du Carrefour : fermé tant que les niveaux 0 à 6 ne sont pas faits, puis ouvert et annoncé une fois ;
     meublé (consignes, registre, entrepôt, sac à dos, réveils, équipage) ;
  3. la traversée ct0 → ct7 comme un enfant (vraies commandes dans bash) : ps, $$, /proc, sleep au premier plan puis
     en arrière-plan, jobs, kill %1, top ; free, df, du, la caisse la plus lourde, uptime, nproc, les jauges ; HOME,
     PATH et son compte, which, export, bash -c, alias, source ; le carnet de bord, tail, grep -c, tail -f ; crontab -l,
     le réveil de la partie entre guillemets (sans guillemets : expliqué), un réveil ajouté au fichier du terrain ;
     os-release, les familles, installer en VM, le magasin, les services, l'équipage ; l'alerte : les suspects arrêtés
     avec kill, le veilleur épargné (un premier essai où il est arrêté par erreur : expliqué, la vague recommence),
     l'exploit « la vague » et ses variantes réservées ; le pupitre et le titre ;
  4. les indices (sudo, une commande qui changerait la machine, « ? » recopié, mauvaises réponses, kill d'un numéro
     qui n'est pas au jeu, kill 1) et la garde ;
  5. la vue déployée : le tableau de bord ;
  6. sécurité : rien hors du terrain ; aucune étape n'utilise sudo, n'installe, n'arrête un service, ne crée un compte
     ni ne pose un vrai cron ; le jeu ne tue que SES processus (numéro ET nom vérifiés) ; aucun processus du jeu ne
     reste ; 14 langues ;
  7. le contenu existant réutilisé sans le casser (machines0, systeme1, dortoir0, systeme2, dortoir1, scripts2).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_ctl_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, controle as K, programme, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
(DOUBLURES / "controle").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                    f"from tg import controle; controle.commande(sys.argv[1:])\" \"$@\"\n")
for nom in ("sudo", "useradd", "systemctl-change"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


from tg.coquille import Coquille  # noqa: E402
SHELL = Coquille(HOME, env=ENV)


def bash(cmd, cwd=None):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd or terminal[0], capture_output=True, text=True, errors="replace",
                       timeout=60, env=ENV)
    return r.stdout


def tape(cmd):
    """Une ligne tapée dans un VRAI shell resté ouvert (les tâches de fond, les alias et les variables restent)."""
    s, code, d = SHELL.lancer(cmd, delai=20)
    terminal[0] = d
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=code)
    return st, s


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
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_controle.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/controle/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
gr = "7:42"
tmp = Path(tempfile.mkdtemp())
for nom, _k in K.caisses(gr):
    (tmp / f"{nom}.bin").write_bytes(K.caisse_octets(gr, nom))
du = [l.split("\t") for l in bash("du -k *", tmp).strip().split("\n")]
gros = max(du, key=lambda x: int(x[0]))[1]
verifier(gros == K.caisse_lourde(gr) + ".bin" and len({k for _n, k in K.caisses(gr)}) == 4,
         f"l'entrepôt : du -k voit la même caisse la plus lourde que le jeu ({gros})")
verifier(K.caisse_ok(K.caisse_lourde(gr), gr) and K.caisse_ok(K.caisse_lourde(gr) + ".bin", gr)
         and not K.caisse_ok("cartes_du_ciel" if K.caisse_lourde(gr) != "cartes_du_ciel" else "sons_du_moteur", gr),
         "la caisse : le nom avec ou sans .bin ; une autre refusée")
(tmp / "j.log").write_text("\n".join(K.journal_lignes(gr)) + "\n")
verifier(bash("grep -c ALERTE j.log", tmp).strip() == str(K.nb_alertes(gr)) and 3 <= K.nb_alertes(gr) <= 6,
         f"le carnet de bord : grep -c ALERTE compte comme le jeu ({K.nb_alertes(gr)})")
verifier(K.cron_pareil("*/15 * * * *", "0,15,30,45 * * * *") and K.cron_pareil("0 20 * * 0", "0 20 * * 7")
         and not K.cron_pareil("0 12 * * *", "12 0 * * *") and K.cron("60 * * * *") is None,
         "cron : */15 = 0,15,30,45 ; dimanche 0 = 7 ; l'ordre des champs compte ; 60 minutes refusé")
import datetime  # noqa: E402
verifier(K.prochaine("30 7 * * 1-5 x", datetime.datetime(2026, 11, 6, 7, 30)) == datetime.datetime(2026, 11, 9, 7, 30),
         "cron : la prochaine sonnerie après un vendredi 7 h 30 est le lundi 7 h 30")
osr = K.os_release()
verifier(not osr or K.distribution_ok(osr.get("ID", ""), osr), f"la distribution de cette machine reconnue ({osr.get('ID')})")
verifier(K.equipage_ajoute(K.equipage_texte(), "mousse")[1] == 1001 and K.equipage_ajoute(K.equipage_texte(), "root")[1] is None
         and not K.nom_valide("Élève") and not K.nom_valide("1x"), "l'équipage : mousse prend l'UID 1001 ; root existe ; noms invalides refusés")
verifier(len(K.vague_suspects(gr, 1)) == 3 and K.donnees()["vague"]["veilleur"] not in K.vague_suspects(gr, 1)
         and K.vague_suspects(gr, 1) != K.vague_suspects(gr, 2) or K.vague_suspects(gr, 2) != K.vague_suspects(gr, 3),
         f"la vague : 3 suspects tirés (vague 1 : {K.vague_suspects(gr, 1)}), le veilleur à part")
reserve = next(m for m in programme.donnees()["mondes"] if m["id"] == "controle")
verifier(reserve["exploits"][0]["id"] == "controle.vague" and reserve["types"] == ["machine", "roche"]
         and all(recompenses.reservee({}, {"id": v.split(":")[0]}, v.split(":")[1]) for v in reserve["variantes_reservees"]),
         f"récompenses : types Machine et Roche, exploit « la vague », variantes réservées {reserve['variantes_reservees']}")
autres = {v for m in programme.donnees()["mondes"] if m["id"] != "controle" for v in m.get("variantes_reservees", [])}
verifier(not autres & set(reserve["variantes_reservees"]), "aucune variante réservée par un autre monde")
from tg import bestiaire as B_, guide as G_  # noqa: E402
verifier(all(v.split(":")[1] in [x if isinstance(x, str) else x.get("id") for x in (B_.espece(v.split(":")[0]).get("variantes") or [])]
             and G_.type_de(v.split(":")[0], v.split(":")[1]) in ("machine", "roche") for v in reserve["variantes_reservees"]),
         "les variantes réservées EXISTENT (bestiaire) et sont de type Machine ou Roche")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "controle"), f"fermé au début (il manque {K.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque", "cave")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = list(chaps[:-1])
    h["chap"] = chaps[-1]
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                "observatoire", "donnees"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid", "bibliotheque")))
st = core.load()
verifier(not histoire.ouvert(st, "controle"), f"sans le niveau 6 (les cadenas) : toujours fermé (il manque {K.manque(st)})")
core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "controle"), "les niveaux 0 à 6 faits : le Poste s'ouvre")
verifier("controle" in st["histoire"].get("mondes_annonces", []), "annoncé une fois")
D = T / "controle"
verifier((D / "consignes_du_poste.txt").is_file() and (D / K.REGISTRE).is_file() and (D / "sac_a_dos.sh").is_file()
         and (D / "reveils.crontab").is_file() and (D / "equipage.txt").is_file() and len(list((D / "entrepot").glob("*.bin"))) == 4,
         "le Poste est meublé (consignes, registre, sac à dos, réveils, équipage, 4 caisses)")

print("3. La traversée du Poste, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/controle")
verifier(lecon(st) == ("ct0", 1), f"entrer dans le Poste choisit le monde : {lecon(st)}")
gr = K._graine(st)
sit = K.cron_situation(gr)
osr = K.os_release()
sorties = {}


def kill_suspects():
    return "kill " + " ".join(str(p) for p, _n in K.suspects_vivants())


def kill_veilleur():
    return "kill " + " ".join(str(p) for p, n in K.vivants() if n == K.donnees()["vague"]["veilleur"])


PARCOURS = [
    "ls", "cat consignes_du_poste.txt",
    "ps", "echo $$", "ls /proc/$$", "head -3 /proc/$$/status", "controle habitants", "sleep 2", "sleep 5",
    "sleep 60 &", "jobs", "kill %1", "top -bn1 | head -3",
    "free -h", "df -h .", "du -sh entrepot/*", "controle entrepot ?", "controle entrepot cartes_du_ciel",
    lambda: f"controle entrepot {K.caisse_lourde(gr)}", "uptime", "nproc", "controle jauges",
    "echo $HOME", "echo $PATH | tr ':' '\\n'", "controle path 999", lambda: f"controle path {len(os.environ['PATH'].split(':'))}",
    "which ls", "export COULEUR=bleu", "bash -c 'echo $COULEUR'", "alias salut='echo Bonjour !'", "cat sac_a_dos.sh",
    "bash sac_a_dos.sh", "source sac_a_dos.sh", "echo $POSTE",
    "controle alertes 3", "controle journal", "tail -n 5 carnet_de_bord.log", "grep -c ALERTE carnet_de_bord.log",
    "controle alertes 99", lambda: f"controle alertes {K.nb_alertes(gr)}", "timeout 1 tail -f carnet_de_bord.log",
    "journalctl --user -n 20 --no-pager", "dmesg | tail -3",
    "controle reveils", "crontab -l", "cat reveils.crontab", "controle cron 0 0 * * *", 'controle cron "? ? ? ? ?"',
    'controle cron "1 1 1 1 1"', lambda: f'controle cron "{sit["rep"]}"', 'echo "*/15 * * * * echo RONDE >> ronde.log"',
    'echo "*/15 * * * * echo RONDE >> ronde.log" >> reveils.crontab', "controle reveils",
    "cat /etc/os-release", "controle distribution licorneOS", lambda: f"controle distribution {osr.get('ID', 'linux')}",
    "controle familles", "controle familles d d d d d",
    lambda: "controle familles " + " ".join(r_ for _n, _i, r_ in K.familles_cartes(gr)), "controle installer",
    "rpm -qa | wc -l" if histoire._outil("rpm+/usr/lib/sysimage/rpm") else "true",
    "dpkg -l | grep -c '^ii'" if histoire._outil("dpkg+/var/lib/dpkg/status") else "true",
    "controle magasin", "systemctl list-units --type=service --state=running --no-pager | head -5", "controle services",
    "cut -d: -f1 /etc/passwd | head -3", "controle useradd Élève", "controle useradd mousse", "tail -2 equipage.txt",
    "controle tableau", "controle alerte", "ps aux | grep fictif", kill_veilleur, "controle tableau", "controle alerte",
    "ps aux | grep fictif", kill_suspects, "controle tableau",
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    st, s = tape(c)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st)))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:100]!r}")
    if histoire.fini(st, "controle"):
        break
if not histoire.fini(st, "controle"):
    for a, c, b in vus[-10:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "controle"), f"le Poste est traversé jusqu'au bout (ct0 → ct7) {lecon(st)}")
etape = {c: (a, b) for a, c, b in vus}
verifier(etape["sleep 2"][0] != etape["sleep 2"][1] and etape["sleep 60 &"][1][0] == "ct1" and etape["kill %1"][1][1] == 9,
         "K1 : sleep 2 au premier plan (un autre nombre que 5 compte aussi), sleep 60 & en arrière-plan, jobs, kill %1")
o = sorties.get("jobs", "")
verifier(re.search(r"\[1\]\+\s+Running\s+sleep 60 &", o) is not None, f"jobs montre la tâche : {o.strip()!r}")
verifier("✖" in ANSI.sub("", sorties.get("controle entrepot cartes_du_ciel", "✖")) or K.caisse_lourde(gr) == "cartes_du_ciel",
         "l'entrepôt : une caisse plus légère refusée")
verifier(etape["bash sac_a_dos.sh"][0] == etape["bash sac_a_dos.sh"][1] and sorties.get("echo $POSTE", "").strip() == "controle",
         "K3 : bash sac_a_dos.sh ne charge rien (un autre habitant), source sac_a_dos.sh le charge : echo $POSTE → controle")
verifier(sorties.get("bash -c 'echo $COULEUR'", "").strip() == "bleu", "export : le nouveau bash a emporté COULEUR")
verifier("tg_ctl" not in (HOME / ".bashrc").read_text(encoding="utf-8", errors="replace") if (HOME / ".bashrc").exists() else True,
         "le vrai ~/.bashrc n'est pas touché par le sac à dos")
verifier(not (D / "carnet_de_bord.log").exists() or etape["controle alertes 3"][0] == etape["controle alertes 3"][1],
         "controle alertes avant le journal : rien ne valide")
verifier(sorties.get("grep -c ALERTE carnet_de_bord.log", "").strip() == str(K.nb_alertes(gr)), "grep -c ALERTE : le bon compte")
o = ANSI.sub("", sorties.get("controle cron 0 0 * * *", ""))
verifier("guillemets" in o or not any((D / x).exists() for x in os.listdir(D)), f"cron sans guillemets : bash a remplacé les * (expliqué) {o[:80]!r}")
verifier(etape['echo "*/15 * * * * echo RONDE >> ronde.log"'][0] == etape['echo "*/15 * * * * echo RONDE >> ronde.log"'][1],
         "un réveil affiché mais pas ajouté au fichier : rien ne valide")
o = ANSI.sub("", sorties.get("controle reveils", ""))
verifier("jamais" in ANSI.sub("", [s_ for c_, s_ in sorties.items() if c_ == "controle reveils"][0]),
         "les réveils : le jeu dit qu'il ne lance jamais ces commandes")
verifier(not (D / "ronde.log").exists() and not (D / "reveil.log").exists(), "aucun réveil du fichier n'a été lancé")
eq = (D / "equipage.txt").read_text()
verifier("mousse:x:1001:1001::/home/mousse:/bin/bash" in eq and "Élève" not in eq, "l'équipage du Poste : mousse (UID 1001) ; « Élève » refusé")
o = ANSI.sub("", sorties.get("controle tableau", ""))
verifier("controle alerte" in o, "le tableau avant l'alerte : il dit comment la déclencher")
verifier(any("veilleur" in ANSI.sub("", s_) and "Oups" in ANSI.sub("", s_) for c_, s_ in sorties.items() if c_ == "controle tableau")
         or "veilleur" in str([ANSI.sub("", x) for x in sorties.values()]), "le veilleur arrêté par erreur : expliqué")
verifier("controle.vague" in recompenses.r_(st)["exploits"], "l'exploit « la vague » (tous les suspects, le veilleur épargné)")
verifier(not any(recompenses.reservee(st, {"id": v.split(":")[0]}, v.split(":")[1]) for v in reserve["variantes_reservees"])
         and recompenses.faveur(st) is not None, "après l'exploit : les variantes réservées sont rencontrables, une faveur active")
verifier("pupitre" in st["quetes"]["objets"] and st["quetes"]["titre"] == "admin_du_poste",
         "récompenses : le pupitre à voyants et le titre d'Admin du Poste")
verifier(K.veilleur_vivant(), "le veilleur fait toujours sa ronde")

print("4. Les indices et la garde")
pas = {s_["cmd"]: s_ for l_ in K.LECONS.values() for s_ in l_["steps"]}
verifier(K.indice(pas["controle entrepot ?"], [("sudo du -sh /", None)]) == langue.t("ct.indice.sudo"), "sudo : jamais ici")
verifier(K.indice(pas["controle magasin"], [("dnf install cowsay", None)]) == langue.t("ct.indice.adulte"), "installer : avec un adulte")
verifier(K.indice(pas["controle services"], [("systemctl restart cups", None)]) == langue.t("ct.indice.adulte"), "redémarrer un service : avec un adulte")
verifier(K.indice(pas["controle useradd ?"], [("useradd mousse", None)]) == langue.t("ct.indice.adulte"), "useradd : avec un adulte (dans une VM)")
verifier(K.indice(pas["controle entrepot ?"], [("controle entrepot ?", None)]) == langue.t("ct.indice.trou"), "« ? » recopié : un trou")
verifier(K.indice(pas['controle cron "? ? ? ? ?"'], [("controle cron 0 7 a b c", None)]) == langue.t("ct.indice.guillemets"),
         "cron sans guillemets : mets des guillemets")
K.noter("alertes", "99 (faux)")
verifier(K.indice(pas["controle alertes ?"], [("controle alertes 99", None)]) == langue.t("ct.indice.rep.alertes"), "les alertes : recompte")
verifier(K.kill_etrangers("kill %1") == [] and K.kill_etrangers("kill -9 1") == ["large"] and K.kill_etrangers("kill -1") == ["large"]
         and K.kill_etrangers("pkill sleep") == ["large"] and K.kill_etrangers("pkill -f fictif") == []
         and K.kill_etrangers("kill 99999999") == [99999999], "kill : %1 est à toi ; kill 1, kill -1, pkill sleep sont trop larges ; un numéro inconnu repéré")
s0 = core.load()
s0.setdefault("controle", {})["faits"] = []
verifier(K.surveiller(s0, ["kill -1"]) and K.surveiller(s0, ["kill -1"]), "kill -1 : la créature alerte À CHAQUE FOIS")
verifier(K.surveiller(s0, ["sudo apt install cowsay"]),
         "sudo apt install : la règle rappelée")
verifier(K.surveiller(s0, ["systemctl stop cups"]), "systemctl stop : avec un adulte")

print("5. La vue déployée : le tableau de bord")
x = deploie.tableaux("ps aux | grep fictif; kill 12; sudo systemctl restart cups")
verifier([(y["jauge"], y["sens"]) for y in x] == [("habitants", "lit"), ("habitants", "arrete"), ("services", "change")], f"{x}")
txt = ANSI.sub("", "\n".join(deploie.ecran("export COULEUR=bleu", deploie.blocs("export COULEUR=bleu"), 1, None, 0.5, 100)))
verifier("📟" in txt and "sac à dos" in txt, "la vue déployée dessine le tableau de bord d'export")
from tg import compagnon  # noqa: E402
verifier(any("controle='tg controle'" in b or "function controle" in b for b in compagnon._blocs().values()), "tg installer pose l'alias controle")

print("6. Sécurité et langues")
K.arreter_tout()
SHELL.lancer("kill %1 2>/dev/null; true")
time.sleep(0.2)
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in K.LECONS for s in K.LECONS[lid]["steps"])
verifier("sudo" not in cmds and not re.search(r"\b(dnf|apt|pacman)\s+install|systemctl\s+(start|stop|restart)|(?<!controle )useradd\s|crontab\s+-e", cmds),
         "aucune étape n'utilise sudo, n'installe, n'arrête un service, ne crée un compte ni ne pose un vrai cron")
src = (RACINE / "pc/tg/controle.py").read_text(encoding="utf-8")
code_seul = "\n".join(l for l in src.split("\n") if not l.strip().startswith(("#", '"', "'")))
verifier(not re.search(r"\[\"(sudo|useradd|crontab|dnf|apt|pkill|killall)\"|\"systemctl\", \"(start|stop|restart)|urlopen|requests\.", code_seul)
         and code_seul.count("os.kill(") == 3, "le jeu ne lance ni sudo, ni useradd, ni crontab, ni installation ; os.kill seulement sur SES processus")
verifier(not K.vivants() and not (JOURNAL.exists() and JOURNAL.read_text()), "aucun processus du jeu ne reste ; sudo jamais appelé")
pids_vus = set(json.loads((core.SAVE_DIR / "controle" / "lances.json").read_text()))
verifier(len(pids_vus) >= 8, f"le jeu se souvient de tous les processus qu'il a lancés (deux vagues : {len(pids_vus)})")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k_ for lid in K.LECONS for s in K.LECONS[lid]["steps"] for k_ in (s["dit"], s["bravo"]) if isinstance(k_, str) and k_ not in dct]
    m += [k_ for k_ in ("hist.controle.titre", "hist.controle.debut", "hist.controle.fin", "ct.ouvert.dit", "dep.tableau",
                        "core.win.apostrophe") if k_ not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes du Poste existent dans les 14 langues {manque}")

print("7. Le contenu existant réutilisé sans le casser")
for lid in ("machines0", "systeme1", "dortoir0", "systeme2", "dortoir1", "scripts2"):
    try:
        d_ = histoire.lecon_def(lid)
        verifier(bool(d_ and d_["steps"]), f"{lid} existe toujours ({len(d_['steps'])} étapes)")
    except Exception as e:                             # noqa: BLE001
        kt = (RACINE / "app/src/main/java/fr/terminagotchi/Histoire.kt").read_text(encoding="utf-8")
        verifier(f'"{lid}"' in kt, f"{lid} existe toujours (Android : {type(e).__name__})")
verifier(reserve["reutilise"]["lecons"] == ["machines0", "systeme1", "dortoir0", "systeme2", "dortoir1", "scripts2"],
         "programme.json : le Poste cite le contenu réutilisé (§ 2.19)")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
