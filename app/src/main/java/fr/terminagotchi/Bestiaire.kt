package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.math.RoundingMode
import java.security.SecureRandom
import java.text.Normalizer
import java.util.zip.Inflater

/**
 * Le bestiaire commun (150 espèces + Abyssor), lu depuis assets/bestiaire.json (le même que le PC et le site).
 * Portage de pc/tg/bestiaire.py : tirage d'une apparition (espèce, variante, shiny), note et rareté de
 * L'INDIVIDU (stats, variante, puissance de l'espèce), images par stade (assets/sprites.bin), migration.
 */
object Bestiaire {
    class Variante(val id: String, val nom: String, val chance: Double, val score: Double, val zone: String, val habitat: String)

    class Espece(
        val id: String, val numero: Int, val nom: String, val famille: String, val icone: String,
        /** rareté « de base » de l'espèce (indicative) : la vraie rareté est celle de chaque individu */
        val rarete: String, val stat: String, val description: String, val comportement: String,
        val capacite: String, val habitat: String, val zone: String, val attireePar: String, val frequence: String,
        val puissance: Int, val tailleCm: Double, val poidsKo: Int, val stats: LinkedHashMap<String, Int>,
        val variantes: List<Variante>, val epreuves: List<String>,
        /** ancien dessin 16×16 (seulement Abyssor, qui garde ses animations faites main) */
        val sprite: List<String>, val spriteShiny: List<String>,
        val palette: Map<Char, Int>, val paletteShiny: Map<Char, Int>,
        val secrete: Boolean = false,
    )

    val RARETES = listOf("commune", "peu commune", "rare", "épique", "légendaire", "mythique")
    val COULEUR_RARETE = mapOf("commune" to 0xFFB0B0C0.toInt(), "peu commune" to 0xFF5FD787.toInt(),
        "rare" to 0xFF5FAFFF.toInt(), "épique" to 0xFFC77DFF.toInt(), "légendaire" to 0xFFFFAF00.toInt(),
        "mythique" to 0xFFFF5F87.toInt())
    val XP = mapOf("commune" to 15, "peu commune" to 25, "rare" to 40, "épique" to 65, "légendaire" to 100, "mythique" to 200)
    val STADES = listOf("bebe", "enfant", "ado", "adulte", "ancien")

    var especes: List<Espece> = emptyList()
        private set
    var marques: List<String> = emptyList()
        private set
    var humeurs: List<String> = emptyList()
        private set
    var habitats: Map<String, String> = emptyMap()
        private set
    var chanceShiny = 100
        private set
    var poidsFrequence: Map<String, Double> = emptyMap()
        private set
    var poidsNote: Map<String, Double> = emptyMap()
        private set
    var paliers: List<Pair<Double, String>> = emptyList()
        private set
    var speciales: Map<String, String> = emptyMap()
        private set
    private var anciens: Map<String, Int> = emptyMap()

    private var ctxApp: Context? = null
    private var sourceSprites: (() -> ByteArray?)? = null
    private var jeuxSprites: JSONObject? = null
    private val decodes = HashMap<String, AnimAuto.Sprite?>()
    private val images = HashMap<String, Bitmap>()
    private val portraits = HashMap<String, Bitmap?>()

    fun charger(ctx: Context) {
        if (especes.isNotEmpty()) return
        synchronized(this) {
            if (especes.isNotEmpty()) return
            ctxApp = ctx.applicationContext
            val texte = ctx.assets.open("bestiaire.json").bufferedReader().use { it.readText() }
            val app = ctx.applicationContext
            chargerDonnees(texte) { try { app.assets.open("sprites.bin").use { it.readBytes() } } catch (e: Exception) { null } }
        }
    }

