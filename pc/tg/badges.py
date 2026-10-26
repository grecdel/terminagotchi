"""Les badges de la salle d'entraînement : un dessin en pixels par famille, une couleur par échelon.

Les badges appartiennent à la PARTIE (ils mesurent ce que l'enfant sait faire), pas à la créature :
la créature, elle, ne gagne que de l'XP.

8 familles (les commandes qu'elles entraînent) :
  explorateur  cd, ls, pwd           batisseur  mkdir, touch        demenageur  cp, mv
  nettoyeur    rm, rmdir, rm -r      lecteur    cat, head, tail     detective   grep, find
  plombier     |  >  >>              cuisinier  recettes (scripts), chmod
5 échelons : Bois → Bronze → Argent → Or → Diamant, à 1 / 5 / 15 / 30 / 50 exercices réussis dans la
famille ; le Diamant demande en plus au moins une médaille d'or (ou de diamant) en temps dans la famille.

Le dessin : 14 × 14 pixels (un écusson). Mêmes données dans l'appli (Badges.kt) et sur le site
(site/src/badges.js) ; les couleurs y sont identiques.
  .  transparent    o  contour    f  fond    h  reflet    i  dessin    k  détail du dessin    s  étincelle
Dans le terminal, un pixel = un demi-caractère « ▀ » (14 colonnes × 7 lignes).
"""
FAMILLES = ("explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier")
ECHELONS = ("bois", "bronze", "argent", "or", "diamant")
SEUILS = (1, 5, 15, 30, 50)

# couleurs : contour, fond, reflet, dessin, détail
COULEURS = {
    "bois":    ("#3a2a1a", "#76583a", "#987654", "#efe0c4", "#4a3522"),
    "bronze":  ("#6b3510", "#d0782a", "#f6ad62", "#fff3e0", "#7a3c0c"),
    "argent":  ("#4a525e", "#aab5c2", "#e6edf4", "#323a47", "#6b7685"),
    "or":      ("#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"),
    "diamant": ("#0b4a66", "#3fcfff", "#d2f8ff", "#06324a", "#1a7fae"),
    "cache":   ("#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"),   # famille pas encore découverte
}
ETINCELLE = "#ffffff"

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
# l'étincelle du diamant (coin en haut à droite)
ETINCELLES = [(1, 12), (0, 12), (2, 12), (1, 11), (1, 13)]


def grille(famille, echelon):
    """La grille 14 × 14 de couleurs « #rrggbb » (None = transparent).
    famille = None ou echelon = None : la famille pas encore découverte (gris, « ? »)."""
    cache = famille is None or echelon is None
    c = COULEURS["cache" if cache else echelon]
    pal = {"o": c[0], "f": c[1], "h": c[2], "i": c[3], "k": c[4], "K": c[4]}
    g = [[pal.get(x) for x in ligne] for ligne in FORME]
    ic = ICONES["cache" if cache else famille]
    for y, ligne in enumerate(ic):
        for x, ch in enumerate(ligne):
            if ch != ".":
                g[3 + y][3 + x] = pal[ch]
    if echelon == "diamant" and not cache:
        for y, x in ETINCELLES:
            g[y][x] = ETINCELLE
    return g


def echelon_de(n, ors=0):
    """L'échelon atteint (indice 0…4, ou -1) avec n réussites et `ors` médailles d'or ou de diamant."""
    k = -1
    for i, s in enumerate(SEUILS):
        if n >= s and (i < 4 or ors >= 1):
            k = i
    return k


# ---------------------------------------------------------------- dans le terminal
def couleur_ansi(echelon):
    """La couleur du texte d'un échelon (son reflet), pour les noms et les titres."""
    return f"\x1b[38;2;{_rvb(COULEURS[echelon or 'cache'][2])}m"


def _rvb(h):
    return ";".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5))




def lignes_terminal(famille, echelon):
    """Le badge en 7 lignes de 14 caractères « ▀ » colorés (haut = couleur du texte, bas = fond)."""
    g = grille(famille, echelon)
    out = []
    for y in range(0, 14, 2):
        s = ""
        for x in range(14):
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


def planche(cases, par_ligne=4, largeur_case=17):
    """Les badges côte à côte : cases = [(famille, echelon, [(texte, couleur) sous le badge])] (famille None =
    « ??? » ; couleur = séquence ANSI ou ""). Renvoie les lignes du terminal (le texte sous chaque badge est centré, coupé à la largeur de la case)."""
    from .langue import largeur, raccourcir
    out = []
    for i in range(0, len(cases), par_ligne):
        rang = cases[i:i + par_ligne]
        dessins = [lignes_terminal(f, e) for f, e, _ in rang]
        marge = (largeur_case - 14) // 2
        for y in range(7):
            out.append(" " + "".join(" " * marge + d[y] + " " * (largeur_case - 14 - marge) for d in dessins))
        n = max(len(t) for _, _, t in rang)
        for y in range(n):
            ligne = " "
            for _, _, t in rang:
                x, c = t[y] if y < len(t) else ("", "")
                brut = raccourcir(x, largeur_case - 1)
                vis = largeur(brut)
                g = (largeur_case - vis) // 2
                ligne += " " * g + c + brut + "\x1b[0m" + " " * (largeur_case - vis - g)
            out.append(ligne)
        out.append("")
    return out
