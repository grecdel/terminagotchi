"""Tests de la vérification au démarrage (pc/tg/sante.py) et de la sauvegarde exportable (pc/tg/sauvegarde.py).

    python3 pc/outils/test_sante.py            vérifie (code de sortie 1 en cas d'échec)
    python3 pc/outils/test_sante.py --ecrire   réécrit d'abord donnees/sante/exemple_pc.tgsauve (lu aussi par
                                               tests/jvm/SanteSauvegarde.kt : même format de fichier en Kotlin)

1. Les vecteurs partagés avec Kotlin (donnees/sante/vecteurs.json) : la liste des parties réparée.
2. Au démarrage, pour de vrai dans un HOME jetable : liste des parties abîmée ou incomplète, sauvegarde coupée
   (save.tmp), sauvegarde effacée (copie de secours), fichiers du jeu abîmés, empreinte (pas de relecture inutile),
   `tg verifier`, jamais pour `tg prompt`.
3. La sauvegarde exportable : exporter → importer (créature, terrain et droits, partie d'avant rangée), le compte
   jamais dans le fichier, rien d'écrasé, fichier coupé / modifié / d'un téléphone / d'une version future refusés,
   chemins dangereux jamais écrits, 10 parties au plus ; les textes dans les 14 langues.
"""
import base64
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_sante_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))

from tg import core, langue, parties  # noqa: E402
from tg import sante, sauvegarde as SV  # noqa: E402

VECTEURS = DEPOT / "donnees" / "sante" / "vecteurs.json"
EXEMPLE = DEPOT / "donnees" / "sante" / "exemple_pc.tgsauve"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


def remise_a_zero():
    for p in (core.SAVE_DIR, core.TERRAIN):
        if p.exists():
            for d, _s, fs in os.walk(p):
                os.chmod(d, 0o755)
                for f in fs:
                    try:
                        os.chmod(os.path.join(d, f), 0o644)
                    except OSError:
                        pass
            shutil.rmtree(p)


def nouvelle(nom="Pixel", xp=250):
    s = core.migrate(core.new_state(nom, "fr"))
    s["xp"] = xp
    s["compte"] = {"cle": "SECRET-123", "pseudo": "Lou"}
    core.save(s)
    return s


langue.definir("fr")

# ---------------------------------------------------------------- 1. vecteurs communs
print("1. Les vecteurs communs (donnees/sante/vecteurs.json)")
V = json.loads(VECTEURS.read_text(encoding="utf-8"))
for v in V["index"]:
    r = sante.reparer_index(v["index"], v["sauvegarde"], v["rangees"])
    verifier(list(r) == [v["attendu"], v["repare"]], f"{v['nom']} → {r}")

# ---------------------------------------------------------------- 2. au démarrage
print("2. Au démarrage : le jeu vérifie ses fichiers et répare doucement")
remise_a_zero()
m, n = sante.au_demarrage()
verifier(m == [] and n > 20, f"premier lancement : rien à dire ({n} fichiers du jeu lus)")
f_emp = core.SAVE_DIR / sante.EMPREINTE
verifier(f_emp.exists(), "l'empreinte des fichiers du jeu est rangée (verification.json)")
t0 = time.time()
m, _ = sante.au_demarrage()
duree = time.time() - t0
verifier(m == [] and duree < 0.3, f"deuxième lancement : rien n'a changé, pas de relecture ({duree * 1000:.0f} ms)")

nouvelle("Pixel")
pid = parties.nouvelle("Brindille", "fr", lambda s: "œuf") or ""
verifier(len(pid) == 8 and core.load()["name"] == "Brindille", "deux parties : Pixel rangée, Brindille active")
idx_f = parties.dossier() / "index.json"
idx_f.write_text("{coupé", encoding="utf-8")
m, _ = sante.au_demarrage()
idx = json.loads(idx_f.read_text(encoding="utf-8"))
verifier([k for k, _ in m] == ["sante.index"] and idx["active"] == pid and "1" in idx["ordre"],
         f"liste des parties abîmée : refaite ({idx}) ; « {sante.textes(m)[0]} »")
verifier(any(p.name.startswith("index.json.casse-") for p in parties.dossier().iterdir()), "l'ancienne est gardée à côté (index.json.casse-…)")
verifier({p["nom"] for p in parties.liste()} == {"Pixel", "Brindille"}, "le menu des parties retrouve les deux créatures")
idx_f.write_text(json.dumps({"active": pid, "ordre": [pid]}), encoding="utf-8")
m, _ = sante.au_demarrage()
verifier([k for k, _ in m] == ["sante.index"] and "1" in json.loads(idx_f.read_text())["ordre"], "une partie rangée oubliée par la liste : rajoutée")
m, _ = sante.au_demarrage()
verifier(m == [], "ensuite : plus rien à réparer")

