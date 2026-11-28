package fr.terminagotchi

import android.graphics.Bitmap

/**
 * Animations procédurales pour tout le bestiaire : portage exact de pc/tg/anim_auto.py.
 *
 * Chaque stade n'a qu'une image fixe : on la pose (pieds au sol) sur une toile un peu plus grande,
 * on la déforme (écrasement, étirement, inclinaison, bascule, saut), on la recolore (sommeil, colère,
 * K.O., flash) et on ajoute des effets en gros pixels. Tout est calculé en entiers (tables, tramage
 * de Bayer, générateur pseudo-aléatoire maison) : mêmes images qu'en Python, pixel pour pixel.
 *
 * Les images sont des indices : 0 = transparent, k = palette[k - 1].
 */
object AnimAuto {

    /** Une image fixe d'un stade : indices de palette (0 = transparent), palette en 0xRRGGBB ou ARGB. */
    class Sprite(val w: Int, val h: Int, val octets: ByteArray, val palette: IntArray)

    /** Une animation : toile largeur × hauteur, images en indices, palette étendue en ARGB.
     *  Les nTeinte premières couleurs sont celles de la bestiole (décalées pour les shiny). */
    class Anim(val largeur: Int, val hauteur: Int, val images: List<ByteArray>, val palette: IntArray,
               val nTeinte: Int, val ips: Int = IPS, val vie: VieInfo? = null)

    /** « statique » : la vie (Vie.kt) posée en (x0, y0) sur la toile ; bitmap() la dessine alors au pixel fin. */
    class VieInfo(val analyse: Vie.Analyse, val x0: Int, val y0: Int)

    val ANIMS = listOf("statique", "mange", "attaque", "salut", "parle", "dort", "content", "affame", "confus",
        "colere", "victoire", "ko", "evolution")
    const val IPS = 8

