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
   Puis les mondes (phase 5), le Port : le phare du jeu s'allume sur 127.0.0.1, l'enfant tape les vraies
   commandes (curl, ss, ip, tracepath, ssh-keygen, http.server --bind 127.0.0.1…) et celles du jeu (`port …`, l'alias
   de tg installer) ; une affirmation dont l'outil manque (« outil ») est sautée et comptée. La Salle des Rouages :
   ce qui dépend de la machine (cœurs, noyau) est comparé à ce que le jeu calcule sur la même machine (« egal_jeu »).
   La Tour des Ondes : les calculs (bc), les capteurs d'exemple anonymisés (grep -o) ; les outils radio absents sont
   sautés (leurs étapes sont cachées), rien n'émet jamais. La Guilde des Bâtisseurs Libres : le git clone échoue (hors
   ligne, aucun clone réseau) et la Guilde pose sa copie du code du jeu ; gcc, file, od, ldd, make ; le petit dépôt
   git de la contribution (aucun remote) ; OpenSCAD s'il est là ; sha256sum et dd sur des FICHIERS du terrain. La Forge :
   les recettes sh, les boucles, python3, la devinette jouée par un robot (seq | sh), le site servi sur 127.0.0.1 et lu
   avec curl, puis éteint (kill %1 : pas de Ctrl+C sans terminal) ; magick, sox, ffmpeg, exiftool sautés s'ils manquent.
   L'Atelier : le robot simulé (echo > robot/led, cat robot/capteur_distance, la vraie boucle for avec le vrai
   cerveau.sh et `atelier pas`) ; ce que lit bash est ce que le jeu a écrit ; Ctrl+C sur la boucle infinie (timeout).
   Le Sommet : les scripts fournis par le jeu (fragile, bivouac, casse, boucle, boussole, porte du CTF) lancés dans bash ;
   ce qui dépend de la partie (journal, éboulis, boussole, fragments) est comparé à ce que le jeu calcule (sommet.egal_rejeu).
   La Bibliothèque du Temps : le vrai git (identité d'EXEMPLE réglée dans chaque album par l'enfant, jamais --global),
   le grimoire du jeu à dates fixes, la formule perdue retrouvée, le conflit, la copie de l'ami (aucun push).
   Le Poste de Contrôle : lecture seule (ps, /proc, free, df, du, os-release, dpkg/rpm, systemctl, /etc/passwd) ; les
   réponses (la caisse la plus lourde, le PATH, les alertes, les paquets, les suspects) comparées à ce que calcule le
   jeu ; la vague : des sleep renommés lancés par le jeu, arrêtés par kill, éteints à la fin.
Utilisé en CI (.github/workflows/rejeu.yml) sur une vraie machine Linux.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

