# Simulation : trois enfants jouent sous Windows dans le terminal du jeu

Date : 2 novembre 2026. Branche `nouveau-bestiaire`. Décision du propriétaire (2 novembre) : sous Windows, plus de
PowerShell ; le jeu ouvre son propre terminal Linux, écrit en Python (`pc/tg/vsh/`), sans aucun programme ajouté.

## 0. Comment on a joué

- **Sur une vraie machine Windows** (GitHub, `windows-latest`, workflow `.github/workflows/windows.yml`, job
  `histoire-terminal-du-jeu`) : `pc/outils/rejeu_bash.py --terminal-du-jeu` joue toute l'histoire comme un enfant,
  ligne par ligne, dans le terminal du jeu : le tronc commun (réveil, nid, grenier, cave, bibliothèque, machines,
  dortoir, atelier, tour, cœur), puis les 12 mondes du Carrefour et le Sommet. Après chaque ligne, le jeu fait son
  tour (la créature mange la commande, l'étape est jugée). À la fin, on vérifie que rien n'a été écrit hors du
  terrain.
- **Sous Linux, en mode « Windows simulé »** (`TG_VSH_MODE=windows`) : la même histoire, avec le même Linux virtuel
  (`/home/<nom>`, `/etc`, `/bin` du jeu, droits gardés à part), pour trouver les écarts avant de les envoyer sur la
  machine Windows.
- **Trois profils d'enfants**, joués par de courtes sessions tapées dans `python pc sh` (mode Windows simulé) et dans
  un vrai pseudo-terminal (touches ↑, Tab, Ctrl+C) :
  - **Léa, 7 ans**, qui a déjà vu l'invite de commandes de Windows à l'école : `dir`, `cls`, `cd..`, `del`,
    `notepad`, `explorer .`, des accents et un emoji ;
  - **Malo, 12 ans**, qui suit l'histoire : le chemin complet du rejeu (dont l'Atelier : `cp cerveau_exemple.sh
    cerveau.sh`, `for i in $(seq 20); do sh cerveau.sh; atelier pas; done`) ;
  - **Inès, 15 ans**, qui va au Sommet : script avec `set -eu`, `"$@"`, `$(( ))`, fonctions avec `local` et
    `${1:-vide}`, `sleep 30 &` / `jobs` / `kill %1`, `timeout 1 sh -c 'while true…'`, `awk`, `sed`, `sqlite3`.

## 1. Ce qui marche

- L'histoire entière est jouable dans le terminal du jeu : sous Linux, 255 sorties identiques au vrai bash et 0 écart
  (mode réel) ; 257 identiques et 0 écart en mode Windows simulé. Sur la vraie machine Windows : voir le § 3.
- Le terminal ressemble à celui de Linux : `lea@vm:~/terrain_terminagotchi/vestibule$`, `ls` en couleurs, ↑ ↓,
  Tab (`cd ter` + Tab → `cd terrain_terminagotchi/`), Ctrl+C arrête `sleep 5`, `exit` ramène au jeu, les accents et
  les emojis passent.
- `chmod 444` puis `echo poire >> repas.txt` : « Permission denied », comme sous Linux ; `./miam.sh` refusé sans le
  droit x, lancé après `chmod +x`.
- `touch ~/dehors.txt`, `echo x > /etc/hostname` : refusés (« Permission denied ») ; rien n'est écrit hors du terrain.
- Le défi de l'Atelier avec `cerveau.sh` et `for i in $(seq 20)` : réussi, exploit donné.
- Les commandes du jeu (`atelier pas`, `assistant`, `agent boucle`, `controle`…) se lancent depuis ce terminal ;
  `timeout -s INT 1 agent boucle` les arrête comme un Ctrl+C.

## 2. Problèmes trouvés et corrigés

| Gravité | Problème | Correction |
|---|---|---|
| Critique | Sur la vraie machine Windows, les fichiers écrits par le jeu avaient des fins de ligne Windows (`\r\n`) : `sha256sum -c` échouait (Citadelle), `grep` montrait un `\r` (Port) | Le jeu écrit le terrain avec des fins de ligne Linux (`droits.installer`, `newline="\n"`) ; la sortie des commandes du jeu est remise en `\n` |
| Critique | Windows ne sait pas envoyer Ctrl+C (SIGINT) à un autre programme : `timeout -s INT 1 agent boucle` bloquait l'Observatoire | Un petit fichier d'arrêt (`TG_ARRET`) : le jeu s'arrête alors comme avec Ctrl+C (`pc/tg/__init__.py`) |
| Important | Les lieux du système n'avaient pas `/etc/hosts` (Port, `cat /etc/hosts`) | Ajouté aux fichiers du Linux virtuel |
| Important | Le PATH demandé au Poste de Contrôle était celui de Windows | Le jeu demande celui du terminal du jeu (`/usr/local/bin:/usr/bin:/bin`) |
| Important | Léa tape `cls`, `cd..`, `del` : seulement « command not found » | Un conseil gentil : « C'est une commande de l'invite de commandes de Windows. Ici, c'est un terminal Linux : essaie `clear` » (14 langues) |
| Moyen | `tg mini`, l'île du bureau et l'espace lançaient encore PowerShell | Ils passent par le terminal du jeu ; `terminal` dans l'espace ouvre une fenêtre de plus |

## 3. Résultat sur la vraie machine Windows

Passage du 2 novembre (GitHub Actions, `windows-latest`, run 41372118541) : **toute l'histoire jouée jusqu'au bout**
(tronc commun, 12 mondes et Sommet) dans le terminal du jeu : 250 sorties conformes à ce que le jeu attend, **0 écart**,
51 cas sautés (réseau, téléphone, commandes du jeu elles-mêmes, outils racontés), et rien d'écrit hors du terrain.
Le job `windows` du même passage (`test_windows.py` : 24 réussis ; `test_terminal.py --windows --git` : 25 identiques)
est vert aussi. Les passages d'avant avaient trouvé les trois problèmes critiques du § 2.

## 4. Ce qui reste raconté sous Windows (jamais bloquant)

Le réseau réel (ping, curl, ssh, ssh-keygen, ip, ss, nslookup…), sudo, systemctl, journalctl, dmesg, lsblk, top /
htop, les gestionnaires de paquets, gcc / make, python3 / pip, openssl, gpg, ImageMagick / ffmpeg / sox / exiftool,
openscad, podman / qemu, les éditeurs (nano, vim, notepad), ln, chown, crontab, useradd. Le terminal dit « cette
commande n'existe pas dans le terminal du jeu sous Windows » et l'étape est racontée, comme sur le téléphone.

## 5. Petites différences connues (non corrigées)

- `nano` / `notepad` hors d'une leçon : le message parle d'une étape racontée alors qu'il n'y en a pas.
- Après `kill %1` puis `wait`, bash interactif écrit « [1]+ Terminated » ; le terminal du jeu ne l'écrit pas.
- Ctrl+C affiche `^C` deux fois.
