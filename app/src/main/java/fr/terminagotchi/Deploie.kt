package fr.terminagotchi

/**
 * La vue déployée d'une commande (`deploie <commande>`, et toute seule après chaque commande dans l'espace de
 * travail) : la ligne se découpe en blocs colorés qui s'allument un par un (commande, option, argument, chemin,
 * tuyau, redirection, lien). Même découpage que le PC (pc/tg/deploie.py) : vecteurs communs dans
 * donnees/espace/vecteurs.json (tests/jvm/Espace.kt). `deploie` ne lance jamais la commande : les lignes qui passent
 * dans les tuyaux viennent de commandes qui ne font que lire (cat, ls, grep…), lancées sans leurs redirections.
 */
object Deploie {
    val GENRES = listOf("commande", "option", "argument", "chemin", "tuyau", "redirection", "lien")
    val COULEURS = mapOf(
        "commande" to 0xFF3DDC84.toInt(), "option" to 0xFFFF9F43.toInt(), "argument" to 0xFF5FAFFF.toInt(),
        "chemin" to 0xFF4DD0E1.toInt(), "tuyau" to 0xFFB284FF.toInt(), "redirection" to 0xFFFF79C6.toInt(),
        "lien" to 0xFFFFD54F.toInt())
    private val OPERATEURS = listOf("2>>", "2>", "&>", ">>", "||", "&&", ">", "<", "|", ";", "&")
    val REDIRECTIONS = mapOf(">" to "ecrase", ">>" to "ajoute", "<" to "entree", "2>" to "erreurs", "2>>" to "erreurs", "&>" to "tout")
    val LIENS = mapOf("&&" to "et", "||" to "ou", ";" to "puis", "&" to "fond")
    private val MOTIF = setOf("grep", "egrep", "fgrep", "sed", "awk")
    private val TEXTE = setOf("echo", "printf", "dis", "say")
    private val TR = setOf("tr")
    private val VALEUR_PAR_CMD = mapOf(
        "head" to setOf("-n", "-c"), "tail" to setOf("-n", "-c"), "find" to setOf("-name", "-iname", "-size", "-type"),
        "cut" to setOf("-d", "-f", "-c"), "sort" to setOf("-k", "-t"), "git" to setOf("-m"), "ping" to setOf("-c"),
        "grep" to setOf("-e", "-m"), "xargs" to setOf("-n"))
    private val CHEMINS = setOf("cd", "ls", "cat", "mkdir", "touch", "rm", "rmdir", "cp", "mv", "tree", "less", "more",
        "head", "tail", "wc", "nano", "du", "file", "stat", "chmod", "sort", "uniq", "rev", "nl", "tac", "pushd", "dir", "type")
    private val CHMOD = Regex("^([ugoa]*[+=-][rwxX]+|[0-7]{3,4})$")
    private val EXTENSION = Regex("^[^-*\\s][^\\s]*\\.[A-Za-z0-9]{1,5}$")
    val SURES = setOf("cat", "ls", "grep", "egrep", "fgrep", "head", "tail", "wc", "sort", "uniq", "echo", "rev", "tr",
        "cut", "tree", "pwd", "whoami", "date", "find", "nl", "tac", "printf", "basename", "dirname", "seq", "fold",
        "expand", "du", "df", "free", "uname", "id", "hostname")
    private val DANGER = Regex("\\$\\(|`|-delete\\b|-exec\\b|-ok\\b|--output|-fprint")
    const val LIGNES_MAX = 40

    class Bloc(val t: String, var g: String, val i: Int, var seg: Int, var role: String, var cmd: String)
    class Etape(val cmd: String, val debut: Int, var fin: Int, val mots: MutableList<String> = mutableListOf()) {
        val texte: String get() = mots.joinToString(" ")
    }
    /** redir : (opérateur, fichier, indice du fichier, indice de l'opérateur) */
    class Chaine(val etapes: MutableList<Etape> = mutableListOf(), var redir: Redir? = null, val debut: Int, var fin: Int)
    class Redir(val op: String, val fichier: String, val k: Int, val kOp: Int)

