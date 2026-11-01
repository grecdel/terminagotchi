"""Captures de la Tour des Ondes (PC), pour les maquettes envoyées au propriétaire.

    python3 pc/outils/capture_ondes.py <dossier de sortie>

Pas besoin d'écran : une vraie partie est créée dans un HOME temporaire (Noisette), la Tour est ouverte (tronc commun
et leçons requises finis). Les commandes du jeu (ondes …, mesh-…) passent par le vrai code ; les commandes de la machine
ne sont lancées que si elles ne font que LIRE (nmcli radio, rfkill list…), et aucun nom de réseau n'est montré. Sorties :
  on_pc_lecon.png        l'écran du jeu (tg) pendant la leçon « Une onde »
  on_pc_onde_mur.png     une onde Wi-Fi accordée, puis LoRa, puis le mur qui les affaiblit
  on_pc_deploie.png      tg deploie "nmcli radio; rfkill list" : les antennes « lit seulement » dans la vue déployée
  on_pc_deploie.gif      la même vue déployée, animée
  on_pc_spectre.png      la règle du spectre, les cartes mélangées, une règle ratée puis rangée
  on_pc_vallee.png       le temps d'émission LoRa, un message trop court, puis le bon SF qui traverse la vallée
  on_pc_maillage.png     le maillage du Terminaworld : la route, un nœud coupé, le message qui trouve un autre chemin
  on_pc_tempete.png      la tempête : trois nœuds coupés sur le chemin, le SOS passe quand même
  on_pc_canaux.png       les canaux (ville EXEMPLE si la machine n'a pas de Wi-Fi) et les radios de la machine
  on_pc_ciel.png         le balcon du ciel : avions fictifs (sans immatriculation) et capteurs anonymisés
  on_pc_repli.png        l'affichage de REPLI tant que l'illustration de la Tour manque (tg ondes)
"""
import io
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_capture_ond_")
os.environ.pop("HISTFILE", None)
os.environ["LC_ALL"] = os.environ.get("LC_ALL", "C.UTF-8")
os.environ["LANG"] = "fr_FR.UTF-8"

from tg import app, core, deploie, histoire, langue, ondes as O  # noqa: E402
from tg.plateforme import RESET, fg  # noqa: E402

sys.path.insert(0, str(RACINE / "pc" / "outils"))
from capture_port import ansi_image  # noqa: E402


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
        h["faits"] += [l for l in lecs if l not in h["faits"]]
        h["chap"] = "ondes"
        h["ouverts"].append("ondes")
        h.setdefault("mondes_annonces", []).extend(["port", "citadelle", "crypte", "machinerie", "ondes"])
        h["faits"] += ["on0"]
        s["step"] = 0
        s["xp"] = 10 * 30 ** 2
        s["annonce"] = "hist.on1.titre"
    core.modifier(ouvrir)
    for c in chaps:
        (core.TERRAIN / histoire.PAR_CHAP[c].get("piece", c)).mkdir(parents=True, exist_ok=True)
    (core.TERRAIN / "ondes").mkdir(parents=True, exist_ok=True)
    st = core.load()
    for rel, txt in O.meubles(st).items():
        p = core.TERRAIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(txt, bytes):
            p.write_bytes(txt)
        else:
            p.write_text(txt, encoding="utf-8")
    app.etape(spontane=False, defis=False)
    app.etape(spontane=False, defis=False)


def session(cmds, ici="ondes"):
    out = []
    d = core.TERRAIN / ici
    invite = f"{fg(78)}noisette@pc{RESET}:{fg(75)}~/terrain_terminagotchi/{ici}{RESET}$ "
    for c in cmds:
        out.append(invite + c)
        mots = shlex.split(c)
        if mots[0] == "ondes" or mots[0].startswith("mesh-"):
            buf = io.StringIO()
            O.commande(mots[1:] if mots[0] == "ondes" else mots, buf)
            out += buf.getvalue().rstrip("\n").split("\n")
        else:
            r = subprocess.run(["bash", "-c", c], cwd=str(d), capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PATH=os.environ.get("PATH", "/usr/bin:/bin")))
            out += (r.stdout + r.stderr).rstrip("\n").split("\n")
        core.modifier(lambda s, c=c: O.surveiller(s, [c]))
    out.append(invite)
    return [l for l in out if l is not None]


