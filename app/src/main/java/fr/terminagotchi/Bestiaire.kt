package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import org.json.JSONObject
import java.security.SecureRandom
import java.text.Normalizer
import kotlin.random.Random

/**
 * Le bestiaire commun (150 espèces en 10 familles), lu depuis assets/bestiaire.json (le même que le PC et le site).
 * Chaque espèce est dessinée à chaque stade (enfant, ado, adulte, finale) et parfois dans des variantes d'habitat.
 */
object Bestiaire {
    class Espece(
        val id: String, val numero: Int, val nom: String, val famille: String, val icone: String,
        val rarete: String, val stat: String, val description: String, val comportement: String,
        val capacite: String, val zone: String, val attireePar: String, val frequence: String,
        val tailleCm: Double, val poidsKo: Int, val stats: LinkedHashMap<String, Int>,
        val sprite: List<String>, val spriteShiny: List<String>,
        val palette: Map<Char, Int>, val paletteShiny: Map<Char, Int>,
        val secrete: Boolean = false,
        val epreuves: List<String> = emptyList(),
        /** id de variante → chance d'apparition (%) ; « classique » toujours présente. */
        val variantes: LinkedHashMap<String, Double> = linkedMapOf("classique" to 100.0),
        /** {variante: {stade: {"l": lignes, "p": palette}}} : les dessins détaillés (32 px). */
        val dessins: JSONObject? = null,
    )

    /** Lieux de l'ancien bestiaire (vieilles sauvegardes) + ceux de bestiaire.json (« lieux »). */
    val HABITATS = mutableMapOf(
        "archives" to "les archives", "marais" to "le marais", "usine" to "l'usine", "grenier" to "le grenier",
        "forteresse" to "la forteresse", "atelier" to "l'atelier", "forge" to "la forge", "foret" to "la forêt",
        "montagne" to "la montagne", "bibliotheque" to "la bibliothèque", "coffre" to "le coffre-fort",
        "laboratoire" to "le laboratoire", "arcade" to "la salle d'arcade", "faille" to "la faille", "grotte" to "la grotte",
    )
    val XP = mapOf("commune" to 15, "peu commune" to 25, "rare" to 40, "légendaire" to 100)
    val COULEUR_RARETE = mapOf("commune" to 0xFFB0B0C0.toInt(), "peu commune" to 0xFF5FD787.toInt(),
        "rare" to 0xFF5FAFFF.toInt(), "épique" to 0xFFC77DFF.toInt(), "légendaire" to 0xFFFFAF00.toInt(),
        "mythique" to 0xFFFF5F87.toInt())

    var especes: List<Espece> = emptyList()
        private set
    var marques: List<String> = emptyList()
        private set
    var humeurs: List<String> = emptyList()
        private set
    private var raretes: List<String> = emptyList()
    private var poids: Map<String, Int> = emptyMap()
    private var chanceShiny = 100
    private var version = 1
    /** Noms de l'ancien bestiaire → nouveaux noms (même numéro). */
    private var anciens: Map<String, String> = emptyMap()
    /** Règles de la rareté d'un individu (« rarete_individu » de bestiaire.json). */
    private var regleRang: JSONObject = JSONObject()
    private val puissance = HashMap<String, Int>()
    private val images = HashMap<String, Bitmap>()

