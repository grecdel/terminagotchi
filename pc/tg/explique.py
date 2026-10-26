"""Expliquer chaque commande et chacune de ses options, en mots d'enfant (la grande maison).

1) OPTIONS : pour chaque commande, ce que veut dire chaque option utilisée dans le jeu (-r, -a, 444, +x…)
   et les symboles (> >> | . .. ~ *). Les textes sont dans les langues : « opt.<clé> », commençant par le
   sens du mot d'où vient la lettre (« récursif », « all »…).
2) VOISINES : les différences entre commandes proches (rm / rmdir / rm -r, cp / mv, cat / head / less…),
   textes « diff.<groupe> ».
3) Où c'est montré :
   - le lexique : sous chaque commande, ses options (lexique.py) ;
   - les leçons et l'histoire : la première fois qu'une option ou un symbole apparaît dans la commande d'une
     étape, la leçon l'explique en une phrase (« 💡 Le -r veut dire… ») ; quand l'étape est réussie, la
     créature le redit dans une bulle et ne le répète plus (state["options_vues"]) ;
   - la commande « tg explique rm » (ou « explique rm ») : la fiche complète d'une commande.
4) Pour les grands : sous chaque explication imagée, l'explication technique exacte (« grand.<commande> »,
   « optg.<clé> », avec les noms longs des options GNU : --recursive, --all, --human-readable…).
   Lexique et fiche : toujours. Leçons et bulles : à partir du palier 1 de vocabulaire (mots.py) ;
   au palier 0, seulement l'image (la version technique reste dans « explique »).
Mêmes tables dans l'appli Android (Explique.kt).
"""
from . import core
from .langue import brut, t
from .mots import palier
from .plateforme import DIM, RESET, BOLD, fg

OPTIONS = {
    "ls": {"-a": "all", "-l": "long", "-R": "recursif_ls"},
    "cp": {"-r": "recursif_cp", "-R": "recursif_cp"},
    "rm": {"-r": "recursif_rm", "-R": "recursif_rm", "-f": "force"},
    "mkdir": {"-p": "parents"},
    "chmod": {"444": "c444", "644": "c644", "600": "c600", "755": "c755", "+x": "plusx", "+r": "plusr"},
    "curl": {"-I": "info", "-o": "output"},
    "df": {"-h": "human"},
    "free": {"-h": "human"},
    "du": {"-s": "summary", "-h": "human"},
    "sort": {"-n": "numeric", "-r": "reverse", "-h": "human"},
    "find": {"-name": "name", "-size": "size"},
    "git": {"-m": "message", "--global": "global"},
    "grep": {"-i": "ignore", "-r": "recursif_grep", "-n": "numero", "-l": "liste", "-c": "count", "-v": "inverse"},
    "head": {"-n": "nombre", "-#": "nombre"},
    "tail": {"-n": "nombre", "-#": "nombre"},
    "ping": {"-c": "count_ping"},
    "ps": {"-A": "all_ps", "aux": "aux"},
    "tar": {"-czf": "tar", "czf": "tar"},
    "uname": {"-a": "all_uname", "-m": "machine"},
    "uniq": {"-c": "count_uniq"},
    "wc": {"-l": "lignes", "-w": "mots", "-c": "caracteres"},
    "base64": {"-d": "decode"},
    "ssh": {"-V": "version"},
    "python3": {"-m": "module"},
}
SYMBOLES = {">": "ecrase", ">>": "ajoute", "|": "tuyau", ".": "ici", "..": "avant", "~": "chambre", "*": "etoile"}
VOISINES = {"rm": "rm", "rmdir": "rm", "cp": "cp_mv", "mv": "cp_mv", "cat": "lire", "head": "lire", "tail": "lire",
            "less": "lire", "touch": "touch_mkdir", "mkdir": "touch_mkdir", "echo": "redir", "ls": "ls",
            "ps": "ps_kill", "kill": "ps_kill"}


def _commande(mot):
    return (core.first_word(mot) or "").lower()


