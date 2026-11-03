package fr.terminagotchi

import org.json.JSONObject

/**
 * Les sons du jeu (idées 81, 82, 83, 86, validées le 3 novembre) : tout est FABRIQUÉ ici, au moment de jouer —
 * portage exact de pc/tg/sons.py (mêmes échantillons, vérifiés par les vecteurs communs donnees/sons/vecteurs.json).
 * Aucune fonction mathématique du système : sinus, exponentielle et 2^x calculés avec + − × ÷ seulement, dans le même
 * ordre qu'en Python (la JVM ne fusionne jamais les opérations : résultats identiques au bit près).
 *
 *   Sons.son(jeu, "evolution")    joue un son si les réglages le permettent (les autres modules n'appellent que ça)
 *   Sons.musique(jeu, cle)        la boucle d'une vue Monde / Espace (cle : biome, « gardiens », ou null)
 *   Sons.commande(jeu, reste)     son … (comme `tg son …` sur PC)
 *
 * Lecture : AudioTrack (Android) en flux, une seule piste mélangée (SonsLecteur.kt) ; attributs « jeu », focus audio,
 * silence si le téléphone est en silencieux ou vibreur, pause quand l'appli passe en arrière-plan.
 */
object Sons {
    const val SR = 22050
    const val N = 1024
    const val PI = 3.141592653589793
    const val DEUX_PI = 6.283185307179586
    const val LN2 = 0.6931471805599453

    // ------------------------------------------------------------------ calcul exact
    private fun sinQuart(x: Double): Double {
        val x2 = x * x
        var terme = x
        var s = x
        for (k in 1..10) {
            terme = -terme * x2 / ((2 * k) * (2 * k + 1)).toDouble()
            s = s + terme
        }
        return s
    }

    fun plancher(x: Double): Int {
        val i = x.toInt()
        return if (x < i) i - 1 else i
    }

    fun expo(x0: Double): Double {
        var x = x0
        if (x < -700.0) x = -700.0
        if (x > 700.0) x = 700.0
        var k = plancher(x / LN2 + 0.5)
        val r = x - k * LN2
        var s = 1.0
        var terme = 1.0
        for (j in 1 until 18) {
            terme = terme * r / j
            s = s + terme
        }
        while (k > 0) { val p = minOf(k, 60); s = s * (1L shl p).toDouble(); k -= p }
        while (k < 0) { val p = minOf(-k, 60); s = s / (1L shl p).toDouble(); k += p }
        return s
    }

    fun pow2(x: Double) = expo(x * LN2)
    fun note(n: Int) = 440.0 * pow2((n - 69) / 12.0)

    val SIN: DoubleArray = DoubleArray(N + 1).also { t ->
        val q = N / 4
        for (i in 0..q) t[i] = sinQuart(DEUX_PI * i / N)
        for (i in q + 1..2 * q) t[i] = t[2 * q - i]
        for (i in 2 * q + 1 until N) t[i] = -t[i - 2 * q]
        t[N] = t[0]
    }
    private val tables = HashMap<String, DoubleArray>()
    val PALIERS = intArrayOf(1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 16, 20, 24)

    @Synchronized
    fun table(forme: String, duty: Double, nh: Int): DoubleArray {
        val cle = "$forme/$duty/$nh"
        tables[cle]?.let { return it }
        val out: DoubleArray
        if (forme == "sin") out = SIN.copyOf()
        else {
            val o = DoubleArray(N)
            val f: Double
            when (forme) {
                "tri" -> {
                    var k = 1
                    while (k <= nh) {
                        val c = (if (((k - 1) / 2) % 2 == 0) 1.0 else -1.0) / (k * k)
                        for (i in 0 until N) o[i] = o[i] + c * SIN[(k * i) % N]
                        k += 2
                    }
                    f = 8.0 / (PI * PI)
                }
                "carre" -> {
                    val dd = (duty * N / 2).toInt()
                    for (k in 1..nh) {
                        val c = SIN[(k * dd) % N] / k
                        val q = N / 4
                        for (i in 0 until N) o[i] = o[i] + c * SIN[(k * i + q) % N]
                    }
                    f = 4.0 / PI * 0.5
                }
                "scie" -> {
                    for (k in 1..nh) {
                        val c = 1.0 / k
                        for (i in 0 until N) o[i] = o[i] + c * SIN[(k * i) % N]
                    }
                    f = 2.0 / PI * 0.6
                }
                else -> throw IllegalArgumentException(forme)
            }
            out = DoubleArray(N + 1)
            for (i in 0 until N) out[i] = o[i] * f
            out[N] = out[0]
        }
        tables[cle] = out
        return out
    }

    fun harmoniques(forme: String, fmax: Double): Int {
        val plafond = when (forme) { "tri" -> 15; "carre" -> 24; "scie" -> 20; else -> 1 }
        val kmax = maxOf(1, ((SR / 2.0 - 200) / maxOf(fmax, 20.0)).toInt())
        val k = minOf(kmax, plafond)
        return PALIERS.filter { it <= k }.max()
    }

    /** Petit hasard reproductible (xorshift 32 bits), le même qu'en Python (sons.Alea). */
    class Alea(graine: Long) {
        private var x: Long = ((graine * 2654435761L + 1) and 0xFFFFFFFFL).let { if (it == 0L) 0x9E3779B9L else it }
        fun suivant(): Long {
            var v = x
            v = v xor ((v shl 13) and 0xFFFFFFFFL)
            v = v xor (v ushr 17)
            v = v xor ((v shl 5) and 0xFFFFFFFFL)
            x = v
            return v
        }
        fun hasard(): Double = suivant() / 4294967296.0
        fun entier(a: Int, b: Int): Int = a + (suivant() % (b - a)).toInt()
    }

    fun md5(texte: String): IntArray =
        java.security.MessageDigest.getInstance("MD5").digest(texte.toByteArray(Charsets.UTF_8)).map { it.toInt() and 0xFF }.toIntArray()

    // ------------------------------------------------------------------ briques
    fun bruit(n: Int, graine: Long = 1): DoubleArray {
        val a = Alea(graine)
        return DoubleArray(n) { a.hasard() * 2.0 - 1.0 }
    }

