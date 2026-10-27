"""Le guide : la bestiole qui accompagne l'enfant (les mêmes règles que Guide.kt sur Android).

Au début, le guide est le compagnon sorti de l'œuf ; ensuite, c'est la bestiole que l'enfant met en tête
de son équipe (`tg guide <nom>`, `tg equipe guide <nom>`, ou `tg troupe <nom>`). Changer de guide compte,
pour quatre raisons (jamais un piège, jamais une punition) :

1. Talents par type : chaque type aide une famille de commandes (TALENTS). Avec le bon guide :
   - une astuce de plus dans les exercices de la salle d'entraînement de cette famille ;
   - +25 % d'XP (arrondi au-dessus, au moins +1) sur ces exercices ;
   - +1 XP par commande de sa famille tapée à la main ;
   - de temps en temps (au plus toutes les 15 minutes), une astuce dans la bulle quand l'enfant tape une
     commande de sa famille.
   9 types pour 8 familles : l'Ombre a le talent « passages secrets » (ls -a, fichiers cachés « .xxx »).
2. Régions gardées (biome/<type>/ dans le terrain) : pour ENTRER, il faut une bestiole de ce type dans
   l'équipe (le compagnon compte) ; pour AGRANDIR (mkdir, touch, cp, mv, rm dans la région), il faut un
   GUIDE de ce type. Le jeu ne bloque rien (ce sont de vrais dossiers) : un message gentil explique quoi
   faire, au plus une fois toutes les 10 minutes par région. region_ouverte() / peut_agrandir() servent
   aussi à la carte.
3. Combats et épreuves à type : TABLE (comme pierre-feuille-ciseaux). Ton coup fait ×1.5 contre un type
   faible (arrondi : 1 → 2, 2 → 3), ×0.67 contre un type fort (au moins 1 cœur) ; le monstre te touche un peu
   plus souvent (+0.15) s'il est fort contre toi, un peu moins (−0.15) si tu es fort contre lui.
   L'Ombre n'est ni forte ni faible… sauf la nuit (20 h – 7 h) où elle est forte contre tous.
   Chaque jour, l'épreuve du jour annonce un type (type_du_jour) : un défi éclair réussi avec un guide fort
   contre ce type rapporte +5 XP.
4. Fatigue et envies : le guide se fatigue en travaillant (+0.5 par commande tapée, de 0 à 100) ; au-delà
   de 30 (« en pleine forme » avant), sa fatigue use plus vite le sommeil et le jeu (jusqu'au double de l'usure
   normale à 100). Sur le banc, une bestiole
   se repose (−20 par heure) ; le guide se repose aussi quand on ne joue pas (−10 par heure après 10 minutes).
   Une bestiole qui n'a pas guidé depuis 2 jours a « envie de sortir » (💭, une bulle au plus toutes les
   6 heures). Pas de mort, pas de punition, pas de série à tenir.

Le type d'une bestiole : celui de sa variante (biomes.json, recopie de donnees/biomes.json, même règle que
donnees/verifier_biomes.py). Le compagnon reçoit un type une fois pour toutes : celui de son œuf (une nouvelle partie, oeufs.py), sinon celui de sa forme
(Intelligence → Machine, Force → Feu, Agilité → Ciel, Endurance → Roche) s'il en a déjà une, sinon
TYPES[somme des codes des lettres de son nom % 9].

Sauvegarde : state["guide"] = {"id": "compagnon" | id d'une bestiole, "type_c": type du compagnon,
"fatigue": {id: 0..100}, "depuis": {id: dernière fois guide (s)}, "t": dernier calcul, "cmd_t": dernière
commande, "astuce_t", "sortie_t", "fatigue_dit", "region_t": {type: s}, "annonce"}.
Une ancienne partie : le compagnon est le guide. Tout est local (rien n'est envoyé : anti-triche intact).
Tests : pc/outils/test_guide.py (PC), tests/jvm/Guide.kt (Android).
"""
import datetime
import json
import math
import pkgutil
import sys
import time

