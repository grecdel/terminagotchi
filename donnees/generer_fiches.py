#!/usr/bin/env python3
"""Fabrique les fiches de séance pour les enseignants et animateurs (docs/fiches/), à partir des leçons du jeu.

    python3 donnees/generer_fiches.py

Une fiche par parcours (tronc commun, puis chaque branche / monde de l'arbre de compétences) : objectifs, déroulé
étape par étape (ce que la créature demande, la commande attendue, ce qu'il faut expliquer), questions à poser.
Les commandes sont celles de Linux / macOS ; le jeu affiche lui-même les variantes Windows et Android.
"""
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
os.environ.setdefault("HOME", str(RACINE / ".fiches_tmp"))      # le jeu ne doit rien écrire chez l'utilisateur
sys.path.insert(0, str(RACINE / "pc"))
import tg.plateforme as plateforme  # noqa: E402

plateforme.C = lambda unix, win=None, mac=None, android=None: unix
plateforme.installer = lambda p, noms=None: f"sudo apt install {p}"
import importlib  # noqa: E402

import tg.mondes  # noqa: E402
importlib.reload(tg.mondes)
import tg.lecons as lecons  # noqa: E402
importlib.reload(lecons)

SORTIE = RACINE / "docs" / "fiches"
MINUTES_PAR_ETAPE = 4


def nom_fichier(t):
    t = t.lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ô", "o"), ("î", "i"), ("û", "u"), ("ç", "c")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def cmd_md(c, tableau=False):
    c = c.replace("`", "'")
    return "`" + (c.replace("|", "\\|") if tableau else c) + "`"


def premier_mot(c):
    return c.split()[0] if c.split() else c


def fiche(titre, icone, desc, liste_lecons, ordre):
    etapes = sum(len(l["steps"]) for l in liste_lecons)
    duree = max(15, 5 * round(etapes * MINUTES_PAR_ETAPE / 5))
    commandes = []
    for l in liste_lecons:
        for s in l["steps"]:
            m = premier_mot(s["cmd"])
            if m not in commandes:
                commandes.append(m)
    o = [f"# {icone} {titre}", "", f"*{desc[0].upper() + desc[1:]}*", "",
         "| | |", "|---|---|",
         f"| **Durée** | environ {duree} min ({len(liste_lecons)} leçon{'s' if len(liste_lecons) > 1 else ''}, {etapes} étapes) |",
         f"| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |",
         "| **Prérequis** | " + ("aucun" if ordre == 0 else "le tronc commun (se repérer, créer, lire, chercher)") + " |",
         "| **Commandes vues** | " + ", ".join(cmd_md(c) for c in commandes) + " |",
         "| **Compétences gagnées** | " + ", ".join(l["skill"] for l in liste_lecons) + " |",
         "", "## Objectifs", ""]
    for l in liste_lecons:
        vues = []
        for s in l["steps"]:
            m = premier_mot(s["cmd"])
            if m not in vues:
                vues.append(m)
        o.append(f"- **{l['titre']}** : {l['steps'][0]['dit'][0].lower() + l['steps'][0]['dit'][1:]} "
                 f"(avec {', '.join(cmd_md(c) for c in vues)})")
    o += ["", "## Mise en route", "",
          "1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.",
          "2. " + ("Rien à choisir : le tronc commun démarre tout seul." if ordre == 0 else
                   f"Choisir la branche : touche [a] puis « {titre} » sur PC, `arbre` sur téléphone."),
          "3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).",
          "4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).", "",
          "## Déroulé", ""]
    for i, l in enumerate(liste_lecons, 1):
        o += [f"### {i}. {l['titre']} → compétence « {l['skill']} »", ""]
        if l.get("prep"):
            o.append("*Le jeu prépare tout seul les fichiers d'exercice : " +
                     ", ".join(cmd_md("~/terrain_terminagotchi/" + p) for p in l["prep"]) + ".*")
            o.append("")
        o += ["| Étape | La créature demande | Commande attendue | À expliquer |", "|---|---|---|---|"]
        for j, s in enumerate(l["steps"], 1):
            astuce = f" *Astuce : {s['astuce']}*" if s.get("astuce") else ""
            o.append(f"| {j} | {s['dit']} | {cmd_md(s['cmd'], tableau=True)} | {s['bravo']}{astuce} |".replace("\n", " "))
        o.append("")
    o += ["## Questions pour vérifier", ""]
    for c in commandes[:6]:
        o.append(f"- Que fait la commande `{c}` ? Dans quelle situation de la vie réelle te servirait-elle ?")
    o += ["- Qu'est-ce qui t'a surpris pendant cette séance ?", "",
          "## Pour aller plus loin", "",
          "- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.",
          "- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.", ""]
    return "\n".join(o)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    index = ["# Fiches de séance", "",
             "Pour les écoles, les clubs et les familles : une fiche par parcours du jeu, générée à partir des leçons",
             "elles-mêmes (`python3 donnees/generer_fiches.py`). Chaque fiche donne la durée, les objectifs, le déroulé",
             "étape par étape et des questions à poser. Le suivi des élèves se fait avec le **mode classe** du site.", "",
             "| Parcours | Leçons | Fiche |", "|---|---|---|"]
    parcours = [("Tronc commun", "🌱", "les bases : se repérer, créer et ranger, lire et chercher, les droits", lecons.TRONC)]
    parcours += [(nom, b["icone"], b["desc"], b["lecons"]) for nom, b in lecons.ARBRE.items()]
    for ordre, (titre, icone, desc, ls) in enumerate(parcours):
        f = f"{ordre:02d}-{nom_fichier(titre)}.md"
        (SORTIE / f).write_text(fiche(titre, icone, desc, ls, ordre), encoding="utf-8")
        index.append(f"| {icone} {titre} | {len(ls)} | [{f}]({f}) |")
    (SORTIE / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"{len(parcours)} fiches écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
