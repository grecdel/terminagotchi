# Plan de bataille — reprise du vendredi 30 octobre 2026, 16 h (Paris)

> Fichier interne de travail. La limite hebdomadaire des gros travaux se réinitialise vendredi à 16 h.
> Objectif : sortir **le plus tôt possible** des versions jouables et testables, puis dérouler le programme
> (`docs/programme.md`, partie 7) monde par monde. L'œuf physique vient en dernier.

## Règles de conduite pour toute la semaine

- **Visuels d'intégration d'abord (règle du propriétaire, 28 octobre)** : avant d'implémenter quoi que ce soit de
  visible (écran, illustration dans le jeu, créature du bureau, île, menu, nouveau monde, animation), préparer des
  **maquettes d'intégration** (captures simulées PC et téléphone montrant le rendu final dans le jeu) et les envoyer
  au propriétaire ; on n'écrit le code qu'après son accord.

- **Budget** : un gros agent à la fois, deux au maximum s'ils touchent des fichiers différents. Un point d'étape
  avec le propriétaire à la fin de chaque phase. Les variantes et illustrations (ChatGPT dans Chrome, peu coûteuses)
  avancent chaque jour en parallèle, quand le PC du propriétaire est allumé.
- **Git** : branche `nouveau-bestiaire` ; jamais `git add -A` ni `git commit -a` (index partagé entre agents) ;
  commit avec `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -- <fichiers>` et les deux
  lignes de fin (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`,
  `Claude-Session: https://claude.ai/code/session_01Divag9b9e52aPY37DGRpjJ`) ; `[skip ci]` sauf pour fabriquer un
  APK d'essai.
- **Interdits** : la mascotte du site dans le jeu ; déployer sur `main` sans accord ; écrire un jeton ou une clé ;
  `pkill -f` avec un motif large ; lancer `generer_jeu.py` sans prévenir (il réécrit `sprites.bin` et les portraits).
- **Tests** : `pc/outils/test_*.py`, `parcours.py`, `sim_suiveur.py`, `personas.py`, `verifier_langues.py`,
  `tests/langues_android.py --sync`, `node site/test/test.mjs`, `node site/test/tirage.mjs`, suites JVM avec le
  wrapper `scratchpad/regr/run.sh` et `LC_ALL=C.UTF-8` (voir `scratchpad/peda/tout.sh`). Si le scratchpad a disparu
  (redémarrage du conteneur), recréer le wrapper `setpriv` et relire ce plan.

## Phase 1 — Vendredi 16 h : la version jouable complète de l'intro (priorité absolue)

1. **Relancer l'agent « Vrai bébé à l'éclosion »** (SendMessage, il reprend où il s'est arrêté) :
   - espèce de départ tirée selon le type de l'œuf, éclosion qui finit sur son sprite **bébé**, compagnon = cette
     espèce dans tout le jeu, anciennes sauvegardes intactes ;
   - **œuf net sur Android** (grand, résolution suffisante, 3 états, animation) ;
   - texte « un œuf mystérieux » remplacé par le type, 14 langues.
2. **Ensuite, le même agent (pour éviter les conflits sur `IntroVue.kt` / `intro.py`) intègre les illustrations** :
   - 3 scènes : `scratchpad/illu/monde.png` (Terminaworld vivant), `dort.png` (endormi), `camp2.png` (camp de
     base, nid au centre, ordinateur branché aux racines) ; copies de sauvegarde à faire dans
     `donnees/illustrations/` dès vendredi 16 h (le scratchpad peut disparaître) ;
   - le camp apparaît d'abord **endormi** (même image désaturée et assombrie par le code), puis à la première
     commande : l'écran de l'ordinateur s'allume, la lumière remonte les câbles et l'arbre, la couleur revient ;
     l'œuf du type tiré apparaît dans le nid **« en téléchargement »** (demande du propriétaire, 28 octobre) : il se
     matérialise au fur et à mesure, ligne de pixels par ligne de pixels, avec une petite barre de progression et un
     pourcentage façon terminal (`réception de l'œuf… 37 %`), des pixels verts qui scintillent sur le bord en cours
     d'écriture, puis un petit éclat quand il est complet (PC : rendu ligne par ligne en demi-blocs ; Android :
     balayage animé) ;
   - Android : vraies images (assets réduits proprement) ; PC : version demi-blocs la plus lisible possible ;
   - captures de démonstration envoyées au propriétaire.
3. **APK d'essai** (commit final sans `[skip ci]`), lien envoyé au propriétaire : c'est la version qu'il attend
   pour tester.

## Phase 2 — Vendredi soir : données du jeu et site

1. `generer_jeu.py` (sprites + portraits de **toutes** les variantes dessinées), puis tous les tests ; commit.
2. **Mettre le site à jour** (accord donné le 28 octobre) : lancer le workflow « Mettre le site en ligne » sur la
   branche `nouveau-bestiaire` (`workflow_dispatch`, sans fusionner dans `main`), vérifier `site-info/url.txt` et
   les journaux, tester l'adresse en ligne.
3. Rappeler au propriétaire, avec un pas-à-pas simple, de régler le secret `SECRET_GRAINES` (anti-triche) — il le
   fait lui-même, la valeur n'est jamais écrite dans la conversation.

## Phase 3 — Samedi : simulations et corrections

1. **Relancer l'agent « Simulations d'apprentissage »** (SendMessage) sur la version de la phase 1 : 6 profils, PC et
   Android, nouvelle hiérarchie (Terminaworld = `/`), rapport `scratchpad/sim/rapport_v2.md` (le recopier dans
   `docs/simulations/` pour ne pas le perdre).
2. Un agent de corrections sur les points **critiques** et **importants** du rapport ; nouvel APK d'essai ;
   point avec le propriétaire.

## Phase 3 bis — La créature qui vit sur le bureau (PC et Android), inspirée de Mochi Desktop

Référence montrée par le propriétaire : <https://github.com/miflow13/mochi-desktop> (MIT, Python + GTK4, Fedora GNOME).
Ce qui plaît : une petite créature **sans fenêtre visible** qui vit sur le bureau, se promène, dort, réagit aux clics
et à l'activité de l'ordinateur, sans rien espionner. On s'en inspire (idées et comportements), sans copier son code
ni ses dessins : notre créature reste celle du joueur, avec ses sprites et ses 5 stades.

Existant : `pc/tg/bureau.py` (`tg bureau`, tkinter : petite carte toujours au premier plan, respire, cligne, bulle,
menu). À faire :
- **PC** : vraie transparence (sans carte sombre) sur Linux — GTK4 / XWayland ou Qt ; fallback tkinter conservé
  pour Windows et macOS ; la créature **marche** le long du bas de l'écran, s'assoit, dort, s'étire ; clic = le petit menu (voir plus bas),
  double-clic = cœur, triple clic = petite phrase, glisser = la déplacer ; **réactions locales** à l'activité (on tape → elle mange
  les miettes de commandes ; inactivité → elle s'endort ; batterie faible → elle bâille), **sans jamais lire** ce qui
  est tapé ni le titre des fenêtres ; lancement automatique à l'ouverture de session (option) ; installation par
  `tg bureau installer`.
- **Android** : une **bulle flottante** au-dessus des autres applications (permission « Afficher par-dessus les autres
  applications », demandée avec une explication) : la créature se balade sur le bord de l'écran, se range dans un
  coin, un appui ouvre le petit menu, un appui long la déplace, glisser vers le bas pour la ranger ; même
  comportement que sur PC ; économe en batterie (animation en pause quand l'écran est éteint).
- **Le petit menu** (demande du propriétaire, 28 octobre) : un **clic** sur la créature (PC) ou un **appui** (Android)
  ouvre un petit menu rond en pixel art autour d'elle, dans le style du jeu : **Jouer** (ouvre le jeu / le terminal),
  **Terminal** (ouvre directement l'invite), **Nourrir / s'occuper** (ses envies du moment), **Carte**, **Équipe**
  (choisir la créature affichée), **Réglages** (taille, son, vitesse, rester sur place, dormir, lancement au
  démarrage, notifications, langue), **La ranger / Quitter**. Les réactions (cœur, petite phrase) passent sur le
  double-clic et le triple clic ; le glisser déplace la créature. Le menu se ferme en cliquant ailleurs.
- **L'île du haut de l'écran** (inspiration montrée par le propriétaire : <https://github.com/Louis-CFM/coucou>, l'« île »
  du haut de l'écran qui s'ouvre avec les interactions ; idées seulement, aucun code ni dessin repris) :
  - **au repos** : une petite **pilule** translucide en haut au centre de l'écran, avec la mini-créature qui
    respire et 2-3 pastilles d'état (faim, XP, nouveauté) ; elle peut aussi se placer en bas ou sur un côté ;
  - **au survol ou au clic**, la pilule **s'agrandit en douceur** en un panneau : la créature parle dans une bulle
    (leçon du moment, « un monstre est apparu ! », « j'ai faim »), les **boutons d'action** (Jouer, Terminal,
    Nourrir, Carte, Réglages), et un **mini-terminal** intégré pour taper une commande sans rien ouvrir ;
  - **les événements** du jeu (monstre apparu, étape réussie, badge gagné, envie urgente) font **s'ouvrir l'île
    toute seule** quelques secondes, avec une petite animation, puis elle se replie ;
  - **effets** : fond sombre avec des particules de pixels qui s'écartent du pointeur, la créature qui fait coucou,
    sautille, et dont les yeux suivent la souris ;
  - **Linux** : île collée au bord du haut avec les bureaux qui le permettent (layer-shell : Sway, Hyprland,
    KDE…), petite fenêtre sans bordure en haut sur GNOME ; **Windows / macOS** : fenêtre sans bordure toujours
    au premier plan ;
  - **Android** : la même île en haut de l'écran (fenêtre par-dessus les autres applications, même autorisation
    que la bulle), plus la **notification permanente** déjà prévue ; un appui l'agrandit ;
  - réglable : activée ou non, position, ouverture automatique sur événement oui/non, discrète en plein écran.
  La créature du bureau et l'île sont **la même créature** : quand l'île s'ouvre, la créature du bureau peut y
  « sauter ».
- **Animations nécessaires** (catalogue § 7.15, à ajouter) : marche, assise, sommeil, étirement, bâillement, réaction
  au clic, cœur, mange — pour le stade bébé d'abord (créature de départ), puis les autres stades.
- **Contrôle** : tests (le compagnon ne lit aucune donnée personnelle), essais sur Fedora GNOME Wayland, Windows,
  Android ; captures et GIF envoyés au propriétaire.

## Idée à maquetter : la « vue déployée » d'une commande

Demande du propriétaire (28 octobre, d'après une vidéo Instagram qu'il a aimée) : voir la commande **se déployer** —
chaque morceau de la syntaxe s'allume à son tour pour montrer **où on en est**, et les **connexions** se dessinent.
Pour Terminagotchi : après (ou pendant) une commande, la ligne se décompose en blocs colorés (commande, options,
arguments, chemins, `|`, `>`, `&&`) qui s'illuminent dans l'ordre d'exécution ; les **tuyaux** deviennent de vrais
tuyaux animés où l'on voit passer les lignes de texte d'une commande à l'autre ; les **chemins** se relient au lieu
correspondant sur la carte du Terminaworld ; une redirection `>` montre le flux qui tombe dans le fichier ; une
commande réseau montre le messager qui part et revient. Mode « pas à pas » (Entrée pour avancer) et mode
automatique ; disponible sur PC (terminal, en couleurs ANSI) et Android (vue graphique), activable avec
`deploie <commande>` ou automatiquement dans les leçons. À maquetter avant toute implémentation (règle des visuels).

Captures envoyées par le propriétaire (projet Coucou), gardées dans `docs/inspirations/coucou_1.png` à `_4.png` :
- **Le laboratoire (captures 1-2)** : trois panneaux synchronisés — à gauche le **code**, avec la ligne en cours
  d'exécution surlignée ; à droite en bas la **machine à états** (états reliés par des traits, l'état actif qui
  brille, les transitions qui s'allument) ; à droite en haut la **créature en direct** dans cet état ; une liste
  d'états avec des interrupteurs pour forcer un état. Adaptation Terminagotchi : **« Le cerveau de ta créature »** —
  son vrai code (faim, jeu, sommeil, mange, confus, colère, content, KO, évolution…) qui se surligne pendant qu'elle
  vit, sa machine à états qui s'allume, et elle qui s'anime à côté ; l'enfant peut basculer un état pour voir le
  code réagir. Sert à la Forge (machines à états, `if`/`case`), à la Guilde (G2 « lire le code de ta créature ») et
  à la vue déployée des commandes (blocs de la commande à gauche, graphe des tuyaux au milieu, résultat à droite).
  Sur PC dans une fenêtre dédiée (`tg cerveau`, `tg deploie …`) ; sur Android en vue graphique.
- **L'île avec question (captures 3-4)** : la créature pose une question avec des boutons de réponse ; une rangée de
  pastilles montre ce qui tourne. Adaptation : quiz de leçon et choix rapides (« Quel guide pour la Citadelle ? ») dans
  l'île ; les pastilles = les créatures de l'équipe avec leur état (dort, a faim, prête). Les accessoires (lunettes…)
  ne sont pas repris : le propriétaire a écarté les accessoires au profit des badges et des auras.


## ✅ Codé (31 octobre) — Thèmes, interface évolutive, personnalisation de l'espace (maquettes validées)

Maquettes validées par le propriétaire (Game Boy inversé : fond #0F380F, texte vert clair). Code :
- `pc/tg/apparence.py` / `Apparence.kt`, données `donnees/apparence.json` (copies `pc/tg/apparence.json`,
  `app/src/main/assets/apparence.json`), vecteurs communs `donnees/apparence/vecteurs.json`, tests
  `pc/outils/test_apparence.py` et `tests/jvm/Apparence.kt` (contraste WCAG de chaque thème : texte ≥ 4,5, texte doux et
  blocs ≥ 3 ; calendrier ; migration ; dispositions identiques Python / Kotlin) ;
- **9 thèmes** par rôles de couleur (sombre, clair, pastel, Matrix, ambre, Game Boy, océan, contraste élevé,
  daltonien) : recoloration de la liste de dessin (espace, bureau, île, téléphone, bulle de l'espace), carte teintée en
  Matrix / ambre / Game Boy, sprites jamais touchés ; dans un vrai terminal, seules les couleurs vives changent (thèmes
  sombres) ; `tg theme <nom>` / `theme <nom>` ; synchronisé par le recensement (le plus récent gagne : champs
  `theme` / `themeDate` du worker — **le site doit être redéployé** pour que le serveur garde le thème) ;
- **interface évolutive** : œuf + invite → éclosion (île) → t0 (Explorateur, Envies) → fin du chapitre 1 (Carte,
  Leçon) → nid1 (vue déployée, assiette) → 1re capture (Équipe) → « La loupe du détective » (Tuyaux ; nouvelle étape
  `cat … | grep Abyssor`, PC et Android) → scripts0 (Cerveau) ; animation d'arrivée (bord doré, « nouveau ») et
  phrase `app.pan.<id>.dit` ; places endormies en pointillés (PC) ; « Tout afficher » (Options › Pour les grands,
  après un calcul pour les grands, réversible) ; anciennes parties : tout visible, thème Sombre, disposition Classique ;
- **options** réorganisées (PC terminal : Apparence, Ma créature partout, Notifications, Compte, Pour les grands ;
  PC fenêtre : roue dentée de `tg espace` ; Android : `options`) ;
- **personnalisation** : PC `tg espace` bouton ✎ (et `ranger`) : grille 24 × 20, glisser par la poignée, agrandir par
  le coin, ✕ pour cacher, tiroir des dalles cachées, Disposition d'origine, « Ma disposition » ; dispositions
  classique / terminal géant / créature au centre / classe ; Android : appui long sur une bande, ≡ pour la déplacer,
  tailles P / M / G, ordre des onglets, dispositions ; les dalles pas encore découvertes n'apparaissent pas.
- Captures : `pc/outils/capture_apparence.py` (PC), `/home/claude/outils/themes/VraiTel.kt` (téléphone) ; textes :
  `donnees/apparence/outils/textes_apparence.py` (14 langues).

## L'espace de travail de Terminagotchi (souhait du propriétaire, 28 octobre)

**✅ Codé (31 octobre, PC et Android, d'après les maquettes validées `docs/maquettes/espace_travail_*.png`)** :
- PC : `tg espace` (GTK 4, repli tkinter ; `tg espace classe` grand écran ; `tg espace texte` dans un terminal d'au
  moins 150 × 40), `pc/tg/espace.py` (réutilise `bureau.Controleur` : jeu, album, île, mini-terminal) et
  `pc/tg/espace_scene.py` (liste de dessin, captures PIL : `pc/outils/capture_espace.py`) ;
- vue déployée : `pc/tg/deploie.py` / `Deploie.kt` (`deploie <commande>`, `deploie --pas …`, alias bash/zsh qui coupe
  le tuyau par un `#` et relit l'historique ; récap automatique après une étape de leçon composée) ;
- cerveau : `pc/tg/cerveau.py` / `Cerveau.kt` (`tg cerveau`, onglet Cerveau) : un vrai `case` shell interprété ligne
  par ligne (vérifié identique à bash), états forçables ;
- Android : commande `espace` (`espace classe`), `deploie`, `cerveau` ; `EspaceEtat.kt` (logique testée JVM),
  `EspaceDessin.kt` (dessin, interface `Toile`), `EspaceVue.kt` (View) au-dessus du terminal existant ;
- vecteurs communs `donnees/espace/vecteurs.json`, tests `pc/outils/test_espace.py`, `tests/jvm/Espace.kt`.
Le messager des commandes réseau dans la vue déployée est fait (31 octobre, avec le Port : `deploie.messager`, PC en
ANSI et `PortDessin.messager` sur Android, vecteurs `donnees/port/vecteurs.json`) ; seule la fenêtre `tg espace` du
PC (`espace_scene`) ne le dessine pas encore. Reste : la carte du PC en fenêtre reliée aux vrais lieux système
(/etc…), la vraie transparence des panneaux sous tkinter.

Le propriétaire adore l'interface des captures Coucou (`docs/inspirations/coucou_1.png` à `_4.png`) et veut
travailler l'**espace de travail** du jeu dans cet esprit : fond très sombre, panneaux arrondis aux bords fins,
typographie nette, accents de couleur lumineux, tout synchronisé. À **maquetter en priorité vendredi** (avant toute
implémentation), PC d'abord puis adaptation téléphone. Première proposition de disposition :
- **Barre du haut** : l'île (créature miniature, état, équipe en pastilles, réglages, son).
- **Colonne de gauche** : *Explorateur* = l'arborescence du terrain / du Terminaworld (le lieu courant surligné) ;
  *Envies* de la créature avec leurs jauges ; *Équipe*.
- **Centre** : le **terminal** (l'outil principal), avec la **vue déployée** de la dernière commande juste au-dessus
  (blocs qui s'allument, tuyaux animés).
- **À droite en haut** : la **créature en direct** dans son état (grande, animée).
- **À droite en bas** : un panneau qui change selon le contexte — la **carte** du Terminaworld (où l'on est), la
  **machine à états** (« le cerveau »), le **graphe des tuyaux** d'une commande, ou la leçon en cours.
- Thème « terminal rétro × pixel art 16-bit » conservé pour la créature et les illustrations ; les panneaux prennent
  le style de Coucou. Mode grand écran pour la classe.

## Phase 4 — Dimanche et début de semaine : les fondations du programme

**✅ Codé (31 octobre, PC et Android, 14 langues)** :
- charte : `donnees/programme.json` (copié dans `pc/tg/` et les assets Android), 63 fiches notions (enfant, grands,
  vrai terminal, limite de l'image, idée fausse, sources, `relu_par` vide en attendant le comité), `pc/tg/programme.py`
  / `Programme.kt` (`explique` montre la limite et l'idée fausse) ; `pc/outils/verifier_programme.py` (chaque étape PC
  et Android a sa fiche, aucune orpheline, 14 langues, copies identiques) ; `pc/outils/rejeu_bash.py` (chaque vraie
  sortie des fiches dans un bash neuf sur un terrain jetable, puis toute l'histoire du PC jouée en vrai bash avec les
  affirmations du jeu vérifiées) et le workflow `.github/workflows/rejeu.yml` ; écart trouvé et corrigé :
  `hist.reveil1.3.adulte` (« `ls` montre le fichier de l'œuf » : bash en montre 6) ;
- Ponts des Nombres : graphe des prérequis (comptage → addition → soustraction / multiplication → division → modulo ;
  puissances → binaire ; passerelles à venir : hexadécimal, pourcentages, moyenne…), `maths <question>` (`tg maths`,
  même moteur que `cherche`), « je ne connais pas » (seul ou après `maths`) jamais bloquant, pile de retour ; fiches
  comptage, addition, soustraction, multiplication, division, modulo, puissances, binaire, chacune avec 3 exemples et
  un exercice généré dont la réponse est vérifiée par bash ; `pc/tg/maths.py` / `Maths.kt`, vecteurs
  `donnees/maths/vecteurs.json` ;
- récompenses par monde : `pc/tg/recompenses.py` / `Recompenses.kt` ; un exploit donne des faveurs (3 rencontres :
  le jeu garde, parmi 4 compteurs de la graine, la première créature du monde en variante rare ; 1 rencontre légendaire
  parmi 8) ; variantes réservées par monde ; série parfaite (5 médailles d'or) ; **le tirage serveur n'a pas changé** :
  chaque créature gardée est le tirage exact d'un (graine, compteur), vecteurs `donnees/recompenses/vecteurs.json`
  vérifiés en Python, Kotlin et JavaScript (`site/test/tirage.mjs`) ;
- coquilles de l'espace de travail PC : polices des captures et de la fenêtre à la taille exacte (les commandes vertes
  recouvraient l'espace d'avant : « découvrirls -R », « …terminagotchipu… »).
Reste : brancher les exploits sur les mondes quand ils existeront (aujourd'hui seule la série parfaite de la salle
d'entraînement en déclenche), la question « Tu connais… ? » posée avant une étape qui déclare `maths` (les étapes des
mondes), l'animation pixel art des ponts, la relecture humaine des fiches (`relu_par`).

1. **Charte de rigueur** (§ 7.1) : `donnees/programme.json` (fiches notions : enfant, grands, vrai terminal,
   limite de l'image, idées fausses, sources), `pc/outils/verifier_programme.py`, rejeu des sorties réelles en CI,
   d'abord sur le **tronc commun**.
2. **Ponts des Nombres** (§ 7.10) : graphe des prérequis, `maths <question>` (même moteur que le lexique), « je ne
   connais pas » jamais bloquant ; premières fiches (division, modulo, puissances, binaire).
3. **Récompenses par monde** (§ 7.6) : rencontres et variantes rares débloquées par les exploits.

## Phase 5 — Les mondes, un par un (ordre du § 7.14)

Port (avec le réseau simulé où les biomes sont des machines) → Citadelle et ses boîtes → Crypte des Codes →
Salle des Rouages (avec VM réelles) → Tour des Ondes → Guilde des Bâtisseurs Libres → Observatoire de l'IA →
Données (SQL) / Forge (site web, multimédia) / Contrôle (Linux de A à Z) / Temps / Atelier (embarqué) → Sommet ;
mode classe en parallèle. Pour chaque monde : fiches → étapes PC et Android → tests → simulations → illustrations
(planche à valider par le propriétaire) → APK d'essai.

**⚓ Le Port — codé (31 octobre).** 11 fiches (`donnees/port/outils/fiches_port.py`, rejeu bash vert), leçons P0 →
P11 sur PC (`pc/tg/port.py`) et Android (`Port.kt`, `PortDessin.kt`), ouvert après le nid et la bibliothèque (arbre
du Carrefour), réseau simulé en boucle locale `127.42.0.0/24` (`donnees/port.json`), vrai phare HTTP/HTTPS sur
`127.0.0.1` lancé par le jeu (Android : dans l'appli), exploits « messager guidé » et « sceau vérifié » qui libèrent
`plumange:orage`, `tortunivers:lagon`, `empyria:nuage` ; 14 langues ; tests `pc/outils/test_port.py`,
`tests/jvm/Port.kt`, simulation `pc/outils/sim_port.py` → `docs/simulations/rapport_port.md`. Maquettes et prompts
d'illustrations envoyés au propriétaire (à valider). Reste : la carte du réseau dans l'onglet de l'espace (maquette
seulement), les illustrations B4/C1/C3/E1-E4/E14, P4 (ssh) seulement raconté sur Android, le Grand Maillage.

**🏰 La Citadelle — codée (31 octobre).** 13 fiches (`donnees/citadelle/outils/fiches_citadelle.py`, rejeu bash
vert), leçons cit0 → cit16 (64 étapes) sur PC (`pc/tg/citadelle.py`) et Android (`Citadelle.kt`,
`CitadelleDessin.kt`), ouverte après le nid, la bibliothèque et la cave (niveaux 4 et 6 du tronc). Paliers C1 à C7 :
utilisateurs et groupes simulés, chmod/umask (dans le terrain seulement, jamais de `sudo`), registre du gardien,
glitchs et ver (`find -newer`, pont vers le Temps), cheval de Troie et processus fantômes (`sleep` renommés, simulés
sur Android), `sha256sum`, sauvegarde contre le Verrouilleur, chiffrement `openssl` avec une clé d'EXEMPLE, faux
facteur (hameçonnage, `diff`), phrases de passe d'exemple, les boîtes « énumération », « droits », « secrets »
(drapeaux déterministes, inspecteur), pare-feu (`ss`) et la grande vague ; pont `curl` depuis le Port. Données
`donnees/citadelle.json` (adresses RFC 5737, noms RFC 2606), vecteurs communs `donnees/citadelle/vecteurs.json`.
Vue déployée : les cadenas r/w/x qui s'allument (`tg deploie chmod …`, écran Espace). Exploits : une « boîte
maîtrisée » par boîte (son gardien devient rencontrable glitch, voir ci-dessous) et « vague repoussée » ; les 4
variantes Démons (`ricanombre:arcane`…) sont retournées au tirage normal le 31 octobre ; 14 langues ; tests `pc/outils/test_citadelle.py`, `tests/jvm/Citadelle.kt`, simulation
`pc/outils/sim_citadelle.py` → `docs/simulations/rapport_citadelle.md`. Prompts d'illustrations envoyés au
propriétaire (à valider), repli dessiné en attendant. Reste : les illustrations B3/C1/C3/C5/D1/E13/E17-E19, les cinq
autres catégories de boîtes.

**🗝 La Crypte des Codes — codée (31 octobre).** 14 fiches (`donnees/crypte/outils/fiches_crypte.py`, rejeu bash
vert), leçons cr0 → cr14 (63 étapes) sur PC (`pc/tg/crypte.py`) et Android (`Crypte.kt`, `CryptePgp.kt`,
`CrypteDessin.kt`), ouverte **après la Citadelle** (1er novembre : mêmes prérequis qu'elle, niveaux 0 à 6, plus sa
porte `cit0` — `requis_lecons` ; l'escalier sous la Racine). Cryptographie K1 → K8 :
encoder n'est pas chiffrer (base64, hexadécimal, 5 messages « secrets » démasqués), César / ROT13 / analyse de
fréquences (grimoire mystère au décalage propre à chaque partie, `crypte roue`), empreintes SHA-256 (effet avalanche,
sceaux vérifiés par `sha256sum -c`), mots de passe (base FICTIVE, attaque par dictionnaire lue avant d'être lancée,
sel `openssl passwd -6`), coffre à une clé (`openssl enc` avec la clé d'EXEMPLE), cadenas ouvert (peintures de
Diffie-Hellman, `gpg` TOUJOURS `--homedir .trousseau` dans le terrain, clés RSA d'exemple `@crypte.example`, chiffrer
pour la créature, signer, vérifier), hasard (`/dev/urandom`, `openssl rand`, le dé truqué d'un glitch), demain (quiz
vrai / faux / on ne sait pas encore : quantique, post-quantique, métadonnées). Blockchain B1 → B6, explication
technique uniquement : registre modifiable sans trace, chaîne d'empreintes que l'enfant casse puis répare
(`verifie_chaine.sh`, `crypte chaine`), copies des 9 biomes et biome tricheur (consensus), minage minuscule
(`mineur.sh`, au plus 3 zéros, s'arrête seul ; table 16^d), transactions signées ajoutées à la chaîne (`crypte
signe`), vitrine du fonctionnement (monnaie, NFT, contrats, consensus : aucune monnaie, aucun jeton, aucun achat, aucun
avis) et carnet de bord infalsifiable vérifié par l'enfant (`crypte recensement`). Sur le téléphone, `gpg` et `openssl`
sont intégrés (sous-ensemble OpenPGP : RSA, signatures v4, clearsign, chiffrement SEIPD/MDC ; `passwd -6`), testés dans
les deux sens contre les vrais outils. Ponts des Nombres : hexadécimal, modulo, puissances, puissance modulo,
probabilités (jamais bloquants). Vue déployée : la roue de César qui tourne pour `tr 'a-z' 'd-za-c'` (`tg deploie`,
écran Espace). Exploits : « chaîne réparée sans indice » (`crypte.chaine`, rencontres favorisées d'une variante rare Ombre ou
Glace) et « carnet de bord vérifié » au bout de B6 (`crypte.b6`, une rencontre légendaire favorisée) ; variantes
existantes réservées à la Crypte (visibles après un de ses exploits) : `corbouh:crypte` (1er novembre, à la place de
`heaumbre:crypte` : Heaumbre est le gardien glitch de la boîte « droits »), `fractalis:cristal`,
`givrarde:aurore`, `lichonarque:crypte` (« gardienne du registre », validée le 1er novembre) ; 14 langues ; données `donnees/crypte.json`, vecteurs
communs `donnees/crypte/vecteurs.json` ; tests `pc/outils/test_crypte.py`, `tests/jvm/Crypte.kt`, simulation
`pc/outils/sim_crypte.py` → `docs/simulations/rapport_crypte.md`, captures `pc/outils/capture_crypte.py`. Prompts
d'illustrations envoyés au propriétaire (à valider), repli dessiné en attendant. Au passage : le tableau de garde de
la Citadelle replie ses étiquettes rouges sur téléphone, un processus fictif de la grande vague n'est plus oublié
juste après son lancement, `time` ou les commandes du jeu ne sont plus pris pour des fautes de frappe, et quand
plusieurs mondes s'ouvrent ensemble (Port et Crypte), ils sont annoncés un par tour. Reste : les illustrations B12/C2/E10/E11.
Garde-fou `gpg` (CR1, validé le 1er novembre) : `tg installer` pose dans `~/.bashrc` et `~/.zshrc` une petite
fonction `gpg` (et `gpg2`) qui, DANS le terrain, refuse de partir si son trousseau (`--homedir`, sinon `GNUPGHOME`)
n'est pas lui aussi dans le terrain, et montre gentiment la bonne commande (`gpg --homedir .trousseau …`, 14 langues) ;
hors du terrain, gpg reste celui des parents ; `tg desinstaller` l'enlève avec le reste (`compagnon._garde_gpg`,
tests en vrai bash — et zsh en CI — dans `pc/outils/test_crypte.py`, Léa de `sim_crypte.py` est arrêtée). Pas de
fish ni PowerShell pour l'instant.

**⚙ La Salle des Rouages — codée (31 octobre), renommée le 1er novembre** (ex-« Salle des Machines » : 14 langues,
carte, annonces ; l'aile du volcan reste « la salle des machines » ; identifiants internes `machines` / `machinerie`
inchangés). 11 fiches (`donnees/machines/outils/fiches_machines.py`, rejeu bash
vert), leçons sm0 → sm10 (65 étapes) sur PC (`pc/tg/machines.py`) et Android (`Machines.kt`, `MachinesDessin.kt`),
ouverte après les niveaux 0 à 3 du tronc (lire et chercher) ; chapitre `machinerie`, dossier `machines`, commande
`machines …` (alias `machines='tg machines'`). Paliers M1 → M7 en **lecture seule** sur la vraie machine (jamais de
`sudo`, rien d'écrit hors du terrain, ni nom de machine, ni nom d'utilisateur, ni numéro de série, ni adresse MAC
enregistrés) : les organes (`nproc`, `free -h`, `lsblk`, `lspci`, `lsusb`, `/proc/cpuinfo` ; le téléphone : `getprop`),
l'ordinateur ouvert dont les pièces s'allument quand une commande les interroge (`machines ouvre`, et dans la vue
déployée `tg deploie nproc` / écran Espace), des 0 et des 1 (`printf %x`, `xxd -b`, son prénom en interrupteurs, jamais
gardé ; Ko / Kio sur une photo de 1 Mio), le réveil étage par étage avec les vraies valeurs (UEFI ou BIOS, noyau,
premier programme ; `dmesg` et `systemd-analyze` acceptés même refusés), le chef d'orchestre (système, licences,
distributions), la maison dans la maison (`/proc/1/cgroup`, boîte détectée), M5 bis **avec un adulte** (rien ne
s'installe ; `conteneur_jetable.sh` se lit, explique avant de télécharger, lance un conteneur alpine `--rm
--network=none` rangé dans `machines/conteneurs/` ; `qemu-img create` d'un disque qcow2 dans le terrain ; `virsh -r` ;
aucune `virt-install` ; tout raconté sur Android et quand l'outil manque), la ferme de serveurs, l'énergie et la
sauvegarde 3-2-1 (`tar`, `sha256sum`, copies au disque 2 et « loin », incendie fictif, `sha256sum -c`, restauration)
et « Monte ta machine » (niveau 1 en sm2, épreuve en sm10 : besoin tiré par partie, pièces génériques, budget en points
fictifs, aucune marque ni prix, drapeau `TG{…}`). Les réponses (cœurs, mémoire, noyau) sont calculées par le jeu sur
la même machine ; le rejeu bash compare (`egal_jeu`). Ponts des Nombres : hexadécimal, binaire, puissances,
multiplication, addition (jamais bloquants). Exploit « Monte ta machine réussi au premier démarrage »
(`machines.premier_demarrage`) ; variantes existantes réservées : `chaudrogre:mecanique`, `homardeur:mecanique`,
`golemmur:desert`, `magmastodonte:canyon` ; 14 langues ; données `donnees/machines.json`, vecteurs communs
`donnees/machines/vecteurs.json` ; tests `pc/outils/test_machines.py`, `tests/jvm/Machines.kt`, simulation
`pc/outils/sim_machines.py` → `docs/simulations/rapport_machines.md`, captures `pc/outils/capture_machines.py`.
Prompts d'illustrations envoyés au propriétaire (à valider), repli dessiné en attendant. Reste : les illustrations
B9/C1/C3/E7/E8/E9, les portes logiques (§ 7.10), les étapes `podman` / `qemu-img` / `virsh` jouées seulement en CI, le
nom (l'aile du volcan s'appelle déjà « la salle des machines »).

**📡 La Tour des Ondes — codée (1er novembre).** 9 fiches (`donnees/ondes/outils/fiches_ondes.py`, rejeu bash), leçons
on0 → on10 sur PC (`pc/tg/ondes.py`) et Android (`Ondes.kt`, `OndesDessin.kt`), ouverte après le niveau 4 du tronc et
les leçons « Les ports » (P7) et « Des 0 et des 1 » (M2) — l'annonce part à la fin de ces leçons ; chapitre et dossier
`ondes`, commandes `ondes …`, `mesh-route`, `mesh-envoie`, `mesh-coupe` (alias bash/zsh/fish/PowerShell). Règle du
monde : **écouter est libre, émettre est réglementé ; le jeu n'émet jamais lui-même**. W1 l'onde (fréquence, longueur
d'onde avec `bc`, le mur qui affaiblit plus les hautes fréquences), W2 les ondes autour de soi et ses radios en
**lecture seule** (`iw dev`, `nmcli -f CHAN,FREQ,SIGNAL dev wifi list --rescan no`, `nmcli radio`, `rfkill list`,
`bluetoothctl show` filtré ; jamais `sudo`, `rfkill block`, connexion, appairage ni balayage actif ; vérification sur
des quantités anonymes — canal, bande, nombre de réseaux — et la leçon explique pourquoi on ne recopie pas les noms
des voisins : aucun SSID, BSSID ni MAC enregistré ni envoyé), W3 la règle du spectre (10 MHz → 10 GHz, bandes libres /
réservées), W4 LoRa (chirp, temps d'émission Semtech au µs, la vallée et le plus petit SF, le 1 % = 36 s/h), passerelle
ou maillage, puis le maillage du Terminaworld (les machines du Port + liens radio, inondation saut par saut, nœud
coupé, autre chemin) et la tempête (couper 3 nœuds du chemin du moment, le SOS passe). W5 Meshtastic et W6 radio
logicielle **avec un adulte, jamais obligatoires** (868 MHz, 25 mW, 1 % ; `pip install` seulement expliqué ;
réception seule ; avions et capteurs fictifs, on garde la température sans l'identifiant ; racontés si le matériel
manque ; aucune marque, aucun prix, aucun lien d'achat). Vue déployée : les antennes « lit / écoute / émet / change ».
Ponts des Nombres (fréquence, puissances de 10, longueur d'onde, temps d'émission + pourcentages, division ; jamais
bloquants). Exploit « Le message qui a traversé la tempête » (`ondes.onde`) ; variantes existantes réservées :
`zapiot:orage`, `ventouzar:orage`, `cyclonaute:orage` (type Ciel, la Foudre portée par la variante « orage ») ; 14
langues ; données `donnees/ondes.json`, vecteurs communs `donnees/ondes/vecteurs.json` ; tests
`pc/outils/test_ondes.py`, `tests/jvm/Ondes.kt`, simulation `pc/outils/sim_ondes.py` →
`docs/simulations/rapport_ondes.md`, captures `pc/outils/capture_ondes.py`. Prompts d'illustrations envoyés au
propriétaire (B5, vignette, gardien, C3, E5, E6 ; à valider), repli dessiné en attendant. Reste : les illustrations,
les vraies radios (vues seulement par des doublures en test), `type rtl_test` (ON9).

**🛠 La Guilde des Bâtisseurs Libres — codée (1er novembre).**

*Fichiers.*
- 6 fiches (`donnees/guilde/outils/fiches_guilde.py`, rejeu bash).
- Leçons gu0 → gu6 sur PC (`pc/tg/guilde.py`) et sur Android (`Guilde.kt`, `GuildeDessin.kt`).
- Chapitre et dossier `guilde`, commandes `guilde …` (alias bash/zsh/fish/PowerShell).
- La Guilde s'ouvre après les niveaux 0 à 4 du tronc commun. Icône du lieu 🧰 : 🛠 ne passait pas le test de largeur des cartes.

*Règles du monde.*
- **Tout reste dans le terrain** (`terrain_terminagotchi/guilde`).
- Jamais `sudo`, rien d'installé, rien de poussé, aucun compte, aucun jeton.
- **Aucune commande du jeu ne vise `/dev/…`**. La créature réagit à `git push`, `gh pr`, `apt/dnf install` et aux écritures vers `/dev`. Le jeu ne les lance jamais.

*Les leçons.*
- **G1 le libre** : les 4 libertés (quiz mélangé), la licence MIT du petit projet, les licences de la machine (`/usr/share/licenses`, `/usr/share/doc/*/copyright`, `rpm -q` sur Fedora, sinon le catalogue de la Guilde ; 5 à trouver), libre ≠ gratuit, puis la licence de Terminagotchi lui-même (`guilde licence terminagotchi`).
- **Licences choisies le 1er novembre** : le code sous GPL-3.0-or-later (`LICENSE`, texte officiel de la FSF, copié depuis `/usr/share/common-licenses/GPL-3`, identique à la copie d'automake et à celle de pikepdf), les images, dessins, textes de l'histoire et sons sous CC BY-NC-SA 4.0 (`LICENSE-images.md`, résumé FR/EN et dossiers concernés ; les polices du site gardent l'OFL). Titulaire : « les contributeurs de Terminagotchi ». Les deux textes sont recopiés dans `guilde.json` (donc dans le `.pyz` et l'APK) ; G2 finit par `head code_du_jeu/LICENSE` sur la copie ; `tg aide` et `aide tout` (téléphone) citent les licences.
- **G2 lire du vrai code** :
  - `git clone --depth 1` du dépôt public. Sans réseau, `guilde copie` pose une copie locale des vrais `pc/tg/*.py` du jeu installé, sans rien télécharger, et l'étape ne bloque pas. Dans le rejeu CI, il n'y a pas de clone réseau.
  - `tree` (repli `find`), `grep -rl faim`, `grep -rn "def etat_de"` : l'enfant trouve lui-même le fichier où sa créature décide qu'elle a faim. La réponse est calculée dans le clone ou la copie réellement présente.
- **G3 compiler** : `bonjour.c` écrit dans le terrain, `gcc`, `file` (ELF), `od` (7f 45 4c 46), `ldd`, `make` sans Makefile. Si `gcc` manque, c'est raconté, et l'installation est expliquée « avec un adulte ».
- **G4 contribuer** :
  - Le travail se fait dans un petit dépôt git LOCAL, sans remote, avec l'identité « Apprenti de la Guilde » dans ce dépôt seulement.
  - Il contient une COPIE de 6 vraies phrases du jeu avec une faute volontaire. Les fichiers de langue du jeu ne sont pas touchés.
  - L'enfant fait : branche, correction par `sed -i`, `git diff`, `git commit -am`, `git log`. La demande de fusion est expliquée « avec un adulte », sans lien vers un compte.
  - Les crédits contributeurs (`CREDITS.txt`) sont une structure prête, avec une liste vide. Aucune donnée inventée ni collectée.
- **G5 fabriquer** : `porte_cle.scad` (OpenSCAD) aux mesures tirées de la partie, les coordonnées du trou, le volume, `openscad -o …stl` (si OpenSCAD manque, le jeu fabrique la plaque STL), `head` du STL. Aucune imprimante pilotée, aucun achat. Le porte-clé est un fichier, pas un objet porté.
- **G6 redonner vie** :
  - `lsblk` en lecture, une fausse image (64 KiB) et son `.sha256`, `sha256sum` et `sha256sum -c`.
  - Le BON disque est choisi dans un lsblk **fictif** (système, sauvegarde, clé).
  - `dd if=image of=cle_usb.img` copie de FICHIER à fichier. L'empreinte prouve la copie, puis vient le certificat.
  - L'écriture sur une vraie clé est seulement expliquée, avec un adulte, `lsblk` d'abord, et l'avertissement que `dd` efface tout. `dd` à l'envers et le disque du système sont expliqués sans danger.

*Le reste.*
- Vue déployée : l'établi (« texte → programme », « code de la pièce → pièce 3D », « l'image → la clé (ici un fichier) »).
- Ponts des Nombres, jamais bloquants : hexadécimal, coordonnées, volume. Les deux derniers sont nouveaux, dans `maths.py` et `Maths.kt`.
- Ponts des mondes : git → Bibliothèque du Temps, gcc → Forge, sha256sum → Crypte, lsblk → Salle des Rouages.
- Exploit « ta première contribution prête » (`guilde.artisan`, à `guilde fusion`). **Depuis le 1er novembre** : aucune variante réservée ni favorisée (les trois variantes sont rendues au tirage normal ; une vieille faveur de la Guilde dans une sauvegarde est ignorée), aucune créature « contributeur ». À la place, deux badges dessinés comme ceux de la salle d'entraînement et un nom coloré : « Artisan » (leçons de la Guilde + contribution d'entraînement, Bit → Méga, orange #FFAF5F) et « Contributeur » (contributions réelles acceptées, crédits `{"pseudo", "contributions"}` vides, Bit → Giga, vert #5FD787). Nouveau genre de récompense `badge` dans `recompenses.py` / `Recompenses.kt`. `guilde badges`, `tg badges` ; titres choisis par `tg badges titre`. **1er novembre, 09:52** : la couleur va sur le **pseudo** de l'enfant (jeu PC, téléphone, et site : profil avec les badges en pixels, classement, records, galerie, badge), jamais sur le nom de la créature ; le site recalcule l'Artisan (leçons synchronisées) et ne prend le Contributeur QUE dans les crédits du dépôt (`site/src/guilde_donnees.js`, redéployer quand ils changent). Voir § 7.12 de `programme.md`. Licences : la **mascotte du site** est exclue de la CC BY-NC-SA (tous droits réservés, les contributeurs de Terminagotchi ; `LICENSE-images.md`, README, G1) ; elle n'apparaît jamais dans le jeu.
- 14 langues. Données `donnees/guilde.json`, vecteurs communs `donnees/guilde/vecteurs.json`.
- Tests : `pc/outils/test_guilde.py` (50), `tests/jvm/Guilde.kt` (28). Simulation `pc/outils/sim_guilde.py` → `docs/simulations/rapport_guilde.md`. Captures `pc/outils/capture_guilde.py`. Le rejeu CI installe gcc, make, file et openscad.
- Prompts d'illustrations envoyés au propriétaire (B13, vignette, C1, C3, C4, E16 ; à valider). Un repli dessiné est affiché en attendant.

*Reste.*
- Les illustrations.
- Un vrai `git clone` vu réussir (la machine de test n'a pas de réseau).
- `satiete.py` absent de la branche main publique (GU10).
- ~~Pas de fichier LICENSE pour Terminagotchi lui-même~~ : réglé le 1er novembre (GPL-3.0-or-later + CC BY-NC-SA 4.0).

**🔭 L'Observatoire de l'IA — codé (1er novembre).**

*Fichiers.*
- 9 fiches (`donnees/observatoire/outils/fiches_observatoire.py`, rejeu bash), données `donnees/observatoire.json`,
  textes `donnees/observatoire/outils/textes_observatoire_*.py` (14 langues), vecteurs communs `donnees/observatoire/vecteurs.json`.
- Leçons ob0 → ob9 sur PC (`pc/tg/observatoire.py`) et sur Android (`Observatoire.kt`, `ObservatoireDessin.kt`).
- Chapitre et dossier `observatoire`, commandes `observatoire`, `assistant`, `agent`, `devine-type`, `devine-mot`
  (alias bash/zsh/fish/PowerShell). L'Observatoire s'ouvre après les niveaux 0 à 6 du tronc commun ; annonce du monde
  à son tour (une à la fois). Icône 🔭, chapitre n° 17, famille Célestes.

*Règles du monde.*
- **Aucune vraie IA** : l'assistant, le devineur de type, le devineur de mots et les agents sont de petits programmes
  du jeu, déterministes, lisibles. Aucun appel réseau, aucun compte, aucune clé d'API. Le jeu le dit à chaque palier
  (« les vraies IA sont bien plus grandes, mais le principe est juste »). Aucune marque d'IA nommée.
- **Tout reste dans le terrain** (`terrain_terminagotchi/observatoire`). Les agents fictifs n'écrivent que là.
- **Le danger n'est jamais lancé** : `rm -rf …` et `sudo chmod -R 777 …` proposés par les agents sont du TEXTE, avec
  un chemin « … » qui ne vise rien ; même accepté, le jeu ne le lance pas et explique pourquoi on refuse.
  `sudo`, `rm -rf ~`, `chmod -R 777` tapés par l'enfant reçoivent une phrase claire.
- Rien n'est envoyé au site ; le devineur de mots n'apprend que sur les phrases de l'histoire du jeu.

*Les leçons.*
- **O1 mission** : consigne floue (l'assistant dit ce qui manque : quoi, quel fichier, quoi chercher), consigne claire,
  `assistant mission.txt > rapport.txt` (ce que l'assistant DIT va sur la sortie d'erreur, ce qu'il PRODUIT sur la sortie).
- **O2 vérifier** : l'assistant trie mais oublie une ligne (exprès) ; `wc -l`, `sort … | diff - tri.txt`, `sh test.sh`
  (ÉCHEC), l'enfant nomme l'oubliée, puis `sort > tri.txt && sh test.sh` (RÉUSSI).
- **O3 secrets** : une clé EXEMPLE dans un fichier « partagé avec la classe », `grep -n`, `sed -i '/…/d'`, `.env`,
  `chmod 600`, `.gitignore`, `export`, `observatoire cle` (n'affiche que le début). La clé ne va jamais dans la sauvegarde.
- **O4 superviser** : Robot-Rangeur et son journal, `git diff`, refuser la proposition dangereuse, valider ; un agent qui tourne
  en rond, arrêté avec Ctrl+C (limite de 20 s en secours).
- **O5 apprendre** : 20 vraies créatures du bestiaire étiquetées Feu / pas Feu, `uniq -c`, `devine-type apprends`,
  `cerveau.txt` (les comptes), la 21e (Cauchemarre, Démon de la brume) le trompe ; l'enfant dit si c'est la famille.
- **O6 biais** : `volcan.txt` (12 Feu, que des lieux chauds) → 1 sur 5 sur d'autres lieux ; quiz ; réentraîné sur
  les exemples variés → 5 sur 5, avec la nuance « 5 sur 5 ici ≠ parfait partout ».
- **O7 devineur de mots** : `tr | sort | uniq -c` sur les vraies phrases de l'histoire (dans la langue du joueur ;
  chinois et japonais : un caractère = un mot), paires de mots avec `tail` + `paste`, `devine-mot suite` (« 3 chances
  sur 4 »), `devine-mot phrase` (qui sonne juste mais peut être faux), quiz v/f.
- **O8 esprit critique** : 5 réponses de l'assistant fictif, dont 2 fausses tirées pour la partie ; l'enfant vérifie
  avec `wc -l`, `echo $((17 % 5))`, `tr … | uniq -c`, `explique ls`, `explique rm`. Puis : ce qu'on confie / ce qu'on
  garde (adresse, mot de passe, photo d'un ami, nom et date de naissance) ; 5 nuances (erreurs sûres d'elles,
  deepfakes, droits d'auteur, énergie des centres de données, « si une IA le dit »), sans peur ni publicité.
- **O9 chef d'équipe** : découper la tâche, choisir la consigne (claire / floue / dangereuse avec sudo), l'agent
  Copieur s'emballe (7 copies par commande tapée, 63 au plus) → `agent stop` (fichier STOP), `ls copies | wc -l`,
  refuser la proposition dangereuse, `diff` du travail du Trieur, `sh tests.sh` (le Compteur s'est trompé : doublons),
  correction `wc -l < liste.txt > compte.txt`, tests verts, `agent bilan`.
- Les lettres des quiz restent v/f et c/g dans toutes les langues (expliquées à l'écran), comme l/p à la Guilde.

*Le reste.*
- Vue déployée : la lunette (« une consigne → un rapport », « des exemples → une devinette », « un texte → la suite
  probable », « deux textes → les différences », « des lignes → les fréquences », « un travail → RÉUSSI ou ÉCHEC »).
- Ponts des Nombres, jamais bloquants : effectifs (nouveau), fréquences (nouveau), probabilités (rempli), dans
  `maths.py` et `Maths.kt` (mêmes tirages, vecteurs communs).
- Ponts des mondes : sort, uniq, grep → Salle des Données ; export → Poste de Contrôle ; git → Bibliothèque du Temps ;
  chmod → Citadelle.
- Exploit « toutes les réponses fausses démasquées » (`observatoire.fausses`), objet loupe de détective (posé, jamais
  porté), titre « Chef des Robots ». Variantes EXISTANTES favorisées (Ciel / Glace) : `seraphibou:cosmique`,
  `zyeuton:brume`, `mutaloupe:cristal`. Comme elles n'apparaissent plus avant l'exploit, le test d'attirance donne
  Célestes 8,0 → 28,0 % au lieu de 28,7 % (`tests/jvm/RetoursEnfants.kt` mis à jour, identique PC / Android).
- Tests : `pc/outils/test_observatoire.py` (67, dont la consigne comprise et le mot d'exemple du devineur dans chacune
  des 14 langues), `tests/jvm/Observatoire.kt` (27). Simulation `pc/outils/sim_observatoire.py` →
  `docs/simulations/rapport_observatoire.md`. Captures `pc/outils/capture_observatoire.py`.
- Prompts d'illustrations envoyés au propriétaire (B11, vignette, C1, C3, E12, E17 nouveau ; à valider). Un repli
  dessiné est affiché en attendant (coupole en caractères sur PC, `ObservatoireDessin` sur le téléphone).

*Reste.*
- Les illustrations.
- Chinois et japonais : le devineur de mots compte des caractères, pas des mots (ces langues n'ont pas d'espaces). Depuis le 1er novembre, `observatoire mots` le dit à l'enfant dans ces deux langues seulement (`ob.mots.caracteres`, détecté sur le texte : `sans_espaces()` / `sansEspaces()`).
  Ce n'est pas dit à l'écran ; à valider (question au propriétaire).
- Les traductions des 13 autres langues sont faites par Claude : une relecture par des locuteurs serait bienvenue.

**📊 La Salle des Données — codée (1er novembre).**

*Fichiers.*
- 6 fiches et 4 fiches de maths (`donnees/donnees/outils/fiches_donnees.py`, rejeu bash), données `donnees/donnees.json`,
  textes `donnees/donnees/outils/textes_donnees_*.py` (14 langues), vecteurs communs `donnees/donnees/vecteurs.json`.
- Leçons dn0 → dn6 sur PC (`pc/tg/donnees.py`) et sur Android (`Donnees.kt`, `DonneesAwk.kt` le petit awk,
  `DonneesSql.kt` le petit sqlite3 sur le SQLite du téléphone, `DonneesDessin.kt`).
- Chapitre et dossier `donnees`, commandes `tg collection --csv` (téléphone : `collection --csv`) et `donnees` (alias
  bash/zsh/fish/PowerShell). La Salle s'ouvre après les niveaux 0 à 4 du tronc commun ; annonce du monde à son tour.
  Icône 📊, chapitre n° 18, famille Abyssaux, objet boulier, titre « Savant des Données ».

*Règles du monde.*
- **Les données de l'enfant** : sa collection, exportée en CSV dans le terrain. Aucune donnée personnelle (ni pseudo,
  ni identifiant ; seulement l'espèce, le type, la famille, les stats, la rareté, shiny, la variante, le jour de capture).
  Rien n'est envoyé au site.
- **Le jeu recalcule chaque réponse sur le même fichier**, au moment de vérifier. Le rejeu bash (CI) compare la sortie
  de bash à ce que le jeu calcule (`egal_jeu`) : il reste déterministe même si la collection change.
- **Plus de bestioles d'exemple (décision du 1er novembre)** : le tableau est seulement SA collection (12 colonnes, la
  colonne `exemple` a disparu). Chaque exercice qui en a besoin annonce « Il te faut au moins X créatures dans ta
  collection » et où aller les rencontrer (forêt, volcan, glacier, ruines, corail, marais… puis réexporter) : D1 en
  demande 3 (`tg collection --csv`), D4 5 (`donnees calcul`), D-SQL 5 (`donnees base`) — `donnees.json` → `minimum`.
  L'étape attend sans bloquer le reste du jeu, comme les autres étapes qui dépendent du joueur. Le rejeu en CI, les
  simulations et les tests jouent avec une collection de TEST fixe (`collection_test`, 10 captures, jamais en partie).
- **L'exploit « une statistique juste » ne se gagne que sur SA vraie collection** : le tableau doit être exactement
  celui que `tg collection --csv` exporte de la partie (`sa_collection` / `saCollection`) ; il est donné par
  `donnees moyenne` (et non plus par l'étape), un tableau retouché à la main ne compte pas.
- **La base est lue en lecture seule** (`DELETE`, `DROP`… refusés). Si `sqlite3` n'est pas installé sur le PC,
  `tg donnees sqlite3 …` fait la même chose avec le moteur SQLite de Python (le jeu le propose).

*Les leçons.*
- **D1 compter et trier** : `tg collection --csv > collection.csv`, `head`, `wc -l` (moins la ligne des titres),
  `donnees trier` (especes.txt, forces.txt), `sort | uniq -c | sort -rn | head -3`, le podium `sort -nr | head -3 > top3.txt`
  (comme l'épreuve « Rétro » du dressage).
- **D2 les colonnes** : `head -1 | tr ',' '\n'`, `cut -d, -f2 | tail -n +2 | sort | uniq -c`, les shiny avec
  `cut -d, -f10 | grep -c 1`, `paste -d:`.
- **D3 le copiste** : un nom mal écrit partout dans le carnet du soigneur (deux fois sur une ligne) ; `sed 's///'`,
  `s///g`, `diff`, `sed -n '2,4p'`, `sed -i`.
- **D4 la calculatrice** : `awk -F,` (colonnes, somme, moyenne : l'exploit), `sort -n > attaques.txt`, médiane, étendue.
- **D5 les machines en chaîne** : `grep -E 'eau|glace'`, `sort -u | xargs echo`, `sed 's|.*|enclos/&.txt|' | xargs touch` (un fichier par espèce),
  `sort -t, -k4 -nr | head -3 | tee rapport.txt`, la moyenne ajoutée avec `>>`, `donnees bilan` (certificat).
- **D-SQL la base de données** : `donnees base` (collection.db : tables creatures et especes), `.tables`, `.schema`,
  `SELECT … ORDER BY … LIMIT 3`, `WHERE`, `COUNT(*) … GROUP BY`, `JOIN`, `AVG`. Chaque requête montre l'autre chemin
  (le même podium que `sort | head`, la même moyenne qu'awk).
- `cut` sans `-d,` et `awk` sans `-F,` sont refusés avec une explication (ils donneraient un résultat faux).

*Le reste.*
- Vue déployée : le laboratoire (tamis grep, ciseaux cut, moulin sort, calculatrice awk, copiste sed, aiguillage tee,
  distributeur xargs, bibliothécaire sqlite3…), « des lignes → des lignes rangées », etc.
- Ponts des Nombres, jamais bloquants : moyenne, médiane, étendue, pourcentages (nouveaux), comptage, effectifs,
  fréquences ; dans `maths.py` et `Maths.kt` (mêmes tirages, vecteurs communs).
- Contenu existant réutilisé sans le changer : épreuves « Rétro » (top3, record), « Données » (différentes),
  « IA » (fréquent), quête q21.
- Exploit « une statistique juste sur ta collection » (`donnees.statistique`, la moyenne). Variantes EXISTANTES
  favorisées (Eau / Glace) : `nautiloque:corail`, `krillou:aurore`, `ondulame:glace`.
- Android : le petit awk est comparé aux sorties du VRAI awk (vecteurs) ; le petit sqlite3 à la mise en forme du vrai
  outil (`%!.15g`, `.tables`), vérifiée en CI où `sqlite3` et `gawk` sont installés. Les autres outils (`cut`, `sort`,
  `uniq`, `sed`, `xargs`, `tee`…) sont ceux du téléphone : `pc/outils/test_donnees_outils.py` compare chaque ligne de
  la Salle entre GNU, toybox (compilé en CI) et busybox. Il a trouvé que toybox n'a ni `cat -n` ni `xargs -I` : le jeu
  dit `nl` pour numéroter les lignes et fabrique les noms des fichiers avec `sed` avant `xargs touch` (PC et téléphone).
  `.tables` est écrit comme le vrai `sqlite3` (chaque nom complété, le dernier aussi), vu par le rejeu en CI.
- Le terminal partagé (`pc/tg/coquille.py` : `tg mini` et les simulations) ne plante plus quand une commande arrête le
  shell (une erreur de syntaxe comme `COUNT(*)` sans guillemets) : il répond, puis repart dans le même dossier.
- `sim_machines.py` (Hugo) a échoué une fois en CI puis est passé à la relance, sans que la cause soit retrouvée ici (pas
  de hasard sans graine ni d'heure trouvés ; 65 essais locaux verts) : la simulation affiche maintenant où il reste
  bloqué, pour la prochaine fois.
- Tests : `pc/outils/test_donnees.py` (67), `tests/jvm/Donnees.kt` (29). Simulation `pc/outils/sim_donnees.py` →
  `docs/simulations/rapport_donnees.md`. Captures `pc/outils/capture_donnees.py`. Rejeu d'un seul monde en local :
  `TG_REJEU_MONDE=donnees`.
- Le test qui échouait parfois (`test_retours_enfants.py`, « niveau max des épreuves ») tirait les épreuves au sort
  sans graine : il est maintenant déterministe (graine fixe, 40 tirages), et `tests/jvm/RetoursEnfants.kt` aussi
  (`Dressage.hasard`). Ce qu'il vérifie n'a pas changé.
- Prompts d'illustrations envoyés au propriétaire (B7, vignette, C1, C3, E18 et E19 nouveaux ; à valider). Un repli
  dessiné est affiché en attendant (laboratoire en caractères sur PC, `DonneesDessin` sur le téléphone).

*Reste.*
- Les illustrations.
- ~~Avec une collection minuscule, l'exploit se gagne sur un tableau en partie d'exemple~~ : réglé le 1er novembre (plus de bestioles d'exemple ; l'exploit seulement sur sa vraie collection).
- Le petit sqlite3 sur un vrai téléphone (le moteur d'Android n'est pas lancé dans les tests JVM).
- Les traductions des 13 autres langues sont faites par Claude : une relecture par des locuteurs serait bienvenue.

**🔨 La Forge — codée (1er novembre).**

*Fichiers.*
- 7 fiches et 2 fiches de maths (`donnees/forge/outils/fiches_forge.py`, rejeu bash), données `donnees/forge.json`
  (la photo d'exemple aux métadonnées inventées y est en base64), textes `donnees/forge/outils/textes_forge_*.py`
  (14 langues), vecteurs communs `donnees/forge/vecteurs.json`.
- Leçons fo0 → fo7 sur PC (`pc/tg/forge.py`) et sur Android (`Forge.kt`, `ForgeDessin.kt`, le site servi par le phare
  de l'appli dans `Port.kt`). Chapitre et dossier `forge`, commande `forge` (alias bash/zsh/fish/PowerShell). S'ouvre
  après les niveaux 0 à 4 du tronc commun ; annonce du monde à son tour. Icône 🔨, chapitre n° 19, famille Constructs,
  objet « petit marteau de forgeron », titre « Maître de la Forge ».
- « L'atelier des Constructs » s'appelle maintenant « la petite forge des Constructs » (§ 2.19) ; « Atelier » reste
  pour les robots.

*Règles du monde.*
- Tout reste dans le terrain : les scripts de l'enfant, son mini-jeu, son site, les images et les sons.
- **Le site** : `python3 -m http.server … --bind 127.0.0.1 --directory site &`, sur un port libre > 1024 (8642, ou le
  suivant si pris) ; l'étape vérifie que la page est servie ET que rien n'écoute sur 0.0.0.0/:: ; un serveur lancé sans
  `--bind` est signalé tout de suite ; arrêt par `fg` puis Ctrl+C. « Publier » est seulement expliqué (avec un adulte),
  aucun compte, aucun hébergeur cité.
- **Le multimédia** : seulement les fichiers du jeu (4 images de la créature, une fanfare fabriquée, la photo d'exemple).
  `exiftool` (ou `forge exif`) sur la photo d'exemple seulement ; `forge exif` / `forge nettoie` refusent tout fichier
  hors du terrain. On explique comment retirer les métadonnées.
- Un outil absent (magick, sox, ffmpeg, exiftool, python3, curl, tree) : l'étape est cachée ou remplacée (repli), rien
  ne bloque. Variantes rares (existantes) : `fondelin:lave`, `boulonnet:neon`, `tisonnier:mecanique` ; exploits
  « un programme qui marche du premier coup » (première recette complète lancée) et « un palier sans indice ».

*Les leçons.* F0 la porte (enclume.txt) · F1 les recettes (`echo … > / >>`, `#!/bin/sh`, `sh`, `chmod +x`, `./`) ·
F2 les boîtes (`nom=Pixel`, `$1`, `$#`, `read`) · F3 aiguillage et manèges (`$?`, `if`, `for`, `seq`, les 10 cabanes,
`while`, les tours) · F4 Python (`python3 -c`, une boucle, `serpent.py`, le Traceback, `sys.argv`) · F5 le mini-jeu
(devinette.sh, un robot qui joue avec `seq | sh`, le donjon, `forge carte "…"` : le jeu devient un lieu 🎮 sur la carte) ·
F6 le site (HTML, CSS, le serveur, `curl`, `fg` + Ctrl+C, publier) · F7 l'atelier multimédia (GIF animé, `sox`,
`ffmpeg`, les métadonnées démasquées puis effacées, le certificat). Ponts des Nombres : boucles (compter les tours) et
priorités des opérations, aussi dans `Maths.kt`.

*Écarts assumés.*
- Téléphone (une ligne = un nouveau shell, pas de clavier pour `read`, pas de Python ni d'outils multimédia) : boîte et
  ouverture sur la même ligne, `echo Léa | sh question.sh`, serpent raconté puis `doom`, `forge serveur` / `forge
  serveur stop` (le site servi par l'appli sur 127.0.0.1), la photo lue et nettoyée par l'appli.
- En CI, « fg puis Ctrl+C » est rejoué par `kill %1`.
- `Ls fantome; echo $?` passe l'étape « $? » (127 n'est pas 0) : sans conséquence.

*Tests.* `pc/outils/test_forge.py` (73), `tests/jvm/Forge.kt` (30), `pc/outils/test_forge_outils.py` (GNU, toybox+mksh,
busybox), simulation `pc/outils/sim_forge.py` → `docs/simulations/rapport_forge.md`, captures `pc/outils/capture_forge.py`,
rejeu d'un seul monde : `TG_REJEU_MONDE=forge`.

*Reste.* Les illustrations (prompts B8, vignettes, C1, C3, E20 à E24 envoyés) ; une relecture des 13 traductions par
des locuteurs.
**⏳ La Bibliothèque du Temps — codée (1er novembre).**

*Fichiers.*
- 5 fiches (`donnees/temps/outils/fiches_temps.py`, rejeu bash : git_album, git_histoire, git_branches, git_partage,
  git_empreintes), données `donnees/temps.json`, textes `donnees/temps/outils/textes_temps_*.py` (14 langues),
  vecteurs communs `donnees/temps/vecteurs.json` (`pc/outils/vecteurs_temps.py` : la spécification, plus des scénarios
  joués avec le VRAI git 2.43.0, version notée dans le fichier).
- Leçons tp0 → tp5 sur PC (`pc/tg/temps.py`) et sur Android (`Temps.kt`, `PetitGit.kt` le petit git de l'appli,
  `TempsDessin.kt`).
- Chapitre et dossier `temps`, commande `temps` (alias bash/zsh/fish/PowerShell). La Bibliothèque s'ouvre après les
  niveaux 0 à 4 du tronc commun ; annonce du monde à son tour. Icône ⏳, chapitre n° 21, famille Constructs (git les
  attire), objet pendule, titre « Archiviste du Temps ».

*Règles du monde.*
- **Tous les dépôts git sont créés DANS le terrain** (`terrain_terminagotchi/temps` : album, grimoire, copie_de_mon_ami).
  Aucun dépôt distant réel, aucun `push`, aucun compte. `git push` est seulement raconté (`temps bateau`).
- **Jamais `git config --global`** : le nom et l'adresse sont des EXEMPLES (`…@temps.invalid`), réglés dans le dépôt.
  Le jeu ne touche jamais `~/.gitconfig` (vérifié par les simulations : le fichier est identique à la fin). Si
  l'enfant tape `--global` lui-même, la garde le prévient et dit à l'adulte comment vérifier (`git config --global --list`).
- Le grimoire de la Bibliothécaire et la page de l'ami sont posés par le jeu avec le vrai git, des dates fixes et
  `core.hooksPath=/dev/null` : mêmes empreintes sur toutes les machines. `temps grimoire neuf` range l'ancien
  (`grimoire.ancienN`) au lieu de l'effacer ; un dossier de l'enfant qui n'est pas vide n'est jamais écrasé.
- **Si git manque** (PC sans git, Windows sans Git for Windows) : la Bibliothèque raconte ce que git ferait et dit
  comment l'installer avec un adulte (Fedora, Ubuntu, Git for Windows). Les étapes qui demandent git sont cachées ;
  rien n'est bloqué.
- **Android** : l'appli n'avait pas de git. `PetitGit.kt` est un petit git honnête, seulement dans le terrain :
  init, config (sans `--global`), status, add, commit, log (`--oneline`, `--graph`, `-S`, `-p`, `-n`, `--all`), show,
  diff, restore, checkout, switch, branch, merge (avance rapide, fusion à 3, conflits avec bornes), clone, pull
  (local), remote -v, hash-object, cat-file, rev-parse, rev-list. Ses objets ont les MÊMES empreintes que le vrai git
  et ses sorties sont comparées octet par octet au vrai git (vecteurs). Ce qu'il ne sait pas faire est dit (« git help »).

*Les leçons.*
- **T0** l'entrée : le registre (les règles ci-dessus).
- **T1 l'album** : `git init -b main album`, `git config user.name/user.email` (dans l'album), `git status`, `git add`,
  `git commit -m`. Réutilise sans les changer git0-2 et la quête Q37.
- **T2 remonter le temps** : le grimoire (6 photos) ; `git log --oneline`, gribouillis + `git diff`, `git restore`,
  `git log --oneline -S secret`, `git show`, `temps perdu EMPREINTE`, `git checkout EMPREINTE~1 -- grimoire.txt`,
  `git commit -am` : **l'exploit « retrouver une version perdue »** (`temps.version`).
- **T3 les mondes parallèles** : `git switch -c reve`, deux « Jour 2 », `git merge reve` → CONFLICT, `temps conflit`
  explique les bornes, `sed -i '/^[<=>]\{7\}/d'` (ou nano), le commit de fusion, `git log --oneline --graph`.
- **T4 partager** : `git clone . ../copie_de_mon_ami`, la page de l'ami (`temps ami`), `git pull ../copie_de_mon_ami`,
  `.gitignore`, `git remote -v`, `temps bateau` (le push raconté).
- **T5 les empreintes** : `git hash-object` = `printf 'blob 6\0temps\n' | sha1sum` (pont Crypte K3, pont des Nombres
  « hexadécimal »), une majuscule change tout, `git cat-file -p HEAD` (la chaîne des photos), `find -newer` (pont
  Citadelle), `temps bilan` (certificat).

*Le reste.*
- Écart assumé avec § 2.13 : `git config` sans `--global` (consigne de sécurité du monde) ; `git push` raconté au lieu
  d'un dépôt local `--bare` (aucun envoi, même local) ; un palier T5 « empreintes » ajouté (ponts K3 et Citadelle).
- Les indices reconnaissent les fautes typiques : `git init` sans nom, `--global`, la photo où la formule est APPARUE,
  `git checkout EMPREINTE` (HEAD détachée), `master` au lieu de `main`, `sed` sans `-i`, bornes restantes, `git pull`
  sans dire d'où, `git commit` sans rien à photographier, dossier `copie_de_mon_ami` déjà pris.
- Vue déployée : la pellicule (un dossier → un album, un fichier → devant l'objectif, deux chemins → un chemin…). Quand
  l'établi de la Guilde reconnaît déjà la commande (`git commit`, `git diff`…), c'est lui qui est montré.
- Exploit `temps.version` : variantes EXISTANTES favorisées (Roche / Ombre) `momiaou:soleil`, `galetard:ruines`,
  `follanterne:brume`.
- Tests : `pc/outils/test_temps.py` (47), `tests/jvm/Temps.kt` (36), vecteurs `--verifier`. Simulation
  `pc/outils/sim_temps.py` → `docs/simulations/rapport_temps.md` (3/3 au bout). Captures `pc/outils/capture_temps.py`.
  Rejeu d'un seul monde en local : `TG_REJEU_MONDE=temps`. En CI, git est le vrai ; `printf … \0` et `sed \{7\}`
  sont aussi rejoués avec toybox (les outils du téléphone).
- Prompts d'illustrations envoyés au propriétaire (B6, vignette, grimoire, pendule ; à valider). Un repli dessiné est
  affiché en attendant (façade en caractères sur PC, `TempsDessin.bibliotheque` sur le téléphone).

*Reste.*
- Les illustrations.
- Le petit git sur un vrai téléphone (seulement en JVM ici) ; toybox `printf`/`sed` vus en CI, pas sur un appareil.
- L'ancienne leçon git1.2 conseille encore `git config --global` dans une astuce (contenu existant, non modifié) : à
  décider par le propriétaire.
- Les traductions des 13 autres langues sont faites par Claude : une relecture par des locuteurs serait bienvenue.

**🤖 L'Atelier — codé (1er novembre).**

*Fichiers.*
- 5 fiches et le Pont des Nombres « logique » (ET, OU, NON : la fiche manquait ; exercice dans `maths.py` et `Maths.kt`)
  (`donnees/atelier/outils/fiches_atelier.py`, rejeu bash), données `donnees/atelier.json` (arènes vérifiées par le
  générateur), textes `donnees/atelier/outils/textes_atelier_*.py` (14 langues), vecteurs `donnees/atelier/vecteurs.json`.
- Leçons at0 → at7 sur PC (`pc/tg/atelier.py`) et sur Android (`Atelier.kt`, `AtelierDessin.kt`).
- L'ancienne aile « atelier » des Constructs est devenue « la petite forge » (§ 2.19) ; le chapitre et le dossier de ce
  monde s'appellent **`robots`** (`~/terrain_terminagotchi/robots`), le monde garde son nom (« L'Atelier des robots »). Commande
  `atelier` (alias bash/zsh/fish/PowerShell, `tg atelier`). S'ouvre après les niveaux 0 à 4 du tronc commun ; annonce à
  son tour. Icône 🤖, chapitre n° 20, famille Constructs, objet robot miniature, titre « Roboticien ».

*Règles du monde.*
- **Le robot est simulé** : `robots/robot/led`, `moteur`, `capteur_distance` (et `journal.txt`) sont des fichiers que
  l'enfant lit et écrit avec `cat` et `echo … >` (« tout est fichier », comme `/sys/class/leds`). Le robot vit sur une
  grille avec des obstacles ; `atelier pas` est la physique du monde (lire le moteur, avancer ou tourner d'un cran,
  écrire le capteur en cm — 10 cm par case — et une ligne du journal).
- **Le cerveau est un vrai script de l'enfant** (`cerveau.sh`), lancé par SA vraie boucle dans SON shell :
  `for i in $(seq 20); do sh cerveau.sh; atelier pas; done` (comme `loop()` sur Arduino). Sur PC, le jeu ne lance
  jamais ce script. Sur le téléphone (dont le shell ne connaît pas `atelier`), l'appli déroule cette même ligne (au plus
  40 tours) et lance `cerveau.sh` avec le vrai `sh` du téléphone, dans le terrain, 5 s au plus par tour.
- **Aucun matériel** : ni `/dev/tty*`, ni port série, ni GPIO, ni flashage. Le vrai Raspberry Pi, `ssh pi@…`,
  `sudo apt` (avec un adulte), `gpioset`/`pinctrl`, `crontab @reboot`, `systemctl --user`, `arduino-cli
  compile/upload`, `screen /dev/ttyUSB0 115200`, `esptool.py` : seulement racontés, facultatifs, « avec un adulte »,
  sans marque mise en avant ni lien d'achat. Le jeu propose seulement des commandes qui LISENT (`ls /sys/class/leds`,
  `command -v gpioset pinctrl`, `crontab -l`, `command -v arduino-cli esptool.py`), cachées si l'outil manque. Une commande
  qui toucherait du vrai matériel (ou `sudo`) : la créature rappelle la règle (une fois), l'indice le dit.

*Les leçons.*
- **at0** la porte ; **at1 (R1) la LED** : `ls robot`, `cat robot/led`, `echo 1 > robot/led`, `atelier robot`, `echo 0`,
  `cat robot/capteur_distance` ; **at2** le moteur, la grille et les coordonnées (`atelier grille`, `echo avance >
  robot/moteur`, `atelier pas`, `atelier ou X Y`, `echo droite`, `atelier cases N` : cm → cases) ;
- **at3 ET / OU / NON** : `[ 5 -lt 10 ] && echo vrai || echo faux`, `d=$(cat robot/capteur_distance); if [ "$d" -lt 10 ];
  then …; else …; fi`, la table de vérité de la porte de la partie (`atelier verite`), trois situations (`atelier choix`) ;
- **at4 (R2) la boucle** : `for i in 1 2 3; do …; sleep 1; done`, `while true …` puis Ctrl+C (PC), le cerveau d'exemple
  (il avance toujours), `cp`, `atelier essai`, la boucle de 10 tours (💥 il se cogne), `nano cerveau.sh` (n'importe quel
  éditeur ; `atelier aide-cerveau` montre les lignes ; téléphone : `edite cerveau.sh`) ;
- **at5 le défi** (exploit) : `atelier defi` (une arène par partie), 20 tours, 0 choc, au moins 12 cases explorées.
  Un cerveau qui fonce se cogne, un cerveau qui s'arrête devant l'obstacle n'explore pas assez : il faut tourner ;
- **at6 (R3 + R4) le vrai Raspberry Pi** (raconté) : `atelier pi`, `ls /sys/class/leds`, `command -v gpioset pinctrl`,
  `atelier gpio` (la rangée de broches), `atelier autonome` (cron, systemd, le journal), `tail -5 robot/journal.txt`,
  `crontab -l` ;
- **at7 l'embarqué et le temps réel** (§ 7.13) : microcontrôleur ou ordinateur (`atelier embarque`), `time sh
  cerveau.sh`, le réflexe (`atelier reflexe` : cm/s × ms ÷ 1000), Arduino / ESP32 depuis le terminal (raconté),
  `command -v arduino-cli esptool.py`, le téléphone robot de poche. **Android** : `lampe on` (une vraie LED), `vibre 300`
  (un vrai moteur), `batterie` (un vrai capteur) — les commandes du jardin du téléphone, réutilisées. Les autres
  capteurs (accéléromètre, lumière, proximité) sont racontés : l'appli ne les utilise pas.
- L'œuf physique (ESP32) est seulement évoqué comme projet futur (`atelier arduino`), rien n'est construit.

*Le reste.*
- Vue déployée : ce que la commande fait au robot (la LED reçoit un ordre, le capteur est lu, le cerveau décide, les
  roues bougent), PC (`deploie.robots`) et téléphone (`Deploie.robots`, `AtelierDessin.robot`).
- Ponts des Nombres, jamais bloquants : coordonnées, logique (nouveau), multiplication.
- Exploit « un robot qui évite tous les obstacles » (`atelier.robot`). Variantes EXISTANTES favorisées (Machine /
  Plante, libres) : `horlogrif:mecanique`, `groinfer:rouille`, `lampignon:forêt`.
- PowerShell : `echo 1 > robot/led` écrit en UTF-16 sous PowerShell 5 : le jeu lit aussi l'UTF-16.
- **Windows — codé (1er novembre, demande du propriétaire) ; remplacé le 2 novembre par le terminal du jeu (voir plus
  bas) : ces étapes PowerShell ne sont plus proposées.** Les mêmes étapes en PowerShell 5.1 et 7
  (`atelier.lecons_pour(True)`) : `Get-Content robot\led`, `if (5 -lt 10) { "vrai" } else { "faux" }`,
  `1..3 | ForEach-Object { … }`, `while ($true) { … }`, `cerveau.ps1` (`Get-Content robot\capteur_distance`,
  `if (…) { … } else { … }`, `Set-Content robot\moteur …`, écrit en UTF-8 avec BOM), la boucle
  `1..20 | ForEach-Object { .\cerveau.ps1; atelier pas }`, `Measure-Command { .\cerveau.ps1 }`,
  `Get-Content robot\journal.txt -Tail 5`. Même défi, même exploit, vérifiés par le carnet. Seules les étapes propres à
  Linux restent cachées (`/sys/class/leds`, `command -v`, `crontab`). Politique d'exécution : le terminal du jeu a déjà
  `-ExecutionPolicy Bypass` pour sa fenêtre ; ailleurs, si Windows refuse le script, le jeu le voit (le moteur reste sur
  `stop` à chaque pas) et explique le message, avec `powershell -ExecutionPolicy Bypass -File .\cerveau.ps1` (pour une
  fois) ; jamais `Set-ExecutionPolicy`. Un joueur Windows qui avait fini la leçon sans le défi reçoit l'exploit en
  réussissant le défi (rattrapage). Textes en 14 langues (les textes tirés de ceux de bash sont fabriqués par
  `textes_atelier.py`, DERIVES). Tests : `test_windows.py` (partie imitée, script refusé, rattrapage), `test_atelier.py`
  § 8, et en CI les VRAIS Windows PowerShell 5.1 et PowerShell 7 jouent le défi (`pc/outils/defi_powershell.py`,
  `.github/workflows/windows.yml`, job `atelier-powershell`). Fiche enseignant (chapitre 20) et PDF à jour.
- Tests : `pc/outils/test_atelier.py` (traversée réelle, 3 défis, dash / mksh / busybox / toybox comparés à bash),
  `tests/jvm/Atelier.kt` (la boucle déroulée par l'appli avec le vrai `sh`). Simulation `pc/outils/sim_atelier.py` →
  `docs/simulations/rapport_atelier.md`. Captures `pc/outils/capture_atelier.py`. Rejeu d'un seul monde :
  `TG_REJEU_MONDE=robots`.
- Prompts d'illustrations envoyés au propriétaire (B10, vignette, E-at1 à E-at4). Repli dessiné en attendant (l'établi
  en caractères).

*Reste.*
- Les illustrations ; une relecture des 13 traductions par des locuteurs.
- La boucle déroulée par l'appli et `edite cerveau.sh` sur un vrai téléphone (APK d'essai).

**⛰ Le Sommet (Expert++) — codé (1er novembre).**

*Fichiers.*
- 7 fiches (`donnees/sommet/outils/fiches_sommet.py`, rejeu bash), données `donnees/sommet.json`, textes
  `donnees/sommet/outils/textes_sommet_*.py` (14 langues), vecteurs communs `donnees/sommet/vecteurs.json`.
- Leçons som0 → som7 sur PC (`pc/tg/sommet.py`) et sur Android (`Sommet.kt`, `SommetDessin.kt`). Chapitre et dossier
  `sommet`, commande `sommet` (alias bash/zsh/fish/PowerShell). Icône 🗻, chapitre n° 23, objet piolet, titre
  « Maître du Sommet ».

*Règles du monde.*
- **L'ouverture** : quand **trois mondes** du Carrefour ont leur **palier 3** (§ 2.18). Rien n'est écrit en dur : le
  jeu parcourt les mondes de `programme.json` (ceux qui ont des paliers et un chapitre) ; la Forge, le Contrôle, le
  Temps, l'Atelier compteront dès qu'ils existeront. Annonce du monde au moment où le 3e palier 3 est atteint.
- **Les scripts fragiles et cassés sont écrits par le jeu dans le terrain** (`fragile.sh`, `sale.sh`, `bivouac.sh`,
  `casse.sh`, `boucle.sh`, `boussole.sh`, `ctf/porte.sh`) : ils ne touchent qu'au dossier où on les lance, jamais de
  réseau ni de `sudo` (vérifié par les tests). Chaque partie a sa graine (journal, éboulis, boussole, CTF différents).
- **Sur PC on lance `bash script.sh`** (le `sh` d'Ubuntu, dash, n'a pas `pipefail`) ; sur le téléphone `sh script.sh`
  (mksh). Les étapes `shellcheck`, `man`, `apropos`, `awk` multi-fichiers et `<( )` sont cachées si l'outil manque,
  jamais bloquantes, et absentes du téléphone.

*Les leçons.*
- **S0 le refuge** (`sommet plan`, carnet). **S1 la corde de rappel** : le script qui ment (code 0 malgré l'échec),
  `set -euo pipefail`, les guillemets. **S2 le bivouac** : `trap … EXIT`, `mktemp`, `getopts`. **S3 les regex
  avancées** : ancres, classes, `{n}`, `grep -oE`, `sed -E` et ses captures, sur un journal de la montagne.
  **S4 les one-liners** : `find -print0 | xargs -0`, `$( )`, `<( )`, awk sur plusieurs fichiers. **S5 le débogage** :
  `bash -n` (la ligne), `bash -x` (la variable mal écrite), `shellcheck` s'il est là, `strace` en notion. **S6 la
  documentation** : `man`, `apropos`, `--help`, la boussole qui se lit avec son aide. **S7 le sommet : les défis** :
  le CTF combiné (trois fragments : regex, find, la porte), le chrono et les records, le défi du jour.
- **Le défi du jour** : trois exercices de la salle d'entraînement tirés du jour, à faire en grade Péta ou Exa (or,
  diamant). Ce sont des exercices que le site vérifie DÉJÀ (graine, compteur, empreinte, heure) : le site n'a pas été
  modifié. Le chrono du CTF est un record local.
- Indices : `sudo` refusé, `./script` sans droit d'exécution, `sed` sans `-i`, `-print0` sans `-0`, `<( )` dans `sh`,
  la boussole sans options, mauvaises réponses expliquées.

*Le reste.*
- Exploit « Trois mondes maîtrisés » (`sommet.trois_mondes`, genre légendaire, 3 rencontres favorisées ; fenêtre d'essais du genre, comme le site l'attend) : un légendaire
  EXISTANT parmi ceux qu'aucun autre monde ne réserve — Infernarque, Tellurion, Rugissire, Sylvarque, Essaimpereur,
  Noctilune, Forgerain, Chaosmere (`legendaires` dans `programme.json`, lu par `recompenses.py` / `Recompenses.kt`).
- Vue déployée : la cordée (relit `bash -n`, lampe frontale `bash -x`, cherche `find -print0`, monte au drapeau) ;
  `bash script.sh` reste au parchemin de la Forge (une seule animation par commande).
- Ponts des Nombres jamais bloquants : logique (S1), comptage (S3), puissances de 10 (S7, les grades Péta/Exa).
- « Pour les grands » à chaque étape (G-32) : 63 textes `.adulte` en 14 langues (`textes_sommet_adulte.py`).
- Mode classe : le Sommet est le chapitre 23 (codes `23-GS-H`, `23-AGS-N`) sur la page /enseignants du site et dans les
  fiches enseignant (PDF refait) ; les tests comptent les codes jusqu'au dernier chapitre. **Le site a changé (page
  /enseignants et ses tests) : il n'est pas redéployé.**
- Tests : `pc/outils/test_sommet.py` (63), `tests/jvm/Sommet.kt` (23), `pc/outils/test_sommet_outils.py` (outils du
  téléphone : toybox compilé en CI, busybox, mksh). Simulation `pc/outils/sim_sommet.py` →
  `docs/simulations/rapport_sommet.md`. Captures `pc/outils/capture_sommet.py`. Rejeu d'un seul monde :
  `TG_REJEU_MONDE=sommet`.
- Prompts d'illustrations envoyés au propriétaire (B16, vignette, C1, E25, E26, E27 nouveaux ; à valider). Repli
  dessiné : la montagne en caractères sur PC, `SommetDessin` sur le téléphone.

*Reste.*
- Les illustrations.
- mksh et toybox ne sont vérifiés qu'en CI (pas installés sur la machine de travail).
- Sur Windows (sans bash), la plupart des étapes du Sommet sont cachées : le monde est fait pour Linux, macOS et le
  téléphone.

**📟 Le Poste de Contrôle — codé (1er novembre).**

*Fichiers.*
- 10 fiches (`donnees/controle/outils/fiches_controle.py`, rejeu bash : 27 cas), données `donnees/controle.json`,
  textes `donnees/controle/outils/textes_controle_*.py` (14 langues), vecteurs communs `donnees/controle/vecteurs.json`.
- Leçons ct0 → ct7 sur PC (`pc/tg/controle.py`) et sur Android (`Controle.kt`, `ControleDessin.kt`).
- Chapitre et dossier `controle`, commande `controle` (alias bash/zsh/fish/PowerShell, `tg controle`). Le Poste s'ouvre
  après les niveaux 0 à 6 du tronc commun ; annonce du monde à son tour. Icône 📟 (🎛 ne passait pas le test de largeur
  des cartes), chapitre n° 22, famille Constructs, objet pupitre, titre « Admin du Poste ».

*Règles du monde.*
- **Lecture seule sur la vraie machine.** Le jeu lit `/proc`, `free`, `df`, `/etc/os-release`, la liste des paquets
  (`rpm -qa` si `/usr/lib/sysimage/rpm` existe, sinon `dpkg -l`) et les services (`systemctl list-units`, en lecture).
  Il ne garde aucune liste : il compte.
- **Rien n'est changé.** `dnf`/`apt install`, `systemctl start/stop/restart`, `useradd`, `crontab -e`, `shutdown`,
  `sudo` reçoivent « avec un adulte » (`ct.indice.adulte`, `ct.indice.sudo`). L'installation de Linux est racontée (VM
  d'abord, empreinte vérifiée, sauvegarde). L'équipage est un fichier du Poste (`equipage.txt`, `controle useradd`).
  Les réveils sont un fichier lu par le jeu, qui calcule la prochaine sonnerie sans jamais les lancer.
- **On n'arrête que les habitants du jeu.** La vague = 3 suspects et un veilleur, de vrais `sleep` renommés (`exec -a
  NOM sleep 900`) qui s'éteignent seuls ; le jeu vérifie le numéro ET le nom (`/proc/PID/cmdline`) et ne touche qu'aux
  numéros de `lances.json`. `kill` d'un numéro étranger, `kill 1`, `kill -1`, `killall`/`pkill` sans « fictif » :
  avertissement à chaque fois. Windows et téléphone : vague simulée (`controle ps`, `controle arrete PID` ; sur le
  téléphone, `kill` est intercepté par le jeu).

*Les leçons.*
- **ct0 la porte** : `ls`, `controle consignes`.
- **ct1 les habitants** : `ps`, `echo $$`, `ls /proc/$$`, `head -3 /proc/$$/status`, `controle habitants`, `sleep 5`,
  `sleep 60 &`, `jobs`, `kill %1`, `top` (téléphone : `top -n 1`).
- **ct2 les jauges** : `free -h`, `df -h .`, `du -sh entrepot/*`, la caisse la plus lourde, `uptime`, `nproc`,
  `controle jauges` (pourcentages).
- **ct3 le sac à dos** : `echo $HOME`, PATH une ligne par dossier et compté, `which ls`, `export`, `bash -c`, `alias`,
  `source sac_a_dos.sh`, `echo $POSTE` (téléphone : sur une ligne, `.tgrc` = `.bashrc`).
- **ct4 le carnet de bord** : `controle journal`, `tail -n 5`, `grep -c ALERTE`, `tail -f`, `journalctl --user`,
  `dmesg | tail -3` (refus acceptés ; téléphone : `logcat`).
- **ct5 les réveils** : `controle reveils`, `crontab -l` (lecture), le réveil demandé (`controle cron "M H J M S"`,
  modulo), `>> reveils.crontab`, la prochaine sonnerie.
- **ct6 Linux de A à Z** (§ 7.13) : `cat /etc/os-release`, `controle distribution`, les familles d/a/p, `controle
  installer`, compter les paquets, `controle magasin`, `systemctl list-units … --state=running`, `controle services`,
  `head -3 /etc/passwd`, `controle useradd`, `tail -2 equipage.txt` (téléphone : `getprop`).
- **ct7 l'alerte** : `controle alerte`, `ps aux | grep fictif`, `kill PID PID PID` (pas le veilleur), `controle tableau`.

*Le reste.*
- Vue déployée : le tableau de bord (une jauge qui respire « on regarde », un voyant qui s'éteint « on arrête un
  habitant », un voyant orange « change la machine : avec un adulte ») ; `free`, `nproc`, `lsblk` restent à
  l'ordinateur ouvert de la Salle des Rouages.
- Ponts des Nombres, jamais bloquants : pourcentages, division (jauges, ct2), modulo (`*/15`, ct5).
- Contenu existant réutilisé sans le changer : `machines0`, `systeme1`, `dortoir0`, `systeme2`, `dortoir1`, `scripts2`.
  Ponts vers la Salle des Rouages (M4), la Citadelle (processus), la Forge, l'Observatoire, la Guilde.
- Exploit « Arrêter tous les processus suspects d'une vague » (`controle.vague`, le veilleur épargné). Variantes
  EXISTANTES favorisées (Machine / Roche) : `ressortine:mecanique`, `parasouris:neon`, `pavegarde:montagne`.
- **Ajout transversal (demande du propriétaire)** : sous Windows, `echo j'aime les chats` (apostrophe non fermée, que
  PowerShell prend pour le début d'un texte et qui fait attendre `>>`) reçoit le conseil « Sous PowerShell, mets ta phrase
  entre guillemets : echo "j'aime les chats" » (`core.win.apostrophe`, 14 langues ; `core.apostrophe_ouverte`, testé
  dans `pc/outils/test_windows.py`).
- Mode classe : chapitre 22 « Le Poste de Contrôle » sur la page /enseignants (`site/src/enseignants_fr.js`, **site non
  redéployé**) et dans les fiches enseignant (codes `22-GS-F`, `22-AGS-K`, PDF refait).
- Tests : `pc/outils/test_controle.py` (65), `tests/jvm/Controle.kt` (22). Simulation `pc/outils/sim_controle.py` →
  `docs/simulations/rapport_controle.md`. Captures `pc/outils/capture_controle.py`. Rejeu d'un seul monde en local :
  `TG_REJEU_MONDE=controle`. En CI, `cron` et `procps` sont installés pour le rejeu.
- Prompts d'illustrations envoyés au propriétaire (B8, vignette, C1, C3 et E25 à E27 nouveaux ; numéros E à confirmer).
  Un repli dessiné est affiché en attendant (pupitre en caractères sur PC et dans l'aide du téléphone,
  `ControleDessin.poste`).

*Reste.*
- Les illustrations.
- `rpm -qa` (Fedora) vérifié par le motif et le rejeu, mais pas lancé sur une vraie Fedora (machine de test Ubuntu).
- Sur le téléphone, le dessin graphique du pupitre (`ControleDessin.poste`) n'est utilisé que par les maquettes et le
  test ; l'entrée du monde montre le pupitre en caractères.
- Les traductions des 13 autres langues sont faites par Claude : une relecture par des locuteurs serait bienvenue.

**🗺 Le monde des biomes et les effets des commandes — codé (1er novembre, propositions validées par le propriétaire).**
Ce n'est pas un monde de leçons mais une nouvelle vue : le prototype « Monde Terminagotchi » v4 entre dans le jeu.

*Fichiers.*
- Génération commune (relief, régions, ponts, objets) : `pc/tg/monde_gen.py` = `Monde.kt` = `site/public/js/monde_gen.js`,
  vecteurs `donnees/monde/vecteurs.json`. Dessins en pixels : `pc/tg/monde_dessin.py`, `MondeDessin.kt`. Vue (caméra,
  créatures, liste et fiche, effets) : `pc/tg/monde.py`, `MondeVue.kt`, `site/public/js/monde_page.js`.
- Effets : `pc/tg/effets.py` = `Effets.kt` = `site/public/js/effets.js`, vecteurs `donnees/effets/vecteurs.json`
  (`evenements(ligne, avant, après, code)` fondé sur la PHOTO du terrain avant/après, jamais sur le seul texte).
- Tests : `pc/outils/test_monde.py`, `pc/outils/test_effets.py`, `tests/jvm/Monde.kt`, `site/test/test.mjs`.
  Simulation : `docs/simulations/rapport_monde.md`.

*Ce que voit l'enfant.*
- PC : onglet « Monde » dans le panneau du moment de `tg espace` (apparaît avec la Carte, fin du chapitre 1) ; la
  commande `monde` (ou `tg monde`) l'ouvre en grand (✕ ou Échap). Le repli tkinter garde la Carte. Le terminal texte
  garde seulement « 🗺 la carte a poussé ».
- Téléphone : onglet « Monde » ; la liste « Mes créatures » est un panneau qui monte du bas. Site : page `/monde`
  (terrain d'essai en mémoire, rien n'est envoyé) — **non déployée**.
- Le VRAI terrain `biome/<type>/parcelle_<n>/` (lecture seule, 8 parcelles et 18 objets dessinés au plus), une
  créature par parcelle (le guide d'abord), les autres au refuge avec la commande `mkdir` pour agrandir.
- Fiche À LA PLACE de la liste (« ← Mes créatures ») ; clic à côté ou Échap : la liste revient.
- Effets ★★★ (1 à 2 s, jamais bloquants) : mkdir (parcelle qui tombe), rmdir, rm (confettis), touch (rayon ou
  frétillement), mv, cp, jokers, cd, pwd, ls / ls -a, find, cat, echo > / >>, chmod et les refus doux (cadenas, « ? »,
  tremblement « pas vide »). ★★ : lucioles des processus, pigeon messager, photo git, empreinte, petit tuyau.
  Rafales groupées (« + 30 »), PowerShell reconnu. Réglage « effets : tous / essentiels / aucun » (options, ou
  `monde effets <niveau>`). L'explication est dite par la créature, 3 fois au plus par sorte d'effet.
- Point d'extension pour les autres mondes : `effets.EXTENSIONS` / `Effets.extensions` / `EXTENSIONS` (JS).

*Reste.*
- ~~Les effets ★★ des mondes finis en parallèle, caisse `tar`, `ln -s`, `du`/`df`, `tree`~~ : codés le 2 novembre
  (paragraphe suivant).
- Le site : à redéployer à la main quand le propriétaire le décide.
- Les traductions des 13 autres langues sont faites par Claude.

**🧩 Les derniers effets dans le monde — codés (2 novembre).** Maquettes montrées au propriétaire :
`/home/claude/outils/effets/derniers/planche_derniers.png` (21 images, outils dans `derniers/travail/`).
- Même règle que les autres effets (`effets.py` = `Effets.kt` = `effets.js`, 123 vecteurs communs) : l'effet vient de
  la photo avant/après du terrain ou de la vraie sortie de la commande, jamais du seul texte ; ★★ (réglage « tous »).
- Effets secondaires : `tar`/`zip`/`gzip` (la caisse : des copies entrent et elle se ferme ; elle s'ouvre et les objets
  ressortent ; `gzip` la serre ; `tar -t` regarde dedans), `ln` (le fil lumineux du raccourci, gris et cassé pour un lien
  mort), `du` (une colonne par élément, tailles des objets), `df` (le réservoir, le % lu dans la sortie), `tree` (la
  brume se lève, dossiers et fichiers comptés).
- Poste de Contrôle : `free` (l'étagère de la mémoire), `systemctl` en lecture (les lanternes), `crontab -l` (le
  réveil), `journalctl` (le registre). Bibliothèque du Temps : `git add` (l'étoile), `git log` (l'album), `git init`
  (un album neuf), `git branch/switch -c/checkout -b` (une branche pousse), `git switch` (on change de monde), `git merge`
  (les branches se rejoignent ; conflit = étiquette « à toi de choisir », pas de refus en plus), `git restore` /
  `checkout --` (l'horloge à l'envers sur ce qui revient). Atelier : le robot simulé (`echo 1 > led` : la lumière,
  `moteur`, `cat capteur_distance` : le sonar, `atelier pas` : un pas). Sommet : `man`/`apropos`/`--help` (le grimoire),
  `shellcheck` (la loupe ; ses remarques ne sont pas un « raté »), `trap … EXIT` (le filet), `mktemp` (le sablier),
  `strace` (l'espion).
- Dessins : `monde.py` (`_effet2`), `MondeVue.kt` (`effet2`), `monde_page.js` (plus simple). Pas d'objet sur les
  créatures, pas de mascotte. Textes `efx.*` en 14 langues. Tests : `test_effets.py` (vrai terrain, vrai git),
  `test_monde.py` et `tests/jvm/Monde.kt` (chaque sorte se dessine), `test_terminal.py` (`ln` comparé au vrai bash).
- Terminal du jeu sous Windows (`vsh`) : `ln` existe maintenant (`-s`, `-f`, `-v`, vers un dossier) ; un lien mort se
  voit dans `ls`. Sous Windows, un lien symbolique demande le « mode développeur » : sinon le refus est expliqué
  (`vsh.ln_windows`), rien n'est bloqué ; jamais de lien vers les dossiers de Windows. `shellcheck`, `strace`,
  `systemctl`, `journalctl`, `crontab` restent racontés sous Windows (pas d'effet, comme avant).
- Site : `effets.js`, `monde_page.js`, `monde_textes.js` modifiés — **non redéployé**.
- Captures PC (le vrai jeu, `tg espace`, monde en grand) : `/home/claude/outils/effets/derniers/integre/pc_*.png`
  (outil `/home/claude/outils/effets2/capture_pc.py`). `tout.sh all` vert le 2 novembre.

**▚ Le glitch — codé (31 octobre, décisions du propriétaire).** Un effet de l'INDIVIDU, comme le shiny (drapeau
`glitch`, indépendant de la variante et du shiny) : l'image se dérègle comme un vieil écran, fabriquée à partir de
l'image de la créature (aucune illustration). Au repos le style A (liseré rose/cyan des couches décalées, 2 tranches
décalées), toutes les 3 à 5,5 secondes une rafale saccadée (1er novembre) : 2 ou 3 secousses de 0,12 s du style C
(couleurs ternies cyan/magenta, balayage, pixels morts, 7 tranches, bande de pixels triés ; chaque secousse a ses
tranches) séparées par de brefs retours au style A (0,08 s) ; gif `glitch_saccade.gif` (`pc/outils/capture_glitch.py`). Déterministe (graine = l'identifiant de l'individu), spécification
en entiers dans `pc/tg/glitch.py`, portages `Glitch.kt` et `site/src/glitch.js`, vecteurs `donnees/glitch/vecteurs.json`
(`pc/outils/vecteurs_glitch.py`). Il se pose par-dessus tout ce qui existait, après la teinte shiny : vie (respiration
au pixel fin), animations, poses du bureau / de l'île / de la bulle, toutes les sorties du terminal (Kitty, iTerm2,
sixel, quadrants, demi-blocs), cartes, face-à-face, galerie et profil du site (portrait redessiné dans un canvas).
Repère du nom : `▚` (1 colonne), lettres rose et cyan. Taux : partout 1 chance sur 4096 (shiny + glitch : 1 sur
409 600) ; tiré À PART (`tirage.glitch` : compteur + 2^20) pour que les tirages déjà enregistrés ne changent pas, et
refait par le serveur. Gardiens des 8 boîtes de la Citadelle (`programme.json`, monde citadelle, « gardiens ») :
Énumération → Ricanombre, Droits → Heaumbre, Secrets → Crânard, Hangar → Ombrachne, Scripts → Marionnoire,
Codes → Torsillon, Forensique → Osselet, Social → Drapouille. Maîtriser une boîte (exploits `citadelle.boite`,
`citadelle.boite.droits`, `citadelle.boite.secrets`) donne 15 rencontres favorisées (1er novembre, 5 avant ; 16 compteurs
essayés, le premier gardien gardé : un gardien courant croisé 94 fois sur 100, un rare 36 à 38 fois sur 100) ; le gardien d'une boîte maîtrisée, chaque fois qu'il apparaît, est glitch 1 fois sur 8 (shiny +
glitch : 1 sur 800) ; on ne le reçoit pas, il faut le dresser. Le serveur accepte « gardien » si l'espèce garde bien
une boîte codée (il ne peut pas savoir ce qui a été maîtrisé hors ligne). Tests `pc/outils/test_glitch.py`,
`tests/jvm/Glitch.kt`, `site/test/tirage.mjs`, `site/test/test.mjs`. Le site est à redéployer pour la galerie.

**🐧 Le terminal du jeu sous Windows — codé (2 novembre, décision du propriétaire).**
Décision (2 novembre, 0 h 30 – 0 h 41) : **un seul terminal Linux pour tous les supports, et tout en virtuel** : le
jeu n'embarque, ne télécharge et n'emballe AUCUN binaire ni code tiers (BusyBox refusé).
- Linux et macOS : le vrai bash / zsh, inchangé. Android : inchangé (sh / toybox et les outils Kotlin).
- Windows : plus de PowerShell. Le jeu ouvre **son propre terminal Linux**, écrit en Python sans aucune dépendance
  (`pc/tg/vsh/`) : un shell POSIX (variables, `$( )`, tuyaux, redirections, `if` / `for` / `while` / `case`,
  fonctions, scripts `./x.sh` avec le droit x, `sh -c`, tâches de fond, `jobs` / `kill`, `trap`, `set -euo
  pipefail`…) et les commandes des leçons (ls, cat, cp, mv, rm, mkdir, chmod, find, grep, sed, awk, sort, uniq, cut,
  tr, wc, head, tail, diff, sha256sum, base64, xxd, tar, gzip, bc, expr, sqlite3 (le sqlite3 de Python), ps, kill,
  timeout, less, man, git — le petit git porté de `PetitGit.kt`…). Il agit sur les VRAIS fichiers de
  `~/terrain_terminagotchi` et seulement là ; `/`, `/etc`, `/bin`, `/proc`, `/var/log` sont de petits fichiers du jeu
  en lecture seule (`~/.terminagotchi/systeme`), les droits Linux (chmod 444, +x) sont gardés dans
  `~/.terminagotchi/droits_terminal.json`. Pas d'Internet, aucun programme de Windows lancé (seulement le Python qui
  fait tourner le jeu : ses propres commandes `tg`, `carte`, `atelier`…, et `python3`, voir plus bas), rien dans le
  registre ni le PATH, rien d'installé. Toujours ce terminal, même si WSL est installé (décision du 2 novembre,
  6 h 26 : la proposition WSL est retirée, le jeu ne le cherche plus).
- Honnêteté : une commande absente dit « cette commande n'existe pas dans le terminal du jeu sous Windows » et
  l'étape est racontée comme sur le téléphone, sans bloquer. Restent racontés : le réseau réel (ping, curl vers
  Internet, ssh, ssh-keygen, ip, ss, nslookup…), sudo, systemctl, journalctl, dmesg, lsblk, top / htop, les
  gestionnaires de paquets, gcc / make, pip et les `python3 -m …` autres que la lanterne `http.server`, openssl, gpg, ImageMagick / ffmpeg / sox / exiftool, openscad, podman / qemu, les
  éditeurs (nano, vim), ln, chown, crontab, useradd.
- Plusieurs fenêtres : `tg terminal`, la touche `[t]` de la fenêtre du jeu, `terminal` dans l'espace ; toutes
  écrivent dans `~/.terminagotchi/historique_terminal`, que le jeu lit (la créature mange chaque commande). Android :
  des onglets de terminal dans l'appli (voir « Onglets du terminal (Android) — codé ») ; dans Termux, le jeu explique
  ses sessions.
- Les petits terminaux (`tg mini`, l'île du bureau, l'espace) passent aussi par le terminal du jeu sous Windows ; les
  fichiers du terrain sont écrits avec des fins de ligne Linux.
- Tests : `pc/outils/test_terminal.py` (chaque cas `vrai_terminal` des fiches et une liste de syntaxes, comparés au
  VRAI bash + coreutils : sortie et code identiques ; le Linux virtuel ; le petit git contre le vrai git),
  `rejeu_bash.py --terminal-du-jeu` (l'histoire entière, les 13 mondes et le Sommet, jouée dans ce terminal, le jeu
  jugeant chaque étape), `test_windows.py`. CI : `rejeu.yml` (comparaison au vrai bash sous Linux, et l'histoire en
  mode Windows simulé) et `windows.yml` (une VRAIE machine Windows de GitHub joue toute l'histoire dans le terminal
  du jeu).
- Résultats (2 novembre) : comparé au vrai bash, 417 cas identiques et 0 différence (CI Linux ; 498 / 0 avec python3 et curl) ; l'histoire dans le
  terminal du jeu : 263 identiques, 0 écart (Linux), 265 / 0 (Windows simulé), **250 / 0 sur la vraie machine
  Windows** (toute l'histoire, les 12 mondes et le Sommet). Simulation des trois enfants :
  `docs/simulations/rapport_terminal.md`.
- **python3 et curl dans le terminal du jeu — codé (2 novembre, accord du propriétaire ; Windows seulement, Linux,
  macOS et Android inchangés).** `python3` / `python` (`pc/tg/vsh/python.py`) lance le Python qui fait DÉJÀ tourner
  le jeu (sys.executable), pour de vrai : `python3 -c`, `python3 script.py args`, `python3 -` / `< script.py`,
  `./script.py` (#!/usr/bin/env python3 et droit x), tuyaux, redirections, `input()` au clavier, la console au clavier,
  Ctrl+C / `timeout` / `kill`. Le dossier courant et le script doivent être dans le terrain ; `-m` est refusé (pip…
  racontés), sauf la lanterne (voir plus bas). Une garde (sys.addaudithook, posée avant la première ligne de l'enfant) refuse d'écrire,
  créer ou effacer hors du terrain, de lire hors du terrain (sauf Python lui-même), de lancer un programme, d'ouvrir
  un serveur et toute connexion sauf le phare (127.0.0.1:8042) et les lanternes ; les fichiers écrits ont des fins de ligne Linux ; le
  Traceback est celui du vrai Python avec les chemins du terminal du jeu. `curl` (`pc/tg/vsh/curl.py`) parle
  seulement au phare du Port et aux lanternes de l'enfant : vraie connexion TCP sur 127.0.0.1, vraie requête HTTP/1.1, sortie du vrai curl 8
  (-I, -i, -s, -S, -v, -o, -O, -X, -d, -H, -A, -f, -L, -w, la barre de progression) ; s'il dort, le jeu le rallume
  (comme sur le téléphone). Toute autre adresse (Internet, https 8443, file://, un port local sans lanterne) :
  message clair (« pas d'Internet dans le terminal du jeu »), aucune connexion, l'étape est racontée. Les étapes
  Python de la Forge (F4) et le facteur du Port (P3, P6) et de la Citadelle (C6) sont réelles sous Windows. Tests : `test_terminal.py` § 5 (26 cas python3 et 22 cas curl comparés au vrai
  python3 et au vrai curl 8.5 sur le même phare : identiques) et § 6 (17 garde-fous × 2 modes ; rien écrit hors du
  terrain), aussi sur la vraie machine Windows (`--garde`) ; rejeu de l'histoire dans le terminal du jeu : 266 / 0
  (Linux), 268 / 0 (Windows simulé). Simulation : `docs/simulations/rapport_terminal.md` § 6.
- **La lanterne de l'enfant — codé (2 novembre, 7 h 25, « oui on le fait »).** `python3 -m http.server PORT --bind
  127.0.0.1 [--directory DOSSIER]` marche pour de vrai dans le terminal du jeu : seulement sur 127.0.0.1 (sans
  `--bind 127.0.0.1`, ou avec 0.0.0.0, refusé avec un message clair et la bonne commande), un port de 1024 à 65535
  (pas celui du phare), un dossier du terrain ; la garde ne laisse ouvrir QUE ce port, sur 127.0.0.1. En tâche de fond
  (`&`), elle ne reçoit pas le Ctrl+C du clavier (comme dans bash) ; `kill %1`, `fg` puis Ctrl+C, ou fermer le
  terminal l'éteignent. Les lanternes allumées sont notées dans `~/.terminagotchi/lanternes.json` : `curl` (toutes les
  fenêtres) peut les visiter, en plus du phare ; un port local sans lanterne répond comme le vrai curl (« Couldn't
  connect », code 7) avec le conseil du jeu, sans jamais toucher un autre programme de l'ordinateur. Les autres `-m`
  restent refusés. Port P5 et Forge F6 sont réels sous Windows. `kill PID` trouve aussi une tâche lancée dans un
  sous-shell (`( … & echo $! > pid )`), `kill %1` vise la tâche la plus récente portant ce numéro. Tests : les 9 cas
  `vrai_terminal` avec un serveur (http, serveur, site_web, couches, curl) comparés au vrai python3 + curl (identiques),
  garde-fous (0.0.0.0, port 80, dossier hors du terrain, curl vers un port éteint, la lanterne visitée puis éteinte) ;
  rejeu de l'histoire 268 / 0 (Linux), 270 / 0 (Windows simulé).
- Onglets de l'écran terminal de l'APK : faits le 2 novembre (voir plus bas).

**🪟 Onglets du terminal (Android) — codé (2 novembre, demande du propriétaire).**
- L'écran terminal de l'APK a de vrais onglets : « Terminal 1 », « Terminal 2 »… au-dessus de l'écran du terminal,
  « + » (ou `terminal`, `tg terminal`, comme sur PC) en ouvre un, `exit` ou ✕ le ferme ; 4 au plus ; le dernier ne se
  ferme pas (`exit` y referme le jeu, comme avant). Cachés pendant l'œuf.
- Chaque onglet est un terminal indépendant (`Onglets.kt`) : son dossier courant, son `cd -`, son code de sortie, son
  historique ↑ ↓ (un nouvel onglet part de l'historique de la partie, comme un nouveau bash), son écran et sa ligne à
  moitié tapée. Même terrain, même créature : elle mange les commandes de tous ; les leçons voient chaque commande avec
  le dossier de SON onglet (`Maison.placer` avant chaque commande : le point de départ n'est jamais celui d'un autre
  onglet). Les variables et les tâches `&` restent limitées à la ligne (comme avant sur le téléphone) ; une seule
  commande tourne à la fois (le gardien des coulisses compare une seule photo) : changer d'onglet attend la fin.
- Textes `ong.*` dans les 14 langues ; l'astuce Termux (`vsh.fenetre.android`) renvoie aussi au bouton « + » de l'appli.
- Tests : `tests/jvm/Onglets.kt` (ouvrir, fermer, maximum, numéros ; cd dans l'un ne change pas l'autre ; `cd -`,
  code, historique par onglet ; commandes des deux onglets mangées ; « ls dans la grande salle » validé seulement dans
  l'onglet qui y est).
- Vérifié sur un téléphone virtuel (test-ecran.yml, Pixel 6, clavier ouvert, 2 novembre) : la ligne de saisie et les
  touches restent visibles avec les onglets (c'est l'écran du terminal qui rétrécit) ; dans le Terminal 2,
  `cd terrain_terminagotchi/nid`, `pwd`, `ls` répondent, `exit` ramène au Terminal 1 resté dans son dossier.
- Commande en attente (accord du propriétaire, 2 novembre) : une ligne tapée pendant qu'une commande tourne est
  montrée grisée « ⏳ en attente : `ls` » puis lancée juste après, dans son onglet, jamais collée à la suivante
  (5 au plus). Ctrl+C (touche ^C de la rangée, ou Ctrl+C d'un clavier branché) arrête la commande en cours (code 130,
  « ^C ») ET vide l'attente ; sans commande en cours, il efface la ligne tapée. Vérifié sur le téléphone virtuel
  (`sleep 6` puis `ls` : grisé puis lancé ; `sleep 15` puis `pwd` puis Ctrl+C : arrêt immédiat, `pwd` oublié).
  Test JVM : `tests/jvm/Onglets.kt` (ordre, 5 au plus, Ctrl+C sur `sleep 15`, code 130).

## ✅ Validé (2 novembre) — Direction artistique « règle C » et nouvelle carte du monde

**Règle C** (décision du propriétaire, 2 novembre 2026), pour toutes les illustrations à venir (§ 7.15) :
- **pixel art net et détaillé**, univers **numérique** : racines à circuits verts, matière qui se défait en pixels,
  quelques pierres à facettes à contour cyan, un hologramme vert pâle, lointains en gros pixels avec lignes de
  données, légère pluie de pixels verts, **grandes zones calmes** (l'œil se repose) ;
- **scènes** riches à petits pixels ; **personnages et objets** seuls sur fond **magenta**, pixel art bien marqué ;
- **gardiens = humanoïdes originaux en uniforme** : le Port, un humanoïde à tête de pieuvre bordeaux, gants noirs,
  casquette d'officier ; la Citadelle, un humanoïde tortue cuirassée en uniforme de garde (ils remplacent le
  lion de mer et le blaireau des anciens prompts, à reprendre dans `outils/port` et `outils/citadelle`).

**Nouvelle carte du monde** (`donnees/illustrations/monde.png`, 1672×941, validée le 2 novembre) : même style que
l'ancienne, avec tous les lieux placés — le Carrefour au pied de l'arbre, le camp et le nid dans les racines, la
Bibliothèque du Temps dans le tronc, l'Observatoire en haut de l'arbre, le Port sur la côte de l'eau, la Forge au
flanc du volcan, la Tour des Ondes dans le ciel, le Poste de Contrôle et l'Atelier dans la cité dorée de la
machine, la Citadelle face au château violet de l'ombre, la Salle des Données dans la glace, la Guilde dans les
arbres du biome plante, le Sommet sur le plus haut pic de la roche ; la Salle des Rouages et la Crypte sous terre.
Ce placement fait foi pour les scènes B du § 7.15. Propagée par `donnees/illustrations/generer_intro.py` (intro
Android `assets/intro/monde.jpg`, PC `illustrations.bin` et désormais aussi `pc/tg/carte_monde.png`, l'onglet
« monde » de l'espace de travail) ; `docs/img/terminaworld.jpg` refaite ; le site n'utilise pas cette image.
**Reste** : `dort.png` (le monde endormi de l'intro, écran 2) est dessinée à part et montre encore l'ancienne vue
(sans les lieux) — à redessiner d'après la nouvelle carte (prompt : `outils/artbook/prompt_dort.md`) ; puis relancer
`generer_intro.py` et refaire `docs/img/reveil_monde.gif` (README), qui fond l'ancien endormi dans l'ancien vivant.

**Artbook (préparation, 2 novembre)** : générateur `docs/artbook/generer_artbook.py` → `docs/artbook/terminagotchi_artbook.pdf`
(brouillon) ; les illustrations des mondes se déposent dans `docs/artbook/illustrations/` et entrent toutes seules
à la prochaine génération (voir la tâche finale plus bas).

## ✅ Codé (3 novembre) — Classe et accessibilité (maquettes validées le 3 novembre)

PC et Android, 14 langues, vecteurs communs `donnees/classe/vecteurs_acces.json` (tests `pc/outils/test_classe_acces.py`
et `tests/jvm/Classe.kt`).

- **54/55 · Séance guidée et écran projecteur** : `tg classe seance N` (le déroulé de l'heure dans le terminal de
  l'enseignant, Entrée = phase suivante, `o` question, `t` trace, `c` commande), `tg classe tableau` (la fenêtre du
  vidéoprojecteur suit les phases ; aucun minuteur pour les élèves). Android : `classe seance …`, `classe tableau`
  (écran plein sur une tablette branchée, boutons tactiles). Contenu des 10 séances : `donnees/classe/seances.json`
  + `donnees/classe/outils/textes_seances*.py`.
- **56 · Place de la classe** (code de séance avec la lettre V) : le poste de l'enseignant l'ouvre
  (`tg classe place ouvrir CODE`), seulement sur le réseau local (adresses privées), 2 h au plus, rien n'est
  enregistré ; les élèves la voient dans `tg espace` (`place`) ou au téléphone (`classe place CODE [ip]`) : « Poste
  N », espèce, stade, et trois gestes tout faits (Coucou, Bravo, Danse), un toutes les 3 s. Ni nom, ni pseudo, ni
  texte libre. Un geste déjà vu n'est plus réaffiché au lancement suivant.
- **58 · Carte de visite** : `tg carte visite [sansnom]` (PNG 750 × 1050 dans le terrain de jeu) ; Android
  `carte visite` (Enregistrer dans Images/Terminagotchi, Partager). Les goûts préférés viennent du nouveau compteur
  `gouts` ; jamais le prénom ni le pseudo ; le jeu n'envoie rien.
- **61 · Lecture facile** : police **Andika** (SIL, OFL 1.1, fichiers d'origine du dépôt google/fonts) livrée dans
  `pc/tg/polices/` et `app/src/main/assets/polices/` avec `OFL-Andika.txt` ; dans le `.pyz`, copiée au premier
  usage dans `~/.cache/terminagotchi/polices/` ; fenêtre GTK : ajoutée aux polices de l'application (fontconfig),
  rien n'est installé sur l'ordinateur. Le terminal garde sa police à chasse fixe.
- **62 · Taille du texte** 100 / 125 / 150 % (Ctrl + / Ctrl −, taille du système par défaut). Corrigé : onglets du
  téléphone qui défilent au lieu d'être coupés, légende de la carte PC, cadre « Tu es ici » qui cachait des noms,
  barre d'XP qui chevauchait le type, titre de la carte créature et nombres des envies au téléphone, vue déployée
  qui sortait de son cadre.
- **64 · Couleurs + formes** (■ ▲ ● ◆ ━ ▼ ✚), allumé d'office avec les thèmes Contraste et Daltonien.
- **65 · Mode calme** : rien ne clignote ni ne secoue ; les éclairs des créatures glitch deviennent leur effet
  léger fixe (exception accordée, seulement dans ce mode) ; défi sans chrono. Automatique si le système demande
  moins d'animations.

Vérifié le 3 novembre : `tout.sh all` vert (52 suites PC avec parcours et personas, langues, site, 43 suites JVM).
Reste au propriétaire : relire `docs/classe/seances_guidees.md` et `docs/classe/kit_mediatheque.md` (brouillons),
essai en classe pilote, essai de la place sur le Wi-Fi d'une école (testée ici sur 127.0.0.1 seulement).

## En continu (chaque jour, peu coûteux)

- Variantes : Abyssaux (en cours, 436 / 682 au 28 octobre), puis Célestes, Constructs, Aberrations ; planche par
  famille finie ; scripts `scratchpad/capt.sh`, `com.sh`, nettoyages `violet.py`, `trou.py`, `brume.py [v|b]`,
  `aile.py`, `ailebleue.py`, `fumee.py`, `frange.py` (à recopier dans `donnees/bestiaire2/outils/` pour ne pas les
  perdre).
- Illustrations : suivre le **catalogue du § 7.15** de `docs/programme.md` (carte et Carrefour d'abord, puis chaque
  monde juste avant son développement), planche de validation au propriétaire, statuts mis à jour dans le catalogue.

## Phase finale — L'œuf physique (projet open source)

Schéma de principe d'abord (à valider avec le propriétaire) : ESP32 + petit écran couleur, coque STL « clic pour
ouvrir » d'après les 9 œufs, boutons, batterie ; usages et fonction des boutons à définir ensemble ; transfert d'un
terminagotchi ; option LoRa pour que les œufs se parlent en maillage (§ 7.11).
Proposition à valider (1er novembre) : `docs/oeuf/proposition.md` (variantes, pièces, sécurité, licences, questions).

## ✅ Vérification finale avant la mise en ligne (2 novembre, soir)

Rapport : `docs/verification_finale.md`. `tout.sh all`, `verifier_programme`, rejeu (vrai bash sur la CI, terminal du
jeu Linux 268 / 0, Windows simulé 270 / 0), JVM, site, 14 langues : vert ; trois enfants au bout sur PC Linux,
terminal du jeu (Windows simulé) et appli Android simulée ; 1 684 liens du site sans erreur ; CI verte et téléphone
virtuel (test 72) vérifié ; APK `essai-95`. Corrigé : message « n'est pas une commande » (casse de ce qui est tapé),
README, `.pyc` retiré. À décider : barre d'XP figée à 159/160 le premier jour (✅ décidé et codé le 2 novembre :
« 🌱 XP de côté », ci-dessous), domaine annoncé mais pas branché,
portugais mélangé (Portugal / Brésil). Pas de fusion dans `main`, site non redéployé.

**🌱 XP de côté — codé (2 novembre, décision du propriétaire : « oui à l'affichage »).** Quand l'XP est mise de côté
parce que la créature doit encore attendre des jours bien nourrie pour grandir (barre bloquée, ex. 159/160), une
indication courte s'affiche à côté de la barre : « 🌱 XP de côté · grandit dans N jours » (« demain » pour 1 jour,
« aujourd'hui » quand le jour en cours peut encore compter). N vient des règles existantes de la satiété (jours
soignés manquants ; le jour en cours compte s'il n'est pas encore validé) : rien d'autre ne change. PC : écran de `tg`
(à côté de la barre, ou juste dessous si le terminal est étroit), mini-terminal, espace de travail (au-dessus de la
barre, et à côté du niveau en mode texte) ; Android : sous la barre d'XP, en vert, et dans `etat`. Le site n'affiche
pas de barre d'XP : rien à y changer. 14 langues (`sat.attente.*`). Même calcul en Python et en Kotlin (vecteurs
« attente » et « attente_partie » de `donnees/satiete/vecteurs.json`, `test_satiete.py` § 10, `tests/jvm/Satiete.kt`).
Maquette et captures : `/home/claude/outils/xp/`.

## ✅ Idées techniques cochées (3 novembre) — codé : 71, 72 (préparé), 73, 77, 78, 80 ; maquettes : 74, 75, 76

- **71 Installeur Windows** : `installeur/windows/` (Inno Setup + Python officiel copié, installation sans droits
  d'administrateur) ; tâche CI `installeur-windows` (apk-essai.yml, apk.yml) qui l'installe, lance `tg verifier`, le
  désinstalle (la créature reste) et l'ajoute à la publication. SmartScreen expliqué dans le README.
- **72 F-Droid (préparé)** : `fdroid/fr.terminagotchi.yml`, `fastlane/metadata/android/`, `app/version.properties`,
  `-Ppublication=fdroid` (version fixe, sans signature, sans bloc de dépendances), `.github/workflows/fdroid.yml`
  (fdroid lint + deux builds identiques). Étapes du propriétaire : `docs/fdroid.md`.
- **73 Sauvegarde exportable** : `tg sauvegarde exporter|importer` (pc/tg/sauvegarde.py), `sauvegarde exporter|importer`
  sur Android (Sauvegarde.kt, sélecteurs de fichiers d'Android) ; fichier `.tgsauve` commun (contrôle sha256), sans la
  clé du compte ; importer = une partie de plus (Parties.importer), jamais de remplacement.
- **77 Vérification au démarrage** : pc/tg/sante.py (`tg verifier`), Sante.kt ; vecteurs `donnees/sante/vecteurs.json`.
- **78 Onglets et rotation** : `configChanges` (TerminalActivity) + Onglets.etat / reprendre ; rotation dans tests/scenario.sh.
- **80 Cyberdeck** : `installeur/cyberdeck/installer.sh`, docs/oeuf/cyberdeck.md § 8 bis, test_cyberdeck.py.
- 14 langues (`sante.*`, `svg.*`). Tests : test_sante.py, test_cyberdeck.py, tests/jvm/SanteSauvegarde.kt, Onglets.kt § 6.
- Maquettes 74 (nuage de synchro), 75 (tablette en paysage), 76 (signaler un bug) et questions :
  `/home/claude/outils/ameliorations/technique/` (planche.png, proposition.md).

**☁ 74, 75, 76 — codé (maquettes validées le 3 novembre, 04 h 34 : « fais ce que tu as dit »).**
- **74 Nuage de synchro** : seulement avec un compte, et seulement **hors ligne** (orange barré, « hors ligne · N en
  attente ») ou **pendant un envoi** (bleu, « envoi… ») ; rien quand tout est à jour (`compte` le dit). PC : à droite du
  nom sur l'écran de `tg` (recense.nuage_pc) ; téléphone : pilule en pixels au bout du chemin de la fenêtre
  d'observation (NuageDessin.kt), la toucher l'explique en une ligne. Une synchro qui ne joint pas le site met
  `compte.hors`, une synchro réussie l'enlève. Vecteurs `donnees/synchro/vecteurs.json`.
- **75 Tablette en paysage** : PanneauDeux.kt (le panneau du layout) : deux colonnes, 40 % à gauche (créature, bulle,
  leçon, observation), le grand terminal à droite ; seulement si le petit côté de l'écran fait ≥ 600 dp (tablette 7
  pouces et plus) et en paysage, hors de l'espace de travail ; un téléphone tourné ne change pas.
- **76 Signaler un souci** : `tg bug` (PC, pc/tg/signaler.py), `bug` / `tg bug` et la ligne « 🐞 Signaler ce souci »
  après une vraie panne du jeu (téléphone, Signaler.kt ; un plantage est noté dans files/erreurs.log et annoncé au
  lancement suivant). D'abord la question des grands (« Tu es un adulte ? » + multiplication), puis le rapport en
  entier ; l'adulte choisit : la page GitHub « nouveau signalement » pré-remplie (il l'envoie lui-même avec son compte)
  ou un fichier texte (`~/rapport-terminagotchi.txt`, « Enregistrer sous » d'Android) ou rien. Jamais : nom de la
  créature, pseudo, dossiers, nom d'utilisateur (nettoyer) ; le jeu n'envoie rien. Vecteurs `donnees/bug/vecteurs.json`.
- 14 langues (`rec.nuage.*`, `bug.*`). Tests : pc/outils/test_signaler.py, tests/jvm/SignalerSynchro.kt ;
  téléphone et tablette virtuels : tests/vitrine.sh (workflow vitrine.yml), qui fait aussi les captures de la fiche
  F-Droid une langue à la fois (fr-FR, en-US). La clé de signature des APK n'est PAS changée (juste avant la mise en
  ligne publique). Captures : `/home/claude/outils/ameliorations/technique/captures/code/`.

**📄 Autour du jeu — codé (3 novembre, maquettes validées : « Va y lance tout »).** Rien ne change dans le jeu.
Site : page **Essayer** (`/essayer`, bouton « Essayer sans installer » sur l'accueil et « Essayer » dans le menu) :
le début du jeu rejoué dans la page (`site/public/js/essayer.js`) sur un faux dossier en mémoire, œuf tiré au hasard
parmi les 9 types (`donnees/oeufs/depart.json`), nom proposé « Noisette », mêmes textes que l'intro du jeu (clés
`intro.*` recopiées dans `site/src/autour_textes.js` par `pc/outils/test_autour.py --site`), rien d'envoyé ni
d'enregistré, pas de minuteur. Partie **À imprimer** en bas des fiches des 12 bestioles qui ont un coloriage validé,
page `/imprimer` (lien « Coloriages et posters pour la classe » sur la page Enseignants). Page **Soutenir** : la
partie « Faire un don » et les liens de dons sont retirés dans les 14 langues ; « D'autres manières d'aider » reste.
Papier (`site/public/imprimer/`, fabriqué par `docs/imprimer/fabriquer/`) : 12 coloriages A4 en contours pixels (un
par famille au moins, chacun regardé à l'œil), planche de 20 stickers, poster A3 sans noms + version fond blanc.
`CONTRIBUTING.md` à la racine (code GPL 3+, art/textes/sons CC BY-NC-SA 4.0), lien depuis le README. Vidéo d'une
minute montée en code (ffmpeg, images du jeu, musique synthétisée, sans voix ni enfant filmé) :
`/home/claude/outils/ameliorations/autour/video/` (pas dans le dépôt). Tests : `pc/outils/test_autour.py`,
`site/test/test.mjs` (« Essayer, À imprimer »). **Le site n'est pas redéployé.**
Fait le 7 novembre : `site/public/imprimer/` est cité dans `LICENSE-images.md`, et `donnees/guilde/outils/fiches_guilde.py`
relancé (guilde.json embarque ce fichier, `test_guilde.py` vérifie qu'ils sont identiques).

## ✅ Accueil et aide — codé (3 novembre, maquettes validées) : idées 1, 2, 4, 5, 6, 9, 22, 25, 66, 69, 79

Règles communes : `pc/tg/aide_douce.py` = `AideDouce.kt` (vecteurs `donnees/accueil/vecteurs.json`,
`pc/outils/vecteurs_accueil.py`) ; écrans dessinés du téléphone : `AccueilDessin.kt` (Peintre, aperçus JVM).
- **1 Qui est avec toi ?** : au tout premier lancement sur l'appareil (aucune autre partie), avant l'histoire ; avec un
  adulte, 4 conseils (relire : `tg aide parents`, `aide parents`, Aide du menu). Choix gardé dans la sauvegarde, jamais envoyé.
- **2 Premier ls** : PC, les cases se dessinent dans le terminal (2–3 s, une touche passe) ; téléphone, les puces de
  l'observatoire apparaissent en pixels, puis « Waouh, j'y vois ! ». Plus court (2 s) après le camp qui se rallume.
- **4 Flèche** : pendant l'œuf, jusqu'à 3 commandes réussies (revient après 1 min sans rien taper) ; PC « ▼ tape ta
  commande ici », téléphone bulle + ligne de saisie verte + ◀◀. (7 nov.) Elle revient PENDANT l'attente, sans attendre
  la commande suivante : vrai shell, une ligne gardée au-dessus de l'invite et un petit guet (`tg prompt-fleche`, jamais
  par-dessus `nano` ou `less`, parti dès qu'une commande arrive) ; terminal du jeu (vsh/, Windows) : la saisie attend la
  minute elle-même ; téléphone : flèche et bouton Perdu revus toutes les 5 s.
- **5 Rangée** : ↑ ⇥ ^C - / ~ | . > ⋯ sur une ligne, ⋯ = ↓ >> * " ' $ & _ = ; la touche du symbole attendu s'allume ;
  PC : la 1re fois qu'un symbole arrive, où il est (AZERTY en français, QWERTY sinon, `tg clavier azerty|qwerty`).
- **6 Perdu** : bouton 🧭 (jaune vif après 2 erreurs de suite ou 2 min), carte « Pas de panique » ; PC `perdu` / `tg perdu`.
- **9 Fermer et revenir** : écran à la fin du tronc commun (une fois) ; « Te revoilà ! » dans un nouveau terminal / à la
  réouverture de l'appli ; ✕ entouré de jaune ; aucune récompense.
- **22 `ls ?` / `? ls`** : fiche courte (jamais un repas) ; PC : l'erreur de bash est rassurée, ligne « ? est un joker ».
- **25 Indices** : `indice` / bouton 💡 dans un exercice, une épreuve de dressage ou une leçon « défi sans aide » ; 3
  niveaux tirés de la commande attendue ; rien n'est retiré, seul « forge.sans_indice » n'est pas donné après la réponse.
  (7 nov.) Aussi au Sommet (les 9 réponses à trou : `sommet dates ?`… `-c ? -p ?`, `-k ?` : coup de pouce, la
  commande qui donne la réponse, la réponse ; `sommet.cible_indice` = `Sommet.cibleIndice`, vecteurs « indices » et
  « trous » de donnees/sommet/vecteurs.json) et dans la chasse au trésor du téléphone (Ctf.kt : ses 3 indices écrits,
  l'épreuve du lieu où l'on est, `indice 2` marche toujours ; le trésor rapporte +40 XP même avec les indices). Les
  indices automatiques du Sommet (« Pas tout à fait… ») restent.
  (8 nov.) Quand il n'y a rien à deviner, la phrase d'aide (`ad.ind.rien`, 14 langues) cite aussi le Sommet, et sur le
  téléphone la chasse au trésor (texte propre à Android). Le test JVM Intro (« whoami : 3e fêlure ») échouait certains
  jours : quand whoami était aussi la commande du jour, sa petite fête (« content ») cachait la fêlure, PC comme
  téléphone. Les réactions de l'œuf passent maintenant avant (`core.PRIORITE_ANIM` = `Jeu.PRIORITE_ANIM`, oeuf_1 à 3 :
  9) ; vérification sans date dans test_intro.py et tests/jvm/Intro.kt. `tout.sh all` relancé le 8 nov. : tout vert.
- **66 Fin grisée** : téléphone et terminal du jeu (vsh/), Tab ou → l'accepte ; jamais pendant un exercice ou un défi.
- **69 Tout au clavier** : téléphone, d'office avec un clavier branché (`clavier on|off`) : rangée effacée, anneau jaune,
  Tab / Entrée / Échap ; bureau : ← → Entrée Échap dans le menu rond, `tg menu` l'ouvre.
- **79 Menu** : téléphone, écran du camp + pluie de pixels + titre en pixels + créature ; PC, titre en blocs, ↑ ↓ Entrée ;
  Jouer, Nouvelle partie, Charger, Options (le compte y est), Aide, Quitter.
Tests : `pc/outils/test_accueil.py`, `tests/jvm/Accueil.kt`, scénario du téléphone virtuel. Captures :
`/home/claude/outils/ameliorations/accueil_aide/captures/` (`pc/outils/capture_accueil.py`). `tout.sh all` vert (3 nov.,
après rebase ; citadelle/crypte/intro/port/parcours relancés seuls quand la machine était trop chargée).
**🔊 Les sons — codé (3 novembre, maquette sonore et 8 décisions validées : idées 81, 82, 83, 86).** Tout est
fabriqué par du code au moment de jouer (aucun fichier son, aucune banque, rien de tiers) : `pc/tg/sons.py` (Python
pur, ni numpy ni bibliothèque mathématique : sinus, e^x et 2^x calculés avec + − × ÷) et `Sons.kt` donnent les mêmes
échantillons au bit près (vecteurs `donnees/sons/vecteurs.json` : 224 sons dont les 9 musiques de biome, le thème et
les motifs des 8 gardiens + gardien glitch, le cri des 151 espèces et des variantes bébé / ado / shiny / glitch ;
`pc/outils/vecteurs_sons.py`, `test_sons.py`, `tests/jvm/Sons.kt`). Recette = celle de la maquette (corrélation 1,00
pour les réussites et les musiques, 0,97 pour les cris : seul le bruit change). Décisions : silencieux par défaut,
question « Tu veux m'entendre ? » une fois à la première éclosion (bulle + terminal ; boîte Oui / Non sur Android) ;
musique seulement dans l'espace (vues Monde / Espace), 20 s de silence après 3 tours, fondu de 1 s ; thème des gardiens
pendant la rencontre d'un gardien ; cri bébé +5 demi-tons, ado +2 ; shiny étincelle, glitch qui bégaie ; au plus un son
de retour par tour (étape, exploit, évolution, nouvelle créature ; erreur douce, « presque », refus doux ; petite
réussite une fois sur trois au plus) ; silence de 20 h 30 à 7 h 30 sauf « ce soir seulement » ; la créature qui dort
ne crie pas ; le mode classe (séance et `espace classe`) coupe tout. Volumes séparés (musique 30, cris 60, réussites 50)
: `tg son [oui|non|musique N|cris N|retours N|soir|essai]` (téléphone : `son`, et « Réglages du son » : de vrais
curseurs de volume — décision du 3 novembre, 04 h 14, voir plus bas ; bulle : réglage Son et cri au toucher). Point d'entrée des autres modules : `sons.son("evolution")` /
`Sons.son(nom, ctx)` (déjà appelé par le chantier « créature » ; le même son demandé deux fois en 3 s ne joue qu'une
fois). Lecture : Linux `pw-play`, sinon `paplay`, sinon `aplay` par l'entrée standard (sinon silence) ; Windows winmm
par ctypes, sinon winsound ; macOS afplay ; Android AudioTrack (focus audio, silencieux/vibreur respecté, pause en
arrière-plan). Les commandes tapées dans le shell (invite) jouent par un petit processus à part (`tg son _jouer`).
CI : `test_sons.py` dans rejeu (Linux) et windows.yml. `tout.sh all` vert (PC, langues, site, 40 suites JVM dont Sons).
*Curseurs du son (3 novembre, 04 h 14)* : sur le téléphone, « Réglages du son » (`son`, ou Réglages) est une vraie
fenêtre (`SonsReglages.kt`) : l'interrupteur son oui / non, trois curseurs de 0 à 100 % (musique, cris, réussites ;
la musique ramenée à 0 s'éteint en gardant son volume, poussée au-dessus de 0 elle s'allume ; un petit son d'essai
quand on lâche le curseur des cris ou des réussites) et le bouton « 🌙 Ce soir seulement ». Accord corrigé sur PC et
téléphone : « Musique des biomes : 30 % (éteinte) » (clés `son.allumee` / `son.eteinte`, féminin en fr, es, it, pt,
ar). Tests : `test_sons.py` et `tests/jvm/Sons.kt` (§ 4, curseurs glissés par les imitations SeekBar / Switch). `tout.sh all`
(6 nov., après rebase) : 98 suites vertes sauf `test_apprendre` (défi du jour `ls -a` du 6 novembre : échoue aussi
sans ce changement, dépend de la date) ; `test_citadelle`, instable sous charge, vert relancé seul.

**🎒 Apprendre en jouant — codé (3 novembre, PC et Android, maquettes validées) : idées 21, 23, 24, 27, 29, 30, 41,
42, 43, 44, 45, 46, 49, 50.** `pc/tg/apprendre.py` et `Apprendre.kt` / `ApprendreDessin.kt`, données
`apprendre.json` (copie PC = copie Android), vecteurs communs `donnees/apprendre/vecteurs.json`, textes
`apr.*` dans les 14 langues (`donnees/apprendre/outils/langues/`). Bac à sable (`tg bac-a-sable`, rien ne compte),
tableau des rares (`tg collection rares`), maîtrise ●●◉ (titre « Main sûre »), révisions espacées (`tg souvenirs`,
jamais « oublié »), commande du jour et calendrier de tampons (`tg jour`, aucun « de suite »), énigme de la semaine
(`tg enigme`), erreurs en mini-énigmes (`tg passe`), carnet illustré (`tg carnet`, 20 images 16 × 16 dessinées en
code), 4 mini-jeux (`tg jeux`) et course optionnelle (`tg course`, `tg course eclairs non`), limite de temps douce
(`tg parent temps 45` + « oui je suis un adulte » : elle dort jusqu'à 7 h, la faim ne baisse pas), sentier des
marmottes (`tg sommet sentier`, exploit `sommet.sentier` → variante `mousselin:montagne`, monde « sentier » dans
programme.json), examen-aventure et diplôme PNG (+ SVG sur PC ; sur le téléphone « Enregistrer l'image » et
« Imprimer », ligne vide pour le prénom, rien d'enregistré). Tests : `pc/outils/test_apprendre.py`,
`tests/jvm/Apprendre.kt`.

## Ce qui attend une décision ou une action du propriétaire

- Tester l'APK d'essai de la phase 1 et donner ses retours.
- Régler `SECRET_GRAINES` (phase 2).
- Le nom de domaine `terminagotchi.com` (pas encore branché sur le site).
- Valider les planches d'illustrations au fil de l'eau.
- Trouver, s'il le peut, des enseignants relecteurs et des classes pilotes.

## Propositions à valider (29 octobre)

### ✅ Validé (29 octobre) — ✅ Codé (31 octobre, PC et Android) — La satiété : pourquoi bien nourrir sa créature, sans mort ni corvée

**✅ Codé** : `pc/tg/satiete.py` et `Satiete.kt` (mêmes règles, vecteurs communs `donnees/satiete/vecteurs.json`),
tests `pc/outils/test_satiete.py`, simulation de 14 jours `pc/outils/sim_satiete.py`, `tests/jvm/Satiete.kt`.
Valeurs retenues : 2160 s d'éveil par point (7 h - 21 h), soit ~23 points par jour ; rassasiée ≥ 80, en forme ≥ 40,
affamée ≥ 15, en veille en dessous (réveil : 3 commandes différentes) ; XP +20 % / −20 % / −40 % (jamais de perte sur
les leçons) ; dressage rassasiée +15 s et exemple tout de suite ; rencontres ×1,25 ; aliments : nouveau goût 8, puis
4-3-2-2-1,5 par famille et par jour, répétée ou ratée 0,5 ; 6 familles (🧭 se repérer, 🧱 bâtir, 🔍 lire et chercher,
🔌 brancher, 🔑 protéger, 🔭 observer), assiette complète +10 faim et +5 XP ; jour soigné = jour qui finit au moins en
forme (ou 3 commandes différentes en forme pendant le jeu) ; évolution : 3 jours soignés pour Bébé → Ado, 7 pour
Ado → Adulte (l'XP en trop attend, jamais perdue, et ne bloque aucune leçon) ; série : médailles à 3, 7, 14, 30 jours,
un jour fini affamée retire un cran ; lien : phrases à 3 jours, cœur à 7, talent « Cœur fidèle » (faim ×1,25 plus
lente) à 30 ; longue absence : 21 jours ; mode vacances `tg vacances` / `vacances`. Reste : la mise en pause
automatique du mode classe (le mode classe n'existe pas encore), la variante rare plus fréquente (le tirage est vérifié
par le serveur), et l'aura du compagnon de départ (il n'a pas d'aura : à maquetter).

Constat : aujourd'hui la faim descend d'un point toutes les 12 minutes (720 s, 24 min avec le talent Gardien) : on
passe de « rassasiée » à « vide » en **environ 20 h**, même si l'enfant n'a pas joué. Trop rapide pour un jeu où
nourrir demande de vraies commandes, et injuste pour un enfant qui ne joue pas tous les jours.

Proposition (à valider par le propriétaire avant code) :
1. **Rythme** : la faim ne descend que pendant les **heures d'éveil** (7 h - 21 h, la créature dort la nuit comme
   l'enfant) et environ **3 fois plus lentement** : de rassasiée à affamée en ~2 jours de vie réelle, jamais de
   chute brutale. **Mode vacances / école** (réglage, ou automatique en mode classe hors des heures de cours) : la
   faim est en pause.
2. **Quatre états** au lieu d'une simple jauge :
   - **Rassasiée (80-100)** : bonus (voir 3) ;
   - **En forme (40-80)** : normal ;
   - **Affamée (15-40)** : petits malus ;
   - **En veille (0-15)** : la créature se met en veille (yeux mi-clos, couleurs ternes). **Jamais de mort**, et
     **l'apprentissage n'est jamais bloqué** : leçons, carte, lexique restent accessibles. Elle se réveille avec
     un « repas complet » (3 à 5 commandes variées).
3. **Ce que rapporte une créature rassasiée** :
   - **Concentration** : +20 % d'XP sur les commandes et les leçons ;
   - **Dressage facilité** : quelques secondes de plus aux épreuves et un indice gratuit ;
   - **Rencontres** : les créatures sauvages sont attirées par une compagne en pleine forme (plus de rencontres,
     un peu plus de chances de variante rare) ;
   - **Évolution** : pour passer au stade suivant, il faut, en plus de l'XP, être restée **bien nourrie** un
     certain nombre de jours (pas forcément d'affilée) — le soin compte, comme dans un vrai tamagotchi ;
   - **Lien** : chaque jour bien nourrie ajoute des points de lien, qui débloquent des phrases, des réactions et,
     à la longue, un talent propre à la créature ;
   - **Aura et biome** : l'aura brille davantage, et son coin de biome fleurit.
4. **Ce que coûte la faim** : moins d'XP, pas de dressage ni d'épreuve de type, le guide est grognon (indices plus
   courts), l'aura pâlit, le biome se fane ; en veille, l'équipe peut choisir un autre guide.
5. **Nourrir intelligemment** (pédagogie) : chaque **famille de commandes** est un **aliment** (se repérer,
   bâtir, lire et chercher, brancher, protéger…). Un repas **varié** nourrit beaucoup plus qu'une même commande
   répétée (rendements décroissants : `ls` dix fois de suite ne rassasie pas), les **nouvelles commandes** (« nouveau
   goût ») nourrissent le plus, une commande **ratée** nourrit à peine. Une petite « assiette » montre les familles
   déjà mangées aujourd'hui : ça pousse naturellement à varier et à découvrir.
6. **Série de soins** : X jours de suite « en forme ou mieux » → badge et petite récompense ; une journée manquée ne
   remet pas tout à zéro (on perd un cran, pas la série entière).
7. **Longue absence** : au-delà de quelques semaines, la créature part se reposer dans son biome (rien n'est perdu,
   on la retrouve en revenant) ; l'héritage reste réservé aux très longues absences.

### Inspirations : CYBERLIFE (et Autonomous System Zero)

CYBERLIFE (Steam, sorti le 27 octobre 2026) : jeu de piratage **entièrement au terminal**, monde unique partagé,
réseau découvert **saut par saut sans carte**, entreprises à pénétrer, « localhost » comme refuge, butin à ramener,
cinq **classes-métiers avec leurs propres commandes**, pas de jauge de vitesse de frappe (« l'observation, pas la
vitesse »), les actions laissent des **traces** dans des journaux. Autonomous System Zero (OneManSprint) : pas
encore sorti, page vide (stratégie / hacking / 4X en ligne) — à revoir à sa sortie.

Ce qu'on peut reprendre, adapté à notre esprit (éducatif, défensif, sans affrontement entre joueurs, sans argent) :
- **Le Port découvert saut par saut** : dans le réseau simulé (biomes = machines), la carte réseau n'est pas
  donnée ; on la dessine soi-même avec `ip route`, `ping`, `tracepath`, et on la garde dans son carnet.
- **Le camp de base = `localhost`** : tout ce qu'on trouve dans le Terminaworld ne compte que **ramené et rangé au
  camp** (apprend `cp`, `mv`, `scp` dans le réseau simulé, la sauvegarde).
- **Les métiers** : à la sortie du tronc commun, on choisit une **spécialité** (Explorateur, Bâtisseur, Défenseur,
  Messager, Développeur…), chacune avec ses propres commandes avancées et ses épreuves — liée à l'orientation des
  mondes (§ 2.9) ; on peut en changer.
- **L'observation avant la vitesse** : principe déjà retenu (les chronos restent facultatifs) ; à afficher.
- **Les traces** : chaque action laisse une ligne dans un journal du jeu ; dans la Citadelle, on apprend à les lire
  (défendre) et à comprendre pourquoi on ne peut pas « passer sans laisser de trace ».
- **Un monde partagé (site)** : des événements de communauté coopératifs (« réveiller ensemble le biome Glace »),
  des cartes réseau partagées entre joueurs, une bibliothèque de petits scripts écrits par les joueurs (Guilde,
  relus avant publication) — jamais d'attaque d'un joueur contre un autre, jamais de commerce.

### Validé par le propriétaire (29 octobre) : le Grand Maillage

Retenus : l'exploration où l'enfant **dessine lui-même la carte réseau**, le **mode survie**, le **camp de base =
`localhost`**, et le **monde à découvrir partagé**. À maquetter puis concevoir en détail :

**Le Grand Maillage** — une « galaxie » numérique **infinie**, générée procéduralement, faite de nœuds (machines,
relais, îlots de données) reliés entre eux, au-delà du Terminaworld. On n'y va que **par le terminal**, à partir de
son `localhost` (le camp de base).
- **Exploration** : aucune carte fournie ; chaque saut se fait avec de vraies commandes du réseau simulé (`ping`,
  `tracepath`, `ip route`, `ssh` vers un nœud, `ls` / `cat` sur place), et l'enfant **dessine sa carte** (un
  fichier de carte qu'il complète lui-même ; la carte du jeu ne montre que ce qu'il a relevé).
- **Mode survie** : ressources limitées pendant une expédition (énergie de la créature, nombre de sauts, place dans
  le sac = taille des fichiers transportés) ; tout ce qui est trouvé ne compte qu'une fois **ramené au localhost**
  (`cp`, `mv`, `scp`), sinon c'est perdu au retour forcé ; on peut poser des **relais** (points de sauvegarde) pour
  aller plus loin.
- **Ce qu'on y trouve** : rencontres de créatures propres au Maillage (variantes « réseau »), **événements**
  (tempête de paquets, nœud qui s'éteint, relais en panne à réparer), **défis particuliers** (énigmes de
  configuration, petites boîtes de la Citadelle, chiffres de la Crypte), fragments d'histoire du Terminaworld.
- **Monde partagé (avec le site)** : la galaxie est la même pour tous ; les nœuds découverts portent le nom de leur
  découvreur ; événements de communauté coopératifs (rallumer ensemble une région éteinte) ; on peut partager ses
  relevés de carte.
- **Progression** : les régions proches sont faciles ; plus on s'éloigne, plus les nœuds demandent des notions
  avancées (redirections, droits, réseau, crypto, scripts) — le Maillage devient le terrain de jeu de tous les
  mondes.

**Mode « Arène » (joueurs expérimentés, JcJ)** — à concevoir avec garde-fous :
- **facultatif**, débloqué seulement après le tronc commun et plusieurs mondes ; pour les mineurs, activé par un
  parent ou un enseignant (ou réservé à une classe / un club) ;
- **attaque-défense façon CTF** : chaque joueur défend un **avant-poste simulé** sur le serveur du jeu (sa machine
  du Maillage) et tente de prendre le drapeau des autres avant-postes — tout est **simulé dans le jeu**, jamais
  la vraie machine d'un joueur, jamais Internet ;
- **pas de discussion libre entre inconnus** (messages prédéfinis seulement), pas de perte définitive (on perd des
  points de saison, pas sa créature ni ses fichiers), saisons courtes, classement par équipes possible ;
- règles d'éthique et rappel légal affichés à l'entrée (comme la Citadelle).

Ordre : après le Port (le réseau simulé en est la base) et la Citadelle (pour l'Arène).

### Validé par le propriétaire (29 octobre, suite) : l'extraction et le convoi

**Ce qu'on rapporte du Grand Maillage** (esprit « Dark Zone » : le butin n'est à soi qu'une fois extrait au localhost) :
1. œufs rares et variantes « Maillage » (néon, données, glitch) introuvables ailleurs ;
2. fragments de code : vrais petits scripts à assembler, qui débloquent des commandes de la créature et des outils
   (scanner, relais plus puissant, sac plus grand) ;
3. de quoi agrandir et décorer le localhost (la base devient une petite machine qu'on améliore) ;
4. cartes et relais : chaque nœud rapporté s'ajoute à la carte partagée avec le nom du découvreur ;
5. archives et fichiers chiffrés (ouverts dans la Crypte) qui racontent pourquoi le Terminaworld s'est endormi ;
6. nourriture rare (bonus temporaires, lien avec la satiété) ;
7. Arène : titres, badges et place au classement uniquement. **Pas d'objets cosmétiques sur les créatures** (essai passé d'accessoires superposés aux images : rendu pas joli, refusé par le propriétaire le 29 octobre).

Risque : énergie à zéro ou « déconnexion » loin de la base → on perd ce qui n'est pas encore rapporté, jamais la
créature ni ce qui est déjà au localhost.

**Le convoi à défendre** : un paquet de données doit traverser plusieurs nœuds jusqu'à destination. On le protège au
vrai terminal : surveiller le trafic (`tail -f`), poser des règles de pare-feu simulé, changer de route, vérifier
l'empreinte (`sha256sum`) à l'arrivée pour prouver qu'il n'a pas été modifié. Coopératif d'abord ; version Arène
ensuite (une équipe escorte, l'autre intercepte, puis on inverse). Notions : routage (Port P9), pare-feu
(Citadelle), intégrité (Crypte K3).

## Tâche finale — L'artbook

- **Artbook PDF (demande du propriétaire, 1er novembre)** : à la fin de toute la conception, un artbook en PDF qui
  reprend l'histoire, le lore, les habitats et des posters de tous les Terminagotchi.
