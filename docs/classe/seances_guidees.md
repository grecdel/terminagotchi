---
title: "Terminagotchi en classe — séances guidées d'une heure"
subtitle: "BROUILLON du 3 novembre 2026 · à relire par des enseignants · complète les fiches enseignant"
lang: fr
---

# À lire d'abord

> **Brouillon.** Ce document n'est pas encore validé : ni par le propriétaire du projet, ni par des enseignants,
> ni en classe pilote. Les commandes `tg classe seance` et `tg classe tableau` citées ici sont **proposées**
> (maquettes du 3 novembre) et **n'existent pas encore** dans le jeu. Tout le reste (codes de séance, bilan,
> `tg espace classe`) existe déjà : voir `fiches_enseignant.md`.

Les **fiches enseignant** disent *quoi* enseigner (objectif, commandes, questions, trace écrite). Ces **séances
guidées** disent *comment mener l'heure*, minute par minute : quoi dire, quoi projeter, où les élèves bloquent,
que faire avec ceux qui ont fini. Une séance = une heure de cours (55 min de travail effectif).

## Les règles qui valent pour toutes les séances

- **Jamais de course.** Le jeu ne chronomètre pas les élèves (code avec `S` : sans chrono). Les durées ci-dessous
  sont pour l'enseignant seulement.
- **Binômes** dès que possible : un au clavier, un qui lit la consigne à voix haute ; on échange à chaque leçon.
- **Pas de classement.** Le bilan ne classe personne ; on ne compare pas les niveaux des créatures.
- **Aucune donnée.** Pseudonymes sur papier en classe ; rien n'est envoyé (voir les fiches, « Données
  personnelles »).
- **Le blocage est normal.** En mode guidé la commande est montrée ; en mode sans aide, trois essais ratés la font
  apparaître ; l'enseignant relance par une question
  plutôt que par la réponse (« Tu cherches un fichier ou un mot dans un fichier ? »).

## Le squelette d'une heure

| Temps | Phase | Ce que fait l'enseignant | Ce qui est projeté |
|---|---|---|---|
| 0-5 | Lancement | fait taper `tg`, puis le code de séance ; lit le but à voix haute | le but du chapitre en grand |
| 5-35 | Jeu en autonomie | circule, relance par des questions, note les blocages fréquents | la commande du moment (ou rien, en mode sans aide) |
| 35-47 | Mise en commun | pose 2 ou 3 questions pour l'oral ; un binôme montre sa solution au tableau | la question pour l'oral |
| 47-52 | Trace écrite | dicte ou projette la trace ; les élèves la recopient | la trace écrite |
| 52-55 | Bilan | `tg classe bilan fichier`, puis `tg classe fin` | rien |

Proposé : `tg classe seance <n>` affiche ce squelette rempli pour la séance n dans le terminal de l'enseignant ;
la touche Entrée passe à la phase suivante, et `tg classe tableau` (le poste branché au vidéoprojecteur) suit les
phases tout seul. En attendant, `tg espace classe` sert de grand écran.

## Préparer la salle (une fois)

