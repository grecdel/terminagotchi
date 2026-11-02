"""Test des effets des commandes dans le monde des biomes (pc/tg/effets.py).

    python3 pc/outils/test_effets.py            (depuis la racine du dépôt)
    python3 pc/outils/test_effets.py --ecrire   (réécrit donnees/effets/vecteurs.json après un changement VOULU)

1. Les vecteurs communs donnees/effets/vecteurs.json : Python les redonne exactement (Kotlin : tests/jvm/Monde.kt,
   JavaScript : site/test/test.mjs).
2. Un effet ne ment jamais : sur un vrai petit terrain (dossier temporaire), on lance de vraies commandes avec bash et
   l'effet suit ce qui a VRAIMENT changé ; une commande ratée ne change rien et donne un signe doux (refus).
3. PowerShell : les cmdlets donnent les mêmes effets ; les rafales sont groupées ; le réglage tous / essentiels / aucun ;
   l'explication n'est dite que 3 fois ; la photo du terrain reste bornée (un terrain géant ne ralentit pas le jeu).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
from tg import effets as E  # noqa: E402

ok = ko = 0


def verif(c, msg):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
        print("  ✗", msg)


VEC = RACINE / "donnees" / "effets" / "vecteurs.json"
if "--ecrire" in sys.argv:
    VEC.write_text(json.dumps(E.vecteurs(), ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print("vecteurs réécrits")

print("1. Les vecteurs communs")
attendu = json.loads(VEC.read_text(encoding="utf-8"))
calcule = json.loads(json.dumps(E.vecteurs(), ensure_ascii=False, sort_keys=True))
verif(len(attendu) == len(calcule), "même nombre de cas")
for a, c in zip(attendu, calcule):
    verif(a == c, f"vecteur « {a['ligne']} »")
print(f"   {len(attendu)} commandes")

print("2. Un vrai petit terrain, de vraies commandes (bash)")
tmp = Path(tempfile.mkdtemp(prefix="tg_effets_"))
T = tmp / "terrain_terminagotchi"
(T / "biome/feu/parcelle_1").mkdir(parents=True)
(T / "biome/plante/parcelle_1").mkdir(parents=True)
(T / "biome/plante/parcelle_1/rose.fleur").write_text("rose\n")
(T / "biome/plante/parcelle_1/mot.txt").write_text("bonjour\n")
cwd = [T / "biome"]


def lancer(ligne):
    avant = E.photo(T, cwd[0])
    time.sleep(0.01)
    p = subprocess.run(["bash", "-c", f"{ligne}\n__c=$?\necho \"@@$PWD\"\nexit $__c"], cwd=cwd[0], capture_output=True, text=True,
                       env=dict(os.environ, LC_ALL="C"))
    lignes = p.stdout.strip().split("\n")
    if lignes and lignes[-1].startswith("@@"):
        cwd[0] = Path(lignes[-1][2:])
    apres = E.photo(T, cwd[0])
    return E.evenements(ligne, avant, apres, p.returncode, "\n".join(lignes[:-1]) + "\n" + p.stderr)


def types(evs):
    return [e["type"] for e in evs]


e = lancer("mkdir feu/parcelle_2")
verif(types(e) == ["dossier+"] and e[0]["parcelle"], f"mkdir : une parcelle de plus ({e})")
e = lancer("mkdir feu/parcelle_2")
verif(types(e) == ["refus"] and e[0]["raison"] == "existe", f"mkdir déjà là : refus doux « existe » ({e})")
e = lancer("touch plante/parcelle_1/sapin.arbre")
verif(types(e) == ["objet+"] and e[0]["via"] == "touch", f"touch : un objet posé ({e})")
e = lancer("touch plante/parcelle_1/sapin.arbre")
verif(types(e) == ["touche"], f"touch encore : seulement l'heure change ({e})")
e = lancer("echo coucou")
verif(e == [], f"echo sans redirection : rien dans le monde (un effet ne ment jamais) ({e})")
e = lancer("echo Salut > plante/parcelle_1/mot.txt")
verif(types(e) == ["ecrit"] and e[0]["mode"] == ">", f"> : le panneau est effacé puis écrit ({e})")
e = lancer("echo Encore >> plante/parcelle_1/mot.txt")
verif(types(e) == ["ecrit"] and e[0]["mode"] == ">>", f">> : une ligne en plus ({e})")
e = lancer("cd plante/parcelle_1")
verif(types(e) == ["cd"] and e[0]["vers"] == "biome/plante/parcelle_1", f"cd : on se déplace ({e})")
e = lancer("mv sapin.arbre ../../feu/parcelle_1/")
verif(types(e) == ["deplace"], f"mv : l'objet déménage ({e})")
e = lancer("cp rose.fleur tulipe.fleur")
verif(types(e) == ["copie"], f"cp : une copie ({e})")
e = lancer("rm *.fleur")
verif(types(e) == ["jokers", "objet-", "objet-"], f"rm *.fleur : les jokers s'allument, deux objets partent ({e})")
e = lancer("rm absent.txt")
verif(types(e) == ["refus"] and e[0]["raison"] == "introuvable", f"rm d'un absent : « ? » ({e})")
e = lancer("chmod a-w ../../feu/parcelle_2")
verif(types(e) == ["droits"], f"chmod : la cloche et les cadenas ({e})")
if os.geteuid() != 0:
    e = lancer("touch ../../feu/parcelle_2/x.fleur")
    verif(types(e) == ["refus"] and e[0]["raison"] == "droits", f"touch refusé : cadenas, rien ne change ({e})")
lancer("chmod u+w ../../feu/parcelle_2")
e = lancer("ls -a")
verif(types(e) == ["ls"] and e[0]["caches"], f"ls -a : le rideau ({e})")
e = lancer("cat mot.txt | grep a | wc -l")
verif(types(e) == ["tuyau"] and e[0]["etapes"] == ["cat", "grep", "wc"], f"tuyau : le petit laboratoire ({e})")
e = lancer("for i in 1 2 3 4 5 6 7 8 9 10; do touch f$i.fleur; done")
verif(types(e) == ["groupe"] and e[0]["n"] == 10, f"une rafale : un seul effet groupé ({e})")
# les effets secondaires (2 novembre) : la caisse, le lien, du, df, gzip, mktemp, git, trap — toujours sur le vrai changement
(T / "biome/feu/parcelle_1/geyser.pierre").write_text("pfff\n")
cwd[0] = T / "biome/feu/parcelle_1"
e = lancer("tar -czf sac.tar.gz geyser.pierre")
verif(types(e) == ["caisse"] and e[0]["quoi"] == "ferme" and e[0]["n"] == 1, f"tar -c : la caisse se ferme sur une copie ({e})")
e = lancer("tar -xzf sac.tar.gz -C ../parcelle_2")
verif(types(e) == ["caisse"] and e[0]["quoi"] == "ouvre" and e[0]["chemins"] == ["biome/feu/parcelle_2/geyser.pierre"],
      f"tar -x : les objets sortent de la caisse ({e})")
e = lancer("tar -tzf sac.tar.gz")
verif(types(e) == ["caisse"] and e[0]["quoi"] == "voir" and e[0]["n"] == 1, f"tar -t : on regarde dans la caisse ({e})")
e = lancer("ln -s ../parcelle_2/geyser.pierre raccourci")
verif(types(e) == ["lien"] and e[0]["cible"] == "biome/feu/parcelle_2/geyser.pierre" and not e[0]["mort"],
      f"ln -s : le fil du raccourci ({e})")
e = lancer("ln -s absent mort")
verif(types(e) == ["lien"] and e[0]["mort"], f"ln -s vers rien : le fil est cassé ({e})")
e = lancer("du -s")
verif(types(e) == ["taille"] and e[0]["elements"][0][1] > 0, f"du : la colonne ({e})")
e = lancer("df .")
verif(types(e) == ["disque"] and isinstance(e[0]["pourcent"], int), f"df : le réservoir ({e})")
e = lancer("gzip -f sac.tar.gz")
verif(types(e) == ["caisse"] and e[0]["quoi"] == "serre", f"gzip : la caisse se serre ({e})")
e = lancer("mktemp -p .")
verif(types(e) == ["sablier"] and e[0]["chemin"], f"mktemp : le sablier sur le nouvel objet ({e})")
e = lancer("trap 'echo' EXIT")
verif(types(e) == ["filet"], f"trap : le filet ({e})")
e = lancer("ls --help > /dev/null")
verif(types(e) == ["grimoire"], f"--help : le grimoire, pas l'effet de ls ({e})")
if subprocess.run(["sh", "-c", "command -v git"], capture_output=True).returncode == 0:
    g = "git -c user.name=t -c user.email=t@temps.invalid -c init.defaultBranch=main"
    e = lancer(f"{g} init -q album")
    verif(types(e) == ["album"] and e[0]["quoi"] == "neuf", f"git init : un album tout neuf ({e})")
    cwd[0] = cwd[0] / "album"
    lancer("echo un > page.txt")
    e = lancer("git add page.txt")
    verif(types(e) == ["etoile"], f"git add : l'étoile ({e})")
    e = lancer(f"{g} commit -qm un")
    verif(types(e) == ["photo"], f"git commit (avec -c) : la photo ({e})")
    e = lancer("git switch -q -c essai")
    verif(types(e) == ["branche"] and e[0]["quoi"] == "nouvelle", f"git switch -c : une branche ({e})")
    lancer(f"echo deux >> page.txt && {g} commit -qam deux")
    e = lancer("git switch -q main")
    verif("branche" in types(e) and e[-1]["quoi"] == "change", f"git switch : on change de monde ({e})")
    e = lancer(f"{g} merge -q essai")
    verif("fusion" in types(e), f"git merge : les branches se rejoignent ({e})")
    e = lancer("git log --oneline")
    verif(types(e) == ["album"] and e[0]["n"] == 2, f"git log : l'album, 2 photos ({e})")
    lancer("rm page.txt")
    e = lancer("git restore page.txt")
    verif(types(e) == ["rembobine"], f"git restore : l'horloge à l'envers ({e})")
    cwd[0] = cwd[0].parent
cwd[0] = T / "biome/plante/parcelle_1"
e = lancer("cd ../.. && rm -r plante")
verif("dossier-" in types(e), f"rm -r : la région part ({e})")

print("3. PowerShell, réglage, explications, photo bornée")
av = {"cwd": "biome", "f": {"biome": ["d", 0, 1, 493]}}
ap = {"cwd": "biome", "f": {"biome": ["d", 0, 1, 493], "biome/feu": ["d", 0, 2, 493]}}
verif(types(E.evenements("New-Item -ItemType Directory feu", av, ap, 0)) == ["dossier+"], "New-Item = mkdir")
verif(types(E.evenements("md feu", av, ap, 0)) == ["dossier+"], "md = mkdir")
verif(types(E.evenements("Remove-Item feu", ap, av, 0)) == ["dossier-"], "Remove-Item = rm")
verif(E.evenements("Set-Location feu", ap, dict(ap, cwd="biome/feu"), 0)[0]["type"] == "cd", "Set-Location = cd")
evs = E.evenements("ps", av, av, 0)
verif(len(E.filtrer(evs, "tous")) == 1 and not E.filtrer(evs, "essentiels") and not E.filtrer(evs, "aucun"),
      "réglage : tous / essentiels / aucun")
cpt, dites = {}, 0
for _ in range(6):
    k = E.a_dire(cpt, evs)
    if k:
        dites += 1
        cpt[k] = cpt.get(k, 0) + 1
verif(dites == E.DITS_MAX == 3, f"l'explication n'est dite que 3 fois ({dites})")
grand = tmp / "grand"
for i in range(40):
    d = grand / f"d{i}"
    d.mkdir(parents=True)
    for j in range(30):
        (d / f"f{j}").write_text("x")
t0 = time.perf_counter()
ph = E.photo(grand, grand)
dt = time.perf_counter() - t0
verif(len(ph["f"]) <= E.MAX_PHOTO, f"photo bornée ({len(ph['f'])} entrées)")
verif(dt < 0.5, f"photo rapide ({dt * 1000:.0f} ms)")
verif(E.evenements("", av, ap, 0) == [] and E.evenements("ls", None, None, 0) == [], "lignes vides : rien, sans erreur")
subprocess.run(["chmod", "-R", "u+w", str(tmp)])

print(f"{'✅' if ko == 0 else '❌'} Effets : {ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
