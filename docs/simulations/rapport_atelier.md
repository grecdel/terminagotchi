# Simulation : trois enfants visitent l'Atelier (dixième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_atelier.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Atelier.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_donnees.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. L'Atelier est ouvert d'avance comme
dans l'arbre du Carrefour (niveaux 0 à 4 du tronc commun).

**Le robot est simulé, la boucle est vraie.** `echo 1 > robot/led`, `cat robot/capteur_distance`, `cp`, `tail`, `time`
et la boucle `for i in $(seq 20); do sh cerveau.sh; atelier pas; done` passent par le vrai bash ; `cerveau.sh` est le
vrai script de l'enfant, lancé par le vrai `sh`. `atelier` est le vrai code du jeu (l'alias de `tg installer` est
remplacé par une petite doublure qui appelle le même code). La boucle infinie `while true …` est arrêtée par un vrai
Ctrl+C (SIGINT) au bout de 2 secondes. Quand l'enfant « ouvre nano », la simulation écrit dans `cerveau.sh` ce qu'il
taperait (pour Léa et Inès : les lignes qu'elles lisent à l'écran dans `atelier aide-cerveau`).

**Aucun matériel, rien d'envoyé.** Les proxys pointent vers 127.0.0.1:9 ; `sudo`, `curl`, `wget`, `arduino-cli`,
`esptool.py`, `screen`, `gpioset`, `pinctrl` et `minicom` sont des doublures qui refusent et notent qu'on les a
appelées : **aucune n'a été appelée** par le jeu. Rien n'est écrit hors du terrain (sauf la sauvegarde du jeu).

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** :
- les coordonnées, dans la ligne « position x=… y=… » de `atelier grille` ;
- les cases libres, dans « capteur : 30 cm » (÷ 10) de `atelier pas` ;
- la table de vérité, d'après le nom de la porte affichée (ET ou OU) et l'explication de `atelier logique` ;
- les trois situations, d'après leurs mots (« il faut les deux », « une seule suffit », « le contraire ») ;
- le réflexe, dans « … cm par seconde » et « … millisecondes » de `atelier reflexe`.

**Android.** `tests/jvm/Atelier.kt` refait la traversée at0 → at7 avec les commandes du téléphone (22 vérifications) :
- le shell du téléphone ne connaît pas `atelier` : l'appli **déroule la boucle** de l'enfant (`Atelier.boucle`) et lance
  `cerveau.sh` avec le vrai `sh` (le test le vérifie : la phrase « je vois un obstacle à … cm » du cerveau d'exemple
  apparaît, puis le 💥) ;
