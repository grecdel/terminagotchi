"""La créature qui vit sur le bureau (`tg bureau`), et l'île du haut de l'écran.

Sans fenêtre visible : la créature se promène le long du bas de l'écran, s'assoit, dort, s'étire, bâille ;
    clic          le petit menu rond autour d'elle (Jouer, Terminal, S'occuper, Carte, Équipe, Réglages, Ranger)
    double-clic   un cœur ;  triple clic : une petite phrase ;  glisser : la déplacer (elle retombe au sol)
    réactions     le jeu compte une commande → elle mange les miettes ; ordinateur inactif → elle s'endort ;
                  batterie faible → elle bâille. Rien d'autre n'est regardé (signaux.py).
L'île : une pilule en haut de l'écran (faim, XP) qui s'agrandit au survol ou au clic (la créature parle, boutons,
mini-terminal) et s'ouvre toute seule quelques secondes sur un événement du jeu.

Les fenêtres :
  GTK 4 (Linux, d'abord) — sur GNOME (Wayland ou X11) : fenêtres X11 transparentes par XWayland, au premier plan,
          sans bordure, les clics passent à travers sauf sur la créature ; sur Sway, Hyprland, KDE… : layer-shell
          (gtk4-layer-shell) si installé ;
  tkinter (Windows, macOS, et en dernier recours sur Linux) — fond transparent sous Windows et macOS, petite carte
          sombre qui suit la créature sous Linux.
TG_BUREAU=gtk|tk force un choix. Tout le comportement est dans bureau_vie.py (testé sans écran), le dessin dans
bureau_scene.py (la même liste de dessin pour chaque fenêtre, et pour les captures simulées).

`tg bureau installer` / `tg bureau desinstaller` : lancement automatique à l'ouverture de session (option).
"""
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import bureau_scene as S
from . import bureau_vie as V
from . import core, langue, poses, signaux
from .langue import sans_marques, t
from .plateforme import IS_WIN, OSK

ZONE_H = 440            # hauteur de la bande du bas où vit la créature (place pour le menu rond)
MARGE_SOL = 10          # les pieds, au-dessus du bord de l'écran
IPS_ECRAN = 12          # images par seconde à l'écran
JOURNAL = core.SAVE_DIR / "bureau.log"


def noter(msg):
    """Une erreur de fenêtre est notée (jamais affichée à l'enfant) : ~/.terminagotchi/bureau.log."""
    try:
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg)[:2000] + "\n")
    except OSError:
        pass


