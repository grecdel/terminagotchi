"""La carte de visite de la créature (idée 58, maquette validée le 3 novembre).

    tg carte visite [sansnom]   une belle image (format carte à jouer, 750 × 1050) enregistrée dans le terrain de jeu :
                                la créature en grand, son nom, espèce · stade · type, niveau, jours, commandes, ses goûts
                                préférés (les commandes qu'elle a le plus mangées), la date d'éclosion, ses titres en
                                petit, le décor de racines à circuits verts, la licence (CC BY-NC-SA 4.0) en bas.
Jamais le prénom ni le pseudo de l'enfant ; `sansnom` cache aussi le nom de la créature. Le jeu n'envoie rien : c'est
l'enfant (ou un adulte) qui partage. Dessinée par le jeu (PIL), même dessin sur Android (CarteVisite.kt, Canvas) ;
mêmes contenus vérifiés par les vecteurs donnees/classe/vecteurs_carte.json (le choix des goûts, les jours).
`tg carte` (sans « visite ») reste la carte du monde.
"""
import time

from . import core
from .langue import sans_marques, t

W, H = 750, 1050
LICENCE = "terminagotchi · image CC BY-NC-SA 4.0"


# ---------------------------------------------------------------- le contenu (pur : mêmes vecteurs que CarteVisite.kt)
def preferes(compteurs, ordre, n=4):
    """Les n goûts préférés : les plus mangés d'abord ; à égalité, le premier goûté. Sans compteurs : les premiers."""
    rang = {c: i for i, c in enumerate(ordre or [])}
    cles = [c for c in (compteurs or {}) if isinstance(compteurs[c], int) and compteurs[c] > 0]
    if not cles:
        return list(ordre or [])[:n]
    return sorted(cles, key=lambda c: (-compteurs[c], rang.get(c, 10 ** 6), c))[:n]


