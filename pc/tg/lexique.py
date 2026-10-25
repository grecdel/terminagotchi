"""Le lexique : toutes les commandes, rangées par chapitres et par univers.

  blanc     = déjà goûtée (sur n'importe lequel de tes appareils)
  gris      = à découvrir ici
  🔒 sombre = existe dans un autre univers (l'appli Android) : pas ici

Fil rouge : l'ordinateur est une grande maison que la créature visite avec l'enfant.
Chaque commande a une IMAGE (la maison) et une explication TECHNIQUE ; l'affichage
suit le palier de vocabulaire (voir mots.py) : l'image seule, puis l'image et la
technique côte à côte, puis la technique avec l'image en petit rappel.
Les mêmes phrases existent dans l'appli Android (Regles.LEXIQUE dans Jeu.kt).
"""
from .mots import palier
from .plateforme import BOLD, DIM, RESET, C, OS_NAMES, OSK, fg, installer

ICI = "ici"
TEL = "telephone"


def _entrees():
    inst = installer("nom")
    return [
        ("🗂 Fichiers et dossiers", ICI, [
            ("pwd", "le point rouge « vous êtes ici » sur le plan de la maison",
             "affiche le dossier où tu te trouves"),
            (C("ls", "dir"), "j'ouvre les yeux et je regarde dans la pièce ("
             + C("ls -a", "dir -Force") + " : même sous le tapis)",
             "liste le contenu (" + C("ls -a : avec les cachés", "dir -Force : avec les cachés") + ")"),
            ("cd", "je passe une porte (cd .. : je recule d'une pièce, cd ~ : je rentre dans ma chambre)",
             "change de dossier (cd nom, cd .. pour remonter, cd ~ pour rentrer)"),
            ("mkdir", "je construis une nouvelle pièce", "crée un dossier"),
            (C("touch", "New-Item"), "je pose une feuille blanche sur la table", "crée un fichier vide"),
            (C("cp", "copy"), "je fais une photocopie d'une feuille", "copie un fichier"),
            (C("mv", "move"), "je porte une feuille ailleurs, ou je change son étiquette", "déplace ou renomme"),
            (C("rm", "del"), "la broyeuse : pas de poubelle, c'est perdu pour toujours !", "supprime, sans corbeille !"),
            (C("chmod", "attrib"), "un cadenas sur la boîte", "change les droits / protège un fichier"),
            ("tree", "le plan de toute la maison", "affiche l'arborescence des dossiers"),
        ]),
        ("🔎 Lire et chercher", ICI, [
            (C("cat", "type"), "je lis la lettre à voix haute", "affiche le contenu d'un fichier"),
            (C("less", "more"), "je lis un gros livre, page après page", "lit un long fichier page par page"),
            (C("head", "Get-Content"), "je lis juste le haut de la lettre", "affiche le début d'un fichier"),
            (C("grep", "Select-String"), "la loupe du détective : elle trouve un mot dans les lettres",
             "cherche un mot dans des fichiers"),
            (C("find", "Get-ChildItem"), "je cherche un objet dans toutes les pièces", "trouve des fichiers par leur nom"),
            (C("wc", "Measure-Object"), "je compte les lignes et les mots de la lettre", "compte lignes et mots"),
            (C("sort", "Sort-Object"), "je range les lignes dans l'ordre, comme un dictionnaire", "trie des lignes"),
        ]),
        ("⚙ Système", ICI, [
            ("whoami", "mon prénom d'habitant de la maison", "ton nom d'utilisateur"),
            (C("date", "Get-Date"), "je regarde l'horloge de la maison", "la date et l'heure"),
            (C("ps", "Get-Process"), "qui est réveillé dans la maison ?", "les programmes en cours (processus)"),
            (C("htop", "tasklist", mac="top"), "qui est réveillé, en direct, comme une caméra",
             "les programmes en direct"),
            (C("kill", "Stop-Process"), "j'envoie un programme se coucher", "arrête un programme"),
            (C("df", "Get-PSDrive"), "la place qui reste dans les placards", "l'espace disque libre"),
            (C("du", "Measure-Object"), "je pèse une pièce et tout ce qu'elle contient", "la taille d'un dossier"),
            (C("sudo", "winget"), "la clé du gardien, pour les gros travaux comme installer : " + inst,
             "agir en administrateur / installer : " + inst),
        ]),
        ("🌐 Réseau", ICI, [
            ("ping", "je crie « Ohé ! » et j'attends l'écho", "teste la connexion"),
            (C("curl", "curl.exe"), "le facteur qui va chercher une lettre sur un site",
             "parle aux sites web (la base du CTF web !)"),
            (C("ip", "ipconfig", mac="ifconfig"), "l'adresse de la maison", "ton adresse IP"),
            ("nslookup", "l'annuaire des maisons d'internet", "l'annuaire d'internet (DNS)"),
            ("ssh", "un tunnel secret vers une autre maison", "se connecter à une autre machine"),
        ]),
        ("🌿 Git et 🧪 scripts", ICI, [
            ("git", "un appareil photo qui garde une photo de tes fichiers à chaque étape",
             "garde l'historique de tes fichiers"),
            (C("bash", "powershell"), "une recette que la maison sait suivre toute seule", "lance un script"),
            (C("alias", "function"), "je donne un surnom à une commande", "crée ta propre commande"),
            (C("python3", "python"), "j'apprends une nouvelle langue à la maison : Python", "programme en Python"),
            (C("nano", "notepad"), "mon cahier pour écrire dans une feuille", "édite un fichier texte"),
        ]),
        ("🌍 Recensement (sur tous tes appareils)", ICI, [
            ("tg", "le registre de la maison : tg compte · tg sync · tg drapeau TG{…} · tg lexique",
             "tg compte · tg sync · tg drapeau TG{…} · tg lexique"),
            ("tg site", "la vitrine de ta maison sur internet : tg site bestiaire · tg site captures",
             "ouvre le site (ton profil) · tg site bestiaire · tg site captures"),
            ("tg collection", "l'album de tes bestioles (et leurs signes uniques)",
             "tes bestioles capturées (et leurs signes uniques)"),
            ("tg bestiaire", "le grand livre des espèces : tg bestiaire Glitchou", "la fiche d'une espèce : tg bestiaire Glitchou"),
        ]),
        ("📱 Ton téléphone (appli Android)", TEL, [
            ("ouvre", "j'allume une appli, comme on allume la télé : ouvre whatsapp", "lance une appli : ouvre whatsapp"),
            ("applis", "la liste de toutes les applis qui habitent le téléphone", "liste tes applis"),
            ("sms", "j'écris un petit mot, tu n'as plus qu'à l'envoyer", "prépare un SMS"),
            ("lampe", "l'interrupteur de la lampe de poche", "lampe torche on/off"),
            ("dis", "le téléphone lit ta phrase à voix haute", "le téléphone parle"),
            ("web", "j'ouvre la fenêtre sur un site", "ouvre un site"),
            ("carte", "je déplie la carte du monde pour trouver un lieu", "cherche un lieu"),
        ]),
        ("🎮 Jeux de l'appli Android", TEL, [
            ("donjon", "une cave aux mille pièces, pleine de trésors", "donjon aléatoire dans de vrais dossiers"),
            ("ctf", "la chasse au trésor : 7 énigmes de détective", "7 épreuves de hacker hors ligne (CTF)"),
            ("doom", "un labyrinthe en 3D que tu dessines toi-même", "ton Doom-like en 3D"),
            ("edite", "mon cahier pour écrire dans une feuille", "l'éditeur de texte de l'appli"),
            ("caresse", "un câlin pour ta créature", "un câlin pour ta créature"),
            ("joue", "pierre-feuille-ciseaux", "pierre-feuille-ciseaux"),
        ]),
    ]


