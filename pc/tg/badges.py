"""Les badges de la salle d'entraînement : un dessin en pixels par famille, un grade par échelon, des étoiles.

Les badges appartiennent à la PARTIE (ils mesurent ce que l'enfant sait faire), pas à la créature :
la créature, elle, ne gagne que de l'XP.

8 familles (les commandes qu'elles entraînent) :
  explorateur  cd, ls, pwd           batisseur  mkdir, touch        demenageur  cp, mv
  nettoyeur    rm, rmdir, rm -r      lecteur    cat, head, tail     detective   grep, find
  plombier     |  >  >>              cuisinier  recettes (scripts), chmod
8 échelons (des tailles d'informatique) : Bit → Octet → Kilo → Méga → Giga → Téra → Péta → Exa, à 1 / 5 / 15 / 30 /
50 / 100 / 200 / 400 exercices réussis dans la famille ; en plus, en médailles de temps dans la famille : Giga au moins
une d'or (ou de diamant), Téra 3 de diamant, Péta 6 de diamant, Exa 10 de diamant ET chaque exercice de la famille
réussi au moins une fois (il a un record ; ça marche hors ligne).
(Avant : Bois / Bronze / Argent / Or / Diamant ; ANCIENS sert à reprendre les vieilles sauvegardes.)

Chaque échelon a son GRADE, dessiné comme les galons des militaires, sous l'écusson :
  Bit 1 chevron · Octet 2 chevrons · Kilo 3 chevrons · Méga 3 chevrons + un arc de pistes dorées (circuit
  imprimé) · Giga 3 chevrons + des ailes de pistes lumineuses et une puce au centre (+ l'étincelle) · Téra : une
  couronne de pistes arc-en-ciel autour de l'écusson, la puce au cœur brillant, un joyau sous les chevrons ·
  Péta : en plus, des orbites et deux satellites en bas, une étoile posée au-dessus de l'écusson (devant) ·
  Exa : en plus, un halo de galaxie tout autour (nébuleuse, étoiles, constellations), jusque derrière les étoiles.
Et des ÉTOILES (0 à 3, au-dessus de l'écusson) : le chemin vers l'échelon suivant, coupé en quarts (arrondis
au-dessus) ; à l'Exa, elles continuent à 600 / 800 / 1000 réussites. Voir ETOILES.

Le dessin complet (« ecusson ») : 18 × 28 pixels. Lignes 0-3 : les 3 étoiles (x = 0, 6, 12) ; l'écusson
14 × 14 en (2, 4) ; les galons dessous et derrière. Mêmes données dans l'appli (Badges.kt) et sur le site
(site/src/entrainement.js) ; les couleurs y sont identiques.
  Écusson :  .  transparent    o  contour    f  fond    h  reflet    i  dessin    k  détail du dessin
  Galons :   a  contour   b  reflet   c  fond (couleurs de l'échelon)    d e g  pistes dorées (contour, piste, via)
             q r s  pistes lumineuses du Giga    z y x  la puce (contour, dessus, corps)    p  pattes de la puce
             1…6  pistes arc-en-ciel du Téra    n  leur contour    v  via    w u  cœur brillant (blanc, cyan)
             o  orbites   L P  satellites    ~ :  halo (espace, nébuleuse)   *  étoile   +  constellation
  Devant l'écusson (DEVANT, Péta et Exa) :  S W s  l'étoile posée dessus (or, cœur blanc, scintillement)
Dans le terminal, un pixel = un demi-caractère « ▀ » (18 colonnes × 14 lignes).
"""
FAMILLES = ("explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier")
ECHELONS = ("bit", "octet", "kilo", "mega", "giga", "tera", "peta", "exa")
SEUILS = (1, 5, 15, 30, 50, 100, 200, 400)
# médailles de diamant demandées par grade (Téra 3, Péta 6, Exa 10) ; le Giga demande 1 médaille d'or ou de diamant
DIAMANTS = (0, 0, 0, 0, 0, 3, 6, 10)
# les étoiles de chaque échelon : réussites pour ★, ★★, ★★★ (quarts du chemin vers l'échelon suivant)
ETOILES = ((2, 3, 4), (8, 10, 13), (19, 23, 27), (35, 40, 45), (63, 75, 88), (125, 150, 175), (250, 300, 350),
           (600, 800, 1000))
