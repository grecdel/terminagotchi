package fr.terminagotchi

/**
 * Le cerveau de ta créature : un VRAI petit programme shell (un `case` sur son état), interprété ici ligne par ligne,
 * exactement comme sur PC (pc/tg/cerveau.py) — vecteurs communs dans donnees/espace/vecteurs.json.
 * Ce qui s'affiche est ce qui s'exécute : la ligne en cours se surligne, la machine à états (lue dans les `etat=…`
 * du programme) allume l'état actif et la flèche prise, et la créature prend la pose de son état.
 * L'enfant peut forcer un état : sa branche s'exécute à chaque tour et l'on voit le code réagir.
 */
object Cerveau {
    val ETATS = listOf("content", "faim", "mange", "joue", "dort", "confus")
    val POSES = mapOf("content" to "assis", "faim" to "baille", "mange" to "mange", "joue" to "salut", "dort" to "dort", "confus" to "sursaut")
    val COULEURS = mapOf("content" to 0xFFE9ECF2.toInt(), "faim" to 0xFFFF9F43.toInt(), "mange" to 0xFF3DDC84.toInt(),
        "joue" to 0xFFFF79C6.toInt(), "dort" to 0xFFB284FF.toInt(), "confus" to 0xFFFF5F6D.toInt())
    /** la place des états sur le dessin de la machine (fractions de largeur et de hauteur) */
    val PLACES = mapOf("faim" to (0.27f to 0.17f), "mange" to (0.76f to 0.17f), "content" to (0.5f to 0.5f),
        "dort" to (0.22f to 0.83f), "joue" to (0.8f to 0.83f), "confus" to (0.5f to 0.95f))
    val IDS = listOf("etat", "faim", "jeu", "sommeil", "repas", "content", "mange", "joue", "dort", "confus",
        "commande_tapee", "commande_ratee", "dire")

    val PROGRAMME = listOf(
        "# {commentaire}",
        "case \"\$etat\" in",
        "  content)",
        "    [ \$faim -lt 30 ] && etat=faim",
        "    [ \$sommeil -lt 20 ] && etat=dort",
        "    [ \$jeu -lt 30 ] && etat=joue",
        "    if commande_ratee; then etat=confus",
        "    elif commande_tapee; then etat=mange",
        "    fi ;;",
        "  faim)",
        "    if commande_tapee; then",
        "      etat=mange",
        "    fi ;;",
        "  mange)",
        "    faim=\$((faim + repas))",
        "    [ \$faim -gt 100 ] && faim=100",
        "    etat=content ;;",
        "  joue)",
        "    jeu=\$((jeu + 10))",
        "    etat=content ;;",
        "  dort)",
        "    sommeil=\$((sommeil + 10))",
        "    [ \$sommeil -ge 90 ] && etat=content ;;",
        "  confus)",
        "    dire \"{phrase}\"",
        "    etat=content ;;",
        "esac",
    )

    private val TEST = Regex("^\\[ \\$(\\w+) -(lt|le|gt|ge|eq|ne) (\\d+) \\] && (.*)$")
    private val SI = Regex("^(if|elif) (\\w+); then(?: (.*))?$")
    private val AFF = Regex("^(\\w+)=(\\w+)$")
    private val CALC = Regex("^(\\w+)=\\$\\(\\((\\w+) ([+-]) (\\w+)\\)\\)$")
    private val DIRE = Regex("^dire \"(.*)\"$")
    private val MOTIF = Regex("^(\\w+)\\)$")

    /** Un tour : les lignes exécutées (numéro, « fait » | « vrai » | « faux »), l'état avant et après, la phrase dite. */
    class Trace(val de: String) {
        val lignes = mutableListOf<Pair<Int, String>>()
        var vers = de
        var dit: String? = null
    }

    private fun comparer(a: Int, op: String, b: Int) = when (op) {
        "lt" -> a < b; "le" -> a <= b; "gt" -> a > b; "ge" -> a >= b; "eq" -> a == b; else -> a != b
    }

    private fun valeur(x: String, v: Map<String, Int>) = x.toIntOrNull() ?: (v[x] ?: 0)

