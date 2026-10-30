"""Les parties : plusieurs créatures rangées dans la maison, une seule active (comme Parties.kt sur Android).

Rangement :
  ~/.terminagotchi/save.json                  la partie ACTIVE (toujours au même endroit : le mode
                                               « prompt » du shell, la fenêtre, le bureau la lisent sans
                                               rien savoir des autres)
  ~/.terminagotchi/parties/index.json         {"active": "<id>", "ordre": ["<id>", …]}
  ~/.terminagotchi/parties/partie_<id>.json   les parties rangées
  ~/.terminagotchi/parties/terrain_<id>/      le terrain de jeu rangé de chaque partie

Choix du terrain : UN TERRAIN PAR PARTIE. Les leçons vérifient des fichiers de ~/terrain_terminagotchi
(nid, repas.txt, carnet git…), les monstres y ont leurs repaires. Le terrain de la partie active est
toujours à cet endroit ; en changeant de partie, il est rangé dans parties/terrain_<id> et celui de
l'autre partie revient. Une nouvelle partie démarre sans terrain : la leçon 1 repart vraiment de zéro
(rien n'est validé d'avance par les fichiers d'une autre créature).
Limite : un terminal resté ouvert DANS le terrain suit le dossier rangé ; il suffit de refaire cd ~.
Si le terrain ne peut pas être déplacé (Windows, dossier ouvert ailleurs), il reste en place, partagé.

Identifiants : « 1 » pour la sauvegarde d'avant (c'est aussi la partie 1 du compte en ligne), puis
8 caractères hexadécimaux au hasard. Rien n'est jamais effacé : une nouvelle partie range l'ancienne.
Tout marche hors ligne ; le compte (clé, pseudo) suit le joueur d'une partie à l'autre.
"""
import json
import os
import random
import time

from . import core

MAX = 10
IDENTITE = ("cle", "pseudo", "serveur", "parties_cache")


def dossier():
    return core.SAVE_DIR / "parties"


def _index_f():
    return dossier() / "index.json"


def _range(i):
    return dossier() / f"partie_{i}.json"


def _terrain_range(i):
    return dossier() / f"terrain_{i}"


def _lire(f):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ecrire(f, o):
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def index():
    """L'index, créé au premier passage : l'ancienne sauvegarde devient la partie 1, active."""
    idx = _lire(_index_f())
    if isinstance(idx, dict):
        return idx
    s = _lire(core.SAVE_FILE)
    idx = {"active": "1", "ordre": []}
    if isinstance(s, dict) and s.get("name"):
        i = str(s.get("partie") or "1")
        idx = {"active": i, "ordre": [i]}
    _ecrire(_index_f(), idx)
    return idx


def active():
    return str(index().get("active", "1"))


def id_de(state):
    return str((state or {}).get("partie") or "1")


def base_de(c):
    """Le compte avec lequel la partie a été synchronisée (son « base » compte pour lui)."""
    return c.get("base_de") or (c.get("pseudo", "") if c.get("base") else "")


def _resume(s, i, est_active, f):
    xp = s.get("xp", 0)
    n = core.level(xp)
    try:
        date = f.stat().st_mtime
    except OSError:
        date = 0
    branche = s.get("branch") or (max(s["stats"], key=s["stats"].get) if s.get("stats") and any(s["stats"].values()) else None)
    return {"id": i, "nom": s.get("name", ""), "niveau": n, "espece": core.forme({"xp": xp, "branch": branche, "espece_compagnon": s.get("espece_compagnon")}, n),
            "shiny": bool(s.get("shiny")), "date": date, "active": est_active}


def liste():
    idx = index()
    act = str(idx.get("active", "1"))
    ids = list(idx.get("ordre", []))
    if act not in ids:
        ids.append(act)
    out = []
    for i in ids:
        f = core.SAVE_FILE if i == act else _range(i)
        s = _lire(f)
        if isinstance(s, dict):
            out.append(_resume(s, i, i == act, f))
    return out


def aucune():
    return not any(p["nom"] for p in liste())


def pleine():
    return len(liste()) >= MAX


def _deplacer(de, vers):
    if not de.exists():
        return True
    if vers.exists():
        return False
    try:
        vers.parent.mkdir(parents=True, exist_ok=True)
        os.replace(de, vers)
        return True
    except OSError:
        return False


