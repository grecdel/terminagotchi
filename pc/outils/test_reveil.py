"""Tests du réveil du Terminaworld et du monde de la carte (idées 31 à 39, 88 ; pc/tg/reveil.py, carte_scene.py).

    python3 pc/outils/test_reveil.py            (depuis la racine du dépôt)
    python3 pc/outils/test_reveil.py --ecrire   réécrit d'abord donnees/reveil/vecteurs.json (lu aussi par
                                                tests/jvm/Reveil.kt : le même calcul en Kotlin)

1. Les vecteurs partagés avec Kotlin : le réveil (paysages, lieux, ★), la signature, la commande de « Y aller »,
   le moment de la journée, la saison, le hasard (FNV), l'événement rare du jour, la météo, les quêtes du monde.
2. Les copies de zones.json (PC, Android) sont identiques ; les masques et l'endormi existent et sont alignés.
3. Une vraie partie : chapitres → biomes, mondes → lieux, une nouvelle à la fois, jamais de retour en arrière ;
   les lieux secrets, les trésors (find) et les habitants posés dans les dossiers des mondes, leurs quêtes ;
   le livre des gardiens ; l'événement rare (on ne peut pas le rater) ; tg carte.
4. L'image de la carte (Pillow et Python pur) et la carte de l'espace (survol, clic = Y aller, fiche, livre,
   carnet, animation qui se passe d'un clic, « effets : aucun »).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DEPOT / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_test_reveil_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")

from tg import core, histoire, langue, quetes, reveil as R  # noqa: E402

VECTEURS = DEPOT / "donnees" / "reveil" / "vecteurs.json"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
    print(("  ✔ " if c else "  ✖ ") + m)


# ---------------------------------------------------------------- 1. vecteurs
CAS = [
    {"ailes": [], "oeuf": "feu", "ouverts": [], "allumes": [], "etoiles": []},
    {"ailes": ["reveil"], "oeuf": "feu", "ouverts": [], "allumes": [], "etoiles": []},
    {"ailes": ["reveil", "nid"], "oeuf": "feu", "ouverts": [], "allumes": [], "etoiles": []},
    {"ailes": ["reveil", "nid", "grenier", "bibliotheque"], "oeuf": "feu", "ouverts": ["port", "forge", "temps"],
     "allumes": ["port"], "etoiles": []},
    {"ailes": ["reveil", "nid", "machines", "cave"], "oeuf": "feu", "ouverts": ["port"], "allumes": ["port"], "etoiles": ["port"]},
    {"ailes": ["reveil", "nid", "grenier", "machines", "dortoir"], "oeuf": "plante", "ouverts": [], "allumes": [], "etoiles": []},
    {"ailes": ["reveil", "nid", "grenier", "cave", "bibliotheque", "machines", "dortoir", "atelier", "tour", "coeur"],
     "oeuf": "glace", "ouverts": ["port", "citadelle", "sommet"], "allumes": ["port", "citadelle"], "etoiles": ["citadelle"]},
    {"ailes": ["reveil", "nid", "cave", "coeur", "grenier"], "oeuf": "ombre", "ouverts": [], "allumes": [], "etoiles": []},
    {"ailes": ["reveil", "nid", "tour"], "oeuf": "inconnu", "ouverts": ["ondes"], "allumes": ["ondes"], "etoiles": ["ondes"]},
    {"ailes": ["nid", "telephone", "reveil"], "oeuf": "eau", "ouverts": [], "allumes": [], "etoiles": []},
]
CHEMINS = [["", "port"], ["grenier", "port"], ["grenier/album", "port"], ["grenier/album/x", "port"], ["port", "port"],
           ["port", "port/quai"], [None, "port"], ["port/quai", ""], ["robots", ""], ["", ""], ["grenier", ""],
           ["temps/album", "temps"], ["temps/album/a/b", "temps"], ["nid", "nid"], ["vestibule", "nid"]]
EVTS = [["1:1000", "20261103", ["racine", "glace"], []], ["1:1000", "20261104", ["racine"], []],
        ["7:42", "20261105", ["racine", "eau", "feu"], ["baleine"]], ["7:42", "20261106", [], []]] + \
       [["3:99", f"202612{j:02d}", ["racine", "feu", "eau", "glace", "plante"], ["etincelles"]] for j in range(1, 13)]
METEO = [
    {"cmds": [], "t": 100, "avant": None},
    {"cmds": [["ls", 0], ["pwd", 10]], "t": 20, "avant": None},
    {"cmds": [["ls", 0], ["cat a.txt | grep b", 10]], "t": 20, "avant": None},
    {"cmds": [["ping -c 1 127.0.0.1", 10]], "t": 20, "avant": None},
    {"cmds": [["ls", 1], ["ls", 2], ["cd x", 3], ["ls", 4], ["pwd", 5]], "t": 6, "avant": None},
    {"cmds": [["ls", 1]], "t": 500, "avant": ["pluie", 450]},
    {"cmds": [["ls", 1]], "t": 500, "avant": ["pluie", 300]},
    {"cmds": [["Test-Connection localhost", 490]], "t": 500, "avant": ["calme", 0]},
    {"cmds": [["echo ok | sort", 499], ["rm -rf x", 499.5]], "t": 500, "avant": ["brume", 420]},
]


def calculer_vecteurs():
    v = {"calcul": [], "chemin": [], "moment": {}, "saison": {}, "fnv": {}, "evenement": [], "meteo": [], "quetes": []}
    for c in CAS:
        e = R.calcul(c["ailes"], c["oeuf"], c["ouverts"], c["allumes"], c["etoiles"])
        v["calcul"].append({"entree": c, "biomes": e["biomes"], "lieux": e["lieux"], "etoiles": e["etoiles"],
                            "signature": R.signature(e)})
    for ici, cible in CHEMINS:
        v["chemin"].append([ici, cible, R.chemin_cd(ici, cible)])
    v["moment"] = {str(h): R.moment(h) for h in range(24)}
    v["saison"] = {str(m): R.saison(m) for m in range(1, 13)}
    v["fnv"] = {s: R.fnv(s) for s in ("", "a", "1:1000:20261103", "Noisette ✨", "Terminaworld")}
    for g, j, rev, vus in EVTS:
        v["evenement"].append([g, j, rev, vus, R.evenement_du_jour(g, j, rev, vus)])
    for c in METEO:
        m = R.meteo([tuple(x) for x in c["cmds"]], c["t"], tuple(c["avant"]) if c["avant"] else None)
        v["meteo"].append(dict(c, sortie=list(m)))
    for q in R.zones()["quetes"]:
        v["quetes"].append({"id": q["id"], "piece": q["piece"], "sorte": q["sorte"], "fichier": q["fichier"], "xp": q["xp"],
                            "apres": q.get("apres"), "buts": [b[0] for b in q["but"]], "pose": sorted(q.get("pose") or {})})
    return json.loads(json.dumps(v))


print("1. Les vecteurs partagés avec Kotlin (donnees/reveil/vecteurs.json)")
vec = calculer_vecteurs()
if "--ecrire" in sys.argv or not VECTEURS.exists():
    VECTEURS.write_text(json.dumps(vec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  (vecteurs écrits : {VECTEURS})")
lu = json.loads(VECTEURS.read_text(encoding="utf-8"))
for k in vec:
    verifier(vec[k] == lu[k], f"vecteurs « {k} » : le calcul Python n'a pas changé")
e = R.calcul(["reveil", "nid"], "feu", [], [], [])
verifier(e["biomes"] == ["racine", "feu"], "chapitre 1 → la Racine, chapitre 2 → le biome de l'œuf (Feu)")
e = R.calcul(["reveil", "nid", "machines"], "feu", [], [], [])
verifier(e["biomes"] == ["racine", "feu", "glace"], "l'aile du Feu, déjà réveillé par l'œuf : la Glace à la place")
e = R.calcul(["reveil", "nid", "machines", "coeur"], "feu", [], [], [])
verifier(len(e["biomes"]) == 10, "le Cœur réveille tout ce qui dort encore")
e = R.calcul(["reveil"], "feu", ["port"], ["forge"], [])
verifier(e["lieux"]["port"] == R.LANTERNE and e["lieux"]["forge"] == R.ALLUME and e["lieux"]["sommet"] == R.FERME,
         "les lieux : lanterne (ouvert), allumé (palier 1), éteint (fermé), même dans un biome endormi")
verifier(R.chemin_cd("grenier", "port") == "cd ../port" and R.chemin_cd("grenier/album/x", "port").startswith("cd ~/"),
         "« Y aller » : relatif s'il est court (2 pas), complet sinon")
verifier(R.moment(22) == "nuit" and R.moment(6) == "nuit" and R.moment(7) == "matin" and R.moment(19) == "soir",
         "la nuit de 21 h à 7 h (comme app.py), le matin 7–9 h, le soir 18–21 h")
verifier(R.meteo([("ls", 0)], 500)[0] == "brume" and R.meteo([("cmd_qui_echoue", 499)], 500)[0] == "calme",
         "la météo : brume douce après une pause ; une erreur ne fait jamais de mauvais temps")

# ---------------------------------------------------------------- 2. les fichiers
print("2. Les fichiers")
z = (DEPOT / "donnees" / "reveil" / "zones.json").read_bytes()
verifier(z == (DEPOT / "pc" / "tg" / "reveil.json").read_bytes() == (DEPOT / "app" / "src" / "main" / "assets" / "reveil.json").read_bytes(),
         "donnees/reveil/zones.json = pc/tg/reveil.json = assets/reveil.json (relancer generer_intro.py sinon)")
try:
    from PIL import Image
    m = Image.open(DEPOT / "pc" / "tg" / "reveil_masques.png")
    verifier(m.size == (480, 270 * 27), f"les 27 masques en bandes de 480×270 ({m.size})")
    v_, d_ = Image.open(DEPOT / "pc" / "tg" / "carte_monde.png"), Image.open(DEPOT / "pc" / "tg" / "carte_dort.png")
    verifier(v_.size == d_.size == (960, 540), "le vivant et l'endormi ont la même taille (alignés)")
    bands = [list(m.crop((0, i * 270, 480, (i + 1) * 270)).getdata()) for i in range(10)]
    sommes = [sum(b[k] for b in bands) for k in range(0, 480 * 270, 997)]
    verifier(all(250 <= s <= 260 for s in sommes), "les 10 masques de paysage se partagent toute l'image (somme ≈ 255)")
except ImportError:
    print("  (Pillow absent : masques non vérifiés)")
verifier((DEPOT / "pc" / "tg" / "reveil_masques.bin").read_bytes()[:4] == b"TGM1", "les masques du terminal (Python pur)")
ill = DEPOT / "donnees" / "illustrations"
verifier((ill / "dort_aligne.png").exists() or (DEPOT / "donnees" / "reveil" / "dort_provisoire.jpg").exists(),
         "l'endormi : dort_aligne.png déposé, sinon le provisoire")

# ---------------------------------------------------------------- 3. une vraie partie
print("3. Une vraie partie")
langue.definir("fr")
T = core.TERRAIN
T.mkdir(parents=True, exist_ok=True)
st = core.new_state("Noisette")
core.migrate(st)
st["oeuf_type"] = "feu"
st.setdefault("guide", {})["type_c"] = "feu"
from tg import intro  # noqa: E402
intro.tout_debloquer(st)
h = histoire.h_(st)
R.tick(st)
verifier(R.r_(st)["dit"] is not None and not st.get("bubble"), "une nouvelle partie : rien à dire, tout dort")
h["ailes"] = ["reveil"]
st.pop("bubble", None)
R.tick(st)
verifier("Racine" in (st.get("bubble") or [""])[0], "chapitre 1 fini : « La Racine se réveille »")
h["ailes"].append("nid")
st.pop("bubble", None)
st.pop("bulles", None)
R.tick(st)
verifier("Feu" in (st.get("bubble") or [""])[0] and "1 / 9" in (st.get("bubble") or [""])[0],
         "chapitre 2 : le biome de l'œuf (Feu), biomes réveillés : 1 / 9")
for c in ("grenier", "cave", "bibliotheque"):
    h["ailes"].append(c)
    for lid in histoire.PAR_CHAP[c]["lecons"]:
        if lid not in h["faits"]:
            h["faits"].append(lid)
for lid in histoire.PAR_CHAP["nid"]["lecons"] + histoire.PAR_CHAP["reveil"]["lecons"]:
    if lid not in h["faits"]:
        h["faits"].append(lid)
histoire.meubler(st)
ouv, allu, eto = R.mondes_etats(st)
verifier("port" in ouv and "temps" in ouv, f"niveau 4 : les mondes s'ouvrent ({', '.join(ouv)})")
dits = []
for _ in range(30):
    st.pop("bubble", None)
    st.pop("bulles", None)
    R.tick(st)
    if st.get("bubble"):
        dits.append(st["bubble"][0])
verifier(len(dits) == 3, f"une nouvelle à la fois : 3 biomes de plus, 3 phrases ({len(dits)})")
rv = R.r_(st)
avant = list(rv["dit"]["biomes"])
h["ailes"].remove("cave")
R.tick(st)
verifier(rv["dit"]["biomes"] == avant, "jamais de retour en arrière (ce qui est dit reste dit)")
h["ailes"].append("cave")
# les quêtes du monde
quetes.poser(st)
q = quetes.q_(st)
poses = [x for x in R.zones()["quetes"] if x["id"] in q["poses"]]
verifier(any(x["sorte"] == "cachette" and x["piece"] == "port" for x in poses) and (T / "port" / ".epave").is_dir(),
         "le lieu secret du Port est posé (port/.epave, un dossier caché)")
verifier((T / "port" / "habitant_plouftin.txt").is_file() and not (T / "port" / "habitant_tritonnet.txt").exists(),
         "le 1er habitant du Port est posé ; le 2e attend le palier 2")
verifier(all(str(p).startswith(str(T)) for p in T.rglob("*")), "le jeu n'écrit que dans le terrain")
# entrer dans la cachette la trouve
st.setdefault("maison", {}).setdefault("visites", []).append("port/.epave")
quetes.tick(st, [], [])
verifier("m02" in q["finies"], "entrer dans port/.epave : lieu secret trouvé (souvenir + XP)")
tr, (n, tot) = R.secrets_carte(st)
verifier(n >= 1 and tot == 15 and any(x[0] == "m02" for x in tr), f"sur la carte : lieux secrets {n} / {tot}, ceux qui restent invisibles")
# Plouftin : lire sa lettre accepte, ranger les bouteilles finit
quetes.tick(st, ["cat habitant_plouftin.txt"], [str(T / "port")])
verifier("m18" in q["actives"], "lire habitant_plouftin.txt accepte la quête")
(T / "port" / "filet").mkdir(exist_ok=True)
for f in T.joinpath("port").rglob("bouteille_*"):
    f.rename(T / "port" / "filet" / f.name)
quetes.tick(st, ["mv"], [str(T / "port")])
verifier("m18" in q["finies"], "les 3 bouteilles rangées dans filet/ : quête finie, Plouftin dit merci")
hb = [x for x in R.habitants_carte(st) if x["id"] == "m18"]
verifier(hb and not hb[0]["besoin"], "sur la carte : plus de « ! » au-dessus de Plouftin")
# un trésor *.secret, à trouver avec find
temps_ok = (T / "temps").is_dir()
if temps_ok and "m15" in q["poses"]:
    quetes.tick(st, ["find . -name '*.secret'", "cat temps/.terrier_du_tronc/racines/cle.secret"], [str(T), str(T)])
    verifier("m15" in q["finies"], "lire cle.secret (trouvé avec find) : trésor trouvé")
# les lieux et « Y aller »
lx = {x["id"]: x for x in R.lieux_carte(st, ici_rel="grenier")}
verifier(lx["port"]["cmd"] == "cd ../port" and lx["port"]["etat"] in ("ouvert", "allume"), "la fiche du Port : « cd ../port »")
verifier(lx["sommet"]["etat"] == "ferme" and lx["sommet"]["cmd"] is None and lx["sommet"]["manque"] != "" or lx["sommet"]["etat"] != "ferme",
         "un lieu pas encore ouvert : pas de « Y aller », ce qui manque pour l'ouvrir")
# l'événement rare : un jour où il y en a un ; vu, il reste quelques minutes puis s'en va ; jamais raté
jour = next(f"2026{m:02d}{j:02d}" for m in range(1, 13) for j in range(1, 29)
            if R.evenement_du_jour(R.graine(st), f"2026{m:02d}{j:02d}", R.etat(st)["biomes"], []))
ev = R.evenement(st, 1000.0, jour)
verifier(ev is not None, f"un jour d'événement rare ({jour} : {ev[0] if ev else None})")
R.noter_evenement(st, ev[0], 1000.0, jour)
verifier(ev[0] in R.r_(st)["evts"] and R.evenement(st, 1100.0, jour) and not R.evenement(st, 2000.0, jour),
         "vu : dans le carnet, visible encore quelques minutes, puis il s'en va (aucun compte à rebours)")
# tg carte
lignes = R.lignes_carte(st)
txt = "\n".join(lignes)
verifier("Biomes réveillés" in txt and "cd ~/terrain_terminagotchi/port" in txt or "cd port" in txt,
         "tg carte : le bilan et la commande à taper pour chaque lieu ouvert")
# le livre des gardiens : une boîte maîtrisée ouvre son chapitre
from tg import citadelle  # noqa: E402
try:
    car = Path(citadelle.dossier() if hasattr(citadelle, "dossier") else T / "citadelle")
except Exception:  # noqa: BLE001
    car = T / "citadelle"
ancien = citadelle.carnet
citadelle.carnet = lambda: "[inspecteur] enumeration boîte maîtrisée (ok)\n"
verifier(R.livre_ouverts(st) == [1], "une boîte maîtrisée à la Citadelle (repérage) : le chapitre 1 s'ouvre")
st.pop("bubble", None)
for _ in range(20):
    R.tick(st)
verifier(1 in [int(x) for x in R.r_(st)["gardiens"]], "la créature annonce le chapitre (une fois)")
if (T / "temps").is_dir() and (histoire.ouvert(st, "temps") or histoire.fini(st, "temps")):
    verifier((T / R.fichier_gardien(1)).is_file(), "le chapitre est posé dans la Bibliothèque du Temps (cat …)")
citadelle.carnet = ancien
core.save(st)

# ---------------------------------------------------------------- 4. l'image et l'espace
print("4. L'image de la carte et la carte de l'espace")
try:
    import time
    e = R.etat(st)
    sig = R.signature(e)
    t0 = time.time()
    im = R.image_carte(sig, "nuit", "hiver")
    verifier(im.size == (960, 540) and time.time() - t0 < 3, f"la carte mélangée (Pillow) en {time.time() - t0:.2f} s")
    a, b = R.image_carte(R.signature(R.calcul([], "feu", [], [], []))), R.image_carte(R.signature(R.calcul(["reveil", "nid", "coeur"], "feu", [], [], [])))
    from PIL import ImageChops, ImageStat
    verifier(ImageStat.Stat(ImageChops.difference(a, b)).mean[0] > 10, "tout endormi ≠ tout vivant")
except ImportError:
    print("  (Pillow absent)")
px = R.pixels_terminal(R.etat(st), 64, 36)
verifier(len(px) == 64 * 36 and all(len(p) == 3 for p in px[:10]), "la carte en Python pur (terminal), sans bibliothèque")
from tg import espace as Esp  # noqa: E402
from tg import espace_scene as S  # noqa: E402
from tg import app  # noqa: E402
import tg.bureau_vie as V  # noqa: E402
horloge = [1000.0]
V.maintenant = lambda: horloge[0]
esp = Esp.Espace(app.etape)
esp.onglet = "carte"
esp.mini.dossier = str(T / "grenier") if (T / "grenier").is_dir() else str(T)
m = esp.modele()
verifier(m.get("reveil") and m["reveil"]["photo"].startswith("reveil:"), "l'espace montre la carte du réveil")
L, Z, taille = S.scene(m, esp.t)
zs = [z_ for z_ in Z if str(z_[4]).startswith("rv:lieu:")]
verifier(len(zs) >= 5, f"des lieux cliquables sur la carte ({len(zs)})")
zp = next((z_ for z_ in zs if z_[4] == "rv:lieu:port"), None)
if zp:
    esp.survol(zp[0] + 2, zp[1] + 2, Z)
    verifier(esp.rv["survol"] == "port", "survol du Port : la bulle")
    esp.clic_droit(zp[0] + 2, zp[1] + 2, Z)
    verifier(esp.rv["fiche"] == "port", "clic droit : la fiche « En savoir plus »")
    esp.rv["fiche"] = None
    esp.mini.saisie = ""
    esp.clic(zp[0] + 2, zp[1] + 2, Z)
    verifier(esp.mini.saisie.startswith("cd ") and "port" in esp.mini.saisie,
             f"clic : « Y aller » écrit la commande sans la lancer ({esp.mini.saisie!r})")
for a_ in ("rv:livre", "rv:livre:1", "rv:carnet", "rv:hab:m18", "rv:fermer"):
    esp.clic_reveil(a_)
    L, Z, taille = S.scene(esp.modele(), esp.t)
    S.vers_pil(L, taille) if "PIL" in sys.modules else None
verifier(True, "fiche d'habitant, livre, chapitre, carnet : dessinés sans erreur")
# une animation : un biome de plus, la vague se passe d'un clic
st = core.load()
R.noter_carte(st, R.signature(R.etat(st)))
histoire.h_(st)["ailes"].append("machines")
core.save(st)
esp2 = Esp.Espace(app.etape)
esp2.onglet = "terminal"
esp2.state = core.load()
esp2.modele()
verifier(esp2.onglet == "carte" and esp2.rv["file"] and esp2.rv["file"][0]["type"] == "biome",
         "un biome se réveille : l'onglet Carte s'ouvre, la vague attend son tour")
esp2.tick()
verifier(esp2.rv["anim"] is not None, "la vague commence")
esp2.clic_reveil("rv:passer")
verifier(esp2.rv["anim"] is None and not esp2.rv["file"], "un clic la passe")
st = core.load()
st.setdefault("effets", {})["niveau"] = "aucun"
R.noter_carte(st, "0000000000-200000000000000")
core.save(st)
esp3 = Esp.Espace(app.etape)
esp3.state = core.load()
esp3.modele()
verifier(not esp3.rv["file"], "réglage « effets : aucun » : pas d'animation, juste la phrase")

print(f"\n{'✅' if not ko else '❌'} Réveil : {ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
