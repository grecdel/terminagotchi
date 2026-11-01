# Simulation — le monde des biomes et les effets des commandes (1er novembre)

Trois enfants simulés tapent de vraies commandes dans l'espace de travail PC (`tg espace`, onglet Monde), sur un vrai
terrain temporaire. Script : `/home/claude/outils/monde/sim.py` (résultats bruts : `sim.json`). Pour chaque commande :
les effets joués dans le monde (calculés par la photo du terrain avant/après) et la phrase de la créature.

## Léa, 7 ans (tape lentement, se trompe)
`mkdir feu`, `mkdir feu/parcele_1` (faute), `ls`, `mkdir feu/parcelle_1`, `cd feu`, `cd parcelle_1`,
`touch braise.pierre`, `toutch rose.fleur` (faute), `rm braise.pierre`, `cd ..`, `pwd`.
- Chaque commande réussie se voit (dossier qui tombe, point jaune de cd, objet posé puis confettis, chemin de pwd).
- `parcele_1` mal écrit : c'est un vrai dossier (pas une parcelle), la créature dit seulement « un nouveau lieu » —
  correct : l'effet ne ment pas.
- **Problème trouvé (important, corrigé)** : `toutch` donnait « ce chemin n'existe pas » (le message « command not
  found » contient « not found »). Maintenant : « Je ne connais pas ce mot-là. Vérifie l'orthographe de la commande. »

## Malik, 12 ans (enchaîne vite, jokers)
`mkdir -p eau/parcelle_1 eau/parcelle_2`, `cd plante/parcelle_1` (depuis le mauvais dossier), `touch a.fleur … h.fleur`,
`rm *.fleur`, `echo bonjour > mot.txt`, `echo encore >> mot.txt`, `cat mot.txt`, `cp …`, `find ../.. -name '*.txt'`.
- 8 fleurs d'un coup : un seul effet groupé « + 8 », puis `rm *.fleur` : les jokers s'allument puis « − 8 ».
- `>` puis `>>` : deux explications différentes ; `cat` déroule le vrai texte du fichier.
- **Problème trouvé (important, corrigé)** : un `cd` raté dans le mini-terminal (message traduit « dossier
  introuvable ») donnait « Rien n'a changé ». Maintenant : « ? » à l'endroit visé et l'explication du chemin.

## Inès, 15 ans (droits, tuyaux, rafales)
`mkdir parcelle_2`, `chmod a-w parcelle_2`, `touch parcelle_2/x.arbre`, `chmod u+w …`, une boucle qui crée 30 fichiers,
`ls parcelle_2 | wc -l`, `rm -r parcelle_2`, `rmdir parcelle_1`, `monde effets essentiels`, `ps`.
- La boucle de 30 fichiers : un seul effet « + 30 » (360 ms de commande, aucune saccade du monde).
- Le tuyau : le petit laboratoire `ls | wc` au-dessus de la région.
- Réglage « essentiels » : `ps` ne montre plus les lucioles (★★), comme prévu.
- La simulation tourne en administrateur (conteneur) : `chmod a-w` n'empêche donc pas `touch`. Le refus « cadenas »
  est vérifié pour de vrai par `pc/outils/test_effets.py` (lancé sans les droits d'administrateur par `tout.sh`).

## Bilan
- Explications : chaque sorte d'effet est dite au plus 3 fois (compteurs dans la partie), jamais deux fois de suite
  pour la même commande.
- Performance mesurée : une image du monde en 14 à 18 ms en moyenne (au plus ~30 ms) pour un grand monde de
  9 régions × 8 parcelles (1 368 hexagones), sous les 50 ms d'une horloge à 20 images par seconde.
- Problèmes critiques : aucun. Problèmes importants : 2, corrigés (ci-dessus). Mineur restant : les captures JVM du
  téléphone n'ont pas de police emoji (cases vides sur les étiquettes) ; un vrai téléphone dessine les emojis.
