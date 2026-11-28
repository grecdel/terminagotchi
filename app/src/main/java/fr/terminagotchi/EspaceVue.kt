package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RadialGradient
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View
import java.util.concurrent.Executors

/**
 * L'espace de travail sur le téléphone (commande `espace`) : la vue graphique au-dessus du terminal de
 * TerminalActivity (qui garde tout son comportement). Le dessin est dans EspaceDessin.kt ; ici : la vie (la créature
 * du bureau, BureauVie, qui respire et cligne ; son cerveau, Cerveau.kt, qui choisit sa pose), la vue déployée de la
 * dernière commande (Deploie.kt, les lignes des tuyaux calculées à part), les onglets et les touchers.
 * Mode classe (`espace classe`) : tout plus grand, pour un grand écran.
 */
class EspaceVue(ctx: Context, jeu: Jeu, private val dossier: () -> java.io.File,
                chemin: () -> String) : View(ctx) {
    private val d = resources.displayMetrics.density
    val etat = EspaceEtat(jeu, dossier, chemin)
    val modele get() = etat.modele
    val cerveau get() = etat.cerveau
    private var zones: List<EspaceDessin.Zone> = emptyList()
    private val t0 = System.nanoTime()
    private var dernier = 0.0
    private val exec = Executors.newSingleThreadExecutor()
    private val bitmaps = HashMap<String, Bitmap>()
    private var monde: Bitmap? = null
    private var animer = false

    init {
        Poses.charger(ctx)
        etat.carte.ecrire = { c -> ecrireCommande?.invoke(c) }
        etat.carte.dire = { s -> etat.ile.annoncer(s) }
        etat.rafraichir(null, maintenant())
    }

    /** « Y aller » sur la carte : TerminalActivity écrit la commande dans la saisie (l'enfant appuie sur Entrée). */
    var ecrireCommande: ((String) -> Unit)? = null

    var classe: Boolean
        get() = etat.classe
        set(v) { etat.classe = v; requestLayout(); invalidate() }

    fun maintenant() = (System.nanoTime() - t0) / 1e9

    /** Après chaque commande : relire le jeu. code : le code de sortie de la dernière commande. */
    fun rafraichir(code: Int?) {
        etat.rafraichir(code, maintenant())
        invalidate()
    }

    /** La vue déployée d'une ligne : les blocs tout de suite, les lignes des tuyaux calculées à part (commandes sûres). */
    fun deployer(ligne: String, auto: Boolean = true) {
        etat.carte.commande(ligne)
        val v = etat.deployer(ligne, auto) ?: return
        exec.execute {
            val copie = Deploie.Vue(v.ligne, v.blocs, v.chaines, null)
            etat.calculer(copie)
            post { if (modele.vue === v) { v.sorties = copie.sorties; invalidate() } }
        }
        invalidate()
    }

    fun onglet(o: String) { modele.onglet = o; requestLayout(); invalidate() }

    /** Les effets d'une commande dans le monde des biomes (avant : la photo du terrain prise avant la commande). */
    fun effets(ligne: String, avant: Effets.Photo?, code: Int?, sortie: String, dossier: java.io.File) {
        etat.effets(ligne, avant, code, sortie, dossier)
        invalidate()
    }

    // ------------------------------------------------------------ le temps
    private val image = object : Runnable {
        override fun run() {
            if (!animer) return
            val now = maintenant()
            val dt = (now - dernier).coerceIn(0.0, 0.25)
            dernier = now
            etat.tick(dt, now)
            invalidate()
            postOnAnimation(this)
        }
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        animer = true
        dernier = maintenant()
        postOnAnimation(image)
    }

    override fun onDetachedFromWindow() {
        animer = false
        removeCallbacks(image)
        super.onDetachedFromWindow()
    }

    // ------------------------------------------------------------ mesure, dessin, toucher
    override fun onMeasure(wSpec: Int, hSpec: Int) {
        val w = MeasureSpec.getSize(wSpec).toFloat()
        val dispo = if (MeasureSpec.getMode(hSpec) == MeasureSpec.UNSPECIFIED) 2000 * d else MeasureSpec.getSize(hSpec).toFloat()
        // la place du terminal, des touches et de la saisie reste libre en dessous
        val h = EspaceDessin.hauteur(modele, w, dispo - 230 * d, d)
        setMeasuredDimension(w.toInt(), h.toInt())
    }

    private val toile = ToileCanvas()
    private val andikas = HashMap<Boolean, Typeface?>()

    /** La police Andika (SIL, OFL) si elle est livrée dans assets/polices/ ; sinon null (police habituelle). */
    private fun andika(gras: Boolean): Typeface? = andikas.getOrPut(gras) {
        try { Typeface.createFromAsset(context.assets, "polices/" + if (gras) "Andika-Bold.ttf" else "Andika-Regular.ttf") } catch (e: Exception) { null }
    }

    override fun onDraw(cv: Canvas) {
        etat.preparer(maintenant())
        toile.facile = modele.confort.facile
        toile.cv = cv
        zones = EspaceDessin.dessiner(toile, modele, width.toFloat(), height.toFloat(), d)
    }

    private var appuiX = 0f
    private var appuiY = 0f
    private var longFait = false
    private var glisseMonde: FloatArray? = null     // x, y d'avant, bougé (1) : on fait glisser le monde des biomes
    private var glisseCarte: FloatArray? = null     // x, y d'avant, bougé (1), largeur : on fait glisser la carte du réveil
    private var glisse: FloatArray? = null          // x, y d'avant, bougé (1), sens (0 options : vertical ; 1 onglets)
    /** Appui long sur une bande (créature, vue déployée) : le mode « ranger mon espace ». */
    private val appuiLong = Runnable {
        val sur = zones.filter { it.dedans(appuiX, appuiY) }.map { it.action }
        if (!etat.rangement && !etat.options && sur.any { it.startsWith("bande:") }) {
            longFait = true
            etat.rangement = true
            performHapticFeedback(0)   // HapticFeedbackConstants.LONG_PRESS
            requestLayout(); invalidate()
        }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.action) {
            MotionEvent.ACTION_DOWN -> {
                appuiX = e.x; appuiY = e.y; longFait = false
                val a = zones.lastOrNull { it.dedans(e.x, e.y) }?.action
                if (modele.onglet == "monde" && !etat.rangement && !etat.options && (a == "monde:vue" || a?.startsWith("monde:crea:") == true)) {
                    glisseMonde = floatArrayOf(e.x, e.y, 0f)
                    return true
                }
                if (modele.onglet == "carte" && !etat.rangement && !etat.options && a == "rv:carte") {
                    val zc = zones.lastOrNull { it.action == "rv:carte" }
                    glisseCarte = floatArrayOf(e.x, e.y, 0f, zc?.w ?: width.toFloat())
                    return true
                }
                val sous = zones.filter { it.dedans(e.x, e.y) }.map { it.action }
                if (etat.options || (!etat.rangement && "onglets:rangee" in sous)) {
                    glisse = floatArrayOf(e.x, e.y, 0f, if (etat.options) 0f else 1f)
                    if (etat.options) return true
                }
                if (etat.rangement && a != null && a.startsWith("rg:tenir:")) {
                    modele.glisse = a.removePrefix("rg:tenir:") to e.y
                    performHapticFeedback(0)   // HapticFeedbackConstants.LONG_PRESS
                    invalidate()
                } else postDelayed(appuiLong, 500)
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                glisseCarte?.let { g ->
                    if (g[2] > 0 || Math.abs(e.x - appuiX) + Math.abs(e.y - appuiY) > 12 * d) {
                        etat.carte.glisser(e.x - g[0], e.y - g[1], g[3]); g[0] = e.x; g[1] = e.y; g[2] = 1f; invalidate()
                    }
                    return true
                }
                glisseMonde?.let { g ->
                    if (g[2] > 0 || Math.abs(e.x - appuiX) + Math.abs(e.y - appuiY) > 12 * d) {
                        modele.monde?.glisser(e.x - g[0], e.y - g[1]); g[0] = e.x; g[1] = e.y; g[2] = 1f; invalidate()
                    }
                    return true
                }
                glisse?.let { g ->
                    if (g[2] > 0 || Math.abs(e.x - appuiX) + Math.abs(e.y - appuiY) > 12 * d) {
                        removeCallbacks(appuiLong)
                        if (g[3] == 0f) modele.defile -= e.y - g[1] else modele.ongletsDecalage -= e.x - g[0]
                        g[0] = e.x; g[1] = e.y; g[2] = 1f; invalidate()
                        return true
                    }
                }
                if (Math.abs(e.x - appuiX) + Math.abs(e.y - appuiY) > 12 * d) removeCallbacks(appuiLong)
                modele.glisse?.let { modele.glisse = it.first to e.y; invalidate() }
                return true
            }
            MotionEvent.ACTION_CANCEL -> { removeCallbacks(appuiLong); modele.glisse = null; invalidate(); return true }
            MotionEvent.ACTION_UP -> {
                removeCallbacks(appuiLong)
                val gc = glisseCarte
                if (gc != null) {
                    glisseCarte = null
                    if (gc[2] == 0f) zones.lastOrNull { it.dedans(e.x, e.y) && it.action != "rv:carte" }?.action?.let { a -> etat.toucher(a) }
                    performClick(); invalidate()
                    return true
                }
                val gl = glisse
                glisse = null
                if (gl != null && gl[2] > 0f) { performClick(); invalidate(); return true }
                val gm = glisseMonde
                if (gm != null) {
                    glisseMonde = null
                    if (gm[2] == 0f) zones.lastOrNull { it.dedans(e.x, e.y) }?.action?.let { a -> etat.toucherMonde(a, e.x, e.y) }
                    performClick(); invalidate()
                    return true
                }
                val g = modele.glisse
                if (g != null) {                       // la bande lâchée : à la place la plus proche
                    modele.glisse = null
                    val places = zones.filter { it.action.startsWith("rg:place:") }
                    val i = places.minByOrNull { Math.abs(it.y + it.h / 2 - e.y) }?.action?.removePrefix("rg:place:")?.toIntOrNull()
                    if (i != null) etat.deplacerBande(g.first, i)
                    requestLayout(); invalidate()
                    return true
                }
                if (longFait) return true
                val a = zones.lastOrNull { it.dedans(e.x, e.y) }?.action ?: return true
                val avant = etat.rangement || etat.options
                if (etat.toucher(a) || avant != (etat.rangement || etat.options)) requestLayout()
                etat.question?.let { q -> demanderQuestion?.invoke(q.first) }
                if (a.startsWith("opt:conf:")) apresConfort?.invoke()
                performClick()
                invalidate()
                return true
            }
        }
        return true
    }

    /** TerminalActivity écrit la question des grands dans le terminal (la réponse s'y tape). */
    var demanderQuestion: ((String) -> Unit)? = null

    /** Après un réglage de « Lecture et confort » : TerminalActivity remet le terminal à la bonne taille. */
    var apresConfort: (() -> Unit)? = null

    override fun performClick(): Boolean { super.performClick(); return true }

    // ------------------------------------------------------------ le pinceau
    private inner class ToileCanvas : Toile {
        var cv: Canvas? = null
        private val p = Paint(Paint.ANTI_ALIAS_FLAG)
        private val pImg = Paint()
        private val r = RectF()

        override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) {
            p.style = Paint.Style.FILL; p.color = c; p.shader = null
            cv?.drawRect(x, y, x + w, y + h, p)
        }

        override fun rrect(x: Float, y: Float, w: Float, h: Float, rr: Float, fond: Int?, bord: Int?, ep: Float) {
            r.set(x, y, x + w, y + h)
            val ra = minOf(rr, w / 2, h / 2)
            p.shader = null
            if (fond != null) { p.style = Paint.Style.FILL; p.color = fond; cv?.drawRoundRect(r, ra, ra, p) }
            if (bord != null && ep > 0) { p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = bord; cv?.drawRoundRect(r, ra, ra, p) }
            p.style = Paint.Style.FILL
        }

        override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) {
            p.style = Paint.Style.FILL; p.color = c; p.shader = null
            r.set(cx - rx, cy - ry, cx + rx, cy + ry); cv?.drawOval(r, p)
        }

        override fun cercle(cx: Float, cy: Float, rr: Float, c: Int, ep: Float) {
            p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = c; p.shader = null
            cv?.drawCircle(cx, cy, rr, p)
            p.style = Paint.Style.FILL
        }

        override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) {
            p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = c; p.shader = null
            p.pathEffect = if (plein > 0) DashPathEffect(floatArrayOf(plein, vide), dec) else null
            cv?.drawLine(x1, y1, x2, y2, p)
            p.pathEffect = null
            p.style = Paint.Style.FILL
        }

        override fun poly(xs: FloatArray, ys: FloatArray, c: Int) {
            val chemin = Path()
            chemin.moveTo(xs[0], ys[0])
            for (i in 1 until xs.size) chemin.lineTo(xs[i], ys[i])
            chemin.close()
            p.style = Paint.Style.FILL; p.color = c; p.shader = null
            cv?.drawPath(chemin, p)
        }

        /** « Lecture facile » (Confort.kt) : Andika si assets/polices/ l'a, 8 % plus grand, lettres plus espacées. */
        var facile = false

        private fun police(taille: Float, gras: Boolean, mono: Boolean) {
            val f = facile && !mono
            p.textSize = if (f) taille * Confort.FACILE_TAILLE else taille
            p.setLetterSpacing(if (f) Confort.FACILE_ESPACE else 0f)
            p.typeface = when {
                mono && gras -> Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                mono -> Typeface.MONOSPACE
                f -> andika(gras) ?: if (gras) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
                gras -> Typeface.DEFAULT_BOLD
                else -> Typeface.DEFAULT
            }
        }

        override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) {
            police(taille, gras, mono)
            p.style = Paint.Style.FILL; p.color = c; p.shader = null
            p.textAlign = when (ancre) { 'c' -> Paint.Align.CENTER; 'd' -> Paint.Align.RIGHT; else -> Paint.Align.LEFT }
            val fm = p.fontMetrics
            cv?.drawText(s, x, y - (fm.ascent + fm.descent) / 2, p)
            p.textAlign = Paint.Align.LEFT
        }

        override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float {
            police(taille, gras, mono)
            return p.measureText(s)
        }

        override fun lueur(cx: Float, cy: Float, rr: Float, c: Int) {
            if (rr <= 0) return
            p.style = Paint.Style.FILL
            p.shader = RadialGradient(cx, cy, rr, c, c and 0x00FFFFFF, Shader.TileMode.CLAMP)
            cv?.drawCircle(cx, cy, rr, p)
            p.shader = null
        }

        override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float,
                           rot: Float, alpha: Float) {
            if (alpha <= 0.01f) return
            val b = bitmaps.getOrPut(c.cle) {
                if (bitmaps.size > 900) bitmaps.clear()      // (le monde des biomes : un dessin par sorte de prisme)
                Bitmap.createBitmap(c.argb, c.w, c.h, Bitmap.Config.ARGB_8888)
            }
            val k = cv ?: return
            pImg.isFilterBitmap = lisse
            pImg.alpha = (255 * alpha.coerceIn(0f, 1f)).toInt()
            k.save()
            k.translate(ax, ay)
            if (rot != 0f) k.rotate(-rot)
            k.scale(if (miroir) -sx else sx, sy)
            k.drawBitmap(b, Rect(0, 0, c.w, c.h), RectF(-c.ax * e, -c.ay * e, (c.w - c.ax) * e, (c.h - c.ay) * e), pImg)
            k.restore()
            pImg.alpha = 255
        }

        override fun clip(x: Float, y: Float, w: Float, h: Float) { cv?.save(); cv?.clipRect(x, y, x + w, y + h) }
        override fun declip() { cv?.restore() }

        override fun photoCercle(nom: String, x: Float, y: Float, w: Float, h: Float, cx: Float, cy: Float, r: Float) {
            val k = cv ?: return
            k.save()
            val rr = maxOf(0.1f, r)
            val c = Path(); c.addRoundRect(RectF(cx - rr, cy - rr, cx + rr, cy + rr), rr, rr, Path.Direction.CW)
            k.clipPath(c)
            photo(nom, x, y, w, h, 0f)
            k.restore()
        }

        override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r0: Float) {
            if (nom.startsWith("reveil:")) { photoReveil(nom, x, y, w, h); return }
            val base = monde ?: try {
                context.assets.open("intro/monde.jpg").use { BitmapFactory.decodeStream(it) }.also { monde = it }
            } catch (e: Exception) { null } ?: return
            val th = nom.substringAfter(':', "")
            val b = if (th.isEmpty()) base else bitmaps.getOrPut("monde:$th") { teinter(base, Apparence.Theme(th)) }
            val k = cv ?: return
            val ech = maxOf(w / b.width, h / b.height)
            val sw = w / ech; val sh = h / ech
            val sx = ((b.width - sw) / 2).toInt(); val sy = ((b.height - sh) / 2).toInt()
            k.save()
            val chemin = Path()
            chemin.addRoundRect(RectF(x, y, x + w, y + h), r0, r0, Path.Direction.CW)
            k.clipPath(chemin)
            pImg.isFilterBitmap = true
            k.drawBitmap(b, Rect(sx, sy, sx + sw.toInt(), sy + sh.toInt()), RectF(x, y, x + w, y + h), pImg)
            k.restore()
        }
    }

    // ------------------------------------------------------------ la carte du réveil (Reveil.Images)
    private var images: Reveil.Images? = null
    private val reveils = LinkedHashMap<String, Bitmap>()

    private fun pixels(nom: String): Triple<IntArray, Int, Int>? = try {
        context.assets.open(nom).use { BitmapFactory.decodeStream(it) }?.let { b ->
            val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height); Triple(px, b.width, b.height)
        }
    } catch (e: Exception) { null }

    /** La carte mélangée de la partie (calculée une fois par état ; on en garde 4). */
    private fun bitmapReveil(nom: String): Bitmap? {
        reveils[nom]?.let { return it }
        val im = images ?: run {
            val v = pixels("intro/monde.jpg") ?: return null
            val dd = pixels("intro/dort.jpg") ?: return null
            val mq = pixels("intro/reveil_masques.png") ?: return null
            Reveil.Images(v.first, dd.first, v.second, v.third, mq.first, mq.second, mq.third).also { images = it }
        }
        val p = nom.split(":")
        var b = Bitmap.createBitmap(im.image(p.take(4).joinToString(":")), im.w, im.h, Bitmap.Config.ARGB_8888)
        if (p.size > 4 && p[4].isNotEmpty()) b = teinter(b, Apparence.Theme(p[4]))
        while (reveils.size >= 4) reveils.remove(reveils.keys.first())
        reveils[nom] = b
        return b
    }

    private fun photoReveil(nom: String, x: Float, y: Float, w: Float, h: Float) {
        val b = bitmapReveil(nom) ?: return
        val k = toile.cv ?: return
        val pi = Paint().apply { isFilterBitmap = true }
        k.drawBitmap(b, null, RectF(x, y, x + w, y + h), pi)
    }

    /** La carte du monde dans la teinte du thème (Matrix, ambre : niveaux de gris teintés ; Game Boy : 4 verts). */
    private fun teinter(b: Bitmap, th: Apparence.Theme): Bitmap {
        val w = b.width; val h = b.height
        val px = IntArray(w * h)
        b.getPixels(px, 0, w, 0, 0, w, h)
        val gb = intArrayOf(0x0F380F, 0x306230, 0x8BAC0F, 0x9BBC0F)
        val t = th.carte
        val col = (t as? org.json.JSONArray)?.let { intArrayOf(it.getInt(0), it.getInt(1), it.getInt(2)) }
        for (i in px.indices) {
            val p = px[i]
            val v = ((p shr 16 and 255) * 0.299 + (p shr 8 and 255) * 0.587 + (p and 255) * 0.114).toInt()
            px[i] = (0xFF shl 24) or (if (col == null) gb[minOf(3, v * 4 / 256)]
                else ((col[0] * v / 255) shl 16) or ((col[1] * v / 255) shl 8) or (col[2] * v / 255))
        }
        return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
    }
}
