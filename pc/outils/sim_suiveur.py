"""Test de régression « l'élève qui suit les consignes », SANS aucune triche sur l'XP (pas de niveau(n)).

    python3 pc/outils/sim_suiveur.py [dossier_temporaire]

Un enfant virtuel, sur une machine neuve et HORS LIGNE (aucune identité git, aucun réseau), tape exactement ce que
l'écran affiche : la commande de l'étape (« ➜ … »), ou, si la leçon attend un niveau (« J'ai encore faim »), la
première idée proposée. Les commandes sont vraiment lancées avec bash (HOME temporaire), la ligne est ajoutée à
~/.bash_history, puis le jeu fait son tour (app.etape), avec le dossier courant comme le crochet d'invite.
Les ailes 3 à 9 sont choisies comme le ferait l'enfant : en y entrant (cd ~/terrain_terminagotchi/<lieu>).

Vérifie (programme d'apprentissage, docs/programme.md §1.8 et §3) :
  - les 10 chapitres sont finis (G-04 mur d'XP, G-07 git sans identité, G-08 curl sans réseau : aucun blocage) ;
  - aucune commande « de remplissage » en dehors de l'œuf du réveil (G-04) ;
  - `ls -a` est enseigné avant que l'exploration (les monstres) ne s'ouvre (G-05) ;
  - spammer une commande déjà goûtée ne donne plus d'XP (anti-remplissage) ;
  - les épreuves de dressage tirées n'exigent que des notions déjà rencontrées (G-06), à plusieurs moments du parcours ;
  - le Terminaworld = tout l'ordinateur (G-33) : « Voyage jusqu'à la Racine » (chapitre 1) et « Les lieux du gardien »
    (chapitre 4) sont faits en tapant ce que l'écran montre, la Racine et les lieux du système sont visités et
    dévoilés sur la carte, et rien n'est écrit hors de la zone d'aventure (à part les réglages du jeu) ;
  - chaque étape montrée a sa version « pour les grands » sous la commande (G-32).
Code de sortie 1 en cas d'échec. Les monstres sont coupés pendant le parcours (on mesure l'histoire).
"""
import builtins
import collections
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else None
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_suiveur_", dir=BASE)
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ.pop("HISTFILE", None)
# machine neuve : aucune identité git (ni globale ni système, pas de devinette par le nom de la machine)…
for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
    os.environ.pop(k, None)
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
_gitglobal = Path(os.environ["HOME"]) / ".gitconfig"
_gitglobal.write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n", encoding="utf-8")
# … et hors ligne (école, proxy, avion) : tout passe par un mandataire qui n'existe pas
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
for k in ("no_proxy", "NO_PROXY"):
    os.environ.pop(k, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg import app, core, dressage, explo, histoire, maison  # noqa: E402
from tg import bestiaire as B  # noqa: E402

HOME = Path.home()
T = core.TERRAIN
(HOME / ".bash_history").touch()
builtins.input = lambda p="": "Pixel"
app.creer_si_besoin()
_tick_explo = explo.tick
explo.tick = lambda *a, **k: None          # pas de monstres pendant le parcours : on mesure l'histoire

ok = ko = 0


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)


cwd = HOME
derniere_sortie = ""


def tape(cmd):
    """L'enfant tape une commande : « cd » change le dossier du terminal, le reste s'exécute vraiment."""
    global cwd, derniere_sortie
    m = re.match(r"^cd\s*(.*)$", cmd)
    if m:
        arg = m.group(1).strip() or "~"
        p = Path(os.path.expanduser(arg)) if arg.startswith("~") else (cwd / arg)
        if p.is_dir():
            cwd = p.resolve()
    else:
        # (C.UTF-8 pour les outils : sans locale fr installée, certains rev bouclent sur les accents)
        r = subprocess.run(["bash", "-c", cmd], cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, timeout=30, env=dict(os.environ, LC_ALL="C.UTF-8"))
        derniere_sortie = r.stdout.decode("utf-8", "replace")
    with open(HOME / ".bash_history", "a") as f:
        f.write(cmd + "\n")
    return app.etape(spontane=False, defis=False, cwd=str(cwd))


