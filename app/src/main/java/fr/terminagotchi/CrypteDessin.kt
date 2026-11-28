package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Le dessin de la Crypte des Codes (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM) :
 *  - roue : la roue de César d'un `tr 'a-z' 'd-za-c'` dans la vue déployée — deux anneaux de lettres, l'anneau intérieur
 *    tourne jusqu'au décalage (animation E10 du § 7.15, en attendant l'illustration) ;
 *  - chaine : la chaîne de blocs ; un maillon cassé devient rouge et la cassure se propage maillon par maillon (E11) ;
 *  - peintures : le mélange des peintures (Diffie-Hellman) avec les vrais petits nombres du jeu ;
 *  - mine : la table du mineur (barres qui explosent ×16 à chaque zéro) ;
 *  - crypte : l'AFFICHAGE DE REPLI de l'illustration B12 (l'escalier sous la Racine, les coffres, la chaîne, le
 *    sphinx de givre), dessiné avec des formes simples (aucune image).
 */
object CrypteDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)

    /** La roue de César : à phase 0, les deux anneaux alignés ; elle tourne lettre par lettre jusqu'au décalage k. */
    fun roue(tl: Toile, k: Int, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val p = ((phase % 1.0) + 1.0) % 1.0
        val tour = if (p >= 0.6) k.toDouble() else k * p / 0.6
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VIOLET, 12), a(EspaceDessin.VIOLET, 90), 1.2f * z)
        val r = min(w * 0.30f, (h - 30 * z) / 2.1f).coerceAtLeast(20 * z)
        val cx = x + r + 24 * z
        val cy = y + 14 * z + r + 4 * z
        tl.cercle(cx, cy, r, a(EspaceDessin.CYAN, 160), 1.6f * z)
        tl.cercle(cx, cy, r * 0.70f, a(EspaceDessin.VIOLET, 180), 1.6f * z)
        tl.cercle(cx, cy, r * 0.42f, a(EspaceDessin.DOUX, 90), 1f * z)
        val taille = (r * 0.17f).coerceIn(6 * z, 13 * z)
        val petite = r < 34 * z                  // roue minuscule (vue déployée du téléphone) : seulement le « a » et sa sœur
        for (i in 0 until 26) {
            if (petite && i != 0) continue
            val ang = -PI / 2 + 2 * PI * i / 26
            tl.texte(Crypte.ALPHA[i].toString(), cx + (r * 0.86f * cos(ang)).toFloat(), cy + (r * 0.86f * sin(ang)).toFloat(), taille,
                if (i == 0) EspaceDessin.JAUNE else EspaceDessin.TEXTE, i == 0, 'c', true)
            val angI = ang - 2 * PI * tour / 26
            val lettre = Crypte.ALPHA[i]
            tl.texte(lettre.toString(), cx + (r * 0.56f * cos(angI)).toFloat(), cy + (r * 0.56f * sin(angI)).toFloat(), taille * 0.9f,
                if (i == 0) EspaceDessin.JAUNE else EspaceDessin.VIOLET, i == 0, 'c', true)
        }
        tl.ligne(cx, cy - r * 1.02f, cx, cy - r * 0.42f, a(EspaceDessin.JAUNE, 200), 1.6f * z)
        tl.texte("+${Math.round(tour)}", cx, cy, 13 * z, EspaceDessin.JAUNE, true, 'c', true)
        // à droite : l'alphabet clair et l'alphabet codé, et l'exemple « bonjour »
        val tx = cx + r + 18 * z
        val tw = x + w - tx - 10 * z
        val kk = Math.round(tour).toInt()
        if (tw > 200 * z) {                      // écran large : les deux alphabets côte à côte, puis l'exemple
            val pas = tw / 26
            val tt = min(12 * z, pas * 1.25f)
            val bas = h >= 108 * z                 // assez de hauteur pour l'exemple sous les alphabets ?
            val y1 = if (bas) y + 30 * z else y + h / 2 - 9 * z
            for (i in 0 until 26) {
                tl.texte(Crypte.ALPHA[i].toString(), tx + pas * (i + 0.5f), y1, tt, EspaceDessin.TEXTE, false, 'c', true)
                tl.texte(Crypte.cesar(Crypte.ALPHA[i].toString(), kk), tx + pas * (i + 0.5f), y1 + 18 * z, tt, EspaceDessin.VIOLET, true, 'c', true)
            }
            if (bas) {
                tl.texte("bonjour → " + Crypte.cesar("bonjour", kk), tx, y + 76 * z, 13 * z, EspaceDessin.TEXTE, true, 'g', true)
                tl.texte("(a + $kk) mod 26", tx, y + 96 * z, 11.5f * z, EspaceDessin.DOUX, false, 'g', true)
            }
        } else if (tw > 60 * z) {                // téléphone : l'exemple sur trois lignes, à la taille de la place
            val tt = min(13 * z, 13 * z * tw / tl.mesure("(a + 25) mod 26", 13 * z, false, true).coerceAtLeast(1f))
            val y0 = cy - 2.2f * tt
            tl.texte("bonjour", tx, y0, tt, EspaceDessin.TEXTE, true, 'g', true)
            tl.texte("→ " + Crypte.cesar("bonjour", kk), tx, y0 + 1.6f * tt, tt, EspaceDessin.VIOLET, true, 'g', true)
            tl.texte("(a + $kk) mod 26", tx, y0 + 3.4f * tt, tt * 0.9f, EspaceDessin.DOUX, false, 'g', true)
        }
    }

    /** La chaîne de blocs (états de Crypte.verifierChaine) ; la cassure se propage avec la phase, maillon par maillon. */
    fun chaine(tl: Toile, etats: List<Pair<Int, String>>, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val n = etats.size + 1
        tl.rrect(x, y, w, h, 14 * z, 0xFF101320.toInt(), a(EspaceDessin.CYAN, 90), 1.2f * z)
        val bw = min(64 * z, (w - 24 * z) / (n * 1.45f))
        val gap = (w - 24 * z - bw * n) / maxOf(1, n - 1)
        val by = y + h / 2 - bw * 0.45f
        val premiereCasse = etats.indexOfFirst { it.second != "ok" }
        val propage = if (premiereCasse < 0) -1 else premiereCasse + ((((phase % 1.0) + 1.0) % 1.0) * (n - premiereCasse)).toInt()
        for (k in 0 until n) {
            val bx = x + 12 * z + k * (bw + gap)
            val rouge = premiereCasse >= 0 && k > premiereCasse && k <= propage
            val c = if (rouge) EspaceDessin.ROUGE else EspaceDessin.CYAN
            if (rouge) tl.lueur(bx + bw / 2, by + bw * 0.45f, bw * 0.9f, a(EspaceDessin.ROUGE, 70))
            tl.rrect(bx, by, bw, bw * 0.9f, 8 * z, a(c, 40), a(c, 220), 1.6f * z)
            tl.texte("#$k", bx + bw / 2, by + bw * 0.28f, 12 * z, EspaceDessin.TEXTE, true, 'c', true)
            tl.texte(if (k == 0) "0000…" else "↤", bx + bw / 2, by + bw * 0.62f, 9.5f * z, EspaceDessin.DOUX, false, 'c', true)
            if (k < n - 1) {
                val e = etats[k].second
                val lx1 = bx + bw; val lx2 = bx + bw + gap; val ly = by + bw * 0.45f
                val casse = e != "ok" && k <= propage
                val col = if (e == "ok") EspaceDessin.VERT else if (casse) EspaceDessin.ROUGE else EspaceDessin.DOUX
                if (e == "casse" && casse) {
                    tl.ligne(lx1, ly, lx1 + gap * 0.35f, ly - 4 * z, col, 2.4f * z)
                    tl.ligne(lx2 - gap * 0.35f, ly + 4 * z, lx2, ly, col, 2.4f * z)
                    tl.texte("✖", (lx1 + lx2) / 2, ly, 13 * z, col, true, 'c')
                } else tl.ligne(lx1, ly, lx2, ly, col, 2.4f * z, if (e == "douteux") 4 * z else 0f, if (e == "douteux") 4 * z else 0f)
            }
        }
    }

    /** Le mélange des peintures : la peinture commune, les deux secrets, les mélanges publics, la couleur commune. */
    fun peintures(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val p = Crypte.peintures()
        val q = ((phase % 1.0) + 1.0) % 1.0
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.JAUNE, 10), a(EspaceDessin.JAUNE, 90), 1.2f * z)
        val r = min(w / 14, h / 7)
        fun pot(cx: Float, cy: Float, c: Int, txt: String, sous: String) {
            tl.ellipse(cx, cy, r, r * 0.8f, c)
            tl.texte(txt, cx, cy, 12 * z, 0xFF0A0C11.toInt(), true, 'c', true)
            tl.texte(sous, cx, cy + r + 12 * z, 10.5f * z, EspaceDessin.DOUX, false, 'c')
        }
        val jaune = 0xFFFFD54F.toInt(); val rouge = 0xFFFF6E6E.toInt(); val bleu = 0xFF64B5F6.toInt()
        val orange = 0xFFFFA45C.toInt(); val vert = 0xFF8BD17C.toInt(); val brun = 0xFFB07A4A.toInt()
        val l1 = y + h * 0.22f; val l2 = y + h * 0.52f; val l3 = y + h * 0.80f
        pot(x + w * 0.5f, l1, jaune, "g=${p["g"]}", "p=${p["p"]}")
        pot(x + w * 0.15f, l1, rouge, "a=${p["a"]}", "🔒")
        pot(x + w * 0.85f, l1, bleu, "b=${p["b"]}", "🔒")
        if (q > 0.25) { pot(x + w * 0.3f, l2, orange, "A=${p["A"]}", "→"); pot(x + w * 0.7f, l2, vert, "B=${p["B"]}", "←") }
        if (q > 0.55) {
            val dx = (w * 0.4f * minOf(1.0, (q - 0.55) / 0.25)).toFloat()
            tl.ligne(x + w * 0.3f, l2 + r, x + w * 0.3f + dx, l3 - r, a(vert, 160), 1.4f * z, 4 * z, 4 * z)
            tl.ligne(x + w * 0.7f, l2 + r, x + w * 0.7f - dx, l3 - r, a(orange, 160), 1.4f * z, 4 * z, 4 * z)
        }
        if (q > 0.8) { pot(x + w * 0.3f, l3, brun, "${p["s1"]}", ""); pot(x + w * 0.7f, l3, brun, "${p["s2"]}", "") }
    }

    /** La table du mineur : une barre par nombre de zéros, chacune 16 fois plus longue (échelle logarithmique). */
    fun mine(tl: Toile, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.ORANGE, 12), a(EspaceDessin.ORANGE, 90), 1.2f * z)
        val lh = (h - 20 * z) / 5
        for (d in 1..5) {
            val ly = y + 10 * z + (d - 1) * lh
            tl.texte("0".repeat(d), x + 12 * z, ly + lh / 2, 12 * z, EspaceDessin.TEXTE, true, 'g', true)
            val bw = (w - 150 * z) * d / 5f
            tl.rrect(x + 80 * z, ly + lh * 0.2f, bw, lh * 0.6f, 4 * z, a(EspaceDessin.ORANGE, 120 + 25 * d), null, 0f)
            tl.texte("16^$d", x + 86 * z + bw, ly + lh / 2, 11 * z, EspaceDessin.DOUX, false, 'g', true)
        }
    }

    /** Le repli de l'illustration B12 : l'escalier sous la Racine, la porte du sphinx, les coffres et la chaîne. */
    fun crypte(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rect(x, y, w, h, 0xFF0D1426.toInt())
        val pierre = 0xFF4A5468.toInt(); val sombre = 0xFF2C3446.toInt(); val givre = 0xFF9FD8F0.toInt()
        // les racines du camp au-dessus, l'escalier qui descend
        for (i in 0 until 6) tl.ligne(x + w * (0.1f + 0.16f * i), y, x + w * (0.25f + 0.1f * i), y + h * 0.16f, 0xFF5A3E2B.toInt(), 5 * z)
        for (i in 0 until 5) tl.rect(x + w * 0.42f + i * 6 * z, y + h * (0.16f + 0.05f * i), w * 0.16f - i * 12 * z, h * 0.05f, if (i % 2 == 0) pierre else sombre)
        // la salle voûtée
        tl.rrect(x + w * 0.08f, y + h * 0.42f, w * 0.84f, h * 0.5f, 30 * z, sombre, pierre, 3 * z)
        tl.rrect(x + w * 0.42f, y + h * 0.50f, w * 0.16f, h * 0.42f, 40 * z, 0xFF1A2236.toInt(), givre, 2 * z)
        tl.texte("🗝", x + w * 0.5f, y + h * 0.66f, 24 * z, EspaceDessin.JAUNE, true, 'c')
        // les coffres et la chaîne
        for ((i, cx) in listOf(0.18f, 0.30f, 0.70f, 0.82f).withIndex()) {
            tl.rrect(x + w * cx - 14 * z, y + h * 0.78f, 28 * z, 20 * z, 4 * z, 0xFF6B4A2A.toInt(), 0xFFD9A441.toInt(), 1.5f * z)
            tl.texte(if (i % 2 == 0) "🔒" else "📜", x + w * cx, y + h * 0.74f, 12 * z, EspaceDessin.TEXTE, false, 'c')
        }
        for (k in 0 until 5) {
            val gx = x + w * (0.22f + 0.14f * k)
            tl.cercle(gx, y + h * 0.48f, 7 * z, a(EspaceDessin.CYAN, 200), 2 * z)
            if (k < 4) tl.ligne(gx + 7 * z, y + h * 0.48f, gx + w * 0.14f - 7 * z, y + h * 0.48f, a(EspaceDessin.CYAN, 160), 2 * z)
        }
        // les flocons du sphinx de givre
        for (k in 0 until 7) {
            val fx = x + w * (0.08f + 0.13f * k) + 4 * z * sin(phase * 6.28 + k).toFloat()
            val fy = y + h * (0.30f + 0.04f * (k % 3)) + 6 * z * sin(phase * 3.0 + k).toFloat()
            tl.texte("❄", fx, fy, 10 * z, a(givre, (140 + 100 * sin(phase * 8 + k)).toInt()), false, 'c')
        }
        tl.texte(t("hist.crypte.titre"), x + w / 2, y + h * 0.36f, 18 * z, EspaceDessin.TEXTE, true, 'c')
    }
}
