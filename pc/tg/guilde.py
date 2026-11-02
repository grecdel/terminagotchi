"""🛠 La Guilde des Bâtisseurs Libres — l'open source et le DIY (docs/programme.md § 7.12), au bord de la Forge.

Le sixième monde de la phase 5 (§ 7.14, étape 7). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 4 du tronc commun (programme.json, « mondes » → guilde → requis) ; son pont vers la Bibliothèque du
Temps (git) sert en G4. Le chapitre et le lieu s'appellent « guilde » : ~/terrain_terminagotchi/guilde/. On en sort et
on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, mur_des_plans.txt) :
  - TOUT RESTE DANS LE TERRAIN. Le jeu n'installe rien (jamais de sudo, ni dnf ni apt), ne pousse rien, n'ouvre
    aucune demande de fusion, ne crée aucun compte et n'utilise aucun jeton. Une vraie contribution, une vraie
    installation ou une vraie impression se font AVEC UN ADULTE, et le jeu les explique seulement.
  - G2 : `git clone` du dépôt public de Terminagotchi dans le terrain ; sans réseau, `guilde copie` pose une copie
    locale du code du jeu (les vrais fichiers du jeu installé) : l'étape ne bloque jamais.
  - G4 : on corrige une faute VOLONTAIRE dans une COPIE de quelques textes du jeu (guilde/contribution/, un petit
    dépôt git local préparé par le jeu, sans aucun « remote ») ; aucun vrai fichier de langue du jeu n'est touché.
    Les crédits « contributeur » du jeu sont une structure prête, VIDE (aucune donnée personnelle).
  - G6 : le jeu n'écrit JAMAIS sur un vrai disque ni sur une vraie clé. `dd` et `cp` se pratiquent sur des FICHIERS
    du terrain (une fausse image d'exemple vers un faux fichier cle_usb.img), vérifiés avec sha256sum. Aucune
    commande du jeu ne vise /dev/… ; aucune image n'est téléchargée. L'écriture sur une vraie clé est seulement
    expliquée (avec un adulte, lsblk pour trouver le bon disque, et dd efface tout).
  - Quand un outil manque (git, gcc, make, openscad, tree, rpm…), son étape est cachée ou racontée.

LES PALIERS (gu0 à gu6) : la porte ; G1 le libre (les 4 libertés, la licence d'un petit projet, les licences des
logiciels de la machine, libre ≠ gratuit, et la licence de Terminagotchi lui-même : GPL-3.0-or-later pour le code,
CC BY-NC-SA 4.0 pour les images et le lore) ; G2 lire le vrai code (clone ou copie, tree, grep, « où ta créature
décide-t-elle qu'elle a faim ? », less, et le début du fichier LICENSE du jeu) ; G3 compiler (bonjour.c, gcc, file, od, ldd, make) ; G4 contribuer (une
branche, corriger la faute, git diff, git commit ; la demande de fusion expliquée ; exploit « artisan ») ; G5 fabriquer
(OpenSCAD : le porte-clé, ses coordonnées, son volume, le fichier STL) ; G6 redonner vie à un vieux PC (lsblk,
l'empreinte de l'image, le bon disque, dd vers un FICHIER, le certificat « un PC sauvé »).

Les commandes du jeu (`guilde …`, alias posé par `tg installer`) écrivent dans le carnet de la guilde
(guilde/carnet_de_la_guilde.txt) ce que les étapes vérifient. Mêmes règles sur Android (Guilde.kt, vecteurs communs
donnees/guilde/vecteurs.json), où git, gcc, openscad et lsblk sont racontés.
"""
import datetime
import hashlib
import json
import os
import pkgutil
import random
import re
import shutil
import struct
import subprocess
import sys
import unicodedata
from pathlib import Path

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, SYS_WIN, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "guilde.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def melange(graine, sel, liste):
    l2 = list(liste)
    random.Random(f"{sel}:{graine}").shuffle(l2)
    return l2


def _tire(graine, sel, n):
    return int(hashlib.sha256(f"{graine}:{sel}".encode()).hexdigest()[:8], 16) % n


# ---------------------------------------------------------------- G1 le libre
def libertes_cartes(graine):
    """Les situations à relier à une des 4 libertés (0 utiliser, 1 étudier, 2 partager, 3 améliorer), mélangées :
    [(n°, id, liberté)]."""
    return [(i + 1, x["id"], str(x["rep"])) for i, x in enumerate(melange(graine, "libertes", donnees()["libertes"]["situations"]))]


def gratuit_cartes(graine):
    """Libre (« l ») ou pas libre (« p », même gratuit) : [(n°, id, l|p)]."""
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(melange(graine, "gratuit", donnees()["gratuit"]))]


def quiz_justes(cartes, rep, lettres):
    """(réponse bien formée, [(n°, id) justes]) ; rep : ce que l'enfant a tapé."""
    r = [ascii_bas(x)[:1] for x in rep]
    if len(r) != len(cartes) or any(not x or x not in lettres for x in r):
        return False, []
    return True, [(n, i) for (n, i, rr), x in zip(cartes, r) if x == rr]


def licence_de_texte(texte):
    """La famille de licence reconnue dans un texte (LICENSE, COPYING, copyright Debian…), ou None. L'ordre compte :
    AGPL et LGPL avant GPL."""
    for f in donnees()["licences"]["familles"]:
        if re.search(f["motif"], texte or "", re.I):
            return f["id"]
    return None


def licence_catalogue(nom):
    return donnees()["licences"]["catalogue"].get(ascii_bas(nom).strip())


def genre_licence(fam):
    return next((f["genre"] for f in donnees()["licences"]["familles"] if f["id"] == fam), None)


def nom_licence(fam):
    return next((f["nom"] for f in donnees()["licences"]["familles"] if f["id"] == fam), fam)


# ---------------------------------------------------------------- G2 lire le vrai code
def faim_fichiers(fichiers):
    """Les fichiers (noms) où la créature DÉCIDE qu'elle a faim, dans un ensemble {nom: texte} : ceux qui définissent
    la fonction de l'état (guilde.json, « faim » → « marques ») ; dans une version plus ancienne du jeu, ceux qui
    comptent les secondes par point de faim."""
    for motif in donnees()["faim"]["marques"]:
        r = sorted({os.path.basename(n) for n, txt in fichiers.items() if re.search(motif, txt, re.M)})
        if r:
            return r
    return []


def faim_ok(reponse, attendus):
    """« satiete », « satiete.py », « pc/tg/satiete.py », « Satiété » : le nom du fichier, sans le chemin."""
    r = ascii_bas((reponse or "").strip()).replace("\\", "/").split("/")[-1].split(":")[0]
    if not r:
        return False
    return any(r == a.lower() or r + ".py" == a.lower() or r + ".kt" == a.lower() for a in attendus)


# ---------------------------------------------------------------- G4 contribuer
def faute(graine):
    """La faute volontaire de cette partie : {ligne, juste, faux}."""
    f = donnees()["contribution"]["fautes"]
    return f[_tire(graine, "faute", len(f))]


def texte_contribution(graine, juste=False):
    """Le fichier langues/fr.txt de la copie : les vraies phrases du jeu, avec UNE faute volontaire (sauf juste=True)."""
    c = donnees()["contribution"]
    f = faute(graine)
    lignes = []
    for i, x in enumerate(c["lignes"]):
        txt = x["texte"]
        if i == f["ligne"] and not juste:
            txt = txt.replace(f["juste"], f["faux"], 1)
        lignes.append(f"{x['cle']} = {txt}")
    return "\n".join(c["entete"] + lignes) + "\n"


def correction_ok(texte, graine):
    return (texte or "").replace("\r\n", "\n").rstrip("\n") == texte_contribution(graine, juste=True).rstrip("\n")


