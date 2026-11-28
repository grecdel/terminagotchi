package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Le dessin de la Forge (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant les
 * illustrations (§ 7.15) :
 *  - forge : l'objet de la vue déployée — le parchemin de la recette qui s'enflamme de gauche à droite (sh cabane.sh),
 *    le manège qui tourne (for, while), l'aiguillage (if), le serpent mécanique (python3), la lanterne (http.server),
 *    la presse à images (magick), les ciseaux à sons, le diapason, la loupe à secrets (exiftool) ;
 *  - village : les 10 cabanes numérotées que la boucle fait pousser une à une ;
 *  - atelier : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (l'enclume, le feu, les parchemins qui brillent).
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object ForgeDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val SYMBOLES = mapOf("parchemin" to "📜", "lanterne" to "🏮", "serpent" to "🐍", "manege" to "🎠", "aiguillage" to "🔀",
        "presse" to "🖼", "ciseaux_sons" to "✂", "diapason" to "🎵", "loupe" to "🔍")
    val COULEURS = mapOf("parchemin" to EspaceDessin.ORANGE, "lanterne" to EspaceDessin.JAUNE, "serpent" to EspaceDessin.VERT,
        "manege" to EspaceDessin.ROSE, "aiguillage" to EspaceDessin.CYAN, "presse" to EspaceDessin.VIOLET,
        "ciseaux_sons" to EspaceDessin.ROUGE, "diapason" to EspaceDessin.BLEU, "loupe" to EspaceDessin.JAUNE)

    fun forge(tl: Toile, x0: Deploie.ForgeD, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[x0.objet] ?: EspaceDessin.ORANGE
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val serre = h < 80 * z
        val r = if (serre) minOf(17 * z, (h - 26 * z) / 2.2f).coerceAtLeast(6 * z) else 17 * z
        val ty = if (serre) y + 22 * z + (h - 22 * z) / 2 - 4 * z else y + h * 0.52f
        val cx = x + w / 2
        when (x0.objet) {
            "parchemin" -> {                                   // la recette brûle de gauche à droite, les commandes s'envolent
                val gx = x + 18 * z; val gw = w - 36 * z
                val front = gx + (q * gw).toFloat()
                tl.rrect(gx, ty - r * 0.5f, gw, r * 1.1f, 4 * z, a(EspaceDessin.JAUNE, 40), a(EspaceDessin.ORANGE, 160), 1.2f * z)
                tl.rrect(front, ty - r * 0.5f, gx + gw - front, r * 1.1f, 4 * z, a(0xFFF3E2B8.toInt(), 230), null, 0f)
                for (k in 0 until 4) tl.ligne(front + 4 * z, ty - r * 0.25f + k * r * 0.22f, gx + gw - 6 * z, ty - r * 0.25f + k * r * 0.22f, a(0xFF7A5A30.toInt(), 160), 1 * z)
                for (k in 0 until 6) {
                    val u = ((k / 6.0 + q * 2) % 1.0).toFloat()
                    tl.cercle(front - 6 * z - k * 9 * z, ty - r * 0.6f - u * r, 1.6f * z, a(EspaceDessin.JAUNE, (255 * (1 - u)).toInt()), 1.4f * z)
                }
                tl.lueur(front, ty, r * 0.8f, a(EspaceDessin.ORANGE, 120))
                tl.texte("🔥", front, ty, r * 0.9f, EspaceDessin.TEXTE, false, 'c')
            }
            "manege" -> {                                      // le manège : des tours, un repère par tour
                tl.cercle(cx, ty + 2 * z, r, c, 2.4f * z)
                for (k in 0 until 6) {
                    val an = q * 2 * PI + k * PI / 3
                    tl.cercle(cx + (r * cos(an)).toFloat(), ty + 2 * z + (r * sin(an)).toFloat(), 2.6f * z, a(c, 230), 2 * z)
                }
                tl.texte("🎠", cx, ty + 2 * z, r * 0.8f, EspaceDessin.TEXTE, false, 'c')
            }
            else -> {                                          // l'objet transforme ce qui passe (▣ → ◆)
                tl.ligne(x + 16 * z, ty + r * 0.7f, x + w - 16 * z, ty + r * 0.7f, a(EspaceDessin.PALE, 120), 2 * z)
                for (k in 0 until 5) {
                    val u = ((k / 5.0 + q) % 1.0).toFloat()
                    val px = x + 18 * z + u * (w - 36 * z)
                    if (px < cx - r - 1 * z) tl.rrect(px - 6 * z, ty - 2 * z, 12 * z, 10 * z, 2 * z, a(EspaceDessin.PALE, 210), null, 0f)
                    else if (px > cx + r + 1 * z) tl.rrect(px - 5 * z, ty, 10 * z, 8 * z, 5 * z, a(c, 230), null, 0f)
                }
                tl.cercle(cx, ty + 2 * z, r, c, 2.4f * z)
                tl.lueur(cx, ty + 2 * z, r * 0.7f, a(c, 70))
                tl.texte(SYMBOLES[x0.objet] ?: "🔨", cx, ty + 2 * z, r * 0.82f, EspaceDessin.TEXTE, false, 'c')
            }
        }
        val titre = x0.outil + " · " + t("fo.objet.${x0.objet}")
        if (serre) {
            tl.texte(titre, x + 14 * z, y + 12 * z, 10.5f * z, c, true, 'g', true)
            val dv = t("fo.mot.${x0.de}") + " → " + t("fo.mot.${x0.vers}")
            if (tl.mesure(titre, 10.5f * z, true, true) + tl.mesure(dv, 9.5f * z, false, false) + 40 * z < w)
                tl.texte(dv, x + w - 14 * z, y + 12 * z, 9.5f * z, a(c, 230), false, 'd')
            return
        }
        tl.texte(titre, cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        tl.texte(t("fo.mot.${x0.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("fo.mot.${x0.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }

    /** Le village : 10 cabanes numérotées qui poussent une à une (la boucle for, un tour par cabane). */
    fun village(tl: Toile, n: Int, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, 0xFF1A1410.toInt(), a(EspaceDessin.ORANGE, 120), 1.2f * z)
        tl.rect(x + 2 * z, y + h * 0.72f, w - 4 * z, h * 0.28f - 2 * z, 0xFF3A2A1C.toInt())
        val vus = minOf(n, (p01(phase) * (n + 2)).toInt())
        val cw = (w - 24 * z) / maxOf(1, n)
        for (k in 0 until n) {
            val bx = x + 12 * z + k * cw + cw * 0.1f
            val bw = cw * 0.8f
            val by = y + h * 0.72f
            val pousse = k < vus
            val col = if (pousse) EspaceDessin.ORANGE else EspaceDessin.PALE
            tl.rect(bx, by - bw * 0.7f, bw, bw * 0.7f, a(col, if (pousse) 230 else 60))
            tl.ligne(bx - 2 * z, by - bw * 0.7f, bx + bw / 2, by - bw * 1.2f, a(EspaceDessin.ROUGE, if (pousse) 240 else 60), 2 * z)
            tl.ligne(bx + bw / 2, by - bw * 1.2f, bx + bw + 2 * z, by - bw * 0.7f, a(EspaceDessin.ROUGE, if (pousse) 240 else 60), 2 * z)
            tl.texte("${k + 1}", bx + bw / 2, by + 9 * z, 9 * z, if (pousse) EspaceDessin.TEXTE else EspaceDessin.PALE, true, 'c', true)
        }
        tl.texte("for i in \$(seq 1 $n)", x + 14 * z, y + 14 * z, 11 * z, EspaceDessin.JAUNE, true, 'g', true)
    }

    /** Le REPLI de l'illustration de l'entrée : l'enclume, le feu qui danse, les parchemins de code qui brillent. */
    fun atelier(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF1A1410.toInt(), a(EspaceDessin.ORANGE, 120), 1.2f * z)
        tl.rect(x + 2 * z, y + h * 0.74f, w - 4 * z, h * 0.26f - 2 * z, 0xFF3A2A1C.toInt())
        // le feu de la forge, qui danse
        val fx = x + w * 0.2f; val fy = y + h * 0.7f
        tl.lueur(fx, fy - 10 * z, 30 * z, a(EspaceDessin.ORANGE, 110))
        for (k in 0 until 5) {
            val hh = (18 + 10 * sin(q * 6.28f * 2 + k)) * z
            tl.ligne(fx - 12 * z + k * 6 * z, fy, fx - 12 * z + k * 6 * z, fy - hh, a(if (k % 2 == 0) EspaceDessin.ORANGE else EspaceDessin.JAUNE, 230), 4 * z)
        }
        // l'enclume
        val ex = x + w * 0.5f; val ey = y + h * 0.74f
        tl.rect(ex - 30 * z, ey - 22 * z, 60 * z, 10 * z, 0xFF6A6F78.toInt())
        tl.rect(ex - 12 * z, ey - 12 * z, 24 * z, 12 * z, 0xFF4A4F58.toInt())
        tl.rect(ex - 20 * z, ey - 2 * z, 40 * z, 4 * z, 0xFF4A4F58.toInt())
        // le marteau qui frappe, des étincelles
        val up = (sin(q * 6.28f * 3) * 0.5f + 0.5f)
        tl.ligne(ex + 4 * z, ey - 26 * z - up * 16 * z, ex + 24 * z, ey - 40 * z - up * 16 * z, 0xFF8A5A30.toInt(), 3 * z)
        tl.rect(ex - 2 * z, ey - 32 * z - up * 16 * z, 12 * z, 8 * z, 0xFF8D929A.toInt())
        if (up < 0.2f) for (k in 0 until 5) tl.cercle(ex + (k - 2) * 7 * z, ey - 28 * z - k % 2 * 5 * z, 1.4f * z, EspaceDessin.JAUNE, 1.4f * z)
        // les parchemins de code qui brillent au mur
        for (k in 0 until 3) {
            val px = x + w * 0.66f + k * 30 * z; val py = y + h * 0.2f + (k % 2) * 8 * z
            tl.rrect(px, py, 22 * z, 30 * z, 3 * z, a(0xFFF3E2B8.toInt(), 220), a(EspaceDessin.JAUNE, 160 + (60 * sin(q * 6.28f + k)).toInt()), 1.2f * z)
            for (j in 0 until 4) tl.ligne(px + 4 * z, py + 7 * z + j * 6 * z, px + 18 * z - (j % 2) * 5 * z, py + 7 * z + j * 6 * z, a(0xFF7A5A30.toInt(), 200), 1 * z)
        }
        tl.texte("🔨", x + w * 0.1f, y + h * 0.16f, 16 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
