"""🗝 La Crypte des Codes — cryptographie et blockchain (docs/programme.md § 7.9, paliers K1 à K8 et B1 à B6).

Le troisième monde de la phase 5 (§ 7.14, étape 4 bis). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → crypte → requis : brancher les commandes, `|` et `>`).
On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, regle_du_sphinx.txt) : tout est HORS LIGNE et reste dans ~/terrain_terminagotchi/crypte/.
Les mots de passe, les clés et les phrases sont des EXEMPLES. gpg ne sert qu'avec `--homedir .trousseau` (un dossier du
terrain : jamais le trousseau de l'utilisateur). AUCUNE vraie crypto-monnaie, aucun portefeuille, jeton, NFT, achat ni
vente : la blockchain est expliquée techniquement (B6), avec ce qu'on a construit soi-même. Le « minage » (B4) est
minuscule : une boucle de quelques milliers d'essais au plus, qui s'arrête seule.

LES PALIERS (cr0 à cr14) : la porte du sphinx ; K1 cacher n'est pas chiffrer (base64, xxd) ; K2 les codes anciens
(César, ROT13, fréquences, pont « modulo ») ; K3 les empreintes (sha256sum, avalanche) ; K4 les mots de passe (base
FICTIVE, attaque par dictionnaire, sel) ; K5 le coffre à une clé (openssl) ; K6 le cadenas ouvert (mélange de
peintures, gpg) ; K7 le hasard ; K8 demain (quiz) ; B1 le registre ; B2 la chaîne d'empreintes (qui se brise) ; B3
les copies des 9 biomes (consensus) ; B4 la preuve de travail ; B5 les échanges signés ; B6 les applications
(explication technique) et le carnet de bord infalsifiable de l'enfant.

LES COMMANDES DU JEU (`crypte …`, alias posé par `tg installer`) font ce qu'un script ne montre pas bien (la roue, les
peintures, l'avalanche, la chaîne dessinée, la table du minage, le quiz) et écrivent dans le carnet du sphinx
(crypte/carnet_du_sphinx.txt) ce que les étapes vérifient. Mêmes règles sur Android (Crypte.kt, vecteurs communs
donnees/crypte/vecteurs.json).
"""
import base64
import codecs
import hashlib
import json
import os
import pkgutil
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from . import core
from .langue import courante, t
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "crypte.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
ALPHA = "abcdefghijklmnopqrstuvwxyz"
LATINES = ("fr", "en", "es", "de", "it", "pt", "id")


def sha(texte):
    return hashlib.sha256(texte.encode("utf-8") if isinstance(texte, str) else texte).hexdigest()


def ascii_bas(texte):
    """Le texte en minuscules sans accents (les codes anciens ne connaissent que a-z)."""
    s = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).replace("œ", "oe").replace("æ", "ae").replace("ß", "ss")


def cesar(texte, k):
    """Décale chaque lettre a-z de k (comme tr 'a-z' 'd-za-c' pour k = 3) ; le reste ne bouge pas."""
    k %= 26
    return "".join(ALPHA[(ALPHA.index(c) + k) % 26] if c in ALPHA else c for c in texte)


def frequences(texte):
    """[(nombre, lettre)] du plus fréquent au moins fréquent (égalités : ordre alphabétique inverse, comme sort -rn)."""
    c = {}
    for x in texte:
        if x in ALPHA:
            c[x] = c.get(x, 0) + 1
    return sorted(((n, l) for l, n in c.items()), key=lambda p: (-p[0], [-ord(x) for x in p[1]]))


def decalage(graine):
    """Le décalage secret du grimoire mystère pour cette partie (jamais 0, 3 ni 13 : ceux-là sont déjà montrés)."""
    evites = donnees()["cesar"]["evites"]
    v = int(sha(f"{graine}:roue")[:8], 16)
    choix = [k for k in range(26) if k not in evites]
    return choix[v % len(choix)]


def deplier(s):
    """Un ensemble de tr (« d-za-c ») en liste de caractères ; None s'il contient autre chose que des lettres."""
    s = s.strip("'\"")
    out = []
    i = 0
    while i < len(s):
        if i + 2 < len(s) and s[i + 1] == "-":
            a, b = ord(s[i]), ord(s[i + 2])
            if b < a:
                return None
            out += [chr(x) for x in range(a, b + 1)]
            i += 3
        else:
            out.append(s[i])
            i += 1
    return out


def rotation(de, vers):
    """Le décalage de `tr DE VERS` si c'est une roue de César sur les minuscules (a-z), sinon None."""
    a, b = deplier(de or ""), deplier(vers or "")
    if not a or not b or len(a) < 26 or len(b) < len(a):
        return None
    ks = set()
    for x, y in zip(a, b):
        if x in ALPHA and y in ALPHA:
            ks.add((ALPHA.index(y) - ALPHA.index(x)) % 26)
        elif x.lower() in ALPHA and y.lower() in ALPHA and x.isupper() == y.isupper():
            ks.add((ALPHA.index(y.lower()) - ALPHA.index(x.lower())) % 26)
        else:
            return None
    if len(ks) != 1 or not set(ALPHA) <= {c for c in a}:
        return None
    return ks.pop()


def message_code(n, texte):
    """Un message de K1 « caché » (jamais chiffré) : base64, hexadécimal ou ROT13."""
    code = next(m["code"] for m in donnees()["messages"] if m["n"] == n)
    b = texte.encode("utf-8")
    if code == "base64":
        return base64.b64encode(b).decode() + "\n"
    if code == "hex":
        return b.hex() + "\n"
    return cesar(ascii_bas(texte), 13) + "\n"


def bits_differents(a_hex, b_hex):
    """Le nombre de bits qui changent entre deux empreintes (l'effet avalanche : environ la moitié)."""
    return bin(int(a_hex, 16) ^ int(b_hex, 16)).count("1")


def lettres_differentes(a_hex, b_hex):
    return sum(1 for x, y in zip(a_hex, b_hex) if x != y)


def base_fictive():
    """La base de mots de passe FICTIVE du gardien : « nom:empreinte sha256 » (sans sel : c'est la faiblesse)."""
    return [f"{x['nom']}:{sha(x['passe'])}" for x in donnees()["base"]]


def trouves_par_dico():
    """[(nom, mot)] que l'attaque par dictionnaire retrouve (dans l'ordre du dictionnaire)."""
    par_empreinte = {sha(x["passe"]): x["nom"] for x in donnees()["base"]}
    return [(par_empreinte[sha(m)], m) for m in donnees()["dico"] if sha(m) in par_empreinte]


def peintures():
    """Diffie-Hellman avec de petits nombres : A = g^a mod p, B = g^b mod p, secret = B^a = A^b mod p."""
    d = donnees()["peintures"]
    p, g, a, b = d["p"], d["g"], d["a"], d["b"]
    A, B = pow(g, a, p), pow(g, b, p)
    return {"p": p, "g": g, "a": a, "b": b, "A": A, "B": B, "s1": pow(B, a, p), "s2": pow(A, b, p)}


def de_suite(graine, n):
    """Le dé pipé (générateur congruentiel trop simple) : x' = (a·x + c) mod m, valeurs 0 à m − 1."""
    d = donnees()["de"]
    x = int(sha(f"{graine}:de")[:4], 16) % d["m"]
    out = []
    for _ in range(n):
        x = (d["a"] * x + d["c"]) % d["m"]
        out.append(x)
    return out


def quiz(graine):
    """Les 6 affirmations du quiz « demain », mélangées pour cette partie : [(n°, id, réponse v/f/s)]."""
    q = list(donnees()["quiz"])
    random.Random(f"quiz:{graine}").shuffle(q)
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(q)]


def bonnes_reponses(graine):
    return [r for _n, _i, r in quiz(graine)]


def bloc_texte(k, precedent, donnees_bloc):
    return f"bloc: {k}\nprecedent: {precedent}\ndonnees: {donnees_bloc}\n"