# ================================================================ ce qui se passe (commun à toutes les fenêtres)
class Controleur:
    def __init__(self, etape, largeur, sol, quitter=None, bip=None):
        self.etape = etape
        self.largeur = largeur
        self.sol = sol
        self.quitter = quitter or (lambda: None)
        self.bip = bip or (lambda: None)
        self.state = None
        self.resume = None
        self.regl = dict(V.DEFAUTS)
        self.c = V.Creature(largeur, self.regl)
        self.vue = S.VueCreature()
        self.clics = V.Clics()
        self.ile = V.Ile()
        dossier = core.TERRAIN if core.TERRAIN.is_dir() else Path.home()
        self.mini = V.MiniTerminal(dossier, compter=self._compter)
        self.album = None
        self.cle_album = None
        self.equipe = []
        self.sig = {"inactif": None, "batterie": None, "discret": False}
        self.t = V.maintenant()
        self.derniere_action = self.t
        self.texte_ile = None              # (texte, jusqu'à quand) : ce que la créature dit dans l'île
        self.pointeur_ile = None
        self.saisie_active = False
        self.prise = None                  # décalage entre le pointeur et les pieds pendant un glisser
        self.notifs = []
        self.jeu()
        self.releve()

    # ------------------------------------------------ le jeu et les signaux
    def _avant_save(self, st):
        self.notifs = list(st.get("notifs") or [])

    def jeu(self):
        """Toutes les 1,5 s : la partie avance (comme l'invite du terminal), et le bureau réagit à ce qui a changé."""
        try:
            st = self.etape(spontane=True, rythme=1.5, defis=True, avant_save=self._avant_save)
        except (core.Probleme, OSError):
            st = None
        except Exception as e:                      # noqa: BLE001 — le bureau ne plante jamais pour le jeu
            noter(f"jeu : {e!r}")
            st = None
        if not st:
            return
        langue.appliquer(st)
        r = V.resume(st)
        if self.resume is not None:
            if r["total"] > self.resume["total"]:
                self.c.reagir("mange")
                self.vue.flotter(random.choice(langue.liste("bur.miam")))
                if self.regl.get("son"):
                    self.bip()
            for cle, texte in V.evenements(self.resume, r, self.notifs):
                if self.ile.annoncer(sans_marques(texte or t(cle)), self.t) and self.c.etat != "dort":
                    self.c.reagir("salut")          # elle fait signe : « regarde en haut ! »
                break
        self.notifs = []
        self.resume = r
        self.state = st
        self.regl = V.reglages(st)
        self.c.regl = self.regl
        self.ile.auto = self.regl["ile_auto"]
        self._album()

    def releve(self):
        """Toutes les 5 s : les signaux anonymes (inactivité, batterie, ne pas déranger)."""
        try:
            self.sig = signaux.releve()
        except Exception as e:                      # noqa: BLE001
            noter(f"signaux : {e!r}")
        self.ile.discrete = bool(self.regl.get("discrete") and self.sig.get("discret"))

    def _album(self):
        st = self.state
        choix = self.regl.get("espece")
        ind = None
        if choix:
            ind = next((c for c in st.get("captures", []) if c.get("id") == choix), None)
        cle = (ind.get("id"), ind.get("stade"), ind.get("shiny")) if ind else \
            (st.get("espece_compagnon"), core.stage(core.level(st["xp"])), st.get("shiny"))
        if cle == self.cle_album and self.album:
            return
        self.cle_album = cle
        a = None
        try:
            if ind:
                from . import bestiaire as B
                e = B.espece(ind.get("espece", ""))
                if e:
                    stade = ind.get("stade", "bebe")
                    a = poses.album_espece(e["id"], "ancien" if stade == "finale" else stade, ind.get("shiny"))
            a = a or poses.album(st)
        except Exception as e:                      # noqa: BLE001
            noter(f"album : {e!r}")
        self.album = a or self.album
        self.equipe = []
        try:
            from . import bestiaire as B
            for ind in list(st.get("captures", []))[-3:]:
                e = B.espece(ind.get("espece", ""))
                if e:
                    al = poses.album_espece(e["id"], "bebe" if ind.get("stade", "bebe") == "bebe" else
                                            ("ancien" if ind.get("stade") == "finale" else ind.get("stade")), ind.get("shiny"))
                    if al:
                        self.equipe.append((al, S.BLEU))
        except Exception as e:                      # noqa: BLE001
            noter(f"équipe : {e!r}")

    def _compter(self, ligne, code):
        """Une commande du mini-terminal : le jeu la compte comme si elle venait du terminal."""
        try:
            st = self.etape(spontane=False, rythme=1.5, defis=True, extra=[ligne], cwd=self.mini.dossier,
                            statut=code, avant_save=self._avant_save)
            if st:
                self.state = st
        except Exception as e:                      # noqa: BLE001
            noter(f"mini-terminal : {e!r}")

    # ------------------------------------------------ le temps
    def tick(self):
        now = V.maintenant()
        dt = now - self.t
        self.t = now
        self.c.tick(dt, self.sig)
        self.vue.tick(dt)
        self.ile.tick(dt, now)
        g = self.clics.attendre(now)
        if g:
            self.geste(g)
        if (self.vue.menu or self.vue.panneau) and now - self.derniere_action > 12:
            self.fermer_menu()

    # ------------------------------------------------ les gestes sur la créature (coordonnées de la zone)
    def appui(self, x, y, zones=None):
        self.derniere_action = self.t
        self.clics.appuyer(x, y, V.maintenant())
        self.sur_creature = zones is None or self._sur(zones, x, y, "creature")
        self.prise = (x - self.c.x, (self.sol - self.c.air) - y)

    def bouge(self, x, y, zones):
        if self.clics.bouger(x, y, V.maintenant()):
            if not self.c.porte:
                if getattr(self, "sur_creature", False):
                    self.c.prendre()
                    self.fermer_menu()
                else:
                    return
            dx, dy = self.prise or (0, 0)
            self.c.deplacer(x - dx, self.sol - (y + dy))

    def relache(self, x, y, zones):
        g = self.clics.relacher(x, y, V.maintenant())
        if g == "glisse_fin":
            if self.c.porte:
                self.c.lacher()
            return
        action = self._zone(zones, x, y)
        if action and action.startswith(("menu:", "reg:", "equipe:", "action:")):
            self.clics.n = 0                        # un bouton : tout de suite, pas un double-clic
            self.action(action)
            return
        if action in (None, "") and (self.vue.menu or self.vue.panneau):
            self.clics.n = 0
            self.fermer_menu()                      # un clic ailleurs ferme le menu
            return
        if action != "creature":
            self.clics.n = 0
        if g == "triple":
            self.geste("triple")

    def geste(self, g):
        if g == "clic":
            if self.vue.menu or self.vue.panneau:
                self.fermer_menu()
            else:
                self.vue.menu = True
                self.vue.bulle = None
                self.c.reagir("sursaut")
        elif g == "double":
            self.fermer_menu()
            self.c.reagir("coeur")
            self.vue.flotter("♥", S.ROUGE)
            if self.regl.get("son"):
                self.bip()
        elif g == "triple":
            self.fermer_menu()
            self.c.reagir("salut")
            self.vue.dire(random.choice(langue.liste("bur.phrases")), self.t)

    @staticmethod
    def _zone(zones, x, y):
        for zx, zy, zw, zh, a in reversed(zones):
            if zx <= x <= zx + zw and zy <= y <= zy + zh:
                return a
        return None

    def _sur(self, zones, x, y, nom):
        return any(a == nom and zx <= x <= zx + zw and zy <= y <= zy + zh for zx, zy, zw, zh, a in zones)

    def fermer_menu(self):
        self.vue.menu = False
        self.vue.panneau = None

    # ------------------------------------------------ les actions
    def action(self, a):
        self.derniere_action = self.t
        cle = a.split(":", 1)[1] if ":" in a else a
        if a.startswith("menu:"):
            if cle == "jouer":
                self.fermer_menu()
                ouvrir_terminal([])
            elif cle == "terminal":
                self.fermer_menu()
                ouvrir_terminal(None)
            elif cle == "carte":
                self.fermer_menu()
                ouvrir_terminal(["carte"])
            elif cle == "ranger":
                self.quitter()
            elif cle == "soccuper":
                self.panneau_envies()
            elif cle == "equipe":
                self.panneau_equipe()
            elif cle == "reglages":
                self.panneau_reglages()
        elif a.startswith("reg:"):
            self.regler(cle)
        elif a.startswith("equipe:"):
            self._sauver({"espece": None if cle == "moi" else cle})
            self.cle_album = None
            self._album()
            self.panneau_equipe()
        elif a == "action:caresser":
            self.fermer_menu()
            self.geste("double")

    def panneau_envies(self):
        st = self.state or {}
        lignes = []
        try:
            from . import envies
            for k, v in envies.valeurs(st).items():
                lignes.append((f"{envies.nom(k)}  {'▰' * int(v // 20)}{'▱' * (5 - int(v // 20))}", None))
            ph = envies.phrase(st)
            if ph:
                self.texte_ile = (sans_marques(ph), self.t + 12)
                self.vue.dire(ph, self.t, 10)
        except Exception as e:                      # noqa: BLE001
            noter(f"envies : {e!r}")
        lignes.append(("♥ " + t("bur.caresser"), "action:caresser"))
        self.vue.menu = False
        self.vue.panneau = (t("bur.menu.soccuper"), lignes[:7])

    def panneau_equipe(self):
        st = self.state or {}
        choix = self.regl.get("espece")
        lignes = [(("● " if not choix else "○ ") + st.get("name", "?"), "equipe:moi")]
        for ind in list(st.get("captures", []))[-6:]:
            lignes.append((("● " if choix == ind.get("id") else "○ ") + ind.get("espece", "?"),
                           "equipe:" + str(ind.get("id"))))
        self.vue.menu = False
        self.vue.panneau = (t("bur.equipe.titre"), lignes)

    def panneau_reglages(self):
        r = self.regl
        oui = lambda b: t("app.on") if b else t("app.off")
        lignes = [
            (t("bur.reg.taille", v=t("bur.reg.taille." + r["taille"])), "reg:taille"),
            (t("bur.reg.vitesse", v=t("bur.reg.vitesse." + r["vitesse"])), "reg:vitesse"),
            (t("bur.reg.sur_place", v=oui(r["sur_place"])), "reg:sur_place"),
            (t("bur.reg.son", v=oui(r["son"])), "reg:son"),
            (t("bur.reg.dormir"), "reg:dormir"),
            (t("bur.reg.demarrage", v=oui(est_installe())), "reg:demarrage"),
            (t("bur.reg.notifs", v=oui((self.state or {}).get("config", {}).get("notifs", True))), "reg:notifs"),
            (t("bur.reg.langue", v=langue.LANGUES.get(langue.courante(), "")), "reg:langue"),
            (t("bur.reg.ile", v=oui(r["ile"])), "reg:ile"),
            (t("bur.reg.ile_pos", v=t("bur.reg.ile_pos." + r["ile_pos"])), "reg:ile_pos"),
            (t("bur.reg.ile_auto", v=oui(r["ile_auto"])), "reg:ile_auto"),
            (t("bur.reg.discrete", v=oui(r["discrete"])), "reg:discrete"),
        ]
        self.vue.menu = False
        self.vue.panneau = (t("bur.menu.reglages"), lignes)

    def _sauver(self, maj, autre=None):
        def f(s):
            s.setdefault("config", {}).setdefault("bureau", {}).update(maj)
            if autre:
                autre(s)
        try:
            st = core.modifier(f)
            if st:
                self.state = st
                self.regl = V.reglages(st)
                self.c.regl = self.regl
                self.ile.auto = self.regl["ile_auto"]
        except (core.Probleme, OSError) as e:
            noter(f"réglages : {e!r}")
            self.regl.update(maj)

    def regler(self, cle):
        r = self.regl
        if cle == "taille":
            self._sauver({"taille": V.suivant(list(V.TAILLES), r["taille"])})
        elif cle == "vitesse":
            self._sauver({"vitesse": V.suivant(list(V.VITESSES), r["vitesse"])})
        elif cle == "ile_pos":
            self._sauver({"ile_pos": V.suivant(V.POSITIONS_ILE, r["ile_pos"])})
        elif cle in ("sur_place", "son", "ile", "ile_auto", "discrete"):
            self._sauver({cle: not r[cle]})
        elif cle == "dormir":
            self.fermer_menu()
            self.c.dormir()
            return
        elif cle == "demarrage":
            if est_installe():
                desinstaller()
            else:
                installer()
        elif cle == "notifs":
            self._sauver({}, lambda s: s["config"].__setitem__("notifs", not s["config"].get("notifs", True)))
        elif cle == "langue":
            codes = list(langue.LANGUES)
            nouveau = V.suivant(codes, langue.courante())
            self._sauver({}, lambda s: s.__setitem__("langue", nouveau))
            langue.definir(nouveau)
        self.panneau_reglages()

    # ------------------------------------------------ l'île
    def info_ile(self):
        st = self.state or {}
        info = {"nom": st.get("name", ""), "faim": int(st.get("hunger", 0)), "xp": 0, "texte": "", "titre": "",
                "dans_equipe": 1 + len(st.get("captures", []))}
        if not st:
            info["texte"] = t("bur.pas_de_creature")
            return info
        lvl = core.level(st["xp"])
        lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
        info["xp"] = int(100 * (st["xp"] - lo) / max(1, hi - lo))
        try:
            from . import envies
            info["titre"] = envies.humeur(st)
        except Exception:                           # noqa: BLE001
            pass
        if self.texte_ile and self.t < self.texte_ile[1]:
            info["texte"] = self.texte_ile[0]
            return info
        b = st.get("bubble")
        if b and time.time() < b[1]:
            info["texte"] = b[0]
            return info
        try:
            from . import compagnon, lecons
            les, _ = lecons.lecon_courante(st)
            if les and lvl >= les["niveau"] and st.get("step", 0) < len(les["steps"]):
                info["texte"] = t("comp.lecon", cmd=compagnon.commande_montree(st, les["steps"][st["step"]],
                                                                              self.mini.dossier).strip("`"))
                return info
            from . import envies
            info["texte"] = envies.phrase(st) or ""
        except Exception as e:                      # noqa: BLE001
            noter(f"île : {e!r}")
        return info

    def scene_ile(self):
        if not self.album:
            return [], []
        return S.scene_ile(self.ile, self.info_ile(), self.album, self.mini, self.t, self.pointeur_ile, self.equipe,
                           self.c)

    def clic_ile(self, x, y, zones):
        a = self._zone(zones, x, y)
        self.saisie_active = a == "ile:saisie"
        if a == "ile:fermer":
            self.ile.fermer()
        elif a and a.startswith("menu:"):
            if a == "menu:soccuper":
                self.panneau_envies()
                self.vue.panneau = None
            elif a in ("menu:reglages", "menu:equipe"):
                self.action(a)                     # le panneau s'ouvre au-dessus de la créature du bureau
            else:
                self.action(a)
        elif a == "ile:creature":
            self.c.reagir("coeur")
        elif a in ("ile", None) and self.ile.etat == "repos":
            self.ile.clic()
        elif a == "ile" and self.ile.etat == "evenement":
            self.ile.clic()
        return self.saisie_active

    def touche_ile(self, texte=None, special=None):
        """Le clavier, seulement quand l'enfant a cliqué dans le mini-terminal de l'île (sa propre fenêtre)."""
        if not self.saisie_active:
            return False
        if special == "entree":
            self.mini.lancer()
        elif special == "effacer":
            self.mini.effacer()
        elif special == "echap":
            self.saisie_active = False
            self.mini.saisie = ""
        elif texte and texte.isprintable():
            self.mini.taper(texte)
        return True

    def scene(self, ox=0, largeur=None):
        if not self.album:
            return [], []
        return S.scene_creature(self.c, self.album, self.vue, self.regl, largeur or self.largeur, ZONE_H, self.sol,
                                ox, self.t, (self.state or {}).get("name", ""))


