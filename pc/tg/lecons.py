"""Le Terminagotchi professeur : tronc commun puis arbre de compétences à 4 branches."""
import os
import re

from . import core
from .plateforme import OSK, C, IS_WIN, est_colle, installer, shell_rc

T = core.TERRAIN
S = "\\" if IS_WIN else "/"


def _protected(p):
    try:
        return (p.stat().st_mode & 0o222) == 0
    except OSError:
        return False


def _commit_fait():
    git = T / "carnet" / ".git"
    heads = git / "refs" / "heads"
    try:
        return any(heads.iterdir()) or (git / "packed-refs").exists()
    except OSError:
        return False


MIAM = T / "nid" / ("miam.ps1" if IS_WIN else "miam.sh")

FS = {
    "terrain":  lambda: T.is_dir(),
    "nid":      lambda: (T / "nid").is_dir(),
    "repas":    lambda: (T / "nid" / "repas.txt").is_file(),
    "protege":  lambda: _protected(T / "nid" / "repas.txt"),
    "secours":  lambda: (T / "nid" / "secours.txt").is_file(),
    "reserve":  lambda: (T / "reserve.txt").is_file(),
    "supprime": lambda: not (T / "reserve.txt").exists(),
    "colis":    lambda: (T / "colis.html").is_file(),
    "carnet":   lambda: (T / "carnet" / ".git").is_dir(),
    "journal":  lambda: (T / "carnet" / "journal.txt").is_file(),
    "commit":   _commit_fait,
    "miam":     lambda: MIAM.is_file(),
    "miam_x":   lambda: MIAM.is_file() and os.access(MIAM, os.X_OK),
}

CD = r"^(cd|set-location|sl)\s+"

