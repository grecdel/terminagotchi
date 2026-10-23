package fr.terminagotchi

import java.io.File

/** Fichiers du Doom-like : le niveau (carte.txt) et les réglages (reglages.txt), modifiables par le joueur. */
object Doom {
    val CARTE_DEFAUT = """
        ################
        #C.....#.......#
        #.####.#.####..#
        #.#..B.#....#..#
        #.#.####.##.#..#
        #.......B.#....#
        ####.####.#.##.#
        #....#..B.#..#.#
        #.##.#.####..#.#
        #..#.........#X#
        ################
    """.trimIndent() + "\n"

    val REGLAGES_DEFAUT = """
        # Réglages du jeu : change une valeur, enregistre, puis relance « doom ».
        # Ce sont des VARIABLES : un nom = une valeur.

        vitesse = 4
        vie = 5
        vitesse_ennemis = 2
        couleur_ciel = violet
        couleur_sol = gris
        couleur_murs = brique
        # couleurs possibles : rouge, orange, jaune, vert, bleu, violet, rose, gris, noir, blanc, brique, pierre
    """.trimIndent() + "\n"

    val LEGENDE = "# = mur · C = départ · B = bestiole · X = sortie · . = vide"

    fun dossier(jeu: Jeu) = File(jeu.terrain, "jeu")

    fun preparer(jeu: Jeu): File {
        val d = dossier(jeu)
        d.mkdirs()
        val carte = File(d, "carte.txt")
        if (!carte.exists()) carte.writeText(CARTE_DEFAUT)
        val reg = File(d, "reglages.txt")
        if (!reg.exists()) reg.writeText(REGLAGES_DEFAUT)
        val lis = File(d, "LISEZMOI.txt")
        if (!lis.exists()) lis.writeText("🎮 L'atelier du jeu\n$LEGENDE\n" +
            "Modifier le niveau :  edite carte.txt\nModifier les réglages :  edite reglages.txt\nJouer :  doom\n")
        return d
    }

    fun carteModifiee(d: File): Boolean {
        val f = File(d, "carte.txt")
        return f.isFile && f.readText().trim() != CARTE_DEFAUT.trim()
    }

    fun reglagesModifies(d: File): Boolean {
        val f = File(d, "reglages.txt")
        if (!f.isFile) return false
        val defaut = lireReglages(REGLAGES_DEFAUT)
        return lireReglages(f.readText()) != defaut
    }

    fun lireReglages(texte: String): Map<String, String> =
        texte.lines().map { it.substringBefore('#').trim() }.filter { '=' in it }
            .associate { it.substringBefore('=').trim().lowercase() to it.substringAfter('=').trim().lowercase() }

    fun couleur(nom: String?, defaut: Int): Int = when (nom) {
        "rouge" -> 0xFFB03030.toInt()
        "orange" -> 0xFFD07020.toInt()
        "jaune" -> 0xFFD0C040.toInt()
        "vert" -> 0xFF30A050.toInt()
        "bleu" -> 0xFF3060C0.toInt()
        "violet" -> 0xFF3A2A6A.toInt()
        "rose" -> 0xFFC060A0.toInt()
        "gris" -> 0xFF505058.toInt()
        "noir" -> 0xFF101014.toInt()
        "blanc" -> 0xFFD8D8D8.toInt()
        "brique" -> 0xFF8A4030.toInt()
        "pierre" -> 0xFF707080.toInt()
        else -> defaut
    }
}