    /** Les mots et les opérateurs d'une ligne : (texte, est un opérateur). Les guillemets restent dans le texte. */
    fun mots(ligne: String): List<Pair<String, Boolean>> {
        val out = mutableListOf<Pair<String, Boolean>>()
        val cour = StringBuilder()
        var q: Char? = null
        var i = 0
        val n = ligne.length
        while (i < n) {
            val c = ligne[i]
            if (q != null) {
                cour.append(c); if (c == q) q = null; i++; continue
            }
            if (c == '"' || c == '\'') { q = c; cour.append(c); i++; continue }
            if (c == '\\' && i + 1 < n) { cour.append(ligne, i, i + 2); i += 2; continue }
            if (c.isWhitespace()) {
                if (cour.isNotEmpty()) { out.add(cour.toString() to false); cour.setLength(0) }
                i++; continue
            }
            var op: String? = null
            for (o in OPERATEURS) {
                if (ligne.startsWith(o, i)) {
                    if (o[0] == '2' && cour.isNotEmpty()) continue
                    op = o; break
                }
            }
            if (op != null) {
                if (cour.isNotEmpty()) { out.add(cour.toString() to false); cour.setLength(0) }
                out.add(op to true)
                i += op.length
                continue
            }
            cour.append(c); i++
        }
        if (cour.isNotEmpty()) out.add(cour.toString() to false)
        return out
    }

    fun nu(m: String): String =
        if (m.length >= 2 && m[0] == m[m.length - 1] && (m[0] == '"' || m[0] == '\'')) m.substring(1, m.length - 1) else m

    fun estChemin(mot: String, existe: ((String) -> Boolean)? = null): Boolean {
        val m = nu(mot)
        if (m.isEmpty()) return false
        if (m in setOf(".", "..", "~", "/")) return true
        if ('/' in m || m.startsWith("~")) return true
        if (m.startsWith(".") && m.length > 1 && !m.startsWith("...")) return true
        if ('*' in m || '?' in m) return true
        if (EXTENSION.matches(m)) return true
        return existe?.invoke(m) == true
    }

    private fun basename(s: String) = s.trimEnd('/').substringAfterLast('/').ifEmpty { s }

    fun blocs(ligne: String, existe: ((String) -> Boolean)? = null): List<Bloc> {
        val out = mutableListOf<Bloc>()
        var debut = true
        var cmd = ""
        var seg = -1
        var nargs = 0
        var cible = false
        var valeur = false
        for ((texte, op) in mots(ligne)) {
            val b = Bloc(texte, "argument", out.size + 1, maxOf(0, seg), "", cmd)
            if (op) {
                when {
                    texte == "|" -> { b.g = "tuyau"; debut = true }
                    texte in REDIRECTIONS -> { b.g = "redirection"; cible = true }
                    else -> { b.g = "lien"; debut = true }
                }
                valeur = false
                out.add(b)
                continue
            }
            if (cible) {
                b.g = "chemin"; b.role = "cible"; cible = false
            } else if (debut) {
                if (Regex("^[A-Za-z_]\\w*=").containsMatchIn(texte)) b.role = "variable"
                else {
                    seg += 1
                    cmd = basename(nu(texte)).lowercase()
                    b.g = "commande"; b.seg = seg; b.cmd = cmd
                    debut = false
                    nargs = 0
                }
            } else if (valeur) {
                b.role = if (cmd != "find" && cmd != "grep") "valeur" else "motif"
                valeur = false
            } else if ((texte.startsWith("-") && texte.length > 1) || (cmd == "chmod" && CHMOD.matches(texte))) {
                b.g = "option"
                if (texte in (VALEUR_PAR_CMD[cmd] ?: emptySet())) valeur = true
            } else {
                when {
                    cmd in MOTIF && nargs == 0 -> b.role = "motif"
                    cmd in TR -> b.role = "motif"
                    cmd in TEXTE -> b.role = "texte"
                    cmd in CHEMINS || estChemin(texte, existe) -> b.g = "chemin"
                }
                nargs += 1
            }
            b.seg = maxOf(0, seg)
            b.cmd = cmd
            out.add(b)
        }
        return out
    }

    fun composee(ligne: String) = blocs(ligne).any { it.g == "tuyau" || it.g == "redirection" || it.g == "lien" }

