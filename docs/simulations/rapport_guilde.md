# Simulation : trois enfants visitent la Guilde des Bâtisseurs Libres (sixième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_guilde.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Guilde.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_ondes.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Guilde est ouverte d'avance
comme dans l'arbre du Carrefour (niveaux 0 à 4 du tronc commun).

**Les vrais outils, mais seulement dans le terrain.** `git`, `gcc`, `make`, `file`, `od`, `ldd`, `sha256sum`, `dd`
et `lsblk` sont les vrais. `dd` n'écrit que vers le fichier `cle_usb.img` du terrain. Le `git clone` est tenté, mais
le réseau est coupé (les proxys pointent vers 127.0.0.1:9). Il échoue, et l'enfant prend la copie de la Guilde
(`guilde copie`), comme le prévoit la leçon. OpenSCAD n'est pas installé sur la machine de test, donc la pièce STL
est fabriquée par le jeu (la plaque sans le trou, c'est dit à l'écran). En CI, OpenSCAD est installé.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** :
- les libertés, lues dans les situations ;
- « gratuit », lu dans les descriptions ;
- le fichier de la faim, lu dans la sortie de `grep -rn "def etat_de"` ;
- la faute, lue dans `cat langues/fr.txt` ;
- le trou et le volume, lus dans `porte_cle.scad`, avec `echo $((L * l * h))` ;
- la clé, lue dans le lsblk fictif (la taille qui correspond aux Go écrits sur la clé).

**Android.** `tests/jvm/Guilde.kt` refait la traversée gu0 → gu6 avec les commandes du téléphone : 28 vérifications.
- git, gcc, make, OpenSCAD et lsblk sont racontés.
- La copie du code est faite d'extraits du vrai code.
- La correction se relit avec `diff`.
- `dd` et `sha256sum` travaillent sur des fichiers.
- Python et Kotlin donnent les mêmes résultats sur les vecteurs communs (`donnees/guilde/vecteurs.json`) : libertés, gratuit, licences, faim, faute, pièce, trou, volume, STL, image et empreinte, disques fictifs, établi.

**Limites honnêtes.**
- La machine de test n'a pas de réseau : le vrai `git clone` du dépôt public n'a **pas** été vu réussir ici. Le chemin « copie » a été joué à sa place.
- OpenSCAD n'a été lancé qu'en CI.
- Le `lsblk` de la machine (étape gu6.1) est le vrai, mais en lecture seule. Le choix de la clé se fait sur un lsblk **fictif**.
- Aucune vraie clé USB, aucun vrai disque n'a été touché.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « artisan » |
|---|---|---|---|---|
| Léa, 7 ans, tape mal | Voir le détail ci-dessous (11 fautes typiques) | 80 | oui, gu0 → gu6 | oui |
| Inès, 12 ans, recopie | Recopie la commande verte (« ? » compris), puis lit l'écran | 67 | oui | oui |
| Hugo, 15 ans, ses variantes | Ses propres variantes de commande, toutes justes (liste ci-dessous) | 61 | oui | oui, 18 variantes justes acceptées sur 18 |

Les fautes de Léa :
- `Cat` et `Ls` avec une majuscule ;
- les libertés dans l'ordre 0 1 2 3 ;
- la licence d'un logiciel inventé ;
- `guilde gratuit l l l l` ;
- `guilde faim aura.py` ;
- `gcc bonjour.c -o bonjour.c` ;
- `sed` sans `-i` ;
- `git statut` et `git commit -m` sans `-a` ;
- le trou à (6 ; largeur) ;
- le volume « 40*24*4 » ;
- le disque du système (`nvme0n1`) ;
- `dd` à l'envers (de la clé vers l'image).

Les variantes de Hugo :
- `guilde libertés` et `guilde pièce` ;
- `head -5`, `find -maxdepth 2`, `grep -rln` ;
- `cc` au lieu de `gcc`, `od -c` ;
- `git checkout -b`, `git diff --word-diff`, `git log --graph` ;
- `guilde trou [6, 14]`, `guilde volume 5.04 cm3` ;
- `sha256sum --check` ;
- `cp` au lieu de `dd` ;
- `guilde disque /dev/sdb` ;
- `guilde vieux-pc`, `guilde clé`.