- deux défis : un cerveau qui tourne « trop tard » (`-lt 0`) se cogne, le cerveau malin réussit, l'exploit est donné ;
- le téléphone robot de poche : `lampe on`, `vibre 300`, `batterie` (les vraies commandes de l'appli ; sous la JVM,
  pas de lampe ni de vibreur, le test vérifie seulement que l'étape avance) ;
- Python et Kotlin donnent les mêmes résultats sur les vecteurs communs (`donnees/atelier/vecteurs.json`) : 25 parcours
  de 24 pas (5 arènes × 5 cerveaux), le verdict du défi, la grille dessinée, le moteur et la LED (UTF-8 et UTF-16), les
  tirages de chaque partie, la vue déployée.

**Les autres shells.** `pc/outils/test_atelier.py` (section 7) lance les lignes du téléphone avec `dash`, `mksh`,
`busybox sh` et les outils de `toybox` / `busybox`, et compare à bash. Ici seul `dash` est installé (identique) ; en CI,
toybox est compilé et busybox installé.

**Limites honnêtes.**
- Le rejeu bash complet de l'histoire tourne en CI ; ici, la partie Atelier a été rejouée avec `TG_REJEU_MONDE=robots`
  (20 identiques, 0 écart) et les fiches (`--fiches`) aussi.
- La boucle déroulée par l'appli et `edite cerveau.sh` n'ont pas été essayés sur un vrai téléphone (tests JVM seulement) ;
  ce sera fait avec l'APK d'essai.
- Les textes des 13 autres langues sont des traductions de Claude, non relues par des locuteurs.

## 1. Les trois profils en bref

| | Léa, 7 ans | Inès, 12 ans | Hugo, 15 ans |
|---|---|---|---|
| Lignes tapées | 67 | 56 | 46 |
| Au bout (at0 → at7) | oui | oui | oui |
| Défis | choc, puis réussi | « pas assez de cases », puis réussi | réussi du premier coup |
| Exploit « le robot qui évite tous les obstacles » | oui | oui | oui |
| Étape validée par une commande qui a échoué | 0 | 0 | 0 |
| Vrai matériel appelé / sudo / réseau | aucun | aucun | aucun |

## 2. Léa, 7 ans : elle se trompe d'abord, puis lit et corrige

Chaque faute a reçu une explication (le test le vérifie : aucune faute « sans explication ») :

| Ce qu'elle tape | Ce que le jeu répond |
|---|---|
| `Ls`, `Cat robot/led` (majuscule) | la commande n'existe pas avec une majuscule (message habituel du tronc commun) |
| `echo 1 robot/led` (sans `>`) | « N'oublie pas le chevron > pour écrire DANS le fichier » ; la LED reste éteinte |
| `echo 2 > robot/led` | « La LED ne comprend que 0 ou 1 » ; l'étape attend |
| `echo marche > robot/moteur` | « Le moteur comprend avance, gauche, droite ou stop » |
| `atelier ou 1 2` (x et y inversés) | « x est le numéro de la colonne, y celui de la ligne » |
| `atelier cases 30` (les centimètres) | « une case fait 10 cm, et le capteur dit 30 cm » |
| `atelier verite 1 1 1 1` | « Relis `atelier logique`, puis essaie ligne par ligne » |
| `atelier choix et et et` | « À revoir : situation 3. Il faut les deux ou une seule suffit ? » |
| `for i in $(seq 10); do sh cerveau.sh; done` (sans le pas du monde) | « il faut les deux : le cerveau PUIS `atelier pas` » |
| un cerveau sans condition (`echo droite > robot/moteur`) | « Ton cerveau.sh doit lire le capteur, avoir un if… Besoin des lignes ? `atelier aide-cerveau` » |
| le défi avec le cerveau d'exemple | 💥 « Ton robot s'est cogné : le défi s'arrête là » ; l'indice : « Ton cerveau tourne-t-il quand le capteur dit moins de 10 cm ? » |
| `atelier reflexe 3000` (sans ÷ 1000) | « 30 × 100, puis divise par 1000 (les ms en secondes) » |

Elle recopie ensuite les lignes de `atelier aide-cerveau`, relance `atelier defi` : 16 cases, aucun choc.

## 3. Inès, 12 ans : elle recopie la commande verte telle quelle

Elle tape `atelier ou ?`, `atelier verite ? ? ? ?`, `atelier choix ? ? ?`, `atelier reflexe ?` avec les « ? » : le jeu
dit « Remplace chaque ? par ta réponse » et redonne l'écran ; elle lit et répond juste. Son premier cerveau **s'arrête**
devant l'obstacle (`stop`) au lieu de tourner : aucun choc, mais seulement 7 cases sur 12 ; le jeu dit « ton robot doit
TOURNER devant l'obstacle (pas s'arrêter), puis repartir ». Elle corrige, réussit.

## 4. Hugo, 15 ans : ses variantes

