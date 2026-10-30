package fr.terminagotchi

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF

/** Pixel art de la créature (mêmes dessins que la version PC). */
object Sprites {
    // l'œuf : celui de son type (Oeufs.kt, dessins de donnees/oeufs/), intact puis fissuré (couleurs ARGB)
    private fun oeuf(jeu: Jeu): List<String> =
        Oeufs.petit(Oeufs.typeDe(jeu), jeu.extra.optJSONObject("intro")?.optJSONArray("faits")?.length() ?: 0).ifEmpty { listOf("....") }

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

    // Le compagnon d'une partie récente EST une espèce du bestiaire (extra « espece_compagnon », tirée avec l'œuf :
    // Oeufs.kt). Ses stades suivent ceux du jeu (mêmes niveaux, mêmes noms) : Bébé → bebe, Ado → ado, Adulte → adulte.
    // Une partie d'avant (sans espèce) garde la petite créature dessinée ci-dessus. Même règle sur PC (sprites.py).
    val STADE_ESPECE = mapOf(1 to "bebe", 2 to "ado", 3 to "adulte")
    private const val CARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz!#$%&*+-=@^~"
    private val cacheEspece = HashMap<String, Pair<List<String>, Map<Char, Int>>?>()

    /** L'espèce du compagnon, ou null (une partie d'avant : la créature d'origine). */
    fun especeCompagnon(jeu: Jeu): Bestiaire.Espece? =
        jeu.extra.optString("espece_compagnon").takeIf { it.isNotEmpty() }?.let { Bestiaire.espece(it) }

    /** (lignes de caractères, palette caractère → ARGB) de l'espèce e au stade st du jeu (1 à 3). */
    private fun dessinEspece(e: Bestiaire.Espece, st: Int, shiny: Boolean): Pair<List<String>, Map<Char, Int>>? =
        synchronized(cacheEspece) {
            cacheEspece.getOrPut("${e.id}/$st/$shiny") {
                val img = Bestiaire.image(e, STADE_ESPECE[st] ?: "adulte") ?: return@getOrPut null
                val pal = img.palette.map { if (shiny) Bestiaire.decaler(it, 0.5) else it }
                val rows = (0 until img.h).map { y ->
                    String(CharArray(img.w) { x -> val o = img.octets[y * img.w + x].toInt() and 0xFF; if (o == 0) '.' else CARS[o - 1] })
                }
                rows to pal.take(CARS.length).withIndex().associate { (k, c) -> CARS[k] to (0xFF000000.toInt() or (c and 0xFFFFFF)) }
            }
        }

    private fun dessinCompagnon(jeu: Jeu, st: Int): Pair<List<String>, Map<Char, Int>>? =
        if (st < 1) null else especeCompagnon(jeu)?.let { dessinEspece(it, st, jeu.shiny) }

    /** Le dessin de la créature à son stade actuel, ou au stade st (pour rejouer une évolution). */
    fun lignes(jeu: Jeu, st: Int = jeu.stade): List<String> = dessinCompagnon(jeu, st)?.first ?: when (st) {
        0 -> oeuf(jeu)
        1 -> BEBE
        else -> {
            val f = jeu.forme ?: jeu.dominant()
            if (st == 2) ADO_TETE.getValue(f) + overlay(ADO, ADO_CORPS[f])
            else ADULTE_TETE.getValue(f) + overlay(ADULTE, ADULTE_CORPS[f])
        }
    }

    fun couleurCorps(jeu: Jeu): Int {
        val f = jeu.forme
        if (f != null && jeu.stade >= 2) return Regles.COULEUR.getValue(f)
        if (jeu.stats.values.all { it == 0 }) return 141
        return Regles.COULEUR.getValue(jeu.dominant())
    }

    private val SHINY = mapOf(39 to 220, 78 to 51, 203 to 129, 221 to 255, 141 to 219)

    private fun palette(jeu: Jeu, cligne: Boolean): Map<Char, Int> {
        val corps = couleurCorps(jeu).let { if (jeu.shiny) SHINY[it] ?: 219 else it }
        return mapOf('b' to corps, 'e' to (if (cligne) corps else 16), 'k' to 211,
            'm' to (if (jeu.faim >= 30) 52 else 16), 'h' to 180, 'w' to 230, 's' to 180, 'c' to 136,
            'a' to 250, 'l' to 51)
    }

