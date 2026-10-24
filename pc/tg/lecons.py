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
        {"dit": "Coucou ! Première question : où sommes-nous ?", "cmd": "pwd",
         "re": r"^(pwd|get-location|gl)\b",
         "bravo": "pwd = « print working directory » : le dossier où tu te trouves."},
        {"dit": "Regarde ce qu'il y a autour de nous.", "cmd": C("ls", "dir"),
         "re": r"^(ls|dir|gci|get-childitem)\b", "bravo": "Voilà les fichiers et dossiers d'ici !"},
        {"dit": "Rentrons à la maison (ton dossier perso).", "cmd": "cd ~",
         "re": r"^(cd|set-location|sl)(\s+~[/\\]?)?\s*$",
         "bravo": "~ veut dire « mon dossier perso ». Tu sais naviguer !"},
    ]},
    {"titre": "Construire mon nid", "skill": "Bâtisseur", "niveau": 3, "steps": [
        {"dit": "Il me faut un terrain de jeu. Crée-le depuis ton dossier perso.",
         "cmd": "mkdir terrain_terminagotchi", "fs": "terrain",
         "bravo": "mkdir = « make directory » : créer un dossier."},
        {"dit": "Entrons dedans.", "cmd": "cd terrain_terminagotchi", "re": CD + r".*terrain_terminagotchi",
         "bravo": "On est chez nous maintenant."},
        {"dit": "Construis-moi un nid !", "cmd": "mkdir nid", "fs": "nid",
         "bravo": "Il est parfait ! Et j'entends du bruit dehors… l'exploration est ouverte !"},
    ]},
    {"titre": "Le garde-manger", "skill": "Inspecteur", "niveau": 4, "steps": [
        {"dit": "J'ai faim… mets une pomme dans mon garde-manger.",
         "cmd": f"echo pomme > nid{S}repas.txt", "fs": "repas",
         "bravo": "« > » envoie le texte dans un fichier (et l'écrase s'il existe !)."},
        {"dit": "Vérifie ce qu'il y a dedans.", "cmd": f"cat nid{S}repas.txt",
         "re": r"^(cat|type|gc|get-content|less|more|head)\b.*repas",
         "bravo": "Toujours vérifier avant d'agir : réflexe de pro."},
        {"dit": "Cherche le mot « pomme » dans le fichier.",
         "cmd": C(f"grep pomme nid{S}repas.txt", f"Select-String pomme nid{S}repas.txt"),
         "re": r"^(grep|select-string|sls|findstr)\b.*pomme",
         "bravo": "Chercher un mot dans des fichiers : super-pouvoir débloqué."},
    ]},
    {"titre": "Le bouclier", "skill": "Gardien", "niveau": 5, "steps": [
        {"dit": "Qui a le droit de toucher à mon repas ?",
         "cmd": C("ls -l nid", f"attrib nid{S}repas.txt"),
         "re": r"^(ls\s+-\w*l|attrib|get-acl|icacls|stat)\b",
         "bravo": C("r = lire, w = écrire, x = exécuter.", "R = lecture seule (absent pour l'instant).")},
        {"dit": "Protège-le pour que personne ne l'abîme !",
         "cmd": C(f"chmod 444 nid{S}repas.txt", f"attrib +r nid{S}repas.txt"), "fs": "protege",
         "bravo": "Bouclier activé : le fichier est en lecture seule."},
        {"dit": "Essaie d'y ajouter une poire, pour voir…",
         "cmd": f"echo poire >> nid{S}repas.txt", "re": r">>.*repas",
         "bravo": "Refusé ! « >> » ajoute à la fin, mais le bouclier tient."},
    ]},
    {"titre": "Grand ménage", "skill": "Nettoyeur", "niveau": 6, "steps": [
        {"dit": "Fais une copie de secours de mon repas.",
         "cmd": f"cp nid{S}repas.txt nid{S}secours.txt", "fs": "secours",
         "bravo": "cp = copier. L'original ne bouge pas."},
        {"dit": "Déplace la copie dans le terrain, sous le nom reserve.txt.",
         "cmd": f"mv nid{S}secours.txt reserve.txt", "fs": "reserve",
         "bravo": "mv sert à déplacer ET à renommer."},
        {"dit": "On n'en a plus besoin : supprime-la.",
         "cmd": C("rm reserve.txt", "rm reserve.txt -Force"), "fs": "supprime",
         "astuce": C("S'il demande confirmation, réponds y.", "-Force car le fichier est protégé."),
         "bravo": "Attention : rm ne passe PAS par la corbeille. Vérifie toujours avant !"},
    ]},
]

