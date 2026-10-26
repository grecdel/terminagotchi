package fr.terminagotchi

import android.graphics.Bitmap

/**
 * Les badges de la salle d'entraînement (portage de pc/tg/badges.py, mêmes dessins et mêmes couleurs ;
 * le site a les siens dans site/src/entrainement.js ; vecteurs communs des dessins : donnees/entrainement/vecteurs.json).
 *
 * Les badges appartiennent à la PARTIE (ce que l'enfant sait faire), pas à la créature (elle gagne de l'XP).
 * 8 familles, 6 grades (des tailles d'informatique) : Bit → Octet → Kilo → Méga → Giga → Téra, à 1 / 5 / 15 / 30 / 50 / 100
 * exercices réussis dans la famille ; le Giga demande en plus au moins une médaille d'or (ou de diamant) en temps,
 * le Téra au moins 3 médailles de diamant.
 * Chaque grade a ses galons sous l'écusson (1, 2, 3 chevrons ; + pistes dorées au Méga ; ailes lumineuses et puce
 * au Giga ; couronne arc-en-ciel, cœur brillant et joyau au Téra) et 0 à 3 étoiles au-dessus : le chemin vers le
 * grade suivant (ETOILES ; au Téra : 150 / 200 / 300).
 * Écusson 14 × 14 : . transparent, o contour, f fond, h reflet, i dessin, k/K détail.
 * Badge complet (ecusson) 18 × 28 : étoiles lignes 0-3 (x = 0, 6, 12), écusson en (2, 4), galons derrière
 * (a b c : couleurs du grade ; d e g pistes dorées ; q r s pistes lumineuses ; z y x p la puce ;
 * 1…6 pistes arc-en-ciel, n leur contour, v via, w u cœur brillant).
 * Dans le terminal de l'appli : la balise ¤badge:<famille>:<grade>~<étoiles>¤ (famille « cache » = « ??? » ;
 * sans ~ : l'écusson seul).
 */
object Badges {
    val FAMILLES = listOf("explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier")
    val ECHELONS = listOf("bit", "octet", "kilo", "mega", "giga", "tera")
    val SEUILS = listOf(1, 5, 15, 30, 50, 100)
    const val DIAMANTS_TERA = 3
    /** Les étoiles de chaque grade : réussites pour ★, ★★, ★★★. */
    val ETOILES = listOf(listOf(2, 3, 4), listOf(8, 10, 13), listOf(19, 23, 27), listOf(35, 40, 45), listOf(63, 75, 88), listOf(150, 200, 300))
    /** Les anciens noms (vieilles sauvegardes : le titre choisi). */
    val ANCIENS = mapOf("bois" to "bit", "bronze" to "octet", "argent" to "kilo", "or" to "mega", "diamant" to "giga")

    /** contour, fond, reflet, dessin, détail (vert circuit → cyan → bleu → violet → or → nacre holographique) */
    val COULEURS: Map<String, List<String>> = mapOf(
        "bit" to listOf("#0d3b1e", "#2f9e4f", "#86e89a", "#eaffe9", "#17602f"),
        "octet" to listOf("#08404d", "#22b0c6", "#a6f3ff", "#062f3a", "#127688"),
        "kilo" to listOf("#152a78", "#4072f0", "#b1c8ff", "#f0f4ff", "#2240b0"),
        "mega" to listOf("#3d0f60", "#a050e6", "#e2b8ff", "#fff0ff", "#5e1f92"),
        "giga" to listOf("#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"),
        "tera" to listOf("#4b3a8c", "#dfe9ff", "#ffffff", "#4b3a8c", "#ff6fd8"),
        "cache" to listOf("#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"),
    )
    const val ETINCELLE = "#ffffff"
    val FIXES = mapOf('d' to "#4a3000", 'e' to "#d9a41a", 'g' to "#fff27a", 'q' to "#0b3f55", 'r' to "#3fd6ff", 's' to "#ffffff", 'z' to "#0c0c10", 'y' to "#4a4a5e", 'x' to "#262630", 'p' to "#d8d8e0", '1' to "#ff5a6e", '2' to "#ffa63d", '3' to "#ffe94a", '4' to "#5cff86", '5' to "#4ad8ff", '6' to "#b46cff", 'n' to "#1a0d33", 'v' to "#ffffff", 'w' to "#ffffff", 'u' to "#8ff7ff")
    const val ETOILE_ON = "#ffd84a"
    const val ETOILE_OFF = "#3c3c4a"
    const val LARGEUR = 18
    const val HAUTEUR = 28
    const val BX = 2
    const val BY = 4

