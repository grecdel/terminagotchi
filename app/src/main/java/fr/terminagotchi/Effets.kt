package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.attribute.PosixFilePermission
import kotlin.math.max
import kotlin.math.min

/**
 * Les commandes qui se voient dans le monde des biomes : la SPÉCIFICATION COMMUNE des effets, même règle que
 * pc/tg/effets.py et site/src/effets.js (vecteurs communs donnees/effets/vecteurs.json, tests/jvm/Monde.kt).
 *   evenements(ligne, avant, apres, code, sortie) → [événement (JSONObject : type, cmd, prio, …)]
 * avant/apres : photo() du terrain juste avant et juste après la commande {cwd, f: {chemin: [genre, taille, date, droits]}}.
 * UN EFFET NE MENT JAMAIS : les fichiers viennent de la comparaison avant/après, jamais du seul texte de la commande ;
 * une commande ratée qui ne change rien : un signe doux (refus : cadenas, rebond, « ? »).
 * Point d'extension (les autres mondes) : Effets.extensions += { ctx -> listOf(...) } (ctx : JSONObject, voir effets.py).
 */
object Effets {
    const val GROUPE = 6
    const val MAX_PHOTO = 800
    const val PROFONDEUR = 6
    const val DITS_MAX = 3
    val NIVEAUX = listOf("tous", "essentiels", "aucun")
    private val IGNORES = setOf(".git", "node_modules", "__pycache__", ".cache", "venv", ".venv", ".gradle", "build")
    private val PS = mapOf("get-location" to "pwd", "gl" to "pwd", "set-location" to "cd", "sl" to "cd", "chdir" to "cd",
        "push-location" to "cd", "pushd" to "cd", "get-childitem" to "ls", "gci" to "ls", "dir" to "ls", "ll" to "ls", "la" to "ls",
        "get-content" to "cat", "gc" to "cat", "type" to "cat", "set-content" to "echo", "sc" to "echo", "add-content" to "echo",
        "ac" to "echo", "out-file" to "tee", "tee-object" to "tee", "copy-item" to "cp", "copy" to "cp", "cpi" to "cp",
        "move-item" to "mv", "move" to "mv", "mi" to "mv", "rename-item" to "mv", "ren" to "mv", "rni" to "mv",
        "remove-item" to "rm", "del" to "rm", "erase" to "rm", "ri" to "rm", "rd" to "rmdir", "new-item" to "touch", "ni" to "touch",
        "md" to "mkdir", "write-output" to "echo", "write-host" to "echo", "write" to "echo", "select-string" to "grep",
        "get-process" to "ps", "gps" to "ps", "stop-process" to "kill", "spps" to "kill", "test-connection" to "ping",
        "invoke-webrequest" to "curl", "iwr" to "curl", "invoke-restmethod" to "curl", "irm" to "curl", "get-filehash" to "sha256sum",
        "sort-object" to "sort", "measure-object" to "wc", "set-acl" to "chmod", "get-acl" to "ls", "compare-object" to "diff",
        "start-sleep" to "sleep")
    private val LIRE = setOf("cat", "head", "tail", "less", "more", "wc", "nl", "bat")
    private val EMPREINTE = setOf("sha256sum", "sha1sum", "md5sum", "base64", "shasum", "b2sum")
    private val RESEAU = setOf("ping", "curl", "wget", "nc", "ssh", "scp", "dig", "nslookup", "host", "traceroute")
    private val PROCESSUS = setOf("ps", "kill", "killall", "pkill", "jobs", "top", "htop", "bg", "fg", "sleep")
    private val CAISSE = setOf("tar", "zip", "unzip", "gzip", "gunzip")
    private val RIEN = setOf("clear", "exit", "alias", "export", "env", "source", ".", "unalias", "set", "history", "reset", "cls")
    private val TUER = setOf("kill", "killall", "pkill")
    private val PRIO = mapOf("jokers" to 3, "dossier+" to 3, "dossier-" to 3, "objet+" to 3, "objet-" to 3, "touche" to 3,
        "deplace" to 3, "renomme" to 3, "copie" to 3, "ecrit" to 3, "droits" to 3, "refus" to 3, "cd" to 3, "pwd" to 3, "ls" to 3,
        "find" to 3, "lire" to 3, "groupe" to 3, "modifie" to 2, "lucioles" to 2, "messager" to 2, "photo" to 2, "empreinte" to 2,
        "tuyau" to 2, "caisse" to 2, "lien" to 2, "taille" to 2, "disque" to 2, "arbre" to 2, "memoire" to 2, "lanternes" to 2,
        "reveil" to 2, "journal" to 2, "etoile" to 2, "album" to 2, "branche" to 2, "fusion" to 2, "rembobine" to 2, "robot" to 2,
        "grimoire" to 2, "loupe" to 2, "filet" to 2, "sablier" to 2, "espion" to 2)
    private val AIDE = setOf("man", "apropos", "whatis", "info")
    private val RX_SC = Regex("^In .+ line [0-9]+:", RegexOption.MULTILINE)
    private val RX_APPEL = Regex("^(?:\\[pid +[0-9]+\\] )?[a-z_0-9]+\\(.*\\)[ \t]+= ", RegexOption.MULTILINE)
    val extensions = mutableListOf<(JSONObject) -> List<JSONObject>>()

    // ------------------------------------------------------------ la photo du terrain
    class Entree(val genre: String, val taille: Long, val date: Long, val droits: Int) {
        override fun equals(other: Any?) = other is Entree && other.genre == genre && other.taille == taille && other.date == date && other.droits == droits
        override fun hashCode() = genre.hashCode() * 31 + droits
    }
    class Photo(val cwd: String?, val f: LinkedHashMap<String, Entree>)

    private fun droitsDe(fi: File): Int = try {
        val p = Files.getPosixFilePermissions(fi.toPath(), LinkOption.NOFOLLOW_LINKS)
        var m = 0
        for ((perm, bit) in listOf(PosixFilePermission.OWNER_READ to 256, PosixFilePermission.OWNER_WRITE to 128,
            PosixFilePermission.OWNER_EXECUTE to 64, PosixFilePermission.GROUP_READ to 32, PosixFilePermission.GROUP_WRITE to 16,
            PosixFilePermission.GROUP_EXECUTE to 8, PosixFilePermission.OTHERS_READ to 4, PosixFilePermission.OTHERS_WRITE to 2,
            PosixFilePermission.OTHERS_EXECUTE to 1)) if (perm in p) m = m or bit
        m
    } catch (e: Exception) {
        (if (fi.canRead()) 256 else 0) or (if (fi.canWrite()) 128 else 0) or (if (fi.canExecute()) 64 else 0)
    }

