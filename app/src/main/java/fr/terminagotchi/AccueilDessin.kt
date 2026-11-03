package fr.terminagotchi

/**
 * Les écrans dessinés de l'accueil et de l'aide (idées du 3 novembre, maquettes validées) : « Qui est avec toi ? » et
 * les conseils pour l'adulte (1), la carte « Pas de panique » (6), le menu du jeu (79), et l'anneau jaune du bouton
 * choisi au clavier (69). Tout passe par le Peintre (IntroVue sur le téléphone, PNG dans le test JVM Accueil.kt).
 */
object AccueilDessin {
    private const val M = Carte.MARGE
    const val FOND = 0xFF0B0D12.toInt()
    const val CARTE = 0xFF151826.toInt()
    const val BLANC = 0xFFF0F0F5.toInt()
    const val GRIS = 0xFFC8C9D4.toInt()
    const val DOUX = 0xFF8A8CA0.toInt()
    const val JAUNE = 0xFFFFD75F.toInt()
    const val VERT = 0xFF5FD787.toInt()
    const val ROSE = 0xFFFF87FF.toInt()

    private fun boutonPlein(p: Peintre, s: String, x: Float, y: Float, w: Float, h: Float, action: String): Intro.Bouton {
        p.rect(x, y, w, h, 0xFF5CFF95.toInt())
        p.rect(x + 2f, y + 2f, w - 4f, h - 4f, 0xFF1D5A36.toInt())
        p.texte(s, x + w / 2 - p.mesure(s, 14f, gras = true) / 2, y + h / 2 + 5f, 14f, 0xFFEFFFF4.toInt(), gras = true)
        return Intro.Bouton(x, y, w, h, action)
    }

    private fun boutonGris(p: Peintre, s: String, x: Float, y: Float, w: Float, h: Float, action: String): Intro.Bouton {
        p.rect(x, y, w, h, 0xFF3A3D52.toInt())
        p.rect(x + 1f, y + 1f, w - 2f, h - 2f, 0xFF22253A.toInt())
        p.texte(s, x + w / 2 - p.mesure(s, 13.5f, gras = true) / 2, y + h / 2 + 5f, 13.5f, GRIS, gras = true)
        return Intro.Bouton(x, y, w, h, action)
    }

    private fun para(p: Peintre, s: String, x: Float, y0: Float, l: Float, taille: Float, couleur: Int, inter: Float,
                     dessin: Boolean, gras: Boolean = false): Float {
        var y = y0
        for (x0 in Intro.couper(p, s, l, taille, gras)) {
            if (dessin) { if (gras) p.texte(Vert.sansMarques(x0), x, y + taille, taille, couleur, gras = true) else Carte.texteVert(p, x0, x, y + taille, taille, couleur) }
            y += inter
        }
        return y
    }

    /** L'anneau jaune autour du bouton choisi au clavier (idée 69). */
    fun anneau(p: Peintre, r: Intro.Rendu, focus: Int) {
        val b = r.boutons.getOrNull(focus) ?: return
        val e = 3f
        p.rect(b.x - e - 2f, b.y - e - 2f, b.w + 2 * e + 4f, e, JAUNE)
        p.rect(b.x - e - 2f, b.y + b.h + 2f, b.w + 2 * e + 4f, e, JAUNE)
        p.rect(b.x - e - 2f, b.y - 2f, e, b.h + 4f, JAUNE)
        p.rect(b.x + b.w + 2f, b.y - 2f, e, b.h + 4f, JAUNE)
    }