    /** Lecture des données (séparée de l'appli : sert aussi aux tests sur ordinateur). */
    fun chargerDonnees(texte: String, sprites: () -> ByteArray?) {
        val o = JSONObject(texte)
        sourceSprites = sprites
        jeuxSprites = null
        decodes.clear()
        chanceShiny = o.optInt("chance_shiny", 100)
        val pf = o.getJSONObject("poids_frequence")
        poidsFrequence = pf.keys().asSequence().associateWith { pf.getDouble(it) }
        val r = o.getJSONObject("rarete")
        val po = r.getJSONObject("poids")
        poidsNote = po.keys().asSequence().associateWith { po.getDouble(it) }
        val pa = r.getJSONArray("paliers")
        paliers = (0 until pa.length()).map { pa.getJSONArray(it).let { p -> p.getDouble(0) to p.getString(1) } }
        val sp = r.optJSONObject("speciales") ?: JSONObject()
        speciales = sp.keys().asSequence().associateWith { sp.getString(it) }
        val an = o.optJSONObject("anciens") ?: JSONObject()
        anciens = an.keys().asSequence().associateWith { an.getInt(it) }
        val ha = o.getJSONObject("habitats")
        habitats = ha.keys().asSequence().associateWith { ha.getString(it) }
        marques = chaines(o.getJSONArray("marques"))
        humeurs = chaines(o.getJSONArray("humeurs"))
        val es = o.getJSONArray("especes")
        especes = (0 until es.length()).map { i ->
            val e = es.getJSONObject(i)
            fun lignes(k: String) = e.optJSONArray(k)?.let { chaines(it) } ?: emptyList()
            fun pal(k: String): Map<Char, Int> {
                val p = e.optJSONObject(k) ?: return emptyMap()
                return p.keys().asSequence().associate { it[0] to (hexa(p.getString(it)) or 0xFF000000.toInt()) }
            }
            val st = e.getJSONObject("stats")
            val va = e.optJSONArray("variantes") ?: JSONArray()
            val variantes = (0 until va.length()).map { k ->
                val v = va.getJSONObject(k)
                Variante(v.getString("id"), v.optString("nom", v.getString("id")), v.optDouble("chance", 1.0),
                    v.optDouble("score", 0.0), v.optString("zone", e.getString("zone")), v.optString("habitat", ""))
            }.ifEmpty { listOf(Variante("classique", "classique", 1.0, 0.0, e.getString("zone"), e.optString("habitat"))) }
            Espece(
                e.getString("id"), e.getInt("numero"), e.getString("nom"), e.getString("famille"),
                e.optString("icone"), e.optString("rarete", "commune"), e.optString("stat"), e.optString("description"),
                e.optString("comportement"), e.optString("capacite"), e.optString("habitat"), e.getString("zone"),
                e.optString("attiree_par"), e.optString("frequence"), e.optInt("puissance", 1),
                e.optDouble("taille_cm", 30.0), e.optInt("poids_ko"),
                LinkedHashMap(st.keys().asSequence().associateWith { st.getInt(it) }),
                variantes, e.optJSONArray("epreuves")?.let { chaines(it) } ?: emptyList(),
                lignes("sprite"), lignes("sprite_shiny"), pal("palette"), pal("palette_shiny"),
                e.optBoolean("secrete"),
            )
        }
    }

    private fun chaines(a: JSONArray) = (0 until a.length()).map { a.getString(it) }

    /** "#rrggbb" → 0xRRGGBB */
    fun hexa(h: String): Int = h.trim().removePrefix("#").toInt(16)

    fun publiques() = especes.filter { !it.secrete }

