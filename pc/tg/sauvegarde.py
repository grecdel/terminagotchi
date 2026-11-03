"""La sauvegarde exportable : un fichier que l'on peut copier (clé USB, autre dossier, autre ordinateur) et réimporter.

    tg sauvegarde exporter [dossier ou fichier]   → ~/terminagotchi-<nom>-<date>.tgsauve (par défaut)
    tg sauvegarde importer <fichier>              → la créature revient comme une partie de plus

Le fichier (même format sur Android, Sauvegarde.kt) est du JSON lisible :
  {"terminagotchi": "sauvegarde", "version": 1, "plateforme": "pc", "date": …, "nom": …, "niveau": …,
   "controle": "<sha256 de contenu>", "contenu": "<texte JSON : {partie, terrain}>"}
  - partie : l'état de la partie active, SANS le compte (sa clé secrète ne quitte jamais l'appareil : on relie un
    nouvel appareil avec `tg compte code`, comme avant) ;
  - terrain : les fichiers et dossiers du terrain de jeu (avec leurs droits : chmod 444 compte pour les leçons),
    sans les liens symboliques, au plus 2 Mo par fichier et 30 Mo en tout (au-delà : non copiés, et on le dit) ;
  - controle : l'empreinte du contenu (un fichier coupé ou abîmé pendant la copie est reconnu).

Importer ne remplace JAMAIS rien : la partie en cours est rangée (comme `tg partie nouvelle`), la créature importée
devient une partie de plus (10 au plus) ; `tg partie charger` revient à l'autre. Une sauvegarde faite sur le téléphone
ne s'importe pas sur PC (les deux jeux ne rangent pas la partie pareil) : pour avoir la même créature sur les deux,
c'est le compte du jeu (`tg compte code` / `compte lier`).
Rien n'est envoyé nulle part : le fichier reste où l'on l'a mis.
"""
import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path

from . import core, droits
from .langue import t

FORMAT = "sauvegarde"
VERSION = 1
EXTENSION = ".tgsauve"
MAX_FICHIER = 2 << 20
MAX_TOTAL = 30 << 20
MAX_ENTREES = 5000
SECRETS = ("compte",)           # jamais dans le fichier


# ---------------------------------------------------------------- fabriquer le fichier
def _terrain(racine):
    """Les entrées du terrain : [{chemin, dossier?, mode, b64?}], et le nombre de fichiers laissés de côté."""
    out, total, laisses = [], 0, 0
    racine = Path(racine)
    if not racine.is_dir() or racine.is_symlink():
        return out, 0
    for d, sous, fichiers in os.walk(racine, followlinks=False):
        sous.sort()
        rel_d = os.path.relpath(d, racine)
        for nom in sorted(sous):
            p = Path(d) / nom
            if p.is_symlink():
                laisses += 1
                continue
            out.append({"chemin": _rel(rel_d, nom), "dossier": True, "mode": _mode(p)})
        for nom in sorted(fichiers):
            p = Path(d) / nom
            if p.is_symlink() or not p.is_file():
                laisses += 1
                continue
            try:
                taille = p.stat().st_size
                if taille > MAX_FICHIER or total + taille > MAX_TOTAL or len(out) >= MAX_ENTREES:
                    laisses += 1
                    continue
                octets = p.read_bytes()
            except OSError:
                laisses += 1
                continue
            total += len(octets)
            out.append({"chemin": _rel(rel_d, nom), "mode": _mode(p), "b64": base64.b64encode(octets).decode("ascii")})
    return out, laisses


def _rel(d, nom):
    return nom if d in (".", "") else (d.replace(os.sep, "/") + "/" + nom)


def _mode(p):
    try:
        return format(droits.mode(str(p)) & 0o777, "o")
    except OSError:
        return "644"


def fabriquer(state, plateforme="pc", racine=None):
    """Le texte du fichier de sauvegarde (et le nombre d'entrées du terrain laissées de côté)."""
    partie = {k: v for k, v in state.items() if k not in SECRETS}
    terrain, laisses = _terrain(racine or core.TERRAIN)
    contenu = json.dumps({"partie": partie, "terrain": terrain}, ensure_ascii=False)
    entete = {
        "terminagotchi": FORMAT, "version": VERSION, "plateforme": plateforme,
        "date": time.strftime("%Y-%m-%d %H:%M"), "nom": state.get("name", ""),
        "niveau": core.level(state.get("xp", 0)),
        "controle": hashlib.sha256(contenu.encode("utf-8")).hexdigest(),
        "contenu": contenu,
    }
    return json.dumps(entete, ensure_ascii=False, indent=1), laisses


def nom_de_fichier(state, quand=None):
    nom = re.sub(r"[^A-Za-z0-9_-]+", "-", core.nom_propre(state.get("name", "")) or "creature").strip("-") or "creature"
    return f"terminagotchi-{nom}-{time.strftime('%Y-%m-%d', time.localtime(quand))}{EXTENSION}"


# ---------------------------------------------------------------- relire le fichier
class Refus(Exception):
    """Le fichier ne peut pas être importé : la raison, dite à l'enfant (clé de texte + paramètres)."""

    def __init__(self, cle, **p):
        super().__init__(cle)
        self.cle, self.p = cle, p