def chaine(lignes):
    """Une chaîne de blocs : chaque bloc porte l'empreinte du bloc d'avant. {nom: texte}, bloc_0 en premier."""
    out = {}
    prec = "0" * 64
    for k, d in enumerate(lignes):
        txt = bloc_texte(k, prec, d)
        out[f"bloc_{k}.txt"] = txt
        prec = sha(txt)
    return out


def verifier_chaine(blocs):
    """blocs = [texte du bloc 0, 1, …] → [(k, état)] pour chaque maillon k → k+1 : « ok », « casse » (l'empreinte
    notée ne correspond plus), « douteux » (après une cassure : plus rien n'est sûr)."""
    out = []
    casse = False
    for k in range(len(blocs) - 1):
        m = re.search(r"^precedent: (\S+)", blocs[k + 1], re.M)
        note = m.group(1) if m else ""
        if casse:
            out.append((k, "douteux"))
        elif note == sha(blocs[k]):
            out.append((k, "ok"))
        else:
            out.append((k, "casse"))
            casse = True
    return out


def tricheur(graine):
    """Le biome dont la copie du registre a été trafiquée (jamais le premier : on compare avec lui)."""
    b = donnees()["biomes"]
    return b[1 + int(sha(f"{graine}:tricheur")[:6], 16) % (len(b) - 1)]


def miner(donnees_bloc, zeros, maximum=None):
    """La preuve de travail : le premier nonce n (1, 2, …) dont sha256(données + n) commence par `zeros` zéros
    hexadécimaux, ou None au-delà de maximum essais."""
    mx = maximum or donnees()["mine"]["max"]
    z = "0" * zeros
    for n in range(1, mx + 1):
        if sha(f"{donnees_bloc}{n}").startswith(z):
            return n
    return None


