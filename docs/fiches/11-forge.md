# 🔨 Forge

*La Forge : programmer, son premier jeu, son site web, du son*

| | |
|---|---|
| **Durée** | environ 25 min (3 leçons, 6 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `cat`, `python3`, `nano`, `echo` |
| **Compétences gagnées** | Créateur de jeux, Tisseur de web, Sonneur |

## Objectifs

- **Mon premier jeu** : voici le code d'un petit jeu. Lis-le ! (avec `cat`, `python3`, `nano`)
- **Mon premier site** : écris une page web. (avec `echo`, `python3`)
- **Faire du son** : un son = une vague de nombres. Lance le programme qui fabrique un La (440 Hz). (avec `python3`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Forge » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Mon premier jeu → compétence « Créateur de jeux »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/forge/devine.py`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Voici le code d'un petit jeu. Lis-le ! | `cat monde/forge/devine.py` | random, input, if/else : 3 briques et c'est un jeu. |
| 2 | Joue ! | `python3 monde/forge/devine.py` | Tu as lancé un programme Python écrit en 8 lignes. |
| 3 | Rends-le plus dur : change BORNE = 3 en BORNE = 10. | `nano monde/forge/devine.py` | Tu as modifié un jeu : c'est comme ça que tout programmeur commence. *Astuce : Dans nano : modifie, puis Ctrl+O, Entrée (enregistrer) et Ctrl+X (quitter).* |

### 2. Mon premier site → compétence « Tisseur de web »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Écris une page web. | `echo '<h1>Le site de ma créature</h1>' > monde/forge/index.html` | <h1> = un grand titre. Le HTML range le texte dans des balises. |
| 2 | Allume un petit serveur web, ouvre http://localhost:8000 dans le navigateur, puis Ctrl+C pour l'éteindre. | `python3 -m http.server 8000 -d monde/forge` | Ton ordinateur est devenu un serveur web ! Un vrai site, c'est ça, sur une machine allumée en permanence. |

### 3. Faire du son → compétence « Sonneur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/forge/bip.py`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Un son = une vague de nombres. Lance le programme qui fabrique un La (440 Hz). | `python3 monde/forge/bip.py` | 8000 mesures par seconde d'une sinusoïde : voilà un fichier son, fabriqué par toi. |

## Questions pour vérifier

- Que fait la commande `cat` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `python3` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `nano` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