# ---------------------------------------------------------------- tronc commun
TRONC = [
    {"titre": "Où suis-je ?", "skill": "Boussole", "niveau": 2, "steps": [
        {"dit": "Coucou ! On visite la maison ensemble. Où est le point rouge « vous êtes ici » ?", "cmd": "pwd",
         "re": r"^(pwd|get-location|gl)\b",
         "bravo": "Trouvé, voilà notre point rouge ! Les grands appellent ça *le dossier où tu es* (pwd)."},
        {"dit": "Ouvre les yeux : qu'est-ce qu'il y a dans cette pièce ?", "cmd": C("ls", "dir"),
         "re": r"^(ls|dir|gci|get-childitem)\b", "bravo": "Tout ce qu'il y a dans la pièce ! Les grands disent *lister le dossier*."},
        {"dit": "Allez, on rentre dans ta chambre !", "cmd": "cd ~",
         "re": r"^(cd|set-location|sl)(\s+~[/\\]?)?\s*$",
         "bravo": "Te revoilà dans ta chambre ! Les grands disent *ton dossier perso* ; son petit nom, c'est ~."},
    ]},
    {"titre": "Construire mon nid", "skill": "Bâtisseur", "niveau": 3, "steps": [
        {"dit": "Il me faut une salle de jeu. Depuis ta chambre, construis une nouvelle pièce !",
         "cmd": "mkdir terrain_terminagotchi", "fs": "terrain",
         "bravo": "Une pièce toute neuve ! Les grands disent *créer un dossier*."},
        {"dit": "Passe la porte de la salle de jeu.", "cmd": "cd terrain_terminagotchi", "re": CD + r".*terrain_terminagotchi",
         "bravo": "On est dans notre salle de jeu ! Passer une porte, les grands disent *changer de dossier*."},
        {"dit": "Construis-moi un petit nid dans cette pièce !", "cmd": "mkdir nid", "fs": "nid",
         "bravo": "Il est parfait ! Une pièce dans une pièce : les grands disent *un sous-dossier*. Et j'entends du bruit dehors…"},
    ]},
    {"titre": "Le garde-manger", "skill": "Inspecteur", "niveau": 4, "steps": [
        {"dit": "J'ai faim ! Prends l'entonnoir « > » et verse une pomme dans la boîte repas.txt de mon nid.",
         "cmd": f"echo pomme > nid{S}repas.txt", "fs": "repas",
         "bravo": "Miam ! Attention : l'entonnoir vide la boîte avant de verser. Les grands disent *écrire dans un fichier*."},
        {"dit": "Lis-moi la lettre repas.txt à voix haute.", "cmd": f"cat nid{S}repas.txt",
         "re": r"^(cat|type|gc|get-content|less|more|head)\b.*repas",
         "bravo": "Une pomme, parfait ! Les grands disent *afficher un fichier*. Toujours vérifier avant d'agir !"},
        {"dit": "Prends la loupe du détective : cherche le mot « pomme » dans la lettre.",
         "cmd": C(f"grep pomme nid{S}repas.txt", f"Select-String pomme nid{S}repas.txt"),
         "re": r"^(grep|select-string|sls|findstr)\b.*pomme",
         "bravo": "La loupe l'a trouvé ! Les grands disent *chercher dans un fichier*."},
    ]},
    {"titre": "Le bouclier", "skill": "Gardien", "niveau": 5, "steps": [
        {"dit": "Qui a le droit de toucher à mon repas ? Regarde les cadenas.",
         "cmd": C("ls -l nid", f"attrib nid{S}repas.txt"),
         "re": r"^(ls\s+-\w*l|attrib|get-acl|icacls|stat)\b",
         "bravo": C("r = lire, w = écrire, x = faire marcher. Les grands disent *les droits*.", "R = lecture seule (pas encore de cadenas). Les grands disent *les attributs*.")},
        {"dit": "Mets un cadenas sur la boîte, que personne ne l'abîme !",
         "cmd": C(f"chmod 444 nid{S}repas.txt", f"attrib +r nid{S}repas.txt"), "fs": "protege",
         "bravo": "Clic ! On peut lire, mais plus écrire. Les grands disent *lecture seule*."},
        {"dit": "Essaie de glisser une poire au fond de la boîte, pour voir…",
         "cmd": f"echo poire >> nid{S}repas.txt", "re": r">>.*repas",
         "bravo": "Refusé ! « >> » ajoute au fond sans rien vider… mais le cadenas tient bon. Les grands disent *ajouter à la fin*."},
    ]},
    {"titre": "Grand ménage", "skill": "Nettoyeur", "niveau": 6, "steps": [
        {"dit": "Fais une photocopie de mon repas, au cas où.",
         "cmd": f"cp nid{S}repas.txt nid{S}secours.txt", "fs": "secours",
         "bravo": "Deux feuilles pareilles, et l'original n'a pas bougé ! Les grands disent *copier*."},
        {"dit": "Porte la copie dans la salle de jeu et colle-lui une nouvelle étiquette : reserve.txt.",
         "cmd": f"mv nid{S}secours.txt reserve.txt", "fs": "reserve",
         "bravo": "Déménagée et renommée d'un coup ! Les grands disent *déplacer* et *renommer*."},
        {"dit": "On n'en a plus besoin. Attention : c'est la broyeuse, pas la poubelle !",
         "cmd": C("rm reserve.txt", "rm reserve.txt -Force"), "fs": "supprime",
         "astuce": C("S'il demande confirmation, réponds y.", "-Force car le fichier est protégé."),
         "bravo": "Broyée pour toujours : pas de poubelle pour la rattraper. Les grands disent *supprimer*. Vérifie toujours avant !"},
    ]},
]

