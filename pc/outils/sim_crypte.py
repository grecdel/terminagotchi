"""Trois enfants traversent la Crypte des Codes (phase 5, cr0 → cr14), dans un VRAI shell resté ouvert —
docs/simulations/rapport_crypte.md.

    python3 pc/outils/sim_crypte.py            (les trois, chacun dans son propre HOME temporaire)
    python3 pc/outils/sim_crypte.py lea        (un seul : lea, ines ou hugo)

Comme sim_citadelle.py : le shell est pc/tg/coquille.py, l'enfant ne lit que la commande montrée et ce que le jeu
écrit dans SON terminal. La Crypte est ouverte d'avance (niveaux 0 à 4 du tronc commun finis).
  - Léa, 7 ans : se trompe d'abord (une majuscule, gpg SANS --homedir vu dans un tuto, un « sudo », `>` au lieu de
    `>>` dans le bloc, une autre clé que l'exemple, une mauvaise roue, un biome au hasard), recopie « ? » une fois ;
    puis lit et corrige.
  - Inès, 12 ans : recopie la commande verte telle quelle (« ? » compris) puis lit l'écran pour remplir les trous.
  - Hugo, 15 ans : ses variantes (`printf a | sha256sum`, `base64 --decode`, `cat … | xxd -r -p`, `fold -w1`,
    `bash dictionnaire.sh`, `xxd parchemin.enc | head -1`, `sha256sum --check`, `cut -d' ' -f1`, `bash mineur.sh 1`…).
Pour le quiz, l'enfant répond, lit les ✔, corrige les autres ; pour la roue, il compte les lettres et calcule le
décalage depuis « e » ; pour le dé, il calcule avec echo $(( … )) ; pour le tricheur, il lit les empreintes.
Vérifie : la Crypte finie (le carnet de bord : crypte.b6), la chaîne réparée SANS indice donne crypte.chaine (et pas
avec un indice), aucune étape validée par une commande qui a échoué, chaque faute de Léa reçoit une explication, les
variantes justes de Hugo acceptées, aucun gpg-agent ne reste, le vrai trousseau (~/.gnupg) jamais créé, rien hors du
terrain, seulement des clés d'exemple. Code de sortie 1 en cas d'échec.
"""
import builtins
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve()
RACINE = ICI.parents[2]
PERSONAS = ("ines", "lea", "hugo")

if len(sys.argv) < 2 or sys.argv[1] not in PERSONAS:
    ko = 0
    for p in PERSONAS:
        r = subprocess.run([sys.executable, str(ICI), p] + sys.argv[1:], text=True)
        ko += r.returncode != 0
    print(f"\nCrypte : {len(PERSONAS) - ko}/{len(PERSONAS)} enfants au bout")
    sys.exit(1 if ko else 0)

QUI = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_sim_cry_{QUI}_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ.pop("GNUPGHOME", None)
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, compagnon, core, crypte as K, explo, histoire, langue, recompenses  # noqa: E402
from tg.coquille import Coquille  # noqa: E402
from tg.plateforme import HOMO, NBSP  # noqa: E402

HOME = Path.home()
(HOME / ".bash_history").touch()
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
# `crypte …` : l'alias crypte='tg crypte' posé par tg installer (le jeu le connaît comme commande, core.BUILTINS)
(DOUBLURES / "crypte").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                  "from tg import crypte; crypte.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "sudo").write_text("#!/bin/sh\necho 'sudo: (simulation) refusé' >&2\nexit 1\n")
if not shutil.which("xxd"):
    (DOUBLURES / "xxd").write_text(
        f"#!{sys.executable}\nimport sys\na = [x for x in sys.argv[1:] if not x.startswith('-')]\n"
        "d = open(a[0], 'rb').read() if a else sys.stdin.buffer.read()\n"
        "if '-r' in sys.argv:\n    sys.stdout.buffer.write(bytes.fromhex(d.decode().replace(chr(10), '').replace(' ', '')))\n"
        "else:\n    [print('%08x: ' % i + d[i:i + 16].hex(' ', 2)) for i in range(0, len(d), 16)]\n")
