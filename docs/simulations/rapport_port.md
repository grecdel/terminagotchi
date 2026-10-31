# Simulation : trois enfants traversent le Port (phase 5, premier monde du Carrefour)

Date : 31 octobre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_port.py` (PC, rejouable à chaque test) ;
pour Android, la traversée du téléphone est rejouée par `tests/jvm/Port.kt` (§ 3 de ce test).

## 0. Comment on a joué

**PC.** Chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert (`pc/tg/coquille.py` : les
tâches `&` et `kill %1` marchent), comme `pc/outils/personas.py`. Après chaque ligne, le jeu fait son tour avec le
code de sortie (le crochet d'invite). L'enfant ne lit **que** la commande montrée (`compagnon.commande_montree`) et ce
que le jeu écrit dans son terminal (`compagnon.annonces`). Le Port est ouvert d'avance comme dans l'arbre du
Carrefour (réveil, nid et bibliothèque finis) ; le vrai phare du port tourne sur `127.0.0.1:8042` (HTTP) et
`127.0.0.1:8443` (HTTPS auto-signé).

**Sans tricher.** Les trous des commandes montrées (`port guide racine … feu`, `port sceau ?`) sont remplis en
**lisant l'écran** : la carte affichée par `port carte` (machines et voisins ⇄) pour le détour, la liste de
`port sceau` et sa règle (notaire, nom exact, pas périmé) pour le sceau.

**Android.** `tests/jvm/Port.kt` refait la traversée P0 → P11 avec les commandes du téléphone (`curl` maison,
`serveur 8000`, `nslookup`, `ss`, `port …`), un premier messager perdu par la Roche éteinte, un faux sceau, puis les
bons : 37 vérifications.

**Limites honnêtes.** Dans le bac à sable, `ping`, `ss`, `ip`, `tracepath`, `ssh`, `ssh-keygen` manquent : de petites
doublures répondent à leur place, seulement pour que la partie avance (leurs vraies sorties sont rejouées en CI par
`pc/outils/rejeu_bash.py`, où ces outils sont installés). Une conséquence : `ping -c 3 locahost` « réussit » avec la
doublure ; avec le vrai `ping`, il échoue (nom inconnu) — l'indice reçu est le même.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Indices reçus | Blocages | Au bout ? |
|---|---|---|---|---|---|
| Léa, 7 ans, tape mal | `Ls`, `Cat`, `Hostname`, `locahost`, `curl-I`, `port cartes` ; le chemin direct `port guide racine roche feu` alors que la Roche est éteinte ; un faux sceau d'abord | 64 | 22 (chaque faute) | 0 | oui, P0 → P11, les 2 exploits |
| Inès, 12 ans, recopie | recopie la commande verte, même `port guide racine … feu` et `port sceau ?`, puis lit la carte et la liste | 48 | 6 | 0 | oui, les 2 exploits |
| Hugo, 15 ans, ses variantes | `ip addr`, `ping -c3 127.0.0.1`, `curl --head`, `curl … -o colis.html`, `head -3`, `curl -sv … -o /dev/null`, `ss -ltn \| grep :8042`, `grep localhost /etc/hosts` ; et une lanterne **sans** `--bind` | 50 | 7 | 0 | oui, les 2 exploits |

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui. Le capitaine parle de quais, de phares et de messagers ; la vraie sortie (`HTTP/1.1 200 OK`, `127.0.0.1`) est toujours expliquée en une phrase. |
| Bloque-t-elle ? | Non. Chaque faute reçoit un indice dans son terminal : majuscules (« les commandes s'écrivent en minuscules »), `locahost` (« Presque ! il faut localhost »), `port cartes`. |
| Le messager perdu | Elle tente le chemin qu'elle connaît (`racine roche feu`) : le messager s'arrête à la Roche éteinte, et l'indice l'envoie lire la carte (« chaque phare ne parle qu'à ses voisins ⇄ »). Elle trouve le détour (6 sauts) : exploit. |
| Le faux sceau | Elle choisit d'abord un sceau signé « par lui-même » : « Ce sceau-là est faux. Le vrai : signé par le notaire… » ; le bon ensuite : exploit. |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout sauf aux deux étapes à trous, voulues (P9 : trouver le détour ; P11 : choisir le sceau). Elle recopie `…` et `?` tels quels : le jeu dit maintenant que ce sont des trous à remplir et où trouver la réponse (`port carte`, `port sceau`). |
| P5 (sa lanterne) | Elle tape `curl http://localhost:8000` aussitôt après avoir lancé `python3 -m http.server … &` : la lanterne n'est pas encore allumée (refus, code 7). Le jeu dit maintenant « une lanterne met une seconde à s'allumer, réessaie ». |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 8 acceptées sur 9 (`ip addr`, `ping -c3 127.0.0.1`, `curl --head`, `curl URL -o fichier`, `head -3`, `curl -sv`, `ss -ltn`, `ss -ltn \| grep :8042`). `grep localhost /etc/hosts` est félicitée avec la commande attendue (`cat /etc/hosts`, pour voir tout l'annuaire). |
| La lanterne ouverte | `python3 -m http.server 8000 --directory quai &` (sans `--bind`) écoute sur **tout** le réseau local : l'étape n'est **pas** validée, la créature prévient (« ta lanterne éclaire TOUT le réseau ! Éteins-la (Ctrl+C / kill %1) et rallume-la avec --bind 127.0.0.1 »), puis il la rallume correctement. |

