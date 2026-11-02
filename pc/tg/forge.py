"""🔨 La Forge — la programmation : des recettes (scripts) aux programmes, puis son propre mini-jeu, son site web et
l'atelier multimédia (docs/programme.md § 2.10 et § 7.13 « Ton site web », « L'atelier multimédia »).

Le neuvième monde de la phase 5 (§ 7.14, étape 9). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → forge → requis) ; `chmod +x` (niveau 6) est enseigné sur
place, en mini-leçon pont (§ 2.9.5). Le chapitre et le lieu s'appellent « forge » : ~/terrain_terminagotchi/forge/.
On en sort et on y revient, l'étape est gardée. (L'ancien « atelier des Constructs » du tronc s'appelle maintenant
« la petite forge des Constructs » à l'écran, § 2.19 ; son dossier reste atelier/ ; « Atelier » est gardé pour les
robots.)

RÈGLES (affichées à l'entrée, enclume.txt) :
  - Les scripts de l'enfant s'écrivent et se lancent DANS LE TERRAIN (forge/). Le jeu ne propose aucune commande
    dangereuse ; il n'exécute lui-même aucun script de l'enfant.
  - Le site web : servi par `python3 -m http.server … --bind 127.0.0.1` (la règle du Port), depuis forge/site,
    sur un port libre au-dessus de 1024 ; personne d'autre que l'ordinateur lui-même ne peut le voir. Le jeu explique
    comment l'arrêter (fg puis Ctrl+C). « Publier » est seulement expliqué (avec un adulte) : aucun compte, aucun
    hébergeur mis en avant.
  - L'atelier multimédia : seulement des fichiers du jeu (les images de la créature, des sons fabriqués, une photo
    d'EXEMPLE aux métadonnées INVENTÉES). `exiftool` sert sur cette photo d'exemple, jamais sur les photos de
    l'enfant ; le jeu montre comment retirer les métadonnées. `forge exif` et `forge nettoie` refusent tout fichier
    hors du terrain.
  - Quand un outil manque (python3, magick, ffmpeg, sox, exiftool), son étape est cachée ou racontée : rien ne bloque.

LES PALIERS (fo0 à fo7) : la porte ; F1 les recettes (#!/bin/sh, sh, chmod +x, ./ : la cabane) ; F2 les boîtes et les
paramètres (variables, $1, $#, read) ; F3 les choix et les répétitions ($?, if, for, while : le village de 10 cabanes) ;
F4 Python depuis le terminal (python3 -c, un programme et ses arguments, lire un Traceback) ; F5 mon mini-jeu (la
devinette, un donjon fabriqué par un script, le jeu posé sur la carte comme un nouveau lieu) ; « Ton site web » (HTML,
CSS, le serveur sur 127.0.0.1, curl, l'arrêter, publier en notions) ; « L'atelier multimédia » (un GIF animé de sa
créature, un la à 440 Hz, couper un son, les métadonnées démasquées et retirées).

Récompenses (§ 7.6) : exploits « forge.premier_coup » (la première fois que la recette complète de la cabane est
lancée, elle marche) et « forge.sans_indice » (un palier fini sans aucun indice) ; variantes EXISTANTES favorisées
(Machine / Feu) : fondelin:lave, boulonnet:neon, tisonnier:mecanique.

Mêmes règles sur Android (Forge.kt) : sh y marche, ./ et read au clavier non (on lance avec sh, read reçoit un tuyau) ;
pas de Python (le serpent est raconté, puis le jeu construit dans l'appli, `doom`) ; le site est servi par l'appli
(`forge serveur`, sur 127.0.0.1) ; les outils multimédia sont racontés, la photo d'exemple se lit avec `forge exif`.
Vecteurs communs donnees/forge/vecteurs.json.
"""
import base64
import hashlib
import json
import math
import os
import pkgutil
import re
import socket
import struct
import sys
import unicodedata
import wave

from . import core, droits
from .langue import brut, t
from .plateforme import BOLD, DIM, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "forge.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_id(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def octets_graine(graine, sel):
    return hashlib.sha256(f"{graine}:{sel}".encode("utf-8")).digest()


def tours_question(graine):
    """La boucle de la question « combien de tours ? » : for i in $(seq A Z)."""
    b = octets_graine(graine, "tours")
    a = 2 + b[0] % 4
    return a, a + 4 + b[1] % 6


def tours_reponse(a, z):
    return z - a + 1


SHEBANG = re.compile(r"^#!\s*/(usr/)?bin/(env\s+)?(ba|da|k|mk|z)?sh\b")


def recette_etat(texte):
    """Ce que la recette de la cabane contient déjà : la première ligne magique, le mkdir, le touch."""
    lignes = (texte or "").splitlines()
    return {"shebang": bool(lignes) and SHEBANG.match(lignes[0].strip()) is not None,
            "mkdir": any(re.match(r"^\s*mkdir\b.*\bcabane\b", l) for l in lignes),
            "touch": any(re.match(r"^\s*touch\b.*\bcabane/\S", l) for l in lignes)}


def recette_complete(texte):
    e = recette_etat(texte)
    return e["shebang"] and e["mkdir"] and e["touch"]


def nom_du_jeu(texte):
    """Le nom que l'enfant donne à son jeu (pour la carte) : lettres, chiffres, espaces, ' et -, 40 caractères."""
    s = "".join(c for c in (texte or "") if c.isalnum() or c in " '-’").strip()
    return re.sub(r"\s+", " ", s)[:40].strip()


def sur(texte):
    """Un texte traduit posé dans un script sh entre guillemets doubles : ni guillemet, ni $, ni `, ni \\."""
    return (texte or "").replace('"', "'").replace("$", "").replace("`", "'").replace("\\", "/")


