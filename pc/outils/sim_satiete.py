"""Simulation de 14 jours de la satiété, avec plusieurs rythmes de jeu (le vrai jeu, de vraies commandes).

    python3 pc/outils/sim_satiete.py [--rapport fichier.txt]

Un enfant de 7 ans joue 20 minutes (30 commandes, une toutes les 40 s, à 17 h) : il tape ce que l'écran montre
(la commande de l'étape, comme pc/outils/sim_suiveur.py) ; quand l'histoire est finie, des commandes variées.
L'horloge est simulée (time.time), du lundi 2 novembre 2026 au dimanche 15, heure de Paris. Trois rythmes :
  - « tous les jours »       : 14 séances ;
  - « un jour sur deux »     : 7 séances ;
  - « une semaine d'absence » : jours 1-3, rien pendant 7 jours, puis jours 11-14.
Chaque rythme tourne dans son propre dossier (un sous-processus). Vérifie :
  - l'apprentissage n'est jamais bloqué : aucune commande de remplissage après le réveil, aucun blocage, les
    leçons avancent à chaque séance tant qu'il en reste ;
  - jamais de mort, rien n'est perdu : XP (avec la réserve) et stade ne baissent jamais ;
  - tous les jours : jamais affamée au début d'une séance, Bébé → Ado au plus tôt au 3e jour soigné ;
  - un jour sur deux : jamais en veille ;
  - une semaine d'absence : affamée ou en veille au retour, de nouveau en forme pendant la séance, puis tout repart.
"""
import builtins
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
RYTHMES = {"tous_les_jours": list(range(14)), "un_jour_sur_deux": list(range(0, 14, 2)),
           "semaine_absence": [0, 1, 2, 10, 11, 12, 13]}
PAR_SEANCE = 30
LIBRES = ["pwd", "ls", "date", "whoami", "ls -a", "echo miam", "cat ~/terrain_terminagotchi/nid/repas.txt", "id",
          "uptime", "df -h", "hostname", "mkdir -p ~/terrain_terminagotchi/jeu/boite", "grep pomme -r ~/terrain_terminagotchi/nid",
          "head -n 2 /etc/hostname", "wc -l /etc/hostname", "cal", "uname", "free", "touch ~/terrain_terminagotchi/jeu/note.txt"]


