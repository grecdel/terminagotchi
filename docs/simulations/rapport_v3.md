# Simulations d'apprentissage, 3e passage

Date : 31 octobre 2026. Branche `nouveau-bestiaire`, version testée : commit `8ca337a` (avant les corrections).

Ce qui est nouveau depuis le 2e passage :
- l'intro en 5 étapes (3 écrans illustrés, le camp qui se réveille, l'œuf « en téléchargement ») ;
- l'éclosion du vrai bébé ;
- les créatures vivantes et les auras qui brillent selon le soin ;
- le bestiaire complet (832 variantes) ;
- les corrections C1 à C4 et I1 à I10 du 2e passage.

## 0. Comment on a joué

**PC.** Chaque enfant a un vrai compte d'ordinateur ordinaire (pas administrateur), avec son dossier `/home/<prénom>`.
On a lancé le vrai premier démarrage (`python3 -m tg`) dans un vrai terminal : les écrans d'intro, le nom de l'œuf,
« je m'installe dans ton terminal ? », puis le vrai bash avec la créature sous chaque invite.

**Android.** Un « élève » refait ce que fait l'écran du téléphone (la saisie, l'intro dessinée, l'œuf, les écrans
« Nouveau », le panneau de la leçon), avec le vrai code du jeu.

**Sans tricher.** Le joueur ne lit que ce qui s'affiche. Pour Léa, un robot recopie la commande en vert, fait les
fautes d'un enfant de 7 ans (majuscules, lettres oubliées, espace oubliée) et tape `aide` quand il ne sait plus.
Tom, Hugo, Sophie, Karim et Zoé ont été joués à la main.

**Limites honnêtes** (viennent du bac à sable, pas du jeu, et ne comptent pas comme défauts) :
- après le redémarrage de l'ordinateur de test, `/dev/null` était de nouveau fermé aux comptes ordinaires : `git`
  ne marchait plus (réparé, puis la partie a repris) ;
- l'éditeur `edite` du téléphone est une autre fenêtre : on a modifié le fichier à la place de l'enfant ;
- le robot ne sait pas recompter : la réponse de l'énigme finale a été tapée à la main (elle est bien acceptée, sur PC
  comme sur Android) ;
- `whoami` répond `nobody` ou `root` dans le bac à sable, et `man` n'y existe pas.

## 1. Les six profils en bref

| Profil | Plateforme | Jusqu'où | Lignes tapées | `aide` | Blocages | Ce qui gêne |
|---|---|---|---|---|---|---|
| Léa, 7 ans, tape mal | PC | les 10 chapitres, énigme finale réussie | ≈ 330 | 78 | 0 | faux message « vestibule n'est pas une commande » (I12) ; astuces de l'œuf disparues (I11) ; jamais vu l'épreuve d'un monstre (I16) |
| Léa | Android | les 10 chapitres, énigme finale réussie | ≈ 270 | 8 | **1** : l'éditeur ouvert dans un repaire (C5) | « Tu es dans : carte.piece.mecanique » (I13) |
| Tom, 10 ans, curieux | PC + Android | œuf éclos, chapitre 1 | ≈ 40 | 0 | 0 | son nom tapé au 3e écran est ignoré (I15, PC) ; « non » devient le nom de l'œuf (I14) |
| Hugo, 15 ans, pressé | PC + Android | œuf en une ligne, placement réussi, chapitre 2 | ≈ 25 | 1 | 0 | faux message « pwd; n'est pas une commande » (I12, PC) |
| Sophie, adulte | les deux | relit les textes « 🧑 », « 💻 », l'intro et l'aura | — | — | — | textes justes ; « C'est ce que `pwd` a montré » parfois faux (mineur) |
| Karim, expert | les deux | noms d'œuf piégés, séquences du terminal, commandes verrouillées | ≈ 30 | — | — | noms nettoyés ; petites fuites (mineurs) |
| Zoé, 9 ans, explore | Android (+ PC rapide) | `/`, `/tmp`, `cd ../../..`, œuf éclos | ≈ 20 | 0 | 0 | 3 messages pour un refus dans `/tmp` (mineur) |

### Léa (7 ans) — détail

