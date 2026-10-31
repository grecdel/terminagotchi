"""Tests de la satiété (pc/tg/satiete.py) et des suites du rapport v3.

    python3 pc/outils/test_satiete.py            vérifie (code de sortie 1 en cas d'échec)
    python3 pc/outils/test_satiete.py --ecrire   réécrit d'abord donnees/satiete/vecteurs.json (lu aussi par
                                                 tests/jvm/Satiete.kt : mêmes calculs en Kotlin)

1. Les vecteurs partagés avec Kotlin (états, aliments, heures d'éveil, XP, série, éclat, et un scénario de 9 jours).
2. Les 7 points validés le 29 octobre, un par un, avec le vrai jeu (core.feed, app.etape).
3. Les suites du rapport v3 : commande réaffichée après une erreur, jauge étiquetée, « Où sommes-nous ? », Racine,
   XP des commandes « pas encore », noms des lieux d'habitat dans les 14 langues.
La simulation de 14 jours (plusieurs rythmes de jeu) est dans pc/outils/sim_satiete.py.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_satiete_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["TZ"] = "UTC"                       # les vecteurs sont en heure UTC (le test Kotlin fait pareil)
time.tzset()
os.environ.pop("HISTFILE", None)
ICI = Path(__file__).resolve().parent
DEPOT = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))

from tg import aura as A  # noqa: E402
from tg import core, histoire, intro, langue, maison  # noqa: E402
from tg import satiete as S  # noqa: E402

VECTEURS = DEPOT / "donnees" / "satiete" / "vecteurs.json"
ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


def ts(j, h, mn=0):
    """Un instant du lundi 2 novembre 2026 (+ j jours) à h:mn, en UTC."""
    return 1793577600 + j * 86400 + h * 3600 + mn * 60


# ---------------------------------------------------------------- 1. vecteurs communs
CMDS = ["ls", "pwd", "cd", "mkdir", "echo", "cat", "grep", "ping", "lampe", "chmod", "whoami", "date", "df",
        "termux-toast", "caresse", "danse", "LS", "inconnue", "edite", "git", "sleep"]
SCENARIO = [   # (jour, heure, minute, op, commande, nouvelle, ratee, repetee)
    (0, 17, 0, "tick", "", 0, 0, 0), (0, 17, 1, "repas", "pwd", 1, 0, 0), (0, 17, 2, "repas", "ls", 1, 0, 0),
    (0, 17, 3, "repas", "ls", 0, 0, 1), (0, 17, 4, "repas", "mkdir", 1, 0, 0), (0, 17, 5, "repas", "cat", 1, 0, 0),
    (0, 17, 6, "repas", "ping", 1, 0, 0), (0, 17, 7, "repas", "chmod", 1, 0, 0), (0, 17, 8, "repas", "date", 1, 0, 0),
    (0, 17, 9, "repas", "cd", 0, 1, 0), (1, 8, 0, "tick", "", 0, 0, 0), (1, 18, 0, "repas", "pwd", 0, 0, 0),
    (1, 18, 1, "repas", "ls", 0, 0, 0), (1, 18, 2, "repas", "date", 0, 0, 0), (2, 18, 0, "repas", "whoami", 1, 0, 0),
    (2, 18, 1, "repas", "pwd", 0, 0, 0), (2, 18, 2, "repas", "echo", 1, 0, 0), (4, 18, 0, "tick", "", 0, 0, 0),
    (4, 18, 1, "repas", "grep", 1, 0, 0), (4, 18, 2, "repas", "ls", 0, 0, 0), (4, 18, 3, "repas", "df", 1, 0, 0),
    (8, 12, 0, "tick", "", 0, 0, 0), (8, 12, 1, "repas", "pwd", 0, 0, 0), (8, 12, 2, "repas", "pwd", 0, 0, 1),
    (8, 12, 3, "repas", "ls", 0, 0, 0), (8, 12, 4, "repas", "cat", 0, 0, 0), (8, 12, 5, "repas", "git", 1, 0, 0),
]


def jouer_scenario():
    """Le scénario sur un état neuf : après chaque pas, [faim arrondie, état, jours, série, assiette, xp]."""
    st = core.new_state("Pixel")
    core.migrate(st)
    st["intro"] = {"etat": "fini"}
    s = S.s_(st)
    st["hunger"], st["last_tick"], s["repas_t"] = 70.0, ts(0, 16), ts(0, 16)
    out = []
    for j, h, mn, op, cmd, nouv, rat, rep in SCENARIO:
        now = ts(j, h, mn)
        if op == "tick":
            S.tick(st, now)
        else:
            S.repas(st, cmd, nouvelle=bool(nouv), ratee=bool(rat), repetee=bool(rep), now=now)
        out.append([round(st["hunger"], 3), S.etat_de(st["hunger"], s["veille"]), s["jours"], s["serie"],
                    len(set(s["assiette"])), st["xp"]])
    return out


def calculer():
    v = {}
    v["etat"] = [[f, ve, S.etat_de(f, ve)] for f in (0, 10, 14.9, 15, 30, 39.9, 40, 60, 79.9, 80, 100) for ve in (False, True)]
    v["famille"] = [[c, S.famille(c)] for c in CMDS]
    paires = [(ts(0, 6), ts(0, 8)), (ts(0, 20), ts(1, 8)), (ts(0, 7), ts(0, 21)), (ts(0, 22), ts(1, 6)),
              (ts(0, 17, 20), ts(1, 17)), (ts(0, 12), ts(3, 12)), (ts(0, 12), ts(7, 12)), (ts(1, 9, 30), ts(1, 9, 31)),
              (ts(2, 21), ts(2, 23)), (ts(0, 0), ts(0, 0))]
    v["eveil"] = [[a, b, S.secondes_eveil(a, b)] for a, b in paires]
    v["taux"] = [[g, e, l, S.taux(g, e, l)] for g in (False, True) for e in (0, 37, 100, 250) for l in (0, 29, 30)]
    v["repas"] = [[n, r, p, k, a, S.valeur_repas(n, r, p, k, a)] for n in (False, True) for r in (False, True)
                  for p in (False, True) for k in (0, 1, 2, 4, 9) for a in (False, True)]
    v["xp"] = [[g, e, r, *S.xp_ajuste(g, e, r)] for g in (0, 1, 2, 3, 7, 12, 20) for e in S.XP_PCT for r in (0, 40, 80, 99)]
    v["serie"] = [[s, S.serie_manquee(s), S.palier_serie(s)] for s in (0, 1, 2, 3, 6, 7, 13, 14, 29, 30, 45)]
    v["minuit"] = [[a, S.minuit_apres(a)] for a in (ts(0, 0), ts(0, 17, 20), ts(3, 23, 59), ts(58, 12))]
    v["aura"] = [[f, m, ve, A.niveau_satiete(f, m, ve)] for f in (0, 14, 15, 39, 40, 79, 80, 100) for m in (0, 49, 50, 100)
                 for ve in (False, True)]
    v["scenario"] = {"pas": [list(x) for x in SCENARIO], "attendu": jouer_scenario()}
    return v


print("1. Les vecteurs partagés avec Kotlin (donnees/satiete/vecteurs.json)")
v = calculer()
if "--ecrire" in sys.argv or not VECTEURS.exists():
    VECTEURS.parent.mkdir(parents=True, exist_ok=True)
    VECTEURS.write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"  (vecteurs écrits : {VECTEURS})")
lu = json.loads(VECTEURS.read_text(encoding="utf-8"))
for k in v:
    verifier(json.loads(json.dumps(v[k])) == lu[k], f"vecteurs « {k} » : le calcul Python n'a pas changé")
sc = v["scenario"]["attendu"]
verifier(sc[8][2] == 1 and sc[13][2] == 2 and sc[16][2] == 3, f"scénario : jours soignés 1, 2, 3 ({[x[2] for x in sc]})")
verifier(sc[17][2] == 4, f"scénario : un jour sans jouer, mais fini en forme, compte aussi ({sc[17][2]})")
verifier(sc[21][1] in ("affamee", "veille") and sc[21][3] < max(x[3] for x in sc[:21]),
         f"scénario : des jours finis affamée font perdre des crans, pas toute la série ({[x[3] for x in sc]})")

# ---------------------------------------------------------------- 2. les 7 points validés
print("2. Rythme : seulement de 7 h à 21 h, 3 fois plus lent, mode vacances")
verifier(S.secondes_eveil(ts(0, 21), ts(1, 7)) == 0, "la nuit (21 h - 7 h), la faim ne baisse pas")
verifier(S.secondes_eveil(ts(0, 0), ts(1, 0)) == 14 * 3600, "une journée entière : 14 h d'éveil")
par_jour = 14 * 3600 / S.taux()
verifier(abs(par_jour - 23.33) < 0.01, f"−{par_jour:.1f} points par jour (avant : −120)")
verifier(1.5 <= (80 - 40) / par_jour <= 2.5, f"de rassasiée à affamée : {(80 - 40) / par_jour:.1f} jours (~2)")
verifier(S.taux(gardien=True) == 2 * S.taux() and S.taux(endurance=100) == 2 * S.taux(), "Gardien ×2, Endurance jusqu'à ×2")
st = core.new_state("Pixel")
core.migrate(st)
s = S.s_(st)
st["hunger"], st["last_tick"] = 80.0, ts(0, 9)
S.vacances(st, True)
S.tick(st, ts(5, 9))
verifier(st["hunger"] == 80.0 and s["vacances"], "en vacances : 5 jours sans bouger la faim")
S.vacances(st, False)
S.tick(st, ts(6, 9))
verifier(abs(st["hunger"] - (80 - par_jour)) < 0.01, f"après les vacances, elle repart doucement ({st['hunger']:.1f})")

print("2. Quatre états, jamais de mort, la veille et le repas complet")
verifier([S.etat_de(x) for x in (95, 60, 20, 5)] == ["rassasiee", "forme", "affamee", "veille"], "95/60/20/5 → les 4 états")
st["hunger"], st["last_tick"] = 20.0, ts(7, 8)
S.tick(st, ts(8, 8))
verifier(s["veille"] and S.etat(st) == "veille", f"sous 15 : en veille ({st['hunger']:.1f}), jamais morte")
S.repas(st, "pwd", now=ts(8, 9))
S.repas(st, "pwd", now=ts(8, 9))
verifier(s["veille"], "deux fois la même commande ne la réveille pas")
S.repas(st, "ls", now=ts(8, 9))
S.repas(st, "date", now=ts(8, 9))
verifier(not s["veille"] and st["hunger"] >= S.REVEIL_FAIM, f"3 commandes différentes : réveillée, en forme ({st['hunger']:.0f})")

print("3. Ce que rapporte une créature rassasiée")
verifier(S.xp_ajuste(10, "rassasiee") == (12, 0), "+20 % d'XP (10 → 12)")
r, tot = 0, 0
for _ in range(5):
    g, r = S.xp_ajuste(1, "rassasiee", r)
    tot += g
verifier(tot == 6, f"les restes ne se perdent pas : 5 × 1 XP → {tot}")
verifier(S.xp_ajuste(10, "affamee") == (8, 0) and S.xp_ajuste(10, "veille") == (6, 0), "affamée −20 %, en veille −40 %")
st = core.new_state("Pixel")
core.migrate(st)
st["intro"] = {"etat": "fini"}
st["hunger"] = 90.0
st["xp"] = 150
S.s_(st)["jours"] = 1
core.add_xp(st, 30)
verifier(st["xp"] == 159 and S.s_(st)["reserve"] == 21, f"pas assez de jours soignés : elle attend au niveau 4 (xp {st['xp']}, "
         f"réserve {S.s_(st)['reserve']})")
verifier(S.niveau_appris(st) == 5 and S.plafond(st) == 4, "l'XP de côté compte pour s'ouvrir, la leçon ne demande pas plus")
c = histoire.PAR_CHAP["grenier"]
verifier(histoire.niveau_requis(st, c, 0) <= core.level(st["xp"]), "une leçon n'est jamais bloquée par l'évolution")
S.s_(st)["jours"] = 3
S.liberer(st)
verifier(st["xp"] == 180 and core.stage(core.level(st["xp"])) == 2, f"3 jours soignés : elle grandit, rien n'est perdu ({st['xp']})")
verifier(A.niveau_satiete(90, 80) == 3 and A.niveau_satiete(60, 80) == 2 and A.niveau_satiete(20, 80) == 1
         and A.niveau_satiete(50, 80, True) == 0, "l'aura : 3 rassasiée, 2 en forme, 1 affamée, 0 en veille")

print("4. Ce que coûte la faim (sans jamais bloquer l'apprentissage)")
from tg import dressage, explo, guide  # noqa: E402
st["hunger"] = 30.0
S.s_(st)["veille"] = False
verifier(S.affamee(st), "30 : affamée")
appels = []
vrai_spawn = explo.spawn
explo.spawn = lambda s_: appels.append(1)
st["explo"] = True
explo.debloque = lambda s_: True
explo.histoire_en_pleine_etape = lambda s_: False       # (pas d'étape en cours : on mesure la faim seule)
import random as _r  # noqa: E402
_r.seed(1)
for _ in range(50):
    explo.tick(st, True, jeu=10)
verifier(not appels, "affamée : aucun monstre (pas de dressage)")
st["hunger"] = 90.0
for _ in range(50):
    explo.tick(st, True, jeu=10)
verifier(len(appels) > 0, f"rassasiée : les monstres reviennent ({len(appels)} sur 50)")
explo.spawn = vrai_spawn
st["hunger"] = 30.0
verifier(guide.apres_defi(st) is None, "affamée : pas de bonus de l'épreuve du jour")
gain = S.gagner_xp(st, 20, lecon=True)
verifier(gain == 20, "une leçon ne perd jamais d'XP, même affamée")

print("5. Nourrir intelligemment : aliments, nouveau goût, rendements décroissants, assiette")
verifier(S.famille("ls") == "reperer" and S.famille("mkdir") == "batir" and S.famille("grep") == "lire"
         and S.famille("ping") == "brancher" and S.famille("chmod") == "proteger" and S.famille("date") == "observer",
         "6 familles : se repérer, bâtir, lire et chercher, brancher, protéger, observer")


def repas_de(cmds, repetees=False):
    t = core.new_state("Pixel")
    core.migrate(t)
    t["hunger"] = 20.0
    for i, cmd in enumerate(cmds):
        S.repas(t, cmd, repetee=repetees and i > 0, now=ts(10, 10, i))
    return t["hunger"] - 20


ls10 = repas_de(["ls"] * 10, repetees=True)
varie = repas_de(["ls", "mkdir", "cat", "ping", "chmod"])
verifier(ls10 < 10 and varie >= 20, f"`ls` dix fois de suite : +{ls10:.1f} ; un repas varié de 5 : +{varie:.1f}")
verifier(S.valeur_repas(True, False, False, 0) > S.valeur_repas(False, False, False, 0) > S.valeur_repas(False, True, False, 0),
         "nouveau goût > commande connue > commande ratée")
t = core.new_state("Pixel")
core.migrate(t)
t["intro"] = {"etat": "fini"}
for i, cmd in enumerate(["pwd", "touch", "head", "curl", "id", "uptime"]):
    S.repas(t, cmd, now=ts(10, 10, i))
verifier(S.s_(t)["complete"] and "Assiette complète" in str(t.get("bubble")) + str(t.get("bulles")), "les 6 familles : assiette complète")

print("6. Série de soins : un jour manqué retire un cran")
verifier(S.serie_manquee(5) == 4 and S.serie_manquee(0) == 0, "un jour fini affamée : 5 → 4 (jamais tout à zéro d'un coup)")
t = core.new_state("Pixel")
core.migrate(t)
t["intro"] = {"etat": "fini"}
st_ = S.s_(t)
t["hunger"], t["last_tick"], st_["repas_t"] = 100.0, ts(0, 18), ts(0, 18)
for i, cmd in enumerate(["pwd", "ls", "date"]):
    S.repas(t, cmd, now=ts(0, 18, i))
S.tick(t, ts(2, 18))
verifier(st_["serie"] == 2 and st_["jours"] == 2, f"joué lundi, rien mardi (fini en forme) : mardi compte aussi ({st_['serie']})")
S.vacances(t, True)
S.tick(t, ts(9, 18))
verifier(st_["serie"] == 2, f"une semaine de vacances : ni gagné ni perdu ({st_['serie']})")
S.vacances(t, False)
t["hunger"] = 30.0
S.tick(t, ts(10, 18))
verifier(st_["serie"] == 1, f"un jour fini affamée : un cran de moins, pas tout ({st_['serie']})")
verifier(S.palier_serie(3) == 1 and S.palier_serie(30) == 4, "médailles à 3, 7, 14 et 30 jours")

print("7. Longue absence et migration")
t = core.new_state("Pixel")
core.migrate(t)
S.s_(t)["repas_t"] = ts(0, 12)
t["hunger"], S.s_(t)["veille"] = 0.0, True
verifier(S.absente(t, ts(30, 12)), "30 jours sans repas : elle se repose dans son biome")
S.repas(t, "ls", now=ts(30, 12))
verifier(not S.s_(t)["veille"] and t["hunger"] >= S.RETOUR_FAIM, "elle revient en forme, rien n'est perdu")
vieille = {"name": "Vieux", "xp": 400, "hunger": 0.0, "total": 300, "stats": {"Intelligence": 0, "Agilité": 0, "Force": 0,
           "Endurance": 0}, "seen": ["ls"], "log": [], "offsets": {}, "born": time.time() - 9 * 86400,
           "last_tick": time.time() - 5 * 86400}
core.migrate(vieille)
verifier(vieille["xp"] == 400 and vieille["hunger"] >= 40 and S.s_(vieille)["jours"] == S.MIGRATION_JOURS,
         f"une ancienne partie passe sans perte (xp 400, faim {vieille['hunger']:.0f}, {S.s_(vieille)['jours']} jours offerts)")
core.tick(vieille)
verifier(vieille["hunger"] >= 40, "… et la vieille date de la faim ne la fait pas tomber tout de suite")

# ---------------------------------------------------------------- 3. suites du rapport v3
print("8. Suites du rapport v3")
from tg import app, compagnon  # noqa: E402
import builtins  # noqa: E402
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
core.modifier(lambda x: (x.update(hunger=50.0), intro.i_(x).update(etat="fini")))
st = core.load()
core.migrate(st)
lig = compagnon.ligne(st)
verifier("🍎" in lig, "la jauge de faim a son étiquette 🍎 (plus de confusion avec le % d'XP)")
st["hunger"] = 5.0
st["xp"] = 50                                      # (éclose : l'œuf n'a pas de visage)
S.s_(st)["veille"] = True
verifier("zᶻ" in compagnon.visage(st), "en veille : yeux mi-clos dans l'invite")
# après une erreur, la commande de l'étape est réaffichée
st["hunger"], S.s_(st)["veille"] = 60.0, False
les, _ = histoire.lecon_courante(st)
verifier(les and core.level(st["xp"]) >= les["niveau"], f"une leçon en cours ({les and les['id']})")
if les:
    st["term_etape"] = f"{les['id']}:{st['step']}"
    core.DERNIER.update(ligne="lss", statut=127)
    st["terminal"] = ["« lss » n'est pas une commande… tu voulais dire « ls » ?"]
    out = "\n".join(compagnon.annonces(st))
    verifier("➜" in out and langue.t("comp.rappel", cmd="").split("{")[0].strip()[:8] in out,
             "après une erreur, la commande attendue est réaffichée")
    core.DERNIER.update(ligne="ls", statut=0)
    out = "\n".join(compagnon.annonces(st))
    verifier("➜" not in out, "sans erreur, pas de répétition")
avant = st["xp"]
st["debloc"] = {"mode": "progressif", "ouverts": [], "file": []}
intro.d_(st)
st["xp"] = avant
core.feed(st, "tg aura")
verifier(st["xp"] == avant, "`tg aura` « pas encore » : pas d'XP")
verifier("pwd" not in langue.t("intro.ici", chemin="/home/x").split("`pwd`")[1][:20] or "montre" in langue.t("intro.ici", chemin="/x"),
         "« Où sommes-nous ? » ne prétend plus que `pwd` a montré le camp")
txt = langue.t("hist.racine.4.dit", chemin_absolu="un chemin qui part de la Racine")
verifier(txt.count("part de la Racine") == 1, "la phrase sur la Racine ne se répète plus")
zones = [z for z in json.loads((DEPOT / "pc/tg/bestiaire.json").read_text(encoding="utf-8"))["habitats"]]
for code in langue.LANGUES:
    manque = [z for z in zones if langue.brut("carte.piece." + z, code) is None]
    verifier(not manque, f"{code} : les {len(zones)} lieux d'habitat ont un nom ({manque[:3]})")
langue.definir("fr") if hasattr(langue, "definir") else None
verifier(maison.nom_piece("abyssal") == "Abysses" and maison.nom_piece("mecanique") == "Atelier des engrenages",
         "abyssal → Abysses, mecanique → Atelier des engrenages")
verifier(explo.lieu("mecanique/repaire") .startswith("Atelier des engrenages"), "la fiche du monstre : le vrai nom du lieu")

print("9. La simulation de 14 jours (pc/outils/sim_satiete.py : tous les jours, un jour sur deux, une semaine d'absence)")
import subprocess  # noqa: E402
r = subprocess.run([sys.executable, str(ICI / "sim_satiete.py")], capture_output=True, text=True, timeout=3000,
                   env={k: v for k, v in os.environ.items() if k not in ("TZ",)})
verifier(r.returncode == 0, "simulation de 14 jours : " + (r.stdout.strip().splitlines() or ["?"])[-1])
if r.returncode:
    print(r.stdout[-3000:], r.stderr[-2000:])
print(f"\n{ok} réussis, {ko} échoués   (HOME={os.environ['HOME']})")
sys.exit(1 if ko else 0)
