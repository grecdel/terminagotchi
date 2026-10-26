"""« La Maison endormie » : le fil conducteur du Terminagotchi (PC), en 10 chapitres.

L'enfant trouve un œuf dans une vieille maison abandonnée : l'ordinateur. La maison s'est endormie
et les monstres de 10 familles se sont installés chacun dans une pièce. Avec sa créature, il réveille
la maison pièce par pièce. Chaque chapitre a un vrai problème à résoudre ; les commandes sont les
outils pour le résoudre.

   1 reveil        Le réveil                 pwd, ls, cd              (on trouve l'œuf)
   2 nid           Le nid                    mkdir, touch, >, cat     (une chambre et un repas)
   3 grenier       Le grenier des Sylvestres tree, mv, cp, rm         (des lianes ont tout mélangé)
   4 cave          La cave des Démons        whoami, sudo -h, chmod   (ils volent la nourriture)
   5 bibliotheque  La bibliothèque           find, less, grep, head, wc (un livre a disparu)
   6 machines      La salle des machines     free, du, df, rm         (la maison étouffe)
   7 dortoir       Le dortoir                ps, &, jobs, kill        (des fantômes refusent de dormir)
   8 atelier       L'atelier des Constructs  scripts, chmod +x, alias, git
   9 tour          La tour des Célestes      ping, ip, curl, nslookup, ssh -V
  10 coeur         Le cœur de la maison      rev, ls -a, find, cat >, grep | wc, puis Abyssor
  (+ telephone : le jardin du téléphone, seulement dans Termux, hors compte)

Liberté : après le chapitre 2, les ailes 3 à 9 se réveillent dans l'ordre qu'on veut. On choisit
une aile en y entrant (cd grenier) ou avec le menu [a] / tg aile <nom>. On peut changer d'aile en
cours de route : l'étape atteinte est gardée (« pas »). Le chapitre 10 s'ouvre quand au moins
5 ailes sont réveillées. La difficulté s'adapte : le niveau demandé suit le nombre d'ailes déjà
réveillées, et les étapes « expert » n'apparaissent qu'à partir du niveau 10.

Les leçons réutilisent les étapes (commandes, validations, textes) de lecons.py : TRONC et ARBRE
restent le catalogue ; ce module les range en chapitres et ajoute ce qui manquait.
Pendant un chapitre, sa famille de monstres est attirée (même champ « attire » que l'attirance
par commande, vérifiable par le serveur : la commande de la famille doit avoir été goûtée).

Sauvegarde : state["histoire"] = {chap, faits (leçons finies), ailes (chapitres finis), pas (étape
gardée par leçon), ouverts (chapitres annoncés), carnet ({commande: chapitre}), meubles…}.
Les anciennes sauvegardes (lesson / arbre / branche) sont rangées dans les bons chapitres (migrer).
"""
import os
import random
import re

from . import core, lecons, maison
from .langue import t
from .mots import palier, termes
from .plateforme import C, IS_WIN, OSK, est_colle, installer

S = lecons.S
CD = lecons.CD
NIVEAU_EXPERT = 10
AILES_POUR_LE_COEUR = 5
T = lambda: core.TERRAIN  # noqa: E731


def _ref(lid, i):
    return dict(lecons.PAR_ID[lid]["steps"][i])


def _entree(piece):
    return {"dit": ("hist.entree.dit", {"piece": piece}), "cmd": f"cd ~/terrain_terminagotchi/{piece}",
            "ici": piece, "bravo": ("hist.entree.bravo", {"piece": piece})}


def _n(lid, i, **k):
    """Une étape nouvelle : textes hist.<leçon>.<i>.dit / .bravo."""
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"

