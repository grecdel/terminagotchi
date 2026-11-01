# Simulation : trois enfants gravissent le Sommet (Expert++)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_sommet.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Sommet.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_donnees.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal.

**L'ouverture, comme dans le jeu.** Le Sommet s'ouvre quand **trois mondes du Carrefour ont leur palier 3** : ici le
Port, la Citadelle et la Salle des Rouages (leurs leçons 0 à 3 faites), le tronc commun fini. Le jeu compte sur la
liste des mondes de `programme.json` : la Forge, le Poste de Contrôle, la Bibliothèque du Temps et l'Atelier, construits
en ce moment par d'autres, compteront dès qu'ils existeront (vérifié par `test_sommet.py` avec un monde ajouté à la
volée), sans rien changer au Sommet.

**Sans danger.** Les scripts fragiles et cassés (`fragile.sh`, `sale.sh`, `bivouac.sh`, `casse.sh`, `boucle.sh`,
`boussole.sh`, `ctf/porte.sh`) sont **écrits par le jeu dans le terrain** ; aucun ne lit ni n'écrit hors du dossier où
on le lance, aucun ne demande `sudo`, aucun n'utilise le réseau (vérifié par les tests). Les proxys pointent vers
127.0.0.1:9 ; `sudo`, `curl` et `wget` sont des doublures qui refusent et notent qu'on les a appelées.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : le nombre de dates dans la sortie de `wc -l`, les
alertes dans `wc -l alertes.txt`, la pierre la plus lourde dans la liste triée, la ligne dans le message de `bash -n`, la
variable fautive dans la trace de `bash -x`, le cap et le nombre de pas dans `sommet boussole`, le lieu dans la réponse
de la boussole, les trois fragments dans `grep`, `find` et la porte.

**Android.** `tests/jvm/Sommet.kt` refait la traversée som0 → som7 avec les commandes du téléphone (`sh` au lieu de
`bash`) : 23 vérifications vertes. Python et Kotlin donnent exactement les mêmes textes de scripts (bash et sh, 14
langues), le même journal, le même éboulis, la même boussole, le même CTF et le même défi du jour (vecteurs communs
`donnees/sommet/vecteurs.json`).

**Limites honnêtes.**
- La machine de test n'a ni `mksh` (le shell du téléphone) ni `busybox` ni `toybox` : le bivouac dans un `sh` qui connaît
  `pipefail` et la comparaison des outils du téléphone (`pc/outils/test_sommet_outils.py`, toybox compilé depuis ses
  sources) tournent **en CI** seulement. Ici, `dash` (le `sh` d'Ubuntu) n'a pas `set -o pipefail` : c'est pourquoi le
  jeu demande `bash` sur PC.
- `shellcheck`, `man`, `apropos` ne sont pas installés ici : leurs étapes sont cachées (jamais bloquantes), comme
  prévu ; elles sont montrées en CI (où ils existent).
- Le chrono du CTF est un record **local** ; le site ne vérifie que les exercices de la salle d'entraînement (dont ceux
  du défi du jour).
- Les textes des 13 autres langues sont des traductions de Claude, non relues par des locuteurs.

## 1. Les trois profils en bref

| | Léa, 7 ans | Inès, 12 ans | Hugo, 15 ans |
|---|---|---|---|
| Lignes tapées | 74 | 73 | 64 |
| Au bout (som0 → som7) | oui | oui | oui |
| Exploit « Trois mondes maîtrisés » | oui | oui | oui |
| Étape validée par une commande en échec | aucune | aucune | aucune |
| Fautes sans explication | aucune | — | — |
| Variantes justes acceptées | — | — | 10 sur 10 |

## 2. Léa, 7 ans : chaque faute reçoit une explication

| Ce qu'elle tape | Ce que le jeu répond |
|---|---|
| `./fragile.sh "carnet de bord.txt"` | « Permission denied » expliqué, puis : « Lance le script avec le shell devant : `bash nom.sh` » |
| `sed '2i set -euo pipefail' fragile.sh` (sans -i) | « Sans -i, sed affiche le résultat mais ne modifie pas le fichier : ajoute -i. » L'étape attend (le fichier n'a pas changé). |
| `sommet dates ?` | « Remplace le ? par ta réponse… » |
| `sommet dates 23` (toutes les lignes datées) | « grep -oE trouve les dates partout ; sort -u enlève les doublons ; wc -l compte. » |
| `find eboulis -type f -print0 \| xargs wc -c` | « -print0 et xargs -0 vont ensemble… » |
| `sommet ligne 3` | « Relis le message de -n : « line … ». » |
| `sommet bug total` | « Dans la trace -x, cherche la variable qui reçoit le calcul : elle ne s'appelle pas total. » |
| `bash boussole.sh` (sans options) | **corrigé pendant la simulation** (voir § 5) : « Relance la boussole avec le cap et le nombre de pas de TA mission (`sommet boussole` les redit). » |
| `sommet drapeau lagopede` (un seul fragment) | « Le drapeau : TG{fragment1-fragment2-fragment3}, seulement les mots après les =. » |

