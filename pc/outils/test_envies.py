"""Test des 6 envies (PC) : seuils, satisfaction de chacune, poussière seulement dans le terrain, sleep.

    python3 pc/outils/test_envies.py          (crée son propre HOME temporaire)

Le jeu avance comme avec le compagnon du terminal (app.etape) ; le temps qui passe est simulé en reculant les
dates rangées dans la sauvegarde. Les mêmes règles sont testées sur Android par tests/jvm/Envies.kt.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_envies_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, envies as E, langue, lexique, registre  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def etape(*lignes, cwd=None):
    return app.etape(spontane=False, defis=False, extra=list(lignes), cwd=cwd)


def modifier(fn):
    return core.modifier(fn)


def regler(**v):
    """Fixe des envies (et remet les rappels à zéro) sans attendre."""
    def f(s):
        e = E.e_(s)
        for k, x in v.items():
            if k == "faim":
                s["hunger"] = x
            else:
                e["v"][k] = x
        e["t"] = time.time()
        e["moment"] = None
    return modifier(f)


def bulles(st):
    return langue.sans_marques(" | ".join([(st.get("bubble") or [""])[0]] + [b[0] for b in st.get("bulles", [])]))


def fichiers_hors_terrain():
    """Les fichiers .tmp ou dossiers .cache apparus dans HOME en dehors du terrain."""
    out = []
    for p in HOME.rglob("*"):
        if T in p.parents or p == T:
            continue
        if p.name == ".cache" or p.suffix == ".tmp":
            out.append(p)
    return out


langue.definir("fr")
E.soir = lambda heure=None: False              # le jour (le soir est testé à part)
(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()

print("Une nouvelle partie")
st = core.load()
core.migrate(st)
v = E.valeurs(st)
verifier(v["jeu"] == 70 and v["curiosite"] == 70 and v["explorer"] == 70 and v["sommeil"] == 90,
         f"valeurs de départ (jeu, curiosité, exploration 70, sommeil 90) : {v}")
verifier(v["proprete"] == 100 and not T.exists(), "pas de terrain : propreté 100, rien n'est créé")

print("Migration d'une ancienne sauvegarde")
vieille = json.loads(core.SAVE_FILE.read_text(encoding="utf-8"))
vieille.pop("envies", None)
vieille["total"], vieille["xp"] = 120, 300
core.SAVE_FILE.write_text(json.dumps(vieille), encoding="utf-8")
st = etape()
v = E.valeurs(st)
verifier(all(abs(v[k] - E.MIGRATION) < 0.01 for k in ("jeu", "curiosite", "explorer", "sommeil")),
         f"les anciennes parties reçoivent des valeurs moyennes ({E.MIGRATION:g})")
verifier(st["xp"] >= 300 and st["total"] == 120 and st["name"] == "Pixel", "rien d'autre n'est cassé (XP, total, nom)")

print("Usure par commande et avec le temps")
regler(jeu=80, curiosite=80, explorer=80, sommeil=80, faim=90)
st = etape("date", "whoami", "pwd", "date")
e = st["envies"]["v"]
verifier(abs(e["jeu"] - (80 - 4 * 0.7)) < 0.01 and abs(e["sommeil"] - (80 - 4 * 0.4)) < 0.01,
         f"4 commandes : jeu −{4 * 0.7:.1f}, sommeil −{4 * 0.4:.1f} ({e['jeu']:.1f}, {e['sommeil']:.1f})")
regler(jeu=30, curiosite=80, explorer=80, sommeil=20)
modifier(lambda s: s["envies"].update(t=time.time() - 3 * 3600, cmd_t=time.time() - 3 * 3600))
st = etape()
e = st["envies"]["v"]
verifier(abs(e["jeu"] - E.PLANCHER_TEMPS) < 0.01, f"le temps seul ne descend pas sous {E.PLANCHER_TEMPS:g} (jeu {e['jeu']:.1f})")
verifier(abs(e["curiosite"] - (80 - 3 * 1.5)) < 0.05, f"curiosité −1.5/h ({e['curiosite']:.1f})")
attendu = 20 + E.REPOS_HEURE * (3 - 1 / 6)
verifier(abs(e["sommeil"] - attendu) < 0.1, f"sans jouer elle se repose toute seule (+25/h après 10 min : {e['sommeil']:.1f})")
regler(faim=50)
modifier(lambda s: s.update(last_tick=time.time() - 7200))
st = etape()
verifier(abs(st["hunger"] - (50 - 7200 / 720)) < 0.1, f"la faim descend 2 fois moins vite : −10 en 2 h ({st['hunger']:.1f})")

print("Envie du moment et rappels espacés")
regler(faim=90, jeu=20, curiosite=80, explorer=80, sommeil=80)
st = etape()
m = E.moment(st)
verifier(m and m["e"] == "jeu" and m["cmd"] == "tg defi", f"la plus basse sous {E.SEUIL:g} : jeu → tg defi ({m})")
regler(faim=20, jeu=10, curiosite=80, explorer=80, sommeil=80)
st = etape()
verifier(E.moment(st)["e"] == "faim", "la faim urgente (< 30) passe toujours devant")
regler(faim=90, jeu=80, curiosite=80, explorer=80, sommeil=80)
st = etape()
verifier(E.moment(st) is None, "tout va bien : pas d'envie du moment")
vues = set()
for _ in range(40):
    regler(faim=90, jeu=30, curiosite=35, explorer=80, sommeil=80)
    vues.add(E.moment(core.load())["e"])
verifier(vues == {"jeu", "curiosite"}, f"un peu de hasard entre les envies proches (à moins de {E.PROCHES:g}) : {sorted(vues)}")
regler(faim=90, jeu=10, curiosite=80, explorer=80, sommeil=80)
modifier(lambda s: s["envies"].update(rappel_t=0, rappel_n=0))
st = None
for i in range(11):
    st = etape("date")
verifier(not E.rappel_recent(st), "pas de rappel avant 12 commandes")
st = etape("date")
r = E.rappel_recent(st)
verifier(bool(r) and "`tg defi`" in r, f"au bout de 12 commandes : la bulle propose la commande, en vert ({r})")
t_rappel = st["envies"]["rappel_t"]
for i in range(14):
    st = etape("date")
verifier(st["envies"]["rappel_t"] == t_rappel, "12 commandes de plus, mais pas 5 minutes : pas de nouveau rappel")
modifier(lambda s: s["envies"].update(rappel_t=time.time() - 5 * 60 - 1))
st = etape("date")
verifier(st["envies"]["rappel_t"] > t_rappel, "après 5 minutes et 12 commandes : un nouveau rappel")
phrases = {k: langue.liste("env.dit." + k) for k in E.ENVIES}
verifier(all(len(p) >= 5 and all("`{cmd}`" in x for x in p) for p in phrases.values()),
         "au moins 5 phrases par envie, chacune avec la commande en vert")
for code in langue.LANGUES:
    d = json.loads((RACINE / "pc/tg/langues" / f"{code}.json").read_text(encoding="utf-8"))
    if not all(len(d["env.dit." + k]) >= 5 for k in E.ENVIES):
        verifier(False, f"{code} : 5 phrases par envie")
        break
else:
    verifier(True, "les 14 langues ont leurs phrases d'envies")

print("Jeu 🎮")
regler(jeu=20)
modifier(lambda s: s["envies"].update(moment={"e": "jeu", "cmd": "tg defi", "t": time.time()}))
xp0 = core.load()["xp"]
subprocess.run([sys.executable, str(RACINE / "pc"), "defi"], capture_output=True)
st = core.load()
if not st.get("defi"):
    st = modifier(core.defi_start)
st = etape(st["defi"]["cmd"])
verifier(st["envies"]["v"]["jeu"] >= 20 + E.GAINS["defi"] - 1, f"défi éclair réussi : jeu +{E.GAINS['defi']:g}")
verifier(st["xp"] >= xp0 + 10 + E.XP_BAS + E.XP_MOMENT, "récompense : l'XP du défi + l'XP de l'envie du moment")
merci = langue.liste("env.merci.jeu")
verifier(st["envies"]["moment"] is None and any(m in bulles(st) for m in merci), "l'envie du moment satisfaite : un merci dans la bulle")
from tg import combat  # noqa: E402
regler(jeu=10)
st = modifier(lambda s: E.plaisir(s, "jeu", "combat"))
verifier(st["envies"]["v"]["jeu"] == 10 + E.GAINS["combat"], "un combat (gagné ou perdu) satisfait le jeu")

print("Curiosité 📚")
regler(curiosite=20)
st = etape("tg explique cp")
verifier(st["envies"]["v"]["curiosite"] >= 20 + E.GAINS["explique"] - 1, "tg explique cp : curiosité +20")
regler(curiosite=20)
st = etape("ls --help")
verifier(st["envies"]["v"]["curiosite"] >= 39, "ls --help : curiosité +20")
regler(curiosite=20)
st = etape("man ls")
verifier(st["envies"]["v"]["curiosite"] >= 39, "man ls : curiosité +20")
regler(curiosite=20)
st = etape("uname")
verifier(st["envies"]["v"]["curiosite"] >= 20 + E.GAINS["nouvelle"] - 1, "une commande jamais goûtée : curiosité +10")
regler(curiosite=20)
modifier(lambda s: s.__setitem__("step", s.get("step", 0) + 1))
st = etape()
verifier(st["envies"]["v"]["curiosite"] >= 20 + E.GAINS["lecon"] - 1, "une étape de leçon : curiosité +15")

print("Propreté 🧹 : la poussière")
verifier(not fichiers_hors_terrain() and not E.poussieres(), "pas encore de poussière, et aucun fichier hors du terrain")
(T / "vestibule").mkdir(parents=True, exist_ok=True)
(T / "nid").mkdir(exist_ok=True)
modifier(lambda s: s["envies"].update(poussiere_t=time.time() - 3 * E.POUSSIERE_INTERVALLE - 5))
st = etape()
ps = E.poussieres()
verifier(len(ps) == 3 and all(p.parent == T / ".cache" for p in ps), f"3 × 45 min : 3 fichiers dans {T.name}/.cache ({[p.name for p in ps]})")
verifier(abs(E.proprete() - (100 - 3 * 12.5)) < 0.01, f"la jauge vient des vrais fichiers : {E.proprete():g}")
verifier("Poussière" in ps[0].read_text(encoding="utf-8"), "chaque fichier dit ce qu'il est")
verifier(".cache" in bulles(st) and "tg envies" in bulles(st), "la première poussière : une bulle parle du placard caché et de tg envies")
(T / ".cache" / "poussiere_2.tmp").unlink()
st = etape()
verifier(abs(E.proprete() - 75) < 0.01, "un fichier effacé à la main : la jauge remonte (75)")
modifier(lambda s: s["envies"].update(poussiere_t=time.time() - 20 * E.POUSSIERE_INTERVALLE))
st = etape()
verifier(len(E.poussieres()) == E.POUSSIERE_MAX and E.proprete() == 0, f"au plus {E.POUSSIERE_MAX} fichiers : propreté 0")
verifier(E.humeur_cle(st) in ("humeur.triste", "humeur.grognon", "humeur.repu", "humeur.creux"),
         "propreté à zéro : pas de mort, juste une humeur")
regler(faim=90, jeu=80, curiosite=80, explorer=80, sommeil=80)
st = etape(cwd=str(HOME))
m = E.moment(st)
verifier(m["e"] == "proprete" and m["cmd"] == f"cd ~/{T.name}",
         f"depuis la maison de l'enfant, on propose d'abord d'aller dans le terrain ({m['cmd']})")
st = etape(f"cd ~/{T.name}", cwd=str(T))
m = E.moment(st)
verifier(m["cmd"] in ("ls -a", "ls .cache", "rm .cache/*.tmp"), f"dans le terrain : {m['cmd']}")
subprocess.run(["bash", "-c", "ls -a; ls .cache; find . -name '*.tmp'"], cwd=str(T), capture_output=True)
xp0 = st["xp"]
subprocess.run(["bash", "-c", "rm .cache/*.tmp"], cwd=str(T))
st = etape("rm .cache/*.tmp", cwd=str(T))
verifier(E.proprete() == 100 and (T / ".cache").is_dir(), "rm .cache/*.tmp : tout propre, le placard reste")
verifier(st["xp"] > xp0 and any(m in bulles(st) for m in langue.liste("env.merci.proprete")), "satisfaite : XP et merci")
subprocess.run(["bash", "-c", "rm -r .cache"], cwd=str(T))
st = etape("rm -r .cache", cwd=str(T))
verifier((T / ".cache").is_dir() and not E.poussieres(), "rm -r .cache : le jeu recrée le placard vide")
verifier(not fichiers_hors_terrain(), "rien n'a été créé hors du terrain (pas de ~/.cache, pas de .tmp ailleurs)")
# le placard remplacé par un lien vers l'extérieur : le jeu n'écrit rien dehors
dehors = Path(tempfile.mkdtemp(prefix="tg_dehors_"))
subprocess.run(["rm", "-r", str(T / ".cache")])
os.symlink(dehors, T / ".cache")
modifier(lambda s: s["envies"].update(poussiere_t=time.time() - 2 * E.POUSSIERE_INTERVALLE))
etape()
verifier(not any(dehors.iterdir()), "un placard qui pointe ailleurs (lien) : aucun fichier écrit dehors")
(T / ".cache").unlink()
etape()

print("Exploration 🧭")
regler(explorer=20)
st = etape(f"cd ~/{T.name}/vestibule", cwd=str(T / "vestibule"))
verifier(st["envies"]["v"]["explorer"] >= 20 + E.GAINS["lieu"] - 1 - 1, f"une pièce jamais visitée : exploration +15 ({st['envies']['v']['explorer']:.1f})")
regler(explorer=20)
st = etape("ls -a", cwd=str(T / "vestibule"))
verifier(st["envies"]["v"]["explorer"] >= 20 + E.GAINS["regarde"] - 1, "ls -a dans la maison du jeu : exploration +8")
regler(explorer=20)
st = etape("cd ~", "ls -a", cwd=str(HOME))
verifier(st["envies"]["v"]["explorer"] < 21, "ls -a hors de la maison du jeu : rien")
regler(explorer=20)
modifier(lambda s: s.setdefault("quetes", {}).setdefault("finies", []).append("q02"))
st = etape()
verifier(st["envies"]["v"]["explorer"] >= 20 + E.GAINS["secret"] - 1, "une pièce secrète trouvée (quête cachette) : exploration +40")

print("Sommeil 😴")
regler(sommeil=20, faim=90, jeu=80, curiosite=80, explorer=80)
modifier(lambda s: s["envies"].update(moment={"e": "sommeil", "cmd": "sleep 10", "t": time.time()}))
t0 = time.time()
subprocess.run(["bash", "-c", "sleep 1"])
verifier(time.time() - t0 >= 1, "sleep : une vraie pause du shell")
st = etape("sleep 10")
verifier(abs(st["envies"]["v"]["sommeil"] - (20 - 0.4 + 50)) < 0.01, f"sleep 10 : sommeil +50 ({st['envies']['v']['sommeil']:.1f})")
verifier(any("Sieste de 10 s" in l for l in st["log"]), "une ligne de journal pour la sieste")
anims = []
_animer = core.animer
core.animer = lambda s, nom: (anims.append(nom), _animer(s, nom))
regler(sommeil=20)
st = etape("sleep 10")
core.animer = _animer
verifier("dort" in anims and st["anim"][0] in ("dort", "evolution", "victoire"), f"la sieste demande l'animation « dort » ({anims}, {st['anim'][0]})")
regler(sommeil=20)
st = etape("sleep 100")
verifier(st["envies"]["v"]["sommeil"] <= 20 + E.SIESTE_MAX, "une longue sieste rapporte au plus +50")
regler(sommeil=20)
st = etape("sleep 2")
verifier(abs(st["envies"]["v"]["sommeil"] - (20 - 0.4 + 10)) < 0.01, "sleep 2 : +10")
texte = json.dumps(json.loads((RACINE / "pc/tg/langues/fr.json").read_text(encoding="utf-8")), ensure_ascii=False)
toutes = " ".join(" ".join(langue.liste("env.dit." + k)) for k in E.ENVIES) + " ".join(langue.liste("env.soir"))
verifier(not re.search(r"suspend|shutdown|poweroff|hibernate|systemctl|veille|halt\b", toutes, re.I),
         "aucune phrase ne propose de mettre en veille ou d'éteindre le vrai ordinateur")
verifier(all(E.suggestion(core.load(), k).split()[0] not in ("shutdown", "systemctl", "poweroff", "halt", "pm-suspend")
             for k in E.ENVIES for _ in range(10)), "aucune suggestion n'éteint ni ne met en veille l'appareil")
E.soir = lambda heure=None: True
regler(sommeil=60)
modifier(lambda s: s["envies"].update(soir_t=0))
st = etape("date")
verifier(abs(st["envies"]["v"]["sommeil"] - (60 - E.SOMMEIL_SOIR)) < 0.01, "le soir, elle fatigue plus vite (1.2 par commande)")
verifier("bâille" in bulles(st) or "Il fait nuit" in bulles(st), f"le soir, elle bâille et propose d'arrêter ({bulles(st)[:70]})")
st = etape("date")
verifier(st["envies"]["soir_t"] > time.time() - 60 and bulles(st).count("bâille") <= 1, "un seul bâillement par 40 minutes")
E.soir = lambda heure=None: False

print("Humeur : les envies combinées, sans punition")
regler(faim=90, jeu=90, curiosite=90, explorer=90, sommeil=90)
st = etape()
verifier(E.humeur_cle(st) == "humeur.joyeux", "tout est haut : joyeux")
regler(faim=90, jeu=0)
verifier(E.humeur_cle(core.load()) == "humeur.triste", "une envie à zéro : triste")
regler(faim=90, jeu=0, curiosite=0)
verifier(E.humeur_cle(core.load()) == "humeur.grognon", "deux envies à zéro : grognon")
regler(faim=20, jeu=0, curiosite=0)
verifier(E.humeur_cle(core.load()) == "humeur.affame", "la faim reste la plus importante")
regler(faim=0, jeu=0, curiosite=0, explorer=0, sommeil=0)
st = etape("date")
verifier(st["name"] == "Pixel" and st["hunger"] > 0, "tout à zéro : elle mange, elle est toujours là")

print("Affichage et aide")
ecran = "\n".join(app.render(core.load(), 0, False).split("\n")[:8])
verifier(all(i in ecran for i in E.ICONES.values()), "la fenêtre principale montre les 6 jauges en petit")
r = subprocess.run([sys.executable, str(RACINE / "pc"), "envies"], capture_output=True, text=True)
sortie = langue.sans_marques(r.stdout)
verifier(all(E.nom(k) in sortie for k in E.ENVIES) and "rm .cache/*.tmp" in sortie and "sleep 10" in sortie
         and "Pour les grands" in sortie, "tg envies : l'état détaillé, et comment satisfaire chacune")
r = subprocess.run([sys.executable, str(RACINE / "pc"), "aide"], capture_output=True, text=True)
verifier("tg envies" in langue.sans_marques(r.stdout), "tg aide mentionne tg envies")
verifier("tg envies" in langue.sans_marques("\n".join(lexique.lignes(core.load()))), "le lexique mentionne tg envies")
verifier(any("envies" in e["cmd"] for e in registre.chercher("envie")), "la recherche trouve tg envies")
verifier(not any("envies" in k for k in json.loads(json.dumps(core.load().get("compte", {})))),
         "rien des envies dans le compte synchronisé (anti-triche inchangé)")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
