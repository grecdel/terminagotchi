# Simulation : trois enfants défendent la Citadelle (phase 5, deuxième monde du Carrefour)

Date : 31 octobre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_citadelle.py` (PC, rejouable à chaque
test et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Citadelle.kt` (§ 4 de ce test).

## 0. Comment on a joué

**PC.** Chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert (`pc/tg/coquille.py`), comme
`sim_port.py`. Après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la commande
montrée (`compagnon.commande_montree`), la sortie de sa commande et ce que le jeu écrit dans son terminal
(`compagnon.annonces`). La Citadelle est ouverte d'avance comme dans l'arbre du Carrefour (nid, bibliothèque et cave
finis : niveaux 0 à 6 du tronc commun). Les simulations tournent **sans** le droit de passer outre les permissions
(`setpriv --bounding-set -dac_override`) : un `chmod` raté se voit comme chez un enfant (pas comme chez root).

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : l'adresse la plus fréquente dans la sortie de
`uniq -c`, les PID de la 2e colonne de `ps`, la ligne `FAILED` de `sha256sum -c`, les drapeaux `TG{…}` de la sortie
de `grep -r`, les remarques du facteur qui parlent du lien, de l'urgence ou du mot de passe ; pendant la grande vague,
l'enfant lit le tableau de garde et répare ce qui est rouge (`find … -delete`, `ps` puis `kill`, `find -perm -o+r`
puis `chmod 600`).

**Android.** `tests/jvm/Citadelle.kt` refait la traversée cit0 → cit16 avec les commandes du téléphone (`citadelle
ps` et `kill` des processus fantômes simulés, `openssl` / `diff` / `shuf` intégrés, `tar cf` sans gzip) : 34
vérifications, dont l'aller-retour avec le **vrai** `openssl` (le téléphone déchiffre ce que openssl a chiffré, et
l'inverse) et `diff` comparé au vrai GNU diff.

**Limites honnêtes.** `ss` manque dans le bac à sable (l'étape cit16.0 est `absent_ok`, une doublure répond dans
test_citadelle) ; la machine de test tourne en root, d'où `setpriv` ; `ps` montre l'utilisateur `root` au lieu de
celui de l'enfant.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Indices reçus | Blocages | Au bout ? |
|---|---|---|---|---|---|
| Léa, 7 ans, tape mal | majuscules (`Ls`, `Cat`, `Grep`, `Find`), `chmod 600 cofre.txt`, `sudo kill …`, recopie `?`, lance `./cadeau.sh` par curiosité, chiffre avec la clé `1234`, faux facteur `1 2 3`, faux drapeau `TG{abc}`, inspecteur appelé trop tôt | 103 | 38 | 0 | oui, cit0 → cit16, les 2 exploits |
| Inès, 12 ans, recopie | recopie la commande verte, `?` compris (6 trous), puis lit l'écran | 83 | 18 | 0 | oui, les 2 exploits |
| Hugo, 15 ans, ses variantes | `ls -la`, `chmod go-rw`, `chmod 744`, `(umask 0077 && touch …)`, `tail -5`, `grep … \| wc -l`, `uniq -c \| sort -rn`, `find -type f … -delete`, `head -n 20`, `chmod a-x`, `ps -ef`, `kill -9`, `sha256sum --check`, `tar -czf … parchemins/`, `diff -u`, `shuf -n4`, `grep -rn`, `find -perm -002`, `chmod o=`, `rm -f`, `grep -ri` | 76 | 11 | 0 | oui, les 2 exploits, 24 variantes acceptées sur 24 |