# ---------------------------------------------------------------- G5 fabriquer
def piece(graine):
    """Les mesures du porte-clé de cette partie (millimètres) et la place du trou."""
    p = donnees()["piece"]
    L = p["longueurs"][_tire(graine, "longueur", len(p["longueurs"]))]
    l = p["largeurs"][_tire(graine, "largeur", len(p["largeurs"]))]
    h = p["epaisseurs"][_tire(graine, "epaisseur", len(p["epaisseurs"]))]
    return {"longueur": L, "largeur": l, "epaisseur": h, "trou_x": p["trou_x"], "trou_y": l // 2, "trou_d": p["trou_d"]}


def _nombre(x):
    try:
        return float(str(x).strip().replace(",", ".").rstrip("."))
    except ValueError:
        return None


def trou_ok(rep, graine):
    p = piece(graine)
    nb = [_nombre(str(x).strip("[](),;")) for x in rep if str(x).strip("[](),;")]
    return len(nb) >= 2 and nb[0] == p["trou_x"] and nb[1] == p["trou_y"]


def volume(graine):
    p = piece(graine)
    return p["longueur"] * p["largeur"] * p["epaisseur"]


def volume_ok(reponse, graine):
    s = ascii_bas((reponse or "").strip()).replace(" ", "")
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(mm3|mm³|cm3|cm³)?", s)
    if not m:
        return False
    v = float(m.group(1).replace(",", "."))
    if m.group(2) and m.group(2).startswith("cm"):
        v *= 1000
    return abs(v - volume(graine)) < 0.5


def scad_texte(graine, nom):
    p = piece(graine)
    return (f"// {t('gu.scad.titre', nom=nom)}\n// {t('gu.scad.mesures')}\n"
            f"longueur = {p['longueur']};\nlargeur = {p['largeur']};\nepaisseur = {p['epaisseur']};\n\n"
            f"difference() {{\n    cube([longueur, largeur, epaisseur]);\n"
            f"    // {t('gu.scad.trou')}\n"
            f"    translate([{p['trou_x']}, largeur / 2, -1])\n"
            f"        cylinder(h = epaisseur + 2, d = {p['trou_d']}, $fn = 32);\n}}\n")


FACES = [((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0)]), ((0, 0, -1), [(0, 0, 0), (1, 1, 0), (1, 0, 0)]),
         ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1)]), ((0, 0, 1), [(0, 0, 1), (1, 1, 1), (0, 1, 1)]),
         ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 1), (0, 0, 1)]),
         ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1)]), ((0, 1, 0), [(0, 1, 0), (1, 1, 1), (1, 1, 0)]),
         ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 1, 1), (0, 1, 0)]),
         ((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1)]), ((1, 0, 0), [(1, 0, 0), (1, 1, 1), (1, 0, 1)])]


def stl_boite(L, l, h, nom="porte_cle"):
    """Un fichier STL texte : la plaque du porte-clé (une boîte, 12 triangles), quand OpenSCAD manque."""
    out = [f"solid {nom}"]
    for n, tri in FACES:
        out.append("  facet normal " + " ".join(str(v) for v in n))
        out.append("    outer loop")
        for (a, b, c) in tri:
            out.append(f"      vertex {a * L} {b * l} {c * h}")
        out.append("    endloop")
        out.append("  endfacet")
    out.append(f"endsolid {nom}")
    return "\n".join(out) + "\n"


def stl_infos(octets):
    """{n, binaire, dims: [x, y, z]} d'un fichier STL (texte ou binaire), ou None s'il est illisible."""
    pts = []
    tete = octets[:5].lower() == b"solid" and b"facet" in octets[:2000]
    if tete:
        txt = octets.decode("utf-8", "replace")
        n = len(re.findall(r"^\s*facet\s+normal\b", txt, re.M))
        for m in re.finditer(r"^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)", txt, re.M):
            try:
                pts.append(tuple(float(v) for v in m.groups()))
            except ValueError:
                return None
    else:
        if len(octets) < 84:
            return None
        n = struct.unpack_from("<I", octets, 80)[0]
        if len(octets) < 84 + 50 * n:
            return None
        for k in range(n):
            v = struct.unpack_from("<12f", octets, 84 + 50 * k)
            pts += [v[3:6], v[6:9], v[9:12]]
    if not pts:
        return {"n": n, "binaire": not tete, "dims": [0.0, 0.0, 0.0]}
    dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 2) for i in range(3)]
    return {"n": n, "binaire": not tete, "dims": [d + 0.0 for d in dims]}


# ---------------------------------------------------------------- G6 redonner vie
def image_octets():
    """La FAUSSE image d'exemple (64 Kio) : une ligne qui dit ce qu'elle est, puis des octets tirés d'une empreinte
    (toujours les mêmes, sur PC et sur Android). Ce n'est pas un système : on s'en sert pour apprendre dd et sha256sum."""
    im = donnees()["image"]
    tete = im["entete"].encode("ascii")
    out = bytearray(tete)
    k = 0
    while len(out) < im["octets"]:
        out += hashlib.sha256(f"guilde-image:{k}".encode()).digest()
        k += 1
    return bytes(out[:im["octets"]])


def image_sha():
    return hashlib.sha256(image_octets()).hexdigest()


def disques(graine):
    """Le lsblk FICTIF de l'ordinateur à sauver : [{nom, taille, rm, type, point}] ; la clé est le disque amovible dont
    la taille correspond à ce qui est écrit dessus (cle_go), l'autre amovible est un gros disque de sauvegarde."""
    d = donnees()["disques"]
    noms = melange(graine, "disques", d["noms"])
    cle = d["cles"][_tire(graine, "cle", len(d["cles"]))]
    rows = [{"nom": noms[0], "taille": d["sauvegarde"], "rm": 1, "type": "disk", "point": ""},
            {"nom": noms[0] + "1", "taille": d["sauvegarde"], "rm": 1, "type": "part", "point": "/media/SAUVEGARDE"},
            {"nom": noms[1], "taille": cle["lsblk"], "rm": 1, "type": "disk", "point": ""},
            {"nom": noms[1] + "1", "taille": cle["lsblk"], "rm": 1, "type": "part", "point": ""}]
    rows.sort(key=lambda r: r["nom"])
    rows += [{"nom": "nvme0n1", "taille": d["systeme"], "rm": 0, "type": "disk", "point": ""},
             {"nom": "nvme0n1p1", "taille": "600M", "rm": 0, "type": "part", "point": "/boot/efi"},
             {"nom": "nvme0n1p2", "taille": d["systeme_racine"], "rm": 0, "type": "part", "point": "/"}]
    return rows


def cle_disque(graine):
    """(nom du disque qui est la clé, taille écrite sur la clé en Go)."""
    d = donnees()["disques"]
    noms = melange(graine, "disques", d["noms"])
    return noms[1], d["cles"][_tire(graine, "cle", len(d["cles"]))]["go"]


def disque_ok(reponse, graine):
    r = (reponse or "").strip().lower()
    if r.startswith("/dev/"):
        r = r[5:]
    return r == cle_disque(graine)[0]


def disque_erreur(reponse, graine):
    """Pourquoi une mauvaise réponse est fausse : systeme, sauvegarde, partition, inconnu."""
    r = (reponse or "").strip().lower()
    r = r[5:] if r.startswith("/dev/") else r
    rows = {x["nom"]: x for x in disques(graine)}
    if r not in rows:
        return "inconnu"
    if r.startswith("nvme"):
        return "systeme"
    if rows[r]["type"] == "part":
        return "partition"
    return "sauvegarde"


# ---------------------------------------------------------------- l'établi (vue déployée, surveillance)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def etabli_de(morceau):
    """(outil, de, vers) d'une commande (un morceau de ligne), ou None : la première règle de guilde.json."""
    m = (morceau or "").strip()
    for r in donnees()["etabli"]["regles"]:
        if re.search(r["motif"], m):
            return r["outil"], r["de"], r["vers"]
    return None


def etablis_de(ligne):
    out = []
    for m in SEPARATEURS.split(ligne or ""):
        a = etabli_de(m)
        if a:
            out.append(a)
    return out


# ================================================================ l'état, le terrain, le carnet de la guilde
def g_(state):
    c = state.setdefault("guilde", {})
    c.setdefault("faits", [])
    return c


def dossier():
    return core.TERRAIN / "guilde"


CARNET = "carnet_de_la_guilde.txt"


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


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def licences_trouvees():
    """Les logiciels dont l'enfant a trouvé la licence (sans doublon)."""
    return sorted(set(re.findall(r"^\[licence\] (\S+) .*\(ok\)\s*$", carnet(), re.M)))


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, contenu):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            p.write_bytes(contenu)
        else:
            p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def _lire(rel, binaire=False):
    try:
        p = core.TERRAIN / rel
        return p.read_bytes() if binaire else p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def bonjour_c():
    msg = t("gu.bonjour.message").replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return donnees()["code"]["bonjour_c"].replace("@MESSAGE@", msg)


