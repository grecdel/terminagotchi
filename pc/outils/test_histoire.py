"""Partie scriptée (PC) : « La Maison endormie », la carte, les quêtes et la migration des sauvegardes.

    python3 pc/outils/test_histoire.py          (crée son propre HOME temporaire)

Comme un vrai terminal : chaque commande est lancée avec bash dans le dossier courant du « terminal »,
écrite dans ~/.bash_history, puis le jeu fait une étape (app.etape) en recevant le dossier courant
d'après la commande (comme le compagnon de l'invite, qui tourne dans le dossier du shell).
  1. chapitres 1-2 : la vieille porte, l'œuf, le nid, le repas ;
  2. liberté : on entre dans la cave (l'aile est choisie toute seule), sa famille est attirée
     (tirage toujours vérifiable), on la réveille, on change d'aile sans perdre l'étape atteinte ;
  3. une pièce secrète (ls -a, cd .placard_secret), une quête d'habitant (les chaussettes), le
     tableau des annonces (quêtes générées), la quête du jour, suivre une quête ;
  4. la carte (brouillard, ★, ◉, largeur des cases) et le journal ; les terres sauvages ;
  5. le cœur s'ouvre à 5 ailes ; Abyssor (réponse comptée en direct) ;
  6. migration d'anciennes sauvegardes (tronc commun, arbre, étape en cours) sans rien perdre ;
  7. rien n'est jamais écrit hors du terrain ; toutes les clés construites existent dans les 14 langues.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_histoire_")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, core, explo, histoire, langue, maison, quetes, tirage  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
GRAINE = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"   # factice
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ENV = dict(os.environ, LC_ALL="C.UTF-8")     # (rev reste bloqué sans locale UTF-8 installée)
ok = ko = 0
terminal = [str(HOME)]          # le dossier courant du « terminal »


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def tape(cmd):
    """L'enfant tape une commande dans son terminal : elle s'exécute vraiment, part dans l'historique,
    puis l'invite (le compagnon) fait une étape de jeu depuis le nouveau dossier courant."""
    r = subprocess.run(["bash", "-c", cmd + "\n__s=$?; pwd; exit $__s"], cwd=terminal[0], capture_output=True, text=True,
                       timeout=30, env=ENV)
    lignes = r.stdout.strip().split("\n")
    if lignes and lignes[-1].startswith("/"):
        terminal[0] = lignes[-1]
    with open(HOME / ".bash_history", "a", encoding="utf-8") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=terminal[0])


def texte(x):
    return ANSI.sub("", "\n".join(x) if isinstance(x, list) else x)


def bulles(st):
    return " | ".join([(st.get("bubble") or [""])[0]] + [b[0] for b in st.get("bulles", [])])


def niveau(n):
    core.modifier(lambda s: s.__setitem__("xp", max(s["xp"], 10 * (n - 1) ** 2)))


def h(st):
    return st["histoire"]


def lecon(st):
    les, _ = histoire.lecon_courante(st)
    return (les["id"], st["step"]) if les else (None, st["step"])


def fichiers_hors_terrain():
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        if racine.startswith(str(T)) or "/.terminagotchi" in racine:
            dossiers[:] = []
            continue
        for f in fichiers:
            out.add(os.path.join(racine, f))
    return out


# ====================================================================== mise en route
(HOME / ".bash_history").touch()
import builtins  # noqa: E402
builtins.input = lambda invite="": "Pixel"
app.creer_si_besoin()
_tick = explo.tick
explo.tick = lambda st, sp, proba=0, jeu=0, lignes=(): _tick(st, sp, proba, 0, lignes)   # pas de monstre au hasard
core.modifier(lambda s: (s["config"].__setitem__("fenetre_dressage", False),
                         tirage.ranger_graines(s, [{"id": f"{tirage.jour_local()}.abcdef123456", "valeur": GRAINE}])))
avant = fichiers_hors_terrain()

print("1. Chapitre 1 : le réveil")
st = tape("date")
verifier(h(st)["chap"] == "reveil" and lecon(st) == ("t0", 0), f"nouvelle partie : chapitre 1, leçon {lecon(st)}")
verifier(not T.exists(), "pas encore de terrain (la vieille porte apparaît avec la leçon 2)")
niveau(2)
for c in ("pwd", "ls", "cd ~"):
    st = tape(c)