# ================================================================ ouvrir le jeu dans un terminal
def ouvrir_terminal(args):
    """args None : un terminal dans le terrain de jeu ; sinon le jeu (`tg` + args) dans un nouveau terminal."""
    from . import compagnon, fenetre
    dossier = str(core.TERRAIN if core.TERRAIN.is_dir() else Path.home())
    if args is None:
        if IS_WIN:
            cmd = ["cmd", "/c", "start", "Terminagotchi", "cmd", "/k"]
        else:
            shell = os.environ.get("SHELL") or "/bin/sh"
            cmd = fenetre.commande_terminal([shell])
    else:
        exe, app = compagnon.commande()
        jeu = [exe, app] + list(args)
        if args and not IS_WIN and OSK != "mac":       # la carte s'affiche puis la fenêtre reste ouverte
            shell = os.environ.get("SHELL") or "/bin/sh"
            jeu = [shell, "-c", " ".join(_guillemets(x) for x in jeu) + "; exec " + _guillemets(shell)]
        cmd = fenetre.commande_terminal(jeu)
    if not cmd:
        return False
    kw = {"cwd": dossier, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WIN:
        kw["creationflags"] = 0x00000008 | 0x00000200
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kw)
        return True
    except OSError as e:
        noter(f"terminal : {e!r}")
        return False