    fun env(n: Int, a0: Double = 0.005, d0: Double = 0.08, s: Double = 0.6, r: Double = 0.08): DoubleArray {
        val a = maxOf(a0, 1e-6)
        val d = maxOf(d0, 1e-6)
        val ir = 1.0 / (maxOf(r, 1e-6) * SR)
        val na = a * SR
        val out = DoubleArray(n)
        var i0 = 0
        while (i0 < n && i0 < na) { out[i0] = i0 / na; i0++ }
        if (i0 < n) {
            var dec = expo(-(i0.toDouble() / SR - a) / d)
            val kd = expo(-1.0 / (SR * d))
            for (i in i0 until n) { out[i] = s + (1.0 - s) * dec; dec = dec * kd }
        }
        for (i in 0 until n) {
            val rel = (n - i) * ir
            if (rel < 1.0) out[i] = out[i] * rel
        }
        return out
    }

    fun osc(forme: String, f0: Double, nb: Int, duty: Double, vib: Double, glis: Double, dur: Double): DoubleArray {
        val gr = if (glis != 0.0) pow2(glis / (12.0 * maxOf(dur, 1e-3) * SR)) else 1.0
        val fmax = f0 * (1.0 + vib) * (if (glis > 0) pow2(glis / 12.0) else 1.0)
        val t = if (forme != "sin") table(forme, duty, harmoniques(forme, fmax)) else SIN
        val out = DoubleArray(nb)
        var ph = 0.0
        if (vib == 0.0 && glis == 0.0) {
            val inc = f0 / SR
            for (i in 0 until nb) {
                ph = ph + inc
                if (ph >= 1.0) ph = ph - 1.0
                val x = ph * N
                val j = x.toInt()
                out[i] = t[j] + (t[j + 1] - t[j]) * (x - j)
            }
            return out
        }
        var g = 1.0
        var vph = 0.0
        val vinc = 5.5 / SR
        for (i in 0 until nb) {
            var x = vph * N
            var j = x.toInt()
            val sv = SIN[j] + (SIN[j + 1] - SIN[j]) * (x - j)
            val f = f0 * (1.0 + vib * sv) * g
            g = g * gr
            vph = vph + vinc
            if (vph >= 1.0) vph = vph - 1.0
            ph = ph + f / SR
            while (ph >= 1.0) ph = ph - 1.0
            x = ph * N
            j = x.toInt()
            out[i] = t[j] + (t[j + 1] - t[j]) * (x - j)
        }
        return out
    }

    fun ton(forme: String, n: Int, dur: Double, vol: Double = 0.3, duty: Double = 0.5, a: Double = 0.005, d: Double = 0.1,
            s: Double = 0.6, r: Double = 0.05, vib: Double = 0.0, glis: Double = 0.0): DoubleArray {
        val nb = (dur * SR).toInt()
        val o = osc(forme, note(n), nb, duty, vib, glis, dur)
        val e = env(nb, a, d, s, r)
        return DoubleArray(nb) { o[it] * e[it] * vol }
    }

    fun sinusAmorti(freq: Double, nb: Int, tau: Double, vol: Double): DoubleArray {
        val k = expo(-1.0 / tau)
        var e = 1.0
        var ph = 0.0
        val inc = freq / SR
        val out = DoubleArray(nb)
        for (i in 0 until nb) {
            val x = ph * N
            val j = x.toInt()
            out[i] = (SIN[j] + (SIN[j + 1] - SIN[j]) * (x - j)) * e * vol
            e = e * k
            ph = ph + inc
            if (ph >= 1.0) ph = ph - 1.0
        }
        return out
    }

    fun amorti(x: DoubleArray, tau: Double, vol: Double): DoubleArray {
        val k = expo(-1.0 / tau)
        var e = 1.0
        val out = DoubleArray(x.size)
        for (i in x.indices) { out[i] = x[i] * e * vol; e = e * k }
        return out
    }

    fun passeBas(x: DoubleArray, fc: Double): DoubleArray {
        val a = expo(-DEUX_PI * fc / SR)
        val b = 1.0 - a
        var acc = 0.0
        val out = DoubleArray(x.size)
        for (i in x.indices) { acc = b * x[i] + a * acc; out[i] = acc }
        return out
    }

    fun passeBasBoucle(x: DoubleArray, fc: Double): DoubleArray = passeBas(x + x, fc).copyOfRange(x.size, 2 * x.size)

    fun echo(x: DoubleArray, ms: Int = 180, fb: Double = 0.3, mix: Double = 0.25, boucle: Boolean = false): DoubleArray {
        val d = (ms * SR / 1000.0).toInt()
        val n = x.size
        val y = x.copyOf()
        var g = mix
        for (k in 1..5) {
            var sh = d * k
            if (boucle) {
                sh %= n
                for (i in 0 until n) y[i] = y[i] + g * x[if (i - sh >= 0) i - sh else i - sh + n]
            } else if (sh < n) {
                for (i in sh until n) y[i] = y[i] + g * x[i - sh]
            }
            g = g * fb
        }
        return y
    }

    fun place(piste: DoubleArray, son: DoubleArray, t: Double, boucle: Boolean = false) {
        val i = (t * SR).toInt()
        val n = piste.size
        val j = minOf(n, i + son.size)
        for (k in i until j) piste[k] += son[k - i]
        if (boucle && i + son.size > n) {
            val debut = if (i < n) n - i else 0
            val lg = son.size - debut
            for (k in 0 until minOf(lg, n)) piste[k] += son[debut + k]
        }
    }

    fun normaliser(x: DoubleArray, crete: Double = 0.5): DoubleArray {
        var m = 0.0
        for (v in x) { if (v > m) m = v else if (-v > m) m = -v }
        if (m == 0.0) m = 1.0
        return DoubleArray(x.size) { x[it] / m * crete }
    }

    fun fondu(x0: DoubleArray, ms: Int = 8): DoubleArray {
        val n = (ms * SR / 1000.0).toInt()
        val x = x0.copyOf()
        for (i in 0 until minOf(20, x.size)) x[i] = x[i] * (i / 19.0)
        val l = x.size
        for (j in 0 until minOf(n, l)) x[l - n + j] = x[l - n + j] * ((n - 1 - j) / (n - 1.0))
        return x
    }

    private fun zeros(n: Int) = DoubleArray(n)
    private fun fois(x: DoubleArray, k: Double) = DoubleArray(x.size) { x[it] * k }

