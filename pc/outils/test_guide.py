"""Test du guide (PC) : types des bestioles, table des types, talents, régions gardées, combats, fatigue.

    python3 pc/outils/test_guide.py          (crée son propre HOME temporaire)

Les mêmes règles sont testées sur Android par tests/jvm/Guide.kt.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_guide_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "donnees"))

from tg import app, bestiaire as B, combat, core, entrainement, envies, equipe, guide as G, langue  # noqa: E402
import verifier_biomes  # noqa: E402

HOME = Path.home()
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def etape(*lignes, cwd=None):
    return app.etape(spontane=False, defis=False, extra=list(lignes), cwd=cwd)


def sans(x):
    return langue.sans_marques("\n".join(x) if isinstance(x, list) else str(x))


def espece_de_type(ty):
    for e in B.publiques():
        if G.type_de(e, "classique") == ty:
            return e
    raise AssertionError(ty)


def donner(ty, stade="enfant"):
    """Ajoute à l'équipe une bestiole de ce type ; renvoie son nom d'espèce."""
    e = espece_de_type(ty)

    def f(s):
        ind = B.individu(e, False, e["zone"], "classique", qualite=0.5)
        ind["stade"] = stade
        ind["xp"] = 0
        s["captures"].append(ind)
    core.modifier(f)
    return e["nom"]


langue.definir("fr")
(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()

print("Les données des types")
d = json.loads((RACINE / "donnees" / "biomes.json").read_text(encoding="utf-8"))
verifier((RACINE / "pc/tg/biomes.json").read_text(encoding="utf-8") == (RACINE / "donnees/biomes.json").read_text(encoding="utf-8"),
         "pc/tg/biomes.json est la copie exacte de donnees/biomes.json")
verifier((RACINE / "app/src/main/assets/biomes.json").read_bytes() == (RACINE / "donnees/biomes.json").read_bytes(),
         "app/src/main/assets/biomes.json est la copie exacte de donnees/biomes.json")
verifier(tuple(x["id"] for x in d["types"]) == G.TYPES, "les 9 types, dans l'ordre de biomes.json")
par_habitat = {h: x["id"] for x in d["types"] for h in x["habitats"]}
faux = [(e["id"], v["id"]) for e in B.publiques() for v in e["variantes"]
        if G.type_de(e, v["id"]) != verifier_biomes.type_de(e, v["id"], d, par_habitat)]
verifier(not faux, f"le type de chaque variante suit la règle de donnees/verifier_biomes.py ({faux[:3]})")
verifier(G.type_de("abyssor") in G.TYPES, "Abyssor (famille Système) a aussi un type")

print("La table des types")
verifier(G.efficacite("eau", "feu") == 1.5 and G.efficacite("feu", "eau") == 0.67, "Eau > Feu (×1.5 / ×0.67)")
verifier(G.efficacite("feu", "plante") == 1.5 and G.efficacite("plante", "eau") == 1.5, "Feu > Plante > Eau")
verifier(G.efficacite("ciel", "eau") == 1.5 and G.efficacite("roche", "ciel") == 1.5, "Foudre > Eau, Roche > Foudre")
verifier(G.efficacite("glace", "plante") == 1.5 and G.efficacite("machine", "glace") == 1.5
         and G.efficacite("poison", "plante") == 1.5, "Glace > Plante, Machine > Glace, Poison > Plante")
verifier(all(not (b in G.TABLE[a] and a in G.TABLE[b]) for a in G.TYPES for b in G.TYPES), "jamais fort l'un contre l'autre")
verifier(all(G.efficacite(a, a) == 1.0 for a in G.TYPES if a != "ombre"), "un type contre lui-même : ×1")
verifier(all(G.efficacite("ombre", x, nuit=False) == 1.0 and G.efficacite(x, "ombre") == 1.0 for x in G.TYPES),
         "l'Ombre est neutre le jour")
verifier(all(G.efficacite("ombre", x, nuit=True) == 1.5 for x in G.TYPES if x != "ombre"), "la nuit, l'Ombre est forte contre tous")
verifier(all(TALENT in G.TALENTS.values() for TALENT in entrainement.FAMILLE_CMDS), "chaque famille de la salle a un type")
verifier(len(set(G.TALENTS.values())) == 9 and G.TALENTS["ombre"] == "secrets", "9 talents différents (Ombre : passages secrets)")
verifier((G.degats(1, 1.5), G.degats(2, 1.5), G.degats(3, 1.5), G.degats(1, 0.67), G.degats(2, 0.67), G.degats(3, 0.67))
         == (2, 3, 5, 1, 1, 2), "les cœurs : ×1.5 arrondi, ×0.67 au moins 1")
verifier(G.type_du_jour(__import__("datetime").date(1970, 1, 1)) == "feu"
         and G.type_du_jour(__import__("datetime").date(1970, 1, 10)) == "feu", "le type du jour tourne sur les 9 types")

print("Une ancienne partie : le compagnon est le guide")
core.modifier(lambda s: s.pop("guide", None))
st = core.load()
core.migrate(st)
verifier(st["guide"]["id"] == "compagnon", "après migration, le guide est le compagnon")
verifier(st["guide"]["type_c"] == G.TYPES[sum(map(ord, "Pixel")) % 9], "le compagnon reçoit un type (d'après son nom)")
st2 = {"name": "Zoé", "branch": "Force"}
verifier(G.type_compagnon_initial(st2) == "feu", "un compagnon de forme Force est de type Feu")
r = sans(subprocess.run([sys.executable, str(RACINE / "pc"), "guide"], capture_output=True, text=True).stdout)
verifier("Ton guide" in r and "Pixel" in r, "tg guide montre le guide")
r = sans(subprocess.run([sys.executable, str(RACINE / "pc"), "types"], capture_output=True, text=True).stdout)
verifier("est fort contre" in r and "Ombre" in r, "tg types montre la table des types")

print("Changer de guide")
plante = donner("plante")
feu = donner("feu")
st = core.load()
core.migrate(st)
verifier(G.region_ouverte(st, "plante") and G.region_ouverte(st, "feu"), "les régions des types de l'équipe sont ouvertes")
r = sans(subprocess.run([sys.executable, str(RACINE / "pc"), "equipe", "guide", plante.lower()], capture_output=True,
                        text=True).stdout)
st = core.load()
verifier("🔄" in r and plante in r and G.actuel(st)[1] == plante, f"tg equipe guide {plante.lower()} : nouveau guide")
verifier(st["active"] == G.actuel(st)[0], "le guide est aussi la bestiole active")
verifier("Bâtisseur" in r, "le message dit son talent")
r = sans(subprocess.run([sys.executable, str(RACINE / "pc"), "guide", plante], capture_output=True, text=True).stdout)
verifier("déjà" in r, "même guide : « déjà ton guide »")
r = sans(subprocess.run([sys.executable, str(RACINE / "pc"), "guide", "licornix"], capture_output=True, text=True).stdout)
verifier("Je ne trouve pas" in r, "nom inconnu : message gentil")
with core.verrou():
    s = core.load()
    core.migrate(s)
    equipe.choisir(s, feu)
    core.save(s)
verifier(G.actuel(core.load())[1] == feu, "tg troupe <nom> met aussi la bestiole en tête (guide)")
r = sans(equipe.ecran_equipe(core.load()))
verifier("Guide" in r and "Feu" in r, "l'écran d'équipe montre le guide et les types")
core.modifier(lambda s: G.choisir(s, "pixel"))
verifier(G.actuel(core.load())[0] == "compagnon", "on peut rendre la place au compagnon")

print("Talents")
core.modifier(lambda s: G.choisir(s, plante))
core.modifier(lambda s: s["seen"].extend(["mkdir", "touch", "date"]))
xp0 = core.load()["xp"]
etape("date")
xp1 = core.load()["xp"]
etape("mkdir truc")
xp2 = core.load()["xp"]
verifier((xp2 - xp1) - (xp1 - xp0) == 1, "guide Plante : +1 XP sur mkdir (pas sur date)")
verifier(G.du_talent("plombier", "ls | wc -l") and G.du_talent("secrets", "ls -a") and G.du_talent("secrets", "cd .cachette")
         and G.du_talent("cuisinier", "./recette.sh") and not G.du_talent("secrets", "cd ..")
         and G.du_talent("detective", "cd x && grep a b"), "les commandes de chaque talent sont reconnues")
core.TERRAIN.mkdir(exist_ok=True)
r = sans(core.modifier(lambda s: s.__setitem__("_r", entrainement.commencer(s, "batisseur")))["_r"])
verifier("te souffle" in r, "exercice Bâtisseur avec un guide Plante : une astuce de plus")
xp_a = core.load()["xp"]
r = []
core.modifier(lambda s: r.extend(entrainement.reussir(s)))
gain = core.load()["xp"] - xp_a
verifier(any("Talent de" in x for x in r), "exercice réussi : +25 % d'XP (talent)")
base = gain - next(int(x.split("+")[1].split()[0]) for x in r if "Talent de" in x)
verifier(gain - base == max(1, -(-base // 4)), f"le bonus vaut 25 % arrondi au-dessus ({base} → +{gain - base})")
core.modifier(lambda s: G.choisir(s, feu))
r = sans(core.modifier(lambda s: s.__setitem__("_r", entrainement.commencer(s, "batisseur")))["_r"])
verifier("te souffle" not in r, "avec un autre guide : pas d'astuce de talent")
core.modifier(lambda s: s["entrainement"].__setitem__("cours", None))

print("Régions gardées")
for x in ("biome/glace", "biome/feu"):
    (core.TERRAIN / x).mkdir(parents=True, exist_ok=True)
st = etape("cd ~/terrain_terminagotchi/biome/glace", cwd=str(core.TERRAIN / "biome/glace"))
verifier("gardée" in sans((st.get("bubble") or [""])[0] + " ".join(b[0] for b in st.get("bulles", []))),
         "région Glace sans bestiole Glace : « gardée »")
core.modifier(lambda s: G.choisir(s, plante))
st = etape("mkdir parcelle_9", cwd=str(core.TERRAIN / "biome/feu"))
bul = sans((st.get("bubble") or [""])[0] + " ".join(b[0] for b in st.get("bulles", [])))
verifier("agrandir" in bul and f"tg guide {feu.lower()}" in bul, "agrandir la région Feu sans guide Feu : le dire, avec la commande")
verifier(G.peut_agrandir(core.modifier(lambda s: G.choisir(s, feu)), "feu"), "avec un guide Feu, on peut l'agrandir")

print("Combats à type")


class De:
    def __init__(self, x):
        self.x = x

    def random(self):
        return self.x


def combat_contre(ty_moi, ty_lui):
    moi = espece_de_type(ty_moi)["nom"]
    if not any(c["espece"] == moi for c in core.load()["captures"]):
        donner(ty_moi)
    lui = espece_de_type(ty_lui)

    def f(s):
        G.choisir(s, moi)
        ind = B.individu(lui, False, lui["zone"], "classique", qualite=0.5)
        s["dressage"] = {"espece": lui["nom"], "rarete": "légendaire", "variante": "classique", "ind": ind,
                         "taches": [], "faites": [], "mefiance": 100}
        combat.preparer(s)
        combat.coup(s, "date", rnd=De(0.0))
    return core.modifier(f)["dressage"]["combat"]


cb = combat_contre("eau", "feu")
verifier(cb["types"] == ["eau", "feu"] and cb["lui"][0] == cb["lui"][1] - 2, "Eau contre Feu : un coup normal fait 2 cœurs")
verifier(any("super efficace" in x for x in cb["journal"]), "« C'est super efficace ! »")
cb = combat_contre("feu", "eau")
verifier(cb["lui"][0] == cb["lui"][1] - 1 and any("pas très efficace" in x for x in cb["journal"]),
         "Feu contre Eau : au moins 1 cœur, « pas très efficace »")
cb = combat_contre("plante", "plante")
verifier(cb["lui"][0] == cb["lui"][1] - 1, "même type : ×1")
verifier(G.efficacite("machine", "ombre") == 1.0, "contre l'Ombre : ×1")
core.modifier(lambda s: s.__setitem__("dressage", None))

print("Épreuve du jour")
ty = G.type_du_jour()
fort = G.forts_contre(ty)[0]
nom_fort = donner(fort)
core.modifier(lambda s: G.choisir(s, nom_fort))
xp0 = core.load()["xp"]
core.modifier(lambda s: s.__setitem__("_b", G.apres_defi(s)))
verifier(core.load()["xp"] - xp0 >= G.BONUS_DEFI and core.load()["_b"], f"guide {fort} contre le type du jour ({ty}) : +5 XP")
faible = next(x for x in G.TYPES if x != "ombre" and G.efficacite(x, ty) <= 1)
nom_faible = donner(faible)
core.modifier(lambda s: G.choisir(s, nom_faible))
core.modifier(lambda s: s.__setitem__("_b", G.apres_defi(s)))
verifier(core.load()["_b"] is None, "un autre guide : pas de bonus (et pas de punition)")
r = []
core.modifier(lambda s: (core.defi_start(s), r.append(" ".join(b[0] for b in s.get("bulles", [])))))
verifier("Épreuve du jour" in sans(r[0]), "le défi éclair annonce le type du jour")
core.modifier(lambda s: s.__setitem__("defi", None))

print("Fatigue et envies")
core.modifier(lambda s: G.choisir(s, plante))
def regler(fat):
    def f(s):
        g = G.g_(s)
        g["fatigue"][g["id"]] = fat
        g["t"] = time.time()
        e = envies.e_(s)
        e["v"]["sommeil"] = e["v"]["jeu"] = 80.0
        e["t"] = time.time()
    core.modifier(f)
envies.soir = lambda heure=None: False
regler(0.0)
etape(*["date"] * 10)
s0 = envies.e_(core.load())["v"]["sommeil"]
f0 = G.fatigue(core.load())
regler(100.0)
etape(*["date"] * 10)
s1 = envies.e_(core.load())["v"]["sommeil"]
verifier(abs(f0 - 10 * G.FATIGUE_COMMANDE) < 0.01, "10 commandes : le guide se fatigue de 5")
verifier(s1 < s0 - 3, f"un guide très fatigué use le sommeil plus vite ({s0:.1f} → {s1:.1f})")
st = core.load()
verifier("bâille" in sans((st.get("bubble") or [""])[0] + " ".join(b[0] for b in st.get("bulles", []))),
         "fatigué : il le dit (et propose de changer de guide)")


def vieillir(sec):
    def f(s):
        g = G.g_(s)
        g["t"] -= sec
        g["cmd_t"] -= sec
    core.modifier(f)


core.modifier(lambda s: G.g_(s)["fatigue"].__setitem__(G.membres(s)[0][0], 80.0))
vieillir(3600)
st = core.modifier(lambda s: G.tick(s, []))
verifier(G.fatigue(st, "compagnon") <= 60.5, "sur le banc, on se repose (−20 par heure)")
f_g = G.fatigue(st)
vieillir(3600)
st = core.modifier(lambda s: G.tick(s, []))
verifier(G.fatigue(st) < f_g, "le guide aussi se repose quand on ne joue pas")
def loin(s):
    g = G.g_(s)
    for m in G.membres(s):
        g["depuis"][m[0]] = time.time() - 3 * 24 * 3600
    g["sortie_t"] = 0
    g["annonce"] = True
core.modifier(loin)
st = etape("date")
verifier("envie de sortir" in sans(G.ecran(st)) or "envie de sortir" in sans(equipe.ecran_equipe(st)),
         "pas guide depuis 2 jours : 💭 envie de sortir")
verifier("sortir se promener" in sans((st.get("bubble") or [""])[0] + " ".join(b[0] for b in st.get("bulles", []))),
         "et une bulle gentille le propose")
verifier("mort" not in json.dumps(st.get("guide")), "rien de grave : pas de mort, pas de punition")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