Commun aux trois : aucune étape validée par une commande qui a échoué ; plus aucun processus fictif à la fin ; seules
les clés d'exemple (et le `1234` de Léa, refusé) ont été tapées ; rien d'écrit hors du terrain et de `~/.terminagotchi`.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : les cadenas (moi, mon club, les autres), le registre du gardien, les glitchs, le cheval en bois ; chaque vraie sortie (`rw-r--r--`, `52`, `FAILED`, `bad decrypt`) est expliquée en une phrase. |
| Le `sudo` | « Pas de sudo dans le jeu : la clé du gardien (root) se demande à un adulte. Tout ce qu'il faut ici marche sans elle. » |
| Le cadeau lancé | Les trésors du bac à sable disparaissent… puis reviennent ; la créature explique « on LIT avant de lancer » ; l'étape (`chmod -x`) attend. |
| La clé `1234` | Corrigé (CI1) : refusée, « utilise la clé d'EXEMPLE montrée ». |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout sauf aux six trous `?` (voulus) : le jeu dit chaque fois que c'est un trou à remplir et quoi y mettre (l'adresse, le numéro, le drapeau…). |
| Les drapeaux | Après le premier drapeau rendu, « Encore un drapeau dans cette boîte » (corrigé : CI2). |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 24 sur 24 acceptées après correction (CI4 : `grep ECHEC … \| wc -l` et `find -perm -002` étaient refusés). |
| La vague | Il répare en lisant le tableau ; entre deux réparations, le jeu dit « Quand tu as tout réparé, regarde le tableau de garde » (corrigé : CI3). |

## 2. Problèmes trouvés, classés

### Critique — corrigé

| # | Problème | Correction |
|---|---|---|
| CI1 | **Chiffrer avec une autre clé que l'exemple (`-pass pass:1234`) validait l'étape cit10.1, puis l'étape cit10.3 (ouvrir avec la clé d'exemple) devenait impossible** : Léa restait bloquée (466 essais). | L'étape vérifie maintenant que `lettre.enc` s'ouvre avec la clé d'EXEMPLE (PC : `openssl -d` ; Android : le même déchiffrement intégré) ; sinon l'indice « utilise la clé d'EXEMPLE montrée ». |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| CI2 | Après un premier drapeau juste, l'indice générique « Ta commande marche aussi, bravo ! » (faux et déroutant). | `citadelle.indice` / `Citadelle.indice` : « Encore un drapeau dans cette boîte » ; un drapeau périmé (rotation) : son explication. |
| CI3 | Pendant la grande vague, chaque réparation (find, kill, chmod) recevait « marche aussi », et le tableau relu « Pas encore » en boucle. | Entre deux réparations : « Quand tu as tout réparé, regarde le tableau de garde » ; « Pas encore : il reste du rouge » seulement quand on relit le tableau. |
| CI4 | Deux variantes justes de Hugo refusées : `grep ECHEC … \| wc -l` (au lieu de `grep -c`) et `find … -perm -002` (au lieu de `-o+w`). | Expressions élargies (PC et Android). |
| CI5 | `(umask 077; touch carnet_secret.txt)` faisait dire au jeu « « (umask » n'est pas une commande… tu voulais dire umask ? » alors que la commande avait marché. | `core.first_word` / `core.feed` lisent la commande de la petite bulle `( … )`. |
| CI6 | Le Verrouilleur frappait APRÈS le tour où la sauvegarde était validée : les étapes « restaurer » et « jeter les .verrou » se validaient toutes seules (cit9 sautait de 0 à 3). | Le Verrouilleur frappe juste après la sauvegarde, une seule fois (`journaux/verrouilleur.log`, que l'enfant peut lire) ; restaurer et jeter les `.verrou` exigent qu'il ait frappé (PC et Android). |
| CI7 | Le cheval lancé par erreur : l'avertissement s'affichait, puis l'indice « marche aussi » juste en dessous. | Pendant cit6, c'est l'indice de l'étape qui explique (une seule fois). |
| CI8 | L'inspecteur appelé avant la réparation, pendant l'étape `chmod o-rwx` : pas d'indice dans le terminal. | « L'inspecteur a encore trouvé une brèche : relis ls -l » aussi pendant l'étape du rempart. |
| CI9 | `citadelle facteur` (la liste relue) pendant l'étape à trous : « marche aussi ». | La règle (« Les 3 vrais indices de piège ? citadelle facteur N N N »). |
| CI10 | `citadelle vague` tapé deux fois lançait deux processus fictifs (il fallait les arrêter tous les deux). | Une seule vague à la fois (PC et Android). |

### Mineurs (notés)

| # | Constat |
|---|---|
| CI11 | `openssl -d` avec une mauvaise clé réussit (charabia, code 0) une fois sur 256 environ (rembourrage valide par hasard). L'étape cit10.2 accepte les deux issues (`tout_code`) ; la fiche du rejeu utilise un sel fixe pour rester stable. Le texte dit « refusé », vrai 255 fois sur 256. |
| CI12 | Les indices commencent par « Pas grave ! Tape : … » même quand l'enfant faisait juste le bon travail (la vague) : c'est la forme commune de tous les indices du jeu. |
| CI13 | Sur le téléphone, `umask` vient du shell de l'appli (souvent 077) et `citadelle masque` sans nombre affiche 077 ; sur PC c'est souvent 022 : les deux sont justes, mais différents. |
| CI14 | `ps` montre le vrai nom d'utilisateur de l'ordinateur (sur la machine de test : `root`) ; `citadelle ps` (téléphone) montre `explorateur`. |

## 3. Ce qui marche bien

- **Rien ne sort du terrain** : glitchs, cheval de Troie, processus fictifs (`sleep` renommés qui s'éteignent seuls),
  Verrouilleur (base64 + mode 000), boîtes, vague : tout dans `~/terrain_terminagotchi/citadelle/` ; la liste des
  processus fictifs dans `~/.terminagotchi/citadelle/`. Jamais de `sudo` (le `chown` est simulé et le dit).
- **Rien de réel** : le journal n'a que des adresses de documentation (RFC 5737), le faux lien un nom réservé
  (RFC 2606), les mots de passe sont des exemples (`licorne-violette-exemple`, une rotation `exemple-xxxxxx`).
- Le moment fort : la boîte « Les droits mal réglés » — `find -perm -o+w` trouve le script modifiable par tous, les
  drapeaux se lisent parce que les cadenas sont mal posés, `chmod o-rwx` et l'inspecteur qui rejoue l'attaque.
- Le pont `curl` du Port (le phare répond `/courrier` sur 127.0.0.1) et le pont `find -newer` vers le Temps
  (le ver qui se copie après le repère) sont joués par les trois enfants.

## 4. Ce qui reste

- Les illustrations (prompts écrits, aucune image générée) ; en attendant, la forteresse est dessinée (PC en
  caractères, téléphone `CitadelleDessin.forteresse`).
- Les cinq autres catégories de boîtes (le hangar ouvert, les scripts trop naïfs, les codes secrets, l'enquête
  numérique, l'ingénierie sociale) : annoncées « bientôt » dans `citadelle boites`.
- La variante « glitch » du gardien de chaque boîte (§ 7.6) : aujourd'hui, un exploit libère quatre variantes
  existantes des Démons (types Ombre et Poison).

## 5. Rejouer

```
python3 pc/outils/sim_citadelle.py            # les trois (≈ 1 min)
TG_DEBUG=1 python3 pc/outils/sim_citadelle.py lea     # une seule, avec chaque ligne tapée et ce qu'elle a lu
python3 pc/outils/test_citadelle.py           # la Citadelle sur PC (43 vérifications)
# Android : tests/jvm/Citadelle.kt (34 vérifications), voir outils/tout.sh jvm Citadelle
```