def credits_texte(state=None):
    """Les crédits ; avec `state`, le pseudo du joueur (s'il y est) dans la couleur de son titre de la Guilde."""
    from .entrainement import pseudo_colore
    moi = (((state or {}).get("compte") or {}).get("pseudo") or "").strip().lower()
    c = [x for x in donnees()["credits"]["contributeurs"] if isinstance(x, dict) and x.get("pseudo")]
    return t("gu.meuble.credits") + "\n\n" + ("".join(t("gu.credits.ligne", pseudo=pseudo_colore(state, x["pseudo"]) if moi and
                                                       str(x["pseudo"]).strip().lower() == moi else x["pseudo"],
                                                       n=int(x.get("contributions") or 0))
                                                     + "\n" for x in c) if c else t("gu.credits.vide") + "\n")


def charge_site(state):
    """Ce qui part au site pour le badge « Artisan » : les leçons de la Guilde réussies et la contribution prête.
    Le site recalcule lui-même le grade (jamais envoyé) ; le badge « Contributeur », lui, ne vient que des crédits."""
    from . import histoire
    faits = histoire.h_(state).get("faits", [])
    return {"lecons": [l for l in donnees()["badges"]["artisan"]["lecons"] if l in faits],
            "contribution": contribution_prete(state)}


# ---------------------------------------------------------------- les badges de la Guilde (1er novembre)
# Pas de créature « contributeur » ni de variante réservée : deux BADGES qui grandissent, dessinés comme ceux de la salle
# d'entraînement (badges.py : écusson, galons du grade), et un PSEUDO COLORÉ (pas le nom de la créature) quand l'un d'eux est le titre affiché.
def palier_artisan(lecons, contribution):
    """Le palier du badge « Artisan » (indice dans guilde.json → badges → artisan → paliers, ou -1) avec `lecons`
    leçons de la Guilde réussies et la contribution d'entraînement (G4) prête ou non. On monte dans l'ordre."""
    k = -1
    for i, p in enumerate(donnees()["badges"]["artisan"]["paliers"]):
        if lecons >= p["lecons"] and (contribution or not p["contribution"]):
            k = i
        else:
            break
    return k


def palier_contributeur(n):
    """Le palier du badge « Contributeur » avec n contributions RÉELLES acceptées (-1 : aucune)."""
    k = -1
    for i, p in enumerate(donnees()["badges"]["contributeur"]["paliers"]):
        if n >= p["n"]:
            k = i
        else:
            break
    return k