    // ---------------------------------------------------------------- 1. qui est avec toi ?
    /** page 1 : « Qui est avec toi ? » (seul / adulte) ; page 2 : les 4 conseils pour l'adulte (C'est parti ▶). */
    fun parent(p: Peintre, page: Int, l: Float, clavier: Boolean = false): Intro.Rendu {
        val lt = l - 2 * M - 16f
        fun dessiner(d: Boolean, hTot: Float): Pair<Float, List<Intro.Bouton>> {
            val bs = mutableListOf<Intro.Bouton>()
            if (d) { p.rect(0f, 0f, l, hTot, FOND); p.rect(M, M, l - 2 * M, hTot - 2 * M, CARTE) }
            var y = M + 14f
            val x = M + 8f
            if (page <= 1) {
                y = para(p, t("ad.parent.question"), x, y, lt, 19f, BLANC, 26f, d, gras = true) + 6f
                y = para(p, t("ad.parent.intro"), x, y, lt, 13.5f, GRIS, 19f, d) + 14f
                if (d) bs.add(boutonPlein(p, "🧒  " + t("ad.parent.seul"), x, y, lt, 44f, "seul"))
                y += 56f
                if (d) bs.add(boutonGris(p, "🤝  " + t("ad.parent.adulte"), x, y, lt, 44f, "adulte"))
                y += 56f
                y = para(p, t("ad.parent.note"), x, y, lt, 11.5f, DOUX, 16f, d) + 4f
            } else {
                y = para(p, "🤝  " + t("ad.parent.titre_conseils"), x, y, lt, 17f, JAUNE, 23f, d, gras = true) + 8f
                for (n in 1..4) {
                    y = para(p, "▸ " + t("ad.parent.c$n.t"), x, y, lt, 14f, VERT, 19f, d, gras = true) + 2f
                    y = para(p, t("ad.parent.c$n"), x + 14f, y, lt - 14f, 12.5f, GRIS, 17f, d) + 8f
                }
                y = para(p, t("ad.parent.relire.tel"), x, y, lt, 11.5f, DOUX, 16f, d) + 10f
                if (d) bs.add(boutonPlein(p, t("ad.parent.go"), x, y, lt, 42f, "parti"))
                y += 50f
            }
            if (clavier) y = para(p, "⌨ " + t("ad.k.aide"), x, y, lt, 11.5f, JAUNE, 16f, d) + 4f
            return y + M to bs
        }
        val h = dessiner(false, 0f).first
        val bs = dessiner(true, h).second
        return Intro.Rendu(l, h, bs)
    }

    // ---------------------------------------------------------------- 6. pas de panique
    /** La carte « Pas de panique, on regarde ensemble » : où es-tu, ta leçon, quoi taper ; deux boutons. */
    fun perdu(p: Peintre, infos: Triple<String, String, String>, l: Float): Intro.Rendu {
        val lt = l - 2 * M - 50f
        fun dessiner(d: Boolean, hTot: Float): Pair<Float, List<Intro.Bouton>> {
            val bs = mutableListOf<Intro.Bouton>()
            if (d) { p.rect(0f, 0f, l, hTot, FOND); p.rect(0f, 0f, l, 3f, JAUNE) }
            var y = 14f
            y = para(p, "🧭 " + t("ad.perdu.titre"), M + 4f, y, l - 2 * M, 16f, BLANC, 22f, d, gras = true) + 10f
            val lignes = listOf(Triple(t("ad.perdu.ou"), infos.first, 0xFFD7D7FF.toInt()),
                Triple(t("ad.perdu.lecon_titre"), infos.second, ROSE), Triple(t("ad.perdu.tape"), infos.third, VERT))
            for ((k, ligne) in lignes.withIndex()) {
                if (ligne.second.isEmpty()) continue
                if (d) {
                    p.rect(M + 4f, y + 1f, 22f, 22f, 0xFF2B4D38.toInt())
                    p.texte("${k + 1}", M + 11f, y + 17f, 13f, VERT, gras = true)
                }
                y = para(p, ligne.first, M + 36f, y, lt, 13.5f, BLANC, 18f, d, gras = true) + 1f
                y = para(p, ligne.second, M + 36f, y, lt, 13f, ligne.third, 18f, d) + 10f
            }
            if (d) bs.add(boutonGris(p, "🏕  " + t("ad.perdu.camp"), M, y, l - 2 * M, 40f, "camp"))
            y += 48f
            if (d) bs.add(boutonPlein(p, t("ad.perdu.ok"), M, y, l - 2 * M, 40f, "ok"))
            y += 50f
            y = para(p, t("ad.perdu.rien.tel"), M, y, l - 2 * M, 11.5f, DOUX, 16f, d) + 8f
            return y to bs
        }
        val h = dessiner(false, 0f).first
        return Intro.Rendu(l, h, dessiner(true, h).second)
    }

    // ---------------------------------------------------------------- 79. le menu du jeu
    private val LETTRES = mapOf(
        'T' to listOf("#####", "..#..", "..#..", "..#..", "..#.."), 'E' to listOf("#####", "#....", "####.", "#....", "#####"),
        'R' to listOf("####.", "#...#", "####.", "#..#.", "#...#"), 'M' to listOf("#...#", "##.##", "#.#.#", "#...#", "#...#"),
        'I' to listOf("#####", "..#..", "..#..", "..#..", "#####"), 'N' to listOf("#...#", "##..#", "#.#.#", "#..##", "#...#"),
        'A' to listOf(".###.", "#...#", "#####", "#...#", "#...#"), 'G' to listOf(".####", "#....", "#.###", "#...#", ".###."),
        'O' to listOf(".###.", "#...#", "#...#", "#...#", ".###."), 'C' to listOf(".####", "#....", "#....", "#....", ".####"),
        'H' to listOf("#...#", "#...#", "#####", "#...#", "#...#"))