# ---------------------------------------------------------------- arbre de compétences
RC = shell_rc()
ARBRE = {
    "Réseau": {"stat": "Agilité", "icone": "📡", "desc": "parler avec internet", "lecons": [
        {"titre": "Le radar", "skill": "Radar", "steps": [
            {"dit": "Le monde est-il là ? Envoie un petit signal.",
             "cmd": C("ping -c 3 example.com", "ping -n 3 example.com"), "re": r"^ping\b",
             "bravo": "Chaque réponse = un aller-retour. Le temps (ms) = la latence."},
            {"dit": "Et nous, quelle est notre adresse ?", "cmd": C("ip a", "ipconfig", mac="ifconfig", android="ifconfig"),
             "re": r"^(ip|ifconfig|ipconfig)\b",
             "bravo": "L'adresse IP, c'est notre numéro de maison sur le réseau."},
        ]},
        {"titre": "Le facteur", "skill": "Facteur", "steps": [
            {"dit": "Frappe à la porte d'un site, sans entrer.",
             "cmd": C("curl -I https://example.com", "curl.exe -I https://example.com"), "re": r"^curl(\.exe)?\b",
             "bravo": "200 = « entrez ! ». 404 = introuvable. 500 = le site est malade."},
            {"dit": "Depuis le terrain, rapporte-moi un colis (une page web).",
             "cmd": C("curl -o colis.html https://example.com", "curl.exe -o colis.html https://example.com"),
             "fs": "colis", "astuce": "Place-toi d'abord dans terrain_terminagotchi.",
             "bravo": "-o = « output » : on range la réponse dans un fichier."},
            {"dit": "Ouvre le colis : regarde les 5 premières lignes.",
             "cmd": C("head -n 5 colis.html", "Get-Content colis.html -Head 5"),
             "re": r"^(head|get-content|gc|cat|type)\b.*colis", "bravo": "Du HTML : le langage des pages web !"},
        ]},
        {"titre": "Le cartographe", "skill": "Cartographe", "steps": [
            {"dit": "Demande à l'annuaire d'internet l'adresse d'un site.", "cmd": "nslookup example.com",
             "re": r"^(nslookup|dig|resolve-dnsname)\b",
             "bravo": "Le DNS traduit les noms (example.com) en adresses IP."},
            {"dit": "Suis le chemin de nos paquets jusqu'au site.",
             "cmd": C("traceroute example.com", "tracert example.com"), "re": r"^(traceroute|tracert|tracepath|mtr)\b",
             "astuce": C(f"Si traceroute est absent : {installer('traceroute')}  (ou essaie tracepath)", None),
             "bravo": "Chaque ligne = un routeur traversé. Internet, c'est une chaîne de relais !"},
        ]},
    ]},
    "Git": {"stat": "Intelligence", "icone": "🌿", "desc": "garder l'histoire de ses fichiers (git requis)", "lecons": [
        {"titre": "Mon premier dépôt", "skill": "Archiviste", "steps": [
            {"dit": "Depuis le terrain, crée un carnet magique qui se souvient de tout.",
             "cmd": "git init carnet", "fs": "carnet",
             "bravo": "Un dépôt git ! Le dossier caché .git garde toute l'histoire."},
            {"dit": "Entre dans le carnet.", "cmd": "cd carnet", "re": CD + r".*carnet", "bravo": "Nous y sommes."},
            {"dit": "Demande-lui comment il va.", "cmd": "git status", "re": r"^git\s+status",
             "bravo": "git status : la commande que les pros tapent 100 fois par jour."},
        ]},
        {"titre": "Premier souvenir", "skill": "Mémoire", "steps": [
            {"dit": "Écris la première page du journal.", "cmd": 'echo "jour 1" > journal.txt', "fs": "journal",
             "bravo": "Le carnet a vu un nouveau fichier… mais ne le garde pas encore."},
            {"dit": "Prépare cette page pour le souvenir.", "cmd": "git add journal.txt", "re": r"^git\s+add\b",
             "bravo": "add = mettre la page dans l'enveloppe."},
            {"dit": "Scelle le souvenir !", "cmd": 'git commit -m "premier souvenir"', "fs": "commit",
             "astuce": 'Si git demande ton nom : git config --global user.name "Ton nom" (idem user.email)',
             "bravo": "Un commit = une photo de tes fichiers à cet instant. Pour toujours."},
        ]},
        {"titre": "Voyage dans le temps", "skill": "Chronomancien", "steps": [
            {"dit": "Ajoute une ligne au journal.", "cmd": 'echo "jour 2" >> journal.txt',
             "re": r">>\s*journal", "bravo": "Le journal a changé…"},
            {"dit": "Qu'est-ce qui a changé depuis le souvenir ?", "cmd": "git diff", "re": r"^git\s+diff",
             "bravo": "+ en vert = ajouté, - en rouge = enlevé."},
            {"dit": "Remonte le fil de nos souvenirs.", "cmd": "git log", "re": r"^git\s+log",
             "astuce": "Tape q pour quitter l'affichage.", "bravo": "Chaque souvenir a un identifiant unique."},
        ]},
    ]},
    "Scripts": {"stat": "Intelligence", "icone": "🧪", "desc": "automatiser et créer TES commandes", "lecons": [
        {"titre": "Ma première recette", "skill": "Cuistot", "steps": [
            {"dit": "Depuis le terrain, écris une recette dans mon nid.",
             "cmd": C(f"echo 'echo \"Miam !\"' > nid{S}miam.sh", f"echo 'Write-Output \"Miam !\"' > nid{S}miam.ps1"),
             "fs": "miam", "bravo": "Un script = une liste de commandes rangée dans un fichier."},
            {"dit": "Cuisine la recette !",
             "cmd": C(f"sh nid{S}miam.sh", f"powershell -ExecutionPolicy Bypass -File nid{S}miam.ps1"),
             "re": r"miam\.(sh|ps1)", "bravo": "Le script a parlé ! Tu viens de programmer."},
        ]},
        {"titre": "Ma propre commande", "skill": "Inventeur", "steps": (
            [{"dit": "Rends la recette exécutable.", "cmd": f"chmod +x nid{S}miam.sh", "fs": "miam_x",
              "bravo": "x = exécutable : c'est maintenant un programme."}] if not IS_WIN else []) + [
            {"dit": "Invente une commande à toi : « miam ».",
             "cmd": C("alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'", 'function miam { Write-Output "Miam !" }'),
             "re": r"^(alias\s+miam|function\s+miam)", "bravo": "Tu viens de créer une commande qui n'existait pas !"},
            {"dit": "Essaie-la !", "cmd": "miam", "re": r"^miam\s*$", "bravo": "MIAM ! C'est la meilleure commande du monde."},
        ]},
        {"titre": "Pour toujours", "skill": "Créateur", "steps": [
            {"dit": "Ta commande disparaîtra à la fermeture du terminal. Rends-la éternelle !",
             "cmd": C(f"echo \"alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'\" >> {RC}",
                      "Add-Content $PROFILE 'function miam { Write-Output \"Miam !\" }'"),
             "re": r"(alias\s+miam.*>>\s*\S*(rc|profile)|^add-content\s+\$profile)",
             "astuce": C(f"{RC} est lu à chaque ouverture du terminal.",
                         "Si $PROFILE n'existe pas : New-Item -Force $PROFILE"),
             "bravo": "Elle est gravée dans ta configuration."},
            {"dit": "Recharge ta configuration.", "cmd": C(f"source {RC}", ". $PROFILE"),
             "re": r"^(source|\.)\s+\S*(rc|profile)",
             "bravo": "Désormais, tes propres inventions me nourrissent ×3 !"},
        ]},
    ]},
    "Système": {"stat": "Force", "icone": "⚙", "desc": "surveiller et maîtriser la machine", "lecons": [
        {"titre": "La vigie", "skill": "Vigie", "steps": [
            {"dit": "Qui est aux commandes de cette machine ?", "cmd": "whoami", "re": r"^whoami\b",
             "bravo": "C'est toi ! Ton nom d'utilisateur."},
            {"dit": "Qui tourne en ce moment dans la machine ?", "cmd": C("ps aux", "Get-Process", android="ps"),
             "re": r"^(ps|get-process|gps|tasklist|top|htop)\b",
             "bravo": "Chaque ligne est un programme vivant, avec son numéro (PID)."},
        ]},
        {"titre": "L'intendant", "skill": "Intendant", "steps": [
            {"dit": "Reste-t-il de la place dans le grenier (le disque) ?", "cmd": C("df -h", "Get-PSDrive"),
             "re": r"^(df|get-psdrive|gdr)\b", "bravo": "-h = « human » : des tailles lisibles (Go, Mo)."},
            {"dit": "Combien pèse notre terrain de jeu ?",
             "cmd": C("du -sh ~/terrain_terminagotchi", "Get-ChildItem ~/terrain_terminagotchi -Recurse | Measure-Object Length -Sum"),
             "re": r"^(du|get-childitem|gci|dir|ls)\b.*terrain", "bravo": "Pratique pour trouver ce qui remplit le disque."},
        ]},
        {"titre": "Le chasseur", "skill": "Chasseur", "steps": [
            {"dit": "Lâche un programme qui dort en arrière-plan.",
             "cmd": C("sleep 300 &", "Start-Process notepad"), "re": r"^(sleep\b.*&|(start-process|saps|start)\b)",
             "bravo": C("& = « en arrière-plan » : le terminal reste libre.", "Un Bloc-notes est apparu.")},
            {"dit": "Repère-le.", "cmd": C("jobs", "Get-Process notepad"), "re": r"^(jobs|get-process|gps|ps)\b",
             "bravo": "Le voilà, avec son numéro."},
            {"dit": "Chasse-le !", "cmd": C("kill %1", "Stop-Process -Name notepad"),
             "re": r"^(kill|stop-process|spps|taskkill)\b", "bravo": "Programme arrêté. Utile quand l'un d'eux est bloqué !"},
        ]},
    ]},
}

