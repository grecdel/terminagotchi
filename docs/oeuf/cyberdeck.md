# Le cyberdeck Terminagotchi — proposition à valider

> **Statut : proposition (2 novembre 2026, réécrite après les décisions du propriétaire du même jour), rien n'est
> fabriqué ni acheté.** C'est la **deuxième forme physique** à côté de l'**œuf** (voir `proposition.md`). Le
> cyberdeck est **seulement du matériel** : un petit ordinateur Linux portable, fait maison, sur lequel on installe
> **le jeu PC tel quel**. Il n'a **aucune fonction spéciale**. Le propriétaire choisit, corrige ou refuse chaque point
> encore ouvert (voir « Questions restantes » à la fin). Aucune marque imposée, aucun lien d'achat. Prix et
> autonomies = **ordres de grandeur**, à revérifier au moment de l'achat.

![Croquis du cyberdeck à clapet : ouvert à plat, de côté (ouvert et fermé), coupe](croquis_cyberdeck.png)

## 1. En une phrase

Un **petit ordinateur portable à clapet**, fait maison (fermé : environ **16 × 12 × 3,4 cm**, un peu plus grand
qu'une console portable), avec un **écran de 5 pouces** qui se replie sur un **clavier de 55 touches à la taille des
doigts d'enfant**. Dedans : **un vrai Linux** et **le jeu Terminagotchi pour PC, installé normalement**. L'enfant y
retrouve **sa créature et sa partie**, comme sur l'ordinateur de la maison.

## 2. Ce que fait le cyberdeck (et ce qu'il ne fait pas)

### 2.1 Le même jeu, rien de nouveau

- C'est un **ordinateur Linux comme un autre**, juste petit et portable. On y installe **le jeu PC tel quel** :
  mêmes mondes, mêmes leçons, mêmes vraies commandes (`ls`, `cd`, `cat`, `grep`, les tubes `|`…), même XP, mêmes
  niveaux. Le jeu utilise déjà Python et sait s'afficher dans un petit terminal (créature en haut, ligne de commande
  en bas) : **aucune version spéciale à écrire**.
- **Pas de « partie propre » au cyberdeck, pas de commande `tg deck envoie / reprend`, pas de créature déplacée**
  (ces idées de la première proposition sont abandonnées). Seul **l'œuf** isole la créature hors du jeu
  (voir `proposition.md`).
- Pour le jeu, le cyberdeck **est un PC** : il apprend donc le **programme PC** des commandes (§ 1.3 de
  `docs/programme.md`), pas celui du téléphone.

### 2.2 Comment la créature passe du PC au cyberdeck : la synchro qui existe déjà

C'est **exactement** la synchronisation qui relie déjà aujourd'hui le PC et le téléphone Android (le
« recensement », fichier `pc/tg/recense.py` côté PC, son équivalent côté téléphone). Rien de nouveau à coder.

En simple :

1. **Un compte sur le site du jeu**, créé une seule fois (avec un adulte) : `tg compte creer Pseudo`. Pas de mot de
   passe : l'appareil garde une **clé secrète**. Seul un **pseudo** part sur le site (pas de nom réel, pas d'adresse,
   pas de position).
2. **Relier un autre appareil** : sur le PC, `tg compte code` donne un **code valable 10 minutes** ; sur le
   cyberdeck (ou le téléphone), `tg compte lier CODE`. Les deux appareils ont maintenant **la même créature**.
3. **Ensuite tout se fait tout seul** : quand l'appareil a Internet, le jeu envoie au site **ce qu'il a gagné depuis
   la dernière fois** (XP, commandes goûtées, collection, records…), au plus une fois par minute ; le site
   **additionne** ce que chaque appareil a gagné et renvoie la créature commune. On peut donc jouer **sur les deux**,
   même le même jour : rien n'est perdu ni compté deux fois.
