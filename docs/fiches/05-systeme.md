# ⚙ Système

*Surveiller et maîtriser la machine*

| | |
|---|---|
| **Durée** | environ 30 min (3 leçons, 7 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `whoami`, `ps`, `df`, `du`, `sleep`, `jobs`, `kill` |
| **Compétences gagnées** | Vigie, Intendant, Chasseur |

## Objectifs

- **La vigie** : qui est aux commandes de cette machine ? (avec `whoami`, `ps`)
- **L'intendant** : reste-t-il de la place dans le grenier (le disque) ? (avec `df`, `du`)
- **Le chasseur** : lâche un programme qui dort en arrière-plan. (avec `sleep`, `jobs`, `kill`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Système » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. La vigie → compétence « Vigie »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Qui est aux commandes de cette machine ? | `whoami` | C'est toi ! Ton nom d'utilisateur. |
| 2 | Qui tourne en ce moment dans la machine ? | `ps aux` | Chaque ligne est un programme vivant, avec son numéro (PID). |

### 2. L'intendant → compétence « Intendant »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Reste-t-il de la place dans le grenier (le disque) ? | `df -h` | -h = « human » : des tailles lisibles (Go, Mo). |
| 2 | Combien pèse notre terrain de jeu ? | `du -sh ~/terrain_terminagotchi` | Pratique pour trouver ce qui remplit le disque. |

### 3. Le chasseur → compétence « Chasseur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Lâche un programme qui dort en arrière-plan. | `sleep 300 &` | & = « en arrière-plan » : le terminal reste libre. |
| 2 | Repère-le. | `jobs` | Le voilà, avec son numéro. |
| 3 | Chasse-le ! | `kill %1` | Programme arrêté. Utile quand l'un d'eux est bloqué ! |

## Questions pour vérifier

- Que fait la commande `whoami` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ps` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `df` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `du` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sleep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `jobs` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
