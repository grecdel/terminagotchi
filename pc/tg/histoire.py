"""« L'éveil du Terminaworld » (titre provisoire, une seule clé : lex.ch.maison) : le fil conducteur du
Terminagotchi (PC), en 10 chapitres. Ancien nom : « La Maison endormie ».

Le monde à explorer : terrain_terminagotchi = le Terminaworld (sa racine = le carrefour), ~ = le camp de base,
dossier = un lieu, fichier = un objet, texte = un parchemin, dossier caché = un passage secret, tree = la carte du
monde. Les lieux gardent les vieux noms écrits sur leurs panneaux (les vrais dossiers ne changent pas, aucune
sauvegarde n'est cassée) : vestibule (l'entrée du monde), grenier (une forêt), cave (une caverne), bibliotheque
(engloutie dans le lagon), salle_des_machines (au pied du volcan), dortoir (un vallon de brume), tour (dans les
nuages), coeur (le cœur du monde). L'enfant trouve un œuf à l'entrée du monde endormi : l'ordinateur. Les monstres
de 10 familles se sont installés chacun dans un lieu. Avec sa créature, il réveille le monde lieu par lieu.
Chaque chapitre a un vrai problème à résoudre ; les commandes sont les outils pour le résoudre.

Le Terminaworld, c'est TOUT l'ordinateur (docs/programme.md § 2.0 bis) : la Racine /, le village /home, ton camp
de base ~, la zone d'aventure ~/terrain_terminagotchi (le seul lieu où l'on bâtit et casse) et les lieux du système
(/etc, /bin, /tmp, /var/log, /dev, /proc), visités en lecture seule. Deux leçons y emmènent : « Voyage jusqu'à la
Racine » (fin du chapitre 1 : cd /, ls, pwd, cd ~, chemin absolu / relatif) et « Les lieux du gardien » (fin du
chapitre 4, niveau 6 du programme « cadenas » : /etc, /bin, /var/log, ls -l : regarder, pas toucher).
Chaque étape a sa version « pour les grands » (clé <étape>.adulte, G-32), affichée juste sous la commande.

   1 reveil        Le réveil                 pwd, ls, cd, puis cd / (on trouve l'œuf, puis le voyage jusqu'à la Racine)
   2 nid           Le nid                    mkdir, touch, >, cat, ls -a (un nid, un repas, un passage secret)
   3 grenier       La forêt du Grenier       tree, mv, cp, rm         (des lianes ont tout mélangé)
   4 cave          La caverne des Démons     whoami, sudo -h, chmod, puis les lieux du gardien (/etc, /bin, /var/log)
   5 bibliotheque  La bibliothèque engloutie find, less, grep, head, wc (un livre a disparu)
   6 machines      La salle des machines du volcan  free, du, df, rm  (le monde étouffe)
   7 dortoir       Le dortoir des brumes     ps, &, jobs, kill        (des fantômes refusent de dormir)
   8 atelier       L'atelier des Constructs  scripts, chmod +x, alias, git
   9 tour          La tour des nuages        ping, ip, curl, nslookup, ssh -V
  10 coeur         Le cœur du monde          rev, ls -a, find, cat >, grep | wc, puis Abyssor
  (+ telephone : le jardin du téléphone, seulement dans Termux, hors compte)

Liberté : après le chapitre 2, les ailes 3 à 9 se réveillent dans l'ordre qu'on veut. On choisit
une aile en y entrant (cd grenier) ou avec le menu [a] / tg aile <nom>. On peut changer d'aile en
cours de route : l'étape atteinte est gardée (« pas »). Le chapitre 10 s'ouvre quand au moins
5 ailes sont réveillées. La difficulté s'adapte : le niveau demandé suit le nombre d'ailes déjà
réveillées (sans jamais dépasser le niveau donné par les leçons déjà faites : pas de remplissage, voir
niveau_requis), et les étapes « expert » n'apparaissent qu'à partir du niveau 10.

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
# la Racine et le camp de base (pour les étapes « ici_abs » / « ou_abs » : un lieu hors de la zone d'aventure)
from pathlib import Path as _Path  # noqa: E402
RACINE = str(_Path(_Path.home().anchor or "/"))
CAMP = str(_Path.home())


def _q(chemin):
    """Un chemin prêt à taper (entre guillemets s'il contient une espace : C:\\Users\\Jean Dupont…)."""
    return f'"{chemin}"' if " " in chemin else chemin


VESTIBULE_ABS = _q(str(_Path.home() / "terrain_terminagotchi" / "vestibule"))

# ---------------------------------------------------------------- les leçons de l'histoire
NOUVELLES = {
    "reveil1": {"titre": "hist.reveil1.titre", "skill": None, "steps": [
        _n("reveil1", 0, cmd="cd terrain_terminagotchi", ici=""),
        _n("reveil1", 1, cmd=C("ls", "dir"), re=LS, ou=""),
        _n("reveil1", 2, cmd="cd vestibule", ici="vestibule"),
        _n("reveil1", 3, cmd=C("ls", "dir"), re=LS, ou="vestibule"),
    ]},
    # « Voyage jusqu'à la Racine » (G-33, niveau 1 du programme) : le Terminaworld est tout l'ordinateur. On va à la
    # Racine, on regarde, on lit le panneau, on rentre au camp, puis on retourne au vestibule par un chemin absolu.
    "racine": {"titre": "hist.racine.titre", "skill": None, "steps": [
        _n("racine", 0, cmd="cd /", ici_abs=RACINE),
        _n("racine", 1, cmd=C("ls", "dir"), re=LS, ou_abs=RACINE),
        _n("racine", 2, cmd="pwd", re=r"^(pwd|get-location|gl)\b", ou_abs=RACINE),
        _n("racine", 3, cmd="cd ~", ici_abs=CAMP, dit=("hist.racine.3.dit", {"chemin": CAMP}),
           bravo=("hist.racine.3.bravo", {"chemin": CAMP})),
        _n("racine", 4, cmd=f"cd {VESTIBULE_ABS}", ici="vestibule"),
    ]},
    "nid0": {"titre": "lec.t1.titre", "skill": "Bâtisseur", "steps": [
        # « depuis » : le lieu d'où `cd ..` mène au carrefour (C1 : depuis le camp, `cd ..` mène au village, pas ici)
        _n("nid0", 0, cmd="cd ..", ici="", exact=True, depuis="vestibule"),
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
    # mini-leçon « pont » (G-05) : les passages secrets (ls -a) juste avant l'ouverture de l'exploration, dont les
    # cachettes, les quêtes et les épreuves de dressage en ont besoin (la version des grands : hist.secrets.<i>.adulte).
    "secrets": {"titre": "hist.secrets.titre", "skill": None, "steps": [
        _n("secrets", 0, cmd=C("ls -a", "dir -Force"), re=lecons.LS_A, ou=""),
        _n("secrets", 1, cmd=C("cat .mot_secret.txt", "type .mot_secret.txt"), re=LIRE + r".*\.mot_secret", ou=""),
    ]},
    "grenier0": {"titre": "hist.grenier0.titre", "skill": "Explorateur", "steps": [
        _entree("grenier"),
        _n("grenier0", 1, cmd=C("tree", "tree /f"), re=r"^(tree|ls(\s+-\w+)*\s+-\w*R)\b", repli=["ls -R"],
           astuce=C("hist.grenier0.1.astuce2", None)),
        _n("grenier0", 2, cmd=C(f"mv fouillis{S}ours_en_peluche.txt ..{S}nid{S}",
                                f"move fouillis{S}ours_en_peluche.txt ..{S}nid{S}"), fs="ours"),
    ]},
    "cave0": {"titre": "hist.cave0.titre", "skill": None, "steps": [
        _entree("cave"),
        _ref("systeme0", 0),
        _n("cave0", 2, cmd="sudo -h", absent_ok=True, re=r"^sudo\s+(-h|--help|-V|--version)(\s|$)", astuce="hist.cave0.2.astuce", win=False),
    ]},
    # « Les lieux du gardien » (G-33, niveau 6 du programme « cadenas ») : la salle des règles, l'armurerie et les
    # archives, en lecture seule ; ls -l montre que seul root (le gardien) peut y écrire. Rien n'est écrit hors de la
    # zone d'aventure, sudo n'est jamais utilisé.
    "gardien": {"titre": "hist.gardien.titre", "skill": None, "steps": [
        _n("gardien", 0, cmd=C("cat /etc/hostname", "hostname"),
           re=r"^((cat|less|more|head|tail|type|gc|get-content)\b.*[\\/]etc[\\/]hostname|hostname\b)"),
        _n("gardien", 1, cmd=C("ls /bin", "dir C:\\Windows\\System32"),
           re=r"^(ls|dir|gci|get-childitem)\b.*([\\/](usr[\\/])?s?bin\b|system32)"),
        _n("gardien", 2, cmd=C("ls /var/log", "dir C:\\Windows\\Logs"),
           re=r"^(ls|dir|gci|get-childitem)\b.*([\\/]var[\\/]log|windows[\\/]logs)"),
        _n("gardien", 3, cmd="ls -l /etc/hostname", re=lecons.LS_L + r".*[\\/]etc[\\/]", win=False),
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
        _n("biblio1", 4, cmd=C(f"cat etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt | grep Abyssor",
                               f"Get-Content etagere_c{S}coin_poussiereux{S}livre_des_abysses.txt | Select-String Abyssor"),
           re=r"\|\s*(grep|select-string|sls|findstr)\b.*abyssor"),             # le premier vrai tuyau
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
        _n("tour2", 1, cmd="ssh -V", re=r"^ssh\s+-V\b", absent_ok=True),
        dict(_ref("reseau2", 1), expert=True),
    ]},
    "coeur0": {"titre": "hist.coeur0.titre", "skill": None, "steps": [
        _entree("coeur"),
        _n("coeur0", 1, cmd="rev message_brouille.txt", re=r"(^|\s)rev\b.*message", win=False,
           astuce="hist.coeur0.1.astuce"),
        _n("coeur0", 2, cmd=C("ls -a", "dir -Force"), re=lecons.LS_A, ou="coeur"),
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
    {"id": "reveil", "n": 1, "piece": "vestibule", "famille": None, "lecons": ["t0", "reveil1", "racine"], "niveaux": [2, 2, 2],
     "objet": "veilleuse"},
    {"id": "nid", "n": 2, "piece": "nid", "famille": None, "lecons": ["nid0", "debarras", "nid1", "secrets"],
     "niveaux": [3, 3, 4, 4],
     "objet": "coussin"},
    {"id": "grenier", "n": 3, "piece": "grenier", "famille": "Sylvestres", "lecons": ["grenier0", "t4"],
     "objet": "plante", "titre": "jardinier"},
    {"id": "cave", "n": 4, "piece": "cave", "famille": "Démons", "lecons": ["cave0", "t3", "gardien"],
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
# phase 5 : les mondes du Carrefour (docs/programme.md § 2.9, § 7.14), un par un. Le premier : le Port (port.py).
from . import port as _port  # noqa: E402
NOUVELLES.update(_port.LECONS)
CHAPITRES.append(_port.CHAPITRE)
lecons.FS.update(_port.FS)
lecons.CREE.update(_port.CREE)
MONDES = tuple(c["piece"] for c in CHAPITRES if c.get("monde"))
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
    if h["v"] < 3:
        _version_v3(state, h)
    if h["v"] < 4:
        _version_v4(state, h)
    return h


def _version_v4(state, h):
    """Sauvegarde v3 → v4 : « Voyage jusqu'à la Racine » finit le chapitre 1, « Les lieux du gardien » le chapitre 4.
    Un chapitre déjà fini les compte comme faites ; une partie en plein chapitre les fera à la fin."""
    h["v"] = 4
    for chap, lid in (("reveil", "racine"), ("cave", "gardien")):
        if chap in h["ailes"] and lid not in h["faits"]:
            h["faits"].append(lid)


def _version_v3(state, h):
    """Sauvegarde v2 → v3 : la mini-leçon « passages secrets » (secrets) finit le chapitre 2. Un chapitre 2 déjà fini
    la compte comme faite (l'exploration est déjà ouverte) ; une partie en plein chapitre 2 la fera à la fin."""
    h["v"] = 3
    if "nid" in h["ailes"] and "secrets" not in h["faits"]:
        h["faits"].append("secrets")


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
    if c.get("monde"):                      # un monde du Carrefour : ses prérequis du tronc commun (programme.json)
        return _port.ouvert(state)
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


XP_LECON_SURE = 20      # XP qu'une leçon finie a donnée au moins (20 à la fin, + 5 par étape avant la dernière)
XP_CHAPITRE_SUR = 30    # XP d'un chapitre fini


def xp_appris(state):
    """L'XP que l'apprentissage seul a forcément donnée : leçons et chapitres finis (jamais la répétition)."""
    h = h_(state)
    return XP_LECON_SURE * len(h["faits"]) + XP_CHAPITRE_SUR * len(h["ailes"])


def niveau_requis(state, c, i):
    """Le niveau demandé pour voir la leçon. G-04 : il ne dépasse jamais le niveau que les leçons et chapitres déjà
    finis ont donné ; un enfant qui suit le parcours n'a donc jamais à « remplir » (seul l'œuf du réveil attend
    ses premières commandes)."""
    if c.get("niveaux"):
        n = c["niveaux"][min(i, len(c["niveaux"]) - 1)]
    else:   # les ailes : la difficulté suit le nombre d'ailes déjà réveillées (ordre libre)
        n = min(12, 5 + nb_ailes(state) + i)
    if c["id"] == "reveil":
        return n
    from . import satiete                  # une évolution qui attend des jours soignés ne bloque jamais une leçon
    return max(1, min(n, core.level(xp_appris(state)), satiete.plafond(state)))


def _repli(s):
    """Un outil absent de cet ordinateur (tree…) : l'étape montre sa commande de repli installée (ls -R)."""
    if not s.get("repli"):
        return s
    from . import verif
    for c in [s["cmd"]] + list(s["repli"]):
        if verif.commande_installee(c.split()[0]):
            return s if c == s["cmd"] else dict(s, cmd=c)
    return s


def etapes(state, lid):
    niv = core.level(state.get("xp", 0))
    return [_repli(s) for s in lecon_def(lid)["steps"]
            if (not s.get("expert") or niv >= NIVEAU_EXPERT) and not (IS_WIN and s.get("win") is False)
            and not (s.get("outil") and not _outil(s["outil"]))]


def _outil(nom):
    """Un outil dont une étape a besoin (openssl, ssh-keygen) : sans lui, l'étape n'est pas montrée (le monde continue)."""
    import shutil
    return shutil.which(nom) is not None


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
                "vieille_cabane/planche_2.txt": dire(state, "hist.meuble.planche"),
                ".mot_secret.txt": dire(state, "hist.meuble.mot_secret", nom=state.get("name", ""))}
    if p == "port":
        return _port.meubles(state)
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
    "secrets": [(".mot_secret.txt", None)],
    "grenier0": [("grenier/fouillis/ours_en_peluche.txt", 2)],
    "biblio0": [("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt", None)],
    "biblio1": [("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt", None)],
    "machines0": [("salle_des_machines/vieux_carton.bin", 3)],
    "atelier0": [("atelier/plan_de_travail.txt", None)],
    "coeur0": [("coeur/message_brouille.txt", None), ("coeur/.porte_secrete/abyssor_dort.txt", None)],
    "coeur1": [(f, 1) for f in FRAGMENTS],
    "coeur2": [("coeur/.porte_secrete/abyssor_dort.txt", None)],
    "port0": [("port/panneau.txt", None)],
    "port2": [("port/annuaire.txt", None)],
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
    for p in maison.PIECES + ("jardin",) + MONDES:
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
    if lid and lid in _port.LECONS:              # le Port : le phare s'allume pour les leçons qui le visitent
        _port.meubler(state, lid, state.get("step", 0))
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
        if c.get("monde"):
            return t("port.ferme", chapitre=nom_chapitre(cid), manque=", ".join(_port.manque(state)))
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
    _port.annonce(state)                         # un monde du Carrefour qui vient de s'ouvrir
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
    state["pas_t"] = __import__("time").time()          # P2-3 : les monstres et les nouveautés attendent ce moment
    core.log(state, f"✔ {step['cmd']}")
    core.say(state, lecons.tx(step["bravo"]), 12)
    core.terminal(state, "✔ " + lecons.tx(step["bravo"]))   # le bravo aussi dans le terminal de l'enfant (P1-4)
    from . import explique
    explique.apres_reussite(state, step["cmd"])           # -r, >>, 444… : expliqués une fois (explique.py)
    if step.get("exploit"):                               # un exploit d'un monde (§ 7.6) : des rencontres rares
        from . import recompenses
        msg = recompenses.exploit(state, step["exploit"])
        if msg:
            core.log(state, msg)
            core.say(state, msg, 16)
    state["step"] += 1
    core.animer(state, "content")
    from . import satiete
    if state["step"] < len(les["steps"]):
        satiete.gagner_xp(state, 5, lecon=True)          # +20 % si elle est rassasiée (jamais moins : leçon)
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
    from . import satiete
    satiete.gagner_xp(state, 20, lecon=True)
    state["annonce"] = None
    if all(x in h["faits"] for x in c["lecons"]):
        _finir_chapitre(state, c)
    else:
        nouv = lecon_id(state)
        state["step"] = h["pas"].pop(nouv, 0) if nouv else 0


def _abs_ok(cwd, lieu):
    return bool(cwd) and os.path.normcase(os.path.normpath(str(cwd))) == os.path.normcase(os.path.normpath(lieu))


def _ou_ok(step, cwd):
    """La commande est tapée au bon endroit : « ou » (un lieu de la zone d'aventure) ou « ou_abs » (un chemin absolu)."""
    if "ou_abs" in step:
        return _abs_ok(cwd, step["ou_abs"])
    return "ou" not in step or maison.dans(cwd, step["ou"])


def _ici_ok(step, cwd):
    if "ici_abs" in step:
        return _abs_ok(cwd, step["ici_abs"])
    if "ici" not in step or not cwd:
        return False
    if step.get("exact"):
        return maison.rel(cwd) == step["ici"]
    return maison.dans(cwd, step["ici"])


def tick_lecon(state, lines, cwds, avants=None):
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
            core.log(state, t("hist.monde.log" if PAR_CHAP[les["chap"]].get("monde") else "hist.chapitre.log",
                              n=PAR_CHAP[les["chap"]]["n"], chapitre=nom_chapitre(les["chap"])))
            core.say(state, dire(state, f"hist.{les['chap']}.debut"), 18)
        else:
            core.say(state, t("lec.annonce"), 10)
        core.animer(state, "parle")
    # G-34 : chaque morceau de ligne (`cd / && ls`) est jugé sur son RÉSULTAT (code de sortie, chemins qui existent
    # depuis le dossier où il a été tapé, commande installée et écrite en minuscules), pas seulement sur son texte
    from . import verif
    avants = list(avants) if avants else [None] * len(lines)
    morcs = []
    for k, (line, cwd) in enumerate(zip(lines, cwds)):
        if est_colle(line):
            continue
        morcs += verif.morceaux(line, avants[k] or cwd, core.statut_de(lines, k))
    tapees = [(m.texte, m.avant) for m in morcs]
    from . import placement
    if placement.actif(state):                  # G-13 : le test « je connais déjà » passe avant la leçon
        placement.tick(state, morcs)
        return
    avant = (les["id"], state["step"])
    for m in morcs:
        step = les["steps"][state["step"]]
        ok = verif.motif_ok(step, m.texte, m.avant) and verif.resultat_ok(step, m) and _ou_ok(step, m.avant)
        if ok or (_ici_ok(step, m.apres) and m.statut in (None, 0)):
            absent = [w for w in (verif.premier(x) for x, _ in verif._couper(m.texte, ("|",)))
                      if w and not verif.commande_installee(w)]
            if ok and absent:                        # l'outil n'est pas là : on le dit au lieu d'un simple bravo
                core.say(state, t("lec.indice.absent", cmd=absent[0]), 12)
                core.terminal(state, t("lec.indice.absent", cmd=absent[0]))
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
        conseil = placement.masquer(state, step, indice(state, step, [l for l, _ in tapees], tapees, morcs))
        placement.rate_une_fois(state, step)          # mode sans aide : 3 essais ratés montrent la commande
        if conseil and conseil != state.get("indice_lecon"):
            state["indice_lecon"] = conseil
            core.say(state, "💡 " + conseil, 12)
        if conseil:
            core.terminal(state, "💡 " + conseil)            # aussi dans le terminal de l'enfant (compagnon)


def en_pleine_etape(state):
    """Une étape de leçon est montrée et l'enfant y travaille (elle ne vient pas d'être réussie) : un monstre, un défi
    éclair ou un écran « Nouveau » attendent la fin de l'étape au lieu de cacher la leçon (P2-3, P2-6)."""
    import time
    try:
        les, _ = lecon_courante(state)
    except Exception:                       # noqa: BLE001
        return False
    if not les or core.level(state.get("xp", 0)) < les["niveau"]:
        return False
    return time.time() - state.get("pas_t", 0) > 2


def aide_lecon(state, cwd=None, tel=False):
    """`aide` quand on est coincé (P2-7) : la leçon en cours, l'étape, où la taper (comparé au dossier où l'enfant est),
    la commande exacte (avec le cd qui y mène), pourquoi, et le dernier indice."""
    from . import compagnon, verif
    out = [t("aide.lecon.titre")]
    les, etiquette = lecon_courante(state)
    from . import intro
    if intro.en_cours(state):                   # I1 : pendant l'œuf, la prochaine commande de sa liste
        p = intro.prochaine(state)
        out.append("🥚 " + t("intro.liste.titre", n=len(intro.i_(state)["faits"]), total=len(intro.checklist())))
        if p:
            out.append(t("aide.lecon.tape", cmd=f"`{intro.commande_de(p)}`"))
    elif not les or core.level(state.get("xp", 0)) < les["niveau"]:
        out.append(t("aide.lecon.aucune"))
    else:
        step = les["steps"][state["step"]]
        out.append(t("aide.lecon.etape", titre=lecons.tx(les["titre"]), n=state["step"] + 1, total=len(les["steps"])))
        out.append(t("aide.lecon.pourquoi", dit=lecons.tx(step["dit"])))
        ici = cwd or maison.ici(state)
        r = maison.rel(ici) if ici else None
        la = nom_lieu(r) if r is not None else (str(ici).replace(str(_Path.home()), "~", 1) if ici else "?")
        lieu = verif.lieu_attendu(state, step)
        if lieu is not None and not verif.au_bon_endroit(state, step, ici):
            out.append(t("aide.lecon.ou", ici=la, lieu=nom_lieu(lieu)))
        else:
            out.append(t("aide.lecon.ok_ici", ici=la))
        from . import placement
        placement.montrer(state, step)          # mode sans aide : `aide` montre la commande
        out.append(t("aide.lecon.tape", cmd=compagnon.commande_montree(state, step, ici)))
        if state.get("indice_lecon"):
            out.append("💡 " + state["indice_lecon"])
    out.append(t("aide.lecon.tout"))
    return out


def nom_lieu(rel):
    """Le nom d'un lieu de la zone d'aventure pour un enfant (« » = le carrefour)."""
    return maison.nom_piece(rel.split("/")[0] if rel else "grande_salle")


def _indice_resultat(state, step, morcs):
    """La commande de l'étape a été tapée, mais elle n'a pas marché : dire POURQUOI (majuscules, outil absent, nom mal
    écrit, pas au bon endroit) avec la commande qui marche d'où l'enfant est."""
    from . import verif
    for m in morcs:
        meme = "re" not in step and verif.premier(m.texte) == verif.premier(step["cmd"])   # étape « fichier »
        if not meme and not verif.motif_ok(step, m.texte, m.avant):
            bas = verif.premier(m.texte)
            if bas and bas != bas.lower() and not IS_WIN and verif.motif_ok(step, m.texte.replace(bas, bas.lower(), 1),
                                                                             m.avant):
                return t("lec.indice.minuscules", cmd=step["cmd"], tape=bas)
            continue
        if not meme and verif.resultat_ok(step, m) and _ou_ok(step, m.avant):
            continue
        for x, _ in verif._couper(m.texte, ("|",)):
            mot = verif.premier(x)
            if mot and not verif.commande_installee(mot) and verif.ponctuation(mot):     # I9 : `pwd,`
                return t("core.inconnue.proche", cmd=mot, proche=verif.ponctuation(mot))
            if mot and not verif.commande_installee(mot):
                return t("lec.indice.absent", cmd=mot) + (" " + lecons.tx(step["astuce"]) if step.get("astuce") else "")
        manque = verif.chemins_manquants(m.texte, m.avant)
        if manque:
            p = manque[0]
            if verif.barre_oubliee(p, m.avant):                            # I9 : nidrepas.txt → nid/repas.txt
                return t("lec.indice.barre", tape=p, proche=verif.barre_oubliee(p, m.avant))
            proche = verif.nom_proche(p, m.avant)
            if proche:
                return t("lec.indice.casse" if proche[1] else "lec.indice.nom", tape=p, proche=proche[0])
            lieu = verif.lieu_attendu(state, step)
            if lieu is not None and maison.rel(m.avant) != lieu:
                return t("lec.indice.lieu", lieu=nom_lieu(lieu), cmd=verif.cd_vers(lieu), etape=step["cmd"])
            return t("lec.indice.manque", nom=p)
        if m.statut == 1 and not meme and grep_rien(m.texte):
            return grep_rien(m.texte)
        if m.statut and not meme:
            return t("lec.indice.rate", cmd=step["cmd"])
    return None


def grep_rien(texte):
    """C3 : grep n'a trouvé aucune ligne (code 1) : le dire, et comment regarder le fichier (au lieu de « une erreur »)."""
    from . import verif
    parts = [p for p, _ in verif._couper(texte, ("|",))]
    k = next((i for i, p in enumerate(parts) if verif.premier(p) == "grep"), None)
    if k is None or any(w.startswith("-") and ("r" in w or "R" in w) for w, _c in verif.mots(parts[k])):
        return None
    args = [w for w, _c in verif.mots(parts[k])[1:] if not w.startswith("-")]
    if not args:
        return None
    fichier = args[1] if len(args) > 1 else next((w for w, _c in verif.mots(parts[k - 1])[1:] if not w.startswith("-")),
                                                  None) if k > 0 else None
    ok = fichier and fichier not in (".", "..") and not fichier.endswith(("/", "\\"))
    return t("lec.indice.grep_rien", mot=args[0], cmd=f"cat {fichier}") if ok else None


def _indice_cd(state, step, morcs):
    """Une étape « va à … » : `cd -` (le lieu d'avant), un lieu qui n'est pas là où l'enfant est, une faute."""
    from . import verif
    for m in morcs:
        g = re.match(r"^(cd|pushd)\s+(.+)$", m.texte.strip())
        if not g:
            continue
        arg = g.group(2).strip().strip("'\"")
        if arg == "-":
            return t("lec.indice.cd_moins", cmd=step["cmd"])
        if "ici" not in step and "ici_abs" not in step:
            continue
        if step.get("depuis") and not _ici_ok(step, m.apres) and not verif.au_bon_endroit(state, step, m.avant):
            # C1 : `cd ..` tapé ailleurs (le camp, la Racine) ne mène pas au carrefour : partir du bon lieu
            return t("lec.indice.lieu", lieu=nom_lieu(step["depuis"]), cmd=verif.cd_vers(step["depuis"]),
                     etape=step["cmd"])
        if m.apres == m.avant and arg not in (".", "") and not os.path.isdir(verif._abs(arg, m.avant)):
            proche = verif.nom_proche(arg, m.avant)
            if proche:
                return t("lec.indice.casse" if proche[1] else "lec.indice.nom", tape=arg, proche=proche[0])
            return t("lec.indice.cd_pas_ici", nom=arg, cmd=step["cmd"] if "ici" not in step or step["cmd"].startswith(
                ("cd ~", "cd /")) else verif.cd_vers(step["ici"]))
    return None


def _indice_variante(state, step, morcs):
    """Une commande juste, mais différente de celle de l'étape : la féliciter, et dire ce que l'étape voulait."""
    from . import verif
    import os.path as op
    cles = set()
    for w, _c in verif.mots(step["cmd"])[1:]:
        if w.startswith("-") or len(w) < 3:
            continue
        b = op.splitext(op.basename(w.rstrip("/")))[0].strip("*")
        if len(b) >= 3:
            cles.add(b.lower())
    for m in morcs:
        if m.statut != 0 or verif.motif_ok(step, m.texte, m.avant):
            continue
        tape = m.texte.lower()
        if verif.premier(m.texte).lower() == verif.premier(step["cmd"]).lower() or any(c in tape for c in cles):
            return t("lec.indice.variante", cmd=step["cmd"])
    return None


def indice(state, step, lignes, tapees, morcs=None):
    """Un indice quand c'est presque ça (mauvais endroit, faute de frappe, mauvais nombre…)."""
    morcs = morcs or []
    if step.get("fs") == "reponse" and (T() / "coeur" / "reponse.txt").is_file():
        return t("hist.indice.nombre")
    if "ou" in step and "re" in step:
        for l, cwd in tapees:
            if re.search(step["re"], l, re.I) and not maison.dans(cwd, step["ou"]):
                return t("hist.indice.piece", piece=maison.nom_piece(step["ou"]) if step["ou"] else
                         maison.nom_piece("grande_salle"), cmd=f"cd ~/{T().name}/{step['ou']}".rstrip("/"))
    if "ou_abs" in step and "re" in step:
        for l, cwd in tapees:
            if re.search(step["re"], l, re.I) and not _ou_ok(step, cwd):
                return t("hist.indice.racine", cmd="cd /")
    if "ici" in step or "ici_abs" in step:
        return _indice_cd(state, step, morcs)
    conseil = _port.indice(step, tapees)                  # le Port : un trou « … » recopié, un messager perdu
    if conseil:
        return conseil
    conseil = _indice_cd(state, step, morcs) or _indice_rm(step, tapees) or _indice_barre(step, morcs) \
        or _indice_resultat(state, step, morcs)
    if conseil:
        return conseil
    from . import dressage
    if not dressage.faute_de_frappe(lignes, step["cmd"], chiffres=True):
        conseil = _indice_chemin(step, tapees)
        if conseil:
            return conseil
    return lecons.indice(step, lignes, state) or _indice_variante(state, step, morcs)


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


def _indice_barre(step, morcs):
    """I9 : `touch nidlit.txt` quand l'étape veut `nid/lit.txt` : la barre / oubliée (le fichier collé est créé)."""
    from . import verif
    attendus = [w for w, _c in verif.mots(step.get("cmd") or "")[1:] if "/" in w]
    for m in morcs:
        for w, _c in verif.mots(m.texte)[1:]:
            for a in attendus:
                if "/" not in w and w == a.replace("/", "", 1) and a.split("/")[0] and \
                        os.path.isdir(os.path.join(m.avant or "", a.split("/")[0])):
                    return t("lec.indice.barre", tape=w, proche=a)
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
    h = {"v": 4, "chap": "reveil", "faits": [], "ailes": [], "pas": {}, "ouverts": [], "annonce": None,
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
    if "nid1" in faits:
        fait("secrets")                     # le tronc commun fini : l'exploration était déjà ouverte (v3)
    if "reveil1" in faits:
        fait("racine")                      # le chapitre 1 était fini (v4)
    if "t3" in faits and "cave0" in faits:
        fait("gardien")
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


# ---------------------------------------------------------------- filets : jamais de blocage technique
def _simple(nom):
    import unicodedata
    x = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", x) or "terminagotchi"


def signer_carnet(state):
    """G-07 : `git commit` refuse de travailler sans auteur (« Please tell me who you are », en anglais). Dès que le
    carnet (le dépôt de la leçon git) existe et qu'aucune identité n'est réglée, le jeu signe CE dépôt seulement
    (git config sans --global, rangé dans carnet/.git/config) au nom de la créature, et l'explique."""
    h = h_(state)
    depot = T() / "carnet"
    if h.get("git_signe") or not (depot / ".git").is_dir():
        return False
    import shutil
    import subprocess
    if not shutil.which("git"):
        return False
    from . import sur
    if not sur.depot_git_sur(depot):
        # le carnet est un lien vers un autre projet (ou son .git renvoie ailleurs) : on n'y touche jamais
        if sur.lien_genant(depot) and sur.lien_genant(depot) not in sur.ALERTES:
            sur.ALERTES.append(sur.lien_genant(depot))
        return False

    def cfg(*a):
        local = ["--local"] if len(a) > 1 else []        # écrire : seulement dans carnet/.git/config
        return subprocess.run(["git", "-C", str(depot), "config", *local, *a], capture_output=True, text=True,
                              timeout=10).stdout.strip()
    try:
        if cfg("user.name") and cfg("user.email"):
            h["git_signe"] = "deja"                     # une identité existe déjà (globale) : on n'y touche pas
            return False
        nom = state.get("name") or "Terminagotchi"
        cfg("user.name", nom)
        cfg("user.email", f"{_simple(nom)}@terminagotchi.invalid")
    except (OSError, subprocess.SubprocessError):
        return False
    h["git_signe"] = True
    core.log(state, t("hist.git.signe.log", nom=nom))
    core.say(state, dire(state, "hist.git.signe.dit", nom=nom), 14)
    core.say(state, t("hist.git.signe.adulte", nom=nom, email=f"{_simple(nom)}@terminagotchi.invalid"), 16)
    return True


def page_secours(titre, texte):
    """Une petite page web locale (le « colis » quand Internet ne répond pas)."""
    import html
    return ("<!doctype html>\n<html>\n<head><meta charset=\"utf-8\"><title>" + html.escape(titre) + "</title></head>\n"
            "<body>\n<h1>" + html.escape(titre) + "</h1>\n<p>" + html.escape(texte) + "</p>\n</body>\n</html>\n")


CURL_COLIS = r"^(curl(\.exe)?\b.*-o|wget\b.*-O)\s*\S*colis\.html"


def colis_hors_ligne(state, lines, cwds):
    """G-08 : `curl -o colis.html …` sans Internet (école, proxy, avion) ne pose aucun fichier, et l'étape attendait ce
    fichier pour toujours. La commande est dans l'historique, donc elle est finie : si le colis n'est arrivé ni dans
    le terrain ni là où elle a été tapée, le facteur en dépose un de secours (page locale) et la créature explique."""
    les, _ = lecon_courante(state)
    if not les or les["id"] != "reseau1" or core.level(state["xp"]) < les["niveau"]:
        return False
    step = les["steps"][state["step"]]
    if step.get("fs") != "colis" or lecons.FS["colis"]():
        return False
    from pathlib import Path
    for l, cwd in zip(lines, cwds):
        if est_colle(l) or not re.search(CURL_COLIS, l, re.I):
            continue
        if cwd and (Path(cwd) / "colis.html").is_file():
            return False                                # arrivé ailleurs : l'indice dit où le taper
        nom = state.get("name", "")
        # posé LÀ où la commande a été tapée (la tour…), pour que l'étape suivante (head -n 5 colis.html) y marche
        ici = maison.rel(cwd) if cwd else None
        rel = f"{ici}/colis.html" if ici else "colis.html"
        if not _ecrire(rel, page_secours(t("hist.colis.titre"), t("hist.colis.texte", nom=nom))):
            return False
        h_(state)["colis_secours"] = True
        core.log(state, t("hist.colis.log"))
        core.say(state, dire(state, "hist.colis.dit", nom=nom), 14)
        core.say(state, t("hist.colis.adulte"), 16)
        return True
    return False


# ---------------------------------------------------------------- à chaque étape de jeu
def tick(state, lines, cwd=None):
    h_(state)
    depart = maison.ici(state)
    cwds = maison.suivre(state, lines, cwd)
    # le dossier où chaque ligne a été tapée : celui d'après la ligne d'avant ; pour la dernière, si elle ne change
    # pas de dossier, celui que donne l'invite (le plus sûr)
    avants = ([depart] + cwds[:-1]) if cwds else []
    if lines and cwd and not re.search(r"(^|[;&|]\s*)(cd|pushd|set-location|sl)\b", lines[-1].strip(), re.I):
        avants[-1] = str(cwd)
    meubler(state)
    _visite_aile(state, cwds + [maison.ici(state)])
    signer_carnet(state)
    colis_hors_ligne(state, lines, cwds)
    _port.surveiller(state, lines)                # le Port : une lanterne ouverte à tout le réseau ? la créature prévient
    tick_lecon(state, lines, cwds, avants)
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
        elif c.get("monde"):
            etat = DIM + t("port.ferme.court", manque=", ".join(_port.manque(state))) + RESET
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
