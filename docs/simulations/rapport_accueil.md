# Accueil et aide — simulation de trois enfants (3 novembre)

Parcours joués par les tests (PC : `pc/outils/test_accueil.py`, captures `pc/outils/capture_accueil.py` ; téléphone :
`tests/jvm/Accueil.kt` et le scénario du téléphone virtuel `tests/scenario.sh`). Ce sont des enfants simulés, pas de
vrais enfants.

## Lina, 7 ans (téléphone, avec son père à côté)
- « Qui est avec toi ? » : le père touche « Un adulte est à côté de moi », lit les 4 conseils, « C'est parti ».
- La bulle « Tape `pwd` ici, puis Entrée » et la ligne verte : elle trouve où taper du premier coup.
- Son premier `ls` : les puces apparaissent une à une, « Waouh, j'y vois ! ». Après 3 commandes, la flèche s'en va.
- Elle se trompe deux fois (`sl`) : le bouton 🧭 Perdu ? devient jaune ; la carte lui redit la commande.
- Point vérifié : sans commande à demander, la bulle dit « Tape ta commande ici » (`ad.fleche.tel0`), jamais un vide.

## Tom, 12 ans (PC Linux, seul)
- Menu du jeu au lancement : ↑ ↓ Entrée ; il ouvre Aide (conseils, fermer et revenir, `tg aide tout`).
- Il tape `ls ?` : bash dit « impossible d'accéder à '?' », la créature rassure puis montre la fiche courte.
- Dans un exercice : `indice` trois fois (coup de pouce, plus clair, réponse) ; rien n'est retiré.
- Le tuyau `|` arrive dans une leçon : « Sur un clavier français (AZERTY) : AltGr + 6 ».
- **Problème corrigé** (vu sur les captures) : la ligne choisie du menu n'était lisible qu'avec une couleur de fond
  → elle est maintenant en vert vif avec ▶, lisible dans tous les terminaux.

## Sacha, 15 ans (Windows, terminal du jeu, clavier seul)
- La fin grisée : `cd vest` montre « ibule/ » en gris, → l'accepte ; pendant l'exercice, rien n'est soufflé.
- Fin du tronc commun : « Tu peux fermer quand tu veux » ; `exit`, nouveau terminal : « Te revoilà ! », une fois.
- Bureau : `tg menu` ouvre le menu rond, ← → Entrée.
- Aucun problème critique.

## Reste (non bloquant)
- Le Sommet et la chasse au trésor gardent leurs indices existants (pas encore les 3 niveaux).
- Sur PC, la flèche ne peut pas revenir toute seule après 1 minute dans le vrai shell (rien ne s'affiche sans
  commande) ; elle revient à la commande suivante.
