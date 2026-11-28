"""Les données de l'Observatoire de l'IA (donnees/observatoire.json), ses fiches notions (charte de rigueur,
docs/programme.md § 7.1) et sa place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 6 du tronc commun,
paliers O1 → O9, ponts, attirance, exploit « toutes les réponses fausses trouvées », variantes réservées des types Ciel
et Glace — des variantes qui EXISTENT déjà dans le bestiaire), les Ponts des Nombres des statistiques et des
probabilités, les maths des étapes et les étapes rejouées dans bash.

    python3 donnees/observatoire/outils/fiches_observatoire.py   écrit donnees/observatoire.json, donnees/programme.json
                                                                 et leurs copies (pc/tg, app/src/main/assets)

AUCUNE VRAIE IA : l'assistant, le devineur de type, le devineur de mots et les agents sont de PETITS PROGRAMMES DU JEU,
déterministes, hors ligne, sans compte ni clé, qui n'agissent que dans le terrain (terrain_terminagotchi/observatoire).
Les créatures des jeux de données sont relues ici dans le VRAI bestiaire du jeu (nom, famille, lieu, type classique),
jamais inventées ; le texte du devineur de mots est fait des VRAIES phrases de l'histoire du jeu (clés de langue).
Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, dans un terrain jetable.
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[3]
ICI = Path(__file__).resolve().parent


def _fr():
    spec = importlib.util.spec_from_file_location("textes_observatoire_fr", ICI / "textes_observatoire_fr.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.K


# ---------------------------------------------------------------- les jeux de données (espèces du VRAI bestiaire)
# O5 : 20 exemples étiquetés (10 « Feu », 10 « pas Feu »), puis la 21e créature, le piège : un Démon qui n'est PAS de
# Feu (Cauchemarre, type Ombre, dans la brume) — le devineur n'a vu que des Démons de Feu, et jamais la brume.
EXEMPLES = ["braisillon", "tritonnet", "cornichaud", "mousselin", "flamouche", "plumange", "cendrouille", "corbouh",
            "tisonnier", "cailloute", "chaudronne", "boulonnet", "infernaille", "gloupi", "fumerole", "pucerise",
            "fondelin", "plouftin", "cigalarme", "racinelle"]
PIEGE = "cauchemarre"
# O6 : les créatures des volcans seulement (volcan, lave, cendres) — toutes de Feu : le devineur croit que tout est Feu
VOLCAN = ["braisillon", "cornichaud", "flamouche", "cendrouille", "sulfurette", "tisonnier", "volcarnage", "fumerole",
          "magmastodonte", "cigalarme", "fondelin", "chaudrogre"]
# O6 : 5 créatures de test, jamais vues à l'entraînement (ni dans EXEMPLES ni dans VOLCAN)
AUTRES = ["raiyon", "ronceau", "lumignon", "engrenaille", "pyrodrac"]
# O4 : la liste à ranger par l'agent (avec 2 doublons) ; O9 : les invités de la fête (avec 3 doublons)
A_NOURRIR = ["Gloupi", "Plumange", "Corbouh", "Gloupi", "Braisillon", "Mousselin", "Plumange", "Cailloute"]
INVITES = ["Pucerise", "Tritonnet", "Fondelin", "Pucerise", "Racinelle", "Boulonnet", "Tritonnet", "Cigalarme", "Pucerise"]

# O7 : le texte du devineur de mots = les VRAIES phrases de l'histoire du jeu (début et fin des 10 premiers chapitres)
CORPUS = [f"hist.{c}.{x}" for c in ("reveil", "nid", "grenier", "cave", "bibliotheque", "machines", "dortoir", "atelier",
                                     "tour", "coeur") for x in ("debut", "fin")]

FAMILLES = {"Démons": "demons", "Élémentaires": "elementaires", "Constructs": "constructs", "Arthropodes": "arthropodes",
            "Abyssaux": "abyssaux", "Sylvestres": "sylvestres", "Célestes": "celestes", "Morts-vivants": "morts_vivants",
            "Aberrations": "aberrations"}


def creatures():
    sys.path.insert(0, str(D / "pc"))
    from tg import bestiaire as B, guide
    out = {}
    for i in dict.fromkeys(EXEMPLES + [PIEGE] + VOLCAN + AUTRES):
        e = B.espece(i)
        assert e and e["nom"].isascii(), i
        out[i] = {"nom": e["nom"], "famille": FAMILLES[e["famille"]], "lieu": e["zone"],
                  "type": guide.type_de(e, "classique")}
    return out


def verifier_donnees(C):
    """Les jeux de données font bien ce que dit la leçon (sinon on s'arrête : la leçon mentirait)."""
    feu = [i for i in EXEMPLES if C[i]["type"] == "feu"]
    assert len(feu) == 10 and len(EXEMPLES) == 20, len(feu)
    assert C[PIEGE]["famille"] == "demons" and C[PIEGE]["type"] != "feu"
    assert all(C[i]["type"] == "feu" for i in EXEMPLES if C[i]["famille"] == "demons")
    assert C[PIEGE]["lieu"] not in {C[i]["lieu"] for i in EXEMPLES}
    assert all(C[i]["type"] == "feu" for i in VOLCAN)
    assert not set(AUTRES) & (set(EXEMPLES) | set(VOLCAN))
    noms = sorted(C[i]["nom"] for i in EXEMPLES)
    assert all(not b.startswith(a) for a, b in zip(noms, noms[1:])), "aucun nom n'est le début d'un autre (tri)"


def donnees_observatoire():
    C = creatures()
    verifier_donnees(C)
    return {
        "note": "Généré par donnees/observatoire/outils/fiches_observatoire.py ; lu par pc/tg/observatoire.py et "
                "Observatoire.kt. Aucune vraie IA : de petits programmes du jeu, déterministes, hors ligne.",
        "creatures": C, "exemples": EXEMPLES, "piege": PIEGE, "volcan": VOLCAN, "autres": AUTRES,
        "piege_cause": "famille",
        "mission": {"verbes": ["compter", "trier", "lister"], "floue": "ob.mission.floue", "tri": "ob.mission.tri",
                    "exemple": "ob.mission.exemple", "filtre": "feu"},
        "secret": {"cle": "exemple-PAS-UNE-VRAIE-CLE-1234", "variable": "CLE_API"},
        "agent": {"liste": A_NOURRIR,
                  "propositions": [{"id": "copie", "sur": True, "texte": "cp a_nourrir.txt sauvegarde.txt"},
                                   {"id": "efface", "sur": False, "texte": "rm -rf ~/…"},
                                   {"id": "note", "sur": True, "texte": "echo ok > note.txt"}],
                  "boucle_tours": 50, "boucle_pause": 0.4},
        "corpus": CORPUS,
        "cjk": [[0x3040, 0x30FF], [0x3400, 0x4DBF], [0x4E00, 0x9FFF], [0xF900, 0xFAFF], [0xFF66, 0xFF9F]],
        "phrase_mots": 8,
        "questions": [{"id": "lignes", "verif": "wc -l devineur/exemples.txt"},
                      {"id": "modulo", "verif": "echo $((17 % 5))"},
                      {"id": "mot", "verif": "tr ' ' '\\n' < mots/histoire.txt | sort | uniq -c | sort -rn | head -3"},
                      {"id": "ls", "verif": "explique ls"},
                      {"id": "rm", "verif": "explique rm"}],
        "fausses": 2,
        "confier": [{"id": "expliquer", "rep": "c"}, {"id": "adresse", "rep": "g"}, {"id": "mot_de_passe", "rep": "g"},
                    {"id": "photo", "rep": "g"}, {"id": "idees", "rep": "c"}, {"id": "naissance", "rep": "g"}],
        "nuances": [{"id": "assuree", "rep": "v"}, {"id": "deepfake", "rep": "v"}, {"id": "droits", "rep": "f"},
                    {"id": "energie", "rep": "f"}, {"id": "forcement", "rep": "f"}],
        "equipe": {"invites": INVITES, "decoupe": ["liste", "compte", "invitations"],
                   "consignes": [{"id": "claire", "rep": True}, {"id": "floue", "rep": False},
                                 {"id": "dangereuse", "rep": False}],
                   "propositions": [{"id": "resume", "sur": True, "texte": "echo fete > resume.txt"},
                                    {"id": "sudo", "sur": False, "texte": "sudo chmod -R 777 /…"},
                                    {"id": "sauvegarde", "sur": True, "texte": "cp liste.txt sauvegarde_liste.txt"}],
                   "copies_par_tour": 7, "copies_max": 63},
        "lunette": {"regles": [
            {"motif": r"^(tg\s+)?assistant\b", "outil": "assistant", "de": "consigne", "vers": "rapport"},
            {"motif": r"^(tg\s+)?devine-type\b", "outil": "devine-type", "de": "exemples", "vers": "devinette"},
            {"motif": r"^(tg\s+)?devine-mot\b", "outil": "devine-mot", "de": "texte", "vers": "suite"},
            {"motif": r"^(tg\s+)?agent\b", "outil": "agent", "de": "consigne", "vers": "journal"},
            {"motif": r"^diff\b", "outil": "diff", "de": "deux_textes", "vers": "differences"},
            {"motif": r"^wc\b", "outil": "wc", "de": "fichier", "vers": "compte"},
            {"motif": r"^uniq\b.*\s-\w*c", "outil": "uniq -c", "de": "lignes", "vers": "effectifs"},
            {"motif": r"^grep\b.*\s-\w*c", "outil": "grep -c", "de": "lignes", "vers": "compte"},
            {"motif": r"^(sh|bash)\s+\S*tests?\.sh\b", "outil": "tests", "de": "travail", "vers": "verdict"}]},
        "couleurs": {"assistant": 117, "devine-type": 215, "devine-mot": 141, "agent": 78, "diff": 229, "wc": 229,
                     "uniq -c": 229, "grep -c": 229, "tests": 78},
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"ob.f.{nid}.enfant", "grands": f"ob.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"ob.f.{nid}.limite", "idees_fausses": [f"ob.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_ANSSI = "ANSSI, Recommandations de sécurité pour un système d'IA générative (2024) : https://cyber.gouv.fr/publications/recommandations-de-securite-pour-un-systeme-dia-generative"
S_CNIL = "CNIL, intelligence artificielle (dossiers et recommandations) : https://www.cnil.fr/fr/intelligence-artificielle"
S_COREUTILS = "GNU coreutils, manuel (wc, sort, uniq, tr, paste, tail, cut) : https://www.gnu.org/software/coreutils/manual/"
FICHES = dict([
    fiche("mission", r"(observatoire\s+(mission|plan|regles)\b|^(tg\s+)?assistant\s+\S*mission|mission\w*\.txt|rapport\.txt|coupole\.txt)", [
        {"prepare": "printf 'Braisillon Feu\\nTritonnet Eau\\nCornichaud Feu\\n' > c.txt", "cmd": "grep -c Feu c.txt",
         "sortie": "2"},
        {"prepare": "echo 'Compte les Feu dans c.txt' > mission.txt", "cmd": "cat mission.txt",
         "sortie": "Compte les Feu dans c.txt"},
        {"cmd": "assistant mission.txt > rapport.txt", "rejeu": "commande du jeu", "motif": "."}],
        [S_ANSSI, "Bash Reference Manual, Redirections (> écrit la sortie dans un fichier) : https://www.gnu.org/software/bash/manual/html_node/Redirections.html",
         S_CNIL]),
    fiche("verifier", r"(observatoire\s+(verifier|oubli)\b|^(sh\s+)?test\.sh\b|^sh\s+test\.sh|tri\.txt|^diff\b.*(tri|creatures)|^wc\b.*creatures)", [
        {"prepare": "printf 'b\\na\\nc\\n' > c.txt && printf 'a\\nc\\n' > t.txt", "cmd": "sort c.txt | diff - t.txt",
         "sortie": "2d1\n< b", "code": 1},
        {"prepare": "printf 'a\\nb\\nc\\n' > c.txt && printf 'a\\nc\\n' > t.txt", "cmd": "wc -l c.txt t.txt",
         "sortie": " 3 c.txt\n 2 t.txt\n 5 total"},
        {"prepare": "printf 'a\\nb\\n' > c.txt && printf 'a\\n' > t.txt",
         "cmd": "[ \"$(sort c.txt)\" = \"$(cat t.txt)\" ] && echo REUSSI || echo ECHEC", "sortie": "ECHEC"}],
        ["GNU diffutils, manuel (diff : lignes en moins « < », en plus « > ») : https://www.gnu.org/software/diffutils/manual/",
         S_COREUTILS, S_ANSSI]),
    fiche("secrets", r"(observatoire\s+(secrets?|cle)\b|config_partagee|\.env\b|\.gitignore|^export\s+CLE_API)", [
        {"prepare": "printf 'ville=Terminaville\\nCLE_API=exemple\\n' > c.txt", "cmd": "grep -n CLE c.txt",
         "sortie": "2:CLE_API=exemple"},
        {"prepare": "printf 'ville=Terminaville\\nCLE_API=exemple\\n' > c.txt", "cmd": "sed -i '/CLE_API/d' c.txt && cat c.txt",
         "sortie": "ville=Terminaville"},
        {"prepare": "echo CLE_API=exemple > .env", "cmd": "chmod 600 .env && stat -c %a .env", "sortie": "600"},
        {"cmd": "export CLE_API=exemple-pas-une-vraie-cle && echo ${#CLE_API}", "sortie": "25"}],
        ["OWASP, Secrets Management Cheat Sheet : https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
         "gitignore(5) : https://git-scm.com/docs/gitignore", "chmod(1), GNU coreutils ; Bash Reference Manual, export",
         S_ANSSI]),
    fiche("superviser", r"(observatoire\s+agent\b|^(tg\s+)?agent\s+(lance|refuse|accepte|valide|boucle|stop)\b|journal_agent|a_nourrir|^git\s+diff\b(?!.*fr\.txt)|chantier)", [
        {"prepare": "printf 'b\\na\\nb\\n' > l.txt && cp l.txt avant.txt", "cmd": "sort -u l.txt -o l.txt && diff avant.txt l.txt",
         "sortie": "1d0\n< b", "code": 1},
        {"cmd": "timeout 1 sleep 5; echo $?", "sortie": "124"},
        {"prepare": "git init -q -b main d && cd d && git config user.name A && git config user.email a@a.invalid && "
                    "printf 'b\\na\\n' > l.txt && git add l.txt && git commit -qm 1 && printf 'a\\nb\\n' > l.txt",
         "cmd": "cd d && git diff --stat | tail -1", "sortie": " 1 file changed, 1 insertion(+), 1 deletion(-)", "outil": "git"}],
        ["OWASP Top 10 for LLM Applications (2025), LLM06 « Excessive Agency » : https://genai.owasp.org/llm-top-10/",
         "NIST, AI Risk Management Framework 1.0 (2023) : https://www.nist.gov/itl/ai-risk-management-framework",
         "Bash Reference Manual, Signals (Ctrl+C envoie SIGINT) ; timeout(1), GNU coreutils", S_ANSSI]),
    fiche("apprendre", r"(observatoire\s+(apprendre|piege)\b|^(tg\s+)?devine-type\b|exemples\.txt|nouvelle\.txt|cerveau\.txt)", [
        {"prepare": "printf 'A x Feu\\nB y pas_Feu\\nC x Feu\\n' > e.txt", "cmd": "awk '{print $3}' e.txt | sort | uniq -c",
         "sortie": "      2 Feu\n      1 pas_Feu"},
        {"prepare": "printf 'A x Feu\\nB y pas_Feu\\nC x Feu\\n' > e.txt", "cmd": "cut -d ' ' -f 3 e.txt | sort | uniq -c",
         "sortie": "      2 Feu\n      1 pas_Feu"},
        {"cmd": "devine-type apprends exemples.txt", "rejeu": "commande du jeu", "motif": "."}],
        ["Inria et Class'Code, MOOC « L'Intelligence Artificielle… avec intelligence ! » : https://pixees.fr/classcode-v2/iai/",
         "Éduscol, programme de NSI de première : algorithmes d'apprentissage (k plus proches voisins) : https://eduscol.education.fr/",
         "scikit-learn, Naive Bayes (classer en comptant des exemples) : https://scikit-learn.org/stable/modules/naive_bayes.html",
         "GNU awk, manuel : https://www.gnu.org/software/gawk/manual/ ; " + S_COREUTILS]),
    fiche("biais", r"(observatoire\s+biais\b|volcan\.txt|autres\.txt)", [
        {"prepare": "printf 'volcan\\nvolcan\\nvolcan\\nlagon\\n' > l.txt", "cmd": "sort l.txt | uniq -c | sort -rn | head -1",
         "sortie": "      3 volcan"},
        {"cmd": "echo $((1 * 100 / 5))", "sortie": "20"}],
        ["Défenseur des droits et CNIL, « Algorithmes : prévenir l'automatisation des discriminations » (2020) : https://www.defenseurdesdroits.fr/",
         "Règlement européen sur l'IA (AI Act, 2024), art. 10 : qualité et représentativité des données d'entraînement",
         S_CNIL]),
    fiche("modele_langage", r"(observatoire\s+(mots|perroquet)\b|^(tg\s+)?devine-mot\b|histoire\.txt|mots\.txt|^tr\b|paste\b)", [
        {"cmd": "echo 'le chat dort et le chat mange' | tr ' ' '\\n' | sort | uniq -c | sort -rn | head -1",
         "sortie": "      2 le"},
        {"prepare": "echo 'le chat dort et le chat mange' | tr ' ' '\\n' > m.txt",
         "cmd": "tail -n +2 m.txt | paste -d ' ' m.txt - | sort | uniq -c | sort -rn | head -1", "sortie": "      2 le chat"}],
        ["D. Jurafsky et J. H. Martin, Speech and Language Processing, chap. 3 « N-gram Language Models » : https://web.stanford.edu/~jurafsky/slp3/",
         "C. E. Shannon, « A Mathematical Theory of Communication » (1948) : textes fabriqués mot après mot avec des paires",
         S_COREUTILS, S_ANSSI]),
    fiche("esprit_critique", r"(observatoire\s+(esprit|confier|nuances)\b|^(tg\s+)?assistant\s+(questions|fausses)\b|^explique\s+(ls|rm)\b|^echo\s+\$\(\(17\s*%\s*5\)\)|^wc\b.*exemples)", [
        {"cmd": "echo $((17 % 5))", "sortie": "2"},
        {"prepare": "printf 'a\\nb\\n' > f.txt", "cmd": "wc -l < f.txt", "sortie": "2"}],
        ["CLEMI, éducation aux médias et à l'information : https://www.clemi.fr/", S_CNIL,
         "Règlement européen sur l'IA (AI Act, 2024), art. 50 : signaler les contenus hypertruqués (deepfakes)",
         "Code de la propriété intellectuelle (droit d'auteur) : https://www.legifrance.gouv.fr/",
         "AIE (Agence internationale de l'énergie), Energy and AI (2025) : https://www.iea.org/reports/energy-and-ai"]),
    fiche("equipe_agents", r"(observatoire\s+(equipe|decoupe|consigne)\b|^(tg\s+)?agent\s+(equipe|bilan)\b|journal_equipe|tests\.sh|compte\.txt|invites\.txt|copies\b|\bSTOP\b)", [
        {"prepare": "mkdir -p eq", "cmd": "touch eq/STOP && [ -e eq/STOP ] && echo arret", "sortie": "arret"},
        {"prepare": "printf 'a\\nb\\n' > l.txt", "cmd": "wc -l < l.txt > c.txt && cat c.txt", "sortie": "2"},
        {"prepare": "printf 'a\\nb\\na\\n' > i.txt && sort -u i.txt > l.txt", "cmd": "diff i.txt l.txt", "sortie": "3d2\n< a", "code": 1}],
        ["OWASP Top 10 for LLM Applications (2025), LLM06 « Excessive Agency » : https://genai.owasp.org/llm-top-10/",
         "NIST, AI Risk Management Framework 1.0 (2023) : garder un humain qui supervise et peut arrêter", S_ANSSI]),
])

OBSERVATOIRE = {"id": "observatoire", "types": ["ciel", "glace"], "requis": ["n4", "n6"],
                "paliers": [f"ob{i}" for i in range(10)], "chapitre": "observatoire",
                "attirance": {"cmds": ["diff", "uniq", "wc", "assistant", "devine-type"], "familles": ["Célestes"]},
                "ponts": {"sort": ["donnees"], "uniq": ["donnees"], "grep": ["donnees"], "export": ["controle"],
                          "git": ["temps"], "chmod": ["citadelle"]},
                "exploits": [{"id": "observatoire.fausses", "nom": "recomp.observatoire.fausses", "recompense": "variante"}],
                "maths": ["effectifs", "frequences", "probabilites"],
                "variantes_reservees": ["seraphibou:cosmique", "zyeuton:brume", "mutaloupe:cristal"]}


def maths_fiche(mid, prerequis, niveau, vrai, sources):
    return mid, {"fiche": True, "titre": f"maths.{mid}.titre", "question": f"maths.{mid}.question", "prerequis": prerequis,
                 "niveau": niveau, "enfant": f"maths.{mid}.enfant", "grands": f"maths.{mid}.grands", "vrai_terminal": vrai,
                 "limite_image": f"maths.{mid}.limite", "idees_fausses": [f"maths.{mid}.idee"],
                 "exemples": [f"maths.{mid}.ex1", f"maths.{mid}.ex2", f"maths.{mid}.ex3"],
                 "exercice": {"type": mid, "consigne": f"maths.{mid}.exo", "erreur": f"maths.{mid}.erreur"},
                 "mots_cles": f"maths.{mid}.kw", "sources": sources, "relu_par": None}


S_STATS = "Programmes de mathématiques des cycles 3 et 4 (organisation et gestion de données, effectifs, fréquences, probabilités) : https://eduscol.education.fr/"
MATHS = dict([
    maths_fiche("effectifs", ["comptage"], "primaire", [
        {"cmd": "printf 'Feu\\nEau\\nFeu\\n' | sort | uniq -c", "sortie": "      1 Eau\n      2 Feu"},
        {"cmd": "printf 'Feu\\nEau\\nFeu\\n' | grep -c Feu", "sortie": "2"}], [S_STATS, S_COREUTILS]),
    maths_fiche("frequences", ["effectifs", "division"], "college", [
        {"cmd": "echo $((10 * 100 / 20))", "sortie": "50"}, {"cmd": "echo $((1 * 100 / 5))", "sortie": "20"}],
        [S_STATS, "Bash, Shell Arithmetic : https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html"]),
    maths_fiche("probabilites", ["frequences"], "college", [
        {"cmd": "echo $((3 * 100 / 4))", "sortie": "75"}, {"cmd": "echo $((1 * 100 / 4))", "sortie": "25"}],
        [S_STATS, "D. Jurafsky et J. H. Martin, Speech and Language Processing, chap. 3 (probabilité du mot suivant)"]),
])

ETAPES = {"ob5.2": {"maths": ["effectifs"]}, "ob6.2": {"maths": ["frequences"]}, "ob6.4": {"maths": ["frequences"]},
          "ob7.4": {"maths": ["probabilites"]}, "ob2.2": {"maths": ["effectifs"]}}


def rejeu():
    K = _fr()
    return {
        "ob0.1": {"contient": ["coupole.txt", "carnet_de_l_observatoire.txt", "missions"],
                  "pourquoi": "hist.ob0.1.bravo : la coupole, le carnet, les missions"},
        "ob1.1": {"sortie": K["ob.mission.floue"], "pourquoi": "hist.ob1.1.bravo : une consigne floue"},
        "ob2.2": {"motif": r"^\s*20 creatures\.txt\n\s*19 tri\.txt", "pourquoi": "hist.ob2.2.bravo : 20 lignes, 19 lignes"},
        "ob2.3": {"motif": r"^\d+d\d+\n< \w+ \w+$", "pourquoi": "hist.ob2.3.bravo : une ligne en moins (<)"},
        "ob2.4": {"motif": "✖", "pourquoi": "hist.ob2.4.bravo : le test échoue"},
        "ob2.6": {"motif": "✔", "pourquoi": "hist.ob2.6.bravo : le test réussit"},
        "ob3.1": {"motif": r"^\d+:CLE_API=", "pourquoi": "hist.ob3.1.bravo : la clé est en clair"},
        "ob5.2": {"sortie": f"     10 {K['ob.label.feu']}\n     10 {K['ob.label.pas_feu']}",
                  "pourquoi": "hist.ob5.2.bravo : 10 et 10, équilibré"},
        "ob6.1": {"motif": r"^\s+\d+ (volcan|lave|cendres)$", "pourquoi": "hist.ob6.1.bravo : seulement des volcans"},
        "ob6.2": {"sortie": f"     12 {K['ob.label.feu']}", "pourquoi": "hist.ob6.2.bravo : 12 Feu, 0 autre"},
        "ob7.1": {"egal_jeu": "mot_frequent", "pourquoi": "hist.ob7.1.bravo : le mot le plus fréquent"},
        "ob7.3": {"egal_jeu": "paire_frequente", "pourquoi": "hist.ob7.3.bravo : la paire la plus fréquente"},
        "ob9.5": {"motif": r"^\d+$", "pourquoi": "hist.ob9.5.bravo : le nombre de copies"},
        "ob9.9": {"motif": "✖", "pourquoi": "hist.ob9.9.bravo : un test échoue (le compte)"},
        "ob9.11": {"motif": r"\A(?![\s\S]*✖)[\s\S]*✔", "pourquoi": "hist.ob9.11.bravo : tous les tests passent"},
    }


def main():
    G = donnees_observatoire()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/observatoire.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/observatoire.json", "app/src/main/assets/observatoire.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["maths"].update(MATHS)
    mondes = [m for m in P["mondes"] if m["id"] != "observatoire"]
    i = next((k for k, m in enumerate(mondes) if m["id"] == "crypte"), len(mondes) - 1) + 1
    mondes.insert(i, OBSERVATOIRE)
    P["mondes"] = mondes
    for cle in ("etapes", "rejeu"):                   # les étapes de l'Observatoire : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("ob") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de l'Observatoire, {len(MATHS)} ponts des nombres, {len(R)} étapes rejouées ; "
          "observatoire.json écrit")


if __name__ == "__main__":
    main()