def sha512crypt(mot, sel, tours=5000):
    """openssl passwd -6 (SHA-crypt d'Ulrich Drepper, 5000 tours) : « $6$sel$… » (vecteurs communs avec Crypte.kt)."""
    p, s = mot.encode(), sel.encode()[:16]
    h = hashlib.sha512
    b = h(p + s + p).digest()
    a = h()
    a.update(p + s)
    n = len(p)
    while n > 64:
        a.update(b)
        n -= 64
    a.update(b[:n])
    n = len(p)
    while n:
        a.update(b if n & 1 else p)
        n >>= 1
    a = a.digest()
    dp = h(p * len(p)).digest()
    P = (dp * (len(p) // 64 + 1))[:len(p)]
    ds = h(s * (16 + a[0])).digest()
    S = (ds * (len(s) // 64 + 1))[:len(s)]
    c = a
    for i in range(tours):
        x = h()
        x.update(P if i & 1 else c)
        if i % 3:
            x.update(S)
        if i % 7:
            x.update(P)
        x.update(c if i & 1 else P)
        c = x.digest()
    car = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    ordre = [(0, 21, 42), (22, 43, 1), (44, 2, 23), (3, 24, 45), (25, 46, 4), (47, 5, 26), (6, 27, 48), (28, 49, 7),
             (50, 8, 29), (9, 30, 51), (31, 52, 10), (53, 11, 32), (12, 33, 54), (34, 55, 13), (56, 14, 35),
             (15, 36, 57), (37, 58, 16), (59, 17, 38), (18, 39, 60), (40, 61, 19), (62, 20, 41)]
    out = ""
    for x, y, z in ordre:
        v = (c[x] << 16) | (c[y] << 8) | c[z]
        for _ in range(4):
            out += car[v & 63]
            v >>= 6
    v = c[63]
    for _ in range(2):
        out += car[v & 63]
        v >>= 6
    return f"$6${s.decode()}${out}"


# ================================================================ l'état, le terrain, le carnet du sphinx
def c_(state):
    c = state.setdefault("crypte", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "crypte"


CARNET = "carnet_du_sphinx.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok", sujet=None):
    debut = rf"^\[{etiquette}\] {re.escape(sujet)}\b" if sujet else rf"^\[{etiquette}\]"
    return re.search(debut + rf".*\({mot}\)\s*$", carnet(), re.M) is not None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _lire(rel):
    try:
        b = (core.TERRAIN / rel).read_bytes()
    except OSError:
        return ""
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    return b.decode("utf-8", "replace")


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, texte, mode=None):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(texte, bytes):
            p.write_bytes(texte)
        else:
            p.write_text(texte, encoding="utf-8")
        if mode is not None:
            os.chmod(p, mode)
        return True
    except OSError:
        return False


def _sur(s):
    """Un texte posé dans un script shell entre guillemets doubles : sans " $ ` \\."""
    return re.sub(r'["$`\\]', "'", s)


def latin():
    """La langue des grimoires codés (les codes anciens ne connaissent que a-z) : la langue choisie si elle s'écrit en
    lettres latines, sinon l'anglais."""
    return courante() if courante() in LATINES else "en"


def grimoire(cle):
    from .langue import brut
    return ascii_bas(brut(cle, latin()) or brut(cle, "en") or "")


def lignes_registre():
    """Le grand registre du village (B1) : les lignes, dans la langue choisie."""
    return [t(f"cr.registre.{i}") for i in range(1, 5)]


def donnees_chaine():
    return [t(f"cr.bloc.{k}") for k in range(donnees()["chaine"]["blocs"])]


def mineur_sh():
    m = donnees()["mine"]
    return ("#!/bin/sh\n"
            f"# {_sur(t('cr.mine.sh1'))}\n"
            f"# {_sur(t('cr.mine.sh2'))}\n"
            f"BLOC=\"{m['donnees']}\"\n"
            "d=${1:-2}\n"
            f"if [ \"$d\" -gt {m['difficulte_max']} ]; then echo \"{_sur(t('cr.mine.trop'))}\"; exit 1; fi\n"
            "z=$(echo 0000000 | cut -c1-$d)\n"
            f"for n in $(seq 1 {m['max']}); do\n"
            "  h=$(printf '%s%s' \"$BLOC\" \"$n\" | sha256sum)\n"
            "  case \"$h\" in\n"
            f"    \"$z\"*) echo \"nonce = $n\"; echo \"$h\"; echo \"{_sur(t('cr.mine.essais'))} $n\"; exit 0 ;;\n"
            "  esac\n"
            "done\n"
            f"echo \"{_sur(t('cr.mine.rien'))}\"\nexit 1\n")


def verifie_sh():
    return ("#!/bin/sh\n"
            f"# {_sur(t('cr.verifie.sh1'))}\n"
            "d=${1:-chaine}\n"
            "n=0; casse=0\n"
            "while [ -f \"$d/bloc_$((n+1)).txt\" ]; do\n"
            "  vrai=$(sha256sum \"$d/bloc_$n.txt\" | cut -c1-64)\n"
            "  note=$(grep '^precedent:' \"$d/bloc_$((n+1)).txt\" | cut -d' ' -f2)\n"
            "  if [ \"$casse\" = 1 ]; then\n"
            f"    echo \"{_sur(t('cr.verifie.maillon'))} $n -> $((n+1)) : ? {_sur(t('cr.verifie.douteux'))}\"\n"
            "  elif [ \"$vrai\" = \"$note\" ]; then\n"
            f"    echo \"{_sur(t('cr.verifie.maillon'))} $n -> $((n+1)) : OK\"\n"
            "  else\n"
            f"    echo \"{_sur(t('cr.verifie.maillon'))} $n -> $((n+1)) : {_sur(t('cr.verifie.casse'))}\"; casse=1\n"
            "  fi\n"
            "  n=$((n+1))\n"
            "done\n"
            f"if [ \"$casse\" = 0 ]; then echo \"{_sur(t('cr.verifie.intacte'))}\"; exit 0; fi\n"
            f"echo \"{_sur(t('cr.verifie.brisee'))}\"; exit 1\n")


def dictionnaire_sh():
    return ("#!/bin/sh\n"
            f"# {_sur(t('cr.dico.sh1'))}\n"
            f"# {_sur(t('cr.dico.sh2'))}\n"
            "while read -r mot; do\n"
            "  e=$(printf '%s' \"$mot\" | sha256sum | cut -c1-64)\n"
            "  qui=$(grep \":$e\\$\" base_fictive.txt | cut -d: -f1)\n"
            f"  if [ -n \"$qui\" ]; then echo \"{_sur(t('cr.dico.trouve'))} $qui -> $mot\"; fi\n"
            "done < dico.txt\n"
            f"echo \"{_sur(t('cr.dico.fin'))}\"\n")


def meubles(state):
    """Ce que le jeu pose dans la Crypte quand elle s'ouvre : {chemin relatif au terrain: texte}."""
    gr = _graine(state)
    m = {"crypte/regle_du_sphinx.txt": t("cr.meuble.regle", nom=state.get("name", "")),
         f"crypte/{CARNET}": t("cr.meuble.carnet") + "\n",
         "crypte/grimoire/cesar.txt": cesar(grimoire("cr.grimoire.cesar"), 3) + "\n",
         "crypte/grimoire/rot13.txt": cesar(grimoire("cr.grimoire.rot13"), 13) + "\n",
         "crypte/grimoire/mystere.txt": cesar(grimoire("cr.grimoire.mystere"), decalage(gr)) + "\n",
         "crypte/base_fictive.txt": "\n".join(base_fictive()) + "\n",
         "crypte/dico.txt": "\n".join(donnees()["dico"]) + "\n",
         "crypte/dictionnaire.sh": dictionnaire_sh(),
         "crypte/parchemin.txt": t("cr.meuble.parchemin", nom=state.get("name", "")) + "\n",
         "crypte/secret.txt": t("cr.meuble.secret") + "\n",
         "crypte/message.txt": t("cr.meuble.message", nom=state.get("name", "")) + "\n",
         "crypte/registre.txt": "\n".join(lignes_registre()) + "\n",
         "crypte/verifie_chaine.sh": verifie_sh(),
         "crypte/mineur.sh": mineur_sh()}
    for x in donnees()["messages"]:
        m[f"crypte/messages/message_{x['n']}.txt"] = message_code(x["n"], t(f"cr.msg.{x['n']}"))
    for i in (1, 2, 3):
        m[f"crypte/grimoires/sort_{i}.txt"] = t(f"cr.sort.{i}") + "\n"
    m["crypte/sceaux.sha256"] = "".join(f"{sha(m[f'crypte/grimoires/sort_{i}.txt'])}  grimoires/sort_{i}.txt\n" for i in (1, 2, 3))
    for nom, txt in chaine(donnees_chaine()).items():
        m["crypte/chaine/" + nom] = txt
        m["crypte/archives/" + nom] = txt
    reg = "\n".join(donnees_chaine()) + "\n"
    tr = tricheur(gr)
    for b in donnees()["biomes"]:
        m[f"crypte/copies/{b}/registre.txt"] = reg if b != tr else reg.replace(t("cr.bloc.2"), t("cr.bloc.2_triche"))
    return m


BESOINS = {"cr0": ["regle_du_sphinx.txt"], "cr1": ["messages/message_1.txt", "messages/message_2.txt"],
           "cr2": ["grimoire/cesar.txt", "grimoire/rot13.txt", "grimoire/mystere.txt"],
           "cr3": ["sceaux.sha256", "grimoires/sort_1.txt", "grimoires/sort_3.txt"],
           "cr4": ["base_fictive.txt", "dico.txt", "dictionnaire.sh"], "cr5": ["parchemin.txt"],
           "cr6": ["secret.txt", "message.txt"], "cr9": ["registre.txt"],
           "cr10": ["verifie_chaine.sh"] + [f"archives/bloc_{k}.txt" for k in range(5)],
           "cr12": ["mineur.sh"], "cr14": ["verifie_chaine.sh"]}


# ---------------------------------------------------------------- gpg (PC) : TOUJOURS --homedir, dans le terrain
def gpg_la():
    return shutil.which("gpg") is not None and not IS_WIN


def trousseau(creature=False):
    g = donnees()["gpg"]
    return dossier() / (g["dossier_creature"] if creature else g["dossier"])


def _gpg(args, creature=False, entree=None, timeout=60):
    d = trousseau(creature)
    try:
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)
        env = {k: v for k, v in os.environ.items() if k != "GNUPGHOME"}
        r = subprocess.run(["gpg", "--homedir", str(d), "--batch", "--no-tty"] + args, input=entree,
                           capture_output=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.SubprocessError):
        return 1, b"", b""


def tuer_agents():
    """Les gpg-agent lancés par gpg pour les trousseaux du terrain s'arrêtent (rien ne traîne après le jeu)."""
    if not shutil.which("gpgconf"):
        return
    for creature in (False, True):
        d = trousseau(creature)
        if d.is_dir():
            try:
                subprocess.run(["gpgconf", "--homedir", str(d), "--kill", "gpg-agent"], capture_output=True, timeout=20)
            except (OSError, subprocess.SubprocessError):
                pass


def a_cle(uid, creature=False, secrete=False):
    code, out, _e = _gpg(["--list-secret-keys" if secrete else "--list-keys", uid], creature)
    return code == 0 and uid.encode() in out


def preparer_creature():
    """La paire de clés d'EXEMPLE de la créature (son trousseau à elle) ; sa clé publique entre dans .trousseau,
    marquée de confiance : l'enfant peut lui écrire, seule elle peut lire."""
    if not gpg_la():
        return False
    g = donnees()["gpg"]
    if not a_cle(g["creature"], True, True):
        _gpg(["--passphrase", "", "--quick-gen-key", g["creature"]], True)
    if not a_cle(g["creature"]):
        code, pub, _e = _gpg(["--armor", "--export", g["creature"]], True)
        if code == 0 and pub:
            _gpg(["--import"], entree=pub)
            code, out, _e = _gpg(["--with-colons", "--fingerprint", g["creature"]])
            fpr = next((l.split(":")[9] for l in out.decode().splitlines() if l.startswith("fpr:")), None)
            if fpr:
                _gpg(["--import-ownertrust"], entree=f"{fpr}:6:\n".encode())
    return a_cle(g["creature"])


def preparer_echanges():
    """B5 : un échange signé par la créature (vrai) et sa copie trafiquée (faux : le sceau ne colle plus)."""
    if not preparer_creature():
        return False
    vrai = t("cr.echange.vrai") + "\n"
    code, signe, _e = _gpg(["--clearsign"], True, entree=vrai.encode("utf-8"))
    if code != 0:
        return False
    s = signe.decode("utf-8")
    _ecrire("crypte/echanges/vrai.txt.asc", s)
    _ecrire("crypte/echanges/faux.txt.asc", s.replace(t("cr.echange.vrai"), t("cr.echange.faux")))
    return True


def verifie_signature(chemin):
    """(ok, uid) : la signature d'un fichier clairsigné, vérifiée dans .trousseau."""
    code, _o, err = _gpg(["--status-fd", "2", "--verify", str(chemin)])
    m = re.search(rb"\[GNUPG:\] GOODSIG \S+ (.*)", err)
    return code == 0 and m is not None, (m.group(1).decode("utf-8", "replace") if m else "")


# ---------------------------------------------------------------- le carnet de bord (B6, le registre du recensement)
def carnet_de_bord(state):
    """Le carnet de bord infalsifiable : une chaîne dont chaque bloc est une étape réussie du parcours."""
    from . import histoire
    h = histoire.h_(state)
    lignes = [t("cr.bord.debut", nom=state.get("name", ""))]
    for lid in h.get("faits", []):
        if lid in LECONS:
            lignes.append(t("cr.bord.lecon", titre=t(LECONS[lid]["titre"])))
    for c in histoire.CHAPITRES:
        if histoire.fini(state, c["id"]):
            lignes.append(t("cr.bord.chapitre", chapitre=histoire.nom_chapitre(c["id"])))
    return chaine(lignes)


# ---------------------------------------------------------------- meubler : appelé à chaque tour pendant une leçon
def meubler(state, lid, step):
    c = c_(state)
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists() and "crypte/" + rel in tous:
            _ecrire("crypte/" + rel, tous["crypte/" + rel])
    if lid == "cr3" and not _fait(c, "altere"):        # un glitch a touché un grimoire : son sceau ne colle plus
        _ecrire("crypte/grimoires/sort_2.txt", t("cr.sort.2_altere") + "\n")
    if lid == "cr9" and step >= 2 and not _fait(c, "registre"):     # B1 : une ligne change, sans trace
        txt = _lire("crypte/registre.txt")
        _ecrire("crypte/registre.txt", txt.replace(t("cr.registre.2"), t("cr.registre.2_triche")))
    if lid == "cr10":
        for k in range(donnees()["chaine"]["blocs"]):
            if not (d / "chaine" / f"bloc_{k}.txt").exists():
                _ecrire(f"crypte/chaine/bloc_{k}.txt", tous[f"crypte/archives/bloc_{k}.txt"])
        if _chaine_cassee() and not dans_carnet("triche", "vu"):
            noter("triche", "chaine (vu)")                 # la chaîne a été brisée une fois : on peut la réparer
        if (state.get("indice_lecon") or "") and "indice:cr10" not in c["faits"]:
            c["faits"].append("indice:cr10")              # un indice a été montré : la variante rare attendra
    if lid in ("cr6", "cr13") and gpg_la():
        preparer_creature()
        if lid == "cr13" and not (d / "echanges" / "faux.txt.asc").exists():
            preparer_echanges()
        if lid == "cr13" and not a_cle(donnees()["gpg"]["moi"], secrete=True):
            _gpg(["--passphrase", "", "--quick-gen-key", donnees()["gpg"]["moi"]])
        c["agents"] = True
    elif c.get("agents"):
        tuer_agents()
        c["agents"] = False
    if lid == "cr14" and not _fait(c, "bord"):
        for nom, txt in carnet_de_bord(state).items():
            _ecrire("crypte/carnet_de_bord/" + nom, txt)
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans, la réponse vient toujours d'une commande."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = c_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("cr.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("cr.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


def _blocs(rel="chaine"):
    d = dossier() / rel
    out = []
    k = 0
    while (d / f"bloc_{k}.txt").is_file():
        out.append(_lire(f"crypte/{rel}/bloc_{k}.txt").replace("\r\n", "\n"))
        k += 1
    return out


def _chaine_cassee(rel="chaine"):
    return any(e != "ok" for _k, e in verifier_chaine(_blocs(rel)))


def _fs_chaine_reparee():
    b = _blocs()
    return dans_carnet("triche", "vu") and len(b) >= donnees()["chaine"]["blocs"] and not _chaine_cassee()


def _fs_openssl():
    try:
        if (dossier() / "parchemin.enc").read_bytes()[:8] != b"Salted__":
            return False
        r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(dossier() / "parchemin.enc"),
                            "-pass", "pass:" + CLE], capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _fs_gpg_fichier(nom, debut):
    try:
        b = (dossier() / nom).read_bytes()
    except OSError:
        return False
    return b.startswith(debut) if debut else bool(b) and b[0] & 0x80 != 0


FS = {
    "cr_demasque": lambda: dans_carnet("demasque"),
    "cr_roue": lambda: dans_carnet("roue"),
    "cr_donne_parchemin": lambda: dans_carnet("donne", sujet="parchemin.enc"),
    "cr_parchemin": _fs_openssl,
    "cr_cle": lambda: a_cle(donnees()["gpg"]["moi"], secrete=True),
    "cr_secret_gpg": lambda: _fs_gpg_fichier("secret.gpg", None),
    "cr_donne_secret": lambda: dans_carnet("donne", sujet="secret.gpg"),
    "cr_message_asc": lambda: _fs_gpg_fichier("message.txt.asc", b"-----BEGIN PGP SIGNED MESSAGE-----"),
    "cr_de": lambda: dans_carnet("de"),
    "cr_quiz": lambda: dans_carnet("quiz"),
    "cr_ajout": lambda: len([x for x in _lire("crypte/registre.txt").splitlines() if x.strip()]) > len(lignes_registre()),
    "cr_triche": lambda: _chaine_cassee(),
    "cr_reparee": _fs_chaine_reparee,
    "cr_consensus": lambda: dans_carnet("consensus"),
    "cr_echange": lambda: bool(_lire("crypte/echange.txt").strip()),
    "cr_echange_asc": lambda: _fs_gpg_fichier("echange.txt.asc", b"-----BEGIN PGP SIGNED MESSAGE-----"),
    "cr_signe": lambda: dans_carnet("signe"),
    "cr_recensement": lambda: dans_carnet("recensement"),
}
CREE = {"cr_parchemin": "crypte/parchemin.enc", "cr_secret_gpg": "crypte/secret.gpg", "cr_echange": "crypte/echange.txt"}

CLE = donnees()["cle_exemple"]
MOI = donnees()["gpg"]["moi"]
CREATURE = donnees()["gpg"]["creature"]
HOMEDIR = "--homedir " + donnees()["gpg"]["dossier"]
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
CR = r"^(tg\s+)?crypte\s+"
GPG = r"^gpg2?\b(?=.*--homedir\s+\S*\.trousseau\b)"
CHIFFRE = f"openssl enc -aes-256-cbc -pbkdf2 -in parchemin.txt -out parchemin.enc -pass pass:{CLE}"
GENKEY = f'gpg {HOMEDIR} --batch --passphrase "" --quick-gen-key {MOI}'
CHIFFRE_GPG = f"gpg {HOMEDIR} -e -r {CREATURE} -o secret.gpg secret.txt"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LECONS = {
    # la porte du sphinx
    "cr0": {"titre": "hist.cr0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "crypte"}), "cmd": "cd ~/terrain_terminagotchi/crypte", "ici": "crypte",
         "bravo": ("hist.entree.bravo", {"piece": "crypte"})},
        _n("cr0", 1, cmd="ls", re=LS, ou="crypte"),
        _n("cr0", 2, cmd="cat regle_du_sphinx.txt", re=LIRE + r".*regle_du_sphinx"),
    ]},
    # K1 cacher n'est pas chiffrer
    "cr1": {"titre": "hist.cr1.titre", "skill": None, "steps": [
        _n("cr1", 0, cmd="echo bonjour | base64", re=r"^(echo|printf)\b.*\|\s*base64\s*$", win=False, ou="crypte"),
        _n("cr1", 1, cmd="base64 -d messages/message_1.txt", re=r"^(base64\s+(-d|--decode)\b.*message_1|cat\b.*message_1.*\|\s*base64\s+(-d|--decode))",
           win=False),
        _n("cr1", 2, cmd="xxd -r -p messages/message_2.txt", re=r"^(xxd\b(?=.*-r)(?=.*-p).*message_2|cat\b.*message_2.*\|\s*xxd\b(?=.*-r))",
           outil="xxd", win=False),
        _n("cr1", 3, cmd="crypte demasque", fs="cr_demasque"),
    ]},
    # K2 les codes anciens (César, ROT13, fréquences ; pont modulo)
    "cr2": {"titre": "hist.cr2.titre", "skill": None, "steps": [
        _n("cr2", 0, cmd="echo bonjour | tr 'a-z' 'd-za-c'", re=r"^(echo|printf)\b.*\|\s*tr\s+['\"]?a-z['\"]?\s+['\"]?d-za-c",
           win=False, ou="crypte"),
        _n("cr2", 1, cmd="tr 'd-za-c' 'a-z' < grimoire/cesar.txt",
           re=r"(^tr\b.*d-za-c['\"]?\s+['\"]?a-z.*<\s*\S*cesar|^cat\b.*cesar.*\|\s*tr\b.*d-za-c['\"]?\s+['\"]?a-z)", win=False),
        _n("cr2", 2, cmd="tr 'a-z' 'n-za-m' < grimoire/rot13.txt",
           re=r"(^tr\b.*(a-z['\"]?\s+['\"]?n-za-m|n-za-m['\"]?\s+['\"]?a-z).*<\s*\S*rot13|^cat\b.*rot13.*\|\s*tr\b.*n-za-m)", win=False),
        _n("cr2", 3, cmd="grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3",
           re=r"^(grep\s+-\w*o\b.*mystere|fold\b.*mystere|cat\b.*mystere.*\|\s*(grep\s+-\w*o|fold)\b).*\|\s*sort\b.*\|\s*uniq\s+-c",
           win=False),
        _n("cr2", 4, cmd="crypte roue ?", fs="cr_roue"),
    ]},
    # K3 les empreintes
    "cr3": {"titre": "hist.cr3.titre", "skill": None, "steps": [
        _n("cr3", 0, cmd="echo -n a | sha256sum", re=r"^(echo\s+-n|printf)\s+['\"]?a['\"]?\s*\|\s*sha256sum\b", win=False, ou="crypte"),
        _n("cr3", 1, cmd="echo -n b | sha256sum", re=r"^(echo\s+-n|printf)\s+['\"]?b['\"]?\s*\|\s*sha256sum\b", win=False),
        _n("cr3", 2, cmd="crypte avalanche chat chas", re=CR + r"avalanche\s+\S+\s+\S+"),
        _n("cr3", 3, cmd="sha256sum -c sceaux.sha256", re=r"^sha256sum\s+(-c|--check)\b.*sceaux", echoue=True, win=False),
    ]},
    # K4 les mots de passe (une base FICTIVE ; jamais un vrai mot de passe)
    "cr4": {"titre": "hist.cr4.titre", "skill": None, "steps": [
        _n("cr4", 0, cmd="cat base_fictive.txt", re=LIRE + r".*base_fictive", ou="crypte"),
        _n("cr4", 1, cmd="cat dictionnaire.sh", re=LIRE + r".*dictionnaire\.sh"),
        _n("cr4", 2, cmd="sh dictionnaire.sh", re=r"^((sh|bash)\s+|\./)\S*dictionnaire\.sh\b", win=False),
        _n("cr4", 3, cmd="openssl passwd -6 licorne", re=r"^openssl\s+passwd\s+-6\b", outil="openssl"),
    ]},
    # K5 le coffre à une clé (openssl, une clé d'EXEMPLE)
    "cr5": {"titre": "hist.cr5.titre", "skill": None, "steps": [
        _n("cr5", 0, cmd="cat parchemin.txt", re=LIRE + r".*parchemin\.txt", ou="crypte"),
        _n("cr5", 1, cmd=CHIFFRE, fs="cr_parchemin", outil="openssl"),
        _n("cr5", 2, cmd="head -c 8 parchemin.enc", re=r"^(head\s+-c\s*8\b.*parchemin\.enc|(xxd|od|hexdump)\b.*parchemin\.enc)",
           outil="openssl", win=False),
        _n("cr5", 3, cmd="crypte donne parchemin.enc", fs="cr_donne_parchemin", outil="openssl"),
    ]},
    # K6 le cadenas ouvert (échange de clés, clé publique, signature ; gpg dans le terrain)
    "cr6": {"titre": "hist.cr6.titre", "skill": None, "steps": [
        _n("cr6", 0, cmd="crypte peintures", re=CR + r"peintures?\b", ou="crypte"),
        _n("cr6", 1, cmd="echo $((5**6 % 23))", re=r"^echo\s+\$\(\(\s*5\s*(\*\*\s*6|(\*\s*5\s*){5})\s*%\s*23\s*\)\)", win=False),
        _n("cr6", 2, cmd=GENKEY, fs="cr_cle", outil="gpg"),
        _n("cr6", 3, cmd=CHIFFRE_GPG, fs="cr_secret_gpg", outil="gpg"),
        _n("cr6", 4, cmd="crypte donne secret.gpg", fs="cr_donne_secret", outil="gpg"),
        _n("cr6", 5, cmd=f"gpg {HOMEDIR} --clearsign message.txt", fs="cr_message_asc", outil="gpg"),
        _n("cr6", 6, cmd=f"gpg {HOMEDIR} --verify message.txt.asc", re=GPG + r".*--verify\b.*message\.txt\.asc", outil="gpg"),
    ]},
    # K7 le hasard
    "cr7": {"titre": "hist.cr7.titre", "skill": None, "steps": [
        _n("cr7", 0, cmd="head -c 16 /dev/urandom | xxd", re=r"^head\s+-c\s*16\s+/dev/u?random\s*\|\s*(xxd|od|base64|hexdump)\b",
           outil="xxd", win=False, ou="crypte"),
        _n("cr7", 1, cmd="openssl rand -hex 16", re=r"^openssl\s+rand\s+-hex\s+16\s*$", outil="openssl"),
        _n("cr7", 2, cmd="crypte de", re=CR + r"de\s*$"),
        _n("cr7", 3, cmd="crypte de ?", fs="cr_de"),
    ]},
    # K8 demain (quantique, bout en bout, métadonnées) : vrai, faux, ou on ne sait pas encore
    "cr8": {"titre": "hist.cr8.titre", "skill": None, "steps": [
        _n("cr8", 0, cmd="crypte quiz", re=CR + r"quiz\s*$", ou="crypte"),
        _n("cr8", 1, cmd="crypte quiz ? ? ? ? ? ?", fs="cr_quiz"),
    ]},
    # B1 le grand registre
    "cr9": {"titre": "hist.cr9.titre", "skill": None, "steps": [
        _n("cr9", 0, cmd="cat registre.txt", re=LIRE + r".*registre\.txt", ou="crypte"),
        _n("cr9", 1, cmd='echo "Lune donne 2 plumes a Pixel" >> registre.txt', fs="cr_ajout", win=False),
        _n("cr9", 2, cmd="crypte registre", re=CR + r"registre\s*$"),
    ]},
    # B2 la chaîne d'empreintes (elle se brise ; on la répare)
    "cr10": {"titre": "hist.cr10.titre", "skill": None, "steps": [
        _n("cr10", 0, cmd="cat chaine/bloc_1.txt", re=LIRE + r".*chaine/bloc_1", ou="crypte"),
        _n("cr10", 1, cmd="sha256sum chaine/bloc_0.txt", re=r"^sha256sum\b.*chaine/bloc_0", win=False),
        _n("cr10", 2, cmd="sh verifie_chaine.sh", re=r"^((sh|bash)\s+|\./)\S*verifie_chaine\.sh\s*$", win=False),
        _n("cr10", 3, cmd="echo triche >> chaine/bloc_1.txt", fs="cr_triche", win=False),
        _n("cr10", 4, cmd="sh verifie_chaine.sh", re=r"^((sh|bash)\s+|\./)\S*verifie_chaine\.sh\s*$", echoue=True, win=False),
        _n("cr10", 5, cmd="cp archives/bloc_1.txt chaine/", fs="cr_reparee", win=False),
        _n("cr10", 6, cmd="crypte chaine", re=CR + r"chaine\s*$"),
    ]},
    # B3 les copies des 9 biomes (consensus)
    "cr11": {"titre": "hist.cr11.titre", "skill": None, "steps": [
        _n("cr11", 0, cmd="sha256sum copies/*/registre.txt", re=r"^sha256sum\b.*copies/", win=False, ou="crypte"),
        _n("cr11", 1, cmd="sha256sum copies/*/registre.txt | cut -c1-64 | sort | uniq -c",
           re=r"^sha256sum\b.*copies.*\|\s*(cut|awk)\b.*\|\s*sort\b.*\|\s*uniq\s+-c", win=False),
        _n("cr11", 2, cmd="diff copies/feu/registre.txt copies/?/registre.txt", re=r"^diff\b.*copies/.*copies/", echoue=True,
           win=False),
        _n("cr11", 3, cmd="crypte consensus ?", fs="cr_consensus"),
    ]},
    # B4 la preuve de travail (un minage minuscule, qui s'arrête seul)
    "cr12": {"titre": "hist.cr12.titre", "skill": None, "steps": [
        _n("cr12", 0, cmd="cat mineur.sh", re=LIRE + r".*mineur\.sh", ou="crypte"),
        _n("cr12", 1, cmd="sh mineur.sh 2", re=r"^((sh|bash)\s+|\./)\S*mineur\.sh\s+2\s*$", win=False),
        _n("cr12", 2, cmd="time sh mineur.sh 3", re=r"^(time\s+((sh|bash)\s+|\./)\S*mineur\.sh\s+3|(tg\s+)?crypte\s+mine\s+3)\b", win=False),
        _n("cr12", 3, cmd="crypte mine", re=CR + r"mine\s*$"),
    ]},
    # B5 les échanges signés
    "cr13": {"titre": "hist.cr13.titre", "skill": None, "steps": [
        _n("cr13", 0, cmd='echo "Pixel donne 2 glands a Lune" > echange.txt', fs="cr_echange", ou="crypte", outil="gpg"),
        _n("cr13", 1, cmd=f"gpg {HOMEDIR} --clearsign echange.txt", fs="cr_echange_asc", outil="gpg"),
        _n("cr13", 2, cmd=f"gpg {HOMEDIR} --verify echanges/faux.txt.asc", re=GPG + r".*--verify\b.*faux\.txt\.asc", echoue=True,
           outil="gpg"),
        _n("cr13", 3, cmd="crypte signe echange.txt.asc", fs="cr_signe", outil="gpg"),
    ]},
    # B6 les applications (explication technique uniquement) et le carnet de bord infalsifiable
    "cr14": {"titre": "hist.cr14.titre", "skill": None, "steps": [
        _n("cr14", 0, cmd="crypte vitrine", re=CR + r"vitrine\b", ou="crypte"),
        _n("cr14", 1, cmd="grep -h donnees chaine/bloc_*.txt", re=r"^(grep|cat)\b.*chaine", win=False),
        _n("cr14", 2, cmd="sh verifie_chaine.sh carnet_de_bord", re=r"^((sh|bash)\s+|\./)\S*verifie_chaine\.sh\s+\S*carnet_de_bord",
           win=False),
        _n("cr14", 3, cmd="crypte recensement", fs="cr_recensement", exploit="crypte.b6"),
    ]},
}
CHAPITRE = {"id": "crypte", "n": 13, "piece": "crypte", "famille": "Morts-vivants", "monde": True,
            "lecons": [f"cr{i}" for i in range(15)], "objet": "sceau_miniature", "titre": "sphinx_de_la_crypte"}


