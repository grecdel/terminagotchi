"""Partie scriptée (PC) pour les retours des simulations d'enfants de 7 ans (dans « La Maison endormie »).

    python3 pc/outils/test_retours_enfants.py          (crée son propre HOME temporaire)

De vraies commandes sont lancées avec bash et écrites dans ~/.bash_history, puis le jeu fait une
étape (app.etape), comme le compagnon du terminal :
  1. leçons (chapitres 1-2, puis la bibliothèque et la cave choisies librement) : « pome » au lieu de
     « pomme » → indice clair, la leçon attend la bonne commande ;
  2. terrain effacé (rm -rf) → bulle + commande à taper ; reconstruit → la leçon reprend au bon
     endroit (repas.txt remis) ; si l'enfant n'y arrive pas, le jeu reconstruit lui-même ;
  3. premier dressage : un monstre courant et commun, 2 épreuves simples, indices « presque »,
     tirage toujours vérifiable (graine, compteur) ; puis la difficulté monte avec les captures ;
  4. attirance : sur beaucoup d'apparitions, la famille attirée sort vraiment plus souvent ;
  5. mini-combat : gagné (peur −40, une épreuve en moins), puis perdu (KO, repos, pas de mort) ;
  6. il manque quelque chose après la commande (mkdir tout seul, cat qui attend le clavier…) → bulle
     avec la commande à taper ; et chaque exemple du lexique marche vraiment depuis le terrain.
"""
import collections
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_enfant_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import (app, bestiaire as B, combat, core, dressage, equipe, exemples, explo, histoire, langue,  # noqa: E402
                lecons, lexique, tirage)

HOME = Path.home()
T = core.TERRAIN
GRAINE = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"   # factice
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd, ou=None):
    """L'enfant tape une commande : elle s'exécute vraiment, part dans l'historique, le jeu avance."""
    subprocess.run(["bash", "-c", cmd], cwd=str(ou or HOME), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False)


def modifier(fn):
    return core.modifier(fn)


def texte(lignes):
    """Le texte tel que l'enfant le lit (sans couleurs, sans les backticks des commandes en vert)."""
    return langue.sans_marques(ANSI.sub("", "\n".join(lignes) if isinstance(lignes, list) else lignes))


def bulles(st):
    return langue.sans_marques(" | ".join([(st.get("bubble") or [""])[0]] + [b[0] for b in st.get("bulles", [])]))


def niveau(n):
    modifier(lambda s: s.__setitem__("xp", max(s["xp"], 10 * (n - 1) ** 2)))


