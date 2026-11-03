# Licence des images, dessins, textes de l'histoire et sons de Terminagotchi

Copyright © 2026 les contributeurs de Terminagotchi

Les images, les dessins, les animations, les textes de l'histoire (le « lore ») et les sons de Terminagotchi sont
sous licence **Creative Commons Attribution - Pas d'Utilisation Commerciale - Partage dans les Mêmes Conditions 4.0
International (CC BY-NC-SA 4.0)**.

Texte officiel de la licence : https://creativecommons.org/licenses/by-nc-sa/4.0/
(en français : https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr ; texte juridique complet :
https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.fr)

**Exception : la mascotte du site** (le petit personnage vert qui sort de son œuf-circuit, sur le site web) n'est
**pas** sous cette licence : **tous droits réservés, les contributeurs de Terminagotchi**. Voir la section
« La mascotte du site » plus bas.

Le **code** du jeu, lui, est sous licence **GNU GPL version 3 ou toute version ultérieure** (GPL-3.0-or-later) :
voir le fichier [`LICENSE`](LICENSE).

## En résumé (français)

Tu as le droit de **partager** (copier et redistribuer) et d'**adapter** (remixer, transformer, créer à partir de)
ces œuvres, à trois conditions :

- **Attribution (BY)** : cite « les contributeurs de Terminagotchi », mets un lien vers la licence et indique si tu
  as fait des modifications.
- **Pas d'utilisation commerciale (NC)** : tu ne peux pas les utiliser pour gagner de l'argent.
- **Partage dans les mêmes conditions (SA)** : si tu les modifies, tu dois partager ta version sous la même
  licence (CC BY-NC-SA 4.0).

Ce résumé n'est pas la licence : seul le texte officiel (lien ci-dessus) fait foi.

## Summary (English)

You are free to **share** (copy and redistribute) and **adapt** (remix, transform, and build upon) these works,
under three conditions:

- **Attribution (BY)**: credit "the Terminagotchi contributors", link to the license, and indicate if changes were
  made.
- **NonCommercial (NC)**: you may not use them for commercial purposes.
- **ShareAlike (SA)**: if you remix or transform them, you must distribute your contributions under the same
  license (CC BY-NC-SA 4.0).

This summary is not the license: only the official text (link above) is legally binding.

## Ce qui est concerné / What this covers

- `donnees/bestiaire2/images/` et `donnees/bestiaire2/animations/` : les créatures, leurs stades et leurs animations ;
- `donnees/illustrations/` (les images), `donnees/portraits/`, `donnees/sources/`, `donnees/animation/` (les images),
  `donnees/oeufs/` (les images) : illustrations, portraits, œufs, planches ;
- dans le jeu pour ordinateur : `pc/tg/sprites.bin`, `pc/tg/poses.bin`, `pc/tg/illustrations.bin`,
  `pc/tg/carte_monde.png` ;
- dans l'appli Android : `app/src/main/assets/portraits/`, `app/src/main/assets/anim/`, `app/src/main/assets/intro/`,
  `app/src/main/assets/sprites.bin`, `app/src/main/assets/poses.bin` ;
- `docs/img/` : les images de la présentation ;
- `site/public/imprimer/` : les coloriages, la planche de stickers et le poster à imprimer (fabriqués par
  `docs/imprimer/fabriquer/`, dont le code est sous GPL comme le reste du code) ;
- `site/public/` : les images du site (portraits, animations), **sauf** le dossier `site/public/polices/` et les
  images de la mascotte du site (voir plus bas) ;
- les textes de l'histoire (récits, dialogues, descriptions des créatures, des lieux et des mondes), qui se trouvent
  dans les fichiers de langue (`pc/tg/langues/`, `app/src/main/assets/langues/`) et leurs sources
  (`donnees/**/outils/textes_*.py`) ;
- les sons du jeu, quand il y en aura.

## Ce qui n'est PAS concerné / What this does NOT cover

- la **mascotte du site** : voir la section suivante (tous droits réservés) ;
- le **code** (Python, Kotlin, JavaScript, scripts, fichiers de construction) : GPL-3.0-or-later, voir `LICENSE` ;
- les polices de caractères de `site/public/polices/` (Press Start 2P, VT323) : elles gardent leur propre licence,
  la SIL Open Font License 1.1 (fichiers `OFL-*.txt` dans ce dossier) ;
- les noms et les textes de licences d'autres logiciels cités dans le jeu (la Guilde des Bâtisseurs Libres) : ils
  appartiennent à leurs auteurs.

## La mascotte du site : tous droits réservés / The website mascot: all rights reserved

**Français.** La mascotte du site de Terminagotchi (le petit personnage vert qui sort d'un œuf aux circuits
lumineux) n'est **pas** sous licence CC BY-NC-SA 4.0, ni sous la GPL : **tous droits réservés, les contributeurs de
Terminagotchi**. Tu peux la voir sur le site et dans ce dépôt, mais pas la copier, la modifier ni la réutiliser
ailleurs sans leur accord écrit. Fichiers concernés :

- `site/public/mascotte.png` (la mascotte) et `site/public/mascotte_mange.png` (la mascotte qui mange, planche
  d'animation) ;
- `site/public/favicon.png` et `site/public/icone.png` (les icônes du site, dessinées d'après la mascotte) ;
- `app/src/main/res/drawable-*/ic_launcher.png` (l'icône de l'appli Android, dessinée d'après la mascotte) ;
- toute autre image, dessin ou animation de cette mascotte.

La mascotte du site n'apparaît pas dans le jeu.

**English.** The Terminagotchi website mascot (the little green character coming out of a glowing circuit egg) is
**not** licensed under CC BY-NC-SA 4.0, nor under the GPL: **all rights reserved, the Terminagotchi contributors**.
You may view it on the website and in this repository, but you may not copy, modify or reuse it elsewhere without
their written permission. Files concerned: `site/public/mascotte.png`, `site/public/mascotte_mange.png`,
`site/public/favicon.png`, `site/public/icone.png`, `app/src/main/res/drawable-*/ic_launcher.png`, and any other
picture, drawing or animation of this mascot. The website mascot does not appear in the game.