    // ------------------------------------------------------------------ 81. musiques des 9 biomes
    val GAMMES = mapOf(
        "majeur_penta" to intArrayOf(0, 2, 4, 7, 9), "mineur_penta" to intArrayOf(0, 3, 5, 7, 10),
        "dorien" to intArrayOf(0, 2, 3, 5, 7, 9, 10), "lydien" to intArrayOf(0, 2, 4, 6, 7, 9, 11),
        "mixo" to intArrayOf(0, 2, 4, 5, 7, 9, 10), "majeur" to intArrayOf(0, 2, 4, 5, 7, 9, 11),
        "par_tons" to intArrayOf(0, 2, 4, 6, 8, 10), "mineur" to intArrayOf(0, 2, 3, 5, 7, 8, 10))

    class Biome(val tonique: Int, val gamme: String, val bpm: Int, val accords: IntArray, val mel: String, val duty: Double,
                val amb: String, val motif: IntArray)

    val BIOMES = linkedMapOf(
        "feu" to Biome(62, "dorien", 104, intArrayOf(0, 3, 4, 3), "carre", 0.25, "crepit", intArrayOf(1, 1, -1, 3, 1, 3, -1, -1)),
        "eau" to Biome(65, "lydien", 88, intArrayOf(0, 1, 4, 3), "tri", 0.5, "bulles", intArrayOf(-1, -1, 3, 4, 5, 7, 8, 6)),
        "glace" to Biome(64, "mineur_penta", 72, intArrayOf(0, 3, 2, 4), "sin", 0.5, "cloche", intArrayOf(0, 2, 3, 4, -1, 2, 2, 1)),
        "plante" to Biome(67, "majeur_penta", 96, intArrayOf(0, 3, 4, 0), "carre", 0.5, "oiseau", intArrayOf(0, 1, 1, 3, 5, 4, 5, 6)),
        "roche" to Biome(57, "mineur_penta", 84, intArrayOf(0, 2, 3, 2), "tri", 0.5, "bois", intArrayOf(1, 2, -1, -1, -1, -1, 0, -1)),
        "ciel" to Biome(72, "majeur", 70, intArrayOf(0, 3, 5, 4), "sin", 0.5, "souffle", intArrayOf(1, 1, 0, 2, 0, 1, 2, 3)),
        "ombre" to Biome(59, "mineur", 66, intArrayOf(0, 5, 3, 4), "tri", 0.5, "goutte", intArrayOf(0, 1, 3, 4, 5, 4, 5, 4)),
        "machine" to Biome(60, "mixo", 112, intArrayOf(0, 6, 3, 4), "carre", 0.125, "tic", intArrayOf(2, -1, -1, 2, 2, 3, 1, -1)),
        "poison" to Biome(63, "par_tons", 92, intArrayOf(0, 1, 2, 1), "carre", 0.375, "bloup", intArrayOf(0, -1, 0, 1, 2, 0, 0, 0)))

    fun degre(b: Biome, d: Int, octave: Int = 0): Int {
        val g = GAMMES.getValue(b.gamme)
        val l = g.size
        return b.tonique + 12 * (octave + Math.floorDiv(d, l)) + g[Math.floorMod(d, l)]
    }

    fun musiqueBiome(cle: String): DoubleArray {
        val b = BIOMES.getValue(cle)
        val h = md5(cle)
        val al = Alea(((h[0].toLong() shl 24) or (h[1].toLong() shl 16) or (h[2].toLong() shl 8) or h[3].toLong()))
        val noire = 60.0 / b.bpm
        val mesures = 4
        val dur = mesures * 4 * noire
        val piste = zeros((dur * SR).toInt())
        val l = GAMMES.getValue(b.gamme).size
        for ((m, acc) in b.accords.withIndex()) {
            val t0 = m * 4 * noire
            for (k in intArrayOf(0, 2)) {
                val n = degre(b, acc + (if (k == 0) 0 else 4 % l), -2)
                place(piste, ton("tri", n, noire * 1.9, 0.22, d = 0.3, s = 0.5, r = 0.08), t0 + k * noire, true)
            }
            for (k in 0 until 8) {
                val n = degre(b, acc + intArrayOf(0, 2, 4, 2)[k % 4], -1)
                place(piste, ton("carre", n, noire * 0.45, 0.05, duty = 0.25, d = 0.06, s = 0.2), t0 + k * noire / 2, true)
            }
            for ((k, p) in b.motif.withIndex()) {
                if (p < 0) continue
                val p2 = p + (if (m != 3) acc else acc - 1)
                if (m == 3 && k >= 6) continue
                val n = degre(b, p2, 0)
                place(piste, ton(b.mel, n, noire * 0.48, if (b.mel != "sin") 0.13 else 0.18, duty = b.duty,
                    d = 0.12, s = 0.45, vib = if (k % 2 != 0) 0.004 else 0.0), t0 + k * noire / 2, true)
            }
        }
        for (i in 0 until mesures * 4) {
            val t = i * noire
            when {
                b.amb == "crepit" -> for (q in 0 until 2) {
                    val g = al.entier(0, 1000000)
                    val c = amorti(bruit((0.015 * SR).toInt(), g.toLong()), 60.0, 0.12)
                    place(piste, c, t + al.hasard() * noire, true)
                }
                b.amb == "bulles" && i % 2 == 1 ->
                    place(piste, ton("sin", 84 + al.entier(0, 6), 0.07, 0.06, d = 0.03, s = 0.1, glis = 7.0), t + noire / 2, true)
                b.amb == "cloche" && i % 4 == 2 ->
                    place(piste, ton("sin", degre(b, al.entier(0, 5), 2), 0.9, 0.05, d = 0.4, s = 0.0), t, true)
                b.amb == "oiseau" && i % 8 == 5 -> for (j in 0 until 3)
                    place(piste, ton("sin", 91 + j, 0.05, 0.035, glis = 4.0), t + j * 0.07, true)
                b.amb == "bois" ->
                    place(piste, sinusAmorti(380.0, (0.04 * SR).toInt(), 120.0, if (i % 2 == 0) 0.12 else 0.06), t, true)
                b.amb == "souffle" && i == 0 -> {
                    val s = passeBas(bruit((dur * SR).toInt(), 7), 500.0)
                    val l2 = s.size
                    for (j in 0 until l2) {
                        val x = (j.toDouble() / l2) * N
                        val q = x.toInt()
                        val sv = SIN[q] + (SIN[q + 1] - SIN[q]) * (x - q)
                        s[j] = s[j] * 0.25 * (0.5 + 0.5 * sv * sv)
                    }
                    place(piste, s, 0.0, true)
                }
                b.amb == "goutte" && i % 3 == 1 -> {
                    val g = ton("sin", 88 + al.entier(0, 4), 0.06, 0.05, d = 0.02, s = 0.0, glis = -5.0)
                    place(piste, g, t + noire * al.hasard(), true)
                }
                b.amb == "tic" -> {
                    place(piste, amorti(bruit((0.01 * SR).toInt(), i.toLong()), 30.0, 0.08), t, true)
                    place(piste, amorti(bruit((0.01 * SR).toInt(), (i + 99).toLong()), 30.0, 0.04), t + noire / 2, true)
                }
                b.amb == "bloup" && i % 4 == 3 ->
                    place(piste, ton("sin", 50, 0.12, 0.12, d = 0.05, s = 0.2, glis = 12.0), t + noire / 2, true)
            }
        }
        val p2 = passeBasBoucle(piste, 4200.0)
        return normaliser(echo(p2, (noire * 750).toInt(), 0.35, 0.22, true), 0.45)
    }