| Question | PC | Android |
|---|---|---|
| Comprend-elle ? | Oui : l'intro, la liste de l'œuf (« ○ pwd ○ ls… ») et l'éclosion sont claires. | Oui, et le panneau de la leçon reste toujours visible. |
| Bloque-t-elle ? | Non (hors bac à sable). Mais après une erreur la commande verte n'est pas réaffichée : `aide` 78 fois (1 ligne sur 4). | **Une fois** : chapitre 8, `edite carte.txt` tapé dans un repaire (C5). |
| Apprend-elle vraiment ? | Oui : toutes les fautes sont rattrapées avec la bonne commande (`cdvestibule`, `ls-a`, `Pwd`…), sauf l'espace oubliée avant un chemin (I12). | Oui, même rattrapage (`cd/home/…` est bien compris). |
| S'ennuie-t-elle ? | Non : l'œuf, puis un chapitre à la fois. L'animation de l'œuf dure quelques secondes à chaque commande : joli, un peu long à la 4e. | Non. 51 écrans de monstre, 6 dressés : rythme vivant. |
| Satiété et aura | La jauge de faim (▰▰▰▱▱) n'a pas d'étiquette : à côté du « 70 % » de l'XP, on peut les confondre. | Les 6 envies en icônes (🍎🎮📚🧭😴🧹) sont plus claires. |
| Texte trop dur ? | « Un chemin qui commence par / part de la Racine : il marche de n'importe où, c'est un chemin qui part de la Racine » (répété, mineur). | Pareil. |

### Tom (10 ans, curieux)

| Question | Constat |
|---|---|
| Comprend-il ? | Oui. Les mots tapés sur les écrans du début font juste passer à la suite (ils ne deviennent plus le nom). |
| Bloque-t-il ? | Non. `exit` sur PC ramène à la fenêtre du jeu ; Entrée le renvoie au terminal (corrigé au 2e passage, vérifié). `exit` ne nourrit plus. |
| Incompréhensions | PC : il tape son nom sur le 3e écran (« Donne-lui d'abord un nom ! ») ; le nom est ignoré et redemandé (**I15**). Les deux : il répond « non » à « Ton œuf s'appellera… C'est bien ça ? » et l'œuf lui est proposé sous le nom « non » (**I14**). |
| Apprend-il ? | `bonjour` tout seul → PC : « tu voulais dire `echo bonjour` ? » ; Android : « je ne connais pas la commande » (mineur). `ls /` compte pour l'œuf : bien. |
| S'ennuie-t-il ? | Non. Il essaie `aura`, `envies` : « pas encore, tu le découvriras bientôt » — mais ces essais lui donnent de l'XP (mineur). |

### Hugo (15 ans, pressé)

| Question | Constat |
|---|---|
| Comprend-il ? | Oui : « p » saute l'intro ; `pwd; ls; echo bonjour; whoami` fait éclore l'œuf d'un coup (PC et Android). |
| Bloque-t-il ? | Non. Le placement passe en 5 lignes ; le `cd ..` du chapitre 2 explique bien de partir du vestibule (C1 corrigé, vérifié). |
| Incompréhension | PC : juste après l'éclosion, « « pwd; » n'est pas une commande… tu voulais dire « pwd » ? » alors que tout a marché (**I12**). |
| S'ennuie-t-il ? | Non : le mode « défi sans aide » après le placement lui va. |

### Sophie (adulte, relit les textes)

| Question | Constat |
|---|---|
| Textes de l'intro | Justes et simples (« `pwd` : l'ordinateur a écrit le chemin du dossier où tu es »). |
| Aura | « La lueur suit aussi le soin… si elle a faim, elle pâlit (rien de grave) » : clair et pas culpabilisant. |
| « 💻 vrai terminal » | Justes pour l'œuf et les chapitres joués ; `edite` → « tape plutôt `nano` » (corrigé au 2e passage, vérifié). |
| À reprendre | L'écran « Où sommes-nous ? » dit « Au camp de base : /home/… C'est ce que `pwd` a montré » même si `pwd` a été tapé ailleurs (Zoé l'a tapé à `/`) (mineur). |

### Karim (expert)

| Question | Constat |
|---|---|
| Nom d'œuf piégé | Les codes d'échappement et les caractères invisibles sont retirés ; `$(rm -rf ~)` reste un simple texte, jamais exécuté ; 16 caractères au plus. |
| Terminal PC | Au tout premier écran, la question « sais-tu afficher des images ? » envoyée au terminal (protocole Kitty) peut s'afficher en clair (`_Gi=31,s=1…`) dans un terminal qui ne la comprend pas (mineur ; GNOME Terminal l'ignore). |
| Commandes verrouillées | `aura`, `envies` « pas encore » donnent quand même de l'XP (mineur). |

