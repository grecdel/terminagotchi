# Vérification finale avant la mise en ligne (2 novembre 2026)

Branche `nouveau-bestiaire`. Rien n'a été fusionné dans `main` et le site n'a pas été redéployé : la fusion et la
mise en ligne attendent l'accord du propriétaire.

**En une phrase :** tout ce qui est testé automatiquement est vert, les trois enfants (7, 12 et 15 ans) vont au bout
sur PC Linux, dans le terminal du jeu sous Windows et sur l'appli Android ; trois petits défauts ont été corrigés ;
il reste surtout des **questions de conception** et une **relecture humaine des langues**, rien de bloquant.

---

## 1. Les tests (tous relancés)

| Quoi | Résultat |
|---|---|
| `tout.sh all` (tests PC, parcours, personas, langues, site, suites JVM de l'appli Android) | ✅ tout vert, relancé trois fois, la dernière sur la version finale de la branche (avec la nouvelle carte du monde et l'artbook de l'autre agent) ; un seul faux rouge, voir § 5 « mineur » |
| Tests PC (`pc/outils/test_*.py`, 42 fichiers) | ✅ 0 échec |
| Suites JVM / Android (38 suites) | ✅ 0 échec |
| Site (`site/test`), tirage, migrations | ✅ |
| Langues | ✅ PC : 14 langues · 8 634 textes · 0 erreur ; Android : 8 613 textes · 0 erreur |
| `verifier_programme.py` (charte de rigueur) | ✅ 175 fiches, 883 étapes PC, 780 étapes Android, 29 notions de maths, 14 mondes |
| Vecteurs communs Python / Kotlin / site (16 fichiers `vecteurs_*.py --verifier`) | ✅ tous à jour |
| Rejeu dans le terminal du jeu (Linux) | ✅ 268 sorties identiques au vrai bash, 0 écart |
| Rejeu dans le terminal du jeu, **Windows simulé** | ✅ 270 identiques, 0 écart |
| Rejeu dans un **vrai bash** | ✅ sur la CI (qui installe les vrais outils). Sur cette machine de travail, il manque `ping`, `ss`, `sqlite3`… : les mondes s'arrêtent au Port faute de `ping` ; ce n'est pas un défaut du jeu. |
| Simulations des 13 mondes (`sim_*.py`, trois enfants chacun) | ✅ 3/3 enfants au bout dans chaque monde ; satiété 20/20 ; suiveur 37/37 |
| CI GitHub sur le commit vérifié | voir § 6 |

## 2. Les trois enfants, sur les trois plateformes

Léa (7 ans, fait des fautes d'abord), Inès (12 ans, recopie la commande verte), Hugo (15 ans, essaie ses propres
variantes, ou lit tout).

| | PC Linux (vrai bash) | Terminal du jeu sous Windows (simulé) | Appli Android (simulée) |
|---|---|---|---|
| Léa | ✅ chapitres 1-4, chaque faute reçoit une explication | ✅ idem, mêmes messages | ✅ les 10 chapitres jusqu'à l'énigme d'Abyssor (*) |
| Inès | ✅ | ✅ | ✅ les 10 chapitres, monde réveillé |
| Hugo | ✅ ses variantes justes sont acceptées | ✅ idem | ✅ les 10 chapitres, monde réveillé |

(*) Le robot qui joue Léa ne sait pas recompter la réponse de l'énigme finale : c'est une limite du robot (déjà
notée le 31 octobre), pas du jeu ; Inès et Hugo répondent juste et l'énigme est acceptée.

Comparaison PC Linux / Windows : les messages du jeu sont **mot pour mot les mêmes** ; seules changent les
sorties normales des commandes (nom d'utilisateur `eleve`, dossier `/home/eleve`).

Commandes « habitudes de Windows » essayées dans le terminal du jeu : `cls`, `cd..`, `del`, `explorer .` reçoivent
le bon conseil (« essaie `clear` », « essaie `cd ..` »…) ; `notepad` est raconté ; `python` hors du terrain explique
qu'il faut entrer dans le terrain.

Comment on a joué (outils, hors du dépôt) : `pc/outils/personas.py` (PC) ; une copie qui remplace le vrai bash par
le terminal du jeu en mode Windows (`/home/claude/outils/verif/personas_vsh.py`) ; le robot de l'appli Android du
31 octobre (`Eleve3.kt` + `bot.py`), recompilé sur le code d'aujourd'hui (`/home/claude/outils/verif/simv3/`).
Limites : le robot Android imite l'écran du terminal de l'appli (pas un vrai téléphone : voir le téléphone virtuel,
§ 6) ; les commandes réseau (`ping`, `ifconfig`) n'existent pas sur la machine de test, l'étape est alors sautée
comme prévu.

## 3. Cohérence

- `programme.json` : les **3 copies sont identiques** (même empreinte).
- Vecteurs communs : Python = Kotlin (= site quand il est concerné), tous à jour.
- **Liens du site** : 1 684 pages et ressources parcourues (dans les 14 langues), **0 lien cassé**. Les textes du site
  existent dans les 14 langues.
- **README** : liens vers `LICENSE`, `LICENSE-images.md`, fiches enseignant (PDF) et images : tous présents.
- **Fiches enseignant** : le `.md` et le `.pdf` sont du même jour ; les codes de séance sont vérifiés par
  `test_classe.py` (vert).
- **Licences et interdits** : la mascotte du site n'apparaît nulle part dans le jeu (PC, appli, monde) — elle sert
  seulement d'icône de l'appli, comme écrit dans le README ; aucune crypto-monnaie, NFT, portefeuille, achat ni vente
  (la Crypte le vérifie par un test) ; aucun accessoire ni cosmétique posé sur les créatures (vérifié par test).

## 4. Ce qui a été corrigé

1. **PC : le message « n'est pas une commande » répétait la faute en minuscules.** Léa tape `ls-R`, le jeu
   disait « « ls-r » n'est pas une commande… tu voulais dire « ls -R » ? ». Il montre maintenant ce qu'elle a
   vraiment tapé (« ls-R »), comme sur Android. (`pc/tg/core.py`)
2. **README pas à jour** : les mondes avancés étaient marqués « en construction » alors qu'ils sont jouables ; le
   Sommet manquait dans le tableau ; l'espace de travail, la vue déployée et la créature du bureau étaient encore dans
   « Bientôt » alors qu'ils existent (`tg espace`, `tg deploie`, `tg cerveau`, `tg bureau`) ; « plus de 680
   variantes » → « plus de 800 » (833 dans le bestiaire) ; une double ligne de séparation.
3. **Un fichier compilé Python** (`pc/__pycache__/__main__.cpython-313.pyc`) était enregistré dans le dépôt par
   erreur et changeait à chaque test : retiré (le dossier `__pycache__` était déjà ignoré).

## 5. Ce qui reste (avec gravité)

**Aucun problème critique.** Rien n'empêche de jouer.

### Moyen (à décider par le propriétaire)

- **La barre d'XP reste bloquée à 159/160 pendant presque tout le premier jour** (PC et Android). C'est voulu (la
  satiété validée le 29 octobre : pour grandir de Bébé à Ado, il faut 3 jours bien nourrie ; l'XP en trop est mise de
  côté, jamais perdue). Mais l'écran principal ne le dit pas : seule une bulle « presque prête à grandir » (une fois
  par heure) et l'écran des envies l'expliquent. Un enfant qui joue toute l'histoire le premier jour voit sa barre
  figée. **Proposition :** afficher à côté de la barre « 🌱 +N XP de côté · grandit dans N jours » (PC et Android,
  14 langues).
- **Le site et le README annoncent `https://terminagotchi.com`**, mais le nom de domaine n'est pas encore branché
  (plan de bataille, « ce qui attend le propriétaire »). **Proposition :** brancher le domaine avant d'annoncer la
  mise en ligne, ou mettre l'adresse actuelle du site dans le README en attendant.

### Mineur

- Android : une commande tapée tout en MAJUSCULES qui est un mot du shell (`FOR`, `IF`, `WHILE`) reçoit « je ne
  connais pas la commande « for » » au lieu de « les commandes s'écrivent en minuscules ».
- Sous Windows, la ligne « 💻 Dans un vrai terminal (Linux, macOS) : `cd /home/eleve/…` marche pareil » montre le
  chemin du Linux virtuel du jeu ; sur un vrai Linux, le dossier personnel aura un autre nom.
- Dans le terminal du jeu sous Windows, `ipconfig` ne reçoit pas de conseil (les autres habitudes de Windows, si).
- **Un test un peu fragile** : `test_monde.py` a échoué une fois (3 vérifications du clic sur une créature qui se
  promène) pendant que l'ordinateur de test était très chargé ; relancé trois fois juste après : 119 / 119. La
  créature bouge entre le moment où le test la vise et le clic. À rendre plus robuste (figer l'horloge du test).
- Petites différences déjà connues du terminal du jeu (voir `docs/simulations/rapport_terminal.md` § 5).

### Langues : à faire relire par des humains

Contrôle automatique : **aucun texte manquant, vide ou resté en français** dans les 14 langues (PC, Android, site) ;
les `{noms}` à remplacer et les commandes en vert sont les mêmes partout. Les deux seuls textes identiques au français
sont des listes de commandes (`citadelle inspecteur …`, `agent lance …`), c'est normal. Un échantillon relu au hasard
(anglais, espagnol, allemand, italien, portugais, russe, indonésien) est juste et naturel. Doutes pour un relecteur :

- **Portugais : mélange du Portugal et du Brésil** (« você / sua » et « tu / teu », « telemóvel » et « celular »,
  « ficheiro » et « arquivo »). Choisir une seule variante (ou deux langues).
- Les phrases à déchiffrer de la Crypte (César, ROT13) restent en anglais dans toutes les langues : c'est sans doute
  voulu (le chiffre porte sur l'alphabet latin), à confirmer.
- Japonais, chinois, hindi, bengali, ourdou, arabe : aucune erreur visible pour un contrôle automatique, mais ils
  n'ont jamais été relus par un locuteur ; l'arabe et l'ourdou (écriture de droite à gauche) mélangés aux commandes
  sont à regarder sur un vrai téléphone.

## 6. CI et téléphone virtuel

| Workflow (GitHub) | Commit `792f20d6` (corrections de cette vérification) | Commit `59a7f64d` (tête de la branche, avec l'artbook) |
|---|---|---|
| Charte de rigueur (rejeu dans un vrai bash, terminal du jeu, Windows simulé, toybox…) | ✅ | ✅ |
| APK d'essai | ✅ `essai-94` | ✅ **`essai-95`** (le plus récent) |
| Windows (le jeu démarre, histoire jouée sur une vraie machine Windows) | ✅ | ✅ |
| Téléphone virtuel (`test-ecran.yml`, Pixel 6, Android 13) | ✅ test n° 72, 35 captures | — (le code de l'appli n'a pas changé depuis) |

APK à tester : <https://github.com/grecdel/terminagotchi/releases/tag/essai-95>.

**Captures du téléphone virtuel** (branche `captures`, « Captures du test 72 ») regardées une par une : intro
illustrée, baptême, œuf qui se fêle, éclosion, nid, fin du tronc commun, onglets du terminal (ouvrir, changer de
dossier, revenir), commande mise en attente puis lancée, Ctrl+C, arbre, recherche, erreur expliquée, jeux de la
créature, collection, dressage (rencontre, examen, repaire), troupe, fiche et animations d'Abyssor, donjon, plan,
CTF, compte créé / lié / état, Doom, retour à l'accueil. **Aucun écran vide, aucun plantage, aucun texte brut
(clé de traduction) visible**, `erreurs_compilation.txt` est vide. Les premiers écrans sont en anglais parce que
le téléphone virtuel est réglé en anglais ; le scénario passe ensuite le jeu en français (`langue fr`), c'est
normal. L'intro montre encore l'ancienne vue du monde endormi (`dort.png`, à redessiner : déjà noté au plan).

## 7. Prêt pour la mise en ligne ?

**Oui, côté code et tests** : la branche `nouveau-bestiaire` (commit `59a7f64d` et ce rapport) peut être fusionnée
dans `main` quand le propriétaire le décide. Avant d'annoncer publiquement, il est conseillé :

1. de tester soi-même l'APK `essai-95` sur un vrai téléphone (surtout l'arabe et l'ourdou) ;
2. de décider pour la barre d'XP figée le premier jour (§ 5) ;
3. de brancher le nom de domaine, ou de corriger l'adresse du README (§ 5) ;
4. de régler le secret `SECRET_GRAINES` du site s'il ne l'est pas encore (anti-triche) ;
5. de lancer la mise en ligne du site (workflow « Mettre le site en ligne ») seulement après la fusion — il n'a pas
   été redéployé pendant cette vérification ;
6. de faire relire les langues par des humains, au moins le portugais (§ 5), puis les langues jamais relues.