# ---------------------------------------------------------------- arbre de compétences
RC = shell_rc()
ARBRE = {
    "Réseau": {"stat": "Agilité", "icone": "📡", "desc": "parler avec les autres maisons (internet)", "lecons": [
        {"titre": "Le radar", "skill": "Radar", "steps": [
            {"dit": "Il y a quelqu'un dans la maison d'en face ? Crie « Ohé ! » (un ping) et écoute l'écho.",
             "cmd": C("ping -c 3 example.com", "ping -n 3 example.com"), "re": r"^ping\b",
             "bravo": "Chaque écho est un aller-retour ; le temps qu'il met (en ms), c'est la latence."},
            {"dit": "Et nous, quelle est l'adresse de notre maison (notre adresse IP) ?", "cmd": C("ip a", "ipconfig", mac="ifconfig", android="ifconfig"),
             "re": r"^(ip|ifconfig|ipconfig)\b",
             "bravo": "Voilà notre adresse IP : notre numéro de maison sur le réseau."},
        ]},
        {"titre": "Le facteur", "skill": "Facteur", "steps": [
            {"dit": "Envoie curl, le facteur, frapper à la porte d'un site sans entrer.",
             "cmd": C("curl -I https://example.com", "curl.exe -I https://example.com"), "re": r"^curl(\.exe)?\b",
             "bravo": "Code de réponse HTTP : 200 = « entrez ! », 404 = introuvable, 500 = le site est malade."},
            {"dit": "Depuis le terrain, télécharge une page web dans colis.html.",
             "cmd": C("curl -o colis.html https://example.com", "curl.exe -o colis.html https://example.com"),
             "fs": "colis", "astuce": "Place-toi d'abord dans terrain_terminagotchi.",
             "bravo": "-o = « output » : la réponse est rangée dans un fichier, comme le facteur dépose une lettre."},
            {"dit": "Affiche les 5 premières lignes du colis.",
             "cmd": C("head -n 5 colis.html", "Get-Content colis.html -Head 5"),
             "re": r"^(head|get-content|gc|cat|type)\b.*colis", "bravo": "Du HTML : le langage dans lequel les pages web sont écrites !"},
        ]},
        {"titre": "Le cartographe", "skill": "Cartographe", "steps": [
            {"dit": "Interroge le DNS (l'annuaire des maisons) : quelle adresse IP pour example.com ?", "cmd": "nslookup example.com",
             "re": r"^(nslookup|dig|resolve-dnsname)\b",
             "bravo": "Le DNS traduit les noms (example.com) en adresses IP."},
            {"dit": "Suis le trajet de nos paquets, de routeur en routeur, jusqu'au site.",
             "cmd": C("traceroute example.com", "tracert example.com"), "re": r"^(traceroute|tracert|tracepath|mtr)\b",
             "astuce": C(f"Si traceroute est absent : {installer('traceroute')}  (ou essaie tracepath)", None),
             "bravo": "Chaque ligne = un routeur traversé. Internet, c'est une chaîne de relais !"},
        ]},
    ]},
    "Git": {"stat": "Intelligence", "icone": "🌿", "desc": "l'appareil photo de tes fichiers (git requis)", "lecons": [
        {"titre": "Mon premier dépôt", "skill": "Archiviste", "steps": [
            {"dit": "Depuis le terrain, fabrique un album photo magique pour tes fichiers : le carnet.",
             "cmd": "git init carnet", "fs": "carnet",
             "bravo": "L'album est prêt ! Il garde ses photos dans une pièce cachée, .git. Les grands disent *un dépôt git*."},
            {"dit": "Passe la porte du carnet.", "cmd": "cd carnet", "re": CD + r".*carnet", "bravo": "Nous y sommes."},
            {"dit": "Demande à l'appareil photo ce qu'il voit.", "cmd": "git status", "re": r"^git\s+status",
             "bravo": "Il te dit ce qui a changé. git status : les pros la tapent 100 fois par jour."},
        ]},
        {"titre": "Premier souvenir", "skill": "Mémoire", "steps": [
            {"dit": "Écris la première page du journal dans un nouveau fichier.", "cmd": 'echo "jour 1" > journal.txt', "fs": "journal",
             "bravo": "git a vu un nouveau fichier… mais n'a pas encore pris la photo : il est « non suivi »."},
            {"dit": "Ajoute le fichier à l'index (pose-le devant l'objectif).", "cmd": "git add journal.txt", "re": r"^git\s+add\b",
             "bravo": "git add met le fichier dans l'index : il sera sur la prochaine photo."},
            {"dit": "Fais ton premier commit (clic, la photo) !", "cmd": 'git commit -m "premier souvenir"', "fs": "commit",
             "astuce": 'Si git demande ton nom : git config --global user.name "Ton nom" (idem user.email)',
             "bravo": "Un commit = une photo de tes fichiers à cet instant, avec un message. Pour toujours."},
        ]},
        {"titre": "Voyage dans le temps", "skill": "Chronomancien", "steps": [
            {"dit": "Ajoute une ligne à la fin du journal (>>).", "cmd": 'echo "jour 2" >> journal.txt',
             "re": r">>\s*journal", "bravo": "Le fichier a changé depuis le dernier commit…"},
            {"dit": "Affiche le diff : ce qui a changé depuis le commit.", "cmd": "git diff", "re": r"^git\s+diff",
             "bravo": "+ en vert = ligne ajoutée, - en rouge = ligne enlevée."},
            {"dit": "Affiche l'historique des commits (l'album).", "cmd": "git log", "re": r"^git\s+log",
             "astuce": "Tape q pour quitter l'affichage.", "bravo": "Chaque commit a un identifiant unique (son hash)."},
        ]},
    ]},
    "Scripts": {"stat": "Intelligence", "icone": "🧪", "desc": "des recettes que la maison suit toute seule, et TES commandes", "lecons": [
        {"titre": "Ma première recette", "skill": "Cuistot", "steps": [
            {"dit": "Depuis le terrain, écris une recette (une liste de commandes) dans mon nid.",
             "cmd": C(f"echo 'echo \"Miam !\"' > nid{S}miam.sh", f"echo 'Write-Output \"Miam !\"' > nid{S}miam.ps1"),
             "fs": "miam", "bravo": "Une recette rangée dans un fichier : les grands disent *un script*."},
            {"dit": "Demande à la maison de suivre la recette !",
             "cmd": C(f"sh nid{S}miam.sh", f"powershell -ExecutionPolicy Bypass -File nid{S}miam.ps1"),
             "re": r"miam\.(sh|ps1)", "bravo": "La maison a suivi le script toute seule. Tu viens de programmer !"},
        ]},
        {"titre": "Ma propre commande", "skill": "Inventeur", "steps": (
            [{"dit": "Autorise la recette à cuisiner seule : rends-la exécutable (qui sait faire quelque chose).", "cmd": f"chmod +x nid{S}miam.sh", "fs": "miam_x",
              "bravo": "x = exécutable : le script est devenu un programme."}] if not IS_WIN else []) + [
            {"dit": "Donne un surnom à la recette : crée l'alias « miam ».",
             "cmd": C("alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'", 'function miam { Write-Output "Miam !" }'),
             "re": r"^(alias\s+miam|function\s+miam)", "bravo": "Un alias, c'est un surnom de commande. Tu as créé une commande qui n'existait pas !"},
            {"dit": "Essaie-la !", "cmd": "miam", "re": r"^miam\s*$", "bravo": "MIAM ! C'est la meilleure commande du monde."},
        ]},
        {"titre": "Pour toujours", "skill": "Créateur", "steps": [
            {"dit": "Ton alias disparaîtra à la fermeture du terminal. Écris-le dans ton fichier de configuration (le carnet de la maison) !",
             "cmd": C(f"echo \"alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'\" >> {RC}",
                      "Add-Content $PROFILE 'function miam { Write-Output \"Miam !\" }'"),
             "re": r"(alias\s+miam.*>>\s*\S*(rc|profile)|^add-content\s+\$profile)",
             "astuce": C(f"{RC} est relu à chaque ouverture du terminal.",
                         "Si $PROFILE n'existe pas : New-Item -Force $PROFILE"),
             "bravo": "Il est gravé dans ta configuration."},
            {"dit": "Recharge ta configuration (source).", "cmd": C(f"source {RC}", ". $PROFILE"),
             "re": r"^(source|\.)\s+\S*(rc|profile)",
             "bravo": "Désormais, tes propres inventions me nourrissent ×3 !"},
        ]},
    ]},
    "Système": {"stat": "Force", "icone": "⚙", "desc": "veiller sur la maison et ses habitants (le système)", "lecons": [
        {"titre": "La vigie", "skill": "Vigie", "steps": [
            {"dit": "Qui est le chef de cette maison (l'utilisateur) ?", "cmd": "whoami", "re": r"^whoami\b",
             "bravo": "C'est toi ! Voilà ton nom d'utilisateur."},
            {"dit": "Qui est réveillé dans la maison ? Liste les processus.", "cmd": C("ps aux", "Get-Process", android="ps"),
             "re": r"^(ps|get-process|gps|tasklist|top|htop)\b",
             "bravo": "Chaque ligne est un processus (un programme réveillé), avec son numéro : le PID."},
        ]},
        {"titre": "L'intendant", "skill": "Intendant", "steps": [
            {"dit": "Reste-t-il de la place sur le disque (les placards) ?", "cmd": C("df -h", "Get-PSDrive"),
             "re": r"^(df|get-psdrive|gdr)\b", "bravo": "-h = « human » : des tailles lisibles (Go, Mo)."},
            {"dit": "Combien pèse le dossier du terrain ?",
             "cmd": C("du -sh ~/terrain_terminagotchi", "Get-ChildItem ~/terrain_terminagotchi -Recurse | Measure-Object Length -Sum"),
             "re": r"^(du|get-childitem|gci|dir|ls)\b.*terrain", "bravo": "du = « disk usage ». Pratique pour trouver ce qui remplit le disque."},
        ]},
        {"titre": "Le chasseur", "skill": "Chasseur", "steps": [
            {"dit": "Lance un processus en arrière-plan (il fait la sieste au fond de la maison).",
             "cmd": C("sleep 300 &", "Start-Process notepad"), "re": r"^(sleep\b.*&|(start-process|saps|start)\b)",
             "bravo": C("& = « en arrière-plan » : le terminal reste libre.", "Un Bloc-notes est apparu.")},
            {"dit": "Retrouve-le dans la liste des tâches.", "cmd": C("jobs", "Get-Process notepad"), "re": r"^(jobs|get-process|gps|ps)\b",
             "bravo": "Le voilà, avec son numéro de tâche."},
            {"dit": "Arrête-le avec kill (au lit !).", "cmd": C("kill %1", "Stop-Process -Name notepad"),
             "re": r"^(kill|stop-process|spps|taskkill)\b", "bravo": "Processus arrêté. Utile quand un programme est bloqué !"},
        ]},
    ]},
}

