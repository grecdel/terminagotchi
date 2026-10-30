package fr.terminagotchi

/**
 * La vie DANS la créature (portage exact de pc/tg/vie.py) : les yeux clignent, le haut du corps respire, les
 * appendices fins (ailes, queues, tentacules, antennes) ondulent, et les pupilles regardent un peu à gauche et à
 * droite — sans aucune nouvelle image dessinée.
 *
 * Les yeux sont cherchés automatiquement (petites taches sombres ou lumineuses bien entourées, dans le haut, de
 * préférence par paires) ; l'épaisseur de la silhouette sépare le corps des parties fines. Si rien n'est sûr, ou si
 * le résultat risquerait d'être cassé, analyser() renvoie null et AnimAuto garde l'animation d'avant.
 *
 * Calcul en entiers, mêmes parcours et mêmes départages qu'en Python : mêmes images, pixel pour pixel
 * (tests/jvm/Vie.kt et pc/outils/test_vie.py, sur donnees/vie/vecteurs.json).
 */
object Vie {
    const val PAD = 2
    const val CYCLE = 64
    const val BLOC = 32
    private val SIN = intArrayOf(0, 38, 71, 92, 100, 92, 71, 38, 0, -38, -71, -92, -100, -92, -71, -38)
    private const val M32 = 0xFFFFFFFFL
    private const val INF = 1 shl 20

    class Oeil(val px: List<IntArray>, val paupiere: Int, val trait: Int) {
        val x0 = px.minOf { it[0] }
        val x1 = px.maxOf { it[0] }
        val y0 = px.minOf { it[1] }
        val y1 = px.maxOf { it[1] }
    }

    class Analyse(val w: Int, val h: Int, val o: IntArray, val n0: Int, val graine: Long) {
        var yeux: List<Oeil> = emptyList()
        /** indices des pixels fins, triés (rang, indice) ; rang et sens dans les tableaux parallèles */
        var finsIdx = IntArray(0)
        var finsRang = IntArray(0)
        var finsSens = IntArray(0)
        var finsSet = BooleanArray(0)
        var amp = 1
        var souffle: IntArray? = null      // haut, fin, xc (null : pas de respiration)
        var ampSouffle = 0                 // étirement au sommet, en 16es de pixel
    }

    fun lum(c: Int): Int = ((c shr 16 and 255) * 299 + (c shr 8 and 255) * 587 + (c and 255) * 114) / 1000

    fun melange(v0: Long): Long {
        var v = v0 and M32
        v = ((v xor (v ushr 15)) * 0x2C1B3C6DL) and M32
        v = ((v xor (v ushr 12)) * 0x297A2D39L) and M32
        return v xor (v ushr 15)
    }

    // ------------------------------------------------------------ les yeux
    private class Bon(val comp: List<Int>, val cx2: Int, val cy2: Int, val force: Int, val n: Int, val lmin: Int)

