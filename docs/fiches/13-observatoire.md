# 🔭 Observatoire

*L'Observatoire de l'IA : comment une IA apprend, se trompe, et comment la piloter*

| | |
|---|---|
| **Durée** | environ 20 min (4 leçons, 5 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `grep`, `tr`, `sort`, `cat` |
| **Compétences gagnées** | Statisticien, Devin, Détecteur de biais, Pilote d'IA |

## Objectifs

- **Apprendre en comptant** : une IA apprend sur des exemples. Combien d'avis positifs ? (avec `grep`, `tr`)
- **Prédire le mot suivant** : après « le chat », quel mot vient le plus souvent ? (avec `grep`)
- **Quand l'IA se trompe** : les exemples d'entraînement sont-ils équilibrés ? Compte. (avec `sort`)
- **Piloter un assistant** : lis cette consigne bien écrite pour un assistant IA. (avec `cat`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Observatoire » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Apprendre en comptant → compétence « Statisticien »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/ia/avis.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Une IA apprend sur des exemples. Combien d'avis positifs ? | `grep -c positif monde/ia/avis.txt` | 5 positifs. |
| 2 | Quels mots reviennent le plus ? Compte-les tous. | `tr ' ' '\n' < monde/ia/avis.txt \| sort \| uniq -c \| sort -rn \| head` | « j'adore » est lié aux avis positifs : un modèle apprend ces liens, sur des milliards de textes. |

### 2. Prédire le mot suivant → compétence « Devin »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/ia/texte.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Après « le chat », quel mot vient le plus souvent ? | `grep -o 'le chat [a-z]*' monde/ia/texte.txt \| sort \| uniq -c \| sort -rn` | « dort » (3 fois) : un modèle de langue prédit le mot le plus probable. Il ne « sait » pas, il calcule. |

### 3. Quand l'IA se trompe → compétence « Détecteur de biais »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/ia/biais.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Les exemples d'entraînement sont-ils équilibrés ? Compte. | `sort monde/ia/biais.txt \| uniq -c` | 4 « docteur : il » pour 1 « elle » : une IA entraînée là-dessus croira que les docteurs sont des hommes. C'est un biais : l'IA répète les déséquilibres de ses données. |

### 4. Piloter un assistant → compétence « Pilote d'IA »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/ia/consigne.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Lis cette consigne bien écrite pour un assistant IA. | `cat monde/ia/consigne.txt` | Rôle, contexte, tâche, format, vérification : une bonne consigne. Et toujours vérifier ce que l'IA répond ! |

## Questions pour vérifier

- Que fait la commande `grep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `tr` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sort` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cat` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
