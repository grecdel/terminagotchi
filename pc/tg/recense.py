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
            return {"erreur": f"le serveur répond {e.code}"}
    except (OSError, ValueError) as e:
        return {"erreur": f"pas de connexion au recensement ({str(e)[:70]})"}


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
        "appareil": APPAREIL, "deltas": deltas,
        "vus": list(state["seen"])[-3000:], "skills": list(state["skills"]),
        "collection": state.get("collection", {}), "records": state.get("records", {}),
        "captures": state.get("captures", [])[-3000:],
        "partage": c.get("partage", {"actif": False, "date": 0}),
        "valeurs": {"nom": state["name"], "nomDate": c.get("nomDate", 0), "trait": state.get("trait", ""),
                    "shiny": bool(state.get("shiny")),
                    "forme": state.get("branch"), "faim": state["hunger"],
                    "faimDate": int(state.get("repas_t", 0) * 1000)},
    }
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
    connus = {x.get("id") for x in state.setdefault("captures", [])}
    for ind in srv.get("captures", []):
        if ind.get("id") not in connus:
            state["captures"].append(ind)
    if "partage" in srv and srv["partage"].get("date", 0) >= c.get("partage", {}).get("date", 0):
        c["partage"] = srv["partage"]
    if "shiny" in srv:
        state["shiny"] = bool(srv["shiny"])
    if srv.get("faimDate", 0) > state.get("repas_t", 0) * 1000:
        state["hunger"] = float(srv.get("faim", state["hunger"]))
        state["repas_t"] = srv["faimDate"] / 1000
        state["last_tick"] = time.time()


def synchroniser(forcer=False):
    """Une synchro complète. Renvoie un message, ou None si rien à faire."""
    with core.verrou():
        st = core.load()
        if st is None:
            return "Pas encore de créature : lance d'abord le jeu."
        core.migrate(st)
        c = compte(st)
        if not c.get("cle"):
            return None if not forcer else "Pas de compte : tape  compte creer TonPseudo"
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
    r = requete(url + "/api/sync", "POST", charge, c["cle"]) if url else {"erreur": "adresse du site inconnue"}
    resultat = []

    def finir(s):
        cc = compte(s)
        cc["en_cours"] = 0
        if "etat" not in r:
            resultat.append("⚠ Synchro impossible : " + r.get("erreur", "erreur inconnue"))
            return
        if url and not cc.get("serveur"):
            cc["serveur"] = url
        avant = s["xp"]
        _appliquer(s, r["etat"], snap)
        gagne = s["xp"] - avant
        if gagne > 0:
            core.log(s, f"🔄 Synchro : +{gagne} XP venus de ton autre appareil")
        for b in r.get("badges", []):
            core.log(s, f"🏅 Badge vérifié : {b['titre']}")
            core.notif(s, f"🏅 Nouveau badge : {b['titre']}")
        resultat.append(f"✔ Synchronisé avec le recensement ({cc.get('pseudo', '?')})")

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
        c.update(cle=cle, pseudo=pseudo, serveur=url, base={"xp": 0, "total": 0, "colles": 0, "stats": {}},
                 dernier=0, en_cours=0)
        core.log(s, f"🌍 Recensé sous le pseudo {pseudo} !")
    core.modifier(f)


