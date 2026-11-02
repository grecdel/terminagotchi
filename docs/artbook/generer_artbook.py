"""Fabrique l'artbook de Terminagotchi en PDF (brouillon reproductible).

    python3 docs/artbook/generer_artbook.py                 (depuis la racine du dépôt ; demande reportlab et Pillow)
    python3 docs/artbook/generer_artbook.py --apercu DOSSIER   (+ quelques pages en PNG, demande pdftoppm)

Contenu : l'histoire du Terminaworld, la Racine et les lieux du système, la carte du monde en double page, les 9
biomes et leurs habitants, chaque monde (son rôle, son gardien), puis un poster par créature du bestiaire (ses 5
stades, ses variantes) et le légendaire secret. Les textes sont écrits ici, en français simple, d'après
docs/programme.md, les fichiers de langue (pc/tg/langues/fr.json) et le bestiaire (pc/tg/bestiaire.json).

Les illustrations des mondes arrivent au fil de l'eau : il suffit de déposer le fichier PNG au bon nom dans
docs/artbook/illustrations/ puis de relancer ce script ; sinon un cadre « illustration à venir » (avec le nom de
fichier attendu) garde sa place. `--manquantes` liste les fichiers attendus qui ne sont pas encore là.

Les créatures sont les images du jeu (donnees/bestiaire2/images/, le légendaire secret dans donnees/portraits/ et
app/src/main/assets/anim/), agrandies sans lissage (pixel art net). La mascotte du site n'y apparaît jamais.
Polices : Press Start 2P et VT323 (site/public/polices/, SIL OFL 1.1), texte courant en DejaVu Sans (ou une police
du système, à défaut Helvetica).
Licence de l'artbook (images et textes) : CC BY-NC-SA 4.0, comme les autres images du jeu (LICENSE-images.md) ;
ce script : GPL-3.0-or-later.
"""
import argparse
import io
import json
import os
import random
import shutil
import subprocess
import sys
import types
import unicodedata
from pathlib import Path

from PIL import Image
from reportlab import rl_config
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
ILLU = ICI / "illustrations"
SORTIE = ICI / "terminagotchi_artbook.pdf"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "terminagotchi_artbook"

W, H = A4
MARGE = 40
DPI = 200                     # résolution visée pour les images (pixels nets, PDF de taille raisonnable)
DPI_PETIT = 130               # pour les petites images (stades, variantes, vignettes)
rl_config.useA85 = 0

# ---------------------------------------------------------------- couleurs (direction artistique « règle C »)
FOND = HexColor("#0b0f14")
FOND2 = HexColor("#121a22")
CADRE = HexColor("#1e2a36")
VERT = HexColor("#3dff7c")
VERT_PALE = HexColor("#9dffc0")
CYAN = HexColor("#3df2ff")
TEXTE = HexColor("#e6f0ff")
DOUX = HexColor("#9aa8b8")
OR = HexColor("#ffd866")
ROSE = HexColor("#ff6fd8")

RARETE_COULEUR = {"commune": "#9aa8b8", "peu commune": "#3dff7c", "rare": "#3df2ff", "épique": "#b48cff",
                  "légendaire": "#ffd866", "mythique": "#ff5a5a"}


# ---------------------------------------------------------------- polices
def _woff2_vers_ttf(src, dst):
    """Convertit une police WOFF2 du site en TTF (fontTools ; brotli, ou à défaut celui de Node.js)."""
    from fontTools.ttLib import TTFont as FT
    import fontTools.ttLib.woff2 as w2
    if not w2.haveBrotli:
        if not shutil.which("node"):
            raise RuntimeError("ni brotli ni node")

        def dec(b):
            js = ("let c=[];process.stdin.on('data',d=>c.push(d)).on('end',()=>process.stdout.write("
                  "require('zlib').brotliDecompressSync(Buffer.concat(c))))")
            return subprocess.run(["node", "-e", js], input=b, capture_output=True, check=True).stdout
        w2.brotli = types.SimpleNamespace(decompress=dec)
        w2.haveBrotli = True
    f = FT(str(src))
    f.flavor = None
    f.save(str(dst))


def _chercher(*noms):
    dossiers = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu-sans-fonts", "/usr/share/fonts/dejavu",
                "/usr/share/fonts/TTF", "/usr/share/fonts/truetype/noto", "/usr/share/fonts/google-noto",
                "/usr/share/fonts/noto", "/Library/Fonts", "C:/Windows/Fonts"]
    for n in noms:
        for d in dossiers:
            p = Path(d) / n
            if p.exists():
                return p
    return None


