"""Rejeu des sorties réelles (charte de rigueur, docs/programme.md § 7.1, règle 2) : ce que le jeu montre ou affirme
doit être ce qu'affiche un vrai bash.

    python3 pc/outils/rejeu_bash.py [--fiches] [--histoire]      (les deux par défaut ; code de sortie 1 en cas d'écart)

1. Les fiches : chaque cas « vrai_terminal » de donnees/programme.json est lancé dans un bash neuf (bash --norc,
   LC_ALL=C : les messages en anglais, comme dans les fiches), dans un terrain jetable (un dossier temporaire, HOME
   temporaire) : « prepare » puis « cmd » ; la sortie doit être « sortie » (exacte) ou contenir « motif » (expression
   régulière, ligne par ligne), et le code de sortie 0 (ou non nul si « code » vaut "non0"). Les cas « rejeu » =
   reseau / telephone / jeu ne se rejouent pas ici (pas de réseau en CI, pas de téléphone, commandes du jeu) ; un cas
   dont l'« outil » n'est pas installé est sauté (et compté).
2. L'histoire (tronc commun et ailes du PC) : un enfant virtuel tape exactement les commandes montrées (comme
   sim_suiveur.py), dans un vrai bash qui reste ouvert, HOME temporaire, hors ligne ; pour chaque étape décrite dans
   « rejeu » (« leçon.étape »), la vraie sortie est comparée à ce que le jeu en dit (texte cité dans « pourquoi »).
Utilisé en CI (.github/workflows/rejeu.yml) sur une vraie machine Linux.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
P = __import__("json").loads((RACINE / "donnees" / "programme.json").read_text(encoding="utf-8"))
ok = ko = saute = 0
ecarts = []


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    print(("  ✔ " if c else "  ✖ ") + m)
    if not c:
        ecarts.append(m)


def _remplir(x, home):
    return x.replace("{HOME}", str(home)).replace("{USER}", os.environ.get("USER") or _moi())


def _moi():
    return subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()


def comparer(cas, sortie, code, home, nom):
    """Vrai si la sortie et le code correspondent au cas ; le message dit ce qui diffère."""
    s = sortie.rstrip("\n")
    attendu_code = cas.get("code", 0)
    if attendu_code == "non0":
        bon_code = code != 0
    else:
        bon_code = code == attendu_code
    if "sortie" in cas:
        bon = s == _remplir(cas["sortie"], home)
        quoi = f"sortie {s!r} (attendu {_remplir(cas['sortie'], home)!r})"
    elif "motif" in cas:
        bon = re.search(cas["motif"], s, re.M) is not None
        quoi = f"sortie {s[:120]!r} (motif {cas['motif']!r})"
    else:
        bon, quoi = True, ""
    verifier(bon and bon_code, f"{nom} : `{cas['cmd']}` → {quoi}, code {code}")


def fiches():
    global saute
    print("1. Les fiches notions (vrai_terminal), dans un bash neuf, sur un terrain jetable")
    for nid, n in P["notions"].items():
        for cas in n["vrai_terminal"]:
            if cas.get("rejeu"):
                saute += 1
                continue
            outil = cas.get("outil")
            if outil and not (os.path.exists(outil) if outil.startswith("/") else shutil.which(outil)):
                print(f"  · {nid} : `{cas['cmd']}` sauté ({outil} absent)")
                saute += 1
                continue
            home = Path(tempfile.mkdtemp(prefix="tg_rejeu_"))
            terrain = home / "terrain"
            terrain.mkdir()
            env = {"HOME": str(home), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C",
                   "USER": os.environ.get("USER") or _moi(), "TERM": "dumb",
                   "GIT_CONFIG_NOSYSTEM": "1"}
            if cas.get("si"):
                if subprocess.run(["bash", "--norc", "-c", cas["si"]], cwd=terrain, env=env, capture_output=True,
                                  timeout=20).returncode != 0:
                    print(f"  · {nid} : `{cas['cmd']}` sauté (`{cas['si']}` impossible ici)")
                    saute += 1
                    continue
            if cas.get("prepare"):
                subprocess.run(["bash", "--norc", "-c", cas["prepare"]], cwd=terrain, env=env, capture_output=True,
                               timeout=20)
            r = subprocess.run(["bash", "--norc", "-c", cas["cmd"]], cwd=terrain, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=40)
            s = r.stdout.decode("utf-8", "replace")
            # les messages d'erreur de bash -c commencent par « bash: line 1: » : on garde le message lui-même
            comparer(cas, s, r.returncode, home, nid)
            shutil.rmtree(home, ignore_errors=True)


def histoire():
    """Le parcours de l'histoire PC en vrai bash ; les affirmations de « rejeu » vérifiées sur les vraies sorties."""
    print("2. L'histoire du PC jouée dans un vrai bash (HOME temporaire, hors ligne)")
    os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_rejeu_histoire_")
    os.environ["LANG"] = "fr_FR.UTF-8"
    os.environ.pop("HISTFILE", None)
    for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
        os.environ.pop(k, None)
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    Path(os.environ["HOME"], ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n[init]\n\tdefaultBranch = main\n")
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        os.environ[k] = "http://127.0.0.1:9"
    sys.path.insert(0, str(RACINE / "pc"))
    import builtins
    from tg import app, core, explo, histoire as H
    from tg.coquille import Coquille
    home = Path.home()
    (home / ".bash_history").touch()
    builtins.input = lambda p="": "Pixel"
    app.creer_si_besoin()
    explo.tick = lambda *a, **k: None
    shell = Coquille(home, env=dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C", LC_MESSAGES="C"))
    etat = {"cwd": home, "sortie": "", "code": 0}

    def tape(cmd):
        etat["sortie"], etat["code"], d = shell.lancer(cmd)
        etat["cwd"] = Path(d)
        with open(home / ".bash_history", "a") as f:
            f.write(cmd + "\n")
        return app.etape(spontane=False, defis=False, cwd=str(etat["cwd"]), statut=etat["code"])

    attendus = P.get("rejeu", {})
    vus = set()
    st = app.etape(spontane=False, defis=False)
    derniere = None
    for _ in range(900):
        les, _e = H.lecon_courante(st)
        h = H.h_(st)
        if not les:
            reste = [a for a in H.AILES if not H.fini(st, a)]
            if H.fini(st, "coeur") or h["chap"] in ("reveil", "nid"):
                break
            cible = "coeur" if not reste and H.ouvert(st, "coeur") else (reste[0] if reste else None)
            if not cible:
                break
            st = tape(f"cd ~/terrain_terminagotchi/{H.PAR_CHAP[cible]['piece']}")
            if H.lecon_courante(st)[0] is None:
                break
            continue
        if core.level(st["xp"]) < les["niveau"]:
            st = tape(core.faim_d_apprendre(st, les["niveau"])[0][0])
            continue
        i = st["step"]
        step = les["steps"][i]
        c = step["cmd"]
        if c.startswith("sleep 300"):
            c = "sleep 30 &"
        if c.startswith("echo ?"):
            c = c.replace("?", (etat["sortie"].strip().split() or ["0"])[-1], 1)
        lieu = step.get("ou") if step.get("ou") is not None else None
        from tg import verif
        voulu = verif.lieu_attendu(st, step) if hasattr(verif, "lieu_attendu") else None
        if voulu is not None and not c.startswith("cd ") and (core.TERRAIN / voulu).resolve() != etat["cwd"].resolve() \
                and (core.TERRAIN / voulu).is_dir():
            st = tape(f"cd ~/terrain_terminagotchi/{voulu}".rstrip("/"))
        cle = f"{les['id']}.{i}"
        if derniere == (cle, c):
            print(f"  · bloqué sur {cle} ({c}) : on s'arrête là")
            break
        derniere = (cle, c)
        st = tape(c)
        if cle in attendus and cle not in vus:
            vus.add(cle)
            a = attendus[cle]
            sortie, code = etat["sortie"], etat["code"]
            if a.get("apres"):
                sortie, code, _d = shell.lancer(a["apres"])
            nom = f"{cle} `{c}`" + (f" puis `{a['apres']}`" if a.get("apres") else "")
            s = sortie.rstrip("\n")
            lignes = [x for x in s.split("\n") if x]
            pq = f"  [{a.get('pourquoi', '')}]" if a.get("pourquoi") else ""
            if "sortie" in a:
                att = _remplir(a["sortie"], home)
                verifier(s == att, f"{nom} : {s!r} (le jeu dit {att!r}){pq}")
            if "motif" in a:
                verifier(re.search(a["motif"], s, re.M) is not None, f"{nom} : {s[:150]!r} ~ {a['motif']!r}{pq}")
            if "contient" in a:
                manque = [x for x in a["contient"] if x not in s.split()]
                verifier(not manque, f"{nom} : contient {a['contient']} (manque {manque}){pq}")
            if "lignes" in a:
                verifier(len(lignes) == a["lignes"], f"{nom} : {len(lignes)} lignes (le jeu dit {a['lignes']}){pq}")
            if "dossiers" in a:
                trouves = sorted(str(Path(x).parent.relative_to(core.TERRAIN)) for x in lignes)
                verifier(trouves == sorted(a["dossiers"]), f"{nom} : dans {trouves}{pq}")
            if "code" in a:
                verifier(code != 0 if a["code"] == "non0" else code == a["code"], f"{nom} : code {code}{pq}")
            if "plus_gros" in a:
                def taille(x):
                    m = re.match(r"([\d.,]+)([KMGT]?)", x.split()[0]) if x.split() else None
                    if not m:
                        return 0
                    return float(m.group(1).replace(",", ".")) * 1024 ** "KMGT".find(m.group(2)) if m.group(2) \
                        else float(m.group(1).replace(",", "."))
                gros = max(lignes, key=taille).split()[-1] if lignes else None
                verifier(gros == a["plus_gros"], f"{nom} : le plus lourd est {gros!r}{pq}")
            if a.get("egal_jeu") == "traces_abyssor":
                n = (s.split() or ["?"])[-1]
                verifier(n == str(H.traces_abyssor()), f"{nom} : bash compte {n}, le jeu attend {H.traces_abyssor()}{pq}")
    h = H.h_(st)
    verifier(H.fini(st, "coeur"), f"l'histoire est allée jusqu'au bout ({h['ailes']})")
    manquent = sorted(set(attendus) - vus)
    verifier(not manquent, f"toutes les étapes décrites ont été rejouées {manquent}")
    shell.fermer()


def main():
    tout = not ({"--fiches", "--histoire"} & set(sys.argv))
    if tout or "--fiches" in sys.argv:
        fiches()
    if tout or "--histoire" in sys.argv:
        histoire()
    print(f"\n{ok} identiques, {ko} écarts, {saute} cas sautés (réseau, téléphone, commandes du jeu, outil absent)")
    for e in ecarts:
        print("   ÉCART", e)
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
