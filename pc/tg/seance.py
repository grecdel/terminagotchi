"""Les séances guidées d'une heure (idée 54) et l'écran projecteur (idée 55), maquettes validées le 3 novembre.

    tg classe seance 5        dans le terminal de l'enseignant : le but, les phases de l'heure avec leur durée, quoi
                              dire, le piège à annoncer, une question pour qui bloque, un défi pour qui a fini.
                              Entrée : phase suivante · o : question · c : montrer / cacher la commande ·
                              t : trace écrite · q : quitter (la séance reste là où elle en est).
    tg classe seance suivante | precedente | phase 3 | question | trace | commande | fin | liste
    tg classe tableau         sur le poste du vidéoprojecteur : en très gros (24 à 60 px), le chapitre, le but, la
                              commande en blocs colorés (comme la vue déployée), la question pour l'oral, la créature de
                              l'enseignant qui dit une phrase ; la trace écrite en grand à la phase « Trace écrite ».
                              Il suit les phases de `tg classe seance` (même partie, même ordinateur) ; ses touches
                              aussi : Entrée, ←, c, o, t, Échap. Aucun minuteur visible.

Aucune donnée d'élève : ce n'est que le déroulé du cours. Le déroulé est dans seances.json (copie de
donnees/classe/seances.json), les textes dans les langues (seance.N.*). En mode sans aide (code avec A), la commande
est cachée au tableau ; l'enseignant peut la montrer (c). Même modèle en Kotlin (Tableau.kt), vecteurs communs
donnees/classe/vecteurs_seances.json.
Sauvegarde (poste de l'enseignant) : state["classe_seance"] = {n, phase, commande (None = selon le code), vue}.
"""
import json
import os
import pkgutil

from . import core
from .langue import t

_D = {}
GENRES = ("lancement", "jeu", "commun", "trace", "bilan")


def donnees():
    if not _D:
        _D.update(json.loads(pkgutil.get_data(__package__, "seances.json").decode("utf-8")))
    return _D


def seance(n):
    return next((s for s in donnees()["seances"] if s["n"] == n), None)


def numeros():
    return [s["n"] for s in donnees()["seances"]]


# ---------------------------------------------------------------- l'état (poste de l'enseignant)
def s_(state):
    e = state.get("classe_seance") if isinstance(state, dict) else None
    return e if isinstance(e, dict) and seance(e.get("n")) else None


def commencer(state, n):
    if seance(n) is None:
        return False
    state["classe_seance"] = {"n": n, "phase": 0, "commande": None, "vue": None}
    return True


def agir(state, quoi, arg=None):
    """suivante, precedente, phase (arg : 1…), question, trace, commande, fin. Renvoie False sans séance."""
    e = s_(state)
    if e is None:
        return False
    nb = len(seance(e["n"])["phases"])
    if quoi == "suivante":
        e["phase"], e["vue"] = min(nb - 1, e["phase"] + 1), None
    elif quoi == "precedente":
        e["phase"], e["vue"] = max(0, e["phase"] - 1), None
    elif quoi == "phase":
        e["phase"], e["vue"] = max(0, min(nb - 1, int(arg) - 1)), None
    elif quoi in ("question", "trace"):
        e["vue"] = None if e.get("vue") == quoi else quoi
    elif quoi == "commande":
        e["commande"] = not modele(e)["commande_visible"]
    elif quoi == "fin":
        state.pop("classe_seance", None)
        state.pop("classe_place", None)              # la place de la classe se ferme avec la séance
    else:
        return False
    return True


# ---------------------------------------------------------------- le modèle (pur : mêmes vecteurs que Tableau.kt)
def _liste(cle):
    from . import langue
    v = langue.liste(cle)
    if isinstance(v, list):
        return [str(x) for x in v]
    return [x for x in t(cle).split("\n") if x]


