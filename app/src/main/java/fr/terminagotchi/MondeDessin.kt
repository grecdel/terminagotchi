package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.round
import kotlin.math.sin

/**
 * Le monde des biomes sur le téléphone : les DESSINS en pixels (portés de pc/tg/monde_dessin.py, eux-mêmes du prototype
 * « Monde Terminagotchi » v4 : prismes hexagonaux en relief, objets du décor) et la VUE (portée de pc/tg/monde.py) :
 * le vrai terrain en relief, l'équipe qui s'y promène, la liste « Mes créatures » dans un panneau qui monte du bas, la
 * fiche À LA PLACE de la liste (« ← Mes créatures »), un toucher à côté la referme ; les effets des commandes
 * (Effets.kt) de 1 à 2 s, jamais bloquants. Tout passe par l'interface Toile (mêmes thèmes, captures JVM).
 * La mascotte du site n'apparaît jamais ; aucun accessoire ; le glitch des créatures reste (Poses.albumEspece).
 */
object MondeDessin {
    private val HR = Monde.HR; private val HH = Monde.HH; private val HZ = Monde.HZ

    class Kind(val top: List<String>, val mur: String, val f: Set<String>)
    val KINDS = linkedMapOf(
        "herbe" to Kind(listOf("#5aa63a", "#4f9634", "#66b843"), "#6b4a2c", setOf("grass")),
        "fleurs" to Kind(listOf("#5aa63a", "#4f9634", "#66b843"), "#6b4a2c", setOf("grass", "flowers")),
        "sombre" to Kind(listOf("#2f6b2c", "#2a6027", "#367a31"), "#5e3f25", setOf("grass")),
        "chemin" to Kind(listOf("#c9a26a", "#b88f58", "#d4b07a"), "#7b5534", setOf()),
        "escalier" to Kind(listOf("#c9a26a", "#b88f58", "#d4b07a"), "#7b5534", setOf("steps")),
        "pont" to Kind(listOf("#a8743f", "#9a6a3a", "#b5804a"), "#5a381e", setOf("planks")),
        "sable" to Kind(listOf("#e6cf8a", "#d9bf78", "#efdb9c"), "#b8945a", setOf()),
        "eau" to Kind(listOf("#2f7fc4", "#2a72b2", "#3a8fd6"), "#1d4a73", setOf("water")),
        "neige" to Kind(listOf("#eef6ff", "#dbeaf8", "#f8fcff"), "#8fa9c2", setOf()),
        "glace" to Kind(listOf("#a8e1f5", "#94d4ec", "#bdeafa"), "#5f9ab8", setOf("ice")),
        "basalte" to Kind(listOf("#4a3f4f", "#3f3544", "#554959"), "#2e2531", setOf("strata")),
        "cone" to Kind(listOf("#5e4646", "#553f40", "#684e4e"), "#4a2c2a", setOf("strata", "embers")),
        "cendre" to Kind(listOf("#6d6670", "#625b66", "#7a7380"), "#2e2531", setOf("embers", "strata")),
        "lave" to Kind(listOf("#ff7a1a", "#f25c0f", "#ff9a33"), "#2e2531", setOf("lava", "strata")),
        "pierre" to Kind(listOf("#8d929a", "#7d828a", "#9ba0a8"), "#5d6168", setOf("strata")),
        "gres" to Kind(listOf("#d08a4e", "#c27a40", "#dc9a5e"), "#9a5a2e", setOf("strata")),
        "nuage" to Kind(listOf("#e6defc", "#d9cff7", "#f1ecff"), "#a99be0", setOf("cloud")),
        "orage" to Kind(listOf("#8f86b8", "#8178ab", "#9d95c4"), "#5f5690", setOf("cloud", "bolt")),
        "dalle" to Kind(listOf("#4b3a6b", "#43345f", "#544276"), "#251c38", setOf("flag")),
        "violette" to Kind(listOf("#3d2f52", "#352947", "#47375e"), "#251c38", setOf()),
        "crypte" to Kind(listOf("#2a2040", "#241b38", "#30254a"), "#1b142a", setOf("flag")),
        "fleche" to Kind(listOf("#3a2d55", "#33284b", "#43345f"), "#2a2140", setOf("spire")),
        "metal" to Kind(listOf("#8a96a3", "#7f8b98", "#96a2ae"), "#4a525c", setOf("plate")),
        "grille" to Kind(listOf("#5d6670", "#535b64", "#68717b"), "#3a4149", setOf("grid")),
        "rouille" to Kind(listOf("#a3562a", "#8f4a24", "#b86a38"), "#5e3018", setOf()),
        "vase" to Kind(listOf("#55702a", "#4b6424", "#617d30"), "#3b4a1c", setOf()),
        "toxique" to Kind(listOf("#8fe03a", "#7fd02c", "#a6f04a"), "#3b4a1c", setOf("toxic")))
    val SOLS: List<String> = KINDS.keys.toList()
    val DECORS = listOf("chene", "cerisier", "sapin", "sapin_neige", "bouleau", "palmier", "fleur:#ff3d5a", "fleur:h200", "rocher",
        "rocher_volc", "galet", "cristal", "champignon", "champi_lum", "champi_tox", "cactus", "buisson", "geyser", "braises", "corail",
        "coquillage", "algues", "bonhomme", "colonne", "paratonnerre", "etoile", "eolienne", "tombe", "rune", "engrenage", "tuyau",
        "neon", "roseau", "bulles", "panneau", "caisse", "parchemin", "parchemin_machine")