def commande(args):
    """tg compte [creer P | lier CODE | code | serveur URL | oublier]"""
    st = core.load()
    if st is None:
        return "Pas encore de créature : lance d'abord le jeu."
    core.migrate(st)
    c = compte(st)
    action = args[0].lower() if args else ""
    if action == "serveur":
        if len(args) < 2:
            return f"Adresse actuelle : {serveur(st) or '(inconnue)'}"
        core.modifier(lambda s: compte(s).update(serveur=args[1].rstrip("/")))
        return f"Adresse du recensement réglée sur {args[1]}"
    url = serveur(st)
    if not url and action in ("creer", "lier", "code", ""):
        return ("Le site du recensement n'est pas encore en ligne (ou pas de connexion).\n"
                "Réessaie plus tard, ou règle l'adresse : compte serveur https://…")
    if action == "creer":
        if c.get("cle"):
            return f"Tu as déjà un compte : {c['pseudo']}. (compte oublier pour en changer)"
        if len(args) < 2:
            return "Exemple : compte creer TonPseudo  (3 à 20 lettres sans accent, chiffres, - ou _)"
        r = requete(url + "/api/inscription", "POST", {"pseudo": args[1], "appareil": APPAREIL})
        if "cle" not in r:
            return "⚠ " + r.get("erreur", "inscription impossible")
        _enregistrer(r["pseudo"], r["cle"], url)
        msg = synchroniser(forcer=True) or ""
        return (f"🌍 Bienvenue au recensement, {r['pseudo']} !\n{msg}\n"
                f"Ton profil public : {url}/joueur/{r['pseudo']}\n"
                f"Pour avoir la même créature sur ton téléphone : compte code")
    if action == "lier":
        if len(args) < 2:
            return "Exemple : compte lier AB3K9Z  (le code s'obtient sur l'autre appareil avec : compte code)"
        r = requete(url + "/api/lier", "POST", {"code": args[1], "appareil": APPAREIL})
        if "cle" not in r:
            return "⚠ " + r.get("erreur", "liaison impossible")
        _enregistrer(r["pseudo"], r["cle"], url)
        msg = synchroniser(forcer=True) or ""
        return (f"🔗 Ce PC est relié au compte {r['pseudo']} !\n{msg}\n"
                "Ta progression d'ici s'ajoute à celle de ton autre appareil.")
    if not c.get("cle"):
        return ("Tu n'as pas encore de compte.\n"
                "  compte creer TonPseudo   → créer ton compte\n"
                "  compte lier CODE         → rejoindre le compte de ton téléphone")
    if action == "code":
        r = requete(url + "/api/code", "POST", {}, c["cle"])
        if "code" not in r:
            return "⚠ " + r.get("erreur", "impossible d'obtenir un code")
        return (f"🔑 Code de liaison : {r['code']}  (valable 10 minutes)\n"
                f"Sur ton téléphone, dans le terminal de l'appli : compte lier {r['code']}")
    if action == "partage":
        choix = (args[1].lower() if len(args) > 1 else "")
        if choix not in ("on", "off"):
            etat = "activé" if c.get("partage", {}).get("actif") else "désactivé"
            return (f"Partage de tes captures dans la galerie publique : {etat}.\n"
                    "  compte partage on   → tes bestioles apparaissent sur le site (avec ton pseudo)\n"
                    "  compte partage off  → elles restent privées")
        actif = choix == "on"
        core.modifier(lambda s: compte(s).update(partage={"actif": actif, "date": int(time.time() * 1000)}))
        msg = synchroniser(forcer=True) or ""
        return ("✔ Tes captures seront visibles dans la galerie : " + f"{url}/captures" if actif
                else "✔ Tes captures ne sont plus visibles dans la galerie.") + ("\n" + msg if msg else "")
    if action == "oublier":
        core.modifier(lambda s: s.__setitem__("compte", {k: v for k, v in compte(s).items() if k == "serveur"}))
        return "Ce PC n'est plus relié au compte (le compte, lui, existe toujours)."
    dernier = c.get("dernier", 0)
    quand = time.strftime("%H:%M", time.localtime(dernier)) if dernier else "jamais"
    return (f"🌍 Compte : {c['pseudo']} · dernière synchro : {quand}\n"
            f"Profil public : {url}/joueur/{c['pseudo']}\n"
            f"Chasse au trésor du site (CTF web, badges vérifiés) : {url}/ctf\n"
            "  compte code   → relier un autre appareil\n  sync          → synchroniser maintenant")


def site(args):
    """tg site [bestiaire|captures|classement] : ouvre le site du recensement."""
    st = core.load()
    c = compte(st) if st else {}
    url = serveur(st) if st else ""
    if not url:
        return "Le site du recensement n'est pas joignable pour l'instant."
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
    return f"🌍 {lien}" + ("  (ouvert dans ton navigateur)" if ouvert else "")


def drapeau(proposition):
    st = core.load()
    if st is None:
        return "Pas encore de créature."
    core.migrate(st)
    c = compte(st)
    if not c.get("cle"):
        return "Il faut un compte pour valider un drapeau de la chasse au trésor du site : compte creer TonPseudo"
    url = serveur(st)
    r = requete(url + "/api/drapeau", "POST", {"drapeau": proposition.strip()}, c["cle"])
    if r.get("ok"):
        def f(s):
            if r.get("nouveau"):
                s["stats"]["Intelligence"] += 3
                core.add_xp(s, 40)
                core.log(s, f"🚩 Drapeau web validé : {r['titre']} !")
        core.modifier(f)
        lignes = [f"🚩 Drapeau validé : {r['titre']} ({r['score']}/{r['sur']})" + ("" if r.get("nouveau") else " — déjà validé"),
                  f"📐 {r['lecon']}"]
        if r.get("badge"):
            lignes.append(f"🏅 Badge vérifié : {url}{r['badge']}")
        if r.get("badgeFinal"):
            lignes.append(f"🏆 TOUS LES DRAPEAUX ! Badge final : {url}{r['badgeFinal']}")
        return "\n".join(lignes)
    return "❌ " + r.get("message", r.get("erreur", "drapeau refusé"))
