"""Les poses de la créature du bureau et de l'île : dessinées pour les bébés de départ, calculées pour le reste.

poses.bin (fabriqué par donnees/bestiaire2/outils/poses_bureau.py, le même fichier sur Android : Poses.kt) contient,
pour chacun des 27 bébés de départ, 12 poses dessinées : marche1 à marche4, assis, dort, etire, baille, sursaut,
coeur, mange, salut (pixels indexés, une palette par espèce, une ancre par pose : le milieu et le bas du corps).

album(state) rassemble ce qu'il faut à la créature du bureau, quelle qu'elle soit :
  - bébé d'une espèce dessinée : les 12 poses (rendu lisse, la taille du dessin) ;
  - les autres stades, les autres espèces, l'œuf et la créature d'avant le bestiaire : l'animation procédurale du jeu
    (anim_auto.py : sommeil, repas, salut… ; vie.py : clignements et respiration), en gros pixels nets ;
    le teint shiny est appliqué dans les deux cas.
Une image (Cadre) est en RGBA (4 octets par pixel), avec son ancre : (ax, ay) = milieu du corps, bas des pieds.
"""
import pkgutil
import struct
import zlib

ETATS = ["marche", "assis", "dort", "etire", "baille", "sursaut", "coeur", "mange", "salut"]
# l'animation procédurale qui remplace chaque pose quand il n'y a pas de dessin (anim_auto.ANIMS)
PROCEDURALE = {"marche": "statique", "assis": "statique", "dort": "dort", "etire": "statique", "baille": "parle",
               "sursaut": "victoire", "coeur": "content", "mange": "mange", "salut": "salut"}
_DONNEES = {}


class Cadre:
    """Une image RGBA et son ancre (le point posé au sol, au milieu du corps)."""
    __slots__ = ("w", "h", "rgba", "ax", "ay", "cle")

    def __init__(self, w, h, rgba, ax, ay, cle=None):
        self.w, self.h, self.rgba, self.ax, self.ay, self.cle = w, h, rgba, ax, ay, cle

    def pixel(self, x, y):
        k = 4 * (y * self.w + x)
        return tuple(self.rgba[k:k + 4])


class Album:
    """Les images de chaque état (« marche » : plusieurs images, les autres : une ou plusieurs).
    ref : la hauteur de référence (la pose assise) ; lisse : dessin fin (mise à l'échelle douce) ou gros pixels."""

    def __init__(self, etats, ref, lisse, dessine, nom):
        self.etats, self.ref, self.lisse, self.dessine, self.nom = etats, max(1, ref), lisse, dessine, nom

    def images(self, etat):
        return self.etats.get(etat) or self.etats["assis"]

    def image(self, etat, t):
        im = self.images(etat)
        return im[t % len(im)]


# ---------------------------------------------------------------- le fichier poses.bin
def lire(octets):
    """(en-tête, blocs) d'un poses.bin ; ValueError s'il est abîmé."""
    if octets[:4] != b"TGPO":
        raise ValueError("pas un fichier de poses")
    if octets[4] != 1:
        raise ValueError("version de poses inconnue")
    n = struct.unpack(">I", octets[5:9])[0]
    import json
    tete = json.loads(octets[9:9 + n].decode("utf-8"))
    return tete, octets[9 + n:]


def donnees():
    """L'en-tête et les blocs de poses.bin (gardés), ou (None, None) si le fichier manque."""
    if "tete" not in _DONNEES:
        try:
            _DONNEES["tete"], _DONNEES["blocs"] = lire(pkgutil.get_data(__package__, "poses.bin"))
        except (OSError, TypeError, ValueError, AttributeError):
            _DONNEES["tete"], _DONNEES["blocs"] = None, None
    return _DONNEES["tete"], _DONNEES["blocs"]


def especes():
    tete, _ = donnees()
    return sorted(tete["especes"]) if tete else []


def a_des_poses(espece_id):
    tete, _ = donnees()
    return bool(tete and espece_id in tete["especes"])


def poses_indexees(espece_id):
    """{pose: (w, h, octets indexés, ax, ay)} et la palette ("#rrggbb") d'une espèce dessinée, ou None."""
    tete, blocs = donnees()
    if not tete or espece_id not in tete["especes"]:
        return None
    cle = ("idx", espece_id)
    if cle not in _DONNEES:
        e = tete["especes"][espece_id]
        brut = zlib.decompress(blocs[e["o"]:e["o"] + e["n"]])
        out, k = {}, 0
        for nom, (w, h, ax, ay) in zip(tete["poses"], e["cadres"]):
            out[nom] = (w, h, brut[k:k + w * h], ax, ay)
            k += w * h
        _DONNEES[cle] = (out, list(e["pal"]))
    return _DONNEES[cle]


def _rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def rgba_depuis_index(w, h, octets, pal):
    """Octets indexés (0 = vide) + palette "#rrggbb" -> RGBA."""
    table = [b"\x00\x00\x00\x00"] + [bytes(_rgb(c)) + b"\xff" for c in pal]
    return b"".join(table[o] if o < len(table) else table[0] for o in octets[:w * h])


