# Simulation : trois enfants visitent la Tour des Ondes (cinquième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_ondes.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Ondes.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_machines.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Tour est ouverte d'avance
comme dans l'arbre du Carrefour (niveau 4 du tronc commun, leçon « Les ports » du Port, leçon « Des 0 et des 1 » de
la Salle des Machines).

**Les radios sont des doublures.** `nmcli`, `iw`, `rfkill`, `bluetoothctl`, `meshtastic` et `rtl_test` sont remplacés
par de petits scripts qui affichent un quartier **fictif** — avec, exprès, le nom et l'adresse MAC d'un réseau de
voisin inventé, pour vérifier que le jeu ne les garde jamais. Rien n'émet ; aucun vrai balayage n'est lancé.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : la longueur d'onde est calculée avec `bc` ;
l'onde qui traverse le mieux est lue dans `ondes mur` ; le nombre de réseaux est compté dans la liste ; la règle et
les bandes libres sont lues sur `ondes spectre` ; le SF dans `ondes vallee` ; les messages par heure sont divisés à
partir du temps affiché ; la tempête est jouée en lisant le chemin affiché après chaque coupure.

**Android.** `tests/jvm/Ondes.kt` refait la traversée on0 → on10 avec les commandes du téléphone (calculs entiers en
millimètres et microsecondes à la place de `bc`, radios racontées) : 28 vérifications, dont l'égalité Python / Kotlin
sur les vecteurs communs (`donnees/ondes/vecteurs.json` : fréquences, longueurs, murs, canaux, règle, bandes, temps
d'émission LoRa au µs près, vallée, routes et inondations du maillage, cible de la tempête, antennes).

**Limites honnêtes.** La machine de test n'a ni carte Wi-Fi, ni Bluetooth, ni carte LoRa, ni clé radio : les vraies
sorties de `nmcli`, `iw`, `rfkill`, `bluetoothctl` n'ont été vues que par les doublures (la CI installe `iw` et
`rfkill` ; le runner GitHub n'a pas de radio non plus). `meshtastic --sendtext` et la vraie radio logicielle n'ont
**jamais** été lancés : ces étapes (W5, W6) sont facultatives, « avec un adulte », et racontées si l'outil manque.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « onde » |
|---|---|---|---|---|
| Léa, 7 ans, tape mal | une majuscule, la longueur du Wi-Fi au lieu de LoRa, `sudo`, `rfkill block`, `bluetoothctl scan on`, la règle dans l'ordre A B C D E F, la vallée en SF7 puis en SF12, la tempête en coupant la racine, le « ? » recopié, `grep` sans `-o` | 84 | oui, on0 → on10 | oui (après une tempête recommencée) |
| Inès, 12 ans, recopie | recopie la commande verte (« ? » compris), puis lit l'écran | 77 | oui | oui (une tempête recommencée) |
| Hugo, 15 ans, ses variantes | `ondes onde 868M`, `bc` avec `scale`, `iwconfig`, `nmcli -t`, `nmcli r`, `rfkill`, `printf … \| bc`, `which`, `less`, `grep -oE`, `ondes nœud`, `ondes écoute`… | 67 | oui | oui, 20 variantes justes acceptées sur 21 |

Commun aux trois : aucune étape validée par une commande qui a échoué ; rien d'écrit hors du terrain et de
`~/.terminagotchi` ; **le nom et l'adresse du réseau du voisin ne sont gardés ni dans le carnet ni dans la
sauvegarde** ; aucun message tapé (« bonjour », « SOS ») n'est gardé.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : les vagues plus serrées quand la fréquence monte, le mur qui « mange » plus le Wi-Fi 5 GHz que LoRa, la règle qui se range, le message qui tombe au milieu de la vallée. |
| `sudo`, `rfkill block`, `scan on` | Chaque fois une phrase claire : « Pas de sudo dans la tour : on lit la radio, on ne la change jamais. » ; « Cette commande change la radio… » ; « balayage actif… utilise --rescan no ». Rien n'est lancé de dangereux (doublures), et la bonne commande est redonnée. |
| La règle dans l'ordre A B C D E F | « 0 bien placée(s) sur 6. Regarde la règle (ondes spectre) et réessaie. » — elle relit et range. |
| La vallée | SF7 : « la portée est trop courte » ; SF12 : « ça passe, mais tu gaspilles le temps d'antenne » ; puis le bon SF. |
| La tempête | Elle coupe la racine (le seul voisin du camp) : la cible est isolée, le jeu le dit et explique comment recommencer (`mesh-coupe -r`, `ondes defi`). Au second essai elle lit le chemin et réussit. |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout sauf aux trous `?` (longueur, onde qui traverse, nombre de réseaux, règle, bandes, SF, messages, choix, nœuds à couper, cible du SOS), voulus : le jeu dit que c'est un trou et ce qu'il faut lire. |
| L'exploit | Le SOS passe malgré trois nœuds coupés : `ondes.onde` gagné, rencontres favorisées des variantes réservées (`zapiot:orage`, `ventouzar:orage`, `cyclonaute:orage`). |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 20 sur 21 acceptées. |
| Refusée | `type rtl_test` à l'étape « Les outils de la radio logicielle » (`command -v` et `which` passent). Mineur, noté (ON9). |

## 2. Problèmes trouvés, classés

### Critiques — aucun ouvert

| # | Problème | État |
|---|---|---|
| ON1 | L'annonce du monde ne partait jamais : la Tour s'ouvre après des **leçons** (P7, M2) et non après un chapitre, or l'annonce n'était vérifiée qu'à la fin d'un chapitre. | `lecons_qui_ouvrent()` : l'annonce est vérifiée aussi à la fin de ces leçons (PC `histoire.finir_lecon`, Android `Histoire.finirLecon`). |
| ON11 | (validation complète) Les quatre nouveaux exercices des Ponts des Nombres (fréquence, puissances de 10, longueur d'onde, temps d'émission) n'existaient que sur PC : sur le téléphone, `maths frequence` aurait fait planter l'appli. | Mêmes générateurs dans `Maths.kt` (mêmes tirages), vérifiés par les vecteurs communs (`tests/jvm/Programme.kt`). |
| ON2 | La tempête en trois étapes (« coupe 1 », « coupe 2 », « coupe 3 ») cassait après un redémarrage du jeu et donnait des indices trompeurs (« cette commande marche aussi »). | Une seule étape « coupe 3 nœuds du chemin » (comptée dans le carnet depuis le dernier `ondes defi`), avec un indice de progression (« 2 sur 3 : lis le nouveau chemin… ») ; cible isolée et nœud hors chemin expliqués. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| ON3 | Sans `-f`, `nmcli dev wifi list` affiche les noms et adresses des réseaux des voisins. | La leçon montre `nmcli -f CHAN,FREQ,SIGNAL dev wifi list --rescan no` ; si l'enfant tape la version sans `-f`, la créature explique pourquoi on ne recopie pas les noms (`on.garde.noms`) ; le jeu ne relit que la colonne FREQ pour vérifier. |
| ON4 | L'onde dessinée était trop clairsemée pour LoRa (on ne voyait pas la vague). | Tracé continu, PC (`grille_onde`) et téléphone (`OndesDessin.vague`). |
| ON5 | Le maillage affichait le mauvais nœud dans « par … ». | Le chemin montre le saut précédent réel ; vecteurs communs Python/Kotlin. |
| ON6 | (Ponts des Nombres) `maths les 0 et les 1` menait au temps d'émission au lieu du binaire : le mot-clé « 1 » (« 1 pourcent ») attrapait la question. | Mots-clés du temps d'émission sans nombres ni « on », dans les 14 langues. |

### Mineurs (notés)

| # | Constat |
|---|---|
| ON7 | Le camp n'a qu'un voisin (la racine) : le couper isole tout. C'est voulu (« Attention aux nœuds dont tout dépend… ») et expliqué, mais les trois enfants simulés l'ont fait une fois. |
| ON8 | Sur une machine sans Wi-Fi (VM, conteneur, CI), `ondes canaux` montre une ville **EXEMPLE** inventée (dit à l'écran) et le compte des réseaux est raconté. |
| ON9 | `type rtl_test` n'avance pas l'étape alors que `command -v` et `which` passent. À regarder (probablement la façon dont le shell de test rapporte `type`). |
| ON12 | Les variantes réservées à la Tour (`zapiot:orage`, `ventouzar:orage`, `cyclonaute:orage`) n'apparaissent plus avant l'exploit : le tirage des Célestes sans attirance passe de 6,7 % à 7,3 % dans le test d'attirance (identique PC / Android ; la valeur attendue de `tests/jvm/RetoursEnfants.kt` est mise à jour). |
| ON13 | Le test du site (`site/test/test.mjs`, non modifié) échoue 3 fois le dimanche (calcul de la « Star de la semaine » qui tombe sur la semaine suivante) ; rejoué avec la date décalée de deux jours : 179 / 179. Indépendant de la Tour. |
| ON10 | Les émojis des biomes (🔥 ❄ ☠…) ne s'affichent pas dans la police des captures PC ; ils s'affichent dans un vrai terminal. |

## 3. Ce qui marche bien

- **Écouter est libre, émettre est réglementé ; le jeu n'émet jamais lui-même** : aucune commande montrée n'émet, ne
  connecte, n'appaire ni ne change la radio ; `test_ondes.py` vérifie qu'aucune leçon ne contient d'adresse réseau,
  de `sudo`, de `rfkill block`, de `pip install` ni de balayage actif, dans les 14 langues.
- **Les voisins sont protégés** : vérification sur des quantités anonymes (canal, bande, nombre de réseaux) ; aucun
  SSID, BSSID ni MAC dans le carnet, la sauvegarde ou ce qui part vers le site ; la leçon explique pourquoi.
- **Avec un adulte, jamais obligatoire** : W5 (Meshtastic, 868 MHz, 25 mW, 1 %) et W6 (radio logicielle, réception
  seule) sont racontés si le matériel manque ; aucune marque, aucun lien d'achat, aucun prix ; `pip install` seulement
  expliqué ; les avions et capteurs du jeu sont fictifs, et l'on garde la température sans l'identifiant.
- **Le maillage du Terminaworld** : les machines du Port deviennent des nœuds radio ; on voit l'inondation saut par
  saut, le message qui prend un autre chemin quand un nœud tombe, et la tempête comme vrai petit problème de graphes.
- Les Ponts des Nombres (fréquence, puissances de 10, longueur d'onde, temps d'émission, pourcentages, division) sont
  proposés sans jamais bloquer ; sur le téléphone, les calculs se font en entiers (mm, µs) puisque `bc` manque.

## 4. Ce qui reste

- Les illustrations (prompts dans `outils/ondes/prompts_illustrations.md`, aucune image générée) ; en attendant, la
  tour, l'onde, le mur, la règle, la vallée et le maillage sont dessinés (PC en caractères, téléphone `OndesDessin`).
- Les vraies radios (Wi-Fi, Bluetooth, LoRa, clé SDR) n'ont été vues que par des doublures.
- ON9 (`type rtl_test`).

## 5. Rejouer

```
python3 pc/outils/sim_ondes.py               # les trois
python3 pc/outils/sim_ondes.py lea           # une seule
python3 pc/outils/test_ondes.py              # la Tour sur PC (49 vérifications)
python3 pc/outils/vecteurs_ondes.py --verifier
# Android : tests/jvm/Ondes.kt (28 vérifications), voir outils/tout.sh jvm Ondes
```
