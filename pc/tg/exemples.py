"""Exemples prêts à taper, et aide quand il manque quelque chose après une commande.

1) Le lexique montre, sous chaque commande qui a besoin de quelque chose après elle, un exemple
   prêt à taper : « ↳ exemple : mkdir cabane ». Les exemples se tapent depuis le terrain de jeu
   (~/terrain_terminagotchi) et n'utilisent que ce qui y existe (nid/, nid/repas.txt écrit pendant
   la leçon « J'inspecte ») ou ce qu'un exemple précédent du lexique crée (mkdir cabane, touch
   lettre.txt, cp … copie.txt). pc/outils/test_retours_enfants.py les lance tous pour de vrai.
   Les commandes ne se traduisent pas ; seuls « exemple » et les mots à remplacer (NUMÉRO…) passent
   par les langues.

2) Quand l'enfant tape une commande connue sans ce qu'il lui faut (mkdir tout seul, cp avec un seul
   nom, cat qui attend le clavier sans fin…), la créature dit dans une bulle ce qui manque et la
   commande corrigée à taper (« Il manque le nom ! … Essaie : mkdir cabane »). Si la leçon en cours
   demande justement cette commande, c'est la commande de la leçon qui est proposée (mkdir nid).
   Sur PC le jeu lit l'historique du shell : il ne voit ni la sortie ni le code de retour de la
   commande, il reconnaît donc la commande « connue sans assez de noms après elle ».

Mêmes règles et mêmes exemples dans l'appli Android (Exemples.kt), qui elle voit aussi la sortie
(« missing operand », « usage: »…).
"""
import re

from . import core
from .langue import t
from .mots import palier, termes
from .plateforme import C, IS_WIN

# ---------------------------------------------------------------- 1. les exemples du lexique
S = "\\" if IS_WIN else "/"
REPAS = f"nid{S}repas.txt"


def _table():
    """{premier mot affiché dans le lexique (en minuscules) : exemple} pour le système courant."""
    return {
        "cd": "cd nid · cd .. · cd ~",
        "mkdir": "mkdir cabane",
        C("touch", "new-item"): C("touch lettre.txt", "New-Item lettre.txt"),
        "echo": "echo coucou > mot.txt",
        C("cp", "copy"): C(f"cp {REPAS} copie.txt", f"copy {REPAS} copie.txt"),
        C("mv", "move"): C("mv copie.txt nid/", "move copie.txt nid"),
        C("rm", "del"): C("rm lettre.txt", "del lettre.txt"),
        "rmdir": "rmdir cabane",
        C("chmod", "attrib"): C(f"chmod 444 {REPAS}", f"attrib +r {REPAS}"),
        "rev": f"rev {REPAS}",
        C("cat", "type"): C(f"cat {REPAS}", f"type {REPAS}"),
        C("less", "more"): C(f"less {REPAS}", f"more {REPAS}"),
        C("head", "get-content"): C(f"head -n 3 {REPAS}", f"Get-Content {REPAS} -Head 3"),
        "tail": f"tail -n 3 {REPAS}",
        C("grep", "select-string"): C(f"grep pomme {REPAS}", f"Select-String pomme {REPAS}"),
        C("find", "get-childitem"): C('find . -name "*.txt"', "Get-ChildItem -Recurse -Filter *.txt"),
        C("wc", "measure-object"): C(f"wc {REPAS}", f"Get-Content {REPAS} | Measure-Object -Line -Word"),
        C("sort", "sort-object"): C(f"sort {REPAS}", f"Get-Content {REPAS} | Sort-Object"),
        "stat": f"stat {REPAS}",
        C("kill", "stop-process"): C("kill {numero}", "Stop-Process -Id {numero}"),
        "du": "du -sh nid",
        C("ping"): C("ping -c 3 example.com", "ping -n 3 example.com"),
        C("curl", "curl.exe"): C("curl -I https://example.com", "curl.exe -I https://example.com"),
        "nslookup": "nslookup example.com",
        "ssh": "ssh {ssh}",
        "git": "git init carnet",
        C("bash", "powershell"): C('bash -c "echo coucou"', 'powershell -c "echo coucou"'),
        C("alias", "function"): C("alias salut='echo coucou'", "function salut { echo coucou }"),
        C("python3", "python"): C('python3 -c "print(2+2)"', 'python -c "print(2+2)"'),
        C("nano", "notepad"): C("nano lettre.txt", "notepad lettre.txt"),
        "tg aile": "tg aile grenier",
        "tg bestiaire": "tg bestiaire Glitchou",
        "tg langue": "tg langue en",
        "tg explique": "tg explique rm",
        # le téléphone (appli Android, ou Termux)
        "ouvre": "ouvre whatsapp",
        "sms": "sms 0612345678 {salut}",
        "lampe": "lampe on",
        "dis": "dis {salut}",
        "web": "web wikipedia.org",
        "carte": "carte tour eiffel",
        "joue": "joue pierre",
    }


