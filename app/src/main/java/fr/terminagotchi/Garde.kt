package fr.terminagotchi

import java.io.File
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey

/**
 * Le gardien des coulisses : le vrai shell du téléphone tourne avec les MÊMES droits que l'appli, il peut donc
 * atteindre tout le dossier privé (files/sauvegarde.json, files/parties, files/racine…), même si la vue simulée
 * (Racine.kt) ne le montre pas (`$HOME/..`, `${HOME%%t*}`, `cd /proc/self/cwd`, un `kill` de l'appli…).
 * Aucune analyse de la ligne tapée ne peut tout prévoir ; le jeu se protège donc en trois couches :
 *
 *  1. Avant : Racine.refus refuse (expliqué) les chemins évidents qui sortent du camp (écritures, lecture des
 *     coulisses) ; la ligne est lancée avec des limites (temps de calcul, taille des fichiers, nombre de processus).
 *  2. Après chaque commande (photo / apres) : tout ce qui est hors du camp de base, dans files/, est comparé à la
 *     photo prise juste avant ; un fichier effacé ou modifié est remis, un fichier ajouté est enlevé, la Racine est
 *     reverrouillée ; dans le camp, un lien symbolique qui mène dehors (coulisses, vrai système) est enlevé ;
 *     et chaque processus lancé par la commande (même en arrière-plan, `&`, `setsid`) est arrêté (nettoyer).
 *     Le jeu (Jeu.sauver, Parties) prévient le gardien de ses propres écritures (noter) : elles ne sont pas annulées.
 *  3. Si l'appli est tuée pendant la commande (photo jamais comparée) : la sauvegarde porte un sceau (HMAC-SHA256,
 *     clé du magasin de clés d'Android, que le shell ne peut ni lire ni utiliser) et une copie de secours scellée
 *     (sauvegarde.json.bak) : une sauvegarde modifiée hors du jeu est remplacée par sa dernière bonne copie.
 */
object Garde {
    /** limites de la ligne tapée : secondes de calcul par processus, taille max d'un fichier (blocs de 512 o), processus */
    const val CPU_S = 25
    const val FICHIER_BLOCS = 100_000           // ≈ 50 Mo
    const val PROCESSUS = 400
    /** au-delà, un fichier n'est pas gardé en mémoire (seule sa taille et sa date comptent) */
    private const val TAILLE_MAX = 2L shl 20

    private class Entree(val dossier: Boolean, val taille: Long, val date: Long, val octets: ByteArray?)

    private val verrou = Any()
    private var photo: Map<String, Entree>? = null
    private var base: File? = null

    /** les lieux protégés : files/ (sauf le camp de base, files/maison) */
    private fun protege(home: File): File = home.parentFile ?: home

    /** dernière lecture de chaque fichier (pour ne pas tout relire à chaque commande) */
    private val cache = HashMap<String, Entree>()

    /** toujours relus en entier (pas seulement taille et date) : tout, sauf les terrains rangés des autres parties */
    private fun critique(f: File) = "/parties/terrain_" !in f.path

    private fun lire(f: File, relire: Boolean = false): Entree? = try {
        if (f.isDirectory) Entree(true, 0, 0, null)
        else {
            val n = f.length()
            val d = f.lastModified()
            val c = cache[f.path]
            if (!relire && !critique(f) && c != null && c.taille == n && c.date == d) c
            else Entree(false, n, d, if (n <= TAILLE_MAX) f.readBytes() else null).also { cache[f.path] = it }
        }
    } catch (e: Exception) { null }

    private fun parcourir(home: File, b: File): Map<String, Entree> {
        val out = HashMap<String, Entree>()
        val camp = home.canonicalPathOrNull()
        val racine = Racine.dossier(home).path
        fun vis(d: File, n: Int) {
            if (n > 40) return
            val l = d.listFiles() ?: return
            for (f in l) {
                val p = f.path
                if (p == home.path || f.canonicalPathOrNull() == camp) continue
                if (java.nio.file.Files.isSymbolicLink(f.toPath())) { out[p] = Entree(false, -1, 0, null); continue }
                // droits retirés (chmod 000 …/sauvegarde.json) : rendus tout de suite, sinon l'appli ne pourrait plus lire
                if (p != racine && !p.startsWith("$racine/")) {
                    if (!f.canRead()) f.setReadable(true, true)
                    if (!f.canWrite()) f.setWritable(true, true)
                    if (f.isDirectory && !f.canExecute()) f.setExecutable(true, true)
                } else if (f.isDirectory && (!f.canRead() || !f.canExecute())) {
                    f.setReadable(true, false); f.setExecutable(true, false)
                }
                lire(f)?.let { out[p] = it }
                if (f.isDirectory) vis(f, n + 1)
            }
        }
        vis(b, 0)
        return out
    }

    private fun File.canonicalPathOrNull(): String? = try { canonicalPath } catch (e: Exception) { null }

