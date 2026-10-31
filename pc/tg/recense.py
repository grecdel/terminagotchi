"""Recensement : un compte en ligne pour avoir LA MÊME créature sur PC et téléphone.

Comment ça marche :
  - `compte creer Pseudo` crée le compte (aucun mot de passe : l'appareil garde une clé secrète) ;
  - `compte code` donne un code à 6 caractères, valable 10 minutes ;
  - sur l'autre appareil, `compte lier CODE` le relie au même compte ;
  - ensuite tout se synchronise tout seul : chaque appareil envoie ce qu'il a GAGNÉ depuis
    la dernière fois, le serveur additionne et renvoie la créature commune.
"""
import json
import threading
import time
import urllib.error
import urllib.request

from . import core
from . import tirage
from .langue import t

INFO = "https://raw.githubusercontent.com/grecdel/terminagotchi-android/site-info/url.txt"
APPAREIL = "pc"
INTERVALLE = 60          # secondes minimum entre deux synchros automatiques
COMPTEURS = ("xp", "total", "colles")

_fil = None


def compte(state):
    return state.setdefault("compte", {})


def requete(url, methode="GET", corps=None, cle=None, delai=10):
    data = json.dumps(corps).encode("utf-8") if corps is not None else None
    req = urllib.request.Request(url, data=data, method=methode,
                                 headers={"content-type": "application/json", "user-agent": "terminagotchi-pc"})
    if cle:
        req.add_header("authorization", "Bearer " + cle)
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except (ValueError, OSError):
            return {"erreur": t("rec.err.serveur", code=e.code)}
    except (OSError, ValueError) as e:
        return {"erreur": t("rec.err.connexion", detail=str(e)[:70])}


def serveur(state):
    """Adresse du site : réglée à la main, sinon publiée par le déploiement automatique."""
    c = compte(state)
    if c.get("serveur"):
        return c["serveur"].rstrip("/")
    try:
        with urllib.request.urlopen(INFO, timeout=8) as r:
            url = r.read().decode("utf-8").strip()
    except OSError:
        url = ""
    return url.rstrip("/") if url.startswith(("https://", "http://")) else ""


# ================================================================ fusion

def _instantane(state):
    return {"xp": state["xp"], "total": state["total"], "colles": state.get("colles", 0),
            "stats": dict(state["stats"])}


def _charge(state):
    c = compte(state)
    base = c.get("base") or {"xp": 0, "total": 0, "colles": 0, "stats": {}}
    snap = _instantane(state)
    deltas = {k: max(0, snap[k] - base.get(k, 0)) for k in COMPTEURS}
    deltas["stats"] = {s: max(0, v - base.get("stats", {}).get(s, 0)) for s, v in snap["stats"].items()}
    charge = {
        "appareil": APPAREIL, "partie": str(state.get("partie") or "1"), "deltas": deltas,
        "vus": list(state["seen"])[-3000:], "skills": list(state["skills"]),
        "collection": state.get("collection", {}), "records": state.get("records", {}),
        "captures": state.get("captures", [])[-3000:],
        "partage": c.get("partage", {"actif": False, "date": 0}),
        "valeurs": {"nom": state["name"], "nomDate": c.get("nomDate", 0), "trait": state.get("trait", ""),
                    "shiny": bool(state.get("shiny")),
                    "forme": state.get("branch"), "faim": state["hunger"],
                    "faimDate": int(state.get("repas_t", 0) * 1000),
                    "theme": state.get("config", {}).get("theme") or "sombre",
                    "themeDate": int(state.get("config", {}).get("theme_date") or 0)},
    }
    from . import entrainement
    charge["entrainement"], snap["ent"] = entrainement.charge(state, base.get("ent"))
    return charge, snap


