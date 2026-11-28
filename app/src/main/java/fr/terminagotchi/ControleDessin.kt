package fr.terminagotchi

import kotlin.math.sin

/**
 * Le dessin du Poste de Contrôle (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant les
 * illustrations (§ 7.15) :
 *  - tableau : le tableau de bord de la vue déployée — une jauge qui oscille quand on LIT (ps, df, journalctl…), un voyant
 *    qui s'éteint quand on ARRÊTE un habitant (kill), un voyant orange qui clignote quand la commande CHANGERAIT la
 *    machine (avec un adulte) ;
 *  - jauges : les jauges du vaisseau (mémoire, disque) en barres ;
 *  - poste : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (le pupitre rond, ses jauges, ses voyants, le réveil, les
 *    habitants qui travaillent ou dorment), formes simples.
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object ControleDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("habitants" to EspaceDessin.VIOLET, "memoire" to EspaceDessin.VERT, "entrepot" to EspaceDessin.JAUNE,
        "charge" to EspaceDessin.ROUGE, "sac" to EspaceDessin.ORANGE, "carnet" to EspaceDessin.JAUNE, "reveil" to EspaceDessin.ORANGE,
        "magasin" to EspaceDessin.CYAN, "services" to EspaceDessin.VIOLET, "equipage" to EspaceDessin.BLEU)
    val SYMBOLES = mapOf("habitants" to "👻", "memoire" to "🥫", "entrepot" to "📦", "charge" to "💨", "sac" to "🎒", "carnet" to "📓",
        "reveil" to "⏰", "magasin" to "🏪", "services" to "🛡", "equipage" to "🧑")

    fun tableau(tl: Toile, x0: Deploie.Tableau, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = if (x0.sens == "change") EspaceDessin.ORANGE else COULEURS[x0.jauge] ?: EspaceDessin.CYAN
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val titre = (SYMBOLES[x0.jauge] ?: "📟") + " " + t("ct.tableau.jauge.${x0.jauge}")
        tl.texte(titre, x + 14 * z, y + 13 * z, 11 * z, c, true, 'g', false)
        tl.texte(t("ct.tableau.sens.${x0.sens}"), x + w - 14 * z, y + 13 * z, 10 * z, a(c, 230), false, 'd')
        val by = y + 26 * z
        val bh = minOf(h - 34 * z, 34 * z).coerceAtLeast(10 * z)
        when (x0.sens) {
            "arrete" -> {                                    // un habitant s'endort : le voyant s'éteint
                val on = q < 0.5f
                tl.cercle(x + 30 * z, by + bh / 2, bh / 3, if (on) EspaceDessin.VIOLET else EspaceDessin.PALE, 2 * z)
                if (on) tl.lueur(x + 30 * z, by + bh / 2, bh / 3, a(EspaceDessin.VIOLET, 90))
                tl.texte("→ 💤", x + 54 * z, by + bh / 2, 14 * z, EspaceDessin.TEXTE, false, 'g')
            }
            "change" -> {                                    // ça changerait la machine : avec un adulte
                val on = (q * 4).toInt() % 2 == 0
                tl.cercle(x + 30 * z, by + bh / 2, bh / 3, if (on) EspaceDessin.ORANGE else EspaceDessin.PALE, 2 * z)
                if (on) tl.lueur(x + 30 * z, by + bh / 2, bh / 3, a(EspaceDessin.ORANGE, 110))
                tl.texte("⚠ 🧑", x + 54 * z, by + bh / 2, 14 * z, EspaceDessin.TEXTE, false, 'g')
            }
            else -> {                                        // on lit : une jauge qui respire
                val p = 0.5f + 0.4f * sin(q * 6.2832f)
                tl.rrect(x + 16 * z, by + bh * 0.25f, w - 32 * z, bh * 0.5f, 5 * z, a(EspaceDessin.PALE, 90), a(c, 160), 1 * z)
                tl.rrect(x + 16 * z, by + bh * 0.25f, (w - 32 * z) * p, bh * 0.5f, 5 * z, a(c, 210), null, 0f)
            }
        }
    }

    /** Les jauges du vaisseau : (nom, pourcentage) en barres horizontales. */
    fun jauges(tl: Toile, valeurs: List<Pair<String, Int>>, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.CYAN, 10), a(EspaceDessin.CYAN, 100), 1.2f * z)
        if (valeurs.isEmpty()) return
        val lh = (h - 16 * z) / valeurs.size
        for ((k, v) in valeurs.withIndex()) {
            val yy = y + 8 * z + k * lh
            val col = if (v.second >= 90) EspaceDessin.ROUGE else EspaceDessin.VERT
            tl.texte(v.first, x + 12 * z, yy + lh / 2, 11 * z, EspaceDessin.DOUX, false, 'g')
            val bx = x + w * 0.38f; val bw = w * 0.5f
            tl.rrect(bx, yy + lh * 0.25f, bw, lh * 0.5f, 4 * z, a(EspaceDessin.PALE, 90), null, 0f)
            tl.rrect(bx, yy + lh * 0.25f, bw * v.second.coerceIn(0, 100) / 100f, lh * 0.5f, 4 * z, a(col, 220), null, 0f)
            tl.texte("${v.second} %", x + w - 10 * z, yy + lh / 2, 10 * z, EspaceDessin.TEXTE, true, 'd', true)
        }
    }

    /** Le REPLI de l'illustration de l'entrée : le pupitre rond du Poste (jauges, voyants, réveil, habitants). */
    fun poste(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF0E1620.toInt(), a(EspaceDessin.CYAN, 120), 1.2f * z)
        // le pupitre
        tl.rrect(x + w * 0.08f, y + h * 0.55f, w * 0.84f, h * 0.35f, 10 * z, 0xFF1B2733.toInt(), a(EspaceDessin.BLEU, 140), 1 * z)
        // trois jauges rondes dont l'aiguille respire
        for (k in 0 until 3) {
            val cx = x + w * (0.22f + 0.18f * k); val cy = y + h * 0.36f; val r = minOf(w, h) * 0.1f
            tl.cercle(cx, cy, r, listOf(EspaceDessin.VERT, EspaceDessin.JAUNE, EspaceDessin.ROUGE)[k], 2 * z)
            val an = (0.6 + 0.25 * sin((q + k * 0.3f) * 6.2832f)) * Math.PI * 2
            tl.ligne(cx, cy, cx + (r * 0.8f * kotlin.math.cos(an)).toFloat(), cy + (r * 0.8f * sin(an)).toFloat(), EspaceDessin.TEXTE, 1.6f * z)
        }
        // les voyants qui clignotent tour à tour
        for (k in 0 until 5) {
            val on = ((q * 5).toInt() % 5) == k
            val vx = x + w * (0.18f + 0.14f * k); val vy = y + h * 0.7f
            tl.cercle(vx, vy, 5 * z, if (on) EspaceDessin.VERT else EspaceDessin.PALE, 2 * z)
            if (on) tl.lueur(vx, vy, 6 * z, a(EspaceDessin.VERT, 100))
        }
        // le réveil (cron) et deux habitants (l'un travaille, l'autre dort)
        tl.texte("⏰", x + w * 0.82f, y + h * 0.33f, 18 * z, EspaceDessin.TEXTE, false, 'c')
        tl.texte(if (q < 0.5f) "🏃" else "🚶", x + w * 0.2f, y + h * 0.8f, 13 * z, EspaceDessin.TEXTE, false, 'c')
        tl.texte("😴", x + w * 0.8f, y + h * 0.8f, 13 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
