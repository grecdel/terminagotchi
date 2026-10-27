package fr.terminagotchi

import java.io.File

/**
 * Valider une étape sur le RÉSULTAT, pas sur le texte tapé (G-34, portage de pc/tg/verif.py) :
 *  - le code de sortie de la commande (Shell.code) : 0 = réussie ;
 *  - le dossier où chaque morceau de la ligne a été tapé (`cd / && ls`, `cd x; ls` : chaque morceau compte) ;
 *  - le nom de la commande écrit en minuscules (`PWD`, `Ls` n'existent pas) ;
 *  - un tuyau est compris (`cat f | grep mot` = `grep mot f`), les jokers sont remplacés (`cat nid/`*`.txt`).
 * Le lieu attendu par une étape (« 📁 à taper depuis … ») est calculé d'après les chemins relatifs de sa commande.
 */
object Verif {
    /** `ls -l`, `ls -la`, `ls -al`, `ls -l -a`, `ls -lh` : le l peut être n'importe où dans les options */
    const val LS_L = "^(ls(\\s+-\\w+)*\\s+-\\w*l\\w*(\\s|$)|stat\\b)"
    /** `ls -a`, `ls -la`, `ls -l -a`, `ls --all`, `ls -A` */
    const val LS_A = "^(ls(\\s+-\\w+)*\\s+(-\\w*[aA]\\w*|--all|--almost-all)(\\s|$))"
    /** ajouter à la fin d'un fichier : `>> f`, `>> ./f`, `| tee -a f` */
    fun ajoute(nom: String) = "(>>\\s*|\\btee\\s+(-\\w+\\s+)*-\\w*a\\w*\\s+)(\\S*/)?$nom"

    class Morceau(val texte: String, val avant: File, val apres: File, val code: Int?)

    /** Coupe sur les séparateurs (hors guillemets) : [(morceau, séparateur qui suit)]. */
    fun couper(texte: String, seps: List<String>): List<Pair<String, String?>> {
        val out = mutableListOf<Pair<String, String?>>()
        val cur = StringBuilder()
        var q: Char? = null
        var i = 0
        while (i < texte.length) {
            val ch = texte[i]
            if (q != null) { cur.append(ch); if (ch == q) q = null; i++; continue }
            if (ch == '\'' || ch == '"') { q = ch; cur.append(ch); i++; continue }
            val pris = seps.firstOrNull { texte.startsWith(it, i) }
            if (pris != null && !(pris == "|" && texte.startsWith("||", i))) {
                out.add(cur.toString().trim() to pris); cur.clear(); i += pris.length; continue
            }
            cur.append(ch); i++
        }
        if (cur.isNotBlank()) out.add(cur.toString().trim() to null)
        return out
    }

    /** Les mots d'un morceau : (mot sans guillemets, cité). */
    fun mots(texte: String): List<Pair<String, Boolean>> {
        val out = mutableListOf<Pair<String, Boolean>>()
        val cur = StringBuilder()
        var cite = false; var vide = true; var q: Char? = null
        for (ch in texte) {
            if (q != null) { if (ch == q) q = null else cur.append(ch); continue }
            if (ch == '\'' || ch == '"') { q = ch; cite = true; vide = false; continue }
            if (ch.isWhitespace()) { if (!vide) out.add(cur.toString() to cite); cur.clear(); cite = false; vide = true; continue }
            cur.append(ch); vide = false
        }
        if (!vide) out.add(cur.toString() to cite)
        return out
    }

    fun premier(texte: String): String = mots(texte).firstOrNull()?.first ?: ""

    /** Le fichier désigné par un mot tapé depuis cwd (~/… = le camp). Un chemin absolu (le Terminaworld) : null. */
    fun fichier(jeu: Jeu, mot: String, cwd: File): File? = when {
        mot == "~" -> jeu.home
        mot.startsWith("~/") -> File(jeu.home, mot.substring(2))
        mot.startsWith("/") -> null
        else -> File(cwd, mot)
    }

    private val CD = Regex("^(cd|pushd)(?:\\s+(.*))?$")