    /** Juste avant de lancer une commande : la photo de tout ce qui est hors du camp. */
    fun photo(home: File) = synchronized(verrou) {
        val b = protege(home)
        base = b
        photo = parcourir(home, b)
    }

    /** Le jeu vient d'écrire ce fichier lui-même (sauvegarde, rangement des parties) : ce n'est pas une attaque. */
    fun noter(f: File) = synchronized(verrou) {
        val p = photo ?: return@synchronized
        val m = HashMap(p)
        val e = lire(f, relire = true)
        if (e == null || !f.exists()) m.remove(f.path) else m[f.path] = e
        // un .tmp renommé : il a disparu, c'est normal
        m.keys.filter { it.endsWith(".tmp") && !File(it).exists() }.forEach { m.remove(it) }
        photo = m
    }

    private fun pareil(a: Entree, b: Entree): Boolean = when {
        a.dossier || b.dossier -> a.dossier == b.dossier
        a.taille != b.taille -> false
        a.octets != null && b.octets != null -> a.octets.contentEquals(b.octets)
        else -> a.date == b.date
    }

    /**
     * Juste après la commande : remet ce qui a changé hors du camp. Renvoie ce qui a été réparé
     * (chemins du Terminaworld ou « coulisses »), vide si rien n'a bougé.
     */
    fun apres(home: File): List<String> = synchronized(verrou) {
        val avant = photo ?: return@synchronized emptyList()
        val b = base ?: return@synchronized emptyList()
        photo = null
        val maintenant = parcourir(home, b)
        val repare = ArrayList<String>()
        // 1. ajouté hors du camp (les plus profonds d'abord) : enlevé
        for (p in maintenant.keys.filter { it !in avant }.sortedByDescending { it.length }) {
            if (p.endsWith(".tmp")) continue                     // une écriture du jeu en cours (sauvegarde.tmp)
            val f = File(p)
            try { f.parentFile?.setWritable(true, true); f.setWritable(true, true) } catch (e: Exception) {}
            if (f.delete() || !f.exists()) repare.add(p)
        }
        // 2. effacé ou modifié : remis (les dossiers d'abord)
        for ((p, e) in avant.entries.sortedBy { it.key.length }) {
            val m = maintenant[p]
            if (m != null && pareil(e, m)) continue
            val f = File(p)
            try {
                f.parentFile?.let { d -> if (!d.isDirectory) d.mkdirs(); d.setWritable(true, true) }
                if (e.dossier) {
                    if (java.nio.file.Files.isSymbolicLink(f.toPath()) || f.isFile) f.delete()
                    f.mkdirs()
                } else if (e.taille >= 0 && e.octets != null) {
                    if (java.nio.file.Files.isSymbolicLink(f.toPath()) || f.isDirectory) f.deleteRecursively()
                    f.setWritable(true, true)
                    f.writeBytes(e.octets)
                    f.setLastModified(e.date)
                } else continue
                repare.add(p)
            } catch (x: Exception) {
                android.util.Log.w("TG", "garde : $p non remis", x)
            }
        }
        // 3. la Racine reste en lecture seule (chmod -R u+w …)
        Racine.reverrouiller(home)
        repare
    }

    /** Dans le camp : les liens symboliques qui mènent dehors (coulisses de l'appli, vrai système) sont enlevés. */
    fun liensDehors(home: File): List<String> {
        val camp = try { home.canonicalPath } catch (e: Exception) { return emptyList() }
        val racine = try { Racine.dossier(home).canonicalPath } catch (e: Exception) { "" }
        val out = ArrayList<String>()
        fun ok(c: String) = c == camp || c.startsWith("$camp/") || (racine.isNotEmpty() && (c == racine || c.startsWith("$racine/"))) ||
            c in Racine.VRAIS
        fun vis(d: File, n: Int) {
            if (n > 40) return
            for (f in d.listFiles() ?: return) {
                val chemin = f.toPath()
                if (java.nio.file.Files.isSymbolicLink(chemin)) {
                    val c = try { f.canonicalPath } catch (e: Exception) { "" }
                    if (!ok(c)) { f.delete(); out.add(f.path) }
                } else if (f.isDirectory) vis(f, n + 1)
            }
        }
        vis(home, 0)
        return out
    }

    // ---------------------------------------------------------------- les processus de la commande
    private fun stat(pid: Int): IntArray? = try {
        val s = File("/proc/$pid/stat").readText()
        val f = s.substring(s.lastIndexOf(')') + 2).split(' ')
        intArrayOf(f[1].toInt(), f[2].toInt(), f[3].toInt())     // ppid, pgrp, session
    } catch (e: Exception) { null }

    private fun uid(pid: Any): String? = try {
        File("/proc/$pid/status").readLines().firstOrNull { it.startsWith("Uid:") }?.split(Regex("\\s+"))?.getOrNull(1)
    } catch (e: Exception) { null }

    fun pids(): Set<Int> = File("/proc").list()?.mapNotNull { it.toIntOrNull() }?.toSet() ?: emptySet()

