# 📡 Ondes

*La Tour des Ondes : radio, Wi-Fi, Bluetooth, LoRa et maillage*

| | |
|---|---|
| **Durée** | environ 25 min (3 leçons, 6 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `python3`, `nmcli`, `rfkill`, `cat`, `grep` |
| **Compétences gagnées** | Sourcier, Radariste, Mailleur |

## Objectifs

- **La longueur d'onde** : une onde fait des vagues : longueur = vitesse de la lumière ÷ fréquence. Calcule celle du Wi-Fi (2,4 GHz). (avec `python3`)
- **Les réseaux autour de moi** : quels réseaux Wi-Fi entends-tu ? (avec `nmcli`, `rfkill`)
- **Le réseau maillé** : sans antenne ni internet, des radios LoRa (Meshtastic) se relaient. Lis le journal du maillage. (avec `cat`, `grep`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Ondes » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. La longueur d'onde → compétence « Sourcier »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Une onde fait des vagues : longueur = vitesse de la lumière ÷ fréquence. Calcule celle du Wi-Fi (2,4 GHz). | `python3 -c "print(3e8 / 2.4e9)"` | 0,125 m : 12,5 cm. Les antennes mesurent souvent un quart ou une demie onde. |
| 2 | Et LoRa, la radio des objets connectés (868 MHz en Europe) ? | `python3 -c "print(3e8 / 868e6)"` | 34,5 cm : une onde plus longue traverse mieux murs et collines. LoRa porte à des kilomètres ! |

### 2. Les réseaux autour de moi → compétence « Radariste »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quels réseaux Wi-Fi entends-tu ? | `nmcli dev wifi list` | SSID = le nom, SIGNAL : −30 dBm excellent, −80 faible. Le canal = la voie dans la fréquence. *Astuce : Sans Wi-Fi (ordinateur branché par câble), la liste peut être vide : c'est normal.* |
| 2 | Les radios de la machine sont-elles allumées ? | `rfkill list` | Wi-Fi, Bluetooth, 4G : chaque radio a son interrupteur. « Mode avion » = tout couper. |

### 3. Le réseau maillé → compétence « Mailleur »

*Le jeu prépare tout seul les fichiers d'exercice : `~/terrain_terminagotchi/monde/ondes/maillage.txt`.*

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Sans antenne ni internet, des radios LoRa (Meshtastic) se relaient. Lis le journal du maillage. | `cat monde/ondes/maillage.txt` | Chaque nœud relaie le message au suivant : c'est un réseau maillé. |
| 2 | Combien de relais ? Compte les lignes « relayé ». | `grep -c relayé monde/ondes/maillage.txt` | 3 relais pour 4 km : en montagne ou après une tempête, ça sauve des vies. |

## Questions pour vérifier

- Que fait la commande `python3` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `nmcli` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `rfkill` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `cat` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `grep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