    /** La photo du terrain (au plus MAX_PHOTO entrées, PROFONDEUR niveaux) ; cwd : le dossier courant (absolu). */
    fun photo(racine: File, cwd: File?): Photo {
        val f = LinkedHashMap<String, Entree>()
        fun tour(d: File, r: String, n: Int) {
            if (n > PROFONDEUR || f.size >= MAX_PHOTO) return
            val es = (d.listFiles() ?: return).sortedBy { it.name }
            for (e in es) {
                if (f.size >= MAX_PHOTO) return
                val c = if (r.isEmpty()) e.name else "$r/${e.name}"
                val lien = try { Files.isSymbolicLink(e.toPath()) } catch (x: Exception) { false }
                val g = if (lien) "l" else if (e.isDirectory) "d" else "f"
                f[c] = Entree(g, if (g == "d") 0 else e.length(), e.lastModified(), droitsDe(e))
                if (g == "d" && e.name !in IGNORES) tour(e, c, n + 1)
            }
        }
        if (racine.isDirectory) tour(racine, "", 1)
        return Photo(relatif(racine, cwd), f)
    }

    fun relatif(racine: File, chemin: File?): String? {
        if (chemin == null) return null
        val a = try { racine.canonicalPath } catch (e: Exception) { racine.absolutePath }
        val b = try { chemin.canonicalPath } catch (e: Exception) { chemin.absolutePath }
        if (b == a) return ""
        if (!b.startsWith("$a/")) return null
        return b.substring(a.length + 1)
    }

    fun photoJson(p: Photo): JSONObject {
        val f = JSONObject()
        for ((k, e) in p.f) f.put(k, JSONArray().put(e.genre).put(e.taille).put(e.date).put(e.droits))
        return JSONObject().put("cwd", p.cwd ?: JSONObject.NULL).put("f", f)
    }

    fun photoDe(o: JSONObject): Photo {
        val f = LinkedHashMap<String, Entree>()
        val fo = o.optJSONObject("f") ?: JSONObject()
        for (k in fo.keys()) { val a = fo.getJSONArray(k); f[k] = Entree(a.getString(0), a.getLong(1), a.getLong(2), a.getInt(3)) }
        return Photo(if (o.isNull("cwd")) null else o.optString("cwd"), f)
    }

    // ------------------------------------------------------------ lire la ligne
    class Seg(val cmd: String, val args: List<Pair<String, Boolean>>, val redir: List<Pair<String, String>>, val fond: Boolean, val tuyau: Boolean)

    private fun jetons(seg: String): List<Pair<String, Boolean>> {
        val out = mutableListOf<Pair<String, Boolean>>()
        val cour = StringBuilder(); var cite = false; var dans = false; var q: Char? = null; var esc = false
        for (c in seg) {
            if (esc) { cour.append(c); esc = false; dans = true }
            else if (q != null) { if (c == q) q = null else if (c == '\\' && q == '"') esc = true else cour.append(c) }
            else if (c == '"' || c == '\'') { q = c; cite = true; dans = true }
            else if (c == '\\') esc = true
            else if (c == ' ' || c == '\t') { if (dans) out.add(cour.toString() to cite); cour.setLength(0); cite = false; dans = false }
            else { cour.append(c); dans = true }
        }
        if (dans) out.add(cour.toString() to cite)
        return out
    }

    fun correspond(nom: String, motif: String): Boolean {
        val rx = StringBuilder(); var i = 0
        while (i < motif.length) {
            val c = motif[i]; i++
            when {
                c == '*' -> rx.append(".*")
                c == '?' -> rx.append(".")
                c == '[' -> {
                    val j = motif.indexOf(']', if (i < motif.length && motif[i] in "!^") i + 1 else i)
                    if (j < 0) rx.append("\\[")
                    else { var cl = motif.substring(i, j); i = j + 1; if (cl.startsWith("!") || cl.startsWith("^")) cl = "^" + cl.substring(1); rx.append("[").append(cl.replace("\\", "\\\\")).append("]") }
                }
                c in ".^$+{}()|\\" -> rx.append('\\').append(c)
                else -> rx.append(c)
            }
        }
        return try { Regex(rx.toString(), RegexOption.DOT_MATCHES_ALL).matches(nom) } catch (e: Exception) { false }
    }

    fun canon(cmd: String): String { val c = cmd.substringAfterLast('/').lowercase(); return PS[c] ?: c }

    private val RX_REDIR = Regex("(\\d?>>?|&>)\\s*(\"[^\"]*\"|'[^']*'|[^\\s<>|;&]+)")
    fun segments(ligne: String): List<Seg> {
        val out = mutableListOf<Seg>()
        val texte = ligne.trim()
        val morceaux = mutableListOf<Pair<String, String>>()
        val cour = StringBuilder(); var q: Char? = null; var i = 0
        while (i < texte.length) {
            val c = texte[i]
            if (q != null) { cour.append(c); if (c == q) q = null; i++; continue }
            if (c == '"' || c == '\'') { q = c; cour.append(c); i++; continue }
            val deux = texte.substring(i, minOf(texte.length, i + 2))
            if (deux == "&&" || deux == "||") { morceaux.add(cour.toString() to deux); cour.setLength(0); i += 2; continue }
            if (c in ";|&" && !(c == '&' && i > 0 && texte[i - 1] == '>')) { morceaux.add(cour.toString() to c.toString()); cour.setLength(0); i++; continue }
            cour.append(c); i++
        }
        morceaux.add(cour.toString() to "")
        var prec = ""
        for ((seg, sep) in morceaux) {
            val s = seg.trim()
            if (s.isEmpty()) { prec = sep; continue }
            val redir = RX_REDIR.findAll(s).filter { !it.groupValues[1].startsWith("2") }
                .map { (if (">>" in it.groupValues[1]) ">>" else ">") to it.groupValues[2].trim('"', '\'') }.toList()
            val s2 = s.replace(RX_REDIR, " ").replace(Regex("<\\s*\\S+"), " ")
            var jet = jetons(s2)
            if (jet.isEmpty()) { prec = sep; continue }
            while (jet.size > 1 && jet[0].first in setOf("do", "then", "else", "{", "!", "time")) jet = jet.drop(1)
            var cmd = canon(jet[0].first); var args = jet.drop(1)
            if (cmd == "sudo" && args.isNotEmpty()) { cmd = canon(args[0].first); args = args.drop(1) }
            out.add(Seg(cmd, args, redir, sep == "&", prec == "|"))
            prec = sep
        }
        return out
    }

