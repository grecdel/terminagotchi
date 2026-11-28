# Simulations d'apprentissage, 2e passage (Terminaworld = `/`)

Date : 30 octobre 2026. Branche `nouveau-bestiaire`, commit `03ee704` (« un vrai bébé de l'espèce tirée sort de l'œuf »).
Le code du jeu n'a pas été modifié. Toutes les parties ont été jouées sur une copie.

## 0. Comment on a joué

**PC.** Chaque enfant a un vrai compte d'ordinateur ordinaire (pas administrateur), avec un dossier `/home/<prénom>`. On a lancé le vrai premier démarrage (`python3 -m tg`) dans un vrai terminal :
- les 4 écrans d'intro ;
- le nom de l'œuf ;
- « je m'installe dans ton terminal ? » ;
- puis un vrai bash, avec la créature sous chaque invite.

**Android.** Un harnais refait `TerminalActivity.valider()` et `rafraichir()` de la version actuelle, avec le vrai `Shell.kt` et la Racine simulée (`Racine.kt`).

**Sans tricher.** Le joueur ne lit que ce qui s'affiche à l'écran : la commande en vert, les « 💡 », la ligne « 📁 » et `aide`. Il n'a jamais reçu d'XP en cadeau.

**Les outils** sont dans `scratchpad/sim/v2/` :
- `pj.py` et `js.py` : le terminal PC ;
- `ajs.py` et `and/Eleve2.kt` : Android ;
- `bot.py` : le robot qui fait des fautes ;
- `partie_pc.sh` et `partie_and.sh` : une partie complète.

Les journaux sont dans `scratchpad/sim/v2/logs/`.

**Tests automatiques du dépôt :** tous verts (13 tests PC, `parcours`, 14 suites JVM, et les personas Léa, Inès et Hugo).

**Limites honnêtes.** Les points suivants viennent du bac à sable, pas du jeu, et ne sont pas comptés comme défauts :
- `/dev/null` était fermé aux utilisateurs ordinaires (réparé) ;
- `getprop` n'existe pas hors du téléphone (simulé) ;
- l'éditeur `edite` d'Android a été simulé en modifiant le fichier à la main ;
- `man` est absent du système de test.

Quand un adulte a dû aider, c'est écrit « (adulte) » dans le journal et compté comme un **blocage**.

## 1. Les six profils en bref

