"""Le mode classe (docs/programme.md § 7.7), 100 % local : rien n'est envoyé, aucun compte, aucun serveur.

  - L'enseignant fabrique un CODE DE SÉANCE (`tg classe creer 5 grand sanschrono`, ou la page /enseignants du site).
    Le code ne contient que des réglages du jeu : le chapitre visé et 3 options. Il ne sert à rien d'autre.
        05-GS-K   = chapitre 5 · G grand écran · S sans chrono · K lettre de contrôle (attrape les fautes de frappe)
        00-K      = pas de chapitre imposé, aucune option
    Options : A « sans aide » (cran C : le but seulement), G grand écran (`tg espace classe`), S sans chrono.
  - L'élève tape `tg classe code 05-GS-K Lynx42` : un PSEUDONYME (2 à 16 lettres ou chiffres, sans espace : pas de
    « Prénom Nom »). Pendant la séance : aucune synchronisation, aucune requête réseau du recensement, faim en
    pause, pas de notifications, les options du code.
  - `tg classe bilan` : le bilan à l'écran (à montrer ou imprimer) ; `tg classe bilan fichier` : le même en .txt et
    en .csv dans le dossier personnel, que l'élève remet lui-même (clé USB, dossier partagé de l'école).
  - `tg classe rassembler <dossier>` (côté enseignant) : lit les .csv remis, écrit bilan_de_classe.csv et montre où la classe
    bloque. Jamais de classement des élèves.
  - `tg classe fin` : la séance se termine, les réglages d'avant reviennent. `tg classe effacer` : tout est oublié.

Les crans (§ 2.0) : A = étape réussie avec la commande montrée ; C = réussie en mode « sans aide » alors que la
commande était cachée ; D = exercice de la salle d'entraînement réussi (résultat vérifié). Le cran B (à trous)
n'existe pas encore dans le jeu : le bilan ne l'invente pas.

Le tableau de bord EN LIGNE (§ 7.7) est reporté : il demande un serveur, une décision du propriétaire et un avis CNIL.
"""
import csv
import io
import re
import time
from pathlib import Path

from . import core
from .langue import t

LETTRES = "ABCDEFGHJKMNPQRSTUVWXYZ"          # 23 lettres, sans I, L, O (confondues avec 1 et 0)
OPTIONS = "AGS"                              # ordre canonique
MOTS_OPTIONS = {"A": ("a", "sansaide", "sans-aide", "noaid"), "G": ("g", "grand", "grandecran", "big", "projection"),
                "S": ("s", "sanschrono", "sans-chrono", "nochrono", "chrono")}
PSEUDO = re.compile(r"^[A-Za-z0-9_-]{2,16}$")
MAX_ETAPES = 400
COLONNES = ["pseudo", "code", "date", "debut", "fin", "minutes", "commandes", "chapitre_vise", "chapitre_en_cours",
            "lecon", "etape", "etapes_cran_A", "etapes_cran_C", "exercices_cran_D", "chapitres_finis",
            "notions_acquises", "blocages"]


# ---------------------------------------------------------------- le code de séance (pur, mêmes vecteurs que le site)
def controle(corps):
    """La lettre de contrôle d'un corps de code (« 05GS ») : somme pondérée des caractères, modulo 23."""
    return LETTRES[sum((i + 1) * ord(c) for i, c in enumerate(corps)) % len(LETTRES)]


def fabriquer(n, options=""):
    """Le code de séance : fabriquer(5, "SG") → « 05-GS-? »."""
    if not isinstance(n, int) or not 0 <= n <= 99:
        raise ValueError(n)
    opts = "".join(o for o in OPTIONS if o in str(options).upper())
    corps = f"{n:02d}{opts}"
    return f"{n:02d}-{opts}-{controle(corps)}" if opts else f"{n:02d}-{controle(corps)}"


def lire(code):
    """{"n": 5, "options": "GS"} si le code est bon, sinon None (faute de frappe, lettre de contrôle fausse…)."""
    brut = re.sub(r"[^0-9A-Za-z]", "", str(code or "")).upper()
    m = re.fullmatch(r"(\d{2})([AGS]*)([A-Z])", brut)
    if not m or controle(m.group(1) + m.group(2)) != m.group(3):
        return None
    opts = m.group(2)
    if "".join(o for o in OPTIONS if o in opts) != opts:      # toujours dans l'ordre, sans doublon
        return None
    return {"n": int(m.group(1)), "options": opts}


# ---------------------------------------------------------------- l'état
def c_(state):
    """La séance en cours (dict) ou None."""
    c = state.get("classe") if isinstance(state, dict) else None
    return c if isinstance(c, dict) and not c.get("fin") else None


