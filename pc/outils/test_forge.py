"""La Forge (phase 5, docs/programme.md § 2.10 et § 7.13 « Ton site web », « L'atelier multimédia »), sur PC.

    python3 pc/outils/test_forge.py          (crée son propre HOME temporaire, hors ligne)

  1. la spécification pure : vecteurs communs à jour (donnees/forge/vecteurs.json, mêmes résultats en Kotlin) ; la
     recette de la cabane ; la question des tours ; la photo d'exemple (métadonnées INVENTÉES, lues comme par un vrai
     lecteur, retirées sans abîmer l'image) ; les GIF et les WAV ; les variantes réservées EXISTENT (Machine ou Feu),
     ni gardiens ni réservées ailleurs ;
  2. l'arbre du Carrefour : fermée tant que le niveau 4 n'est pas fait, puis ouverte et annoncée une fois ; meublée ;
  3. la traversée fo0 → fo7 comme un enfant (vraies commandes dans bash, hors ligne), avec ses erreurs : les exploits
     « premier coup » et « sans indice », le jeu posé sur la carte, le site servi sur 127.0.0.1 puis éteint ;
  4. les indices ; 5. la vue déployée (le parchemin, le manège, la lanterne) ;
  6. sécurité : rien hors du terrain, aucun réseau sauf 127.0.0.1, forge exif / nettoie refusent tout fichier hors du
     terrain, le serveur n'écoute jamais tout le réseau sans que le jeu le dise.
"""
import io
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_forge_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"                 # hors ligne
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, maison, recompenses, forge as FO  # noqa: E402
from tg import bestiaire as B, guide  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
JOURNAL = DOUBLURES / "appels.txt"
for nom, corps in (("forge", "from tg import forge; sys.exit(forge.commande(sys.argv[1:]) or 0)"),
                   ("tg", "from tg import app; sys.argv = ['tg'] + sys.argv[1:]; app._main()")):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                 f"{corps}\" \"$@\"\n")
    (DOUBLURES / nom).chmod(0o755)
for nom in ("sudo", "wget"):
    (DOUBLURES / nom).write_text(f"#!/bin/sh\necho \"{nom} $*\" >> {JOURNAL}\necho '{nom}: (test) refusé' >&2\nexit 1\n")
    (DOUBLURES / nom).chmod(0o755)
VRAI_CURL = shutil.which("curl")
if VRAI_CURL:                                            # curl : seulement vers 127.0.0.1 / localhost (sinon noté)
    (DOUBLURES / "curl").write_text("#!/bin/sh\ncase \"$*\" in *localhost*|*127.0.0.1*) exec " + VRAI_CURL + " \"$@\";; esac\n"
                                    f"echo \"curl $*\" >> {JOURNAL}\nexit 7\n")
    (DOUBLURES / "curl").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C")
PYTHON = shutil.which("python3")
PIDS = DOUBLURES / "pid_serveur"


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def bash(cmd, cwd=None):
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd or terminal[0], capture_output=True, text=True, errors="replace",
                       timeout=60, env=ENV, stdin=subprocess.DEVNULL)
    return r.stdout


def tape(cmd, vrai=None):
    """L'enfant tape cmd (gardée dans l'historique) ; vrai : ce que le terminal exécute vraiment (Ctrl+C, &…)."""
    r = subprocess.run(["bash", "-c", (vrai or cmd) + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True,
                       text=True, errors="replace", timeout=180, env=ENV, stdin=subprocess.DEVNULL)
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


langue.definir("fr")
D = FO.donnees()
print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_forge.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/forge/vecteurs.json)" + (" " + r.stdout[-300:] if r.returncode else ""))
verifier(FO.recette_complete("#!/bin/sh\nmkdir -p cabane\ntouch cabane/porte.txt cabane/toit.txt\n")
         and not FO.recette_complete("mkdir -p cabane\ntouch cabane/porte.txt\n")
         and FO.recette_etat("#!/usr/bin/env bash\nmkdir cabane\n") == {"shebang": True, "mkdir": True, "touch": False},
         "la recette de la cabane : la ligne magique, le mkdir, le touch")
