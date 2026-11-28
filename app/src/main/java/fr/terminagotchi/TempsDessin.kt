package fr.terminagotchi

import kotlin.math.sin

/**
 * Le dessin de la Bibliothèque du Temps (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant
 * les illustrations (§ 7.15) :
 *  - pellicule : la vue déployée d'une commande git — des photos défilent devant l'objectif (git add, git commit), la
 *    pellicule se déroule (git log), deux chemins se séparent ou se rejoignent (git switch -c, git merge), une copie part
 *    (git clone) ou revient (git pull), une empreinte s'imprime (git hash-object) ;
 *  - bibliotheque : l'AFFICHAGE DE REPLI de l'illustration de l'entrée (les rayonnages, la grande horloge, l'album ouvert),
 *    formes simples ;
 *  - chemins : deux chemins qui partent d'une photo et se rejoignent (la fusion), pour `temps branches`.
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object TempsDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("album" to EspaceDessin.JAUNE, "photo" to EspaceDessin.JAUNE, "pellicule" to EspaceDessin.ORANGE,
        "differences" to EspaceDessin.ROUGE, "deux_chemins" to EspaceDessin.VIOLET, "un_chemin" to EspaceDessin.VERT, "copie" to EspaceDessin.CYAN,
        "empreinte" to EspaceDessin.BLEU, "objectif" to EspaceDessin.JAUNE, "signature" to EspaceDessin.ORANGE, "etat" to EspaceDessin.CYAN,
        "fichier" to EspaceDessin.PALE)

    fun pellicule(tl: Toile, p: Deploie.PelliculeD, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[p.vers] ?: EspaceDessin.JAUNE
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val serre = h < 80 * z
        val fy = if (serre) y + 22 * z + (h - 22 * z) / 2 - 7 * z else y + h * 0.42f
        val fh = if (serre) minOf(18 * z, h - 30 * z).coerceAtLeast(10 * z) else 26 * z
        // la bande de film et ses perforations
        tl.rect(x + 14 * z, fy, w - 28 * z, fh, a(0xFF20242C.toInt(), 230))
        var px = x + 16 * z
        while (px < x + w - 18 * z) { tl.rect(px, fy + 2 * z, 3 * z, 2 * z, a(EspaceDessin.PALE, 160)); tl.rect(px, fy + fh - 4 * z, 3 * z, 2 * z, a(EspaceDessin.PALE, 160)); px += 8 * z }
        // les photos qui défilent ; au milieu, l'objectif et son flash
        val cx = x + w / 2
        for (k in 0 until 5) {
            val u = ((k / 5.0f + q) % 1f)
            val vx = x + 20 * z + u * (w - 56 * z)
            val dedans = vx > cx - 10 * z
            tl.rrect(vx, fy + 5 * z, 16 * z, fh - 10 * z, 2 * z, a(if (dedans) c else EspaceDessin.PALE, if (dedans) 230 else 150), null, 0f)
        }
        val flash = (sin(q * 12.566f) > 0.7f)
        tl.cercle(cx, fy + fh / 2, fh * 0.55f, c, 2 * z)
        if (flash) tl.lueur(cx, fy + fh / 2, fh * 0.9f, a(EspaceDessin.TEXTE, 120))
        val titre = p.outil
        val dv = t("tp.pellicule.${p.de}") + " → " + t("tp.pellicule.${p.vers}")
        if (serre) {
            tl.texte(titre, x + 14 * z, y + 12 * z, 10.5f * z, c, true, 'g', true)
            if (tl.mesure(titre, 10.5f * z, true, true) + tl.mesure(dv, 9.5f * z, false, false) + 40 * z < w)
                tl.texte(dv, x + w - 14 * z, y + 12 * z, 9.5f * z, a(c, 230), false, 'd')
            return
        }
        tl.texte("🎞 $titre", cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        tl.texte(t("tp.pellicule.${p.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("tp.pellicule.${p.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }

    /** Deux chemins partent d'une photo et se rejoignent (la fusion) ; phase : les photos apparaissent une à une. */
    fun chemins(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VIOLET, 10), a(EspaceDessin.VIOLET, 100), 1.2f * z)
        val ym = y + h * 0.62f; val yh = y + h * 0.30f
        val xs = listOf(0.12f, 0.32f, 0.52f, 0.72f, 0.9f).map { x + it * w }
        tl.ligne(xs[0], ym, xs[4], ym, EspaceDessin.JAUNE, 3 * z)
        tl.ligne(xs[0], ym, xs[1] + 10 * z, yh, EspaceDessin.VIOLET, 3 * z)
        tl.ligne(xs[1] + 10 * z, yh, xs[3] - 10 * z, yh, EspaceDessin.VIOLET, 3 * z)
        tl.ligne(xs[3] - 10 * z, yh, xs[4], ym, EspaceDessin.VIOLET, 3 * z)
        val n = (q * 6).toInt()
        val pts = listOf(xs[0] to ym, xs[2] to ym, xs[2] to yh, xs[4] to ym)
        for ((k, pt) in pts.withIndex()) if (k <= n) tl.cercle(pt.first, pt.second, 7 * z, if (pt.second == yh) EspaceDessin.VIOLET else EspaceDessin.JAUNE, 3 * z)
        tl.texte("main", x + 10 * z, ym + 18 * z, 10 * z, EspaceDessin.JAUNE, true, 'g', true)
        tl.texte("reve", xs[2], yh - 14 * z, 10 * z, EspaceDessin.VIOLET, true, 'c', true)
        tl.texte("git merge", xs[4], ym + 18 * z, 10 * z, EspaceDessin.VERT, true, 'd', true)
    }

    /** Le REPLI de l'illustration de l'entrée : les rayonnages, la grande horloge, l'album ouvert sur le pupitre. */
    fun bibliotheque(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF1A1420.toInt(), a(EspaceDessin.JAUNE, 120), 1.2f * z)
        // les rayonnages
        val couleurs = listOf(EspaceDessin.ROUGE, EspaceDessin.JAUNE, EspaceDessin.VERT, EspaceDessin.BLEU, EspaceDessin.VIOLET, EspaceDessin.ORANGE)
        for (r in 0 until 3) {
            val ry = y + h * (0.22f + 0.2f * r)
            tl.rect(x + 10 * z, ry, w * 0.36f, 3 * z, a(EspaceDessin.PALE, 120))
            tl.rect(x + w * 0.62f, ry, w * 0.36f - 10 * z, 3 * z, a(EspaceDessin.PALE, 120))
            for (k in 0 until 7) {
                val c = couleurs[(k + r) % couleurs.size]
                tl.rect(x + 14 * z + k * w * 0.048f, ry - 16 * z, w * 0.036f, 16 * z, a(c, 200))
                tl.rect(x + w * 0.64f + k * w * 0.046f, ry - 15 * z, w * 0.034f, 15 * z, a(couleurs[(k + r + 3) % couleurs.size], 200))
            }
        }
        // la grande horloge
        val cx = x + w / 2; val cy = y + h * 0.36f; val rr = minOf(w, h) * 0.16f
        tl.cercle(cx, cy, rr, EspaceDessin.JAUNE, 2.5f * z)
        tl.lueur(cx, cy, rr * 0.8f, a(EspaceDessin.JAUNE, 50))
        val an = q * 6.2832f
        tl.ligne(cx, cy, cx + rr * 0.75f * kotlin.math.cos(an - 1.57f), cy + rr * 0.75f * kotlin.math.sin(an - 1.57f), EspaceDessin.TEXTE, 2 * z)
        tl.ligne(cx, cy, cx + rr * 0.45f * kotlin.math.cos(an / 12 - 1.57f), cy + rr * 0.45f * kotlin.math.sin(an / 12 - 1.57f), EspaceDessin.TEXTE, 3 * z)
        // l'album ouvert sur le pupitre, et ses photos
        val ay = y + h * 0.74f
        tl.rrect(cx - 60 * z, ay, 120 * z, 34 * z, 4 * z, a(EspaceDessin.TEXTE, 230), EspaceDessin.JAUNE, 1.2f * z)
        tl.ligne(cx, ay, cx, ay + 34 * z, a(EspaceDessin.FOND, 200), 1 * z)
        for (k in 0 until 4) {
            val vx = cx - 54 * z + (k % 2) * 26 * z + (k / 2) * 60 * z
            tl.rect(vx, ay + 5 * z, 20 * z, 24 * z, a(if (k == (q * 4).toInt() % 4) EspaceDessin.ORANGE else EspaceDessin.PALE, 210))
        }
        tl.texte("⏳", x + w * 0.08f, y + h * 0.88f, 16 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
