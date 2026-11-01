package fr.terminagotchi

import kotlin.math.min
import kotlin.math.sin

/**
 * Le dessin de la Salle des Rouages (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant
 * les illustrations (§ 7.15 : B9, E7, E8, E9) :
 *  - ordinateur : l'ordinateur ouvert ; chaque pièce interrogée (nproc, free, lsblk…) s'allume (vue déployée, capture) ;
 *  - interrupteurs : les octets d'un mot en interrupteurs (128 … 1), « é » sur deux rangées (UTF-8) ;
 *  - reveil : la machine qui se réveille étage par étage, du micrologiciel à la session ;
 *  - atelier : « Monte ta machine » — six emplacements, les pièces choisies, ce qui ne va pas en rouge, les jauges
 *    de points et de watts ;
 *  - ferme : la ferme de serveurs et la sauvegarde 3-2-1 (le bâtiment, le disque 2, la copie LOIN qui survit) ;
 *  - conteneur : le conteneur jetable qui naît d'une image, dit bonjour et disparaît (--rm) ;
 *  - salle : l'AFFICHAGE DE REPLI de l'illustration B9 (la salle des machines sous le camp), avec des formes simples.
 */
object MachinesDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("processeur" to 0xFFFF5F6D.toInt(), "memoire" to 0xFF5FD7FF.toInt(), "stockage" to 0xFFFFD54F.toInt(),
        "carte_mere" to 0xFF3DDC84.toInt(), "graphique" to 0xFFFF79C6.toInt(), "usb" to 0xFFF5F5A0.toInt(), "alimentation" to 0xFFFF9F43.toInt())

    /** L'ordinateur ouvert : le boîtier, la carte mère, le processeur et son ventilateur, les barrettes de mémoire, la
     *  carte graphique, le disque, l'alimentation, les prises USB ; les pièces allumées brillent de leur couleur. */
    fun ordinateur(tl: Toile, allumees: Collection<String>, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.ORANGE, 10), a(EspaceDessin.ORANGE, 90), 1.2f * z)
        val cw = min(w - 16 * z, h * 1.7f); val ch = cw / 1.7f
        val cx = x + (w - cw) / 2; val cy = y + (h - ch) / 2
        tl.rrect(cx, cy, cw, ch, 10 * z, 0xFF161A24.toInt(), a(EspaceDessin.PALE, 200), 2 * z)
        fun piece(p: String, px: Float, py: Float, pw: Float, ph: Float, r: Float = 4 * z) {
            val on = p in allumees
            val c = COULEURS[p] ?: EspaceDessin.DOUX
            if (on) tl.lueur(px + pw / 2, py + ph / 2, maxOf(pw, ph) * 0.7f, a(c, (60 + 40 * sin(q * 6.28)).toInt()))
            tl.rrect(px, py, pw, ph, r, if (on) a(c, 90) else 0xFF22283A.toInt(), if (on) c else a(EspaceDessin.PALE, 160), 1.4f * z)
        }
        val u = cw / 20
        piece("alimentation", cx + u * 0.6f, cy + u * 0.6f, u * 5.4f, u * 3.2f)
        piece("stockage", cx + u * 0.6f, cy + ch - u * 4.2f, u * 5.4f, u * 3.4f)
        piece("carte_mere", cx + u * 6.8f, cy + u * 0.6f, u * 12.6f, ch - u * 1.2f, 6 * z)
        piece("processeur", cx + u * 8.2f, cy + u * 2.0f, u * 3.6f, u * 3.6f)
        val ventilo = "processeur" in allumees
        tl.cercle(cx + u * 10f, cy + u * 3.8f, u * 1.3f, if (ventilo) EspaceDessin.TEXTE else EspaceDessin.PALE, 1.2f * z)
        val ang = q * 6.28 * 3
        for (k in 0 until 3) { val t2 = ang + k * 2.09
            tl.ligne(cx + u * 10f, cy + u * 3.8f, cx + u * 10f + (u * 1.2f * kotlin.math.cos(t2)).toFloat(), cy + u * 3.8f + (u * 1.2f * sin(t2)).toFloat(),
                if (ventilo) EspaceDessin.TEXTE else EspaceDessin.PALE, 1.2f * z) }
        for (k in 0 until 4) piece("memoire", cx + u * (13.4f + 1.2f * k), cy + u * 1.6f, u * 0.7f, u * 5.0f, 2 * z)
        piece("graphique", cx + u * 7.6f, cy + ch - u * 4.6f, u * 10.6f, u * 1.6f)
        for (k in 0 until 3) piece("usb", cx + u * (7.8f + 1.4f * k), cy + ch - u * 2.2f, u * 1.0f, u * 0.8f, 1.5f * z)
        // les noms des pièces allumées, sous le boîtier si la place le permet
        val noms = Machines.PIECES.filter { it in allumees }.joinToString(" · ") { t("ma.piece.$it") }
        if (noms.isNotEmpty() && h > ch + 26 * z && tl.mesure(noms, 11 * z, true) <= w - 8 * z) tl.texte(noms, x + w / 2, cy + ch + 12 * z, 11 * z, EspaceDessin.TEXTE, true, 'c')
    }

    /** Les interrupteurs d'un mot : une rangée de huit par octet (UTF-8 : « é » prend deux rangées), avec les valeurs. */
    fun interrupteurs(tl: Toile, mot: String, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val lignes = Machines.interrupteurs(mot).flatMap { (c, oct) -> oct.mapIndexed { i, b -> (if (i == 0) c else "") to b } }
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.JAUNE, 10), a(EspaceDessin.JAUNE, 90), 1.2f * z)
        val lh = min(36 * z, (h - 34 * z) / maxOf(1, lignes.size))
        val gauche = x + 34 * z
        val pas = (w - 34 * z - 70 * z) / 8
        val valeurs = listOf(128, 64, 32, 16, 8, 4, 2, 1)
        for (k in 0 until 8) tl.texte("${valeurs[k]}", gauche + pas * (k + 0.5f), y + 14 * z, 9.5f * z, EspaceDessin.DOUX, false, 'c', true)
        lignes.forEachIndexed { r, (c, b) ->
            val ly = y + 26 * z + r * lh
            tl.texte(c, x + 16 * z, ly + lh / 2, 15 * z, EspaceDessin.TEXTE, true, 'c')
            for (k in 0 until 8) {
                val on = b[k] == '1'
                val bx = gauche + pas * k + pas * 0.18f
                tl.rrect(bx, ly + lh * 0.12f, pas * 0.64f, lh * 0.76f, 5 * z, if (on) a(EspaceDessin.JAUNE, 220) else 0xFF22283A.toInt(),
                    if (on) EspaceDessin.JAUNE else a(EspaceDessin.PALE, 160), 1.2f * z)
                if (on) tl.lueur(bx + pas * 0.32f, ly + lh / 2, pas * 0.5f, a(EspaceDessin.JAUNE, 60))
            }
            tl.texte("= ${Integer.parseInt(b, 2)}", x + w - 12 * z, ly + lh / 2, 11 * z, EspaceDessin.TEXTE, false, 'd', true)
        }
    }

    /** La machine qui se réveille étage par étage : cinq étages, allumés un par un du bas (le bouton) vers le haut. */
    fun reveil(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val e = listOf("micrologiciel", "chargeur", "noyau", "init", "session")
        val q = p01(phase)
        val allumes = (q * (e.size + 1)).toInt().coerceAtMost(e.size)
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.ORANGE, 10), a(EspaceDessin.ORANGE, 90), 1.2f * z)
        val eh = (h - 24 * z) / e.size
        for (i in e.indices) {
            val ey = y + h - 12 * z - (i + 1) * eh
            val on = i < allumes
            val c = listOf(EspaceDessin.ORANGE, EspaceDessin.JAUNE, EspaceDessin.ROUGE, EspaceDessin.VERT, EspaceDessin.CYAN)[i]
            if (on) tl.lueur(x + w / 2, ey + eh / 2, w * 0.4f, a(c, 40))
            tl.rrect(x + 14 * z + i * 6 * z, ey + 3 * z, w - 28 * z - i * 12 * z, eh - 6 * z, 6 * z, if (on) a(c, 70) else 0xFF1C2130.toInt(),
                if (on) c else a(EspaceDessin.PALE, 140), 1.4f * z)
            tl.texte("${i + 1}. " + t("ma.etage.${e[i]}"), x + w / 2, ey + eh / 2, min(13 * z, eh * 0.4f),
                if (on) EspaceDessin.TEXTE else EspaceDessin.PALE, on, 'c')
        }
        tl.texte("⏻", x + 22 * z, y + h - 20 * z, 14 * z, EspaceDessin.ORANGE, true, 'c')
    }

    /** Monte ta machine : six emplacements ; la pièce choisie (ou « ? »), les problèmes en rouge, les jauges. */
    fun atelier(tl: Toile, choix: List<String>, besoin: String, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val r = Machines.montage(choix, besoin)
        val b = Machines.donnees().optJSONObject("besoins")?.optJSONObject(besoin)
        val budget = b?.optInt("budget", 99) ?: 99
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.ORANGE, 10), a(EspaceDessin.ORANGE, 90), 1.2f * z)
        tl.texte("🔧 " + t("ma.monte.titre"), x + 12 * z, y + 16 * z, 13 * z, EspaceDessin.TEXTE, true, 'g')
        val cats = Machines.CATEGORIES
        val bw = (w - 24 * z) / 3; val bh = min(54 * z, (h - 110 * z) / 2)
        cats.forEachIndexed { i, c ->
            val bx = x + 12 * z + (i % 3) * bw; val by = y + 32 * z + (i / 3) * (bh + 8 * z)
            val pc = choix.mapNotNull { Machines.piece(it) }.firstOrNull { it.first == c }?.second
            val mal = r.problemes.any { p -> (c == "processeur" || c == "carte_mere") && p == "prise" || (c == "memoire" || c == "carte_mere") && p == "memoire" ||
                c == "alimentation" && p == "alimentation" || p == "manque:$c" }
            val col = when { pc == null -> EspaceDessin.PALE; mal -> EspaceDessin.ROUGE; else -> EspaceDessin.VERT }
            tl.rrect(bx + 3 * z, by, bw - 6 * z, bh, 8 * z, a(col, 40), col, 1.4f * z)
            tl.texte(t("ma.cat.$c"), bx + bw / 2, by + bh * 0.3f, 10.5f * z, EspaceDessin.DOUX, false, 'c')
            tl.texte(pc?.optString("id") ?: "?", bx + bw / 2, by + bh * 0.68f, 16 * z, EspaceDessin.TEXTE, true, 'c', true)
        }
        val gy = y + 32 * z + 2 * (bh + 8 * z) + 6 * z
        fun jauge(lbl: String, v: Int, max: Int, yy: Float, infini: Boolean = false) {
            val gw = w - 24 * z - 160 * z
            tl.texte(lbl, x + 12 * z, yy + 7 * z, 11 * z, EspaceDessin.DOUX, false, 'g')
            tl.rrect(x + 100 * z, yy, gw, 14 * z, 7 * z, 0xFF22283A.toInt(), null, 0f)
            val f = if (max <= 0) 1f else (v.toFloat() / max).coerceIn(0f, 1f)
            tl.rrect(x + 100 * z, yy, gw * f, 14 * z, 7 * z, if (v > max) EspaceDessin.ROUGE else EspaceDessin.VERT, null, 0f)
            tl.texte("$v / ${if (infini) "∞" else max}", x + 104 * z + gw, yy + 7 * z, 10.5f * z, EspaceDessin.TEXTE, false, 'g', true)
        }
        jauge(t("ma.cat.alimentation"), r.watts, r.fournit, gy)
        jauge("★", r.points, budget, gy + 22 * z, infini = budget >= 99)
        val ok = r.problemes.isEmpty() && choix.isNotEmpty()
        if (gy + 60 * z < y + h) tl.texte(if (ok) "⚡ " + t("ma.demarre.ok") else if (choix.isEmpty()) t("ma.monte.besoin", "besoin" to t("ma.besoin.$besoin"))
            else "💥 " + t("ma.demarre.rate"), x + w / 2, gy + 54 * z, 11.5f * z, if (ok) EspaceDessin.VERT else EspaceDessin.ROUGE, true, 'c')
    }

    /** La ferme et la sauvegarde 3-2-1 : le bâtiment (le poste et le disque 2) brûle à la fin de la phase si une copie
     *  est LOIN ; elle reste allumée de l'autre côté de la colline. */
    fun ferme(tl: Toile, loin: Boolean, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rect(x, y, w, h, 0xFF0D1426.toInt())
        // le bâtiment de la ferme : des armoires de serveurs
        val bx = x + w * 0.05f; val bw = w * 0.55f; val by = y + h * 0.25f; val bh = h * 0.6f
        tl.rrect(bx, by, bw, bh, 8 * z, 0xFF1E2433.toInt(), a(EspaceDessin.PALE, 200), 2 * z)
        val feu = q > 0.6
        for (k in 0 until 4) {
            val sx = bx + 10 * z + k * (bw - 20 * z) / 4
            tl.rrect(sx, by + 12 * z, (bw - 20 * z) / 4 - 8 * z, bh - 24 * z, 4 * z, 0xFF12161F.toInt(), a(EspaceDessin.CYAN, 120), 1.2f * z)
            for (l in 0 until 5) tl.ellipse(sx + 10 * z, by + 24 * z + l * (bh - 40 * z) / 5, 2.5f * z, 2.5f * z,
                if (feu) EspaceDessin.PALE else if ((k + l + (q * 10).toInt()) % 3 == 0) EspaceDessin.VERT else EspaceDessin.CYAN)
        }
        tl.texte("💾 1   💾 2", bx + bw / 2, by - 10 * z, 12 * z, EspaceDessin.TEXTE, true, 'c')
        if (feu) for (k in 0 until 6) tl.texte("🔥", bx + bw * (0.1f + 0.16f * k), by + bh * (0.3f + 0.1f * (k % 3)), 18 * z, EspaceDessin.ORANGE, false, 'c')
        // la colline et la copie LOIN
        tl.poly(floatArrayOf(x + w * 0.6f, x + w * 0.72f, x + w * 0.84f), floatArrayOf(y + h * 0.85f, y + h * 0.45f, y + h * 0.85f), 0xFF2B4A3A.toInt())
        val lx = x + w * 0.86f; val ly = y + h * 0.55f
        tl.rrect(lx - 22 * z, ly, 44 * z, 36 * z, 6 * z, if (loin) a(EspaceDessin.VERT, 80) else 0xFF22283A.toInt(),
            if (loin) EspaceDessin.VERT else a(EspaceDessin.PALE, 160), 1.6f * z)
        tl.texte(if (loin) "💾 3" else "?", lx, ly + 18 * z, 12 * z, EspaceDessin.TEXTE, true, 'c')
        tl.texte(t("ma.panne.bilan", "copies" to (if (loin) 3 else 2), "supports" to (if (loin) 3 else 2), "loin" to t(if (loin) "ma.oui" else "ma.non")),
            x + w / 2, y + h - 10 * z, 10.5f * z, EspaceDessin.TEXTE, false, 'c')
        tl.texte(if (feu) (if (loin) "✔ " + t("ma.panne.sauvee") else "✖ " + t("ma.panne.perdu")) else "3 · 2 · 1",
            x + w / 2, y + 14 * z, 12 * z, if (!feu) EspaceDessin.JAUNE else if (loin) EspaceDessin.VERT else EspaceDessin.ROUGE, true, 'c')
    }

    /** Le conteneur jetable : il naît de l'image (phase < 1/3), dit bonjour (< 2/3), puis disparaît en étincelles. */
    fun conteneur(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.CYAN, 10), a(EspaceDessin.CYAN, 90), 1.2f * z)
        // l'image (le modèle), à gauche
        tl.rrect(x + 16 * z, y + h * 0.3f, w * 0.22f, h * 0.4f, 6 * z, a(EspaceDessin.BLEU, 60), EspaceDessin.BLEU, 1.4f * z)
        tl.texte("alpine", x + 16 * z + w * 0.11f, y + h * 0.5f, 11 * z, EspaceDessin.TEXTE, true, 'c', true)
        tl.ligne(x + 16 * z + w * 0.22f, y + h * 0.5f, x + w * 0.45f, y + h * 0.5f, a(EspaceDessin.BLEU, 160), 1.4f * z, 4 * z, 4 * z)
        val cx = x + w * 0.62f; val cy = y + h * 0.5f; val s = min(w * 0.18f, h * 0.32f)
        when {
            q < 0.33 -> { val f = (q / 0.33).toFloat()
                tl.rrect(cx - s * f, cy - s * f, 2 * s * f, 2 * s * f, 6 * z, a(EspaceDessin.CYAN, 60), EspaceDessin.CYAN, 1.6f * z)
                tl.texte(t("ma.conteneur.temps0"), x + w / 2, y + h - 14 * z, 11 * z, EspaceDessin.TEXTE, false, 'c') }
            q < 0.66 -> {
                tl.rrect(cx - s, cy - s, 2 * s, 2 * s, 6 * z, a(EspaceDessin.CYAN, 60), EspaceDessin.CYAN, 1.6f * z)
                tl.rrect(cx + s * 0.6f, cy - s * 1.6f, s * 1.6f, s * 0.7f, 8 * z, EspaceDessin.TEXTE, null, 0f)
                tl.texte("bonjour", cx + s * 1.4f, cy - s * 1.25f, 11 * z, 0xFF0A0C11.toInt(), true, 'c', true)
                tl.texte(t("ma.conteneur.temps1"), x + w / 2, y + h - 14 * z, 11 * z, EspaceDessin.TEXTE, false, 'c') }
            else -> { val f = ((q - 0.66) / 0.34).toFloat()
                for (k in 0 until 10) tl.texte("✨", cx + (k - 5) * s * 0.3f * (1 + f), cy + ((k * 37) % 11 - 5) * s * 0.12f * (1 + f), 10 * z,
                    a(EspaceDessin.JAUNE, (255 * (1 - f)).toInt()), false, 'c')
                tl.texte(t("ma.conteneur.temps2"), x + w / 2, y + h - 14 * z, 11 * z, EspaceDessin.TEXTE, false, 'c') }
        }
    }

    /** Le repli de l'illustration B9 : la salle des machines sous le camp (tuyaux, engrenages, l'ordinateur au centre). */
    fun salle(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rect(x, y, w, h, 0xFF1A1410.toInt())
        // le plafond : le sol du camp et l'échelle de la trappe
        tl.rect(x, y, w, h * 0.1f, 0xFF4A3424.toInt())
        for (k in 0 until 6) tl.ligne(x + w * 0.48f, y + h * (0.1f + 0.05f * k), x + w * 0.52f, y + h * (0.1f + 0.05f * k), 0xFF8A6A4A.toInt(), 2 * z)
        tl.ligne(x + w * 0.48f, y + h * 0.08f, x + w * 0.48f, y + h * 0.4f, 0xFF8A6A4A.toInt(), 2 * z)
        tl.ligne(x + w * 0.52f, y + h * 0.08f, x + w * 0.52f, y + h * 0.4f, 0xFF8A6A4A.toInt(), 2 * z)
        // les tuyaux et la vapeur
        for (k in 0 until 3) tl.ligne(x, y + h * (0.2f + 0.08f * k), x + w * 0.3f, y + h * (0.2f + 0.08f * k), 0xFFB87333.toInt(), 5 * z)
        tl.texte("≋", x + w * 0.31f, y + h * (0.18f - 0.03f * sin(q * 6.28).toFloat()), 18 * z, a(EspaceDessin.TEXTE, 120), false, 'c')
        // les engrenages
        for ((gx, gy, gr) in listOf(Triple(0.8f, 0.25f, 0.08f), Triple(0.9f, 0.4f, 0.05f))) {
            tl.cercle(x + w * gx, y + h * gy, w * gr, 0xFFC9A227.toInt(), 3 * z)
            for (k in 0 until 8) { val t2 = q * 6.28 + k * 0.785
                tl.ligne(x + w * gx, y + h * gy, x + w * gx + (w * gr * kotlin.math.cos(t2)).toFloat(), y + h * gy + (w * gr * sin(t2)).toFloat(), 0xFFC9A227.toInt(), 2 * z) }
        }
        // l'ordinateur ouvert au centre, toutes pièces allumées
        ordinateur(tl, Machines.PIECES, phase, x + w * 0.2f, y + h * 0.45f, w * 0.6f, h * 0.5f, z)
    }
}
