"""Les 12 coloriages validés (au moins un par famille) et les réglages du contour choisis à l'œil pour chacun.
(id, stade, réglages de contour.contour, niveau affiché)"""
CHOIX = [
    ("braisillon", "bebe", dict(seuil=18, trait_min=10), "facile"),
    ("gouttelin", "enfant", dict(), "facile"),
    ("drapouille", "enfant", dict(seuil=32, trait_min=8, noir=True), "moyen"),
    ("felicorne", "enfant", dict(), "moyen"),
    ("glandouille", "enfant", dict(), "facile"),
    ("sporichon", "enfant", dict(seuil=28, pupille=36), "moyen"),
    ("pucerise", "enfant", dict(seuil=8), "facile"),
    ("clopinou", "enfant", dict(), "facile"),
    ("poulpiot", "enfant", dict(), "moyen"),
    ("rugisoleil", "enfant", dict(seuil=28), "un peu plus dur"),
    ("lanternix", "enfant", dict(seuil=40), "un peu plus dur"),
    ("gloupi", "enfant", dict(), "un peu plus dur"),
]
BASE = dict(haut=100, k=5, mini=50, seuil=22)
