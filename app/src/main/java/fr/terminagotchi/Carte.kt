package fr.terminagotchi

/**
 * Le dessin de la carte qui pousse (le modèle est dans Maison.kt) : à gauche le Terminaworld en pixel art (une tuile
 * par lieu, un objet par fichier, la brume sur ce qui n'est pas encore exploré), à droite la sortie de `tree`, ligne
 * par ligne, chaque ligne alignée sur son dessin ; dessous, où on est et les commandes déjà rencontrées (en vert).
 *
 * Sans Android : tout passe par un Peintre (rectangles, images en pixels, texte). CarteVue.kt le branche sur un
 * Canvas ; le test JVM (tests/jvm/Carte.kt) sur une image Java pour fabriquer les aperçus. Les unités sont des dp.
 * Les tuiles sont calculées (des hexagones en relief, comme les illustrations du site) et les icônes sont de petits
 * dessins de 8×8 pixels : rien à charger, et le même rendu partout.
 */
interface Peintre {
    fun rect(x: Float, y: Float, w: Float, h: Float, couleur: Int)
    fun pixels(p: Carte.Pix, x: Float, y: Float, echelle: Float)
    /** y = ligne de base du texte */
    fun texte(s: String, x: Float, y: Float, taille: Float, couleur: Int, mono: Boolean = false, gras: Boolean = false)
    fun mesure(s: String, taille: Float, mono: Boolean = false, gras: Boolean = false): Float
    /** La créature de l'enfant debout à (x centre, y pieds), haute de h ; false si elle n'est pas dessinable (épingle). */
    fun creature(x: Float, y: Float, h: Float): Boolean = false
}

object Carte {
    class Pix(val w: Int, val h: Int, val px: IntArray)

    // ---------------------------------------------------------------- couleurs (comme le site : CRT vert, 16 bits)
    const val FOND = 0xFF08100C.toInt()
    const val PANNEAU = 0xFF0F1A14.toInt()
    const val RAYURE = 0xFF0C1611.toInt()
    const val BORD = 0xFF2B4D38.toInt()
    const val BORD_VIF = 0xFF4C8C63.toInt()
    const val VERT = 0xFF5CFF95.toInt()
    const val AMBRE = 0xFFFFB84D.toInt()
    const val TEXTE = 0xFFDCF7E6.toInt()
    const val DOUX = 0xFF9CC4AA.toInt()
    const val BRUME = 0xFF5D6B62.toInt()
    const val VIOLET = 0xFFB48CFF.toInt()
    const val JAUNE = 0xFFFFE14A.toInt()
    const val BALAYAGE = 0x26000000

    // ---------------------------------------------------------------- mise en page (dp)
    const val MARGE = 10f
    const val HAUT_TITRE = 34f
    const val HAUT_LIGNE = 34f
    const val RETRAIT = 16f
    const val ECHELLE = 2f
    const val TAILLE = 11f
    const val TAILLE_TITRE = 13f

    /** (dessus, côté) de la tuile d'un lieu. */
    val SOLS_PIECES = mapOf(
        "vestibule" to (0xFFD9B47A to 0xFF7B5534), "nid" to (0xFFC9A26A to 0xFF6B4A2C), "grenier" to (0xFF5AA63A to 0xFF2F6B2C),
        "cave" to (0xFF8D929A to 0xFF5D6168), "bibliotheque" to (0xFFA8743F to 0xFF5A381E),
        "salle_des_machines" to (0xFFE8562A to 0xFF3A2A30), "dortoir" to (0xFF4B3A6B to 0xFF251C38),
        "atelier" to (0xFFC9A26A to 0xFF7D828A), "tour" to (0xFFDFE9FF to 0xFF8B9AC4), "coeur" to (0xFFFF6FA8 to 0xFF7A2A55),
        "jardin" to (0xFF66B843 to 0xFF6B4A2C)).mapValues { (_, v) -> v.first.toInt() to v.second.toInt() }
    val SOLS = mapOf("camp" to (0xFFD9B47A to 0xFF7B5534), "lieu" to (0xFF5AA63A to 0xFF6B4A2C),
        "porte" to (0xFF8FA9C2 to 0xFF3D5A73), "secret" to (0xFF4B3A6B to 0xFF251C38),
        "brume" to (0xFF6A6F78 to 0xFF3A3D44),
        // la Racine (bois), le village, ton camp de base, la zone d'aventure, les lieux du système (pierre)
        "racine" to (0xFF8A5A30 to 0xFF4A2E18), "village" to (0xFFE0C48A to 0xFF8A6A3A), "camp_base" to (0xFFD9B47A to 0xFF7B5534),
        "zone" to (0xFF86D45A to 0xFF2F6B2C), "chemin" to (0xFF9CC4AA to 0xFF4C6A58), "systeme" to (0xFFA7ACB4 to 0xFF5D6168),
    ).mapValues { (_, v) -> v.first.toInt() to v.second.toInt() }