def remplir(ex):
    """Les mots à remplacer d'un exemple, dans la langue courante (NUMÉRO, NOM@ADRESSE, coucou)."""
    return ex.replace("{numero}", t("lex.ex.numero")).replace("{ssh}", t("lex.ex.ssh")) \
             .replace("{salut}", t("lex.ex.salut"))


def lexique(cmd):
    """L'exemple prêt à taper d'une commande du lexique (telle qu'affichée), ou None."""
    ex = _table().get(cmd.lower())
    return remplir(ex) if ex else None


# ---------------------------------------------------------------- 2. « il manque quelque chose »
# commande : (message, exemple, noms nécessaires après elle, options suivies d'une valeur, attend le clavier)
# « attend le clavier » : sans nom de fichier, la commande lit le clavier sans fin (cat, grep pomme…).
REGLES = {
    "mkdir": ("mkdir", "mkdir cabane", 1, (), False),
    "rmdir": ("rmdir", "rmdir cabane", 1, (), False),
    "touch": ("touch", "touch lettre.txt", 1, (), False),
    "cat": ("lire", "cat nid/repas.txt", 1, (), True),
    "less": ("lire", "less nid/repas.txt", 1, (), False),
    "head": ("lire", "head -n 3 nid/repas.txt", 1, ("-n", "-c"), True),
    "tail": ("lire", "tail -n 3 nid/repas.txt", 1, ("-n", "-c"), True),
    "wc": ("lire", "wc nid/repas.txt", 1, (), True),
    "sort": ("lire", "sort nid/repas.txt", 1, ("-k", "-t", "-o"), True),
    "rev": ("lire", "rev nid/repas.txt", 1, (), True),
    "stat": ("lire", "stat nid/repas.txt", 1, ("-c",), False),
    "cp": ("deux", "cp nid/repas.txt copie.txt", 2, (), False),
    "mv": ("deux", "mv copie.txt nid/", 2, (), False),
    "rm": ("rm", "rm lettre.txt", 1, (), False),
    "grep": ("grep", "grep pomme nid/repas.txt", 2, ("-e", "-m", "-A", "-B", "-C"), True),
    "chmod": ("chmod", "chmod 444 nid/repas.txt", 2, (), False),
    "find": ("find", 'find . -name "*.txt"', 1, (), False),
    "kill": ("kill", "kill {numero}", 1, ("-s",), False),
    "ping": ("reseau", "ping -c 3 example.com", 1, ("-c", "-i", "-W", "-s", "-w"), False),
    "curl": ("reseau", "curl -I https://example.com", 1, ("-o", "-H", "-X", "-d", "-A", "-u", "-e"), False),
    "nslookup": ("reseau", "nslookup example.com", 1, (), True),
    "ssh": ("ssh", "ssh {ssh}", 1, ("-p", "-i", "-l"), False),
    "nano": ("nano", "nano lettre.txt", 1, (), False),
    "git": ("git", "git init carnet", 1, ("-C", "-c"), False),
}
# les noms Windows (PowerShell demande alors les paramètres sans fin : même aide, même Ctrl+C)
WINDOWS = {"md": "mkdir", "new-item": "touch", "ni": "touch", "type": "cat", "gc": "cat", "get-content": "cat",
           "more": "less", "copy": "cp", "cpi": "cp", "copy-item": "cp", "move": "mv", "mi": "mv", "move-item": "mv",
           "del": "rm", "erase": "rm", "ri": "rm", "remove-item": "rm", "select-string": "grep", "sls": "grep",
           "stop-process": "kill", "spps": "kill", "notepad": "nano"}
