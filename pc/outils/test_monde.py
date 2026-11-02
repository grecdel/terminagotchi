"""Test du monde des biomes (pc/tg/monde_gen.py, monde_dessin.py, monde.py) et de son intégration dans `tg espace`.

    python3 pc/outils/test_monde.py             (depuis la racine du dépôt)
    python3 pc/outils/test_monde.py --ecrire    (réécrit donnees/monde/vecteurs.json après un changement VOULU)
    python3 pc/outils/test_monde.py --site      (recopie les textes du jeu dans site/src/monde_textes.js)

1. La génération commune : donnees/monde/vecteurs.json (Kotlin : tests/jvm/Monde.kt ; JavaScript : site/test/test.mjs).
2. Le vrai terrain : lire_terrain ne lit que biome/<type>/<parcelle>/ (lecture seule), dans l'ordre parcelle_1, 2…10.
3. Les dessins : chaque sol, chaque objet ; aucun accessoire, la mascotte du site n'apparaît jamais.
4. L'espace de travail : l'onglet Monde, la commande `monde` (en grand), de vraies commandes tapées → de vrais effets,
   la fiche À LA PLACE de la liste (clic sur une créature, « ← Mes créatures », clic à côté, Échap), le réglage des
   effets, l'explication dite 3 fois, le repli tkinter qui garde la carte, le glitch des créatures qui reste.
5. La performance : un grand monde (9 régions × 8 parcelles) se dessine bien sous 50 ms (20 images par seconde).
6. Les textes : chaque clé utilisée existe en 14 langues ; le site a les mêmes textes que le jeu.
"""
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_monde_")
os.environ.pop("HISTFILE", None)
os.environ["SHELL"] = "/bin/bash"

from tg import monde_gen as G  # noqa: E402
from tg import monde_dessin as MD  # noqa: E402
from tg import effets as EF  # noqa: E402

ok = ko = 0


def verif(c, msg):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
        print("  ✗", msg)


def textes_site():
    """Les textes de la page /monde : les clés du jeu (monde.*, efx.*, carte.biome.* → type.*) + celles du site."""
    langues = ["fr", "en", "es", "de", "it", "pt", "ru", "ja", "zh", "ar", "hi", "bn", "ur", "id"]
    actuel = (RACINE / "site/src/monde_textes.js").read_text(encoding="utf-8")
    d0 = json.loads(actuel[actuel.index("export default ") + 15:].rstrip().rstrip(";"))
    out = {}
    for code in langues:
        d = json.loads((RACINE / f"pc/tg/langues/{code}.json").read_text(encoding="utf-8"))
        x = {k: d[k] for k in sorted(d) if k.startswith(("monde.", "efx."))}
        for ty in G.TYPES:
            x["type." + ty] = d["carte.biome." + ty]
        for k, v in (d0.get(code) or {}).items():
            if k.startswith("site."):
                x[k] = v
        out[code] = x
    entete = actuel[:actuel.index("export default ")]
    return actuel, entete + "export default " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"


