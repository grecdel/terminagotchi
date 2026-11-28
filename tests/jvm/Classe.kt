/*
 * Test JVM du mode classe et de l'accessibilité (idées du 3 novembre) : Classe.kt, EcransClasse.kt, Confort.kt.
 *   1. les vecteurs communs donnees/classe/vecteurs.json (codes, dont la lettre V) et vecteurs_acces.json (confort,
 *      séance guidée, place de la classe, carte de visite) : mêmes résultats qu'en Python ;
 *   2. la séance guidée sur une vraie partie (commencer, suivante, question, trace, fin) ;
 *   3. le dessin sans écran (tableau, carte de visite) : pas d'exception, les textes attendus sont là ;
 *   4. la place : jamais d'adresse publique, rien n'est envoyé sans le code V.
 *
 *   java -cp <imitations>:<appli.jar>:classe.jar:kotlin-stdlib.jar ClasseKt app/src/main/assets
 */
import fr.terminagotchi.CarteVisite
import fr.terminagotchi.Classe
import fr.terminagotchi.Confort
import fr.terminagotchi.EcransDessin
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Place
import fr.terminagotchi.Poses
import fr.terminagotchi.Seances
import fr.terminagotchi.Toile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsC(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilC(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsC(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okC = 0
var koC = 0

fun verifC(c: Boolean, m: String) {
    if (c) okC++ else koC++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

class ToileC : Toile {
    val textes = mutableListOf<String>()
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) {}
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) {}
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) {}
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) {}
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) {}
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) {}
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { textes.add(s) }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.55f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) {}
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) {}
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) {}
}

/** Une valeur JSON (Python) comparée à une valeur Kotlin (Map, List, String, Int, Boolean). */
fun egal(j: Any?, k: Any?): Boolean = when (j) {
    null, JSONObject.NULL -> k == null || k == ""
    is JSONArray -> k is List<*> && k.size == j.length() && (0 until j.length()).all { egal(j.get(it), k[it]) }
    is Number -> k is Number && j.toDouble() == k.toDouble()
    else -> j == k
}

