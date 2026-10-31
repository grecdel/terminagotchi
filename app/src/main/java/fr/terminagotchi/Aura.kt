package fr.terminagotchi

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import org.json.JSONObject

/**
 * Les auras de rareté (portage de pc/tg/aura.py) : une lueur qui suit la silhouette d'une bestiole et montre
 * sa rareté. Calculée depuis le MASQUE de l'image (pixels non vides, dehors seulement : les trous fermés restent
 * vides), plus large et plus forte pour les plus rares ; elle respire (une vague part de la silhouette), les plus
 * rares ont un reflet qui passe en diagonale, les shiny une lueur arc-en-ciel et des étincelles.
 *
 *   commune : presque invisible · peu commune : vert, 1 px · rare : bleu, 2 px · épique : violet, 2 px + reflet
 *   légendaire : or, 3 px + reflet · mythique : rose, 3 px + reflet · shiny : arc-en-ciel, 3 px + étincelles
 *
 * Le calcul se fait en petits pixels (tableaux d'entiers, testable hors téléphone : tests/jvm/Aura.kt) ; le
 * dessin agrandit l'aura avec lissage (lueur douce) sous la bestiole restée nette. Les masques et les calques
 * sont gardés en cache (une image = quelques centaines de pixels).
 *
 * Par-dessus, le DÉCOR (en entiers, la même liste qu'en Python, au demi-pixel pour l'écran fin du téléphone) :
 * particules qui montent du bord de la silhouette, reflet qui passe SUR la créature (légendaire, mythique, shiny),
 * étincelles en petites étoiles (shiny). L'ÉCLAT (0 à 3) suit le soin (faim et envies) : l'aura brille davantage
 * quand la créature est bien soignée, et pâlit quand elle est négligée — jamais de mort ni de punition.
 */
object Aura {
    class Palier(val couleur: Int?, val rayon: Int, val force: Int, val reflet: Boolean = false)

    /** Une aura calculée : toile largeur × hauteur (l'image agrandie de r de chaque côté), pixels ARGB (0 = vide). */
    class Calque(val largeur: Int, val hauteur: Int, val r: Int, val px: IntArray)

    const val PHASES = 16
    /** image fixe (listes) : la lueur au plus fort */
    const val PHASE_FIXE = 4
    val ORDRE = listOf("commune", "peu commune", "rare", "épique", "légendaire", "mythique", "shiny")
    val PALIERS: Map<String, Palier> = mapOf(
        "commune" to Palier(Bestiaire.COULEUR_RARETE.getValue("commune"), 1, 40),
        "peu commune" to Palier(Bestiaire.COULEUR_RARETE.getValue("peu commune"), 1, 150),
        "rare" to Palier(Bestiaire.COULEUR_RARETE.getValue("rare"), 2, 170),
        "épique" to Palier(Bestiaire.COULEUR_RARETE.getValue("épique"), 2, 195, true),
        "légendaire" to Palier(Bestiaire.COULEUR_RARETE.getValue("légendaire"), 3, 215, true),
        "mythique" to Palier(Bestiaire.COULEUR_RARETE.getValue("mythique"), 3, 230, true),
        "shiny" to Palier(null, 3, 220, true),
    )

    /** Le palier d'aura : shiny d'abord, sinon la rareté (commune si inconnue). */
    fun palierDe(rarete: String?, shiny: Boolean): String = if (shiny) "shiny" else if (rarete != null && rarete in PALIERS) rarete else "commune"

    fun palierInd(ind: JSONObject): String = palierDe(Bestiaire.rareteDe(ind), ind.optBoolean("shiny"))

    /** La créature principale n'a pas de rareté et ne naît jamais shiny : pas d'aura (null, pas de lueur grise).
     *  Seul un compagnon shiny d'une ancienne sauvegarde (avant cette règle) garde sa lueur arc-en-ciel. */
    fun palierCompagnon(jeu: Jeu): String? = if (jeu.shiny) "shiny" else null

