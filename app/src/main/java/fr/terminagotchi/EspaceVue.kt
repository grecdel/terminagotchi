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
        etat.rafraichir(null, maintenant())
    }

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
        val v = etat.deployer(ligne, auto) ?: return
        exec.execute {
            val copie = Deploie.Vue(v.ligne, v.blocs, v.chaines, null)
            etat.calculer(copie)
            post { if (modele.vue === v) { v.sorties = copie.sorties; invalidate() } }
        }
        invalidate()
    }

    fun onglet(o: String) { modele.onglet = o; requestLayout(); invalidate() }

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

    override fun onDraw(cv: Canvas) {
        etat.preparer(maintenant())
        toile.cv = cv
        zones = EspaceDessin.dessiner(toile, modele, width.toFloat(), height.toFloat(), d)
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_UP) return true
        val a = zones.lastOrNull { it.dedans(e.x, e.y) }?.action ?: return true
        if (etat.toucher(a)) requestLayout()
        performClick()
        invalidate()
        return true
    }

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

        private fun police(taille: Float, gras: Boolean, mono: Boolean) {
            p.textSize = taille
            p.typeface = when {
                mono && gras -> Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                mono -> Typeface.MONOSPACE
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
                if (bitmaps.size > 160) bitmaps.clear()
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

        override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r0: Float) {
            val b = monde ?: try {
                context.assets.open("intro/monde.jpg").use { BitmapFactory.decodeStream(it) }.also { monde = it }
            } catch (e: Exception) { null } ?: return
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
}
