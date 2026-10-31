"""Test de la créature du bureau, du petit menu rond et de l'île (pc/tg/bureau*.py, poses.py, signaux.py) :
  1. les poses dessinées (poses.bin) : les 27 bébés de départ × 12 poses, les mêmes octets sur PC et Android, aucun
     petit point isolé qui traîne, des ancres dans l'image ; le script de génération redonne le même fichier ;
  2. l'album de chaque créature : poses dessinées pour un bébé de départ, animation procédurale sinon ;
  3. le comportement (marche, sommeil, réveil, batterie, repas, glisser), les gestes (clic, double, triple, glisser),
     le menu rond, l'île (survol, événements, discrétion), le mini-terminal ;
  4. la VIE PRIVÉE : aucune lecture du clavier, du texte tapé, des titres ou du contenu des fenêtres, aucune capture
     d'écran (PC et Android) ;
  5. le lancement automatique, les réglages, la liste de dessin et une capture simulée.

    python3 pc/outils/test_bureau.py
"""
import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
MAISON = tempfile.mkdtemp(prefix="tg_bureau_")
os.environ["HOME"] = MAISON
os.environ["XDG_CONFIG_HOME"] = os.path.join(MAISON, ".config")

from tg import bureau, bureau_scene as S, bureau_vie as V, core, langue, poses, signaux  # noqa: E402

ok = ko = 0


def verifier(c, m):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
    print(("  ✔ " if c else "  ✖ ") + m)


# ---------------------------------------------------------------- 1. poses.bin
def test_poses():
    print("Les poses dessinées")
    pc = (RACINE / "pc/tg/poses.bin").read_bytes()
    an = (RACINE / "app/src/main/assets/poses.bin").read_bytes()
    verifier(pc == an, f"poses.bin identique sur PC et Android ({len(pc) // 1024} Ko)")
    depart = json.loads((RACINE / "donnees/oeufs/depart.json").read_text(encoding="utf-8"))["depart"]
    bebes = sorted(e for l in depart.values() for e in l)
    verifier(poses.especes() == bebes, f"les {len(bebes)} bébés de départ ont leurs poses")
    tete, _ = poses.donnees()
    verifier(tete["poses"] == ["marche1", "marche2", "marche3", "marche4", "assis", "dort", "etire", "baille",
                               "sursaut", "coeur", "mange", "salut", "cligne", "bouche1", "bouche2", "bouche3"],
             "12 poses dessinées + « cligne » et la mâchoire « bouche1 » à « bouche3 » (calculées)")
    diff_cligne = 0
    for esp in bebes:
        idx, _p = poses.poses_indexees(esp)
        diff_cligne += idx["cligne"][2] != idx["assis"][2] and idx["cligne"][:2] == idx["assis"][:2]
    verifier(diff_cligne >= 20, f"« cligne » : assis les yeux fermés pour {diff_cligne} bébés sur 27")
    from scipy import ndimage  # noqa: F401  (outil de contrôle seulement)
    import numpy as np
    loin, ancres, couleurs = [], [], []
    for esp in bebes:
        idx, pal = poses.poses_indexees(esp)
        couleurs.append(len(pal) <= 255)
        for nom, (w, h, o, ax, ay) in idx.items():
            m = np.frombuffer(o, dtype=np.uint8).reshape(h, w) > 0
            ancres.append(0 <= ax <= w and 0 < ay <= h and m[0].any() and m[-1].any() and m[:, 0].any() and m[:, -1].any())
            lab, n = ndimage.label(m, structure=np.ones((3, 3)))
            if n > 1:
                tailles = ndimage.sum(m, lab, range(1, n + 1))
                corps = int(np.argmax(tailles)) + 1
                dist = ndimage.distance_transform_edt(lab != corps)
                lim = 20 if nom.startswith("marche") or nom == "assis" else 40
                for i in range(1, n + 1):
                    if i != corps and dist[lab == i].min() > lim:
                        loin.append(f"{esp}/{nom}")
    verifier(not loin, "aucun petit point isolé loin du corps" + (f" : {loin[:5]}" if loin else ""))
    verifier(all(ancres), "chaque pose est recadrée au plus juste, ancre dans l'image")
    verifier(all(couleurs), "une palette d'au plus 255 couleurs par espèce")
    try:
        sys.path.insert(0, str(RACINE / "donnees/bestiaire2/outils"))
        import poses_bureau
        refait, _ = poses_bureau.construire()
        verifier(refait == pc, "le script de génération redonne exactement poses.bin")
    except ImportError as e:
        print(f"  (génération non vérifiée : {e})")