def _porter_compte(depuis, vers):
    """Le compte du joueur (clé, pseudo…) passe dans la partie qui devient active."""
    c = vers.setdefault("compte", {})
    source = (depuis or {}).get("compte", {})
    pseudo = source.get("pseudo", "")
    avant = base_de(c)
    for k in IDENTITE:
        if k in source:
            c[k] = source[k]
        elif k != "serveur":
            c.pop(k, None)
    if pseudo and pseudo != avant:
        # jamais synchronisée avec CE compte : tout ce qu'elle a gagné partira à sa première synchro
        c["base"] = {"xp": 0, "total": 0, "colles": 0, "stats": {}}
        c["dernier"] = 0
        c["base_de"] = pseudo


def _basculer(i, nouvelle=None):
    """Range la partie active (sauvegarde + terrain) et installe la partie i. False si rien n'a bougé."""
    with core.verrou():
        idx = index()
        act = str(idx.get("active", "1"))
        if act == i:
            return False
        ids = list(idx.get("ordre", []))
        courant = _lire(core.SAVE_FILE)
        arrivee = nouvelle if nouvelle is not None else _lire(_range(i))
        if not isinstance(arrivee, dict):
            return False
        if isinstance(courant, dict) and courant.get("name"):
            if _range(act).exists():
                return False                       # jamais écraser une partie rangée
            courant["partie"] = act
            _ecrire(_range(act), courant)
            if act not in ids:
                ids.append(act)
            _deplacer(core.TERRAIN, _terrain_range(act))
        elif act in ids:
            ids.remove(act)                        # un état vide : rien à ranger
        arrivee["partie"] = i
        _porter_compte(courant, arrivee)
        # l'historique du shell a continué pendant qu'elle dormait : elle ne mange pas les commandes des autres
        arrivee["offsets"] = {}
        core.read_new_lines(arrivee)
        _ecrire(core.SAVE_FILE, arrivee)
        if nouvelle is None:
            try:
                _range(i).unlink()
            except OSError:
                pass
        if not core.TERRAIN.exists():
            _deplacer(_terrain_range(i), core.TERRAIN)
        if i not in ids:
            ids.append(i)
        _ecrire(_index_f(), {"active": i, "ordre": ids})
        return True


def charger(i):
    return _basculer(str(i))


def _nouvel_id():
    pris = {p["id"] for p in liste()}
    while True:
        i = "".join(random.choice("0123456789abcdef") for _ in range(8))
        if i not in pris and not _range(i).exists() and not _terrain_range(i).exists():
            return i


def nouvelle(nom, langue_code, message_oeuf, intro=False):
    """Une nouvelle partie : l'ancienne est rangée. Renvoie l'id (None si plein ou impossible).
    intro : la partie commence par l'œuf et sa liste de commandes, le jeu s'ouvre petit à petit (intro.py)."""
    if pleine():
        return None
    ancien = _lire(core.SAVE_FILE) or {}
    s = core.migrate(core.new_state(nom[:16] or "Pixel", langue_code))
    if intro:
        from . import intro as I
        I.nouvelle_partie(s)
    if isinstance(ancien.get("config"), dict):
        s["config"] = dict(ancien["config"])        # les réglages de l'appareil suivent (notifications, compagnon)
        s["config"].pop("aura", None)               # l'aura de rareté, elle, se règle partie par partie (tg aura)
    core.log(s, message_oeuf(s))
    core.animer(s, "salut")
    s["notifs"] = []
    i = _nouvel_id()
    return i if _basculer(i, s) else None


def depuis_compte(i, nom, langue_code):
    """Une partie du compte en ligne, pas encore ici : elle arrive vide, la synchro la remplit."""
    if pleine() or any(p["id"] == i for p in liste()):
        return False
    s = core.migrate(core.new_state(nom or "?", langue_code))
    s["notifs"] = []
    return _basculer(str(i), s)


def oublier_compte():
    """Déconnexion : le compte est retiré de TOUTES les parties (l'adresse du site reste)."""
    with core.verrou():
        idx = index()
        act = str(idx.get("active", "1"))
        for i in set(idx.get("ordre", [])) | {act}:
            f = core.SAVE_FILE if i == act else _range(i)
            s = _lire(f)
            if not isinstance(s, dict):
                continue
            c = s.setdefault("compte", {})
            if base_de(c):
                c["base_de"] = base_de(c)
            for k in IDENTITE:
                if k != "serveur":
                    c.pop(k, None)
            _ecrire(f, s)


def date_courte(t):
    return time.strftime("%d/%m %H:%M", time.localtime(t)) if t else ""
