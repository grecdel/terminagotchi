"""Mini-combat : quand un monstre sauvage apparaît, une bestiole de ta troupe l'affronte d'abord.

Court (5 tours au plus), au tour par tour, et chaque coup est une VRAIE commande tapée dans le
terminal :
  - la commande de la famille de ta bestiole (« attiree_par » : chmod pour les Démons, ls pour
    les Sylvestres…) → attaque spéciale, 2 cœurs ;
  - ls (ou dir) → observer : tu vois ses stats, tu esquives son coup, et ton coup suivant
    touche à coup sûr (+1 cœur) ;
  - n'importe quelle autre commande → attaque, 1 cœur.
(Pour une bestiole de la famille Sylvestres, ls est sa commande : chez elle, ls observe ET prépare
l'attaque spéciale suivante, voir coup().)

Gagner : le monstre a moins peur (méfiance −40), une épreuve de dressage en moins, l'exemple
s'affiche tout de suite. Perdre : rien de grave, pas de mort — la bestiole fait l'animation « ko »
puis se repose 5 minutes (elle ne combat plus pendant ce temps). Le dressage commence après.

Le combat ne touche pas à l'anti-triche : il ne change aucun champ tiré de la graine.
"""
import random
import time

from . import bestiaire as B
from . import core
from . import equipe
from .langue import t

TOURS_MAX = 5
REPOS = 300                                   # secondes de repos après un KO
BAISSE_PEUR = 40
COEURS_MONSTRE = {"commune": 3, "peu commune": 3, "rare": 4, "épique": 4, "légendaire": 5, "mythique": 5}
BONUS_STADE = {"bebe": 0, "enfant": 0, "ado": 1, "adulte": 1, "ancien": 2}
OBSERVER = {"ls", "dir", "gci", "get-childitem"}


def _borne(x, a, b):
    return max(a, min(b, x))


def repose(ind, maintenant=None):
    return (ind or {}).get("repos", 0) > (maintenant or time.time())


def minutes_de_repos(ind):
    return max(1, round(((ind or {}).get("repos", 0) - time.time()) / 60))


def combattant(state):
    """La bestiole de la troupe qui combat : l'active si elle est reposée, sinon la plus récente reposée."""
    act = equipe.active(state)
    if act and not repose(act) and B.espece(act.get("espece")):
        return act
    for c in reversed(state.get("captures", [])):
        if not repose(c) and B.espece(c.get("espece")):
            return c
    return None


def _ind(state):
    cb = (state.get("dressage") or {}).get("combat") or {}
    return next((c for c in state.get("captures", []) if c.get("id") == cb.get("id")), None)


def en_cours(state):
    cb = (state.get("dressage") or {}).get("combat")
    return bool(cb) and not cb.get("fin")


def preparer(state):
    """Au début d'un dressage : le combat, si tu as une bestiole reposée dans ta troupe."""
    d = state.get("dressage")
    if not d or not state.get("captures"):
        return False
    ind = combattant(state)
    if ind is None:
        core.say(state, t("dress.combat.tous_repos"), 8)
        return False
    e = B.espece(ind["espece"])
    moi = 3 + BONUS_STADE.get(equipe.stade(ind), 0)
    lui = COEURS_MONSTRE.get(d.get("rarete"), 3)
    d["combat"] = {"id": ind["id"], "espece": ind["espece"], "special": e.get("attiree_par") or "",
                   "capacite": e.get("capacite") or "", "moi": [moi, moi], "lui": [lui, lui], "tour": 0,
                   "observe": False, "vu": False, "fin": None, "journal": []}
    core.say(state, t("dress.combat.debut", nom=ind["espece"], monstre=d["espece"], cmd=d["combat"]["special"]), 12)
    return True


def _anim(state, ind, nom):
    """La fenêtre du face-à-face (et l'écran principal sans fenêtre) jouent cette animation de la bestiole."""
    state["anim_troupe"] = {"id": ind["id"], "nom": nom, "t": time.time()}