# ---------------------------------------------------------------- 2. albums
def partie(espece="glandouille", xp=20, **kw):
    st = core.new_state("Noisette")
    core.migrate(st)
    st["espece_compagnon"] = espece
    st["xp"] = xp
    st.update(kw)
    return st


def test_albums():
    print("L'album de chaque créature")
    a = poses.album(partie())
    verifier(a.dessine and a.lisse and len(a.images("marche")) == 4, "bébé de départ : les poses dessinées (4 images de marche)")
    verifier(all(a.images(e) for e in poses.ETATS), "les 9 états ont une image")
    b = poses.album(partie(xp=500))
    verifier(not b.dessine and not b.lisse and len(b.images("dort")) > 1, "adulte : l'animation procédurale (sommeil animé)")
    c = poses.album(partie(espece="braisillon", shiny=True))
    d = poses.album(partie(espece="braisillon"))
    verifier(c.image("assis", 0).rgba != d.image("assis", 0).rgba, "shiny : les poses dessinées changent de teinte")
    vieux = partie(xp=20)
    vieux.pop("espece_compagnon")
    e = poses.album(vieux)
    verifier(e is not None and e.images("marche"), "créature d'avant le bestiaire : une image qui respire")
    f = poses.album(partie(xp=0))
    verifier(f is not None and f.image("assis", 0).w > 0, "l'œuf : une image")
    g = poses.album_espece("cornichaud", "adulte")
    verifier(g is not None and not g.dessine, "une bestiole de l'équipe sans dessin : procédurale")


# ---------------------------------------------------------------- 3. comportement
def test_creature():
    print("Le comportement")
    c = V.Creature(1200, {}, hasard=random.Random(3))
    xs, etats = [], set()
    for _ in range(3000):
        c.tick(0.1, {"inactif": 1.0, "batterie": None})
        xs.append(c.x)
        etats.add(c.etat)
    verifier(min(xs) >= 50 and max(xs) <= 1150, "elle marche sans sortir de l'écran")
    verifier({"marche", "assis"} <= etats and "dort" not in etats, f"elle marche et s'assoit, sans dormir ({sorted(etats)})")
    c.tick(0.1, {"inactif": V.SOMMEIL + 1})
    verifier(c.etat == "dort", "ordinateur inactif : elle s'endort")
    c.reagir("mange")
    verifier(c.etat == "dort", "elle dort : les miettes attendront")
    c.tick(0.1, {"inactif": 0.5})
    verifier(c.etat == "etire", "l'ordinateur se réveille : elle s'étire")
    c = V.Creature(1200, {}, hasard=random.Random(4))
    vu = False
    for _ in range(1300):
        c.tick(0.1, {"inactif": 1, "batterie": (9, False)})
        vu = vu or c.etat == "baille"
    verifier(vu, "batterie faible : elle bâille")
    c.reagir("mange")
    verifier(c.etat == "mange", "le jeu compte une commande : elle mange")
    c = V.Creature(1200, {"sur_place": True}, hasard=random.Random(5))
    x0 = c.x
    for _ in range(2000):
        c.tick(0.1, {"inactif": 1})
    verifier(c.x == x0, "« rester sur place » : elle ne marche pas")
    c.prendre()
    c.deplacer(400, 250)
    c.tick(0.1)
    verifier(c.air == 250 and c.x == 400, "glisser : elle suit le pointeur")
    c.lacher()
    for _ in range(25):
        c.tick(0.05)
    verifier(c.air == 0 and c.etat == "sursaut", "lâchée : elle retombe au sol (petit sursaut)")
    c.dormir()
    c.tick(0.1, {"inactif": 0})
    verifier(c.etat == "dort", "« faire dodo » : elle dort même si l'ordinateur est utilisé")
    k = V.Creature(800, {}, hasard=random.Random(1))
    k.changer("marche")
    k.dir = -1
    verifier(k.image()[3] is True, "elle marche vers la gauche : l'image est retournée")