# ---------------------------------------------------------------- le JPEG d'exemple et ses métadonnées (EXIF)
def segments_jpeg(o):
    """[(marqueur, début des données, fin)] des segments d'un JPEG, jusqu'au début de l'image (SOS) ; None sinon."""
    if len(o) < 4 or o[0] != 0xFF or o[1] != 0xD8:
        return None
    out, i = [], 2
    while i + 4 <= len(o):
        if o[i] != 0xFF:
            return None
        m = o[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        n = (o[i + 2] << 8) | o[i + 3]
        if n < 2 or i + 2 + n > len(o):
            return None
        out.append((m, i + 4, i + 2 + n))
        if m == 0xDA:
            break
        i += 2 + n
    return out


def _app1_exif(o):
    for m, a, b in segments_jpeg(o) or []:
        if m == 0xE1 and o[a:a + 6] == b"Exif\0\0":
            return o[a + 6:b]
    return None


def a_exif(o):
    return _app1_exif(o) is not None


TAGS = {0x010E: "description", 0x010F: "marque", 0x0110: "modele", 0x0132: "date", 0x9003: "date_orig",
        0x0001: "lat_ref", 0x0002: "lat", 0x0003: "lon_ref", 0x0004: "lon"}


def exif_de(o):
    """Les métadonnées lisibles d'un JPEG : [(nom, valeur)] dans l'ordre (marque, modèle, dates, GPS), [] s'il n'y en a
    pas, None si ce n'est pas un JPEG. Lit le format TIFF (II ou MM), IFD0, Exif IFD, GPS IFD : chaînes et fractions."""
    if segments_jpeg(o) is None:
        return None
    tiff = _app1_exif(o)
    if tiff is None or len(tiff) < 8:
        return []
    be = tiff[:2] == b"MM"
    f16, f32 = (">H", ">I") if be else ("<H", "<I")

    def u16(p):
        return struct.unpack(f16, tiff[p:p + 2])[0]

    def u32(p):
        return struct.unpack(f32, tiff[p:p + 4])[0]

    vals = {}

    def ifd(p, gps=False, prof=0):
        if prof > 3 or p + 2 > len(tiff):
            return
        for k in range(u16(p)):
            e = p + 2 + 12 * k
            if e + 12 > len(tiff):
                return
            tag, typ, n = u16(e), u16(e + 2), u32(e + 4)
            taille = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1}.get(typ, 1) * n
            dp = e + 8 if taille <= 4 else u32(e + 8)
            if not gps and tag in (0x8769, 0x8825):
                ifd(u32(e + 8), gps=tag == 0x8825, prof=prof + 1)
                continue
            if (tag >= 0x0005 and gps) or (not gps and tag not in (0x010E, 0x010F, 0x0110, 0x0132, 0x9003)):
                continue
            if gps and tag not in (1, 2, 3, 4):
                continue
            if typ == 2:
                vals[TAGS[tag]] = tiff[dp:dp + n].split(b"\0")[0].decode("latin-1").strip()
            elif typ == 5 and n == 3:
                r = [u32(dp + 8 * j) / max(1, u32(dp + 8 * j + 4)) for j in range(3)]
                vals[TAGS[tag]] = r
    ifd(u32(4))
    out = [(k, vals[k]) for k in ("marque", "modele", "date", "date_orig", "description") if k in vals]
    for c, ref in (("lat", "lat_ref"), ("lon", "lon_ref")):
        if c in vals:
            d, m, s = vals[c]
            out.append((c, f"{int(d)}° {int(m)}' {s:.2f}\" {vals.get(ref, '')}".strip()))
    return out


def sans_exif(o):
    """Le même JPEG sans ses segments de métadonnées Exif (APP1) : l'image ne change pas."""
    seg = segments_jpeg(o)
    if seg is None:
        return o
    out = bytearray(o[:2])
    i = 2
    for m, a, b in seg:
        debut = a - 4
        out += o[i:debut]
        if not (m == 0xE1 and o[a:a + 6] == b"Exif\0\0"):
            out += o[debut:b]
        i = b
    out += o[i:]
    return bytes(out)


def photo_octets():
    return base64.b64decode(donnees()["photo"]["base64"])


# ---------------------------------------------------------------- GIF et WAV : de vrais fichiers ?
def images_gif(o):
    """Le nombre d'images d'un GIF (0 si ce n'est pas un GIF lisible)."""
    if len(o) < 13 or o[:6] not in (b"GIF87a", b"GIF89a"):
        return 0
    i = 13 + (3 * 2 ** ((o[10] & 7) + 1) if o[10] & 0x80 else 0)
    n = 0

    def sauter(i):
        while i < len(o) and o[i]:
            i += o[i] + 1
        return i + 1
    while i < len(o):
        b = o[i]
        if b == 0x3B:
            return n
        if b == 0x21:
            i = sauter(i + 2)
        elif b == 0x2C:
            if i + 10 > len(o):
                return n
            f = o[i + 9]
            i += 10 + (3 * 2 ** ((f & 7) + 1) if f & 0x80 else 0)
            i = sauter(i + 1)
            n += 1
        else:
            return n
    return n


def wav_ok(o):
    return len(o) > 44 and o[:4] == b"RIFF" and o[8:12] == b"WAVE"