    private fun options(args: List<Pair<String, Boolean>>) =
        args.filter { (a, c) -> a.startsWith("-") && !a.startsWith("--") && !c }.joinToString("") { it.first.substring(1) } +
            args.filter { it.first.startsWith("--") }.joinToString(" ") { it.first }
    private fun chemins(args: List<Pair<String, Boolean>>) = args.filter { (a, c) -> !(a.startsWith("-") && !c) }.map { it.first }
    private fun joindre(cwd: String?, arg: String): String? {
        if (cwd == null) return null
        val a = arg.replace("\\", "/")
        if (a.startsWith("/") || a.startsWith("~")) {
            val m = Regex("terrain_terminagotchi(?:/(.*))?$").find(a) ?: return null
            return m.groupValues[1].trim('/')
        }
        val parts = if (cwd.isEmpty()) mutableListOf() else cwd.split("/").toMutableList()
        for (p in a.split("/")) {
            if (p == "" || p == ".") continue
            if (p == "..") { if (parts.isEmpty()) return null; parts.removeAt(parts.size - 1) } else parts.add(p)
        }
        return parts.joinToString("/")
    }
    private fun parent(c: String) = if ('/' in c) c.substringBeforeLast('/') else ""
    private fun nom(c: String) = c.substringAfterLast('/')
    private fun joker(a: String, cite: Boolean) = !cite && listOf("*", "?", "[").any { it in a }
    private fun haut(xs: List<String>): List<String> { val s = xs.toSet(); return s.filter { x -> s.none { y -> y != x && x.startsWith("$y/") } }.sorted() }
    private fun sous(xs: List<String>, d: String) = xs.count { it.startsWith("$d/") }
    fun region(chemin: String?): Pair<String?, String?> {
        val p = (chemin ?: "").split("/")
        if (p.size >= 2 && p[0] == "biome" && p[1] in Monde.TYPES) return p[1] to p.getOrNull(2)
        return null to null
    }
    private fun estParcelle(c: String): Boolean {
        val (ty, parc) = region(c)
        return ty != null && parc != null && nom(c) == parc && Regex("parcelle[_-]?\\d*").matches(parc.lowercase())
    }
    private fun ev(t: String, cmd: String, vararg k: Pair<String, Any?>): JSONObject {
        val o = JSONObject().put("type", t).put("cmd", cmd).put("prio", PRIO[t] ?: 2)
        for ((a, b) in k) o.put(a, b ?: JSONObject.NULL)
        return o
    }
    private fun arr(xs: List<String>) = JSONArray().also { a -> xs.forEach { a.put(it) } }

    // ------------------------------------------------------------ la règle commune
    fun evenements(ligne: String, avant: Photo, apres: Photo, code: Int?, sortie: String = ""): List<JSONObject> =
        try { calcul(ligne, avant, apres, code, sortie) } catch (e: Exception) { emptyList() }

