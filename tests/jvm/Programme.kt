/*
 * Test JVM de la phase 4 sur Android (portage de pc/outils/test_programme.py) :
 *   1. chaque étape du VRAI catalogue de l'appli (Jeu.catalogue) renvoie à une fiche notion (Programme.kt) ;
 *   2. Ponts des Nombres : les vecteurs communs donnees/maths/vecteurs.json (exercices, recherches dans plusieurs
 *      langues, graphe des prérequis) donnent EXACTEMENT les mêmes résultats qu'en Python ; « je ne connais pas »
 *      tapé dans le terminal ouvre un pont ; on descend, on répond, on revient où on était ;
 *   3. récompenses : les vecteurs donnees/recompenses/vecteurs.json (compteur gardé et tirage exact) ; un exploit,
 *      ses faveurs, la série parfaite ;
 *   4. explique : la limite de l'image et l'idée fausse.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Programme.kt -d programme.jar
 *   java -cp <imitations>:<appli.jar>:programme.jar:kotlin-stdlib.jar ProgrammeKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Explique
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maths
import fr.terminagotchi.Programme
import fr.terminagotchi.Recompenses
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsP(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilP(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsP(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okP = 0
var koP = 0
fun verifierP(c: Boolean, m: String) {
    if (c) okP++ else koP++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun liste(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_programme_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilP(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"

    println("1. Chaque étape de l'appli renvoie à une fiche notion")
    val sans = mutableListOf<String>()
    var n = 0
    for ((lid, l) in jeu.catalogue) l.etapes.forEachIndexed { i, e ->
        n++
        if (Programme.notionsDe(e.cmd).isEmpty()) sans.add("$lid.$i `${e.cmd}`")
    }
    verifierP(sans.isEmpty() && n > 100, "$n étapes, toutes avec une fiche ${sans.take(4)}")
    verifierP(File(depot, "donnees/programme.json").readText() == File(assets, "programme.json").readText(),
        "assets/programme.json identique à donnees/programme.json")

    println("2. Les Ponts des Nombres (vecteurs communs avec le PC)")
    val vm = JSONObject(File(depot, "donnees/maths/vecteurs.json").readText())
    val exos = vm.getJSONArray("exercices")
    val diff = mutableListOf<String>()
    for (i in 0 until exos.length()) {
        val x = exos.getJSONObject(i)
        val e = Maths.generer(x.getString("type"), x.getLong("graine"), x.getLong("k"))
        val p = x.getJSONObject("params")
        val pareil = e.reponse == x.getString("reponse") && e.verif == x.getString("verif") &&
            p.keys().asSequence().all { e.params[it] == p.getString(it) } && e.params.size == p.length()
        if (!pareil) diff.add("${x.getString("type")}#${x.getLong("k")} ${e.params} ${e.reponse} ${e.verif}")
    }
    verifierP(diff.isEmpty(), "${exos.length()} exercices identiques au Python ${diff.take(2)}")
    val rech = vm.getJSONArray("recherches")
    val rd = mutableListOf<String>()
    for (i in 0 until rech.length()) {
        val x = rech.getJSONObject(i)
        Langue.definir(x.getString("langue"))
        val r = Maths.chercher(x.getString("question"))
        val att = if (x.isNull("attendu")) null else x.getString("attendu")
        if (r != att) rd.add("${x.getString("langue")} « ${x.getString("question")} » → $r (Python : $att)")
    }
    Langue.definir("fr")
    verifierP(rd.isEmpty(), "${rech.length()} recherches identiques au Python (même moteur que le lexique) ${rd.take(3)}")
    val pre = vm.getJSONObject("tous_prerequis")
    verifierP(pre.keys().asSequence().all { Maths.tousPrerequis(it) == liste(pre.getJSONArray(it)) }, "graphe des prérequis identique")
    val commandes = Commandes(app, jeu, { dossier })
    val r1 = commandes.executer("maths modulo")?.texte ?: ""
    verifierP(r1.contains("modulo", true) && Maths.etat(jeu).optString("question") == "division", "maths modulo : fiche, exercice, question")
    val r2 = commandes.executer("je ne connais pas")?.texte ?: ""
    verifierP(r2.isNotEmpty() && Maths.etat(jeu).optString("courant") == "division", "« je ne connais pas » tapé tout seul : on descend à la division")
    val rep = Maths.etat(jeu).getJSONObject("exo").getString("reponse")
    commandes.executer("maths ${rep.toInt() + 1}")
    verifierP("division" !in liste(Maths.etat(jeu).optJSONArray("acquis")), "réponse fausse : pas encore allumé")
    val rep2 = Maths.etat(jeu).getJSONObject("exo").getString("reponse")
    commandes.executer("maths $rep2")
    verifierP("division" in liste(Maths.etat(jeu).optJSONArray("acquis")) && Maths.etat(jeu).optString("courant") == "modulo",
        "réponse juste : le pont s'allume, retour au modulo")
    for (code in listOf("en", "ar", "zh", "hi")) {
        Langue.definir(code); jeu.changerLangue(code)
        val m = Maths.lignes(jeu, t("maths.mot.inconnu"))
        verifierP(m.isNotEmpty() && m.none { it.contains("{") }, "$code : « ${t("maths.mot.inconnu")} » répond sans clé brute")
    }
    Langue.definir("fr"); jeu.changerLangue("fr")

    println("3. Les récompenses par monde (vecteurs communs)")
    val vr = JSONObject(File(depot, "donnees/recompenses/vecteurs.json").readText())
    val cas = vr.getJSONArray("cas")
    val rdiff = mutableListOf<String>()
    for (i in 0 until cas.length()) {
        val x = cas.getJSONObject(i)
        val (nGarde, champs) = Recompenses.favoriser(x.getString("valeur"), x.getLong("n0"), x.getString("genre"), liste(x.getJSONArray("types")),
            cible = x.optString("cible").ifEmpty { null })
        val att = x.getJSONObject("attendu")
        if (nGarde != att.getLong("n") || champs.toString() != att.getJSONObject("champs").toString())
            rdiff.add("${x.getString("exploit")} n0=${x.getLong("n0")} → $nGarde (Python ${att.getLong("n")})")
    }
    verifierP(rdiff.isEmpty(), "${cas.length()} faveurs identiques au Python (compteur gardé et tirage exact) ${rdiff.take(2)}")
    val msg = Recompenses.exploit(jeu, "crypte.chaine")
    verifierP(msg != null && Recompenses.exploit(jeu, "crypte.chaine") == null && Recompenses.faveur(jeu)?.optInt("reste") == 3,
        "un exploit : 3 rencontres favorisées, une seule fois")
    val serie = listOf("or", "or", "argent", "or", "diamant", "or", "or", "or").map { Recompenses.serie(jeu, it) }
    verifierP(serie.last() != null && serie.dropLast(1).all { it == null }, "5 médailles d'or de suite : série parfaite")

    println("4. explique : la limite de l'image")
    val ex = Explique.fiche(jeu, "rm")
    verifierP(ex.contains(t("prog.limite", "texte" to t("prog.rm.limite"))), "explique rm montre où l'image s'arrête")

    println("\n$okP réussis, $koP échoués")
    kotlin.system.exitProcess(if (koP > 0) 1 else 0)
}
