"""Les Ponts des Nombres (docs/programme.md § 7.10) : les mathématiques par la pratique, jamais un mur.

    tg maths                       les passerelles, les ponts allumés, comment demander
    tg maths <mots>                la fiche la plus proche (même moteur de recherche que le lexique : registre.py),
                                   ses exemples et un exercice (nombres tirés au hasard, corrigé par le jeu)
    tg maths <nombre>              la réponse à l'exercice en cours
    tg maths oui | un peu | pas du tout | je ne connais pas
                                   la réponse à « Tu connais … ? » : « oui » continue, sinon on descend dans le
                                   graphe des prérequis (division avant modulo, multiplication avant division…),
                                   puis on revient exactement où on était

Rien n'est jamais fermé : chaque commande marche à tout moment, sans réponse obligatoire. Les fiches et le graphe
sont dans programme.json (« maths ») ; les textes sont des clés de langue. Mêmes règles dans l'appli Android
(Maths.kt) : vecteurs communs donnees/maths/vecteurs.json (exercices et recherches).
"""
import re

from . import programme, registre
from .langue import brut, courante, t
from .tirage import Hasard

MASQUE = (1 << 64) - 1


def noeuds():
    return programme.donnees().get("maths", {})


def titre(mid):
    return t(noeuds()[mid]["titre"])


def m_(state):
    m = state.setdefault("maths", {})
    for k, v in (("acquis", []), ("connus", []), ("pile", []), ("courant", None), ("question", None), ("exo", None),
                 ("n", 0)):
        m.setdefault(k, v)
    return m


# ---------------------------------------------------------------- le graphe des prérequis
def prerequis(mid):
    return list(noeuds().get(mid, {}).get("prerequis", []))


def tous_prerequis(mid):
    """Tous les prérequis, des plus profonds aux plus proches (ordre topologique, sans doublon)."""
    out = []

    def visiter(x):
        for p in prerequis(x):
            if p not in out:
                visiter(p)
                out.append(p)
    visiter(mid)
    return out


def sait(state, mid):
    m = m_(state)
    return mid in m["acquis"] or mid in m["connus"]


def manquant(state, mid):
    """Le premier prérequis DIRECT ni acquis ni déclaré connu (celui qu'on demande), ou None."""
    return next((p for p in prerequis(mid) if not sait(state, p)), None)


# ---------------------------------------------------------------- la recherche (moteur du lexique)
_INDEX = {}


def _concepts(mid):
    """(concepts du titre et des mots-clés, concepts de la question et de l'image), en français et dans la langue."""
    code = courante()
    if (mid, code) not in _INDEX:
        n = noeuds()[mid]
        codes = ["fr"] if code == "fr" else ["fr", code]
        forts = [n["titre"]] + ([n["mots_cles"]] if n.get("mots_cles") else [])
        doux = [n[k] for k in ("question", "enfant") if n.get(k)]
        _INDEX[(mid, code)] = tuple(registre.concepts(" ".join(brut(c, x) or "" for x in codes for c in cles))
                                    for cles in (forts, doux))
    return _INDEX[(mid, code)]


def chercher(requete):
    """L'identifiant de la notion la plus proche de la question, ou None (les mots du titre et des mots-clés
    comptent 10, ceux de la question et de l'image 3)."""
    q = requete.strip().lower()
    if not q:
        return None
    if q in noeuds():
        return q
    qc = registre.concepts(requete)
    meilleur, score = None, 0.0
    for mid, n in noeuds().items():
        forts, doux = _concepts(mid)
        a, b = len(qc & forts), len(qc & (doux - forts))
        if not a and not b:
            continue
        s = a * 10 + b * 3 - len((forts | doux) - qc) * 0.01 + (1 if n.get("fiche") else 0)
        if s > score:
            meilleur, score = mid, s
    return meilleur


