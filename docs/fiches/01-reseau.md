# 📡 Réseau

*Parler avec internet*

| | |
|---|---|
| **Durée** | environ 30 min (3 leçons, 7 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `ping`, `ip`, `curl`, `head`, `nslookup`, `traceroute` |
| **Compétences gagnées** | Radar, Facteur, Cartographe |

## Objectifs

- **Le radar** : le monde est-il là ? Envoie un petit signal. (avec `ping`, `ip`)
- **Le facteur** : frappe à la porte d'un site, sans entrer. (avec `curl`, `head`)
- **Le cartographe** : demande à l'annuaire d'internet l'adresse d'un site. (avec `nslookup`, `traceroute`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Réseau » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Le radar → compétence « Radar »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Le monde est-il là ? Envoie un petit signal. | `ping -c 3 example.com` | Chaque réponse = un aller-retour. Le temps (ms) = la latence. |
| 2 | Et nous, quelle est notre adresse ? | `ip a` | L'adresse IP, c'est notre numéro de maison sur le réseau. |

### 2. Le facteur → compétence « Facteur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Frappe à la porte d'un site, sans entrer. | `curl -I https://example.com` | 200 = « entrez ! ». 404 = introuvable. 500 = le site est malade. |
| 2 | Depuis le terrain, rapporte-moi un colis (une page web). | `curl -o colis.html https://example.com` | -o = « output » : on range la réponse dans un fichier. *Astuce : Place-toi d'abord dans terrain_terminagotchi.* |
| 3 | Ouvre le colis : regarde les 5 premières lignes. | `head -n 5 colis.html` | Du HTML : le langage des pages web ! |

### 3. Le cartographe → compétence « Cartographe »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Demande à l'annuaire d'internet l'adresse d'un site. | `nslookup example.com` | Le DNS traduit les noms (example.com) en adresses IP. |
| 2 | Suis le chemin de nos paquets jusqu'au site. | `traceroute example.com` | Chaque ligne = un routeur traversé. Internet, c'est une chaîne de relais ! *Astuce : Si traceroute est absent : sudo apt install traceroute  (ou essaie tracepath)* |

## Questions pour vérifier

- Que fait la commande `ping` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ip` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `curl` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `head` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `nslookup` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `traceroute` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
