package fr.terminagotchi

import android.content.Context
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.zip.Inflater

/**
 * Les poses de la créature de la bulle et de l'île (comme pc/tg/poses.py) : dessinées pour les 27 bébés de départ
 * (assets/poses.bin, fabriqué par donnees/bestiaire2/outils/poses_bureau.py : marche1 à marche4, assis, dort, etire,
 * baille, sursaut, coeur, mange, salut), calculées (AnimAuto, Vie) pour les autres stades et les autres espèces.
 *
 * Format : "TGPO" | version | longueur de l'en-tête (4 octets) | en-tête JSON | blocs zlib (un par espèce, les octets
 * indexés des 12 poses bout à bout). Une espèce ne se décompresse que si elle est affichée.
 */
object Poses {
    val NOMS = listOf("marche1", "marche2", "marche3", "marche4", "assis", "dort", "etire", "baille",
        "sursaut", "coeur", "mange", "salut")
    val ETATS = listOf("marche", "assis", "dort", "etire", "baille", "sursaut", "coeur", "mange", "salut")
    /** l'animation procédurale qui remplace chaque pose quand il n'y a pas de dessin (comme poses.PROCEDURALE) */
    val PROCEDURALE = mapOf("marche" to "statique", "assis" to "statique", "dort" to "dort", "etire" to "statique",
        "baille" to "parle", "sursaut" to "victoire", "coeur" to "content", "mange" to "mange", "salut" to "salut")

    /** Une image ARGB et son ancre (ax, ay) : le milieu du corps et le bas des pieds. */
    class Cadre(val w: Int, val h: Int, val argb: IntArray, val ax: Int, val ay: Int, val cle: String)

    /** Les images de chaque état ; ref : la hauteur de la pose assise ; lisse : dessin fin (sinon gros pixels). */
    class Album(val etats: Map<String, List<Cadre>>, val ref: Int, val lisse: Boolean, val dessine: Boolean) {
        fun images(etat: String): List<Cadre> = etats[etat]?.takeIf { it.isNotEmpty() } ?: etats.getValue("assis")
        fun image(etat: String, t: Int): Cadre { val l = images(etat); return l[Math.floorMod(t, l.size)] }
    }

    private var tete: JSONObject? = null
    private var blocs: ByteArray = ByteArray(0)
    private val indexees = HashMap<String, Pair<Map<String, IntArray>, IntArray>>()

    /** Lit un poses.bin (les octets du fichier) ; faux s'il est abîmé. */
    fun lire(octets: ByteArray): Boolean {
        if (octets.size < 9 || String(octets, 0, 4, Charsets.US_ASCII) != "TGPO" || octets[4].toInt() != 1) return false
        val n = ((octets[5].toInt() and 255) shl 24) or ((octets[6].toInt() and 255) shl 16) or
            ((octets[7].toInt() and 255) shl 8) or (octets[8].toInt() and 255)
        return try {
            tete = JSONObject(String(octets, 9, n, Charsets.UTF_8))
            blocs = octets.copyOfRange(9 + n, octets.size)
            synchronized(indexees) { indexees.clear() }
            true
        } catch (e: Exception) { false }
    }

    fun charger(ctx: Context) {
        if (tete != null) return
        try { ctx.assets.open("poses.bin").use { lire(it.readBytes()) } } catch (e: Exception) { }
    }

    fun especes(): List<String> = tete?.optJSONObject("especes")?.keys()?.asSequence()?.sorted()?.toList() ?: emptyList()

    fun aDesPoses(espece: String?): Boolean = espece != null && tete?.optJSONObject("especes")?.has(espece) == true

    private fun gonfler(b: ByteArray, off: Int, len: Int): ByteArray {
        val inf = Inflater()
        inf.setInput(b, off, len)
        val out = ByteArrayOutputStream(len * 4)
        val buf = ByteArray(65536)
        while (!inf.finished()) {
            val k = inf.inflate(buf)
            if (k == 0 && (inf.needsInput() || inf.needsDictionary())) break
            out.write(buf, 0, k)
        }
        inf.end()
        return out.toByteArray()
    }

    /** Les cadres (w, h, ax, ay, puis les octets indexés en entiers) et la palette (0xRRGGBB) d'une espèce dessinée. */
    fun indexees(espece: String): Pair<Map<String, IntArray>, IntArray>? {
        synchronized(indexees) { indexees[espece]?.let { return it } }
        val e = tete?.optJSONObject("especes")?.optJSONObject(espece) ?: return null
        val brut = gonfler(blocs, e.getInt("o"), e.getInt("n"))
        val cad = e.getJSONArray("cadres")
        val pal = e.getJSONArray("pal")
        val palette = IntArray(pal.length()) { java.lang.Long.parseLong(pal.getString(it).substring(1), 16).toInt() }
        val out = LinkedHashMap<String, IntArray>()
        var k = 0
        for (i in NOMS.indices) {
            val c = cad.getJSONArray(i)
            val w = c.getInt(0); val h = c.getInt(1)
            val v = IntArray(4 + w * h)
            v[0] = w; v[1] = h; v[2] = c.getInt(2); v[3] = c.getInt(3)
            for (p in 0 until w * h) v[4 + p] = brut[k + p].toInt() and 255
            k += w * h
            out[NOMS[i]] = v
        }
        val r = out to palette
        synchronized(indexees) { indexees[espece] = r }
        return r
    }

