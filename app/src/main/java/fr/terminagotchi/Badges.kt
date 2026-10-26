package fr.terminagotchi

import android.graphics.Bitmap

/**
 * Les badges de la salle d'entraînement (portage de pc/tg/badges.py, mêmes dessins et mêmes couleurs ;
 * le site a les siens dans site/src/entrainement.js).
 *
 * Les badges appartiennent à la PARTIE (ce que l'enfant sait faire), pas à la créature (elle gagne de l'XP).
 * 8 familles, 5 échelons : Bois → Bronze → Argent → Or → Diamant, à 1 / 5 / 15 / 30 / 50 exercices réussis
 * dans la famille ; le Diamant demande en plus au moins une médaille d'or (ou de diamant) en temps.
 * Dessin 14 × 14 : . transparent, o contour, f fond, h reflet, i dessin, k/K détail.
 * Dans le terminal de l'appli : la balise ¤badge:<famille>:<échelon>¤ (famille « cache » = « ??? »).
 */
object Badges {
    val FAMILLES = listOf("explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier")
    val ECHELONS = listOf("bois", "bronze", "argent", "or", "diamant")
    val SEUILS = listOf(1, 5, 15, 30, 50)

    /** contour, fond, reflet, dessin, détail */
    val COULEURS: Map<String, List<String>> = mapOf(
        "bois" to listOf("#3a2a1a", "#76583a", "#987654", "#efe0c4", "#4a3522"),
        "bronze" to listOf("#6b3510", "#d0782a", "#f6ad62", "#fff3e0", "#7a3c0c"),
        "argent" to listOf("#4a525e", "#aab5c2", "#e6edf4", "#323a47", "#6b7685"),
        "or" to listOf("#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"),
        "diamant" to listOf("#0b4a66", "#3fcfff", "#d2f8ff", "#06324a", "#1a7fae"),
        "cache" to listOf("#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"),
    )
    const val ETINCELLE = "#ffffff"

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

    /** La grille 14 × 14 (« #rrggbb » ou null). famille ou échelon null (ou « cache ») : la famille pas encore découverte. */
    fun grille(famille: String?, echelon: String?): List<List<String?>> {
        val cache = famille == null || echelon == null || famille == "cache" || echelon !in ECHELONS
        val c = COULEURS.getValue(if (cache) "cache" else echelon!!)
        val pal = mapOf('o' to c[0], 'f' to c[1], 'h' to c[2], 'i' to c[3], 'k' to c[4], 'K' to c[4])
        val g = FORME.map { l -> l.map { pal[it] }.toMutableList() }
        val ic = ICONES.getValue(if (cache) "cache" else famille!!)
        ic.forEachIndexed { y, l -> l.forEachIndexed { x, ch -> if (ch != '.') g[3 + y][3 + x] = pal[ch] } }
        if (echelon == "diamant" && !cache) for ((y, x) in ETINCELLES) g[y][x] = ETINCELLE
        return g
    }

    /** L'échelon atteint (0…4, ou -1) avec n réussites et `ors` médailles d'or ou de diamant. */
    fun echelonDe(n: Int, ors: Int = 0): Int {
        var k = -1
        SEUILS.forEachIndexed { i, s -> if (n >= s && (i < 4 || ors >= 1)) k = i }
        return k
    }

    fun argb(h: String): Int = (0xFF000000L or h.substring(1).toLong(16)).toInt()

    /** Le reflet de l'échelon (couleur des noms et des titres). */
    fun couleur(echelon: String?): Int = argb(COULEURS.getValue(echelon?.takeIf { it in ECHELONS } ?: "cache")[2])

    private val images = HashMap<String, Bitmap>()

    /** Le badge en image (14 × 14 pixels agrandis `echelle` fois, bords nets). */
    fun bitmap(famille: String?, echelon: String?, echelle: Int = 4): Bitmap {
        val cle = "$famille-$echelon-$echelle"
        images[cle]?.let { return it }
        val g = grille(famille, echelon)
        val px = IntArray(14 * 14)
        for (y in 0 until 14) for (x in 0 until 14) px[y * 14 + x] = g[y][x]?.let { argb(it) } ?: 0
        val b = Bitmap.createScaledBitmap(Bitmap.createBitmap(px, 14, 14, Bitmap.Config.ARGB_8888), 14 * echelle, 14 * echelle, false)
        images[cle] = b
        return b
    }

    /** La balise du terminal (TerminalActivity.miseEnForme la remplace par l'image). */
    fun balise(famille: String?, echelon: String?) = "¤badge:${famille ?: "cache"}:${echelon ?: "cache"}¤"
}