def actif(state):
    return c_(state) is not None


def actif_sur_disque():
    """Pour les fonctions réseau qui n'ont pas l'état sous la main (recense.requete)."""
    try:
        return actif(core.load())
    except Exception:
        return False


def option(state, o):
    c = c_(state)
    return bool(c and o in c.get("options", ""))


def sans_chrono(state):
    return option(state, "S")


def _chapitre(n):
    from . import histoire
    return next((c for c in histoire.CHAPITRES if c.get("n") == n and n > 0 and histoire.chapitre_dispo(c)), None)


def _nom(n):
    from . import histoire
    c = _chapitre(n)
    return f"{n} · {histoire.nom_chapitre(c['id'])}" if c else "—"


# ---------------------------------------------------------------- ce que la séance retient (appelé par le jeu)
def etape(state, les, i, step):
    """Une étape de leçon réussie (histoire.avancer), avant que l'étape avance."""
    c = c_(state)
    if c is None:
        return
    from . import placement
    cran = "C" if placement.cache(state, step) else "A"
    c["etapes"] = (c["etapes"] + [{"l": les["id"], "i": i, "cmd": step.get("cmd", ""), "cran": cran,
                                   "t": int(time.time())}])[-MAX_ETAPES:]


def rate(state, les, i):
    """Une ligne tapée qui n'a pas fait avancer l'étape (histoire.tick_lecon)."""
    c = c_(state)
    if c is None:
        return
    cle = f"{les['id']}:{i}"
    c["rates"][cle] = c["rates"].get(cle, 0) + 1
    step = les["steps"][i] if i < len(les["steps"]) else {}
    c["cmds"][cle] = step.get("cmd", "")


def exercice(state, typ):
    """Un exercice de la salle d'entraînement réussi (entrainement.reussir) : cran D."""
    c = c_(state)
    if c is None:
        return
    c["ex"] = (c["ex"] + [{"type": typ, "t": int(time.time())}])[-MAX_ETAPES:]


# ---------------------------------------------------------------- rejoindre, finir
def rejoindre(state, code, pseudo):
    d = lire(code)
    if d is None:
        return t("classe.code.faux", code=str(code or ""))
    if not PSEUDO.match(str(pseudo or "")):
        return t("classe.pseudo.faux")
    if d["n"] and _chapitre(d["n"]) is None:
        return t("classe.code.chapitre", n=d["n"])
    if actif(state):
        finir(state)
    from . import histoire, placement, satiete
    h = histoire.h_(state)
    cfg = state.setdefault("config", {})
    avant = {"sans_aide": bool(cfg.get("sans_aide")), "notifs": cfg.get("notifs", True),
             "vacances": bool(satiete.s_(state).get("vacances"))}
    state["classe"] = {"code": fabriquer(d["n"], d["options"]), "n": d["n"], "options": d["options"], "pseudo": pseudo,
                       "debut": int(time.time()), "fin": None, "total0": state.get("total", 0),
                       "faits0": list(h["faits"]), "ailes0": list(h["ailes"]), "etapes": [], "rates": {}, "cmds": {},
                       "ex": [], "avant": avant}
    cfg["notifs"] = False
    satiete.vacances(state, True)
    if "A" in d["options"]:
        cfg["sans_aide"] = True
    out = [t("classe.bienvenue", pseudo=pseudo, code=state["classe"]["code"])]
    if d["n"]:
        cid = _chapitre(d["n"])["id"]
        out.append(histoire.choisir(state, cid, dit=False))
    out.append(t("classe.reglages", liste=", ".join(t("classe.opt." + o) for o in d["options"]) or t("classe.opt.aucune")))
    if "G" in d["options"]:
        out.append(t("classe.grand"))
    if placement.sans_aide(state) and "A" not in d["options"]:
        out.append(t("classe.deja_sans_aide"))
    out.append(t("classe.rien_envoye"))
    return "\n".join(out)


def finir(state):
    c = c_(state)
    if c is None:
        return t("classe.pas_de_seance")
    from . import satiete
    c["fin"] = int(time.time())
    av = c.get("avant", {})
    cfg = state.setdefault("config", {})
    cfg["sans_aide"] = av.get("sans_aide", False)
    cfg["notifs"] = av.get("notifs", True)
    satiete.vacances(state, av.get("vacances", False))
    return t("classe.fini", pseudo=c["pseudo"])


def effacer(state):
    state.pop("classe", None)
    return t("classe.efface")


