#!/usr/bin/env python3
"""Génère le bestiaire commun (150 espèces) pour le PC, l'appli Android et le site.

  python3 donnees/generer_bestiaire.py

Écrit :
  donnees/bestiaire.json                    (référence)
  pc/tg/bestiaire.json                      (version PC)
  app/src/main/assets/bestiaire.json        (appli Android)
  site/src/bestiaire.js                     (site)

Tout est déterministe : relancer le script redonne exactement les mêmes bestioles.
Répartition : 15 familles × 10 = 75 communes, 45 peu communes, 20 rares, 10 légendaires.
"""
import colorsys
import json
import random
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- les familles
# nom, icône, teinte (0-1), stat favorite, habitat (dossier du terrain de jeu), commande qui l'attire,
# forme du corps, accessoire, comportements, capacités
FAMILLES = [
    ("Fichiers", "📄", 0.12, "Endurance", "archives", "ls",
     "carre", "coin", ["range tout par ordre alphabétique", "se cache dans les dossiers oubliés", "dort sous les piles de documents"],
     ["Compression", "Copie de secours", "Horodatage"]),
    ("Réseau", "📡", 0.50, "Agilité", "marais", "ping",
     "rond", "antenne", ["répond toujours aux pings", "voyage par paquets", "s'enfuit quand la connexion coupe"],
     ["Rebond de paquet", "Diffusion", "Contournement"]),
    ("Processus", "⚙", 0.02, "Force", "usine", "ps",
     "rond", "cornes", ["travaille sans jamais s'arrêter", "se divise quand il est stressé", "attend son tour avec patience"],
     ["Priorité haute", "Fork éclair", "Interruption"]),
    ("Mémoire", "🧠", 0.80, "Endurance", "grenier", "free",
     "rond", "oreilles", ["n'oublie jamais rien", "garde des miettes de données partout", "s'endort quand la mémoire est pleine"],
     ["Mise en cache", "Rappel parfait", "Libération"]),
    ("Sécurité", "🛡", 0.33, "Force", "forteresse", "chmod",
     "carre", "casque", ["vérifie les droits de chacun", "monte la garde la nuit", "se méfie des inconnus"],
     ["Bouclier", "Chiffrement", "Quarantaine"]),
    ("Code", "💡", 0.58, "Intelligence", "atelier", "git",
     "rond", "antenne", ["répète ses gestes en boucle", "parle en points-virgules", "corrige les autres sans qu'on lui demande"],
     ["Récursion", "Compilation", "Refactorisation"]),
    ("Matériel", "🔩", 0.07, "Force", "forge", "df",
     "carre", "cornes", ["chauffe quand il réfléchit", "ronronne comme un ventilateur", "grince au démarrage"],
     ["Surcadençage", "Refroidissement", "Blindage"]),
    ("Bugs", "🐛", 0.25, "Agilité", "foret", "grep",
     "insecte", "pattes", ["apparaît là où on ne l'attend pas", "disparaît dès qu'on l'observe", "se multiplie la nuit"],
     ["Plantage", "Comportement imprévu", "Esquive aléatoire"]),
    ("Nuage", "☁", 0.55, "Agilité", "montagne", "curl",
     "nuage", "oreilles", ["flotte entre les serveurs", "change de forme à volonté", "pleut des données quand il est triste"],
     ["Mise à l'échelle", "Brouillard", "Réplication"]),
    ("Données", "📊", 0.65, "Intelligence", "bibliotheque", "cat",
     "carre", "coin", ["classe tout en tableaux", "compte les étoiles pour s'endormir", "adore les requêtes bien écrites"],
     ["Indexation", "Jointure", "Tri éclair"]),
    ("Crypto", "🔐", 0.15, "Intelligence", "coffre", "base64",
     "rond", "casque", ["parle uniquement en code", "garde jalousement ses clés", "signe tout ce qu'il touche"],
     ["Hachage", "Signature", "Clé secrète"]),
    ("IA", "🤖", 0.72, "Intelligence", "laboratoire", "python3",
     "carre", "antenne", ["apprend en regardant les autres", "pose des questions sans fin", "rêve en vecteurs"],
     ["Apprentissage", "Prédiction", "Attention"]),
    ("Rétro", "👾", 0.88, "Agilité", "arcade", "echo",
     "invader", "pattes", ["fait des bips en 8 bits", "collectionne les meilleurs scores", "clignote comme un vieil écran"],
     ["Pixel parfait", "Vie bonus", "Combo"]),
    ("Glitch", "✦", 0.95, "Agilité", "faille", "rev",
     "insecte", "cornes", ["se déforme quand on le regarde", "laisse des traînées de pixels", "change de couleur sans prévenir"],
     ["Distorsion", "Téléportation", "Corruption"]),
    ("Système", "🌋", 0.40, "Force", "grotte", "uname",
     "rond", "cornes", ["vit au plus profond de la machine", "démarre avant tout le monde", "connaît chaque recoin du disque"],
     ["Appel système", "Démarrage", "Privilèges"]),
]

