"""Les mots du jeu : accords du français et vocabulaire qui grandit avec l'enfant.

1) accorder(modele, **valeurs) : remplit une phrase modèle (« Dressage de {nom} ») et fait
   l'élision quand le nom inséré commence par une voyelle (« Dressage d'Inodin »).
   Mots élidés : de, que, le, la, je, me, te, se, ne, ce, lorsque, puisque, jusque.
   Le genre des espèces n'est pas connu : les phrases modèles utilisent des tournures neutres
   (« Un monstre sauvage : {nom} ! », « {nom} rejoint ta troupe »).
   Chaque phrase reste ENTIÈRE dans le modèle (prête à être traduite plus tard).

2) terme(cle, palier) : le jargon arrive progressivement.
   palier 0 = l'image seule          « la mémoire de la maison »
   palier 1 = l'image et le vrai mot « la mémoire de la maison (la RAM) »
   palier 2 = le vrai mot seul       « la RAM »
   palier_de(niveau, lecons) choisit le palier (mêmes seuils sur PC et Android) :
     - par le niveau de la créature : < 7 → 0, 7 à 11 → 1, 12 et plus → 2 ;
     - par les leçons terminées : 8 leçons (tronc commun + 3) → au moins 1, 14 → 2.
"""
import re

VOYELLES = "aàâäeéèêëiîïoôöuùûüœæ"
_ELIDABLES = ("de", "que", "le", "la", "je", "me", "te", "se", "ne", "ce", "lorsque", "puisque", "jusque")
_MOTIF = re.compile(r"\b(" + "|".join(_ELIDABLES) + r") \{(\w+)\}", re.I)


def voyelle(mot):
    """Vrai si le mot commence par une voyelle (on ne compte ni h ni y, souvent non élidés)."""
    mot = str(mot or "")
    return bool(mot) and mot[0].lower() in VOYELLES


def accorder(modele, **valeurs):
    """« Dressage de {nom} » + nom=Inodin → « Dressage d'Inodin »."""
    def elide(m):
        mot, cle = m.group(1), m.group(2)
        return mot[:-1] + "'{" + cle + "}" if voyelle(valeurs.get(cle)) else m.group(0)
    return _MOTIF.sub(elide, modele).format(**valeurs)


# ---------------------------------------------------------------- vocabulaire progressif
SEUIL_NIVEAU = (7, 12)       # niveau de la créature pour passer au palier 1, puis 2
SEUIL_LECONS = (8, 14)       # nombre de leçons terminées pour passer au palier 1, puis 2

# clé : (image seule, image + vrai mot, vrai mot seul)
TERMES = {
    "mefiance":     ("Peur", "Méfiance (il a peur de toi)", "Méfiance"),
    "pv":           ("cœurs", "cœurs (PV)", "PV"),
    "atk":          ("force", "force (ATK)", "ATK"),
    "def":          ("bouclier", "bouclier (DEF)", "DEF"),
    "vit":          ("vitesse", "vitesse (VIT)", "VIT"),
    "int":          ("astuce", "astuce (INT)", "INT"),
    "stats":        ("forces", "forces (stats)", "stats"),
    "ram":          ("la mémoire de la maison", "la mémoire de la maison (la RAM)", "la RAM"),
    "processeur":   ("le cerveau de la maison", "le cerveau de la maison (le processeur)", "le processeur"),
    "executable":   ("qui sait faire quelque chose", "qui sait faire quelque chose (exécutable)", "exécutable"),
    "ctf":          ("la chasse au trésor", "la chasse au trésor (CTF)", "le CTF"),
    "dossier":      ("pièce", "pièce (dossier)", "dossier"),
    "dossiers":     ("pièces", "pièces (dossiers)", "dossiers"),
    "fichier":      ("feuille", "feuille (fichier)", "fichier"),
    "fichiers":     ("feuilles", "feuilles (fichiers)", "fichiers"),
    "processus":    ("programme réveillé", "programme réveillé (processus)", "processus"),
    "disque":       ("les placards", "les placards (le disque)", "le disque"),
    "dns":          ("l'annuaire des maisons", "l'annuaire des maisons (DNS)", "le DNS"),
    "ip":           ("l'adresse de la maison", "l'adresse de la maison (adresse IP)", "l'adresse IP"),
    "arborescence": ("le plan de la maison", "le plan de la maison (l'arborescence)", "l'arborescence"),
    "terrain":      ("ta salle de jeu", "ta salle de jeu (terrain_terminagotchi)", "terrain_terminagotchi"),
}


def palier_de(niveau, lecons=0):
    p = 2 if niveau >= SEUIL_NIVEAU[1] else 1 if niveau >= SEUIL_NIVEAU[0] else 0
    q = 2 if lecons >= SEUIL_LECONS[1] else 1 if lecons >= SEUIL_LECONS[0] else 0
    return max(p, q)


def palier(state):
    """Le palier de vocabulaire d'une partie (niveau de la créature, leçons terminées)."""
    from . import core
    return palier_de(core.level(state.get("xp", 0)), len(state.get("skills", [])))


def terme(cle, p=0, majuscule=False):
    """Le mot à afficher pour ce palier (0, 1 ou 2)."""
    t = TERMES[cle][max(0, min(2, p))]
    return t[0].upper() + t[1:] if majuscule else t


def termes(p=0):
    """Tous les termes d'un palier, pour remplir des modèles : « {ram} », « {processeur} »…"""
    return {k: terme(k, p) for k in TERMES}
