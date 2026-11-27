"""Les mondes avancés du Terminaworld (le Port est dans lecons.py, avec le Réseau).

Chaque monde est une branche de l'arbre de compétences : des leçons courtes, avec de VRAIES commandes.
Une leçon peut préparer ses fichiers d'exercice dans le terrain de jeu (« prep ») ; une étape est validée
par la commande tapée (« re ») ou par l'état du terrain (« existe », « absent », « contient »).
"""
import base64

from .plateforme import C, installer

# ---------------------------------------------------------------- fichiers d'exercice
JOURNAL_AUTH = "\n".join([
    "Nov 27 09:58:12 citadelle sshd[801]: Accepted password for alice from 192.168.1.20 port 50110 ssh2",
    "Nov 27 10:01:02 citadelle sshd[812]: Failed password for root from 203.0.113.7 port 51234 ssh2",
    "Nov 27 10:01:04 citadelle sshd[812]: Failed password for root from 203.0.113.7 port 51236 ssh2",
    "Nov 27 10:01:06 citadelle sshd[812]: Failed password for admin from 203.0.113.7 port 51240 ssh2",
    "Nov 27 10:02:40 citadelle sshd[820]: Failed password for bob from 198.51.100.23 port 40022 ssh2",
    "Nov 27 10:03:15 citadelle sshd[825]: Accepted publickey for bob from 192.168.1.31 port 50200 ssh2",
    "Nov 27 10:04:01 citadelle sshd[830]: Failed password for root from 203.0.113.7 port 51290 ssh2",
    "Nov 27 10:04:03 citadelle sshd[830]: Failed password for root from 203.0.113.7 port 51292 ssh2",
    "Nov 27 10:05:59 citadelle sshd[841]: Failed password for test from 198.51.100.23 port 40100 ssh2",
]) + "\n"

MESSAGE_CESAR = "WHUPLQDJRWFKL HVW XQ JHQLH\n"          # « TERMINAGOTCHI EST UN GENIE », décalé de 3
TRESOR = base64.b64encode("Le trésor est caché sous la Racine.\n".encode()).decode() + "\n"

CREATURES_CSV = """nom,famille,rarete,taille_cm
Braisillon,Démons,commune,45
Cornichaud,Démons,commune,90
Infernarque,Démons,légendaire,900
Gouttelin,Élémentaires,commune,30
Tellurion,Élémentaires,légendaire,1100
Osselet,Morts-vivants,commune,40
Lichonarque,Morts-vivants,légendaire,240
Glandouille,Sylvestres,commune,35
Mousselin,Sylvestres,commune,120
Krillou,Abyssaux,commune,50
Poulpiot,Abyssaux,commune,60
Auréolin,Célestes,rare,180
Runodrake,Constructs,rare,420
Chaosmère,Aberrations,légendaire,1200
"""

AVIS = """positif : j'adore ce jeu, ma créature est trop mignonne
positif : le terminal devient facile, j'adore apprendre
négatif : le défi éclair est trop rapide pour moi
positif : les dessins sont superbes, j'adore
négatif : j'ai perdu mon dressage, trop dur
positif : super jeu pour apprendre le terminal
négatif : ma créature a faim trop souvent
positif : j'adore le Port et les réseaux
"""

TEXTE_IA = """le chat dort sur le canapé
le chat mange sa pâtée
le chat dort au soleil
le chien court dans le jardin
le chat dort encore
le chien mange sa pâtée
le chat joue avec la ficelle
"""

BIAIS = """docteur : il
docteur : il
docteur : il
docteur : il
docteur : elle
infirmier : elle
infirmier : elle
infirmier : elle
infirmier : il
"""

CONSIGNE = """# Une bonne consigne pour un assistant IA
Rôle      : tu es un professeur de terminal patient, pour une élève de 10 ans.
Contexte  : elle sait déjà utiliser ls et cd, elle découvre grep.
Tâche     : explique-lui grep avec un exemple tiré de la vie de tous les jours.
Format    : 5 lignes maximum, puis un petit exercice.
Vérifie   : si tu n'es pas sûr d'une option, dis-le au lieu d'inventer.
"""

LICENCE = """MIT License

Copyright (c) 2026 Les Bâtisseurs Libres

Permission is hereby granted, free of charge, to any person obtaining a copy of this software, to deal in the
Software without restriction, including the rights to use, copy, modify, merge, publish, distribute...
"""

BONJOUR_C = """#include <stdio.h>

int main(void) {
    printf("Bonjour depuis un programme compilé !\\n");
    return 0;
}
"""

DEVINE_PY = """import random

# Le jeu du nombre mystère : change BORNE pour le rendre plus dur !
BORNE = 3
secret = random.randint(1, BORNE)
essai = input(f"Devine mon nombre (1 à {BORNE}) : ")
if essai.strip() == str(secret):
    print("Gagné ! Tu lis dans mes pensées.")
else:
    print(f"Perdu, c'était {secret}. Retente ta chance !")
"""

BIP_PY = """import math, os, struct, wave

# Fabrique un son : 1 seconde de La (440 Hz), 8000 mesures par seconde.
with wave.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bip.wav"), "w") as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000)
    for i in range(8000):
        f.writeframes(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / 8000))))
print("bip.wav est prêt : ouvre-le avec ton lecteur de sons !")
"""