4. **Sans Internet**, le jeu marche quand même (il garde d'avance les tirages des prochains jours) ; il rattrape la
   synchro à la prochaine connexion.
5. **Sans compte**, le cyberdeck est simplement **un ordinateur de plus avec sa propre partie**, comme un deuxième
   PC : rien ne passe d'un appareil à l'autre.
6. En **mode classe**, aucune synchro (règle déjà en place dans le jeu).

### 2.3 Wi-Fi éteint par défaut : est-ce compatible avec la synchro ?

**Pas complètement, il faut le dire franchement** : la synchro passe **par Internet** (le site du jeu). Wi-Fi
éteint = pas de synchro tant qu'on ne l'allume pas (le jeu continue de marcher, et rattrape au retour du Wi-Fi).
Rien n'est perdu, mais la créature du PC et celle du cyberdeck ne se rejoignent qu'une fois le Wi-Fi allumé.

**Proposition (en attente)** : Wi-Fi **éteint par défaut** ; un adulte enregistre **une fois** le Wi-Fi de la maison ;
l'enfant peut **allumer ou éteindre le Wi-Fi lui-même**, comme le mode avion d'un téléphone (c'est le réglage
normal de Linux, pas une fonction du jeu ; il est en général permis sans droits d'administrateur, **à vérifier au
prototype**). Allumé, le jeu synchronise tout seul comme sur le PC. Autre choix possible : Wi-Fi **allumé à la
maison** comme sur l'ordinateur familial (synchro toujours à jour). Voir question 3.

Les mises à jour du système et du jeu se font comme sur un PC (Wi-Fi allumé par l'adulte), ou par la carte microSD.

### 2.4 Un vrai Linux, mais l'enfant ne peut pas le casser (proposé, en attente)

- L'enfant a **son propre compte sur l'appareil, sans droits d'administrateur** (pas de `sudo`). L'adulte garde un
  **compte administrateur** (mot de passe choisi par lui) pour les mises à jour.
- Au démarrage, le cyberdeck peut ouvrir directement **le jeu** (comme on lance le jeu sur le PC).
- **Remise à zéro facile** : un adulte recopie l'**image prête** sur la carte microSD (comme on installe un
  système) ; la partie de l'enfant est **dans son compte du jeu** (si synchro) ou sauvegardée à part.
- Pas de navigateur installé, pas de messagerie.

### 2.5 Avec l'œuf

L'œuf se branche au cyberdeck **comme au PC**, par câble USB-C, puisque c'est **le même jeu** :
- **mode compagnon** : la créature de l'œuf réagit aux commandes tapées au clavier du cyberdeck ;
- **envoyer / reprendre** la créature dans l'œuf, avec les mêmes commandes que sur le PC (noms choisis quand
  l'œuf sera codé).

### 2.6 Qui fait quoi : œuf ou ordinateur ?

| | **L'œuf** | **PC, téléphone, cyberdeck** |
|---|---|---|
| Son rôle | **promener et soigner** la créature | **apprendre le terminal** |
| Ce qu'on y fait | marcher (compteur de pas), nourrir, caresser, coucher, avec 3 boutons | taper de vraies commandes : leçons, mondes, quêtes, défis |
| Terminal | **aucun** | **le vrai** (PC, cyberdeck) ou celui de l'appli (téléphone) |
| Ce que ça rapporte | **forme** (satiété), **bonne humeur** (envies de jeu, de sommeil, d'explorer), **jours soignés** (qui aident à grandir), journal de balade et petites découvertes | **XP, niveaux**, évolution, nouveaux mondes, badges |
| XP | **aucune** (proposition) | toute l'XP du jeu |
| Où est la créature | **déplacée** dans l'œuf, **à part du jeu**, le temps de la balade | dans le jeu ; **la même** sur les trois grâce au compte |
| Internet | jamais | seulement pour la synchro du compte (si on en a un) |

Le cyberdeck et le PC sont **le même jeu** ; le cyberdeck, c'est juste un PC qu'on peut emporter.

## 3. La forme à clapet

- **Le bas** porte le **clavier**, les **cartes** (Linux, charge), et à l'arrière les **accus** (trappe vissée en
  dessous). **Le couvercle** porte l'**écran** et le **haut-parleur**.
- **Deux charnières à friction** (comme un petit ordinateur portable) : l'écran tient à l'angle choisi, jusqu'à
  **≈ 110°**. Fermé, l'écran est **protégé** dans le sac : plus besoin de housse.
- **Touches en creux** sous le bord du dessus : fermé, l'écran ne les touche pas.
- Prise **USB-C sur le côté droit** (recharge et branchement de l'œuf), bouton **marche / arrêt propre** et deux
  **voyants** sur le dessus, à l'arrière du clavier ; **aérations** dessous (sous le ventilateur) et sur le dessus.
- Le cyberdeck s'utilise **posé sur une table** (ou sur les genoux), écran levé.

## 4. Les variantes

L'ancienne variante A « Micro » (terminal imité, microcontrôleur) est **supprimée** : son rôle « simple et pas
cher » revient à l'**œuf**. Il reste :

| | **C. « Grand confort »** (variante principale) | **Option « Clapet compact »** (ancienne B, plus petite, moins chère) |
|---|---|---|
| Pour qui | le cyberdeck « normal » : grand écran, chiffres en accès direct, fluide | petit budget, plus léger ; toujours un **vrai Linux** et le jeu PC |
| Contenu | carte Linux 1 à 2 Go + petit ventilateur, écran **5 pouces 1280 × 720**, clavier **55 touches** (rangée de chiffres), haut-parleur, **4 accus 18650** | petite carte Linux 512 Mo à 1 Go (sans ventilateur), écran **4 pouces 800 × 480**, clavier **44 touches** (chiffres avec Fn), haut-parleur, **2 accus 18650** |
| Fermé (L × P × épaisseur) | **≈ 160 × 120 × 34 mm** (bas 24 + couvercle 10) | **≈ 145 × 100 × 31 mm** (bas 22 + couvercle 9) |
| Ouvert, écran levé | ≈ 135 mm de haut | ≈ 115 mm de haut |
| Poids estimé | **≈ 520 g** | **≈ 340 g** |
| Texte à l'écran | ≈ 60 colonnes × 20 lignes (police assez grosse pour 7 ans) | ≈ 50 colonnes × 18 lignes |
| Difficulté | ★★★ : alimentation plus forte, ventilation, charnières | ★★☆ : préparation du système, énergie, charnières |
| Consommation en marche | **≈ 4 W** (carte ≈ 2,2 W, écran ≈ 1,5 W, clavier + son ≈ 0,2 W, ventilateur ≈ 0,1 W en moyenne) | **≈ 1,7 W** (carte ≈ 0,8 W, écran ≈ 0,8 W, clavier ≈ 0,1 W) |
| Allumé, écran éteint | ≈ 2,4 W : pas de vraie veille, donc **on l'éteint** en le refermant | ≈ 0,9 W : idem |
| **Autonomie estimée** | **≈ 7 h** de jeu (≈ 5,5 h luminosité à fond) | **≈ 9 h** de jeu |
| Recharge complète | ≈ 3,5 h (chargeur 5 V 3 A) à 5 h (5 V 2 A) | ≈ 3 h (5 V 2 A) |
| À 1 h par jour | une charge **par semaine** environ | une charge **par semaine** environ |
| **Prix estimé des pièces (fin 2026)** | **≈ 145 à 290 €** | **≈ 80 à 165 €** |

**Comment l'autonomie est calculée** (80 % de la batterie utilisable, 85 % de rendement pour fabriquer le 5 V à
partir des accus) :
- **C** : 4 accus 18650 de 3000 mAh = 4 × 3000 mAh × 3,7 V ≈ **44 Wh**. Utiles : 44 × 0,80 × 0,85 ≈ **30 Wh**.
  En jeu : 30 Wh / 4 W ≈ **7,5 h**. Luminosité et carte à fond (≈ 5,5 W) : 30 / 5,5 ≈ **5,5 h**. Laissé allumé écran
  éteint : 30 / 2,4 ≈ 12 h, d'où l'**arrêt propre** quand on le range. Recharge : 44 Wh / (15 W × 0,85) ≈ **3,5 h**
  avec un chargeur 5 V 3 A ; ≈ 5 h avec 5 V 2 A. Avec seulement 2 accus (plus léger), ≈ **3,5 h** de jeu : pas
  conseillé.
- **Compact** : 2 accus = 2 × 3000 mAh × 3,7 V ≈ 22 Wh ; utiles ≈ **15 Wh** ; 15 / 1,7 ≈ **9 h**. Recharge :
  22 Wh / (10 W × 0,85) ≈ 2,6 h, soit **≈ 3 h**.
- Éteint, il ne consomme presque rien (la carte de charge coupe tout) : à 1 h par jour, **une charge par semaine**.
- **Attention** : calculs sur le papier. La vraie consommation dépend de la carte, de l'écran et de la luminosité :
  on la **mesure** au premier prototype (testeur USB) et on corrige ce tableau.

**Comment les prix sont calculés** (pièces neuves, petites quantités, en ligne, fin 2026 ; somme des lignes du § 5) :
- C : de 50 + 5 + 30 + 12 + 3 + 20 + 10 + 1 + 3 + 4 + 4 + 3 + 1 ≈ **146 €** à 90 + 10 + 50 + 28 + 6 + 45 + 25 + 2 + 6 + 10 + 7 + 5 + 3 ≈ **287 €**.
- Compact : de ≈ **77 €** à ≈ **166 €**.
- Les cartes Linux ont augmenté plusieurs fois en 2026 (la mémoire coûte plus cher) : une petite carte « format
  zéro » reste vers 15 à 25 €, une carte de 1 à 2 Go dépasse souvent 50 à 80 €. Les modèles changent vite : on
  choisira au moment d'acheter. Le clapet coûte quelques euros de plus que l'ancienne forme d'un seul bloc
  (charnières, un peu plus de plastique).

## 5. Liste des composants (génériques)

Pas de marque imposée, pas de lien d'achat. **Prix = estimations**, à revérifier.

| Composant | Description simple | C | Compact | Prix estimé |
|---|---|:-:|:-:|---|
| **Carte Linux** 1 à 2 Go + **dissipateur avec petit ventilateur** | le cerveau de C | ✓ | | 50 à 90 € |
| **Petite carte Linux** « format zéro » (≈ 65 × 30 mm, 4 cœurs 64 bits, 512 Mo à 1 Go, faible consommation) + petit dissipateur | le cerveau du compact | | ✓ | 15 à 25 € |
| **Carte microSD** 16 à 32 Go, de bonne qualité | le disque : système + jeu | ✓ | ✓ | 5 à 10 € |
| **Écran IPS** 5 pouces 1280 × 720 (C) / 4 pouces 800 × 480 (compact), liaison vidéo adaptée à la carte | la fenêtre du jeu | ✓ | ✓ | 30 à 50 € / 15 à 30 € |
| **Clavier** : 55 (C) ou 44 (compact) **boutons tactiles** à course franche + **capuchons imprimés** ≈ 10 mm + **plaque de circuit** (commandée d'après nos plans, ou plaque à trous) | les touches | ✓ | ✓ | 12 à 28 € / 10 à 25 € |
| **Petite puce de clavier** (microcontrôleur avec USB, type RP2040 ou équivalent) + **programme de clavier libre** existant | fait de la grille de touches un « clavier USB » que Linux reconnaît | ✓ | ✓ | 3 à 6 € |
| **Accus 18650 avec circuit de protection intégré**, identiques, neufs, du même lot + **support solide** : 4 (C) ou 2 (compact) | l'énergie | ✓ | ✓ | 20 à 45 € / 10 à 25 € |
| **Carte d'alimentation** : charge USB-C + sortie 5 V (5 A pour C, 2,5 A pour le compact) + protections (surcharge, décharge profonde, court-circuit, température si possible) + signal « batterie faible » pour l'arrêt propre | recharge et arrêt sans danger | ✓ | ✓ | 10 à 25 € / 5 à 15 € |
| **2 charnières à friction** (métal, petites) | l'écran tient à l'angle choisi | ✓ | ✓ | 4 à 10 € |
| **Bouton marche / arrêt** + 2 voyants | allumer, éteindre proprement | ✓ | ✓ | 1 à 2 € |
| **Petit ampli audio + haut-parleur 8 Ω ≈ 20 mm** | le son | ✓ | ✓ | 3 à 6 € |
| **Filament PETG** (tient mieux la chaleur que le PLA) : ≈ 200 à 250 g (C), ≈ 150 g (compact) | la coque | ✓ | ✓ | 4 à 7 € / 3 à 5 € |
| Visserie : vis + **inserts laiton**, vis de trappe, fils fins, gaine thermo, ruban isolant (Kapton), nappe souple entre bas et couvercle | assemblage, isolation | ✓ | ✓ | 3 à 5 € / 2 à 4 € |
| Vitre avant (fine plaque acrylique) | protège l'écran | ✓ | ✓ | 1 à 3 € |

Outils (déjà présents ou à emprunter) : imprimante 3D, fer à souder, multimètre (idéalement un **testeur USB**),
lecteur de carte microSD, câble USB-C.

### 5.1 Un clavier pour des doigts d'enfant (proposé, en attente)

- **Touches ≈ 10 mm, espacées de 12 mm** (un clavier de téléphone en a 5 ou 6) ; **grille droite**, sans décalage,
  plus facile à viser. Course franche avec un petit **clic**.
- **AZERTY** (le propriétaire est français) ; **QWERTY** disponible dans les plans, même plaque, autres capuchons.
- **Les symboles du terminal ont leur propre touche, en bleu** : `-` `.` `/` `~` `|`.
- **Touches de commande en gris** : Effacer, Entrée, Maj, Ctrl (pour **Ctrl + C**), Tab (complétion), flèches.
- **C** : vraie **rangée de chiffres** (55 touches, 5 rangées × 11). **Compact** : chiffres avec **Fn** (44 touches,
  4 rangées × 11), petits chiffres orange imprimés sur la rangée du haut.
- Lettres **en relief ou gravées** sur les capuchons (pas d'autocollants), capuchons **bien emboîtés**.

Disposition proposée (C, 5 rangées × 11 ; Entrée sur deux rangées) :

| | | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 0 | ⌫ |
| A | Z | E | R | T | Y | U | I | O | P | ↵ |
| Q | S | D | F | G | H | J | K | L | M | ↵ |
| ⇧ | W | X | C | V | B | N | **-** | **.** | **/** | ↑ |
| Ctrl | Fn | Tab | **~** | espace | (espace) | (espace) | **\|** | ← | ↓ | → |

## 6. Sécurité

### 6.1 Les accus 18650

- **Toujours des accus avec circuit de protection** **et** une carte de charge dédiée (4,2 V maximum par accu).
  **Jamais d'accus nus récupérés**, **jamais** de mélange vieux / neufs ou de modèles différents.
- Accus **dans un support solide** à l'arrière du bas, séparés de l'électronique par une **paroi isolante**, loin
  des vis, des charnières et des arêtes ; fils gainés. Rien ne peut les percer si le cyberdeck tombe.
- **Trappe batterie fermée par une vis** (dessous) : l'enfant n'atteint pas les accus sans tournevis.
- **Charger sur une surface dure**, pas sous un oreiller ni au soleil, de préférence en présence d'un adulte.
- **Batterie presque vide : sauvegarde puis arrêt propre** (validé), avec un message de la créature (« je vais
  dormir, recharge-moi »). Ce n'est pas une fonction du jeu : c'est le système qui s'éteint proprement, et le jeu
  sauvegarde comme quand on éteint un PC.
- Jamais d'accu gonflé, cabossé, chaud ou à la gaine abîmée : on le remplace. Fin de vie : bac de recyclage.
  Souder **accus débranchés**.

### 6.2 La chaleur

- C : **dissipateur + petit ventilateur**, aération dessous et sur le dessus. Compact : dissipateur seul.
  Objectif : **coque tiède**, jamais chaude au toucher (moins de ≈ 40 °C dehors), mesuré au prototype après une heure.
- **Ne pas laisser allumé fermé** (l'air circule mal) : refermer = éteindre proprement (proposé : arrêt propre quand
  on referme le clapet, si la carte le permet ; sinon un appui sur le bouton).
- Coque en **PETG** (le PLA se déforme vers 55 à 60 °C, par exemple dans une voiture au soleil). Ne pas utiliser
  sous une couverture ni sur un lit.

### 6.3 Les enfants

- **Montage et soudure par un adulte.** L'enfant peut choisir les couleurs, poser les capuchons du clavier,
  installer le jeu.
- Coque **sans arêtes vives** ; charnières sans endroit où **se pincer les doigts** (écart ≥ 8 mm ou cache) ; pas de
  petites pièces détachables, pas d'aimant accessible.
- **Volume limité** ; pas de son la nuit.
- Honnêteté : un cyberdeck fait maison **n'est pas un jouet certifié**. On le donne en connaissance de cause et sous
  surveillance. On partage **les plans**, chacun fabrique le sien (vendre des appareils montés demanderait le
  marquage CE et des tests : ce n'est pas l'objectif).

## 7. Ce qui est open source

Mêmes licences que l'œuf (validées le 2 novembre 2026) :

| Partie | Licence | En simple |
|---|---|---|
| **Code** : le jeu, le programme du clavier, les scripts qui préparent l'image du système | **GPL-3.0-or-later** | tout le monde peut lire, modifier et partager, à condition de partager ses modifications pareil |
| **Dessins, sons, textes**, motifs décoratifs de la coque | **CC BY-NC-SA 4.0** | réutilisation en citant Terminagotchi, sans usage commercial, partage à l'identique |
| **Matériel** : coque (STL + fichiers sources), plaque du clavier, schéma électrique, liste des pièces, notice | **CERN-OHL-S-2.0** | chacun peut fabriquer et modifier, mais doit publier ses plans modifiés sous la même licence |

Le système Linux et les logiciels de l'image gardent **leurs propres licences libres** ; le programme de clavier
libre réutilisé aussi.

## 8. Comment on avancerait (après validation)

1. **Maquettes d'abord** (règle du propriétaire) : images du cyberdeck ouvert et fermé ; **maquette en carton ou
   imprimée vide** du clapet pour tester avec un enfant la taille des touches, l'angle de l'écran et le poids.
2. **Essai sans matériel** : le jeu PC dans une fenêtre de terminal réglée à 60 × 20 (écran C) et 50 × 18
   (compact) pour vérifier que tout reste lisible.
3. **Prototype sur table** : carte Linux + écran + clavier USB ordinaire ; image du système (compte enfant sans
   droits, jeu installé, Wi-Fi éteint par défaut, arrêt propre) ; **test de la synchro** avec le compte, Wi-Fi
   allumé par l'enfant.
4. **Clavier v1** (55 touches), essais de frappe par des enfants de 7, 12 et 15 ans.
5. **Énergie** : 4 accus protégés, carte de charge, arrêt propre sur batterie faible ; **mesures** de consommation et
   de température, tableaux du § 4 corrigés.
6. **Coque v1 à clapet** (OpenSCAD ou FreeCAD, fichiers ouverts) : charnières, nappe entre bas et couvercle,
   aérations, trappe vissée.
7. **Œuf branché** au cyberdeck (mode compagnon), quand l'œuf existera.
8. Dossier de fabrication complet dans `materiel/cyberdeck/` (notice pas à pas pour un parent et son enfant).

## 9. Questions restantes

| # | Question | Ma proposition |
|---|---|---|
| 1 | Garder l'option « Clapet compact » (4 pouces, 2 accus, ≈ 80 à 165 €) à côté de C ? | **Oui, en option** dans les plans (même dessin de coque, réduit) ; on fabrique **C d'abord**. |
| 2 | C avec 4 accus (≈ 7 h, ≈ 520 g) ou 2 accus (≈ 3,5 h, ≈ 430 g) ? | **4 accus** : 3,5 h, c'est trop court pour une journée. |
| 3 | Wi-Fi : éteint par défaut (synchro seulement quand l'enfant l'allume) ou allumé à la maison ? | **Éteint par défaut, l'enfant peut l'allumer** comme un mode avion (à vérifier sans droits d'administrateur) ; le jeu rattrape la synchro dès que le Wi-Fi revient. |
| 4 | Refermer le clapet éteint-il le cyberdeck ? | **Oui, arrêt propre** (sauvegarde comme un PC), si la carte sait détecter le clapet ; sinon bouton. |
| 5 | Démarrer directement sur le jeu, ou sur un bureau Linux ? | **Directement sur le jeu** dans un terminal plein écran ; l'enfant peut le quitter et rester dans son vrai shell. |
| 6 | Compte enfant sans `sudo` + compte adulte ? | **Oui** (proposé, en attente). |
| 7 | Clavier AZERTY, touches ≈ 10 mm, 55 touches pour C ? | **Oui** (proposé, en attente) ; QWERTY dans les plans. |
| 8 | Coque en PETG ? | **Oui** (proposé, en attente). |
| 9 | Dossier `materiel/cyberdeck/` dans ce dépôt ? | **Oui** (proposé, en attente) ; cette proposition reste dans `docs/oeuf/`. |

## Fichiers de ce dossier (cyberdeck)

- `cyberdeck.md` — ce document.
- `croquis_cyberdeck.py` → `croquis_cyberdeck.svg` / `.png` (matplotlib : `python3 croquis_cyberdeck.py`) :
  ouvert à plat vu de face, de côté ouvert et fermé, coupe de côté.

## Décisions du propriétaire

### 2 novembre 2026 (première série)

- **1. Vrai Linux** : oui.
- **2. Variantes visées : A « Micro » et C « Grand confort »** (B n'est plus la cible). → *remplacé par la deuxième
  série : A est supprimée.*
- **3. Forme à clapet** (l'écran se replie sur le clavier), et non plus d'un seul bloc : croquis et tailles à refaire.
  → *fait (§ 3, § 4, croquis).*
- **4. Sa propre partie, créatures déplacées** : explication demandée. → *remplacé par la deuxième série : plus de
  partie propre ni de créature déplacée.*
- **5. Batterie presque vide** : sauvegarde automatique puis arrêt propre, oui.

### 2 novembre 2026 (deuxième série)

Mots du propriétaire : « le cyberdeck c'est pour le côté hardware, donc les fonctionnalités restent les mêmes, on
crée juste un Linux portable et on installe le jeu dessus. Seul l'œuf a une fonction d'isolation » ; « pour la
version A je pensais plutôt à un espace simple, sans terminal, éventuellement un compteur de pas et des boutons pour
nourrir simplement, il faut une vraie complémentarité entre le cyberdeck et l'œuf ».

- **Le cyberdeck est seulement du matériel** : un ordinateur Linux portable fait maison avec **le jeu PC installé
  tel quel**. Aucune fonction spéciale : **pas de partie propre, pas de `tg deck envoie / reprend`**.
- **Synchro PC ↔ cyberdeck = celle qui existe déjà entre PC et téléphone** (compte du jeu, § 2.2).
- **Vrai Linux** et **forme à clapet** : validés.
- **Variante A « Micro » supprimée** (son rôle simple revient à l'œuf). **C « Grand confort » (5 pouces) = variante
  principale** ; l'ancienne B reste en **option** plus petite et moins chère (« Clapet compact »).
- **Batterie presque vide : sauvegarde puis arrêt propre** : validé.
- **L'œuf se branche au cyberdeck comme au PC** (mode compagnon), puisque c'est le même jeu.
- **Complémentarité** : œuf = promener et soigner ; PC / téléphone / cyberdeck = apprendre le terminal (§ 2.6).
- Restent **proposés, en attente** : clavier AZERTY ≈ 10 mm, compte enfant sans `sudo`, Wi-Fi éteint par défaut
  (compatible avec la synchro seulement quand on l'allume, § 2.3), PETG, dossier `materiel/cyberdeck/`.
