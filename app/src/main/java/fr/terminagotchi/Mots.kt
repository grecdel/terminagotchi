package fr.terminagotchi

/**
 * Les mots du jeu (même règles que pc/tg/mots.py) :
 *
 * 1) accorder("Dressage de {nom}", "nom" to "Inodin") → « Dressage d'Inodin ».
 *    Élision devant une voyelle pour : de, que, le, la, je, me, te, se, ne, ce, lorsque, puisque, jusque.
 *    Le genre des espèces n'est pas connu : les phrases modèles restent neutres
 *    (« Un monstre sauvage : {nom} ! », « {nom} rejoint ta troupe »). Chaque phrase est entière : prête à traduire.
 *
 * 2) terme("ram", palier) : le jargon arrive progressivement.
 *    palier 0 = l'image seule (« la mémoire de la maison »), 1 = l'image et le vrai mot
 *    (« la mémoire de la maison (la RAM) »), 2 = le vrai mot seul (« la RAM »).
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

    /** clé → (image seule, image + vrai mot, vrai mot seul) */
    val TERMES: Map<String, List<String>> = mapOf(
        "mefiance" to listOf("Peur", "Méfiance (il a peur de toi)", "Méfiance"),
        "pv" to listOf("cœurs", "cœurs (PV)", "PV"),
        "atk" to listOf("force", "force (ATK)", "ATK"),
        "def" to listOf("bouclier", "bouclier (DEF)", "DEF"),
        "vit" to listOf("vitesse", "vitesse (VIT)", "VIT"),
        "int" to listOf("astuce", "astuce (INT)", "INT"),
        "stats" to listOf("forces", "forces (stats)", "stats"),
        "ram" to listOf("la mémoire de la maison", "la mémoire de la maison (la RAM)", "la RAM"),
        "processeur" to listOf("le cerveau de la maison", "le cerveau de la maison (le processeur)", "le processeur"),
        "executable" to listOf("qui sait faire quelque chose", "qui sait faire quelque chose (exécutable)", "exécutable"),
        "ctf" to listOf("la chasse au trésor", "la chasse au trésor (CTF)", "le CTF"),
        "dossier" to listOf("pièce", "pièce (dossier)", "dossier"),
        "dossiers" to listOf("pièces", "pièces (dossiers)", "dossiers"),
        "fichier" to listOf("feuille", "feuille (fichier)", "fichier"),
        "fichiers" to listOf("feuilles", "feuilles (fichiers)", "fichiers"),
        "un_dossier" to listOf("une pièce", "une pièce (un dossier)", "un dossier"),
        "un_fichier" to listOf("une feuille", "une feuille (un fichier)", "un fichier"),
        "rendre_executable" to listOf("autorise-la à cuisiner toute seule",
            "autorise-la à cuisiner toute seule (rends-la exécutable)", "rends-la exécutable"),
        "processus" to listOf("programme réveillé", "programme réveillé (processus)", "processus"),
        "disque" to listOf("les placards", "les placards (le disque)", "le disque"),
        "dns" to listOf("l'annuaire des maisons", "l'annuaire des maisons (DNS)", "le DNS"),
        "ip" to listOf("l'adresse de la maison", "l'adresse de la maison (adresse IP)", "l'adresse IP"),
        "arborescence" to listOf("le plan de la maison", "le plan de la maison (l'arborescence)", "l'arborescence"),
        "terrain" to listOf("ta salle de jeu", "ta salle de jeu (terrain_terminagotchi)", "terrain_terminagotchi"),
    )

    fun palier(niveau: Int, lecons: Int = 0): Int {
        val p = if (niveau >= SEUIL_NIVEAU[1]) 2 else if (niveau >= SEUIL_NIVEAU[0]) 1 else 0
        val q = if (lecons >= SEUIL_LECONS[1]) 2 else if (lecons >= SEUIL_LECONS[0]) 1 else 0
        return maxOf(p, q)
    }

    fun palier(jeu: Jeu): Int = palier(jeu.niveau, jeu.skills.size)

    fun terme(cle: String, p: Int = 0, majuscule: Boolean = false): String {
        val t = TERMES[cle]?.get(p.coerceIn(0, 2)) ?: cle
        return if (majuscule) t.replaceFirstChar { it.uppercaseChar() } else t
    }

    /** Tous les termes d'un palier ({ram}, et {Ram} avec majuscule) pour remplir un modèle. */
    fun termes(p: Int): Map<String, String> {
        val m = HashMap<String, String>()
        for (k in TERMES.keys) {
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
