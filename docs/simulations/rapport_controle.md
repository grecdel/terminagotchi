# Simulation : trois enfants visitent le Poste de Contrôle (administration système)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_controle.py` (PC, rejouable à chaque
test et en CI). Pour Android, la traversée du téléphone est rejouée par `tests/jvm/Controle.kt`.

## 0. Comment on a joué

**PC.** Chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert (`pc/tg/coquille.py`). Le
jeu fait son tour après chaque ligne, avec le code de sortie. L'enfant ne lit **que** la commande montrée, la sortie
de sa commande et ce que le jeu écrit dans son terminal. Le Poste est ouvert d'avance (niveaux 0 à 6 du tronc
commun), comme dans l'arbre du Carrefour.

**De vraies commandes, en lecture.** Les commandes sont les vraies :
- `ps`, `/proc/$$/status`, `free`, `df`, `du`, `uptime`, `nproc` ;
- `journalctl --user`, `dmesg`, `/etc/os-release`, `dpkg -l`, `systemctl list-units` ;
- `cut -d: -f1 /etc/passwd`.

Ce qui changerait la machine passe par des **doublures** qui notent l'appel (`sudo`, `useradd`). La simulation vérifie
qu'aucune n'a été appelée. Les réveils ne sont jamais lancés : le jeu les lit et calcule la prochaine sonnerie. La
vague est faite de vrais `sleep` renommés (`exec -a bavard_fictif sleep 900`), lancés par le jeu. Le jeu vérifie le
numéro **et** le nom (`/proc/PID/cmdline`) avant de dire qu'un habitant est arrêté. À la fin, aucun ne reste.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** :
- la caisse la plus lourde, lue dans `du -sh entrepot/*` ;
- le nombre de dossiers du PATH, compté avec `wc -l` ;
- les alertes, lues dans `grep -c` ;
- le réveil, déduit de la phrase du Poste (« du lundi au vendredi à 7 h 30 ») ;
- la distribution, lue dans `/etc/os-release` (ligne `ID=`) ;
- les familles, déduites des noms et de la fiche d/a/p ;
- les numéros des suspects, lus dans la colonne PID de `ps aux | grep fictif`, sans le veilleur.

**Android.** `tests/jvm/Controle.kt` refait la traversée avec les commandes du téléphone (22 vérifications) :
- `top -n 1` ;
- `export …; sh -c …` sur une seule ligne ;
- `. ./sac_a_dos.sh; echo $POSTE` ;
- `logcat`, `getprop` ;
- la vague simulée (`controle ps`, `kill` intercepté par le jeu).

Python et Kotlin donnent les mêmes résultats sur les vecteurs communs (`donnees/controle/vecteurs.json`) :
- caisses, jauges, PATH, carnet ;
- cron (champs, règle « jour du mois OU jour de la semaine », prochaine sonnerie) ;
- os-release, familles, noms d'utilisateur ;
- vague, tableau de bord de la vue déployée.

**Limites honnêtes.**
- La machine de test est un Ubuntu dans un conteneur, sans systemd en marche et sans `crontab` :
  - `journalctl --user` et `dmesg` y sont refusés, ce qui est prévu : ces étapes comptent même si la commande est
    refusée (`tout_code`) ;
  - `systemctl` répond qu'il n'y a pas de systemd, et l'étape est validée sur la commande tapée ;
  - l'étape `crontab -l` est cachée quand l'outil manque. En CI, le paquet `cron` est installé, et elle est jouée.
- `rpm -qa` (Fedora) n'a **pas** été vu ici : l'étape n'apparaît que si `/usr/lib/sysimage/rpm` existe. Le chemin
  Debian (`dpkg -l`) a été joué. Sur le Fedora du propriétaire, ce sera l'autre étape. Elle est vérifiée par le motif
  et le rejeu, mais pas lancée sur une vraie Fedora.
- Personne n'a joué sous Windows ou sur un vrai téléphone. Les équivalents Windows (Get-Process, Get-Service,
  `$PID`, vague simulée) sont couverts par `test_controle.py` et la CI Windows ; le téléphone par le test JVM.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « la vague » |