    /** Les morceaux d'une ligne, avec le dossier de chacun (les « cd » rejoués) et leur code de sortie. */
    fun morceaux(jeu: Jeu, ligne: String, avant: File, apres: File, code: Int?): List<Morceau> {
        val parts = couper(ligne.trim(), listOf("&&", ";"))
        val tousOk = code == 0 && parts.all { it.second == "&&" || it.second == null }
        var cur = avant
        val out = mutableListOf<Morceau>()
        parts.forEachIndexed { k, (txt, _) ->
            val a = cur
            val m = CD.find(txt)
            if (m != null) {
                val arg = (m.groupValues[2]).trim().trim('\'', '"')
                cur = when {
                    k == parts.size - 1 -> apres
                    arg.isEmpty() || arg == "~" -> jeu.home
                    else -> fichier(jeu, arg, cur)?.let { f -> try { f.canonicalFile } catch (e: Exception) { f } }
                        ?.takeIf { it.isDirectory } ?: cur
                }
            }
            out.add(Morceau(txt, a, if (k == parts.size - 1) apres else cur, if (k == parts.size - 1 || tousOk) code else null))
        }
        return out
    }

    private val JOKER = Regex("[*?\\[]")

    private fun glob(motif: String): Regex =
        Regex(motif.map { c -> when (c) { '*' -> ".*"; '?' -> "."; else -> Regex.escape(c.toString()) } }.joinToString(""))

    /** Remplace les jokers non cités par les noms qu'ils désignent (comme le shell). */
    fun developper(jeu: Jeu, texte: String, cwd: File): String = mots(texte).joinToString(" ") { (m, cite) ->
        if (cite || !JOKER.containsMatchIn(m) || m.startsWith("-")) m
        else {
            val tete = m.substringBeforeLast('/', "")
            val nom = m.substringAfterLast('/')
            val d = if (tete.isEmpty()) cwd else fichier(jeu, tete, cwd)
            val r = try { glob(nom) } catch (e: Exception) { null }
            val trouves = d?.list()?.filter { r != null && r.matches(it) && (nom.startsWith(".") || !it.startsWith(".")) }?.sorted()
            if (trouves.isNullOrEmpty()) m else trouves.joinToString(" ") { if (tete.isEmpty()) it else "$tete/$it" }
        }
    }

    /** `PWD`, `Ls` : un nom de commande avec des majuscules n'existe pas. */
    fun casseOk(mot: String) = mot.isEmpty() || mot == mot.lowercase()

    /** Le texte ressemble à la commande de l'étape (sur la ligne entière ou sur une partie d'un tuyau). */
    fun motifOk(jeu: Jeu, e: Etape, texte: String, cwd: File): Boolean {
        val re = e.re ?: return false
        val dev = developper(jeu, texte, cwd)
        val tuyau = couper(dev, listOf("|")).map { it.first }
        val parties = mutableListOf(texte, dev)
        parties += tuyau
        parties += couper(texte, listOf("|")).map { it.first }
        if (tuyau.size > 1) {
            val fichiers = mots(tuyau[0]).drop(1).map { it.first }.filter { !it.startsWith("-") }
            parties += tuyau.drop(1).map { it + " " + fichiers.joinToString(" ") }
        }
        return parties.any { p -> re.containsMatchIn(p.trim()) && couper(p, listOf("|")).all { casseOk(premier(it.first)) } }
    }

    private val LIT = setOf("cat", "less", "more", "head", "tail", "wc", "ls", "stat", "du", "file", "rev", "sort", "uniq",
        "grep", "chmod", "rm", "rmdir", "cp", "mv", "sh", "source", ".", "find", "nl", "od")
    private val CREE = setOf("mkdir", "touch", "tee")
    private val AVEC_VALEUR = mapOf("head" to setOf("-n", "-c"), "tail" to setOf("-n", "-c"), "grep" to setOf("-e", "-m"))
    private val REDIR = Regex("(?<![<\\d&])(\\d?>>?)\\s*([^\\s|;&<>]+)")

    /** Les arguments « chemins » : (à lire, à créer). */
    private fun arguments(cmd: String, args: List<Pair<String, Boolean>>): Pair<List<Pair<String, Boolean>>, List<Pair<String, Boolean>>> {
        val vals = AVEC_VALEUR[cmd] ?: emptySet()
        var libres = mutableListOf<Pair<String, Boolean>>()
        var saute = false
        for ((m, c) in args) {
            if (saute) { saute = false; continue }
            if (m.startsWith("-") && m.length > 1) { if (m in vals) saute = true; if (cmd == "find") break; continue }
            libres.add(m to c)
        }
        if (cmd == "grep" && args.none { it.first == "-e" }) libres = libres.drop(1).toMutableList()
        if (cmd == "chmod") libres = libres.drop(1).toMutableList()
        if (cmd == "find") libres = libres.take(1).toMutableList()
        if ((cmd == "cp" || cmd == "mv") && libres.size >= 2) return libres.dropLast(1) to emptyList()
        if (cmd in CREE) return emptyList<Pair<String, Boolean>>() to libres
        if (cmd in LIT) return libres to emptyList()
        return emptyList<Pair<String, Boolean>>() to emptyList()
    }

