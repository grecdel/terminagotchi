# Simulation : trois enfants visitent la Salle des Données (huitième monde du Carrefour)

Date : 1er novembre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_donnees.py` (PC, rejouable à chaque
test et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Donnees.kt`.

## 0. Comment on a joué

**PC.** Comme `sim_observatoire.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Salle est ouverte d'avance
comme dans l'arbre du Carrefour (niveaux 0 à 4 du tronc commun).

**Sur SA collection.** Chaque enfant a sa propre collection de créatures ; le jeu l'écrit en tableau avec
`tg collection --csv > collection.csv`, puis vérifie chaque réponse en recalculant sur **ce même fichier**.
- Léa a une collection **minuscule** (2 bestioles) : le jeu la complète avec 8 bestioles d'exemple, marquées
  `exemple = 1` dans le tableau, et le dit à l'écran (« 2 bestioles à toi + 8 bestioles d'EXEMPLE »).
- Inès en a 7, Hugo 40 (dont des doublons et des shiny).

**Hors ligne, rien d'envoyé.** Les proxys pointent vers 127.0.0.1:9 ; `sudo`, `curl` et `wget` sont des doublures qui
refusent et notent qu'on les a appelées. `cut`, `sort`, `uniq`, `tr`, `paste`, `sed`, `awk`, `grep`, `xargs`, `tee` sont
les vrais. Le tableau et la base restent dans le terrain ; le CSV ne contient ni le nom du joueur, ni d'identifiant, ni
de date précise (seulement le jour de capture).

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** :
- le nombre de bestioles, dans `wc -l` (moins la ligne des titres) ; les shiny, dans `grep -c` ;
- le nom mal écrit (et le bon), dans `donnees copiste` ;
- la moyenne, dans la sortie de l'awk ; la médiane, dans `cat -n attaques.txt` ; l'étendue, dans `sed -n '1p;$p'` ;
- le type préféré, dans la première ligne du `GROUP BY`.

**Android.** `tests/jvm/Donnees.kt` refait la traversée dn0 → dn6 avec les commandes du téléphone, sur une vraie
collection de 7 bestioles : 29 vérifications.
- Le téléphone a son petit `awk` (DonneesAwk.kt) et son petit `sqlite3` (DonneesSql.kt, sur le SQLite d'Android) ;
  `collection --csv` remplace `tg collection --csv`.
- Python et Kotlin donnent les mêmes résultats sur les vecteurs communs (`donnees/donnees/vecteurs.json`) : le tableau,
  les statistiques, le carnet du soigneur, la base, la mise en forme des réponses SQL, les instruments de la vue
  déployée. Les sorties du petit awk sont comparées à celles du **vrai** awk (mawk ici ; gawk et busybox aussi en CI
  quand ils sont installés).
- `cut`, `sort`, `uniq`, `sed`, `xargs`, `tee`… sont ceux du téléphone (toybox) : `pc/outils/test_donnees_outils.py`
  lance chaque ligne de la Salle avec GNU, toybox et busybox sur le même tableau, et compare sorties et fichiers. En CI,
  toybox est compilé depuis ses sources (version 0.8.11) ; ici, ni toybox ni busybox ne sont installés (le test l'a dit).

**Limites honnêtes.**
- Le rejeu bash complet de l'histoire ne tourne qu'en CI (la machine de test n'a pas `ping` et tourne en root). La
  partie Salle des Données du rejeu a été jouée ici (`TG_REJEU_MONDE=donnees`), et elle est verte.
- L'outil `sqlite3` n'est pas installé sur la machine de test : ici, les requêtes passent par le repli
  `tg donnees sqlite3 …` (le moteur SQLite de Python, le même moteur). La comparaison avec le **vrai** outil `sqlite3`
  (espacement de `.tables`, écriture des nombres) est faite en CI, où il est installé.
- Sur le téléphone, le moteur SQLite d'Android n'est pas lancé dans les tests JVM (un moteur Python le remplace) ; il le
  sera sur le vrai téléphone (APK d'essai).
- Les textes des 13 autres langues sont des traductions de Claude, non relues par des locuteurs.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « statistique juste » |
|---|---|---|---|---|
| Léa, 7 ans, se trompe d'abord, 2 bestioles | Voir ses fautes ci-dessous, puis lit et corrige | 68 | oui, dn0 → dn6 | oui |
| Inès, 12 ans, recopie, 7 bestioles | Recopie la commande verte (« ? » compris), puis lit l'écran | 60 | oui | oui |
| Hugo, 15 ans, ses variantes, 40 bestioles | Ses propres variantes de commande, toutes justes | 51 | oui | oui, 17 variantes justes acceptées sur 17 |

Les fautes de Léa :
- `Ls`, `Cat`, `Head` avec une majuscule ;
- `tg collection > collection.csv` (sans `--csv`), puis `tg collection --csv` (sans `>`) ;
- compter la ligne des titres (`donnees combien 11` au lieu de 10) ;
- `cut -f2` sans `-d,` ; `sed 's/…/…/'` sans `g` ; `awk` sans `-F,` ;
- donner la somme au lieu de la moyenne ; la valeur du milieu de la liste **non triée** pour la médiane ; le maximum
  pour l'étendue ;
- `donnees bilan` avant d'avoir fini le rapport ;
- une requête SQL sans guillemets ; un type au hasard (« dragon ») pour son type préféré.

Les variantes de Hugo :
- `head -n 3`, `wc -l < collection.csv`, `sort -rn`, `sort -nr | head -n 3` ;
- `tr , '\n'`, `cut -f2 -d,`, `grep -cx 1`, `grep -cE ',(eau|glace),'` ;
- `awk -F','` (avec guillemets) pour les trois calculs ;
- `head -1 attaques.txt; tail -1 attaques.txt` au lieu de `sed -n '1p;$p'` ;
- `sort -t, -k4 -rn … | head -n 3 | tee rapport.txt` ;
- SQL en minuscules (`select … order by …`), `sqlite3 -header`.

Ce qui vaut pour les trois enfants :
- aucune étape n'a été validée par une commande qui a échoué ;
- rien n'a été écrit hors du terrain et de `~/.terminagotchi` ;
- le CSV ne contient aucune donnée personnelle (ni le nom du joueur, ni les identifiants des créatures) ;
- aucun téléchargement tenté, aucun `sudo` ;
- la base `collection.db` est ouverte **en lecture seule** pour les requêtes (`DELETE` est refusé, sur PC comme sur le
  téléphone).

### Léa (7 ans, 2 bestioles)

| Question | Constat |
|---|---|
| Une collection minuscule bloque-t-elle ? | Non : le jeu ajoute 8 bestioles d'exemple, clairement marquées (colonne `exemple`, et le message à l'écran). Les statistiques se calculent sur les 10 lignes. |
| Comprend-elle ? | Oui : « une ligne par bestiole, plus la ligne des titres » ; le moulin qui trie avant de compter ; « regarde la ligne où le nom est DEUX fois : sans g, seul le premier est corrigé ! ». |
| Ses fautes | Chacune reçoit une phrase qui explique quoi changer : « Ajoute --csv », « ajoute > et le nom du fichier », « enlève la ligne des titres », « Il manque -d, », « Il manque -F, », « Il manque le g », « Mets la requête SQL entre guillemets », « la somme divisée par le nombre de bestioles »… |
| Le bilan trop tôt | La commande répond « Le rapport n'est pas encore complet : il faut le podium (3 lignes) puis une ligne « moyenne X ». » |

### Inès (12 ans, 7 bestioles)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout, sauf aux trous `?` (combien, shiny, le nom à corriger, moyenne, médiane, étendue, type préféré). C'est voulu : le jeu dit « Remplace le ? par ta réponse » et où la lire. |
| L'exploit | `donnees moyenne X` juste : `donnees.statistique` est gagné, et les variantes réservées deviennent des rencontres favorisées. Ce sont des variantes **existantes** des types Eau et Glace : `nautiloque:corail`, `krillou:aurore`, `ondulame:glace` (ni gardiens, ni déjà réservées ailleurs). |
| Les Ponts des Nombres | Proposés à 8 étapes, jamais bloquants : 4 notions nouvelles (moyenne, médiane, étendue, pourcentages, aussi dans `maths` sur le téléphone) et 3 qui existaient déjà (comptage, effectifs, fréquences). |

### Hugo (15 ans, 40 bestioles)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 17 sur 17 acceptées. |
| SQL en minuscules, `-header` | Acceptés : le jeu vérifie le sens de la requête, pas la casse. |
| `head -1 …; tail -1 …` | Accepté à la place de `sed -n '1p;$p'`. |

## 2. Problèmes trouvés, classés

### Critiques — aucun ouvert

| # | Problème | État |
|---|---|---|
| DN1 | `cut -f2 collection.csv` (sans `-d,`) et `awk '{…}' collection.csv` (sans `-F,`) étaient acceptés comme justes, alors qu'ils donnent un résultat **faux** (cut coupe aux tabulations, awk aux espaces). L'enfant aurait appris une commande fausse. | Les étapes exigent maintenant `-d,` et `-F,` (PC et Android) ; le contenu de `noms.txt` et `types.txt` est vérifié ; un indice dédié (« Il manque -d, », « Il manque -F, ») explique pourquoi. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| DN2 | Après une mauvaise médiane, Léa tape `cat -n attaques.txt` (ce que l'indice lui conseille), et le jeu lui redit « Pas tout à fait » comme si c'était une nouvelle mauvaise réponse. | L'indice « mauvaise réponse » ne vient que juste après une réponse (`donnees mediane …`), pas après une commande de lecture (PC et Android). |
| DN3 | Un texte contenait `{action}` en clair (vu par `verifier_langues`) : il aurait été pris pour un champ à remplir. | Remplacé par `{…}` dans les 14 langues. |

### Mineurs (notés)

| # | Constat |
|---|---|
| DN4 | « Pas grave ! Tape : donnees moyenne ? » remontre la commande avec son `?` ; l'indice juste au-dessus dit de remplacer le `?`. C'est le fonctionnement commun à tous les mondes. |
| DN5 | Le bilan trop tôt ne reçoit que la réponse de la commande (✋ … pas encore complet), pas de phrase en plus dans le journal du jeu. La phrase suffit. |
| DN6 | Avec une collection minuscule, la statistique de l'exploit est calculée sur le tableau complété (les bestioles d'exemple comptent). C'est dit à l'écran, mais l'exploit se gagne donc en partie sur des bestioles qui ne sont pas les siennes. |
| DN7 | Les émojis (📊, 🏅, ⚗…) ne s'affichent pas dans la police des captures (PC et maquettes du téléphone) ; ils s'affichent dans un vrai terminal et sur le téléphone. |
| DN8 | Dans les maquettes du téléphone, le dessin de l'instrument (vue déployée) est coupé en bas, comme la lunette de l'Observatoire : la bande est plus basse que la place demandée. Le dessin s'adapte maintenant quand il a peu de place (titre et « de → vers » sur une seule ligne) ; à vérifier sur un vrai téléphone. |

## 3. Ce qui marche bien

- **Ses propres données.** Les nombres viennent de SA collection : la moyenne d'Inès n'est pas celle de Hugo. Le jeu
  recalcule chaque réponse sur le même fichier, au moment de la vérifier.
- **Deux chemins, un résultat.** Le podium avec `sort | head` puis avec `ORDER BY … LIMIT 3` ; la moyenne avec `awk`
  puis avec `AVG` ; `uniq -c` puis `GROUP BY` : l'enfant voit que les deux donnent la même chose, et peut vérifier.
- **Des erreurs d'analyste expliquées.** Compter la ligne des titres, trier avant `uniq -c`, oublier le séparateur, la
  médiane sur une liste non triée : chacune a sa phrase.
- **Rien ne sort du terrain.** Le tableau et la base restent dans `terrain_terminagotchi/donnees` ; rien n'est envoyé
  au site.
- **Le téléphone aussi.** Le petit awk et le petit sqlite3 donnent les mêmes sorties que les vrais outils sur les
  vecteurs communs.

## 4. Ce qui reste

- Les illustrations : prompts dans `outils/donnees/prompts_illustrations.md` (B7, vignette, C1, C3, E18, E19), aucune
  image générée. En attendant, le laboratoire, le podium et les instruments sont dessinés : en caractères sur PC, avec
  `DonneesDessin` sur le téléphone.
- Une relecture des traductions par des locuteurs.
- DN6 : décider si l'exploit doit demander au moins 3 bestioles à soi.
- Vérifier sur un vrai téléphone le petit sqlite3 (moteur SQLite d'Android) et le dessin de l'instrument (DN8).

## 5. Rejouer

```
python3 pc/outils/sim_donnees.py                # les trois
python3 pc/outils/sim_donnees.py lea            # une seule
python3 pc/outils/test_donnees.py               # la Salle des Données sur PC (67 vérifications)
python3 pc/outils/vecteurs_donnees.py --verifier
python3 pc/outils/test_donnees_outils.py         # toybox / busybox contre GNU (s'ils sont installés)
python3 pc/outils/capture_donnees.py <dossier>  # les captures PC
TG_REJEU_MONDE=donnees python3 pc/outils/rejeu_bash.py   # la Salle seule dans le rejeu bash
# Android : tests/jvm/Donnees.kt (29 vérifications), voir outils/tout.sh jvm Donnees
```