# ---------------------------------------------------------------- les leçons de l'histoire
NOUVELLES = {
    "reveil1": {"titre": "hist.reveil1.titre", "skill": None, "steps": [
        _n("reveil1", 0, cmd="cd terrain_terminagotchi", ici=""),
        _n("reveil1", 1, cmd=C("ls", "dir"), re=LS, ou=""),
        _n("reveil1", 2, cmd="cd vestibule", ici="vestibule"),
        _n("reveil1", 3, cmd=C("ls", "dir"), re=LS, ou="vestibule"),
    ]},
    "nid0": {"titre": "lec.t1.titre", "skill": "Bâtisseur", "steps": [
        _n("nid0", 0, cmd="cd ..", ici="", exact=True),
        _ref("t1", 2),
        _n("nid0", 2, cmd=C(f"touch nid{S}lit.txt", f"New-Item nid{S}lit.txt"), fs="lit"),
    ]},
    # une pièce en trop : démolir une pièce vide (rmdir), puis la broyeuse pour une pièce pleine (rm -r)
    "debarras": {"titre": "hist.debarras.titre", "skill": None, "steps": [
        _n("debarras", 0, cmd="mkdir debarras", fs="debarras_la"),
        _n("debarras", 1, cmd="rmdir debarras", fs="debarras_parti"),
        _n("debarras", 2, cmd="rm -r vieille_cabane", fs="cabane_partie"),
    ]},
    "nid1": {"titre": "lec.t2.titre", "skill": None, "steps": [_ref("t2", 0), _ref("t2", 1)]},
    "grenier0": {"titre": "hist.grenier0.titre", "skill": "Explorateur", "steps": [
        _entree("grenier"),
        _n("grenier0", 1, cmd=C("tree", "tree /f"), re=r"^(tree|ls\s+-\w*R)\b",
           astuce=C(("hist.grenier0.1.astuce", {"cmd": installer("tree")}), None)),
        _n("grenier0", 2, cmd=C(f"mv fouillis{S}ours_en_peluche.txt ..{S}nid{S}",
                                f"move fouillis{S}ours_en_peluche.txt ..{S}nid{S}"), fs="ours"),
    ]},
    "cave0": {"titre": "hist.cave0.titre", "skill": None, "steps": [
        _entree("cave"),
        _ref("systeme0", 0),
        _n("cave0", 2, cmd="sudo -h", re=r"^sudo\s+(-h|--help|-V)\b", astuce="hist.cave0.2.astuce", win=False),
    ]},
    "biblio0": {"titre": "hist.biblio0.titre", "skill": None, "steps": [
        _entree("bibliotheque"),
        _n("biblio0", 1, cmd=C('find . -name "*abysses*"', "Get-ChildItem -Recurse -Filter *abysses*"),
           re=r"^(find|get-childitem|gci|dir)\b.*abyss"),
        _n("biblio0", 2, cmd=C(f"less etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt",
                               f"more etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt"),
           re=r"^(less|more|cat|type|gc|get-content)\b.*abysses", astuce="lec.git2.2.astuce"),
    ]},
    "biblio1": {"titre": "hist.biblio1.titre", "skill": "Inspecteur", "steps": [
        _ref("t2", 2),
        _n("biblio1", 1, cmd=C(f"head -n 3 etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt",
                               f"Get-Content etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt -Head 3"),
           re=r"^(head|get-content|gc)\b.*abysses"),
        _n("biblio1", 2, cmd=C(f"wc -l etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt",
                               f"Get-Content etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt | Measure-Object -Line"),
           re=r"^(wc\b|get-content.*measure-object|gc.*measure)"),
        _n("biblio1", 3, cmd=C("grep -rn TRESOR .", "Select-String -Path * -Pattern TRESOR"),
           re=r"^(grep\s+-\w*r|select-string|sls)\b.*tresor", expert=True),
    ]},
    "machines0": {"titre": "hist.machines0.titre", "skill": None, "steps": [
        _entree("salle_des_machines"),
        _n("machines0", 1, cmd="free -h", re=r"^free\b", win=False),
        _n("machines0", 2, cmd=C("du -sh *", "Get-ChildItem | Measure-Object Length -Sum"),
           re=r"^(du|get-childitem|gci|dir)\b", ou="salle_des_machines"),
        _n("machines0", 3, cmd=C("rm vieux_carton.bin", "rm vieux_carton.bin"), fs="carton"),
    ]},
    "dortoir0": {"titre": "hist.dortoir0.titre", "skill": "Vigie", "steps": [
        _entree("dortoir"),
        _ref("systeme0", 1),
    ]},
    "atelier0": {"titre": "hist.atelier0.titre", "skill": None, "steps": [
        _entree("atelier"),
        _n("atelier0", 1, cmd=C("cat plan_de_travail.txt", "type plan_de_travail.txt"), re=LIRE + r".*plan_de_travail"),
    ]},
    "tour0": {"titre": "lec.reseau0.titre", "skill": "Radar", "steps": [
        _entree("tour"),
        _ref("reseau0", 0),
        _ref("reseau0", 1),
    ]},
    "tour2": {"titre": "lec.reseau2.titre", "skill": "Cartographe", "steps": [
        _ref("reseau2", 0),
        _n("tour2", 1, cmd="ssh -V", re=r"^ssh\s+-V\b"),
        dict(_ref("reseau2", 1), expert=True),
    ]},
    "coeur0": {"titre": "hist.coeur0.titre", "skill": None, "steps": [
        _entree("coeur"),
        _n("coeur0", 1, cmd="rev message_brouille.txt", re=r"(^|\s)rev\b.*message", win=False,
           astuce="hist.coeur0.1.astuce"),
        _n("coeur0", 2, cmd=C("ls -a", "dir -Force"), re=r"^(ls\s+-\w*a|dir\s+-force|gci\s+-force|get-childitem\s+-force)",
           ou="coeur"),
        _n("coeur0", 3, cmd="cd .porte_secrete", ici="coeur/.porte_secrete"),
    ]},
    "coeur1": {"titre": "hist.coeur1.titre", "skill": None, "steps": [
        _n("coeur1", 0, cmd=C('find ~/terrain_terminagotchi -name "fragment*"',
                              "Get-ChildItem ~/terrain_terminagotchi -Recurse -Filter fragment*"),
           re=r"^(find|get-childitem|gci|dir)\b.*fragment"),
        _n("coeur1", 1, cmd=C(f"cat coeur/.porte_secrete/fragment_1.txt grenier/fragment_2.txt tour/fragment_3.txt"
                              f" > coeur/coeur_repare.txt",
                              "Get-Content coeur/.porte_secrete/fragment_1.txt, grenier/fragment_2.txt, "
                              "tour/fragment_3.txt > coeur/coeur_repare.txt"), fs="coeur_repare"),
        _n("coeur1", 2, cmd=C("chmod 444 coeur/coeur_repare.txt", "attrib +r coeur/coeur_repare.txt"), fs="coeur_protege"),
    ]},
    "coeur2": {"titre": "hist.coeur2.titre", "skill": "Héros", "steps": [
        _n("coeur2", 0, cmd=C("cat coeur/.porte_secrete/abyssor_dort.txt", "type coeur/.porte_secrete/abyssor_dort.txt"),
           re=LIRE + r".*abyssor"),
        _n("coeur2", 1, cmd=C("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l",
                              "(Get-ChildItem ~/terrain_terminagotchi -Recurse -File | Select-String ABYSSOR "
                              "-CaseSensitive -List).Count"),
           re=r"(grep|select-string|sls)\b.*abyssor"),
        _n("coeur2", 2, cmd="echo ? > coeur/reponse.txt", fs="reponse"),
    ]},
}
# les étapes en plus pour les experts (niveau 10 et plus) dans les leçons reprises telles quelles
EXPERT = {
    "t4": [_n("t4", 3, cmd=C(f"cp -r grenier{S}fouillis grenier{S}fouillis_secours",
                             f"Copy-Item -Recurse grenier{S}fouillis grenier{S}fouillis_secours"), fs="fouillis_copie",
              expert=True)],
}

