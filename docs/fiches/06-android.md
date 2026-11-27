# 📱 Android

*Piloter ton téléphone : applis, liens, outils*

| | |
|---|---|
| **Durée** | environ 60 min (4 leçons, 15 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `termux-toast`, `termux-vibrate`, `termux-torch`, `termux-open-url`, `am`, `pm`, `echo`, `source`, `ouvre`, `termux-battery-status`, `termux-tts-speak`, `termux-clipboard-set` |
| **Compétences gagnées** | Télécommande, Portier, Lanceur, Majordome |

## Objectifs

- **Les petits pouvoirs** : fais apparaître un petit message sur l'écran. (avec `termux-toast`, `termux-vibrate`, `termux-torch`)
- **Ouvrir le monde** : ouvre un site dans ton navigateur. (avec `termux-open-url`, `am`)
- **Lancer n'importe quelle appli** : chaque appli a un nom secret (son « paquet »). Trouve celui des Réglages. (avec `pm`, `am`, `echo`, `source`, `ouvre`)
- **Le majordome** : comment va la batterie ? (avec `termux-battery-status`, `termux-tts-speak`, `termux-clipboard-set`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Android » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Les petits pouvoirs → compétence « Télécommande »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Fais apparaître un petit message sur l'écran. | `termux-toast "Coucou !"` | Termux:API relie le terminal aux fonctions du téléphone. *Astuce : Il faut l'appli Termux:API et : pkg install termux-api* |
| 2 | Fais-moi vibrer ! | `termux-vibrate -d 400` | -d = durée en millisecondes. |
| 3 | Allume la lampe torche… | `termux-torch on` | Lumière ! Pratique dans le noir. |
| 4 | … et éteins-la. | `termux-torch off` | Tu commandes le matériel du téléphone en une ligne. |

### 2. Ouvrir le monde → compétence « Portier »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Ouvre un site dans ton navigateur. | `termux-open-url https://fr.wikipedia.org` | Android choisit tout seul la bonne appli pour ce lien. |
| 2 | Cherche un lieu dans les cartes. | `am start -a android.intent.action.VIEW -d "geo:0,0?q=Tour Eiffel"` | Un « intent » = une demande envoyée à Android : « montre-moi ça ». |
| 3 | Prépare un appel (sans appeler !). | `am start -a android.intent.action.DIAL -d tel:0123456789` | DIAL ouvre le clavier avec le numéro : c'est toi qui décides d'appeler. |

### 3. Lancer n'importe quelle appli → compétence « Lanceur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Chaque appli a un nom secret (son « paquet »). Trouve celui des Réglages. | `pm list packages \| grep settings` | Le paquet des Réglages, c'est com.android.settings. |
| 2 | Lance les Réglages par leur nom secret. | `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER com.android.settings` | MAIN + LAUNCHER = « ouvre-la comme depuis son icône ». *Astuce : Si rien ne s'ouvre : autorise Termux à « s'afficher par-dessus les autres applis ».* |
| 3 | C'est long à taper… invente ta commande « ouvre » pour toujours ! | `echo 'ouvre() { am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER "$1"; }' >> ~/.bashrc` | Elle est gravée dans ta configuration. |
| 4 | Recharge ta configuration. | `source ~/.bashrc` | Ta commande « ouvre » est prête. |
| 5 | Essaie-la avec n'importe quelle appli ! | `ouvre com.android.settings` | Tu lances tes applis au clavier, comme un pro. |

### 4. Le majordome → compétence « Majordome »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Comment va la batterie ? | `termux-battery-status` | percentage = le pourcentage, status = en charge ou non. |
| 2 | Fais-moi parler ! | `termux-tts-speak "Bonjour, je suis ton Terminagotchi"` | J'ai une voix maintenant ! |
| 3 | Range un texte dans le presse-papier. | `termux-clipboard-set "Coucou"` | Colle-le où tu veux : il est dans le presse-papier. |

## Questions pour vérifier

- Que fait la commande `termux-toast` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `termux-vibrate` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `termux-torch` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `termux-open-url` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `am` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `pm` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
