"""⚙ La Salle des Machines — le matériel et l'infrastructure (docs/programme.md § 7.3 et § 7.13 M5 bis).

Le quatrième monde de la phase 5 (§ 7.14, étape 5). Il s'ouvre selon l'arbre du Carrefour : ses prérequis sont les
niveaux 0 à 3 du tronc commun (programme.json, « mondes » → machines → requis : lire et chercher). Le chapitre
s'appelle « machinerie » (le chapitre « machines » est déjà l'aile du volcan) ; son lieu est
~/terrain_terminagotchi/machines/. On en sort et on y revient, l'étape est gardée.

RÈGLES (affichées à l'entrée, plan_de_la_salle.txt) : LECTURE SEULE sur la vraie machine. Jamais de sudo ; rien n'est
écrit hors du terrain ; aucune donnée personnelle (ni numéro de série, ni adresse MAC, ni nom d'utilisateur, ni nom de
la machine) n'est enregistrée par le jeu ni envoyée. Les réponses attendues (cœurs, mémoire, noyau…) sont CALCULÉES
PAR LE JEU sur la même machine au moment de la vérification : toujours justes. Une commande absente ou refusée
(lspci, dmesg, systemd-analyze, /proc incomplet d'un conteneur) ne bloque jamais : l'étape est cachée si l'outil
manque, ou acceptée quelle que soit la réponse quand un refus est normal (le texte explique les deux cas).

M5 bis « Ta propre machine virtuelle » se fait AVEC UN ADULTE : rien ne s'installe tout seul ; le conteneur est
jetable (--rm), son image minuscule (alpine) est rangée dans le terrain (conteneur_jetable.sh, lu avant d'être lancé,
qui dit ce qu'il va télécharger) ; aucune machine virtuelle n'est créée automatiquement (pas de virt-install) ; virsh
seulement en lecture (-r). Sans podman / qemu-img / virsh, l'étape se raconte (`machines conteneur`, `machines vm`).

« Monte ta machine » (M1 niveau 1 et l'épreuve M7) : des pièces GÉNÉRIQUES (aucune marque), un budget en points
FICTIFS (rien ne s'achète), la compatibilité (prise du processeur, type de mémoire), la consommation et le besoin.

LES PALIERS (sm0 à sm10) : la porte ; M1 les organes (cœurs, mémoire, stockage) puis la ville qui relie tout
(carte mère, bus, Monte ta machine niveau 1) ; M2 des 0 et des 1 (hexadécimal, interrupteurs, Ko / Kio) ; M3 le réveil
(étage par étage) ; M4 le chef d'orchestre (système d'exploitation, licences) ; M5 la maison dans la maison ; M5 bis
le conteneur jetable et le disque virtuel ; M6 les fermes de serveurs (énergie) et la sauvegarde 3-2-1 (une panne
simulée DANS LE TERRAIN) ; M7 l'épreuve « Monte ta machine » (drapeau TG{…}).

LES COMMANDES DU JEU (`machines …`, alias posé par `tg installer`) dessinent l'ordinateur ouvert dont les pièces
s'allument quand une commande les interroge, les interrupteurs, le réveil étage par étage, l'orchestre, la ferme,
l'atelier ; elles écrivent dans le carnet de la salle (machines/carnet_de_la_salle.txt) ce que les étapes vérifient
— jamais une valeur de la machine. Mêmes règles sur Android (Machines.kt, vecteurs communs donnees/machines/vecteurs.json),
où beaucoup est raconté (pas de lspci, de conteneur ni de machine virtuelle sur un téléphone).
"""
import json
import os
import pkgutil
import platform
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata

from . import core
from .langue import t
from .plateforme import BOLD, DIM, IS_WIN, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "machines.json").decode("utf-8"))
    return _D


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
SEPARATEURS = re.compile(r"\|\||&&|[|;&]")


def pieces_de(ligne):
    """Les pièces de l'ordinateur qu'une ligne interroge (dans l'ordre de donnees()["pieces"]) : nproc → processeur,
    free → mémoire, lsblk → stockage, lspci → carte mère… Chaque morceau de la ligne (| ; && ||) compte."""
    al = donnees()["allume"]
    morceaux = [m.strip() for m in SEPARATEURS.split(ligne or "") if m.strip()]
    out = []
    for p in donnees()["pieces"]:
        for m in morceaux:
            if any(re.search(x, m, re.I) for x in al.get(p, [])):
                out.append(p)
                break
    return out


def bits(octet):
    """Un octet en 8 interrupteurs : 65 → « 01000001 »."""
    return format(octet & 255, "08b")


def interrupteurs(mot):
    """[(caractère, [8 bits par octet UTF-8])] : « é » prend DEUX octets (UTF-8), « A » un seul (comme ASCII)."""
    return [(c, [bits(b) for b in c.encode("utf-8")]) for c in mot]


def ascii_bas(texte):
    s = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def lettre_defi(nom):
    """La lettre du défi des interrupteurs : la première lettre A-Z du nom de la créature (sans accent), sinon A."""
    for c in ascii_bas(nom).upper():
        if "A" <= c <= "Z":
            return c
    return "A"


def unites(n):
    """Un nombre d'octets dans les deux familles d'unités : Ko / Mo / Go (1000) et Kio / Mio / Gio (1024)."""
    return {"octets": n, "ko": n / 1000, "kio": n / 1024, "mo": n / 1000 ** 2, "mio": n / 1024 ** 2,
            "go": n / 1000 ** 3, "gio": n / 1024 ** 3}


def nombre(texte):
    """« 7,8 Gi » → (7.8, « gi ») ; None si ce n'est pas un nombre."""
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*([A-Za-z]*)", texte or "")
    if not m:
        return None
    return float(m.group(1).replace(",", ".")), m.group(2).lower()


def memoire_ok(reponse, kio):
    """La réponse de l'enfant (lue dans free -h) est-elle la mémoire de la machine (MemTotal, en Kio) ? Gio ou Go,
    Mio ou Mo (selon l'unité tapée), à 10 % près (free -h arrondit : 7.8Gi, 15Gi, 512Mi)."""
    x = nombre(reponse)
    if not x or not kio:
        return False
    v, u = x
    octets = kio * 1024
    grands = [octets / 1024 ** 3, octets / 1000 ** 3]
    petits = [octets / 1024 ** 2, octets / 1000 ** 2]
    if u.startswith("k") or (not u and v > 50000):        # MemTotal de /proc/meminfo, en kB (des Kio)
        return abs(v - kio) <= 0.1 * kio
    if u.startswith("m"):
        cand = petits
    elif u.startswith(("g", "t")):
        cand = grands if u.startswith("g") else [c / 1024 for c in grands]
    else:
        cand = grands + (petits if octets < 4 * 1024 ** 3 else [])
    return any(abs(v - c) <= max(0.6 if c < 100 else 64, 0.1 * c) for c in cand)


def melange(graine, sel, liste):
    l2 = list(liste)
    random.Random(f"{sel}:{graine}").shuffle(l2)
    return l2


LETTRES = "ABCDE"


def reveil_cartes(graine):
    """Les étapes du réveil, mélangées pour cette partie : [(lettre, étape)]."""
    return list(zip(LETTRES, melange(graine, "reveil", donnees()["reveil"])))


def reveil_reponse(graine):
    """Les lettres des cartes dans le bon ordre (du micrologiciel à la session)."""
    pos = {e: l for l, e in reveil_cartes(graine)}
    return [pos[e] for e in donnees()["reveil"]]


def orchestre(graine):
    """Les tâches mélangées pour cette partie : [(n°, tâche, lettre du bon musicien)] ; musiciens A-E dans l'ordre."""
    o = donnees()["orchestre"]
    lettre = {m: LETTRES[i] for i, m in enumerate(o["musiciens"])}
    return [(i + 1, x["id"], lettre[x["rep"]]) for i, x in enumerate(melange(graine, "orchestre", o["taches"]))]


def range_boites(graine):
    """Les applications à ranger, mélangées : [(n°, id, « c » conteneur ou « v » machine virtuelle)]."""
    return [(i + 1, x["id"], x["rep"]) for i, x in enumerate(melange(graine, "range", donnees()["range"]))]


def besoin_epreuve(graine):
    """Le besoin de l'épreuve M7 pour cette partie (jouer, dessiner, serveur, robot)."""
    import hashlib
    e = donnees()["epreuve"]
    return e[int(hashlib.sha256(f"{graine}:besoin".encode()).hexdigest()[:8], 16) % len(e)]


def drapeau(graine):
    import hashlib
    return "TG{" + besoin_epreuve(graine) + "-" + hashlib.sha256(f"{graine}:drapeau".encode()).hexdigest()[:8] + "}"


def piece(pid):
    """(catégorie, pièce) d'un identifiant du catalogue (« p2 » ou « P2 »), ou (None, None)."""
    for cat, l in donnees()["catalogue"].items():
        if cat == "note":
            continue
        for x in l:
            if x["id"] == (pid or "").upper():
                return cat, x
    return None, None


