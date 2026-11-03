"""Le réveil du Terminaworld, de biome en biome, et le monde de la carte (idées 31, 32, 33, 34, 35, 37, 38, 39, 88 ;
maquettes validées le 3 novembre : outils/reveil/planche_reveil.png, outils/ameliorations/monde/planche_*.png).

Les données : donnees/reveil/zones.json (copiée dans pc/tg/reveil.json et les assets Android) : les 10 paysages (la
Racine + 9 biomes), les 15 lieux (bâtiments ou portes), les chemins, les lieux secrets et les habitants (des quêtes de
quetes.py, posées dans les dossiers des mondes), les 12 événements rares, les 8 gardiens du livre.

Deux choses se réveillent, chacune avec sa règle :
  - les PAYSAGES suivent le fil de l'histoire : chapitre 1 → la Racine, chapitre 2 → le biome de l'œuf, chaque aile
    → son biome (s'il est déjà réveillé : la Glace, puis la Roche, qui n'ont pas de chapitre), le Cœur → tout ;
  - les LIEUX suivent les mondes du Carrefour : éteint (monde fermé), lanterne (ouvert), allumé (palier 1 fini),
    ★ au palier 3. Jamais de retour en arrière.
calcul() est la fonction PURE qui décide (mêmes vecteurs que Reveil.kt : donnees/reveil/vecteurs.json), comme
chemin_cd() (la commande que « Y aller » écrit), moment() / saison(), evenement_du_jour() et meteo().

L'image de la carte = le monde vivant (carte_monde.png) et le monde endormi (carte_dort.png, alignés) mélangés pixel
par pixel avec les masques (reveil_masques.png) ; image_carte() le fait avec Pillow (fenêtre), pixels_terminal() en
Python pur (tg carte, dans un terminal qui sait montrer les images).
"""
import datetime
import json
import math
import os
import pkgutil
import re
import struct
import zlib

FERME, LANTERNE, ALLUME = 0.0, 0.45, 1.0
NB_BIOMES = 9                     # la Racine ne compte pas dans « biomes réveillés : 4 / 9 »

_Z = None


def zones():
    global _Z
    if _Z is None:
        try:
            _Z = json.loads(pkgutil.get_data(__package__, "reveil.json").decode("utf-8"))
        except (OSError, TypeError, ValueError):
            _Z = {"taille": [1672, 941], "biomes": {}, "chapitres": {}, "remplacants": [], "lieux": {}, "chemins": {},
                  "pieces": {}, "quetes": [], "evenements": [], "gardiens": [], "moments": {}, "saisons": {},
                  "meteo": {}}
    return _Z


def biomes():
    return list(zones()["biomes"])


def lieux():
    return list(zones()["lieux"])


# ================================================================ les fonctions pures (vecteurs communs avec Kotlin)
def calcul(ailes, oeuf, ouverts, allumes, etoiles):
    """Le réveil d'une partie. ailes : les chapitres finis DANS L'ORDRE où ils l'ont été ; oeuf : le type de l'œuf ;
    ouverts / allumes / etoiles : les mondes du Carrefour ouverts, au palier 1, au palier 3.
    → {"biomes": [réveillés, dans l'ordre], "lieux": {lieu: 0 | 0,45 | 1}, "etoiles": [lieux ★]}"""
    z = zones()
    bs = biomes()
    rev = []
    for a in ailes:
        cible = z["chapitres"].get(a)
        if cible is None:
            continue
        if cible == "tout":
            rev += [b for b in bs if b not in rev]
            continue
        if cible == "oeuf":
            cible = oeuf if oeuf in bs else None
        if cible is None:
            continue
        if cible in rev:                              # déjà réveillé (le biome de l'œuf) : la Glace, puis la Roche
            cible = next((r for r in z["remplacants"] if r not in rev), None)
        if cible:
            rev.append(cible)
    ls = {}
    for l, d in z["lieux"].items():
        m = d.get("monde")
        if m is None:
            ls[l] = ALLUME if l == "camp" or "reveil" in ailes else FERME
        else:
            ls[l] = ALLUME if m in allumes else LANTERNE if m in ouverts else FERME
    return {"biomes": rev, "lieux": ls, "etoiles": [l for l, d in z["lieux"].items() if d.get("monde") in etoiles]}


