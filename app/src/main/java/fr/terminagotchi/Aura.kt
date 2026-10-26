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

    /** L'aura seule d'une image (masque plein, w × h) pour un palier et une phase de respiration. */
    fun calque(w: Int, h: Int, plein: BooleanArray, nom: String, phase: Int = PHASE_FIXE): Calque {
        val p = PALIERS[nom] ?: PALIERS.getValue("commune")
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
            var a = p.force * chute * vague
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
            if (nom == "shiny" && d <= 2.2f && hasard(x, y, ph / 2) % 23 == 0) { c = 0xFFFFFF; a = 255.0 }   // étincelle
            out[k] = (a.toInt().coerceIn(0, 255) shl 24) or c
        }
        return Calque(W, H, r, out)
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

    /**
     * La bestiole posée sur son aura : une nouvelle image agrandie de rayon × echelle de chaque côté.
     * garder = true : gardée en cache (les petites images des listes).
     */
    fun entourer(bmp: Bitmap, echelle: Int, nom: String, phase: Int = PHASE_FIXE, garder: Boolean = false): Bitmap {
        val (w, h, plein) = masque(bmp, echelle)
        val cle = "$w/$h/${plein.contentHashCode()}/$nom/${((phase % PHASES) + PHASES) % PHASES}"
        val cleImage = "$cle/${System.identityHashCode(bmp)}/$echelle"
        if (garder) synchronized(entoures) { entoures[cleImage]?.let { return it } }
        val aur = synchronized(calques) { calques[cle] } ?: run {
            val c = calque(w, h, plein, nom, phase)
            Bitmap.createBitmap(c.px, c.largeur, c.hauteur, Bitmap.Config.ARGB_8888).also { b ->
                synchronized(calques) {
                    calques[cle] = b
                    while (calques.size > 160) calques.remove(calques.keys.first())
                }
            }
        }
        val e = maxOf(1, echelle)
        val m = (PALIERS[nom] ?: PALIERS.getValue("commune")).rayon * e
        val res = Bitmap.createBitmap(bmp.width + 2 * m, bmp.height + 2 * m, Bitmap.Config.ARGB_8888)
        val cv = Canvas(res)
        val dst = RectF(0f, 0f, (aur.width * e).toFloat(), (aur.height * e).toFloat())
        cv.drawBitmap(aur, null as Rect?, dst, doux)                 // la lueur douce (agrandie avec lissage)
        cv.drawBitmap(aur, null as Rect?, dst, leger)                // + un peu de netteté (gros pixels)
        cv.drawBitmap(bmp, m.toFloat(), m.toFloat(), net)            // la bestiole, nette, par-dessus
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
