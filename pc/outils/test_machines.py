"""La Salle des Machines (phase 5, docs/programme.md § 7.3 et § 7.13 M5 bis), sur PC.

    python3 pc/outils/test_machines.py          (crée son propre HOME temporaire)

  1. la spécification pure : vecteurs communs à jour (donnees/machines/vecteurs.json, mêmes résultats en Kotlin) ;
     les réponses du jeu = la vraie machine (nproc, free -h, /proc/cpuinfo, uname -r) ; les interrupteurs = od ;
     les unités = numfmt ; chaque besoin de « Monte ta machine » a une solution, et les pièges sont bien vus ;
  2. l'arbre du Carrefour : fermée tant que les niveaux 0 à 3 ne sont pas finis, puis ouverte et annoncée une fois
     (une nouvelle à la fois) ; meublée (plan, photo de 1 Mio, script du conteneur jetable, collection, ferme) ;
  3. la traversée sm0 → sm10 comme un enfant (vraies commandes dans bash, commandes du jeu `machines …`) : cœurs et
     mémoire lus puis donnés, l'ordinateur ouvert qui s'allume, Monte ta machine niveau 1, hexadécimal, interrupteurs,
     unités, le réveil, l'orchestre, la maison dans la maison, le conteneur et le disque virtuel (outils absents :
     raconté), la ferme, la sauvegarde 3-2-1 et la panne (dans le terrain), l'épreuve réussie au premier démarrage
     (variante rare), la carte mère miniature et le titre ;
  4. les indices (sudo, « ? » recopié, mauvais nombre de cœurs, mauvais interrupteurs, tar à l'envers) et la garde ;
  5. la vue déployée : l'ordinateur ouvert de `nproc`, `free -h`… ;
  6. sécurité : rien hors du terrain (sauf ~/.terminagotchi), jamais de sudo, aucune donnée personnelle (ni le prénom
     tapé, ni le nom de la machine, ni le nom d'utilisateur) dans le carnet ou la sauvegarde ; 14 langues.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_mac_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, machines as M, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
XXD = (f"#!{sys.executable}\nimport sys\na = [x for x in sys.argv[1:] if not x.startswith('-')]\n"
       "d = open(a[0], 'rb').read() if a else sys.stdin.buffer.read()\n"
       "if '-r' in sys.argv:\n    sys.stdout.buffer.write(bytes.fromhex(d.decode().replace(chr(10), '').replace(' ', '')))\n"
       "elif '-b' in sys.argv:\n"
       "    for i in range(0, len(d), 6):\n"
       "        x = d[i:i + 6]; s = ' '.join(format(b, '08b') for b in x)\n"
       "        print('%08x: ' % i + s.ljust(54) + ' ' + ''.join(chr(b) if 32 <= b < 127 else '.' for b in x))\n"
       "else:\n    [print('%08x: ' % i + d[i:i + 16].hex(' ', 2)) for i in range(0, len(d), 16)]\n")
if not shutil.which("xxd"):            # une doublure de xxd (-r -p, -b et l'affichage simple) si l'outil manque
    (DOUBLURES / "xxd").write_text(XXD)
    (DOUBLURES / "xxd").chmod(0o755)
QEMU = not shutil.which("qemu-img")
if QEMU:                               # une doublure de qemu-img (create, info) pour traverser M5 bis ici
    (DOUBLURES / "qemu-img").write_text(
        f"#!{sys.executable}\nimport sys, os\na = sys.argv[1:]\n"
        "if a[0] == 'create':\n    f = a[-2]\n    open(f, 'wb').write(b'QFI\\xfb' + bytes(196604))\n"
        "    print(f\"Formatting '{f}', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=1073741824 lazy_refcounts=off refcount_bits=16\")\n"
        "elif a[0] == 'info':\n    print('image: ' + a[-1]); print('file format: qcow2'); print('virtual size: 1 GiB (1073741824 bytes)')\n"
        "    print('disk size: 196 KiB')\nelse:\n    sys.exit(1)\n")
    (DOUBLURES / "qemu-img").chmod(0o755)
(DOUBLURES / "machines").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                    "from tg import machines; machines.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "machines").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8")


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
                       errors="replace", timeout=400, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
        lignes = lignes[:-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)
    return st, "\n".join(lignes) + r.stderr


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


def solution(besoin):
    """Une machine qui répond au besoin (cherchée comme un enfant patient : toutes les combinaisons)."""
    import itertools
    cat = M.donnees()["catalogue"]
    for combo in itertools.product(*[[x["id"] for x in cat[c]] for c in M.donnees()["categories"]]):
        if not M.montage(list(combo), besoin)["problemes"]:
            return list(combo)
    return None


langue.definir("fr")
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_machines.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/machines/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
verifier(str(M.coeurs()) == bash("nproc").strip() and M.coeurs() in M.coeurs_justes(),
         f"les cœurs du jeu = nproc ({M.coeurs()}, justes : {sorted(M.coeurs_justes())})")
verifier(M.processeurs_cpuinfo() == int(bash("grep -c ^processor /proc/cpuinfo").strip() or 0), "/proc/cpuinfo compté comme grep -c")
total = (bash("free -h | awk '/^Mem:/ {print $2}'").strip() or "?")
verifier(M.memoire_ok(total, M.memoire_kio()) and not M.memoire_ok("9999", M.memoire_kio()),
         f"free -h dit {total} : le jeu l'accepte (et refuse 9999)")
verifier(M.noyau() == bash("uname -r").strip(), "le noyau du jeu = uname -r")
od = bash("printf 'Zoé' | od -An -tx1").split()
verifier([format(int(x, 16), "08b") for x in od] == [b for _c, bb in M.interrupteurs("Zoé") for b in bb],
         "les interrupteurs = les vrais octets (od) ; « é » prend deux octets")
if shutil.which("numfmt"):
    verifier(bash("numfmt --to=iec 1048576").strip() == "1.0M" and abs(M.unites(1048576)["mio"] - 1) < 1e-9 and
             abs(M.unites(1048576)["mo"] - 1.048576) < 1e-9, "1 Mio = 1 048 576 octets = 1,05 Mo (numfmt d'accord)")
sols = {b: solution(b) for b in M.donnees()["besoins"]}
verifier(all(sols.values()), f"chaque besoin a au moins une machine possible {sols}")
verifier(set(M.montage(["P2", "C2", "M3", "S1", "G0", "A1"], "ecole")["problemes"]) == {"prise"} and
         "memoire" in M.montage(["P1", "C1", "M3", "S1", "G0", "A1"], "ecole")["problemes"] and
         "alimentation" in M.montage(["P3", "C2", "M3", "S1", "G2", "A1"], "ecole")["problemes"] and
         "budget" in M.montage(["P3", "C2", "M4", "S2", "G2", "A3"], "jouer")["problemes"],
         "les pièges : prise, type de mémoire, alimentation trop faible, budget")
gr = "7:42"
verifier(sorted(M.reveil_reponse(gr)) == list("ABCDE") and len({x for _n, _i, x in M.orchestre(gr)}) == 5,
         "le réveil et l'orchestre : des permutations de A à E")
verifier(re.fullmatch(r"TG\{(jouer|dessiner|serveur|robot)-[0-9a-f]{8}\}", M.drapeau(gr)) is not None, f"drapeau {M.drapeau(gr)}")
verifier(M.boite_de("flags\t\t: fpu hypervisor sse", "0::/", True)["vm"] and M.boite_de("", "0::/docker/abc")["conteneur"] == "conteneur",
         "la maison dans la maison : hypervisor, docker")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "machinerie"), "fermée au début")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    h["chap"] = "bibliotheque"
    h.setdefault("mondes_annonces", []).extend(["port", "crypte"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "machinerie"), f"niveaux 0 à 3 finis : la Salle s'ouvre (il manquait {M.manque(core.load())})")
verifier("machinerie" in st["histoire"].get("mondes_annonces", []), "annoncée une fois")
D = T / "machines"
verifier((D / "plan_de_la_salle.txt").is_file() and (D / "photo.bin").stat().st_size == 1048576 and
         (D / "conteneur_jetable.sh").is_file() and (D / "ferme" / "loin").is_dir() and (D / "collection.txt").is_file(),
         "la Salle est meublée (plan, photo de 1 Mio, script du conteneur, ferme, collection)")
s = bash("sh conteneur_jetable.sh", str(D))
verifier(("podman" in s) and "alpine" not in bash("cat carnet_de_la_salle.txt", str(D)) or shutil.which("podman"),
         "le script du conteneur jetable explique et ne télécharge rien sans « lancer »")

print("3. La traversée de la Salle, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/machines")
verifier(lecon(st) == ("sm0", 1), f"entrer dans la Salle choisit le monde : {lecon(st)}")
gr = M._graine(st)
nom = st.get("name", "")
sorties = {}
k = M.memoire_kio()
PARCOURS = [
    "ls", "cat plan_de_la_salle.txt",
    "nproc", f"machines coeurs {M.coeurs() + 7}", f"machines coeurs {M.coeurs()}", "free -h",
    f"machines memoire {k / 1024 ** 2:.1f}", "lsblk", "machines ouvre",
    "head -5 /proc/cpuinfo", "grep -c ^processor /proc/cpuinfo", "lspci", "lsusb", "machines monte 1",
    "machines monte 1 P2 C2 M3 S1 G0 A1", "machines monte 1 P1 C1 M1 S1 G0 A1",
    "printf '%x\\n' 65", "echo -n A | xxd -b", "machines interrupteurs Zoé", "machines allume 11111111",
    lambda: "machines allume " + M.bits(ord(M.lettre_defi(nom))), "wc -c photo.bin", "machines unites",
    "uname -r", "uptime", "dmesg | head -5", "systemd-analyze", "machines reveil", "machines reveil A B C D E",
    lambda: "machines reveil " + " ".join(M.reveil_reponse(gr)),
    "uname -srmo", "cat /etc/os-release", "ps", "which ls", "lsmod | head -5", "machines orchestre",
    lambda: "machines orchestre " + " ".join(l for _n, _i, l in M.orchestre(gr)), "machines licences",
    "cat /proc/1/cgroup", "machines boite", "machines range", lambda: "machines range " + " ".join(r for _n, _i, r in M.range_boites(gr)),
    "machines adulte", "command -v podman qemu-img virsh", "cat conteneur_jetable.sh", "sh conteneur_jetable.sh",
    "sh conteneur_jetable.sh lancer", "machines conteneur", "qemu-img create -f qcow2 disque_virtuel.qcow2 1G",
    "qemu-img info disque_virtuel.qcow2", "virsh -r -c qemu:///system list --all", "machines vm",
    "df -h .", "du -sh .", "machines ferme", "machines energie",
    "ls ferme", "tar czf sauvegarde.tar.gz collection.txt", "sha256sum sauvegarde.tar.gz > sauvegarde.sha256",
    "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/", "machines panne",
    "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/", "machines panne", "cd ferme/loin", "sha256sum -c sauvegarde.sha256",
    "tar xzf sauvegarde.tar.gz -C ../..", "cd ../..",
    "machines monte", lambda: "machines monte " + " ".join(solution(M.besoin_epreuve(gr))), "machines demarre",
    lambda: "machines drapeau " + M.drapeau(gr),
]
vus = []
for c in PARCOURS:
    if callable(c):
        c = c()
    avant = lecon(st)
    st, s = tape(c)
    sorties[c] = s
    vus.append((avant, c, lecon(st)))
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:100]!r}")
    if histoire.fini(st, "machinerie"):
        break
if not histoire.fini(st, "machinerie"):
    for a, c, b in vus[-6:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "machinerie"), f"la Salle est traversée jusqu'au bout (sm0 → sm10) {lecon(st)}")
verifier(sorties.get("printf '%x\\n' 65", "").strip() == "41", "printf %x 65 : 41")
verifier("01000001" in sorties.get("echo -n A | xxd -b", ""), "xxd -b : 01000001")
verifier(sorties.get("wc -c photo.bin", "").strip() == "1048576 photo.bin", "la photo : 1 048 576 octets")
verifier("✔" in sorties.get(f"machines coeurs {M.coeurs()}", "") and "✖" in sorties.get(f"machines coeurs {M.coeurs() + 7}", ""),
         "machines coeurs : le bon nombre accepté, un faux refusé")
o = ANSI.sub("", sorties.get("machines ouvre", ""))
verifier("●" in o and "processeur" in o and "mémoire vive" in o and "stockage" in o, "l'ordinateur ouvert : processeur, mémoire, stockage allumés")
verifier("prise" in ANSI.sub("", sorties.get("machines monte 1 P2 C2 M3 S1 G0 A1", "")), "niveau 1 : la prise qui ne va pas est expliquée")
verifier("Zoé" not in M.carnet() and "3 lettres" in M.carnet(), "le prénom tapé reste sur l'écran (le carnet ne le garde pas)")
verifier("sauvegarde.tar.gz: OK" in sorties.get("sha256sum -c sauvegarde.sha256", ""), "la copie lointaine est intacte (OK)")
verifier("perdu" in M.carnet() and "(ok)" in M.carnet().split("[panne]")[-1], "la panne : d'abord tout serait perdu, puis la ferme est sauvée")
verifier((D / "collection.txt").read_text(encoding="utf-8").startswith(M.MARQUE), "la collection est restaurée")
r_ = recompenses.r_(st)
verifier("machines.premier_demarrage" in r_["exploits"], "Monte ta machine réussi au premier démarrage : la variante rare")
verifier("carte_mere_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "architecte_des_machines",
         "récompenses : la carte mère miniature et le titre d'Architecte des Machines")
verifier(not recompenses.reservee(st, {"id": "chaudrogre"}, "mecanique") and recompenses.reservee({}, {"id": "chaudrogre"}, "mecanique"),
         "chaudrogre:mecanique n'apparaît qu'après l'exploit de la Salle")

print("4. Les indices et la garde")
pas = {s_["cmd"]: s_ for l_ in M.LECONS.values() for s_ in l_["steps"]}
verifier(M.indice(pas["machines coeurs ?"], [("sudo dmesg", None)]) == langue.t("ma.indice.sudo"), "sudo : jamais ici")
verifier(M.indice(pas["machines coeurs ?"], [("machines coeurs ?", None)]) == langue.t("ma.indice.trou"), "« ? » recopié : un trou à remplir")
M.noter("coeurs", "99 (faux)")
verifier(M.indice(pas["machines coeurs ?"], [("machines coeurs 99", None)]) == langue.t("ma.indice.coeurs"), "mauvais nombre de cœurs")
M.noter("allume", "P (faux)")
verifier(M.indice(pas["machines allume ?"], [("machines allume 00000000", None)]) == langue.t("ma.indice.allume"), "mauvais interrupteurs")
verifier(M.indice(pas["tar czf sauvegarde.tar.gz collection.txt"], [("tar czf collection.txt sauvegarde.tar.gz", None)])
         == langue.t("ma.indice.tar_sens"), "tar à l'envers : l'ordre expliqué")
s0 = core.load()
verifier(M.surveiller(s0, ["sudo dmesg"]) and not M.surveiller(s0, ["sudo dmesg"]), "hors leçon : sudo sur le matériel, la créature prévient (une fois)")

print("5. La vue déployée : l'ordinateur ouvert")
x = deploie.pieces("nproc && free -h | head -2")
verifier([y["pieces"] for y in x] == [["processeur"], ["memoire"]], f"nproc → processeur, free → mémoire ({x})")
txt = ANSI.sub("", "\n".join(deploie.ecran("lsblk", deploie.blocs("lsblk"), 1, None, 0.9, 100)))
verifier("stockage s'allume" in txt and "▤" in txt, "la vue déployée dessine l'ordinateur ouvert")
out = io.StringIO()
M.commande(["ouvre"], out)
verifier("1 processeur" in ANSI.sub("", out.getvalue()), "machines ouvre dessine l'ordinateur et sa légende")
from tg import compagnon  # noqa: E402
verifier(any("machines='tg machines'" in b or "function machines" in b for b in compagnon._blocs().values()),
         "tg installer pose l'alias machines='tg machines'")

print("6. Sécurité et langues")
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in M.LECONS for s in M.LECONS[lid]["steps"])
verifier(not re.search(r"https?://", cmds) and "sudo" not in cmds and "virt-install" not in cmds,
         "aucune adresse réseau, aucun sudo, aucun virt-install dans les leçons")
import getpass  # noqa: E402
prive = [x for x in (os.uname().nodename, getpass.getuser()) if len(x) > 2]
etat = json.dumps(core.load().get("machinerie", {}), ensure_ascii=False)
verifier(not any(p in M.carnet() or p in etat for p in prive), "ni le nom de la machine ni le nom d'utilisateur dans le carnet ou la sauvegarde")
fr = langue._charger("fr")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k_ for lid in M.LECONS for s in M.LECONS[lid]["steps"] for k_ in (s["dit"], s["bravo"]) if isinstance(k_, str) and k_ not in dct]
    m += [k_ for k_ in ("hist.machinerie.titre", "hist.machinerie.debut", "hist.machinerie.fin", "ma.ouvert.dit", "dep.piece") if k_ not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes de la Salle existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