def test_animation():
    print("La vie dans chaque pose et les transitions")
    c = V.Creature(1000, {}, hasard=random.Random(8))
    c.changer("assis", 10)
    for _ in range(10):
        c.tick(0.1, {"inactif": 1})
    ys = []
    for _ in range(40):
        c.tick(0.1, {"inactif": 1})
        ys.append(V.animer(c).sy)
    verifier(max(ys) - min(ys) > 0.02, f"assise : elle respire (sy de {min(ys):.3f} à {max(ys):.3f})")
    c.cligne = -0.05
    verifier(V.animer(c).etat == "cligne", "assise : elle cligne des yeux")
    c.changer("baille")
    c.tick(0.05)
    an = V.animer(c)
    verifier(an.ancien is not None and an.ancien[0] == "assis" and an.sy < 1, "changement : l'ancienne pose se tasse")
    for _ in range(3):
        c.tick(0.05)
    an = V.animer(c)
    verifier(an.ancien is not None and 0.01 < an.opacite < 0.99, "puis un court fondu croisé")
    for _ in range(5):
        c.tick(0.05)
    verifier(V.animer(c).ancien is None, f"transition finie en {V.TRANSITION} s")
    c.dormir()
    for _ in range(10):
        c.tick(0.1)
    an = V.animer(c)
    verifier(sum(1 for e in an.effets if e[0] == "z") == 3 and not an.miroir, "dort : des « z » qui montent, à l'endroit")
    c.changer("mange", 3.0)
    c.tick(0.3)
    verifier(any(e[0] == "miette" for e in V.animer(c).effets), "mange : la miette arrive")
    for _ in range(28):
        c.tick(0.1)
    verifier(not any(e[0] == "miette" for e in V.animer(c).effets), "trois bouchées : la miette a disparu")
    c.changer("salut", 2.0)
    c.tick(0.5)
    rots = []
    for _ in range(12):
        c.tick(0.05)
        rots.append(V.animer(c).rot)
    verifier(max(rots) > 2 and min(rots) < -2, "salut : elle se balance")
    c.changer("sursaut")
    c.tick(0.25)
    an = V.animer(c)
    verifier(an.dy < -10 and an.ombre < 0.8, "sursaut : un saut, l'ombre rétrécit")
    durees = set()
    for _ in range(20):
        c.changer("etire")
        durees.add(round(c.duree, 3))
    verifier(len(durees) > 10, "les durées changent un peu à chaque fois")
    a = poses.album(partie())
    verifier(a.images("cligne") and a.images("cligne")[0].rgba != a.images("assis")[0].rgba, "l'album a sa pose « cligne »")
    L, _ = S.scene_creature(c, a, S.VueCreature(), V.DEFAUTS, 1000, 440, 430)
    verifier(any(op[0] == "imgt" for op in L), "le dessin déforme la pose à la taille de l'écran (imgt)")


PHRASES = ["Coucou, on joue ?", "J'ai un peu faim… Tape `date` !", "我很喜欢你哦。", "Привет!"]


