package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Le dessin de la Salle des Données (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant les
 * illustrations (§ 7.15) :
 *  - labo : l'instrument de la vue déployée — les lignes (▤) entrent dans le tamis (grep), les ciseaux (cut), le moulin
 *    (sort), la calculatrice (awk), le copiste (sed), l'aiguillage (tee), la bibliothécaire (sqlite3)… et ressortent
 *    gardées, coupées, rangées, calculées ;
 *  - podium : les 3 plus fortes attaques de SA collection, en barres qui montent ;
 *  - laboratoire : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (les paillasses, les instruments, l'histogramme au
 *    mur qui pousse), formes simples.
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object DonneesDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val SYMBOLES = mapOf("bibliotheque" to "🗄", "export" to "📤", "copiste" to "✎", "calculatrice" to "🧮", "ciseaux" to "✂",
        "traducteur" to "🔤", "colle" to "🧴", "moulin" to "⚙", "aiguillage" to "🔀", "distributeur" to "📦", "tamis" to "🔍")
    val COULEURS = mapOf("bibliotheque" to EspaceDessin.JAUNE, "export" to EspaceDessin.CYAN, "copiste" to EspaceDessin.VIOLET,
        "calculatrice" to EspaceDessin.ORANGE, "ciseaux" to EspaceDessin.ROUGE, "traducteur" to EspaceDessin.VERT, "colle" to EspaceDessin.JAUNE,
        "moulin" to EspaceDessin.JAUNE, "aiguillage" to EspaceDessin.BLEU, "distributeur" to EspaceDessin.CYAN, "tamis" to EspaceDessin.CYAN)

    fun labo(tl: Toile, x0: Deploie.LaboD, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[x0.instrument] ?: EspaceDessin.CYAN
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        // place comptée : sur un petit écran (boîte basse), le titre et « de → vers » tiennent sur UNE ligne en haut,
        // l'instrument est plus petit, et rien ne se chevauche
        val serre = h < 80 * z
        val r = if (serre) minOf(17 * z, (h - 26 * z) / 2.2f).coerceAtLeast(6 * z) else 17 * z
        val ty = if (serre) y + 22 * z + (h - 22 * z) / 2 - 4 * z else y + h * 0.52f
        val cx = x + w / 2
        // le tapis : les lignes avancent, entrent dans l'instrument et ressortent transformées
        tl.ligne(x + 16 * z, ty + r * 0.7f, x + w - 16 * z, ty + r * 0.7f, a(EspaceDessin.PALE, 120), 2 * z)
        for (k in 0 until 6) {
            val u = ((k / 6.0 + q) % 1.0).toFloat()
            val px = x + 18 * z + u * (w - 36 * z)
            if (px < cx - r - 1 * z) tl.rrect(px - 7 * z, ty - 2 * z, 14 * z, 10 * z, 2 * z, a(EspaceDessin.PALE, 210), null, 0f)
            else if (px > cx + r + 1 * z) tl.rrect(px - 6 * z, ty, 12 * z, 8 * z, 2 * z, a(c, 230), null, 0f)
        }
        // l'instrument, qui tourne doucement
        tl.cercle(cx, ty + 2 * z, r, c, 2.4f * z)
        tl.lueur(cx, ty + 2 * z, r * 0.7f, a(c, 70))
        val an = q * 2 * PI
        tl.ligne(cx, ty + 2 * z, cx + (r * 0.76f * cos(an)).toFloat(), ty + 2 * z + (r * 0.76f * sin(an)).toFloat(), a(EspaceDessin.TEXTE, 180), 1.6f * z)
        tl.texte(SYMBOLES[x0.instrument] ?: "📊", cx, ty + 2 * z, r * 0.82f, EspaceDessin.TEXTE, false, 'c')
        val titre = x0.outil + " · " + t("dn.instrument.${x0.instrument}")
        if (serre) {
            tl.texte(titre, x + 14 * z, y + 12 * z, 10.5f * z, c, true, 'g', true)
            val dv = t("dn.labo.${x0.de}") + " → " + t("dn.labo.${x0.vers}")
            if (tl.mesure(titre, 10.5f * z, true, true) + tl.mesure(dv, 9.5f * z, false, false) + 40 * z < w)   // sinon : le titre seul
                tl.texte(dv, x + w - 14 * z, y + 12 * z, 9.5f * z, a(c, 230), false, 'd')
            return
        }
        tl.texte(titre, cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        tl.texte(t("dn.labo.${x0.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("dn.labo.${x0.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }
        // l'instrument, qui tourne doucement
        tl.cercle(cx, ty + 2 * z, 17 * z, c, 2.4f * z)
        tl.lueur(cx, ty + 2 * z, 12 * z, a(c, 70))
        val an = q * 2 * PI
        tl.ligne(cx, ty + 2 * z, cx + (13 * z * cos(an)).toFloat(), ty + 2 * z + (13 * z * sin(an)).toFloat(), a(EspaceDessin.TEXTE, 180), 1.6f * z)
        tl.texte(SYMBOLES[x0.instrument] ?: "📊", cx, ty + 2 * z, 14 * z, EspaceDessin.TEXTE, false, 'c')
        tl.texte(x0.outil + " · " + t("dn.instrument.${x0.instrument}"), cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        tl.texte(t("dn.labo.${x0.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("dn.labo.${x0.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }

    /** Le podium : les 3 plus fortes attaques (des barres qui montent, la première dorée). */
    fun podium(tl: Toile, valeurs: List<Pair<String, Int>>, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.JAUNE, 10), a(EspaceDessin.JAUNE, 100), 1.2f * z)
        if (valeurs.isEmpty()) return
        val q = minOf(1.0, p01(phase) * 1.6).toFloat()
        val maxi = maxOf(1, valeurs.maxOf { it.second })
        val bw = (w - 40 * z) / valeurs.size
        for ((k, v) in valeurs.withIndex()) {
            val bh = (h - 46 * z) * v.second / maxi * q
            val bx = x + 20 * z + k * bw
            val col = listOf(EspaceDessin.JAUNE, EspaceDessin.PALE, EspaceDessin.ORANGE)[k % 3]
            tl.rrect(bx + 6 * z, y + h - 22 * z - bh, bw - 12 * z, bh, 4 * z, a(col, 220), col, 1 * z)
            tl.texte("${v.second}", bx + bw / 2, y + h - 30 * z - bh, 11 * z, EspaceDessin.TEXTE, true, 'c', true)
            tl.texte(v.first, bx + bw / 2, y + h - 10 * z, 10 * z, EspaceDessin.DOUX, false, 'c')
        }
    }

    /** Le REPLI de l'illustration de l'entrée : le laboratoire de tri (paillasses, instruments, histogramme qui pousse). */
    fun laboratoire(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF0E1A24.toInt(), a(EspaceDessin.CYAN, 120), 1.2f * z)
        tl.rect(x + 2 * z, y + h * 0.72f, w - 4 * z, h * 0.28f - 2 * z, 0xFF1B2A36.toInt())
        // l'histogramme au mur, qui pousse
        val hx = x + w * 0.58f; val hb = y + h * 0.62f
        for (k in 0 until 6) {
            val v = (0.3f + 0.6f * ((k * 37) % 10) / 10f) * (0.6f + 0.4f * sin(q * 6.28f + k).coerceAtLeast(0f))
            tl.rect(hx + k * 14 * z, hb - v * h * 0.45f, 10 * z, v * h * 0.45f, listOf(EspaceDessin.CYAN, EspaceDessin.JAUNE, EspaceDessin.ORANGE)[k % 3])
        }
        tl.ligne(hx - 4 * z, hb, hx + 86 * z, hb, EspaceDessin.PALE, 1.4f * z)
        // la paillasse et ses instruments
        val sy = y + h * 0.72f
        for ((k, s) in listOf("🔍", "✂", "⚙", "🧮", "✎").withIndex()) {
            val sx = x + w * 0.08f + k * w * 0.1f
            tl.rrect(sx - 12 * z, sy - 26 * z, 24 * z, 22 * z, 5 * z, a(EspaceDessin.PALE, 40), a(EspaceDessin.PALE, 160), 1 * z)
            tl.texte(s, sx, sy - 15 * z, 12 * z, EspaceDessin.TEXTE, false, 'c')
        }
        // une feuille de tableau qui glisse sur la paillasse
        val fx = x + w * 0.05f + q * w * 0.45f
        tl.rrect(fx, sy + 8 * z, 26 * z, 18 * z, 3 * z, a(EspaceDessin.TEXTE, 230), EspaceDessin.PALE, 1 * z)
        for (k in 0 until 3) tl.ligne(fx + 3 * z, sy + 13 * z + k * 4 * z, fx + 23 * z, sy + 13 * z + k * 4 * z, a(EspaceDessin.FOND, 200), 1 * z)
        tl.texte("📊", x + w * 0.12f, y + h * 0.18f, 16 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
