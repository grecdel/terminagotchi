# À imprimer : coloriages, stickers, poster

Les fichiers prêts à imprimer sont dans [`site/public/imprimer/`](../../site/public/imprimer/) (le site les sert
sur `/imprimer` et en bas des fiches des bestioles concernées) :

- `coloriages/` : 12 coloriages A4 (PDF), au moins un par famille, contours « en escaliers de pixels » faits à partir
  des vrais sprites ; chacun a été regardé à l'œil avant d'être gardé ;
- `stickers_A4.pdf` : 15 bestioles, 3 œufs et 2 commandes, avec un trait gris de découpe ;
- `poster_A3.pdf` (fond sombre) et `poster_A3_fond_blanc.pdf` (moins d'encre) : la carte du Terminaworld, sans les
  noms des mondes.

Les textes des fichiers sont en français. Licence : CC BY-NC-SA 4.0 (voir [`LICENSE-images.md`](../../LICENSE-images.md)).

## Les refaire

Outils de fabrication (hors du jeu) : Python 3 avec Pillow, numpy, scipy, scikit-learn, scikit-image et Playwright
(Chromium), depuis la racine du dépôt :

    python3 docs/imprimer/fabriquer/coloriages.py [dossier_pour_regarder] [id ...]
    python3 docs/imprimer/fabriquer/stickers_poster.py [dossier_pour_regarder]

La liste des coloriages et les réglages choisis pour chacun sont dans `fabriquer/choix.py`. Pour en ajouter un :
l'ajouter à `choix.py`, le fabriquer, **le regarder en entier**, puis l'ajouter à `COLORIAGES` dans
`site/src/worker.js` (`pc/outils/test_autour.py` vérifie que les deux listes sont les mêmes).