from . import bestiaire as B
from . import core
from .langue import t
from .plateforme import BOLD, DIM, RESET, C, fg

TYPES = ("feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")
ICONES = {"feu": "🔥", "eau": "💧", "glace": "🧊", "plante": "🌿", "roche": "🗻", "ciel": "⚡", "ombre": "🌙",
          "machine": "🔩", "poison": "🧪"}
COULEURS = {"feu": 202, "eau": 33, "glace": 117, "plante": 70, "roche": 180, "ciel": 229, "ombre": 99,
            "machine": 248, "poison": 148}
# type → talent (une famille de la salle d'entraînement, ou « secrets » pour l'Ombre)
TALENTS = {"ciel": "explorateur", "plante": "batisseur", "roche": "demenageur", "feu": "nettoyeur",
           "glace": "lecteur", "poison": "detective", "eau": "plombier", "machine": "cuisinier", "ombre": "secrets"}
CMDS_TALENT = {
    "explorateur": {"cd", "ls", "pwd", "tree", "dir", "gci", "get-childitem", "set-location", "sl", "get-location"},
    "batisseur": {"mkdir", "md", "touch", "new-item", "ni"},
    "demenageur": {"cp", "mv", "copy", "move", "copy-item", "move-item", "ren", "rename-item"},
    "nettoyeur": {"rm", "rmdir", "rd", "del", "remove-item"},
    "lecteur": {"cat", "head", "tail", "less", "more", "type", "get-content", "gc"},
    "detective": {"grep", "find", "select-string", "sls"},
    "cuisinier": {"sh", "bash", "chmod", "zsh"},
}
AFFICHE_TALENT = {"explorateur": "cd ls pwd", "batisseur": "mkdir touch", "demenageur": "cp mv",
                  "nettoyeur": "rm rmdir", "lecteur": "cat head tail", "detective": "grep find",
                  "plombier": "| > >>", "cuisinier": "sh chmod", "secrets": "ls -a"}
# l'astuce de chaque talent : (commande Unix, commande Windows)
ASTUCES = {"explorateur": ("cd -", "cd -"), "batisseur": ("mkdir -p a/b/c", "mkdir a/b/c"),
           "demenageur": ("cp -r", "Copy-Item -Recurse"), "nettoyeur": ("rm -i", "Remove-Item -Confirm"),
           "lecteur": ("head -n 3", "Get-Content -Head 3"), "detective": ("grep -i", "Select-String"),
           "plombier": ("ls | wc -l", "dir | Measure-Object"), "cuisinier": ("chmod +x", "Unblock-File"),
           "secrets": ("ls -a", "dir -Force")}
# qui est fort contre qui (×1.5) ; l'inverse est faible (×0.67) ; l'Ombre : neutre, forte contre tous la nuit
TABLE = {"feu": ("plante", "glace"), "eau": ("feu", "roche"), "plante": ("eau", "roche"), "glace": ("plante", "ciel"),
         "roche": ("feu", "ciel"), "ciel": ("eau", "machine"), "machine": ("glace", "poison"),
         "poison": ("plante", "eau"), "ombre": ()}
FORT, FAIBLE = 1.5, 0.67
BONUS_TALENT = 0.25
BONUS_DEFI = 5
TYPE_BRANCHE = {"Intelligence": "machine", "Force": "feu", "Agilité": "ciel", "Endurance": "roche"}
FATIGUE_COMMANDE = 0.5
REPOS_BANC = 20.0                   # par heure
REPOS_GUIDE = 10.0                  # par heure, après PAUSE sans commande
PAUSE = 600
FATIGUE_ALERTE = 70.0
EN_FORME = 30.0                     # sous ce seuil, la fatigue ne change rien
FATIGUE_DELAI = 3600
ASTUCE_DELAI = 15 * 60
SORTIE_APRES = 2 * 24 * 3600
SORTIE_DELAI = 6 * 3600
REGION_DELAI = 600
SOIR, MATIN = 20, 7
CHANGE = {"mkdir", "md", "touch", "new-item", "ni", "cp", "copy", "copy-item", "mv", "move", "move-item", "rm",
          "rmdir", "rd", "del", "remove-item"}
