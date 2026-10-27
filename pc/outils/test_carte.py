"""Test de la carte qui pousse (PC) : le vrai terrain dessiné à côté de `tree`, dévoilé au fil des découvertes.

    python3 pc/outils/test_carte.py               (crée son propre HOME temporaire)
    python3 pc/outils/test_carte.py --ansi DOSSIER   écrit aussi les 3 étapes en couleur (DOSSIER/pc_N.ansi)

  1. juste éclos : le camp de base, les lieux de l'histoire dans la brume (░ ???), rien de caché ;
  2. après mkdir : les lieux visités se dévoilent, un nouveau lieu brille (✨ nouveau !) puis plus,
     « la carte a poussé : + cabane/ » passe dans l'invite (journal), ◉ suit le dossier courant ;
  3. la porte du monde, ses régions (couleur et emoji de donnees/biomes.json), les parcelles ;
     les passages secrets n'apparaissent qu'après `ls -a` ; `tree` dévoile tout un coin ;
  4. les objets (note, recette, carte postale, coffre) ; un dossier géant n'est pas exploré ;
  5. la légende ne liste que les commandes rencontrées ; mode colonnes aligné dans les 14 langues ;
     mode texte (terminal étroit ou sans couleur) ; les textes existent dans les 14 langues ;
  6. le Terminaworld = tout l'ordinateur (G-33) : la carte part de la Racine /, les lieux du système sont des
     repères dans la brume tant qu'on ne les a pas visités, puis le village, ton camp de base, la zone d'aventure ;
     ◉ et le panneau « la Racine → … » suivent l'enfant partout ; visiter un lieu du système le présente
     (enfant + grands) ; écrire hors de la zone d'aventure : un avertissement gentil, rien n'est bloqué ni écrit
     par le jeu ; le carnet des lieux (lexique) avec la version des grands.
Le même modèle est testé sur Android par tests/jvm/Carte.kt.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_carte_")
os.environ["LANG"] = "fr_FR.UTF-8"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import core, histoire, langue, maison  # noqa: E402

ok = ko = 0
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
T = core.TERRAIN
SORTIE = sys.argv[sys.argv.index("--ansi") + 1] if "--ansi" in sys.argv else None


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def texte(x):
    return ANSI.sub("", "\n".join(x) if isinstance(x, list) else x)


def tape(st, ligne, ou=None):
    """L'enfant tape une ligne (déjà exécutée) depuis le dossier ou (relatif au terrain)."""
    cmd = core.first_word(ligne)
    if cmd and cmd not in st["seen"]:
        st["seen"].append(cmd)
    maison.suivre(st, [ligne], str(T / ou) if ou is not None else None)


def ligne_de(ns, r):
    return next((n for n in ns if n["rel"] == r), None)


def montrer(st, nom):
    c = maison.carte(st, "colonnes")
    print("\n".join("     " + l for l in c))
    if SORTIE:
        Path(SORTIE).mkdir(parents=True, exist_ok=True)
        (Path(SORTIE) / f"pc_{nom}.ansi").write_text("\n".join(c) + "\n", encoding="utf-8")
    return c


langue.definir("fr")
st = core.new_state("Pixel")
st["seen"] = []

print("1. Les régions viennent de donnees/biomes.json")
bio = json.loads((RACINE / "donnees" / "biomes.json").read_text(encoding="utf-8"))
verifier([b["id"] for b in bio["types"]] == list(maison.BIOMES), "les 9 types de biome, dans le même ordre")
verifier(all(maison.BIOMES[b["id"]][1:] == (b["couleurs"]["principale"], b["couleurs"]["sombre"], b["couleurs"]["claire"])
             for b in bio["types"]), "mêmes couleurs (principale, sombre, claire)")
verifier(all(langue.largeur(maison.BIOMES[b][0]) == 2 for b in maison.BIOMES), "emojis larges de 2 colonnes (cases alignées)")
verifier(all(langue.largeur(e) == 2 for e in list(maison.EMOJIS.values()) + list(maison.ICONES.values())),
         "toutes les icônes de la carte font 2 colonnes")

