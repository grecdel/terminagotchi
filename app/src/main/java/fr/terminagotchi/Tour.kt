package fr.terminagotchi

import kotlin.random.Random

/**
 * Un tour de jeu après chaque commande tapée (dans le même ordre que app.boucle_jeu sur PC) :
 * la créature mange, le terrain effacé est repéré, la Maison endormie avance (pièces visitées, chapitres,
 * leçons, quêtes : Histoire.tick), le défi, le dressage (et son mini-combat), la troupe, l'attirance, puis
 * peut-être un monstre. Sans écran : TerminalActivity affiche les messages, et les tests JVM
 * (tests/jvm/RetoursEnfants.kt, tests/jvm/Histoire.kt) rejouent les mêmes tours.
 * cwd : le dossier courant du terminal APRÈS la commande (Shell.dossier), pour la carte de la maison.
 */
object Tour {
    class Resultat(val mange: Boolean, val messages: List<Pair<String, Int>>, val saut: Int)

    const val ROSE = 0xFFFF87FF.toInt()

    /** hasard = false : aucun monstre n'apparaît au hasard (tests). */
    fun apresCommande(jeu: Jeu, ligne: String, colle: Boolean, rappel: Boolean = false, hasard: Boolean = true, cwd: java.io.File? = null): Resultat {
        val msgs = mutableListOf<Pair<String, Int>>()
        var saut = 0
        jeu.tick()
        val mange = jeu.manger(ligne, colle, rappel)
        // l'œuf et sa liste (Intro.kt) : la commande qui le fait éclore ne valide pas déjà la leçon 1
        val eclot = Intro.apresCommande(jeu, ligne, colle || rappel)
        Terrain.verifier(jeu, ligne, colle)?.let { msgs.add(it to 0xFFFFAF5F.toInt()) }   // terrain effacé : le reconstruire
        Histoire.tick(jeu, if (eclot) null else ligne, colle, cwd)
        if (!colle && !rappel) Defis.verifier(jeu, ligne)?.let { msgs.add(it to 0xFFFFD75F.toInt()); saut = 8 }
        val combats = Intro.ouvert(jeu, "combats")              // les monstres arrivent avec leur présentation
        if (combats) Explo.verifier(jeu)?.let { msgs.add(it to ROSE) }
        Dressage.verifier(jeu, ligne, colle)?.let { msgs.add(it to ROSE); saut = 8 }
        Equipe.apresCommande(jeu, colle || rappel)?.let { msgs.add(it to 0xFFFFAF00.toInt()) }
        if (combats) Explo.attirer(jeu, ligne, colle || rappel)    // la commande d'une famille l'attire
        if (hasard && !colle && !rappel && combats && Explo.debloquee(jeu) && !Dressage.actif(jeu) && Random.nextInt(25) == 0) {
            Explo.spawn(jeu)                                       // en jouant, un monstre peut surgir
        }
        Envies.apresCommande(jeu, ligne, colle || rappel)          // les 6 envies : usure, plaisirs, poussière, rappel espacé
        Guide.apresCommande(jeu, ligne, colle || rappel, cwd)?.let { msgs.add(it to ROSE) }   // le guide : talents, fatigue, régions
        // salle d'entraînement : l'exercice en cours est-il réussi ? (entrainement répond lui-même aux réponses)
        if (Regles.premierMot(ligne) !in setOf("entrainement", "exercice"))
            Entrainement.apresCommande(jeu, ligne, colle || rappel, cwd)?.let { msgs.add(it to 0xFFFFD75F.toInt()) }
        Intro.verifier(jeu)                                        // les fonctions qui s'ouvrent maintenant (Intro.kt)
        return Resultat(mange, msgs, saut)
    }

    /** Toutes les ~5 s, sans commande : le terrain, les leçons « fichiers », le chrono du dressage. */
    fun periodique(jeu: Jeu, cwd: java.io.File? = null): List<Pair<String, Int>> {
        val msgs = mutableListOf<Pair<String, Int>>()
        jeu.tick()
        Terrain.verifier(jeu, null, false)?.let { msgs.add(it to 0xFFFFAF5F.toInt()) }
        Histoire.tick(jeu, null, false, cwd)
        Defis.verifier(jeu, null)
        val combats = Intro.ouvert(jeu, "combats")
        if (combats && jeu.existe && jeu.stade >= 1 && Defis.actif(jeu) == null && !Dressage.actif(jeu) && Random.nextInt(60) == 0) Defis.lancer(jeu)
        if (combats) Explo.verifier(jeu)?.let { msgs.add(it to ROSE) }
        Dressage.verifier(jeu, null, false)?.let { msgs.add(it to ROSE) }
        Intro.verifier(jeu)
        return msgs
    }
}
