"""Registre de commandes + recherche intelligente en français.

On peut chercher une commande par son nom (« grep ») ou décrire ce qu'on veut faire
(« supprimer un dossier », « voir les fichiers cachés »). Aucune IA externe :
synonymes + racines de mots + score de correspondance, 100 % hors ligne.
"""
import re
import unicodedata

from . import core, lexique
from .plateforme import BOLD, DIM, GEST, INSTALL, IS_WIN, OSK, RESET, C, fg, installer, piege

# ================================================================ registre

def E(unix, win, desc, kw="", danger=False, note=None, mac=None, android=None):
    return {"type": "cmd", "cmd": C(unix, win, mac, android), "desc": desc, "kw": kw,
            "danger": danger, "note": note,
            "noms": {x.split()[0].lower() for x in (unix, win, mac, android) if x}}


def R(titre, kw, steps):
    return {"type": "recette", "titre": titre, "kw": kw,
            "steps": [(C(*s[:2]) if len(s) == 3 else C(*s[:-1]), s[-1]) for s in steps]}


LAUNCHER = "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
NOTE_ANDROID = None if OSK == "android" else "Android uniquement (dans Termux)."


def A(cmd, desc, kw, danger=False):
    """Commande propre à Android/Termux."""
    e = E(cmd, cmd, desc, kw, danger=danger, note=NOTE_ANDROID)
    e["android"] = True
    return e


def RA(titre, kw, steps):
    r = {"type": "recette", "titre": titre + ("" if OSK == "android" else " (Android)"), "kw": kw, "steps": steps,
         "android": True}
    return r


