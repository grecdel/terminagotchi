package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

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
    val DUREES = mapOf("etire" to 2.4, "baille" to 2.6, "sursaut" to 1.2, "coeur" to 2.6, "mange" to 3.4, "salut" to 2.8)
    const val BATTERIE_BASSE = 15
    const val IPS_MARCHE = 6
    const val IPS = 8
    /** secondes : tassement de l'ancienne pose, court fondu, étirement et rebond de la nouvelle (comme bureau_vie.py) */
    const val TRANSITION = 0.36
    const val CLIGNEMENT = 0.14

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
        /** l'image d'avant le dernier changement (état, image, miroir) et le temps depuis ce changement */
        var prec: Triple<String, Int, Boolean>? = null; private set
        var tTrans = TRANSITION; private set
        /** elle parle : (texte, début) ; la mâchoire suit les syllabes */
        var parole: Pair<String, Double>? = null; private set
        /** où est sa bouche : fractions du corps depuis les pieds (album) */
        var bouche: Pair<Float, Float> = BOUCHE_DEFAUT
        /** largeur de sa bouche (fraction de la largeur du corps) ; null : pas de bouche (album) */
        var levre: Float? = null
        /** le bord avant du corps à la hauteur de la bouche (album) */
        var bordCorps = 0.42f
        /** le prochain clignement (secondes) ; négatif pendant le clignement */
        var cligne = 1.5 + h.nextDouble() * 2.5; private set

        fun changer(e: String, d: Double? = null) {
            if (e != etat || tEtat > TRANSITION) {
                val an = animer(this)                  // l'image montrée juste avant (et son miroir), qui s'efface
                prec = Triple(an.etat, an.k, an.miroir)
                tTrans = 0.0
            }
            etat = e; tEtat = 0.0
            // des durées un peu au hasard : elle ne fait jamais tout au même rythme
            duree = d ?: ((DUREES[e] ?: 4.0) * (0.8 + h.nextDouble() * 0.55))
            if (e == "marche" && (surPlace || rangee)) { etat = "assis"; duree = 6 + h.nextDouble() * 6 }
        }

        fun reagir(quoi: String) {
            if (quoi !in DUREES) return
            if (etat == "dort" && (quoi == "mange" || quoi == "baille")) return
            forceDodo = false
            changer(quoi)
        }

        fun dormir() { forceDodo = true; changer("dort", 600.0) }

        /** Elle dit texte : la bouche s'ouvre à chaque syllabe (assise ; elle s'arrête de marcher pour parler). */
        fun parler(texte: String) {
            parole = texte to t
            if (etat == "marche" || etat == "dort") changer("assis", dureeParole(texte) + 0.6)
        }

        /** L'ouverture de la bouche (0 à 1) pour la parole en cours, ou null. */
        fun parle(): Double? {
            val (texte, debut) = parole ?: return null
            if (t - debut > dureeParole(texte)) { parole = null; return null }
            return paroleNiveau(texte, t - debut)
        }

        fun tick(dt0: Double, s: Signaux = Signaux()) {
            val dt = dt0.coerceIn(0.0, 0.5)
            t += dt; tEtat += dt; tTrans += dt
            cligne -= dt
            if (cligne < -CLIGNEMENT) cligne = if (h.nextDouble() > 0.2) 2.2 + h.nextDouble() * 4.3 else 0.35
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

        /** Pour les tests : forcer le prochain clignement. */
        fun clignerDans(s: Double) { cligne = s }
    }

    /**
     * Ce qu'on dessine à un instant (comme bureau_vie.Anime) : la pose, sa déformation autour des pieds (sx, sy, rot en
     * degrés, dy en dp), le miroir, son opacité, l'ancienne pose qui s'efface pendant une transition, l'ombre et les
     * petits effets (genre « z », « coeur », « etincelle », « miette » ; x, y en fractions du corps depuis les pieds ;
     * taille : fraction de la hauteur, sauf la miette : diamètre en fraction de la LARGEUR ; opacité). La miette se
     * dessine DERRIÈRE : fond (la bouche ouverte, ou null), la miette, puis la pose trouée à la bouche ; les autres
     * effets devant. Les déformations sont continues : appliquées à la résolution de l'écran.
     */
    class Anime(var etat: String, var k: Int, var dy: Float, val miroir: Boolean) {
        var sx = 1f; var sy = 1f; var rot = 0f; var opacite = 1f; var ombre = 1f
        var ancien: Ancien? = null
        var fond: String? = null
        val effets = mutableListOf<Effet>()
    }
    class Ancien(val etat: String, val k: Int, val opacite: Float, val miroir: Boolean)
    class Effet(val genre: String, val x: Float, val y: Float, val taille: Float, val opacite: Float)

    private fun doux(x0: Double): Double { val x = x0.coerceIn(0.0, 1.0); return x * x * (3 - 2 * x) }

    private fun enveloppe(p: Double, monte: Double = 0.3, descend: Double = 0.7): Double = when {
        p < monte -> doux(p / monte)
        p < descend -> 1.0
        else -> 1.0 - doux((p - descend) / (1 - descend))
    }

    /** L'image animée de la créature (même calcul que bureau_vie.animer). */
    fun animer(c: Creature): Anime {
        val im = c.image()
        val a = Anime(im.first.first, im.first.second, im.second.first, im.second.second)
        val u = c.tEtat; val d = max(0.1, c.duree); val t = c.t
        val p = min(1.0, u / d)
        if (c.porte || c.air > 0) { a.ombre = max(0.3f, 1 - c.air / 300f); a.sy = 1.04f; a.sx = 0.97f; return a }
        val souffle = sin(2 * PI * t / 3.2)
        if (a.etat in setOf("assis", "coeur", "salut", "mange", "etire", "baille")) {
            a.sy = (1 + 0.016 * souffle).toFloat(); a.sx = (1 - 0.007 * souffle).toFloat()
        }
        val parle = if (a.etat == "assis" || a.etat == "marche") c.parle() else null
        when (a.etat) {
            "assis" -> if (parle != null) a.etat = poseBouche(parle) else if (c.cligne < 0) a.etat = "cligne"
            "dort" -> {
                val lent = sin(2 * PI * t / 4.6)
                a.sy = (1 + 0.024 * lent).toFloat(); a.sx = (1 - 0.01 * lent).toFloat()
                for (i in 0 until 3) {
                    val ph = ((t / 1.6 + i / 3.0) % 1.0)
                    a.effets.add(Effet("z", (0.28 + 0.22 * ph).toFloat(), (-(0.95 + 0.5 * ph)).toFloat(),
                        (0.14 + 0.2 * ph).toFloat(), sin(PI * ph).toFloat()))
                }
            }
            "etire", "baille" -> {
                val e = enveloppe(p)
                if (a.etat == "etire") { a.sy *= (1 + 0.07 * e).toFloat(); a.sx *= (1 - 0.04 * e).toFloat() }
                else {
                    a.sy *= (1 + 0.045 * e).toFloat(); a.sx *= (1 + 0.02 * e).toFloat(); a.rot = (-3.0 * e).toFloat()
                    // la fin du bâillement : fondu vers la bouche grande ouverte, la mâchoire se referme, assise
                    if (p >= BAILLE_FIN[0]) {
                        val ferme = doux((p - BAILLE_FIN[1]) / (BAILLE_FIN[2] - BAILLE_FIN[1]))
                        a.etat = poseBouche(1 - ferme)
                        val f = doux((p - BAILLE_FIN[0]) / (BAILLE_FIN[1] - BAILLE_FIN[0]))
                        if (f < 1) { a.ancien = Ancien("baille", a.k, (1 - f).toFloat(), a.miroir); a.opacite = f.toFloat() }
                    }
                }
            }
            "sursaut" -> when {
                u < 0.55 -> {
                    val hh = sin(PI * u / 0.55)
                    a.dy = (-hh * 18).toFloat(); a.ombre = (1 - 0.45 * hh).toFloat()
                    if (u < 0.08) { a.sy = 0.9f; a.sx = 1.06f } else { a.sy = (1 + 0.05 * hh).toFloat(); a.sx = (1 - 0.03 * hh).toFloat() }
                }
                u < 0.72 -> { val q = sin(PI * (u - 0.55) / 0.17); a.sy = (1 - 0.1 * q).toFloat(); a.sx = (1 + 0.06 * q).toFloat() }
            }
            "mange" -> manger(c, a, p)
            "coeur" -> {
                a.dy = (-abs(sin(u * 5.5)) * 2.5 * (1 - p)).toFloat()
                a.effets.add(Effet("coeur", (0.32 + 0.05 * sin(u * 4)).toFloat(), (-(0.95 + 0.6 * p)).toFloat(),
                    (0.16 + 0.1 * p).toFloat(), (1 - doux(p)).toFloat()))
            }
            "salut" -> {
                // coucou : deux ou trois petits sauts (tassement, ombre), bouche ouverte toute contente, balancier
                a.dy = 0f
                val n = max(2, min(SAUTS, ((d - SAUT_DEBUT - 0.5) / SAUT).toInt()))
                val w = (u - SAUT_DEBUT) / SAUT
                if (w >= 0 && w < n) {
                    val f = w - floor(w)
                    if (f < 0.18) {
                        val q = sin(PI * f / 0.18); a.sy *= (1 - 0.07 * q).toFloat(); a.sx *= (1 + 0.045 * q).toFloat()
                    } else if (f < 0.82) {
                        val hh = sin(PI * (f - 0.18) / 0.64)
                        a.dy = (-SAUT_HAUTEUR * hh).toFloat(); a.ombre = (1 - 0.45 * hh).toFloat()
                        a.sy *= (1 + 0.04 * hh).toFloat(); a.sx *= (1 - 0.025 * hh).toFloat()
                    } else {
                        val q = sin(PI * (f - 0.82) / 0.18); a.sy *= (1 - 0.09 * q).toFloat(); a.sx *= (1 + 0.06 * q).toFloat()
                    }
                }
                if (u >= 0.08 && u < SAUT_DEBUT + n * SAUT + 0.35) a.etat = "salut_ouvert"
                a.rot = (5.0 * sin(2 * PI * u / 0.55) * (if (p > 0.8) 1 - doux((p - 0.8) / 0.2) else 1.0)).toFloat()
            }
        }
        val pr = c.prec
        if (pr != null && c.tTrans < TRANSITION) {
            val q = c.tTrans / TRANSITION
            val fondu = doux((q - 0.35) / 0.3)
            if (q < 0.5) { val ta = doux(q * 2); a.sy *= (1 - 0.08 * ta).toFloat(); a.sx *= (1 + 0.05 * ta).toFloat() }
            else {
                val q2 = (q - 0.5) * 2
                a.sy *= (0.92 + 0.08 * doux(q2) + 0.05 * sin(PI * q2)).toFloat()
                a.sx *= (1.05 - 0.05 * doux(q2) - 0.03 * sin(PI * q2)).toFloat()
                a.dy -= (1.5 * sin(PI * q2)).toFloat()
            }
            if ((pr.first != a.etat || pr.second != a.k) && pr.first != c.etat && fondu < 1) {
                a.ancien = Ancien(pr.first, pr.second, (1 - fondu).toFloat(), pr.third)
                a.opacite = fondu.toFloat()
            }
        }
        return a
    }

    val BAILLE_FIN = doubleArrayOf(0.66, 0.72, 0.93)
    const val SAUTS = 3
    const val SAUT = 0.42
    const val SAUT_DEBUT = 0.15
    const val SAUT_HAUTEUR = 10.0
    const val BOUCHEES = 3

    /** Trois bouchées, la miette toujours DERRIÈRE la créature (comme bureau_vie.manger). */
    private fun manger(c: Creature, a: Anime, p: Double) {
        val bx = c.bouche.first.toDouble(); val by = c.bouche.second.toDouble()
        a.etat = "assis"
        val q = (p - 0.04) / 0.92 * BOUCHEES
        if (q < 0 || q >= BOUCHEES) return
        val v = q - floor(q)
        val bordC = c.bordCorps.toDouble()
        val depart = bordC + 0.32
        val lv = c.levre
        if (lv != null) {
            val taille = 0.6 * lv
            val ouvre = if (v < 0.5) doux((v - 0.1) / 0.3) else 1 - doux((v - 0.5) / 0.22)
            val k = (ouvre.coerceIn(0.0, 1.0) * 3 + 0.5).toInt()
            if (k > 0) { a.fond = POSES_BOUCHE[k]; a.etat = "trou$k" }
            if (v < 0.72) {
                val bord = bordC + taille / 2
                val x: Double; val y: Double
                if (v < 0.42) {
                    val m = doux(v / 0.3); x = depart + (bord - depart) * m; y = by - 0.12 * sin(PI * m)
                } else {
                    val m = doux((v - 0.42) / 0.1); x = bord + (bx - bord) * m; y = by + 0.01 * m
                }
                a.effets.add(Effet("miette", x.toFloat(), y.toFloat(), (taille * (1 - 0.25 * doux((v - 0.5) / 0.22))).toFloat(),
                    doux(v / 0.08).toFloat()))
            }
            if (v > 0.7) {
                val bosse = sin(PI * (v - 0.7) / 0.3); a.sy *= (1 - 0.05 * bosse).toFloat(); a.sx *= (1 + 0.03 * bosse).toFloat()
            }
        } else {
            val fin = bordC - 0.08
            if (v < 0.5) {
                val m = doux(v / 0.5)
                a.effets.add(Effet("miette", (depart + (fin - depart) * m).toFloat(), (by - 0.1 * sin(PI * m)).toFloat(), 0.09f,
                    doux(v / 0.08).toFloat()))
            }
            if (v >= 0.42 && v < 0.8) {
                val e = (v - 0.42) / 0.38
                a.effets.add(Effet("etincelle", (bordC + 0.05).toFloat(), (by - 0.04 - 0.08 * e).toFloat(),
                    (0.12 + 0.1 * sin(PI * e)).toFloat(), sin(PI * e).toFloat()))
            }
            if (v > 0.45 && v < 0.8) {
                val bosse = sin(PI * (v - 0.45) / 0.35); a.sy *= (1 - 0.05 * bosse).toFloat(); a.sx *= (1 + 0.03 * bosse).toFloat()
            }
        }
    }

    /** La mini-créature de l'île respire et cligne avec la créature de la bulle : (état, sx, sy). */
    fun miniVie(c: Creature?, t: Double): Triple<String, Float, Float> {
        val s = sin(2 * PI * t / 3.2)
        val parle = c?.parle()
        val etat = if (parle != null) poseBouche(parle) else if (c != null && c.cligne < 0) "cligne" else "assis"
        return Triple(etat, (1 - 0.007 * s).toFloat(), (1 + 0.016 * s).toFloat())
    }

    // ------------------------------------------------------------ la mâchoire (manger, parler), comme bureau_vie.py
    val BOUCHE_DEFAUT = 0.12f to -0.3f
    val POSES_BOUCHE = listOf("assis", "bouche1", "bouche2", "bouche3")

    /** La pose de la mâchoire pour une ouverture de 0 (fermée) à 1 (grande ouverte) : les images de poses.bin. */
    fun poseBouche(niveau: Double): String = POSES_BOUCHE[(niveau.coerceIn(0.0, 1.0) * 3 + 0.5).toInt()]

    const val SYLLABE = 0.16
    private const val VOYELLES = "aeiouyàâäéèêëîïôöùûüÿœæ"
    private val PAUSES = mapOf('.' to 0.3, '!' to 0.3, '?' to 0.3, '…' to 0.35, ',' to 0.18, ';' to 0.2, ':' to 0.2, ' ' to 0.04)

    /** Le texte coupé pour la bouche : (durée, amplitude) ; amplitude 0 = une pause (même découpage qu'en Python). */
    fun syllabes(texte: String): List<Pair<Double, Double>> {
        val out = mutableListOf<Pair<Double, Double>>()
        var dansVoyelle = false
        var autres = 0
        var k = 0
        for (ch in texte.lowercase()) {
            val pause = PAUSES[ch]
            if (pause != null) { out.add(pause to 0.0); dansVoyelle = false; continue }
            val latin = ch.code < 128 || ch in VOYELLES || ch in '\u00c0'..'\u024f'
            if (latin || ch in '\u0400'..'\u04ff') {
                val voyelle = ch in VOYELLES || ch in "аеёиоуыэюя"
                if (voyelle && !dansVoyelle) { out.add(SYLLABE to (if (k % 2 == 1) 0.75 else 1.0)); k++ }
                dansVoyelle = voyelle
            } else if (ch.isLetter()) {
                autres++
                if (autres % 2 == 1) { out.add(SYLLABE to (if (k % 2 == 1) 0.75 else 1.0)); k++ }
            }
        }
        return out
    }

    fun dureeParole(texte: String): Double = syllabes(texte).sumOf { it.first }

    /** L'ouverture de la bouche (0 à 1) au temps t d'une phrase : une ouverture par syllabe, fermée aux pauses. */
    fun paroleNiveau(texte: String, t0: Double): Double {
        if (t0 < 0) return 0.0
        var t = t0
        for ((d, a) in syllabes(texte)) {
            if (t < d) return if (a > 0) a * sin(PI * t / d) else 0.0
            t -= d
        }
        return 0.0
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