def contributions_de(pseudo, contributeurs):
    """Le nombre de contributions acceptées d'un pseudo dans les crédits (sans tenir compte des majuscules), ou 0."""
    p = (pseudo or "").strip().lower()
    if not p:
        return 0
    for x in contributeurs or []:
        if isinstance(x, dict) and str(x.get("pseudo", "")).strip().lower() == p:
            try:
                return max(0, int(x.get("contributions") or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def lecons_faites(state):
    from . import histoire
    faits = histoire.h_(state).get("faits", [])
    return sum(1 for l in donnees()["badges"]["artisan"]["lecons"] if l in faits)


def contribution_prete(state):
    from . import recompenses
    return "guilde.artisan" in recompenses.r_(state)["exploits"]


def artisan(state):
    """(palier, échelon ou None, leçons réussies, contribution prête)."""
    n, c = lecons_faites(state), contribution_prete(state)
    k = palier_artisan(n, c)
    return k, (donnees()["badges"]["artisan"]["paliers"][k]["echelon"] if k >= 0 else None), n, c


def contributeur(state):
    """(palier, échelon ou None, contributions acceptées) : le pseudo du recensement retrouvé dans les crédits."""
    from . import recense
    n = contributions_de(recense.compte(state).get("pseudo"), donnees()["credits"]["contributeurs"])
    k = palier_contributeur(n)
    return k, (donnees()["badges"]["contributeur"]["paliers"][k]["echelon"] if k >= 0 else None), n


def couleur_badge(b):
    return donnees()["badges"][b]["couleur"]


def titres(state):
    """Les titres des badges de la Guilde : [(identifiant, texte, couleur)] (Contributeur d'abord)."""
    from .entrainement import nom_echelon
    out = []
    for b, (k, en, *_r) in (("contributeur", contributeur(state)), ("artisan", artisan(state))):
        if en:
            out.append((f"{b}:{en}", t("ent.titre.famille", badge=t(donnees()["badges"][b]["nom"]), echelon=nom_echelon(en)),
                        couleur_badge(b)))
    return out


def progres_artisan(state):
    from .entrainement import nom_echelon
    k, en, n, c = artisan(state)
    P = donnees()["badges"]["artisan"]["paliers"]
    if k + 1 >= len(P):
        return t("gu.badge.artisan.max")
    p = P[k + 1]
    if n >= p["lecons"] and p["contribution"] and not c:
        return t("gu.badge.artisan.contribution", echelon=nom_echelon(p["echelon"]))
    return t("gu.badge.artisan.progres", n=n, s=p["lecons"], echelon=nom_echelon(p["echelon"]))


def progres_contributeur(state):
    from .entrainement import nom_echelon
    k, en, n = contributeur(state)
    P = donnees()["badges"]["contributeur"]["paliers"]
    if k < 0:
        return t("gu.badge.contributeur.aucune")
    if k + 1 >= len(P):
        return t("gu.badge.contributeur.max")
    return t("gu.badge.contributeur.progres", n=n, s=P[k + 1]["n"], echelon=nom_echelon(P[k + 1]["echelon"]))


def lignes_badges(state):
    """Les deux badges de la Guilde dessinés (écusson et grade), leur progression, et ce que colore le nom."""
    from . import badges as B
    from .entrainement import colorer, nom_echelon
    cases = []
    for b, (k, en, *_r), prog in (("artisan", artisan(state), progres_artisan(state)),
                                  ("contributeur", contributeur(state), progres_contributeur(state))):
        nom = t(donnees()["badges"][b]["nom"])
        coul = "\x1b[38;2;" + B._rvb(couleur_badge(b)) + "m"
        cases.append((b if en else None, en, 0, [(nom, coul + BOLD), (nom_echelon(en) if en else "—", coul), (prog, DIM)]))
    out = [f" {_c(215)}{BOLD}🛠 " + t("gu.badges.titre") + RESET, ""] + B.planche(cases, par_ligne=2, largeur_case=38)
    out.append(" " + t("gu.badges.nom", artisan=colorer(t("gu.badge.artisan"), couleur_badge("artisan")),
                         contributeur=colorer(t("gu.badge.contributeur"), couleur_badge("contributeur")),
                         cmd="`tg badges titre`"))
    return out


def meubles(state):
    """Ce que le jeu pose dans la Guilde quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    gr = _graine(state)
    return {"guilde/mur_des_plans.txt": t("gu.meuble.mur", nom=state.get("name", "")) + "\n",
            f"guilde/{CARNET}": t("gu.meuble.carnet") + "\n",
            "guilde/CREDITS.txt": credits_texte(),
            "guilde/petit_projet/LICENSE": donnees()["code"]["licence_mit"],
            "guilde/petit_projet/LISEZMOI.txt": t("gu.meuble.projet") + "\n",
            "guilde/atelier/bonjour.c": bonjour_c(),
            "guilde/atelier/etoiles.c": donnees()["code"]["etoiles_c"],
            "guilde/fabrique/porte_cle.scad": scad_texte(gr, state.get("name", "")),
            "guilde/vieux_pc/LISEZMOI.txt": t("gu.meuble.vieux_pc") + "\n"}


BESOINS = {"gu0": ["mur_des_plans.txt"], "gu1": ["petit_projet/LICENSE"], "gu3": ["atelier/bonjour.c", "atelier/etoiles.c"],
           "gu5": ["fabrique/porte_cle.scad"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de la Guilde : les fichiers dont la leçon a besoin, les ponts des nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists():
            _ecrire("guilde/" + rel, tous["guilde/" + rel])
    if lid == "gu6" and step >= 2 and not (d / "vieux_pc" / IMAGE).exists():
        poser_cle(state)
    if lid == "gu2" and (code_du_jeu() / "pc").is_dir() and not (code_du_jeu() / "LICENSE").exists():
        poser_licences()                      # une copie (ou un clone) d'avant le 1er novembre : sans LICENSE
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = g_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("gu.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("gu.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- la vraie machine (lue, jamais modifiée)
def licence_reelle(nom):
    """(famille, source) de la licence d'un logiciel installé, lue dans /usr/share/licenses/<nom>/ (Fedora) ou
    /usr/share/doc/<nom>/copyright (Debian, Ubuntu) ; sinon le catalogue du jeu ; sinon (None, None). Lecture seule."""
    n = re.sub(r"[^a-z0-9.+_-]", "", ascii_bas(nom))
    if not n:
        return None, None
    if not SYS_WIN:
        for base in (Path("/usr/share/licenses") / n, Path("/usr/share/doc") / n):
            fichiers = []
            if base.is_dir():
                try:
                    fichiers = sorted(p for p in base.iterdir() if p.is_file())
                except OSError:
                    fichiers = []
            if base.parent.name == "doc":
                fichiers = [p for p in fichiers if p.name == "copyright"]
            for p in fichiers[:6]:
                try:
                    with open(p, encoding="utf-8", errors="replace") as f:
                        fam = licence_de_texte(f.read(40000))
                except OSError:
                    fam = None
                if fam:
                    return fam, str(p)
    fam = licence_catalogue(n)
    return (fam, "catalogue") if fam else (None, None)


def code_du_jeu():
    return dossier() / "code_du_jeu"


def poser_copie():
    """Sans réseau : une COPIE locale du vrai code du jeu installé (pc/tg/*.py) dans le terrain, avec un mot qui dit
    d'où elle vient. Rien n'est téléchargé. Renvoie le nombre de fichiers copiés."""
    src = Path(__file__).resolve().parent
    dest = code_du_jeu() / "pc" / "tg"
    n = 0
    try:
        dest.mkdir(parents=True, exist_ok=True)
        for p in sorted(src.glob("*.py")):
            shutil.copyfile(p, dest / p.name)
            n += 1
        (code_du_jeu() / "LISEZMOI_COPIE.txt").write_text(t("gu.copie.lisezmoi") + "\n", encoding="utf-8")
    except OSError:
        pass
    poser_licences()
    return n


def poser_licences():
    """Les licences du jeu (LICENSE : la GPL du code ; LICENSE-images.md : CC BY-NC-SA pour les images et le lore) à la
    racine de la copie, comme dans le dépôt : seulement celles qui manquent (un clone récent les a déjà)."""
    for nom, texte in donnees().get("licences_du_jeu", {}).get("fichiers", {}).items():
        p = code_du_jeu() / nom
        if not p.exists():
            try:
                p.write_text(texte, encoding="utf-8")
            except OSError:
                pass


def fichiers_du_code():
    """{chemin relatif: texte} des fichiers Python (ou Kotlin) du clone ou de la copie, pour la question de la faim."""
    out = {}
    base = code_du_jeu()
    if not base.is_dir():
        return out
    for racine, dossiers, fichiers in os.walk(base):
        dossiers[:] = [x for x in dossiers if x not in (".git", "__pycache__", "node_modules", "build")]
        for f in fichiers:
            if f.endswith((".py", ".kt")):
                p = Path(racine) / f
                try:
                    out[str(p.relative_to(base))] = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    return out


# ---------------------------------------------------------------- G4 : le petit dépôt local de la contribution
CONTRIB = "contribution"
BRANCHE_MOT = "faute"


def _git_la():
    from .vsh.git import git_present
    return git_present()


def _git(args, cwd, timeout=20):
    from .plateforme import terminal_virtuel
    if terminal_virtuel():                     # le petit git du terminal du jeu (Windows)
        from .vsh.git import git_du_jeu
        return git_du_jeu(args, cwd, timeout=timeout)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANGUAGE="C")
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def poser_contribution(state):
    """Le petit dépôt de l'exercice : une COPIE de quelques phrases du jeu avec une faute volontaire, un premier
    commit signé « La Guilde », et l'identité locale de l'apprenti (dans CE dépôt seulement, pas de remote).
    Sans git : seulement les fichiers. Renvoie True si le dossier est prêt."""
    d = dossier() / CONTRIB
    if (d / "langues" / "fr.txt").exists():
        return True
    gr = _graine(state)
    try:
        (d / "langues").mkdir(parents=True, exist_ok=True)
        (d / "langues" / "fr.txt").write_text(texte_contribution(gr), encoding="utf-8")
        (d / "LISEZMOI.txt").write_text(t("gu.contrib.lisezmoi") + "\n", encoding="utf-8")
    except OSError:
        return False
    if _git_la():
        c = donnees()["contribution"]
        base = ["-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
        if _git([*base, "init", "-q"], d)[0] == 0:
            _git(["config", "user.name", c["apprenti_nom"]], d)
            _git(["config", "user.email", c["apprenti_email"]], d)
            _git(["config", "commit.gpgsign", "false"], d)
            _git(["add", "."], d)
            _git([*base, "-c", f"user.name={c['guilde_nom']}", "-c", f"user.email={c['guilde_email']}", "commit", "-q",
                  "-m", c["premier_commit"]], d)
    return True


def contribution_commitee(state):
    """La correction est enregistrée par un commit sur une AUTRE branche que main (git), sans rien pousser."""
    d = dossier() / CONTRIB
    if not (d / ".git").is_dir():
        return False
    code, br = _git(["rev-parse", "--abbrev-ref", "HEAD"], d)
    if code or br.strip() in ("main", "master", "HEAD", ""):
        return False
    code, txt = _git(["show", "HEAD:langues/fr.txt"], d)
    code2, n = _git(["rev-list", "--count", "HEAD"], d)
    return code == 0 and correction_ok(txt, _graine(state)) and code2 == 0 and n.strip().isdigit() and int(n) >= 2


def corrigee(state):
    return correction_ok(_lire(f"guilde/{CONTRIB}/langues/fr.txt"), _graine(state))


# ---------------------------------------------------------------- G6 : la fausse image et la fausse clé
IMAGE = "image_linux_exemple.iso"
CLE = "cle_usb.img"


def poser_cle(state):
    d = "guilde/vieux_pc/"
    _ecrire(d + IMAGE, image_octets())
    _ecrire(d + IMAGE + ".sha256", f"{image_sha()}  {IMAGE}\n")
    _ecrire(d + CLE, b"\0" * donnees()["image"]["cle_octets"])


def cle_copiee():
    b = _lire(f"guilde/vieux_pc/{CLE}", binaire=True)
    return b is not None and hashlib.sha256(b).hexdigest() == image_sha()


# ---------------------------------------------------------------- les leçons
LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
GU = r"^(tg\s+)?guilde\s+"

FS = {
    "gu_libertes": lambda: dans_carnet("libertes"),
    "gu_gratuit": lambda: dans_carnet("gratuit"),
    "gu_licences": lambda: len(licences_trouvees()) >= donnees()["licences"]["a_trouver"],
    "gu_code": lambda: (code_du_jeu() / "pc").is_dir() or (code_du_jeu() / ".git").is_dir(),
    "gu_faim": lambda: dans_carnet("faim"),
    "gu_contribution": lambda: (dossier() / CONTRIB / "langues" / "fr.txt").is_file(),
    "gu_corrige": lambda: corrigee(core.load()),
    "gu_commit": lambda: contribution_commitee(core.load()),
    "gu_trou": lambda: dans_carnet("trou"),
    "gu_volume": lambda: dans_carnet("volume"),
    "gu_stl": lambda: dans_carnet("stl"),
    "gu_disque": lambda: dans_carnet("disque"),
    "gu_copiee": lambda: cle_copiee(),
    "gu_certificat": lambda: (dossier() / "vieux_pc" / "certificat_pc_sauve.txt").is_file(),
}
CREE = {}


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


A, C, F, V = "guilde/atelier", "guilde/contribution", "guilde/fabrique", "guilde/vieux_pc"
LECONS = {
    # la porte de la Guilde
    "gu0": {"titre": "hist.gu0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "guilde"}), "cmd": "cd ~/terrain_terminagotchi/guilde", "ici": "guilde",
         "bravo": ("hist.entree.bravo", {"piece": "guilde"})},
        _n("gu0", 1, cmd="ls", re=LS, ou="guilde"),
        _n("gu0", 2, cmd="cat mur_des_plans.txt", re=LIRE + r".*mur_des_plans", ou="guilde"),
    ]},
    # G1 le libre : les 4 libertés, une licence, les licences de la machine, libre ≠ gratuit
    "gu1": {"titre": "hist.gu1.titre", "skill": None, "steps": [
        _n("gu1", 0, cmd="guilde libertes", re=GU + r"libert[eé]s?\s*$", ou="guilde"),
        _n("gu1", 1, cmd="guilde libertes ? ? ? ?", fs="gu_libertes"),
        _n("gu1", 2, cmd="cat petit_projet/LICENSE", re=LIRE + r".*petit_projet/LICENSE", ou="guilde"),
        _n("gu1", 3, cmd="ls /usr/share/licenses", re=r"^ls\b.*/usr/share/licenses", outil="/usr/share/licenses", win=False),
        _n("gu1", 4, cmd="rpm -q --qf '%{LICENSE}\\n' bash", re=r"^rpm\s+-q\b", outil="rpm+/usr/lib/sysimage/rpm", win=False,
           tout_code=True),   # seulement là où rpm est LE gestionnaire (Fedora, openSUSE) : ailleurs, rpm -q crée ~/.rpmdb
        _n("gu1", 5, cmd="guilde licence ?", fs="gu_licences"),
        _n("gu1", 6, cmd="guilde gratuit", re=GU + r"gratuits?\s*$"),
        _n("gu1", 7, cmd="guilde gratuit ? ? ? ?", fs="gu_gratuit"),
        _n("gu1", 8, cmd="guilde licence terminagotchi", re=GU + r"licen[cs]es?\s+terminagotchi\b"),
    ]},
    # G2 lire du vrai code : le jeu lui-même
    "gu2": {"titre": "hist.gu2.titre", "skill": None, "steps": [
        _n("gu2", 0, cmd="guilde depot", re=GU + r"d[eé]p[oô]t\b", ou="guilde"),
        _n("gu2", 1, cmd="git clone --depth 1 https://github.com/grecdel/terminagotchi.git code_du_jeu",
           re=r"^git\s+clone\b.*terminagotchi", outil="git", reseau=True, ou="guilde"),
        _n("gu2", 2, cmd="guilde copie", fs="gu_code"),
        _n("gu2", 3, cmd="tree -L 2 code_du_jeu", re=r"^(tree|find|ls)\b.*code_du_jeu", ou="guilde",
           repli=["find code_du_jeu -maxdepth 2 -type d"]),
        _n("gu2", 4, cmd='grep -rl "faim" code_du_jeu/pc/tg', re=r"^grep\b.*-\w*r\w*.*faim.*code_du_jeu", ou="guilde", win=False),
        _n("gu2", 5, cmd='grep -rn "def ' 'etat_de" code_du_jeu/pc/tg', re=r"^grep\b.*etat_de.*code_du_jeu", ou="guilde",
           win=False),
        _n("gu2", 6, cmd="guilde faim ?", fs="gu_faim"),
        _n("gu2", 7, cmd="less code_du_jeu/pc/tg/satiete.py", re=LIRE + r".*code_du_jeu.*satiete", ou="guilde", win=False),
        _n("gu2", 8, cmd="head code_du_jeu/LICENSE", re=LIRE + r"(?!.*petit_projet).*\bLICENSE(\s|$)", ou="guilde",
           win=False),   # (aussi `cd code_du_jeu` puis `head LICENSE`)
    ]},
    # G3 compiler : du texte au programme
    "gu3": {"titre": "hist.gu3.titre", "skill": None, "steps": [
        _n("gu3", 0, cmd="guilde compiler", re=GU + r"compil", ou=A),
        _n("gu3", 1, cmd="cat bonjour.c", re=LIRE + r".*bonjour\.c", ou=A),
        _n("gu3", 2, cmd="guilde gcc", re=GU + r"gcc\b", ou=A),
        _n("gu3", 3, cmd="gcc bonjour.c -o bonjour && ./bonjour", re=r"^(gcc|cc|clang)\b.*bonjour\.c", outil="gcc", ou=A,
           win=False),
        _n("gu3", 4, cmd="file bonjour", re=r"^file\b.*bonjour", outil="gcc+file", ou=A, win=False),
        _n("gu3", 5, cmd="od -An -tx1 -N4 bonjour", re=r"^(od|xxd|hexdump)\b.*bonjour", outil="gcc+od", ou=A, win=False),
        _n("gu3", 6, cmd="ldd bonjour", re=r"^ldd\b.*bonjour", outil="gcc+ldd", ou=A, win=False, tout_code=True),
        _n("gu3", 7, cmd="make etoiles && ./etoiles 5", re=r"^make\b.*etoiles", outil="gcc+make", ou=A, win=False),
    ]},
    # G4 contribuer : une branche, la correction, git diff, git commit ; la demande de fusion expliquée
    "gu4": {"titre": "hist.gu4.titre", "skill": None, "steps": [
        _n("gu4", 0, cmd="guilde contribution", fs="gu_contribution", ou="guilde"),
        _n("gu4", 1, cmd="git status", re=r"^git\s+status\b", outil="git", ou=C, win=False),
        _n("gu4", 2, cmd="git switch -c corrige-une-faute", re=r"^git\s+(switch\s+-c|checkout\s+-b)\s+\S", outil="git",
           ou=C, win=False),
        _n("gu4", 3, cmd="cat langues/fr.txt", re=LIRE + r".*fr\.txt", ou=C),
        _n("gu4", 4, cmd="sed -i 's/?/?/' langues/fr.txt", fs="gu_corrige", ou=C, win=False),
        _n("gu4", 5, cmd="git diff", re=r"^git\s+diff\b", outil="git", ou=C, win=False),
        _n("gu4", 6, cmd='git commit -am "Corrige une faute"', fs="gu_commit", outil="git", ou=C, win=False),
        _n("gu4", 7, cmd="git log --oneline", re=r"^git\s+log\b", outil="git", ou=C, win=False),
        _n("gu4", 8, cmd="guilde fusion", re=GU + r"fusion\b", exploit="guilde.artisan"),
    ]},
    # G5 fabriquer : OpenSCAD, le porte-clé, ses coordonnées, son volume, le fichier STL
    "gu5": {"titre": "hist.gu5.titre", "skill": None, "steps": [
        _n("gu5", 0, cmd="guilde piece", re=GU + r"pi[eè]ce\b", ou=F),
        _n("gu5", 1, cmd="cat porte_cle.scad", re=LIRE + r".*porte_cle\.scad", ou=F),
        _n("gu5", 2, cmd="guilde trou ? ?", fs="gu_trou"),
        _n("gu5", 3, cmd="guilde volume ?", fs="gu_volume"),
        _n("gu5", 4, cmd="openscad -o porte_cle.stl porte_cle.scad", re=r"^openscad\b.*-o\s+\S+\.stl", outil="openscad",
           ou=F, win=False, tout_code=True),
        _n("gu5", 5, cmd="guilde stl", fs="gu_stl", ou=F),
        _n("gu5", 6, cmd="head -3 porte_cle.stl", re=LIRE + r".*porte_cle\.stl", ou=F),
    ]},
    # G6 redonner vie à un vieux PC : lsblk, l'empreinte, le bon disque, dd vers un FICHIER, le certificat
    "gu6": {"titre": "hist.gu6.titre", "skill": None, "steps": [
        _n("gu6", 0, cmd="guilde sauver", re=GU + r"(sauver|vieux)", ou=V),
        _n("gu6", 1, cmd="lsblk", re=r"^lsblk\b", outil="lsblk", win=False, tout_code=True),
        _n("gu6", 2, cmd="guilde cle", re=GU + r"cl[eé]\b", ou=V),
        _n("gu6", 3, cmd=f"sha256sum {IMAGE}", re=r"^sha256sum\b.*image_linux", ou=V, win=False),
        _n("gu6", 4, cmd=f"sha256sum -c {IMAGE}.sha256", re=r"^sha256sum\b.*(-c|--check)\b", ou=V, win=False),
        _n("gu6", 5, cmd="guilde disques", re=GU + r"disques\s*$", ou=V),
        _n("gu6", 6, cmd="guilde disque ?", fs="gu_disque"),
        _n("gu6", 7, cmd=f"dd if={IMAGE} of={CLE} bs=64k", fs="gu_copiee", ou=V, win=False),
        _n("gu6", 8, cmd=f"sha256sum {IMAGE} {CLE}", re=r"^sha256sum\b.*cle_usb", ou=V, win=False),
        _n("gu6", 9, cmd="guilde certificat", fs="gu_certificat"),
    ]},
}
CHAPITRE = {"id": "guilde", "n": 16, "piece": "guilde", "famille": "Constructs", "monde": True,
            "lecons": [f"gu{i}" for i in range(7)], "objet": "boite_a_outils", "titre": "batisseur_libre"}


