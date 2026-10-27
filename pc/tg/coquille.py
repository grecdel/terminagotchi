"""Un shell qui reste ouvert d'une commande à l'autre (comme un vrai terminal) : le dossier courant, `cd -`,
les alias (`alias miam=…` puis `miam`), les variables, les tâches de fond (`sleep 300 &`, `jobs`, `kill %1`) et
`cd x && ls` marchent comme chez l'enfant. Chaque commande renvoie sa sortie, son code de sortie ($?) et le dossier
d'arrivée ($PWD). Utilisé par `tg mini` et par les tests qui jouent un enfant (sim_suiveur, personas).
"""
import os
import select
import signal
import subprocess
import time
import uuid


class Coquille:
    def __init__(self, cwd=None, env=None, shell="bash"):
        self.marque = "__tg_fin_" + uuid.uuid4().hex[:12]
        self.env = dict(env or os.environ)
        self.cwd = str(cwd or os.path.expanduser("~"))
        self.shell = shell
        self.p = None
        self._demarrer()

    def _demarrer(self):
        self.p = subprocess.Popen([self.shell, "--norc", "--noprofile"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, cwd=self.cwd, env=self.env, start_new_session=True)
        self._ecrire("shopt -s expand_aliases 2>/dev/null; exec 2>&1\n")

    def _ecrire(self, texte):
        self.p.stdin.write(texte.encode("utf-8"))
        self.p.stdin.flush()

    def lancer(self, cmd, delai=30):
        """(sortie, code, dossier) d'une ligne de commande. Une commande qui ne s'arrête pas est interrompue."""
        if self.p.poll() is not None:              # `exit` tapé : un nouveau shell, dans le dernier dossier
            self._demarrer()
        # la ligne seule (les alias définis à la ligne d'avant s'appliquent), l'entrée fermée (cat tout seul…)
        self._ecrire(f"{cmd}\n" if cmd.strip().startswith("alias ") else f"{{ {cmd}\n}} </dev/null\n")
        self._ecrire(f"printf '\\n{self.marque} %s %s\\n' \"$?\" \"$PWD\"\n")
        brut, fin = b"", time.time() + delai
        cle = ("\n" + self.marque + " ").encode()
        while cle not in brut:
            reste = fin - time.time()
            if reste <= 0:
                try:
                    os.killpg(self.p.pid, signal.SIGINT)
                except OSError:
                    pass
                fin = time.time() + 3
                if b"__tg_coupe" in brut:
                    break
                brut += b"__tg_coupe"
                continue
            r, _, _ = select.select([self.p.stdout], [], [], min(reste, 0.5))
            if r:
                x = os.read(self.p.stdout.fileno(), 65536)
                if not x:
                    break
                brut += x
        texte = brut.decode("utf-8", "replace").replace("__tg_coupe", "")
        avant, _, apres = texte.partition("\n" + self.marque + " ")
        code, _, dossier = apres.strip().partition(" ")
        try:
            code = int(code)
        except ValueError:
            code = 130
        if dossier:
            self.cwd = dossier.strip()
        return avant, code, self.cwd

    def fermer(self):
        try:
            os.killpg(self.p.pid, signal.SIGTERM)
        except OSError:
            pass
