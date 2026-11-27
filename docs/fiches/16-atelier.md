# 🤖 Atelier

*L'Atelier : Raspberry Pi, robots, électronique embarquée*

| | |
|---|---|
| **Durée** | environ 20 min (2 leçons, 5 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `cat`, `echo`, `for` |
| **Compétences gagnées** | Électronicien, Capteur |

## Objectifs

- **Allumer une LED** : sur un Raspberry Pi, une broche (GPIO) est un simple fichier ! Regarde l'état de la LED branchée sur la broche 17. (avec `cat`, `echo`, `for`)
- **Lire un capteur** : lis le capteur de température. (avec `cat`, `echo`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Atelier » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Allumer une LED → compétence « Électronicien »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/atelier/gpio17/value`, `~/terrain_terminagotchi/monde/atelier/gpio17/direction`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Sur un Raspberry Pi, une broche (GPIO) est un simple fichier ! Regarde l'état de la LED branchée sur la broche 17. | `cat monde/atelier/gpio17/value` | 0 = éteinte. Sous Linux, « tout est fichier », même une broche électrique. |
| 2 | Allume-la : écris 1 dans le fichier. | `echo 1 > monde/atelier/gpio17/value` | 💡 Allumée ! Sur un vrai Pi, le courant passe dans la LED. |
| 3 | Fais-la clignoter 3 fois. | `for i in 1 2 3; do echo 1 > monde/atelier/gpio17/value; sleep 1; echo 0 > monde/atelier/gpio17/value; sleep 1; done` | Une LED qui clignote : le « Bonjour le monde » de l'électronique. |

### 2. Lire un capteur → compétence « Capteur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/atelier/capteur/temperature`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Lis le capteur de température. | `cat monde/atelier/capteur/temperature` | 21500 = 21,5 °C en millidegrés, comme dans /sys/class/thermal sur un vrai Pi. |
| 2 | Convertis en degrés. | `echo $(( $(cat monde/atelier/capteur/temperature) / 1000 ))` | Un robot fait ça en boucle : lire un capteur, calculer, agir (moteur, LED…). |

## Questions pour vérifier

- Que fait la commande `cat` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `for` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
