"""Anti-triche : les apparitions tirées d'une « graine » signée par le serveur.

Principe
--------
Le serveur du recensement donne à chaque appareil une graine par jour (quelques jours d'avance,
gardées en cache : le jeu reste jouable hors ligne). Chaque apparition est tirée de façon
DÉTERMINISTE à partir de (graine, compteur) : espèce, variante, shiny, qualité, stats, marque,
humeur, taille, stade, teinte. L'individu garde « graine » (l'identifiant) et « n » (le compteur).
À la synchro, le serveur refait le même tirage : une sauvegarde modifiée à la main ne correspond
plus et la bestiole est marquée « non vérifiée » sur le site.

Sans graine (anciennes sauvegardes, pas de compte, longtemps hors ligne), on tire au hasard comme
avant : la bestiole est jouable, mais « non vérifiée » sur le site.

Spécification (identique en Python, en Kotlin — Tirage.kt — et en JavaScript — site/src/tirage.js)
--------------------------------------------------------------------------------------------------
Tous les calculs sont en entiers. Vecteurs de test communs : donnees/anti_triche/vecteurs.json.

  splitmix64 (modulo 2^64) :
      etat += 0x9E3779B97F4A7C15
      z = etat
      z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9
      z = (z ^ (z >> 27)) * 0x94D049BB133111EB
      sortie = z ^ (z >> 31)
  état de départ = int(valeur[0:16], 16) XOR ((compteur + 1) * 0xD1B54A32D192ED03)
      (valeur = la graine en hexadécimal, 64 caractères ; compteur ≥ 0)
  entier(n)        = sortie % n
  pondere(poids)   = r = entier(somme des poids) ; premier indice i tel que r < poids[0] + … + poids[i]

  Ordre des tirages (chacun consomme toujours ses nombres, même s'il ne sert pas) :
   1. espèce      : pondere(poids) sur les espèces publiques, dans l'ordre du fichier, avec
                    poids = poids_frequence[frequence] × (ATTIRANCE si famille == famille attirée, sinon 1)
                    (famille attirée : celle dont l'enfant vient de taper la commande « attiree_par »,
                    déclarée avec l'apparition dans le champ « attire » ; absente = aucune)
   2. variante    : pondere(round(chance × 10)) sur les variantes de l'espèce
   3. shiny       : entier(chance_shiny) == 0
   4. Abyssor     : entier(15) == 0 ; s'il est permis (3 légendaires et pas encore d'Abyssor), l'espèce
                    devient Abyssor, variante « classique »
   5. qualité q   : entier(1001)  (en millièmes)
   6. stats       : pour chaque stat, dans l'ordre de l'espèce (PV, ATK, DEF, VIT, INT) :
                      bruit = entier(161) + entier(161) + entier(161) − 240
                      v = 31 × (q + bruit) ; iv = 0 si v ≤ 0, sinon min(31, (v + 500) // 1000)
                      stat = base + iv // 2
                    potentiel = (200 × Σiv + 31 × nb) // (62 × nb)
   7. marque      : marques[entier(nb marques)]
   8. humeur      : humeurs[entier(nb humeurs)]
   9. taille      : en dixièmes de cm = (round(taille_cm × 10) × (800 + entier(451)) + 500) // 1000
  10. stade       : pondere([35, 35, 20, 10]) parmi bebe, enfant, ado, adulte
  11. teinte      : (150 + entier(701)) millièmes (gardée seulement si shiny)
  12. note        : en dixièmes, N = 140·Ps·q + 140·Pv·score + 10000·Pp·(puissance − 1) + 140000·Pb·shiny
                    (Ps, Pv, Pp, Pb = poids de rarete.poids ; score de la variante en millièmes)
                    note = min(1000, (N + 7000) // 14000)
      rareté      : le dernier palier dont le seuil (× 10, arrondi) ≤ note ; Abyssor : « mythique »

  L'attirance ne change QUE le tirage 1 (chaque tirage consomme toujours un seul nombre) : shiny,
  qualité, stats… restent ceux du compteur. Le serveur refait le tirage avec la famille déclarée et
  vérifie qu'elle est plausible : une vraie famille, dont la commande fait partie des commandes que
  le joueur a déjà tapées (« vus »).
"""
import time

from . import bestiaire as B

MASQUE = (1 << 64) - 1
VERSION = 1
MAX_APPARITIONS = 200          # apparitions au plus par graine (par jour et par appareil)
POIDS_STADES = [35, 35, 20, 10]
ATTIRANCE = 4                  # la famille attirée pèse 4 fois plus lourd (≈ 10 % → ≈ 30 % des apparitions)


def poids_especes(pub, attire=None):
    """Le poids de chaque espèce publique au tirage 1 (entiers)."""
    pf = B.donnees()["poids_frequence"]
    return [pf[x["frequence"]] * (ATTIRANCE if attire and x["famille"] == attire else 1) for x in pub]


class Hasard:
    """splitmix64, état de départ tiré de la graine et du compteur."""

    def __init__(self, valeur, compteur):
        self.etat = (int(valeur[:16], 16) ^ (((compteur + 1) * 0xD1B54A32D192ED03) & MASQUE)) & MASQUE

    def suivant(self):
        self.etat = (self.etat + 0x9E3779B97F4A7C15) & MASQUE
        z = self.etat
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASQUE
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASQUE
        return z ^ (z >> 31)

    def entier(self, n):
        return self.suivant() % n

    def pondere(self, poids):
        r = self.entier(sum(poids))
        cumul = 0
        for i, p in enumerate(poids):
            cumul += p
            if r < cumul:
                return i
        return len(poids) - 1


