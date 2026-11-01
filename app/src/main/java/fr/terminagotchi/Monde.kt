package fr.terminagotchi

import java.io.File
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Le monde des biomes : la GÉNÉRATION COMMUNE (relief, disposition des régions, chemins et ponts), même règle que
 * pc/tg/monde_gen.py et site/src/monde_gen.js (vecteurs communs donnees/monde/vecteurs.json, tests/jvm/Monde.kt).
 * Porté du prototype « Monde Terminagotchi » v4 ; dessiné par MondeDessin.kt (le VRAI terrain, en lecture seule) :
 *   biome/<type>/  une région ; biome/<type>/parcelle_<n>/  une parcelle (fleur de 19 hexagones) ; ses fichiers : des objets.
 */
object Monde {
    val TYPES = listOf("feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")
    const val MAX_PARCELLES = 8
    const val MAX_OBJETS = 18
    const val HR = 14.0
    const val TILT = 0.62
    const val HZ = 5.0
    val SQ3 = sqrt(3.0)
    val HH = HR * sin(Math.PI / 3) * TILT
    val FLOWER: List<IntArray> = buildList {
        for (q in -2..2) for (r in -2..2) if (abs(q) + abs(r) + abs(q + r) <= 4) add(intArrayOf(q, r))
    }
    val DIRS = listOf(intArrayOf(1, 0), intArrayOf(1, -1), intArrayOf(0, -1), intArrayOf(-1, 0), intArrayOf(-1, 1), intArrayOf(0, 1))
    val DIR_EDGE = listOf(intArrayOf(0, 1), intArrayOf(5, 0), intArrayOf(4, 5), intArrayOf(3, 4), intArrayOf(2, 3), intArrayOf(1, 2))
    val SCEN_BLOCK = setOf("chene", "sapin", "sapin_neige", "bouleau", "cerisier", "rocher", "rocher_volc", "tombe", "tuyau",
        "engrenage", "cristal", "colonne")
    private val LIQUIDES = setOf("eau", "lave", "toxique")
    private val AQUA_DECO = setOf("corail", "algues", "bulles", "roseau", "coquillage")
    private val MN6 = listOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1), intArrayOf(-1, 1), intArrayOf(1, -1))
    private val ANG = mapOf("roche" to 0, "feu" to 48, "machine" to 100, "ombre" to 150, "poison" to 192, "eau" to 236,
        "glace" to 282, "ciel" to 322)
    private val ORDRE = listOf("plante", "roche", "feu", "machine", "ombre", "poison", "eau", "glace", "ciel")
    private val RX_PARCELLE = Regex("parcelle[_-]?(\\d+)", RegexOption.IGNORE_CASE)

    // ------------------------------------------------------------ hasard reproductible (FNV-1a, mulberry32)
    fun hachage(s: String): Long {
        var h = 2166136261L.toInt()
        for (c in s) { h = h xor c.code; h *= 16777619 }
        return h.toLong() and 0xFFFFFFFFL
    }

    fun hasard(graine: Long): () -> Double {
        var a = graine.toInt()
        return {
            a += 0x6D2B79F5
            var t = (a xor (a ushr 15)) * (1 or a)
            t = (t + (t xor (t ushr 7)) * (61 or t)) xor t
            ((t xor (t ushr 14)).toLong() and 0xFFFFFFFFL).toDouble() / 4294967296.0
        }
    }

    fun rnd(s: String) = hasard(hachage(s))()
    fun arrondi(x: Double, n: Double = 1000.0) = floor(x * n + 0.5) / n
    fun <T> melanger(xs: List<T>, r: () -> Double): List<T> {
        val l = xs.toMutableList()
        for (i in l.size - 1 downTo 1) { val j = (r() * (i + 1)).toInt(); val x = l[i]; l[i] = l[j]; l[j] = x }
        return l
    }
    private fun <T> choisir(xs: List<T>, r: () -> Double) = xs[(r() * xs.size).toInt()]
    fun anneau(q: Int, r: Int) = (abs(q) + abs(r) + abs(q + r)) / 2

    class Scen(val k: String, val s: Double)
    class Cell(var kind: String, var h: Double, val v: Int, val d: Int, val flow: Int? = null, val crater: Int = 0,
               val float: Int = 0, val machine: Int = 0, var block: Boolean = false, var scen: Scen? = null)

    // ------------------------------------------------------------ une parcelle
    fun genParcelle(tid: String, nom: String, volcan: Boolean = false, laveDir: Int = 0): LinkedHashMap<String, Cell> {
        val r = hasard(hachage("$tid:$nom"))
        val out = LinkedHashMap<String, Cell>()
        val pool = r() < .6
        val s1 = r() * 6
        val s2 = r() * 6
        val ring2 = mutableListOf<String>(); val ring1 = mutableListOf<String>()
        for (f in FLOWER) {
            val q = f[0]; val r_ = f[1]
            val d = anneau(q, r_)
            val k = "$q,$r_"
            var kind = "herbe"; var h = 2.0
            var flow: Int? = null; var crater = 0; var float = 0; var machine = 0
            when (tid) {
                "feu" -> if (volcan) {
                    val dq = DIRS[laveDir][0]; val dr = DIRS[laveDir][1]
                    val ch1 = q == dq && r_ == dr; val ch2 = q == 2 * dq && r_ == 2 * dr
                    if (d == 0) { kind = "lave"; h = 8.2; crater = 1; flow = 0 }
                    else if (d == 1) { kind = if (ch1) "lave" else "cone"; h = if (ch1) 8.4 else 9.8 + ((q * 3 + r_) and 1) * .8; if (ch1) flow = 1 }
                    else { kind = if (ch2) "lave" else if (r() < .35) "cendre" else "cone"; h = if (ch2) 6.4 else 6.8 + r() * .5; if (ch2) flow = 2 }
                } else {
                    kind = if (pool && d == 0) "lave" else if (r() < .25) "cendre" else "basalte"
                    h = if (kind == "lave") 1.5 else 2.2 + r() * .6
                    if (kind == "lave") flow = 0
                }
                "eau" -> { kind = if (!pool && d == 0) "sable" else "eau"; h = if (kind == "sable") 1.3 else .55 }
                "glace" -> {
                    val cliff = ((q * 2 + r_ * 3 + floor(s1 + .5).toInt()) % 5 + 5) % 5 == 0 && d > 0
                    kind = if (pool && d == 0) "glace" else if (cliff) "glace" else "neige"
                    h = if (pool && d == 0) 2.4 else if (cliff) 4.9 else 3 + (if (d == 1) .4 else 0.0)
                }
                "plante" -> {
                    kind = if (r() < .25) "fleurs" else if (r() < .4) "sombre" else "herbe"
                    h = 2 + .55 * sin(q * 1.3 + s1) + .45 * cos(r_ * 1.1 + s2)
                }
                "roche" -> {
                    val trail = (q == 1 && r_ == 0) || (q == 2 && r_ == -1) || (q == 1 && r_ == -1)
                    if (d == 0) { kind = "neige"; h = 9.8 }
                    else if (d == 1) { h = if (trail) 7.2 else 6.8 + r() * 1.8; kind = if (h > 7.9) "neige" else "pierre" }
                    else { h = if (trail) 4.8 else 3.6 + r() * 1.6; kind = if (h > 4.6) "pierre" else if (r() < .5) "gres" else "sable" }
                }
                "ciel" -> {
                    var sector = 0
                    if (d != 0) {
                        val a = atan2(r_ + q / 2.0, q * SQ3 / 2)
                        sector = 1 + floor(arrondi((a + Math.PI) / (Math.PI * 2), 1e6) * 3).toInt() % 3
                    }
                    h = doubleArrayOf(6.2, 4.4, 7.4, 5.4)[sector] + (r() - .5) * .5
                    kind = if (r() < .2) "orage" else "nuage"
                    float = 1
                }
                "ombre" -> { kind = if (d == 0) "crypte" else if (r() < .35) "violette" else "dalle"; h = if (d == 0) .7 else 2 + (if (d == 1) 0.0 else .3) }
                "machine" -> { kind = if (r() < .25) "grille" else if (r() < .15) "rouille" else "metal"; h = 3 + (if (d == 1 && r() < .35) .6 else 0.0); machine = 1 }
                "poison" -> { val tox = (pool && d == 0) || (d == 1 && r() < .25); kind = if (tox) "toxique" else "vase"; h = if (kind == "toxique") .65 else 1.2 + r() * .3 }
            }
            out[k] = Cell(kind, arrondi(h), (r() * 4).toInt(), d, flow, crater, float, machine)
            if (d == 2) ring2.add(k); if (d == 1) ring1.add(k)
        }
        fun scen(cands: List<String>, keys: List<String>, n: Int) {
            for (k in melanger(cands, r).take(n)) out.getValue(k).scen = Scen(choisir(keys, r), arrondi(.85 + r() * .45))
        }
        if (tid == "plante") scen(ring2, listOf("chene", "sapin", "bouleau", "chene", "cerisier"), 5)
        if (tid == "glace") scen(ring2, listOf("sapin_neige", "cristal"), 2)
        if (tid == "roche") scen(ring2, listOf("rocher"), 2)
        if (tid == "machine") scen(ring2, listOf("tuyau", "engrenage"), 2)
        if (tid == "poison") scen(ring2.filter { out.getValue(it).kind == "vase" }, listOf("roseau", "champi_tox"), 3)
        if (tid == "eau") scen(ring1, listOf("corail", "algues"), 2)
        if (tid == "ombre") {
            for (k in melanger(ring2, r).take(2)) { val c = out.getValue(k); c.kind = "fleche"; c.h = arrondi(8.5 + r() * 2); c.block = true }
            scen(ring2.filter { out.getValue(it).kind != "fleche" }, listOf("tombe"), 1)
        }
        if (tid == "feu" && !volcan) scen(ring2, listOf("braises", "rocher_volc"), 2)
        return out
    }

    // ------------------------------------------------------------ les objets → décor
    private val FLEURS = linkedMapOf("rose" to "#ff3d5a", "tulipe" to "#ff8a3d", "tournesol" to "#ffd23f", "marguerite" to "#ffffff",
        "lavande" to "#a77bff", "bleuet" to "#4f8cff", "coquelicot" to "#ff2a2a", "violette" to "#8a4fff", "lys" to "#ffe9f2")
    private val MOTS = listOf(Triple("geyser", "geyser", 1), Triple("braise", "braises", 0), Triple("corail", "corail", 0),
        Triple("coquill", "coquillage", 0), Triple("algue", "algues", 0), Triple("bonhomme", "bonhomme", 1),
        Triple("colonne", "colonne", 1), Triple("ruine", "colonne", 1), Triple("paratonnerre", "paratonnerre", 1),
        Triple("etoile", "etoile", 0), Triple("eolienne", "eolienne", 1), Triple("tombe", "tombe", 1), Triple("rune", "rune", 1),
        Triple("engrenage", "engrenage", 1), Triple("rouage", "engrenage", 1), Triple("tuyau", "tuyau", 1), Triple("neon", "neon", 1),
        Triple("lampe", "neon", 1), Triple("roseau", "roseau", 0), Triple("bulle", "bulles", 0), Triple("cristal", "cristal", 1),
        Triple("cactus", "cactus", 1))
    private const val ACC_DE = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿœæ"
    private const val ACC_A = "aaaaaaceeeeiiiinooooouuuuyyoa"
    private fun norm(s: String) = s.lowercase().map { val i = ACC_DE.indexOf(it); if (i >= 0) ACC_A[i] else it }.joinToString("")

    /** L'objet dessiné pour un fichier : (clé du dessin, bloque le passage). */
    fun deco(nom: String, tid: String): Pair<String, Boolean> {
        val i = nom.lastIndexOf('.')
        val base = norm(if (i > 0) nom.substring(0, i) else nom)
        val ext = norm(if (i > 0) nom.substring(i + 1) else "")
        fun a(vararg ms: String) = ms.any { base.contains(it) }
        for ((m, k, b) in MOTS) if (base.contains(m)) return k to (b == 1)
        if (ext == "arbre") {
            if (a("sapin", "pin")) return (if (tid == "glace") "sapin_neige" else "sapin") to true
            if (a("bouleau")) return "bouleau" to true
            if (a("cerisier", "sakura")) return "cerisier" to true
            if (a("palmier", "coco")) return "palmier" to true
            return "chene" to true
        }
        if (ext == "fleur") {
            var col: String? = null
            for ((k, c) in FLEURS) if (base.contains(k)) col = c
            return "fleur:" + (col ?: "h${hachage(base) % 360}") to false
        }
        if (ext == "pierre" || ext == "rocher") return if (a("galet")) "galet" to false else (if (tid == "feu") "rocher_volc" else "rocher") to true
        if (ext == "champignon") return (when (tid) { "ombre" -> "champi_lum"; "poison" -> "champi_tox"; else -> "champignon" }) to false
        if (ext == "plante" || ext == "buisson") return "buisson" to false
        if (ext in setOf("tar", "gz", "tgz", "zip")) return "caisse" to false
        if (ext in setOf("sh", "py", "ps1")) return "parchemin_machine" to false
        if (ext in setOf("txt", "md", "log", "csv")) return "parchemin" to false
        return "panneau" to false
    }

    // ------------------------------------------------------------ lire le vrai terrain
    class ParcelleT(val nom: String, val objets: List<String>, val plus: Int = 0, val caches: Int = 0)

    private fun cleParcelle(n: String): Triple<Int, Int, String> {
        val m = RX_PARCELLE.matchEntire(n)
        return if (m != null) Triple(0, m.groupValues[1].toIntOrNull() ?: 0, n) else Triple(1, 0, n.lowercase())
    }

    fun lireTerrain(racine: File): LinkedHashMap<String, List<ParcelleT>> {
        val out = LinkedHashMap<String, List<ParcelleT>>()
        val b = File(racine, "biome")
        for (tid in TYPES) {
            val d = File(b, tid)
            if (!d.isDirectory) continue
            val noms = (d.listFiles() ?: emptyArray()).filter { it.isDirectory && !it.name.startsWith(".") }.map { it.name }
            val ps = noms.sortedWith(compareBy({ cleParcelle(it).first }, { cleParcelle(it).second }, { cleParcelle(it).third }))
                .take(MAX_PARCELLES).map { n ->
                    val fs = (File(d, n).listFiles() ?: emptyArray()).filter { !it.isDirectory }.map { it.name }.sorted()
                    val vis = fs.filter { !it.startsWith(".") }
                    ParcelleT(n, vis.take(MAX_OBJETS), max(0, vis.size - MAX_OBJETS), fs.size - vis.size)
                }
            out[tid] = ps
        }
        return out
    }

    // ------------------------------------------------------------ la disposition
    private fun plan(q: Int, r: Int) = doubleArrayOf(1.5 * q, SQ3 * (r + q / 2.0))
    fun macro(m: Int, n: Int) = intArrayOf(m * 5 + n * 2, m * -2 + n * 3)
    private fun angDiff(a: Double, b: Double): Double { val d = abs(a - b) % 360; return if (d > 180) 360 - d else d }

    fun disposition(regions: Map<String, Int>): Map<String, List<IntArray>> {
        val occ = LinkedHashMap<String, IntArray>()
        fun P(m: Int, n: Int): DoubleArray { val a = macro(m, n); return plan(a[0], a[1]) }
        fun ang(m: Int, n: Int): Double { val p = P(m, n); return (Math.toDegrees(atan2(p[1], p[0])) + 360) % 360 }
        fun dist(m: Int, n: Int): Double { val p = P(m, n); return hypot(p[0], p[1]) / 5 }
        fun frontiere(cells: List<IntArray>): List<IntArray> {
            val o = LinkedHashMap<String, IntArray>()
            for (c in cells) for (d in MN6) { val k = "${c[0] + d[0]},${c[1] + d[1]}"; if (k !in occ && k !in o) o[k] = intArrayOf(c[0] + d[0], c[1] + d[1]) }
            return o.values.toList()
        }
        val out = LinkedHashMap<String, List<IntArray>>()
        for (tid in ORDRE) {
            val n = regions[tid] ?: 0
            if (n == 0) continue
            val pref = (ANG[tid] ?: 0).toDouble()
            val cells = mutableListOf<IntArray>()
            if (occ.isEmpty()) cells.add(intArrayOf(0, 0))
            else {
                var best: IntArray? = null; var bs: Double? = null
                for (c in frontiere(occ.values.toList())) {
                    val x = c[0]; val y = c[1]
                    val s = arrondi(angDiff(ang(x, y), pref) * .08 + dist(x, y) * .9 + ((x * 7 + y * 13) and 3) * .001, 1e6)
                    if (bs == null || s < bs) { bs = s; best = c }
                }
                cells.add(best!!)
            }
            occ["${cells[0][0]},${cells[0][1]}"] = cells[0]
            while (cells.size < n) {
                var cx = 0.0; var cy = 0.0
                for (c in cells) cx += P(c[0], c[1])[0]
                for (c in cells) cy += P(c[0], c[1])[1]
                cx /= cells.size; cy /= cells.size
                var best: IntArray? = null; var bs: Double? = null
                for (c in frontiere(cells)) {
                    val x = c[0]; val y = c[1]; val p = P(x, y)
                    val s = arrondi(dist(x, y) * .7 + (if (tid == "plante") 0.0 else angDiff(ang(x, y), pref) * .03) +
                        hypot(p[0] - cx, p[1] - cy) / 5 * 1.3 + ((x * 7 + y * 13) and 3) * .001, 1e6)
                    if (bs == null || s < bs) { bs = s; best = c }
                }
                if (best == null) break
                cells.add(best); occ["${best[0]},${best[1]}"] = best
            }
            out[tid] = cells
        }
        return out
    }

    // ------------------------------------------------------------ le monde entier
    class Hex(val q: Int, val r: Int, val cle: String, val oq: Int, val or_: Int, val parcelle: String, var region: String?,
              var kind: String, var h: Double, val v: Int, val d: Int, var flow: Int?, val crater: Int, var float: Int,
              var machine: Int, var block: Boolean, var scen: Scen?) {
        var between: List<String>? = null
        var bridge = false
        var base = 0.0
        var mur = 1
        var pilier = 0
    }
    class Pose(val oq: Int, val or_: Int, val k: String, val bloque: Boolean)
    class Parcelle(val type: String, val nom: String, val m: IntArray, val volcan: Boolean, val objets: List<String>,
                   val plus: Int, val caches: Int) {
        val id = "$type/$nom"
        val centre = macro(m[0], m[1])
        val gen = genParcelle(type, nom, volcan, 0)
        val poses = LinkedHashMap<String, Pose>()
    }
    class Carte(val parcelles: List<Parcelle>, val hex: LinkedHashMap<String, Hex>, val cordes: List<Pair<String, String>>) {
        val par = parcelles.associateBy { it.id }
        val parCle = hex.values.associateBy { it.cle }
        fun at(q: Int, r: Int) = hex["$q,$r"]
    }

    fun construire(terrain: Map<String, List<ParcelleT>>): Carte {
        val lay = disposition(terrain.mapValues { it.value.size })
        val parcelles = mutableListOf<Parcelle>()
        var volcanFait = false
        for (tid in TYPES) terrain[tid]?.forEachIndexed { i, p ->
            val volcan = tid == "feu" && !volcanFait
            volcanFait = volcanFait || volcan
            val l = lay[tid] ?: return@forEachIndexed
            parcelles.add(Parcelle(tid, p.nom, if (i < l.size) l[i] else l.last(), volcan, p.objets, p.plus, p.caches))
        }
        val hexs = LinkedHashMap<String, Hex>()
        for (p in parcelles) for (f in FLOWER) {
            val g = p.gen.getValue("${f[0]},${f[1]}")
            val h = Hex(p.centre[0] + f[0], p.centre[1] + f[1], "${p.id}:${f[0]},${f[1]}", f[0], f[1], p.id, p.type, g.kind, g.h,
                g.v, g.d, g.flow, g.crater, g.float, g.machine, g.block, g.scen)
            if (h.scen != null && h.scen!!.k in SCEN_BLOCK) h.block = true
            hexs["${h.q},${h.r}"] = h
        }
        fun at(q: Int, r: Int) = hexs["$q,$r"]
        val vp = parcelles.firstOrNull { it.volcan }
        if (vp != null) {
            val vq = vp.centre[0]; val vr = vp.centre[1]; val dq = DIRS[0][0]; val dr = DIRS[0][1]
            for (h in hexs.values) {
                if (h.region != "feu" || h.parcelle == vp.id) continue
                val d = anneau(h.q - vq, h.r - vr)
                val pied = arrondi(5.6 - (d - 3) * 1.05)
                if (pied > h.h) { h.h = pied; h.kind = if (rnd(h.cle) < .35) "cendre" else "cone"; h.scen = null; h.block = false }
                for (k in 3 until 8) if (h.q == vq + dq * k && h.r == vr + dr * k) { h.kind = "lave"; h.flow = k; h.h = arrondi(max(1.3, h.h - .35)) }
            }
        }
        for (h in hexs.values) {
            if (h.region != "eau" || h.kind != "eau" || h.d < 2) continue
            if (rnd(h.cle + "s") < .5 && DIRS.any { at(h.q + it[0], h.r + it[1])?.region != "eau" }) { h.kind = "sable"; h.h = 1.35 }
        }
        val cordes = mutableListOf<Pair<String, String>>()
        val fait = HashSet<String>()
        val parM = parcelles.associateBy { "${it.m[0]},${it.m[1]}" }
        fun ph(p: Parcelle) = FLOWER.map { at(p.centre[0] + it[0], p.centre[1] + it[1])!! }
        fun hd(h: Hex, c: IntArray) = anneau(h.q - c[0], h.r - c[1])
        for (p in parcelles) for (mv in MN6) {
            val o = parM["${p.m[0] + mv[0]},${p.m[1] + mv[1]}"] ?: continue
            if (o.type == p.type) continue
            val cle = listOf(p.id, o.id).sorted().joinToString("-")
            if (cle in fait) continue
            fait.add(cle)
            val oc = o.centre; val pc = p.centre
            val ca = ph(p).filter { it.d == 2 }.sortedWith(compareBy({ hd(it, oc) }, { abs(it.q - it.r) })).firstOrNull() ?: continue
            val cb = DIRS.mapNotNull { at(ca.q + it[0], ca.r + it[1]) }.filter { it.parcelle == o.id }.sortedBy { hd(it, pc) }.firstOrNull() ?: continue
            val ta = p.type; val tb = o.type
            val pont = ta in setOf("eau", "ciel") || tb in setOf("eau", "ciel") || ca.kind in LIQUIDES || cb.kind in LIQUIDES
            fun interieur(c: Hex, pp: Parcelle, pcen: IntArray): Hex? {
                if (pp.volcan || pp.type == "eau" || pp.type == "ciel") return null
                return DIRS.mapNotNull { at(c.q + it[0], c.r + it[1]) }
                    .filter { it.parcelle == pp.id && it.d == 1 && it.region != null && it.kind != "fleche" }
                    .sortedWith(compareBy<Hex>({ anneau(it.q - pcen[0], it.r - pcen[1]) }, { abs(it.h - c.h) })).firstOrNull()
            }
            val raide = abs(ca.h - cb.h) > 1.4
            val ia = if (raide) interieur(ca, p, oc) else null
            val ib = if (raide) interieur(cb, o, pc) else null
            val chaine = listOfNotNull(ia, ca, cb, ib)
            val h0 = if ((ia ?: ca).kind == "fleche") 2.0 else (ia ?: ca).h
            val h1 = if ((ib ?: cb).kind == "fleche") 2.0 else (ib ?: cb).h
            val ha = if (ca.kind == "fleche") 2.0 else ca.h
            val hb = if (cb.kind == "fleche") 2.0 else cb.h
            chaine.forEachIndexed { i, h ->
                h.h = arrondi(h0 + (h1 - h0) * (i + .5) / chaine.size)
                h.kind = if (pont) "pont" else if (abs(ha - hb) > 1.4) "escalier" else "chemin"
                if (h === ca || h === cb) h.region = null
                h.block = false; h.scen = null
                if (pont) h.float = 0
                h.machine = 0; h.bridge = pont; h.between = listOf(ta, tb)
            }
            if (pont) for (i in 0 until chaine.size - 1) cordes.add(chaine[i].cle to chaine[i + 1].cle)
        }
        for (h in hexs.values) {
            h.base = arrondi(if (h.float != 0) h.h - 1.1 else if (h.machine != 0) h.h - .6 else if (h.bridge) h.h - .35 else -1.5)
            h.mur = max(1, floor((h.h - h.base) * HZ + .5).toInt())
            h.pilier = if (h.machine != 0) floor((h.base + 1.5) * HZ + .5).toInt() else 0
        }
        for (p in parcelles) {
            val pris = HashSet<String>()
            for (nom in p.objets) {
                val (k, bloque) = deco(nom, p.type)
                val cands = FLOWER.filter { o ->
                    val h = at(p.centre[0] + o[0], p.centre[1] + o[1])!!
                    !(h.region == null || h.block || h.scen != null || "${o[0]},${o[1]}" in pris || h.crater != 0 ||
                        (o[0] == 0 && o[1] == 0) || (h.kind in LIQUIDES && k !in AQUA_DECO))
                }
                if (cands.isEmpty()) continue
                val o = choisir(cands, hasard(hachage(p.id + "/" + nom)))
                pris.add("${o[0]},${o[1]}")
                p.poses[nom] = Pose(o[0], o[1], k, bloque)
            }
        }
        return Carte(parcelles, hexs, cordes)
    }

    /** creatures : [(id, type)] dans l'ordre de l'équipe → (id → parcelle, ids au refuge). */
    fun placeCreatures(m: Carte, creatures: List<Pair<String, String>>): Pair<LinkedHashMap<String, String>, List<String>> {
        val libres = LinkedHashMap<String, ArrayDeque<String>>()
        for (p in m.parcelles) libres.getOrPut(p.type) { ArrayDeque() }.addLast(p.id)
        val maison = LinkedHashMap<String, String>(); val refuge = mutableListOf<String>()
        for ((i, ty) in creatures) { val l = libres[ty]; if (l != null && l.isNotEmpty()) maison[i] = l.removeFirst() else refuge.add(i) }
        return maison to refuge
    }

    fun solX(q: Int, r: Int) = HR * 1.5 * q
    fun solY(q: Int, r: Int) = HR * SQ3 * (r + q / 2.0) * TILT
}