LAUNCHER = "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
ARBRE["Android"] = {"stat": "Agilité", "icone": "📱", "desc": "piloter ton téléphone : applis, liens, outils",
                    "android": True, "lecons": [
    {"titre": "Les petits pouvoirs", "skill": "Télécommande", "steps": [
        {"dit": "Fais apparaître un petit mot sur l'écran du téléphone.", "cmd": 'termux-toast "Coucou !"',
         "re": r"^termux-toast\b", "astuce": "Il faut l'appli Termux:API et : pkg install termux-api",
         "bravo": "Termux:API, c'est le pont entre le terminal et le téléphone."},
        {"dit": "Fais frissonner le téléphone !", "cmd": "termux-vibrate -d 400", "re": r"^termux-vibrate\b",
         "bravo": "-d = la durée, en millisecondes."},
        {"dit": "Appuie sur l'interrupteur de la lampe…", "cmd": "termux-torch on", "re": r"^termux-torch\s+on",
         "bravo": "Lumière ! Pratique dans le noir."},
        {"dit": "… et éteins-la.", "cmd": "termux-torch off", "re": r"^termux-torch\s+off",
         "bravo": "Tu commandes le matériel du téléphone en une ligne."},
    ]},
    {"titre": "Ouvrir le monde", "skill": "Portier", "steps": [
        {"dit": "Ouvre la fenêtre sur un site, dans ton navigateur.", "cmd": "termux-open-url https://fr.wikipedia.org",
         "re": r"^termux-open-url\b", "bravo": "Android choisit tout seul la bonne appli pour ce lien."},
        {"dit": "Déplie la carte pour trouver un lieu.",
         "cmd": 'am start -a android.intent.action.VIEW -d "geo:0,0?q=Tour Eiffel"',
         "re": r"^am\s+start\b.*geo:", "bravo": "Un « intent » = une demande envoyée à Android : « montre-moi ça »."},
        {"dit": "Compose un numéro (sans appeler !).", "cmd": "am start -a android.intent.action.DIAL -d tel:0123456789",
         "re": r"^am\s+start\b.*DIAL", "bravo": "DIAL ouvre le clavier avec le numéro : c'est toi qui décides d'appeler."},
    ]},
    {"titre": "Lancer n'importe quelle appli", "skill": "Lanceur", "steps": [
        {"dit": "Chaque appli a un nom secret : son paquet. Trouve celui des Réglages.",
         "cmd": "pm list packages | grep settings", "re": r"^pm\s+list\s+packages",
         "bravo": "Le paquet des Réglages, c'est com.android.settings."},
        {"dit": "Lance les Réglages par leur paquet.",
         "cmd": f"{LAUNCHER} com.android.settings", "re": r"^am\s+start\b.*LAUNCHER",
         "astuce": "Si rien ne s'ouvre : autorise Termux à « s'afficher par-dessus les autres applis ».",
         "bravo": "MAIN + LAUNCHER = « ouvre-la comme si on touchait son icône »."},
        {"dit": "C'est long à taper… écris ta fonction « ouvre » dans ~/.bashrc, pour toujours !",
         "cmd": f"echo 'ouvre() {{ {LAUNCHER} \"$1\"; }}' >> ~/.bashrc",
         "re": r"ouvre\s*\(\).*>>\s*\S*bashrc", "bravo": "Elle est gravée dans ta configuration."},
        {"dit": "Recharge ta configuration.", "cmd": "source ~/.bashrc", "re": r"^(source|\.)\s+\S*bashrc",
         "bravo": "Ta commande « ouvre » est prête."},
        {"dit": "Essaie-la avec n'importe quelle appli !", "cmd": "ouvre com.android.settings",
         "re": r"^ouvre\s+\S+", "bravo": "Tu allumes tes applis au clavier, comme un pro."},
    ]},
    {"titre": "Le majordome", "skill": "Majordome", "steps": [
        {"dit": "Il reste combien à manger dans le ventre du téléphone (la batterie) ?", "cmd": "termux-battery-status", "re": r"^termux-battery-status\b",
         "bravo": "percentage = le pourcentage, status = en charge ou non."},
        {"dit": "Fais-moi parler !", "cmd": 'termux-tts-speak "Bonjour, je suis ton Terminagotchi"',
         "re": r"^termux-tts-speak\b", "bravo": "J'ai une voix maintenant !"},
        {"dit": "Range un texte dans la poche magique du téléphone : le presse-papier.", "cmd": 'termux-clipboard-set "Coucou"',
         "re": r"^termux-clipboard-set\b", "bravo": "Colle-le où tu veux : il est dans le presse-papier."},
    ]},
]}