Ce qui vaut pour les trois enfants :
- aucune étape n'a été validée par une commande qui a échoué ;
- rien n'a été écrit hors du terrain et de `~/.terminagotchi` ;
- **aucune commande tapée n'écrit vers `/dev`** ;
- le petit dépôt de la contribution n'a **aucun remote** : rien ne peut être poussé ;
- la fausse clé est une copie exacte de l'image (même empreinte SHA-256), et le certificat est écrit dans `vieux_pc`.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : les 4 libertés avec un exemple chacune, « libre ≠ gratuit », la ligne `def etat_de` qui dit « c'est ici », le programme qui parle après `gcc`, la ligne rouge / verte de `git diff`, le porte-clé vu de dessus avec son trou. |
| `sed` sans `-i` | Avant : rien ne se passait (le fichier ne changeait pas). Maintenant : « Sans -i, sed AFFICHE le texte corrigé mais ne change pas le fichier. Ajoute -i… ». |
| `git commit -m` sans `-a` | Avant : « nothing added to commit » sans explication du jeu. Maintenant : l'indice dit que le commit doit contenir la correction (`-am`), et sur sa branche, pas sur main. |
| `dd` à l'envers | La clé vide écrase l'image. Le jeu explique if (ce qu'on lit) et of (ce qu'on écrit **et efface**), puis dit de taper `guilde cle` pour tout remettre. C'est la leçon la plus importante de G6, apprise sans danger, sur un fichier. |
| Le disque du système | « Attention : c'est le disque du système (celui où il y a /) ! » — puis elle relit les tailles. |
| `gcc … -o bonjour.c` | gcc refuse lui-même (« input file is the same as output file ») et n'écrase rien. Avant : seul ce message anglais l'expliquait. Maintenant : « Avec -o, on donne le nom du PROGRAMME à fabriquer, pas celui de la recette » (GU14). |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout, sauf aux trous `?` (libertés, licences, gratuit, faim, faute, trou, volume, disque). C'est voulu : le jeu dit que c'est un trou et ce qu'il faut lire. |
| Le `git clone` sans réseau | Échec (code 128). L'étape est marquée « réseau » et ne bloque pas : « Sinon, pas grave : la Guilde a une copie », puis `guilde copie`. |
| L'exploit | `guilde fusion` après le commit sur sa branche : `guilde.artisan` est gagné. *(1er novembre : il ne favorise plus de variantes ; il fait grandir le badge « Artisan ».)* |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 18 sur 18 acceptées. |
| `guilde disque /dev/sdb` | Accepté : c'est une **réponse** au quiz, pas une écriture. La garde `/dev` ne vise que les écritures (`of=/dev/…`, `> /dev/sd…`, `cp/cat/tee/dd/mv … /dev/sd…`). |
| `cp` au lieu de `dd` | Accepté : la clé est vérifiée par son empreinte, pas par la commande. |

## 2. Problèmes trouvés, classés

### Critiques — aucun ouvert

