# Simulation : trois enfants descendent dans la Crypte des Codes (troisième monde du Carrefour)

Date : 31 octobre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_crypte.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Crypte.kt` (§ 4 de ce test).

## 0. Comment on a joué

**PC.** Comme `sim_citadelle.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée (`compagnon.commande_montree`), la sortie de sa commande et ce que le jeu écrit dans son terminal
(`compagnon.annonces`). La Crypte est ouverte d'avance comme dans l'arbre du Carrefour (niveaux 0 à 4 du tronc
commun finis). `GNUPGHOME` est retiré de l'environnement : on vérifie que le **vrai** trousseau (`~/.gnupg`) n'est
jamais créé par le jeu.

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : pour la roue, l'enfant compte les lettres du
grimoire mystère et calcule le décalage depuis « e » ; pour le dé, il calcule avec `echo $(( (5*x+3) % 8 ))` à partir
du dernier tirage montré ; pour le quiz, il répond, lit les ✔ et corrige les autres ; pour le biome tricheur, il lit
les empreintes de `sha256sum copies/*/registre.txt`.

**Android.** `tests/jvm/Crypte.kt` refait la traversée cr0 → cr14 avec les commandes du téléphone (`openssl passwd
-6`, `openssl rand`, `openssl enc`, `gpg` intégré dans `.trousseau`, `crypte mine 3` au lieu de `time sh mineur.sh 3`,
`echo $((5*5*5*5*5*5 % 23))` car le shell du téléphone n'a pas `**`) : 39 vérifications, dont la compatibilité dans
les deux sens avec le **vrai** `gpg` (le téléphone lit une clé, un message chiffré et une signature du vrai gpg, et le
vrai gpg vérifie et déchiffre ce que le téléphone a produit) et `openssl passwd -6` comparé au vrai openssl.

**Limites honnêtes.** `xxd` manque dans le bac à sable de test : une doublure le remplace (`xxd -r -p`), le paquet
`xxd` est installé en CI. La machine de test tourne en root. Le minage à 3 zéros prend 6 à 9 s dans `sh` (le jeu
le dit et s'arrête seul) ; à 4 zéros, seule la table l'affiche (rien n'est lancé).

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Indices reçus | Blocages | Au bout ? |
|---|---|---|---|---|---|
| Léa, 7 ans, tape mal | majuscules (`Ls`, `Cat`, `Grep`), recopie `?` (roue), `gpg --quick-gen-key …` **sans** `--homedir` (vu dans un tuto), chiffre avec la clé `1234`, quiz tout « v », `echo triche > chaine/bloc_1.txt` (un seul `>`), `sudo cp …`, mauvais biome | 82 | 18 | 0 | oui, cr0 → cr14, la légendaire ; **pas** la variante (elle a eu un indice pendant la chaîne : c'est voulu) |
| Inès, 12 ans, recopie | recopie la commande verte, `?` compris, puis lit l'écran ; quiz en trois essais | 70 | 5 | 0 | oui, la variante (chaîne réparée sans indice) et la légendaire |
| Hugo, 15 ans, ses variantes | `printf a \| sha256sum`, `base64 --decode`, `cat … \| xxd -r -p`, `fold -w1 … \| uniq -c`, `sha256sum --check`, `bash dictionnaire.sh`, `xxd parchemin.enc \| head -n 1`, `less`, `od -An -tx1`, `awk '{print $1}'`, `bash mineur.sh 2`, `time bash mineur.sh 3`, `cat chaine/bloc_*.txt`… | 65 | 0 | 0 | oui, la variante et la légendaire, 21 variantes acceptées sur 21 |

Commun aux trois : aucune étape validée par une commande qui a échoué ; aucun `gpg-agent` du terrain ne reste en vie
à la fin ; seules les clés d'exemple (et le `1234` de Léa, refusé) ont été tapées ; rien d'écrit hors du terrain et de
`~/.terminagotchi`.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : « cacher n'est pas chiffrer », la roue, l'empreinte qui change entièrement, le coffre à une clé puis le cadenas ouvert, la chaîne qui casse maillon par maillon. Chaque vraie sortie (`Ym9uam91cgo=`, `FAILED`, `Salted__`, `Good signature`, `BAD signature`, `nonce = 139`) est expliquée en une phrase. |
| `gpg` sans `--homedir` | La créature prévient aussitôt : « gpg sans --homedir .trousseau utilise TON vrai trousseau… » et montre la bonne commande. **Mais** dans un vrai terminal, la clé d'exemple a déjà été créée dans son vrai trousseau (voir CR1). |
| La clé `1234` | Refusée : « Utilise la clé d'EXEMPLE montrée (sphinx-de-givre-exemple), jamais un vrai mot de passe. » |
| `sudo` | « Pas de sudo ici : la Crypte n'en a jamais besoin. » |
| Le quiz | Deux essais faux, puis juste en lisant les ✔ ; aucune pression. |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout sauf aux trous `?` (roue, dé, quiz, tricheur, voulus) : le jeu dit que c'est un trou et ce qu'il faut lire. |
| La variante rare | Elle répare la chaîne en lisant `verifie_chaine.sh` et `archives/` sans indice : `crypte.chaine` est gagné, au bon moment (quand `crypte chaine` montre la chaîne réparée). |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 21 sur 21 acceptées après correction (CR3). |
| Fausses variantes | `bash mineur.sh 1` (au lieu de 2) et `openssl rand -hex 32` (au lieu de 16) **étaient acceptées** avec un bravo qui ne collait pas (« 139 essais », « 32 chiffres ») : corrigé (CR3). |

## 2. Problèmes trouvés, classés

### Critique — documenté, décision du propriétaire demandée

| # | Problème | État |
|---|---|---|
| CR1 | **`gpg` tapé sans `--homedir`** dans un vrai terminal (PC) utilise le vrai trousseau de l'utilisateur : une clé d'**exemple** (`explorateur@crypte.example`, sans phrase de passe) y est alors créée. Le jeu ne peut pas l'empêcher (la commande est lancée par le vrai shell, avant que le jeu la voie). | Le jeu prévient tout de suite, une seule fois (`crypte.surveiller` hors des leçons, l'indice de l'étape pendant), et toutes les commandes montrées ont `--homedir .trousseau`. Sur le **téléphone**, `gpg` est intégré et **refuse** toute commande sans `--homedir` dans le terrain : aucun risque. **Question au propriétaire** : poser, dans le terrain, une petite fonction de shell `gpg` qui refuse sans `--homedir` (comme l'alias `crypte`) ? Non fait sans son accord, car cela modifie le shell de l'utilisateur. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| CR2 | `time sh mineur.sh 3` et les commandes du jeu (`crypte`, `citadelle`, `port`, `deploie`…) faisaient dire au jeu « « time » n'est pas une commande » alors qu'elles avaient marché (défaut ancien, pas propre à la Crypte). | `core.BUILTINS` connaît les mots du shell (`time`, `case`, `until`, `function`, `select`, `command`, `builtin`, `local`, `declare`, `times`) et les commandes du jeu. |
| CR3 | Deux mauvaises variantes de Hugo étaient acceptées (`bash mineur.sh 1`, `openssl rand -hex 32`) ; une juste (`echo $((5*5*5*5*5*5 % 23))`) était refusée sur PC. | Expressions resserrées / élargies (PC et Android). |
| CR4 | `gpg` sans `--homedir` pendant une leçon : deux avertissements à la suite (⚠ de la surveillance puis 💡 de l'indice). | Pendant les leçons de la Crypte, seul l'indice de l'étape parle. |
| CR5 | Le pont « comptage » au milieu de cr11 coupait l'enquête du biome tricheur. | Retiré ; les ponts restent sur l'hexadécimal, le modulo, les puissances, la puissance modulo et les probabilités. |
| CR6 | Sur PC, le texte déchiffré de `crypte roue N` dépassait la largeur du terminal (ligne de 130 caractères). | Replié à 76 colonnes. |
| CR6 bis | En rejouant aussi la simulation de la Citadelle : un processus fictif de la grande vague pouvait être **oublié** (deux fois sur trois sur la machine de test) : juste après son lancement, son nom n'est pas encore visible dans `/proc`, le jeu le rayait de sa liste ; le tableau disait « vague repoussée » et le `sleep` restait 15 min. Défaut ancien de la Citadelle. | `citadelle.lancer_fictifs` garde les processus qu'il vient de lancer sans relire leur nom ; `sim_citadelle.py` 3 fois sur 3 au bout. |
| CR6 ter | Le Port et la Crypte s'ouvrent au même moment (niveaux 0 à 4) : deux annonces de monde à la suite. | Une nouvelle à la fois : la Crypte est annoncée au tour suivant (`histoire.annoncer_monde`, `Histoire.annoncerMonde`), vérifié par `test_port.py` et `tests/jvm/Port.kt`. |
| CR7 | Sur le téléphone, la petite roue de la vue déployée empilait ses 26 lettres illisiblement, et l'exemple « bonjour → … » sortait du cadre. | Roue minuscule : seulement le « a » et sa sœur ; l'exemple passe sur trois lignes à la taille de la place (captures `cry_tel_roue.png`, `cry_tel_deploie_roue.png`). |

### Mineurs (notés)

| # | Constat |
|---|---|
| CR8 | `echo triche > chaine/bloc_1.txt` (un seul `>`, Léa) est accepté comme « modifier un vieux bloc » : le bloc est écrasé au lieu d'être complété, la chaîne casse de la même façon et la réparation (`cp archives/…`) le remet. L'indice « un seul > effacerait » est donné au registre (cr9), où c'est important. |
| CR9 | L'indice d'un trou recopié dit « Tape : crypte roue ? » : la forme commune de tous les indices (la ligne au-dessus explique quoi mettre). |
| CR10 | Le minage à 3 zéros dure 6 à 9 s dans `sh` sur PC (~0,1 s sur le téléphone, calcul intégré) : le texte annonce « plus long », jamais un chiffre de durée. |

## 3. Ce qui marche bien

- **Rien ne sort du terrain** : grimoires, base fictive, coffres, `.trousseau` et `.trousseau_creature` (clés RSA
  d'EXEMPLE, adresses `@crypte.example`, RFC 2606), chaîne, copies des 9 biomes, carnet de bord, tout dans
  `~/terrain_terminagotchi/crypte/`. Les `gpg-agent` du terrain sont arrêtés (`gpgconf --kill`) en quittant les leçons
  gpg et par `crypte stop`. Jamais de `sudo`, aucun accès réseau.
- **Aucune monnaie** : B6 (`crypte vitrine`) explique seulement le fonctionnement (« une transaction = une ligne
  signée », « le solde se recompte en relisant la chaîne », « une chaîne publique n'est pas anonyme »), sans avis ;
  `test_crypte.py` vérifie qu'aucun texte, dans aucune langue, ne parle d'acheter, de vendre ou d'investir.
- Le moment fort : casser soi-même la chaîne, voir le maillon 1 → 2 passer au rouge et la suite devenir « plus
  sûr », puis la réparer ; et à la fin, vérifier **son propre** parcours enchaîné (`sh verifie_chaine.sh carnet_de_bord`).
- Les Ponts des Nombres (hexadécimal, modulo, puissances, puissance modulo, probabilités) sont proposés sans jamais
  bloquer : « Si ce n'est pas le cas, tape … (ou « je ne sais pas ») : rien ne s'arrête ».

## 4. Ce qui reste

- Les illustrations (prompts écrits dans `outils/crypte/prompts_illustrations.md`, aucune image générée) ; en
  attendant, la crypte, la roue, la chaîne, les peintures et la table du mineur sont dessinées (PC en caractères,
  téléphone `CrypteDessin`).
- CR1 : la décision sur un garde-fou `gpg` dans le shell.
- La légendaire « gardienne du registre » : l'exploit `crypte.b6` favorise aujourd'hui les rencontres légendaires et
  réserve `lichonarque:crypte` (espèce et variante existantes) ; à confirmer par le propriétaire.

## 5. Rejouer

```
python3 pc/outils/sim_crypte.py               # les trois (≈ 2 min)
TG_DEBUG=1 python3 pc/outils/sim_crypte.py lea      # une seule, avec chaque ligne tapée et ce qu'elle a lu
python3 pc/outils/test_crypte.py              # la Crypte sur PC (47 vérifications)
# Android : tests/jvm/Crypte.kt (39 vérifications), voir outils/tout.sh jvm Crypte
```
