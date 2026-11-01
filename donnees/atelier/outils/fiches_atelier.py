"""Les données de l'Atelier (donnees/atelier.json), ses fiches notions (charte de rigueur, docs/programme.md § 7.1) et sa
place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc, paliers R1 → R4 et « L'embarqué et le
temps réel » du § 7.13), les ponts, l'exploit « le robot simulé qui évite tous les obstacles » (§ 7.6), ses variantes
réservées des types Machine et Plante — des variantes qui EXISTENT déjà dans le bestiaire, ni gardiens ni réservées par
un autre monde —, le Pont des Nombres « logique » (ET / OU / NON, § 7.10 : la fiche manquait), les maths des étapes et
les étapes rejouées dans bash.

    python3 donnees/atelier/outils/fiches_atelier.py   écrit donnees/atelier.json, donnees/programme.json
                                                       et leurs copies (pc/tg, app/src/main/assets)

LE ROBOT EST SIMULÉ (§ 2.16, variante sans matériel) : un dossier robot/ dans le terrain (terrain_terminagotchi/robots),
dont les fichiers led, moteur et capteur_distance sont lus et écrits comme /sys/class/gpio ou /sys/class/leds sur un
vrai Raspberry Pi. Le robot vit sur une GRILLE avec des obstacles ; `atelier pas` est la « physique » : le jeu lit
robot/moteur, fait bouger le robot d'une case (ou tourner), puis écrit ce que voit le capteur. Le cerveau du robot est
un petit script de l'enfant (cerveau.sh), lancé par SA boucle (`for i in $(seq 20); do sh cerveau.sh; atelier pas;
done`), comme la fonction loop() d'une carte Arduino. Le jeu n'accède à AUCUN matériel : ni /dev/tty*, ni port série,
ni flashage, ni GPIO ; le vrai matériel (Raspberry Pi, carte Arduino ou ESP32) est facultatif, raconté, « avec un
adulte », sans marque mise en avant ni lien d'achat.

LES ARÈNES DU DÉFI sont vérifiées ici : un cerveau « tourne quand l'obstacle est tout près, sinon avance » (à droite OU à
gauche) visite au moins CASES_MIN cases en PAS pas sans se cogner ; un cerveau qui avance toujours se cogne ; un cerveau
qui s'arrête devant l'obstacle reste en dessous de CASES_MIN (il faut tourner).
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "O": (-1, 0)}
ORDRE = "NESO"
CASE_CM = 10
PAS = 20
CASES_MIN = 12
# l'arène d'entraînement (R1 → R2) : 8 × 5, un seul obstacle ; le robot part de (1 ; 1), tourné vers l'est
ENTRAINEMENT = {"grille": ["........", "........", "...#....", "........", "........"], "depart": [1, 1, "E"]}
# les arènes du défi (une par partie, tirée de la graine) : 10 × 6 ou 9 × 6, quelques obstacles (#)
ARENES = [
    {"grille": ["..........", "..#....#..", "..#.......", ".....##...", "#.........", "....#....."], "depart": [3, 2, "E"]},
    {"grille": ["..........", ".##.......", "......#...", "...#......", "........#.", ".........."], "depart": [0, 3, "E"]},
    {"grille": [".........", "....#....", ".#.......", ".....#...", "..#......", "........."], "depart": [8, 2, "S"]},
    {"grille": ["..........", "...#......", ".......#..", "..........", ".#....#...", ".........."], "depart": [4, 3, "N"]},
]
# Les situations de logique (atelier choix) : la bonne porte (et / ou / non). Les textes ne disent jamais le mot.
CHOIX = [{"id": "arret", "rep": "ou"}, {"id": "porte", "rep": "et"}, {"id": "veilleuse", "rep": "non"},
         {"id": "avance", "rep": "et"}, {"id": "alarme", "rep": "ou"}, {"id": "arrosage", "rep": "non"}]
# Le réflexe (L'embarqué et le temps réel) : vitesse du robot (cm/s) × temps d'un tour de boucle (ms) / 1000
REFLEXE = {"vitesses": [20, 30, 40, 50, 60], "temps_ms": [100, 200, 500, 1000]}
# La vue déployée : ce que la commande fait au robot (la pièce, le sens). Le premier motif qui correspond gagne.
AVANT = r"^(do\s+|then\s+|else\s+)?"
VUE = [
    {"motif": AVANT + r"(tg\s+)?atelier\s+pas\b", "piece": "roues", "sens": "bouge"},
    {"motif": AVANT + r"(sh|bash)\s+\S*cerveau\w*\.sh\b", "piece": "cerveau", "sens": "pense"},
    {"motif": r">\s*\S*robot/led\b", "piece": "led", "sens": "ecrit"},
    {"motif": r">\s*\S*robot/moteur\b", "piece": "moteur", "sens": "ecrit"},
    {"motif": r"\brobot/capteur_distance\b", "piece": "capteur", "sens": "lit"},
    {"motif": r"\brobot/led\b|/sys/class/leds\b", "piece": "led", "sens": "lit"},
    {"motif": r"\brobot/moteur\b", "piece": "moteur", "sens": "lit"},
]
COULEURS = {"led": 220, "moteur": 215, "capteur": 117, "roues": 78, "cerveau": 213}


def libre(g, x, y):
    return 0 <= y < len(g) and 0 <= x < len(g[0]) and g[y][x] != "#"


def distance(g, x, y, d):
    dx, dy = DIRS[d]
    n = 0
    while libre(g, x + dx * (n + 1), y + dy * (n + 1)):
        n += 1
    return n


def simuler(arene, cerveau, pas=PAS):
    """(cases visitées, chocs) d'un cerveau (distance en cm → moteur) sur une arène."""
    g = arene["grille"]
    x, y, d = arene["depart"]
    vus, chocs = {(x, y)}, 0
    for _ in range(pas):
        m = cerveau(distance(g, x, y, d) * CASE_CM)
        if m == "avance":
            dx, dy = DIRS[d]
            if libre(g, x + dx, y + dy):
                x, y = x + dx, y + dy
                vus.add((x, y))
            else:
                chocs += 1
        elif m in ("droite", "gauche"):
            d = ORDRE[(ORDRE.index(d) + (1 if m == "droite" else -1)) % 4]
    return len(vus), chocs