    private fun yeux(w: Int, h: Int, o: IntArray, lum: IntArray): List<Oeil> {
        fun op(x: Int, y: Int) = x in 0 until w && y in 0 until h && o[y * w + x] != 0
        val R = if (maxOf(w, h) < 36) 2 else 3
        val smax = 4 + (w * h) / 40
        val cote = 2 + maxOf(w, h) / 8
        val anneau = ArrayList<IntArray>()
        for (dy in -R..R) for (dx in -R..R) if (maxOf(Math.abs(dx), Math.abs(dy)) == R) anneau.add(intArrayOf(dx, dy))
        val moy = IntArray(w * h) { -1 }
        for (y in 0 until h) for (x in 0 until w) {
            if (o[y * w + x] == 0) continue
            var s = 0; var n = 0
            for (d in anneau) if (op(x + d[0], y + d[1])) { s += lum[o[(y + d[1]) * w + x + d[0]]]; n++ }
            if (4 * n >= 3 * anneau.size) moy[y * w + x] = s / n
        }
        for (sorte in 0..1) {                 // 0 sombre, 1 clair
            val cand = BooleanArray(w * h)
            for (k in 0 until w * h) {
                val m = moy[k]
                if (m < 0) continue
                val L = lum[o[k]]
                cand[k] = if (sorte == 0) m - L >= 35 && L * 100 <= m * 62 else L - m >= 60 && L >= 150
            }
            val vu = BooleanArray(w * h)
            val comps = ArrayList<List<Int>>()
            for (k in 0 until w * h) {
                if (!cand[k] || vu[k]) continue
                val pile = ArrayList<Int>(); val comp = ArrayList<Int>()
                pile.add(k); vu[k] = true
                while (pile.isNotEmpty()) {
                    val q = pile.removeAt(pile.size - 1)
                    comp.add(q)
                    val qx = q % w; val qy = q / w
                    for (dy in -1..1) for (dx in -1..1) {
                        val X = qx + dx; val Y = qy + dy
                        if (X in 0 until w && Y in 0 until h && cand[Y * w + X] && !vu[Y * w + X]) {
                            vu[Y * w + X] = true; pile.add(Y * w + X)
                        }
                    }
                }
                comps.add(comp.sorted())
            }
            val bons = ArrayList<Bon>()
            for (comp in comps) {
                val xs = comp.map { it % w }; val ys = comp.map { it / w }
                val bw = xs.max() - xs.min() + 1; val bh = ys.max() - ys.min() + 1
                val cy2 = ys.min() + ys.max()
                if (comp.size > smax || bw > cote || bh > cote || cy2 > (h * 4) / 3) continue
                val force = comp.sumOf { Math.abs(moy[it] - lum[o[it]]) }
                bons.add(Bon(comp, xs.min() + xs.max(), cy2, force, comp.size, comp.minOf { lum[o[it]] }))
            }
            if (bons.isEmpty() || comps.size > 6) continue
            var meilleur: List<Bon>? = null
            var score = -1
            for (i in bons.indices) for (j in i + 1 until bons.size) {
                val a = bons[i]; val b = bons[j]
                val dy2 = Math.abs(a.cy2 - b.cy2); val dx2 = Math.abs(a.cx2 - b.cx2)
                if (dy2 > 2 + h / 8 || dx2 < 4 || dx2 > w || maxOf(a.n, b.n) > 2 * minOf(a.n, b.n) + 1 ||
                    Math.abs(a.lmin - b.lmin) > 40) continue
                val s = a.force + b.force - 10 * dy2
                if (s > score) { meilleur = listOf(a, b); score = s }
            }
            if (meilleur == null) {
                if (bons.size == 1 && comps.size <= 2 && bons[0].cy2 <= h) meilleur = listOf(bons[0]) else continue
            }
            val res = ArrayList<Oeil>()
            for (b in meilleur) {
                val comp = java.util.TreeSet(b.comp)
                if (sorte == 0) {
                    val ajout = java.util.TreeSet<Int>()
                    for (q in comp.toList()) {
                        val qx = q % w; val qy = q / w
                        for (dy in -1..1) for (dx in -1..1) {
                            val X = qx + dx; val Y = qy + dy; val k = Y * w + X
                            if (X in 0 until w && Y in 0 until h && o[k] != 0 && k !in comp && moy[k] >= 0 &&
                                lum[o[k]] - moy[k] >= 60 && lum[o[k]] >= 150) ajout.add(k)
                        }
                    }
                    if (ajout.size <= comp.size / 2 + 1) comp.addAll(ajout)
                }
                val compte = java.util.TreeMap<Int, Int>()
                for (q in comp) {
                    val qx = q % w; val qy = q / w
                    for (dy in -1..1) for (dx in -1..1) {
                        val X = qx + dx; val Y = qy + dy; val k = Y * w + X
                        if (X in 0 until w && Y in 0 until h && o[k] != 0 && k !in comp) compte[o[k]] = (compte[o[k]] ?: 0) + 1
                    }
                }
                if (compte.isEmpty()) continue
                val peau = compte.keys.minWith(compareBy<Int>({ -compte.getValue(it) }, { it }))
                var trait = (compte.keys + comp.map { o[it] }).minWith(compareBy<Int>({ lum[it] }, { it }))
                if (lum[peau] - lum[trait] < 25) trait = peau
                val px = comp.map { intArrayOf(it % w, it / w) }.sortedWith(compareBy<IntArray>({ it[1] }, { it[0] }))
                res.add(Oeil(px, peau, trait))
            }
            if (res.isNotEmpty()) return res
        }
        return emptyList()
    }