    /** « #rrggbb » ou « hNNN » (une teinte) → 0xRRGGBB. */
    fun hexa(c: String): Int {
        if (c.startsWith("h")) {
            val h = (c.substring(1).toIntOrNull() ?: 0) / 360.0; val l = .62; val s = .85
            val q = if (l < .5) l * (1 + s) else l + s - l * s; val p = 2 * l - q
            fun hue(t0: Double): Double { var t = t0; if (t < 0) t += 1; if (t > 1) t -= 1
                return when { t < 1.0 / 6 -> p + (q - p) * 6 * t; t < .5 -> q; t < 2.0 / 3 -> p + (q - p) * (2.0 / 3 - t) * 6; else -> p } }
            return ((hue(h + 1.0 / 3) * 255).toInt() shl 16) or ((hue(h) * 255).toInt() shl 8) or (hue(h - 1.0 / 3) * 255).toInt()
        }
        return c.substring(1, 7).toInt(16)
    }
    fun shade(c: Int, amt: Int): Int {
        val r = ((c shr 16 and 255) + amt).coerceIn(0, 255); val g = ((c shr 8 and 255) + amt).coerceIn(0, 255); val b = ((c and 255) + amt).coerceIn(0, 255)
        return (r shl 16) or (g shl 8) or b
    }
    private fun mod(a: Int, b: Int) = if (a >= 0) a % b else -((-a) % b)
    fun hexInside(dx: Double, dy: Double) = abs(dy) <= HH && abs(dx) <= HR - abs(dy) * (HR / 2) / HH
    fun hexBottom(dx: Double) = if (abs(dx) <= HR / 2) HH else HH * (HR - abs(dx)) / (HR / 2)

    class Pix(val w: Int, val h: Int) {
        val d = IntArray(w * h)
        fun px(x: Number, y: Number, c: Any, ww: Int = 1, hh: Int = 1) {
            val col = (if (c is String) hexa(c) else c as Int) or (0xFF shl 24)
            val x0 = floor(x.toDouble()).toInt(); val y0 = floor(y.toDouble()).toInt()
            for (yy in max(0, y0) until min(h, y0 + hh)) for (xx in max(0, x0) until min(w, x0 + ww)) d[yy * w + xx] = col
        }
        fun ombre(x: Int, y: Int) { if (x in 0 until w && y in 0 until h && d[y * w + x] == 0) d[y * w + x] = (140 shl 24) or 0x141E0F }
        fun cadre(ax: Int, ay: Int, cle: String) = Poses.Cadre(w, h, d, ax, ay, cle)
    }

    private fun blob(g: Pix, cx: Int, cy: Int, rx: Int, ry: Int, cols: List<String>, r: () -> Double) {
        val c3 = cols.map { hexa(it) }
        for (y in -ry..ry) for (x in -rx..rx) {
            val d = (x * x).toDouble() / (rx * rx) + (y * y).toDouble() / (ry * ry)
            if (d > 1) continue
            var c = c3[1]; val l = (x.toDouble() / rx) * .7 + (y.toDouble() / ry)
            if (l > .55) c = c3[0] else if (l < -.6) c = c3[2]
            if (d > .82 && l > 0) c = c3[0]
            if (r() < .08) c = c3[if (r() < .5) 0 else 2]
            g.px(cx + x, cy + y, c)
        }
        for (y in -ry - 1..ry + 1) for (x in -rx - 1..rx + 1) {
            val d = (x * x).toDouble() / (rx * rx) + (y * y).toDouble() / (ry * ry)
            val d2 = (x * x).toDouble() / ((rx + 1) * (rx + 1)) + (y * y).toDouble() / ((ry + 1) * (ry + 1))
            if (d > 1 && d2 <= 1.0) g.ombre(cx + x, cy + y)
        }
    }

