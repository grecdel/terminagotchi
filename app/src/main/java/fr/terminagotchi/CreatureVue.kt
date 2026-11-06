package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
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

/**
 * Par-dessus l'écran du jeu (thème « créature », 3 novembre) : l'album des stades (commande `album`, ou le bouton
 * « Album » de la carte de la créature) et le moment d'évolution en plein écran. Le dessin est dans CreatureDessin ;
 * ici le temps et les touchers. fermer : appelé quand l'enfant referme (✕, toucher dehors, ou la fin de l'évolution).
 */
class CreatureVue(ctx: Context, private val jeu: Jeu, val mode: String, de: String? = null,
                  private val fermer: (CreatureVue) -> Unit) : View(ctx) {
    private val d = resources.displayMetrics.density
    private val t0 = System.nanoTime()
    fun maintenant() = (System.nanoTime() - t0) / 1e9
    private val album = if (mode == "album") CreatureDessin.modeleAlbum(jeu) else null
    private val evo = if (mode == "evolution") CreatureDessin.modeleEvo(jeu, de, 0.0) else null
    private var zones: List<EspaceDessin.Zone> = emptyList()
    private val toile = ToileCanvasCreature()
    private var vivant = false

    init {
        isClickable = true
        Poses.charger(ctx)
        // le son « evolution » : déjà joué par le moteur de sons (Sons.apresTour) quand le stade change
    }

    private val image = object : Runnable {
        override fun run() {
            if (!vivant) return
            invalidate()
            postOnAnimation(this)
        }
    }

    override fun onAttachedToWindow() { super.onAttachedToWindow(); vivant = true; postOnAnimation(image) }
    override fun onDetachedFromWindow() { vivant = false; removeCallbacks(image); super.onDetachedFromWindow() }

    override fun onDraw(cv: Canvas) {
        toile.cv = cv
        val w = width.toFloat(); val h = height.toFloat()
        album?.let { zones = CreatureDessin.album(toile, it, w, h, d, maintenant()) }
        evo?.let { CreatureDessin.evolution(toile, it, w, h, d, maintenant()) }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_UP) return true
        performClick()
        if (evo != null) {
            if (Creature.peutPasser(maintenant())) fermer(this)       // on peut passer au bout de 2 s
            return true
        }
        val a = zones.lastOrNull { it.dedans(e.x, e.y) }?.action
        val al = album ?: return true
        when {
            a == null || a == "album:fermer" -> fermer(this)
            a == "album:salut" -> al.salut = maintenant()
            a.startsWith("album:") && a != "album:cadre" -> { al.choisi = a.substringAfter(":"); al.salut = maintenant() }
        }
        invalidate()
        return true
    }

    override fun performClick(): Boolean { super.performClick(); return true }

    /** Le pinceau (le même contrat que celui de l'espace, EspaceVue). */
    private inner class ToileCanvasCreature : Toile {
        var cv: Canvas? = null
        private val p = Paint(Paint.ANTI_ALIAS_FLAG)
        private val pImg = Paint()
        private val r = RectF()
        private val bitmaps = HashMap<String, Bitmap>()

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

        override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float { police(taille, gras, mono); return p.measureText(s) }

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
                if (bitmaps.size > 300) bitmaps.clear()
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

        override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) {}
    }
}