    /**
     * Arrête tous les processus nés de la commande (sh de pid `sh`) : ses descendants, sa session (sh est lancé par
     * setsid), et les orphelins de l'appli (même utilisateur, nés pendant la commande, rattachés à init).
     * Renvoie le nombre de processus arrêtés.
     */
    fun nettoyer(sh: Int, avant: Set<Int>): Int {
        if (sh <= 0) return 0
        val moi = uid("self") ?: return 0
        val soi = try { File("/proc/self").canonicalFile.name.toIntOrNull() ?: -1 } catch (e: Exception) { -1 }
        var total = 0
        for (tour in 0 until 4) {
            val tous = pids()
            val info = tous.associateWith { stat(it) }
            val vises = HashSet<Int>()
            fun descend(p: Int): Boolean {
                var x = p
                for (i in 0 until 64) {
                    if (x == sh) return true
                    x = info[x]?.get(0) ?: return false
                    if (x <= 1) return false
                }
                return false
            }
            for (p in tous) {
                if (p == soi || p in avant && p != sh) continue
                val s = info[p] ?: continue
                val dela = p == sh || descend(p) || s[2] == sh || s[1] == sh
                val orphelin = p !in avant && s[0] == 1
                if ((dela || orphelin) && uid(p) == moi) vises.add(p)
            }
            if (vises.isEmpty()) break
            total += vises.size
            try {
                ProcessBuilder("kill", "-9", *vises.map { it.toString() }.toTypedArray())
                    .redirectErrorStream(true).start().apply { inputStream.readBytes(); waitFor() }
            } catch (e: Exception) {
                try { ProcessBuilder(Shell.SH, "-c", "kill -9 " + vises.joinToString(" ")).start().waitFor() } catch (x: Exception) {}
            }
            Thread.sleep(30)
        }
        return total
    }

    // ---------------------------------------------------------------- le sceau de la sauvegarde
    private const val ALIAS = "terminagotchi_sceau"
    private var cle: SecretKey? = null
    /** vrai si la clé vient d'être créée (première fois avec le sceau : les sauvegardes d'avant n'en ont pas) */
    @Volatile var cleNeuve = false
        private set
    /** sous la JVM des tests (pas de magasin de clés Android) : une clé par processus */
    @Volatile var exigerSceau = false

    private fun cle(): SecretKey? {
        cle?.let { return it }
        val k = try {
            val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            if (!ks.containsAlias(ALIAS)) {
                // KeyGenParameterSpec.Builder(ALIAS, PURPOSE_SIGN = 4).build(), par réflexion (rien d'Android à compiler)
                val b = Class.forName("android.security.keystore.KeyGenParameterSpec\$Builder")
                    .getConstructor(String::class.java, Int::class.javaPrimitiveType).newInstance(ALIAS, 4)
                val spec = b.javaClass.getMethod("build").invoke(b) as java.security.spec.AlgorithmParameterSpec
                KeyGenerator.getInstance("HmacSHA256", "AndroidKeyStore").apply { init(spec) }.generateKey()
                cleNeuve = true
            }
            exigerSceau = true
            ks.getKey(ALIAS, null) as SecretKey
        } catch (e: Exception) {
            // pas de magasin de clés (JVM des tests) : une clé en mémoire
            KeyGenerator.getInstance("HmacSHA256").generateKey()
        }
        cle = k
        return k
    }

    private fun hmac(texte: String): String? = try {
        val m = Mac.getInstance("HmacSHA256")
        m.init(cle())
        m.doFinal(texte.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    } catch (e: Exception) { null }

    private const val MARQUE = ",\"sceau\":\""

    /** Le texte à écrire : le JSON, avec son sceau à la fin. */
    fun sceller(o: org.json.JSONObject): String {
        o.remove("sceau")
        val s = o.toString()
        val h = hmac(s) ?: return s
        return if (s == "{}") s else s.dropLast(1) + MARQUE + h + "\"}"
    }

    /** « ok » (sceau bon), « sans » (pas de sceau : sauvegarde d'avant), « faux » (modifiée hors du jeu). */
    fun verifier(texte: String): String {
        val t = texte.trimEnd()
        val i = t.lastIndexOf(MARQUE)
        if (i < 0 || !t.endsWith("\"}")) return "sans"
        val h = t.substring(i + MARQUE.length, t.length - 2)
        val brut = t.substring(0, i) + "}"
        return if (hmac(brut) == h) "ok" else "faux"
    }

    /** Une sauvegarde sans sceau est acceptée seulement si le sceau n'existait pas encore (mise à jour de l'appli). */
    fun acceptable(texte: String): Boolean = when (verifier(texte)) {
        "ok" -> true
        "sans" -> { cle(); !exigerSceau || cleNeuve }
        else -> false
    }

    /** Pour les tests : oublier la clé (comme un autre appareil) ou faire comme si le magasin de clés existait. */
    fun pourTests(exiger: Boolean) { exigerSceau = exiger; cleNeuve = false }
}