REGISTRE = [
    # --- navigation
    E("pwd", "pwd", "Afficher le dossier où tu te trouves", "ou suis position actuel chemin"),
    E("ls", "dir", "Lister le contenu d'un dossier", "voir fichier dossier contenu lister ici"),
    E("ls -a", "dir -Force", "Voir aussi les fichiers cachés", "voir fichier cache invisible secret masque"),
    E("ls -l", "dir", "Lister avec les détails (taille, date, droits)", "voir detail taille date droit"),
    E("cd dossier", "cd dossier", "Aller dans un dossier", "aller entrer naviguer dossier changer"),
    E("cd ..", "cd ..", "Remonter au dossier parent", "remonter revenir retour parent precedent dossier"),
    E("cd ~", "cd ~", "Revenir à ton dossier perso", "revenir maison perso accueil home"),
    E("tree", "tree /f", "Voir le plan de tous les dossiers (l'arborescence)", "arbre arborescence structure voir dossier plan",
      note=None if IS_WIN else f"S'il est absent : {installer('tree')}"),
    # --- fichiers et dossiers
    E("mkdir nom", "mkdir nom", "Créer un dossier", "creer dossier"),
    E("mkdir -p a/b/c", "mkdir a\\b\\c", "Créer plusieurs dossiers imbriqués d'un coup", "creer dossier imbrique plusieurs sous"),
    E("touch fichier.txt", "New-Item fichier.txt", "Créer un fichier vide", "creer fichier vide"),
    E('echo "texte" > fichier.txt', 'echo "texte" > fichier.txt', "Écrire du texte dans un fichier (l'écrase)",
      "ecrire texte fichier remplacer", danger=True),
    E('echo "texte" >> fichier.txt', 'echo "texte" >> fichier.txt', "Ajouter du texte à la fin d'un fichier",
      "ajouter ecrire texte fin fichier"),
    E("cat fichier.txt", "cat fichier.txt", "Afficher le contenu d'un fichier", "lire voir contenu fichier ouvrir"),
    E("less fichier.txt", "more fichier.txt", "Lire un long fichier page par page", "lire long page fichier defiler"),
    E("head -n 5 fichier.txt", "Get-Content fichier.txt -Head 5", "Voir les premières lignes d'un fichier",
      "debut premier ligne fichier voir"),
    E("tail -n 5 fichier.txt", "Get-Content fichier.txt -Tail 5", "Voir les dernières lignes d'un fichier",
      "fin dernier ligne fichier voir log"),
    E("cp source copie", "cp source copie", "Copier un fichier", "copier fichier"),
    E("cp -r dossier copie", "cp -r dossier copie", "Copier un dossier entier", "copier dossier entier tout"),
    E("mv ancien nouveau", "mv ancien nouveau", "Renommer un fichier ou un dossier", "renommer nom fichier dossier changer"),
    E("mv fichier dossier/", "mv fichier dossier\\", "Déplacer un fichier dans un dossier", "deplacer fichier dossier ranger"),
    E("rm fichier", "rm fichier", "Supprimer un fichier (sans corbeille !)", "supprimer fichier", danger=True),
    E("rm -r dossier", "rm -r dossier", "Supprimer un dossier et tout son contenu", "supprimer dossier tout entier", danger=True),
    E("rmdir dossier", "rmdir dossier", "Supprimer un dossier vide", "supprimer dossier vide"),
    # --- recherche
    E('grep "mot" fichier.txt', 'Select-String "mot" fichier.txt', "Chercher un mot dans un fichier",
      "chercher mot texte fichier dans"),
    E('grep -r "mot" .', 'Get-ChildItem -Recurse | Select-String "mot"', "Chercher un mot dans tous les fichiers d'un dossier",
      "chercher mot texte tout fichier dossier partout"),
    E('find . -name "*.txt"', "Get-ChildItem -Recurse -Filter *.txt", "Trouver des fichiers par leur nom",
      "chercher trouver fichier nom perdu ou"),
    # --- protections
    E("ls -l fichier", "attrib fichier", "Voir les droits d'un fichier", "voir droit proteger qui"),
    E("chmod 444 fichier", "attrib +r fichier", "Protéger un fichier (lecture seule)", "proteger fichier lecture seule"),
    E("chmod 644 fichier", "attrib -r fichier", "Enlever la protection d'un fichier", "enlever retirer proteger modifier deproteger"),
    E("chmod +x script.sh", "Unblock-File script.ps1", "Autoriser une recette (un script) à se lancer toute seule",
      "executable rendre lancer script autoriser recette"),
    # --- système
    E("whoami", "whoami", "Afficher ton nom d'utilisateur", "qui utilisateur nom moi"),
    E("date", "Get-Date", "Afficher la date et l'heure", "heure date"),
    E("ps aux", "Get-Process", "Voir les programmes qui tournent", "voir processus tourne", android="ps"),
    E("top", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
      "Voir ce qui consomme le plus", "consomme lent ralentit processus ressource cpu"),
    E("kill PID", "Stop-Process -Id PID", "Arrêter un programme (par son numéro)", "arreter processus bloque", danger=True),
    E("pkill nom", "Stop-Process -Name nom", "Arrêter un programme par son nom", "arreter processus nom bloque", danger=True),
    E("df -h", "Get-PSDrive", "Voir l'espace libre sur le disque", "espace libre"),
    E("du -sh dossier", "(Get-ChildItem dossier -Recurse | Measure-Object Length -Sum).Sum",
      "Connaître la taille d'un dossier", "taille dossier espace"),
    E("free -h", "Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory",
      "Voir la mémoire libre de la maison (la RAM)", "memoire vive ram libre", mac="vm_stat"),
    E("uname -a", "systeminfo", "Informations sur le système", "info systeme version machine"),
    E("clear", "cls", "Nettoyer l'écran du terminal", "nettoyer"),
    E("history", "history", "Voir les commandes tapées avant", "historique"),
    E("man commande", "Get-Help commande", "Lire le manuel d'une commande", "aide"),
    E(installer("nom"), "winget install nom", "Installer un logiciel", "installer"),
    E(f"{INSTALL.get(GEST, 'sudo apt install').replace('install', 'remove').replace('-S', '-R').replace(' add', ' del')} nom",
      "winget uninstall nom", "Désinstaller un logiciel", "supprimer desinstaller", danger=True,
      mac="brew uninstall nom", android="pkg uninstall nom"),
    E({"dnf": "sudo dnf upgrade", "pacman": "sudo pacman -Syu", "zypper": "sudo zypper update",
       "apk": "sudo apk upgrade"}.get(GEST, "sudo apt update && sudo apt upgrade"),
      "winget upgrade --all", "Mettre à jour tous les logiciels", "mettre jour mise niveau logiciel tout",
      mac="brew upgrade", android="pkg upgrade"),
    E(f"{'dnf search' if GEST == 'dnf' else 'pacman -Ss' if GEST == 'pacman' else 'apt search'} nom",
      "winget search nom", "Chercher un logiciel à installer", "chercher installer logiciel",
      mac="brew search nom", android="pkg search nom"),
    # --- réseau
    E("ping -c 3 example.com", "ping -n 3 example.com", "Tester si internet marche", "tester internet marche"),
    E("ip a", "ipconfig", "Voir ton adresse IP", "voir ip", mac="ifconfig", android="ifconfig"),
    E("curl -I https://site.com", "curl.exe -I https://site.com", "Vérifier si un site répond", "verifier site repond marche internet"),
    E("curl -o fichier https://site.com/fichier", "curl.exe -o fichier https://site.com/fichier",
      "Télécharger un fichier", "telecharger fichier internet"),
    E("nslookup site.com", "nslookup site.com", "Trouver l'adresse d'un site dans l'annuaire", "trouver ip site dns adresse annuaire"),
    E("ssh utilisateur@machine", "ssh utilisateur@machine", "Se connecter à une autre machine à distance",
      "connecter distance autre machine serveur"),
    # --- git
    E("git init", "git init", "Fabriquer un album photo git pour tes fichiers", "creer git depot album"),
    E("git status", "git status", "Voir l'état des fichiers suivis", "voir git etat modifie"),
    E("git add fichier", "git add fichier", "Préparer un fichier pour le prochain souvenir", "git preparer ajouter"),
    E('git commit -m "message"', 'git commit -m "message"', "Prendre une photo de tes fichiers (un souvenir)", "git enregistrer sauvegarder version photo"),
    E("git log", "git log", "Voir l'historique des versions", "git historique"),
    E("git diff", "git diff", "Voir ce qui a changé", "git voir modifie"),
    E("git clone https://...", "git clone https://...", "Récupérer un projet existant", "git telecharger recuperer projet"),
    # --- scripts / commandes perso
    E("alias nom='commande'", "function nom { commande }", "Créer ta propre commande (raccourci)", "creer commande"),
    E("sh script.sh", "powershell -ExecutionPolicy Bypass -File script.ps1", "Lancer un script", "lancer script executer"),
    # --- Android (Termux) : piloter le téléphone
    A("termux-open-url https://site.com", "Ouvrir un site ou un lien (Android choisit l'appli)",
      "ouvrir site lien navigateur internet youtube"),
    A(f"{LAUNCHER} nom.du.paquet", "Lancer une application avec son nom secret", "lancer ouvrir demarrer application paquet"),
    A("pm list packages | grep nom", "Trouver le nom secret d'une application installée",
      "trouver chercher liste application installe nom paquet"),
    A('am start -a android.intent.action.VIEW -d "geo:0,0?q=lieu"', "Chercher un lieu dans les cartes",
      "carte lieu itineraire gps endroit"),
    A("am start -a android.intent.action.DIAL -d tel:0612345678", "Préparer un appel (sans appeler)",
      "telephone numero"),
    A('am start -a android.intent.action.SENDTO -d sms:0612345678 --es sms_body "Salut"', "Préparer un SMS",
      "sms envoyer"),
    A("am start -a android.intent.action.SENDTO -d mailto:ami@exemple.fr", "Écrire un e-mail", "mail envoyer ecrire"),
    A("am start -a android.settings.SETTINGS", "Ouvrir les réglages du téléphone", "ouvrir reglage telephone"),
    A("am start -a android.settings.WIFI_SETTINGS", "Ouvrir les réglages Wi-Fi", "ouvrir reglage wifi"),
    A("am start -a android.settings.BLUETOOTH_SETTINGS", "Ouvrir les réglages Bluetooth", "ouvrir reglage bluetooth"),
    A("termux-torch on", "Allumer la lampe torche (off pour éteindre)", "allumer eteindre lampe"),
    A("termux-battery-status", "Voir l'état de la batterie", "voir batterie"),
    A("termux-volume music 10", "Régler le volume (0 à 15)", "regler volume"),
    A("termux-brightness 128", "Régler la luminosité (0 à 255)", "regler luminosite ecran"),
    A('termux-tts-speak "Bonjour"', "Faire parler le téléphone", "parler lire voix haute"),
    A("termux-vibrate -d 500", "Faire vibrer (le vibreur)", "vibrer"),
    A('termux-toast "Coucou"', "Afficher un petit message à l'écran", "afficher message ecran"),
    A("termux-clipboard-get", "Voir le contenu du presse-papier", "voir presse papier copier"),
    A('termux-clipboard-set "texte"', "Mettre un texte dans le presse-papier", "copier presse papier texte"),
    A("termux-share fichier", "Partager un fichier (WhatsApp, mail…)", "partager envoyer fichier"),
    A("termux-open fichier", "Ouvrir un fichier avec son appli (PDF, photo…)", "ouvrir fichier pdf photo image"),
    A("termux-camera-photo photo.jpg", "Prendre une photo", "prendre photo"),
    A("termux-wifi-connectioninfo", "Infos sur le Wi-Fi connecté", "voir wifi info"),
    A("termux-setup-storage", "Donner à Termux l'accès à tes fichiers (Téléchargements, photos…)",
      "acces fichier telechargement stockage autoriser"),
    # --- recettes : suites de commandes
    R("Créer un dossier et entrer dedans", "creer dossier entrer aller", [
        ("mkdir projet", "mkdir projet", "crée le dossier"),
        ("cd projet", "cd projet", "entre dedans")]),
    R("Renommer un fichier en sécurité", "renommer fichier securite", [
        ("ls", "dir", "vérifie le nom exact"),
        ("mv ancien.txt nouveau.txt", "mv ancien.txt nouveau.txt", "renomme"),
        ("ls", "dir", "vérifie le résultat")]),
    R("Faire une sauvegarde avant de modifier", "copier sauvegarde modifier avant securite", [
        ("cp fichier.txt fichier.txt.bak", "cp fichier.txt fichier.txt.bak", "photocopie de secours"),
        ("nano fichier.txt", "notepad fichier.txt", "modifie tranquillement l'original")]),
    R("Supprimer un dossier sans faire de bêtise", "supprimer dossier securite tout", [
        ("ls dossier", "dir dossier", "regarde d'abord ce qu'il contient"),
        ("rm -r dossier", "rm -r dossier", "la broyeuse : c'est irréversible !"),
        ("ls", "dir", "vérifie qu'il a disparu")]),
    R("Retrouver un fichier perdu et le lire", "chercher trouver fichier perdu lire", [
        ('find ~ -name "*nom*"', "Get-ChildItem ~ -Recurse -Filter *nom*", "cherche partout chez toi"),
        ("cat chemin/trouvé", "cat chemin\\trouvé", "affiche son contenu")]),
    R("Protéger un fichier important", "proteger fichier important", [
        ("chmod 444 fichier", "attrib +r fichier", "lecture seule"),
        ("ls -l fichier", "attrib fichier", "vérifie la protection")]),
    R("Vérifier que internet fonctionne", "tester internet marche connexion", [
        ("ping -c 3 example.com", "ping -n 3 example.com", "le réseau répond-il ?"),
        ("curl -I https://example.com", "curl.exe -I https://example.com", "les sites répondent-ils ?")]),
    R("Libérer de l'espace disque", "espace plein liberer disque", [
        ("df -h", "Get-PSDrive", "combien reste-t-il ?"),
        ("du -sh * | sort -h", "Get-ChildItem | Sort-Object Length", "qu'est-ce qui pèse lourd ici ?"),
        ("rm gros_fichier", "rm gros_fichier", "supprime ce qui est inutile (prudence !)")]),
    R("Arrêter un programme bloqué", "arreter processus bloque", [
        ("ps aux | grep nom", "Get-Process nom", "trouve son numéro"),
        ("kill PID", "Stop-Process -Name nom", "envoie-le se coucher")]),
    R("Commencer un projet avec git", "creer projet git commencer", [
        ("mkdir projet", "mkdir projet", "crée le dossier"),
        ("cd projet", "cd projet", "entre dedans"),
        ("git init", "git init", "sors l'appareil photo git"),
        ("git add .", "git add .", "prépare tous les fichiers"),
        ('git commit -m "début"', 'git commit -m "début"', "clic : la première photo")]),
    R("Télécharger un fichier dans un dossier", "telecharger fichier dossier internet", [
        ("cd dossier", "cd dossier", "va dans le bon dossier"),
        ("curl -o fichier https://site.com/fichier", "curl.exe -o fichier https://site.com/fichier", "télécharge")]),
    R("Créer et lancer un script", "creer script lancer automatiser", [
        ("echo 'echo Bonjour' > script.sh", "echo 'Write-Output Bonjour' > script.ps1", "écris la recette"),
        ("chmod +x script.sh", "Unblock-File script.ps1", "autorise-la à cuisiner"),
        ("./script.sh", "powershell -ExecutionPolicy Bypass -File script.ps1", "la maison la suit toute seule")]),
    RA("Lancer une appli dont je ne connais pas le nom", "lancer ouvrir application nom trouver", [
        ("pm list packages | grep -i youtube", "cherche son paquet avec un mot de son nom"),
        (f"{LAUNCHER} com.google.android.youtube", "allume-la avec son nom secret")]),
    RA("Créer ma commande « ouvre » pour lancer les applis", "creer commande lancer ouvrir application", [
        (f"echo 'ouvre() {{ {LAUNCHER} \"$1\"; }}' >> ~/.bashrc", "enregistre la commande"),
        ("source ~/.bashrc", "la maison relit son carnet"),
        ("ouvre com.android.settings", "utilise-la avec n'importe quel nom secret")]),
    RA("Récupérer un fichier téléchargé dans Termux", "recuperer fichier telechargement copier", [
        ("termux-setup-storage", "autorise l'accès (une seule fois)"),
        ("ls ~/storage/downloads", "regarde tes téléchargements"),
        ("cp ~/storage/downloads/fichier ~/", "copie-le chez toi")]),
    R("Créer ta propre commande pour toujours", "creer commande toujours permanent", [
        ("alias salut='echo Salut !'", "function salut { 'Salut !' }", "invente-la"),
        (f"echo \"alias salut='echo Salut !'\" >> ~/.bashrc", "Add-Content $PROFILE \"function salut { 'Salut !' }\"",
         "enregistre-la dans ta configuration")]),
]