def _guillemets(x):
    return "'" + str(x).replace("'", "'\\''") + "'"


# ================================================================ lancement automatique à l'ouverture de session
def _fichier_demarrage():
    if IS_WIN:
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        return base / "Microsoft/Windows/Start Menu/Programs/Startup/terminagotchi-bureau.cmd"
    if OSK == "mac":
        return Path.home() / "Library/LaunchAgents/fr.terminagotchi.bureau.plist"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart/terminagotchi-bureau.desktop"


def contenu_demarrage():
    from . import compagnon
    exe, app = compagnon.commande()
    if IS_WIN:
        w = Path(exe).with_name("pythonw.exe")
        return f'@echo off\r\nstart "" "{w if w.exists() else exe}" "{app}" bureau\r\n'
    if OSK == "mac":
        return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
                "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\"><dict>\n"
                "<key>Label</key><string>fr.terminagotchi.bureau</string>\n<key>ProgramArguments</key><array>"
                f"<string>{exe}</string><string>{app}</string><string>bureau</string></array>\n"
                "<key>RunAtLoad</key><true/>\n</dict></plist>\n")
    return ("[Desktop Entry]\nType=Application\nName=Terminagotchi\nComment=" + t("bur.demarrage.commentaire") +
            f"\nExec=\"{exe}\" \"{app}\" bureau\nIcon=utilities-terminal\nTerminal=false\n"
            "X-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Delay=8\n")


def est_installe():
    return _fichier_demarrage().exists()


def installer():
    f = _fichier_demarrage()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenu_demarrage(), encoding="utf-8")
        return True, t("bur.demarrage.oui")
    except OSError as e:
        return False, t("bur.demarrage.echec", erreur=e)


def desinstaller():
    try:
        _fichier_demarrage().unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        return False, t("bur.demarrage.echec", erreur=e)
    return True, t("bur.demarrage.non")


# ================================================================ GTK 4
def _layer_shell_lib():
    for d in ("/usr/lib64", "/usr/lib", "/usr/lib/x86_64-linux-gnu", "/usr/lib/aarch64-linux-gnu", "/usr/local/lib"):
        p = os.path.join(d, "libgtk4-layer-shell.so")
        if os.path.exists(p):
            return p
        if os.path.exists(p + ".0"):
            return p + ".0"
    return None


def mode_gtk(env=None):
    """« layer » (layer-shell : Sway, Hyprland, KDE…), « x11 » (GNOME et les autres, par XWayland ou X11), ou None."""
    env = os.environ if env is None else env
    wl, x = env.get("WAYLAND_DISPLAY"), env.get("DISPLAY")
    bureau = env.get("XDG_CURRENT_DESKTOP", "").lower()
    if wl and "gnome" not in bureau and _layer_shell_lib():
        return "layer"
    if x:
        return "x11"
    return None


class _X11:
    """Quelques réglages de fenêtre par la Xlib (XWayland) : type, premier plan, position. Aucune lecture."""

    def __init__(self):
        import ctypes
        self.c = ctypes
        self.x = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.x.XOpenDisplay.restype = ctypes.c_void_p
        self.x.XInternAtom.restype = ctypes.c_ulong
        self.x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        self.x.XMoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int]
        self.x.XFlush.argtypes = [ctypes.c_void_p]
        self.d = self.x.XOpenDisplay(None)
        if not self.d:
            raise OSError("pas d'affichage X")

    def atome(self, nom):
        return self.x.XInternAtom(self.d, nom.encode(), 0)

    def proprietes(self, xid, type_, etats):
        c = self.c
        atom = self.atome("ATOM")
        t_ = (c.c_ulong * 1)(self.atome(type_))
        self.x.XChangeProperty(self.d, xid, self.atome("_NET_WM_WINDOW_TYPE"), atom, 32, 0, c.cast(t_, c.c_void_p), 1)
        e = (c.c_ulong * len(etats))(*[self.atome(n) for n in etats])
        self.x.XChangeProperty(self.d, xid, self.atome("_NET_WM_STATE"), atom, 32, 0, c.cast(e, c.c_void_p), len(etats))
        self.x.XFlush(self.d)

    def deplacer(self, xid, x, y):
        self.x.XMoveWindow(self.d, xid, int(x), int(y))
        self.x.XFlush(self.d)