verifier(lecon(st) == ("reveil1", 0), f"« Où suis-je ? » finie → {lecon(st)}")
verifier((T / "vestibule" / "oeuf_tout_chaud.txt").is_file(), "la vieille maison est là : vestibule/oeuf_tout_chaud.txt")
ecran = texte(app.render(st, 0, True))
verifier("Chapitre 1 · Le réveil" in ecran and "La vieille porte" in ecran, "l'écran montre le chapitre et la leçon")
st = tape("cd terrain_terminagotchi")
verifier(lecon(st) == ("reveil1", 1), "cd terrain_terminagotchi : entré dans la grande salle (vu par le dossier courant)")
st = tape("ls")
st = tape("ls")
verifier(lecon(st) == ("reveil1", 2), "ls dans la grande salle")
st = tape("cd vestibule")
st = tape("ls")
verifier(histoire.fini(st, "reveil") and h(st)["chap"] == "nid", "l'œuf est trouvé : chapitre 1 fini, chapitre 2")
verifier("CRAC" in bulles(st), "texte de fin du chapitre dit par la créature")
verifier("veilleuse" in st["quetes"]["objets"], "récompense du chapitre : une veilleuse")

print("2. Chapitre 2 : le nid")
niveau(3)
st = tape("mkdir nid")
verifier(lecon(st) == ("nid0", 0) and "pas dans la bonne pièce" not in bulles(st), f"{lecon(st)} : il faut d'abord reculer")
subprocess.run(["rmdir", str(T / "vestibule" / "nid")])
st = tape("cd ..")
verifier(lecon(st) == ("nid0", 1), "cd .. : retour dans la grande salle")
st = tape("mkdir nid")
st = tape("touch nid/lit.txt")
verifier("nid0" in h(st)["faits"] and "Bâtisseur" in st["skills"], "le nid et le lit (compétence Bâtisseur)")
verifier(explo.debloque(st), "les monstres peuvent arriver")
niveau(4)
st = tape("echo pome > nid/repas.txt")
verifier("pomme" in (st.get("indice_lecon") or ""), "« pome » : l'indice de toujours marche dans l'histoire")
st = tape("echo pomme > nid/repas.txt")
st = tape("cat nid/repas.txt")
verifier(histoire.fini(st, "nid") and histoire.chapitre_courant(st) is None, "chapitre 2 fini : aucune aile imposée")
ecran = texte(app.render(dict(st, dressage=None), 0, True))     # (le premier monstre vient d'arriver)
verifier("Quelle aile réveiller" in ecran, "l'écran propose de choisir une aile")
verifier(all((T / p).is_dir() for p in maison.AILES) and not (T / "coeur").exists(),
         "les 7 portes des ailes sont posées (pas encore le cœur)")

print("3. Liberté : on entre dans la cave")
niveau(5)
st = tape("cd cave")
verifier(h(st)["chap"] == "cave" and lecon(st) == ("cave0", 1), f"entrer dans la cave la choisit (et l'entrée est validée) : {lecon(st)}")
verifier("Démons" in bulles(st), "texte d'ouverture du chapitre (les Démons)")
st = tape("whoami")
st = tape("sudo -h")
verifier(lecon(st) == ("t3", 0), f"whoami, sudo -h (expliqué) → {lecon(st)}")
st = tape("ls -l nid")
verifier(lecon(st) == ("t3", 0) and "nid" in (st.get("indice_lecon") or "") + bulles(st) or lecon(st) == ("t3", 1),
         "ls -l nid depuis la cave : pas au bon endroit")
st = tape("cd ..")
st = tape("ls -l nid")
st = tape("chmod 444 nid/repas.txt")
verifier(lecon(st) == ("t3", 2), "chmod 444 : le cadenas est posé")
verifier(histoire.famille_attiree(st) == "Démons", "pendant la cave, les Démons sont attirés (chmod a été goûtée)")


def tirages(s):
    from tg import dressage
    s["compte"]["apparitions"] = {}
    vus = []
    for i in range(41):
        explo.spawn(s)
        v = s["sauvages"][-1]["ind"]
        if i == 0:                      # (le tout premier monstre essaie plusieurs compteurs : on le met de côté)
            s["captures"].append(dict(v, id="essai"))
        else:
            vus.append(v)
        dressage.abandonner(s)
        s["sauvages"] = []
    s["captures"] = [c for c in s["captures"] if c.get("id") != "essai"]
    s["_tir"] = vus


