# 🏭 Machines

*La Salle des Machines : matériel, démarrage, système, machines virtuelles, cloud*

| | |
|---|---|
| **Durée** | environ 25 min (3 leçons, 6 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `lscpu`, `free`, `uptime`, `uname`, `systemd-detect-virt`, `ssh` |
| **Compétences gagnées** | Mécano, Réveilleur, Virtualiseur |

## Objectifs

- **Ouvrir le capot** : quel est le cerveau de la machine (processeur) ? (avec `lscpu`, `free`)
- **Le réveil** : depuis combien de temps la machine est-elle réveillée ? (avec `uptime`, `uname`)
- **Les machines dans la machine** : sommes-nous dans une vraie machine… ou une machine virtuelle ? (avec `systemd-detect-virt`, `ssh`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Machines » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Ouvrir le capot → compétence « Mécano »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quel est le cerveau de la machine (processeur) ? | `lscpu` | Cœurs (cores) = les ouvriers ; fréquence (GHz) = leur vitesse. |
| 2 | Et la mémoire vive (RAM) ? | `free -h` | La RAM = la table de travail (rapide, s'efface à l'arrêt) ; le disque = l'armoire. |

### 2. Le réveil → compétence « Réveilleur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Depuis combien de temps la machine est-elle réveillée ? | `uptime` | Au démarrage : firmware (BIOS/UEFI) → chargeur → noyau → services. |
| 2 | Quel noyau (le cœur du système) fait tourner tout ça ? | `uname -a` | Le noyau parle au matériel ; tous les programmes passent par lui. |

### 3. Les machines dans la machine → compétence « Virtualiseur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Sommes-nous dans une vraie machine… ou une machine virtuelle ? | `systemd-detect-virt` | « none » = vraie machine. kvm, vmware, wsl… = une machine simulée par une autre : c'est la base du cloud. |
| 2 | Le cloud, ce sont des milliers de machines virtuelles louées à la minute. As-tu l'outil pour t'y connecter ? | `ssh -V` | SSH = le câble invisible pour piloter une machine à distance, dans le cloud comme à la maison. *Astuce : S'il manque : sudo apt install openssh-client* |

## Questions pour vérifier

- Que fait la commande `lscpu` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `free` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `uptime` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `uname` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `systemd-detect-virt` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ssh` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
