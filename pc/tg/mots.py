"""Les mots du jeu : accords du français et vocabulaire qui grandit avec l'enfant.

1) accorder(modele, **valeurs) : remplit une phrase modèle (« Dressage de {nom} ») et fait
   l'élision quand le nom inséré commence par une voyelle (« Dressage d'Inodin »).
   Mots élidés : de, que, le, la, je, me, te, se, ne, ce, lorsque, puisque, jusque.
   Le genre des espèces n'est pas connu : les phrases modèles utilisent des tournures neutres
   (« Un monstre sauvage : {nom} ! », « {nom} rejoint ta troupe »).
   Chaque phrase reste ENTIÈRE dans le modèle : elle est traduite dans langues/xx.json
   (voir langue.py) ; l'élision n'est appliquée qu'en français.

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


def elider(modele, valeurs):
    """« de {nom} » → « d'{nom} » quand la valeur commence par une voyelle (le modèle n'est pas rempli)."""
    def elide(m):
        mot, cle = m.group(1), m.group(2)
        return mot[:-1] + "'{" + cle + "}" if voyelle(valeurs.get(cle)) else m.group(0)
    return _MOTIF.sub(elide, modele)


def accorder(modele, **valeurs):
    """« Dressage de {nom} » + nom=Inodin → « Dressage d'Inodin »."""
    return elider(modele, valeurs).format(**valeurs)


# ---------------------------------------------------------------- vocabulaire progressif
SEUIL_NIVEAU = (7, 12)       # niveau de la créature pour passer au palier 1, puis 2
SEUIL_LECONS = (8, 14)       # nombre de leçons terminées pour passer au palier 1, puis 2

# Les mots eux-mêmes sont dans les fichiers de langue (langues/xx.json), clés « terme.<clé> » :
# [image seule, image + vrai mot, vrai mot seul]. Exemple en français :
#   "terme.ram": ["la mémoire de la maison", "la mémoire de la maison (la RAM)", "la RAM"]


def _cles():
    from . import langue
    return [k[6:] for k in langue._charger(langue.DEFAUT) if k.startswith("terme.")]


def palier_de(niveau, lecons=0):
    p = 2 if niveau >= SEUIL_NIVEAU[1] else 1 if niveau >= SEUIL_NIVEAU[0] else 0
    q = 2 if lecons >= SEUIL_LECONS[1] else 1 if lecons >= SEUIL_LECONS[0] else 0
    return max(p, q)


def palier(state):
    """Le palier de vocabulaire d'une partie (niveau de la créature, leçons terminées)."""
    from . import core
    return palier_de(core.level(state.get("xp", 0)), len(state.get("skills", [])))


def terme(cle, p=0, majuscule=False):
    """Le mot à afficher pour ce palier (0, 1 ou 2), dans la langue courante."""
    from . import langue
    v = langue.brut("terme." + cle) or [cle] * 3
    t = v[max(0, min(2, p))]
    return t[0].upper() + t[1:] if majuscule and t else t


def termes(p=0):
    """Tous les termes d'un palier, pour remplir des modèles : « {ram} », « {Processeur} » (majuscule)…
    Attention au genre : « pièce » est féminin mais « dossier » masculin ; les modèles évitent
    donc les adjectifs accordés et utilisent les formes avec article (« {un_dossier} »)."""
    t = {k: terme(k, p) for k in _cles()}
    t.update({k[0].upper() + k[1:]: terme(k, p, majuscule=True) for k in _cles()})
    return t