### Zoé (9 ans, explore hors consignes)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui. « passer » mène droit au nom. L'œuf accepte `ls` et `pwd` tapés à la Racine. |
| `/tmp` sur Android | Le refus est maintenant expliqué (« garde /tmp en lecture seule pour protéger le téléphone ») — mais 3 messages pour un seul refus (mineur, déjà relevé). |
| `cd ../../..` à la Racine | Ne bouge plus, sans un mot (mineur, déjà relevé). |
| Écran « Où sommes-nous ? » | « C'est ce que `pwd` a montré : /home/explorateur » alors que son `pwd` a montré `/` (mineur). |

## 2. La satiété et l'aura : claires, pas punitives… mais trop rapides

On a mesuré sur PC ce qui se passe quand l'enfant ne joue pas (faim de départ : 90 sur 100).

| Absence | Faim | Aura | Visage | Commandes pour revenir à l'aura normale |
|---|---|---|---|---|
| 8 h (une journée d'école) | 50 | normale | normal | 0 |
| 14 h (une nuit) | 20 | pâle | normal | 4 |
| 24 h | 0 | grise, sans particules | triste (╥_╥) | 10 |
| 2 ou 3 jours | 0 | grise | triste | 10 |

- **Pas punitif** : rien n'est perdu, pas de mort, l'XP continue, et 10 commandes suffisent à revenir. L'aura pâlit en
  douceur et le texte dit « rien de grave ».
- **Mais trop rapide** : après une seule nuit, la créature a faim ; après une journée sans jouer, elle pleure et dit
  « Je suis à bout de forces… nourris-moi vite ! ». Pour un enfant qui ne joue pas tous les jours, c'est stressant.
  C'est exactement le constat de la proposition « satiété » validée le 29 octobre (faim seulement de 7 h à 21 h,
  3 fois plus lente, 4 états, mode vacances), **qui n'est pas encore codée**. Ce n'est pas une erreur du code : c'est
  une fonction qui reste à faire.
- **L'aura du soin ne se voit qu'avec un guide capturé** : la créature de départ n'a pas d'aura de rareté (sauf
  shiny), donc l'éclat qui suit le soin n'apparaît qu'après le premier dressage.
- Sur PC, l'Endurance ralentit la faim ; sur Android, non (petite différence entre les deux versions).

## 3. Problèmes classés

### Critiques (l'enfant reste bloqué) — corrigé