# ---------------------------------------------------------------- les exercices (même hasard qu'Android)
def generer(typ, graine, k):
    """Un exercice : (paramètres du texte, réponse attendue, commande de vérification dans un vrai terminal)."""
    h = Hasard(f"{graine & MASQUE:016x}", k)
    if typ == "comptage":
        n = 3 + h.entier(10)
        return {"etoiles": "★" * n}, str(n), f"seq {n} | wc -l"
    if typ == "addition":
        a, b = 2 + h.entier(19), 2 + h.entier(19)
        return {"a": a, "b": b}, str(a + b), f"echo $(({a} + {b}))"
    if typ == "soustraction":
        a = 5 + h.entier(16)
        b = 1 + h.entier(a - 1)
        return {"a": a, "b": b}, str(a - b), f"echo $(({a} - {b}))"
    if typ == "multiplication":
        a, b = 2 + h.entier(9), 2 + h.entier(9)
        return {"a": a, "b": b}, str(a * b), f"echo $(({a} * {b}))"
    if typ in ("division", "modulo"):
        b = 2 + h.entier(8)
        q = 1 + h.entier(9)
        r = h.entier(b)
        a = b * q + r
        if typ == "division":
            return {"a": a, "b": b}, str(q), f"echo $(({a} / {b}))"
        return {"a": a, "b": b}, str(r), f"echo $(({a} % {b}))"
    if typ == "puissances":
        a, b = 2 + h.entier(4), 2 + h.entier(3)
        calcul = " × ".join([str(a)] * b)
        return {"a": a, "b": b, "calcul": calcul}, str(a ** b), "echo $((" + " * ".join([str(a)] * b) + "))"
    if typ == "binaire":
        n = 1 + h.entier(31)
        bits = format(n, "b")
        return {"bits": bits}, str(n), f"echo $((2#{bits}))"
    raise ValueError(typ)


def _graine(state):
    """La graine des exercices de la partie (tirée une fois : les nombres changent d'une partie à l'autre)."""
    m = m_(state)
    if not isinstance(m.get("graine"), int):
        import time
        m["graine"] = int(time.time())
    return m["graine"]


def _nouvel_exo(state, mid):
    m = m_(state)
    n = noeuds()[mid]
    p, rep, verif = generer(n["exercice"]["type"], _graine(state), m["n"])
    m["n"] += 1
    m["exo"] = {"notion": mid, "params": {k: str(v) for k, v in p.items()}, "reponse": rep, "verif": verif}
    return t(n["exercice"]["consigne"], **m["exo"]["params"])


# ---------------------------------------------------------------- l'écran d'une fiche
def _mot(cle):
    return " ".join(registre.mots(t(cle)))


def mots_reponse(texte):
    """« oui » / « peu » / « non » (pas du tout, je ne connais pas) / None, en français ou dans la langue choisie."""
    x = " ".join(registre.mots(texte))
    for code in ("fr", courante()):
        for genre, cle in (("non", "maths.mot.inconnu"), ("non", "maths.mot.non"), ("peu", "maths.mot.peu"),
                           ("oui", "maths.mot.oui")):
            v = brut(cle, code)
            if v and x == " ".join(registre.mots(v)):
                return genre
    return None


def _question(state, mid, cmd):
    """La question sur le premier prérequis manquant (jamais obligatoire), ou []."""
    p = manquant(state, mid)
    m = m_(state)
    m["question"] = p
    if not p:
        return []
    return ["", " " + t("maths.demande", notion=titre(p), question=t(noeuds()[p]["question"])),
            " " + t("maths.choix", oui=f"{cmd} {t('maths.mot.oui')}", peu=f"{cmd} {t('maths.mot.peu')}",
                    non=f"{cmd} {t('maths.mot.non')}")]