    /** Les couleurs à dessiner (ARGB) : celles du dessin de l'œuf au stade 0, sinon la palette xterm convertie. */
    fun couleurs(jeu: Jeu, cligne: Boolean, st: Int = jeu.stade): Map<Char, Int> =
        if (st == 0) Oeufs.palette(Oeufs.typeDe(jeu))
        else dessinCompagnon(jeu, st)?.second ?: palette(jeu, cligne).mapValues { x256(it.value) }

    // ------------------------------------------------------------ animations automatiques (moteur AnimAuto)
    /** Lignes de caractères + palette xterm → image en indices + palette 0xRRGGBB (comme sprites._indexer sur PC). */
    fun indexer(rows: List<String>, pal: Map<Char, Int>, argb: Boolean = false): AnimAuto.Sprite {
        val w = rows.maxOf { it.length }
        val codes = mutableListOf<Int>()
        val octets = ByteArray(w * rows.size)
        rows.forEachIndexed { y, r ->
            for (x in 0 until w) {
                val c = pal[if (x < r.length) r[x] else '.'] ?: continue
                if (c !in codes) codes.add(c)
                octets[y * w + x] = (codes.indexOf(c) + 1).toByte()
            }
        }
        return AnimAuto.Sprite(w, rows.size, octets, IntArray(codes.size) { (if (argb) codes[it] else x256(codes[it])) and 0xFFFFFF })
    }

    /** Coupe les bords vides communs à toutes les images (hauteur gardée paire, comme sprites._recadrer). */
    fun recadrer(a: AnimAuto.Anim): AnimAuto.Anim {
        val W = a.largeur; val H = a.hauteur
        var x0 = W; var y0 = H; var x1 = -1; var y1 = -1
        for (f in a.images) for (y in 0 until H) for (x in 0 until W) if (f[y * W + x].toInt() != 0) {
            if (y < y0) y0 = y; if (y > y1) y1 = y; if (x < x0) x0 = x; if (x > x1) x1 = x
        }
        if (x1 < 0) return a
        y0 -= y0 % 2
        val nw = x1 - x0 + 1
        var nh = y1 - y0 + 1
        nh += nh % 2
        val out = a.images.map { f ->
            val b = ByteArray(nw * nh)
            for (y in 0 until nh) if (y0 + y < H) System.arraycopy(f, (y0 + y) * W + x0, b, y * nw, nw)
            b
        }
        return AnimAuto.Anim(nw, nh, out, a.palette, a.nTeinte, a.ips)
    }

    /** La créature principale joue une animation automatique (mange, evolution, victoire, ko, dort, affame, colere…). */
    fun animation(jeu: Jeu, nom: String): AnimAuto.Anim {
        val st = jeu.stade
        // couleurs ARGB du stade (l'œuf, l'espèce, ou la créature d'origine) ; l'image d'avant avec SES couleurs
        val img = indexer(lignes(jeu, st), couleurs(jeu, false, st), true)
        val de = if (nom == "evolution" && st > 0) indexer(lignes(jeu, st - 1), couleurs(jeu, false, st - 1), true) else null
        return recadrer(AnimAuto.images(img, nom, de))
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

    private fun cadre(rows: List<String>): Pair<Int, Int> = maxOf(18, rows.maxOf { it.length }) to maxOf(16, rows.size + 1)

    /** La taille réelle d'un pixel dans bitmap(jeu, echelle0) (plus petite pour une grande espèce) : pour l'aura. */
    fun echelle(jeu: Jeu, echelle0: Int, st: Int = jeu.stade): Int {
        val (l, h) = cadre(lignes(jeu, st))
        return maxOf(1, Math.round(echelle0 * minOf(18f / l, 16f / h)))
    }

    /** Dessine la créature sur un cadre fixe de 18×16 pixels (pour qu'elle ne « saute » pas en grandissant). Une espèce
     *  du bestiaire est plus grande (jusqu'à 44 pixels) : le cadre s'agrandit et ses pixels rétrécissent d'autant, pour
     *  que l'image garde à peu près la même taille (widget, notification). */
    fun bitmap(jeu: Jeu, echelle0: Int, cligne: Boolean = false, st: Int = jeu.stade): Bitmap {
        val rows = lignes(jeu, st)
        val pal = couleurs(jeu, cligne, st)
        val (largeur, hauteur) = cadre(rows)
        val echelle = echelle(jeu, echelle0, st)
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
                    p.color = code
                    c.drawRect(((ox + i) * echelle).toFloat(), ((oy + j) * echelle).toFloat(),
                        ((ox + i + 1) * echelle).toFloat(), ((oy + j + 1) * echelle).toFloat(), p)
                }
            }
        }
        return bmp
    }
}
