package fr.terminagotchi

/**
 * Le dessin du Sommet (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant les illustrations
 * (§ 7.15) :
 *  - cordee : le geste de la vue déployée — un grimpeur (▲) monte le long d'une corde vers le drapeau ; « relit » (bash -n,
 *    shellcheck), « éclaire » (bash -x, une lampe frontale), « cherche » (find -print0), « grimpe » (bash script.sh) ;
 *  - refuge : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (la montagne, le refuge, la cordée, le drapeau), formes simples.
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object SommetDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("relire" to EspaceDessin.VIOLET, "eclairer" to EspaceDessin.JAUNE, "chercher" to EspaceDessin.CYAN,
        "grimper" to EspaceDessin.ROUGE)
    val SYMBOLES = mapOf("relire" to "🔎", "eclairer" to "🔦", "chercher" to "🧭", "grimper" to "🧗")

    fun cordee(tl: Toile, x0: Deploie.CordeeD, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[x0.geste] ?: EspaceDessin.CYAN
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val titre = x0.outil + " · " + t("som.cordee.geste.${x0.geste}")
        tl.texte(titre, x + 14 * z, y + 12 * z, 10.5f * z, c, true, 'g', true)
        val dv = t("som.cordee.${x0.de}") + " → " + t("som.cordee.${x0.vers}")
        if (tl.mesure(titre, 10.5f * z, true, true) + tl.mesure(dv, 9.5f * z, false, false) + 40 * z < w)
            tl.texte(dv, x + w - 14 * z, y + 12 * z, 9.5f * z, a(c, 230), false, 'd')
        if (h < 40 * z) return
        // la pente et la corde : du bas à gauche vers le drapeau en haut à droite
        val bx = x + 20 * z; val by = y + h - 10 * z
        val hx = x + w - 36 * z; val hy = y + 26 * z
        tl.poly(floatArrayOf(bx - 6 * z, hx, hx + 22 * z), floatArrayOf(by, hy, by), a(EspaceDessin.PALE, 90))
        tl.ligne(bx, by, hx, hy, a(EspaceDessin.TEXTE, 150), 1.5f * z, 4 * z, 3 * z, q * 7 * z)
        for (k in 1..4) {                                      // les points d'assurage
            val u = k / 5f
            tl.cercle(bx + (hx - bx) * u, by + (hy - by) * u, 2 * z, a(c, 200), 1.2f * z)
        }
        tl.texte("🚩", hx + 6 * z, hy - 2 * z, 12 * z, EspaceDessin.TEXTE, false, 'c')
        val gx = bx + (hx - bx) * q; val gy = by + (hy - by) * q
        if (x0.geste == "eclairer") tl.lueur(gx, gy, 16 * z, a(EspaceDessin.JAUNE, 90))
        tl.texte(SYMBOLES[x0.geste] ?: "▲", gx, gy - 6 * z, 12 * z, EspaceDessin.TEXTE, false, 'c')
    }

    /** Le refuge du Sommet (repli de l'illustration de l'entrée) : trois sommets, le refuge, la cordée, le drapeau. */
    fun refuge(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rect(x, y, w, h, a(0x1B2440, 255))
        for ((k, f) in listOf(0.2f to 0.55f, 0.55f to 0.25f, 0.85f to 0.5f).withIndex()) {
            val cx = x + w * f.first; val top = y + h * f.second
            tl.poly(floatArrayOf(cx - w * 0.28f, cx, cx + w * 0.28f), floatArrayOf(y + h, top, y + h), a(if (k == 1) 0x8C96AA else 0x5C6476, 255))
            tl.poly(floatArrayOf(cx - w * 0.06f, cx, cx + w * 0.06f), floatArrayOf(top + h * 0.1f, top, top + h * 0.1f), a(EspaceDessin.TEXTE, 230))
        }
        tl.texte("🚩", x + w * 0.55f, y + h * 0.25f - 10 * z, 14 * z, EspaceDessin.TEXTE, false, 'c')
        tl.rrect(x + w * 0.12f, y + h * 0.78f, 34 * z, 20 * z, 3 * z, a(0x8D5A3B, 255), null, 0f)
        tl.texte("🗻", x + w * 0.12f + 17 * z, y + h * 0.78f + 10 * z, 11 * z, EspaceDessin.TEXTE, false, 'c')
        val gx = x + w * (0.3f + 0.22f * q); val gy = y + h * (0.85f - 0.55f * q)
        tl.texte("🧗", gx, gy, 13 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
