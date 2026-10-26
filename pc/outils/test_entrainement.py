"""Test de la salle d'entraînement (PC) : tirage commun, chaque exercice réussi pour de vrai, badges, titres, synchro.

    python3 pc/outils/test_entrainement.py          (crée son propre HOME temporaire)

Chaque exercice est fait avec les vraies commandes (bash) dans ~/terrain_terminagotchi/salle_entrainement, puis le
jeu avance comme avec le compagnon du terminal (app.etape). Les mêmes règles sont testées sur Android par
tests/jvm/Entrainement.kt, et le site refait les mêmes tirages (site/test/tirage.mjs).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_entrainement_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
sys.path.insert(0, str(RACINE / "donnees" / "entrainement"))

from tg import app, badges as B, core, entrainement as E, langue  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def sans(lignes):
    return langue.sans_marques("\n".join(lignes))


def etat():
    return core.load()


def modifier(fn):
    out = []
    core.modifier(lambda s: out.append(fn(s)))
    return out[0] if out else None


def bash(cmd, ou):
    subprocess.run(["bash", "-c", cmd], cwd=ou, capture_output=True, env=dict(os.environ, HOME=str(HOME)))


def lancer(typ):
    """Commence cet exercice précis (comme commencer, sans hasard sur le type)."""
    def f(s):
        gid, valeur, n = E._graine(s)
        p, emp = E.generer(typ, valeur, n)
        assert E.preparer(typ, p), typ
        E.e_(s)["cours"] = {"type": typ, "g": gid, "v": valeur, "n": n, "debut": time.time() - 3, "e": emp}
        return p
    return modifier(f)


langue.definir("fr")
(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()

print("Vecteurs communs (donnees/entrainement/vecteurs.json)")
import generer  # noqa: E402
V = json.loads((RACINE / "donnees/entrainement/vecteurs.json").read_text(encoding="utf-8"))
verifier(generer.vecteurs() == V, f"{len(V['exercices'])} tirages, médailles, échelons et semaines identiques au fichier")
verifier(len({x["empreinte"] for x in V["exercices"]}) > 400, "les tirages sont variés")
verifier(set(E.TYPES) == {x["type"] for x in V["exercices"]}, "les vecteurs couvrent les 19 exercices")
verifier(len(B.FAMILLES) == 8 and B.SEUILS == (1, 5, 15, 30, 50, 100), "8 familles, grades à 1 / 5 / 15 / 30 / 50 / 100")
verifier(B.echelon_de(50, 0) == 3 and B.echelon_de(50, 1) == 4 and B.echelon_de(15, 0) == 2,
         "le Giga demande aussi une médaille d'or")
verifier(B.ECHELONS == ("bit", "octet", "kilo", "mega", "giga", "tera"), "grades : Bit, Octet, Kilo, Méga, Giga, Téra")
verifier(B.echelon_de(300, 9, 2) == 4 and B.echelon_de(300, 3, 3) == 5 and B.echelon_de(99, 3, 3) == 4,
         "le Téra : 100 réussites et 3 médailles de diamant")
verifier([B.etoiles_de(n, 0) for n in (1, 2, 3, 4)] == [0, 1, 2, 3] and B.etoiles_de(5, 1) == 0
         and [B.etoiles_de(n, 2) for n in (18, 19, 23, 27, 29)] == [0, 1, 2, 3, 3], "étoiles : un quart du chemin chacune")
verifier([B.etoiles_de(n, 4) for n in (50, 62, 63, 75, 88, 99)] == [0, 0, 1, 2, 3, 3] and B.etoiles_de(9, -1) == 0,
         "Giga → Téra : étoiles à 63 / 75 / 88")
verifier([B.etoiles_de(n, 5) for n in (100, 150, 200, 299, 300, 999)] == [0, 1, 2, 2, 3, 3], "au Téra, les étoiles continuent à 150 / 200 / 300")
verifier(all(a < b for k in range(5) for a, b in zip((B.SEUILS[k],) + B.ETOILES[k], B.ETOILES[k] + (B.SEUILS[k + 1],))),
         "les étoiles tombent entre deux grades")
def _pixels(g):
    return sum(1 for l in g for c in l if c)
gal = [_pixels(B.galons(e)) for e in B.ECHELONS]
verifier(all(len(B.ecusson(f, e)) == 28 and all(len(l) == 18 for l in B.ecusson(f, e)) for f in B.FAMILLES for e in B.ECHELONS),
         "badge complet : 18 × 28 pixels")
verifier(gal == sorted(gal) and len(set(gal)) == 6, f"les galons grandissent à chaque grade ({gal} pixels)")
verifier(sum(1 for c in B.ecusson("lecteur", "kilo", 2)[2] if c == B.ETOILE_ON) == 10
         and _pixels(B.ecusson(None, None)) == _pixels(B.grille(None, None)), "étoiles allumées sur le badge ; « ??? » sans galons")
verifier(E.migrer_titre("explorateur:argent") == "explorateur:kilo" and E.migrer_titre("touche") == "touche",
         "vieille sauvegarde : le titre « … d'Argent » devient « … Kilo »")

print("Avant le terrain, avant les commandes")
st = etat()
r = sans(modifier(lambda s: E.commande_texte(s, [])))
verifier("pas encore" in r or "première leçon" in r, "pas de terrain : on continue la première leçon")
T.mkdir()
(T / "nid").mkdir()
(T / "nid" / "lit.txt").write_text("doux\n")
r = sans(modifier(lambda s: E.commande_texte(s, [])))
verifier("premières commandes" in r, "aucune commande connue : la salle attend gentiment")
lignes = sans(modifier(E.ecran_badges))
verifier(lignes.count("???") == 8, "les 8 badges sont cachés (« ??? »)")

print("Explorateur : le dossier courant")
modifier(lambda s: s["seen"].extend(["cd"]))
verifier(modifier(E.familles_ouvertes) == ["explorateur"], "cd tapé : seule la famille Explorateur s'ouvre")
r = sans(modifier(lambda s: E.commande_texte(s, ["batisseur"])))
verifier("encore caché" in r, "une famille fermée : elle reste cachée, sans reproche")
r = sans(modifier(lambda s: E.commande_texte(s, [])))
verifier("Salle d'entraînement" in r and "Explorateur" in r and "salle_entrainement" in r, "un exercice commence : " + r.splitlines()[1][:60])
c = etat()["entrainement"]["cours"]
p, _ = E.generer(c["type"], c["v"], c["n"])
cible = E.salle() / p["pieces"][p["i"]] / p["coins"][p["j"]]
verifier(cible.is_dir(), "la salle est préparée dans le terrain")
xp0 = etat()["xp"]
st = app.etape(spontane=False, defis=False, extra=[f"cd {cible}"], cwd=str(cible))
verifier(st["entrainement"]["cours"] is None, "être dans la bonne pièce réussit l'exercice")
verifier(st["entrainement"]["familles"]["explorateur"]["n"] == 1 and st["xp"] > xp0, "1 réussite et de l'XP pour la créature")
verifier(st["entrainement"]["records"].get(c["type"]) and len(st["entrainement"]["envoyer"]) == 1,
         "un record personnel, un exercice à envoyer au site")
verifier(E.titre_affiche(st)[0] == "Élève de la salle", "premier titre : « Élève de la salle »")
verifier("Explorateur" in langue.sans_marques(" ".join(st["log"])) or "exercice réussi" in " ".join(st["log"]),
         "le journal le raconte")
verifier((T / "nid" / "lit.txt").is_file(), "rien n'est touché hors de la salle d'entraînement")

print("Chaque exercice, pour de vrai")
modifier(lambda s: (s["seen"].extend(["ls", "mkdir", "touch", "cp", "mv", "rm", "rmdir", "cat", "head", "tail",
                                      "grep", "find", "echo", "wc", "sh", "chmod"]),
                    E.e_(s)["sym"].extend([">", ">>", "|"])))
verifier(modifier(E.familles_ouvertes) == list(B.FAMILLES), "toutes les commandes connues : les 8 familles sont ouvertes")
S = E.salle()
for typ, (fam, _c, _s, _par, a_reponse) in E.TYPES.items():
    p = lancer(typ)
    if a_reponse:
        faux = sans(modifier(lambda s: E.commande_texte(s, ["zzz"])))
        bon = E.reponse(typ, p)
        if typ == "det_grep":
            sortie = subprocess.run(["bash", "-c", f"grep -l {p['mots'][0]} indices/*"], cwd=S, capture_output=True, text=True).stdout
            verifier(sortie.strip() == f"indices/{bon}.txt", "grep trouve le bon objet : " + sortie.strip())
        if typ == "plo_tuyau":
            sortie = subprocess.run(["bash", "-c", E.idees(typ, p)[0]], cwd=S, capture_output=True, text=True).stdout
            verifier(sortie.strip() == bon, f"le tuyau compte {bon}")
        if typ in ("lec_cat", "lec_head", "lec_tail", "cui_lancer"):
            sortie = subprocess.run(["bash", "-c", E.idees(typ, p)[-1]], cwd=S, capture_output=True, text=True).stdout
            verifier(bon in sortie.split("\n")[-2].lower() or bon in sortie.lower(), f"la commande d'idée montre la réponse ({bon})")
        r = sans(modifier(lambda s: E.commande_texte(s, [bon + (".txt" if typ == "det_grep" else "")])))
        verifier("Pas tout à fait" in faux and "Bravo" in r, f"{typ} : mauvaise réponse gentille, puis bonne réponse")
        continue
    if typ in ("exp_chemin", "exp_cle"):
        ici = S / p["pieces"][p["i"]] / p["coins"][p["j"]]
        st = app.etape(spontane=False, defis=False, extra=[f"cd {ici}"], cwd=str(ici))
    else:
        for x in E.idees(typ, p):
            bash(x, S)
        if typ == "bat_objets":
            bash(f"touch {p['pieces'][0]}/{p['objets'][1]}.txt", S)
        if typ == "cui_ecrire":
            verifier(subprocess.run(["bash", "-c", "./miam.sh"], cwd=S, capture_output=True, text=True).stdout.strip()
                     == p["mots"][0], "la recette écrite dit le mot")
        avant = etat()["entrainement"]["cours"]
        verifier(avant is not None, f"{typ} : pas réussi avant le tour de jeu")
        st = app.etape(spontane=False, defis=False, extra=E.idees(typ, p), cwd=str(S))
    verifier(st["entrainement"]["cours"] is None, f"{typ} ({fam}) réussi avec {', '.join(E.idees(typ, p))}")

print("Pas de punition")
p = lancer("net_rm")
(S / p["pieces"][0] / (p["objets"][0] + ".txt")).unlink()
st = app.etape(spontane=False, defis=False, extra=["rm x"], cwd=str(S))
dits = " ".join([(st.get("bubble") or [""])[0]] + [b[0] for b in st.get("bulles", [])])
verifier(st["entrainement"]["cours"] is not None and "pas grave" in dits,
         "l'objet à garder est effacé : un « oups » gentil, rien de perdu")
r = sans(modifier(lambda s: E.commande_texte(s, ["fin"])))
verifier("rangé" in r and etat()["entrainement"]["cours"] is None, "tg entrainement fin range l'exercice")
r = sans(modifier(lambda s: E.commande_texte(s, ["fin"])))
verifier("Pas d'exercice" in r, "rien à ranger : on le dit simplement")
p = lancer("lec_cat")
r = sans(modifier(lambda s: E.commande_texte(s, [langue.sans_marques(core.piege(p["mots"][0])) if False else
                                                 "а" + p["mots"][0][1:]])))
verifier("collée" in r and etat()["entrainement"]["cours"], "une réponse collée (piégée) ne compte pas")
modifier(lambda s: E.commande_texte(s, ["fin"]))

print("La salle reste dans le terrain")
lancer("bat_pieces")
(S / "../nid/lit.txt").resolve()
verifier((T / "nid" / "lit.txt").is_file() and S.resolve().parent == T.resolve(), "la salle est une pièce du terrain")
import shutil  # noqa: E402
shutil.rmtree(S)
dehors = Path(tempfile.mkdtemp(prefix="tg_dehors_"))
(dehors / "precieux.txt").write_text("à garder")
S.symlink_to(dehors)
r = sans(modifier(lambda s: E.commencer(s, "batisseur")))
verifier((dehors / "precieux.txt").is_file() and "préparer" in r, "une salle remplacée par un lien : on ne touche à rien")
S.unlink()

print("Badges et échelons")
def regler(f, n, ors=0):
    def g(s):
        x = E.fam_(E.e_(s), f)
        x.update(n=n, bronze=n - ors, argent=0, **{"or": ors}, diamant=0)
    modifier(g)
regler("batisseur", 4)
lancer("bat_pieces")
for x in ("cave", "jardin", "grenier", "salon", "bureau", "chambre", "garage", "veranda", "atelier", "cuisine",
          "bibliotheque", "couloir"):
    bash(f"mkdir -p {x}", S)
st = app.etape(spontane=False, defis=False, extra=["mkdir cave"], cwd=str(S))
verifier(B.echelon_de(st["entrainement"]["familles"]["batisseur"]["n"]) == 1, "5e réussite : badge Bâtisseur en Octet")
verifier("badge Bâtisseur : Octet" in " ".join(st["log"]), "« badge Bâtisseur : Octet » dans le journal")
regler("nettoyeur", 50, 0)
verifier(E.echelon(E.e_(etat()), "nettoyeur") == 3, "50 réussites sans médaille d'or : encore Méga")
regler("nettoyeur", 50, 1)
verifier(E.echelon(E.e_(etat()), "nettoyeur") == 4, "… avec une médaille d'or : Giga")
regler("cuisinier", 100, 1)
r = sans(modifier(lambda s: E.ecran_badges(s)))
verifier("💎 0/3" in r, "100 réussites sans 3 médailles de diamant : encore Giga (💎 0/3)")
modifier(lambda s: E.fam_(E.e_(s), "cuisinier").update(diamant=3, bronze=96, **{"or": 1}))
verifier(E.echelon(E.e_(etat()), "cuisinier") == 5 and "Cuisinier Téra" == E.titre_affiche(etat())[0],
         "… avec 3 médailles de diamant : Téra, le plus beau titre « Cuisinier Téra »")
regler("cuisinier", 0)
regler("plombier", 9)
r = sans(modifier(lambda s: E.ecran_badges(s)))
verifier("Octet ★☆☆" in r and "9/15 → Kilo" in r, "tg badges : le grade, ses étoiles et la suite (Octet ★☆☆ · 9/15 → Kilo)")
regler("plombier", 0)
ecran = sans(modifier(E.ecran_badges))
verifier("Giga" in ecran and "Octet" in ecran and "▀" in ecran and "50/100 → Téra" in ecran, "tg badges dessine les badges, leurs grades et leurs étoiles")
verifier("Nettoyeur Giga" in ecran, "le titre affiché est le plus beau : « Nettoyeur Giga »")
verifier("`tg badges grades`" in ecran or "tg badges grades" in ecran, "tg badges présente les grades")
gr = sans(modifier(lambda s: E.commande_badges(s, ["grades"])))
verifier("8 bits" in gr and "dès 50" in gr, "tg badges grades : ce que veulent dire Bit, Octet, Kilo…")
verifier(all(x in gr for x in ("Bit", "Octet", "Kilo", "Méga", "Giga", "Téra", "300", "bibliothèque de films", "▀")),
         "… avec les 6 galons, le Téra et ses étoiles")
liste = sans(modifier(lambda s: E.ecran_titres(s)))
verifier("Élève de la salle" in liste and "Bâtisseur Octet" in liste, "tg badges titre : la liste des titres")
n = sans(modifier(lambda s: E.ecran_titres(s))).split("\n").index(
    next(l for l in liste.split("\n") if "Élève de la salle" in l))
modifier(lambda s: E.ecran_titres(s, str(n)))
verifier(E.titre_affiche(etat())[0] == "Élève de la salle", "on choisit son titre")
modifier(lambda s: E.ecran_titres(s, "auto"))
verifier(E.titre_affiche(etat())[0] == "Nettoyeur Giga", "auto : le plus beau titre revient")
for f in B.FAMILLES:
    regler(f, 30, 1)
verifier(E.titre_affiche(etat()) == ("Légende de la salle", "arc"), "8 familles en Méga : « Légende de la salle » (arc-en-ciel)")
import re  # noqa: E402
verifier("« Légende de la salle »" in re.sub(r"\x1b\[[0-9;]*m", "", app.render(etat(), 0, False)),
         "le titre est à côté du nom sur l'écran principal")

print("Star de la semaine (gardée une semaine)")
modifier(lambda s: E.e_(s).update(hebdo={"semaine": E.semaine_precedente(), "familles": ["lecteur"]}))
verifier(any(i == "star:lecteur" for i, _x, _c in E.titres(etat())), "gagnée la semaine dernière : affichée cette semaine")
modifier(lambda s: E.e_(s).update(hebdo={"semaine": E.semaine(time.time() - 14 * 86400), "familles": ["lecteur"]}))
verifier(not any(i.startswith("star:") for i, _x, _c in E.titres(etat())), "la semaine d'après, elle disparaît")
verifier(E.semaine(1793000000) == "2026-W44", "semaines ISO (UTC)")

print("Synchro (ce qui part au site, ce qui revient)")
st = etat()
charge, snap = E.charge(st, {"lecteur": {"n": 10}})
verifier(charge["deltas"]["lecteur"]["n"] == 20 and charge["deltas"]["batisseur"]["n"] == 30, "les compteurs partent en différence")
verifier(all({"id", "type", "g", "n", "t", "d", "e"} <= set(r) for r in charge["runs"]) and charge["runs"],
         f"{len(charge['runs'])} exercices à vérifier (type, graine, compteur, temps, empreinte)")
typ = next(iter(st["entrainement"]["records"]))
srv = {"familles": {f: {"n": 100, "bronze": 0, "argent": 0, "or": 1, "diamant": 0} for f in B.FAMILLES},
       "records": {typ: {"t": st["entrainement"]["records"][typ]["t"], "v": True}}}
def appliquer(s):
    E.appliquer(s, srv, snap, charge["runs"], {"hebdo": {"semaine": "2026-W40", "familles": []}, "compte": {"lecteur": 2}})
modifier(appliquer)
st = etat()
verifier(st["entrainement"]["familles"]["lecteur"]["n"] == 100 and not st["entrainement"]["envoyer"],
         "les compteurs communs reviennent, les exercices envoyés sont oubliés")
verifier(st["entrainement"]["records"][typ]["v"] is True, "le site a vérifié le record : « ✔ vérifié »")
verifier("2 fois" in sans(modifier(E.ecran_badges)), "le compteur en ligne des Stars de la semaine s'affiche")
recs = sans(modifier(E.ecran_records))
verifier("vérifié" in recs and " s" in recs, "tg badges records")

print("Les commandes à taper")
def sans_cd(s):
    s["seen"] = [x for x in s["seen"] if x != "find"]
modifier(sans_cd)
st = etat()
verifier(E.vert(st, "ls") == "`ls`".replace("ls", core.piege("ls")) or E.vert(st, "ls").startswith("`"),
         "une commande déjà rencontrée est en vert")
verifier(not E.vert(st, "find . -name x").startswith("`"), "une commande jamais rencontrée n'est pas en vert")
verifier("tg entrainement" in app.aide(), "tg aide parle de la salle d'entraînement")

print()
print(f"{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
