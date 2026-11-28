/*
 * Test JVM : « Signaler un souci » (idée 76, Signaler.kt) et le nuage de synchro (idée 74, Recensement.etatNuage,
 * NuageDessin), portage de pc/outils/test_signaler.py :
 *   1. les vecteurs partagés avec Python (donnees/bug/vecteurs.json, donnees/synchro/vecteurs.json) : nettoyer, le
 *      rapport (titre, corps), l'adresse de la page GitHub, l'état du nuage — exactement les mêmes résultats ;
 *   2. une panne notée (files/erreurs.log) se relit : commande, erreur et endroit, trace en noms de fichiers seulement ;
 *      le rapport ne contient ni le nom de la créature, ni le pseudo, ni les dossiers de l'appareil ;
 *   3. le nuage dessiné : orange barré (hors ligne), bleu avec une flèche (envoi) ; une synchro ratée met « hors »,
 *      une synchro réussie l'enlève ;
 *   4. les textes dans les 14 langues.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/SignalerSynchro.kt -d signaler.jar
 *   java -cp <imitations>:<appli.jar>:signaler.jar:kotlin-stdlib.jar SignalerSynchroKt app/src/main/assets
 */
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.NuageDessin
import fr.terminagotchi.Recensement
import fr.terminagotchi.Signaler
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsSB(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilSB(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsSB(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okSB = 0
var koSB = 0
fun verifSB(c: Boolean, m: String) {
    if (c) okSB++ else koSB++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun chainesSB(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_signaler_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilSB(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")

    println("1. Les vecteurs communs (donnees/bug/vecteurs.json, donnees/synchro/vecteurs.json)")
    val vb = JSONObject(File("donnees/bug/vecteurs.json").readText())
    val nt = vb.getJSONArray("nettoyer")
    for (i in 0 until nt.length()) {
        val c = nt.getJSONObject(i)
        val r = Signaler.nettoyer(c.getString("texte"), c.getString("home"), c.getString("utilisateur"), chainesSB(c.getJSONArray("caches")))
        verifSB(r == c.getString("attendu"), "nettoyer · ${c.getString("nom")} → $r")
    }
    val rp = vb.getJSONArray("rapport")
    for (i in 0 until rp.length()) {
        val c = rp.getJSONObject(i)
        val ch = c.getJSONObject("champs")
        val e = c.getJSONObject("etiquettes").let { o -> o.keys().asSequence().associateWith { o.getString(it) } }
        val (titre, corps) = Signaler.rapport(Signaler.Champs(ch.getString("version"), ch.getString("appareil"), ch.getString("langue"),
            ch.getString("ecran"), ch.getString("commande"), ch.getString("erreur"), chainesSB(ch.getJSONArray("trace"))), e)
        verifSB(titre == c.getString("titre"), "rapport · ${c.getString("nom")} : le titre")
        verifSB(corps == c.getString("corps"), "rapport · ${c.getString("nom")} : le corps")
        verifSB(Signaler.adresse(titre, corps) == c.getString("adresse"), "rapport · ${c.getString("nom")} : l'adresse (même encodage)")
    }
    val vs = JSONObject(File("donnees/synchro/vecteurs.json").readText()).getJSONArray("nuage")
    for (i in 0 until vs.length()) {
        val c = vs.getJSONObject(i)
        val e = Recensement.etatNuage(c.getJSONObject("compte"), c.getInt("total"), c.getBoolean("envoi"))
        val att = c.optJSONArray("attendu")
        val ok = if (att == null) e == null else e != null && e.first == att.getString(0) && e.second == att.getInt(1)
        verifSB(ok, "nuage · ${c.getString("nom")} → $e")
    }

    println("2. Une panne notée, puis le rapport")
    val panne = try {
        listOf(1)[3]
        null
    } catch (e: Exception) { e }!!
    Signaler.noter(dossier, panne, "cat repas.txt")
    val p = Signaler.dernierePanne(dossier)!!
    verifSB(p[1] == "cat repas.txt", "la commande qui a planté est gardée")
    @Suppress("UNCHECKED_CAST") val trace = p[3] as List<String>
    verifSB(trace.isNotEmpty() && "IndexOutOfBoundsException" in trace.last().substringBefore(":"),
        "l'erreur : son type et son message (${trace.last().take(60)})")
    verifSB(trace.none { "/" in it.substringBefore(' ') }, "la trace : des noms de fichiers seulement, jamais de dossiers")
    Signaler.noter(dossier, IllegalStateException("plus récente", RuntimeException("la cause")), "ls")
    val p2 = Signaler.dernierePanne(dossier)!!
    verifSB(p2[1] == "ls" && (p2[2] as String).startsWith("RuntimeException: la cause"), "la dernière panne gagne, et c'est la cause qui est dite")
    val home = dossier.parentFile.absolutePath
    Signaler.noter(dossier, IllegalArgumentException("fichier $home/x/Noisette.txt de Zorglub"), "cat Noisette.txt")
    val ch = Signaler.champs(dossier, "0.1.97", "Android 14 · téléphone", t("bug.tel.ecran", "i" to 2, "n" to 2), home, listOf("Noisette", "Zorglub"))
    val (titre, corps) = Signaler.rapport(ch, Signaler.etiquettes())
    val tout = titre + corps
    verifSB(home !in tout && "Noisette" !in tout && "Zorglub" !in tout, "jamais : le dossier de l'appareil, le nom de la créature, le pseudo")
    verifSB(corps.startsWith("Ce que je faisais : \n") && "Version : 0.1.97 · Android" in corps && "Écran : terminal, onglet 2 sur 2" in corps
        && "Dernière commande : cat ….txt" in corps, "le corps : version, appareil, écran, commande (nettoyée)")
    val url = Signaler.adresse(titre, corps)
    verifSB(url.startsWith("https://github.com/grecdel/terminagotchi/issues/new?title=%5Bbug%5D%20IllegalArgumentException") && url.length < 8000,
        "l'adresse : la page « nouveau signalement », déjà remplie")
    val src = File("app/src/main/java/fr/terminagotchi/Signaler.kt").readText()
    verifSB("HttpURLConnection" !in src && "openConnection" !in src && "Socket" !in src, "Signaler.kt ne fait aucun appel réseau")
    val vide = File(dossier, "vide").apply { mkdirs() }
    verifSB(Signaler.dernierePanne(vide) == null && Signaler.rapport(Signaler.champs(vide, "1", "a", "e", home, emptyList()),
        Signaler.etiquettes()).first == "[bug] un souci dans le jeu", "sans panne notée : `bug` marche quand même")
    File(vide, Signaler.JOURNAL).writeText("n'importe quoi\n\n")
    verifSB(Signaler.dernierePanne(vide) == null, "un journal illisible : rien (pas de plantage)")

    println("3. Le nuage")
    val b = NuageDessin.pilule("hors", "hors ligne", 2f)
    val couleurs = (0 until b.w * b.h).map { b.px[it] }.toSet()
    verifSB(NuageDessin.ORANGE in couleurs && NuageDessin.BLEU !in couleurs, "hors ligne : un nuage orange")
    val b2 = NuageDessin.pilule("envoi", "envoi…", 2f)
    verifSB(NuageDessin.BLEU in (0 until b2.w * b2.h).map { b2.px[it] }.toSet(), "envoi : un nuage bleu")
    verifSB(NuageDessin.FORME.all { it.length == 12 } && NuageDessin.MARQUES.getValue("hors").all { (i, j) -> NuageDessin.FORME[j][i] == 'X' }
        && NuageDessin.MARQUES.getValue("envoi").all { (i, j) -> NuageDessin.FORME[j][i] == 'X' }, "la barre et la flèche sont creusées dans le nuage")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.total = 7
    verifSB(Recensement.nuage(jeu) == null && Recensement.phraseNuage(jeu) == "", "sans compte : jamais de nuage")
    Recensement.enregistrer(jeu, "Lou", "cle", "http://127.0.0.1:9")
    val prep = Recensement.preparer(jeu, forcer = true)!!
    verifSB(Recensement.nuage(jeu)?.first == "envoi", "pendant l'envoi : « envoi »")
    Recensement.appliquer(jeu, prep, JSONObject().put("erreur", "pas de connexion"), "")
    verifSB(Recensement.nuage(jeu) == ("hors" to 7) && "7" in Recensement.phraseNuage(jeu), "le site ne répond pas : hors ligne, 7 en attente")
    val prep2 = Recensement.preparer(jeu, forcer = true)!!
    Recensement.appliquer(jeu, prep2, JSONObject().put("etat", JSONObject().put("xp", jeu.xp).put("total", 7).put("colles", 0)
        .put("stats", JSONObject())), "http://127.0.0.1:9")
    verifSB(Recensement.nuage(jeu) == null, "une synchro réussie : le nuage s'en va")

    println("4. Les textes dans les 14 langues")
    val cles = listOf("rec.nuage.mot.hors", "rec.nuage.mot.envoi", "rec.nuage.attente", "rec.nuage.dit.hors", "rec.nuage.dit.envoi",
        "bug.titre", "bug.adulte", "bug.question", "bug.non", "bug.partira", "bug.jamais", "bug.ouverte", "bug.annule",
        "bug.tel.signaler", "bug.tel.ouvrir", "bug.tel.fichier", "bug.tel.annuler", "bug.tel.note", "bug.tel.avant", "bug.tel.panne",
        "bug.tel.ecran", "bug.tel.espace", "bug.tel.telephone", "bug.tel.tablette", "bug.tel.ecrit", "bug.tel.erreur",
        "bug.tel.pas_navigateur") + listOf("faisais", "version", "appareil", "langue", "ecran", "commande", "erreur", "sans", "pied").map { "bug.l.$it" }
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val tx = cles.map { t(it, "n" to 3, "q" to "12 × 13", "i" to 1, "fichier" to "f") }
        verifSB(tx.all { it.isNotEmpty() && !it.startsWith("bug.") && !it.startsWith("rec.nuage") && "{" !in it }, "$code : ${tx[13]} · ${tx[0]}")
    }
    Langue.definir("fr")

    println("\n$okSB réussis, $koSB échoués")
    if (koSB > 0) System.exit(1)
}