def options(ligne):
    """Les options et symboles d'une commande, dans l'ordre : [(tel qu'écrit, clé)], sans doublon de clé."""
    out, vues = [], set()

    def ajouter(montre, cle):
        if cle and cle not in vues:
            vues.add(cle)
            out.append((montre, cle))

    for k, morceau in enumerate(ligne.split("|")):
        if k:
            ajouter("|", SYMBOLES["|"])                               # le tuyau, entre deux commandes
        mots = morceau.split()
        if not mots:
            continue
        cmd = _commande(mots[0])
        table = OPTIONS.get(cmd, {})
        for m in mots[1:]:
            m = m.strip("\"'")
            if m in (">", ">>"):
                ajouter(m, SYMBOLES[m])
            elif m in table:
                ajouter(m, table[m])
            elif m.startswith("-") and len(m) > 1 and m[1:].isdigit() and "-#" in table:
                ajouter(m, table["-#"])                               # head -3 : le nombre de lignes
            elif m.startswith("-") and not m.startswith("--") and m[1:].isalpha():
                for lettre in m[1:]:
                    ajouter("-" + lettre, table.get("-" + lettre))
            elif m in (".", "..", "~") or m.startswith(("../", "~/")):
                cle = ".." if m.startswith("..") else "~" if m.startswith("~") else "."
                ajouter(cle, SYMBOLES[cle])
            if "*" in m and not m.startswith("-"):
                ajouter("*", SYMBOLES["*"])
    return out


def phrase(montre, cle):
    """« 💡 Le -r veut dire « récursif » : … »"""
    return t("opt.phrase", opt=montre, sens=t("opt." + cle))


def grand(cle):
    """« Pour les grands : … » (l'explication technique exacte)."""
    return t("grand.ligne", texte=t(cle))


def grand_commande(nom, technique=None):
    """L'explication technique d'une commande : grand.<cmd>, sinon la technique du lexique."""
    if brut("grand." + nom) is not None:
        return grand("grand." + nom)
    return t("grand.ligne", texte=technique) if technique else None


def phrases(state, montre, cle):
    """L'image (la créature), puis la version des grands à partir du palier 1."""
    out = [phrase(montre, cle)]
    if palier(state) >= 1:
        out.append(grand("optg." + cle))
    return out


def nouvelles(state, cmd):
    """Les options de cette commande que la créature n'a pas encore expliquées."""
    vues = set(state.get("options_vues", []))
    return [(m, c) for m, c in options(cmd.split("    ")[0]) if c not in vues]


def apres_reussite(state, cmd):
    """Étape réussie : la créature explique (une seule fois) les nouvelles options, puis s'en souvient."""
    nouv = nouvelles(state, cmd)
    for montre, cle in nouv:
        for x in phrases(state, montre, cle):
            core.say(state, x, 14)
            core.log(state, x)
    state["options_vues"] = list(state.get("options_vues", [])) + [c for _m, c in nouv]


def lignes_options(cmd):
    """Les lignes « `-r` : sens » d'une commande, pour le lexique et la fiche."""
    table = OPTIONS.get(_commande(cmd), {})
    out, vues = [], set()
    for opt, cle in table.items():
        if cle in vues:
            continue
        vues.add(cle)
        montre = "-3" if opt == "-#" else opt
        out.append(f"`{montre}` : " + t("opt." + cle))
        out.append("   " + grand("optg." + cle))
    return out


def fiche(state, cmd):
    """La fiche complète d'une commande : image, exemple, options, voisines."""
    from . import exemples, lexique
    cmd = (cmd or "").strip()
    nom = _commande(cmd) if cmd else ""
    if not nom:
        return [t("explique.aide", ex="tg explique rm")]
    entree = None
    for _titre, _u, commandes in lexique._entrees():
        for c, image, technique in commandes:
            if c.split()[0].lower() == nom or c.lower() == cmd.lower():
                entree = (c, image, technique)
                break
        if entree:
            break
    opts = lignes_options(nom)
    diff = VOISINES.get(nom)
    if not entree and not opts and not diff:
        return [t("explique.inconnue", cmd=cmd, ex="tg explique rm")]
    out = ["", f" {fg(213)}{BOLD}" + t("explique.titre", cmd=entree[0] if entree else nom) + RESET]
    if entree:
        out.append("  " + entree[1])
    g = grand_commande(nom, entree[2] if entree else None)
    if g:
        out.append(f"  {DIM}{g}{RESET}")
    ex = exemples.lexique(entree[0] if entree else nom)
    if ex:
        out.append(f"  {fg(110)}↳ " + t("lex.exemple", ex=ex) + RESET)
    if opts:
        out += ["", f" {BOLD}" + t("explique.options") + RESET] + ["   " + o for o in opts]
    if diff:
        out += ["", f" {BOLD}" + t("explique.diff") + RESET, "   " + t("diff." + diff)]
    out.append(f"\n {DIM}" + t("explique.aide", ex="tg explique rm") + RESET)
    return out
