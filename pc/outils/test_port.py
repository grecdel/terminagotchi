"""Le Port (phase 5, docs/programme.md § 2.12 et § 7.2), sur PC.

    python3 pc/outils/test_port.py          (crée son propre HOME temporaire)

  1. le réseau simulé : vecteurs communs à jour (donnees/port/vecteurs.json, mêmes résultats en Kotlin) ; routes,
     guidage, phares éteints, TTL ;
  2. le phare du port : un vrai serveur HTTP sur 127.0.0.1 seulement (pages, HEAD, 404, chaque machine du
     Terminaworld à son adresse de boucle locale sous Linux), le sceau en HTTPS (certificat auto-signé refusé, puis
     reconnu avec --cacert), rien d'autre que des pages fabriquées (pas de ../), il s'éteint sur demande ;
  3. l'arbre du Carrefour : fermé (avec ce qui manque) tant que le nid et la bibliothèque ne sont pas finis, puis
     ouvert, annoncé une fois ; le menu des lieux ;
  4. la traversée P0 → P11 comme un enfant (vraies commandes dans bash, commandes du jeu `port …`), les exploits
     (messager guidé, sceau vérifié), le phare miniature, le titre ; les variantes réservées libérées ;
  5. le messager de la vue déployée (ANSI), la commande tg port, l'alias posé par tg installer ;
  6. sécurité : rien n'est écrit hors du terrain (sauf le sceau dans ~/.terminagotchi/port), aucune adresse visée
     hors de la boucle locale, aucune donnée personnelle dans la clé ssh ; 14 langues.
Les outils absents de la machine de test (ping, ss, ip, tracepath, ssh-keygen…) sont remplacés par de petites
doublures, seulement pour que la partie avance : leurs vraies sorties sont rejouées par rejeu_bash.py (CI).
"""
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_port_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, deploie, histoire, langue, port, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
SORTIES = {"ping": "64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.03 ms\n3 packets transmitted, 3 received, 0% packet loss",
           "ss": "State  Recv-Q Send-Q Local Address:Port Peer Address:Port\nLISTEN 0 5 127.0.0.1:8042 0.0.0.0:*",
           "ip": "1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\ndefault via 10.0.0.1 dev eth0",
           "tracepath": " 1:  127.0.0.1    0.05ms reached", "hostname": "machine"}
for outil, sortie in SORTIES.items():
    if not shutil.which(outil):
        (DOUBLURES / outil).write_text(f"#!/bin/sh\ncat <<'FIN'\n{sortie}\nFIN\n")
        (DOUBLURES / outil).chmod(0o755)
if not shutil.which("ssh-keygen"):
    (DOUBLURES / "ssh-keygen").write_text('#!/bin/sh\nf=""; while [ $# -gt 0 ]; do [ "$1" = "-f" ] && f="$2"; shift; done\n'
                                         'echo "-----FAUSSE CLE-----" > "$f"; chmod 600 "$f"\n'
                                         'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAdoublure explorateur" > "$f.pub"\n')
    (DOUBLURES / "ssh-keygen").chmod(0o755)
if not shutil.which("ssh"):
    (DOUBLURES / "ssh").write_text("#!/bin/sh\necho 'OpenSSH_9.6p1, OpenSSL 3.0.13' >&2\n")
    (DOUBLURES / "ssh").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8")
PY = f"{sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); from tg import port; port.commande(sys.argv[1:])\""


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    """L'enfant tape une commande : vraie commande dans bash (les commandes du jeu `port …` comme l'alias
    port='tg port'), historique, puis l'invite fait une étape de jeu avec le code de sortie."""
    vrai = re.sub(r"^port\b", PY, cmd)
    r = subprocess.run(["bash", "-c", vrai + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       timeout=60, env=ENV)
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


print("1. Le réseau simulé du Terminaworld")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_port.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/port/vecteurs.json)")
verifier(port.route("camp", "feu") == ["camp", "racine", "roche", "feu"], "camp → feu : racine, roche (3 sauts)")
verifier(port.route("camp", "feu", ["roche"]) == ["camp", "racine", "plante", "poison", "ombre", "machine", "feu"],
         "la Roche éteinte : le détour par la Plante, le Poison, l'Ombre et la Machine")
