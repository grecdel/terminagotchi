package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View

/**
 * La carte qui pousse, à l'écran (commande « carte ») : le dessin de Carte.kt sur un Canvas, à la place de
 * l'observatoire du terminal. Elle se redessine après chaque commande (TerminalActivity appelle rafraichir) :
 * ce qui vient d'apparaître scintille quelques secondes (nouveau !).
 *
 * Gestes : un doigt fait glisser la carte, deux doigts zooment (pincer), un double appui remet le zoom de départ,
 * le ✕ en haut à droite la ferme. creature : l'image de la créature de l'enfant (le « tu es ici »).
 */
class CarteVue(ctx: Context, private val jeu: Jeu, private val creature: () -> Bitmap?, private val fermer: () -> Unit) : View(ctx) {
    private val d = resources.displayMetrics.density
    private var zoom = 0f                     // 0 : pas encore choisi (ajusté à la largeur au premier dessin)
    private var ox = 0f
    private var oy = 0f
    private var noeuds: List<Maison.Noeud> = emptyList()
    private var pied: List<String> = emptyList()
    private var titre = ""
    private val brillent = HashMap<String, Long>()
    private var taille = Carte.Taille(320f, 200f)
    private var phase = 0
    private var ouverte = 0L

    private val pFond = Paint()
    private val pTexte = Paint(Paint.ANTI_ALIAS_FLAG)
    private val pPix = Paint().apply { isFilterBitmap = false }
    private val bitmaps = java.util.IdentityHashMap<Carte.Pix, Bitmap>()
    private var toile: Canvas? = null
    private val dst = RectF()

    private val peintre = object : Peintre {
        override fun rect(x: Float, y: Float, w: Float, h: Float, couleur: Int) {
            pFond.color = couleur
            toile?.drawRect(x, y, x + w, y + h, pFond)
        }

        override fun pixels(p: Carte.Pix, x: Float, y: Float, echelle: Float) {
            val b = bitmaps.getOrPut(p) { Bitmap.createBitmap(p.px, p.w, p.h, Bitmap.Config.ARGB_8888) }
            dst.set(x, y, x + p.w * echelle, y + p.h * echelle)
            toile?.drawBitmap(b, null, dst, pPix)
        }

        private fun police(taille: Float, mono: Boolean, gras: Boolean) {
            pTexte.textSize = taille
            pTexte.typeface = if (mono) (if (gras) Typeface.create(Typeface.MONOSPACE, Typeface.BOLD) else Typeface.MONOSPACE)
                else if (gras) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        }

        override fun texte(s: String, x: Float, y: Float, taille: Float, couleur: Int, mono: Boolean, gras: Boolean) {
            police(taille, mono, gras)
            pTexte.color = couleur
            toile?.drawText(s, x, y, pTexte)
        }

        override fun mesure(s: String, taille: Float, mono: Boolean, gras: Boolean): Float {
            police(taille, mono, gras)
            return pTexte.measureText(s)
        }

        override fun creature(x: Float, y: Float, h: Float): Boolean {
            val b = try { creature() } catch (e: Exception) { null } ?: return false
            val w = h * b.width / maxOf(1, b.height)
            dst.set(x - w / 2, y - h, x + w / 2, y)
            toile?.drawBitmap(b, null, dst, pPix)
            return true
        }
    }

    init {
        isClickable = true
        rafraichir()
        ouverte = System.currentTimeMillis()
    }

    /** Relit le terrain (après une commande) : ce qui apparaît scintille 8 secondes. */
    fun rafraichir() {
        noeuds = try { Maison.noeuds(jeu, marquer = true) } catch (e: Exception) { android.util.Log.e("TG", "carte", e); emptyList() }
        pied = try { Maison.pied(jeu) } catch (e: Exception) { emptyList() }
        titre = Carte.titre(jeu)
        val now = System.currentTimeMillis()
        for (n in noeuds) if (n.nouveau) brillent[n.cle] = now
        brillent.entries.removeAll { now - it.value > 8000L }
        invalidate()
        if (brillent.isNotEmpty()) animer()
    }

    private val pas = Runnable {
        phase++
        val now = System.currentTimeMillis()
        brillent.entries.removeAll { now - it.value > 8000L }
        invalidate()
        if (brillent.isNotEmpty() || now - ouverte < 6000L) animer()
    }