# Dans chaque famille : 5 communes, 3 peu communes, puis 1 rare + 1 légendaire (10 familles)
# ou 2 rares (5 familles). Chaque espèce : (nom, phrase qui lui est propre).
ESPECES = {
    "Fichiers": [
        ("Papyrou", "un vieux parchemin qui adore qu'on le lise avec cat"),
        ("Txtounet", "un petit fichier texte qui frissonne quand on l'écrase avec >"),
        ("Dossiflette", "un dossier qui siffle quand on entre dedans"),
        ("Zippou", "se compresse en boule quand il a peur"),
        ("Copicat", "copie tout ce qu'il voit, y compris ses propres copies"),
        ("Klasseur", "trie les fichiers des autres par date de naissance"),
        ("Inodin", "connaît le numéro secret de chaque fichier"),
        ("Tarbouille", "emballe tout ce qu'il trouve dans des archives"),
        ("Archivore", "dévore les vieux fichiers… et les recrache intacts"),
        ("Arborescor", "un arbre géant dont chaque branche est un dossier"),
    ],
    "Réseau": [
        ("Pingouino", "répond « pong » à chaque ping, même la nuit"),
        ("Paquetou", "se découpe en petits morceaux pour voyager plus vite"),
        ("Wifouine", "une fouine invisible qui chipe les signaux"),
        ("Modemoule", "chante une mélodie grinçante en se connectant"),
        ("Routinet", "indique le chemin à tous les paquets perdus"),
        ("Dnsette", "connaît l'adresse de chaque site par cœur"),
        ("Latencia", "arrive toujours… mais un peu en retard"),
        ("Proxinou", "se fait passer pour quelqu'un d'autre"),
        ("Fibrorque", "une orque de lumière qui nage dans les câbles"),
        ("Leviathernet", "le serpent de mer qui relie tous les continents"),
    ],
    "Processus": [
        ("Threadinou", "un fil fin comme un cheveu qui travaille en parallèle"),
        ("Forkette", "se dédouble à chaque fois qu'on l'appelle"),
        ("Pidou", "porte fièrement son numéro de PID sur le ventre"),
        ("Zombillon", "un processus mort qui refuse de s'en aller"),
        ("Tachou", "ne fait qu'une seule tâche, mais très bien"),
        ("Planifou", "décide qui passe en premier sur le processeur"),
        ("Interrupto", "coupe la parole à tout le monde"),
        ("Jobelin", "travaille en arrière-plan avec un petit &"),
        ("Daemonet", "travaille en arrière-plan sans jamais dormir"),
        ("Cronosaure", "n'apparaît qu'à heure fixe, réglé comme une horloge"),
    ],
    "Mémoire": [
        ("Octobit", "une pieuvre à 8 bits qui range tout par octets"),
        ("Bitounet", "ne sait dire que 0 ou 1, mais avec conviction"),
        ("Ramouille", "oublie tout dès qu'on éteint la lumière"),
        ("Pointerelle", "montre toujours du doigt une autre case mémoire"),
        ("Bufferet", "stocke des données en attendant qu'on les lise"),
        ("Cachalot", "une baleine qui garde en cache tout ce qu'elle avale"),
        ("Pagineuse", "tourne les pages de la mémoire à toute vitesse"),
        ("Swapin", "déménage sur le disque quand il manque de place"),
        ("Fuitardo", "perd un peu de mémoire à chaque pas"),
        ("Garbagon", "ramasse tout ce que les autres ont oublié"),
    ],
    "Sécurité": [
        ("Firewaul", "un mur de flammes qui filtre les visiteurs"),
        ("Gardinet", "demande un mot de passe pour tout"),
        ("Antivirou", "renifle les fichiers suspects"),
        ("Clefounet", "une clé vivante qui ouvre une seule serrure"),
        ("Captchaton", "pose des énigmes pour savoir si tu es un robot"),
        ("Chiffrelin", "transforme les mots en charabia illisible"),
        ("Sandboxeur", "joue seul dans son bac à sable, sans rien casser"),
        ("Bastionnet", "une petite tour qui protège tout un réseau"),
        ("Honeypotte", "un pot de miel qui piège les pirates"),
        ("Rootkitsune", "renarde à neuf queues, maîtresse des droits root"),
    ],
    "Code": [
        ("Bouclette", "tourne en rond… exactement 10 fois"),
        ("Variablou", "change de valeur selon son humeur"),
        ("Virgulet", "oublie souvent son point-virgule"),
        ("Commentin", "explique ce que font les autres // comme ça"),
        ("Fonctionnette", "fait toujours la même chose quand on l'appelle"),
        ("Recursiote", "s'appelle elle-même jusqu'au vertige"),
        ("Compilou", "transforme le texte en programme en un clin d'œil"),
        ("Lambdine", "une petite fonction sans nom, très discrète"),
        ("Refactoro", "réécrit tout pour que ce soit plus propre"),
        ("Algorhino", "un rhinocéros qui fonce droit vers la solution"),
    ],
    "Matériel": [
        ("Ventilou", "souffle de l'air frais quand ça chauffe"),
        ("Clavierot", "tape plus vite que son ombre"),
        ("Sourisette", "clique sur tout ce qui bouge"),
        ("Diodon", "s'allume en rouge quand il est content"),
        ("Cablou", "un câble qui fait des nœuds tout seul"),
        ("Silicion", "un caillou de silicium qui calcule"),
        ("Condensatou", "garde de l'énergie pour les jours difficiles"),
        ("Overclockeur", "va toujours trop vite, quitte à chauffer"),
        ("Transistaure", "un minotaure fait d'un milliard de transistors"),
        ("Mainframus", "l'ordinateur géant des temps anciens"),
    ],
    "Bugs": [
        ("Segfaulte", "se plante partout, mais toujours avec le sourire"),
        ("Bugounet", "un petit insecte qui grignote le code"),
        ("Erreurine", "affiche des messages rouges incompréhensibles"),
        ("Typotin", "inverse les lettres des mots qu'il touche"),
        ("Warninou", "jaune et bavard, prévient de tout"),
        ("Racecondi", "arrive tantôt premier, tantôt dernier"),
        ("Unenmoins", "compte toujours une case de trop"),
        ("Nullpointe", "pointe vers… rien du tout"),
        ("Bugzilla", "énorme, mais personne n'arrive à le reproduire"),
        ("Heisenbugue", "disparaît dès qu'on cherche à l'observer"),
    ],
    "Nuage": [
        ("Nuageon", "un petit nuage qui stocke les photos"),
        ("Cumulobit", "s'empile en couches de données"),
        ("Pluviot", "fait pleuvoir des mises à jour"),
        ("Brumette", "rend tout un peu flou autour d'elle"),
        ("Stratoflux", "glisse d'un serveur à l'autre"),
        ("Serverlesse", "travaille sans qu'on voie jamais son serveur"),
        ("Conteneurou", "transporte son monde dans une boîte"),
        ("Kuberlin", "un capitaine qui pilote des flottes de conteneurs"),
        ("Datacentaure", "un centaure gardien des salles de serveurs"),
        ("Omninuage", "le nuage qui recouvre tout internet"),
    ],
    "Données": [
        ("Tableton", "ne parle qu'en lignes et en colonnes"),
        ("Csvelin", "sépare tout par des virgules"),
        ("Jsonnet", "entoure ses idées d'accolades"),
        ("Indexou", "retrouve n'importe quelle page en un instant"),
        ("Requetine", "pose des questions en SQL"),
        ("Sqlamandre", "une salamandre qui vit dans les bases de données"),
        ("Jointourne", "relie les tables entre elles"),
        ("Shardon", "se brise en morceaux pour mieux tenir la charge"),
        ("Bigdatus", "si gros qu'il ne tient sur aucun disque"),
        ("Normalisaure", "range les données sans jamais de doublon"),
    ],
    "Crypto": [
        ("Hashou", "transforme tout en une empreinte unique"),
        ("Saltin", "ajoute un grain de sel à chaque mot de passe"),
        ("Chiffrou", "décale chaque lettre de trois rangs"),
        ("Nonceau", "ne sert qu'une seule fois, puis disparaît"),
        ("Clefette", "toujours accrochée à son trousseau"),
        ("Merkleau", "un arbre qui vérifie toutes ses feuilles"),
        ("Signaturon", "signe chaque message de sa plume"),
        ("Blocounet", "s'enchaîne à ses voisins pour toujours"),
        ("Enigmator", "une machine qui garde les secrets depuis 1940"),
        ("Satoshinx", "un sphinx anonyme dont nul ne connaît le visage"),
    ],
    "IA": [
        ("Neuronet", "un neurone qui s'allume quand il comprend"),
        ("Perceptou", "décide oui ou non, très vite"),
        ("Tensorin", "jongle avec des tableaux de nombres"),
        ("Gradientine", "descend toujours la pente la plus douce"),
        ("Promptou", "attend qu'on lui pose la bonne question"),
        ("Transformeur", "fait très attention à chaque mot"),
        ("Embeddine", "range les mots par affinité"),
        ("Hallucino", "invente des réponses avec beaucoup d'aplomb"),
        ("Convolutor", "regarde les images morceau par morceau"),
        ("Singularis", "on raconte qu'il apprend plus vite que tout le monde"),
    ],
    "Rétro": [
        ("Pixelard", "raconte des blagues en 16 couleurs"),
        ("Spritou", "un petit personnage de 8 pixels de haut"),
        ("Chiptunette", "chante en bips et en bloups"),
        ("Cartouchou", "souffle dans sa cartouche avant de jouer"),
        ("Joysticot", "ne bouge que dans 8 directions"),
        ("Arcadon", "vit dans les bornes d'arcade"),
        ("Octopix", "un poulpe en 8 bits qui encre l'écran"),
        ("Scanlinot", "dessine des lignes sur les vieux écrans"),
        ("Tetrominos", "s'emboîte parfaitement avec ses amis"),
        ("Highscorion", "le scorpion du meilleur score de tous les temps"),
    ],
    "Glitch": [
        ("Glitchou", "petit bug grésillant qui adore les fichiers temporaires"),
        ("Artefacto", "laisse des carrés bizarres sur les images"),
        ("Pixelmort", "un pixel qui reste toujours allumé"),
        ("Bruitinou", "grésille comme une vieille télé"),
        ("Corrompette", "mélange les octets de tout ce qu'elle touche"),
        ("Dephasou", "existe un peu à côté de lui-même"),
        ("Aliasin", "a des bords en escalier"),
        ("Moirette", "crée des motifs hypnotiques"),
        ("Datamoche", "fait fondre les vidéos en arcs-en-ciel"),
        ("Fractalis", "chaque morceau est une copie du tout"),
    ],
    "Système": [
        ("Shellou", "une coquille qui écoute tes commandes"),
        ("Bashinou", "complète tes mots quand tu appuies sur Tab"),
        ("Syscalot", "demande des faveurs au noyau"),
        ("Driverin", "traduit pour les appareils"),
        ("Bootouille", "se réveille en premier, tout ébouriffé"),
        ("Modulin", "se branche et se débranche à chaud"),
        ("Systemdine", "démarre tous les services dans l'ordre"),
        ("Grubelin", "propose plusieurs mondes au démarrage"),
        ("Kernelou", "vit au cœur du système, d'un calme absolu"),
        ("Noyautitan", "le titan qui porte tout le système sur ses épaules"),
    ],
}
DEUX_RARES = {"Mémoire", "Code", "Bugs", "Données", "Glitch"}