# sauvegarde coupée : save.tmp bon, save.json abîmé
bon = core.SAVE_FILE.read_bytes()
for b in core._secours():
    if b.exists():
        os.utime(b, (time.time() - 3600, time.time() - 3600))
tmp = core.SAVE_FILE.with_suffix(".tmp")
st = json.loads(bon)
st["xp"] = 999
tmp.write_text(json.dumps(st), encoding="utf-8")
core.SAVE_FILE.write_text('{"name": "Bri', encoding="utf-8")
m, _ = sante.au_demarrage()
verifier([k for k, _ in m] == ["sante.tmp"] and core.load()["xp"] == 999 and not tmp.exists(),
         "sauvegarde coupée, écriture inachevée bonne : remise en place (rien de perdu)")
verifier(any(p.name.startswith("save.json.casse-") for p in core.SAVE_DIR.iterdir()), "le fichier abîmé est gardé à côté")
# sauvegarde effacée : la copie de secours revient
core.save(core.load())
for b in core._secours():
    if not b.exists():
        b.write_bytes(core.SAVE_FILE.read_bytes())
core.SAVE_FILE.unlink()
m, _ = sante.au_demarrage()
verifier([k for k, _ in m] == ["sante.manquante"] and core.load() and core.load()["name"] == "Brindille",
         "sauvegarde effacée (rm) : la copie de secours revient, pas d'œuf neuf en silence")
m, _ = sante.au_demarrage()
verifier(m == [], "une sauvegarde bonne : on n'y touche pas")
# droits retirés : on ne touche à rien (core l'explique)
if os.geteuid() != 0:
    os.chmod(core.SAVE_FILE, 0)
    m, _ = sante.au_demarrage()
    verifier(m == [] and core.SAVE_FILE.exists(), "sauvegarde aux droits retirés : rien n'est déplacé (le jeu explique déjà)")
    os.chmod(core.SAVE_FILE, 0o600)

# fichiers du jeu abîmés : une copie du jeu dans un dossier à part
copie = Path(tempfile.mkdtemp(prefix="tg_copie_")) / "pc"
shutil.copytree(DEPOT / "pc", copie, ignore=shutil.ignore_patterns("__pycache__", "outils"))
(copie / "tg" / "forge.json").write_text('{"coupé', encoding="utf-8")
(copie / "tg" / "langues" / "de.json").write_text("", encoding="utf-8")
code = ("import sys; sys.path.insert(0, %r); from tg import sante\n"
        "m, n = sante.au_demarrage(); print(sorted(k + ':' + p.get('fichier', '') for k, p in m)); print(sante.textes(m)[0])\n"
        "m2, _ = sante.au_demarrage(); print(len(m2))") % str(copie)
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, HOME=tempfile.mkdtemp()))
lignes = r.stdout.splitlines()
verifier(r.returncode == 0 and lignes[:1] == ["['sante.fichier:forge.json', 'sante.langue:langues/de.json']"],
         f"un fichier du jeu et une langue abîmés : dit à l'adulte ({lignes[:1]}) {r.stderr[-300:]}")
verifier(len(lignes) > 1 and "réinstaller" in lignes[1], f"« {lignes[1] if len(lignes) > 1 else ''} »")
verifier(lignes[2:3] == ["2"], "tant qu'il n'est pas réparé, on le redit à chaque lancement")
# dans un .pyz (comme la version téléchargée)
pyz = copie.parent / "jeu.pyz"
shutil.copy(copie.parent / "pc" / "tg" / "langues" / "fr.json", copie.parent / "fr.json")
(copie / "tg" / "forge.json").write_text((DEPOT / "pc" / "tg" / "forge.json").read_text(encoding="utf-8"), encoding="utf-8")
(copie / "tg" / "langues" / "de.json").write_text((DEPOT / "pc" / "tg" / "langues" / "de.json").read_text(encoding="utf-8"), encoding="utf-8")
subprocess.run([sys.executable, "-m", "zipapp", str(copie), "-o", str(pyz)], check=True)
code = ("import sys; sys.path.insert(0, %r); from tg import sante\n"
        "m, n = sante.au_demarrage(); print(m, n); print(sante.commande())") % str(pyz)
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, HOME=tempfile.mkdtemp()))
verifier(r.returncode == 0 and r.stdout.startswith("[] ") and "✅" in r.stdout, f"dans le .pyz : tout se lit ({r.stdout.strip()[:120]}) {r.stderr[-300:]}")
# tg verifier ; tg prompt ne vérifie jamais
r = subprocess.run([sys.executable, str(DEPOT / "pc"), "verifier"], capture_output=True, text=True)
verifier(r.returncode == 0 and r.stdout.startswith("✅ Tout est en ordre"), f"`tg verifier` : « {r.stdout.strip()[:90]} »")
f_emp.unlink()
subprocess.run([sys.executable, str(DEPOT / "pc"), "prompt", "--statut=0"], capture_output=True, text=True)
verifier(not f_emp.exists(), "`tg prompt` (après chaque commande du shell) ne vérifie rien : il reste instantané")

