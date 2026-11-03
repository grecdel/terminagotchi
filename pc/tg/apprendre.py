"""Apprendre en jouant (idées cochées du 3 novembre, maquettes validées : /home/claude/outils/ameliorations/apprendre_jouer).

Un seul module pour les 14 idées, chacune petite et jamais punitive (rien ne se perd, aucun minuteur imposé) :
  27 le bac à sable      `tg bac-a-sable [neuf]` : ~/terrain_terminagotchi/bac_a_sable/, rien n'y compte (ni leçon, ni XP,
                         ni faim, ni défi, ni rencontre) ; une commande jamais tapée y devient « découverte » (sans XP).
  46 les rares            `tg collection rares [2]` : légendaires, mythique, shiny ; ce qui manque est une silhouette.
  43 la maîtrise          trois ronds par commande (découverte, avec une option, 5 réussites sans aide) ; titre « Main sûre ».
  24 les révisions        au plus une invitation par jour (1, 3, 7, 14, 30 jours) ; `tg souvenirs`.
  29 la commande du jour  `tg jour` : la même graine pour tous (la date), +8 XP et un tampon, aucun « jours de suite ».
  44 les énigmes          `tg enigme [reponse <mot> | indice]` : une par semaine, fabriquée par la graine de la semaine.
  23 les mini-énigmes     après une erreur connue (5 cas, devinés en regardant le terrain), deux indices, +3 XP.
  21 le dictionnaire      `tg carnet [page]` : une image 16 × 16 dessinée en code par commande (apprendre.json « pictos »).
  41 les mini-jeux        `tg jeux [nom | reponse N]` : labyrinthe, taupes, pêche, facteur (dans le terrain).
  42 la course            `tg course oui|non`, `tg course eclairs oui|non` : chrono et « fantôme » seulement si on veut.
  49 le temps doux        `tg parent temps <minutes>|non` (confirmation adulte) : elle bâille puis s'endort jusqu'à 7 h.
  45 le sentier           `tg sommet sentier` : le sentier des marmottes, ouvert dès un monde au palier 3.
  30 l'examen             `tg examen` : 5 salles à la fin d'un chapitre, puis un diplôme PNG (sans prénom tapé).
Les mêmes règles sur Android (Apprendre.kt) ; vecteurs communs donnees/apprendre/vecteurs.json (test_apprendre.py).
Rien n'est envoyé : tout reste dans la sauvegarde et dans le terrain.
"""
import datetime
import json
import os
import pkgutil
import re
import shutil
import struct
import time
import zlib
from pathlib import Path

from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, fg

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads(pkgutil.get_data(__package__, "apprendre.json").decode("utf-8"))
    return _D


def cmds():
    return donnees()["cmds"]


# ================================================================ la spécification pure (vecteurs communs, Kotlin)
def fnv(texte):
    """FNV-1a 32 bits des octets UTF-8 (la graine du jour, de la semaine : la même pour tous, sans réseau)."""
    h = 0x811C9DC5
    for o in texte.encode("utf-8"):
        h = ((h ^ o) * 0x01000193) & 0xFFFFFFFF
    return h


def jours_entre(a, b):
    """Le nombre de jours de la date a (AAAA-MM-JJ) à la date b."""
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return 0


def intervalle(etape):
    iv = donnees()["revision"]["intervalles"]
    return iv[max(0, min(int(etape), len(iv) - 1))]


def revision_due(vus, jour):
    """La commande à rafraîchir aujourd'hui (la plus en retard sur son intervalle ; à égalité, l'ordre du carnet),
    ou None. vus : {commande: [dernier jour, étape]}."""
    best, bv = None, None
    for c in cmds():
        v = vus.get(c)
        if not v:
            continue
        retard = jours_entre(v[0], jour) - intervalle(v[1])
        if retard >= 0 and (bv is None or retard > bv):
            best, bv = c, retard
    return best


def commande_du_jour(jour, connues):
    """La commande du jour : parmi celles déjà connues et la toute prochaine à découvrir (graine = la date)."""
    pool = [c for c in cmds() if c in connues]
    prochaine = next((c for c in cmds() if c not in connues), None)
    if prochaine:
        pool.append(prochaine)
    return pool[fnv(jour) % len(pool)] if pool else cmds()[0]


def niveau_maitrise(m, vue):
    """0 à 3 ronds : découverte, avec une option, maîtrisée (5 réussites sans aide). m = [option, réussites, maîtrisée]."""
    m = m or [0, 0, 0]
    if m[2]:
        return 3
    if not vue:
        return 0
    return 2 if m[0] else 1


def enigme(semaine, connues):
    """(modèle, mot, nombre) de l'énigme de la semaine « 2026-W45 » : même graine pour tous ; le modèle suit les
    commandes connues (ls est toujours permis)."""
    e = donnees()["enigmes"]
    mods = [m["id"] for m in e["modeles"] if m["besoin"] == "ls" or m["besoin"] in connues]
    mod = mods[fnv(semaine) % len(mods)]
    mot = e["mots"][fnv(semaine + ":mot") % len(e["mots"])]
    return mod, mot, 3 + fnv(semaine + ":n") % 5


def etat_temps(secondes, limite, baille=5, pause=60):
    """« eveil », « baille » (bientôt l'heure), « dort » (la limite est atteinte) ou « pause » (sans limite : une heure
    de jeu, une seule proposition)."""
    m = secondes / 60.0
    if limite:
        if m >= limite:
            return "dort"
        if m >= limite - baille:
            return "baille"
        return "eveil"
    return "pause" if m >= pause else "eveil"


def ajouter_temps(etat, now, trou=300):
    """Le temps de jeu du jour : entre deux commandes rapprochées (moins de trou secondes), le temps compte."""
    jour = jour_de(now)
    if etat.get("jour") != jour:
        etat.update(jour=jour, s=0, t=now, baille=False)
        return etat
    dt = now - float(etat.get("t") or now)
    if 0 < dt <= trou:
        etat["s"] = float(etat.get("s", 0)) + dt
    etat["t"] = now
    return etat