    // ---------------------------------------------------------------- l'éclat selon le soin
    /** % de la force de la lueur selon l'éclat 0 (en veille) à 3 (rassasiée et bien soignée). */
    val ECLAT_FORCE = intArrayOf(45, 70, 100, 125)
    const val ECLAT_NORMAL = 2

    /** faim et moyenne des envies (0 à 100) → éclat 0 à 3 (le même calcul que aura.niveau_soin en Python). */
    fun niveauSoin(faim: Int, envies: Int): Int {
        val soin = (faim * 6 + envies * 4) / 10
        return when {
            faim < 15 -> 0
            soin >= 80 && faim >= 70 -> 3
            soin >= 40 && faim >= 30 -> 2
            else -> 1
        }
    }

    /** L'éclat d'après les 4 états de la satiété (le même calcul que aura.niveau_satiete en Python). */
    fun niveauSatiete(faim: Int, envies: Int, veille: Boolean = false): Int = when {
        // d'après les 4 états de la satiété (Satiete.kt) : veille 0, affamée 1, en forme 2, rassasiée et bien soignée 3
        veille || faim < Satiete.AFFAMEE -> 0
        faim < Satiete.FORME -> 1
        faim >= Satiete.RASSASIEE && envies >= 50 -> 3
        else -> 2
    }

    /** L'éclat de l'aura de la créature selon le soin : la faim (60 %), les envies jeu, curiosité, exploration et
     *  sommeil (40 %). */
    fun eclat(jeu: Jeu): Int = try {
        val faim = jeu.faim
        val autres = listOf("jeu", "curiosite", "explorer", "sommeil").map { Envies.valeur(jeu, it) }
        niveauSatiete(faim.toInt(), autres.average().toInt(), jeu.extra.optJSONObject("satiete")?.optBoolean("veille") == true)
    } catch (e: Exception) { ECLAT_NORMAL }

    /** Le réglage de la partie (bouton ✨ de l'écran principal) : affichée par défaut. */
    fun active(jeu: Jeu): Boolean = jeu.module("aura").optBoolean("on", true)

    /** Allume ou éteint l'aura de la créature de l'écran principal ; renvoie le nouvel état. */
    fun basculer(jeu: Jeu): Boolean {
        val on = !active(jeu)
        jeu.module("aura").put("on", on)
        return on
    }

    // ---------------------------------------------------------------- calcul
    private val distancesCache = LinkedHashMap<String, FloatArray>()

    /**
     * Distance (en pixels) de chaque pixel vide DEHORS à la silhouette, sur la toile agrandie de r de chaque côté
     * (-1 = rien : trop loin, ou trou fermé à l'intérieur).
     */
    fun distances(w: Int, h: Int, plein: BooleanArray, r: Int): FloatArray {
        val cle = "$w/$h/$r/" + plein.contentHashCode()
        synchronized(distancesCache) { distancesCache[cle]?.let { return it } }
        val W = w + 2 * r; val H = h + 2 * r
        val d = FloatArray(W * H) { -1f }
        fun pleinA(x: Int, y: Int) = x in 0 until w && y in 0 until h && plein[y * w + x]
        val voisins = ArrayList<Triple<Int, Int, Float>>()
        for (dy in -r..r) for (dx in -r..r) {
            val l = Math.hypot(dx.toDouble(), dy.toDouble()).toFloat()
            if ((dx != 0 || dy != 0) && l <= r + 0.5f) voisins.add(Triple(dx, dy, l))
        }
        for (y in 0 until h) for (x in 0 until w) {
            if (!plein[y * w + x]) continue
            var bord = false
            for (b in -1..1) for (a in -1..1) if ((a != 0 || b != 0) && !pleinA(x + a, y + b)) bord = true
            if (!bord) continue
            for ((dx, dy, l) in voisins) {
                if (pleinA(x + dx, y + dy)) continue
                val k = (y + r + dy) * W + x + r + dx
                if (d[k] < 0 || l < d[k]) d[k] = l
            }
        }
        // seulement dehors : remplissage depuis le bord de la toile
        val dehors = BooleanArray(W * H)
        val pile = ArrayDeque<Int>()
        for (k in 0 until W * H) if (k % W == 0 || k % W == W - 1 || k / W == 0 || k / W == H - 1) { dehors[k] = true; pile.add(k) }
        while (pile.isNotEmpty()) {
            val k = pile.removeLast()
            val x = k % W; val y = k / W
            for ((X, Y) in listOf(x + 1 to y, x - 1 to y, x to y + 1, x to y - 1)) {
                if (X !in 0 until W || Y !in 0 until H || dehors[Y * W + X] || pleinA(X - r, Y - r)) continue
                dehors[Y * W + X] = true
                pile.add(Y * W + X)
            }
        }
        for (k in d.indices) if (!dehors[k]) d[k] = -1f
        synchronized(distancesCache) {
            distancesCache[cle] = d
            while (distancesCache.size > 96) distancesCache.remove(distancesCache.keys.first())
        }
        return d
    }