    /** Exécute UN tour du programme (le `case` sur etat) : (nouvel état, variables, trace). */
    fun executer(etat0: String, var0: Map<String, Int>, signaux: Map<String, Boolean>,
                 programme: List<String> = PROGRAMME): Triple<String, Map<String, Int>, Trace> {
        val v = LinkedHashMap(var0)
        var etat = etat0
        val tr = Trace(etat0)
        var i = 0
        val n = programme.size
        while (i < n && !programme[i].trim().startsWith("case ")) i++
        if (i >= n) return Triple(etat, v, tr)
        tr.lignes.add(i to "fait")
        i++
        var trouve = false
        while (i < n) {
            val s = programme[i].trim()
            val m = MOTIF.matchEntire(s)
            if (m != null && m.groupValues[1] == etat) { tr.lignes.add(i to "fait"); i++; trouve = true; break }
            if (s == "esac") { tr.lignes.add(i to "fait"); return Triple(etat, v, tr) }
            i++
        }
        if (!trouve) return Triple(etat, v, tr)
        val pile = mutableListOf<BooleanArray>()           // [déjà pris, on exécute]
        fun actif() = pile.all { it[1] }
        fun faire(cmd0: String) {
            var cmd = cmd0.trim()
            if (cmd.endsWith(";;")) cmd = cmd.dropLast(2).trim()
            if (cmd.endsWith("; fi")) cmd = cmd.dropLast(4).trim()
            if (cmd.isEmpty()) return
            AFF.matchEntire(cmd)?.let { a ->
                if (a.groupValues[1] == "etat") etat = a.groupValues[2] else v[a.groupValues[1]] = valeur(a.groupValues[2], v)
                return
            }
            CALC.matchEntire(cmd)?.let { c ->
                val a = valeur(c.groupValues[2], v); val b = valeur(c.groupValues[4], v)
                v[c.groupValues[1]] = if (c.groupValues[3] == "+") a + b else a - b
                return
            }
            DIRE.matchEntire(cmd)?.let { d -> tr.dit = d.groupValues[1] }
        }
        while (i < n) {
            val s = programme[i].trim()
            if (s == "esac" || (MOTIF.matches(s) && pile.isEmpty())) break
            val finBranche = s.endsWith(";;")
            val coeur = if (finBranche) s.dropLast(2).trim() else s
            val m = SI.matchEntire(coeur)
            if (m != null && m.groupValues[1] == "if") {
                if (actif()) {
                    val ok = signaux[m.groupValues[2]] == true
                    tr.lignes.add(i to if (ok) "vrai" else "faux")
                    pile.add(booleanArrayOf(ok, ok))
                    if (ok && m.groupValues[3].isNotEmpty()) faire(m.groupValues[3])
                } else pile.add(booleanArrayOf(true, false))
            } else if (m != null && m.groupValues[1] == "elif") {
                if (pile.isNotEmpty()) {
                    val deja = pile.last()[0]
                    pile.last()[1] = false
                    if (!deja && pile.dropLast(1).all { it[1] }) {
                        val ok = signaux[m.groupValues[2]] == true
                        tr.lignes.add(i to if (ok) "vrai" else "faux")
                        pile[pile.size - 1] = booleanArrayOf(ok, ok)
                        if (ok && m.groupValues[3].isNotEmpty()) faire(m.groupValues[3])
                    }
                }
            } else if (coeur == "fi" || coeur.startsWith("fi ")) {
                if (pile.isNotEmpty()) pile.removeAt(pile.size - 1)
                if (actif()) tr.lignes.add(i to "fait")
            } else if (s.startsWith("#")) {
                // un commentaire
            } else if (actif()) {
                val tst = TEST.matchEntire(coeur)
                if (tst != null) {
                    val ok = comparer(valeur(tst.groupValues[1], v), tst.groupValues[2], tst.groupValues[3].toInt())
                    tr.lignes.add(i to if (ok) "vrai" else "faux")
                    if (ok) faire(tst.groupValues[4])
                } else {
                    tr.lignes.add(i to "fait")
                    faire(coeur)
                }
            }
            if (finBranche && pile.isEmpty()) break
            i++
        }
        tr.vers = etat
        return Triple(etat, v, tr)
    }