VEC = RACINE / "donnees" / "monde" / "vecteurs.json"
if "--ecrire" in sys.argv:
    VEC.write_text(json.dumps(G.vecteurs(), ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print("vecteurs réécrits")
if "--site" in sys.argv:
    (RACINE / "site/src/monde_textes.js").write_text(textes_site()[1], encoding="utf-8")
    print("site/src/monde_textes.js recopié")

print("1. La génération commune (vecteurs)")
att = json.loads(VEC.read_text(encoding="utf-8"))
cal = json.loads(json.dumps(G.vecteurs(), ensure_ascii=False, sort_keys=True))
for k in ("hachage", "hasard", "deco"):
    verif(att[k] == cal[k], k)
for i, (a, c) in enumerate(zip(att["mondes"], cal["mondes"])):
    verif(a == c, f"monde {i}")
verif(len(att["mondes"]) == 4, "4 mondes")

print("2. Le vrai terrain (lecture seule)")
tmp = Path(tempfile.mkdtemp(prefix="tg_terrain_"))
for d in ("biome/feu/parcelle_10", "biome/feu/parcelle_2", "biome/feu/grotte", "biome/plante/parcelle_1", "biome/lune/x",
          "nid"):
    (tmp / d).mkdir(parents=True)
(tmp / "biome/plante/parcelle_1/rose.fleur").write_text("")
(tmp / "biome/plante/parcelle_1/.cache").write_text("")
avant = sorted(str(p) for p in tmp.rglob("*"))
terr = G.lire_terrain(tmp)
verif(list(terr) == ["feu", "plante"], f"seules les vraies régions : {list(terr)}")
verif([p["nom"] for p in terr["feu"]] == ["parcelle_2", "parcelle_10", "grotte"], f"ordre des parcelles {terr['feu']}")
verif(terr["plante"][0]["objets"] == ["rose.fleur"] and terr["plante"][0]["caches"] == 1, "objets visibles, cachés comptés")
verif(sorted(str(p) for p in tmp.rglob("*")) == avant, "le monde ne touche à rien (lecture seule)")
m = G.construire(terr)
verif(len(m["hex"]) == 19 * 4, "19 hexagones par parcelle")
verif(any(p["volcan"] for p in m["parcelles"]), "la première parcelle de feu est un volcan")

print("3. Les dessins")
for k in MD.SOLS:
    s = MD.sprite(k, 1, 12, 0)
    verif(any(s.rgba[3::4]), f"sol {k}")
for k in MD.DECORS:
    verif(any(MD.decor(k).rgba[3::4]), f"décor {k}")
code_monde = "".join((RACINE / f"pc/tg/{f}").read_text(encoding="utf-8") for f in ("monde.py", "monde_dessin.py",
                                                                                   "monde_gen.py", "effets.py"))
verif(not re.search(r"mascotte\w*\.png|favicon|icone\.png", code_monde), "la mascotte du site n'apparaît jamais")
verif("accessoire" not in code_monde.replace("aucun accessoire", "").replace("Pas d'accessoires", ""),
      "aucun accessoire sur les créatures")

print("4. L'espace de travail")
from tg import app, core, intro, langue  # noqa: E402
from tg import espace as ES  # noqa: E402
from tg import espace_scene as S  # noqa: E402
import tg.bureau_vie as V  # noqa: E402

T = core.TERRAIN
for d in ("vestibule", "nid", "biome/feu/parcelle_1", "biome/plante/parcelle_1", "biome/plante/parcelle_2",
          "biome/eau/parcelle_1"):
    (T / d).mkdir(parents=True, exist_ok=True)
(T / "biome/plante/parcelle_1/rose.fleur").write_text("rose\n")
(T / "biome/plante/parcelle_1/mot.txt").write_text("bonjour\nle monde\n")
st = core.new_state("Noisette")
core.migrate(st)
st["config"]["langue"] = "fr"
st["espece_compagnon"] = "glandouille"
st["oeuf_type"] = "plante"
intro.tout_debloquer(st)
from tg import guide as GD  # noqa: E402
GD.g_(st)["type_c"] = "plante"                      # le compagnon (Glandouille) est de type plante
st["captures"] = [{"id": f"c{i}", "espece": e, "nom": n, "stade": "bebe", "xp": 0}
                  for i, (e, n) in enumerate([("braisillon", "Brai"), ("gouttelin", "Plic"), ("fumerole", "Fumi")])]
st["captures"][2]["glitch"] = True
core.save(st)
langue.definir("fr")
horloge = [1000.0]
V.maintenant = lambda: horloge[0]


def avancer(esp, s, pas=0.05):
    for _ in range(int(s / pas)):
        horloge[0] += pas
        esp.tick()


def taper(esp, ligne):
    esp.mini.saisie = ligne
    esp.entree()


esp = ES.Espace(app.etape)
esp.mini.dossier = str(T / "biome")
m = esp.modele()
verif("monde" in (m.get("onglets") or []), f"l'onglet Monde est là ({m.get('onglets')})")
esp.onglet = "monde"
avancer(esp, .5)
L, Z, _ = S.scene(esp.modele(), esp.t)
verif(any(op[0] == "calque" for op in L), "le monde est dessiné (dans son calque)")
v = esp.monde
# l'équipe : le guide (le compagnon) d'abord, puis les bestioles les plus récentes : Fumi (feu) prend la parcelle de feu
verif(v.maison == {"compagnon": "plante/parcelle_1", "c2": "feu/parcelle_1", "c1": "eau/parcelle_1"},
      f"une créature par parcelle : {v.maison}")
verif(v.refuge == ["c0"], f"Brai attend au refuge (une seule parcelle de feu) : {v.refuge}")
glitch = next((e for e in v.equipe if e["id"] == "c2"), None)
verif(glitch is not None and glitch["album"] is not None and getattr(glitch["album"], "glitch", None) is not None,
      "le glitch de la créature reste (son album le porte)")
taper(esp, "monde")
verif(esp.monde_grand, "la commande « monde » ouvre le monde en grand")
avancer(esp, .3)
L, Z, _ = S.scene(esp.modele(), esp.t)
verif(any(z[4] == "monde:fermer" for z in Z), "le bouton ✕ du monde en grand")
# de vraies commandes, de vrais effets
taper(esp, "mkdir feu/parcelle_2")
verif(any(e["type"] == "dossier+" for e in v.effets), f"mkdir → la parcelle tombe du ciel ({[e['type'] for e in v.effets]})")
verif(any(p["id"] == "feu/parcelle_2" for p in v.carte["parcelles"]), "le monde a relu le vrai terrain")
avancer(esp, 2.5)
taper(esp, "touch plante/parcelle_2/sapin.arbre")
verif(any(e["type"] == "objet+" for e in v.effets), "touch → un objet tombe")
avancer(esp, 2.5)
taper(esp, "rm plante/parcelle_1/rose.fleur")
verif(any(e["type"] == "objet-" and e.get("pts_avant") for e in v.effets), "rm → confettis là où était l'objet")
avancer(esp, 2.5)
taper(esp, "cat plante/parcelle_1/mot.txt")
lire = [e for e in v.effets if e["type"] == "lire"]
verif(lire and lire[0].get("lignes", [])[:2] == ["bonjour", "le monde"], f"cat → le parchemin montre le vrai texte {lire}")
avancer(esp, 2.5)
taper(esp, "rmdir plante")
verif(any(e["type"] == "refus" for e in v.effets) and any(p["type"] == "plante" for p in v.carte["parcelles"]),
      "rmdir d'un dossier plein : refus doux, rien ne change")
dits = (core.load().get("effets") or {}).get("dits") or {}
verif(sum(dits.values()) >= 4, f"la créature explique (compteurs {dits})")
for _ in range(4):
    avancer(esp, 2.2)
    taper(esp, "mkdir plante/parcelle_9")
    taper(esp, "rmdir plante/parcelle_9")
verif((core.load()["effets"]["dits"]).get("efx.dit.parcelle", 0) == 3, "l'explication n'est dite que 3 fois")
# le réglage
taper(esp, "monde effets aucun")
avancer(esp, 2.5)
taper(esp, "mkdir eau/parcelle_2")
verif(not v.effets, "réglage « aucun » : aucun effet")
taper(esp, "monde effets essentiels")
avancer(esp, .5)
taper(esp, "ps")
verif(not v.effets, "réglage « essentiels » : pas de lucioles (★★)")
taper(esp, "monde effets tous")
verif(esp.niveau_effets() == "tous", "réglage « tous »")
# la fiche à la place de la liste
avancer(esp, 2.5)
L, Z, _ = S.scene(esp.modele(), esp.t)
cz = next((z for z in Z if z[4].startswith("monde:crea:")), None)
verif(cz is not None, "une créature à toucher")
esp.clic(cz[0] + cz[2] / 2, cz[1] + cz[3] / 2, Z)
verif(v.sel == cz[4].split(":", 2)[2], "clic sur une créature : sa fiche")
L, Z, _ = S.scene(esp.modele(), esp.t)
verif(any(z[4] == "monde:liste_retour" for z in Z), "la fiche a « ← Mes créatures » (à la place de la liste)")
verif(not any(z[4].startswith("monde:region:") and z[0] > v.aire[0] + v.aire[2] for z in Z), "la liste n'est plus là")
vue = next(z for z in Z if z[4] == "monde:vue")
esp.lacher(vue[0] + 5, vue[1] + vue[3] - 5, Z)
verif(v.sel is None, "un clic à côté : la liste revient")
esp.clic(cz[0] + cz[2] / 2, cz[1] + cz[3] / 2, Z)
esp.echap()
verif(v.sel is None and esp.monde_grand, "Échap : la fiche se referme d'abord")
esp.echap()
verif(not esp.monde_grand, "Échap encore : le monde en grand se referme")
# glisser et zoomer
esp.onglet = "monde"
avancer(esp, .2)
L, Z, _ = S.scene(esp.modele(), esp.t)
vue = next(z for z in Z if z[4] == "monde:vue")
c0 = list(v.cam)
esp.appui(vue[0] + 50, vue[1] + 50, Z)
esp.bouger(vue[0] + 120, vue[1] + 80)
esp.lacher(vue[0] + 120, vue[1] + 80, Z)
verif(v.cam[0] != c0[0] and v.manuel, "glisser déplace le monde")
z0 = v.cam[2]
esp.molette(vue[0] + 60, vue[1] + 60, 1, Z)
verif(v.cam[2] > z0, "la molette zoome")
# les effets secondaires et ceux des mondes (2 novembre) : chaque sorte se dessine sans erreur, à chaque instant
from tg import effets as EF  # noqa: E402
NOUVEAUX = {"caisse", "lien", "taille", "disque", "arbre", "memoire", "lanternes", "reveil", "journal", "etoile", "album",
            "branche", "fusion", "rembobine", "robot", "grimoire", "loupe", "filet", "sablier", "espion"}
vus, ko_dessin = set(), []
for c_ in EF.vecteurs():
    lot = [dict(x) for x in c_["attendu"] if x["type"] in NOUVEAUX]
    if not lot:
        continue
    vus |= {x["type"] for x in lot}
    try:
        v.preparer(lot)
        v.lancer(lot)
        n_ = 0
        for _ in range(10):
            avancer(esp, .2)
            L, Z, _x = S.scene(esp.modele(), esp.t)
            n_ += len(L)
    except Exception as x:                       # noqa: BLE001
        ko_dessin.append(f"{c_['ligne']} : {x!r}")
verif(not ko_dessin, f"les nouveaux effets se dessinent sans erreur {ko_dessin[:3]}")
verif(vus == NOUVEAUX, f"toutes les sortes nouvelles sont dessinées ({NOUVEAUX - vus})")
# le repli tkinter garde la carte
esp.tk = True
verif("monde" not in (esp.modele().get("onglets") or []), "tkinter : pas d'onglet Monde (la carte reste)")
esp.tk = False

print("5. La performance (20 images par seconde)")
grand = {t: [{"nom": f"parcelle_{i}", "objets": ["chene.arbre", "rose.fleur", "x.txt"]} for i in range(1, 9)]
         for t in G.TYPES}
from tg import monde as MO  # noqa: E402
vg = MO.Vue()
vg.equipe = [{"id": f"c{i}", "nom": "x", "type": t, "album": None, "stade": "bebe"} for i, t in enumerate(G.TYPES * 3)]
t0 = time.perf_counter()
vg._reconstruire(grand)
dt_gen = time.perf_counter() - t0
vg.aire = (0, 0, 1200, 700)
vg.tout_voir(False)
for _ in range(3):                                  # les dessins des prismes, une seule fois
    vg.dessiner([], [], (0, 0, 1600, 760), 0)
for _ in range(40):
    vg.dessiner([], [], (0, 0, 1600, 760), 0)
images = []
for i in range(40):
    vg.tick(0.05)
    t0 = time.perf_counter()
    vg.dessiner([], [], (0, 0, 1600, 760), 0)
    images.append(time.perf_counter() - t0)
moy = sum(images) / len(images) * 1000
print(f"   grand monde ({len(vg.carte['hex'])} hexagones) : construit en {dt_gen * 1000:.0f} ms, "
      f"une image en {moy:.1f} ms (au plus {max(images) * 1000:.1f} ms)")
verif(moy < 50, f"une image en moins de 50 ms ({moy:.1f} ms)")
verif(dt_gen < 2.0, f"le monde se construit vite ({dt_gen:.2f} s)")
(RACINE / "pc/outils").exists()

print("6. Les textes (14 langues, site)")
fr = json.loads((RACINE / "pc/tg/langues/fr.json").read_text(encoding="utf-8"))
utilisees = set(re.findall(r'["\']((?:monde|efx)\.[a-z_.]+)["\']', code_monde + (RACINE / "pc/tg/espace.py").read_text(
    encoding="utf-8") + (RACINE / "pc/tg/espace_scene.py").read_text(encoding="utf-8")))
utilisees = {k for k in utilisees if not k.endswith(".") and k not in ("efx.dit", "monde.py")
              and not any(x.startswith(k + ".") for x in fr)}      # un début de clé (efx.dit.ecrit + .ajoute)
for v_ in json.loads((RACINE / "donnees/effets/vecteurs.json").read_text(encoding="utf-8")):
    utilisees |= set(v_["dit"])
utilisees |= {"efx.niveau." + n for n in EF.NIVEAUX}
manque = sorted(k for k in utilisees if k not in fr)
verif(not manque, f"clés manquantes : {manque}")
for code in ("en", "ar", "ja", "ur"):
    d = json.loads((RACINE / f"pc/tg/langues/{code}.json").read_text(encoding="utf-8"))
    verif(all(k in d for k in utilisees), f"{code} : toutes les clés du monde")
actuel, voulu = textes_site()
verif(actuel == voulu, "site/src/monde_textes.js à jour (python3 pc/outils/test_monde.py --site)")

print(f"{'✅' if ko == 0 else '❌'} Monde : {ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