a, z = FO.tours_question("1:1793534400")
verifier(2 <= a <= 5 and a + 4 <= z <= a + 9 and FO.tours_reponse(a, z) == int(bash(f"seq {a} {z} | wc -l").strip()),
         f"la question des tours : seq {a} {z} → {FO.tours_reponse(a, z)} tours (comme seq | wc -l)")
o = FO.photo_octets()
ex = dict(FO.exif_de(o))
verifier(ex.get("marque") == "Terminacam" and ex.get("modele") == "TC-7" and ex.get("lat", "").startswith("0°")
         and "inventees" in ex.get("description", ""), f"la photo d'exemple : des métadonnées INVENTÉES {ex}")
try:
    from PIL import Image
    im = Image.open(io.BytesIO(o))
    e_ = im.getexif()
    verifier(e_.get(271) == "Terminacam" and e_.get_ifd(0x8825).get(1) == "N" and im.size == (128, 96),
             "un vrai lecteur (Pillow) lit les mêmes métadonnées")
    im2 = Image.open(io.BytesIO(FO.sans_exif(o)))
    im2.load()
    verifier(not im2.getexif() and im2.size == (128, 96), "sans métadonnées, l'image se lit toujours (même taille)")
except ImportError:
    print("  · Pillow absent : la lecture par un autre outil est faite en CI (exiftool)")
verifier(not FO.a_exif(FO.sans_exif(o)) and FO.exif_de(FO.sans_exif(o)) == [] and FO.exif_de(b"pas une photo") is None,
         "forge nettoie retire tout ; un fichier qui n'est pas un JPEG est refusé")
tmp = Path(tempfile.mkdtemp())
if shutil.which("convert") or shutil.which("magick"):
    im_ = shutil.which("magick") or shutil.which("convert")
    bash(f"{im_} -size 4x4 xc:red a.png && {im_} -size 4x4 xc:blue b.png && {im_} -size 4x4 xc:lime c.png && "
         f"{im_} -delay 20 -loop 0 a.png b.png c.png anim.gif", tmp)
    verifier(FO.images_gif((tmp / "anim.gif").read_bytes()) == 3, "un GIF de 3 images : le jeu en compte 3")
verifier(FO.wav_ok(FO.fanfare_octets()) and len(FO.fanfare_octets()) > 40000, "fanfare.wav : un vrai fichier WAV (1 seconde)")
if shutil.which("ffprobe"):
    (tmp / "f.wav").write_bytes(FO.fanfare_octets())
    verifier(bash("ffprobe -v error -show_entries format=duration -of csv=p=0 f.wav", tmp).strip() == "1.000000",
             "ffprobe lit la fanfare : 1 seconde")
gardiens = set(recompenses.gardiens().values())
m = next(x for x in recompenses.mondes() if x["id"] == "forge")
autres = {v for x in recompenses.mondes() if x["id"] != "forge" for v in x.get("variantes_reservees", [])}
ok_var = True
for v in m["variantes_reservees"]:
    eid, vid = v.split(":")
    e = B.espece(eid)
    ok_var &= bool(e) and any(x["id"] == vid for x in e["variantes"]) and guide.type_de(e, vid) in ("machine", "feu") \
        and eid not in gardiens and v not in autres
verifier(ok_var and len(m["variantes_reservees"]) == 3, f"variantes réservées EXISTANTES, Machine ou Feu, ni gardiens ni déjà réservées : {m['variantes_reservees']}")
p_ = FO.port_libre()
s_ = socket.socket()
s_.bind(("127.0.0.1", p_))
s_.listen(1)
verifier(FO.port_libre() == p_ + 1 and p_ >= 1024, f"un port déjà pris : le jeu en propose un autre ({p_} → {p_ + 1})")
if Path("/proc/net/tcp").exists():
    s2 = socket.socket()
    s2.bind(("0.0.0.0", p_ + 5))
    s2.listen(1)
    verifier(FO.ecoute_partout(p_ + 5) and not FO.ecoute_partout(p_), "le jeu voit un serveur ouvert à TOUT le réseau (0.0.0.0)")
    s2.close()