LAUNCHER = "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
ARBRE["Android"] = {"stat": "Agilité", "icone": "📱", "desc": "piloter ton téléphone : applis, liens, outils",
                    "android": True, "lecons": [
    {"titre": "Les petits pouvoirs", "skill": "Télécommande", "steps": [
        {"dit": "Fais apparaître un petit message sur l'écran.", "cmd": 'termux-toast "Coucou !"',
         "re": r"^termux-toast\b", "astuce": "Il faut l'appli Termux:API et : pkg install termux-api",
         "bravo": "Termux:API relie le terminal aux fonctions du téléphone."},
        {"dit": "Fais-moi vibrer !", "cmd": "termux-vibrate -d 400", "re": r"^termux-vibrate\b",
         "bravo": "-d = durée en millisecondes."},
        {"dit": "Allume la lampe torche…", "cmd": "termux-torch on", "re": r"^termux-torch\s+on",
         "bravo": "Lumière ! Pratique dans le noir."},
        {"dit": "… et éteins-la.", "cmd": "termux-torch off", "re": r"^termux-torch\s+off",
         "bravo": "Tu commandes le matériel du téléphone en une ligne."},
    ]},
    {"titre": "Ouvrir le monde", "skill": "Portier", "steps": [
        {"dit": "Ouvre un site dans ton navigateur.", "cmd": "termux-open-url https://fr.wikipedia.org",
         "re": r"^termux-open-url\b", "bravo": "Android choisit tout seul la bonne appli pour ce lien."},
        {"dit": "Cherche un lieu dans les cartes.",
         "cmd": 'am start -a android.intent.action.VIEW -d "geo:0,0?q=Tour Eiffel"',
         "re": r"^am\s+start\b.*geo:", "bravo": "Un « intent » = une demande envoyée à Android : « montre-moi ça »."},
        {"dit": "Prépare un appel (sans appeler !).", "cmd": "am start -a android.intent.action.DIAL -d tel:0123456789",
         "re": r"^am\s+start\b.*DIAL", "bravo": "DIAL ouvre le clavier avec le numéro : c'est toi qui décides d'appeler."},
    ]},
    {"titre": "Lancer n'importe quelle appli", "skill": "Lanceur", "steps": [
        {"dit": "Chaque appli a un nom secret (son « paquet »). Trouve celui des Réglages.",
         "cmd": "pm list packages | grep settings", "re": r"^pm\s+list\s+packages",
         "bravo": "Le paquet des Réglages, c'est com.android.settings."},
        {"dit": "Lance les Réglages par leur nom secret.",
         "cmd": f"{LAUNCHER} com.android.settings", "re": r"^am\s+start\b.*LAUNCHER",
         "astuce": "Si rien ne s'ouvre : autorise Termux à « s'afficher par-dessus les autres applis ».",
         "bravo": "MAIN + LAUNCHER = « ouvre-la comme depuis son icône »."},
        {"dit": "C'est long à taper… invente ta commande « ouvre » pour toujours !",
         "cmd": f"echo 'ouvre() {{ {LAUNCHER} \"$1\"; }}' >> ~/.bashrc",
         "re": r"ouvre\s*\(\).*>>\s*\S*bashrc", "bravo": "Elle est gravée dans ta configuration."},
        {"dit": "Recharge ta configuration.", "cmd": "source ~/.bashrc", "re": r"^(source|\.)\s+\S*bashrc",
         "bravo": "Ta commande « ouvre » est prête."},
        {"dit": "Essaie-la avec n'importe quelle appli !", "cmd": "ouvre com.android.settings",
         "re": r"^ouvre\s+\S+", "bravo": "Tu lances tes applis au clavier, comme un pro."},
    ]},
    {"titre": "Le majordome", "skill": "Majordome", "steps": [
        {"dit": "Comment va la batterie ?", "cmd": "termux-battery-status", "re": r"^termux-battery-status\b",
         "bravo": "percentage = le pourcentage, status = en charge ou non."},
        {"dit": "Fais-moi parler !", "cmd": 'termux-tts-speak "Bonjour, je suis ton Terminagotchi"',
         "re": r"^termux-tts-speak\b", "bravo": "J'ai une voix maintenant !"},
        {"dit": "Range un texte dans le presse-papier.", "cmd": 'termux-clipboard-set "Coucou"',
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
