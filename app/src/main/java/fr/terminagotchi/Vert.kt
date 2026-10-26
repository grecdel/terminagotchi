package fr.terminagotchi

import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan

/**
 * Les commandes à taper, en vert (portage de langue.rendre sur PC).
 *
 * Dans les textes (assets/langues/xx.json et le code), une commande à taper est entre backticks : `mkdir cabane`.
 * Le rendu se fait au moment d'afficher : le terminal (miseEnForme), la bulle, la leçon, le lexique, le dressage,
 * la notification et le widget enlèvent les backticks et mettent la commande en vert (ForegroundColorSpan).
 * Les caractères de la commande ne changent pas : le copier-coller marche comme avant.
 * En arabe et en ourdou, Langue.bidi isole déjà chaque passage `…` de gauche à droite (LRI … PDI, gardés dans le vert).
 */
object Vert {
    /** le vert du PC (couleur 84 des 256 couleurs du terminal) */
    const val COULEUR = 0xFF5FFF87.toInt()
    const val MARQUE = '`'
    val PASSAGE = Regex("`([^`\\n]+)`")

    /** Le texte sans les backticks, et la place de chaque commande dans ce texte (début inclus, fin exclue). */
    fun passages(s: String): Pair<String, List<Pair<Int, Int>>> {
        if (MARQUE !in s) return s to emptyList()
        val sb = StringBuilder()
        val ou = mutableListOf<Pair<Int, Int>>()
        var i = 0
        for (m in PASSAGE.findAll(s)) {
            sb.append(s, i, m.range.first)
            val a = sb.length
            sb.append(m.groupValues[1])
            ou.add(a to sb.length)
            i = m.range.last + 1
        }
        sb.append(s, i, s.length)
        return sb.toString() to ou
    }

    /** Le texte sans backticks (Toast, recherche, copie…). */
    fun sansMarques(s: String): String = passages(s).first

    /** Ajoute le texte à sb en mettant les commandes en vert. Renvoie sb. */
    fun ajouter(sb: SpannableStringBuilder, s: String): SpannableStringBuilder {
        val (txt, ou) = passages(s)
        val d = sb.length
        sb.append(txt)
        for ((a, b) in ou) sb.setSpan(ForegroundColorSpan(COULEUR), d + a, d + b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        return sb
    }

    /** Le texte prêt à afficher (TextView, notification, widget) : les commandes en vert, sans backticks. */
    fun rendre(s: CharSequence?): CharSequence {
        if (s == null) return ""
        if (s !is String || MARQUE !in s) return s
        return ajouter(SpannableStringBuilder(), s)
    }
}
