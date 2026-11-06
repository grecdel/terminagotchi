"""Tests du thème « créature » (pc/tg/creature.py ; maquettes validées le 3 novembre).

    python3 pc/outils/test_creature.py            vérifie (code de sortie 1 en cas d'échec)
    python3 pc/outils/test_creature.py --ecrire   réécrit d'abord donnees/creature/vecteurs.json (lu aussi par
                                                  tests/jvm/Creature.kt : mêmes calculs en Kotlin)

1. Les vecteurs partagés avec Kotlin (humeurs, goûts, fêtes, devinettes, phases de l'évolution, espèces).
2. Avec le vrai jeu (core.feed, app.boucle_jeu) : plat préféré et goût secret (double faim, pas d'XP en plus),
   humeurs du moment (curieux, fier, câlin, enjoué, surpris, bavard, rêveur) qui passent devant triste/grognon,
   album des stades, moment d'évolution, éclosiversaire (à la visite suivante, une seule fois), envie mystère
   (après le chapitre 1, 2 par jour, 3 indices, « plus tard », la même joie sans XP).
3. L'espace de travail : le modèle et le dessin (humeur, glyphe, fête, envie, promenade, évolution, album) sans planter,
   et le réglage « rester sur place ».
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_creature_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["TZ"] = "UTC"                       # les vecteurs sont en heure UTC (le test Kotlin fait pareil)
time.tzset()
os.environ.pop("HISTFILE", None)
ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))

from tg import bestiaire as B  # noqa: E402
from tg import core, envies, guide, histoire, langue  # noqa: E402
from tg import creature as CR  # noqa: E402

VECTEURS = DEPOT / "donnees" / "creature" / "vecteurs.json"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


def ts(j, h=12, mn=0):
    """Un instant du lundi 2 novembre 2026 (+ j jours) à h:mn, en UTC."""
    return 1793577600 + j * 86400 + h * 3600 + mn * 60


# ---------------------------------------------------------------- 1. vecteurs communs
LIGNES = ["ls -a", "ls -la", "dir -Force", "ls", "ls -l", "pwd", "pwd ", "Get-Location", "whoami", "date", "Get-Date",
          "mkdir nid", "mkdir", "cat repas.txt", "cat", "type a.txt", "grep pomme f", "cat f | grep a", "cp a b",
          "echo coucou", "echo", "cd ~", "cd", "cd ~/", "cd nid", "ls -R", "tree", "lsblk"]


def calculer():
    v = {}
    evts = [[], ["curieux"], ["fier", "curieux"], ["enjoue", "reveur"], ["calin", "bavard", "enjoue"], ["fete", "gourmand"],
            ["surpris", "curieux", "calin"], ["reveur"], ["inconnu"]]
    v["humeur"] = [[e, CR.choisir_humeur(set(e))] for e in evts]
    v["active"] = [[h, t0, now, CR.humeur_active({"h": h, "t": t0} if h else None, now)]
                   for h in (None, "curieux", "fete", "triste") for t0, now in ((100, 100), (100, 279), (100, 280),
                                                                                (100, 699), (100, 700), (100, 99))]
    v["variete"] = [[d, CR.variete(d)] for d in (["ls"], ["ls", "pwd", "cd", "cat"], ["ls", "pwd", "ls", "cat"],
                                                 ["a", "ls", "pwd", "cd", "cat"], ["ls", "pwd", "cd", "cat", "cat"])]
    v["calin"] = [[d, n, CR.pause_calin(d, n)] for d, n in ((0, 5000), (1000, 2799), (1000, 2800), (1000, 99999))]
    v["aliment"] = [[ty, CR.aliment(ty)] for ty in guide.TYPES + ("rien",)]
    v["secret"] = [[g, p, CR.gout_secret(g, p)] for g in (0, 1, 5, 11, 12, 987654321) for p in (None, "date", "ls")]
    v["mois"] = [[a, m, j, n, list(CR.ajouter_mois(a, m, j, n))] for a, m, j in ((2026, 1, 31), (2026, 10, 3), (2027, 12, 31),
                                                                                (2028, 1, 29), (2026, 8, 31))
                 for n in (1, 2, 3, 6, 12, 13, 25)]
    ecl = ts(0, 18)
    v["fete"] = [[ecl, now, f, CR.fete_due(ecl, now, f)] for now in (ts(0), ts(29), ts(30), ts(31), ts(45), ts(59),
                                                                       ts(61), ts(90), ts(200), ts(365), ts(800))
                 for f in ([], [1], [1, 2], [1, 2, 3, 6])] + [[None, ts(40), [], CR.fete_due(None, ts(40), [])]]
    v["eligibles"] = [[s, w, CR.eligibles(s, w)] for s in ([], ["ls"], ["ls", "pwd", "grep"], ["dir", "type", "cd"],
                                                           ["ls", "pwd", "cd", "cat", "echo", "cp", "mkdir", "date",
                                                            "whoami", "grep"]) for w in (False, True)]
    v["proposer"] = [[c, n, a, d, m, CR.peut_proposer(c, n, a, d, m)] for c in (False, True) for n in (0, 1, 2)
                     for a in (False, True) for d in (14, 15) for m in (False, True)]
    v["devinette"] = [[e, n, d, CR.choisir_devinette(e, n, d)] for e in ([], ["ls"], ["ls", "pwd", "cd_maison"])
                      for n in (0, 1, 7, 20368) for d in (None, "ls", "pwd")]
    v["trouve"] = [[i, l, CR.trouve(i, l)] for i in [d["id"] for d in CR.donnees()["devinettes"]] for l in LIGNES]
    v["phase"] = [[x, list(CR.phase_evolution(x)), CR.peut_passer(x)] for x in
                  (0, 0.5, 1.74, 1.75, 2.0, 3.0, 3.74, 3.75, 4.0, 4.24, 4.25, 4.4, 4.65, 6, 30)]
    v["migration"] = [[s, i, CR.pages_migration(s, i)] for s in (CR.donnees()["album_stades_compagnon"],
                                                                 CR.donnees()["album_stades_equipe"]) for i in (0, 1, 2, 4)]
    v["jour"] = [[x, CR.numero_jour(x), list(CR.date_locale(x))] for x in (0, ts(0), ts(0, 23, 59), ts(1, 0), ts(365))]
    v["especes"] = [[e["id"], e.get("attiree_par"), guide.type_de(e), CR.aliment(guide.type_de(e))] for e in B.especes()]
    return v


print("1. Les vecteurs partagés avec Kotlin (donnees/creature/vecteurs.json)")
v = calculer()
if "--ecrire" in sys.argv or not VECTEURS.exists():
    VECTEURS.parent.mkdir(parents=True, exist_ok=True)
    VECTEURS.write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"  (vecteurs écrits : {VECTEURS})")
lu = json.loads(VECTEURS.read_text(encoding="utf-8"))
for k in v:
    verifier(json.loads(json.dumps(v[k])) == lu.get(k), f"vecteurs « {k} » : le calcul Python n'a pas changé")
verifier(CR.choisir_humeur({"calin", "fier"}) == "calin" and CR.choisir_humeur({"fete", "gourmand"}) == "fete"
         and CR.choisir_humeur({"curieux", "bavard"}) == "bavard",
         "priorité : la fête, le retour, le plat préféré, la leçon réussie… (le plus précis avant « curieux »)")
verifier(CR.fete_due(ts(0), ts(30), []) == [1, False] and CR.fete_due(ts(0), ts(45), []) == [1, True]
         and CR.fete_due(ts(0), ts(45), [1]) is None, "1 mois : le jour même, ou en retard à la visite suivante, une fois")
verifier(CR.fete_due(ts(0), ts(200), []) == [6, True], "longue absence : on fête la plus récente (6 mois), pas toutes")
verifier(all(x[1] for x in v["especes"]) and all(x[3] for x in v["especes"]),
         f"chaque espèce ({len(v['especes'])}) a un plat préféré et un aliment préféré")
verifier(not CR.eligibles(["ls", "grep"], True).count("grep"), "Windows : pas de devinette sans équivalent (grep)")
cmp_ = json.loads((DEPOT / "pc/tg/creature.json").read_text(encoding="utf-8")) == \
    json.loads((DEPOT / "app/src/main/assets/creature.json").read_text(encoding="utf-8"))
verifier(cmp_, "creature.json : la même copie sur PC et sur Android")

# ---------------------------------------------------------------- 2. avec le vrai jeu
print("2. Avec le vrai jeu")
from tg import app  # noqa: E402

langue.definir("fr")


def partie(espece="glandouille"):
    st = core.new_state("Noisette")
    core.migrate(st)
    st["intro"] = {"etat": "fini"}
    st["espece_compagnon"] = espece
    st["xp"] = 40                                    # niveau 3 : un bébé éclos
    st["seen"] = ["pwd", "ls", "cd"]
    CR.c_(st)["graine"] = 9                          # son goût secret : « head » (pas une commande de ces tests)
    return st


st = partie()
c = CR.c_(st)
verifier(CR.stade_compagnon(st) == "bebe" and c["album"].get("bebe", {}).get("avant"),
         "une créature déjà éclose : son stade passé est « avant l'album »")
plat = CR.plat(st)
verifier(plat == B.espece("glandouille")["attiree_par"], f"le plat préféré vient du bestiaire (attiree_par = {plat})")
st["hunger"] = 30.0
st["derniers"] = []
xp0 = st["xp"]
core.feed(st, plat, 0)
h1 = st["hunger"]
st2 = partie()
st2["hunger"] = 30.0
st2["espece_compagnon"] = "braisillon"            # le même repas, sans être son plat préféré
autre = next(x for x in ("ls", "pwd", "cd") if x != B.espece("braisillon")["attiree_par"])
core.feed(st2, plat if plat != B.espece("braisillon")["attiree_par"] else autre, 0)
verifier(h1 - 30.0 > st2["hunger"] - 30.0 + 0.5, f"le plat préféré nourrit deux fois plus ({h1 - 30:.0f} contre {st2['hunger'] - 30:.0f})")
verifier("♥" in st["log"][-1], f"le journal le dit : « {st['log'][-1][6:]} »")
xp_plat = st["xp"] - xp0
st3 = partie("braisillon")
xp3 = st3["xp"]
core.feed(st3, "ls" if B.espece("braisillon")["attiree_par"] != "ls" else "pwd", 0)
verifier(xp_plat <= st3["xp"] - xp3, f"pas d'XP en plus pour le plat préféré ({xp_plat} ≤ {st3['xp'] - xp3})")
core.feed(st, plat, 0)
verifier("♥" not in st["log"][-1], "la même commande de suite : l'anti-répétition reste (pas de bonus)")
app.boucle_jeu(st, [], spontane=False, defis=False)
s = CR.secret(st)
verifier(s and s != plat, f"un goût secret pour chaque créature ({s}), jamais son plat préféré")
st["hunger"] = 30.0
core.feed(st, s, 0)
verifier(c["secret"] and any("goût secret" in x for x in st.get("terminal", [])), "le goût secret trouvé : dit dans le terminal")

# humeurs du moment (app.boucle_jeu : core.feed puis creature.tick)
st = partie()
c = CR.c_(st)
app.boucle_jeu(st, ["uptime"], spontane=False, defis=False)
verifier(CR.humeur(st) == "curieux", f"une commande jamais goûtée : curieux ({CR.humeur(st)})")
verifier(envies.humeur_cle(st) == "humeur.curieux", "l'humeur du moment passe devant l'humeur habituelle")
envies.e_(st)["v"].update(jeu=0.0, curiosite=0.0)
verifier(envies.humeur_cle(st) == "humeur.curieux", "… même devant « grognon » (humeur positive prioritaire)")
c["humeur"]["t"] -= 200
verifier(CR.humeur(st) is None and envies.humeur_cle(st) == "humeur.grognon", "au bout de 3 minutes, l'humeur habituelle revient")
st["hunger"] = 5.0
c["humeur"] = {"h": "fier", "t": time.time()}
verifier(envies.humeur_cle(st) in ("humeur.affame", "sat.etat.veille"), "jamais devant « affamé » ou la veille (la santé)")
st = partie()
st["seen"] += ["hostname", "uname", "id", "df", "uptime", "tg", "sleep"]
c = CR.c_(st)
c["derniere_t"] = time.time() - 3600
app.boucle_jeu(st, ["hostname"], spontane=False, defis=False)
verifier(CR.humeur(st) == "calin", f"on revient après une pause : câlin ({CR.humeur(st)})")
for l in ("uname", "id", "df", "uptime"):
    app.boucle_jeu(st, [l], spontane=False, defis=False)
verifier(CR.humeur(st) == "enjoue", f"des commandes toutes différentes : enjoué ({CR.humeur(st)})")
app.boucle_jeu(st, ["tg explique ls"], spontane=False, defis=False)
verifier(CR.humeur(st) == "bavard", f"tg explique : bavard ({CR.humeur(st)})")
app.boucle_jeu(st, ["sleep 1"], spontane=False, defis=False)
verifier(CR.humeur(st) == "reveur", f"sleep : rêveur ({CR.humeur(st)})")
verifier(all(langue.t(f"humeur.{h}") != f"humeur.{h}" for h in CR.donnees()["humeurs"]),
         "chaque humeur a son nom (14 langues : verifier_langues)")

# 16, 84 : album et évolution
st = partie()
st["xp"] = 155
from tg import satiete  # noqa: E402
satiete.s_(st)["jours"] = 99                        # assez de jours soignés pour grandir (satiete.retenir)
c = CR.c_(st)
c["album"] = {}
CR.c_(st)
core.add_xp(st, 10)
c = CR.c_(st)
verifier(CR.stade_compagnon(st) == "ado" and c["album"].get("ado", {}).get("t"), "grandir : une page datée dans l'album")
verifier(c["evolution"] and c["evolution"]["de"] == "bebe" and c["evolution"]["vers"] == "ado",
         "le moment d'évolution est demandé (de bébé à ado)")
sortie = CR.album_lignes(st)
verifier(any("Ado" in x for x in sortie) and any("bientôt" in x for x in sortie), "tg album : les stades, « bientôt » ensuite")
verifier(any("avant l'album" in x for x in sortie), "le bébé d'avant l'album est noté « avant l'album »")
st["captures"] = [{"id": "x", "espece": "Gouttelin", "nom": "Plic", "stade": "bebe", "xp": 0}]
from tg import equipe  # noqa: E402
equipe.gagner(st, st["captures"][0], 200)
al = CR.album_lignes(st, "plic")
verifier(len(al) == 7 and "bientôt" in al[-1], "l'album d'une bestiole de l'équipe : ses 5 stades")

# 17 : l'éclosiversaire
st = partie()
c = CR.c_(st)
c["eclosion"] = time.time() - 31 * 86400
app.boucle_jeu(st, ["pwd"], spontane=False, defis=False)
verifier(c["fetes"] == [1] and CR.fete_active(st) and CR.humeur(st) == "fete", "1 mois : la fête (confettis, « en fête »)")
verifier(any("éclosiversaire" in x for x in st.get("terminal", [])), "« ★ Joyeux éclosiversaire » dans le terminal")
verifier(c["pages"] and c["pages"][-1]["m"] == 1, "une page « 1 mois » dans l'album")
app.boucle_jeu(st, ["ls"], spontane=False, defis=False)
verifier(c["fetes"] == [1] and len(c["pages"]) == 1, "pas deux fois la même fête")

# 18 : l'envie mystère
st = partie()
c = CR.c_(st)
st["seen"] = ["pwd", "ls", "cd", "whoami", "date", "mkdir", "cat"]
for _ in range(20):
    app.boucle_jeu(st, ["pwd"], spontane=False, defis=False)
verifier(CR.envie(st) is None, "avant la fin du chapitre 1 : pas d'envie mystère")
histoire.h_(st)["ailes"].append("reveil")
envies.e_(st)["moment"] = None
for _ in range(16):
    envies.e_(st)["moment"] = None
    app.boucle_jeu(st, ["pwd"] if not CR.envie(st) or CR.envie(st)["id"] != "pwd" else ["uptime"],
                   spontane=False, defis=False)
e = CR.envie(st)
verifier(e is not None and e["id"] in CR.eligibles(st["seen"]), f"après le chapitre 1 et 15 commandes : une envie mystère ({e and e['id']})")
xp0 = st["xp"]
r1 = CR.indice(st)
r2 = CR.indice(st)
r3 = CR.indice(st)
r4 = CR.indice(st)
verifier("1 sur 3" in r1 and "3 sur 3" in r3 and "3 sur 3" in r4, "3 indices au plus")
dv = next(d for d in CR.donnees()["devinettes"] if d["id"] == e["id"])
verifier(dv["cmd"] in r3, f"le dernier donne la réponse ({r3})")
ligne = {"ls_a": "ls -a", "ls_l": "ls -l", "cd_maison": "cd ~", "mkdir": "mkdir x", "cat": "cat a.txt",
         "grep": "grep a b", "cp": "cp a b", "echo": "echo a"}.get(e["id"], dv["cmd"])
app.boucle_jeu(st, [ligne], spontane=False, defis=False)
verifier(CR.envie(st) is None and c["gouts"] == 1, "trouvée : un goût de plus dans l'album")
dits = [st["bubble"][0]] if st.get("bubble") else []
dits += [x[0] for x in st.get("bulles", [])]
verifier(any("trouvé" in x for x in dits), "« Tu as trouvé ! » dans la bulle (même joie avec ou sans indice)")
verifier(st["xp"] - xp0 <= 7, f"pas d'XP en plus pour l'envie (seulement le repas : +{st['xp'] - xp0})")
c["depuis"] = 99
envies.e_(st)["moment"] = None
app.boucle_jeu(st, ["whoami"], spontane=False, defis=False)
verifier(CR.envie(st) is not None, "une deuxième envie le même jour")
verifier("plus tard" in CR.indice(st, ["plus-tard"]).lower() and CR.envie(st) is None, "« plus tard » la range")
c["depuis"] = 99
app.boucle_jeu(st, ["whoami"], spontane=False, defis=False)
verifier(CR.envie(st) is None, "au plus 2 par jour")
verifier("pas d'envie" in CR.indice(st), "tg indice sans envie : une phrase gentille")
verifier(CR.gouts_lignes(st) and any("plat préféré" in x for x in CR.gouts_lignes(st)), "tg gouts : ce qu'elle aime")

# son() : le moteur de sons n'existe peut-être pas encore
verifier(CR.son("evolution", st) in (True, False), "son(« evolution ») : par le moteur de sons, sans planter")

# ---------------------------------------------------------------- 3. l'espace de travail
print("3. L'espace de travail (modèle et dessin, sans fenêtre)")
from tg import espace as ES  # noqa: E402
from tg import espace_scene as SC  # noqa: E402

st = partie()
st["xp"] = 60
core.save(st)


class FauxEspace(ES.Espace):
    def jeu(self):
        self.state = core.load()
        self.regl = dict(self.regl)
        self.c.regl = dict(self.regl, sur_place=self._sur_place())
        self._album()
        self._creature()


ctl = FauxEspace(lambda **k: core.load())
verifier(not ctl.c.regl.get("sur_place"), "par défaut, elle se promène dans la fenêtre en direct")
m = ctl.modele()
verifier(m.get("promenade") is not None, "le modèle : la promenade et le sol de son biome")
c = CR.c_(ctl.state)
c["humeur"] = {"h": "surpris", "t": time.time()}
c["fete"] = {"m": 1, "t": time.time()}
c["envie"] = {"id": "ls_a", "k": 1, "t": time.time()}
m = ctl.modele()
verifier(m["etat_nom"] == langue.t("humeur.surpris") and m.get("glyphe") == "exclam" and m.get("fete") and m.get("envie"),
         "humeur du moment, son glyphe « ! », la fête, l'envie mystère")
L, Z, _ = SC.scene(m, 1.0)
verifier(len(L) > 50, "le dessin de l'espace avec la fête et l'envie")
ctl.evo = {"t0": ctl.t - 0.5, "de": "bebe", "vers": "bebe"}
for tt in (0.5, 2.5, 4.0, 5.0):
    ctl.evo["t0"] = ctl.t - tt
    L, Z, _ = SC.scene(ctl.modele(), tt)
verifier(True, "le moment d'évolution se dessine à chaque phase")
ctl.evo["t0"] = ctl.t - 1.0
ctl.passer_evolution()
verifier(ctl.evo is not None, "on ne peut pas passer avant 2 secondes")
ctl.evo["t0"] = ctl.t - 2.5
ctl.passer_evolution()
verifier(ctl.evo is None, "après 2 secondes, Entrée (ou un clic) passe le moment")
ctl.onglet = "album"
m = ctl.modele()
verifier(m.get("album_pages") and len(m["album_pages"]["pages"]) == 3 and "album" in (m.get("onglets") or SC.ONGLETS),
         "l'onglet « Album » du panneau du moment : 3 stades")
L, Z, _ = SC.scene(m, 1.0)
verifier(any(z[4] == "album:bebe" for z in Z), "un clic sur un stade le fait saluer")
ctl.clic_options("opt:sur_place")
verifier(ctl.c.regl.get("sur_place") and core.load()["config"].get("direct_sur_place"), "le réglage « rester sur place »")
ctl.clic_options("opt:sur_place")

print(f"\n{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
