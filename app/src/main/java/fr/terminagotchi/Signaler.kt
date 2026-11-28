package fr.terminagotchi

import java.io.File

/**
 * Signaler un souci (idée 76), comme pc/tg/signaler.py : un rapport qu'un ADULTE relit, puis envoie lui-même.
 *  - `bug` (ou la ligne « 🐞 Signaler ce souci » après une vraie panne du jeu) : d'abord la question des grands
 *    (« Tu es un adulte ? », une multiplication, comme « Tout afficher ») ;
 *  - puis une carte montre TOUT ce qui partirait, avec « Ouvrir la page » (le navigateur ouvre la page GitHub
 *    « nouveau signalement » déjà remplie : rien n'est envoyé tant que l'adulte n'a pas appuyé sur le bouton d'envoi
 *    de la page, avec son compte), « Enregistrer » (un fichier texte, via le « Enregistrer sous » d'Android) ou
 *    « Annuler ». Le jeu n'envoie jamais rien lui-même.
 * Jamais dans le rapport : le nom de la créature, le pseudo, les fichiers, la position, les dossiers de l'appareil.
 * Les morceaux communs (nettoyer, rapport, adresse) ont les mêmes vecteurs que Python : donnees/bug/vecteurs.json.
 */
object Signaler {
    const val PAGE = "https://github.com/grecdel/terminagotchi/issues/new"
    const val FICHIER = "rapport-terminagotchi.txt"
    const val JOURNAL = "erreurs.log"
    private const val TRACE_MAX = 12
    private const val LIGNE_MAX = 160
    private const val TITRE_MAX = 80
    private const val NON_RESERVES = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"

    // ---------------------------------------------------------------- morceaux communs (mêmes vecteurs que Python)
    /** Au plus n caractères (points de code, comme Python), « … » à la fin si on a coupé. */
    fun couper(s: String, n: Int): String {
        val nb = s.codePointCount(0, s.length)
        return if (nb <= n) s else s.substring(0, s.offsetByCodePoints(0, n - 1)) + "…"
    }

    /** Le dossier de l'appareil (→ ~), le nom de la créature et le pseudo (→ …), le nom d'utilisateur (→ ~). */
    fun nettoyer(texte: String, home: String = "", utilisateur: String = "", caches: List<String> = emptyList()): String {
        var r = texte
        if (home.codePointCount(0, home.length) >= 3)
            for (h in listOf(home, home.replace("\\", "/"), home.replace("/", "\\"))) r = r.replace(h, "~")
        for (mot in caches) if (mot.codePointCount(0, mot.length) >= 3) r = r.replace(mot, "…")
        if (utilisateur.codePointCount(0, utilisateur.length) >= 3) r = r.replace(utilisateur, "~")
        return r
    }

    class Champs(val version: String, val appareil: String, val langue: String, val ecran: String,
                 val commande: String, val erreur: String, val trace: List<String>)

    /** (titre, corps) du signalement ; e : les étiquettes déjà traduites (faisais, version… sans, pied). */
    fun rapport(c: Champs, e: Map<String, String>): Pair<String, String> {
        val titre = "[bug] " + couper(c.erreur.ifEmpty { e.getValue("sans") }, TITRE_MAX)
        val lignes = mutableListOf(e.getValue("faisais") + " ", "")
        for ((k, v) in listOf("version" to c.version, "appareil" to c.appareil, "langue" to c.langue, "ecran" to c.ecran,
                "commande" to c.commande, "erreur" to c.erreur))
            if (v.isNotEmpty()) lignes.add(e.getValue(k) + " " + v)
        val trace = c.trace.map { couper(it, LIGNE_MAX) }.takeLast(TRACE_MAX)
        if (trace.isNotEmpty()) { lignes.add(""); lignes.add("```"); lignes.addAll(trace); lignes.add("```") }
        lignes.add(""); lignes.add(e.getValue("pied"))
        return titre to lignes.joinToString("\n")
    }

