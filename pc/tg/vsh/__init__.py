"""Le terminal du jeu (décision du 2 novembre) : un petit Linux virtuel écrit en Python, sans aucun programme
extérieur. Sous Windows, le jeu ouvre ce terminal au lieu de PowerShell : un shell POSIX (sh) et les commandes des
leçons, qui agissent sur les VRAIS fichiers du terrain (et seulement là). Sous Linux et macOS, le terminal du jeu
reste le vrai bash/zsh ; ce terminal virtuel y sert aux tests (comparé au vrai bash) et à `tg sh`.

    shell.py     l'interprète (variables, $( ), tuyaux, if/for/while/case, fonctions, scripts, tâches de fond)
    syntaxe.py   la lecture d'une ligne en arbre
    vfs.py       les chemins Linux du terminal et les vrais fichiers derrière (écriture limitée au terrain)
    interne.py   les commandes internes (cd, echo, export, alias, read, test, jobs, kill, sh…)
    outils.py    les commandes de fichiers (ls, cat, cp, mv, rm, mkdir, chmod, head, tail, wc, du…)
    texte.py     grep, sort, uniq, cut, tr, paste, diff… ; sed.py, awk.py
    fichiers.py  find, sha256sum, base64, xxd, od, shuf, tar, gzip ; calcul.py (bc, expr) ; base_sql.py (sqlite3)
    git.py       le petit git (le même que celui du téléphone, PetitGit.kt)
    terminal.py  la fenêtre : invite $, historique ↑ ↓, Tab, Ctrl+C, couleurs, le compagnon après chaque commande
"""
from .shell import Entree, Flux, Interrompu, Shell, Sortie  # noqa: F401
from .vfs import Vfs  # noqa: F401


def existe(nom):
    """La commande existe-t-elle dans le terminal du jeu ?"""
    from . import interne, outils
    return nom in outils.TOUS or nom in interne.INTERNES or outils.est_du_jeu(nom)


def commandes():
    from . import interne, outils
    return sorted(set(outils.TOUS) | set(interne.INTERNES))


class CoquilleVirtuelle:
    """Comme coquille.Coquille (un shell qui reste ouvert), mais avec le terminal du jeu : lancer(ligne) →
    (sortie, code, dossier). Utilisé par les tests (comparé au vrai bash) et par les petits terminaux du jeu sous
    Windows (tg mini, l'espace)."""

    def __init__(self, cwd=None, env=None, vfs=None, mode=None, jeu=None, historique=None):
        import os
        self.historique = historique
        self.vfs = vfs or Vfs(mode=mode)
        self.sh = Shell(self.vfs, interactif=False, env={k: v for k, v in (env or {}).items()
                                                        if k in ("LANG", "LC_ALL", "TERM")})
        self.sh.nom = "bash"
        if cwd is not None:
            v = self.vfs.virtuel(str(cwd)) if self.vfs.mode == "windows" else os.path.abspath(str(cwd))
            if v:
                self.sh.cwd = v
                self.sh.vars["PWD"] = v
        if jeu == "auto":                        # les commandes du jeu (tg, carte, atelier…) lancées par le jeu
            from .outils import lanceur_du_jeu
            jeu = lanceur_du_jeu(self.vfs)
        if jeu:
            self.sh.sur_jeu = jeu
        self.cwd = self.vfs.pour_le_jeu(self.sh.cwd)

    def lancer(self, cmd, delai=30, interrompre=None, env=None):
        import threading
        self.vfs.fd.clear()
        if self.historique is not None:          # comme le terminal du jeu : la ligne va dans l'historique
            try:
                with open(self.historique, "a", encoding="utf-8") as f:
                    f.write(cmd.replace("\n", "; ") + "\n")
            except OSError:
                pass
        tampon = Flux("tampon")
        fini = threading.Event()
        res = {}
        self.sh.arret.clear()

        def tourner():
            try:
                res["code"] = self.sh.executer(cmd, Entree(b""), tampon, tampon)
            except Sortie as s:
                res["code"] = s.code
            except Interrompu:
                res["code"] = 130
            except Exception as e:              # noqa: BLE001 — une erreur du terminal ne casse pas le jeu
                import traceback
                tampon.write(f"bash: erreur interne du terminal du jeu : {e!r}\n")
                tampon.write(traceback.format_exc())
                res["code"] = 1
            fini.set()
        fil = threading.Thread(target=tourner, daemon=True)
        fil.start()
        import time
        fin = time.time() + delai
        while not fini.wait(0.05):
            if time.time() > fin or (interrompre and interrompre()):
                self.sh.arret.set()
                fini.wait(3)
                break
        texte = tampon.octets().decode("utf-8", "replace")
        self.cwd = self.vfs.pour_le_jeu(self.sh.cwd)
        return texte, res.get("code", 130), self.cwd

    def fermer(self):
        for t in self.sh.taches:
            t.arret.set()