for _e in REGISTRE:
    if _e["type"] == "cmd":
        core.NOMS_CONNUS.update(_e["noms"])

# ================================================================ moteur de recherche

SYNONYMES = {
    "dossier": "dossier repertoire folder directory rep",
    "fichier": "fichier file document doc texte txt",
    "creer": "creer cree creation fabriquer nouveau nouvelle generer construire init",
    "supprimer": "supprimer supprime effacer efface enlever detruire delete virer jeter",
    "voir": "voir afficher affiche lister liste montrer regarder visualiser",
    "copier": "copier copie dupliquer duplique",
    "sauvegarde": "sauvegarde sauvegarder backup bak",
    "deplacer": "deplacer deplace bouger ranger move",
    "renommer": "renommer renomme rename",
    "chercher": "chercher cherche trouver trouve rechercher recherche localiser retrouver",
    "lire": "lire ouvrir lecture read",
    "proteger": "proteger protege verrouiller bloquer securiser",
    "droit": "droit droits permission permissions acces",
    "internet": "internet reseau connexion connecte web wifi ligne",
    "site": "site url page",
    "ip": "ip adresse",
    "telecharger": "telecharger download recuperer rapatrier",
    "processus": "processus programme application appli tache logiciel",
    "arreter": "arreter tuer fermer kill stopper stop quitter",
    "espace": "espace disque place stockage",
    "taille": "taille poids gros lourd volume",
    "installer": "installer installe paquet",
    "aller": "aller entrer changer naviguer deplacer",
    "remonter": "remonter revenir retour arriere parent",
    "ou": "ou position emplacement actuel courant",
    "historique": "historique precedent anciennes",
    "qui": "qui utilisateur user compte",
    "heure": "heure date jour",
    "memoire": "memoire ram",
    "git": "git version depot commit",
    "script": "script automatiser automatique batch",
    "commande": "commande raccourci alias fonction",
    "nettoyer": "nettoyer clear ecran effacer-ecran",
    "aide": "aide manuel help documentation",
    "cache": "cache caches cachee invisible masque secret",
    "lancer": "lancer executer demarrer run",
    "ecrire": "ecrire ecris inserer mettre",
    "ajouter": "ajouter rajouter append",
    "telephone": "telephone appeler appel numero tel",
    "sms": "sms texto",
    "mail": "mail email courriel",
    "carte": "carte cartes map maps itineraire gps",
    "lampe": "lampe torche flash lumiere",
    "allumer": "allumer eteindre activer",
    "batterie": "batterie charge",
    "volume": "volume son",
    "luminosite": "luminosite",
    "photo": "photo camera appareil selfie",
    "parler": "parler voix",
    "vibrer": "vibrer vibration vibreur",
    "reglage": "reglage reglages parametre parametres",
    "partager": "partager share",
    "presse": "presse-papier presse",
    "envoyer": "envoyer",
    "regler": "regler ajuster",
    "youtube": "youtube whatsapp instagram spotify netflix",
    "modifier": "modifier editer changer",
    "tout": "tout tous toutes entier complet",
}
STOP = set("""le la les l un une des de du d pour comment je j veux voudrais aimerais faire fais
mon ma mes ton ta tes son sa ses a au aux et en sur dans quel quelle quels quelles est ce c que qu
il y on me m te t se s avec par plus peux peut puis dois faut sont etre avoir ca cela ceci""".split())


