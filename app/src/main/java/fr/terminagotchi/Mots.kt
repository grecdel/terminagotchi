package fr.terminagotchi

/**
 * Les mots du jeu (même règles que pc/tg/mots.py) :
 *
 * 1) accorder("Dressage de {nom}", "nom" to "Inodin") → « Dressage d'Inodin ».
 *    Élision devant une voyelle pour : de, que, le, la, je, me, te, se, ne, ce, lorsque, puisque, jusque.
 *    Le genre des espèces n'est pas connu : les phrases modèles restent neutres
 *    (« Un monstre sauvage : {nom} ! », « {nom} rejoint ta troupe »). Chaque phrase est entière : prête à traduire.
 *
 * 2) terme("ram", palier) : le jargon arrive progressivement, dans la langue choisie (clés « terme.xxx »).
 *    palier 0 = l'image seule (« la mémoire du monde »), 1 = l'image et le vrai mot
 *    (« la mémoire du monde (la RAM) »), 2 = le vrai mot seul (« la RAM »).
 *    palier(niveau, lecons) : niveau < 7 → 0, 7 à 11 → 1, 12 et plus → 2 ;
 *    ou, si c'est plus haut, 8 leçons terminées → 1, 14 → 2.
 */
object Mots {
    private const val VOYELLES = "aàâäeéèêëiîïoôöuùûüœæ"
    private val MOTIF = Regex("\\b(de|que|le|la|je|me|te|se|ne|ce|lorsque|puisque|jusque) \\{(\\w+)\\}", RegexOption.IGNORE_CASE)
    private val TROU = Regex("\\{(\\w+)\\}")

    fun voyelle(mot: String?): Boolean = !mot.isNullOrEmpty() && mot[0].lowercaseChar() in VOYELLES

    fun accorder(modele: String, vararg valeurs: Pair<String, Any?>): String {
        val v = valeurs.associate { it.first to (it.second?.toString() ?: "") }
        return remplir(modele, v)
    }

    fun remplir(modele: String, v: Map<String, String>): String {
        val elide = MOTIF.replace(modele) { m ->
            val mot = m.groupValues[1]
            val cle = m.groupValues[2]
            if (voyelle(v[cle])) mot.dropLast(1) + "'{" + cle + "}" else m.value
        }
        return TROU.replace(elide) { m -> v[m.groupValues[1]] ?: m.value }
    }

    // ---------------------------------------------------------------- vocabulaire progressif
    val SEUIL_NIVEAU = listOf(7, 12)
    val SEUIL_LECONS = listOf(8, 14)

    /** Les clés du vocabulaire progressif (« terme.<clé> » dans assets/langues/xx.json : 3 paliers). */
    val CLES = listOf("mefiance", "pv", "atk", "def", "vit", "int", "stats", "ram", "processeur", "executable", "ctf",
        "dossier", "dossiers", "fichier", "fichiers", "un_dossier", "un_fichier", "rendre_executable", "processus",
        "disque", "dns", "ip", "arborescence", "terrain", "droits", "script", "cache", "administrateur", "reseau",
        "racine", "village", "camp", "chemin_absolu", "chemin_relatif", "systeme")

    fun palier(niveau: Int, lecons: Int = 0): Int {
        val p = if (niveau >= SEUIL_NIVEAU[1]) 2 else if (niveau >= SEUIL_NIVEAU[0]) 1 else 0
        val q = if (lecons >= SEUIL_LECONS[1]) 2 else if (lecons >= SEUIL_LECONS[0]) 1 else 0
        return maxOf(p, q)
    }

    /** les leçons terminées : celles de l'histoire (Histoire.kt), ou à défaut les compétences des anciennes sauvegardes */
    fun palier(jeu: Jeu): Int {
        val faits = jeu.extra.optJSONObject("histoire")?.optJSONArray("faits")?.length() ?: 0
        return palier(jeu.niveau, maxOf(faits, jeu.skills.size))
    }

    fun terme(cle: String, p: Int = 0, majuscule: Boolean = false): String {
        val v = Langue.brut("terme.$cle")
        val t = (v as? org.json.JSONArray)?.optString(p.coerceIn(0, 2))?.ifEmpty { null } ?: cle
        return if (majuscule) t.replaceFirstChar { it.uppercaseChar() } else t
    }

    /** Tous les termes d'un palier ({ram}, et {Ram} avec majuscule) pour remplir un modèle. */
    fun termes(p: Int): Map<String, String> {
        val m = HashMap<String, String>()
        for (k in CLES) {
            m[k] = terme(k, p)
            m[k.replaceFirstChar { it.uppercaseChar() }] = terme(k, p, true)
        }
        return m
    }

    /** PV/ATK/DEF… → cœurs, force, bouclier… selon le palier. */
    private val CLES_STAT = mapOf("PV" to "pv", "ATK" to "atk", "DEF" to "def", "VIT" to "vit", "INT" to "int")

    fun nomStat(k: String, p: Int): String = CLES_STAT[k]?.let { terme(it, p) } ?: k

    fun texteStats(stats: Map<String, Int>, p: Int): String =
        stats.entries.joinToString("  ") { "${nomStat(it.key, p)} ${it.value}" }
}