ANCIENS = {"bois": "bit", "bronze": "octet", "argent": "kilo", "or": "mega", "diamant": "giga"}

# couleurs : contour, fond, reflet, dessin, détail (vert circuit → cyan → bleu → violet → or → nacre holographique →
# rubis → cosmos)
COULEURS = {
    "bit":   ("#0d3b1e", "#2f9e4f", "#86e89a", "#eaffe9", "#17602f"),
    "octet": ("#08404d", "#22b0c6", "#a6f3ff", "#062f3a", "#127688"),
    "kilo":  ("#152a78", "#4072f0", "#b1c8ff", "#f0f4ff", "#2240b0"),
    "mega":  ("#3d0f60", "#a050e6", "#e2b8ff", "#fff0ff", "#5e1f92"),
    "giga":  ("#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"),
    "tera":  ("#4b3a8c", "#dfe9ff", "#ffffff", "#4b3a8c", "#ff6fd8"),
    "peta":  ("#4a0a18", "#e8344e", "#ff9aa8", "#fff0f0", "#8a1028"),
    "exa":   ("#0b0626", "#3a1f9e", "#9f8bff", "#ffe36e", "#ff7ad9"),
    "cache": ("#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"),   # famille pas encore découverte
}
ETINCELLE = "#ffffff"
# couleurs fixes des galons (pistes, puce)
FIXES = {"d": "#4a3000", "e": "#d9a41a", "g": "#fff27a", "q": "#0b3f55", "r": "#3fd6ff", "s": "#ffffff",
         "z": "#0c0c10", "y": "#4a4a5e", "x": "#262630", "p": "#d8d8e0",
         "1": "#ff5a6e", "2": "#ffa63d", "3": "#ffe94a", "4": "#5cff86", "5": "#4ad8ff", "6": "#b46cff",
         "n": "#1a0d33", "v": "#ffffff", "w": "#ffffff", "u": "#8ff7ff",
         "o": "#cfd8ff", "L": "#fff3b0", "P": "#ff9f43", "~": "#14214f", ":": "#5a2470", "*": "#ffffff", "+": "#7f9cff",
         "S": "#ffd84a", "W": "#ffffff", "s": "#fff6c8"}
ETOILE_ON, ETOILE_OFF = "#ffd84a", "#3c3c4a"
LARGEUR, HAUTEUR, BX, BY = 18, 28, 2, 4

FORME = [
    "...oooooooo...",
    "..ohhhhhhhhfo.",
    ".ohhffffffffo.",
    "ohhffffffffffo",
    "ohfffffffffffo",
    "ohfffffffffffo",
    "ohfffffffffffo",
    "ohfffffffffffo",
    "ohfffffffffffo",
    "offfffffffffo.",
    ".offfffffffo..",
    "..offfffffo...",
    "...offfffo....",
    ".....ooo......",
]

ICONES = {
    "explorateur": [          # une boussole
        "...ii...",
        "...ii...",
        "..ikki..",
        "iiikkiii",
        "iiiKKiii",
        "..iKKi..",
        "...ii...",
        "...ii...",
    ],
    "batisseur": [            # une maison et sa porte
        "...ii...",
        "..iiii..",
        ".iiiiii.",
        "iiiiiiii",
        ".iiiiii.",
        ".iikkii.",
        ".iikkii.",
        ".iikkii.",
    ],
    "demenageur": [           # un carton qui part (flèche)
        "....i...",
        "....ii..",
        "iiiiiii.",
        "iiiiiiii",
        "iiiiiii.",
        "....ii..",
        "....i...",
        "........",
    ],
    "nettoyeur": [            # un balai
        ".......i",
        "......i.",
        ".....i..",
        "....i...",
        "..kkkk..",
        ".iiiiii.",
        "iiiiiii.",
        "i.i.i.i.",
    ],
    "lecteur": [              # un livre ouvert
        "iii..iii",
        "iiiiiiii",
        "ikkiikki",
        "iiiiiiii",
        "ikkiikki",
        "iiiiiiii",
        "ikkiikki",
        "iiiiiiii",
    ],
    "detective": [            # une loupe
        "..iiii..",
        ".i....i.",
        "i......i",
        "i......i",
        ".i....i.",
        "..iiiik.",
        "......kk",
        ".......k",
    ],
    "plombier": [             # un tuyau et sa goutte
        "iiiiii..",
        "kkkkkii.",
        "iiiiiii.",
        ".....ii.",
        ".....ii.",
        "....iiii",
        "........",
        ".....k..",
    ],
    "cuisinier": [            # une toque
        ".i.ii.i.",
        "iiiiiiii",
        "iiiiiiii",
        ".iiiiii.",
        "..iiii..",
        "..kkkk..",
        "..iiii..",
        "..iiii..",
    ],
    "cache": [                # « ??? »
        "..iiii..",
        ".ii..ii.",
        ".....ii.",
        "....ii..",
        "...ii...",
        "...ii...",
        "........",
        "...ii...",
    ],
}
# l'étincelle du Giga et au-delà (coin en haut à droite de l'écusson)
ETINCELLES = [(1, 12), (0, 12), (2, 12), (1, 11), (1, 13)]

