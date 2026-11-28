"""La Citadelle (phase 5, docs/programme.md § 2.11 et § 7.5), sur PC.

    python3 pc/outils/test_citadelle.py          (crée son propre HOME temporaire)

  1. la spécification pure : vecteurs communs à jour (donnees/citadelle/vecteurs.json, mêmes résultats en Kotlin) ;
     chmod (octal et lettres) identique au vrai chmod, umask, journal, drapeaux, force des phrases de passe ;
  2. l'arbre du Carrefour : fermée tant que le nid, la bibliothèque et la cave ne sont pas finis, puis ouverte et
     annoncée une fois ; elle est meublée (règle d'or, journaux, cadeau…) ;
  3. la traversée cit0 → cit16 comme un enfant (vraies commandes dans bash, commandes du jeu `citadelle …`) : le ver
     qui se copie, le cheval de Troie désarmé, les processus fictifs arrêtés, le Verrouilleur déjoué, le coffre
     openssl, le faux facteur, les trois boîtes (enquête puis rempart, l'inspecteur), la grande vague ; les deux
     exploits, le bouclier miniature, le titre ; les variantes réservées libérées ;
  4. les indices (sudo, « ? » recopié, mauvais drapeau, rempart pas réparé) et le cheval lancé par erreur ;
  5. la vue déployée : les cadenas d'un chmod / umask qui s'allument ;
  6. sécurité : rien n'est écrit hors du terrain (sauf ~/.terminagotchi), aucun processus fictif ne survit, aucune
     adresse visée hors de la boucle locale, jamais de sudo, aucun mot de passe autre que les exemples ; 14 langues.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_cit_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, citadelle as C, core, deploie, histoire, langue, port, recompenses  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0
terminal = [str(HOME)]
DOUBLURES = Path(tempfile.mkdtemp(prefix="tg_doublures_"))
if not shutil.which("ss"):
    (DOUBLURES / "ss").write_text("#!/bin/sh\necho 'State Recv-Q Send-Q Local Address:Port Peer Address:Port'\n"
                                  "echo 'LISTEN 0 5 127.0.0.1:8042 0.0.0.0:*'\n")
    (DOUBLURES / "ss").chmod(0o755)
(DOUBLURES / "citadelle").write_text(f"#!/bin/sh\nexec {sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                     "from tg import citadelle; citadelle.commande(sys.argv[1:])\" \"$@\"\n")
(DOUBLURES / "citadelle").chmod(0o755)
os.environ["PATH"] = f"{DOUBLURES}:{os.environ.get('PATH', '/usr/bin:/bin')}"
ENV = dict(os.environ, LC_ALL="C.UTF-8")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       errors="replace", timeout=60, env=ENV)
    lignes = r.stdout.rstrip("\n").split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
        lignes = lignes[:-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    st = app.etape(spontane=False, defis=False, cwd=terminal[0], statut=r.returncode)
    return st, "\n".join(lignes) + r.stderr


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if Path(racine) == T or T in Path(racine).parents:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


print("1. La spécification pure")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_citadelle.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "vecteurs communs à jour (donnees/citadelle/vecteurs.json)" + (" " + r.stdout[-200:] if r.returncode else ""))
d = tempfile.mkdtemp()
justes = 0
for spec in ("600", "755", "u+x", "go-r", "o-rwx", "a=r", "u+x,g-w", "+x", "-x", "g=rw", "0644", "a+w", "o-w"):
    for depart in (0o644, 0o755, 0o600, 0o777):
        f = Path(d) / "f"
        if f.exists():
            f.unlink()
        f.write_text("x")
        os.chmod(f, depart)
        subprocess.run(["bash", "-c", f"umask 022; chmod {spec} f"], cwd=d)
        justes += (f.stat().st_mode & 0o777) == C.chmod_mode(spec, depart, 0o022)
verifier(justes == 52, f"chmod_mode = le vrai chmod (13 réglages × 4 départs, umask 022) : {justes}/52")
verifier(C.umask_mode(0o077) == 0o600 and C.umask_mode(0o022) == 0o644 and C.umask_mode(0o022, True) == 0o755,
         "umask : 077 → 600, 022 → 644 (dossier 755)")
verifier(C.echecs() == {"203.0.113.66": 50, "198.51.100.23": 2} and len(C.journal()) == 90,
         "le journal : 90 lignes, 52 échecs, dont 50 pour l'intrus 203.0.113.66 (adresse de documentation)")
verifier(re.fullmatch(r"TG\{droits-donjon-[0-9a-f]{8}\}", C.drapeau("1:0", "droits", "donjon")) is not None and
         C.drapeau("1:0", "droits", "donjon") != C.drapeau("2:0", "droits", "donjon"), "les drapeaux changent à chaque partie")
verifier(C.duree_essais(C.bits({"bits": 20})) < 1 and C.duree_essais(C.bits({"mots": 6, "liste": 7776})) > 1e6 * 365 * 86400,
         "force : court et connu = un instant ; 6 mots parmi 7776 = des millions d'années")
verifier(len(C.bons_indices("1:0")) == 3, "le faux facteur : 3 vrais indices sur 6")

print("2. L'arbre du Carrefour")
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
AVANT = fichiers_hors_terrain()
st = core.load()
verifier(not histoire.ouvert(st, "citadelle") and "cave" in histoire.choisir(st, "citadelle", dit=False).lower() or
         "cadenas" in histoire.choisir(st, "citadelle", dit=False).lower(), "fermée au début (il manque la cave…)")


def ouvrir(s):
    h = histoire.h_(s)
    for c in ("reveil", "nid", "bibliotheque", "cave"):
        for lid in histoire.PAR_CHAP[c]["lecons"]:
            if lid not in h["faits"]:
                h["faits"].append(lid)
    h["ailes"] = ["reveil", "nid", "bibliotheque"]
    h["chap"] = "cave"
    h.setdefault("mondes_annonces", []).append("port")     # le Port déjà annoncé (il s'ouvre avant)
    s["xp"] = 10 * 30 ** 2
    s["step"] = 0


core.modifier(ouvrir)
T.mkdir(exist_ok=True)
st, _ = tape("ls")
verifier(histoire.fini(st, "cave") and histoire.ouvert(st, "citadelle"), "nid, bibliothèque et cave finis : la Citadelle s'ouvre")
verifier("citadelle" in st["histoire"].get("mondes_annonces", []), "annoncée une fois")
verifier((T / "citadelle" / "regle_d_or.txt").is_file() and (T / "citadelle" / "journaux" / "acces.log").is_file(),
         "la Citadelle est meublée (règle d'or, journal du gardien…)")

print("3. La traversée de la Citadelle, comme un enfant")
for _ in range(20):
    if not port.phare_allume():
        break
    port.eteindre_phare()
    time.sleep(0.2)
st, _ = tape("cd ~/terrain_terminagotchi/citadelle")
verifier(lecon(st) == ("cit0", 1), f"entrer dans la Citadelle choisit le monde : {lecon(st)}")
gr = C._graine(st)
dr = {(b, g): C.drapeau(gr, b, g) for b in ("enumeration", "droits", "secrets") for g in ("entree", "donjon")}
sorties = {}


def joue(cmds):
    global st
    for c in cmds:
        if callable(c):
            c = c()
        st, s = tape(c)
        sorties[c] = s
        if os.environ.get("TG_DEBUG"):
            print(f"    · {c} → {lecon(st)} {s[:90]!r}")


def pids():
    return " ".join(str(p) for p, _n in C.fictifs_vivants())


PARCOURS = [
    "ls", "cat regle_d_or.txt",
    "ls -l coffre.txt", "chmod 600 coffre.txt", "chmod u+x ronde.sh",
    "id", "grep veilleurs groupes.txt", "citadelle chown sentinelle:veilleurs tour_de_guet.txt",
    "umask", "(umask 077; touch carnet_secret.txt)", "citadelle masque 077",
    "tail -n 5 journaux/acces.log", "grep -c ECHEC journaux/acces.log",
    'grep ECHEC journaux/acces.log | cut -d " " -f 4 | sort | uniq -c | sort -n', "echo 203.0.113.66 > intrus.txt",
    'find . -name "*.glitch"', "find . -newer repere.txt", 'find . -name "*.glitch" -delete',
    "cat cadeau.sh", "grep rm cadeau.sh", "chmod -x cadeau.sh",
    "ps aux | grep fictif", lambda: f"kill {pids()}", "citadelle tableau",
    "sha256sum tresor/carte.txt", "sha256sum -c empreintes_tresor.sha256", "echo couronne > altere.txt",
    "tar czf coffre_de_secours.tar.gz parchemins", "tar xzf coffre_de_secours.tar.gz", "rm -f parchemins/*.verrou",
    "sha256sum -c parchemins.sha256",
    "cat lettre.txt", C.CHIFFRE, C.DECHIFFRE.format(C.MAUVAISE), C.DECHIFFRE.format(C.PASSE),
    "diff vraie_lettre.txt lettre_du_facteur.txt", "curl -s http://localhost:8042/courrier", "citadelle facteur",
    "citadelle facteur 1 2 3" if C.bons_indices(gr) != [1, 2, 3] else "citadelle facteur 4 5 6",
    lambda: "citadelle facteur " + " ".join(map(str, C.bons_indices(gr))),
    "wc -l mots.txt", "shuf -n 4 mots.txt", "citadelle force",
    "citadelle boites", "ls -la boites/enumeration", 'grep -r "TG{" boites/enumeration',
    "citadelle drapeau TG{faux}", "citadelle drapeau " + dr[("enumeration", "entree")],
    "citadelle drapeau " + dr[("enumeration", "donjon")], "citadelle inspecteur enumeration",
    "chmod o-rwx boites/enumeration/.cave_oubliee", "citadelle inspecteur enumeration",
    "ls -l boites/droits", "find boites/droits -perm -o+w", 'grep -r "TG{" boites/droits',
    "citadelle drapeau " + dr[("droits", "entree")], "citadelle drapeau " + dr[("droits", "donjon")],
    "chmod o-rwx boites/droits/*", "citadelle inspecteur droits",
    "ls -la boites/secrets", "grep -r mot_de_passe boites/secrets",
    "citadelle drapeau " + dr[("secrets", "entree")], "citadelle drapeau " + dr[("secrets", "donjon")],
    "rm boites/secrets/.historique_fictif", "citadelle rotation secrets", "citadelle inspecteur secrets",
    "ss -tln", "citadelle vague", "citadelle tableau",
    'find . -name "*.glitch" -delete', lambda: f"kill {pids()}", "chmod 600 secrets_du_pont_levis.txt", "citadelle tableau",
]
etapes_vues = []
for c in PARCOURS:
    avant = lecon(st)
    joue([c])
    etapes_vues.append((avant, c, lecon(st)))
    if histoire.fini(st, "citadelle"):
        break
if not histoire.fini(st, "citadelle"):
    for a, c, b in etapes_vues[-6:]:
        print("     ", a, c, "→", b)
verifier(histoire.fini(st, "citadelle"), f"la Citadelle est défendue jusqu'au bout (cit0 → cit16) {lecon(st)}")
verifier("rw-r--r--" in sorties.get("ls -l coffre.txt", ""), "ls -l : le coffre était rw-r--r-- (ouvert)")
verifier("50 203.0.113.66" in sorties.get('grep ECHEC journaux/acces.log | cut -d " " -f 4 | sort | uniq -c | sort -n', ""),
         "le tuyau du registre trouve l'intrus (50 échecs)")
verifier("virus_fictif_5" in sorties.get("find . -newer repere.txt", ""), "find -newer voit le ver qui s'est copié")
verifier("couronne.txt: FAILED" in sorties.get("sha256sum -c empreintes_tresor.sha256", ""), "sha256sum -c : la couronne a été touchée")
verifier("bad decrypt" in sorties.get(C.DECHIFFRE.format(C.MAUVAISE), "") and "Pixel" in sorties.get(C.DECHIFFRE.format(C.PASSE), ""),
         "openssl : la mauvaise clé est refusée, la bonne rend la lettre")
verifier((T / "citadelle" / "lettre.enc").read_bytes()[:8] == b"Salted__", "la lettre chiffrée commence par Salted__")
verifier("JAMAIS" in sorties.get("curl -s http://localhost:8042/courrier", ""), "le pont curl : le phare du Port répond /courrier")
verifier(oct((T / "citadelle" / "carnet_secret.txt").stat().st_mode & 0o777) == "0o600", "umask 077 : le carnet secret est né en 600")
r_ = recompenses.r_(st)
verifier({"citadelle.boite", "citadelle.boite.droits", "citadelle.boite.secrets", "citadelle.vague"} <= set(r_["exploits"]),
         "les exploits de la Citadelle : les trois boîtes maîtrisées et la grande vague")
verifier(recompenses.boites_maitrisees(st) == ["enumeration", "droits", "secrets"]
         and recompenses.gardien_de(st, {"id": "cranard"}) == "secrets", "les gardiens des trois boîtes sont rencontrables (glitch)")
verifier("bouclier_miniature" in st["quetes"]["objets"] and st["quetes"]["titre"] == "gardien_de_la_citadelle",
         "récompenses : le bouclier miniature et le titre de Gardien de la Citadelle")
verifier(not recompenses.reservee({}, {"id": "ricanombre"}, "arcane") and not recompenses.reservee({}, {"id": "sulfurette"}, "toxique"),
         "les 4 variantes Démons sont au tirage normal (la récompense de la Citadelle : le glitch des gardiens)")
verifier(st["citadelle"]["proprietaires"].get("tour_de_guet.txt") == "sentinelle:veilleurs", "chown simulé : seul le registre change")
verifier(not C.fictifs_vivants(), "plus aucun processus fictif en vie")

print("4. Les indices et la surveillance")
pas = {s_["cmd"]: s_ for l_ in C.LECONS.values() for s_ in l_["steps"]}
verifier(C.indice(pas["kill ?"], [("sudo kill 1", None)]) == langue.t("cit.indice.sudo"), "sudo tenté : jamais dans le jeu (indice)")
verifier(C.indice(pas["echo ? > intrus.txt"], [("echo ? > intrus.txt", None)]) == langue.t("cit.indice.trou"), "« ? » recopié : un trou à remplir")
C.noter("drapeau", "TG{x} (faux)")
verifier(C.indice(pas["citadelle drapeau ?"], [("citadelle drapeau TG{x}", None)]) == langue.t("cit.indice.drapeau"), "mauvais drapeau : l'indice")
C.noter("inspecteur", "droits (refus)")
verifier(C.indice(pas["citadelle inspecteur droits"], [("citadelle inspecteur droits", None)]) == langue.t("cit.indice.rempart"),
         "rempart pas réparé : l'indice")
(T / "citadelle" / "bac_a_sable" / "tresor_1.txt").unlink()
C.surveiller(core.load(), ["./cadeau.sh"])
verifier((T / "citadelle" / "bac_a_sable" / "tresor_1.txt").is_file(), "le cheval lancé par erreur : la créature prévient, les trésors reviennent")

print("5. La vue déployée : les cadenas")
x = deploie.droits("chmod 600 coffre.txt")[0]
verifier(x["avant"] == "rw-r--r--" and x["apres"] == "rw-------" and x["octal"] == "600" and x["suppose"], "chmod 600 : rw-r--r-- → rw-------")
x = deploie.droits("chmod u+x ronde.sh", str(T / "citadelle"))[0]
verifier(not x["suppose"] and x["apres"][2] == "x", "chmod u+x sur un vrai fichier : son mode réel lu, la clé x s'allume")
verifier(deploie.droits("(umask 077; touch f)")[0]["apres"] == "rw-------" and deploie.droits("ls -l") == [], "umask 077 ; ls -l : rien")
txt = ANSI.sub("", "\n".join(deploie.ecran("chmod 600 coffre.txt", deploie.blocs("chmod 600 coffre.txt"), 1, None, 0.8, 100)))
verifier("rw-------" in txt and "[r]" not in txt and "[w]" not in txt and "🙂" in txt and "[r" not in txt.split("🌍")[0][-30:] or "[·]" in txt,
         "la vue déployée dessine les cadenas (moi, mon club, les autres), ceux qui changent entre crochets")
out = io.StringIO()
C.commande(["cadenas", str(T / "citadelle" / "coffre.txt")], out)
verifier("rw-------" in out.getvalue(), "tg citadelle cadenas")
from tg import compagnon  # noqa: E402
verifier(any("citadelle='tg citadelle'" in b or "function citadelle" in b for b in compagnon._blocs().values()),
         "tg installer pose l'alias citadelle='tg citadelle'")

print("6. Sécurité et langues")
port.eteindre_phare()
C.arreter_fictifs()
nouveaux = sorted(x for x in fichiers_hors_terrain() - AVANT if not x.endswith(".bash_history") and "/.terminagotchi/" not in x
                  and "/.cache/powershell/" not in x)
verifier(not nouveaux, f"rien d'écrit hors du terrain et de ~/.terminagotchi ({nouveaux[:3]})")
cmds = " ".join(s.get("cmd") or "" for lid in C.LECONS for s in C.LECONS[lid]["steps"])
verifier(set(re.findall(r"https?://([^/:\s]+)", cmds)) <= {"localhost", "127.0.0.1"}, "les leçons ne visent que la boucle locale")
verifier("sudo" not in cmds, "aucune leçon ne demande sudo")
verifier(set(re.findall(r"pass:(\S+)", cmds)) <= {C.PASSE, C.MAUVAISE} and "exemple" in C.PASSE,
         "seulement des clés d'exemple (jamais un vrai mot de passe)")
verifier(all(a.startswith(("198.51.100.", "203.0.113.")) for a in C.echecs()), "le journal n'a que des adresses de documentation")
manque = {}
for code in langue.LANGUES:
    dct = langue._charger(code)
    m = [k for lid in C.LECONS for s in C.LECONS[lid]["steps"] for k in (s["dit"], s["bravo"]) if isinstance(k, str) and k not in dct]
    m += [k for k in ("hist.citadelle.titre", "hist.citadelle.debut", "hist.citadelle.fin", "cit.ouvert.dit", "dep.droits") if k not in dct]
    if m:
        manque[code] = m[:3]
verifier(not manque, f"les textes de la Citadelle existent dans les 14 langues {manque}")

shutil.rmtree(DOUBLURES, ignore_errors=True)
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
