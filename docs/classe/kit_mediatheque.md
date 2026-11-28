---
title: "Terminagotchi — kit d'atelier en médiathèque"
subtitle: "BROUILLON du 3 novembre 2026 · à relire · pour une médiathèque, un tiers-lieu, un club"
lang: fr
---

# À lire d'abord

> **Brouillon.** Ce kit n'a pas encore été testé dans une vraie médiathèque. L'affiche est une maquette
> (`/home/claude/outils/ameliorations/classe/planche_2.png`), pas encore un fichier à imprimer du dépôt.

**Ce que c'est.** Un atelier d'**1 h 30** pour 8 à 16 enfants **dès 7 ans** (en binômes), animé par une personne
qui n'a pas besoin d'être informaticienne. Les enfants font éclore leur créature en tapant leurs premières vraies
commandes d'ordinateur.

**Ce que ce n'est pas.** Il n'y a ni compte à créer, ni inscription en ligne, ni achat, ni publicité, ni discussion
entre enfants dans le jeu. Rien n'est envoyé sur Internet pendant l'atelier.

# Le matériel

| Quoi | Combien | Remarque |
|---|---|---|
| Ordinateurs (Linux, macOS ou Windows) | 1 pour 2 enfants | Python 3 installé ; le jeu tourne hors ligne |
| Le fichier du jeu `terminagotchi.pyz` | copié sur chaque poste | aucune installation ; une clé USB suffit |
| Vidéoprojecteur ou grand écran | 1 | sur le poste de l'animateur (`tg espace classe`) |
| Feuilles « Ma créature » et crayons | 1 par enfant | pour dessiner sa créature à la fin (voir plus bas) |
| Étiquettes de pseudonymes | 1 par binôme | un pseudonyme inventé, jamais le prénom |
| L'affiche | 2 ou 3 | à remplir au stylo (date, heure, lieu, places) |

**La veille.** Lancer le jeu une fois sur chaque poste et le refermer : c'est le moyen de vérifier que Python
fonctionne. Ne pas faire éclore les œufs : c'est le meilleur moment de l'atelier.

**Pour effacer après l'atelier.** Sur chaque poste, supprimer les dossiers `terrain_terminagotchi` et
`.terminagotchi` du dossier personnel (ou `tg classe effacer` puis supprimer ces deux dossiers). Rien d'autre n'a
été écrit sur l'ordinateur.

# Le déroulé (1 h 30)

| Temps | Phase | Ce que fait l'animateur |
|---|---|---|
| 0-10 | Accueil | binômes, pseudonymes sur les étiquettes ; « un ordinateur, ça s'écoute et ça se parle : on va lui parler avec des mots » |
| 10-15 | Lancement | au grand écran, l'animateur tape `tg` et montre l'œuf ; puis chaque binôme tape `tg classe code 01-GS-B <pseudo>` |
| 15-35 | L'éclosion | les enfants suivent la consigne du jeu (`pwd`, `ls`, `echo`) ; l'animateur passe de binôme en binôme |
| 35-40 | Pause « crac ! » | on fait le tour des créatures écloses (à voix haute, sans comparer) |
| 40-70 | Le premier chapitre | « Où suis-je ? », « Le vieux chemin » ; on échange les rôles (clavier / lecteur) à chaque leçon |
| 70-80 | Dessine ta créature | sur la feuille « Ma créature » : son nom, ce qu'elle aime manger (les commandes) |
| 80-90 | Au revoir | ce qu'on a appris (3 mots au tableau : `pwd`, `ls`, `cd`) ; `tg classe fin` ; où retrouver le jeu chez soi (avec un adulte) |

**Le geste qui débloque presque tout.** L'espace entre la commande et ce qui suit (`cd vestibule`, pas
`cdvestibule`) ; et la touche Tab, qui complète les noms.

**Si un enfant va beaucoup plus vite.** Le chapitre 2 (« Le nid ») est ouvert : il peut continuer seul.

**Si un enfant est découragé.** Le jeu ne punit jamais : la créature n'a pas faim pendant une séance (code de
séance), et avec le code guidé la commande à taper est toujours montrée à l'écran. Changer les rôles du binôme aide souvent.

# Pour l'animateur qui n'a jamais ouvert un terminal

- Le **terminal** est la fenêtre noire où l'on tape. Le jeu ouvre le sien sous Windows ; sous Linux et macOS,
  c'est l'application « Terminal ».
- `pwd` dit **où l'on est**, `ls` montre **ce qu'il y a ici**, `cd nom` **entre** dans un dossier, `cd ..`
  **remonte**.
- Rien de ce que les enfants tapent dans le jeu ne peut abîmer l'ordinateur : le jeu ne travaille que dans
  `terrain_terminagotchi`. Il ne lance jamais `sudo`.

# Ce qui reste à faire avant de diffuser ce kit

- Valider l'affiche (maquette du 3 novembre) puis en faire un PDF A4 imprimable dans le dépôt.
- Dessiner la feuille « Ma créature » (A4, à colorier).
- Tester l'atelier une fois avec de vrais enfants et ajuster les temps.
