"""Le lexique : toutes les commandes, rangées par chapitres et par univers.

  blanc     = déjà goûtée (sur n'importe lequel de tes appareils)
  gris      = à découvrir ici
  🔒 sombre = existe dans un autre univers (l'appli Android) : pas ici
"""
from .plateforme import BOLD, DIM, RESET, C, GEST, IS_WIN, OS_NAMES, OSK, fg, installer

ICI = "ici"
TEL = "telephone"


def _entrees():
    inst = installer("nom")
    return [
        ("🗂 Fichiers et dossiers", ICI, [
            ("pwd", "affiche le dossier où tu te trouves"),
            (C("ls", "dir"), "liste le contenu (" + C("ls -a : avec les cachés", "dir -Force : avec les cachés") + ")"),
            ("cd", "change de dossier (cd nom, cd .. pour remonter, cd ~ pour rentrer)"),
            ("mkdir", "crée un dossier"),
            (C("touch", "New-Item"), "crée un fichier vide"),
            (C("cp", "copy"), "copie un fichier"),
            (C("mv", "move"), "déplace ou renomme"),
            (C("rm", "del"), "supprime, sans corbeille !"),
            (C("chmod", "attrib"), "change les droits / protège un fichier"),
            ("tree", "affiche l'arborescence"),
        ]),
        ("🔎 Lire et chercher", ICI, [
            (C("cat", "type"), "affiche le contenu d'un fichier"),
            (C("less", "more"), "lit un long fichier page par page"),
            (C("head", "Get-Content"), "affiche le début d'un fichier"),
            (C("grep", "Select-String"), "cherche un mot dans des fichiers"),
            (C("find", "Get-ChildItem"), "trouve des fichiers par leur nom"),
            (C("wc", "Measure-Object"), "compte lignes et mots"),
            (C("sort", "Sort-Object"), "trie des lignes"),
        ]),
        ("⚙ Système", ICI, [
            ("whoami", "ton nom d'utilisateur"),
            (C("date", "Get-Date"), "la date et l'heure"),
            (C("ps", "Get-Process"), "les programmes en cours"),
            (C("htop", "tasklist", mac="top"), "les programmes en direct"),
            (C("kill", "Stop-Process"), "arrête un programme"),
            (C("df", "Get-PSDrive"), "l'espace disque libre"),
            (C("du", "Measure-Object"), "la taille d'un dossier"),
            (C("sudo", "winget"), "agir en administrateur / installer : " + inst),
        ]),
        ("🌐 Réseau", ICI, [
            ("ping", "teste la connexion"),
            (C("curl", "curl.exe"), "parle aux sites web (la base du CTF web !)"),
            (C("ip", "ipconfig", mac="ifconfig"), "ton adresse IP"),
            ("nslookup", "l'annuaire d'internet (DNS)"),
            ("ssh", "se connecter à une autre machine"),
        ]),
        ("🌿 Git et 🧪 scripts", ICI, [
            ("git", "garde l'historique de tes fichiers"),
            (C("bash", "powershell"), "lance un script"),
            (C("alias", "function"), "crée ta propre commande"),
            (C("python3", "python"), "programme en Python"),
            (C("nano", "notepad"), "édite un fichier texte"),
        ]),
        ("🌍 Recensement (sur tous tes appareils)", ICI, [
            ("tg", "tg compte · tg sync · tg drapeau TG{…} · tg lexique"),
        ]),
        ("📱 Ton téléphone (appli Android)", TEL, [
            ("ouvre", "lance une appli : ouvre whatsapp"),
            ("applis", "liste tes applis"),
            ("sms", "prépare un SMS"),
            ("lampe", "lampe torche on/off"),
            ("dis", "le téléphone parle"),
            ("web", "ouvre un site"),
            ("carte", "cherche un lieu"),
        ]),
        ("🎮 Jeux de l'appli Android", TEL, [
            ("donjon", "donjon aléatoire dans de vrais dossiers"),
            ("ctf", "7 épreuves de hacker hors ligne"),
            ("doom", "ton Doom-like en 3D"),
            ("edite", "l'éditeur de texte de l'appli"),
            ("caresse", "un câlin pour ta créature"),
            ("joue", "pierre-feuille-ciseaux"),
        ]),
    ]


def lignes(state):
    vus = {c.lower() for c in state.get("seen", [])}
    ici = OS_NAMES.get(OSK, "PC")
    sortie = []
    total = 0
    goutees = 0
    for titre, univers, commandes in _entrees():
        autre = univers == TEL and OSK != "android"
        sortie.append("")
        sortie.append(f"{fg(147)}{BOLD}{titre}{RESET}" + (f" {DIM}(pas ici sur {ici}){RESET}" if autre else ""))
        for cmd, desc in commandes:
            mot = cmd.split()[0].lower()
            gout = mot in vus
            if autre:
                sortie.append(f"  {fg(238)}🔒 {cmd:<15} {desc}{RESET}")
                continue
            total += 1
            goutees += gout
            if gout:
                sortie.append(f"  {fg(255)}● {BOLD}{cmd:<15}{RESET}{fg(255)} {desc}{RESET}")
            else:
                sortie.append(f"  {fg(244)}○ {cmd:<15} {desc}{RESET}")
    entete = [f" {fg(213)}── 📖 Lexique ({ici}) ── goûtées : {goutees}/{total}{RESET}",
              f" {DIM}blanc = déjà tapée (sur n'importe quel appareil) · gris = à découvrir · 🔒 = autre univers{RESET}"]
    return entete + sortie