    private fun calcul(ligne: String, avant: Photo, apres: Photo, code: Int?, sortie: String): List<JSONObject> {
        val segs = segments(ligne)
        if (segs.isEmpty()) return emptyList()
        val cmds = segs.map { it.cmd }
        val fa = avant.f; val fb = apres.f
        val cwd0 = avant.cwd; val cwd1 = apres.cwd
        val moinsTout = fa.keys.filter { it !in fb }; val plusTout = fb.keys.filter { it !in fa }
        val plus = haut(plusTout); val moins = haut(moinsTout)
        val changes = fa.keys.filter { it in fb && fa[it] != fb[it] && fa.getValue(it).genre == "f" }.sorted()
        val droits = fa.keys.filter { it in fb && fa.getValue(it).droits != fb.getValue(it).droits }.sorted()
        val evs = mutableListOf<JSONObject>()
        val principal = segs.firstOrNull { it.cmd !in RIEN } ?: segs[0]
        val cmd0 = principal.cmd
        val vises = mutableListOf<String>()
        for (s in segs) for ((a, cite) in s.args) if (joker(a, cite)) {
            val base = joindre(cwd0, if ('/' in a) parent(a) else ".") ?: continue
            val motif = nom(a)
            vises += fa.keys.filter { parent(it) == base && correspond(nom(it), motif) && (motif.startsWith(".") || !nom(it).startsWith(".")) }.sorted()
        }
        if (vises.isNotEmpty()) evs.add(ev("jokers", cmd0, "chemins" to arr(vises.take(40)), "n" to vises.size))
        val usesP = HashSet<String>(); val usesM = HashSet<String>()
        if ("mv" in cmds) for (m in moins) {
            val g = fa.getValue(m).genre; val taille = fa.getValue(m).taille
            val cands = plus.filter { it !in usesP && fb.getValue(it).genre == g && (g == "d" || fb.getValue(it).taille == taille) }
                .sortedWith(compareBy({ nom(it) != nom(m) }, { it }))
            if (cands.isNotEmpty()) {
                val p = cands[0]; usesP.add(p); usesM.add(m)
                evs.add(ev(if (parent(p) == parent(m)) "renomme" else "deplace", "mv", "de" to m, "vers" to p, "genre" to g, "n" to sous(moinsTout, m) + 1))
            }
        }
        if ("cp" in cmds || "copy" in cmds) {
            val sources = mutableListOf<String>()
            for (s in segs) if (s.cmd == "cp") {
                val ch = chemins(s.args)
                for (a in ch.dropLast(1)) { val r = joindre(cwd0, a); if (r != null && r in fa) sources.add(r) }
                if (s.args.any { (a, c) -> joker(a, c) }) sources += vises
            }
            for (p in plus) {
                if (p in usesP) continue
                val g = fb.getValue(p).genre
                val cands = sources.filter { fa.getValue(it).genre == g && (g == "d" || fa.getValue(it).taille == fb.getValue(p).taille) }
                    .sortedWith(compareBy({ nom(it) != nom(p) }, { it }))
                if (cands.isNotEmpty()) { usesP.add(p); evs.add(ev("copie", "cp", "de" to cands[0], "vers" to p, "genre" to g, "n" to sous(plusTout, p) + 1)) }
            }
        }
        val usesC = HashSet<String>()
        evs += consommer(segs, cwd0, fa, fb, plus, moins, changes, usesP, usesM, usesC)
        val redirs = segs.flatMap { s -> s.redir.map { it.first to joindre(cwd0, it.second) } }
        val via = when {
            "touch" in cmds -> "touch"
            redirs.isNotEmpty() || "tee" in cmds -> "ecrire"
            "curl" in cmds || "wget" in cmds -> "messager"
            cmds.any { it in CAISSE } -> "caisse"
            "git" in cmds -> "photo"
            "mkdir" in cmds -> "mkdir"
            else -> "autre"
        }
        for (p in plus) {
            if (p in usesP) continue
            if (fb.getValue(p).genre == "d") {
                val parcs = (listOf(p) + plusTout.filter { it.startsWith("$p/") }).filter { fb.getValue(it).genre == "d" && estParcelle(it) }.sorted()
                evs.add(ev("dossier+", if (cmd0 != "cd") cmd0 else "mkdir", "chemin" to p, "n" to sous(plusTout, p) + 1,
                    "parcelle" to parcs.isNotEmpty(), "parcelles" to arr(parcs.take(8)), "region" to region(p).first))
            } else evs.add(ev("objet+", cmd0, "chemin" to p, "via" to via, "region" to region(p).first))
        }
        for (m in moins) {
            if (m in usesM) continue
            if (fa.getValue(m).genre == "d") evs.add(ev("dossier-", cmd0, "chemin" to m, "n" to sous(moinsTout, m) + 1, "region" to region(m).first))
            else evs.add(ev("objet-", cmd0, "chemin" to m, "region" to region(m).first))
        }
        for (c in changes) {
            val a = fa.getValue(c); val b = fb.getValue(c)
            if ((a.taille == b.taille && a.date == b.date) || c in usesC) continue
            val cible = redirs.firstOrNull { it.second == c }?.first
            if (cible != null) evs.add(ev("ecrit", if (cmd0 == "echo" || cmd0 == "printf") "echo" else cmd0, "chemin" to c, "mode" to cible, "avant" to a.taille, "apres" to b.taille))
            else if ("touch" in cmds && a.taille == b.taille) evs.add(ev("touche", "touch", "chemin" to c))
            else if ("tee" in cmds) evs.add(ev("ecrit", "tee", "chemin" to c, "mode" to (if ("a" in options(segs.first { it.cmd == "tee" }.args)) ">>" else ">"), "avant" to a.taille, "apres" to b.taille))
            else evs.add(ev("modifie", cmd0, "chemin" to c))
        }
        for (c in droits) evs.add(ev("droits", if ("chmod" in cmds) "chmod" else cmd0, "chemin" to c, "avant" to fa.getValue(c).droits,
            "apres" to fb.getValue(c).droits, "genre" to fa.getValue(c).genre))
        if (cwd0 != cwd1 && ("cd" in cmds || "pushd" in cmds || "popd" in cmds)) evs.add(ev("cd", "cd", "de" to cwd0, "vers" to cwd1))
        val fichiers = evs.filter { it.getString("type") != "jokers" }
        val tuyaux = segs.size > 1 && segs.any { it.tuyau }
        if (fichiers.isEmpty() && code == 0 && tuyaux) {
            val src = chemins(segs[0].args).map { joindre(cwd1, it) }.firstOrNull { it != null && it in fb }
            evs.add(ev("tuyau", segs[0].cmd, "etapes" to arr(segs.map { it.cmd }.take(6)), "source" to src, "region" to region(src ?: cwd1 ?: "").first))
        } else if (fichiers.isEmpty() && code == 0) {
            for (s in segs) {
                val c = s.cmd; val args = s.args; val ch = chemins(args)
                if (args.any { it.first == "--help" }) continue
                if (c == "pwd") evs.add(ev("pwd", c, "chemin" to cwd1))
                else if (c == "ls" && !s.tuyau) {
                    val cible = if (ch.isNotEmpty() && !joker(args.last().first, args.last().second)) joindre(cwd1, ch[0]) else cwd1
                    if (cible != null && (cible == "" || (cible in fb && fb.getValue(cible).genre == "d"))) {
                        val o = options(args)
                        evs.add(ev("ls", c, "chemin" to cible, "caches" to ("a" in o || "force" in o.lowercase()), "long" to ("l" in o),
                            "n" to fb.keys.count { parent(it) == cible && ("a" in o || !nom(it).startsWith(".")) }))
                    }
                } else if (c == "find") {
                    val base = (if (ch.isNotEmpty() && !ch[0].startsWith("-")) joindre(cwd1, ch[0]) else cwd1) ?: continue
                    var motif: String? = null
                    args.forEachIndexed { i, (a, _) -> if ((a == "-name" || a == "-iname") && i + 1 < args.size) motif = args[i + 1].first }
                    val ci = args.any { it.first == "-iname" }
                    val mo = motif
                    val trouves = fb.keys.filter { (base == "" || it.startsWith("$base/")) &&
                        (mo == null || correspond(if (ci) nom(it).lowercase() else nom(it), if (ci) mo.lowercase() else mo)) }.sorted()
                    evs.add(ev("find", c, "chemin" to base, "motif" to mo, "chemins" to arr(trouves.take(40)), "n" to trouves.size))
                } else if (c in LIRE && !s.tuyau) {
                    for (a in ch.take(3)) { val r = joindre(cwd1, a); if (r != null && r in fb && fb.getValue(r).genre == "f") evs.add(ev("lire", c, "chemin" to r, "taille" to fb.getValue(r).taille)) }
                } else if (c in EMPREINTE) {
                    for (a in ch.take(3)) { val r = joindre(cwd1, a); if (r != null && r in fb && fb.getValue(r).genre == "f") evs.add(ev("empreinte", c, "chemin" to r)) }
                } else if (c == "git" && sansValeurs(args, setOf("-C", "-c")).firstOrNull() == "commit") evs.add(ev("photo", "git", "quoi" to "commit"))
                if (c in RESEAU) evs.add(ev("messager", c, "cible" to cibleReseau(args), "ok" to true))
                if (c in PROCESSUS || s.fond) evs.add(ev("lucioles", c, "quoi" to (if (s.fond) "part" else if (c in TUER) "eteint" else "voir"), "ok" to true))
            }
        }
        val (autres, absorbe) = secondaires(segs, cwd0, cwd1, fa, fb, code, sortie, evs.toList())
        evs += autres
        if (fichiers.isEmpty() && code != null && code != 0 && !absorbe) {
            if (cmd0 in RESEAU) evs.add(ev("messager", cmd0, "cible" to cibleReseau(principal.args), "ok" to false))
            else if (cmd0 in TUER) evs.add(ev("lucioles", cmd0, "quoi" to "eteint", "ok" to false))
            else if (cmd0 !in RIEN) evs.add(refus(principal, cwd0, fa, sortie))
        }
        if (extensions.isNotEmpty()) {
            val ctx = JSONObject().put("ligne", ligne).put("cmds", arr(cmds)).put("avant", photoJson(avant)).put("apres", photoJson(apres))
                .put("code", code ?: JSONObject.NULL).put("sortie", sortie).put("plus", arr(plus)).put("moins", arr(moins))
                .put("changes", arr(changes)).put("deja", JSONArray(evs.map { JSONObject(it.toString()) }))
            for (f in extensions) try { evs += f(ctx) } catch (e: Exception) { }
        }
        return grouper(evs)
    }

