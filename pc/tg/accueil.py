"""Le menu des parties, en texte (même rendu que MenuParties.kt sur Android) :

  ┌ Terminagotchi ┐
  1  continuer    Pixel · Bébé niv. 4
  2  nouvelle partie
  3  charger
  4  compte       (non connecté)

Affiché seulement au lancement interactif de `tg` et par `tg parties` (jamais par le mode « prompt »
du shell, `tg --une-fois` ni les sous-commandes). Tout marche hors ligne : les parties du compte
viennent d'un cache local, rafraîchi en fond avec un délai court.

On répond par le chiffre ou par le mot, en français (toujours) ou dans la langue choisie :
clés part.mots.continuer / nouvelle / charger / compte / quitter des fichiers de langue. Le « oui »
d'une confirmation se dit dans n'importe laquelle des 14 langues (clé part.oui : oui, yes, sí, ja,
да, はい, 是, हाँ, نعم, হ্যাঁ, ya, ہاں…). Même règle sur Android (MenuParties.kt).
"""
import json
import sys
import threading
import unicodedata
import urllib.request

from . import core, langue, parties, recense, sprites
from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

def _norm(texte):
    return unicodedata.normalize("NFC", (texte or "").strip().lower())


def mots(cle):
    """Les mots acceptés pour une action du menu : ceux de la langue choisie, et toujours ceux du français."""
    out = set()
    for code in {langue.courante(), langue.DEFAUT}:
        v = langue._charger(code).get(cle) or []
        out |= {_norm(x) for x in (v if isinstance(v, list) else [v])}
    return out


def oui(reponse):
    """Vrai si la réponse est « oui » dans l'une des 14 langues (le reste compte comme non)."""
    r = _norm(reponse)
    if not r:
        return False
    for code in langue.LANGUES:
        v = langue._charger(code).get("part.oui") or []
        if r in {_norm(x) for x in v}:
            return True
    return False


def action(reponse):
    """L'action du menu désignée par une réponse (chiffre ou mot) : continuer, nouvelle, charger, compte,
    quitter, ou None."""
    r = _norm(reponse)
    if r in ("", "1") or r in mots("part.mots.continuer"):
        return "continuer"
    if r in ("q", "0") or r in mots("part.mots.quitter"):
        return "quitter"
    if r == "2" or r in mots("part.mots.nouvelle"):
        return "nouvelle"
    if r == "3" or r in mots("part.mots.charger"):
        return "charger"
    if r == "4" or r in mots("part.mots.compte"):
        return "compte"
    return None

_rafraichi = {"ok": None}         # None : pas encore de réponse · True / False : en ligne / hors ligne


def _qui(st):
    if not st or not st.get("name"):
        return t("part.oeuf_sans_nom")
    n = core.level(st["xp"])
    return t("part.qui", nom=st["name"] + (" ✨" if st.get("shiny") else ""), espece=core.forme(st, n), n=n)


def _etat():
    st = core.load()
    if st:
        core.migrate(st)
    return st


def ecran_menu(st):
    c = (st or {}).get("compte", {})
    compte = c.get("pseudo") if c.get("cle") else t("part.non_connecte")
    return "\n".join([
        f"{fg(213)}┌ Terminagotchi ┐{RESET}",
        f"{BOLD}1{RESET}  " + t("part.m.continuer") + "    " + _qui(st),
        f"{BOLD}2{RESET}  " + t("part.m.nouvelle"),
        f"{BOLD}3{RESET}  " + t("part.m.charger"),
        f"{BOLD}4{RESET}  " + t("part.m.compte") + "       " + compte,
        f"{DIM}" + t("part.m.aide") + RESET,
    ])


# ---------------------------------------------------------------- compte en ligne (en fond, jamais bloquant)
def _rafraichir_compte(st):
    """En fond, 4 s au plus : la liste des parties du compte, gardée en cache (pour le hors-ligne)."""
    c = (st or {}).get("compte", {})
    if not c.get("cle") or not c.get("serveur"):
        return

    def f():
        try:
            req = urllib.request.Request(c["serveur"].rstrip("/") + "/api/parties",
                                         headers={"authorization": "Bearer " + c["cle"], "user-agent": "terminagotchi-pc"})
            with urllib.request.urlopen(req, timeout=4) as r:
                a = json.loads(r.read().decode("utf-8")).get("parties")
            if not isinstance(a, list):
                raise ValueError
            cle = c["cle"]
            core.modifier(lambda s: s.setdefault("compte", {}).__setitem__("parties_cache", a)
                          if s.get("compte", {}).get("cle") == cle else None)
            _rafraichi["ok"] = True
        except Exception:
            _rafraichi["ok"] = False
    threading.Thread(target=f, daemon=True).start()


