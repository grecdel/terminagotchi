/*
 * Test JVM des sons (portage de pc/outils/test_sons.py) :
 *   1. la recette (Sons.kt) : les vecteurs communs donnees/sons/vecteurs.json (calcul exact de expo, 2^x, sinus, hasard,
 *      puis l'empreinte de CHAQUE son : réussites, erreurs, 9 musiques, gardiens, 151 cris et leurs variantes) donnent
 *      EXACTEMENT les mêmes échantillons qu'en Python ;
 *   2. les règles : quel son après un tour (au plus un, petite réussite une fois sur trois), les permissions (silencieux
 *      par défaut, nuit 20 h 30 – 7 h 30, « ce soir seulement », mode classe, créature qui dort) ;
 *   3. la commande `son …` (même effet que `tg son …`) et Sons.son() qui ne joue rien sans les réglages.
 *   java -cp <imitations>:<appli.jar>:sons.jar:kotlin-stdlib.jar SonsKt app/src/main/assets
 */
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Sons
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

class ActifsS(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilS(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsS(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okS = 0
var koS = 0
fun verifierS(c: Boolean, m: String) {
    if (c) okS++ else koS++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun empreinteS(e: ShortArray): String {
    val b = java.nio.ByteBuffer.allocate(e.size * 2).order(java.nio.ByteOrder.LITTLE_ENDIAN)
    for (s in e) b.putShort(s)
    return MessageDigest.getInstance("SHA-256").digest(b.array()).joinToString("") { "%02x".format(it) }
}

fun resumeS(o: JSONObject?): Sons.Resume? = o?.let {
    Sons.Resume(it.getInt("lecon"), it.getInt("etape"), it.getInt("niveau"), it.getInt("stade"), it.getInt("exploits"),
        it.getInt("collection"), it.getInt("total"))
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_sons_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilS(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    val v = JSONObject(File(depot, "donnees/sons/vecteurs.json").readText())

    println("1. La recette : vecteurs communs (donnees/sons/vecteurs.json)")
    val c = v.getJSONObject("calcul")
    fun paires(cle: String, f: (Double) -> Double): Boolean {
        val a = c.getJSONArray(cle)
        return (0 until a.length()).all { val p = a.getJSONArray(it); f(p.getDouble(0)) == p.getString(1).toDouble() }
    }
    verifierS(paires("expo") { Sons.expo(it) }, "e^x au bit près")
    verifierS(paires("pow2") { Sons.pow2(it) }, "2^x au bit près")
    verifierS(paires("note") { Sons.note(it.toInt()) }, "fréquence des notes au bit près")
    verifierS(paires("sin") { Sons.SIN[it.toInt()] }, "table du sinus au bit près")
    val al = c.getJSONArray("alea")
    verifierS(listOf(0L, 1L, 7L, 123456L, 4294967295L).withIndex().all { (i, g) -> Sons.Alea(g).suivant() == al.getLong(i) }, "le hasard reproductible")
    verifierS(Sons.md5("braisillon").toList() == (0 until 16).map { c.getJSONArray("md5").getInt(it) }, "md5 du nom d'espèce")
    val ex = v.getJSONObject("exemple")
    val e0 = Sons.echantillons(ex.getString("nom"))
    val deb = ex.getJSONArray("debut")
    verifierS((0 until deb.length()).all { e0[it].toInt() == deb.getInt(it) }, "les 200 premiers échantillons de la petite réussite")
    val sons = v.getJSONArray("sons")
    val rates = mutableListOf<String>()
    var musiques = 0
    var cris = 0
    val t0 = System.currentTimeMillis()
    for (i in 0 until sons.length()) {
        val s = sons.getJSONObject(i)
        val e = Sons.pcm(Sons.fabriquer(s.getString("nom")))
        if (e.size != s.getInt("n") || empreinteS(e) != s.getString("empreinte")) rates.add(s.getString("nom"))
        if (s.getString("nom").startsWith("biome_")) musiques++
        if (s.getString("nom").startsWith("cri:")) cris++
    }
    verifierS(rates.isEmpty(), "${sons.length()} sons identiques au Python (dont $musiques musiques, $cris cris) en ${System.currentTimeMillis() - t0} ms ${rates.take(5)}")
    verifierS(musiques == 9 && cris >= 151, "les 9 musiques et au moins 151 cris sont vérifiés")

    println("2. Les règles")
    val ch = v.getJSONArray("choisir")
    verifierS((0 until ch.length()).all {
        val k = ch.getJSONObject(it)
        val r = Sons.choisir(resumeS(k.optJSONObject("avant")), resumeS(k.optJSONObject("apres")), k.getString("marque"), k.getInt("n"))
        r.first == k.getJSONArray("attendu").getString(0) && r.second == k.getJSONArray("attendu").getInt(1)
    }, "${ch.length()} cas : quel son après un tour (au plus un ; petite réussite une fois sur trois)")
    val ap = v.getJSONArray("apparitions")
    verifierS((0 until ap.length()).all {
        val k = ap.getJSONObject(it)
        Sons.nomApparition(k.getString("id"), k.getJSONObject("ind"), k.getBoolean("nouvelle")) == k.getString("attendu")
    }, "${ap.length()} cas : le son d'une apparition (motif du gardien, cri d'une espèce nouvelle)")
    val pe = v.getJSONArray("permis")
    val pRates = (0 until pe.length()).filter {
        val k = pe.getJSONObject(it)
        val q = k.getJSONArray("quand")
        Sons.permis(k.getJSONObject("r"), k.getString("cat"), q.getInt(0), q.getInt(1), q.getInt(2), q.getInt(3),
            k.getBoolean("classe"), k.getBoolean("dort")) != k.getBoolean("attendu")
    }
    verifierS(pRates.isEmpty(), "${pe.length()} cas de permission identiques (nuit, ce soir, classe, sommeil) $pRates")
    val so = v.getJSONArray("soirees")
    verifierS((0 until so.length()).all {
        val q = so.getJSONObject(it).getJSONArray("quand")
        Sons.soiree(q.getInt(0), q.getInt(1), q.getInt(2), q.getInt(3)) == so.getJSONObject(it).getString("attendu")
    }, "la soirée (20 h 30 – 7 h 30, après minuit = la veille)")
    val cat = v.getJSONObject("categories")
    verifierS(cat.keys().asSequence().all { Sons.categorie(it) == cat.getString(it) }, "catégories (evolution = réussite, cri, musique)")

    println("3. La commande et Sons.son()")
    val r = Sons.reglages(jeu)
    verifierS(!r.getBoolean("on") && !r.getBoolean("musique"), "silencieux par défaut, musique éteinte")
    verifierS(!Sons.son(jeu, "evolution"), "Sons.son ne joue rien tant que le son est éteint")
    verifierS(Sons.commande(jeu, "").contains("🔇") || Sons.commande(jeu, "").isNotBlank(), "son : l'état des réglages")
    Sons.commande(jeu, "oui")
    verifierS(Sons.reglages(jeu).getBoolean("on") && Sons.reglages(jeu).getBoolean("demande"), "son oui : allumé (et la question ne sera plus posée)")
    Sons.commande(jeu, "musique 40")
    verifierS(Sons.reglages(jeu).getInt("v_musique") == 40 && Sons.reglages(jeu).getBoolean("musique"), "son musique 40 : le volume, et la musique s'allume")
    Sons.commande(jeu, "cris 0")
    verifierS(Sons.reglages(jeu).getInt("v_cris") == 0, "son cris 0 : les cris se taisent")
    Sons.commande(jeu, "cris 250")
    verifierS(Sons.reglages(jeu).getInt("v_cris") == 100, "un volume reste entre 0 et 100")
    Sons.commande(jeu, "musique non")
    verifierS(!Sons.reglages(jeu).getBoolean("musique"), "son musique non")
    jeu.module("espace").put("classe", true)
    verifierS(!Sons.peut(jeu, "reussite_etape") && Sons.musique(jeu, "feu") == null, "le mode classe coupe tout")
    jeu.module("espace").put("classe", false)
    Sons.commande(jeu, "non")
    verifierS(!Sons.reglages(jeu).getBoolean("on"), "son non : tout se tait")
    val av = Sons.resume(jeu)
    Sons.marquer("erreur_presque")
    verifierS(Sons.apresTour(jeu, av, av, 127) == null && Sons.marque.isEmpty(), "après un tour : la marque est consommée, pas de question")
    // la première éclosion : la question, une seule fois
    jeu.module("son").put("demande", false)
    val oeuf = Sons.Resume(0, 0, 1, 0, 0, 0, 0)
    val bebe = Sons.Resume(0, 0, 2, 1, 0, 0, 1)
    val q1 = Sons.apresTour(jeu, oeuf, bebe, 0)
    val q2 = Sons.apresTour(jeu, oeuf, bebe, 0)
    verifierS(q1 == Langue.t("son.question.terminal", "cmd" to "son", "nom" to jeu.nom) && q2 == null, "à la première éclosion : « Tu veux m'entendre ? », une seule fois")
    verifierS(Langue.t("son.question").isNotBlank() && Langue.t("son.question") != "son.question", "la question existe en français")

    println("\n$okS ✔   $koS ✖")
    dossier.deleteRecursively()
    if (koS > 0) kotlin.system.exitProcess(1)
}
