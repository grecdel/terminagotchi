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

/** Le bestiaire commun (150 espèces), lu depuis assets/bestiaire.json (le même que le PC et le site). */
object Bestiaire {
    class Espece(
        val id: String, val numero: Int, val nom: String, val famille: String, val icone: String,
        val rarete: String, val stat: String, val description: String, val comportement: String,
        val capacite: String, val zone: String, val attireePar: String, val frequence: String,
        val tailleCm: Double, val poidsKo: Int, val stats: LinkedHashMap<String, Int>,
        val sprite: List<String>, val spriteShiny: List<String>,
        val palette: Map<Char, Int>, val paletteShiny: Map<Char, Int>,
    )

    val HABITATS = mapOf(
        "archives" to "les archives", "marais" to "le marais", "usine" to "l'usine", "grenier" to "le grenier",
        "forteresse" to "la forteresse", "atelier" to "l'atelier", "forge" to "la forge", "foret" to "la forêt",
        "montagne" to "la montagne", "bibliotheque" to "la bibliothèque", "coffre" to "le coffre-fort",
        "laboratoire" to "le laboratoire", "arcade" to "la salle d'arcade", "faille" to "la faille", "grotte" to "la grotte",
    )
    val XP = mapOf("commune" to 15, "peu commune" to 25, "rare" to 40, "légendaire" to 100)
    val COULEUR_RARETE = mapOf("commune" to 0xFFB0B0C0.toInt(), "peu commune" to 0xFF5FD787.toInt(),
        "rare" to 0xFF5FAFFF.toInt(), "légendaire" to 0xFFFFAF00.toInt())

    var especes: List<Espece> = emptyList()
        private set
    var marques: List<String> = emptyList()
        private set
    var humeurs: List<String> = emptyList()
        private set
    private var raretes: List<String> = emptyList()
    private var poids: Map<String, Int> = emptyMap()
    private var chanceShiny = 100
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
                Espece(
                    e.getString("id"), e.getInt("numero"), e.getString("nom"), e.getString("famille"),
                    e.getString("icone"), e.getString("rarete"), e.getString("stat"), e.getString("description"),
                    e.getString("comportement"), e.getString("capacite"), e.getString("zone"),
                    e.getString("attiree_par"), e.getString("frequence"), e.getDouble("taille_cm"), e.getInt("poids_ko"),
                    LinkedHashMap(st.keys().asSequence().associateWith { st.getInt(it) }),
                    lignes("sprite"), lignes("sprite_shiny"), pal("palette"), pal("palette_shiny"),
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
    }

    fun tirer(): Pair<Espece, Boolean> {
        val total = poids.values.sum().coerceAtLeast(1)
        var t = Random.nextInt(total)
        var rarete = raretes.first()
        for (r in raretes) {
            t -= poids[r] ?: 0
            if (t < 0) { rarete = r; break }
        }
        val e = especes.filter { it.rarete == rarete }.random()
        return e to (Random.nextInt(chanceShiny) == 0)
    }

    /** Une bestiole capturée : un individu unique, avec sa marque et son potentiel. */
    fun individu(e: Espece, shiny: Boolean, zone: String): JSONObject {
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
            .put("stats", st).put("zone", zone)
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