# ====================================================================== mise en route
(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()
# pas de monstre au hasard pendant le test : ils sont appelés exprès (explo.spawn)
_tick = explo.tick
explo.tick = lambda st, sp, proba=0, jeu=0, lignes=(): _tick(st, sp, proba, 0, lignes)
modifier(lambda s: (s["config"].__setitem__("fenetre_dressage", False), s.__setitem__("explo", True),
                    tirage.ranger_graines(s, [{"id": f"{tirage.jour_local()}.abcdef123456", "valeur": GRAINE}])))
niveau(2)
for c in ("pwd", "ls", "cd ~"):
    tape(c)
for c in ("cd terrain_terminagotchi", "ls", "cd vestibule", "ls"):     # chapitre 1 : la vieille porte, l'œuf
    tape(c)
niveau(3)
for c in ("cd ..", "mkdir nid", "touch nid/lit.txt",                  # chapitre 2 : le nid
          "mkdir debarras", "rmdir debarras", "rm -r vieille_cabane"):  # et une pièce en trop
    tape(c, T)
st = core.load()
verifier("nid0" in st["histoire"]["faits"] and "Bâtisseur" in st["skills"], "chapitres 1-2 : terrain, œuf et nid construits")
verifier("debarras" in st["histoire"]["faits"], "une pièce en trop : démolie avec rmdir, la cabane broyée avec rm -r")


def lec(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"] if les else None), st["step"]


print("1. Leçons : un indice quand c'est presque ça")
niveau(4)
st = tape("echo pome > nid/repas.txt", T)
verifier(lec(st) == ("nid1", 0), "« pome » : la leçon attend encore la bonne commande")
verifier("pome" in (st.get("indice_lecon") or "") and "pomme" in st["indice_lecon"], f"indice : {st.get('indice_lecon')}")
ecran = texte(app.render(dict(st, dressage=None), 0, True))
verifier("💡 Presque" in ecran, "l'indice s'affiche sous la leçon")
if "💡 Presque" not in ecran:
    print(ecran)
st = tape("echo pomme > nid/repas.txt", T)
verifier(lec(st) == ("nid1", 1) and not st.get("indice_lecon"), "« pomme » : étape réussie, l'indice disparaît")
st = tape("cat nid/repas.txt", T)
verifier(histoire.fini(st, "nid"), "chapitre 2 fini : la maison est libre")
niveau(5)
for c in ("cd bibliotheque", 'find . -name "*abysses*"', "less etagere_c/coin_poussiereux/livre_des_abysses.txt"):
    st = tape(c, T / "bibliotheque" if c.startswith(("find", "less")) else T)
verifier(lec(st) == ("biblio1", 0), "la bibliothèque : le livre est retrouvé, on passe à la loupe")
st = tape("cd ..")
st = tape("grep pome nid/repas.txt", T)
verifier(lec(st) == ("biblio1", 0) and "« pome »" in (st.get("indice_lecon") or ""), "grep pome : indice, pas de silence")
st = tape("grep pomme nid/repas.txt", T)
verifier(lec(st) == ("biblio1", 1), "grep pomme : réussi")
core.modifier(lambda s: histoire.choisir(s, "cave"))                  # on change d'aile (l'étape est gardée)
for c in ("cd cave", "whoami", "sudo -h", "cd .."):
    st = tape(c, T)
st = tape("ls -l nid", T)
verifier(lec(st) == ("t3", 1), "la cave (droits) : on en est à chmod 444 nid/repas.txt")
st = tape("chmod 444 nid/repas.tx", T)
verifier("repas.tx »" in (st.get("indice_lecon") or ""), f"chmod 444 nid/repas.tx : {st.get('indice_lecon')}")

print("2. Terrain effacé")
st = tape("rm -rf ~/terrain_terminagotchi")
p = st.get("terrain_perdu") or {}
verifier(p.get("cmd") == "mkdir -p ~/terrain_terminagotchi/nid", f"détecté : la commande proposée est « {p.get('cmd')} »")
verifier("mkdir -p ~/terrain_terminagotchi/nid" in bulles(st), "une bulle claire donne la commande")
verifier("➜ mk" in texte(app.render(dict(st, dressage=None), 0, True)) and "~/terrain_terminagotchi/nid" in texte(app.render(dict(st, dressage=None), 0, True)),
         "le bandeau (avec la commande) reste sur l'écran principal")
verifier(not explo.debloque(st), "pas de monstre tant que le nid n'existe pas")
st = tape("mkdir -p ~/terrain_terminagotchi/nid")
verifier(not st.get("terrain_perdu"), "reconstruit : plus d'alerte")
verifier((T / "nid" / "repas.txt").is_file(), "repas.txt remis pour que la leçon continue")
verifier(lec(st) == ("t3", 1), "la leçon reprend au bon endroit (chmod 444)")
verifier((T / "cave").is_dir() and (T / "grenier").is_dir(), "les portes des ailes sont reposées")
st = tape("chmod 444 nid/repas.txt", T)
verifier(lec(st) == ("t3", 2), "chmod 444 : réussi après la reconstruction")
st = tape("rm -rf ~/terrain_terminagotchi")
for i in range(terrain_aide := 12):
    st = tape(["date", "whoami", "ls", "pwd"][i % 4])
verifier(not st.get("terrain_perdu") and (T / "nid" / "repas.txt").is_file(),
         f"l'enfant n'y arrive pas : reconstruit tout seul après {terrain_aide} commandes")
st = tape("echo poire >> nid/repas.txt", T)
verifier(histoire.fini(st, "cave"), "la cave est réveillée malgré deux effacements")
st = tape("cd ~/terrain_terminagotchi/grenier")
verifier(st["histoire"]["chap"] == "grenier", "entrer dans le grenier le choisit")
st = tape("ls -R", T / "grenier")
st = tape("mv fouillis/ours_en_peluche.txt ../nid/", T / "grenier")
verifier(lec(st) == ("t4", 0), "grenier (copie) : on commence (l'ours a été remis après l'effacement)")
st = tape("cp nid/repas.txt nid/secours.txt", T)
subprocess.run(["rm", "-rf", str(T / "nid" / "secours.txt")])
st = tape("ls", T)
verifier(st["step"] == 0 and "étape d'avant" in bulles(st), "secours.txt effacé avant le mv : on refait l'étape d'avant")
for c in ("cp nid/repas.txt nid/secours.txt", "mv nid/secours.txt reserve.txt", "rm reserve.txt"):
    st = tape(c, T)
verifier(histoire.fini(st, "grenier") and histoire.chapitre_courant(st) is None, "le grenier est réveillé")

print("3. Premier dressage facile")
st = modifier(explo.spawn)
d = st.get("dressage")
verifier(d is not None, "un monstre apparaît")
e = B.espece(d["espece"])
ind = d["ind"]
verifier(e["frequence"] == "souvent" and ind["rarete"] == "commune", f"premier monstre : {e['nom']} ({e['frequence']}, {ind['rarete']})")
verifier(len(d["taches"]) == 2 and d["taches"][0] == "Rencontre:examiner" and d["taches"][1] in dressage.SIMPLES,
         f"2 épreuves simples : {d['taches']}")
verifier(d["duree"] is None and "combat" not in d, "pas de chrono, pas de combat (troupe vide)")
champs = tirage.tirer(GRAINE, ind["n"], False, ind.get("attire"))[1]
verifier(champs.items() <= ind.items(), f"vérifiable : (graine, compteur {ind['n']}) refait exactement le même individu")
nom = dressage.nom_fichier(d["espece"])
st = tape(f"cat ~/terrain_terminagotchi/monstre_{nom[:-1]}.txt")
verifier("monstre_" + nom + ".txt" in (st["dressage"].get("indice") or ""), f"faute dans le nom : {st['dressage'].get('indice')}")
st = tape(f"cat ~/terrain_terminagotchi/monstre_{nom}.txt")
verifier(st["dressage"]["faites"] == ["Rencontre:examiner"], "fiche lue : 1re épreuve réussie")
_, ex = dressage.aide(d["taches"][1], d["espece"])
rep = dressage.contexte(st)["d"]
st = tape(ex.split("    ")[0], rep)
verifier(not st.get("dressage") and len(st["captures"]) == 1, f"2e épreuve ({ex}) : première bestiole dressée !")

print("   … puis la difficulté monte avec les captures")
moy = []
for n in range(0, 14):
    tailles = [len(dressage.choisir_epreuves(x, False, "rare", n)) for x in B.publiques()]
    moy.append(sum(tailles) / len(tailles))
verifier(all(a <= b + 1e-9 for a, b in zip(moy, moy[1:])), "épreuves par dressage : " + " → ".join(f"{x:.1f}" for x in moy))
niv = [max(dressage._par_id(dressage._fid(y))["niveau"] for y in dressage.choisir_epreuves(B.espece("Braisillon"), False, "épique", n)[2:])
       for n in (1, 4, 6, 9, 13)]
verifier(niv == sorted(niv) and niv[0] == 1 and niv[-1] == 3, f"niveau max des épreuves (1, 4, 6, 9, 13 captures) : {niv}")
for_ = [n for n in range(14) if any(f == "Code:compte" for f in (dressage._fid(y) for y in dressage.choisir_epreuves(
    B.espece("Gribouilleur") or B.publiques()[0], False, "rare", n)))]
verifier(not any(n < 8 for n in for_), "pas de boucle for avant 8 captures")

print("4. Attirance")
N = 1200
for fam in ("Démons", "Célestes"):
    cmd = B.familles()[fam]
    tape(cmd if cmd != "ping" else "ping -c 1 127.0.0.1")
    compte = collections.Counter()
    temoin = collections.Counter()

    def tirages(s, attirer):
        for i in range(N):
            if i % 150 == 0:
                s["compte"]["apparitions"] = {}
            if attirer:
                explo.attirer(s, [cmd])
            explo.spawn(s)
            v = s["sauvages"][-1]["ind"]                 # (une légendaire déjà vue aujourd'hui ne se dresse pas)
            (compte if attirer else temoin)[B.espece(v["espece"])["famille"]] += 1
            assert tirage.tirer(GRAINE, v["n"], False, v.get("attire"))[1].items() <= v.items()
            dressage.abandonner(s)
            s["sauvages"] = []
    modifier(lambda s: tirages(s, False))
    modifier(lambda s: tirages(s, True))
    a, b = 100 * temoin[fam] / N, 100 * compte[fam] / N
    verifier(b > 2 * a, f"{fam} ({cmd}) : {a:.1f} % sans attirance → {b:.1f} % avec ({N} apparitions vérifiables)")
st = core.load()
verifier(cmd in st["seen"], "la commande d'attirance fait partie des commandes goûtées (le serveur le vérifie)")
st = tape("chmod 600 /dev/null 2>/dev/null; true")
verifier(explo.attirance(st) == "Démons", "taper chmod attire les Démons")
verifier("Démons" in texte(explo.ecran_collection(st)), "la collection montre l'attirance du moment")

print("5. Mini-combat")


class Des:
    """Dés truqués pour le test : une suite de tirages qui revient en boucle."""
    def __init__(self, suite):
        self.suite, self.i = suite, 0

    def random(self):
        self.i += 1
        return self.suite[(self.i - 1) % len(self.suite)]


def nouveau_monstre(s):
    dressage.abandonner(s)
    s["sauvages"] = []
    explo.spawn(s)


st = modifier(nouveau_monstre)
d = st["dressage"]
cb = d.get("combat")
bete = st["captures"][0]
verifier(cb is not None and cb["id"] == bete["id"], f"{bete['espece']} (troupe) affronte {d['espece']}")
ecran = texte(dressage.lignes_ecran(st))
verifier("COMBAT" in ecran and "VS" in ecran and cb["special"][1:] in ecran and "attaque spéciale" in ecran
         and "observer" in ecran, "l'écran montre le combat et les 3 coups")
print("\n".join("     " + l for l in ecran.split("\n")[-12:]))
taches = list(d["taches"])
peur = d["mefiance"]
combat.random = Des([0.0])                 # tout touche
for _ in range(5):
    st = tape(cb["special"])
    if st["dressage"]["combat"]["fin"]:
        break
d = st["dressage"]
verifier(d["combat"]["fin"] == "gagne" and d["combat"]["tour"] <= 5, f"combat gagné en {d['combat']['tour']} tours")
verifier(d["mefiance"] == peur - combat.BAISSE_PEUR, f"la peur baisse : {peur} → {d['mefiance']}")
fam = [f for f in taches if not f.startswith("Rencontre:")]
verifier(len(d["taches"]) == len(taches) - (1 if len(fam) >= 2 else 0), f"épreuves : {len(taches)} → {len(d['taches'])}")
verifier(st.get("anim_troupe", {}).get("nom") == "victoire", "animation de victoire demandée")
verifier(d["lignes"] == [] and d["faites"] == [], "le dressage commence après le combat (les coups ne comptent pas)")

st = modifier(nouveau_monstre)
combat.random = Des([0.99, 0.0])            # tu rates, le monstre touche
for _ in range(5):
    st = tape("date")
    if st["dressage"]["combat"]["fin"]:
        break
cbp = st["dressage"]["combat"]
bete = next(c for c in st["captures"] if c["id"] == cbp["id"])
verifier(cbp["fin"] == "perdu" and cbp["moi"][0] == 0, f"combat perdu en {cbp['tour']} tours")
verifier(bete in st["captures"] and combat.repose(bete), "pas de mort : la bestiole est toujours là et se repose")
verifier(st.get("anim_troupe", {}).get("nom") == "ko", "animation « ko » demandée")
r = equipe.animation(bete, "ko")
verifier(r is not None and len(r[0]) > 1, f"l'animation ko existe pour {bete['espece']} ({len(r[0])} images)")
verifier("💤" in texte(equipe.ecran_equipe(st)), "la troupe montre qu'elle se repose")
st = modifier(nouveau_monstre)
verifier(not st["dressage"].get("combat") and "se repose" in bulles(st), "toute la troupe se repose : pas de combat")
combat.random = random

print("6. Il manque quelque chose après la commande (mkdir tout seul…)")


def tape_sans_lancer(cmd):
    """La commande part dans l'historique sans être lancée (cat tout seul attendrait le clavier sans fin)."""
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False)


modifier(lambda s: (s.__setitem__("bubble", None), s.__setitem__("bulles", [])))
st = tape_sans_lancer("mkdir")
verifier("Il manque le nom" in bulles(st) and "Essaie : mkdir " in bulles(st), f"mkdir seul → bulle : {bulles(st)}")
verifier(any("Essaie : mkdir " in langue.sans_marques(m) for m in st["log"][-3:]), "… et la même aide au-dessus de l'invite (journal)")
modifier(lambda s: (s.__setitem__("bubble", None), s.__setitem__("bulles", [])))
st = tape_sans_lancer("cat")
verifier("cat nid/repas.txt" in bulles(st) and "Ctrl+C" in bulles(st), f"cat seul → bulle : {bulles(st)}")
modifier(lambda s: (s.__setitem__("bubble", None), s.__setitem__("bulles", [])))
st = tape_sans_lancer("cp nid/repas.txt")
verifier("DEUX noms" in bulles(st), "cp avec un seul nom → il en faut deux")
modifier(lambda s: (s.__setitem__("bubble", None), s.__setitem__("bulles", [])))
st = tape_sans_lancer("mkdir cabane_test")
st = tape_sans_lancer("ls -l | grep repas")
verifier("Il manque" not in bulles(st) and "✍" not in bulles(st), "commande complète (ou avec un tuyau) → pas d'aide")
for cmd in ("mkdir", "touch", "cat", "cp", "mv", "rm", "rmdir", "grep", "chmod", "head", "tail", "wc", "find", "kill",
            "ping", "ssh", "curl", "nano", "less"):
    # (pas d'aide pour une commande absente de cet ordinateur : core.feed dit déjà qu'il ne la connaît pas)
    present = core.commande_existe(cmd)
    verifier(exemples.manque(cmd) == cmd and bool(exemples.aide(st, cmd)) == present,
             f"{cmd} seul : aide prévue" + ("" if present else " (absente ici : pas d'aide, « commande inconnue »)"))
# la leçon en cours demande cette commande : c'est elle qui est proposée
_lc = lecons.lecon_courante
lecons.lecon_courante = lambda s: ({"steps": [{"cmd": "mkdir nid"}]}, "")
verifier("Essaie : `mkdir nid`" in exemples.aide({"step": 0, "xp": 0}, "mkdir"), "pendant la leçon « mkdir nid » : Essaie : mkdir nid")
lecons.lecon_courante = _lc

# Les exemples du lexique marchent vraiment depuis le terrain de jeu (dans l'ordre du lexique)
lancees = []
for _titre, univers, cmds in lexique._entrees():
    for cmd, _i, _t in cmds:
        ex = exemples.lexique(cmd)
        if ex and univers == lexique.ICI and not cmd.startswith("tg"):
            lancees += ex.split(" · ")
for regle in exemples.REGLES.values():                 # les exemples des bulles qui ne sont pas dans le lexique PC
    if regle[1] not in lancees:
        lancees.append(regle[1])
lancees.append("echo coucou > mot.txt")
HORS_LIGNE = ("ping", "curl", "nslookup", "ssh", "kill", "nano")   # réseau, NUMÉRO à remplacer, éditeur plein écran
(T / "nid" / "repas.txt").chmod(0o644)                 # la leçon des droits l'a mis sous cadenas
for ex in lancees:
    if ex.split()[0] in HORS_LIGNE:
        continue
    r = subprocess.run(["bash", "-c", ex], cwd=str(T), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=30)
    verifier(r.returncode == 0, f"exemple « {ex} » : marche depuis le terrain"
             + ("" if r.returncode == 0 else f" ✖ {r.stdout}{r.stderr}".strip()))
    verifier(exemples.manque(ex) is None, f"   … et n'est pas pris pour une commande incomplète")
for cmd, ex in (("mkdir", "mkdir cabane"), ("cat", "cat nid/repas.txt"), ("cp", "cp nid/repas.txt copie.txt"),
                ("grep", "grep pomme nid/repas.txt"), ("chmod", "chmod 444 nid/repas.txt"),
                ("head", "head -n 3 nid/repas.txt"), ("find", 'find . -name "*.txt"'), ("kill", "kill NUMÉRO"),
                ("ping", "ping -c 3 example.com")):
    verifier(exemples.lexique(cmd) == ex, f"lexique : {cmd} → exemple : {ex}")
ecran = texte(lexique.lignes(core.load()))
verifier("↳ exemple : mkdir cabane" in ecran and "↳ exemple : cat nid/repas.txt" in ecran,
         "le lexique affiche « ↳ exemple : mkdir cabane »")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