    /** Teinte (0..1), saturation, valeur → 0xRRGGBB (comme colorsys.hsv_to_rgb). */
    fun hsv(t: Double, s: Double, v: Double): Int {
        val h = ((t % 1.0) + 1.0) % 1.0 * 6.0
        val i = h.toInt() % 6
        val f = h - Math.floor(h)
        val p = v * (1 - s); val q = v * (1 - s * f); val u = v * (1 - s * (1 - f))
        val (r, g, b) = when (i) { 0 -> Triple(v, u, p); 1 -> Triple(q, v, p); 2 -> Triple(p, v, u)
            3 -> Triple(p, q, v); 4 -> Triple(u, p, v); else -> Triple(v, p, q) }
        return ((r * 255).toInt() shl 16) or ((g * 255).toInt() shl 8) or (b * 255).toInt()
    }

    private fun hasard(x: Int, y: Int, n: Int): Int {
        var v = (x.toLong() * 73856093L) xor (y.toLong() * 19349663L) xor (n.toLong() * 83492791L)
        v = (v xor (v ushr 13)) * 1274126177L
        return ((v xor (v ushr 16)) and 0xFFFF).toInt()
    }

    /** L'aura seule d'une image (masque plein, w × h) pour un palier, une phase de respiration et un éclat. */
    fun calque(w: Int, h: Int, plein: BooleanArray, nom: String, phase: Int = PHASE_FIXE, eclat: Int = ECLAT_NORMAL): Calque {
        val p = PALIERS[nom] ?: PALIERS.getValue("commune")
        val ef = ECLAT_FORCE[eclat.coerceIn(0, 3)]
        val r = p.rayon
        val W = w + 2 * r; val H = h + 2 * r
        val dist = distances(w, h, plein, r)
        val out = IntArray(W * H)
        val ph = ((phase % PHASES) + PHASES) % PHASES
        val tour = 2 * Math.PI * ph / PHASES
        for (k in dist.indices) {
            val d = dist[k]
            if (d < 0) continue
            val x = k % W; val y = k / W
            val chute = ((r + 0.75 - d) / (r - 0.25)).coerceIn(0.0, 1.0)
            if (chute <= 0) continue
            val vague = 0.78 + 0.22 * Math.sin(tour - 0.9 * (d - 1))
            var a = p.force * chute * vague * ef / 100
            var c = p.couleur?.and(0xFFFFFF) ?: hsv((x + y).toDouble() / maxOf(8, W + H) * 1.6 + ph.toDouble() / PHASES, 0.55, 1.0)
            if (p.reflet) {
                val pos = ph.toDouble() / PHASES * (W + H + 8) - 4
                val e = maxOf(0.0, 1.0 - Math.abs((x + y) - pos) / 3.0)
                if (e > 0) {
                    fun eclaircir(v: Int) = (v + (255 - v) * 0.55 * e).toInt()
                    c = (eclaircir(c shr 16 and 0xFF) shl 16) or (eclaircir(c shr 8 and 0xFF) shl 8) or eclaircir(c and 0xFF)
                    a += 60 * e * chute
                }
            }
            if (eclat <= 0) {                                         // en veille : une lueur grise et douce
                val r_ = c shr 16 and 255; val g_ = c shr 8 and 255; val b_ = c and 255
                val gr = (r_ + g_ + b_) / 3
                c = (((r_ + gr) / 2) shl 16) or (((g_ + gr) / 2) shl 8) or ((b_ + gr) / 2)
            }
            out[k] = (a.toInt().coerceIn(0, 255) shl 24) or c
        }
        return Calque(W, H, r, out)
    }