s_.close()

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "forge"), f"fermée au début (il manque {FO.manque(st)})")


def ouvrir(s, chaps=("reveil", "nid", "bibliotheque")):
    h = histoire.h_(s)
    for c in chaps:
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"][:len(chaps) - 1]
    h["chap"] = chaps[-1]
    h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde",
                                                "observatoire", "donnees"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(lambda s: ouvrir(s, chaps=("reveil", "nid")))
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(not histoire.ouvert(st, "forge"), f"sans le niveau 3-4 (la bibliothèque) : toujours fermée (il manque {FO.manque(st)})")
core.modifier(ouvrir)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "forge"), "le niveau 4 fait : la Forge s'ouvre")
st, _ = tape("ls")
verifier("forge" in st["histoire"].get("mondes_annonces", []), "annoncée une fois (une nouvelle à la fois)")
FD = T / "forge"
verifier((FD / "enclume.txt").is_file() and (FD / FO.CARNET).is_file(), "la Forge est meublée (enclume, carnet)")
verifier(langue.t("hist.atelier.titre") == "La petite forge des Constructs" and langue.t("carte.piece.atelier") == "Petite forge",
         "§ 2.19 : l'ancien atelier des Constructs s'appelle « la petite forge » (son dossier reste atelier/)")

print("3. La traversée de la Forge, comme un enfant (avec ses erreurs)")
st, _ = tape("cd ~/terrain_terminagotchi/forge")
verifier(lecon(st) == ("fo0", 1), f"entrer dans la Forge choisit le monde : {lecon(st)}")
sorties = {}
SERVEUR = "python3 -m http.server 8642 --bind 127.0.0.1 --directory site &"
GIF = FO.GIF if shutil.which("magick") else FO.GIF.replace("magick", "convert", 1)
PARCOURS = [
    "ls", "cat enclume.txt",
    "forge recette", "echo '#!/bin/sh' > cabane.sh", "echo 'mkdir -p cabane' > cabane.sh",       # oups : > efface
    "echo '#!/bin/sh' > cabane.sh", "echo 'mkdir -p cabane' >> cabane.sh",
    "echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh", "cat cabane.sh", "sh cabane.sh", "./cabane.sh",
    "chmod +x cabane.sh", "./cabane.sh",
    "forge boites", "nom=Pixel", 'echo "Bonjour $nom"', "echo 'echo \"Bonjour $1 !\"' > salut.sh", "sh salut.sh",
    "sh salut.sh Léa", "echo 'echo \"Tu as donné $# prénoms.\"' >> salut.sh", "sh salut.sh Léa Tom Sam",
    "echo 'read prenom' > question.sh && echo 'echo \"Salut $prenom !\"' >> question.sh", "echo Léa | sh question.sh",
    "forge aiguillage", "ls fantome; echo $?", "forge code 0", "forge code 2",
    'if [ -f cabane/porte.txt ]; then echo "La porte est là !"; fi', 'for i in 1 2 3; do echo "Tour $i"; done',
    "for i in $(seq 1 10); do mkdir -p village/cabane_$i; done", "ls village | wc -l",
    "n=3; while [ $n -gt 0 ]; do echo $n; n=$((n - 1)); done", "forge tours 1",
    lambda: "forge tours {}".format(FO.tours_reponse(*FO.tours_question(FO._graine(core.load())))),
    "forge serpent", "python3 --version", 'python3 -c "print(2 + 3 * 4)"', "python3 -c \"for i in range(3): print('Pixel')\"",
    "cat serpent.py", "python3 serpent.py", "forge erreur ValueError", "forge erreur IndexError", "python3 serpent.py Pixel 3",
    "forge jeu", "cat mon_jeu/devinette.sh", "seq 1 10 | sh mon_jeu/devinette.sh", "seq 1 10 | sh mon_jeu/devinette.sh",
    "echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_$s; done' > donjon.sh", "sh donjon.sh",
    'echo "Le trésor est ici !" > mon_jeu/donjon/salle_3/tresor.txt', 'forge carte "La grotte de Pixel"',
    "tree mon_jeu" if shutil.which("tree") else "find mon_jeu",
    "forge site", "echo '<h1>Bienvenue chez Pixel</h1>' > site/index.html",
    "echo '<p>Ici vit ma créature. Elle adore les cabanes.</p>' >> site/index.html",
    "echo 'h1 { color: orange; }' > site/style.css", "echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html",
    "cat site/index.html",
    ("python3 -m http.server 8642 --directory site &", "python3 -m http.server 8642 --directory site >/dev/null 2>&1 & "
     f"echo $! > {PIDS}; sleep 1"),                                         # oups : sans --bind 127.0.0.1
    ("fg", f"kill $(cat {PIDS}); sleep 0.5"),                         # (Ctrl+C ; hors d'un vrai terminal : kill)
    (SERVEUR, f"{SERVEUR[:-2]} >/dev/null 2>&1 & echo $! > {PIDS}; sleep 1"),
    "curl localhost:8642",
    ("fg", f"kill $(cat {PIDS}); sleep 0.5"),                         # fg puis Ctrl+C
    "forge publier",
    "forge multimedia", "ls multimedia", GIF, "sox -n multimedia/la.wav synth 0.5 sine 440",
    "ffmpeg -i multimedia/fanfare.wav -ss 0.5 -t 0.5 multimedia/fin.wav",
    "exiftool multimedia/photo_exemple.jpg" if shutil.which("exiftool") else "tg forge exif multimedia/photo_exemple.jpg",
    "forge appareil Canon", "forge appareil Terminacam",
    "exiftool -all= -overwrite_original multimedia/photo_exemple.jpg" if shutil.which("exiftool")
    else "tg forge nettoie multimedia/photo_exemple.jpg",
    "forge bilan",
]
vus = []
indices = {}
for c in PARCOURS:
    vrai = None
    if callable(c):
        c = c()
    if isinstance(c, tuple):
        c, vrai = c
    avant = lecon(st)
    st, s = tape(c, vrai)
    sorties.setdefault(c, s)
    vus.append((avant, c, lecon(st), st.get("indice_lecon")))
    if st.get("indice_lecon"):
        indices.setdefault(c, st["indice_lecon"])
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} : {avant} → {lecon(st)} {ANSI.sub('', s)[:int(os.environ.get('TG_LARGE', '110'))]!r} {st.get('indice_lecon')}")
    if histoire.fini(st, "forge"):
        break
