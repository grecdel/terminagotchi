"""Test de l'introduction et du déblocage progressif (PC) : écrans du début, l'œuf et sa liste de commandes, ses
réactions et l'éclosion, l'écran « merci », la table de déblocage (intro.json), « pas encore », la migration des
anciennes parties, `tg debloquer tout`, l'invite du shell, le guide à l'écran principal, les régions gardées sur la
carte, et les 14 langues.

    python3 pc/outils/test_intro.py          (crée son propre HOME temporaire)

Les mêmes règles sont testées sur Android par tests/jvm/Intro.kt.
"""
import builtins
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_intro_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import (accueil, app, bestiaire as B, compagnon, core, guide as G, histoire, intro, langue, maison,  # noqa: E402
                parties)

HOME = Path.home()
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def propre(x):
    x = "\n".join(x) if isinstance(x, list) else str(x)
    return langue.sans_marques(ANSI.sub("", x))


def plat(x):
    """Le texte sur une seule ligne (les phrases sont coupées à l'écran)."""
    return re.sub(r"\s+", " ", propre(x))


def tape(*cmds):
    """L'enfant tape des commandes dans son terminal (l'historique du shell), puis une étape de jeu."""
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        for c in cmds:
            f.write(c + "\n")
    return app.etape(spontane=False, defis=False)