# ---------------------------------------------------------------- le bilan
def resume(state):
    """Le bilan de la séance (en cours, sinon la dernière) en dict, ou None."""
    c = state.get("classe") if isinstance(state.get("classe"), dict) else None
    if c is None:
        return None
    from . import histoire
    h = histoire.h_(state)
    fin = c.get("fin") or int(time.time())
    les, _ = histoire.lecon_courante(state)
    cours = histoire.chapitre_courant(state)
    lecon = etape_txt = ""
    if les and cours:
        lecon = f"{cours['lecons'].index(les['id']) + 1}/{len(cours['lecons'])}"
        etape_txt = f"{state.get('step', 0) + 1}/{len(les['steps'])}"
    notions = []
    for e in c["etapes"]:
        if e["cran"] in ("C", "D") and e["cmd"] and e["cmd"] not in notions:
            notions.append(e["cmd"])
    blocages = sorted(((n, c["cmds"].get(k, ""), k) for k, n in c["rates"].items() if n >= 3), reverse=True)
    return {
        "pseudo": c["pseudo"], "code": c["code"], "date": time.strftime("%Y-%m-%d", time.localtime(c["debut"])),
        "debut": time.strftime("%H:%M", time.localtime(c["debut"])), "fin": time.strftime("%H:%M", time.localtime(fin)),
        "minutes": max(0, round((fin - c["debut"]) / 60)), "commandes": max(0, state.get("total", 0) - c["total0"]),
        "chapitre_vise": _nom(c["n"]) if c["n"] else "—",
        "chapitre_en_cours": f"{cours['n']} · {histoire.nom_chapitre(cours['id'])}" if cours else "—",
        "lecon": lecon, "etape": etape_txt,
        "etapes_cran_A": sum(1 for e in c["etapes"] if e["cran"] == "A"),
        "etapes_cran_C": sum(1 for e in c["etapes"] if e["cran"] == "C"),
        "exercices_cran_D": len(c["ex"]),
        "chapitres_finis": [f"{histoire.PAR_CHAP[a]['n']} · {histoire.nom_chapitre(a)}" for a in h["ailes"]
                            if a not in c["ailes0"] and a in histoire.PAR_CHAP],
        "notions_acquises": notions,
        "blocages": [f"{cmd or k} ({n})" for n, cmd, k in blocages[:8]],
        "en_cours": not c.get("fin"),
    }


def lignes_bilan(state):
    r = resume(state)
    if r is None:
        return [t("classe.pas_de_seance")]
    out = [t("classe.bilan.titre", pseudo=r["pseudo"], code=r["code"]),
           t("classe.bilan.quand", date=r["date"], debut=r["debut"], fin=r["fin"], minutes=r["minutes"]),
           t("classe.bilan.commandes", n=r["commandes"]),
           t("classe.bilan.vise", chapitre=r["chapitre_vise"]),
           t("classe.bilan.cours", chapitre=r["chapitre_en_cours"], lecon=r["lecon"] or "—", etape=r["etape"] or "—"),
           t("classe.bilan.crans", a=r["etapes_cran_A"], c=r["etapes_cran_C"], d=r["exercices_cran_D"]),
           t("classe.bilan.finis", liste=", ".join(r["chapitres_finis"]) or "—"),
           t("classe.bilan.notions", liste=", ".join(r["notions_acquises"]) or "—"),
           t("classe.bilan.blocages", liste=", ".join(r["blocages"]) or "—"),
           t("classe.bilan.legende"),
           t("classe.rien_envoye")]
    return out


def _ligne_csv(r):
    return [r[k] if not isinstance(r[k], list) else " | ".join(r[k]) for k in COLONNES]


def ecrire_fichiers(state, dossier=None):
    """Le bilan en .txt (à imprimer) et en .csv (pour l'enseignant), dans le dossier personnel. Renvoie les chemins."""
    r = resume(state)
    if r is None:
        return []
    dossier = Path(dossier) if dossier else Path.home()
    base = dossier / f"terminagotchi_bilan_{r['pseudo']}_{r['date']}"
    txt = base.with_suffix(".txt")
    txt.write_text("\n".join(_sans_ansi(x) for x in lignes_bilan(state)) + "\n", encoding="utf-8")
    f = io.StringIO()
    w = csv.writer(f, delimiter=";", lineterminator="\n")
    w.writerow(COLONNES)
    w.writerow(_ligne_csv(r))
    cs = base.with_suffix(".csv")
    cs.write_text("﻿" + f.getvalue(), encoding="utf-8")       # BOM : le tableur de l'école lit les accents
    return [txt, cs]