## 2. Problèmes trouvés, classés

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| PO1 | **La lanterne sans `--bind` recevait « Ta commande marche aussi, bravo ! »** (elle n'était pas validée, mais le message félicitait). | `port.indice` : jamais « marche aussi » pour une lanterne ouverte ; `port.surveiller` (à chaque tour, partout) fait parler la créature dès qu'une lanterne est lancée sans `--bind 127.0.0.1` / `-b 127.0.0.1` (clé `port.lanterne.ouverte`, 14 langues). |
| PO2 | **`curl -s http://locahost:8042/eau \| head -n 3` validait l'étape** : `head` rend 0 même quand `curl` échoue (le tuyau cache l'erreur). | L'expression de l'étape (PC et Android) exige `localhost` ou `127.0.0.1` ; indice « Presque ! il faut localhost » quand un nom d'hôte faux est tapé (PC et Android). |
| PO3 | **Les trous recopiés (`port guide racine … feu`, `port sceau ?`), un messager perdu, un faux sceau recevaient « Ta commande marche aussi, bravo ! »**. | `port.indice` / `Port.indice` (PC et Android) : « … et ? sont des trous à remplir », la règle des sceaux quand la liste est relue, « ton messager s'est perdu, regarde la carte », « ce sceau-là est faux » (le carnet de bord dit ce qui s'est passé). |
| PO4 | **Le phare n'était pas encore allumé à la toute première commande de P3** quand l'enfant tape vite (`curl --head` refusé, code 7) : le jeu allume le phare au tour qui *suit* le changement de leçon. | Le phare s'allume dès la leçon d'avant (P2, P5, P10 en plus de P3, P6, P7, P11), PC et Android. |
| PO5 | `curl http://localhost:8000` tapé une demi-seconde après `python3 -m http.server … &` : refusé, et l'indice générique (« la commande a répondu par une erreur ») n'aidait pas. | Indice dédié (`port.indice.lanterne`) : « une lanterne met une seconde à s'allumer, réessaie ; sinon rallume-la ». |

### Mineurs (notés)

| # | Constat |
|---|---|
| PO6 | Les variantes `curl --cacert=fichier` (avec `=`) n'existent pas dans curl (code 2) : refusées à juste titre, mais l'indice reste générique. |
| PO7 | `grep localhost /etc/hosts` est félicitée puis l'étape demande `cat /etc/hosts` : voulu (voir tout l'annuaire), mais Hugo aurait aimé qu'on l'accepte. |
| PO8 | Sur une machine où `tracepath` n'existe pas (macOS, certains Linux minimaux), l'étape P9.1 est passée (`absent_ok`) et `traceroute` est proposé en repli. |

## 3. Ce qui marche bien

- Les vraies commandes réseau marchent **sans jamais sortir de la machine** : seulement `localhost` / `127.0.0.1`
  dans les commandes tapées (vérifié pour les trois profils), aucun serveur de l'enfant ne reste allumé à la fin.
- Le détour par la carte (la Roche éteinte) est le moment fort : Léa et Inès lisent vraiment la carte.
- Les deux exploits (messager guidé sans perte, sceau vérifié) arrivent naturellement, et libèrent les variantes
  réservées du Port.
- La vue déployée montre le messager qui part vers `localhost:8042` et revient (`tg deploie curl …`,
  `tg deploie port messager feu`).

## 4. Ce qui reste

- Les illustrations (prompts écrits, aucune image générée) ; en attendant tout est dessiné ou écrit.
- La carte du réseau dans l'onglet de `tg espace` / l'écran Espace : maquette seulement (à valider).
- P4 (ssh) sur Android : raconté (le téléporteur), pas de vraie clé.

## 5. Rejouer

```
python3 pc/outils/sim_port.py            # les trois (≈ 3 min)
TG_DEBUG=1 python3 pc/outils/sim_port.py lea     # une seule, avec chaque ligne tapée et ce qu'elle a lu
python3 pc/outils/test_port.py           # le Port sur PC (46 vérifications)
# Android : tests/jvm/Port.kt (37 vérifications), voir la CI ou outils/tout.sh jvm Port
```