if not histoire.fini(st, "forge"):
    for a_, c, b, ind in vus[-8:]:
        print("     ", a_, c, "→", b, ind)
verifier(histoire.fini(st, "forge"), f"la Forge est traversée jusqu'au bout (fo0 → fo7) {lecon(st)}")
verifier((FD / "cabane" / "porte.txt").is_file() and os.access(FD / "cabane.sh", os.X_OK), "la cabane est bâtie par la recette (exécutable)")
verifier("forge.premier_coup" in recompenses.r_(st)["exploits"], "l'exploit « un programme qui marche du premier coup »")
verifier("forge.sans_indice" in recompenses.r_(st)["exploits"], "l'exploit « un palier sans indice » (F4, sans erreur)")
verifier("indice:fo1" in FO.f_(st)["faits"] and "indice:fo2" in FO.f_(st)["faits"], "les paliers avec un indice ne comptent pas")
verifier(indices.get("echo 'mkdir -p cabane' > cabane.sh") == langue.t("fo.indice.efface"), "un > qui efface la recette : l'indice")
verifier(indices.get("./cabane.sh") == langue.t("fo.indice.chmod"), "./ sans chmod +x : l'indice du cadenas")
verifier(indices.get("sh salut.sh") == langue.t("fo.indice.prenom"), "salut.sh sans prénom : l'indice")
verifier(all((FD / "village" / f"cabane_{i}").is_dir() for i in range(1, 11)), "le village : 10 cabanes en une boucle")
verifier(sorties.get("ls village | wc -l", "").strip() == "10", "ls village | wc -l → 10")
verifier("IndexError" in sorties.get("python3 serpent.py", "") or not PYTHON, "python3 serpent.py sans arguments : un Traceback IndexError")
verifier(re.search(r"3\. Sssalut Pixel", sorties.get("python3 serpent.py Pixel 3", "")) is not None or not PYTHON,
         "python3 serpent.py Pixel 3 : trois fois Pixel")
