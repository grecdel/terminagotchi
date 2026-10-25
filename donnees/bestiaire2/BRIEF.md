# Nouveau bestiaire Terminagotchi — consignes pour une famille

Jeu : un tamagotchi qui vit dans le terminal. Les monstres sont dessinés en pixel art 16 bits (style SNES) par un générateur d'images,
une image = une créature à 5 stades côte à côte (bébé, enfant, ado, adulte, ancien), sur fond uni.

10 familles × 15 espèces. Chaque famille (description de l'auteur du jeu) :
1. Démons — Feu et ténèbres : cornes, ailes membraneuses, griffes, queues épineuses, yeux lumineux. Des diablotins jusqu'aux seigneurs infernaux. Rouge, noir, violet, orange incandescent.
2. Élémentaires — Forces de la nature : créatures de feu, glace, eau, foudre, roche et vent. Leur corps se transforme progressivement en incarnation de leur élément. Couleurs propres à chaque élément.
3. Morts-vivants — Nécromancie : squelettes, fantômes, goules, chevaliers maudits, spectres et liches. Leur évolution développe leurs pouvoirs surnaturels. Os, vert spectral, bleu froid, noir.
4. Bêtes monstrueuses — Instinct sauvage : loups cuirassés, félins à cornes, ours géants, chimères, sangliers blindés. Les jeunes ressemblent à des animaux, les adultes deviennent redoutables. Brun, ocre, gris, fourrure et os.
5. Sylvestres — Nature vivante : arbres animés, champignons guerriers, plantes carnivores, esprits des racines, créatures florales. Vert mousse, bois, ambre, fleurs lumineuses.
6. Arthropodes — Essaims et carapaces : scarabées cuirassés, araignées, scorpions, mantes, mille-pattes géants, créatures à chitine. Vert acide, noir brillant, jaune, pourpre.
7. Abyssaux — Profondeurs marines : poissons monstrueux, serpents de mer, céphalopodes, crustacés géants, créatures bioluminescentes. Bleu profond, turquoise, violet, cyan lumineux.
8. Célestes — Lumière et cosmos : gardiens ailés, créatures astrales, lions sacrés, êtres de lumière, animaux constellés. Blanc, or, bleu céleste, argent.
9. Constructs — Magie et métal : automates, armures vivantes, gardiens de pierre, marionnettes enchantées, machines runiques. Bronze, acier, cuivre, cristaux énergétiques.
10. Aberrations — Mutations et chaos : monstres oculaires, créatures tentaculaires, parasites, masses vivantes, entités qui défient la biologie. Violet, magenta, vert toxique, noir iridescent.

## Ce qu'on te demande
Écris le fichier JSON de TA famille (chemin donné dans ta mission) : une liste de 15 espèces, du rang 1 au rang 15.

Format exact de chaque espèce :
{
  "rang": 1,
  "nom": "Nom français original, un seul mot, mignon ou impressionnant, facile à retenir (jeu de mots bienvenu)",
  "id": "le nom en minuscules sans accents ni espaces",
  "rarete": "commune | peu commune | rare | légendaire",
  "posture": "quadrupède | bipède | serpentin | volant | flottant | rampant | multipattes | amorphe",
  "taille_finale": "petite | moyenne | grande | colossale",
  "fiche": "Une phrase en français pour la fiche du bestiaire (ce qu'elle est, où elle vit).",
  "caractere": "2-4 mots en français (ex: timide et gourmand)",
  "apparence": "In English: base look shared by all stages — body plan, materials, 3 dominant colors.",
  "stades": {
    "bebe":   "In English, one sentence: baby anatomy (round, cute, simple, big eyes).",
    "enfant": "In English, one sentence: what NEW body parts appear.",
    "ado":    "In English, one sentence: what changes again (proportions, new parts).",
    "adulte": "In English, one sentence: the powerful final anatomy.",
    "ancien": "In English, one sentence: elder/wise version (beard, moss, cracks, relics, halo, cane...) — older, not weaker-looking."
  },
  "habitats": ["6 à 10 lieux de vie plausibles pour CETTE créature, pris dans la liste ci-dessous, le plus évident en premier"]
}

Rareté : rangs 1-6 commune, 7-10 peu commune, 11-14 rare, 15 légendaire (le seigneur/la reine de la famille).

Habitats autorisés (orthographe exacte) :
glace, toundra, eau pétillante, lagon, abyssal, corail, marais, jungle, forêt, champignonnière, désert, sable, canyon, volcan, cendres, lave,
orage, nuage, aurore, cosmique, lune, soleil, cristal, arcane, ruines, ossuaire, crypte, brume, ombre, toxique, rouille, mécanique, néon, prairie, montagne.

## Règles de design (très important)
- CHAQUE STADE CHANGE D'ANATOMIE comme une évolution Pokémon (pas la même image agrandie) : le bébé est rond et simple, puis des membres, cornes, ailes, carapaces, armes... apparaissent ou se transforment.
- Varie les plans de corps dans la famille : pas 15 dragons ! Mélange les postures (quadrupède, serpentin, flottant, multipattes...). Au maximum 2 créatures de type dragon par famille.
- Designs ORIGINAUX : rien qui ressemble à un personnage existant (Pokémon, Digimon, Dragon Quest, Zelda, Final Fantasy, Marvel, etc.). Ne cite aucun nom de marque, d'œuvre ou de personnage.
- Descriptions concrètes et visuelles (formes, matières, couleurs), courtes : le générateur d'images doit pouvoir les dessiner.
- Les 15 noms doivent être tous différents et ne pas reprendre ces noms déjà utilisés : Abyssor, Darmong.
- Vérifie que ton fichier est un JSON valide (python3 -m json.tool fichier).
