# 🧪 Scripts

*Automatiser et créer TES commandes*

| | |
|---|---|
| **Durée** | environ 30 min (3 leçons, 7 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `echo`, `sh`, `chmod`, `alias`, `miam`, `source` |
| **Compétences gagnées** | Cuistot, Inventeur, Créateur |

## Objectifs

- **Ma première recette** : depuis le terrain, écris une recette dans mon nid. (avec `echo`, `sh`)
- **Ma propre commande** : rends la recette exécutable. (avec `chmod`, `alias`, `miam`)
- **Pour toujours** : ta commande disparaîtra à la fermeture du terminal. Rends-la éternelle ! (avec `echo`, `source`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Scripts » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Ma première recette → compétence « Cuistot »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Depuis le terrain, écris une recette dans mon nid. | `echo 'echo "Miam !"' > nid/miam.sh` | Un script = une liste de commandes rangée dans un fichier. |
| 2 | Cuisine la recette ! | `sh nid/miam.sh` | Le script a parlé ! Tu viens de programmer. |

### 2. Ma propre commande → compétence « Inventeur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Rends la recette exécutable. | `chmod +x nid/miam.sh` | x = exécutable : c'est maintenant un programme. |
| 2 | Invente une commande à toi : « miam ». | `alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'` | Tu viens de créer une commande qui n'existait pas ! |
| 3 | Essaie-la ! | `miam` | MIAM ! C'est la meilleure commande du monde. |

### 3. Pour toujours → compétence « Créateur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Ta commande disparaîtra à la fermeture du terminal. Rends-la éternelle ! | `echo "alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'" >> ~/.bashrc` | Elle est gravée dans ta configuration. *Astuce : ~/.bashrc est lu à chaque ouverture du terminal.* |
| 2 | Recharge ta configuration. | `source ~/.bashrc` | Désormais, tes propres inventions me nourrissent ×3 ! |

## Questions pour vérifier

- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sh` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `chmod` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `alias` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `miam` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `source` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
