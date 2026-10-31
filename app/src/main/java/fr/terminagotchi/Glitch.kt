package fr.terminagotchi

import org.json.JSONObject

/**
 * L'effet « glitch » d'une créature : portage exact de pc/tg/glitch.py (la spécification y est), le même que le site
 * (site/src/glitch.js) ; vecteurs communs : donnees/glitch/vecteurs.json (tests/jvm/Glitch.kt).
 * Effet de l'INDIVIDU (comme le shiny, indépendant de la variante) : au repos le style A (léger : liseré rose et
 * cyan, 2 tranches décalées), toutes les quelques secondes un éclair bref du style C (fort). Il se pose sur chaque
 * image (vie, animations, poses de la bulle et de l'île), après la teinte shiny ; déterministe (graine = l'individu).
 * Pixels : ARGB (Int), transparents si alpha = 0.
 */
object Glitch {
    private const val ROSE = 0xFF2878
    private const val CYAN = 0x28E6FF
    private val MORTS = intArrayOf(ROSE, CYAN, 0xF0FF50, 0xFFFFFF)
    const val ECLAIR_MS = 260L
    /** le repère du nom (1 colonne dans un terminal), comme le ✨ du shiny */
    const val REPERE = "▚"

    fun fnv(texte: String): Long {
        var h = -0x340d631b7bdddcdbL                          // 0xCBF29CE484222325
        for (b in texte.toByteArray(Charsets.UTF_8)) {
            h = h xor (b.toLong() and 0xFF)
            h *= 0x100000001B3L
        }
        return h
    }

    private class Hasard(texte: String) {
        private var etat = fnv(texte)
        fun suivant(): Long {
            etat += -0x61c8864680b583ebL                       // 0x9E3779B97F4A7C15
            var z = etat
            z = (z xor (z ushr 30)) * -0x40a7b892e31b1a47L
            z = (z xor (z ushr 27)) * -0x6b2fb644ecceee15L
            return z xor (z ushr 31)
        }
        fun n(k: Int): Int = java.lang.Long.remainderUnsigned(suivant(), k.toLong()).toInt()
    }

    private fun plein(p: Int) = (p ushr 24) != 0

    /** Les pixels transparents reliés au bord de l'image (4 voisins) : le dehors de la silhouette. */
    private fun exterieur(w: Int, h: Int, pl: BooleanArray): BooleanArray {
        val dehors = BooleanArray(w * h)
        val pile = IntArray(w * h)
        var n = 0
        for (i in 0 until w * h) {
            val x = i % w
            if (!pl[i] && (i < w || i >= w * (h - 1) || x == 0 || x == w - 1)) { dehors[i] = true; pile[n++] = i }
        }
        while (n > 0) {
            val i = pile[--n]
            val x = i % w
            for (j in intArrayOf(if (i >= w) i - w else -1, if (i + w < w * h) i + w else -1, if (x > 0) i - 1 else -1,
                if (x < w - 1) i + 1 else -1)) {
                if (j >= 0 && !pl[j] && !dehors[j]) { dehors[j] = true; pile[n++] = j }
            }
        }
        return dehors
    }