def note_entiere(e, vid, q, shiny):
    """Note en dixièmes (0…1000), tout en entiers (q en millièmes)."""
    r = B.donnees()["rarete"]
    p = r["poids"]
    score = round(B.variante(e, vid).get("score", 0) * 1000)
    n = (140 * p["stats"] * q + 140 * p["variante"] * score
         + 10000 * p["puissance"] * (e.get("puissance", 1) - 1) + 140000 * p["bonus_shiny"] * (1 if shiny else 0))
    return min(1000, (n + 7000) // 14000)


def rarete_entiere(e, note10):
    r = B.donnees()["rarete"]
    if e["id"] in r.get("speciales", {}):
        return r["speciales"][e["id"]]
    nom = "commune"
    for seuil, palier in r["paliers"]:
        if note10 >= round(seuil * 10):
            nom = palier
    return nom


def tirer(valeur, compteur, abyssor_permis=False, attire=None):
    """Le tirage complet d'une apparition. Renvoie (espèce, champs de l'individu).
    attire : la famille attirée (ou None)."""
    d = B.donnees()
    h = Hasard(valeur, compteur)
    pub = B.publiques()
    e = pub[h.pondere(poids_especes(pub, attire))]
    v = e["variantes"][h.pondere([round(x["chance"] * 10) for x in e["variantes"]])]["id"]
    shiny = h.entier(d["chance_shiny"]) == 0
    if h.entier(15) == 0 and abyssor_permis:
        e, v = B.espece("Abyssor"), "classique"
    q = h.entier(1001)
    iv = {}
    for k in e["stats"]:
        bruit = h.entier(161) + h.entier(161) + h.entier(161) - 240
        x = 31 * (q + bruit)
        iv[k] = 0 if x <= 0 else min(31, (x + 500) // 1000)
    marque = d["marques"][h.entier(len(d["marques"]))]
    humeur = d["humeurs"][h.entier(len(d["humeurs"]))]
    taille10 = (round(e["taille_cm"] * 10) * (800 + h.entier(451)) + 500) // 1000
    stade = B.STADES[h.pondere(POIDS_STADES)]
    teinte = 150 + h.entier(701)
    note10 = note_entiere(e, v, q, shiny)
    nb = len(iv)
    champs = {
        "espece": e["nom"],
        "variante": v,
        "shiny": shiny,
        "marque": marque,
        "humeur": humeur,
        "taille": taille10 / 10,
        "qualite": q / 1000,
        "potentiel": (200 * sum(iv.values()) + 31 * nb) // (62 * nb),
        "stats": {k: b + iv[k] // 2 for k, b in e["stats"].items()},
        "note": note10 / 10,
        "rarete": rarete_entiere(e, note10),
        "stade": stade,
    }
    if shiny:
        champs["teinte"] = teinte / 1000
    return e, champs


# ---------------------------------------------------------------- les graines en cache (state["compte"])
def jour_local(t=None):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def graine_du_jour(state, t=None):
    """(identifiant, valeur) de la graine d'aujourd'hui pour cet appareil, ou None."""
    c = state.get("compte") or {}
    jour = jour_local(t)
    for gid, val in (c.get("graines") or {}).items():
        if gid.split(".")[0] == jour and isinstance(val, str) and len(val) >= 16:
            return gid, val
    return None


def ranger_graines(state, graines, t=None):
    """Garde les graines reçues du serveur (et oublie celles de plus de 2 jours)."""
    c = state.setdefault("compte", {})
    cache = c.setdefault("graines", {})
    for g in graines or []:
        if isinstance(g, dict) and isinstance(g.get("id"), str) and isinstance(g.get("valeur"), str):
            cache[g["id"]] = g["valeur"]
    limite = jour_local((t or time.time()) - 2 * 86400)
    for gid in [k for k in cache if k.split(".")[0] < limite]:
        del cache[gid]
        c.get("apparitions", {}).pop(gid, None)


def apparition(state, zone_de, abyssor_permis=False, attire=None):
    """Une apparition tirée de la graine du jour (vérifiable par le serveur), ou None s'il n'y en a pas.

    zone_de(espèce, variante) donne le dossier où elle se cache. attire : la famille attirée (ou None),
    gardée dans l'individu (« attire ») pour que le serveur refasse le même tirage. Renvoie (espèce, individu)."""
    g = graine_du_jour(state)
    if not g:
        return None
    gid, valeur = g
    c = state["compte"]
    compteurs = c.setdefault("apparitions", {})
    n = compteurs.get(gid, 0)
    if n >= MAX_APPARITIONS:
        return None
    compteurs[gid] = n + 1
    e, champs = tirer(valeur, n, abyssor_permis, attire)
    ind = B.individu(e, champs["shiny"], zone_de(e, champs["variante"]), champs["variante"])
    ind.update(champs)
    ind["graine"] = gid
    ind["n"] = n
    if attire:
        ind["attire"] = attire
    return e, ind
