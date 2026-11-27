# 🛠 Guilde

*La Guilde des Bâtisseurs Libres : open source, contribuer, compiler*

| | |
|---|---|
| **Durée** | environ 30 min (3 leçons, 7 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `head`, `grep`, `cp`, `sed`, `diff`, `cc`, `./monde/guilde/bonjour` |
| **Compétences gagnées** | Compagnon, Contributeur, Fondeur |

## Objectifs

- **Les règles du libre** : chaque projet libre a une licence. Lis le début de celle-ci. (avec `head`, `grep`)
- **Ma première contribution** : il y a une faute dans le projet. Garde d'abord une copie de l'original. (avec `cp`, `sed`, `diff`)
- **Compiler** : le code C doit être traduit en langage machine : compile-le. (avec `cc`, `./monde/guilde/bonjour`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Guilde » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Les règles du libre → compétence « Compagnon »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/guilde/LICENSE`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Chaque projet libre a une licence. Lis le début de celle-ci. | `head -n 3 monde/guilde/LICENSE` | MIT : une des licences les plus simples. |
| 2 | Que permet-elle ? Cherche le mot « use ». | `grep -i use monde/guilde/LICENSE` | Utiliser, copier, modifier, partager : les 4 libertés du logiciel libre. |

### 2. Ma première contribution → compétence « Contributeur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/guilde/projet/bonjour.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Il y a une faute dans le projet. Garde d'abord une copie de l'original. | `cp monde/guilde/projet/bonjour.txt monde/guilde/projet/bonjour.orig` | L'original est à l'abri. |
| 2 | Corrige « Bonjur » en « Bonjour ». | `sed -i 's/Bonjur/Bonjour/' monde/guilde/projet/bonjour.txt` | Corrigé ! |
| 3 | Fabrique le patch : la recette de ta correction. | `diff -u monde/guilde/projet/bonjour.orig monde/guilde/projet/bonjour.txt` | - l'ancienne ligne, + la nouvelle : c'est ce qu'on propose à un projet (une « pull request »). Terminagotchi lui-même est libre : tu peux y contribuer ! |

### 3. Compiler → compétence « Fondeur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/guilde/bonjour.c`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Le code C doit être traduit en langage machine : compile-le. | `cc monde/guilde/bonjour.c -o monde/guilde/bonjour` | Le compilateur a transformé ton texte en programme. *Astuce : Pas de compilateur ? sudo apt install gcc* |
| 2 | Lance ton programme compilé. | `./monde/guilde/bonjour` | Linux, Firefox, Python… tous compilés à partir de code ouvert à tous. |

## Questions pour vérifier

- Que fait la commande `head` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `grep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cp` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sed` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `diff` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cc` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