    // ------------------------------------------------------------ l'épaisseur, le corps et les parties fines
    private fun epaisseur(w: Int, h: Int, o: IntArray): IntArray {
        val d = IntArray(w * h) { if (o[it] == 0) 0 else INF }
        fun v(x: Int, y: Int) = if (x in 0 until w && y in 0 until h) d[y * w + x] else 0
        for (y in 0 until h) for (x in 0 until w) {
            val k = y * w + x
            if (d[k] != 0) d[k] = minOf(d[k], v(x - 1, y) + 1, v(x - 1, y - 1) + 1, minOf(v(x, y - 1) + 1, v(x + 1, y - 1) + 1))
        }
        for (y in h - 1 downTo 0) for (x in w - 1 downTo 0) {
            val k = y * w + x
            if (d[k] != 0) d[k] = minOf(d[k], v(x + 1, y) + 1, v(x + 1, y + 1) + 1, minOf(v(x, y + 1) + 1, v(x - 1, y + 1) + 1))
        }
        return d
    }

    private fun fins(a: Analyse, ep: IntArray): Boolean {
        val w = a.w; val h = a.h; val o = a.o
        var k = if (maxOf(w, h) < 30) 2 else 3
        var coeur = (0 until w * h).filter { ep[it] >= k }
        if (coeur.size < 4) { k -= 1; coeur = (0 until w * h).filter { ep[it] >= k } }
        if (coeur.size < 4) return false
        val g = IntArray(w * h) { INF }
        for (q in coeur) g[q] = 0
        var front: List<Int> = coeur
        var n = 0
        while (front.isNotEmpty()) {
            n++
            val suite = ArrayList<Int>()
            for (q in front) {
                val qx = q % w; val qy = q / w
                for (dy in -1..1) for (dx in -1..1) {
                    val X = qx + dx; val Y = qy + dy
                    if (X in 0 until w && Y in 0 until h) {
                        val r = Y * w + X
                        if (o[r] != 0 && g[r] == INF) { g[r] = n; suite.add(r) }
                    }
                }
            }
            front = suite
        }
        val cx2 = 2 * coeur.sumOf { it % w } / coeur.size
        val cy2 = 2 * coeur.sumOf { it / w } / coeur.size
        val haut = coeur.minOf { it / w }
        val bas = coeur.maxOf { it / w }
        val idx = ArrayList<Int>(); val rang = ArrayList<Int>(); val sens = ArrayList<Int>()
        for (q in 0 until w * h) {
            if (o[q] != 0 && g[q] > k && g[q] < INF && q / w < (h * 3) / 4) {
                val dx2 = Math.abs(2 * (q % w) - cx2); val dy2 = Math.abs(2 * (q / w) - cy2)
                idx.add(q); rang.add(g[q] - k); sens.add(if (dx2 >= dy2) 1 else 0)
            }
        }
        a.finsSet = BooleanArray(w * h)
        if (idx.size >= 4) {
            val ordre = idx.indices.sortedWith(compareBy<Int>({ rang[it] }, { idx[it] }))
            a.finsIdx = IntArray(ordre.size) { idx[ordre[it]] }
            a.finsRang = IntArray(ordre.size) { rang[ordre[it]] }
            a.finsSens = IntArray(ordre.size) { sens[ordre[it]] }
            for (q in a.finsIdx) a.finsSet[q] = true
        }
        a.amp = if (maxOf(w, h) < 36) 1 else 2
        val finSouffle = haut + (bas - haut) * 3 / 5
        a.souffle = if (finSouffle - haut >= 3) intArrayOf(haut, finSouffle, cx2 / 2) else null
        a.ampSouffle = souffleMax(h)
        return true
    }

