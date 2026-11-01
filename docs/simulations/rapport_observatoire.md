# Simulation : trois enfants visitent l'Observatoire de l'IA (septième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_observatoire.py` (PC, rejouable à chaque
test et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Observatoire.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_guilde.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. L'Observatoire est ouvert d'avance
comme dans l'arbre du Carrefour (niveaux 0 à 6 du tronc commun).

**Aucune vraie IA, aucun réseau.** L'assistant, les devineurs et les agents sont le code du jeu. Les proxys pointent
vers 127.0.0.1:9 ; `sudo`, `curl` et `wget` sont des doublures qui refusent et notent qu'on les a appelées.
`wc`, `sort`, `diff`, `cut`, `awk`, `tr`, `paste`, `uniq`, `sed`, `chmod`, `git diff` et `sh` sont les vrais.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** :
- la créature oubliée, lue dans la sortie de `diff` (la ligne avec `<`) ;
- la proposition dangereuse, lue dans le journal de l'agent (`rm -rf`, `sudo`) ;
- le piège, lu dans `cerveau.txt` ;
- les 2 réponses fausses, en comparant avec ses propres vérifications (`wc -l`, `echo $((17 % 5))`, le comptage des
  mots, `explique ls`, `explique rm`) ;
- les cartes des quiz (perroquet, confier, nuances, découpe, consigne), lues à l'écran.

**Android.** `tests/jvm/Observatoire.kt` refait la traversée ob0 → ob9 avec les commandes du téléphone : 27 vérifications.
- Pas de git ni de Ctrl+C sur le téléphone : `diff` remplace `git diff`, `agent stop` remplace Ctrl+C, `export` et
  `echo ${#CLE_API}` vont sur la même ligne. C'est dit à l'écran.
- Python et Kotlin donnent les mêmes résultats sur les vecteurs communs (`donnees/observatoire/vecteurs.json`) :
  consignes comprises, tri oublieux, devineur (cerveau, votes, scores), mots et paires, phrases, réponses fausses,
  quiz, équipe.

