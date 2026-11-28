package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Le dessin de la Guilde des Bâtisseurs Libres (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en
 * attendant les illustrations (§ 7.15 : B13, C4, E16) :
 *  - etabli : l'établi de la vue déployée — ce qui entre (texte, image, changement…) passe sous la roue dentée de
 *    l'outil (gcc, dd, sha256sum, git commit…) et ressort transformé (programme, clé-fichier, empreinte, version) ;
 *  - libertes : les 4 libertés, quatre panneaux (utiliser, étudier, partager, améliorer) ;
 *  - piece : le porte-clé vu de dessus et de biais, ses mesures, le trou à ses coordonnées (x ; y) ;
 *  - cle : la fausse image et la fausse clé (des FICHIERS), leurs empreintes, vertes quand elles sont identiques ;
 *  - guilde : l'AFFICHAGE DE REPLI de l'illustration B13 (la maison des artisans, le grand mur de plans, l'imprimante 3D,
 *    le vieux PC qui se rallume), formes simples.
 * Aucun objet n'est posé SUR la créature (pas d'accessoire) : le porte-clé est un fichier STL dessiné à part.
 */
object GuildeDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("gcc" to EspaceDessin.ORANGE, "make" to EspaceDessin.ORANGE, "openscad" to EspaceDessin.JAUNE,
        "dd" to EspaceDessin.CYAN, "sha256sum" to EspaceDessin.VERT, "git clone" to EspaceDessin.VIOLET,
        "git diff" to EspaceDessin.VIOLET, "git commit" to EspaceDessin.VIOLET)

    /** Une roue dentée (le travail de l'outil), qui tourne avec la phase. */
    private fun roue(tl: Toile, cx: Float, cy: Float, r: Float, phase: Double, c: Int, z: Float) {
        tl.cercle(cx, cy, r, c, 2.2f * z)
        tl.cercle(cx, cy, r * 0.35f, c, 1.6f * z)
        for (k in 0 until 8) {
            val an = phase * 2 * PI + k * PI / 4
            tl.ligne(cx + (r * cos(an)).toFloat(), cy + (r * sin(an)).toFloat(), cx + ((r + 5 * z) * cos(an)).toFloat(),
                cy + ((r + 5 * z) * sin(an)).toFloat(), c, 3 * z)
        }
    }

    fun etabli(tl: Toile, et: Deploie.Etabli, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[et.outil] ?: EspaceDessin.ORANGE
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val ty = y + h * 0.48f
        // le tapis de l'établi
        tl.ligne(x + 16 * z, ty + 14 * z, x + w - 16 * z, ty + 14 * z, a(EspaceDessin.PALE, 200), 2 * z)
        for (k in 0 until 10) { val u = ((k / 10.0 + q) % 1.0).toFloat()
            tl.ligne(x + 16 * z + u * (w - 32 * z), ty + 11 * z, x + 16 * z + u * (w - 32 * z), ty + 17 * z, a(EspaceDessin.PALE, 160), 1 * z) }
        val cx = x + w / 2
        roue(tl, cx, ty - 4 * z, 13 * z, q, c, z)
        tl.texte(et.outil, cx, y + 13 * z, 11.5f * z, c, true, 'c', true)
        // l'objet qui avance : avant la roue, il a la forme de « de » ; après, celle de « vers »
        val ox = x + 22 * z + q.toFloat() * (w - 44 * z)
        val avant = ox < cx
        if (avant) tl.rrect(ox - 9 * z, ty - 8 * z, 18 * z, 20 * z, 3 * z, a(EspaceDessin.TEXTE, 230), a(EspaceDessin.PALE, 255), 1 * z)
        else tl.rrect(ox - 10 * z, ty - 6 * z, 20 * z, 18 * z, 6 * z, a(c, 230), a(c, 255), 1 * z)
        tl.texte(t("gu.etabli.${et.de}"), x + 16 * z, y + h - 9 * z, 10.5f * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("→ " + t("gu.etabli.${et.vers}"), x + w - 16 * z, y + h - 9 * z, 10.5f * z, c, true, 'd')
    }

    fun libertes(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float, allumees: Int = 4) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VERT, 10), a(EspaceDessin.VERT, 100), 1.2f * z)
        val icones = listOf("▶", "🔍", "🤝", "🔧")
        val cols = listOf(EspaceDessin.VERT, EspaceDessin.CYAN, EspaceDessin.JAUNE, EspaceDessin.ORANGE)
        val lw = (w - 50 * z) / 4
        for (k in 0..3) {
            val px = x + 10 * z + k * (lw + 10 * z)
            val on = k < allumees
            tl.rrect(px, y + 12 * z, lw, h - 24 * z, 10 * z, a(cols[k], if (on) 40 else 10), a(cols[k], if (on) 200 else 60), 1.4f * z)
            tl.texte("$k", px + lw / 2, y + 30 * z, 18 * z, a(cols[k], if (on) 255 else 90), true, 'c', true)
            tl.texte(icones[k], px + lw / 2, y + h / 2 + 4 * z, 20 * z, EspaceDessin.TEXTE, false, 'c')
            if (on) tl.lueur(px + lw / 2, y + h / 2 + 4 * z, 10 * z * (0.7f + 0.3f * sin(phase * 6.28 + k).toFloat()), a(cols[k], 90))
            tl.texte(t("gu.liberte.$k").split(" ").first(), px + lw / 2, y + h - 22 * z, 9.5f * z, EspaceDessin.TEXTE, true, 'c')
        }
    }

    /** Le porte-clé de dessus (à gauche) avec son repère et son trou, et de biais (à droite), à la bonne échelle. */
    fun piece(tl: Toile, p: Guilde.Piece, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float, trou: Boolean = true) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.JAUNE, 10), a(EspaceDessin.JAUNE, 100), 1.2f * z)
        val zone = minOf((w * 0.55f - 30 * z) / p.longueur, (h - 50 * z) / p.largeur)
        val ox = x + 24 * z; val oy = y + h - 26 * z
        // le repère (x vers la droite, y vers le haut)
        tl.ligne(ox, oy, ox + p.longueur * zone + 10 * z, oy, EspaceDessin.DOUX, 1.2f * z)
        tl.ligne(ox, oy, ox, oy - p.largeur * zone - 10 * z, EspaceDessin.DOUX, 1.2f * z)
        tl.texte("x", ox + p.longueur * zone + 14 * z, oy, 10 * z, EspaceDessin.DOUX, false, 'g')
        tl.texte("y", ox, oy - p.largeur * zone - 16 * z, 10 * z, EspaceDessin.DOUX, false, 'c')
        tl.rrect(ox, oy - p.largeur * zone, p.longueur * zone, p.largeur * zone, 4 * z, a(EspaceDessin.ORANGE, 220), a(EspaceDessin.ORANGE, 255), 1.4f * z)
        if (trou) {
            val hx = ox + p.trouX * zone; val hy = oy - p.trouY * zone
            tl.ellipse(hx, hy, p.trouD * zone / 2, p.trouD * zone / 2, EspaceDessin.FOND)
            tl.ligne(hx, hy, hx, oy, a(EspaceDessin.TEXTE, 120), 1 * z, 3 * z, 3 * z)
            tl.ligne(ox, hy, hx, hy, a(EspaceDessin.TEXTE, 120), 1 * z, 3 * z, 3 * z)
            tl.texte("(${p.trouX} ; ${p.trouY})", hx + 8 * z, hy - 9 * z, 10 * z, EspaceDessin.TEXTE, true, 'g', true)
        }
        tl.texte("${p.longueur} × ${p.largeur} × ${p.epaisseur} mm", ox, y + 14 * z, 11 * z, EspaceDessin.JAUNE, true, 'g', true)
        // de biais : la plaque en volume, qui tourne doucement
        val cx = x + w * 0.78f; val cy = y + h * 0.55f
        val an = p01(phase) * 2 * PI
        val L = minOf(w * 0.18f, 70 * z); val l = L * p.largeur / p.longueur; val e = maxOf(4 * z, L * p.epaisseur / p.longueur * 2)
        val ca = cos(an).toFloat(); val sa = sin(an).toFloat()
        fun pt(px: Float, py: Float) = floatArrayOf(cx + px * ca - py * sa, cy + (px * sa + py * ca) * 0.45f)
        val c = listOf(pt(-L / 2, -l / 2), pt(L / 2, -l / 2), pt(L / 2, l / 2), pt(-L / 2, l / 2))
        tl.poly(floatArrayOf(c[0][0], c[1][0], c[2][0], c[3][0]), floatArrayOf(c[0][1] + e, c[1][1] + e, c[2][1] + e, c[3][1] + e), a(EspaceDessin.ORANGE, 120))
        tl.poly(floatArrayOf(c[0][0], c[1][0], c[2][0], c[3][0]), floatArrayOf(c[0][1], c[1][1], c[2][1], c[3][1]), a(EspaceDessin.ORANGE, 240))
        if (trou) { val tp = pt(-L / 2 + L * p.trouX / p.longueur, l / 2 - l * p.trouY / p.largeur); tl.ellipse(tp[0], tp[1], 4 * z, 2 * z, EspaceDessin.FOND) }
    }

    /** La fausse image et la fausse clé : deux fichiers, et leurs empreintes (vertes quand elles sont pareilles). */
    fun cle(tl: Toile, copiee: Boolean, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        val c = if (copiee) EspaceDessin.VERT else EspaceDessin.CYAN
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val sha = Guilde.imageSha()
        // l'image (un disque) à gauche, la clé (un fichier) à droite
        tl.cercle(x + 40 * z, y + h * 0.42f, 20 * z, EspaceDessin.TEXTE, 2 * z)
        tl.cercle(x + 40 * z, y + h * 0.42f, 5 * z, EspaceDessin.TEXTE, 1.5f * z)
        tl.texte(Guilde.IMAGE, x + 12 * z, y + h * 0.42f + 32 * z, 9.5f * z, EspaceDessin.DOUX, false, 'g', true)
        val kx = x + w - 60 * z
        tl.rrect(kx - 18 * z, y + h * 0.42f - 12 * z, 36 * z, 24 * z, 4 * z, a(c, 60), c, 1.6f * z)
        tl.rect(kx + 18 * z, y + h * 0.42f - 6 * z, 10 * z, 12 * z, a(EspaceDessin.PALE, 255))
        tl.texte(Guilde.CLE + " (" + t("gu.etabli.fichier") + ")", x + w - 12 * z, y + h * 0.42f + 32 * z, 9.5f * z, EspaceDessin.DOUX, false, 'd', true)
        // les octets qui passent de l'une à l'autre
        if (!copiee) for (k in 0 until 6) { val u = (q + k / 6f) % 1f
            tl.texte("01"[k % 2].toString(), x + 64 * z + u * (w - 150 * z), y + h * 0.42f + (sin(u * 6.28) * 6 * z).toFloat(), 11 * z, a(c, (255 * (1 - u)).toInt()), true, 'c', true) }
        else tl.texte("=", x + w / 2, y + h * 0.42f, 22 * z, c, true, 'c')
        tl.texte(sha.take(16) + "…", x + 16 * z, y + h - 12 * z, 10 * z, EspaceDessin.VERT, false, 'g', true)
        tl.texte(if (copiee) sha.take(16) + "…" else "0".repeat(16) + "…", x + w - 16 * z, y + h - 12 * z, 10 * z, c, false, 'd', true)
    }

    /** Le REPLI de l'illustration B13 : la maison des artisans au bord de la Forge, le grand mur de plans partagés,
     *  l'imprimante 3D qui dépose sa pièce couche par couche, le vieux PC dont l'écran se rallume. */
    fun guilde(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase).toFloat()
        tl.rrect(x, y, w, h, 14 * z, 0xFF1A1410.toInt(), a(EspaceDessin.ORANGE, 120), 1.2f * z)
        // le sol et la lueur de la Forge voisine
        tl.rect(x + 2 * z, y + h * 0.8f, w - 4 * z, h * 0.2f - 2 * z, 0xFF2A2018.toInt())
        tl.lueur(x + w * 0.08f, y + h * 0.75f, 30 * z * (0.8f + 0.2f * sin(q * 6.28f)), a(EspaceDessin.ORANGE, 120))
        // la maison : un toit, une façade, une porte
        tl.poly(floatArrayOf(x + w * 0.18f, x + w * 0.5f, x + w * 0.82f), floatArrayOf(y + h * 0.32f, y + h * 0.08f, y + h * 0.32f), 0xFF7A3B2A.toInt())
        tl.rect(x + w * 0.22f, y + h * 0.32f, w * 0.56f, h * 0.48f, 0xFF5A4636.toInt())
        tl.rrect(x + w * 0.46f, y + h * 0.58f, w * 0.08f, h * 0.22f, 6 * z, 0xFF2D2219.toInt(), a(EspaceDessin.JAUNE, 120), 1 * z)
        // le grand mur de plans : des feuilles qui s'allument une à une
        for (k in 0 until 12) {
            val col = k % 6; val lig = k / 6
            val px = x + w * 0.25f + col * w * 0.035f; val py = y + h * 0.36f + lig * h * 0.1f
            val on = ((q * 12).toInt() >= k)
            tl.rect(px, py, w * 0.028f, h * 0.075f, if (on) a(EspaceDessin.CYAN, 200) else a(EspaceDessin.PALE, 160))
        }
        // l'imprimante 3D : un cadre, la buse qui va et vient, la pièce qui monte
        val ix = x + w * 0.58f; val iy = y + h * 0.36f; val iw = w * 0.16f; val ih = h * 0.38f
        tl.rrect(ix, iy, iw, ih, 4 * z, null, a(EspaceDessin.TEXTE, 200), 1.5f * z)
        val couches = (q * 6).toInt()
        for (k in 0..couches) tl.rect(ix + iw * 0.3f, iy + ih - 6 * z - k * 3 * z, iw * 0.4f, 3 * z, a(EspaceDessin.ORANGE, 230))
        val bx = ix + iw * (0.3f + 0.4f * ((sin(q * 18.85f) + 1) / 2))
        tl.rect(bx - 3 * z, iy + ih - 12 * z - couches * 3 * z, 6 * z, 6 * z, EspaceDessin.JAUNE)
        // le vieux PC : son écran se rallume
        val vx = x + w * 0.84f; val vy = y + h * 0.58f
        tl.rrect(vx - 22 * z, vy - 18 * z, 44 * z, 32 * z, 3 * z, if (q > 0.5f) a(EspaceDessin.VERT, 180) else 0xFF202020.toInt(), EspaceDessin.PALE, 2 * z)
        tl.rect(vx - 6 * z, vy + 14 * z, 12 * z, 8 * z, EspaceDessin.PALE)
        if (q > 0.5f) tl.texte("$ _", vx, vy - 2 * z, 10 * z, EspaceDessin.FOND, true, 'c', true)
        tl.texte("🛠", x + w * 0.5f, y + h * 0.22f, 16 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