def montage(choix, besoin):
    """Vérifie une machine montée (spécification commune) : {problemes: [codes], points, watts, fournit, coeurs, gio,
    go}. Codes : manque:<cat>, double:<cat>, inconnu:<id>, prise, memoire, alimentation, budget, besoin:graphique,
    besoin:sans_graphique, besoin:gio, besoin:go, besoin:coeurs, besoin:watts, besoin:mini."""
    pb = []
    pris = {}
    for pid in choix:
        cat, x = piece(pid)
        if not x:
            pb.append("inconnu:" + str(pid).upper())
        elif cat in pris:
            pb.append("double:" + cat)
        else:
            pris[cat] = x
    for cat in donnees()["categories"]:
        if cat not in pris:
            pb.append("manque:" + cat)
    P, C, M, S, G, A = (pris.get(c, {}) for c in donnees()["categories"])
    points = sum(x.get("points", 0) for x in pris.values())
    watts = sum(x.get("watts", 0) for c, x in pris.items() if c != "alimentation")
    fournit = A.get("fournit", 0)
    if P and C and P["prise"] != C["prise"]:
        pb.append("prise")
    if M and C and M["type"] != C["type"]:
        pb.append("memoire")
    if A and watts > fournit:
        pb.append("alimentation")
    b = donnees()["besoins"].get(besoin, {})
    if points > b.get("budget", 999):
        pb.append("budget")
    if b.get("graphique") and G and G.get("aucune"):
        pb.append("besoin:graphique")
    if b.get("sans_graphique") and G and not G.get("aucune"):
        pb.append("besoin:sans_graphique")
    if M and M["gio"] < b.get("gio", 0):
        pb.append("besoin:gio")
    if S and S["go"] < b.get("go", 0):
        pb.append("besoin:go")
    if P and P["coeurs"] < b.get("coeurs", 0):
        pb.append("besoin:coeurs")
    if "watts_max" in b and watts > b["watts_max"]:
        pb.append("besoin:watts")
    if b.get("mini") and C and not C.get("mini"):
        pb.append("besoin:mini")
    return {"problemes": pb, "points": points, "watts": watts, "fournit": fournit, "coeurs": P.get("coeurs", 0),
            "gio": M.get("gio", 0), "go": S.get("go", 0)}


def energie(watts, heures):
    """Wh et kWh consommés : watts × heures."""
    return {"wh": watts * heures, "kwh": watts * heures / 1000}


def boite_de(cpuinfo, cgroup, dockerenv=False, containerenv=False):
    """La maison dans la maison (spécification commune) : {vm: le processeur annonce « hypervisor », conteneur:
    « docker » / « podman » / « conteneur » / None} lu dans /proc/cpuinfo, /proc/1/cgroup, /.dockerenv,
    /run/.containerenv."""
    vm = re.search(r"^flags\s*:.*\bhypervisor\b", cpuinfo or "", re.M) is not None
    if dockerenv:
        c = "docker"
    elif containerenv:
        c = "podman"
    elif re.search(r"(docker|kubepods|containerd|lxc|libpod)", cgroup or ""):
        c = "conteneur"
    else:
        c = None
    return {"vm": vm, "conteneur": c}


MARQUE = "# terminagotchi: collection"     # la première ligne, jamais traduite (le jeu reconnaît la collection intacte)


def collection_texte(state):
    """La collection de la créature en texte (espèces seulement : aucun surnom, aucune donnée personnelle)."""
    from . import bestiaire
    noms = []
    for x in state.get("captures", []) or []:
        e = bestiaire.espece(x.get("espece")) if isinstance(x, dict) else None
        noms.append(e["nom"] if e else (x.get("espece") if isinstance(x, dict) else str(x)))
    lignes = [MARQUE, t("ma.collection.titre")] + [f"{i + 1}. {n}" for i, n in enumerate(noms)]
    if not noms:
        lignes.append(t("ma.collection.vide"))
    return "\n".join(lignes) + "\n"