    fun sol(n: Maison.Noeud): Pair<Int, Int> = when {
        n.brume || n.garde == "fermee" -> SOLS.getValue("brume")           // une région fermée est grise
        n.genre == "piece" -> SOLS_PIECES[n.biome] ?: SOLS.getValue("lieu")
        n.genre in SOLS && n.genre != "lieu" -> SOLS.getValue(n.genre)
        n.genre in setOf("region", "parcelle", "lieu") && n.biome in Maison.BIOMES ->
            Maison.BIOMES.getValue(n.biome!!).let { it.principale to it.sombre }
        !n.dossier -> n.parent?.let { sol(it) } ?: SOLS.getValue("lieu")
        else -> SOLS[n.genre] ?: SOLS.getValue("lieu")
    }

    // ---------------------------------------------------------------- les icônes (8×8, « . » = transparent)
    private val PALETTE = mapOf(
        'k' to 0xFF1A1A22, 'w' to 0xFFFFFFFF, 'r' to 0xFFE8562A, 'o' to 0xFFFFB347, 'y' to 0xFFFFD36B, 'Y' to 0xFFE8B830,
        'b' to 0xFF2F7FC4, 'c' to 0xFF7CC7FF, 'g' to 0xFF5AA63A, 'G' to 0xFF2F6B2C, 'l' to 0xFF86D45A, 'n' to 0xFF8A5A30,
        'N' to 0xFF4A2E18, 'p' to 0xFFD8CCF5, 'P' to 0xFF6B5A9B, 's' to 0xFFA7ACB4, 'S' to 0xFF5D6168, 'm' to 0xFF7DFFCF,
        'e' to 0xFFF1E3C0, 'E' to 0xFFC9B48A, 'R' to 0xFFFF6FA8, 'D' to 0xFFB0305A, 't' to 0xFF3DF2FF, 'v' to 0xFFB6FF4A,
        'V' to 0xFF6A8F2A, 'u' to 0xFFC04AFF, 'f' to 0xFFE6EBF0, 'F' to 0xFF9AA3AD,
    ).mapValues { it.value.toInt() }