def trois_coupes(cible, n=3):
    """Trois nœuds à couper, un par un, toujours sur le chemin du moment, sans jamais isoler la cible."""
    def cherche(coupes):
        if len(coupes) == n:
            return coupes
        r = O.route("camp", cible, coupes)
        for x in (r or [])[1:-1]:
            if O.route("camp", cible, coupes + [x]):
                res = cherche(coupes + [x])
                if res:
                    return res
        return None
    return cherche([]) or []


def main():
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    sortie.mkdir(parents=True, exist_ok=True)
    langue.definir("fr")
    preparer()
    st = core.load()
    lignes = app.render(st, 0, False).rstrip("\n").split("\n")
    ansi_image(lignes, 110, None, 15).convert("RGB").save(sortie / "on_pc_lecon.png")

    lignes = session(["ondes onde wifi24", "ondes onde lora", "ondes mur brique 1"])
    ansi_image(lignes, 110, None, 13).convert("RGB").save(sortie / "on_pc_onde_mur.png")

    ligne = "nmcli radio; rfkill list"
    bl = deploie.blocs(ligne)
    d = str(core.TERRAIN / "ondes")
    ansi_image(deploie.ecran(ligne, bl, 1, None, 0.8, 100, d), 100, None, 15).convert("RGB").save(sortie / "on_pc_deploie.png")
    images = [ansi_image(deploie.ecran(ligne, bl, 1, None, i / 20, 96, d), 96, 24, 15).convert("RGB") for i in range(20)]
    images[0].save(sortie / "on_pc_deploie.gif", save_all=True, append_images=images[1:], duration=140, loop=0)

    st = core.load()
    rep = O.regle_reponse(O._graine(st))
    faux = list(reversed(rep))
    lignes = session(["ondes spectre", "ondes regle", "ondes regle " + " ".join(faux), "ondes regle " + " ".join(rep)])
    ansi_image(lignes, 116, None, 12).convert("RGB").save(sortie / "on_pc_spectre.png")

    st = core.load()
    sf = O.sf_min(O.vallee_m(O._graine(st)))
    lignes = session(["ondes temps", f"ondes vallee {max(7, sf - 1) if sf > 7 else 7}", f"ondes vallee {sf}"])
    ansi_image(lignes, 116, None, 12).convert("RGB").save(sortie / "on_pc_vallee.png")

    lignes = session(["mesh-route", "mesh-envoie feu \"bonjour\"", "mesh-coupe roche", "mesh-envoie feu \"bonjour\"",
                      "mesh-coupe -r"])
    ansi_image(lignes, 116, None, 12).convert("RGB").save(sortie / "on_pc_maillage.png")

    st = core.load()
    cible = O.defi_cible(O._graine(st))
    lignes = session(["ondes defi"] + [f"mesh-coupe {x}" for x in trois_coupes(cible)] + [f"mesh-envoie {cible} \"SOS\""])
    ansi_image(lignes, 116, None, 12).convert("RGB").save(sortie / "on_pc_tempete.png")

    lignes = session(["ondes canaux", "ondes radios", "nmcli radio 2>/dev/null || echo '(pas de nmcli ici)'"])
    ansi_image(lignes, 110, None, 13).convert("RGB").save(sortie / "on_pc_canaux.png")

    lignes = session(["ondes avions", "grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json", "ondes anonyme"])
    ansi_image(lignes, 116, None, 13).convert("RGB").save(sortie / "on_pc_ciel.png")

    lignes = session(["ondes"])
    ansi_image(lignes, 104, None, 16).convert("RGB").save(sortie / "on_pc_repli.png")
    shutil.rmtree(os.environ["HOME"], ignore_errors=True)
    print("captures de la Tour des Ondes écrites dans", sortie)


if __name__ == "__main__":
    main()
