"""Les quêtes secondaires : la maison est grande, il s'y passe plein de choses (façon « monde ouvert »).

Quatre sortes de quêtes écrites à la main (44, voir QUETES), posées dans les pièces quand leur porte
s'ouvre :
  lettre    une lettre à lire (cat lettre_du_jardinier.txt) : la lire accepte la mini-quête ;
  habitant  un monstre habitant demande un service (cat habitant_mousseline.txt) ;
  cachette  une pièce secrète (dossier qui commence par un point) : on la trouve avec ls -a, y entrer
            (cd .nid_de_hibou) suffit ;
  sauvage   regarder les terres sauvages hors de la maison (cat /etc/hostname), en lecture seule.
Plus les quêtes GÉNÉRÉES à partir de modèles (perdu, construire, copie, compter, protéger, mot secret) :
le tableau des annonces du vestibule en propose toujours 3, tirées d'une graine propre à la partie ;
et une QUÊTE DU JOUR (même graine + la date), qui change chaque jour.
La difficulté des quêtes générées suit le niveau de la créature.

Règle d'or : une quête ne demande JAMAIS d'écrire ou de supprimer hors de ~/terrain_terminagotchi.
Le jeu n'écrit lui-même que dans le terrain.

Sauvegarde : state["quetes"] = {actives, finies, suivie, vu, gen, gen_n, offertes, jour, objets,
titres, titre, poses, souvenirs}.
Récompenses : XP, objets (décorations rangées dans nid/decorations/), titres, souvenirs du carnet.
"""
import datetime
import getpass
import os
import random
import re

from . import core, maison
from .langue import t
from .mots import palier, termes
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg

T = lambda: core.TERRAIN  # noqa: E731
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail|bat|nl)\b"


def _q(id_, piece, sorte, fichier, but, xp=15, objet=None, titre=None, pose=None, win=True):
    return {"id": id_, "piece": piece, "sorte": sorte, "fichier": fichier, "but": but, "xp": xp,
            "objet": objet, "titre": titre, "pose": pose, "win": win}


MOTS_MAGIQUES = ("BLOUP", "ZORGLUB", "PLOUF", "SPLASH", "GLOUBI", "SCHLOUK")
TUYAUX = ("rouge", "bleu", "vert")


def _rnd(state, sel):
    return random.Random(f"{state.get('partie') or '1'}:{int(state.get('born', 0))}:{sel}")


def _compte(rel, motif):
    d = T() / rel
    try:
        return sum(1 for p in d.iterdir() if p.is_file() and re.fullmatch(motif, p.name))
    except OSError:
        return 0


def _lignes(rel, mots=False):
    x = _lire(rel)
    if x is None:
        return -1
    return len(x.split()) if mots else sum(1 for l in x.split("\n") if l.strip())