    // ------------------------------------------------------------------ 82. un cri par espèce
    class Timbre(val forme: String, val duty: Double, val contour: String, val extra: String?)

    val TIMBRE = mapOf(
        "Démons" to Timbre("carre", 0.25, "pique", "crepit"), "Élémentaires" to Timbre("tri", 0.5, "vague", null),
        "Morts-vivants" to Timbre("sin", 0.5, "ouh", "vibrato"), "Bêtes monstrueuses" to Timbre("scie", 0.5, "grogne", null),
        "Sylvestres" to Timbre("tri", 0.5, "flute", "souffle"), "Arthropodes" to Timbre("carre", 0.125, "trille", null),
        "Abyssaux" to Timbre("sin", 0.5, "bulle", null), "Célestes" to Timbre("sin", 0.5, "etoile", "cloche"),
        "Constructs" to Timbre("carre", 0.5, "bipboup", null), "Aberrations" to Timbre("tri", 0.5, "bizarre", "wobble"))
    val AGE = mapOf("bebe" to 5, "enfant" to 3, "ado" to 2)
    val RARES = setOf("rare", "légendaire", "mythique")

    fun taille(cm: Double): Int = if (cm <= 30) 5 else if (cm <= 90) 0 else if (cm <= 220) -5 else -12

    fun cri(eid: String, famille: String, tailleCm: Double, rarete: String, stade: String = "", shiny: Boolean = false,
            glitch: Boolean = false): DoubleArray {
        val h = md5(eid)
        val tb = TIMBRE[famille] ?: TIMBRE.getValue("Constructs")
        val forme = tb.forme; val duty = tb.duty; val contour = tb.contour; val extra = tb.extra
        val base = 69 + taille(tailleCm) + (h[0] % 7) - 3 + (AGE[stade] ?: 0)
        val nbSyll = 1 + h[1] % 3
        val lg = 0.13 + (h[2] % 6) * 0.025
        val sortie = mutableListOf<DoubleArray>()
        for (s in 0 until nbSyll) {
            val n0 = base + intArrayOf(0, 3, -2, 5, 7)[(h[3] + s) % 5]
            val sg = if (s % 2 == 0) 1 else -1
            val (g, v) = when (contour) {
                "pique" -> (5 + h[4] % 5).toDouble() to 0.0
                "vague" -> (sg * 4).toDouble() to 0.01
                "ouh" -> -3.0 to 0.02
                "grogne" -> 2.0 to 0.03
                "flute" -> 1.0 to 0.006
                "trille" -> 0.0 to 0.0
                "bulle" -> (9 + h[4] % 5).toDouble() to 0.0
                "etoile" -> 2.0 to 0.0
                "bipboup" -> 0.0 to 0.0
                else -> ((if ((h[4] + s) % 2 == 0) 1 else -1) * 7).toDouble() to 0.0
            }
            val d = lg * (if (contour == "ouh" || contour == "flute") 1.5 else 1.0)
            var x: DoubleArray = when (contour) {
                "trille" -> {
                    var acc = DoubleArray(0)
                    for (k in 0 until (d / 0.03).toInt() + 2) acc += ton(forme, n0 + (k % 2) * 2, 0.03, 0.3, duty, d = 0.01, s = 0.6, r = 0.008)
                    acc
                }
                "bipboup" -> ton(forme, n0 + (s % 2) * 5, d, 0.3, duty, d = 0.04, s = 0.7, r = 0.02)
                else -> ton(forme, n0, d, 0.35, duty, a = 0.012, d = 0.06, s = 0.65, r = 0.04, vib = v, glis = g)
            }
            if (extra == "wobble") {
                var ph = 0.0
                val inc = 14.0 / SR
                for (i in x.indices) {
                    val q = ph * N
                    val j = q.toInt()
                    x[i] = x[i] * (0.7 + 0.3 * (SIN[j] + (SIN[j + 1] - SIN[j]) * (q - j)))
                    ph = ph + inc
                    if (ph >= 1.0) ph = ph - 1.0
                }
            }
            if (extra == "cloche" && x.size <= (d * 1.6 * SR).toInt()) {
                val c = ton("sin", n0 + 19, d * 1.6, 0.08, d = 0.08, s = 0.0)
                x = DoubleArray(x.size) { x[it] + c[it] }
            }
            if (extra == "souffle") {
                val b = passeBas(bruit(x.size, h[5].toLong()), 1500.0)
                val e = env(x.size, 0.02, 0.05, 0.4, 0.03)
                x = DoubleArray(x.size) { x[it] + b[it] * e[it] * 0.12 }
            }
            if (extra == "crepit") {
                val n = minOf((0.012 * SR).toInt(), x.size)
                val b = bruit((0.012 * SR).toInt(), h[6].toLong())
                for (i in 0 until n) x[i] = x[i] + b[i] * 0.15
            }
            if (contour == "grogne") x = fois(passeBas(x, 1400.0), 1.6)
            sortie.add(x)
            sortie.add(zeros(((0.025 + (h[7] % 3) * 0.02) * SR).toInt()))
        }
        var x = DoubleArray(0)
        for (p in sortie.dropLast(1)) x += p
        if (rarete in RARES || shiny) {
            x += zeros((0.02 * SR).toInt())
            place(x, ton("sin", base + 24, 0.12, 0.07, d = 0.05, s = 0.0), maxOf(0.0, x.size.toDouble() / SR - 0.14))
            if (shiny && rarete in RARES) {
                x += zeros((0.06 * SR).toInt())
                place(x, ton("sin", base + 31, 0.12, 0.06, d = 0.05, s = 0.0), maxOf(0.0, x.size.toDouble() / SR - 0.13))
            }
        }
        x = passeBas(x, 5000.0)
        x = fondu(normaliser(echo(x, 70, 0.2, 0.12), 0.42), 5)
        if (glitch) x = glitcher(x, (h[8] + 256 * h[9]).toLong())
        return x
    }