def modele(e):
    """Ce que montrent le terminal de l'enseignant et le tableau, pour l'état e = {n, phase, commande, vue}."""
    sd = seance(e["n"])
    phases = sd["phases"]
    k = max(0, min(len(phases) - 1, int(e.get("phase") or 0)))
    ph = phases[k]
    genre, minutes = ph[0], ph[1]
    cmd = ph[2] if len(ph) > 2 else ""
    sans_aide = "A" in sd["code"].split("-")[1] if sd["code"].count("-") == 2 else False
    visible = e.get("commande") if isinstance(e.get("commande"), bool) else not sans_aide
    vue = e.get("vue")
    vue = "commun" if vue == "question" else "trace" if vue == "trace" else genre
    n = sd["n"]
    return {
        "n": n, "code": sd["code"], "k": k + 1, "total": len(phases), "genre": genre, "vue": vue,
        "minutes": minutes, "duree": sum(p[1] for p in phases),
        "nom": t(ph[3]) if len(ph) > 3 and ph[3] else t("classe.phase." + genre),
        "commande": cmd if visible else "", "commande_cachee": bool(cmd) and not visible,
        "commande_visible": visible,
        "but": t(f"seance.{n}.but"), "question": t(f"seance.{n}.question"), "bulle": t(f"seance.{n}.bloque"),
        "piege": t(f"seance.{n}.piege"), "fini": t(f"seance.{n}.fini"), "trace": _liste(f"seance.{n}.trace"),
        "phases": [[p[0], p[1], t(p[3]) if len(p) > 3 and p[3] else t("classe.phase." + p[0])] for p in phases],
    }


def chapitre(n):
    from . import classe
    return t("esp.chapitre", n=n, titre=classe._nom(n).split(" · ", 1)[-1])


# ---------------------------------------------------------------- le terminal de l'enseignant
def lignes_plan(e, couleurs=True):
    from .plateforme import BOLD, DIM, RESET, fg
    if not couleurs:
        BOLD = DIM = RESET = ""                     # noqa: N806
        fg = lambda n: ""                            # noqa: E731
    m = modele(e)
    out = [f"{BOLD}" + t("classe.seance.titre", n=m["n"], chapitre=chapitre(m["n"])) + f"{RESET}   {DIM}"
           + t("classe.seance.duree", minutes=m["duree"], code=m["code"]) + RESET,
           t("classe.seance.but", but=m["but"]), ""]
    for i, (genre, mn, nom) in enumerate(m["phases"], 1):
        marque = f"{fg(78)}✓{RESET}" if i < m["k"] else f"{fg(221)}▶{RESET}" if i == m["k"] else " "
        dire = t("classe.dire." + genre, code=m["code"])
        ligne = f"  {marque} {i}  {nom[:26]:<26} {mn:>3} min   {DIM if i != m['k'] else ''}{dire}{RESET}"
        out.append(ligne)
        if i == m["k"] and genre == "jeu":
            out.append(f"{' ' * 41}{fg(214)}" + t("classe.seance.attention", piege=m["piege"]) + RESET)
    out += ["", f"{fg(75)}" + t("classe.seance.bloque", bulle=m["bulle"]) + RESET,
            f"{fg(78)}" + t("classe.seance.fini", fini=m["fini"]) + RESET]
    if m["commande_cachee"]:
        out.append(f"{DIM}" + t("classe.seance.cachee") + RESET)
    out += ["", f"{DIM}" + t("classe.seance.touches") + RESET, f"{DIM}" + t("classe.seance.tableau") + RESET]
    return out


def liste():
    out = [t("classe.seance.liste")]
    for s in donnees()["seances"]:
        out.append(f"  {s['n']:>2}. {chapitre(s['n'])}  ({s['code']})")
    out.append(t("classe.seance.usage"))
    return out


MOTS = {"suivante": "suivante", "next": "suivante", "precedente": "precedente", "précédente": "precedente",
        "prev": "precedente", "question": "question", "trace": "trace", "commande": "commande", "fin": "fin",
        "end": "fin", "phase": "phase"}


