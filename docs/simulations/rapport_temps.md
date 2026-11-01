# Simulation : trois enfants visitent la Bibliothèque du Temps (git)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_temps.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Temps.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_guilde.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Bibliothèque est ouverte
d'avance (niveaux 0 à 4 du tronc commun).

**Le vrai git, seulement dans le terrain.** Tous les dépôts (`album`, `grimoire`, `copie_de_mon_ami`) sont créés dans
`~/terrain_terminagotchi/temps`. Aucun dépôt distant réel, aucun `push`, aucun compte. Le `~/.gitconfig` de chaque
enfant est préparé **sans identité** (`user.useConfigOnly`) : git refuse de photographier tant que l'album n'a pas son
nom et son adresse d'exemple, réglés **dans l'album** (`git config` sans `--global`). Le grimoire du Bibliothécaire et
la page de l'ami sont posés par le jeu avec une identité d'exemple réglée dans CE dépôt et des dates fixes : les
empreintes sont les mêmes sur toutes les machines (git 2.43.0 ici).

**Sans tricher.** Le seul trou « ? » est une empreinte : l'enfant la lit dans `git log --oneline -S secret` (la ligne
du haut, la plus récente des deux photos, est celle où la formule a disparu).

**Android.** `tests/jvm/Temps.kt` refait la traversée tp0 → tp5 avec le petit git intégré de l'appli
(`PetitGit.kt`) : 36 vérifications. Ses sorties (empreintes, `git log --oneline`, `git status`, conflit, `--graph`,
`cat-file -p`, `hash-object`) sont comparées octet par octet à celles du vrai git enregistrées dans
`donnees/temps/vecteurs.json`.

**Limites honnêtes.**
- La machine de test est un Linux : le parcours Windows (Git for Windows ou git absent) n'a été vérifié que par les
  tests unitaires (variantes PowerShell des commandes, message « git manque raconté »), pas joué par un enfant.
- Sur un vrai téléphone, `printf 'blob 6\0temps\n' | sha1sum` et `sed -i '/^[<=>]\{7\}/d'` passent par toybox :
  vérifiés en CI avec toybox 0.8.11 compilé, pas sur un appareil.
- Quand Léa tape `git config --global`, c'est **son** shell qui écrit dans son `~/.gitconfig` : le jeu ne peut pas
  l'empêcher, il prévient (⚠) et dit à l'adulte comment vérifier. Le jeu, lui, n'y touche jamais (vérifié pour Inès
  et Hugo : le fichier est identique octet par octet à la fin).

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « version perdue » |
|---|---|---|---|---|
| Léa, 7 ans, tape mal | Voir le détail ci-dessous (fautes typiques) | 72 | oui, tp0 → tp5 | oui |
| Inès, 12 ans, recopie | Recopie la commande verte (« ? » compris), puis lit l'écran | 62 | oui | oui |
| Hugo, 15 ans, ses variantes | Ses propres variantes, toutes justes | 59 | oui | oui, 14 variantes justes acceptées sur 14 |

## 2. Léa, 7 ans : chaque faute reçoit une explication

| Faute | Ce que le jeu répond |
|---|---|
| `Ls`, `Cat …` | les commandes s'écrivent en minuscules |
| `git init` (sans nom) | « Donne un nom à l'album : git init -b main album. (Ton git init tout seul a fait un album du dossier où tu es : ce n'est pas grave.) » |
| `git config --global user.name …` | ⚠ « --global change la configuration de git pour TOUT l'ordinateur (~/.gitconfig)… un adulte peut vérifier : git config --global --list » |
| `git statut` | « Presque ! Tu as écrit « statut », il faut « status ». » |
| `temps perdu <photo où la formule est apparue>` | « Ça, c'est la photo où la formule est APPARUE. Cherche celle où elle a DISPARU (la plus récente des deux). » |
| `git checkout <empreinte>` (tout l'album dans le passé) | « Tu as fait voyager tout l'album dans le passé (« detached HEAD »). Reviens avec git switch main, puis ramène seulement le fichier… » |
| `git switch principal` | l'erreur de git, puis « Pas grave ! Tape : git switch main » |
| `sed` sans `-i` | « Il manque -i : sans lui, sed montre le résultat mais ne change pas le fichier. » |
| `git pull` sans dire d'où | « Dis à git d'où récupérer : git pull ../copie_de_mon_ami » |

Aucune étape n'a été validée par une commande qui a échoué.

## 3. Inès, 12 ans : elle recopie

Elle tape `temps perdu ?` et `git checkout ?~1 -- grimoire.txt` tels quels : le jeu explique qu'il faut remplacer `?`
par une empreinte (les 7 premiers caractères d'une ligne de `git log --oneline`). Elle la lit à l'écran et repart.

## 4. Hugo, 15 ans : ses variantes

Acceptées : `git init album` (son album s'appelle alors `master` : l'indice le lui dit, et il tape `git switch
master`), `git config --local`, `git status -s`, `git log --oneline -n 10`, `git log -S secret --oneline`,
`git checkout -- grimoire.txt`, `git restore --source=<empreinte>~1 grimoire.txt`, `git checkout -b reve`,
`git commit -a -m '…'`, `git log --graph --oneline --all`, `less`, `temps branche`… Refusées : aucune.

## 5. Ce que la simulation vérifie (les trois enfants)

- la Bibliothèque traversée, tp0 → tp5 ;
- l'exploit « retrouver une version perdue » (`temps.version`) ;
- aucune étape validée par une commande qui a échoué ;
- rien d'écrit hors du terrain et de `~/.terminagotchi` ;
- le `~/.gitconfig` jamais changé par le jeu ;
- aucun remote hors du terrain (3 ou 4 dépôts, tous dans `terrain_terminagotchi/temps`) ;
- aucun `push` tapé.

Résultat : **3/3 enfants au bout**, 25 vérifications réussies, 0 échouée.
