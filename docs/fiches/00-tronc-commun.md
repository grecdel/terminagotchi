# 🌱 Tronc commun

*Les bases : se repérer, créer et ranger, lire et chercher, les droits*

| | |
|---|---|
| **Durée** | environ 60 min (5 leçons, 15 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | aucun |
| **Commandes vues** | `pwd`, `ls`, `cd`, `mkdir`, `echo`, `cat`, `grep`, `chmod`, `cp`, `mv`, `rm` |
| **Compétences gagnées** | Boussole, Bâtisseur, Inspecteur, Gardien, Nettoyeur |

## Objectifs

- **Où suis-je ?** : coucou ! Première question : où sommes-nous ? (avec `pwd`, `ls`, `cd`)
- **Construire mon nid** : il me faut un terrain de jeu. Crée-le depuis ton dossier perso. (avec `mkdir`, `cd`)
- **Le garde-manger** : j'ai faim… mets une pomme dans mon garde-manger. (avec `echo`, `cat`, `grep`)
- **Le bouclier** : qui a le droit de toucher à mon repas ? (avec `ls`, `chmod`, `echo`)
- **Grand ménage** : fais une copie de secours de mon repas. (avec `cp`, `mv`, `rm`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Rien à choisir : le tronc commun démarre tout seul.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Où suis-je ? → compétence « Boussole »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Coucou ! Première question : où sommes-nous ? | `pwd` | pwd = « print working directory » : le dossier où tu te trouves. |
| 2 | Regarde ce qu'il y a autour de nous. | `ls` | Voilà les fichiers et dossiers d'ici ! |
| 3 | Rentrons à la maison (ton dossier perso). | `cd ~` | ~ veut dire « mon dossier perso ». Tu sais naviguer ! |

### 2. Construire mon nid → compétence « Bâtisseur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Il me faut un terrain de jeu. Crée-le depuis ton dossier perso. | `mkdir terrain_terminagotchi` | mkdir = « make directory » : créer un dossier. |
| 2 | Entrons dedans. | `cd terrain_terminagotchi` | On est chez nous maintenant. |
| 3 | Construis-moi un nid ! | `mkdir nid` | Il est parfait ! Et j'entends du bruit dehors… l'exploration est ouverte ! |

### 3. Le garde-manger → compétence « Inspecteur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | J'ai faim… mets une pomme dans mon garde-manger. | `echo pomme > nid/repas.txt` | « > » envoie le texte dans un fichier (et l'écrase s'il existe !). |
| 2 | Vérifie ce qu'il y a dedans. | `cat nid/repas.txt` | Toujours vérifier avant d'agir : réflexe de pro. |
| 3 | Cherche le mot « pomme » dans le fichier. | `grep pomme nid/repas.txt` | Chercher un mot dans des fichiers : super-pouvoir débloqué. |

### 4. Le bouclier → compétence « Gardien »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Qui a le droit de toucher à mon repas ? | `ls -l nid` | r = lire, w = écrire, x = exécuter. |
| 2 | Protège-le pour que personne ne l'abîme ! | `chmod 444 nid/repas.txt` | Bouclier activé : le fichier est en lecture seule. |
| 3 | Essaie d'y ajouter une poire, pour voir… | `echo poire >> nid/repas.txt` | Refusé ! « >> » ajoute à la fin, mais le bouclier tient. |

### 5. Grand ménage → compétence « Nettoyeur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Fais une copie de secours de mon repas. | `cp nid/repas.txt nid/secours.txt` | cp = copier. L'original ne bouge pas. |
| 2 | Déplace la copie dans le terrain, sous le nom reserve.txt. | `mv nid/secours.txt reserve.txt` | mv sert à déplacer ET à renommer. |
| 3 | On n'en a plus besoin : supprime-la. | `rm reserve.txt` | Attention : rm ne passe PAS par la corbeille. Vérifie toujours avant ! *Astuce : S'il demande confirmation, réponds y.* |

## Questions pour vérifier

- Que fait la commande `pwd` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ls` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cd` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `mkdir` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cat` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