Acceptées : `ls -l robot`, `cat ./robot/led`, `printf 1 > robot/led`, `printf '0\n' > robot/led`,
`head -1 robot/capteur_distance`, `echo right > robot/moteur` (le moteur comprend aussi l'anglais),
`for i in {1..3}; do …; done`, `while :; do …; done`, `cp -v`, `time bash cerveau.sh`, `which gpioset pinctrl`, `tail -n 5 robot/journal.txt`,
et SON cerveau (tourne à **gauche**, `-le 5`), qui réussit le défi du premier coup.

## 5. Ce qui a été corrigé grâce aux simulations

| # | Constat | Gravité | Correction |
|---|---|---|---|
| AT1 | `for i in {1..3}; do …` (Hugo) refusé : le motif n'acceptait que `for i in 1 2 3` | importante | le motif accepte `1 2 3`, `{1..3}` et `$(seq 3)` (PC et téléphone) ; la simulation exige maintenant 0 variante refusée |
| AT2 | `[ 5 -lt 10 ] && echo vrai \|\| echo faux` jamais validé : le jeu coupe la ligne en morceaux (`&&`, `;`) avant de comparer | critique | les motifs portent sur le bon morceau (`[ … ]`, `if [ "$d" -lt 10 ]`, `for i in …`, `while true`) |
| AT3 | la boucle infinie de la simulation ne s'arrêtait pas : un SIGINT envoyé seulement au `sleep` ne coupe pas la boucle d'un shell non interactif | critique (outil) | la simulation et le test arrêtent la boucle comme un vrai Ctrl+C au clavier (SIGINT à toute la ligne) |
| AT4 | sur le téléphone, `vibre 300` plante sous la JVM (pas de vibreur dans les imitations) | outil | le test JVM ne lance pas les trois commandes du vrai téléphone, il vérifie que l'étape avance |
| AT5 | l'inscription « je vois un obstacle à … cm » du cerveau d'exemple devait rester dans la langue de l'enfant | moyenne | le cerveau d'exemple est écrit avec les textes de la langue choisie (14 langues) |

Aucun problème critique ou important ne reste ouvert.

## 6. Ce qui reste à regarder

- Après un **choc**, le défi s'arrête, mais la boucle de l'enfant continue ses tours restants (le robot se cogne encore
  et la grille se redessine) : c'est fidèle à un vrai robot, mais un peu long à lire ; le message de fin est clair.
- ~~Le défi n'est pas jouable sous **Windows**~~ : fait (1er novembre). Voir § 7.

## 7. Windows : le même parcours en PowerShell (1er novembre)

On a rejoué at4 → at5 « comme sous Windows » (`pc/outils/test_windows.py`) puis pour de vrai sur la machine Windows de
GitHub, dans Windows PowerShell 5.1 et PowerShell 7 (`pc/outils/defi_powershell.py`).

- **Léa (7 ans)** copie `cerveau_exemple.ps1`, lance la boucle `for ($i=1; $i -le 10; $i++) { … }` : 💥 le choc, comme
  sous Linux. Elle oublie `atelier pas` dans sa boucle `ForEach-Object` : l'indice lui montre `.\cerveau.ps1` puis
  `atelier pas` (avant la correction, l'indice de la boucle apparaissait même quand la boucle était juste, parce que
  la ligne est coupée aux « ; » : corrigé pour bash aussi).
- **Inès (12 ans)** travaille dans un PowerShell ordinaire de l'école : Windows répond « l'exécution de scripts est
  désactivée sur ce système ». Son robot reste immobile (moteur sur `stop`) ; le jeu le voit et explique que ce n'est
  pas sa faute, avec `atelier aide-cerveau` qui donne `powershell -ExecutionPolicy Bypass -File .\cerveau.ps1` (pour
  cette fois, rien n'est changé sur l'ordinateur). En CI, la fenêtre « Restricted » imitée confirme le message et que
  les deux façons proposées marchent.
- **Hugo (15 ans)** écrit son cerveau avec `@' … '@ | Set-Content cerveau.ps1`, puis avec `>` (UTF-16 sous 5.1) : les
  deux sont reconnus ; le défi réussi donne l'exploit. Un ancien joueur Windows (leçon finie sans le défi) le reçoit en
  réussissant le défi.

Résultat sur la vraie machine Windows de GitHub (run 41348631277, 1er novembre) : Windows PowerShell 5.1.26100
(Desktop) et PowerShell 7 jouent at3 → at7 ; dans les deux, 20 pas, aucun choc, 18 cases explorées, l'exploit donné ; la
fenêtre « Restricted » répond bien « running scripts is disabled on this system », les deux façons proposées à l'enfant
y marchent, et la politique d'exécution de la machine est la même avant et après.

Problème trouvé et corrigé : les textes avec des accolades PowerShell (`{ … }`) cassaient `str.format` ; elles sont
doublées dans les fichiers de textes (`{{ … }}`), comme `TG{{…}}` ailleurs.
- Sur un vrai téléphone : la boucle déroulée par l'appli (40 tours au plus) et l'éditeur `edite cerveau.sh`.