def lire(texte, plateforme="pc"):
    """Le contenu vérifié d'un fichier de sauvegarde : (entête, partie, terrain). Lève Refus sinon."""
    try:
        o = json.loads(texte)
    except ValueError:
        raise Refus("svg.refus.illisible") from None
    if not isinstance(o, dict) or o.get("terminagotchi") != FORMAT or not isinstance(o.get("contenu"), str):
        raise Refus("svg.refus.illisible")
    if not isinstance(o.get("version"), int) or o["version"] > VERSION:
        raise Refus("svg.refus.version")
    if hashlib.sha256(o["contenu"].encode("utf-8")).hexdigest() != o.get("controle"):
        raise Refus("svg.refus.abime")
    if o.get("plateforme") != plateforme:
        raise Refus("svg.refus.plateforme")
    try:
        c = json.loads(o["contenu"])
    except ValueError:
        raise Refus("svg.refus.abime") from None
    partie, terrain = c.get("partie"), c.get("terrain", [])
    if not isinstance(partie, dict) or not isinstance(partie.get("name"), str) or "xp" not in partie \
            or not isinstance(terrain, list):
        raise Refus("svg.refus.abime")
    return o, partie, terrain


def chemin_sur(chemin):
    """Un chemin du terrain relatif, sans « .. », sans racine ni lecteur : sinon None (jamais écrit)."""
    if not isinstance(chemin, str) or not chemin or "\0" in chemin or "\\" in chemin:
        return None
    morceaux = chemin.split("/")
    if chemin.startswith("/") or any(m in ("", ".", "..") for m in morceaux) or ":" in morceaux[0]:
        return None
    return morceaux


def _poser_terrain(racine, terrain):
    """Écrit le terrain sous racine (un dossier neuf). Renvoie [(chemin, mode)] à poser une fois en place."""
    from . import sur
    racine = Path(racine)
    racine.mkdir(parents=True, exist_ok=False)
    modes = []
    for e in terrain[:MAX_ENTREES]:
        if not isinstance(e, dict):
            continue
        m = chemin_sur(e.get("chemin"))
        if m is None:
            continue
        p = racine.joinpath(*m)
        try:
            mode = int(str(e.get("mode", "644")), 8) & 0o777
        except ValueError:
            mode = 0o644
        if e.get("dossier"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            try:
                octets = base64.b64decode(e.get("b64", ""), validate=True)
            except (ValueError, TypeError):
                continue
            if len(octets) > MAX_FICHIER:
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.is_symlink() or p.is_dir():
                continue
            fd = sur.ouvrir_nofollow(p, mode=0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(octets)
        modes.append(("/".join(m), mode, bool(e.get("dossier"))))
    return modes


def _appliquer_modes(racine, modes):
    # les fichiers d'abord, puis les dossiers du plus profond au moins profond (un dossier 555 n'empêche rien)
    for chemin, mode, dossier in sorted(modes, key=lambda x: (x[2], -x[0].count("/"))):
        try:
            droits.poser(str(Path(racine).joinpath(*chemin.split("/"))), mode)
        except OSError:
            pass


# ---------------------------------------------------------------- les commandes
def exporter(cible=None):
    st = core.load()
    if st is None or not st.get("name"):
        return t("svg.rien")
    texte, laisses = fabriquer(st)
    f = Path(cible).expanduser() if cible else Path.home()
    if f.is_dir():
        f = f / nom_de_fichier(st)
    elif not f.name.endswith(EXTENSION):
        f = f.with_name(f.name + EXTENSION)
    if f.exists():
        return t("svg.existe", fichier=str(f))
    f.parent.mkdir(parents=True, exist_ok=True)
    from . import sur
    fd = sur.ouvrir_nofollow(f, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode=0o644)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texte)
    lignes = [t("svg.exporte", nom=st["name"], fichier=str(f), taille=_taille(len(texte.encode("utf-8"))))]
    if laisses:
        lignes.append(t("svg.laisses", n=laisses))
    lignes.append(t("svg.exporte.astuce", fichier=f.name))
    return "\n".join(lignes)


def _taille(n):
    return f"{max(1, round(n / 1024))} Ko" if n < 1 << 20 else f"{n / (1 << 20):.1f} Mo"


def importer(fichier):
    from . import parties
    if not fichier:
        return t("svg.aide")
    f = Path(fichier).expanduser()
    try:
        if not f.is_file() or f.stat().st_size > MAX_TOTAL * 2:
            return t("svg.introuvable", fichier=str(f))
        texte = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return t("svg.refus.illisible")
    try:
        entete, partie, terrain = lire(texte)
    except Refus as r:
        return t(r.cle, **r.p)
    if parties.pleine():
        return t("svg.plein", max=parties.MAX)
    i = parties._nouvel_id()
    try:
        modes = _poser_terrain(parties._terrain_range(i), terrain)
    except OSError as e:
        from . import sur
        return sur.message_os(e)
    st = core.migrate(dict(partie))
    st["name"] = core.nom_propre(st.get("name", "")) or "Pixel"
    st["partie"] = i
    for k in SECRETS:
        st.pop(k, None)
    if not parties._basculer(i, st):
        return t("svg.refus.place")
    _appliquer_modes(core.TERRAIN if not parties._terrain_range(i).exists() else parties._terrain_range(i), modes)
    return t("svg.importe", nom=st["name"], niveau=core.level(st.get("xp", 0)), date=entete.get("date", "?"))


def commande(args):
    """tg sauvegarde exporter [où] | importer <fichier>"""
    action = (args[0].lower() if args else "")
    if action in ("exporter", "exporte", "export"):
        return exporter(args[1] if len(args) > 1 else None)
    if action in ("importer", "importe", "import"):
        return importer(" ".join(args[1:]) if len(args) > 1 else None)
    return t("svg.aide")
