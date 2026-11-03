"""Tests de « Signaler un souci » (idée 76, pc/tg/signaler.py) et du petit nuage de synchro (idée 74, recense.py).

    python3 pc/outils/test_signaler.py            vérifie (code de sortie 1 en cas d'échec)
    python3 pc/outils/test_signaler.py --ecrire   réécrit d'abord les vecteurs communs avec Kotlin :
                                                  donnees/bug/vecteurs.json, donnees/synchro/vecteurs.json
                                                  (relus par tests/jvm/SignalerSynchro.kt)

1. Les vecteurs communs : nettoyer (dossier personnel, nom, pseudo, utilisateur), le rapport (titre, corps), l'adresse
   de la page GitHub (encodage), et l'état du nuage (rien / envoi / hors ligne + nombre en attente).
2. Le rapport du PC : la dernière panne d'erreurs.log (commande, erreur, trace sans dossiers, chemins Windows aussi),
   jamais le nom de la créature, le pseudo, le dossier personnel ; `tg bug` : la question des grands d'abord,
   mauvaise réponse → rien ; [o] ouvre la page (rien d'autre), [f] écrit le fichier, [n] n'envoie rien ; le jeu
   n'envoie jamais rien lui-même (aucun appel réseau).
3. Le nuage : une synchro qui ne joint pas le site → « hors ligne », le compte et l'écran de tg le disent ; une synchro
   réussie l'efface ; pas de compte → rien.
4. Les textes dans les 14 langues.
"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_bug_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["COLUMNS"] = "120"
os.environ.pop("HISTFILE", None)
ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))

from tg import apparence, core, langue, recense, signaler, sur  # noqa: E402

V_BUG = DEPOT / "donnees" / "bug" / "vecteurs.json"
V_SYNC = DEPOT / "donnees" / "synchro" / "vecteurs.json"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


langue.definir("fr")
ETIQ = {"faisais": "Ce que je faisais :", "version": "Version :", "appareil": "Appareil :", "langue": "Langue :",
        "ecran": "Écran :", "commande": "Dernière commande :", "erreur": "Erreur :", "sans": "un souci dans le jeu",
        "pied": "(Rapport préparé par Terminagotchi.)"}


def fabriquer():
    nettoyer = [
        {"nom": "dossier personnel Linux", "home": "/home/lou", "utilisateur": "lou", "caches": ["Pixel", "Loulou"],
         "texte": "FileNotFoundError: '/home/lou/terrain/Pixel.txt'"},
        {"nom": "Windows, barres dans les deux sens", "home": "C:\\Users\\Marie", "utilisateur": "Marie", "caches": [],
         "texte": "C:\\Users\\Marie\\jeu et C:/Users/Marie/jeu, Marie"},
        {"nom": "mots trop courts gardés", "home": "~", "utilisateur": "al", "caches": ["Bo", ""],
         "texte": "Bo et al vont bien"},
        {"nom": "pseudo et nom dans un message", "home": "/data/user/0/fr.terminagotchi/files", "utilisateur": "",
         "caches": ["Noisette", "Zorglub"], "texte": "Noisette (Zorglub) : /data/user/0/fr.terminagotchi/files/terrain/x"},
        {"nom": "accents et emoji", "home": "/home/élodie", "utilisateur": "élodie", "caches": ["Étoile✨"],
         "texte": "/home/élodie/a — Étoile✨ dit bonjour à élodie"},
    ]
    for c in nettoyer:
        c["attendu"] = signaler.nettoyer(c["texte"], c["home"], c["utilisateur"], c["caches"])
    rapports = [
        {"nom": "PC, avec une panne", "champs": {"version": "0.4 · PC", "appareil": "Linux · Python 3.12", "langue": "fr",
                                                "ecran": "tg (100 × 30)", "commande": "tg monde",
                                                "erreur": "KeyError: 'biome' (monde_dessin.py:212)",
                                                "trace": ["app.py:12 _main", "monde_dessin.py:212 dessiner", "KeyError: 'biome'"]}},
        {"nom": "téléphone, sans panne notée", "champs": {"version": "0.1.97 · Android", "appareil": "Android 14 · téléphone",
                                                         "langue": "fr", "ecran": "terminal, onglet 2 sur 2", "commande": "",
                                                         "erreur": "", "trace": []}},
        {"nom": "trace longue et lignes trop longues (coupées)", "champs": {
            "version": "0.4 · PC", "appareil": "Windows 11 · terminal du jeu", "langue": "ja", "ecran": "tg (80 × 24)",
            "commande": "tg sauvegarde exporter ~/clé", "erreur": "ValueError: " + "x" * 120 + " (sauvegarde.py:9)",
            "trace": [f"f{i}.py:{i} g{i}" for i in range(20)] + ["ValueError: " + "é" * 200]}},
        {"nom": "caractères spéciaux dans l'adresse", "champs": {"version": "1 & 2 = 3?", "appareil": "a+b/c#d%e",
                                                                "langue": "ar", "ecran": "中文 · 😵", "commande": "echo \"*\" 'x'",
                                                                "erreur": "", "trace": ["~ ok"]}},
    ]
    for r in rapports:
        r["etiquettes"] = ETIQ
        r["titre"], r["corps"] = signaler.rapport(r["champs"], ETIQ)
        r["adresse"] = signaler.adresse(r["titre"], r["corps"])
    V_BUG.write_text(json.dumps({"nettoyer": nettoyer, "rapport": rapports}, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    nuage = [
        {"nom": "pas de compte", "compte": {}, "total": 9, "envoi": False},
        {"nom": "pas de compte, même pendant un envoi", "compte": {"pseudo": "Lou"}, "total": 9, "envoi": True},
        {"nom": "à jour : rien à l'écran", "compte": {"cle": "k", "hors": False, "base": {"total": 9}}, "total": 9, "envoi": False},
        {"nom": "envoi en cours", "compte": {"cle": "k", "hors": True, "base": {"total": 2}}, "total": 9, "envoi": True},
        {"nom": "hors ligne, 3 en attente", "compte": {"cle": "k", "hors": True, "base": {"total": 6}}, "total": 9, "envoi": False},
        {"nom": "hors ligne, rien en attente", "compte": {"cle": "k", "hors": True, "base": {"total": 9}}, "total": 9, "envoi": False},
        {"nom": "hors ligne sans base (premier envoi raté)", "compte": {"cle": "k", "hors": True}, "total": 4, "envoi": False},
        {"nom": "hors ligne, base plus grande (autre appareil)", "compte": {"cle": "k", "hors": True, "base": {"total": 50}},
         "total": 9, "envoi": False},
    ]
    for c in nuage:
        e = recense.etat_nuage(c["compte"], c["total"], c["envoi"])
        c["attendu"] = list(e) if e else None
    V_SYNC.write_text(json.dumps({"nuage": nuage}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if "--ecrire" in sys.argv:
    fabriquer()

# ---------------------------------------------------------------- 1. vecteurs communs
print("1. Les vecteurs communs (donnees/bug/vecteurs.json, donnees/synchro/vecteurs.json)")
vb = json.loads(V_BUG.read_text(encoding="utf-8"))
for c in vb["nettoyer"]:
    verifier(signaler.nettoyer(c["texte"], c["home"], c["utilisateur"], c["caches"]) == c["attendu"],
             f"nettoyer · {c['nom']} → {c['attendu'][:60]}")
for r in vb["rapport"]:
    ti, co = signaler.rapport(r["champs"], r["etiquettes"])
    verifier((ti, co, signaler.adresse(ti, co)) == (r["titre"], r["corps"], r["adresse"]), f"rapport · {r['nom']}")
vs = json.loads(V_SYNC.read_text(encoding="utf-8"))
for c in vs["nuage"]:
    e = recense.etat_nuage(c["compte"], c["total"], c["envoi"])
    verifier((list(e) if e else None) == c["attendu"], f"nuage · {c['nom']} → {c['attendu']}")
# quelques valeurs écrites à la main (les vecteurs ne se contentent pas de recopier le code)
n0 = vb["nettoyer"][0]["attendu"]
verifier(n0 == "FileNotFoundError: '~/terrain/….txt'", "le dossier personnel devient ~, le nom de la créature …")
verifier(vb["nettoyer"][1]["attendu"] == "~\\jeu et ~/jeu, ~", "Windows : les deux sortes de barres, le nom d'utilisateur")
verifier(vb["nettoyer"][2]["attendu"] == "Bo et al vont bien", "les mots de moins de 3 lettres ne sont pas touchés")
r0 = vb["rapport"][0]
verifier(r0["titre"] == "[bug] KeyError: 'biome' (monde_dessin.py:212)", "le titre : l'erreur et l'endroit")
verifier(r0["corps"].startswith("Ce que je faisais : \n\nVersion : 0.4 · PC\n"), "le corps commence par « Ce que je faisais »")
verifier(r0["adresse"].startswith("https://github.com/grecdel/terminagotchi/issues/new?title=%5Bbug%5D%20KeyError%3A%20%27biome%27"),
         "l'adresse : la page « nouveau signalement » du dépôt, titre encodé")
verifier(vb["rapport"][1]["titre"] == "[bug] un souci dans le jeu" and "Dernière commande" not in vb["rapport"][1]["corps"]
         and "```" not in vb["rapport"][1]["corps"], "sans panne : un titre simple, pas de ligne vide « commande », pas de trace")
r2 = vb["rapport"][2]["corps"]
verifier(r2.count("\n") < 30 and "f7.py:7 g7" not in r2 and "f19.py" in r2 and max(len(l) for l in r2.split("\n")) <= 160,
         "trace : les 12 dernières lignes, 160 caractères au plus par ligne")
verifier(len(vb["rapport"][2]["titre"]) == 6 + 80 and vb["rapport"][2]["titre"].endswith("…"), "le titre est coupé à 80 caractères")
verifier(all(len(r["adresse"]) < 8000 for r in vb["rapport"]), "l'adresse reste courte (< 8000 caractères)")
verifier("%2B" in vb["rapport"][3]["adresse"] and "%26" in vb["rapport"][3]["adresse"] and "%23" in vb["rapport"][3]["adresse"]
         and "~%20ok" in vb["rapport"][3]["adresse"] and "%F0%9F%98%B5" in vb["rapport"][3]["adresse"],
         "encodage : + & # % et emoji encodés, ~ gardé")

# ---------------------------------------------------------------- 2. le rapport du PC et tg bug
print("2. Le rapport du PC, `tg bug`")
core.SAVE_DIR.mkdir(parents=True, exist_ok=True)
home = os.path.expanduser("~")
st = core.migrate(core.new_state("Noisette", "fr"))
st["compte"] = {"cle": "SECRET-CLE", "pseudo": "Zorglub"}
core.save(st)
sys.argv = ["tg", "monde"]
try:
    {}["biome"]
except KeyError:
    f = sur.noter_trace()
log = Path(f).read_text(encoding="utf-8")
verifier("[tg monde] Traceback" in log, "erreurs.log garde la commande qui a planté")
(core.SAVE_DIR / "erreurs.log").write_text(log + "2026-11-03 10:00:00 [tg sauvegarde exporter " + home + "/Noisette] Traceback (most recent call last):\n"
                                           '  File "C:\\Users\\Zorglub\\tg\\app.py", line 12, in _main\n    x()\n'
                                           f'  File "{home}/tg/sauvegarde.py", line 40, in exporter\n    open(p)\n'
                                           f"PermissionError: [Errno 13] Permission denied: '{home}/Noisette.tgsauve'\n\n",
                                           encoding="utf-8")
ch = signaler.champs_pc(core.load())
tout = json.dumps(ch, ensure_ascii=False)
verifier(ch["commande"] == "tg sauvegarde exporter ~/…", f"la dernière panne : sa commande ({ch['commande']})")
verifier(ch["erreur"].startswith("PermissionError") and ch["erreur"].endswith("(sauvegarde.py:40)"), f"l'erreur et l'endroit ({ch['erreur'][:70]})")
verifier(ch["trace"][:2] == ["app.py:12 _main", "sauvegarde.py:40 exporter"], "la trace : des noms de fichiers seulement (chemins Windows aussi)")
verifier(home not in tout and "Noisette" not in tout and "Zorglub" not in tout and "SECRET" not in tout,
         "jamais : dossier personnel, nom de la créature, pseudo, clé du compte")
verifier(ch["langue"] == "fr" and ch["version"].startswith(core.VERSION) and "Python" in ch["appareil"], "version, système, langue")


def jouer(reponses, ouvrir=None):
    it = iter(reponses)
    vus = []
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        r = signaler.commande(demander=lambda p: (vus.append(p), next(it, ""))[1], ouvrir=ouvrir)
    return r, sortie.getvalue(), vus


q, rep = apparence.question_adulte(7)
apparence_q = apparence.question_adulte
apparence.question_adulte = lambda n=None: (q, rep)
r, s, vus = jouer(["12"])
verifier("Tu es un adulte ?" in vus[0] and q in vus[0] and r == langue.t("bug.non") and "Ce qui partira" not in s,
         "la question des grands d'abord ; mauvaise réponse : rien n'est montré")
ouvertes = []
r, s, vus = jouer([rep, "o"], ouvrir=lambda u: ouvertes.append(u) or True)
verifier(len(ouvertes) == 1 and ouvertes[0].startswith(signaler.PAGE + "?title=") and "Ce qui partira" in s and r == langue.t("bug.ouverte"),
         "[o] : le rapport est montré, puis la page pré-remplie s'ouvre (rien d'autre)")
verifier(home not in ouvertes[0] and "Noisette" not in ouvertes[0] and "Zorglub" not in ouvertes[0], "l'adresse ne contient rien de personnel")
r, s, vus = jouer([rep, "o"], ouvrir=lambda u: False)
verifier(signaler.PAGE in r, "pas de navigateur : l'adresse est donnée à copier")
fichier = Path(home) / signaler.FICHIER
r, s, vus = jouer([rep, "f"])
verifier(fichier.exists() and "[bug] PermissionError" in fichier.read_text(encoding="utf-8") and "~/" + signaler.FICHIER in r,
         "[f] : le rapport est écrit dans ~/rapport-terminagotchi.txt")
fichier.unlink()
r, s, vus = jouer([rep, "n"])
verifier(r == langue.t("bug.annule") and not fichier.exists(), "[n] : rien n'est envoyé ni écrit")
r, s, vus = jouer([rep, ""])
verifier(r == langue.t("bug.annule"), "Entrée seule : rien")
apparence.question_adulte = apparence_q
src = (DEPOT / "pc" / "tg" / "signaler.py").read_text(encoding="utf-8")
verifier("urllib" not in src and "requete" not in src and "socket" not in src, "signaler.py ne fait aucun appel réseau")
(core.SAVE_DIR / "erreurs.log").unlink()
ch = signaler.champs_pc(None)
verifier(ch["erreur"] == "" and ch["trace"] == [] and signaler.rapport(ch, signaler.etiquettes())[0] == "[bug] un souci dans le jeu",
         "sans panne notée : `tg bug` marche quand même (titre simple)")
import subprocess  # noqa: E402
env = dict(os.environ, PYTHONPATH=str(ICI.parent))
p = subprocess.run([sys.executable, "-m", "tg", "bug"], input="0\n", capture_output=True, text=True, env=env, timeout=60)
verifier(p.returncode == 0 and "Tu es un adulte ?" in p.stdout and "Ce n'est pas la bonne réponse" in p.stdout, "`tg bug` depuis le terminal")

# ---------------------------------------------------------------- 3. le nuage
print("3. Le nuage de synchro")
from tg import app  # noqa: E402


def avec_compte(**c):
    def f(s):
        s["compte"] = dict({"cle": "k", "pseudo": "Lou", "serveur": "http://127.0.0.1:9", "base": {"total": 0}}, **c)
        s["total"] = 5
    core.modifier(f)


avec_compte()
verifier(recense.nuage(core.load()) is None and recense.nuage_pc(core.load()) == "", "compte à jour : rien à l'écran")
msg = recense.synchroniser(forcer=True)
s2 = core.load()
verifier(s2["compte"].get("hors") is True and recense.nuage(s2) == ("hors", 5), f"le site ne répond pas → hors ligne, 5 en attente ({msg[:50]})")
ecran = app.render(s2, 0, False)
verifier("📴 hors ligne · 5 en attente" in ecran, "l'écran de tg le montre à droite du nom")
verifier("📴 Pas d'Internet" in recense.commande([]), "`tg compte` explique en une ligne")
core.modifier(lambda s: s["compte"].update(en_cours=__import__("time").time()))
verifier(recense.nuage(core.load()) == ("envoi", 0) and "☁" in recense.nuage_pc(core.load()), "pendant un envoi : ☁ envoi…")
core.modifier(lambda s: s["compte"].update(en_cours=__import__("time").time() - 300))
verifier(recense.nuage(core.load())[0] == "hors", "un envoi trop vieux (fil coupé) n'est plus « en cours »")
# une synchro réussie (réponse du site imitée) efface le nuage
vrai = recense.requete
recense.requete = lambda url, *a, **k: {"etat": {"xp": 0, "total": 5, "colles": 0, "stats": {}}}
recense.synchroniser(forcer=True)
recense.requete = vrai
s3 = core.load()
verifier(s3["compte"].get("hors") is False and recense.nuage(s3) is None and "📴" not in app.render(s3, 0, False),
         "une synchro réussie : le nuage s'en va")
core.modifier(lambda s: s.update(compte={}))
verifier(recense.nuage(core.load()) is None, "sans compte : jamais de nuage")

# ---------------------------------------------------------------- 4. langues
print("4. Les textes dans les 14 langues")
cles = ["rec.nuage.mot.hors", "rec.nuage.mot.envoi", "rec.nuage.attente", "rec.nuage.dit.hors", "rec.nuage.dit.envoi",
        "bug.titre", "bug.adulte", "bug.question", "bug.non", "bug.partira", "bug.jamais", "bug.pc.o", "bug.pc.f", "bug.pc.n",
        "bug.ouverte", "bug.pas_navigateur", "bug.ecrit", "bug.annule", "bug.apres", "bug.terminal_du_jeu"] + \
       ["bug.l." + k for k in ETIQ]
for code in langue.LANGUES:
    langue.definir(code)
    tx = [langue.t(k, n=3, q="12 × 13", fichier="f", url="u") for k in cles]
    verifier(all(x and not x.startswith(("bug.", "rec.nuage")) and "{" not in x for x in tx)
             and langue.t("bug.pc.o").startswith("[o]") and langue.t("bug.pc.f").startswith("[f]") and langue.t("bug.pc.n").startswith("[n]")
             and "`tg bug`" in langue.t("bug.apres"), f"{code} : {tx[5]} · {tx[0]}")
langue.definir("fr")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