def polices():
    """Enregistre les polices ; renvoie {titre, pixel, texte, gras}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    noms = {}
    for cle, woff in (("pixel_titre", "press-start-2p-latin-400-normal.woff2"), ("pixel", "vt323-latin-400-normal.woff2")):
        ttf = CACHE / (woff.replace(".woff2", ".ttf"))
        try:
            if not ttf.exists():
                _woff2_vers_ttf(RACINE / "site" / "public" / "polices" / woff, ttf)
            pdfmetrics.registerFont(TTFont(cle, str(ttf)))
            noms[cle] = cle
        except Exception as e:  # noqa: BLE001 — police de secours
            print(f"(police {woff} indisponible : {e} ; police de secours)")
            noms[cle] = None
    t = _chercher("DejaVuSans.ttf", "NotoSans-Regular.ttf")
    g = _chercher("DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf")
    if t and g:
        pdfmetrics.registerFont(TTFont("texte", str(t)))
        pdfmetrics.registerFont(TTFont("texte_gras", str(g)))
        noms["texte"], noms["gras"] = "texte", "texte_gras"
    else:
        noms["texte"], noms["gras"] = "Helvetica", "Helvetica-Bold"
    noms["titre"] = noms["pixel_titre"] or noms["gras"]
    noms["pixel"] = noms["pixel"] or "Courier"
    return noms


F = None
ETOILE = "★"


# ---------------------------------------------------------------- données du jeu
def charger():
    best = json.load(open(RACINE / "pc" / "tg" / "bestiaire.json", encoding="utf-8"))
    fr = json.load(open(RACINE / "pc" / "tg" / "langues" / "fr.json", encoding="utf-8"))
    biomes = json.load(open(RACINE / "donnees" / "biomes.json", encoding="utf-8"))
    return best, fr, biomes


def sans_accent(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def type_de(esp, variante, biomes):
    """Le biome (type) où vit une créature : règle de donnees/biomes.json."""
    v = sans_accent(variante)
    if v == "classique":
        return biomes["classique_par_espece"].get(esp["id"]) or biomes["classique_par_famille"].get(esp["famille"])
    for t in biomes["types"]:
        if v in [sans_accent(h) for h in t["habitats"]]:
            return t["id"]
    return biomes["classique_par_famille"].get(esp["famille"])


def image_creature(esp, variante, stade):
    v = sans_accent(variante).replace(" ", "_")
    p = RACINE / "donnees" / "bestiaire2" / "images" / f"{esp['numero']:03d}_{esp['id']}_{v}_{stade}.png"
    return p if p.exists() else None


# ---------------------------------------------------------------- dessin : outils
_IMAGES = {}


def pix(im, larg_pt, haut_pt, dpi=None):
    """L'image à la bonne taille pour DPI : agrandie SANS lissage (facteur entier, pixel art net) si elle est
    trop petite, réduite proprement si elle est bien plus grande que ce qui sera imprimé."""
    dpi = dpi or DPI
    cible = max(larg_pt / 72 * dpi / max(1, im.width), haut_pt / 72 * dpi / max(1, im.height))
    if cible < 0.75:
        return im.resize((max(1, round(im.width * cible)), max(1, round(im.height * cible))), Image.LANCZOS)
    k = max(1, min(6, round(cible)))
    return im.resize((im.width * k, im.height * k), Image.NEAREST) if k > 1 else im


def _rgb(col):
    return tuple(round(v * 255) for v in (col.red, col.green, col.blue))


def poser(c, im, x, y, w, h, fond=None, dpi=None, qualite=80):
    """Pose l'image im (PIL) exactement dans (x, y, w, h), aplatie sur la couleur unie fond et mise en JPEG de
    haute qualité (4:4:4) : le PDF reste léger et les pixels restent nets."""
    fond = fond or FOND
    src = pix(im, w, h, dpi or (DPI if w > 200 or h > 200 else DPI_PETIT))
    if src.mode == "RGBA":
        bg = Image.new("RGBA", src.size, _rgb(fond) + (255,))
        bg.alpha_composite(src)
        src = bg
    b = io.BytesIO()
    src.convert("RGB").save(b, "JPEG", quality=qualite, subsampling=0, optimize=True)
    b.seek(0)
    c.drawImage(ImageReader(b), x, y, w, h)


def dessiner_image(c, im, x, y, w, h, net=True, ancre="c", fond=None):
    """Dessine im (PIL) dans la boîte (x, y, w, h) en gardant ses proportions ; renvoie la boîte occupée."""
    r = min(w / im.width, h / im.height)
    dw, dh = im.width * r, im.height * r
    dx = x + (w - dw) / 2
    dy = y if ancre == "b" else y + (h - dh) / 2
    poser(c, im, dx, dy, dw, dh, fond)
    return dx, dy, dw, dh


def ouvrir(p):
    im = Image.open(p)
    im.load()
    return im.convert("RGBA") if im.mode in ("P", "LA", "L", "RGBA") else im.convert("RGB")


def rogner(im):
    if im.mode == "RGBA":
        b = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if b:
            return im.crop(b)
    return im


def fond_page(c, graine, pluie=True, couleur=None):
    c.setFillColor(FOND)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    if couleur is not None:                       # une fine bande de la couleur du biome, en haut, en gros pixels
        col = HexColor(couleur)
        for i in range(0, int(W), 12):
            c.setFillColor(Color(col.red, col.green, col.blue, alpha=0.55 if (i // 12) % 3 else 0.9))
            c.rect(i, H - 8, 12, 8, stroke=0, fill=1)
    if pluie:                                     # légère pluie de pixels verts (toujours la même pour une page)
        rnd = random.Random(graine)
        for _ in range(55):
            x = rnd.randrange(0, int(W) // 6) * 6
            y = rnd.randrange(0, int(H) // 6) * 6
            n = rnd.randint(1, 4)
            a = rnd.choice((0.10, 0.16, 0.24, 0.35))
            for k in range(n):
                c.setFillColor(Color(0.24, 1, 0.49, alpha=a * (1 - k / (n + 1))))
                c.rect(x, y - k * 8, 3, 3, stroke=0, fill=1)


def cadre_pixel(c, x, y, w, h, couleur=CYAN, fond=FOND2, ep=3):
    """Un cadre aux coins taillés en escalier (pixel art)."""
    s = ep
    c.setFillColor(fond)
    c.rect(x + s, y + s, w - 2 * s, h - 2 * s, stroke=0, fill=1)
    c.setFillColor(couleur)
    c.rect(x + 2 * s, y, w - 4 * s, s, stroke=0, fill=1)
    c.rect(x + 2 * s, y + h - s, w - 4 * s, s, stroke=0, fill=1)
    c.rect(x, y + 2 * s, s, h - 4 * s, stroke=0, fill=1)
    c.rect(x + w - s, y + 2 * s, s, h - 4 * s, stroke=0, fill=1)
    for (cx, cy) in ((x + s, y + s), (x + w - 2 * s, y + s), (x + s, y + h - 2 * s), (x + w - 2 * s, y + h - 2 * s)):
        c.rect(cx, cy, s, s, stroke=0, fill=1)


def pied(c, n, titre=""):
    c.setFont(F["pixel"], 12)
    c.setFillColor(DOUX)
    c.drawString(MARGE, 22, "TERMINAGOTCHI · artbook · CC BY-NC-SA 4.0")
    c.drawRightString(W - MARGE, 22, f"{titre}  {n}" if titre else str(n))


def titre_pixel(c, txt, x, y, taille=18, couleur=VERT, centre=False, ombre=True):
    if txt == txt.upper() and F["titre"] == "pixel_titre":
        txt = sans_accent(txt)          # la police pixel écrase les capitales accentuées : on les écrit sans accent
    c.setFont(F["titre"], taille)
    if ombre:
        c.setFillColor(HexColor("#0a3d1f"))
        (c.drawCentredString if centre else c.drawString)(x + 2, y - 2, txt)
    c.setFillColor(couleur)
    (c.drawCentredString if centre else c.drawString)(x, y, txt)


def largeur_titre(txt, taille):
    txt = sans_accent(txt)
    return pdfmetrics.stringWidth(txt, F["titre"], taille)


def titre_ajuste(c, txt, x, y, taille_max, larg_max, **kw):
    t = taille_max
    while t > 8 and largeur_titre(txt, t) > larg_max:
        t -= 1
    titre_pixel(c, txt, x, y, t, **kw)
    return t


def style(taille=12, couleur=TEXTE, gras=False, centre=False, interligne=1.38):
    return ParagraphStyle("s", fontName=F["gras"] if gras else F["texte"], fontSize=taille,
                          leading=taille * interligne, textColor=couleur,
                          alignment=TA_CENTER if centre else TA_LEFT, spaceAfter=0)


def para(c, html, x, y_haut, w, st):
    """Écrit un paragraphe dont le HAUT est à y_haut ; renvoie le y du bas."""
    p = Paragraph(html, st)
    _, h = p.wrap(w, 10000)
    p.drawOn(c, x, y_haut - h)
    return y_haut - h


def paras(c, liste, x, y, w, st, ecart=8):
    for t in liste:
        y = para(c, t, x, y, w, st) - ecart
    return y


def puce(c, x, y, couleur=VERT, t=5):
    c.setFillColor(couleur)
    c.rect(x, y, t, t, stroke=0, fill=1)


def etiquette(c, txt, x, y, couleur=CYAN, taille=13):
    """Une petite pastille de texte (police VT323) ; renvoie sa largeur."""
    c.setFont(F["pixel"], taille)
    lw = pdfmetrics.stringWidth(txt, F["pixel"], taille) + 12
    c.setFillColor(Color(couleur.red, couleur.green, couleur.blue, alpha=0.16))
    c.rect(x, y - 4, lw, taille + 4, stroke=0, fill=1)
    c.setFillColor(couleur)
    c.rect(x, y - 4, 2, taille + 4, stroke=0, fill=1)
    c.drawString(x + 7, y, txt)
    return lw


# ---------------------------------------------------------------- les illustrations à venir
ATTENDUES = []          # (fichier, légende) de chaque emplacement, pour --manquantes


def illustration(c, fichier, legende, x, y, w, h, repli=None, couleur=CYAN):
    """Un emplacement d'illustration : docs/artbook/illustrations/<fichier> s'il existe (ou l'image de repli
    validée du dépôt), sinon un cadre « illustration à venir » avec le nom du fichier attendu."""
    p = ILLU / fichier
    if not p.exists() and repli is not None and Path(repli).exists():
        p = Path(repli)
    ATTENDUES.append((fichier, legende, p.exists()))
    cadre_pixel(c, x, y, w, h, couleur=couleur)
    if p.exists():
        im = ouvrir(p)
        r = max((w - 12) / im.width, (h - 12) / im.height)          # remplit le cadre (recadrage centré)
        cw, ch = (w - 12) / r, (h - 12) / r
        l0, t0 = (im.width - cw) / 2, (im.height - ch) / 2
        im = im.crop((int(l0), int(t0), int(l0 + cw), int(t0 + ch)))
        poser(c, im.convert("RGB"), x + 6, y + 6, w - 12, h - 12, dpi=150, qualite=88)
        return True
    c.setFillColor(Color(couleur.red, couleur.green, couleur.blue, alpha=0.06))
    for i in range(0, int(w - 12), 12):                               # trame de pixels discrète
        for j in range(0, int(h - 12), 12):
            if (i // 12 + j // 12) % 2 == 0:
                c.rect(x + 6 + i, y + 6 + j, 6, 6, stroke=0, fill=1)
    petit = w < 260
    c.setFillColor(couleur)
    c.setFont(F["titre"], 6 if petit else 9)
    c.drawCentredString(x + w / 2, y + h / 2 + 10, "ILLUSTRATION A VENIR")
    c.setFont(F["pixel"], 15)
    c.setFillColor(TEXTE)
    c.drawCentredString(x + w / 2, y + h / 2 - 10, legende[:70])
    c.setFillColor(DOUX)
    c.setFont(F["pixel"], 12)
    c.drawCentredString(x + w / 2, y + h / 2 - 26, fichier if petit else "docs/artbook/illustrations/" + fichier)
    return False


# ---------------------------------------------------------------- les textes
HISTOIRE = [
    "Dans ton ordinateur se cache un monde entier : le <b>Terminaworld</b>. Ses chemins sont des dossiers, ses objets "
    "sont des fichiers, et des créatures y vivent, toutes faites de pixels et de petites lignes de données.",
    "Au centre pousse un arbre immense : <b>la Racine</b>. Ses branches touchent le ciel, ses racines plongent sous "
    "la terre, et des fils verts courent dans son écorce comme les circuits d'une carte électronique. Tous les "
    "chemins du monde partent de son pied. C'est pour ça qu'un chemin qui commence par <font color='#3dff7c'>/</font> "
    "part toujours de la Racine.",
    "Autour de l'arbre flottent <b>neuf terres</b>, les biomes : le Feu, l'Eau, la Glace, la Plante, la Roche, le "
    "Ciel &amp; Foudre, l'Ombre, la Machine et le Poison. Chacun a ses couleurs, ses paysages et ses habitants.",
    "Un jour, le Terminaworld s'est <b>endormi</b>. Plus un bruit, plus une lumière. Il ne restait qu'une toute petite "
    "lueur verte au pied de l'arbre.",
    "Un seul moyen de le réveiller : taper des <b>commandes</b> dans l'invite de commande, la ligne où l'on écrit "
    "des ordres à l'ordinateur. C'est un vrai terminal, comme celui des informaticiens. À chaque commande, la lumière "
    "remonte les câbles, puis l'arbre, et les couleurs reviennent.",
    "Et dans le nid, entre les racines, un <b>œuf</b> apparaît, ligne de pixels par ligne de pixels, comme un "
    "fichier qui se télécharge. Il a faim de commandes. <font color='#3dff7c'>pwd</font>, "
    "<font color='#3dff7c'>ls</font>, <font color='#3dff7c'>echo</font>, <font color='#3dff7c'>whoami</font>… "
    "Crac ! Il éclot. Ta créature est née, et elle sera ton guide dans tout le Terminaworld.",
]

LIEUX_SYSTEME = [
    ("/", "la Racine", "le pied du grand arbre, d'où partent tous les chemins du monde"),
    ("/home", "le village", "les maisons de tous les habitants"),
    ("~", "ton camp de base", "ta maison à toi, dans les racines : le nid, le feu, l'ordinateur"),
    ("~/terrain_terminagotchi", "la zone d'aventure", "le terrain de jeu : le seul endroit où l'on bâtit et où l'on casse"),
    ("/etc", "la salle des règles", "les règlements du monde, que seul le gardien peut changer"),
    ("/bin", "l'armurerie des commandes", "là où dorment toutes les commandes, prêtes à servir"),
    ("/tmp", "le terrain vague", "on y pose des choses qui s'envolent toutes seules"),
    ("/var/log", "les archives", "le registre où le gardien note tout ce qui se passe"),
    ("/dev", "les portails des machines", "des portes vers l'écran, le disque… et un trou noir"),
    ("/proc", "le miroir des habitants", "un miroir qui montre ce que fait chaque programme, en direct"),
]

BIOMES_TEXTE = {
    "feu": ("Le Feu", "Des volcans qui grondent, des rivières de lave et des plaines de cendres encore tièdes. Les "
            "habitants du Feu aiment la chaleur, les étincelles et les farces qui piquent un peu.",
            "Au nord-ouest de la carte, autour du volcan ; la Forge est accrochée à son flanc."),
    "eau": ("L'Eau", "Un lagon turquoise, des récifs de corail, des sources qui pétillent et, tout au fond, les "
            "abysses où brillent des lumières vivantes.",
            "À l'ouest, la grande côte bleue ; le Port y amarre ses bateaux-messagers."),
    "glace": ("La Glace", "La banquise, la toundra, des grottes de cristal et des aurores qui dansent dans le ciel. "
              "Tout y est calme, froid et transparent.",
              "À l'ouest, sous la côte : un palais de glace abrite la Salle des Données."),
    "plante": ("La Plante", "Des forêts profondes, des prairies, des jungles et des champignonnières. Ici, tout pousse, "
               "tout respire, et les arbres cachent des maisons.",
               "Au sud-ouest ; la Guilde des Bâtisseurs Libres vit dans les cabanes perchées."),
    "roche": ("La Roche", "Des montagnes, des canyons, des déserts, des dunes et des ruines très anciennes. Les "
              "habitants de la Roche sont solides et patients.",
              "Au sud, au bout du grand chemin ; le Sommet est planté sur le plus haut pic."),
    "ciel": ("Le Ciel & Foudre", "Une mer de nuages, des orages qui crépitent, de la brume et, tout en haut, "
             "l'espace. Des îles flottent, reliées par des ponts de lumière.",
             "Au nord-est ; la Tour des Ondes y fait vibrer ses antennes."),
    "ombre": ("L'Ombre", "Un royaume violet de cryptes, d'ossuaires, de lunes et de tours magiques. On y voit peu, "
              "mais on y entend beaucoup de secrets.",
              "À l'est, le château violet ; la Citadelle monte la garde juste en face."),
    "machine": ("La Machine", "Une cité dorée pleine d'engrenages, de tuyaux, de néons et de vieilles pièces "
                "rouillées. Ça tourne, ça cliquette, ça calcule.",
                "À l'est ; le Poste de Contrôle et l'Atelier sont dans la cité dorée."),
    "poison": ("Le Poison", "Des marais verts qui luisent, des ruines couvertes de mousse et des cascades fluo. "
               "Gluant, oui… mais ses habitants sont souvent très gentils.",
               "Au sud-est, autour des vieilles arches."),
}

# (id, icône texte, nom, où sur la carte, ce qu'on voit, ce qu'on apprend, gardien, fichier gardien ou None, repli)
MONDES = [
    ("carrefour", "Le Carrefour", "au pied de l'arbre, sur la grande place ronde",
     "Une place pavée au pied de la Racine. Tout autour, des portes en arc, chacune avec la bannière et la couleur d'un "
     "monde. Au milieu brille le cristal vert : la dernière lumière qui restait quand tout dormait.",
     "C'est d'ici que partent tous les chemins. Le Carrefour montre les mondes déjà ouverts et ceux qui attendent "
     "encore leur clé.",
     "Pas de gardien : c'est ta créature qui t'accueille et te montre les portes.", None),
    ("forge", "La Forge", "au flanc du volcan, au nord-ouest",
     "Un atelier de forgerons-programmeurs : des enclumes chaudes, des cheminées, et des parchemins de code qui "
     "s'allument ligne par ligne.",
     "Programmer : écrire ses propres recettes (des scripts), puis de vrais programmes, et même son petit jeu.",
     "Boulonnet, un petit automate de bronze né d'un boulon oublié, attend les apprentis à la fin de la Forge.",
     "forge_gardien.png"),
    ("citadelle", "La Citadelle", "face au château violet de l'Ombre, à l'est",
     "Une forteresse blanche à remparts et tours de guet. Au loin, des glitchs rôdent dans la brume violette.",
     "Se défendre : les cadenas des fichiers, les mots de passe, repérer une anomalie. Ici on défend, on n'attaque "
     "jamais : toutes les menaces sont fausses, inventées par le jeu.",
     "Le garde de la Citadelle, un humanoïde tortue à la carapace cuirassée, en uniforme de garde. Il connaît chaque "
     "serrure par cœur.", "citadelle_gardien.png"),
    ("port", "Le Port", "sur la côte de l'Eau, à l'ouest",
     "Des quais numérotés, des phares, des bateaux-messagers qui partent et reviennent, et un annuaire géant.",
     "Les réseaux : l'adresse d'une machine (le numéro du quai), l'annuaire (DNS), l'écho du sonar (ping), le facteur "
     "qui rapporte les pages (curl).",
     "Le capitaine du Port, un humanoïde à tête de pieuvre bordeaux, gants noirs et casquette d'officier.",
     "port_gardien.png"),
    ("ondes", "La Tour des Ondes", "dans le ciel, au nord-est",
     "Une tour fine au-dessus des nuages, avec des antennes qui vibrent de toutes les couleurs. On y voit les ondes.",
     "La radio : les fréquences, le Wi-Fi, LoRa qui parle très loin avec très peu, et les réseaux maillés où les "
     "messages sautent de nœud en nœud.",
     "La gardienne des ondes, en long manteau bleu nuit brodé de vaguelettes. Elle écoute avec un grand cornet : "
     "« chut… écoute ».", "ondes_gardien.png"),
    ("temps", "La Bibliothèque du Temps", "dans le tronc de l'arbre",
     "Une bibliothèque ronde aux étagères infinies, cachée derrière une fenêtre du tronc. Ses livres-versions sont "
     "reliés par des fils de lumière.",
     "Git : prendre des « photos » de son travail (les commits), remonter le temps, ouvrir des mondes parallèles (les "
     "branches) et les réunir.",
     "La Bibliothécaire, qui garde le grand grimoire où chaque version est écrite.", "temps_gardien.png"),
    ("donnees", "La Salle des Données", "dans le palais de glace, à l'ouest",
     "Une grande salle de tri aux murs de cristal : des colonnes de chiffres lumineux, des tamis, des moulins.",
     "Trier, chercher et compter dans du texte (grep, sort, cut, awk…), et faire des statistiques sur sa propre "
     "collection de créatures.",
     "Nautiloque, un céphalopode à coquille en spirale qui parle par éclairs de lumière.", "donnees_gardien.png"),
    ("controle", "Le Poste de Contrôle", "dans la cité dorée de la Machine",
     "La salle de contrôle d'un vaisseau, sous un grand dôme : des jauges, des voyants et des habitants-processus au "
     "travail.",
     "Faire tourner un système : les processus, la mémoire, les disques, les réveils programmés (cron), le carnet de "
     "bord, les paquets.",
     "La cheffe de quart, en combinaison bleu nuit pleine de petites poches, casque-micro sur les oreilles : "
     "« d'abord on regarde, ensuite on décide ».", "controle_gardien.png"),
    ("machines", "La Salle des Rouages", "sous terre, sous le camp (hors de la carte)",
     "Une salle pleine de rouages sous les racines : le processeur-cuisinier, la mémoire-plan de travail, les "
     "disques-garde-manger.",
     "Le matériel : ce qu'il y a dans un ordinateur, le binaire, comment la machine se réveille, et les maisons dans "
     "la maison (machines virtuelles, conteneurs).",
     "La cheffe mécanicienne, un petit robot de laiton et de cuivre aux grands yeux-lampes, dont la cheminée souffle "
     "des nuages en forme de cœur.", "machines_gardien.png"),
    ("atelier", "L'Atelier", "dans la cité dorée de la Machine, près des bras-robots",
     "Un établi avec des petits robots, des cartes électroniques et des LED qui clignotent.",
     "Les robots et l'électronique : allumer une LED, lire un capteur, apprendre à un robot à éviter les obstacles "
     "(avec un vrai Raspberry Pi si un adulte aide, sinon un robot simulé).",
     "Pas de gardien : ce sont tes robots qui t'attendent sur l'établi.", None),
    ("observatoire", "L'Observatoire de l'IA", "tout en haut de l'arbre",
     "Une coupole dorée et une grande lunette, perchées dans les feuilles. Des robots-assistants y reçoivent leurs "
     "missions.",
     "Comprendre l'intelligence artificielle : donner une consigne claire à un assistant, puis toujours vérifier son "
     "travail. Le capitaine, c'est toi.",
     "Séraphibou, un petit hibou à six ailes qui lit les étoiles la nuit.", "observatoire_gardien.png"),
    ("crypte", "La Crypte des Codes", "sous terre, sous la Racine (hors de la carte)",
     "Une crypte sous l'arbre : des coffres, des sceaux, des grimoires codés, et un escalier qui s'ouvre entre les "
     "racines du camp.",
     "Les codes secrets : la roue de César, les empreintes, les clés qu'on échange sans les montrer, et la chaîne de "
     "blocs qu'on ne peut pas falsifier.",
     "Les sphinx de givre, doux et sages, et la légendaire gardienne du registre.", "crypte_gardien.png"),
    ("guilde", "La Guilde des Bâtisseurs Libres", "dans les cabanes perchées de la Plante, au sud-ouest",
     "Une guilde d'artisans dans les arbres : un grand mur de plans partagés, une imprimante 3D, de vieux PC réparés.",
     "Le logiciel libre et le « fais-le toi-même » : lire le code des autres, l'améliorer, le partager. Terminagotchi "
     "aussi est libre.",
     "La maîtresse d'ouvrage, tablier de cuir et lunettes relevées, qui tend un plan ouvert : « tiens, il est à toi "
     "aussi ! »", "guilde_gardien.png"),
    ("ponts", "Les Ponts des Nombres", "entre les îles, partout où il faut compter",
     "Des îlots reliés par des passerelles de pierre qui s'allument quand on trouve le bon nombre.",
     "Les mathématiques par la pratique : le partage, le reste, le binaire, les puissances… Un pont, jamais un mur : "
     "on peut toujours dire « je ne connais pas encore » et apprendre sur place.",
     "Pas de gardien : chaque pont s'allume pour toi.", None),
    ("entrainement", "La salle d'entraînement", "près du Carrefour",
     "Un gymnase avec des cibles et le grand tableau des grades, de Bit jusqu'à Exa.",
     "S'entraîner sur des défis courts pour devenir rapide et sûr de soi au clavier.",
     "Pas de gardien : le tableau des grades suffit à donner envie !", None),
    ("sommet", "Le Sommet", "sur le plus haut pic de la Roche, au sud",
     "Un sommet au-dessus des nuages, avec un petit drapeau rouge, d'où l'on voit tout le Terminaworld.",
     "Le niveau expert : des scripts solides qui ne mentent pas, des enquêtes, et le grand défi final en cordée.",
     "Les créatures légendaires, qui attendent là-haut les vrais maîtres.", "sommet_gardien.png"),
]

# où se trouve chaque lieu sur la nouvelle carte (pixels de monde.png, 1672×941, validée le 2 novembre 2026)
CARTE_POINTS = [
    ("Le Carrefour", 770, 470), ("Le camp et le nid", 620, 330), ("La Bibliothèque du Temps", 900, 205),
    ("L'Observatoire", 890, 60), ("Le Port", 310, 330), ("La Forge", 415, 165), ("La Tour des Ondes", 1310, 55),
    ("Le Poste de Contrôle", 1390, 290), ("L'Atelier", 1555, 345), ("La Citadelle", 1190, 525),
    ("La Salle des Données", 185, 515), ("La Guilde", 420, 690), ("Le Sommet", 922, 590),
]

FAMILLES_TEXTE = {
    "Démons": "Feu et ténèbres : cornes, ailes, queues pointues et yeux qui brillent. Des petits diablotins farceurs "
              "jusqu'aux grands seigneurs.",
    "Élémentaires": "Les forces de la nature : feu, glace, eau, foudre, roche et vent. En grandissant, leur corps "
                    "devient leur élément.",
    "Morts-vivants": "Squelettes, fantômes et lanternes de la brume. Ils font « bouh », mais ils sont souvent très "
                     "attachants.",
    "Bêtes monstrueuses": "L'instinct sauvage : loups cuirassés, félins à cornes, ours géants. Les petits ressemblent "
                          "à des animaux, les grands impressionnent.",
    "Sylvestres": "La nature vivante : arbres qui marchent, champignons courageux, fleurs lumineuses.",
    "Arthropodes": "Essaims et carapaces : scarabées, araignées, mantes et mille-pattes brillants.",
    "Abyssaux": "Les profondeurs de la mer : poissons étranges, serpents de mer, pieuvres et lumières vivantes.",
    "Célestes": "La lumière et les étoiles : gardiens ailés, animaux constellés, êtres de lumière.",
    "Constructs": "La magie et le métal : automates, armures vivantes, gardiens de pierre et machines à runes.",
    "Aberrations": "Mutations et chaos : des créatures à yeux, à tentacules, qui ne ressemblent à rien de connu.",
}

STADES = ["bebe", "enfant", "ado", "adulte", "ancien"]
STADE_NOM = {"bebe": "bébé", "enfant": "enfant", "ado": "ado", "adulte": "adulte", "ancien": "ancien"}


# ---------------------------------------------------------------- les pages
class Livre:
    def __init__(self, chemin):
        self.c = canvas.Canvas(str(chemin), pagesize=A4, pageCompression=1)
        self.c.setTitle("Terminagotchi — l'artbook du Terminaworld (brouillon)")
        self.c.setAuthor("les contributeurs de Terminagotchi")
        self.c.setSubject("Histoire, lore, habitats et posters des créatures — CC BY-NC-SA 4.0")
        self.n = 1
        self.sommaire = []

    def suivante(self, titre=""):
        pied(self.c, self.n, titre)
        self.c.showPage()
        self.n += 1

    def marque(self, titre):
        self.sommaire.append((titre, self.n))
        self.c.bookmarkPage(f"p{self.n}")
        self.c.addOutlineEntry(titre, f"p{self.n}", level=0)


def page_couverture(L, carte):
    c = L.c
    fond_page(c, 1)
    im = ouvrir(carte).convert("RGB")
    # l'arbre au centre de la carte, en grand
    boite = (int(im.width * 0.27), 0, int(im.width * 0.73), int(im.height * 0.72))
    arbre = im.crop(boite)
    x0, y0, w0, h0 = 0, H * 0.30, W, H * 0.70
    r = max(w0 / arbre.width, h0 / arbre.height)
    cw, ch = w0 / r, h0 / r
    arbre = arbre.crop((int((arbre.width - cw) / 2), 0, int((arbre.width + cw) / 2), int(ch)))
    poser(c, arbre, x0, y0, w0, h0, dpi=150, qualite=88)
    for i in range(24):                                            # fondu vers le noir, en bandes de pixels
        c.setFillColor(Color(0.043, 0.059, 0.078, alpha=min(1, (24 - i) / 24)))
        c.rect(0, y0 + i * 6, W, 6, stroke=0, fill=1)
    titre_pixel(c, "TERMINAGOTCHI", W / 2, H * 0.24, 30, VERT, centre=True)
    c.setFont(F["pixel"], 26)
    c.setFillColor(CYAN)
    c.drawCentredString(W / 2, H * 0.24 - 40, "L'ARTBOOK DU TERMINAWORLD")
    c.setFont(F["texte"], 13)
    c.setFillColor(TEXTE)
    c.drawCentredString(W / 2, H * 0.24 - 72, "L'histoire, les lieux, les habitats et toutes les créatures")
    c.setFont(F["pixel"], 15)
    c.setFillColor(DOUX)
    c.drawCentredString(W / 2, 70, "brouillon — les illustrations des mondes arrivent au fil de l'eau")
    c.setFillColor(VERT)
    c.rect(W / 2 - 60, H * 0.24 - 92, 120, 3, stroke=0, fill=1)
    L.suivante()


def page_bienvenue(L, nb_creatures):
    c = L.c
    fond_page(c, 2)
    L.marque("Bienvenue")
    titre_pixel(c, "BIENVENUE", MARGE, H - 90, 22)
    y = para(c, "Ce livre est un voyage dans le <b>Terminaworld</b>, le monde caché dans ton ordinateur. Tu y "
                "trouveras son histoire, la carte de tous ses lieux, ses neuf terres et "
                f"<b>{nb_creatures} créatures</b>, chacune avec son poster.", MARGE, H - 120, W - 2 * MARGE,
             style(14))
    y = para(c, "Pour les parents : Terminagotchi est un jeu libre qui apprend le vrai terminal (la ligne de "
                "commande) aux enfants dès 7 ans. Chaque lieu de ce livre correspond à une vraie notion "
                "d'informatique ; les encadrés « pour les grands » donnent le mot exact.", MARGE, y - 14,
             W - 2 * MARGE, style(11.5, DOUX))
    titre_pixel(c, "SOMMAIRE", MARGE, y - 50, 14, CYAN)
    L._y_sommaire = y - 78
    L._page_sommaire = c.getPageNumber()
    # le sommaire est rempli à la fin (on ne connaît pas encore les numéros) : voir remplir_sommaire
    L.suivante("Bienvenue")


def page_histoire(L, camp):
    c = L.c
    fond_page(c, 3)
    L.marque("L'histoire du Terminaworld")
    titre_pixel(c, "L'HISTOIRE", MARGE, H - 90, 22)
    c.setFont(F["pixel"], 18)
    c.setFillColor(CYAN)
    c.drawString(MARGE, H - 116, "du Terminaworld")
    y = paras(c, HISTOIRE[:4], MARGE, H - 140, W - 2 * MARGE, style(12.5), 7)
    hh = 200
    illustration(c, "camp.png", "Le camp de base, au pied de l'arbre", MARGE, y - hh - 6, W - 2 * MARGE, hh,
                 repli=camp)
    y = paras(c, HISTOIRE[4:], MARGE, y - hh - 20, W - 2 * MARGE, style(12.5), 7)
    L.suivante("L'histoire")


def pages_carte(L, carte):
    """La carte en double page : moitié gauche sur une page paire, moitié droite sur la suivante."""
    c = L.c
    if L.n % 2 == 1:                                                  # la double page commence à gauche
        fond_page(c, 99)
        titre_pixel(c, "NOTES DE VOYAGE", MARGE, H - 90, 16, CYAN)
        para(c, "Cette page est là pour que la carte tombe sur une vraie double page quand le livre est imprimé.",
             MARGE, H - 120, W - 2 * MARGE, style(11, DOUX))
        L.suivante()
    im = ouvrir(carte).convert("RGB")
    jpg = CACHE / "carte_double_page.jpg"                             # un seul fichier : la carte n'est rangée
    im.save(jpg, "JPEG", quality=90, subsampling=0, optimize=True)    # qu'une fois dans le PDF pour les 2 pages
    lh = 565
    lw = lh * im.width / im.height
    x0 = (2 * W - lw) / 2                                             # position sur la double page
    y0 = H - 92 - lh
    for cote in (0, 1):
        fond_page(c, 4 + cote, pluie=False)
        if cote == 0:
            L.marque("La carte du Terminaworld")
        c.saveState()
        p = c.beginPath()
        p.rect(0, 0, W, H)
        c.clipPath(p, stroke=0, fill=0)
        c.drawImage(str(jpg), x0 - cote * W, y0, lw, lh)
        c.restoreState()
        # repères numérotés (gros pixels)
        for i, (nom, px, py) in enumerate(CARTE_POINTS, 1):
            x = x0 + px / im.width * lw - cote * W
            y = y0 + lh - py / im.height * lh
            if -14 < x < W + 14:
                c.setFillColor(HexColor("#0b0f14"))
                c.rect(x - 9, y - 9, 18, 18, stroke=0, fill=1)
                c.setFillColor(VERT)
                c.rect(x - 7, y - 7, 14, 14, stroke=0, fill=1)
                c.setFillColor(FOND)
                c.setFont(F["pixel"], 13)
                c.drawCentredString(x, y - 4, str(i))
        if cote == 0:
            titre_pixel(c, "LA CARTE DU TERMINAWORLD", MARGE, H - 62, 19)
        else:
            c.setFont(F["pixel"], 18)
            c.setFillColor(CYAN)
            c.drawRightString(W - MARGE, H - 62, "Chaque lieu à sa place, autour de la Racine.")
        # légende en bas, répartie sur les deux pages
        moitie = (len(CARTE_POINTS) + 1) // 2
        items = list(enumerate(CARTE_POINTS, 1))[cote * moitie:(cote + 1) * moitie]
        col_w = (W - 2 * MARGE) / 2
        for k, (i, (nom, _, _)) in enumerate(items):
            x = MARGE + (k % 2) * col_w
            y = y0 - 30 - (k // 2) * 22
            c.setFillColor(VERT)
            c.rect(x, y - 3, 14, 14, stroke=0, fill=1)
            c.setFillColor(FOND)
            c.setFont(F["pixel"], 13)
            c.drawCentredString(x + 7, y, str(i))
            c.setFillColor(TEXTE)
            c.setFont(F["texte"], 11)
            c.drawString(x + 22, y, nom)
        if cote == 1:
            c.setFont(F["texte"], 10)
            c.setFillColor(DOUX)
            c.drawString(MARGE, y0 - 30 - 3 * 22 - 4, "Sous terre, hors de la vue : la Salle des Rouages et la Crypte des Codes.")
        L.suivante("La carte")


def page_racine(L):
    c = L.c
    fond_page(c, 6)
    L.marque("La Racine et les lieux du système")
    titre_pixel(c, "LA RACINE", MARGE, H - 90, 22)
    c.setFont(F["pixel"], 18)
    c.setFillColor(CYAN)
    c.drawString(MARGE, H - 116, "et les lieux du système")
    y = para(c, "Le Terminaworld, ce n'est pas seulement ton terrain de jeu : c'est <b>tout l'ordinateur</b>, vu "
                "comme un monde. Certains lieux appartiennent au gardien du monde (on l'appelle <i>root</i>) : on "
                "peut les regarder, mais on n'y touche pas. Si on essaie, le gardien dit non : "
                "« Permission denied ».", MARGE, H - 140, W - 2 * MARGE, style(12.5))
    y -= 18
    for chemin, nom, image in LIEUX_SYSTEME:
        cadre_pixel(c, MARGE, y - 44, W - 2 * MARGE, 44, couleur=CADRE, fond=FOND2, ep=2)
        c.setFont(F["pixel"], 17)
        c.setFillColor(VERT)
        c.drawString(MARGE + 12, y - 27, chemin)
        c.setFont(F["gras"], 12)
        c.setFillColor(TEXTE)
        c.drawString(MARGE + 175, y - 19, nom[0].upper() + nom[1:])
        c.setFont(F["texte"], 9.5)
        c.setFillColor(DOUX)
        c.drawString(MARGE + 175, y - 34, image)
        y -= 50
    para(c, "<font color='#3df2ff'>Pour les grands</font> — la Racine est « / », la racine de l'arborescence "
            "unique ; ~ est le dossier personnel ($HOME). Le jeu n'écrit que dans ~/terrain_terminagotchi et n'utilise "
            "jamais sudo.", MARGE, y - 6, W - 2 * MARGE, style(10.5, DOUX))
    L.suivante("La Racine")


def page_biomes_intro(L):
    c = L.c
    fond_page(c, 7)
    L.marque("Les neuf biomes")
    titre_pixel(c, "LES NEUF", MARGE, H - 90, 22)
    titre_pixel(c, "BIOMES", MARGE, H - 120, 22)
    y = paras(c, [
        "Autour de la Racine flottent neuf terres. Chaque créature vit dans le biome qui lui ressemble : un "
        "diablotin de braise au Feu, une pieuvre lumineuse dans l'Eau, un petit automate dans la Machine.",
        "Quand ton œuf apparaît dans le nid, il appartient à l'un de ces neuf biomes. Et dans ton propre monde, tu "
        "fais pousser des régions de chaque biome pour accueillir les créatures que tu rencontres.",
        "Une même espèce peut avoir plusieurs <b>variantes</b> : un petit diablotin qui a grandi dans la lave n'a pas "
        "les mêmes couleurs que son cousin des cendres. La variante dit dans quel biome il vit.",
    ], MARGE, H - 150, W - 2 * MARGE, style(13), 10)
    oeufs = RACINE / "donnees" / "oeufs"
    types = ["feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison"]
    tw = (W - 2 * MARGE) / 3
    for i, t in enumerate(types):
        x = MARGE + (i % 3) * tw
        yy = y - 30 - (i // 3) * 150
        p = oeufs / f"oeuf_{t}_intact.png"
        if p.exists():
            dessiner_image(c, rogner(ouvrir(p)), x + tw / 2 - 40, yy - 100, 80, 95)
        c.setFont(F["titre"], 8)
        c.setFillColor(VERT)
        c.drawCentredString(x + tw / 2, yy - 118, BIOMES_TEXTE[t][0].upper())
    L.suivante("Les biomes")


def pages_biomes(L, best, biomes, fr):
    c = L.c
    especes = [e for e in best["especes"] if e.get("famille") != "Système"]
    for t in biomes["types"]:
        tid = t["id"]
        nom, texte, ou = BIOMES_TEXTE[tid]
        fond_page(c, 100 + len(tid), couleur=t["couleurs"]["principale"])
        L.marque("Biome : " + nom)
        accent = HexColor(t["couleurs"]["principale"])
        titre_pixel(c, nom.upper(), MARGE, H - 80, 20)
        illustration(c, f"biome_{tid}.png", nom, MARGE, H - 330, W - 2 * MARGE, 225, couleur=accent)
        y = para(c, texte, MARGE, H - 350, W - 2 * MARGE - 120, style(12.5))
        y = para(c, "<font color='#3df2ff'>Sur la carte :</font> " + ou, MARGE, y - 8, W - 2 * MARGE - 120,
                 style(11, DOUX))
        p = RACINE / "donnees" / "oeufs" / f"oeuf_{tid}_intact.png"
        if p.exists():
            dessiner_image(c, rogner(ouvrir(p)), W - MARGE - 90, H - 450, 80, 95)
        oeuf = fr.get(f"intro.type.{tid}")
        if oeuf:
            y = para(c, "<i>" + oeuf + "</i>", MARGE, y - 8, W - 2 * MARGE - 120, style(11, VERT_PALE))
        lieux = ", ".join(best["habitats"].get(sans_accent(h), h) for h in t["habitats"])
        y = para(c, "<font color='#3df2ff'>Ses paysages :</font> " + lieux + ".", MARGE, y - 8,
                 W - 2 * MARGE - 120, style(11, DOUX))
        # habitants : les espèces dont la forme classique vit ici
        hab = [e for e in especes if type_de(e, "classique", biomes) == tid]
        c.setFont(F["titre"], 9)
        c.setFillColor(CYAN)
        c.drawString(MARGE, y - 26, f"SES HABITANTS ({len(hab)})")
        cols, taille = 8, (W - 2 * MARGE) / 8
        yy = y - 40
        for i, e in enumerate(hab[:32]):
            x = MARGE + (i % cols) * taille
            ty = yy - (i // cols + 1) * (taille + 10)
            if ty < 40:
                break
            p = image_creature(e, "classique", "enfant")
            if p:
                dessiner_image(c, rogner(ouvrir(p)), x + 4, ty + 10, taille - 8, taille - 12, ancre="b")
            c.setFont(F["pixel"], 11)
            c.setFillColor(TEXTE)
            c.drawCentredString(x + taille / 2, ty, e["nom"])
        L.suivante("Biome : " + nom)


def page_mondes_intro(L):
    c = L.c
    fond_page(c, 200)
    L.marque("Les mondes et leurs gardiens")
    titre_pixel(c, "LES MONDES", MARGE, H - 90, 22)
    c.setFont(F["pixel"], 18)
    c.setFillColor(CYAN)
    c.drawString(MARGE, H - 116, "et leurs gardiens")
    y = paras(c, [
        "Quand on connaît bien les commandes de base, de nouvelles portes s'ouvrent au Carrefour. Derrière chacune "
        "se trouve un <b>monde</b> : un lieu du Terminaworld où l'on apprend un vrai métier de l'informatique.",
        "Chaque monde a son décor, ses épreuves et souvent son <b>gardien</b>. Les gardiens sont des personnages "
        "originaux en uniforme, ou des créatures que l'on connaît déjà. Ils accueillent, expliquent, et remettent "
        "un titre à la fin : Maître de la Forge, Savant des Données, Chef des Robots…",
        "On choisit son chemin : il n'y a pas d'ordre obligatoire, et aucun monde ne bloque les autres. Ceux qui "
        "en ont maîtrisé trois peuvent monter au <b>Sommet</b>.",
    ], MARGE, H - 150, W - 2 * MARGE, style(13), 10)
    y -= 10
    for i, m in enumerate(MONDES):
        x = MARGE + (i % 2) * (W - 2 * MARGE) / 2
        yy = y - (i // 2) * 24
        puce(c, x, yy + 3, VERT, 6)
        c.setFont(F["texte"], 11.5)
        c.setFillColor(TEXTE)
        c.drawString(x + 14, yy, m[1])
    L.suivante("Les mondes")


def pages_mondes(L):
    c = L.c
    for i, (mid, nom, ou, voit, apprend, gardien, fgard) in enumerate(MONDES):
        fond_page(c, 300 + i)
        L.marque("Monde : " + nom)
        titre_ajuste(c, nom.upper(), MARGE, H - 80, 20, W - 2 * MARGE)
        c.setFont(F["pixel"], 16)
        c.setFillColor(CYAN)
        c.drawString(MARGE, H - 104, "Sur la carte : " + ou)
        illustration(c, f"{mid}.png", "L'entrée : " + nom, MARGE, H - 365, W - 2 * MARGE, 245)
        y = H - 390
        for titre, txt in (("CE QU'ON Y VOIT", voit), ("CE QU'ON Y APPREND", apprend)):
            c.setFont(F["titre"], 9)
            c.setFillColor(VERT)
            c.drawString(MARGE, y, titre)
            y = para(c, txt, MARGE, y - 10, W - 2 * MARGE, style(12.5)) - 28
        c.setFont(F["titre"], 9)
        c.setFillColor(VERT)
        c.drawString(MARGE, y, "LE GARDIEN")
        if fgard:
            gw = 190
            gh = min(250, y - 50)
            illustration(c, fgard, "Le gardien", W - MARGE - gw, y + 12 - gh, gw, gh, couleur=HexColor("#ff00ff"))
            para(c, gardien, MARGE, y - 10, W - 2 * MARGE - gw - 18, style(12.5))
        else:
            para(c, gardien, MARGE, y - 10, W - 2 * MARGE, style(12.5))
        L.suivante("Monde : " + nom)


def page_bestiaire_intro(L, best):
    c = L.c
    fond_page(c, 400)
    L.marque("Le bestiaire")
    titre_pixel(c, "LE BESTIAIRE", MARGE, H - 90, 22)
    n = len(best["especes"])
    y = paras(c, [
        f"Le Terminaworld abrite <b>{n} espèces</b> de créatures, rangées en dix familles. Elles sont attirées par les "
        "commandes que tu tapes, et chacune grandit en <b>cinq stades</b> : bébé, enfant, ado, adulte et ancien. "
        "À chaque stade, son corps change vraiment.",
        "Certaines sont communes, d'autres rares, quelques-unes légendaires… et une seule est mythique. Chaque espèce "
        "peut avoir des <b>variantes</b> selon le biome où elle vit ; les plus difficiles à trouver sont marquées "
        f"{ETOILE}. Très rarement, une créature naît <b>chromatique</b> (une chance sur {best.get('chance_shiny', 100)}), "
        "avec d'autres couleurs.",
    ], MARGE, H - 120, W - 2 * MARGE, style(12.5), 10)
    y -= 10
    for fam, txt in FAMILLES_TEXTE.items():
        c.setFont(F["titre"], 9)
        c.setFillColor(CYAN)
        c.drawString(MARGE, y, sans_accent(fam.upper()))
        y = para(c, txt, MARGE, y - 6, W - 2 * MARGE, style(11, DOUX)) - 12
    L.suivante("Le bestiaire")


def page_famille(L, fam, especes):
    c = L.c
    fond_page(c, 500 + len(fam))
    L.marque("Famille : " + fam)
    titre_ajuste(c, fam.upper(), MARGE, H - 90, 22, W - 2 * MARGE)
    y = para(c, FAMILLES_TEXTE.get(fam, ""), MARGE, H - 112, W - 2 * MARGE, style(13))
    cols = 5
    tw = (W - 2 * MARGE) / cols
    th = 120
    for i, e in enumerate(especes):
        x = MARGE + (i % cols) * tw
        yy = y - 30 - (i // cols + 1) * (th + 22)
        p = image_creature(e, "classique", "adulte")
        if p:
            dessiner_image(c, rogner(ouvrir(p)), x + 6, yy + 18, tw - 12, th - 10, ancre="b")
        c.setFont(F["pixel"], 13)
        c.setFillColor(TEXTE)
        c.drawCentredString(x + tw / 2, yy + 4, f"{e['numero']:03d} {e['nom']}")
    L.suivante("Famille : " + fam)


def poster(L, e, biomes, best):
    c = L.c
    tid = type_de(e, "classique", biomes) or "ombre"          # le légendaire secret (famille « Système ») : l'ombre
    tinfo = next((t for t in biomes["types"] if t["id"] == tid), biomes["types"][0])
    accent = HexColor(tinfo["couleurs"]["principale"])
    fond_page(c, 1000 + e["numero"], couleur=tinfo["couleurs"]["principale"])
    rar = e.get("rarete", "commune")
    rcol = HexColor(RARETE_COULEUR.get(rar, "#9aa8b8"))
    # en-tête
    c.setFont(F["pixel"], 20)
    c.setFillColor(rcol)
    c.drawString(MARGE, H - 58, f"N° {e['numero']:03d}")
    c.drawRightString(W - MARGE, H - 58, rar.upper())
    titre_ajuste(c, e["nom"].upper(), W / 2, H - 100, 28, W - 2 * MARGE, centre=True)
    # la grande image : l'adulte (ou le portrait du légendaire secret)
    zone = (MARGE, H - 470, W - 2 * MARGE, 350)
    fond_panneau = Color(accent.red * 0.12, accent.green * 0.12, accent.blue * 0.12 + 0.03)
    cadre_pixel(c, *zone, couleur=accent, fond=fond_panneau)
    if e["id"] == "abyssor":
        grand = RACINE / "donnees" / "portraits" / "151_abyssor_adulte.png"
    else:
        grand = image_creature(e, "classique", "adulte")
    if grand and grand.exists():
        dessiner_image(c, rogner(ouvrir(grand)), zone[0] + 20, zone[1] + 14, zone[2] - 40, zone[3] - 28, ancre="b",
                       fond=fond_panneau)
    # pastilles
    x = MARGE
    y = H - 500
    for txt, col in ((e["famille"] if e["famille"] != "Système" else "Système (secret)", CYAN),
                     ("tout au fond de la grotte" if e["id"] == "abyssor" else "biome : " + BIOMES_TEXTE[tid][0], accent),
                     (f"{e.get('taille_cm', 0):g} cm · {e.get('poids_ko', 0):g} Ko", DOUX)):
        x += etiquette(c, txt, x, y, col, 15) + 8
    # texte
    desc = e.get("description", "")
    comp = e.get("comportement", "")
    y = para(c, desc, MARGE, y - 16, W - 2 * MARGE, style(12.5))
    if comp:
        y = para(c, comp, MARGE, y - 4, W - 2 * MARGE, style(11, VERT_PALE))
    # les 5 stades, à la même échelle (le grand dessin est au même cadre pour tous les stades)
    c.setFont(F["titre"], 8)
    c.setFillColor(VERT)
    c.drawString(MARGE, y - 20, "SES STADES")
    bas = 150
    hz = y - 30 - bas
    if e["id"] == "abyssor":
        imgs = []
        for st in ("enfant", "ado", "adulte", "finale"):
            p = RACINE / "app" / "src" / "main" / "assets" / "anim" / "abyssor" / st / "content.webp"
            if p.exists():
                imgs.append((st if st != "finale" else "final", ouvrir(p).crop((0, 0, 128, 128))))
        cellw = (W - 2 * MARGE) / max(1, len(imgs))
        for i, (st, im) in enumerate(imgs):
            dessiner_image(c, rogner(im), MARGE + i * cellw + 8, bas + 14, cellw - 16, hz - 10, ancre="b")
            c.setFont(F["pixel"], 13)
            c.setFillColor(DOUX)
            c.drawCentredString(MARGE + i * cellw + cellw / 2, bas, st)
    else:
        cellw = (W - 2 * MARGE) / 5
        ims = [(st, image_creature(e, "classique", st)) for st in STADES]
        ims = [(st, ouvrir(p)) for st, p in ims if p]
        if ims:
            ref = max(im.height for _, im in ims)
            r = min((hz - 10) / ref, (cellw - 10) / max(im.width for _, im in ims))
            for i, (st, im) in enumerate(ims):
                b = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, im.width, im.height)
                cr = im.crop((b[0], b[1], b[2], im.height))          # même échelle pour tous ; posés au sol
                cx = MARGE + i * cellw + cellw / 2
                poser(c, cr, cx - cr.width * r / 2, bas + 14, cr.width * r, cr.height * r)
                c.setFont(F["pixel"], 13)
                c.setFillColor(DOUX)
                c.drawCentredString(cx, bas, STADE_NOM[st])
    # les variantes (adultes)
    vars_ = [v for v in e.get("variantes", []) if v["id"] != "classique"]
    if vars_:
        c.setFont(F["titre"], 8)
        c.setFillColor(VERT)
        c.drawString(MARGE, bas - 22, "SES VARIANTES")
        n = len(vars_)
        cellw = min(80, (W - 2 * MARGE) / n)
        for i, v in enumerate(vars_):
            x = MARGE + i * cellw
            p = image_creature(e, v["id"], "adulte")
            if p:
                dessiner_image(c, rogner(ouvrir(p)), x + 4, 58, cellw - 8, 62, ancre="b")
            rare = v.get("chance", 100) < 10
            c.setFont(F["texte"] if rare else F["pixel"], 9 if rare else 12)
            c.setFillColor(OR if rare else DOUX)
            c.drawCentredString(x + cellw / 2, 44, (ETOILE + " " if rare else "") + v.get("nom", v["id"]))
    L.suivante(e["nom"])


def page_fin(L):
    c = L.c
    fond_page(c, 9999)
    L.marque("Crédits et licence")
    titre_pixel(c, "CRÉDITS", MARGE, H - 90, 22)
    paras(c, [
        "Terminagotchi est un jeu libre, fait par <b>les contributeurs de Terminagotchi</b>.",
        "Les images, les dessins et les textes de l'histoire de ce livre sont sous licence <b>Creative Commons "
        "Attribution - Pas d'Utilisation Commerciale - Partage dans les Mêmes Conditions 4.0 International "
        "(CC BY-NC-SA 4.0)</b> : tu peux les partager et les transformer, sans gagner d'argent avec, en citant "
        "« les contributeurs de Terminagotchi » et en partageant ta version sous la même licence. "
        "Texte officiel : creativecommons.org/licenses/by-nc-sa/4.0/deed.fr",
        "Le code du jeu (et le programme qui fabrique ce livre) est sous licence GNU GPL version 3 ou ultérieure.",
        "Polices : Press Start 2P et VT323 (SIL Open Font License 1.1) ; DejaVu Sans.",
        "La mascotte du site n'apparaît pas dans ce livre : elle n'est pas sous cette licence.",
    ], MARGE, H - 130, W - 2 * MARGE, style(12), 12)
    c.setFont(F["pixel"], 18)
    c.setFillColor(VERT)
    c.drawCentredString(W / 2, 120, "$ echo \"à bientôt dans le Terminaworld\"")
    L.suivante("Crédits")


def remplir_sommaire(chemin, L):
    """Deuxième passage : le sommaire de la page 2 avec les vrais numéros (on réécrit la page par-dessus)."""
    from pypdf import PdfReader, PdfWriter
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    global F
    y = L._y_sommaire
    gros = [(t, n) for t, n in L.sommaire if not t.startswith(("Biome :", "Monde :", "Famille :"))]
    fam = [(t, n) for t, n in L.sommaire if t.startswith("Famille :")]
    lignes = gros[1:]
    lignes.insert(lignes.index(next(x for x in lignes if x[0] == "Le bestiaire")) + 1, ("Les posters, famille par famille", fam[0][1] if fam else 0))
    for t, n in lignes:
        c.setFont(F["texte"], 12.5)
        c.setFillColor(TEXTE)
        c.drawString(MARGE + 14, y, t)
        c.setFillColor(VERT)
        c.rect(MARGE, y + 3, 6, 6, stroke=0, fill=1)
        c.setFont(F["pixel"], 16)
        c.drawRightString(W - MARGE, y, str(n))
        c.setFillColor(CADRE)
        tw = pdfmetrics.stringWidth(t, F["texte"], 12.5)
        for xx in range(int(MARGE + 24 + tw), int(W - MARGE - 30), 6):
            c.rect(xx, y + 2, 2, 2, stroke=0, fill=1)
        y -= 24
    c.save()
    r = PdfReader(str(chemin))
    s = PdfReader(io.BytesIO(tampon.getvalue()))
    w = PdfWriter(clone_from=r)
    w.pages[L._page_sommaire - 1].merge_page(s.pages[0])
    with open(chemin, "wb") as f:
        w.write(f)


def apercus(pdf, dossier, pages):
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    for nom, p in pages.items():
        out = dossier / nom
        subprocess.run(["pdftoppm", "-png", "-r", "80", "-f", str(p), "-l", str(p), "-singlefile", str(pdf),
                        str(out)], check=True)
    print(f"aperçus : {dossier}")


def main():
    global F
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apercu", help="dossier où écrire quelques pages en PNG (pdftoppm)")
    ap.add_argument("--manquantes", action="store_true", help="liste les illustrations attendues absentes")
    ap.add_argument("--sortie", default=str(SORTIE))
    a = ap.parse_args()
    F = polices()
    if F["texte"] == "Helvetica":
        globals()["ETOILE"] = "*"
    best, fr, biomes = charger()
    carte = RACINE / "donnees" / "illustrations" / "monde.png"
    camp = RACINE / "donnees" / "illustrations" / "camp2.png"
    ILLU.mkdir(exist_ok=True)
    L = Livre(a.sortie)
    especes = sorted(best["especes"], key=lambda e: e["numero"])
    page_couverture(L, carte)
    page_bienvenue(L, len(especes))
    page_histoire(L, camp)
    pages_carte(L, carte)
    page_racine(L)
    page_biomes_intro(L)
    pages_biomes(L, best, biomes, fr)
    page_mondes_intro(L)
    pages_mondes(L)
    page_bestiaire_intro(L, best)
    familles = []
    for e in especes:
        if e["famille"] not in familles:
            familles.append(e["famille"])
    reperes = {}
    for fam in familles:
        liste = [e for e in especes if e["famille"] == fam]
        if fam != "Système":
            page_famille(L, fam, liste)
        else:
            fond_page(L.c, 777)
            L.marque("Le légendaire secret")
            titre_pixel(L.c, "LE SECRET", MARGE, H - 90, 22, ROSE)
            para(L.c, "Tout au fond de la grotte dort une créature que presque personne n'a vue. On dit qu'elle ne se "
                      "montre qu'aux maîtres qui ont déjà dressé trois légendaires… Tourne la page si tu oses.",
                 MARGE, H - 130, W - 2 * MARGE, style(14))
            L.suivante("Le secret")
        for e in liste:
            reperes[e["id"]] = L.n
            poster(L, e, biomes, best)
    page_fin(L)
    L.c.save()
    try:
        remplir_sommaire(a.sortie, L)
    except ImportError:
        print("(pypdf absent : le sommaire de la page 2 reste vide ; les signets du PDF suffisent)")
    pres = sum(1 for _, _, ok in ATTENDUES if ok)
    print(f"{a.sortie} : {L.n - 1} pages, {os.path.getsize(a.sortie) // 1024 // 1024} Mo ; "
          f"illustrations : {pres} / {len(ATTENDUES)} présentes")
    if a.manquantes:
        vus = set()
        for f, leg, ok in ATTENDUES:
            if f not in vus and not ok:
                vus.add(f)
                print(f"  à venir : docs/artbook/illustrations/{f}  — {leg}")
    if a.apercu:
        n = {t: p for t, p in L.sommaire}
        apercus(a.sortie, a.apercu, {
            "01_couverture": 1, "02_sommaire": 2, "03_histoire": n["L'histoire du Terminaworld"],
            "04_carte_gauche": n["La carte du Terminaworld"], "05_carte_droite": n["La carte du Terminaworld"] + 1,
            "06_racine": n["La Racine et les lieux du système"], "07_biome_feu": n["Biome : Le Feu"],
            "08_monde_port": n["Monde : Le Port"], "09_famille_demons": n["Famille : Démons"],
            "10_poster_braisillon": reperes.get("braisillon", 1), "11_poster_abyssor": reperes.get("abyssor", 1),
            "12_poster_tellurion": reperes.get("tellurion", 1),
        })


if __name__ == "__main__":
    main()