def commande(args, interactif=False):
    """tg classe seance [N | suivante | precedente | phase K | question | trace | commande | fin | liste]."""
    a0 = args[0].lower() if args else ""
    if a0 in ("liste", "list"):
        return "\n".join(liste())
    if a0.isdigit():
        n = int(a0)
        if seance(n) is None:
            return t("classe.seance.inconnue", n=n) + "\n" + "\n".join(liste())
        st = core.modifier(lambda s: commencer(s, n))
        if interactif:
            return boucle()
        return "\n".join(lignes_plan(st["classe_seance"]))
    if a0 in MOTS:
        q = MOTS[a0]
        if q == "phase" and not (len(args) > 1 and args[1].isdigit()):
            return t("classe.seance.usage")
        res = []
        st = core.modifier(lambda s: res.append(agir(s, q, args[1] if len(args) > 1 else None)))
        if not res or not res[0]:
            return t("classe.seance.aucune") + "\n" + "\n".join(liste())
        if q == "fin":
            return t("classe.seance.finie")
        return "\n".join(lignes_plan(st["classe_seance"]))
    st = core.load() or {}
    e = s_(st)
    if e is None:
        return "\n".join(liste())
    if interactif:
        return boucle()
    return "\n".join(lignes_plan(e))


def boucle():
    """La séance au clavier : Entrée passe à la phase suivante (le tableau suit tout seul)."""
    import sys
    from .plateforme import Clavier, clear
    with Clavier() as clav:
        while True:
            st = core.load() or {}
            e = s_(st)
            if e is None:
                return t("classe.seance.finie")
            clear()
            sys.stdout.write("\n".join(lignes_plan(e)) + "\n")
            sys.stdout.flush()
            k = None
            while k is None:
                k = clav.touche(0.5)
            k = k.lower()
            if k in ("q", "\x1b", "\x03", "\x04"):
                return t("classe.seance.pause")
            quoi = {"\r": "suivante", "\n": "suivante", " ": "suivante", "o": "question", "t": "trace",
                    "c": "commande", "p": "precedente", "b": "precedente"}.get(k)
            if quoi:
                core.modifier(lambda s: agir(s, quoi))


# ---------------------------------------------------------------- l'écran projecteur (liste de dessin, 1600 × 900)
W, H = 1600, 900


def _texte_code(L, x, y, s, taille, coul, coul_code, largeur, S):
    """Une ligne dont les passages `…` sont des commandes (chasse fixe, vertes) ; renvoie la hauteur utilisée."""
    morceaux = []
    for i, p in enumerate(str(s).split("`")):
        if p:
            morceaux.append((p, i % 2 == 1))
    lignes, cour, lw = [], [], 0.0
    for txt, code in morceaux:
        mots = [txt] if code else txt.split(" ")
        for j, mot in enumerate(mots):
            m = mot if code else (mot + (" " if j < len(mots) - 1 else ""))
            w = S.lt(m, taille, code)
            if lw + w > largeur and cour:
                lignes.append(cour)
                cour, lw = [], 0.0
            cour.append((m, code))
            lw += w
    if cour:
        lignes.append(cour)
    for i, lig in enumerate(lignes):
        xx = x
        fus = []                                 # les mots voisins du même genre en un seul texte (espaces exacts)
        for m, code in lig:
            if fus and fus[-1][1] == code and not code:
                fus[-1] = (fus[-1][0] + m, code)
            else:
                fus.append((m, code))
        for m, code in fus:
            L.append(("texte", xx, y + i * taille * 1.35, m, taille, coul_code if code else coul, code, "g", code))
            xx += S.lt(m, taille, code)
    return len(lignes) * taille * 1.35