# les galons : (première ligne, lignes de 18 pixels) ; dessinés derrière l'écusson
GALONS = {
    "bit": (16, [
        ".......aaa........",
        ".....aabbbaa......",
        "...aabbcccbbaa....",
        "..abbccaaaccbba...",
        ".abccaa...aaccba..",
        ".acaa.......aaca..",
        "..a...........a...",
    ]),
    "octet": (16, [
        ".......aaa........",
        ".....aabbbaa......",
        "...aabbcccbbaa....",
        "..abbccaaaccbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaa...aaccba..",
        ".acaa.......aaca..",
        "..a...........a...",
    ]),
    "kilo": (16, [
        ".......aaa........",
        ".....aabbbaa......",
        "...aabbcccbbaa....",
        "..abbccaaaccbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaa...aaccba..",
        ".acaa.......aaca..",
    ]),
    "mega": (7, [
        "d................d",
        "gd..............dg",
        "ed..............de",
        "egd............dge",
        "ed..............de",
        "egd............dge",
        "ed..............de",
        "egd............dge",
        "ed..............de",
        "ded....aaa.....ded",
        ".ded.aabbbaa..ded.",
        "..daabbcccbbaaed..",
        "..abbccaaaccbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaa...aaccba..",
        ".acaa.......aaca..",
    ]),
    "giga": (4, [
        "q................q",
        "sq..............qs",
        "rsq............qsr",
        "rrq............qrr",
        "rsq............qsr",
        "rrq............qrr",
        "rsq............qsr",
        "rrq............qrr",
        "rsq............qsr",
        "rrq............qrr",
        "rsq............qsr",
        "rrq............qrr",
        "qrrq...aaa....qrrq",
        ".qrrqaabbbaa.qrrq.",
        "..qaabpcpcpbaarq..",
        "..abbzyyyyyzbba...",
        ".abcczxsxxxzccba..",
        ".acaazxxxxxzaaca..",
        "..abbcpapapcbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaa...aaccba..",
        ".acaa.......aaca..",
    ]),
    "tera": (4, [
        "1111n........n1111",
        "1v1n..........n1v1",
        "1vn............nv1",
        "22n............n22",
        "2vn............nv2",
        "33n............n33",
        "3vn............nv3",
        "33n............n33",
        "4vn............nv4",
        "44n............n44",
        "5vn............nv5",
        "55n............n55",
        "n55n...aaa....n55n",
        ".n66naabbbaa.n66n.",
        "..naabpcpcpbaa6n..",
        "..abbzyyyyyzbba...",
        ".abcczxuwuxzccba..",
        ".acaazxuuuxzaaca..",
        "..abbcpapapcbba...",
        ".abccaabbbaaccba..",
        ".acaabbcccbbaaca..",
        "..abbccaaaccbba...",
        ".abccaanwnaaccba..",
        ".acaa.nuwun.aaca..",
    ]),
    "peta": (4, [
        "1111n........n1111",
        "1v1n..........n1v1",
        "1vn............nv1",
        "22n............n22",
        "2vn............nv2",
        "33n............n33",
        "3vn............nv3",
        "33n............n33",
        "4vn............nv4",
        "44n............n44",
        "5vn............nv5",
        "55n............n55",
        "n55n...aaa....n55n",
        ".n66naabbbaa.n66n.",
        "o.naabpcpcpbaa6n.o",
        "..abbzyyyyyzbba...",
        "oabcczxuwuxzccba.o",
        "LPcaazxuuuxzaaca..",
        "PPabbcpapapcbba..o",
        "oabccaabbbaaccba.o",
        "oacaabbcccbbaacaLP",
        "..abbccaaaccbba.PP",
        "oabccaanwnaaccbaoo",
        ".acaa.nuwun.aaca..",
    ]),
    "exa": (0, [
        "..:~~*~~:~~*~:~~..",
        ".~~:~~:~~:~:~~:~+.",
        "~+~~:~~:~:~*:~~:~~",
        "*~:~~:~:~~:~~:~~:~",
        "1111n:~~:~~:~n1111",
        "1v1n~~:~~:~~:~n1v1",
        "1vn~:~~:~~:~:~~nv1",
        "22n~~:~~:~:~~:~n22",
        "2vn:~~:~:~~:~~:nv2",
        "33n~:~:~~:~~:~~n33",
        "3vn~:~~:~~:~~:~nv3",
        "33n~~:~~:~~:~:~n33",
        "4vn:~~:~~:~:~~:nv4",
        "44n~:~~:~:~~:~~n44",
        "5vn~~:~:~~:~~:*nv5",
        "55n:~:~~:~~:~~:n55",
        "n55n~~:aaa~~:*n55n",
        "~n66naabbbaa:n66n~",
        "o~naabpcpcpbaa6n:o",
        ":~abbzyyyyyzbba~~:",
        "oabcczxuwuxzccba~o",
        "LPcaazxuuuxzaaca~~",
        "PPabbcpapapcbba~:o",
        "oabccaabbbaaccba~o",
        "oacaabbcccbbaacaLP",
        "~~abbccaaaccbba~PP",
        "oabccaanwnaaccbaoo",
        ".acaa~nuwun~aaca..",
    ]),
}
# devant l'écusson (Péta, Exa) : l'étoile posée dessus
DEVANT = {
    "peta": (3, [
        "........s.........",
        "........S.........",
        "......sSWSs.......",
        "........S.........",
    ]),
    "exa": (3, [
        "........s.........",
        "........S.........",
        "......sSWSs.......",
        "........S.........",
    ]),
}
ETOILE = ["..x..", ".xxx.", "xxxxx", ".x.x."]
X_ETOILES = (0, 6, 12)


