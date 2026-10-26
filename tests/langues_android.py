"""Contrôle des fichiers de langue de l'appli Android (app/src/main/assets/langues/xx.json).

    python3 tests/langues_android.py           contrôle (code de sortie 1 s'il y a une erreur)
    python3 tests/langues_android.py --sync    recopie d'abord depuis le PC (pc/tg/langues/xx.json) les clés
                                               communes, puis range les clés dans l'ordre du français

Une clé est « commune » quand elle existe aussi sur PC avec exactement le même texte français :
elle doit alors avoir la même traduction que sur PC (--sync la recopie). Les autres clés sont propres
à Android (téléphone, donjon, CTF, Doom, widget, notifications…).

Pour chaque langue, par rapport au français (fr.json) :
  - aucune clé manquante, aucune clé inconnue, même type (texte ou liste) ;
  - « terme.* » : exactement 3 paliers (image seule, image + mot, mot seul) ;
  - les {params} du français sont tous là, et rien d'autre ({Processeur} et {processeur} sont équivalents) ;
  - l'emoji de tête est gardé (✨ ⬆ 🎓 🌳 🐾 💨 🌲 ⚡ : il annonce un événement) ;
  - les phrases criées (dress.fichier.cri) restent en MAJUSCULES ASCII (la commande tr A-Z a-z) ;
  - les commandes à taper (compte creer, partie charger 2, langue en…) ne sont pas traduites ;
  - les mots du menu des parties (part.oui, part.mots.*) ne sont pas vides.
Et dans le code Kotlin : toutes les clés utilisées existent en français.
"""
import glob
import json
import os
import re
import sys
from collections import OrderedDict

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(ICI)
LANGUES = os.path.join(DEPOT, "app", "src", "main", "assets", "langues")
PC = os.path.join(DEPOT, "pc", "tg", "langues")
KOTLIN = os.path.join(DEPOT, "app", "src", "main", "java", "fr", "terminagotchi")
CODES = ["fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur"]
PARAM = re.compile(r"\{(\w+)\}")
EMOJIS = "✨⬆🎓🌳🎯🐾💨🌲⚡"
# commandes à taper telles quelles (si le français les contient, la traduction aussi)
COMMANDES = [
    "compte creer", "compte lier", "compte secours", "compte code", "compte site", "compte oublier",
    "compte partage on", "compte partage off", "partie nouvelle", "partie charger", "langue en", "langue xx",
    "notifs on", "notifs off", "notif on", "notif off", "notif reglages", "lampe on", "lampe off", "devine 10", "joue pierre", "renomme Pixel",
    "dressage abandon", "donjon nouveau", "cd 01_cache", "drapeau TG", "indice 1", "edite notes.txt",
    "edite carte.txt", "edite reglages.txt", "bestiaire Braisillon", "bestiaire Glitchou",
    "anime {nom_min} evolution", "cherche grep", "arbre scripts",
    "defi records", "site bestiaire", "site captures", "ouvre whatsapp",
    "carte tour eiffel", "appelle 0612345678", "sms 0612345678", "vibre 500",
    "reglages wifi", "equipe epee_rouillee", "bois potion_de_soin", "ls -a", "chmod 755", "cd escalier",
    "mv objet ~/terrain_terminagotchi/donjon/sac/", "tg compte lier", "ping -c 3", "applis what",
]


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def ecrire(chemin, d):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


def params(x):
    return {p.lower() for p in PARAM.findall(x)}


def tete(texte):
    texte = texte.lstrip()
    return texte[0] if texte and texte[0] in EMOJIS else ""


def communes(fr, pc_fr):
    return [k for k, v in fr.items() if pc_fr.get(k) == v]


def synchroniser(fr):
    """Recopie les clés communes depuis le PC et range chaque fichier dans l'ordre du français."""
    pc_fr = charger(os.path.join(PC, "fr.json"))
    com = communes(fr, pc_fr)
    for code in CODES[1:]:
        chemin = os.path.join(LANGUES, code + ".json")
        d = charger(chemin) if os.path.exists(chemin) else OrderedDict()
        pc = charger(os.path.join(PC, code + ".json"))
        for k in com:
            if k in pc:
                d[k] = pc[k]
        rangee = OrderedDict((k, d[k]) for k in fr if k in d)
        rangee.update((k, v) for k, v in d.items() if k not in rangee)
        ecrire(chemin, rangee)
    print(f"--sync : {len(com)} clés communes recopiées depuis le PC")