    val FORME = listOf(
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
    )

    val ICONES: Map<String, List<String>> = mapOf(
        "explorateur" to listOf("...ii...", "...ii...", "..ikki..", "iiikkiii", "iiiKKiii", "..iKKi..", "...ii...", "...ii..."),
        "batisseur" to listOf("...ii...", "..iiii..", ".iiiiii.", "iiiiiiii", ".iiiiii.", ".iikkii.", ".iikkii.", ".iikkii."),
        "demenageur" to listOf("....i...", "....ii..", "iiiiiii.", "iiiiiiii", "iiiiiii.", "....ii..", "....i...", "........"),
        "nettoyeur" to listOf(".......i", "......i.", ".....i..", "....i...", "..kkkk..", ".iiiiii.", "iiiiiii.", "i.i.i.i."),
        "lecteur" to listOf("iii..iii", "iiiiiiii", "ikkiikki", "iiiiiiii", "ikkiikki", "iiiiiiii", "ikkiikki", "iiiiiiii"),
        "detective" to listOf("..iiii..", ".i....i.", "i......i", "i......i", ".i....i.", "..iiiik.", "......kk", ".......k"),
        "plombier" to listOf("iiiiii..", "kkkkkii.", "iiiiiii.", ".....ii.", ".....ii.", "....iiii", "........", ".....k.."),
        "cuisinier" to listOf(".i.ii.i.", "iiiiiiii", "iiiiiiii", ".iiiiii.", "..iiii..", "..kkkk..", "..iiii..", "..iiii.."),
        "cache" to listOf("..iiii..", ".ii..ii.", ".....ii.", "....ii..", "...ii...", "...ii...", "........", "...ii..."),
    )
    private val ETINCELLES = listOf(1 to 12, 0 to 12, 2 to 12, 1 to 11, 1 to 13)

    /** Les galons : (première ligne, lignes de 18 pixels), derrière l'écusson. */
    val GALONS: Map<String, Pair<Int, List<String>>> = mapOf(
        "bit" to (16 to listOf(
            ".......aaa........",
            ".....aabbbaa......",
            "...aabbcccbbaa....",
            "..abbccaaaccbba...",
            ".abccaa...aaccba..",
            ".acaa.......aaca..",
            "..a...........a...",
        )),
        "octet" to (16 to listOf(
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
        )),
        "kilo" to (16 to listOf(
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
        )),
        "mega" to (7 to listOf(
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
        )),
        "giga" to (4 to listOf(
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
        )),
        "tera" to (4 to listOf(
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
        )),
    )
    private val ETOILE = listOf("..x..", ".xxx.", "xxxxx", ".x.x.")
    private val X_ETOILES = listOf(0, 6, 12)

    /** L'écusson seul : grille 14 × 14 (« #rrggbb » ou null). famille ou grade null (ou « cache ») : pas encore découvert. */
    fun grille(famille: String?, echelon: String?): List<MutableList<String?>> {
        val cache = famille == null || famille == "cache" || famille !in ICONES || echelon !in ECHELONS
        val c = COULEURS.getValue(if (cache) "cache" else echelon!!)
        val pal = mapOf('o' to c[0], 'f' to c[1], 'h' to c[2], 'i' to c[3], 'k' to c[4], 'K' to c[4])
        val g = FORME.map { l -> l.map { pal[it] }.toMutableList() }
        val ic = ICONES.getValue(if (cache) "cache" else famille!!)
        ic.forEachIndexed { y, l -> l.forEachIndexed { x, ch -> if (ch != '.') g[3 + y][3 + x] = pal[ch] } }
        if ((echelon == "giga" || echelon == "tera") && !cache) for ((y, x) in ETINCELLES) g[y][x] = ETINCELLE
        return g
    }