# ================================================================ l'arbre du Carrefour : quand la Crypte s'ouvre
def _besoin():
    from . import programme
    P = programme.donnees()
    m = next((x for x in P.get("mondes", []) if x["id"] == "crypte"), {})
    besoin = []
    for n in m.get("requis", []):
        besoin += [c for c in P.get("tronc", {}).get(n, []) if c not in besoin]
    return besoin


def ouvert(state):
    from . import histoire
    return all(histoire.fini(state, c) for c in _besoin())


def manque(state):
    from . import histoire
    return [histoire.nom_chapitre(c) for c in _besoin() if not histoire.fini(state, c)]


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "crypte" in deja or histoire.fini(state, "crypte") or not ouvert(state):
        return False
    deja.append("crypte")
    core.log(state, t("cr.ouvert.log"))
    core.say(state, histoire.dire(state, "cr.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
SANS_HOMEDIR = re.compile(r"(^|[;&|]\s*)gpg2?\s(?!.*--homedir)")


def indice(step, tapees):
    """Un indice de la Crypte : un trou « ? » recopié, gpg sans --homedir, la clé d'exemple oubliée, une mauvaise
    roue, une réponse fausse au dé, au quiz, au consensus."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(SANS_HOMEDIR.search(l) for l in lignes):
        return t("cr.indice.homedir")
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("cr.indice.sudo")
    if "?" in cmd.split() and any(re.search(r"(^|\s|/)\?(\s|/|$)|…|<", l) for l in lignes if not l.startswith("tr ")):
        return t("cr.indice.trou")
    for et, cle in (("roue", "cr.indice.roue"), ("de", "cr.indice.de"), ("quiz", "cr.indice.quiz"),
                    ("consensus", "cr.indice.consensus")):
        if cmd.startswith(f"crypte {et} ?"):
            der = [l for l in carnet().splitlines() if l.startswith(f"[{et}]")]
            if der and der[-1].endswith("(faux)"):
                return t(cle)
            if lignes and re.match(CR + et + r"\s*$", lignes[-1]):
                return t(cle + "_aide")
    if cmd.startswith("openssl enc") and any("pass:" in l and CLE not in l for l in lignes):
        return t("cr.indice.cle")
    if cmd.startswith("cp archives") and any(re.match(r"^((sh|bash)\s+|\./)\S*verifie_chaine", l) for l in lignes):
        return t("cr.indice.reparer")
    if cmd == "echo triche >> chaine/bloc_1.txt" and any(re.match(r"^echo\b.*>\s*chaine/", l) and ">>" not in l for l in lignes):
        return t("cr.indice.ajouter")
    if cmd.startswith("crypte donne") and any(l.startswith("crypte donne") for l in lignes):
        return t("cr.indice.donne")
    return None


def surveiller(state, lignes):
    """À chaque tour : gpg tapé SANS --homedir (il viserait le vrai trousseau de l'utilisateur) : la créature prévient.
    Pendant une leçon de la Crypte, c'est l'indice de l'étape qui le dit (une seule fois)."""
    from . import histoire
    les, _e = histoire.lecon_courante(state)
    if les and les["id"] in LECONS:
        return False
    for l in lignes or []:
        l = (l or "").strip()
        if SANS_HOMEDIR.search(l) and re.search(r"gpg2?\s+(-\w*[esdk]|--(gen|quick|sign|clearsign|encrypt|decrypt|import|"
                                                r"export|full|delete))", l):
            core.say(state, t("cr.indice.homedir"), 16)
            core.terminal(state, "⚠ " + t("cr.indice.homedir"))
            return True
    return False


# ================================================================ les commandes du jeu : tg crypte …
def _c(n):
    return fg(n)


def roue_lignes(k, couleur=True):
    """La roue de César en caractères : l'alphabet clair et, en dessous, l'alphabet décalé de k."""
    k %= 26
    haut = " ".join(ALPHA)
    bas = " ".join(cesar(ALPHA, k))
    if couleur:
        return [f"  {DIM}{t('cr.roue.clair'):<9}{RESET} {haut}", f"  {_c(213)}{t('cr.roue.code'):<9}{RESET} {_c(213)}{bas}{RESET}",
                f"  {DIM}a → {ALPHA[k]} : +{k} (mod 26){RESET}"]
    return [f"  {t('cr.roue.clair'):<9} {haut}", f"  {t('cr.roue.code'):<9} {bas}", f"  a → {ALPHA[k]} : +{k} (mod 26)"]


def lignes_roue(state, arg):
    gr = _graine(state)
    k = decalage(gr)
    mystere = _lire("crypte/grimoire/mystere.txt").strip() or cesar(grimoire("cr.grimoire.mystere"), k)
    if not arg:
        return [f" {_c(213)}{BOLD}🎡 " + t("cr.roue.titre") + RESET, ""] + roue_lignes(3) + ["", "  " + t("cr.roue.aide")]
    try:
        n = int(arg) % 26
    except ValueError:
        return [t("cr.roue.aide")]
    essai = cesar(mystere, -n)
    out = [f" {_c(213)}{BOLD}🎡 " + t("cr.roue.titre") + RESET, ""] + roue_lignes(n) + ["", "  " + essai[:160]]
    if n == k:
        noter("roue", f"{n} (ok)")
        out += ["", f"  {_c(78)}✔ " + t("cr.roue.ok", n=n) + RESET]
    else:
        noter("roue", f"{n} (faux)")
        out += ["", f"  {_c(203)}✖ " + t("cr.roue.faux") + RESET]
    return out


def lignes_demasque():
    out = [f" {_c(213)}{BOLD}🎭 " + t("cr.demasque.titre") + RESET, ""]
    for x in donnees()["messages"]:
        brut_ = _lire(f"crypte/messages/message_{x['n']}.txt").strip()
        try:
            if x["code"] == "base64":
                clair = base64.b64decode(brut_).decode("utf-8")
            elif x["code"] == "hex":
                clair = bytes.fromhex(brut_).decode("utf-8")
            else:
                clair = codecs.decode(brut_, "rot13")
        except (ValueError, UnicodeDecodeError):
            clair = "?"
        out.append(f"  {BOLD}{x['n']}.{RESET} {DIM}{x['code']:<7}{RESET} {brut_[:28]}{'…' if len(brut_) > 28 else ''}")
        out.append(f"     → {clair}")
    noter("demasque", "5 (ok)")
    return out + ["", f"  {_c(78)}" + t("cr.demasque.morale") + RESET]


def lignes_avalanche(a, b):
    ha, hb = sha(a), sha(b)
    marque = "".join("^" if x != y else " " for x, y in zip(ha, hb))
    noter("avalanche", f"{a} {b} (ok)")
    return [f" {_c(213)}{BOLD}🏔 " + t("cr.avalanche.titre") + RESET, "",
            f"  {a:<10} {ha}", f"  {b:<10} {hb}", f"  {'':<10} {_c(203)}{marque}{RESET}", "",
            "  " + t("cr.avalanche.compte", lettres=lettres_differentes(ha, hb), bits=bits_differents(ha, hb)),
            "  " + t("cr.avalanche.morale")]


def lignes_donne(state, nom):
    if not nom:
        return [t("cr.donne.aide")]
    p = dossier() / nom
    if not p.is_file():
        p = Path(os.getcwd()) / nom
    if not p.is_file():
        return [t("cr.inconnu", nom=nom)]
    b = p.read_bytes()
    if b[:8] == b"Salted__":
        try:
            r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(p), "-pass", "pass:" + CLE],
                               capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return [t("cr.donne.outil", outil="openssl")]
        if r.returncode != 0:
            noter("donne", f"{p.name} (faux)")
            return [f" {_c(203)}✖ " + t("cr.donne.ferme") + RESET]
        noter("donne", f"{p.name} (ok)")
        return [f" {_c(78)}🔓 " + t("cr.donne.ouvert") + RESET, "  " + r.stdout.decode("utf-8", "replace").strip(),
                "", "  " + t("cr.donne.probleme")]
    if b and b[0] & 0x80:
        if not gpg_la():
            return [t("cr.donne.outil", outil="gpg")]
        preparer_creature()
        code, out, _e = _gpg(["-d", str(p)], True)
        if code != 0:
            noter("donne", f"{p.name} (faux)")
            return [f" {_c(203)}✖ " + t("cr.donne.pas_pour_moi") + RESET]
        noter("donne", f"{p.name} (ok)")
        return [f" {_c(78)}🔓 " + t("cr.donne.gpg") + RESET, "  " + out.decode("utf-8", "replace").strip(), "",
                "  " + t("cr.donne.privee")]
    return [t("cr.donne.clair")]


def lignes_peintures():
    p = peintures()
    return [f" {_c(213)}{BOLD}🎨 " + t("cr.peintures.titre") + RESET, "",
            "  " + t("cr.peintures.public", p=p["p"], g=p["g"]),
            "  " + t("cr.peintures.moi", a=p["a"], g=p["g"], p=p["p"], A=p["A"]),
            "  " + t("cr.peintures.elle", b=p["b"], g=p["g"], p=p["p"], B=p["B"]),
            "  " + t("cr.peintures.melange", s=p["s1"], A=p["A"], B=p["B"], a=p["a"], b=p["b"], p=p["p"]),
            "", f"  {_c(78)}" + t("cr.peintures.morale") + RESET, f"  {DIM}" + t("cr.peintures.grands") + RESET]


def lignes_de(state, arg):
    gr = _graine(state)
    d = donnees()["de"]
    suite = de_suite(gr, d["montres"] + 1)
    out = [f" {_c(213)}{BOLD}🎲 " + t("cr.de.titre") + RESET, "", "  " + "  ".join(map(str, suite[:-1])) + "  ?", "",
           "  " + t("cr.de.regle", a=d["a"], c=d["c"], m=d["m"])]
    if not arg:
        return out + ["  " + t("cr.de.aide")]
    try:
        n = int(arg)
    except ValueError:
        return out + ["  " + t("cr.de.aide")]
    if n == suite[-1]:
        noter("de", f"{n} (ok)")
        return out + ["", f"  {_c(78)}✔ " + t("cr.de.ok") + RESET]
    noter("de", f"{n} (faux)")
    return out + ["", f"  {_c(203)}✖ " + t("cr.de.faux") + RESET]


def lignes_quiz(state, reponses):
    gr = _graine(state)
    q = quiz(gr)
    if not reponses:
        out = [f" {_c(213)}{BOLD}🔮 " + t("cr.quiz.titre") + RESET, ""]
        for n, i, _r in q:
            out.append(f"  {BOLD}{n}.{RESET} " + t("cr.quiz." + i))
        return out + ["", "  " + t("cr.quiz.aide")]
    r = [x.lower()[:1] for x in reponses]
    bonnes = bonnes_reponses(gr)
    if len(r) != len(bonnes) or any(x not in "vfs" for x in r):
        return [t("cr.quiz.aide")]
    justes = sum(1 for x, y in zip(r, bonnes) if x == y)
    if justes == len(bonnes):
        noter("quiz", " ".join(r) + " (ok)")
        out = [f" {_c(78)}✔ " + t("cr.quiz.ok") + RESET]
    else:
        noter("quiz", " ".join(r) + " (faux)")
        out = [f" {_c(203)}✖ " + t("cr.quiz.faux", n=justes, total=len(bonnes)) + RESET]
    for (n, i, rep), x in zip(q, r):
        if x == rep:
            out.append(f"  {_c(78)}✔{RESET} {n}. " + t("cr.quiz." + i + ".pourquoi"))
    return out


def lignes_registre_ecran():
    actuel = [x for x in _lire("crypte/registre.txt").splitlines() if x.strip()]
    origine = lignes_registre()
    out = [f" {_c(213)}{BOLD}📜 " + t("cr.registre.titre") + RESET, ""]
    for i, l in enumerate(actuel):
        change = i < len(origine) and l != origine[i]
        out.append(f"  {(_c(203) + '≠') if change else ' '}{RESET} {i + 1}. {l}")
    noter("registre", "lu (ok)")
    return out + ["", "  " + t("cr.registre.morale")]


def dessin_chaine(etats, couleur=True):
    """La chaîne en caractères : [0]━[1]━✖━[2]… (les maillons cassés rouges, les douteux gris)."""
    out = "  [0]"
    for k, e in etats:
        if e == "ok":
            lien = f"{_c(78)}━━{RESET}" if couleur else "━━"
        elif e == "casse":
            lien = f"{_c(203)}━✖━{RESET}" if couleur else "━✖━"
        else:
            lien = f"{DIM}┄?┄{RESET}" if couleur else "┄?┄"
        out += f"{lien}[{k + 1}]"
    return out


def lignes_chaine(state, rel="chaine"):
    blocs = _blocs(rel)
    if len(blocs) < 2:
        return [t("cr.chaine.vide", dossier=rel)]
    etats = verifier_chaine(blocs)
    out = [f" {_c(213)}{BOLD}⛓ " + t("cr.chaine.titre") + RESET, "", dessin_chaine(etats), ""]
    for k, e in etats:
        out.append(f"  {t('cr.verifie.maillon')} {k} → {k + 1} : " + t("cr.chaine." + e))
    if all(e == "ok" for _k, e in etats):
        noter("chaine", f"{rel} intacte (ok)")
        out += ["", f"  {_c(78)}✔ " + t("cr.chaine.intacte") + RESET]
        c = c_(state)
        from . import histoire
        les, _e = histoire.lecon_courante(state)
        if rel == "chaine" and les and les["id"] == "cr10" and dans_carnet("triche", "vu"):
            if "indice:cr10" in c["faits"] or state.get("indice_lecon"):
                out.append("  " + t("cr.chaine.avec_indice"))
            else:
                from . import recompenses
                msg = recompenses.exploit(state, "crypte.chaine")
                if msg:
                    core.log(state, msg)
                    core.say(state, msg, 16)
                    out.append(f"  {_c(213)}✨ " + msg + RESET)
    else:
        noter("chaine", f"{rel} brisee (brisee)")
        out += ["", f"  {_c(203)}✖ " + t("cr.chaine.brisee") + RESET]
    return out


def lignes_consensus(state, arg):
    gr = _graine(state)
    if not arg:
        return [t("cr.consensus.aide")]
    b = arg.lower()
    if b not in donnees()["biomes"]:
        return [t("cr.consensus.inconnu", liste=", ".join(donnees()["biomes"]))]
    if b == tricheur(gr):
        noter("consensus", f"{b} (ok)")
        return [f" {_c(78)}✔ " + t("cr.consensus.ok", biome=b) + RESET, "  " + t("cr.consensus.morale")]
    noter("consensus", f"{b} (faux)")
    return [f" {_c(203)}✖ " + t("cr.consensus.faux", biome=b) + RESET]


def lignes_mine(arg=None):
    m = donnees()["mine"]
    out = [f" {_c(213)}{BOLD}⛏ " + t("cr.mine.titre") + RESET, "", f"  {DIM}{t('cr.mine.entete')}{RESET}"]
    zs = [int(arg)] if arg and arg.isdigit() and 1 <= int(arg) <= 4 else range(1, m["table"] + 1)
    for z in zs:
        if z <= 4:
            t0 = time.time()
            n = miner(m["donnees"], z)
            ms = (time.time() - t0) * 1000
            out.append(f"  {'0' * z:<6} {16 ** z:>9}   {n if n else '—':>8}   {ms:7.0f} ms")
        else:
            out.append(f"  {'0' * z:<6} {16 ** z:>9}   {'…':>8}   " + t("cr.mine.trop_long"))
    noter("mine", "table (ok)")
    return out + ["", "  " + t("cr.mine.morale"), f"  {DIM}" + t("cr.mine.energie") + RESET]


def lignes_signe(state, nom):
    if not gpg_la():
        return [t("cr.donne.outil", outil="gpg")]
    p = dossier() / (nom or "echange.txt.asc")
    if not p.is_file():
        return [t("cr.inconnu", nom=nom or "echange.txt.asc")]
    ok, uid = verifie_signature(p)
    if not ok:
        noter("signe", f"{p.name} (refuse)")
        return [f" {_c(203)}✖ " + t("cr.signe.refuse") + RESET]
    if MOI not in uid:
        noter("signe", f"{p.name} (pas_moi)")
        return [f" {_c(203)}✖ " + t("cr.signe.pas_moi", uid=uid) + RESET]
    blocs = _blocs()
    texte = p.read_text(encoding="utf-8", errors="replace")
    ligne = next((x for x in texte.splitlines() if x.strip() and not x.startswith(("-----", "Hash:"))), "?")
    if blocs and not _chaine_cassee():
        k = len(blocs)
        txt = bloc_texte(k, sha(blocs[-1]), f"{ligne} [{t('cr.signe.par', uid=uid)}]")
        _ecrire(f"crypte/chaine/bloc_{k}.txt", txt)
    noter("signe", f"{p.name} (ok)")
    return [f" {_c(78)}✔ " + t("cr.signe.ok", uid=uid) + RESET, "  " + t("cr.signe.ajoute", ligne=ligne)]


def lignes_vitrine():
    out = [f" {_c(213)}{BOLD}🏛 " + t("cr.vitrine.titre") + RESET, "", f"  {DIM}" + t("cr.vitrine.regle") + RESET, ""]
    for v in donnees()["vitrine"]:
        out.append(f"  {BOLD}{t('cr.vitrine.' + v)}{RESET}")
        out.append("     " + t(f"cr.vitrine.{v}.comment"))
        out.append(f"     {_c(78)}🧱 {t(f'cr.vitrine.{v}.briques')}{RESET}")
    noter("vitrine", "lue (ok)")
    return out + ["", "  " + t("cr.vitrine.anonyme"), f"  {_c(203)}" + t("cr.vitrine.privee") + RESET]


def lignes_recensement(state):
    blocs = _blocs("carnet_de_bord")
    if len(blocs) < 2:
        return [t("cr.chaine.vide", dossier="carnet_de_bord")]
    etats = verifier_chaine(blocs)
    out = [f" {_c(213)}{BOLD}📖 " + t("cr.recensement.titre") + RESET, "", dessin_chaine(etats), ""]
    if all(e == "ok" for _k, e in etats):
        noter("recensement", f"{len(blocs)} (ok)")
        return out + [f"  {_c(78)}✔ " + t("cr.recensement.ok", n=len(blocs)) + RESET, "  " + t("cr.recensement.morale")]
    noter("recensement", "brise (brise)")
    return out + [f"  {_c(203)}✖ " + t("cr.recensement.brise") + RESET]


CRYPTE = ['        ╔═══════════╗', '   🗝   ║ ▓▓  ◈  ▓▓ ║   🗝', '  ▄▄▄▄▄▄╣  ╔═════╗  ╠▄▄▄▄▄▄', '  █▒▒▒▒█║  ║ ▒▒▒ ║  ║█▒▒▒▒█',
          '  █ 📜 █║  ║ ⛓ ║  ║█ 🔒 █', '  ▀▀▀▀▀▀╩══╩═════╩══╩▀▀▀▀▀▀', '   ❄    ░░░ ▒▒▒ ░░░    ❄']


def banniere(largeur=None):
    """L'entrée de la Crypte : l'illustration B12 si elle existe (illustrations.bin, « crypte »), sinon le REPLI dessiné
    en caractères (la porte du sphinx, les coffres, la chaîne) : rien ne manque tant que l'image n'est pas là."""
    try:
        from . import scenes
        if scenes.disponible("crypte"):
            return scenes.illustration("crypte", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    return [f"  {_c(117)}{l}{RESET}" for l in CRYPTE]


def aide():
    return banniere() + [f" {_c(213)}{BOLD}🗝 " + t("cr.aide.titre") + RESET] + ["  " + l for l in t("cr.aide.liste").split("\n")]


def commande(args, sortie=None):
    """tg crypte [regle|demasque|roue|avalanche|donne|peintures|de|quiz|registre|chaine|consensus|mine|signe|vitrine|
    recensement|stop]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = (a[0].lower() if a else "aide").replace("î", "i").replace("é", "e")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    if sous == "stop":
        tuer_agents()
        out.write(t("cr.stop") + "\n")
        return
    lignes = []

    def f(st):
        c_(st)
        if sous == "regle":
            lignes.extend(banniere() + t("cr.meuble.regle", nom=st.get("name", "")).split("\n"))
        elif sous == "demasque":
            lignes.extend(lignes_demasque())
        elif sous == "roue":
            lignes.extend(lignes_roue(st, reste[0] if reste else None))
        elif sous == "avalanche":
            lignes.extend(lignes_avalanche(reste[0], reste[1]) if len(reste) >= 2 else [t("cr.avalanche.aide")])
        elif sous == "donne":
            lignes.extend(lignes_donne(st, reste[0] if reste else None))
        elif sous in ("peintures", "peinture"):
            lignes.extend(lignes_peintures())
        elif sous == "de":
            lignes.extend(lignes_de(st, reste[0] if reste else None))
        elif sous == "quiz":
            lignes.extend(lignes_quiz(st, reste))
        elif sous == "registre":
            lignes.extend(lignes_registre_ecran())
        elif sous == "chaine":
            lignes.extend(lignes_chaine(st, reste[0].rstrip("/") if reste else "chaine"))
        elif sous == "consensus":
            lignes.extend(lignes_consensus(st, reste[0] if reste else None))
        elif sous == "mine":
            lignes.extend(lignes_mine(reste[0] if reste else None))
        elif sous == "signe":
            lignes.extend(lignes_signe(st, reste[0] if reste else None))
        elif sous == "vitrine":
            lignes.extend(lignes_vitrine())
        elif sous == "recensement":
            lignes.extend(lignes_recensement(st))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