# ---------------------------------------------------------------- 3. la sauvegarde exportable
print("3. La sauvegarde dans un fichier : exporter, importer")
remise_a_zero()
verifier(SV.exporter() == langue.t("svg.rien"), "pas encore de créature : rien à exporter")
s = nouvelle("Pixel", xp=1234)
nid = core.TERRAIN / "nid"
nid.mkdir(parents=True)
(nid / "repas.txt").write_text("pomme\n", encoding="utf-8")
os.chmod(nid / "repas.txt", 0o444)
(core.TERRAIN / "carnet").mkdir()
(core.TERRAIN / "carnet" / "miam.sh").write_text("echo miam\n", encoding="utf-8")
os.chmod(core.TERRAIN / "carnet" / "miam.sh", 0o755)
(core.TERRAIN / "gros.bin").write_bytes(b"x" * (SV.MAX_FICHIER + 1))
os.symlink("/etc/passwd", core.TERRAIN / "lien")
cle = Path(tempfile.mkdtemp(prefix="tg_cle_usb_"))
texte = SV.exporter(str(cle))
fichiers = list(cle.glob("*.tgsauve"))
verifier(len(fichiers) == 1 and fichiers[0].name.startswith("terminagotchi-Pixel-") and str(fichiers[0]) in texte,
         f"exporter dans un dossier (clé USB) : {fichiers[0].name if fichiers else '?'}")
print("     « " + texte.replace("\n", "\n       ") + " »")
brut = fichiers[0].read_text(encoding="utf-8")
o = json.loads(brut)
verifier(o["terminagotchi"] == "sauvegarde" and o["plateforme"] == "pc" and o["nom"] == "Pixel" and o["niveau"] == core.level(1234),
         "le fichier dit ce qu'il contient (jeu, appareil, nom, niveau, date)")
verifier("SECRET-123" not in brut and "compte" not in json.loads(o["contenu"])["partie"], "la clé secrète du compte n'est JAMAIS dans le fichier")
chemins = {e["chemin"]: e for e in json.loads(o["contenu"])["terrain"]}
verifier("nid/repas.txt" in chemins and chemins["nid/repas.txt"]["mode"] == "444" and "gros.bin" not in chemins and "lien" not in chemins,
         "le terrain : les fichiers avec leurs droits (444), sans le fichier trop gros ni le lien")
verifier("2 fichiers" in texte, "les fichiers laissés de côté sont annoncés")
verifier(SV.exporter(str(fichiers[0])).startswith("Ce fichier existe déjà"), "un fichier qui existe déjà n'est jamais écrasé")
# exporter vers un nom de fichier sans extension
SV.exporter(str(cle / "ma_copie"))
verifier((cle / "ma_copie.tgsauve").exists(), "exporter vers un nom choisi : l'extension .tgsauve est ajoutée")

# on continue de jouer, puis on importe : la créature exportée revient comme une partie de plus
st = core.load()
st["name"] = "Autre"
st["xp"] = 5
core.save(st)
os.chmod(nid / "repas.txt", 0o644)
(nid / "repas.txt").write_text("poire\n", encoding="utf-8")
avant = len(parties.liste())
r = SV.importer(str(fichiers[0]))
st = core.load()
verifier(r.startswith("💾 Pixel est de retour") and st["name"] == "Pixel" and st["xp"] == 1234, f"importer : « {r} »")
verifier(len(parties.liste()) == avant + 1 and any(p["nom"] == "Autre" for p in parties.liste()),
         "la partie d'avant est rangée, pas remplacée (tg partie charger)")
verifier((nid / "repas.txt").read_text() == "pomme\n" and stat.S_IMODE(os.stat(nid / "repas.txt").st_mode) == 0o444
         and os.access(core.TERRAIN / "carnet" / "miam.sh", os.X_OK), "le terrain revient avec ses fichiers et ses droits (444, script exécutable)")
