"""Pour ceux qui connaissent déjà un peu le terminal (G-13, simulation de Hugo) :

  - `tg placement` : un petit test SANS AIDE (la commande n'est pas montrée, seulement le but) : où es-tu, va à la
    Racine, reviens au camp de base, montre les fichiers cachés. Réussi en 10 lignes au plus : le chapitre 1 est validé
    et la suite se joue en mode « sans aide ». Raté : rien n'est perdu, on fait le chapitre 1 avec l'aide.
  - `tg sansaide on|off` : le mode « défi sans aide » : chaque étape montre son but, pas la commande ; `aide` (ou trois
    essais ratés) la montre. Les étapes sont toujours validées sur le résultat (verif.py).
"""
import re
import time
from pathlib import Path

from . import core
from .langue import t

DEFIS = [
    {"id": "pwd", "but": "plac.but.pwd", "re": r"^pwd(\s|$)"},
    {"id": "racine", "but": "plac.but.racine", "ici": "racine"},
    {"id": "camp", "but": "plac.but.camp", "ici": "camp"},
    {"id": "caches", "but": "plac.but.caches", "re": r"^ls(\s+-\w+)*\s+(-\w*[aA]\w*|--all|--almost-all)(\s|$)"},
]
ESSAIS_MAX = 10


def p_(state):
    return state.setdefault("placement", {"etat": None, "i": 0, "lignes": 0})


def actif(state):
    return p_(state).get("etat") == "en_cours"


def sans_aide(state):
    return bool(state.get("config", {}).get("sans_aide"))


def commencer(state):
    """`tg placement` : seulement tant que le chapitre 1 n'est pas fini."""
    from . import histoire
    if histoire.fini(state, "reveil"):
        return t("plac.deja")
    p = p_(state)
    p.update(etat="en_cours", i=0, lignes=0, t=time.time())
    return t("plac.debut", n=len(DEFIS), max=ESSAIS_MAX) + "\n" + but(state)


def but(state):
    p = p_(state)
    d = DEFIS[min(p["i"], len(DEFIS) - 1)]
    return t("plac.etape", n=p["i"] + 1, total=len(DEFIS), but=t(d["but"]))


def _reussi(d, m):
    if m.statut not in (None, 0):
        return False
    if "re" in d:
        return bool(re.search(d["re"], m.texte.strip()))
    lieu = str(Path(Path.home().anchor or "/")) if d["ici"] == "racine" else str(Path.home())
    return m.apres and str(Path(m.apres)) == lieu and m.apres != m.avant


def tick(state, morcs):
    """Les morceaux de ligne tapés pendant le test (verif.morceaux)."""
    p = p_(state)
    if not actif(state):
        return
    for m in morcs:
        p["lignes"] += 1
        d = DEFIS[p["i"]]
        if _reussi(d, m):
            p["i"] += 1
            if p["i"] >= len(DEFIS):
                return reussir(state)
            core.say(state, but(state), 12)
            core.terminal(state, "✔ " + but(state))
        if p["lignes"] >= ESSAIS_MAX:
            return rater(state)


def reussir(state):
    """Le chapitre 1 est validé (comme s'il avait été fait), la suite se joue sans aide."""
    from . import histoire
    p = p_(state)
    p["etat"] = "reussi"
    h = histoire.h_(state)
    T = core.TERRAIN
    try:
        (T / "vestibule").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    for lid in histoire.PAR_CHAP["reveil"]["lecons"]:
        if lid not in h["faits"]:
            h["faits"].append(lid)
    state["step"] = 0
    core.add_xp(state, histoire.XP_LECON_SURE * len(histoire.PAR_CHAP["reveil"]["lecons"]))
    histoire._finir_chapitre(state, histoire.PAR_CHAP["reveil"])
    state.setdefault("config", {})["sans_aide"] = True
    msg = t("plac.ok")
    core.say(state, msg, 16)
    core.terminal(state, msg)
    core.log(state, t("plac.ok.log"))


def rater(state):
    p = p_(state)
    p["etat"] = "rate"
    msg = t("plac.rate")
    core.say(state, msg, 14)
    core.terminal(state, msg)


def commande(state, args):
    """`tg placement` et `tg sansaide on|off`."""
    if args and args[0] in ("on", "off"):
        state.setdefault("config", {})["sans_aide"] = args[0] == "on"
        return t("sa.on" if args[0] == "on" else "sa.off")
    return commencer(state)


def cache(state, step):
    """Mode sans aide : la commande est cachée tant que l'enfant ne l'a pas demandée (`aide`) ou n'a pas raté 3 fois."""
    if not sans_aide(state):
        return False
    vu = state.get("sa_vu") or []
    les_id = (state.get("histoire") or {}).get("chap")
    cle = f"{les_id}:{step.get('cmd')}"
    return cle not in vu and state.get("sa_essais", {}).get(cle, 0) < 3


def masquer(state, step, texte):
    """I2 : en mode sans aide, un indice ne donne pas la commande de l'étape (tant qu'elle est cachée)."""
    if not texte or not cache(state, step) or not step.get("cmd"):
        return texte
    return texte.replace(step["cmd"], "…")


def montrer(state, step):
    """`aide` en mode sans aide : la commande de l'étape devient visible."""
    les_id = (state.get("histoire") or {}).get("chap")
    cle = f"{les_id}:{step.get('cmd')}"
    vu = state.setdefault("sa_vu", [])
    if cle not in vu:
        vu.append(cle)
        del vu[:-50]


def rate_une_fois(state, step):
    les_id = (state.get("histoire") or {}).get("chap")
    cle = f"{les_id}:{step.get('cmd')}"
    e = state.setdefault("sa_essais", {})
    e[cle] = e.get(cle, 0) + 1
    if len(e) > 50:
        for k in list(e)[:-50]:
            e.pop(k, None)