    val ICONES: Map<String, List<String>> = mapOf(
        "feu" to listOf("...y....", "..yo....", "..ooy.o.", ".oorooo.", ".orrrro.", ".rrryrr.", "..rrrr..", "...NN..."),
        "eau" to listOf("...c....", "...c....", "..cbc...", "..cbb...", ".cbbbb..", ".cwbbb..", ".cbbbb..", "..bbb..."),
        "glace" to listOf("...w....", ".w.c.w..", "..wcw...", "wcccccw.", "..wcw...", ".w.c.w..", "...w....", "........"),
        "plante" to listOf("..lgg...", ".lggggg.", ".ggGgGg.", ".gGggGg.", "..gGGg..", "...nn...", "...nn...", "..NnnN.."),
        "roche" to listOf("........", "...ss...", "..swss..", ".sssssS.", ".ssSssS.", "sssSsSSS", "SSSSSSSS", "........"),
        "ciel" to listOf("....yy..", "...yy...", "..yy....", ".yyyyy..", "...yy...", "..yy....", ".yy.....", ".y......"),
        "ombre" to listOf("..ppp...", ".pp...m.", "pp......", "pp....m.", "pp......", ".pp...pp", "..pppppp", "...pppp."),
        "machine" to listOf("...ss...", ".s.ss.s.", "..ssss..", "ssS..Sss", "ssS..Sss", "..ssss..", ".s.ss.s.", "...ss..."),
        "poison" to listOf("...ww...", "...ss...", "...ss...", "..svvs..", ".svvvvs.", ".vvVvvv.", ".vvvvVv.", "..vvvv.."),
        "camp" to listOf("...y....", "..yoy...", "..oro...", ".orrro..", "..rrr...", ".NnNnN..", "NnNNnNn.", "........"),
        "oeuf" to listOf("........", "...ee...", "..eeee..", "..eyee..", ".eeeeye.", ".eyeeee.", ".EeeeeE.", "..EEEE.."),
        "nid" to listOf("........", "........", "..e..e..", ".eee.ee.", "NnNnNnNn", "nNnNnNnN", ".NnNnNn.", "..NNNN.."),
        "livre" to listOf("........", ".DDDDDD.", ".DeeeeD.", ".DEEEED.", ".DeeeeD.", ".DEEEED.", ".DDDDDD.", "........"),
        "fantome" to listOf("..ffff..", ".ffffff.", ".fkffkf.", ".ffffff.", ".ffffff.", ".ffffff.", ".f.ff.f.", "........"),
        "marteau" to listOf(".SSSS...", ".SSSSs..", "...n....", "...n....", "...n....", "...n....", "...N....", "........"),
        "antenne" to listOf("t......t", ".t....t.", "..t..t..", "...ss...", "...ss...", "..ssss..", "..s..s..", ".SS..SS."),
        "coeur" to listOf("........", ".RR.RR..", "RwRRRRR.", "RRRRRRR.", ".RRRRR..", "..RRR...", "...R....", "........"),
        "fleur" to listOf("..R.R...", ".RRyRR..", "..RRR...", "...g....", ".g.g.g..", "..ggg...", "...g....", "........"),
        "cadenas" to listOf("..SSS...", ".S...S..", ".S...S..", "YYYYYYY.", "YYYkYYY.", "YYYkYYY.", "YYYYYYY.", "........"),
        "portail" to listOf("tttttttt", ".s....s.", ".s.uu.s.", ".s.uu.s.", ".s.uu.s.", ".s.uu.s.", ".s....s.", "SS....SS"),
        "note" to listOf("........", ".eeeee..", ".eEEEe..", ".eeeee..", ".eEEEe..", ".eeeee..", ".eEEee..", "..eeee.."),
        "recette" to listOf("........", ".eeeeee.", ".eEeEEe.", ".eeeeee.", ".eEEeEe.", ".ee.yye.", ".eeeyye.", "........"),
        "image" to listOf("........", "kkkkkkkk", "kcccycck", "kcccccck", "kccgcgck", "kcgggggk", "kkkkkkkk", "........"),
        "coffre" to listOf("........", ".nnnnnn.", "nNNNNNNn", "nnnYYnnn", "nnnYYnnn", "nNNNNNNn", ".nnnnnn.", "........"),
        "secret" to listOf("..PPPP..", ".PkkkkP.", "PkkkkkkP", "PkkYkkkP", "PkkkkkkP", "PkkkkkkP", "PkkkkkkP", "PPPPPPPP"),
        "cle" to listOf("........", ".YYY....", "Y...Y...", "Y...YYYY", ".YYY..Y.", "......YY", "........", "........"),
        "brume" to listOf("........", "..ff....", ".ffff.f.", "ffFfffff", "fffffFf.", ".FffFff.", "..FFFF..", "........"),
        // la Racine (un arbre et ses racines), le village, la zone d'aventure (le sac), les lieux du système
        "arbre" to listOf("..gGg...", ".gGgGg..", "gGgGgGg.", ".gGgGg..", "...n....", "...n....", "..NnN...", ".N.n.N.."),
        "village" to listOf("..r..r..", ".rrrrrr.", "rrrrrrrr", ".eeeeee.", ".ekeeke.", ".eeeeee.", ".ekeeke.", "........"),
        "sac" to listOf("..nnn...", ".n...n..", ".nNNNn..", "nNnnnNn.", "nNnYnNn.", "nNnnnNn.", "nNNNNNn.", "........"),
        "outils" to listOf("..SSSS..", "..S..S..", "rrrrrrrr", "rYYrrYYr", "rrrrrrrr", "rrrrrrrr", "DDDDDDDD", "........"),
        "feuille" to listOf("......o.", "....ooo.", "..oooYo.", ".ooYoo..", ".oYoo...", ".Yoo....", "Y.......", "........"),
        "prise" to listOf("..s..s..", "..s..s..", ".ssssss.", ".SSSSSS.", "..SSSS..", "...kk...", "...kk...", "....kk.."),
        "boule" to listOf("..PPPP..", ".PpcwpP.", "PpcppppP", "PppppppP", ".PppppP.", "..PPPP..", ".NnnnnN.", "NNNNNNNN"),
        "epingle" to listOf("..RRR...", ".RRwRR..", ".RRRRR..", "..RRR...", "...k....", "...k....", "...k....", "........"),
        "etoile" to listOf("..y..", "..y..", "yywyy", "..y..", "..y.."),
        "petite_etoile" to listOf(".....", "..y..", ".ywy.", "..y..", "....."),
    )
    /** l'icône d'un lieu du Terminaworld (hors de la zone d'aventure) */
    val ICONES_LIEUX = mapOf("racine" to "arbre", "village" to "village", "camp" to "camp", "zone" to "sac", "chemin" to "plante",
        "armurerie" to "outils", "portails" to "prise", "regles" to "note", "miroir" to "boule", "vague" to "feuille",
        "archives" to "livre", "systeme" to "coffre")
    /** l'icône d'un lieu de l'histoire */
    val ICONES_PIECES = mapOf("vestibule" to "oeuf", "nid" to "nid", "grenier" to "plante", "cave" to "cadenas",
        "bibliotheque" to "livre", "salle_des_machines" to "feu", "dortoir" to "fantome", "atelier" to "marteau",
        "tour" to "antenne", "coeur" to "coeur", "jardin" to "fleur")