CHAPITRES = [
    {"id": "reveil", "n": 1, "piece": "vestibule", "famille": None, "lecons": ["t0", "reveil1"], "niveaux": [2, 2],
     "objet": "veilleuse"},
    {"id": "nid", "n": 2, "piece": "nid", "famille": None, "lecons": ["nid0", "debarras", "nid1"], "niveaux": [3, 3, 4],
     "objet": "coussin"},
    {"id": "grenier", "n": 3, "piece": "grenier", "famille": "Sylvestres", "lecons": ["grenier0", "t4"],
     "objet": "plante", "titre": "jardinier"},
    {"id": "cave", "n": 4, "piece": "cave", "famille": "Démons", "lecons": ["cave0", "t3"],
     "objet": "cadenas_dore", "titre": "gardien_des_cles"},
    {"id": "bibliotheque", "n": 5, "piece": "bibliotheque", "famille": "Abyssaux", "lecons": ["biblio0", "biblio1"],
     "objet": "marque_page", "titre": "bibliothecaire"},
    {"id": "machines", "n": 6, "piece": "salle_des_machines", "famille": "Élémentaires", "lecons": ["machines0", "systeme1"],
     "objet": "ventilateur", "titre": "mecanicien"},
    {"id": "dortoir", "n": 7, "piece": "dortoir", "famille": "Morts-vivants", "lecons": ["dortoir0", "systeme2"],
     "objet": "boite_a_musique", "titre": "veilleur"},
    {"id": "atelier", "n": 8, "piece": "atelier", "famille": "Constructs",
     "lecons": ["atelier0", "scripts0", "scripts1", "git0", "git1", "git2"], "objet": "robot_jouet", "titre": "inventeur"},
    {"id": "tour", "n": 9, "piece": "tour", "famille": "Célestes", "lecons": ["tour0", "reseau1", "tour2"],
     "objet": "telescope", "titre": "astronome"},
    {"id": "coeur", "n": 10, "piece": "coeur", "famille": "Aberrations", "lecons": ["coeur0", "coeur1", "coeur2"],
     "niveaux": [10, 11, 12], "objet": "couronne", "titre": "heros"},
    {"id": "telephone", "n": 0, "piece": "jardin", "famille": None, "android": True,
     "lecons": ["android0", "android1", "android2", "android3"], "objet": "antenne"},
]
PAR_CHAP = {c["id"]: c for c in CHAPITRES}
AILES = [c["id"] for c in CHAPITRES if 3 <= c["n"] <= 9]


def chapitre_dispo(c):
    return not c.get("android") or OSK == "android"


def lecon_def(lid):
    if lid in NOUVELLES:
        return NOUVELLES[lid]
    base = lecons.PAR_ID[lid]
    return {"titre": base["titre"], "skill": base["skill"], "steps": list(base["steps"]) + EXPERT.get(lid, [])}


def chapitre_de_lecon(lid):
    return next((c for c in CHAPITRES if lid in c["lecons"]), None)


def chapitre_de_piece(p):
    return next((c for c in CHAPITRES if c["piece"] == p), None)


# ---------------------------------------------------------------- l'état
def h_(state):
    h = state.get("histoire")
    if not isinstance(h, dict):
        migrer(state)
        h = state["histoire"]
    for k, v in {"chap": "reveil", "faits": [], "ailes": [], "pas": {}, "ouverts": [], "annonce": None,
                 "carnet": {}, "meubles": [], "suggere": [], "v": 1}.items():
        h.setdefault(k, v)
    if h["v"] < 2:
        _version_v2(state, h)
    return h


def _version_v2(state, h):
    """Sauvegarde v1 → v2 : la leçon « Une pièce en trop » (debarras) arrive entre le nid (nid0) et le garde-manger
    (nid1). Le chapitre 2 déjà fini la compte comme faite ; une partie en plein garde-manger le garde (son étape est
    rangée pour après le débarras) ; une partie en plein nid0 continue nid0 à la même étape."""
    h["v"] = 2
    if "debarras" in h["faits"]:
        return
    if "nid1" in h["faits"] or "nid" in h["ailes"]:
        h["faits"].append("debarras")
    elif "nid0" in h["faits"] and h.get("chap") == "nid":
        if state.get("step", 0) > 0:
            h["pas"]["nid1"] = state["step"]
        state["step"] = 0


def fini(state, cid):
    return cid in h_(state)["ailes"]


def nb_ailes(state):
    return sum(1 for a in h_(state)["ailes"] if a in AILES)


def ouvert(state, cid):
    """Le chapitre peut être joué (ou rejoué) maintenant."""
    c = PAR_CHAP.get(cid)
    if not c or not chapitre_dispo(c):
        return False
    if cid == "reveil":
        return True
    if cid == "nid":
        return fini(state, "reveil")
    if cid == "coeur":
        return nb_ailes(state) >= AILES_POUR_LE_COEUR
    return fini(state, "nid")


def piece_ouverte(state, p):
    """La pièce existe dans la maison de cette partie (sa porte a été posée)."""
    if p == "vestibule":
        h = h_(state)
        return fini(state, "reveil") or (h.get("chap") == "reveil" and "t0" in h["faits"])
    c = chapitre_de_piece(p)
    if not c:
        return False
    if p == "nid":
        return fini(state, "reveil")
    return ouvert(state, c["id"])


def _palier(state):
    return palier(state)


def dire(state, cle, **p):
    """Un texte de l'histoire, avec le jargon du palier de l'enfant ({dossier}, {processus}…)."""
    d = termes(_palier(state))
    d.update(p)
    return t(cle, **d)


