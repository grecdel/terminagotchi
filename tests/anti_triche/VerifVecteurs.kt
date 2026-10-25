import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Tirage
import org.json.JSONObject
import java.io.File

/**
 * Anti-triche : l'appli Android donne EXACTEMENT les mêmes tirages que le PC et le serveur.
 * Compilation sur ordinateur (org.json et android.* doivent être fournis à part, ils ne sont pas dans le dépôt) :
 *   kotlinc -cp <imitations org.json + android> app/src/main/java/fr/terminagotchi/(tous les .kt) tests/anti_triche/VerifVecteurs.kt -d verif.jar
 *   kotlin -cp verif.jar:<imitations> VerifVecteursKt app/src/main/assets/bestiaire.json donnees/anti_triche/vecteurs.json
 */
fun canon(v: Any?): String = when (v) {
    is JSONObject -> v.keys().asSequence().sorted().joinToString(",", "{", "}") { "$it:${canon(v.get(it))}" }
    is Number -> Math.round(v.toDouble() * 1000).toString()
    else -> v.toString()
}

fun main(args: Array<String>) {
    Bestiaire.chargerDonnees(File(args[0]).readText()) { null }
    val v = JSONObject(File(args[1]).readText())
    var ko = 0
    val sm = v.getJSONArray("splitmix")
    for (i in 0 until sm.length()) {
        val s = sm.getJSONObject(i)
        val h = Tirage.Hasard(s.getString("valeur"), s.getLong("n"))
        val attendu = s.getJSONArray("sorties")
        for (k in 0 until attendu.length()) {
            val o = java.lang.Long.toUnsignedString(h.suivant())
            if (o != attendu.getString(k)) { ko++; println("✖ splitmix64 ${s.getString("valeur").take(16)} #$k : $o ≠ ${attendu.getString(k)}") }
        }
    }
    val ts = v.getJSONArray("tirages")
    var pareils = 0
    for (i in 0 until ts.length()) {
        val t = ts.getJSONObject(i)
        val attire = if (t.has("attire")) t.getString("attire") else null
        val r = Tirage.tirer(t.getString("valeur"), t.getLong("n"), t.getBoolean("abyssor"), attire)
        val a = canon(t.getJSONObject("attendu")); val o = canon(r.champs)
        if (a == o) pareils++ else { ko++; if (ko < 4) println("✖ ${t.getString("valeur").take(8)}#${t.getLong("n")} :\n  $o\n  $a") }
    }
    println("${if (pareils == ts.length()) "✔" else "✖"} Kotlin : $pareils/${ts.length()} tirages identiques au Python, splitmix64 ${if (ko == 0) "OK" else "KO"}")
    if (ko > 0) System.exit(1)
}