# ================================================================ l'arbre du Carrefour : quand la Guilde s'ouvre
def _monde():
    from . import programme
    return next((x for x in programme.donnees().get("mondes", []) if x["id"] == "guilde"), {})


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
    if "guilde" in deja or histoire.fini(state, "guilde") or not ouvert(state):
        return False
    deja.append("guilde")
    core.log(state, t("gu.ouvert.log"))
    core.say(state, histoire.dire(state, "gu.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"guilde libertes ? ? ? ?": "libertes", "guilde gratuit ? ? ? ?": "gratuit", "guilde licence ?": "licence",
            "guilde faim ?": "faim", "guilde trou ? ?": "trou", "guilde volume ?": "volume", "guilde disque ?": "disque"}
DEV = re.compile(r"(\bof=/dev/|>\s*/dev/(sd|nvme|mmcblk|hd|vd|disk)|\b(cp|cat|tee|dd|mv)\b.*\s/dev/(sd|nvme|mmcblk|hd|vd|disk))")
POUSSE = re.compile(r"(^|[;&|]\s*)(git\s+push\b|gh\s+(pr|repo|auth)\b|git\s+remote\s+add\b)")
INSTALLE = re.compile(r"(^|[;&|]\s*)(sudo\s+)?(dnf|yum|apt|apt-get|zypper|pacman|pip3?|snap|flatpak)\s+(install|-S\b|upgrade|update)")


def indice(step, tapees):
    """Un indice de la Guilde : un sudo, une écriture vers /dev, un trou « ? » recopié, une mauvaise réponse (les
    libertés, libre ou gratuit, la faim, le trou, le volume, le disque), la faute mal corrigée, le clone sans réseau."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(DEV.search(l) for l in lignes):
        return t("gu.indice.dev")
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("gu.indice.sudo")
    if any(POUSSE.search(l) for l in lignes):
        return t("gu.indice.local")
    if "?" in cmd.split() and any(TROU.search(l) for l in lignes if re.match(GU, l) or l.startswith("sed ")):
        return t("gu.indice.trou")
    et = REPONSES.get(cmd)
    if et:
        der = [l for l in carnet().splitlines() if l.startswith(f"[{et}]")]
        if der and not der[-1].endswith("(ok)"):
            if et == "disque":
                m = re.search(r"\((\w+)\)\s*$", der[-1])
                return t("gu.indice.disque." + (m.group(1) if m else "inconnu"))
            if et == "licence" and der[-1].endswith("(inconnu)"):
                return t("gu.indice.licence")
            return t("gu.indice.rep." + et)
    if any(re.match(r"^(gcc|cc|clang)\b.*-o\s*\S+\.c\b", l) for l in lignes):
        return t("gu.indice.gcc_o")
    if step.get("fs") == "gu_code" and any(re.match(r"^git\s+clone\b", l) for l in lignes):
        return t("gu.indice.clone")
    if step.get("fs") == "gu_corrige" and any(re.match(r"^sed\b(?!.*\s-i)", l) for l in lignes):
        return t("gu.indice.sed_i")
    if step.get("fs") == "gu_corrige" and any(l.startswith(("sed", "nano", "vi")) for l in lignes):
        return t("gu.indice.faute")
    if step.get("fs") == "gu_commit" and any(re.match(r"^git\s+commit\b", l) for l in lignes):
        return t("gu.indice.commit")
    if any(re.match(r"^dd\b.*\bif=\S*cle_usb", l) or re.match(r"^cp\s+\S*cle_usb\S*\s+\S*image_linux", l) for l in lignes):
        return t("gu.indice.inverse")
    if step.get("fs") == "gu_copiee" and any(re.match(r"^(dd|cp)\b", l) for l in lignes):
        return t("gu.indice.copie")
    return None


def surveiller(state, lignes):
    """À chaque tour : une écriture vers un vrai disque (/dev/…) — l'alerte la plus forte, à chaque fois ; un git push,
    une demande de fusion ou un remote : tout reste local (une fois) ; une installation : avec un adulte (une fois)."""
    if not dossier().is_dir():
        return False
    c = g_(state)
    for l in lignes or []:
        l = (l or "").strip()
        if DEV.search(l):
            msg = t("gu.garde.dev")
        elif POUSSE.search(l) and not _fait(c, "garde:pousse"):
            msg = t("gu.garde.local")
        elif INSTALLE.search(l) and not _fait(c, "garde:installe"):
            msg = t("gu.garde.installe")
        else:
            continue
        core.say(state, msg, 16)
        core.terminal(state, "⚠ " + msg)
        return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


GUILDE = ["      ┌─┬─┬─┬─┐  ⚙", "   ╭──┴─┴─┴─┴─┴──╮", "   │ ▤ ▤  🛠  ▤ ▤ │", "   │ ▤ ▤ ╭──╮ ▤ ▤ │",
          "  ▁│▁▁▁▁▁│▒▒│▁▁▁▁▁│▁"]


def banniere(largeur=None):
    """L'entrée de la Guilde : l'illustration B13 si elle existe (illustrations.bin, « guilde »), sinon le REPLI dessiné
    en caractères (la maison des artisans et son grand mur de plans)."""
    try:
        from . import scenes
        if scenes.disponible("guilde"):
            return scenes.illustration("guilde", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    cols = [215, 229, 78, 117, 141]
    return [f"  {_c(cols[i % len(cols)])}{l}{RESET}" for i, l in enumerate(GUILDE)]


def aide():
    return banniere() + [f" {_c(215)}{BOLD}🛠 " + t("gu.aide.titre") + RESET] + ["  " + l for l in t("gu.aide.liste").split("\n")]


def lignes_libertes(state, rep):
    c = libertes_cartes(_graine(state))
    if not rep:
        out = [f" {_c(78)}{BOLD}🗽 " + t("gu.libertes.titre") + RESET, ""]
        out += [f"  {BOLD}{k}{RESET} · " + t(f"gu.liberte.{k}") for k in range(4)] + [""]
        out += [f"  {n}. " + t("gu.situation." + i) for n, i, _r in c]
        return out + ["", "  " + t("gu.libertes.aide")]
    bon, justes = quiz_justes(c, rep, "0123")
    if not bon:
        return [t("gu.libertes.aide")]
    out = []
    if len(justes) == len(c):
        noter("libertes", " ".join(rep) + " (ok)")
        out.append(f" {_c(78)}✔ " + t("gu.libertes.ok") + RESET)
    else:
        noter("libertes", " ".join(rep) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("gu.quiz.faux", n=len(justes), total=len(c)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("gu.situation." + i + ".pourquoi"))
    return out


def lignes_gratuit(state, rep):
    c = gratuit_cartes(_graine(state))
    if not rep:
        out = [f" {_c(229)}{BOLD}🎁 " + t("gu.gratuit.titre") + RESET, ""]
        out += [f"  {n}. " + t("gu.gratuit." + i) for n, i, _r in c]
        return out + ["", "  " + t("gu.gratuit.aide")]
    bon, justes = quiz_justes(c, rep, "lp")
    if not bon:
        return [t("gu.gratuit.aide")]
    out = []
    if len(justes) == len(c):
        noter("gratuit", " ".join(rep) + " (ok)")
        out += [f" {_c(78)}✔ " + t("gu.gratuit.ok") + RESET, "  " + t("gu.gratuit.morale")]
    else:
        noter("gratuit", " ".join(rep) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("gu.quiz.faux", n=len(justes), total=len(c)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("gu.gratuit." + i + ".pourquoi"))
    return out


def lignes_licence(arg):
    if not arg:
        return [t("gu.licence.aide", total=donnees()["licences"]["a_trouver"])]
    nom = re.sub(r"[^a-z0-9.+_-]", "", ascii_bas(arg))
    fam, source = licence_reelle(nom)
    if not fam:
        noter("licence", f"{nom or '?'} (inconnu)")
        return [f" {_c(215)}? " + t("gu.licence.inconnue", nom=nom or arg) + RESET]
    noter("licence", f"{nom} {fam} (ok)")
    n = len(licences_trouvees())
    total = donnees()["licences"]["a_trouver"]
    ou_ = t("gu.licence.catalogue") if source == "catalogue" else t("gu.licence.fichier", fichier=source)
    out = [f" {_c(78)}✔ {BOLD}{nom}{RESET} : {nom_licence(fam)}  {DIM}({ou_}){RESET}",
           "  " + t("gu.genre." + genre_licence(fam))]
    if nom == "terminagotchi":                # le jeu lui-même : le code ET les images
        out += ["  " + l for l in t("gu.licence.jeu").split("\n")]
    return out + ["  " + (t("gu.licence.encore", n=n, total=total) if n < total else t("gu.licence.fini", n=n))]


def lignes_depot():
    out = [f" {_c(117)}{BOLD}📦 " + t("gu.depot.titre") + RESET, ""]
    out += ["  " + l for l in t("gu.depot.texte").split("\n")]
    la = shutil.which("git") is not None
    out += ["", "  " + (f"{_c(78)}✔ git{RESET}  " + t("gu.outil.present") if la else f"{DIM}✖ git{RESET}  " + t("gu.depot.sans_git"))]
    noter("depot", "lu (ok)")
    return out


def lignes_copie():
    base = code_du_jeu()
    if (base / ".git").is_dir() and (base / "pc").is_dir():
        n = sum(1 for _ in (base / "pc").rglob("*.py"))
        noter("copie", "clone (ok)")
        return [f" {_c(78)}✔ " + t("gu.copie.clone", n=n) + RESET]
    if base.exists() and not (base / "pc" / "tg").is_dir():
        try:
            if not any(base.iterdir()):
                base.rmdir()
        except OSError:
            pass
    n = poser_copie()
    noter("copie", f"copie {n} (ok)")
    return [f" {_c(78)}✔ " + t("gu.copie.posee", n=n) + RESET, "  " + t("gu.copie.pourquoi")]


def lignes_faim(arg):
    att = faim_fichiers(fichiers_du_code())
    if not (code_du_jeu()).is_dir():
        return [t("gu.faim.sans_code")]
    if not arg:
        return [t("gu.faim.aide")]
    if faim_ok(arg, att):
        noter("faim", f"{att[0]} (ok)")
        out = [f" {_c(78)}✔ " + t("gu.faim.ok", fichier=att[0]) + RESET]
        txt = next((v for k, v in fichiers_du_code().items() if os.path.basename(k) == att[0]), "")
        m = re.search(donnees()["faim"]["marques"][0] + r".*?(?=^\S)", txt, re.M | re.S)
        if m:
            out += [f"  {_c(117)}{l}{RESET}" for l in m.group(0).rstrip().split("\n")[:8]]
        return out + ["  " + t("gu.faim.morale")]
    noter("faim", f"{ascii_bas(arg)[:40]} (faux)")
    return [f" {_c(203)}✖ " + t("gu.faim.faux") + RESET]


def lignes_compiler():
    out = [f" {_c(215)}{BOLD}⚙ " + t("gu.compiler.titre") + RESET, "",
           f"  {_c(117)}📄 bonjour.c{RESET}  ──{_c(215)}⚙ gcc{RESET}──▶  {_c(78)}🧩 bonjour{RESET}  ──▶  ▶ ./bonjour", ""]
    out += ["  " + l for l in t("gu.compiler.texte").split("\n")]
    noter("compiler", "lu (ok)")
    return out


def lignes_gcc():
    la = shutil.which("gcc") is not None and not SYS_WIN
    out = [f" {_c(215)}{BOLD}🔧 " + t("gu.gcc.titre") + RESET, ""]
    if la:
        try:
            v = subprocess.run(["gcc", "--version"], capture_output=True, text=True, timeout=10).stdout.split("\n")[0]
        except (OSError, subprocess.SubprocessError):
            v = "gcc"
        out += [f"  {_c(78)}✔{RESET} {v}", "  " + t("gu.gcc.present")]
    else:
        out += [f"  {DIM}✖ gcc{RESET}", ""] + ["  " + l for l in t("gu.gcc.absent").split("\n")]
    noter("gcc", ("present" if la else "raconte") + " (ok)")
    return out


def lignes_contribution(state):
    pret = poser_contribution(state)
    git = (dossier() / CONTRIB / ".git").is_dir()
    out = [f" {_c(141)}{BOLD}🤝 " + t("gu.contrib.titre") + RESET, ""]
    out += ["  " + l for l in t("gu.contrib.texte").split("\n")]
    out += ["", "  " + (t("gu.contrib.pret_git") if git else t("gu.contrib.pret_sans_git") if pret else t("gu.contrib.rate"))]
    noter("contribution", ("git" if git else "fichiers") + " (ok)")
    return out


def lignes_fusion(state):
    git = (dossier() / CONTRIB / ".git").is_dir()
    fait = contribution_commitee(state) if git else corrigee(state)
    out = [f" {_c(141)}{BOLD}🔀 " + t("gu.fusion.titre") + RESET, ""]
    out += ["  " + l for l in t("gu.fusion.texte").split("\n")]
    out += ["", f"  {_c(78) if fait else _c(215)}" + (t("gu.fusion.prete") if fait else t("gu.fusion.pas_prete")) + RESET]
    out += ["", f" {_c(229)}{BOLD}📜 " + t("gu.credits.titre") + RESET] + ["  " + l for l in credits_texte(state).rstrip().split("\n")]
    noter("fusion", ("prete" if fait else "pas_prete") + " (ok)")
    return out + ["", "  " + progres_contributeur(state) + f"  {DIM}(`guilde badges`){RESET}"]


def dessin_piece(p, trou=True):
    """Le porte-clé vu de dessus, en caractères (1 caractère = 2 mm en largeur, 4 mm en hauteur)."""
    W, H = max(6, p["longueur"] // 2), max(3, p["largeur"] // 4)
    tx, ty = p["trou_x"] // 2, H - 1 - (p["trou_y"] // 4)
    out = ["┌" + "─" * W + "┐"]
    for r in range(H):
        ligne = ["█"] * W
        if trou and r == min(H - 1, max(0, ty)):
            ligne[min(W - 1, tx)] = "○"
        out.append("│" + "".join(ligne) + "│")
    out.append("└" + "─" * W + "┘")
    return out


def lignes_piece(state):
    p = piece(_graine(state))
    out = [f" {_c(215)}{BOLD}🖨 " + t("gu.piece.titre") + RESET, ""]
    out += [f"  {_c(215)}{l}{RESET}" for l in dessin_piece(p)]
    out += ["  " + t("gu.piece.mesures", L=p["longueur"], l=p["largeur"], h=p["epaisseur"]), ""]
    out += ["  " + l for l in t("gu.piece.texte").split("\n")]
    noter("piece", "vue (ok)")
    return out


def lignes_trou(state, rep):
    gr = _graine(state)
    if len(rep) < 2:
        return [t("gu.trou.aide")]
    if trou_ok(rep, gr):
        p = piece(gr)
        noter("trou", f"{p['trou_x']} {p['trou_y']} (ok)")
        return [f" {_c(78)}✔ " + t("gu.trou.ok", x=p["trou_x"], y=p["trou_y"]) + RESET, "  " + t("gu.trou.morale")]
    noter("trou", " ".join(rep[:2]) + " (faux)")
    return [f" {_c(203)}✖ " + t("gu.trou.faux") + RESET]


def lignes_volume(state, arg):
    gr = _graine(state)
    if not arg:
        return [t("gu.volume.aide")]
    if volume_ok(arg, gr):
        v = volume(gr)
        noter("volume", f"{v} (ok)")
        return [f" {_c(78)}✔ " + t("gu.volume.ok", v=v, cm=f"{v / 1000:g}") + RESET, "  " + t("gu.volume.morale")]
    noter("volume", f"{arg} (faux)")
    return [f" {_c(203)}✖ " + t("gu.volume.faux") + RESET]


def lignes_stl(state):
    d = dossier() / "fabrique"
    p = piece(_graine(state))
    f = d / "porte_cle.stl"
    fait_par_jeu = False
    if not f.is_file():
        _ecrire("guilde/fabrique/porte_cle.stl", stl_boite(p["longueur"], p["largeur"], p["epaisseur"]))
        fait_par_jeu = True
    b = _lire("guilde/fabrique/porte_cle.stl", binaire=True) or b""
    inf = stl_infos(b)
    if not inf:
        noter("stl", "illisible (faux)")
        return [f" {_c(203)}✖ " + t("gu.stl.illisible") + RESET]
    out = [f" {_c(215)}{BOLD}🧊 " + t("gu.stl.titre") + RESET, ""]
    if fait_par_jeu:
        out.append(f"  {DIM}" + t("gu.stl.par_le_jeu") + RESET)
    out += [f"  {_c(215)}{l}{RESET}" for l in dessin_piece(p, trou=not fait_par_jeu)]
    x, y, z = inf["dims"]
    out += ["  " + t("gu.stl.infos", n=inf["n"], x=f"{x:g}", y=f"{y:g}", z=f"{z:g}"), "",
            "  " + t("gu.stl.morale"), f"  {DIM}" + t("gu.stl.adulte") + RESET]
    noter("stl", ("jeu" if fait_par_jeu else "openscad") + f" {inf['n']} (ok)")
    return out


def lignes_vieux_pc():
    out = [f" {_c(78)}{BOLD}💻 " + t("gu.vieux.titre") + RESET, ""]
    out += ["  " + l for l in t("gu.vieux.texte").split("\n")]
    noter("vieux_pc", "lu (ok)")
    return out


def lignes_cle(state):
    poser_cle(state)
    out = [f" {_c(117)}{BOLD}💾 " + t("gu.cle.titre") + RESET, ""]
    out += [f"  📀 {IMAGE}  ({donnees()['image']['octets'] // 1024} Kio)", f"  📄 {IMAGE}.sha256",
            f"  🔑 {CLE}  ({donnees()['image']['cle_octets'] // 1024} Kio)", ""]
    out += ["  " + l for l in t("gu.cle.texte").split("\n")]
    noter("cle", "posee (ok)")
    return out


def majmin(nom):
    """Les numéros du pilote (comme lsblk) : sda 8:0, sda1 8:1, sdb 8:16… ; nvme0n1 259:0, nvme0n1p1 259:1…"""
    m = re.fullmatch(r"sd([a-z])(\d*)", nom)
    if m:
        return f"8:{16 * (ord(m.group(1)) - 97) + int(m.group(2) or 0)}"
    m = re.fullmatch(r"nvme0n1(?:p(\d+))?", nom)
    return f"259:{int(m.group(1) or 0) if m else 0}"


def lignes_disques(state):
    gr = _graine(state)
    _nom, go = cle_disque(gr)
    out = [f" {_c(117)}{BOLD}🔍 " + t("gu.disques.titre") + RESET, "", f"  {DIM}" + t("gu.disques.fictif") + RESET, ""]
    out.append(f"  {BOLD}NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS{RESET}")
    rows = disques(gr)
    for k, r in enumerate(rows):
        enfant = r["type"] == "part"
        dernier = k + 1 >= len(rows) or rows[k + 1]["type"] != "part"
        nom = (("└─" if dernier else "├─") if enfant else "") + r["nom"]
        out.append(f"  {nom:<11} {majmin(r['nom']):<7} {r['rm']:>2} {r['taille']:>6}  0 {r['type']:<4} {r['point']}")
    out += ["", "  " + t("gu.disques.question", go=go), f"  {DIM}" + t("gu.disques.aide") + RESET]
    noter("disques", "vus (ok)")
    return out


def lignes_disque(state, arg):
    gr = _graine(state)
    if not arg:
        return [t("gu.disque.aide")]
    if disque_ok(arg, gr):
        nom, go = cle_disque(gr)
        noter("disque", f"{nom} (ok)")
        return [f" {_c(78)}✔ " + t("gu.disque.ok", nom=nom, go=go) + RESET, "  " + t("gu.disque.morale")]
    err = disque_erreur(arg, gr)
    noter("disque", f"{ascii_bas(arg)[:20]} ({err})")
    return [f" {_c(203)}✖ " + t("gu.indice.disque." + err) + RESET]


def lignes_certificat(state):
    if not cle_copiee():
        return [f" {_c(215)}✖ " + t("gu.certificat.pas_encore") + RESET]
    if not dans_carnet("disque"):
        return [f" {_c(215)}✖ " + t("gu.certificat.disque") + RESET]
    date = datetime.date.today().isoformat()
    texte = t("gu.certificat.texte", nom=state.get("name", ""), date=date, empreinte=image_sha()[:16])
    _ecrire("guilde/vieux_pc/certificat_pc_sauve.txt", texte + "\n")
    noter("certificat", "pc_sauve (ok)")
    return [f" {_c(78)}{BOLD}🏅 " + t("gu.certificat.titre") + RESET, ""] + ["  " + l for l in texte.split("\n")] + \
        ["", "  " + t("gu.certificat.morale")]


def commande(args, sortie=None):
    """tg guilde [plan|libertes …|licence NOM|gratuit …|depot|copie|faim FICHIER|compiler|gcc|contribution|fusion|
    credits|piece|trou X Y|volume V|stl|sauver|cle|disques|disque NOM|certificat]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide")).replace("œ", "oe").replace("-", "_")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        g_(st)
        arg = " ".join(reste) if reste else None
        if sous in ("plan", "mur", "regles"):
            lignes.extend(banniere() + t("gu.meuble.mur", nom=st.get("name", "")).split("\n"))
        elif sous in ("libertes", "liberte"):
            lignes.extend(lignes_libertes(st, reste))
        elif sous in ("licence", "licences", "license"):
            lignes.extend(lignes_licence(reste[0] if reste else None))
        elif sous in ("gratuit", "gratuits"):
            lignes.extend(lignes_gratuit(st, reste))
        elif sous in ("depot", "depots"):
            lignes.extend(lignes_depot())
        elif sous == "copie":
            lignes.extend(lignes_copie())
        elif sous == "faim":
            lignes.extend(lignes_faim(reste[0] if reste else None))
        elif sous in ("compiler", "compile", "compilateur"):
            lignes.extend(lignes_compiler())
        elif sous == "gcc":
            lignes.extend(lignes_gcc())
        elif sous in ("contribution", "contribuer"):
            lignes.extend(lignes_contribution(st))
        elif sous in ("fusion", "credits"):
            lignes.extend(lignes_fusion(st))
        elif sous in ("badges", "badge"):
            lignes.extend(lignes_badges(st))
        elif sous in ("piece", "porte_cle"):
            lignes.extend(lignes_piece(st))
        elif sous == "trou":
            lignes.extend(lignes_trou(st, reste))
        elif sous == "volume":
            lignes.extend(lignes_volume(st, arg))
        elif sous == "stl":
            lignes.extend(lignes_stl(st))
        elif sous in ("sauver", "vieux_pc", "vieux", "pc"):
            lignes.extend(lignes_vieux_pc())
        elif sous in ("cle", "cles"):
            lignes.extend(lignes_cle(st))
        elif sous == "disques":
            lignes.extend(lignes_disques(st))
        elif sous == "disque":
            lignes.extend(lignes_disque(st, reste[0] if reste else None))
        elif sous == "certificat":
            lignes.extend(lignes_certificat(st))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