_BIOMES = None


# ---------------------------------------------------------------- les types
def biomes():
    global _BIOMES
    if _BIOMES is None:
        try:
            _BIOMES = json.loads(pkgutil.get_data(__package__, "biomes.json").decode("utf-8"))
        except (OSError, TypeError, ValueError):
            _BIOMES = {"types": [], "classique_par_famille": {}, "classique_par_espece": {}}
    return _BIOMES


def type_de(espece, variante="classique"):
    """Le type d'une espèce dans une variante (même règle que donnees/verifier_biomes.py)."""
    e = B.espece(espece) if isinstance(espece, str) else espece
    if not e:
        return "eau"
    b = biomes()
    if variante and variante != "classique":
        for x in b["types"]:
            if variante in x["habitats"]:
                return x["id"]
    return b["classique_par_espece"].get(e["id"]) or b["classique_par_famille"].get(e["famille"]) or "eau"


def type_ind(ind):
    return type_de(ind.get("espece"), ind.get("variante", "classique"))


def nom_type(ty):
    return t("type.nom." + ty)


def etiquette(ty):
    return f"{ICONES[ty]} {nom_type(ty)}"


def efficacite(att, defe, nuit=None):
    """×1.5, ×0.67 ou ×1 : la force du type att contre le type defe."""
    if att == "ombre":
        if nuit is None:
            h = time.localtime().tm_hour
            nuit = h >= SOIR or h < MATIN
        return FORT if nuit and defe != "ombre" else 1.0
    if defe in TABLE.get(att, ()):
        return FORT
    if att in TABLE.get(defe, ()):
        return FAIBLE
    return 1.0


def degats(n, mult):
    """Les cœurs d'un coup, avec la force du type (1 → 2 et 2 → 3 si fort ; au moins 1 si faible)."""
    if mult == 1.0:
        return n
    return max(1, int(math.floor(n * mult + 0.5)))


def forts_contre(ty):
    """Les types forts contre ty (sans l'Ombre, qui ne l'est que la nuit)."""
    return [a for a in TYPES if ty in TABLE[a]]


def jour(d=None):
    d = d or datetime.date.today()
    return (d - datetime.date(1970, 1, 1)).days


def type_du_jour(d=None):
    return TYPES[jour(d) % len(TYPES)]


# ---------------------------------------------------------------- l'état
def type_compagnon_initial(state):
    if state.get("oeuf_type") in TYPES:                 # une nouvelle partie : le type de son œuf (oeufs.py)
        return state["oeuf_type"]
    if state.get("branch") in TYPE_BRANCHE:
        return TYPE_BRANCHE[state["branch"]]
    return TYPES[sum(ord(c) for c in state.get("name", "")) % len(TYPES)]


def g_(state):
    """L'état du guide (une ancienne partie : le compagnon est le guide)."""
    g = state.get("guide")
    if not isinstance(g, dict):
        g = state["guide"] = {"id": "compagnon"}
    now = time.time()
    for k, v in {"id": "compagnon", "fatigue": {}, "depuis": {}, "t": now, "cmd_t": 0, "astuce_t": 0, "sortie_t": now,
                 "fatigue_dit": 0, "region_t": {}, "annonce": False}.items():
        g.setdefault(k, v)
    if g.get("type_c") not in TYPES:
        g["type_c"] = type_compagnon_initial(state)
    if g["id"] != "compagnon" and not _capture(state, g["id"]):
        g["id"] = "compagnon"                           # la bestiole n'est plus là : le compagnon reprend
    return g


