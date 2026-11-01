# Simulation : trois enfants visitent la Forge (neuvième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_forge.py` (PC, rejouable à chaque test et
en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Forge.kt` (30 vérifications).

## 0. Comment on a joué

**PC.** Comme `sim_donnees.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Forge est ouverte d'avance comme
dans l'arbre du Carrefour (niveaux 0 à 4 du tronc commun).

**Hors ligne, rien d'envoyé.** `sudo` et `wget` sont des doublures qui refusent et notent qu'on les a appelées ; `curl`
ne passe que vers 127.0.0.1 / localhost. Le petit serveur web est le vrai `python3 -m http.server`.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : le code dans la sortie d'`echo $?`, le nombre de
tours dans `forge tours` (seq A Z), le nom de l'erreur dans la dernière ligne du Traceback, la marque de l'appareil dans
les métadonnées. Sans clavier ici : la devinette est jouée par un tuyau de réponses, « fg puis Ctrl+C » devient
`kill %1` (dans un bash non interactif, un travail lancé avec `&` ignore SIGINT).

| Enfant | Âge | Façon de jouer | Lignes tapées | Résultat |
|---|---|---|---|---|
| Léa | 7 ans | se trompe d'abord, lit l'indice, corrige | 88 | Forge finie, 10/10 vérifications |
| Inès | 12 ans | recopie la commande verte (« ? » compris), puis lit l'écran | 70 | Forge finie, 7/7 |
| Hugo | 15 ans | ses propres variantes (18 essayées, 18 acceptées) | 66 | Forge finie, 9/9 |

Pour les trois : aucune étape validée par une commande qui a échoué ; rien d'écrit hors du terrain et de
`~/.terminagotchi` ; aucun `sudo`, aucun réseau hors de 127.0.0.1 ; la lanterne (le serveur) est éteinte à la fin ; le
jeu de l'enfant est posé sur la carte ; l'exploit « un programme qui marche du premier coup » est donné une seule fois,
à la première recette **complète** lancée.

## 1. Léa, 7 ans (les fautes)

Ses fautes, et ce que le jeu lui a répondu (toutes ont reçu une explication) :
- une majuscule en tête de commande : l'indice habituel du tronc commun.
- `echo 'mkdir -p cabane' > cabane.sh` (un seul `>`) : la recette est effacée → « Oups : un seul > a effacé la recette.
  Réécris la ligne #!/bin/sh avec >, puis ajoute le reste avec >>. »
- `./cabane.sh` avant `chmod +x` : « Permission denied : la recette n'a pas encore le droit x. Tape chmod +x cabane.sh. »
- `nom = Pixel` (espaces) : **corrigé pendant la simulation** — avant, le jeu proposait « npm ? » ; maintenant :
  « Pas d'espace autour du = ! … Avec des espaces, le terminal croit que “nom” est une commande. »
- `sh salut.sh` sans prénom : « Donne un prénom après salut.sh : sh salut.sh Léa. »
- `forge code 0`, `forge tours` avec un tour de moins, `forge erreur Traceback` : chaque fois l'indice qui dit où lire.
- `curl localhost:8642` avant d'allumer la lanterne : **corrigé** — avant, rien n'expliquait l'échec ; maintenant
  « Allume d'abord la lanterne qui sert ta page (la commande http.server) ; curl juste après. »
- `python3 -m http.server 8642 --directory site &` **sans** `--bind 127.0.0.1` : vu au tour même, « ⚠ Ta lanterne
  écoute tout le réseau ! Éteins-la et rallume-la avec --bind 127.0.0.1 » ; l'étape ne passe pas tant que le serveur
  écoute 0.0.0.0 ; la simulation vérifie qu'il est éteint au tour suivant.
- `forge appareil TC-7` (le modèle au lieu de la marque), `forge bilan` trop tôt : l'indice, puis la liste de ce qui manque.

Constat : le palier des recettes, fini avec des indices, ne compte pas pour l'exploit « sans indice » (voulu).

## 2. Inès, 12 ans (recopie)

Elle tape la commande verte telle quelle, `?` compris : « Écris ta réponse à la place du ? » ; puis elle lit l'écran.
`forge carte` sans nom : **corrigé** — le jeu disait seulement que la commande « marche aussi » ; il donne maintenant
l'exemple `forge carte "La grotte de Pixel"`.

## 3. Hugo, 15 ans (ses variantes)

Acceptées (18/18) : `bash cabane.sh`, `chmod u+x cabane.sh`, `echo "Bonjour ${nom}"`, `for i in {1..3}`, `seq 10`,
`python3 -V`, `python3 -m http.server -b 127.0.0.1 -d site 8642 &`, `curl -s http://127.0.0.1:8642/`, `kill %1`,
`ffmpeg -y …`, `exiftool -s …`, `magick`/`convert`, etc. Il a obtenu l'exploit « sans indice » sur un palier.

## 4. Problèmes trouvés et corrigés

| # | Gravité | Problème | Correction |
|---|---|---|---|
| FO1 | important | `nom = Pixel` → le jeu proposait « npm ? » | `core.inconnue.egal` : explique « pas d'espace autour du = » (PC et téléphone) |
| FO2 | important | `nom=Pixel` comptait comme commande inconnue | une affectation `x=…` est reconnue (core.feed, verif.casse_ok, Verif.kt) |
| FO3 | important | `curl` avant la lanterne : échec sans explication | indice `fo.indice.allume_d_abord` |
| FO4 | moyen | `forge carte` sans nom disait « marche aussi » | `fo.carte.aide` avec l'exemple |
| FO5 | moyen | sur la carte, le dossier du jeu restait dans la brume | un dossier qui contient `.lieu` n'est jamais dans la brume (PC et téléphone) |
| FO6 | moyen | l'indice `./cabane.sh` n'était pas donné à l'étape `chmod` | condition élargie |
| FO7 | petit | `ffprobe` donnait 0,999909 s pour la fanfare | fanfare en 24 000 Hz (durée exacte) |
| FO8 | petit | sur le téléphone, serpent.py et devinette.sh en arabe et en ourdou contenaient des marques de sens d'écriture (≠ PC) | textes de fichiers sans ces marques des deux côtés (`tf`, vecteurs communs) |

## 5. Restes connus (assumés)

- `Ls fantome; echo $?` passe l'étape « $? » (le code 127 n'est pas 0, c'est bien « problème ») : la majuscule est déjà
  signalée ailleurs ; sans conséquence.
- Sur le téléphone : pas de Python (le serpent est raconté, puis `doom`), pas de magick/sox/ffmpeg/exiftool (la photo
  d'exemple, elle, est vraiment lue et nettoyée par l'appli), le site est servi par l'appli elle-même (127.0.0.1),
  « fg puis Ctrl+C » devient `forge serveur stop`.
- En CI, `fg` puis Ctrl+C est rejoué par `kill %1`.