def nom_chapitre(cid):
    return t(f"hist.{cid}.titre")


def niveau_requis(state, c, i):
    if c.get("niveaux"):
        return c["niveaux"][min(i, len(c["niveaux"]) - 1)]
    # les ailes : la difficulté suit le nombre d'ailes déjà réveillées (ordre libre)
    return min(12, 5 + nb_ailes(state) + i)


def etapes(state, lid):
    niv = core.level(state.get("xp", 0))
    return [s for s in lecon_def(lid)["steps"]
            if (not s.get("expert") or niv >= NIVEAU_EXPERT) and not (IS_WIN and s.get("win") is False)]


def chapitre_courant(state):
    h = h_(state)
    c = PAR_CHAP.get(h.get("chap"))
    if c and ouvert(state, c["id"]) and not fini(state, c["id"]):
        return c
    return None


def lecon_id(state):
    c = chapitre_courant(state)
    if not c:
        return None
    faits = h_(state)["faits"]
    return next((lid for lid in c["lecons"] if lid not in faits), None)


def lecon_courante(state):
    """(leçon, étiquette) ou (None, None). La leçon : titre, skill, niveau, steps (filtrées), id, chap."""
    lid = lecon_id(state)
    if not lid:
        return None, None
    c = chapitre_courant(state)
    i = c["lecons"].index(lid)
    d = lecon_def(lid)
    st = etapes(state, lid)
    if not st:
        return None, None
    if state.get("step", 0) >= len(st):
        # filet de sécurité : toutes les étapes sont faites (sauvegarde d'une autre version…) → la leçon se termine
        finir_lecon(state, {"id": lid, "chap": c["id"], "titre": d["titre"], "skill": d["skill"], "steps": st})
        return lecon_courante(state)
    state["step"] = max(0, min(state.get("step", 0), len(st) - 1))
    les = {"id": lid, "chap": c["id"], "titre": d["titre"], "skill": d["skill"], "steps": st,
           "niveau": niveau_requis(state, c, i)}
    lecons.PALIER[0] = _palier(state)
    return les, t("hist.etiquette", n=c["n"], chapitre=nom_chapitre(c["id"]), i=i + 1, total=len(c["lecons"]))


