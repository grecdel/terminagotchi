"""Trois enfants défendent la Citadelle (phase 5, cit0 → cit16), dans un VRAI shell resté ouvert —
docs/simulations/rapport_citadelle.md.

    python3 pc/outils/sim_citadelle.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/sim_citadelle.py lea        (un seul : lea, ines ou hugo)

Comme sim_port.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu écrit dans
SON terminal. La Citadelle est ouverte d'avance (nid, bibliothèque et cave finis : l'arbre du Carrefour).
  - Léa, 7 ans : se trompe d'abord (une majuscule, un nom de fichier mal écrit, un « sudo » vu à la télé), recopie
    « ? » une fois, lance le cadeau ./cadeau.sh par curiosité, donne un faux drapeau, appelle l'inspecteur trop tôt ;
    puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`ls -la`, `chmod go-rw`, `chmod 0600`, `grep -rn`, `find -type f … -delete`,
    `kill -9`, `sha256sum --check`, `tar -czf`, `uniq -c | sort -rn`…).
Vérifie : la Citadelle finie (les 2 exploits), aucune étape validée par une commande qui a échoué, chaque faute de Léa
reçoit une explication, les variantes justes de Hugo acceptées, aucun processus fictif ne reste, rien d'écrit hors du
terrain, jamais de sudo exécuté, seulement des clés d'exemple. Code de sortie 1 en cas d'échec.
"""
import builtins
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nCitadelle : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_cit_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, citadelle as C, compagnon, core, explo, histoire, langue, port  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
SORTIES = {"ping": "64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.03 ms\n3 packets transmitted, 3 received, 0% packet loss",
           "ss": "State  Recv-Q Send-Q Local Address:Port Peer Address:Port\nLISTEN 0 5 127.0.0.1:8042 0.0.0.0:*",
           "ip": "1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\ndefault via 10.0.0.1 dev eth0",
           "tracepath": " 1:  127.0.0.1    0.05ms reached", "hostname": "machine"}
for outil, sortie in SORTIES.items():
    if not shutil.which(outil):
        (DOUBLURES / outil).write_text(f"#!/bin/sh\ncat <<'FIN'\n{sortie}\nFIN\n")
if not shutil.which("ssh-keygen"):
    (DOUBLURES / "ssh-keygen").write_text('#!/bin/sh\nf=""; while [ $# -gt 0 ]; do [ "$1" = "-f" ] && f="$2"; shift; done\n'
                                         'echo "-----FAUSSE CLE-----" > "$f"; chmod 600 "$f"\n'
                                         'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAdoublure explorateur" > "$f.pub"\n')
if not shutil.which("ssh"):
    (DOUBLURES / "ssh").write_text("#!/bin/sh\necho 'OpenSSH_9.6p1, OpenSSL 3.0.13' >&2\n")
# `citadelle …` comme l'alias citadelle='tg citadelle' posé par tg installer ; un faux sudo qui n'exécute RIEN (il dit
# seulement qu'il refuse) : un enfant peut taper sudo, la simulation vérifie qu'il n'en a jamais besoin
(DOUBLURES / "citadelle").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                     "from tg import citadelle; citadelle.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (simulation) refusé' >&2\nexit 1\n")
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
    h["chap"] = "cave"
    h.setdefault("mondes_annonces", []).append("port")
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
core.TERRAIN.mkdir(exist_ok=True)
SH = Coquille(HOME, env=dict(os.environ, LC_ALL="C.UTF-8"))
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
journal = []          # (étape, commande, code, lu) : la partie entière, pour le rapport


def tape(cmd):
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=20)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:160]))
    memoire[cmd.split()[0] if cmd.split() else ""] = propre(etat["sortie"])
    memoire[cmd] = propre(etat["sortie"])
    if cmd.startswith("citadelle drapeau TG{") and "validé" in memoire[cmd]:
        memoire.setdefault("_drapeaux", []).append(cmd.split()[-1])
    return st


memoire = {}


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip() for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip() for p in parts if p]


