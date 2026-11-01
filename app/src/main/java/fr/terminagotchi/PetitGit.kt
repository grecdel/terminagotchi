package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Le petit git du téléphone (la Bibliothèque du Temps, docs/programme.md § 2.13) : le téléphone n'a pas git, alors
 * l'appli en a un petit, HONNÊTE et testé. Il range ses photos à la façon de git (blobs, arbres, commits) et calcule les
 * MÊMES empreintes SHA-1 que le vrai git ; il écrit les mêmes messages (en anglais, comme git avec LC_ALL=C) pour ce
 * que font les leçons : init, config, status, add, commit, log (--oneline, --graph, -S, -p), diff (--staged), show,
 * restore, checkout, switch, branch, merge (et ses conflits), clone et pull entre dossiers du terrain, remote -v,
 * hash-object, cat-file, rev-parse. Vérifié contre le VRAI git par tests/jvm/Temps.kt (vecteurs
 * donnees/temps/vecteurs.json, faits par pc/outils/vecteurs_temps.py).
 *
 * Ce qu'il ne fait pas (il le dit) : push, remote add, fetch d'un serveur, rebase, stash, tags, sous-modules, éditeur
 * (il faut -m), --global (chaque album garde son nom d'exemple). Le dessin --graph est fidèle pour les chemins simples
 * (une branche qui part et revient) ; les gros historiques emmêlés peuvent se dessiner autrement que sur un ordinateur.
 * Il ne travaille QUE dans le terrain : ses données sont dans <dépôt>/.git/petit_git.json.
 */
object PetitGit {
    class Res(val texte: String, val code: Int = 0)

    /** l'heure des photos : (secondes depuis 1970, décalage en minutes) — les tests la fixent */
    @Volatile var horloge: () -> Pair<Long, Int> = {
        val ms = System.currentTimeMillis()
        (ms / 1000) to (java.util.TimeZone.getDefault().getOffset(ms) / 60000)
    }
    /** comment montrer un chemin (l'appli : le chemin du Terminaworld, /home/explorateur/…) */
    @Volatile var afficher: (String) -> String = { it }
    const val FICHIER = "petit_git.json"
    private val VIDE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"     // l'arbre vide de git

    // ================================================================ les empreintes
    private fun sha1(b: ByteArray): ByteArray = MessageDigest.getInstance("SHA-1").digest(b)
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    private fun deHex(h: String) = ByteArray(h.length / 2) { h.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
    fun blobSha(octets: ByteArray): String = hex(sha1("blob ${octets.size}\u0000".toByteArray(Charsets.US_ASCII) + octets))
    fun blobSha(texte: String) = blobSha(texte.toByteArray(Charsets.UTF_8))

    private fun shaObjet(type: String, corps: ByteArray) = hex(sha1("$type ${corps.size}\u0000".toByteArray(Charsets.US_ASCII) + corps))

    // ================================================================ le dépôt
    class Depot(val racine: File) {
        val gitDir = File(racine, ".git")
        var j: JSONObject = JSONObject()

        fun charger(): Depot {
            j = try { JSONObject(File(gitDir, FICHIER).readText()) } catch (e: Exception) { JSONObject() }
            for (k in listOf("objets", "branches", "index", "config", "remotes", "amont")) if (j.optJSONObject(k) == null) j.put(k, JSONObject())
            if (j.optJSONObject("head") == null) j.put("head", JSONObject().put("ref", "master"))
            return this
        }

        fun sauver() {
            gitDir.mkdirs()
            File(gitDir, FICHIER).writeText(j.toString())
            // (pour les curieux qui font cat .git/HEAD : la même chose que le vrai git)
            try { File(gitDir, "HEAD").writeText(if (refHead() != null) "ref: refs/heads/${refHead()}\n" else "${head()}\n") } catch (e: Exception) { }
        }

        val objets: JSONObject get() = j.getJSONObject("objets")
        val branches: JSONObject get() = j.getJSONObject("branches")
        val index: JSONObject get() = j.getJSONObject("index")
        val config: JSONObject get() = j.getJSONObject("config")
        val remotes: JSONObject get() = j.getJSONObject("remotes")
        val amont: JSONObject get() = j.getJSONObject("amont")
        val fusion: JSONObject? get() = j.optJSONObject("fusion")

        /** la branche de HEAD, ou null si HEAD est détachée */
        fun refHead(): String? = j.getJSONObject("head").optString("ref").ifEmpty { null }
        /** l'empreinte de la photo de HEAD, ou null (pas encore de photo) */
        fun head(): String? = refHead()?.let { branches.optString(it).ifEmpty { null } } ?: j.getJSONObject("head").optString("detache").ifEmpty { null }
        fun objet(h: String): JSONObject? = objets.optJSONObject(h)
        fun blob(h: String): String = objet(h)?.optString("c") ?: ""
        fun commit(h: String): JSONObject? = objet(h)?.takeIf { it.optString("t") == "commit" }
        fun parents(h: String): List<String> = commit(h)?.optJSONArray("parents")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        fun conflits(): List<String> = fusion?.optJSONArray("conflits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()

        fun ajouterBlob(texte: String): String { val h = blobSha(texte); if (!objets.has(h)) objets.put(h, JSONObject().put("t", "blob").put("c", texte)); return h }

        /** l'arbre (récursif) d'une liste {chemin: blob} ; renvoie son empreinte */
        fun ecrireArbre(fichiers: Map<String, String>): String {
            val ici = HashMap<String, String>()                      // nom -> blob
            val sous = HashMap<String, MutableMap<String, String>>()  // dossier -> fichiers
            for ((p, h) in fichiers) {
                val k = p.indexOf('/')
                if (k < 0) ici[p] = h else sous.getOrPut(p.substring(0, k)) { HashMap() }[p.substring(k + 1)] = h
            }
            val entrees = ArrayList<Triple<String, String, String>>()  // mode, nom, empreinte
            for ((n, h) in ici) entrees.add(Triple("100644", n, h))
            for ((n, f) in sous) entrees.add(Triple("40000", n, ecrireArbre(f)))
            entrees.sortBy { if (it.first == "40000") it.second + "/" else it.second }
            val corps = java.io.ByteArrayOutputStream()
            for ((m, n, h) in entrees) { corps.write("$m $n\u0000".toByteArray(Charsets.UTF_8)); corps.write(deHex(h)) }
            val h = shaObjet("tree", corps.toByteArray())
            if (!objets.has(h)) objets.put(h, JSONObject().put("t", "tree").put("e", JSONArray(entrees.map { JSONArray(listOf(it.first, it.second, it.third)) })))
            return h
        }

        /** {chemin: blob} d'un arbre */
        fun aplatir(arbre: String?, prefixe: String = ""): Map<String, String> {
            val out = LinkedHashMap<String, String>()
            val o = arbre?.let { objet(it) } ?: return out
            val e = o.optJSONArray("e") ?: return out
            for (i in 0 until e.length()) {
                val x = e.getJSONArray(i)
                if (x.getString(0) == "40000") out.putAll(aplatir(x.getString(2), prefixe + x.getString(1) + "/"))
                else out[prefixe + x.getString(1)] = x.getString(2)
            }
            return out
        }

        fun arbreDe(c: String?): String? = c?.let { commit(it)?.optString("tree") }
        fun fichiersDe(c: String?): Map<String, String> = aplatir(arbreDe(c))

        fun ecrireCommit(arbre: String, parents: List<String>, auteur: String, committer: String, msg: String): String {
            val sb = StringBuilder("tree $arbre\n")
            for (p in parents) sb.append("parent $p\n")
            sb.append("author $auteur\ncommitter $committer\n\n").append(msg)
            val h = shaObjet("commit", sb.toString().toByteArray(Charsets.UTF_8))
            if (!objets.has(h)) objets.put(h, JSONObject().put("t", "commit").put("tree", arbre).put("parents", JSONArray(parents))
                .put("author", auteur).put("committer", committer).put("msg", msg))
            return h
        }

        fun corpsCommit(h: String): String {
            val c = commit(h) ?: return ""
            val sb = StringBuilder("tree ${c.optString("tree")}\n")
            for (p in parents(h)) sb.append("parent $p\n")
            return sb.append("author ${c.optString("author")}\ncommitter ${c.optString("committer")}\n\n").append(c.optString("msg")).toString()
        }

        // ------------------------------------------------ la copie de travail (les vrais fichiers du dossier)
        fun travail(): Map<String, File> {
            val out = java.util.TreeMap<String, File>()
            racine.walkTopDown().onEnter { it == racine || it.name != ".git" }.filter { it.isFile }.forEach {
                out[it.relativeTo(racine).path.replace(File.separatorChar, '/')] = it
            }
            return out
        }

        fun lire(p: String): String? = File(racine, p).let { if (it.isFile) try { it.readText() } catch (e: Exception) { null } else null }
        fun shaTravail(p: String): String? = File(racine, p).let { if (it.isFile) blobSha(it.readBytes()) else null }

        fun poser(p: String, blob: String?) {
            val f = File(racine, p)
            if (blob == null) { f.delete(); var d = f.parentFile; while (d != null && d != racine && (d.list()?.isEmpty() == true)) { d.delete(); d = d.parentFile }; return }
            f.parentFile?.mkdirs()
            f.writeText(blob(blob))
        }

        // ------------------------------------------------ .gitignore (motifs simples : *.tmp, nom, dossier/)
        fun ignore(p: String): Boolean {
            val motifs = (lire(".gitignore") ?: "").lines().map { it.trim() }.filter { it.isNotEmpty() && !it.startsWith("#") && !it.startsWith("!") }
            val nom = p.substringAfterLast('/')
            return motifs.any { m ->
                val re = glob(m.trimEnd('/').trimStart('/'))
                re.matches(nom) || re.matches(p) || p.split('/').dropLast(1).any { re.matches(it) }
            }
        }

        fun cfg(k: String): String? = config.optString(k).ifEmpty { null }
    }

    /** un motif de .gitignore (*, ?) en expression régulière */
    fun glob(m: String): Regex = Regex(m.map { c -> when (c) { '*' -> "[^/]*"; '?' -> "[^/]"; else -> if (c.isLetterOrDigit()) "$c" else "\\$c" } }.joinToString(""))

    // ================================================================ trouver le dépôt
    fun estDepot(d: File) = File(d, ".git/$FICHIER").isFile

    /** le dépôt du dossier ici (ou d'un dossier parent, sans sortir du terrain), ou null */
    fun trouver(ici: File, terrain: File): Depot? {
        var d: File? = ici.canonicalFile
        val t = terrain.canonicalFile
        while (d != null && (d.path == t.path || d.path.startsWith(t.path + File.separator))) {
            if (estDepot(d)) return Depot(d).charger()
            d = d.parentFile
        }
        return null
    }

    fun ouvrir(d: File): Depot? = if (estDepot(d)) Depot(d).charger() else null

    // ================================================================ les révisions : HEAD, HEAD~1, main, 6b4cd1e, X^, origin/main
    fun resoudre(dep: Depot, rev: String): String? {
        var r = rev.trim()
        if (r.endsWith("^{tree}")) return resoudre(dep, r.removeSuffix("^{tree}"))?.let { dep.arbreDe(it) }
        val m = Regex("^(.*?)((?:[~^]\\d*)*)$").find(r) ?: return null
        val base = m.groupValues[1]
        var h: String? = when {
            base == "HEAD" || base == "@" -> dep.head()
            base == "MERGE_HEAD" -> dep.fusion?.optString("tete")?.ifEmpty { null }
            base == "FETCH_HEAD" -> dep.j.optString("fetch_head").ifEmpty { null }
            dep.branches.has(base) -> dep.branches.getString(base)
            base.contains('/') && dep.remotes.has(base.substringBefore('/')) -> dep.remotes.getJSONObject(base.substringBefore('/'))
                .optJSONObject("refs")?.optString(base.substringAfter('/'))?.ifEmpty { null }
            base.length >= 4 && base.matches(Regex("[0-9a-fA-F]+")) -> dep.objets.keys().asSequence().filter { it.startsWith(base.lowercase()) }.toList()
                .let { if (it.size == 1) it[0] else null }
            else -> null
        } ?: return null
        for (s in Regex("[~^]\\d*").findAll(m.groupValues[2])) {
            val n = s.value.drop(1).ifEmpty { "1" }.toInt()
            if (s.value[0] == '~') repeat(n) { h = h?.let { dep.parents(it).firstOrNull() } }
            else h = if (n == 0) h else h?.let { dep.parents(it).getOrNull(n - 1) }
            if (h == null) return null
        }
        return h
    }

    // ================================================================ les différences (Myers, comme git)
    fun lignes(t: String): List<String> { if (t.isEmpty()) return emptyList(); val l = t.split("\n"); return if (t.endsWith("\n")) l.dropLast(1) else l }

    /** les paires (i, j) des lignes communes, dans l'ordre (diff de Myers, le plus court script d'édition) */
    fun communes(a: List<String>, b: List<String>): List<Pair<Int, Int>> {
        val n = a.size; val m = b.size; val max = n + m
        val v = IntArray(2 * max + 2); val traces = ArrayList<IntArray>()
        var fin = -1
        for (d in 0..max) {
            traces.add(v.copyOf())
            var k = -d
            while (k <= d) {
                var x = if (k == -d || (k != d && v[max + k - 1] < v[max + k + 1])) v[max + k + 1] else v[max + k - 1] + 1
                var y = x - k
                while (x < n && y < m && a[x] == b[y]) { x++; y++ }
                v[max + k] = x
                if (x >= n && y >= m) { fin = d; break }
                k += 2
            }
            if (fin >= 0) break
        }
        val paires = ArrayList<Pair<Int, Int>>()
        var x = n; var y = m
        for (d in fin downTo 1) {
            val vv = traces[d]
            val k = x - y
            val pk = if (k == -d || (k != d && vv[max + k - 1] < vv[max + k + 1])) k + 1 else k - 1
            val px = vv[max + pk]; val py = px - pk
            while (x > px && y > py) { x--; y--; paires.add(x to y) }
            x = px; y = py
        }
        while (x > 0 && y > 0) { x--; y--; paires.add(x to y) }
        return paires.reversed()
    }

    /** les blocs de changements : (début a, fin a, début b, fin b) (fins exclues) */
    private fun blocs(a: List<String>, b: List<String>): List<IntArray> {
        val out = ArrayList<IntArray>()
        var i = 0; var j = 0
        for ((x, y) in communes(a, b) + listOf(a.size to b.size)) {
            if (x > i || y > j) out.add(intArrayOf(i, x, j, y))
            i = x + 1; j = y + 1
        }
        return out
    }

    fun nbPlusMoins(a: String, b: String): Pair<Int, Int> {
        var p = 0; var mo = 0
        for (c in blocs(lignes(a), lignes(b))) { mo += c[1] - c[0]; p += c[3] - c[2] }
        return p to mo
    }

    private fun fonction(a: List<String>, avant: Int): String {
        for (i in avant - 1 downTo 0) if (a[i].isNotEmpty() && (a[i][0].isLetter() && a[i][0].code < 128 || a[i][0] == '_' || a[i][0] == '$'))
            return " " + a[i].trimEnd().let { if (it.length > 80) it.substring(0, 80) else it }
        return ""
    }

    /** le diff unifié de deux textes (3 lignes de contexte), sans les en-têtes de fichiers */
    fun unifie(ta: String, tb: String): List<String> {
        val a = lignes(ta); val b = lignes(tb)
        val cs = blocs(a, b)
        if (cs.isEmpty()) return emptyList()
        val out = ArrayList<String>()
        val ctx = 3
        var g = 0
        while (g < cs.size) {
            var h = g
            while (h + 1 < cs.size && cs[h + 1][0] - cs[h][1] <= 2 * ctx) h++
            val a0 = maxOf(0, cs[g][0] - ctx); val a1 = minOf(a.size, cs[h][1] + ctx)
            val b0 = cs[g][2] - (cs[g][0] - a0); val b1 = cs[h][3] + (a1 - cs[h][1])
            fun plage(s: Int, n: Int) = if (n == 1) "${s + 1}" else if (n == 0) "$s,0" else "${s + 1},$n"
            out.add("@@ -${plage(a0, a1 - a0)} +${plage(b0, b1 - b0)} @@" + fonction(a, a0))
            var i = a0; var jb = b0
            for (k in g..h) {
                val c = cs[k]
                while (i < c[0]) { out.add(" " + a[i]); i++; jb++ }
                for (x in c[0] until c[1]) { out.add("-" + a[x]); if (x == a.size - 1 && !ta.endsWith("\n")) out.add("\\ No newline at end of file") }
                for (y in c[2] until c[3]) { out.add("+" + b[y]); if (y == b.size - 1 && !tb.endsWith("\n")) out.add("\\ No newline at end of file") }
                i = c[1]; jb = c[3]
            }
            while (i < a1) { out.add(" " + a[i]); if (i == a.size - 1 && !ta.endsWith("\n") && !tb.endsWith("\n")) out.add("\\ No newline at end of file"); i++ }
            g = h + 1
        }
        return out
    }

    /** le diff git de deux listes {chemin: blob} (null : le fichier n'existe pas) */
    fun diffGit(dep: Depot, avant: Map<String, String>, apres: Map<String, String>, textesApres: Map<String, String>? = null): List<String> {
        val out = ArrayList<String>()
        for (p in (avant.keys + apres.keys).toSortedSet()) {
            val ha = avant[p]; val hb = apres[p]
            if (ha == hb) continue
            val ta = ha?.let { dep.blob(it) } ?: ""
            val tb = textesApres?.get(p) ?: hb?.let { dep.blob(it) } ?: ""
            out.add("diff --git a/$p b/$p")
            when {
                ha == null -> { out.add("new file mode 100644"); out.add("index 0000000..${hb!!.take(7)}") }
                hb == null -> { out.add("deleted file mode 100644"); out.add("index ${ha.take(7)}..0000000") }
                else -> out.add("index ${ha.take(7)}..${hb.take(7)} 100644")
            }
            val u = unifie(ta, tb)
            if (u.isNotEmpty()) { out.add(if (ha == null) "--- /dev/null" else "--- a/$p"); out.add(if (hb == null) "+++ /dev/null" else "+++ b/$p"); out.addAll(u) }
        }
        return out
    }

    /** « 1 file changed, 1 insertion(+) » et le diffstat (fichier | 1 +) */
    fun resume(fichiers: Int, plus: Int, moins: Int): String {
        val sb = StringBuilder(" $fichiers file${if (fichiers == 1) "" else "s"} changed")
        if (plus > 0 || moins == 0) sb.append(", $plus insertion${if (plus == 1) "" else "s"}(+)")
        if (moins > 0 || plus == 0) sb.append(", $moins deletion${if (moins == 1) "" else "s"}(-)")
        return sb.toString()
    }

    fun diffstat(dep: Depot, avant: Map<String, String>, apres: Map<String, String>, modes: Boolean): List<String> {
        val ch = (avant.keys + apres.keys).toSortedSet().filter { avant[it] != apres[it] }
        if (ch.isEmpty()) return emptyList()
        val nb = ch.associateWith { nbPlusMoins(avant[it]?.let { h -> dep.blob(h) } ?: "", apres[it]?.let { h -> dep.blob(h) } ?: "") }
        val large = ch.maxOf { it.length }
        val maxN = nb.values.maxOf { it.first + it.second }
        val lnum = "$maxN".length
        val place = maxOf(1, 79 - (large + 3 + lnum + 1) - 1)
        val out = ArrayList<String>()
        for (p in ch) {
            val (pl, mo) = nb[p]!!
            var a = pl; var b = mo
            if (maxN > place) { a = if (pl == 0) 0 else maxOf(1, pl * place / maxN); b = if (mo == 0) 0 else maxOf(1, mo * place / maxN) }
            out.add(" ${p.padEnd(large)} | ${"${pl + mo}".padStart(lnum)}" + (if (pl + mo > 0) " " + "+".repeat(a) + "-".repeat(b) else ""))
        }
        out.add(resume(ch.size, nb.values.sumOf { it.first }, nb.values.sumOf { it.second }))
        if (modes) for (p in ch) { if (avant[p] == null) out.add(" create mode 100644 $p"); if (apres[p] == null) out.add(" delete mode 100644 $p") }
        return out
    }

    // ================================================================ la fusion ligne à ligne (diff3, « zélée » comme git)
    class Fusion(val texte: String, val conflit: Boolean)

    fun fusionner(base: String, nous: String, eux: String, nomEux: String): Fusion {
        val o = lignes(base); val a = lignes(nous); val b = lignes(eux)
        class Bloc(val o0: Int, val o1: Int, val l: List<String>)
        fun changes(x: List<String>) = blocs(o, x).map { Bloc(it[0], it[1], x.subList(it[2], it[3])) }
        val ca = changes(a); val cb = changes(b)
        val tous = (ca.map { 0 to it } + cb.map { 1 to it }).sortedWith(compareBy({ it.second.o0 }, { it.second.o1 }))
        val out = ArrayList<String>()
        var conflit = false
        var i = 0; var pos = 0
        while (i < tous.size) {
            var j = i
            var fin = tous[i].second.o1
            // deux changements qui se chevauchent ou se touchent (même aux bords) forment un seul bloc, comme dans git
            while (j + 1 < tous.size && tous[j + 1].second.o0 <= fin) { j++; fin = maxOf(fin, tous[j].second.o1) }
            val debut = tous[i].second.o0
            while (pos < debut) { out.add(o[pos]); pos++ }
            val groupe = tous.subList(i, j + 1)
            fun cote(c: Int, lst: List<String>): List<String> {
                val bl = groupe.filter { it.first == c }.map { it.second }
                if (bl.isEmpty()) return o.subList(debut, fin)
                val r = ArrayList<String>(); var p = debut
                for (x in bl) { while (p < x.o0) { r.add(o[p]); p++ }; r.addAll(x.l); p = x.o1 }
                while (p < fin) { r.add(o[p]); p++ }
                return r
            }
            val va = cote(0, a); val vb = cote(1, b)
            if (va == vb || groupe.all { it.first == 0 }) out.addAll(va)
            else if (groupe.all { it.first == 1 }) out.addAll(vb)
            else {
                var d = 0
                while (d < va.size && d < vb.size && va[d] == vb[d]) d++
                var f = 0
                while (f < va.size - d && f < vb.size - d && va[va.size - 1 - f] == vb[vb.size - 1 - f]) f++
                out.addAll(va.subList(0, d))
                out.add("<<<<<<< HEAD"); out.addAll(va.subList(d, va.size - f)); out.add("======="); out.addAll(vb.subList(d, vb.size - f)); out.add(">>>>>>> $nomEux")
                out.addAll(va.subList(va.size - f, va.size))
                conflit = true
            }
            pos = fin
            i = j + 1
        }
        while (pos < o.size) { out.add(o[pos]); pos++ }
        return Fusion(if (out.isEmpty()) "" else out.joinToString("\n") + "\n", conflit)
    }

    // ================================================================ les commandes
    private fun hashCourt(h: String) = h.take(7)
    private fun sujet(dep: Depot, h: String) = dep.commit(h)?.optString("msg")?.lines()?.firstOrNull() ?: ""
    private fun ident(ts: Long, tz: Int, nom: String, mail: String): String {
        val s = if (tz < 0) "-" else "+"; val a = Math.abs(tz)
        return "$nom <$mail> $ts $s${"%02d%02d".format(a / 60, a % 60)}"
    }

    private fun dateGit(id: String): String {
        val m = Regex("> (\\d+) ([+-])(\\d\\d)(\\d\\d)$").find(id) ?: return ""
        val off = (m.groupValues[3].toInt() * 60 + m.groupValues[4].toInt()) * (if (m.groupValues[2] == "-") -1 else 1)
        val d = Instant.ofEpochSecond(m.groupValues[1].toLong()).atOffset(ZoneOffset.ofTotalSeconds(off * 60))
        return DateTimeFormatter.ofPattern("EEE MMM d HH:mm:ss yyyy", Locale.ENGLISH).format(d) + " ${m.groupValues[2]}${m.groupValues[3]}${m.groupValues[4]}"
    }

    private fun auteurNom(id: String) = id.substringBefore(" <")
    private fun auteurMail(id: String) = id.substringAfter("<").substringBefore(">")

    /** les décorations d'une photo : (HEAD -> main, origin/main, reve) */
    fun decorations(dep: Depot, h: String): String {
        val noms = ArrayList<String>()
        for (b in dep.branches.keys().asSequence().toSortedSet()) if (dep.branches.getString(b) == h) noms.add(b)
        for (r in dep.remotes.keys().asSequence().toSortedSet()) {
            val o = dep.remotes.getJSONObject(r)
            val refs = o.optJSONObject("refs") ?: JSONObject()
            val liste = (refs.keys().asSequence().map { it to refs.getString(it) } + listOfNotNull(o.optString("head").ifEmpty { null }?.let { "HEAD" to (refs.optString(it)) }))
                .sortedBy { it.first }
            for ((b, x) in liste) if (x == h) noms.add("$r/$b")
        }
        noms.reverse()
        val rh = dep.refHead()
        if (dep.head() == h) {
            if (rh != null) { noms.remove(rh); noms.add(0, "HEAD -> $rh") } else noms.add(0, "HEAD")
        }
        return if (noms.isEmpty()) "" else " (" + noms.joinToString(", ") + ")"
    }

    /** les photos depuis des points de départ, dans l'ordre de git log (date, puis ordre d'arrivée) */
    fun ordre(dep: Depot, departs: List<String>): List<String> {
        data class E(val h: String, val date: Long, val n: Int)
        var n = 0
        val vus = HashSet<String>()
        val file = java.util.PriorityQueue<E>(compareBy<E>({ -it.date }, { it.n }))
        fun date(h: String) = Regex("> (\\d+) ").find(dep.commit(h)?.optString("committer") ?: "")?.groupValues?.get(1)?.toLong() ?: 0L
        for (d in departs) if (vus.add(d)) file.add(E(d, date(d), n++))
        val out = ArrayList<String>()
        while (file.isNotEmpty()) {
            val e = file.poll()
            out.add(e.h)
            for (p in dep.parents(e.h)) if (vus.add(p)) file.add(E(p, date(p), n++))
        }
        return out
    }

    /** l'ordre « topologique » de git log --graph : les enfants avant les parents, le dernier parent d'une fusion d'abord */
    fun ordreGraphe(dep: Depot, departs: List<String>): List<String> {
        val tous = ordre(dep, departs)
        val enfants = HashMap<String, Int>()
        for (h in tous) for (p in dep.parents(h)) enfants[p] = (enfants[p] ?: 0) + 1
        val pile = ArrayList<String>()
        for (d in departs.distinct().reversed()) if ((enfants[d] ?: 0) == 0 && d !in pile) pile.add(d)
        val out = ArrayList<String>()
        while (pile.isNotEmpty()) {
            val h = pile.removeAt(pile.size - 1)
            out.add(h)
            for (p in dep.parents(h)) {
                enfants[p] = (enfants[p] ?: 1) - 1
                if (enfants[p] == 0) pile.add(p)
            }
        }
        return out
    }

    /** le dessin des chemins (git log --graph), fidèle pour une branche qui part et revient */
    fun graphe(dep: Depot, ordre: List<String>, texte: (String) -> List<String>): List<String> {
        val out = ArrayList<String>()
        val cols = ArrayList<String>()
        for (h in ordre) {
            var c = cols.indexOf(h)
            if (c < 0) { cols.add(h); c = cols.size - 1 }
            val ps = dep.parents(h)
            val tete = cols.indices.joinToString(" ") { if (it == c) "*" else "|" }
            val lignes = texte(h)
            if (ps.size > 1) {
                out.add("$tete   " + lignes[0])
                cols[c] = ps[0]
                cols.add(c + 1, ps[1])
                out.add("| ".repeat(c) + "|\\  ")
                for (l in lignes.drop(1)) out.add(cols.indices.joinToString(" ") { "|" } + (if (l.isEmpty()) "" else " $l"))
                continue
            }
            out.add("$tete " + lignes[0])
            for (l in lignes.drop(1)) out.add(cols.indices.joinToString(" ") { "|" } + (if (l.isEmpty()) "" else " $l"))
            if (ps.isEmpty()) { cols.removeAt(c); continue }
            cols[c] = ps[0]
            val autre = cols.indices.firstOrNull { it != c && cols[it] == ps[0] }
            if (autre != null) {                      // deux chemins arrivent à la même photo : ils se rejoignent
                val haut = maxOf(c, autre)
                out.add((0 until haut).joinToString(" ") { "|" } + "/" + "  " + (haut + 1 until cols.size).joinToString("") { " /" })
                cols.removeAt(haut)
            }
        }
        return out
    }

    // ------------------------------------------------ l'état du dossier (git status)
    class Etat(val prets: List<Pair<String, String>>, val pasPrets: List<Pair<String, String>>, val nonSuivis: List<String>, val conflits: List<String>)

    fun etat(dep: Depot): Etat {
        val tete = dep.fichiersDe(dep.head())
        val idx = dep.index.keys().asSequence().associateWith { dep.index.getString(it) }
        val conf = dep.conflits().toSet()
        val prets = ArrayList<Pair<String, String>>()
        for (p in (tete.keys + idx.keys).toSortedSet()) {
            if (p in conf) continue
            val a = tete[p]; val b = idx[p]
            if (a == null && b != null) prets.add("new file" to p) else if (a != null && b == null) prets.add("deleted" to p) else if (a != b) prets.add("modified" to p)
        }
        val pas = ArrayList<Pair<String, String>>()
        for (p in idx.keys.toSortedSet()) {
            if (p in conf) continue
            val s = dep.shaTravail(p)
            if (s == null) pas.add("deleted" to p) else if (s != idx[p]) pas.add("modified" to p)
        }
        val suivis = idx.keys
        val non = java.util.TreeSet<String>()
        for (p in dep.travail().keys) {
            if (p in suivis || dep.ignore(p)) continue
            val k = p.indexOf('/')
            if (k > 0 && suivis.none { it.startsWith(p.substring(0, k + 1)) }) non.add(p.substring(0, k + 1)) else non.add(p)
        }
        return Etat(prets, pas, non.toList(), conf.toSortedSet().toList())
    }

    private fun suivi(dep: Depot): List<String> {
        val b = dep.refHead() ?: return emptyList()
        val up = dep.amont.optString(b).ifEmpty { return emptyList() }
        val h = resoudre(dep, up) ?: return emptyList()
        val moi = dep.head() ?: return emptyList()
        val chezMoi = ordre(dep, listOf(moi)).toSet(); val chezEux = ordre(dep, listOf(h)).toSet()
        val avance = (chezMoi - chezEux).size; val retard = (chezEux - chezMoi).size
        return when {
            avance == 0 && retard == 0 -> listOf("Your branch is up to date with '$up'.")
            retard == 0 -> listOf("Your branch is ahead of '$up' by $avance commit${if (avance > 1) "s" else ""}.", "  (use \"git push\" to publish your local commits)")
            avance == 0 -> listOf("Your branch is behind '$up' by $retard commit${if (retard > 1) "s" else ""}, and can be fast-forwarded.", "  (use \"git pull\" to update your local branch)")
            else -> listOf("Your branch and '$up' have diverged,", "and have $avance and $retard different commits each, respectively.", "  (use \"git pull\" if you want to integrate the remote branch with yours)")
        }
    }

    fun status(dep: Depot, court: Boolean = false): String {
        val e = etat(dep)
        if (court) {
            val l = java.util.TreeMap<String, String>()
            for ((k, p) in e.prets) l[p] = (when (k) { "new file" -> "A"; "deleted" -> "D"; else -> "M" }) + " "
            for ((k, p) in e.pasPrets) l[p] = (l[p]?.take(1) ?: " ") + (if (k == "deleted") "D" else "M")
            for (p in e.conflits) l[p] = "UU"
            return (l.map { "${it.value} ${it.key}" } + e.nonSuivis.map { "?? $it" }).joinToString("\n")
        }
        val out = ArrayList<String>()
        val rh = dep.refHead()
        out.add(if (rh != null) "On branch $rh" else "HEAD detached at ${hashCourt(dep.head() ?: "")}")
        val s = suivi(dep)
        if (s.isNotEmpty()) { out.addAll(s); out.add("") }
        val initial = dep.head() == null
        if (initial) { out.add(""); out.add("No commits yet"); out.add("") }
        if (dep.fusion != null) {
            if (e.conflits.isNotEmpty()) out.addAll(listOf("You have unmerged paths.", "  (fix conflicts and run \"git commit\")", "  (use \"git merge --abort\" to abort the merge)", ""))
            else out.addAll(listOf("All conflicts fixed but you are still merging.", "  (use \"git commit\" to conclude merge)", ""))
        }
        fun ent(k: String, p: String) = "\t" + "$k:".padEnd(if (k.startsWith("both") || k.endsWith("by us") || k.endsWith("by them")) 17 else 12) + p
        if (e.prets.isNotEmpty()) {
            out.add("Changes to be committed:")
            out.add(if (initial) "  (use \"git rm --cached <file>...\" to unstage)" else "  (use \"git restore --staged <file>...\" to unstage)")
            for ((k, p) in e.prets) out.add(ent(k, p))
            out.add("")
        }
        if (e.conflits.isNotEmpty()) {
            out.add("Unmerged paths:"); out.add("  (use \"git add <file>...\" to mark resolution)")
            for (p in e.conflits) out.add(ent("both modified", p))
            out.add("")
        }
        if (e.pasPrets.isNotEmpty()) {
            out.add("Changes not staged for commit:")
            out.add(if (e.pasPrets.any { it.first == "deleted" }) "  (use \"git add/rm <file>...\" to update what will be committed)" else "  (use \"git add <file>...\" to update what will be committed)")
            out.add("  (use \"git restore <file>...\" to discard changes in working directory)")
            for ((k, p) in e.pasPrets) out.add(ent(k, p))
            out.add("")
        }
        if (e.nonSuivis.isNotEmpty()) {
            out.add("Untracked files:"); out.add("  (use \"git add <file>...\" to include in what will be committed)")
            for (p in e.nonSuivis) out.add("\t$p")
            out.add("")
        }
        if (e.prets.isEmpty()) out.add(when {
            e.pasPrets.isNotEmpty() || e.conflits.isNotEmpty() -> "no changes added to commit (use \"git add\" and/or \"git commit -a\")"
            e.nonSuivis.isNotEmpty() -> "nothing added to commit but untracked files present (use \"git add\" to track)"
            initial -> "nothing to commit (create/copy files and use \"git add\" to track)"
            else -> "nothing to commit, working tree clean"
        })
        while (out.isNotEmpty() && out.last().isEmpty()) out.removeAt(out.size - 1)
        return out.joinToString("\n")
    }

    // ------------------------------------------------ poser une photo dans le dossier (switch, checkout, merge, pull)
    /** les fichiers suivis qui seraient écrasés en passant de la photo a à la photo b */
    private fun ecrases(dep: Depot, a: String?, b: String?): List<String> {
        val fa = dep.fichiersDe(a); val fb = dep.fichiersDe(b)
        val idx = dep.index.keys().asSequence().associateWith { dep.index.getString(it) }
        return (fa.keys + fb.keys + idx.keys).toSortedSet().filter { p ->
            fa[p] != fb[p] && (idx[p] != fa[p] || (idx[p] != null && dep.shaTravail(p) != idx[p]) || (idx[p] == null && dep.shaTravail(p) != null && fb[p] != null))
        }
    }

    private fun allerA(dep: Depot, a: String?, b: String?) {
        val fa = dep.fichiersDe(a); val fb = dep.fichiersDe(b)
        for (p in (fa.keys + fb.keys)) if (fa[p] != fb[p]) {
            dep.poser(p, fb[p])
            if (fb[p] == null) dep.index.remove(p) else dep.index.put(p, fb[p])
        }
    }

    private fun modifiesGardes(dep: Depot): List<String> {
        val e = etat(dep)
        return (e.prets.map { it.second } + e.pasPrets.map { it.second }).toSortedSet().map { "M\t$it" }
    }

    private fun basculer(dep: Depot, cible: String?, branche: String?, nouvelle: Boolean, depuis: String): Res {
        val avant = dep.head()
        val bloque = ecrases(dep, avant, cible)
        if (bloque.isNotEmpty()) return Res("error: Your local changes to the following files would be overwritten by checkout:\n" +
            bloque.joinToString("\n") { "\t$it" } + "\nPlease commit your changes or stash them before you switch branches.\nAborting", 1)
        val etaitDetache = dep.refHead() == null
        val ancien = dep.refHead() ?: avant
        val gardes = modifiesGardes(dep)                 // (les fichiers modifiés suivent : M fichier, comme git)
        allerA(dep, avant, cible)
        val l = ArrayList<String>()
        if (etaitDetache && avant != null && avant != cible) l.add("Previous HEAD position was ${hashCourt(avant)} ${sujet(dep, avant)}")
        l.addAll(gardes)
        if (branche != null) {
            if (nouvelle) dep.branches.put(branche, cible ?: JSONObject.NULL)
            if (cible == null && nouvelle) dep.branches.remove(branche)
            l.add(if (nouvelle) "Switched to a new branch '$branche'" else if (dep.refHead() == branche) "Already on '$branche'" else "Switched to branch '$branche'")
            dep.j.put("head", JSONObject().put("ref", branche))
        } else {
            dep.j.put("head", JSONObject().put("detache", cible))
            l.add("Note: switching to '$depuis'.\n\nYou are in 'detached HEAD' state. You can look around, make experimental\nchanges and commit them, and you can discard any commits you make in this\n" +
                "state without impacting any branches by switching back to a branch.\n\nIf you want to create a new branch to retain commits you create, you may\n" +
                "do so (now or later) by using -c with the switch command. Example:\n\n  git switch -c <new-branch-name>\n\nOr undo this operation with:\n\n  git switch -\n\n" +
                "Turn off this advice by setting config variable advice.detachedHead to false\n\nHEAD is now at ${hashCourt(cible ?: "")} ${sujet(dep, cible ?: "")}")
        }
        if (ancien != null) dep.j.put("precedent", ancien)
        dep.sauver()
        return Res(l.joinToString("\n"))
    }

    // ------------------------------------------------ la photo (commit)
    private fun identite(dep: Depot): Res? {
        if (dep.cfg("user.email") != null && dep.cfg("user.name") != null) return null
        return Res("Author identity unknown\n\n*** Please tell me who you are.\n\nRun\n\n  git config --global user.email \"you@example.com\"\n" +
            "  git config --global user.name \"Your Name\"\n\nto set your account's default identity.\nOmit --global to set the identity only in this repository.\n\n" +
            "fatal: no ${if (dep.cfg("user.email") == null) "email" else "name"} was given and auto-detection is disabled", 128)
    }

    /** une photo de l'index ; renvoie (empreinte, sortie) — utilisé par commit, merge, et par le jeu (le grimoire) */
    fun photographier(dep: Depot, msg: String, parents: List<String>, auteur: Pair<String, String>? = null, quand: Pair<Long, Int>? = null): String {
        val (ts, tz) = quand ?: horloge()
        val nom = auteur?.first ?: dep.cfg("user.name")!!
        val mail = auteur?.second ?: dep.cfg("user.email")!!
        val id = ident(ts, tz, nom, mail)
        val arbre = dep.ecrireArbre(dep.index.keys().asSequence().associateWith { dep.index.getString(it) })
        val h = dep.ecrireCommit(arbre, parents, id, id, msg)
        val rh = dep.refHead()
        if (rh != null) dep.branches.put(rh, h) else dep.j.put("head", JSONObject().put("detache", h))
        return h
    }

    private fun nettoyerMessage(ms: List<String>): String {
        val t = ms.joinToString("\n\n").lines().map { it.trimEnd() }.dropWhile { it.isEmpty() }.dropLastWhile { it.isEmpty() }
        return if (t.isEmpty()) "" else t.joinToString("\n") + "\n"
    }

    private fun stage(dep: Depot, p: String) {
        val f = File(dep.racine, p)
        if (f.isFile) dep.index.put(p, dep.ajouterBlob(f.readText())) else dep.index.remove(p)
        val c = dep.conflits()
        if (p in c) dep.fusion?.put("conflits", JSONArray(c - p))
    }

    fun commit(dep: Depot, args: List<String>): Res {
        val msgs = ArrayList<String>(); var tout = false; var calme = false; var vide = false
        var i = 0
        while (i < args.size) {
            val a = args[i]
            when {
                a == "--message" || a == "-m" -> { msgs.add(args.getOrNull(i + 1) ?: return Res("error: switch `m' requires a value", 129)); i++ }
                a.startsWith("--message=") -> msgs.add(a.substringAfter("="))
                a == "--all" -> tout = true
                a == "--quiet" -> calme = true
                a == "--allow-empty" -> vide = true
                a.startsWith("-") && !a.startsWith("--") && a.length > 1 -> {
                    var k = 1
                    while (k < a.length) {
                        when (a[k]) {
                            'a' -> tout = true
                            'q' -> calme = true
                            'm' -> { val r = a.substring(k + 1); if (r.isNotEmpty()) msgs.add(r) else { msgs.add(args.getOrNull(i + 1) ?: return Res("error: switch `m' requires a value", 129)); i++ }; k = a.length }
                            else -> return Res("error: unknown switch `${a[k]}'", 129)
                        }
                        k++
                    }
                }
                else -> return Res(t("tp.tel.git"), 1)
            }
            i++
        }
        if (tout) {
            for (p in dep.index.keys().asSequence().toList()) stage(dep, p)
            for (p in dep.conflits()) stage(dep, p)
        }
        if (dep.conflits().isNotEmpty()) return Res("error: Committing is not possible because you have unmerged files.\nhint: Fix them up in the work tree, and then use 'git add/rm <file>'\n" +
            "hint: as appropriate to mark resolution and make a commit.\nfatal: Exiting because of an unresolved conflict.", 128)
        val fusion = dep.fusion
        val msg = nettoyerMessage(msgs).ifEmpty { fusion?.optString("msg")?.let { "$it\n" } ?: "" }
        if (msg.isEmpty()) return Res(t("tp.tel.editeur"), 1)
        val tete = dep.head()
        val arbre = dep.ecrireArbre(dep.index.keys().asSequence().associateWith { dep.index.getString(it) })
        if (fusion == null && !vide && arbre == (dep.arbreDe(tete) ?: VIDE)) { dep.sauver(); return Res(status(dep), 1) }
        identite(dep)?.let { dep.sauver(); return it }
        val parents = listOfNotNull(tete) + listOfNotNull(fusion?.optString("tete")?.ifEmpty { null })
        val avant = dep.fichiersDe(tete)
        val h = photographier(dep, msg, parents)
        dep.j.remove("fusion")
        dep.sauver()
        if (calme) return Res("")
        val ou = dep.refHead() ?: "detached HEAD"
        val l = arrayListOf("[$ou${if (tete == null) " (root-commit)" else ""} ${hashCourt(h)}] ${msg.lines().first()}")
        if (fusion == null) l.addAll(diffstat(dep, avant, dep.fichiersDe(h), true).filter { it.startsWith(" ") && !it.contains(" | ") })
        return Res(l.joinToString("\n"))
    }

    // ------------------------------------------------ log, show
    private fun enTete(dep: Depot, h: String, deco: Boolean): List<String> {
        val c = dep.commit(h)!!
        val l = arrayListOf("commit $h" + (if (deco) decorations(dep, h) else ""))
        val ps = dep.parents(h)
        if (ps.size > 1) l.add("Merge: " + ps.joinToString(" ") { hashCourt(it) })
        val a = c.optString("author")
        l.add("Author: ${auteurNom(a)} <${auteurMail(a)}>")
        l.add("Date:   ${dateGit(a)}")
        l.add("")
        for (m in c.optString("msg").trimEnd('\n').lines()) l.add(if (m.isEmpty()) "" else "    $m")
        return l
    }

    private fun compte(t: String, s: String): Int { if (s.isEmpty()) return 0; var n = 0; var k = t.indexOf(s); while (k >= 0) { n++; k = t.indexOf(s, k + s.length) }; return n }

    fun log(dep: Depot, args: List<String>): Res {
        var uneLigne = false; var graphe = false; var cherche: String? = null; var max = Int.MAX_VALUE; var patch = false; var tous = false
        val revs = ArrayList<String>()
        var i = 0
        while (i < args.size) {
            val a = args[i]
            when {
                a == "--oneline" -> uneLigne = true
                a == "--graph" -> graphe = true
                a == "--all" -> tous = true
                a == "-p" || a == "--patch" -> patch = true
                a == "--decorate" || a == "--no-decorate" || a == "--" -> {}
                a == "-S" -> { cherche = args.getOrNull(i + 1); i++ }
                a.startsWith("-S") -> cherche = a.substring(2)
                a == "-n" -> { max = args.getOrNull(i + 1)?.toIntOrNull() ?: max; i++ }
                a.startsWith("--max-count=") -> max = a.substringAfter("=").toIntOrNull() ?: max
                a.matches(Regex("-\\d+")) -> max = a.drop(1).toInt()
                a.startsWith("-") -> return Res("${t("tp.tel.inconnu", "cmd" to "log $a")}", 1)
                else -> revs.add(a)
            }
            i++
        }
        val departs = if (tous) (listOfNotNull(dep.head()) + dep.branches.keys().asSequence().toSortedSet().map { dep.branches.getString(it) }).distinct()
            else if (revs.isEmpty()) listOfNotNull(dep.head())
            else revs.map { resoudre(dep, it) ?: return Res("fatal: ambiguous argument '$it': unknown revision or path not in the working tree.\n" +
                "Use '--' to separate paths from revisions, like this:\n'git <command> [<revision>...] -- [<file>...]'", 128) }
        if (departs.isEmpty()) return Res("fatal: your current branch '${dep.refHead() ?: "master"}' does not have any commits yet", 128)
        var liste = if (graphe) ordreGraphe(dep, departs) else ordre(dep, departs)
        cherche?.let { s -> liste = liste.filter { h ->
            val ps = dep.parents(h)
            if (ps.size > 1) false else {
                val a = dep.fichiersDe(ps.firstOrNull()); val b = dep.fichiersDe(h)
                (a.keys + b.keys).any { p -> a[p] != b[p] && compte(a[p]?.let { x -> dep.blob(x) } ?: "", s) != compte(b[p]?.let { x -> dep.blob(x) } ?: "", s) }
            } } }
        liste = liste.take(max)
        fun texte(h: String): List<String> {
            val l = if (uneLigne) arrayListOf("${hashCourt(h)}${decorations(dep, h)} ${sujet(dep, h)}") else ArrayList(enTete(dep, h, true))
            if (patch && dep.parents(h).size <= 1) { val d = diffGit(dep, dep.fichiersDe(dep.parents(h).firstOrNull()), dep.fichiersDe(h)); if (d.isNotEmpty()) { if (!uneLigne) l.add(""); l.addAll(d) } }
            return l
        }
        if (graphe) {
            val g = graphe(dep, liste) { h -> texte(h).let { t -> if (uneLigne) t else t + "" } }
            return Res(g.joinToString("\n").trimEnd())
        }
        return Res(liste.joinToString(if (uneLigne) "\n" else "\n\n") { texte(it).joinToString("\n") })
    }

    fun show(dep: Depot, args: List<String>): Res {
        val stat = "--stat" in args
        val revs = args.filter { !it.startsWith("--") }
        val rev = revs.firstOrNull() ?: "HEAD"
        if (rev.contains(':')) {
            val h = resoudre(dep, rev.substringBefore(':').ifEmpty { "HEAD" }) ?: return Res("fatal: invalid object name '${rev.substringBefore(':')}'.", 128)
            val b = dep.fichiersDe(h)[rev.substringAfter(':')] ?: return Res("fatal: path '${rev.substringAfter(':')}' does not exist in '${rev.substringBefore(':')}'", 128)
            return Res(dep.blob(b).trimEnd('\n'))
        }
        val h = resoudre(dep, rev) ?: return Res("fatal: ambiguous argument '$rev': unknown revision or path not in the working tree.\n" +
            "Use '--' to separate paths from revisions, like this:\n'git <command> [<revision>...] -- [<file>...]'", 128)
        val c = dep.commit(h) ?: return Res(dep.blob(h).trimEnd('\n'))
        val l = ArrayList(enTete(dep, h, true))
        val ps = dep.parents(h)
        if (ps.size <= 1) {
            val a = dep.fichiersDe(ps.firstOrNull()); val b = dep.fichiersDe(h)
            val d = if (stat) diffstat(dep, a, b, false) else diffGit(dep, a, b)
            if (d.isNotEmpty()) { l.add(""); l.addAll(d) }
        }
        return Res(l.joinToString("\n"))
    }

    fun diff(dep: Depot, args: List<String>): Res {
        val staged = args.any { it == "--staged" || it == "--cached" }
        val chemins = args.filter { !it.startsWith("-") }
        val idx = dep.index.keys().asSequence().associateWith { dep.index.getString(it) }
        fun garde(m: Map<String, String>) = if (chemins.isEmpty() || chemins == listOf(".")) m else m.filterKeys { k -> chemins.any { k == it || k.startsWith(it.trimEnd('/') + "/") } }
        if (staged) return Res(diffGit(dep, garde(dep.fichiersDe(dep.head())), garde(idx)).joinToString("\n"))
        val conf = dep.conflits().toSet()
        val travail = HashMap<String, String>(); val textes = HashMap<String, String>()
        for (p in idx.keys) {
            if (p in conf) continue
            val f = File(dep.racine, p)
            if (f.isFile) { val t = f.readText(); travail[p] = blobSha(t); textes[p] = t }
        }
        return Res(diffGit(dep, garde(idx.filterKeys { it !in conf }), garde(travail), textes).joinToString("\n"))
    }

    // ------------------------------------------------ restore, checkout, switch, branch
    private fun cheminsSuivis(dep: Depot, chemins: List<String>, source: Map<String, String>): List<String>? {
        val tous = (source.keys + dep.index.keys().asSequence()).toSortedSet()
        val out = ArrayList<String>()
        for (c in chemins) {
            val m = if (c == ".") tous.toList() else tous.filter { it == c || it.startsWith(c.trimEnd('/') + "/") }
            if (m.isEmpty()) return null
            out.addAll(m)
        }
        return out.distinct()
    }

    fun restore(dep: Depot, args: List<String>): Res {
        var source: String? = null; var staged = false; var travail = false
        val chemins = ArrayList<String>()
        var i = 0
        while (i < args.size) {
            val a = args[i]
            when {
                a.startsWith("--source=") -> source = a.substringAfter("=")
                a == "--source" || a == "-s" -> { source = args.getOrNull(i + 1); i++ }
                a == "--staged" || a == "-S" -> staged = true
                a == "--worktree" || a == "-W" -> travail = true
                a == "--" -> {}
                a.startsWith("-") -> return Res(t("tp.tel.inconnu", "cmd" to "restore $a"), 1)
                else -> chemins.add(a)
            }
            i++
        }
        if (chemins.isEmpty()) return Res("fatal: you must specify path(s) to restore", 128)
        if (!staged) travail = true
        val src = when {
            source != null -> resoudre(dep, source)?.let { dep.fichiersDe(it) } ?: return Res("fatal: could not resolve $source", 128)
            staged -> dep.fichiersDe(dep.head())
            else -> dep.index.keys().asSequence().associateWith { dep.index.getString(it) }
        }
        val liste = cheminsSuivis(dep, chemins, src) ?: return Res("error: pathspec '${chemins.first { cheminsSuivis(dep, listOf(it), src) == null }}' did not match any file(s) known to git", 1)
        for (p in liste) {
            if (staged) { if (src[p] == null) dep.index.remove(p) else dep.index.put(p, src[p]) }
            if (travail) dep.poser(p, src[p])
        }
        dep.sauver()
        return Res("")
    }

    fun switch(dep: Depot, args: List<String>, checkout: Boolean): Res {
        val creer = args.indexOfFirst { it == "-c" || it == "-b" || it == "--create" }
        if (creer >= 0) {
            val nom = args.getOrNull(creer + 1) ?: return Res("error: switch `${args[creer].trimStart('-')}' requires a value", 129)
            if (dep.branches.has(nom)) return Res("fatal: a branch named '$nom' already exists", 128)
            if (!nomValide(nom)) return Res("fatal: '$nom' is not a valid branch name", 128)
            val depart = args.filterIndexed { k, x -> k != creer && k != creer + 1 && !x.startsWith("-") }.firstOrNull()
            val cible = if (depart != null) resoudre(dep, depart) ?: return Res("fatal: invalid reference: $depart", 128) else dep.head()
            if (dep.head() == null && depart == null) { dep.j.put("head", JSONObject().put("ref", nom)); dep.sauver(); return Res("Switched to a new branch '$nom'") }
            return basculer(dep, cible, nom, true, nom)
        }
        val reste = args.filter { it != "--detach" && it != "-d" }
        val nom = reste.firstOrNull() ?: return Res("fatal: missing branch or commit argument", 128)
        val voulu = if (nom == "-") dep.j.optString("precedent").ifEmpty { return Res("fatal: invalid reference: @{-1}", 128) } else nom
        if (dep.branches.has(voulu)) return basculer(dep, dep.branches.getString(voulu), voulu, false, voulu)
        // origin/main → une branche locale qui suit (comme git switch main dans un clone)
        for (r in dep.remotes.keys()) {
            val ref = dep.remotes.getJSONObject(r).optJSONObject("refs")?.optString(voulu)?.ifEmpty { null }
            if (ref != null) { dep.amont.put(voulu, "$r/$voulu"); val b = basculer(dep, ref, voulu, true, voulu); return Res("branch '$voulu' set up to track '$r/$voulu'.\n" + b.texte, b.code) }
        }
        val h = resoudre(dep, voulu)
        if (h != null && dep.commit(h) != null) {
            if (!checkout && "--detach" !in args && "-d" !in args) return Res("fatal: a branch is expected, got commit '$voulu'\nhint: If you want to detach HEAD at the commit, try again with the --detach option.", 128)
            return basculer(dep, h, null, false, voulu)
        }
        return Res(if (checkout) "error: pathspec '$voulu' did not match any file(s) known to git" else "fatal: invalid reference: $voulu", if (checkout) 1 else 128)
    }

    private fun nomValide(n: String) = n.isNotEmpty() && !n.startsWith("-") && !n.contains("..") && n.none { it.isWhitespace() || it in "~^:?*[\\" } && !n.endsWith("/") && !n.endsWith(".lock")

    fun checkout(dep: Depot, args: List<String>): Res {
        val k = args.indexOf("--")
        if (k >= 0) {
            val avant = args.subList(0, k).filter { !it.startsWith("-") }
            val chemins = args.subList(k + 1, args.size)
            if (avant.isEmpty()) return restore(dep, chemins)
            val h = resoudre(dep, avant[0]) ?: return Res("fatal: invalid reference: ${avant[0]}", 128)
            val src = dep.fichiersDe(h)
            val liste = cheminsSuivis(dep, chemins, src)?.filter { src.containsKey(it) }?.takeIf { it.isNotEmpty() }
                ?: return Res("error: pathspec '${chemins.firstOrNull()}' did not match any file(s) known to git", 1)
            for (p in liste) { dep.index.put(p, src[p]); dep.poser(p, src[p]) }
            dep.sauver()
            return Res("")
        }
        if (args.any { it == "-b" || it == "-B" }) return switch(dep, args.map { if (it == "-B") "-b" else it }, true)
        val nom = args.firstOrNull { !it.startsWith("-") || it == "-" } ?: return Res("", 0)
        if (args.size >= 2 && resoudre(dep, nom) != null && args.drop(1).all { File(dep.racine, it).exists() || dep.index.has(it) })
            return checkout(dep, listOf(nom, "--") + args.drop(1))
        if (!dep.branches.has(nom) && nom != "-" && resoudre(dep, nom) == null && (File(dep.racine, nom).exists() || dep.index.has(nom))) return restore(dep, args)
        return switch(dep, args, true)
    }

    fun branch(dep: Depot, args: List<String>): Res {
        val noms = args.filter { !it.startsWith("-") }
        if (args.any { it == "-d" || it == "-D" || it == "-m" || it == "-M" }) return Res(t("tp.tel.inconnu", "cmd" to "branch " + args.joinToString(" ")), 1)
        if (noms.isEmpty()) {
            val l = ArrayList<String>()
            if (dep.refHead() == null && dep.head() != null) l.add("* (HEAD detached at ${hashCourt(dep.head()!!)})")
            for (b in dep.branches.keys().asSequence().toSortedSet()) l.add((if (b == dep.refHead()) "* " else "  ") + b)
            return Res(l.joinToString("\n"))
        }
        val nom = noms[0]
        if (dep.branches.has(nom)) return Res("fatal: a branch named '$nom' already exists", 128)
        if (!nomValide(nom)) return Res("fatal: '$nom' is not a valid branch name", 128)
        val h = (noms.getOrNull(1)?.let { resoudre(dep, it) ?: return Res("fatal: not a valid object name: '$it'", 128) } ?: dep.head())
            ?: return Res("fatal: not a valid object name: '${dep.refHead() ?: "HEAD"}'", 128)
        dep.branches.put(nom, h)
        dep.sauver()
        return Res("")
    }

    // ------------------------------------------------ merge, clone, pull
    fun ancetres(dep: Depot, h: String): Set<String> = ordre(dep, listOf(h)).toSet()

    fun base(dep: Depot, a: String, b: String): String? {
        val la = ancetres(dep, a)
        return ordre(dep, listOf(b)).firstOrNull { it in la }
    }

    fun merge(dep: Depot, args: List<String>, autre: String? = null, nomAutre: String? = null, avantTexte: String = ""): Res {
        if ("--abort" in args) {
            val f = dep.fusion ?: return Res("fatal: There is no merge to abort (MERGE_HEAD missing).", 128)
            val tete = dep.head()
            for (p in dep.travail().keys.filter { it in dep.fichiersDe(tete) || dep.index.has(it) }) dep.poser(p, dep.fichiersDe(tete)[p])
            dep.index.let { i -> i.keys().asSequence().toList().forEach { i.remove(it) } }
            for ((p, x) in dep.fichiersDe(tete)) { dep.index.put(p, x); dep.poser(p, x) }
            dep.j.remove("fusion"); dep.sauver()
            if (f.length() < 0) return Res("")
            return Res("")
        }
        if (dep.fusion != null) return Res("error: Merging is not possible because you have unmerged files.\nhint: Fix them up in the work tree, and then use 'git add/rm <file>'\n" +
            "hint: as appropriate to mark resolution and make a commit.\nfatal: Exiting because of an unresolved conflict.", 128)
        val nom = nomAutre ?: args.firstOrNull { !it.startsWith("-") } ?: return Res("fatal: No remote for the current branch.", 128)
        val eux = autre ?: resoudre(dep, nom) ?: return Res("merge: $nom - not something we can merge", 1)
        val nous = dep.head()
        val l = ArrayList<String>()
        if (avantTexte.isNotEmpty()) l.add(avantTexte)
        if (nous == null) {                                  // une branche sans photo : on prend tout
            allerA(dep, null, eux); dep.branches.put(dep.refHead() ?: "master", eux); dep.sauver()
            return Res((l + listOf("Fast-forward")).joinToString("\n"))
        }
        if (eux in ancetres(dep, nous)) return Res((l + "Already up to date.").joinToString("\n"))
        val bloque = ecrases(dep, nous, eux)
        if (bloque.isNotEmpty()) return Res((l + ("error: Your local changes to the following files would be overwritten by merge:\n" + bloque.joinToString("\n") { "\t$it" } +
            "\nPlease commit your changes or stash them before you merge.\nAborting")).joinToString("\n"), 1)
        if (nous in ancetres(dep, eux)) {                    // l'avance rapide
            val a = dep.fichiersDe(nous); val b = dep.fichiersDe(eux)
            allerA(dep, nous, eux)
            val rh = dep.refHead()
            if (rh != null) dep.branches.put(rh, eux) else dep.j.put("head", JSONObject().put("detache", eux))
            dep.sauver()
            l.add("Updating ${hashCourt(nous)}..${hashCourt(eux)}"); l.add("Fast-forward"); l.addAll(diffstat(dep, a, b, true))
            return Res(l.joinToString("\n"))
        }
        if (autre != null && nomAutre != null && nomAutre.startsWith("pull:")) {
            return Res((l + listOf("hint: You have divergent branches and need to specify how to reconcile them.", "hint: You can do so by running one of the following commands sometime before",
                "hint: your next pull:", "hint:", "hint:   git config pull.rebase false  # merge", "hint:   git config pull.rebase true   # rebase",
                "hint:   git config pull.ff only       # fast-forward only", "hint:", "hint: You can replace \"git config\" with \"git config --global\" to set a default",
                "hint: preference for all repositories. You can also pass --rebase, --no-rebase,", "hint: or --ff-only on the command line to override the configured default per",
                "hint: invocation.", "fatal: Need to specify how to reconcile divergent branches.")).joinToString("\n"), 128)
        }
        val b0 = base(dep, nous, eux)
        val fb = dep.fichiersDe(b0); val fa = dep.fichiersDe(nous); val fe = dep.fichiersDe(eux)
        val conflits = ArrayList<String>()
        val etiquette = nomAutre?.removePrefix("pull:") ?: nom
        for (p in (fb.keys + fa.keys + fe.keys).toSortedSet()) {
            val o = fb[p]; val a = fa[p]; val e = fe[p]
            when {
                a == e -> {}
                o == a -> { dep.poser(p, e); if (e == null) dep.index.remove(p) else dep.index.put(p, e) }
                o == e -> {}
                a == null || e == null -> {
                    l.add("CONFLICT (modify/delete): $p deleted in ${if (a == null) "HEAD" else etiquette} and modified in ${if (a == null) etiquette else "HEAD"}.  Version ${if (a == null) etiquette else "HEAD"} of $p left in tree.")
                    if (a == null) dep.poser(p, e)
                    conflits.add(p)
                }
                else -> {
                    l.add("Auto-merging $p")
                    val r = fusionner(o?.let { dep.blob(it) } ?: "", dep.blob(a), dep.blob(e), etiquette)
                    File(dep.racine, p).apply { parentFile?.mkdirs() }.writeText(r.texte)
                    if (r.conflit) { l.add("CONFLICT (${if (o == null) "add/add" else "content"}): Merge conflict in $p"); conflits.add(p) }
                    else dep.index.put(p, dep.ajouterBlob(r.texte))
                }
            }
        }
        val rh = dep.refHead()
        val msg = if (nomAutre != null && nomAutre.startsWith("pull:")) "Merge branch '${etiquette}'" else "Merge branch '$etiquette'" + (if (rh != null && rh !in setOf("main", "master")) " into $rh" else "")
        if (conflits.isNotEmpty()) {
            dep.j.put("fusion", JSONObject().put("tete", eux).put("msg", msg).put("conflits", JSONArray(conflits)))
            dep.sauver()
            l.add("Automatic merge failed; fix conflicts and then commit the result.")
            return Res(l.joinToString("\n"), 1)
        }
        identite(dep)?.let { dep.sauver(); return Res((l + it.texte).joinToString("\n"), it.code) }
        val h = photographier(dep, "$msg\n", listOf(nous, eux))
        dep.sauver()
        l.removeAll { it.startsWith("Auto-merging") }
        l.add("Merge made by the 'ort' strategy."); l.addAll(diffstat(dep, fa, dep.fichiersDe(h), true))
        return Res(l.joinToString("\n"))
    }

    fun clone(ici: File, terrain: File, args: List<String>): Res {
        val mots = args.filter { !it.startsWith("-") }
        val src = mots.getOrNull(0) ?: return Res("fatal: You must specify a repository to clone.", 129)
        if (src.contains("://") || src.contains("@")) return Res(t("tp.tel.push"), 1)
        val fs = File(src).let { if (it.isAbsolute) it else File(ici, src) }
        val srcDep = ouvrir(fs.canonicalFile) ?: return Res("fatal: repository '$src' does not exist", 128)
        val nomDest = mots.getOrNull(1) ?: fs.canonicalFile.name.removeSuffix(".git")
        val fd = File(nomDest).let { if (it.isAbsolute) it else File(ici, nomDest) }.canonicalFile
        if (!(fd.path + File.separator).startsWith(terrain.canonicalPath + File.separator)) return Res(t("tp.tel.hors_terrain"), 1)
        if (fd.exists() && (fd.list()?.isNotEmpty() == true)) return Res("fatal: destination path '$nomDest' already exists and is not an empty directory.", 128)
        val d = Depot(fd).charger()
        d.j.put("objets", JSONObject(srcDep.objets.toString()))
        val refs = JSONObject()
        for (b in srcDep.branches.keys()) refs.put(b, srcDep.branches.getString(b))
        val tete = srcDep.refHead()
        d.remotes.put("origin", JSONObject().put("url", fs.path).put("refs", refs).put("head", tete ?: ""))
        if (tete != null && srcDep.head() != null) {
            d.branches.put(tete, srcDep.head()); d.j.put("head", JSONObject().put("ref", tete)); d.amont.put(tete, "origin/$tete")
            allerA(d, null, srcDep.head())
        }
        d.sauver()
        return Res("Cloning into '$nomDest'...\ndone.")
    }

    fun pull(dep: Depot, ici: File, args: List<String>): Res {
        val mots = args.filter { !it.startsWith("-") }
        val depot = mots.getOrNull(0)
        val url: String
        val nomRemote: String?
        if (depot == null) {
            val b = dep.refHead()
            val up = b?.let { dep.amont.optString(it).ifEmpty { null } } ?: return Res("There is no tracking information for the current branch.\nPlease specify which branch you want to merge with.\n" +
                "See git-pull(1) for details.\n\n    git pull <remote> <branch>\n\nIf you wish to set tracking information for this branch you can do so with:\n\n" +
                "    git branch --set-upstream-to=<remote>/<branch> ${b ?: "main"}\n", 1)
            nomRemote = up.substringBefore('/')
            url = dep.remotes.getJSONObject(nomRemote).optString("url")
        } else if (dep.remotes.has(depot)) { nomRemote = depot; url = dep.remotes.getJSONObject(depot).optString("url") }
        else { nomRemote = null; url = depot }
        if (url.contains("://") || url.contains("@")) return Res(t("tp.tel.push"), 1)
        val f = File(url).let { if (it.isAbsolute) it else File(ici, url) }
        val autre = ouvrir(f.canonicalFile) ?: return Res("fatal: '$url' does not appear to be a git repository\nfatal: Could not read from remote repository.\n\n" +
            "Please make sure you have the correct access rights\nand the repository exists.", 128)
        val ref = mots.getOrNull(1)
        val h = (if (ref != null) autre.branches.optString(ref).ifEmpty { null } else if (nomRemote != null && depot == null) autre.branches.optString(dep.amont.optString(dep.refHead() ?: "").substringAfter('/')).ifEmpty { null } else autre.head())
            ?: return Res("fatal: couldn't find remote ref ${ref ?: "HEAD"}", 1)
        for (k in autre.objets.keys()) if (!dep.objets.has(k)) dep.objets.put(k, autre.objets.getJSONObject(k))
        dep.j.put("fetch_head", h)
        val montre = if (nomRemote != null) afficher(url) else url
        val qui = ref ?: if (nomRemote != null && depot == null) dep.amont.optString(dep.refHead() ?: "").substringAfter('/') else "HEAD"
        if (nomRemote != null) {
            val o = dep.remotes.getJSONObject(nomRemote)
            val refs = o.optJSONObject("refs") ?: JSONObject().also { o.put("refs", it) }
            for (b in autre.branches.keys()) refs.put(b, autre.branches.getString(b))
        }
        val tete = "From $montre\n * branch            ${qui.padEnd(10)} -> FETCH_HEAD"
        return merge(dep, emptyList(), h, "pull:$qui", tete)
    }

    // ------------------------------------------------ config, cat-file, hash-object, remote
    fun config(dep: Depot?, args: List<String>): Res {
        if (args.any { it == "--global" || it == "--system" }) return Res(t("tp.tel.global"), 1)
        val a = args.filter { it != "--local" }
        if (dep == null) return Res("fatal: not in a git directory", 128)
        if (a.firstOrNull() == "--list" || a.firstOrNull() == "-l") return Res(dep.config.keys().asSequence().toList().joinToString("\n") { "$it=${dep.config.getString(it)}" })
        if (a.firstOrNull() == "--unset") { a.getOrNull(1)?.let { dep.config.remove(it) }; dep.sauver(); return Res("") }
        val cle = a.getOrNull(0) ?: return Res("error: no action specified", 2)
        if (!cle.contains('.')) return Res("error: key does not contain a section: $cle", 2)
        if (a.size == 1) return dep.cfg(cle)?.let { Res(it) } ?: Res("", 1)
        dep.config.put(cle, a.drop(1).joinToString(" "))
        dep.sauver()
        return Res("")
    }

    fun catFile(dep: Depot, args: List<String>): Res {
        val opt = args.firstOrNull { it.startsWith("-") } ?: return Res("usage: git cat-file (-t | -s | -e | -p) <object>", 129)
        val rev = args.firstOrNull { !it.startsWith("-") } ?: return Res("usage: git cat-file (-t | -s | -e | -p) <object>", 129)
        val h = resoudre(dep, rev) ?: return Res("fatal: Not a valid object name $rev", 128)
        val o = dep.objet(h) ?: return Res("fatal: Not a valid object name $rev", 128)
        val ty = o.optString("t")
        return when (opt) {
            "-t" -> Res(ty)
            "-p" -> Res(when (ty) {
                "commit" -> dep.corpsCommit(h).trimEnd('\n')
                "tree" -> { val e = o.getJSONArray("e"); (0 until e.length()).joinToString("\n") { val x = e.getJSONArray(it)
                    (if (x.getString(0) == "40000") "040000 tree " else "100644 blob ") + x.getString(2) + "\t" + x.getString(1) } }
                else -> o.optString("c").trimEnd('\n')
            })
            "-s" -> Res("${if (ty == "blob") o.optString("c").toByteArray().size else 0}")
            else -> Res("usage: git cat-file (-t | -s | -e | -p) <object>", 129)
        }
    }

    fun remote(dep: Depot, args: List<String>): Res {
        if (args.isNotEmpty() && args[0] in setOf("add", "set-url", "rename", "remove", "rm")) return Res(t("tp.tel.push"), 1)
        val v = "-v" in args || "--verbose" in args
        return Res(dep.remotes.keys().asSequence().toSortedSet().flatMap { r -> val u = afficher(dep.remotes.getJSONObject(r).optString("url"))
            if (v) listOf("$r\t$u (fetch)", "$r\t$u (push)") else listOf(r) }.joinToString("\n"))
    }

    /** git rev-list [--reverse] [--count] [--parents] [--first-parent] [-n N] REV [^REV | A..B] */
    fun revList(dep: Depot, args: List<String>): Res {
        val inclus = ArrayList<String>(); val exclus = ArrayList<String>(); var max = Int.MAX_VALUE
        var i = 0
        while (i < args.size) {
            val a = args[i]
            when {
                a == "-n" || a == "--max-count" -> { max = args.getOrNull(i + 1)?.toIntOrNull() ?: max; i++ }
                a.startsWith("--max-count=") -> max = a.substringAfter("=").toIntOrNull() ?: max
                a.startsWith("-") -> {}
                a.contains("..") -> { exclus.add(a.substringBefore("..").ifEmpty { "HEAD" }); inclus.add(a.substringAfter("..").ifEmpty { "HEAD" }) }
                a.startsWith("^") -> exclus.add(a.drop(1))
                else -> inclus.add(a)
            }
            i++
        }
        fun h(r: String) = resoudre(dep, r)
        val pos = inclus.map { h(it) ?: return Res("fatal: ambiguous argument '$it': unknown revision or path not in the working tree.", 128) }
        val neg = exclus.mapNotNull { h(it) }.flatMap { ordre(dep, listOf(it)) }.toSet()
        var liste: List<String> = if ("--first-parent" in args) {
            val out = ArrayList<String>(); var x = pos.firstOrNull(); while (x != null && x !in neg) { out.add(x); x = dep.parents(x).firstOrNull() }; out
        } else ordre(dep, pos).filter { it !in neg }
        liste = liste.take(max)
        if ("--count" in args) return Res("${liste.size}")
        if ("--reverse" in args) liste = liste.reversed()
        return Res(liste.joinToString("\n") { if ("--parents" in args) (listOf(it) + dep.parents(it)).joinToString(" ") else it })
    }

    // ================================================================ l'entrée : git <commande> …
    fun init(ici: File, terrain: File, args: List<String>): Res {
        var branche = "master"; var calme = false
        val mots = ArrayList<String>()
        var i = 0
        while (i < args.size) {
            val a = args[i]
            when {
                a == "-b" || a == "--initial-branch" -> { branche = args.getOrNull(i + 1) ?: return Res("error: switch `b' requires a value", 129); i++ }
                a.startsWith("--initial-branch=") -> branche = a.substringAfter("=")
                a == "-q" || a == "--quiet" -> calme = true
                a.startsWith("-") -> return Res(t("tp.tel.inconnu", "cmd" to "init $a"), 1)
                else -> mots.add(a)
            }
            i++
        }
        val d = (mots.firstOrNull()?.let { File(it).let { f -> if (f.isAbsolute) f else File(ici, it) } } ?: ici).canonicalFile
        if (!(d.path + File.separator).startsWith(terrain.canonicalPath + File.separator)) return Res(t("tp.tel.hors_terrain"), 1)
        val deja = estDepot(d)
        d.mkdirs()
        val dep = Depot(d).charger()
        if (!deja) dep.j.put("head", JSONObject().put("ref", branche))
        dep.sauver()
        if (calme) return Res("")
        return Res("${if (deja) "Reinitialized existing" else "Initialized empty"} Git repository in ${afficher(File(d, ".git").path)}/")
    }

    fun add(dep: Depot, args: List<String>): Res {
        val chemins = args.filter { !it.startsWith("-") }
        val toutes = args.any { it == "-A" || it == "--all" } || chemins.contains(".")
        if (chemins.isEmpty() && !toutes) return Res("Nothing specified, nothing added.\nhint: Maybe you wanted to say 'git add .'?\nhint: Turn this message off by running\nhint: \"git config advice.addEmptyPathspec false\"", 0)
        val travail = dep.travail().keys
        val cibles = LinkedHashSet<String>()
        if (toutes) { cibles.addAll(travail.filter { !dep.ignore(it) || dep.index.has(it) }); cibles.addAll(dep.index.keys().asSequence()) }
        for (c in chemins.filter { it != "." }) {
            val m = (travail + dep.index.keys().asSequence()).filter { it == c || it.startsWith(c.trimEnd('/') + "/") }
            if (m.isEmpty()) return Res("fatal: pathspec '$c' did not match any files", 128)
            val ign = m.filter { dep.ignore(it) && !dep.index.has(it) }
            if (ign.isNotEmpty() && ign.size == m.size) return Res("The following paths are ignored by one of your .gitignore files:\n$c\nhint: Use -f if you really want to add them.\n" +
                "hint: Turn this message off by running\nhint: \"git config advice.addIgnoredFile false\"", 1)
            cibles.addAll(m - ign.toSet())
        }
        for (p in cibles) stage(dep, p)
        dep.sauver()
        return Res("")
    }

    /** git … tapé dans l'appli : la ligne déjà découpée en mots (sans tuyau ni redirection). */
    fun executer(mots: List<String>, ici: File, terrain: File): Res {
        val sous = mots.getOrNull(0) ?: return Res(t("tp.tel.git"), 1)
        val args = mots.drop(1)
        try {
            when (sous) {
                "help", "--help", "-h" -> return Res(t("tp.tel.git"))
                "version", "--version" -> return Res("git version 2.43.0 (" + t("tp.tel.version") + ")")
                "init" -> return init(ici, terrain, args)
                "clone" -> return clone(ici, terrain, args)
                "hash-object" -> {
                    val f = args.firstOrNull { !it.startsWith("-") } ?: return Res("usage: git hash-object [-t <type>] [-w] [--path=<file> | --no-filters]", 129)
                    val x = File(f).let { if (it.isAbsolute) it else File(ici, f) }
                    if (!x.isFile) return Res("fatal: could not open '$f' for reading: No such file or directory", 128)
                    return Res(blobSha(x.readBytes()))
                }
                "push" -> return Res(t("tp.tel.push"), 1)
                "fetch", "rebase", "stash", "tag", "reset", "rm", "mv", "revert", "cherry-pick", "blame", "bisect", "submodule", "gc", "reflog", "am", "apply", "grep", "describe", "shortlog", "notes", "worktree" ->
                    return Res(t("tp.tel.inconnu", "cmd" to sous), 1)
            }
            val dep = trouver(ici, terrain)
            if (sous == "config") return config(dep, args)
            if (dep == null) return Res("fatal: not a git repository (or any of the parent directories): .git", 128)
            return when (sous) {
                "status" -> Res(status(dep, args.any { it == "-s" || it == "--short" }))
                "add" -> add(dep, args)
                "commit" -> commit(dep, args)
                "log" -> log(dep, args)
                "show" -> show(dep, args)
                "diff" -> diff(dep, args)
                "restore" -> restore(dep, args)
                "checkout" -> checkout(dep, args)
                "switch" -> switch(dep, args, false)
                "branch" -> branch(dep, args)
                "merge" -> merge(dep, args)
                "pull" -> pull(dep, ici, args)
                "remote" -> remote(dep, args)
                "cat-file" -> catFile(dep, args)
                "rev-list" -> revList(dep, args)
                "rev-parse" -> {
                    if ("--show-toplevel" in args) Res(afficher(dep.racine.path))
                    else args.filter { !it.startsWith("-") }.map { resoudre(dep, it) ?: return Res("$it\nfatal: ambiguous argument '$it': unknown revision or path not in the working tree.", 128) }.let { Res(it.joinToString("\n")) }
                }
                else -> Res(t("tp.tel.inconnu", "cmd" to sous), 1)
            }
        } catch (e: Exception) {
            return Res("petit git : ${e.message ?: e.javaClass.simpleName}", 1)
        }
    }
}