def coup(state, ligne, rnd=None):
    """Un coup : la commande tapée. Renvoie le résultat du combat s'il vient de finir, sinon None."""
    rnd = rnd or random
    d = state["dressage"]
    cb = d["combat"]
    ind = _ind(state)
    if ind is None:                                        # la bestiole n'est plus là : pas de combat
        return finir(state, "nul")
    cmd = core.first_word(ligne) or ""
    st_t = ind.get("stats") or B.espece(ind["espece"])["stats"]
    st_m = (d.get("ind") or {}).get("stats") or B.espece(d["espece"])["stats"]
    nom, monstre = ind["espece"], d["espece"]
    journal = []
    observe = cmd in OBSERVER
    special = bool(cb["special"]) and cmd == cb["special"]
    if observe and not special:
        cb["observe"] = cb["vu"] = True
        journal.append(t("dress.combat.observe", nom=nom, monstre=monstre, atk=st_m.get("ATK", "?"), **{"def": st_m.get("DEF", "?")}))
    else:
        sur = cb["observe"]
        cb["observe"] = observe                            # ls chez les Sylvestres : attaque ET observe
        p = _borne(0.7 + (st_t.get("VIT", 30) - st_m.get("VIT", 30)) / 60, 0.45, 0.9)
        if sur or rnd.random() < p:
            n = (2 if special else 1) + (1 if sur else 0)
            cb["lui"][0] = max(0, cb["lui"][0] - n)
            journal.append(t("dress.combat.special", nom=nom, capacite=cb["capacite"] or cmd, n=n) if special
                           else t("dress.combat.attaque", nom=nom, n=n))
            if special:
                _anim(state, ind, "attaque")
        else:
            journal.append(t("dress.combat.rate", nom=nom))
    if cb["lui"][0] > 0:                                   # le monstre répond
        if observe:
            journal.append(t("dress.combat.esquive", nom=nom, monstre=monstre))
        elif rnd.random() < _borne(0.45 + (st_m.get("ATK", 30) - st_t.get("DEF", 30)) / 60, 0.2, 0.75):
            cb["moi"][0] = max(0, cb["moi"][0] - 1)
            journal.append(t("dress.combat.touche", nom=nom, monstre=monstre))
        else:
            journal.append(t("dress.combat.manque", monstre=monstre))
    cb["tour"] += 1
    cb["journal"] = (cb["journal"] + journal)[-4:]
    if cb["lui"][0] <= 0:
        return finir(state, "gagne")
    if cb["moi"][0] <= 0:
        return finir(state, "perdu")
    if cb["tour"] >= TOURS_MAX:
        return finir(state, "nul")
    return None


def _plus_dure(d):
    """L'épreuve à retirer après une victoire : la plus difficile qui reste (il en reste toujours au
    moins une de sa famille)."""
    from . import dressage
    reste = [f for f in d["taches"] if f not in d["faites"] and not f.startswith("Rencontre:")]
    if len(reste) < 2:
        return None
    return max(reste, key=lambda f: (dressage._par_id(f)["niveau"], d["taches"].index(f)))


def finir(state, resultat):
    d = state["dressage"]
    cb = d["combat"]
    cb["fin"] = resultat
    ind = _ind(state)
    nom = cb["espece"]
    if resultat == "gagne":
        d["mefiance"] = max(0, d.get("mefiance", 100) - BAISSE_PEUR)
        f = _plus_dure(d)
        if f:
            d["taches"].remove(f)
        d["exemple_tout_de_suite"] = True
        if ind:
            equipe.gagner(state, ind, 20)
            _anim(state, ind, "victoire")
        core.log(state, t("dress.combat.gagne.log", nom=nom, monstre=d["espece"]))
        core.say(state, t("dress.combat.gagne", monstre=d["espece"]), 12)
    elif resultat == "perdu":
        if ind:
            ind["repos"] = time.time() + REPOS
            _anim(state, ind, "ko")
        core.log(state, t("dress.combat.perdu.log", nom=nom))
        core.say(state, t("dress.combat.perdu", nom=nom), 12)
    else:
        core.say(state, t("dress.combat.nul"), 10)
    from . import envies
    envies.plaisir(state, "jeu", "combat")            # gagné ou perdu : on a bien joué
    # le dressage commence maintenant : chrono à zéro, les commandes du combat ne comptent pas
    d["debut"] = time.time()
    d["lignes"] = []
    return resultat


def coeurs(n, maxi):
    from .plateforme import RESET, fg
    return f"{fg(196)}{'❤' * n}{RESET}{fg(240)}{'♡' * (maxi - n)}{RESET}"