    // ---------------------------------------------------------------- le décor (entiers, identique au Python)
    const val CYCLE_DECOR = 32
    val PARTICULES = mapOf("commune" to 0, "peu commune" to 4, "rare" to 6, "épique" to 8, "légendaire" to 10,
        "mythique" to 12, "shiny" to 12)
    private val ARC = intArrayOf(0xFF7A7A, 0xFFC56B, 0xFFF27A, 0x7DFF9B, 0x7AC8FF, 0xC59BFF)
    private val REFLET = setOf("légendaire", "mythique", "shiny")
    private val SIN = intArrayOf(0, 38, 71, 92, 100, 92, 71, 38, 0, -38, -71, -92, -100, -92, -71, -38)

    /** Un point du décor en demi-pixels sur la toile de l'aura (2W × 2H) ; devant = par-dessus la créature. */
    class Point(val x2: Int, val y2: Int, val couleur: Int, val alpha: Int, val devant: Boolean)

    private fun clair(c: Int, pct: Int): Int {
        val r = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
        return ((r + (255 - r) * pct / 100) shl 16) or ((g + (255 - g) * pct / 100) shl 8) or (b + (255 - b) * pct / 100)
    }

    /** Les particules qui montent (derrière) et les étincelles des shiny (devant) — même liste qu'aura.decor. */
    fun decor(w: Int, h: Int, plein: BooleanArray, nom: String, phase: Int = PHASE_FIXE, eclat: Int = ECLAT_NORMAL): List<Point> {
        val p = PALIERS[nom] ?: PALIERS.getValue("commune")
        val r = p.rayon
        val W = w + 2 * r; val H = h + 2 * r
        val ec = eclat.coerceIn(0, 3)
        val ef = ECLAT_FORCE[ec]
        val out = ArrayList<Point>()
        val n = (PARTICULES[nom] ?: 0) * intArrayOf(0, 1, 2, 3)[ec] / 2
        val ph = Math.floorMod(phase, CYCLE_DECOR)
        val oi = ORDRE.indexOf(nom)
        val graine = if (oi >= 0) (w * 131 + h * 7 + oi * 1013).toLong() else (w * 131 + h).toLong()
        val base = p.couleur?.and(0xFFFFFF) ?: 0xFFFFFF
        val a0 = minOf(255, (p.force + 40) * ef / 100)
        val bords = Array(h) { y ->
            var g = -1; var d = -1
            for (x in 0 until w) if (plein[y * w + x]) { if (g < 0) g = x; d = x }
            if (g < 0) null else intArrayOf(g, d)
        }
        for (i in 0 until n) {
            val hs = Vie.melange(graine * 7919 + i * 104729L + 17)
            val vie = (14 + (hs ushr 8) % 12).toInt()
            val age = ((ph + (hs ushr 16) % CYCLE_DECOR) % CYCLE_DECOR).toInt()
            if (age >= vie) continue
            val y0 = h / 3 + ((hs ushr 3) % maxOf(1, h - h / 3)).toInt()
            val b = bords[y0] ?: continue
            val ecart = ((hs ushr 24) % (r + 1)).toInt()
            val x0 = if (hs and 1L == 1L) 2 * (r + b[0] - 1 - ecart) else 2 * (r + b[1] + 1 + ecart) + 1
            val x2 = x0 + Math.floorDiv(SIN[(age * 2 + i * 3) % 16], 50)
            val y2 = 2 * (y0 + r) - age * (h + 2 * r) / vie
            if (x2 !in 0 until 2 * W || y2 !in 0 until 2 * H) continue
            val sx = Math.floorDiv(x2, 2) - r; val sy = Math.floorDiv(y2, 2) - r
            if (sx in 0 until w && sy in 0 until h && plein[sy * w + sx]) continue
            val a = a0 * minOf(age + 1, 3, vie - age) / 3
            val c = if (p.couleur == null) ARC[i % 6] else clair(base, 45)
            out.add(Point(x2, y2, c, a, false))
        }
        if (nom == "shiny" && ec > 0) {
            val bord = ArrayList<IntArray>()
            for (y in 0 until H) for (x in 0 until W) {
                val sx = x - r; val sy = y - r
                if (sx in 0 until w && sy in 0 until h && plein[sy * w + sx]) continue
                var pres = false
                for (bb in -1..1) for (aa in -1..1) {
                    val X = sx + aa; val Y = sy + bb
                    if (X in 0 until w && Y in 0 until h && plein[Y * w + X]) pres = true
                }
                if (pres) bord.add(intArrayOf(x, y))
            }
            if (bord.isNotEmpty()) {
                val fente = Math.floorDiv(phase, 4)
                val etape = Math.floorMod(phase, 4)
                val bras = intArrayOf(1, 3, 4, 2)[etape]
                for (j in 0 until 3) {
                    val hs = Vie.melange(graine * 31 + fente * 977L + j * 1013L + 5)
                    val q = bord[(hs % bord.size).toInt()]
                    val cx2 = 2 * q[0] + 1; val cy2 = 2 * q[1] + 1
                    out.add(Point(cx2, cy2, 0xFFFFFF, 255, true))
                    for (k in 1..bras) {
                        val a = 255 - 200 * k / (bras + 1)
                        val c = if (k > 1) 0xFFF6C8 else 0xFFFFFF
                        for (d in arrayOf(intArrayOf(k, 0), intArrayOf(-k, 0), intArrayOf(0, k), intArrayOf(0, -k))) {
                            if (cx2 + d[0] in 0 until 2 * W && cy2 + d[1] in 0 until 2 * H) out.add(Point(cx2 + d[0], cy2 + d[1], c, a, true))
                        }
                    }
                }
            }
        }
        return out
    }