    fun charger(ctx: Context) {
        if (especes.isNotEmpty()) return
        synchronized(this) {
            if (especes.isNotEmpty()) return
            val o = JSONObject(ctx.assets.open("bestiaire.json").bufferedReader().use { it.readText() })
            val ra = o.getJSONArray("raretes")
            raretes = (0 until ra.length()).map { ra.getString(it) }
            val po = o.getJSONObject("poids")
            poids = raretes.associateWith { po.optInt(it) }
            chanceShiny = o.optInt("chance_shiny", 100)
            version = o.optInt("version", 1)
            o.optJSONObject("lieux")?.let { l -> l.keys().forEach { HABITATS[it] = l.getString(it) } }
            regleRang = o.optJSONObject("rarete_individu") ?: JSONObject()
            anciens = o.optJSONObject("anciens")?.let { a -> a.keys().asSequence().associateWith { a.getString(it) } } ?: emptyMap()
            val ma = o.getJSONArray("marques")
            marques = (0 until ma.length()).map { ma.getString(it) }
            val hu = o.getJSONArray("humeurs")
            humeurs = (0 until hu.length()).map { hu.getString(it) }
            val es = o.getJSONArray("especes")
            especes = (0 until es.length()).map { i ->
                val e = es.getJSONObject(i)
                fun lignes(k: String) = e.getJSONArray(k).let { a -> (0 until a.length()).map { a.getString(it) } }
                fun pal(k: String): Map<Char, Int> {
                    val p = e.getJSONObject(k)
                    return p.keys().asSequence().associate { it[0] to Color.parseColor(p.getString(it)) }
                }
                val st = e.getJSONObject("stats")
                puissance[e.getString("id")] = e.optInt("puissance", 1)
                Espece(
                    e.getString("id"), e.getInt("numero"), e.getString("nom"), e.getString("famille"),
                    e.getString("icone"), e.getString("rarete"), e.getString("stat"), e.getString("description"),
                    e.getString("comportement"), e.getString("capacite"), e.getString("zone"),
                    e.getString("attiree_par"), e.getString("frequence"), e.getDouble("taille_cm"), e.getInt("poids_ko"),
                    LinkedHashMap(st.keys().asSequence().associateWith { st.getInt(it) }),
                    lignes("sprite"), lignes("sprite_shiny"), pal("palette"), pal("palette_shiny"),
                    e.optBoolean("secrete"),
                    e.optJSONArray("epreuves")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: listOf(e.getString("famille")),
                    e.optJSONArray("variantes")?.let { a ->
                        LinkedHashMap((0 until a.length()).associate { a.getJSONObject(it).getString("id") to a.getJSONObject(it).optDouble("chance", 1.0) })
                    }?.takeIf { it.isNotEmpty() } ?: linkedMapOf("classique" to 100.0),
                    e.optJSONObject("dessins"),
                )
            }
        }
    }