    fun chaines(bl: List<Bloc>): List<Chaine> {
        val out = mutableListOf<Chaine>()
        var cour: Chaine? = null
        var etape: Etape? = null
        var attente: Pair<String, Int>? = null
        for ((k, b) in bl.withIndex()) {
            if (cour == null) cour = Chaine(debut = k, fin = k)
            if (b.g == "lien") {
                if (cour.etapes.isNotEmpty()) out.add(cour)
                cour = null; etape = null
                continue
            }
            cour.fin = k
            if (b.g == "tuyau") { etape = null; continue }
            if (b.g == "redirection") { attente = b.t to k; continue }
            if (attente != null) {
                if (attente.first in setOf(">", ">>", "&>")) cour.redir = Redir(attente.first, nu(b.t), k, attente.second)
                attente = null
                continue
            }
            if (etape == null) {
                etape = Etape(b.cmd, k, k)
                cour.etapes.add(etape)
            }
            etape.fin = k
            etape.mots.add(b.t)
        }
        if (cour != null && cour.etapes.isNotEmpty()) out.add(cour)
        return out
    }

    fun sure(etapes: List<Etape>): Boolean = etapes.all { e ->
        e.cmd in SURES && !DANGER.containsMatchIn(e.texte) &&
            !((e.cmd == "sort" || e.cmd == "uniq") && Regex("(^|\\s)-o\\b").containsMatchIn(e.texte))
    }

    /** Ce qui passe dans chaque tuyau : par chaîne, la sortie après chaque étape (null si on ne peut pas le savoir
     *  sans danger). lancer(texte) lance une commande sûre et rend sa sortie. */
    fun flux(ligne: String, lancer: (String) -> String, existe: ((String) -> Boolean)? = null): List<List<List<String>>?> =
        chaines(blocs(ligne, existe)).map { c ->
            if (!sure(c.etapes)) null
            else c.etapes.indices.map { k ->
                val texte = c.etapes.subList(0, k + 1).joinToString(" | ") { it.texte }
                val s = try { lancer(texte) } catch (e: Exception) { "" }
                s.split("\n").filter { it.isNotEmpty() }.take(LIGNES_MAX)
            }
        }

    // ------------------------------------------------------------ le messager des commandes réseau (le Port)
    val RESEAU = setOf("ping", "curl", "wget", "ssh", "scp", "nslookup", "host", "dig", "tracepath", "traceroute", "tracert",
        "getent", "port", "telnet", "nc")
    private val PORT_MESSAGER = setOf("messager", "guide")
    private val VALEUR_RESEAU = setOf("-c", "-W", "-w", "-i", "-o", "-p", "-l", "-d", "-H", "-X", "-m", "-A", "-b", "--cacert",
        "--output", "--connect-timeout", "-t", "-q")
    private val BIOMES = setOf("racine", "feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")

    class Messager(val seg: Int, val cmd: String, val dest: String, val local: Boolean)

    private fun hote(mot: String): String {
        val m = Regex("^[a-z]+://([^/]+)").find(mot)
        return (m?.groupValues?.get(1) ?: mot.substringBefore('/')).substringAfterLast('@')
    }

    /** La destination reste dans l'ordinateur (localhost, 127.x, ::1, une machine du Terminaworld). */
    fun local(dest: String): Boolean {
        var h = dest.lowercase()
        h = if (h.startsWith("[")) h.substring(1).substringBefore(']') else if (h.count { it == ':' } == 1) h.substringBefore(':') else h
        return h == "localhost" || h == "::1" || h == "camp" || h.startsWith("127.") || h.endsWith(".terminaworld") ||
            h.endsWith(".localhost") || h in BIOMES
    }