Le Sommet est annoncé pour les grands (palier de vocabulaire 2), mais rien n'en interdit l'entrée : Léa va au bout,
lentement, en lisant les indices. Les mots techniques (code de retour, variable, expression régulière) sont expliqués
une fois dans les bravos.

## 3. Inès, 12 ans : elle recopie les « ? »

À chacune des 10 étapes à trou (`sommet dates ?`, `sommet alertes ?`, `sommet lourd ?`, `sommet ligne ?`,
`sommet bug ?`, `bash boussole.sh -c ? -p ?`, `sommet arrivee ?`, `bash ctf/porte.sh -k ?`, `sommet drapeau ?`), le jeu
répond « Remplace le ? par ta réponse (lis l'écran, ou le résultat de la commande d'avant) » et l'étape attend. Elle
relit l'écran et répond juste. Un détail : pour compter les alertes, elle tape `wc -l alertes.txt` pendant l'étape
« réponds au jeu » ; le jeu dit alors « Ta commande marche aussi… mais cette étape veut te faire découvrir
`sommet alertes ?` » — la formule générique du jeu, un peu étrange ici, sans gêner (mineur, laissé tel quel, même
comportement dans la Salle des Données).

## 4. Hugo, 15 ans : ses variantes

Toutes acceptées : `sed -i '2a set -euo pipefail'` (la ceinture après le commentaire : toujours avant `cp`),
`grep -Eo …`, `grep -E 'ALERTE|ERREUR' journal.log -c`, `find … -print0 | xargs -0 du -b | sort -rn | head -6`,
`sh -n casse.sh` (le message de `dash` est différent : « casse.sh: 8: Syntax error: "fi" unexpected (expecting
"then") » ; la réponse 8 reste juste), `bash -x ./boucle.sh`, `grep -Eo 'fragment1=…'`, `bash boussole.sh -h`,
`head -n 5`, `less -FX refuge.txt`.

## 5. Problèmes trouvés et ce qui a été fait

| # | Gravité | Problème | Fait |
|---|---|---|---|
| S1 | important | `bash boussole.sh` sans options : la boussole affiche son aide (sortie d'erreur), mais le jeu ne disait rien de plus | corrigé (PC et téléphone) : l'indice rappelle la mission et l'aide (`som.indice.rep.arrivee`) |
| S2 | important (téléphone) | `sh ctf/porte.sh -k CLÉ` ne validait pas l'étape sur Android : le vérificateur prenait la clé pour un FICHIER manquant | corrigé : la porte écrit `ctf/porte_ouverte.txt` ; l'étape vérifie ce fichier (PC et téléphone, vecteurs mis à jour) |
| S3 | mineur | avec `du -b` au lieu de `wc -c`, il n'y a pas de ligne « total » : le bravo dit pourtant « la première ligne est le total » | laissé : la réponse reste juste ; question au propriétaire (§ 6) |
| S4 | mineur | formule générique « Ta commande marche aussi… » pendant une étape de réponse (Inès) | laissé (comportement commun à tous les mondes) |
| S5 | — (outil) | la simulation lisait mal la sortie de `du -b` et le message de `dash -n` | `sim_sommet.py` corrigé |

## 6. Questions pour le propriétaire

1. Le Sommet est « pour les grands » : faut-il le **cacher** aux plus jeunes (option parent) ou seulement le montrer
   plus tard ? Proposition : le laisser ouvert (règle « jamais de blocage ») et l'annoncer avec la mention « Expert++ ».
2. Le défi du jour du Sommet se compose d'exercices de la salle d'entraînement (déjà vérifiés par le site) ; le site ne
   sait pas qu'ils forment un « défi ». Faut-il que le site affiche un badge « défi du jour réussi » ? Proposition :
   plus tard, avec ses tests ; rien n'a été changé sur le site.
