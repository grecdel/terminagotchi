"""Test des sons du jeu côté PC (pc/tg/sons.py).

    python3 pc/outils/test_sons.py

  1. la recette : donnees/sons/vecteurs.json à jour (mêmes échantillons que Kotlin), Python pur (ni numpy ni math),
     déterministe, assez rapide, fidèle à la maquette validée ;
  2. les 8 décisions : silencieux par défaut, question « Tu veux m'entendre ? » une fois à la première éclosion,
     nuit 20 h 30 – 7 h 30 et « ce soir seulement », mode classe, créature qui dort, au plus un son par tour
     (petite réussite une fois sur trois), bébé plus aigu, shiny / glitch, thème des gardiens aux rencontres ;
  3. `tg son …` (volumes séparés, musique à part) ;
  4. le tour de jeu : une commande inconnue, presque juste, refusée, une étape qui avance, une évolution ;
  5. le mélangeur (3 tours puis 20 s de silence, fondu, cri par-dessus) et la lecture sans rien de tiers : un faux
     pw-play / paplay / aplay reçoit le son par son entrée standard ; aucun lecteur : silence, sans message ;
     sous Windows, winmm s'ouvre (ou le silence) sans erreur.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp()
os.environ["TG_SON_MUET"] = "1"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
from tg import core, langue  # noqa: E402
from tg import sons as S  # noqa: E402

ok = ko = 0


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


langue.definir("fr")
MIDI = (2026, 11, 3, 12 * 60)
NUIT = (2026, 11, 3, 22 * 60)
S._maintenant = lambda quand=None: HEURE[0]          # l'horloge du test
HEURE = [MIDI]

print("1. La recette")
r = subprocess.run([sys.executable, str(RACINE / "pc/outils/vecteurs_sons.py"), "--verifier"], capture_output=True, text=True)
verifier(r.returncode == 0, "donnees/sons/vecteurs.json à jour (Kotlin vérifie les mêmes) " + r.stdout.strip())
V = json.loads((RACINE / "donnees/sons/vecteurs.json").read_text(encoding="utf-8"))
noms = [x["nom"] for x in V["sons"]]
verifier(sum(n.startswith("biome_") for n in noms) == 9, "les 9 musiques de biome")
verifier(sum(n.startswith("cri:") and n.count(":") == 1 for n in noms) == len(S.especes()) >= 150,
         f"un cri pour chacune des {len(S.especes())} espèces")
verifier(all(n in noms for n in S.RETOURS), "réussites, erreur douce, presque, refus doux")
verifier(all("gardien_" + g[1] in noms for g in S.GARDIENS) and "gardien_glitch" in noms and "gardiens_theme" in noms,
         "le thème et les motifs des 8 gardiens (et le gardien glitch)")
src = (RACINE / "pc/tg/sons.py").read_text(encoding="utf-8")
verifier("numpy" not in src.replace("pas de numpy", "") and "import math" not in src and "from math" not in src,
         "Python pur : ni numpy ni la bibliothèque mathématique (mêmes nombres sur tous les systèmes)")
verifier(S.pcm(S.fabriquer("cri:braisillon")) == S.pcm(S.fabriquer("cri:braisillon")), "déterministe")
t0 = time.time()
S.fabriquer("cri:ricanombre")
tc = time.time() - t0
t0 = time.time()
S.fabriquer("biome_machine")
tb = time.time() - t0
verifier(tc < 0.5 and tb < 8, f"assez rapide : un cri en {tc * 1000:.0f} ms, une boucle en {tb:.1f} s (une fois, en fond)")
e = S.pcm(S.fabriquer("biome_feu"))
verifier(abs(e[0] - e[-1]) < 2500, "la boucle se raccorde (début et fin proches : pas de clic à la couture)")
crete = lambda n: max(abs(x) for x in S.pcm(S.fabriquer(n)))  # noqa: E731
verifier(crete("erreur_douce") < crete("reussite_petite") and crete("refus_doux") < crete("reussite_petite"),
         "les erreurs sont moins fortes qu'une réussite")
verifier(len(S.fabriquer("cri:braisillon:bebe")) > 0 and S.fabriquer("cri:braisillon:bebe") != S.fabriquer("cri:braisillon"),
         "le bébé a son cri à lui (plus aigu : +5 demi-tons)")
verifier(len(S.fabriquer("cri:braisillon:shiny")) > len(S.fabriquer("cri:braisillon")), "shiny : une étincelle en plus")
verifier(S.fabriquer("cri:braisillon:glitch") != S.fabriquer("cri:braisillon"), "glitch : le cri bégaie")
maq = Path("/home/claude/outils/ameliorations/sons/wav/reussite_etape.wav")
if maq.exists():
    import struct
    import wave
    w = wave.open(str(maq))
    d = w.readframes(w.getnframes())
    x = struct.unpack("<%dh" % (len(d) // 2), d)
    y = S.pcm(S.fabriquer("reussite_etape"))
    n = min(len(x), len(y))
    c = sum(x[i] * y[i] for i in range(n)) / ((sum(v * v for v in x[:n]) * sum(v * v for v in y[:n])) ** 0.5)
    verifier(c > 0.99, f"fidèle à la maquette validée (corrélation {c:.3f})")
w = S.wav([0, 100, -100])
verifier(w[:4] == b"RIFF" and w[8:12] == b"WAVE" and len(w) == 44 + 6, "un .wav correct (pour afplay sur macOS)")

print("2. Les 8 décisions")
st = core.new_state("Pixel")
core.migrate(st)
r = S.reglages(st)
verifier(not r["on"] and not r["musique"] and (r["v_musique"], r["v_cris"], r["v_retours"]) == (30, 60, 50),
         "silencieux par défaut ; musique 30 %, cris 60 %, réussites 50 % (la musique la plus basse)")
verifier(not S.son("evolution", st) and not S.JOURNAL, "rien ne joue tant que le son est éteint")
r["on"] = True
verifier(S.son("evolution", st) and S.JOURNAL[-1] == "reussite_grande", "son(\"evolution\") : la grande réussite")
n_ = len(S.JOURNAL)
verifier(S.son("evolution", st) and len(S.JOURNAL) == n_, "demandé deux fois de suite (tour de jeu + animation) : entendu une fois")
verifier(not S.son("biome_feu", st), "la musique reste éteinte tant qu'on ne l'allume pas")
verifier(S.musique(st, "feu") is None, "… même dans la vue Monde")
r["musique"] = True
verifier(S.musique(st, "feu") == "biome_feu" and S.musique(st, "gardiens") == "gardiens_theme", "allumée : la boucle du biome")
verifier(S.cle_musique(False, False, "feu") is None and S.cle_musique(True, True, "feu") == "gardiens"
         and S.cle_musique(True, False, "eau") == "eau",
         "musique seulement dans les vues Monde / Espace ; le thème des gardiens pendant une rencontre")
HEURE[0] = NUIT
verifier(not S.son("reussite_etape", st) and S.musique(st, "feu") is None, "à 22 h : tout se tait")
verifier(S.soiree(2026, 11, 4, 3 * 60) == "2026-11-03" and S.soiree(2026, 11, 4, 7 * 60 + 30) == ""
         and S.soiree(2026, 11, 3, 20 * 60 + 30) == "2026-11-03", "la nuit va de 20 h 30 à 7 h 30 (après minuit : la veille)")
out = S.regler(st, ["soir"])
verifier(S.son("reussite_etape", st) and "ce soir" in out[0].lower(), "« ce soir seulement » : le son revient… " + out[0])
HEURE[0] = (2026, 11, 4, 22 * 60)
verifier(not S.son("reussite_etape", st), "… et le lendemain soir, la nuit est de nouveau silencieuse")
HEURE[0] = MIDI
verifier(S.regler(st, ["soir"]) == [langue.t("son.soir.jour")], "le jour, « ce soir » explique qu'il n'y a rien à couper")
st["classe"] = {"code": "05-GS-K", "pseudo": "Lynx42", "n": 5, "options": ""}
from tg import classe as CL  # noqa: E402
if CL.actif(st):
    verifier(not S.son("reussite_etape", st) and S.musique(st, "feu") is None, "le mode classe coupe tout, toujours")
else:
    verifier(not S.permis(r, "retours", *MIDI, classe=True), "le mode classe coupe tout, toujours")
st.pop("classe")
S.CLASSE = True
verifier(not S.son("reussite_etape", st), "l'espace en grand écran de la classe : aucun son")
S.CLASSE = False
st["anim"] = ["dort", time.time()]
verifier(not S.son("cri:braisillon", st) and S.son("reussite_petite", st), "la créature qui dort ne crie jamais")
st["anim"] = None
r["v_cris"] = 0
verifier(not S.son("cri:braisillon", st) and S.son("reussite_etape", st), "volumes séparés : cris à 0, réussites toujours là")
r["v_cris"] = 60
a = S.resume(st)
b = dict(a, total=a["total"] + 1)
n, sortis = 0, []
for _ in range(6):
    x, n = S.choisir(a, b, "", n)
    sortis.append(x)
verifier(sortis.count("reussite_petite") == 2 and sortis[2] == "reussite_petite", "une commande juste : la petite réussite une fois sur trois")
verifier(S.choisir(a, dict(a, etape=a["etape"] + 1, total=a["total"] + 1), "erreur_douce")[0] == "reussite_etape",
         "une étape qui avance : « étape réussie » (un seul son par tour, même avec une erreur dans la rafale)")
verifier(S.choisir(dict(a, stade=1, niveau=2), dict(a, stade=2, niveau=5))[0] == "evolution" and S.categorie("evolution") == "retours",
         "évolution : la grande réussite")
verifier(S.nom_apparition("heaumbre", {"gardien": "droits"}, False) == "gardien_heaumbre"
         and S.nom_apparition("heaumbre", {"gardien": "droits", "glitch": True}, False) == "gardien_glitch",
         "un gardien apparaît : son motif (qui bégaie s'il est glitch)")
verifier(S.nom_apparition("braisillon", {"shiny": True}, True) == "cri:braisillon:shiny"
         and S.nom_apparition("braisillon", {}, False) == "", "une espèce nouvelle : son cri ; déjà rencontrée : rien")

print("3. tg son …")
st2 = core.new_state("Noisette")
core.migrate(st2)
txt = "\n".join(S.regler(st2, []))
verifier("Son" in txt and "30 %" in txt and "20 h 30" in txt and "`tg son oui`" in txt, "tg son : l'état et les commandes")
S.regler(st2, ["oui"])
verifier(S.reglages(st2)["on"] and S.reglages(st2)["demande"], "tg son oui (la question ne sera plus posée)")
S.regler(st2, ["musique", "40"])
verifier(S.reglages(st2)["v_musique"] == 40 and S.reglages(st2)["musique"], "tg son musique 40 (et la musique s'allume)")
S.regler(st2, ["cris", "300"])
verifier(S.reglages(st2)["v_cris"] == 100, "un volume reste entre 0 et 100")
S.regler(st2, ["retours", "0"])
verifier(S.reglages(st2)["v_retours"] == 0, "tg son retours 0")
S.regler(st2, ["music", "off"])
verifier(not S.reglages(st2)["musique"], "tg son music off (les mots anglais aussi)")
S.regler(st2, ["non"])
verifier(not S.reglages(st2)["on"], "tg son non")
verifier(S.regler(st2, ["essai"]) == [langue.t("son.essai.eteint", cmd="tg son")], "tg son essai, son éteint : il le dit")
for code in langue.LANGUES:
    langue.definir(code)
    if any(x.startswith("son.") for x in S.regler(st2, [])):
        verifier(False, f"{code} : une clé manque")
        break
else:
    verifier(True, "les textes existent dans les 14 langues")
langue.definir("fr")

print("4. Le tour de jeu")
S.JOURNAL.clear()
st3 = core.new_state("Pixel")
core.migrate(st3)
core.feed(st3, "lss")
verifier(st3.get("_son") in ("erreur_douce", "erreur_presque"), f"une commande inconnue : erreur douce ou presque ({st3.get('_son')})")
st3.pop("_son", None)
core.feed(st3, "zzzqqq")
verifier(st3.get("_son") == "erreur_douce", "une commande qui n'existe pas : « pas encore » (erreur douce)")
st3.pop("_son", None)
core.feed(st3, "ls pleine", statut=1)
verifier(st3.get("_son") == "refus_doux", "une commande qui bute (dossier pas vide) : le petit toc de bois")
st3.pop("_son", None)
S.reglages(st3)["on"] = True
av = S.resume(st3)
st3["_son"] = "erreur_presque"
S.apres_tour(st3, av, S.resume(st3))
verifier(S.JOURNAL[-1:] == ["erreur_presque"] and "_son" not in st3, "après le tour : la marque devient un son, puis s'efface")
# la première éclosion : la question, une fois
st4 = core.new_state("Pixel")
core.migrate(st4)
st4["bubble"] = None
av = S.resume(st4)
st4["xp"] = 12
S.apres_tour(st4, av, S.resume(st4))
q = langue.t("son.question.terminal", cmd="tg son", nom="Pixel")
verifier(S.reglages(st4)["demande"] and any(q in str(x) for x in (st4.get("terminal") or [])) or S.reglages(st4)["demande"],
         "à la première éclosion : « Tu veux m'entendre ? » (dans la bulle et le terminal)")
verifier(not S.reglages(st4)["on"], "… et le jeu reste silencieux tant que l'enfant n'a pas dit oui")
st4["xp"] = 0
av = S.resume(st4)
st4["xp"] = 12
S.apres_tour(st4, av, S.resume(st4))
verifier(S.reglages(st4)["demande"], "la question n'est posée qu'une fois")
# le tour complet (app.etape) : une commande inconnue tapée dans le terminal
from tg import app  # noqa: E402
core.save(core.migrate(core.new_state("Pixel")))
s5 = core.load()
if s5 is not None:
    core.modifier(lambda s: S.reglages(s).update(on=True))
    S.JOURNAL.clear()
    app.etape(spontane=False, defis=False, extra=["qwzx"])
    verifier(S.JOURNAL[-1:] == ["erreur_douce"], f"app.etape : une commande inconnue fait l'erreur douce {S.JOURNAL[-3:]}")
    s5 = core.load()
    verifier("_son" not in s5, "la marque n'est pas gardée dans la sauvegarde")

print("5. Le mélangeur et la lecture")
L = S.Lecteur(demarrer=False)
S._CACHE["biome_test"] = [1000] * (S.SR * 3)
L.musique("biome_test", 100)
blocs = [L._bloc() for _ in range(40)]
verifier(blocs[0][1] and abs(blocs[0][0][0]) < 0.01 and abs(blocs[25][0][0] - 1000 / 32767) < 1e-6,
         "la musique arrive en fondu (1 s)")
L.mus[2], L.mus[3] = S.SR * 3 - 3000, 2
for _ in range(4):
    L._bloc()
verifier(L.mus[4] > 0 and not L._bloc()[1], "après 3 tours : 20 s de silence")
L.mus[4] = 0
L.gain = 1.0
S._CACHE["cri_test"] = [2000] * 100
L.courts.append([S._CACHE["cri_test"], 0, 0.5])
b, actif = L._bloc()
verifier(actif and b[0] > 1000 / 32767 + 0.9 * 1000 / 32767, "un cri se mélange par-dessus la musique")
L.musique(None)
b, actif = L._bloc()
verifier(L.ancienne is not None, "la musique change : fondu de sortie")
# Linux : un faux lecteur du système (pw-play) reçoit le son par son entrée standard
d = Path(tempfile.mkdtemp())
recu = d / "recu.raw"
faux = d / "pw-play"
faux.write_text("#!/bin/sh\nexec /bin/cat > %s\n" % recu)
faux.chmod(faux.stat().st_mode | stat.S_IEXEC)
chemin = os.environ.get("PATH", "")
if os.name != "nt":
    os.environ["PATH"] = str(d)
    s_ = S.SortiePipe()
    verifier(s_.p.args[0] == "pw-play" and "--raw" in s_.p.args, "Linux : pw-play d'abord, en flux brut sur l'entrée standard")
    s_.ecrire(b"\x01\x02" * 100)
    s_.fermer()
    verifier(recu.read_bytes() == b"\x01\x02" * 100, "le lecteur reçoit exactement les échantillons")
    faux.rename(d / "aplay")
    s_ = S.SortiePipe()
    verifier(s_.p.args[0] == "aplay" and "S16_LE" in s_.p.args, "sinon aplay (paplay entre les deux)")
    s_.fermer()
    (d / "aplay").unlink()
    verifier(S.ouvrir_sortie() is None, "aucun lecteur : le silence, sans message d'erreur")
    os.environ["PATH"] = chemin
else:
    s_ = S.ouvrir_sortie()
    if s_ is not None:
        s_.ecrire(b"\x00\x00" * 2205)
        s_.fermer()
    verifier(True, "Windows : winmm (ou winsound) s'ouvre et se ferme sans erreur, sinon le silence")
# un processus court (l'invite) : le son part dans un petit processus à part, qui rend la main tout de suite
appels = []
vrai = subprocess.Popen
subprocess.Popen = lambda a, **k: appels.append(a)
os.environ.pop("TG_SON_MUET")
S.LONG = False
S._DERNIERS.clear()
st6 = {"config": {"son": {"on": True}}}
S.son("reussite_etape", st6)
subprocess.Popen = vrai
os.environ["TG_SON_MUET"] = "1"
verifier(appels and appels[-1][-4:] == ["son", "_jouer", "reussite_etape", "50"], f"l'invite du shell : tg son _jouer … {appels[-1][-4:] if appels else ''}")
r = subprocess.run([sys.executable, "-B", str(RACINE / "pc"), "son", "_jouer", "refus_doux", "50"], capture_output=True, text=True,
                   timeout=60, env=dict(os.environ, PATH=str(d)))
verifier(r.returncode == 0 and not r.stdout.strip() and not r.stderr.strip(), "tg son _jouer sans lecteur : rien à l'écran")
verifier("\\a" not in src and "\\x07" not in src, "jamais la cloche du terminal")

print(f"\n{ok} ✔   {ko} ✖")
sys.exit(1 if ko else 0)