st = core.modifier(tirages)
vus = st.pop("_tir")
verifier(all(v.get("attire") == "Démons" for v in vus), "chaque apparition déclare la famille attirée (champ attire)")
verifier(all(tirage.tirer(GRAINE, v["n"], False, v.get("attire"))[1].items() <= v.items() for v in vus),
         "et reste vérifiable : (graine, compteur, attire) refait exactement le même individu")
from tg import bestiaire as B  # noqa: E402
n_dem = sum(1 for v in vus if B.espece(v["espece"])["famille"] == "Démons")
verifier(n_dem >= 6, f"les Démons sortent plus souvent : {n_dem}/40")
core.modifier(lambda s: s.__setitem__("sauvages", []))
st = tape("echo poire >> nid/repas.txt")
verifier(histoire.fini(st, "cave") and "gardien_des_cles" in st["quetes"]["titres"], "la cave est réveillée : titre « Gardien des clés »")
verifier((T / "nid" / "decorations" / "cadenas_dore.txt").is_file(), "objet gagné : nid/decorations/cadenas_dore.txt")
verifier(histoire.famille_attiree(st) is None, "plus de chapitre en cours : plus d'attirance d'histoire")

print("   … changer d'aile sans rien perdre")
st = tape("cd grenier")
verifier(h(st)["chap"] == "grenier", "cd grenier : le grenier est choisi")
st = tape("ls -R")
verifier(lecon(st) == ("grenier0", 2), "tree (ou ls -R) : le plan du grenier")
print("  " + app.commande_histoire("aile", ["tour"]))
st = core.load()
verifier(h(st)["chap"] == "tour" and h(st)["pas"].get("grenier0") == 2, "tg aile tour : l'étape du grenier est gardée")
st = tape("cd ../tour")
verifier(lecon(st) == ("tour0", 1), "dans la tour")
print("  " + app.commande_histoire("aile", ["grenier"]))
st = tape("cd ../grenier")
verifier(lecon(st) == ("grenier0", 2) and h(st)["pas"].get("tour0") == 1, "retour au grenier : on reprend à l'ours")
st = tape("mv fouillis/ours_en_peluche.txt ../nid/")
verifier(lecon(st) == ("t4", 0), "l'ours est au nid")

print("4. Une pièce secrète")
st = tape("cd ../vestibule")
st = tape("cat lettre_de_bienvenue.txt")
verifier("q01" in st["quetes"]["actives"], "lire la lettre de bienvenue accepte la quête")
st = tape("ls -a")
st = tape("cd .placard_secret")
verifier("q01" in st["quetes"]["finies"] and "q02" in st["quetes"]["finies"], "cd .placard_secret : la pièce secrète est trouvée")
verifier(quetes.secrets(st)[0] == 1, f"pièces secrètes : {quetes.secrets(st)}")
verifier("fouineur" in st["quetes"]["titres"], "titre « Fouineur »")

print("5. Une quête d'habitant : les chaussettes de Mousseline")
st = tape("cd ~/terrain_terminagotchi/grenier")
st = tape("cat habitant_mousseline.txt")
verifier("q11" in st["quetes"]["actives"], "Mousseline demande un service")
r = subprocess.run(["bash", "-c", 'find . -name "chaussette*"'], cwd=terminal[0], capture_output=True, text=True, env=ENV)
trouvees = r.stdout.split()
verifier(len(trouvees) == 3, f"find trouve les 3 chaussettes (même dans un coin caché) : {trouvees}")
st = tape('find . -name "chaussette*"')
for c in trouvees:
    st = tape(f"mv {c} panier/")
verifier("q11" in st["quetes"]["finies"] and "pelote" in st["quetes"]["objets"], "chaussettes rangées : quête finie, une pelote de laine")

