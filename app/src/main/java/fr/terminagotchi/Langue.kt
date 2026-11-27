package fr.terminagotchi

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.util.Locale

/**
 * Les langues du jeu (mêmes catalogues que le PC : assets/i18n/<code>.json, générés par donnees/generer_langues.py).
 * Le français est la langue d'origine ; un texte sans traduction reste en français.
 */
object Langue {
    val LANGUES = linkedMapOf("fr" to "Français", "en" to "English")
    var code = "fr"
        private set
    private var textes: Map<String, String> = emptyMap()
    private var motifs: List<Pair<Regex, String>> = emptyList()
    private var ctx: Context? = null

    private fun fichier(c: Context) = File(c.filesDir, "langue")

    /** Au démarrage : la langue choisie, sinon celle du téléphone pour une nouvelle partie, sinon le français. */
    fun init(c: Context, partieExistante: Boolean) {
        if (ctx != null) return
        ctx = c.applicationContext
        val choisie = try { fichier(c).readText().trim() } catch (e: Exception) { "" }
        val defaut = if (partieExistante) "fr" else Locale.getDefault().language
        charger(choisie.ifEmpty { defaut })
    }

    private fun charger(c: String) {
        code = if (c in LANGUES) c else "fr"
        textes = emptyMap()
        motifs = emptyList()
        if (code == "fr") return
        try {
            val o = JSONObject(ctx!!.assets.open("i18n/$code.json").bufferedReader().use { it.readText() })
            val t = o.getJSONObject("textes")
            textes = t.keys().asSequence().associateWith { t.getString(it) }
            val m = o.getJSONArray("motifs")
            motifs = (0 until m.length()).map { i ->
                val p = m.getJSONArray(i)
                Regex(p.getString(0)) to p.getString(1).replace(Regex("\\\\(\\d)"), "\\$$1")
            }
        } catch (e: Exception) {
            // catalogue absent ou illisible : on reste en français
        }
    }

    fun choisir(c: String): Boolean {
        val k = c.trim().lowercase()
        if (k !in LANGUES) return false
        ctx?.let { fichier(it).writeText(k) }
        charger(k)
        return true
    }

    /** Traduit un texte français (ou le laisse tel quel). */
    fun tr(texte: String): String {
        if (code == "fr" || texte.isEmpty()) return texte
        textes[texte]?.let { return it }
        var t = texte
        for ((re, r) in motifs) t = re.replace(t, r)
        return t
    }
}

/** Raccourci : « texte ».tr() */
fun String.tr(): String = Langue.tr(this)
