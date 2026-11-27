# 🎛 Contrôle

*Le Poste de Contrôle : administrer un système Linux de A à Z*

| | |
|---|---|
| **Durée** | environ 25 min (3 leçons, 6 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `id`, `cut`, `systemctl`, `journalctl`, `crontab`, `apt` |
| **Compétences gagnées** | Concierge, Régisseur, Horloger |

## Objectifs

- **Les habitants** : qui suis-je, et dans quels groupes ? (avec `id`, `cut`)
- **Les services** : quels services sont en panne ? (avec `systemctl`, `journalctl`)
- **Les tâches planifiées** : quelles tâches reviennent toutes seules ? (avec `crontab`, `apt`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Contrôle » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Les habitants → compétence « Concierge »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Qui suis-je, et dans quels groupes ? | `id` | uid = ton numéro, groupes = tes clés. sudo = le groupe des administrateurs. |
| 2 | Qui d'autre habite la machine ? | `cut -d: -f1 /etc/passwd` | Beaucoup d'« utilisateurs » sont des services : chacun dans sa chambre. |

### 2. Les services → compétence « Régisseur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quels services sont en panne ? | `systemctl --failed` | Un service = un programme qui tourne en fond (serveur web, impression…). |
| 2 | Lis les dernières erreurs du journal système. | `journalctl -p err -n 20` | Le journal raconte tout ce qui se passe : le premier réflexe d'un admin en cas de panne. |

### 3. Les tâches planifiées → compétence « Horloger »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quelles tâches reviennent toutes seules ? | `crontab -l` | cron lance des commandes à heure fixe : « 0 3 * * * » = tous les jours à 3 h. |
| 2 | Des mises à jour en attente ? | `apt list --upgradable` | Mettre à jour = boucher les failles. C'est la règle n°1 de la sécurité. |

## Questions pour vérifier

- Que fait la commande `id` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cut` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `systemctl` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `journalctl` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `crontab` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `apt` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