print("6. Le tableau des annonces, la quête du jour, suivre une quête")
st = tape("cat ~/terrain_terminagotchi/vestibule/tableau_des_annonces.txt")
gen = [g for g in st["quetes"]["offertes"]]
verifier(len(gen) == 3 and all(g in st["quetes"]["actives"] for g in gen), f"3 quêtes générées acceptées : {gen}")
jour = (st["quetes"].get("jour") or {}).get("id")
verifier(jour and jour in st["quetes"]["actives"], f"une quête du jour : {jour}")
g1 = st["quetes"]["gen"][gen[0]]
print("   modèle :", g1["m"], g1["p"], "·", quetes.titre(st, gen[0]))
p = g1["p"]
faire = {"perdu": lambda: f"mv $(find ~/terrain_terminagotchi/{p['piece']} -name {p.get('fichier')}) ~/terrain_terminagotchi/nid/",
         "construire": lambda: f"mkdir ~/terrain_terminagotchi/{p['piece']}/{p.get('nom')}",
         "copie": lambda: f"mkdir -p ~/terrain_terminagotchi/nid/copies && cp ~/terrain_terminagotchi/{p['piece']}/{p.get('fichier')} "
                          "~/terrain_terminagotchi/nid/copies/",
         "compter": lambda: f"ls ~/terrain_terminagotchi/{p['piece']}/{p.get('tas')} | wc -l > ~/terrain_terminagotchi/nid/{p.get('reponse')}",
         "proteger": lambda: f"chmod 444 ~/terrain_terminagotchi/{p['piece']}/{p.get('fichier')}",
         "mot": lambda: f"echo {p.get('mot')} > ~/terrain_terminagotchi/nid/{p.get('reponse')}"}[g1["m"]]()
st = tape(faire)
verifier(gen[0] in st["quetes"]["finies"], f"quête générée réussie ({g1['m']})")
verifier(len(st["quetes"]["offertes"]) == 3 and gen[0] not in st["quetes"]["offertes"], "une nouvelle annonce la remplace")
num = quetes.numerotees(st)
print("  " + app.commande_histoire("quetes", ["suivre", str(num.index(gen[1]) + 1)]))
st = core.load()
verifier(st["quetes"]["suivie"] == gen[1], "quetes suivre N")
verifier("👣" in texte(app.render(dict(st, dressage=None), 0, True)), "la quête suivie s'affiche sur l'écran principal")
graines = {quetes.generer(st, f"g{i}", 5)["m"] + str(sorted(quetes.generer(st, f"g{i}", 5)["p"].items())) for i in range(30)}
verifier(len(graines) > 15, f"le générateur varie ({len(graines)} quêtes différentes sur 30)")
autre = dict(st, partie="abcd1234")
verifier(quetes.generer(autre, "g1", 5) != quetes.generer(st, "g1", 5) or quetes.generer(autre, "g2", 5) != quetes.generer(st, "g2", 5),
         "une autre partie a d'autres quêtes (graine par partie)")
verifier(set(quetes.modeles(5)) < set(quetes.modeles(12)), "la difficulté des quêtes générées suit le niveau")

print("7. La carte et le journal")
st = tape("cat /etc/hostname")
verifier("terres sauvages" in bulles(st), "lire /etc/hostname : avertissement des terres sauvages (lecture seule)")
carte = app.commande_histoire("carte", [])
print("\n".join("     " + l for l in carte.split("\n")))
c = texte(carte)
verifier("Grenier" in c and "Cave" in c and "Tour" in c, "pièces visitées révélées")
verifier("Dortoir" not in c and "░░░░" in c, "pièces jamais visitées dans le brouillard")
verifier("◉" in c and "★" in c and "✓" in c, "◉ tu es ici, ★ quêtes, ✓ réveillée")
verifier("Terres sauvages" in c, "les terres sauvages apparaissent sur la carte")
verifier(len(maison.verifier_largeur(maison.carte(core.load()))) == 1, "toutes les lignes du plan ont la même largeur")
core.modifier(lambda s: s["sauvages"].append({"f": "x", "e": next(e["nom"] for e in B.publiques() if e["famille"] == "Célestes"),
                                              "zone": "nuage", "shiny": False, "v": "classique"}))