    /** Les messagers d'une ligne (même spécification que deploie.messager sur PC, vecteurs donnees/port/vecteurs.json). */
    fun messager(ligne: String): List<Messager> {
        val out = mutableListOf<Messager>()
        val bl = blocs(ligne)
        for (c in chaines(bl)) for (e in c.etapes) {
            val m = mots(e.texte).map { it.first }
            if (e.cmd !in RESEAU || m.size < 2) continue
            val args = m.drop(1)
            val dest: String
            if (e.cmd == "port") {
                if (args[0].lowercase() !in PORT_MESSAGER || args.size < 2) continue
                val d = if (args[0].lowercase() == "guide") args.last() else args[1]
                dest = if (d == "camp" || d == "localhost" || '.' in d) d else "$d.terminaworld"
            } else {
                val libres = mutableListOf<String>()
                var saute = false
                for (x in args) {
                    if (saute) { saute = false; continue }
                    if (x.startsWith("-")) { saute = x in VALEUR_RESEAU; continue }
                    libres.add(nu(x))
                }
                if (e.cmd == "getent" && libres.isNotEmpty() && libres[0] in setOf("hosts", "ahosts")) libres.removeAt(0)
                if (libres.isEmpty()) continue
                dest = hote(libres[0])
            }
            val seg = bl.firstOrNull { it.g == "commande" && it.i - 1 == e.debut }?.seg ?: 0
            out.add(Messager(seg, e.cmd, dest, local(dest)))
        }
        return out
    }

    // ------------------------------------------------------------ les cadenas qui s'allument (la Citadelle)
    private val OPTIONS_CHMOD = setOf("-R", "-v", "-c", "-f", "--recursive", "--verbose", "--changes", "--silent", "--quiet")
    private val MODE_CHMOD = Regex("[0-7]{1,4}|[ugoa]*(?:[-+=][rwx]*)+(?:,[ugoa]*(?:[-+=][rwx]*)+)*")

    class Droits(val seg: Int, val cmd: String, val mode: String, val fichier: String, val avant: String, val apres: String,
                 val octal: String, val suppose: Boolean)

    /** Les cadenas d'une ligne (même spécification que deploie.droits sur PC, vecteurs donnees/citadelle/vecteurs.json) :
     *  chaque `chmod MODE fichier` (le mode du fichier n'est pas lu : on suppose rw-r--r--) et `umask NNN`. */
    fun droits(ligne: String): List<Droits> {
        val out = mutableListOf<Droits>()
        val bl = blocs(ligne)
        for (c in chaines(bl)) for (e in c.etapes) {
            val m = mots(e.texte).map { it.first.trimEnd(')') }
            val cmd = e.cmd.trimStart('(')
            val seg = bl.firstOrNull { it.g == "commande" && it.i - 1 == e.debut }?.seg ?: 0
            if (cmd == "chmod") {
                val args = m.drop(1).filter { it !in OPTIONS_CHMOD }
                if (args.size < 2 || !MODE_CHMOD.matches(args[0])) continue
                val base = "644".toInt(8)
                val apres = Citadelle.chmodMode(args[0], base) ?: continue
                out.add(Droits(seg, "chmod", args[0], nu(args[1]), Citadelle.modeTexte(base), Citadelle.modeTexte(apres), "%03o".format(apres), true))
            } else if (cmd == "umask" && m.size >= 2 && Regex("[0-7]{1,4}").matches(m[1])) {
                val apres = Citadelle.umaskMode(m[1].toInt(8))
                out.add(Droits(seg, "umask", m[1], "", "rw-rw-rw-", Citadelle.modeTexte(apres), "%03o".format(apres), false))
            }
        }
        return out
    }

    // ------------------------------------------------------------ les mots pour le dire
    fun nomGenre(g: String) = t("dep.genre.$g")

    fun phraseCommande(cmd: String) = if (Langue.existe("dep.c.$cmd")) t("dep.c.$cmd") else t("dep.c.autre")

    private fun option(b: Bloc): String? {
        val table = Explique.OPTIONS[b.cmd] ?: emptyMap()
        return table[b.t] ?: if (b.t.length > 2 && b.t[0] == '-' && b.t[1] != '-') table["-" + b.t[1]] else null
    }

    private fun voisins(b: Bloc, bl: List<Bloc>): Pair<String, String> {
        val k = b.i - 1
        val avant = bl.subList(0, k).lastOrNull { it.g == "commande" }?.cmd ?: "?"
        val apres = bl.subList(k + 1, bl.size).firstOrNull { it.g == "commande" }?.cmd ?: "?"
        return avant to apres
    }