def explication(image, technique, p):
    """Palier 0 : l'image · palier 1 : l'image — la technique · palier 2 : la technique (l'image)."""
    if p <= 0 or image == technique:
        return image
    if p == 1:
        return f"{image} {DIM}— {technique}{RESET}"
    return f"{technique} {DIM}({image}){RESET}"


def lignes(state):
    vus = {c.lower() for c in state.get("seen", [])}
    ici = OS_NAMES.get(OSK, "PC")
    p = palier(state)
    sortie = []
    total = 0
    goutees = 0
    for titre, univers, commandes in _entrees():
        autre = univers == TEL and OSK != "android"
        sortie.append("")
        sortie.append(f"{fg(147)}{BOLD}{titre}{RESET}" + (f" {DIM}(pas ici sur {ici}){RESET}" if autre else ""))
        for cmd, image, technique in commandes:
            mot = cmd.split()[0].lower()
            gout = mot in vus
            if autre:
                sortie.append(f"  {fg(238)}🔒 {cmd:<15} {image}{RESET}")
                continue
            total += 1
            goutees += gout
            desc = explication(image, technique, p)
            if gout:
                sortie.append(f"  {fg(255)}● {BOLD}{cmd:<15}{RESET}{fg(255)} {desc}{RESET}")
            else:
                sortie.append(f"  {fg(244)}○ {cmd:<15} {desc}{RESET}")
    entete = [f" {fg(213)}── 📖 Lexique ({ici}) ── goûtées : {goutees}/{total}{RESET}",
              f" {DIM}blanc = déjà tapée (sur n'importe quel appareil) · gris = à découvrir · 🔒 = autre univers{RESET}"]
    return entete + sortie


def images():
    """{commande : image} pour la recherche « / » (commandes Linux/Mac et Windows)."""
    out = {}
    for _t, _u, commandes in _entrees():
        for cmd, image, _tech in commandes:
            out.setdefault(cmd.split()[0].lower(), image)
    return out