print("2. Juste éclos")
(T / "vestibule").mkdir(parents=True)
(T / "vestibule" / "oeuf_tout_chaud.txt").write_text("chaud\n")
(T / "nid").mkdir()
(T / ".cachette").mkdir()
h = histoire.h_(st)
h["faits"].append("t0")
tape(st, "pwd", "")
ns = maison.noeuds(st)
verifier(ns[0]["genre"] == "zone" and ns[0]["ici"] and ns[0]["etiquette"] == "la zone d'aventure",
         "la zone d'aventure (~/terrain_terminagotchi) : tu es ici")
verifier(ligne_de(ns, "vestibule")["brume"] and ligne_de(ns, "vestibule")["etiquette"] == "???",
         "vestibule pas encore visité : dans la brume")
verifier(ligne_de(ns, "nid") is None, "le nid n'est pas encore posé par l'histoire : invisible")
verifier(ligne_de(ns, ".cachette") is None, "pas de passage secret avant `ls -a`")
verifier(ligne_de(ns, "vestibule/oeuf_tout_chaud.txt") is None, "ce qu'il y a dans la brume reste caché")
c1 = montrer(st, "1_eclos")
verifier(len(maison.verifier_largeur(c1)) == 1, "mode colonnes : tree commence à la même colonne partout")
verifier("░░░" in texte(c1) and "✨ nouveau !" in texte(c1), "brume ░ et ✨ nouveau ! à la première carte")
verifier("`pwd`" in "\n".join(c1) and "`mkdir`" not in "\n".join(c1), "légende : pwd rencontré, pas encore mkdir")
ns = maison.noeuds(st)
verifier(not any(n["nouveau"] for n in ns), "déjà montré : plus de ✨ la fois suivante")

print("3. Après les leçons mkdir")
h["ailes"] += ["reveil", "nid"]
tape(st, "cd vestibule", "vestibule")
tape(st, "cd ..", "")
ns = maison.noeuds(st)
verifier(not ligne_de(ns, "vestibule")["brume"] and ligne_de(ns, "vestibule")["nouveau"], "vestibule visité : dévoilé (et nouveau)")
verifier(ligne_de(ns, "vestibule/oeuf_tout_chaud.txt")["genre"] == "note", "oeuf_tout_chaud.txt : une note")
verifier(ligne_de(ns, "nid")["brume"], "le nid posé, pas encore visité : brume")
(T / "cabane").mkdir()
st["log"] = []
tape(st, "mkdir cabane", "")
verifier(any("la carte a poussé : + cabane/" in x for x in st["log"]), "« 🗺 la carte a poussé : + cabane/ » dans le journal")
tape(st, "cd cabane", "cabane")
(T / "cabane" / "lit.sh").write_text("echo zzz\n")
(T / "cabane" / "photo.png").write_bytes(b"\x89PNG")
(T / "cabane" / "tresor.zip").write_bytes(b"PK")
tape(st, "touch lit.sh photo.png tresor.zip", "cabane")
ns = maison.noeuds(st)
verifier([ligne_de(ns, f"cabane/{f}")["genre"] for f in ("lit.sh", "photo.png", "tresor.zip")] == ["recette", "image", "coffre"],
         "objets : recette (.sh), carte postale (.png), coffre (le reste)")
verifier(ligne_de(ns, "cabane")["ici"] and not ns[0]["ici"], "◉ suit le dossier courant (cabane)")
verifier(ligne_de(ns, "cabane")["branches"] == "├── " and ligne_de(ns, "cabane/tresor.zip")["branches"] == "│   └── ",
         "les débuts de lignes de tree (├── │   └──)")