    // ------------------------------------------------------------------ 83. réussite et erreur
    fun suite(notes: IntArray, forme: String = "carre", duty: Double = 0.5, vol: Double = 0.3, ecart: Double = 0.08,
              lg: Double = 0.12, d: Double = 0.1, s: Double = 0.6): DoubleArray {
        val x = zeros(((ecart * notes.size + lg + 0.4) * SR).toInt())
        for ((i, n) in notes.withIndex()) place(x, ton(forme, n, lg, vol, duty, d = d, s = s), i * ecart)
        return x
    }

    fun sonRetour(nom: String): DoubleArray {
        val x: DoubleArray = when (nom) {
            "reussite_petite" -> suite(intArrayOf(79, 84), "carre", 0.25, ecart = 0.07, lg = 0.09, d = 0.05, s = 0.4)
            "reussite_etape" -> suite(intArrayOf(72, 76, 79, 84), "carre", 0.25, ecart = 0.075, lg = 0.14, d = 0.07, s = 0.5)
            "reussite_grande" -> suite(intArrayOf(72, 76, 79, 84, 88, 91), "carre", 0.25, ecart = 0.07, lg = 0.16, d = 0.08, s = 0.5).also {
                place(it, ton("tri", 48, 0.7, 0.25, d = 0.3, s = 0.4), 0.0)
                place(it, ton("sin", 96, 0.4, 0.08, d = 0.2, s = 0.0), 0.42)
            }
            "erreur_douce" -> suite(intArrayOf(71, 67), "tri", ecart = 0.12, lg = 0.14, vol = 0.25, d = 0.08, s = 0.5)
            "erreur_presque" -> suite(intArrayOf(69, 67, 69), "sin", ecart = 0.09, lg = 0.1, vol = 0.25, d = 0.05, s = 0.5)
            "refus_doux" -> {
                val t = sinusAmorti(520.0, (0.06 * SR).toInt(), 160.0, 0.35)
                t + zeros((0.07 * SR).toInt()) + fois(t, 0.6) + zeros((0.1 * SR).toInt())
            }
            else -> throw NoSuchElementException(nom)
        }
        val crete = if (nom.startsWith("reussite")) 0.4 else 0.3
        return fondu(normaliser(echo(passeBas(x, 5000.0), 90, 0.25, 0.15), crete))
    }

    // ------------------------------------------------------------------ 86. thème des gardiens
    val GARDIENS = listOf(Triple("enumeration", "ricanombre", 0), Triple("droits", "heaumbre", 2), Triple("secrets", "cranard", 3),
        Triple("hangar", "ombrachne", 5), Triple("scripts", "marionnoire", 7), Triple("codes", "torsillon", 8),
        Triple("forensique", "osselet", 10), Triple("social", "drapouille", 12))
    val LEITMOTIV = intArrayOf(0, 3, 7, 6, 3, 2, 0, -2)

    fun themeGardiens(): DoubleArray {
        val noire = 60.0 / 80
        val dur = 16 * noire * 2
        val x = zeros((dur * SR).toInt())
        val base = 64
        val accords = arrayOf(intArrayOf(0, 3, 7), intArrayOf(-4, 0, 3), intArrayOf(-7, -4, 0), intArrayOf(-1, 3, 6))
        for (m in 0 until 8) {
            val a = accords[m % 4]
            val t0 = m * 4 * noire
            place(x, ton("tri", base - 24 + a[0], 4 * noire * 0.98, 0.25, d = 1.0, s = 0.6, r = 0.2), t0, true)
            for (k in 0 until 8)
                place(x, ton("carre", base - 12 + a[k % 3], noire * 0.3, 0.05, 0.125, d = 0.05, s = 0.2), t0 + k * noire / 2, true)
            if (m in setOf(0, 1, 4, 5)) for ((k, iv0) in LEITMOTIV.withIndex()) {
                var iv = iv0
                if (m % 2 == 1 && k >= 4) iv = LEITMOTIV[k] - 2
                place(x, ton("carre", base + iv, noire * 0.45, 0.13, 0.25, d = 0.12, s = 0.5, vib = 0.004), t0 + k * noire / 2, true)
            }
            if (m in setOf(2, 3, 6, 7)) for ((k, iv) in intArrayOf(7, 6, 3, 0).withIndex())
                place(x, ton("sin", base + 12 + iv, noire * 0.95, 0.12, d = 0.3, s = 0.4, vib = 0.006), t0 + k * noire, true)
        }
        return normaliser(echo(passeBasBoucle(x, 3800.0), (noire * 750).toInt(), 0.35, 0.25, true), 0.45)
    }

    fun motifGardien(i: Int): DoubleArray {
        val formes = arrayOf("carre", "tri", "sin", "scie", "carre", "tri", "sin", "carre")
        val duty = doubleArrayOf(0.25, 0.5, 0.5, 0.5, 0.125, 0.5, 0.5, 0.375)[i]
        val base = 60 + GARDIENS[i].third % 12
        val x = zeros((2.6 * SR).toInt())
        for (k in 0 until 5) place(x, ton(formes[i], base + LEITMOTIV[k], 0.28, 0.25, duty, d = 0.1, s = 0.5, vib = 0.005), k * 0.22)
        place(x, ton("tri", base - 12, 1.4, 0.25, d = 0.6, s = 0.3), 0.0)
        place(x, ton("sin", base + 19, 0.8, 0.08, d = 0.3, s = 0.0), 1.1)
        return fondu(normaliser(echo(passeBas(x, 4200.0), 200, 0.35, 0.25), 0.42))
    }