def grille(famille, echelon):
    """L'écusson seul : grille 14 × 14 de couleurs « #rrggbb » (None = transparent).
    famille = None ou echelon = None : la famille pas encore découverte (gris, « ? »)."""
    cache = famille is None or echelon not in ECHELONS
    c = COULEURS["cache" if cache else echelon]
    pal = {"o": c[0], "f": c[1], "h": c[2], "i": c[3], "k": c[4], "K": c[4]}
    g = [[pal.get(x) for x in ligne] for ligne in FORME]
    ic = ICONES["cache" if cache else famille]
    for y, ligne in enumerate(ic):
        for x, ch in enumerate(ligne):
            if ch != ".":
                g[3 + y][3 + x] = pal[ch]
    if echelon in ECHELONS[4:] and not cache:
        for y, x in ETINCELLES:
            g[y][x] = ETINCELLE
    return g


def _couche(g, echelon, motifs):
    c = COULEURS[echelon]
    pal = dict(FIXES, a=c[0], b=c[2], c=c[1])
    if echelon in motifs:
        y0, lignes = motifs[echelon]
        for y, ligne in enumerate(lignes):
            for x, ch in enumerate(ligne):
                if ch != ".":
                    g[y0 + y][x] = pal[ch]
    return g


def galons(echelon, devant=True):
    """Le grade seul : grille 18 × 28 (None = transparent), sans écusson ni étoiles (avec ce qui passe devant)."""
    g = [[None] * LARGEUR for _ in range(HAUTEUR)]
    if echelon not in ECHELONS:
        return g
    _couche(g, echelon, GALONS)
    return _couche(g, echelon, DEVANT) if devant else g