def _appliquer(state, srv, snap):
    """Recopie la créature commune, en gardant ce qui a été gagné ici PENDANT la synchro."""
    c = compte(state)
    for k in COMPTEURS:
        state[k] = int(srv.get(k, 0)) + (state.get(k, 0) - snap[k])
    for s in state["stats"]:
        state["stats"][s] = int(srv.get("stats", {}).get(s, 0)) + (state["stats"][s] - snap["stats"].get(s, 0))
    c["base"] = {k: int(srv.get(k, 0)) for k in COMPTEURS}
    c["base"]["stats"] = {s: int(v) for s, v in srv.get("stats", {}).items()}
    for cmd in srv.get("vus", []):
        if cmd not in state["seen"]:
            state["seen"].append(cmd)
    for sk in srv.get("skills", []):
        if sk not in state["skills"]:
            state["skills"].append(sk)
    for esp, n in srv.get("collection", {}).items():
        if n > state["collection"].get(esp, 0):
            state["collection"][esp] = n
    for cmd, t in srv.get("records", {}).items():
        if cmd not in state["records"] or t < state["records"][cmd]:
            state["records"][cmd] = t
    if srv.get("nom"):
        state["name"] = srv["nom"]
        c["nomDate"] = srv.get("nomDate", 0)
    if srv.get("trait"):
        state["trait"] = srv["trait"]
    if srv.get("forme"):
        state["branch"] = srv["forme"]
    ici = {x.get("id"): x for x in state.setdefault("captures", [])}
    for ind in srv.get("captures", []):
        if ind.get("id") in ici:
            if "verifie" in ind:                    # anti-triche : le verdict du serveur
                ici[ind["id"]]["verifie"] = bool(ind["verifie"])
        else:
            state["captures"].append(ind)
            ici[ind.get("id")] = ind
    if "partage" in srv and srv["partage"].get("date", 0) >= c.get("partage", {}).get("date", 0):
        c["partage"] = srv["partage"]
    if "shiny" in srv:
        state["shiny"] = bool(srv["shiny"])
    if int(srv.get("themeDate") or 0) > int(state.get("config", {}).get("theme_date") or 0):   # le plus récent gagne
        from . import apparence
        if srv.get("theme") in apparence.donnees()["themes"]:
            state.setdefault("config", {})["theme"] = srv["theme"]
            state["config"]["theme_date"] = int(srv["themeDate"])
    if srv.get("faimDate", 0) > state.get("repas_t", 0) * 1000:
        state["hunger"] = float(srv.get("faim", state["hunger"]))
        state["repas_t"] = srv["faimDate"] / 1000
        state["last_tick"] = time.time()


def synchroniser(forcer=False):
    """Une synchro complète. Renvoie un message, ou None si rien à faire."""
    with core.verrou():
        st = core.load()
        if st is None:
            return t("rec.pas_de_creature")
        core.migrate(st)
        c = compte(st)
        if not c.get("cle"):
            return None if not forcer else t("rec.pas_de_compte")
        maintenant = time.time()
        if c.get("en_cours", 0) > maintenant - 30:
            return None
        if not forcer and maintenant - c.get("dernier", 0) < INTERVALLE:
            return None
        c["en_cours"] = maintenant
        c["dernier"] = maintenant
        charge, snap = _charge(st)
        core.save(st)
    url = serveur(st)
    # partie 1 (celle d'avant les parties multiples) : l'adresse d'origine ; les autres ont la leur,
    # qu'un site pas encore à jour refuse au lieu de mélanger deux créatures
    route = "/api/sync" if charge["partie"] == "1" else "/api/sync/" + charge["partie"]
    r = requete(url + route, "POST", charge, c["cle"]) if url else {"erreur": t("rec.err.adresse")}
    resultat = []

    def finir(s):
        cc = compte(s)
        cc["en_cours"] = 0
        if str(s.get("partie") or "1") != charge["partie"]:
            return                                 # on a changé de partie pendant la synchro
        if "etat" not in r:
            resultat.append(t("rec.sync.impossible", erreur=r.get("erreur", t("rec.err.inconnue"))))
            return
        if url and not cc.get("serveur"):
            cc["serveur"] = url
        avant = s["xp"]
        _appliquer(s, r["etat"], snap)
        from . import entrainement             # salle d'entraînement : compteurs, records vérifiés, Star de la semaine
        if isinstance(r["etat"].get("entrainement"), dict):     # (un site pas encore à jour n'en renvoie pas)
            compte(s)["base"]["ent"] = entrainement.appliquer(s, r["etat"].get("entrainement"), snap["ent"],
                                                              charge["entrainement"]["runs"], r.get("entrainement"))
        tirage.ranger_graines(s, r.get("graines"))   # graines des prochains jours (jeu hors ligne)
        gagne = s["xp"] - avant
        if gagne > 0:
            core.log(s, t("rec.sync.xp", n=gagne))
        for b in r.get("badges", []):
            core.log(s, t("rec.badge.log", titre=b["titre"]))
            core.notif(s, t("rec.badge.notif", titre=b["titre"]))
        resultat.append(t("rec.sync.ok", pseudo=cc.get("pseudo", "?")))

    core.modifier(finir)
    return resultat[0] if resultat else None