(T / "cabane" / "photo.png").unlink()
tape(st, "rm photo.png", "cabane")
verifier(any("rétréci : − photo.png" in x for x in st["log"]), "rm : « la carte a rétréci : − photo.png »")
c2 = montrer(st, "2_mkdir")
verifier(len(maison.verifier_largeur(c2)) == 1, "colonnes alignées")
verifier("`mkdir`" in "\n".join(c2) and "`touch`" in "\n".join(c2) and "`tree`" not in "\n".join(c2),
         "légende : mkdir et touch rencontrés, pas encore tree")

print("4. Fin de partie : régions, parcelles, passages secrets, tree")
for p in maison.AILES:
    (T / p).mkdir(exist_ok=True)
for b, n in (("feu", 2), ("eau", 1), ("plante", 1)):
    for i in range(1, n + 1):
        (T / "biome" / b / f"parcelle_{i}").mkdir(parents=True)
(T / "biome" / "feu" / "parcelle_1" / "braises.pierre").write_text("")
(T / "grenier" / ".placard").mkdir()
tape(st, "cd ~/terrain_terminagotchi/biome", "biome")
ns = maison.noeuds(st)
verifier(ligne_de(ns, "biome")["genre"] == "porte", "biome/ : la porte du monde")
verifier(ligne_de(ns, "biome/feu")["genre"] == "region" and ligne_de(ns, "biome/feu")["brume"], "biome/feu : une région, dans la brume")
tape(st, "tree", "biome")
ns = maison.noeuds(st)
verifier(not ligne_de(ns, "biome/feu")["brume"] and ligne_de(ns, "biome/feu/parcelle_2")["genre"] == "parcelle",
         "`tree` dévoile tout le coin : régions et parcelles")
verifier(ligne_de(ns, "biome/feu")["etiquette"] == "région Feu" and ligne_de(ns, "biome/feu/parcelle_1")["biome"] == "feu",
         "région Feu ; ses parcelles en prennent la couleur")
verifier(ligne_de(ns, "biome/feu/parcelle_1/braises.pierre")["genre"] == "coffre", "un objet posé dans une parcelle")
verifier(ligne_de(ns, ".cachette") is None, "toujours pas de passage secret")
tape(st, "ls -la", "")
ns = maison.noeuds(st)
verifier(ligne_de(ns, ".cachette")["genre"] == "secret", "après `ls -a` : .cachette, un passage secret")
verifier(ligne_de(ns, "grenier/.placard") is None, "grenier pas visité : son passage secret reste dans la brume")
tape(st, "cd grenier", "grenier")
h["chap"] = "grenier"
ns = maison.noeuds(st)
verifier(ligne_de(ns, "grenier/.placard")["genre"] == "secret" and "▶" in ligne_de(ns, "grenier")["marques"],
         "grenier visité : .placard apparaît ; ▶ chapitre en cours")
geant = T / "cabane" / "geant"
geant.mkdir()
for i in range(maison.TROP_GRAND + 5):
    (geant / f"f{i}").write_text("")
tape(st, "cd cabane/geant", "cabane/geant")
ns = maison.noeuds(st)
verifier(ligne_de(ns, "cabane/geant") is not None and not any(n["rel"].startswith("cabane/geant/") for n in ns),
         "un dossier géant est sur la carte, mais pas exploré")
tape(st, "cd ..", "cabane")
for i in range(20):
    (T / "cabane" / f"caillou_{i:02}.txt").write_text("")
ns = maison.noeuds(st)
suite = [n for n in ns if n["genre"] == "suite"]
verifier(len(suite) == 1 and suite[0]["suite"] > 0, f"plus de {maison.MAX_PAR_DOSSIER} entrées : « + n autres »")
for f in (T / "cabane").glob("caillou_*"):
    f.unlink()
tape(st, "cd ~/terrain_terminagotchi/biome/feu/parcelle_1", "biome/feu/parcelle_1")
c3 = montrer(st, "3_fin")
verifier(len(maison.verifier_largeur(c3)) == 1, "colonnes alignées en fin de partie")
verifier("`ls -a`" in "\n".join(c3) and "`tree`" in "\n".join(c3), "légende : ls -a et tree rencontrés")