def lancer(*argv):
    """`tg …` : ce que la commande affiche."""
    vieux = sys.argv
    sys.argv = ["tg", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            app.main()
    finally:
        sys.argv = vieux
    return buf.getvalue()


FR = langue._charger("fr")


def cles_affichees(texte):
    return [k for k in re.findall(r"\b[a-z_]+(?:\.[\w-]+)+\b", propre(texte)) if k in FR]


print("1. Les données : une seule source (donnees/intro.json), recopiée à l'identique")
src = (RACINE / "donnees" / "intro.json").read_text(encoding="utf-8")
verifier((RACINE / "pc" / "tg" / "intro.json").read_text(encoding="utf-8") == src, "pc/tg/intro.json = donnees/intro.json")
verifier((RACINE / "app" / "src" / "main" / "assets" / "intro.json").read_text(encoding="utf-8") == src,
         "app/src/main/assets/intro.json = donnees/intro.json")
D = json.loads(src)
ids = [f["id"] for f in D["deblocages"]]
verifier(len(ids) == len(set(ids)) and ids[0] == "histoire", f"{len(ids)} fonctions, l'histoire d'abord : {', '.join(ids)}")
attendues = {"histoire", "envies", "carte", "lexique", "quetes", "combats", "extras", "equipe", "entrainement", "compte",
             "biomes", "donjon"}
verifier(attendues <= set(ids), "toutes les fonctions du jeu sont dans la table (envies, carte, lexique, quêtes, équipe…)")
toutes = [c for f in D["deblocages"] for c in f["commandes"]]
verifier(len(toutes) == len(set(toutes)), "chaque commande appartient à une seule fonction")
verifier(all(f["quand"].get("eclos") for f in D["deblocages"]), "rien ne s'ouvre avant l'éclosion")
connues = {"eclos", "niveau", "lecons", "chapitres", "ailes", "captures", "apres"}
verifier(all(set(f["quand"]) <= connues for f in D["deblocages"]), "les conditions sont toutes connues : " + ", ".join(sorted(connues)))
lecons_hist = {l for c in histoire.CHAPITRES for l in c["lecons"]}
verifier(all(l in lecons_hist for f in D["deblocages"] for l in f["quand"].get("lecons", [])),
         "les leçons de la table existent dans l'histoire")
verifier(all(c in histoire.PAR_CHAP for f in D["deblocages"] for c in f["quand"].get("chapitres", [])),
         "les chapitres de la table existent")
verifier(all(f["id"] == "histoire" or (f"deb.{f['id']}.titre" in FR and f"deb.{f['id']}.texte" in FR and f["cmd_pc"] and f["cmd_tel"])
             for f in D["deblocages"]), "chaque fonction a son titre, son texte et ses commandes PC / Android")
verifier(len(D["checklist"]) == 4 and [c["id"] for c in D["checklist"]] == ["pwd", "ls", "echo", "whoami"],
         "la liste de l'œuf : pwd, ls, echo, whoami (des commandes que tous les shells connaissent)")
for c in D["checklist"]:
    verifier(re.search(c["re"], intro.commande_de(c), re.I) is not None, f"« {intro.commande_de(c)} » est reconnue par sa règle")
verifier(not re.search(D["checklist"][2]["re"], "echo", re.I), "« echo » tout seul ne compte pas (il faut un message)")

print("2. Les écrans du début : Entrée = suite, p = passer, puis le nom (demandé et confirmé)")
reponses = iter(["", "", "", "", "Brindille", ""])
invites = []
with redirect_stdout(io.StringIO()) as buf:
    nom = intro.jouer_ecrans(lambda _invite="": (invites.append(_invite), next(reponses))[1])
ecrans = buf.getvalue()
verifier(nom == "Brindille", "4 fois Entrée : les 4 écrans, puis le nom demandé, puis Entrée = oui")
verifier("Brindille" in propre(invites[-1]) and "?" in propre(invites[-1]),
         f"le nom est confirmé ({propre(invites[-1]).strip()!r})")
p = propre(ecrans)
for k in (1, 2, 3, 4):
    verifier(langue.t(f"intro.e.titre.{k}") in p, f"écran {k} : « {langue.t(f'intro.e.titre.{k}')} »")
verifier("vrai terminal" in p and "invite de commande" in p, "l'écran 3 dit ce qu'est l'invite de commande et que c'est un vrai terminal")
verifier("▀" in ecrans or "▄" in ecrans, "chaque écran a sa scène en pixels (demi-blocs)")
with redirect_stdout(io.StringIO()):
    r = iter(["p", "Brindille", "oui"])
    verifier(intro.jouer_ecrans(lambda _i="": next(r)) == "Brindille", "p : passer l'intro (le nom est quand même demandé)")
    # simulation de Tom (P1-6) : un mot tapé sur un écran ne devient pas le nom de l'œuf
    r = iter(["jouer", "oui", "", "", "Pixou", ""])
    verifier(intro.jouer_ecrans(lambda _i="": next(r)) == "Pixou", "« jouer » tapé à l'écran 1 n'est PAS le nom de l'œuf")
    r = iter(["", "", "", "", "jouer", "Pixou", ""])
    verifier(intro.jouer_ecrans(lambda _i="": next(r)) == "Pixou", "« Ton œuf s'appellera « jouer » ? » : un autre nom le remplace")
    r = iter(["", "", "", "", "\x1b[2JZoé\u202e", ""])
    verifier(intro.jouer_ecrans(lambda _i="": next(r)) == "[2JZoé", "le nom perd ses caractères de contrôle")

print("3. Nouvelle partie : l'œuf seul, l'invite et la liste")
(HOME / ".bash_history").touch()
reponses = iter(["", "", "", "", "Pixou", ""])
builtins.input = lambda _invite="": next(reponses)
with redirect_stdout(io.StringIO()):
    app.creer_si_besoin(avec_intro=True)
st = core.load()
core.migrate(st)
verifier(st["name"] == "Pixou", "le nom tapé pendant l'intro est celui de l'œuf")
verifier(intro.en_cours(st) and st["debloc"]["mode"] == "progressif" and not st["debloc"]["ouverts"],
         "l'intro est en cours, rien n'est encore ouvert")
ecran = app.render(st, 0, True)
pe = plat(ecran)
verifier(all(intro.commande_de(c) in pe for c in D["checklist"]), "l'écran montre la liste : pwd, ls, echo bonjour, whoami")
verifier("0/4" in pe and langue.t("intro.astuce.0") in pe, "0/4 et la première astuce (taper la commande en vert, Entrée)")
verifier(langue.t("intro.ou.pc") in pe, "où taper (l'invite de commande, après le $)")
verifier(langue.t("app.digere", os="x").split("(")[0].strip() not in pe and "INT" not in pe,
         "rien d'autre : ni les statistiques, ni ce que la créature digère")
verifier("`" not in ANSI.sub("", langue.rendre(ecran)), "les commandes sont en vert (plus aucun ` à l'écran)")
for cmd in ("carte", "quetes", "envies", "guide", "entrainement", "compte", "lexique", "defi"):
    sortie = propre(lancer(cmd))
    verifier(f"🔒 {cmd} : pas encore" in sortie and "Traceback" not in sortie, f"`tg {cmd}` : « pas encore » (jamais une erreur)")
verifier("[m]" not in propre(app.touches(st)) and "[o]" in propre(app.touches(st)),
         "le pied de la fenêtre cache les touches des fonctions fermées ([m] carte…), garde [o] options")

print("4. Chaque bonne commande fait réagir l'œuf ; l'XP s'arrête avant l'éclosion")
st = tape("ls")
verifier(st["intro"]["faits"] == ["ls"] and st["anim"][0] == "oeuf_1", "ls : l'œuf réagit (animation oeuf_1)")
verifier(core.stage(core.level(st["xp"])) == 0, "il ne grandit pas encore")
verifier(langue.t("intro.astuce.1") in plat(app.render(st, 1, True)), "2e astuce : une erreur, ce n'est pas grave")
st = tape("blablabla")
verifier(st["intro"]["erreur"] and langue.t("intro.astuce.erreur") in plat(app.render(st, 2, True)),
         "une commande inconnue : l'astuce dit que ce n'est pas grave")
st = tape("pwd", "date", "uname", "hostname", "id", "df", "cal")
verifier(st["intro"]["faits"] == ["ls", "pwd"] and st["xp"] <= 9 and core.level(st["xp"]) == 1,
         f"plein d'autres commandes : l'œuf garde ses 9 XP au plus ({st['xp']})")
verifier(langue.t("intro.astuce.2") in plat(app.render(st, 3, True)), "3e astuce : ↑ rappelle la commande d'avant")
st = tape("whoami")
verifier(len(st["intro"]["faits"]) == 3 and st["anim"][0] == "oeuf_3", "whoami : 3e fêlure")
verifier(langue.t("intro.astuce.3") in plat(app.render(st, 4, True)), "4e astuce : Tab complète")
st = tape("echo")
verifier(len(st["intro"]["faits"]) == 3, "« echo » sans message ne compte pas")

print("5. Les fêlures et l'animation de l'œuf (mêmes images qu'Android)")
fel = [sum(r.count("f") for r in intro.image_oeuf(n)) for n in range(4)]
imgs = [intro.image_oeuf(n) for n in range(4)]
verifier(fel[0] == 0 < fel[1] < fel[3] and len({tuple(x) for x in imgs}) == 4,
         f"3 stades de fêlure : intact, une fêlure qui luit, le dessin fissuré, une grande fêlure ({fel} pixels qui luisent)")
from tg import oeufs as O
src = (RACINE / "donnees" / "oeufs" / "oeufs.json").read_text(encoding="utf-8")
verifier((RACINE / "pc" / "tg" / "oeufs.json").read_text(encoding="utf-8") == src
         and (RACINE / "app" / "src" / "main" / "assets" / "oeufs.json").read_text(encoding="utf-8") == src,
         "oeufs.json : une seule source (donnees/oeufs/), recopiée à l'identique pour PC et Android")
verifier(O.types() == list(G.TYPES) and all((RACINE / "donnees" / "oeufs" / f"oeuf_{ty}_{e}.png").is_file()
                                            for ty in G.TYPES for e in O.donnees()["etats"]),
         "un œuf par type de biome (9), chacun dessiné en 3 états (intact, fissure, eclosion)")
W0, H0 = O.taille()
ok = True
for ty in O.types():
    x = O.donnees()["types"][ty]
    pal = O.palette(ty)
    for taille in ("grand", "petit"):
        w, h = O.taille(taille)
        for e, rows in x[taille].items():
            ok &= len(rows) == h and all(len(r) == w for r in rows) and all(c == "." or c in pal for r in rows for c in r)
            ok &= sum(c != "." for r in rows for c in r) > w * h // 6
    ok &= len(x["palette"]) <= 36 and len(x["feles"][0]) >= 6 and len(x["feles"][1]) >= 8
    ok &= intro.image_oeuf(0, "", 0, ty) != intro.image_oeuf(0, "", 0, "feu" if ty != "feu" else "eau")
verifier(ok and (W0, H0) == (intro.W_OEUF, intro.H_OEUF), f"les 9 œufs : {W0}×{H0} pixels (petit {O.taille('petit')}), palette limitée, contour net")
verifier(intro.image_oeuf(1, "remue", 1) != intro.image_oeuf(1, "remue", 3), "il remue (penche à gauche, à droite)")
verifier(any("h" in r for r in intro.image_oeuf(1, "brille", 0)) and any("y" in r for r in intro.image_oeuf(1, "brille", 0)),
         "il brille (étincelles)")
verifier(intro.image_oeuf(3, "eclot", 7) is None, "à la fin de l'éclosion : la créature prend la place")
neuf = core.migrate(core.new_state("Zoé"))
intro.nouvelle_partie(neuf)
verifier(neuf["oeuf_type"] in G.TYPES and G.g_(neuf)["type_c"] == neuf["oeuf_type"] == O.type_de(neuf),
         f"nouvelle partie : un œuf {neuf['oeuf_type']}, et le compagnon qui en sort est du même type")
verifier(len({core.new_state("Zoé")["oeuf_type"] for _ in range(300)}) == 9, "le type de l'œuf est tiré au hasard parmi les 9")
vieux = core.migrate(core.new_state("Vieux"))
vieux.pop("oeuf_type")
vieux["guide"]["type_c"] = "roche"
from tg import sprites as SP
verifier(O.type_de(core.migrate(vieux)) == "roche" and G.g_(vieux)["type_c"] == "roche"
         and SP.get_sprite(vieux, 0) == O.petit("roche") and SP.palette(vieux)["A"] == O.palette("roche")["A"],
         "une ancienne partie garde le type de son compagnon ; son œuf (écran principal) est l'œuf de ce type")
verifier(intro.image_oeuf(2, "", 0, "glace") == [r for r in O.donnees()["types"]["glace"]["grand"]["fissure"]]
         and intro.image_oeuf(3, "eclot", 4, "glace") != intro.image_oeuf(3, "eclot", 1, "glace"),
         "2 fêlures : le dessin fissuré ; l'éclosion : le dessin éclos")
for nom in ("oeuf_1", "oeuf_2", "oeuf_3", "eclosion"):
    f, ips = intro.animation(nom, st)
    verifier(len(f) >= 8 and ips > 0, f"animation {nom} : {len(f)} images")

print("6. La dernière commande : l'éclosion, la créature dit merci")
st = tape("echo bonjour")
verifier(intro.eclos(st) and core.stage(core.level(st["xp"])) == 1 and core.level(st["xp"]) == 2,
         "l'œuf a éclos : bébé, niveau 2")
verifier(st["anim"][0] == "eclosion", "animation de l'éclosion")
verifier(st["debloc"]["file"][:2] == ["merci", "merci2"] and intro.ouvert(st, "histoire"),
         "l'histoire s'ouvre, l'écran « merci » attend")
merci = plat(app.render(st, 5, True))
verifier("Pixou" in merci and langue.t("intro.recap") in merci, "merci : la créature remercie et récapitule")
verifier(all(c in merci for c in ("pwd", "ls", "echo", "whoami")) and "print working directory" in merci,
         "le vrai sens des commandes (print working directory…)")
st = core.modifier(intro.lu)
ici = plat(app.render(st, 6, True))
verifier(str(HOME) in ici and "camp de base" in ici and "pwd" in ici, "où on est : le camp de base (ce que pwd a montré)")
verifier(langue.t("hist.reveil.titre") in ici, "et la suite : le chapitre 1 « Le réveil »")
st = core.modifier(intro.lu)
ecran = propre(app.render(st, 7, True))
verifier(langue.t("lec.t0.titre") in ecran and "(1/3)" in ecran,
         "après l'écran merci : la leçon 1 du chapitre 1, à son début (les commandes de l'œuf ne la valident pas)")
verifier(not intro.ouvert(st, "envies") and "🍎" not in ecran, "les envies ne sont pas encore ouvertes (pas de jauges)")

print("7. La table de déblocage, dans l'ordre de l'histoire")


def apres(fn, attendu, msg):
    s = core.modifier(lambda x: (fn(x), intro.verifier(x)))
    nouveaux = [x for x in s["debloc"]["file"] if x not in ("merci", "merci2")]
    verifier(all(intro.ouvert(s, a) for a in attendu) and set(attendu) <= set(nouveaux), msg + f" → {', '.join(attendu)}")
    core.modifier(lambda x: x["debloc"].__setitem__("file", []))
    return s


st = apres(lambda s: histoire.h_(s)["faits"].append("t0"), ["envies"], "leçon t0 finie")
verifier(any("✨" in l and langue.t("deb.envies.titre") in l for l in st["log"]), "une ligne ✨ Nouveau dans le journal")
verifier("🔒" not in propre(lancer("envies")), "`tg envies` répond maintenant")
st = apres(lambda s: (histoire.h_(s)["faits"].append("reveil1"), histoire.h_(s)["ailes"].append("reveil")), ["carte"],
           "chapitre 1 fini")
verifier("[m]" in propre(app.touches(st)), "la touche [m] carte apparaît")
st = apres(lambda s: histoire.h_(s)["faits"].extend(["nid0", "debarras"]), ["lexique"], "leçon debarras finie")
st = apres(lambda s: histoire.h_(s)["faits"].append("nid1"), ["quetes"], "leçon nid1 finie")
st = apres(lambda s: histoire.h_(s)["ailes"].append("nid"), ["combats"], "chapitre 2 fini")
st = apres(lambda s: s.__setitem__("xp", 10 * 3 ** 2), ["extras"], "niveau 4")
e = next(x for x in B.publiques() if G.type_de(x, "classique") == "feu")
st = apres(lambda s: s["captures"].append(dict(B.individu(e, False, e["zone"], "classique", qualite=0.5), stade="enfant", xp=0)),
           ["equipe"], "une première bestiole dressée")
st = apres(lambda s: s.__setitem__("xp", 10 * 5 ** 2), ["entrainement"], "niveau 6")
st = apres(lambda s: histoire.h_(s)["ailes"].append("grenier"), ["compte"], "une aile réveillée")
st = apres(lambda s: histoire.h_(s)["ailes"].append("cave"), ["biomes"], "deux ailes (et l'équipe déjà là)")
st = apres(lambda s: histoire.h_(s)["ailes"].append("bibliotheque"), ["donjon"], "trois ailes")
verifier(all(intro.ouvert(st, f) for f in ids), "tout est ouvert à la fin")
verifier(len(st["debloc"]["presentes"]) == len(set(st["debloc"]["presentes"])) == len(ids), "chaque fonction présentée une seule fois")
carte_eq = plat(intro.lignes_ecran(st, "equipe"))
verifier("tg equipe" in carte_eq and "tg guide <nom>" in carte_eq, "l'écran de l'équipe donne les commandes PC")

print("8. L'invite du shell : la liste au début, l'œuf qui réagit, puis les écrans une fois")
s2 = core.new_state("Zou")
core.migrate(s2)
intro.nouvelle_partie(s2)
p1 = propre(intro.pour_prompt(s2))
verifier(all(intro.commande_de(c) in p1 for c in D["checklist"]), "la première invite montre la liste")
verifier(intro.pour_prompt(s2) == [], "… une seule fois")
s2["intro"]["faits"] = ["pwd"]
s2["intro"]["evt"] = [1, 123.0]
verifier("✔" in propre(intro.pour_prompt(s2)), "après une bonne commande : l'œuf et la liste (✔ pwd)")
verifier("➜ ls" in propre(compagnon.ligne(s2)) and "1/4" in propre(compagnon.ligne(s2)),
         "la ligne du compagnon dit la prochaine commande de la liste")
intro.finir(s2)
p2 = propre(intro.pour_prompt(s2))
verifier("Zou" in p2 and s2["debloc"]["file"] == ["merci2"], "après l'éclosion : l'écran « merci » dans le shell, une fois")

print("9. Anciennes parties : rien ne se ferme (migration)")
v = core.migrate(core.new_state("Vieux"))
verifier(v["debloc"]["mode"] == "ancien" and all(intro.ouvert(v, f) for f in ids) and intro.eclos(v),
         "une partie d'avant (sans « debloc ») : tout est ouvert, pas d'œuf qui attend")
verifier(v["debloc"]["file"] == [] and "histoire" in v["debloc"]["presentes"], "rien à présenter de ce qui est déjà atteint")
v2 = core.new_state("Avancé")
v2["xp"] = 10 * 6 ** 2
v2["histoire"] = {"chap": None, "faits": ["t0", "reveil1", "nid0", "debarras", "nid1", "secrets"], "ailes": ["reveil", "nid", "grenier"],
                  "pas": {}, "ouverts": [], "v": 9}
core.migrate(v2)
deja = set(v2["debloc"]["presentes"])
verifier({"envies", "carte", "lexique", "quetes", "combats", "extras", "entrainement", "compte"} <= deja,
         "ce qu'elle avait déjà atteint est noté comme présenté (pas d'écran en trop)")
verifier("equipe" not in deja and intro.ouvert(v2, "equipe"), "l'équipe (pas encore de bestiole) reste ouverte")
intro.verifier(v2)
verifier(v2["debloc"]["file"] == [], "pas de vague d'écrans à l'ouverture d'une vieille partie")
v2["captures"].append(dict(B.individu(e, False, e["zone"], "classique", qualite=0.5), stade="enfant", xp=0))
intro.verifier(v2)
verifier(v2["debloc"]["file"] == [] and "equipe" in v2["debloc"]["presentes"],
         "plus tard non plus : un ancien joueur n'a pas d'écran « nouveau » pour ce qu'il connaît déjà")
verifier(intro.bloque(v2, "troupe") is None, "aucune commande ne répond « pas encore » à un ancien joueur")

print("10. `tg debloquer tout` (parents, tests) : avec confirmation")
s3 = core.load()
core.modifier(lambda s: (s.update(intro={"etat": "oeuf", "faits": [], "evt": None, "erreur": False}),
                         s.update(debloc={"mode": "progressif", "ouverts": [], "presentes": [], "file": []}), s.update(xp=0)))
builtins.input = lambda _i="": "non"
verifier("Rien n'a changé" in propre(lancer("debloquer", "tout")) and intro.en_cours(core.load()), "« non » : rien ne change")
builtins.input = lambda _i="": "oui"
verifier("débloqué" in propre(lancer("debloquer", "tout")), "« oui » : tout est débloqué")
s3 = core.load()
verifier(intro.eclos(s3) and all(intro.ouvert(s3, f) for f in ids) and core.level(s3["xp"]) >= 2, "l'œuf a éclos, tout est ouvert")
verifier("🔒 carte" not in propre(lancer("carte")) and "Terminaworld" in propre(lancer("carte")), "`tg carte` répond")

print("11. L'écran principal montre le GUIDE actuel (sprite, stade, aura)")
compagnon_seul = propre(app.dessin_guide(core.load(), 0)[0])
core.modifier(lambda s: G.choisir(s, e["nom"]))
st = core.load()
dessin, w = app.dessin_guide(st, 0)
verifier(G.actuel(st)[3] is not None and propre(dessin) != compagnon_seul and w > 0,
         f"le guide {e['nom']} est dessiné à la place du compagnon")
ecran = app.render(st, 1, True)
verifier(dessin[0].split("\x1b")[0] in ecran or "▀" in ecran, "et il est bien dans l'écran principal")
core.modifier(lambda s: G.choisir(s, s["name"]))
verifier(propre(app.dessin_guide(core.load(), 0)[0]) == compagnon_seul, "redevenu le compagnon : le compagnon est dessiné")

print("12. La carte grise les régions gardées (guide.region_ouverte / guide.peut_agrandir)")
T = core.TERRAIN
st = core.load()
core.migrate(st)
x = next(ty for ty in G.TYPES if ty not in G.types_equipe(st))       # un type absent de l'équipe
(T / "biome" / x / "parcelle_1").mkdir(parents=True, exist_ok=True)
(T / "biome" / "feu").mkdir(parents=True, exist_ok=True)
core.modifier(lambda s: maison.m_(s)["visites"].extend(["biome", f"biome/{x}", "biome/feu"]))
st = core.load()
core.migrate(st)
ns = {n["rel"]: n for n in maison.noeuds(st)}
verifier(ns[f"biome/{x}"]["garde"] == "fermee" and ns[f"biome/{x}/parcelle_1"]["garde"] == "fermee",
         f"biome/{x} : aucune bestiole {x} dans l'équipe → fermée (et ses parcelles)")
verifier(G.type_compagnon_initial(st) == "feu" or ns["biome/feu"]["garde"] == "visite",
         "biome/feu : une bestiole feu dans l'équipe, mais pas guide → visite")
verifier(maison.sol(ns[f"biome/{x}"]) == maison.SOLS["brume"], "la région fermée est grise sur le dessin")
texte = propre(maison.carte(st, "texte"))
verifier("🔒" in texte and langue.t("carte.garde.fermee", type=G.etiquette(x)) in texte, "la carte en texte dit 🔒 fermée")
core.modifier(lambda s: G.choisir(s, e["nom"]))
st = core.load()
ns = {n["rel"]: n for n in maison.noeuds(st)}
verifier(ns["biome/feu"]["garde"] == "", "le guide est de type feu : la région feu est normale (on peut l'agrandir)")
verifier(propre(maison.carte(st, "colonnes")) and len(maison.verifier_largeur(maison.carte(st, "colonnes"))) == 1,
         "la carte en colonnes reste alignée")

print("13. Une nouvelle partie depuis le menu (parties.nouvelle) peut commencer par l'intro")
reponses = iter(["oui", "", "", "", "", "Mimi", ""])
with redirect_stdout(io.StringIO()):
    msg = accueil.nouvelle(lambda _i="": next(reponses), avec_intro=True)
st = core.load()
core.migrate(st)
verifier(st["name"] == "Mimi" and intro.en_cours(st) and parties.liste(), "menu → nouvelle partie : intro, puis l'œuf seul")
s4 = core.migrate(core.new_state("Robot"))
verifier(not intro.en_cours(s4), "sans personne au clavier (scripts) : pas d'intro, tout est ouvert")

print("14. Les 14 langues : aucun texte manquant à l'écran")
for code in langue.LANGUES:
    langue.definir(code)
    s5 = core.migrate(core.new_state("Ana"))
    intro.nouvelle_partie(s5)
    textes = [intro.ecran_intro(k) for k in (1, 2, 3, 4)] + [intro.lignes_ecran_oeuf(s5)]
    s5["intro"]["faits"] = ["pwd", "ls"]
    s5["intro"]["erreur"] = True
    textes.append(intro.lignes_ecran_oeuf(s5))
    intro.finir(s5)
    textes += [intro.lignes_ecran(s5, c) for c in ["merci", "merci2"] + ids[1:]]
    textes.append(intro.bloque(core.migrate(dict(s5, debloc={"mode": "progressif", "ouverts": [], "presentes": [], "file": []})),
                               "carte") or "")
    bruts = [k for x in textes for k in cles_affichees(x)]
    verifier(not bruts, f"{code} : intro, œuf, merci et 11 écrans de nouveautés traduits" + (f" (clés : {bruts[:3]})" if bruts else ""))
    impairs = [x for x in textes for l in (x if isinstance(x, list) else [x]) if ANSI.sub("", l).count("`") % 2]
    verifier(not impairs, f"{code} : commandes en vert bien fermées")
langue.definir("fr")

print(f"\n{ok} vérifications réussies, {ko} échouée(s)")
sys.exit(1 if ko else 0)