MAILLAGE = """[nœud Pixel]     message « coucou » envoyé (868 MHz, LoRa)
[nœud Ferme]     reçu de Pixel, relayé (saut 1)
[nœud Colline]   reçu de Ferme, relayé (saut 2)
[nœud Village]   reçu de Colline, relayé (saut 3)
[nœud Zoé]       message « coucou » reçu après 3 sauts, 4,2 km, sans internet !
"""

F = "monde"            # dossier des mondes dans le terrain de jeu


def _p(*morceaux):
    return "/".join((F,) + morceaux)


MONDES = {
    # ------------------------------------------------------------------------------------------ 📡
    "Ondes": {"stat": "Agilité", "icone": "📡", "desc": "la Tour des Ondes : radio, Wi-Fi, Bluetooth, LoRa et maillage",
              "lecons": [
        {"titre": "La longueur d'onde", "skill": "Sourcier", "steps": [
            {"dit": "Une onde fait des vagues : longueur = vitesse de la lumière ÷ fréquence. Calcule celle du Wi-Fi (2,4 GHz).",
             "cmd": C('python3 -c "print(3e8 / 2.4e9)"', 'python -c "print(3e8 / 2.4e9)"'), "re": r"3e8\s*/\s*2\.4e9",
             "bravo": "0,125 m : 12,5 cm. Les antennes mesurent souvent un quart ou une demie onde."},
            {"dit": "Et LoRa, la radio des objets connectés (868 MHz en Europe) ?",
             "cmd": C('python3 -c "print(3e8 / 868e6)"', 'python -c "print(3e8 / 868e6)"'), "re": r"3e8\s*/\s*868e6",
             "bravo": "34,5 cm : une onde plus longue traverse mieux murs et collines. LoRa porte à des kilomètres !"},
        ]},
        {"titre": "Les réseaux autour de moi", "skill": "Radariste", "steps": [
            {"dit": "Quels réseaux Wi-Fi entends-tu ?",
             "cmd": C("nmcli dev wifi list", "netsh wlan show networks mode=bssid",
                      mac="system_profiler SPAirPortDataType", android="termux-wifi-scaninfo"),
             "re": r"^(nmcli|netsh|system_profiler|termux-wifi|iw\b|iwlist|airport)",
             "astuce": "Sans Wi-Fi (ordinateur branché par câble), la liste peut être vide : c'est normal.",
             "bravo": "SSID = le nom, SIGNAL : −30 dBm excellent, −80 faible. Le canal = la voie dans la fréquence."},
            {"dit": "Les radios de la machine sont-elles allumées ?",
             "cmd": C("rfkill list", "Get-PnpDevice -Class Bluetooth", mac="system_profiler SPBluetoothDataType",
                      android="termux-telephony-deviceinfo"),
             "re": r"^(rfkill|bluetoothctl|get-pnpdevice|system_profiler|termux-telephony)",
             "bravo": "Wi-Fi, Bluetooth, 4G : chaque radio a son interrupteur. « Mode avion » = tout couper."},
        ]},
        {"titre": "Le réseau maillé", "skill": "Mailleur", "prep": {_p("ondes", "maillage.txt"): MAILLAGE}, "steps": [
            {"dit": "Sans antenne ni internet, des radios LoRa (Meshtastic) se relaient. Lis le journal du maillage.",
             "cmd": C(f"cat {_p('ondes', 'maillage.txt')}", f"Get-Content {_p('ondes', 'maillage.txt')}"),
             "re": r"(cat|get-content|gc|type|less|more)\b.*maillage",
             "bravo": "Chaque nœud relaie le message au suivant : c'est un réseau maillé."},
            {"dit": "Combien de relais ? Compte les lignes « relayé ».",
             "cmd": C(f"grep -c relayé {_p('ondes', 'maillage.txt')}",
                      f"(Select-String relayé {_p('ondes', 'maillage.txt')}).Count"),
             "re": r"(grep|select-string).*relay",
             "bravo": "3 relais pour 4 km : en montagne ou après une tempête, ça sauve des vies."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🛡
    "Citadelle": {"stat": "Force", "icone": "🛡", "desc": "la Citadelle : cybersécurité défensive, attaques simulées, boîtes à percer puis réparer",
                  "lecons": [
        {"titre": "Le guet", "skill": "Guetteur",
         "prep": {_p("citadelle", "journal_auth.log"): JOURNAL_AUTH}, "steps": [
            {"dit": "Quelqu'un essaie d'entrer dans la Citadelle ! Cherche les échecs de connexion dans le journal.",
             "cmd": C(f"grep Failed {_p('citadelle', 'journal_auth.log')}",
                      f"Select-String Failed {_p('citadelle', 'journal_auth.log')}"),
             "re": r"(grep|select-string|findstr).*failed", "bravo": "« Failed password » : des mots de passe ratés, à la chaîne…"},
            {"dit": "Qui attaque ? Compte les essais par adresse.",
             "cmd": C(f"grep Failed {_p('citadelle', 'journal_auth.log')} | cut -d' ' -f11 | sort | uniq -c | sort -rn",
                      f"Select-String Failed {_p('citadelle', 'journal_auth.log')} | ForEach-Object {{ ($_ -split ' ')[10] }} | Group-Object | Sort-Object Count -Descending"),
             "re": r"(uniq\s+-c|group-object)",
             "bravo": "203.0.113.7 a essayé 5 fois sur root : une attaque par force brute. On le bloquerait au pare-feu."},
        ]},
        {"titre": "Les remparts", "skill": "Bâtisseur de remparts",
         "prep": {_p("citadelle", "coffre.txt"): "code du coffre : 4242\n"}, "steps": [
            {"dit": "Qui peut lire le coffre ? Regarde ses droits.",
             "cmd": C(f"ls -l {_p('citadelle', 'coffre.txt')}", f"Get-Acl {_p('citadelle', 'coffre.txt')} | Format-List"),
             "re": r"^(ls\s+-l|get-acl|icacls)", "bravo": "rw-r--r-- : tout le monde peut le lire. Pas terrible pour un code secret !"},
            {"dit": "Ferme les remparts : toi seul peux lire et écrire.",
             "cmd": C(f"chmod 600 {_p('citadelle', 'coffre.txt')}",
                      f"icacls {_p('citadelle', 'coffre.txt')} /inheritance:r /grant:r \"$env:USERNAME:F\""),
             "re": r"^(chmod\s+0?600|icacls\b.*/inheritance:r)",
             "bravo": "600 = rw------- : le principe du moindre privilège. Chacun n'a que ce dont il a besoin."},
        ]},
        {"titre": "L'empreinte", "skill": "Vérificateur",
         "prep": {_p("citadelle", "rapport.txt"): "Rapport du guet : RAS, tout est calme.\n"}, "steps": [
            {"dit": "Prends l'empreinte du rapport (SHA-256).",
             "cmd": C(f"sha256sum {_p('citadelle', 'rapport.txt')}", f"Get-FileHash {_p('citadelle', 'rapport.txt')}",
                      mac=f"shasum -a 256 {_p('citadelle', 'rapport.txt')}"),
             "re": r"(sha256sum|get-filehash|shasum).*rapport", "bravo": "64 caractères : l'empreinte unique de ce fichier."},
            {"dit": "Un espion modifie le rapport…",
             "cmd": C(f"echo 'tout va bien, ouvrez les portes' >> {_p('citadelle', 'rapport.txt')}",
                      f"Add-Content {_p('citadelle', 'rapport.txt')} 'tout va bien, ouvrez les portes'"),
             "re": r"(>>|add-content).*rapport", "bravo": "Le texte a l'air innocent…"},
            {"dit": "Reprends l'empreinte et compare.",
             "cmd": C(f"sha256sum {_p('citadelle', 'rapport.txt')}", f"Get-FileHash {_p('citadelle', 'rapport.txt')}",
                      mac=f"shasum -a 256 {_p('citadelle', 'rapport.txt')}"),
             "re": r"(sha256sum|get-filehash|shasum).*rapport",
             "bravo": "Tout a changé ! C'est ainsi qu'on vérifie qu'un fichier téléchargé n'a pas été trafiqué."},
        ]},
        {"titre": "La boîte à percer", "skill": "Hacker éthique",
         "prep": {_p("citadelle", "boite", "accueil.txt"): "Bienvenue sur le serveur de la boulangerie.\n",
                  _p("citadelle", "boite", ".config"): "utilisateur=admin\nmot_de_passe=tournesol\n"}, "steps": [
            {"dit": "Une « boîte » d'entraînement : un faux serveur à auditer. Montre TOUS ses fichiers, même cachés.",
             "cmd": C(f"ls -a {_p('citadelle', 'boite')}", f"Get-ChildItem -Force {_p('citadelle', 'boite')}"),
             "re": r"(ls\s+-\w*a|get-childitem.*-force|gci.*-force|dir\s+/a)",
             "bravo": "Un fichier caché, .config… suspect."},
            {"dit": "Cherche un mot de passe oublié dans la boîte.",
             "cmd": C(f"grep -r mot_de_passe {_p('citadelle', 'boite')}",
                      f"Get-ChildItem -Force -Recurse {_p('citadelle', 'boite')} | Select-String mot_de_passe"),
             "re": r"(grep\s+-\w*r|select-string).*mot_de_passe",
             "bravo": "Percée ! Un mot de passe en clair dans un fichier : la faille la plus courante du monde."},
            {"dit": "Maintenant, répare : supprime ce fichier dangereux.",
             "cmd": C(f"rm {_p('citadelle', 'boite', '.config')}", f"Remove-Item -Force {_p('citadelle', 'boite', '.config')}"),
             "absent": _p("citadelle", "boite", ".config"),
             "bravo": "Percer pour apprendre, réparer pour protéger : c'est le métier de hacker éthique."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🗝
    "Crypte": {"stat": "Intelligence", "icone": "🗝", "desc": "la Crypte des Codes : cryptographie, des codes anciens à la blockchain",
               "lecons": [
        {"titre": "Le code de César", "skill": "Centurion", "prep": {_p("crypte", "message.txt"): MESSAGE_CESAR}, "steps": [
            {"dit": "Jules César décalait chaque lettre de 3. Chiffre BONJOUR.",
             "cmd": C("echo BONJOUR | tr 'A-Z' 'D-ZA-C'",
                      "python -c \"print(''.join(chr((ord(c)-62)%26+65) for c in 'BONJOUR'))\""),
             "re": r"(tr\b.*d-za-c|ord\(c\))", "bravo": "ERQMRXU : illisible… sauf pour qui connaît la clé (3)."},
            {"dit": "Un message chiffré t'attend dans la crypte. Déchiffre-le !",
             "cmd": C(f"tr 'D-ZA-C' 'A-Z' < {_p('crypte', 'message.txt')}",
                      f"python -c \"print(''.join(chr((ord(c)-68)%26+65) if c.isalpha() else c for c in open('{_p('crypte', 'message.txt')}').read()))\""),
             "re": r"(tr\b.*a-z.*message|message.*tr\b|ord\(c\).*message|message.*ord\(c\))",
             "bravo": "26 clés possibles seulement : un ordinateur casse César en un clin d'œil."},
        ]},
        {"titre": "Le colis en base64", "skill": "Transcripteur", "prep": {_p("crypte", "colis.b64"): TRESOR}, "steps": [
            {"dit": "Base64 transforme n'importe quoi en lettres simples. Encode un mot.",
             "cmd": C("echo -n secret | base64", "[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('secret'))"),
             "re": r"(base64|tobase64string)", "bravo": "c2VjcmV0 : ce n'est PAS un chiffrement, juste un emballage."},
            {"dit": "Ouvre le colis de la crypte.",
             "cmd": C(f"base64 -d {_p('crypte', 'colis.b64')}", f"certutil -decode {_p('crypte', 'colis.b64')} tresor.txt"),
             "re": r"(base64\s+(-d|--decode)|certutil\s+-decode).*colis",
             "bravo": "N'importe qui peut le déballer : base64 sert à transporter, pas à cacher."},
        ]},
        {"titre": "L'empreinte magique", "skill": "Hacheur",
         "prep": {_p("crypte", "a.txt"): "terminagotchi\n", _p("crypte", "b.txt"): "terminagotchI\n"}, "steps": [
            {"dit": "a.txt et b.txt ne diffèrent que d'une lettre. Compare leurs empreintes.",
             "cmd": C(f"sha256sum {_p('crypte', 'a.txt')} {_p('crypte', 'b.txt')}",
                      f"Get-FileHash {_p('crypte', 'a.txt')}, {_p('crypte', 'b.txt')}",
                      mac=f"shasum -a 256 {_p('crypte', 'a.txt')} {_p('crypte', 'b.txt')}"),
             "re": r"(sha256sum|get-filehash|shasum).*a\.txt",
             "bravo": "Une lettre change, toute l'empreinte change : l'effet avalanche. Et impossible de revenir en arrière."},
        ]},
        {"titre": "La blockchain à la main", "skill": "Forgeron de chaînes", "steps": [
            {"dit": "Écris le premier bloc du registre.",
             "cmd": C(f"echo 'bloc 1 : Alice donne 5 pommes à Bob' > {_p('crypte', 'bloc1.txt')}",
                      f"Set-Content {_p('crypte', 'bloc1.txt')} 'bloc 1 : Alice donne 5 pommes à Bob'"),
             "existe": _p("crypte", "bloc1.txt"), "bravo": "Bloc 1 posé."},
            {"dit": "Le bloc 2 commence par l'empreinte du bloc 1.",
             "cmd": C(f"sha256sum {_p('crypte', 'bloc1.txt')} > {_p('crypte', 'bloc2.txt')}",
                      f"(Get-FileHash {_p('crypte', 'bloc1.txt')}).Hash | Set-Content {_p('crypte', 'bloc2.txt')}"),
             "existe": _p("crypte", "bloc2.txt"), "bravo": "Le bloc 2 est accroché au bloc 1 par son empreinte."},
            {"dit": "Ajoute la transaction du bloc 2.",
             "cmd": C(f"echo 'bloc 2 : Bob donne 2 pommes à Zoé' >> {_p('crypte', 'bloc2.txt')}",
                      f"Add-Content {_p('crypte', 'bloc2.txt')} 'bloc 2 : Bob donne 2 pommes à Zoé'"),
             "re": r"(>>|add-content).*bloc2",
             "bravo": "Si quelqu'un trafique le bloc 1, son empreinte change et ne correspond plus au bloc 2 : "
                      "toute la chaîne crie au voleur. C'est ça, une blockchain !"},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ ⚙
    "Machines": {"stat": "Force", "icone": "🏭", "desc": "la Salle des Machines : matériel, démarrage, système, machines virtuelles, cloud",
                 "lecons": [
        {"titre": "Ouvrir le capot", "skill": "Mécano", "steps": [
            {"dit": "Quel est le cerveau de la machine (processeur) ?",
             "cmd": C("lscpu", "Get-CimInstance Win32_Processor", mac="sysctl -n machdep.cpu.brand_string",
                      android="cat /proc/cpuinfo"),
             "re": r"^(lscpu|get-ciminstance|gcim|sysctl|cat\s+/proc/cpuinfo|wmic)",
             "bravo": "Cœurs (cores) = les ouvriers ; fréquence (GHz) = leur vitesse."},
            {"dit": "Et la mémoire vive (RAM) ?",
             "cmd": C("free -h", "Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory,TotalVisibleMemorySize",
                      mac="vm_stat", android="free -h"),
             "re": r"^(free|get-ciminstance|gcim|vm_stat|cat\s+/proc/meminfo)",
             "bravo": "La RAM = la table de travail (rapide, s'efface à l'arrêt) ; le disque = l'armoire."},
        ]},
        {"titre": "Le réveil", "skill": "Réveilleur", "steps": [
            {"dit": "Depuis combien de temps la machine est-elle réveillée ?",
             "cmd": C("uptime", "(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime"),
             "re": r"^(uptime|\(get-date\)|get-uptime)", "bravo": "Au démarrage : firmware (BIOS/UEFI) → chargeur → noyau → services."},
            {"dit": "Quel noyau (le cœur du système) fait tourner tout ça ?",
             "cmd": C("uname -a", "[Environment]::OSVersion", android="uname -a"),
             "re": r"^(uname|\[environment\]|ver\b|systeminfo)", "bravo": "Le noyau parle au matériel ; tous les programmes passent par lui."},
        ]},
        {"titre": "Les machines dans la machine", "skill": "Virtualiseur", "steps": [
            {"dit": "Sommes-nous dans une vraie machine… ou une machine virtuelle ?",
             "cmd": C("systemd-detect-virt", "(gcim Win32_ComputerSystem).Model", mac="sysctl -n kern.hv_vmm_present"),
             "re": r"^(systemd-detect-virt|\(gcim|sysctl|virt-what|hostnamectl)",
             "bravo": "« none » = vraie machine. kvm, vmware, wsl… = une machine simulée par une autre : c'est la base du cloud."},
            {"dit": "Le cloud, ce sont des milliers de machines virtuelles louées à la minute. As-tu l'outil pour t'y connecter ?",
             "cmd": "ssh -V", "re": r"^ssh\b", "astuce": f"S'il manque : {installer('openssh-client')}",
             "bravo": "SSH = le câble invisible pour piloter une machine à distance, dans le cloud comme à la maison."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🔨
    "Forge": {"stat": "Intelligence", "icone": "🔨", "desc": "la Forge : programmer, son premier jeu, son site web, du son",
              "lecons": [
        {"titre": "Mon premier jeu", "skill": "Créateur de jeux", "prep": {_p("forge", "devine.py"): DEVINE_PY}, "steps": [
            {"dit": "Voici le code d'un petit jeu. Lis-le !",
             "cmd": C(f"cat {_p('forge', 'devine.py')}", f"Get-Content {_p('forge', 'devine.py')}"),
             "re": r"(cat|get-content|gc|less|more|type)\b.*devine", "bravo": "random, input, if/else : 3 briques et c'est un jeu."},
            {"dit": "Joue !", "cmd": C(f"python3 {_p('forge', 'devine.py')}", f"python {_p('forge', 'devine.py')}"),
             "re": r"python3?\b.*devine", "bravo": "Tu as lancé un programme Python écrit en 8 lignes."},
            {"dit": "Rends-le plus dur : change BORNE = 3 en BORNE = 10.",
             "cmd": C(f"nano {_p('forge', 'devine.py')}", f"notepad {_p('forge', 'devine.py')}"),
             "contient": (_p("forge", "devine.py"), "BORNE = 10"),
             "astuce": "Dans nano : modifie, puis Ctrl+O, Entrée (enregistrer) et Ctrl+X (quitter).",
             "bravo": "Tu as modifié un jeu : c'est comme ça que tout programmeur commence."},
        ]},
        {"titre": "Mon premier site", "skill": "Tisseur de web", "steps": [
            {"dit": "Écris une page web.",
             "cmd": C(f"echo '<h1>Le site de ma créature</h1>' > {_p('forge', 'index.html')}",
                      f"Set-Content {_p('forge', 'index.html')} '<h1>Le site de ma créature</h1>'"),
             "existe": _p("forge", "index.html"), "bravo": "<h1> = un grand titre. Le HTML range le texte dans des balises."},
            {"dit": "Allume un petit serveur web, ouvre http://localhost:8000 dans le navigateur, puis Ctrl+C pour l'éteindre.",
             "cmd": C(f"python3 -m http.server 8000 -d {_p('forge')}", f"python -m http.server 8000 -d {_p('forge')}"),
             "re": r"http\.server", "bravo": "Ton ordinateur est devenu un serveur web ! Un vrai site, c'est ça, sur une machine allumée en permanence."},
        ]},
        {"titre": "Faire du son", "skill": "Sonneur", "prep": {_p("forge", "bip.py"): BIP_PY}, "steps": [
            {"dit": "Un son = une vague de nombres. Lance le programme qui fabrique un La (440 Hz).",
             "cmd": C(f"python3 {_p('forge', 'bip.py')}", f"python {_p('forge', 'bip.py')}"),
             "existe": _p("forge", "bip.wav"),
             "bravo": "8000 mesures par seconde d'une sinusoïde : voilà un fichier son, fabriqué par toi."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🛠
    "Guilde": {"stat": "Endurance", "icone": "🛠", "desc": "la Guilde des Bâtisseurs Libres : open source, contribuer, compiler",
               "lecons": [
        {"titre": "Les règles du libre", "skill": "Compagnon", "prep": {_p("guilde", "LICENSE"): LICENCE}, "steps": [
            {"dit": "Chaque projet libre a une licence. Lis le début de celle-ci.",
             "cmd": C(f"head -n 3 {_p('guilde', 'LICENSE')}", f"Get-Content {_p('guilde', 'LICENSE')} -Head 3"),
             "re": r"(head|get-content|gc|cat)\b.*license", "bravo": "MIT : une des licences les plus simples."},
            {"dit": "Que permet-elle ? Cherche le mot « use ».",
             "cmd": C(f"grep -i use {_p('guilde', 'LICENSE')}", f"Select-String use {_p('guilde', 'LICENSE')}"),
             "re": r"(grep|select-string).*use", "bravo": "Utiliser, copier, modifier, partager : les 4 libertés du logiciel libre."},
        ]},
        {"titre": "Ma première contribution", "skill": "Contributeur",
         "prep": {_p("guilde", "projet", "bonjour.txt"): "Bonjur le monde !\n"}, "steps": [
            {"dit": "Il y a une faute dans le projet. Garde d'abord une copie de l'original.",
             "cmd": C(f"cp {_p('guilde', 'projet', 'bonjour.txt')} {_p('guilde', 'projet', 'bonjour.orig')}",
                      f"Copy-Item {_p('guilde', 'projet', 'bonjour.txt')} {_p('guilde', 'projet', 'bonjour.orig')}"),
             "existe": _p("guilde", "projet", "bonjour.orig"), "bravo": "L'original est à l'abri."},
            {"dit": "Corrige « Bonjur » en « Bonjour ».",
             "cmd": C(f"sed -i 's/Bonjur/Bonjour/' {_p('guilde', 'projet', 'bonjour.txt')}",
                      f"(Get-Content {_p('guilde', 'projet', 'bonjour.txt')}) -replace 'Bonjur','Bonjour' | Set-Content {_p('guilde', 'projet', 'bonjour.txt')}",
                      mac=f"sed -i '' 's/Bonjur/Bonjour/' {_p('guilde', 'projet', 'bonjour.txt')}"),
             "contient": (_p("guilde", "projet", "bonjour.txt"), "Bonjour"), "bravo": "Corrigé !"},
            {"dit": "Fabrique le patch : la recette de ta correction.",
             "cmd": C(f"diff -u {_p('guilde', 'projet', 'bonjour.orig')} {_p('guilde', 'projet', 'bonjour.txt')}",
                      f"Compare-Object (Get-Content {_p('guilde', 'projet', 'bonjour.orig')}) (Get-Content {_p('guilde', 'projet', 'bonjour.txt')})"),
             "re": r"^(diff|compare-object|fc)\b",
             "bravo": "- l'ancienne ligne, + la nouvelle : c'est ce qu'on propose à un projet (une « pull request »). "
                      "Terminagotchi lui-même est libre : tu peux y contribuer !"},
        ]},
        {"titre": "Compiler", "skill": "Fondeur", "prep": {_p("guilde", "bonjour.c"): BONJOUR_C}, "steps": [
            {"dit": "Le code C doit être traduit en langage machine : compile-le.",
             "cmd": f"cc {_p('guilde', 'bonjour.c')} -o {_p('guilde', 'bonjour')}",
             "re": r"^(cc|gcc|clang)\b.*bonjour\.c", "astuce": f"Pas de compilateur ? {installer('gcc')}",
             "bravo": "Le compilateur a transformé ton texte en programme."},
            {"dit": "Lance ton programme compilé.", "cmd": f"./{_p('guilde', 'bonjour')}", "re": r"bonjour(\.exe)?\s*$",
             "bravo": "Linux, Firefox, Python… tous compilés à partir de code ouvert à tous."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🔭
    "Observatoire": {"stat": "Intelligence", "icone": "🔭", "desc": "l'Observatoire de l'IA : comment une IA apprend, se trompe, et comment la piloter",
                     "lecons": [
        {"titre": "Apprendre en comptant", "skill": "Statisticien", "prep": {_p("ia", "avis.txt"): AVIS}, "steps": [
            {"dit": "Une IA apprend sur des exemples. Combien d'avis positifs ?",
             "cmd": C(f"grep -c positif {_p('ia', 'avis.txt')}", f"(Select-String positif {_p('ia', 'avis.txt')}).Count"),
             "re": r"(grep|select-string).*positif", "bravo": "5 positifs."},
            {"dit": "Quels mots reviennent le plus ? Compte-les tous.",
             "cmd": C(f"tr ' ' '\\n' < {_p('ia', 'avis.txt')} | sort | uniq -c | sort -rn | head",
                      f"(Get-Content {_p('ia', 'avis.txt')}) -split ' ' | Group-Object | Sort-Object Count -Descending | Select -First 10"),
             "re": r"(uniq\s+-c|group-object)",
             "bravo": "« j'adore » est lié aux avis positifs : un modèle apprend ces liens, sur des milliards de textes."},
        ]},
        {"titre": "Prédire le mot suivant", "skill": "Devin", "prep": {_p("ia", "texte.txt"): TEXTE_IA}, "steps": [
            {"dit": "Après « le chat », quel mot vient le plus souvent ?",
             "cmd": C(f"grep -o 'le chat [a-z]*' {_p('ia', 'texte.txt')} | sort | uniq -c | sort -rn",
                      f"Select-String -AllMatches 'le chat \\w+' {_p('ia', 'texte.txt')} | % {{ $_.Matches.Value }} | Group-Object"),
             "re": r"le chat.*(uniq|group-object)",
             "bravo": "« dort » (3 fois) : un modèle de langue prédit le mot le plus probable. Il ne « sait » pas, il calcule."},
        ]},
        {"titre": "Quand l'IA se trompe", "skill": "Détecteur de biais", "prep": {_p("ia", "biais.txt"): BIAIS}, "steps": [
            {"dit": "Les exemples d'entraînement sont-ils équilibrés ? Compte.",
             "cmd": C(f"sort {_p('ia', 'biais.txt')} | uniq -c", f"Get-Content {_p('ia', 'biais.txt')} | Group-Object"),
             "re": r"(uniq\s+-c|group-object)",
             "bravo": "4 « docteur : il » pour 1 « elle » : une IA entraînée là-dessus croira que les docteurs sont des hommes. "
                      "C'est un biais : l'IA répète les déséquilibres de ses données."},
        ]},
        {"titre": "Piloter un assistant", "skill": "Pilote d'IA", "prep": {_p("ia", "consigne.txt"): CONSIGNE}, "steps": [
            {"dit": "Lis cette consigne bien écrite pour un assistant IA.",
             "cmd": C(f"cat {_p('ia', 'consigne.txt')}", f"Get-Content {_p('ia', 'consigne.txt')}"),
             "re": r"(cat|get-content|gc|less|more)\b.*consigne",
             "bravo": "Rôle, contexte, tâche, format, vérification : une bonne consigne. Et toujours vérifier ce que l'IA répond !"},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 📊
    "Données": {"stat": "Endurance", "icone": "📊", "desc": "la Salle des Données : trier, compter, chercher, les bases de données (SQL)",
                "lecons": [
        {"titre": "Le tableau", "skill": "Archiviste des données", "prep": {_p("donnees", "creatures.csv"): CREATURES_CSV}, "steps": [
            {"dit": "Un fichier CSV : un tableau en texte. Regarde le début.",
             "cmd": C(f"head -n 5 {_p('donnees', 'creatures.csv')}", f"Get-Content {_p('donnees', 'creatures.csv')} -Head 5"),
             "re": r"(head|get-content|gc|cat)\b.*creatures", "bravo": "Une ligne = une créature, les virgules séparent les colonnes."},
            {"dit": "Combien de lignes ?",
             "cmd": C(f"wc -l {_p('donnees', 'creatures.csv')}", f"(Get-Content {_p('donnees', 'creatures.csv')}).Count"),
             "re": r"(wc\s+-l|\.count)", "bravo": "15 lignes : l'en-tête + 14 créatures."},
        ]},
        {"titre": "Trier et regrouper", "skill": "Trieur", "steps": [
            {"dit": "Combien de créatures par famille ? (colonne 2)",
             "cmd": C(f"cut -d, -f2 {_p('donnees', 'creatures.csv')} | sort | uniq -c",
                      f"Import-Csv {_p('donnees', 'creatures.csv')} | Group-Object famille"),
             "re": r"(cut\b.*uniq|group-object)", "bravo": "cut découpe une colonne, sort trie, uniq -c compte : un vrai rapport."},
            {"dit": "Les 3 plus grandes créatures (colonne 4, en nombres, à l'envers).",
             "cmd": C(f"sort -t, -k4 -n -r {_p('donnees', 'creatures.csv')} | head -n 3",
                      f"Import-Csv {_p('donnees', 'creatures.csv')} | Sort-Object {{[int]$_.taille_cm}} -Descending | Select -First 3"),
             "re": r"(sort\b.*-k\s*4|sort-object)", "bravo": "Chaosmère, 12 m ! -t, = séparateur, -k4 = colonne 4, -n = nombres."},
        ]},
        {"titre": "La base de données", "skill": "Maître du SQL", "steps": [
            {"dit": "Range le tableau dans une vraie base de données.",
             "cmd": f"sqlite3 {_p('donnees', 'base.db')} \".import --csv {_p('donnees', 'creatures.csv')} creatures\"",
             "existe": _p("donnees", "base.db"), "astuce": f"Si sqlite3 manque : {installer('sqlite3')}",
             "bravo": "Une base de données : des tableaux qu'on interroge avec le langage SQL."},
            {"dit": "Pose une question en SQL : combien par famille ?",
             "cmd": f"sqlite3 {_p('donnees', 'base.db')} \"SELECT famille, COUNT(*) FROM creatures GROUP BY famille;\"",
             "re": r"select\b.*from\b", "bravo": "SELECT … FROM … GROUP BY : la langue de presque toutes les bases du monde."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🎛
    "Contrôle": {"stat": "Force", "icone": "🎛", "desc": "le Poste de Contrôle : administrer un système Linux de A à Z",
                 "lecons": [
        {"titre": "Les habitants", "skill": "Concierge", "steps": [
            {"dit": "Qui suis-je, et dans quels groupes ?", "cmd": C("id", "whoami /groups"), "re": r"^(id|whoami)\b",
             "bravo": "uid = ton numéro, groupes = tes clés. sudo = le groupe des administrateurs."},
            {"dit": "Qui d'autre habite la machine ?", "cmd": C("cut -d: -f1 /etc/passwd", "Get-LocalUser"),
             "re": r"(/etc/passwd|get-localuser|net\s+user)", "bravo": "Beaucoup d'« utilisateurs » sont des services : chacun dans sa chambre."},
        ]},
        {"titre": "Les services", "skill": "Régisseur", "steps": [
            {"dit": "Quels services sont en panne ?", "cmd": C("systemctl --failed", "Get-Service | Where Status -eq Stopped"),
             "re": r"^(systemctl|get-service|gsv|service)\b", "bravo": "Un service = un programme qui tourne en fond (serveur web, impression…)."},
            {"dit": "Lis les dernières erreurs du journal système.", "cmd": C("journalctl -p err -n 20", "Get-EventLog System -EntryType Error -Newest 20"),
             "re": r"^(journalctl|get-eventlog|get-winevent|dmesg|tail\b.*/var/log)",
             "bravo": "Le journal raconte tout ce qui se passe : le premier réflexe d'un admin en cas de panne."},
        ]},
        {"titre": "Les tâches planifiées", "skill": "Horloger", "steps": [
            {"dit": "Quelles tâches reviennent toutes seules ?", "cmd": C("crontab -l", "Get-ScheduledTask | Select -First 10"),
             "re": r"^(crontab|get-scheduledtask|schtasks)\b",
             "bravo": "cron lance des commandes à heure fixe : « 0 3 * * * » = tous les jours à 3 h."},
            {"dit": "Des mises à jour en attente ?", "cmd": C("apt list --upgradable", "winget upgrade", mac="brew outdated"),
             "re": r"^(apt|dnf|pacman|winget|brew|pkg)\b",
             "bravo": "Mettre à jour = boucher les failles. C'est la règle n°1 de la sécurité."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🤖
    "Atelier": {"stat": "Agilité", "icone": "🤖", "desc": "l'Atelier : Raspberry Pi, robots, électronique embarquée",
                "lecons": [
        {"titre": "Allumer une LED", "skill": "Électronicien",
         "prep": {_p("atelier", "gpio17", "value"): "0\n", _p("atelier", "gpio17", "direction"): "out\n"}, "steps": [
            {"dit": "Sur un Raspberry Pi, une broche (GPIO) est un simple fichier ! Regarde l'état de la LED branchée sur la broche 17.",
             "cmd": C(f"cat {_p('atelier', 'gpio17', 'value')}", f"Get-Content {_p('atelier', 'gpio17', 'value')}"),
             "re": r"(cat|get-content|gc)\b.*gpio17", "bravo": "0 = éteinte. Sous Linux, « tout est fichier », même une broche électrique."},
            {"dit": "Allume-la : écris 1 dans le fichier.",
             "cmd": C(f"echo 1 > {_p('atelier', 'gpio17', 'value')}", f"Set-Content {_p('atelier', 'gpio17', 'value')} 1"),
             "contient": (_p("atelier", "gpio17", "value"), "1"), "bravo": "💡 Allumée ! Sur un vrai Pi, le courant passe dans la LED."},
            {"dit": "Fais-la clignoter 3 fois.",
             "cmd": C(f"for i in 1 2 3; do echo 1 > {_p('atelier', 'gpio17', 'value')}; sleep 1; echo 0 > {_p('atelier', 'gpio17', 'value')}; sleep 1; done",
                      f"1..3 | % {{ Set-Content {_p('atelier', 'gpio17', 'value')} 1; sleep 1; Set-Content {_p('atelier', 'gpio17', 'value')} 0; sleep 1 }}"),
             "re": r"(for\b|1\.\.3).*gpio17", "bravo": "Une LED qui clignote : le « Bonjour le monde » de l'électronique."},
        ]},
        {"titre": "Lire un capteur", "skill": "Capteur", "prep": {_p("atelier", "capteur", "temperature"): "21500\n"}, "steps": [
            {"dit": "Lis le capteur de température.",
             "cmd": C(f"cat {_p('atelier', 'capteur', 'temperature')}", f"Get-Content {_p('atelier', 'capteur', 'temperature')}"),
             "re": r"(cat|get-content|gc)\b.*temperature",
             "bravo": "21500 = 21,5 °C en millidegrés, comme dans /sys/class/thermal sur un vrai Pi."},
            {"dit": "Convertis en degrés.",
             "cmd": C(f"echo $(( $(cat {_p('atelier', 'capteur', 'temperature')}) / 1000 ))",
                      f"[int](Get-Content {_p('atelier', 'capteur', 'temperature')}) / 1000"),
             "re": r"/\s*1000", "bravo": "Un robot fait ça en boucle : lire un capteur, calculer, agir (moteur, LED…)."},
        ]},
    ]},
    # ------------------------------------------------------------------------------------------ 🔢
    "Nombres": {"stat": "Intelligence", "icone": "🔢", "desc": "les Ponts des Nombres : binaire, hexadécimal, octets, puissances",
                "lecons": [
        {"titre": "Le binaire", "skill": "Binariste", "steps": [
            {"dit": "Un ordinateur ne connaît que 0 et 1. Que vaut 101010 en binaire ?",
             "cmd": C("echo $((2#101010))", "[Convert]::ToInt32('101010', 2)"), "re": r"(2#[01]+|toint32\('[01]+',\s*2\))",
             "bravo": "42 ! 32 + 8 + 2 : chaque chiffre vaut le double du précédent."},
            {"dit": "Et 255 en hexadécimal (base 16) ?", "cmd": C("printf '%x\\n' 255", "'{0:x}' -f 255"),
             "re": r"(%x|\{0:x\})", "bravo": "ff : les couleurs #ff0000 (rouge) des pages web, c'est de l'hexadécimal !"},
        ]},
        {"titre": "Les octets", "skill": "Peseur d'octets", "steps": [
            {"dit": "Un kilo-octet informatique, c'est 2 puissance 10 octets. Calcule 1024 × 1024.",
             "cmd": C("echo $((1024 * 1024))", "1024 * 1024"), "re": r"1024\s*\*\s*1024",
             "bravo": "1 048 576 octets = 1 Mio. Bit, Octet, Kilo, Méga, Giga, Téra, Péta, Exa : ×1024 à chaque marche."},
            {"dit": "Les droits 644 de chmod sont un nombre en base 8. Que donne 420 (décimal) en octal ?",
             "cmd": C("printf '%o\\n' 420", "[Convert]::ToString(420, 8)"), "re": r"(%o|tostring\(420,\s*8\))",
             "bravo": "644 = rw-r--r-- : 6 = 4+2 (lire+écrire), 4 = lire. Les maths sont partout dans le terminal !"},
        ]},
    ]},
}