verifier(port.route("camp", "feu", ["racine"]) is None, "la Racine éteinte : plus rien ne passe (le routeur central)")
verifier(all(m["adresse"].startswith("127.") for m in port.machines()), "toutes les machines sont en boucle locale (127.0.0.0/8)")
verifier(port.guider(["racine", "roche", "feu"], ["roche"])["raison"] == "eteint" and
         port.guider(["racine", "feu"])["raison"] == "pas_relie" and port.guider(["racine"] + ["eau", "plante"] * 4)["raison"] == "ttl",
         "un messager se perd : phare éteint, pas de phare entre deux machines, TTL épuisé")
verifier(port.couches_ok("Application, transport, RÉSEAU, liaison") and not port.couches_ok("liaison reseau transport application"),
         "les couches dans l'ordre (accents et majuscules sans importance)")

print("2. Le phare du port (un vrai petit serveur, seulement sur la boucle locale)")
for _ in range(30):                                          # un phare resté d'une autre partie (sim_port…) : éteint
    if not port.phare_allume():
        break
    port.eteindre_phare()
    time.sleep(0.2)
serveurs = port.phare(attendre=False)
verifier(serveurs and all(s.server_address[0].startswith("127.") for s in serveurs), "toutes les écoutes sont sur 127.x")
ouverts = [s.server_address for s in serveurs]
with urllib.request.urlopen("http://127.0.0.1:8042/feu", timeout=3) as rep:
    corps = rep.read().decode()
    verifier(rep.status == 200 and corps.startswith("🔥 feu.terminaworld (127.42.0.2)") and
             rep.headers["Server"] == "PhareDuPort/1.0", "GET /feu : la page du biome Feu (Server: PhareDuPort/1.0)")
req = urllib.request.Request("http://127.0.0.1:8042/", method="HEAD")
with urllib.request.urlopen(req, timeout=3) as rep:
    verifier(rep.status == 200 and rep.read() == b"", "HEAD / : l'enveloppe sans la lettre")
for chemin in ("/volcan_perdu", "/../../etc/passwd", "/%2e%2e/save.json"):
    try:
        urllib.request.urlopen("http://127.0.0.1:8042" + chemin, timeout=3)
        code = 200
    except urllib.error.HTTPError as e:
        code = e.code
    verifier(code == 404, f"{chemin} : 404 (le phare ne sert que ses pages)")
if sys.platform.startswith("linux") and any(a[0] == "127.42.0.3" for a in ouverts):
    with urllib.request.urlopen("http://127.42.0.3:8042/", timeout=3) as rep:
        verifier(rep.read().decode().startswith("💧 eau.terminaworld"), "127.42.0.3:8042 : la machine Eau répond à sa propre adresse")
if shutil.which("openssl") and any(a[1] == 8443 for a in ouverts):
    r1 = subprocess.run(["curl", "-sS", "https://localhost:8443/"], capture_output=True, text=True)
    r2 = subprocess.run(["curl", "-sS", "--cacert", str(core.SAVE_DIR / "port" / "sceau.pem"), "https://localhost:8443/feu"],
                        capture_output=True, text=True)
    verifier(r1.returncode == 60 and "self-signed certificate" in r1.stderr and r2.returncode == 0 and "feu.terminaworld" in r2.stdout,
             "le sceau : curl refuse le certificat auto-signé (60), puis l'accepte avec --cacert")
    verifier(oct((core.SAVE_DIR / "port" / "sceau_cle.pem").stat().st_mode & 0o777) == "0o600", "la clé du sceau est protégée (600)")
verifier(port.eteindre_phare() and (time.sleep(0.6) or not port.phare_allume()), "tg port stop : le phare s'éteint")

print("3. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()                                       # premier lancement : la partie est créée
AVANT = fichiers_hors_terrain()        # ce que l'installation a posé (.bashrc, profil et cache PowerShell en CI…)
st = core.load()
verifier(not histoire.ouvert(st, "port") and "Le nid" in histoire.choisir(st, "port", dit=False), "fermé au début (il manque le nid…)")
verifier(any("s'ouvre après" in ANSI.sub("", l) for l in histoire.lignes_ailes(st)), "le menu des lieux dit ce qui manque")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    h["chap"] = "bibliotheque"
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.fini(st, "bibliotheque") and histoire.ouvert(st, "port"), "nid et bibliothèque finis : le Port s'ouvre")
verifier(st["histoire"].get("mondes_annonces") == ["port"] and "port" in " ".join(x for x in st["log"]).lower(),
         "annoncé une fois (journal et créature)")