    private val sprites = HashMap<String, Poses.Cadre>()
    /** Le prisme hexagonal en relief (Cadre ; ancre : le centre du dessus, en entiers arrondis). */
    fun sprite(kind: String, v: Int, mur: Int, pilier: Int): Poses.Cadre {
        val cle = "hex|$kind|$v|$mur|$pilier"
        sprites[cle]?.let { return it }
        val K = KINDS[kind] ?: KINDS.getValue("herbe")
        val top = K.top.map { hexa(it) }; val wall = hexa(K.mur); val f = K.f
        val w2 = (HR * 2 + 3).toInt(); val cx = HR + 1.5; val cy = HH + 1
        val g = Pix(w2, ceil(HH * 2 + mur + pilier + 3).toInt())
        val r = Monde.hasard(Monde.hachage("$kind|$v|$mur|$pilier|1"))
        val fleurs = listOf("#ffffff", "#ffd84a", "#ff6fa8", "#b48cff").map { hexa(it) }
        for (sy in 0 until g.h) for (sx in 0 until g.w) {
            val x = sx; val y = sy
            val dx = sx + .5 - cx; val dy = sy + .5 - cy
            var col: Int? = null
            if (hexInside(dx, dy)) {
                val n = r()
                var c = top[0]; if (n < .3) c = top[1] else if (n < .42) c = top[2]
                if ("water" in f) { val b = mod(x + y * 2 + v * 3, 9); c = if (b < 2) top[2] else if (b < 5) top[0] else top[1] }
                if ("lava" in f) { val b = mod(x * 2 - y + v * 5, 8); c = if (b < 2) 0xffd36b else if (b < 4) top[2] else if (n < .5) top[0] else top[1]; if (n < .05) c = 0x3a2a2a }
                if ("toxic" in f) { val b = mod(x * 2 + y + v * 4, 9); c = if (b < 2) 0xd9ff8a else if (b < 5) top[0] else top[1] }
                if ("ice" in f && mod(x - y * 2 + 40, 11) < 2) c = 0xffffff
                if ("planks" in f) c = if (x % 4 == 0) 0x5a381e else if ((x / 4) % 2 != 0) top[0] else top[2]
                if ("steps" in f && floor(dy + HH + .5).toInt() % 4 == 0) c = 0x8a6a40
                if ("flag" in f && (mod(x + 2 * y, 10) == 0 || mod(x - 2 * y + 60, 10) == 0)) c = shade(top[0], -22)
                if ("grid" in f && (mod(x + 2 * y, 5) == 0 || mod(x - 2 * y + 60, 5) == 0)) c = 0x363d45
                if ("plate" in f && mod(x + 2 * y, 13) == 0) c = 0x5f6a75
                if ("cloud" in f && hypot(dx / HR, dy / HH) > .7 && n < .55) c = 0xffffff
                if ("bolt" in f) { val rx = floor(dx + .5).toInt(); if ((rx == -1 && dy > -5 && dy < 0) || (rx == 0 && dy >= -1 && dy < 1) || (rx == 1 && dy >= 0 && dy < 4)) c = 0xffe14a }
                if ("flowers" in f && n > .93) c = fleurs[(r() * 4).toInt()]
                if ("embers" in f && n > .95) c = if (n > .975) 0xff7a1a else 0xffb347
                if ("spire" in f) c = shade(c, floor(-dy * 2 + .5).toInt())
                if (kind == "neige" && n > .9) c = 0xc6dcf0
                if (kind == "rouille" && n > .9) c = 0x6e3418
                if (kind == "violette" && n > .97) c = 0x7dffcf
                val edge = !hexInside(dx + 1.2 * (if (dx >= 0) 1 else -1), dy) || !hexInside(dx, dy + (if (dy < 0) -1.1 else 1.1))
                if (edge) c = shade(c, if (dy < 0) 30 else -24)
                col = c
            } else if (abs(dx) <= HR && dy > hexBottom(dx) && dy <= hexBottom(dx) + mur) {
                val face = if (dx < -HR / 2) 0 else if (dx > HR / 2) 2 else 1
                val depth = dy - hexBottom(dx)
                var c = shade(wall, intArrayOf(14, 0, -26)[face] - min(30.0, depth * .35).toInt())
                if (depth < 1.2) c = shade(wall, intArrayOf(40, 26, 6)[face])
                if ("strata" in f && floor(depth + .5).toInt() % HZ.toInt() == 0 && depth > 2) c = shade(c, -18)
                if ("cloud" in f && depth > mur - 3) c = 0xffffff
                if ("lava" in f && mod(floor(dx + .5).toInt() + floor(depth * .35 + .5).toInt() + v, 5) == 0) c = if (depth < mur * .7) 0xff7a1a else 0xc2410c
                if (r() < .06) c = shade(c, -12)
                col = c
            } else if (pilier > 0 && abs(dx) <= 3 && dy > HH + mur && dy <= HH + mur + pilier) {
                col = if (dx < -1) 0x5d6670 else if (dx > 1) 0x2c3238 else 0x3a4149
            }
            if (col != null) g.d[sy * g.w + sx] = col or (0xFF shl 24)
        }
        return g.cadre(round(cx).toInt(), round(cy).toInt(), cle).also { sprites[cle] = it }
    }