def pids_lus():
    """Les numéros que l'enfant lit dans la dernière sortie de ps (2e colonne des lignes « fictif », sans le grep)."""
    out = []
    for cle in ("ps aux | grep fictif", "ps -ef | grep fictif", "ps"):
        for l in memoire.get(cle, "").split("\n"):
            m = l.split()
            if len(m) > 2 and "fictif" in l and "grep" not in l and m[1].isdigit():
                out.append(m[1])
        if out:
            break
    return out


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "echo ? > intrus.txt":
        lignes = [l.split() for l in memoire.get("grep", "").split("\n") if len(l.split()) == 2 and l.split()[0].isdigit()]
        if not lignes:
            st = tape('grep ECHEC journaux/acces.log | cut -d " " -f 4 | sort | uniq -c | sort -n')
            lignes = [l.split() for l in propre(etat["sortie"]).split("\n") if len(l.split()) == 2]
        return st, "echo " + max(lignes, key=lambda x: int(x[0]))[1] + " > intrus.txt"
    if cmd == "kill ?":
        if not pids_lus():
            st = tape("ps aux | grep fictif")
        return st, "kill " + " ".join(pids_lus())
    if cmd == "echo ? > altere.txt":
        for l in memoire.get("sha256sum -c empreintes_tresor.sha256", memoire.get("sha256sum", "")).split("\n"):
            if "FAILED" in l and ":" in l:
                return st, "echo " + Path(l.split(":")[0]).stem + " > altere.txt"
    if cmd == "citadelle facteur ? ? ?":
        st = tape("citadelle facteur")
        bons = []
        for l in propre(etat["sortie"]).split("\n"):
            m = re.match(r"\s*(\d)\.\s+(.*)$", l)
            if m and re.search(r"(lien|URGENT|mot de passe)", m.group(2)) and "commence" not in m.group(2):
                bons.append(m.group(1))
        return st, "citadelle facteur " + " ".join(bons)
    if cmd == "citadelle drapeau ?":
        vus = re.findall(r"TG\{[^}]+\}", " ".join(v for k, v in memoire.items() if k.startswith("grep -r")))
        donnes = set(memoire.get("_drapeaux", []))
        reste = [x for x in dict.fromkeys(vus) if x not in donnes and x.split("-")[0][3:] == boite_courante(st)]
        return st, "citadelle drapeau " + (reste[0] if reste else "?")
    return st, cmd


def boite_courante(st):
    les, _ = histoire.lecon_courante(st)
    return {"cit13": "enumeration", "cit14": "droits", "cit15": "secrets"}.get((les or {}).get("id"), "")


def reparer_vague():
    """La grande vague : l'enfant lit le tableau, répare ce qui est rouge, avec ce qu'il a appris."""
    tab = propre(etat["sortie"])
    if re.search(r"✖ glitchs", tab):
        tape('find . -name "*.glitch"')
        tape('find . -name "*.glitch" -delete')
    if re.search(r"✖ processus", tab):
        tape("ps aux | grep fictif")
        tape("kill " + " ".join(pids_lus()))
    if re.search(r"✖ secrets", tab):
        tape('find . -maxdepth 1 -perm -o+r -name "*secret*"')
        for f in propre(etat["sortie"]).split("\n"):
            if f.strip():
                tape(f"chmod 600 {f.strip()}")


