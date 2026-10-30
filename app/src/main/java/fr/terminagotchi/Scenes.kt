package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * L'intro en images sur le téléphone (portage de pc/tg/scenes.py, mêmes paramètres : intro.json « illustrations » ;
 * maquettes docs/maquettes/intro_telephone.png et intro_etapes.png).
 *
 * Les illustrations (assets/intro/monde.jpg, dort.jpg, camp.jpg, réduites par donnees/illustrations/generer_intro.py)
 * sont décodées une fois en pixels (chargeur : BitmapFactory sur Android, ImageIO dans les tests JVM). Le camp de base :
 *  1. il dort : la même image désaturée, assombrie, bleuie par le code (endormir) ;
 *  2. à la 1re commande de la liste, il se réveille : l'écran de l'ordinateur s'allume, la lumière remonte les câbles
 *     puis les veines de l'arbre (lumieres), la couleur revient derrière elle (eveil : chaque pixel retrouve sa couleur
 *     à l'instant donné par carteEveil) ;
 *  3. l'œuf du type tiré arrive « en téléchargement » (telecharge : ligne de pixels par ligne de pixels sur l'œuf fin
 *     104×104 d'Oeufs.fin, la ligne en cours scintille en vert, le bas n'est qu'un contour pointillé) ; chaque commande
 *     en apporte un morceau (cibles 37, 62, 87, 100 %) ; petit éclat à 100 % ;
 *  4. il éclot : la coquille reste dans le nid, le vrai bébé de l'espèce tirée sort (Peintre.bebe).
 * moment(jeu, t) dit où en est l'intro à l'instant t (ms) ; Intro.kt dessine (dessinerEcran, dessinerOeuf, dessinerCarte).
 */