def synchroniser_en_fond():
    """Synchro automatique sans bloquer le jeu (au plus une à la fois)."""
    global _fil
    if _fil and _fil.is_alive():
        return
    _fil = threading.Thread(target=lambda: _sans_erreur(synchroniser), daemon=True)
    _fil.start()


def _sans_erreur(f):
    try:
        f()
    except Exception:
        pass


# ================================================================ commandes « compte »

def _enregistrer(pseudo, cle, url):
    def f(s):
        c = compte(s)
        base = c.get("base")
        meme = (c.get("base_de") or (c.get("pseudo") if base else "")) == pseudo and base
        c.update(cle=cle, pseudo=pseudo, serveur=url, base={"xp": 0, "total": 0, "colles": 0, "stats": {}},
                 dernier=0, en_cours=0, base_de=pseudo)
        if meme:
            c["base"] = base                       # cette partie connaît déjà ce compte : pas de double envoi
        core.log(s, t("rec.recense.log", pseudo=pseudo))
    core.modifier(f)


def commande(args):
    """tg compte [creer P | lier TG-XXXX-XX | secours TG-… | code | site | serveur URL | oublier]"""
    st = core.load()
    if st is None:
        return t("rec.pas_de_creature")
    core.migrate(st)
    c = compte(st)
    action = args[0].lower() if args else ""
    if action == "serveur":
        if len(args) < 2:
            return t("rec.adresse", url=serveur(st) or t("rec.inconnue"))
        core.modifier(lambda s: compte(s).update(serveur=args[1].rstrip("/")))
        return t("rec.adresse.reglee", url=args[1])
    url = serveur(st)
    if not url and action in ("creer", "lier", "secours", "code", "site", ""):
        return t("rec.hors_ligne")
    if action == "creer":
        if c.get("cle"):
            return t("rec.deja_compte", pseudo=c["pseudo"])
        if len(args) < 2:
            return t("rec.creer.exemple")
        r = requete(url + "/api/inscription", "POST", {"pseudo": args[1], "appareil": APPAREIL})
        if "cle" not in r:
            return "⚠ " + r.get("erreur", t("rec.err.inscription"))
        _enregistrer(r["pseudo"], r["cle"], url)
        msg = synchroniser(forcer=True) or ""
        secours = ("\n\n" + t("rec.secours.donne", code=r["secours"])) if r.get("secours") else ""
        return t("rec.bienvenue", pseudo=r["pseudo"], msg=msg, url=f"{url}/joueur/{r['pseudo']}") + secours
    if action in ("lier", "secours"):
        if len(args) < 2:
            return t("rec.lier.exemple" if action == "lier" else "rec.secours.exemple")
        route = "/api/lier" if action == "lier" else "/api/secours/recuperer"
        r = requete(url + route, "POST", {"code": args[1], "appareil": APPAREIL})
        if "cle" not in r:
            return "⚠ " + r.get("erreur", t("rec.err.liaison"))
        _enregistrer(r["pseudo"], r["cle"], url)
        msg = synchroniser(forcer=True) or ""
        return t("rec.relie", pseudo=r["pseudo"], msg=msg)
    if not c.get("cle"):
        return t("rec.sans_compte")
    if action == "code":
        r = requete(url + "/api/code", "POST", {}, c["cle"])
        if "code" not in r:
            return "⚠ " + r.get("erreur", t("rec.err.code"))
        return t("rec.code", code=r.get("jeton") or r["code"])
    if action == "site":
        r = requete(url + "/api/lien-site", "POST", {}, c["cle"])
        if not r.get("lien"):
            return "⚠ " + r.get("erreur", t("rec.err.code"))
        lien = url + r["lien"]
        try:
            import webbrowser
            webbrowser.open(lien)
        except Exception:
            pass
        return t("rec.lien_site", lien=lien)
    if action == "partage":
        choix = (args[1].lower() if len(args) > 1 else "")
        if choix not in ("on", "off"):
            etat = t("rec.active") if c.get("partage", {}).get("actif") else t("rec.desactive")
            return t("rec.partage.etat", etat=etat)
        actif = choix == "on"
        core.modifier(lambda s: compte(s).update(partage={"actif": actif, "date": int(time.time() * 1000)}))
        msg = synchroniser(forcer=True) or ""
        return (t("rec.partage.on", url=f"{url}/captures") if actif
                else t("rec.partage.off")) + ("\n" + msg if msg else "")
    if action in ("oublier", "deconnexion", "sortir"):
        requete(url + "/api/deconnexion", "POST", {}, c["cle"], delai=4)   # le site oublie la clé de ce PC (si en ligne)
        from . import parties
        parties.oublier_compte()              # dans toutes les parties ; le point de synchro de chacune reste
        return t("rec.oublie")
    dernier = c.get("dernier", 0)
    quand = time.strftime("%H:%M", time.localtime(dernier)) if dernier else t("rec.jamais")
    return t("rec.resume", pseudo=c["pseudo"], quand=quand, profil=f"{url}/joueur/{c['pseudo']}", ctf=f"{url}/ctf")