def a_taper(st, les):
    """Ce que l'écran demande : la commande de l'étape, adaptée comme le ferait l'enfant."""
    c = les["steps"][st["step"]]["cmd"]
    if c.startswith("sleep 300"):
        return "sleep 2 &"                 # (même geste, sans attendre 5 minutes)
    if c.startswith("echo ?"):             # l'énigme : la réponse est ce que la commande d'avant a affiché
        n = (derniere_sortie.strip().split() or ["0"])[-1]
        return c.replace("?", n, 1)
    return c


def hors_zone():
    """Les fichiers du HOME hors de la zone d'aventure (sans les réglages cachés du jeu, de git et du shell)."""
    out = set()
    for racine, dossiers, fichiers in os.walk(HOME):
        dossiers[:] = [d for d in dossiers if not d.startswith(".") and Path(racine, d) != T]
        out |= {os.path.join(racine, f) for f in fichiers if not f.startswith(".")}
    return out


st = app.etape(spontane=False, defis=False)
hors_avant = hors_zone()
sans_grands = []
stats = collections.Counter()
grind = collections.Counter()
blocages = []
log = []
explo_avant_ls_a = None
notions_apres = {}
suivi = None
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
for _ in range(900):
    les, _e = histoire.lecon_courante(st)
    h = histoire.h_(st)
    if explo_avant_ls_a is None and explo.debloque(st):
        explo_avant_ls_a = "all" not in st.get("options_vues", [])
    if not les:
        reste = [a for a in histoire.AILES if not histoire.fini(st, a)]
        if histoire.fini(st, "coeur") or h["chap"] in ("reveil", "nid"):
            break
        if not reste and histoire.ouvert(st, "coeur"):
            st = tape("cd ~/terrain_terminagotchi/coeur")
        elif reste:
            st = tape(f"cd ~/terrain_terminagotchi/{histoire.PAR_CHAP[reste[0]]['piece']}")
        else:
            break
        if histoire.lecon_courante(st)[0] is None:
            blocages.append(("choix", reste[:1]))
            break
        continue
    chap = les["chap"]
    if core.level(st["xp"]) < les["niveau"]:
        idees, _n = core.faim_d_apprendre(st, les["niveau"])
        c = idees[0]
        grind[chap] += 1
    else:
        c = a_taper(st, les)
        ecran = ANSI.sub("", app.render(st, 0, False))
        if "🧑 Pour les grands :" not in ecran:
            sans_grands.append((les["id"], st["step"]))
        depuis = [l for l in ecran.splitlines() if "📁" in l]      # « 📁 à taper depuis … : cd ~/… » sous la commande
        m = re.search(r"(cd ~/[^\s`]+)", (st.get("indice_lecon") or "") + " " + " ".join(depuis))
        if m and m.group(1) != c and suivi != (les["id"], st["step"]) and not c.startswith("cd ") \
                and Path(os.path.expanduser(m.group(1)[3:])).resolve() != cwd:
            suivi = (les["id"], st["step"])  # l'indice dit d'aller ailleurs d'abord (« se tape depuis… ») : il y va
            st = tape(m.group(1).strip("`"))
            log.append((chap, les["id"], st["step"], m.group(1)))
            continue
    stats[chap] += 1
    log.append((chap, les["id"], st["step"], c))
    if len(log) >= 4 and log[-1] == log[-2] == log[-3] == log[-4]:
        blocages.append(log[-1])
        print("BLOCAGE", log[-1], "dossier", cwd, "| indice :", st.get("indice_lecon"))
        break
    if explo.debloque(st) and chap not in notions_apres:      # les monstres arrivent : leurs épreuves comptent
        notions_apres[chap] = dressage.rencontrees(st)
    st = tape(c)

h = histoire.h_(st)
print("chapitres finis :", h["ailes"], "· niveau", core.level(st["xp"]), "· xp", st["xp"])
for c in stats:
    print(f"   {c:14s} commandes {stats[c]:4d}   dont remplissage (niveau requis) {grind[c]:4d}")
print("1. Le parcours complet, sans triche")
for c in ("reveil", "nid", "grenier", "cave", "bibliotheque", "machines", "dortoir", "atelier", "tour", "coeur"):
    verifier(histoire.fini(st, c), f"chapitre {histoire.PAR_CHAP[c]['n']} ({c}) fini")