for f in DOUBLURES.iterdir():
    f.chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"

builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
explo.tick = lambda *a, **k: None
langue.definir("fr")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = "bibliotheque"
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
journal = []          # (leçon, étape, commande, code, lu) : la partie entière, pour le rapport
memoire = {}


def tape(cmd):
    etat["sortie"], etat["code"], d = SH.lancer(cmd, delai=60)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    lus = []
    st = app.etape(spontane=False, defis=False, cwd=d, statut=etat["code"],
                   avant_save=lambda s: lus.extend(compagnon.annonces(s)))
    etat["terminal"] = [propre(x) for x in lus]
    les, _ = histoire.lecon_courante(st)
    journal.append(((les or {}).get("id"), st["step"], cmd, etat["code"], " ".join(etat["terminal"])[:160]))
    memoire[cmd] = propre(etat["sortie"])
    memoire[cmd.split()[0] if cmd.split() else ""] = propre(etat["sortie"])
    return st


def montree(st, step):
    texte = propre(compagnon.commande_montree(st, step))
    parts = [p.strip() for p in re.split(r"\s+puis\s+", texte)]
    return [p.removesuffix("(q pour sortir)").strip() for p in parts if p]


def biome_different():
    """Le biome dont l'empreinte n'est pas celle de la majorité (lu dans la sortie de sha256sum copies/*)."""
    for cle, s in list(memoire.items())[::-1]:
        if cle.startswith("sha256sum") and "copies/" in s:
            paires = re.findall(r"^([0-9a-f]{64})\s+copies/(\w+)/", s, re.M)
            comptes = {}
            for h, _b in paires:
                comptes[h] = comptes.get(h, 0) + 1
            return next((b for h, b in paires if comptes[h] == 1), None)
    return None


def resoudre(cmd, st):
    """Les trous « ? » remplis en lisant l'écran (jamais en trichant)."""
    if cmd == "crypte roue ?":
        s = next((v for k, v in list(memoire.items())[::-1] if "mystere" in k and "uniq" in k), "")
        m = re.search(r"^\s*\d+\s+([a-z])\s*$", s, re.M)
        if not m:
            st = tape("grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3")
            m = re.search(r"^\s*\d+\s+([a-z])\s*$", propre(etat["sortie"]), re.M)
        k = (ord(m.group(1)) - ord("e")) % 26
        return st, f"crypte roue {k}"
    if cmd == "crypte de ?":
        if "crypte de" not in memoire:
            st = tape("crypte de")
        tirages = re.findall(r"^\s+((?:\d+\s+)+)\?\s*$", memoire.get("crypte de", ""), re.M)
        x = tirages[0].split()[-1] if tirages else "0"
        st = tape(f"echo $(( (5*{x}+3) % 8 ))")
        return st, f"crypte de {propre(etat['sortie']).strip()}"
    if cmd.startswith("diff copies/feu/registre.txt copies/?"):
        if not biome_different():
            st = tape("sha256sum copies/*/registre.txt")
        return st, cmd.replace("?", biome_different() or "eau")
    if cmd == "crypte consensus ?":
        return st, f"crypte consensus {biome_different() or 'eau'}"
    return st, cmd


def quiz(st):
    """Le quiz : répondre, lire les ✔, changer les autres (v → f → s), jusqu'à six sur six."""
    rep = ["v"] * 6 if QUI != "hugo" else [r for _n, _i, r in K.quiz(K._graine(st))]
    for _ in range(4):
        st = tape("crypte quiz " + " ".join(rep))
        if K.dans_carnet("quiz"):
            break
        bons = {int(n) for n in re.findall(r"✔\s+(\d)\.", propre(etat["sortie"]))}
        rep = [r if i + 1 in bons else {"v": "f", "f": "s", "s": "v"}[r] for i, r in enumerate(rep)]
    return st


