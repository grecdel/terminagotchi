"""Captures de l'Observatoire de l'IA (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_observatoire.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), l'Observatoire est ouvert (tronc
commun fini). Les commandes du jeu (observatoire, assistant, agent, devine-type, devine-mot) passent par le vrai code ;
les autres (wc, diff, sort, cut, tr, paste, sh…) sont lancées pour de vrai, mais SEULEMENT dans le terrain temporaire.
Aucune vraie IA, aucun réseau. Sorties :
  ob_pc_lecon.png      l'écran du jeu (tg) pendant la leçon « Donner une mission »
  ob_pc_mission.png    la consigne floue, la consigne claire, assistant mission.txt > rapport.txt
  ob_pc_verifier.png   wc -l, diff, sh test.sh : l'assistant a oublié une ligne
  ob_pc_devineur.png   le devineur apprend sur 20 créatures, son cerveau, il se trompe sur la 21e
  ob_pc_biais.png      le biais du volcan : uniq -c, 1 sur 5, puis 5 sur 5 avec des exemples variés
  ob_pc_mots.png       tr | sort | uniq -c, les paires, devine-mot suite et phrase
  ob_pc_fausses.png    les 5 réponses de l'assistant, les vérifications, les 2 fausses démasquées
  ob_pc_agent.png      le journal de l'agent, accepter le danger (jamais lancé), le refuser, Ctrl+C
  ob_pc_urgence.png    l'équipe : l'agent Copieur s'emballe, l'arrêt d'urgence, les tests, le bilan
  ob_pc_deploie.png    tg deploie "sort creatures.txt | diff - tri.txt" : la lunette dans la vue déployée
  ob_pc_deploie.gif    la même vue déployée, animée
  ob_pc_repli.png      l'affichage de REPLI tant que l'illustration de l'Observatoire manque (tg observatoire)
"""
import io
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_obs_")
os.environ.pop("HISTFILE", None)
os.environ.pop("CLE_API", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"
os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
os.environ["GIT_PAGER"] = "cat"

from tg import app, core, deploie, histoire, langue, observatoire as O  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402

JEU = {"observatoire": O.commande, "assistant": O.commande_assistant, "agent": O.commande_agent,
       "devine-type": O.commande_devine_type, "devine-mot": O.commande_devine_mot}


def preparer():
    import builtins
    builtins.input = lambda p="": "Noisette"
    app.creer_si_besoin(avec_intro=False)
    chaps, lecs = O._besoin()

    def ouvrir(s):
        h = histoire.h_(s)
        for c in chaps:
            for lid in histoire.PAR_CHAP[c]["lecons"]:
                if lid not in h["faits"]:
                    h["faits"].append(lid)
            if c not in h.setdefault("ailes", []):
                h["ailes"].append(c)
        h["chap"] = "observatoire"
        h["ouverts"].append("observatoire")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire"])
        h["faits"] += ["ob0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.ob1.titre"
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "observatoire").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in O.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="observatoire"):
    out = []
    d = core.TERRAIN / ici
    d.mkdir(parents=True, exist_ok=True)
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        ctrl_c = c.endswith("#^C")
        c = c.removesuffix("#^C").strip()
        out.append(invite + c)
        mots = shlex.split(c.split(">")[0]) if c.split()[0] in JEU else []
        if mots and mots[0] in JEU:
            buf, err = io.StringIO(), io.StringIO()
            vieux = os.getcwd()
            os.chdir(d)
            try:
                if mots[0] == "assistant":
                    JEU[mots[0]](mots[1:], buf, err)
                elif mots[0] == "agent" and mots[1:] == ["boucle"]:
                    p = subprocess.Popen([sys.executable, "-c", f"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); "
                                          "from tg import observatoire; observatoire.commande_agent(['boucle'])"],
                                         cwd=str(d), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    time.sleep(1.4)
                    p.send_signal(signal.SIGINT)
                    buf.write(p.communicate(timeout=30)[0].replace("\n⏹", "^C\n⏹"))
                else:
                    JEU[mots[0]](mots[1:], buf)
            finally:
                os.chdir(vieux)
            if ">" in c:
                (d / c.split(">")[1].strip()).write_text(buf.getvalue(), encoding="utf-8")
                out += err.getvalue().rstrip("\n").split("\n")
            else:
                out += (err.getvalue() + buf.getvalue()).rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            txt = (r.stdout + r.stderr).rstrip("\n")
            if txt:
                out += txt.split("\n")
        if ctrl_c:
            pass
        st = core.modifier(lambda s, c=c: O.meubler(s, "ob9", 0) if (core.TERRAIN / "observatoire/equipe/journal_equipe.txt").exists() else None)
    out.append(invite)
    return [l for l in out if l is not None]


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "ob_pc_lecon.png")

    st = core.load()
    gr = O._graine(st)
    lignes = session(["cat mission_floue.txt", "assistant mission_floue.txt",
                      'echo "Compte les créatures Feu dans creatures.txt" > mission.txt',
                      "assistant mission.txt > rapport.txt", "cat rapport.txt"], ici="observatoire/missions")
    ansi_image(lignes, 118, None, 13).convert("RGB").save(sortie / "ob_pc_mission.png")

    O.poser_verifier()
    lignes = session(["assistant mission_tri.txt > tri.txt", "wc -l creatures.txt tri.txt", "sort creatures.txt | diff - tri.txt",
                      "sh test.sh", "observatoire oubli " + O.trier_assistant(O.texte_types().splitlines(), gr)[1].split()[0],
                      "sort creatures.txt > tri.txt && sh test.sh"], ici="observatoire/missions")
    ansi_image(lignes, 118, None, 13).convert("RGB").save(sortie / "ob_pc_verifier.png")

    O.poser_devineur()
    lignes = session(["head -5 exemples.txt", "awk '{print $4}' exemples.txt | sort | uniq -c", "devine-type apprends exemples.txt",
                      "grep -E '^(famille|lieu) +(Démons|brume)' cerveau.txt", "cat nouvelle.txt", "devine-type teste nouvelle.txt",
                      "observatoire piege famille"], ici="observatoire/devineur")
    ansi_image(lignes, 118, None, 12).convert("RGB").save(sortie / "ob_pc_devineur.png")

    O.poser_biais()
    lignes = session(["cut -d ' ' -f 3 volcan.txt | sort | uniq -c", "cut -d ' ' -f 4 volcan.txt | sort | uniq -c",
                      "devine-type apprends volcan.txt", "devine-type teste autres.txt", "devine-type apprends exemples.txt",
                      "devine-type teste autres.txt"], ici="observatoire/devineur")
    ansi_image(lignes, 118, None, 11).convert("RGB").save(sortie / "ob_pc_biais.png")

    O.poser_mots()
    lignes = session(["tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -5", "tr ' ' '\\n' < histoire.txt > mots.txt",
                      "tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -5",
                      "devine-mot suite le", "devine-mot phrase le", "devine-mot phrase le"], ici="observatoire/mots")
    ansi_image(lignes, 118, None, 11).convert("RGB").save(sortie / "ob_pc_mots.png")

    fausses = " ".join(str(n) for n, _i, f in O.questions(gr) if f)
    lignes = session(["assistant questions", "wc -l devineur/exemples.txt", "echo $((17 % 5))",
                      "tr ' ' '\\n' < mots/histoire.txt | sort | uniq -c | sort -rn | head -1", f"assistant fausses {fausses}"])
    ansi_image(lignes, 122, None, 12).convert("RGB").save(sortie / "ob_pc_fausses.png")

    O.poser_chantier()
    dg = O.dangereuse(gr)
    lignes = session(["agent lance", "git --no-pager diff --color=always", f"agent accepte {dg}", f"agent refuse {dg}", "agent valide",
                      "agent boucle"], ici="observatoire/chantier")
    ansi_image(lignes, 118, None, 11).convert("RGB").save(sortie / "ob_pc_agent.png")

    session(["observatoire equipe", "observatoire decoupe " + " ".join(O.decoupe_reponse(gr)),
             "observatoire consigne " + next(n for n, _i, r_ in O.consigne_cartes(gr) if r_ == "true")])
    lignes = session(["agent equipe", "ls copies | wc -l", "ls copies | wc -l", "agent stop", "ls copies | wc -l",
                      f"agent refuse {O.dangereuse(gr, 'equipe')}", "sh tests.sh", "wc -l < liste.txt > compte.txt", "sh tests.sh",
                      "agent bilan"], ici="observatoire/equipe")
    ansi_image(lignes, 118, None, 11).convert("RGB").save(sortie / "ob_pc_urgence.png")

    ligne = "sort creatures.txt | diff - tri.txt"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "observatoire" / "missions")
    ansi_image(deploie.ecran(ligne, bl, 4, None, 0.7, 100, d), 100, None, 15).convert("RGB").save(sortie / "ob_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 4, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "ob_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    lignes = session(["observatoire"])
    ansi_image(lignes, 114, None, 16).convert("RGB").save(sortie / "ob_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de l'Observatoire écrites dans", sortie)


if __name__ == "__main__":
    main()