    // ------------------------------------------------------------ caisses, liens, retours dans le temps (effets.py)
    private class Archive(val mode: String?, val archive: String?, val fichiers: List<String>)

    private fun archive(seg: Seg): Archive {
        val c = seg.cmd; val args = seg.args
        if (c == "tar") {
            var mode: String? = null; var archive: String? = null; val fichiers = mutableListOf<String>(); var attend: String? = null
            for ((i, p) in args.withIndex()) {
                val (a, cite) = p
                if (attend != null) { if (attend == "f") archive = a; attend = null; continue }
                if (a.startsWith("--") && !cite) {
                    when {
                        a.startsWith("--file=") -> archive = a.substring(7)
                        a in setOf("--create", "--append", "--update") -> mode = "c"
                        a in setOf("--extract", "--get") -> mode = "x"
                        a == "--list" -> mode = "t"
                        a == "--file" || a == "--directory" -> attend = if (a == "--file") "f" else "C"
                    }
                    continue
                }
                var lettres: String? = null
                if (a.startsWith("-") && a.length > 1 && !cite) lettres = a.substring(1)
                else if (i == 0 && !cite && Regex("[A-Za-z]+").matches(a) && "cxt".any { it in a }) lettres = a
                if (lettres != null) {
                    for (x in lettres) when (x) { 'c', 'r', 'u' -> mode = "c"; 'x' -> mode = "x"; 't' -> mode = "t" }
                    if ('f' in lettres) attend = "f" else if ('C' in lettres) attend = "C"
                    continue
                }
                fichiers.add(a)
            }
            return Archive(mode, archive, fichiers)
        }
        val ch = chemins(args)
        if (c == "unzip") return Archive("x", ch.firstOrNull(), emptyList())
        if (c == "zip") return Archive("c", ch.firstOrNull(), ch.drop(1))
        if (c == "gzip" || c == "gunzip") return Archive(if (c == "gunzip" || "d" in options(args)) "u" else "g", null, ch)
        return Archive(null, null, emptyList())
    }

    private fun fichiersSous(f: Map<String, Entree>, r: String): Int {
        val e = f[r] ?: return 0
        if (e.genre != "d") return 1
        return f.entries.count { it.key.startsWith("$r/") && it.value.genre != "d" }
    }

    private fun consommer(segs: List<Seg>, cwd0: String?, fa: Map<String, Entree>, fb: Map<String, Entree>, plus: List<String>, moins: List<String>,
                          changes: List<String>, up: HashSet<String>, um: HashSet<String>, uc: HashSet<String>): List<JSONObject> {
        val evs = mutableListOf<JSONObject>()
        val libres = plus.filter { it !in up }
        for (s in segs) {
            val c = s.cmd; val ch = if (c == "git") sansValeurs(s.args, setOf("-C", "-c")) else chemins(s.args)
            if (c in CAISSE) {
                val ar = archive(s)
                val arch = if (ar.archive != null && ar.archive.isNotEmpty()) joindre(cwd0, ar.archive) else null
                if (ar.mode == "c" && arch != null && (arch in libres || arch in changes) && arch !in up) {
                    up.add(arch); uc.add(arch)
                    val srcs = ar.fichiers.mapNotNull { joindre(cwd0, it) }.filter { it in fa }
                    evs.add(ev("caisse", c, "quoi" to "ferme", "chemin" to arch, "chemins" to arr(srcs.take(8)),
                        "n" to srcs.sumOf { fichiersSous(fa, it) }, "region" to region(arch).first))
                } else if (ar.mode == "x" && arch != null && arch in fb) {
                    val sortis = libres.filter { it !in up } + changes.filter { it !in uc && it != arch }
                    if (sortis.isNotEmpty()) {
                        for (p in sortis) { up.add(p); uc.add(p) }
                        evs.add(ev("caisse", c, "quoi" to "ouvre", "chemin" to arch, "chemins" to arr(sortis.take(8)),
                            "n" to sortis.sumOf { fichiersSous(fb, it) }, "region" to region(sortis[0]).first))
                    }
                } else if (ar.mode == "g" || ar.mode == "u") {
                    for (p in libres) {
                        if (p in up) continue
                        val avant = if (ar.mode == "g" && p.endsWith(".gz")) p.dropLast(3) else if (ar.mode == "u") "$p.gz" else null
                        if (avant != null && avant.isNotEmpty() && avant in moins && avant !in um) {
                            up.add(p); um.add(avant)
                            evs.add(ev("caisse", c, "quoi" to (if (ar.mode == "g") "serre" else "ouvre"), "chemin" to p, "de" to avant,
                                "chemins" to arr(listOf(p)), "n" to 1, "region" to region(p).first))
                        }
                    }
                }
            } else if (c == "ln" && ch.size in 1..2) {
                val sym = "s" in options(s.args) || s.args.any { it.first == "--symbolic" }
                val cibleArg = ch[0]
                var lien = joindre(cwd0, if (ch.size == 2) ch[1] else nom(cibleArg.trimEnd('/')))
                if (lien != null && fa[lien]?.genre == "d") lien = (if (lien.isNotEmpty()) "$lien/" else "") + nom(cibleArg.trimEnd('/'))
                if (lien != null && lien in libres && lien !in up) {
                    up.add(lien)
                    val cible = joindre(if (sym) parent(lien) else cwd0, cibleArg)
                    evs.add(ev("lien", "ln", "chemin" to lien, "cible" to cible, "dehors" to (cible == null),
                        "mort" to (cible != null && cible !in fb), "dur" to !sym, "region" to region(lien).first))
                }
            } else if (c == "git" && (ch.firstOrNull() == "restore" || (ch.firstOrNull() == "checkout" && s.args.any { it.first == "--" }))) {
                val revenus = libres.filter { it !in up } + changes.filter { it !in uc }
                for (p in revenus) { up.add(p); uc.add(p) }
                if (revenus.isNotEmpty()) evs.add(ev("rembobine", "git", "chemin" to revenus[0], "chemins" to arr(revenus.take(8)),
                    "n" to revenus.size, "region" to region(revenus[0]).first))
            } else if (c == "git" && ch.firstOrNull() == "init") {
                for (p in libres) {
                    if (p in up) continue
                    if (nom(p) == ".git" || "$p/.git" in fb) {
                        up.add(p)
                        evs.add(ev("album", "git", "quoi" to "neuf", "chemin" to (if (nom(p) == ".git") parent(p) else p), "n" to 0))
                    }
                }
            } else if (c == "mktemp") {
                val p = libres.firstOrNull { it !in up }
                if (p != null) { up.add(p); evs.add(ev("sablier", "mktemp", "chemin" to p, "nom" to nom(p), "genre" to fb.getValue(p).genre, "region" to region(p).first)) }
            }
        }
        return evs
    }