    fun simple(t: String) =
        Normalizer.normalize(t.lowercase().trim(), Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"), "")

    /** Retrouve une espèce par son nom (sans majuscules ni accents), son identifiant ou son numéro. */
    fun espece(nom: String?): Espece? {
        if (nom.isNullOrBlank()) return null
        val n = simple(nom).trimStart('#')
        return especes.firstOrNull { simple(it.nom) == n || it.id == n || it.numero.toString() == n.trimStart('0') }
            ?: especes.firstOrNull { n.length >= 3 && simple(it.nom).startsWith(n) }
    }

    // ---------------------------------------------------------------- hasard « à la Python »
    /** random.choices(population, poids) : un seul tirage pondéré. */
    fun <T> choisir(liste: List<T>, poids: List<Double>, rnd: kotlin.random.Random = kotlin.random.Random): T {
        var total = 0.0
        val cumul = poids.map { total += it; total }
        val x = rnd.nextDouble() * total
        var i = cumul.indexOfFirst { it > x }
        if (i < 0) i = liste.size - 1
        return liste[i]
    }

    /** round(x, n) de Python (arrondi exact au plus proche, à égalité vers le pair). */
    fun arrondi(x: Double, n: Int): Double = BigDecimal(x).setScale(n, RoundingMode.HALF_EVEN).toDouble()

    // ---------------------------------------------------------------- apparition, note, rareté
    class Tirage(val espece: Espece, val shiny: Boolean, val variante: String)

    /** {famille: commande qui l'attire} (une commande par famille, champ « attiree_par »), comme B.familles() sur PC. */
    fun familles(): Map<String, String> {
        val out = LinkedHashMap<String, String>()
        for (e in publiques()) if (e.famille !in out) out[e.famille] = e.attireePar
        return out
    }

    /** Une apparition : l'espèce (selon sa fréquence, et la famille attirée), sa variante (selon son habitat),
     *  shiny ou pas. Sans graine (non vérifiable) ; même pondération que Tirage.poidsEspeces. */
    fun tirer(rnd: kotlin.random.Random = kotlin.random.Random, attire: String? = null): Tirage {
        val pub = publiques()
        val e = choisir(pub, fr.terminagotchi.Tirage.poidsEspeces(pub, attire).map { it.toDouble() }, rnd)
        val v = choisir(e.variantes, e.variantes.map { it.chance }, rnd)
        val shiny = rnd.nextInt(chanceShiny) == 0
        return Tirage(e, shiny, v.id)
    }

    fun variante(e: Espece, vid: String?): Variante = e.variantes.firstOrNull { it.id == vid } ?: e.variantes.first()

    /** Note sur 100 : 60 % qualité des stats, 25 % variante, 15 % puissance de l'espèce, +10 shiny. */
    fun note(e: Espece, vid: String?, qualite: Double, shiny: Boolean): Double {
        val p = poidsNote
        val n = (p["stats"] ?: 60.0) * qualite + (p["variante"] ?: 25.0) * variante(e, vid).score +
            (p["puissance"] ?: 15.0) * (e.puissance - 1) / 14 + (if (shiny) p["bonus_shiny"] ?: 10.0 else 0.0)
        return arrondi(minOf(100.0, n), 1)
    }

    /** La rareté d'un individu (et plus de l'espèce) ; Abyssor est toujours mythique. */
    fun rarete(e: Espece, vid: String?, qualite: Double, shiny: Boolean): String {
        speciales[e.id]?.let { return it }
        val n = note(e, vid, qualite, shiny)
        var nom = "commune"
        for ((seuil, palier) in paliers) if (n >= seuil) nom = palier
        return nom
    }

    /** Rareté d'une bestiole de la troupe (les anciennes captures n'en ont pas : on la recalcule). */
    fun rareteDe(ind: JSONObject): String {
        ind.optString("rarete").takeIf { it.isNotEmpty() }?.let { return it }
        val e = espece(ind.optString("espece")) ?: return "commune"
        return rarete(e, ind.optString("variante", "classique"), ind.optDouble("potentiel", 50.0) / 100, ind.optBoolean("shiny"))
    }

    /** Une bestiole : unique, avec sa marque, ses stats tirées et sa rareté. */
    fun individu(e: Espece, shiny: Boolean, zone: String, vid: String = "classique", qualite: Double? = null,
                 rnd: java.util.Random = java.util.Random()): JSONObject {
        val q = qualite ?: rnd.nextDouble()
        val iv = LinkedHashMap<String, Int>()
        for (k in e.stats.keys) iv[k] = Math.rint(31 * (q + rnd.nextGaussian() * 0.08)).toInt().coerceIn(0, 31)
        val st = JSONObject()
        for ((k, v) in e.stats) st.put(k, v + (iv[k] ?: 0) / 2)
        val b = ByteArray(5)
        SecureRandom().nextBytes(b)
        return JSONObject()
            .put("id", b.joinToString("") { "%02x".format(it) })
            .put("espece", e.nom).put("variante", vid).put("shiny", shiny)
            .put("date", System.currentTimeMillis())
            .put("marque", marques[rnd.nextInt(marques.size)]).put("humeur", humeurs[rnd.nextInt(humeurs.size)])
            .put("taille", arrondi(e.tailleCm * (0.8 + rnd.nextDouble() * 0.45), 1))
            .put("qualite", arrondi(q, 3))
            .put("potentiel", Math.rint(100.0 * iv.values.sum() / (31 * iv.size)).toInt())
            .put("stats", st)
            .put("note", note(e, vid, q, shiny))
            .put("rarete", rarete(e, vid, q, shiny))
            .put("zone", zone)
    }

    // ---------------------------------------------------------------- migration des anciennes sauvegardes
    /**
     * Sauvegardes d'avant le nouveau bestiaire : chaque ancienne espèce devient la nouvelle de même numéro,
     * et le stade « finale » devient « ancien ». extra = les modules de la sauvegarde Android. Renvoie true si
     * quelque chose a changé.
     */
    fun migrer(extra: JSONObject): Boolean {
        if (anciens.isEmpty()) return false
        var change = false
        fun nouveau(nom: String?): String? {
            if (nom == null || espece(nom) != null) return nom
            val n = anciens[nom] ?: return nom
            val e = especes.firstOrNull { it.numero == n } ?: return nom
            change = true
            return e.nom
        }
        val explo = extra.optJSONObject("explo")
        explo?.optJSONArray("captures")?.let { caps ->
            for (i in 0 until caps.length()) {
                val c = caps.optJSONObject(i) ?: continue
                c.put("espece", nouveau(c.optString("espece")))
                if (c.optString("stade") == "finale") { c.put("stade", "ancien"); change = true }
            }
        }
        explo?.optJSONObject("collection")?.let { col ->
            val neuf = JSONObject()
            for (k in col.keys().asSequence().toList()) {
                val n = nouveau(k) ?: k
                neuf.put(n, neuf.optInt(n) + col.optInt(k))
            }
            explo.put("collection", neuf)
        }
        explo?.optJSONArray("sauvages")?.let { s ->
            for (i in 0 until s.length()) s.optJSONObject(i)?.let { it.put("e", nouveau(it.optString("e"))) }
        }
        extra.optJSONObject("dressage")?.optJSONObject("en_cours")?.let { d ->
            d.put("espece", nouveau(d.optString("espece")))
            d.optJSONObject("ind")?.let { it.put("espece", nouveau(it.optString("espece"))) }
        }
        return change
    }

    // ---------------------------------------------------------------- images par stade (sprites.bin)
    private fun jeux(): JSONObject {
        jeuxSprites?.let { return it }
        synchronized(this) {
            jeuxSprites?.let { return it }
            val o = try {
                val brut = sourceSprites?.invoke()
                if (brut == null) JSONObject() else JSONObject(String(gonfler(brut), Charsets.UTF_8))
            } catch (e: Exception) { JSONObject() }
            jeuxSprites = o
            return o
        }
    }

    /** zlib.decompress */
    fun gonfler(brut: ByteArray, taille: Int = 0): ByteArray {
        val inf = Inflater()
        inf.setInput(brut)
        val out = java.io.ByteArrayOutputStream(if (taille > 0) taille else brut.size * 4)
        val buf = ByteArray(65536)
        while (!inf.finished()) {
            val n = inf.inflate(buf)
            if (n == 0 && (inf.needsInput() || inf.needsDictionary())) break
            out.write(buf, 0, n)
        }
        inf.end()
        return out.toByteArray()
    }

    /** L'image d'un stade (indices + palette) ; la forme classique si la variante n'est pas dessinée. */
    fun image(e: Espece, stade: String = "adulte", vid: String = "classique"): AnimAuto.Sprite? {
        val cle = "${e.id}/$vid/$stade"
        synchronized(decodes) { if (decodes.containsKey(cle)) return decodes[cle] }
        val s = jeux()
        val jeu = s.optJSONObject("${e.id}/$vid") ?: s.optJSONObject("${e.id}/classique")
        val img = jeu?.let {
            val st = it.getJSONObject("stades")
            val a = st.optJSONArray(stade) ?: st.optJSONArray("adulte") ?: return@let null
            val w = a.getInt(0); val h = a.getInt(1)
            val octets = gonfler(java.util.Base64.getDecoder().decode(a.getString(2)), w * h)
            val p = it.getJSONArray("palette")
            AnimAuto.Sprite(w, h, octets, IntArray(p.length()) { k -> hexa(p.getString(k)) })
        }
        synchronized(decodes) { decodes[cle] = img }
        return img
    }

    // ---------------------------------------------------------------- couleurs (shiny)
    private const val UN_TIERS = 1.0 / 3.0
    private const val UN_SIXIEME = 1.0 / 6.0
    private const val DEUX_TIERS = 2.0 / 3.0

    /** x % 1.0 de Python (toujours positif) */
    private fun mod1(x: Double): Double { val m = x % 1.0; return if (m != 0.0 && m < 0) m + 1.0 else m }

    private fun v(m1: Double, m2: Double, teinte: Double): Double {
        val h = mod1(teinte)
        if (h < UN_SIXIEME) return m1 + (m2 - m1) * h * 6.0
        if (h < 0.5) return m2
        if (h < DEUX_TIERS) return m1 + (m2 - m1) * (DEUX_TIERS - h) * 6.0
        return m1
    }

    /** Décale la teinte d'une couleur 0xRRGGBB (shiny : chaque individu a la sienne). Comme colorsys en Python. */
    fun decaler(rgb: Int, teinte: Double): Int {
        val r = ((rgb shr 16) and 0xFF) / 255.0; val g = ((rgb shr 8) and 0xFF) / 255.0; val b = (rgb and 0xFF) / 255.0
        val maxc = maxOf(r, g, b); val minc = minOf(r, g, b)
        val sumc = maxc + minc; val rangec = maxc - minc
        val l = sumc / 2.0
        var h = 0.0; var s = 0.0
        if (minc != maxc) {
            s = if (l <= 0.5) rangec / sumc else rangec / (2.0 - maxc - minc)
            val rc = (maxc - r) / rangec; val gc = (maxc - g) / rangec; val bc = (maxc - b) / rangec
            h = if (r == maxc) bc - gc else if (g == maxc) 2.0 + rc - bc else 4.0 + gc - rc
            h = mod1(h / 6.0)
        }
        h = mod1(h + teinte)
        s = minOf(1.0, s * 1.1)
        val (r2, g2, b2) = if (s == 0.0) Triple(l, l, l) else {
            val m2 = if (l <= 0.5) l * (1.0 + s) else l + s - (l * s)
            val m1 = 2.0 * l - m2
            Triple(v(m1, m2, h + UN_TIERS), v(m1, m2, h), v(m1, m2, h - UN_TIERS))
        }
        return ((r2 * 255).toInt() shl 16) or ((g2 * 255).toInt() shl 8) or (b2 * 255).toInt()
    }

    /** Palette d'un individu (décalée s'il est shiny), en ARGB. */
    fun paletteDe(img: AnimAuto.Sprite, shiny: Boolean, teinte: Double): IntArray =
        IntArray(img.palette.size) { (if (shiny) decaler(img.palette[it], teinte) else img.palette[it] and 0xFFFFFF) or 0xFF000000.toInt() }

    /** Décalage de teinte d'une vraie image (portraits, animations faites main) : filtre de couleur. */
    fun filtreTeinte(tours: Double): ColorMatrixColorFilter {
        val a = Math.toRadians(tours * 360.0)
        val c = Math.cos(a).toFloat(); val s = Math.sin(a).toFloat()
        val lr = 0.213f; val lg = 0.715f; val lb = 0.072f
        val m = floatArrayOf(
            lr + c * (1 - lr) + s * (-lr), lg + c * (-lg) + s * (-lg), lb + c * (-lb) + s * (1 - lb), 0f, 0f,
            lr + c * (-lr) + s * 0.143f, lg + c * (1 - lg) + s * 0.140f, lb + c * (-lb) + s * (-0.283f), 0f, 0f,
            lr + c * (-lr) + s * (-(1 - lr)), lg + c * (-lg) + s * lg, lb + c * (1 - lb) + s * lb, 0f, 0f,
            0f, 0f, 0f, 1f, 0f)
        return ColorMatrixColorFilter(ColorMatrix(m))
    }

    // ---------------------------------------------------------------- dessins
    /**
     * La bestiole en gros pixels, posée pieds au sol sur un cadre carré (pour ne pas être déformée).
     * Son vrai stade et sa variante ; shiny = palette décalée de « teinte ». Abyssor garde son ancien dessin.
     */
    fun bitmap(e: Espece, shiny: Boolean = false, echelle: Int = 5, stade: String = "adulte",
               vid: String = "classique", teinte: Double = 0.5): Bitmap {
        val cle = "${e.id}-$vid-$stade-$shiny-$teinte-$echelle"
        images[cle]?.let { return it }
        val img = image(e, stade, vid)
        val bmp = if (img == null) bitmapAncien(e, shiny, echelle) else {
            val pal = paletteDe(img, shiny, teinte)
            val n = maxOf(img.w, img.h)
            val ox = (n - img.w) / 2
            val oy = n - img.h
            val px = IntArray(n * n)
            for (y in 0 until img.h) for (x in 0 until img.w) {
                val k = img.octets[y * img.w + x].toInt() and 0xFF
                if (k != 0) px[(y + oy) * n + x + ox] = pal[k - 1]
            }
            val b = Bitmap.createBitmap(px, n, n, Bitmap.Config.ARGB_8888)
            Bitmap.createScaledBitmap(b, n * echelle, n * echelle, false)
        }
        if (images.size > 200) images.clear()
        images[cle] = bmp
        return bmp
    }

    /** L'ancien dessin 16×16 (Abyssor). */
    private fun bitmapAncien(e: Espece, shiny: Boolean, echelle: Int): Bitmap {
        val rows = if (shiny && e.spriteShiny.isNotEmpty()) e.spriteShiny else e.sprite
        val pal = if (shiny && e.paletteShiny.isNotEmpty()) e.paletteShiny else e.palette
        val n = 16
        val bmp = Bitmap.createBitmap(n * echelle, n * echelle, Bitmap.Config.ARGB_8888)
        if (rows.isEmpty()) return bmp
        val c = Canvas(bmp)
        val p = Paint()
        val ox = (n - rows[0].length) / 2
        val oy = (n - rows.size) / 2
        rows.forEachIndexed { y, l ->
            l.forEachIndexed { x, ch ->
                val col = pal[ch] ?: return@forEachIndexed
                p.color = col
                c.drawRect(((x + ox) * echelle).toFloat(), ((y + oy) * echelle).toFloat(),
                    ((x + ox + 1) * echelle).toFloat(), ((y + oy + 1) * echelle).toFloat(), p)
            }
        }
        return bmp
    }

    /** Le grand portrait peint (assets/portraits/<id>/<variante>_<stade>.webp), ou null. */
    fun portrait(e: Espece, vid: String = "classique", stade: String = "adulte"): Bitmap? {
        val cle = "${e.id}/$vid/$stade"
        if (portraits.containsKey(cle)) return portraits[cle]
        val ctx = ctxApp ?: return null
        fun lire(v: String, s: String) = try {
            ctx.assets.open("portraits/${e.id}/${v}_$s.webp").use { BitmapFactory.decodeStream(it) }
        } catch (x: Exception) { null }
        val b = lire(vid, stade) ?: lire("classique", stade) ?: lire("classique", "adulte")
        if (portraits.size > 40) portraits.clear()
        portraits[cle] = b
        return b
    }

    /** Couleur d'un pixel (u, v entre 0 et 1) : sert au Doom pour dessiner les bestioles en 3D. */
    fun pixel(e: Espece, u: Double, v: Double): Int {
        val img = image(e, "adulte", "classique")
        if (img == null) {
            val n = 16
            val rows = e.sprite
            if (rows.isEmpty()) return 0
            val ox = (n - rows[0].length) / 2
            val oy = (n - rows.size) / 2
            val x = (u * n).toInt() - ox
            val y = (v * n).toInt() - oy
            if (y < 0 || y >= rows.size || x < 0 || x >= rows[y].length) return 0
            return e.palette[rows[y][x]] ?: 0
        }
        val n = maxOf(img.w, img.h)
        val x = (u * n).toInt() - (n - img.w) / 2
        val y = (v * n).toInt() - (n - img.h)
        if (y < 0 || y >= img.h || x < 0 || x >= img.w) return 0
        val k = img.octets[y * img.w + x].toInt() and 0xFF
        return if (k == 0) 0 else img.palette[k - 1] or 0xFF000000.toInt()
    }

    // ---------------------------------------------------------------- textes
    fun lieu(zone: String): String {
        val base = zone.substringBefore('/')
        val prof = zone.count { it == '/' }.coerceAtMost(3)
        // v3 : le vrai nom du lieu dans la langue choisie (« Atelier des engrenages »), sinon celui du bestiaire
        return Langue.ou("carte.piece.$base", habitats[base] ?: base) + listOf("", " " + t("exp.recoin"), " " + t("exp.cachette"),
            " " + t("exp.sanctuaire"))[prof]
    }

    /** Le nom d'une rareté, d'une fréquence, dans la langue choisie (identifiants en français dans les données). */
    fun nomRarete(r: String) = Langue.ou("rarete.$r", r)
    fun nomFrequence(f: String) = Langue.ou("frequence.$f", f)

    /**
     * Balise de dessin pour le terminal de l'appli : ¤id:variante:stade*teinte+~n¤
     * (* = shiny, avec sa teinte ; + = grand portrait ; ~n = aura de rareté, palier n de Aura.ORDRE).
     * Remplacée par l'image à l'affichage.
     */
    fun balise(e: Espece, vid: String = "classique", stade: String = "adulte", shiny: Boolean = false,
               teinte: Double = 0.5, grand: Boolean = false, aura: String? = null): String =
        "¤${e.id}:$vid:$stade" + (if (shiny) "*$teinte" else "") + (if (grand) "+" else "") +
            (if (aura != null) "~${Aura.code(aura)}" else "") + "¤"

    /** Une bestiole de la troupe, avec son aura de rareté (aura = false pour la dessiner sans). */
    fun balise(ind: JSONObject, grand: Boolean = false, aura: Boolean = true): String {
        val e = espece(ind.optString("espece")) ?: return ""
        return balise(e, ind.optString("variante", "classique"), Equipe.stade(ind), ind.optBoolean("shiny"),
            ind.optDouble("teinte", 0.5), grand, if (aura) Aura.palierInd(ind) else null)
    }

    /** Nom à afficher : §arc-en-ciel§ pour les shiny, les légendaires et les mythiques. */
    fun nomAffiche(e: Espece, shiny: Boolean = false, rareteInd: String? = null): String {
        val nom = e.nom + if (shiny) " ✨" else ""
        val r = rareteInd ?: if (e.rarete == "mythique") "mythique" else null
        return if (shiny || r == "légendaire" || r == "mythique") "§$nom§" else nom
    }
}