def _capture(state, i):
    return next((c for c in state.get("captures", []) if c.get("id") == i), None)


def membres(state):
    """L'équipe : le compagnon d'abord, puis les bestioles (les plus récentes d'abord) : [(id, nom, type, ind)]."""
    g = g_(state)
    out = [("compagnon", state.get("name", "?"), g["type_c"], None)]
    for c in reversed(state.get("captures", [])):
        if B.espece(c.get("espece")):
            out.append((c["id"], c["espece"], type_ind(c), c))
    return out


def actuel(state):
    """(id, nom, type, ind) du guide."""
    g = g_(state)
    return next((m for m in membres(state) if m[0] == g["id"]), membres(state)[0])


def types_equipe(state):
    return {m[2] for m in membres(state)}


def talent(state):
    return TALENTS[actuel(state)[2]]


def region_ouverte(state, ty):
    """On peut entrer dans la région ty : une bestiole de ce type est dans l'équipe."""
    return ty in types_equipe(state)


def peut_agrandir(state, ty):
    """On peut agrandir la région ty : le guide est de ce type."""
    return actuel(state)[2] == ty


def fatigue(state, i=None):
    g = g_(state)
    return float(g["fatigue"].get(i or g["id"], 0.0))


def _depuis(state, m):
    g = g_(state)
    if m[0] in g["depuis"]:
        return g["depuis"][m[0]]
    if m[3] is not None:
        return (m[3].get("date") or 0) / 1000 or time.time()
    return state.get("born") or time.time()


def envie_de_sortir(state, m, now=None):
    now = now or time.time()
    return m[0] != g_(state)["id"] and now - _depuis(state, m) >= SORTIE_APRES


def cmd_guide(nom=None):
    return "tg guide" + (f" {nom.lower()}" if nom else " <nom>")


def cmd_types():
    return "tg types"


# ---------------------------------------------------------------- changer de guide
def trouver(state, nom):
    from .bestiaire import _simple
    n = _simple((nom or "").strip())
    if not n:
        return None
    if n in ("compagnon", _simple(state.get("name", "")), "0"):
        return membres(state)[0]
    e = B.espece(nom)
    if e:
        return next((m for m in membres(state)[1:] if m[1] == e["nom"]), None)
    return None


def choisir(state, nom, silencieux=False):
    """Met la bestiole nom en tête de l'équipe. Renvoie (texte, ind changé ou None)."""
    m = trouver(state, nom)
    if not m:
        return t("guide.inconnu", nom=nom, cmd="tg guide"), None
    g = g_(state)
    avant = actuel(state)
    if m[0] == avant[0]:
        return t("guide.deja", nom=m[1]), None
    now = time.time()
    g["depuis"][avant[0]] = now
    g["depuis"][m[0]] = now
    g["id"] = m[0]
    if m[3] is not None:
        state["active"] = m[0]                   # le guide est aussi la bestiole active (elle grandit, elle combat)
    g["fatigue_dit"] = 0
    core.animer(state, "salut")
    if not silencieux:
        core.log(state, "🐾 " + t("guide.change.log", nom=m[1], type=nom_type(m[2])))
    tal = TALENTS[m[2]]
    texte = (t("guide.change", ancien=avant[1], nom=m[1], icone=ICONES[m[2]], type=nom_type(m[2])) + "\n"
             + t("guide.change.talent", talent=t("guide.talent." + tal), aide=aide_talent(tal)))
    return texte, m[3]


def aide_talent(tal):
    return t("guide.talent.secrets.aide" if tal == "secrets" else "guide.talent.aide", cmds=AFFICHE_TALENT[tal])


def astuce(tal):
    u, w = ASTUCES[tal]
    return t("guide.astuce." + tal, cmd=C(u, w))


def suivre_choix_equipe(state, ind):
    """`tg troupe <nom>` met aussi cette bestiole en tête : elle devient le guide."""
    g = g_(state)
    if ind and g["id"] != ind.get("id"):
        now = time.time()
        g["depuis"][g["id"]] = now
        g["depuis"][ind["id"]] = now
        g["id"] = ind["id"]


