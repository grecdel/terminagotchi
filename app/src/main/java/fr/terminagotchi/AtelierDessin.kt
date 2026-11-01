package fr.terminagotchi

/**
 * Le dessin de l'Atelier (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant les
 * illustrations (§ 7.15, B10) :
 *  - robot : dans la vue déployée, ce que la commande fait au robot simulé — l'ordre part du clavier vers la pièce
 *    (la LED s'allume, le moteur tourne), la valeur du capteur revient, le robot roule d'une case (atelier pas), le
 *    cerveau réfléchit (sh cerveau.sh) ;
 *  - grille : la grille du robot (obstacles, cases visitées, la flèche du robot), formes simples.
 * Aucun objet n'est posé sur la créature (pas d'accessoire) ; aucune marque.
 */
object AtelierDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val SYMBOLES = mapOf("led" to "💡", "moteur" to "⚙", "capteur" to "◉", "roues" to "🤖", "cerveau" to "🧠")
    val COULEURS = mapOf("led" to EspaceDessin.JAUNE, "moteur" to EspaceDessin.ORANGE, "capteur" to EspaceDessin.CYAN,
        "roues" to EspaceDessin.VERT, "cerveau" to EspaceDessin.VIOLET)

    fun robot(tl: Toile, r: Deploie.RobotD, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[r.piece] ?: EspaceDessin.CYAN
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val titre = t("at.piece.${r.piece}") + " — " + t("at.sens.${r.sens}")
        tl.texte(titre, x + 14 * z, y + 13 * z, 10.5f * z, c, true, 'g', false)
        val ty = y + (h + 18 * z) / 2
        val gauche = x + 30 * z
        val droite = x + w - 40 * z
        if (r.sens == "bouge") {
            // le robot roule d'une case sur le sol quadrillé
            for (k in 0..8) { val gx = gauche + k * (droite - gauche) / 8; tl.ligne(gx, ty + 14 * z, gx, ty + 18 * z, a(EspaceDessin.PALE, 120), 1 * z) }
            tl.ligne(gauche, ty + 16 * z, droite, ty + 16 * z, a(EspaceDessin.PALE, 120), 1.4f * z)
            val rx = gauche + q.toFloat() * (droite - gauche)
            tl.rrect(rx - 13 * z, ty - 12 * z, 26 * z, 22 * z, 5 * z, a(c, 60), c, 1.6f * z)
            tl.cercle(rx - 7 * z, ty + 12 * z, 4 * z, c, 1.6f * z)
            tl.cercle(rx + 7 * z, ty + 12 * z, 4 * z, c, 1.6f * z)
            tl.texte("▶", rx, ty - 1 * z, 11 * z, EspaceDessin.TEXTE, true, 'c')
            return
        }
        // le clavier, le fil, la pièce : l'ordre part (écrit, décide) ou la valeur revient (lit)
        tl.texte("⌨", gauche, ty, 16 * z, EspaceDessin.TEXTE, false, 'c')
        tl.ligne(gauche + 14 * z, ty, droite - 18 * z, ty, a(EspaceDessin.PALE, 140), 1.6f * z, 4 * z, 4 * z)
        val va = r.sens == "ecrit" || r.sens == "pense"
        val px = if (va) gauche + 14 * z + q.toFloat() * (droite - gauche - 32 * z) else droite - 18 * z - q.toFloat() * (droite - gauche - 32 * z)
        tl.texte(if (va) "▸" else "◂", px, ty, 13 * z, c, true, 'c')
        val allume = r.piece == "led" && r.sens == "ecrit" && q > 0.8
        if (allume) tl.lueur(droite, ty, 18 * z, a(c, 120))
        tl.cercle(droite, ty, 13 * z, c, 2 * z)
        tl.texte(SYMBOLES[r.piece] ?: "🤖", droite, ty, 13 * z, EspaceDessin.TEXTE, false, 'c')
    }
}