    fun courte(b: Bloc, bl: List<Bloc>): String = when (b.g) {
        "commande" -> phraseCommande(b.cmd)
        "option" -> option(b)?.takeIf { Langue.existe("dep.o.$it") }?.let { t("dep.o.$it") } ?: t("dep.o.autre", "cmd" to b.cmd)
        "argument" -> t("dep.a." + b.role.ifEmpty { "simple" })
        "chemin" -> if (b.role == "cible") t("dep.ch.cible") else t("dep.ch.simple")
        "tuyau" -> voisins(b, bl).let { t("dep.tuyau", "a" to it.first, "b" to it.second) }
        "redirection" -> t("dep.r." + (REDIRECTIONS[b.t] ?: "ecrase"), "a" to voisins(b, bl).first,
            "f" to (bl.getOrNull(b.i)?.t?.let { nu(it) } ?: "?"))
        else -> voisins(b, bl).let { t("dep.l." + (LIENS[b.t] ?: "puis"), "a" to it.first, "b" to it.second) }
    }

    fun longue(b: Bloc, bl: List<Bloc>) = t("dep.phrase", "mot" to b.t, "genre" to nomGenre(b.g), "texte" to courte(b, bl))

    /** Un chemin dans le terrain : (chemin relatif, lieu) ou null. dossier : le dossier courant (vrai chemin). */
    fun lieu(jeu: Jeu, b: Bloc, dossier: java.io.File): Pair<String, String>? {
        val m = nu(b.t).let { if (it.startsWith("~")) jeu.home.path + it.substring(1) else it }
        val f = if (m.startsWith("/")) java.io.File(m) else java.io.File(dossier, m)
        val r = try { Maison.rel(jeu, f.canonicalPath) } catch (e: Exception) { null } ?: return null
        val piece = r.split("/")[0]
        return r to (if (piece.isNotEmpty()) piece else "")
    }

    private const val RONDS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

    fun rond(i: Int) = if (i in 1..RONDS.length) RONDS[i - 1].toString() else "$i"

    /** Une ligne : ①cat ②lianes.txt ③| ④grep ⑤-i ⑥gland (le terminal simple, après une étape de leçon). */
    fun compacte(bl: List<Bloc>) = bl.joinToString(" ") { rond(it.i) + it.t }

    // ------------------------------------------------------------ l'état de la vue qui se déploie
    /** Une vue déployée en cours : la ligne, ses blocs, ses chaînes, ce qui passe dans les tuyaux, le bloc allumé. */
    class Vue(val ligne: String, val blocs: List<Bloc>, val chaines: List<Chaine>, var sorties: List<List<List<String>>?>?,
              var auto: Boolean = true) {
        var actif = 1
        var t = 0.0
        var phase = 0.0
        var lieu: Pair<String, String>? = null
        /** les messagers des commandes réseau (le messager part vers sa destination et revient) */
        val messagers: List<Messager> = try { messager(ligne) } catch (e: Exception) { emptyList() }
        fun messagerDe(b: Bloc): Messager? = if (b.g == "commande") messagers.firstOrNull { it.seg == b.seg } else null
        /** les cadenas d'un chmod / umask (la Citadelle) : ils s'allument ou s'éteignent */
        val cadenas: List<Droits> = try { droits(ligne) } catch (e: Exception) { emptyList() }
        fun droitsDe(b: Bloc): Droits? = if (b.g == "commande") cadenas.firstOrNull { it.seg == b.seg } else null

        fun avancer(dt: Double) {
            t += dt
            val b = blocs[actif - 1]
            val reseau = messagerDe(b) != null || droitsDe(b) != null
            val duree = if (b.g == "tuyau" || b.g == "redirection" || reseau) 2.4 else 1.2
            phase = if (b.g in setOf("tuyau", "redirection", "chemin") || reseau) t / duree else minOf(1.0, t / duree)
            if (auto && t >= duree && actif < blocs.size) { actif += 1; t = 0.0 }
        }

        fun suivant() {
            actif = if (actif < blocs.size) actif + 1 else 1
            t = 0.0
        }
    }

    fun vue(ligne: String, existe: ((String) -> Boolean)? = null, auto: Boolean = true): Vue? {
        val bl = blocs(ligne, existe)
        if (bl.isEmpty()) return null
        return Vue(ligne, bl, chaines(bl), null, auto)
    }
}