# ================================================================ la vraie machine (lue, jamais modifiée)
def _lire_sys(chemin):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def coeurs():
    """Ce que `nproc` affiche ici (le jeu le lance s'il existe, sinon il le calcule comme lui)."""
    if shutil.which("nproc") and not IS_WIN:
        try:
            r = subprocess.run(["nproc"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip().isdigit():
                return int(r.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def processeurs_cpuinfo():
    """Le nombre de lignes « processor » de /proc/cpuinfo (None hors Linux)."""
    txt = _lire_sys("/proc/cpuinfo")
    return len(re.findall(r"^processor\s*:", txt, re.M)) or None


def coeurs_justes():
    """Les réponses justes à « combien de cœurs ? » ici : nproc, et aussi ce que comptent os.cpu_count et
    /proc/cpuinfo (ils diffèrent quand un programme n'a droit qu'à une partie des cœurs)."""
    s = {coeurs()}
    if os.cpu_count():
        s.add(os.cpu_count())
    p = processeurs_cpuinfo()
    if p:
        s.add(p)
    return s


def memoire_kio():
    m = re.search(r"^MemTotal:\s+(\d+)\s*kB", _lire_sys("/proc/meminfo"), re.M)
    if m:
        return int(m.group(1))
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // 1024
    except (ValueError, OSError, AttributeError):
        return None


def noyau():
    return platform.release()


def micrologiciel():
    if not sys.platform.startswith("linux"):
        return None
    return "UEFI" if os.path.isdir("/sys/firmware/efi") else "BIOS"


def premier_programme():
    return _lire_sys("/proc/1/comm").strip() or None


def session():
    return os.path.basename(os.environ.get("SHELL", "")) or None


def allumee_depuis():
    """Les minutes depuis l'allumage (/proc/uptime), ou None."""
    try:
        return int(float(_lire_sys("/proc/uptime").split()[0]) // 60)
    except (ValueError, IndexError):
        return None


def disques():
    """Le nombre de disques (lsblk : les « disk » de /sys/block, sans les disques en mémoire ni les boucles)."""
    try:
        return len([d for d in os.listdir("/sys/block") if not d.startswith(("loop", "ram", "zram", "dm-", "md", "sr"))])
    except OSError:
        return None


def bus_pci():
    try:
        return len(os.listdir("/sys/bus/pci/devices"))
    except OSError:
        return None


def bus_usb():
    try:
        return len([d for d in os.listdir("/sys/bus/usb/devices") if ":" not in d and not d.startswith("usb")])
    except OSError:
        return None


def os_release():
    d = {}
    for l in _lire_sys("/etc/os-release").splitlines():
        if "=" in l:
            k, v = l.split("=", 1)
            d[k.strip()] = v.strip().strip('"')
    return d


def boite():
    return boite_de(_lire_sys("/proc/cpuinfo"), _lire_sys("/proc/1/cgroup"), os.path.exists("/.dockerenv"),
                    os.path.exists("/run/.containerenv"))


# ================================================================ l'état, le terrain, le carnet de la salle
def c_(state):
    c = state.setdefault("machinerie", {})
    c.setdefault("faits", [])
    c.setdefault("allumees", [])
    return c


def dossier():
    return core.TERRAIN / "machines"


CARNET = "carnet_de_la_salle.txt"


def noter(etiquette, texte):
    try:
        d = dossier()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / CARNET, "a", encoding="utf-8") as f:
            f.write(f"[{etiquette}] {texte}\n")
        return True
    except OSError:
        return False


def carnet():
    try:
        return (dossier() / CARNET).read_text(encoding="utf-8")
    except OSError:
        return ""


def dans_carnet(etiquette, mot="ok"):
    return re.search(rf"^\[{etiquette}\].*\({mot}\)\s*$", carnet(), re.M) is not None


def _graine(state):
    return f"{state.get('partie') or '1'}:{int(state.get('born', 0))}"


def _lire(rel):
    try:
        return (core.TERRAIN / rel).read_bytes().decode("utf-8", "replace")
    except OSError:
        return ""


def _fait(c, cle):
    if cle in c["faits"]:
        return True
    c["faits"].append(cle)
    return False


def _ecrire(rel, contenu):
    p = core.TERRAIN / rel
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            p.write_bytes(contenu)
        else:
            p.write_text(contenu, encoding="utf-8")
        return True
    except OSError:
        return False


def _sur(s):
    """Un texte posé dans un script shell entre guillemets doubles : sans " $ ` \\."""
    return re.sub(r'["$`\\]', "'", s)


def photo():
    """La « photo » de la créature : exactement 1 048 576 octets (1 Mio), toujours les mêmes."""
    n = donnees()["photo"]["octets"]
    return (bytes(range(256)) * (n // 256 + 1))[:n]


def conteneur_sh():
    """Le script du conteneur JETABLE (M5 bis), lu par l'enfant avant d'être lancé (avec un adulte). Tout reste dans
    machines/conteneurs/ ; l'image est minuscule (alpine) ; --rm : le conteneur disparaît après avoir parlé."""
    c = donnees()["conteneur"]
    img = c["image"]
    return ("#!/bin/sh\n"
            f"# {_sur(t('ma.sh.c1'))}\n"
            f"# {_sur(t('ma.sh.c2'))}\n"
            f"# {_sur(t('ma.sh.c3'))}\n"
            "ICI=$(cd \"$(dirname \"$0\")\" && pwd)\n"
            f"D=\"$ICI/{c['dossier']}\"\n"
            f"IMAGE={img}\n"
            "P=\"podman --root $D/stockage --runroot $D/run --tmpdir $D/tmp\"\n"
            "absent() {\n"
            f"  echo \"{_sur(t('ma.sh.absent'))}\"\n"
            f"  echo \"[conteneur] podman absent (raconte)\" >> \"$ICI/{CARNET}\"\n"
            "  exit 1\n"
            "}\n"
            "case \"$1\" in\n"
            "lancer)\n"
            "  command -v podman >/dev/null 2>&1 || absent\n"
            "  mkdir -p \"$D/stockage\" \"$D/run\" \"$D/tmp\" \"$D/xdg\" && chmod 700 \"$D/run\"\n"
            f"  echo \"{_sur(t('ma.sh.lance', mo=c['taille_mo']))}\"\n"
            "  echo \"  podman run --rm --network=none $IMAGE echo bonjour\"\n"
            "  T=\"\"; command -v timeout >/dev/null 2>&1 && T=\"timeout 300\"\n"
            "  if env XDG_RUNTIME_DIR=\"$D/run\" XDG_DATA_HOME=\"$D/xdg\" XDG_CONFIG_HOME=\"$D/xdg\" \\\n"
            "       $T $P run --rm --network=none $IMAGE echo bonjour; then\n"
            f"    echo \"{_sur(t('ma.sh.ps'))}\"\n"
            "    env XDG_RUNTIME_DIR=\"$D/run\" XDG_DATA_HOME=\"$D/xdg\" XDG_CONFIG_HOME=\"$D/xdg\" $P ps -a\n"
            f"    echo \"[conteneur] alpine (ok)\" >> \"$ICI/{CARNET}\"\n"
            "  else\n"
            f"    echo \"{_sur(t('ma.sh.echec'))}\"\n"
            f"    echo \"[conteneur] alpine (echec)\" >> \"$ICI/{CARNET}\"\n"
            "    exit 1\n"
            "  fi ;;\n"
            "effacer)\n"
            "  command -v podman >/dev/null 2>&1 || absent\n"
            "  env XDG_RUNTIME_DIR=\"$D/run\" XDG_DATA_HOME=\"$D/xdg\" XDG_CONFIG_HOME=\"$D/xdg\" $P system reset --force\n"
            f"  echo \"{_sur(t('ma.sh.efface'))}\" ;;\n"
            "*)\n"
            f"  echo \"{_sur(t('ma.sh.explique1'))}\"\n"
            f"  echo \"{_sur(t('ma.sh.explique2', mo=c['taille_mo']))}\"\n"
            "  echo \"  $IMAGE\"\n"
            f"  echo \"{_sur(t('ma.sh.explique3'))}\"\n"
            "  echo \"  sh conteneur_jetable.sh lancer\"\n"
            f"  command -v podman >/dev/null 2>&1 || echo \"{_sur(t('ma.sh.absent'))}\" ;;\n"
            "esac\n")


def meubles(state):
    """Ce que le jeu pose dans la Salle des Machines quand elle s'ouvre : {chemin relatif au terrain: contenu}."""
    f = donnees()["ferme"]
    return {"machines/plan_de_la_salle.txt": t("ma.meuble.plan", nom=state.get("name", "")) + "\n",
            f"machines/{CARNET}": t("ma.meuble.carnet") + "\n",
            "machines/" + donnees()["photo"]["nom"]: photo(),
            "machines/conteneur_jetable.sh": conteneur_sh(),
            "machines/" + f["collection"]: collection_texte(state),
            "machines/ferme/disque_2/LISEZMOI.txt": t("ma.meuble.disque_2") + "\n",
            "machines/" + f["loin"] + "LISEZMOI.txt": t("ma.meuble.loin") + "\n"}


BESOINS = {"sm0": ["plan_de_la_salle.txt"], "sm3": [donnees()["photo"]["nom"]], "sm7": ["conteneur_jetable.sh"],
           "sm9": ["collection.txt", "ferme/disque_2/LISEZMOI.txt", "ferme/loin/LISEZMOI.txt"]}


def meubler(state, lid, step):
    """Appelé à chaque tour pendant une leçon de la Salle : les fichiers dont la leçon a besoin, les ponts des nombres."""
    d = dossier()
    if not d.is_dir():
        return
    tous = meubles(state)
    for rel in BESOINS.get(lid, []):
        if not (d / rel).exists() and "machines/" + rel in tous:
            _ecrire("machines/" + rel, tous["machines/" + rel])
    if lid == "sm9" and step <= 1:                   # tar dans le mauvais sens (tar czf collection.txt …) : on la repose
        txt = _lire("machines/collection.txt")
        if not txt.startswith(MARQUE):
            _ecrire("machines/collection.txt", tous["machines/collection.txt"])
    pont_maths(state, lid, step)


def pont_maths(state, lid, step):
    """Les Ponts des Nombres (§ 7.10) : avant une étape qui déclare une notion, la créature propose le pont, une fois.
    Jamais un mur : l'étape se fait sans."""
    from . import maths, programme
    e = programme.donnees().get("etapes", {}).get(f"{lid}.{step}", {})
    c = c_(state)
    for mid in e.get("maths", []):
        if mid in maths.noeuds() and not maths.sait(state, mid) and not _fait(c, "pont:" + mid):
            core.say(state, t("ma.pont", notion=maths.titre(mid), cmd="maths " + mid), 16)
            core.terminal(state, "🔢 " + t("ma.pont", notion=maths.titre(mid), cmd="maths " + mid))
            break


# ---------------------------------------------------------------- ce que les étapes vérifient (fichiers et carnet)
def _qcow2():
    try:
        return (dossier() / donnees()["vm"]["disque"]).read_bytes()[:4] == b"QFI\xfb"
    except OSError:
        return False


def _copie_valide(rel):
    """Une copie de la sauvegarde (archive + empreinte) au bon endroit, et l'archive correspond à son empreinte."""
    import hashlib
    f = donnees()["ferme"]
    d = dossier() / rel
    try:
        arch = (d / f["archive"]).read_bytes()
        note = (d / f["empreinte"]).read_text(encoding="utf-8", errors="replace").split()
    except OSError:
        return False
    return bool(note) and note[0] == hashlib.sha256(arch).hexdigest() and arch[:2] == b"\x1f\x8b"


def _archive_ok():
    try:
        return (dossier() / donnees()["ferme"]["archive"]).read_bytes()[:2] == b"\x1f\x8b"
    except OSError:
        return False


def _empreinte_ok():
    import hashlib
    f = donnees()["ferme"]
    try:
        note = (dossier() / f["empreinte"]).read_text(encoding="utf-8").split()
        return bool(note) and note[0] == hashlib.sha256((dossier() / f["archive"]).read_bytes()).hexdigest()
    except OSError:
        return False


def _restauree():
    txt = _lire("machines/" + donnees()["ferme"]["collection"])
    return txt.startswith(MARQUE) and dans_carnet("panne")


FS = {
    "ma_coeurs": lambda: dans_carnet("coeurs"),
    "ma_memoire": lambda: dans_carnet("memoire"),
    "ma_monte1": lambda: dans_carnet("monte1"),
    "ma_interrupteurs": lambda: dans_carnet("interrupteurs"),
    "ma_allume": lambda: dans_carnet("allume"),
    "ma_reveil": lambda: dans_carnet("reveil"),
    "ma_orchestre": lambda: dans_carnet("orchestre"),
    "ma_range": lambda: dans_carnet("range"),
    "ma_conteneur": lambda: dans_carnet("histoire_conteneur"),
    "ma_qcow2": _qcow2,
    "ma_archive": _archive_ok,
    "ma_empreinte": _empreinte_ok,
    "ma_disque_2": lambda: _copie_valide("ferme/disque_2"),
    "ma_loin": lambda: _copie_valide("ferme/loin"),
    "ma_panne": lambda: dans_carnet("panne"),
    "ma_restauree": _restauree,
    "ma_monte": lambda: dans_carnet("monte"),
    "ma_demarre": lambda: dans_carnet("demarre"),
    "ma_drapeau": lambda: dans_carnet("drapeau"),
}
CREE = {"ma_qcow2": "machines/disque_virtuel.qcow2", "ma_archive": "machines/sauvegarde.tar.gz",
        "ma_empreinte": "machines/sauvegarde.sha256"}

LS = r"^(ls|dir|gci|get-childitem)\b"
LIRE = r"^(cat|type|gc|get-content|less|more|head|tail)\b"
MA = r"^(tg\s+)?machines\s+"
SH = r"^((sh|bash)\s+|\./)\S*"


def _n(lid, i, **k):
    d = {"dit": f"hist.{lid}.{i}.dit", "bravo": f"hist.{lid}.{i}.bravo"}
    d.update(k)
    return d


LECONS = {
    # la porte de la salle des machines
    "sm0": {"titre": "hist.sm0.titre", "skill": None, "steps": [
        {"dit": ("hist.entree.dit", {"piece": "machines"}), "cmd": "cd ~/terrain_terminagotchi/machines", "ici": "machines",
         "bravo": ("hist.entree.bravo", {"piece": "machines"})},
        _n("sm0", 1, cmd="ls", re=LS, ou="machines"),
        _n("sm0", 2, cmd="cat plan_de_la_salle.txt", re=LIRE + r".*plan_de_la_salle"),
    ]},
    # M1 les organes : le cuisinier, le plan de travail, le garde-manger
    "sm1": {"titre": "hist.sm1.titre", "skill": None, "steps": [
        _n("sm1", 0, cmd="nproc", re=r"^(nproc|lscpu)\b", outil="nproc", win=False, ou="machines"),
        _n("sm1", 1, cmd="machines coeurs ?", fs="ma_coeurs", outil="nproc"),
        _n("sm1", 2, cmd="free -h", re=r"^(free|cat\s+/proc/meminfo|vmstat)\b", outil="free", win=False),
        _n("sm1", 3, cmd="machines memoire ?", fs="ma_memoire", outil="free"),
        _n("sm1", 4, cmd="lsblk", re=r"^(lsblk|df)\b", outil="lsblk", win=False, tout_code=True),
        _n("sm1", 5, cmd="machines ouvre", re=MA + r"ouvre\b"),
    ]},
    # M1 la ville qui relie tout : /proc/cpuinfo, la carte mère et ses bus, Monte ta machine niveau 1
    "sm2": {"titre": "hist.sm2.titre", "skill": None, "steps": [
        _n("sm2", 0, cmd="head -5 /proc/cpuinfo", re=r"^(cat|head|less|grep)\b.*/proc/cpuinfo", outil="/proc/cpuinfo", win=False,
           ou="machines"),
        _n("sm2", 1, cmd="grep -c ^processor /proc/cpuinfo", re=r"^grep\s+-\w*c\w*\s+['\"]?\^?processor.*/proc/cpuinfo",
           outil="/proc/cpuinfo", win=False),
        _n("sm2", 2, cmd="lspci", re=r"^lspci\b", outil="lspci", win=False, tout_code=True),
        _n("sm2", 3, cmd="lsusb", re=r"^lsusb\b", outil="lsusb", win=False, tout_code=True),
        _n("sm2", 4, cmd="machines monte 1 ? ? ? ? ? ?", fs="ma_monte1"),
    ]},
    # M2 des 0 et des 1 : hexadécimal, les interrupteurs, les unités
    "sm3": {"titre": "hist.sm3.titre", "skill": None, "steps": [
        _n("sm3", 0, cmd="printf '%x\\n' 65", re=r"^printf\s+['\"]?%x", win=False, ou="machines"),
        _n("sm3", 1, cmd="echo -n A | xxd -b", re=r"^(echo\s+-n|printf)\s+['\"]?A['\"]?\s*\|\s*xxd\s+-\w*b", outil="xxd",
           win=False),
        _n("sm3", 2, cmd="machines interrupteurs ?", fs="ma_interrupteurs"),
        _n("sm3", 3, cmd="machines allume ?", fs="ma_allume"),
        _n("sm3", 4, cmd="wc -c photo.bin", re=r"^(wc\s+-c\b.*photo\.bin|stat\b.*%s.*photo\.bin|ls\s+-\w*l\w*\b.*photo\.bin)",
           win=False),
        _n("sm3", 5, cmd="machines unites", re=MA + r"unit[eé]s?\b"),
    ]},
    # M3 le réveil de la machine
    "sm4": {"titre": "hist.sm4.titre", "skill": None, "steps": [
        _n("sm4", 0, cmd="uname -r", re=r"^uname\s+-\w*r", win=False, ou="machines"),
        _n("sm4", 1, cmd="uptime", re=r"^uptime\b", outil="uptime", win=False),
        _n("sm4", 2, cmd="dmesg | head -5", re=r"^dmesg\b", outil="dmesg", win=False, tout_code=True),
        _n("sm4", 3, cmd="systemd-analyze", re=r"^systemd-analyze\b", outil="systemd-analyze", win=False, tout_code=True),
        _n("sm4", 4, cmd="machines reveil", re=MA + r"r[eé]veil\s*$"),
        _n("sm4", 5, cmd="machines reveil ? ? ? ? ?", fs="ma_reveil"),
    ]},
    # M4 le chef d'orchestre (le système d'exploitation, les licences)
    "sm5": {"titre": "hist.sm5.titre", "skill": None, "steps": [
        _n("sm5", 0, cmd="uname -srmo", re=r"^uname\b", win=False, ou="machines"),
        _n("sm5", 1, cmd="cat /etc/os-release", re=LIRE + r".*/etc/(os|lsb)-release", outil="/etc/os-release", win=False),
        _n("sm5", 2, cmd="ps", re=r"^ps\b", win=False),
        _n("sm5", 3, cmd="which ls", re=r"^(which|command\s+-v|type)\s+ls\b", win=False),
        _n("sm5", 4, cmd="lsmod | head -5", re=r"^(lsmod|cat\s+/proc/modules)\b", outil="lsmod", win=False, tout_code=True),
        _n("sm5", 5, cmd="machines orchestre", re=MA + r"orchestre\s*$"),
        _n("sm5", 6, cmd="machines orchestre ? ? ? ? ?", fs="ma_orchestre"),
        _n("sm5", 7, cmd="machines licences", re=MA + r"licences?\b"),
    ]},
    # M5 la maison dans la maison
    "sm6": {"titre": "hist.sm6.titre", "skill": None, "steps": [
        _n("sm6", 0, cmd="cat /proc/1/cgroup", re=LIRE + r".*/proc/(1|self)/cgroup", outil="/proc/1/cgroup", win=False, tout_code=True,
           ou="machines"),
        _n("sm6", 1, cmd="machines boite", re=MA + r"bo[iî]te\b"),
        _n("sm6", 2, cmd="machines range", re=MA + r"range\s*$"),
        _n("sm6", 3, cmd="machines range ? ? ? ?", fs="ma_range"),
    ]},
    # M5 bis ta propre machine virtuelle (AVEC UN ADULTE ; sans les outils, elle se raconte)
    "sm7": {"titre": "hist.sm7.titre", "skill": None, "steps": [
        _n("sm7", 0, cmd="machines adulte", re=MA + r"adulte\b", ou="machines"),
        _n("sm7", 1, cmd="command -v podman qemu-img virsh", re=r"^(command\s+-v|which|type)\s+\S", win=False, tout_code=True),
        _n("sm7", 2, cmd="cat conteneur_jetable.sh", re=LIRE + r".*conteneur_jetable\.sh"),
        _n("sm7", 3, cmd="sh conteneur_jetable.sh", re=SH + r"conteneur_jetable\.sh\s*$", win=False, tout_code=True),
        _n("sm7", 4, cmd="sh conteneur_jetable.sh lancer", re=SH + r"conteneur_jetable\.sh\s+lancer\b", outil="podman",
           win=False, tout_code=True),
        _n("sm7", 5, cmd="machines conteneur", fs="ma_conteneur"),
        _n("sm7", 6, cmd="qemu-img create -f qcow2 disque_virtuel.qcow2 1G", fs="ma_qcow2", outil="qemu-img", win=False),
        _n("sm7", 7, cmd="qemu-img info disque_virtuel.qcow2", re=r"^qemu-img\s+info\b.*disque_virtuel", outil="qemu-img",
           win=False),
        _n("sm7", 8, cmd="virsh -r -c qemu:///system list --all", re=r"^virsh\b.*\blist\b", outil="virsh", win=False,
           tout_code=True),
        _n("sm7", 9, cmd="machines vm", re=MA + r"vm\b"),
    ]},
    # M6 les fermes de serveurs (et l'énergie)
    "sm8": {"titre": "hist.sm8.titre", "skill": None, "steps": [
        _n("sm8", 0, cmd="df -h .", re=r"^df\b", win=False, ou="machines"),
        _n("sm8", 1, cmd="du -sh .", re=r"^du\b", win=False),
        _n("sm8", 2, cmd="machines ferme", re=MA + r"ferme\b"),
        _n("sm8", 3, cmd="machines energie", re=MA + r"[eé]nergie\b"),
    ]},
    # M6 la sauvegarde 3-2-1 (une panne simulée, seulement dans le terrain)
    "sm9": {"titre": "hist.sm9.titre", "skill": None, "steps": [
        _n("sm9", 0, cmd="ls ferme", re=LS + r".*ferme", ou="machines"),
        _n("sm9", 1, cmd="tar czf sauvegarde.tar.gz collection.txt", fs="ma_archive", win=False),
        _n("sm9", 2, cmd="sha256sum sauvegarde.tar.gz > sauvegarde.sha256", fs="ma_empreinte", win=False),
        _n("sm9", 3, cmd="cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/", fs="ma_disque_2", win=False),
        _n("sm9", 4, cmd="cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/", fs="ma_loin", win=False),
        _n("sm9", 5, cmd="machines panne", fs="ma_panne"),
        {"dit": "hist.sm9.6.dit", "cmd": "cd ferme/loin", "ici": "machines/ferme/loin", "exact": True,
         "bravo": "hist.sm9.6.bravo"},
        _n("sm9", 7, cmd="sha256sum -c sauvegarde.sha256", re=r"^sha256sum\s+(-c|--check)\b.*sauvegarde\.sha256", win=False,
           ou="machines/ferme/loin"),
        _n("sm9", 8, cmd="tar xzf sauvegarde.tar.gz -C ../..", fs="ma_restauree", win=False),
    ]},
    # M7 l'épreuve : Monte ta machine (drapeau TG{…})
    "sm10": {"titre": "hist.sm10.titre", "skill": None, "steps": [
        _n("sm10", 0, cmd="machines monte", re=MA + r"monte\s*$", ou="machines"),
        _n("sm10", 1, cmd="machines monte ? ? ? ? ? ?", fs="ma_monte"),
        _n("sm10", 2, cmd="machines demarre", fs="ma_demarre"),
        _n("sm10", 3, cmd="machines drapeau ?", fs="ma_drapeau"),
    ]},
}
CHAPITRE = {"id": "machinerie", "n": 14, "piece": "machines", "famille": "Constructs", "monde": True,
            "lecons": [f"sm{i}" for i in range(11)], "objet": "carte_mere_miniature", "titre": "architecte_des_machines"}


# ================================================================ l'arbre du Carrefour : quand la Salle s'ouvre
def _besoin():
    from . import programme
    P = programme.donnees()
    m = next((x for x in P.get("mondes", []) if x["id"] == "machines"), {})
    besoin = []
    for n in m.get("requis", []):
        besoin += [c for c in P.get("tronc", {}).get(n, []) if c not in besoin]
    return besoin


def ouvert(state):
    from . import histoire
    return bool(_besoin()) and all(histoire.fini(state, c) for c in _besoin())


def manque(state):
    from . import histoire
    return [histoire.nom_chapitre(c) for c in _besoin() if not histoire.fini(state, c)]


def annonce(state):
    from . import histoire
    h = histoire.h_(state)
    deja = h.setdefault("mondes_annonces", [])
    if "machinerie" in deja or histoire.fini(state, "machinerie") or not ouvert(state):
        return False
    deja.append("machinerie")
    core.log(state, t("ma.ouvert.log"))
    core.say(state, histoire.dire(state, "ma.ouvert.dit"), 18)
    return True


# ================================================================ les indices et la surveillance
TROU = re.compile(r"(^|\s)(\?|…|<[^>]*>)(\s|$)")
REPONSES = {"machines coeurs ?": "coeurs", "machines memoire ?": "memoire", "machines allume ?": "allume",
            "machines reveil ? ? ? ? ?": "reveil", "machines orchestre ? ? ? ? ?": "orchestre",
            "machines range ? ? ? ?": "range", "machines monte 1 ? ? ? ? ? ?": "monte1",
            "machines monte ? ? ? ? ? ?": "monte", "machines demarre": "demarre", "machines drapeau ?": "drapeau"}


def indice(step, tapees):
    """Un indice de la Salle : un sudo, un trou « ? » recopié, une mauvaise réponse (cœurs, mémoire, interrupteurs,
    réveil, orchestre, boîtes, montage, drapeau), podman lancé sans le script, tar dans le mauvais sens."""
    cmd = step.get("cmd") or ""
    lignes = [(l or "").strip() for l, _c in tapees]
    if any(re.match(r"^sudo\b", l) for l in lignes):
        return t("ma.indice.sudo")
    if cmd.startswith("tar czf") and any(re.match(r"^tar\s+-?c\w*f\s+collection\.txt\b", l) for l in lignes):
        return t("ma.indice.tar_sens")
    if "?" in cmd.split() and any(TROU.search(l) for l in lignes if re.match(MA, l)):
        return t("ma.indice.trou")
    if cmd == "machines interrupteurs ?" and any(re.match(MA + r"interrupteurs\s*$", l) for l in lignes):
        return t("ma.indice.interrupteurs")
    et = REPONSES.get(cmd)
    if et:
        der = [l for l in carnet().splitlines() if l.startswith(f"[{et}]")]
        if der and not der[-1].endswith("(ok)"):
            return t("ma.indice." + et)
    if re.search(r"(^|\s)(podman|docker)\s+run\b", " ".join(lignes)) and cmd.startswith("sh conteneur_jetable"):
        return t("ma.indice.script")
    if cmd.startswith("cp sauvegarde") and any(re.match(r"^cp\b", l) for l in lignes):
        return t("ma.indice.copie")
    return None


SURVEILLE = re.compile(r"(^|[;&|]\s*)(sudo\s+(dmesg|lshw|dmidecode|lspci|fdisk|parted|smartctl|podman|virsh|qemu)|"
                       r"virt-install\b|(podman|docker)\s+run\b)")


def surveiller(state, lignes):
    """À chaque tour : les pièces interrogées s'allument (l'ordinateur ouvert) ; un sudo sur le matériel, un
    virt-install ou un podman / docker run tapé directement : la créature rappelle la règle (une fois)."""
    if not dossier().is_dir():
        return False
    c = c_(state)
    for l in lignes or []:
        for p in pieces_de((l or "").strip()):
            if p not in c["allumees"]:
                c["allumees"].append(p)
    from . import histoire
    les, _e = histoire.lecon_courante(state)
    if les and les["id"] in LECONS:
        return False
    for l in lignes or []:
        m = SURVEILLE.search((l or "").strip())
        if m and not _fait(c, "garde:" + ("sudo" if "sudo" in m.group(0) else "adulte")):
            msg = t("ma.indice.sudo" if "sudo" in m.group(0) else "ma.garde.adulte")
            core.say(state, msg, 16)
            core.terminal(state, "⚠ " + msg)
            return True
    return False


# ================================================================ les dessins (caractères) et les commandes du jeu
def _c(n):
    return fg(n)


COULEURS = {"processeur": 203, "memoire": 117, "stockage": 179, "carte_mere": 78, "graphique": 213, "usb": 229,
            "alimentation": 215}
RANG = {p: i + 1 for i, p in enumerate(["processeur", "memoire", "stockage", "carte_mere", "graphique", "usb",
                                         "alimentation"])}


def grille_ordinateur():
    """L'ordinateur ouvert en caractères : [(caractère, pièce ou None)] par ligne (la pièce colore la case)."""
    W, H = 46, 12
    g = [[(" ", None) for _ in range(W)] for _ in range(H)]

    def met(r, c, ch, p):
        if 0 <= r < H and 0 <= c < W:
            g[r][c] = (ch, p)

    def boite_(r0, c0, r1, c1, p, rempli=" "):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if r in (r0, r1) and c in (c0, c1):
                    ch = {(r0, c0): "┌", (r0, c1): "┐", (r1, c0): "└", (r1, c1): "┘"}[(r, c)]
                elif r in (r0, r1):
                    ch = "─"
                elif c in (c0, c1):
                    ch = "│"
                else:
                    ch = rempli
                met(r, c, ch, p)
    for c in range(W):
        met(0, c, "═", None)
        met(H - 1, c, "═", None)
    for r in range(H):
        met(r, 0, "║", None)
        met(r, W - 1, "║", None)
    for (r, c), ch in {(0, 0): "╔", (0, W - 1): "╗", (H - 1, 0): "╚", (H - 1, W - 1): "╝"}.items():
        met(r, c, ch, None)
    boite_(1, 2, 3, 12, "alimentation", "▒")
    boite_(6, 2, 9, 12, "stockage", "▤")
    boite_(1, 15, 10, 43, "carte_mere", "·")
    boite_(3, 18, 6, 26, "processeur", "▓")
    for k in range(4):
        for r in range(2, 7):
            met(r, 30 + 2 * k, "║", "memoire")
    for c in range(17, 40):
        met(8, c, "▬", "graphique")
    for c in range(17, 21):
        met(9, c, "▭", "usb")
    for p, (r, c) in {"alimentation": (2, 4), "stockage": (7, 4), "carte_mere": (2, 17), "processeur": (4, 21),
                      "memoire": (7, 33), "graphique": (8, 41), "usb": (9, 22)}.items():
        met(r, c, str(RANG[p]), p)
    return g


def dessin_ordinateur(allumees, couleur=True):
    out = []
    for ligne in grille_ordinateur():
        s = ""
        for ch, p in ligne:
            if not couleur:
                s += ch
            elif p is None:
                s += f"{DIM}{ch}{RESET}"
            elif p in allumees:
                s += f"{_c(COULEURS[p])}{BOLD if ch.isdigit() else ''}{ch}{RESET}"
            else:
                s += f"{_c(240)}{ch}{RESET}"
        out.append("  " + s)
    return out


def valeur_piece(p):
    """Ce que la machine dit d'elle-même pour une pièce allumée (jamais de marque, de numéro de série ni d'adresse)."""
    if p == "processeur":
        return t("ma.ouvre.v.processeur", n=coeurs())
    if p == "memoire":
        k = memoire_kio()
        return t("ma.ouvre.v.memoire", gio=f"{k / 1024 ** 2:.1f}") if k else ""
    if p == "stockage":
        n = disques()
        return t("ma.ouvre.v.stockage", n=n) if n else ""
    if p == "carte_mere":
        n = bus_pci()
        return t("ma.ouvre.v.carte_mere", n=n) if n else ""
    if p == "usb":
        n = bus_usb()
        return t("ma.ouvre.v.usb", n=n) if n is not None else ""
    if p == "alimentation":
        m = allumee_depuis()
        return t("ma.ouvre.v.alimentation", h=m // 60, m=m % 60) if m is not None else ""
    return ""


def lignes_ouvre(state):
    c = c_(state)
    al = c["allumees"]
    out = [f" {_c(215)}{BOLD}🔩 " + t("ma.ouvre.titre") + RESET, ""] + dessin_ordinateur(al) + [""]
    for p in donnees()["pieces"]:
        allu = p in al
        v = valeur_piece(p) if allu else ""
        marque = f"{_c(COULEURS[p])}●{RESET}" if allu else f"{DIM}○{RESET}"
        out.append(f"  {marque} {RANG[p]} {t('ma.piece.' + p):<22} " + (v if allu else DIM + t("ma.ouvre.eteinte") + RESET))
    n = len([p for p in donnees()["pieces"] if p in al])
    out += ["", "  " + t("ma.ouvre.compte", n=n, total=len(donnees()["pieces"]))]
    if n < len(donnees()["pieces"]):
        out.append(f"  {DIM}" + t("ma.ouvre.aide") + RESET)
    noter("ouvre", f"{n} (ok)")
    return out


def lignes_coeurs(arg):
    if not arg:
        return [t("ma.coeurs.aide")]
    try:
        n = int(arg)
    except ValueError:
        return [t("ma.coeurs.aide")]
    justes = coeurs_justes()
    if n in justes:
        noter("coeurs", f"{n} (ok)")
        out = [f" {_c(78)}✔ " + t("ma.coeurs.ok", n=n) + RESET]
        if len(justes) > 1:
            out.append("  " + t("ma.coeurs.plusieurs", nproc=coeurs(), cpuinfo=processeurs_cpuinfo() or "?"))
        return out + ["  " + t("ma.coeurs.morale")]
    noter("coeurs", f"{n} (faux)")
    return [f" {_c(203)}✖ " + t("ma.coeurs.faux", n=n) + RESET]


def lignes_memoire(arg):
    if not arg:
        return [t("ma.memoire.aide")]
    k = memoire_kio()
    if not k:
        noter("memoire", "inconnue (ok)")
        return [t("ma.memoire.inconnue")]
    if memoire_ok(arg, k):
        noter("memoire", "juste (ok)")
        return [f" {_c(78)}✔ " + t("ma.memoire.ok", gio=f"{k / 1024 ** 2:.1f}", go=f"{k * 1024 / 1000 ** 3:.1f}") + RESET,
                "  " + t("ma.memoire.morale")]
    noter("memoire", "loin (faux)")
    return [f" {_c(203)}✖ " + t("ma.memoire.faux") + RESET]


def ligne_interrupteurs(b):
    return " ".join(f"{_c(229)}■{RESET}" if x == "1" else f"{DIM}□{RESET}" for x in b)


def lignes_interrupteurs(state, mot):
    if not mot:
        return [t("ma.interrupteurs.aide")]
    mot = mot[:12]
    out = [f" {_c(229)}{BOLD}💡 " + t("ma.interrupteurs.titre") + RESET, "",
           f"  {DIM}{'':<5}128 64 32 16 8 4 2 1{RESET}"]
    total = 0
    for ch, octets in interrupteurs(mot):
        for i, b in enumerate(octets):
            total += 1
            out.append(f"  {BOLD}{(ch if i == 0 else ''):<3}{RESET}  " + ligne_interrupteurs(b) +
                       f"   {b}  = {int(b, 2):>3}  = 0x{int(b, 2):02x}")
    out += ["", "  " + t("ma.interrupteurs.compte", lettres=len(mot), octets=total)]
    if any(len(o) > 1 for _c2, o in interrupteurs(mot)):
        out.append("  " + t("ma.interrupteurs.utf8"))
    lettre = lettre_defi(state.get("name", ""))
    out += ["", f"  {_c(215)}🎯 " + t("ma.interrupteurs.defi", lettre=lettre) + RESET]
    noter("interrupteurs", f"{len(mot)} lettres (ok)")       # jamais le mot lui-même (le prénom reste sur l'écran)
    return out


def lignes_allume(state, arg):
    lettre = lettre_defi(state.get("name", ""))
    if not arg:
        return [t("ma.allume.aide", lettre=lettre)]
    b = re.sub(r"[\s_]", "", arg)
    if not re.fullmatch(r"[01]{8}", b):
        return [t("ma.allume.huit")]
    voulu = bits(ord(lettre))
    out = ["  " + ligne_interrupteurs(b) + f"   {b} = {int(b, 2)}"]
    if b == voulu:
        noter("allume", f"{lettre} (ok)")
        return out + [f" {_c(78)}✔ " + t("ma.allume.ok", lettre=lettre, n=ord(lettre)) + RESET]
    noter("allume", f"{lettre} (faux)")
    return out + [f" {_c(203)}✖ " + t("ma.allume.faux", lettre=lettre, n=int(b, 2), c=chr(int(b, 2)) if 32 < int(b, 2) < 127 else "?") + RESET]


def _fr(x, d=2):
    s = f"{x:,.{d}f}".replace(",", " ")
    return s


def lignes_unites(arg=None):
    try:
        n = int(arg) if arg else (dossier() / donnees()["photo"]["nom"]).stat().st_size
    except (ValueError, OSError):
        n = donnees()["photo"]["octets"]
    u = unites(n)
    out = [f" {_c(117)}{BOLD}📏 " + t("ma.unites.titre", n=_fr(n, 0)) + RESET, "",
           f"  {DIM}{t('ma.unites.mille'):<34}{t('ma.unites.mil24')}{RESET}",
           f"  {_fr(u['ko'])} Ko{'':<18}{_fr(u['kio'])} Kio".replace("  Ko", " Ko"),
           f"  {_fr(u['mo'])} Mo{'':<22}{_fr(u['mio'])} Mio",
           f"  {_fr(u['go'], 4)} Go{'':<20}{_fr(u['gio'], 4)} Gio", "",
           "  " + t("ma.unites.morale"), f"  {DIM}" + t("ma.unites.grands") + RESET]
    noter("unites", f"{n} (ok)")
    return out


def lignes_reveil(state, rep):
    gr = _graine(state)
    cartes = reveil_cartes(gr)
    if not rep:
        out = [f" {_c(215)}{BOLD}⏰ " + t("ma.reveil.titre") + RESET, ""]
        for l, e in cartes:
            out.append(f"  {BOLD}{l}{RESET}  " + t("ma.reveil." + e))
        return out + ["", "  " + t("ma.reveil.aide")]
    r = [x.upper()[:1] for x in rep]
    bon = reveil_reponse(gr)
    if r != bon:
        justes = sum(1 for x, y in zip(r, bon) if x == y)
        noter("reveil", " ".join(r) + " (faux)")
        return [f" {_c(203)}✖ " + t("ma.reveil.faux", n=justes, total=len(bon)) + RESET]
    noter("reveil", " ".join(r) + " (ok)")
    return [f" {_c(78)}✔ " + t("ma.reveil.ok") + RESET, ""] + lignes_etages(1.0) + ["", "  " + t("ma.reveil.morale")]


def etages_valeurs():
    return {"micrologiciel": micrologiciel() or "?", "chargeur": "", "noyau": noyau() or "?",
            "init": premier_programme() or "?", "session": session() or "?"}


def lignes_etages(phase):
    """La machine qui se réveille étage par étage (du bas vers le haut) ; phase 0 → 1 allume les étages un par un."""
    v = etages_valeurs()
    etapes = donnees()["reveil"]
    allumes = int(round(phase * len(etapes)))
    out = []
    for i in range(len(etapes) - 1, -1, -1):
        e = etapes[i]
        on = i < allumes
        val = f" ({v[e]})" if v[e] else ""
        barre = f"{_c(215)}▓▓▓▓{RESET}" if on else f"{DIM}░░░░{RESET}"
        out.append(f"  {barre} {i + 1}. " + (t("ma.etage." + e) + val if on else DIM + t("ma.etage." + e) + RESET))
    return out


def lignes_orchestre(state, rep):
    gr = _graine(state)
    o = orchestre(gr)
    mus = donnees()["orchestre"]["musiciens"]
    if not rep:
        out = [f" {_c(213)}{BOLD}🎼 " + t("ma.orchestre.titre") + RESET, ""]
        out += [f"  {BOLD}{LETTRES[i]}{RESET} " + t("ma.orchestre.m." + m) for i, m in enumerate(mus)]
        out.append("")
        out += [f"  {n}. " + t("ma.orchestre.t." + tid) for n, tid, _l in o]
        return out + ["", "  " + t("ma.orchestre.aide")]
    r = [x.upper()[:1] for x in rep]
    if len(r) != len(o):
        return [t("ma.orchestre.aide")]
    justes = [(n, tid) for (n, tid, l), x in zip(o, r) if x == l]
    out = []
    if len(justes) == len(o):
        noter("orchestre", " ".join(r) + " (ok)")
        out.append(f" {_c(78)}✔ " + t("ma.orchestre.ok") + RESET)
    else:
        noter("orchestre", " ".join(r) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("ma.orchestre.faux", n=len(justes), total=len(o)) + RESET)
    for n, tid in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("ma.orchestre.t." + tid + ".pourquoi"))
    return out


def lignes_licences():
    o = os_release()
    nom = o.get("PRETTY_NAME") or o.get("NAME") or ""
    out = [f" {_c(78)}{BOLD}📜 " + t("ma.licences.titre") + RESET, ""]
    if nom:
        out.append("  " + t("ma.licences.toi", nom=nom))
    out += ["  " + t("ma.licences.libre"), "  " + t("ma.licences.proprio"), "  " + t("ma.licences.gpl"),
            "  " + t("ma.licences.distrib"), f"  {DIM}" + t("ma.licences.grands") + RESET]
    noter("licences", "lues (ok)")
    return out


MAISON = ["   ╔══════════════════════╗", "   ║  ⌂  {a:<17}║", "   ║   ┌──────────────┐   ║", "   ║   │ ⌂ {b:<11}│   ║",
          "   ║   │  ┌────────┐  │   ║", "   ║   │  │ 📦 {c:<5}│  │   ║", "   ║   │  └────────┘  │   ║",
          "   ║   └──────────────┘   ║", "   ╚══════════════════════╝"]


def lignes_boite():
    b = boite()
    out = [f" {_c(117)}{BOLD}🏠 " + t("ma.boite.titre") + RESET, ""]
    out += [l.format(a=t("ma.boite.vraie")[:17], b=t("ma.boite.vm")[:11], c=t("ma.boite.app")[:5]) for l in MAISON]
    out.append("")
    if b["conteneur"]:
        out.append("  📦 " + t("ma.boite.dans_conteneur", quoi=b["conteneur"]))
    if b["vm"]:
        out.append("  🏠 " + t("ma.boite.dans_vm"))
    if not b["vm"] and not b["conteneur"]:
        out.append("  🏠 " + t("ma.boite.vraie_machine"))
    out += ["", "  " + t("ma.boite.vm_def"), "  " + t("ma.boite.conteneur_def"), f"  {DIM}" + t("ma.boite.grands") + RESET]
    noter("boite", "vue (ok)")
    return out


def lignes_range(state, rep):
    gr = _graine(state)
    r_ = range_boites(gr)
    if not rep:
        out = [f" {_c(117)}{BOLD}📦 " + t("ma.range.titre") + RESET, ""]
        out += [f"  {n}. " + t("ma.range." + i) for n, i, _r in r_]
        return out + ["", "  " + t("ma.range.aide")]
    r = [x.lower()[:1] for x in rep]
    if len(r) != len(r_) or any(x not in "cv" for x in r):
        return [t("ma.range.aide")]
    justes = [(n, i) for (n, i, rr), x in zip(r_, r) if x == rr]
    out = []
    if len(justes) == len(r_):
        noter("range", " ".join(r) + " (ok)")
        out.append(f" {_c(78)}✔ " + t("ma.range.ok") + RESET)
    else:
        noter("range", " ".join(r) + " (faux)")
        out.append(f" {_c(203)}✖ " + t("ma.range.faux", n=len(justes), total=len(r_)) + RESET)
    for n, i in justes:
        out.append(f"  {_c(78)}✔{RESET} {n}. " + t("ma.range." + i + ".pourquoi"))
    return out


def lignes_adulte():
    c = donnees()["conteneur"]
    out = [f" {_c(215)}{BOLD}🧑‍🔧 " + t("ma.adulte.titre") + RESET, ""]
    out += ["  " + l for l in t("ma.adulte.regles", mo=c["taille_mo"]).split("\n")]
    outils = [(o, shutil.which(o) is not None) for o in ("podman", "qemu-img", "virsh")]
    out += ["", "  " + t("ma.adulte.outils") + " " +
            "  ".join(f"{_c(78)}✔ {o}{RESET}" if la else f"{DIM}✖ {o}{RESET}" for o, la in outils)]
    if not any(la for _o, la in outils):
        out.append("  " + t("ma.adulte.aucun"))
    noter("adulte", "lu (ok)")
    return out


CONTENEUR = [["  ┌─────────┐", "  │  📦     │", "  │  alpine │", "  └─────────┘"],
             ["  ┌─────────┐", "  │  📦 💬  │", "  │ bonjour │", "  └─────────┘"],
             ["  ┌ ─ ─ ─ ─ ┐", "    ✨  ✨   ", "  │  --rm   │", "  └ ─ ─ ─ ─ ┘"]]


def lignes_conteneur(state):
    vrai = dans_carnet("conteneur", "ok")
    out = [f" {_c(117)}{BOLD}📦 " + t("ma.conteneur.titre") + RESET, ""]
    for k, d in enumerate(CONTENEUR):
        out += [l + "   " + (t(f"ma.conteneur.temps{k}") if i == 1 else "") for i, l in enumerate(d)]
    out.append("")
    out.append("  " + t("ma.conteneur.vrai" if vrai else "ma.conteneur.raconte"))
    out += ["  " + t("ma.conteneur.image"), f"  {DIM}" + t("ma.conteneur.grands") + RESET]
    noter("histoire_conteneur", ("vrai" if vrai else "raconte") + " (ok)")
    return out


def lignes_vm():
    out = [f" {_c(117)}{BOLD}🖥 " + t("ma.vm.titre") + RESET, ""]
    p = dossier() / donnees()["vm"]["disque"]
    if _qcow2():
        try:
            reel = p.stat().st_blocks * 512
        except (OSError, AttributeError):
            reel = p.stat().st_size
        out.append("  " + t("ma.vm.disque", reel=_fr(reel / 1024, 0)) )
    for k in range(1, 8):
        out.append(f"  {k}. " + t(f"ma.vm.etape{k}"))
    out += ["", "  " + t("ma.vm.adulte"), f"  {DIM}" + t("ma.vm.grands") + RESET]
    noter("vm", "racontee (ok)")
    return out


FERME = ["   ❄  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  ❄", "   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐", "   │▤ ● ▤│ │▤ ● ▤│ │▤ ● ▤│ │▤ ● ▤│",
         "   │▤ ● ▤│ │▤ ● ▤│ │▤ ● ▤│ │▤ ● ▤│", "   └──────┘ └──────┘ └──────┘ └──────┘", "     ⚡═════════╪═════════╪═════════⚡"]


def lignes_ferme():
    out = [f" {_c(78)}{BOLD}🏭 " + t("ma.ferme.titre") + RESET, ""] + [f"  {_c(117)}{l}{RESET}" for l in FERME] + [""]
    for k in ("serveur", "datacenter", "cloud", "redondance", "froid"):
        out.append("  • " + t("ma.ferme." + k))
    noter("ferme", "vue (ok)")
    return out


def lignes_energie():
    e = donnees()["energie"]
    x = energie(e["watts"], e["heures"])
    out = [f" {_c(78)}{BOLD}🌱 " + t("ma.energie.titre") + RESET, "",
           "  " + t("ma.energie.calcul", w=e["watts"], h=_fr(e["heures"], 0), wh=_fr(x["wh"], 0), kwh=_fr(x["kwh"], 0)),
           "  " + t("ma.energie.fabrication"), ""]
    for k in range(1, 5):
        out.append(f"  {_c(78)}✔{RESET} " + t(f"ma.energie.geste{k}"))
    out += ["", f"  {DIM}" + t("ma.energie.grands") + RESET]
    noter("energie", "vue (ok)")
    return out


def bilan_321():
    """(copies, supports, loin) : les endroits qui gardent la collection (le poste, le disque 2, loin) ; chaque endroit est
    un support différent."""
    f = donnees()["ferme"]
    ailleurs = [x for x in ("ferme/disque_2", "ferme/loin") if _copie_valide(x)]
    original = _lire("machines/" + f["collection"]).startswith(MARQUE)
    copies = len(ailleurs) + (1 if original or _copie_valide("") else 0)     # une copie par endroit
    return copies, copies, "ferme/loin" in ailleurs


def lignes_panne(state):
    f = donnees()["ferme"]
    copies, supports, loin = bilan_321()
    out = [f" {_c(203)}{BOLD}🔥 " + t("ma.panne.titre") + RESET, "",
           "  " + t("ma.panne.bilan", copies=copies, supports=supports, loin=t("ma.oui") if loin else t("ma.non")), ""]
    if not loin:
        noter("panne", "rien au loin (perdu)")
        return out + [f" {_c(203)}✖ " + t("ma.panne.perdu") + RESET, "  " + t("ma.panne.refais")]
    # l'incendie touche tout le bâtiment : le poste (machines/) et le disque 2 ; la copie « loin » survit
    for rel in ("machines/" + f["collection"], "machines/" + f["archive"], "machines/ferme/disque_2/" + f["archive"]):
        if (core.TERRAIN / rel).exists():
            _ecrire(rel, t("ma.panne.cendres") + "\n")
    noter("panne", f"{copies}-{supports}-1 (ok)")
    return out + [f"  {_c(203)}🔥 " + t("ma.panne.brule") + RESET, f" {_c(78)}✔ " + t("ma.panne.sauvee") + RESET,
                  "  " + t("ma.panne.suite")]


def _montage_lignes(choix, besoin, r):
    out = []
    for cat in donnees()["categories"]:
        x = next((piece(p)[1] for p in choix if piece(p)[0] == cat), None)
        out.append(f"  {t('ma.cat.' + cat):<18} " + (f"{BOLD}{x['id']}{RESET} " + texte_piece(cat, x) if x else DIM + "—" + RESET))
    b = donnees()["besoins"][besoin]
    if besoin != "ecole":                       # le besoin rappelé à chaque montage (on le relit quand ça ne démarre pas)
        out.insert(0, "  " + t("ma.monte.besoin", besoin=t("ma.besoin." + besoin)))
    out += ["", "  " + t("ma.monte.totaux", points=r["points"], budget=b["budget"] if b["budget"] < 99 else "∞",
                         watts=r["watts"], fournit=r["fournit"])]
    return out


def texte_piece(cat, x):
    if cat == "processeur":
        return t("ma.p.processeur", coeurs=x["coeurs"], prise=x["prise"], w=x["watts"], pts=x["points"])
    if cat == "carte_mere":
        return t("ma.p.carte_mere" + ("_mini" if x.get("mini") else ""), prise=x["prise"], type=x["type"], w=x["watts"],
                 pts=x["points"])
    if cat == "memoire":
        return t("ma.p.memoire", gio=x["gio"], type=x["type"], w=x["watts"], pts=x["points"])
    if cat == "stockage":
        return t("ma.p.ssd" if x["ssd"] else "ma.p.disque", go=_fr(x["go"], 0), w=x["watts"], pts=x["points"])
    if cat == "graphique":
        return t("ma.p.sans_graphique") if x.get("aucune") else t("ma.p.graphique", w=x["watts"], pts=x["points"])
    return t("ma.p.alimentation", w=x["fournit"], pts=x["points"])


def lignes_catalogue(besoin):
    b = donnees()["besoins"][besoin]
    out = [f" {_c(215)}{BOLD}🔧 " + t("ma.monte.titre") + RESET, "",
           "  " + t("ma.monte.besoin", besoin=t("ma.besoin." + besoin)),
           "  " + t("ma.monte.budget", budget=b["budget"]) if b["budget"] < 99 else "  " + t("ma.monte.sans_budget"), ""]
    for cat in donnees()["categories"]:
        out.append(f"  {BOLD}{t('ma.cat.' + cat)}{RESET}")
        for x in donnees()["catalogue"][cat]:
            out.append(f"    {x['id']}  " + texte_piece(cat, x))
    out += ["", f"  {DIM}" + t("ma.monte.regles") + RESET, "  " + t("ma.monte.aide" + ("1" if besoin == "ecole" else ""))]
    return out


def lignes_probleme(pb):
    out = []
    for p in pb:
        k, _s, v = p.partition(":")
        if k in ("manque", "double"):
            out.append(f"  {_c(203)}✖{RESET} " + t("ma.pb." + k, cat=t("ma.cat." + v)))
        elif k == "inconnu":
            out.append(f"  {_c(203)}✖{RESET} " + t("ma.pb.inconnu", id=v))
        else:
            out.append(f"  {_c(203)}✖{RESET} " + t("ma.pb." + p.replace(":", "_")))
    return out


def lignes_monte(state, args):
    c = c_(state)
    niveau1 = bool(args) and args[0] == "1"
    choix = args[1:] if niveau1 else list(args)
    besoin = "ecole" if niveau1 else besoin_epreuve(_graine(state))
    if not choix:
        if not niveau1 and "chrono" not in c:
            c["chrono"] = int(time.time())
        return lignes_catalogue(besoin)
    r = montage(choix, besoin)
    out = [f" {_c(215)}{BOLD}🔧 " + t("ma.monte.machine") + RESET, ""] + _montage_lignes(choix, besoin, r) + [""]
    if niveau1:                               # niveau 1 : on assemble et on démarre tout de suite
        if r["problemes"]:
            noter("monte1", " ".join(x.upper() for x in choix) + " (faux)")
            return out + lignes_probleme(r["problemes"]) + ["", "  " + t("ma.monte.reessaie")]
        noter("monte1", " ".join(x.upper() for x in choix) + " (ok)")
        return out + [f"  {_c(78)}⚡ " + t("ma.demarre.ok") + RESET, "  " + t("ma.monte.niveau1_ok")]
    c["choix"] = [x.upper() for x in choix]
    noter("monte", " ".join(c["choix"]) + " (ok)")
    return out + ["  " + t("ma.monte.pret")]


def lignes_demarre(state):
    c = c_(state)
    choix = c.get("choix")
    if not choix:
        return [t("ma.demarre.rien")]
    besoin = besoin_epreuve(_graine(state))
    r = montage(choix, besoin)
    c["demarrages"] = c.get("demarrages", 0) + 1
    out = [f" {_c(215)}{BOLD}🔌 " + t("ma.demarre.titre") + RESET, ""] + _montage_lignes(choix, besoin, r) + [""]
    if r["problemes"]:
        noter("demarre", " ".join(choix) + " (faux)")
        return out + [f"  {_c(203)}💥 " + t("ma.demarre.rate") + RESET] + lignes_probleme(r["problemes"]) + \
            ["", "  " + t("ma.monte.reessaie")]
    noter("demarre", " ".join(choix) + " (ok)")
    out += dessin_ordinateur(donnees()["pieces"]) + ["", f"  {_c(78)}⚡ " + t("ma.demarre.ok") + RESET]
    if "chrono" in c:
        s = max(0, int(time.time()) - c["chrono"])
        out.append("  ⏱ " + t("ma.demarre.chrono", m=s // 60, s=s % 60))
    out.append(f"  {_c(229)}🚩 {drapeau(_graine(state))}{RESET}   " + t("ma.demarre.drapeau"))
    if c["demarrages"] == 1 and not _fait(c, "premier_demarrage"):
        from . import recompenses
        msg = recompenses.exploit(state, "machines.premier_demarrage")
        if msg:
            core.log(state, msg)
            core.say(state, msg, 16)
            out.append(f"  {_c(213)}✨ " + msg + RESET)
    return out


def lignes_drapeau(state, arg):
    if not arg:
        return [t("ma.drapeau.aide")]
    if arg.strip() == drapeau(_graine(state)):
        noter("drapeau", "TG (ok)")
        return [f" {_c(78)}🚩 " + t("ma.drapeau.ok") + RESET]
    noter("drapeau", "faux (faux)")
    return [f" {_c(203)}✖ " + t("ma.drapeau.faux") + RESET]


SALLE = ['   ⚙  ╔════════════════════════════╗  ⚙', '      ║ ▓▓▓  ║║║║  ▤▤▤   ≋≋≋≋  ║', '  ═══╣ ▓▓▓  ║║║║  ▤▤▤   ≋≋≋≋  ╠═══',
         '      ║  ○────○────○────○────○  ║', '   ⚙  ╚════════╦══════╦════════╝  ⚙', '      ░░░░░░░░░║ 0101 ║░░░░░░░░░']


def banniere(largeur=None):
    """L'entrée de la Salle : l'illustration B9 si elle existe (illustrations.bin, « machines »), sinon le REPLI dessiné
    en caractères (la salle sous le camp, le processeur, la mémoire, les disques, les tuyaux)."""
    try:
        from . import scenes
        if scenes.disponible("machines"):
            return scenes.illustration("machines", largeur or 60, 24)
    except Exception:                                    # noqa: BLE001
        pass
    return [f"  {_c(215)}{l}{RESET}" for l in SALLE]


def aide():
    return banniere() + [f" {_c(215)}{BOLD}⚙ " + t("ma.aide.titre") + RESET] + ["  " + l for l in t("ma.aide.liste").split("\n")]


def commande(args, sortie=None):
    """tg machines [plan|ouvre|coeurs N|memoire N|interrupteurs MOT|allume BITS|unites|reveil …|orchestre …|licences|
    boite|range …|adulte|conteneur|vm|ferme|energie|panne|monte [1] …|demarre|drapeau TG{…}]."""
    out = sortie if sortie is not None else sys.stdout
    a = list(args)
    sous = ascii_bas((a[0] if a else "aide").lower()).replace("œ", "oe")
    reste = [x for x in a[1:] if x not in ("?", "…")]
    lignes = []

    def f(st):
        c_(st)
        arg = reste[0] if reste else None
        if sous in ("plan", "regle"):
            lignes.extend(banniere() + t("ma.meuble.plan", nom=st.get("name", "")).split("\n"))
        elif sous == "ouvre":
            lignes.extend(lignes_ouvre(st))
        elif sous in ("coeurs", "coeur"):
            lignes.extend(lignes_coeurs(arg))
        elif sous == "memoire":
            lignes.extend(lignes_memoire(" ".join(reste) if reste else None))
        elif sous == "interrupteurs":
            lignes.extend(lignes_interrupteurs(st, " ".join(reste) if reste else None))
        elif sous == "allume":
            lignes.extend(lignes_allume(st, "".join(reste) if reste else None))
        elif sous in ("unites", "unite"):
            lignes.extend(lignes_unites(arg))
        elif sous == "reveil":
            lignes.extend(lignes_reveil(st, reste))
        elif sous == "orchestre":
            lignes.extend(lignes_orchestre(st, reste))
        elif sous in ("licences", "licence"):
            lignes.extend(lignes_licences())
        elif sous == "boite":
            lignes.extend(lignes_boite())
        elif sous == "range":
            lignes.extend(lignes_range(st, reste))
        elif sous == "adulte":
            lignes.extend(lignes_adulte())
        elif sous == "conteneur":
            lignes.extend(lignes_conteneur(st))
        elif sous == "vm":
            lignes.extend(lignes_vm())
        elif sous == "ferme":
            lignes.extend(lignes_ferme())
        elif sous == "energie":
            lignes.extend(lignes_energie())
        elif sous == "panne":
            lignes.extend(lignes_panne(st))
        elif sous == "monte":
            lignes.extend(lignes_monte(st, reste))
        elif sous == "demarre":
            lignes.extend(lignes_demarre(st))
        elif sous == "drapeau":
            lignes.extend(lignes_drapeau(st, arg))
        else:
            lignes.extend(aide())
    if core.modifier(f) is None:
        f({})
    out.write("\n".join(lignes) + RESET + "\n")