def mots(texte):
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", t)


def racine(m):
    if len(m) > 3 and m.endswith(("s", "x")):
        m = m[:-1]
    return m[:6]


RACINE_CONCEPT = {}
for _canon, _variantes in SYNONYMES.items():
    for _v in _variantes.split():
        for _m in mots(_v):
            RACINE_CONCEPT.setdefault(racine(_m), _canon)


def concepts(texte):
    return {RACINE_CONCEPT.get(racine(m), racine(m)) for m in mots(texte) if m not in STOP}


for _e in REGISTRE:
    base = _e["desc"] if _e["type"] == "cmd" else _e["titre"]
    _e["concepts"] = concepts(base + " " + _e["kw"])


def chercher(requete, n=3):
    req = requete.strip().lower()
    if not req:
        return []
    premier = req.split()[0]
    qc = concepts(requete)
    scores = []
    for idx, e in enumerate(REGISTRE):
        s = 0.0
        if e["type"] == "cmd" and premier in e["noms"]:
            s = 100 + (5 if e["cmd"].lower() == req else 0) - idx * 0.01
        elif qc:
            commun = len(qc & e["concepts"])
            if commun:
                s = commun * 10 - len(e["concepts"] - qc) * 0.5
                if qc <= e["concepts"]:
                    s += 5
                if e["type"] == "recette" and commun >= 2:
                    s += 4
        if s > 0:
            if e.get("android") and OSK != "android":
                s -= 3
            scores.append((s, e))
    scores.sort(key=lambda x: -x[0])
    if not scores:
        return []
    seuil = scores[0][0] * 0.5
    return [e for s, e in scores[:n] if s >= seuil]


