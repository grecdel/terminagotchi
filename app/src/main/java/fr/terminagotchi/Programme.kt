package fr.terminagotchi

import org.json.JSONObject

/**
 * Les fiches notions de la charte de rigueur (docs/programme.md § 7.1), comme pc/tg/programme.py :
 * assets/programme.json (copie de donnees/programme.json). Chaque étape renvoie à ses fiches par le « motif »
 * de chaque notion ; `explique` montre où l'image s'arrête et l'idée fausse à démonter.
 */
object Programme {
    @Volatile var chargeur: (() -> String?)? = null
    private var p: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("programme.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = p ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { p = it }

    fun notions(): JSONObject = donnees().optJSONObject("notions") ?: JSONObject()

    private val motifs = HashMap<String, Regex>()

    /** Les fiches d'une commande, dans l'ordre du fichier. */
    fun notionsDe(cmd: String): List<String> {
        val c = cmd.trim()
        val n = notions()
        return n.keys().asSequence().filter { id ->
            val r = synchronized(motifs) { motifs.getOrPut(id) { Regex(n.getJSONObject(id).getString("motif")) } }
            r.containsMatchIn(c)
        }.toList()
    }

    /** « Où l'image s'arrête » et « idée fausse » de la première fiche d'une commande. */
    fun lignesFiche(cmd: String): List<String> {
        val id = (notionsDe(cmd).firstOrNull() ?: notionsDe(cmd.trim() + " x").firstOrNull()) ?: return emptyList()
        val f = notions().getJSONObject(id)
        val out = mutableListOf(t("prog.limite", "texte" to t(f.getString("limite_image"))))
        val idees = f.optJSONArray("idees_fausses")
        if (idees != null) for (i in 0 until idees.length()) out.add(t("prog.idee", "texte" to t(idees.getString(i))))
        return out
    }
}