class FenetresGtk:
    def __init__(self, etape, mode):
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("PangoCairo", "1.0")
        if mode == "layer":
            gi.require_version("Gtk4LayerShell", "1.0")
        if mode == "x11":
            gi.require_version("GdkX11", "4.0")
        from gi.repository import Gdk, Gio, GLib, Gtk, Pango, PangoCairo
        import cairo
        self.Gtk, self.Gdk, self.GLib, self.Pango, self.PangoCairo, self.cairo = Gtk, Gdk, GLib, Pango, PangoCairo, cairo
        self.mode = mode
        self.etape = etape
        self.surfaces = {}
        self.regions = {}
        self.zones = {"creature": [], "ile": []}
        self.x11 = _X11() if mode == "x11" else None
        self.app = Gtk.Application(application_id="fr.terminagotchi.bureau",
                                   flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.app.connect("activate", self._activer)
        self.ctl = None
        self.ile_pos = None

    def lancer(self):
        self.app.run([])

    # ------------------------------------------------ fenêtres
    def _css(self):
        Gtk, Gdk = self.Gtk, self.Gdk
        css = "window.tg, window.tg > * { background: transparent; box-shadow: none; }"
        p = Gtk.CssProvider()
        try:
            p.load_from_string(css)
        except (AttributeError, TypeError):
            try:
                p.load_from_data(css, -1)
            except TypeError:
                p.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), p,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _fenetre(self, w, h, nom, dessin):
        Gtk = self.Gtk
        win = Gtk.Window(application=self.app)
        win.set_title("Terminagotchi")
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_default_size(w, h)
        win.add_css_class("tg")
        da = Gtk.DrawingArea()
        da.set_content_width(w)
        da.set_content_height(h)
        da.set_draw_func(dessin)
        win.set_child(da)
        win.da = da
        win.nom = nom
        return win

    def _activer(self, app):
        Gdk, Gtk = self.Gdk, self.Gtk
        self._css()
        mon = Gdk.Display.get_default().get_monitors().get_item(0)
        g = mon.get_geometry()
        self.ecran = (g.x, g.y, g.width, g.height)
        self.ctl = Controleur(self.etape, g.width, ZONE_H - MARGE_SOL, quitter=self.app.quit,
                              bip=lambda: Gdk.Display.get_default().beep())
        self.win = self._fenetre(g.width, ZONE_H, "creature", self._dessiner_creature)
        self.win_ile = self._fenetre(S.ILE_L, S.ILE_H, "ile", self._dessiner_ile)
        for w in (self.win, self.win_ile):
            self._gestes(w)
            self._placer(w)
        clavier = Gtk.EventControllerKey()
        clavier.connect("key-pressed", self._touche)
        self.win_ile.add_controller(clavier)
        self.win.present()
        if self.ctl.regl.get("ile", True):
            self.win_ile.present()
        self.GLib.timeout_add(1000 // IPS_ECRAN, self._image)
        self.GLib.timeout_add(1500, self._jeu)
        self.GLib.timeout_add(5000, self._releve)

    def _placer(self, win):
        """Où va chaque fenêtre : layer-shell (bord de l'écran), ou X11 (type, premier plan, position)."""
        if self.mode == "layer":
            from gi.repository import Gtk4LayerShell as L
            L.init_for_window(win)
            L.set_layer(win, L.Layer.OVERLAY)
            L.set_namespace(win, "terminagotchi")
            if win.nom == "creature":
                for bord in (L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
                    L.set_anchor(win, bord, True)
                L.set_keyboard_mode(win, L.KeyboardMode.NONE)
            else:
                self._ancrer_ile(win)
                L.set_keyboard_mode(win, L.KeyboardMode.ON_DEMAND)
        elif self.mode == "x11":
            win.connect("realize", self._realise)
            win.connect("map", lambda w: self.GLib.timeout_add(60, self._deplacer, w))

    def _ancrer_ile(self, win):
        from gi.repository import Gtk4LayerShell as L
        pos = self.ctl.regl.get("ile_pos", "haut")
        for bord in (L.Edge.TOP, L.Edge.BOTTOM, L.Edge.LEFT, L.Edge.RIGHT):
            L.set_anchor(win, bord, False)
        L.set_anchor(win, {"haut": L.Edge.TOP, "bas": L.Edge.BOTTOM, "cote": L.Edge.RIGHT}[pos], True)
        self.ile_pos = pos

    def _xid(self, win):
        from gi.repository import GdkX11
        return GdkX11.X11Surface.get_xid(win.get_surface())

    def _realise(self, win):
        try:
            if win.nom == "creature":
                self.x11.proprietes(self._xid(win), "_NET_WM_WINDOW_TYPE_DOCK",
                                    ["_NET_WM_STATE_ABOVE", "_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER",
                                     "_NET_WM_STATE_STICKY"])
            else:
                self.x11.proprietes(self._xid(win), "_NET_WM_WINDOW_TYPE_UTILITY",
                                    ["_NET_WM_STATE_ABOVE", "_NET_WM_STATE_SKIP_TASKBAR", "_NET_WM_STATE_SKIP_PAGER",
                                     "_NET_WM_STATE_STICKY"])
        except Exception as e:                      # noqa: BLE001
            noter(f"x11 : {e!r}")

    def _position_ile(self):
        x, y, w, h = self.ecran
        pos = self.ctl.regl.get("ile_pos", "haut")
        if pos == "bas":
            return x + (w - S.ILE_L) // 2, y + h - ZONE_H - S.ILE_H // 3
        if pos == "cote":
            return x + w - S.ILE_L - 8, y + h // 3
        return x + (w - S.ILE_L) // 2, y + 34                    # sous la barre du haut de GNOME

    def _deplacer(self, win):
        try:
            x, y, w, h = self.ecran
            if win.nom == "creature":
                self.x11.deplacer(self._xid(win), x, y + h - ZONE_H)
            else:
                self.x11.deplacer(self._xid(win), *self._position_ile())
                self.ile_pos = self.ctl.regl.get("ile_pos")
        except Exception as e:                      # noqa: BLE001
            noter(f"x11 : {e!r}")
        return False

    # ------------------------------------------------ gestes
    def _gestes(self, win):
        Gtk = self.Gtk
        g = Gtk.GestureDrag()
        g.set_button(1)
        g.connect("drag-begin", lambda ge, x, y: self._appui(win, x, y))
        g.connect("drag-update", lambda ge, dx, dy: self._bouge(win, ge, dx, dy))
        g.connect("drag-end", lambda ge, dx, dy: self._relache(win, ge, dx, dy))
        win.da.add_controller(g)
        if win.nom == "ile":
            m = Gtk.EventControllerMotion()
            m.connect("enter", lambda c, x, y: self._survol(x, y))
            m.connect("motion", lambda c, x, y: self._survol(x, y))
            m.connect("leave", lambda c: self._survol(None, None))
            win.da.add_controller(m)

    def _appui(self, win, x, y):
        self._depart = (x, y)
        if win.nom == "creature":
            self.ctl.appui(x, y, self.zones["creature"])

    def _bouge(self, win, ge, dx, dy):
        if win.nom == "creature":
            x0, y0 = self._depart
            self.ctl.bouge(x0 + dx, y0 + dy, self.zones["creature"])

    def _relache(self, win, ge, dx, dy):
        x0, y0 = self._depart
        if win.nom == "creature":
            self.ctl.relache(x0 + dx, y0 + dy, self.zones["creature"])
        elif abs(dx) < 6 and abs(dy) < 6:
            if self.ctl.clic_ile(x0, y0, self.zones["ile"]):
                self.win_ile.present()                  # le clavier vient dans l'île (son propre champ)

    def _survol(self, x, y):
        self.ctl.pointeur_ile = None if x is None else (x, y)
        dedans = x is not None and any(a == "ile" and zx <= x <= zx + zw and zy <= y <= zy + zh
                                       for zx, zy, zw, zh, a in self.zones["ile"])
        self.ctl.ile.survol(dedans, V.maintenant())

    def _touche(self, ctrl, keyval, keycode, etat):
        Gdk = self.Gdk
        nom = Gdk.keyval_name(keyval) or ""
        special = {"Return": "entree", "KP_Enter": "entree", "BackSpace": "effacer", "Escape": "echap"}.get(nom)
        u = Gdk.keyval_to_unicode(keyval)
        return self.ctl.touche_ile(chr(u) if u and not special else None, special)

    # ------------------------------------------------ boucle
    def _image(self):
        try:
            self.ctl.tick()
            self.win.da.queue_draw()
            if self.ctl.regl.get("ile", True):
                if not self.win_ile.get_visible():
                    self.win_ile.present()
                if self.mode == "layer" and self.ile_pos != self.ctl.regl.get("ile_pos"):
                    self._ancrer_ile(self.win_ile)
                elif self.mode == "x11" and self.ile_pos != self.ctl.regl.get("ile_pos"):
                    self._deplacer(self.win_ile)
                self.win_ile.da.queue_draw()
            elif self.win_ile.get_visible():
                self.win_ile.set_visible(False)
        except Exception as e:                      # noqa: BLE001
            noter(f"image : {e!r}")
        return True

    def _jeu(self):
        self.ctl.jeu()
        return True

    def _releve(self):
        self.ctl.releve()
        return True

    # ------------------------------------------------ dessin (cairo)
    def _dessiner_creature(self, da, cr, w, h):
        L, zones = self.ctl.scene(0, w)
        self.zones["creature"] = zones
        self._peindre(cr, L)
        # les clics passent à travers, sauf sur la créature et ses menus (toute la bande quand le menu est ouvert)
        if self.ctl.vue.menu or self.ctl.vue.panneau or self.ctl.c.porte:
            reg = [(0, 0, w, h)]
        else:
            reg = [z[:4] for z in zones]
        self._region(self.win, reg)

    def _dessiner_ile(self, da, cr, w, h):
        L, zones = self.ctl.scene_ile()
        self.zones["ile"] = zones
        self._peindre(cr, L)
        self._region(self.win_ile, [z[:4] for z in zones if z[4] == "ile"] or [(0, 0, 1, 1)])

    def _region(self, win, rects):
        cairo = self.cairo
        cle = tuple((int(x), int(y), int(w) + 1, int(h) + 1) for x, y, w, h in rects)
        if self.regions.get(win.nom) == cle:
            return
        self.regions[win.nom] = cle
        surf = win.get_surface()
        if surf is None:
            return
        reg = cairo.Region([cairo.RectangleInt(max(0, x), max(0, y), max(1, w), max(1, h)) for x, y, w, h in cle])
        surf.set_input_region(reg)

    def _surface(self, cad):
        s = self.surfaces.get(cad.cle) if cad.cle else None
        if s is None:
            cairo = self.cairo
            src = bytes(cad.rgba)
            data = bytearray(len(src))
            data[0::4], data[1::4], data[2::4], data[3::4] = src[2::4], src[1::4], src[0::4], src[3::4]
            stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, cad.w)
            if stride != cad.w * 4:
                d2 = bytearray(stride * cad.h)
                for y in range(cad.h):
                    d2[y * stride:y * stride + cad.w * 4] = data[y * cad.w * 4:(y + 1) * cad.w * 4]
                data = d2
            s = (cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, cad.w, cad.h, stride), data)
            if cad.cle:
                if len(self.surfaces) > 400:
                    self.surfaces.clear()
                self.surfaces[cad.cle] = s
        return s[0]

    def _peindre(self, cr, liste):
        cairo, math_ = self.cairo, __import__("math")
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        def coul(c):
            cr.set_source_rgba(c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)

        def rrect(x, y, w, h, r):
            r = max(0, min(r, w / 2, h / 2))
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -math_.pi / 2, 0)
            cr.arc(x + w - r, y + h - r, r, 0, math_.pi / 2)
            cr.arc(x + r, y + h - r, r, math_.pi / 2, math_.pi)
            cr.arc(x + r, y + r, r, math_.pi, 3 * math_.pi / 2)
            cr.close_path()

        for op in liste:
            k = op[0]
            if k == "img":
                _, cad, x, y, e, miroir, lisse = op
                cr.save()
                cr.translate(x + (cad.w * e if miroir else 0), y)
                cr.scale(-e if miroir else e, e)
                cr.set_source_surface(self._surface(cad), 0, 0)
                cr.get_source().set_filter(cairo.FILTER_GOOD if lisse else cairo.FILTER_NEAREST)
                cr.paint()
                cr.restore()
            elif k == "imgt":
                # déformation continue autour des pieds, à la résolution de l'écran (cairo rééchantillonne une fois)
                _, cad, ax, ay, e, miroir, lisse, sx, sy, rot, alpha = op
                if alpha <= 0.01:
                    continue
                cr.save()
                cr.translate(ax, ay)
                if rot:
                    cr.rotate(-math_.radians(rot))
                cr.scale((-e if miroir else e) * sx, e * sy)
                cr.translate(-cad.ax, -cad.ay)
                cr.set_source_surface(self._surface(cad), 0, 0)
                cr.get_source().set_filter(cairo.FILTER_GOOD if lisse else cairo.FILTER_NEAREST)
                cr.paint_with_alpha(alpha) if alpha < 1 else cr.paint()
                cr.restore()
            elif k == "rrect":
                _, x, y, w, h, r, f, b, ep = op
                rrect(x, y, w, h, r)
                if f:
                    coul(f)
                    cr.fill_preserve()
                if b and ep:
                    coul(b)
                    cr.set_line_width(ep)
                    cr.stroke()
                else:
                    cr.new_path()
            elif k == "ellipse":
                _, cx, cy, rx, ry, f = op
                cr.save()
                cr.translate(cx, cy)
                cr.scale(max(0.1, rx), max(0.1, ry))
                cr.arc(0, 0, 1, 0, 2 * math_.pi)
                cr.restore()
                coul(f)
                cr.fill()
            elif k == "arc":
                _, cx, cy, rx, ry, c, ep = op
                cr.save()
                cr.translate(cx, cy)
                cr.scale(rx, ry)
                cr.arc(0, 0, 1, 0, 2 * math_.pi)
                cr.restore()
                coul(c)
                cr.set_line_width(ep)
                cr.set_dash([3, 6])
                cr.stroke()
                cr.set_dash([])
            elif k == "rect":
                _, x, y, w, h, c = op
                coul(c)
                cr.rectangle(x, y, w, h)
                cr.fill()
            elif k == "texte":
                _, x, y, texte, sz, c, gras, ancre, mono = op
                lay = self.PangoCairo.create_layout(cr)
                fd = self.Pango.FontDescription.from_string(("monospace" if mono else "Cantarell, Inter, sans-serif")
                                                            + (" Bold" if gras else ""))
                fd.set_absolute_size(sz * self.Pango.SCALE)
                lay.set_font_description(fd)
                lay.set_text(texte, -1)
                tw, th = lay.get_pixel_size()
                dx = {"g": 0, "c": -tw / 2, "d": -tw}[ancre]
                cr.move_to(x + dx, y - th / 2)
                coul(c)
                self.PangoCairo.show_layout(cr, lay)


