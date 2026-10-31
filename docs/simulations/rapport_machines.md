# Simulation : trois enfants visitent la Salle des Machines (quatrième monde du Carrefour)

Date : 31 octobre 2026. Branche `nouveau-bestiaire`. Outil : `pc/outils/sim_machines.py` (PC, rejouable à chaque test
et en CI) ; pour Android, la traversée du téléphone est rejouée par `tests/jvm/Machines.kt` (§ 4 de ce test).

## 0. Comment on a joué

**PC.** Comme `sim_crypte.py` : chaque enfant a son propre `HOME` temporaire et un vrai `bash` qui reste ouvert
(`pc/tg/coquille.py`) ; après chaque ligne, le jeu fait son tour avec le code de sortie. L'enfant ne lit **que** la
commande montrée, la sortie de sa commande et ce que le jeu écrit dans son terminal. La Salle est ouverte d'avance
comme dans l'arbre du Carrefour (niveaux 0 à 3 du tronc commun finis : lire et chercher).

**Sans tricher.** Les trous « ? » sont remplis en **lisant l'écran** : le nombre de cœurs dans la sortie de `nproc`,
la mémoire dans la colonne `total` de `free -h` (ou `MemTotal` en kB pour Hugo), la lettre du défi dans l'écran des
interrupteurs, les cartes du réveil, l'orchestre et les boîtes d'après leurs textes (puis les ✔), la machine de
l'épreuve d'après le catalogue et les règles affichées, le drapeau dans l'écran du démarrage. Les réponses attendues
sont calculées par le jeu **sur la même machine** au moment de la vérification.

**Android.** `tests/jvm/Machines.kt` refait la traversée sm0 → sm10 avec les commandes du téléphone (`cat
/proc/cpuinfo`, `getprop ro.product.model`, `getprop ro.build.version.release`, `xxd -b` intégré ; le conteneur et la
machine virtuelle racontés) : 30 vérifications, dont l'égalité Python / Kotlin sur les vecteurs communs
(`donnees/machines/vecteurs.json` : interrupteurs, unités, réveil, orchestre, boîtes, montage, drapeau, boîte détectée).

**Limites honnêtes.** La machine de test tourne en root, sans `podman`, `qemu-img`, `virsh`, `lspci`, `lsusb` ni
`xxd` : les étapes qui en ont besoin sont **cachées** (drapeau `outil`) et n'ont pas été jouées ici ; la CI installe
`qemu-utils`, `pciutils`, `usbutils` et `xxd` (et le runner GitHub a `podman`), donc elles y sont rejouées par
`rejeu_bash.py`. Le vrai lancement d'un conteneur n'a **jamais** été fait sur la machine de test.

## 1. Les trois profils en bref