# ---------------------------------------------------------------- talents
def _morceaux(ligne):
    import re
    return [x.strip() for x in re.split(r"\s*(?:&&|\|\||;)\s*", ligne.strip()) if x.strip()]


def du_talent(tal, ligne):
    """La ligne tapée utilise-t-elle une commande de ce talent ?"""
    from . import maison
    if tal == "plombier":
        return any(s in ligne for s in ("|", ">"))
    for m in _morceaux(ligne):
        mot = core.first_word(m) or ""
        if tal == "secrets":
            if maison.voit_caches(m) or any(x.startswith(".") and x not in (".", "..") and not x.startswith(("./", "../", ".\\"))
                                             for x in m.split()[1:]):
                return True
        elif tal == "cuisinier" and (mot in CMDS_TALENT[tal] or mot.startswith(("./", ".\\"))):
            return True
        elif mot in CMDS_TALENT.get(tal, ()):
            return True
    return False


def indice_exercice(state, famille):
    """Une ligne d'astuce en plus dans un exercice de la famille du talent du guide (sinon None)."""
    m = actuel(state)
    if TALENTS[m[2]] != famille:
        return None
    return t("guide.ent.indice", icone=ICONES[m[2]], nom=m[1], talent=t("guide.talent." + famille), astuce=astuce(famille))


def bonus_exercice(state, famille, xp):
    """+25 % d'XP sur un exercice de la famille du talent du guide : (xp en plus, texte) ou (0, None)."""
    m = actuel(state)
    if TALENTS[m[2]] != famille:
        return 0, None
    n = max(1, math.ceil(xp * BONUS_TALENT))
    core.add_xp(state, n)
    return n, t("guide.ent.bonus", icone=ICONES[m[2]], nom=m[1], xp=n)


# ---------------------------------------------------------------- combats et épreuve du jour
def debut_combat(state, ind, monstre, variante):
    """Les types du combat : (type de ta bestiole, type du monstre, texte)."""
    tm, tl = type_ind(ind), type_de(monstre, variante)
    m = efficacite(tm, tl)
    effet = t("guide.combat.fort") if m > 1 else t("guide.combat.faible") if efficacite(tl, tm) > 1 else t("guide.combat.neutre")
    texte = t("guide.combat.types", nom=ind["espece"], type_moi=etiquette(tm), monstre=monstre, type_lui=etiquette(tl), effet=effet)
    if tm == "ombre" and m > 1:
        texte += " " + t("guide.combat.nuit")
    return tm, tl, texte


def apres_defi(state):
    """Défi éclair réussi : si le guide est fort contre le type du jour, +5 XP."""
    m = actuel(state)
    ty = type_du_jour()
    if efficacite(m[2], ty) <= 1:
        return None
    core.add_xp(state, BONUS_DEFI)
    texte = t("guide.defi.bonus", icone=ICONES[m[2]], nom=m[1], type=nom_type(ty), xp=BONUS_DEFI)
    core.log(state, texte)
    core.say(state, texte, 8)
    return texte


def annonce_defi(state):
    ty = type_du_jour()
    core.say(state, t("guide.defi.annonce", type=etiquette(ty), forts=", ".join(etiquette(x) for x in forts_contre(ty))), 12)


# ---------------------------------------------------------------- le tour de jeu
def usure_en_plus(f):
    """En pleine forme (fatigue < 30) : rien ; ensuite l'usure du sommeil et du jeu grandit, jusqu'au double à 100."""
    return max(0.0, f - EN_FORME) / (100 - EN_FORME)