def signature(etat):
    """Une courte chaîne qui change dès que l'image de la carte change : « 1100000000-2210…-★… »."""
    b = "".join("1" if x in etat["biomes"] else "0" for x in biomes())
    l = "".join("2" if etat["lieux"].get(x) == ALLUME else "1" if etat["lieux"].get(x) == LANTERNE else "0" for x in lieux())
    return b + "-" + l


def depuis_signature(sig):
    bs, _, ls = (sig or "").partition("-")
    return {"biomes": [b for b, c in zip(biomes(), bs) if c == "1"],
            "lieux": {l: ALLUME if c == "2" else LANTERNE if c == "1" else FERME for l, c in zip(lieux(), ls)},
            "etoiles": []}


def chemin_cd(ici, cible):
    """La commande que « Y aller » écrit (sans la lancer) : ici et cible relatifs au terrain (« » = le terrain
    lui-même, « grenier/album »…) ; ici None = hors du terrain. Chemin relatif s'il est court (2 pas au plus), sinon
    complet. None : on y est déjà."""
    c = [x for x in (cible or "").split("/") if x]
    if ici is None:
        return "cd ~/terrain_terminagotchi" + ("/" + "/".join(c) if c else "")
    i = [x for x in ici.split("/") if x]
    n = 0
    while n < min(len(i), len(c)) and i[n] == c[n]:
        n += 1
    monter, descendre = len(i) - n, c[n:]
    if not monter and not descendre:
        return None
    if monter + len(descendre) <= 2:
        return "cd " + "/".join([".."] * monter + descendre)
    return "cd ~/terrain_terminagotchi" + ("/" + "/".join(c) if c else "")


def moment(heure):
    """matin, jour, soir ou nuit (zones.json « moments » : [début, fin[ en heures ; la nuit passe minuit)."""
    for nom, (a, b) in zones()["moments"].items():
        if (a <= heure < b) if a < b else (heure >= a or heure < b):
            return nom
    return "jour"


def saison(mois):
    for nom, ms in zones()["saisons"].items():
        if mois in ms:
            return nom
    return "ete"


def fnv(texte):
    """FNV-1a 32 bits (le même hasard que Reveil.kt, sans dépendre d'une bibliothèque)."""
    h = 0x811C9DC5
    for o in texte.encode("utf-8"):
        h = ((h ^ o) * 0x01000193) & 0xFFFFFFFF
    return h


