"""L'espace de travail de Terminagotchi : `tg espace` (fenêtre dédiée), `tg espace classe` (grand écran),
`tg espace texte` (dans le terminal, quand il est assez grand).

Tout ce qui vit vient de la créature du bureau (bureau.Controleur : le jeu toutes les 1,5 s, l'album des poses, la
vie, l'île et son mini-terminal qui lance de vraies commandes comptées par le jeu). L'espace y ajoute :
    - un terminal complet au centre (historique, ↑, Tab, Ctrl+C), avec les messages du compagnon comme dans le vrai
      terminal (annonces de leçon, ligne de la créature) ;
    - la vue déployée de la dernière commande (deploie.py), toute seule ou pas à pas ;
    - le cerveau de la créature (cerveau.py) qui choisit sa pose dans le panneau « en direct » ;
    - le panneau du moment : Carte, Cerveau, Tuyaux, Leçon (un clic sur un onglet, ou les commandes `carte`,
      `cerveau`, `tuyaux`, `lecon` tapées dans le terminal de l'espace).
Fenêtres : GTK 4 d'abord, tkinter en repli (comme la créature du bureau) ; TG_ESPACE=gtk|tk|texte force un choix.
Le dessin est dans espace_scene.py (testé sans écran, captures avec PIL).
"""
import os
import re
import shlex
import sys
import time
from pathlib import Path

from . import apparence as A
from . import bureau as B
from . import bureau_vie as V
from . import cerveau as CV
from . import core
from . import deploie as D
from . import espace_scene as S
from . import langue
from .langue import sans_marques, t

IPS = 20
LIGNES_MAX = 400
# les commandes de l'espace lui-même (pas lancées dans le shell)
PANNEAUX = {"carte": "carte", "map": "carte", "cerveau": "cerveau", "brain": "cerveau", "tuyaux": "tuyaux",
            "lecon": "lecon", "leçon": "lecon"}
# les commandes du jeu (alias du compagnon) : lancées par tg
DU_JEU = {"aide", "quetes", "explique", "entrainement", "exercice", "badges", "guide", "types", "equipe", "envies",
          "satiete", "vacances", "lexique", "collection", "bestiaire", "histoire", "journal"}

# ---------------------------------------------------------------- couleurs ANSI → (r, g, b, a)
_BASE16 = [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200), (188, 63, 188), (17, 168, 205),
           (229, 229, 229), (102, 102, 102), (241, 76, 76), (35, 209, 139), (245, 245, 67), (59, 142, 234),
           (214, 112, 214), (41, 184, 219), (255, 255, 255)]