RACINE = Path(__file__).resolve().parents[2]
# --terminal-du-jeu (décision du 2 novembre) : l'histoire est jouée dans le terminal du jeu (vsh/, le petit Linux écrit
# en Python, celui de Windows) au lieu du vrai bash ; le jeu juge alors les outils comme sous Windows (ceux du terminal
# du jeu). Sous Windows, c'est ce que fait la CI (.github/workflows/windows.yml).
VIRTUEL = "--terminal-du-jeu" in sys.argv
if VIRTUEL:
    os.environ["TG_TERMINAL_VIRTUEL"] = "1"
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
    global saute
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
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost,127.0.0.1"     # le Port : la boucle locale, directe
    sys.path.insert(0, str(RACINE / "pc"))
    import builtins
    from tg import app, core, explo, histoire as H
    from tg.coquille import Coquille
    home = Path.home()
    (home / ".bash_history").touch()
    builtins.input = lambda p="": "Pixel"
    app.creer_si_besoin()
    explo.tick = lambda *a, **k: None
    if VIRTUEL:
        from tg.vsh import CoquilleVirtuelle
        shell = CoquilleVirtuelle(home, jeu="auto")
        home_aff = PurePosixPath(shell.vfs.home) if shell.vfs.mode == "windows" else home
        if shell.vfs.mode == "windows":           # (Windows : whoami dit le nom du Linux virtuel)
            os.environ["USER"] = shell.vfs.utilisateur
        avant_home = set(os.listdir(home))
    else:
        shell = Coquille(home, env=dict(os.environ, LC_ALL="C.UTF-8", LANGUAGE="C", LC_MESSAGES="C"))
        home_aff = home
    etat = {"cwd": home, "sortie": "", "code": 0}

    from tg import port as P_
    from tg import citadelle as C_
    jeu_port = f"{sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); from tg import port; port.commande(sys.argv[1:])\""
    jeu_cit = jeu_port.replace("port; port.", "citadelle; citadelle.")
    jeu_cry = jeu_port.replace("port; port.", "crypte; crypte.")
    jeu_mac = jeu_port.replace("port; port.", "machines; machines.")
    jeu_ond = jeu_port.replace("port; port.", "ondes; ondes.")
    jeu_gui = jeu_port.replace("port; port.", "guilde; guilde.")
    jeu_obs = {n: jeu_port.replace("port; port.commande", "observatoire; observatoire." + f) for n, f in
               (("observatoire", "commande"), ("assistant", "commande_assistant"), ("agent", "commande_agent"),
                ("devine-type", "commande_devine_type"), ("devine-mot", "commande_devine_mot"))}
    jeu_obs["explique"] = (f"{sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); from tg import app; "
                           f"sys.argv = ['tg', 'explique'] + sys.argv[1:]; app._main()\"")
    from tg import crypte as K_
    from tg import machines as M_
    from tg import ondes as O_
    from tg import guilde as G_
    from tg import observatoire as OB_
    from tg import donnees as DN_
    jeu_don = jeu_port.replace("port; port.commande(sys.argv[1:])", "donnees; sys.exit(donnees.commande(sys.argv[1:]) or 0)")
    from tg import forge as FO_
    jeu_for = jeu_port.replace("port; port.commande(sys.argv[1:])", "forge; sys.exit(forge.commande(sys.argv[1:]) or 0)")
    from tg import atelier as AT_
    jeu_ate = jeu_port.replace("port; port.commande(sys.argv[1:])", "atelier; sys.exit(atelier.commande(sys.argv[1:]) or 0)")
    from tg import sommet as SO_
    jeu_som = jeu_port.replace("port; port.commande(sys.argv[1:])", "sommet; sys.exit(sommet.commande(sys.argv[1:]) or 0)")
    jeu_tmp = jeu_port.replace("port; port.", "temps; temps.")
    from tg import temps as TP_
    jeu_ctl = jeu_port.replace("port; port.", "controle; controle.")
    from tg import controle as CT_
    jeu_tg = (f"{sys.executable} -c \"import sys; sys.path.insert(0, '{RACINE / 'pc'}'); from tg import app; "
              f"sys.argv = ['tg'] + sys.argv[1:]; app._main()\"")

    def coupe_suivante(st_):
        """La tempête : un nœud du chemin actuel qui laisse encore assez de chemins (l'enfant lit mesh-route)."""
        o = O_.o_(st_)
        cible, coupes = o.get("cible"), list(o.get("coupes", []))
        reste = O_.donnees()["maillage"]["coupes_defi"] - O_._defi_coupes()

        def jouable(cs, n):
            if n <= 0:
                return True
            r = O_.route("camp", cible, cs)
            return any(O_.route("camp", cible, cs + [x]) and jouable(cs + [x], n - 1) for x in (r or [])[1:-1])
        r = O_.route("camp", cible, coupes) or []
        return next((x for x in r[1:-1] if O_.route("camp", cible, coupes + [x]) and jouable(coupes + [x], reste - 1)),
                    (r[1:-1] or ["racine"])[0])

    def tape(cmd):
        if VIRTUEL:                                     # le terminal du jeu lance lui-même les commandes du jeu
            vrai = cmd
            if cmd.startswith("while true"):
                vrai = "timeout -s INT 2 bash -c " + __import__("shlex").quote(cmd)
            etat["sortie"], etat["code"], d = shell.lancer(vrai)
            etat["cwd"] = Path(d)
            with open(home / ".bash_history", "a", encoding="utf-8") as f:
                f.write(cmd + "\n")
            return app.etape(spontane=False, defis=False, cwd=str(etat["cwd"]), statut=etat["code"])
        vrai = re.sub(r"^port\b", jeu_port, cmd)          # l'alias port='tg port' (posé par tg installer)
        vrai = re.sub(r"(^|;\s*)citadelle\b", lambda m: m.group(1) + jeu_cit, vrai)   # et citadelle='tg citadelle'
        vrai = re.sub(r"(^|;\s*)crypte\b", lambda m: m.group(1) + jeu_cry, vrai)       # et crypte='tg crypte'
        vrai = re.sub(r"(^|;\s*)machines\b", lambda m: m.group(1) + jeu_mac, vrai)     # et machines='tg machines'
        vrai = re.sub(r"(^|;\s*)ondes\b", lambda m: m.group(1) + jeu_ond, vrai)         # et ondes='tg ondes'
        vrai = re.sub(r"(^|;\s*)(mesh-(envoie|coupe|route))\b", lambda m: m.group(1) + jeu_ond + " " + m.group(2), vrai)
        vrai = re.sub(r"(^|;\s*)guilde\b", lambda m: m.group(1) + jeu_gui, vrai)       # et guilde='tg guilde'
        vrai = re.sub(r"(^|;\s*|timeout -s INT 1\s+)(observatoire|assistant|agent|devine-type|devine-mot|explique)(?=\s|$)",
                      lambda m: m.group(1) + jeu_obs[m.group(2)], vrai)      # et les alias de l'Observatoire
        vrai = re.sub(r"(^|;\s*)controle(?=\s|$)", lambda m: m.group(1) + jeu_ctl, vrai)  # et controle='tg controle'
        vrai = re.sub(r"(^|;\s*)donnees(?=\s|$)", lambda m: m.group(1) + jeu_don, vrai)   # et donnees='tg donnees'
        vrai = re.sub(r"(^|;\s*)forge(?=\s|$)", lambda m: m.group(1) + jeu_for, vrai)     # et forge='tg forge'
        vrai = re.sub(r"(^|;\s*)atelier(?=\s|$)", lambda m: m.group(1) + jeu_ate, vrai)  # et atelier='tg atelier'
        vrai = re.sub(r"(^|;\s*)sommet(?=\s|$)", lambda m: m.group(1) + jeu_som, vrai)    # et sommet='tg sommet'
        vrai = re.sub(r"(^|;\s*)temps(?=\s|$)", lambda m: m.group(1) + jeu_tmp, vrai)     # et temps='tg temps'
        vrai = re.sub(r"(^|;\s*|&&\s*)tg(?=\s)", lambda m: m.group(1) + jeu_tg, vrai)   # tg collection --csv, tg donnees …
        if cmd.startswith("while true"):                 # l'Atelier : la boucle infinie, arrêtée par Ctrl+C (un vrai SIGINT)
            vrai = "timeout -s INT 2 bash -c " + __import__("shlex").quote(cmd)
        etat["sortie"], etat["code"], d = shell.lancer(vrai)
        etat["cwd"] = Path(d)
        with open(home / ".bash_history", "a") as f:
            f.write(cmd + "\n")
        return app.etape(spontane=False, defis=False, cwd=str(etat["cwd"]), statut=etat["code"])

    attendus = P.get("rejeu", {})
    seul = os.environ.get("TG_REJEU_MONDE")           # (en local : rejouer un seul monde, les autres marqués finis)
    if seul:
        def tout_fini(s_):
            h_ = H.h_(s_)
            for c_ in H.CHAPITRES:
                if c_["id"] != seul and H.chapitre_dispo(c_):
                    h_["faits"] += [x for x in c_["lecons"] if x not in h_["faits"]]
                    if c_["id"] not in h_["ailes"]:
                        h_["ailes"].append(c_["id"])
            h_["chap"] = None
            h_.setdefault("mondes_annonces", []).extend(m_ for m_ in H.MONDES_MODS if m_ != seul)
            s_["xp"] = max(s_.get("xp", 0), 10 * 30 ** 2)
        core.modifier(tout_fini)
        core.TERRAIN.mkdir(parents=True, exist_ok=True)
        attendus = {k: v for k, v in attendus.items() if any(k.startswith(l_ + ".") for l_ in H.PAR_CHAP[seul]["lecons"])}
        st = app.etape(spontane=False, defis=False)
    vus = set()
    sautes = set()
    st = app.etape(spontane=False, defis=False)
    derniere = None
    for _ in range(1200):
        les, _e = H.lecon_courante(st)
        h = H.h_(st)
        if not les:
            reste = [a for a in H.AILES if not H.fini(st, a)]
            if (H.fini(st, "sommet") and H.fini(st, "controle")) or h["chap"] in ("reveil", "nid"):
                break
            if H.fini(st, "coeur"):                 # le tronc et les ailes faits : les mondes du Carrefour, dans l'ordre
                reste = [m_ for m_ in ("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire",
                                       "donnees", "forge", "robots", "temps", "controle", "sommet") if not H.fini(st, m_)][:1]
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
        if les["id"].startswith("dn") and not etat.get("collection_test"):   # la Salle des Données : la collection de TEST
            etat["collection_test"] = True                # (fixe : le rejeu reste déterministe ; plus de bestioles d'exemple)
            st = core.modifier(lambda s_: s_.__setitem__("captures", DN_.collection_test()))
        i = st["step"]
        step = les["steps"][i]
        c = step["cmd"]
        if c.startswith("sleep 300"):
            c = "sleep 30 &"
        if c.startswith("echo ?") and not les["id"].startswith("cit"):
            c = c.replace("?", (etat["sortie"].strip().split() or ["0"])[-1], 1)
        if c == "port guide racine … feu":           # l'enfant trouve le détour sur la carte
            c = "port guide " + " ".join(P_.route("camp", "feu", P_.p_(st)["eteints"] or ["roche"])[1:])
        if c == "port sceau ?":
            c = f"port sceau {P_.vrai_sceau(P_._graine(st))}"
        gr = C_._graine(st)
        if c == "echo ? > intrus.txt":               # la Citadelle : l'enfant lit la réponse sur l'écran
            c = f"echo {C_.intrus()} > intrus.txt"
        if c == "echo ? > altere.txt":
            c = "echo " + C_.donnees()["tresor_altere"].split(".")[0] + " > altere.txt"
        if c == "kill ?" and les["id"].startswith("cit"):
            c = "kill " + " ".join(str(p) for p, _n in C_.fictifs_vivants())
        if c == "citadelle facteur ? ? ?":
            c = "citadelle facteur " + " ".join(map(str, C_.bons_indices(gr)))
        if c == "citadelle drapeau ?":
            b = {"cit13": "enumeration", "cit14": "droits", "cit15": "secrets"}[les["id"]]
            faits = re.findall(rf"^\[drapeau\] {b} (\w+) \(ok\)", C_.carnet(), re.M)
            c = "citadelle drapeau " + C_.drapeau(gr, b, "donjon" if "entree" in faits else "entree")
        if les["id"] == "cit16" and i == 2:           # la grande vague : tout réparer avant le tableau
            c = ('find . -name "*.glitch" -delete; kill ' + " ".join(str(p) for p, _n in C_.fictifs_vivants()) +
                 " 2>/dev/null; chmod 600 " + C_.donnees()["vague"]["secret"] + "; citadelle tableau")
        if c == "crypte roue ?":                     # la Crypte : l'enfant compte les lettres, lit le dé, les copies…
            c = f"crypte roue {K_.decalage(K_._graine(st))}"
        if c == "crypte de ?":
            c = f"crypte de {K_.de_suite(K_._graine(st), K_.donnees()['de']['montres'] + 1)[-1]}"
        if c == "crypte quiz ? ? ? ? ? ?":
            c = "crypte quiz " + " ".join(K_.bonnes_reponses(K_._graine(st)))
        if "copies/?/" in c or c == "crypte consensus ?":
            c = c.replace("?", K_.tricheur(K_._graine(st)))
        gm = M_._graine(st)                          # la Salle des Rouages : l'enfant lit l'écran (nproc, free -h…)
        if c == "machines coeurs ?":
            c = f"machines coeurs {M_.coeurs()}"
        if c == "machines memoire ?":
            c = f"machines memoire {(M_.memoire_kio() or 0) / 1024 ** 2:.1f}"
        if c == "machines monte 1 ? ? ? ? ? ?":
            c = "machines monte 1 P1 C1 M1 S1 G0 A1"
        if c == "machines interrupteurs ?":
            c = "machines interrupteurs Pixel"
        if c == "machines allume ?":
            c = "machines allume " + M_.bits(ord(M_.lettre_defi(st.get("name", ""))))
        if c == "machines reveil ? ? ? ? ?":
            c = "machines reveil " + " ".join(M_.reveil_reponse(gm))
        if c == "machines orchestre ? ? ? ? ?":
            c = "machines orchestre " + " ".join(l for _n, _i, l in M_.orchestre(gm))
        if c == "machines range ? ? ? ?":
            c = "machines range " + " ".join(r for _n, _i, r in M_.range_boites(gm))
        if c == "machines monte ? ? ? ? ? ?":
            c = "machines monte " + {"jouer": "P2 C1 M2 S1 G1 A2", "dessiner": "P2 C1 M2 S2 G0 A1",
                                     "serveur": "P3 C2 M3 S3 G0 A2", "robot": "P4 C3 M3 S1 G0 A1"}[M_.besoin_epreuve(gm)]
        if c == "machines drapeau ?":
            c = "machines drapeau " + M_.drapeau(gm)
        go = O_._graine(st)                          # la Tour des Ondes : l'enfant calcule, lit la règle, la vallée…
        if c == "ondes longueur ?":
            c = "ondes longueur 34.6"
        if c == "ondes traverse ?":
            c = "ondes traverse lora"
        if c == "ondes reseaux ?":
            c = f"ondes reseaux {len(O_.wifi_freqs() or [])}"
        if c == "ondes regle ? ? ? ? ? ?":
            c = "ondes regle " + " ".join(O_.regle_reponse(go))
        if c == "ondes libre ? ? ? ? ? ?":
            c = "ondes libre " + " ".join(r_ for _n, _i, r_ in O_.libre_cartes(go))
        if c == "ondes vallee ?":
            c = f"ondes vallee {O_.sf_min(O_.vallee_m(go))}"
        if c == "ondes messages ?":
            c = f"ondes messages {O_.messages_heure(O_.sf_min(O_.vallee_m(go)))}"
        if c == "ondes choix ? ? ? ?":
            c = "ondes choix " + " ".join(r_ for _n, _i, r_ in O_.choix_cartes(go))
        if c == "mesh-coupe ?":
            c = f"mesh-coupe {coupe_suivante(st)}"
        if c == 'mesh-envoie ? "SOS"':
            c = f'mesh-envoie {O_.o_(st).get("cible") or O_.defi_cible(go)} "SOS"'
        gg = G_._graine(st)                          # la Guilde : l'enfant lit les situations, le plan, le lsblk fictif…
        if c == "guilde libertes ? ? ? ?":
            c = "guilde libertes " + " ".join(r_ for _n, _i, r_ in G_.libertes_cartes(gg))
        if c == "guilde gratuit ? ? ? ?":
            c = "guilde gratuit " + " ".join(r_ for _n, _i, r_ in G_.gratuit_cartes(gg))
        if c == "guilde licence ?":
            c = "guilde licence " + next(x for x in ("bash", "coreutils", "grep", "sed", "git", "gcc", "make", "python3", "firefox")
                                         if x not in G_.licences_trouvees())
        if c == "guilde faim ?":
            c = "guilde faim " + (G_.faim_fichiers(G_.fichiers_du_code()) or ["satiete.py"])[0]
        if c == "sed -i 's/?/?/' langues/fr.txt":
            c = f"sed -i 's/{G_.faute(gg)['faux']}/{G_.faute(gg)['juste']}/' langues/fr.txt"
        if c == "guilde trou ? ?":
            c = f"guilde trou {G_.piece(gg)['trou_x']} {G_.piece(gg)['trou_y']}"
        if c == "guilde volume ?":
            c = f"guilde volume {G_.volume(gg)}"
        if c == "guilde disque ?":
            c = f"guilde disque {G_.cle_disque(gg)[0]}"
        if c == "less code_du_jeu/pc/tg/satiete.py":
            c = "less -FX code_du_jeu/pc/tg/satiete.py | head -3"     # (pas de terminal ici : less écrit tout)
        go_ = OB_._graine(st)                        # l'Observatoire : l'enfant lit le journal, les réponses, le diff…
        if c == 'echo "?" > mission.txt':
            c = f'echo "{OB_.t("ob.mission.exemple")}" > mission.txt'
        if c == "observatoire oubli ?":
            c = "observatoire oubli " + OB_.trier_assistant(OB_.texte_types().splitlines(), go_)[1].split()[0]
        if c == "agent refuse ?":
            c = f"agent refuse {OB_.dangereuse(go_, 'equipe' if les['id'] == 'ob9' else 'agent')}"
        if c == "agent boucle":
            c = "timeout -s INT 1 agent boucle"          # Ctrl+C au bout d'une seconde (un vrai SIGINT)
        if c == "observatoire piege ?":
            c = "observatoire piege famille"
        if c == "observatoire biais ?":
            c = "observatoire biais " + next(str(n) for n, _i, r_ in OB_.biais_cartes(go_) if r_ == "o")
        if c in ("devine-mot suite ?", "devine-mot phrase ?"):
            c = c.replace("?", OB_.effectifs(OB_._table_mots())[0][0])
        if c == "observatoire perroquet ? ? ?":
            c = "observatoire perroquet " + " ".join(r_ for _n, _i, r_ in OB_.perroquet_cartes(go_))
        if c == "assistant fausses ? ?":
            c = "assistant fausses " + " ".join(str(n) for n, _i, f_ in OB_.questions(go_) if f_)
        if c == "observatoire confier ? ? ? ? ? ?":
            c = "observatoire confier " + " ".join(r_ for _n, _i, r_ in OB_.confier_cartes(go_))
        if c == "observatoire nuances ? ? ? ? ?":
            c = "observatoire nuances " + " ".join(r_ for _n, _i, r_ in OB_.nuances_cartes(go_))
        if c == "observatoire decoupe ? ? ?":
            c = "observatoire decoupe " + " ".join(OB_.decoupe_reponse(go_))
        if c == "observatoire consigne ?":
            c = "observatoire consigne " + next(n for n, _i, r_ in OB_.consigne_cartes(go_) if r_ == "true")
        if c.startswith("donnees ") and c.endswith(" ?") or "s/?/?/" in c:   # la Salle des Données : calculé sur le fichier
            r_ = DN_.lignes_du_fichier() or []
            rep_ = {"combien": len(r_), "shiny": DN_.nb_shiny(r_), "moyenne": DN_.nombre_awk(DN_.moyenne(r_)),
                    "mediane": DN_.nombre_awk((DN_.medianes(r_) or [0])[0]), "etendue": DN_.etendue(r_),
                    "sql": (DN_.types_majoritaires(r_) or ["?"])[0]}
            if c.startswith("donnees "):
                c = c[:-1] + str(rep_.get(c.split()[1], "?"))
            else:
                _f, _j, mal_, bon_ = DN_.carnet_soigneur(r_)
                c = c.replace("s/?/?/", f"s/{mal_}/{bon_}/")
        if c == "forge code ?":                     # la Forge : l'enfant lit l'écran (echo $?), compte les tours…
            c = "forge code " + ((etat["sortie"].strip().split() or ["2"])[-1])
        if c == "forge tours ?":
            c = "forge tours " + str(FO_.tours_reponse(*FO_.tours_question(FO_._graine(st))))
        if c == "forge erreur ?":
            c = "forge erreur IndexError"
        if c == "forge appareil ?":
            c = "forge appareil " + FO_.donnees()["photo"]["marque"]
        if c == "sh question.sh":                   # (pas de clavier ici : la réponse arrive par un tuyau)
            c = "echo Léa | sh question.sh"
        if c == "sh mon_jeu/devinette.sh":          # (le robot joue à la place de l'enfant)
            c = "seq 1 10 | sh mon_jeu/devinette.sh"
        if c == "fg" and les["id"] == "fo6":         # fg puis Ctrl+C : ici, sans terminal, kill %1
            c = "kill %1"
        ga = AT_._graine(st)                         # l'Atelier : l'enfant lit la grille, le capteur, la table, le réflexe
        if c == "atelier ou ?":
            c = "atelier ou {x} {y}".format(**AT_.a_(st)["robot"])
        if c == "atelier cases ?":
            c = f"atelier cases {AT_.capteur_de(st) // 10}"
        if c == "atelier verite ? ? ? ?":
            c = "atelier verite " + " ".join(AT_.table_verite(AT_.porte(ga)))
        if c == "atelier choix ? ? ?":
            c = "atelier choix " + " ".join(r_ for _n, _i, r_ in AT_.choix_cartes(ga))
        if c == "atelier reflexe ?":
            c = f"atelier reflexe {AT_.reflexe(ga)[2]}"
        if c == "nano cerveau.sh":                   # l'enfant écrit son cerveau dans l'éditeur
            c = "printf '%s' " + __import__("shlex").quote(AT_.cerveau_malin()) + " > cerveau.sh"
        if les["id"].startswith("som") and les["id"][3:].isdigit():   # le Sommet : l'enfant lit l'écran (mission, fragments…)
            c = SO_.reponse_rejeu(st, c)
        if les["id"].startswith("tp") and "?" in c:      # la Bibliothèque du Temps : l'empreinte lue dans git log -S secret
            c = c.replace("?", TP_.hash_perte()[:7], 1)
        gc_ = CT_._graine(st)                        # le Poste de Contrôle : l'enfant lit du, le PATH, le carnet, l'écran…
        if les["id"].startswith("ct"):
            c = {"controle entrepot ?": f"controle entrepot {CT_.caisse_lourde(gc_)}",
                 "controle path ?": f"controle path {len(CT_.path_actuel().split(':'))}",
                 "controle alertes ?": f"controle alertes {CT_.nb_alertes(gc_)}",
                 'controle cron "? ? ? ? ?"': f'controle cron "{CT_.cron_situation(gc_)["rep"]}"',
                 "controle distribution ?": f"controle distribution {CT_.os_release().get('ID', 'linux')}",
                 "controle familles ? ? ? ? ?": "controle familles " + " ".join(r_ for _n, _i, r_ in CT_.familles_cartes(gc_)),
                 "controle useradd ?": "controle useradd mousse",
                 "kill ?": "kill " + " ".join(str(p) for p, _n in CT_.suspects_vivants()),
                 "top": "top -bn1 | head -5",                  # (pas de terminal ici : top écrit une fois)
                 "tail -f carnet_de_bord.log": "timeout 1 tail -f carnet_de_bord.log"}.get(c, c)
        if c.endswith(" &") and "http.server" in c:
            c = c[:-2] + " >/dev/null 2>&1 &"       # (les lignes du serveur n'encombrent pas la suite)
        lieu = step.get("ou") if step.get("ou") is not None else None
        from tg import verif
        voulu = verif.lieu_attendu(st, step) if hasattr(verif, "lieu_attendu") else None
        if voulu is not None and not c.startswith("cd ") and (core.TERRAIN / voulu).resolve() != etat["cwd"].resolve() \
                and (core.TERRAIN / voulu).is_dir():
            st = tape(f"cd ~/terrain_terminagotchi/{voulu}".rstrip("/"))
        # la clé « leçon.étape » compte TOUTES les étapes de la leçon : une étape cachée parce que son outil manque
        # (xxd, lspci, qemu-img…) ne décale pas les suivantes
        orig = next((k for k, x in enumerate(H.lecon_def(les["id"])["steps"])
                     if x is step or (x.get("dit"), x.get("bravo")) == (step.get("dit"), step.get("bravo"))), i)
        cle = f"{les['id']}.{orig}"
        if derniere == (cle, c):
            print(f"  · bloqué sur {cle} ({c}) : on s'arrête là")
            break
        derniere = (cle, c)
        if os.environ.get("TG_REJEU_BAVARD"):
            print(f"    {cle} $ {c}")
        st = tape(c)
        if "http.server" in c:                         # la lanterne met un instant à s'allumer
            port_ = int((re.search(r"http\.server\s+(\d+)", c) or re.search(r"(8000)", "8000")).group(1))
            for _ in range(40):
                if P_.phare_allume(port_):
                    break
                __import__("time").sleep(0.2)
            if les["id"] == "fo6":                    # la Forge vérifie la page servie : un tour de plus, lanterne allumée
                st = tape("true")
        if cle in attendus and cle not in vus:
            vus.add(cle)
            a = attendus[cle]
            if VIRTUEL:                                  # une commande que le terminal du jeu n'a pas : racontée
                from tg.vsh.outils import RACONTEES
                from tg.verif import premier as _premier
                absente = next((w for w in (_premier(x) for x in re.split(r"\||&&|;", c)) if w in RACONTEES), None)
                if not absente and "/proc/$$" in c and shell.vfs.mode == "transparent":
                    absente = "/proc/$$ (le shell est ici un programme Python)"
                if absente:
                    print(f"  · {cle} `{c}` raconté ({absente} n'existe pas dans le terminal du jeu)")
                    sautes.add(cle)
                    saute += 1
                    continue
            if a.get("outil") and not _present(a["outil"]):
                print(f"  · {cle} `{c}` sauté ({a['outil']} absent)")
                sautes.add(cle)
                saute += 1
                continue
            sortie, code = etat["sortie"], etat["code"]
            if a.get("apres"):
                sortie, code, _d = shell.lancer(a["apres"])
            nom = f"{cle} `{c}`" + (f" puis `{a['apres']}`" if a.get("apres") else "")
            s = sortie.rstrip("\n")
            lignes = [x for x in s.split("\n") if x]
            pq = f"  [{a.get('pourquoi', '')}]" if a.get("pourquoi") else ""
            if "sortie" in a:
                att = _remplir(a["sortie"], home_aff)
                verifier(s == att, f"{nom} : {s!r} (le jeu dit {att!r}){pq}")
            if "motif" in a:
                verifier(re.search(a["motif"], s, re.M) is not None, f"{nom} : {s[:150]!r} ~ {a['motif']!r}{pq}")
            if "contient" in a:
                manque = [x for x in a["contient"] if x not in s.split()]
                verifier(not manque, f"{nom} : contient {a['contient']} (manque {manque}){pq}")
            if "lignes" in a:
                verifier(len(lignes) == a["lignes"], f"{nom} : {len(lignes)} lignes (le jeu dit {a['lignes']}){pq}")
            if "dossiers" in a:
                Pc_ = PurePosixPath if isinstance(home_aff, PurePosixPath) else Path
                trouves = sorted(str(Pc_(x).parent.relative_to(Pc_(home_aff) / "terrain_terminagotchi")) for x in lignes)
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
            if a.get("egal_jeu") == "coeurs":            # la Salle des Rouages : le jeu calcule sur la même machine
                verifier(s.strip().isdigit() and int(s.strip()) in M_.coeurs_justes(),
                         f"{nom} : bash dit {s.strip()!r}, le jeu accepte {sorted(M_.coeurs_justes())}{pq}")
            if a.get("egal_jeu") == "cpuinfo":
                verifier(s.strip() == str(M_.processeurs_cpuinfo()), f"{nom} : bash compte {s.strip()!r}, le jeu {M_.processeurs_cpuinfo()}{pq}")
            if a.get("egal_jeu") == "noyau":
                verifier(s.strip() == M_.noyau(), f"{nom} : bash dit {s.strip()!r}, le jeu lit {M_.noyau()!r}{pq}")
            if a.get("egal_jeu") == "mot_frequent":       # l'Observatoire : bash et le devineur de mots comptent pareil
                e_ = OB_.effectifs(OB_._table_mots())
                l0 = (lignes or [""])[0].split()
                verifier(len(l0) == 2 and int(l0[0]) == e_[0][1] and l0[1] in [w for w, n in e_ if n == e_[0][1]],
                         f"{nom} : bash dit {l0}, le jeu {e_[0]}{pq}")
            if a.get("egal_jeu") == "paire_frequente":
                p_ = OB_.top_paires(OB_._table_mots())
                l0 = (lignes or [""])[0].split()
                verifier(len(l0) == 3 and int(l0[0]) == p_[0][1] and tuple(l0[1:]) in [x for x, n in p_ if n == p_[0][1]],
                         f"{nom} : bash dit {l0}, le jeu {p_[0]}{pq}")
            if (a.get("egal_jeu") or "").split(":")[0] in EGAL_DONNEES:   # la Salle des Données : le jeu calcule pareil
                verifier(EGAL_DONNEES[a["egal_jeu"]](s, DN_.lignes_du_fichier() or [], DN_), f"{nom} : {s[:150]!r}{pq}")
            if a.get("egal_jeu") in EGAL_ATELIER:          # l'Atelier : bash lit ce que le jeu a écrit pour le robot
                verifier(EGAL_ATELIER[a["egal_jeu"]](s, AT_.capteur_de(__import__("tg.core", fromlist=["x"]).load()), AT_),
                         f"{nom} : {s[:150]!r}{pq}")
            if les["id"].startswith("som") and a.get("egal_jeu"):    # le Sommet : ce que le jeu calcule pour cette partie
                verifier(SO_.egal_rejeu(a["egal_jeu"], s, SO_._graine(st)), f"{nom} : {s[:150]!r}{pq}")
            if a.get("egal_jeu") == "entrepot":            # le Poste de Contrôle : le jeu calcule pareil
                gros_ = os.path.basename(max((x.split("\t") for x in lignes if "\t" in x), key=lambda x: _taille_du(x[0]),
                                             default=["", ""])[1])
                verifier(gros_ == CT_.caisse_lourde(CT_._graine(st)) + ".bin", f"{nom} : du dit {gros_!r}{pq}")
            if a.get("egal_jeu") == "path":
                verifier(CT_.path_ok(str(len(lignes)), CT_.path_actuel()), f"{nom} : {len(lignes)} dossiers{pq}")
            if a.get("egal_jeu") == "alertes":
                verifier(s.strip() == str(CT_.nb_alertes(CT_._graine(st))), f"{nom} : bash compte {s.strip()!r}, le jeu {CT_.nb_alertes(CT_._graine(st))}{pq}")
            if a.get("egal_jeu") == "paquets":
                m_, n_ = CT_.magasin()
                verifier(m_ is not None and s.strip() == str(n_), f"{nom} : bash compte {s.strip()!r}, le jeu {n_}{pq}")
            if a.get("egal_jeu") == "suspects":
                vus_ = {n_ for _p, n_ in CT_.vivants()}
                verifier(bool(vus_) and all(n_ in s for n_ in vus_), f"{nom} : {sorted(vus_)} dans ps{pq}")
            if a.get("egal_jeu") == "traces_abyssor":
                n = (s.split() or ["?"])[-1]
                verifier(n == str(H.traces_abyssor()), f"{nom} : bash compte {n}, le jeu attend {H.traces_abyssor()}{pq}")
    h = H.h_(st)
    verifier(H.fini(st, "coeur"), f"l'histoire est allée jusqu'au bout ({h['ailes']})")
    verifier(H.fini(st, "port"), "le Port, premier monde du Carrefour, est allé jusqu'au bout (P0 → P11)")
    verifier(H.fini(st, "citadelle"), "la Citadelle, deuxième monde, est allée jusqu'au bout (cit0 → cit16)")
    verifier(H.fini(st, "crypte"), "la Crypte des Codes, troisième monde, est allée jusqu'au bout (cr0 → cr14)")
    verifier(H.fini(st, "machinerie"), "la Salle des Rouages, quatrième monde, est allée jusqu'au bout (sm0 → sm10)")
    verifier(H.fini(st, "ondes"), "la Tour des Ondes, cinquième monde, est allée jusqu'au bout (on0 → on10)")
    verifier(H.fini(st, "guilde"), "la Guilde des Bâtisseurs Libres, sixième monde, est allée jusqu'au bout (gu0 → gu6)")
    verifier(H.fini(st, "observatoire"), "l'Observatoire de l'IA, septième monde, est allé jusqu'au bout (ob0 → ob9)")
    verifier(H.fini(st, "donnees"), "la Salle des Données, huitième monde, est allée jusqu'au bout (dn0 → dn6)")
    verifier(H.fini(st, "forge"), "la Forge, neuvième monde, est allée jusqu'au bout (fo0 → fo7)")
    verifier(H.fini(st, "robots"), "l'Atelier, dixième monde, est allé jusqu'au bout (at0 → at7)")
    verifier(H.fini(st, "temps") or not shutil.which("git"), "la Bibliothèque du Temps, onzième monde, est allée jusqu'au bout (tp0 → tp5)")
    verifier(H.fini(st, "controle"), "le Poste de Contrôle, douzième monde, est allé jusqu'au bout (ct0 → ct7)")
    verifier(H.fini(st, "sommet"), "le Sommet (Expert++), ouvert par 3 mondes au palier 3, est gravi jusqu'au bout (som0 → som7)")
    CT_.arreter_tout()
    P_.eteindre_phare()
    C_.arreter_fictifs()
    K_.tuer_agents()
    # (une étape cachée parce que son outil manque — sox, exiftool… — n'a pas pu être rejouée : sautée et comptée)
    absents = {k for k in set(attendus) - vus if attendus[k].get("outil") and not _present(attendus[k]["outil"])}
    for k in sorted(absents):
        print(f"  · {k} sauté ({attendus[k]['outil']} absent, étape cachée)")
    saute += len(absents)
    if VIRTUEL:                        # le terminal du jeu : les étapes cachées parce que l'outil lui manque (racontées)
        from tg.vsh.outils import RACONTEES
        from tg.verif import premier as _premier

        def cachee(k):
            lid, _p, i = k.rpartition(".")
            try:
                stp = H.lecon_def(lid)["steps"][int(i)]
            except (KeyError, IndexError, ValueError):
                return False
            return bool(stp.get("outil") and not H._outil(stp["outil"])) or _premier(stp.get("cmd", "")) in RACONTEES
        caches = {k for k in set(attendus) - vus - absents if cachee(k)}
        for k in sorted(caches):
            print(f"  · {k} raconté (outil absent du terminal du jeu, étape cachée)")
        saute += len(caches)
        absents |= caches
    if VIRTUEL:                        # rien d'écrit dans le dossier personnel hors du terrain et du dossier du jeu
        apres_home = set(os.listdir(home)) - avant_home - {"terrain_terminagotchi", ".terminagotchi", ".bash_history",
                                                            ".gitconfig"}
        verifier(not apres_home, f"le terminal du jeu n'a rien écrit hors du terrain {sorted(apres_home)}")
    manquent = sorted(set(attendus) - vus - absents)
    verifier(not manquent, f"toutes les étapes décrites ont été rejouées {manquent}")
    shell.fermer()


