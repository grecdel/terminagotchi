"""Les mondes font apparaître des créatures (docs/programme.md § 7.6) : les exploits débloquent des rencontres.

Chaque monde (programme.json, « mondes ») a ses types attirés et ses exploits. Un exploit donne des FAVEURS :
  - « variante »   (bonus_variante rencontres) : à chaque apparition, le jeu essaie jusqu'à essais_variante
                   compteurs de la graine et garde la première créature d'un type du monde dans une variante rare
                   (pas « classique »), sinon la première d'un type du monde, sinon la toute première ;
  - « legendaire » (bonus_legendaire rencontre) : jusqu'à essais_legendaire compteurs, la première légendaire,
                   sinon la toute première.
  - « gardien »    (bonus_gardien rencontres) : jusqu'à essais_gardien compteurs, le premier GARDIEN de la boîte
                   maîtrisée (« gardiens » du monde : boîte → espèce), sinon le tout premier.
Les variantes « réservées » d'un monde (variantes_reservees) n'apparaissent qu'une fois un de ses exploits réussi.

Le glitch (glitch.py, tirage.glitch) : chaque créature a 1 chance sur 4096 d'être glitch ; le gardien d'une boîte
maîtrisée de la Citadelle (exploit « gardien », champ « boite »), chaque fois qu'il apparaît, 1 chance sur 8.
L'individu le déclare (« gardien » : la boîte) pour que le serveur refasse le même tirage. On ne le reçoit jamais :
il faut le rencontrer, puis le dresser.

Le tirage lui-même ne change PAS (pc/tg/tirage.py, Tirage.kt, site/src/tirage.js) : chaque créature reste le tirage
exact d'un (graine, compteur), vérifié par le serveur comme les autres. Le jeu choisit seulement QUEL compteur il
garde parmi quelques-uns (comme pour le tout premier monstre facile) : les compteurs écartés ne servent jamais, le
serveur refuse toujours un compteur utilisé deux fois et en garde au plus 200 par jour. On rencontre donc plus
souvent les créatures du monde, sans jamais les recevoir : il faut toujours les dresser (§ 7.6, « tirage au
hasard »). Mêmes règles dans l'appli Android (Recompenses.kt) ; vecteurs communs donnees/recompenses/vecteurs.json,
vérifiés aussi par le serveur (site/test/tirage.mjs).
"""
import time

from . import programme
from .langue import t

REPETABLES = ("entrainement.serie_parfaite",)      # chaque nouvelle série parfaite redonne une faveur


def conf():
    return programme.donnees().get("recompenses", {})


def mondes():
    return programme.donnees().get("mondes", [])


def exploit_def(eid):
    """(monde, exploit) d'un identifiant d'exploit, ou (None, None)."""
    for m in mondes():
        for x in m.get("exploits", []):
            if x["id"] == eid:
                return m, x
    return None, None


def r_(state):
    r = state.setdefault("recompenses", {})
    r.setdefault("exploits", {})
    r.setdefault("faveurs", [])
    r.setdefault("serie", 0)
    return r


def gardiens():
    """{boîte: identifiant de l'espèce gardienne} (les 8 boîtes de la Citadelle, codées ou annoncées)."""
    out = {}
    for m in mondes():
        out.update(m.get("gardiens", {}))
    return out


def boites_maitrisees(state):
    """Les boîtes maîtrisées (leur exploit « gardien » est réussi)."""
    faits = r_(state)["exploits"]
    return [x["boite"] for m in mondes() for x in m.get("exploits", [])
            if x.get("recompense") == "gardien" and x.get("boite") and x["id"] in faits]


def gardien_de(state, e):
    """La boîte maîtrisée dont cette espèce est le gardien, ou None."""
    eid = (e.get("id") if isinstance(e, dict) else getattr(e, "id", None)) or ""
    g = gardiens()
    return next((b for b in boites_maitrisees(state) if g.get(b) == eid), None)


def _nom_espece(eid):
    from . import bestiaire
    e = bestiaire.espece(eid)
    return e["nom"] if e else eid


def exploit(state, eid, maintenant=None):
    """Un exploit réussi : la faveur qu'il donne. Renvoie le texte à dire, ou None (inconnu, ou déjà fait)."""
    m, x = exploit_def(eid)
    if not x:
        return None
    r = r_(state)
    if eid in r["exploits"] and eid not in REPETABLES:
        return None
    r["exploits"][eid] = int(maintenant if maintenant is not None else time.time())
    n = conf().get("bonus_" + x["recompense"], 1)
    r["faveurs"].append({"exploit": eid, "reste": n})
    if x["recompense"] == "gardien":
        return t("recomp.gardien", boite=t("cit.boite." + x["boite"]), espece=_nom_espece(gardiens().get(x["boite"], "")))
    return t("recomp.exploit", exploit=t(x["nom"]), n=n)


def faveur(state):
    """La faveur active (la plus ancienne qui reste), ou None."""
    for f in r_(state)["faveurs"]:
        if f.get("reste", 0) > 0 and exploit_def(f.get("exploit"))[1]:
            return f
    return None


def _type(e, vid):
    from . import guide
    return guide.type_de(e, vid)