    fun glitcher(x: DoubleArray, graine: Long = 5): DoubleArray {
        val al = Alea(graine)
        val y = x.copyOf()
        val n = x.size
        for (q in 0 until 6) {
            val i = al.entier(0, maxOf(1, n - 4000))
            val lg = al.entier(400, 1400)
            val frag = x.copyOfRange(i, minOf(n, i + lg))
            val rep = al.entier(2, 4)
            for (r in 0 until rep) {
                val j = i + r * lg
                if (j + lg < n) System.arraycopy(frag, 0, y, j, frag.size)
            }
        }
        for (k in y.indices) y[k] = plancher(y[k] * 24 + 0.5) / 24.0
        return fondu(normaliser(passeBas(y, 4500.0), 0.4))
    }

    // ------------------------------------------------------------------ le catalogue
    val RETOURS = listOf("reussite_petite", "reussite_etape", "reussite_grande", "erreur_douce", "erreur_presque", "refus_doux")
    val ALIAS = mapOf("evolution" to "reussite_grande", "palier" to "reussite_grande", "nouvelle_creature" to "reussite_grande",
        "etape" to "reussite_etape", "exploit" to "reussite_grande", "erreur" to "erreur_douce", "presque" to "erreur_presque",
        "refus" to "refus_doux", "reussite" to "reussite_petite")
    val STADES = setOf("bebe", "enfant", "ado", "adulte", "ancien")

    fun vrai(nom: String) = ALIAS[nom] ?: nom

    fun categorie(nom0: String): String {
        val nom = vrai(nom0)
        return when {
            nom.startsWith("biome_") || nom == "gardiens_theme" -> "musique"
            nom.startsWith("cri:") || nom.startsWith("gardien_") -> "cris"
            else -> "retours"
        }
    }

    fun fabriquer(nom0: String): DoubleArray {
        val nom = vrai(nom0)
        if (nom in RETOURS) return sonRetour(nom)
        if (nom.startsWith("biome_") && nom.substring(6) in BIOMES) return musiqueBiome(nom.substring(6))
        if (nom == "gardiens_theme") return themeGardiens()
        if (nom == "gardien_glitch") return glitcher(motifGardien(0))
        if (nom.startsWith("gardien_")) {
            val i = GARDIENS.indexOfFirst { it.second == nom.substring(8) }
            if (i >= 0) return motifGardien(i)
        }
        if (nom.startsWith("cri:")) {
            val p = nom.split(":")
            val e = Bestiaire.especes.firstOrNull { it.id == p[1] }
            return cri(p[1], e?.famille ?: "", e?.tailleCm ?: 90.0, e?.rarete ?: "",
                p.drop(2).firstOrNull { it in STADES } ?: "", "shiny" in p.drop(2), "glitch" in p.drop(2))
        }
        throw NoSuchElementException(nom)
    }

    fun pcm(x: DoubleArray): ShortArray = ShortArray(x.size) {
        val s = plancher(x[it] * 32767.0 + 0.5)
        (if (s > 32767) 32767 else if (s < -32767) -32767 else s).toShort()
    }

    private val cache = LinkedHashMap<String, ShortArray>()

    fun echantillons(nom0: String): ShortArray {
        val nom = vrai(nom0)
        synchronized(cache) { cache[nom]?.let { return it } }
        val e = pcm(fabriquer(nom))
        synchronized(cache) {
            cache[nom] = e
            if (cache.size > 40) cache.keys.filter { !it.startsWith("biome_") && !it.startsWith("gardiens_") }.take(10).forEach { cache.remove(it) }
        }
        return e
    }

    fun enCache(nom: String): ShortArray? = synchronized(cache) { cache[vrai(nom)] }

    fun nomCri(eid: String, stade: String = "", shiny: Boolean = false, glitch: Boolean = false) =
        "cri:" + eid + (if (stade.isNotEmpty()) ":$stade" else "") + (if (shiny) ":shiny" else "") + (if (glitch) ":glitch" else "")

    // ------------------------------------------------------------------ réglages et permissions (mêmes règles en Python)
    val DEFAUTS = linkedMapOf<String, Any>("on" to false, "musique" to false, "v_musique" to 30, "v_cris" to 60, "v_retours" to 50,
        "soir" to "", "demande" to false, "n" to 0)
    const val NUIT_DEBUT = 20 * 60 + 30
    const val NUIT_FIN = 7 * 60 + 30

    fun reglages(jeu: Jeu): JSONObject {
        val r = jeu.module("son")
        for ((k, v) in DEFAUTS) if (!r.has(k)) r.put(k, v)
        return r
    }

    fun soiree(annee: Int, mois: Int, jour: Int, minutes: Int): String {
        if (minutes in NUIT_FIN until NUIT_DEBUT) return ""
        var d = java.time.LocalDate.of(annee, mois, jour)
        if (minutes < NUIT_FIN) d = d.minusDays(1)
        return "%04d-%02d-%02d".format(d.year, d.monthValue, d.dayOfMonth)
    }

    fun permis(r: JSONObject, cat: String, annee: Int, mois: Int, jour: Int, minutes: Int, classe: Boolean = false, dort: Boolean = false): Boolean {
        if (!r.optBoolean("on") || classe) return false
        if (cat == "musique" && !r.optBoolean("musique")) return false
        if (r.optInt("v_$cat", 0) <= 0) return false
        val s = soiree(annee, mois, jour, minutes)
        if (s.isNotEmpty() && r.optString("soir") != s) return false
        if (cat == "cris" && dort) return false
        return true
    }

    fun maintenant(ms: Long = System.currentTimeMillis()): IntArray {
        val c = java.util.Calendar.getInstance().apply { timeInMillis = ms }
        return intArrayOf(c.get(java.util.Calendar.YEAR), c.get(java.util.Calendar.MONTH) + 1, c.get(java.util.Calendar.DAY_OF_MONTH),
            c.get(java.util.Calendar.HOUR_OF_DAY) * 60 + c.get(java.util.Calendar.MINUTE))
    }

    /** le mode classe (l'espace en grand écran pour la classe) coupe tout */
    fun classe(jeu: Jeu): Boolean = jeu.module("espace").optBoolean("classe")

    private fun dort(jeu: Jeu): Boolean = jeu.anim?.let { it.first == "dort" && System.currentTimeMillis() - it.second < 30_000 } ?: false

    fun peut(jeu: Jeu, nom: String): Boolean {
        val m = maintenant()
        return permis(reglages(jeu), categorie(nom), m[0], m[1], m[2], m[3], classe(jeu), dort(jeu))
    }