verifier("Bravo" in sorties.get("seq 1 10 | sh mon_jeu/devinette.sh", ""), "le robot (seq 1 10 |) trouve le nombre de la devinette")
n_ = next((n for n in maison.monde(st) if n.get("genre") == "jeu"), None)
verifier(n_ is not None and "La grotte de Pixel" in n_["etiquette"] and maison.emoji(n_) == "🎮",
         f"le jeu de l'enfant est un nouveau lieu sur la carte : {n_ and n_['etiquette']}")
carte = ANSI.sub("", "\n".join(maison.carte(st, "texte")))
verifier("🎮" in carte and "La grotte de Pixel" in carte, "la carte (tg carte) dessine 🎮 « La grotte de Pixel »")
if PYTHON and VRAI_CURL:
    verifier("Bienvenue chez Pixel" in sorties.get("curl localhost:8642", ""), "curl localhost:8642 reçoit la page de l'enfant")
    verifier(re.search(r"^\[serveur\] 864\d \(ok\)", FO.carnet(), re.M) is not None, "le serveur a été vu, sur 127.0.0.1")
    verifier(FO._page(8642) is None, "puis éteint (fg puis Ctrl+C)")
    if Path("/proc/net/tcp").exists():
        verifier(indices.get("python3 -m http.server 8642 --directory site &") == langue.t("port.lanterne.ouverte"),
                 "sans --bind 127.0.0.1 : la créature le dit tout de suite, l'étape ne passe pas")
verifier("Terminacam" in ANSI.sub("", sorties.get("tg forge exif multimedia/photo_exemple.jpg",
                                                   sorties.get("exiftool multimedia/photo_exemple.jpg", ""))),
         "les métadonnées démasquées : la marque Terminacam")
verifier(FO._photo_propre(), "la photo d'exemple est nettoyée (plus d'Exif)")
if shutil.which("convert") or shutil.which("magick"):
    verifier(FO.images_gif((FD / "multimedia" / "creature.gif").read_bytes()) == 4, "creature.gif : 4 images de la créature")
verifier((FD / "certificat_de_la_forge.txt").is_file() and "La grotte de Pixel" in (FD / "certificat_de_la_forge.txt").read_text(),
         "le certificat de Maître de la Forge")
verifier("marteau_de_forge" in st["quetes"]["objets"] and st["quetes"]["titre"] == "maitre_de_la_forge",
         "récompenses : le petit marteau de forge (posé, jamais porté) et le titre de Maître de la Forge")
verifier(not recompenses.reservee(st, {"id": "fondelin"}, "lave") and recompenses.reservee({}, {"id": "fondelin"}, "lave")
         and recompenses.reservee({}, {"id": "boulonnet"}, "neon") and recompenses.reservee({}, {"id": "tisonnier"}, "mecanique")
         and not recompenses.reservee({}, {"id": "fondelin"}, "volcan"),
         "fondelin:lave, boulonnet:neon, tisonnier:mecanique n'apparaissent qu'après un exploit ; fondelin:volcan reste libre")

print("4. Les indices")
pas = {s_["cmd"]: s_ for l_ in FO.LECONS.values() for s_ in l_["steps"]}
verifier(FO.indice(pas["echo '#!/bin/sh' > cabane.sh"], [('echo "#!/bin/sh" > cabane.sh', None)])
         == langue.t("fo.indice.guillemets_simples"), "des guillemets doubles autour de #! : prendre des simples")
verifier(FO.indice(pas["forge tours ?"], [("forge tours ?", None)]) == langue.t("fo.indice.trou"), "« ? » recopié : un trou à remplir")
FO.noter("tours", "3 (faux)")
verifier(FO.indice(pas["forge tours ?"], [("forge tours 3", None)]) == langue.t("fo.indice.rep.tours"), "une mauvaise réponse : l'indice")
verifier(FO.indice(pas[FO.SERVEUR], [("python3 -m http.server 8642", None)]) == langue.t("port.lanterne.ouverte"),
         "un serveur sans --bind 127.0.0.1 : jamais « ça marche aussi »")

