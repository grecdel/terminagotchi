package fr.terminagotchi

import kotlin.random.Random

/**
 * Un tour de jeu après chaque commande tapée (dans le même ordre que app.boucle_jeu sur PC) :
 * la créature mange, le terrain effacé est repéré, les leçons avancent, le défi, le dressage (et son
 * mini-combat), la troupe, l'attirance, puis peut-être un monstre. Sans écran : TerminalActivity
 * affiche les messages, et le test JVM (tests/jvm/RetoursEnfants.kt) rejoue les mêmes tours.
 */
object Tour {
    class Resultat(val mange: Boolean, val messages: List<Pair<String, Int>>, val saut: Int)

    const val ROSE = 0xFFFF87FF.toInt()

    /** hasard = false : aucun monstre n'apparaît au hasard (tests). */
    fun apresCommande(jeu: Jeu, ligne: String, colle: Boolean, rappel: Boolean = false, hasard: Boolean = true): Resultat {
        val msgs = mutableListOf<Pair<String, Int>>()
        var saut = 0
        jeu.tick()
        val mange = jeu.manger(ligne, colle, rappel)
        Terrain.verifier(jeu, ligne, colle)?.let { msgs.add(it to 0xFFFFAF5F.toInt()) }   // terrain effacé : le reconstruire
        jeu.leconTick(ligne, colle)
        if (!colle && !rappel) Defis.verifier(jeu, ligne)?.let { msgs.add(it to 0xFFFFD75F.toInt()); saut = 8 }
        Explo.verifier(jeu)?.let { msgs.add(it to ROSE) }
        Dressage.verifier(jeu, ligne, colle)?.let { msgs.add(it to ROSE); saut = 8 }
        Equipe.apresCommande(jeu, colle || rappel)?.let { msgs.add(it to 0xFFFFAF00.toInt()) }
        Explo.attirer(jeu, ligne, colle || rappel)                 // la commande d'une famille l'attire
        if (hasard && !colle && !rappel && Explo.debloquee(jeu) && !Dressage.actif(jeu) && Random.nextInt(25) == 0) {
            Explo.spawn(jeu)                                       // en jouant, un monstre peut surgir
        }
        return Resultat(mange, msgs, saut)
    }

    /** Toutes les ~5 s, sans commande : le terrain, les leçons « fichiers », le chrono du dressage. */
    fun periodique(jeu: Jeu): List<Pair<String, Int>> {
        val msgs = mutableListOf<Pair<String, Int>>()
        jeu.tick()
        Terrain.verifier(jeu, null, false)?.let { msgs.add(it to 0xFFFFAF5F.toInt()) }
        jeu.leconTick(null, false)
        Defis.verifier(jeu, null)
        if (jeu.existe && jeu.stade >= 1 && Defis.actif(jeu) == null && !Dressage.actif(jeu) && Random.nextInt(60) == 0) Defis.lancer(jeu)
        Explo.verifier(jeu)?.let { msgs.add(it to ROSE) }
        Dressage.verifier(jeu, null, false)?.let { msgs.add(it to ROSE) }
        return msgs
    }
}
