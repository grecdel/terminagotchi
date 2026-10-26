package fr.terminagotchi

import org.json.JSONArray

/**
 * Expliquer chaque commande et chacune de ses options, en mots d'enfant (le monde à explorer), puis pour les grands
 * (portage de pc/tg/explique.py : mêmes tables, mêmes textes « opt.* », « optg.* », « grand.* », « diff.* »).
 *
 *  - le lexique : sous chaque commande, « Pour les grands : … » et ses options (TerminalActivity.remplirLexique) ;
 *  - les leçons et l'histoire : la première fois qu'une option ou un symbole apparaît dans la commande d'une étape,
 *    la leçon l'explique (« 💡 Le -r veut dire… ») ; à la réussite, la créature le redit dans une bulle, une seule
 *    fois (module « explique », liste « vues »). La version des grands suit, à partir du palier 1 (Mots.kt) ;
 *  - la commande « explique rm » : la fiche complète d'une commande (image, exemple, options, voisines).
 */
object Explique {
    val OPTIONS: Map<String, Map<String, String>> = mapOf(
        "ls" to mapOf("-a" to "all", "-l" to "long", "-R" to "recursif_ls"),
        "cp" to mapOf("-r" to "recursif_cp", "-R" to "recursif_cp"),
        "rm" to mapOf("-r" to "recursif_rm", "-R" to "recursif_rm", "-f" to "force"),
        "mkdir" to mapOf("-p" to "parents"),
        "chmod" to mapOf("444" to "c444", "644" to "c644", "600" to "c600", "755" to "c755", "+x" to "plusx", "+r" to "plusr"),
        "curl" to mapOf("-I" to "info", "-o" to "output"),
        "df" to mapOf("-h" to "human"),
        "free" to mapOf("-h" to "human"),
        "du" to mapOf("-s" to "summary", "-h" to "human"),
        "sort" to mapOf("-n" to "numeric", "-r" to "reverse", "-h" to "human"),
        "find" to mapOf("-name" to "name", "-size" to "size"),
        "git" to mapOf("-m" to "message", "--global" to "global"),
        "grep" to mapOf("-i" to "ignore", "-r" to "recursif_grep", "-n" to "numero", "-l" to "liste", "-c" to "count", "-v" to "inverse"),
        "head" to mapOf("-n" to "nombre", "-#" to "nombre"),
        "tail" to mapOf("-n" to "nombre", "-#" to "nombre"),
        "ping" to mapOf("-c" to "count_ping"),
        "ps" to mapOf("-A" to "all_ps", "aux" to "aux"),
        "tar" to mapOf("-czf" to "tar", "czf" to "tar"),
        "uname" to mapOf("-a" to "all_uname", "-m" to "machine"),
        "uniq" to mapOf("-c" to "count_uniq"),
        "wc" to mapOf("-l" to "lignes", "-w" to "mots", "-c" to "caracteres"),
        "base64" to mapOf("-d" to "decode"),
        "ssh" to mapOf("-V" to "version"),
        "python3" to mapOf("-m" to "module"),
    )
    val SYMBOLES = mapOf(">" to "ecrase", ">>" to "ajoute", "|" to "tuyau", "." to "ici", ".." to "avant", "~" to "chambre", "*" to "etoile")
    val VOISINES = mapOf("rm" to "rm", "rmdir" to "rm", "cp" to "cp_mv", "mv" to "cp_mv", "cat" to "lire", "head" to "lire",
        "tail" to "lire", "less" to "lire", "touch" to "touch_mkdir", "mkdir" to "touch_mkdir", "echo" to "redir", "ls" to "ls",
        "ps" to "ps_kill", "kill" to "ps_kill")

    /** Les options et symboles d'une commande, dans l'ordre : (tel qu'écrit, clé), sans doublon de clé. */
    fun options(ligne: String): List<Pair<String, String>> {
        val out = mutableListOf<Pair<String, String>>()
        val vues = mutableSetOf<String>()
        fun ajouter(montre: String, cle: String?) {
            if (cle != null && vues.add(cle)) out.add(montre to cle)
        }
        for ((k, morceau) in ligne.split("|").withIndex()) {
            if (k > 0) ajouter("|", SYMBOLES["|"])
            val mots = morceau.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            if (mots.isEmpty()) continue
            val table = OPTIONS[Regles.premierMot(mots[0])] ?: emptyMap()
            for (m0 in mots.drop(1)) {
                val m = m0.trim('"', '\'')
                when {
                    m == ">" || m == ">>" -> ajouter(m, SYMBOLES[m])
                    m in table -> ajouter(m, table[m])
                    m.startsWith("-") && m.length > 1 && m.drop(1).all { it.isDigit() } && "-#" in table -> ajouter(m, table["-#"])
                    m.startsWith("-") && !m.startsWith("--") && m.drop(1).all { it.isLetter() } ->
                        for (l in m.drop(1)) ajouter("-$l", table["-$l"])
                    m == "." || m == ".." || m == "~" || m.startsWith("../") || m.startsWith("~/") -> {
                        val c = if (m.startsWith("..")) ".." else if (m.startsWith("~")) "~" else "."
                        ajouter(c, SYMBOLES[c])
                    }
                }
                if ('*' in m && !m.startsWith("-")) ajouter("*", SYMBOLES["*"])
            }
        }
        return out
    }

