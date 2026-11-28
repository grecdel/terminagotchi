"""Les données de la Bibliothèque du Temps (donnees/temps.json), ses fiches notions (charte de rigueur,
docs/programme.md § 7.1) et sa place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc,
paliers T1 → T4 et les empreintes, ponts vers la Guilde, la Crypte et la Citadelle, attirance, exploit « retrouver une
version perdue » et ses variantes réservées des types Roche et Ombre — des variantes qui EXISTENT déjà dans le
bestiaire, ni gardiens de la Citadelle ni déjà réservées par un autre monde), les maths des étapes et les étapes
rejouées dans bash.

    python3 donnees/temps/outils/fiches_temps.py   écrit donnees/temps.json, donnees/programme.json
                                                   et leurs copies (pc/tg, app/src/main/assets)

RÈGLES : tous les dépôts git sont créés DANS le terrain (terrain_terminagotchi/temps), sans « remote » réel, sans
push, sans compte. Les identités (user.name, user.email) sont des valeurs d'EXEMPLE (domaine .invalid, qui n'existe
pas), réglées dans le dépôt du terrain seulement (git config sans --global) : jamais la configuration de l'ordinateur.
Le grimoire du jeu a des dates fixes : ses empreintes (hash) sont les mêmes partout, et le petit git du téléphone
(PetitGit.kt) les retrouve à l'identique (vecteurs donnees/temps/vecteurs.json, faits avec le VRAI git).
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------- les identités d'exemple (domaine .invalid : RFC 2606)
IDENTITES = {
    "apprenti": {"nom": "Apprenti du Temps", "email": "apprenti@temps.invalid"},
    "bibliothecaire": {"nom": "Bibliothecaire du Temps", "email": "bibliothecaire@temps.invalid"},
    "ami": {"nom": "Ami du Temps", "email": "ami@temps.invalid"},
}
# le grimoire : 6 photos à dates fixes (le 1er janvier 2026 à 10 h UTC, puis un jour de plus à chaque photo).
# Chaque photo donne le contenu COMPLET des fichiers qu'elle change (lignes = clés de langue ; « S » = la ligne secrète,
# « secret : <formule> » — le mot « secret » reste le même dans toutes les langues pour `git log -S secret`).
GRIMOIRE = {
    "date0": 1767261600, "pas": 86400, "fuseau": "+0000", "secrets": 5, "mot": "secret",
    "photos": [
        {"message": "tp.grim.m1", "fichiers": {"grimoire.txt": ["tp.grim.titre", "tp.grim.f1"], "etiquettes.txt": ["tp.grim.e1"]}},
        {"message": "tp.grim.m2", "fichiers": {"grimoire.txt": ["tp.grim.titre", "tp.grim.f1", "S"]}},
        {"message": "tp.grim.m3", "fichiers": {"grimoire.txt": ["tp.grim.titre", "tp.grim.f1", "S", "tp.grim.f2"]}},
        {"message": "tp.grim.m4", "fichiers": {"grimoire.txt": ["tp.grim.titre", "tp.grim.f1", "S", "tp.grim.f2", "tp.grim.f3"]}},
        {"message": "tp.grim.m5", "fichiers": {"grimoire.txt": ["tp.grim.titre", "tp.grim.f1", "tp.grim.f2", "tp.grim.f3"]}},
        {"message": "tp.grim.m6", "fichiers": {"etiquettes.txt": ["tp.grim.e1", "tp.grim.e2"]}},
    ],
    "perte": 4,          # la photo (indice) qui a perdu la formule secrète : celle qu'on cherche avec git log -S
    "apparition": 1,     # la photo où elle est apparue
}
# T5 les empreintes : un petit mot (le même partout : son empreinte git est connue), et trois fichiers datés pour find -newer
EMPREINTES = {"mot": "temps\n", "mot_change": "Temps\n", "dates": {"ancien.txt": 3, "repere.txt": 2, "nouveau.txt": 1}}
# la pellicule (vue déployée) : chaque commande git a son image (§ 2.13 : un album de photos qui remonte le temps)
PELLICULE = [
    {"motif": r"^git\s+init\b", "outil": "git init", "de": "dossier", "vers": "album"},
    {"motif": r"^git\s+config\b", "outil": "git config", "de": "nom", "vers": "signature"},
    {"motif": r"^git\s+status\b", "outil": "git status", "de": "album", "vers": "etat"},
    {"motif": r"^git\s+add\b", "outil": "git add", "de": "fichier", "vers": "objectif"},
    {"motif": r"^git\s+commit\b", "outil": "git commit", "de": "objectif", "vers": "photo"},
    {"motif": r"^git\s+log\b", "outil": "git log", "de": "album", "vers": "pellicule"},
    {"motif": r"^git\s+(diff|show)\b", "outil": "git diff", "de": "deux_photos", "vers": "differences"},
    {"motif": r"^git\s+(restore|checkout\s+\S+\s+--)\b", "outil": "git restore", "de": "ancienne_photo", "vers": "fichier"},
    {"motif": r"^git\s+(switch|branch|checkout\s+-b)\b", "outil": "git switch", "de": "chemin", "vers": "deux_chemins"},
    {"motif": r"^git\s+merge\b", "outil": "git merge", "de": "deux_chemins", "vers": "un_chemin"},
    {"motif": r"^git\s+clone\b", "outil": "git clone", "de": "album", "vers": "copie"},
    {"motif": r"^git\s+pull\b", "outil": "git pull", "de": "copie", "vers": "album"},
    {"motif": r"^git\s+(hash-object|cat-file)\b", "outil": "git hash-object", "de": "fichier", "vers": "empreinte"},
]
COULEURS = {"album": 179, "photo": 229, "pellicule": 215, "differences": 203, "deux_chemins": 141, "un_chemin": 78,
            "copie": 117, "empreinte": 110}


def donnees_temps():
    return {
        "note": "Généré par donnees/temps/outils/fiches_temps.py ; lu par pc/tg/temps.py, Temps.kt et PetitGit.kt. Tous "
                "les dépôts sont dans le terrain (terrain_terminagotchi/temps), sans remote réel ni push ni compte ; les "
                "identités sont des EXEMPLES réglés dans le dépôt seulement (jamais git config --global).",
        "identites": IDENTITES, "grimoire": GRIMOIRE, "empreintes": EMPREINTES,
        "pellicule": {"regles": PELLICULE}, "couleurs": COULEURS,
        "branche": "reve", "copie": "copie_de_mon_ami",
    }


# ---------------------------------------------------------------- les fiches notions (charte de rigueur)
def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"tp.f.{nid}.enfant", "grands": f"tp.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"tp.f.{nid}.limite", "idees_fausses": [f"tp.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


S_GIT = "Git, documentation officielle (git-init, git-status, git-add, git-commit, git-config) : https://git-scm.com/docs"
S_BOOK = "Pro Git (S. Chacon, B. Straub), 2e édition, chapitres 2 et 3 : https://git-scm.com/book/fr/v2"
S_OBJ = "Pro Git, 10.2 « Les objets de Git » (blob, tree, commit, empreintes SHA-1) : https://git-scm.com/book/fr/v2/Les-tripes-de-Git-Les-objets-de-Git"
S_FIND = "GNU findutils, -newer : https://www.gnu.org/software/findutils/manual/html_node/find_html/Comparing-Timestamps.html"
# (un dépôt jetable : identité d'exemple réglée DANS le dépôt, dates fixes pour que les empreintes soient toujours les mêmes)
ID = "git config user.name 'Apprenti du Temps' && git config user.email apprenti@temps.invalid"
DATES = "export GIT_AUTHOR_DATE='1767261600 +0000' GIT_COMMITTER_DATE='1767261600 +0000'"
DEPOT = f"git init -q -b main a && cd a && {ID} && echo 'Jour 1' > c.txt"
UN = f"{DEPOT} && git add c.txt && {DATES} && git commit -qm 'Jour 1'"
FICHES = dict([
    fiche("git_album", r"(^git\s+(init|config|status|add|commit)\b|^(tg\s+)?temps\s+(plan|registre|album)\b|registre_du_temps|chronique\.txt)", [
        {"cmd": "git init -b main album", "motif": r"^Initialized empty Git repository in .*/album/\.git/$"},
        {"prepare": DEPOT, "cmd": "cd a && git status --short", "sortie": "?? c.txt"},
        {"prepare": f"{DEPOT} && git add c.txt", "cmd": "cd a && git status --short", "sortie": "A  c.txt"},
        {"prepare": f"{DEPOT} && git add c.txt", "cmd": f"cd a && {DATES} && git commit -m 'Jour 1'",
         "sortie": "[main (root-commit) 298a1bb] Jour 1\n 1 file changed, 1 insertion(+)\n create mode 100644 c.txt"},
        {"prepare": DEPOT, "cmd": "cd a && git config user.name", "sortie": "Apprenti du Temps"},
        {"prepare": "git init -q -b main a", "cmd": "cd a && git config --local --list | grep -c '^user\\.' || true", "sortie": "0"}],
        [S_GIT, S_BOOK]),
    fiche("git_histoire", r"(^git\s+(log|diff|show|restore|checkout\s+\S+\s+--|checkout\s+--)\b|^(tg\s+)?temps\s+(grimoire|perdu)\b|grimoire\.txt)", [
        {"prepare": UN, "cmd": "cd a && git log --oneline", "sortie": "298a1bb Jour 1"},
        {"prepare": f"{UN} && echo 'Jour 2' >> c.txt", "cmd": "cd a && git diff",
         "sortie": "diff --git a/c.txt b/c.txt\nindex 12f9021..5225e44 100644\n--- a/c.txt\n+++ b/c.txt\n@@ -1 +1,2 @@\n Jour 1\n+Jour 2"},
        {"prepare": f"{UN} && echo 'tache' >> c.txt", "cmd": "cd a && git restore c.txt && cat c.txt", "sortie": "Jour 1"},
        {"prepare": f"{UN} && echo 'secret : x' >> c.txt && git commit -qam 'Ajoute' && sed -i '/secret/d' c.txt && git commit -qam 'Range'",
         "cmd": "cd a && git log --format=%s -S secret", "sortie": "Range\nAjoute"},
        {"prepare": f"{UN} && echo 'secret : x' >> c.txt && git commit -qam 'Ajoute' && sed -i '/secret/d' c.txt && git commit -qam 'Range'",
         "cmd": "cd a && git checkout HEAD~1 -- c.txt && cat c.txt", "sortie": "Jour 1\nsecret : x"}],
        [S_GIT, S_BOOK, "Git, git-restore et git-checkout : https://git-scm.com/docs/git-restore"]),
    fiche("git_branches", r"(^git\s+(switch|branch|merge|checkout\s+-b)\b|^(tg\s+)?temps\s+(branches|conflit)\b|^sed\b.*\[<=>\]|^notepad\b.*chronique)", [
        {"prepare": UN, "cmd": "cd a && git switch -c reve && git branch", "sortie": "Switched to a new branch 'reve'\n  main\n* reve"},
        {"prepare": f"{UN} && git switch -qc reve && echo 'Jour 2 : un reve' >> c.txt && git commit -qam reve && git switch -q main"
                    " && echo 'Jour 2 : une balade' >> c.txt && git commit -qam balade",
         "cmd": "cd a && git merge reve", "code": "non0",
         "sortie": "Auto-merging c.txt\nCONFLICT (content): Merge conflict in c.txt\nAutomatic merge failed; fix conflicts and then commit the result."},
        {"prepare": f"{UN} && git switch -qc reve && echo 'Jour 2 : un reve' >> c.txt && git commit -qam reve && git switch -q main"
                    " && echo 'Jour 2 : une balade' >> c.txt && git commit -qam balade && (git merge reve >/dev/null || true)",
         "cmd": "cd a && cat c.txt", "sortie": "Jour 1\n<<<<<<< HEAD\nJour 2 : une balade\n=======\nJour 2 : un reve\n>>>>>>> reve"},
        {"prepare": f"{UN} && git switch -qc reve && echo 'Jour 2 : un reve' >> c.txt && git commit -qam reve && git switch -q main"
                    " && echo 'Jour 2 : une balade' >> c.txt && git commit -qam balade && (git merge reve >/dev/null || true)",
         "cmd": "cd a && sed -i '/^[<=>]\\{7\\}/d' c.txt && cat c.txt", "sortie": "Jour 1\nJour 2 : une balade\nJour 2 : un reve"}],
        [S_GIT, "Pro Git, 3.2 « Branches et fusions » : https://git-scm.com/book/fr/v2/Les-branches-avec-Git-Branches-et-fusions%C2%A0%3A-les-bases"]),
    fiche("git_partage", r"(^git\s+(clone|pull|remote)\b|^(tg\s+)?temps\s+(partage|ami|bateau)\b|\.gitignore|copie_de_mon_ami|brouillon\.tmp)", [
        {"prepare": UN, "cmd": "git clone -q a b && cd b && git log --oneline", "sortie": "298a1bb Jour 1"},
        {"prepare": f"{UN} && cd .. && git clone -q a b", "cmd": "cd b && git remote -v | head -1 | sed 's|\\t.*/|\\t|'",
         "sortie": "origin\ta (fetch)"},
        {"prepare": UN, "cmd": "cd a && echo '*.tmp' > .gitignore && touch brouillon.tmp && git status --short",
         "sortie": "?? .gitignore"}],
        [S_GIT, "Pro Git, 2.5 « Travailler avec des dépôts distants » : https://git-scm.com/book/fr/v2/Les-bases-de-Git-Travailler-avec-des-d%C3%A9p%C3%B4ts-distants",
         "Git, gitignore : https://git-scm.com/docs/gitignore"]),
    fiche("git_empreintes", r"(^git\s+(hash-object|cat-file)\b|sha1sum|^(tg\s+)?temps\s+(empreintes?|bilan)\b|^find\b.*-newer|mot\.txt)", [
        {"prepare": "printf 'temps\\n' > mot.txt", "cmd": "git hash-object mot.txt", "sortie": "eb51c8df438dd920beceb5c9ef1e691531fa8a2d"},
        {"cmd": "printf 'blob 6\\0temps\\n' | sha1sum", "sortie": "eb51c8df438dd920beceb5c9ef1e691531fa8a2d  -"},
        {"prepare": UN, "cmd": "cd a && git cat-file -p HEAD | head -1 | cut -c1-5", "sortie": "tree "},
        {"prepare": "touch -d '3 days ago' ancien.txt && touch -d '2 days ago' repere.txt && touch -d '1 day ago' nouveau.txt",
         "cmd": "find . -type f -newer repere.txt", "sortie": "./nouveau.txt"}],
        [S_OBJ, "FIPS 180-4, Secure Hash Standard (SHA-1) : https://csrc.nist.gov/pubs/fips/180-4/upd1/final", S_FIND]),
])

TEMPS = {"id": "temps", "types": ["roche", "ombre"], "requis": ["n4"], "chapitre": "temps",
         "paliers": [f"tp{i}" for i in range(6)],
         "attirance": {"cmds": ["git"], "familles": ["Constructs"]},
         "ponts": {"git_switch": ["guilde"], "empreintes": ["crypte"], "find_newer": ["citadelle"], "nano": ["forge"]},
         "reutilise": {"lecons": ["git0", "git1", "git2"], "quetes": ["q37"]},
         "exploits": [{"id": "temps.version", "nom": "recomp.temps.version", "recompense": "variante"}],
         "maths": ["hexadecimal"],
         "variantes_reservees": ["momiaou:soleil", "galetard:ruines", "follanterne:brume"]}

ETAPES = {"tp5.2": {"maths": ["hexadecimal"]}}


def rejeu():
    """Ce que le jeu affirme des vraies sorties de git (LC_ALL=C : les messages en anglais)."""
    return {
        "tp0.1": {"contient": ["registre_du_temps.txt"], "pourquoi": "hist.tp0.1.bravo : le registre"},
        "tp1.1": {"motif": r"^Initialized empty Git repository in .*/temps/album/\.git/$", "outil": "git",
                  "pourquoi": "hist.tp1.1.bravo : l'album est prêt, avec son passage secret .git"},
        "tp1.6": {"motif": r"Untracked files:[\s\S]*chronique\.txt", "outil": "git",
                  "pourquoi": "hist.tp1.6.bravo : chronique.txt est « non suivi » (Untracked)"},
        "tp1.8": {"motif": r"^\[(main|master) \(root-commit\) [0-9a-f]{7}\] Jour 1$", "outil": "git",
                  "pourquoi": "hist.tp1.8.bravo : la toute première photo (root-commit) et son numéro"},
        "tp2.2": {"lignes": 6, "outil": "git", "pourquoi": "hist.tp2.2.bravo : six photos dans le grimoire"},
        "tp2.4": {"motif": r"^\+gribouillis$", "outil": "git", "pourquoi": "hist.tp2.4.bravo : + la ligne ajoutée"},
        "tp2.6": {"lignes": 2, "outil": "git", "pourquoi": "hist.tp2.6.bravo : deux photos parlent du secret"},
        "tp2.7": {"motif": r"^-secret : ", "outil": "git", "pourquoi": "hist.tp2.7.bravo : - la ligne effacée"},
        "tp3.7": {"motif": r"^CONFLICT \(content\): Merge conflict in chronique\.txt$", "code": "non0", "outil": "git",
                  "pourquoi": "hist.tp3.7.bravo : un conflit"},
        "tp3.8": {"motif": r"^<<<<<<< HEAD$[\s\S]*^=======$[\s\S]*^>>>>>>> reve$", "outil": "git",
                  "pourquoi": "hist.tp3.8.bravo : les trois bornes du conflit"},
        "tp3.11": {"motif": r"^\*\s+[0-9a-f]{7} ", "outil": "git", "pourquoi": "hist.tp3.11.bravo : les deux chemins qui se rejoignent"},
        "tp4.4": {"motif": r"^Fast-forward$", "outil": "git", "pourquoi": "hist.tp4.4.bravo : la page de ton ami arrive"},
        "tp4.7": {"motif": r"\.gitignore", "outil": "git", "pourquoi": "hist.tp4.7.bravo : brouillon.tmp est ignoré"},
        "tp4.9": {"motif": r"^origin\t.*/temps/album(/\.)? \(fetch\)$", "outil": "git",
                  "pourquoi": "hist.tp4.9.bravo : origin, l'album d'où vient la copie"},
        "tp5.2": {"sortie": "eb51c8df438dd920beceb5c9ef1e691531fa8a2d", "outil": "git",
                  "pourquoi": "hist.tp5.2.bravo : l'empreinte de mot.txt"},
        "tp5.3": {"sortie": "eb51c8df438dd920beceb5c9ef1e691531fa8a2d  -",
                  "pourquoi": "hist.tp5.3.bravo : la même empreinte, calculée par sha1sum"},
        "tp5.5": {"sortie": "59b96ff1782835a2bc483e5f3332f1396b0abd1e", "outil": "git",
                  "pourquoi": "hist.tp5.5.bravo : une seule lettre change tout"},
        "tp5.7": {"motif": r"^tree [0-9a-f]{40}$[\s\S]*^parent [0-9a-f]{40}$", "outil": "git",
                  "pourquoi": "hist.tp5.7.bravo : chaque photo garde l'empreinte de la précédente"},
        "tp5.9": {"contient": ["./mot.txt", "./nouveau.txt"], "lignes": 2, "pourquoi": "hist.tp5.9.bravo : changés après le repère"},
    }


def main():
    G = donnees_temps()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/temps.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/temps.json", "app/src/main/assets/temps.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["mondes"] = [TEMPS if m["id"] == "temps" else m for m in P["mondes"]]
    for cle in ("etapes", "rejeu"):                   # les étapes de la Bibliothèque du Temps : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("tp") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Bibliothèque du Temps, {len(R)} étapes rejouées ; temps.json écrit")


if __name__ == "__main__":
    main()