def faute(cmd, st):
    """La faute de Léa (7 ans) la première fois qu'elle voit l'étape, ou None."""
    if cmd.startswith("gpg --homedir .trousseau --batch --passphrase"):
        return f"gpg --quick-gen-key {K.MOI}"              # vu dans un tuto : SANS --homedir (le jeu doit l'arrêter)
    if cmd == "echo triche >> chaine/bloc_1.txt":
        return "echo triche > chaine/bloc_1.txt"           # un seul > : le bloc est écrasé
    if cmd == "cp archives/bloc_1.txt chaine/":
        return "sudo cp archives/bloc_1.txt chaine/"
    if cmd.startswith("openssl enc -aes-256-cbc"):
        return cmd.replace(K.CLE, "1234")
    if cmd == "crypte roue ?":
        return cmd                                          # recopie le « ? »
    if cmd == "crypte consensus ?":
        return "crypte consensus roche" if K.tricheur(K._graine(st)) != "roche" else "crypte consensus eau"
    if re.match(r"^(cat|ls|grep)\b", cmd):
        return cmd[0].upper() + cmd[1:]
    return None


def variante(cmd):
    regles = [
        (r"^echo bonjour \| base64$", "printf 'bonjour\\n' | base64"), (r"^base64 -d (\S+)$", r"base64 --decode \1"),
        (r"^xxd -r -p (\S+)$", r"cat \1 | xxd -r -p"), (r"^echo -n a \| sha256sum$", "printf a | sha256sum"),
        (r"^echo -n b \| sha256sum$", "printf b | sha256sum"),
        (r"^grep -o '\[a-z\]' grimoire/mystere\.txt \| sort \| uniq -c \| sort -rn \| head -3$",
         "fold -w1 grimoire/mystere.txt | grep '[a-z]' | sort | uniq -c | sort -rn | head -n 3"),
        (r"^sha256sum -c (\S+)$", r"sha256sum --check \1"), (r"^sh dictionnaire\.sh$", "bash dictionnaire.sh"),
        (r"^head -c 8 parchemin\.enc$", "xxd parchemin.enc | head -n 1"), (r"^cat parchemin\.txt$", "less parchemin.txt"),
        (r"^echo \$\(\(5\*\*6 % 23\)\)$", "echo $((5*5*5*5*5*5 % 23))"),
        (r"^head -c 16 /dev/urandom \| xxd$", "head -c 16 /dev/urandom | od -An -tx1"),
        (r"^sha256sum chaine/bloc_0\.txt$", "sha256sum chaine/bloc_0.txt chaine/bloc_1.txt"),
        (r"^sh verifie_chaine\.sh$", "bash verifie_chaine.sh"), (r"^cat chaine/bloc_1\.txt$", "head chaine/bloc_1.txt"),
        (r"^sha256sum copies/\*/registre\.txt \| cut -c1-64 \| sort \| uniq -c$",
         "sha256sum copies/*/registre.txt | awk '{print $1}' | sort | uniq -c"),
        (r"^sh mineur\.sh 2$", "bash mineur.sh 2"), (r"^time sh mineur\.sh 3$", "time bash mineur.sh 3"),
        (r"^grep -h donnees chaine/bloc_\*\.txt$", "cat chaine/bloc_*.txt"),
        (r"^sh verifie_chaine\.sh carnet_de_bord$", "bash verifie_chaine.sh carnet_de_bord"),
    ]
    for a, b in regles:
        if re.match(a, cmd):
            return re.sub(a, lambda m: m.expand(b) if re.search(r"\\\d", b) else b, cmd)
    return None