print("5. Les 14 langues, le mode texte")
casses = []
for code in langue.LANGUES:
    langue.definir(code)
    c = maison.carte(st, "colonnes")
    if len(maison.verifier_largeur(c)) != 1:
        casses.append(f"{code} : colonnes {maison.verifier_largeur(c)}")
    if re.search(r"\{[a-z_]+\}|carte\.[a-z]", texte(c)):
        casses.append(f"{code} : texte à remplir")
langue.definir("fr")
verifier(not casses, f"14 langues : colonnes alignées, rien à remplir {casses}")
t = texte(maison.carte(st, "texte"))
verifier("├── grenier/" in t and "SEP" not in t and maison.SEP not in t and "région Feu" in t,
         "mode texte : tree annoté (sans colonnes)")
cles = [k for k in langue._charger("fr") if k.startswith(("carte.monde.", "carte.biome."))]
manque = {code: [k for k in cles if k not in langue._charger(code)] for code in langue.LANGUES}
cles += [k for k in langue._charger("fr") if k.startswith("lieu.")] + ["carte.absolu", "carte.lieu.decouvert", "carte.prudence.systeme"]
manque = {code: [k for k in cles if k not in langue._charger(code)] for code in langue.LANGUES}
verifier(len(cles) >= 70 and not any(manque.values()), f"{len(cles)} textes de la carte et des lieux dans les 14 langues")
verifier(len(st["maison"]["montres"]) <= 800 and len(st["maison"]["empreinte"]) <= 400, "la sauvegarde reste petite")

print("6. Le Terminaworld = tout l'ordinateur : la carte part de la Racine")
HOME = Path.home()


def dehors(st, ligne, cwd):
    """Une ligne tapée hors de la zone d'aventure (cwd absolu)."""
    cmd = core.first_word(ligne)
    if cmd and cmd not in st["seen"]:
        st["seen"].append(cmd)
    st["bubble"], st["bulles"] = None, []
    maison.suivre(st, [ligne], str(cwd))
    return " | ".join([(st.get("bubble") or [""])[0]] + [b[0] for b in st.get("bulles", [])])


tape(st, "cd ~/terrain_terminagotchi/grenier", "grenier")
m = maison.monde(st)
verifier(m[0]["lieu"] == "racine" and m[0]["nom"] == "/" and m[0]["prof"] == 0, "1re ligne : la Racine /")
reperes = [n for n in m if n["genre"] == "systeme"]
verifier(reperes and all(Path(n["abs"]).is_dir() for n in reperes) and {n["nom"] for n in reperes} >= {"etc", "usr"},
         f"les lieux du système qui existent ici sont des repères : {[n['nom'] for n in reperes]}")
verifier(all(n["brume"] and n["etiquette"] == "???" for n in reperes), "jamais visités : dans la brume")
camp = next(n for n in m if n["lieu"] == "camp")
zone = next(n for n in m if n["genre"] == "zone")
verifier(camp["abs"] == str(HOME) and camp["etiquette"] == "ton camp de base", "ton camp de base = ~ (le vrai dossier personnel)")
verifier(m.index(camp) < m.index(zone) and zone["prof"] == camp["prof"] + 1 and zone["nom"] == T.name,
         "la zone d'aventure est sous le camp de base")
verifier(any(n["lieu"] == "village" and n["abs"] == str(HOME.parent) for n in m), "le village = le dossier au-dessus du camp")
verifier(ligne_de(m, "grenier")["ici"] and ligne_de(m, "grenier")["prof"] == zone["prof"] + 1, "◉ dans la zone, sous la zone d'aventure")
c = texte(maison.carte(st, "texte"))
verifier(c.index("la Racine") < c.index("ton camp de base") < c.index("la zone d'aventure") < c.index("Grenier"),
         "la carte, de haut en bas : la Racine → … → ton camp → la zone d'aventure → les lieux")