**C5. Android, chapitre 8 : l'éditeur s'ouvre au mauvais endroit, et l'étape ne passe jamais.** ✅ corrigé
- Les étapes « Mon premier niveau » (`edite carte.txt`), « Les réglages » (`edite reglages.txt`) et `cat carte.txt`
  n'avaient pas de lieu. Un monstre a emmené Léa dans un repaire (`mecanique/repaire_engrenaille`) : là, `edite
  carte.txt` ouvre une feuille **vide** (un autre fichier). Elle dessine, enregistre… et rien ne se passe, pour toujours.
- En plus, `aide` répondait « 📁 Tu es dans : carte.piece.mecanique. C'est le bon endroit. »
- *Correction :* ces trois étapes se tapent dans la « Salle de jeu » (`~/terrain_terminagotchi/jeu`). La leçon montre
  « `cd ~/terrain_terminagotchi/jeu` puis `edite carte.txt` », `aide` dit d'y aller, et si l'enfant tape `edite` ailleurs
  il lit « Bonne commande, mais pas au bon endroit ! Marche d'abord jusqu'au lieu Salle de jeu ».
- *Fichiers :* `Arbre.kt`, `Histoire.kt` (indice), nom « Salle de jeu » dans les 14 langues.
- *Test :* `tests/jvm/SimulationsV3.kt`.

### Importants (incompréhension réelle) — tous corrigés

**I11. PC : les astuces de l'œuf disparaissent après la première commande.** ✅
- La nouvelle intro n'affiche l'astuce que tant que le camp dort. Après `pwd`, l'enfant ne voit plus « Ce n'est pas
  grave si l'ordinateur ne comprend pas », ni « Si l'ordinateur n'affiche plus que >, appuie sur Ctrl+C » (la leçon du
  problème C2), ni ↑ et Tab. Sur Android, elles restaient.
- *Correction :* l'astuce du moment reste sous la liste de l'œuf jusqu'à l'éclosion. *Fichier :* `pc/tg/intro.py`.

**I12. PC : faux « n'est pas une commande ».** ✅
- `cd/home/lea/terrain_terminagotchi/vestibule` (espace oubliée) → « « vestibule » n'est pas une commande. Essaie : ls,
  pwd, cd ». Faux et inutile. `cd/` → aucun mot.
- `pwd; ls; echo bonjour; whoami` (Hugo) → la commande marche, puis « « pwd; » n'est pas une commande… ».
- *Correction :* « « cd/home/… » n'est pas une commande… tu voulais dire « cd /home/… » ? » ; le `;` ou le `|` collé
  n'est plus pris pour une partie du nom. *Fichier :* `pc/tg/core.py`.

**I13. Le nom brut « carte.piece.mecanique » s'affiche.** ✅
- Dans un repaire d'habitat (mecanique, abyssal, désert, marais…), `aide` et les indices affichaient la clé interne
  au lieu d'un nom (PC et Android).
- *Correction :* un lieu sans nom traduit garde son nom de dossier (« mecanique »). *Fichiers :* `Maison.kt`,
  `pc/tg/maison.py`.

**I14. « non » devient le nom de l'œuf.** ✅
- À « Ton œuf s'appellera « Tom le dragon ». C'est bien ça ? », Tom répond « non » : le jeu propose « Ton œuf
  s'appellera « non » ». Un Entrée de trop, et l'œuf s'appelle « non » (PC et Android).
- *Correction :* « non » (dans les 14 langues) fait reposer la question du nom. *Fichiers :* `pc/tg/intro.py`,
  `MenuParties.kt`, `TerminalActivity.kt`.

**I15. PC : le nom tapé sur le dernier écran de l'intro est ignoré.** ✅
- Le 3e écran dit « Donne-lui d'abord un nom ! ». Tom tape « Tom le dragon » : le jeu l'oublie et redemande
  « Comment veux-tu appeler ton œuf ? ». (Sur Android, ce nom était bien pris.) Déjà relevé en mineur au 2e passage.
- *Correction :* un mot tapé sur le dernier écran est proposé comme nom, puis confirmé. Les mots tapés sur les écrans
  d'avant font toujours seulement passer à la suite. *Fichier :* `pc/tg/intro.py`.

**I16. PC : l'épreuve du monstre reste invisible (I3 pas complètement réglé).** ✅
- La ligne « 🐾 Crânard : lis sa fiche… » n'apparaissait que si la dernière commande n'avait laissé aucun message. Or
  presque chaque commande en laisse un (« a mangé « ls » »). Léa a eu 2 monstres en 10 chapitres et n'a jamais vu ce
  qu'ils demandaient (ils ont été dressés par hasard).
- *Correction :* la ligne du monstre s'affiche sous le message. *Fichier :* `pc/tg/compagnon.py`.

Tests ajoutés : `pc/outils/test_simulations_v3.py` (34 vérifications) et `tests/jvm/SimulationsV3.kt` (23).

### Mineurs (notés, pas corrigés)

- **PC, après une erreur, la commande verte n'est pas réaffichée** sous l'invite (seulement le 💡 et « a goûté… ») :
  Léa a tapé `aide` 78 fois sur PC contre 8 sur Android. `aide` marche bien, mais c'est un détour. À surveiller.
- La jauge de faim du PC (▰▰▰▱▱) n'a pas d'étiquette, juste à côté du pourcentage d'XP.
- La satiété descend trop vite (voir partie 2) : la proposition validée le 29 octobre reste à coder.
- L'écran « Où sommes-nous ? » dit que `pwd` a montré le camp, même si `pwd` a été tapé ailleurs (Zoé à `/`).
- « Un chemin qui commence par / part de la Racine : il marche de n'importe où, c'est un chemin qui part de la
  Racine » : la phrase se répète.
- « Où taper ? … après le signe $ (ou >) » : or « > » est justement l'invite qui attend la fin d'une apostrophe.
- Écrans de l'intro PC : « 1/3 » à côté de 5 points (les 5 étapes) — un peu déroutant.
- Android : `bonjour` tout seul → « je ne connais pas la commande » (le PC propose `echo bonjour`).
- `Miam` (majuscule) sur Android → « Je ne connais pas la commande « miam » » au lieu de « en minuscules ».
- Les commandes « pas encore » (`aura`, `envies`) donnent de l'XP.
- La bulle « Bonjour le monde ! … » reste affichée longtemps après l'éclosion (Android).
- « 💡 Indice Presque ! » : il manque toujours une espace (panneau du dressage Android, déjà relevé).
- Android, refus dans `/tmp` : 3 messages pour un seul refus (déjà relevé).
- `cd ../../..` à la Racine ne bouge plus, sans un mot (déjà relevé).
- PC : la question « images ? » au terminal (Kitty) peut s'afficher en clair dans un terminal qui ne la comprend pas.
- La faim descend selon l'Endurance sur PC, pas sur Android.
- « ✔ Défi 2/4 : … » se lit comme si le défi 2 était déjà réussi (placement, déjà relevé).

## 4. Comparaison avec le 2e passage

| Problème du 2e passage | État | Vérifié par |
|---|---|---|
| C1 `cd ..` du chapitre 2 | **réglé** | Hugo, PC et Android, après le placement |
| C2 l'invite `>` et Ctrl+C | **réglé** pour l'invite ; l'astuce de l'œuf avait disparu avec la nouvelle intro → I11, corrigé | test |
| C3 la liste de courses (Android) | **réglé** | Léa Android, chapitre 5 sans blocage |
| C4 `~/tgrc` sans point | **réglé** | Léa Android : « Presque ! Tu as écrit .trc, il faut .tgrc » |
| I1 `aide` qui se contredit | **réglé** | Léa, 78 `aide` sans « commande inconnue » |
| I2 mode sans aide | **réglé** | Hugo : « à toi de trouver la commande ! » |
| I3 monstre invisible sur PC | **en partie**, fini avec I16 | Léa PC |
| I4 « 💻 » faux sur Android | **réglé** | Sophie |
| I5 `exit` | **réglé** | Tom PC |
| I6 faux messages d'erreur | **réglé** pour les alias et `cd -` ; nouveaux cas → I12, corrigé | Hugo, Léa |
| I7 `/tmp` | **réglé** (expliqué) | Zoé Android |
| I8 entre deux chapitres | **réglé** | Léa |
| I9 fautes d'enfant | **réglé** (`pwd,`, `bonjour`, barre oubliée) ; nouveau cas : espace oubliée avant `/` → I12 | Léa |
| I10 exemple du dressage à 7 ans | **réglé** : aucune attente d'exemple chez Léa | Léa Android |
| Mineur « nom tapé sur le dernier écran » | devenu I15, corrigé | Tom PC |
| Mineur « l'espèce du bébé jamais nommée sur PC » | **réglé** : « doudou est né ! · Bébé Momiaou » | Léa PC |

## 5. Ce qui marche bien dans la nouvelle version

- L'intro en 5 étapes est courte et claire ; le camp qui se rallume à la première commande fait vraiment plaisir.
- La liste de l'œuf (« ✓ pwd ○ ls ○ echo bonjour ○ whoami ») suffit pour savoir quoi taper, sans flèche.
- L'éclosion nomme le bébé et son espèce, puis récapitule les 4 commandes « comme un vrai informaticien ».
- Les fautes de frappe sont presque toutes rattrapées avec la bonne commande, sur les deux plateformes.
- Les 10 chapitres se jouent jusqu'au bout sur PC et sur Android, jusqu'à l'énigme d'Abyssor.

## 6. Ce qui reste à faire

1. **Coder la satiété validée le 29 octobre** (heures d'éveil, 3 fois plus lente, 4 états, mode vacances).
2. PC : réafficher la commande de la leçon sous l'invite après une erreur (moins de détours par `aide`).
3. Les mineurs ci-dessus, en particulier l'écran « Où sommes-nous ? » et la jauge de faim sans étiquette.
4. Des noms d'enfant pour les lieux d'habitat (mecanique, abyssal…) dans les 14 langues, au lieu du nom de dossier.

## 7. Rejouer

Dossier de travail : `/home/claude/outils/sim/v3/` (copie de la version testée dans `copie/` et `/opt/tg_sim/v3`).
- Session PC (compte ordinaire `/home/NOM`) : `./serve.sh NOM` en fond, puis `python3 js.py t NOM 'commande'`.
- Partie PC complète de Léa : `PREMIER="" python3 bot.py lea lea 400` (journal `logs/lea_pc_bot.txt`).
- Android : compiler `and/app.jar` (l'appli) et `and/eleve3.jar` (depuis `and/Eleve3.kt`), puis
  `python3 ajs.py serve NOM` en fond et `python3 ajs.py t NOM 'commande'` ; partie complète :
  `ANDROID=1 PREMIER="" python3 bot.py lea lea 400`.
- Satiété : `python3 py/nuit.py <copie du dépôt>`.
- Tous les tests : `M=/home/claude/outils/sim/out /home/claude/outils/sim/tout.sh all`.