fausses, sans_explication, variantes_ok, variantes_refusees = [], [], [], []
tentes = set()
st = tape("ls")
assert histoire.ouvert(st, "crypte"), "la Crypte devrait être ouverte (niveaux 0 à 4 finis)"
st = tape("cd ~/terrain_terminagotchi/crypte")
for _ in range(400):
    if histoire.fini(st, "crypte"):
        break
    les, _e = histoire.lecon_courante(st)
    if not les or not les["id"].startswith("cr"):
        st = tape("cd ~/terrain_terminagotchi/crypte")
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
        if QUI == "ines" and "?" in derniere.split() and not derniere.startswith("crypte quiz"):
            essais.append(derniere)                                # recopie les « ? »
    for essai in essais:
        for c in a_taper[:-1]:
            st = tape(c)
        st = tape(essai)
        les2, _ = histoire.lecon_courante(st)
        apres = (les2["id"], st["step"]) if les2 else None
        if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
            fausses.append((avant, essai, etat["code"]))
        if QUI == "hugo":
            (variantes_ok if apres != avant else variantes_refusees).append(essai)
        elif apres == avant and not any(x.strip() for x in etat["terminal"]):
            sans_explication.append((avant, essai, etat["sortie"][:60]))
        if essai == "echo triche > chaine/bloc_1.txt" and apres != avant:
            break                                                  # écrasé, mais la chaîne est bien brisée : on continue
        if apres != avant:
            break
    les2, _ = histoire.lecon_courante(st)
    if ((les2["id"], st["step"]) if les2 else None) != avant:
        continue
    for c in a_taper[:-1]:
        st = tape(c)
    if derniere.startswith("crypte quiz ?"):
        st = quiz(st)
    else:
        st, derniere = resoudre(derniere, st)
        st = tape(derniere)
    les2, _ = histoire.lecon_courante(st)
    apres = (les2["id"], st["step"]) if les2 else None
    if apres != avant and etat["code"] not in (0, None) and not any(step.get(k) for k in ("echoue", "absent_ok", "tout_code")):
        fausses.append((avant, derniere, etat["code"]))

verifier(histoire.fini(st, "crypte"), f"la Crypte traversée, cr0 → cr14 ({len(journal)} lignes tapées)")
ex = (st.get("recompenses") or {}).get("exploits") or {}
verifier("crypte.b6" in ex, f"le carnet de bord vérifié : la légendaire (crypte.b6) {sorted(ex)}")
indice_b2 = "indice:cr10" in K.c_(st)["faits"]
verifier(("crypte.chaine" in ex) == (not indice_b2),
         f"la variante rare (crypte.chaine) seulement si la chaîne a été réparée SANS indice (indice reçu : {indice_b2})")
verifier(not fausses, f"aucune étape validée par une commande qui a échoué {fausses[:4]}")
K.tuer_agents()
r = subprocess.run(["bash", "-c", f"ps -eo args | grep -c '^gpg-agent.*{core.TERRAIN}'"], capture_output=True, text=True)
verifier(r.stdout.strip() == "0", "aucun gpg-agent du terrain ne reste en vie")
if QUI == "lea":                 # Léa a tapé gpg SANS --homedir : c'est SA commande (le jeu ne peut pas l'empêcher), il prévient
    lu = [lu_ for _l, _s, c, _code, lu_ in journal if c.startswith("gpg --quick-gen-key")]
    verifier(lu and "--homedir" in lu[0], f"gpg tapé sans --homedir : la créature prévient tout de suite ({lu[:1]})")
else:
    verifier(not (HOME / ".gnupg").exists(), "le vrai trousseau (~/.gnupg) n'a jamais été créé")
cles = set()
for _l, _s, c, _code, _lu in journal:
    cles |= set(re.findall(r"pass:(\S+)", c))
verifier(cles <= {K.CLE, "1234"}, f"seulement des clés d'exemple tapées {sorted(cles)}")
if QUI == "lea":
    verifier(not sans_explication, f"chaque faute reçoit une explication {sans_explication[:4]}")
    verifier(any(c.startswith("gpg --quick-gen-key") for _l, _s, c, _code, _lu in journal), "elle a tapé gpg sans --homedir (arrêté, expliqué)")
if QUI == "hugo":
    verifier(len(variantes_ok) >= 15, f"ses variantes justes sont acceptées ({len(variantes_ok)})")
    print(f"    variantes refusées : {variantes_refusees}")
if os.environ.get("TG_DEBUG"):
    for j in journal:
        print("    ·", j)
SH.fermer()
shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"[{QUI}] {ok} réussis, {ko} échoués, {len(journal)} lignes, {sum(1 for j in journal if j[4].strip())} lectures   (HOME={HOME})")
sys.exit(1 if ko else 0)