def scene(m, t_=0.0):
    """La liste de dessin de l'écran projecteur. m : modele() + {chapitre, album, anime, theme}."""
    from . import apparence
    from . import deploie as D
    from . import espace_scene as S
    S.CONF.update(facile=False, calme=True, formes=bool((m.get("confort") or {}).get("formes")), taille=100)
    L = [("rect", 0, 0, W, H, S.FOND)]
    Z = []
    # l'en-tête
    L.append(("rrect", 24, 26, 40, 40, 11, S._a(S.VERT, 30), S._a(S.VERT, 140), 1))
    L.append(("texte", 44, 46, ">_", 15, S.VERT, True, "c", True))
    L.append(("texte", 78, 37, "Terminagotchi", 18, S.TEXTE, True, "g", False))
    L.append(("texte", 78, 60, t("classe.tableau.sous"), 13, S.DOUX, False, "g", False))
    if m.get("vide"):
        L.append(("texte", W / 2, H / 2 - 30, t("classe.tableau.attente"), 34, S.TEXTE, True, "c", False))
        L.append(("texte", W / 2, H / 2 + 30, t("classe.tableau.attente.aide"), 22, S.DOUX, False, "c", True))
        return apparence.recolorer(L, m.get("theme")), Z, (W, H)
    ch = m.get("chapitre") or chapitre(m["n"])
    cw = S.lt(ch, 18, False) + 60
    L.append(("rrect", W / 2 - cw / 2, 26, cw, 40, 20, S.PANNEAU, S.BORD_FORT, 1))
    L.append(("texte", W / 2, 46, ch, 18, S.TEXTE, True, "c", False))
    ph = t("classe.tableau.phase", k=m["k"], n=m["total"], nom=m["nom"])
    S.chip(L, W - 24, 46, ph, S.JAUNE, 15, fond=(30, 26, 12, 255), ancre="d")
    vue = m["vue"]
    alb, an = m.get("album"), m.get("anime")
    from .langue import sans_marques
    m = dict(m, but=sans_marques(m["but"]), question=sans_marques(m["question"]), bulle=sans_marques(m["bulle"]))

    def creature(cx, pieds, haut):
        if not alb or not an:
            return
        e = haut / max(1, alb.ref)
        if not alb.lisse:
            e = max(1.0, float(int(e)))
        ref = alb.images("assis")[0]
        L.append(("ellipse", cx, pieds + 4, ref.w * e * 0.32, 9, (0, 0, 0, 90)))
        cad = alb.image(an.etat, an.k)
        L.append(("imgt", cad, cx, pieds, e, False, alb.lisse, an.sx, an.sy, 0.0, 1.0))

    def bulle(x, y, w, texte, taille=22):
        lignes = S.couper(texte, w - 40, taille)[:4]
        h = 30 + taille * 1.35 * len(lignes)
        L.append(("rrect", x, y, w, h, 16, (22, 26, 36, 250), S.BORD_FORT, 1))
        L.append(("poly", [(x + w * 0.62, y + h), (x + w * 0.70, y + h + 22), (x + w * 0.74, y + h)], (22, 26, 36, 250)))
        for i, l in enumerate(lignes):
            L.append(("texte", x + 20, y + 15 + taille * 0.67 + i * taille * 1.35, l, taille, S.TEXTE, False, "g", False))

    pied = t("classe.tableau.touches")
    if vue == "trace":
        x, y, w, h = 24, 92, W - 48, H - 150
        L.append(("rrect", x, y, w, h, 18, S.PANNEAU, S._a(S.VERT, 140), 1.5))
        L.append(("texte", x + 30, y + 36, S.espace_lettres(t("classe.tableau.recopier").upper()), 15, S.VERT, True,
                  "g", False))
        yy = y + 90
        for l in m["trace"]:
            yy += _texte_code(L, x + 30, yy, l, 34, S.TEXTE, S.VERT, w - 330, S) + 16
        creature(x + w - 140, y + h - 30, 150)
    elif vue in ("commun", "bilan", "lancement"):
        x, y, w, h = 24, 92, W - 48, H - 150
        L.append(("rrect", x, y, w, h, 18, S._a(S.VIOLET, 14) if vue == "commun" else S.PANNEAU,
                  S._a(S.VIOLET, 150) if vue == "commun" else S.BORD_FORT, 1.5))
        titre = {"commun": "classe.tableau.oral", "bilan": "classe.tableau.fin", "lancement": "classe.tableau.but"}[vue]
        L.append(("texte", x + 36, y + 40, S.espace_lettres(t(titre).upper()), 15,
                  S.VIOLET if vue == "commun" else S.JAUNE, True, "g", False))
        if vue == "commun":
            yy = y + 130
            for l in S.couper(m["question"], w - 520, 56)[:4]:
                L.append(("texte", x + 36, yy, l, 56, S.TEXTE, True, "g", False))
                yy += 76
            L.append(("texte", x + 36, yy + 20, t("classe.tableau.oral.aide"), 22, S.DOUX, False, "g", False))
            bulle(x + w - 440, y + 80, 400, m["bulle"])
        elif vue == "lancement":
            yy = y + 110
            for l in S.couper(m["but"], w - 520, 44)[:3]:
                L.append(("texte", x + 36, yy, l, 44, S.TEXTE, True, "g", False))
                yy += 60
            L.append(("texte", x + 36, yy + 40, t("classe.tableau.taper"), 24, S.DOUX, False, "g", False))
            L.append(("texte", x + 36, yy + 100, "tg", 40, S.VERT, True, "g", True))
            L.append(("texte", x + 36, yy + 160, f"tg classe code {m['code']} " + t("classe.tableau.pseudo"), 40,
                      S.VERT, True, "g", True))
            L.append(("texte", x + 36, yy + 210, t("classe.tableau.pseudo.aide"), 20, S.PALE, False, "g", False))
        else:
            yy = y + 130
            L.append(("texte", x + 36, yy, t("classe.tableau.bravo"), 50, S.TEXTE, True, "g", False))
            L.append(("texte", x + 36, yy + 90, t("classe.tableau.bilan"), 26, S.DOUX, False, "g", False))
            L.append(("texte", x + 36, yy + 160, "tg classe bilan fichier", 40, S.VERT, True, "g", True))
            L.append(("texte", x + 36, yy + 220, "tg classe fin", 40, S.VERT, True, "g", True))
        creature(x + w - 240, y + h - 40, 250)
    else:                                            # « jeu » : le but, la commande, la question
        x, y, w, h = 24, 92, 1036, 546
        L.append(("rrect", x, y, w, h, 18, S.PANNEAU, S.BORD_FORT, 1))
        L.append(("texte", x + 30, y + 36, S.espace_lettres(t("classe.tableau.but").upper()), 14, S.JAUNE, True, "g",
                  False))
        yy = y + 84
        for l in S.couper(m["but"], w - 60, 40)[:3]:
            L.append(("texte", x + 30, yy, l, 40, S.TEXTE, True, "g", False))
            yy += 54
        yy += 30
        L.append(("texte", x + 30, yy, S.espace_lettres(t("classe.tableau.commande").upper()), 14, S.VERT, True, "g",
                  False))
        L.append(("texte", x + w - 30, yy, t("classe.tableau.cachee.aide"), 14, S.PALE, False, "d", False))
        yy += 56
        if m["commande"]:
            bl = D.blocs(m["commande"])
            taille = 42
            while taille > 22 and sum(S.lt(b["t"], taille, True) + 34 for b in bl) + 22 * len(bl) > w - 60:
                taille -= 2
            bx = x + 30
            for b in bl:
                col = D.COULEURS[b["g"]]
                bw = S.lt(b["t"], taille, True) + 34
                L.append(("rrect", bx, yy - taille * 0.85, bw, taille * 1.7, 12, S._a(col, 30), S.rgb(col), 2))
                L.append(("texte", bx + bw / 2, yy, b["t"], taille, S.rgb(col), True, "c", True))
                if S.CONF["formes"]:
                    L.append(("texte", bx + bw - 10, yy - taille * 0.85, S.forme(b["g"]), 14, S.rgb(col), True, "c",
                              False))
                L.append(("texte", bx + bw / 2, yy + taille * 0.85 + 22, D.nom_genre(b["g"]).upper(), 13,
                          S.rgb(col), True, "c", False))
                L.append(("texte", bx + bw / 2, yy + taille * 0.85 + 44, S.court(D.courte(b, bl), max(110, bw + 20), 15),
                          15, S.DOUX, False, "c", False))
                bx += bw + 22
        else:
            msg = t("classe.tableau.cachee") if m["commande_cachee"] else t("classe.tableau.sans_commande")
            L.append(("texte", x + 30, yy, msg, 28, S.DOUX, False, "g", False))
        # la créature de l'enseignant et sa phrase
        x2, w2 = 1076, W - 24 - 1076
        L.append(("rrect", x2, y, w2, h, 18, S.PANNEAU, S.BORD_FORT, 1))
        bulle(x2 + 24, y + 26, w2 - 48, m["bulle"])
        creature(x2 + w2 / 2, y + h - 40, 220)
        # la question pour l'oral
        y3 = y + h + 16
        L.append(("rrect", 24, y3, W - 48, 172, 18, S._a(S.VIOLET, 14), S._a(S.VIOLET, 150), 1.5))
        L.append(("texte", 54, y3 + 32, S.espace_lettres(t("classe.tableau.oral").upper()), 14, S.VIOLET, True, "g",
                  False))
        L.append(("texte", 54, y3 + 86, S.court(m["question"], W - 140, 40), 40, S.TEXTE, True, "g", False))
        L.append(("texte", 54, y3 + 140, t("classe.tableau.oral.plus_tard"), 18, S.DOUX, False, "g", False))
    L.append(("texte", 24, H - 22, pied, 15, S.PALE, False, "g", False))
    L.append(("texte", W - 24, H - 22, t("classe.tableau.sans_minuteur"), 15, S.PALE, False, "d", False))
    return apparence.recolorer(L, m.get("theme")), Z, (W, H)