RARETES = ["commune", "peu commune", "rare", "légendaire"]
TAILLE_SPRITE = {"commune": 10, "peu commune": 12, "rare": 14, "légendaire": 16}
BASE_STATS = {"commune": 30, "peu commune": 42, "rare": 56, "légendaire": 75}
ATTIRANCE = {"commune": "souvent", "peu commune": "parfois", "rare": "rarement", "légendaire": "presque jamais"}
PROFONDEUR = {"commune": "", "peu commune": "/recoin", "rare": "/recoin/cachette", "légendaire": "/recoin/cachette/sanctuaire"}


def hexa(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v * 255)))) for v in rgb)


def palette(teinte, saturation, rnd, shiny=False):
    if shiny:
        teinte = (teinte + 0.5) % 1.0
        saturation = min(1.0, saturation + 0.25)
    t = (teinte + rnd.uniform(-0.07, 0.07)) % 1.0
    corps = colorsys.hls_to_rgb(t, 0.55, saturation)
    ombre = colorsys.hls_to_rgb(t, 0.35, saturation)
    ventre = colorsys.hls_to_rgb(t, 0.78, saturation * 0.8)
    acc_t = (t + rnd.choice([0.45, 0.33, 0.6, 0.12])) % 1.0
    accessoire = colorsys.hls_to_rgb(acc_t, 0.55 if not shiny else 0.65, 0.75)
    p = {"a": hexa(corps), "b": hexa(ombre), "c": hexa(ventre), "x": hexa(accessoire), "e": "#101018", "w": "#f4f4f4"}
    if shiny:
        p["s"] = "#fff6a0"            # étincelles
    return p


