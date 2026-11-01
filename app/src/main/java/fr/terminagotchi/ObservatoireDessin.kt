package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Le dessin de l'Observatoire de l'IA (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant
 * les illustrations (§ 7.15) :
 *  - lunette : la lunette de la vue déployée — ce qui entre (une consigne, deux textes, des exemples…) passe sous la
 *    lentille de l'outil (assistant, diff, wc, uniq -c, tests…) et ressort vérifié ou transformé (rapport, différences…) ;
 *  - votes : le devineur de type devant chaque créature testée — ses votes « Feu » et « pas Feu », ✔ ou ✖ ;
 *  - copies : l'agent Copieur qui s'emballe, puis l'arrêt d'urgence (le compteur s'arrête, le panneau STOP s'allume) ;
 *  - coupole : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (la coupole ouverte sur les étoiles, la lunette, les
 *    petits robots-assistants qui tournent autour), formes simples.
 * Aucun robot n'est une vraie IA ; aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object ObservatoireDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("assistant" to EspaceDessin.CYAN, "devine-type" to EspaceDessin.ORANGE, "devine-mot" to EspaceDessin.VIOLET,
        "agent" to EspaceDessin.VERT, "diff" to EspaceDessin.JAUNE, "wc" to EspaceDessin.JAUNE, "uniq -c" to EspaceDessin.JAUNE,
        "grep -c" to EspaceDessin.JAUNE, "tests" to EspaceDessin.VERT)

    /** La lentille (le travail de l'outil), qui tourne avec la phase. */
    private fun lentille(tl: Toile, cx: Float, cy: Float, r: Float, phase: Double, c: Int, z: Float) {
        tl.cercle(cx, cy, r, c, 2.4f * z)
        tl.cercle(cx, cy, r * 0.62f, a(c, 160), 1.4f * z)
        tl.lueur(cx, cy, r * 0.5f, a(c, 70))
        val an = phase * 2 * PI
        tl.ligne(cx + (r * 0.3f * cos(an)).toFloat(), cy + (r * 0.3f * sin(an)).toFloat(), cx + (r * 0.55f * cos(an)).toFloat(),
            cy + (r * 0.55f * sin(an)).toFloat(), a(EspaceDessin.TEXTE, 200), 2 * z)
        tl.ligne(cx + r * 0.7f, cy + r * 0.7f, cx + r * 1.25f, cy + r * 1.25f, c, 4 * z)
    }

    fun lunette(tl: Toile, lu: Deploie.Lunette, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[lu.outil] ?: EspaceDessin.CYAN
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val ty = y + h * 0.5f
        // le ciel étoilé qui défile sous la lunette
        for (k in 0 until 12) { val u = ((k / 12.0 + q) % 1.0).toFloat()
            tl.texte(if (k % 3 == 0) "✦" else "·", x + 16 * z + u * (w - 32 * z), ty + 16 * z + (k % 2) * 4 * z, 9 * z, a(EspaceDessin.PALE, 200), false, 'c') }
        val cx = x + w / 2
        lentille(tl, cx, ty - 6 * z, 14 * z, q, c, z)
        tl.texte(lu.outil, cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        val ox = x + 22 * z + q.toFloat() * (w - 44 * z)
        if (ox < cx) tl.rrect(ox - 9 * z, ty - 10 * z, 18 * z, 20 * z, 3 * z, a(EspaceDessin.TEXTE, 230), a(EspaceDessin.PALE, 255), 1 * z)
        else { tl.rrect(ox - 10 * z, ty - 8 * z, 20 * z, 18 * z, 6 * z, a(c, 230), a(c, 255), 1 * z); tl.texte("✔", ox, ty, 10 * z, EspaceDessin.FOND, true, 'c') }
        tl.texte(t("ob.lunette.${lu.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("ob.lunette.${lu.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }

    /** Le devineur de type devant chaque créature : une barre « Feu » (orange) et une barre « pas Feu » (bleue), ✔ ou ✖. */
    fun votes(tl: Toile, essais: List<Observatoire.Essai>, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.ORANGE, 10), a(EspaceDessin.ORANGE, 100), 1.2f * z)
        if (essais.isEmpty()) return
        val maxi = maxOf(1, essais.maxOf { maxOf(it.vf, it.vp) })
        val lh = (h - 24 * z) / essais.size
        val q = minOf(1.0, p01(phase) * 1.6).toFloat()
        for ((k, e) in essais.withIndex()) {
            val ly = y + 12 * z + k * lh + lh / 2
            val ok = e.vrai != null && e.devine == e.vrai
            tl.texte(if (ok) "✔" else if (e.vrai != null) "✖" else "?", x + 16 * z, ly, 13 * z, if (ok) EspaceDessin.VERT else EspaceDessin.ROUGE, true, 'c')
            tl.texte(e.nom, x + 28 * z, ly, 11 * z, EspaceDessin.TEXTE, true, 'g')
            val bx = x + w * 0.42f; val bw = w * 0.4f
            tl.rrect(bx, ly - 8 * z, maxOf(2 * z, bw * e.vf / maxi * q), 7 * z, 2 * z, EspaceDessin.ORANGE, null, 0f)
            tl.rrect(bx, ly + 1 * z, maxOf(2 * z, bw * e.vp / maxi * q), 7 * z, 2 * z, EspaceDessin.BLEU, null, 0f)
            tl.texte(Observatoire.label(e.devine), x + w - 12 * z, ly, 10.5f * z, if (e.devine) EspaceDessin.ORANGE else EspaceDessin.BLEU, true, 'd', true)
        }
    }

    /** L'agent Copieur qui s'emballe : des feuilles qui s'empilent ; avec STOP, le panneau rouge s'allume et tout s'arrête. */
    fun copies(tl: Toile, n: Int, stop: Boolean, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = if (stop) EspaceDessin.VERT else EspaceDessin.ROUGE
        tl.rrect(x, y, w, h, 14 * z, a(c, 12), a(c, 110), 1.2f * z)
        val q = p01(phase).toFloat()
        val montre = minOf(n, 40)
        for (k in 0 until montre) {
            val col = k % 10; val lig = k / 10
            val px = x + 18 * z + col * 14 * z + (if (!stop && k == montre - 1) sin(q * 6.28f) * 2 * z else 0f)
            tl.rect(px, y + h - 24 * z - lig * 12 * z, 11 * z, 9 * z, a(EspaceDessin.PALE, 220))
        }
        tl.texte("$n", x + w * 0.68f, y + h * 0.42f, 26 * z, c, true, 'c', true)
        tl.texte(t("ob.lunette.compte"), x + w * 0.68f, y + h * 0.42f + 22 * z, 10 * z, EspaceDessin.DOUX, false, 'c')
        // le panneau d'arrêt d'urgence
        val sx = x + w - 36 * z; val sy = y + 30 * z
        val xs = FloatArray(8) { i -> sx + (18 * z * cos(PI / 8 + i * PI / 4)).toFloat() }
        val ys = FloatArray(8) { i -> sy + (18 * z * sin(PI / 8 + i * PI / 4)).toFloat() }
        tl.poly(xs, ys, if (stop) EspaceDessin.ROUGE else a(EspaceDessin.ROUGE, 70))
        tl.texte("STOP", sx, sy, 8.5f * z, EspaceDessin.TEXTE, true, 'c', true)
        if (stop) tl.lueur(sx, sy, 22 * z, a(EspaceDessin.ROUGE, 90))
    }

    /** Le REPLI de l'illustration de l'entrée : la coupole ouverte sur les étoiles, la grande lunette, les petits
     *  robots-assistants (des programmes du jeu) qui tournent autour, le panneau d'arrêt d'urgence près de la porte. */
    fun coupole(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF0B1024.toInt(), a(EspaceDessin.VIOLET, 120), 1.2f * z)
        for (k in 0 until 24) { val sx = x + ((k * 73) % 100) / 100f * w; val sy = y + ((k * 37) % 50) / 100f * h
            tl.texte(if (k % 4 == 0) "✦" else "·", sx, sy + 8 * z, (if (k % 4 == 0) 10 else 8) * z, a(EspaceDessin.TEXTE, 120 + 120 * ((k + (q * 8).toInt()) % 2)), false, 'c') }
        tl.rect(x + 2 * z, y + h * 0.82f, w - 4 * z, h * 0.18f - 2 * z, 0xFF1B2030.toInt())
        // la coupole (un demi-disque) et sa fente ouverte
        val cx = x + w * 0.5f; val cy = y + h * 0.62f; val r = minOf(w * 0.24f, h * 0.42f)
        val xs = FloatArray(17) { i -> cx + (r * cos(PI + i * PI / 16)).toFloat() }
        val ys = FloatArray(17) { i -> cy + (r * sin(PI + i * PI / 16)).toFloat() }
        tl.poly(xs, ys, 0xFF6C7A96.toInt())
        tl.rect(cx - r, cy, 2 * r, h * 0.2f, 0xFF4A5468.toInt())
        tl.rect(cx - r * 0.12f, cy - r, r * 0.24f, r, 0xFF0B1024.toInt())
        // la lunette qui pointe le ciel et balaie doucement
        val an = -PI / 2 + 0.35 * sin(q * 2 * PI)
        tl.ligne(cx, cy - r * 0.2f, cx + (r * 1.05 * cos(an)).toFloat(), cy - r * 0.2f + (r * 1.05 * sin(an)).toFloat(), EspaceDessin.JAUNE, 7 * z)
        tl.lueur(cx + (r * 1.1 * cos(an)).toFloat(), cy - r * 0.2f + (r * 1.1 * sin(an)).toFloat(), 10 * z, a(EspaceDessin.JAUNE, 120))
        tl.rrect(cx - 10 * z, cy + h * 0.06f, 20 * z, h * 0.14f, 5 * z, 0xFF2D2219.toInt(), a(EspaceDessin.JAUNE, 120), 1 * z)
        // trois petits robots-assistants en orbite
        for (k in 0 until 3) {
            val b = q * 2 * PI + k * 2 * PI / 3
            val rx = cx + (r * 1.45f * cos(b)).toFloat(); val ry = cy - r * 0.25f + (r * 0.35f * sin(b)).toFloat()
            tl.rrect(rx - 7 * z, ry - 6 * z, 14 * z, 12 * z, 3 * z, listOf(EspaceDessin.CYAN, EspaceDessin.VERT, EspaceDessin.ORANGE)[k], EspaceDessin.FOND, 1 * z)
            tl.rect(rx - 3 * z, ry - 2 * z, 2 * z, 2 * z, EspaceDessin.FOND); tl.rect(rx + 1 * z, ry - 2 * z, 2 * z, 2 * z, EspaceDessin.FOND)
        }
        // le petit panneau STOP près de la porte
        tl.ellipse(cx + 26 * z, cy + h * 0.12f, 6 * z, 6 * z, EspaceDessin.ROUGE)
        tl.texte("🔭", x + w * 0.12f, y + h * 0.18f, 16 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
