"""Les fiches notions de la Citadelle (charte de rigueur, docs/programme.md § 7.1) et sa place dans donnees/programme.json :
le monde (prérequis = niveaux 0 à 6 du tronc commun, paliers, ponts, attirance, exploits, variantes réservées aux
Démons), les maths des étapes et les étapes rejouées dans bash.

    python3 donnees/citadelle/outils/fiches_citadelle.py      écrit donnees/programme.json et ses deux copies

Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, dans un terrain jetable :
seulement des fichiers fabriqués sur place, des processus `sleep` renommés arrêtés à la fin, openssl en local avec
une clé d'EXEMPLE. Rien ne sort de la machine, rien n'est écrit hors du terrain.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"cit.f.{nid}.enfant", "grands": f"cit.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"cit.f.{nid}.limite", "idees_fausses": [f"cit.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


JOURNAL = ("printf '2026-10-31 06:00:00 OK 198.51.100.7 porte-nord sentinelle\\n"
           "2026-10-31 06:00:41 ECHEC 203.0.113.66 poterne admin\\n2026-10-31 06:01:22 ECHEC 203.0.113.66 poterne root\\n"
           "2026-10-31 06:02:03 ECHEC 198.51.100.23 poterne forgeron\\n' > acces.log")

FICHES = dict([
    fiche("utilisateurs", r"(groupes\.txt|habitants\.txt|^(tg\s+)?citadelle\s+chown\b|^chown\b|^groups\b)", [
        {"prepare": "printf 'veilleurs:x:2001:gardien,sentinelle\\ncuisine:x:1002:forgeron\\n' > groupes.txt",
         "cmd": "grep veilleurs groupes.txt | cut -d: -f4", "sortie": "gardien,sentinelle"},
        {"cmd": "id -u", "motif": r"^\d+$"},
        {"cmd": "touch f; chown root f 2>&1; echo \"code $?\"", "motif": r"(Operation not permitted|code 0)"}],
        ["man 5 passwd : https://man7.org/linux/man-pages/man5/passwd.5.html",
         "man 5 group : https://man7.org/linux/man-pages/man5/group.5.html",
         "POSIX.1-2024, chown : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chown.html",
         "man 1 id"]),
    fiche("umask", r"(\bumask\b|^(tg\s+)?citadelle\s+masque\b)", [
        {"cmd": "(umask 077; touch f); stat -c %a f", "sortie": "600"},
        {"cmd": "(umask 022; touch f; mkdir d); stat -c %a f d", "sortie": "644\n755"}],
        ["POSIX.1-2024, umask : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/umask.html",
         "man 2 umask : https://man7.org/linux/man-pages/man2/umask.2.html"]),
    fiche("journaux", r"(acces\.log|journaux/)", [
        {"prepare": JOURNAL, "cmd": "grep -c ECHEC acces.log", "sortie": "3"},
        {"prepare": JOURNAL, "cmd": "grep ECHEC acces.log | cut -d ' ' -f 4 | sort | uniq -c | sort -n",
         "sortie": "      1 198.51.100.23\n      2 203.0.113.66"},
        {"prepare": JOURNAL, "cmd": "tail -n 1 acces.log", "sortie": "2026-10-31 06:02:03 ECHEC 198.51.100.23 poterne forgeron"}],
        ["man 1 grep, man 1 cut, man 1 sort, man 1 uniq (GNU coreutils)",
         "RFC 5737 (adresses réservées à la documentation : 198.51.100.0/24, 203.0.113.0/24)",
         "ANSSI, Recommandations de sécurité pour la journalisation des systèmes Microsoft Windows et GNU/Linux (2022)",
         "man 1 journalctl"]),
    fiche("find_newer", r"-newer\b", [
        {"prepare": "touch -d '2020-01-01' vieux; touch -d '2021-01-01' repere; touch neuf",
         "cmd": "find . -newer repere -type f | sort", "sortie": "./neuf"},
        {"prepare": "mkdir -p a/b; touch -d '2021-01-01' repere; touch a/b/x.glitch",
         "cmd": "find . -name '*.glitch'", "sortie": "./a/b/x.glitch"}],
        ["GNU findutils, find : https://www.gnu.org/software/findutils/manual/html_mono/find.html (-newer, -name, -delete)",
         "POSIX.1-2024, find : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html"]),
    fiche("cheval", r"cadeau\.sh", [
        {"prepare": "printf '#!/bin/sh\\necho surprise\\n' > cadeau.sh; chmod 755 cadeau.sh",
         "cmd": "chmod -x cadeau.sh; ./cadeau.sh", "code": "non0", "motif": r"Permission denied"},
        {"prepare": "printf '#!/bin/sh\\nrm -f bac/*.txt\\n' > cadeau.sh", "cmd": "grep -n rm cadeau.sh",
         "sortie": "2:rm -f bac/*.txt"}],
        ["ANSSI, Guide d'hygiène informatique (2017), mesure 13 : n'installer que des logiciels de confiance",
         "MITRE ATT&CK, T1204 « User Execution » (l'utilisateur lance lui-même le piège)",
         "POSIX.1-2024, chmod : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html"]),
    fiche("processus_suspects", r"(fictif|^(tg\s+)?citadelle\s+ps\b)", [
        {"cmd": "bash -c 'exec -a miner_fictif sleep 30' & sleep 0.5; ps -eo args | grep -c '^miner_fictif 30$'; kill $!",
         "sortie": "1"},
        {"cmd": "bash -c 'exec -a flood_fictif sleep 30' & p=$!; sleep 0.3; kill $p; wait $p 2>/dev/null; "
                "ps -p $p > /dev/null; echo \"vivant $?\"", "sortie": "vivant 1"}],
        ["man 1 ps : https://man7.org/linux/man-pages/man1/ps.1.html", "man 1 kill, man 7 signal (SIGTERM)",
         "bash(1), exec -a nom (le nom affiché du processus)"]),
    fiche("empreinte", r"(sha256sum|empreintes|\.sha256\b|get-filehash)", [
        {"prepare": "printf 'bonjour\\n' > a", "cmd": "sha256sum a",
         "sortie": "9cec0af545144159bac85c7b908d5e0b9b0ef961497401c5ad8da26f065ad926  a"},
        {"prepare": "printf 'bonjour\\n' > a; sha256sum a > s; printf 'bonjour!\\n' > a", "cmd": "sha256sum -c s",
         "code": "non0", "motif": r"^a: FAILED$"}],
        ["FIPS 180-4 (SHA-256)", "man 1 sha256sum (GNU coreutils)",
         "ANSSI, Guide de sélection d'algorithmes cryptographiques (2021)"]),
    fiche("sauvegarde", r"^tar\b", [
        {"prepare": "mkdir p; echo parchemin > p/a.txt", "cmd": "tar czf s.tar.gz p && rm -r p && tar xzf s.tar.gz && cat p/a.txt",
         "sortie": "parchemin"},
        {"prepare": "mkdir p; echo x > p/a.txt; tar czf s.tar.gz p", "cmd": "tar tzf s.tar.gz", "sortie": "p/\np/a.txt"}],
        ["GNU tar : https://www.gnu.org/software/tar/manual/tar.html",
         "ANSSI et Cybermalveillance.gouv.fr : la règle 3-2-1 des sauvegardes (rançongiciels)"]),
    fiche("chiffrement", r"(^openssl\s+enc\b|^gpg\b)", [
        {"prepare": "echo 'le secret de la créature' > l",
         "cmd": "openssl enc -aes-256-cbc -pbkdf2 -in l -out l.enc -pass pass:exemple && head -c 8 l.enc",
         "sortie": "Salted__", "outil": "openssl"},
        {"prepare": "echo secret > l; openssl enc -aes-256-cbc -pbkdf2 -S 0011223344556677 -in l -out l.enc -pass pass:exemple",
         "cmd": "openssl enc -d -aes-256-cbc -pbkdf2 -S 0011223344556677 -in l.enc -pass pass:mauvaise", "code": "non0",
         "motif": r"bad decrypt", "outil": "openssl"},
        {"prepare": "echo secret > l; openssl enc -aes-256-cbc -pbkdf2 -in l -out l.enc -pass pass:exemple",
         "cmd": "openssl enc -d -aes-256-cbc -pbkdf2 -in l.enc -pass pass:exemple", "sortie": "secret", "outil": "openssl"}],
        ["FIPS 197 (AES)", "RFC 8018 (PBKDF2)", "man 1 openssl-enc : https://docs.openssl.org/3.0/man1/openssl-enc/",
         "GnuPG, gpg --symmetric : https://www.gnupg.org/documentation/manuals/gnupg/"]),
    fiche("hameconnage", r"(^diff\b|lettre_du_facteur|^(tg\s+)?citadelle\s+facteur\b|/courrier\b)", [
        {"prepare": "printf 'Bonjour\\nLe capitaine\\n' > vraie; printf 'Bonjour\\nLe capitaine URGENT\\n' > fausse",
         "cmd": "diff vraie fausse", "code": "non0", "sortie": "2c2\n< Le capitaine\n---\n> Le capitaine URGENT"},
        {"prepare": "printf 'clique ici : http://port-du-terminaworld.example/urgent\\n' > lettre",
         "cmd": "grep -o 'http[^ ]*' lettre", "sortie": "http://port-du-terminaworld.example/urgent"}],
        ["RFC 2606 (les noms .example sont réservés : ils n'appartiennent à personne)",
         "Cybermalveillance.gouv.fr, « Hameçonnage » : https://www.cybermalveillance.gouv.fr/",
         "man 1 diff (GNU diffutils)"]),
    fiche("phrase_de_passe", r"(^shuf\b|mots\.txt|^(tg\s+)?citadelle\s+(force|phrase)\b)", [
        {"prepare": "seq 128 > mots.txt", "cmd": "wc -l mots.txt", "sortie": "128 mots.txt"},
        {"prepare": "seq 128 > mots.txt", "cmd": "shuf -n 4 mots.txt | sort -u | wc -l", "sortie": "4"},
        {"cmd": "echo $((128**4))", "sortie": "268435456"}],
        ["NIST SP 800-63B (2017, rév. 2024) : longueur plutôt que complexité, listes de mots de passe connus",
         "EFF, Diceware word lists : https://www.eff.org/dice", "ANSSI, Recommandations relatives à l'authentification (2021)",
         "man 1 shuf (GNU coreutils)"]),
    fiche("boites", r"(boites/|^(tg\s+)?citadelle\s+(bo[iî]tes?|drapeau|inspecteur|rotation)\b)", [
        {"prepare": "mkdir -p b/.cave; echo 'TG{exemple}' > b/.cave/note.txt", "cmd": "grep -r 'TG{' b",
         "sortie": "b/.cave/note.txt:TG{exemple}"},
        {"prepare": "mkdir b; echo x > b/ronde.sh; chmod 757 b/ronde.sh; echo y > b/ok.txt; chmod 644 b/ok.txt",
         "cmd": "find b -perm -o+w", "sortie": "b/ronde.sh"},
        {"prepare": "mkdir b; echo x > b/s; chmod 757 b/s", "cmd": "chmod o-rwx b/s; stat -c %a b/s", "sortie": "750"}],
        ["Code pénal (France), article 323-1 : accès frauduleux à un système de traitement automatisé de données",
         "ANSSI, Guide d'hygiène informatique (2017) : principe du moindre privilège",
         "Root-Me et Hack The Box : plateformes d'entraînement légales (on n'attaque que ce qu'on a le droit d'attaquer)"]),
    fiche("pare_feu", r"^(tg\s+)?citadelle\s+(vague|tableau)\b", [
        {"prepare": "python3 -m http.server 8774 --bind 127.0.0.1 >/dev/null 2>&1 & echo $! > pid; "
                    "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do curl -s -o /dev/null http://127.0.0.1:8774/ && break; sleep 0.3; done",
         "cmd": "ss -tln | grep -c '127.0.0.1:8774'; kill $(cat pid)", "sortie": "1", "outil": "ss"}],
        ["man 8 ss", "man 8 nft (nftables, le pare-feu de Linux)",
         "ANSSI, Recommandations pour la définition d'une politique de filtrage réseau d'un pare-feu (2013)"]),
])

CITADELLE = {"requis": ["n4", "n6"], "paliers": [f"cit{i}" for i in range(17)],
             "attirance": {"cmds": ["chmod", "sha256sum", "umask", "openssl", "tar"], "activites": ["ctf"],
                           "familles": ["Démons"]},
             "ponts": {"curl": ["port"], "find_newer": ["temps"], "ps_kill": ["controle"], "sort_uniq": ["donnees"],
                       "tar": ["controle"]},
             "exploits": [{"id": "citadelle.boite", "nom": "recomp.citadelle.boite", "recompense": "variante"},
                          {"id": "citadelle.vague", "nom": "recomp.citadelle.vague", "recompense": "variante"}],
             "maths": ["puissances"],
             "variantes_reservees": ["ricanombre:arcane", "ombrachne:crypte", "flamouche:marais", "sulfurette:toxique"]}

ETAPES = {"cit4.1": {"maths": ["comptage"]}, "cit12.0": {"maths": ["puissances"]}, "cit12.2": {"maths": ["puissances"]}}

REJEU = {
    "cit1.0": {"motif": r"^-rw-r--r-- .*coffre\.txt$", "pourquoi": "hist.cit1.0.bravo : rw- r-- r-- (tout le monde peut lire)"},
    "cit3.0": {"motif": r"^0[0-7]{3}$", "pourquoi": "hist.cit3.0.bravo : quatre chiffres (souvent 0022)"},
    "cit4.1": {"sortie": "52", "pourquoi": "hist.cit4.1.bravo : 52 échecs"},
    "cit4.2": {"motif": r"^\s+50 203\.0\.113\.66$", "pourquoi": "hist.cit4.2.bravo : 50 échecs pour 203.0.113.66"},
    "cit5.0": {"lignes": 4, "motif": r"virus_fictif_1\.glitch", "pourquoi": "hist.cit5.0.bravo : quatre glitchs"},
    "cit5.1": {"motif": r"\./remparts/nord/virus_fictif_5\.glitch", "pourquoi": "hist.cit5.1.bravo : le ver s'est copié"},
    "cit6.1": {"motif": r"rm -f bac_a_sable/tresor_\*\.txt", "pourquoi": "hist.cit6.1.bravo : la ligne piégée"},
    "cit8.1": {"code": "non0", "motif": r"tresor/couronne\.txt: FAILED", "pourquoi": "hist.cit8.1.bravo : la couronne"},
    "cit9.3": {"motif": r"parchemins/charte\.txt: OK", "code": 0, "pourquoi": "hist.cit9.3.bravo : tout est OK"},
    "cit10.3": {"motif": r"Pixel", "outil": "openssl", "pourquoi": "hist.cit10.3.bravo : la lettre revient en clair"},
    "cit11.0": {"code": "non0", "motif": r"^> .*port-du-terminaworld\.example", "pourquoi": "hist.cit11.0.bravo : le faux lien"},
    "cit12.0": {"sortie": "128 mots.txt", "pourquoi": "hist.cit12.0.bravo : 128 mots"},
    "cit12.1": {"lignes": 4, "pourquoi": "hist.cit12.1.bravo : 4 mots au hasard"},
    "cit13.2": {"lignes": 2, "motif": r"TG\{enumeration-entree-[0-9a-f]{8}\}", "pourquoi": "hist.cit13.2.bravo : deux drapeaux"},
    "cit14.1": {"sortie": "boites/droits/ronde.sh", "pourquoi": "hist.cit14.1.bravo : ronde.sh, modifiable par tous"},
}


def main():
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    for m in P["mondes"]:
        if m["id"] == "citadelle":
            m.update(CITADELLE)
    P["etapes"].update(ETAPES)
    P["rejeu"].update(REJEU)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Citadelle, {len(REJEU)} étapes rejouées")


if __name__ == "__main__":
    main()