def verifier_langue(code, fr, d, pc, com):
    err = []
    for k in fr:
        if k not in d:
            err.append(f"{code}: clé manquante : {k}")
    for k in d:
        if k not in fr:
            err.append(f"{code}: clé inconnue : {k}")
    for k, v in fr.items():
        if k not in d:
            continue
        w = d[k]
        if type(v) is not type(w):
            err.append(f"{code}: {k} : type différent ({type(v).__name__} ≠ {type(w).__name__})")
            continue
        if k in com and pc is not None and k in pc and pc[k] != w:
            err.append(f"{code}: {k} : clé commune avec le PC mais traduction différente (lance --sync)")
        if isinstance(v, list):
            if k.startswith("terme.") and len(w) != 3:
                err.append(f"{code}: {k} : il faut 3 paliers (image seule, image + mot, mot seul)")
            if not w or not all(isinstance(x, str) and x.strip() for x in w):
                err.append(f"{code}: {k} : liste vide ou élément vide")
                continue
            attendus = set().union(*(params(x) for x in v))
            for x in w:
                p = params(x)
                if k.startswith("terme."):
                    if p - attendus:
                        err.append(f"{code}: {k} : paramètres en trop {sorted(p - attendus)}")
                elif attendus and p != attendus:
                    err.append(f"{code}: {k} : paramètres {sorted(p)} au lieu de {sorted(attendus)} dans « {x[:50]} »")
                elif not attendus and p:
                    err.append(f"{code}: {k} : paramètres en trop {sorted(p)}")
            if k == "dress.fichier.cri":
                for x in w:
                    if not (x.isascii() and x == x.upper()):
                        err.append(f"{code}: {k} : « {x} » doit rester en MAJUSCULES ASCII (tr A-Z a-z)")
        else:
            if params(v) != params(w):
                err.append(f"{code}: {k} : paramètres {sorted(params(w))} au lieu de {sorted(params(v))}")
            if tete(v) and tete(v) != tete(w):
                err.append(f"{code}: {k} : l'emoji de tête « {tete(v)} » doit rester en premier")
            if v.strip() and not w.strip():
                err.append(f"{code}: {k} : traduction vide")
            for c in COMMANDES:
                if c in v and c not in w:
                    err.append(f"{code}: {k} : la commande « {c} » ne doit pas être traduite")
    return err


ESPACES = ("app", "core", "dress", "dressa", "ep", "epa", "aide", "aidea", "lec", "leca", "reg", "lex", "lexa", "eq",
           "exp", "expa", "rec", "reca", "part", "terme", "stat", "skill", "trait", "stade", "forme", "humeur", "branche",
           "rarete", "stade_bestiole", "frequence", "mini", "arbre", "tel", "cre", "defi", "edite", "doom", "notifs", "ctf",
           "donjon", "jeu", "widget", "rappel", "rech", "shell", "term", "hist", "hista", "qu", "qua", "carte", "cartea")


def cles_du_code():
    """Les chaînes du code Kotlin qui ressemblent à une clé de langue (fichier:ligne)."""
    motif = re.compile(r'"((?:' + "|".join(ESPACES) + r')\.[\w.\-À-ÿ]+)"')
    trouvees = {}
    for f in sorted(glob.glob(os.path.join(KOTLIN, "*.kt"))):
        with open(f, encoding="utf-8") as fh:
            for i, ligne in enumerate(fh, 1):
                if ligne.strip().startswith(("//", "*")):
                    continue
                for m in motif.finditer(ligne):
                    trouvees.setdefault(m.group(1), f"{os.path.basename(f)}:{i}")
    return trouvees


def main():
    fr = charger(os.path.join(LANGUES, "fr.json"))
    if "--sync" in sys.argv:
        synchroniser(fr)
    pc_fr = charger(os.path.join(PC, "fr.json"))
    com = set(communes(fr, pc_fr))
    erreurs = []
    for k, ou in cles_du_code().items():
        if k.endswith(".") or k in fr or any(x.startswith(k + ".") for x in fr):
            continue
        if re.search(r"\.(txt|sh|json|html|bin)$", k):          # un nom de fichier (carte.txt), pas une clé
            continue
        erreurs.append(f"code : clé absente de fr.json : {k} ({ou})")
    for k in ("part.oui", "part.non", "part.mots.continuer", "part.mots.nouvelle", "part.mots.charger", "part.mots.compte"):
        if not fr.get(k):
            erreurs.append(f"fr : {k} manque (mots du menu des parties)")
    for code in CODES[1:]:
        chemin = os.path.join(LANGUES, code + ".json")
        if not os.path.exists(chemin):
            erreurs.append(f"{code}: fichier de langue absent")
            continue
        pcf = os.path.join(PC, code + ".json")
        erreurs += verifier_langue(code, fr, charger(chemin), charger(pcf) if os.path.exists(pcf) else None, com)
    for e in erreurs:
        print(" ✖", e)
    n = len([c for c in CODES if os.path.exists(os.path.join(LANGUES, c + ".json"))])
    print(f"{n} langues · {len(fr)} clés ({len(com)} communes avec le PC) · {len(erreurs)} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
