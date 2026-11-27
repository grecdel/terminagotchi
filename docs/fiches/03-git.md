# ⏳ Git

*La Bibliothèque du Temps : git, remonter le temps de ses fichiers (git requis)*

| | |
|---|---|
| **Durée** | environ 35 min (3 leçons, 9 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `git`, `cd`, `echo` |
| **Compétences gagnées** | Archiviste, Mémoire, Chronomancien |

## Objectifs

- **Mon premier dépôt** : depuis le terrain, crée un carnet magique qui se souvient de tout. (avec `git`, `cd`)
- **Premier souvenir** : écris la première page du journal. (avec `echo`, `git`)
- **Voyage dans le temps** : ajoute une ligne au journal. (avec `echo`, `git`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Git » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Mon premier dépôt → compétence « Archiviste »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Depuis le terrain, crée un carnet magique qui se souvient de tout. | `git init carnet` | Un dépôt git ! Le dossier caché .git garde toute l'histoire. |
| 2 | Entre dans le carnet. | `cd carnet` | Nous y sommes. |
| 3 | Demande-lui comment il va. | `git status` | git status : la commande que les pros tapent 100 fois par jour. |

### 2. Premier souvenir → compétence « Mémoire »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Écris la première page du journal. | `echo "jour 1" > journal.txt` | Le carnet a vu un nouveau fichier… mais ne le garde pas encore. |
| 2 | Prépare cette page pour le souvenir. | `git add journal.txt` | add = mettre la page dans l'enveloppe. |
| 3 | Scelle le souvenir ! | `git commit -m "premier souvenir"` | Un commit = une photo de tes fichiers à cet instant. Pour toujours. *Astuce : Si git demande ton nom : git config --global user.name "Ton nom" (idem user.email)* |

### 3. Voyage dans le temps → compétence « Chronomancien »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Ajoute une ligne au journal. | `echo "jour 2" >> journal.txt` | Le journal a changé… |
| 2 | Qu'est-ce qui a changé depuis le souvenir ? | `git diff` | + en vert = ajouté, - en rouge = enlevé. |
| 3 | Remonte le fil de nos souvenirs. | `git log` | Chaque souvenir a un identifiant unique. *Astuce : Tape q pour quitter l'affichage.* |

## Questions pour vérifier

- Que fait la commande `git` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cd` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