object Scenes {
    /** Décode une illustration (« monde », « dort », « camp ») en pixels ARGB, ou null. */
    var chargeur: ((String) -> Carte.Pix?)? = null
    private val images = HashMap<String, Carte.Pix?>()

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { nom ->
            try {
                app.assets.open("intro/$nom.jpg").use { android.graphics.BitmapFactory.decodeStream(it) }?.let { b ->
                    val px = IntArray(b.width * b.height)
                    b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
                    Carte.Pix(b.width, b.height, px).also { b.recycle() }
                }
            } catch (e: Throwable) { null }
        }
    }

    /** Une illustration (« monde », « dort », « camp », ou « camp_dort » : le camp endormi calculé), ou null. */
    fun image(nom: String): Carte.Pix? = synchronized(images) {
        if (images.containsKey(nom)) return images[nom]
        val p = if (nom == "camp_dort") image("camp")?.let { endormir(it) } else try { chargeur?.invoke(nom) } catch (e: Throwable) { null }
        images[nom] = p
        p
    }

    fun disponible(): Boolean = image("camp") != null

    fun params(): JSONObject = Intro.d().optJSONObject("illustrations") ?: JSONObject()
    fun camp(): JSONObject = params().optJSONObject("camp") ?: JSONObject()
    private fun tele(): JSONObject = params().optJSONObject("telechargement") ?: JSONObject()

    /** La taille de l'image d'origine (les coordonnées d'intro.json sont dans ce repère). */
    fun taille(): Pair<Float, Float> = camp().optJSONArray("taille").let { (it?.optDouble(0, 1533.0) ?: 1533.0).toFloat() to (it?.optDouble(1, 863.0) ?: 863.0).toFloat() }

    private fun pt(o: JSONObject, k: String, d: Pair<Float, Float>): Pair<Float, Float> =
        o.optJSONArray(k)?.let { it.optDouble(0).toFloat() to it.optDouble(1).toFloat() } ?: d

    // ---------------------------------------------------------------- le camp endormi
    /** Le camp endormi : la même image, presque sans couleur, sombre et bleutée (intro.json camp.dort). */
    fun endormir(src: Carte.Pix): Carte.Pix {
        val d = camp().optJSONObject("dort") ?: JSONObject()
        val sat = d.optDouble("couleur", 0.15).toFloat()
        val lum = d.optDouble("lumiere", 0.38).toFloat()
        val m = d.optDouble("melange", 0.25).toFloat()
        val bl = d.optJSONArray("bleu") ?: JSONArray(listOf(20, 28, 60))
        val br = bl.optInt(0) * m
        val bg = bl.optInt(1) * m
        val bb = bl.optInt(2) * m
        val out = IntArray(src.px.size)
        for (i in src.px.indices) {
            val c = src.px[i]
            val r = (c shr 16) and 0xFF
            val g = (c shr 8) and 0xFF
            val b = c and 0xFF
            val gris = 0.299f * r + 0.587f * g + 0.114f * b
            fun v(x: Int, bleu: Float) = ((gris + (x - gris) * sat) * lum * (1 - m) + bleu).toInt().coerceIn(0, 255)
            out[i] = (c and 0xFF000000.toInt()) or (v(r, br) shl 16) or (v(g, bg) shl 8) or v(b, bb)
        }
        return Carte.Pix(src.w, src.h, out)
    }

    // ---------------------------------------------------------------- le réveil du camp
    class Point(val x: Float, val y: Float, val t: Float)

    private fun echantillons(): List<Point> {
        val c = camp()
        val v = c.optDouble("vitesse", 620.0).toFloat()
        val (ox, oy) = pt(c, "ordi", 312f to 408f)
        val out = mutableListOf(Point(ox, oy, 0.15f))
        val chemins = c.optJSONArray("chemins") ?: JSONArray()
        for (q in 0 until chemins.length()) {
            val ch = chemins.getJSONObject(q)
            val t0 = ch.optDouble("t").toFloat()
            val p = ch.getJSONArray("pts")
            var s = 0f
            for (k in 0 until p.length() - 1) {
                val a = p.getJSONArray(k); val b = p.getJSONArray(k + 1)
                val xa = a.getDouble(0).toFloat(); val ya = a.getDouble(1).toFloat()
                val xb = b.getDouble(0).toFloat(); val yb = b.getDouble(1).toFloat()
                val lg = Math.hypot((xb - xa).toDouble(), (yb - ya).toDouble()).toFloat()
                val n = maxOf(1, (lg / 14).toInt())
                for (j in 0 until n) {
                    val f = j.toFloat() / n
                    out.add(Point(xa + (xb - xa) * f, ya + (yb - ya) * f, t0 + (s + lg * f) / v))
                }
                s += lg
            }
            val z = p.getJSONArray(p.length() - 1)
            out.add(Point(z.getDouble(0).toFloat(), z.getDouble(1).toFloat(), t0 + s / v))
        }
        return out
    }

    private var tmCache: Pair<Int, FloatArray>? = null

    /** L'instant (s) où chaque pixel de l'image (w×h) retrouve sa couleur : la couleur part des points où passe la
     *  lumière ; tout est revenu à « fin ». Calculé sur une grille de 48×27, puis lissé. */
    fun carteEveil(w: Int, h: Int): FloatArray {
        tmCache?.let { if (it.first == w * 100000 + h) return it.second }
        val c = camp()
        val (tw, th) = taille()
        val cv = c.optDouble("couleur_vitesse", 360.0).toFloat()
        val fin = c.optDouble("fin", 2.9).toFloat()
        val pts = echantillons()
        val GW = 48; val GH = 27
        val g = FloatArray(GW * GH)
        for (gy in 0 until GH) for (gx in 0 until GW) {
            val x = (gx + 0.5f) * tw / GW
            val y = (gy + 0.5f) * th / GH
            var m = fin
            for (p in pts) {
                val dx = x - p.x; val dy = y - p.y
                val t = p.t + Math.sqrt((dx * dx + dy * dy).toDouble()).toFloat() / cv
                if (t < m) m = t
            }
            g[gy * GW + gx] = m
        }
        val out = FloatArray(w * h)
        for (y in 0 until h) {
            val sy = (y + 0.5f) / h * GH - 0.5f
            val ya = sy.toInt().coerceIn(0, GH - 1)
            val yb = minOf(GH - 1, ya + 1)
            val fy = (sy - ya).coerceIn(0f, 1f)
            for (x in 0 until w) {
                val sx = (x + 0.5f) / w * GW - 0.5f
                val xa = sx.toInt().coerceIn(0, GW - 1)
                val xb = minOf(GW - 1, xa + 1)
                val fx = (sx - xa).coerceIn(0f, 1f)
                val a = g[ya * GW + xa] * (1 - fx) + g[ya * GW + xb] * fx
                val b = g[yb * GW + xa] * (1 - fx) + g[yb * GW + xb] * fx
                out[y * w + x] = a * (1 - fy) + b * fy
            }
        }
        tmCache = (w * 100000 + h) to out
        return out
    }

    private var eveilBuf: Carte.Pix? = null

    /** Le camp à l'instant te (s) du réveil : endormi là où la couleur n'est pas encore revenue, en couleur derrière
     *  (un fondu de « fondu » s). Le même tampon est réutilisé d'une image à l'autre. */
    fun eveil(te: Float): Carte.Pix? {
        val base = image("camp") ?: return null
        val dort = image("camp_dort") ?: return null
        val tm = carteEveil(base.w, base.h)
        val buf = eveilBuf?.takeIf { it.w == base.w && it.h == base.h } ?: Carte.Pix(base.w, base.h, IntArray(base.px.size)).also { eveilBuf = it }
        val fd = camp().optDouble("fondu", 0.4).toFloat()
        val o = buf.px
        for (i in o.indices) {
            val f = (te - tm[i]) / fd
            o[i] = when {
                f <= 0f -> dort.px[i]
                f >= 1f -> base.px[i]
                else -> melange(dort.px[i], base.px[i], f)
            }
        }
        return buf
    }

    fun melange(a: Int, b: Int, f: Float): Int {
        val r = (((a shr 16) and 0xFF) + (((b shr 16) and 0xFF) - ((a shr 16) and 0xFF)) * f).toInt()
        val g = (((a shr 8) and 0xFF) + (((b shr 8) and 0xFF) - ((a shr 8) and 0xFF)) * f).toInt()
        val bl = ((a and 0xFF) + ((b and 0xFF) - (a and 0xFF)) * f).toInt()
        return (0xFF shl 24) or (r shl 16) or (g shl 8) or bl
    }

    /** Les lumières du réveil à l'instant t (s) : l'écran de l'ordinateur qui s'allume, puis la tête de chaque chemin
     *  de lumière (et un reste qui s'éteint au bout) ; (x, y, intensité) dans le repère de l'image d'origine. */
    fun lumieres(t: Float): List<Triple<Float, Float, Float>> {
        val c = camp()
        val v = c.optDouble("vitesse", 620.0).toFloat()
        val (ox, oy) = pt(c, "ordi", 312f to 408f)
        val out = mutableListOf<Triple<Float, Float, Float>>()
        if (t >= 0) out.add(Triple(ox, oy, minOf(1f, t / 0.5f) * (if (t < c.optDouble("duree", 3.4) - 0.6) 1f else 0.6f)))
        val chemins = c.optJSONArray("chemins") ?: JSONArray()
        for (q in 0 until chemins.length()) {
            val ch = chemins.getJSONObject(q)
            val p = ch.getJSONArray("pts")
            var s = (t - ch.optDouble("t").toFloat()) * v
            if (s < 0) continue
            var trouve = false
            for (k in 0 until p.length() - 1) {
                val a = p.getJSONArray(k); val b = p.getJSONArray(k + 1)
                val xa = a.getDouble(0).toFloat(); val ya = a.getDouble(1).toFloat()
                val xb = b.getDouble(0).toFloat(); val yb = b.getDouble(1).toFloat()
                val lg = Math.hypot((xb - xa).toDouble(), (yb - ya).toDouble()).toFloat()
                if (s <= lg) {
                    val f = s / maxOf(1f, lg)
                    out.add(Triple(xa + (xb - xa) * f, ya + (yb - ya) * f, 1f))
                    trouve = true
                    break
                }
                s -= lg
            }
            if (!trouve) {
                val reste = 1 - s / (v * 0.5f)
                val z = p.getJSONArray(p.length() - 1)
                if (reste > 0) out.add(Triple(z.getDouble(0).toFloat(), z.getDouble(1).toFloat(), reste))
            }
        }
        return out
    }

    // ---------------------------------------------------------------- le déroulé
    /** Le pourcentage de l'œuf reçu après n commandes de la liste. */
    fun cible(n: Int): Int {
        val c = tele().optJSONArray("cibles") ?: JSONArray(listOf(0, 37, 62, 87, 100))
        return c.optInt(n.coerceIn(0, c.length() - 1))
    }

    /** Où en est l'intro : phase dort | eveil | telech | eclat | eclot | ne ; te = secondes depuis le début de la phase ;
     *  pct = l'œuf reçu ; k = numéro d'image (le scintillement). */
    class Moment(val phase: String, val te: Float, val pct: Float, val k: Int)

    fun moment(jeu: Jeu, t: Long): Moment {
        val i = Intro.i(jeu)
        val faits = Intro.faits(jeu).size
        val fini = i.optString("etat") == "fini"
        val c = camp()
        val tl = tele()
        val duree = (c.optDouble("duree", 3.4) * 1000).toLong()
        val vit = tl.optDouble("vitesse", 24.0).toFloat()
        val tv = i.optJSONArray("evt")?.optLong(1, 0L) ?: 0L
        val te = i.optLong("eveil", 0L).takeIf { it > 0 } ?: if (faits == 1) tv else 0L
        if (faits == 0 && !fini) return Moment("dort", 0f, 0f, 0)
        if (te > 0 && t - te < duree) return Moment("eveil", (t - te) / 1000f, 0f, ((t - te) / 100).toInt())
        val n = if (fini) Intro.liste().size else faits
        val depart: Long
        val de: Int
        if (n <= 1) { depart = if (te > 0) te + duree else 0L; de = 0 }
        else { depart = if (te > 0) maxOf(tv, te + duree) else tv; de = cible(n - 1) }
        val a = cible(n)
        val pct = if (depart <= 0L) a.toFloat() else minOf(a.toFloat(), de + maxOf(0f, (t - depart) / 1000f) * vit)
        val k = ((t / 83) % 1_000_000L).toInt()
        if (!fini || pct < 100f) return Moment("telech", (t - depart) / 1000f, pct, k)
        val eclat = tl.optDouble("eclat", 0.7).toFloat()
        val eclot = tl.optDouble("eclot", 1.0).toFloat()
        var x = if (depart > 0) (t - depart) / 1000f - (100 - de) / vit else 99f
        if (x < eclat) return Moment("eclat", x, 100f, (x * 10).toInt())
        x -= eclat
        if (x < eclot) return Moment("eclot", x, 100f, (x * 6 / eclot).toInt())
        return Moment("ne", x, 100f, k)
    }

    /** Vrai tant que l'image bouge (réveil, réception, éclat, éclosion, étincelles du bébé) : la vue se redessine. */
    fun anime(m: Moment): Boolean = m.phase != "dort"

    // ---------------------------------------------------------------- l'œuf « en téléchargement »
    /** Un nombre de [0, 1) qui ne dépend que de (x, y, k) : le scintillement est le même à chaque rendu d'une image. */
    fun h(x: Int, y: Int, k: Int): Float {
        var v = ((x.toLong() * 73856093L) xor (y.toLong() * 19349663L) xor (k.toLong() * 83492791L)) and 0xFFFFFFFFL
        v = ((v xor (v ushr 13)) * 1274126177L) and 0xFFFFFFFFL
        return ((v xor (v ushr 16)) and 0xFFFFL).toFloat() / 65536f
    }

    const val VERT = 0xFF5CFF95.toInt()
    const val VERT_PALE = 0xFFDCFFE1.toInt()

    private fun alpha(c: Int, a: Int) = (c and 0xFFFFFF) or (a shl 24)

    /** La ligne en cours de réception : la première ligne où les pixels reçus atteignent pct % de l'œuf. */
    fun coupe(px: IntArray, w: Int, h: Int, pct: Float): Int {
        val par = IntArray(h) { y -> (0 until w).count { x -> (px[y * w + x] ushr 24) != 0 } }
        val tot = maxOf(1, par.sum())
        var acc = 0
        for (y in 0 until h) {
            acc += par[y]
            if (par[y] > 0 && acc.toFloat() / tot >= pct / 100f) return y
        }
        return h
    }

    /** L'œuf reçu à pct % (px : ARGB, w×h ; F = finesse : 4 pour l'œuf fin) → dans out (ARGB). Le haut est reçu ; la
     *  ligne en cours (F/2 pixels) scintille en vert ; juste au-dessus quelques pixels clignent ; le bas n'est qu'un
     *  contour fantôme en pointillés et quelques points très pâles ; des pixels verts sautent hors de la ligne. */
    fun telecharge(px: IntArray, w: Int, h: Int, pct: Float, k: Int, F: Int, out: IntArray) {
        fun op(x: Int, y: Int) = x in 0 until w && y in 0 until h && (px[y * w + x] ushr 24) != 0
        if (pct >= 100f) { System.arraycopy(px, 0, out, 0, px.size); return }
        java.util.Arrays.fill(out, 0)
        val cut = if (pct > 0) coupe(px, w, h, pct) else -1
        val ep = maxOf(1, F / 2)
        for (y in 0 until h) for (x in 0 until w) {
            val p = px[y * w + x]
            if ((p ushr 24) == 0) continue
            val i = y * w + x
            if (y < cut - ep + 1) {
                out[i] = if (y >= cut - 6 * ep && h(x, y, k) < 0.10f * (6 * ep - (cut - y)) / (6 * ep)) 0xFF96FFAA.toInt() else p
            } else if (pct > 0 && y <= cut) {
                val r = h(x, y, k + 7)
                out[i] = if (r < 0.55f) VERT else if (r < 0.75f) VERT_PALE else p
            } else {
                val bord = !op(x + ep, y) || !op(x - ep, y) || !op(x, y + ep) || !op(x, y - ep)
                out[i] = when {
                    bord && (if (F > 1) (y / ep) % 2 == 0 else (x + y) % 2 == 0) -> alpha(if (F > 1) VERT else 0x3CBE6E, 230)
                    !bord && F == 1 -> alpha(0, 120)
                    !bord && (x / ep + y / ep) % 9 == 0 -> alpha(VERT, 40)
                    else -> 0
                }
            }
        }
        if (cut in 0 until h && pct > 0) for (x in 0 until w) {
            if (op(x, cut) && h(x, cut, k + 3) < 0.12f) {
                val yy = cut + intArrayOf(-3, -2, 2, 3, 4)[(h(x, 0, k) * 5).toInt().coerceIn(0, 4)] * ep
                if (yy in 0 until h) out[yy * w + x] = alpha(VERT, intArrayOf(120, 200, 255)[(h(x, 1, k) * 3).toInt().coerceIn(0, 2)])
            }
        }
    }

    private var oeufBuf: Carte.Pix? = null
    private val oeufs = HashMap<String, Carte.Pix?>()

    /** L'œuf du moment (fin si possible, sinon le 26×26) : (pixels, finesse). Le même tampon pour la réception. */
    fun oeuf(ty: String, m: Moment): Pair<Carte.Pix, Int>? {
        val fin = Oeufs.aDesFins()
        val F = if (fin) (Oeufs.dFin().optInt("fin", 4)) else 1
        fun img(fele: Int, nom: String, k: Int): Carte.Pix? = synchronized(oeufs) {
            val cle = "$ty/$fin/$fele/$nom/$k"
            if (oeufs.containsKey(cle)) return@synchronized oeufs[cle]
            if (oeufs.size > 40) oeufs.clear()
            (if (fin) Oeufs.fin(ty, fele, nom, k) else Intro.pixOeuf(fele, nom, k, ty)).also { oeufs[cle] = it }
        }
        return when (m.phase) {
            "telech" -> {
                val src = img(0, "", 0) ?: return null
                val b = oeufBuf?.takeIf { it.w == src.w && it.h == src.h } ?: Carte.Pix(src.w, src.h, IntArray(src.px.size)).also { oeufBuf = it }
                telecharge(src.px, src.w, src.h, m.pct, m.k, F, b.px)
                b to F
            }
            "eclat" -> img(0, "brille", m.k)?.let { it to F }
            "eclot" -> img(3, "eclot", minOf(5, m.k))?.let { it to F }
            "ne" -> img(3, "eclot", 5)?.let { it to F }
            else -> null
        }
    }

    /** Le recadrage horizontal du téléphone (0 gauche, 1 droite) : sur l'ordinateur pendant le réveil, puis glisse
     *  doucement vers le nid quand l'œuf arrive. */
    fun cadrage(jeu: Jeu, m: Moment): Float {
        val c = camp().optJSONObject("cadrage") ?: JSONObject()
        val a = c.optDouble("eveil", 0.12).toFloat()
        val b = c.optDouble("oeuf", 0.5).toFloat()
        return when (m.phase) {
            "dort", "eveil" -> a
            "telech" -> if (Intro.faits(jeu).size <= 1) { val f = (m.te / 1.2f).coerceIn(0f, 1f); a + (b - a) * f * f * (3 - 2 * f) } else b
            else -> b + (c.optDouble("ne", 0.45).toFloat() - b) * (m.te / 0.8f).coerceIn(0f, 1f)
        }
    }
}