    /** Les pixels (ARGB, w × h) avec l'effet : un NOUVEAU tableau. s : la taille d'un pixel de créature. */
    fun appliquer(w: Int, h: Int, px: IntArray, graine: String, style: String = "A", phase: Int = 0, s0: Int = 1): IntArray {
        val s = maxOf(1, s0)
        val w0 = maxOf(1, w / s); val h0 = maxOf(1, h / s)
        val r = Hasard("$graine:$style:$phase")
        val fort = style == "C"
        val pl = BooleanArray(w * h) { plein(px[it]) }
        val out = px.copyOf()
        if (fort) for (i in out.indices) {
            if (!pl[i]) continue
            val p = out[i]
            var rr = (p ushr 16) and 255; var gg = (p ushr 8) and 255; var bb = p and 255
            val m = (rr + gg + bb) / 3
            rr = (55 * rr + 45 * m) / 100; gg = (55 * gg + 45 * m) / 100; bb = (55 * bb + 45 * m) / 100
            rr = minOf(255, rr * 105 / 100 + 18); bb = minOf(255, bb * 110 / 100 + 28)
            out[i] = (p and -0x1000000) or (rr shl 16) or (gg shl 8) or bb
        }
        val d = s * (if (fort) maxOf(2, w0 / 12) else maxOf(1, w0 / 24))
        val dehors = if (fort) null else exterieur(w, h, pl)
        for (y in 0 until h) {
            val b = y * w
            for (x in 0 until w) {
                if (pl[b + x] || (dehors != null && !dehors[b + x])) continue
                if (x + d < w && pl[b + x + d]) out[b + x] = -0x1000000 or CYAN
                else if (x - d >= 0 && pl[b + x - d]) out[b + x] = -0x1000000 or ROSE
            }
        }
        val ligne = IntArray(w)
        repeat(if (fort) 7 else 2) {
            val y0 = r.n(h0)
            val hh = 1 + r.n(maxOf(1, h0 / (if (fort) 7 else 10)))
            val sens = if (r.n(2) != 0) 1 else -1
            val dx = sens * (1 + r.n(if (fort) maxOf(3, w0 / 5) else maxOf(2, w0 / 12))) * s
            for (y in y0 * s until minOf(h, (y0 + hh) * s)) {
                System.arraycopy(out, y * w, ligne, 0, w)
                for (x in 0 until w) out[y * w + x] = ligne[Math.floorMod(x - dx, w)]
            }
        }
        if (fort) {
            for (y in 0 until h) {
                if ((y / s) % 3 != 0) continue
                for (i in y * w until (y + 1) * w) {
                    val p = out[i]
                    if (!plein(p)) continue
                    out[i] = (p and -0x1000000) or ((((p ushr 16) and 255) * 78 / 100) shl 16) or
                        ((((p ushr 8) and 255) * 78 / 100) shl 8) or ((p and 255) * 78 / 100)
                }
            }
            repeat(maxOf(1, w0 * h0 / 250)) {
                val yu = r.n(h0); val xu = r.n(w0); val c = MORTS[r.n(4)]
                if (yu * s < h && xu * s < w && plein(out[yu * s * w + xu * s])) {
                    for (y in yu * s until minOf(h, yu * s + s)) for (x in xu * s until minOf(w, xu * s + s)) out[y * w + x] = -0x1000000 or c
                }
            }
            val x0 = w0 / 4 + r.n(maxOf(1, w0 / 2))
            val ww = 2 + r.n(2)
            for (x in x0 * s until minOf(w, (x0 + ww) * s)) {
                val ys = (0 until h).filter { plein(out[it * w + x]) }
                val vals = ys.map { out[it * w + x] }.sortedBy { ((it ushr 16) and 255) + ((it ushr 8) and 255) + (it and 255) }
                for ((k, y) in ys.withIndex()) out[y * w + x] = vals[k]
            }
        }
        return out
    }

    /** (style, phase) à l'instant t (ms, horloge murale) : ("A", 0) au repos, ("C", phase) pendant un éclair. */
    fun etat(graine: String, t: Long = System.currentTimeMillis()): Pair<String, Int> {
        val hh = fnv("$graine:eclair")
        val periode = 3000L + java.lang.Long.remainderUnsigned(hh, 2500L)
        val t2 = t + java.lang.Long.remainderUnsigned(hh ushr 20, periode)
        val u = t2 % periode
        if (u < ECLAIR_MS) return "C" to ((t2 / periode % 4).toInt() * 2 + if (u >= ECLAIR_MS / 2) 1 else 0)
        return "A" to 0
    }

    /** L'effet à appliquer : la graine de l'individu, son style et sa phase. */
    data class Spec(val graine: String, val style: String, val phase: Int)

    /** La graine de l'effet d'un individu : son identifiant. */
    fun graine(ind: JSONObject): String = ind.optString("id").ifEmpty { "${ind.optString("espece")}:${ind.optLong("date")}" }

    /** La graine si l'individu est glitch, sinon null. */
    fun de(ind: JSONObject?): String? = if (ind != null && ind.optBoolean("glitch")) graine(ind) else null

    /** L'effet à cet instant (style A, ou C pendant un éclair) pour une graine, ou null. */
    fun maintenant(graine: String?): Spec? = graine?.let { val (s, p) = etat(it); Spec(it, s, p) }

    /** L'effet au repos (style A) pour une graine, ou null. */
    fun repos(graine: String?): Spec? = graine?.let { Spec(it, "A", 0) }

    /** Les pixels avec l'effet (inchangés sans effet). */
    fun sur(w: Int, h: Int, px: IntArray, g: Spec?, s: Int = 1): IntArray =
        if (g == null) px else appliquer(w, h, px, g.graine, g.style, g.phase, s)

    /** Une image Android avec l'effet (2 pixels × s de marge à gauche et à droite pour le liseré). */
    fun bitmap(b: android.graphics.Bitmap, g: Spec?, s: Int = 1): android.graphics.Bitmap {
        if (g == null) return b
        val w = b.width; val h = b.height; val m = 2 * s
        val px = IntArray(w * h)
        b.getPixels(px, 0, w, 0, 0, w, h)
        val W = w + 2 * m
        val grand = IntArray(W * h)
        for (y in 0 until h) System.arraycopy(px, y * w, grand, y * W + m, w)
        return android.graphics.Bitmap.createBitmap(appliquer(W, h, grand, g.graine, g.style, g.phase, s), W, h,
            android.graphics.Bitmap.Config.ARGB_8888)
    }
}