verifier("🐾" in texte(maison.carte(core.load())), "🐾 : un monstre Céleste est là (dans la tour, visitée)")
core.modifier(lambda s: s.__setitem__("sauvages", []))
j = texte(app.commande_histoire("quetes", []))
print("\n".join("     " + l for l in j.split("\n")[:14]))
verifier("Quête principale" in j and "Quêtes secondaires en cours" in j and "Terminées" in j, "le journal a ses 3 parties")
verifier("1. " in j and "[du jour]" in j, "quêtes numérotées, quête du jour marquée")
lex = texte(app.lexique.lignes(core.load()))
verifier("Carnet d'aventure" in lex and "📖 La cave" in lex and "📖 Le réveil" in lex, "le carnet range chaque commande avec son chapitre")
verifier("Gardien des clés" in lex and "Souvenirs" in lex, "les souvenirs (titres, objets) sont dans le carnet")

print("8. Le cœur et Abyssor")
verifier(not histoire.ouvert(core.load(), "coeur"), "le cœur est fermé (1 aile réveillée)")
core.modifier(lambda s: s["histoire"]["ailes"].extend(["bibliotheque", "machines", "dortoir", "atelier"]))
st = tape("cd ~/terrain_terminagotchi")
verifier(histoire.ouvert(st, "coeur") and (T / "coeur" / "message_brouille.txt").is_file(), "5 ailes : le cœur s'ouvre (et ses meubles)")
verifier("ihcto" not in (T / "coeur" / "message_brouille.txt").read_text() and
         subprocess.run(["rev", str(T / "coeur" / "message_brouille.txt")], capture_output=True, text=True, env=ENV,
                        timeout=10).stdout.startswith("Le cœur"),
         "le message brouillé se lit avec rev")
core.modifier(lambda s: (s["histoire"]["faits"].extend(["coeur0", "coeur1"]), histoire.choisir(s, "coeur"),
                         s.__setitem__("xp", 10 * 11 ** 2)))
st = tape("cat coeur/.porte_secrete/abyssor_dort.txt")
n = histoire.traces_abyssor()
r = subprocess.run(["bash", "-c", "grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l"], capture_output=True, text=True, env=ENV)
verifier(3 <= n <= 6 and int(r.stdout.strip()) == n, f"Abyssor a laissé {n} griffures (grep -rl | wc -l dit {r.stdout.strip()})")
st = tape("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l")
st = tape(f"echo {n + 1} > coeur/reponse.txt")
verifier(lecon(st) == ("coeur2", 2) and "nombre" in (st.get("indice_lecon") or ""), "mauvais nombre : Abyssor secoue la tête")
st = tape("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l > coeur/reponse.txt")
verifier(histoire.fini(st, "coeur"), "bonne réponse : le cœur bat, la maison est réveillée")
verifier("La maison est réveillée" in texte(app.render(dict(st, dressage=None), 0, True)), "écran de fin")

print("9. Migration des anciennes sauvegardes")


def ancienne(**k):
    s = core.migrate(core.new_state("Vieux"))
    s.update(k)
    s.pop("histoire", None)
    return histoire.migrer(s)


s = ancienne(lesson=5, step=1, arbre={"Réseau": 1, "Git": 3}, branche="Réseau",
             skills=["Boussole", "Bâtisseur", "Inspecteur", "Gardien", "Nettoyeur", "Radar", "Archiviste"], seen=["ls", "git"])
hh = s["histoire"]
verifier({"t0", "reveil1", "nid0", "nid1", "t3", "t4", "tour0", "git0", "git1", "git2"} <= set(hh["faits"]),
         "tronc commun + branches → leçons faites dans les chapitres")
verifier({"reveil", "nid"} <= set(hh["ailes"]) and hh["chap"] == "tour" and lecon(s) == ("reseau1", 1),
         f"branche Réseau en cours (Le facteur, étape 2) → la tour, même étape : {hh['chap']} {lecon(s)}")
verifier(hh["carnet"].get("git") == "avant", "carnet : les commandes d'avant sont rangées « avant l'histoire »")
s = ancienne(lesson=3, step=1, skills=["Boussole", "Bâtisseur", "Inspecteur"])
verifier(s["histoire"]["chap"] == "cave" and s["histoire"]["pas"].get("t3") == 1 and lecon(s) == ("cave0", 0),
         "en pleine leçon des droits → la cave (l'étape chmod est gardée pour plus tard)")