def _usure(state, g, now):
    """Le temps qui passe : le banc repose, le guide se repose quand on ne joue pas."""
    dt = max(0.0, min(now - g.get("t", now), 7 * 24 * 3600))
    g["t"] = now
    if dt <= 0:
        return
    for m in membres(state):
        f = g["fatigue"].get(m[0], 0.0)
        if not f:
            continue
        if m[0] != g["id"]:
            f -= REPOS_BANC * dt / 3600
        else:
            debut = max(now - dt, g.get("cmd_t", 0) + PAUSE)
            if now > debut:
                f -= REPOS_GUIDE * (now - debut) / 3600
        g["fatigue"][m[0]] = round(max(0.0, f), 3)


def _region(state, lignes, g, now):
    from . import maison
    cwd = maison.ici(state)
    r = maison.rel(cwd) if cwd else None
    parts = (r or "").split("/")
    ty = parts[1] if len(parts) >= 2 and parts[0] == "biome" and parts[1] in TYPES else None
    if not ty:
        return None
    if now - g["region_t"].get(ty, 0) < REGION_DELAI:
        return None
    if not region_ouverte(state, ty):
        g["region_t"][ty] = now
        texte = t("guide.region.fermee", type=etiquette(ty))
    elif not peut_agrandir(state, ty) and any((core.first_word(x) or "") in CHANGE for l in lignes for x in _morceaux(l)):
        g["region_t"][ty] = now
        qui = next((m for m in membres(state) if m[2] == ty), None)
        texte = t("guide.region.guide", type=etiquette(ty), cmd=cmd_guide(qui[1] if qui else None))
    else:
        return None
    core.say(state, texte, 12)
    return texte


def tick(state, lignes):
    """À chaque étape de jeu (app.boucle_jeu), après les envies."""
    g = g_(state)
    now = time.time()
    _usure(state, g, now)
    tapees = [l for l in lignes if not core.est_colle(l) and core.first_word(l)]
    m = actuel(state)
    tal = TALENTS[m[2]]
    if tapees:
        g["cmd_t"] = now
        from . import envies
        e = envies.e_(state)
        f = fatigue(state)
        for l in tapees:
            for k in ("sommeil", "jeu"):
                n = envies.SOMMEIL_SOIR if k == "sommeil" and envies.soir() else envies.PAR_COMMANDE[k]
                e["v"][k] = max(0.0, e["v"][k] - n * usure_en_plus(f))
            f = min(100.0, f + FATIGUE_COMMANDE)
        g["fatigue"][m[0]] = round(f, 3)
        bonus = sum(1 for l in tapees if du_talent(tal, l))
        from . import intro
        if bonus:
            core.add_xp(state, bonus)
            if now - g["astuce_t"] >= ASTUCE_DELAI and intro.ouvert(state, "equipe"):
                g["astuce_t"] = now
                core.say(state, f"{ICONES[m[2]]} {m[1]} : " + astuce(tal), 10)
        if f >= FATIGUE_ALERTE and now - g["fatigue_dit"] >= FATIGUE_DELAI and len(membres(state)) > 1:
            g["fatigue_dit"] = now
            core.say(state, t("guide.fatigue.dit", nom=m[1], cmd=cmd_guide()), 12)
        if len(membres(state)) > 1 and not g["annonce"]:
            g["annonce"] = True
            core.say(state, t("guide.premiere", cmd="tg guide", cmd2=cmd_guide()), 14)
        elif now - g["sortie_t"] >= SORTIE_DELAI:
            veut = [x for x in membres(state) if envie_de_sortir(state, x, now)]
            if veut:
                g["sortie_t"] = now
                x = veut[int(now) % len(veut)]
                core.say(state, t("guide.sortie.dit", nom=x[1], cmd=cmd_guide(x[1])), 12)
    from . import intro
    if intro.ouvert(state, "biomes"):               # les régions gardées : après leur présentation (intro.json)
        _region(state, tapees, g, now)


# ---------------------------------------------------------------- écrans
def barre(v, n=8):
    k = max(0, min(n, int(v / 100 * n + 0.5)))
    return "▰" * k + "▱" * (n - k)