# ================================================================ tkinter (Windows, macOS ; repli Linux)
TRANSP = "#ff00fe"


class FenetresTk:
    def __init__(self, etape, tk):
        self.tk = tk
        self.root = root = tk.Tk()
        root.withdraw()
        self.ecran = (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
        self.ctl = Controleur(etape, self.ecran[2], ZONE_H - MARGE_SOL, quitter=root.destroy, bip=root.bell)
        self.images = {}
        self.win = self._fenetre("creature")
        self.win_ile = self._fenetre("ile")
        self.zones = {"creature": [], "ile": []}
        self.geo = {}
        root.after(80, self._image)
        root.after(1500, self._jeu)
        root.after(5000, self._releve)

    def _fenetre(self, nom):
        tk = self.tk
        w = tk.Toplevel(self.root)
        w.title("Terminagotchi")
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        self.transparent = False
        if IS_WIN:
            w.configure(bg=TRANSP)
            w.attributes("-transparentcolor", TRANSP)
            fond, self.transparent = TRANSP, True
        elif OSK == "mac":
            try:
                w.configure(bg="systemTransparent")
                w.attributes("-transparent", True)
                fond, self.transparent = "systemTransparent", True
            except tk.TclError:
                fond = "#10121a"
        else:
            fond = "#10121a"
        cv = tk.Canvas(w, bg=fond, highlightthickness=0, bd=0)
        cv.pack(fill="both", expand=True)
        w.cv = cv
        w.nom = nom
        w.fond = fond
        cv.bind("<ButtonPress-1>", lambda e: self._appui(w, e))
        cv.bind("<B1-Motion>", lambda e: self._bouge(w, e))
        cv.bind("<ButtonRelease-1>", lambda e: self._relache(w, e))
        if nom == "ile":
            cv.bind("<Motion>", lambda e: self._survol(e.x + self.geo.get("ile", (0, 0))[0], e.y))
            cv.bind("<Leave>", lambda e: self._survol(None, None))
            w.bind("<Key>", self._touche)
        return w

    # ------------------------------------------------ gestes (coordonnées de la zone)
    def _ox(self, w):
        return self.geo.get(w.nom, (0, 0))[0]

    def _appui(self, w, e):
        if w.nom == "creature":
            self.ctl.appui(e.x + self._ox(w), e.y + self.geo["creature"][1], self.zones["creature"])
        self._depart = (e.x, e.y)

    def _bouge(self, w, e):
        if w.nom == "creature":
            self.ctl.bouge(e.x + self._ox(w), e.y + self.geo["creature"][1], self._zones_zone())

    def _relache(self, w, e):
        if w.nom == "creature":
            self.ctl.relache(e.x + self._ox(w), e.y + self.geo["creature"][1], self._zones_zone())
        elif abs(e.x - self._depart[0]) < 6 and abs(e.y - self._depart[1]) < 6:
            gx, gy = self.geo.get("ile", (0, 0))[:2]
            if self.ctl.clic_ile(e.x + gx, e.y + gy, self.zones["ile"]):
                w.focus_force()

    def _zones_zone(self):
        return self.zones["creature"]

    def _survol(self, x, y):
        self.ctl.pointeur_ile = None if x is None else (x, y)
        self.ctl.ile.survol(x is not None, V.maintenant())

    def _touche(self, e):
        special = {"Return": "entree", "KP_Enter": "entree", "BackSpace": "effacer", "Escape": "echap"}.get(e.keysym)
        self.ctl.touche_ile(None if special else e.char, special)

    # ------------------------------------------------ boucle
    def _jeu(self):
        self.ctl.jeu()
        self.root.after(1500, self._jeu)

    def _releve(self):
        self.ctl.releve()
        self.root.after(5000, self._releve)

    def _image(self):
        try:
            self.ctl.tick()
            self._dessiner_creature()
            if self.ctl.regl.get("ile", True):
                self.win_ile.deiconify()
                self._dessiner_ile()
            else:
                self.win_ile.withdraw()
        except self.tk.TclError:
            return
        except Exception as e:                      # noqa: BLE001
            noter(f"tk : {e!r}")
        self.root.after(1000 // IPS_ECRAN, self._image)

    def _boite(self, liste, zones, marge=8):
        xs, ys = [], []
        for z in zones:
            xs += [z[0], z[0] + z[2]]
            ys += [z[1], z[1] + z[3]]
        for op in liste:
            if op[0] == "img":
                _, cad, x, y, e, _m, _l = op
                xs += [x, x + cad.w * e]
                ys += [y, y + cad.h * e]
            elif op[0] == "imgt":
                _, cad, ax, ay, e, _m, _l, sx, sy, _r, _a = op
                xs += [ax - cad.w * e * sx, ax + cad.w * e * sx]
                ys += [ay - cad.h * e * sy - 30, ay + 4]
        if not xs:
            return 0, 0, 10, 10
        return (int(min(xs)) - marge, int(min(ys)) - marge, int(max(xs) - min(xs)) + 2 * marge,
                int(max(ys) - min(ys)) + 2 * marge)

    def _poser(self, w, x, y, ww, hh):
        g = f"{max(1, ww)}x{max(1, hh)}+{int(x)}+{int(y)}"
        if getattr(w, "g", None) != g:
            w.geometry(g)
            w.g = g

    def _dessiner_creature(self):
        L, zones = self.ctl.scene(0)
        self.zones["creature"] = zones
        bx, by, bw, bh = self._boite(L, zones)
        ex, ey, el, eh = self.ecran
        self.geo["creature"] = (bx, by)
        self._poser(self.win, ex + bx, ey + eh - ZONE_H + by, bw, bh)
        self._peindre(self.win, L, -bx, -by)

    def _dessiner_ile(self):
        L, zones = self.ctl.scene_ile()
        self.zones["ile"] = zones
        boite = next((z for z in zones if z[4] == "ile"), None)
        if not boite:
            return
        x, y, w, h = [int(v) for v in boite[:4]]
        ex, ey, el, eh = self.ecran
        self.geo["ile"] = (x, y)
        pos = self.ctl.regl.get("ile_pos", "haut")
        gx = ex + (el - S.ILE_L) // 2 + x if pos != "cote" else ex + el - w - 12
        gy = ey + 34 + y if pos == "haut" else (ey + eh - ZONE_H - h - 20 if pos == "bas" else ey + eh // 3)
        self._poser(self.win_ile, gx, gy, w, h)
        self._peindre(self.win_ile, L, -x, -y)

    # ------------------------------------------------ dessin (Canvas)
    def _hex(self, c, fond=(16, 18, 26)):
        a = c[3] / 255 if len(c) > 3 else 1
        return "#%02x%02x%02x" % tuple(int(c[i] * a + fond[i] * (1 - a)) for i in range(3))

    def _photo(self, cad, e, miroir):
        cle = (cad.cle, round(e, 3), miroir)
        p = self.images.get(cle)
        if p is None:
            p = self.tk.PhotoImage(data=_png_base64(cad, e, miroir), format="png")
            if len(self.images) > 300:
                self.images.clear()
            self.images[cle] = p
        return p

    def _photo2(self, cad, ex, ey, miroir):
        cle = (cad.cle, ex, ey, miroir)
        p = self.images.get(cle)
        if p is None:
            p = self.tk.PhotoImage(data=_png_base64(cad, ex, miroir, ey), format="png")
            if len(self.images) > 300:
                self.images.clear()
            self.images[cle] = p
        return p

    def _peindre(self, w, liste, dx, dy):
        cv = w.cv
        cv.delete("all")
        for op in liste:
            k = op[0]
            if k == "img":
                _, cad, x, y, e, miroir, lisse = op
                cv.create_image(int(x + dx), int(y + dy), image=self._photo(cad, e, miroir), anchor="nw")
            elif k == "imgt":
                # tkinter : pas de rotation ni de fondu ; l'étirement est arrondi au pour-cent (images gardées)
                _, cad, ax, ay, e, miroir, lisse, sx, sy, rot, alpha = op
                if alpha < 0.5:
                    continue
                ex, ey = round(e * sx, 2), round(e * sy, 2)
                p = self._photo2(cad, ex, ey, miroir)
                pax = (cad.w - cad.ax if miroir else cad.ax) * ex
                cv.create_image(int(ax + dx - pax), int(ay + dy - cad.ay * ey), image=p, anchor="nw")
            elif k == "rrect":
                _, x, y, ww, hh, r, f, b, ep = op
                if f is None and b is None:
                    continue
                if f is not None and f[3] < 30 and not b:
                    continue
                x, y = x + dx, y + dy
                r = min(r, ww / 2, hh / 2)
                pts = [x + r, y, x + ww - r, y, x + ww, y, x + ww, y + r, x + ww, y + hh - r, x + ww, y + hh,
                       x + ww - r, y + hh, x + r, y + hh, x, y + hh, x, y + hh - r, x, y + r, x, y]
                cv.create_polygon(pts, smooth=True, fill=self._hex(f) if f else "",
                                  outline=self._hex(b) if b else "", width=ep if b else 0)
            elif k == "ellipse":
                _, cx, cy, rx, ry, f = op
                if f[3] < 40:
                    continue
                cv.create_oval(cx + dx - rx, cy + dy - ry, cx + dx + rx, cy + dy + ry, fill=self._hex(f), outline="")
            elif k == "arc":
                _, cx, cy, rx, ry, c, ep = op
                cv.create_oval(cx + dx - rx, cy + dy - ry, cx + dx + rx, cy + dy + ry, outline=self._hex(c), dash=(3, 6))
            elif k == "rect":
                _, x, y, ww, hh, c = op
                cv.create_rectangle(x + dx, y + dy, x + dx + ww, y + dy + hh, fill=self._hex(c), outline="")
            elif k == "texte":
                _, x, y, texte, sz, c, gras, ancre, mono = op
                police = ("TkFixedFont" if mono else "TkDefaultFont", -int(sz)) + (("bold",) if gras else ())
                cv.create_text(x + dx, y + dy, text=texte, fill=self._hex(c), font=police,
                               anchor={"g": "w", "c": "center", "d": "e"}[ancre])


def _png_base64(cad, e, miroir, ey=None):
    """Une image (cadre) agrandie ou réduite au plus proche, en PNG (base64) pour tkinter (sans bibliothèque).
    ey : une autre échelle en hauteur (étirement)."""
    import base64
    import struct
    import zlib
    ey = e if ey is None else ey
    W, H = max(1, round(cad.w * e)), max(1, round(cad.h * ey))
    src = cad.rgba
    xs = [min(cad.w - 1, int(x / e)) for x in range(W)]
    if miroir:
        xs = [cad.w - 1 - x for x in xs]
    brut = bytearray()
    for y in range(H):
        sy = min(cad.h - 1, int(y / ey)) * cad.w
        brut.append(0)
        for x in xs:
            k = 4 * (sy + x)
            brut += src[k:k + 4]

    def bloc(ty, d):
        return struct.pack(">I", len(d)) + ty + d + struct.pack(">I", zlib.crc32(ty + d) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
           + bloc(b"IDAT", zlib.compress(bytes(brut), 6)) + bloc(b"IEND", b""))
    return base64.b64encode(png).decode("ascii")


# ================================================================ lancement
def lancer(etape, args=()):
    args = [a.lower() for a in args]
    if args and args[0] in ("installer", "install"):
        print(installer()[1])
        return
    if args and args[0] in ("desinstaller", "désinstaller", "uninstall"):
        print(desinstaller()[1])
        return
    if os.environ.get("TG_BUREAU", "") != "tk" and not IS_WIN and OSK not in ("mac", "android"):
        m = mode_gtk()
        if m == "layer" and _layer_shell_lib() not in os.environ.get("LD_PRELOAD", ""):
            # gtk4-layer-shell doit être chargé avant libwayland : on se relance une fois avec LD_PRELOAD
            env = dict(os.environ, LD_PRELOAD=(_layer_shell_lib() + " " + os.environ.get("LD_PRELOAD", "")).strip())
            from . import compagnon
            exe, app = compagnon.commande()
            try:
                os.execve(exe, [exe, app, "bureau"], env)
            except OSError as e:
                noter(f"layer-shell : {e!r}")
                m = "x11" if os.environ.get("DISPLAY") else None
        if m == "x11":
            os.environ["GDK_BACKEND"] = "x11"       # XWayland : position, premier plan et clics qui traversent
        if m:
            try:
                FenetresGtk(etape, m).lancer()
                return
            except (ImportError, ValueError, OSError) as e:
                noter(f"GTK 4 indisponible ({m}) : {e!r}")
            except Exception as e:                  # noqa: BLE001 — sinon, le repli tkinter
                noter(f"GTK 4 : {e!r}")
    try:
        import tkinter as tk
    except ImportError:
        print(t("bur.tkinter"))
        from .plateforme import installer as inst
        print(" Linux : " + inst("python3-gobject gtk4", {"apt": "python3-gi gir1.2-gtk-4.0", "pacman": "python-gobject gtk4",
                                                          "zypper": "python3-gobject typelib-1_0-Gtk-4_0"}))
        print(" " + t("bur.tkinter.autres"))
        return
    try:
        FenetresTk(etape, tk).root.mainloop()
    except tk.TclError as e:
        print(t("bur.pas_d_ecran", erreur=e))