def un_rythme(nom):
    jours = RYTHMES[nom]
    os.environ["HOME"] = tempfile.mkdtemp(prefix=f"tg_simsat_{nom}_")
    os.environ["LANG"] = "fr_FR.UTF-8"
    os.environ["TZ"] = "Europe/Paris"
    time.tzset()
    os.environ.pop("HISTFILE", None)
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        os.environ[k] = "http://127.0.0.1:9"
    horloge = [time.mktime((2026, 11, 2, 16, 50, 0, 0, 0, -1))]
    time.time = lambda: horloge[0]                       # l'horloge simulée (tout le jeu lit time.time)
    sys.path.insert(0, str(ICI.parent))
    from tg import app, core, explo, histoire, satiete as S  # noqa: E402
    from tg.coquille import Coquille  # noqa: E402
    home = Path.home()
    (home / ".bash_history").touch()
    builtins.input = lambda p="": "Pixel"
    app.creer_si_besoin()
    explo.tick = lambda *a, **k: None                    # pas de monstres : on mesure l'histoire et la faim
    shell = Coquille(home, env=dict(os.environ, LC_ALL="C.UTF-8"))
    cwd = [home]
    sortie = [""]

    def tape(cmd):
        sortie[0], code, d = shell.lancer(cmd)
        cwd[0] = Path(d)
        with open(home / ".bash_history", "a") as f:
            f.write(cmd + "\n")
        horloge[0] += 40
        return app.etape(spontane=False, defis=False, cwd=str(cwd[0]), statut=code)

    def a_taper(st, les):
        c = les["steps"][st["step"]]["cmd"]
        if c.startswith("sleep 300"):
            return "sleep 1 &"
        if c.startswith("echo ?"):
            return c.replace("?", (sortie[0].strip().split() or ["0"])[-1], 1)
        return c

    st = app.etape(spontane=False, defis=False)
    lignes, problemes = [], []
    grind_apres_reveil = 0
    total_avant = -1
    libre = 0
    for j in range(14):
        debut = time.mktime((2026, 11, 2 + j, 17, 0, 0, 0, 0, -1))
        if j not in jours:
            continue
        horloge[0] = debut
        st = app.etape(spontane=False, defis=False)
        etat_debut, faim_debut = S.etat(st), st["hunger"]
        faits_avant = len(histoire.h_(st)["faits"])
        dernier = []
        for _ in range(PAR_SEANCE):
            les, _e = histoire.lecon_courante(st)
            h = histoire.h_(st)
            if not les:
                reste = [a for a in histoire.AILES if not histoire.fini(st, a)]
                if not histoire.fini(st, "coeur") and h["chap"] not in ("reveil", "nid") and (reste or histoire.ouvert(st, "coeur")):
                    c = f"cd ~/terrain_terminagotchi/{histoire.PAR_CHAP[reste[0]]['piece']}" if reste else "cd ~/terrain_terminagotchi/coeur"
                else:
                    c = LIBRES[libre % len(LIBRES)]
                    libre += 1
            elif core.level(st["xp"]) < les["niveau"]:
                c = core.faim_d_apprendre(st, les["niveau"])[0][0]
                if les["chap"] != "reveil":
                    grind_apres_reveil += 1
            else:
                c = a_taper(st, les)
                ecran = app.render(st, 0, False)
                import re
                m = re.search(r"(cd ~/[^\s`\x1b]+)", (st.get("indice_lecon") or "") + " " +
                              " ".join(l for l in ecran.splitlines() if "📁" in l))
                if m and m.group(1) != c and not c.startswith("cd ") and dernier[-1:] != [m.group(1)] \
                        and Path(os.path.expanduser(m.group(1)[3:])).resolve() != cwd[0]:
                    c = m.group(1)
            dernier.append(c)
            if len(dernier) >= 5 and len(set(dernier[-5:])) == 1 and histoire.lecon_courante(st)[0]:
                problemes.append(f"jour {j + 1} : blocage sur « {c} »")
                break
            st = tape(c)
        s = S.s_(st)
        total = st["xp"] + s["reserve"]
        if total < total_avant:
            problemes.append(f"jour {j + 1} : XP perdue ({total_avant} → {total})")
        total_avant = total
        reste_lecons = histoire.lecon_courante(st)[0] is not None or faits_avant < len(histoire.h_(st)["faits"])
        lignes.append({"jour": j + 1, "debut": etat_debut, "faim_debut": round(faim_debut, 1), "fin": S.etat(st),
                       "faim_fin": round(st["hunger"], 1), "assiette": S.nb_assiette(st), "jours_soignes": s["jours"],
                       "serie": s["serie"], "niveau": core.level(st["xp"]), "stade": core.stage(core.level(st["xp"])),
                       "reserve": s["reserve"], "lecons": len(histoire.h_(st)["faits"]),
                       "lecons_jour": len(histoire.h_(st)["faits"]) - faits_avant, "chapitres": len(histoire.h_(st)["ailes"]),
                       "avance": reste_lecons})
    print(json.dumps({"lignes": lignes, "problemes": problemes, "grind": grind_apres_reveil}))