def test_machoire():
    print("La mâchoire : manger, parler ; le sommeil sans « z » dessinés")
    verifier([V.pose_bouche(n) for n in (0, 0.1, 0.3, 0.5, 0.7, 0.9, 1)] ==
             ["assis", "assis", "bouche1", "bouche2", "bouche2", "bouche3", "bouche3"], "pose_bouche : 0 fermée → 1 grande ouverte")
    sans, avec = [], 0
    for esp in poses.especes():
        idx, _p = poses.poses_indexees(esp)
        if all(idx[b][2] == idx["assis"][2] for b in ("bouche1", "bouche2", "bouche3")):
            sans.append(esp)
        elif len({idx[b][2] for b in ("assis", "bouche1", "bouche2", "bouche3")}) == 4:
            avec += 1
    verifier(avec == 25 and sorted(sans) == ["boulonnet", "zyeuton"],
             f"25 bébés ouvrent la bouche en 3 étapes ; sans bouche : {sans}")
    sys.path.insert(0, str(RACINE / "donnees/bestiaire2/outils"))
    try:
        import numpy as np
        import poses_bureau as PB
        from PIL import Image
        restes = []
        for d in sorted((RACINE / "donnees/bestiaire2/animations").iterdir()):
            esp = d.name.split("_", 1)[1]
            a = np.array(Image.open(d / "dort.png").convert("RGBA"))
            a[..., 3] = np.where(a[..., 3] > 0, 255, 0)
            o, _e, _a, _d = PB.nettoyer(a, "dort")
            _s, zz = PB.sans_zzz(o, esp)
            cad = poses.album_dessine(esp).image("dort", 0)
            n_final = sum(1 for k in range(3, len(cad.rgba), 4) if cad.rgba[k])
            if zz.sum() < 20 or n_final != int((o[..., 3] > 0).sum() - zz.sum()):
                restes.append(esp)
        verifier(not restes, "dort : les « z » dessinés sont retirés sur les 27 bébés, rien d'autre"
                 + (f" {restes}" if restes else ""))
    except ImportError:
        pass
    c = V.Creature(1000, {}, hasard=random.Random(9))
    c.bouche = (0.3, -0.35)
    c.changer("mange", 4.0)
    vus, miettes = set(), []
    for _ in range(40):
        c.tick(0.1)
        an = V.animer(c)
        vus.add(an.etat)
        miettes.append(max([e[3] for e in an.effets if e[0] == "miette"], default=0))
    verifier({"assis", "bouche1", "bouche2", "bouche3"} <= vus and "mange" not in vus,
             "manger : la bouche s'ouvre et se ferme (pose neutre, sans la miette dessinée)")
    verifier(miettes[-1] == 0 and max(miettes) > 0.1 and miettes[15] < max(miettes), "la miette rapetisse en 3 bouchées")
    for ph in PHRASES:
        verifier(V.syllabes(ph) and abs(V.duree_parole(ph) - sum(d for d, _ in V.syllabes(ph))) < 1e-9, f"syllabes : « {ph} »")
    c = V.Creature(1000, {}, hasard=random.Random(10))
    c.changer("marche")
    c.parler(PHRASES[0])
    verifier(c.etat == "assis", "elle s'arrête de marcher pour parler")
    bouches = set()
    for _ in range(int(V.duree_parole(PHRASES[0]) / 0.05)):
        c.tick(0.05)
        bouches.add(V.animer(c).etat)
    verifier({"bouche2", "bouche3"} & bouches and "assis" in bouches, f"elle parle : la bouche suit les syllabes {sorted(bouches)}")
    c.tick(0.5)
    verifier(c.parle() is None and V.animer(c).etat in ("assis", "cligne"), "après la phrase, la bouche se ferme")
    c.parler(PHRASES[1])
    c.tick(0.1)
    verifier(V.mini_vie(c, 0.1)[0].startswith("bouche"), "dans l'île aussi, la mini-créature parle")


def test_clics():
    print("Les gestes")
    cl = V.Clics()

    def clic(t, x=10, y=10):
        cl.appuyer(x, y, t)
        return cl.relacher(x, y, t + 0.05)
    clic(0.0)
    verifier(cl.attendre(0.1) is None and cl.attendre(0.5) == "clic", "un clic (après le délai du double-clic)")
    clic(1.0)
    clic(1.2)
    verifier(cl.attendre(1.7) == "double", "un double-clic")
    clic(2.0)
    clic(2.2)
    verifier(clic(2.4) == "triple" and cl.attendre(3.0) is None, "un triple clic")
    cl.appuyer(10, 10, 4.0)
    verifier(not cl.bouger(12, 11, 4.1) and cl.bouger(40, 10, 4.2), "un glisser au-delà de quelques pixels")
    verifier(cl.relacher(40, 10, 4.3) == "glisse_fin" and cl.attendre(5) is None, "la fin du glisser n'est pas un clic")