s = ancienne(lesson=2, step=2)
verifier(s["histoire"]["chap"] is None and "nid1" in s["histoire"]["faits"] and s["histoire"]["pas"].get("biblio1") == 0
         and histoire.fini(s, "nid"), "grep en cours : le garde-manger est fini (le grep revient à la bibliothèque)")
s = ancienne(lesson=1, step=1)
verifier(s["histoire"]["chap"] == "reveil" and lecon(s) == ("reveil1", 0), "en train de construire le terrain → la vieille porte")
s = ancienne(lesson=0, step=0)
verifier(lecon(s) == ("t0", 0) and not s["histoire"]["faits"], "toute nouvelle partie : rien de fait")
# une vraie sauvegarde d'avant, dans le fichier : la première étape de jeu la range
vieille = core.load()
vieille.pop("histoire")
vieille.pop("quetes")
vieille.update(lesson=4, step=2, arbre={"Système": 2}, branche=None)
core.save(vieille)
st = tape("date")
verifier("histoire" in st and "systeme1" in h(st)["faits"] and "dortoir0" in h(st)["faits"],
         "sauvegarde d'avant lue depuis le fichier : rangée dans les chapitres au premier passage")
verifier(h(st)["chap"] == "grenier" and lecon(st) == ("grenier0", 0) and h(st)["pas"].get("t4") == 2,
         f"leçon « Grand ménage » en cours → le grenier, étape rm gardée : {lecon(st)}")

print("10. Sécurité et langues")
apres = fichiers_hors_terrain()
nouveaux = sorted(x for x in apres - avant if not x.endswith(".bash_history"))
verifier(not nouveaux, f"rien d'écrit hors du terrain ({nouveaux[:3]})")
cles = set()
for c in histoire.CHAPITRES:
    cles |= {f"hist.{c['id']}.{x}" for x in ("titre", "court", "debut", "fin")}
for lid, d in list(histoire.NOUVELLES.items()) + [(k, {"titre": None, "steps": v}) for k, v in histoire.EXPERT.items()]:
    if d["titre"]:
        cles.add(d["titre"])
    for s_ in d["steps"]:
        for k in ("dit", "bravo", "astuce"):
            v = s_.get(k)
            if v:
                cles.add(v[0] if isinstance(v, tuple) else v)
for q in quetes.QUETES:
    cles |= {f"qu.{q['id']}.titre", f"qu.{q['id']}.texte"}
objets = {q["objet"] for q in quetes.QUETES if q["objet"]} | {c["objet"] for c in histoire.CHAPITRES} | set(quetes.OBJETS_PERDUS)
cles |= {f"qu.objet.{o}" for o in objets}
cles |= {f"qu.titre.{q['titre']}" for q in quetes.QUETES if q["titre"]} | {f"qu.titre.{c['titre']}" for c in histoire.CHAPITRES if c.get("titre")}
cles |= {f"qu.gen.{m}.{x}" for m in quetes.MODELES_FACILES + quetes.MODELES_MOYENS + quetes.MODELES_DURS for x in ("titre", "texte")}
cles |= {f"carte.piece.{p}" for p in maison.PIECES + ("grande_salle", "recoins", "sauvage", "jardin")}
cles |= {"skill.Explorateur", "skill.Héros", "skill.Explorateur.desc", "skill.Héros.desc"}
manquantes = {}
for code in langue.LANGUES:
    d = langue._charger(code)
    m = sorted(k for k in cles if k not in d)
    if m:
        manquantes[code] = m
verifier(not manquantes, f"{len(cles)} clés construites présentes dans les 14 langues"
         + (f" — manquantes : { {k: v[:3] for k, v in manquantes.items()} }" if manquantes else ""))
for code in ("fr", "en", "ja", "ar"):
    langue.definir(code)
    for k in ("hist.coeur.debut", "qu.q11.texte", "hist.entree.dit"):
        x = langue.t(k, **dict(histoire.termes(1), piece="grenier"))
        verifier("{" not in x, f"{code} : {k} rempli sans accolade oubliée")
    verifier("ABYSSOR" in langue.t("hist.meuble.griffure") and "ABYSSOR" not in langue.t("hist.meuble.abyssor"),
             f"{code} : ABYSSOR en majuscules sur les griffures seulement (l'énigme compte juste)")
langue.definir("fr")

print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