fun main(args: Array<String>) {
    val assets = File(args.getOrElse(0) { "app/src/main/assets" })
    val racine = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "classe_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilC(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    Seances.chargeur = { File(assets, "seances.json").readText() }

    println("1. Les codes de séance (donnees/classe/vecteurs.json)")
    val vc = JSONObject(File(racine, "donnees/classe/vecteurs.json").readText())
    var faux = 0
    for (nom in listOf("codes", "avec_v")) {
        val a = vc.getJSONArray(nom)
        for (i in 0 until a.length()) {
            val x = a.getJSONObject(i)
            if (Classe.fabriquer(x.getInt("n"), x.getString("options")) != x.getString("code")) faux++
            if (Classe.lire(x.getString("code")) != (x.getInt("n") to x.getString("options"))) faux++
        }
    }
    for (nom in listOf("faux", "faux_v")) {
        val a = vc.getJSONArray(nom)
        for (i in 0 until a.length()) {
            val x = a.getJSONObject(i)
            val attendu = x.opt("lu").let { if (it is JSONArray) it.getInt(0) to it.getString(1) else null }
            if (Classe.lire(x.getString("code")) != attendu) { faux++; println("     ${x.getString("code")}") }
        }
    }
    verifC(faux == 0, "fabriquer et lire comme en Python, lettre V comprise ($faux écart(s))")

    println("2. Les vecteurs de l'accessibilité et de la classe (donnees/classe/vecteurs_acces.json)")
    val v = JSONObject(File(racine, "donnees/classe/vecteurs_acces.json").readText())
    faux = 0
    val conf = v.getJSONArray("confort")
    for (i in 0 until conf.length()) {
        val x = conf.getJSONObject(i); val sy = x.getJSONObject("systeme"); val at = x.getJSONObject("attendu")
        val r = Confort.resoudre(x.getJSONObject("c"), x.getString("theme"), sy.getDouble("echelle"), sy.getBoolean("moins_animations"))
        if (r.taille != at.getInt("taille") || r.police != at.getString("police") || r.formes != at.getBoolean("formes") || r.calme != at.getBoolean("calme")) {
            faux++; if (faux < 5) println("     $x → $r")
        }
    }
    verifC(faux == 0, "lecture et confort : ${conf.length()} cas identiques ($faux écart(s))")
    faux = 0
    v.getJSONArray("tailles").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i); if (Confort.tailleDe(x.getDouble("echelle")) != x.getInt("taille")) faux++ } }
    v.getJSONArray("suivantes").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i); if (Confort.tailleSuivante(x.getInt("taille"), x.getInt("sens")) != x.getInt("suivante")) faux++ } }
    verifC(faux == 0, "taille du texte depuis le système, Ctrl + / Ctrl − ($faux écart(s))")
    faux = 0
    v.getJSONArray("privee").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i); if (Place.privee(x.getString("ip")) != x.getBoolean("ok")) { faux++; println("     ${x.getString("ip")}") } } }
    verifC(faux == 0, "place : seules les adresses du réseau local sont acceptées ($faux écart(s))")
    faux = 0
    v.getJSONArray("cle").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i); val at = x.opt("cle").takeIf { it is String }
        if (Place.cle(x.getString("code")) != at) { faux++; println("     ${x.getString("code")} → ${Place.cle(x.getString("code"))} au lieu de $at") } } }
    verifC(faux == 0, "place : la clé vient du code, et seulement s'il a la lettre V ($faux écart(s))")
    faux = 0
    v.getJSONArray("profil").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i); val r = Place.profilValide(x.getJSONObject("p"))
        val at = x.opt("ok")
        val bon = if (at is JSONObject) r != null && r.getString("espece") == at.getString("espece") && r.getString("stade") == at.getString("stade") && r.getInt("niveau") == at.getInt("niveau") else r == null
        if (!bon) { faux++; println("     ${x.getJSONObject("p")} → $r") } } }
    verifC(faux == 0, "place : un profil reçu n'a que espèce, stade, niveau, bien formés ($faux écart(s))")
    faux = 0
    v.getJSONArray("preferes").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i)
        val ordre = x.getJSONArray("ordre").let { o -> (0 until o.length()).map { o.getString(it) } }
        val r = CarteVisite.preferes(x.getJSONObject("compteurs"), ordre)
        if (!egal(x.getJSONArray("gouts"), r)) { faux++; println("     $x → $r") } } }
    v.getJSONArray("jours").let { a -> for (i in 0 until a.length()) { val x = a.getJSONObject(i)
        if (CarteVisite.jours(x.getLong("ne"), x.getLong("maintenant")) != x.getInt("jours")) faux++ } }
    verifC(faux == 0, "carte de visite : goûts préférés et jours comme en Python ($faux écart(s))")
    faux = 0
    val ss = v.getJSONArray("seances")
    for (i in 0 until ss.length()) {
        val x = ss.getJSONObject(i)
        val m = Seances.modele(JSONObject(x.getJSONObject("e").toString()))
        val at = x.getJSONObject("modele")
        for (k in at.keySet()) if (!egal(at.get(k), m[k])) { faux++; if (faux < 6) println("     séance ${x.getJSONObject("e")} : $k = ${m[k]} au lieu de ${at.get(k)}") }
    }
    verifC(faux == 0, "séances guidées : ${ss.length()} modèles identiques au PC ($faux écart(s))")

    println("3. Une vraie partie")
    val jeu = Jeu(app)
    jeu.nom = "Pixel"
    jeu.extra.put("born", System.currentTimeMillis() / 1000 - 3 * 86400)
    for (c in listOf("ls", "ls", "pwd", "cd", "ls")) jeu.manger(c, false)
    val g = jeu.extra.optJSONObject("gouts")
    verifC(g != null && g.optInt("ls") >= 1 && g.optInt("pwd") == 1 && g.optInt("cd") == 1, "chaque goût est compté (la carte de visite) : $g")
    val cv = CarteVisite.contenu(jeu, true)
    verifC(cv["gouts"] == listOf("ls", "pwd", "cd") && cv["jours"] == 4 && cv["nom"] == "Pixel", "contenu de la carte : $cv")
    verifC(CarteVisite.contenu(jeu, false)["nom"] == "", "« sans nom » cache le nom de la créature")
    val tl = ToileC()
    EcransDessin.carte(tl, cv, null)
    verifC(tl.textes.contains("Pixel") && tl.textes.any { it.contains("CC BY-NC-SA") }, "la carte se dessine (nom, licence)")
    verifC(Seances.commande(jeu, listOf("99")).contains("99"), "séance inconnue : message et liste")
    val p = Seances.commande(jeu, listOf("5"))
    verifC(p.contains("▶ 1") && Seances.e(jeu)?.optInt("phase") == 0, "séance 5 commencée, phase 1")
    Seances.commande(jeu, listOf("suivante")); Seances.commande(jeu, listOf("suivante"))
    val m = Seances.modele(Seances.e(jeu)!!)
    verifC(m["k"] == 3, "deux fois « suivante » : phase 3")
    Seances.commande(jeu, listOf("trace"))
    verifC(Seances.modele(Seances.e(jeu)!!)["vue"] == "trace", "« trace » montre la trace écrite")
    for (vue in listOf("trace", "question", "phase")) {
        val t2 = ToileC()
        if (vue == "question") Seances.agir(jeu, "question") else if (vue == "phase") Seances.agir(jeu, "question")
        val z = EcransDessin.tableau(t2, Seances.modele(Seances.e(jeu)!!), null, 0, null)
        verifC(z.any { it.action == "tab:suivante" } && t2.textes.isNotEmpty(), "le tableau se dessine (vue $vue, ${t2.textes.size} textes)")
    }
    for (k in 1..Seances.modele(Seances.e(jeu)!!)["total"] as Int) {
        Seances.agir(jeu, "phase", k)
        val t2 = ToileC()
        EcransDessin.tableau(t2, Seances.modele(Seances.e(jeu)!!), null, 0, null)
    }
    verifC(true, "toutes les phases de la séance 5 se dessinent")
    EcransDessin.tableau(ToileC(), null, null, 0, null)
    verifC(Seances.commande(jeu, listOf("fin")).isNotEmpty() && Seances.e(jeu) == null, "« fin » termine la séance")

    println("4. La place, côté téléphone")
    val cl = Place.Client("05-GS-K", Place.profil(jeu))
    verifC(cl.cle == null && !cl.rejoindre() && cl.etat == "absente", "sans la lettre V : aucune demande")
    verifC(Place.demander("8.8.8.8", Place.PORT, JSONObject()) == null, "une adresse publique est refusée avant toute connexion")
    verifC(Place.profilValide(Place.profil(jeu)) != null, "notre profil est valide (et ne contient ni nom ni pseudo)")
    verifC(!Place.profil(jeu).has("nom") && Place.profil(jeu).length() == 3, "profil : espèce, stade, niveau seulement")

    println("\n$okC ✔  $koC ✖")
    dossier.deleteRecursively()
    if (koC > 0) kotlin.system.exitProcess(1)
}