def ecusson(famille, echelon, etoiles=0):
    """Le badge complet 18 × 28 : galons (derrière), écusson, et les 3 étoiles (0 à 3 allumées) au-dessus.
    Famille pas encore découverte (famille ou echelon None) : l'écusson gris seul."""
    cache = famille is None or echelon not in ECHELONS
    g = galons(None if cache else echelon, devant=False)
    for y, ligne in enumerate(grille(famille, echelon)):
        for x, col in enumerate(ligne):
            if col:
                g[BY + y][BX + x] = col
    if not cache:
        _couche(g, echelon, DEVANT)
        for i, x0 in enumerate(X_ETOILES):
            for y, ligne in enumerate(ETOILE):
                for x, ch in enumerate(ligne):
                    if ch == "x":
                        g[y][x0 + x] = ETOILE_ON if i < etoiles else ETOILE_OFF
    return g


def echelon_de(n, ors=0, diamants=0, tous_types=False):
    """L'échelon atteint (indice 0…7, ou -1) avec n réussites, `ors` médailles d'or ou de diamant (Giga : 1),
    `diamants` médailles de diamant (DIAMANTS : Téra 3, Péta 6, Exa 10) et, pour l'Exa, chaque exercice de la
    famille réussi au moins une fois (`tous_types`). On monte dans l'ordre : pas de Téra sans Giga, etc."""
    k = -1
    for i, s in enumerate(SEUILS):
        if n >= s and (i < 4 or ors >= 1) and diamants >= DIAMANTS[i] and (i < 7 or tous_types):
            k = i
        else:
            break
    return k


def etoiles_de(n, k):
    """Les étoiles (0…3) dans l'échelon k avec n réussites (k = -1 : aucune)."""
    return 0 if k < 0 else sum(1 for s in ETOILES[k] if n >= s)


def prochaine_etoile(n, k):
    """Le nombre de réussites de la prochaine étoile dans l'échelon k, ou None (3 étoiles)."""
    return next((s for s in ETOILES[k] if n < s), None) if k >= 0 else None


def texte_etoiles(n):
    return "★" * n + "☆" * (3 - n)


# ---------------------------------------------------------------- dans le terminal
def couleur_ansi(echelon):
    """La couleur du texte d'un échelon (son reflet), pour les noms et les titres."""
    return f"\x1b[38;2;{_rvb(COULEURS[echelon if echelon in COULEURS else 'cache'][2])}m"


def _rvb(h):
    return ";".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5))


def lignes_grille(g):
    """Une grille de pixels (hauteur paire) en lignes de caractères « ▀ » colorés (haut = texte, bas = fond)."""
    out = []
    for y in range(0, len(g), 2):
        s = ""
        for x in range(len(g[y])):
            a, b = g[y][x], g[y + 1][x]
            if a is None and b is None:
                s += "\x1b[0m "
            elif a is None:
                s += f"\x1b[0m\x1b[38;2;{_rvb(b)}m▄"
            elif b is None:
                s += f"\x1b[0m\x1b[38;2;{_rvb(a)}m▀"
            else:
                s += f"\x1b[38;2;{_rvb(a)};48;2;{_rvb(b)}m▀"
        out.append(s + "\x1b[0m")
    return out


def lignes_terminal(famille, echelon, etoiles=0):
    """Le badge complet en 14 lignes de 18 caractères."""
    return lignes_grille(ecusson(famille, echelon, etoiles))


def planche(cases, par_ligne=4, largeur_case=19):
    """Les badges côte à côte : cases = [(famille, echelon, etoiles, [(texte, couleur) sous le badge])] (famille None =
    « ??? » ; couleur = séquence ANSI ou ""). Renvoie les lignes du terminal (le texte sous chaque badge est centré,
    coupé à la largeur de la case)."""
    from .langue import largeur, raccourcir
    out = []
    for i in range(0, len(cases), par_ligne):
        rang = cases[i:i + par_ligne]
        dessins = [lignes_terminal(f, e, n) for f, e, n, _ in rang]
        marge = (largeur_case - LARGEUR) // 2
        for y in range(HAUTEUR // 2):
            out.append(" " + "".join(" " * marge + d[y] + " " * (largeur_case - LARGEUR - marge) for d in dessins).rstrip())
        n = max(len(t) for *_, t in rang)
        for y in range(n):
            ligne = " "
            for *_, t in rang:
                x, c = t[y] if y < len(t) else ("", "")
                brut = raccourcir(x, largeur_case - 1)
                vis = largeur(brut)
                g = (largeur_case - vis) // 2
                ligne += " " * g + c + brut + "\x1b[0m" + " " * (largeur_case - vis - g)
            out.append(ligne.rstrip())
        out.append("")
    return out