def branche_dispo(b):
    return not ARBRE[b].get("android") or OSK == "android"


for _b in ARBRE.values():
    for _i, _l in enumerate(_b["lecons"]):
        _l["niveau"] = 6 + 2 * _i


def tronc_fini(state):
    return state["lesson"] >= len(TRONC)


def lecon_courante(state):
    """(leçon, étiquette) ou (None, None)."""
    if not tronc_fini(state):
        return TRONC[state["lesson"]], f"Leçon {state['lesson'] + 1}/{len(TRONC)}"
    b = state.get("branche")
    if b:
        i = state["arbre"].get(b, 0)
        les = ARBRE[b]["lecons"]
        if i < len(les):
            return les[i], f"{b} {i + 1}/{len(les)}"
    return None, None


def choisir_branche(state, b):
    if state.get("branche") != b:
        state["branche"] = b
        state["step"] = 0
        state["annonce"] = None
        core.say(state, f"Branche {b} ! On commence quand tu veux.", 8)


def avancer(state, les):
    step = les["steps"][state["step"]]
    core.log(state, f"✔ {step['cmd']}")
    core.say(state, step["bravo"], 12)
    state["step"] += 1
    if state["step"] < len(les["steps"]):
        core.add_xp(state, 5)
        return True
    state["step"] = 0
    if les["skill"] not in state["skills"]:
        state["skills"].append(les["skill"])
    core.log(state, f"🎓 « {les['titre']} » finie → {les['skill']} !")
    msg = f"Leçon finie ! J'ai appris « {les['skill']} » grâce à toi."
    if not tronc_fini(state):
        state["lesson"] += 1
        if tronc_fini(state):
            msg += " L'arbre de compétences est ouvert : touche [a] !"
    else:
        b = state["branche"]
        state["arbre"][b] = state["arbre"].get(b, 0) + 1
        state["stats"][ARBRE[b]["stat"]] += 5
        if state["arbre"][b] >= len(ARBRE[b]["lecons"]):
            core.log(state, f"🌳 Branche {b} maîtrisée !")
            msg += f" Branche {b} maîtrisée ! Choisis-en une autre [a]."
            state["branche"] = None
    core.add_xp(state, 20)
    core.say(state, msg, 14)
    return False


def tick(state, lines):
    les, _ = lecon_courante(state)
    if not les or core.level(state["xp"]) < les["niveau"]:
        return
    if state.get("annonce") != les["titre"]:
        state["annonce"] = les["titre"]
        core.say(state, "J'ai quelque chose à t'apprendre !", 10)
    for line in (l for l in lines if not est_colle(l)):
        step = les["steps"][state["step"]]
        if "re" in step and re.search(step["re"], line, re.I):
            if not avancer(state, les):
                return
    step = les["steps"][state["step"]]
    if "fs" in step and FS[step["fs"]]():
        avancer(state, les)