    private val cache = HashMap<String, Pix>()

    fun icone(nom: String): Pix = cache.getOrPut("i:$nom") {
        val l = ICONES[nom] ?: ICONES.getValue("coffre")
        val w = l.maxOf { it.length }
        Pix(w, l.size, IntArray(w * l.size) { i -> l[i / w].getOrNull(i % w)?.let { PALETTE[it] } ?: 0 })
    }

    fun nomIcone(n: Maison.Noeud): String = when {
        n.brume -> "brume"
        n.lieu != null -> ICONES_LIEUX[n.lieu!!] ?: "coffre"
        n.genre == "zone" -> "sac"
        n.genre == "piece" -> ICONES_PIECES[n.biome] ?: "plante"
        n.genre == "region" || (n.genre == "parcelle" && n.biome != null) -> n.biome ?: "plante"
        n.genre == "parcelle" -> "plante"
        n.genre == "lieu" -> n.biome ?: "plante"
        n.genre == "porte" -> "portail"
        n.genre == "camp" -> "camp"
        n.genre == "secret" -> "secret"
        n.genre == "secret_objet" -> "cle"
        else -> n.genre
    }

    private fun eclaircir(c: Int, d: Int): Int {
        fun f(v: Int) = (v + d).coerceIn(0, 255)
        return (c and 0xFF000000.toInt()) or (f(c shr 16 and 255) shl 16) or (f(c shr 8 and 255) shl 8) or f(c and 255)
    }