def verifier_arenes():
    for a in ARENES:
        assert libre(a["grille"], a["depart"][0], a["depart"][1]), a
        for sens in ("droite", "gauche"):
            n, c = simuler(a, lambda d, s=sens: s if d < CASE_CM else "avance")
            assert c == 0 and n >= CASES_MIN + 2, (a, sens, n, c)
        n, c = simuler(a, lambda d: "avance")
        assert c > 0, a
        n, c = simuler(a, lambda d: "stop" if d < CASE_CM else "avance")
        assert n < CASES_MIN, (a, "stop", n)


def donnees_atelier():
    verifier_arenes()
    return {
        "note": "Généré par donnees/atelier/outils/fiches_atelier.py ; lu par pc/tg/atelier.py et Atelier.kt. Le robot est "
                "SIMULÉ dans le terrain : aucun matériel, aucun port série, aucun flashage.",
        "robot": {"case_cm": CASE_CM, "moteurs": ["avance", "gauche", "droite", "stop"], "fichiers": ["led", "moteur", "capteur_distance"]},
        "directions": {"ordre": ORDRE, "pas": {k: list(v) for k, v in DIRS.items()}, "fleches": {"N": "▲", "E": "▶", "S": "▼", "O": "◀"}},
        "entrainement": ENTRAINEMENT, "arenes": ARENES,
        "defi": {"pas": PAS, "cases_min": CASES_MIN, "pas_max": 60},
        "essai": {"pas_min": 5},
        "verite": {"portes": ["et", "ou"]},
        "choix": {"situations": CHOIX, "montrees": 3},
        "reflexe": REFLEXE,
        "vue": {"regles": VUE}, "couleurs": COULEURS,
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"at.f.{nid}.enfant", "grands": f"at.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"at.f.{nid}.limite", "idees_fausses": [f"at.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_GPIO = "Documentation du noyau Linux, sysfs : LED (/sys/class/leds) et GPIO (Documentation/admin-guide/gpio/sysfs.rst, remplacée par l'interface caractère libgpiod) : https://docs.kernel.org/"
S_PI = "Raspberry Pi Documentation (Raspberry Pi OS, configuration, GPIO, pinctrl) : https://www.raspberrypi.com/documentation/"
S_BASH = "Bash Reference Manual (Conditional Constructs, Looping Constructs, Bash Conditional Expressions) : https://www.gnu.org/software/bash/manual/"
S_POSIX = "POSIX.1-2024, Shell Command Language (if, for, while, test) : https://pubs.opengroup.org/onlinepubs/9799919799/"
S_CRON = "crontab(5) et systemd.timer(5), pages de manuel : https://man7.org/linux/man-pages/"
S_ARDUINO = "Arduino CLI, documentation (compile, upload, monitor) : https://arduino.github.io/arduino-cli/"
S_ESP = "Espressif, esptool (documentation) : https://docs.espressif.com/projects/esptool/"
S_RT = "Notions de systèmes temps réel et de microcontrôleurs : programme de technologie du cycle 4 et de NSI (architectures matérielles) : https://eduscol.education.fr/"
FICHES = dict([
    fiche("robot_fichiers", r"(\brobot/|^(tg\s+)?atelier\s+(plan|robot|grille|pas|ou|cases|led)\b|plan_de_l_atelier|/sys/class/(leds|gpio)|\bgpioset\b|\bpinctrl\b)", [
        {"prepare": "mkdir -p robot && echo 0 > robot/led", "cmd": "echo 1 > robot/led && cat robot/led", "sortie": "1"},
        {"prepare": "mkdir -p robot && echo 30 > robot/capteur_distance", "cmd": "cat robot/capteur_distance", "sortie": "30"},
        {"prepare": "mkdir -p robot", "cmd": "echo avance > robot/moteur && ls robot", "sortie": "moteur"},
        {"cmd": "ls /sys/class/leds", "rejeu": "dépend de la machine (les LED de l'ordinateur)", "motif": "."},
        {"cmd": "atelier pas", "rejeu": "commande du jeu", "motif": "."}],
        [S_GPIO, S_PI, S_BASH]),
    fiche("conditions_robot", r"(^\[\s|^if\b|\bthen\b|^(tg\s+)?atelier\s+(logique|verite|choix)\b|-lt\s)", [
        {"cmd": "[ 5 -lt 10 ] && echo vrai || echo faux", "sortie": "vrai"},
        {"cmd": "[ 50 -lt 10 ] && echo vrai || echo faux", "sortie": "faux"},
        {"cmd": "d=30; if [ \"$d\" -lt 10 ]; then echo obstacle; else echo libre; fi", "sortie": "libre"},
        {"cmd": "echo $(( 1 && 0 )) $(( 1 || 0 )) $(( !1 ))", "sortie": "0 1 0"}],
        [S_BASH, S_POSIX, "Algèbre de Boole : programme de NSI (première), « types et valeurs de base » : https://eduscol.education.fr/"]),
    fiche("boucle_robot", r"(^for\b|^while\b|\bsleep\b|cerveau|^(tg\s+)?atelier\s+(essai|defi|aide-cerveau)\b|^(nano|edite|vi|vim)\b.*\.sh)", [
        {"cmd": "for i in 1 2 3; do echo tour $i; done", "sortie": "tour 1\ntour 2\ntour 3"},
        {"prepare": "printf 'd=$(cat c)\\nif [ \"$d\" -lt 10 ]; then echo droite; else echo avance; fi\\n' > cerveau.sh && echo 0 > c",
         "cmd": "sh cerveau.sh", "sortie": "droite"},
        {"prepare": "printf 'd=$(cat c)\\nif [ \"$d\" -lt 10 ]; then echo droite; else echo avance; fi\\n' > cerveau.sh && echo 40 > c",
         "cmd": "sh cerveau.sh", "sortie": "avance"},
        {"cmd": "n=0; while [ $n -lt 3 ]; do n=$((n + 1)); done; echo $n", "sortie": "3"},
        {"cmd": "for i in $(seq 20); do sh cerveau.sh; atelier pas; done", "rejeu": "commande du jeu", "motif": "."}],
        [S_BASH, S_POSIX, S_ARDUINO]),
    fiche("vrai_pi", r"(^(tg\s+)?atelier\s+(pi|gpio|autonome)\b|\bcrontab\b|\bsystemctl\b|journal\.txt|command\s+-v\s+(gpioset|pinctrl))", [
        {"prepare": "mkdir -p robot && printf 'pas 1\\npas 2\\npas 3\\n' > robot/journal.txt", "cmd": "tail -2 robot/journal.txt",
         "sortie": "pas 2\npas 3"},
        {"cmd": "command -v gpioset pinctrl || echo absent", "rejeu": "dépend de la machine (un Raspberry Pi les a)", "motif": "."},
        {"cmd": "crontab -l", "rejeu": "dépend de la machine (souvent « no crontab for … »)", "motif": "."}],
        [S_PI, S_CRON, S_GPIO]),
    fiche("embarque", r"(^(tg\s+)?atelier\s+(embarque|reflexe|arduino|telephone)\b|^time\b|arduino-cli|esptool|/dev/tty|^(lampe|vibre|batterie)\b)", [
        {"cmd": "echo $(( 50 * 200 / 1000 ))", "sortie": "10"},
        {"cmd": "time sleep 0", "rejeu": "le temps change à chaque fois", "motif": "."},
        {"cmd": "command -v arduino-cli esptool.py || echo absent", "rejeu": "dépend de la machine", "motif": "."}],
        [S_RT, S_ARDUINO, S_ESP]),
])

ATELIER = {"id": "atelier", "types": ["machine", "plante"], "requis": ["n4"], "chapitre": "robots",
           "paliers": [f"at{i}" for i in range(8)],
           "attirance": {"cmds": ["atelier", "sleep", "crontab", "gpioset", "pinctrl", "arduino-cli"],
                         "familles": ["Constructs", "Sylvestres"]},
           "ponts": {"ssh": ["port"], "nano": ["forge"], "for": ["forge"], "if": ["forge"], "systemctl": ["controle"],
                     "lscpu": ["machines"], "lora": ["ondes"]},
           "reutilise": {"chapitres": ["telephone"], "lecons": ["android0", "android3", "telephone0"]},
           "exploits": [{"id": "atelier.robot", "nom": "recomp.atelier.robot", "recompense": "variante"}],
           "maths": ["coordonnees", "logique", "multiplication"],
           "variantes_reservees": ["tisonnier:mecanique", "groinfer:rouille", "lampignon:forêt"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


S_ARITH = "Bash, Shell Arithmetic (&&, ||, ! : 1 = vrai, 0 = faux) : https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html"
MATHS = dict([
    maths_fiche("logique", [], "primaire", [
        {"cmd": "echo $(( 1 && 1 )) $(( 1 && 0 ))", "sortie": "1 0"},
        {"cmd": "echo $(( 0 || 1 )) $(( 0 || 0 ))", "sortie": "1 0"},
        {"cmd": "echo $(( !0 )) $(( !1 ))", "sortie": "1 0"}],
        [S_ARITH, "Programme de NSI (première), booléens et tables de vérité : https://eduscol.education.fr/",
         "G. Boole, An Investigation of the Laws of Thought (1854)"]),
])

# les maths des étapes (les Ponts des Nombres, proposés une fois, jamais un mur)
ETAPES = {"at2.3": {"maths": ["coordonnees"]}, "at2.6": {"maths": ["multiplication"]}, "at3.4": {"maths": ["logique"]},
          "at3.6": {"maths": ["logique"]}, "at7.3": {"maths": ["multiplication"]}}


def rejeu():
    """Ce que le jeu affirme des vraies sorties (le robot simulé change avec ce que fait l'enfant : le rejeu compare la
    sortie de bash à ce que LE JEU calcule sur les mêmes fichiers, egal_jeu)."""
    return {
        "at0.1": {"contient": ["plan_de_l_atelier.txt", "carnet_de_l_atelier.txt", "robot"], "pourquoi": "hist.at0.1.bravo : le plan, le carnet, le robot"},
        "at1.0": {"contient": ["capteur_distance", "led", "moteur"], "pourquoi": "hist.at1.0.bravo : trois fichiers, trois pièces du robot"},
        "at1.1": {"sortie": "0", "pourquoi": "hist.at1.1.bravo : 0, la LED est éteinte"},
        "at1.5": {"egal_jeu": "capteur", "pourquoi": "hist.at1.5.bravo : le capteur donne une distance en centimètres"},
        "at3.1": {"sortie": "vrai", "pourquoi": "hist.at3.1.bravo : 5 est plus petit que 10, c'est vrai"},
        "at3.2": {"egal_jeu": "obstacle_libre", "pourquoi": "hist.at3.2.bravo : le robot lit son capteur et décide"},
        "at4.0": {"egal_jeu": "capteur3", "pourquoi": "hist.at4.0.bravo : trois lectures, une par tour"},
        "at4.2": {"motif": r"robot/capteur_distance", "pourquoi": "hist.at4.2.bravo : le cerveau lit le capteur"},
        "at6.5": {"egal_jeu": "journal", "pourquoi": "hist.at6.5.bravo : les dernières lignes du journal du robot"},
    }


def main():
    G = donnees_atelier()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/atelier.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/atelier.json", "app/src/main/assets/atelier.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    P["mondes"] = [ATELIER if m["id"] == "atelier" else m for m in P["mondes"]]
    for cle in ("etapes", "rejeu"):                   # les étapes de l'Atelier : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("at") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de l'Atelier, {len(MATHS)} pont des nombres, {len(R)} étapes rejouées ; atelier.json écrit "
          f"({len(ARENES)} arènes vérifiées)")


if __name__ == "__main__":
    main()
