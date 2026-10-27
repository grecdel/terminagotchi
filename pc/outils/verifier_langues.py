"""Contrôle des fichiers de langue de Terminagotchi (PC).

    python3 pc/outils/verifier_langues.py          (depuis la racine du dépôt)

Vérifie, pour chaque langue (pc/tg/langues/xx.json) par rapport au français (fr.json) :
  - qu'aucune clé ne manque et qu'il n'y a pas de clé inconnue ;
  - que le type est le même (texte ou liste) ; « terme.* » : exactement 3 paliers ;
  - que chaque {param} du français est présent dans la traduction (et rien d'autre) ;
  - que l'emoji de tête est gardé (il déclenche les notifications : ✨ ⬆ 🎓 🌳 …) ;
  - que les phrases criées (dress.fichier.cri) restent en MAJUSCULES ASCII (tr A-Z a-z) ;
  - que chaque traduction a autant de commandes balisées `…` (affichées en vert) que le français, et que
    chaque passage `…` tient sur une ligne ;
Et dans le code (pc/tg/*.py) : que toutes les clés utilisées existent en français.
Code de sortie 1 s'il y a une erreur.
"""
import ast
import glob
import json
import os
import re
import string
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
TG = os.path.join(os.path.dirname(ICI), "tg")
LANGUES = os.path.join(TG, "langues")
ESPACES = ("app", "core", "dress", "ep", "aide", "lec", "reg", "lex", "eq", "exp", "rec", "notif", "comp", "bur",
           "mini", "terme", "stat", "skill", "trait", "stade", "forme", "humeur", "branche", "rarete",
           "stade_bestiole", "frequence", "hist", "qu", "carte", "env", "ent", "guide", "type", "types", "intro", "deb", "vrai")


def params(texte):
    out = set()
    try:
        for _lit, champ, _spec, _conv in string.Formatter().parse(texte):
            if champ is not None:
                out.add(champ)
    except ValueError as e:
        out.add(f"<accolade mal fermée : {e}>")
    return out


def tete(texte):
    """Le symbole de tête (emoji) s'il y en a un."""
    texte = texte.lstrip()
    return texte[0] if texte and not texte[0].isalnum() and texte[0] not in "«(\"'[{.…*-+¡¿«" else ""


def charger(code):
    with open(os.path.join(LANGUES, code + ".json"), encoding="utf-8") as f:
        return json.load(f)


def marqueurs(v):
    """Nombre de backticks (les commandes à taper, en vert) de chaque texte d'une valeur."""
    return [x.count("`") for x in (v if isinstance(v, list) else [v]) if isinstance(x, str)]


def marques_ok(code, k, v):
    """Chaque ligne a un nombre pair de backticks : un passage `…` ne coupe jamais une ligne."""
    for x in (v if isinstance(v, list) else [v]):
        if isinstance(x, str) and any(l.count("`") % 2 for l in x.split("\n")):
            return [f"{code}: {k} : passage `…` ouvert sans être fermé sur la même ligne"]
    return []


def verifier_marques(code, k, v, w):
    """Autant de commandes balisées que le français (phrase par phrase si les listes ont la même longueur)."""
    a, b = marqueurs(v), marqueurs(w)
    if isinstance(v, list) and isinstance(w, list) and len(a) != len(b):
        a, b = [sum(a)], [sum(b)]
    if a != b:
        return [f"{code}: {k} : {sum(b)} marqueur(s) ` au lieu de {sum(a)} (les commandes en vert)"]
    return marques_ok(code, k, w)


def verifier_langue(code, fr, d):
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
        if type(v) is type(w):
            err += verifier_marques(code, k, v, w)
        if type(v) is not type(w):
            err.append(f"{code}: {k} : type différent ({type(v).__name__} ≠ {type(w).__name__})")
            continue
        if isinstance(v, list):
            if k.startswith("terme.") and len(w) != 3:
                err.append(f"{code}: {k} : il faut 3 paliers")
            if not w:
                err.append(f"{code}: {k} : liste vide")
            attendus = set().union(*(params(x) for x in v)) if v else set()
            for x in w:
                if not isinstance(x, str):
                    err.append(f"{code}: {k} : élément non texte")
                    continue
                p = params(x)
                if k.startswith("terme.") or k == "app.aide":
                    if p - attendus:
                        err.append(f"{code}: {k} : paramètres en trop {sorted(p - attendus)}")
                elif p != attendus:
                    err.append(f"{code}: {k} : paramètres {sorted(p)} au lieu de {sorted(attendus)} dans « {x[:50]} »")
            if k == "dress.fichier.cri":
                for x in w:
                    if not (x.isascii() and x == x.upper()):
                        err.append(f"{code}: {k} : « {x} » doit rester en MAJUSCULES ASCII (tr A-Z a-z)")
            if k == "app.aide":
                txt = "\n".join(w)
                for cmd in re.findall(r"(?:tg|terminagotchi\.pyz) [a-z]+", "\n".join(v)):
                    if cmd not in txt:
                        err.append(f"{code}: app.aide : la commande « {cmd} » a disparu")
        else:
            # {Processeur} (majuscule de début de phrase) et {processeur} sont interchangeables
            pv, pw = {x.lower() for x in params(v)}, {x.lower() for x in params(w)}
            if pv != pw:
                err.append(f"{code}: {k} : paramètres {sorted(pw)} au lieu de {sorted(pv)}")
            if tete(v) and tete(v) != tete(w) and tete(v) in "✨⬆🎓🌳🎯🐾💨🌲⚡":
                err.append(f"{code}: {k} : l'emoji de tête « {tete(v)} » doit rester en premier")
            if not w.strip() and v.strip():
                err.append(f"{code}: {k} : traduction vide")
    return err


def cles_du_code():
    """Toutes les chaînes du code qui ressemblent à une clé de langue."""
    motif = re.compile(r"^(" + "|".join(ESPACES) + r")\.[\w.\-]+$")
    trouvees = {}
    for f in glob.glob(os.path.join(TG, "*.py")):
        with open(f, encoding="utf-8") as fh:
            arbre = ast.parse(fh.read())
        for n in ast.walk(arbre):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and motif.match(n.value):
                trouvees.setdefault(n.value, f"{os.path.basename(f)}:{n.lineno}")
    return trouvees


def main():
    fr = charger("fr")
    erreurs = []
    codes = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(LANGUES, "*.json")))
    for k, ou in cles_du_code().items():
        # préfixes construits dans le code (t("stat." + x)…) : seules les clés complètes sont vérifiées
        if k.endswith(".") or k in fr or any(x.startswith(k + ".") for x in fr):
            continue
        if re.search(r"\.(txt|sh|json|html|bin)$", k):          # un nom de fichier (intro.json), pas une clé
            continue
        erreurs.append(f"code : clé absente de fr.json : {k} ({ou})")
    for k, v in fr.items():
        erreurs += marques_ok("fr", k, v)
        for x in (v if isinstance(v, list) else [v]):
            if "<accolade" in " ".join(params(x)):
                erreurs.append(f"fr : accolade mal fermée dans « {x[:60]} »")
    for code in codes:
        if code == "fr":
            continue
        erreurs += verifier_langue(code, fr, charger(code))
    attendues = {"fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur"}
    for code in sorted(attendues - set(codes)):
        erreurs.append(f"{code}: fichier de langue absent")
    for e in erreurs:
        print(" ✖", e)
    print(f"{len(codes)} langues · {len(fr)} clés · {len(erreurs)} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
