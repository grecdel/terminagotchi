package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * La vie de la créature de la bulle et de l'île, sans aucune fenêtre (comme pc/tg/bureau_vie.py) : ce qu'elle fait,
 * où elle est, les gestes (appui, double, triple, appui long pour la déplacer, glisser vers le bas pour la ranger),
 * le petit menu rond et l'île. Testé sans téléphone : tests/jvm/Bulle.kt.
 *
 * Elle ne réagit qu'à des signaux du JEU (commandes comptées, faim, étapes, monstre) et à la batterie : jamais à ce
 * qui se passe dans les autres applications (aucune lecture de l'écran ni de ce qui est tapé).
 */
object BureauVie {
    val TAILLES = linkedMapOf("petite" to 56f, "moyenne" to 76f, "grande" to 100f)        // dp
    val VITESSES = linkedMapOf("lente" to 18f, "normale" to 32f, "rapide" to 54f)        // dp par seconde
    val DUREES = mapOf("etire" to 2.4, "baille" to 2.6, "sursaut" to 1.2, "coeur" to 2.6, "mange" to 2.6, "salut" to 2.4)
    const val BATTERIE_BASSE = 15
    const val IPS_MARCHE = 6
    const val IPS = 8

    /** (clé, symbole, angle) : Jouer en haut, comme sur PC et sur la maquette */
    val MENU = listOf(Triple("jouer", "▶", 90.0), Triple("terminal", ">_", 42.0), Triple("soccuper", "♥", 4.0),
        Triple("carte", "◉", -36.0), Triple("ranger", "⌄", 216.0), Triple("reglages", "⚙", 176.0), Triple("equipe", "●●", 138.0))

    /** Des signaux anonymes : secondes depuis la dernière commande du jeu, batterie (pourcent, branchée) */
    class Signaux(val inactif: Double? = null, val batterie: Int? = null, val enCharge: Boolean = true)

    class Creature(largeur: Float, var vitesse: Float = 32f, var surPlace: Boolean = false,
                   private val h: java.util.Random = java.util.Random(), x: Float? = null,
                   /** secondes sans commande du jeu avant qu'elle s'endorme */
                   val sommeil: Double = 1200.0) {
        var largeur = max(80f, largeur)
        var x = x ?: this.largeur * 0.7f
        var air = 0f
        private var vy = 0f
        var dir = -1
        var etat = "assis"; private set
        var tEtat = 0.0; private set
        var duree = 3.0; private set
        var t = 0.0; private set
        var porte = false; private set
        var rangee = false
        private var forceDodo = false
        private var battT = 0.0
        var bord = 40f

        fun changer(e: String, d: Double? = null) {
            etat = e; tEtat = 0.0
            duree = d ?: DUREES[e] ?: 4.0
            if (e == "marche" && (surPlace || rangee)) { etat = "assis"; duree = 6 + h.nextDouble() * 6 }
        }

        fun reagir(quoi: String) {
            if (quoi !in DUREES) return
            if (etat == "dort" && (quoi == "mange" || quoi == "baille")) return
            forceDodo = false
            changer(quoi)
        }

        fun dormir() { forceDodo = true; changer("dort", 600.0) }

        fun tick(dt0: Double, s: Signaux = Signaux()) {
            val dt = dt0.coerceIn(0.0, 0.5)
            t += dt; tEtat += dt
            if (porte) return
            if (air > 0f) {
                vy += (900 * dt).toFloat()
                air = max(0f, air - vy * dt.toFloat())
                if (air == 0f) { vy = 0f; changer("sursaut") }
                return
            }
            val basse = s.batterie != null && s.batterie <= BATTERIE_BASSE && !s.enCharge
            if (etat == "dort") {
                if (forceDodo) { if (tEtat > duree) { forceDodo = false; changer("etire") } }
                else if (s.inactif == null || s.inactif < 4) changer("etire")
                return
            }
            if (s.inactif != null && s.inactif >= sommeil && etat !in DUREES) { changer("dort", 1e6); return }
            if (basse) {
                battT += dt
                if (battT > 90 && (etat == "assis" || etat == "marche")) { battT = 0.0; reagir("baille"); return }
            }
            if (etat == "marche") {
                x += dir * vitesse * (if (basse) 0.6f else 1f) * dt.toFloat()
                if (x < bord) { x = bord; dir = 1 } else if (x > largeur - bord) { x = largeur - bord; dir = -1 }
            }
            if (tEtat >= duree) decider(s.inactif)
        }

        private fun decider(inactif: Double?) {
            if (etat in DUREES) { changer("assis", 3 + h.nextDouble() * 4); return }
            if (etat == "marche") {
                if (h.nextDouble() < 0.15) changer("etire") else changer("assis", 5 + h.nextDouble() * 6)
                return
            }
            val p = h.nextDouble()
            val calme = inactif != null && inactif > 60
            when {
                p < (if (calme) 0.35 else 0.6) && !surPlace && !rangee -> { dir = if (h.nextBoolean()) 1 else -1; changer("marche", 4 + h.nextDouble() * 6) }
                p < 0.72 -> changer("etire")
                p < (if (calme) 0.9 else 0.8) -> changer("baille")
                else -> changer("assis", 4 + h.nextDouble() * 5)
            }
        }

        fun prendre() { porte = true; forceDodo = false; rangee = false }
        fun deplacer(nx: Float, nair: Float) { x = nx.coerceIn(20f, largeur - 20f); air = max(0f, nair) }
        fun lacher() { porte = false; vy = 0f; if (air <= 2f) { air = 0f; changer("sursaut") } }

        /** Rangée dans le coin le plus proche : elle s'y assoit et ne se promène plus (un appui la réveille). */
        fun ranger() { rangee = true; porte = false; air = 0f; x = if (x < largeur / 2) bord else largeur - bord; changer("assis", 8.0) }

        /** (état montré, numéro d'image, décalage vertical en dp, miroir) */
        fun image(): Pair<Pair<String, Int>, Pair<Float, Boolean>> {
            val miroir = dir < 0
            if (porte || air > 0) return ("sursaut" to 0) to (0f to miroir)
            if (etat == "marche") {
                val k = (t * IPS_MARCHE).toInt()
                return ("marche" to k) to ((-abs(sin(t * PI * IPS_MARCHE / 2)) * 2).toFloat() to miroir)
            }
            var dy = 0.0
            if (etat == "sursaut" && tEtat < 0.5) dy = -sin(tEtat / 0.5 * PI) * 10
            else if (etat == "salut") dy = -abs(sin(tEtat * 5)) * 2
            return (etat to (tEtat * IPS).toInt()) to (dy.toFloat() to (miroir && etat != "dort"))     // les « z Z » à l'endroit
        }
    }

    /**
     * Les gestes du doigt : appui (le menu), double (un cœur), triple (une phrase), appui long puis glisser (la déplacer),
     * glisser vite vers le bas (la ranger dans un coin).
     */
    class Gestes(val delai: Double = 0.32, val seuil: Float = 12f, val appuiLong: Double = 0.42, val versLeBas: Float = 60f) {
        var n = 0; private set
        private var dernier: Double? = null
        private var depart: Triple<Float, Float, Double>? = null
        var glisse = false; private set
        private var bouge = false

        fun appuyer(x: Float, y: Float, t: Double) { depart = Triple(x, y, t); glisse = false; bouge = false }

        /** vrai pendant un déplacement (après un appui long) */
        fun bouger(x: Float, y: Float, t: Double): Boolean {
            val d = depart ?: return false
            if (!glisse && !bouge && hypot(x - d.first, y - d.second) > seuil) {
                bouge = true
                if (t - d.third >= appuiLong) glisse = true
                n = 0
            }
            return glisse
        }

        /** (immobile assez longtemps : l'appui long commence le déplacement) */
        fun tenir(t: Double): Boolean {
            val d = depart ?: return false
            if (!bouge && !glisse && t - d.third >= appuiLong) { glisse = true; n = 0 }
            return glisse
        }

        /** « glisse_fin », « ranger » (glissé vite vers le bas), « triple », ou null (attendre()) */
        fun relacher(x: Float, y: Float, t: Double): String? {
            val d = depart ?: return null
            depart = null
            if (glisse) { glisse = false; return "glisse_fin" }
            if (bouge) { bouge = false; return if (y - d.second > versLeBas && abs(x - d.first) < y - d.second) "ranger" else null }
            if (dernier != null && t - dernier!! > delai) n = 0
            n += 1
            dernier = t
            if (n >= 3) { n = 0; dernier = null; return "triple" }
            return null
        }

        fun attendre(t: Double): String? {
            val dn = dernier ?: return null
            if (n > 0 && depart == null && t - dn > delai) { val k = n; n = 0; dernier = null; return if (k == 1) "appui" else "double" }
            return null
        }
    }

    /** Largeur approchée d'un texte (comme bureau_vie.largeur_texte) */
    fun largeurTexte(texte: String, taille: Float): Float {
        var n = 0f
        for (c in texte) {
            val o = c.code
            n += if (o in 0x1100..0x115F || o in 0x2E80..0xA4CF || o in 0xAC00..0xD7A3 || o in 0xF900..0xFAFF || o in 0xFF00..0xFF60) 1f else 0.58f
        }
        return n * taille
    }

    class Bouton(val cle: String, val symbole: String, val libelle: String, val x: Float, val y: Float, val w: Float, val h: Float) {
        fun touche(px: Float, py: Float) = px in x..(x + w) && py in y..(y + h)
    }

    /** Les boutons du menu rond autour de la créature (comme bureau_vie.menu_positions), dans une zone l × hz ;
     *  sur un écran étroit, l'ovale se resserre en largeur et garde sa hauteur. Rend aussi (cx, cy, rx, ry). */
    fun menuPositions(cx0: Float, cyCorps: Float, hautCreature: Float, libelles: Map<String, String>, taille: Float,
                      l: Float, hz: Float, rayonMin: Float): Pair<List<Bouton>, FloatArray> {
        val bh = taille + 22f * taille / 14f
        val larg = MENU.map { largeurTexte(libelles[it.first] ?: it.first, taille) + bh + 18f * taille / 14f }
        val r = max(rayonMin, hautCreature * 1.9f)
        val demi = (larg.maxOrNull() ?: 0f) / 2
        val marge = 8f * taille / 14f
        val rx = max(rayonMin * 0.4f, min(r, (l - 2 * demi - 2 * marge) / 2))
        val ry = r * 0.82f
        val cx = cx0.coerceIn(min(rx + demi + marge, l / 2), max(l - rx - demi - marge, l / 2))
        val cy = max(cyCorps - r * 0.5f, ry + bh / 2 + marge)
        val out = MENU.mapIndexed { i, (cle, sym, ang) ->
            val a = Math.toRadians(ang)
            val bx = cx + rx * cos(a).toFloat(); val by = cy - ry * sin(a).toFloat()
            Bouton(cle, sym, libelles[cle] ?: cle, bx - larg[i] / 2, (by - bh / 2).coerceAtMost(hz - bh), larg[i], bh)
        }
        return out to floatArrayOf(cx, cy, rx, ry)
    }

    /** L'île : « repos » (pilule), « ouverte », « evenement » (ouverte toute seule quelques secondes). */
    class Ile(var auto: Boolean = true) {
        var etat = "repos"; private set
        var ouverture = 0f; private set
        var evenement: String? = null; private set
        private var tEvt = 0.0
        val DUREE = 6.0

        fun basculer() { etat = if (etat == "ouverte") "repos" else "ouverte"; if (etat == "repos") evenement = null }
        fun fermer() { etat = "repos"; evenement = null }
        fun annoncer(texte: String): Boolean {
            evenement = texte
            if (!auto || etat == "ouverte") return false
            etat = "evenement"; tEvt = 0.0
            return true
        }

        fun tick(dt: Double) {
            if (etat == "evenement") { tEvt += dt; if (tEvt > DUREE) { etat = "repos"; evenement = null } }
            val but = when (etat) { "repos" -> 0f; "evenement" -> 0.55f; else -> 1f }
            ouverture += (but - ouverture) * min(1f, (dt * 9).toFloat())
            if (abs(but - ouverture) < 0.01f) ouverture = but
        }
    }

    /** Ce que le jeu a compté (rien d'autre n'est regardé) */
    class Resume(val total: Int, val lecon: Int, val etape: Int, val faim: Double, val monstre: Boolean)

    /** Les événements à annoncer dans l'île entre deux relevés du jeu : clés de texte. */
    fun evenements(a: Resume?, b: Resume?): List<String> {
        if (a == null || b == null) return emptyList()
        val out = mutableListOf<String>()
        if (b.monstre && !a.monstre) out.add("bur.ile.monstre")
        if (b.lecon > a.lecon || (b.lecon == a.lecon && b.etape > a.etape)) out.add("bur.ile.etape")
        if (b.faim < 25 && a.faim >= 25) out.add("bur.ile.envie_faim")
        return out
    }
}