    // ------------------------------------------------------------ les effets secondaires et ceux des mondes (effets.py)
    private fun nombre(txt: String): Double? {
        val m = Regex("([0-9]+(?:[.,][0-9]+)?)([KMGTPkmgtp]?)[iI]?[BboO]?").matchEntire(txt.trim()) ?: return null
        return m.groupValues[1].replace(",", ".").toDouble() * Math.pow(1024.0, "_KMGTP".indexOf(m.groupValues[2].uppercase().ifEmpty { "_" }).toDouble())
    }
    private fun lignes(sortie: String) = sortie.split("\n").filter { it.isNotBlank() }
    private fun sansValeurs(args: List<Pair<String, Boolean>>, avecValeur: Set<String>): List<String> {
        val out = mutableListOf<String>(); var saute = false
        for ((a, cite) in args) {
            if (saute) { saute = false; continue }
            if (a.startsWith("-") && !cite) { saute = a in avecValeur; continue }
            out.add(a)
        }
        return out
    }

    private fun secondaires(segs: List<Seg>, cwd0: String?, cwd1: String?, fa: Map<String, Entree>, fb: Map<String, Entree>, code: Int?,
                            sortie: String, deja: List<JSONObject>): Pair<List<JSONObject>, Boolean> {
        val evs = mutableListOf<JSONObject>(); var absorbe = false
        val ok = code == 0
        for ((i, s) in segs.withIndex()) {
            var c = s.cmd; val args = s.args
            var ch = chemins(args)
            var o = options(args)
            val tuyau = s.tuyau || (i + 1 < segs.size && segs[i + 1].tuyau) || s.redir.isNotEmpty()
            if (c == "tg" && ch.firstOrNull() == "atelier") { c = "atelier"; ch = ch.drop(1) }
            if (c == "tree" && ok && !tuyau) {
                var prof = PROFONDEUR; var cible: String? = null; var saute = false
                for ((a, cite) in args) {
                    if (saute) { saute = false; if (Regex("[0-9]+").matches(a)) prof = max(1, a.toInt()); continue }
                    if (a == "-L" && !cite) saute = true
                    else if (!(a.startsWith("-") && !cite) && cible == null) cible = a
                }
                val base = if (cible != null) joindre(cwd1, cible) else cwd1
                if (base != null && (base == "" || fb[base]?.genre == "d")) {
                    val tout = "a" in o
                    val pref = if (base.isNotEmpty()) "$base/" else ""
                    var vus = fb.keys.filter { x -> x.startsWith(pref) && x != base &&
                        (tout || x.substring(pref.length).split("/").none { it.startsWith(".") }) && x.substring(pref.length).count { it == '/' } < prof }
                    if ("d" in o) vus = vus.filter { fb.getValue(it).genre == "d" }
                    val niv = vus.maxOfOrNull { x -> x.substring(pref.length).count { it == '/' } + 1 } ?: 0
                    evs.add(ev("arbre", c, "chemin" to base, "niveaux" to niv, "dossiers" to vus.count { fb.getValue(it).genre == "d" },
                        "fichiers" to vus.count { fb.getValue(it).genre != "d" }))
                }
            } else if (c == "du" && ok && !tuyau) {
                var elems = mutableListOf<String?>()
                for ((a, cite) in args) {
                    if (a.startsWith("-") && !cite) continue
                    if (joker(a, cite)) {
                        val base = joindre(cwd1, if ('/' in a) parent(a) else ".")
                        if (base != null) elems.addAll(fb.keys.filter { parent(it) == base && correspond(nom(it), nom(a)) && !nom(it).startsWith(".") }.sorted())
                    } else { val r = joindre(cwd1, a); if (r != null && (r == "" || r in fb)) elems.add(r) }
                }
                if (ch.isEmpty()) {
                    elems = (if ("s" in o) mutableListOf() else fb.keys.filter { parent(it) == cwd1 && fb.getValue(it).genre == "d" }.sorted().toMutableList<String?>())
                    if (elems.isEmpty()) elems = mutableListOf(cwd1)
                }
                val el = elems.filterNotNull()
                if (el.isNotEmpty()) {
                    fun poids(r: String): Long = (if (fb[r]?.genre == "f") fb.getValue(r).taille else 0L) +
                        fb.entries.filter { it.key.startsWith(if (r.isNotEmpty()) "$r/" else "") && it.value.genre == "f" }.sumOf { it.value.taille }
                    val tailles = el.take(8).map { it to poids(it) }
                    evs.add(ev("taille", c, "chemin" to (if (el.size > 1) parent(el[0]) else el[0]),
                        "elements" to JSONArray().also { j -> tailles.forEach { (r, t) -> j.put(JSONArray().put(r).put(t)) } },
                        "total" to tailles.sumOf { it.second }))
                }
            } else if (c in CAISSE && ok && !tuyau && archive(s).mode == "t") {
                val arch = joindre(cwd1, archive(s).archive ?: "")
                if (arch != null && fb[arch]?.genre == "f") evs.add(ev("caisse", c, "quoi" to "voir", "chemin" to arch, "chemins" to JSONArray(),
                    "n" to lignes(sortie).size, "region" to region(arch).first))
            } else if (c == "df" && ok && !tuyau) {
                val m = Regex("([0-9]{1,3})%").find(sortie)
                evs.add(ev("disque", c, "pourcent" to m?.groupValues?.get(1)?.toInt()))
            } else if (c == "free" && ok && !tuyau) {
                var p: Int? = null
                for (l in sortie.split("\n")) {
                    val m = Regex("^\\s*[mM][eéEÉ][mM][a-zA-Z]*\\.?\\s*:\\s*(\\S+)\\s+(\\S+)").find(l) ?: continue
                    val tot = nombre(m.groupValues[1]); val uti = nombre(m.groupValues[2])
                    if (tot != null && tot != 0.0 && uti != null) p = max(0, min(100, Math.floor(uti * 100 / tot + .5).toInt()))
                    break
                }
                evs.add(ev("memoire", c, "pourcent" to p))
            } else if (c == "systemctl" && ok && !tuyau && (ch.isEmpty() || ch[0] in setOf("list-units", "status", "is-active"))) {
                evs.add(ev("lanternes", c, "n" to sortie.split("\n").count { Regex("\\brunning\\b").containsMatchIn(it) }))
            } else if (c == "crontab" && ok && !tuyau && "l" in o) {
                evs.add(ev("reveil", c, "n" to lignes(sortie).count { !it.trim().startsWith("#") }))
            } else if (c == "journalctl" && ok && !tuyau) {
                evs.add(ev("journal", c, "n" to lignes(sortie).count { !it.startsWith("--") }))
            } else if (c == "git" && sansValeurs(args, setOf("-C", "-c")).isNotEmpty()) {
                val sous = sansValeurs(args, setOf("-C", "-c"))[0]
                var k = 0
                while (k < args.size && !(args[k].first == sous && (k == 0 || args[k - 1].first !in setOf("-C", "-c")))) k++
                val reste = args.drop(k + 1)
                ch = listOf(sous) + sansValeurs(reste, setOf("-m", "--message", "-F"))
                o = options(reste)
                if (sous in setOf("branch", "switch", "checkout", "merge") && evs.any { it.getString("type") in setOf("branche", "fusion") }) continue
                if (sous == "add" && ok) {
                    var cibles = ch.drop(1).mapNotNull { joindre(cwd1, it) }.filter { it == "" || it in fb }
                    if ("A" in o || "all" in o) cibles = if (cwd1 != null) listOf(cwd1) else emptyList()
                    if (cibles.isNotEmpty()) evs.add(ev("etoile", c, "chemin" to cibles[0], "chemins" to arr(cibles.take(8)), "n" to cibles.size))
                } else if (sous == "log" && ok && !tuyau) {
                    val n = if ("oneline" in o) lignes(sortie).size else sortie.split("\n").count { it.startsWith("commit ") }
                    evs.add(ev("album", c, "quoi" to "voir", "chemin" to cwd1, "n" to n))
                } else if (sous == "branch" && ok && ch.size >= 2 && "dDmMc".none { it in o }) {
                    evs.add(ev("branche", c, "quoi" to "nouvelle", "nom" to ch[1], "chemin" to cwd1))
                } else if ((sous == "switch" || sous == "checkout") && ok && ch.size >= 2 && args.none { it.first == "--" }) {
                    val neuve = ("c" in o && sous == "switch") || ("b" in o && sous == "checkout")
                    evs.add(ev("branche", c, "quoi" to (if (neuve) "nouvelle" else "change"), "nom" to ch[1], "chemin" to cwd1))
                } else if (sous == "merge" && ch.size >= 2) {
                    if (ok) evs.add(ev("fusion", c, "ok" to true, "nom" to ch[1], "chemin" to cwd1))
                    else if ("conflict" in sortie.lowercase() || "conflit" in sortie.lowercase()) {
                        absorbe = true; evs.add(ev("fusion", c, "ok" to false, "nom" to ch[1], "chemin" to cwd1))
                    }
                }
            } else if (c == "atelier" && ch.firstOrNull() == "pas" && ok) {
                evs.add(ev("robot", c, "quoi" to "pas", "valeur" to null))
            } else if ((c in AIDE || args.any { it.first == "--help" }) && ok && i == 0) {
                evs.add(ev("grimoire", c, "mot" to (if (ch.isNotEmpty() && c in AIDE) ch[0] else c)))
            } else if (c == "shellcheck" && ch.isNotEmpty()) {
                val r = joindre(cwd1, ch.last())
                val n = RX_SC.findAll(sortie).count()
                if (ok || n > 0) { absorbe = absorbe || !ok; evs.add(ev("loupe", c, "chemin" to (if (r != null && r in fb) r else null), "ok" to ok, "n" to n)) }
            } else if (c == "trap" && ok && ch.size >= 2 && ch[0] != "-") {
                evs.add(ev("filet", c, "signaux" to arr(ch.drop(1).take(3).map { it.uppercase() })))
            } else if (c == "mktemp" && ok && (deja + evs).none { it.getString("type") == "sablier" }) {
                val l = (lignes(sortie).firstOrNull() ?: "").trim()
                evs.add(ev("sablier", c, "chemin" to null, "nom" to l.replace("\\", "/").split("/").last().take(24),
                    "genre" to (if ("d" in o) "d" else "f"), "region" to null))
            } else if (c == "strace") {
                val n = RX_APPEL.findAll(sortie).count()
                if (n > 0) {
                    absorbe = absorbe || !ok
                    val cible = sansValeurs(args, setOf("-e", "-o", "-p", "-s", "-u", "-E", "-P", "-a", "-X", "-b", "-O", "-S", "-I"))
                    evs.add(ev("espion", c, "n" to n, "cible" to (cible.firstOrNull() ?: "")))
                }
            }
        }
        for (e in deja) {
            val ch = if (e.has("chemin") && !e.isNull("chemin")) e.getString("chemin") else ""
            if (nom(parent(ch)) != "robot") continue
            val t = e.getString("type")
            if ((t == "ecrit" || t == "objet+") && nom(ch) in setOf("led", "moteur")) {
                var v: String? = null
                for (s in segs) if (s.redir.any { joindre(cwd0, it.second) == ch } && s.cmd in setOf("echo", "printf")) v = chemins(s.args).joinToString(" ").take(12)
                evs.add(ev("robot", "echo", "quoi" to nom(ch), "valeur" to v, "chemin" to ch))
            } else if (t == "lire" && nom(ch) == "capteur_distance") {
                val m = Regex("-?[0-9]+").find(sortie)
                evs.add(ev("robot", e.getString("cmd"), "quoi" to "capteur", "valeur" to m?.value, "chemin" to ch))
            }
        }
        return evs to absorbe
    }