def test_menu():
    print("Le petit menu rond")
    lib = {k: langue.t("bur.menu." + k) for k, _s, _a in V.MENU}
    for x in (60, 900, 1860):
        b, (cx, cy, r) = V.menu_positions(x, 380, 100, lib, largeur=1920, hauteur=440)
        dedans = all(bx >= 0 and by >= 0 and bx + bw <= 1920 and by + bh <= 440 for _k, _s, _l, bx, by, bw, bh in b)
        verifier(dedans and len(b) == 7, f"7 boutons, tous dans la bande (créature en x = {x})")
        chev = [(i, j) for i in range(7) for j in range(i + 1, 7)
                if not (b[i][3] + b[i][5] <= b[j][3] or b[j][3] + b[j][5] <= b[i][3]
                        or b[i][4] + b[i][6] <= b[j][4] or b[j][4] + b[j][6] <= b[i][4])]
        verifier(not chev, "aucun bouton n'en chevauche un autre")
    for x in (40, 196, 360):                       # un téléphone (393 dp de large), comme la bulle Android
        b2, _ = V.menu_positions(x, 380, 56, lib, largeur=393, hauteur=420)
        chev = [(i, j) for i in range(7) for j in range(i + 1, 7)
                if not (b2[i][3] + b2[i][5] <= b2[j][3] or b2[j][3] + b2[j][5] <= b2[i][3]
                        or b2[i][4] + b2[i][6] <= b2[j][4] or b2[j][4] + b2[j][6] <= b2[i][4])]
        verifier(not chev and all(e[3] >= 0 and e[3] + e[5] <= 393 for e in b2),
                 f"écran étroit : le menu tient sans chevauchement (x = {x})")
    haut = min(b, key=lambda e: e[4])
    verifier(haut[0] == "jouer", "« Jouer » en haut, comme sur la maquette")
    verifier(V.touche(b, b[1][3] + 5, b[1][4] + 5) == b[1][0], "un clic sur un bouton le trouve")
    for code in langue.LANGUES:
        langue.definir(code)
        b, _ = V.menu_positions(900, 380, 100, {k: langue.t("bur.menu." + k) for k, _s, _a in V.MENU},
                                largeur=1920, hauteur=440)
        chev = [(i, j) for i in range(7) for j in range(i + 1, 7)
                if not (b[i][3] + b[i][5] <= b[j][3] or b[j][3] + b[j][5] <= b[i][3]
                        or b[i][4] + b[i][6] <= b[j][4] or b[j][4] + b[j][6] <= b[i][4])]
        if chev:
            verifier(False, f"menu en {code} : boutons qui se chevauchent {chev}")
    langue.definir("fr")
    verifier(True, "le menu tient dans les 14 langues")


def test_ile():
    print("L'île")
    ile = V.Ile()
    ile.survol(True, 0)
    for k in range(20):
        ile.tick(0.05, k * 0.05)
    verifier(ile.etat == "ouverte" and ile.ouverture == 1.0, "au survol, elle s'agrandit en douceur")
    ile.survol(False, 1.0)
    ile.tick(0.05, 1.5)
    verifier(ile.etat == "ouverte", "elle attend un peu avant de se replier")
    for k in range(30):
        ile.tick(0.05, 2.0 + k * 0.05)
    verifier(ile.etat == "repos" and ile.ouverture == 0.0, "puis se replie en pilule")
    verifier(ile.annoncer("Un monstre est apparu !") and ile.etat == "evenement", "un événement l'ouvre toute seule")
    for k in range(140):
        ile.tick(0.05, 10 + k * 0.05)
    verifier(ile.etat == "repos", "quelques secondes, puis elle se replie")
    ile.auto = False
    verifier(not ile.annoncer("x") and ile.etat == "repos", "ouverture automatique coupée : elle reste en pilule")
    ile.auto, ile.discrete = True, True
    verifier(not ile.annoncer("x"), "« ne pas déranger » : elle reste discrète")
    ile.discrete = False
    ile.clic()
    ile.survol(False, 50)
    for k in range(40):
        ile.tick(0.05, 50 + k * 0.05)
    verifier(ile.etat == "ouverte", "ouverte d'un clic : elle reste ouverte")
    a = {"sauvages": 0, "lesson": 1, "step": 2, "hunger": 40, "total": 3}
    b = dict(a, sauvages=1, step=3, hunger=20)
    ev = [k for k, _ in V.evenements(a, b, ["🎓 Nouveau badge !"])]
    verifier(ev == ["bur.ile.monstre", "bur.ile.etape", "bur.ile.envie_faim", ""], f"événements du jeu : {ev}")