# ---------------------------------------------------------------- vérifications de fichiers
def _ecrire(rel, texte, binaire=False):
    p = T() / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if binaire:
            p.write_bytes(texte)
        else:
            p.write_text(texte if texte.endswith("\n") else texte + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _lire(rel):
    p = T() / rel
    try:
        brut = p.read_bytes()
    except OSError:
        return None
    if brut[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return brut.decode("utf-16", errors="replace")
    return brut.decode("utf-8", errors="replace")


FRAGMENTS = ("coeur/.porte_secrete/fragment_1.txt", "grenier/fragment_2.txt", "tour/fragment_3.txt")


def _repare():
    txt = _lire("coeur/coeur_repare.txt")
    if not txt:
        return False
    for f in FRAGMENTS:
        x = (_lire(f) or "").strip()
        if not x or x not in txt:
            return False
    return True


def traces_abyssor():
    """Le nombre de fichiers de la maison qui contiennent le mot ABYSSOR (la réponse de l'énigme)."""
    n = 0
    if not T().is_dir():
        return 0
    for racine, dossiers, fichiers in os.walk(T()):
        dossiers[:] = [d for d in dossiers if d != ".git"]
        for f in fichiers:
            p = os.path.join(racine, f)
            if f == "reponse.txt" and os.path.basename(racine) == "coeur":
                continue
            try:
                if os.path.getsize(p) < 200000 and b"ABYSSOR" in open(p, "rb").read():
                    n += 1
            except OSError:
                pass
    return n


def _reponse():
    x = (_lire("coeur/reponse.txt") or "").strip()
    return x.isdigit() and int(x) == traces_abyssor()


def debarras():
    """Le débarras de la leçon « Une pièce en trop » (dans la grande salle ou dans le nid), ou None."""
    return next((p for p in (T() / "debarras", T() / "nid" / "debarras") if p.is_dir()), None)


lecons.FS.update({
    "lit": lambda: (T() / "nid" / "lit.txt").is_file(),
    "debarras_la": lambda: debarras() is not None,
    "debarras_parti": lambda: debarras() is None,
    "cabane_partie": lambda: not (T() / "vieille_cabane").exists() and T().is_dir(),
    "ours": lambda: (T() / "nid" / "ours_en_peluche.txt").is_file(),
    "carton": lambda: not (T() / "salle_des_machines" / "vieux_carton.bin").exists()
    and (T() / "salle_des_machines").is_dir(),
    "fouillis_copie": lambda: (T() / "grenier" / "fouillis_secours").is_dir(),
    "coeur_repare": _repare,
    "coeur_protege": lambda: _repare() and lecons._protected(T() / "coeur" / "coeur_repare.txt"),
    "reponse": _reponse,
})
lecons.CREE.update({"lit": "nid/lit.txt", "debarras_la": "debarras", "ours": "nid/ours_en_peluche.txt", "coeur_repare": "coeur/coeur_repare.txt"})


# ---------------------------------------------------------------- les meubles de la maison
def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _rnd(state, sel):
    return random.Random(f"{_graine(state)}:{sel}")


def _meubles(state, p):
    """Ce que le jeu pose dans une pièce quand sa porte s'ouvre : {chemin: texte (ou octets)}."""
    if p == "vestibule":
        return {"vestibule/oeuf_tout_chaud.txt": dire(state, "hist.meuble.oeuf")}
    if p == "grenier":
        return {"grenier/fouillis/ours_en_peluche.txt": dire(state, "hist.meuble.ours"),
                "grenier/fouillis/malle/vieille_robe.txt": dire(state, "hist.meuble.robe"),
                "grenier/fouillis/carton/jouet_casse.txt": dire(state, "hist.meuble.jouet")}
    if p == "bibliotheque":
        return {"bibliotheque/etagere_a/livre_des_recettes.txt": dire(state, "hist.meuble.recettes"),
                "bibliotheque/etagere_b/livre_des_etoiles.txt": dire(state, "hist.meuble.etoiles"),
                "bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt": livre_abysses(state)}
    if p == "salle_des_machines":
        return {"salle_des_machines/vieux_carton.bin": b"\0" * 300000}
    if p == "atelier":
        return {"atelier/plan_de_travail.txt": dire(state, "hist.meuble.plan")}
    if p == "nid":       # la vieille cabane pleine de planches de la leçon « Une pièce en trop » (seulement par BESOINS)
        return {"vieille_cabane/planche_1.txt": dire(state, "hist.meuble.planche"),
                "vieille_cabane/planche_2.txt": dire(state, "hist.meuble.planche")}
    if p == "coeur":
        m = {"coeur/message_brouille.txt": "\n".join(l[::-1] for l in dire(state, "hist.meuble.message").split("\n")),
             "coeur/.porte_secrete/abyssor_dort.txt": dire(state, "hist.meuble.abyssor")}
        for i, f in enumerate(FRAGMENTS):
            m[f] = t(f"hist.meuble.fragment.{i + 1}")
        r = _rnd(state, "abyssor")
        lieux = ["grenier/griffure.txt", "cave/griffure.txt", "bibliotheque/etagere_a/griffure.txt",
                 "dortoir/griffure.txt", "atelier/griffure.txt", "tour/griffure.txt", "vestibule/griffure.txt"]
        for f in r.sample(lieux, r.randint(3, 6)):
            m[f] = t("hist.meuble.griffure")
        return m
    return {}


def livre_abysses(state):
    return "\n".join(_liste("hist.meuble.abysses"))


def _liste(cle):
    from .langue import liste
    return liste(cle)


# fichiers dont une leçon a besoin : remis s'ils disparaissent (tant que l'étape n'est pas passée)
BESOINS = {
    "reveil1": [("vestibule/oeuf_tout_chaud.txt", None)],
    "debarras": [("vieille_cabane/planche_1.txt", 2), ("vieille_cabane/planche_2.txt", 2)],
    "grenier0": [("grenier/fouillis/ours_en_peluche.txt", 2)],
    "biblio0": [("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt", None)],
    "biblio1": [("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt", None)],
    "machines0": [("salle_des_machines/vieux_carton.bin", 3)],
    "atelier0": [("atelier/plan_de_travail.txt", None)],
    "coeur0": [("coeur/message_brouille.txt", None), ("coeur/.porte_secrete/abyssor_dort.txt", None)],
    "coeur1": [(f, 1) for f in FRAGMENTS],
    "coeur2": [("coeur/.porte_secrete/abyssor_dort.txt", None)],
}


def meubler(state):
    """Pose les portes des pièces ouvertes et leurs meubles (une fois). Jamais hors du terrain.
    Si le terrain a disparu après sa construction, rien n'est fait (terrain.py aide à le refaire)."""
    h = h_(state)
    lid = lecon_id(state)
    if not T().is_dir():
        if lid != "reveil1":
            return []
        try:
            T().mkdir(parents=True, exist_ok=True)
        except OSError:
            return []
    poses = []
    for p in maison.PIECES + ("jardin",):
        if p == "nid" or not piece_ouverte(state, p) and not (p == "vestibule" and lid == "reveil1"):
            continue
        d = T() / p
        if not d.is_dir():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            # la pièce avait disparu (terrain effacé) : ses meubles et ses quêtes pas finies reviennent
            if "piece:" + p in h["meubles"]:
                h["meubles"].remove("piece:" + p)
            from . import quetes
            q = quetes.q_(state)
            q["poses"] = [x for x in q["poses"] if x in q["finies"] or quetes.PAR_ID[x]["piece"] != p]
        cle = "piece:" + p
        if cle not in h["meubles"]:
            h["meubles"].append(cle)
            for rel, contenu in _meubles(state, p).items():
                if not (T() / rel).exists():
                    _ecrire(rel, contenu, binaire=isinstance(contenu, bytes))
                    poses.append(rel)
    # les fichiers dont la leçon en cours a besoin
    if lid in BESOINS:
        step = state.get("step", 0)
        piece = chapitre_courant(state)["piece"]
        tous = {}
        for p in (piece, "coeur", "grenier", "tour", "vestibule"):
            tous.update(_meubles(state, p) if piece_ouverte(state, p) or p == piece else {})
        for rel, jusque in BESOINS[lid]:
            if (jusque is None or step < jusque) and not (T() / rel).exists() and rel in tous:
                if lid == "grenier0" and (T() / "nid" / "ours_en_peluche.txt").exists():
                    continue
                _ecrire(rel, tous[rel], binaire=isinstance(tous[rel], bytes))
                poses.append(rel)
    return poses


# ---------------------------------------------------------------- choisir une aile
def choisir(state, cid, dit=True):
    """Commence (ou reprend) un chapitre. Renvoie le message à afficher."""
    c = PAR_CHAP.get(cid)
    if not c or not chapitre_dispo(c):
        return t("hist.aile.inconnue", nom=cid)
    if fini(state, cid):
        return t("hist.aile.deja", chapitre=nom_chapitre(cid))
    if not ouvert(state, cid):
        if cid == "coeur":
            return t("hist.coeur.ferme", n=nb_ailes(state), total=AILES_POUR_LE_COEUR)
        return t("hist.aile.fermee", chapitre=nom_chapitre(cid))
    h = h_(state)
    if h.get("chap") == cid and chapitre_courant(state):
        return t("hist.aile.en_cours", chapitre=nom_chapitre(cid))
    ancien = lecon_id(state)
    if ancien:
        h["pas"][ancien] = state.get("step", 0)          # l'étape atteinte est gardée
    h["chap"] = cid
    nouv = lecon_id(state)
    state["step"] = h["pas"].pop(nouv, 0) if nouv else 0
    state["annonce"] = None
    state["indice_lecon"] = None
    msg = t("hist.aile.choisie", chapitre=nom_chapitre(cid))
    if dit:
        core.say(state, msg, 8)
    return msg


def chercher_chapitre(nom):
    """« grenier », « 3 », « Le grenier… » → l'identifiant du chapitre (ou None)."""
    n = (nom or "").strip().lower()
    if not n:
        return None
    for c in CHAPITRES:
        if n in (c["id"], c["piece"], str(c["n"])) or (len(n) >= 3 and nom_chapitre(c["id"]).lower().find(n) >= 0):
            return c["id"]
    return None


def _visite_aile(state, cwds):
    """Entrer dans une aile pas encore réveillée la choisit (s'il n'y a pas de chapitre en cours)."""
    if not fini(state, "nid"):
        return
    h = h_(state)
    for cwd in cwds:
        p = maison.rel(cwd) if cwd else None
        if not p:
            continue
        c = chapitre_de_piece(p.split("/")[0])
        if not c or fini(state, c["id"]) or not ouvert(state, c["id"]) or h.get("chap") == c["id"]:
            continue
        if not chapitre_courant(state):
            choisir(state, c["id"])
        elif c["id"] not in h["suggere"]:
            h["suggere"].append(c["id"])
            core.say(state, t("hist.aile.autre", chapitre=nom_chapitre(c["id"]), id=c["id"]), 10)


# ---------------------------------------------------------------- avancer
def _finir_chapitre(state, c):
    from . import quetes
    h = h_(state)
    if c["id"] not in h["ailes"]:
        h["ailes"].append(c["id"])
    core.log(state, t("hist.chapitre.fini.log", chapitre=nom_chapitre(c["id"])))
    core.say(state, dire(state, f"hist.{c['id']}.fin"), 16)
    core.animer(state, "victoire")
    core.add_xp(state, 30)
    quetes.recompenser(state, {"objet": c.get("objet"), "titre": c.get("titre")}, souvenir=("chap", c["id"]))
    h["chap"] = None
    if c["id"] == "reveil":
        h["chap"] = "nid"
    elif c["id"] == "nid":
        core.say(state, dire(state, "hist.libre.dit"), 16)
    elif c["id"] == "coeur":
        core.say(state, dire(state, "hist.fin.dit"), 16)
    elif c["id"] in AILES:
        if nb_ailes(state) == AILES_POUR_LE_COEUR:
            core.log(state, t("hist.coeur.ouvert.log"))
            core.say(state, dire(state, "hist.coeur.ouvert.dit"), 16)
        else:
            core.say(state, t("hist.aile.suite", n=nb_ailes(state)), 12)
    state["annonce"] = None


def avancer(state, les):
    """Une étape réussie. Renvoie True s'il reste des étapes dans la leçon."""
    step = les["steps"][state["step"]]
    core.log(state, f"✔ {step['cmd']}")
    core.say(state, lecons.tx(step["bravo"]), 12)
    from . import explique
    explique.apres_reussite(state, step["cmd"])           # -r, >>, 444… : expliqués une fois (explique.py)
    state["step"] += 1
    core.animer(state, "content")
    if state["step"] < len(les["steps"]):
        core.add_xp(state, 5)
        return True
    finir_lecon(state, les)
    return False


def finir_lecon(state, les):
    h = h_(state)
    state["step"] = 0
    if les["id"] not in h["faits"]:
        h["faits"].append(les["id"])
    sk = les.get("skill")
    if sk and sk not in state["skills"]:
        state["skills"].append(sk)
    c = PAR_CHAP[les["chap"]]
    if sk:
        core.log(state, t("lec.finie.log", titre=lecons.tx(les["titre"]), skill=core.nom_skill(sk)))
        core.say(state, t("lec.finie.dit", skill=core.nom_skill(sk)), 14)
    else:
        core.log(state, t("hist.lecon.finie.log", titre=lecons.tx(les["titre"])))
        core.say(state, t("hist.lecon.finie.dit"), 12)
    stat = {"tour": "Agilité", "atelier": "Intelligence", "dortoir": "Force", "machines": "Force", "cave": "Force"}
    if c["id"] in stat:
        state["stats"][stat[c["id"]]] += 5
    core.add_xp(state, 20)
    state["annonce"] = None
    if all(x in h["faits"] for x in c["lecons"]):
        _finir_chapitre(state, c)
    else:
        nouv = lecon_id(state)
        state["step"] = h["pas"].pop(nouv, 0) if nouv else 0


def _ici_ok(step, cwd):
    if "ici" not in step or not cwd:
        return False
    if step.get("exact"):
        return maison.rel(cwd) == step["ici"]
    return maison.dans(cwd, step["ici"])


def tick_lecon(state, lines, cwds):
    # filet de sécurité : un chapitre dont toutes les leçons sont faites se termine (le suivant démarre)
    c = chapitre_courant(state)
    if c and all(x in h_(state)["faits"] for x in c["lecons"]):
        _finir_chapitre(state, c)
    les, _ = lecon_courante(state)
    if not les or core.level(state["xp"]) < les["niveau"]:
        return
    h = h_(state)
    if state.get("annonce") != les["titre"]:
        state["annonce"] = les["titre"]
        if les["chap"] not in h["ouverts"]:
            h["ouverts"].append(les["chap"])
            core.log(state, t("hist.chapitre.log", n=PAR_CHAP[les["chap"]]["n"], chapitre=nom_chapitre(les["chap"])))
            core.say(state, dire(state, f"hist.{les['chap']}.debut"), 18)
        else:
            core.say(state, t("lec.annonce"), 10)
        core.animer(state, "parle")
    tapees = [(l, c) for l, c in zip(lines, cwds) if not est_colle(l)]
    avant = (les["id"], state["step"])
    for line, cwd in tapees:
        step = les["steps"][state["step"]]
        ok = "re" in step and re.search(step["re"], line, re.I) and ("ou" not in step or maison.dans(cwd, step["ou"]))
        if ok or _ici_ok(step, cwd):
            if not avancer(state, les):
                state["indice_lecon"] = None
                return
    # les étapes déjà faites (fichiers, dossier courant) passent toutes, jusqu'à la fin de la leçon s'il le faut
    for _ in les["steps"]:
        step = les["steps"][state["step"]]
        if not (("fs" in step and lecons.FS[step["fs"]]()) or _ici_ok(step, maison.ici(state))):
            break
        if not avancer(state, les):
            state["indice_lecon"] = None
            return
    if avant != (les["id"], state["step"]):
        state["indice_lecon"] = None
    elif tapees:
        step = les["steps"][state["step"]]
        conseil = indice(state, step, [l for l, _ in tapees], tapees)
        if conseil and conseil != state.get("indice_lecon"):
            state["indice_lecon"] = conseil
            core.say(state, "💡 " + conseil, 12)


def indice(state, step, lignes, tapees):
    """Un indice quand c'est presque ça (mauvais endroit, faute de frappe, mauvais nombre…)."""
    if step.get("fs") == "reponse" and (T() / "coeur" / "reponse.txt").is_file():
        return t("hist.indice.nombre")
    if "ou" in step and "re" in step:
        for l, cwd in tapees:
            if re.search(step["re"], l, re.I) and not maison.dans(cwd, step["ou"]):
                return t("hist.indice.piece", piece=maison.nom_piece(step["ou"]) if step["ou"] else
                         maison.nom_piece("grande_salle"), cmd=f"cd ~/{T().name}/{step['ou']}".rstrip("/"))
    if "ici" in step:
        return None
    conseil = _indice_rm(step, tapees)
    if conseil:
        return conseil
    from . import dressage
    if not dressage.faute_de_frappe(lignes, step["cmd"], chiffres=True):
        conseil = _indice_chemin(step, tapees)
        if conseil:
            return conseil
    return lecons.indice(step, lignes)


def _cible(cwd, mot):
    """Le dossier visé par un mot tapé (relatif au dossier courant, ou ~/…)."""
    from pathlib import Path
    if mot.startswith("~"):
        return Path(os.path.expanduser(mot))
    return Path(cwd or Path.home()) / mot


def _indice_rm(step, tapees):
    """rm sur une pièce (« rm debarras » échoue) ; rmdir sur une pièce pleine (« rmdir vieille_cabane » refuse)."""
    for l, cwd in tapees:
        mots = l.split()
        if not mots:
            continue
        cmd, args = mots[0].lower(), [m for m in mots[1:] if not m.startswith("-")]
        if cmd == "rm" and not any(re.match(r"^-\w*[rR]", m) for m in mots[1:]):
            for a in args:
                if _cible(cwd, a).is_dir():
                    return t("hist.indice.rmdir", nom=a.rstrip("/\\"))
        if cmd == "rmdir" and step["cmd"].startswith("rm -r"):
            for a in args:
                p = _cible(cwd, a)
                if p.is_dir() and any(p.iterdir()):
                    return t("hist.indice.plein", nom=a.rstrip("/\\"), cmd=step["cmd"])
    return None


def _indice_chemin(step, tapees):
    """Le fichier de l'étape n'est pas arrivé au bon endroit DANS le terrain (sinon lecons.indice dit d'y aller) :
    c'est devenu un dossier (mkdir nid/lit.txt), ou la commande a été tapée sans son chemin (touch lit.txt dans la
    grande salle), ou depuis une autre pièce (touch nid/lit.txt dans le nid)."""
    rel = lecons.CREE.get(step.get("fs"))
    if not rel or "/" not in rel or rel.replace("/", S) not in step["cmd"] or lecons.FS[step["fs"]]():
        return None
    p = T() / rel
    if p.is_dir():
        return t("hist.indice.dossier", nom=p.name, rel=rel.replace("/", S), cmd=step["cmd"])
    premier = step["cmd"].split()[0].lower()
    for l, cwd in tapees:
        if not l.split() or l.split()[0].lower() != premier:
            continue
        r = maison.rel(cwd)
        if r is None:
            continue
        if r == "":
            return t("hist.indice.chemin", cmd=step["cmd"])
        return t("hist.indice.depuis", terrain=f"cd ~/{T().name}", cmd=step["cmd"])
    return None


# ---------------------------------------------------------------- attirance du chapitre
def famille_attiree(state):
    """La famille du chapitre en cours, si sa commande a déjà été goûtée (sinon le serveur refuserait)."""
    from . import bestiaire as B
    c = chapitre_courant(state)
    fam = c.get("famille") if c else None
    if fam and B.familles().get(fam) in state.get("seen", []):
        return fam
    return None


# ---------------------------------------------------------------- le carnet d'aventure
def noter(state):
    """Chaque nouvelle commande goûtée est rangée avec le moment de l'histoire où on l'a apprise."""
    h = h_(state)
    c = chapitre_courant(state)
    ou = c["id"] if c else ("libre" if fini(state, "nid") else "reveil")
    for cmd in state.get("seen", []):
        if cmd not in h["carnet"]:
            h["carnet"][cmd] = ou


# ---------------------------------------------------------------- migration des anciennes sauvegardes
COUVRE = {"reseau0": ["tour0"], "systeme0": ["dortoir0"], "reseau2": ["tour2"], "scripts2": []}
PREFIXE = {"Réseau": "reseau", "Git": "git", "Scripts": "scripts", "Système": "systeme", "Android": "android"}


def migrer(state):
    """Range la progression d'avant (tronc commun + arbre) dans les chapitres, sans rien perdre."""
    if isinstance(state.get("histoire"), dict):
        return state
    h = {"v": 2, "chap": "reveil", "faits": [], "ailes": [], "pas": {}, "ouverts": [], "annonce": None,
         "carnet": {}, "meubles": [], "suggere": []}
    L, s = state.get("lesson", 0), state.get("step", 0)
    faits, pas = [], {}

    def fait(*ids):
        for x in ids:
            if x not in faits:
                faits.append(x)
    if L >= 1:
        fait("t0")
    if L >= 2:
        fait("reveil1", "nid0", "debarras")
    if L >= 3:
        fait("nid1")
    if L >= 4:
        fait("t3")
    if L >= 5:
        fait("t4")
    courant = None
    if L == 0:
        pas["t0"] = s
    elif L == 2:
        if s <= 1:
            pas["nid1"] = s
        else:
            fait("nid1")                                    # le grep est la 1re étape de biblio1
            pas["biblio1"] = 0
    elif L == 3:
        pas["t3"], courant = s, "cave"
    elif L == 4:
        pas["t4"], courant = s, "grenier"
    for b, n in (state.get("arbre") or {}).items():
        pre = PREFIXE.get(b)
        if not pre:
            continue
        for i in range(n):
            lid = f"{pre}{i}"
            fait(*COUVRE.get(lid, [lid]))
    b = state.get("branche")
    if b in PREFIXE and L >= 5:
        lid = f"{PREFIXE[b]}{(state.get('arbre') or {}).get(b, 0)}"
        if s and lid in ("reseau0",):
            pas["tour0"] = s + 1
        elif s and lid == "reseau2":
            pas["tour2"] = min(s, 1)
        elif s and lid in lecons.PAR_ID and lid not in COUVRE:
            pas[lid] = s
        c = chapitre_de_lecon(COUVRE.get(lid, [lid])[0] if COUVRE.get(lid) else lid)
        courant = c["id"] if c else courant
    h["faits"], h["pas"] = faits, pas
    state["histoire"] = h
    for c in CHAPITRES:
        if all(x in faits for x in c["lecons"]):
            h["ailes"].append(c["id"])
    if not fini(state, "reveil"):
        h["chap"] = "reveil"
    elif not fini(state, "nid"):
        h["chap"] = "nid"
    else:
        h["chap"] = courant if courant and not fini(state, courant) else None
    h["ouverts"] = [c for c in h["ailes"]]
    lid = lecon_id(state)
    state["step"] = pas.pop(lid, 0) if lid else 0
    if L >= 2:
        state.setdefault("maison", {"visites": ["", "nid"], "cwd": None, "sauvage": [], "averti": 0, "prudence": 0})
    for cmd in state.get("seen", []):
        h["carnet"][cmd] = "avant"
    state["annonce"] = None
    return state


# ---------------------------------------------------------------- à chaque étape de jeu
def tick(state, lines, cwd=None):
    h_(state)
    cwds = maison.suivre(state, lines, cwd)
    meubler(state)
    _visite_aile(state, cwds + [maison.ici(state)])
    tick_lecon(state, lines, cwds)
    meubler(state)
    from . import quetes
    quetes.tick(state, lines, cwds)
    noter(state)


# ---------------------------------------------------------------- écrans
def lignes_ailes(state):
    """Le menu des chapitres (touche [a], tg aile)."""
    from .plateforme import BOLD, DIM, RESET, fg
    out = [f" {fg(213)}── 🏚 " + t("hist.menu.titre") + f" ──{RESET}", ""]
    for c in CHAPITRES:
        if not chapitre_dispo(c):
            continue
        cid = c["id"]
        if fini(state, cid):
            etat = f"{fg(78)}✓ " + t("hist.menu.reveillee") + RESET
        elif h_(state).get("chap") == cid:
            etat = f"{fg(213)}▶ " + t("hist.menu.en_cours") + RESET
        elif ouvert(state, cid):
            etat = f"{fg(226)}" + t("hist.menu.libre") + RESET
        elif cid == "coeur":
            etat = DIM + t("hist.coeur.ferme", n=nb_ailes(state), total=AILES_POUR_LE_COEUR) + RESET
        else:
            etat = DIM + t("hist.menu.fermee") + RESET
        faits = sum(1 for x in c["lecons"] if x in h_(state)["faits"])
        num = f"{c['n']:>2}" if c["n"] else " +"
        out.append(f" {BOLD}{num}. {maison.ICONES.get(c['piece'], '')} {nom_chapitre(cid)}{RESET} "
                   f"{DIM}({faits}/{len(c['lecons'])} · {c['piece']}/){RESET}  {etat}")
    out.append("")
    out.append(f" {DIM}" + t("hist.menu.aide") + RESET)
    return out


def bandeau(state):
    """Ce que l'écran principal montre quand il n'y a pas de leçon : (titre, texte) ou None."""
    if chapitre_courant(state):
        return None
    if fini(state, "coeur"):
        return t("hist.fin.titre"), t("hist.fin.suite")
    if fini(state, "nid"):
        libres = [nom_chapitre(c) for c in AILES if not fini(state, c)]
        if ouvert(state, "coeur") and not fini(state, "coeur"):
            libres.append(nom_chapitre("coeur"))
        return t("hist.choisir.titre"), t("hist.choisir.aide", n=nb_ailes(state))
    return None
