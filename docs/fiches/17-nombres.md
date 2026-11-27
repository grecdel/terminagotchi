# 🔢 Nombres

*Les Ponts des Nombres : binaire, hexadécimal, octets, puissances*

| | |
|---|---|
| **Durée** | environ 15 min (2 leçons, 4 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `echo`, `printf` |
| **Compétences gagnées** | Binariste, Peseur d'octets |

## Objectifs

- **Le binaire** : un ordinateur ne connaît que 0 et 1. Que vaut 101010 en binaire ? (avec `echo`, `printf`)
- **Les octets** : un kilo-octet informatique, c'est 2 puissance 10 octets. Calcule 1024 × 1024. (avec `echo`, `printf`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Nombres » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Le binaire → compétence « Binariste »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Un ordinateur ne connaît que 0 et 1. Que vaut 101010 en binaire ? | `echo $((2#101010))` | 42 ! 32 + 8 + 2 : chaque chiffre vaut le double du précédent. |
| 2 | Et 255 en hexadécimal (base 16) ? | `printf '%x\n' 255` | ff : les couleurs #ff0000 (rouge) des pages web, c'est de l'hexadécimal ! |

### 2. Les octets → compétence « Peseur d'octets »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Un kilo-octet informatique, c'est 2 puissance 10 octets. Calcule 1024 × 1024. | `echo $((1024 * 1024))` | 1 048 576 octets = 1 Mio. Bit, Octet, Kilo, Méga, Giga, Téra, Péta, Exa : ×1024 à chaque marche. |
| 2 | Les droits 644 de chmod sont un nombre en base 8. Que donne 420 (décimal) en octal ? | `printf '%o\n' 420` | 644 = rw-r--r-- : 6 = 4+2 (lire+écrire), 4 = lire. Les maths sont partout dans le terminal ! |

## Questions pour vérifier

- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `printf` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