    /** Les 12 poses dessinées d'un bébé de départ, ou null. teinte : décalage shiny (ou null). */
    fun dessine(espece: String, teinte: Double? = null): Album? {
        val (idx, pal0) = indexees(espece) ?: return null
        val pal = IntArray(pal0.size) { val c = if (teinte != null) Bestiaire.decaler(pal0[it], teinte) else pal0[it]; c or 0xFF000000.toInt() }
        val cad = idx.mapValues { (nom, v) ->
            val w = v[0]; val h = v[1]
            val argb = IntArray(w * h) { p -> val o = v[4 + p]; if (o == 0 || o > pal.size) 0 else pal[o - 1] }
            Cadre(w, h, argb, v[2], v[3], "$espece/$nom/$teinte")
        }
        val etats = LinkedHashMap<String, List<Cadre>>()
        etats["marche"] = (1..4).map { cad.getValue("marche$it") }
        for (e in ETATS.drop(1)) etats[e] = listOf(cad.getValue(e))
        return Album(etats, cad.getValue("assis").h, lisse = true, dessine = true)
    }

    /** Une animation indexée (AnimAuto) en cadres ARGB, l'ancre au milieu et en bas de la silhouette. */
    fun cadres(a: AnimAuto.Anim, cle: String, pas: Int = 1): List<Cadre> {
        val W = a.largeur; val H = a.hauteur
        var bas = 0
        for (y in H - 1 downTo 0) if ((0 until W).any { x -> a.images[0][y * W + x].toInt() != 0 }) { bas = y + 1; break }
        val pal = IntArray(a.palette.size) { a.palette[it] or 0xFF000000.toInt() }
        return a.images.filterIndexed { i, _ -> i % pas == 0 }.mapIndexed { k, f ->
            Cadre(W, H, IntArray(W * H) { p -> val o = f[p].toInt() and 255; if (o == 0 || o > pal.size) 0 else pal[o - 1] },
                W / 2, if (bas > 0) bas else H, "$cle/$k")
        }
    }

    /** L'animation procédurale du compagnon (tous stades, œuf et créature d'avant le bestiaire compris). */
    fun procedural(jeu: Jeu): Album {
        val vus = HashMap<String, List<Cadre>>()
        val etats = LinkedHashMap<String, List<Cadre>>()
        for (e in ETATS) {
            val nom = PROCEDURALE.getValue(e)
            etats[e] = vus.getOrPut(nom) {
                val a = Sprites.animation(jeu, nom)
                cadres(a, "jeu/${jeu.stade}/$nom", if (nom == "statique" && a.images.size > 16) 2 else 1)
            }
        }
        val ref = etats.getValue("assis")[0].let { c -> c.ay - (0 until c.h).first { y -> (0 until c.w).any { x -> c.argb[y * c.w + x] != 0 } } }
        return Album(etats, maxOf(1, ref), lisse = false, dessine = false)
    }

    /** L'album de la créature : ses poses dessinées si c'est un bébé de départ, sinon l'animation du jeu. */
    fun album(jeu: Jeu): Album {
        val esp = jeu.extra.optString("espece_compagnon").takeIf { it.isNotEmpty() }
        if (jeu.stade == 1 && esp != null) dessine(esp, if (jeu.shiny) 0.5 else null)?.let { return it }
        return procedural(jeu)
    }

    /** L'album d'une bestiole de l'équipe : dessinée au stade bébé si possible, sinon l'animation de son stade. */
    fun albumEspece(espece: Bestiaire.Espece, stade: String, shiny: Boolean): Album? {
        if (stade == "bebe") dessine(espece.id, if (shiny) 0.5 else null)?.let { return it }
        val img = Bestiaire.image(espece, if (stade == "finale") "ancien" else stade) ?: return null
        val etats = LinkedHashMap<String, List<Cadre>>()
        val vus = HashMap<String, List<Cadre>>()
        for (e in ETATS) {
            val nom = PROCEDURALE.getValue(e)
            etats[e] = vus.getOrPut(nom) {
                val a = AnimAuto.images(img, nom)
                cadres(Sprites.recadrer(a), "${espece.id}/$stade/$nom", if (nom == "statique" && a.images.size > 16) 2 else 1)
            }
        }
        return Album(etats, img.h, lisse = false, dessine = false)
    }
}