def ecran_fiche(state, mid, cmd):
    """Toute la fiche : image, version des grands, limite, idée fausse, exemples, exercice, question."""
    m = m_(state)
    n = noeuds()[mid]
    m["courant"] = mid
    out = [t("maths.titre") + " · " + titre(mid)]
    if not n.get("fiche"):
        base = [titre(p) for p in prerequis(mid)] or [titre("comptage")]
        out.append(" " + t("maths.pas_encore", notion=titre(mid), liste=", ".join(base)))
        m["question"] = None
        return out
    out += [" " + t(n["enfant"]), " " + t("grand.ligne", texte=t(n["grands"])),
            " " + t("prog.limite", texte=t(n["limite_image"]))]
    out += [" " + t("prog.idee", texte=t(k)) for k in n["idees_fausses"]]
    out += [" " + t("maths.exemples")] + ["   • " + t(k) for k in n["exemples"]]
    if prerequis(mid):
        out.append(" " + t("maths.prerequis", liste=", ".join(titre(p) for p in prerequis(mid))))
    out += ["", " " + t("maths.exercice", exo=_nouvel_exo(state, mid)), "   " + t("maths.repondre", cmd=cmd)]
    return out + _question(state, mid, cmd)


def apercu(state, cmd):
    m = m_(state)
    fiches = [mid for mid, n in noeuds().items() if n.get("fiche")]
    out = [t("maths.titre"), " " + t("maths.aide", cmd=cmd),
           " " + t("maths.passerelles", liste=", ".join(titre(x) for x in fiches))]
    out.append(" " + (t("maths.allumes", liste=", ".join(titre(x) for x in m["acquis"])) if m["acquis"]
                      else t("maths.aucun")))
    if m["courant"]:
        out.append(" " + t("maths.en_cours", notion=titre(m["courant"])))
    return out


def repondre_nombre(state, texte, cmd):
    m = m_(state)
    e = m.get("exo")
    if not e:
        return [t("maths.pas_exo", cmd=f"{cmd} division")]
    mid = e["notion"]
    n = noeuds()[mid]
    verif = " " + t("maths.verifie", verif=e["verif"])
    if texte.strip().lstrip("0") == e["reponse"].lstrip("0") or texte.strip() == e["reponse"]:
        m["exo"] = None
        if mid not in m["acquis"]:
            m["acquis"].append(mid)
        out = [t("maths.juste", notion=titre(mid)), verif]
        if m["pile"]:
            haut = m["pile"].pop()
            out += ["", t("maths.retour", notion=titre(haut))] + ecran_fiche(state, haut, cmd)
        return out
    astuce = t(n["exercice"]["erreur"], **e["params"])
    out = [t("maths.faux", reponse=e["reponse"], astuce=astuce), verif]
    out.append(" " + t("maths.encore", exo=_nouvel_exo(state, mid)))
    return out


def repondre_mot(state, genre, cmd):
    m = m_(state)
    q = m.get("question")
    if not q:                                       # « je ne connais pas » sans question : la notion en cours
        cour = m.get("courant")                     # (on descend vers son premier prérequis), sinon le début
        if genre == "oui":
            return apercu(state, cmd)
        if cour and manquant(state, cour):
            q = manquant(state, cour)
        elif cour:
            return [t("maths.descend", notion=titre(cour))] + ([t("maths.fond")] if not prerequis(cour) else []) + \
                ecran_fiche(state, cour, cmd)
        else:
            return [t("maths.fond")] + ecran_fiche(state, "comptage", cmd)
    cour = m.get("courant")
    if genre == "oui":
        if q not in m["connus"]:
            m["connus"].append(q)
        m["question"] = None
        suite = _question(state, cour, cmd) if cour else []
        if suite:
            return suite[1:]
        return [t("maths.continue", notion=titre(cour))] if cour else apercu(state, cmd)
    if cour and cour != q and cour not in m["pile"]:
        m["pile"].append(cour)
    out = [t("maths.descend", notion=titre(q))]
    if not prerequis(q):
        out.append(t("maths.fond"))
    return out + ecran_fiche(state, q, cmd)


def commande(state, args, cmd="tg maths"):
    """tg maths … : les lignes à afficher (l'état « maths » de la partie est mis à jour)."""
    texte = " ".join(args).strip()
    if not texte:
        return apercu(state, cmd)
    if re.fullmatch(r"-?\d+", texte):
        return repondre_nombre(state, texte, cmd)
    genre = mots_reponse(texte)
    if genre:
        return repondre_mot(state, genre, cmd)
    mid = chercher(texte)
    if not mid:
        return [t("maths.rien", cmd=cmd)]
    return ecran_fiche(state, mid, cmd)
