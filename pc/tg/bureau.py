"""Compagnon de bureau : la créature flotte au-dessus de tes fenêtres (et de ton terminal).

- fond transparent (Windows, macOS) ou petite carte sombre (Linux)
- toujours au premier plan, déplaçable à la souris
- respire, cligne des yeux, saute quand elle mange, parle dans une bulle
- double-clic : fiche détaillée · clic droit : menu
"""
import math
import random
import time

from . import core, lecons, sprites
from .plateforme import IS_WIN, OSK, piege

PX = 7                 # taille d'un pixel de la créature à l'écran
W, H = 250, 215        # taille de la fenêtre
TRANSP = "#ff00fe"     # couleur rendue transparente (Windows)


def hexa(n):
    return "#%02x%02x%02x" % sprites.x256(n)


class Bureau:
    def __init__(self, tk, etape):
        self.tk = tk
        self.etape = etape
        self.root = root = tk.Tk()
        root.title("Terminagotchi")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        self.carte = False
        if IS_WIN:
            fond = TRANSP
            root.configure(bg=fond)
            root.attributes("-transparentcolor", fond)
        elif OSK == "mac":
            fond = "systemTransparent"
            root.configure(bg=fond)
            try:
                root.attributes("-transparent", True)
            except tk.TclError:
                fond = "#1e1e2e"
                self.carte = True
        else:
            fond = TRANSP
            self.carte = True
            try:
                root.wait_visibility()
                root.attributes("-alpha", 0.94)
            except tk.TclError:
                pass
        self.fond = fond
        self.cv = tk.Canvas(root, width=W, height=H, bg=fond if not self.carte else TRANSP,
                            highlightthickness=0, bd=0)
        if self.carte:
            self.cv.configure(bg="#1e1e2e")
        self.cv.pack()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{sw - W - 30}+{sh - H - 70}")

        self.state = None
        self.total = None
        self.saut = []
        self.flottants = []          # textes « +miam » qui montent
        self.frame = 0
        self.details = False
        self.bulle = True
        self.blink = 0

        self.cv.bind("<ButtonPress-1>", self._prise)
        self.cv.bind("<B1-Motion>", self._glisse)
        self.cv.bind("<Double-Button-1>", lambda e: self._basculer_details())
        self.cv.bind("<Button-3>", self._menu)
        self.cv.bind("<Button-2>", self._menu)          # clic droit sur macOS
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Fiche détaillée", command=self._basculer_details)
        self.menu.add_command(label="Bulle on/off", command=self._basculer_bulle)
        self.menu.add_command(label="Au premier plan on/off", command=self._basculer_dessus)
        self.menu.add_separator()
        self.menu.add_command(label="Fermer le compagnon", command=root.destroy)

        self._jeu()
        self._anim()

    # --------------------------------------------------------- interactions
    def _prise(self, e):
        self._dx, self._dy = e.x, e.y

    def _glisse(self, e):
        self.root.geometry(f"+{self.root.winfo_x() + e.x - self._dx}+{self.root.winfo_y() + e.y - self._dy}")

    def _menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def _basculer_details(self):
        self.details = not self.details

    def _basculer_bulle(self):
        self.bulle = not self.bulle

    def _basculer_dessus(self):
        self.root.attributes("-topmost", not self.root.attributes("-topmost"))

    # --------------------------------------------------------- boucles
    def _jeu(self):
        st = self.etape(spontane=True, rythme=1.5, defis=True)
        if st:
            if self.total is not None and st["total"] > self.total:
                self.saut = [-6, -12, -15, -12, -6, 0]
                self.flottants.append([random.choice(["+miam", "miam !", "+XP", "crunch"]), 0])
            self.total = st["total"]
            self.state = st
        self.root.after(1500, self._jeu)

    def _anim(self):
        self.frame += 1
        if self.blink > 0:
            self.blink -= 1
        elif random.random() < 0.02:
            self.blink = 2
        self._dessiner()
        self.root.after(110, self._anim)

    # --------------------------------------------------------- dessin
    def _bulle(self, texte, y_bas):
        cv = self.cv
        t = cv.create_text(W // 2, 10, text=texte, width=W - 30, font=("TkDefaultFont", 9),
                           fill="#1e1e2e", anchor="n")
        x1, y1, x2, y2 = cv.bbox(t)
        dy = max(4, y_bas - y2 - 14)
        cv.move(t, 0, dy - 10)
        x1, y1, x2, y2 = x1 - 8, y1 + dy - 16, x2 + 8, y2 + dy - 4
        r = 8
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
               W // 2 + 7, y2, W // 2, y2 + 9, W // 2 - 7, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        cv.tag_lower(cv.create_polygon(pts, smooth=True, fill="#f5f0e6", outline="#c8bfae"), t)

    def _dessiner(self):
        cv, st = self.cv, self.state
        cv.delete("all")
        if not st:
            cv.create_text(W // 2, H // 2, text="(pas encore de créature :\nlance d'abord le jeu)",
                           fill="#bbbbbb", font=("TkDefaultFont", 9))
            return
        if self.carte:
            cv.create_rectangle(2, 2, W - 2, H - 2, fill="#1e1e2e", outline="#3a3a55")

        rows = sprites.get_sprite(st)
        pal = sprites.palette(st, blink=self.blink > 0)
        sw = max(len(r) for r in rows) * PX
        sh = len(rows) * PX
        respire = round(math.sin(self.frame / 6) * 2)
        saut = self.saut.pop(0) if self.saut else 0
        x0 = (W - sw) // 2
        y0 = H - sh - 38 + respire + saut

        # ombre
        cv.create_oval(x0 + 10, H - 40, x0 + sw - 10, H - 32, fill="#00000a" if self.carte else "#333333",
                       outline="")
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                code = pal.get(c)
                if code is None:
                    continue
                x, y = x0 + i * PX, y0 + j * PX
                cv.create_rectangle(x, y, x + PX, y + PX, fill=hexa(code), outline="")

        # textes flottants
        for f in list(self.flottants):
            f[1] += 1
            cv.create_text(x0 + sw + 4, y0 + 10 - f[1] * 2, text=f[0], fill="#ffd75f",
                           font=("TkDefaultFont", 9, "bold"), anchor="w")
            if f[1] > 15:
                self.flottants.remove(f)

        # nom, niveau, faim
        lvl = core.level(st["xp"])
        cv.create_text(W // 2, H - 22, text=f"{st['name']} · niv. {lvl}", fill="#e6e6e6",
                       font=("TkDefaultFont", 9, "bold"))
        jx, jy = W // 2 - 40, H - 10
        coul = "#5fd787" if st["hunger"] >= 60 else "#ffd75f" if st["hunger"] >= 30 else "#ff5f5f"
        cv.create_rectangle(jx, jy - 3, jx + 80, jy + 3, fill="#3a3a3a", outline="")
        cv.create_rectangle(jx, jy - 3, jx + 80 * st["hunger"] / 100, jy + 3, fill=coul, outline="")

        if self.details:
            self._fiche(st)
        else:
            b = st.get("bubble")
            if self.bulle and b and time.time() < b[1]:
                self._bulle(b[0], y0)
            elif st["defi"]:
                self._bulle(f"⚡ Tape « {piege(st['defi']['cmd'])} » vite !", y0)

    def _fiche(self, st):
        lvl = core.level(st["xp"])
        stade = core.stage(lvl)
        forme = core.STAGES[stade] + (f" {core.FORMES[st['branch']]}" if stade >= 2 and st.get("branch") else "")
        lignes = [f"{forme} · {st['xp']} XP", f"caractère : {st['trait']}",
                  "  ".join(f"{v['short']} {st['stats'][v['stat']]}" for v in core.CATEGORIES.values()),
                  f"compétences : {len(st['skills'])} · bestioles : {sum(st['collection'].values())}"]
        les, etiq = lecons.lecon_courante(st)
        if les and lvl >= les["niveau"]:
            lignes.append(f"leçon ➜ {piege(les['steps'][st['step']]['cmd'])}")
        self.cv.create_rectangle(8, 8, W - 8, 92, fill="#2a2a40", outline="#5f5f87")
        self.cv.create_text(16, 14, text="\n".join(lignes), fill="#e6e6e6", anchor="nw",
                            font=("TkDefaultFont", 8), width=W - 30)


def lancer(etape):
    try:
        import tkinter as tk
    except ImportError:
        print("Le compagnon de bureau a besoin de tkinter.")
        from .plateforme import installer
        print(" Linux :", installer("python3-tk", {"dnf": "python3-tkinter", "pacman": "tk", "zypper": "python3-tk"}))
        print(" macOS / Windows : réinstalle Python depuis python.org (tkinter est inclus).")
        return
    try:
        Bureau(tk, etape).root.mainloop()
    except tk.TclError as e:
        print("Impossible d'ouvrir une fenêtre (pas d'écran graphique ?) :", e)