verifier((T / "port" / "panneau.txt").is_file() and (T / "port" / "annuaire.txt").read_text().startswith("127.0.0.1\tlocalhost"),
         "le port est meublé (panneau, annuaire au format de /etc/hosts…)")
st, _ = tape("pwd")
verifier(st["histoire"].get("mondes_annonces") == ["port", "crypte"],
         "la Crypte, ouverte en même temps, est annoncée au tour suivant (une nouvelle à la fois)")

print("4. La traversée du Port, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/port")
verifier(lecon(st) == ("port0", 1), f"entrer dans le port choisit le monde : {lecon(st)}")
graine = port._graine(st)
vrai = port.vrai_sceau(graine)
faux = vrai % 4 + 1
PARCOURS = [
    "ls", "cat panneau.txt",
    "hostname", "ip a", "ping -c 3 localhost",
    "cat /etc/hosts", "getent hosts localhost", "grep feu annuaire.txt",
    "curl -I http://localhost:8042/", "curl -s http://localhost:8042/eau | head -n 3",
    "curl -o colis.html http://localhost:8042/feu", "curl -I http://localhost:8042/volcan_perdu",
    "ssh -V", 'ssh-keygen -t ed25519 -N "" -C explorateur -f cle_du_port', "cat cle_du_port.pub",
    'echo "Bienvenue sur mon quai" > quai/index.html',
    "python3 -m http.server 8000 --bind 127.0.0.1 --directory quai > /dev/null 2>&1 & sleep 1.5; curl -s http://localhost:8000; kill %1",
    "curl -v http://localhost:8042/", "port couches", 'echo "application transport reseau liaison" > couches.txt',
    "ss -tln", "ss -tln | grep 8042", "port carte",
    "ss -t", "ss -u", "port course",
    "ip route", "tracepath -n 127.0.0.1", "port messager feu", "port eteins roche", "port guide racine roche feu",
    "port guide racine plante poison ombre machine feu",
    "ip route | grep default", "ip neigh", "port gardien",
    "curl https://localhost:8443", "curl --cacert sceau_du_phare.pem https://localhost:8443", "port sceau", f"port sceau {faux}",
    f"port sceau {vrai}",
]
sorties = {}
for c in PARCOURS:
    st, s = tape(c)
    sorties[c] = s
    if os.environ.get("TG_DEBUG"):
        print(f"    · {c} → {lecon(st)} {(s if '8443' in c else s[:70])!r}")
    if histoire.fini(st, "port"):
        break
verifier(histoire.fini(st, "port"), f"le Port est réveillé jusqu'au bout (P0 → P11) {lecon(st)}")
verifier(sorties["curl -I http://localhost:8042/"].startswith("HTTP/1.1 200 OK"), "curl -I : la vraie réponse du phare")
verifier(len(sorties["curl -s http://localhost:8042/eau | head -n 3"].strip().split("\n")) == 3, "le tuyau | head -n 3")
verifier("Bienvenue sur mon quai" in sorties[PARCOURS[16]], "la lanterne de l'enfant (http.server --bind 127.0.0.1) répond")
verifier("> GET / HTTP/1.1" in sorties["curl -v http://localhost:8042/"], "curl -v : la lettre (la requête) est visible")
r_ = recompenses.r_(st)
verifier("port.messager" in r_["exploits"] and "port.sceau" in r_["exploits"], "les deux exploits du Port (messager guidé, sceau)")
verifier("phare_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "capitaine_du_port",
         "récompenses : le phare miniature et le titre de Capitaine du Port")
verifier(not recompenses.reservee(st, {"id": "plumange"}, "orage") and recompenses.reservee({}, {"id": "plumange"}, "orage")
         and not recompenses.reservee({}, {"id": "lumignon"}, "orage"), "variantes réservées : plumange:orage libérée par les exploits")
