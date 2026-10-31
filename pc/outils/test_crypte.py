"""La Crypte des Codes (phase 5, docs/programme.md § 7.9), sur PC.

    python3 pc/outils/test_crypte.py          (crée son propre HOME temporaire)

  1. la spécification pure : vecteurs communs à jour (donnees/crypte/vecteurs.json, mêmes résultats en Kotlin) ;
     César = le vrai tr, sha512crypt = le vrai openssl passwd -6, la preuve de travail = la vraie boucle shell,
     la chaîne et sa vérification, les peintures, le dé pipé, le quiz, le grimoire mystère (le « e » en tête) ;
  2. l'arbre du Carrefour : fermée tant que les niveaux 0 à 4 ne sont pas finis, puis ouverte et annoncée une fois ;
     elle est meublée (règle du sphinx, messages, grimoires, chaîne, copies…) ;
  3. la traversée cr0 → cr14 comme un enfant (vraies commandes dans bash, gpg avec --homedir .trousseau, commandes du
     jeu `crypte …`) : la roue, l'avalanche, l'attaque par dictionnaire sur la base fictive, le coffre openssl, la
     paire de clés, le secret pour la créature, la signature, le dé, le quiz, le registre, la chaîne qui se brise puis
     réparée SANS indice (variante rare), les copies et le tricheur, le minage, l'échange signé ajouté à la chaîne,
     la vitrine, le carnet de bord (légendaire) ; le sceau miniature et le titre ;
  4. les indices (gpg sans --homedir, « ? » recopié, mauvaise roue, mauvais biome…) et la surveillance ;
  5. la vue déployée : la roue de César d'un `tr` ;
  6. sécurité : rien hors du terrain (sauf ~/.terminagotchi), aucun gpg-agent ne reste, aucune adresse réseau, jamais
     de sudo, seulement des clés d'exemple, aucun mot « acheter / vendre / portefeuille » dans les leçons ; 14 langues.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_cry_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
os.environ.pop("GNUPGHOME", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, crypte as K, deploie, histoire, langue, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
if not shutil.which("xxd"):            # une doublure de xxd (seulement -r -p et l'affichage simple) si l'outil manque
    (DOUBLURES / "xxd").write_text(
        f"#!{sys.executable}\nimport sys\na = [x for x in sys.argv[1:] if not x.startswith('-')]\n"
        "d = open(a[0], 'rb').read() if a else sys.stdin.buffer.read()\n"
        "if '-r' in sys.argv:\n    sys.stdout.buffer.write(bytes.fromhex(d.decode().replace(chr(10), '').replace(' ', '')))\n"
        "else:\n    [print('%08x: ' % i + d[i:i + 16].hex(' ', 2)) for i in range(0, len(d), 16)]\n")
    (DOUBLURES / "xxd").chmod(0o755)
(DOUBLURES / "crypte").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                  "from tg import crypte; crypte.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "crypte").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8")
GPG = shutil.which("gpg") is not None


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=120, env=ENV)
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


def agents():
    r = subprocess.run(["bash", "-c", "ps -eo args | grep -c '^gpg-agent.*" + str(T) + "'"], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_crypte.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/crypte/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
justes = 0
for k in (1, 3, 7, 13, 25):
    de = K.ALPHA
    vers = K.ALPHA[k:] + K.ALPHA[:k]
    s = subprocess.run(["tr", de, vers], input="le sphinx de givre, 2026 !", capture_output=True, text=True).stdout
    justes += s == K.cesar("le sphinx de givre, 2026 !", k) and K.rotation(de, vers) == k
verifier(justes == 5, f"César = le vrai tr, et la roue lit le décalage de `tr a-z …` ({justes}/5)")
if shutil.which("openssl"):
    vrai = subprocess.run(["openssl", "passwd", "-6", "-salt", "sel2026", "licorne"], capture_output=True, text=True).stdout.strip()
    verifier(vrai == K.sha512crypt("licorne", "sel2026"), "sha512crypt = openssl passwd -6 (le portage Android aussi : vecteurs)")
m = subprocess.run(["bash", "-c", K.mineur_sh().replace("\nd=${1:-2}", "\nd=2")], capture_output=True, text=True, cwd=tempfile.mkdtemp())
verifier(f"nonce = {K.miner('bloc5', 2)}" in m.stdout and K.miner("bloc5", 2) == 139 and K.miner("bloc5", 3) == 2615,
         "la preuve de travail du jeu = la vraie boucle du mineur (2 zéros : 139, 3 zéros : 2615)")
langue.definir("fr")
ch = K.chaine(K.donnees_chaine())
blocs = [ch[f"bloc_{k}.txt"] for k in range(5)]
casse = list(blocs)
casse[1] += "triche\n"
verifier([e for _k, e in K.verifier_chaine(blocs)] == ["ok"] * 4 and
         [e for _k, e in K.verifier_chaine(casse)] == ["ok", "casse", "douteux", "douteux"],
         "la chaîne : intacte, puis brisée au maillon 1 → 2 et tout ce qui suit devient douteux")
p = K.peintures()
verifier(p["A"] == 8 and p["B"] == 19 and p["s1"] == p["s2"] == 2, "les peintures : 5^6 mod 23 = 8, secret commun 2")
verifier(len(set(K.de_suite("1:0", 8))) == 8, "le dé pipé parcourt ses 8 faces (période complète : prévisible)")
for code in langue.LANGUES:
    langue.definir(code)
    f = K.frequences(K.grimoire("cr.grimoire.mystere"))
    if not f or f[0][1] != "e" or f[0][0] == f[1][0]:
        verifier(False, f"grimoire mystère en {code} : le « e » doit être la lettre la plus fréquente ({f[:3]})")
langue.definir("fr")
verifier(len(K.trouves_par_dico()) == 3 and all(len(x["passe"]) > 20 for x in K.donnees()["base"] if x["nom"] in ("gardien", "sphinx")),
         "l'attaque par dictionnaire trouve 3 mots faibles ; les phrases de passe résistent")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "crypte"), "fermée au début")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid"]
    h["chap"] = "bibliotheque"
    h.setdefault("mondes_annonces", []).extend(["port"])
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.ouvert(st, "crypte"), f"niveaux 0 à 4 finis : la Crypte s'ouvre (il manquait {K.manque(core.load())})")
verifier("crypte" in st["histoire"].get("mondes_annonces", []), "annoncée une fois")
verifier((T / "crypte" / "regle_du_sphinx.txt").is_file() and (T / "crypte" / "chaine" / "bloc_4.txt").is_file() and
         len(list((T / "crypte" / "copies").iterdir())) == 9, "la Crypte est meublée (règle, chaîne, 9 copies…)")

print("3. La traversée de la Crypte, comme un enfant")
st, _ = tape("cd ~/terrain_terminagotchi/crypte")
verifier(lecon(st) == ("cr0", 1), f"entrer dans la Crypte choisit le monde : {lecon(st)}")
gr = K._graine(st)
sorties = {}
H = K.HOMEDIR


def de_suivant():
    return K.de_suite(gr, K.donnees()["de"]["montres"] + 1)[-1]


PARCOURS = [
    "ls", "cat regle_du_sphinx.txt",
    "echo bonjour | base64", "base64 -d messages/message_1.txt", "xxd -r -p messages/message_2.txt", "crypte demasque",
    "echo bonjour | tr 'a-z' 'd-za-c'", "tr 'd-za-c' 'a-z' < grimoire/cesar.txt", "tr 'a-z' 'n-za-m' < grimoire/rot13.txt",
    "grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3", "crypte roue 5" if K.decalage(gr) != 5 else "crypte roue 6",
    lambda: f"crypte roue {K.decalage(gr)}",
    "echo -n a | sha256sum", "echo -n b | sha256sum", "crypte avalanche chat chas", "sha256sum -c sceaux.sha256",
    "cat base_fictive.txt", "cat dictionnaire.sh", "sh dictionnaire.sh", "openssl passwd -6 licorne",
    "cat parchemin.txt", K.CHIFFRE, "head -c 8 parchemin.enc", "crypte donne parchemin.enc",
    "crypte peintures", "echo $((5**6 % 23))", K.GENKEY, K.CHIFFRE_GPG, "crypte donne secret.gpg",
    f"gpg {H} --clearsign message.txt", f"gpg {H} --verify message.txt.asc",
    "head -c 16 /dev/urandom | xxd", "openssl rand -hex 16", "crypte de", lambda: f"crypte de {de_suivant()}",
    "crypte quiz", "crypte quiz v v v v v v", lambda: "crypte quiz " + " ".join(K.bonnes_reponses(gr)),
    "cat registre.txt", 'echo "Lune donne 2 plumes a Pixel" >> registre.txt', "crypte registre",
    "cat chaine/bloc_1.txt", "sha256sum chaine/bloc_0.txt", "sh verifie_chaine.sh", "echo triche >> chaine/bloc_1.txt",
    "sh verifie_chaine.sh", "cp archives/bloc_1.txt chaine/", "crypte chaine",
    "sha256sum copies/*/registre.txt", "sha256sum copies/*/registre.txt | cut -c1-64 | sort | uniq -c",
    lambda: f"diff copies/feu/registre.txt copies/{K.tricheur(gr)}/registre.txt", "crypte consensus feu",
    lambda: f"crypte consensus {K.tricheur(gr)}",
    "cat mineur.sh", "sh mineur.sh 2", "time sh mineur.sh 3", "crypte mine",
    'echo "Pixel donne 2 glands a Lune" > echange.txt', f"gpg {H} --clearsign echange.txt",
    f"gpg {H} --verify echanges/faux.txt.asc", "crypte signe echange.txt.asc",
    "crypte vitrine", "grep -h donnees chaine/bloc_*.txt", "sh verifie_chaine.sh carnet_de_bord", "crypte recensement",
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
    if histoire.fini(st, "crypte"):
        break
if not histoire.fini(st, "crypte"):
    for a, c, b in vus[-6:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "crypte"), f"la Crypte est traversée jusqu'au bout (cr0 → cr14) {lecon(st)}")
verifier(sorties.get("echo bonjour | base64", "").strip() == "Ym9uam91cgo=", "base64 : Ym9uam91cgo=")
verifier("dragon-exemple" in sorties.get("base64 -d messages/message_1.txt", ""), "le message « secret » se lit sans clé")
verifier(sorties.get("echo bonjour | tr 'a-z' 'd-za-c'", "").strip() == "erqmrxu", "la roue de César : erqmrxu")
verifier("sort_2.txt: FAILED" in sorties.get("sha256sum -c sceaux.sha256", ""), "le sceau du grimoire touché : FAILED")
verifier(all(x in sorties.get("sh dictionnaire.sh", "") for x in ("soleil", "123456", "licorne")) and
         "plumange" not in sorties.get("sh dictionnaire.sh", ""), "l'attaque par dictionnaire : 3 mots faibles, pas les phrases")
verifier("CASSÉ" in sorties.get("sh verifie_chaine.sh", "") or any("CASSÉ" in v for k, v in sorties.items() if "verifie" in k),
         "verifie_chaine.sh : le maillon cassé")
verifier("nonce = 139" in sorties.get("sh mineur.sh 2", "") and "nonce = 2615" in sorties.get("time sh mineur.sh 3", ""),
         "le mineur trouve 139 puis 2615 et s'arrête seul")
if GPG:
    verifier("Good signature" in sorties.get(f"gpg {H} --verify message.txt.asc", ""), "gpg : bon sceau")
    verifier("BAD signature" in sorties.get(f"gpg {H} --verify echanges/faux.txt.asc", ""), "gpg : l'échange trafiqué est rejeté")
    verifier("givre" in ANSI.sub("", sorties.get("crypte donne secret.gpg", "")), "la créature ouvre le secret avec SA clé privée")
    verifier((T / "crypte" / "chaine" / "bloc_5.txt").is_file(), "l'échange signé devient le bloc 5 de la chaîne")
r_ = recompenses.r_(st)
verifier("crypte.chaine" in r_["exploits"], "la chaîne réparée sans indice : variante rare (crypte.chaine)")
verifier("crypte.b6" in r_["exploits"], "le carnet de bord vérifié : la légendaire (crypte.b6)")
verifier("sceau_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "sphinx_de_la_crypte",
         "récompenses : le sceau miniature et le titre de Sphinx de la Crypte")
verifier(not recompenses.reservee(st, {"id": "lichonarque"}, "crypte") and recompenses.reservee({}, {"id": "lichonarque"}, "crypte"),
         "la gardienne du registre (lichonarque:crypte) n'apparaît qu'après un exploit de la Crypte")

print("4. Les indices et la surveillance")
pas = {s_["cmd"]: s_ for l_ in K.LECONS.values() for s_ in l_["steps"]}
verifier(K.indice(pas[K.GENKEY], [("gpg --quick-gen-key moi", None)]) == langue.t("cr.indice.homedir"),
         "gpg sans --homedir : l'indice (le vrai trousseau n'est jamais visé par les leçons)")
verifier(K.indice(pas["crypte roue ?"], [("crypte roue ?", None)]) == langue.t("cr.indice.trou"), "« ? » recopié : un trou à remplir")
K.noter("roue", "4 (faux)")
verifier(K.indice(pas["crypte roue ?"], [("crypte roue 4", None)]) == langue.t("cr.indice.roue"), "mauvaise roue : compter les lettres")
K.noter("consensus", "roche (faux)")
verifier(K.indice(pas["crypte consensus ?"], [("crypte consensus roche", None)]) == langue.t("cr.indice.consensus"), "mauvais biome")
s0 = core.load()
verifier(K.surveiller(s0, ["gpg --gen-key"]) and not K.surveiller(s0, [f"gpg {H} --list-keys"]),
         "la créature prévient si gpg est tapé sans --homedir")
verifier(all(K.SANS_HOMEDIR.search(x["cmd"]) is None for l_ in K.LECONS.values() for x in l_["steps"]),
         "toutes les commandes gpg des leçons portent --homedir .trousseau")

print("5. La vue déployée : la roue de César")
x = deploie.roue("echo bonjour | tr 'a-z' 'd-za-c'")
verifier(x and x[0]["decalage"] == 3 and x[0]["seg"] == 1, "tr 'a-z' 'd-za-c' : décalage 3, sur le bloc du tr")
verifier(deploie.roue("tr 'd-za-c' 'a-z'")[0]["decalage"] == 23 and deploie.roue("tr a-z A-Z") == [], "le retour : 23 ; a-z → A-Z n'est pas une roue")
txt = ANSI.sub("", "\n".join(deploie.ecran("echo bonjour | tr 'a-z' 'd-za-c'", deploie.blocs("echo bonjour | tr 'a-z' 'd-za-c'"),
                                           4, None, 0.9, 100)))
verifier("d e f g" in txt and "+3" in txt, "la vue déployée dessine la roue (alphabet clair et décalé)")
out = io.StringIO()
K.commande(["chaine"], out)
verifier("[0]" in ANSI.sub("", out.getvalue()) and "[4]" in ANSI.sub("", out.getvalue()), "crypte chaine dessine la chaîne")
from tg import compagnon  # noqa: E402
verifier(any("crypte='tg crypte'" in b or "function crypte" in b for b in compagnon._blocs().values()),
         "tg installer pose l'alias crypte='tg crypte'")

print("6. Sécurité et langues")
K.tuer_agents()
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
verifier(not (HOME / ".gnupg").exists(), "le vrai trousseau (~/.gnupg) n'a jamais été créé ni touché")
verifier(agents() == 0, "aucun gpg-agent du terrain ne reste en vie")
cmds = " ".join(s.get("cmd") or "" for lid in K.LECONS for s in K.LECONS[lid]["steps"])
verifier(not re.search(r"https?://", cmds) and "sudo" not in cmds, "aucune adresse réseau, aucun sudo dans les leçons")
verifier(set(re.findall(r"pass:(\S+)", cmds)) <= {K.CLE} and "exemple" in K.CLE, "seulement la clé d'exemple")
fr = langue._charger("fr")
textes = " ".join(v for k, v in fr.items() if isinstance(v, str) and (k.startswith("cr.") or k.startswith("hist.cr")))
verifier(not re.search(r"\b(achète|acheter|vends|vendre|investi|portefeuille|gagner de l'argent|rentab)", textes, re.I),
         "aucun texte de la Crypte ne parle d'acheter, de vendre ou d'investir")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k for lid in K.LECONS for s in K.LECONS[lid]["steps"] for k in (s["dit"], s["bravo"]) if isinstance(k, str) and k not in dct]
    m += [k for k in ("hist.crypte.titre", "hist.crypte.debut", "hist.crypte.fin", "cr.ouvert.dit", "dep.roue") if k not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes de la Crypte existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