    /** Une tuile hexagonale en relief (16×12 pixels) : le dessus (avec un peu de grain) sur son côté. */
    fun tuile(dessus: Int, cote: Int, graine: Int, petite: Boolean = false): Pix = cache.getOrPut("t:$dessus:$cote:${graine and 7}:$petite") {
        val w = 16; val haut = if (petite) 6 else 8; val mur = if (petite) 2 else 4; val h = haut + mur
        val r = 8f; val hh = (haut - 1) / 2f; val cx = 7.5f; val cy = hh
        val px = IntArray(w * h)
        var s = graine * 2654435761L.toInt() + 12345
        fun hasard(): Int { s = s xor (s shl 13); s = s xor (s ushr 17); s = s xor (s shl 5); return (s ushr 1) % 100 }
        fun dedans(dx: Float, dy: Float) = Math.abs(dy) <= hh + 0.5f && Math.abs(dx) <= r - Math.abs(dy) * (r / 2) / (hh + 0.5f)
        fun bas(dx: Float) = if (Math.abs(dx) <= r / 2) hh + 0.5f else (hh + 0.5f) * (r - Math.abs(dx)) / (r / 2)
        for (y in 0 until h) for (x in 0 until w) {
            val dx = x + 0.5f - cx - 0.5f; val dy = y + 0.5f - cy - 0.5f
            var c = 0
            if (dedans(dx, dy)) {
                val n = hasard()
                c = if (n < 25) eclaircir(dessus, -14) else if (n < 35) eclaircir(dessus, 14) else dessus
                if (!dedans(dx, dy - 1.1f)) c = eclaircir(c, 34)
                else if (!dedans(dx + (if (dx < 0) -1.2f else 1.2f), dy)) c = eclaircir(c, if (dy < 0) 24 else -20)
            } else if (Math.abs(dx) <= r && dy > bas(dx) && dy <= bas(dx) + mur) {
                val face = if (dx < -r / 2) 14 else if (dx > r / 2) -26 else 0
                val prof = dy - bas(dx)
                c = eclaircir(cote, face - (prof * 6).toInt())
                if (prof < 1.2f) c = eclaircir(cote, face + 26)
            }
            px[y * w + x] = c
        }
        Pix(w, h, px)
    }

    // ---------------------------------------------------------------- dessiner
    /** la commande écrite au-dessus de la colonne `tree` : toute la carte part de la Racine */
    const val INVITE_TREE = "~$ tree -F /"

    class Ligne(val n: Maison.Noeud, val y: Float, val xTuile: Float)

    /** Taille du dessin (largeur, hauteur) en dp, pour la même liste. */
    class Taille(val l: Float, val h: Float)

    private fun pointilles(p: Peintre, x0: Float, y0: Float, x1: Float, y1: Float) {
        if (x0 == x1) { var y = minOf(y0, y1); while (y < maxOf(y0, y1)) { p.rect(x0, y, 2f, 2f, BORD_VIF); y += 4f } }
        else { var x = minOf(x0, x1); while (x < maxOf(x0, x1)) { p.rect(x, y0, 2f, 2f, BORD_VIF); x += 4f } }
    }

    /** Coupe un texte (avec ses `commandes`) en lignes de largeur l au plus. */
    fun couper(p: Peintre, s: String, l: Float, taille: Float): List<String> {
        val out = mutableListOf<String>()
        var cur = ""
        for (mot in s.split(" ")) {
            val essai = if (cur.isEmpty()) mot else "$cur $mot"
            if (cur.isNotEmpty() && p.mesure(Vert.sansMarques(essai), taille) > l) { out.add(cur); cur = mot } else cur = essai
        }
        if (cur.isNotEmpty()) out.add(cur)
        // un passage `…` coupé en deux est refermé puis rouvert (comme langue.equilibrer sur PC)
        var ouvert = false
        return out.map { x ->
            var y = if (ouvert) "`$x" else x
            ouvert = y.count { it == '`' } % 2 == 1
            if (ouvert) y += "`"
            y
        }
    }

    /** Écrit un texte dont les `commandes` sont en vert. */
    fun texteVert(p: Peintre, s: String, x: Float, y: Float, taille: Float, couleur: Int) {
        var cx = x
        for ((i, morceau) in s.split('`').withIndex()) {
            if (morceau.isEmpty()) continue
            p.texte(morceau, cx, y, taille, if (i % 2 == 1) VERT else couleur, mono = i % 2 == 1)
            cx += p.mesure(morceau, taille, mono = i % 2 == 1)
        }
    }