def jour_de(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def prochain_reveil(ts, heure=7):
    """L'instant du prochain réveil (7 h, heure locale) après ts."""
    d = datetime.datetime.fromtimestamp(ts)
    r = d.replace(hour=heure, minute=0, second=0, microsecond=0)
    if r <= d:
        r += datetime.timedelta(days=1)
    return r.timestamp()


def semaine(ts=None):
    from . import entrainement
    return entrainement.semaine(ts)


# ================================================================ l'état (state["apprendre"])
def a_(state):
    a = state.get("apprendre")
    if not isinstance(a, dict):
        a = state["apprendre"] = {}
    for k, v in {"vus": {}, "rev": {}, "maitrise": {}, "tampons": [], "enigmes": [], "eindices": {}, "erreur": None,
                 "erreur_t": 0, "jeux": {}, "course": False, "eclairs": True, "temps": {}, "bac_ici": False,
                 "sentier": [], "examen": {}, "diplomes": []}.items():
        if k not in a:
            a[k] = json.loads(json.dumps(v))
    return a


def terrain():
    return core.TERRAIN


def dans(chemin, dossier):
    """chemin est dossier ou dedans (comparaison des chemins résolus)."""
    if not chemin:
        return False
    try:
        p, d = Path(chemin).resolve(), Path(dossier).resolve()
    except OSError:
        return False
    return p == d or d in p.parents


def info(state, texte):
    """Une ligne à montrer dans le terminal sous la commande, qui n'est PAS une erreur (compagnon.annonces)."""
    f = state.setdefault("terminal_info", [])
    if texte and texte not in f:
        f.append(texte)
        del f[:-6]


def dire(state, texte, secs=10):
    core.say(state, texte, secs)
    info(state, texte)


def _ecrire(p, contenu):
    """Écrit un fichier du jeu dans le terrain, jamais à travers un lien (sur.py)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink():
        return
    p.write_text(contenu, encoding="utf-8")


def _vider(d):
    """Efface un dossier du jeu DANS le terrain (jamais un lien, jamais ailleurs)."""
    if d.is_symlink() or not dans(d, terrain()) or Path(d).resolve() == terrain().resolve():
        return False
    if d.exists():
        shutil.rmtree(d)
    return True


def core_cmd(x):
    return "tg " + x


def mots_de(ligne):
    return (ligne or "").strip().split()


def premier(ligne):
    return core.first_word(ligne or "") or ""


# ================================================================ 27. le bac à sable
def dossier_bac():
    return terrain() / donnees()["bac"]["dossier"]


def preparer_bac(neuf=False):
    d = dossier_bac()
    if neuf:
        _vider(d)
    d.mkdir(parents=True, exist_ok=True)
    for rel, cle in donnees()["bac"]["jouets"].items():
        p = d / rel
        if rel.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        elif not p.exists():
            _ecrire(p, t(cle, cmd=core_cmd("bac-a-sable neuf")) + "\n")
    return d


def commande_bac(state, args):
    neuf = bool(args) and args[0].lower() in ("neuf", "new", "reset")
    d = preparer_bac(neuf)
    rel = "~/" + str(d.relative_to(Path.home())) if dans(d, Path.home()) else str(d)
    out = [f"{fg(221)}{BOLD}🏖 " + t("apr.bac.titre", nom=state.get("name", "")) + RESET,
           "  " + t("apr.bac.regle"),
           "  " + t("apr.bac.aller", cmd=f"cd {rel}")]
    out.append("  " + (t("apr.bac.neuf_ok") if neuf else t("apr.bac.neuf", cmd="tg bac-a-sable neuf")))
    return out


def en_pause(state, cwd):
    """Vrai si le tour ne compte rien : le bac à sable (cwd dedans) ou elle dort (limite de temps douce)."""
    a = a_(state)
    bac = dans(cwd, dossier_bac())
    if bac and not a["bac_ici"]:
        info(state, "🏖 " + t("apr.bac.bandeau"))
    a["bac_ici"] = bac
    tp = a["temps"]
    if tp.get("dort") and not endormie(state):          # 7 h : elle se réveille, rien n'est perdu
        tp["dort"] = 0
        dire(state, "☀ " + t("apr.temps.reveil", nom=state.get("name", "")), 10)
        core.animer(state, "content")
    return bac or endormie(state)


def tour_pause(state, lines):
    """Le tour pendant le bac à sable ou le sommeil : une commande jamais tapée devient « découverte », rien d'autre."""
    for line in lines:
        if core.est_colle(line):
            continue
        c = premier(line)
        connue = c in cmds() or any(c in v["cmds"] for v in core.CATEGORIES.values())
        if c and connue and c not in state["seen"]:
            state["seen"].append(c)
        if endormie(state) and not a_(state)["bac_ici"]:
            core.animer(state, "dort")
            info(state, "💤 " + t("apr.temps.chut", nom=state.get("name", "")))


# ================================================================ 46. le tableau des rares
def _ombre(e, echelle=2):
    """La silhouette d'une bestiole pas encore rencontrée (gris), en demi-blocs."""
    from . import bestiaire as B
    img = B.image(e)
    if not img:
        return [f"{fg(238)}  ???{RESET}"]
    w, h, octets, pal = img
    return B.lignes_image(*_reduire(w, h, octets, echelle), ["#3a3a4c"] * len(pal))


def _reduire(w, h, octets, k):
    if k <= 1:
        return w, h, octets
    w2, h2 = w // k, h // k
    out = bytearray(w2 * h2)
    for y in range(h2):
        for x in range(w2):
            v = 0
            for dy in range(k):
                for dx in range(k):
                    v = v or octets[(y * k + dy) * w + x * k + dx]
            out[y * w2 + x] = v
    return w2, h2, bytes(out)


def _dessin(e, shiny=False, teinte=0.5, echelle=2):
    from . import bestiaire as B
    img = B.image(e)
    if not img:
        return B.dessin(e, shiny)
    w, h, octets, pal = img
    if shiny:
        pal = [B.decaler(c, teinte) for c in pal]
    return B.lignes_image(*_reduire(w, h, octets, echelle), pal)


def indice_rare(e):
    """« attirée par `ping` », ou « se montre très rarement » quand la commande n'est pas enseignée (sudo)."""
    c = e.get("attiree_par", "")
    if c in ("sudo", "su", "doas", "") or c not in set(cmds()) | {"ps", "df", "free", "ping", "git", "rev"}:
        return t("apr.rares.tres_rarement")
    return t("apr.rares.attiree", cmd=c)


def rares(page=1):
    """Les espèces du tableau : page 1 les légendaires et le mythique, page 2 les rares."""
    from . import bestiaire as B
    r = ("légendaire", "mythique") if page == 1 else ("rare",)
    return [e for e in B.especes() if e.get("rarete") in r and (not e.get("secrete") or e.get("rarete") == "mythique")]


def ecran_rares(state, args):
    from . import bestiaire as B
    import shutil as _sh
    page = 2 if args and args[0] in ("2", "rares", "rare") else 1
    liste = rares(page)
    vues = {n for n, k in state.get("collection", {}).items() if k}
    vues_id = {(B.espece(n) or {}).get("id") for n in vues}
    caps = state.get("captures", [])
    n_ok = sum(1 for e in liste if e["id"] in vues_id or e["nom"] in vues)
    shinies = [c for c in caps if c.get("shiny")]
    out = [f" {fg(213)}── ✨ " + t("apr.rares.titre" if page == 1 else "apr.rares.titre2", nom=state.get("name", ""))
           + f"  {BOLD}{n_ok} / {len(liste)}{RESET}{fg(213)}   shiny : {len(shinies)} ──{RESET}", ""]
    larg = 26
    par = max(1, min(4, (_sh.get_terminal_size((100, 30)).columns - 1) // larg))
    cases = []
    for e in liste:
        ok = e["id"] in vues_id or e["nom"] in vues
        img = _dessin(e) if ok else _ombre(e)
        legende = (f"{fg(255)}{BOLD}{e['nom']}{RESET}", f"{fg(244)}{B.nom_rarete(e['rarete'])} · " + t("apr.rares.dressee") + RESET) \
            if ok else (f"{fg(244)}???{RESET}", f"{DIM}{indice_rare(e)}{RESET}")
        cases.append(img + list(legende))
    for i in range(0, len(cases), par):
        rang = cases[i:i + par]
        haut = max(len(c) for c in rang)
        for y in range(haut):
            ligne = ""
            for c in rang:
                s = c[y] if y < len(c) else ""
                ligne += " " + s + " " * max(0, larg - _largeur(s))
            out.append(ligne.rstrip())
        out.append("")
    if page == 1 and shinies:
        out.append(f" {fg(213)}" + t("apr.rares.shiny", n=len(shinies)) + RESET)
        for c in shinies[-4:]:
            e = B.espece(c.get("espece", ""))
            if e:
                out += ["  " + x for x in _dessin(e, True, c.get("teinte", 0.5), 3)]
    out.append(f" {DIM}" + t("apr.rares.pied", cmd="tg collection rares 2" if page == 1 else "tg collection rares") + RESET)
    return out


_ANSI = re.compile(r"\033\[[0-9;]*m")


def _largeur(s):
    import unicodedata
    s = _ANSI.sub("", s)
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 0 if unicodedata.combining(c) else 1 for c in s)


# ================================================================ 43. la maîtrise
def noter_usage(state, ligne, statut, aide=False):
    """Une commande tapée (et réussie, ou au code inconnu) : la maîtrise et les révisions (dernier usage)."""
    a = a_(state)
    c = premier(ligne)
    if c not in cmds() or statut not in (None, 0):
        return None
    m = a["maitrise"].setdefault(c, [0, 0, 0])
    if any(x.startswith("-") and len(x) > 1 and x != "--" for x in mots_de(ligne)[1:]):
        m[0] = 1
    msg = None
    if not aide:
        m[1] += 1
        if m[1] >= donnees()["maitrise"]["reussites"] and not m[2]:
            m[2] = 1
            msg = "🏅 " + t("apr.maitrise.or", cmd=c)
            core.log(state, msg)
            if nb_maitrisees(state) == donnees()["maitrise"]["titre"]:
                msg += " " + t("apr.maitrise.titre", titre=t("apr.titre.main_sure"))
    return msg


def nb_maitrisees(state):
    return sum(1 for m in a_(state)["maitrise"].values() if m and m[2])


def ronds(state, c):
    n = niveau_maitrise(a_(state)["maitrise"].get(c), c in state.get("seen", []))
    if n == 3:
        return f"{fg(220)}●●◉{RESET}"
    return f"{fg(78)}" + "●" * n + f"{fg(240)}" + "○" * (3 - n) + RESET


def lignes_maitrise(state):
    out = [f" {fg(213)}── 🏅 " + t("apr.maitrise.titre_ecran") + f" ──{RESET}",
           "  " + "   ".join(f"{c} {ronds(state, c)}" for c in cmds()[:10]),
           "  " + "   ".join(f"{c} {ronds(state, c)}" for c in cmds()[10:]),
           f"  {DIM}" + t("apr.maitrise.legende", n=donnees()["maitrise"]["reussites"]) + RESET]
    return out


# ================================================================ 24. les révisions
def noter_vu(state, c, now):
    a = a_(state)
    if c not in cmds():
        return None
    jour = jour_de(now)
    v = a["vus"].get(c)
    r = a["rev"]
    msg = None
    if r.get("jour") == jour and r.get("cmd") == c and not r.get("fait"):
        r["fait"] = True
        etape = (v[1] if v else 0) + 1
        a["vus"][c] = [jour, etape]
        xp = donnees()["revision"]["xp"]
        core.add_xp(state, xp)
        msg = "🍃 " + t("apr.rev.fait", xp=xp, n=intervalle(etape))
        core.log(state, msg)
        return msg
    a["vus"][c] = [jour, v[1] if v else 0]
    return msg


def inviter_revision(state, now):
    """Au plus une invitation par jour, seulement dans la bulle, pendant qu'on joue déjà."""
    a = a_(state)
    jour = jour_de(now)
    if a["rev"].get("jour") == jour:
        return
    c = revision_due(a["vus"], jour)
    if not c:
        return
    from . import histoire
    if histoire.en_pleine_etape(state):
        return
    a["rev"] = {"jour": jour, "cmd": c, "fait": False}
    core.say(state, t("apr.rev.invite", cmd=c, xp=donnees()["revision"]["xp"]), 14)


def lignes_souvenirs(state):
    a = a_(state)
    jour = jour_de(time.time())
    out = [f" {fg(150)}── 🍃 " + t("apr.rev.titre") + f"  {DIM}" + t("apr.rev.sous_titre") + RESET]
    liste = sorted(((jours_entre(v[0], jour) - intervalle(v[1]), c, v) for c, v in a["vus"].items() if c in cmds()),
                   key=lambda x: -x[0])
    if not liste:
        out.append("  " + t("apr.rev.rien"))
    for retard, c, v in liste[:8]:
        n = jours_entre(v[0], jour)
        quand = t("apr.rev.aujourdhui") if n <= 0 else t("apr.rev.il_y_a", n=n)
        image = t(f"lex.{c}.i", opt="ls -a").split(" (")[0]
        etat = f"{fg(150)}" + t("apr.rev.a_rafraichir") + RESET if retard >= 0 else f"{DIM}" + t("apr.rev.prochain", n=max(1, -retard)) + RESET
        out.append(f"  {fg(150)}🍂{RESET} {BOLD}{c:<7}{RESET} {quand:<18} {image}   {etat}")
    out.append(f"  {DIM}" + t("apr.rev.pied") + RESET)
    return out


# ================================================================ 29. la commande du jour
def mission_du_jour(state, now=None):
    jour = jour_de(now or time.time())
    c = commande_du_jour(jour, set(state.get("seen", [])))
    return jour, c


def verifier_jour(state, ligne, statut, now):
    if statut not in (None, 0):
        return None
    a = a_(state)
    jour, c = mission_du_jour(state, now)
    if jour in a["tampons"]:
        return None
    motif = donnees()["jour"]["missions"].get(c)
    if motif and re.search(motif, (ligne or "").strip()):
        a["tampons"] = (a["tampons"] + [jour])[-62:]
        xp = donnees()["jour"]["xp"]
        core.add_xp(state, xp)
        msg = "☀ " + t("apr.jour.fait", cmd=c, xp=xp)
        core.log(state, msg)
        core.animer(state, "content")
        return msg
    return None


def ecran_jour(state):
    a = a_(state)
    jour, c = mission_du_jour(state)
    ex = donnees()["jour"]["exemples"][c]
    fait = jour in a["tampons"]
    d = datetime.date.fromisoformat(jour)
    out = [f"{fg(221)}┌─ ☀ " + t("apr.jour.titre", date=d.strftime("%d/%m")) + RESET,
           f"{fg(221)}│{RESET} " + t("apr.jour.mission", cmd=f"`{ex}`"),
           f"{fg(221)}│{RESET} {DIM}" + t("apr.jour.regle") + RESET,
           f"{fg(221)}│{RESET} " + (f"{fg(78)}✓ " + t("apr.jour.deja") + RESET if fait else t("apr.jour.recompense", xp=donnees()["jour"]["xp"])),
           f"{fg(221)}└──{RESET}"]
    out += calendrier(a["tampons"], d)
    return out


def calendrier(tampons, d):
    """Le mois en cours : ☀ les jours tamponnés, rien les autres (aucun total de « jours de suite »)."""
    import calendar
    mois = t("apr.mois." + str(d.month))
    out = [f" {fg(221)}" + t("apr.jour.tampons", mois=mois, annee=d.year) + RESET]
    sem = calendar.Calendar().monthdayscalendar(d.year, d.month)
    for w in sem:
        cases = []
        for j in w:
            if not j:
                cases.append("   ")
                continue
            k = f"{d.year:04d}-{d.month:02d}-{j:02d}"
            cases.append(f"{fg(221)} ☀ {RESET}" if k in tampons else f"{DIM}{j:>3}{RESET}")
        out.append("  " + "".join(cases))
    return out


# ================================================================ 44. les énigmes de la semaine
def dossier_enigme(sem):
    return terrain() / "enigmes" / ("semaine_" + sem.split("-W")[-1])


def preparer_enigme(state, sem):
    mod, mot, n = enigme(sem, set(state.get("seen", [])))
    d = dossier_enigme(sem)
    if not (d / "lis-moi.txt").exists():
        d.mkdir(parents=True, exist_ok=True)
        _ecrire(d / "lis-moi.txt", t("apr.enigme." + mod + ".texte", n=n) + "\n")
        noms = "abcdefg"
        if mod == "phare":
            vrai = fnv(sem + ":vrai") % n
            for k in range(n):
                _ecrire(d / f"parchemin_{noms[k]}.txt", (t("apr.enigme.phare.vrai", mot=mot) if k == vrai
                                                         else t("apr.enigme.phare.faux")) + "\n")
        elif mod == "cache":
            for k in range(n):
                _ecrire(d / f"caillou_{k + 1}.txt", t("apr.enigme.cache.caillou") + "\n")
            _ecrire(d / ".secret.txt", t("apr.enigme.cache.secret", mot=mot) + "\n")
        elif mod == "profond":
            p = d
            for k in range(n):
                p = p / f"salle_{k + 1}"
                p.mkdir(parents=True, exist_ok=True)
                _ecrire(p / "rien.txt", t("apr.enigme.profond.rien") + "\n")
            _ecrire(p / "coffre.txt", t("apr.enigme.profond.coffre", mot=mot) + "\n")
        elif mod == "ordre":
            autres = [m for m in donnees()["enigmes"]["mots"] if m > mot][:n] or ["zebre"]
            lignes = autres + [mot]
            lignes.sort(key=lambda x: fnv(sem + x))
            _ecrire(d / "mots.txt", "\n".join(lignes) + "\n")
        elif mod == "compte":
            for k in range(n):
                _ecrire(d / "cailloux" / f"galet_{k + 1}.txt", "·\n")
    garder = donnees()["enigmes"]["garder"]
    base = terrain() / "enigmes"
    if base.is_dir() and not base.is_symlink():      # les 4 dernières semaines seulement
        semaines = [semaine(time.time() - 7 * 86400 * k).split("-W")[-1] for k in range(garder)]
        for x in base.iterdir():
            if x.is_dir() and not x.is_symlink() and x.name.startswith("semaine_") and x.name[8:] not in semaines:
                _vider(x)
    return mod, mot, n, d


def reponse_enigme(sem, state):
    mod, mot, n = enigme(sem, set(state.get("seen", [])))
    return str(n) if mod == "compte" else mot


def _normal(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def commande_enigme(state, args):
    a = a_(state)
    sem = semaine()
    mod, mot, n, d = preparer_enigme(state, sem)
    rel = "~/" + str(d.relative_to(Path.home())) if dans(d, Path.home()) else str(d)
    num = sem.split("-W")[-1]
    if args and args[0].lower() in ("reponse", "réponse", "answer") and len(args) > 1:
        prop = _normal(" ".join(args[1:]))
        for k in range(donnees()["enigmes"]["garder"]):
            s = semaine(time.time() - 7 * 86400 * k)
            if s not in a["enigmes"] and _normal(reponse_enigme(s, state)) == prop:
                a["enigmes"] = (a["enigmes"] + [s])[-20:]
                xp = donnees()["enigmes"]["xp"]
                core.add_xp(state, xp)
                core.animer(state, "victoire")
                msg = "🎉 " + t("apr.enigme.bravo", xp=xp, n=s.split("-W")[-1])
                core.log(state, msg)
                return [msg]
        return ["🤔 " + t("apr.enigme.pas_encore")]
    if args and args[0].lower() in ("indice", "hint"):
        k = a["eindices"][sem] = min(2, a["eindices"].get(sem, 0) + 1)
        return ["💡 " + t(f"apr.enigme.{mod}.indice{k}", n=n)]
    out = [f"{fg(147)}{BOLD}🧩 " + t("apr.enigme.titre", n=num) + RESET,
           "  " + t("apr.enigme." + mod + ".texte", n=n),
           "  " + t("apr.enigme.aller", cmd=f"cd {rel}"),
           f"  {DIM}" + t("apr.enigme.repondre", cmd="tg enigme reponse …", indice="tg enigme indice") + RESET]
    if sem in a["enigmes"]:
        out.insert(1, f"  {fg(78)}✓ " + t("apr.enigme.resolue") + RESET)
    passees = [s.split("-W")[-1] for s in a["enigmes"][-4:]]
    if passees:
        out.append(f"  {DIM}" + t("apr.enigme.passees", liste=" · ".join("✓ " + p for p in passees)) + RESET)
    return out


# ================================================================ 23. les erreurs en mini-énigmes
def _arg(ligne, k=1):
    m = [x for x in mots_de(ligne)[1:] if not x.startswith("-")]
    return m[k - 1] if len(m) >= k else None


def cause_erreur(ligne, cwd):
    """(type, cible) d'une erreur connue, devinée en regardant le terrain (jamais en lisant le message d'erreur), ou None."""
    if not cwd:
        return None
    c = premier(ligne)
    ici = Path(cwd)
    a1 = _arg(ligne)
    if not a1 or any(ch in ligne for ch in "|;&<>*?$`"):
        return None
    p = ici / os.path.expanduser(a1)
    if c == "cd":
        return ("lieu", a1) if not p.exists() else None
    if c == "mkdir" and "-p" not in mots_de(ligne):
        return ("existe", a1) if p.exists() else None
    if c == "rm" and not any(x.startswith("-") and "r" in x.lower() for x in mots_de(ligne)[1:]):
        return ("rm_dossier", a1) if p.is_dir() else None
    if c in ("cat", "head", "less", "tail", "more"):
        if p.is_dir():
            return ("cat_dossier", a1)
        return ("introuvable", a1) if not p.exists() else None
    if c in ("cp", "mv"):
        return ("introuvable", a1) if not p.exists() else None
    return None


def resolu(e, ligne, statut):
    """L'énigme d'erreur est-elle résolue par cette commande réussie ?"""
    if statut not in (None, 0):
        return False
    c = premier(ligne)
    m = mots_de(ligne)
    typ = e["type"]
    if typ == "lieu":
        return c == "cd" or c == "mkdir"
    if typ == "existe":
        return (c == "mkdir" and e["cible"] not in m) or (c == "cd" and e["cible"].rstrip("/") in [x.rstrip("/") for x in m])
    if typ == "rm_dossier":
        return c == "rmdir" or (c == "rm" and any(x.startswith("-") and "r" in x.lower() for x in m[1:]))
    if typ == "cat_dossier":
        return c in ("ls", "cd") and e["cible"].rstrip("/") in [x.rstrip("/") for x in m]
    if typ == "introuvable":
        return c == e.get("cmd") or c in ("ls", "find")
    return False


def verifier_erreur(state, ligne, statut, cwd, now):
    a = a_(state)
    e = a.get("erreur")
    if e:
        if resolu(e, ligne, statut) and (premier(ligne) not in ("ls", "find") or e["type"] != "introuvable" or e["indice"] >= 2):
            a["erreur"] = None
            xp = donnees()["erreurs"]["xp"]
            core.add_xp(state, xp)
            core.animer(state, "content")
            return "🧩 " + t("apr.err.resolue", xp=xp)
        if e["indice"] < 2:
            e["indice"] = 2
            return "💡 " + t(f"apr.err.{e['type']}.indice2", cible=e["cible"])
        return None
    if statut in (None, 0) or not dans(cwd, terrain()) or dans(cwd, dossier_bac()):
        return None
    if now - float(a.get("erreur_t") or 0) < donnees()["erreurs"]["delai"]:
        return None
    from . import histoire
    if histoire.en_pleine_etape(state):
        return None
    ce = cause_erreur(ligne, cwd)
    if not ce:
        return None
    a["erreur"] = {"type": ce[0], "cible": ce[1], "indice": 1, "cmd": premier(ligne)}
    a["erreur_t"] = now
    return ("🧩 " + t(f"apr.err.{ce[0]}", cible=ce[1]) + "\n   💡 " + t(f"apr.err.{ce[0]}.indice1", cible=ce[1])
            + f"\n   {DIM}" + t("apr.err.passe", cmd="tg passe") + RESET)


def passer(state):
    a_(state)["erreur"] = None
    return t("apr.err.passee")


# ================================================================ 21. le dictionnaire illustré
def picto(c, gris=False):
    """L'image 16 × 16 d'une commande en demi-blocs (8 lignes) ; gris : la silhouette d'une commande pas encore tapée."""
    from .bestiaire import bg24, fg24
    p = donnees()["pictos"]
    rows = p["images"].get(c)
    if not rows:
        return ["".ljust(16)] * 8
    pal = p["palette"]

    def coul(ch):
        if ch == ".":
            return None
        return "#3a3a4c" if gris else pal[ch]
    out = []
    for y in range(0, 16, 2):
        s = ""
        for x in range(16):
            ca, cb = coul(rows[y][x]), coul(rows[y + 1][x])
            if ca is None and cb is None:
                s += " "
            elif cb is None:
                s += fg24(ca) + "▀" + RESET
            elif ca is None:
                s += fg24(cb) + "▄" + RESET
            else:
                s += fg24(ca) + bg24(cb) + "▀" + RESET
        out.append(s)
    return out


def image_courte(c):
    return t(f"lex.{c}.i", opt="ls -a").split(" (")[0]


def ecran_carnet(state, args):
    import shutil as _sh
    liste = cmds()
    par_page = 6
    pages = (len(liste) + par_page - 1) // par_page
    try:
        page = max(1, min(pages, int(args[0]))) if args else 1
    except ValueError:
        page = 1
    vus = set(state.get("seen", []))
    out = [f" {fg(213)}── 📖 " + t("apr.carnet.titre", nom=state.get("name", ""), page=page, pages=pages) + f" ──{RESET}"]
    larg = 40
    par = max(1, min(3, (_sh.get_terminal_size((100, 30)).columns - 1) // larg))
    cases = []
    for c in liste[(page - 1) * par_page:page * par_page]:
        vu = c in vus
        img = picto(c, gris=not vu)
        texte = [f"{fg(255) if vu else fg(244)}{BOLD}{c}{RESET} {ronds(state, c)}",
                 (f"{fg(252)}" + image_courte(c) + RESET) if vu else f"{DIM}" + t("apr.carnet.a_decouvrir") + RESET]
        cases.append([img[k] + "  " + (texte[k - 3] if 3 <= k < 5 else "") for k in range(8)])
    for i in range(0, len(cases), par):
        rang = cases[i:i + par]
        for y in range(8):
            out.append(" " + "".join(c[y] + " " * max(0, larg - _largeur(c[y])) for c in rang).rstrip())
        out.append("")
    out.append(f" {DIM}" + t("apr.carnet.legende", cmd=f"tg carnet {page % pages + 1}", explique="tg explique cd") + RESET)
    return out


# ================================================================ 41 / 42. les mini-jeux et la course
def dossier_jeux():
    return terrain() / "jeux"


LABY = {"grotte": ["salle_humide", "salle_seche"], "grotte/salle_humide": ["impasse"],
        "grotte/salle_seche": ["tunnel", "eboulis"], "grotte/salle_seche/tunnel": ["salle_du_tresor"]}
LABY_TRESOR = "grotte/salle_seche/tunnel/salle_du_tresor"
FACTEUR = {"lettre_1.txt": "chateau", "lettre_2.txt": "moulin", "lettre_3.txt": "phare", "lettre_4.txt": "chateau"}


def preparer_jeu(nom):
    d = dossier_jeux() / nom
    _vider(d)
    d.mkdir(parents=True, exist_ok=True)
    if nom == "labyrinthe":
        for p, enfants in LABY.items():
            for e in enfants:
                (d / p / e).mkdir(parents=True, exist_ok=True)
        _ecrire(d / "grotte" / "salle_humide" / "impasse" / "note.txt", t("apr.jeux.laby.impasse") + "\n")
        _ecrire(d / LABY_TRESOR / "tresor.txt", t("apr.jeux.laby.tresor") + "\n")
        _ecrire(d / "grotte" / "salle_seche" / "eboulis" / "note.txt", t("apr.jeux.laby.eboulis") + "\n")
    elif nom == "taupes":
        for k in range(1, 6):
            _ecrire(d / f"taupe_{k}.txt", "( o.o )\n")
        for k in range(1, 4):
            _ecrire(d / f"fleur_{k}.txt", "✿\n")
    elif nom == "peche":
        for k in range(1, 4 + 1):
            _ecrire(d / f".poisson_{k}", "><(((º>\n")
        _ecrire(d / "algue.txt", "~\n")
        _ecrire(d / "bouee.txt", "o\n")
    elif nom == "facteur":
        for f, maison in FACTEUR.items():
            _ecrire(d / f, t("apr.jeux.facteur.pour", maison=maison) + "\n")
        for maison in sorted(set(FACTEUR.values())):
            (d / maison).mkdir(exist_ok=True)
    return d


def jeu_gagne(nom, cwd, ligne=""):
    d = dossier_jeux() / nom
    if nom == "labyrinthe":
        return dans(cwd, d / LABY_TRESOR) or bool(re.match(r"^cat\s+.*tresor\.txt", ligne.strip()) and dans(cwd, d))
    if nom == "taupes":
        return d.is_dir() and not list(d.glob("taupe_*")) and len(list(d.glob("fleur_*"))) == 3
    if nom == "facteur":
        return d.is_dir() and not list(d.glob("lettre_*")) and all((d / m / f).exists() for f, m in FACTEUR.items())
    return False


def carte_labyrinthe(state):
    """La carte qui se dessine : les salles déjà visitées (✓), la salle où l'on est (◆)."""
    j = a_(state)["jeux"]
    vues = set(j.get("vues", []))
    out = []
    for p in ["grotte"] + [f"{k}/{e}" for k, v in LABY.items() for e in v]:
        prof = p.count("/")
        nom = p.split("/")[-1]
        marque = "◆" if p == j.get("ici") else "✓" if p in vues else "·"
        coul = fg(221) if marque == "◆" else fg(78) if marque == "✓" else fg(240)
        out.append("   " + "  " * prof + f"{coul}{marque} {nom if marque != '·' else '???'}{RESET}")
    return out


def commande_jeux(state, args):
    a = a_(state)
    j = a["jeux"]
    noms = donnees()["jeux"]["ordre"]
    if not args:
        out = [f"{fg(147)}{BOLD}🎮 " + t("apr.jeux.titre") + RESET]
        for k, n in enumerate(noms, 1):
            rec = j.get("records", {}).get(n)
            out.append(f"  {k}. {BOLD}{t('apr.jeux.' + n + '.nom')}{RESET}  {DIM}" + t("apr.jeux." + n + ".court") + RESET
                       + (f"  {fg(147)}👻 {rec:.1f} s{RESET}" if rec and a["course"] else ""))
        out.append(f"  {DIM}" + t("apr.jeux.pied", cmd="tg jeux labyrinthe", course="tg course oui") + RESET)
        return out
    x = args[0].lower()
    if x in ("reponse", "réponse") and len(args) > 1:
        if j.get("actif") != "peche":
            return [t("apr.jeux.pas_de_peche")]
        if args[1].strip() == "4":
            return gagner(state, "peche")
        return ["🎣 " + t("apr.jeux.peche.encore")]
    if x == "carte":
        return [f"{fg(147)}🗺 " + t("apr.jeux.laby.nom") + RESET] + carte_labyrinthe(state)
    if x.isdigit() and 1 <= int(x) <= len(noms):
        x = noms[int(x) - 1]
    if x not in noms:
        return [t("apr.jeux.inconnu", liste=", ".join(noms))]
    d = preparer_jeu(x)
    j.update(actif=x, debut=time.time(), vues=[], ici=None)
    rel = "~/" + str(d.relative_to(Path.home())) if dans(d, Path.home()) else str(d)
    out = [f"{fg(147)}{BOLD}🎮 " + t("apr.jeux." + x + ".nom") + RESET,
           "  " + t("apr.jeux." + x + ".regle", cmd="tg jeux reponse 3"),
           "  " + t("apr.jeux.aller", cmd=f"cd {rel}")]
    if a["course"]:
        rec = j.get("records", {}).get(x)
        out.append(f"  {fg(147)}⏱ " + (t("apr.course.fantome", s=f"{rec:.1f}") if rec else t("apr.course.premier")) + RESET)
    return out


def gagner(state, nom, now=None):
    a = a_(state)
    j = a["jeux"]
    now = now or time.time()
    j["actif"] = None
    out = ["🎉 " + t("apr.jeux.gagne", jeu=t("apr.jeux." + nom + ".nom"))]
    jour = jour_de(now)
    xj = j.get("xp_jour") or ["", 0]
    if xj[0] != jour:
        xj = [jour, 0]
    if xj[1] < donnees()["jeux"]["plafond"]:
        xj[1] += 1
        xp = donnees()["jeux"]["xp"]
        core.add_xp(state, xp)
        out[0] += f" +{xp} XP"
    j["xp_jour"] = xj
    if a["course"] and j.get("debut"):
        dt = now - float(j["debut"])
        recs = j.setdefault("records", {})
        ancien = recs.get(nom)
        out.append("⏱ " + t("apr.course.temps", s=f"{dt:.1f}") + "   " + (
            ("👻 " + t("apr.course.bat", s=f"{ancien:.1f}")) if ancien and dt < ancien else
            ("👻 " + t("apr.course.fantome", s=f"{ancien:.1f}")) if ancien else t("apr.course.premier_temps")))
        recs[nom] = dt if ancien is None else min(ancien, dt)
    core.animer(state, "victoire")
    core.log(state, out[0])
    from . import envies
    envies.plaisir(state, "jeu", "defi")
    return out


def verifier_jeux(state, ligne, cwd, now):
    a = a_(state)
    j = a["jeux"]
    nom = j.get("actif")
    if not nom:
        return None
    if nom == "labyrinthe" and cwd and dans(cwd, dossier_jeux() / nom):
        rel = str(Path(cwd).resolve().relative_to((dossier_jeux() / nom).resolve()))
        if rel != ".":
            j["ici"] = rel
            if rel not in j.setdefault("vues", []):
                j["vues"].append(rel)
    if nom == "taupes" and (dossier_jeux() / nom).is_dir() and len(list((dossier_jeux() / nom).glob("fleur_*"))) < 3:
        return "🌸 " + t("apr.jeux.taupes.fleur", cmd="tg jeux taupes")
    if jeu_gagne(nom, cwd, ligne):
        return "\n".join(gagner(state, nom, now))
    return None


def commande_course(state, args):
    a = a_(state)
    if args and args[0].lower() in ("eclairs", "éclairs", "defis", "défis"):
        if len(args) > 1:
            a["eclairs"] = args[1].lower() in ("oui", "on", "yes")
        return [t("apr.course.eclairs." + ("on" if a["eclairs"] else "off"), cmd="tg course eclairs " + ("non" if a["eclairs"] else "oui"))]
    if args:
        a["course"] = args[0].lower() in ("oui", "on", "yes")
    return [f"{fg(147)}⏱ " + t("apr.course." + ("on" if a["course"] else "off")) + RESET,
            f"  {DIM}" + t("apr.course.regle") + RESET,
            "  " + t("apr.course.eclairs." + ("on" if a["eclairs"] else "off"), cmd="tg course eclairs " + ("non" if a["eclairs"] else "oui"))]


def eclairs(state):
    """Les défis éclair surprises sont-ils permis ? (interrupteur de l'idée 42, allumé au départ)"""
    return bool(a_(state).get("eclairs", True))


# ================================================================ 49. la limite de temps douce
def endormie(state, now=None):
    d = a_(state)["temps"].get("dort") or 0
    return (now or time.time()) < d


def secondes_endormies(state, t0, t1):
    """Les secondes de [t0, t1] pendant lesquelles elle dort (la faim ne baisse pas : comme en vacances)."""
    tp = a_(state)["temps"]
    d0, d1 = float(tp.get("dort_debut") or 0), float(tp.get("dort") or 0)
    return max(0.0, min(t1, d1) - max(t0, d0))


def regler_temps(state, args):
    a = a_(state)
    tp = a["temps"]
    if args and args[0].lower() in ("non", "off", "aucune", "none", "0"):
        tp["limite"] = None
        tp["dort"] = 0
        return t("apr.temps.enleve")
    try:
        m = int(args[0])
    except (ValueError, IndexError):
        lim = tp.get("limite")
        return t("apr.temps.actuel", n=lim) if lim else t("apr.temps.aucune", cmd="tg parent temps 45")
    m = max(10, min(600, m))
    tp["limite"] = m
    return "✓ " + t("apr.temps.ok", nom=state.get("name", ""), n=m, cmd="tg parent temps non")


def commande_parent(state_ou_none, args, demander=None):
    """tg parent temps <minutes>|non : demande la même confirmation qu'un adulte pour `tg debloquer`."""
    import sys
    if not args or args[0].lower() not in ("temps", "time"):
        return [t("apr.parent.aide", cmd="tg parent temps 45")]
    if len(args) > 1 and "--oui" not in sys.argv:
        q = t("apr.parent.question", n=args[1]) + " " + t("apr.parent.confirmer") + " "
        try:
            rep = (demander or input)(q)
        except (KeyboardInterrupt, EOFError):
            rep = ""
        if _normal(rep) != _normal(t("apr.parent.phrase")):
            return [t("apr.parent.non")]
    out = []
    core.modifier(lambda s: out.append(regler_temps(s, args[1:])))
    return out


def verifier_temps(state, now):
    a = a_(state)
    tp = a["temps"]
    ajouter_temps(tp, now, donnees()["temps"]["trou"])
    e = etat_temps(tp.get("s", 0), tp.get("limite"), donnees()["temps"]["baille"], donnees()["temps"]["pause"])
    nom = state.get("name", "")
    if e == "baille" and not tp.get("baille"):
        tp["baille"] = True
        core.animer(state, "dort")
        dire(state, "💤 " + t("apr.temps.baille", nom=nom), 12)
    elif e == "dort" and not endormie(state, now) and tp.get("dort_jour") != tp.get("jour"):
        tp["dort_jour"] = tp.get("jour")
        tp["dort_debut"] = now
        tp["dort"] = prochain_reveil(now, donnees()["temps"]["reveil"])
        core.animer(state, "dort")
        dire(state, "🌙 " + t("apr.temps.dort", nom=nom), 16)
    elif e == "pause" and tp.get("pause_dite") != tp.get("jour"):
        tp["pause_dite"] = tp.get("jour")
        dire(state, "☕ " + t("apr.temps.pause", nom=nom), 12)


# ================================================================ 45. le sentier des marmottes (au Sommet)
def sentier_ouvert(state):
    from . import sommet
    try:
        return len(sommet.mondes_au_palier(state, 3)) >= 1
    except Exception:                      # noqa: BLE001
        return False


def dossier_sentier():
    return terrain() / "sommet" / "sentier"


def preparer_sentier():
    d = dossier_sentier()
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "inscriptions.txt").exists():
        _ecrire(d / "inscriptions.txt", "\n".join(t("apr.sentier.inscription." + str(k)) for k in range(1, 6)) + "\n")
        _ecrire(d / "sommet.txt", t("apr.sentier.sommet_txt") + "\n")
        _ecrire(d / "panneau.txt", t("apr.sentier.panneau") + "\n")
        for k, n in enumerate(("gris", "rond", "plat"), 1):
            _ecrire(d / "eboulis" / f"{n}.caillou", "◍\n")
        _ecrire(d / "eboulis" / "touffe_d_herbe.txt", "\"\n")
    return d


def commande_sentier(state):
    if not sentier_ouvert(state):
        return ["🐾 " + t("apr.sentier.ferme")]
    d = preparer_sentier()
    faits = a_(state)["sentier"]
    rel = "~/" + str(d.relative_to(Path.home())) if dans(d, Path.home()) else str(d)
    out = [f"{fg(78)}{BOLD}🐾 " + t("apr.sentier.titre") + RESET, "  " + t("apr.sentier.regle"),
           "  " + t("apr.sentier.aller", cmd=f"cd {rel}")]
    for k, e in enumerate(donnees()["sentier"]["etapes"], 1):
        ok = e["id"] in faits
        coul = fg(78) if ok else fg(252)
        out.append(f"  {coul}{'✓' if ok else '○'} S{k} " + t("apr.sentier." + e["id"]) + f"  `{e['cmd']}`{RESET}")
    out.append(f"  {DIM}" + t("apr.sentier.pied") + RESET)
    return out


def verifier_sentier(state, ligne, statut, cwd):
    a = a_(state)
    if statut not in (None, 0) or not cwd or not dans(cwd, dossier_sentier()):
        return None
    etapes = donnees()["sentier"]["etapes"]
    e = next((x for x in etapes if x["id"] not in a["sentier"]), None)
    if not e:
        return None
    ok = bool(e.get("motif") and re.search(e["motif"], ligne.strip()))
    if e.get("fs"):
        ok = (dossier_sentier() / e["fs"].rstrip("/")).is_dir()
    if not ok:
        return None
    a["sentier"].append(e["id"])
    xp = donnees()["sentier"]["xp"]
    core.add_xp(state, xp)
    k = etapes.index(e) + 1
    msg = "🐾 " + t("apr.sentier.franchi", n=k, xp=xp)
    if k == len(etapes):
        from . import recompenses
        r = recompenses.exploit(state, donnees()["sentier"]["exploit"])
        msg += "\n🏔 " + t("apr.sentier.fin", nom=state.get("name", "")) + (("\n" + r) if r else "")
        core.animer(state, "victoire")
    else:
        msg += "  " + t("apr.sentier.suivant", cmd=etapes[k]["cmd"])
    core.log(state, msg.split("\n")[0])
    return msg


# ================================================================ 30. l'examen-aventure et le diplôme
def examens():
    return donnees()["examens"]


def examen_dispo(state):
    """Le chapitre fini dont l'examen n'est pas encore passé (le plus ancien d'abord), ou None."""
    from . import histoire
    for c in examens()["chapitres"]:
        if histoire.fini(state, c) and c not in a_(state)["diplomes"]:
            return c
    return None


def dossier_examen():
    return terrain() / "examen"


def preparer_salle(chap, k):
    typ = examens()["chapitres"][chap][k]
    d = dossier_examen() / f"salle_{k + 1}"
    _vider(d)
    d.mkdir(parents=True, exist_ok=True)
    _ecrire(d / "plan.txt", t("apr.exam.plan", n=k + 1, mission=t("apr.exam.salle." + typ)) + "\n")
    if typ == "cd":
        (d / "passage").mkdir(exist_ok=True)
    elif typ == "ls_a":
        _ecrire(d / ".cle_cachee", "🗝\n")
    elif typ == "cat":
        _ecrire(d / "parchemin.txt", t("apr.exam.parchemin") + "\n")
    elif typ == "mv":
        _ecrire(d / "ours.txt", "ʕ•ᴥ•ʔ\n")
        (d / "coffre").mkdir(exist_ok=True)
    elif typ == "cp":
        _ecrire(d / "carte.txt", "🗺\n")
    elif typ == "rm":
        _ecrire(d / "caillou.txt", "◍\n")
    elif typ == "chmod":
        _ecrire(d / "secret.txt", "…\n")
    elif typ in ("head", "grep", "wc", "sort"):
        _ecrire(d / "livre.txt", "\n".join(t("apr.exam.livre." + str(i)) for i in range(1, 7)) + "\n")
    elif typ == "find":
        _ecrire(d / "a" / "b" / "c" / "petite.cle", "🗝\n")
    elif typ == "tree":
        (d / "foret" / "arbre" / "branche").mkdir(parents=True, exist_ok=True)
    return d


def salle_reussie(typ, ligne, statut, d):
    s = examens()["salles"][typ]
    if statut not in (None, 0):
        return False
    ok = True
    if s.get("motif"):
        ok = bool(re.search(s["motif"], ligne.strip()))
    if s.get("fs"):
        p = d / s["fs"].rstrip("/")
        ok = p.is_dir() if s["fs"].endswith("/") else p.exists()
    if s.get("absent"):
        ok = ok and not (d / s["absent"]).exists()
    return ok


def commande_examen(state, args):
    a = a_(state)
    ex = a["examen"]
    if args and args[0].lower() in ("diplome", "diplôme") and a["diplomes"]:
        c = a["diplomes"][-1]
        p = ecrire_diplome(state, c)
        return ["🎓 " + t("apr.exam.diplome_ecrit", chemin=_rel(p))]
    if not ex.get("chap"):
        c = examen_dispo(state)
        if not c:
            return ["📜 " + t("apr.exam.aucun")]
        ex.update(chap=c, salle=0, essais=0, debut=time.time())
        preparer_salle(c, 0)
    c = ex["chap"]
    k = ex["salle"]
    typ = examens()["chapitres"][c][k]
    d = dossier_examen() / f"salle_{k + 1}"
    if not d.exists():
        preparer_salle(c, k)
    from . import histoire
    out = [f"{fg(221)}{BOLD}📜 " + t("apr.exam.titre", chapitre=histoire.nom_chapitre(c), n=k + 1) + RESET,
           "  " + t("apr.exam.salle." + typ),
           "  " + t("apr.exam.aller", cmd=f"cd {_rel(d)}"),
           f"  {DIM}" + t("apr.exam.regle") + RESET]
    return out


def _rel(p):
    return "~/" + str(Path(p).relative_to(Path.home())) if dans(p, Path.home()) else str(p)


def verifier_examen(state, ligne, statut, cwd, now):
    a = a_(state)
    ex = a["examen"]
    c = ex.get("chap")
    if not c or premier(ligne) == "tg":
        return None
    k = ex["salle"]
    typ = examens()["chapitres"][c][k]
    d = dossier_examen() / f"salle_{k + 1}"
    if cwd and not dans(cwd, d):
        return None
    s = examens()["salles"][typ]
    if s.get("cwd"):
        ok = bool(cwd) and dans(cwd, d / s["cwd"]) and statut in (None, 0)
    else:
        ok = salle_reussie(typ, ligne, statut, d)
    if not ok:
        ex["essais"] = ex.get("essais", 0) + 1
        if ex["essais"] == examens()["essais"]:
            return "🧭 " + t("apr.exam.guide", cmd=s["cmd"])
        return None
    ex["essais"] = 0
    if k + 1 < len(examens()["chapitres"][c]):
        ex["salle"] = k + 1
        d2 = preparer_salle(c, k + 1)
        return "✓ " + t("apr.exam.franchie", n=k + 1, cmd=f"cd ../salle_{k + 2}") + "\n   " + t("apr.exam.salle." + examens()["chapitres"][c][k + 1]) \
            + ("" if d2 else "")
    a["diplomes"].append(c)
    debut = ex.get("debut")
    ex.clear()
    xp = examens()["xp"]
    core.add_xp(state, xp)
    core.animer(state, "victoire")
    p = ecrire_diplome(state, c, now)
    msg = "🎓 " + t("apr.exam.fini", xp=xp) + "\n   " + t("apr.exam.diplome_ecrit", chemin=_rel(p))
    if a["course"] and debut:
        msg += "\n   ⏱ " + t("apr.course.temps", s=f"{now - debut:.0f}")
    core.log(state, msg.split("\n")[0])
    return msg


# ---------------------------------------------------------------- le dessin du diplôme (PNG, Python pur)
POLICE = {   # 5 × 7, une ligne = 5 bits (les lettres latines, les chiffres, quelques signes ; accents dessinés à part)
    "A": "01110100011000111111100011000110001", "B": "11110100011000111110100011000111110",
    "C": "01110100011000010000100001000101110", "D": "11110100011000110001100011000111110",
    "E": "11111100001000011110100001000011111", "F": "11111100001000011110100001000010000",
    "G": "01110100011000010111100011000101111", "H": "10001100011000111111100011000110001",
    "I": "01110001000010000100001000010001110", "J": "00111000100001000010000101001001100",
    "K": "10001100101010011000101001001010001", "L": "10000100001000010000100001000011111",
    "M": "10001110111010110101100011000110001", "N": "10001100011100110101100111000110001",
    "O": "01110100011000110001100011000101110", "P": "11110100011000111110100001000010000",
    "Q": "01110100011000110001101011001001101", "R": "11110100011000111110101001001010001",
    "S": "01111100001000001110000010000111110", "T": "11111001000010000100001000010000100",
    "U": "10001100011000110001100011000101110", "V": "10001100011000110001100010101000100",
    "W": "10001100011000110101101011010101010", "X": "10001100010101000100010101000110001",
    "Y": "10001100010101000100001000010000100", "Z": "11111000010001000100010001000011111",
    "0": "01110100011001110101110011000101110", "1": "00100011000010000100001000010001110",
    "2": "01110100010000100010001000100011111", "3": "11111000100010000010000011000101110",
    "4": "00010001100101010010111110001000010", "5": "11111100001111000001000011000101110",
    "6": "00110010001000011110100011000101110", "7": "11111000010001000100010000100001000",
    "8": "01110100011000101110100011000101110", "9": "01110100011000101111000010001001100",
    " ": "00000000000000000000000000000000000", "'": "00100001000100000000000000000000000",
    "-": "00000000000000011111000000000000000", ".": "00000000000000000000000000110001100",
    ",": "00000000000000000000001100010001000", ":": "00000011000110000000011000110000000",
    "/": "00001000010001000100010001000010000", "!": "00100001000010000100001000000000100",
    "?": "01110100010000100010001000000000100", "★": "00100001001111101110010100100010000",
    "(": "00010001000100001000010000010000010", ")": "01000001000001000010000100010001000",
}


def _sans_accent(ch):
    import unicodedata
    d = unicodedata.normalize("NFKD", ch)
    base = "".join(c for c in d if not unicodedata.combining(c))
    return base, len(d) > len(base)


def lisible_png(texte):
    """Le texte s'écrit-il avec la police du diplôme PNG ? (les écritures non latines : voir le .svg à côté)"""
    return all(_sans_accent(c)[0].upper() in POLICE or c in "œŒæÆß" for c in texte)


class Toile:
    def __init__(self, w, h, fond):
        self.w, self.h = w, h
        self.px = [list(fond) for _ in range(w * h)]

    def point(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h and c is not None:
            self.px[y * self.w + x] = list(c)

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.point(xx, yy, c)

    def texte(self, x, y, s, c, k=1):
        """Écrit s (majuscules 5 × 7, échelle k) ; renvoie la largeur."""
        x0 = x
        for ch in s:
            if ch in "œŒ":
                x += self.texte(x, y, "OE", c, k)
                continue
            base, accent = _sans_accent(ch)
            g = POLICE.get(base.upper(), POLICE["?"])
            for i, b in enumerate(g):
                if b == "1":
                    self.rect(x + (i % 5) * k, y + (i // 5) * k, k, k, c)
            if accent:
                self.rect(x + 1 * k, y - 2 * k, 3 * k, k, c)
            x += 6 * k
        return x - x0

    def png(self, echelle=1):
        raw = bytearray()
        for y in range(self.h):
            ligne = bytearray()
            for x in range(self.w):
                ligne += bytes(self.px[y * self.w + x]) * echelle
            for _ in range(echelle):
                raw += b"\x00" + ligne

        def bloc(ty, d):
            return struct.pack(">I", len(d)) + ty + d + struct.pack(">I", zlib.crc32(ty + d) & 0xFFFFFFFF)
        return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", self.w * echelle, self.h * echelle, 8, 2, 0, 0, 0))
                + bloc(b"IDAT", zlib.compress(bytes(raw), 6)) + bloc(b"IEND", b""))


def _hex(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def contenu_diplome(state, chap, now=None):
    """Les textes du diplôme (communs au PNG, au SVG et à Android) : titre, lieu, nom de la créature, mois, commandes."""
    from . import histoire
    d = datetime.date.fromtimestamp(now or time.time())
    cm = [examens()["salles"][x]["cmd"].split()[0] for x in examens()["chapitres"][chap]]
    vus = []
    for c in cm:
        if c not in vus:
            vus.append(c)
    return {"titre": t("apr.diplome.titre"), "lieu": histoire.nom_chapitre(chap), "decerne": t("apr.diplome.decerne"),
            "nom": state.get("name", ""), "ligne": t("apr.diplome.ligne"), "mois": t("apr.mois." + str(d.month)) + f" {d.year}",
            "cmds": "  ".join(vus)}


def ecrire_diplome(state, chap, now=None):
    """diplome_<chapitre>.png (à imprimer avec un adulte) et diplome_<chapitre>.svg (toutes les écritures) dans le terrain.
    Aucun prénom tapé : une ligne vide pour l'écrire à la main."""
    from . import bestiaire as B
    c = contenu_diplome(state, chap, now)
    W, H = 300, 210
    fond, encre, vert, or_ = (246, 240, 222), (40, 36, 52), _hex("#1f8a4c"), _hex("#c99a2e")
    tl = Toile(W, H, fond)
    for k in range(3):                                   # le cadre à circuits verts
        tl.rect(4 + k * 3, 4 + k * 3, W - 8 - k * 6, 1, vert)
        tl.rect(4 + k * 3, H - 5 - k * 3, W - 8 - k * 6, 1, vert)
        tl.rect(4 + k * 3, 4 + k * 3, 1, H - 8 - k * 6, vert)
        tl.rect(W - 5 - k * 3, 4 + k * 3, 1, H - 8 - k * 6, vert)
    for x in range(20, W - 20, 16):
        tl.rect(x, 4, 2, 9, vert)
        tl.rect(x + 6, H - 13, 2, 9, vert)

    def centre(y, s, coul, k=1):
        if not lisible_png(s):
            return
        w = len(s) * 6 * k
        tl.texte((W - w) // 2, y, s, coul, k)
    centre(22, "★ TERMINAGOTCHI ★", vert)
    centre(36, c["titre"].upper(), encre, 2)
    centre(58, c["lieu"].upper(), or_)
    e = B.espece(state.get("espece_compagnon") or "") if state.get("espece_compagnon") else None
    img = B.image(e) if e else None
    if img:                                             # la créature, en vrais pixels
        w, h, octets, pal = img
        x0, y0 = (W - w) // 2, 72
        for y in range(h):
            for x in range(w):
                v = octets[y * w + x]
                if v:
                    tl.point(x0 + x, y0 + y, _hex(pal[v - 1]))
    centre(122, c["decerne"].upper(), encre)
    centre(134, c["nom"].upper(), encre, 2)
    tl.rect(70, 168, W - 140, 1, encre)                # la ligne vide : le prénom s'écrit à la main
    centre(172, c["ligne"].upper(), (120, 112, 130))
    centre(152, c["cmds"].upper(), vert)
    centre(190, c["mois"].upper(), encre)
    tl.rect(W - 44, 150, 24, 24, or_)                  # le sceau
    tl.texte(W - 38, 158, "★", fond)
    dossier = terrain()
    dossier.mkdir(parents=True, exist_ok=True)
    p = dossier / f"diplome_{chap}.png"
    if not p.is_symlink():
        p.write_bytes(tl.png(3))
    s = dossier / f"diplome_{chap}.svg"
    if not s.is_symlink():
        from xml.sax.saxutils import escape as x
        s.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="630" viewBox="0 0 300 210">'
            f'<image href="{p.name}" width="300" height="210" style="image-rendering:pixelated"/>'
            f'<rect x="20" y="20" width="260" height="60" fill="#f6f0de"/><rect x="40" y="118" width="220" height="30" fill="#f6f0de"/>'
            f'<rect x="60" y="186" width="180" height="12" fill="#f6f0de"/>'
            f'<text x="150" y="44" text-anchor="middle" font-size="16" fill="#282434">{x(c["titre"])}</text>'
            f'<text x="150" y="64" text-anchor="middle" font-size="9" fill="#c99a2e">{x(c["lieu"])}</text>'
            f'<text x="150" y="128" text-anchor="middle" font-size="7" fill="#282434">{x(c["decerne"])}</text>'
            f'<text x="150" y="145" text-anchor="middle" font-size="12" fill="#282434">{x(c["nom"])}</text>'
            f'<text x="150" y="195" text-anchor="middle" font-size="7" fill="#282434">{x(c["mois"])}</text>'
            f'<text x="150" y="178" text-anchor="middle" font-size="5" fill="#787082">{x(c["ligne"])}</text></svg>\n',
            encoding="utf-8")
    return p


# ================================================================ le tour de jeu (app.boucle_jeu)
AIDES = ("aide", "help", "indice", "hint")


def tour(state, lines, cwd, statut_de=None, now=None):
    """Après le tour normal : maîtrise, révisions, commande du jour, mini-énigmes, jeux, sentier, examen, temps."""
    now = now or time.time()
    a = a_(state)
    aide_avant = bool(a.get("aide_avant"))         # la commande d'avant était une aide (gardé d'un tour à l'autre)
    for k, line in enumerate(lines):
        if core.est_colle(line) or not line.strip():
            continue
        statut = statut_de(lines, k) if statut_de else None
        c = premier(line)
        mots = mots_de(line)
        est_aide = c in AIDES or (c == "tg" and len(mots) > 1 and mots[1].lower() in AIDES)
        for msg in (noter_usage(state, line, statut, aide=aide_avant),
                    noter_vu(state, c, now) if statut in (None, 0) else None,
                    verifier_jour(state, line, statut, now),
                    verifier_erreur(state, line, statut, cwd, now) if c != "tg" else None,
                    verifier_jeux(state, line, cwd, now),
                    verifier_sentier(state, line, statut, cwd),
                    verifier_examen(state, line, statut, cwd, now)):
            if msg:
                info(state, msg)
                core.say(state, msg.split("\n")[0], 10)
        aide_avant = est_aide
    a["aide_avant"] = aide_avant
    if lines:
        verifier_temps(state, now)
        inviter_revision(state, now)


def eclairs_permis(state):
    return eclairs(state)


# ================================================================ les commandes `tg …`
def commande(mode, args):
    """Le point d'entrée des sous-commandes (app.py) : imprime l'écran demandé."""
    sortie = []
    if mode == "parent":
        print("\n".join(commande_parent(None, args)))
        return

    def faire(s):
        a_(s)
        if mode in ("bac-a-sable", "bac_a_sable", "bac"):
            sortie.extend(commande_bac(s, args))
        elif mode == "rares":
            sortie.extend(ecran_rares(s, args))
        elif mode in ("souvenirs", "revisions", "révisions"):
            sortie.extend(lignes_souvenirs(s))
        elif mode == "jour":
            sortie.extend(ecran_jour(s))
        elif mode in ("enigme", "énigme"):
            sortie.extend(commande_enigme(s, args))
        elif mode == "passe":
            sortie.append(passer(s))
        elif mode == "carnet":
            sortie.extend(ecran_carnet(s, args))
        elif mode == "jeux":
            sortie.extend(commande_jeux(s, args))
        elif mode == "course":
            sortie.extend(commande_course(s, args))
        elif mode == "sentier":
            sortie.extend(commande_sentier(s))
        elif mode == "examen":
            sortie.extend(commande_examen(s, args))
        elif mode == "maitrise":
            sortie.extend(lignes_maitrise(s))
    core.modifier(faire)
    print("\n".join(sortie))