def couleur_256(n):
    if n < 16:
        return _BASE16[n]
    if n < 232:
        n -= 16
        v = [0, 95, 135, 175, 215, 255]
        return v[n // 36], v[(n // 6) % 6], v[n % 6]
    g = 8 + 10 * (n - 232)
    return g, g, g


_SGR = re.compile(r"\033\[([0-9;]*)m")
_AUTRES = re.compile(r"\033\[[0-9;?]*[A-Za-ln-z]|\033[78]|\033\][^\007]*\007|\033_[^\033]*\033\\")


def spans(ligne, defaut=S.TEXTE):
    """Une ligne avec des couleurs ANSI → [(texte, (r, g, b, a), gras)]."""
    from .langue import rendre
    ligne = _AUTRES.sub("", rendre(str(ligne), couleur=True).replace("\t", "    "))
    out = []
    coul, gras, dim = defaut, False, False
    pos = 0
    for m in _SGR.finditer(ligne):
        if m.start() > pos:
            out.append((ligne[pos:m.start()], S._a(coul, 150) if dim else coul, gras))
        pos = m.end()
        codes = [int(c) if c.isdigit() else 0 for c in m.group(1).split(";")] if m.group(1) else [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                coul, gras, dim = defaut, False, False
            elif c == 1:
                gras = True
            elif c == 2:
                dim = True
            elif c == 22:
                gras = dim = False
            elif c == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                coul = couleur_256(codes[i + 2]) + (255,)
                i += 2
            elif c == 38 and i + 4 < len(codes) and codes[i + 1] == 2:
                coul = (codes[i + 2], codes[i + 3], codes[i + 4], 255)
                i += 4
            elif 30 <= c <= 37:
                coul = _BASE16[c - 30] + (255,)
            elif 90 <= c <= 97:
                coul = _BASE16[c - 90 + 8] + (255,)
            elif c == 39:
                coul = defaut
            i += 1
    if pos < len(ligne):
        out.append((ligne[pos:], S._a(coul, 150) if dim else coul, gras))
    return [s for s in out if s[0]]


# ================================================================ ce qui se passe (commun à toutes les fenêtres)
class Espace(B.Controleur):
    def __init__(self, etape, classe=False):
        self.classe = classe
        self.lignes = []                  # le terminal : [[(texte, couleur, gras)]]
        self.onglet = "carte"
        self.dep = None
        self.cv = CV.Cerveau()
        self.cv_dernier = -1e9
        self.historique_pos = None
        self.ile_ouverte = False
        self.mots = []                    # les derniers mots tapés (ils flottent autour de la créature)
        self.apres_commande = False
        self.a_dire = []
        self.tape_t = 0.0
        self.son = False
        self.rangement = False            # le mode « ranger mon espace »
        self.glisse = None                # (dalle, « dalle » | « coin », case de départ, (x0, y0) du clic)
        self.options = False              # le panneau des options (roue dentée)
        self.question = None              # (question, réponse) pour les grands, avant « Tout afficher »
        self.arrivees = {}                # panneau → heure de son apparition (animation d'arrivée)
        super().__init__(etape, 600, 400)
        self.c.regl = dict(self.regl, sur_place=True)
        self.c.changer("assis", 4)
        if self.state:
            self.cv.lire_jeu(self.state)
        self.lignes.append(spans("\033[38;5;245m" + t("esp.bienvenue") + "\033[0m"))

    # ------------------------------------------------ le jeu
    def jeu(self):
        super().jeu()
        self.c.regl = dict(self.regl, sur_place=True)
        self._annonces()

    def _theme(self, L):
        return L                                     # l'île ouverte dans l'espace : recolorée avec toute la scène

    def _annonces(self):
        """Les panneaux qui viennent d'apparaître : l'animation d'arrivée et la phrase de la créature."""
        st = self.state
        if not st:
            return
        try:
            a = A.a_(st)
        except Exception:                            # noqa: BLE001
            return
        neufs = list(a.get("annonces") or [])
        if not neufs:
            return
        for n in neufs:
            self.arrivees[n] = self.t
        self.vue.dire(t(f"app.pan.{neufs[-1]}.dit"), self.t, 6.0)
        if "carte" in neufs:
            self.onglet = "carte"
        for o in ("tuyaux", "cerveau"):
            if o in neufs:
                self.onglet = o
        self.c.reagir("salut")
        self._modifier(lambda s_: A.a_(s_).__setitem__("annonces", []))

    def _modifier(self, f):
        try:
            st = core.modifier(f)
            if st:
                self.state = st
                A.activer(st)
        except (core.Probleme, OSError) as e:
            B.noter(f"apparence : {e!r}")

    def _avant_save(self, st):
        super()._avant_save(st)
        if not self.apres_commande:
            return
        from . import compagnon
        try:
            dire = compagnon.annonces(st)
            ligne = compagnon.ligne(st)
        except Exception as e:                       # noqa: BLE001 — l'espace ne plante jamais pour le compagnon
            B.noter(f"espace annonces : {e!r}")
            dire, ligne = [], ""
        self.a_dire = list(dire) + ([ligne] if ligne else [])
        st["prompt_vu"] = st.get("nlog", 0)

    # ------------------------------------------------ le temps
    def tick(self):
        now = V.maintenant()
        dt = now - self.t
        self.t = now
        self.c.tick(dt, {})                          # dans l'espace, c'est son cerveau qui décide de dormir
        self.vue.tick(dt)
        self.ile.tick(dt, now)
        if now - self.cv_dernier >= self.cv.PAS:
            self.cv.tour(self.cv.lire_jeu(self.state), now)
            self.cv_dernier = now
            if self.cv.trace.dit and self.cv.trace.de == "confus":
                self.vue.dire(self.cv.trace.dit, now, 4.0)
        self._poser()
        if self.dep:
            self._avancer_deploie(dt)

    def _poser(self):
        """La pose de la créature suit son cerveau (les autres moments : elle vit, respire, cligne, s'étire)."""
        voulu = self.cv.pose()
        c = self.c
        if voulu == "dort":
            if c.etat != "dort":
                c.dormir()
            return
        if c.etat == "dort":
            c.force_dodo = False
            c.changer("etire")
            return
        if voulu != "assis" and c.etat != voulu and (c.etat in ("assis", "marche") or c.t_etat > c.duree):
            c.changer(voulu, self.cv.PAS)

    # ------------------------------------------------ la vue déployée
    def deployer(self, ligne, dossier=None, auto=True):
        dossier = dossier or self.mini.dossier
        bl = D.blocs(ligne, D.existe_dans(dossier))
        if not bl:
            return
        try:
            sorties = D.flux(ligne, D.lanceur(dossier), D.existe_dans(dossier))
        except Exception as e:                       # noqa: BLE001
            B.noter(f"flux : {e!r}")
            sorties = None
        lieu = None
        for b in bl:
            if b["g"] == "chemin":
                lie = D.lieu(b, dossier)
                if lie:
                    rel = lie[0]
                    lieu = (os.path.basename(rel) or rel, (os.path.dirname(rel) or rel.split("/")[0]) + "/",
                            rel.split("/")[0])
                    break
        self.dep = {"ligne": ligne, "blocs": bl, "chaines": D.chaines(bl), "sorties": sorties, "actif": 1,
                    "phase": 0.0, "auto": auto if self.dep is None else self.dep["auto"], "t": 0.0,
                    "lieu": lieu[:2] if lieu else None, "lieu_piece": lieu[2] if lieu else None}
        vus = set()
        mots = []
        for m in [(b["t"], S.rgb(D.COULEURS[b["g"]])) for b in bl if b["g"] in ("commande", "tuyau")] + self.mots:
            if m[0] not in vus:
                vus.add(m[0])
                mots.append(m)
        self.mots = mots[:4]

    def _avancer_deploie(self, dt):
        d = self.dep
        d["t"] += dt
        b = d["blocs"][d["actif"] - 1]
        duree = 2.4 if b["g"] in ("tuyau", "redirection") else 1.2
        d["phase"] = (d["t"] / duree) if b["g"] in ("tuyau", "redirection", "chemin") else min(1.0, d["t"] / duree)
        if d["auto"] and d["t"] >= duree and d["actif"] < len(d["blocs"]):
            d["actif"] += 1
            d["t"] = 0.0

    def pas_suivant(self):
        if not self.dep:
            return
        d = self.dep
        d["actif"] = d["actif"] + 1 if d["actif"] < len(d["blocs"]) else 1
        d["t"] = 0.0

    # ------------------------------------------------ le terminal
    def invite(self):
        return [(self.mini.invite()[:-1], S.BLEU, False), ("$ ", S.TEXTE, False)]

    def ecrire(self, texte, couleur=S.TEXTE):
        for l in str(texte).split("\n"):
            self.lignes.append(spans(l, couleur))
        del self.lignes[:-LIGNES_MAX]

    def taper(self, texte):
        self.mini.taper(texte)
        self.tape_t = self.t
        self.historique_pos = None

    def effacer(self):
        self.mini.effacer()

    def rappeler(self, sens):
        h = self.mini.historique
        if not h:
            return
        p = len(h) if self.historique_pos is None else self.historique_pos
        p = max(0, min(len(h), p + sens))
        self.historique_pos = p
        self.mini.saisie = h[p] if p < len(h) else ""

    def completer(self):
        """Tab : complète le dernier mot avec un nom du dossier courant (le plus long début commun)."""
        s = self.mini.saisie
        mot = s.split(" ")[-1]
        base, debut = os.path.split(mot)
        try:
            noms = [n for n in os.listdir(os.path.join(self.mini.dossier, os.path.expanduser(base) or "."))
                    if n.startswith(debut) and (debut.startswith(".") or not n.startswith("."))]
        except OSError:
            return
        if not noms:
            return
        commun = os.path.commonprefix(noms)
        if len(noms) == 1 and os.path.isdir(os.path.join(self.mini.dossier, base, noms[0])):
            commun += "/"
        elif len(noms) == 1:
            commun += " "
        self.mini.saisie = s[:len(s) - len(debut)] + commun if commun else s
        if len(noms) > 1 and commun == debut:
            self.ecrire("  ".join(sorted(noms)[:20]), S.DOUX)

    def arreter(self):
        self.lignes.append(self.invite() + [(self.mini.saisie + "^C", S.TEXTE, True)])
        self.mini.saisie = ""

    def entree(self):
        """Entrée dans le terminal de l'espace."""
        ligne = self.mini.saisie.strip()
        if not ligne:
            if self.dep and not self.dep["auto"]:
                self.pas_suivant()                  # pas à pas : Entrée sur une ligne vide = le bloc suivant
            self.lignes.append(self.invite())
            return
        self.lignes.append(self.invite() + [(ligne, S.TEXTE, True)])
        self.historique_pos = None
        if self.question:
            self.mini.saisie = ""
            self.repondre_question(ligne)
            return
        try:
            mots = shlex.split(ligne)
        except ValueError:
            mots = ligne.split()
        premier = mots[0].lower() if mots else ""
        if premier in ("clear", "effacer"):
            self.lignes = []
            self.mini.saisie = ""
            self.mini.historique.append(ligne)
            return
        if premier in ("deploie", "déploie"):
            self.mini.saisie = ""
            self.mini.historique.append(ligne)
            reste = ligne.split(None, 1)[1] if len(ligne.split(None, 1)) > 1 else ""
            pas = reste.startswith("--pas")
            reste = reste.replace("--pas", "", 1).strip()
            if not reste and self.dep:
                reste = self.dep["ligne"]
            if reste:
                self.deployer(reste, auto=not pas)
                if pas:
                    self.dep["auto"] = False
                self.ecrire("▸ " + t("esp.deploie_ok"), S._a(S.VIOLET, 255))
            else:
                self.ecrire(t("dep.aide"), S.DOUX)
            return
        if premier in PANNEAUX:
            self.mini.saisie = ""
            self.mini.historique.append(ligne)
            self.onglet = PANNEAUX[premier]
            if self.onglet == "cerveau" and len(mots) > 1 and mots[1] in CV.ETATS:
                self.cv.forcer(mots[1])
            if premier in ("carte", "map"):           # la carte est aussi une vraie commande du jeu (tg carte)
                self._jeu_tg(["carte"], ligne)
            return
        if premier in ("theme", "thème", "ranger", "options"):
            self.mini.saisie = ""
            self.mini.historique.append(ligne)
            if premier == "ranger":
                self.clic_rangement("ranger")
            elif premier == "options":
                self.options = True
            elif len(mots) > 1 and mots[1] in A.ordre():
                self._modifier(lambda s_: A.choisir_theme(s_, mots[1]))
                self.ecrire("🎨 " + t("app.theme.ok", nom=t("app.theme." + mots[1])), S.VERT)
            else:
                self.ecrire(t("app.theme.liste", liste=" ".join(A.ordre())), S.DOUX)
            return
        if premier == "classe":
            self.mini.saisie = ""
            self.classe = not self.classe
            return
        if premier in DU_JEU:
            self.mini.saisie = ""
            self.mini.historique.append(ligne)
            self._jeu_tg(mots, ligne)
            return
        self.apres_commande = True
        try:
            code, sortie = self.mini.lancer(ligne)
        finally:
            self.apres_commande = False
        for l in [x for l0 in sortie for x in str(l0).split("\n")]:
            if l == "@vrai_terminal":
                self.ecrire(t("bur.ile.vrai_terminal"), S.ORANGE)
            elif l == "@trop_long":
                self.ecrire(t("bur.ile.trop_long"), S.ORANGE)
            else:
                self.lignes.append(spans(l))
        if code is not None:
            self.deployer(ligne)
            self.mots = self.mots[:4]
            if code != 0:
                self.cv.var["repas"] = 0
        for l in self.a_dire:
            for x in str(l).split("\n"):
                self.lignes.append(spans(x))
        self.a_dire = []
        del self.lignes[:-LIGNES_MAX]

    def _jeu_tg(self, mots, ligne):
        """Une commande du jeu (alias du compagnon : aide, quetes, carte…) : lancée par tg, sa sortie ici."""
        from . import compagnon
        exe, app = compagnon.commande()
        cmd = " ".join(shlex.quote(x) for x in [exe, app] + list(mots))
        code, sortie = V.executer(cmd, self.mini.dossier, 10.0, "/bin/sh" if os.name != "nt" else None)
        for l in sortie[-60:]:
            if not l.startswith("@"):
                self.lignes.append(spans(l))
        self.mini.historique.append(ligne)

    # ------------------------------------------------ clics
    def clic(self, x, y, zones):
        a = self._zone(zones, x, y)
        if self.options:
            self.clic_options(a)
            return
        if a and (a.startswith("rg:") or a == "ranger"):
            self.clic_rangement(a)
            return
        if a == "reglages":
            self.options = True
            return
        if not a:
            return
        if self.ile_ouverte and a.startswith(("ile:", "menu:")):
            self.clic_ile(x - (S.Mise(self.classe).W / 2 - 450), y - 70,
                          [(zx - (S.Mise(self.classe).W / 2 - 450), zy - 70, zw, zh, za) for zx, zy, zw, zh, za in
                           zones])
            if a == "ile:fermer":
                self.ile_ouverte = False
            return
        if a == "ile":
            self.ile_ouverte = not self.ile_ouverte
            self.ile.etat = "ouverte" if self.ile_ouverte else "repos"
            self.ile.ouverture = 1.0 if self.ile_ouverte else 0.0
        elif a.startswith("onglet:"):
            self.onglet = a.split(":", 1)[1]
        elif a.startswith("forcer:"):
            e = a.split(":", 1)[1]
            self.cv.forcer(None if self.cv.force == e else e)
            self.cv_dernier = -1e9
        elif a == "dep:pas":
            if self.dep:
                self.dep["auto"] = not self.dep["auto"]
        elif a.startswith("dep:bloc:") and self.dep:
            self.dep["actif"] = int(a.rsplit(":", 1)[1])
            self.dep["t"] = 0.0
            self.dep["auto"] = False
        elif a == "dep:lecon":
            lec = self._lecon()
            if lec and lec.get("cmd"):
                self.deployer(lec["cmd"])
        elif a == "creature":
            self.c.reagir("coeur")
        elif a == "son":
            self.son = not self.son
        elif a.startswith("lieu:"):
            self.onglet = "carte"

    # ------------------------------------------------ ranger son espace
    def clic_rangement(self, a):
        st = self.state
        if a == "ranger":
            self.rangement = not self.rangement
            self.options = False
            if self.rangement and st and A.disposition(st)[1] == "classe":
                self._modifier(lambda s_: A.choisir_disposition(s_, "classique"))
            return
        if not st:
            return
        if a == "rg:fini":
            self.rangement = False
        elif a == "rg:origine":
            self._modifier(A.origine)
        elif a == "rg:mienne":
            self._modifier(A.enregistrer_mienne)
            self.vue.dire(t("esp.rg.enregistree"), self.t, 4.0)
        elif a.startswith("rg:cacher:"):
            k = a.rsplit(":", 1)[1]
            self._modifier(lambda s_: A.modifier(s_, k, cacher=True))
        elif a.startswith("rg:remettre:"):
            k = a.rsplit(":", 1)[1]
            self._modifier(lambda s_: A.modifier(s_, k, cacher=False))

    def appui(self, x, y, zones):
        """Le bouton de la souris s'enfonce : en mode rangement, sur une poignée ou un coin, la dalle est prise."""
        if not self.rangement or not self.state:
            return False
        a = self._zone(zones, x, y)
        if a and a.startswith(("rg:dalle:", "rg:coin:")):
            k = a.rsplit(":", 1)[1]
            cases, _nom = A.disposition(self.state)
            if k in cases:
                self.glisse = (k, "dalle" if a.startswith("rg:dalle:") else "coin", list(cases[k]), (x, y), (x, y))
                return True
        return False

    def bouger(self, x, y):
        if self.glisse:
            self.glisse = self.glisse[:4] + ((x, y),)

    def lacher(self, x, y, zones):
        """La dalle est lâchée : elle s'aimante sur la grille (déplacée ou agrandie par crans)."""
        if not self.glisse:
            self.clic(x, y, zones)
            return
        self.bouger(x, y)
        k, case = self.glisse[0], self._case_visee()
        if abs(x - self.glisse[3][0]) + abs(y - self.glisse[3][1]) < 4:
            self.glisse = None
            self.clic(x, y, zones)
            return
        self.glisse = None
        self._modifier(lambda s_: A.modifier(s_, k, case=case))

    # ------------------------------------------------ les options (roue dentée)
    def clic_options(self, a):
        st = self.state
        if a in (None, "opt:fermer"):
            self.options = False
            return
        if a == "opt:panneau" or not st:
            return
        if a.startswith("opt:theme:"):
            cle = a.rsplit(":", 1)[1]
            self._modifier(lambda s_: A.choisir_theme(s_, cle))
        elif a.startswith("opt:dispo:"):
            nom = a.rsplit(":", 1)[1]
            self._modifier(lambda s_: A.choisir_disposition(s_, nom))
        elif a == "opt:ranger":
            self.options = False
            self.clic_rangement("ranger")
        elif a == "opt:tout":
            if A.a_(st).get("tout"):
                self._modifier(lambda s_: A.tout_afficher(s_, False))
            else:
                q, rep = A.question_adulte()
                self.question = (q, rep)
                self.options = False
                self.ecrire("🔒 " + t("app.tout.question", q=q), S.JAUNE)
        elif a == "opt:notifs":
            self._modifier(lambda s_: s_["config"].__setitem__("notifs", not s_["config"].get("notifs", True)))
        elif a == "opt:bureau":
            from .app import lancer_detache
            lancer_detache("bureau")

    def repondre_question(self, ligne):
        """La réponse des grands à la question de « Tout afficher » (tapée dans le terminal de l'espace)."""
        q, rep = self.question
        self.question = None
        if ligne.strip() == rep:
            self._modifier(lambda s_: A.tout_afficher(s_, True))
            self.ecrire("🔓 " + t("app.tout.ok"), S.VERT)
        else:
            self.ecrire(t("app.tout.non"), S.DOUX)

    # ------------------------------------------------ ce qu'on dessine
    def _lecon(self):
        st = self.state or {}
        try:
            from . import compagnon, lecons
            les, _ = lecons.lecon_courante(st)
            if not les or core.level(st.get("xp", 0)) < les["niveau"]:
                return None
            k = st.get("step", 0)
            step = les["steps"][k]
            return {"titre": sans_marques(lecons.tx(les["titre"])),
                    "k": k + 1, "n": len(les["steps"]), "dit": lecons.tx(step["dit"]),
                    "cmd": compagnon.commande_montree(st, step, self.mini.dossier).strip("`"),
                    "grand": lecons.adulte(step)}
        except Exception as e:                       # noqa: BLE001
            B.noter(f"leçon : {e!r}")
            return None

    def modele(self):
        st = self.state or {}
        m = {"classe": self.classe, "t": self.t, "son": self.son, "onglet": self.onglet}
        m["nom"] = st.get("name", "")
        m["album"] = self.album
        m["mini"] = V.mini_vie(self.c, self.t)
        try:
            from . import histoire
            c = histoire.chapitre_courant(st)
            m["chapitre"] = t("esp.chapitre", n=c["n"], titre=histoire.nom_chapitre(c["id"])) if c else ""
        except Exception:                            # noqa: BLE001
            m["chapitre"] = ""
        m["espece_stade"] = self._espece_stade(st)
        e = self.cv.etat
        m["etat_nom"] = CV.nom_etat(e)
        m["etat_couleur"] = S.rgb(CV.COULEURS[e]) if e != "content" else S.VERT
        m["gains"] = self._gains(st)
        m["niveau"] = core.level(st.get("xp", 0)) if st else 1
        lvl = m["niveau"]
        lo, hi = 10 * (lvl - 1) ** 2, 10 * lvl ** 2
        m["xp"] = int(100 * (st.get("xp", 0) - lo) / max(1, hi - lo)) if st else 0
        m["type_nom"] = self._type(st)
        m["equipe"], m["equipe_lignes"] = self._equipe(st)
        m["monstre"] = self._monstre(st)
        if self.ile.etat == "evenement" and self.ile.evenement:
            m["evenement"] = self.ile.evenement
        m["arbre"], m["lieux"], m["ici_piece"], m["ici_nom"] = self._monde(st)
        m["envies"], m["assiette"], m["satiete"] = self._envies(st)
        m["deploie"] = self.dep
        m["lignes"] = self.lignes
        m["invite"] = self.invite()
        m["saisie"] = self.mini.saisie
        m["tape_recent"] = self.t - self.tape_t < 0.6
        home = os.path.expanduser("~")
        d = self.mini.dossier
        m["cwd"] = "~" + d[len(home):] if d.startswith(home) else d
        m["lecon"] = self._lecon()
        m["anime"] = V.animer(self.c)
        b = self.vue.bulle
        m["bulle"] = b[0] if b and self.t < b[1] else self._bulle(st)
        m["mots"] = self.mots
        k, genre = self.cv.ligne_en_cours(self.t)
        m["cerveau"] = {"code": CV.texte_programme(m["nom"]), "ligne": (k, genre),
                        "faites": {i for i, _g in self.cv.trace.lignes}, "etat": self.cv.etat,
                        "de": self.cv.trace.de, "vers": self.cv.trace.vers, "force": self.cv.force,
                        "vars": [(CV.ident(x), self.cv.var.get(x, 0)) for x in ("faim", "jeu", "sommeil", "repas")]}
        if self.ile_ouverte and self.album:
            self.ile.ouverture = 1.0
            self.ile.etat = "ouverte"
            m["ile_ouverte"] = self.scene_ile()
        self._modele_apparence(m, st)
        return m

    def _modele_apparence(self, m, st):
        """Le thème, les panneaux déjà apparus, la disposition, le mode rangement et les options."""
        try:
            th = A.theme(st) if st else A.Theme("sombre")
            vis = A.visibles(st) if st else None
            cases, nom = A.disposition(st) if st else (A.preset("classique"), "classique")
        except Exception as e:                       # noqa: BLE001 — l'apparence ne casse jamais l'espace
            B.noter(f"apparence : {e!r}")
            th, vis, cases, nom = A.Theme("sombre"), None, A.preset("classique"), "classique"
        m["theme"] = th
        m["photo"] = "monde:" + th.cle if th.carte else "monde"
        if vis is not None:
            m["visibles"] = vis
            m["onglets"] = A.onglets(st)
            m["assiette_visible"] = "assiette" in vis
            if "equipe" not in vis:
                m["equipe"], m["monstre"] = [], None
        if nom == "classe":
            m["classe"] = True
        else:
            m["cases"] = cases
        m["caches"] = A.caches(st) if st else []
        m["rangement"] = self.rangement
        m["arrivees"] = {k: self.t - v for k, v in self.arrivees.items() if self.t - v < S.ARRIVEE}
        if self.glisse and self.glisse[4]:
            k, mode, case0, p0, (x, y) = self.glisse
            r0 = A.rect_de(case0)
            r = (r0[0] + x - p0[0], r0[1] + y - p0[1], r0[2], r0[3]) if mode == "dalle" else \
                (r0[0], r0[1], max(120, r0[2] + x - p0[0]), max(120, r0[3] + y - p0[1]))
            m["glisse"] = (k, mode, r, self._case_visee())
        m["options"] = self._options_modele(st, th, nom) if self.options else None

    def _case_visee(self):
        k, mode, case0, p0, (x, y) = self.glisse
        g = A.grille()
        sx = (g["w"] + g["ecart"]) / g["colonnes"]
        sy = (g["h"] + g["ecart"]) / g["rangees"]
        c, r, w, h = case0
        if mode == "dalle":
            c, r = c + round((x - p0[0]) / sx), r + round((y - p0[1]) / sy)
        else:
            w, h = w + round((x - p0[0]) / sx), h + round((y - p0[1]) / sy)
        return A.borner([c, r, w, h])

    def _options_modele(self, st, th, nom):
        cfg = (st or {}).get("config", {})
        return {"theme": th.cle, "dispo": nom, "tout": bool(A.a_(st).get("tout")) if st else False,
                "notifs": bool(cfg.get("notifs", True)), "question": self.question[0] if self.question else None,
                "langue": langue.LANGUES.get(langue.courante(), "")}

    def _bulle(self, st):
        bub = st.get("bubble")
        if bub and time.time() < bub[1]:
            return bub[0]
        if self.dep and self.dep["blocs"]:
            cmds = [b["t"] for b in self.dep["blocs"] if b["g"] == "commande"]
            if cmds:
                return t("esp.bulle.miam", cmd=cmds[-1])
        return None

    def _espece_stade(self, st):
        try:
            return sans_marques(core.forme(st)) if st else ""
        except Exception:                            # noqa: BLE001
            return ""

    def _type(self, st):
        try:
            from . import bestiaire
            e = bestiaire.espece(st.get("espece_compagnon"))
            return e["famille"] if e else ""          # les familles du bestiaire gardent leur nom (comme le jeu)
        except Exception:                            # noqa: BLE001
            return ""

    def _gains(self, st):
        """« faim +2 · curiosité +8 » : ce que la dernière commande a donné (envies du jeu)."""
        try:
            from . import envies
            vals = envies.valeurs(st)
        except Exception:                            # noqa: BLE001
            return ""
        avant = getattr(self, "_vals_avant", None)
        if avant is None or st.get("total") != getattr(self, "_total_avant", None):
            self._gains_txt = ""
            if avant is not None:
                d = sorted(((vals[k] - avant.get(k, vals[k]), k) for k in vals), reverse=True)
                self._gains_txt = " · ".join(f"{envies.nom(k).lower()} +{int(round(v))}" for v, k in d[:2] if v >= 0.5)
            self._vals_avant = vals
            self._total_avant = st.get("total")
        return self._gains_txt

    def _equipe(self, st):
        """Les pastilles de l'île [(album, statut, actif)] et les lignes du panneau Équipe."""
        pastilles, lignes = [], []
        if not st:
            return pastilles, lignes
        from . import bestiaire as Bs
        from . import poses
        statut = {"mange": "mange", "dort": "dort"}.get(self.cv.etat, "faim" if self.cv.etat == "faim" else "pret")
        pastilles.append((self.album, statut, True))
        lignes.append((self.album, st.get("name", ""), self._espece_stade(st) + (" · " + self._type(st) if
                                                                                  self._type(st) else ""),
                       statut, t("esp.statut." + statut), True))
        for ind in list(st.get("captures", []))[-4:]:
            e = Bs.espece(ind.get("espece", ""))
            if not e:
                continue
            stade = ind.get("stade", "bebe")
            try:
                from . import glitch as G
                al = poses.album_espece(e["id"], "ancien" if stade == "finale" else stade, ind.get("shiny"), G.de(ind))
            except Exception:                        # noqa: BLE001
                al = None
            s = "dort" if V.maintenant() % 60 < 20 and ind is st.get("captures", [])[0] else "pret"
            pastilles.append((al, s, False))
            lignes.append((al, ind.get("nom") or e["nom"], e["nom"] + " · " + Bs.nom_stade(stade), s,
                           t("esp.statut." + s), False))
        return pastilles[:4], lignes

    def _monstre(self, st):
        try:
            sauv = st.get("sauvages") or []
            if not sauv:
                return ""
            from . import maison
            p = maison.piece_de(st)
            return t("esp.monstres", n=len(sauv))
        except Exception:                            # noqa: BLE001
            return ""

    def _monde(self, st):
        """L'Explorateur (les lignes de l'arbre avec leurs marques), les lieux de la carte, et où l'on est."""
        arbre, lieux = [], {}
        ici_piece, ici_nom = None, ""
        if not st:
            return arbre, lieux, ici_piece, ici_nom
        from . import histoire, maison
        try:
            nds = maison.noeuds(st)
        except Exception as e:                       # noqa: BLE001
            B.noter(f"explorateur : {e!r}")
            nds = []
        actif = (self.dep or {}).get("lieu")
        ici_rel = maison.rel(maison.ici(st)) if maison.ici(st) else None
        piece_ici = ici_rel.split("/")[0] if ici_rel else None
        for n in nds:
            if n.get("suite"):
                continue
            if n["prof"] >= 2 and not (piece_ici and (n["rel"] + "/").startswith(piece_ici + "/")):
                continue                          # l'intérieur des autres lieux reste replié (comme la maquette)
            nom = n["nom"] + ("/" if n["dossier"] and n["prof"] else "")
            if n["prof"] == 0:
                nom = core.TERRAIN.name
            ligne = {"nom": nom, "prof": n["prof"], "dossier": n["dossier"], "ici": n.get("ici"),
                     "brume": n.get("brume"), "rel": n["rel"]}
            mq = None
            if n["prof"] == 0:
                mq = (t("esp.camp"), S.PALE)
            elif n["nom"].startswith("."):
                mq = (t("esp.secret"), S.PALE)
            elif n["prof"] == 1 and n["dossier"] and n["nom"] in maison.PIECES:
                p = n["nom"]
                marques = maison.marques(st, p)
                court_ = t("esp.biome." + p)
                if "✓" in marques:
                    mq = ("✓ " + court_, S.VERT)
                    lieux[p] = (court_, "reveille")
                elif "▶" in marques:
                    mq = ("▶ " + court_, S.VERT)
                    lieux[p] = (court_, "en_cours")
                else:
                    mq = (t("esp.endormi"), S.PALE)
                    lieux[p] = (court_, "brume")
            if actif and n["rel"] and actif[1].rstrip("/") == n["rel"]:
                ligne["chemin_actif"] = True
            ligne["marque"] = mq
            arbre.append(ligne)
        # le camp de base, au-dessus du terrain
        arbre.insert(0, {"nom": "~", "prof": 0, "dossier": True, "ici": False, "brume": False, "rel": "~",
                         "marque": (t("esp.camp"), S.PALE)})
        for l in arbre[1:]:
            l["prof"] += 1
        if arbre[1:] and arbre[1]["marque"] and arbre[1]["marque"][0] == t("esp.camp"):
            arbre[1]["marque"] = None
        p = maison.piece_de(st)
        if p in S.LIEUX_CARTE:
            ici_piece = p
            ici_nom = t("esp.biome_long." + p) if p else ""
        return arbre, lieux, ici_piece, ici_nom

    def _envies(self, st):
        lignes, assiette, sat = [], [], ("", S.DOUX)
        if not st:
            return lignes, assiette, sat
        try:
            from . import envies, satiete
            vals = envies.valeurs(st)
            avant = getattr(self, "_vals_envies", {})
            for k in envies.ENVIES:
                v = vals.get(k, 0)
                lignes.append((envies.nom(k), k, v, v - avant.get(k, v) > 0.4))
            if st.get("total") != getattr(self, "_total_envies", None):
                self._vals_envies = vals
                self._total_envies = st.get("total")
            mangees = set(satiete.s_(st).get("assiette", []))
            couleurs = [S.ORANGE, S.JAUNE, S.CYAN, S.VIOLET, S.ROSE, S.BLEU]
            for f, c in zip(satiete.FAMILLES, couleurs):
                assiette.append((t("sat.famille." + f), f in mangees, c))
            e = satiete.etat(st)
            sat = (satiete.nom_etat(e), {"rassasiee": S.VERT, "forme": S.VERT, "affamee": S.ORANGE}.get(e, S.ROUGE))
        except Exception as e:                       # noqa: BLE001
            B.noter(f"envies : {e!r}")
        return lignes, assiette, sat


# ================================================================ GTK 4
class FenetreGtk:
    _surface = B.FenetresGtk._surface            # les images des créatures : le même cache que le bureau

    def __init__(self, ctl):
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo
        import cairo
        self.Gdk = Gdk
        self.Gtk, self.GLib, self.Pango, self.PangoCairo, self.cairo = Gtk, GLib, Pango, PangoCairo, cairo
        self.ctl = ctl
        self.zones = []
        self.echelle = (1.0, 0.0, 0.0)
        self.surfaces = {}
        self.photos = {}
        self.app = Gtk.Application(application_id="fr.terminagotchi.espace")
        self.app.connect("activate", self._activer)

    def lancer(self):
        self.app.run([])

    def _activer(self, app):
        Gtk = self.Gtk
        win = Gtk.ApplicationWindow(application=app)
        win.set_title(t("esp.titre_fenetre"))
        win.set_default_size(1600, 900)
        da = Gtk.DrawingArea()
        da.set_draw_func(self._dessiner)
        da.set_focusable(True)
        win.set_child(da)
        glisser = Gtk.GestureDrag()              # un clic, ou un glisser-déposer (mode rangement)
        glisser.connect("drag-begin", lambda g, x, y: self._appui(x, y))
        glisser.connect("drag-update", lambda g, dx, dy: self._bouger(dx, dy))
        glisser.connect("drag-end", lambda g, dx, dy: self._lacher(dx, dy))
        da.add_controller(glisser)
        clav = Gtk.EventControllerKey()
        clav.connect("key-pressed", self._touche)
        win.add_controller(clav)
        self.da = da
        win.present()
        da.grab_focus()
        self.GLib.timeout_add(int(1000 / IPS), self._image)
        self.GLib.timeout_add(1500, lambda: (self.ctl.jeu(), True)[1])
        self.GLib.timeout_add(5000, lambda: (self.ctl.releve(), True)[1])

    def _image(self):
        try:
            self.ctl.tick()
            self.da.queue_draw()
        except Exception as e:                       # noqa: BLE001
            B.noter(f"espace image : {e!r}")
        return True

    def _clic(self, x, y):
        e, ox, oy = self.echelle
        self.ctl.clic((x - ox) / e, (y - oy) / e, self.zones)

    def _logique(self, x, y):
        e, ox, oy = self.echelle
        return (x - ox) / e, (y - oy) / e

    def _appui(self, x, y):
        self.depart = (x, y)
        self.ctl.appui(*self._logique(x, y), self.zones)

    def _bouger(self, dx, dy):
        self.ctl.bouger(*self._logique(self.depart[0] + dx, self.depart[1] + dy))

    def _lacher(self, dx, dy):
        self.ctl.lacher(*self._logique(self.depart[0] + dx, self.depart[1] + dy), self.zones)

    def _touche(self, ctrl, keyval, keycode, etat):
        Gdk = self.Gdk
        nom = Gdk.keyval_name(keyval) or ""
        ctrl_on = bool(etat & Gdk.ModifierType.CONTROL_MASK)
        c = self.ctl
        if ctrl_on and nom.lower() == "c":
            c.arreter()
        elif ctrl_on and nom.lower() == "l":
            c.lignes = []
        elif nom in ("Return", "KP_Enter"):
            c.entree()
        elif nom == "BackSpace":
            c.effacer()
        elif nom == "Up":
            c.rappeler(-1)
        elif nom == "Down":
            c.rappeler(1)
        elif nom == "Tab":
            c.completer()
        elif nom == "F11":
            c.classe = not c.classe
        elif nom == "Escape":
            c.ile_ouverte = False
        else:
            u = Gdk.keyval_to_unicode(keyval)
            if u and chr(u).isprintable():
                c.taper(chr(u))
        return True

    def _dessiner(self, da, cr, w, h):
        L, Z, (W, H) = S.scene(self.ctl.modele(), self.ctl.t)
        e = min(w / W, h / H)
        ox, oy = (w - W * e) / 2, (h - H * e) / 2
        self.echelle = (e, ox, oy)
        self.zones = Z
        f0 = L[0][5] if L and L[0][0] == "rect" else (9, 11, 16)
        cr.set_source_rgb(f0[0] / 255, f0[1] / 255, f0[2] / 255)
        cr.paint()
        peindre_cairo(self, cr, S.a_l_echelle(L, e, ox, oy))


def peindre_cairo(f, cr, liste):
    """Dessine une liste avec cairo (fenêtre GTK 4). f : l'objet qui garde cairo, Pango, PangoCairo et les caches."""
    import io
    import math as m_
    import pkgutil
    cairo = f.cairo

    def coul(c):
        cr.set_source_rgba(c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)

    def rrect(x, y, w, h, r):
        r = max(0, min(r, w / 2, h / 2))
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -m_.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, m_.pi / 2)
        cr.arc(x + r, y + h - r, r, m_.pi / 2, m_.pi)
        cr.arc(x + r, y + r, r, m_.pi, 3 * m_.pi / 2)
        cr.close_path()

    base = []
    for op in liste:
        k = op[0]
        if k in ("img", "imgt", "arc"):
            base.append(op)
            continue
        if base:
            B.FenetresGtk._peindre_liste(f, cr, base)
            base = []
        if k == "rect":
            _, x, y, w, h, c = op
            coul(c)
            cr.rectangle(x, y, w, h)
            cr.fill()
        elif k == "rrect":
            _, x, y, w, h, r, fo, bo, ep = op
            rrect(x, y, w, h, r)
            if fo:
                coul(fo)
                cr.fill_preserve()
            if bo and ep:
                coul(bo)
                cr.set_line_width(ep)
                cr.stroke()
            else:
                cr.new_path()
        elif k == "ellipse":
            _, cx, cy, rx, ry, fo = op
            cr.save()
            cr.translate(cx, cy)
            cr.scale(max(0.1, rx), max(0.1, ry))
            cr.arc(0, 0, 1, 0, 2 * m_.pi)
            cr.restore()
            coul(fo)
            cr.fill()
        elif k == "cercle":
            _, cx, cy, r, c, ep = op
            cr.arc(cx, cy, r, 0, 2 * m_.pi)
            coul(c)
            cr.set_line_width(ep)
            cr.stroke()
        elif k == "lueur":
            _, cx, cy, r, c = op
            g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
            g.add_color_stop_rgba(0, c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)
            g.add_color_stop_rgba(1, c[0] / 255, c[1] / 255, c[2] / 255, 0)
            cr.set_source(g)
            cr.arc(cx, cy, r, 0, 2 * m_.pi)
            cr.fill()
        elif k == "ligne":
            _, x1, y1, x2, y2, c, ep, ti = op
            coul(c)
            cr.set_line_width(ep)
            if ti:
                cr.set_dash([ti[0], ti[1]], ti[2])
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()
            cr.set_dash([])
        elif k == "poly":
            _, pts, c = op
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.close_path()
            coul(c)
            cr.fill()
        elif k == "photo":
            _, nom, x, y, w, h = op
            s = f.photos.get(nom)
            if s is None and nom not in f.photos:
                data = S.photo_png(nom)
                s = f.photos[nom] = cairo.ImageSurface.create_from_png(io.BytesIO(data)) if data else None
            if s is None:
                continue
            sw, sh = s.get_width(), s.get_height()
            r_ = max(w / sw, h / sh)
            cr.save()
            rrect(x, y, w, h, 9)
            cr.clip()
            cr.translate(x + (w - sw * r_) / 2, y + (h - sh * r_) / 2)
            cr.scale(r_, r_)
            cr.set_source_surface(s, 0, 0)
            cr.paint()
            cr.restore()
        elif k == "texte":
            _, x, y, s, sz, c, gras, ancre, mono = op
            lay = f.PangoCairo.create_layout(cr)
            fd = f.Pango.FontDescription.from_string(("DejaVu Sans Mono, monospace" if mono else
                                                      "Inter, Cantarell, sans-serif") + (" Bold" if gras else ""))
            fd.set_absolute_size(sz * f.Pango.SCALE)
            lay.set_font_description(fd)
            lay.set_text(s, -1)
            tw, th = lay.get_pixel_size()
            dx = {"g": 0, "c": -tw / 2, "d": -tw}[ancre]
            cr.move_to(x + dx, y - th / 2)
            coul(c)
            f.PangoCairo.show_layout(cr, lay)
    if base:
        B.FenetresGtk._peindre_liste(f, cr, base)


# ================================================================ tkinter (repli)
class FenetreTk:
    def __init__(self, ctl, tk):
        self.tk = tk
        self.ctl = ctl
        self.zones = []
        self.echelle = (1.0, 0.0, 0.0)
        self.racine = tk.Tk()
        self.racine.title(t("esp.titre_fenetre"))
        self.racine.geometry("1440x810")
        self.racine.configure(bg="#090b10")
        self.can = tk.Canvas(self.racine, bg="#090b10", highlightthickness=0)
        self.can.pack(fill="both", expand=True)
        self.can.bind("<Button-1>", lambda e: self.ctl.appui(*self._logique(e.x, e.y), self.zones))
        self.can.bind("<B1-Motion>", lambda e: self.ctl.bouger(*self._logique(e.x, e.y)))
        self.can.bind("<ButtonRelease-1>", lambda e: self.ctl.lacher(*self._logique(e.x, e.y), self.zones))
        self.racine.bind("<Key>", self._touche)
        self.photos = {}
        self.images = {}

    def lancer(self):
        self._image()
        self.racine.after(1500, self._jeu)
        self.racine.mainloop()

    def _jeu(self):
        self.ctl.jeu()
        self.racine.after(1500, self._jeu)

    def _clic(self, x, y):
        e, ox, oy = self.echelle
        self.ctl.clic((x - ox) / e, (y - oy) / e, self.zones)

    def _logique(self, x, y):
        e, ox, oy = self.echelle
        return (x - ox) / e, (y - oy) / e

    def _touche(self, ev):
        c = self.ctl
        ks = ev.keysym
        if ev.state & 0x4 and ks.lower() == "c":
            c.arreter()
        elif ks == "Return":
            c.entree()
        elif ks == "BackSpace":
            c.effacer()
        elif ks == "Up":
            c.rappeler(-1)
        elif ks == "Down":
            c.rappeler(1)
        elif ks == "Tab":
            c.completer()
            return "break"
        elif ks == "F11":
            c.classe = not c.classe
        elif ev.char and ev.char.isprintable():
            c.taper(ev.char)

    def _image(self):
        try:
            self.ctl.tick()
            self._dessiner()
        except Exception as e:                       # noqa: BLE001
            B.noter(f"espace tk : {e!r}")
        self.racine.after(int(1000 / 12), self._image)

    def _hex(self, c, fond=None):
        fond = fond or getattr(self, "mix", (15, 17, 24))   # tkinter n'a pas de transparence : mêlée au panneau
        a = c[3] / 255 if len(c) > 3 else 1
        r, g, b = (int(c[i] * a + fond[i] * (1 - a)) for i in range(3))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _dessiner(self):
        can = self.can
        w, h = max(200, can.winfo_width()), max(200, can.winfo_height())
        L, Z, (W, H) = S.scene(self.ctl.modele(), self.ctl.t)
        e = min(w / W, h / H)
        ox, oy = (w - W * e) / 2, (h - H * e) / 2
        self.echelle, self.zones = (e, ox, oy), Z
        th = A.theme(self.ctl.state) if self.ctl.state else A.Theme("sombre")
        self.mix = th.r["panneau"]
        can.configure(bg="#%02x%02x%02x" % th.r["fond"])
        can.delete("all")
        self.images = {}
        for op in S.a_l_echelle(L, e, ox, oy):
            k = op[0]
            if k == "rect":
                _, x, y, ww, hh, c = op
                can.create_rectangle(x, y, x + ww, y + hh, fill=self._hex(c), width=0)
            elif k == "rrect":
                _, x, y, ww, hh, r, fo, bo, ep = op
                can.create_rectangle(x, y, x + ww, y + hh, fill=self._hex(fo) if fo else "",
                                     outline=self._hex(bo) if bo and ep else "", width=max(1, int(ep)) if bo else 0)
            elif k == "ellipse":
                _, cx, cy, rx, ry, c = op
                can.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill=self._hex(c), width=0)
            elif k == "cercle":
                _, cx, cy, r, c, ep = op
                can.create_oval(cx - r, cy - r, cx + r, cy + r, outline=self._hex(c), width=max(1, int(ep)))
            elif k == "ligne":
                _, x1, y1, x2, y2, c, ep, ti = op
                can.create_line(x1, y1, x2, y2, fill=self._hex(c), width=max(1, int(ep)),
                                dash=(int(ti[0]), int(ti[1])) if ti else None)
            elif k == "poly":
                _, pts, c = op
                can.create_polygon(*[v for p in pts for v in p], fill=self._hex(c), outline="")
            elif k == "texte":
                _, x, y, s, sz, c, gras, ancre, mono = op
                can.create_text(x, y, text=s, fill=self._hex(c), anchor={"g": "w", "c": "center", "d": "e"}[ancre],
                                font=("DejaVu Sans Mono" if mono else "DejaVu Sans", -max(6, int(sz)),
                                      "bold" if gras else "normal"))
            elif k == "photo":
                _, nom, x, y, ww, hh = op
                ph = self._photo(nom, int(ww), int(hh))
                if ph:
                    can.create_image(x, y, image=ph, anchor="nw")
            elif k in ("img", "imgt"):
                ph, x, y = self._sprite(op)
                if ph:
                    can.create_image(x, y, image=ph, anchor="nw")

    def _photo(self, nom, w, h):
        cle = (nom, w // 8, h // 8)
        if cle in self.photos:
            return self.photos[cle]
        ph = None
        try:
            from PIL import ImageTk
            im = S.photo_pil(nom)
            if im:
                r_ = max(w / im.width, h / im.height)
                im = im.resize((int(im.width * r_) + 1, int(im.height * r_) + 1))
                im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w,
                              (im.height - h) // 2 + h))
                ph = ImageTk.PhotoImage(im)
        except Exception:                            # noqa: BLE001 — sans PIL : pas de carte dessinée
            ph = None
        self.photos = {k: v for k, v in self.photos.items() if k[0] != nom}
        self.photos[cle] = ph
        return ph

    def _sprite(self, op):
        """Une image de créature (tkinter : agrandie au plus proche, sans déformation fine)."""
        import base64
        if op[0] == "img":
            _, cad, x, y, e, miroir, lisse = op
        else:
            _, cad, ax, ay, e, miroir, lisse, sx, sy, rot, alpha = op
            x, y = ax - cad.ax * e, ay - cad.ay * e
        n = max(1, int(round(e)))
        cle = (cad.cle, id(cad), n, miroir)
        ph = self.images.get(cle)
        if ph is None:
            png = B._png_base64(cad, n, miroir)
            ph = self.tk.PhotoImage(data=png)
            self.images[cle] = ph
        return ph, x, y


# ================================================================ dans le terminal (texte)
def assez_grand():
    try:
        import shutil
        c, l = shutil.get_terminal_size((80, 24))
    except OSError:
        return False
    return c >= 150 and l >= 40


def ecran_texte(ctl, cols, rangs):
    """L'espace de travail en couleurs ANSI : à gauche l'Explorateur et les envies, au centre la vue déployée et le
    terminal, à droite la créature (et son cerveau ou la carte en texte)."""
    from .plateforme import BOLD, DIM, RESET, fg
    from .langue import largeur, ajuster
    m = ctl.modele()
    g_w, d_w = 30, 46
    c_w = cols - g_w - d_w - 4
    gauche = [f"{fg(245)}{BOLD}" + t("esp.explorateur").upper() + RESET]
    for n in m["arbre"][: max(5, rangs // 2 - 3)]:
        coul = 78 if n.get("ici") else (250 if not n.get("brume") else 244)
        mq = n.get("marque")
        s = "  " * min(n["prof"], 4) + n["nom"]
        gauche.append(f"{fg(coul)}{ajuster(s, g_w - 10)}{RESET}" + (f"{DIM}{ajuster(mq[0], 9)}{RESET}" if mq else ""))
    gauche.append("")
    gauche.append(f"{fg(245)}{BOLD}" + t("esp.envies", nom=m["nom"]).upper() + RESET)
    cols_env = {"faim": 215, "jeu": 211, "curiosite": 221, "explorer": 78, "sommeil": 141, "proprete": 80}
    for nom_, cle, v, monte in m["envies"]:
        n = int(max(0, min(100, v)) / 100 * 12)
        gauche.append(f"{ajuster(nom_, 11)} {fg(cols_env.get(cle, 78))}{'█' * n}{fg(238)}{'░' * (12 - n)}{RESET} "
                      f"{int(v):>3}{'↑' if monte else ''}")
    gauche.append(t("esp.assiette") + " " + " ".join((f"{fg(78)}●{RESET}" if mangee else f"{fg(240)}○{RESET}")
                                                     for _f, mangee, _c in m["assiette"]) + f" {DIM}{m['satiete'][0]}{RESET}")
    gauche.append("")
    gauche.append(f"{fg(245)}{BOLD}" + t("esp.equipe").upper() + RESET)
    for _a, nom_, sous, statut, ns, actif in m["equipe_lignes"][:5]:
        gauche.append(f"{BOLD if actif else ''}{ajuster(nom_, 14)}{RESET} {DIM}{ns}{RESET}")
    # le centre : la vue déployée, puis le terminal
    centre = []
    dp = ctl.dep
    if dp:
        centre += D.ecran(dp["ligne"], dp["blocs"], dp["actif"], dp["sorties"], dp["phase"] % 1.0, c_w,
                          ctl.mini.dossier)[:14]
    else:
        centre += [f" {fg(213)}{BOLD}" + t("dep.titre") + RESET, "", f"  {DIM}" + t("esp.deploie_vide") + RESET]
    centre.append(f"{fg(238)}" + "─" * c_w + RESET)
    place = rangs - len(centre) - 3
    for spans_ in ctl.lignes[-max(1, place):]:
        centre.append("".join(f"\033[38;2;{c[0]};{c[1]};{c[2]}m" + ("\033[1m" if g else "") + s + RESET
                              for s, c, g in spans_))
    centre.append(f"{fg(75)}{ctl.mini.invite()}{RESET} {BOLD}{ctl.mini.saisie}{RESET}{fg(78)}█{RESET}")
    # la droite : la créature (texte), son état, puis le cerveau
    droite = [f"{fg(245)}{BOLD}" + t("esp.en_direct", nom=m["nom"]).upper() + RESET +
              f"  {fg(CV.ANSI[ctl.cv.etat])}● {m['etat_nom']}{RESET}"]
    try:
        from . import sprites
        sp, _w = sprites.creature(ctl.state)
        droite += sp
    except Exception:                                # noqa: BLE001
        pass
    if m.get("bulle"):
        droite.append(f"{fg(255)}💬 {sans_marques(m['bulle'])[:d_w - 4]}{RESET}")
    droite.append("")
    code = CV.texte_programme(m["nom"])
    k, genre = ctl.cv.ligne_en_cours(ctl.t)
    droite.append(f"{fg(245)}{BOLD}" + t("esp.onglet.cerveau").upper() + f"{RESET} {DIM}cerveau.sh{RESET}")
    debut = max(0, min(len(code) - 12, (k or 0) - 5))
    for i in range(debut, min(len(code), debut + 12)):
        l = code[i][:d_w - 4]
        droite.append((f"{fg(78)}▌\033[48;5;236m{BOLD}{l}{RESET}" if i == k else f" {DIM}{l}{RESET}"))
    droite.append("  " + "  ".join((f"{fg(CV.ANSI[e])}\033[7m{CV.nom_etat(e)}{RESET}" if e == ctl.cv.etat else
                                    f"{fg(CV.ANSI[e])}{CV.nom_etat(e)}{RESET}") for e in CV.ETATS))
    out = [f"{fg(78)}{BOLD}>_ Terminagotchi{RESET}  {DIM}{m.get('chapitre', '')}{RESET}   "
           f"{BOLD}{m['nom']}{RESET} {DIM}{m['espece_stade']}{RESET}  {fg(78)}● {m['etat_nom']}{RESET} {DIM}"
           f"{m['gains']}{RESET}   {fg(221)}{t('esp.niveau', n=m['niveau'])}{RESET}", ""]
    for i in range(rangs - 3):
        g = gauche[i] if i < len(gauche) else ""
        c = centre[i] if i < len(centre) else ""
        d = droite[i] if i < len(droite) else ""
        out.append(_case(g, g_w) + f"{fg(238)}│{RESET}" + _case(c, c_w) + f"{fg(238)}│{RESET}" + _case(d, d_w))
    out.append(f"{DIM}" + t("esp.texte.touches") + RESET)
    return out


def _case(s, n):
    """s coupé ou complété à n colonnes visibles (les couleurs ne comptent pas)."""
    from .langue import largeur
    vis = re.sub(r"\033\[[0-9;]*m", "", s)
    if largeur(vis) <= n:
        return s + " " * (n - largeur(vis))
    out, w, i = "", 0, 0
    while i < len(s) and w < n - 1:
        m = re.match(r"\033\[[0-9;]*m", s[i:])
        if m:
            out += m.group(0)
            i += len(m.group(0))
            continue
        cw = largeur(s[i])
        if w + cw > n - 1:
            break
        out += s[i]
        w += cw
        i += 1
    return out + "…" + " " * max(0, n - w - 1) + "\033[0m"


def mode_texte(etape, classe=False):
    """L'espace de travail dans le terminal (raw : les touches arrivent une par une)."""
    import shutil
    from .app import Clavier
    ctl = Espace(etape, classe)
    clav = Clavier()
    dernier_jeu = 0.0
    with clav:
        sys.stdout.write("\033[?1049h\033[H\033[2J")
        try:
            while True:
                now = time.monotonic()
                if now - dernier_jeu > 1.5:
                    ctl.jeu()
                    dernier_jeu = now
                ctl.tick()
                c, l = shutil.get_terminal_size((160, 45))
                sys.stdout.write("\033[H" + "\n".join(x + "\033[K" for x in ecran_texte(ctl, c, l)[:l]) + "\033[J")
                sys.stdout.flush()
                k = clav.touche(1 / 10)
                if not k:
                    continue
                if k in ("\x03",):
                    if not ctl.mini.saisie:
                        break
                    ctl.arreter()
                elif k == "\x04" or k == "\x1b":
                    break
                elif k in ("\r", "\n"):
                    ctl.entree()
                elif k in ("\x7f", "\b"):
                    ctl.effacer()
                elif k == "\t":
                    ctl.completer()
                elif k in ("\x1b[A", "UP"):
                    ctl.rappeler(-1)
                elif k in ("\x1b[B", "DOWN"):
                    ctl.rappeler(1)
                elif len(k) == 1 and k.isprintable():
                    ctl.taper(k)
        finally:
            sys.stdout.write("\033[?1049l")
            sys.stdout.flush()


# ================================================================ lancer
def lancer(etape, args=()):
    """tg espace [classe] [texte] : la fenêtre dédiée (GTK 4, sinon tkinter), ou le mode texte."""
    args = [a.lower() for a in args]
    classe = "classe" in args or "class" in args
    force = os.environ.get("TG_ESPACE", "")
    texte = "texte" in args or "text" in args or force == "texte"
    ecran_dispo = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) or os.name == "nt" or \
        sys.platform == "darwin"
    if not texte and ecran_dispo:
        if force != "tk":
            try:
                ctl = Espace(etape, classe)
                FenetreGtk(ctl).lancer()
                return
            except (ImportError, ValueError) as e:
                B.noter(f"espace gtk : {e!r}")
            except Exception as e:                   # noqa: BLE001
                B.noter(f"espace gtk : {e!r}")
        try:
            import tkinter
            ctl = Espace(etape, classe)
            FenetreTk(ctl, tkinter).lancer()
            return
        except Exception as e:                       # noqa: BLE001
            B.noter(f"espace tk : {e!r}")
    if sys.stdout.isatty() and assez_grand():
        mode_texte(etape, classe)
        return
    print(t("esp.trop_petit"))