    /** Les chemins tapés qui n'existent pas depuis cwd (ou dont le dossier parent manque, pour ce qui est créé). */
    fun cheminsManquants(jeu: Jeu, texte: String, cwd: File): List<String> {
        val manque = mutableListOf<String>()
        for ((partie, _) in couper(texte, listOf("|"))) {
            val sans = REDIR.replace(partie, " ").replace(Regex("<\\s*"), " ")
            val ms = mots(sans)
            if (ms.isEmpty()) continue
            val cmd = ms[0].first.lowercase()
            var (lire, creer) = arguments(cmd, ms.drop(1))
            if (cmd == "mkdir" && ms.any { it.first == "-p" }) creer = emptyList()
            for ((m, c) in lire) {
                if ('$' in m || (JOKER.containsMatchIn(m) && !c) || m == "-" || m == "." || m == "..") continue
                val f = fichier(jeu, m, cwd) ?: continue
                if (!f.exists()) manque.add(m)
            }
            for ((m, c) in creer) {
                if ('$' in m || (JOKER.containsMatchIn(m) && !c)) continue
                val f = fichier(jeu, m.trimEnd('/'), cwd) ?: continue
                if (f.parentFile?.isDirectory != true) manque.add(m)
            }
        }
        for (r in REDIR.findAll(texte)) {
            val m = r.groupValues[2]
            if (m == "/dev/null" || m.startsWith("&") || '$' in m) continue
            val f = fichier(jeu, m, cwd) ?: continue
            if (f.parentFile?.isDirectory != true) manque.add(m)
        }
        return manque
    }

    /** Le morceau a vraiment marché : son code de sortie (une étape « echoue » veut un refus : le cadenas). */
    fun resultatOk(jeu: Jeu, e: Etape, m: Morceau): Boolean {
        if (e.reseau) return cheminsManquants(jeu, m.texte, m.avant).isEmpty()     // hors ligne : avoir essayé suffit
        if (e.echoue) return if (m.code != null) m.code != 0 else cheminsManquants(jeu, m.texte, m.avant).isEmpty()
        if (m.code != null) return m.code == 0
        return cheminsManquants(jeu, m.texte, m.avant).isEmpty()
    }

    // ---------------------------------------------------------------- le lieu attendu par une étape
    private fun cheminsCommande(cmd: String): Pair<List<String>, List<String>> {
        val lire = mutableListOf<String>(); val creer = mutableListOf<String>()
        for ((partie, _) in couper(cmd, listOf("|", "&&", ";"))) {
            val ms = mots(REDIR.replace(partie, " "))
            if (ms.isEmpty()) continue
            val (l, c) = arguments(ms[0].first.lowercase(), ms.drop(1))
            lire += l.filter { !(JOKER.containsMatchIn(it.first) && !it.second) }.map { it.first }
            creer += c.map { it.first }
            creer += REDIR.findAll(partie).map { it.groupValues[2] }
        }
        fun garder(m: String) = m.isNotEmpty() && !m.startsWith("/") && !m.startsWith("~") && !m.startsWith("$") &&
            !m.startsWith("-") && m != "." && m != ".." && m != "?"
        return lire.filter(::garder) to creer.filter(::garder)
    }

    /** Le lieu de la zone d'aventure (« » = le carrefour) d'où la commande de l'étape marche, ou null (partout). */
    fun lieuAttendu(jeu: Jeu, e: Etape): String? {
        e.ou?.let { return if (it.startsWith("/")) null else it }
        if (e.ici != null) return null
        val (lire, creer) = cheminsCommande(e.cmd)
        if (lire.isEmpty() && creer.isEmpty()) return null
        if (!jeu.terrain.isDirectory) return null
        val avecDossier = (lire + creer).any { '/' in it }
        val candidats = mutableListOf<String>()
        if (avecDossier) candidats.add("")
        Histoire.chapitreCourant(jeu)?.piece?.let { if (it !in setOf("vestibule", "nid", "jardin")) candidats.add(it) }
        candidats += listOf("", "nid")
        jeu.terrain.listFiles()?.filter { it.isDirectory && !it.name.startsWith(".") }?.map { it.name }?.sorted()?.let { candidats += it }
        for (c in candidats.distinct()) {
            val base = if (c.isEmpty()) jeu.terrain else File(jeu.terrain, c)
            if (lire.all { File(base, it).exists() } && creer.all { File(base, it).parentFile?.isDirectory == true }) {
                if (lire.isNotEmpty() || avecDossier) return c
            }
        }
        return if (avecDossier) "" else null
    }