print("5. La vue déployée : l'atelier de la forge")
x = deploie.forges("sh cabane.sh")
verifier([(y["outil"], y["objet"]) for y in x] == [("sh", "parchemin")], f"sh cabane.sh : le parchemin {x}")
x = deploie.forges("for i in $(seq 1 10); do mkdir -p village/cabane_$i; done")
verifier([(y["outil"], y["objet"]) for y in x] == [("for", "manege")], f"la boucle : le manège {x}")
verifier(deploie.forges("sh tests.sh") == [] and deploie.lunettes("sh tests.sh"), "sh tests.sh reste à la lunette de l'Observatoire")
l_ = "sh cabane.sh"
txt = ANSI.sub("", "\n".join(deploie.ecran(l_, deploie.blocs(l_), 1, None, 0.5, 100)))
verifier("📜" in txt and "🔥" in txt and "parchemin" in txt, "la vue déployée : le parchemin qui s'enflamme")

print("6. Sécurité")
verifier(fichiers_hors_terrain() - AVANT <= {str(HOME / ".bash_history"), str(HOME / ".terminagotchi.json")}
         or all("terminagotchi" in p or p.endswith(".bash_history") for p in fichiers_hors_terrain() - AVANT),
         f"rien d'écrit hors du terrain ({sorted(fichiers_hors_terrain() - AVANT)[:4]})")
verifier(not JOURNAL.exists(), f"aucun appel réseau hors de 127.0.0.1, ni sudo {JOURNAL.read_text()[:200] if JOURNAL.exists() else ''}")
dehors = Path(tempfile.mkdtemp()) / "photo.jpg"
dehors.write_bytes(FO.photo_octets())
o_ = ANSI.sub("", "\n".join(FO.lignes_exif(str(dehors)) + FO.lignes_nettoie(str(dehors))))
verifier(o_.count(langue.t("fo.exif.hors_terrain")) == 2 and FO.a_exif(dehors.read_bytes()),
         "forge exif et forge nettoie refusent une photo hors du terrain (et n'y touchent pas)")
src = (RACINE / "pc/tg/forge.py").read_text(encoding="utf-8")
verifier("urllib" not in src and "requests" not in src and "recense" not in src and "subprocess" not in src,
         "le module n'envoie rien et ne lance aucun script de l'enfant")
verifier("127.0.0.1" in FO.SERVEUR and all("0.0.0.0" not in (s_.get("cmd") or "") for l_ in FO.LECONS.values() for s_ in l_["steps"]),
         "le serveur montré est attaché à 127.0.0.1 ; aucune commande n'ouvre le réseau")
DANGER = re.compile(r"\brm\s+-\w*r|\bsudo\b|\bdd\b|\bmkfs|\bcurl\b.*\|\s*(sh|bash)|chmod\s+-R|>\s*/dev/")
verifier(not [s_["cmd"] for l_ in FO.LECONS.values() for s_ in l_["steps"] if DANGER.search(s_.get("cmd") or "")],
         "aucune commande dangereuse proposée")
for code in langue.LANGUES:
    langue.definir(code)
    sp = FO.serpent_py()
    dv = FO.devinette_sh()
    ok_ = '"' not in FO.sur(langue.t("fo.devinette.plus")) and sp.count('print(f"') == 1 and "$essais" in dv
    if PYTHON:
        ok_ &= subprocess.run([PYTHON, "-c", f"compile({sp!r}, 's', 'exec')"]).returncode == 0
    ok_ &= subprocess.run(["sh", "-n"], input=dv, text=True).returncode == 0
    verifier(ok_, f"{code} : serpent.py est du Python valide, devinette.sh du sh valide")
langue.definir("fr")

if PIDS.exists():                                        # (au cas où : la lanterne du test est éteinte)
    try:
        os.kill(int(PIDS.read_text().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
