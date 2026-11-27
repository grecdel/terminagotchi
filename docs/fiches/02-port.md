# ⚓ Port

*Les réseaux : adresses, ports, TCP/UDP, routage, box, HTTPS*

| | |
|---|---|
| **Durée** | environ 35 min (5 leçons, 9 étapes) |
| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |
| **Prérequis** | le tronc commun (se repérer, créer, lire, chercher) |
| **Commandes vues** | `ss`, `grep`, `curl`, `nslookup`, `ip`, `ping` |
| **Compétences gagnées** | Capitaine, Aiguilleur, Gardien du phare, Douanier, Coffre-fort |

## Objectifs

- **Les quais** : une machine a une adresse (IP) et des quais numérotés : les ports. Lesquels attendent des bateaux ? (avec `ss`, `grep`)
- **TCP et UDP** : regarde une connexion se faire, en mode bavard. (avec `curl`, `nslookup`)
- **Le phare** : par où sortent nos paquets ? Regarde la table des routes. (avec `ip`, `ping`)
- **La box** : quelle est ton adresse vue d'internet ? (avec `curl`)
- **Le cadenas** : regarde le certificat d'un site : sa carte d'identité. (avec `curl`)

## Mise en route

1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.
2. Choisir la branche : touche [a] puis « Port » sur PC, `arbre` sur téléphone.
3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).
4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).

## Déroulé

### 1. Les quais → compétence « Capitaine »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Une machine a une adresse (IP) et des quais numérotés : les ports. Lesquels attendent des bateaux ? | `ss -tuln` | LISTEN = un quai qui attend. 22 = SSH, 53 = DNS, 80 = web, 443 = web chiffré. |
| 2 | L'annuaire des quais : cherche à quoi sert le port 443. | `grep -w 443 /etc/services` | https 443/tcp : chaque service a son numéro de quai, le même partout dans le monde. |

### 2. TCP et UDP → compétence « Aiguilleur »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Regarde une connexion se faire, en mode bavard. | `curl -v https://example.com -o /dev/null` | « Connected to … port 443 » : TCP fait une poignée de main (SYN, SYN-ACK, ACK) avant de parler. |
| 2 | Le DNS, lui, envoie une carte postale (UDP). Pose ta question à un serveur précis : 1.1.1.1. | `nslookup example.com 1.1.1.1` | UDP, port 53 : pas de poignée de main, plus rapide, mais sans garantie d'arrivée. |

### 3. Le phare → compétence « Gardien du phare »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Par où sortent nos paquets ? Regarde la table des routes. | `ip route` | « default » / 0.0.0.0 : la passerelle, la sortie vers internet. Chez toi, c'est la box ! |
| 2 | Envoie un signal à la passerelle (l'adresse de la ligne « default »). | `ping -c 2 192.168.1.1` | 1 ou 2 ms : elle est tout près. C'est le premier relais de chacun de tes paquets. *Astuce : Remplace 192.168.1.1 par l'adresse de ta passerelle.* |

### 4. La box → compétence « Douanier »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Quelle est ton adresse vue d'internet ? | `curl https://api.ipify.org` | Différente de ton adresse locale : la box traduit (NAT) toute la maison en une seule adresse. |

### 5. Le cadenas → compétence « Coffre-fort »

| Étape | La créature demande | Commande attendue | À expliquer |
|---|---|---|---|
| 1 | Regarde le certificat d'un site : sa carte d'identité. | `curl -vI https://wikipedia.org` | subject, issuer, expire date : le certificat prouve qui est le site ; ensuite tout est chiffré (TLS). |
| 2 | Compare avec un site en http (sans s). | `curl -vI http://example.com` | Pas de certificat, pas de chiffrement : en http:// chaque relais peut lire. Le cadenas, ça compte ! |

## Questions pour vérifier

- Que fait la commande `ss` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `grep` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `curl` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `nslookup` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ip` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Que fait la commande `ping` ? Dans quelle situation de la vie réelle te servirait-elle ?
- Qu'est-ce qui t'a surpris pendant cette séance ?

## Pour aller plus loin

- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.
- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.