    /** Les flèches de la machine, lues dans le programme : chaque `etat=X` dans la branche d'un état. */
    fun transitions(programme: List<String> = PROGRAMME): List<Pair<String, String>> {
        val out = mutableListOf<Pair<String, String>>()
        var cour: String? = null
        for (l in programme) {
            val s = l.trim()
            val m = MOTIF.matchEntire(s)
            if (m != null) { cour = m.groupValues[1]; continue }
            val c = cour ?: continue
            for (x in Regex("\\betat=(\\w+)").findAll(s)) {
                val vers = x.groupValues[1]
                if (vers != c && (c to vers) !in out) out.add(c to vers)
            }
        }
        return out
    }

    fun ident(x: String) = if (Langue.existe("cerv.id.$x")) t("cerv.id.$x") else x

    fun nomEtat(e: String) = ident(e)

    /** Le programme tel qu'il s'affiche : les noms traduits, le commentaire et la phrase dans la langue. */
    fun texteProgramme(nom: String, programme: List<String> = PROGRAMME): List<String> {
        val table = IDS.associateWith { ident(it) }
        val motif = Regex("\\b(" + IDS.sortedByDescending { it.length }.joinToString("|") + ")\\b")
        return programme.map { l ->
            when {
                l.startsWith("# {commentaire}") -> "# " + t("cerv.commentaire", "nom" to nom)
                "{phrase}" in l -> l.replace("dire", table.getValue("dire")).replace("{phrase}", t("cerv.phrase"))
                else -> motif.replace(l) { table.getValue(it.groupValues[1]) }
            }
        }
    }

    /** Un cerveau qui vit : un tour toutes les PAS secondes ; la ligne en cours avance pendant le tour. */
    class Vivant(var etat: String = "content") {
        val PAS = 2.4
        var v: Map<String, Int> = mapOf("faim" to 60, "jeu" to 60, "sommeil" to 80, "repas" to 0)
        var force: String? = null
        var trace = Trace(etat)
        var tTour = -1e9
        var dit: String? = null
        private val vu = HashMap<String, Double>()
        private var total: Int? = null
        private var faimJeu: Double? = null
        private var attente = false

        /** Relit le jeu (satiété, envies, commandes tapées) : renvoie les signaux. */
        fun lireJeu(jeu: Jeu, code: Int?): Map<String, Boolean> {
            val sig = HashMap<String, Boolean>()
            sig["commande_tapee"] = false; sig["commande_ratee"] = false
            if (!jeu.existe) return sig
            val nv = HashMap(v)
            val fj = jeu.faim
            for (cle in listOf("jeu", "sommeil")) {
                val x = try { Envies.valeur(jeu, cle) } catch (e: Exception) { null } ?: continue
                if (cle !in vu || Math.abs(x - vu.getValue(cle)) >= 1) { nv[cle] = Math.round(x).toInt(); vu[cle] = x }
            }
            val tot = jeu.total
            if (total != null && tot > total!!) {
                sig["commande_tapee"] = true
                sig["commande_ratee"] = code != null && code != 0
                val avant = faimJeu ?: fj
                nv["repas"] = maxOf(0, Math.round(fj - avant).toInt())
                nv["faim"] = Math.round(avant).toInt()
                attente = true
            } else if (!attente) nv["faim"] = Math.round(fj).toInt()
            faimJeu = fj
            total = tot
            v = nv
            return sig
        }

        fun tour(signaux: Map<String, Boolean>, maintenant: Double): Trace {
            force?.let { etat = it }
            val de = etat
            val r = executer(etat, v, signaux)
            etat = r.first; v = r.second; trace = r.third
            trace.dit?.let { dit = it }
            if (attente && trace.de != "faim" && trace.vers != "mange") attente = false
            force?.let { etat = it }
            tTour = maintenant
            return trace
        }

        fun ligneEnCours(maintenant: Double): Pair<Int, String>? {
            if (trace.lignes.isEmpty()) return null
            val par = PAS * 0.8 / trace.lignes.size
            val k = minOf(((maintenant - tTour) / maxOf(0.05, par)).toInt(), trace.lignes.size - 1)
            return trace.lignes[maxOf(0, k)]
        }

        fun pose() = POSES[etat] ?: "assis"

        fun forcer(e: String?) {
            force = if (e in ETATS) e else null
            force?.let { etat = it; tTour = -1e9 }
        }
    }
}