    /** Encodage d'adresse (UTF-8, tout sauf A-Z a-z 0-9 - . _ ~ en %XX majuscules), comme Python. */
    fun coder(s: String): String {
        val sb = StringBuilder()
        for (b in s.toByteArray(Charsets.UTF_8)) {
            val c = b.toInt() and 0xFF
            if (c < 128 && NON_RESERVES.indexOf(c.toChar()) >= 0) sb.append(c.toChar()) else sb.append("%%%02X".format(c))
        }
        return sb.toString()
    }

    fun adresse(titre: String, corps: String) = "$PAGE?title=${coder(titre)}&body=${coder(corps)}"

    fun etiquettes(): Map<String, String> =
        listOf("faisais", "version", "appareil", "langue", "ecran", "commande", "erreur", "sans", "pied").associateWith { t("bug.l.$it") }

    // ---------------------------------------------------------------- Android : la dernière panne
    /** Une erreur imprévue : rangée dans files/erreurs.log (date, [commande], résumé, trace courte), pour `bug`. */
    fun noter(dossier: File, e: Throwable, commande: String = "") {
        try {
            val f = File(dossier, JOURNAL)
            if (f.length() > 200_000) f.writeText("")
            val date = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.ROOT).format(java.util.Date())
            val cmd = commande.replace("\n", " ").replace("]", ")").take(120)
            f.appendText("$date [$cmd] " + resume(e).joinToString("\n") + "\n\n")
        } catch (x: Exception) {
        }
    }

    /** L'erreur en lignes courtes : « Fichier.kt:212 fonction » pour les cadres du jeu, puis « Type: message ».
     *  Jamais de dossiers (seulement des noms de fichiers du jeu). */
    fun resume(e: Throwable): List<String> {
        val cadres = e.stackTrace.filter { it.className.startsWith("fr.terminagotchi") }.take(TRACE_MAX - 1).reversed()
            .map { "${it.fileName ?: "?"}:${it.lineNumber} ${it.methodName}" }
        val cause = generateSequence(e) { it.cause }.last()
        val type = cause.javaClass.simpleName.ifEmpty { cause.javaClass.name }
        return cadres + listOf(if (cause.message.isNullOrBlank()) type else "$type: ${cause.message!!.lines().first()}")
    }

    /** La dernière panne du journal : (date, commande, erreur, trace), ou null. */
    fun dernierePanne(dossier: File): List<Any>? {
        val texte = try { File(dossier, JOURNAL).readText() } catch (e: Exception) { return null }
        val blocs = texte.split("\n\n").map { it.trim('\n') }.filter { Regex("^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2} ").containsMatchIn(it) }
        val b = blocs.lastOrNull() ?: return null
        val date = b.take(19)
        var reste = b.drop(20)
        var commande = ""
        Regex("^\\[(.*?)\\] ?").find(reste)?.let { m -> commande = m.groupValues[1]; reste = reste.substring(m.range.last + 1) }
        val trace = reste.split("\n").filter { it.isNotBlank() }
        val derniere = trace.lastOrNull() ?: ""
        val endroit = trace.dropLast(1).lastOrNull()?.substringBefore(' ')
        return listOf(date, commande, if (endroit != null) "$derniere ($endroit)" else derniere, trace)
    }

    /** Ce que le rapport contiendrait (rien d'autre). ecran : déjà traduit (« terminal, onglet 2 sur 2 »). */
    fun champs(dossier: File, version: String, appareil: String, ecran: String, home: String, caches: List<String>): Champs {
        val p = dernierePanne(dossier)
        fun n(x: String) = nettoyer(x, home, "", caches)
        @Suppress("UNCHECKED_CAST")
        return Champs("$version · Android", appareil, Langue.courante, ecran, n((p?.get(1) as String?) ?: ""),
            n((p?.get(2) as String?) ?: ""), ((p?.get(3) as List<String>?) ?: emptyList()).map { n(it) })
    }
}