**Limites honnêtes.**
- Le rejeu bash complet de l'histoire ne tourne qu'en CI (la machine de test n'a pas `ping`, `ss`, `ip`). La partie
  Observatoire du rejeu a été jouée ici aussi, et elle est verte.
- Ctrl+C est envoyé par la simulation (SIGINT) ; il n'a pas été tapé au clavier par un vrai enfant.
- Les textes des 13 autres langues sont des traductions de Claude, non relues par des locuteurs.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « réponses fausses » |
|---|---|---|---|---|
| Léa, 7 ans, se trompe d'abord | Voir le détail ci-dessous (fautes typiques), puis lit et corrige | 112 | oui, ob0 → ob9 | oui |
| Inès, 12 ans, recopie | Recopie la commande verte (« ? » compris), puis lit l'écran | 98 | oui | oui |
| Hugo, 15 ans, ses variantes | Ses propres variantes de commande, toutes justes | 84 | oui | oui, 23 variantes justes acceptées sur 23 |

Les fautes de Léa :
- `Ls`, `Cat` avec une majuscule ;
- la consigne « Fais un truc » ;
- `assistant mission.txt` sans `>` ;
- « Pikachu » comme créature oubliée ; `sh test.sh` sans refaire le tri ;
- `chmod 644 .env` ;
- **accepter** la proposition dangereuse de l'agent ; valider avant d'avoir relu ;
- laisser tourner l'agent jusqu'à sa limite de temps ;
- « lieu » pour le piège ; « le devineur aime le Feu » pour le biais ;
- un mot qui n'existe pas (`devine-mot suite xyz`) ;
- les mauvaises réponses fausses (`1 2`) ; tout confier (`c c c c c c`) ; tout « vrai » ;
- le mauvais ordre (`1 2 3`) ; la consigne dangereuse (avec sudo) ;
- `sudo rm -rf copies` quand l'agent Copieur s'emballe ;
- le bilan trop tôt.

Les variantes de Hugo :
- `less -FX`, `head`, `head -n 5` ;
- `diff <(sort creatures.txt) tri.txt`, `./test.sh`, `wc -l tri.txt creatures.txt` ;
- `grep -n CLE_API …`, `sed -i.bak`, `printf … > .env`, `chmod u=rw,go= .env`, `printf '.env\n' >> .gitignore` ;
- `git diff --stat`, `diff -u` ;
- `awk … | sort | uniq -c | sort -rn`, `cut -d' ' -f3` ;
- `tr -s ' ' '\n'`, `paste -d' ' mots.txt <(tail -n +2 mots.txt)` ;
- `bash tests.sh`, `touch STOP`, `ls copies/ | wc -l`, `wc -l liste.txt | cut -d' ' -f1 > compte.txt` ;
- une autre consigne claire (« Liste les créatures Eau de creatures.txt »).

Ce qui vaut pour les trois enfants :
- aucune étape n'a été validée par une commande qui a échoué ;
- rien n'a été écrit hors du terrain et de `~/.terminagotchi` ;
- **aucune proposition dangereuse n'a été exécutée** : le terrain est intact après « accepter » ;
- aucun téléchargement tenté ; `sudo` n'est jamais passé (la doublure a refusé le `sudo rm -rf copies` de Léa) ;
- Ctrl+C a arrêté l'agent qui tourne en rond ; l'arrêt d'urgence a arrêté l'équipe.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : « Fais un truc » → l'assistant dit ce qui manque (quoi, quel fichier) ; 20 contre 19 lignes ; la ligne `<` du diff ; le devineur qui se trompe « sûr de lui » ; « que du chaud ! » ; « ça sonne comme l'histoire… mais est-ce vrai ? ». |
| Accepter le danger | Le jeu ne lance rien, et dit : « Tu as voulu ACCEPTER l'action dangereuse ! Le jeu ne la lance jamais, mais un vrai agent, si. Refuse-la : agent refuse N. » |
| `sudo rm -rf copies` | « ⛔ sudo, rm -rf ~ ou chmod -R 777 peuvent tout casser. Dans l'Observatoire, ces commandes se REFUSENT : jamais sans un adulte. » Puis elle tape `agent stop`. |
| `sh test.sh` sans refaire le tri | Avant : seul le message ÉCHEC du test. Maintenant : « Le test veut toutes les lignes, triées : sort creatures.txt > tri.txt » (OB6). |
| Les quiz | Chaque mauvaise réponse a une phrase qui fait relire (« Peut-on compter les invités avant d'avoir une liste sans doublons ? », « Regarde cerveau.txt… »). |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout, sauf aux trous `?` (oubliée, refus, piège, biais, mots, réponses fausses, quiz). C'est voulu : le jeu dit que c'est un trou (« sans le point d'interrogation ») et ce qu'il faut lire. |
| L'exploit | `assistant fausses N N` juste : `observatoire.fausses` est gagné, et les variantes réservées deviennent des rencontres favorisées. Ce sont des variantes **existantes** des types Ciel et Glace : `seraphibou:cosmique`, `zyeuton:brume`, `mutaloupe:cristal`. |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 23 sur 23 acceptées (après la correction OB5). |
| `touch STOP` au lieu de `agent stop` | Accepté : c'est le même arrêt d'urgence (le fichier STOP). |
| `wc -l liste.txt \| cut …` | Accepté : le test vérifie le nombre dans `compte.txt`, pas la commande. |

## 2. Problèmes trouvés, classés

### Critiques — aucun ouvert

| # | Problème | État |
|---|---|---|
| OB4 | Après « agent accepte N » (la proposition dangereuse), le jeu disait « Ta commande marche aussi, bravo ! ». Féliciter l'acceptation du danger est le contraire de la leçon. | Indice dédié `ob.indice.accepte` (14 langues), prioritaire. Le danger n'est toujours jamais lancé. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| OB1 | O8 : `wc -l exemples.txt` était proposé depuis le mauvais dossier (le fichier est dans `devineur/`). | L'étape ob8.2 se fait dans `devineur` ; la question dit `devineur/exemples.txt`. |
| OB2 | Les cartes des quiz (découpe, consigne, perroquet) n'étaient pas à l'écran au moment de répondre. | `observatoire equipe` montre les cartes de la découpe, la découpe juste montre celles de la consigne, `devine-mot phrase` montre celles du perroquet. |
| OB3 | Une mauvaise réponse au biais ne remontrait pas les choix. | Les choix sont remontrés avec l'explication. |
| OB5 | `diff <(sort creatures.txt) tri.txt` (Hugo) était refusé : la substitution `<( )` était prise pour un chemin de fichier. | `verif.py` ignore `<( … )` et `>( … )` quand il cherche les fichiers manquants. |
| OB6 | `sh test.sh` seul, à l'étape du tri juste : aucune explication du jeu. | L'indice `ob.indice.tri` est aussi donné après `sh test.sh`, `bash test.sh` ou `./test.sh` (PC et Android). |
| OB12 | Sur le téléphone, en arabe et en ourdou, les mots des données (familles, lieux, types, réponses) recevaient les marques de sens d'écriture ajoutées à l'affichage : le devineur n'apprenait rien et l'assistant ne trouvait pas le type (vu par les vecteurs communs). | `Observatoire.mot()` enlève ces marques ; les vecteurs Python ↔ Kotlin sont identiques dans les 14 langues. |
| OB13 | En chinois et en japonais, 7 textes « pour les grands » étaient trop courts (moins de 20 signes, règle G-32). | Complétés. |
| OB7 | `cd …/equipe` avant `agent equipe` (montré « cd … puis agent equipe ») recevait « Ta commande marche aussi, bravo ! Mais… ». | Un `cd` n'est plus jamais pris pour une « variante » d'une étape qui n'est pas un `cd` (`histoire.py` et `Histoire.kt`, pour tous les mondes). |

### Mineurs (notés)

| # | Constat |
|---|---|
| OB8 | En chinois et en japonais, le devineur de mots compte des **caractères** (ces langues n'ont pas d'espaces). C'est juste pour le principe, mais ce n'est pas dit à l'écran. |
| OB9 | Les émojis (🔭, 🤖…) ne s'affichent pas dans la police des captures PC ; ils s'affichent dans un vrai terminal. |
| OB10 | Les variantes réservées à l'Observatoire n'apparaissent plus avant l'exploit : dans le test d'attirance, les Célestes attirés passent de 28,7 % à 28,0 % (identique PC / Android ; valeur attendue de `tests/jvm/RetoursEnfants.kt` mise à jour). |
| OB11 | Les lettres des quiz restent v/f (vrai / faux) et c/g (confier / garder) dans toutes les langues ; chaque langue l'explique à l'écran (« v (vrai) ou f (faux) »). |

## 3. Ce qui marche bien

- **Aucune vraie IA, et c'est dit.** Chaque palier rappelle que les robots sont de petits programmes du jeu ; « les
  vraies IA sont bien plus grandes, mais le principe est juste ». Aucune marque citée.
- **Le danger n'est jamais lancé.** Les propositions `rm -rf …` et `sudo chmod -R 777 …` sont du texte avec un chemin
  « … » qui ne vise rien. Même acceptées, elles ne font rien, et l'enfant apprend à les refuser.
- **Les secrets restent secrets.** La clé est un exemple qui ne marche nulle part ; elle ne va jamais dans la
  sauvegarde ; `observatoire cle` n'en montre que le début.
- **Des chiffres vrais.** Le devineur apprend sur 20 vraies créatures, se trompe sur la 21e (Cauchemarre) ; le biais
  du volcan donne 1 sur 5, puis 5 sur 5 ; le devineur de mots compte les vraies phrases de l'histoire, dans la
  langue du joueur.
- **L'esprit critique, sans peur.** Vérifier, garder ses secrets, deepfakes, droits d'auteur, énergie : des phrases
  nuancées, et « si tu as un doute, demande à un adulte ».
- **Les Ponts des Nombres** (effectifs, fréquences, probabilités) sont proposés sans jamais bloquer.

## 4. Ce qui reste

- Les illustrations : prompts dans `outils/observatoire/prompts_illustrations.md` (B11, vignette, C1, C3, E12, E17),
  aucune image générée. En attendant, la coupole, les votes, les copies et la lunette sont dessinés : en caractères
  sur PC, avec `ObservatoireDessin` sur le téléphone.
- Une relecture des traductions par des locuteurs.
- OB8 : dire (ou non) à l'écran qu'en chinois et en japonais on compte des caractères.

## 5. Rejouer

```
python3 pc/outils/sim_observatoire.py              # les trois
python3 pc/outils/sim_observatoire.py lea          # une seule
python3 pc/outils/test_observatoire.py             # l'Observatoire sur PC (67 vérifications)
python3 pc/outils/vecteurs_observatoire.py --verifier
python3 pc/outils/capture_observatoire.py <dossier> # les captures PC
# Android : tests/jvm/Observatoire.kt (27 vérifications), voir outils/tout.sh jvm Observatoire
```