# ---------------------------------------------------------------- l'album de la créature
def _teinte(pal, teinte):
    if teinte is None:
        return pal
    from . import bestiaire as B
    return [B.decaler(c, teinte) for c in pal]


def album_dessine(espece_id, teinte=None, nom=None):
    """Les 12 poses dessinées d'un bébé de départ, ou None."""
    r = poses_indexees(espece_id)
    if not r:
        return None
    idx, pal = r
    pal = _teinte(pal, teinte)
    cad = {p: Cadre(w, h, rgba_depuis_index(w, h, o, pal), ax, ay, f"{espece_id}/{p}/{teinte}")
           for p, (w, h, o, ax, ay) in idx.items()}
    etats = {"marche": [cad[f"marche{k}"] for k in (1, 2, 3, 4)]}
    for e in ETATS[1:]:
        etats[e] = [cad[e]]
    return Album(etats, cad["assis"].h, True, True, nom or espece_id)


def _cadres_toile(W, H, frames, pal, cle, ax=None, ay=None):
    pal_rgba = [b"\x00\x00\x00\x00"] + [bytes(_rgb(c)) + b"\xff" for c in pal]
    out = []
    for k, f in enumerate(frames):
        rg = b"".join(pal_rgba[o] if o < len(pal_rgba) else pal_rgba[0] for o in f[:W * H])
        out.append(Cadre(W, H, rg, W // 2 if ax is None else ax, H - 2 if ay is None else ay, f"{cle}/{k}"))
    return out


def album_procedural(e, stade, teinte=None, vid="classique"):
    """L'animation procédurale du jeu pour une espèce du bestiaire à un stade (« bebe », « ado »…), ou None."""
    from . import anim_auto
    etats, vus, ref = {}, {}, 1
    for etat in ETATS:
        nom = PROCEDURALE[etat]
        if nom not in vus:
            r = anim_auto.toiles(e, stade, vid, nom, teinte)
            if r is None:
                return None
            W, H, fr, pal = r
            if nom == "statique" and len(fr) > 16:
                fr = fr[::2]                                  # 32 images de vie suffisent au bureau
            vus[nom] = _cadres_toile(W, H, fr, pal, f"{e['id']}/{stade}/{nom}/{teinte}")
        etats[etat] = vus[nom]
    img = anim_auto.B.image(e, stade, vid)
    if img:
        ref = img[1]
    return Album(etats, ref, False, False, e["id"])


def album_lignes(rows, pal_car, cle):
    """Une image en caractères (sprites.py : la créature d'avant le bestiaire, l'œuf) -> album sans animation dessinée
    (la vie de vie.py si elle trouve les yeux, sinon l'image fixe)."""
    from . import sprites, vie
    w = max(len(r) for r in rows)
    h = len(rows)
    cars = sorted({c for r in rows for c in r if pal_car.get(c) is not None})
    pal = ["#%02x%02x%02x" % sprites.x256(pal_car[c]) for c in cars]
    num = {c: k + 1 for k, c in enumerate(cars)}
    o = bytes(num.get(r[x], 0) if x < len(r) else 0 for r in rows for x in range(w))
    a = vie.analyse_gardee(w, h, o, [int(c[1:], 16) for c in pal])
    if a is not None:
        fr = []
        for t in range(0, vie.CYCLE, 2):
            W2, H2, img = vie.image(a, t)
            fr.append(img)
        cad = _cadres_toile(W2, H2, fr, pal, cle, ax=W2 // 2, ay=H2)
    else:
        cad = _cadres_toile(w, h, [o], pal, cle, ax=w // 2, ay=h)
    return Album({e: cad for e in ETATS}, h, False, False, cle)


def album(state):
    """L'album de la créature d'une partie (voir le haut du fichier)."""
    from . import core, sprites
    st = core.stage(core.level(state["xp"]))
    teinte = 0.5 if state.get("shiny") else None
    e = sprites.espece_compagnon(state)
    if e and st == 1:
        a = album_dessine(e["id"], teinte, state.get("name"))
        if a:
            return a
    if e and st >= 1:
        a = album_procedural(e, sprites.STADE_ESPECE.get(st, "adulte"), teinte)
        if a:
            return a
    rows = sprites.get_sprite(state)
    pal = sprites.palette(state)
    return album_lignes(rows, pal, f"lignes/{st}/{state.get('espece_compagnon')}")


def album_espece(espece_id, stade="bebe", shiny=False):
    """L'album d'une bestiole de l'équipe (choisie pour le bureau) : dessinée au stade bébé si possible."""
    from . import bestiaire as B
    teinte = 0.5 if shiny else None
    if stade == "bebe":
        a = album_dessine(espece_id, teinte)
        if a:
            return a
    e = B.espece(espece_id)
    return album_procedural(e, stade, teinte) if e else None
