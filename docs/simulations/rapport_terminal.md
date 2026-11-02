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

Le réseau réel (ping, curl vers Internet, ssh, ssh-keygen, ip, ss, nslookup…), sudo, systemctl, journalctl, dmesg,
lsblk, top / htop, les gestionnaires de paquets, gcc / make, pip et `python3 -m …`, openssl, gpg, ImageMagick / ffmpeg / sox / exiftool,
openscad, podman / qemu, les éditeurs (nano, vim, notepad), ln, chown, crontab, useradd. Le terminal dit « cette
commande n'existe pas dans le terminal du jeu sous Windows » et l'étape est racontée, comme sur le téléphone.

## 5. Petites différences connues (non corrigées)

- `nano` / `notepad` hors d'une leçon : le message parle d'une étape racontée alors qu'il n'y en a pas.
- Après `kill %1` puis `wait`, bash interactif écrit « [1]+ Terminated » ; le terminal du jeu ne l'écrit pas.

## 6. Ajout du 2 novembre : python3 et curl, et plus de proposition WSL

Décisions du propriétaire : `python3` (le Python qui fait déjà tourner le jeu) pour de vrai dans le terrain, `curl`
limité au phare du Port, et toujours le terminal du jeu sous Windows (la proposition WSL est retirée).

Les trois enfants, rejoués en mode Windows simulé (`/home/lea`) :

- **Léa, 7 ans** : tape `python` depuis `~` → « dans le terminal du jeu, Python travaille seulement dans ton terrain.
  Va d'abord dedans : cd ~/terrain_terminagotchi » ; `curl google.com` → « pas d'Internet dans le terminal du jeu
  (rien ne sort de l'ordinateur). Ici, curl parle seulement au phare du Port : http://localhost:8042/ ». Au Port,
  `curl http://localhost:8042/feu | head -n 1` montre la barre de progression puis « 🔥 feu.terminaworld ».
- **Malo, 12 ans** : la Forge, F4 pour de vrai : `python3 --version`, `python3 -c "print(2 + 3 * 4)"` → 14,
  `python3 serpent.py` → le vrai Traceback (`File "/home/lea/terrain_terminagotchi/forge/serpent.py", line 2` …
  `IndexError: list index out of range`), puis `python3 serpent.py Malo`. `python3 -m pip install pygame` → « les
  modules de Python (-m) ne se lancent pas dans le terminal du jeu ; cette étape est racontée ». Au clavier (vrai
  pseudo-terminal) : `input()` attend sa réponse, la console `python3` marche (`1 + 1` → 2, `exit()`), Ctrl+C arrête
  `time.sleep(30)` avec le vrai `KeyboardInterrupt` (code 130).
- **Inès, 15 ans** : un programme qui compte les mots d'un fichier du terrain (juste) ; un programme qui écrit dans
  `../../Documents/x.txt` → `PermissionError: … le terminal du jeu garde Python dans ton terrain : écrire hors du
  terrain, c'est refusé` ; `shutil.rmtree("/home")`, `os.system`, `subprocess`, `urllib` vers Internet, un serveur
  sur 0.0.0.0 : refusés de la même façon ; `ls -a ~` ne montre toujours que le terrain et `.terminagotchi`.

| Gravité | Problème trouvé | Correction |
|---|---|---|
| Important | Le Traceback montrait les lignes de la garde (`<tg-python>`), même dans les exceptions enchaînées et la console | Retirées partout : le Traceback est celui du vrai Python |
| Important | `python3 -c 'print(1); 1/0' 2>&1` : l'ordre de la sortie différait du vrai Python | Même tampon que le vrai Python (et `export PYTHONUNBUFFERED=1` respecté) |
| Moyen | Le phare endormi (30 minutes sans visite) : `curl` répondait « Couldn't connect » | Le jeu rallume le phare puis curl frappe encore une fois (comme sur le téléphone) |
| Moyen | `curl -o` vers un dossier absent, `curl -f` sur un 404, `curl -O` sans nom : messages différents du vrai curl | Identiques au vrai curl 8.5 |

Résultats : `test_terminal.py` 498 identiques au vrai bash / python3 / curl, 0 différence ; garde-fous 17 cas × 2
modes ; rejeu de l'histoire dans le terminal du jeu 266 / 0 (Linux) et 268 / 0 (Windows simulé) ; sur la vraie machine
Windows : voir le passage de la CI cité dans le rapport final.

Reste raconté (jamais bloquant) : la lanterne de l'enfant (`python3 -m http.server`, Port P5 et Forge F6) et son
`curl` vers 8000 / 8642, et le sceau https (8443, qui demande openssl).