| Profil | Ce qu'il fait | Lignes tapées | Au bout ? | Exploit « premier démarrage » |
|---|---|---|---|---|
| Léa, 7 ans, tape mal | une majuscule (`Nproc`), `sudo dmesg`, le « ? » recopié, une virgule dans la mémoire (`7,8`), de mauvais interrupteurs, les cartes du réveil dans l'ordre A B C D E, `tar czf collection.txt sauvegarde.tar.gz` (à l'envers), la copie au mauvais endroit, la panne déclenchée trop tôt, une machine dont la prise ne va pas au premier démarrage | 79 | oui, sm0 → sm10 | non (premier démarrage raté : c'est voulu) |
| Inès, 12 ans, recopie | recopie la commande verte (« ? » compris), puis lit l'écran | 69 | oui | oui |
| Hugo, 15 ans, ses variantes | `lscpu`, `cat /proc/meminfo`, `df -h`, `printf A \| od`, `wc -c`, `uname -a`, `command -v ls`, `bash …`, `tar -czf`, `cp sauvegarde.* …`, `sha256sum --check`… | 61 | oui | oui, 26 variantes justes acceptées sur 26 |

Commun aux trois : aucune étape validée par une commande qui a échoué ; rien d'écrit hors du terrain et de
`~/.terminagotchi` ; le prénom tapé dans `machines interrupteurs` n'est gardé ni dans le carnet ni dans la sauvegarde ;
aucun nom de machine, nom d'utilisateur, numéro de série ni adresse MAC dans ce que le jeu enregistre.

### Léa (7 ans)

| Question | Constat |
|---|---|
| Comprend-elle ? | Oui : le cuisinier, le plan de travail, le garde-manger ; les interrupteurs de son prénom (« é » prend deux rangées) ; la machine qui se réveille étage par étage avec les vraies valeurs de son ordinateur. |
| `sudo dmesg` | « Pas de sudo ici : la Salle des Machines se visite en lecture seule. » ; `dmesg` sans sudo est accepté même s'il est refusé (« Operation not permitted » est expliqué comme normal). |
| La panne trop tôt | « Si ça brûlait maintenant, tout serait perdu » : rien n'est effacé, elle refait la copie au loin. |
| La machine qui ne démarre pas | Chaque problème est dit en une phrase (prise, type de mémoire, alimentation, besoin) ; pas de pression, pas de limite de temps. |

### Inès (12 ans)

| Question | Constat |
|---|---|
| Recopier suffit-il ? | Partout sauf aux trous `?` (cœurs, mémoire, interrupteurs, réveil, orchestre, boîtes, montage, drapeau), voulus : le jeu dit que c'est un trou et ce qu'il faut lire. |
| L'exploit | Machine juste au premier démarrage : `machines.premier_demarrage` gagné, rencontres favorisées des variantes réservées. |

### Hugo (15 ans)

| Question | Constat |
|---|---|
| Ses variantes justes ? | 26 sur 26 acceptées après corrections (MA3, MA4). |
| Fausses variantes | `Cat /proc/cpuinfo \| head` passait grâce au tuyau (MA5) : corrigé en demandant `head -5 /proc/cpuinfo`. |

## 2. Problèmes trouvés, classés

### Critiques — aucun ouvert

| # | Problème | État |
|---|---|---|
| MA1 | Une commande absente (code 127) validait les étapes « tout code accepté » (`dmesg`, `systemd-analyze`, `virsh` : leur échec est normal). | `tout_code` accepte tout code **sauf** 127 (`pc/tg/verif.py`). |
| MA2 | Les étapes propres à Linux (`lsblk`, `lspci`, `lsusb`, `dmesg`, `systemd-analyze`, `lsmod`, `/etc/os-release`, `/proc/1/cgroup`, `podman`, `qemu-img`, `virsh`) bloquaient une machine qui ne les a pas. | Drapeau `outil` (accepte aussi un chemin comme `/proc/cpuinfo`) : l'étape est cachée si l'outil manque ; jamais bloquant. |

### Importants — tous corrigés

| # | Problème | Correction |
|---|---|---|
| MA3 | `cat /proc/meminfo` (réponse en kB) refusé à la question de la mémoire. | `memoire_ok` accepte Gio, Go, Mio et kB. |
| MA4 | `stat -c %s` n'existe pas sur macOS ; `od` refusé pour le binaire de « A ». | L'étape demande `wc -c photo.bin` (stat et ls -l acceptés) ; `od` accepté à côté de `xxd -b`. |
| MA5 | Un tuyau (`Cat … \| head`) faisait passer une majuscule fautive. | L'étape est `head -5 /proc/cpuinfo`. |
| MA6 | `cat /proc/uptime` accepté avec un bravo qui ne collait pas (« up … load average »). | L'étape demande `uptime` seul. |
| MA7 | Le besoin de l'épreuve n'était pas rappelé sur l'écran du montage. | La ligne « Le besoin : … » est en tête du montage et du démarrage. |
| MA8 | La collection reposée par le jeu (après un `tar` à l'envers) n'était pas reconnue dans une autre langue. | Marque de collection indépendante de la langue (`# terminagotchi: collection`). |
| MA9 | Le bilan 3-2-1 comptait mal les copies. | Une copie par endroit (le poste, le disque 2, loin) ; chaque endroit est un support différent. |
| MA10 | (captures) `sh conteneur_jetable.sh` sans podman disait seulement « podman n'est pas installé », sans expliquer ce qu'il ferait. | Le script explique toujours d'abord (image, taille, commande), puis signale l'absence de podman ; `lancer` et `effacer` seulement exigent podman. PC et Android. |
| MA11 | (captures) Sur le téléphone, la jauge d'alimentation de l'atelier affichait « ∞ » au lieu des watts fournis ; le mot « points » n'était pas traduit ; les noms des pièces débordaient sous le dessin de la salle ; le nom du lieu (« machines · la salle des machines ») chevauchait le nom de la créature. | Jauge corrigée (∞ seulement pour le budget de l'école), « ★ » à la place de « points », noms masqués s'ils ne tiennent pas, lieu court « les rouages » (14 langues). |
| MA12 | Les interrupteurs `▮▯` manquent dans plusieurs polices de terminal. | `■ □` (présents partout), PC et Android. |

### Mineurs (notés)

| # | Constat |
|---|---|
| MA13 | Comme partout dans le jeu, `Dmesg \| head` passe grâce au tuyau (le shell signale l'erreur, `head` réussit) : comportement général, pas propre à la Salle. |
| MA14 | Sur macOS, la leçon est plus courte (les outils propres à Linux sont cachés) ; le contenu est raconté par `machines ouvre`, `machines reveil`, `machines boite`. |
| MA15 | Sur PC, la ligne des règles de l'atelier dépasse 120 colonnes en français : le terminal la replie. |
| MA16 | En CI, le runner GitHub a `podman` : le rejeu lance vraiment `sh conteneur_jetable.sh lancer` (image alpine téléchargée une fois, `--rm`, `--network=none`, tout dans le terrain jetable, délai maximal 300 s) ; si cela échoue, l'étape l'accepte (« avec un adulte », jamais bloquant). |

## 3. Ce qui marche bien

- **Lecture seule** : aucune commande montrée n'écrit hors du terrain ; jamais de `sudo` ; `virsh -r` ; `uname` sans
  `-a` (le nom de la machine n'est jamais affiché par le jeu) ; `test_machines.py` le vérifie dans les 14 langues.
- **Réponses justes sur chaque machine** : cœurs (nproc, `/proc/cpuinfo`, plages de `/sys`), mémoire, noyau, premier
  programme, micrologiciel (UEFI ou BIOS) sont lus au moment de la vérification ; le rejeu bash compare ce que dit le
  vrai bash à ce que calcule le jeu (`egal_jeu`).
- **Avec un adulte** : rien ne s'installe tout seul ; le script se lit avant d'être lancé et explique avant de
  télécharger ; le conteneur est jetable et rangé dans `machines/conteneurs/` ; aucune `virt-install` automatique ;
  sur le téléphone, tout est raconté.
- **« Monte ta machine »** : pièces génériques (prises A et B, mémoire type 4 et 5), budget en points fictifs, aucune
  marque, aucun prix, aucun achat ; le niveau 1 démarre tout de suite, l'épreuve a un besoin tiré par partie et un
  drapeau `TG{…}`.
- Le moment fort : l'incendie de la ferme qui épargne la copie « loin », puis `sha256sum -c` et la restauration.
- Les Ponts des Nombres (hexadécimal, binaire, puissances, multiplication, addition) sont proposés sans jamais bloquer.

## 4. Ce qui reste

- Les illustrations (prompts écrits dans `outils/machines/prompts_illustrations.md`, aucune image générée) ; en
  attendant, la salle, l'ordinateur ouvert, les interrupteurs, le réveil, l'atelier, la ferme et le conteneur sont
  dessinés (PC en caractères, téléphone `MachinesDessin`).
- Les étapes `podman`, `qemu-img`, `virsh`, `lspci`, `lsusb`, `xxd` : jouées seulement en CI, pas sur la machine de
  test.
- Le nom : l'aile du volcan s'appelle déjà « la salle des machines » (pièce `salle_des_machines`) ; le monde utilise
  le chapitre `machinerie` et le dossier `machines` (question au propriétaire).

## 5. Rejouer

```
python3 pc/outils/sim_machines.py               # les trois
python3 pc/outils/sim_machines.py lea           # une seule
python3 pc/outils/test_machines.py              # la Salle sur PC (46 vérifications)
# Android : tests/jvm/Machines.kt (30 vérifications), voir outils/tout.sh jvm Machines
```
