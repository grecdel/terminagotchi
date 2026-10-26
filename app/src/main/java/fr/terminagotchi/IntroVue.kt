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
 * L'intro dessinée (Intro.kt) à la place de l'observatoire du terminal : les écrans du début, l'œuf et sa liste de
 * commandes (avec ses animations : il remue, brille, se fêle, éclot), puis les écrans de présentation (merci, chaque
 * fonction qui s'ouvre). Tout passe par le Peintre d'Intro (le même dessin que les aperçus du test JVM).
 * action : ce qu'a touché l'enfant (« suivant », « passer », « ok »).
 * creature : l'image de la créature (son guide) pour les écrans de présentation.
 */
class IntroVue(ctx: Context, private val jeu: Jeu, private val creature: () -> Bitmap?, private val action: (String) -> Unit) : View(ctx) {
    private val d = resources.displayMetrics.density
    /** « ecran » (page), « oeuf », « carte » (cid) */
    var mode = "ecran"
        private set
    var page = 1
        private set
    var cid = ""
        private set
    var chemin = "~"
    private var rendu = Intro.Rendu(320f, 200f, emptyList())
    private var anim: List<Triple<Int, String, Int>>? = null
    private var animK = 0
    private var phase = 0

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

    init { isClickable = true }

    fun montrerEcran(n: Int) { mode = "ecran"; page = n; majTaille() }
    fun montrerOeuf() { if (mode != "oeuf") { mode = "oeuf"; majTaille() } else invalidate() }
    fun montrerCarte(c: String) { if (mode != "carte" || cid != c) { mode = "carte"; cid = c; majTaille() } else invalidate() }

    /** Joue une réaction de l'œuf (« oeuf_1 » à « oeuf_3 », « eclosion ») : 6 images par seconde. */
    fun jouer(nom: String) {
        val n = Intro.numeroAnim(nom)
        if (n == 0) return
        anim = Intro.reaction(n)
        animK = 0
        removeCallbacks(pas)
        postDelayed(pas, 160L)
        invalidate()
    }

    private val pas = Runnable {
        val a = anim ?: return@Runnable
        animK++
        if (animK >= a.size) { anim = null; invalidate(); return@Runnable }
        invalidate()
        relancer()
    }

    private fun relancer() { removeCallbacks(pas); postDelayed(pas, 160L) }

    /** Le petit balancement de l'œuf quand rien ne se passe. */
    private val respire = Runnable {
        phase++
        if (mode == "oeuf" && anim == null) invalidate()
        if (isAttachedToWindow) postDelayed(this.respireRef, 900L)
    }
    private val respireRef: Runnable get() = respire

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        postDelayed(respire, 900L)
    }

    override fun onDetachedFromWindow() {
        removeCallbacks(respire)
        removeCallbacks(pas)
        super.onDetachedFromWindow()
    }

    private fun imageCourante(): Carte.Pix? {
        val a = anim
        if (a != null) {
            val (f, nom, k) = a[minOf(animK, a.size - 1)]
            return Intro.pixOeuf(f, nom, k) ?: creatureEnPix()
        }
        val fele = minOf(3, Intro.faits(jeu).size)
        return if (fele > 0 && phase % 6 == 0) Intro.pixOeuf(fele, "remue", 1) else null
    }

    /** À la fin de l'éclosion : la créature (sa première image) dans le cadre de l'œuf. */
    private fun creatureEnPix(): Carte.Pix? = try {
        val b = Sprites.bitmap(jeu, 1)
        val px = IntArray(b.width * b.height)
        b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        Carte.Pix(b.width, b.height, px)
    } catch (e: Exception) { null }

    private fun dessiner(l: Float): Intro.Rendu = when (mode) {
        "oeuf" -> Intro.dessinerOeuf(peintre, jeu, l, imageCourante())
        "carte" -> Intro.dessinerCarte(peintre, jeu, cid, l, chemin)
        else -> Intro.dessinerEcran(peintre, page, nbEcrans(), l)
    }

    fun nbEcrans() = Intro.d().optJSONArray("ecrans")?.length() ?: 4

    private fun majTaille() {
        val l = (if (width > 0) width else resources.displayMetrics.widthPixels - (40 * d).toInt()) / d
        val avant = rendu.h
        rendu = dessiner(l)                       // toile = null : seulement mesurer
        if (Math.abs(avant - rendu.h) > 0.5f) requestLayout()
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        if (w > 0) { toile = null; rendu = dessiner(w / d) }
        setMeasuredDimension(w, (rendu.h * d).toInt())
    }

    override fun onDraw(canvas: Canvas) {
        canvas.save()
        canvas.scale(d, d)
        toile = canvas
        rendu = dessiner(width / d)
        toile = null
        canvas.restore()
        if ((rendu.h * d).toInt() != height) requestLayout()
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.actionMasked == MotionEvent.ACTION_UP) {
            val x = e.x / d
            val y = e.y / d
            val b = rendu.boutons.firstOrNull { x >= it.x - 6 && x <= it.x + it.w + 6 && y >= it.y - 6 && y <= it.y + it.h + 6 }
            if (b != null) action(b.action)
            else if (mode == "carte" || mode == "ecran") action(if (mode == "carte") "ok" else "suivant")
            performClick()
        }
        return true
    }

    override fun performClick(): Boolean = super.performClick()
}