def site(args):
    """tg site [bestiaire|captures|classement] : ouvre le site du recensement."""
    st = core.load()
    c = compte(st) if st else {}
    url = serveur(st) if st else ""
    if not url:
        return t("rec.site.injoignable")
    page = (args[0].lower() if args else "")
    chemins = {"bestiaire": "/bestiaire", "captures": "/captures", "classement": "/classement", "ctf": "/ctf"}
    if page in chemins:
        lien = url + chemins[page]
    elif c.get("pseudo"):
        lien = f"{url}/joueur/{c['pseudo']}"
    else:
        lien = url
    try:
        import webbrowser
        ouvert = webbrowser.open(lien)
    except Exception:
        ouvert = False
    return f"🌍 {lien}" + ("  " + t("rec.site.ouvert") if ouvert else "")


def drapeau(proposition):
    st = core.load()
    if st is None:
        return t("rec.drapeau.pas_de_creature")
    core.migrate(st)
    c = compte(st)
    if not c.get("cle"):
        return t("rec.drapeau.compte")
    url = serveur(st)
    r = requete(url + "/api/drapeau", "POST", {"drapeau": proposition.strip()}, c["cle"])
    if r.get("ok"):
        def f(s):
            if r.get("nouveau"):
                s["stats"]["Intelligence"] += 3
                core.add_xp(s, 40)
                core.log(s, t("rec.drapeau.log", titre=r["titre"]))
        core.modifier(f)
        lignes = [t("rec.drapeau.ok", titre=r["titre"], score=r["score"], sur=r["sur"])
                  + ("" if r.get("nouveau") else t("rec.drapeau.deja")),
                  f"📐 {r['lecon']}"]
        if r.get("badge"):
            lignes.append(t("rec.badge.log", titre=f"{url}{r['badge']}"))
        if r.get("badgeFinal"):
            lignes.append(t("rec.drapeau.final", url=f"{url}{r['badgeFinal']}"))
        return "\n".join(lignes)
    return "❌ " + r.get("message", r.get("erreur", t("rec.drapeau.refuse")))