def _rarete(c):
    if c.get("rarete"):
        return c["rarete"]
    from . import bestiaire
    return bestiaire.rarete_de(c)


def _id(e):
    return (e.get("id") if isinstance(e, dict) else getattr(e, "id", None)) or ""


def choisir(candidats, genre, types, cible=None):
    """L'indice du candidat gardé parmi [(espèce, champs)] (dans l'ordre des compteurs).
    cible : l'espèce gardienne (genre « gardien »)."""
    if genre == "gardien":
        return next((i for i, (e, _c) in enumerate(candidats) if _id(e) == cible), 0)
    if genre == "legendaire":
        return next((i for i, (_e, c) in enumerate(candidats) if _rarete(c) == "légendaire"), 0)
    rare = next((i for i, (e, c) in enumerate(candidats)
                 if c.get("variante", "classique") != "classique" and _type(e, c.get("variante")) in types), None)
    if rare is not None:
        return rare
    return next((i for i, (e, c) in enumerate(candidats) if _type(e, c.get("variante")) in types), 0)


def reussi(genre, types, e, champs, cible=None):
    """Le candidat gardé est bien celui que l'exploit attire (sinon : la rencontre normale)."""
    if genre == "gardien":
        return _id(e) == cible
    if genre == "legendaire":
        return _rarete(champs) == "légendaire"
    return _type(e, champs.get("variante")) in types


def reservee(state, e, vid):
    """La variante est réservée par un monde dont aucun exploit n'est encore réussi. Une réservation vaut pour toutes
    les espèces (« orage ») ou pour une seule (« plumange:orage », l'identifiant de l'espèce avant les deux-points)."""
    faits = r_(state)["exploits"]
    eid = (e.get("id") if isinstance(e, dict) else getattr(e, "id", None)) or ""
    for m in mondes():
        res = m.get("variantes_reservees", [])
        if (vid in res or f"{eid}:{vid}" in res) and not any(x["id"] in faits for x in m.get("exploits", [])):
            return True
    return False


def favoriser(valeur, n0, genre, types, abyssor_permis=False, attire=None, cible=None):
    """Spécification pure (vecteurs communs) : le compteur gardé et le tirage, de n0 à n0 + essais − 1."""
    from . import tirage
    essais = conf().get("essais_" + genre, 1)
    cands = [tirage.tirer(valeur, n0 + k, abyssor_permis, attire) for k in range(essais)]
    i = choisir(cands, genre, types, cible)
    return n0 + i, cands[i][1]


def marquer_glitch(state, e, ind):
    """Après le choix de l'apparition : le gardien d'une boîte maîtrisée le déclare (« gardien »), puis le glitch est
    tiré (à part : tirage.glitch, de la même graine ; au hasard sans graine). Renvoie le texte à dire, ou None."""
    from . import tirage
    b = gardien_de(state, e)
    if b:
        ind["gardien"] = b
    else:
        ind.pop("gardien", None)
    v = tirage.valeur_de(state, ind)
    g = tirage.glitch(v, ind["n"], bool(b)) if v else tirage.glitch_au_hasard(bool(b))
    if g:
        ind["glitch"] = True
    else:
        ind.pop("glitch", None)
    if not g:
        return None
    return t("recomp.glitch_gardien" if b else "recomp.glitch", espece=ind.get("espece", ""))


def apparition(state, premiere, tirer_un):
    """Après le tirage normal (premiere = (espèce, individu)) : la faveur d'un exploit et les variantes réservées.
    tirer_un() fait l'apparition suivante (compteur suivant de la graine, ou hasard local), ou None.
    Renvoie ((espèce, individu), texte à dire ou None)."""
    cands = [premiere]
    texte = None
    f = faveur(state)
    if f:
        m, x = exploit_def(f["exploit"])
        genre, types = x["recompense"], m.get("types", [])
        cible = m.get("gardiens", {}).get(x.get("boite")) if genre == "gardien" else None
        essais = conf().get("essais_" + genre, 1)
        while len(cands) < essais:
            c = tirer_un()
            if c is None:
                break
            cands.append(c)
        i = choisir([(e, ind) for e, ind in cands], genre, types, cible)
        f["reste"] -= 1
        r_(state)["faveurs"] = [g for g in r_(state)["faveurs"] if g.get("reste", 0) > 0]
        if reussi(genre, types, *cands[i], cible=cible):
            texte = t("recomp.rencontre", exploit=t(x["nom"]))
        e, ind = cands[i]
    else:
        e, ind = premiere
    for _ in range(4):                      # une variante réservée (monde pas encore réussi) : la suivante
        if not reservee(state, e, ind.get("variante", "classique")):
            break
        c = tirer_un()
        if c is None:
            break
        e, ind = c
    return (e, ind), texte


def serie(state, medaille):
    """Salle d'entraînement : une médaille de plus. 5 en or ou diamant de suite = une série parfaite (exploit)."""
    r = r_(state)
    r["serie"] = r["serie"] + 1 if medaille in ("or", "diamant") else 0
    if r["serie"] >= conf().get("serie_parfaite", 5):
        r["serie"] = 0
        return exploit(state, "entrainement.serie_parfaite")
    return None
