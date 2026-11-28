/*
 * Test JVM (hors téléphone) de la vie dans la créature (Vie.kt) et du décor des auras (Aura.kt), portage de
 * pc/outils/test_vie.py :
 *   1. mêmes images qu'en Python : les vecteurs de donnees/vie/vecteurs.json (yeux trouvés, 64 images de vie,
 *      animations « statique » et « content » d'AnimAuto, particules / étincelles / reflet, éclat selon le soin) ;
 *   2. tout le bestiaire (assets) : aucune image de vie vide, tronquée ou hors palette.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Vie.kt -d vie.jar
 *   java -cp <imitations>:<appli.jar>:vie.jar:kotlin-stdlib.jar VieKt app/src/main/assets [donnees/vie/vecteurs.json]
 */
import fr.terminagotchi.AnimAuto
import fr.terminagotchi.Aura
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Equipe
import fr.terminagotchi.Vie
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

var okV = 0
var koV = 0

fun verifV(c: Boolean, m: String) {
    if (c) okV++ else koV++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun fnv(b: ByteArray): Long {
    var h = 0x811C9DC5L
    for (x in b) h = ((h xor (x.toLong() and 0xFF)) * 0x01000193L) and 0xFFFFFFFFL
    return h
}

fun empreinte(pts: List<Aura.Point>): Long =
    fnv(pts.joinToString("") { "${it.x2},${it.y2},${it.couleur},${it.alpha},${if (it.devant) 1 else 0};" }.toByteArray())

val PALIERS_V = listOf("peu commune", "rare", "épique", "légendaire", "mythique", "shiny")
val PHASES_V = listOf(0, 3, 7, 13, 21, 30)

fun longs(a: JSONArray) = (0 until a.length()).map { a.getLong(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val fv = File(args.getOrNull(1) ?: "donnees/vie/vecteurs.json")
    val v = JSONObject(fv.readText())

    println("1. Les mêmes images qu'en Python (donnees/vie/vecteurs.json)")
    val sprites = v.getJSONArray("sprites")
    var avecYeux = 0
    for (i in 0 until sprites.length()) {
        val sp = sprites.getJSONObject(i)
        val w = sp.getInt("w"); val h = sp.getInt("h")
        val o = Bestiaire.gonfler(java.util.Base64.getDecoder().decode(sp.getString("o")), w * h)
        val pj = sp.getJSONArray("pal")
        val pal = IntArray(pj.length()) { pj.getInt(it) }
        val att = sp.getJSONObject("attendu")
        val oi = IntArray(w * h) { o[it].toInt() and 0xFF }
        val a = Vie.analyser(w, h, oi, pal)
        val an = att.opt("analyse")
        var memes = true
        if (an == null || an == JSONObject.NULL) {
            memes = a == null
        } else {
            val aj = an as JSONObject
            if (a == null) memes = false else {
                val yj = aj.getJSONArray("yeux")
                val yeux = (0 until yj.length()).map { k ->
                    val l = yj.getJSONArray(k); (0 until l.length()).map { q -> l.getJSONArray(q).let { listOf(it.getInt(0), it.getInt(1)) } }
                }
                memes = yeux == a.yeux.map { e -> e.px.map { listOf(it[0], it[1]) } } && aj.getInt("fins") == a.finsIdx.size
                val sj = aj.opt("souffle")
                memes = memes && (if (sj == null || sj == JSONObject.NULL) a.souffle == null
                    else a.souffle?.toList() == (0 until 3).map { (sj as JSONArray).getInt(it) })
                if (yeux.isNotEmpty()) avecYeux++
            }
        }
        val vieAtt = longs(att.getJSONArray("vie"))
        val vieK = if (a == null) emptyList() else (0 until Vie.CYCLE).map { fnv(Vie.image(a, it)) }
        val sp8 = AnimAuto.Sprite(w, h, o, pal)
        fun anim(nom: String): List<Long> {
            val x = AnimAuto.images(sp8, nom)
            val tout = java.io.ByteArrayOutputStream()
            x.images.forEach { tout.write(it) }
            return listOf(x.largeur.toLong(), x.hauteur.toLong(), x.images.size.toLong(), fnv(tout.toByteArray()))
        }
        val plein = BooleanArray(w * h) { oi[it] != 0 }
        val decorOk = PALIERS_V.all { nom ->
            val attendu = longs(att.getJSONObject("decor").getJSONArray(nom))
            val calc = PHASES_V.flatMap { ph -> (0..3).map { ec -> empreinte(Aura.decor(w, h, plein, nom, ph, ec)) } }
            attendu == calc
        }
        val refletOk = PALIERS_V.all { nom ->
            val r = att.getJSONObject("reflet").getJSONArray(nom)
            PHASES_V.withIndex().all { (k, ph) ->
                val x = Aura.reflet(nom, ph, w + 6, h + 6)
                if (r.isNull(k)) x == null else x == r.getInt(k)
            }
        }
        val f4 = if (a == null) emptyList() else (0 until Vie.CYCLE step 3).map { fnv(Vie.imageFine(a, it, 4)) }
        val f3 = if (a == null) emptyList() else (0 until 20 step 2).map { fnv(Vie.imageFine(a, it, 3)) }
        val finOk = f4 == longs(att.getJSONArray("fine4")) && f3 == longs(att.getJSONArray("fine3"))
        val st = anim("statique") == longs(att.getJSONArray("statique"))
        val co = anim("content") == longs(att.getJSONArray("content"))
        verifV(memes && vieK == vieAtt && finOk && st && co && decorOk && refletOk,
            "${sp.getString("nom")} : yeux ${if (memes) "=" else "≠"}, vie ${if (vieK == vieAtt) "=" else "≠"}, " +
                "pixel fin ×4 et ×3 ${if (finOk) "=" else "≠"}, " +
                "statique ${if (st) "=" else "≠"}, content ${if (co) "=" else "≠"}, décor ${if (decorOk) "=" else "≠"}, " +
                "reflet ${if (refletOk) "=" else "≠"}")
    }
    verifV(avecYeux >= 8, "des yeux trouvés dans $avecYeux images des vecteurs")
    val soin = v.getJSONArray("soin")
    verifV((0 until soin.length()).all { val x = soin.getJSONArray(it); Aura.niveauSoin(x.getInt(0), x.getInt(1)) == x.getInt(2) },
        "l'éclat selon le soin : mêmes paliers qu'en Python")

    println("2. Tout le bestiaire (assets) : jamais d'image vide ou cassée")
    Bestiaire.chargerDonnees(File(assets, "bestiaire.json").readText()) { File(assets, "sprites.bin").readBytes() }
    var n = 0; var vivants = 0
    val casses = ArrayList<String>()
    val sautsFins = ArrayList<String>()
    val t0 = System.currentTimeMillis()
    for (e in Bestiaire.especes) for (va in e.variantes) for (st in Equipe.STADES) {
        val img = Bestiaire.image(e, st, va.id) ?: continue
        n++
        val oi = IntArray(img.w * img.h) { img.octets[it].toInt() and 0xFF }
        val a = Vie.analyser(img.w, img.h, oi, img.palette) ?: continue
        vivants++
        for (F in intArrayOf(3, 4)) {
            var avant = Vie.decalages(a, 0, F)
            for (t in 1..16) {
                val apres = Vie.decalages(a, t, F)
                if (avant.first.indices.any { Math.abs(avant.first[it] - apres.first[it]) > 1 } ||
                    avant.second.indices.any { Math.abs(avant.second[it] - apres.second[it]) > 1 }) {
                    sautsFins.add("${e.id}/${va.id}/$st ×$F @$t"); break
                }
                avant = apres
            }
        }
        val n0 = oi.count { it != 0 }
        for (t in 0 until Vie.CYCLE) {
            val im = Vie.image(a, t)
            val k = im.count { it.toInt() != 0 }
            val mx = im.maxOf { it.toInt() and 0xFF }
            if (im.size != Vie.largeur(a) * Vie.hauteur(a) || k == 0 || k * 100 < n0 * 88 || mx > img.palette.size) {
                casses.add("${e.id}/${va.id}/$st@$t"); break
            }
        }
    }
    verifV(n > 3000, "$n images passées en revue (${(System.currentTimeMillis() - t0) / 1000} s)")
    verifV(sautsFins.isEmpty(), "à chaque image, aucune ligne ni pixel d'appendice ne bouge de plus d'UN pixel de l'image finale" +
        if (sautsFins.isEmpty()) "" else " : ${sautsFins.take(5)}")
    verifV(casses.isEmpty(), "aucune image de vie vide, tronquée ou hors palette" + if (casses.isEmpty()) "" else " : ${casses.take(5)}")
    verifV(vivants * 100 >= n * 90, "la vie anime $vivants images sur $n")
    val e = Bestiaire.espece("ectoplouf")!!
    val st = AnimAuto.images(Bestiaire.image(e, "bebe")!!, "statique")
    verifV(st.images.size == Vie.CYCLE && st.images.map { it.toList() }.toSet().size >= 3, "au pixel du sprite : 64 images, les yeux clignent")

    // Android : AnimAuto.bitmap dessine la vie au pixel fin sur la toile recadrée (même place qu'au pixel du sprite)
    val rec = fr.terminagotchi.Sprites.recadrer(st)
    val rv = rec.vie
    // le dessin réel commence PAD pixels après le coin de la vie : il faut ≥ 1 pixel de marge sur les côtés (ondulation)
    // et ≥ 2 au-dessus (respiration), et rien ne doit dépasser en bas
    verifV(rv != null && rv.x0 + Vie.PAD >= 1 && rv.y0 + Vie.PAD >= 2 &&
        rv.x0 + Vie.largeur(rv.analyse) - Vie.PAD + 1 <= rec.largeur && rv.y0 + Vie.hauteur(rv.analyse) <= rec.hauteur,
        "la vie au pixel fin garde sa place sur la toile recadrée (en-tête Android) : " +
            "${rv?.x0},${rv?.y0} sur ${rec.largeur}×${rec.hauteur}")

    println("\n$okV réussis, $koV échoués")
    if (koV > 0) System.exit(1)
}