    /** Ce qui peut bouger dans l'image (octets 0 = vide, palette en 0xRRGGBB ou ARGB), ou null si rien de sûr. */
    fun analyser(w: Int, h: Int, octets: IntArray, palette: IntArray): Analyse? {
        try {
            if (w < 6 || h < 6 || octets.size < w * h) return null
            val o = octets.copyOf(w * h)
            val n0 = o.count { it != 0 }
            if (n0 < 12) return null
            val lum = IntArray(palette.size + 1) { if (it == 0) 0 else lum(palette[it - 1] and 0xFFFFFF) }
            if (o.max() >= lum.size) return null
            var g = ((w * 31 + h).toLong()) and 0x7FFFFFFFL
            for (v in o) g = (g * 131 + v) and 0x7FFFFFFFL
            val a = Analyse(w, h, o, n0, g)
            a.yeux = yeux(w, h, o, lum)
            if (!fins(a, epaisseur(w, h, o))) { a.souffle = null; a.finsSet = BooleanArray(w * h) }
            if (a.yeux.isEmpty() && a.finsIdx.isEmpty() && a.souffle == null) return null
            val bande = a.souffle?.let { it[1] - it[0] + 1 } ?: 0
            val hautMax = n0 + n0 / 8 + 2 * bande + 4
            for (t in 0 until CYCLE) {
                val n = image(a, t).count { it.toInt() != 0 }
                if (n * 100 < n0 * 88 || n > hautMax) return null
            }
            return a
        } catch (e: RuntimeException) {
            return null
        }
    }

    fun analyser(w: Int, h: Int, octets: ByteArray, palette: IntArray): Analyse? =
        analyser(w, h, IntArray(w * h) { if (it < octets.size) octets[it].toInt() and 0xFF else 0 }, palette)

    private val gardees = LinkedHashMap<String, Analyse?>()

    /** analyser(), gardée en mémoire (l'équipe, le guide, le combat). */
    fun analyseGardee(w: Int, h: Int, octets: IntArray, palette: IntArray): Analyse? {
        val cle = "$w/$h/${octets.contentHashCode()}/${palette.contentHashCode()}/${octets.size}"
        synchronized(gardees) { if (gardees.containsKey(cle)) return gardees[cle] }
        val a = analyser(w, h, octets, palette)
        synchronized(gardees) {
            if (gardees.size > 48) gardees.clear()
            gardees[cle] = a
        }
        return a
    }

    // ------------------------------------------------------------ le temps qui passe
    /** L'étirement de la respiration au sommet, en 16es de pixel : presque rien pour un bébé, 1,5 pixel pour un grand. */
    fun souffleMax(h: Int) = if (h < 25) 9 else if (h < 40) 16 else 24

    /** (paupière 0|1|2, regard -1|0|1, souffle 0 à 100 en cosinus doux sur 16 images, phase de l'ondulation) à l'image t. */
    fun programme(a: Analyse, t: Int): IntArray {
        val b = t / BLOC
        val i = t % BLOC
        val hsh = melange(a.graine xor ((b.toLong() * 0x9E3779B1L) and M32))
        var paup = 0
        var regard = 0
        if ((hsh ushr 8) % 5 != 0L) {
            val o = (3 + hsh % 18).toInt()
            val debuts = if ((hsh ushr 5) % 4 == 0L) intArrayOf(o, o + 4) else intArrayOf(o)
            for (debut in debuts) {
                if (i == debut || i == debut + 2) paup = maxOf(paup, 1)
                else if (i == debut + 1) paup = 2
            }
            if ((hsh ushr 11) % 3 != 0L) {
                val g0 = ((o + 7 + (hsh ushr 14) % 5) % BLOC).toInt()
                if (i >= g0 && i < g0 + 6 && !(i >= o - 1 && i <= o + 7)) regard = if ((hsh ushr 17) % 2 == 1L) 1 else -1
            }
        } else if ((hsh ushr 11) % 2 == 1L) {
            val g0 = (6 + (hsh ushr 14) % 12).toInt()
            if (i >= g0 && i < g0 + 7) regard = if ((hsh ushr 17) % 2 == 1L) 1 else -1
        }
        val souffle = (100 - SIN[(t + 4) % 16]) / 2
        return intArrayOf(paup, regard, souffle, t % 16)
    }