def principal():
    ok = ko = 0
    out = []

    def verifier(c, m):
        nonlocal ok, ko
        ok, ko = ok + bool(c), ko + (not c)
        out.append(("  ✔ " if c else "  ✖ ") + m)
        print(out[-1])

    res = {}
    for nom in RYTHMES:
        r = subprocess.run([sys.executable, __file__, "--rythme", nom], capture_output=True, text=True, timeout=3000)
        try:
            res[nom] = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            print(r.stdout[-2000:], r.stderr[-3000:])
            res[nom] = {"lignes": [], "problemes": ["la simulation a planté"], "grind": -1}
    noms = {"rassasiee": "rassasiée", "forme": "en forme", "affamee": "affamée", "veille": "en veille", "repos": "repos"}
    for nom, r in res.items():
        out.append(f"\n{nom.replace('_', ' ')}")
        print(out[-1])
        out.append(" jour | début            | fin              | assiette | jours soignés | série | niveau (stade) | réserve | leçons (+jour)")
        print(out[-1])
        for x in r["lignes"]:
            out.append(f"  {x['jour']:>3} | {noms[x['debut']]:<10} {x['faim_debut']:>5} | {noms[x['fin']]:<10} {x['faim_fin']:>5} |"
                       f"   {x['assiette']}/6    | {x['jours_soignes']:>7}       | {x['serie']:>4}  | {x['niveau']:>4} ({x['stade']})       |"
                       f" {x['reserve']:>5}   | {x['lecons']:>3} (+{x['lecons_jour']})")
            print(out[-1])
        verifier(not r["problemes"], f"{nom} : aucun blocage, rien de perdu {r['problemes'][:3]}")
        verifier(r["grind"] == 0, f"{nom} : aucune commande de remplissage après le réveil ({r['grind']})")
        stades = [x["stade"] for x in r["lignes"]]
        verifier(stades == sorted(stades), f"{nom} : le stade ne baisse jamais {stades}")
        verifier(all(x["avance"] or x["chapitres"] >= 10 for x in r["lignes"]),
                 f"{nom} : chaque séance fait avancer les leçons (tant qu'il en reste)")
    a = res["tous_les_jours"]["lignes"]
    verifier(a and all(x["debut"] in ("rassasiee", "forme") for x in a),
             f"tous les jours : jamais affamée au début d'une séance {[x['debut'] for x in a]}")
    ado = next((x for x in a if x["stade"] >= 2), None)
    verifier(ado is not None and ado["jours_soignes"] >= 3, f"tous les jours : Bébé → Ado au jour {ado and ado['jour']} "
             f"(après {ado and ado['jours_soignes']} jours soignés)")
    verifier(a[-1]["serie"] >= 14 and a[-1]["jours_soignes"] >= 14, f"tous les jours : série de {a[-1]['serie']} jours")
    b = res["un_jour_sur_deux"]["lignes"]
    verifier(b and all(x["debut"] in ("rassasiee", "forme") for x in b),
             f"un jour sur deux : en forme à chaque retour {[x['debut'] for x in b]}")
    verifier(any(x["stade"] >= 2 for x in b), f"un jour sur deux : elle grandit quand même (stade {b[-1]['stade']})")
    c = res["semaine_absence"]["lignes"]
    retour = next((x for x in c if x["jour"] == 11), None)
    verifier(retour and retour["debut"] in ("affamee", "veille") and retour["fin"] in ("forme", "rassasiee"),
             f"une semaine d'absence : affamée (jamais morte) au retour, de nouveau en forme pendant la séance "
             f"({retour and retour['debut']} {retour and retour['faim_debut']} → {retour and retour['fin']})")
    verifier(retour and retour["serie"] >= 1, f"une semaine d'absence : la série n'est pas perdue en entier ({retour and retour['serie']})")
    verifier(b and b[-1]["serie"] >= 12, f"un jour sur deux : les jours sans jeu finis en forme comptent (série {b and b[-1]['serie']})")
    out.append(f"\n{ok} réussis, {ko} échoués")
    print(out[-1])
    if "--rapport" in sys.argv:
        Path(sys.argv[sys.argv.index("--rapport") + 1]).write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    if "--rythme" in sys.argv:
        un_rythme(sys.argv[sys.argv.index("--rythme") + 1])
    else:
        principal()