def jours(ne, maintenant):
    """Le nombre de jours depuis l'éclosion (le jour même compte : 1)."""
    if not ne:
        return 0
    return max(1, int((maintenant - ne) // 86400) + 1)


def date_eclos(ne):
    return time.strftime("%d/%m/%Y", time.localtime(ne)) if ne else ""


def contenu(state, avec_nom=True, maintenant=None):
    from . import bestiaire, entrainement
    now = maintenant or time.time()
    lvl = core.level(state.get("xp", 0))
    e = bestiaire.espece(state.get("espece_compagnon")) if state.get("espece_compagnon") else None
    titres = []
    try:
        titres = [(sans_marques(x), c) for _i, x, c in entrainement.titres(state)][:3]
    except Exception:                                # noqa: BLE001 — une carte sans titres plutôt que pas de carte
        titres = []
    return {"nom": state.get("name", "") if avec_nom else "",
            "espece": e["nom"] if e else "", "stade": sans_marques(t(f"stade.{core.stage(lvl)}")),
            "type": e.get("famille", "") if e else "", "niveau": lvl,
            "jours": jours(state.get("born"), now), "commandes": int(state.get("total", 0)),
            "gouts": preferes(state.get("gouts"), state.get("seen")), "eclos": date_eclos(state.get("born")),
            "titres": titres}


# ---------------------------------------------------------------- le dessin (liste de dessin de l'espace)
def scene(c, album, t_=0.0):
    from . import bureau_vie as V
    from . import espace_scene as S
    S.CONF.update(facile=False, calme=True, formes=False, taille=100)
    L = [("rect", 0, 0, W, H, (5, 7, 10, 255)),
         ("rrect", 18, 18, W - 36, H - 36, 26, S.PANNEAU, S._a(S.VERT, 200), 3)]
    # le décor : racines à circuits verts (dessinées, déterministes)
    for i in range(14):
        x = 40 + (i * 53) % (W - 80)
        y0 = H - 40 - (i * 37) % 260
        L.append(("ligne", x, H - 24, x, y0, S._a(S.VERT, 40), 1.4, None))
        L.append(("ligne", x, y0, x + (18 if i % 2 else -18), y0 - 18, S._a(S.VERT, 40), 1.4, None))
        L.append(("ellipse", x + (18 if i % 2 else -18), y0 - 18, 2.6, 2.6, S._a(S.VERT, 90)))
    L.append(("texte", W / 2, 62, S.espace_lettres("TERMINAGOTCHI"), 15, S.VERT, True, "c", False))
    bx, by, bw, bh = 70, 92, W - 140, 400
    L.append(("rrect", bx, by, bw, bh, 20, (13, 16, 22, 255), S.BORD_FORT, 1))
    L.append(("lueur", W / 2, by + bh * 0.58, bh * 0.5, S._a(S.VERT, 34)))
    if album:
        haut_c = 300
        e = haut_c / max(1, album.ref)
        if not album.lisse:
            e = max(1.0, float(int(e)))
        ref = album.images("assis")[0]
        L.append(("ellipse", W / 2, by + bh - 40, ref.w * e * 0.32, 10, (0, 0, 0, 100)))
        L.append(("imgt", album.image("assis", int(t_ * V.IPS)), W / 2, by + bh - 42, e, False, album.lisse, 1.0, 1.0,
                  0.0, 1.0))
    y = by + bh + 70
    if c["nom"]:
        L.append(("texte", W / 2, y, S.court(c["nom"], W - 120, 44), 44, S.TEXTE, True, "c", False))
        y += 48
    sous = " · ".join(x for x in (c["espece"], c["stade"], c["type"]) if x)
    L.append(("texte", W / 2, y, S.court(sous, W - 120, 19), 19, S.DOUX, False, "c", False))
    y += 52
    cw, gap = 180, 18
    x0 = W / 2 - (3 * cw + 2 * gap) / 2
    for i, (v, lib, col) in enumerate(((c["niveau"], t("cv.niveau"), S.JAUNE), (c["jours"], t("cv.jours"), S.CYAN),
                                       (c["commandes"], t("cv.commandes"), S.VERT))):
        xx = x0 + i * (cw + gap)
        L.append(("rrect", xx, y, cw, 86, 14, S._a(col, 20), S._a(col, 170), 1.5))
        L.append(("texte", xx + cw / 2, y + 34, str(v), 30, col, True, "c", False))
        L.append(("texte", xx + cw / 2, y + 66, lib, 14, S.DOUX, False, "c", False))
    y += 124
    if c["gouts"]:
        L.append(("texte", 80, y, t("cv.gouts"), 16, S.TEXTE, True, "g", False))
    xx = 80 + S.lt(t("cv.gouts"), 16) + 20
    for g in c["gouts"]:
        gw = S.lt(g, 16, True) + 24
        if xx + gw > W - 70:
            break
        L.append(("rrect", xx, y - 16, gw, 32, 9, S._a(S.VERT, 22), S._a(S.VERT, 160), 1.2))
        L.append(("texte", xx + gw / 2, y, g, 16, S.VERT, True, "c", True))
        xx += gw + 10
    y += 48
    if c["titres"]:
        xx = 80
        for txt, col in c["titres"]:
            rgb = S.JAUNE if col == "arc" else tuple(int(col[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
            w_ = S.chip(L, xx, y, S.court(txt, 260, 13), rgb, 13) if xx < W - 200 else 0
            xx += w_ + 8
        y += 40
    if c["eclos"]:
        L.append(("texte", 80, y, t("cv.eclos", date=c["eclos"]), 15, S.DOUX, False, "g", False))
    L.append(("texte", W / 2, H - 46, LICENCE, 13, S.PALE, False, "c", False))
    return L


def image(state, avec_nom=True):
    """L'image PIL de la carte (RGB)."""
    from . import espace_scene as S
    from . import poses
    try:
        album = poses.album(state)
    except Exception:                                # noqa: BLE001
        album = None
    return S.vers_pil(scene(contenu(state, avec_nom), album), (W, H)).convert("RGB")


def commande(args):
    """tg carte visite [sansnom] : l'image dans le terrain de jeu (rien n'est envoyé)."""
    st = core.load()
    if st is None:
        return t("cv.pas_de_partie")
    core.migrate(st)
    avec_nom = not any(a.lower() in ("sansnom", "sans-nom", "noname", "anonyme") for a in args)
    try:
        im = image(st, avec_nom)
    except ImportError:
        return t("cv.sans_pil")
    core.TERRAIN.mkdir(parents=True, exist_ok=True)
    p = core.TERRAIN / "ma_carte_de_visite.png"
    im.save(p, "PNG")
    return t("cv.ok", chemin=str(p)) + "\n" + t("cv.partage")