# ---------------------------------------------------------------- la vue déployée : l'atelier de la forge
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def forge_de(morceau):
    """(outil, objet, de, vers) d'une commande (un morceau de ligne), ou None : la première règle de forge.json."""
    m = (morceau or "").strip()
    for r in donnees()["atelier"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["objet"], r["de"], r["vers"]
    return None


def forges_de(ligne):
    return [a for a in (forge_de(m) for m in SEPARATEURS.split(ligne or "")) if a]


# ================================================================ l'état, le terrain, le carnet de la forge
def f_(state):
    c = state.setdefault("forge", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "forge"


CARNET = "carnet_de_la_forge.txt"


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def dernier(etiquette):
    der = [x for x in carnet().splitlines() if x.startswith(f"[{etiquette}]")]
    return der[-1] if der else None


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _lire(rel, binaire=False):
    try:
        p = dossier() / rel
        return p.read_bytes() if binaire else p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _ecrire(rel, contenu):
    p = dossier() / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            p.write_bytes(contenu)
        else:
            p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def dans_le_terrain(chemin):
    """Le chemin (absolu) est dans le terrain du jeu (jamais les photos de l'enfant, ni ailleurs)."""
    try:
        p = os.path.realpath(str(chemin))
        r = os.path.realpath(str(core.TERRAIN))
        return p == r or p.startswith(r + os.sep)
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------- ce que le jeu pose dans la forge
_BIDI = re.compile("[\u200e\u200f\u2066-\u2069]")


def tf(cle, **p):
    """Le texte d'une clé SANS les marques de sens d'écriture (RLM, LRI…) : il va dans un FICHIER de code (serpent.py,
    devinette.sh), identique à celui du téléphone (Forge.tf)."""
    return _BIDI.sub("", t(cle, **p))


def serpent_py():
    """serpent.py : le petit programme Python du palier F4 (commentaires dans la langue de l'enfant)."""
    salut = sur(tf("fo.serpent.salut", nom="{nom}")).replace("'", "’")
    return ("# " + tf("fo.serpent.com1") + "\n# " + tf("fo.serpent.com2") + " python3 serpent.py NOM FOIS\n"
            "import sys\n\n"
            "nom = sys.argv[1]          # " + tf("fo.serpent.com3") + "\n"
            "fois = int(sys.argv[2])    # " + tf("fo.serpent.com4") + "\n\n"
            "for i in range(fois):\n"
            f"    print(f\"{{i + 1}}. {salut}\")\n")


def devinette_sh():
    """mon_jeu/devinette.sh : le jeu de devinette (read, while, if) que l'enfant lit, lance, puis fait jouer à un robot."""
    return ("#!/bin/sh\n"
            "# " + sur(tf("fo.devinette.com")) + "\n"
            "secret=$(( $(date +%s) % 10 + 1 ))\n"
            "essais=0\n"
            "reponse=0\n"
            f"echo \"{sur(tf('fo.devinette.debut'))}\"\n"
            "while [ \"$reponse\" != \"$secret\" ]; do\n"
            "  read reponse || exit 1\n"
            "  essais=$((essais + 1))\n"
            "  if [ \"$reponse\" -lt \"$secret\" ] 2>/dev/null; then\n"
            f"    echo \"{sur(tf('fo.devinette.plus'))}\"\n"
            "  elif [ \"$reponse\" -gt \"$secret\" ] 2>/dev/null; then\n"
            f"    echo \"{sur(tf('fo.devinette.moins'))}\"\n"
            "  fi\n"
            "done\n"
            f"echo \"{sur(tf('fo.devinette.bravo', n='@@'))}\"\n").replace("@@", "$essais")


def meubles(state):
    """Ce que le jeu pose dans la Forge quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    return {"forge/enclume.txt": t("fo.meuble.enclume") + "\n", f"forge/{CARNET}": t("fo.meuble.carnet") + "\n"}


SANS_INDICE = ("fo1", "fo2", "fo3", "fo4", "fo5", "fo6", "fo7")


def meubler(state, lid, step):
    d = dossier()
    if not d.is_dir():
        return
    if lid == "fo0" and not (d / "enclume.txt").exists():
        _ecrire("enclume.txt", t("fo.meuble.enclume") + "\n")
    if lid == "fo4" and not (d / "serpent.py").exists():
        _ecrire("serpent.py", serpent_py())
    if lid == "fo5" and step >= 1 and not (d / "mon_jeu" / "devinette.sh").exists():
        _ecrire("mon_jeu/devinette.sh", devinette_sh())
    if lid == "fo6" and step >= 1 and not (d / "site").is_dir():
        (d / "site").mkdir(parents=True, exist_ok=True)
    if lid == "fo7" and 5 <= step <= 7 and not (d / "multimedia" / "photo_exemple.jpg").exists():
        _ecrire("multimedia/photo_exemple.jpg", photo_octets())
    c = f_(state)
    if lid in SANS_INDICE and state.get("indice_lecon") and f"indice:{lid}" not in c["faits"]:
        c["faits"].append(f"indice:{lid}")              # un indice a été montré dans ce palier : il ne compte plus
    pont_maths(state, lid, step)


def lecon_finie(state, lid):
    """Un palier fini (histoire.finir_lecon) : sans aucun indice, l'exploit « forge.sans_indice » (une fois)."""
    if lid not in SANS_INDICE:
        return
    c = f_(state)
    if f"indice:{lid}" in c["faits"] or state.get("indice_lecon"):
        return
    from . import recompenses
    msg = recompenses.exploit(state, "forge.sans_indice")
    if msg:
        core.log(state, msg)
        core.say(state, "✨ " + t("fo.sans_indice", palier=t(f"hist.{lid}.titre")) + " " + msg, 18)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = f_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("fo.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("fo.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- le serveur du site (fo6)
def ports_possibles(state=None):
    p0 = donnees()["site"]["port"]
    out = []
    if state is not None and f_(state).get("port"):
        out.append(int(f_(state)["port"]))
    return list(dict.fromkeys(out + list(range(p0, p0 + donnees()["site"]["plage"]))))


def port_libre(p0=None):
    """Le premier port libre (sur 127.0.0.1) à partir de 8642."""
    p0 = p0 or donnees()["site"]["port"]
    for p in range(p0, p0 + donnees()["site"]["plage"]):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return p0


def _page(port, chemin="/"):
    """Le corps de la page servie sur 127.0.0.1:port, ou None (rien n'écoute)."""
    import http.client
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=0.6)
        c.request("GET", chemin)
        r = c.getresponse()
        corps = r.read(65536).decode("utf-8", "replace")
        c.close()
        return corps if r.status == 200 else None
    except (OSError, http.client.HTTPException):
        return None


def ecoute_partout(port):
    """Vrai si un serveur écoute sur ce port pour TOUT le réseau (0.0.0.0 ou ::), d'après /proc/net (Linux)."""
    for f, tout in (("/proc/net/tcp", "00000000"), ("/proc/net/tcp6", "0" * 32)):
        try:
            with open(f, encoding="ascii") as x:
                lignes = x.read().splitlines()[1:]
        except OSError:
            continue
        for l in lignes:
            p = l.split()
            if len(p) > 3 and p[3] == "0A" and ":" in p[1]:
                adr, pt = p[1].split(":")
                if int(pt, 16) == port and adr == tout:
                    return True
    return False


def titre_du_site():
    m = re.search(r"<h1[^>]*>(.*?)</h1>", _lire("site/index.html") or "", re.I | re.S)
    return m.group(1).strip() if m else None


def serveur_du_site(state=None):
    """(port, ouvert_a_tous) du serveur qui sert la page de l'enfant (forge/site), ou (None, False)."""
    h1 = titre_du_site()
    if not h1:
        return None, False
    for p in ports_possibles(state):
        corps = _page(p)
        if corps is not None and h1 in corps:
            return p, ecoute_partout(p)
    return None, False


def _serveur_ok():
    p, partout = serveur_du_site(core.load())
    if p and not partout:
        if not dans_carnet("serveur") or (dernier("serveur") or "").split()[1:2] != [str(p)]:
            noter("serveur", f"{p} (ok)")
        return True
    return False


def _port_note():
    der = dernier("serveur")
    try:
        return int(der.split()[1]) if der else None
    except (ValueError, IndexError):
        return None


def _arrete_ok():
    p = _port_note()
    return p is not None and dans_carnet("serveur") and _page(p) is None


# ---------------------------------------------------------------- les vérifications des étapes
def _recette():
    return _lire("cabane.sh") or ""


def _cabane_ok():
    return (dossier() / "cabane" / "porte.txt").is_file() and (dossier() / "cabane" / "toit.txt").is_file()


def _exec_ok():
    p = dossier() / "cabane.sh"
    return p.is_file() and droits.acces(p, os.X_OK)


def _contient(rel, motif):
    return re.search(motif, _lire(rel) or "") is not None


def _village_ok():
    return all((dossier() / "village" / f"cabane_{i}").is_dir() for i in range(1, 11))


def _donjon_ok():
    return all((dossier() / "mon_jeu" / "donjon" / f"salle_{i}").is_dir() for i in range(1, 4))


def _photo_propre():
    o = _lire("multimedia/photo_exemple.jpg", binaire=True)
    return o is not None and segments_jpeg(o) is not None and not a_exif(o)


FS = {
    "fo_shebang": lambda: recette_etat(_recette())["shebang"],
    "fo_mkdir": lambda: (lambda e: e["shebang"] and e["mkdir"])(recette_etat(_recette())),
    "fo_touch": lambda: recette_complete(_recette()),
    "fo_cabane": _cabane_ok,
    "fo_exec": _exec_ok,
    "fo_salut": lambda: _contient("salut.sh", r"\$\{?1\b"),
    "fo_dieses": lambda: _contient("salut.sh", r"\$#"),
    "fo_question": lambda: _contient("question.sh", r"(^|\s)read\s+\w+"),
    "fo_code": lambda: dans_carnet("code"),
    "fo_village": _village_ok,
    "fo_tours": lambda: dans_carnet("tours"),
    "fo_erreur": lambda: dans_carnet("erreur"),
    "fo_donjon_sh": lambda: _contient("donjon.sh", r"(?s)\bfor\b.*\bmkdir\b.*donjon"),
    "fo_donjon": _donjon_ok,
    "fo_tresor": lambda: bool((_lire("mon_jeu/donjon/salle_3/tresor.txt") or "").strip()),
    "fo_lieu": lambda: (dossier() / "mon_jeu" / ".lieu").is_file(),
    "fo_html": lambda: _contient("site/index.html", r"(?i)<h1[^>]*>.+</h1>"),
    "fo_p": lambda: _contient("site/index.html", r"(?i)<p[\s>]"),
    "fo_css": lambda: _contient("site/style.css", r"\{[^}]*:[^}]*\}"),
    "fo_link": lambda: _contient("site/index.html", r"(?i)<link\b[^>]*style\.css"),
    "fo_serveur": _serveur_ok,
    "fo_arrete": _arrete_ok,
    "fo_gif": lambda: images_gif(_lire("multimedia/creature.gif", binaire=True) or b"") >= 2,
    "fo_la": lambda: wav_ok(_lire("multimedia/la.wav", binaire=True) or b""),
    "fo_coupe": lambda: wav_ok(_lire("multimedia/fin.wav", binaire=True) or b""),
    "fo_appareil": lambda: dans_carnet("appareil"),
    "fo_propre": _photo_propre,
    "fo_bilan": lambda: dans_carnet("bilan"),
}
CREE = {}

# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
FO = r"^(tg\s+)?forge\s+"
SH = r"^(sh|bash|dash|zsh)\s+"
PY = r"^python3?\s+"
O = "forge"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


GIF = "magick -delay 20 -loop 0 multimedia/creature_*.png multimedia/creature.gif"
SERVEUR = "python3 -m http.server 8642 --bind 127.0.0.1 --directory site &"
LECONS = {
    # la porte de la Forge
    "fo0": {"titre": "hist.fo0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "forge"}), "cmd": "cd ~/terrain_terminagotchi/forge", "ici": "forge",
         "bravo": ("hist.entree.bravo", {"piece": "forge"})},
        _n("fo0", 1, cmd="ls", re=LS, ou=O),
        _n("fo0", 2, cmd="cat enclume.txt", re=LIRE + r".*enclume", ou=O),
    ]},
    # F1 les recettes : #!/bin/sh, sh, chmod +x (pont du niveau 6), ./
    "fo1": {"titre": "hist.fo1.titre", "skill": None, "steps": [
        _n("fo1", 0, cmd="forge recette", re=FO + r"recettes?\s*$"),
        _n("fo1", 1, cmd="echo '#!/bin/sh' > cabane.sh", fs="fo_shebang", ou=O, win=False),
        _n("fo1", 2, cmd="echo 'mkdir -p cabane' >> cabane.sh", fs="fo_mkdir", ou=O, win=False),
        _n("fo1", 3, cmd="echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh", fs="fo_touch", ou=O, win=False),
        _n("fo1", 4, cmd="cat cabane.sh", re=LIRE + r".*cabane\.sh", ou=O),
        _n("fo1", 5, cmd="sh cabane.sh", fs="fo_cabane", ou=O, win=False),
        _n("fo1", 6, cmd="chmod +x cabane.sh", fs="fo_exec", ou=O, win=False),
        _n("fo1", 7, cmd="./cabane.sh", re=r"^\./cabane\.sh\b", ou=O, win=False),
    ]},
    # F2 les boîtes et les paramètres : variables, $1, $#, read
    "fo2": {"titre": "hist.fo2.titre", "skill": None, "steps": [
        _n("fo2", 0, cmd="forge boites", re=FO + r"bo[iî]tes?\s*$"),
        _n("fo2", 1, cmd="nom=Pixel", re=r"^[A-Za-z_]\w*=\S", win=False),
        _n("fo2", 2, cmd='echo "Bonjour $nom"', re=r"^echo\b.*\$\{?[A-Za-z_]\w*", win=False),
        _n("fo2", 3, cmd="echo 'echo \"Bonjour $1 !\"' > salut.sh", fs="fo_salut", ou=O, win=False),
        _n("fo2", 4, cmd="sh salut.sh Léa", re=SH + r"salut\.sh\s+\S", ou=O, win=False),
        _n("fo2", 5, cmd="echo 'echo \"Tu as donné $# prénoms.\"' >> salut.sh", fs="fo_dieses", ou=O, win=False),
        _n("fo2", 6, cmd="sh salut.sh Léa Tom Sam", re=SH + r"salut\.sh(\s+\S+){2,}", ou=O, win=False),
        _n("fo2", 7, cmd="echo 'read prenom' > question.sh && echo 'echo \"Salut $prenom !\"' >> question.sh",
           fs="fo_question", ou=O, win=False),
        _n("fo2", 8, cmd="sh question.sh", re=r"(" + SH + r"|\|\s*(sh|bash)\s+)question\.sh", ou=O, win=False),
    ]},
    # F3 les choix et les répétitions : $?, if, for, while
    "fo3": {"titre": "hist.fo3.titre", "skill": None, "steps": [
        _n("fo3", 0, cmd="forge aiguillage", re=FO + r"aiguillages?\s*$"),
        _n("fo3", 1, cmd="ls fantome; echo $?", re=r"^echo\s+[\"']?\$\?", ou=O, win=False),
        _n("fo3", 2, cmd="forge code ?", fs="fo_code"),
        _n("fo3", 3, cmd='if [ -f cabane/porte.txt ]; then echo "La porte est là !"; fi', re=r"^if\s+\[\s+-[fed]\b",
           ou=O, win=False),
        _n("fo3", 4, cmd='for i in 1 2 3; do echo "Tour $i"; done', re=r"^for\s+\w+\s+in\b", win=False),
        _n("fo3", 5, cmd="for i in $(seq 1 10); do mkdir -p village/cabane_$i; done", fs="fo_village", ou=O, win=False),
        _n("fo3", 6, cmd="ls village | wc -l", re=r"^ls\b.*village.*\|\s*wc\b", ou=O, win=False),
        _n("fo3", 7, cmd="n=3; while [ $n -gt 0 ]; do echo $n; n=$((n - 1)); done", re=r"^while\b", win=False),
        _n("fo3", 8, cmd="forge tours ?", fs="fo_tours"),
    ]},
    # F4 Python depuis le terminal
    "fo4": {"titre": "hist.fo4.titre", "skill": None, "steps": [
        _n("fo4", 0, cmd="forge serpent", re=FO + r"serpents?\s*$"),
        _n("fo4", 1, cmd="python3 --version", re=PY + r"(--version|-V)\b", outil="python3"),
        _n("fo4", 2, cmd='python3 -c "print(2 + 3 * 4)"', re=PY + r"-c\b.*print", outil="python3"),
        _n("fo4", 3, cmd="python3 -c \"for i in range(3): print('Pixel')\"", re=PY + r"-c\b.*\bfor\b.*range\s*\(\s*3\s*\)",
           outil="python3"),
        _n("fo4", 4, cmd="cat serpent.py", re=LIRE + r".*serpent\.py", ou=O),
        _n("fo4", 5, cmd="python3 serpent.py", re=PY + r"serpent\.py\s*$", ou=O, outil="python3", tout_code=True),
        _n("fo4", 6, cmd="forge erreur ?", fs="fo_erreur"),
        _n("fo4", 7, cmd="python3 serpent.py Pixel 3", re=PY + r"serpent\.py\s+\S+\s+\d+", ou=O, outil="python3"),
    ]},
    # F5 mon mini-jeu : la devinette, le donjon fabriqué par un script, le jeu sur la carte
    "fo5": {"titre": "hist.fo5.titre", "skill": None, "steps": [
        _n("fo5", 0, cmd="forge jeu", re=FO + r"jeu\s*$", ou=O),
        _n("fo5", 1, cmd="cat mon_jeu/devinette.sh", re=LIRE + r".*devinette\.sh", ou=O),
        _n("fo5", 2, cmd="sh mon_jeu/devinette.sh", re=SH + r"\S*devinette\.sh", ou=O, win=False, tout_code=True),
        _n("fo5", 3, cmd="seq 1 10 | sh mon_jeu/devinette.sh", re=r"^seq\b.*\|\s*(sh|bash)\s+\S*devinette\.sh", ou=O,
           win=False),
        _n("fo5", 4, cmd="echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_$s; done' > donjon.sh",
           fs="fo_donjon_sh", ou=O, win=False),
        _n("fo5", 5, cmd="sh donjon.sh", fs="fo_donjon", ou=O, win=False),
        _n("fo5", 6, cmd='echo "Le trésor est ici !" > mon_jeu/donjon/salle_3/tresor.txt', fs="fo_tresor", ou=O),
        _n("fo5", 7, cmd='forge carte "La grotte de Pixel"', fs="fo_lieu"),
        _n("fo5", 8, cmd="tree mon_jeu", re=r"^(tree|find|ls)\b.*mon_jeu", ou=O, repli=["find mon_jeu"]),
    ]},
    # Ton site web : HTML, CSS, le serveur sur 127.0.0.1, curl, l'arrêter, publier (notions)
    "fo6": {"titre": "hist.fo6.titre", "skill": None, "steps": [
        _n("fo6", 0, cmd="forge site", re=FO + r"site\s*$", ou=O),
        _n("fo6", 1, cmd="echo '<h1>Bienvenue chez Pixel</h1>' > site/index.html", fs="fo_html", ou=O),
        _n("fo6", 2, cmd="echo '<p>Ici vit ma créature. Elle adore les cabanes.</p>' >> site/index.html", fs="fo_p", ou=O),
        _n("fo6", 3, cmd="echo 'h1 { color: orange; }' > site/style.css", fs="fo_css", ou=O),
        _n("fo6", 4, cmd="echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html", fs="fo_link", ou=O),
        _n("fo6", 5, cmd="cat site/index.html", re=LIRE + r".*site/index\.html", ou=O),
        _n("fo6", 6, cmd=SERVEUR, fs="fo_serveur", ou=O, outil="python3", win=False),
        _n("fo6", 7, cmd="curl localhost:8642", re=r"^curl\b.*(localhost|127\.0\.0\.1):\d{4,5}", outil="python3+curl", win=False),
        _n("fo6", 8, cmd="fg", fs="fo_arrete", outil="python3", win=False),
        _n("fo6", 9, cmd="forge publier", re=FO + r"publi"),
    ]},
    # L'atelier multimédia : un GIF animé de sa créature, un la, couper un son, les métadonnées démasquées
    "fo7": {"titre": "hist.fo7.titre", "skill": None, "steps": [
        _n("fo7", 0, cmd="forge multimedia", re=FO + r"multim[eé]dias?\s*$", ou=O),
        _n("fo7", 1, cmd="ls multimedia", re=LS + r".*multimedia", ou=O),
        _n("fo7", 2, cmd=GIF, fs="fo_gif", ou=O, outil="magick|convert", repli=[GIF.replace("magick", "convert", 1)],
           win=False),
        _n("fo7", 3, cmd="sox -n multimedia/la.wav synth 0.5 sine 440", fs="fo_la", ou=O, outil="sox", win=False),
        _n("fo7", 4, cmd="ffmpeg -i multimedia/fanfare.wav -ss 0.5 -t 0.5 multimedia/fin.wav", fs="fo_coupe", ou=O,
           outil="ffmpeg", win=False),
        _n("fo7", 5, cmd="exiftool multimedia/photo_exemple.jpg",
           re=r"^(exiftool\b|(tg\s+)?forge\s+exif\b).*photo_exemple", ou=O,
           repli=["tg forge exif multimedia/photo_exemple.jpg"]),
        _n("fo7", 6, cmd="forge appareil ?", fs="fo_appareil"),
        _n("fo7", 7, cmd="exiftool -all= -overwrite_original multimedia/photo_exemple.jpg", fs="fo_propre", ou=O,
           repli=["tg forge nettoie multimedia/photo_exemple.jpg"]),
        _n("fo7", 8, cmd="forge bilan", fs="fo_bilan"),
    ]},
}
CHAPITRE = {"id": "forge", "n": 19, "piece": "forge", "famille": "Constructs", "monde": True,
            "lecons": [f"fo{i}" for i in range(8)], "objet": "marteau_de_forge", "titre": "maitre_de_la_forge"}