# images des commandes qui ne sont pas dans le lexique (les autres viennent de lexique.py)
IMAGES_EN_PLUS = {
    "rmdir": "je démonte une pièce vide", "tail": "je lis juste le bas de la lettre",
    "echo": "je dis une phrase (avec > : l'entonnoir la verse dans une boîte)",
    "clear": "je range la table : l'écran redevient tout propre", "cls": "je range la table : l'écran redevient tout propre",
    "history": "le carnet de tout ce que tu as tapé", "man": "le mode d'emploi d'une commande",
    "get-help": "le mode d'emploi d'une commande", "uname": "la fiche de la maison : son nom, sa version",
    "systeminfo": "la fiche de la maison : son nom, sa version", "free": "la mémoire de la maison, comme un plan de travail",
    "top": "qui est réveillé, en direct, comme une caméra", "pkill": "j'envoie un programme se coucher, par son nom",
    "rm": "la broyeuse : pas de poubelle, c'est perdu pour toujours !",
    "termux-open-url": "j'ouvre la fenêtre sur un site", "am": "je demande à Android d'allumer quelque chose",
    "pm": "le registre des applis et de leurs noms secrets", "termux-torch": "l'interrupteur de la lampe de poche",
    "termux-battery-status": "combien il reste à manger dans le ventre du téléphone",
    "termux-tts-speak": "le téléphone lit ta phrase à voix haute", "termux-vibrate": "le téléphone frissonne",
    "termux-toast": "un petit mot qui apparaît sur l'écran", "termux-clipboard-get": "la poche magique du téléphone",
    "termux-clipboard-set": "la poche magique du téléphone", "termux-volume": "le bouton du son",
    "termux-brightness": "le variateur de lumière de l'écran", "termux-share": "je glisse une feuille dans une boîte aux lettres",
    "termux-open": "j'ouvre une feuille avec l'appli qui sait la lire", "termux-camera-photo": "clic : l'appareil photo du téléphone",
    "termux-wifi-connectioninfo": "le câble invisible qui relie la maison à internet",
    "termux-setup-storage": "j'ouvre la porte entre Termux et tes photos, téléchargements…",
}