| Profil | Plateforme | Résultat | Blocages (aide d'un adulte) |
|---|---|---|---|
| Léa, 7 ans, tape mal (majuscules, lettres oubliées, `cdvestibule`, `ls-a`) | PC | 10 chapitres, ≈ 320 lignes (dont ≈ 70 `aide`) | **3** : `cd ..` depuis le camp (C1) ; deux fois coincée sur l'invite `>` (C2) |
| Léa | Android | 10 chapitres, ≈ 340 lignes | **2** : liste de courses au mauvais endroit (C3) ; `~/tgrc` sans point (C4) |
| Tom, 10 ans, curieux (`bonjour`, `exit`, `rm`, `/etc`, `man`) | PC | chapitre 2 | aucun, mais `exit` le laisse dans une fenêtre qui n'écoute plus (I5) |
| Hugo, 15 ans (œuf en une ligne, `tg placement`, mode sans aide) | PC + Android | placement réussi en 5 lignes | **1 sur chaque plateforme** : juste après le test, `cd ..` ne mène pas au carrefour (C1) |
| Sophie, adulte (lit « Pour les grands » et « 💻 ») | les deux | 72 lignes « 💻 » relues | les « 🧑 » sont justes ; plusieurs « 💻 » sont fausses sur Android (I4) |
| Karim, expert | les deux | confinement Android solide | petites fuites de lecture, faux messages d'erreur (I6, mineurs) |
| Zoé, 9 ans, explore la Racine hors consignes | PC + Android | `/`, `/bin`, `/etc`, `/proc`, `/home`, `..` à la Racine | le jeu se tait pendant l'exploration libre ; `/tmp` se comporte différemment sur PC et Android (I7) |

## 2. La nouvelle hiérarchie (Racine, `~`, `..`, chemins absolus)

**Ce qui marche bien :**
- La leçon « Voyage jusqu'à la Racine » est claire : `cd /`, puis `ls`, puis `pwd`, puis `cd ~`, puis le chemin complet.
- Sur PC, le chemin du camp est vrai (`/home/lea`) : « la Racine → le village → ton camp de base ».
- `..` est enfin bien expliqué : « le lieu parent, un cran plus haut vers la Racine ».
- `cd -` reçoit un bon indice sur PC.
- La carte montre la Racine.
- `cd /` puis `ls` donne le bon bravo (« home, c'est le village ; etc, la salle des règles… »).
- Le refus d'écrire dans `/etc` est juste et expliqué.

**Ce qui reste faux ou flou :**
- **Le lieu attendu pour `cd ..` est faux** (voir C1). C'est la seule étape de la hiérarchie qui bloque.
- La forme `cd ~/terrain_terminagotchi/vestibule` est acceptée comme « chemin complet ». Pourtant, le texte pour enfant ne dit pas que `~/…` est aussi un chemin qui part de la Racine. Seul le texte des grands le dit.
- Sur Android, le chemin absolu `/home/explorateur/…` est présenté avec « 💻 marche pareil ». Sur un vrai ordinateur, c'est `/home/<ton nom>`.
- Sur PC, `cd ..` tapé à la Racine reste à `/` sans aucun mot. Zoé a fait `cd ../../../..` sans savoir pourquoi elle ne bougeait plus.
- L'écran « Où sommes-nous ? Au camp de base : /home/zoe » s'est affiché alors que Zoé était à `/`. L'écran arrive une commande trop tard.

## 3. Problèmes classés

Chaque point donne le fichier concerné et la façon de le reproduire.

### Critiques (l'enfant reste bloqué ou apprend quelque chose de faux)

**C1. L'étape « Remonte d'un cran : `cd ..` » (chapitre 2, `nid0` étape 0) ne sait pas d'où il faut partir.**
- `aide` répond « 📁 Tu es dans : ~. C'est le bon endroit », puis « Tu es dans : /. C'est le bon endroit ». Depuis `~`, `cd ..` mène à `/home`, puis à `/`. Le jeu ne dit jamais « va d'abord au vestibule ».
- Juste après `tg placement` (et `placement` sur Android), l'ado est au camp. Il n'a jamais vu le vestibule, et l'étape est impossible telle qu'elle est écrite.
- *Fichiers :* `pc/tg/verif.py` (`lieu_attendu`, `au_bon_endroit`) et l'étape `nid0` de `pc/tg/histoire.py` ; les équivalents `Verif.kt` et `Histoire.kt`.
- *Reproduire (PC) :* finir « Voyage jusqu'à la Racine », taper `cd` (retour au camp), puis `cd ..`, puis `aide`.
- *Reproduire (placement) :* `tg placement`, puis `pwd`, `cd /`, `cd`, `ls -a`, puis `cd ..`.
- *Piste :* le lieu attendu de `cd ..` est le vestibule. Il faut afficher « `cd ~/terrain_terminagotchi/vestibule` puis `cd ..` », ou accepter « arriver au carrefour » d'où que l'on vienne. Après le placement, commencer le chapitre 2 au carrefour.

**C2. Une apostrophe laisse l'enfant coincé sur l'invite `>`, sans explication.**
- Léa recopie l'indice du jeu « Tape ls pour voir ce qu'il y a ici, ou pwd pour savoir où tu es ». L'apostrophe ouvre une citation, et bash attend la suite avec `>`. Tout ce qu'elle tape ensuite (`aide`, `cd …`) disparaît. La créature ne parle plus, car l'invite du jeu ne s'affiche plus. Il a fallu un adulte pour Ctrl+C (deux fois dans la partie).
- Ctrl+C n'est enseigné qu'au chapitre 10, et seulement dans le texte des grands.
- *Fichier :* la clé `fr.json` de l'indice « n'existe pas là où tu es. Tape ls pour voir… » (`pc/tg/verif.py`).
- *Reproduire :* au chapitre 2, `mv nidsecours.txt reserve.txt`, puis taper la phrase de l'indice.
- *Piste :* mettre les commandes de l'indice en vert et sans phrase autour (`ls`, `pwd`) ; apprendre Ctrl+C dès l'œuf (« si l'ordinateur attend avec `>`, Ctrl+C ») ; dans la fenêtre `tg`, détecter une invite qui ne revient plus.

**C3. Android : la leçon « Le tuyau » (chapitre 5) peut valider des commandes au mauvais endroit, puis bloquer.**
- Un monstre arrive entre l'étape 2 (`echo banane > courses.txt`) et l'étape 3. Son dressage emmène l'enfant dans un repaire. Les étapes 3 et 4 (`echo pomme >> courses.txt`, `echo cerise >> …`) n'ont pas de « 📁 » : elles sont validées dans le repaire.
- `sort courses.txt` montre alors seulement « banane ».
- Ensuite, `cat courses.txt | grep pomme` ne trouve rien et est refusé à l'infini. Le message est contradictoire : « ✓ Fait. (Pas de message = tout s'est bien passé.) » plus « 💡 La commande a répondu par une erreur ».
- *Fichiers :* les étapes `tuyaux1` d'Android (`Histoire.kt` ou `Arbre.kt`, sans `ou`) et `TerminalActivity.valider()` pour « ✓ Fait » avec un code de sortie 1.
- *Reproduire :* `partie_and.sh lea lea 400`, journal `logs/lea_and_bot.txt`, autour de « Le tuyau ».
- *Piste :* donner `ou = "bibliotheque"` à toutes les étapes de `courses.txt` ; pour `grep`, dire « aucune ligne ne contient pomme : vérifie le contenu avec `cat courses.txt` » ; ne pas afficher « ✓ Fait » quand le code de sortie n'est pas 0.

**C4. Android : `~/tgrc` (sans le point) est accepté, et l'étape suivante devient impossible.**
- `echo 'miam() {…}' >> ~/tgrc` valide l'étape, car la règle `\S*tgrc` de `Arbre.kt` ligne 137 accepte n'importe quoi devant `tgrc`.
- Ensuite, `miam` répond « not found » pour toujours, et l'indice « relis le message » n'aide pas.
- *Reproduire :* au chapitre 8, taper `~/tgrc`.
- *Piste :* exiger `~/.tgrc` (ou vérifier que le fichier `~/.tgrc` contient `miam`) ; à l'étape `miam`, dire « la fonction doit être dans ~/.tgrc (avec le point) ».

### Importants

**I1. `aide` sur PC se contredit.**
- `aide` affiche la leçon, puis toute la notice du développeur (`terminagotchi.pyz mini … (Termux:Float)`, `tg drapeau TG{…}`), puis la créature ajoute « « aide » n'est pas une commande… tu voulais dire « guide » ? ✖ commande inconnue ».
- Pendant l'œuf, `aide` dit « Pas de leçon en ce moment : marche jusqu'à un lieu » au lieu de la commande suivante de l'œuf (`pwd`).
- *Fichiers :* l'alias `aide='tg aide'` de `pc/tg/compagnon.py` et le traitement de `tg aide` dans `pc/tg/app.py` ; la détection « commande inconnue » de `core`/`verif`, qui ne connaît pas les alias.
- *Reproduire :* taper `aide` à n'importe quel moment.

**I2. Le mode « sans aide » donne quand même la réponse.**
- Les lignes « 🧑 Pour les grands » et « 💻 … `mkdir nid` marche pareil » restent affichées.
- La bulle « Ta commande marche aussi… cette étape veut te faire découvrir `mkdir debarras` » donne aussi la commande.
- Sur Android, pendant `placement`, le panneau garde la leçon normale « ➜ `pwd` » sous le défi 1.
- *Fichiers :* `compagnon.annonces` (PC), `placement.cache` (pas appliqué aux lignes 🧑, 💻 et 💡) ; `Jeu.texteLecon` (Android).
- *Reproduire :* `tg placement`, réussir les 4 défis, puis regarder l'étape suivante.

**I3. Sur PC, les monstres sont annoncés une seule fois, puis plus rien.**
- Léa a lu « ⚔ Un monstre sauvage apparaît : Scarabouille ! » et n'a plus jamais vu ses épreuves dans son terminal : la ligne du compagnon montre toujours la leçon. Résultat : 0 dressage en 10 chapitres, et des fichiers `monstre_*.txt` qui traînent.
- Sur Android, c'est l'inverse : le panneau du monstre remplace la leçon.
- *Fichier :* `pc/tg/compagnon.py` (`ligne` et `annonces` ne montrent jamais `dressage`).
- *Reproduire :* `partie_pc.sh lea lea 400`, puis chercher « Scarabouille » dans `logs/lea_pc.log`.
- *Piste :* entre deux étapes de leçon, montrer l'épreuve du monstre en cours sur une ligne (« 🐾 Scarabouille : `cat …` »).

**I4. Android : la ligne « 💻 Dans un vrai terminal… marche pareil » est fausse pour plusieurs commandes.**
- C'est faux pour `doom`, `edite carte.txt`, `edite reglages.txt`, `getprop ro.product.model`, `echo … >> ~/.tgrc` (un vrai terminal lit `~/.bashrc`) et `cd /home/explorateur/…`.
- La ligne « 🧑 » juste au-dessus dit pourtant « commande de l'appli ».
- *Fichier :* `Vrai.kt`, qui n'exclut pas les commandes de l'appli (le suiveur PC, lui, les exclut).
- *Reproduire :* chapitre 6, étape `getprop`, et chapitre 8, `doom`.

**I5. Après `exit`, Tom se retrouve dans la fenêtre du jeu, qui ignore ce qu'il tape.**
- `touch nid/lit.txt` tapé dans cette fenêtre ne fait rien, sans aucun message. La touche `q` ferme tout (« À plus tard ! ») et il n'y a plus de terminal.
- De plus, `exit` est récompensé : « a mangé « exit » ★ nouveau goût ».
- *Fichiers :* `app.fenetre()` et `compagnon.proposer()`.
- *Piste :* « Entrée = retourner dans le terminal » ; si des lettres arrivent dans la fenêtre, dire « tape tes commandes dans le terminal ».

**I6. Faux messages d'erreur après des commandes réussies.**
- PC : `alias miam=…`, puis `miam` affiche « Miam ! », puis « « miam » n'est pas une commande… tu voulais dire « am » ? ». Les alias ne sont pas vus par la vérification.
- Android : `cd -` et `cd ..; cd ..; pwd` affichent la bonne réponse, puis l'orange « 🤔 Cet objet ou ce lieu n'existe pas ici ». La règle « toute sortie de `cd` = erreur » de `TerminalActivity.expliquer` se trompe.
- *Reproduire :* PC, chapitre 8, étape `miam` ; Android, `cd /` puis `cd -`.

**I7. `/tmp` n'est pas le même partout.**
- Sur PC, on peut écrire dans `/tmp`, comme sur un vrai Linux.
- Sur Android, la Racine simulée refuse : « le terrain vague est un lieu du système… on ne touche pas ». Le texte des grands parle alors de `/etc` (« écrire dans /etc échouerait aussi »).
- *Fichier :* `Racine.kt` (refus) et la clé du texte adulte.
- *Piste :* rendre `/tmp` modifiable dans la Racine simulée, ou expliquer que c'est une particularité du téléphone.

**I8. Entre deux chapitres, il n'y a plus de commande à taper.**
- PC : la ligne de la créature est vide ; seul « tg aile choisit un lieu » est passé dans un écran « Nouveau ».
- Android : « Marche jusqu'à un lieu (`cd grenier`, `cd cave`…) ». Ces `cd` relatifs ne marchent que depuis le carrefour. C'était déjà le point P2-1 du premier rapport.
- *Fichiers :* `compagnon.ligne` (PC), `Jeu.texteLecon` (Android).
- *Piste :* montrer `cd ~/terrain_terminagotchi/grenier`.

**I9. Les indices se trompent sur certaines fautes d'enfant.**
- Barre oubliée : `chmod 444 nidrepas.txt` et `touch nidlit.txt` donnent seulement « n'existe pas ici. Tape ls… », au lieu de « tu as oublié le / : `nid/repas.txt` ». En plus, `touch nidlit.txt` crée un fichier parasite.
- Virgule : `pwd,` donne « L'outil « pwd, » n'est pas installé sur cet ordinateur ». C'est faux.
- Mot connu : `bonjour` donne « Essaie : ls, pwd, cd », alors que `echo bonjour` est dans la liste de l'œuf.
- *Fichier :* `pc/tg/verif.py` (indices) ; équivalent `Verif.kt`.

**I10. La courbe de difficulté des dressages Android est trop raide pour un enfant de 7 ans.**
- Une épreuve affiche « Tape : l'exemple s'affiche dans 75 s (cherche d'abord dans le Lexique) », avec un chrono de 150 s. L'épreuve demande « gamelle DANS l'enclos » (`touch enclos/gamelle`) depuis un autre lieu.
- Léa a dû attendre l'exemple 2 fois sur 3. C'est ralenti par le jeu, mais ça devient de la frustration pour un enfant de 7 ans.
- *Piste :* au palier 7-9 ans, montrer l'exemple tout de suite.

### Mineurs

- Le texte « Halte ! un lieu du système est un lieu du système » se répète (PC et Android, quand le lieu n'a pas de nom). Le texte vient de la clé `carte.prudence.systeme`.
- Il manque un espace dans « 💡 IndicePresque ! » (panneau du dressage Android, 19 fois dans la partie). Déjà relevé au premier rapport.
- Sur Android, un refus d'écriture affiche encore 3 messages (le gardien, le texte des grands, puis l'orange).
- **Nouveau (œuf à type) :**
  - sur PC, l'espèce du bébé n'est jamais nommée (« Doudou est né ! ») ; Android l'affiche dans le titre (« Bébé Engrenaille ») ;
  - l'œuf « Glace, tout froid » devient ensuite « oeuf_tout_chaud.txt » et « tout chaud dans mon œuf » au vestibule ;
  - le message « Un œuf Glace ! » n'existe que sur PC.
- Sur l'écran 4 de l'intro PC, le nom tapé directement est ignoré : il faut le retaper.
- `touch coucou.txt` dans `/etc` affiche « il y a un cadenas sur « coucou.txt » ». En fait, le cadenas est sur le dossier `/etc`.
- `rm oeuf_tout_chaud.txt` et `rm -r vestibule` n'ont aucune réaction (le jeu reconstruit sans un mot) et sont récompensés. `rm -rf /tmp/x` donne « ★ nouveau goût » avant d'avoir appris `rm -r`.
- `cp nid/repas.tt nid/secours.txt` est validé : le fichier `repas.tt` venait d'une faute antérieure (`echo pomme > nid/repas.tt`).
- Sur PC, Zoé explore `/bin`, `/etc` et `/proc` librement et le jeu ne dit rien. C'est une occasion manquée de nommer les lieux (« salle des règles », « armurerie »).
- Placement : « ✔ Défi 2/4 : … » se lit comme si le défi 2 était déjà réussi.
- Racine simulée d'Android :
  - `..` à `/` n'est pas `/` lui-même (`ls -la /`) ;
  - `/etc/passwd` est absent ;
  - `ls ${HOME%%t*}` liste encore la vraie racine du système (lecture seule ; déjà relevé).
- Les stats « INT AGI FOR END » et « ATK DEF VIT PV » sont toujours dans l'en-tête Android dès que l'équipe est ouverte.
- La bulle « Une sieste éclair : `sleep 10` » arrive à la fin de la partie.

## 4. Comparaison avec le premier rapport

| Sujet (premier rapport) | État | Commentaire |
|---|---|---|
| P1-1 plantage du défi éclair | **réglé** | test de non-régression |
| P1-2 validation sur le texte (`PWD`, `Ls`, `ls -l nid` depuis la cave…) | **réglé** en grande partie | `PWD` et `Ls` sont refusés avec une explication. Reste C3, C4 et le `cp` du fichier parasite |
| P1-3 l'indice « pas au bon endroit » donne un mauvais lieu | **réglé** sauf `cd ..` | « `cd ~/…/bibliotheque` puis `head …` ». Nouveau cas : C1 |
| P1-4 indices absents du terminal PC | **réglé** | bravo, indices, Halte !, erreurs expliquées en français dans le terminal |
| P1-5 démarrage PC à deux fenêtres | **réglé** | une seule fenêtre ; reste `exit` (I5) |
| P1-6 un mot de l'intro devient le nom de l'œuf | **réglé** | le nom est confirmé. Petit reste : l'écran 4 ignore le nom |
| P2-1 `cd` relatifs dans « Quel lieu réveiller » | **reste** (Android) | I8 |
| P2-2 dressage : le lieu sur une autre ligne | **réglé** | la ligne « Où » est à côté de « Tape » |
| P2-3 les panneaux masquent la leçon | **reste** (Android) | PC : c'est l'inverse, le dressage est invisible (I3) |
| P2-4 erreurs du shell en anglais sur PC | **réglé** | « 🤔 « No such file… » : … n'existe pas là où tu es (Carrefour) » |
| P2-5 jargon | en partie | PC propre ; Android affiche encore les stats |
| P2-7 `aide` n'aide pas | **en partie** | la leçon est en tête, mais I1 |
| P2-10 fautes collées et majuscules | **réglé** | `cdvestibule`, `ls-a`, `cd..`, `PWD`. Nouveau : barre oubliée, virgule (I9) |
| Advanced P1-1 écritures hors du camp (Android) | **réglé** | `$HOME/..`, `rm $HOME/../sauvegarde.json` sont refusés |
| Advanced P1-2 `ls -la` refusé | **réglé** | personas Hugo |
| Advanced P1-5 `tg mini` sans ↑, Tab, alias | **réglé** (tests) | non rejoué à la main |
| Advanced P1-6 `..` mal expliqué | **réglé** | « le lieu parent, vers la Racine » |
| Advanced P2-2 `cd x && ls`, `cd -` (Android) | **réglé**, avec un faux message (I6) | |
| Advanced P2-3 processus orphelins | **réglé** | « 🧹 4 programmes… je les ai arrêtés » |
| Advanced P2-10 ennui de l'ado, test de placement | **réglé** | `tg placement` en 5 lignes ; nouvelles fuites (I2) et C1 |
| Advanced P2-11 parallèle « vrai terminal » | **réglé** sur PC | Android : I4 |
| `ls -l /etc/hostname` contredit sur Android | **réglé** | le texte des grands explique `r--r--r--` |
| « IndicePresque », 3 messages de refus, `rm` du vestibule sans mot | **reste** | mineurs |
| Nouveau | — | C1, C2, C3, C4, I1, I2, I3, I4, I5, I6, I7, I9, I10 ; œuf à type (mineurs) |

## 5. La courbe de difficulté

- **De l'œuf au chapitre 2 :** très douce. Les fautes de frappe sont toutes rattrapées avec la bonne commande. Le seul mur est C1 (`cd ..`).
- **Chapitres 3 et 4 :** bons. Les « `cd … puis …` » évitent les blocages de lieu du premier rapport.
- **Chapitre 5 (Android) :** le pic, avec les tuyaux, plus le combat, plus un dressage avec un exemple caché (C3, I10).
- **Chapitre 8 :** script, `chmod +x`, alias ou fonction, `git`. C'est dense pour 7 ans, mais ça passe si l'enfant ne fait pas de faute dans `~/.tgrc` (C4).
- **Chapitre 10 :** l'énigme marche avec le vrai compte trouvé par `grep` (il en a trouvé 4 dans la partie de Léa, et la réponse a été acceptée).

## 6. Ce qui manque encore pour « maîtriser le terminal »

- **Ctrl+C et l'invite `>` dès l'œuf** (voir C2). Aussi : `clear`, et ↑ et Tab utilisés dans une étape.
- **Les guillemets et les apostrophes** (C2 montre pourquoi), puis `2>`, `&&`, `;` et `$?`. Les jokers ont une vraie leçon (`*`, `?`).
- **`--help` et `man`** : `man` est absent des systèmes minimaux. Il faut enseigner `--help` d'abord.
- **Un éditeur sur PC** (`nano`), les variables, `PATH`, `.bashrc` (le vrai, pas `~/.tgrc`), les tâches (`fg`, `bg`), `cut`, `sort`, `uniq` et `tar` sur PC.
- **Les mondes avancés du programme** (Carrefour, Forge, Citadelle…) ne sont toujours pas jouables.
- **PC et Android enseignent encore des choses différentes** (G-09) : tuyaux et `sort` seulement sur Android ; `less`, `git` et `curl` seulement sur PC.

## 7. Les corrections les plus urgentes

1. **C1** : le lieu attendu de `cd ..` (`verif.lieu_attendu` et `Verif.kt`), et le début du chapitre 2 après le placement.
2. **C2** : des indices sans phrase recopiable autour des commandes, et Ctrl+C enseigné dès l'œuf.
3. **C3** : un « 📁 » sur toutes les étapes de `courses.txt` (Android) ; pas de « ✓ Fait » quand le code de sortie n'est pas 0.
4. **C4** : la règle `~/.tgrc` exacte (`Arbre.kt` ligne 137).
5. **I1, I2, I3** : `aide` qui ne se contredit pas ; un vrai mode sans aide ; le dressage visible dans le terminal PC.

## 8. Rejouer

Dossier de travail : `S=/tmp/claude-0/-home-claude/cfd82251-4fa5-55cd-8b51-4f0548d9aa8a/scratchpad/sim/v2`.

1. Copier le dépôt : `git archive HEAD | tar -x -C $S/copie`, puis copier ce dossier dans `/opt/tg_sim/copie` (lisible par tous).
2. Partie PC complète de Léa : `$S/partie_pc.sh lea lea 400`. Le joueur est l'utilisateur `nobody`, avec `/home/lea`.
3. Partie Android complète de Léa : `$S/partie_and.sh lea lea 400`. Avant, il faut `and/app.jar` (l'appli compilée) et `and/eleve2.jar` (compilé depuis `and/Eleve2.kt`).
4. Pas à pas sur PC : `python3 $S/js.py t NOM 'commande'`.
5. Pas à pas sur Android : `python3 $S/ajs.py t NOM 'commande'`.