carnet = port.carnet()
verifier("[guide]" in carnet and "(perdu)" in carnet and "[sceau]" in carnet, "le carnet de bord garde la carte et les essais")
pub = (T / "port" / "cle_du_port.pub").read_text()
verifier(pub.strip().endswith(" explorateur") and os.environ.get("USER", "§") not in pub.split()[-1],
         "la clé ssh ne porte aucune donnée personnelle (commentaire « explorateur »)")

print("5. La vue déployée et la commande")
d = deploie.messager("curl -s http://localhost:8042/eau | head -n 3")
verifier(d == [{"seg": 0, "cmd": "curl", "dest": "localhost:8042", "local": True}], "le messager de curl va à localhost:8042")
verifier(deploie.messager("ping -c 3 example.com")[0]["local"] is False and deploie.messager("ls -l") == [],
         "example.com : dehors (avec un adulte) ; ls : pas de messager")
txt = ANSI.sub("", "\n".join(deploie.ecran("port messager feu", deploie.blocs("port messager feu"), 1, None, 0.25, 100)))
verifier("✉" in txt and "feu.terminaworld" in txt and "boucle locale" in txt, "la vue déployée dessine le messager (aller, puis retour)")
sortie = io.StringIO()
port.commande(["annuaire", "feu"], sortie)
verifier("feu.terminaworld → 127.42.0.2" in sortie.getvalue(), "tg port annuaire feu")
from tg import compagnon  # noqa: E402
verifier(any("port='tg port'" in b or "function port" in b for b in compagnon._blocs().values()),
         "tg installer pose l'alias port='tg port'")

print("5 bis. Les indices du Port (sim_port.py : ce qui a gêné Léa, Inès et Hugo)")
pas = {s_["cmd"]: s_ for l_ in port.LECONS.values() for s_ in l_["steps"]}
G, S_, Q, C = pas["port guide racine … feu"], pas["port sceau ?"], pas["curl http://localhost:8000"], \
    pas["curl -s http://localhost:8042/eau | head -n 3"]
verifier(port.indice(G, [("port guide racine … feu", None)]) == langue.t("port.indice.remplace") and
         port.indice(S_, [("port sceau ?", None)]) == langue.t("port.indice.remplace") and
         port.indice(S_, [("port sceau", None)]) == langue.t("port.sceau.aide"), "« … » et « ? » recopiés : des trous à remplir")
verifier("locahost" in (port.indice(C, [("curl -s http://locahost:8042/eau | head -n 3", None)]) or "") and
         not re.search(C["re"], "curl -s http://locahost:8042/eau | head -n 3"), "« locahost » caché par le tuyau : ni validé, ni « marche aussi »")
verifier("8000" in (port.indice(Q, [("curl http://localhost:8000", None)]) or ""), "la lanterne pas encore allumée : « réessaie dans une seconde »")
verifier(port.indice(pas["python3 -m http.server 8000 --bind 127.0.0.1 --directory quai &"],
                     [("python3 -m http.server 8000 --directory quai &", None)]) == langue.t("port.lanterne.ouverte") and
         port.SANS_BIND.search("python3 -m http.server 8000") and not port.SANS_BIND.search("python3 -m http.server 8000 -b 127.0.0.1"),
         "la lanterne SANS --bind : prévenu, jamais « marche aussi »")

print("6. Sécurité et langues")
port.eteindre_phare()
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)     # le cache de PowerShell lui-même (tg installer lit $PROFILE)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in port.LECONS for s in port.LECONS[lid]["steps"])
hotes = set(re.findall(r"https?://([^/:\s]+)", cmds))
verifier(hotes <= {"localhost", "127.0.0.1"}, f"les leçons ne visent que la boucle locale {sorted(hotes)}")
verifier("--bind 127.0.0.1" in cmds, "le serveur de l'enfant est attaché à 127.0.0.1")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k for lid in port.LECONS for s in port.LECONS[lid]["steps"] for k in (s["dit"], s["bravo"])
         if isinstance(k, str) and k not in dct]
    m += [k for k in ("hist.port.titre", "hist.port.debut", "hist.port.fin", "port.ferme", "dep.messager") if k not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes du Port existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