    private val BAYER = intArrayOf(0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
    private const val CODES = "WKYORPBCVGMSD"
    private val SPECIAUX = intArrayOf(
        0xFFFFFF, // W blanc
        0x1B1B25, // K noir
        0xFFD83A, // Y jaune étoile
        0xFF9A1F, // O orange
        0xE8333C, // R rouge
        0xFF6B9D, // P rose cœur
        0x8FC4FF, // B bleu zzz
        0x4FC3F7, // C goutte
        0xC58CFF, // V violet spirale
        0x5CBF4A, // G vert feuille
        0x8A5A2B, // M marron
        0xD9D6CC, // S os / vapeur
        0x2D3A6E) // D bleu nuit

    private val GLYPHES: Map<String, Array<String>> = mapOf(
        "pomme" to arrayOf(
            "...M...",
            "...MGG.",
            ".RRMRR.",
            "RRWRRRR",
            "RWRRRRR",
            "RRRRRRR",
            ".RRRRR."),
        "pomme1" to arrayOf(
            "...M...",
            "...MGG.",
            "..RMRR.",
            "...RRRR",
            "...RRRR",
            "..RRRRR",
            ".RRRRR."),
        "pomme2" to arrayOf(
            "...M...",
            "...MGG.",
            "...MRR.",
            "....RRR",
            "....RRR",
            "....RRR",
            "...RRR."),
        "trognon" to arrayOf(
            "...M...",
            "..RMR..",
            "...S...",
            "...S...",
            "...S...",
            "..RRR..",
            "...R..."),
        "etoile" to arrayOf(
            "...Y...",
            "...Y...",
            "..YYY..",
            "YYYWYYY",
            ".YYYYY.",
            "..YYY..",
            ".YY.YY.",
            ".Y...Y."),
        "etincelle" to arrayOf(
            "..W..",
            "..Y..",
            "WYYYW",
            "..Y..",
            "..W.."),
        "point" to arrayOf(
            ".Y.",
            "YWY",
            ".Y."),
        "coeur" to arrayOf(
            ".PP.PP.",
            "PWPPPPP",
            "PPPPPPP",
            ".PPPPP.",
            "..PPP..",
            "...P..."),
        "petit_coeur" to arrayOf(
            ".P.P.",
            "PPPPP",
            "PPPPP",
            ".PPP.",
            "..P.."),
        "z" to arrayOf(
            "BBBB",
            "..B.",
            ".B..",
            "BBBB"),
        "Z" to arrayOf(
            "BBBBB",
            "...B.",
            "..B..",
            ".B...",
            "BBBBB"),
        "colere" to arrayOf(
            "...R.R...",
            "...R.R...",
            "..RR.RR..",
            "RRR...RRR",
            ".........",
            "RRR...RRR",
            "..RR.RR..",
            "...R.R...",
            "...R.R..."),
        "spirale" to arrayOf(
            "..VVVVV..",
            ".V.....V.",
            "V..VVV..V",
            "V.V...V.V",
            "V.V.W.V.V",
            "V.V..V..V",
            "V..VV..V.",
            ".V....V..",
            "..VVVV..."),
        "goutte" to arrayOf(
            ".C.",
            ".C.",
            "CCC",
            "CWC",
            ".C."),
        "vague" to arrayOf(
            ".YY..",
            "Y..YY"),
        "vapeur" to arrayOf(
            ".S.",
            "SSS",
            ".S."),
        "crane" to arrayOf(
            "....WWWWW....",
            "..WWWWWWWWW..",
            ".WWWWWWWWWWW.",
            "WWWWWWWWWWWWW",
            "WWWWWWWWWWWWW",
            "WWRKRWWWRKRWW",
            "WWKRKWWWKRKWW",
            "WWRKRWWWRKRWW",
            ".WWWWWKWWWWW.",
            "..WWWKKKWWW..",
            "...WWWWWWW...",
            "...WKWKWKW...",
            "...WWWWWWW..."),
        "os" to arrayOf(
            "SW.............WS",
            "WWW...........WWW",
            "..WWW.......WWW..",
            "....WWW...WWW....",
            "......WWWWW......",
            "....WWW...WWW....",
            "..WWW.......WWW..",
            "WWW...........WWW",
            "SW.............WS"),
    )

    // ------------------------------------------------------------ couleurs (0xRRGGBB)
    private fun sombre(c: Int): Int {
        val r = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
        return (r * 50 / 100 shl 16) or (g * 55 / 100 shl 8) or minOf(255, b * 70 / 100 + 24)
    }

    private fun gris(c: Int): Int {
        val r = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
        val l = (r * 30 + g * 59 + b * 11) / 100 * 75 / 100 + 60
        return (l shl 16) or (l shl 8) or minOf(255, l + 14)
    }

    private fun rouge(c: Int): Int {
        val r = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
        return ((r + 3 * 235) / 4 shl 16) or (g * 40 / 100 shl 8) or (b * 35 / 100)
    }

    // ------------------------------------------------------------ outils
    /** Générateur congruentiel (identique côté Python). */
    private class Hasard(graine: Int) {
        var s: Long = graine.toLong() and 0x7FFFFFFFL
        fun n(k: Int): Int {
            s = (s * 1103515245L + 12345L) and 0x7FFFFFFFL
            return ((s shr 8) % k).toInt()
        }
    }

    private fun fdiv(a: Int, b: Int) = Math.floorDiv(a, b)

    private fun dim(n: Int, pct: Int) = maxOf(1, (n * pct + 50) / 100)

    private class Spr(val w: Int, val h: Int, val o: IntArray)

    /** Coupe les bords transparents. */
    private fun rogner(w: Int, h: Int, octets: ByteArray): Spr {
        var x0 = w; var y0 = h; var x1 = -1; var y1 = -1
        for (y in 0 until h) for (x in 0 until w) {
            if (octets[y * w + x].toInt() and 0xFF != 0) {
                x0 = minOf(x0, x); y0 = minOf(y0, y); x1 = maxOf(x1, x); y1 = maxOf(y1, y)
            }
        }
        if (x1 < 0) return Spr(1, 1, IntArray(1))
        val nw = x1 - x0 + 1; val nh = y1 - y0 + 1
        val o = IntArray(nw * nh)
        for (y in 0 until nh) for (x in 0 until nw) o[y * nw + x] = octets[(y0 + y) * w + x0 + x].toInt() and 0xFF
        return Spr(nw, nh, o)
    }

    private class Toile(val w: Int, val h: Int, val sp: Int) {
        val px = ByteArray(w * h)

        fun c(code: Char): Int = sp + 1 + CODES.indexOf(code)

        fun pt(x: Int, y: Int, v: Int) {
            if (x in 0 until w && y in 0 until h) px[y * w + x] = v.toByte()
        }

        fun glyphe(nom: String, x: Int, y: Int, quart: Int = 0, contour: Boolean = true, ech: Int = 1) {
            val g = GLYPHES.getValue(nom)
            val gh = g.size; val gw = g[0].length
            for (passe in (if (contour) 0 else 1)..1) {
                for (r in 0 until gh) for (q in 0 until gw) {
                    val ch = g[r][q]
                    if (ch == '.') continue
                    val X: Int; val Y: Int
                    when (quart) {
                        1 -> { X = gh - 1 - r; Y = q }
                        2 -> { X = gw - 1 - q; Y = gh - 1 - r }
                        3 -> { X = r; Y = gw - 1 - q }
                        else -> { X = q; Y = r }
                    }
                    val de = if (passe == 0) -1 else 0
                    val a = if (passe == 0) ech + 1 else ech
                    val col = c(if (passe == 0) 'K' else ch)
                    for (ey in de until a) for (ex in de until a) pt(x + X * ech + ex, y + Y * ech + ey, col)
                }
            }
        }

        /** Voir Toile.sprite en Python : mêmes paramètres, même calcul. */
        fun sprite(s: Spr, cx: Int, base: Int, nw: Int, nh: Int, dx: Int = 0, dy: Int = 0, pench: Int = 0,
                   off: Int = 0, alt: Int = 0, mix: Int = 0, blanc: Int = 0, rot: Int = 0, sil: Int = 0,
                   trame: Int = 0) {
            val dw = if (rot == 1) nh else nw
            val dh = if (rot == 1) nw else nh
            val x0 = cx - dw / 2 + dx
            val y0 = base - dh + dy
            val blancI = c('W')
            for (j in 0 until dh) {
                val y = y0 + j
                if (y < 0 || y >= h) continue
                val dec = fdiv(pench * (dh - 1 - j), 100)
                for (i in 0 until dw) {
                    val x = x0 + i + dec
                    if (x < 0 || x >= w) continue
                    val u: Int; val v: Int
                    when (rot) {
                        1 -> { u = j; v = nh - 1 - i }
                        2 -> { u = i; v = nh - 1 - j }
                        else -> { u = i; v = j }
                    }
                    var valeur = s.o[((2 * v + 1) * s.h) / (2 * nh) * s.w + ((2 * u + 1) * s.w) / (2 * nw)]
                    if (valeur == 0) continue
                    val b = BAYER[(y and 3) * 4 + (x and 3)]
                    if ((trame > 0 && b >= trame) || (trame < 0 && b < -trame)) continue
                    valeur = if (sil != 0) sil else valeur + (if (b < mix) alt else off)
                    if (b < blanc) valeur = blancI
                    px[y * w + x] = valeur.toByte()
                }
            }
        }
    }

    private fun eclat(t: Toile, x: Int, y: Int, L: Int, creux: Boolean = false) {
        val dirs = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1),
            intArrayOf(1, 1), intArrayOf(1, -1), intArrayOf(-1, 1), intArrayOf(-1, -1))
        for (k in 0 until 8) {
            val ux = dirs[k][0]; val uy = dirs[k][1]
            val n = if (k < 4) L else (L * 2) / 3
            for (r in 1..n) {
                if (creux && r <= n / 2) continue
                t.pt(x + ux * r, y + uy * r, t.c(if (r <= n / 3) 'W' else if (r < n) 'Y' else 'O'))
            }
        }
        if (!creux) t.pt(x, y, t.c('W'))
    }

    private fun bulle(t: Toile, x: Int, y: Int, points: Int, e: Int = 1) {
        fun pb(i: Int, j: Int, code: Char) {
            for (b in 0 until e) for (a in 0 until e) t.pt(x + i * e + a, y + j * e + b, t.c(code))
        }
        for (j in 0 until 6) for (i in 0 until 14) {
            if ((j == 0 || j == 5) && (i == 0 || i == 13)) continue
            val bord = j == 0 || j == 5 || i == 0 || i == 13
            pb(i, j, if (bord) 'K' else 'W')
        }
        for (k in 0 until points) for (a in 0 until 2) for (b in 0 until 2) pb(2 + 4 * k + a, 2 + b, 'K')
        pb(3, 5, 'W'); pb(2, 6, 'K'); pb(3, 6, 'W'); pb(4, 6, 'K'); pb(1, 7, 'K'); pb(2, 7, 'K')
    }

    // ------------------------------------------------------------ les animations
    private class Ctx(val spr: Spr, val largeur: Int, val hauteur: Int, val sp: Int, val pal: IntArray = IntArray(0)) {
        val w = spr.w
        val h = spr.h
        val cx = largeur / 2
        val base = hauteur - 2
        val top = base - h
        val left = cx - w / 2
        val right = left + w
        val e = if (maxOf(w, h) >= 40) 2 else 1
        val frames = ArrayList<ByteArray>()
        var vie: VieInfo? = null

        fun toile() = Toile(largeur, hauteur, sp)

        fun pose(t: Toile, sx: Int = 100, sy: Int = 100, dx: Int = 0, dy: Int = 0, pench: Int = 0, off: Int = 0,
                 alt: Int = 0, mix: Int = 0, blanc: Int = 0, rot: Int = 0, sil: Int = 0) =
            t.sprite(spr, cx, base, dim(w, sx), dim(h, sy), dx, dy, pench, off, alt, mix, blanc, rot, sil)

        fun garder(t: Toile) { frames.add(t.px) }
    }

    /** Au repos : la vie dans la créature (Vie.kt : yeux qui clignent, haut du corps qui respire, parties fines qui
     *  ondulent, petits regards), 64 images ; si rien n'est sûr sur cette image, l'écrasement doux d'avant (8 images). */
    private fun statique(c: Ctx) {
        val a = Vie.analyseGardee(c.w, c.h, c.spr.o, c.pal)
        if (a != null) {
            val W2 = Vie.largeur(a); val H2 = Vie.hauteur(a)
            c.vie = VieInfo(a, c.cx - W2 / 2, c.base - H2)
            for (k in 0 until Vie.CYCLE) {
                val img = Vie.image(a, k)
                val t = c.toile()
                t.sprite(Spr(W2, H2, IntArray(img.size) { img[it].toInt() and 0xFF }), c.cx, c.base, W2, H2)
                c.garder(t)
            }
            return
        }
        val sy = intArrayOf(100, 99, 97, 96, 96, 97, 99, 100)
        val sx = intArrayOf(100, 100, 101, 102, 102, 101, 100, 100)
        for (f in 0 until 8) {
            val t = c.toile()
            c.pose(t, sx[f], sy[f])
            c.garder(t)
        }
    }

    private fun miettes(t: Toile, x: Int, y: Int, debut: Int, f: Int) {
        val a = f - debut
        if (a < 0 || a > 3) return
        val r = Hasard(debut * 31 + 7)
        repeat(6) {
            val px = x + r.n(5) - 2
            val py = y + r.n(4) - 1
            val vx = r.n(5) - 2
            val col = "RSW"[r.n(3)]
            t.pt(px + vx * a, py + a * (a + 1) / 2 + a, t.c(col))
        }
    }

    private fun mange(c: Ctx) {
        val ax = c.right - 2
        val ay = c.top + c.h * 40 / 100 - 3
        val sx0 = c.largeur - 8
        val sy0 = maxOf(0, c.top - 8)
        val vol = intArrayOf(0, 35, 70, 100)
        val arc = intArrayOf(0, 3, 2, 0)
        val croc = mapOf(4 to "pomme1", 6 to "pomme2", 8 to "trognon")
        val pench = intArrayOf(0, 0, 4, 8, 12, 6, 12, 6, 12, 4, 0, 0)
        val sx = intArrayOf(100, 100, 100, 101, 104, 100, 104, 100, 104, 100, 100, 101)
        val sy = intArrayOf(100, 100, 100, 99, 94, 100, 94, 100, 94, 100, 97, 100)
        val dx = intArrayOf(0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0)
        for (f in 0 until 12) {
            val t = c.toile()
            c.pose(t, sx[f], sy[f], dx = dx[f], pench = pench[f])
            if (f < 4) {
                val x = sx0 + fdiv((ax - sx0) * vol[f], 100)
                val y = sy0 + fdiv((ay - sy0) * vol[f], 100) - arc[f]
                t.glyphe("pomme", x, y)
            } else if (f < 9) {
                t.glyphe(croc[f] ?: croc.getValue(f - 1), ax, ay)
            } else if (f == 9) {
                t.glyphe("trognon", ax, ay + 3)
            }
            for (d in intArrayOf(4, 6, 8)) miettes(t, ax + 2, ay + 4, d, f)
            if (f >= 10) t.glyphe("point", c.right, c.top - 3 - (f - 10) * 2)
            c.garder(t)
        }
    }

    private fun attaque(c: Ctx) {
        val elan = maxOf(4, c.w / 5)
        val p = intArrayOf(0, -25, -60, -80, 70, 100, 90, 60, 30, 10)
        val sx = intArrayOf(100, 104, 108, 110, 112, 104, 100, 100, 100, 100)
        val sy = intArrayOf(100, 97, 94, 92, 94, 100, 102, 100, 100, 100)
        val pench = intArrayOf(0, -5, -10, -12, 15, 10, 0, 0, 0, 0)
        val secousse = intArrayOf(0, 0, 0, 0, 0, -1, 1, 0, 0, 0)
        val L = maxOf(4, c.h / 5)
        for (f in 0 until 10) {
            val t = c.toile()
            val dx = fdiv(elan * p[f], 100)
            c.pose(t, sx[f], sy[f], dx = dx, dy = secousse[f], pench = pench[f])
            val ex = minOf(c.right + dx + L / 2 + 1, c.largeur - 2 - L)
            val ey = c.top + c.h / 2
            if (f == 4) {
                for (k in 0 until 3) {
                    t.pt(c.left + dx - 2 - 3 * k, c.top + c.h / 3 + 3 * k, t.c('S'))
                    t.pt(c.left + dx - 3 - 3 * k, c.top + c.h / 3 + 3 * k, t.c('S'))
                }
            }
            when (f) {
                5 -> eclat(t, ex, ey, L * 2 / 3)
                6 -> eclat(t, ex, ey, L)
                7 -> eclat(t, ex, ey, L + 1, creux = true)
            }
            c.garder(t)
        }
    }

    private fun salut(c: Ctx) {
        val saut = maxOf(3, c.h / 6)
        val p = intArrayOf(0, 0, 40, 80, 100, 80, 40, 0, 0, 0)
        val sy = intArrayOf(100, 92, 104, 104, 100, 104, 104, 94, 100, 100)
        val sx = intArrayOf(100, 106, 97, 97, 100, 97, 97, 106, 100, 100)
        for (f in 0 until 10) {
            val t = c.toile()
            c.pose(t, sx[f], sy[f], dy = -(saut * p[f] / 100))
            if (f in 3..8) {
                t.glyphe("etoile", c.right - 3, c.top - 10 - (f - 3))
                if (f % 2 == 1) t.glyphe("point", c.right + 4, c.top - 6 - (f - 3))
            } else if (f == 9) {
                t.glyphe("etincelle", c.right - 2, c.top - 16)
            }
            c.garder(t)
        }
    }

    private fun parle(c: Ctx) {
        val points = intArrayOf(1, 1, 2, 2, 3, 3, 3, 0, 3, 0, 3, 3)
        val sy = intArrayOf(100, 97, 100, 97, 100, 97, 100, 100, 100, 100, 97, 100)
        val bx = minOf(c.largeur - 1 - 14 * c.e, c.right - 3 * c.e)
        val by = maxOf(0, c.top - 10 * c.e)
        for (f in 0 until 12) {
            val t = c.toile()
            c.pose(t, 100, sy[f])
            bulle(t, bx, by, points[f], c.e)
            c.garder(t)
        }
    }

    private fun dort(c: Ctx) {
        val sy = intArrayOf(90, 90, 89, 88, 88, 87, 87, 88, 88, 89, 90, 90)
        val sx = intArrayOf(105, 105, 105, 106, 106, 107, 107, 106, 106, 105, 105, 105)
        val n = c.sp / 2
        for (f in 0 until 12) {
            val t = c.toile()
            c.pose(t, sx[f], sy[f], off = n)
            val haut = c.base - dim(c.h, sy[f])
            for (i in 0 until 3) {
                val p = (f + 4 * i) % 12
                if (p > 10) continue
                val x = c.right - 3 + p / 2 + (i % 2)
                val y = haut - 3 - p
                if (p < 5) t.glyphe("z", x, y) else t.glyphe("Z", x, y - 1)
            }
            c.garder(t)
        }
    }

    private fun content(c: Ctx) {
        val saut = maxOf(3, c.h / 4)
        val b = intArrayOf(0, 55, 90, 90, 55, 0, 0, 55, 90, 90, 55, 0)
        val sy = intArrayOf(92, 104, 100, 100, 104, 94, 92, 104, 100, 100, 104, 94)
        val sx = intArrayOf(108, 96, 100, 100, 96, 106, 108, 96, 100, 100, 96, 106)
        val houle = intArrayOf(0, 1, 1, 0, -1, -1)
        for (f in 0 until 12) {
            val t = c.toile()
            c.pose(t, sx[f], sy[f], dy = -(saut * b[f] / 100))
            for (i in 0 until 3) {
                val p = (f + 4 * i) % 12
                if (p > 9) continue
                val x = c.left - 3 + (i * (c.w + 2)) / 2 + houle[p % 6]
                val y = c.top - 4 - p
                t.glyphe(if (p < 6) "coeur" else "petit_coeur", x, y)
            }
            c.garder(t)
        }
    }

    private fun affame(c: Ctx) {
        val tremble = intArrayOf(0, 1, 0, -1)
        val sy = intArrayOf(98, 97, 98, 97, 98, 97, 98, 97, 98, 97, 98, 97)
        for (f in 0 until 12) {
            val t = c.toile()
            val gargouille = f % 4 >= 2
            c.pose(t, if (gargouille) 103 else 100, sy[f], dx = tremble[f % 4])
            val p = f % 6
            t.glyphe("goutte", c.left - 2, c.top + 1 + p)
            val q = (f + 3) % 6
            t.glyphe("goutte", c.right - 1, c.top + q)
            if (gargouille) {
                val yb = c.top + c.h * 65 / 100
                t.glyphe("vague", c.right + 2, yb, contour = false)
                t.glyphe("vague", c.right + 3 + (f % 2), yb + 3, contour = false)
            }
            c.garder(t)
        }
    }

    private fun confus(c: Ctx) {
        val pench = intArrayOf(0, 8, 14, 16, 14, 8, 0, -8, -14, -16, -14, -8)
        for (f in 0 until 12) {
            val t = c.toile()
            c.pose(t, pench = pench[f])
            val hx = c.cx + fdiv(pench[f] * c.h, 100)
            val e = c.e
            val y = maxOf(1, c.top - 11 * e)
            t.glyphe("spirale", hx - 11 * e, y + (f % 2) * e, quart = f % 4, ech = e)
            t.glyphe("spirale", hx + 2 * e, y + (1 - f % 2) * e, quart = (f + 2) % 4, ech = e)
            c.garder(t)
        }
    }

    private fun colere(c: Ctx) {
        val mix = intArrayOf(10, 16, 16, 16, 16, 12, 16, 16, 16, 16)
        val dx = intArrayOf(0, 2, -2, 1, -1, 2, -2, 1, -1, 0)
        val dy = intArrayOf(0, 0, 1, 0, 1, 0, 0, 1, 0, 0)
        val sy = intArrayOf(100, 102, 103, 103, 102, 103, 103, 102, 101, 100)
        val n = c.sp / 2
        for (f in 0 until 10) {
            val t = c.toile()
            c.pose(t, 100, sy[f], dx = dx[f], dy = dy[f], alt = n, mix = mix[f])
            if (f % 5 != 4) {
                val g = if (f % 2 == 1) c.e else 0
                t.glyphe("colere", c.right - 5 * c.e - g, maxOf(1, c.top - 7 * c.e) - g, ech = c.e)
            }
            val p = f % 5
            t.glyphe("vapeur", c.left - 1 - p / 2, c.top - 1 - p, contour = false)
            val q = (f + 2) % 5
            t.glyphe("vapeur", c.left + 2 - q / 2, c.top - 3 - q, contour = false)
            c.garder(t)
        }
    }

    private fun victoire(c: Ctx) {
        val saut = maxOf(5, (c.top * 2) / 3)
        val p = intArrayOf(0, 0, 45, 75, 95, 100, 95, 75, 45, 0, 0, 0, 0, 0)
        val sy = intArrayOf(100, 88, 108, 106, 104, 100, 100, 104, 106, 90, 96, 100, 100, 100)
        val sx = intArrayOf(100, 110, 94, 96, 98, 100, 100, 98, 96, 110, 104, 100, 100, 100)
        val places = arrayOf(
            intArrayOf(c.left - 8, c.top + c.h / 4), intArrayOf(c.right + 1, c.top + c.h / 5),
            intArrayOf(c.left - 4, c.top - 6), intArrayOf(c.right - 3, c.top - 9), intArrayOf(c.cx - 3, c.top - 14),
            intArrayOf(c.left - 9, c.top + c.h / 2), intArrayOf(c.right + 2, c.top + c.h / 2))
        for (f in 0 until 14) {
            val t = c.toile()
            for (k in places.indices) {
                if (f < 3 + k / 2) continue
                val x = places[k][0]; val y = places[k][1]
                when ((f + 2 * k) % 4) {
                    0 -> t.glyphe("etoile", x, y)
                    1, 3 -> t.glyphe("etincelle", x + 1, y + 1)
                    else -> t.glyphe("point", x + 2, y + 2)
                }
            }
            c.pose(t, sx[f], sy[f], dy = -(saut * p[f] / 100))
            c.garder(t)
        }
    }

    private fun echCrane(D: Int) = if (D >= 40) 2 else 1

    private fun ko(c: Ctx) {
        val n = c.sp / 2
        val couche = c.h >= c.w
        val pen = intArrayOf(15, 35, 60)
        val ecr = intArrayOf(70, 35, 35)
        val flottes = intArrayOf(5, 2, -1, 0, 0, -1, -1, 0, 0, -1)
        for (f in 0 until 16) {
            val t = c.toile()
            if (f == 0) {
                c.pose(t, 108, 92, dx = -1, blanc = 8)
            } else if (f <= 3) {
                if (couche) c.pose(t, pench = pen[f - 1], alt = n, mix = 4 * f)
                else c.pose(t, 100, ecr[f - 1], rot = if (f == 3) 2 else 0, alt = n, mix = 4 * f)
            } else {
                val rebond = if (f == 4) -2 else 0
                if (couche) c.pose(t, rot = 1, dy = rebond, alt = n, mix = 16)
                else c.pose(t, 100, if (f == 4) 80 else 100, rot = 2, dy = rebond, alt = n, mix = 16)
            }
            if (f >= 6) {
                val haut = if (couche) c.w else c.h
                val e = echCrane(maxOf(c.w, c.h))
                val flotte = flottes[f - 6] * e
                val y = maxOf(1, c.base - haut - 16 * e) + flotte
                if (f >= 8) t.glyphe("os", c.cx - 8 * e - e / 2, y + 6 * e, ech = e)
                t.glyphe("crane", c.cx - 6 * e - e / 2, y, ech = e)
            }
            c.garder(t)
        }
    }

    private fun evolution(c: Ctx, ancien: Spr, nNouv: Int, tBlanc: Int) {
        val r = Hasard(4242)
        val ow = ancien.w; val oh = ancien.h
        for (f in 0 until 16) {
            val t = c.toile()
            if (f < 4) {
                t.sprite(ancien, c.cx, c.base, ow, oh, off = nNouv, blanc = 4 * f)
            } else if (f < 6) {
                val k = if (f == 4) 104 else 96
                t.sprite(ancien, c.cx, c.base, dim(ow, k), dim(oh, k), sil = tBlanc)
            } else if (f < 10) {
                val m = 4 * (f - 5)
                val tw = ow + fdiv((c.w - ow) * m, 16)
                val th = oh + fdiv((c.h - oh) * m, 16)
                t.sprite(ancien, c.cx, c.base, maxOf(1, tw), maxOf(1, th), sil = tBlanc, trame = -m)
                val nw = c.w + fdiv((ow - c.w) * (16 - m), 16)
                val nh = c.h + fdiv((oh - c.h) * (16 - m), 16)
                t.sprite(c.spr, c.cx, c.base, maxOf(1, nw), maxOf(1, nh), sil = tBlanc, trame = m)
            } else if (f < 12) {
                c.pose(t, sil = tBlanc)
                val L = if (f == 10) (c.h * 2) / 3 else c.h / 2
                eclat(t, c.cx, c.base - c.h / 2, L, creux = f == 11)
            } else {
                c.pose(t, blanc = 4 * (15 - f))
            }
            if (f >= 2) {
                repeat(5) {
                    val x = c.left - 4 + r.n(c.w + 8)
                    val y = c.top - 4 + r.n(c.h + 4)
                    t.glyphe(if (r.n(2) != 0) "point" else "etincelle", x, y)
                }
            }
            c.garder(t)
        }
    }

    // ------------------------------------------------------------ API
    /**
     * Calcule les images d'une animation. palette : couleurs du sprite (0xRRGGBB ou ARGB, l'alpha est ignoré).
     * de : le stade précédent, pour « evolution » (sinon l'évolution part du même sprite).
     */
    fun images(w: Int, h: Int, octets: ByteArray, palette: IntArray, nom: String, de: Sprite? = null): Anim {
        val spr = rogner(w, h, octets)
        val base = IntArray(palette.size) { palette[it] and 0xFFFFFF }
        val N = base.size
        var pal: IntArray
        val nTeinte: Int
        var ancien: Spr? = null
        val lw: Int; val lh: Int
        if (nom == "evolution") {
            val palA: IntArray
            if (de != null) {
                ancien = rogner(de.w, de.h, de.octets)
                palA = IntArray(de.palette.size) { de.palette[it] and 0xFFFFFF }
            } else {
                ancien = spr
                palA = base.copyOf()
            }
            pal = base + palA
            nTeinte = pal.size
            lw = maxOf(spr.w, ancien.w); lh = maxOf(spr.h, ancien.h)
        } else {
            pal = when (nom) {
                "dort" -> base + IntArray(N) { sombre(base[it]) }
                "colere" -> base + IntArray(N) { rouge(base[it]) }
                "ko" -> base + IntArray(N) { gris(base[it]) }
                else -> base
            }
            nTeinte = if (nom == "dort") 2 * N else N
            lw = spr.w; lh = spr.h
        }
        val sp = pal.size
        pal += SPECIAUX
        val D = maxOf(lw, lh)
        val mx = 8 + D / 8
        var mt = 12 + D / 4
        if (nom == "ko") mt = maxOf(mt, 16 * echCrane(D) + 2 - (lh - minOf(lw, lh)))
        val W = D + 2 * mx
        var H = lh + mt + 2
        if (H % 2 != 0) H += 1
        val c = Ctx(spr, W, H, sp, base)
        when (nom) {
            "statique" -> statique(c)
            "mange" -> mange(c)
            "attaque" -> attaque(c)
            "salut" -> salut(c)
            "parle" -> parle(c)
            "dort" -> dort(c)
            "content" -> content(c)
            "affame" -> affame(c)
            "confus" -> confus(c)
            "colere" -> colere(c)
            "victoire" -> victoire(c)
            "ko" -> ko(c)
            "evolution" -> evolution(c, ancien!!, N, sp + 1)
            else -> throw IllegalArgumentException("animation inconnue : $nom")
        }
        val argb = IntArray(pal.size) { pal[it] or 0xFF000000.toInt() }
        return Anim(W, H, c.frames, argb, nTeinte, vie = c.vie)
    }

    /** Variante pratique : à partir d'un Sprite. */
    fun images(s: Sprite, nom: String, de: Sprite? = null): Anim = images(s.w, s.h, s.octets, s.palette, nom, de)

    private var paletteGardee: Triple<Any, Double?, IntArray>? = null

    /**
     * UNE image de l'animation (numéro k, modulo leur nombre) en Bitmap agrandie sans lissage : pour la vie au repos,
     * calculée image par image au moment de l'afficher (pas 64 grandes images en mémoire).
     */
    fun bitmap(anim: Anim, k: Int, echelle: Int, teinte: Double?, glitch: Glitch.Spec? = null): Bitmap {
        val g = paletteGardee
        val pal = if (g != null && g.first === anim && g.second == teinte) g.third else {
            val p = anim.palette.copyOf()
            if (teinte != null) for (i in 0 until anim.nTeinte) p[i] = Bestiaire.decaler(p[i] and 0xFFFFFF, teinte) or 0xFF000000.toInt()
            paletteGardee = Triple(anim, teinte, p)
            p
        }
        val e = maxOf(1, echelle)
        val W = anim.largeur; val H = anim.hauteur
        val v = anim.vie
        if (v != null) {                     // la vie au pixel fin : respiration et ondulations sans gros saut
            val a = v.analyse
            val fine = Vie.imageFine(a, k, e)
            val WF = Vie.largeur(a) * e; val HF = Vie.hauteur(a) * e
            val px = IntArray(W * e * H * e)
            val ox = v.x0 * e; val oy = v.y0 * e
            for (y in 0 until HF) {
                val Y = oy + y
                if (Y < 0 || Y >= H * e) continue
                for (x in 0 until WF) {
                    val X = ox + x
                    if (X < 0 || X >= W * e) continue
                    val c = fine[y * WF + x].toInt() and 0xFF
                    if (c != 0) px[Y * W * e + X] = pal[c - 1]
                }
            }
            // le glitch par-dessus la vie (un pixel de créature = e pixels fins), comme rendu_fin.composer_vie sur PC
            return Bitmap.createBitmap(Glitch.sur(W * e, H * e, px, glitch, e), W * e, H * e, Bitmap.Config.ARGB_8888)
        }
        if (glitch != null) {                  // le glitch : sur l'image au pixel de créature, puis agrandie
            val img = anim.images[Math.floorMod(k, anim.images.size)]
            val px = IntArray(W * H) { val v = img[it].toInt() and 0xFF; if (v == 0) 0 else pal[v - 1] }
            return agrandir(Glitch.sur(W, H, px, glitch), W, H, e)
        }
        val img = anim.images[Math.floorMod(k, anim.images.size)]
        val ligne = IntArray(W * e)
        val bmp = Bitmap.createBitmap(W * e, H * e, Bitmap.Config.ARGB_8888)
        for (y in 0 until H) {
            for (x in 0 until W) {
                val v = img[y * W + x].toInt() and 0xFF
                val col = if (v == 0) 0 else pal[v - 1]
                for (a in 0 until e) ligne[x * e + a] = col
            }
            for (b in 0 until e) bmp.setPixels(ligne, 0, W * e, 0, y * e + b, W * e, 1)
        }
        return bmp
    }

    /**
     * Les images en Bitmap agrandies sans lissage (echelle × echelle par pixel).
     * teinte (0..1, null = normal) : shiny, décalage de teinte des couleurs de la bestiole seulement
     * (Bestiaire.decaler, comme B.decaler dans anim_auto.lignes sur PC).
     */
    /** Des pixels ARGB (W × H) agrandis sans lissage (e × e par pixel). */
    fun agrandir(px: IntArray, W: Int, H: Int, e: Int): Bitmap {
        val ligne = IntArray(W * e)
        val bmp = Bitmap.createBitmap(W * e, H * e, Bitmap.Config.ARGB_8888)
        for (y in 0 until H) {
            for (x in 0 until W) { val c = px[y * W + x]; for (a in 0 until e) ligne[x * e + a] = c }
            for (b in 0 until e) bmp.setPixels(ligne, 0, W * e, 0, y * e + b, W * e, 1)
        }
        return bmp
    }

    fun bitmaps(anim: Anim, echelle: Int, teinte: Double?, glitch: Glitch.Spec? = null): List<Bitmap> {
        val pal = anim.palette.copyOf()
        if (teinte != null) {
            for (k in 0 until anim.nTeinte) pal[k] = Bestiaire.decaler(pal[k] and 0xFFFFFF, teinte) or 0xFF000000.toInt()
        }
        val e = maxOf(1, echelle)
        val W = anim.largeur; val H = anim.hauteur
        if (glitch != null) return anim.images.map { img ->
            agrandir(Glitch.sur(W, H, IntArray(W * H) { val v = img[it].toInt() and 0xFF; if (v == 0) 0 else pal[v - 1] }, glitch), W, H, e)
        }
        val ligne = IntArray(W * e)
        return anim.images.map { img ->
            val bmp = Bitmap.createBitmap(W * e, H * e, Bitmap.Config.ARGB_8888)
            for (y in 0 until H) {
                for (x in 0 until W) {
                    val v = img[y * W + x].toInt() and 0xFF
                    val col = if (v == 0) 0 else pal[v - 1]
                    for (a in 0 until e) ligne[x * e + a] = col
                }
                for (b in 0 until e) bmp.setPixels(ligne, 0, W * e, 0, y * e + b, W * e, 1)
            }
            bmp
        }
    }
}