def test_mini_terminal():
    print("Le mini-terminal de l'île")
    d = tempfile.mkdtemp(prefix="tg_mini_")
    os.mkdir(os.path.join(d, "grenier"))
    vus = []
    m = V.MiniTerminal(d, compter=lambda l, c: vus.append((l, c)), shell="/bin/sh")
    code, sortie = m.lancer("echo bonjour")
    verifier(code == 0 and sortie == ["bonjour"], "une vraie commande, sa sortie")
    m.lancer("cd grenier")
    verifier(m.dossier.endswith("grenier") and m.invite().endswith("grenier $"), "cd change le dossier de l'invite")
    code, _ = m.lancer("ls nexistepas")
    verifier(code not in (0, None) and vus[-1] == ("ls nexistepas", code), "le jeu compte la commande, avec son code de sortie")
    code, sortie = m.lancer("vim notes.txt")
    verifier(code is None and sortie == ["@vrai_terminal"] and vus[-1][0] != "vim notes.txt",
             "une commande plein écran n'est pas lancée (le vrai terminal)")
    m.DELAI = 0.5
    t0 = time.time()
    code, sortie = m.lancer("sleep 20")
    verifier(code == 124 and sortie[-1] == "@trop_long" and time.time() - t0 < 5, "une commande trop longue est arrêtée")


# ---------------------------------------------------------------- 4. vie privée
INTERDITS_PC = [
    r"pynput", r"\bimport keyboard\b", r"\bevdev\b", r"/dev/input", r"XQueryKeymap", r"XGrabKeyboard", r"XRecord",
    r"SetWindowsHookEx", r"GetAsyncKeyState", r"GetKeyState", r"CGEventTap", r"GetWindowText", r"GetForegroundWindow",
    r"_NET_ACTIVE_WINDOW", r"_NET_WM_NAME", r"\bWM_NAME\b", r"XGetInputFocus", r"ImageGrab", r"screenshot",
    r"xdotool", r"wmctrl", r"xprop", r"org\.gnome\.Shell\.Eval", r"Screencast", r"get_clipboard", r"clipboard",
    r"XFetchName", r"NSWorkspace", r"frontmostApplication", r"bash_history", r"read_new_lines",
]
INTERDITS_ANDROID = [
    r"AccessibilityService", r"MediaProjection", r"getRunningTasks", r"getRunningAppProcesses", r"UsageStatsManager",
    r"READ_LOGS", r"ClipboardManager", r"PACKAGE_USAGE_STATS", r"BIND_ACCESSIBILITY", r"getForegroundWindow",
    r"TYPE_ACCESSIBILITY", r"captureScreen", r"PixelCopy", r"ScreenCapture",
]