- Un poste par binôme, le jeu copié (`terminagotchi.pyz`) ; Python 3 suffit, rien à installer.
- Lancer le jeu une fois sur chaque poste **avant** la première séance : l'éclosion de l'œuf prend 5 à 10 minutes ;
  sinon, la prévoir dans la séance 1 (c'est le cas ci-dessous).
- Vidéoprojecteur sur le poste de l'enseignant.
- Une feuille « pseudonymes ↔ élèves » gardée par l'enseignant.

\newpage

# Séance 1 — Où suis-je ? (fiche 1)

**Objectifs.** Savoir dire où l'on est (`pwd`), voir ce qu'il y a (`ls`), se déplacer (`cd`), revenir chez soi
(`cd ~`). **Code** : `01-GS-B` (guidée).

| Temps | Déroulé |
|---|---|
| 0-5 | « Aujourd'hui, vous allez faire éclore une créature… en parlant à l'ordinateur. » Faire taper `tg` puis `tg classe code 01-GS-B <pseudo>`. |
| 5-15 | Éclosion de l'œuf : les élèves suivent la consigne du jeu (`pwd`, `ls`, `echo`). **Piège** : l'espace oublié (`cd..` au lieu de `cd ..`) ; montrer au tableau que l'espace sépare la commande de ce qu'on lui donne. |
| 15-30 | Leçons « Où suis-je ? » et « Le vieux chemin ». **Piège** : les accents et majuscules des noms de dossiers ; la touche Tab complète le nom. |
| 30-35 | « Voyage jusqu'à la Racine » pour ceux qui ont fini ; les autres terminent. |
| 35-47 | Mise en commun : « Que répond l'ordinateur à `pwd` ? Pourquoi le chemin commence-t-il par `/` ? » Un binôme dessine au tableau le chemin parcouru. |
| 47-52 | Trace écrite de la fiche 1. |
| 52-55 | Bilan, fin de séance. |

**Ceux qui ont fini.** `ls -a` dans leur dossier personnel : « Qu'est-ce que ces fichiers qui commencent par un
point ? » (réponse en séance 2).
**Ceux qui bloquent.** L'activité « L'arbre de la classe » (sans ordinateur) en petit groupe, avec l'enseignant.

\newpage

# Séance 2 — Le nid (fiche 2)

**Objectifs.** Créer un dossier et un fichier, écrire et lire un fichier, voir les fichiers cachés.
**Code** : `02-GS-D`.

| Temps | Déroulé |
|---|---|
| 0-5 | Rappel oral : « Comment savoir où je suis ? Comment revenir chez moi ? » Lancer le code. |
| 5-20 | « Construire mon nid », « Un lieu en trop ». **Piège** : `rm` supprime sans corbeille ; le jeu ne touche que le terrain de jeu, mais le dire dès maintenant. |
| 20-35 | « Le garde-manger », « Les passages secrets ». **Piège** : `>` remplace le contenu ; faire constater en tapant deux fois `echo … >` puis `cat`. |
| 35-47 | Mise en commun : « Que se passe-t-il si on utilise `>` deux fois ? » ; « Comment voit-on un fichier caché ? » |
| 47-52 | Trace écrite de la fiche 2. |
| 52-55 | Bilan, fin. |

**Ceux qui ont fini.** `echo … >>` (ajouter au lieu de remplacer) : faire deviner la différence.

\newpage

# Séance 5 — Chercher (fiche 5)

**Objectifs.** Trouver un fichier par son nom (`find`), chercher un mot dans un texte (`grep`), enchaîner deux
commandes avec le tuyau `|`. **Code** : `05-GS-K` (guidée) ou `05-AGS-Q` (sans aide, pour une classe à l'aise).

| Temps | Déroulé |
|---|---|
| 0-5 | Lancement. Au tableau : « Où peut bien être rangé le livre ? » |
| 5-17 | « Le livre perdu » : `find . -name "*livre*"`. **Piège** : oublier les guillemets autour de `*livre*`. |
| 17-35 | « La loupe du détective » : `grep`, `head`, `wc -l`, puis `cat livre.txt \| grep Abyssor`. **Piège** : on sort de `less` avec la touche `q` (l'écrire au tableau avant de commencer). |
| 35-47 | Mise en commun : « Quelle différence entre `find` et `grep` ? » ; jouer « la chaîne de traitement » (fiche 5) avec 3 élèves debout. |
| 47-52 | Trace écrite de la fiche 5. |
| 52-55 | Bilan, fin. |

**Si un élève bloque.** « Cherches-tu un FICHIER (`find`) ou un MOT dans un fichier (`grep`) ? »
**Ceux qui ont fini.** `grep -rn Abyssor . | wc -l` : combien de fois le nom apparaît-il dans toute la
bibliothèque ?

\newpage

# Séance 10 — Le grand défi (fiche 10)

**Objectifs.** Réinvestir le tronc commun sans que les commandes soient données. **Code** : `10-AGS-E` (sans aide,
conseillé).

| Temps | Déroulé |
|---|---|
| 0-5 | Présenter le défi au tableau : trois épreuves, en binômes ; « la réponse n'est pas écrite, c'est à vous de choisir l'outil ». |
| 5-40 | « Le message à l'envers », « Les morceaux du cœur », « Abyssor, le gardien ». L'enseignant ne donne **aucune commande** ; il renvoie vers la trace écrite des séances précédentes (« Quelle fiche parle de chercher ? »). |
| 40-50 | Mise en commun : chaque binôme explique **une** commande qu'il a utilisée et pourquoi. |
| 50-55 | Bilan : c'est la séance où les « commandes trouvées seul » (cran C) disent le plus ce qui est acquis. |

\newpage

# Les autres séances

Les séances 3, 4, 6, 7, 8 et 9 suivent le squelette d'une heure avec le déroulé de leur fiche (les temps de la
fiche donnent déjà le découpage). Points d'attention propres à chacune :

| Séance | Piège principal | Pour ceux qui ont fini |
|---|---|---|
| 3 · Ranger | `mv` sert à déplacer **et** à renommer | `cp -r` d'un dossier entier, puis `ls -R` pour vérifier |
| 4 · Les droits | après `chmod 444`, l'écriture est refusée : c'est voulu | lire `ls -l` et traduire `rw-r--r--` en français |
| 6 · La place | confusion mémoire vive / disque | `du -sh *` pour trouver ce qui pèse le plus |
| 7 · Les programmes | `kill` arrête, il ne « tue » rien | lancer deux `sleep … &` et n'en arrêter qu'un |
| 8 · Scripts et git | `chmod +x` oublié avant `./script.sh` | une deuxième recette, puis `git diff` entre les deux |
| 9 · Le réseau | le filtrage de l'établissement bloque parfois `ping` | préférer le monde 11 (réseau simulé) si c'est bloqué |

# À vérifier avant de publier

- Relecture par au moins deux enseignants (cycle 3 et lycée) ; essai en classe pilote.
- Les temps : à ajuster après les premières classes.
- Les commandes `tg classe seance` et `tg classe tableau` : à retirer de ce texte si elles ne sont pas codées.