    fun volume(jeu: Jeu, nom: String): Int = reglages(jeu).optInt("v_" + categorie(nom), 0).coerceIn(0, 100)

    // ------------------------------------------------------------------ quel son après un tour de jeu
    class Resume(val lecon: Int, val etape: Int, val niveau: Int, val stade: Int, val exploits: Int, val collection: Int, val total: Int)

    fun resume(jeu: Jeu): Resume = Resume(jeu.lecon, jeu.etape, jeu.niveau, jeu.stade,
        Recompenses.etat(jeu).getJSONObject("exploits").length(), Explo.collection(jeu).length(), jeu.total)

    /** (nom du son ou "", nouveau compteur) : au plus un son de retour par tour (même règle que sons.choisir). */
    fun choisir(avant: Resume?, apres: Resume?, marque: String = "", n0: Int = 0): Pair<String, Int> {
        var n = n0
        if (avant == null || apres == null) return "" to n
        if (apres.stade > avant.stade) return (if (avant.stade == 0) "eclosion" else "evolution") to n
        if (apres.exploits > avant.exploits || apres.collection > avant.collection || apres.niveau > avant.niveau) return "reussite_grande" to n
        if (apres.lecon != avant.lecon || apres.etape != avant.etape) return "reussite_etape" to n
        if (marque in setOf("erreur_douce", "erreur_presque", "refus_doux")) return marque to n
        if (apres.total > avant.total) {
            n += 1
            return (if (n % 3 == 0) "reussite_petite" else "") to n % 3
        }
        return "" to n
    }

    /** Le son d'une bestiole qui apparaît (même règle que sons.nom_apparition) : le motif du gardien (qui bégaie s'il
     *  est glitch), sinon son cri si l'espèce est nouvelle, sinon rien. */
    fun nomApparition(eid: String, ind: JSONObject?, nouvelle: Boolean): String {
        val b = ind?.optString("gardien").orEmpty()
        if (b.isNotEmpty()) {
            if (ind?.optBoolean("glitch") == true) return "gardien_glitch"
            return GARDIENS.firstOrNull { it.first == b }?.let { "gardien_" + it.second } ?: ""
        }
        if (nouvelle && eid.isNotEmpty()) return nomCri(eid, "", ind?.optBoolean("shiny") == true, ind?.optBoolean("glitch") == true)
        return ""
    }

    /** Explo.spawn : une bestiole vient d'apparaître (rencontre). */
    fun apparition(jeu: Jeu, e: Bestiaire.Espece, ind: JSONObject) {
        try {
            val nom = nomApparition(e.id, ind, Explo.collection(jeu).optInt(e.nom) == 0)
            if (nom.isNotEmpty()) son(jeu, nom)
        } catch (x: Exception) { }
    }

    /** la marque d'erreur du tour en cours (commande inconnue, presque, refusée), posée avant le tour de jeu */
    var marque = ""

    fun marquer(nom: String) { if (marque.isEmpty()) marque = nom }

    /** Appelé après le tour de jeu (TerminalActivity) : le son de retour, s'il y en a un ; renvoie la question à poser
     *  (« Tu veux m'entendre ? ») à la première éclosion, sinon null. */
    fun apresTour(jeu: Jeu, avant: Resume, apres: Resume, code: Int?): String? {
        val m = marque.ifEmpty { if (code != null && code != 0) "refus_doux" else "" }
        marque = ""
        return try {
            val r = reglages(jeu)
            val (nom, n) = choisir(avant, apres, m, r.optInt("n"))
            r.put("n", n)
            var question: String? = null
            if (nom == "eclosion") {
                if (!r.optBoolean("demande")) { r.put("demande", true); question = t("son.question.terminal", "nom" to jeu.nom) }
                val e = jeu.especeCompagnon
                son(jeu, if (e != null) nomCri(e, "bebe", jeu.shiny) else "reussite_grande")
            } else if (nom.isNotEmpty()) son(jeu, nom)
            question
        } catch (x: Exception) { null }
    }

    // ------------------------------------------------------------------ jouer
    val JOURNAL = mutableListOf<String>()

    /** Le point d'entrée des autres modules : Sons.son(jeu, "evolution"). Ne lève jamais d'erreur, ne bloque jamais. */
    private val derniers = HashMap<String, Long>()

    /** la partie ouverte dans le terminal (pour Sons.son(nom) sans partie, appelé par les autres modules) */
    @Volatile var courant: Jeu? = null

    /** Sons.son("evolution", ctx) : même chose, avec la partie ouverte (Creature.son le trouve par son nom). */
    fun son(nom: String, ctx: android.content.Context?): Boolean {
        val j = courant ?: (try { ctx?.let { Jeu(it) } } catch (x: Exception) { null }) ?: return false
        return son(j, nom)
    }

    fun son(jeu: Jeu, nom0: String): Boolean = try {
        val nom = vrai(nom0)
        val now = System.currentTimeMillis()
        if (!peut(jeu, nom)) false
        else if (now - (synchronized(derniers) { derniers[nom] } ?: 0L) < 3000) true   // pas deux fois le même en 3 s
        else {
            synchronized(derniers) { derniers[nom] = now }
            synchronized(JOURNAL) { JOURNAL.add(nom); while (JOURNAL.size > 50) JOURNAL.removeAt(0) }
            SonsLecteur.jouer(nom, volume(jeu, nom))
            true
        }
    } catch (x: Exception) { false }

    /** La boucle d'une vue Monde / Espace (cle : un biome, « gardiens », ou null), si les réglages le permettent. */
    fun musique(jeu: Jeu, cle: String?): String? {
        val nom = when { cle.isNullOrEmpty() -> null; cle == "gardiens" -> "gardiens_theme"; else -> "biome_$cle" } ?: return null
        if (nom.startsWith("biome_") && nom.substring(6) !in BIOMES) return null
        return if (peut(jeu, nom)) nom else null
    }

    /** Quelle boucle pour une vue (même règle que sons.cle_musique) : rien hors des vues Monde / Espace ; le thème des
     *  gardiens pendant une rencontre de gardien ; sinon la musique du biome. */
    fun cleMusique(vue: Boolean, gardien: Boolean, biome: String?): String? =
        if (!vue) null else if (gardien) "gardiens" else biome?.ifEmpty { null }