def test_vie_privee():
    print("La vie privée")
    fichiers = ["bureau.py", "bureau_vie.py", "bureau_scene.py", "signaux.py", "poses.py"]
    trouves = []
    for f in fichiers:
        src = (RACINE / "pc/tg" / f).read_text(encoding="utf-8")
        code = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
        code = re.sub(r'"""(?:.|\n)*?"""', "", code)              # les explications ne comptent pas
        trouves += [f"{f}: {m}" for m in INTERDITS_PC if re.search(m, code)]
    verifier(not trouves, "PC : aucune lecture du clavier, des fenêtres, du presse-papiers ni de l'écran"
             + (f" ({trouves})" if trouves else ""))
    src = (RACINE / "pc/tg/signaux.py").read_text(encoding="utf-8")
    appels = set(re.findall(r'"(org\.[A-Za-z.]+\.(?:GetIdletime|GetSessionIdleTime))"', src))
    verifier(appels == {"org.gnome.Mutter.IdleMonitor.GetIdletime", "org.freedesktop.ScreenSaver.GetSessionIdleTime"},
             "D-Bus : seulement les deux compteurs d'inactivité")
    cmds = set(re.findall(r'_sortie\(\["([a-z]+)"', src))
    verifier(cmds <= {"gdbus", "ioreg", "pmset", "gsettings"}, f"commandes du système permises seulement ({sorted(cmds)})")
    verifier("org.gnome.desktop.notifications" in src and "show-banners" in src, "« ne pas déranger » : un réglage du système")
    # sous Linux, les signaux rendent des nombres (ou None), jamais du texte
    s = signaux.releve()
    verifier(set(s) == {"inactif", "batterie", "discret"} and (s["inactif"] is None or isinstance(s["inactif"], float))
             and isinstance(s["discret"], bool), "les signaux : trois valeurs anonymes")
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "BAT0"))
    Path(d, "BAT0/capacity").write_text("12\n")
    Path(d, "BAT0/status").write_text("Discharging\n")
    verifier(signaux._batterie_linux(d) == (12, False), "batterie : pourcentage et secteur, rien d'autre")
    kt = []
    for f in list((RACINE / "app/src/main/java/fr/terminagotchi").rglob("*.kt")):
        if f.name.startswith(("Bulle", "BureauVie", "Poses", "Ile")):
            code = f.read_text(encoding="utf-8")
            kt += [f"{f.name}: {m}" for m in INTERDITS_ANDROID if re.search(m, code)]
    man = (RACINE / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    kt += [f"manifeste: {m}" for m in INTERDITS_ANDROID if re.search(m, man)]
    verifier(not kt, "Android : ni accessibilité, ni capture d'écran, ni applis ouvertes, ni presse-papiers"
             + (f" ({kt})" if kt else ""))
    verifier("SYSTEM_ALERT_WINDOW" in man and "BulleService" in man, "Android : la bulle demande « par-dessus les autres applis »")


# ---------------------------------------------------------------- 5. contrôleur, réglages, démarrage, dessin
class FauxJeu:
    def __init__(self, st):
        self.st = st
        self.lignes = []

    def __call__(self, spontane=True, rythme=1.5, defis=True, avant_save=None, extra=None, cwd=None, statut=None):
        if extra:
            self.lignes += extra
            self.st["total"] += 1
        if avant_save:
            avant_save(self.st)
        return self.st


def test_controleur():
    print("Le bureau en marche (sans fenêtre)")
    st = partie()
    core.SAVE_DIR.mkdir(parents=True, exist_ok=True)
    core.save(st)
    jeu = FauxJeu(st)
    c = bureau.Controleur(jeu, 1600, 430)
    verifier(c.album is not None and c.album.dessine, "la créature du bureau : ses poses dessinées")
    st["total"] += 1
    c.jeu()
    verifier(c.c.etat == "mange" and c.vue.flottants, "une commande comptée : elle mange (« +miam »)")
    st["sauvages"] = [{"f": "x"}]
    c.jeu()
    verifier(c.ile.etat == "evenement" and c.c.parole is not None, "un monstre apparaît : l'île s'ouvre, elle l'annonce")
    L, z = c.scene()
    cr = next(e for e in z if e[4] == "creature")
    c.appui(cr[0] + cr[2] / 2, cr[1] + cr[3] / 2, z)
    c.relache(cr[0] + cr[2] / 2, cr[1] + cr[3] / 2, z)
    time.sleep(0.4)
    c.tick()
    L, z = c.scene()
    verifier(c.vue.menu and sum(1 for e in z if e[4].startswith("menu:")) == 7, "un clic : le menu rond s'ouvre")
    c.fermer_menu()
    L, z = c.scene()
    cr = next(e for e in z if e[4] == "creature")
    mx, my = cr[0] + cr[2] / 2, cr[1] + cr[3] / 2
    c.appui(mx, my, z)
    c.bouge(mx + 30, my - 150, z)
    verifier(c.c.porte and c.c.air > 100, "glisser depuis la créature : on la soulève")
    c.relache(mx + 30, my - 150, z)
    verifier(not c.c.porte, "relâchée, elle retombe")
    c.appui(5, 5, z)
    c.bouge(200, 5, z)
    verifier(not c.c.porte, "glisser ailleurs ne l'attrape pas")
    c.relache(200, 5, z)
    c.vue.menu = True
    c.action("menu:reglages")
    verifier(c.vue.panneau and len(c.vue.panneau[1]) == 12, "Réglages : 12 réglages")
    c.action("reg:taille")
    verifier(core.load()["config"]["bureau"]["taille"] == "grande", "un réglage est gardé dans la partie")
    c.action("reg:sur_place")
    verifier(c.c.regl["sur_place"] is True, "et la créature le suit tout de suite")
    c.action("reg:demarrage")
    f = bureau._fichier_demarrage()
    verifier(f.exists() and "bureau" in f.read_text() and "X-GNOME-Autostart-enabled=true" in f.read_text(),
             "lancement au démarrage : un fichier dans ~/.config/autostart")
    c.action("reg:demarrage")
    verifier(not f.exists(), "et on peut le retirer")
    c.action("menu:equipe")
    verifier(c.vue.panneau and c.vue.panneau[1][0][1] == "equipe:moi", "Équipe : choisir qui vient sur le bureau")
    c.action("menu:soccuper")
    verifier(c.vue.panneau and c.vue.panneau[1][-1][1] == "action:caresser", "S'occuper : ses envies et un câlin")
    c.fermer_menu()
    c.ile.fermer()
    c.ile.clic()
    for _ in range(30):
        c.ile.tick(0.05, 0)
    L, z = c.scene_ile()
    noms = [e[4] for e in z]
    verifier("ile:saisie" in noms and sum(1 for n in noms if n.startswith("menu:")) >= 5,
             "l'île ouverte : mini-terminal et boutons d'action")
    sx = next(e for e in z if e[4] == "ile:saisie")
    verifier(c.clic_ile(sx[0] + 5, sx[1] + 5, z) and c.touche_ile("l") and c.touche_ile("s"), "on tape dans l'île")
    c.mini.dossier = tempfile.mkdtemp()
    c.touche_ile(special="entree")
    verifier(jeu.lignes[-1] == "ls", "Entrée : la commande est lancée et comptée par le jeu")
    c.saisie_active = False
    verifier(not c.touche_ile("x"), "sans clic dans l'île, le clavier n'est jamais lu")


def test_dessin():
    print("Le dessin")
    st = partie()
    a = poses.album(st)
    c = V.Creature(1920, {}, x=1265, hasard=random.Random(2))
    vue = S.VueCreature()
    L, z = S.scene_creature(c, a, vue, V.DEFAUTS, 1920, 440, 430)
    img = [e for e in L if e[0] == "imgt"]
    verifier(len(img) == 1 and abs(img[0][2] - 1265) < 2, "la créature est posée sur son ancre")
    ile = V.Ile()
    L, z = S.scene_ile(ile, {"nom": "Noisette", "faim": 38, "xp": 62}, a, V.MiniTerminal("/tmp"), 0)
    verifier([e[4] for e in z] == ["ile"] and abs(z[0][2] - S.PILULE_W) < 1, "au repos : une pilule")
    try:
        im = S.vers_pil(L, (S.ILE_L, S.ILE_H))
        verifier(im.getbbox() is not None, "capture simulée (PIL) : l'île est dessinée")
    except ImportError:
        print("  (PIL absent : capture simulée non vérifiée)")


def main():
    test_poses()
    test_albums()
    test_creature()
    test_animation()
    test_machoire()
    test_clics()
    test_menu()
    test_ile()
    test_mini_terminal()
    test_vie_privee()
    test_controleur()
    test_dessin()
    print(f"\n{ok} réussis, {ko} échoués")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
