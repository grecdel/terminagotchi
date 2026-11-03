/*
 * Test JVM : la vérification au démarrage (Sante.kt) et la sauvegarde exportable (Sauvegarde.kt), portage de
 * pc/outils/test_sante.py :
 *   1. les vecteurs partagés avec Python (donnees/sante/vecteurs.json) : la liste des parties réparée pareil ;
 *   2. au démarrage : liste des parties abîmée ou incomplète refaite (l'ancienne gardée à côté), sauvegarde coupée
 *      remise en place depuis sauvegarde.tmp (sceau vérifié), rien à faire quand tout va bien ;
 *   3. exporter → importer : la créature revient comme une partie de plus (l'autre rangée), avec son terrain et ses
 *      droits (444) ; ni sceau ni clé du compte dans le fichier ; fichier modifié, coupé, d'un PC (fichier d'exemple
 *      fabriqué par Python : même format, même contrôle), d'une version future : refusés ; chemins « .. » jamais
 *      écrits ; 10 parties au plus ; les textes dans les 14 langues.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/SanteSauvegarde.kt -d sante.jar
 *   java -cp <imitations>:<appli.jar>:sante.jar:kotlin-stdlib.jar SanteSauvegardeKt app/src/main/assets
 */
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Parties
import fr.terminagotchi.Sante
import fr.terminagotchi.Sauvegarde
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsSS(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilSS(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsSS(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okSS = 0
var koSS = 0
fun verifSS(c: Boolean, m: String) {
    if (c) okSS++ else koSS++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun versKotlin(v: Any?): Any? = when (v) {
    null, JSONObject.NULL -> null
    else -> v
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_sante_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilSS(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")

    println("1. Les vecteurs communs (donnees/sante/vecteurs.json)")
    val v = JSONObject(File("donnees/sante/vecteurs.json").readText()).getJSONArray("index")
    for (i in 0 until v.length()) {
        val c = v.getJSONObject(i)
        val idx = versKotlin(c.opt("index"))
        val actif = versKotlin(c.opt("sauvegarde")) as String?
        val r = c.getJSONArray("rangees").let { a -> (0 until a.length()).map { a.getString(it) } }
        val (o, repare) = Sante.reparerIndex(idx, actif, r)
        val att = c.getJSONObject("attendu")
        val ordre = (0 until o.getJSONArray("ordre").length()).map { o.getJSONArray("ordre").getString(it) }
        val ordreAtt = (0 until att.getJSONArray("ordre").length()).map { att.getJSONArray("ordre").getString(it) }
        verifSS(o.getString("active") == att.getString("active") && ordre == ordreAtt && repare == c.getBoolean("repare"),
            "${c.getString("nom")} → ${o} $repare")
    }

    println("2. Au démarrage")
    verifSS(Sante.auDemarrage(app).isEmpty(), "premier lancement : rien à dire")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.xp = 1234
    jeu.module("compte").put("cle", "SECRET-123").put("pseudo", "Lou")
    jeu.sauver()
    verifSS(Sante.auDemarrage(app).isEmpty(), "une partie qui va bien : rien à dire")
    // une deuxième partie (Pixel est rangée)
    val id2 = Parties.nouvelle(app)!!
    jeu.recharger(); jeu.nom = "Brindille"; jeu.sauver()
    val idx = File(File(dossier, "parties"), "index.json")
    idx.writeText("{coupé")
    val m = Sante.auDemarrage(app)
    verifSS(m.size == 1 && m[0].startsWith("🔧") && Parties.liste(app).map { it.nom }.toSet() == setOf("Pixel", "Brindille"),
        "liste des parties abîmée : refaite, les deux créatures retrouvées (« ${m.firstOrNull()} »)")
    verifSS(File(dossier, "parties").listFiles()!!.any { it.name.startsWith("index.json.casse-") }, "l'ancienne gardée à côté")
    verifSS(Parties.active(app) == id2, "la partie active reste Brindille")
    verifSS(Sante.auDemarrage(app).isEmpty(), "ensuite : plus rien à réparer")
    // sauvegarde coupée : la partie active abîmée, sauvegarde.tmp bonne et plus récente que la copie de secours
    jeu.xp = 77; jeu.sauver()
    val act = Parties.fichierActif(app)
    val tmp = File(dossier, "sauvegarde.tmp")
    act.copyTo(tmp, overwrite = true)
    File(dossier, "sauvegarde.json.bak").setLastModified(System.currentTimeMillis() - 3_600_000)
    act.writeText("{\"nom\": \"Bri")
    val m2 = Sante.auDemarrage(app)
    verifSS(m2 == listOf(t("sante.tmp")) && !tmp.exists() && Jeu(app).xp == 77, "sauvegarde coupée : l'écriture inachevée bonne revient")
    // une sauvegarde.tmp modifiée hors du jeu (sceau faux) n'est jamais prise
    fr.terminagotchi.Garde.pourTests(exiger = true)
    val faux = JSONObject(act.readText()); faux.put("xp", 999999)
    tmp.writeText(faux.toString())
    act.writeText("{")
    val m3 = Sante.auDemarrage(app)
    verifSS(m3.none { it == t("sante.tmp") } && tmp.exists(), "une écriture inachevée sans bon sceau : jamais prise")
    fr.terminagotchi.Garde.pourTests(exiger = false)
    tmp.delete()
    jeu.recharger()
    jeu.sauver()

    println("3. La sauvegarde dans un fichier")
    Parties.charger(app, "1"); jeu.recharger()
    verifSS(jeu.nom == "Pixel", "on revient sur Pixel")
    val nid = File(jeu.terrain, "nid").apply { mkdirs() }
    File(nid, "repas.txt").writeText("pomme\n")
    File(nid, "repas.txt").setWritable(false, false)
    File(jeu.terrain, "gros.bin").writeBytes(ByteArray(Sauvegarde.MAX_FICHIER + 1))
    try { java.nio.file.Files.createSymbolicLink(File(jeu.terrain, "lien").toPath(), File("/etc/passwd").toPath()) } catch (e: Exception) {}
    val (texte, laisses) = Sauvegarde.fabriquer(app, jeu)
    val o = JSONObject(texte)
    verifSS(o.getString("plateforme") == "android" && o.getString("nom") == "Pixel" && o.getInt("niveau") == jeu.niveau, "le fichier dit ce qu'il contient")
    verifSS("SECRET-123" !in texte && "\"sceau\"" !in texte, "ni la clé du compte ni le sceau du téléphone dans le fichier")
    verifSS(laisses == 2, "le fichier trop gros et le lien laissés de côté ($laisses)")
    verifSS(Sauvegarde.nomDeFichier("Pixel").matches(Regex("terminagotchi-Pixel-\\d{4}-\\d\\d-\\d\\d\\.tgsauve")), "nom proposé : ${Sauvegarde.nomDeFichier("Pixel")}")
    // on change, puis on importe
    jeu.nom = "Autre"; jeu.xp = 5; jeu.sauver()
    File(nid, "repas.txt").setWritable(true, false); File(nid, "repas.txt").writeText("poire\n")
    val avant = Parties.liste(app).size
    val r = Sauvegarde.importer(app, jeu, texte)
    verifSS(r.startsWith("💾 Pixel est de retour") && jeu.nom == "Pixel" && jeu.xp == 1234, "importer : « $r »")
    verifSS(Parties.liste(app).size == avant + 1 && Parties.liste(app).any { it.nom == "Autre" }, "la partie d'avant est rangée, pas remplacée")
    verifSS(File(jeu.terrain, "nid/repas.txt").readText() == "pomme\n" && !File(jeu.terrain, "nid/repas.txt").canWrite(),
        "le terrain revient avec ses droits (repas.txt en lecture seule)")
    verifSS(jeu.module("compte").optString("cle") == "SECRET-123", "le compte de l'appareil suit le joueur")
    verifSS(fr.terminagotchi.Garde.acceptable(Parties.fichierActif(app).readText()), "la partie importée est scellée par CE téléphone")

    println("   refus")
    fun refus(x: String): String? = try { Sauvegarde.lire(x); null } catch (e: Sauvegarde.Refus) { e.cle }
    verifSS(refus(texte.take(texte.length / 2)) == "svg.refus.illisible", "fichier coupé")
    val mod = JSONObject(texte); val c = JSONObject(mod.getString("contenu")); c.getJSONObject("partie").put("xp", 999999); mod.put("contenu", c.toString())
    verifSS(refus(mod.toString()) == "svg.refus.abime", "XP changée à la main : refusé")
    verifSS(refus(JSONObject(texte).put("version", 9).toString()) == "svg.refus.version", "version future")
    verifSS(refus("{\"a\":1}") == "svg.refus.illisible" && refus("") == "svg.refus.illisible", "autre chose")
    val pc = File("donnees/sante/exemple_pc.tgsauve").readText()
    verifSS(refus(pc) == "svg.refus.plateforme", "le fichier d'exemple fabriqué par Python (PC) : même format et même contrôle, refusé pour l'appareil")
    val pcAbime = JSONObject(pc); pcAbime.put("contenu", pcAbime.getString("contenu").replace("Exemple", "Exempla"))
    verifSS(refus(pcAbime.toString()) == "svg.refus.abime", "… et modifié : abîmé (le contrôle est le même qu'en Python)")
    for (mauvais in listOf("../x", "/etc/x", "a/../../b", "C:/x", "a\\b", "", "./x", "a//b"))
        verifSS(Sauvegarde.cheminSur(mauvais) == null, "chemin refusé : \"$mauvais\"")
    // fichier piégé, contrôle recalculé : rien hors du terrain
    val p = JSONObject(texte); val pc2 = JSONObject(p.getString("contenu"))
    pc2.getJSONArray("terrain").put(JSONObject().put("chemin", "../../evade.txt").put("b64", "eA=="))
    val contenu = pc2.toString()
    p.put("contenu", contenu).put("controle", java.security.MessageDigest.getInstance("SHA-256").digest(contenu.toByteArray()).joinToString("") { "%02x".format(it) })
    val r2 = Sauvegarde.importer(app, jeu, p.toString())
    verifSS(r2.startsWith("💾") && dossier.walkTopDown().none { it.name == "evade.txt" }, "fichier piégé (../) : rien écrit hors du terrain")
    var garde = 0
    while (!Parties.pleine(app) && garde++ < 20) {       // chaque nouvel œuf reçoit un nom (sinon il est remplacé)
        Parties.nouvelle(app); jeu.recharger(); jeu.nom = "P$garde"; jeu.sauver()
    }
    verifSS(Sauvegarde.importer(app, jeu, texte) == t("svg.plein", "max" to Parties.MAX), "10 parties : on le dit")

    println("4. Les textes dans les 14 langues")
    for (code in listOf("fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur")) {
        Langue.definir(code)
        val tx = listOf(t("sante.index", "n" to 2), t("sante.tmp"), t("svg.aide.tel"), t("svg.tel.exporte", "nom" to "P", "fichier" to "f", "taille" to "1 Ko"),
            t("svg.importe.tel", "nom" to "P", "niveau" to 2, "date" to "d"), t("svg.refus.abime"), t("svg.tel.annule"), t("svg.plein", "max" to 10))
        verifSS(tx.none { it.startsWith("sante.") || it.startsWith("svg.") || "{" in it }, "$code : ${tx[0].take(40)}")
    }
    Langue.definir("fr")
    dossier.walkTopDown().forEach { it.setWritable(true, false) }
    dossier.deleteRecursively()
    println("\n$okSS réussis, $koSS échoués")
    if (koSS > 0) kotlin.system.exitProcess(1)
}