# ---------------------------------------------------------------- écrans
def lignes_parties(st):
    """[(id, nom si elle vient du compte, sinon None)], texte affiché."""
    choix, lignes = [], [f"{fg(213)}┌ " + t("part.l.titre") + f" ┐{RESET}"]
    for p in parties.liste():
        choix.append((p["id"], None))
        lignes.append(f"{BOLD}{len(choix)}{RESET}  " + t("part.l.ligne", nom=p["nom"] or t("part.oeuf_sans_nom"),
                                                          espece=p["espece"], n=p["niveau"], date=parties.date_courte(p["date"]))
                      + (f"  {fg(78)}" + t("part.l.en_cours") + RESET if p["active"] else ""))
    c = (st or {}).get("compte", {})
    if c.get("cle"):
        ici = {i for i, _ in choix}
        autres = [p for p in c.get("parties_cache", []) if isinstance(p, dict) and str(p.get("partie")) not in ici]
        hors = f" {DIM}" + t("part.hors_ligne") + RESET if _rafraichi["ok"] is False else ""
        lignes.append(f"{fg(111)}☁ " + t("part.l.compte", pseudo=c.get("pseudo", "?")) + RESET + hors)
        for p in autres:
            n = int(p.get("niveau") or 1)
            choix.append((str(p["partie"]), p.get("nom") or "?"))
            lignes.append(f"{BOLD}{len(choix)}{RESET}  " + t("part.l.ligne", nom=p.get("nom") or "?",
                                                              espece=core.forme({"xp": 10 * (n - 1) ** 2, "branch": p.get("forme")}, n),
                                                              n=n, date=""))
        if not autres and _rafraichi["ok"] is not False:
            lignes.append(f"   {DIM}" + t("part.l.compte_vide") + RESET)
    return choix, "\n".join(lignes)


def _message_oeuf(s):
    return t("app.oeuf_apparu", trait=core.nom_trait(s["trait"]))


def nouvelle(demander, confirmer=True, avec_intro=None):
    """Demande confirmation puis le nom ; l'ancienne partie est rangée. Renvoie le message.
    avec_intro (par défaut : une vraie personne au clavier) : les écrans de l'intro, puis l'œuf et sa liste."""
    st = _etat()
    if parties.pleine():
        return t("part.plein", n=parties.MAX)
    if st and st.get("name") and confirmer:
        print(t("part.n.confirmer", nom=st["name"]))
        if not oui(demander("  " + t("part.oui_non") + " ")):
            return t("part.n.rien")
    if avec_intro is None:
        avec_intro = sys.stdin.isatty() and sys.stdout.isatty()
    from . import intro
    from .plateforme import clear
    nom = intro.jouer_ecrans(demander, clear) if avec_intro else None
    nom = (nom or demander(t("app.nom_creature") + " ")).strip()[:16] or "Pixel"
    i = parties.nouvelle(nom, langue.courante(), _message_oeuf, intro=avec_intro)
    if not i:
        return t("part.n.echec")
    return t("part.n.ok", nom=nom)


def charger(n, choix):
    if not (1 <= n <= len(choix)):
        return t("part.l.pas_de_numero", n=n)
    i, du_compte = choix[n - 1]
    st = _etat()
    if st and parties.id_de(st) == i:
        return t("part.continuer", nom=st.get("name", ""))
    ok = parties.depuis_compte(i, du_compte, langue.courante()) if du_compte else parties.charger(i)
    if not ok:
        return t("part.plein", n=parties.MAX) if parties.pleine() else t("part.l.echec")
    st = _etat()
    langue.appliquer(st)
    if st.get("compte", {}).get("cle"):
        recense.synchroniser_en_fond()           # en fond : jamais d'attente, rien ne casse hors ligne
    if du_compte:
        return t("part.l.depuis_compte", nom=du_compte)
    return t("part.l.ok", qui=_qui(st))


def texte_compte(st):
    """L'état du compte, sans réseau."""
    c = (st or {}).get("compte", {})
    if not c.get("cle"):
        return t("rec.sans_compte")
    url = c.get("serveur", "")
    d = c.get("dernier", 0)
    import time
    quand = time.strftime("%H:%M", time.localtime(d)) if d else t("rec.jamais")
    return t("rec.resume", pseudo=c.get("pseudo", "?"), quand=quand, profil=f"{url}/joueur/{c.get('pseudo', '')}", ctf=f"{url}/ctf")


def commande(args, demander=input):
    """tg partie [nouvelle | charger [n]]"""
    action = args[0].lower() if args else "charger"
    if action == "nouvelle":
        return nouvelle(demander)
    if action in ("charger", "liste"):
        st = _etat()
        if len(args) < 2:
            _rafraichir_compte(st)
        choix, texte = lignes_parties(st)
        if len(args) > 1 and args[1].isdigit():
            return charger(int(args[1]), choix)
        return texte + f"\n{DIM}" + t("part.l.astuce") + RESET
    return t("part.aide")


def menu(demander=input):
    """Le menu du lancement. Renvoie False si le joueur veut quitter."""
    _rafraichir_compte(_etat())
    msg = ""
    while True:
        st = _etat()
        if msg:
            print(msg + "\n")
        print(ecran_menu(st))
        try:
            r = demander(f"{BOLD}> {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return False
        rl = r.lower()
        msg = ""
        quoi = action(r)
        if quoi == "continuer":
            if st and st.get("name"):
                print("\n".join(sprites.creature(st)[0]))
            return True
        if quoi == "quitter":
            return False
        try:
            if quoi == "nouvelle":
                msg = nouvelle(demander)
            elif quoi == "charger":
                choix, texte = lignes_parties(st)
                print(texte)
                n = demander(t("part.l.numero") + " ").strip()
                msg = charger(int(n), choix) if n.isdigit() else ""
            elif quoi == "compte":
                msg = texte_compte(st)
            elif rl.split()[0] in ("compte", "partie"):
                mots = r.split()[1:]
                msg = recense.commande(mots) if rl.startswith("compte") else commande(mots, demander)
            else:
                msg = t("part.m.inconnu")
        except (KeyboardInterrupt, EOFError):
            print()
            msg = ""