    fun phrase(montre: String, cle: String) = t("opt.phrase", "opt" to montre, "sens" to t("opt.$cle"))
    fun grand(cle: String) = t("grand.ligne", "texte" to t(cle))

    /** L'explication technique d'une commande : grand.<cmd>, sinon la technique du lexique. */
    fun grandCommande(nom: String, technique: String? = null): String? =
        if (Langue.existe("grand.$nom")) grand("grand.$nom") else technique?.let { t("grand.ligne", "texte" to it) }

    /** L'image (la créature), puis la version des grands à partir du palier 1. */
    fun phrases(jeu: Jeu, montre: String, cle: String): List<String> =
        listOf(phrase(montre, cle)) + if (Mots.palier(jeu) >= 1) listOf(grand("optg.$cle")) else emptyList()

    private fun vues(jeu: Jeu): JSONArray = jeu.module("explique").optJSONArray("vues")
        ?: JSONArray().also { jeu.module("explique").put("vues", it) }

    /** Les options de cette commande que la créature n'a pas encore expliquées. */
    fun nouvelles(jeu: Jeu, cmd: String): List<Pair<String, String>> {
        val v = vues(jeu)
        val deja = (0 until v.length()).map { v.optString(it) }.toSet()
        return options(cmd.split("    ")[0]).filter { it.second !in deja }
    }

    /** Étape réussie : la créature explique (une seule fois) les nouvelles options, puis s'en souvient. */
    fun apresReussite(jeu: Jeu, cmd: String) {
        val nouv = nouvelles(jeu, cmd)
        for ((montre, cle) in nouv) for (x in phrases(jeu, montre, cle)) { jeu.dire(x, 14); jeu.log(x) }
        val v = vues(jeu)
        for ((_, cle) in nouv) v.put(cle)
    }

    /** Les lignes « `-r` : sens » puis « Pour les grands : … » d'une commande (lexique et fiche). */
    fun lignesOptions(cmd: String): List<String> {
        val table = OPTIONS[cmd] ?: return emptyList()
        val out = mutableListOf<String>()
        val vues = mutableSetOf<String>()
        for ((opt, cle) in table) {
            if (!vues.add(cle)) continue
            out.add("`${if (opt == "-#") "-3" else opt}` : " + t("opt.$cle"))
            out.add("   " + grand("optg.$cle"))
        }
        return out
    }

    /** La fiche complète d'une commande : image, pour les grands, exemple, options, voisines. */
    fun fiche(jeu: Jeu, demande: String): String {
        val nom = Regles.premierMot(demande)
        if (nom.isEmpty()) return t("explique.aide", "ex" to "explique rm")
        val m = Regles.LEXIQUE.firstOrNull { it.cmd == nom }
        val opts = lignesOptions(nom)
        val diff = VOISINES[nom]
        if (m == null && opts.isEmpty() && diff == null) return t("explique.inconnue", "cmd" to demande.trim(), "ex" to "explique rm")
        val out = mutableListOf(t("explique.titre", "cmd" to nom))
        if (m != null) out.add("  " + m.image)
        grandCommande(nom, m?.technique)?.let { out.add("  $it") }
        (m?.let { Exemples.lexique(it) } ?: Exemples.LEXIQUE[nom]?.let { Exemples.remplir(it) })?.let {
            out.add("  ↳ " + t("lex.exemple", "ex" to it))
        }
        if (opts.isNotEmpty()) { out.add(""); out.add(t("explique.options")); out.addAll(opts.map { "   $it" }) }
        if (diff != null) { out.add(""); out.add(t("explique.diff")); out.add("   " + t("diff.$diff")) }
        out.add("")
        out.add(t("explique.aide", "ex" to "explique rm"))
        return out.joinToString("\n")
    }
}