    private fun cibleReseau(args: List<Pair<String, Boolean>>): String {
        var out = ""; var saute = false
        for ((a, _) in args) {
            if (saute) { saute = false; continue }
            if (a.startsWith("-")) { saute = a in setOf("-c", "-o", "-O", "-w", "-W", "-i", "-p", "-H", "-d", "-X", "-m", "--output", "-Count"); continue }
            out = a
        }
        val m = Regex("^[a-z]+://([^/:]+)").find(out)
        return m?.groupValues?.get(1) ?: out
    }

    private fun refus(seg: Seg, cwd: String?, fa: Map<String, Entree>, sortie: String): JSONObject {
        val s = sortie.lowercase()
        fun any(vararg xs: String) = xs.any { it in s }
        val raison = when {
            any("command not found", "commande introuvable", "not recognized", "n'est pas reconnu") -> "commande"
            any("permission", "non accordée", "denied", "refusé", "accès", "unauthorizedaccess", "operation not permitted", "opération non permise") -> "droits"
            any("not empty", "pas vide", "non vide", "directory not empty") -> "pas_vide"
            any("file exists", "existe déjà", "already exists", "le fichier existe") -> "existe"
            any("no such", "aucun fichier", "introuvable", "cannot find", "not found", "n'existe pas", "does not exist", "itemnotfound") -> "introuvable"
            any("is a directory", "est un dossier", "est un répertoire") -> "dossier"
            seg.cmd == "cd" -> "introuvable"
            else -> "autre"
        }
        val ch = chemins(seg.args)
        val cible = if (ch.isNotEmpty() && raison != "commande") joindre(cwd, ch.last()) else null
        return ev("refus", seg.cmd, "raison" to raison, "chemin" to cible, "existe" to (cible != null && cible in fa))
    }

