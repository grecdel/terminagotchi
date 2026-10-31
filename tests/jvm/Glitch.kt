/*
 * Test JVM de l'effet glitch (portage de pc/outils/test_glitch.py) :
 *   1. l'effet sur l'image (Glitch.kt) : les vecteurs communs donnees/glitch/vecteurs.json (empreinte des pixels de chaque
 *      cas, horloge des éclairs, fnv) donnent EXACTEMENT les mêmes résultats qu'en Python et en JavaScript ;
 *   2. le tirage du glitch (Tirage.glitch, à part : compteur + 2^20) : donnees/anti_triche/vecteurs.json (« glitchs ») ;
 *      les tirages déjà enregistrés ne changent pas ;
 *   3. les gardiens de la Citadelle : 8 boîtes, 8 espèces différentes ; maîtriser une boîte (son exploit) rend son
 *      gardien plus fréquent (faveur « gardien ») et, quand il apparaît, glitch 1 fois sur 8 environ ; ailleurs,
 *      très rare ; les 4 variantes Démons ne sont plus réservées ;
 *   4. l'image : Bestiaire.bitmap, AnimAuto.bitmap (vie au pixel fin), les poses (Album.image) changent avec un individu
 *      glitch et pas sans ; la balise ¤…!graine¤ ; le nom avec ▚.
 *   java -cp <imitations>:<appli.jar>:glitch.jar:kotlin-stdlib.jar GlitchKt app/src/main/assets
 */
import fr.terminagotchi.AnimAuto
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Glitch
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Poses
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Tirage
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

