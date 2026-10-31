"""Les fiches notions de la Crypte des Codes (charte de rigueur, docs/programme.md § 7.1) et sa place dans
donnees/programme.json : le monde (prérequis = niveaux 0 à 4 du tronc commun, paliers, ponts, attirance, exploits,
variantes réservées aux types Ombre et Glace), les maths des étapes (Ponts des Nombres) et les étapes rejouées dans bash.

    python3 donnees/crypte/outils/fiches_crypte.py      écrit donnees/programme.json et ses deux copies

Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, dans un terrain jetable : des
fichiers fabriqués sur place, openssl en local avec une clé d'EXEMPLE, gpg avec un --homedir jetable (jamais le
trousseau de l'utilisateur ; son gpg-agent est arrêté à la fin). Rien ne sort de la machine.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"cr.f.{nid}.enfant", "grands": f"cr.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"cr.f.{nid}.limite", "idees_fausses": [f"cr.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


GPG_CLE = ("mkdir -m 700 t && gpg --homedir t --batch --passphrase '' --quick-gen-key sphinx@crypte.example "
           ">/dev/null 2>&1")
GPG_FIN = "; gpgconf --homedir t --kill gpg-agent"

FICHES = dict([
    fiche("encodage", r"(base64|xxd|crypte\s+demasque)", [
        {"cmd": "echo bonjour | base64", "sortie": "Ym9uam91cgo="},
        {"cmd": "echo Ym9uam91cgo= | base64 -d", "sortie": "bonjour"},
        {"cmd": "printf 'Hi' | od -An -tx1", "sortie": " 48 69"},
        {"cmd": "echo 626f6e6a6f7572 | xxd -r -p", "sortie": "bonjour", "outil": "xxd"}],
        ["RFC 4648 (base16, base32, base64) : https://www.rfc-editor.org/rfc/rfc4648",
         "man 1 base64 (GNU coreutils), man 1 xxd, man 1 od",
         "ANSSI, Guide de sélection d'algorithmes cryptographiques (2021) : encodage ≠ chiffrement"]),
    fiche("substitution", r"(^tr\b|\|\s*tr\b|mystere|crypte\s+roue)", [
        {"cmd": "echo bonjour | tr 'a-z' 'd-za-c'", "sortie": "erqmrxu"},
        {"cmd": "echo erqmrxu | tr 'd-za-c' 'a-z'", "sortie": "bonjour"},
        {"cmd": "echo uryyb | tr 'a-z' 'n-za-m'", "sortie": "hello"},
        {"cmd": "echo eeeab | grep -o '[a-z]' | sort | uniq -c | sort -rn | head -n 1", "sortie": "      3 e"}],
        ["POSIX.1-2024, tr : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tr.html",
         "Simon Singh, Histoire des codes secrets (1999) : César, al-Kindi (analyse de fréquences), Vigenère, Kasiski",
         "D. Kahn, The Codebreakers (1967)"]),
    fiche("hachage", r"(\|\s*sha256sum|crypte\s+avalanche|sceaux)", [
        {"cmd": "echo -n a | sha256sum", "sortie": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb  -"},
        {"cmd": "echo -n b | sha256sum", "sortie": "3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d  -"},
        {"prepare": "printf 'sort\\n' > s; sha256sum s > sceaux; printf 'sort!\\n' > s", "cmd": "sha256sum -c sceaux",
         "code": "non0", "motif": r"^s: FAILED$"}],
        ["FIPS 180-4 (SHA-256) : https://csrc.nist.gov/pubs/fips/180-4/upd1/final",
         "man 1 sha256sum (GNU coreutils)", "M. Stevens et al., SHAttered (2017) : la première collision SHA-1"]),
    fiche("mots_de_passe", r"(base_fictive|dictionnaire\.sh|openssl\s+passwd)", [
        {"cmd": "openssl passwd -6 -salt abcdefgh licorne",
         "sortie": "$6$abcdefgh$LBfJchvsjtkLn7O11D7NsWSuRtEB44nhzqe/jwDYwsdvaAAIzZl6ZZfTbPRWrK.ZADurJUQYLPM4n5EnWbpwa/",
         "outil": "openssl"},
        {"cmd": "printf %s soleil | sha256sum | cut -c1-64",
         "sortie": "e93e24c1b877a15df5e4a8cbb20f351b891b750779cf5e8fb99119a7142d89cf"},
        {"cmd": "echo $((128**4))", "sortie": "268435456"}],
        ["NIST SP 800-63B (rév. 2024) : longueur plutôt que complexité, listes de mots de passe compromis",
         "U. Drepper, Unix crypt using SHA-256 and SHA-512 (2007) : https://www.akkadia.org/drepper/SHA-crypt.txt",
         "RFC 9106 (Argon2)", "man 1 openssl-passwd : https://docs.openssl.org/3.0/man1/openssl-passwd/"]),
    fiche("symetrique", r"(parchemin\.(txt|enc)|crypte\s+donne\s+parchemin)", [
        {"prepare": "echo 'pour ma creature' > p",
         "cmd": "openssl enc -aes-256-cbc -pbkdf2 -in p -out p.enc -pass pass:sphinx-de-givre-exemple && head -c 8 p.enc",
         "sortie": "Salted__", "outil": "openssl"},
        {"prepare": "echo 'pour ma creature' > p; openssl enc -aes-256-cbc -pbkdf2 -in p -out p.enc -pass pass:sphinx-de-givre-exemple",
         "cmd": "openssl enc -d -aes-256-cbc -pbkdf2 -in p.enc -pass pass:sphinx-de-givre-exemple", "sortie": "pour ma creature",
         "outil": "openssl"}],
        ["FIPS 197 (AES)", "RFC 8018 (PBKDF2)", "man 1 openssl-enc : https://docs.openssl.org/3.0/man1/openssl-enc/"]),
    fiche("asymetrique", r"(crypte\s+peintures|\$\(\(\s*5|quick-gen-key|\s-e\s+-r\s|crypte\s+donne\s+secret|message\.txt)", [
        {"cmd": "echo $((5**6 % 23)) $((5**15 % 23)) $((19**6 % 23)) $((8**15 % 23))", "sortie": "8 19 2 2"},
        {"cmd": GPG_CLE + " && echo 'le sceau' > m && gpg --homedir t --batch --clearsign m 2>/dev/null && "
                "gpg --homedir t --verify m.asc 2>&1 | grep -c 'Good signature'" + GPG_FIN, "sortie": "1", "outil": "gpg"},
        {"cmd": GPG_CLE + " && echo 'pour elle' > s && gpg --homedir t --batch -e -r sphinx@crypte.example -o s.gpg s "
                "2>/dev/null && gpg --homedir t --batch -d s.gpg 2>/dev/null" + GPG_FIN, "sortie": "pour elle", "outil": "gpg"}],
        ["W. Diffie et M. Hellman, New Directions in Cryptography (1976)", "RFC 9580 (OpenPGP, 2024)",
         "GnuPG, manuel : https://www.gnupg.org/documentation/manuals/gnupg/",
         "RFC 8446 (TLS 1.3 : échange de clés et certificats, pont vers le Port)"]),
    fiche("hasard", r"(/dev/u?random|openssl\s+rand|crypte\s+de\b)", [
        {"cmd": "head -c 16 /dev/urandom | wc -c", "sortie": "16"},
        {"cmd": "openssl rand -hex 16 | tr -d '\\n' | wc -c", "sortie": "32", "outil": "openssl"},
        {"cmd": "x=6; echo $(( (5*x+3) % 8 ))", "sortie": "1"}],
        ["man 4 urandom, man 2 getrandom", "NIST SP 800-90A (générateurs déterministes)",
         "Debian DSA-1571-1 (2008) : des clés OpenSSL devinables"]),
    fiche("post_quantique", r"crypte\s+quiz", [
        {"cmd": "echo $((256 / 2))", "sortie": "128"}],
        ["NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA), août 2024",
         "P. Shor, Algorithms for quantum computation (1994) ; L. Grover (1996)",
         "ANSSI, Avis sur la migration vers la cryptographie post-quantique (2022, mis à jour 2023)"]),
    fiche("registre", r"(registre\.txt|crypte\s+registre)", [
        {"prepare": "printf 'Pixel a donne 3 glands\\n' > registre.txt", "cmd": "echo 'Lune donne 2 plumes' >> registre.txt; cat registre.txt",
         "sortie": "Pixel a donne 3 glands\nLune donne 2 plumes"}],
        ["S. Nakamoto, Bitcoin: A Peer-to-Peer Electronic Cash System (2008), § 1-2 (le registre)",
         "POSIX.1-2024, Shell Command Language, redirections (>>)"]),
    fiche("chaine_blocs", r"(chaine/|verifie_chaine|crypte\s+chaine|archives/)", [
        {"prepare": "printf 'bloc: 0\\n' > b0; printf 'precedent: %s\\n' \"$(sha256sum b0 | cut -c1-64)\" > b1",
         "cmd": "test \"$(sha256sum b0 | cut -c1-64)\" = \"$(cut -d' ' -f2 b1)\" && echo OK; echo triche >> b0; "
                "test \"$(sha256sum b0 | cut -c1-64)\" = \"$(cut -d' ' -f2 b1)\" || echo CASSE", "sortie": "OK\nCASSE"}],
        ["S. Haber et W. S. Stornetta, How to time-stamp a digital document (1991)",
         "S. Nakamoto (2008), § 3-4 (serveur d'horodatage, chaîne d'empreintes)", "Pro Git, chap. 10 (les objets de git)"]),
    fiche("consensus", r"(copies/|crypte\s+consensus)", [
        {"prepare": "for i in 1 2 3; do echo vrai > c$i; done; echo triche > c4",
         "cmd": "sha256sum c1 c2 c3 c4 | cut -c1-64 | sort | uniq -c | sort -rn | awk '{print $1}'", "sortie": "3\n1"}],
        ["L. Lamport, R. Shostak, M. Pease, The Byzantine Generals Problem (1982)",
         "S. Nakamoto (2008), § 5 et 11 (le réseau, la majorité honnête)"]),
    fiche("preuve_travail", r"(mineur\.sh|crypte\s+mine)", [
        {"cmd": "for n in $(seq 1 1000); do h=$(printf 'bloc5%s' $n | sha256sum); case $h in 00*) echo $n; break;; esac; done",
         "sortie": "139"}],
        ["A. Back, Hashcash (2002)", "S. Nakamoto (2008), § 4 (preuve de travail)",
         "Cambridge Centre for Alternative Finance, Bitcoin Electricity Consumption Index"]),
    fiche("signature", r"(echange|crypte\s+signe)", [
        {"cmd": GPG_CLE + " && echo 'Pixel donne 2 glands' > e && gpg --homedir t --batch --clearsign e 2>/dev/null && "
                "sed -i 's/2 glands/20 glands/' e.asc && gpg --homedir t --verify e.asc 2>&1 | grep -c 'BAD signature'" + GPG_FIN,
         "sortie": "1", "outil": "gpg"}],
        ["RFC 9580 (OpenPGP), signatures en texte clair", "S. Nakamoto (2008), § 2 (transactions : une chaîne de signatures)"]),
    fiche("applications", r"(crypte\s+(vitrine|recensement)|carnet_de_bord|grep\s+-h\s+donnees)", [
        {"prepare": "mkdir c; printf 'donnees: a\\n' > c/bloc_0.txt; printf 'donnees: b\\n' > c/bloc_1.txt",
         "cmd": "grep -h donnees c/bloc_*.txt", "sortie": "donnees: a\ndonnees: b"}],
        ["S. Nakamoto (2008)", "V. Buterin, Ethereum White Paper (2014) : contrats intelligents",
         "EIP-721 (jetons non fongibles) : https://eips.ethereum.org/EIPS/eip-721",
         "Décision du propriétaire (28 octobre 2026) : explication technique uniquement, aucun avis"]),
])

CRYPTE = {"requis": ["n4"], "paliers": [f"cr{i}" for i in range(15)],
          "attirance": {"cmds": ["base64", "tr", "sha256sum", "openssl", "gpg"], "familles": ["Morts-vivants"]},
          "ponts": {"sha256sum": ["citadelle"], "openssl": ["citadelle"], "https": ["port"], "git": ["temps"],
                    "boucles": ["forge"], "diff": ["citadelle"]},
          "exploits": [{"id": "crypte.chaine", "nom": "recomp.crypte.chaine", "recompense": "variante"},
                       {"id": "crypte.b6", "nom": "recomp.crypte.b6", "recompense": "legendaire"}],
          "maths": ["division", "modulo", "puissances", "puissance_modulo", "hexadecimal", "probabilites"],
          "variantes_reservees": ["heaumbre:crypte", "fractalis:cristal", "givrarde:aurore", "lichonarque:crypte"],
          "gardienne": "lichonarque:crypte"}

ETAPES = {"cr1.2": {"maths": ["hexadecimal"]}, "cr2.4": {"maths": ["modulo"]}, "cr4.2": {"maths": ["puissances"]},
          "cr6.1": {"maths": ["puissance_modulo"]}, "cr7.3": {"maths": ["modulo"]},
          "cr12.1": {"maths": ["puissances"]}, "cr12.2": {"maths": ["probabilites"]}}

REJEU = {
    "cr1.0": {"sortie": "Ym9uam91cgo=", "pourquoi": "hist.cr1.0.bravo : Ym9uam91cgo="},
    "cr1.1": {"motif": r"dragon-exemple", "pourquoi": "hist.cr1.1.bravo : n'importe qui peut le lire"},
    "cr2.0": {"sortie": "erqmrxu", "pourquoi": "hist.cr2.0.bravo : erqmrxu"},
    "cr2.2": {"motif": r"^rot treize se decode", "pourquoi": "hist.cr2.2.bravo : la même commande décode"},
    "cr3.0": {"sortie": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb  -", "pourquoi": "hist.cr3.0.bravo"},
    "cr3.3": {"code": "non0", "motif": r"grimoires/sort_2\.txt: FAILED", "pourquoi": "hist.cr3.3.bravo : sort_2 FAILED"},
    "cr4.2": {"motif": r"lune -> soleil", "contient": ["123456", "licorne"], "pourquoi": "hist.cr4.2.bravo : soleil, 123456, licorne"},
    "cr4.3": {"motif": r"^\$6\$[./0-9A-Za-z]{1,16}\$[./0-9A-Za-z]{86}$", "outil": "openssl", "pourquoi": "hist.cr4.3.bravo : $6$, le sel"},
    "cr5.2": {"sortie": "Salted__", "outil": "openssl", "pourquoi": "hist.cr5.2.bravo : Salted__"},
    "cr6.1": {"sortie": "8", "pourquoi": "hist.cr6.1.bravo : 8"},
    "cr6.6": {"motif": r"Good signature", "outil": "gpg", "pourquoi": "hist.cr6.6.bravo : Good signature"},
    "cr7.1": {"motif": r"^[0-9a-f]{32}$", "outil": "openssl", "pourquoi": "hist.cr7.1.bravo : 32 chiffres hexadécimaux"},
    "cr10.1": {"motif": r"^[0-9a-f]{64}  chaine/bloc_0\.txt$", "pourquoi": "hist.cr10.1.bravo : 64 signes"},
    "cr10.2": {"code": 0, "motif": r"maillon 3 -> 4 : OK", "pourquoi": "hist.cr10.2.bravo : tous les maillons OK"},
    "cr10.4": {"code": "non0", "motif": r"maillon 1 -> 2 : CASSÉ", "pourquoi": "hist.cr10.4.bravo : CASSÉ au maillon 1 → 2"},
    "cr11.1": {"motif": r"^\s+8 [0-9a-f]{64}$", "pourquoi": "hist.cr11.1.bravo : 8 pareilles, 1 différente"},
    "cr11.2": {"code": "non0", "motif": r"^> .*100", "pourquoi": "hist.cr11.2.bravo : la ligne trafiquée"},
    "cr12.1": {"motif": r"^nonce = 139$", "pourquoi": "hist.cr12.1.bravo : nonce = 139"},
    "cr12.2": {"motif": r"^nonce = 2615$", "pourquoi": "hist.cr12.2.bravo : 2615 essais"},
    "cr13.2": {"code": "non0", "motif": r"BAD signature", "outil": "gpg", "pourquoi": "hist.cr13.2.bravo : BAD signature"},
    "cr14.2": {"code": 0, "motif": r"maillon 0 -> 1 : OK", "pourquoi": "hist.cr14.2.bravo : le carnet de bord tient"},
}


def main():
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    for m in P["mondes"]:
        if m["id"] == "crypte":
            m.update(CRYPTE)
    for cle in ("etapes", "rejeu"):                   # les étapes de la Crypte : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("cr") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    P["rejeu"].update(REJEU)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches de la Crypte, {len(REJEU)} étapes rejouées")


if __name__ == "__main__":
    main()