    /** La position du reflet qui passe sur la créature (x + y sur la toile), ou null. */
    fun reflet(nom: String, phase: Int, W: Int, H: Int): Int? {
        if (nom !in REFLET) return null
        val ph = Math.floorMod(phase, CYCLE_DECOR)
        if (ph >= 20) return null
        return ph * (W + H + 8) / 20 - 4
    }

    /** Une couleur de la créature (0xRRGGBB) éclaircie par le reflet. */
    fun lustrer(c: Int, x: Int, y: Int, pos: Int?): Int {
        if (pos == null) return c
        val d = Math.abs(x + y - pos)
        return if (d > 2) c else clair(c, (3 - d) * 18)
    }

    // ---------------------------------------------------------------- dessin
    /** Le masque d'une image agrandie (echelle pixels d'écran par petit pixel) : (largeur, hauteur, plein). */
    fun masque(bmp: Bitmap, echelle: Int): Triple<Int, Int, BooleanArray> {
        val e = maxOf(1, echelle)
        val w = bmp.width / e; val h = bmp.height / e
        val plein = BooleanArray(w * h)
        for (y in 0 until h) for (x in 0 until w) plein[y * w + x] = (bmp.getPixel(x * e + e / 2, y * e + e / 2) ushr 24) >= 128
        return Triple(w, h, plein)
    }

    private val calques = LinkedHashMap<String, Bitmap>()
    private val entoures = LinkedHashMap<String, Bitmap>()
    private val net = Paint()
    private val leger = Paint().apply { setAlpha(90) }
    private val doux = Paint().apply { isFilterBitmap = true }
    private val pinceau = Paint()