    fun grouper(evs: List<JSONObject>): List<JSONObject> {
        val compte = HashMap<String, Int>()
        for (e in evs) compte[e.getString("type")] = (compte[e.getString("type")] ?: 0) + 1
        val out = mutableListOf<JSONObject>(); val fait = HashSet<String>()
        for (e in evs) {
            val t = e.getString("type")
            if ((compte[t] ?: 0) > GROUPE && t != "jokers") {
                if (t in fait) continue
                fait.add(t)
                val tous = evs.filter { it.getString("type") == t }
                val ch = tous.mapNotNull { x -> listOf("chemin", "vers").map { if (x.has(it) && !x.isNull(it)) x.getString(it) else "" }.firstOrNull { it.isNotEmpty() } }
                val regs = tous.map { if (it.has("region") && !it.isNull("region")) it.getString("region") else null }.toSet()
                out.add(JSONObject().put("type", "groupe").put("cmd", e.getString("cmd")).put("prio", 3).put("sorte", t).put("n", tous.size)
                    .put("chemins", arr(ch.take(GROUPE))).put("region", if (regs.size == 1) regs.first() ?: JSONObject.NULL else JSONObject.NULL))
            } else out.add(e)
        }
        return out
    }

    fun filtrer(evs: List<JSONObject>, niveau: String): List<JSONObject> = when (niveau) {
        "aucun" -> emptyList()
        "essentiels" -> evs.filter { it.optInt("prio", 2) >= 3 }
        else -> evs.toList()
    }

    fun cleDit(e: JSONObject): String {
        val t = if (e.getString("type") != "groupe") e.getString("type") else e.optString("sorte")
        val via = e.optString("via")
        return when {
            t == "refus" -> "efx.dit.refus." + e.optString("raison", "autre")
            t == "ecrit" -> "efx.dit.ecrit" + if (e.optString("mode") == ">>") ".ajoute" else ".efface"
            t == "ls" && e.optBoolean("caches") -> "efx.dit.ls_a"
            t == "objet+" && via in setOf("touch", "ecrire", "messager", "caisse") -> "efx.dit.objet.$via"
            t == "dossier+" && e.optBoolean("parcelle") -> "efx.dit.parcelle"
            t == "lucioles" -> "efx.dit.lucioles." + e.optString("quoi", "voir")
            t == "messager" -> "efx.dit.messager" + if (e.optBoolean("ok")) "" else ".rate"
            t in setOf("caisse", "album", "branche", "robot") -> "efx.dit.$t." + (if (e.isNull("quoi")) "" else e.optString("quoi"))
            t == "lien" -> "efx.dit.lien" + if (e.optBoolean("mort")) ".mort" else ""
            t == "fusion" -> "efx.dit.fusion" + if (e.optBoolean("ok")) "" else ".conflit"
            t == "loupe" -> "efx.dit.loupe" + if (e.optBoolean("ok")) ".ok" else ""
            else -> "efx.dit." + t.replace("+", "_plus").replace("-", "_moins")
        }
    }

    fun aDire(compteurs: JSONObject, evs: List<JSONObject>): String? {
        for (e in evs) { val k = cleDit(e); if (compteurs.optInt(k, 0) < DITS_MAX) return k }
        return null
    }
}
