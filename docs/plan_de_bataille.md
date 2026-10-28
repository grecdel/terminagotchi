# Plan de bataille — reprise du vendredi 30 octobre 2026, 16 h (Paris)

> Fichier interne de travail. La limite hebdomadaire des gros travaux se réinitialise vendredi à 16 h.
> Objectif : sortir **le plus tôt possible** des versions jouables et testables, puis dérouler le programme
> (`docs/programme.md`, partie 7) monde par monde. L'œuf physique vient en dernier.

## Règles de conduite pour toute la semaine

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
     l'œuf du type tiré apparaît dans le nid ;
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

## Phase 4 — Dimanche et début de semaine : les fondations du programme

1. **Charte de rigueur** (§ 7.1) : `donnees/programme.json` (fiches notions : enfant, grands, vrai terminal,
   limite de l'image, idées fausses, sources), `pc/outils/verifier_programme.py`, rejeu des sorties réelles en CI,
   d'abord sur le **tronc commun**.
2. **Ponts des Nombres** (§ 7.10) : graphe des prérequis, `maths <question>` (même moteur que le lexique), « je ne
   connais pas » jamais bloquant ; premières fiches (division, modulo, puissances, binaire).
3. **Récompenses par monde** (§ 7.6) : rencontres et variantes rares débloquées par les exploits.

## Phase 5 — Les mondes, un par un (ordre du § 7.14)

Port (avec le réseau simulé où les biomes sont des machines) → Citadelle et ses boîtes → Crypte des Codes →
Salle des Machines (avec VM réelles) → Tour des Ondes → Guilde des Bâtisseurs Libres → Observatoire de l'IA →
Données (SQL) / Forge (site web, multimédia) / Contrôle (Linux de A à Z) / Temps / Atelier (embarqué) → Sommet ;
mode classe en parallèle. Pour chaque monde : fiches → étapes PC et Android → tests → simulations → illustrations
(planche à valider par le propriétaire) → APK d'essai.

## En continu (chaque jour, peu coûteux)

- Variantes : Abyssaux (en cours, 436 / 682 au 28 octobre), puis Célestes, Constructs, Aberrations ; planche par
  famille finie ; scripts `scratchpad/capt.sh`, `com.sh`, nettoyages `violet.py`, `trou.py`, `brume.py [v|b]`,
  `aile.py`, `ailebleue.py`, `fumee.py`, `frange.py` (à recopier dans `donnees/bestiaire2/outils/` pour ne pas les
  perdre).
- Illustrations des mondes (entrée de chaque monde, gardiens, animations pédagogiques), en commençant par la Crypte
  sous la Racine et le Port.

## Phase finale — L'œuf physique (projet open source)

Schéma de principe d'abord (à valider avec le propriétaire) : ESP32 + petit écran couleur, coque STL « clic pour
ouvrir » d'après les 9 œufs, boutons, batterie ; usages et fonction des boutons à définir ensemble ; transfert d'un
terminagotchi ; option LoRa pour que les œufs se parlent en maillage (§ 7.11).

## Ce qui attend une décision ou une action du propriétaire

- Tester l'APK d'essai de la phase 1 et donner ses retours.
- Régler `SECRET_GRAINES` (phase 2).
- Le nom de domaine `terminagotchi.com` (pas encore branché sur le site).
- Valider les planches d'illustrations au fil de l'eau.
- Trouver, s'il le peut, des enseignants relecteurs et des classes pilotes.
