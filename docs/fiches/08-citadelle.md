# 🛡 Citadelle

*La Citadelle : cybersécurité défensive, attaques simulées, boîtes à percer puis réparer*

| | |
|---|---|
| **Durée** | environ 40 min (4 leçons, 10 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `grep`, `ls`, `chmod`, `sha256sum`, `echo`, `rm` |
| **Compétences gagnées** | Guetteur, Bâtisseur de remparts, Vérificateur, Hacker éthique |

## Objectifs

- **Le guet** : quelqu'un essaie d'entrer dans la Citadelle ! Cherche les échecs de connexion dans le journal. (avec `grep`)
- **Les remparts** : qui peut lire le coffre ? Regarde ses droits. (avec `ls`, `chmod`)
- **L'empreinte** : prends l'empreinte du rapport (SHA-256). (avec `sha256sum`, `echo`)
- **La boîte à percer** : une « boîte » d'entraînement : un faux serveur à auditer. Montre TOUS ses fichiers, même cachés. (avec `ls`, `grep`, `rm`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Citadelle » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Le guet → compétence « Guetteur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/citadelle/journal_auth.log`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quelqu'un essaie d'entrer dans la Citadelle ! Cherche les échecs de connexion dans le journal. | `grep Failed monde/citadelle/journal_auth.log` | « Failed password » : des mots de passe ratés, à la chaîne… |
| 2 | Qui attaque ? Compte les essais par adresse. | `grep Failed monde/citadelle/journal_auth.log \| cut -d' ' -f11 \| sort \| uniq -c \| sort -rn` | 203.0.113.7 a essayé 5 fois sur root : une attaque par force brute. On le bloquerait au pare-feu. |

### 2. Les remparts → compétence « Bâtisseur de remparts »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/citadelle/coffre.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Qui peut lire le coffre ? Regarde ses droits. | `ls -l monde/citadelle/coffre.txt` | rw-r--r-- : tout le monde peut le lire. Pas terrible pour un code secret ! |
| 2 | Ferme les remparts : toi seul peux lire et écrire. | `chmod 600 monde/citadelle/coffre.txt` | 600 = rw------- : le principe du moindre privilège. Chacun n'a que ce dont il a besoin. |

### 3. L'empreinte → compétence « Vérificateur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/citadelle/rapport.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Prends l'empreinte du rapport (SHA-256). | `sha256sum monde/citadelle/rapport.txt` | 64 caractères : l'empreinte unique de ce fichier. |
| 2 | Un espion modifie le rapport… | `echo 'tout va bien, ouvrez les portes' >> monde/citadelle/rapport.txt` | Le texte a l'air innocent… |
| 3 | Reprends l'empreinte et compare. | `sha256sum monde/citadelle/rapport.txt` | Tout a changé ! C'est ainsi qu'on vérifie qu'un fichier téléchargé n'a pas été trafiqué. |

### 4. La boîte à percer → compétence « Hacker éthique »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/citadelle/boite/accueil.txt`, `~/terrain_terminagotchi/monde/citadelle/boite/.config`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Une « boîte » d'entraînement : un faux serveur à auditer. Montre TOUS ses fichiers, même cachés. | `ls -a monde/citadelle/boite` | Un fichier caché, .config… suspect. |
| 2 | Cherche un mot de passe oublié dans la boîte. | `grep -r mot_de_passe monde/citadelle/boite` | Percée ! Un mot de passe en clair dans un fichier : la faille la plus courante du monde. |
| 3 | Maintenant, répare : supprime ce fichier dangereux. | `rm monde/citadelle/boite/.config` | Percer pour apprendre, réparer pour protéger : c'est le métier de hacker éthique. |

## Questions pour vérifier

- Que fait la commande `grep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ls` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `chmod` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sha256sum` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `rm` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