EX_WINDOWS = {"touch": "New-Item lettre.txt", "cat": f"type {REPAS}", "less": f"more {REPAS}",
              "cp": f"copy {REPAS} copie.txt", "mv": "move copie.txt nid", "rm": "del lettre.txt",
              "grep": f"Select-String pomme {REPAS}", "kill": "Stop-Process -Id {numero}",
              "ping": "ping -n 3 example.com", "nano": "notepad lettre.txt", "chmod": f"attrib +r {REPAS}",
              "head": f"Get-Content {REPAS} -Head 3", "find": "Get-ChildItem -Recurse -Filter *.txt"}
SPECIAL = re.compile(r"[|<>;&`$()]")          # tuyau, redirection, plusieurs commandes : on ne devine pas


def canon(mot):
    """Le nom de référence d'une commande (copy → cp sous Windows, /bin/mkdir → mkdir)."""
    m = core.first_word(mot) or ""
    return WINDOWS.get(m, m) if IS_WIN else m


def manque(ligne):
    """La commande de référence si la ligne est une commande connue SANS ce qu'il lui faut après elle, sinon None."""
    if not ligne or SPECIAL.search(ligne):
        return None
    mots = ligne.split()
    cmd = canon(mots[0])
    regle = REGLES.get(cmd)
    if not regle:
        return None
    _cle, _ex, besoin, avec_valeur, _clavier = regle
    if cmd == "find":
        # find tout seul (ou « find . -name » sans le nom) : il faut lui dire quoi chercher
        if len(mots) == 1 or mots[-1] in ("-name", "-iname", "-type"):
            return cmd
        return None
    noms, saute = [], False
    for m in mots[1:]:
        if saute:
            saute = False
            continue
        if m.startswith("-") and len(m) > 1:
            saute = m in avec_valeur
            continue
        noms.append(m)
    return cmd if len(noms) < besoin else None


def _exemple_lecon(state, cmd):
    """La commande de la leçon en cours si elle commence par la même commande (mkdir nid plutôt que mkdir cabane)."""
    try:
        from . import lecons
        les, _ = lecons.lecon_courante(state)
        if not les:
            return None
        modele = les["steps"][state.get("step", 0)]["cmd"].split("    ")[0].strip()
    except (KeyError, IndexError, TypeError):
        return None
    if modele and canon(modele.split()[0]) == cmd and not manque(modele):
        return modele
    return None


def aide(state, ligne):
    """Le texte de la bulle d'aide pour cette ligne, ou None."""
    cmd = manque(ligne)
    if not cmd or (not IS_WIN and not core.commande_existe(core.first_word(ligne))):
        return None                       # absente de cet ordinateur : core.feed dit déjà qu'il ne la connaît pas
    cle, ex, _b, _v, clavier = REGLES[cmd]
    if IS_WIN:
        ex = EX_WINDOWS.get(cmd, ex)
    ex = remplir(_exemple_lecon(state, cmd) or ex)
    texte = t("aide.manque." + cle, cmd=core.first_word(ligne), ex=ex, **termes(palier(state)))
    if clavier or IS_WIN:
        texte += " " + t("aide.manque.bloque")
    return texte


def tick(state, lignes):
    """Après les commandes tapées : une bulle claire pour chaque commande à qui il manque quelque chose."""
    for ligne in lignes:
        if core.est_colle(ligne):
            continue
        texte = aide(state, ligne)
        if texte:
            core.say(state, texte, 14)
            core.log(state, texte)
            core.animer(state, "confus")
