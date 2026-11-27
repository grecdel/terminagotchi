# 📊 Données

*La Salle des Données : trier, compter, chercher, les bases de données (SQL)*

| | |
|---|---|
| **Durée** | environ 25 min (3 leçons, 6 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `head`, `wc`, `cut`, `sort`, `sqlite3` |
| **Compétences gagnées** | Archiviste des données, Trieur, Maître du SQL |

## Objectifs

- **Le tableau** : un fichier CSV : un tableau en texte. Regarde le début. (avec `head`, `wc`)
- **Trier et regrouper** : combien de créatures par famille ? (colonne 2) (avec `cut`, `sort`)
- **La base de données** : range le tableau dans une vraie base de données. (avec `sqlite3`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Données » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Le tableau → compétence « Archiviste des données »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/donnees/creatures.csv`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Un fichier CSV : un tableau en texte. Regarde le début. | `head -n 5 monde/donnees/creatures.csv` | Une ligne = une créature, les virgules séparent les colonnes. |
| 2 | Combien de lignes ? | `wc -l monde/donnees/creatures.csv` | 15 lignes : l'en-tête + 14 créatures. |

### 2. Trier et regrouper → compétence « Trieur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Combien de créatures par famille ? (colonne 2) | `cut -d, -f2 monde/donnees/creatures.csv \| sort \| uniq -c` | cut découpe une colonne, sort trie, uniq -c compte : un vrai rapport. |
| 2 | Les 3 plus grandes créatures (colonne 4, en nombres, à l'envers). | `sort -t, -k4 -n -r monde/donnees/creatures.csv \| head -n 3` | Chaosmère, 12 m ! -t, = séparateur, -k4 = colonne 4, -n = nombres. |

### 3. La base de données → compétence « Maître du SQL »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Range le tableau dans une vraie base de données. | `sqlite3 monde/donnees/base.db ".import --csv monde/donnees/creatures.csv creatures"` | Une base de données : des tableaux qu'on interroge avec le langage SQL. *Astuce : Si sqlite3 manque : sudo apt install sqlite3* |
| 2 | Pose une question en SQL : combien par famille ? | `sqlite3 monde/donnees/base.db "SELECT famille, COUNT(*) FROM creatures GROUP BY famille;"` | SELECT … FROM … GROUP BY : la langue de presque toutes les bases du monde. |

## Questions pour vérifier

- Que fait la commande `head` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `wc` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cut` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sort` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sqlite3` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
