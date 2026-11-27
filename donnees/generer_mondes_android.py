#!/usr/bin/env python3
"""Fabrique app/src/main/java/fr/terminagotchi/Mondes.kt à partir des mondes du PC (pc/tg/mondes.py).

    python3 donnees/generer_mondes_android.py

Les leçons restent les mêmes sur PC et téléphone. Le téléphone n'a ni Python, ni compilateur, ni sqlite, ni git :
les leçons qui en ont besoin sont retirées ou remplacées ci-dessous (ANDROID).
"""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "pc"))

import tg.plateforme as plateforme  # noqa: E402

# Le téléphone utilise les commandes Linux (variante « android » quand elle existe)
plateforme.C = lambda unix, win=None, mac=None, android=None: android or unix
plateforme.installer = lambda p, noms=None: ""
import importlib  # noqa: E402

import tg.mondes as mondes_pc  # noqa: E402
importlib.reload(mondes_pc)
P = mondes_pc._p

CLES = {"Ondes": ("ondes", "Tour des Ondes"), "Citadelle": ("citadelle", "Citadelle"), "Crypte": ("crypte", "Crypte des Codes"),
        "Machines": ("machines", "Salle des Machines"), "Forge": ("forge", "Forge"), "Guilde": ("guilde", "Guilde des Bâtisseurs"),
        "Observatoire": ("observatoire", "Observatoire de l'IA"), "Données": ("donnees", "Salle des Données"),
        "Contrôle": ("controle", "Poste de Contrôle"), "Atelier": ("atelier", "Atelier"), "Nombres": ("nombres", "Ponts des Nombres")}

DE_SH = 'echo "Le dé roule… il tombe sur $((RANDOM % 6 + 1)) !"\n'

# titre de leçon → None (retirée) ou leçon de remplacement (même format que le PC)
ANDROID = {
    "La longueur d'onde": {"titre": "La longueur d'onde", "skill": "Sourcier", "steps": [
        {"dit": "Longueur d'onde = vitesse de la lumière ÷ fréquence. En millimètres, pour le Wi-Fi (2 400 MHz) :",
         "cmd": "echo $((300000 / 2400))", "re": r"300000\s*/\s*2400",
         "bravo": "125 mm = 12,5 cm. Les antennes mesurent souvent un quart ou une demie onde."},
        {"dit": "Et LoRa, la radio des objets connectés (868 MHz) ?", "cmd": "echo $((300000 / 868))", "re": r"300000\s*/\s*868",
         "bravo": "345 mm : une onde plus longue traverse mieux murs et collines. LoRa porte à des kilomètres !"},
    ]},
    "Les réseaux autour de moi": None,
    "Les machines dans la machine": None,
    "Mon premier jeu": {"titre": "Mon premier jeu", "skill": "Créateur de jeux", "prep": {P("forge", "de.sh"): DE_SH}, "steps": [
        {"dit": "Voici le code d'un petit jeu de dé. Lis-le !", "cmd": f"cat {P('forge', 'de.sh')}", "re": r"cat\b.*de\.sh",
         "bravo": "$RANDOM donne un nombre au hasard ; % 6 garde le reste de la division par 6 (0 à 5), + 1 → 1 à 6."},
        {"dit": "Lance le dé !", "cmd": f"sh {P('forge', 'de.sh')}", "re": r"^sh\b.*de\.sh", "bravo": "Tu as lancé ton premier programme de jeu."},
        {"dit": "Fabrique un dé à 20 faces : remplace 6 par 20.", "cmd": f"sed -i 's/% 6/% 20/' {P('forge', 'de.sh')}",
         "contient": (P("forge", "de.sh"), "% 20"), "bravo": "Relance-le : tu as modifié un jeu, comme tout programmeur qui commence."},
    ]},
    "Mon premier site": {"titre": "Mon premier site", "skill": "Tisseur de web", "steps": [
        {"dit": "Écris une page web.", "cmd": f"echo '<h1>Le site de ma créature</h1>' > {P('forge', 'index.html')}",
         "existe": P("forge", "index.html"), "bravo": "<h1> = un grand titre. Le HTML range le texte dans des balises."},
        {"dit": "Regarde le code de ta page.", "cmd": f"cat {P('forge', 'index.html')}", "re": r"cat\b.*index\.html",
         "bravo": "Un navigateur lit ces balises et dessine la page. Sur PC, le jeu t'apprend à l'héberger toi-même !"},
    ]},
    "Faire du son": None,
    "Compiler": None,
    "La base de données": None,
    "Les habitants": {"titre": "Les habitants", "skill": "Concierge", "steps": [
        {"dit": "Qui suis-je pour Android, et dans quels groupes ?", "cmd": "id", "re": r"^id\b",
         "bravo": "Chaque appli a son propre utilisateur (u0_a…) : c'est le bac à sable d'Android."},
        {"dit": "Quelle version d'Android fait tourner le téléphone ?", "cmd": "getprop ro.build.version.release", "re": r"^getprop\b",
         "bravo": "getprop lit les réglages du système : modèle, version, langue…"},
    ]},
    "Les services": {"titre": "Les services", "skill": "Régisseur", "steps": [
        {"dit": "Combien de programmes tournent ?", "cmd": "ps -A | wc -l", "re": r"^ps\b.*\|\s*wc",
         "bravo": "Des centaines : les services d'Android travaillent en permanence en arrière-plan."},
        {"dit": "Lis les derniers messages du journal de l'appli.", "cmd": "logcat -d -t 10", "re": r"^logcat\b",
         "bravo": "Le journal raconte tout : le premier réflexe d'un développeur ou d'un admin en cas de panne."},
    ]},
    "Les tâches planifiées": None,
}


