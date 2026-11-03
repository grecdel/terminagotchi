# Contribuer à Terminagotchi

Merci de vouloir aider ! Terminagotchi est un jeu **libre et gratuit** pour apprendre le terminal dès 7 ans. On peut
aider sans savoir programmer : jouer et raconter ce qui coince, corriger une traduction, relire une leçon, proposer
une idée, dessiner.

## 1. Les façons d'aider

| Tu veux… | Ce que tu fais |
|---|---|
| Signaler un problème | Ouvre une *Issue* sur GitHub (`grecdel/terminagotchi`) : ce que tu as tapé, ce que tu attendais, ce qui s'est passé, PC ou téléphone, et la langue du jeu. Une capture d'écran aide beaucoup. |
| Proposer une idée | Ouvre une *Issue* qui commence par « Idée : ». Explique ce que verrait l'enfant. |
| Faire jouer un enfant et raconter | Note où il hésite, ce qui le fait rire, ce qui l'ennuie. Pas de prénom, pas de photo d'enfant, pas d'âge exact : « un enfant de 8-9 ans » suffit. |
| Corriger une traduction | Les textes sont dans `pc/tg/langues/xx.json` (une langue par fichier, 14 langues). Le français est la référence. |
| Relire une leçon (enseignant, spécialiste) | Dis-nous si c'est juste, clair et dans le bon ordre. |
| Écrire du code | Lis la partie 4 avant de commencer. |
| Dessiner | Lis la partie 5 avant de commencer. |
| Faire colorier en classe | Les coloriages, les stickers et le poster sont gratuits sur [terminagotchi.com/imprimer](https://terminagotchi.com/imprimer) (fichiers dans `site/public/imprimer/`). |

## 2. Les règles du jeu (on ne les change pas)

Ces règles protègent les enfants qui jouent. Une contribution qui ne les respecte pas sera refusée, même si elle
est très bien faite.

- **Rien à acheter.** Pas d'achat dans le jeu, pas de monnaie payante, pas de « version premium ».
- **Pas de publicité**, pas de lien vers une boutique, pas d'appel aux dons dans le jeu.
- **Pas de crypto, pas de NFT.**
- **Pas d'objets cosmétiques ni d'accessoires** sur les créatures (chapeaux, habits, skins…). Une créature change
  en grandissant et selon l'endroit où elle vit, c'est tout.
- **Jamais punitif.** Pas de série à perdre, pas de créature qui meurt ou qui boude parce qu'on n'a pas joué, pas
  de message qui culpabilise, pas de chrono stressant imposé.
- **Pas de texte libre entre enfants.** Les joueurs ne peuvent pas s'écrire de messages.
- **Aucune donnée personnelle** envoyée ou enregistrée. Le jeu marche hors ligne ; le site est facultatif.
- **Le jeu ne touche qu'à son terrain** (`terrain_terminagotchi/`). Jamais de `sudo`, rien qui modifie le vrai
  système de l'enfant.
- **La mascotte du site n'apparaît jamais dans le jeu.**
- **Rien de tiers embarqué** : pas de bibliothèque ou de programme d'ailleurs ajouté au jeu, rien téléchargé par le
  jeu. Les sons sont fabriqués par notre propre code (synthèse), pas pris dans des banques de sons.
- **PC et téléphone restent égaux** : ce qui existe sur l'un existe sur l'autre (et sous Windows aussi).
- **Les vraies commandes restent vraies** : ce que l'enfant apprend doit marcher dans un vrai terminal.

## 3. D'abord une maquette

Tout ce qui **se voit ou s'entend** dans le jeu (un écran, un dessin, une animation, un son, un nouveau monde) se
montre **avant** d'être codé : une image qui montre le rendu final sur PC et sur téléphone, jointe à une *Issue*.
On code seulement quand la maquette est acceptée. Ça évite de travailler pour rien.

## 4. Pour le code

1. Récupère le code : `git clone https://github.com/grecdel/terminagotchi`, puis travaille sur une branche à toi.
2. Lance le jeu sur PC : `python3 pc` dans le dossier.
3. Où sont les choses :
   - `pc/tg/` : le jeu sur PC (Python) ; `pc/tg/vsh/` : le terminal intégré pour Windows ;
   - `app/` : le jeu sur Android (Kotlin) ;
   - `site/` : le site terminagotchi.com ;
   - `donnees/` : les créatures, les illustrations, les leçons (`programme.json`) ;
   - `docs/` : le programme complet des leçons et les maquettes.
4. Lance les tests avant d'envoyer : les `pc/outils/test_*.py`, `pc/outils/verifier_langues.py` et, si tu touches
   au site, `node site/test/test.mjs`. Ce que tu changes en Python doit aussi être changé en Kotlin (et
   inversement) ; les tests comparent les deux.
5. Ajoute les textes **en français d'abord**, dans les 14 fichiers de langues (une traduction approximative vaut
   mieux qu'une clé manquante ; signale-la pour relecture).
6. Ouvre une *Pull Request* : ce qui change pour l'enfant (en une ou deux phrases), comment tu as testé, captures
   PC et téléphone si quelque chose se voit.

## 5. Pour les dessins

- Style : **pixel art net**, univers numérique (racines à circuits verts, pixels qui se défont, lignes de données,
  petite pluie de pixels verts, zones calmes). Comme les créatures et l'intro du jeu.
- Créatures et objets sur fond uni, détourés ; scènes en 16:9.
- Montre d'abord une **planche** (plusieurs propositions côte à côte) dans une *Issue*.

## 6. Licences : ce que devient ta contribution

En envoyant une contribution, tu acceptes qu'elle soit partagée sous les mêmes licences que le reste du jeu :

- **Images, dessins, textes de l'histoire, sons** : **Creative Commons BY-NC-SA 4.0** (CC BY-NC-SA 4.0). Tout le monde peut les
  partager et les modifier, en citant « les contributeurs de Terminagotchi », **sans usage commercial**, et sous la
  même licence. Détails : [`LICENSE-images.md`](LICENSE-images.md).
- **Code** (Python, Kotlin, JavaScript…) : **GNU GPL 3 ou plus récente**. Détails : [`LICENSE`](LICENSE).
- La **mascotte du site** n'est pas libre (tous droits réservés) : ne la réutilise pas.

N'envoie que ce que tu as fait toi-même (ou qui a une licence compatible, en le disant clairement).

## 7. Entre nous

On reste gentil et patient, surtout avec les débutants : ici, beaucoup apprennent. Les questions « bêtes »
n'existent pas. On critique une idée, jamais une personne.

Merci !