    fun auBonEndroit(jeu: Jeu, e: Etape, cwd: String?): Boolean {
        val lieu = lieuAttendu(jeu, e) ?: return true
        if (e.ou != null) return Maison.dans(jeu, cwd, lieu)
        return cwd != null && Maison.rel(jeu, cwd) == lieu
    }

    fun cdVers(jeu: Jeu, lieu: String) = "cd ~/${jeu.terrain.name}/$lieu".trimEnd('/')

    /** La commande de l'étape telle qu'on la montre : précédée du « cd » qui y mène si l'enfant n'est pas au bon lieu. */
    fun commandeMontree(jeu: Jeu, e: Etape, cwd: String? = Maison.ici(jeu)): String {
        if (Placement.cache(jeu, e)) return t("sa.cache")          // G-13 : mode « défi sans aide »
        val cmd = Regles.piege(e.cmd)
        return try {
            if (!auBonEndroit(jeu, e, cwd)) t("comp.lecon.puis", "cd" to Regles.piege(cdVers(jeu, lieuAttendu(jeu, e)!!)), "cmd" to cmd)
            else "`$cmd`"
        } catch (x: Exception) { "`$cmd`" }
    }

    // ---------------------------------------------------------------- fautes collées, casse, noms proches
    private val CONNUES = listOf("mkdir", "rmdir", "touch", "chmod", "whoami", "grep", "find", "head", "tail", "echo", "cat",
        "pwd", "cd", "ls", "cp", "mv", "rm", "wc", "du", "df", "ps", "rev")

    /** des commandes courantes (pour reconnaître `PWD`, `Ls`… écrites en majuscules) */
    val MOTS_CONNUS: Set<String> = CONNUES.toSet() + setOf("date", "id", "uname", "hostname", "uptime", "free", "sort", "uniq",
        "ping", "ifconfig", "clear", "history", "sleep", "kill", "jobs", "tree", "less", "more", "stat", "file", "tee")

    /** `cdvestibule` → `cd vestibule`, `ls-a` → `ls -a`, `cd/` → `cd /`, `cd..` → `cd ..` (ou null). */
    fun collee(mot: String): String? {
        if (mot in CONNUES) return null
        for (c in CONNUES.sortedByDescending { it.length }) {
            if (mot.lowercase().startsWith(c) && mot.length > c.length) {
                val reste = mot.substring(c.length)
                if (reste[0] in "-/~." || reste.all { it.isLetterOrDigit() || it == '_' }) return "$c $reste"
            }
        }
        return null
    }

    /** Un nom qui existe là où l'enfant est et qui ressemble au mot tapé : (proche, seule la casse diffère) ou null. */
    fun nomProche(jeu: Jeu, mot: String, cwd: File): Pair<String, Boolean>? {
        val parts = mot.trimEnd('/').split('/').filter { it.isNotEmpty() }
        var base: File = if (mot.startsWith("~")) jeu.home else if (mot.startsWith("/")) return null else cwd
        val tete = mutableListOf<String>()
        val p0 = if (mot.startsWith("~")) parts.drop(1) else parts
        var i = 0
        while (i < p0.size && File(base, p0[i]).exists()) { base = File(base, p0[i]); tete.add(p0[i]); i++ }
        if (i >= p0.size) return null
        val nom = p0[i]
        val reste = p0.drop(i + 1)
        val noms = base.list()?.toList() ?: return null
        fun joindre(n: String) = ((if (mot.startsWith("~")) listOf("~") else emptyList()) + tete + n + reste).joinToString("/")
        noms.firstOrNull { it != nom && it.lowercase() == nom.lowercase() }?.let { return joindre(it) to true }
        Indices.plusProche(nom, noms, 0.75)?.takeIf { it != nom }?.let { return joindre(it) to false }
        return null
    }
}