def _lire(rel):
    try:
        brut = (T() / rel).read_bytes()
    except OSError:
        return None
    if brut[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return brut.decode("utf-16", errors="replace")
    return brut.decode("utf-8", errors="replace")


# ---------------------------------------------------------------- ce que posent certaines quêtes
def _pose_journal(state):
    return {"nid/journal_intime.txt": t("qu.q10.page")}


def _pose_chaussettes(state):
    return {"grenier/panier/.vide": "", "grenier/fouillis/malle/chaussette_rouge.txt": "🧦",
            "grenier/fouillis/carton/chaussette_verte.txt": "🧦", "grenier/vieux_coffre/.fond/chaussette_bleue.txt": "🧦"}


def _pose_feuilles(state):
    n = _rnd(state, "feuilles").randint(5, 9)
    return {f"grenier/lianes/feuille_{i + 1}.txt": "🍃" for i in range(n)}


def _pose_photos(state):
    m = {"grenier/album/.vide": ""}
    for x in ("plage", "foret", "gateau", "chat"):
        m[f"grenier/fouillis/photo_{x}.txt"] = "📷 " + x
    return m


def _pose_gateau(state):
    return {"cave/tonneau/.fond/gateau.txt": "🍰"}


def _pose_inventaire(state):
    r = _rnd(state, "inventaire")
    choses = list(t("qu.q18.choses").split(", ")) if t("qu.q18.choses") else ["?"]
    r.shuffle(choses)
    return {"cave/inventaire.txt": "\n".join(choses[:r.randint(6, min(12, len(choses)))])}


def _pose_glouglou(state):
    mot = _rnd(state, "mot").choice(MOTS_MAGIQUES)
    return {"bibliotheque/etagere_b/journal_de_bord.txt": t("qu.q20.journal") + f"\nMOT MAGIQUE : {mot}\n"
            + t("qu.q20.journal_fin")}


def _pose_titres(state):
    titres = t("qu.q21.titres").split(", ")
    _rnd(state, "titres").shuffle(titres)
    return {"bibliotheque/titres.txt": "\n".join(titres)}


def _pose_grand_livre(state):
    return {"bibliotheque/grand_livre.txt": "\n".join(t("qu.q23.page", n=i + 1) for i in range(40))}


def _pose_tuyaux(state):
    gros = _rnd(state, "tuyau").choice(TUYAUX)
    m = {}
    for x in TUYAUX:
        m[f"salle_des_machines/tuyaux/{x}/bouchon.bin"] = b"\0" * (90000 if x == gros else 6000)
    return m


def _pose_conte(state):
    return {"dortoir/conte_du_soir.txt": "\n\n".join(t("qu.q32.conte", n=i + 1) for i in range(30))}


def _pose_machine(state):
    return {"atelier/machine.sh": 'echo "Vrrr… clic !"'}


# ---------------------------------------------------------------- les 44 quêtes écrites à la main
QUETES = [
    # le vestibule
    _q("q01", "vestibule", "lettre", "lettre_de_bienvenue.txt", [("visite", "vestibule/.placard_secret")], 15, "paillasson"),
    _q("q02", "vestibule", "cachette", ".placard_secret", [], 10, titre="fouineur"),
    _q("q03", "vestibule", "lettre", "mot_du_facteur.txt", [("dossier", "vestibule/boite_aux_lettres")], 15, "timbre"),
    _q("q04", "vestibule", "habitant", "habitant_pantoufle.txt", [("fichier", "vestibule/tapis.txt")], 15, "tapis"),
    _q("q05", "vestibule", "lettre", "horloge_du_hall.txt", [("plein", "vestibule/heure.txt")], 15, "horloge"),
    # le nid
    _q("q06", "nid", "lettre", "liste_de_courses.txt", [("lignes", "nid/courses.txt", 3)], 20, "panier"),
    _q("q07", "nid", "habitant", "habitant_grignote.txt", [("fichier", "nid/coussin.txt")], 15, "bougie"),
    _q("q08", "nid", "cachette", ".sous_le_lit", [], 10, "doudou"),
    _q("q09", "nid", "lettre", "recette_de_mamie.txt", [("fichier", "nid/recette_copie.txt")], 15, "tablier"),
    _q("q10", "nid", "lettre", "page_du_journal.txt", [("lignes", "nid/journal_intime.txt", 3)], 15, titre="ecrivain",
       pose=_pose_journal),
    # le grenier des Sylvestres
    _q("q11", "grenier", "habitant", "habitant_mousseline.txt", [("nb", "grenier/panier", r"chaussette_.*", 3)], 30,
       "pelote", pose=_pose_chaussettes),
    _q("q12", "grenier", "cachette", ".nid_de_hibou", [], 10, "plume"),
    _q("q13", "grenier", "lettre", "lettre_du_jardinier.txt",
       [("reponse", "grenier/reponse_jardinier.txt", lambda s: _compte("grenier/lianes", r"feuille_.*"))], 25, "arrosoir",
       pose=_pose_feuilles),
    _q("q14", "grenier", "habitant", "habitant_ronce.txt", [("nb", "grenier/album", r"photo_.*", 4)], 25, "cadre_photo",
       pose=_pose_photos),
    # la cave des Démons
    _q("q15", "cave", "lettre", "avis_de_vol.txt", [("fichier", "nid/gateau.txt")], 25, "gateau", pose=_pose_gateau),
    _q("q16", "cave", "habitant", "habitant_braise.txt", [("protege", "cave/coffre.txt")], 25, "bougie_rouge"),
    _q("q17", "cave", "cachette", ".trappe", [], 10, "cristal"),
    _q("q18", "cave", "lettre", "inventaire_a_verifier.txt",
       [("reponse", "cave/reponse_inventaire.txt", lambda s: _lignes("cave/inventaire.txt"))], 25, "sablier",
       pose=_pose_inventaire),
    _q("q19", "cave", "sauvage", "plan_des_fondations.txt", [("cmd", r"^(ls|dir|gci|get-childitem)\s+([a-z]:)?[\\/]\s*$")],
       20, titre="explorateur"),
    # la bibliothèque des Abyssaux
    _q("q20", "bibliotheque", "habitant", "habitant_glouglou.txt",
       [("contient", "bibliotheque/mot_magique.txt", lambda s: _rnd(s, "mot").choice(MOTS_MAGIQUES))], 25, "coquillage",
       pose=_pose_glouglou),
    _q("q21", "bibliotheque", "lettre", "fiche_de_pret.txt", [("trie", "bibliotheque/titres_ranges.txt", "bibliotheque/titres.txt")],
       25, "lampe_de_lecture", pose=_pose_titres),
    _q("q22", "bibliotheque", "cachette", ".salle_des_archives", [], 10, "parchemin"),
    _q("q23", "bibliotheque", "lettre", "livre_ouvert.txt", [("cmd", r"^(head|get-content|gc)\b.*grand_livre")], 15, "loupe",
       pose=_pose_grand_livre),
    # la salle des machines des Élémentaires
    _q("q24", "salle_des_machines", "habitant", "habitant_etincelle.txt",
       [("cmd_ici", r"^(df|get-psdrive|gdr)\b", "salle_des_machines")], 15, "ampoule"),
    _q("q25", "salle_des_machines", "lettre", "note_du_chauffagiste.txt",
       [("contient", "salle_des_machines/reponse_tuyau.txt", lambda s: _rnd(s, "tuyau").choice(TUYAUX))], 25,
       "cle_a_molette", pose=_pose_tuyaux),
    _q("q26", "salle_des_machines", "cachette", ".chaufferie", [], 10, "lanterne"),
    _q("q27", "salle_des_machines", "habitant", "habitant_givre.txt", [("fichier", "salle_des_machines/frigo/glacon.txt")],
       15, "boule_a_neige"),
    _q("q28", "salle_des_machines", "sauvage", "plaque_du_constructeur.txt",
       [("cmd", r"^(cat|less|more|head|type)\s+/etc/os-release" if not IS_WIN else r"^(systeminfo|get-computerinfo)\b")],
       20, titre="explorateur"),
    # le dortoir des Morts-vivants
    _q("q29", "dortoir", "habitant", "habitant_berceuse.txt",
       [("cmd", r"^(ps|get-process|gps|tasklist)\b.*\|\s*(wc|measure-object|measure)")], 20, "attrape_reves"),
    _q("q30", "dortoir", "lettre", "journal_du_veilleur.txt",
       [("contient", "dortoir/veilleur.txt", lambda s: getpass.getuser())], 20, "bonnet_de_nuit"),
    _q("q31", "dortoir", "cachette", ".sous_les_draps", [], 10, "etoile_filante"),
    _q("q32", "dortoir", "lettre", "histoire_du_soir.txt", [("cmd", r"^(less|more)\b.*conte")], 15, "livre_de_contes",
       pose=_pose_conte),
    _q("q33", "dortoir", "lettre", "reveil_matin.txt", [("cmd", r"^(uptime|get-uptime)\b")], 15, "reveil"),
    # l'atelier des Constructs
    _q("q34", "atelier", "habitant", "habitant_boulon.txt",
       [("fichier", "atelier/bonjour.sh" if not IS_WIN else "atelier/bonjour.ps1"),
        ("cmd", r"^(sh|bash|zsh|\./|powershell|pwsh|\.\\).*bonjour")], 30, "tournevis"),
    _q("q35", "atelier", "lettre", "plan_secret.txt", [("exec", "atelier/machine.sh")], 20, "engrenage", pose=_pose_machine,
       win=False),
    _q("q36", "atelier", "cachette", ".etabli_cache", [], 10, "boulon_d_or"),
    _q("q37", "atelier", "lettre", "carnet_de_bord.txt", [("commits", 2)], 30, "appareil_photo"),
    # la tour des Célestes
    _q("q38", "tour", "habitant", "habitant_nuage.txt", [("cmd", r"^ping\b.*(127\.0\.0\.1|localhost)")], 20, "cerf_volant"),
    _q("q39", "tour", "sauvage", "carte_des_terres_sauvages.txt",
       [("cmd", r"^(cat|less|more|head|type|gc|get-content)\s+/etc/hostname" if not IS_WIN else r"^hostname\b")], 20,
       titre="explorateur"),
    _q("q40", "tour", "cachette", ".observatoire", [], 10, "longue_vue"),
    _q("q41", "tour", "lettre", "telegramme.txt", [("ip", "tour/adresse.txt")], 25, "boussole"),
    # le cœur de la maison
    _q("q42", "coeur", "habitant", "habitant_bizarre.txt", [("contient", "coeur/envers.txt", "ihctoganimret")], 25, "miroir"),
    _q("q43", "coeur", "cachette", ".chambre_des_echos", [], 10, "coquille"),
    _q("q44", "coeur", "lettre", "dernier_message.txt",
       [("reponse", "coeur/reponse_mots.txt", lambda s: _lignes("coeur/message_brouille.txt", mots=True))], 25,
       titre="detective"),
]
PAR_ID = {q["id"]: q for q in QUETES}

# ---------------------------------------------------------------- les quêtes générées
OBJETS_PERDUS = ("bille", "toupie", "crayon", "gomme", "sifflet", "ballon", "bouton", "petite_cle")
COINS = ("sous_le_tapis", "derriere_le_rideau", "dans_un_tiroir", "sous_une_planche")
CONSTRUCTIONS = ("cabane", "tipi", "chateau_fort", "igloo", "grotte", "tente")
MODELES_FACILES = ("perdu", "construire", "copie")
MODELES_MOYENS = ("compter", "proteger")
MODELES_DURS = ("mot",)
NB_ANNONCES = 3


def modeles(niveau):
    """La difficulté suit le niveau : de plus en plus de sortes de quêtes, et plus cachées."""
    m = list(MODELES_FACILES)
    if niveau >= 7:
        m += MODELES_MOYENS
    if niveau >= 12:
        m += MODELES_DURS
    if IS_WIN and "proteger" in m:
        m.remove("proteger")
    return m


def _pieces_libres(state):
    from . import histoire
    return [p for p in maison.PIECES if p != "nid" and histoire.piece_ouverte(state, p) and (T() / p).is_dir()]


def generer(state, sel, niveau):
    """Une quête tirée d'un modèle : {"m": modèle, "p": paramètres, "pose": {fichier: contenu}}."""
    r = random.Random(f"{state.get('partie') or '1'}:{int(state.get('born', 0))}:gen:{sel}")
    pieces = _pieces_libres(state) or ["vestibule"]
    m = r.choice(modeles(niveau))
    piece = r.choice(pieces)
    k = re.sub(r"\W", "", str(sel))[-6:]
    p = {"piece": piece}
    pose = {}
    if m == "perdu":
        obj = r.choice(OBJETS_PERDUS)
        coin = r.choice(COINS)
        if niveau >= 10:
            coin = "." + coin                                  # plus dur : un coin caché (ls -a, find)
        p.update(objet=obj, fichier=f"{obj}.txt")
        pose[f"{piece}/{coin}/{obj}.txt"] = "✨ " + obj
    elif m == "construire":
        p.update(nom=r.choice(CONSTRUCTIONS) + "_" + k[-2:])
    elif m == "copie":
        obj = r.choice(OBJETS_PERDUS)
        p.update(fichier=f"recette_{obj}.txt")
        pose[f"{piece}/recette_{obj}.txt"] = "1. …\n2. …\n3. ✨"
    elif m == "compter":
        n = r.randint(4, 9 if niveau < 10 else 15)
        p.update(tas=f"tas_{k}", reponse=f"reponse_{k}.txt")
        for i in range(n):
            pose[f"{piece}/tas_{k}/caillou_{i + 1}.txt"] = "🪨"
    elif m == "proteger":
        p.update(fichier=f"tresor_{k}.txt")
        pose[f"{piece}/tresor_{k}.txt"] = "💎"
    elif m == "mot":
        mot = r.choice(MOTS_MAGIQUES)
        p.update(tas=f"pile_{k}", reponse=f"mot_{k}.txt", mot=mot)
        n = r.randint(5, 9)
        bon = r.randrange(n)
        for i in range(n):
            pose[f"{piece}/pile_{k}/papier_{i + 1}.txt"] = ("MOTSECRET : " + mot) if i == bon else "…"
    return {"m": m, "p": p, "pose": pose}


def _but_gen(g):
    m, p = g["m"], g["p"]
    if m == "perdu":
        return [("fichier", f"nid/{p['fichier']}")]
    if m == "construire":
        return [("dossier", f"{p['piece']}/{p['nom']}")]
    if m == "copie":
        return [("fichier", f"nid/copies/{p['fichier']}")]
    if m == "compter":
        rel = f"{p['piece']}/{p['tas']}"
        return [("reponse", f"nid/{p['reponse']}", lambda s: _compte(rel, r"caillou_.*"))]
    if m == "proteger":
        return [("protege", f"{p['piece']}/{p['fichier']}")]
    if m == "mot":
        return [("contient", f"nid/{p['reponse']}", p["mot"])]
    return []


# ---------------------------------------------------------------- l'état
def q_(state):
    q = state.setdefault("quetes", {})
    for k, v in {"actives": [], "finies": [], "suivie": None, "vu": {}, "gen": {}, "gen_n": 0, "offertes": [],
                 "jour": None, "objets": [], "titres": [], "titre": None, "poses": [], "souvenirs": []}.items():
        q.setdefault(k, v)
    return q


def _dispo(state, quete):
    """La quête existe dans cette partie : sa pièce est ouverte (et le nid construit pour le nid)."""
    from . import histoire
    if IS_WIN and not quete["win"]:
        return False
    p = quete["piece"]
    if p == "nid":
        return "nid0" in histoire.h_(state)["faits"] and (T() / "nid").is_dir()
    return histoire.piece_ouverte(state, p) and (T() / p).is_dir()


def texte(state, qid, cle="texte"):
    """Le texte d'une quête (écrite à la main ou générée), avec le jargon du palier."""
    q = q_(state)
    d = termes(palier(state))
    d["nom"] = state.get("name", "")
    if qid in q["gen"]:
        g = q["gen"][qid]
        p = dict(g["p"])
        if "piece" in p:
            p["dossier_piece"] = p["piece"]
            p["piece"] = maison.nom_piece(p["piece"])
        if "objet" in p:
            p["objet"] = t("qu.objet." + p["objet"])
        d.update(p)
        return t(f"qu.gen.{g['m']}.{cle}", **d)
    return t(f"qu.{qid}.{cle}", **d)


def titre(state, qid):
    return texte(state, qid, "titre")


def _ecrire(rel, contenu):
    p = T() / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            p.write_bytes(contenu)
        else:
            p.write_text(contenu + ("" if contenu.endswith("\n") or not contenu else "\n"), encoding="utf-8")
    except OSError:
        pass


def poser(state):
    """Pose les lettres, habitants, cachettes et objets des quêtes dont la pièce vient de s'ouvrir (une fois)."""
    q = q_(state)
    for quete in QUETES:
        if quete["id"] in q["poses"] or not _dispo(state, quete):
            continue
        q["poses"].append(quete["id"])
        p = quete["piece"]
        if quete["sorte"] == "cachette":
            _ecrire(f"{p}/{quete['fichier']}/tresor.txt", texte(state, quete["id"]))
        else:
            if not (T() / p / quete["fichier"]).exists():
                _ecrire(f"{p}/{quete['fichier']}", texte(state, quete["id"]))
        if quete["pose"]:
            for rel, contenu in quete["pose"](state).items():
                if not (T() / rel).exists():
                    _ecrire(rel, contenu)


# ---------------------------------------------------------------- le tableau des annonces et la quête du jour
def _tableau(state):
    q = q_(state)
    lignes = [t("qu.tableau.titre"), ""]
    for i, gid in enumerate(q["offertes"], 1):
        etat = " ✔" if gid in q["finies"] else (" ▶" if gid in q["actives"] else "")
        lignes.append(f"{i}. {titre(state, gid)}{etat}")
        lignes.append("   " + texte(state, gid))
        lignes.append("")
    lignes.append(t("qu.tableau.pied"))
    _ecrire("vestibule/tableau_des_annonces.txt", "\n".join(lignes))


def _nouvelle_gen(state, gid=None):
    q = q_(state)
    if gid is None:
        q["gen_n"] += 1
        gid = f"g{q['gen_n']}"
    g = generer(state, gid, core.level(state.get("xp", 0)))
    for rel, contenu in g.pop("pose").items():
        if not (T() / rel).exists():
            _ecrire(rel, contenu)
    q["gen"][gid] = g
    return gid


def annonces(state):
    """Le vestibule propose toujours NB_ANNONCES quêtes générées (dès qu'il existe)."""
    from . import histoire
    if not histoire.piece_ouverte(state, "vestibule") or not (T() / "vestibule").is_dir():
        return
    q = q_(state)
    change = False
    q["offertes"] = [g for g in q["offertes"] if g not in q["finies"]]
    while len(q["offertes"]) < NB_ANNONCES:
        q["offertes"].append(_nouvelle_gen(state))
        change = True
    if change or not (T() / "vestibule" / "tableau_des_annonces.txt").exists():
        _tableau(state)


def quete_du_jour(state):
    """Une quête par jour (graine de la partie + la date). Celle d'hier s'en va si elle n'est pas faite."""
    from . import histoire
    if "nid0" not in histoire.h_(state)["faits"]:
        return
    q = q_(state)
    jour = datetime.date.today().strftime("%Y%m%d")
    if (q.get("jour") or {}).get("date") == jour:
        return
    ancien = (q.get("jour") or {}).get("id")
    if ancien and ancien in q["actives"]:
        q["actives"].remove(ancien)
    gid = _nouvelle_gen(state, f"j{jour}")
    q["jour"] = {"date": jour, "id": gid}
    q["actives"].append(gid)
    core.log(state, t("qu.jour.log", titre=titre(state, gid)))


# ---------------------------------------------------------------- vérifier
def _vrai(state, qid, spec):
    k = spec[0]
    if k == "visite":
        return maison.visitee(state, spec[1])
    if k == "fichier":
        return (T() / spec[1]).is_file()
    if k == "plein":
        return bool((_lire(spec[1]) or "").strip())
    if k == "dossier":
        return (T() / spec[1]).is_dir()
    if k == "contient":
        mot = spec[2](state) if callable(spec[2]) else spec[2]
        return mot.lower() in (_lire(spec[1]) or "").lower()
    if k == "lignes":
        return _lignes(spec[1]) >= spec[2]
    if k == "nb":
        return _compte(spec[1], spec[2]) >= spec[3]
    if k == "reponse":
        x = (_lire(spec[1]) or "").strip()
        return x.isdigit() and int(x) == spec[2](state)
    if k == "trie":
        a, b = _lire(spec[1]), _lire(spec[2])
        la = [l.strip() for l in (a or "").split("\n") if l.strip()]
        lb = [l.strip() for l in (b or "").split("\n") if l.strip()]
        return bool(la) and la == sorted(lb)
    if k == "protege":
        from .lecons import _protected
        return (T() / spec[1]).is_file() and _protected(T() / spec[1])
    if k == "exec":
        p = T() / spec[1]
        return p.is_file() and os.access(p, os.X_OK)
    if k == "commits":
        try:
            return len((T() / "carnet" / ".git" / "logs" / "HEAD").read_text(encoding="utf-8").splitlines()) >= spec[1]
        except OSError:
            return False
    if k == "ip":
        return bool(re.search(r"\b(\d{1,3}\.){3}\d{1,3}\b|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}", _lire(spec[1]) or "", re.I))
    if k in ("cmd", "cmd_ici"):
        return bool(q_(state)["vu"].get(qid))
    return False


def buts(state, qid):
    q = q_(state)
    if qid in q["gen"]:
        return _but_gen(q["gen"][qid])
    return PAR_ID[qid]["but"]


def _voir_commandes(state, qid, lignes):
    for l, cwd in lignes:
        for spec in buts(state, qid):
            if spec[0] == "cmd" and re.search(spec[1], l, re.I):
                q_(state)["vu"][qid] = True
            if spec[0] == "cmd_ici" and re.search(spec[1], l, re.I) and maison.dans(cwd, spec[2]):
                q_(state)["vu"][qid] = True


def recompenser(state, rec, souvenir=None):
    """XP, objet (une décoration dans le nid), titre, et un souvenir dans le carnet d'aventure."""
    q = q_(state)
    if rec.get("xp"):
        core.add_xp(state, rec["xp"])
    obj = rec.get("objet")
    if obj and obj not in q["objets"]:
        q["objets"].append(obj)
        if (T() / "nid").is_dir():
            _ecrire(f"nid/decorations/{obj}.txt", t("qu.deco.fichier", objet=t("qu.objet." + obj)))
        core.log(state, t("qu.objet.log", objet=t("qu.objet." + obj)))
    ti = rec.get("titre")
    if ti and ti not in q["titres"]:
        q["titres"].append(ti)
        q["titre"] = ti
        core.log(state, t("qu.titre.log", titre=t("qu.titre." + ti)))
    if souvenir:
        q["souvenirs"] = (q["souvenirs"] + [list(souvenir)])[-200:]


def terminer(state, qid):
    q = q_(state)
    if qid in q["actives"]:
        q["actives"].remove(qid)
    if qid not in q["finies"]:
        q["finies"].append(qid)
    if q.get("suivie") == qid:
        q["suivie"] = None
    nom = titre(state, qid)
    if qid in q["gen"]:
        rec = {"xp": 40 if qid.startswith("j") else 20}
    else:
        d = PAR_ID[qid]
        rec = {"xp": d["xp"], "objet": d["objet"], "titre": d["titre"]}
    core.log(state, t("qu.finie.log", titre=nom))
    core.say(state, t("qu.finie.dit", titre=nom, xp=rec["xp"]), 12)
    core.animer(state, "victoire")
    recompenser(state, rec, souvenir=("quete", qid))
    if qid in q["offertes"]:
        annonces(state)
        _tableau(state)


def accepter(state, qid):
    q = q_(state)
    if qid in q["actives"] or qid in q["finies"]:
        return
    q["actives"].append(qid)
    core.log(state, t("qu.acceptee.log", titre=titre(state, qid)))
    core.say(state, t("qu.acceptee.dit", titre=titre(state, qid)), 10)


def _lues(lignes):
    """Les noms de fichiers lus (cat, less…) dans ces lignes."""
    out = []
    for l, _cwd in lignes:
        if re.search(LIRE, l, re.I):
            out += [os.path.basename(x.strip("'\"")) for x in l.split()[1:]]
    return out


def tick(state, lignes, cwds):
    """À chaque étape de jeu, après les leçons."""
    if not T().is_dir():
        return
    from . import intro
    if not intro.ouvert(state, "quetes"):           # les quêtes arrivent avec leur présentation (intro.json)
        return
    q = q_(state)
    poser(state)
    annonces(state)
    quete_du_jour(state)
    tapees = [(l, c) for l, c in zip(lignes, cwds) if not core.est_colle(l)]
    lus = _lues(tapees)
    for quete in QUETES:
        qid = quete["id"]
        if qid in q["finies"] or qid not in q["poses"]:
            continue
        if quete["sorte"] == "cachette":
            if maison.visitee(state, f"{quete['piece']}/{quete['fichier']}"):
                core.say(state, t("qu.cachette.dit"), 10)
                terminer(state, qid)
        elif qid not in q["actives"] and quete["fichier"] in lus:
            accepter(state, qid)
    if "tableau_des_annonces.txt" in lus:
        for gid in q["offertes"]:
            accepter(state, gid)
        _tableau(state)
    for qid in list(q["actives"]):
        if qid not in q["gen"] and qid not in PAR_ID:
            q["actives"].remove(qid)
            continue
        _voir_commandes(state, qid, tapees)
        if all(_vrai(state, qid, s) for s in buts(state, qid)):
            terminer(state, qid)


# ---------------------------------------------------------------- pour la carte et l'écran
def secrets(state):
    q = q_(state)
    caches = [x for x in QUETES if x["sorte"] == "cachette" and x["id"] in q["poses"]]
    return sum(1 for x in caches if x["id"] in q["finies"]), len(caches)


def piece_de_quete(state, qid):
    q = q_(state)
    if qid in q["gen"]:
        return q["gen"][qid]["p"].get("piece")
    return PAR_ID[qid]["piece"]


def etoile(state, p):
    """★ : une quête à trouver (lettre pas encore lue) ou en cours dans cette pièce."""
    q = q_(state)
    for quete in QUETES:
        if quete["piece"] == p and quete["sorte"] != "cachette" and quete["id"] in q["poses"] \
                and quete["id"] not in q["finies"]:
            return True
    if p == "vestibule" and any(g not in q["actives"] for g in q["offertes"]):
        return True
    return any(piece_de_quete(state, x) == p for x in q["actives"])


def numerotees(state):
    """Les quêtes secondaires en cours, dans l'ordre du journal (pour « quetes suivre 3 »)."""
    q = q_(state)
    jour = (q.get("jour") or {}).get("id")
    return sorted(q["actives"], key=lambda x: (x != jour,))


def suivre(state, n):
    liste = numerotees(state)
    try:
        i = int(n)
    except (TypeError, ValueError):
        return t("qu.suivre.aide")
    if not 1 <= i <= len(liste):
        return t("qu.suivre.aucune", n=n)
    q_(state)["suivie"] = liste[i - 1]
    return t("qu.suivre.ok", titre=titre(state, liste[i - 1]))


def ligne_suivie(state):
    q = q_(state)
    s = q.get("suivie")
    if s and s in q["actives"]:
        return t("qu.suivie", titre=titre(state, s), piece=maison.nom_piece(piece_de_quete(state, s) or "vestibule"))
    return None


def journal(state):
    """tg quetes : la quête principale, les secondaires en cours (numérotées) et les terminées."""
    from . import histoire, lecons
    q = q_(state)
    out = [f" {fg(213)}── 📜 " + t("qu.journal.titre", nom=state["name"]) + f" ──{RESET}"]
    if q.get("titre"):
        out.append(f" {DIM}" + t("qu.journal.titre_porte", titre=t("qu.titre." + q["titre"])) + RESET)
    out.append("")
    out.append(f" {BOLD}" + t("qu.journal.principale") + RESET)
    les, etiq = histoire.lecon_courante(state)
    if les:
        out.append(f"   ▶ {etiq} · {lecons.tx(les['titre'])}")
        out.append(f"     {fg(226)}➜ {les['steps'][state['step']]['cmd']}{RESET}")
    else:
        b = histoire.bandeau(state)
        out.append("   " + (b[1] if b else t("qu.journal.rien")))
    out.append("")
    out.append(f" {BOLD}" + t("qu.journal.en_cours") + RESET)
    liste = numerotees(state)
    jour = (q.get("jour") or {}).get("id")
    if not liste:
        out.append(f"   {DIM}" + t("qu.journal.aucune") + RESET)
    for i, qid in enumerate(liste, 1):
        marque = "👣 " if q.get("suivie") == qid else ""
        quoi = f"{fg(214)}" + t("qu.journal.du_jour") + f"{RESET} " if qid == jour else ""
        out.append(f"   {i}. {marque}{quoi}{BOLD}{titre(state, qid)}{RESET} {DIM}({maison.nom_piece(piece_de_quete(state, qid) or 'vestibule')}){RESET}")
        for x in _couper(texte(state, qid), 72):
            out.append(f"      {DIM}{x}{RESET}")
    out.append("")
    finies = [x for x in q["finies"]]
    a_trouver = sum(1 for x in QUETES if x["id"] in q["poses"] and x["id"] not in q["finies"]
                    and x["id"] not in q["actives"] and x["sorte"] != "cachette")
    out.append(f" {BOLD}" + t("qu.journal.terminees", n=len(finies)) + RESET)
    for qid in finies[-5:][::-1]:
        out.append(f"   ✔ {titre(state, qid)}")
    s, tot = secrets(state)
    out.append("")
    out.append(" " + t("qu.journal.bilan", lettres=a_trouver, secrets=s, total=tot, objets=len(q["objets"])))
    out.append(f" {DIM}" + t("qu.journal.aide") + RESET)
    return out


def _couper(x, n):
    from .langue import envelopper
    return envelopper(x, n)
