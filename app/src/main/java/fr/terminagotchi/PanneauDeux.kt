package fr.terminagotchi

import android.content.Context
import android.util.AttributeSet
import android.view.View
import android.widget.LinearLayout

/**
 * Le panneau du jeu (idée 75). D'habitude : une colonne, comme avant (LinearLayout vertical).
 * Sur une TABLETTE tournée en paysage (deux = true) : deux colonnes sans rien déplacer.
 *  - à gauche (40 %) : tout ce qui vient AVANT `debutDroite` (la créature, ses jauges, la bulle, la leçon, la fenêtre
 *    d'observation, et ce qui s'insère à côté d'eux : l'intro, la carte) ;
 *  - à droite : `debutDroite` (la rangée des onglets) et ce qui suit : le terminal, qui prend toute la hauteur libre
 *    (l'élément qui a un poids), la rangée de touches, la ligne de saisie.
 * Les vues restent les mêmes, dans le même ordre : le reste de l'écran (qui insère à côté de l'observatoire ou du
 * terminal) n'a rien à savoir. Un téléphone tourné garde une seule colonne (TerminalActivity.majDisposition).
 */
class PanneauDeux(c: Context, a: AttributeSet?) : LinearLayout(c, a) {
    var deux = false
    var debutDroite: View? = null
    /** l'écart entre les deux colonnes, en pixels */
    var ecart = 0

    private fun indexDroite(): Int {
        val d = debutDroite ?: return childCount
        for (i in 0 until childCount) if (getChildAt(i) === d) return i
        return childCount
    }

    private fun marges(v: View): MarginLayoutParams =
        v.layoutParams as? MarginLayoutParams ?: MarginLayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)

    private fun largeurs(w: Int): Pair<Int, Int> {
        val interieur = w - paddingLeft - paddingRight - ecart
        val g = (interieur * 0.4f).toInt()
        return g to (interieur - g)
    }

    override fun onMeasure(wSpec: Int, hSpec: Int) {
        if (!deux) { super.onMeasure(wSpec, hSpec); return }
        val w = MeasureSpec.getSize(wSpec)
        val h = MeasureSpec.getSize(hSpec)
        val (lg, ld) = largeurs(w)
        val haut = h - paddingTop - paddingBottom
        val i0 = indexDroite()
        // à gauche : chacun sa hauteur, dans la place qui reste
        var y = 0
        for (i in 0 until i0) y += mesurer(getChildAt(i), lg, maxOf(0, haut - y))
        // à droite : d'abord ceux qui n'ont pas de poids, puis le terminal prend le reste
        var pris = 0
        var extensible: View? = null
        for (i in i0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == View.GONE) continue
            val lp = marges(v)
            if (((v.layoutParams as? LinearLayout.LayoutParams)?.weight ?: 0f) > 0f && extensible == null) {
                extensible = v; pris += lp.topMargin + lp.bottomMargin; continue
            }
            pris += mesurer(v, ld, maxOf(0, haut - pris))
        }
        extensible?.let { v ->
            val lp = marges(v)
            v.measure(MeasureSpec.makeMeasureSpec(maxOf(0, ld - lp.leftMargin - lp.rightMargin), MeasureSpec.EXACTLY),
                MeasureSpec.makeMeasureSpec(maxOf(0, haut - pris), MeasureSpec.EXACTLY))
        }
        setMeasuredDimension(w, h)
    }

    /** Mesure une vue dans une colonne ; renvoie la hauteur qu'elle prend (marges comprises), 0 si elle est cachée. */
    private fun mesurer(v: View, largeur: Int, reste: Int): Int {
        if (v.visibility == View.GONE) return 0
        val lp = marges(v)
        val lw = maxOf(0, largeur - lp.leftMargin - lp.rightMargin)
        val ws = if (lp.width >= 0) MeasureSpec.makeMeasureSpec(minOf(lp.width, lw), MeasureSpec.EXACTLY)
            else if (lp.width == LayoutParams.MATCH_PARENT) MeasureSpec.makeMeasureSpec(lw, MeasureSpec.EXACTLY)
            else MeasureSpec.makeMeasureSpec(lw, MeasureSpec.AT_MOST)
        val dispo = maxOf(0, reste - lp.topMargin - lp.bottomMargin)
        val hs = if (lp.height >= 0) MeasureSpec.makeMeasureSpec(minOf(lp.height, dispo), MeasureSpec.EXACTLY)
            else MeasureSpec.makeMeasureSpec(dispo, MeasureSpec.AT_MOST)
        v.measure(ws, hs)
        return v.measuredHeight + lp.topMargin + lp.bottomMargin
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        if (!deux) { super.onLayout(changed, l, t, r, b); return }
        val (lg, _) = largeurs(r - l)
        val i0 = indexDroite()
        var y = paddingTop
        for (i in 0 until i0) y = poser(getChildAt(i), paddingLeft, y)
        y = paddingTop
        for (i in i0 until childCount) y = poser(getChildAt(i), paddingLeft + lg + ecart, y)
    }

    private fun poser(v: View, x: Int, y: Int): Int {
        if (v.visibility == View.GONE) return y
        val lp = marges(v)
        val haut = y + lp.topMargin
        v.layout(x + lp.leftMargin, haut, x + lp.leftMargin + v.measuredWidth, haut + v.measuredHeight)
        return haut + v.measuredHeight + lp.bottomMargin
    }
}