    /** Le grade seul : grille 18 × 28 (null = transparent). */
    fun galons(echelon: String?): List<MutableList<String?>> {
        val g = List(HAUTEUR) { MutableList<String?>(LARGEUR) { null } }
        if (echelon !in ECHELONS) return g
        val c = COULEURS.getValue(echelon!!)
        val pal = FIXES + mapOf('a' to c[0], 'b' to c[2], 'c' to c[1])
        val (y0, lignes) = GALONS.getValue(echelon)
        lignes.forEachIndexed { y, l -> l.forEachIndexed { x, ch -> if (ch != '.') g[y0 + y][x] = pal[ch] } }
        return g
    }

    /** Le badge complet 18 × 28 : galons, écusson, 3 étoiles (0 à 3 allumées). Pas encore découvert : l'écusson gris seul. */
    fun ecusson(famille: String?, echelon: String?, etoiles: Int = 0): List<MutableList<String?>> {
        val cache = famille == null || famille == "cache" || famille !in ICONES || echelon !in ECHELONS
        val g = galons(if (cache) null else echelon)
        grille(famille, echelon).forEachIndexed { y, l -> l.forEachIndexed { x, c -> if (c != null) g[BY + y][BX + x] = c } }
        if (!cache) X_ETOILES.forEachIndexed { i, x0 ->
            ETOILE.forEachIndexed { y, l -> l.forEachIndexed { x, ch -> if (ch == 'x') g[y][x0 + x] = if (i < etoiles) ETOILE_ON else ETOILE_OFF } }
        }
        return g
    }

    /** Le grade atteint (0…5, ou -1) : n réussites, `ors` médailles d'or ou de diamant (Giga : 1), `diamants` (Téra : 3). */
    fun echelonDe(n: Int, ors: Int = 0, diamants: Int = 0): Int {
        var k = -1
        SEUILS.forEachIndexed { i, s -> if (n >= s && (i < 4 || ors >= 1) && (i < 5 || diamants >= DIAMANTS_TERA)) k = i }
        return k
    }

    /** Les étoiles (0…3) dans le grade k avec n réussites. */
    fun etoilesDe(n: Int, k: Int): Int = if (k < 0) 0 else ETOILES[k].count { n >= it }

    /** Les réussites de la prochaine étoile dans le grade k, ou null. */
    fun prochaineEtoile(n: Int, k: Int): Int? = if (k < 0) null else ETOILES[k].firstOrNull { n < it }

    fun texteEtoiles(n: Int) = "★".repeat(n) + "☆".repeat(3 - n)

    fun argb(h: String): Int = (0xFF000000L or h.substring(1).toLong(16)).toInt()

    /** Le reflet du grade (couleur des noms et des titres). */
    fun couleur(echelon: String?): Int = argb(COULEURS.getValue(echelon?.takeIf { it in ECHELONS } ?: "cache")[2])

    private val images = HashMap<String, Bitmap>()

    /** Le badge en image, bords nets : l'écusson seul (etoiles null, 14 × 14) ou complet (18 × 28), agrandi `echelle` fois. */
    fun bitmap(famille: String?, echelon: String?, echelle: Int = 4, etoiles: Int? = null): Bitmap {
        val cle = "$famille-$echelon-$echelle-$etoiles"
        images[cle]?.let { return it }
        val g = if (etoiles == null) grille(famille, echelon) else ecusson(famille, echelon, etoiles)
        val h = g.size
        val w = g[0].size
        val px = IntArray(w * h)
        for (y in 0 until h) for (x in 0 until w) px[y * w + x] = g[y][x]?.let { argb(it) } ?: 0
        val b = Bitmap.createScaledBitmap(Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888), w * echelle, h * echelle, false)
        images[cle] = b
        return b
    }

    /** La balise du terminal (TerminalActivity.miseEnForme la remplace par l'image) ; avec étoiles : le badge complet. */
    fun balise(famille: String?, echelon: String?, etoiles: Int? = null) =
        "¤badge:${famille ?: "cache"}:${echelon ?: "cache"}${if (etoiles != null) "~$etoiles" else ""}¤"
}