def faute(cmd, st):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd == "chmod 600 coffre.txt":
        return "chmod 600 cofre.txt"
    if cmd == "kill ?":
        return "sudo kill " + " ".join(pids_lus() or ["1"])
    if cmd == "echo ? > intrus.txt":
        return cmd                                        # recopie le « ? »
    if cmd == "chmod -x cadeau.sh":
        return "./cadeau.sh"                              # par curiosité : elle lance le cadeau
    if cmd == "citadelle drapeau ?" and boite_courante(st) == "enumeration":
        return "citadelle drapeau TG{abc}"
    if cmd.startswith("chmod o-rwx boites/enumeration"):
        return "citadelle inspecteur enumeration"         # l'inspecteur trop tôt
    if cmd.startswith("openssl enc -aes-256-cbc"):
        return cmd.replace(C.PASSE, "1234")               # une autre clé que l'exemple
    if cmd == "citadelle facteur ? ? ?":
        return "citadelle facteur 1 2 3"
    if re.match(r"^(cat|ls|grep|find)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^ls -l coffre\.txt$", "ls -la coffre.txt"), (r"^chmod 600 coffre\.txt$", "chmod go-rw coffre.txt"),
        (r"^chmod u\+x ronde\.sh$", "chmod 744 ronde.sh"), (r"^grep veilleurs groupes\.txt$", "grep -n veilleurs groupes.txt"),
        (r"^\(umask 077; touch carnet_secret\.txt\)$", "(umask 0077 && touch carnet_secret.txt)"),
        (r"^tail -n 5 (\S+)$", r"tail -5 \1"), (r"^grep -c ECHEC (\S+)$", r"grep ECHEC \1 | wc -l"),
        (r'^grep ECHEC (\S+) \| cut -d " " -f 4 \| sort \| uniq -c \| sort -n$', r'grep ECHEC \1 | cut -d" " -f4 | sort | uniq -c | sort -rn'),
        (r'^find \. -name "\*\.glitch"$', "find . -type f -name '*.glitch'"),
        (r'^find \. -name "\*\.glitch" -delete$', "find . -type f -name '*.glitch' -delete"),
        (r"^cat cadeau\.sh$", "head -n 20 cadeau.sh"), (r"^grep rm cadeau\.sh$", "grep -n rm cadeau.sh"),
        (r"^chmod -x cadeau\.sh$", "chmod a-x cadeau.sh"), (r"^ps aux \| grep fictif$", "ps -ef | grep fictif"),
        (r"^sha256sum -c (\S+)$", r"sha256sum --check \1"), (r"^tar czf (\S+) parchemins$", r"tar -czf \1 parchemins/"),
        (r"^tar xzf (\S+)$", r"tar -xzf \1"), (r"^diff (\S+) (\S+)$", r"diff -u \1 \2"),
        (r"^wc -l mots\.txt$", "wc -l < mots.txt"), (r"^shuf -n 4 mots\.txt$", "shuf -n4 mots.txt"),
        (r"^ls -la (\S+)$", r"ls -lA \1"), (r'^grep -r "TG\{" (\S+)$', r"grep -rn TG \1"),
        (r"^find boites/droits -perm -o\+w$", "find boites/droits -perm -002"),
        (r"^chmod o-rwx boites/droits/\*$", "chmod o= boites/droits/*"), (r"^rm (boites/\S+)$", r"rm -f \1"),
        (r"^grep -r mot_de_passe (\S+)$", r"grep -ri mot_de_passe \1"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return re.sub(a, b, cmd)
    return None


fausses, sans_indice, variantes_ok, variantes_refusees, cadeau = [], [], [], [], {}
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "citadelle"), "la Citadelle devrait être ouverte (nid, bibliothèque et cave finis)"
st = tape("cd ~/terrain_terminagotchi/citadelle")
for _ in range(500):
    if histoire.fini(st, "citadelle"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("cit"):
        st = tape("cd ~/terrain_terminagotchi/citadelle")
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
        if QUI == "lea" and faute(derniere, st):
            essais.append(faute(derniere, st))
        if QUI == "hugo" and variante(derniere):
            essais.append(variante(derniere))
        if QUI == "ines" and "?" in derniere.split():
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        tresor_avant = (core.TERRAIN / "citadelle/bac_a_sable/tresor_1.txt").exists()
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if essai == "./cadeau.sh":
            cadeau = {"avant": tresor_avant, "apres": (core.TERRAIN / "citadelle/bac_a_sable/tresor_1.txt").exists(),
                      "prevenu": any("LIT" in x for x in etat["terminal"]), "valide": apres != avant}
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]) and essai != "./cadeau.sh":
            sans_indice.append((avant, essai, etat["sortie"][:60]))
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    st, derniere = resoudre(derniere, st)
    if les["id"] == "cit16" and st["step"] == 2:
        st = tape("citadelle tableau")
        reparer_vague()
    st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "citadelle"), f"la Citadelle défendue, cit0 → cit16 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier({"citadelle.boite", "citadelle.vague"} <= set(ex), f"les deux exploits de la Citadelle {sorted(ex)}")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
r = subprocess.run(["bash", "-c", "ps -eo args | grep -c '^[a-z_]*_fictif '"], capture_output=True, text=True)
verifier(r.stdout.strip() == "0" and not C.fictifs_vivants(), "plus aucun processus fictif à la fin")
cles = set()
for _l, _s, c, _code, _lu in journal:
    cles |= set(re.findall(r"pass:(\S+)", c))
verifier(cles <= {C.PASSE, C.MAUVAISE, "1234"}, f"seulement des clés d'exemple tapées {sorted(cles)}")
if QUI == "lea":
    verifier(not sans_indice, f"chaque faute reçoit une explication {sans_indice[:4]}")
    verifier(cadeau and cadeau["apres"] and cadeau["prevenu"] and not cadeau["valide"],
             f"le cadeau lancé par erreur : la créature prévient, les trésors reviennent, l'étape attend {cadeau}")
    verifier(any(c.startswith("sudo") for _l, _s, c, _code, _lu in journal), "elle a tenté sudo (refusé, expliqué)")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 18, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
C.arreter_fictifs()
port.eteindre_phare()
SH.fermer()
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
