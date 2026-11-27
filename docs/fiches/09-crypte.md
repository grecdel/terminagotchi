# 🗝 Crypte

*La Crypte des Codes : cryptographie, des codes anciens à la blockchain*

| | |
|---|---|
| **Durée** | environ 30 min (4 leçons, 8 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `echo`, `tr`, `base64`, `sha256sum` |
| **Compétences gagnées** | Centurion, Transcripteur, Hacheur, Forgeron de chaînes |

## Objectifs

- **Le code de César** : jules César décalait chaque lettre de 3. Chiffre BONJOUR. (avec `echo`, `tr`)
- **Le colis en base64** : base64 transforme n'importe quoi en lettres simples. Encode un mot. (avec `echo`, `base64`)
- **L'empreinte magique** : a.txt et b.txt ne diffèrent que d'une lettre. Compare leurs empreintes. (avec `sha256sum`)
- **La blockchain à la main** : écris le premier bloc du registre. (avec `echo`, `sha256sum`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Crypte » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Le code de César → compétence « Centurion »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/crypte/message.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Jules César décalait chaque lettre de 3. Chiffre BONJOUR. | `echo BONJOUR \| tr 'A-Z' 'D-ZA-C'` | ERQMRXU : illisible… sauf pour qui connaît la clé (3). |
| 2 | Un message chiffré t'attend dans la crypte. Déchiffre-le ! | `tr 'D-ZA-C' 'A-Z' < monde/crypte/message.txt` | 26 clés possibles seulement : un ordinateur casse César en un clin d'œil. |

### 2. Le colis en base64 → compétence « Transcripteur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/crypte/colis.b64`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Base64 transforme n'importe quoi en lettres simples. Encode un mot. | `echo -n secret \| base64` | c2VjcmV0 : ce n'est PAS un chiffrement, juste un emballage. |
| 2 | Ouvre le colis de la crypte. | `base64 -d monde/crypte/colis.b64` | N'importe qui peut le déballer : base64 sert à transporter, pas à cacher. |

### 3. L'empreinte magique → compétence « Hacheur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/crypte/a.txt`, `~/terrain_terminagotchi/monde/crypte/b.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | a.txt et b.txt ne diffèrent que d'une lettre. Compare leurs empreintes. | `sha256sum monde/crypte/a.txt monde/crypte/b.txt` | Une lettre change, toute l'empreinte change : l'effet avalanche. Et impossible de revenir en arrière. |

### 4. La blockchain à la main → compétence « Forgeron de chaînes »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Écris le premier bloc du registre. | `echo 'bloc 1 : Alice donne 5 pommes à Bob' > monde/crypte/bloc1.txt` | Bloc 1 posé. |
| 2 | Le bloc 2 commence par l'empreinte du bloc 1. | `sha256sum monde/crypte/bloc1.txt > monde/crypte/bloc2.txt` | Le bloc 2 est accroché au bloc 1 par son empreinte. |
| 3 | Ajoute la transaction du bloc 2. | `echo 'bloc 2 : Bob donne 2 pommes à Zoé' >> monde/crypte/bloc2.txt` | Si quelqu'un trafique le bloc 1, son empreinte change et ne correspond plus au bloc 2 : toute la chaîne crie au voleur. C'est ça, une blockchain ! |

## Questions pour vérifier

- Que fait la commande `echo` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `tr` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `base64` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `sha256sum` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