def _sans_ansi(s):
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", s).replace("`", "")


# ---------------------------------------------------------------- côté enseignant : rassembler les bilans remis
def rassembler(dossier, sortie=None):
    """Lit les terminagotchi_bilan_*.csv d'un dossier, écrit bilan_de_classe.csv et renvoie (lignes à afficher, chemin)."""
    dossier = Path(dossier)
    rangs = []
    for p in sorted(dossier.glob("terminagotchi_bilan_*.csv")):
        try:
            texte = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        for ligne in csv.DictReader(io.StringIO(texte), delimiter=";"):
            if ligne.get("pseudo") and set(COLONNES) <= set(ligne):
                rangs.append({k: ligne[k] for k in COLONNES})
    if not rangs:
        return [t("classe.rassembler.rien", dossier=str(dossier))], None
    rangs.sort(key=lambda x: (x["date"], x["pseudo"].lower()))      # par date puis par ordre alphabétique : pas de classement
    sortie = Path(sortie) if sortie else dossier / "bilan_de_classe.csv"
    f = io.StringIO()
    w = csv.writer(f, delimiter=";", lineterminator="\n")
    w.writerow(COLONNES)
    for x in rangs:
        w.writerow([x[k] for k in COLONNES])
    sortie.write_text("﻿" + f.getvalue(), encoding="utf-8")
    blocs, chap = {}, {}
    for x in rangs:
        for b in filter(None, (s.strip() for s in x["blocages"].split("|"))):
            nom = re.sub(r"\s*\(\d+\)$", "", b)
            blocs[nom] = blocs.get(nom, 0) + 1
        chap[x["chapitre_en_cours"]] = chap.get(x["chapitre_en_cours"], 0) + 1
    out = [t("classe.rassembler.titre", n=len(rangs), fichier=str(sortie))]
    out.append(t("classe.rassembler.chapitres", liste=", ".join(f"{k} : {v}" for k, v in sorted(chap.items())) or "—"))
    tri = sorted(blocs.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    out.append(t("classe.rassembler.blocages", liste=", ".join(f"{k} ({v})" for k, v in tri) or "—"))
    out.append(t("classe.rassembler.note"))
    return out, sortie


# ---------------------------------------------------------------- tg classe …
def _creer(args):
    from . import histoire
    n, opts = 0, ""
    for a in args:
        x = a.lower()
        o = next((k for k, mots in MOTS_OPTIONS.items() if x in mots), None)
        if o:
            opts += o
        elif x.isdigit():
            n = int(x)
        else:
            c = histoire.chercher_chapitre(x)
            if not c:
                return t("classe.creer.inconnu", nom=a)
            n = c["n"] if isinstance(c, dict) else histoire.PAR_CHAP[c]["n"]
    if n and _chapitre(n) is None:
        return t("classe.code.chapitre", n=n)
    code = fabriquer(n, opts)
    return t("classe.creer.ok", code=code, chapitre=_nom(n) if n else "—",
             liste=", ".join(t("classe.opt." + o) for o in OPTIONS if o in opts) or t("classe.opt.aucune"))


def commande(args):
    """tg classe [code CODE PSEUDO | bilan [fichier] | fin | effacer | creer … | rassembler DOSSIER]."""
    sous = args[0].lower() if args else ""
    if sous in ("creer", "créer", "nouveau", "new", "create"):
        return _creer(args[1:])
    if sous in ("rassembler", "collect"):
        lignes, _ = rassembler(args[1] if len(args) > 1 else ".")
        return "\n".join(lignes)
    if sous in ("code", "rejoindre", "join"):
        if len(args) < 3:
            return t("classe.code.usage")
        out = []
        core.modifier(lambda s: out.append(rejoindre(s, args[1], args[2])))
        return out[0] if out else ""
    st = core.load()
    if st is None:
        return t("classe.pas_de_seance")
    if sous in ("bilan", "report"):
        core.migrate(st)
        lignes = lignes_bilan(st)
        if len(args) > 1 and args[1].lower() in ("fichier", "file", "csv"):
            chemins = ecrire_fichiers(st)
            if chemins:
                lignes.append(t("classe.bilan.ecrit", liste="\n  " + "\n  ".join(str(p) for p in chemins)))
        return "\n".join(lignes)
    if sous in ("fin", "quitter", "stop", "end"):
        out = []
        core.modifier(lambda s: out.append(finir(s)))
        return out[0] if out else ""
    if sous in ("effacer", "erase"):
        out = []
        core.modifier(lambda s: out.append(effacer(s)))
        return out[0] if out else ""
    c = c_(st)
    etat = t("classe.etat.on", pseudo=c["pseudo"], code=c["code"]) if c else t("classe.etat.off")
    return etat + "\n" + t("classe.aide")
