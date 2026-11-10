package fr.terminagotchi

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Une fiche par-dessus l'écran du jeu (allègement du 9 novembre, variante B) : le menu ☰ et ses 7 gros boutons, la
 * fiche de la créature (on la touche), la leçon en détail (le + de la ligne 🎯), les réglages. Une carte sombre en haut,
 * qui défile si elle est trop longue ; ✕ ou un toucher à côté la ferment. Le clavier de l'écran se range quand elle
 * s'ouvre (essai-111 : il cachait le bas du menu ☰) et revient quand elle se ferme (TerminalActivity.nouvelleFiche).
 */
class Fiche(private val ctx: Context, titre: String, private val surFermer: (Fiche) -> Unit) {
    private val dp = ctx.resources.displayMetrics.density
    private fun px(v: Float) = (v * dp).toInt()

    /** la vue à poser dans le cadre de l'écran (FrameLayout « fond ») */
    val racine = FrameLayout(ctx)
    /** le contenu de la carte (ce que remplissent texte, gros, barre, boutons) */
    val corps = LinearLayout(ctx)

    init {
        racine.setBackgroundColor(0xB0000000.toInt())
        racine.isClickable = true
        racine.setOnClickListener { fermer() }
        val defile = ScrollView(ctx)
        defile.isFocusable = false
        val carte = LinearLayout(ctx)
        carte.orientation = LinearLayout.VERTICAL
        carte.background = GradientDrawable().apply { setColor(0xFF1E1E2E.toInt()); setStroke(px(1f), 0xFF45456A.toInt()); cornerRadius = 18 * dp }
        carte.setPadding(px(14f), px(10f), px(14f), px(14f))
        carte.isClickable = true                         // un toucher dans la carte ne la ferme pas
        val tete = LinearLayout(ctx)
        tete.orientation = LinearLayout.HORIZONTAL
        tete.gravity = Gravity.CENTER_VERTICAL
        val t = TextView(ctx)
        t.text = titre
        t.textSize = 18f
        t.setTypeface(t.typeface, Typeface.BOLD)
        t.setTextColor(0xFFE6E6E6.toInt())
        tete.addView(t, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        val x = TextView(ctx)
        x.text = "✕"
        x.textSize = 22f
        x.gravity = Gravity.CENTER
        x.setTextColor(0xFF9A9AB0.toInt())
        x.contentDescription = Langue.t("ui.fermer")
        x.isFocusable = false
        x.setOnClickListener { fermer() }
        tete.addView(x, LinearLayout.LayoutParams(px(44f), px(44f)))
        carte.addView(tete)
        corps.orientation = LinearLayout.VERTICAL
        carte.addView(corps, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))
        defile.addView(carte, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT))
        val lp = FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP)
        lp.setMargins(px(10f), px(10f), px(10f), px(10f))
        racine.addView(defile, lp)
    }

    fun fermer() {
        (racine.parent as? android.view.ViewGroup)?.removeView(racine)
        surFermer(this)
    }

    private fun ajouter(v: View, haut: Float = 8f) {
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.topMargin = px(haut)
        corps.addView(v, lp)
    }

    /** Un texte (mis en forme : Vert.rendre pour les `commandes`). */
    fun texte(s: CharSequence, taille: Float = 14f, couleur: Int = 0xFFE6E6E6.toInt(), gras: Boolean = false, mono: Boolean = false): TextView {
        val v = TextView(ctx)
        v.text = s
        v.textSize = taille
        v.setTextColor(couleur)
        if (mono) v.typeface = Typeface.MONOSPACE
        if (gras) v.setTypeface(v.typeface, Typeface.BOLD)
        v.setLineSpacing(px(2f).toFloat(), 1f)
        ajouter(v, 6f)
        return v
    }

    /** Un titre de partie (« Ses envies », « Forces et équipe »…). */
    fun sousTitre(s: String) { texte(s, 13f, 0xFFFFD75F.toInt(), gras = true).also { (it.layoutParams as LinearLayout.LayoutParams).topMargin = px(14f) } }

    /** Un gros bouton (le menu ☰) : l'icône, le titre, une ligne d'explication. */
    fun gros(icone: String, titre: String, sous: String, action: () -> Unit): View {
        val b = LinearLayout(ctx)
        b.orientation = LinearLayout.HORIZONTAL
        b.gravity = Gravity.CENTER_VERTICAL
        b.setMinimumHeight(px(58f))
        b.setPadding(px(12f), px(8f), px(12f), px(8f))
        b.background = GradientDrawable().apply { setColor(0xFF26263A.toInt()); setStroke(px(1f), 0xFF3A3A55.toInt()); cornerRadius = 12 * dp }
        val i = TextView(ctx)
        i.text = icone
        i.textSize = 24f
        i.gravity = Gravity.CENTER
        b.addView(i, LinearLayout.LayoutParams(px(44f), LinearLayout.LayoutParams.WRAP_CONTENT))
        val col = LinearLayout(ctx)
        col.orientation = LinearLayout.VERTICAL
        val t = TextView(ctx)
        t.text = titre
        t.textSize = 16f
        t.setTypeface(t.typeface, Typeface.BOLD)
        t.setTextColor(0xFFE6E6E6.toInt())
        col.addView(t)
        if (sous.isNotEmpty()) {
            val s = TextView(ctx)
            s.text = sous
            s.textSize = 12f
            s.setTextColor(0xFF9A9AB0.toInt())
            col.addView(s)
        }
        val lpc = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        lpc.marginStart = px(8f)
        b.addView(col, lpc)
        b.isFocusable = false
        b.setOnClickListener { action() }
        ajouter(b, 8f)
        var avant = ""                                  // tests/vitrine.sh : où toucher ce bouton (logcat TG_POS)
        b.addOnLayoutChangeListener { w, _, _, _, _, _, _, _, _ ->
            val xy = IntArray(2)
            w.getLocationOnScreen(xy)
            val ici = "${xy[0] + w.width / 2} ${xy[1] + w.height / 2}"
            if (ici != avant) { avant = ici; android.util.Log.i("TG_POS", "gros:$icone $ici") }
        }
        return b
    }

    /** Une jauge : l'icône, le nom, la barre colorée, la valeur sur 100. */
    fun barre(icone: String, nom: String, valeur: Double, couleur: Int) {
        val l = LinearLayout(ctx)
        l.orientation = LinearLayout.HORIZONTAL
        l.gravity = Gravity.CENTER_VERTICAL
        val n = TextView(ctx)
        n.text = "$icone $nom"
        n.textSize = 14f
        n.setTextColor(0xFFE6E6E6.toInt())
        l.addView(n, LinearLayout.LayoutParams(px(130f), LinearLayout.LayoutParams.WRAP_CONTENT))
        val b = Barre(ctx)
        b.part = (valeur / 100.0).toFloat()
        b.couleur = couleur
        val lpb = LinearLayout.LayoutParams(0, px(10f), 1f)
        lpb.marginEnd = px(8f)
        l.addView(b, lpb)
        val v = TextView(ctx)
        v.text = Math.round(valeur).toString()
        v.textSize = 13f
        v.gravity = Gravity.END
        v.setTextColor(0xFF9A9AB0.toInt())
        l.addView(v, LinearLayout.LayoutParams(px(34f), LinearLayout.LayoutParams.WRAP_CONTENT))
        ajouter(l, 6f)
    }

    /** Une rangée de boutons (Album, Aura, Indice…). */
    fun boutons(vararg b: Pair<String, () -> Unit>) {
        val l = LinearLayout(ctx)
        l.orientation = LinearLayout.HORIZONTAL
        for ((k, p) in b.withIndex()) {
            val t = TextView(ctx)
            t.text = p.first
            t.textSize = 15f
            t.gravity = Gravity.CENTER
            t.setTextColor(0xFFE6E6E6.toInt())
            t.setMinimumHeight(px(44f))
            t.setPadding(px(14f), px(8f), px(14f), px(8f))
            t.background = GradientDrawable().apply { setColor(0xFF2E2E48.toInt()); setStroke(px(1f), 0xFF45456A.toInt()); cornerRadius = 10 * dp }
            t.isFocusable = false
            t.setOnClickListener { p.second() }
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            if (k > 0) lp.marginStart = px(8f)
            l.addView(t, lp)
        }
        ajouter(l, 12f)
    }
}

/** Une barre arrondie (l'XP de l'en-tête, les envies de la fiche) : part de 0 à 1. */
class Barre(ctx: Context) : View(ctx) {
    var part = 0f
        set(v) { field = v.coerceIn(0f, 1f); invalidate() }
    var couleur = 0xFFFFD75F.toInt()
        set(v) { field = v; invalidate() }
    var fond = 0xFF2E2E48.toInt()
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val r = RectF()

    override fun onDraw(c: Canvas) {
        val w = width.toFloat()
        val h = height.toFloat()
        val rayon = h / 2
        p.color = fond
        r.set(0f, 0f, w, h)
        c.drawRoundRect(r, rayon, rayon, p)
        if (part > 0f) {
            p.color = couleur
            r.set(0f, 0f, maxOf(h, w * part), h)
            c.drawRoundRect(r, rayon, rayon, p)
        }
    }
}