    private val decos = HashMap<String, Poses.Cadre>()
    /** Un objet du décor (Cadre, ancre au milieu du bas). */
    fun decor(k: String): Poses.Cadre {
        decos[k]?.let { return it }
        val r = Monde.hasard(Monde.hachage(k))
        val g: Pix
        when {
            k == "chene" || k == "cerisier" -> {
                g = Pix(30, 38); g.px(13, 22, "#6b4426", 4, 14); g.px(13, 22, "#8a5a33", 1, 14); g.px(12, 35, "#5a381e", 6, 2)
                val cols = if (k == "cerisier") listOf("#d9659a", "#f28bbb", "#ffc2dc") else listOf("#2f7a2a", "#3f9a35", "#6cc24e")
                blob(g, 15, 14, 12, 11, cols, r); blob(g, 9, 18, 6, 5, cols, r); blob(g, 21, 18, 6, 5, cols, r)
                if (k == "cerisier") repeat(8) { g.px(5 + (r() * 20).toInt(), 6 + (r() * 14).toInt(), "#ffffff") }
            }
            k == "sapin" || k == "sapin_neige" -> {
                g = Pix(24, 40); g.px(10, 30, "#6b4426", 4, 9)
                for (L in 0 until 4) { val top = 2 + L * 7; val hgt = 12; val wb = 4 + L * 2
                    for (y in 0 until hgt) { val w = floor(y.toDouble() / hgt * wb + .5).toInt() + 1
                        for (x in -w..w) { var col = if (x < -w / 3.0) "#1f5a2a" else if (x > w / 3.0) "#14421f" else "#2a7035"
                            if (y == hgt - 1) col = "#123a1b"; if (r() < .07) col = "#3f8a45"
                            if (k == "sapin_neige" && (y < 3 || (y == hgt - 2 && r() < .6))) col = if (x < 0) "#ffffff" else "#dbeaf8"
                            g.px(12 + x, top + y, col) } } }
            }
            k == "bouleau" -> { g = Pix(26, 40); g.px(11, 18, "#eeeeea", 4, 21); repeat(6) { g.px(11 + (r() * 3).toInt(), 20 + (r() * 18).toInt(), "#2a2a2a", 2, 1) }
                g.px(10, 38, "#5a381e", 6, 2); blob(g, 13, 12, 10, 10, listOf("#5c9a2a", "#80c03c", "#b5e46a"), r) }
            k == "palmier" -> { g = Pix(32, 40); for (y in 0 until 24) g.px(15 + round(sin(y / 7.0) * 2).toInt(), 14 + y, if (y % 3 != 0) "#9a6a3a" else "#7a4f28", 3, 1)
                for ((dx, dy) in listOf(-12 to 4, 12 to 4, -9 to -3, 9 to -3, 0 to -6, -13 to 9, 13 to 9)) { var tt = 0.0
                    while (tt <= 1) { g.px(round(16 + dx * tt).toInt(), round(13 + dy * tt + sin(tt * 3) * 3 * (if (dx != 0) 1 else 0)).toInt(), if (tt > .7) "#2f8a2a" else "#3fae35", 2, 2); tt += .08 } } }
            k.startsWith("fleur:") -> { val col = k.substring(6); g = Pix(20, 16)
                for ((x, y) in listOf(5 to 8, 11 to 5, 15 to 10, 9 to 11)) { g.px(x, y + 1, "#2f7a2a", 1, 4); g.px(x + 1, y + 3, "#3f9a35")
                    for ((a, b) in listOf(-1 to 0, 1 to 0, 0 to -1, 0 to 1)) g.px(x + a, y + b, col); g.px(x, y, "#ffe066") } }
            k == "rocher" -> { g = Pix(26, 20); blob(g, 13, 11, 11, 7, listOf("#5d6168", "#8d929a", "#c3c7cc"), r); g.px(8, 9, "#4a4d52", 3, 1); g.px(15, 12, "#4a4d52", 4, 1) }
            k == "rocher_volc" -> { g = Pix(26, 20); blob(g, 13, 11, 11, 7, listOf("#211a24", "#3f3544", "#5c4f62"), r); g.px(8, 9, "#ff7a1a", 3, 1); g.px(10, 10, "#ff7a1a", 1, 2); g.px(15, 12, "#ffb347", 4, 1); g.px(18, 11, "#ff7a1a") }
            k == "galet" -> { g = Pix(22, 12); blob(g, 6, 7, 4, 3, listOf("#6d7178", "#9ba0a8", "#d0d3d7"), r); blob(g, 14, 6, 5, 3, listOf("#6d7178", "#a7abb2", "#d8dbdf"), r); blob(g, 11, 9, 3, 2, listOf("#6d7178", "#9ba0a8", "#d0d3d7"), r) }
            k == "cristal" -> { g = Pix(22, 30); for (q in listOf(intArrayOf(11, 2, 4, 26), intArrayOf(6, 10, 3, 18), intArrayOf(16, 8, 3, 20))) for (i in 0 until q[3]) {
                val ww = min(q[2], ceil(i / 2.0).toInt() + 1); g.px(q[0] - ww + 1, q[1] + i, "#3fb8e8", ww, 1); g.px(q[0] + 1, q[1] + i, "#1f7fb0", ww, 1); g.px(q[0], q[1] + i, "#c9f4ff") } }
            k == "champignon" || k == "champi_lum" || k == "champi_tox" -> { g = Pix(18, 18); g.px(7, 10, "#f3e7d0", 4, 7); g.px(10, 10, "#d8c9ad", 1, 7)
                blob(g, 9, 8, 7, 4, when (k) { "champignon" -> listOf("#a3141e", "#e0303a", "#ff6a6a"); "champi_lum" -> listOf("#1f8f8a", "#3fe0d0", "#b9fff4"); else -> listOf("#5a1f80", "#8a3fc0", "#c48aff") }, r)
                val dot = if (k == "champi_tox") "#b6ff4a" else "#ffffff"; g.px(5, 7, dot, 2, 1); g.px(10, 5, dot, 2, 2); g.px(13, 8, dot) }
            k == "cactus" -> { g = Pix(20, 30); g.px(8, 4, "#3f9a35", 5, 25); g.px(9, 4, "#6cc24e", 1, 25); g.px(3, 12, "#3f9a35", 3, 8); g.px(3, 17, "#3f9a35", 6, 3); g.px(14, 9, "#3f9a35", 3, 9); g.px(11, 15, "#3f9a35", 4, 3); g.px(10, 3, "#ff6fa8", 2, 2) }
            k == "buisson" -> { g = Pix(24, 16); blob(g, 12, 9, 10, 6, listOf("#2f7a2a", "#3f9a35", "#6cc24e"), r) }
            k == "geyser" -> { g = Pix(24, 26); blob(g, 12, 20, 10, 5, listOf("#211a24", "#3f3544", "#5c4f62"), r); g.px(9, 15, "#3f3544", 7, 3); g.px(10, 14, "#ff7a1a", 5, 2); g.px(11, 13, "#ffd36b", 3, 1) }
            k == "braises" -> { g = Pix(20, 12); blob(g, 10, 7, 8, 3, listOf("#211a24", "#3f3544", "#554959"), r); repeat(7) { g.px(4 + (r() * 12).toInt(), 5 + (r() * 4).toInt(), if (r() < .5) "#ff7a1a" else "#ffd36b") } }
            k == "corail" -> { g = Pix(22, 24); val cc = listOf("#ff6f91", "#ff8fab", "#ffb3c6")
                for ((x, h) in listOf(6 to 14, 11 to 20, 16 to 12)) { for (y in 0 until h) g.px(x + round(sin(y / 3.0)).toInt(), 23 - y, cc[y % 3], 2, 1); g.px(x - 2, 23 - h + 4, cc[0], 2, 1); g.px(x + 2, 23 - h + 7, cc[1], 2, 1) } }
            k == "coquillage" -> { g = Pix(16, 12); for (i in 0 until 5) g.px(4 + i * 2 - (if (i > 2) 1 else 0), 2 + abs(2 - i), "#ffe3c2", 2, 8 - abs(2 - i) * 2); g.px(3, 9, "#e8b98a", 10, 2); for (i in 0 until 4) g.px(5 + i * 2, 4, "#e8b98a", 1, 5) }
            k == "algues" -> { g = Pix(18, 24); for ((x, h, c2) in listOf(Triple(4, 18, "#2f9a5a"), Triple(9, 22, "#3fbf6a"), Triple(14, 15, "#2a7a4a"))) for (y in 0 until h) g.px(x + round(sin(y / 3.0 + x) * 1.5).toInt(), 23 - y, c2, 2, 1) }
            k == "bonhomme" -> { g = Pix(20, 30); blob(g, 10, 22, 7, 6, listOf("#b9cde0", "#e9f4ff", "#ffffff"), r); blob(g, 10, 11, 5, 5, listOf("#b9cde0", "#e9f4ff", "#ffffff"), r)
                g.px(8, 9, "#222222"); g.px(12, 9, "#222222"); g.px(10, 11, "#ff8a3d", 3, 1); g.px(6, 3, "#2b2b2b", 9, 2); g.px(8, 0, "#2b2b2b", 5, 3); g.px(9, 19, "#222222"); g.px(9, 22, "#222222") }
            k == "colonne" -> { g = Pix(18, 32); g.px(4, 28, "#b8945a", 10, 3); g.px(5, 8, "#efdb9c", 8, 20); g.px(5, 8, "#f7e9b8", 2, 20); g.px(11, 8, "#c9ab68", 2, 20); g.px(7, 8, "#d9bf78", 1, 20); g.px(4, 6, "#e6cf8a", 10, 2); g.px(6, 4, "#e6cf8a", 4, 2); g.px(10, 5, "#e6cf8a", 2, 1) }
            k == "paratonnerre" -> { g = Pix(14, 36); g.px(6, 6, "#8a96a3", 2, 28); g.px(6, 6, "#c9d2db", 1, 28); g.px(3, 33, "#4a525c", 8, 2); g.px(6, 2, "#ffe14a", 2, 4); g.px(5, 4, "#ffe14a", 4, 1) }
            k == "etoile" -> { g = Pix(18, 14); g.px(8, 2, "#ffe14a", 2, 3); g.px(3, 5, "#ffe14a", 12, 2); g.px(5, 7, "#ffd23f", 8, 2); g.px(4, 9, "#ffd23f", 3, 2); g.px(11, 9, "#ffd23f", 3, 2); g.px(8, 5, "#fff6b0", 2, 2) }
            k == "eolienne" -> { g = Pix(24, 38); g.px(11, 12, "#e6ecfb", 3, 25); g.px(11, 12, "#ffffff", 1, 25); g.px(9, 36, "#a9b2d6", 7, 2)
                for (tt in 0 until 9) { g.px(12 - tt, 11 - round(tt * .5).toInt(), "#c5cdea", 2, 1); g.px(12 + tt, 11 - round(tt * .5).toInt(), "#c5cdea", 2, 1); g.px(12, 11 + tt, "#c5cdea", 2, 1) }; g.px(11, 10, "#8b9ac4", 3, 3) }
            k == "tombe" -> { g = Pix(18, 24); g.px(3, 8, "#7d828a", 12, 15); g.px(5, 5, "#7d828a", 8, 3); g.px(7, 4, "#8d929a", 4, 1); g.px(3, 8, "#9ba0a8", 2, 15); g.px(8, 10, "#4a4d52", 2, 8); g.px(6, 12, "#4a4d52", 6, 2); g.px(2, 22, "#3d2f52", 14, 2) }
            k == "rune" -> { g = Pix(18, 30); g.px(4, 4, "#5d6168", 10, 24); g.px(4, 4, "#8d929a", 2, 24); g.px(5, 2, "#5d6168", 7, 2); g.px(8, 9, "#c48aff", 2, 12); g.px(6, 12, "#c48aff", 6, 2); g.px(6, 17, "#c48aff", 2, 2); g.px(10, 17, "#c48aff", 2, 2); g.px(3, 27, "#251c38", 12, 2) }
            k == "engrenage" -> { g = Pix(26, 26); for (i in 0 until 8) { val a = i * PI / 4; g.px(13 + cos(a) * 10 - 2, 13 + sin(a) * 10 - 2, "#4a525c", 4, 4) }
                blob(g, 13, 13, 9, 9, listOf("#4a525c", "#8a96a3", "#c9d2db"), r); blob(g, 13, 13, 3, 3, listOf("#2c3238", "#3a4149", "#4a525c"), r) }
            k == "tuyau" -> { g = Pix(26, 28); g.px(4, 8, "#b86a38", 5, 18); g.px(4, 8, "#d48a55", 1, 18); g.px(4, 6, "#8f4a24", 16, 5); g.px(4, 6, "#d48a55", 16, 1); g.px(17, 6, "#b86a38", 5, 14); g.px(20, 6, "#8f4a24", 2, 14); g.px(2, 24, "#5e3018", 9, 3); g.px(15, 19, "#5e3018", 9, 3); g.px(10, 7, "#3df2ff", 2, 2) }
            k == "neon" -> { g = Pix(18, 40); g.px(8, 8, "#4a525c", 2, 30); g.px(8, 8, "#8a96a3", 1, 30); g.px(5, 37, "#3a4149", 8, 2); g.px(4, 4, "#4a525c", 10, 4); g.px(5, 8, "#3df2ff", 8, 2); g.px(6, 10, "#b9fbff", 6, 1) }
            k == "roseau" -> { g = Pix(18, 26); for ((x, h) in listOf(4 to 18, 8 to 22, 12 to 16, 15 to 20)) { g.px(x, 25 - h, "#6a8f2a", 1, h); g.px(x - 1, 25 - h, "#7a4f28", 3, 4) } }
            k == "bulles" -> { g = Pix(20, 18); for ((x, y, rr) in listOf(Triple(6, 12, 3), Triple(13, 9, 4), Triple(10, 4, 2))) { blob(g, x, y, rr, rr, listOf("#4b6424", "#8fe03a", "#d9ff8a"), r); g.px(x - 1, y - 1, "#ffffff") } }
            k == "caisse" -> { g = Pix(22, 18); g.px(2, 4, "#8a5a33", 18, 13); g.px(2, 4, "#b5804a", 18, 2); g.px(2, 15, "#5a381e", 18, 2); for (x in listOf(2, 10, 18)) g.px(x, 4, "#5a381e", 2, 13); g.px(3, 8, "#6b4426", 16, 1); g.px(3, 11, "#6b4426", 16, 1) }
            k == "parchemin" || k == "parchemin_machine" -> { g = Pix(20, 22); g.px(4, 4, "#f3e2b8", 12, 15); g.px(3, 2, "#d9bf8a", 14, 3); g.px(3, 18, "#d9bf8a", 14, 3)
                for (i in 0 until 4) g.px(6, 7 + i * 3, "#7b5534", 8 - (i % 2) * 3, 1)
                if (k == "parchemin_machine") { g.px(12, 12, "#4a525c", 6, 6); g.px(14, 14, "#3df2ff", 2, 2) } }
            else -> { g = Pix(20, 24); g.px(9, 10, "#6b4426", 2, 14); g.px(2, 3, "#8a5a33", 16, 9); g.px(2, 3, "#a8743f", 16, 1); g.px(2, 11, "#5a381e", 16, 1); g.px(5, 6, "#3a2414", 10, 1); g.px(5, 8, "#3a2414", 7, 1) }
        }
        return g.cadre(g.w / 2, g.h, "deco|$k").also { decos[k] = it }
    }
}