    /** Appelé régulièrement par le terminal quand l'espace (Monde, Espace) est ouvert ou fermé. */
    fun suivre(jeu: Jeu, vue: Boolean) {
        try {
            val gardien = jeu.module("dressage").optJSONObject("en_cours")?.optJSONObject("ind")?.has("gardien") == true
            val biome = jeu.especeCompagnon?.let { Bestiaire.especes.firstOrNull { e -> e.id == it } }?.let { Guide.typeDe(it) }
            jouerMusique(jeu, cleMusique(vue, gardien, biome))
        } catch (x: Exception) { }
    }

    /** Les lignes du petit menu « Réglages > Son » du téléphone (texte, action) : chaque toucher fait un pas. */
    fun menu(jeu: Jeu): List<Pair<String, String>> {
        val r = reglages(jeu)
        val oui = t("son.allume"); val non = t("son.eteint")
        return listOf(t("son.etat.titre", "etat" to if (r.optBoolean("on")) oui else non) to "on",
            t("son.etat.musique", "v" to r.optInt("v_musique"), "etat" to if (r.optBoolean("musique")) oui else non).trim() to "musique",
            t("son.etat.cris", "v" to r.optInt("v_cris")).trim() to "cris",
            t("son.etat.retours", "v" to r.optInt("v_retours")).trim() to "retours",
            t("son.etat.nuit").trim() to "soir")
    }

    val PAS = intArrayOf(0, 15, 30, 50, 70, 100)

    /** Un toucher dans « Réglages > Son » : allumer / éteindre, ou le volume suivant (0, 15, 30, 50, 70, 100 %). */
    fun toucher(jeu: Jeu, quoi: String): String {
        val r = reglages(jeu)
        fun suivant(v: Int) = PAS.firstOrNull { it > v } ?: 0
        return when (quoi) {
            "on" -> commande(jeu, if (r.optBoolean("on")) "non" else "oui")
            "musique" -> if (!r.optBoolean("musique")) commande(jeu, "musique oui")
                else suivant(r.optInt("v_musique")).let { if (it == 0) commande(jeu, "musique non").also { r.put("v_musique", 15) } else commande(jeu, "musique $it") }
            "cris", "retours" -> commande(jeu, "$quoi ${suivant(r.optInt("v_$quoi"))}")
            "soir" -> commande(jeu, "soir")
            else -> ""
        }
    }

    /** La vue Monde / Espace demande sa musique (null : silence). */
    fun jouerMusique(jeu: Jeu, cle: String?) {
        try {
            val nom = musique(jeu, cle)
            SonsLecteur.musique(nom, reglages(jeu).optInt("v_musique", 30))
        } catch (x: Exception) { }
    }

    // ------------------------------------------------------------------ son …
    private fun ouiNon(m: String?): Boolean? = when (m?.lowercase()) {
        "oui", "on", "yes", "o", "y", "1" -> true; "non", "off", "no", "n", "0" -> false; else -> null }

    fun lignesEtat(jeu: Jeu): List<String> {
        val r = reglages(jeu)
        val oui = t("son.allume"); val non = t("son.eteint")
        val out = mutableListOf(t("son.etat.titre", "etat" to if (r.optBoolean("on")) oui else non),
            t("son.etat.musique", "v" to r.optInt("v_musique"), "etat" to if (r.optBoolean("musique")) oui else non),
            t("son.etat.cris", "v" to r.optInt("v_cris")), t("son.etat.retours", "v" to r.optInt("v_retours")))
        val m = maintenant()
        val s = soiree(m[0], m[1], m[2], m[3])
        out.add(if (s.isNotEmpty() && r.optString("soir") == s) t("son.etat.nuit.soir") else t("son.etat.nuit"))
        if (classe(jeu)) out.add(t("son.etat.classe"))
        out.add(t("son.etat.aide"))
        return out
    }

    fun commande(jeu: Jeu, reste: String): String {
        val r = reglages(jeu)
        val a = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.map { it.lowercase() }
        if (a.isEmpty()) return lignesEtat(jeu).joinToString("\n")
        val mot = a[0]
        ouiNon(mot)?.let { on ->
            r.put("on", on); r.put("demande", true)
            if (on) son(jeu, "reussite_petite")
            return if (on) t("son.ok.on") else t("son.ok.off")
        }
        val cats = mapOf("musique" to "musique", "music" to "musique", "cris" to "cris", "cri" to "cris", "voix" to "cris",
            "retours" to "retours", "reussites" to "retours", "réussites" to "retours", "effets" to "retours",
            "cries" to "cris", "feedback" to "retours")
        cats[mot]?.let { cat ->
            val v = a.getOrNull(1) ?: ""
            val o = ouiNon(v)
            if (cat == "musique" && o != null) {
                r.put("musique", o)
                if (o) r.put("on", true)
                return if (o) t("son.ok.musique.on") else t("son.ok.musique.off")
            }
            val chiffres = v.trimEnd('%')
            if (chiffres.isNotEmpty() && chiffres.all { it.isDigit() }) {
                r.put("v_$cat", chiffres.take(4).toInt().coerceIn(0, 100))
                if (cat == "musique" && r.optInt("v_musique") > 0) r.put("musique", true)
                return t("son.ok.volume", "cat" to t("son.cat.$cat"), "v" to r.optInt("v_$cat"))
            }
            if (o != null) {
                r.put("v_$cat", if (o) DEFAUTS.getValue("v_$cat") as Int else 0)
                return t("son.ok.volume", "cat" to t("son.cat.$cat"), "v" to r.optInt("v_$cat"))
            }
            return t("son.aide.$cat")
        }
        if (mot in setOf("soir", "ce-soir", "cesoir", "tonight")) {
            val m = maintenant()
            val s = soiree(m[0], m[1], m[2], m[3])
            if (s.isEmpty()) return t("son.soir.jour")
            r.put("soir", s); r.put("on", true)
            return t("son.soir.ok")
        }
        if (mot in setOf("essai", "essaie", "test")) {
            var quoi = a.getOrNull(1) ?: "reussite_etape"
            if (quoi == "cri") quoi = jeu.especeCompagnon?.let { nomCri(it) } ?: "reussite_etape"
            if (!r.optBoolean("on")) return t("son.essai.eteint")
            return if (son(jeu, quoi)) t("son.essai.ok") else t("son.essai.pas_maintenant")
        }
        return lignesEtat(jeu).joinToString("\n")
    }

    private fun t(cle: String, vararg p: Pair<String, Any?>) = Langue.t(cle, "cmd" to "son", *p)
}