    private fun titrePixel(p: Peintre, mot: String, x: Float, y: Float, px: Float, coul: Int) {
        for ((dx, c) in listOf(px / 2 to 0xFF0F3A22.toInt(), 0f to coul)) {
            var cx = x
            for (ch in mot) {
                val rows = LETTRES[ch] ?: continue
                for ((j, r) in rows.withIndex()) for ((i, v) in r.withIndex())
                    if (v == '#') p.rect(cx + i * px + dx, y + j * px + dx, px, px, c)
                cx += 6 * px
            }
        }
    }

    /** La pluie légère de pixels verts (règle C), tirée d'une graine fixe et de l'heure (elle descend doucement). */
    fun pluie(p: Peintre, l: Float, h: Float, quand: Long, n: Int = 40) {
        val r = java.util.Random(4)
        for (k in 0 until n) {
            val x = r.nextFloat() * l
            val v = 8f + r.nextFloat() * 18f
            val y = ((r.nextFloat() * h + quand / 1000f * v) % h)
            val c = if (r.nextBoolean()) 0x995CFF95.toInt() else 0x6686D45A
            p.rect(x, y, 3f, 3f, c)
            p.rect(x, y - 4f, 3f, 3f, c and 0x55FFFFFF)
        }
    }

    /** Le menu (idée 79) dans l × h : le camp en fond, la pluie, le titre en gros pixels, la créature dans son nid
     *  avec son nom et son niveau, puis Jouer, Nouvelle partie, Charger, Options, Aide, Quitter. */
    fun menu(p: Peintre, l: Float, h: Float, qui: String, compte: String, quand: Long = System.currentTimeMillis(),
             clavier: Boolean = false): Intro.Rendu {
        p.rect(0f, 0f, l, h, 0xFF07090D.toInt())
        val hHaut = minOf(h * 0.52f, l * 1.05f)
        Scenes.image("camp")?.let { img ->
            val e = maxOf(l / img.w, hHaut / img.h)
            val cw = l / e
            val ch = hHaut / e
            p.image(img, ((img.w - cw) * 0.5f).toInt(), ((img.h - ch) / 2).toInt(), cw.toInt(), ch.toInt(), 0f, 0f, l, hHaut, true)
        }
        p.rect(0f, 0f, l, hHaut, 0x8C07090D.toInt())
        for (k in 0 until 24) p.rect(0f, hHaut - 48f + k * 2f, l, 2f, ((k * 10 + 10) shl 24) or 0x07090D)
        p.rect(0f, hHaut, l, h - hHaut, 0xFF07090D.toInt())
        pluie(p, l, hHaut, quand)
        val px = minOf(7f, (l - 2 * M) / (6 * 7f))
        titrePixel(p, "TERMINA", (l - (6 * 7 - 1) * px) / 2, 26f, px, 0xFF5CFF95.toInt())
        titrePixel(p, "GOTCHI", (l - (6 * 6 - 1) * px) / 2, 26f + 7 * px, px, 0xFF86D45A.toInt())
        val hC = minOf(120f, hHaut * 0.36f)
        p.creature(l / 2, hHaut - 30f, hC)
        p.texte(qui, l / 2 - p.mesure(qui, 13f) / 2, hHaut - 8f, 13f, 0xFFD7D7E0.toInt())
        val bs = mutableListOf<Intro.Bouton>()
        val bw = minOf(l - 4 * M, 340f)
        val bx = (l - bw) / 2
        var y = hHaut + 14f
        val pas = minOf(50f, (h - y - 40f) / 6f).coerceAtLeast(38f)
        val boutons = listOf("1" to "▶  " + t("part.m.jouer"), "2" to "🥚  " + t("part.m.nouvelle").replaceFirstChar { it.uppercase() },
            "3" to "📂  " + t("part.m.charger").replaceFirstChar { it.uppercase() },
            "4" to "⚙  " + t("part.m.options"), "5" to "❓  " + t("part.m.aide_menu"), "q" to "✕  " + t("part.m.quitter"))
        for ((k, b) in boutons.withIndex()) {
            bs.add(if (k == 0) boutonPlein(p, b.second, bx, y, bw, pas - 8f, b.first) else boutonGris(p, b.second, bx, y, bw, pas - 8f, b.first))
            y += pas
        }
        val pied = if (clavier) "⌨ " + t("part.m.touches.tel") else t("part.m.horsligne", "compte" to compte)
        para(p, pied, bx, y + 2f, bw, 11.5f, DOUX, 16f, true)
        return Intro.Rendu(l, h, bs)
    }
}