    /**
     * La bestiole posée sur son aura : une nouvelle image agrandie de rayon × echelle de chaque côté.
     * garder = true : gardée en cache (les petites images des listes).
     */
    fun entourer(bmp: Bitmap, echelle: Int, nom: String, phase: Int = PHASE_FIXE, garder: Boolean = false,
                 eclat: Int = ECLAT_NORMAL): Bitmap {
        val (w, h, plein) = masque(bmp, echelle)
        val ph = ((phase % PHASES) + PHASES) % PHASES
        val cle = "$w/$h/${plein.contentHashCode()}/$nom/$ph/$eclat"
        val cleImage = "$cle/${Math.floorMod(phase, CYCLE_DECOR)}/${System.identityHashCode(bmp)}/$echelle"
        if (garder) synchronized(entoures) { entoures[cleImage]?.let { return it } }
        val aur = synchronized(calques) { calques[cle] } ?: run {
            val c = calque(w, h, plein, nom, phase, eclat)
            Bitmap.createBitmap(c.px, c.largeur, c.hauteur, Bitmap.Config.ARGB_8888).also { b ->
                synchronized(calques) {
                    calques[cle] = b
                    while (calques.size > 160) calques.remove(calques.keys.first())
                }
            }
        }
        val e = maxOf(1, echelle)
        val r = (PALIERS[nom] ?: PALIERS.getValue("commune")).rayon
        val m = r * e
        val res = Bitmap.createBitmap(bmp.width + 2 * m, bmp.height + 2 * m, Bitmap.Config.ARGB_8888)
        val cv = Canvas(res)
        val dst = RectF(0f, 0f, (aur.width * e).toFloat(), (aur.height * e).toFloat())
        cv.drawBitmap(aur, null as Rect?, dst, doux)                 // la lueur douce (agrandie avec lissage)
        cv.drawBitmap(aur, null as Rect?, dst, leger)                // + un peu de netteté (gros pixels)
        val dec = decor(w, h, plein, nom, phase, eclat)
        val cote = maxOf(1f, e / 2f)
        fun point(q: Point) {
            pinceau.color = (q.alpha.coerceIn(0, 255) shl 24) or q.couleur
            val x = q.x2 * e / 2f; val y = q.y2 * e / 2f
            cv.drawRect(x, y, x + cote, y + cote, pinceau)
        }
        for (q in dec) if (!q.devant) point(q)                       // les particules, derrière
        cv.drawBitmap(bmp, m.toFloat(), m.toFloat(), net)            // la bestiole, nette, par-dessus
        val pos = reflet(nom, phase, w + 2 * r, h + 2 * r)
        if (pos != null) {                                           // le reflet qui passe sur la créature
            for (y in 0 until h) for (x in 0 until w) {
                if (!plein[y * w + x] || Math.abs(x + r + y + r - pos) > 2) continue
                val c0 = bmp.getPixel(x * e + e / 2, y * e + e / 2) and 0xFFFFFF
                pinceau.color = 0xFF000000.toInt() or lustrer(c0, x + r, y + r, pos)
                cv.drawRect((m + x * e).toFloat(), (m + y * e).toFloat(), (m + (x + 1) * e).toFloat(), (m + (y + 1) * e).toFloat(), pinceau)
            }
        }
        for (q in dec) if (q.devant) point(q)                        // les étincelles, devant
        if (garder) synchronized(entoures) {
            entoures[cleImage] = res
            while (entoures.size > 48) entoures.remove(entoures.keys.first())
        }
        return res
    }

    /** Index d'un palier dans la balise de dessin (¤…~n¤, voir Bestiaire.balise). */
    fun code(nom: String): Int = ORDRE.indexOf(nom).coerceAtLeast(0)
    fun deCode(n: Int?): String? = if (n == null) null else ORDRE.getOrNull(n)
}