class ActifsG(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilG(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsG(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okG = 0
var koG = 0
fun verifierG(c: Boolean, m: String) {
    if (c) okG++ else koG++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun empreinteG(px: IntArray): String {
    val sb = StringBuilder()
    for (p in px) sb.append(String.format("%08x", p))
    return MessageDigest.getInstance("SHA-256").digest(sb.toString().toByteArray()).joinToString("") { "%02x".format(it) }
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_glitch_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilG(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"

    println("1. L'effet sur l'image : vecteurs communs (donnees/glitch/vecteurs.json)")
    val v = JSONObject(File(depot, "donnees/glitch/vecteurs.json").readText())
    val fnv = v.getJSONArray("fnv")
    verifierG((0 until fnv.length()).all { java.lang.Long.toUnsignedString(Glitch.fnv(fnv.getJSONObject(it).getString("texte"))) == fnv.getJSONObject(it).getString("h") },
        "fnv1a-64 identique (UTF-8 compris)")
    val imgs = v.getJSONObject("images")
    val cas = v.getJSONArray("cas")
    val rates = mutableListOf<String>()
    for (i in 0 until cas.length()) {
        val c = cas.getJSONObject(i)
        val im = imgs.getJSONObject(c.getString("image"))
        val w = im.getInt("w"); val h = im.getInt("h"); val s = c.getInt("s")
        val src = im.getJSONArray("px").let { a -> IntArray(a.length()) { java.lang.Long.parseLong(a.getString(it), 16).toInt() } }
        val px = IntArray(w * s * h * s) { k -> src[(k / (w * s) / s) * w + (k % (w * s)) / s] }
        val o = Glitch.appliquer(w * s, h * s, px, c.getString("graine"), c.getString("style"), c.getInt("phase"), s)
        if (empreinteG(o) != c.getString("empreinte")) rates.add("${c.getString("image")} s=$s ${c.getString("style")}${c.getInt("phase")}")
    }
    verifierG(rates.isEmpty(), "${cas.length()} images identiques au Python ${rates.take(3)}")
    val ex = v.getJSONObject("exemple")
    val car = imgs.getJSONObject("carre").getJSONArray("px").let { a -> IntArray(a.length()) { java.lang.Long.parseLong(a.getString(it), 16).toInt() } }
    val o = Glitch.appliquer(9, 7, car, ex.getString("graine"), ex.getString("style"), ex.getInt("phase"))
    verifierG((0 until o.size).all { String.format("%08x", o[it]) == ex.getJSONArray("px").getString(it) }, "l'exemple pixel par pixel")
    val ecl = v.getJSONArray("eclairs")
    val eRates = (0 until ecl.length()).map { ecl.getJSONObject(it) }.filter { x ->
        val (st, ph) = Glitch.etat(x.getString("graine"), x.getLong("t"))
        st != x.getJSONArray("etat").getString(0) || ph != x.getJSONArray("etat").getInt(1)
    }
    verifierG(eRates.isEmpty(), "${ecl.length()} instants : mêmes éclairs (style C) qu'en Python")
    var c = 0
    for (t in 0L until 60_000L step 10) if (Glitch.etat("a1b2c3d4e5", t).first == "C") c++
    verifierG(c in 200..800, "un éclair de temps en temps : ${c * 10} ms de style C par minute (≈ 4 %)")

    println("2. Le tirage du glitch (à part, compteur + 2^20)")
    val va = JSONObject(File(depot, "donnees/anti_triche/vecteurs.json").readText())
    val gl = va.getJSONArray("glitchs")
    val gRates = (0 until gl.length()).map { gl.getJSONObject(it) }.filter { x ->
        Tirage.glitch(x.getString("valeur"), x.getLong("n"), x.getBoolean("gardien")) != x.getBoolean("glitch") }
    verifierG(gRates.isEmpty() && (0 until gl.length()).count { gl.getJSONObject(it).getBoolean("glitch") } > 10,
        "${gl.length()} tirages du glitch identiques au Python")
    val g0 = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"
    var n1 = 0; var n8 = 0
    for (n in 0L until 200_000L) { if (Tirage.glitch(g0, n)) n1++; if (n < 20_000 && Tirage.glitch(g0, n, true)) n8++ }
    verifierG(n1 in 25..75, "glitch partout : $n1 sur 200 000 (1 chance sur 4096 : ≈ 49)")
    verifierG(n8 in 2200..2800, "gardien d'une boîte maîtrisée : $n8 sur 20 000 (1 chance sur 8 : ≈ 2500)")
    val avant = Tirage.tirer(g0, 3).champs.toString()
    verifierG(!Tirage.tirer(g0, 3).champs.has("glitch") && avant == Tirage.tirer(g0, 3).champs.toString(),
        "le tirage d'un individu ne change pas (le glitch se décide à part)")

    println("3. Les gardiens des boîtes de la Citadelle")
    val gd = Recompenses.gardiens()
    verifierG(gd.size == 8 && gd.values.toSet().size == 8 && gd.values.all { Bestiaire.espece(it) != null },
        "8 boîtes, 8 gardiens différents : $gd")
    verifierG(gd.keys == setOf("enumeration", "droits", "secrets", "hangar", "scripts", "codes", "forensique", "social"), "les 8 catégories")
    verifierG(!Recompenses.reservee(jeu, "arcane", "ricanombre") && !Recompenses.reservee(jeu, "toxique", "sulfurette"),
        "les 4 variantes Démons retournent au tirage normal")
    val ric = Bestiaire.espece("ricanombre")!!
    verifierG(Recompenses.gardienDe(jeu, ric) == null, "avant la boîte : Ricanombre n'est pas encore un gardien rencontrable")
    val msg = Recompenses.exploit(jeu, "citadelle.boite")
    verifierG(msg != null && msg.contains("Ricanombre") && Recompenses.faveur(jeu)?.optInt("reste") == 5,
        "boîte Énumération maîtrisée : $msg")
    verifierG(Recompenses.gardienDe(jeu, ric) == "enumeration" && Recompenses.gardienDe(jeu, Bestiaire.espece("heaumbre")!!) == null,
        "Ricanombre garde la boîte Énumération ; Heaumbre attend la boîte des droits")
    Recompenses.exploit(jeu, "citadelle.boite.droits")
    verifierG(Recompenses.boitesMaitrisees(jeu) == listOf("enumeration", "droits"), "deux boîtes maîtrisées")
    var glitchs = 0
    repeat(800) {
        val ind = Bestiaire.individu(ric, false, "", "classique")
        if (Recompenses.marquerGlitch(jeu, ric, ind) != null) glitchs++
        if (ind.optString("gardien") != "enumeration") koG++
    }
    verifierG(glitchs in 60..150, "le gardien, quand il apparaît : glitch $glitchs fois sur 800 (≈ 100)")
    val autre = Bestiaire.espece("braisillon")!!
    var rares = 0
    repeat(4000) { val ind = Bestiaire.individu(autre, false, "", "classique"); if (Recompenses.marquerGlitch(jeu, autre, ind) != null) rares++ }
    verifierG(rares <= 6, "ailleurs, très rare : $rares sur 4000")
    // la faveur : la première créature gardienne parmi les compteurs essayés
    val vr = JSONObject(File(depot, "donnees/recompenses/vecteurs.json").readText()).getJSONArray("cas")
    val gCas = (0 until vr.length()).map { vr.getJSONObject(it) }.filter { it.getString("genre") == "gardien" }
    verifierG(gCas.size >= 12 && gCas.any { it.getJSONObject("attendu").getJSONObject("champs").getString("espece") == "Ricanombre" },
        "faveurs « gardien » dans les vecteurs communs (${gCas.size})")

    println("4. L'image")
    val ind = JSONObject().put("id", "a1b2c3d4e5").put("espece", "Ombrachne").put("stade", "adulte").put("glitch", true)
    val omb = Bestiaire.espece("ombrachne")!!
    val b0 = Bestiaire.bitmap(omb, false, 3, "adulte")
    val bA = Bestiaire.bitmap(omb, false, 3, "adulte", glitch = Glitch.repos(Glitch.de(ind)))
    val bC = Bestiaire.bitmap(omb, false, 3, "adulte", glitch = Glitch.Spec("a1b2c3d4e5", "C", 2))
    fun px(b: android.graphics.Bitmap) = IntArray(b.width * b.height).also { b.getPixels(it, 0, b.width, 0, 0, b.width, b.height) }
    verifierG(!px(b0).contentEquals(px(bA)) && !px(bA).contentEquals(px(bC)), "Bestiaire.bitmap : repos (A) et éclair (C) différents de l'image normale")
    val bS = Bestiaire.bitmap(omb, true, 3, "adulte", teinte = 0.4, glitch = Glitch.repos("a1b2c3d4e5"))
    verifierG(!px(bS).contentEquals(px(bA)), "shiny + glitch : la teinte d'abord, l'effet par-dessus")
    val img = Bestiaire.image(omb, "adulte")!!
    val anim = AnimAuto.images(img, "statique")
    if (anim.vie != null) {
        val v0 = AnimAuto.bitmap(anim, 5, 3, null)
        val vg = AnimAuto.bitmap(anim, 5, 3, null, Glitch.Spec("a1b2c3d4e5", "A", 0))
        verifierG(!px(v0).contentEquals(px(vg)) && v0.width == vg.width, "la vie au pixel fin : l'effet par-dessus la respiration")
    }
    val mange = AnimAuto.images(img, "mange")
    verifierG(AnimAuto.bitmaps(mange, 2, null, Glitch.repos("x")).size == AnimAuto.bitmaps(mange, 2, null).size, "les animations gardent leurs images")
    val al = Poses.albumEspece(omb, "adulte", false, "a1b2c3d4e5")!!
    val al0 = Poses.albumEspece(omb, "adulte", false)!!
    val c1 = al.image("assis", 0); val c0 = al0.image("assis", 0)
    verifierG(c1.w == c0.w + 4 && c1.ax == c0.ax + 2 && !c1.argb.contentEquals(c0.argb), "les poses de la bulle et de l'île : l'effet sur chaque image")
    verifierG(Bestiaire.balise(ind).contains("!a1b2c3d4e5¤") && !Bestiaire.balise(JSONObject(ind.toString()).put("glitch", false)).contains("!"),
        "la balise du terminal porte la graine d'un glitch : ${Bestiaire.balise(ind)}")
    verifierG(Bestiaire.nomAffiche(omb, false, "rare", true).endsWith(" ▚") && Bestiaire.nomAffiche(omb, true, null, true).contains("✨ ▚"),
        "le nom : ${Bestiaire.nomAffiche(omb, true, null, true)}")

    println("\n$okG réussis, $koG échoués")
    if (koG > 0) System.exit(1)
}