verifier(st.get("compte", {}).get("cle") == "SECRET-123", "le compte de l'appareil suit le joueur (comme pour une autre partie)")
verifier(not (core.TERRAIN / "lien").exists(), "aucun lien recréé")

# refus
print("   refus")
def refus(txt):
    try:
        SV.lire(txt)
    except SV.Refus as e:
        return e.cle
    return None
verifier(refus(brut[: len(brut) // 2]) == "svg.refus.illisible", "fichier coupé : refusé (illisible)")
mod = json.loads(brut)
c = json.loads(mod["contenu"]); c["partie"]["xp"] = 999999; mod["contenu"] = json.dumps(c)
verifier(refus(json.dumps(mod)) == "svg.refus.abime", "XP changée à la main dans le fichier : refusé (abîmé)")
mod = json.loads(brut); mod["plateforme"] = "android"
verifier(refus(json.dumps(mod)) == "svg.refus.plateforme", "une sauvegarde du téléphone : expliqué (le compte du jeu)")
mod = json.loads(brut); mod["version"] = 99
verifier(refus(json.dumps(mod)) == "svg.refus.version", "une version future : mettre le jeu à jour")
verifier(refus('{"bonjour": 1}') == "svg.refus.illisible" and refus("") == "svg.refus.illisible", "autre chose qu'une sauvegarde : refusé")
verifier(SV.importer(str(cle / "absent.tgsauve")).startswith("Je ne trouve pas"), "fichier introuvable : dit simplement")
for mauvais in ("../evade.txt", "/etc/x", "a/../../b", "C:/x", "a\\b", "", "./x", "a//b"):
    verifier(SV.chemin_sur(mauvais) is None, f"chemin refusé : {mauvais!r}")
verifier(SV.chemin_sur("nid/repas.txt") == ["nid", "repas.txt"], "chemin normal accepté")
# un fichier piégé (contrôle recalculé) n'écrit rien hors du terrain
c = json.loads(json.loads(brut)["contenu"])
c["terrain"].append({"chemin": "../../evade.txt", "b64": base64.b64encode(b"x").decode()})
c["terrain"].append({"chemin": "nid/../../evade2.txt", "b64": base64.b64encode(b"x").decode()})
contenu = json.dumps(c)
piege = dict(json.loads(brut), contenu=contenu, controle=hashlib.sha256(contenu.encode()).hexdigest())
fp = cle / "piege.tgsauve"
fp.write_text(json.dumps(piege), encoding="utf-8")
r = SV.importer(str(fp))
verifier(r.startswith("💾") and not (Path.home() / "evade.txt").exists() and not (core.TERRAIN.parent / "evade2.txt").exists()
         and not list(Path.home().glob("evade*")), "fichier piégé (../) : importé sans rien écrire hors du terrain")
# 10 parties au plus
while not parties.pleine():
    parties.nouvelle("P", "fr", lambda s: "œuf")
verifier(SV.importer(str(fichiers[0])) == langue.t("svg.plein", max=parties.MAX), "10 parties : on le dit, rien ne change")

# le fichier d'exemple partagé avec Kotlin
if "--ecrire" in sys.argv or not EXEMPLE.exists():
    remise_a_zero()
    s = nouvelle("Exemple", xp=90)
    (core.TERRAIN / "nid").mkdir(parents=True)
    (core.TERRAIN / "nid" / "repas.txt").write_text("pomme\n", encoding="utf-8")
    txt, _ = SV.fabriquer(core.load())
    o = json.loads(txt); o["date"] = "2026-11-03 10:00"
    EXEMPLE.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
e, p, t = SV.lire(EXEMPLE.read_text(encoding="utf-8"))
verifier(p["name"] == "Exemple" and t[0]["chemin"] == "nid", "le fichier d'exemple (lu aussi par Kotlin) se relit")

print("4. Les textes dans les 14 langues")
for code in langue.LANGUES:
    langue.definir(code)
    tx = [langue.t(k, n=3, fichier="f", code="de", max=10, nom="P", taille="1 Ko", niveau=2, date="d")
          for k in ("sante.index", "sante.tmp", "sante.manquante", "sante.fichier", "sante.langue", "sante.ok", "svg.exporte",
                    "svg.aide", "svg.importe", "svg.refus.abime", "svg.refus.plateforme", "svg.plein")]
    verifier(all(x and not x.startswith(("sante.", "svg.")) and "{" not in x for x in tx), f"{code} : {tx[0][:50]}")
langue.definir("fr")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
