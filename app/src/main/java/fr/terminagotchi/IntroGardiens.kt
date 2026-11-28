package fr.terminagotchi

import org.json.JSONObject

/**
 * L'écran 3 de l'intro (9 novembre, planche validée) : « Les gardiens dorment aussi ». Dessiné par le code avec les
 * vrais dessins du jeu, comme sur PC (pc/tg/scenes.py, gardiens) : sur un fond de lignes de données, les bébés des
 * 9 biomes endormis (Zz), le cœur du monde, et dessous Abyssor, le gardien, en silhouette sombre qui dort (pas
 * effrayante : pas d'yeux, pas de couleur, juste une lueur violette). Les espèces : intro.json « gardiens ».
 * Les étiquettes (« le cœur du monde », « Abyssor, le gardien ») sont écrites par Intro.dessinerEcran.
 */
object IntroGardiens {
    /** Lit un fichier des assets (Intro.init ; le test JVM le donne aussi). */
    @Volatile var lecteur: ((String) -> String?)? = null

    const val FOND = 0xFF0A0E16.toInt()
    const val SILHOUETTE = 0xFF241E3E.toInt()
    const val COEUR_X = 0.5f
    const val COEUR_Y = 0.62f

    private fun rgb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r.coerceIn(0, 255) shl 16) or (g.coerceIn(0, 255) shl 8) or b.coerceIn(0, 255)

    /** Une couleur endormie (comme le camp endormi, un peu moins sombre). */
    private fun dormir(c: Int): Int {
        val r = (c shr 16) and 255; val g = (c shr 8) and 255; val b = c and 255
        val gris = 0.299f * r + 0.587f * g + 0.114f * b
        fun v(x: Int, bleu: Int) = (((gris + (x - gris) * 0.45f) * 0.75f) * 0.8f + bleu * 0.2f).toInt()
        return rgb(v(r, 20), v(g, 28), v(b, 60))
    }

    /** Pose un calque (0 = transparent) agrandi ou réduit à dw×dh (plus proche voisin) en (x0, y0). */
    private fun poser(px: IntArray, W: Int, H: Int, cal: IntArray, cw: Int, ch: Int, x0f: Float, y0f: Float, dwf: Float, dhf: Float) {
        val x0 = Math.round(x0f); val y0 = Math.round(y0f)
        val dw = maxOf(1, Math.round(dwf)); val dh = maxOf(1, Math.round(dhf))
        for (y in 0 until dh) {
            val Y = y0 + y
            if (Y !in 0 until H) continue
            val sy = minOf(ch - 1, y * ch / dh)
            for (x in 0 until dw) {
                val X = x0 + x
                if (X !in 0 until W) continue
                val q = cal[sy * cw + minOf(cw - 1, x * cw / dw)]
                val a = q ushr 24
                if (a == 0) continue
                if (a >= 255) { px[Y * W + X] = q or (0xFF shl 24); continue }
                val f = px[Y * W + X]; val k = a / 255f
                fun m(s: Int) = (((f shr s) and 255) + (((q shr s) and 255) - ((f shr s) and 255)) * k).toInt()
                px[Y * W + X] = rgb(m(16), m(8), m(0))
            }
        }
    }

    /** Une lueur ronde (ajoutée), comme scenes._lueur. */
    private fun lueur(px: IntArray, W: Int, H: Int, cx: Float, cy: Float, r: Float, c: Int, force: Float) {
        for (y in maxOf(0, (cy - r).toInt())..minOf(H - 1, (cy + r).toInt())) for (x in maxOf(0, (cx - r).toInt())..minOf(W - 1, (cx + r).toInt())) {
            val d = Math.hypot((x + 0.5 - cx), (y + 0.5 - cy)).toFloat() / r
            if (d >= 1f) continue
            val f = (1 - d) * (1 - d) * force
            val p = px[y * W + x]
            fun a(s: Int) = (((p shr s) and 255) + ((c shr s) and 255) * f).toInt()
            px[y * W + x] = rgb(a(16), a(8), a(0))
        }
    }

    /** Un petit « z » de sommeil en pixels (4×4 fois e). */
    private val Z = listOf(0 to 0, 1 to 0, 2 to 0, 3 to 0, 2 to 1, 1 to 2, 0 to 3, 1 to 3, 2 to 3, 3 to 3)
    private fun zz(px: IntArray, W: Int, H: Int, x: Float, y: Float, e: Int, c: Int) {
        for ((dx, dy) in Z)
            for (i in 0 until e) for (j in 0 until e) {
                val X = (x + dx * e + i).toInt(); val Y = (y + dy * e + j).toInt()
                if (X in 0 until W && Y in 0 until H) px[Y * W + X] = c
            }
    }

    /** La forme du gardien qui dort (sa 1re image « dort », 48×48, assets/anim/<id>/pixels.json) : opaque ?, côté. */
    fun masque(gid: String): Pair<BooleanArray, Int>? {
        val texte = lecteur?.invoke("anim/$gid/pixels.json") ?: return null
        return try { masqueDe(JSONObject(texte)) } catch (e: Exception) { null }
    }

    private fun masqueDe(d: JSONObject): Pair<BooleanArray, Int> {
        val anims = d.getJSONObject("anims")
        val a = anims.optJSONObject("adulte")?.optJSONObject("dort") ?: anims.getJSONObject(anims.keys().next()).getJSONObject("statique")
        val n = d.optInt("taille", 48)
        val brut = java.util.Base64.getDecoder().decode(a.getJSONArray("images").getString(0))
        val o = if (d.optString("format") == "zlib") Bestiaire.gonfler(brut, n * n) else brut
        return BooleanArray(n * n) { it < o.size && o[it].toInt() != 0 } to n
    }

    private val cache = HashMap<String, Carte.Pix>()

    /** Les pixels de l'écran des gardiens (W×H). */
    fun pix(W: Int, H: Int): Carte.Pix = synchronized(cache) { cache.getOrPut("$W×$H") { dessiner(W, H) } }

    private fun dessiner(W: Int, H: Int): Carte.Pix {
        val g = Intro.d().optJSONObject("illustrations")?.optJSONObject("gardiens") ?: JSONObject()
        val px = IntArray(W * H) { FOND }
        // les lignes de données (racines à circuits)
        val pas = maxOf(4, W / 11)
        var k = 0
        var x = pas / 2
        while (x < W) {
            for (y in 0 until H) px[y * W + x] = rgb(26, 58, 40)
            var y = (H * (0.05f + (k * 37 % 80) / 400f)).toInt()
            while (y < H) {
                for (dx in -1..1) for (dy in -1..1) if ((dx != 0 || dy != 0) && x + dx in 0 until W && y + dy in 0 until H) px[(y + dy) * W + x + dx] = rgb(40, 92, 60)
                y += maxOf(6, (H * 0.26f).toInt())
            }
            x += pas; k++
        }
        for (j in 0 until W * H / 160) {                 // une pluie de pixels verts, légère
            val X = (Scenes.h(j, 1, 7) * W).toInt(); val Y = (Scenes.h(j, 2, 7) * H).toInt()
            px[Y * W + X] = rgb(40 + (60 * Scenes.h(j, 3, 7)).toInt(), 120 + (80 * Scenes.h(j, 4, 7)).toInt(), 70)
        }
        // les créatures des biomes qui dorment
        val especes = g.optJSONArray("especes")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        val n = maxOf(1, especes.size)
        val slot = W / (n + 0.6f)
        for ((i, eid) in especes.withIndex()) {
            val e = Bestiaire.espece(eid) ?: continue
            val s = Bestiaire.image(e, "bebe") ?: continue
            val cal = IntArray(s.w * s.h) { p -> val v = s.octets[p].toInt() and 0xFF; if (v == 0) 0 else dormir(s.palette[v - 1]) }
            var hb = minOf(H * 0.25f, slot * 1.05f)
            if (hb >= s.h) hb = (hb / s.h).toInt() * s.h.toFloat()   // de gros pixels réguliers (un nombre entier de fois)
            val dw = s.w * (hb / s.h)
            val cx = slot * (i + 0.8f)
            val bas = H * (0.47f + 0.07f * (i % 2))
            poser(px, W, H, cal, s.w, s.h, cx - dw / 2, bas - hb, dw, hb)
            val ez = maxOf(1, H / 70)
            zz(px, W, H, cx + dw * 0.35f, bas - hb - 5 * ez, ez, rgb(143, 163, 200))
        }
        // le cœur du monde, puis Abyssor qui dort dessous
        val cx = W * COEUR_X; val cy = H * COEUR_Y; val r = maxOf(2f, H * 0.045f)
        for (y in 0 until H) for (xx in 0 until W) {
            val d = Math.hypot(xx + 0.5 - cx, y + 0.5 - cy).toFloat()
            if (d in r * 0.75f..r * 1.15f || d <= r * 0.35f) px[y * W + xx] = rgb(95, 215, 135)
        }
        lueur(px, W, H, cx, cy, r * 2.4f, rgb(95, 215, 135), 0.35f)
        masque(g.optString("gardien", "abyssor"))?.let { (m, nn) ->
            var x0 = nn; var x1 = 0; var y0 = nn; var y1 = 0
            for (i in m.indices) if (m[i]) { x0 = minOf(x0, i % nn); x1 = maxOf(x1, i % nn + 1); y0 = minOf(y0, i / nn); y1 = maxOf(y1, i / nn + 1) }
            if (x1 <= x0) return@let
            val cw = x1 - x0; val ch = y1 - y0
            val dh = H * 0.30f
            val dw = cw * (dh / ch)
            val haut = cy + r * 1.6f
            val sil = IntArray(cw * ch) { p -> if (m[(y0 + p / cw) * nn + x0 + p % cw]) SILHOUETTE else 0 }
            val bord = IntArray(cw * ch) { p ->
                val xx = p % cw; val yy = p / cw
                if (sil[p] == 0 && listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1).any { (dx, dy) -> xx + dx in 0 until cw && yy + dy in 0 until ch && sil[(yy + dy) * cw + xx + dx] != 0 })
                    (110 shl 24) or (120 shl 16) or (90 shl 8) or 200 else 0
            }
            lueur(px, W, H, W / 2f, haut + dh * 0.55f, dh * 0.7f, rgb(70, 50, 130), 0.25f)
            poser(px, W, H, bord, cw, ch, W / 2f - dw / 2, haut, dw, dh)
            poser(px, W, H, sil, cw, ch, W / 2f - dw / 2, haut, dw, dh)
            val ez = maxOf(1, H / 60)
            zz(px, W, H, W / 2f + dw * 0.55f, haut + dh * 0.15f, ez, rgb(169, 155, 224))
            zz(px, W, H, W / 2f + dw * 0.55f + 5 * ez, haut - 2 * ez, ez + (if (H > 100) 1 else 0), rgb(169, 155, 224))
        }
        return Carte.Pix(W, H, px)
    }
}