# ================================================================ l'arbre du Carrefour : quand la Forge s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "forge"), {})


def _besoin():
    from . import programme
    P = programme.donnees()
    m = _monde()
    chaps = []
    for n in m.get("requis", []):
        chaps += [c for c in P.get("tronc", {}).get(n, []) if c not in chaps]
    return chaps, list(m.get("requis_lecons", []))


def ouvert(state):
    from . import histoire
    chaps, lecs = _besoin()
    if not chaps and not lecs:
        return False
    faits = histoire.h_(state)["faits"]
    return all(histoire.fini(state, c) for c in chaps) and all(l in faits for l in lecs)


def manque(state):
    from . import histoire, lecons
    chaps, lecs = _besoin()
    faits = histoire.h_(state)["faits"]
    out = [histoire.nom_chapitre(c) for c in chaps if not histoire.fini(state, c)]
    for l in lecs:
        if l not in faits:
            ch = histoire.chapitre_de_lecon(l)
            out.append(f"{lecons.tx(histoire.lecon_def(l)['titre'])} ({histoire.nom_chapitre(ch['id']) if ch else '?'})")
    return out


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "forge" in deja or histoire.fini(state, "forge") or not ouvert(state):
        return False
    deja.append("forge")
    core.log(state, t("fo.ouvert.log"))
    core.say(state, histoire.dire(state, "fo.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"forge code ?": "code", "forge tours ?": "tours", "forge erreur ?": "erreur", "forge appareil ?": "appareil"}
SANS_BIND = re.compile(r"^(python3?|py)\s+-m\s+http\.server\b(?!.*(--bind[=\s]+|\s-b\s+)(127\.|localhost|::1))")


def indice(step, tapees):
    """Un indice de la Forge : un « ? » recopié, une mauvaise réponse, des guillemets doubles autour de #!, un > qui a
    effacé la recette, une recette incomplète, ./ sans chmod +x, salut.sh sans prénom, un serveur ouvert à tout le
    réseau ou un port déjà pris, curl trop tôt, le serveur pas encore arrêté."""
    cmd = step.get("cmd") or ""
    fs = step.get("fs")
    lignes = [(l or "").strip() for l, _c in tapees]
    et = REPONSES.get(cmd)
    if et:
        if any(re.match(FO + et, l) and TROU.search(l[len("forge"):]) for l in lignes):
            return t("fo.indice.trou")
        der = dernier(et)
        if der and not der.endswith("(ok)") and any(re.match(FO + et, l) for l in lignes):
            return t("fo.indice.rep." + et)
    if fs == "fo_shebang" and any(re.match(r'^echo\s+"#!', l) for l in lignes):
        return t("fo.indice.guillemets_simples")
    if fs in ("fo_mkdir", "fo_touch", "fo_cabane") and (dossier() / "cabane.sh").exists() \
            and not recette_etat(_recette())["shebang"]:
        return t("fo.indice.efface")
    if fs == "fo_cabane" and any(re.match(SH + r"\S*cabane\.sh", l) for l in lignes):
        e = recette_etat(_recette())
        manque_ = [k for k in ("shebang", "mkdir", "touch") if not e[k]]
        if manque_:
            return t("fo.indice.recette", ligne=t("fo.recette.ligne." + manque_[0]))
    if (cmd.startswith("./") or fs == "fo_exec") and any(l.startswith("./cabane") for l in lignes) and not _exec_ok():
        return t("fo.indice.chmod")
    if cmd.startswith("sh salut.sh") and any(re.match(SH + r"salut\.sh\s*$", l) for l in lignes):
        return t("fo.indice.prenom")
    if fs == "fo_lieu" and any(re.match(FO + r"carte\s*$", l) for l in lignes):
        return t("fo.carte.aide")
    if fs == "fo_serveur" and any(l.startswith("curl") for l in lignes) and not serveur_du_site(core.load())[0]:
        return t("fo.indice.allume_d_abord")
    if fs == "fo_serveur":
        if any(SANS_BIND.search(l) for l in lignes):
            from . import port
            return t("port.lanterne.ouverte")
        p, partout = serveur_du_site(core.load())
        if p and partout:
            return t("fo.indice.partout", port=p)
        if any(re.match(r"^python3?\s+-m\s+http\.server\b", l) for l in lignes) and not titre_du_site():
            return t("fo.indice.pas_de_page")
    if cmd.startswith("curl") and any(l.startswith("curl") for l in lignes) and _port_note() \
            and _page(_port_note()) is None:
        return t("fo.indice.serveur_eteint")
    if fs == "fo_arrete" and _port_note() and _page(_port_note()) is not None:
        return t("fo.indice.ctrl_c")
    return None


def surveiller(state, lignes):
    """La première fois que la recette COMPLÈTE de la cabane est lancée (sh cabane.sh ou ./cabane.sh), si la cabane
    est bâtie : l'exploit « forge.premier_coup ». Un essai avec une recette incomplète ne compte pas encore."""
    c = f_(state)
    if "essai_cabane" in c["faits"]:
        return False
    for l in lignes or []:
        l = (l or "").strip()
        if not re.match(r"^((sh|bash|dash)\s+(\./)?|\./)cabane\.sh\b", l):
            continue
        if not recette_complete(_recette()):
            continue
        c["faits"].append("essai_cabane")
        if _cabane_ok():
            from . import recompenses
            msg = recompenses.exploit(state, "forge.premier_coup")
            if msg:
                core.log(state, msg)
                core.say(state, "🔥 " + t("fo.premier_coup") + " " + msg, 18)
                core.terminal(state, "🔥 " + t("fo.premier_coup") + " " + msg)
            return True
        return False
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
FORGE = ["      ╔═╗      🔨", "   ▄▄▄╣ ╠▄▄▄  ✦ ✦", "   █▓▓▓▓▓▓▓█  📜", "  ▀▀▀█▀▀▀█▀▀▀", "     █▄▄▄█   🔥🔥"]


def banniere(largeur=None):
    """L'entrée de la Forge : l'illustration (illustrations.bin, « forge ») si elle existe, sinon le REPLI dessiné en
    caractères (l'enclume, le parchemin, le feu)."""
    try:
        from . import scenes
        if scenes.disponible("forge"):
            return scenes.illustration("forge", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [208, 214, 229, 203, 196]
    return [f"  {fg(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(FORGE)]


def aide():
    return banniere() + [f" {fg(208)}{BOLD}🔨 " + t("fo.aide.titre") + RESET] + \
        ["  " + l for l in t("fo.aide.liste").split("\n")]


def _bloc(cle, **p):
    return ["  " + l for l in t(cle, **p).split("\n")]


def _rep(arg):
    return (arg or "").strip()


def lignes_atelier(etiquette, titre, texte, icone, couleur, **p):
    noter(etiquette, "lu (ok)")
    return [f" {fg(couleur)}{BOLD}{icone} " + t(titre) + RESET, ""] + _bloc(texte, **p)


def lignes_code(arg):
    if not arg:
        return [t("fo.code.aide")]
    a = _rep(arg)
    if re.fullmatch(r"\d{1,3}", a) and int(a) != 0:
        noter("code", f"{a} (ok)")
        return [f" {fg(78)}✔ " + t("fo.code.ok", n=a) + RESET]
    noter("code", f"{a[:12]} (faux)")
    return [f" {fg(203)}✖ " + t("fo.indice.rep.code") + RESET]


def lignes_tours(state, arg):
    a, z = tours_question(_graine(state))
    if not arg:
        return [t("fo.tours.aide", a=a, z=z)]
    if _rep(arg) == str(tours_reponse(a, z)):
        noter("tours", f"{_rep(arg)} (ok)")
        return [f" {fg(78)}✔ " + t("fo.tours.ok", a=a, z=z, n=tours_reponse(a, z)) + RESET]
    noter("tours", f"{_rep(arg)[:12]} (faux)")
    return [f" {fg(203)}✖ " + t("fo.indice.rep.tours") + RESET, "  " + t("fo.tours.aide", a=a, z=z)]


def lignes_serpent():
    import shutil
    if not (dossier() / "serpent.py").exists():
        _ecrire("serpent.py", serpent_py())
    la = shutil.which("python3") or shutil.which("python")
    noter("serpent", ("present" if la else "raconte") + " (ok)")
    out = [f" {fg(78)}{BOLD}🐍 " + t("fo.serpent.titre") + RESET, ""] + _bloc("fo.serpent.texte")
    out += ["", "  " + t("fo.serpent.present" if la else "fo.serpent.absent")]
    if not la:
        out += ["", f"  {DIM}$ python3 serpent.py{RESET}"] + ["  " + l for l in donnees()["traceback"]]
    return out


def lignes_erreur(arg):
    if not arg:
        return [t("fo.erreur.aide")]
    if ascii_id(_rep(arg)).replace(":", "") in ("indexerror",):
        noter("erreur", "IndexError (ok)")
        return [f" {fg(78)}✔ " + t("fo.erreur.ok") + RESET]
    noter("erreur", f"{_rep(arg)[:16]} (faux)")
    return [f" {fg(203)}✖ " + t("fo.indice.rep.erreur") + RESET]


def lignes_jeu():
    _ecrire("mon_jeu/devinette.sh", devinette_sh())
    noter("jeu", "devinette (ok)")
    return [f" {fg(213)}{BOLD}🎮 " + t("fo.jeu.titre") + RESET, ""] + _bloc("fo.jeu.texte")


def lignes_carte(state, arg):
    nom = nom_du_jeu(arg)
    if not nom:
        return [t("fo.carte.aide")]
    if not (dossier() / "mon_jeu").is_dir():
        return [f" {fg(215)}✋ " + t("fo.carte.pas_de_jeu") + RESET]
    _ecrire("mon_jeu/.lieu", nom + "\n")
    f_(state)["jeu"] = nom
    noter("carte", f"{nom} (ok)")
    return [f" {fg(213)}{BOLD}🗺 " + t("fo.carte.ok", nom=nom) + RESET, ""] + _bloc("fo.carte.texte", nom=nom)


def lignes_site(state):
    (dossier() / "site").mkdir(parents=True, exist_ok=True)
    p0 = donnees()["site"]["port"]
    p = port_libre(p0)
    f_(state)["port"] = p
    noter("site", f"{p} (ok)")
    out = [f" {fg(117)}{BOLD}🌐 " + t("fo.site.titre") + RESET, ""] + _bloc("fo.site.texte", port=p0)
    if p != p0:
        out += ["", f"  {fg(215)}⚠ " + t("fo.site.port_pris", port=p0, autre=p) + RESET]
    import shutil
    if not shutil.which("python3"):
        out += ["", "  " + t("fo.site.sans_python", port=p0)]
    return out


def lignes_multimedia(state):
    import shutil
    from . import sprites
    d = "multimedia/"
    rows = sprites.get_sprite(state) if state.get("xp") is not None else sprites.BABY
    pal = sprites.palette(state) if state.get("xp") is not None else {"b": 213, "e": 16}
    for k, dy in enumerate(donnees()["multimedia"]["sauts"]):
        cadre = ["."] * (4 - dy) + list(rows) + ["."] * dy
        chemin = dossier() / d / f"creature_{k + 1}.png"
        try:
            chemin.parent.mkdir(parents=True, exist_ok=True)
            sprites.png(str(chemin), cadre, pal, echelle=4, marge=2)
        except OSError:
            pass
    _ecrire(d + "fanfare.wav", fanfare_octets())
    if not (dossier() / d / "photo_exemple.jpg").exists() or not dans_carnet("multimedia"):
        _ecrire(d + "photo_exemple.jpg", photo_octets())
    outils = ["magick", "sox", "ffmpeg", "exiftool"]
    la = [o for o in outils if shutil.which(o) or (o == "magick" and shutil.which("convert"))]
    pas = [o for o in outils if o not in la]
    noter("multimedia", "fichiers (ok)")
    out = [f" {fg(141)}{BOLD}🎞 " + t("fo.multimedia.titre") + RESET, ""] + _bloc("fo.multimedia.texte")
    out += ["", "  " + t("fo.multimedia.outils", presents=", ".join(la) or "—", absents=", ".join(pas) or "—")]
    return out


def fanfare_octets():
    """fanfare.wav : do mi sol do (1 seconde, 24 000 Hz, 16 bits, mono), fabriquée par le jeu."""
    import io
    taux = 24000
    notes = donnees()["multimedia"]["fanfare_hz"]
    dur = int(taux * donnees()["multimedia"]["note_s"])
    ech = bytearray()
    for f in notes:
        for k in range(dur):
            env = min(1.0, k / 400, (dur - k) / 400)
            ech += struct.pack("<h", int(9000 * env * math.sin(2 * math.pi * f * k / taux)))
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(bytes(ech))
    return b.getvalue()


def _chemin(arg):
    from pathlib import Path
    a = _rep(arg).strip("'\"")
    if not a:
        return None
    p = Path(os.path.expanduser(a))
    return p if p.is_absolute() else Path(os.getcwd()) / p


def lignes_exif(arg):
    p = _chemin(arg)
    if p is None:
        return [t("fo.exif.aide")]
    if not dans_le_terrain(p):
        return [f" {fg(203)}✋ " + t("fo.exif.hors_terrain") + RESET]
    try:
        o = p.read_bytes()
    except OSError:
        return [f" {fg(203)}✖ " + t("fo.exif.introuvable", fichier=p.name) + RESET]
    ex = exif_de(o)
    if ex is None:
        return [f" {fg(203)}✖ " + t("fo.exif.pas_jpeg", fichier=p.name) + RESET]
    noter("exif", f"{p.name} {len(ex)} (ok)")
    out = [f" {fg(229)}{BOLD}🔍 " + t("fo.exif.titre", fichier=p.name) + RESET, ""]
    if not ex:
        return out + ["  " + t("fo.exif.aucune")]
    w = max(len(t("fo.exif." + k)) for k, _v in ex)
    out += [f"  {t('fo.exif.' + k):<{w}} : {v}" for k, v in ex]
    return out + ["", "  " + t("fo.exif.morale")]


def lignes_appareil(arg):
    if not arg:
        return [t("fo.appareil.aide")]
    bon = donnees()["photo"]["marque"]
    if ascii_id(_rep(arg)) == ascii_id(bon):
        noter("appareil", f"{bon} (ok)")
        return [f" {fg(78)}✔ " + t("fo.appareil.ok", marque=bon) + RESET]
    noter("appareil", f"{_rep(arg)[:16]} (faux)")
    return [f" {fg(203)}✖ " + t("fo.indice.rep.appareil") + RESET]


def lignes_nettoie(arg):
    p = _chemin(arg)
    if p is None:
        return [t("fo.nettoie.aide")]
    if not dans_le_terrain(p):
        return [f" {fg(203)}✋ " + t("fo.exif.hors_terrain") + RESET]
    try:
        o = p.read_bytes()
    except OSError:
        return [f" {fg(203)}✖ " + t("fo.exif.introuvable", fichier=p.name) + RESET]
    if segments_jpeg(o) is None:
        return [f" {fg(203)}✖ " + t("fo.exif.pas_jpeg", fichier=p.name) + RESET]
    if not a_exif(o):
        return ["  " + t("fo.nettoie.deja", fichier=p.name)]
    try:
        p.write_bytes(sans_exif(o))
    except OSError:
        return [f" {fg(203)}✖ " + t("fo.exif.introuvable", fichier=p.name) + RESET]
    noter("nettoie", f"{p.name} (ok)")
    return [f" {fg(78)}✔ " + t("fo.nettoie.ok", fichier=p.name) + RESET]


def manques_bilan():
    """Ce qui manque encore pour le certificat de la Forge (les clés des textes)."""
    out = []
    if not _cabane_ok():
        out.append("fo.bilan.m.cabane")
    if not _village_ok():
        out.append("fo.bilan.m.village")
    if not dans_carnet("erreur"):
        out.append("fo.bilan.m.serpent")
    if not (dossier() / "mon_jeu" / ".lieu").is_file():
        out.append("fo.bilan.m.jeu")
    if not FS["fo_html"]():
        out.append("fo.bilan.m.site")
    if not _photo_propre():
        out.append("fo.bilan.m.photo")
    return out


def lignes_bilan(state):
    m = manques_bilan()
    if m:
        noter("bilan", "pas encore (faux)")
        return [f" {fg(215)}✋ " + t("fo.bilan.pas_encore") + RESET] + ["   · " + t(k) for k in m]
    nom = f_(state).get("jeu") or (_lire("mon_jeu/.lieu") or "").strip() or "?"
    certif = t("fo.bilan.texte", nom=state.get("name") or "?", jeu=nom, titre=titre_du_site() or "?")
    _ecrire("certificat_de_la_forge.txt", certif + "\n")
    noter("bilan", "certificat (ok)")
    return [f" {fg(78)}{BOLD}🏅 " + t("fo.bilan.titre") + RESET, ""] + ["  " + l for l in certif.split("\n")]


def commande(args, sortie=None):
    """tg forge [plan|recette|boites|aiguillage|code N|tours N|serpent|erreur MOT|jeu|carte NOM|site|publier|
    multimedia|exif FICHIER|appareil MOT|nettoie FICHIER|bilan]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_id(a[0] if a else "aide")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        f_(st)
        arg = " ".join(reste) if reste else None
        if sous in ("plan", "enclume", "regles"):
            lignes.extend(banniere() + t("fo.meuble.enclume").split("\n"))
        elif sous in ("recette", "recettes"):
            lignes.extend(lignes_atelier("recette", "fo.recette.titre", "fo.recette.texte", "📜", 214))
        elif sous in ("boites", "boite"):
            lignes.extend(lignes_atelier("boites", "fo.boites.titre", "fo.boites.texte", "📦", 117))
        elif sous in ("aiguillage", "aiguillages"):
            lignes.extend(lignes_atelier("aiguillage", "fo.aiguillage.titre", "fo.aiguillage.texte", "🔀", 229))
        elif sous == "code":
            lignes.extend(lignes_code(arg))
        elif sous == "tours":
            lignes.extend(lignes_tours(st, arg))
        elif sous in ("serpent", "serpents", "python"):
            lignes.extend(lignes_serpent())
        elif sous == "erreur":
            lignes.extend(lignes_erreur(arg))
        elif sous == "jeu":
            lignes.extend(lignes_jeu())
        elif sous == "carte":
            lignes.extend(lignes_carte(st, arg))
        elif sous == "site":
            lignes.extend(lignes_site(st))
        elif sous in ("publier", "publie", "publication"):
            lignes.extend(lignes_atelier("publier", "fo.publier.titre", "fo.publier.texte", "🌍", 117))
        elif sous in ("multimedia", "multimedias"):
            lignes.extend(lignes_multimedia(st))
        elif sous == "exif":
            lignes.extend(lignes_exif(arg))
        elif sous == "appareil":
            lignes.extend(lignes_appareil(arg))
        elif sous == "nettoie":
            lignes.extend(lignes_nettoie(arg))
        elif sous == "bilan":
            lignes.extend(lignes_bilan(st))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    if lignes:
        out.write("\n".join(lignes) + RESET + "\n")
    return 0


def brut_fr(cle):
    return brut(cle, "fr")