    /**
     * Dessine la carte : titre, une ligne par nœud (dessin à gauche, `tree` à droite), pied (où on est, légende).
     * nouveaux : les clés qui brillent encore ; phase : le pas de l'animation (scintillement). Renvoie la taille.
     */
    fun dessiner(p: Peintre, titre: String, noeuds: List<Maison.Noeud>, pied: List<String>, nouveaux: Set<String>,
                 phase: Int = 0, largeurMin: Float = 320f): Taille {
        // 1. mesurer : la colonne du dessin, puis celle de tree
        var gauche = 0f
        for (n in noeuds) {
            val lab = n.etiquette + (if (n.marques.isNotEmpty()) "  " + n.marques else "") + (if (n.garde.isNotEmpty()) "  🔒" else "")
            gauche = maxOf(gauche, MARGE + n.prof * RETRAIT + 38f + p.mesure(lab, TAILLE, gras = n.dossier))
        }
        gauche += 12f
        val xTree = gauche + 12f
        var droite = xTree + p.mesure(INVITE_TREE, TAILLE, mono = true)
        for (n in noeuds) {
            var w = p.mesure(Maison.texteTree(n), TAILLE, mono = true)
            if (n.ici) w += 12f + p.mesure("◉", TAILLE, gras = true)
            if (n.nouveau || n.cle in nouveaux) w += 24f + p.mesure(t("carte.monde.nouveau"), TAILLE, gras = true)
            droite = maxOf(droite, xTree + w)
        }
        val largeur = maxOf(largeurMin, droite + MARGE)
        val lignesPied = pied.flatMap { couper(p, it, largeur - 2 * MARGE, TAILLE) }
        val hRangs = noeuds.size * HAUT_LIGNE
        val yRangs = HAUT_TITRE + 22f
        val hauteur = yRangs + hRangs + 14f + lignesPied.size * 16f + MARGE

        // 2. le fond, le cadre et le titre (comme le site : trois pastilles, texte vert)
        p.rect(0f, 0f, largeur, hauteur, FOND)
        p.rect(0f, 0f, largeur, HAUT_TITRE, PANNEAU)
        p.rect(0f, HAUT_TITRE - 2f, largeur, 2f, BORD)
        for ((i, c) in listOf(0xFFFF5A5A.toInt(), 0xFFFFC94D.toInt(), VERT).withIndex()) p.rect(MARGE + i * 11f, 13f, 7f, 7f, c)
        p.texte(titre, MARGE + 40f, 22f, TAILLE_TITRE, VERT, gras = true)
        p.texte(INVITE_TREE, xTree, HAUT_TITRE + 16f, TAILLE, BORD_VIF, mono = true)
        p.rect(gauche + 2f, HAUT_TITRE + 4f, 2f, hRangs + 18f, BORD)

        // 3. les rangées (une rayure sur deux), les pointillés qui relient chaque lieu à son parent
        val ys = HashMap<Maison.Noeud, Float>()
        val xs = HashMap<Maison.Noeud, Float>()
        for ((i, n) in noeuds.withIndex()) {
            ys[n] = yRangs + i * HAUT_LIGNE
            xs[n] = MARGE + n.prof * RETRAIT
            if (i % 2 == 1) p.rect(0f, ys.getValue(n), largeur, HAUT_LIGNE, RAYURE)
        }
        for (n in noeuds) {
            val par = n.parent ?: continue
            val px0 = xs.getValue(par) + 8f
            val py0 = ys.getValue(par) + 30f
            val y = ys.getValue(n) + 20f
            pointilles(p, px0, py0, px0, y)
            pointilles(p, px0, y, xs.getValue(n) + 2f, y)
        }
        // 4. chaque ligne : la tuile (ou l'objet), son icône, son nom ; puis la ligne de tree
        for (n in noeuds) {
            val y = ys.getValue(n)
            val x = xs.getValue(n)
            val brille = n.nouveau || n.cle in nouveaux
            if (n.genre == "suite") {
                for (k in 0..2) p.rect(x + 6f + k * 6f, y + 18f, 3f, 3f, DOUX)
            } else if (n.dossier) {
                val (dessus, cote) = sol(n)
                p.pixels(tuile(dessus, cote, n.rel.hashCode()), x, y + 9f, ECHELLE)
                p.pixels(icone(nomIcone(n)), x + 8f, y + 1f, ECHELLE)
            } else {
                val (dessus, cote) = sol(n)
                p.pixels(tuile(dessus, cote, n.rel.hashCode(), petite = true), x + 4f, y + 18f, 1.5f)
                p.pixels(icone(nomIcone(n)), x + 8f, y + 6f, ECHELLE)
            }
            if (brille) {                                          // ✨ nouveau ! : deux étoiles qui scintillent
                val grande = (phase + n.rel.length) % 2 == 0
                p.pixels(icone(if (grande) "etoile" else "petite_etoile"), x + 26f, y + 2f, ECHELLE)
                p.pixels(icone(if (grande) "petite_etoile" else "etoile"), x - 2f, y + 14f, 1.5f)
            }
            if (n.ici && !p.creature(x + 25f, y + 27f, 24f)) p.pixels(icone("epingle"), x + 18f, y + 2f, ECHELLE)   // la créature est ici
            val lab = n.etiquette
            val coul = if (n.brume || n.garde == "fermee") BRUME else if (n.dossier) TEXTE else DOUX
            p.texte(lab, x + 38f, y + 21f, TAILLE, coul, gras = n.dossier && !n.brume)
            if (n.marques.isNotEmpty()) p.texte(n.marques, x + 38f + p.mesure(lab, TAILLE, gras = n.dossier && !n.brume) + 6f, y + 21f, TAILLE, AMBRE)
            if (n.garde.isNotEmpty()) {                            // 🔒 fermée (grise) · 👣 visite seulement (Guide.kt)
                val xg = x + 38f + p.mesure(lab, TAILLE, gras = n.dossier && !n.brume) + 6f +
                    (if (n.marques.isNotEmpty()) p.mesure(n.marques, TAILLE) + 6f else 0f)
                if (n.garde == "fermee") p.pixels(icone("cadenas"), xg, y + 10f, 1.5f)
                else p.texte("👣", xg, y + 21f, TAILLE, AMBRE)
            }
            // tree
            p.texte(n.branches, xTree, y + 21f, TAILLE, BORD_VIF, mono = true)
            val xn = xTree + p.mesure(n.branches, TAILLE, mono = true)
            val nom = Maison.texteTree(n).removePrefix(n.branches)
            val cn = when {
                n.brume || n.genre == "suite" || n.garde == "fermee" -> BRUME
                n.genre == "secret" || n.genre == "secret_objet" -> VIOLET
                n.dossier && n.biome in Maison.BIOMES -> Maison.BIOMES.getValue(n.biome!!).claire
                n.dossier -> AMBRE
                else -> TEXTE
            }
            if (n.ici) p.rect(xn - 2f, y + 7f, p.mesure(nom, TAILLE, mono = true) + 4f, 19f, 0xFF1F3A2A.toInt())
            p.texte(nom, xn, y + 21f, TAILLE, cn, mono = true, gras = n.ici)
            var xx = xn + p.mesure(nom, TAILLE, mono = true) + 8f
            if (n.ici) { p.texte("◉", xx, y + 21f, TAILLE, VERT, gras = true); xx += p.mesure("◉", TAILLE) + 8f }
            if (brille) {
                p.pixels(icone("petite_etoile"), xx, y + 10f, ECHELLE)
                p.texte(t("carte.monde.nouveau"), xx + 12f, y + 21f, TAILLE, JAUNE, gras = true)
            }
        }
        // 5. le pied : où on est, les signes, les commandes rencontrées (en vert)
        var y = yRangs + hRangs + 14f
        p.rect(0f, y - 8f, largeur, 2f, BORD)
        for ((i, l) in lignesPied.withIndex()) {
            texteVert(p, l, MARGE, y + 10f, TAILLE, if (i == 0 && l.startsWith("◉")) VERT else DOUX)
            y += 16f
        }
        // 6. les lignes de balayage de l'écran cathodique
        var b = 0f
        while (b < hauteur) { p.rect(0f, b, largeur, 1f, BALAYAGE); b += 3f }
        p.rect(0f, 0f, largeur, 2f, BORD); p.rect(0f, hauteur - 2f, largeur, 2f, BORD)
        p.rect(0f, 0f, 2f, hauteur, BORD); p.rect(largeur - 2f, 0f, 2f, hauteur, BORD)
        return Taille(largeur, hauteur)
    }

    /** Le titre dessiné en haut de la carte. */
    fun titre(jeu: Jeu) = t("carte.monde.titre", "nom" to jeu.nom)
}