    private fun animer() {
        removeCallbacks(pas)
        postDelayed(pas, 400L)
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Carte.FOND)
        if (zoom == 0f && width > 0) zoom = maxOf(0.75f, minOf(1.2f, width / (taille.l * d)))
        val z = if (zoom == 0f) 1f else zoom
        borner()
        canvas.save()
        canvas.translate(ox, oy)
        canvas.scale(d * z, d * z)
        toile = canvas
        taille = Carte.dessiner(peintre, titre, noeuds, pied, brillent.keys, phase, 320f)
        toile = null
        canvas.restore()
        // le ✕ (fixe, en haut à droite) et, au début, comment se déplacer
        val c = 28f * d
        pFond.color = 0xCC0F1A14.toInt()
        canvas.drawRect(width - c - 4f * d, 4f * d, width - 4f * d, 4f * d + c, pFond)
        pTexte.color = Carte.VERT
        pTexte.typeface = Typeface.DEFAULT_BOLD
        pTexte.textSize = 18f * d
        canvas.drawText("✕", width - c + 2f * d, 4f * d + c - 8f * d, pTexte)
        if (System.currentTimeMillis() - ouverte < 6000L) {
            pTexte.typeface = Typeface.DEFAULT
            pTexte.textSize = 11f * d
            val s = t("carte.monde.geste")
            val w = pTexte.measureText(s)
            pFond.color = 0xDD0F1A14.toInt()
            canvas.drawRect(0f, height - 22f * d, width.toFloat(), height.toFloat(), pFond)
            pTexte.color = Carte.DOUX
            canvas.drawText(s, maxOf(4f * d, (width - w) / 2), height - 7f * d, pTexte)
        }
    }

    /** La carte ne part pas hors de la vue. */
    private fun borner() {
        val z = if (zoom == 0f) 1f else zoom
        val lw = taille.l * d * z
        val lh = taille.h * d * z
        ox = if (lw <= width) 0f else ox.coerceIn(width - lw, 0f)
        oy = if (lh <= height) 0f else oy.coerceIn(height - lh, 0f)
    }

    // ---------------------------------------------------------------- gestes
    private var x0 = 0f
    private var y0 = 0f
    private var dist0 = 0f
    private var zoom0 = 1f
    private var bouge = false
    private var dernierAppui = 0L

    private fun ecart(e: MotionEvent): Float {
        val dx = e.getX(0) - e.getX(1)
        val dy = e.getY(0) - e.getY(1)
        return Math.sqrt((dx * dx + dy * dy).toDouble()).toFloat()
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { x0 = e.x; y0 = e.y; bouge = false; parent?.requestDisallowInterceptTouchEvent(true) }
            MotionEvent.ACTION_POINTER_DOWN -> if (e.pointerCount >= 2) { dist0 = ecart(e); zoom0 = if (zoom == 0f) 1f else zoom; bouge = true }
            MotionEvent.ACTION_MOVE -> {
                if (e.pointerCount >= 2 && dist0 > 0f) {
                    val fx = (e.getX(0) + e.getX(1)) / 2
                    val fy = (e.getY(0) + e.getY(1)) / 2
                    val avant = if (zoom == 0f) 1f else zoom
                    zoom = (zoom0 * ecart(e) / dist0).coerceIn(0.5f, 3f)
                    ox = fx - (fx - ox) * zoom / avant
                    oy = fy - (fy - oy) * zoom / avant
                    invalidate()
                } else if (e.pointerCount == 1) {
                    val dx = e.x - x0
                    val dy = e.y - y0
                    if (bouge || Math.abs(dx) + Math.abs(dy) > 8f * d) {
                        bouge = true
                        ox += dx; oy += dy
                        x0 = e.x; y0 = e.y
                        invalidate()
                    }
                }
            }
            MotionEvent.ACTION_POINTER_UP -> { dist0 = 0f; x0 = e.x; y0 = e.y }
            MotionEvent.ACTION_UP -> {
                if (!bouge) {
                    val c = 36f * d
                    val now = System.currentTimeMillis()
                    if (e.x > width - c && e.y < c) fermer()
                    else if (now - dernierAppui < 350L) { zoom = 0f; ox = 0f; oy = 0f; invalidate() }
                    dernierAppui = now
                    performClick()
                }
            }
        }
        return true
    }

    override fun performClick(): Boolean = super.performClick()

    override fun onDetachedFromWindow() {
        removeCallbacks(pas)
        super.onDetachedFromWindow()
    }
}