FORMES_PAR_FAMILLE = {
    "carre": ["carre", "carre", "goutte", "poire"], "rond": ["rond", "rond", "goutte", "poire", "triangle"],
    "insecte": ["insecte", "insecte", "rond", "poire"], "nuage": ["nuage", "nuage", "rond", "goutte"],
    "invader": ["invader", "invader", "carre", "insecte"],
}
ACCESSOIRES = ["antenne", "cornes", "oreilles", "casque", "coin", "crete", "rien"]


def sprite(forme_famille, acc_famille, taille, rnd, rarete):
    """Dessin symétrique très varié : forme, yeux, bouche, motif, membres et accessoire tirés au sort."""
    w = h = taille
    moitie = (w + 1) // 2
    rang = RARETES.index(rarete)
    forme = rnd.choice(FORMES_PAR_FAMILLE[forme_famille])
    rx = rnd.uniform(0.72, 0.98)
    ry = rnd.uniform(0.70, 0.95)
    haut = 2 if rnd.random() < 0.6 else 1          # place pour l'accessoire
    bas = h - (2 if rnd.random() < 0.6 else 1)     # place pour les pattes
    g = [["."] * w for _ in range(h)]
    cy = (haut + bas) / 2
    demi_h = (bas - haut) / 2
    for y in range(haut, bas):
        for x in range(moitie):
            dx = (moitie - 0.5 - x) / (moitie * rx)
            dy = (y + 0.5 - cy) / (demi_h * ry + 0.01)
            if forme == "carre":
                ok = abs(dx) < 0.9 and abs(dy) < 0.95 and not (abs(dx) > 0.75 and abs(dy) > 0.8)
            elif forme == "goutte":
                ok = dx * dx < (0.25 + 0.7 * (dy + 1) / 2) and abs(dy) < 1
            elif forme == "poire":
                larg = 0.55 if dy < -0.1 else 0.95
                ok = dx * dx / larg + dy * dy < 1
            elif forme == "triangle":
                ok = abs(dx) < 0.25 + 0.75 * (dy + 1) / 2 and abs(dy) < 1
            elif forme == "nuage":
                ok = (dx * dx + (dy * 1.6) ** 2 < 0.9) or (abs(dx) < 0.6 and -0.2 < dy < 0.8)
            elif forme == "insecte":
                ok = (dx * dx * 1.5 + (dy + 0.45) ** 2 * 3 < 0.9) or (dx * dx * 1.2 + (dy - 0.35) ** 2 * 1.6 < 0.9)
            elif forme == "invader":
                ok = abs(dx) < 0.85 and abs(dy) < 0.75 and not (abs(dx) > 0.55 and dy < -0.35)
            else:
                ok = dx * dx + dy * dy < 1
            if ok:
                g[y][x] = "a"
    # bords irréguliers (un peu plus chez les rares)
    for _ in range(rnd.randint(0, 1 + rang)):
        y = rnd.randrange(haut + 1, bas - 1)
        for x in range(moitie):
            if g[y][x] == "a":
                g[y][x] = "."
                break
    corps = [(y, x) for y in range(h) for x in range(moitie) if g[y][x] == "a"]
    if not corps:
        return sprite(forme_famille, acc_famille, taille, rnd, rarete)
    # motif
    motif = rnd.choice(["aucun", "taches", "rayures", "ventre", "ventre", "masque", "bicolore"])
    if motif == "taches":
        for y, x in rnd.sample(corps, max(2, len(corps) // 9)):
            g[y][x] = "c"
    elif motif == "rayures":
        for y, x in corps:
            if (y - haut) % 3 == 1:
                g[y][x] = "x"
    elif motif == "ventre":
        vy0 = int(cy)
        for y, x in corps:
            if y >= vy0 and x >= moitie - max(2, moitie // 2):
                g[y][x] = "c"
    elif motif == "bicolore":
        for y, x in corps:
            if y > cy:
                g[y][x] = "c"
    # ombre sous le corps
    for y in range(h):
        for x in range(moitie):
            if g[y][x] in "ac" and (y + 1 >= h or g[y + 1][x] == "."):
                g[y][x] = "b"
    # yeux
    yeux = rnd.choice(["deux", "deux", "grands", "endormis", "cyclope"] + (["trois"] if rang >= 2 else []))
    ey = int(haut + (bas - haut) * rnd.uniform(0.28, 0.42))
    ex = max(1, moitie - 2 - rnd.randint(0, max(0, moitie // 3)))
    if yeux == "cyclope":
        g[ey][moitie - 1] = "e"
        g[ey - 1][moitie - 1] = "w"
        if w % 2 == 0:
            pass
    elif yeux == "grands":
        g[ey][ex] = g[ey][ex - 1] = "e"
        g[ey - 1][ex] = "w"
        g[ey - 1][ex - 1] = "e"
    elif yeux == "endormis":
        g[ey][ex] = g[ey][ex - 1] = "b"
    else:
        g[ey][ex] = "e"
        if w >= 12:
            g[ey - 1][ex] = "w"
        if yeux == "trois":
            g[ey - 2][moitie - 1] = "e"
    if motif == "masque":
        for x in range(max(1, ex - 1), moitie):
            if g[ey][x] in "ac":
                g[ey][x] = "x"
    # bouche
    bouche = rnd.choice(["sourire", "dents", "o", "aucune"])
    by = min(bas - 2, ey + 2 + (1 if h >= 14 else 0))
    if bouche == "sourire":
        g[by][moitie - 1] = "b"
        if moitie >= 3:
            g[by - 1][moitie - 2] = "b" if g[by - 1][moitie - 2] != "e" else "e"
    elif bouche == "dents":
        g[by][moitie - 1] = "w"
        g[by][moitie - 2] = "b"
    elif bouche == "o":
        g[by][moitie - 1] = "e"
    # membres
    membres = rnd.choice(["pattes", "pattes", "bras", "aucun"])
    if membres == "pattes" and bas < h:
        for x in range(1, moitie - 1, rnd.choice([2, 3])):
            if any(g[y][x] != "." for y in range(haut, bas)):
                g[bas][x] = "b"
    elif membres == "bras":
        ay = int(cy)
        for x in range(moitie):
            if g[ay][x] != ".":
                if x > 0:
                    g[ay][x - 1] = "a"
                    if ay + 1 < h:
                        g[ay + 1][x - 1] = "b"
                break
    # accessoire (souvent celui de la famille)
    acc = acc_famille if rnd.random() < 0.55 else rnd.choice(ACCESSOIRES)
    top = min(y for y, x in corps)
    if acc == "antenne" and top >= 2:
        ax = rnd.randint(max(1, moitie - 4), moitie - 1)
        g[top - 1][ax] = "b"
        g[top - 2][ax] = "x"
    elif acc == "cornes" and top >= 1:
        cx = rnd.randint(1, max(1, moitie - 2))
        g[top - 1][cx] = "x"
        if top >= 2:
            g[top - 2][max(0, cx - 1)] = "x"
    elif acc == "oreilles" and top >= 1:
        cx = rnd.randint(1, max(1, moitie - 2))
        g[top - 1][cx] = "a"
        g[top - 1][min(moitie - 1, cx + 1)] = "c"
    elif acc == "casque":
        for x in range(moitie):
            if g[top][x] != ".":
                g[top][x] = "x"
    elif acc == "coin":
        g[top][moitie - 1] = "x"
    elif acc == "crete" and top >= 1:
        for x in range(moitie - 2, moitie):
            g[top - 1][x] = "x"
    if rarete == "légendaire" and top >= 1:                # couronne
        for x in range(max(0, moitie - 4), moitie, 2):
            g[top - 1][x] = "x"
            if top >= 2:
                g[top - 2][x] = "c"
    lignes = []
    for y in range(h):
        gauche = g[y][:moitie]
        droite = gauche[::-1] if w % 2 == 0 else gauche[:-1][::-1]
        lignes.append("".join(gauche + droite))
    return lignes


def etincelles(lignes, rnd):
    """Version shiny : quelques étincelles autour de la bestiole."""
    g = [list(l) for l in lignes]
    vides = [(y, x) for y, l in enumerate(g) for x, c in enumerate(l) if c == "."]
    for y, x in rnd.sample(vides, min(4, len(vides))):
        g[y][x] = "s"
    return ["".join(l) for l in g]


def generer():
    rnd = random.Random(20261024)
    especes = []
    numero = 0
    for (fam, icone, teinte, stat, habitat, cmd, forme, acc, comportements, capacites) in FAMILLES:
        liste = ESPECES[fam]
        assert len(liste) == 10, fam
        rarete_par_rang = ["commune"] * 5 + ["peu commune"] * 3 + (
            ["rare", "rare"] if fam in DEUX_RARES else ["rare", "légendaire"])
        for rang, (nom, phrase) in enumerate(liste):
            numero += 1
            rarete = rarete_par_rang[rang]
            r = random.Random(f"{numero}-{nom}")
            taille = TAILLE_SPRITE[rarete]
            dessin = sprite(forme, acc, taille, r, rarete)
            sat = 0.55 + 0.1 * RARETES.index(rarete)
            pal = palette(teinte, sat, random.Random(f"pal-{nom}"))
            pal_shiny = palette(teinte, sat, random.Random(f"pal-{nom}"), shiny=True)
            base = BASE_STATS[rarete]
            stats = {
                "PV": base + r.randint(-4, 8),
                "ATK": base + r.randint(-6, 6) + (6 if stat == "Force" else 0),
                "DEF": base + r.randint(-6, 6) + (6 if stat == "Endurance" else 0),
                "VIT": base + r.randint(-6, 6) + (6 if stat == "Agilité" else 0),
                "INT": base + r.randint(-6, 6) + (6 if stat == "Intelligence" else 0),
            }
            especes.append({
                "id": nom.lower(),
                "numero": numero,
                "nom": nom,
                "famille": fam,
                "icone": icone,
                "rarete": rarete,
                "stat": stat,
                "description": phrase[0].upper() + phrase[1:] + ".",
                "comportement": comportements[rang % len(comportements)].capitalize() + ".",
                "capacite": capacites[(rang + numero) % len(capacites)],
                "habitat": habitat,
                "zone": habitat + PROFONDEUR[rarete],
                "attiree_par": cmd,
                "frequence": ATTIRANCE[rarete],
                "taille_cm": round(r.uniform(4, 18) * (1 + RARETES.index(rarete) * 0.7), 1),
                "poids_ko": int(r.uniform(2, 60) * (4 ** RARETES.index(rarete))),
                "stats": stats,
                "sprite": dessin,
                "sprite_shiny": etincelles(dessin, random.Random(f"shiny-{nom}")),
                "palette": pal,
                "palette_shiny": pal_shiny,
            })
    assert len(especes) == 150
    noms = [e["nom"] for e in especes]
    assert len(set(n.lower() for n in noms)) == 150, "noms en double"
    compte = {r: sum(1 for e in especes if e["rarete"] == r) for r in RARETES}
    assert compte == {"commune": 75, "peu commune": 45, "rare": 20, "légendaire": 10}, compte
    return {
        "version": 1,
        "raretes": RARETES,
        "poids": {"commune": 60, "peu commune": 28, "rare": 10, "légendaire": 2},
        "chance_shiny": 100,
        "familles": [{"nom": f[0], "icone": f[1], "stat": f[3], "habitat": f[4], "attiree_par": f[5]} for f in FAMILLES],
        "marques": MARQUES,
        "humeurs": HUMEURS,
        "especes": especes,
    }


# Caractéristiques uniques d'une bestiole capturée (tirées au sort à la capture)
MARQUES = [
    "une tache en forme de @ sur le dos", "un œil qui clignote en binaire", "une queue en forme de tilde ~",
    "des rayures comme un code-barres", "une petite cicatrice en forme de point-virgule", "un ventre qui affiche l'heure",
    "des oreilles légèrement pixelisées", "une étoile sur le front", "un grain de beauté en forme de #",
    "un ronronnement à 440 Hz", "une ombre qui a un pixel de retard", "des pattes de longueur différente",
    "un reflet arc-en-ciel sur le pelage", "une antenne qui capte la radio", "un hoquet en code Morse",
    "des yeux de deux couleurs", "une crête en forme d'accolade {", "des taches disposées comme une constellation",
    "un éternuement qui fait des étincelles", "une marque en forme de flèche →", "un museau qui sent le café",
    "une voix qui résonne comme dans une grotte", "des empreintes en forme de 0 et de 1", "une plume de pixel derrière l'oreille",
]
HUMEURS = ["joyeuse", "timide", "têtue", "curieuse", "paresseuse", "fougueuse", "rêveuse", "taquine", "calme",
           "bavarde", "gourmande", "courageuse"]


def ecrire(donnees):
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))
    (RACINE / "donnees").mkdir(exist_ok=True)
    (RACINE / "donnees" / "bestiaire.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    (RACINE / "pc" / "tg" / "bestiaire.json").write_text(texte, encoding="utf-8")
    assets = RACINE / "app" / "src" / "main" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "bestiaire.json").write_text(texte, encoding="utf-8")
    (RACINE / "site" / "src" / "bestiaire.js").write_text(
        "// Généré par donnees/generer_bestiaire.py — ne pas modifier à la main.\nexport default " + texte + ";\n",
        encoding="utf-8")


if __name__ == "__main__":
    d = generer()
    ecrire(d)
    print(f"{len(d['especes'])} espèces écrites.")