    private fun simple(t: String) =
        Normalizer.normalize(t.lowercase().trim(), Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"), "")

    fun espece(nom: String?): Espece? {
        if (nom.isNullOrBlank()) return null
        val n = simple(nom).trimStart('#')
        return especes.firstOrNull { simple(it.nom) == n || it.id == n || it.numero.toString() == n.trimStart('0') }
            ?: especes.firstOrNull { n.length >= 3 && simple(it.nom).startsWith(n) }
            ?: anciens.entries.firstOrNull { simple(it.key) == n }?.let { a -> especes.firstOrNull { it.nom == a.value } }
    }

    /**
     * Vieilles sauvegardes : les bestioles de l'ancien bestiaire prennent le nom de leur remplaçante (même numéro).
     * Le monstre sauvage en cours est oublié (il vivait dans un ancien lieu).
     */
    fun migrer(jeu: Jeu) {
        val ex = jeu.module("explo")
        if (anciens.isEmpty() || ex.optInt("bestiaire_v", 1) >= version) return
        val caps = ex.optJSONArray("captures")
        if (caps != null) for (i in 0 until caps.length()) {
            val c = caps.getJSONObject(i)
            anciens[c.optString("espece")]?.let { c.put("espece", it) }
        }
        ex.optJSONObject("collection")?.let { col ->
            val neuve = JSONObject()
            for (k in col.keys().asSequence().toList()) {
                val n = anciens[k] ?: k
                neuve.put(n, neuve.optInt(n) + col.optInt(k))
            }
            ex.put("collection", neuve)
        }
        ex.put("bestiaire_v", version)
        val dr = jeu.module("dressage")
        dr.remove("en_cours")
        dr.put("familles", org.json.JSONArray())
    }

    /** La forme d'un individu (classique, volcan, lave…), tirée selon les chances des variantes dessinées. */
    fun tirerVariante(e: Espece): String {
        var t = Random.nextDouble(e.variantes.values.sum().coerceAtLeast(0.001))
        for ((id, c) in e.variantes) { t -= c; if (t < 0) return id }
        return "classique"
    }

    fun tirer(): Pair<Espece, Boolean> {
        val total = poids.values.sum().coerceAtLeast(1)
        var t = Random.nextInt(total)
        var rarete = raretes.first()
        for (r in raretes) {
            t -= poids[r] ?: 0
            if (t < 0) { rarete = r; break }
        }
        val e = especes.filter { it.rarete == rarete && !it.secrete }.random()
        return e to (Random.nextInt(chanceShiny) == 0)
    }

    /** Une bestiole capturée : un individu unique, avec sa marque et son potentiel. */
    fun individu(e: Espece, shiny: Boolean, zone: String, variante: String? = null): JSONObject {
        val b = ByteArray(5)
        SecureRandom().nextBytes(b)
        val iv = e.stats.keys.associateWith { Random.nextInt(32) }
        val st = JSONObject()
        for ((k, v) in e.stats) st.put(k, v + (iv[k] ?: 0) / 4)
        return JSONObject()
            .put("id", b.joinToString("") { "%02x".format(it) })
            .put("espece", e.nom).put("shiny", shiny).put("date", System.currentTimeMillis())
            .put("marque", marques.random()).put("humeur", humeurs.random())
            .put("taille", Math.round(e.tailleCm * Random.nextDouble(0.8, 1.25) * 10) / 10.0)
            .put("potentiel", Math.round(100.0 * iv.values.sum() / (31 * iv.size)).toInt())
            .put("stats", st).put("zone", zone).put("variante", variante ?: tirerVariante(e))
    }

    /** Dessin de la bestiole sur un cadre de 16×16 pixels. */
    fun bitmap(e: Espece, shiny: Boolean = false, echelle: Int = 5): Bitmap {
        val cle = "${e.id}-$shiny-$echelle"
        images[cle]?.let { return it }
        val rows = if (shiny) e.spriteShiny else e.sprite
        val pal = if (shiny) e.paletteShiny else e.palette
        val n = 16
        val bmp = Bitmap.createBitmap(n * echelle, n * echelle, Bitmap.Config.ARGB_8888)
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
        images[cle] = bmp
        return bmp
    }

    /**
     * Dessin détaillé (32 px) d'une bestiole à un stade et dans une forme donnés ; teinte = décalage shiny
     * (0 = couleurs normales). Renvoie null pour les espèces sans dessins détaillés.
     */
    fun dessin(e: Espece, variante: String = "classique", stade: String = "adulte", teinte: Double = 0.0, echelle: Int = 4): Bitmap? {
        val ds = e.dessins ?: return null
        val v = ds.optJSONObject(variante) ?: ds.optJSONObject("classique") ?: return null
        val x = v.optJSONObject(stade) ?: v.optJSONObject("adulte") ?: return null
        val cle = "${e.id}-$variante-$stade-$teinte-$echelle"
        images[cle]?.let { return it }
        val l = x.getJSONArray("l")
        val p = x.getJSONObject("p")
        val pal = HashMap<Char, Int>()
        for (k in p.keys()) {
            var c = Color.parseColor(p.getString(k))
            if (teinte != 0.0) {
                val hsv = FloatArray(3)
                Color.colorToHSV(c, hsv)
                hsv[0] = ((hsv[0] + teinte * 360) % 360).toFloat()
                c = Color.HSVToColor(hsv)
            }
            pal[k[0]] = c
        }
        val n = 32
        val bmp = Bitmap.createBitmap(n * echelle, n * echelle, Bitmap.Config.ARGB_8888)
        val cv = Canvas(bmp)
        val paint = Paint()
        val h = l.length()
        val w = (0 until h).maxOfOrNull { l.getString(it).length } ?: 0
        val ox = (n - w) / 2
        val oy = n - h                                  // posé en bas du cadre, comme sur le sol
        for (y in 0 until h) {
            val ligne = l.getString(y)
            for (xx in ligne.indices) {
                val col = pal[ligne[xx]] ?: continue
                paint.color = col
                cv.drawRect(((xx + ox) * echelle).toFloat(), ((y + oy) * echelle).toFloat(),
                    ((xx + ox + 1) * echelle).toFloat(), ((y + oy + 1) * echelle).toFloat(), paint)
            }
        }
        images[cle] = bmp
        return bmp
    }

    /** Le dessin d'un individu de la troupe : son stade, sa forme, sa teinte shiny et l'aura de sa rareté. */
    fun dessinIndividu(ind: JSONObject, echelle: Int = 4): Bitmap? {
        val e = espece(ind.optString("espece")) ?: return null
        val teinte = if (ind.optBoolean("shiny")) ind.optDouble("teinte", 0.5) else 0.0
        return dessinRang(e, ind.optString("variante", "classique").ifEmpty { "classique" },
            ind.optString("stade", "enfant"), teinte, rangIndividu(ind), echelle)
    }

    /** Dessin détaillé entouré de l'aura de sa rareté (rare et plus). */
    fun dessinRang(e: Espece, variante: String, stade: String, teinte: Double, rang: String, echelle: Int = 4): Bitmap? {
        val b = dessin(e, variante, stade, teinte, echelle) ?: return null
        if (rang !in setOf("rare", "épique", "légendaire", "mythique")) return b
        val cle = "${e.id}-$variante-$stade-$teinte-$echelle-$rang"
        images[cle]?.let { return it }
        return aura(b, COULEUR_RARETE[rang] ?: Color.WHITE, echelle).also { images[cle] = it }
    }

    /** Contour lumineux d'un pixel autour de la silhouette. */
    private fun aura(b: Bitmap, couleur: Int, echelle: Int): Bitmap {
        val out = b.copy(Bitmap.Config.ARGB_8888, true)
        val n = b.width / echelle
        val plein = Array(n) { y -> BooleanArray(n) { x -> Color.alpha(b.getPixel(x * echelle, y * echelle)) > 0 } }
        val cv = Canvas(out)
        val p = Paint().apply { color = couleur }
        for (y in 0 until n) for (x in 0 until n) {
            if (plein[y][x]) continue
            val bord = (x > 0 && plein[y][x - 1]) || (x < n - 1 && plein[y][x + 1]) ||
                (y > 0 && plein[y - 1][x]) || (y < n - 1 && plein[y + 1][x])
            if (bord) cv.drawRect((x * echelle).toFloat(), (y * echelle).toFloat(),
                ((x + 1) * echelle).toFloat(), ((y + 1) * echelle).toFloat(), p)
        }
        return out
    }

    /** Note sur 100 d'un individu : 60 % stats (en centile), 25 % rareté de sa forme, 15 % puissance, +10 shiny. */
    fun noteIndividu(ind: JSONObject): Int {
        val e = espece(ind.optString("espece")) ?: return 0
        val po = regleRang.optJSONObject("poids") ?: JSONObject("""{"stats":60,"variante":25,"puissance":15,"bonus_shiny":10}""")
        val pot = ind.optInt("potentiel", 50).coerceIn(0, 100)
        val stats = regleRang.optJSONArray("centiles")?.optDouble(pot) ?: (pot / 100.0)
        val max = e.variantes.values.maxOrNull() ?: 100.0
        val ch = e.variantes[ind.optString("variante", "classique")] ?: max
        var note = po.optDouble("stats") * stats + po.optDouble("variante") * (1 - ch / max) +
            po.optDouble("puissance") * ((puissance[e.id] ?: 1) - 1) / 14.0
        if (ind.optBoolean("shiny")) note += po.optDouble("bonus_shiny")
        return Math.round(minOf(100.0, note)).toInt()
    }

    /** Rareté propre à un individu : commune, peu commune, rare, épique, légendaire (ou mythique). */
    fun rangIndividu(ind: JSONObject): String {
        val e = espece(ind.optString("espece")) ?: return "commune"
        regleRang.optJSONObject("speciales")?.optString(e.id)?.takeIf { it.isNotEmpty() }?.let { return it }
        val note = noteIndividu(ind)
        var rang = "commune"
        val pa = regleRang.optJSONArray("paliers") ?: return rang
        for (i in 0 until pa.length()) {
            val x = pa.getJSONArray(i)
            if (note >= x.getDouble(0)) rang = x.getString(1)
        }
        return rang
    }

    fun nomVariante(v: String?) = if (v.isNullOrEmpty() || v == "classique") "" else v.replace('_', ' ')

    /** Couleur d'un pixel (u, v entre 0 et 1) : sert au Doom pour dessiner les bestioles en 3D. */
    fun pixel(e: Espece, u: Double, v: Double): Int {
        val n = 16
        val rows = e.sprite
        val ox = (n - rows[0].length) / 2
        val oy = (n - rows.size) / 2
        val x = (u * n).toInt() - ox
        val y = (v * n).toInt() - oy
        if (y < 0 || y >= rows.size || x < 0 || x >= rows[y].length) return 0
        return e.palette[rows[y][x]] ?: 0
    }

    fun lieu(zone: String): String {
        val base = zone.substringBefore('/')
        val prof = zone.count { it == '/' }.coerceAtMost(3)
        return (HABITATS[base] ?: base) + listOf("", " (un recoin)", " (une cachette)", " (le sanctuaire)")[prof]
    }
}