def _present(outil):
    """L'outil d'une affirmation est là : une commande (shutil.which) ou un fichier du système (/proc/self, /etc/passwd)."""
    return os.path.exists(outil) if outil.startswith("/") else shutil.which(outil) is not None


def _taille_du(x):
    """« 512K », « 8.0K », « 1.2M » (du -h) → un nombre d'octets, pour trouver le plus lourd."""
    m = re.match(r"([\d.,]+)([KMGT]?)", x.strip())
    if not m:
        return 0
    return float(m.group(1).replace(",", ".")) * 1024 ** ("KMGT".find(m.group(2)) + 1 if m.group(2) else 0)


def _egal_lignes(s, r, D):
    return re.fullmatch(r"\s*(\d+)\s+collection\.csv", s.strip()) is not None and int(s.split()[0]) == len(r) + 1


def _egal_uniq(s, attendu):
    """uniq -c : chaque ligne « n valeur » est l'effectif que le jeu calcule (l'ordre des ex aequo peut changer)."""
    vu = {}
    for l in s.strip().splitlines():
        m = l.split(None, 1)
        if len(m) != 2 or not m[0].isdigit():
            return False
        vu[m[1].strip()] = int(m[0])
    return bool(vu) and all(attendu.get(k) == n for k, n in vu.items())