def etat_fatigue(v):
    return t("guide.fatigue.repose" if v < EN_FORME else "guide.fatigue.ok" if v < FATIGUE_ALERTE else "guide.fatigue.fatigue")


def ligne_equipe(state):
    """La ligne « 🧭 Guide : … » de l'écran d'équipe."""
    m = actuel(state)
    return t("guide.equipe", icone=ICONES[m[2]], nom=m[1], type=nom_type(m[2]), cmd=cmd_guide())


def ecran(state):
    """tg guide : le guide, son talent, sa fatigue, les régions ouvertes, l'épreuve du jour, l'équipe."""
    from .langue import envelopper
    g = g_(state)
    m = actuel(state)
    tal = TALENTS[m[2]]
    out = [f" {fg(213)}{BOLD}" + t("guide.ecran.titre", icone=ICONES[m[2]], nom=m[1], type=nom_type(m[2])) + RESET, ""]
    for l in envelopper(t("guide.ecran.talent", talent=t("guide.talent." + tal), aide=aide_talent(tal)), 76):
        out.append(" " + l)
    f = fatigue(state)
    out.append(" " + t("guide.ecran.fatigue", barre=barre(f), etat=etat_fatigue(f)))
    ouvertes = [ty for ty in TYPES if region_ouverte(state, ty)]
    out.append(" " + t("guide.ecran.regions", liste=" ".join(ICONES[x] for x in ouvertes)))
    ty = type_du_jour()
    out.append(" " + t("guide.ecran.jour", type=etiquette(ty), forts=", ".join(etiquette(x) for x in forts_contre(ty))))
    out.append("")
    now = time.time()
    for x in membres(state):
        marque = f"{fg(226)}🧭{RESET}" if x[0] == g["id"] else "  "
        sortie = "  " + t("guide.ecran.sortir") if envie_de_sortir(state, x, now) else ""
        out.append(f" {marque} {fg(COULEURS[x[2]])}{ICONES[x[2]]} {x[1]}{RESET} {DIM}· {nom_type(x[2])} · "
                   f"{t('guide.talent.' + TALENTS[x[2]])} · {barre(fatigue(state, x[0]), 5)}{RESET}{sortie}")
    out.append("")
    for l in envelopper(t("guide.ecran.pied", cmd=cmd_guide(), types=cmd_types()), 76):
        out.append(f" {DIM}{l}{RESET}")
    return out


def ecran_types(state=None):
    """tg types : la table des types expliquée aux enfants, et les talents."""
    out = [f" {fg(213)}{BOLD}" + t("types.titre") + RESET, " " + t("types.intro"), ""]
    for ty in TYPES:
        if ty == "ombre":
            continue
        out.append(" " + t("types.ligne", icone=ICONES[ty], type=nom_type(ty),
                           liste=", ".join(etiquette(x) for x in TABLE[ty])))
    out.append(" " + t("types.ombre"))
    out += ["", f" {BOLD}" + t("types.talents") + RESET]
    for ty in TYPES:
        tal = TALENTS[ty]
        out.append(f" {ICONES[ty]} {nom_type(ty)} → {t('guide.talent.' + tal)} {DIM}({AFFICHE_TALENT[tal]}){RESET}")
    out += ["", f" {DIM}" + t("types.pied", cmd=cmd_guide()) + RESET]
    return out


def animation_changement(ind, state):
    """Une courte animation quand le guide change (dans un vrai terminal seulement)."""
    if not sys.stdout.isatty():
        return
    try:
        if ind is not None:
            from . import equipe
            r = equipe.animation(ind, "salut")
            if r:
                equipe.derouler(r[0], r[1], 1)
                return
        for x in ("  🐾 ·", "  🐾 · ✨", "  🐾 · ✨ · 🧭"):
            sys.stdout.write("\r" + x)
            sys.stdout.flush()
            time.sleep(0.18)
        sys.stdout.write("\n")
    except Exception:
        pass