class Tableau:
    """Le contrôleur de la fenêtre du tableau (mêmes fenêtres que tg espace : GTK 4, sinon tkinter)."""

    def __init__(self, etape):
        from . import bureau as B
        from . import bureau_vie as V
        self.V = V
        self.ctl = B.Controleur(etape, 600, 400)
        self.ctl.c.regl = dict(self.ctl.regl, sur_place=True)
        self.ctl.c.calme = True
        self.classe = True
        self.tk = False
        self.lu = -1e9
        self.e = None

    # ce que les fenêtres de l'espace attendent
    @property
    def state(self):
        return self.ctl.state

    @property
    def t(self):
        return self.ctl.t

    def jeu(self):
        self.ctl.jeu()

    def releve(self):
        pass

    def tick(self):
        now = self.V.maintenant()
        self.ctl.c.tick(now - self.ctl.t, {})
        self.ctl.t = now
        if now - self.lu > 0.5:
            self.lu = now
            try:
                self.e = s_(core.load() or {})
            except (core.Probleme, OSError):
                pass

    def modele(self):
        from . import apparence, confort
        st = self.ctl.state
        if self.e is None:
            m = {"vide": True}
        else:
            m = modele(self.e)
            m["chapitre"] = chapitre(m["n"])
        m["album"] = self.ctl.album
        m["anime"] = self.V.animer(self.ctl.c)
        m["theme"] = apparence.theme(st) if st else apparence.Theme("sombre")
        m["confort"] = confort.reglages(st) if st else {}
        return m

    def dessin(self, m, t_):
        return scene(m, t_)

    def _agir(self, quoi):
        core.modifier(lambda s: agir(s, quoi))
        self.lu = -1e9

    def entree(self):
        self._agir("suivante")

    def taper(self, c):
        quoi = {"c": "commande", "o": "question", "t": "trace", " ": "suivante", "p": "precedente",
                "b": "precedente"}.get(c.lower())
        if quoi:
            self._agir(quoi)
        elif c.lower() == "q":
            self.arreter()

    def effacer(self):
        self._agir("precedente")

    def rappeler(self, sens):
        self._agir("precedente" if sens < 0 else "suivante")

    def echap(self):
        self.arreter()

    def completer(self):
        pass

    def arreter(self):
        os._exit(0)                                  # la fenêtre du tableau se ferme (la séance reste où elle en est)

    def zoomer(self, sens):
        pass

    def clic(self, x, y, zones):
        self._agir("suivante")

    def appui(self, x, y, zones):
        pass

    def bouger(self, x, y):
        pass

    def lacher(self, x, y, zones):
        self.clic(x, y, zones)

    def molette(self, x, y, sens, zones):
        pass


def lancer_tableau(etape):
    """tg classe tableau : la fenêtre (GTK 4, sinon tkinter) ; sans écran, le déroulé dans le terminal."""
    import os
    import sys
    from . import espace as E
    ecran = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) or os.name == "nt" or \
        sys.platform == "darwin"
    if ecran:
        try:
            E.FenetreGtk(Tableau(etape)).lancer()
            return ""
        except SystemExit:
            return ""
        except Exception as e:                       # noqa: BLE001
            E.B.noter(f"tableau gtk : {e!r}")
        try:
            import tkinter
            E.FenetreTk(Tableau(etape), tkinter).lancer()
            return ""
        except SystemExit:
            return ""
        except Exception as e:                       # noqa: BLE001
            E.B.noter(f"tableau tk : {e!r}")
    return t("classe.tableau.sans_ecran")