verifier(not blocages, f"aucun blocage ({blocages or 'rien'})")
verifier(sum(v for k, v in grind.items() if k != "reveil") == 0,
         f"aucune commande de remplissage après le réveil (G-04) : {dict(grind)}")
verifier(grind["reveil"] <= 4, f"l'œuf : au plus 4 premières commandes avant le chapitre 1 ({grind['reveil']})")
verifier(sum(stats.values()) < 200, f"parcours guidé en {sum(stats.values())} commandes")
print("2. Les blocages techniques")
r = subprocess.run(["git", "-C", str(T / "carnet"), "log", "--format=%an"], capture_output=True, text=True)
verifier(r.returncode == 0 and "Pixel" in r.stdout, f"git : le carnet est signé au nom de la créature (G-07) : {r.stdout.strip()!r}")
r = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True)
verifier(not r.stdout.strip(), "git : la configuration globale n'est pas touchée")
verifier(h.get("colis_secours") and (T / "colis.html").is_file(), "curl sans réseau : colis de secours, pas de blocage (G-08)")
print("3. ls -a avant les monstres (G-05)")
verifier(explo_avant_ls_a is False, "l'exploration ne s'ouvre qu'après la leçon des passages secrets")
verifier("secrets" in h["faits"] and h["faits"].index("secrets") < h["faits"].index("grenier0"),
         "les passages secrets sont appris au chapitre 2")
print("3 bis. Le Terminaworld = tout l'ordinateur (G-33), la version des grands (G-32)")
verifier({"racine", "gardien"} <= set(h["faits"]) and h["faits"].index("racine") < h["faits"].index("nid0"),
         "« Voyage jusqu'à la Racine » faite au chapitre 1, « Les lieux du gardien » à la cave")
racine = [x for x in log if x[1] == "racine"]
verifier([x[3] for x in racine][:4] == ["cd /", "ls", "pwd", "cd ~"] and racine[-1][3].startswith("cd /"),
         f"la Racine : cd /, ls, pwd, cd ~, puis un chemin absolu ({[x[3] for x in racine]})")
m = maison.monde(st)
vus = {n["lieu"] for n in m if n["genre"] == "systeme" and not n["brume"]}
verifier(m[0]["lieu"] == "racine" and {"regles", "armurerie", "archives"} <= vus,
         f"sur la carte : la Racine, la salle des règles, l'armurerie, les archives dévoilées ({sorted(vus)})")
verifier(hors_zone() == hors_avant, f"rien n'est écrit hors de la zone d'aventure ({sorted(hors_zone() - hors_avant)[:3]})")
verifier(not sans_grands, f"chaque étape montrée a sa version des grands {sans_grands[:5]}")
print("4. Anti-remplissage")
st = tape("date")
avant = st["xp"]
for _ in range(5):
    st = tape("date")
verifier(st["xp"] == avant, f"5 × date : XP {avant} → {st['xp']} (aucune XP pour la répétition)")
print("5. Dressage : seulement des notions rencontrées (G-06)")
for chap, notions in notions_apres.items():
    mauvais = set()
    for e in B.publiques():
        for rar in ("commune", "rare", "légendaire"):
            for n in (0, 4, 20):
                for x in dressage.choisir_epreuves(e, False, rar, n, notions):
                    fid = dressage._fid(x)
                    if not dressage.connue(fid, notions):
                        mauvais.add(fid)
    verifier(not mauvais, f"au début de « {chap} » : aucune épreuve inconnue tirée {sorted(mauvais) or ''}")
debut = notions_apres.get("grenier", set())
pref = [dressage._fid(x) for x in dressage.choisir_epreuves(B.espece("Braisillon"), False, "légendaire", 30, debut)]
verifier(all(dressage.connue(f, debut) for f in pref) and not any(f.endswith((":archive", ":decode", ":empreinte", ":variable",
         ":chuchote", ":coeurs")) for f in pref), f"un légendaire au chapitre 3 : {pref}")
print(f"\n{ok} réussis, {ko} échoués   (HOME={HOME})")
sys.exit(1 if ko else 0)