def image(e):
    """L'image (la maison) d'une commande trouvée, ou None."""
    cle = e["cmd"].split()[0].lower()
    return lexique.images().get(cle) or IMAGES_EN_PLUS.get(cle)


def afficher(resultats, nom):
    """Lignes à afficher, commandes piégées contre le copier-coller."""
    if not resultats:
        return [f" {nom} se gratte la tête… je ne connais pas encore ça.",
                f" {DIM}Essaie d'autres mots : « supprimer fichier », « voir ip », « grep »…{RESET}"]
    out = []
    for e in resultats:
        if e["type"] == "cmd":
            out.append(f" {BOLD}{e['desc']}{RESET}")
            out.append(f"   {fg(226)}➜ {piege(e['cmd'])}{RESET}")
            if image(e):
                out.append(f"   {fg(147)}🏠 {image(e)}{RESET}")
            if e["danger"]:
                out.append(f"   {fg(203)}⚠ irréversible : vérifie avant !{RESET}")
            if e["note"]:
                out.append(f"   {DIM}{e['note']}{RESET}")
        else:
            out.append(f" {BOLD}Recette : {e['titre']}{RESET}")
            for i, (cmd, expl) in enumerate(e["steps"], 1):
                out.append(f"   {i}. {fg(226)}{piege(cmd)}{RESET}  {DIM}{expl}{RESET}")
        out.append("")
    return out


def memoriser(state, resultats):
    """Les commandes consultées rapportent un bonus si on les tape dans les 15 min."""
    import time
    now = time.time()
    for e in resultats:
        cmds = [e["cmd"]] if e["type"] == "cmd" else [c for c, _ in e["steps"]]
        for c in cmds:
            w = core.first_word(c)
            if w:
                state["cherche"][w] = now