verifier(f"Tu es ici : {T / 'grenier'}" in c, "le panneau donne le chemin absolu complet")
verifier("🚇 la Racine → " in c and "→ ton camp de base → la zone d'aventure → Grenier" in c, "… lu lieu par lieu, comme une ligne de métro")
verifier("part de la Racine (absolu)" in c, "absolu / relatif expliqué sous la carte")
verifier(len(maison.verifier_largeur(maison.carte(st, "colonnes"))) == 1, "mode colonnes : toujours aligné avec la Racine")
b = dehors(st, "cd /", Path("/"))
m = maison.monde(st)
verifier(m[0]["ici"] and "la Racine" in b and "Pour les grands" in b, "cd / : ◉ à la Racine, présentée (enfant + grands)")
b = dehors(st, "cat /etc/hostname", Path("/"))
etc = next(n for n in maison.monde(st) if n["nom"] == "etc")
verifier(not etc["brume"] and etc["etiquette"] == "la salle des règles" and "la salle des règles" in b,
         "cat /etc/hostname : la salle des règles se dévoile et se présente")
b = dehors(st, "cd /etc", Path("/etc"))
m = maison.monde(st)
verifier(next(n for n in m if n["nom"] == "etc")["ici"] and not any(n["ici"] for n in m if n["genre"] != "systeme"),
         "cd /etc : ◉ sur la salle des règles")
verifier("🚇 la Racine → la salle des règles" in texte(maison.carte(st, "texte")), "le panneau : la Racine → la salle des règles")
print("   … écrire hors de la zone d'aventure : un rappel gentil (le jeu ne bloque ni n'écrit rien)")
st["maison"]["prudence"] = 0
b = dehors(st, "touch essai", Path("/etc"))
verifier("lieu du système" in b and "Permission denied" in b and "Pour les grands" in b, f"touch dans /etc : « on regarde, on ne touche pas » ({b[:60]}…)")
verifier(not Path("/etc/essai").exists(), "le jeu n'a rien exécuté ni écrit : il lit seulement ce qui a été tapé")
st["maison"]["prudence"] = 0
verifier("lieu du système" in dehors(st, "echo coucou > /tmp/x.txt", HOME), "echo … > /tmp/… depuis le camp : rappel « lieu du système »")
st["maison"]["prudence"] = 0
verifier("zone d'aventure" in dehors(st, "mkdir cabane", HOME), "mkdir dans le camp de base : « seulement dans la zone d'aventure »")
st["maison"]["prudence"] = 0
verifier(dehors(st, "echo \"alias miam='sh ~/x.sh'\" >> ~/.bashrc", HOME) == "", "les réglages du camp (~/.bashrc) des leçons : pas de rappel")
st["maison"]["prudence"] = 0
verifier(dehors(st, "ls /etc > /dev/null", HOME) == "", "lire et jeter dans le trou noir (/dev/null) : pas de rappel")
st["maison"]["prudence"] = 0
verifier(dehors(st, "cp /etc/hostname ~/terrain_terminagotchi/", HOME) == "", "copier DEPUIS la salle des règles vers la zone : permis")
st["maison"]["prudence"] = 0
verifier(dehors(st, "mkdir ~/terrain_terminagotchi/cabane2", HOME) == "", "bâtir dans la zone d'aventure : aucun rappel")
from tg import lexique  # noqa: E402
lx = texte(lexique.lignes_lieux(st))
verifier(all(maison.nom_lieu(l) in lx for _c, l in maison.LIEUX_CARNET) and lx.count("Pour les grands") == len(maison.LIEUX_CARNET),
         "le carnet des lieux : chaque lieu, son image et la version des grands")

print(f"\n{ok} réussis, {ko} échoués   (HOME={os.environ['HOME']})")
sys.exit(1 if ko else 0)