|---|---|---|---|---|
| Léa, 7 ans, se trompe d'abord | 13 fautes typiques (liste ci-dessous), puis lit et corrige | 85 | oui, ct0 → ct7 | oui |
| Inès, 12 ans, recopie | Recopie la commande verte (« ? » compris), puis lit l'écran | 70 | oui | oui |
| Hugo, 15 ans, ses variantes | Ses propres variantes, toutes justes | 63 | oui | oui, 37 variantes justes acceptées sur 37 |

Les fautes de Léa, et ce que le jeu lui répond :
- `Cat`, `Ls`, `Ps` avec une majuscule : le conseil habituel du tronc commun (« les commandes s'écrivent en
  minuscules ») ;
- `controle entrepot cartes_du_ciel` (une caisse plus légère) : « Ce n'est pas la plus lourde. Relis les tailles de
  du -sh entrepot/* (K < M < G) » ;
- `controle path 1` : « Le nombre n'est pas bon. Compte les lignes : echo $PATH | tr ':' '\n' | wc -l » ;
- `export COULEUR = bleu` (des espaces autour du =) : « Pas d'espace autour du = ». Cette erreur est très courante :
  bash répond « not a valid identifier », ce qui ne veut rien dire pour un enfant ;
- `bash sac_a_dos.sh` au lieu de `source` : « bash sac_a_dos.sh lance un AUTRE habitant : il charge le sac, puis
  s'en va avec. source le charge dans TON terminal » ;
- `controle alertes 24` (toutes les lignes du carnet comptées) : « Recompte : grep -c ALERTE carnet_de_bord.log » ;
- `controle cron 0 7 * * *` sans guillemets (bash remplace `*` par des noms de fichiers) : « Mets les 5 champs entre
  guillemets » ;
- le réveil affiché par `echo` mais pas ajouté au fichier : « Ajoute la ligne DANS le fichier : mets >>
  reveils.crontab à la fin » ;
- `controle distribution linux` : « Ce n'est pas ce que dit ta machine. Relis la ligne ID= » ;
- `controle familles d d d d d` : « 2 justes sur 5. Relis la liste » ;
- `controle useradd Lea` (une majuscule) : la règle des noms (minuscules, sans espace ni accent, 16 caractères au
  plus) ;
- `kill 1` : le système refuse (Léa n'est pas root). Le jeu ajoute : « cette commande pourrait arrêter beaucoup
  d'habitants d'un coup… On arrête UN habitant à la fois, avec son numéro » ;
- elle arrête ensuite **le veilleur** : le tableau de bord dit « Oups, le veilleur est arrêté ! Relance une alerte
  et ne touche qu'aux suspects ». Elle relance, puis réussit.

Chaque faute reçoit une explication (vérifié par la simulation).

Les variantes de Hugo, toutes acceptées : `ps -ef`, `echo $BASHPID`, `ls /proc/self`, `cat /proc/self/status | head -3`,
`sleep 3`, `sleep 90 &`, `jobs -l`, `kill -TERM %1`, `top -b -n 1 | head -5`, `vmstat`, `df -h ~`,
`du -h entrepot/*`, `uptime -p`, `lscpu | head -5`, `printenv HOME`, `printenv PATH`, `type ls`,
`export COULEUR="bleu"`, `sh -c 'echo $COULEUR'`, `alias salut='echo Salut !'`, `less sac_a_dos.sh`,
`. ./sac_a_dos.sh`, `echo "$POSTE"`, `tail -5`, `grep … | wc -l`, `tail -F`, `journalctl --user -n 5`,
`controle réveil`, `less reveils.crontab`, `printf … >> reveils.crontab`, `grep ^ID= /etc/os-release`,
`controle famille`, `dpkg-query -l | grep -c '^ii'`, `systemctl --type=service …`,
`getent passwd | cut -d: -f1 | head -3`, `tail -n 2 equipage.txt`, `pgrep -af fictif`, `kill -TERM PID…`,
`controle installation`.

## 2. Ce que la simulation a trouvé, et ce qui a été corrigé

| Gravité | Trouvaille | Correction |
|---|---|---|
| **Critique** | Une première version de la simulation tapait un vrai `kill 1` en root dans le bac à sable de test. C'est dangereux ailleurs que dans un conteneur jetable. | La simulation imite maintenant le refus du système (une fonction `kill` de la coquille). Le jeu, lui, avertit sur `kill 1`, `kill -1`, `killall` et `pkill` sans « fictif » (`ct.garde.kill_large`), à **chaque** fois, pas seulement pendant la vague. |
| **Critique** | `ps aux \| grep fictif` montre aussi toute ligne de commande qui contient le mot « fictif » (par exemple le `grep` lui-même, ou un autre shell). Un enfant pressé pourrait lire un mauvais numéro. | La leçon prévient que la ligne du `grep` apparaît aussi et que les habitants du Poste ont un nom qui finit par `_fictif` (dernière colonne). Le jeu vérifie le numéro ET le nom avant tout « arrêté », et `pas_a_nous` explique quand un numéro n'est pas un habitant du Poste. La simulation lit la colonne COMMAND. |
| Important | `pgrep -a fictif` ne trouve rien : le nom du processus reste `sleep`, seul `argv[0]` est renommé. | Hugo utilise `pgrep -af fictif` (-f : toute la ligne de commande). C'est une remarque à garder pour les grands : un nom affiché peut mentir, d'où « vérifier le nom ET le numéro » (fiche `poste_alerte`). |
| Important | `du` lancé **dans** le sous-dossier `entrepot` faisait échouer les étapes suivantes (le jeu acceptait le sous-dossier comme « dans le Poste »). | L'étape est `du -sh entrepot/*` depuis `controle`. Les textes sont mis à jour dans les 14 langues. |
| Important | `controle entrepot coffre.bin` était refusé (l'enfant recopie le nom avec `.bin`). | `.bin` et le chemin sont retirés avant la comparaison (vecteurs régénérés). |
| Important | `export COULEUR = bleu` et `bash sac_a_dos.sh` ne recevaient que le message de bash. | Ajout de deux conseils : `ct.indice.export_espaces` et `ct.indice.source`. |
| Moyen | `tail -f` ne rend pas la main sans Ctrl+C ; dans le rejeu et la simulation, `timeout 1 tail -f` n'était pas reconnu. | Le motif accepte un préfixe `timeout`, et l'étape accepte un code de sortie non nul (Ctrl+C). |
| Moyen | Sur le téléphone, chaque ligne va dans un nouveau shell : `export` puis `sh -c` sur deux lignes ne marchait pas. | Le téléphone a ses propres étapes sur UNE ligne (`export …; sh -c …`, `. ./sac_a_dos.sh; echo $POSTE`), avec une explication (`ct.tel.sac`). |
| Faible | (vu sur les captures) Le pupitre de repli en caractères était de travers (lignes de largeurs différentes à cause de ⏰ et 📟). | Les lignes sont recalculées avec la largeur réelle des caractères, sur PC et sur le téléphone. |

Aucun problème critique ou important n'est resté ouvert.

## 3. Sécurité : ce qui a été vérifié pour chaque enfant

- Le Poste est fini, ct0 → ct7, et l'exploit « la vague » est obtenu (tous les suspects arrêtés, veilleur épargné).
- Aucune étape n'a été validée par une commande qui a échoué. Seules exceptions : celles qui ont le droit d'être
  refusées (`dmesg`, `journalctl`, `tail -f` arrêté par Ctrl+C).
- Rien n'a été écrit hors du terrain et de `~/.terminagotchi`.
- Aucun processus du jeu ne reste à la fin.
- Ni `sudo` ni `useradd` n'ont été appelés : l'équipage est un fichier du Poste (`equipage.txt`).
- Aucun réveil du fichier n'a été lancé : pas de `ronde.log` ni de `veille.log`.
- Le jeu ne touche jamais à un processus qui n'est pas à lui : `kill` d'un numéro étranger reçoit un avertissement,
  et le jeu lui-même n'arrête que les numéros de `lances.json` dont le nom est encore le bon.
