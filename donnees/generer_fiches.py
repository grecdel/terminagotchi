#!/usr/bin/env python3
"""Fabrique les fiches de séance pour les enseignants et animateurs (docs/fiches/), à partir des leçons du jeu.

    python3 donnees/generer_fiches.py                 (français → docs/fiches/)
    TG_LANGUE=en python3 donnees/generer_fiches.py    (anglais → docs/fiches/en/)

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

LANGUE = os.environ.get("TG_LANGUE", "fr")
SORTIE = RACINE / "docs" / "fiches" / ("" if LANGUE == "fr" else LANGUE)
from tg.langue import tr  # noqa: E402
EN = {'| **Durée** | environ {duree} min ({n} leçon{s}, {etapes} étapes) |': '| **Duration** | about {duree} min ({n} lesson{s}, {etapes} steps) |', '| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |': '| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |', '| **Prérequis** | ': '| **Prerequisites** | ', 'aucun': 'none', 'le tronc commun (se repérer, créer, lire, chercher)': 'the core lessons (finding your way, creating, reading, searching)', '| **Commandes vues** | ': '| **Commands covered** | ', '| **Compétences gagnées** | ': '| **Skills earned** | ', '## Objectifs': '## Objectives', 'avec': 'with', '## Mise en route': '## Getting started', "1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone.": '1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.', '2. Rien à choisir : le tronc commun démarre tout seul.': '2. Nothing to choose: the core lessons start by themselves.', '2. Choisir la branche : touche [a] puis « {titre} » sur PC, `arbre` sur téléphone.': '2. Choose the branch: press [a] then « {titre} » on PC, `arbre` on a phone.', '3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là).': '3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).', "4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu).": '4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).', '## Déroulé': '## Lesson plan', '### {i}. {titre} → compétence « {skill} »': '### {i}. {titre} → skill « {skill} »', "*Le jeu prépare tout seul les fichiers d'exercice : ": '*The game prepares the exercise files by itself: ', '| Étape | La créature demande | Commande attendue | À expliquer |': '| Step | The creature asks | Expected command | What to explain |', ' *Astuce : {a}*': ' *Tip: {a}*', '## Questions pour vérifier': '## Questions to check understanding', '- Que fait la commande `{c}` ? Dans quelle situation de la vie réelle te servirait-elle ?': '- What does the `{c}` command do? In which real-life situation would it help you?', "- Qu'est-ce qui t'a surpris pendant cette séance ?": '- What surprised you during this session?', '## Pour aller plus loin': '## Going further', "- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre.": '- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.', '- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun.': "- **Class mode** (census website → Class) lets you follow everyone's progress.", '# Fiches de séance': '# Lesson sheets', 'Pour les écoles, les clubs et les familles : une fiche par parcours du jeu, générée à partir des leçons': 'For schools, clubs and families: one sheet per learning path of the game, generated from the lessons', 'elles-mêmes (`python3 donnees/generer_fiches.py`). Chaque fiche donne la durée, les objectifs, le déroulé': 'themselves (`python3 donnees/generer_fiches.py`). Each sheet gives the duration, objectives, the plan', 'étape par étape et des questions à poser. Le suivi des élèves se fait avec le **mode classe** du site.': "step by step and questions to ask. Pupils are followed with the website's **class mode**.", '| Parcours | Leçons | Fiche |': '| Path | Lessons | Sheet |', 'Tronc commun': 'Core lessons', 'les bases : se repérer, créer et ranger, lire et chercher, les droits': 'the basics: finding your way, creating and tidying, reading and searching, permissions'}


def L(t):
    """Les phrases des fiches dans la langue demandée."""
    return EN.get(t, t) if LANGUE == "en" else t
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
         L("| **Durée** | environ {duree} min ({n} leçon{s}, {etapes} étapes) |").format(
             duree=duree, n=len(liste_lecons), s="s" if len(liste_lecons) > 1 else "", etapes=etapes),
         L("| **Public** | dès 10 ans ; dès 7 ans accompagné (lire les consignes à voix haute) |"),
         L("| **Prérequis** | ") + (L("aucun") if ordre == 0 else L("le tronc commun (se repérer, créer, lire, chercher)")) + " |",
         L("| **Commandes vues** | ") + ", ".join(cmd_md(c) for c in commandes) + " |",
         L("| **Compétences gagnées** | ") + ", ".join(tr(l["skill"]) for l in liste_lecons) + " |",
         "", L("## Objectifs"), ""]
    for l in liste_lecons:
        vues = []
        for s in l["steps"]:
            m = premier_mot(s["cmd"])
            if m not in vues:
                vues.append(m)
        o.append(f"- **{l['titre']}** : {l['steps'][0]['dit'][0].lower() + l['steps'][0]['dit'][1:]} "
                 f"({L('avec')} {', '.join(cmd_md(c) for c in vues)})")
    o += ["", L("## Mise en route"), "",
          L("1. Chaque élève (ou binôme) lance le jeu : `tg` sur PC, l'appli Terminagotchi sur téléphone."),
          L("2. Rien à choisir : le tronc commun démarre tout seul.") if ordre == 0 else
          L("2. Choisir la branche : touche [a] puis « {titre} » sur PC, `arbre` sur téléphone.").format(titre=titre),
          L("3. Se placer dans le terrain de jeu : `cd ~/terrain_terminagotchi` (les chemins des exercices partent de là)."),
          L("4. Les commandes se tapent **à la main** : le jeu refuse le copier-coller (c'est voulu)."), "",
          L("## Déroulé"), ""]
    for i, l in enumerate(liste_lecons, 1):
        o += [L("### {i}. {titre} → compétence « {skill} »").format(i=i, titre=l['titre'], skill=tr(l['skill'])), ""]
        if l.get("prep"):
            o.append(L("*Le jeu prépare tout seul les fichiers d'exercice : ") +
                     ", ".join(cmd_md("~/terrain_terminagotchi/" + p) for p in l["prep"]) + ".*")
            o.append("")
        o += [L("| Étape | La créature demande | Commande attendue | À expliquer |"), "|---|---|---|---|"]
        for j, s in enumerate(l["steps"], 1):
            astuce = L(" *Astuce : {a}*").format(a=s['astuce']) if s.get("astuce") else ""
            o.append(f"| {j} | {s['dit']} | {cmd_md(s['cmd'], tableau=True)} | {s['bravo']}{astuce} |".replace("\n", " "))
        o.append("")
    o += [L("## Questions pour vérifier"), ""]
    for c in commandes[:6]:
        o.append(L("- Que fait la commande `{c}` ? Dans quelle situation de la vie réelle te servirait-elle ?").format(c=c))
    o += [L("- Qu'est-ce qui t'a surpris pendant cette séance ?"), "",
          L("## Pour aller plus loin"), "",
          L("- La **salle d'entraînement** (`tg entrainement` / `entrainement`) fait réviser ces commandes au chronomètre."),
          L("- Le **mode classe** (site du recensement → Classe) permet de suivre la progression de chacun."), ""]
    return "\n".join(o)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    index = [L("# Fiches de séance"), "",
             L("Pour les écoles, les clubs et les familles : une fiche par parcours du jeu, générée à partir des leçons"),
             L("elles-mêmes (`python3 donnees/generer_fiches.py`). Chaque fiche donne la durée, les objectifs, le déroulé"),
             L("étape par étape et des questions à poser. Le suivi des élèves se fait avec le **mode classe** du site."), "",
             *(["🇬🇧 [English version](en/)", ""] if LANGUE == "fr" else ["🇫🇷 [Version française](../)", ""]),
             L("| Parcours | Leçons | Fiche |"), "|---|---|---|"]
    parcours = [(L("Tronc commun"), "🌱", L("les bases : se repérer, créer et ranger, lire et chercher, les droits"), lecons.TRONC)]
    parcours += [(nom, b["icone"], b["desc"], b["lecons"]) for nom, b in lecons.ARBRE.items()]
    for ordre, (titre, icone, desc, ls) in enumerate(parcours):
        f = f"{ordre:02d}-{nom_fichier(titre)}.md"
        (SORTIE / f).write_text(fiche(titre, icone, desc, ls, ordre), encoding="utf-8")
        index.append(f"| {icone} {titre} | {len(ls)} | [{f}]({f}) |")
    (SORTIE / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"{len(parcours)} fiches écrites dans {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
