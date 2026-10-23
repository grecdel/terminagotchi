package fr.terminagotchi

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF

/** Pixel art de la créature (mêmes dessins que la version PC). */
object Sprites {
    private val OEUF = listOf(
        "....wwww....",
        "...wwwwww...",
        "..wwwswwww..",
        "..wwwwwwsw..",
        ".wwswwwwwww.",
        ".wwwwwwwsww.",
        ".wwwwswwwww.",
        ".wwwwwwwwww.",
        "..wwwwwwww..",
        "...wwwwww...",
    )
    private val BEBE = listOf(
        "............",
        "....bbbb....",
        "..bbbbbbbb..",
        ".bbbbbbbbbb.",
        ".bbebbbbebb.",
        ".bbebbbbebb.",
        "bbkbbmmbbkbb",
        "bbbbbbbbbbbb",
        ".bbbbbbbbbb.",
        "..bb....bb..",
    )
    private val ADO = listOf(
        "..bbbbbbbb..",
        ".bbbbbbbbbb.",
        ".bbebbbbebb.",
        ".bbebbbbebb.",
        "bbkbbbbbbkbb",
        "bbbbbmmbbbbb",
        ".bbbbbbbbbb.",
        ".bbbbbbbbbb.",
        "..bbb..bbb..",
        "..bb....bb..",
    )
    private val ADO_TETE = mapOf(
        "Intelligence" to listOf("......l.....", "......a....."),
        "Force" to listOf(".h........h.", ".hh......hh."),
        "Agilité" to listOf("..h......h..", "..hh....hh.."),
        "Endurance" to listOf("............", "...cccccc..."),
    )
    private val ADO_CORPS = mapOf(
        "Endurance" to mapOf(6 to "??c?c??c?c??", 7 to "???c?cc?c???"),
        "Intelligence" to mapOf(2 to "??l?????l???"),
    )
    private val ADULTE = listOf(
        "..bbbbbbbbbbbb..",
        "..bbbbbbbbbbbb..",
        ".bbbeebbbbeebbb.",
        ".bbbeebbbbeebbb.",
        ".bbkbbbbbbbbkbb.",
        "..bbbbbmmbbbbb..",
        "..bbbbbbbbbbbb..",
        "..bbbbbbbbbbbb..",
        "..bbbbbbbbbbbb..",
        "...bbbb..bbbb...",
        "...bbb....bbb...",
    )
    private val ADULTE_TETE = mapOf(
        "Intelligence" to listOf(".......ll.......", ".......aa......."),
        "Force" to listOf(".hh..........hh.", ".hhh........hhh."),
        "Agilité" to listOf("...hh......hh...", "...hhh....hhh..."),
        "Endurance" to listOf("................", "....cccccccc...."),
    )
    private val ADULTE_CORPS = mapOf(
        "Intelligence" to mapOf(2 to "???l??llll??l???"),
        "Force" to mapOf(4 to "h??????????????h", 5 to "hh????????????hh"),
        "Agilité" to mapOf(4 to "w??????????????w", 5 to "ww????????????ww", 6 to "ww????????????ww",
            7 to "w??????????????w"),
        "Endurance" to mapOf(6 to "???c?c?c?c?c????", 7 to "????c?c?c?c?c???", 8 to "???c?c?c?c?c????"),
    )

    private fun overlay(base: List<String>, ovl: Map<Int, String>?): List<String> {
        if (ovl == null) return base
        val rows = base.toMutableList()
        for ((i, mask) in ovl) {
            rows[i] = mask.zip(rows[i]).map { (m, b) -> if (m == '?') b else m }.joinToString("")
        }
        return rows
    }

    fun lignes(jeu: Jeu): List<String> = when (jeu.stade) {
        0 -> OEUF
        1 -> BEBE
        else -> {
            val f = jeu.forme ?: jeu.dominant()
            if (jeu.stade == 2) ADO_TETE.getValue(f) + overlay(ADO, ADO_CORPS[f])
            else ADULTE_TETE.getValue(f) + overlay(ADULTE, ADULTE_CORPS[f])
        }
    }

    fun couleurCorps(jeu: Jeu): Int {
        val f = jeu.forme
        if (f != null && jeu.stade >= 2) return Regles.COULEUR.getValue(f)
        if (jeu.stats.values.all { it == 0 }) return 141
        return Regles.COULEUR.getValue(jeu.dominant())
    }

    private fun palette(jeu: Jeu, cligne: Boolean): Map<Char, Int> {
        val corps = couleurCorps(jeu)
        return mapOf('b' to corps, 'e' to (if (cligne) corps else 16), 'k' to 211,
            'm' to (if (jeu.faim >= 30) 52 else 16), 'h' to 180, 'w' to 230, 's' to 180, 'c' to 136,
            'a' to 250, 'l' to 51)
    }

    /** Couleur xterm-256 → couleur Android. */
    fun x256(n: Int): Int {
        val base = intArrayOf(0x000000, 0x800000, 0x008000, 0x808000, 0x000080, 0x800080, 0x008080, 0xc0c0c0,
            0x808080, 0xff0000, 0x00ff00, 0xffff00, 0x0000ff, 0xff00ff, 0x00ffff, 0xffffff)
        if (n < 16) return Color.rgb(base[n] shr 16, (base[n] shr 8) and 0xff, base[n] and 0xff)
        if (n < 232) {
            val k = n - 16
            val lv = intArrayOf(0, 95, 135, 175, 215, 255)
            return Color.rgb(lv[k / 36], lv[(k / 6) % 6], lv[k % 6])
        }
        val g = 8 + (n - 232) * 10
        return Color.rgb(g, g, g)
    }

    /** Dessine la créature sur un cadre fixe de 18×16 pixels (pour qu'elle ne « saute » pas en grandissant). */
    fun bitmap(jeu: Jeu, echelle: Int, cligne: Boolean = false): Bitmap {
        val rows = lignes(jeu)
        val pal = palette(jeu, cligne)
        val largeur = 18
        val hauteur = 16
        val bmp = Bitmap.createBitmap(largeur * echelle, hauteur * echelle, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        val p = Paint()
        val w = rows.maxOf { it.length }
        val ox = (largeur - w) / 2
        val oy = (hauteur - rows.size - 1).coerceAtLeast(0)
        p.color = Color.argb(70, 0, 0, 0)
        c.drawOval(RectF(((ox + 1) * echelle).toFloat(), ((hauteur - 1.4f) * echelle),
            ((ox + w - 1) * echelle).toFloat(), ((hauteur - 0.4f) * echelle)), p)
        rows.forEachIndexed { j, row ->
            row.forEachIndexed { i, ch ->
                val code = pal[ch]
                if (code != null) {
                    p.color = x256(code)
                    c.drawRect(((ox + i) * echelle).toFloat(), ((oy + j) * echelle).toFloat(),
                        ((ox + i + 1) * echelle).toFloat(), ((oy + j + 1) * echelle).toFloat(), p)
                }
            }
        }
        return bmp
    }
}