    /** Largeur et hauteur des images de vie (l'image d'origine agrandie de PAD à gauche, à droite et en haut). */
    fun largeur(a: Analyse) = a.w + 2 * PAD
    fun hauteur(a: Analyse) = a.h + PAD

    /** L'image de vie numéro t (octets indexés, largeur(a) × hauteur(a), pieds sur la dernière ligne). */
    fun image(a: Analyse, t: Int): ByteArray {
        val w = a.w; val h = a.h
        val W2 = w + 2 * PAD; val H2 = h + PAD
        val p = programme(a, t)
        val paup = p[0]; val regard = p[1]; val souffle = p[2]; val ph = p[3]
        val src = a.o.copyOf()
        for (oe in a.yeux) {
            var dec = 0
            if (regard != 0 && oe.px.all { val x = it[0] + regard; x in 0 until w && a.o[it[1] * w + x] != 0 }) {
                dec = regard
                val vals = oe.px.map { a.o[it[1] * w + it[0]] }
                for (q in oe.px) src[q[1] * w + q[0]] = oe.paupiere
                for ((n, q) in oe.px.withIndex()) src[q[1] * w + q[0] + dec] = vals[n]
            }
            if (paup != 0) {
                val hh = oe.y1 - oe.y0 + 1
                for (q in oe.px) if (paup == 2 || q[1] - oe.y0 < (hh + 1) / 2) src[q[1] * w + q[0] + dec] = oe.paupiere
                if (paup == 2 && hh >= 2) for (q in oe.px) if (q[1] == oe.y1) src[q[1] * w + q[0] + dec] = oe.trait
            }
        }
        val out = IntArray(W2 * H2)
        for (y in 0 until h) for (x in 0 until w) {
            val q = y * w + x
            if (src[q] != 0 && !a.finsSet[q]) out[(y + PAD) * W2 + x + PAD] = src[q]
        }
        for (n in a.finsIdx.indices) {
            val q = a.finsIdx[n]; val rang = a.finsRang[n]
            val r = minOf(rang, 4)
            val dep = Math.floorDiv(a.amp * r * SIN[Math.floorMod(ph - rang, 16)], 400)
            var x = q % w + PAD; var y = q / w + PAD
            if (a.finsSens[n] == 1) y += dep else x += dep
            if (x in 0 until W2 && y in 0 until H2) out[y * W2 + x] = src[q]
        }
        // la respiration : un léger étirement vers le haut, pieds fixes ; chaque ligne prend la ligne d'origine la plus
        // proche (le décalage grandit doucement des pieds au sommet : aucune ligne de coupure)
        var res = out
        if (a.souffle != null && souffle != 0) {
            val amp = a.ampSouffle * souffle / 100
            if (amp != 0) {
                val bas = H2 - 1
                val H16 = h * 16
                val nv = IntArray(W2 * H2)
                for (y in 0 until H2) {
                    val d = bas - y
                    val sy = bas - (2 * d * H16 + H16 + amp) / (2 * (H16 + amp))
                    if (sy >= 0) System.arraycopy(out, sy * W2, nv, y * W2, W2)
                }
                res = nv
            }
        }
        return ByteArray(res.size) { res[it].toByte() }
    }
}