def kt(t):
    return json.dumps(t, ensure_ascii=False).replace("$", "\\$")


def etape(st):
    args = [kt(st["dit"]), kt(st["cmd"]), kt(st["bravo"])]
    if "re" in st:
        args.append("re = r(" + kt(st["re"]) + ")")
    elif "existe" in st:
        args.append(f"fs = {{ File(it.terrain, {kt(st['existe'])}).exists() }}")
    elif "absent" in st:
        args.append(f"fs = {{ !File(it.terrain, {kt(st['absent'])}).exists() }}")
    elif "contient" in st:
        ch, tx = st["contient"]
        args.append(f"fs = {{ File(it.terrain, {kt(ch)}).let {{ f -> f.exists() && {kt(tx)} in f.readText() }} }}")
    else:
        raise ValueError(st)
    if st.get("astuce"):
        args.append("astuce = " + kt(st["astuce"]))
    return "Etape(" + ", ".join(args) + ")"


def lecon(l):
    prep = ", ".join(f"{kt(k)} to {kt(v)}" for k, v in (l.get("prep") or {}).items())
    etapes = ",\n                ".join(etape(s) for s in l["steps"])
    return (f"Lecon({kt(l['titre'])}, {kt(l['skill'])}, 1, listOf(\n                {etapes},\n            )"
            + (f", prep = mapOf({prep})" if prep else "") + ")")


def main():
    blocs = []
    for nom, b in mondes_pc.MONDES.items():
        cle, titre = CLES[nom]
        lecons = []
        for l in b["lecons"]:
            l = ANDROID.get(l["titre"], l) if l["titre"] in ANDROID else l
            if l:
                lecons.append(lecon(l))
        corps = ",\n            ".join(lecons)
        blocs.append(f"        {kt(cle)} to Branche({kt(cle)}, {kt(titre)}, {kt(b['icone'])}, {kt(b['stat'])}, {kt(b['desc'])}, listOf(\n"
                     f"            {corps},\n        )),")
    ordre = ", ".join(kt(CLES[n][0]) for n in mondes_pc.MONDES)
    code = f"""package fr.terminagotchi

// Généré par donnees/generer_mondes_android.py à partir de pc/tg/mondes.py — ne pas modifier à la main.

import java.io.File

/** Les mondes avancés du Terminaworld, version téléphone (le Port est dans Arbre.kt). */
object Mondes {{
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    val ORDRE = listOf({ordre})

    fun branches(): Map<String, Branche> = linkedMapOf(
{chr(10).join(blocs)}
    )
}}
"""
    (RACINE / "app/src/main/java/fr/terminagotchi/Mondes.kt").write_text(code, encoding="utf-8")
    print(f"Mondes.kt : {len(blocs)} mondes")


if __name__ == "__main__":
    main()