def evenement_du_jour(graine, jour, reveilles, vus):
    """L'événement rare du jour (au plus un ; un jour sur « evenement_chance » environ), seulement dans un biome
    réveillé ; ceux pas encore vus d'abord : on ne peut pas le « rater », il revient un autre jour. → id ou None."""
    z = zones()
    h = fnv(f"{graine}:{jour}")
    k = max(1, z.get("evenement_chance", 3))
    if h % k:
        return None
    cand = [e for e in z["evenements"] if e["biome"] in reveilles]
    if not cand:
        return None
    pool = [e for e in cand if e["id"] not in vus] or cand
    return pool[(h // k) % len(pool)]["id"]


def premier_mot(ligne):
    m = re.match(r"\s*([^\s|;&]+)", ligne or "")
    return m.group(1).lower() if m else ""


def meteo(cmds, maintenant, avant=None):
    """La météo de la carte (idée 88) d'après les dernières commandes [(ligne, instant en s)] :
    brume (personne ne tape), arc (des tuyaux |), eclairs (le réseau : ping, curl…), pluie (beaucoup de commandes),
    calme. Jamais de mauvais temps pour une erreur (on ne regarde pas les erreurs). Elle ne change pas plus d'une fois
    par minute (avant : (météo, instant du dernier changement)). → (météo, instant du changement)"""
    p = zones()["meteo"]
    cmds = list(cmds)[-10:]
    recent = [l for l, t_ in cmds if maintenant - t_ <= p.get("fenetre_s", 120)]
    if not cmds or maintenant - cmds[-1][1] > p.get("pause_s", 120):
        m = "brume"
    elif any("|" in l for l in recent):
        m = "arc"
    elif any(premier_mot(l) in p.get("reseau", []) for l in recent):
        m = "eclairs"
    elif len(recent) >= p.get("pluie_n", 5):
        m = "pluie"
    else:
        m = "calme"
    if avant is None:
        return m, maintenant
    if m != avant[0] and maintenant - avant[1] >= p.get("garde_s", 60):
        return m, maintenant
    return avant[0], avant[1]


def evenement_visible(vu_t, maintenant):
    """L'événement du jour se voit jusqu'à quelques minutes après qu'on l'a vu (vu_t None : pas encore vu)."""
    return vu_t is None or maintenant - vu_t < zones().get("evenement_duree_s", 300)


# ================================================================ la partie
def r_(state):
    r = state.setdefault("reveil", {})
    for k, v in {"dit": None, "carte": None, "evts": [], "evt": None, "gardiens": [], "meteo": None}.items():
        r.setdefault(k, v)
    return r


def _mondes():
    from . import programme
    return {m["id"]: m for m in programme.donnees().get("mondes", [])}


def mondes_etats(state):
    """(ouverts, allumes, etoiles) : les mondes du Carrefour ouverts, au palier 1, au palier 3."""
    from . import histoire
    h = histoire.h_(state)
    faits = set(h["faits"])
    ouv, allu, eto = [], [], []
    ms = _mondes()
    for l, d in zones()["lieux"].items():
        mid = d.get("monde")
        if not mid or mid not in ms:
            continue
        ch = d.get("chapitre") or mid
        try:
            o = histoire.ouvert(state, ch) or histoire.fini(state, ch)
        except Exception:                            # noqa: BLE001 — le réveil ne casse jamais le jeu
            o = False
        ps = ms[mid].get("paliers") or []
        fin = histoire.fini(state, ch)
        if o or fin:
            ouv.append(mid)
        if fin or (len(ps) > 1 and ps[1] in faits):
            allu.append(mid)
        if fin or (len(ps) > 3 and ps[3] in faits):
            eto.append(mid)
    return ouv, allu, eto


def etat(state):
    from . import histoire, oeufs
    h = histoire.h_(state)
    ouv, allu, eto = mondes_etats(state)
    return calcul(list(h["ailes"]), oeufs.type_de(state), ouv, allu, eto)


def nb_allumes(e):
    return sum(1 for v in e["lieux"].values() if v == ALLUME)


def nb_biomes(e):
    return sum(1 for b in e["biomes"] if b != "racine")


def nom_biome(b):
    from .langue import t
    return t("reveil.biome." + b)


def nom_lieu(l):
    from .langue import t
    return t("reveil.lieu." + l)


def tick(state):
    """À chaque tour (après les leçons et les quêtes) : dire UNE nouvelle à la fois (un biome qui se réveille, un lieu
    qui s'allume, un chemin, un chapitre du livre des gardiens), et poser le livre dans la Bibliothèque du Temps."""
    from . import core
    from .langue import t
    try:
        e = etat(state)
    except Exception:                                # noqa: BLE001
        return
    r = r_(state)
    poser_livre(state)
    avant = r["dit"]
    if avant is None:                                # 1re fois (mise à jour d'une partie déjà avancée) : un résumé
        r["dit"] = {"biomes": list(e["biomes"]), "lieux": {l: v for l, v in e["lieux"].items()}}
        if nb_biomes(e) >= 1 or nb_allumes(e) > 2:
            core.say(state, t("reveil.absence", n=nb_biomes(e), total=NB_BIOMES, l=nb_allumes(e), lt=len(e["lieux"])), 14)
        return
    for b in e["biomes"]:
        if b not in avant["biomes"]:
            avant["biomes"].append(b)
            if b == "racine":
                core.say(state, t("reveil.racine.dit"), 12)
            else:
                core.say(state, t("reveil.biome.dit", biome=nom_biome(b), n=nb_biomes(e), total=NB_BIOMES), 12)
            core.log(state, t("reveil.biome.log", biome=nom_biome(b)))
            return
    for l, v in e["lieux"].items():
        a = avant["lieux"].get(l, FERME)
        if v > a:
            avant["lieux"][l] = v
            if v == ALLUME and l not in ("camp", "carrefour"):
                core.say(state, t("reveil.lieu.dit", lieu=nom_lieu(l)), 10)
            elif v == LANTERNE and l in zones()["chemins"]:
                core.log(state, t("reveil.chemin.dit", lieu=nom_lieu(l)))
            return
    for n in livre_ouverts(state):
        if n not in r["gardiens"]:
            r["gardiens"].append(n)
            core.say(state, t("reveil.gardien.dit", titre=t(f"reveil.gardien.{n}.titre")), 12)
            return


# ---------------------------------------------------------------- le livre des gardiens (idée 37)
def livre_ouverts(state):
    """Les chapitres ouverts (1 à 8) : la boîte de leur gardien est maîtrisée à la Citadelle."""
    try:
        from . import citadelle
        return [i + 1 for i, (boite, _e) in enumerate(zones()["gardiens"])
                if citadelle.dans_carnet("inspecteur", sujet=boite)]
    except Exception:                                # noqa: BLE001
        return []


def fichier_gardien(n):
    return f"temps/livre_des_gardiens/{n}_{zones()['gardiens'][n - 1][1]}.txt"


def poser_livre(state):
    """Le fichier du chapitre, dans la Bibliothèque du Temps, quand ce monde est ouvert (le livre se lit aussi sur la
    carte dès le 1er chapitre)."""
    from . import core, histoire
    from .langue import t
    try:
        if not (histoire.ouvert(state, "temps") or histoire.fini(state, "temps")) or not (core.TERRAIN / "temps").is_dir():
            return
    except Exception:                                # noqa: BLE001
        return
    for n in livre_ouverts(state):
        p = core.TERRAIN / fichier_gardien(n)
        if not p.exists():
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(t(f"reveil.gardien.{n}.titre") + "\n\n" + t(f"reveil.gardien.{n}.texte") + "\n", encoding="utf-8")
            except OSError:
                pass


# ---------------------------------------------------------------- les quêtes du monde (idées 33 et 35)
def quetes():
    """Les quêtes posées dans les dossiers des mondes (zones.json « quetes ») au format de quetes.py : 13 lieux
    secrets (cachettes), 2 trésors (*.secret, à trouver avec find), 26 habitants (le 2e après le palier 2)."""
    out = []
    for q in zones().get("quetes", []):
        but = []
        for b in q["but"]:
            b = list(b)
            if b[0] == "reponse" and isinstance(b[2], dict):
                b[2] = _calcul_reponse(b[2])
            but.append(tuple(b))
        pose = q.get("pose")
        out.append({"id": q["id"], "piece": q["piece"], "sorte": q["sorte"], "fichier": q["fichier"], "but": but,
                    "xp": q["xp"], "objet": None, "titre": None, "pose": (lambda s, p=pose: dict(p)) if pose else None,
                    "win": q.get("win", True), "apres": q.get("apres"), "espece": q.get("espece"), "pos": q.get("pos")})
    return out


def _calcul_reponse(d):
    from . import quetes as Q
    if "lignes" in d:
        return lambda s, f=d["lignes"]: Q._lignes(f)
    if "compte" in d:
        return lambda s, c=d["compte"]: Q._compte(c[0], c[1])
    return lambda s: -1


def _q_monde():
    return {q["id"]: q for q in zones().get("quetes", [])}


def secrets_carte(state):
    """[(id, x, y)] des lieux secrets TROUVÉS (on ne montre jamais ceux qui restent), et (trouvés, total)."""
    from . import quetes as Q
    q = Q.q_(state)
    qs = [x for x in zones().get("quetes", []) if x["sorte"] in ("cachette", "tresor")]
    trouves = [(x["id"], x["pos"][0], x["pos"][1]) for x in qs if x["id"] in q["finies"]]
    return trouves, (len(trouves), len(qs))


def habitants_carte(state):
    """[{id, espece, x, y, besoin, piece, fichier}] : les habitants posés (leur monde est ouvert) ; besoin : la quête
    n'est pas finie (le « ! » jaune)."""
    from . import quetes as Q
    q = Q.q_(state)
    out = []
    for x in zones().get("quetes", []):
        if x["sorte"] != "habitant" or x["id"] not in q["poses"]:
            continue
        out.append({"id": x["id"], "espece": x.get("espece"), "x": x["pos"][0], "y": x["pos"][1], "piece": x["piece"],
                    "besoin": x["id"] not in q["finies"], "active": x["id"] in q["actives"], "fichier": x["fichier"],
                    "xp": x["xp"]})
    return out


def lieu_de_piece(piece):
    for l, d in zones()["lieux"].items():
        if d.get("piece") == piece:
            return l
    return None


# ---------------------------------------------------------------- les lieux sur la carte (idée 32)
def lieux_carte(state, e=None, ici_rel=None):
    """[{id, etat, x, y, nom, titre, biome, palier, paliers, etoile, cmd, habitants, secrets, manque, debut}]."""
    from . import histoire
    from .langue import t
    e = e or etat(state)
    ms = _mondes()
    faits = set(histoire.h_(state)["faits"])
    hab = habitants_carte(state)
    from . import quetes as Q
    finies = set(Q.q_(state)["finies"])
    W, H = zones()["taille"]
    out = []
    for l, d in zones()["lieux"].items():
        v = e["lieux"].get(l, FERME)
        et = "allume" if v == ALLUME else "ouvert" if v == LANTERNE else "ferme"
        cx, cy = d["ellipse"][0], d["ellipse"][1]
        x = {"id": l, "etat": et, "x": cx / W, "y": cy / H, "nom": nom_lieu(l), "biome": d["biome"],
             "etoile": l in e["etoiles"], "palier": 0, "paliers": 0, "cmd": None, "habitants": 0, "secrets": (0, 0),
             "titre": nom_lieu(l), "manque": "", "debut": ""}
        mid = d.get("monde")
        if mid and mid in ms:
            ps = ms[mid].get("paliers") or []
            fin = histoire.fini(state, d.get("chapitre") or mid)
            x["paliers"] = len(ps)
            x["palier"] = len(ps) if fin else sum(1 for p in ps if p in faits)
            x["titre"] = t(f"hist.{d.get('chapitre') or mid}.titre")
            x["debut"] = t(f"hist.{d.get('chapitre') or mid}.debut")
            x["habitants"] = sum(1 for h in hab if h["piece"] == d.get("piece") and h["besoin"])
            sec = [q["id"] for q in zones().get("quetes", []) if q["piece"] == d.get("piece") and q["sorte"] in ("cachette", "tresor")]
            x["secrets"] = (sum(1 for s in sec if s in finies), len(sec))
            if et == "ferme":
                try:
                    x["manque"] = ", ".join(histoire.MONDES_MODS[d.get("chapitre") or mid].manque(state))
                except Exception:                    # noqa: BLE001
                    x["manque"] = ""
            else:
                x["cmd"] = chemin_cd(ici_rel, d.get("piece"))
        elif l == "carrefour":
            x["cmd"] = chemin_cd(ici_rel, "") if et != "ferme" else None
            x["debut"] = t("reveil.lieu.carrefour.apprend")
        else:
            x["cmd"] = chemin_cd(ici_rel, "nid") if histoire.piece_ouverte(state, "nid") else None
            x["debut"] = t("reveil.lieu.camp.apprend")
        out.append(x)
    return out


def chemins_carte(e):
    """[(lieu, points en fractions, état)] : la route d'un lieu prend l'état de son lieu (idée 39)."""
    W, H = zones()["taille"]
    out = []
    for l, pts in zones()["chemins"].items():
        v = e["lieux"].get(l, FERME)
        out.append((l, [(x / W, y / H) for x, y in pts], "allume" if v == ALLUME else "ouvert" if v == LANTERNE else "ferme"))
    return out


def ici_rel(state):
    """Où l'on est, relatif au terrain (« grenier/album »), ou None hors du terrain."""
    from . import core, maison
    i = maison.ici(state)
    if not i:
        return None
    try:
        r = os.path.relpath(os.path.normpath(i), str(core.TERRAIN))
    except ValueError:
        return None
    if r == ".":
        return ""
    if r.startswith(".."):
        return None
    return r.replace(os.sep, "/")


# ---------------------------------------------------------------- l'événement rare du jour (idée 38)
def graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def evenement(state, maintenant=None, jour=None):
    """L'événement du jour s'il se voit maintenant : (id, données) ou None."""
    import time
    maintenant = time.time() if maintenant is None else maintenant
    jour = jour or datetime.date.today().strftime("%Y%m%d")
    r = r_(state)
    try:
        rev = etat(state)["biomes"]
    except Exception:                                # noqa: BLE001
        return None
    ev = r.get("evt") or {}
    # l'événement du jour reste le même toute la journée (une fois vu, il entre dans le carnet)
    eid = ev.get("id") if ev.get("jour") == jour else evenement_du_jour(graine(state), jour, rev, r["evts"])
    if not eid:
        return None
    vu_t = ev.get("t") if ev.get("jour") == jour and ev.get("id") == eid else None
    if not evenement_visible(vu_t, maintenant):
        return None
    return eid, next(e for e in zones()["evenements"] if e["id"] == eid)


def noter_evenement(state, eid, maintenant=None, jour=None):
    """L'événement a été vu (sur la carte) : il entre dans le carnet ; il reste encore quelques minutes."""
    import time
    maintenant = time.time() if maintenant is None else maintenant
    jour = jour or datetime.date.today().strftime("%Y%m%d")
    r = r_(state)
    ev = r.get("evt") or {}
    if ev.get("jour") != jour or ev.get("id") != eid:
        r["evt"] = {"jour": jour, "id": eid, "t": maintenant}
    if eid not in r["evts"]:
        r["evts"].append(eid)
        from . import quetes as Q
        Q.q_(state)["souvenirs"] = (Q.q_(state)["souvenirs"] + [["evenement", eid]])[-200:]


def noter_carte(state, sig):
    r_(state)["carte"] = sig


# ================================================================ l'image de la carte
_MASQUES = {}


def _masques_pil():
    """{nom: image L 960×540} (agrandies une fois depuis reveil_masques.png)."""
    if not _MASQUES:
        import io
        from PIL import Image
        b = Image.open(io.BytesIO(pkgutil.get_data(__package__, "reveil_masques.png"))).convert("L")
        noms = ["b_" + x for x in biomes()] + ["l_" + x for x in lieux()] + ["lumieres", "feuillage"]
        h = b.height // len(noms)
        for i, n in enumerate(noms):
            _MASQUES[n] = b.crop((0, i * h, b.width, (i + 1) * h)).resize((960, 540), Image.BILINEAR)
    return _MASQUES


def _png(nom):
    import io
    from PIL import Image
    return Image.open(io.BytesIO(pkgutil.get_data(__package__, nom))).convert("RGB")


_IMAGES = {}


def alpha_pil(e):
    """Le masque « réveillé » A (0 : endormi, 255 : vivant) de l'état e, en 960×540."""
    from PIL import Image, ImageChops
    M = _masques_pil()
    a = Image.new("L", (960, 540), 0)
    for b in e["biomes"]:
        a = ImageChops.add(a, M["b_" + b])
    for l, v in e["lieux"].items():
        a = Image.composite(Image.new("L", a.size, int(round(v * 255))), a, M["l_" + l])
    return a


def image_carte(sig, quand=None, sais=None):
    """La carte mélangée (PIL RGB 960×540) : l'état sig (signature), le moment de la journée et la saison."""
    cle = (sig, quand, sais)
    if cle in _IMAGES:
        return _IMAGES[cle]
    from PIL import Image
    if "v" not in _IMAGES:
        _IMAGES["v"] = _png("carte_monde.png")
        _IMAGES["d"] = _png("carte_dort.png")
    v, d = _IMAGES["v"], _IMAGES["d"]
    e = depuis_signature(sig)
    a = alpha_pil(e)
    if sais and sais != "ete":
        v = saison_pil(v, sais)
    im = Image.composite(v, d, a)
    if quand and quand != "jour":
        im = moment_pil(im, quand)
    if len(_IMAGES) > 12:
        for k in [k for k in _IMAGES if k not in ("v", "d")]:
            del _IMAGES[k]
    _IMAGES[cle] = im
    return im


def moment_pil(im, quand):
    """Matin rosé, soir orangé, nuit bleue ; les lumières (fenêtres, lanternes, circuits) restent allumées."""
    from PIL import Image, ImageEnhance
    M = _masques_pil()
    if quand == "matin":
        t_ = Image.blend(im, Image.new("RGB", im.size, (255, 205, 190)), 0.18)
    elif quand == "soir":
        t_ = Image.blend(ImageEnhance.Brightness(im).enhance(0.82), Image.new("RGB", im.size, (255, 120, 60)), 0.16)
    else:
        r, g, b = ImageEnhance.Brightness(im).enhance(0.36).split()
        t_ = Image.merge("RGB", (r.point(lambda x: int(x * 0.62)), g.point(lambda x: int(x * 0.74)),
                                 b.point(lambda x: min(255, int(x * 1.25) + 14))))
    force = {"matin": 0.3, "soir": 0.8, "nuit": 1.0}.get(quand, 1.0)
    lum = M["lumieres"].point(lambda x: int(x * force))
    return Image.composite(im, t_, lum)


def saison_pil(v, sais):
    """Le repli calculé des saisons (les illustrations viendront plus tard) : le feuillage change de couleur."""
    from PIL import Image, ImageEnhance
    f = _masques_pil()["feuillage"]
    if sais == "automne":
        g = v.convert("L")
        roux = Image.merge("RGB", (g.point(lambda x: min(255, int(x * 1.6) + 50)), g.point(lambda x: int(x * 0.9) + 10),
                                   g.point(lambda x: int(x * 0.25))))
        return Image.composite(roux, v, f.point(lambda x: int(x * 0.85)))
    if sais == "hiver":
        g = v.convert("L")
        neige = Image.merge("RGB", (g.point(lambda x: min(255, int(x * 0.9) + 60)), g.point(lambda x: min(255, int(x * 0.95) + 66)),
                                    g.point(lambda x: min(255, int(x * 1.05) + 80))))
        return Image.composite(neige, v, f.point(lambda x: int(x * 0.55)))
    if sais == "printemps":
        clair = ImageEnhance.Color(v).enhance(1.12)
        return Image.composite(clair, v, f)
    return v


# ---------------------------------------------------------------- dans le terminal (Python pur)
_MT = {}


def _masques_terminal():
    if not _MT:
        try:
            data = pkgutil.get_data(__package__, "reveil_masques.bin")
        except OSError:
            data = None
        if not data or data[:4] != b"TGM1":
            _MT["_"] = None
            return _MT
        n, w, h = struct.unpack(">BHH", data[4:9])
        i = 9
        _MT["_"] = (w, h)
        for _ in range(n):
            lg = data[i]
            nom = data[i + 1:i + 1 + lg].decode()
            i += 1 + lg
            (z,) = struct.unpack(">I", data[i:i + 4])
            i += 4
            _MT[nom] = zlib.decompress(data[i:i + z])
            i += z
    return _MT


def pixels_terminal(e, W, H, pa=1.0):
    """La carte mélangée en W×H pixels [(r, g, b)] sans aucune bibliothèque (illustrations.bin + reveil_masques.bin)."""
    from . import scenes
    M = _masques_terminal()
    v = scenes.reduire("monde", W, H, 0.5, pa)
    d = scenes.reduire("dort", W, H, 0.5, pa)
    if not M.get("_"):
        return v
    mw, mh = M["_"]
    bs = [M["b_" + b] for b in e["biomes"] if "b_" + b in M]
    ls = [(M["l_" + l], val) for l, val in e["lieux"].items() if "l_" + l in M]
    out = []
    for y in range(H):
        my = min(mh - 1, int(y * mh / H))
        for x in range(W):
            k = my * mw + min(mw - 1, int(x * mw / W))
            a = min(255, sum(m[k] for m in bs)) / 255
            for m, val in ls:
                f = m[k] / 255
                a = a * (1 - f) + f * val
            p, q = v[y * W + x], d[y * W + x]
            out.append((int(q[0] + (p[0] - q[0]) * a), int(q[1] + (p[1] - q[1]) * a), int(q[2] + (p[2] - q[2]) * a)))
    return out


def lignes_carte(state):
    """Les lignes du réveil pour `tg carte` (le terminal n'a pas de clic : la commande à taper est écrite)."""
    from .langue import t
    from .plateforme import BOLD, DIM, RESET, fg
    e = etat(state)
    out = [f" {fg(84)}🌈 " + t("reveil.bilan", n=nb_biomes(e), total=NB_BIOMES, l=nb_allumes(e), lt=len(e["lieux"])) + RESET]
    ici = ici_rel(state)
    for x in lieux_carte(state, e, ici):
        if x["id"] == "camp":
            continue
        marque = {"allume": f"{fg(78)}●", "ouvert": f"{fg(221)}●", "ferme": f"{DIM}●"}[x["etat"]]
        nom = x["nom"] if x["etat"] != "ferme" else "?"
        info = t("reveil.palier", i=x["palier"], n=x["paliers"]) if x["paliers"] and x["etat"] != "ferme" else ""
        cmd = f"  {fg(226)}{x['cmd']}{RESET}" if x["cmd"] else ""
        out.append(f"   {marque}{RESET} {BOLD if x['etat'] != 'ferme' else ''}{nom}{RESET}"
                   f"{' ★' if x['etoile'] else ''} {DIM}{info}{RESET}{cmd}")
    _tr, (n, tot) = secrets_carte(state)
    out.append(" " + t("reveil.secrets.compte", n=n, total=tot))
    r = r_(state)
    out.append(" " + t("reveil.evt.carnet", n=len(r["evts"]), total=len(zones()["evenements"])))
    out.append(" " + t("reveil.livre.compte", n=len(livre_ouverts(state)), total=len(zones()["gardiens"])))
    return out