| # | Problème | État |
|---|---|---|
| GU1 | Le test de la faim cherchait `def etat_de` dans **tous** les fichiers, y compris `guilde.py` lui-même (la commande montrée contenait le texte cherché) : deux « bonnes » réponses, dont une fausse. | La commande de l'étape est écrite en deux morceaux dans le code ; la marque vient de `guilde.json`. Même chose dans `Guilde.kt`. |
| GU2 | `guilde disque /dev/sda` (une réponse) était pris pour une écriture vers un disque dans la simulation. | La vérification utilise la même expression que la garde du jeu (`DEV`), qui ne vise que les écritures. |
| GU3 | Les exercices des Ponts des Nombres « coordonnées » et « volume » n'existaient que sur PC. | Mêmes générateurs dans `Maths.kt` (mêmes tirages), vérifiés par les vecteurs communs. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| GU4 | Après une bonne licence (« 1 sur 5 »), le jeu ajoutait « 💡 … Pas grave ! » comme après une erreur. | L'indice de progression des licences est retiré : le compteur « 1 sur 5 : continue ! » est déjà dans la sortie de `guilde licence`. |
| GU5 | Le pont des maths disait « … parle de Les coordonnées ». | Nouvelle phrase : « Cette étape utilise une notion de maths : {notion}. » (14 langues). |
| GU6 | Un pont « pourcentages » sur l'entrée du vieux PC, alors qu'aucun pourcentage n'y apparaît. | Retiré. Restent les ponts : hexadécimal (ELF, gu3.5 ; empreinte, gu6.3), coordonnées (gu5.2) et volume (gu5.3). |
| GU7 | `cd vieux_pc` déclenchait « Ta commande marche aussi » (le mot « vieux » était dans la commande de l'étape). | L'étape s'appelle maintenant `guilde sauver` (`guilde vieux-pc` reste accepté). |
| GU8 | `sed` sans `-i`, `git commit` sans `-a`, `dd` à l'envers : rien n'expliquait l'échec. | Trois indices dédiés (`gu.indice.sed_i`, `gu.indice.commit`, `gu.indice.inverse`). |
| GU14 | `gcc bonjour.c -o bonjour.c` : seul le message anglais de gcc l'expliquait. | Indice `gu.indice.gcc_o` (14 langues), vérifié par la simulation de Léa. |
| GU9 | Sur le téléphone, le `diff` intégré affiche le format normal (`<` / `>`) et non le format `-u`. | L'étape du téléphone utilise `diff` sans `-u` ; son texte explique `<` (avant) et `>` (après). |

### Mineurs (notés)

| # | Constat |
|---|---|
| GU10 | Le dépôt GitHub public (branche main) n'a pas encore `satiete.py` : un vrai clone de main trouverait la faim ailleurs. Le jeu calcule la bonne réponse dans le clone **ou** la copie réellement présente, avec une marque de repli (« point de faim ») pour l'ancienne version. Ça marche dans les deux cas, mais le texte de l'étape gu2.7 cite `satiete.py`. |
| GU11 | `rpm -q` (licence de bash) n'est montré que là où rpm est LE gestionnaire de paquets (`/usr/lib/sysimage/rpm` : Fedora, openSUSE). Ailleurs, l'étape est cachée. La CI (Ubuntu, où le paquet rpm est installé) a montré que `rpm -q` y crée `~/.rpmdb` dans le dossier personnel : c'est une écriture hors du terrain, attrapée par `test_guilde.py`, et c'est ce qui a imposé cette condition. |
| GU12 | Les émojis (🗽, 🎁…) ne s'affichent pas dans la police des captures PC ; ils s'affichent dans un vrai terminal. |
| GU15 | Les variantes réservées à la Guilde (`engrenaille:mecanique`, `rouillot:rouille`, `lampignon:champignonniere`) n'apparaissent plus avant l'exploit : dans le test d'attirance, les Célestes sans attirance passent de 7,3 % à 8,0 % (identique PC / Android ; valeur attendue de `tests/jvm/RetoursEnfants.kt` mise à jour). *1er novembre : ces réservations sont supprimées (badge « Artisan » à la place) ; le test d'attirance reste vert.* |
| GU13 | L'icône du lieu est 🧰 et non 🛠 : 🛠 ne passait pas le test de largeur des cartes du camp. |

## 3. Ce qui marche bien

- **Rien ne sort du terrain.**
  - Le clone, la copie, la contribution, la pièce, l'image et la clé sont tous dans `terrain_terminagotchi/guilde`.
  - Le dépôt de la contribution n'a pas de remote. L'identité « Apprenti de la Guilde » est locale à ce dépôt.
  - `git push`, `gh pr`, `sudo`, `apt/dnf install` et les écritures vers `/dev` reçoivent chacun une phrase claire de la créature. Le jeu ne les lance jamais lui-même.
- **Les vrais disques ne sont jamais visés.**
  - `dd` ne se pratique que de fichier à fichier, et l'empreinte prouve la copie.
  - L'écriture sur une vraie clé est seulement expliquée, « avec un adulte », en vérifiant d'abord le bon disque avec `lsblk`.
- **Le vrai code du jeu.** L'enfant trouve lui-même, avec `grep`, le fichier où sa créature décide qu'elle a faim. Puis il le lit.
- **La contribution est un vrai geste.** Branche, correction, `git diff`, commit, `git log`, sur une **copie** des vraies phrases du jeu, avec une faute volontaire. Les fichiers de langue du jeu ne contiennent aucune faute ajoutée.
- **Les crédits sont prêts mais vides.** `CREDITS.txt` explique que le jeu ne collecte ni nom ni adresse.
- **Les Ponts des Nombres** (hexadécimal, coordonnées, volume) sont proposés sans jamais bloquer.

## 4. Ce qui reste

- Les illustrations : prompts dans `outils/guilde/prompts_illustrations.md` (B13, vignette, C1, C3, C4, E16), aucune image générée.
  - En attendant, la maison, les libertés, la pièce et la clé sont dessinées : en caractères sur PC, avec `GuildeDessin` sur le téléphone.
- Un vrai `git clone` réussi, vu sur une machine avec réseau.
- GU10 : publier `satiete.py` sur main (ou adapter le texte de gu2.7).

## 5. Rejouer

```
python3 pc/outils/sim_guilde.py              # les trois
python3 pc/outils/sim_guilde.py lea          # une seule
python3 pc/outils/test_guilde.py             # la Guilde sur PC (50 vérifications)
python3 pc/outils/vecteurs_guilde.py --verifier
python3 pc/outils/capture_guilde.py <dossier> # les captures PC
# Android : tests/jvm/Guilde.kt (28 vérifications), voir outils/tout.sh jvm Guilde
```