def _egal_tops(s, r, D):
    l = [x.split(",") for x in s.strip().splitlines()]
    return [int(x[3]) for x in l if len(x) > 3] == D.top3(r)


EGAL_DONNEES = {
    "lignes": _egal_lignes,
    "espece_frequente": lambda s, r, D: _egal_uniq(s, dict(D.effectifs([x["nom"] for x in r])))
    and int(s.split()[0]) == D.effectifs([x["nom"] for x in r])[0][1],
    "top3": lambda s, r, D: True,               # sort -nr | head -3 > top3.txt n'affiche rien : le fichier est vérifié par le jeu
    "types": lambda s, r, D: _egal_uniq(s, dict(D.effectifs([x["type"] for x in r]))),
    "shiny": lambda s, r, D: s.strip() == str(D.nb_shiny(r)),
    "une_faute_reste": lambda s, r, D: s.count(D.carnet_soigneur(r)[2]) == 1,
    "somme": lambda s, r, D: s.strip() == str(D.somme(r)),
    "moyenne_awk": lambda s, r, D: s.strip() == D.nombre_awk(D.moyenne(r)),
    "min_max": lambda s, r, D: s.split() == [str(min(D.attaques(r))), str(max(D.attaques(r)))],
    "especes_xargs": lambda s, r, D: sorted(s.split()) == sorted({x["nom"] for x in r}),
    "rapport_top": _egal_tops,
    "schema": lambda s, r, D: s.strip() == D.donnees()["schema"]["creatures"] + ";",
    "sql_top3": lambda s, r, D: [int(x.split("|")[1]) for x in s.strip().splitlines()] == D.top3(r),
    "sql_group": lambda s, r, D: [tuple(x.split("|")) for x in s.strip().splitlines()]
    == [(ty, str(n)) for ty, n in D.effectifs([x["type"] for x in r])],
    "sql_join": lambda s, r, D: len(s.strip().splitlines()) == min(5, len(r)) and all(
        D.ascii_id(__import__("tg.bestiaire", fromlist=["x"]).espece(x.split("|")[0])["habitat"]) == x.split("|")[1]
        for x in s.strip().splitlines()),
    "sql_moyenne": lambda s, r, D: s.strip() == D.valeur_sql(D.moyenne(r)),
}


EGAL_ATELIER = {
    "capteur": lambda s, cm, A: s.strip() == str(cm),
    "capteur3": lambda s, cm, A: s.split() == [str(cm)] * 3,
    "obstacle_libre": lambda s, cm, A: s.strip() == ("obstacle" if cm < 10 else "libre"),
    "journal": lambda s, cm, A: s.strip().splitlines() == (A.dossier_robot() / "journal.txt").read_text(encoding="utf-8").strip().splitlines()[-5:],
}


def main():
    tout = not ({"--fiches", "--histoire"} & set(sys.argv))
    if VIRTUEL:                       # (les fiches : pc/outils/test_terminal.py les compare au vrai bash)
        tout = False
        sys.argv.append("--histoire")
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
