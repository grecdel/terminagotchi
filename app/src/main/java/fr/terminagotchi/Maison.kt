package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Le monde à explorer, le Terminaworld (portage de pc/tg/maison.py) : les lieux sont de vrais dossiers du terrain,
 * la carte pousse au fil des découvertes.
 *
 *   ~/terrain_terminagotchi/            le camp de base
 *       vestibule/ nid/                 chapitres 1 et 2
 *       grenier/ cave/ bibliotheque/ salle_des_machines/ dortoir/ atelier/ tour/   chapitres 3 à 9
 *       coeur/                          chapitre 10 (ouvert quand 5 ailes sont réveillées)
 *       jardin/                         le jardin du téléphone
 *       biome/<type>/parcelle_<n>/      la porte du Terminaworld, ses régions et leurs parcelles
 *       (plus les lieux inventés par l'enfant, et des passages secrets « .cachette »)
 *
 * Dossier = lieu, fichier = objet, dossier caché = passage secret, `tree` = la carte du Terminaworld.
 *
 * Où est l'enfant ? Sur le téléphone, c'est simple : le terminal de l'appli (Shell.kt) gère lui-même « cd », son
 * dossier courant est connu après chaque commande (Tour.apresCommande le reçoit). Un lieu est « visité » quand on y
 * est vraiment entré.
 *
 * La carte qui pousse (commande « carte ») : le VRAI terrain, dessiné (CarteVue.kt, Carte.kt) à côté de la sortie de
 * `tree`, ligne par ligne. Elle ne montre que ce que l'enfant a découvert : un lieu visité (ou montré par `tree`)
 * dévoile ce qu'il contient, un lieu jamais visité reste dans la brume, les passages secrets n'apparaissent qu'après
 * `ls -a`, ce qui apparaît pour la première fois brille (nouveau !), ◉ = tu es ici, et la légende ne liste que les
 * commandes déjà rencontrées. Le texte (carte()) est la même carte en `tree` annoté (terminal, tests).
 *
 * Terres sauvages : tout ce qui est hors de la maison de l'appli (/system, /proc…). On peut y regarder (lecture
 * seule), le jeu prévient : on ne touche à rien là-bas. Le jeu n'y écrit jamais rien.
 */
object Maison {
    val AILES = listOf("grenier", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier", "tour")
    val PIECES = listOf("vestibule", "nid") + AILES + "coeur"
    val ICONES = mapOf("vestibule" to "🥚", "nid" to "🏠", "grenier" to "🌿", "cave" to "🔒", "bibliotheque" to "📚",
        "salle_des_machines" to "🔥", "dortoir" to "👻", "atelier" to "🔧", "tour" to "📡", "coeur" to "💜",
        "recoins" to "🚪", "sauvage" to "🌲", "jardin" to "📱")
    val PRUDENCE = setOf("rm", "rmdir", "mv", "chmod", "chown", "del", "remove-item", "move-item", "ren")

    /** Une région du monde (donnees/biomes.json, vérifié par tests/jvm/Carte.kt) : emoji, principale, sombre, claire. */
    class Biome(val emoji: String, val principale: Int, val sombre: Int, val claire: Int)

    val BIOMES = linkedMapOf(
        "feu" to Biome("🔥", 0xFFE8562A.toInt(), 0xFF3A2A30.toInt(), 0xFFFFB347.toInt()),
        "eau" to Biome("💧", 0xFF2F7FC4.toInt(), 0xFF1D4F7A.toInt(), 0xFF7CC7FF.toInt()),
        "glace" to Biome("🧊", 0xFF9FD8F2.toInt(), 0xFF5689A3.toInt(), 0xFFF5FBFF.toInt()),
        "plante" to Biome("🌿", 0xFF5AA63A.toInt(), 0xFF2F6B2C.toInt(), 0xFF86D45A.toInt()),
        "roche" to Biome("🗻", 0xFFC9A26A.toInt(), 0xFF7D828A.toInt(), 0xFFEFDB9C.toInt()),
        "ciel" to Biome("⚡", 0xFFDFE9FF.toInt(), 0xFF8B9AC4.toInt(), 0xFFFFFFFF.toInt()),
        "ombre" to Biome("🌙", 0xFF4B3A6B.toInt(), 0xFF251C38.toInt(), 0xFF8F7BC0.toInt()),
        "machine" to Biome("🔩", 0xFF8A96A3.toInt(), 0xFF4A525C.toInt(), 0xFFC9D2DB.toInt()),
        "poison" to Biome("🧪", 0xFF6A8F2A.toInt(), 0xFF3B4A1C.toInt(), 0xFFB6FF4A.toInt()),
    )
    val EMOJIS = mapOf("camp" to "⛺", "porte" to "🌀", "lieu" to "🌳", "note" to "📜", "recette" to "📝",
        "image" to "🌅", "coffre" to "📦", "secret" to "🔑", "secret_objet" to "🔑", "brume" to "░░", "suite" to "··")
    private val TEXTES = setOf("txt", "md", "log", "csv", "json", "ini", "cfg", "conf", "yml", "yaml", "html", "xml", "")
    private val SCRIPTS = setOf("sh", "ps1", "py", "bat", "cmd", "bash", "zsh", "fish", "js", "rb", "pl", "kts")
    private val IMAGES = setOf("png", "jpg", "jpeg", "gif", "bmp", "webp", "svg", "ico", "tif", "tiff")
    /** niveaux montrés sous le camp de base */
    const val PROFONDEUR = 5
    /** au-delà : une ligne « + n autres » */
    const val MAX_PAR_DOSSIER = 16
    const val MAX_LIGNES = 150
    /** un dossier plus grand n'est pas exploré (on ne lit pas un dossier géant) */
    const val TROP_GRAND = 200
    val IGNORES = setOf(".git", "node_modules", "__pycache__", ".cache", "venv", ".venv", ".gradle", "build")
    /** la légende : les commandes du monde, dans l'ordre où on les apprend, avec leurs synonymes */
    val LEGENDE = listOf("pwd" to setOf("pwd"), "ls" to setOf("ls", "dir", "ll", "la"), "cd" to setOf("cd", "chdir", "pushd"),
        "mkdir" to setOf("mkdir", "md"), "touch" to setOf("touch"), "cp" to setOf("cp", "copy"), "mv" to setOf("mv", "move", "ren"),
        "rm" to setOf("rm", "rmdir", "rd", "del"), "tree" to setOf("tree"), "ls_a" to emptySet())
    val CHANGE = setOf("mkdir", "md", "touch", "rm", "rmdir", "rd", "del", "mv", "move", "ren", "cp", "copy", "tar", "unzip", "git", "edite")
    private val SEP_CMD = Regex("\\s*(?:&&|\\|\\||;)\\s*")
    private val LS = setOf("ls", "dir", "ll", "la")

    fun m(jeu: Jeu): JSONObject {
        val m = jeu.module("maison")
        for (k in listOf("visites", "sauvage", "montres", "arbres")) if (!m.has(k)) m.put(k, JSONArray())
        if (!m.has("cwd")) m.put("cwd", JSONObject.NULL)
        if (!m.has("averti")) m.put("averti", 0L)
        if (!m.has("prudence")) m.put("prudence", 0L)
        if (!m.has("ls_a")) m.put("ls_a", false)
        return m
    }

    private fun liste(o: JSONObject, k: String) = Quetes.liste(o, k)

    fun nomPiece(p: String) = t("carte.piece.$p")

    private fun normal(chemin: String): String = try {
        java.nio.file.Paths.get(chemin).normalize().toString()
    } catch (e: Exception) { chemin }

    /** Le chemin d'un dossier dans la maison (« grenier/fouillis », « » pour la grande salle), ou null. */
    fun rel(jeu: Jeu, chemin: String?): String? {
        if (chemin == null) return null
        val c = normal(chemin)
        val t = jeu.terrain.path
        return when {
            c == t -> ""
            c.startsWith("$t/") -> c.substring(t.length + 1).trimEnd('/')
            else -> null
        }
    }

    /** Vrai si le dossier cwd est la pièce (ou une de ses sous-pièces). piece = « » : la grande salle. */
    fun dans(jeu: Jeu, cwd: String?, piece: String): Boolean {
        val r = rel(jeu, cwd) ?: return false
        return piece == "" || r == piece || r.startsWith("$piece/")
    }

    /** Le dernier dossier courant connu (chemin absolu) ou null. */
    fun ici(jeu: Jeu): String? = m(jeu).let { if (it.isNull("cwd")) null else it.optString("cwd").ifEmpty { null } }

    fun pieceDe(jeu: Jeu): String? {
        val r = rel(jeu, ici(jeu)) ?: return null
        return if (r.isEmpty()) "" else r.split("/")[0]
    }

    // ---------------------------------------------------------------- suivre le dossier courant
    private fun visiter(jeu: Jeu, cwd: String) {
        val m = m(jeu)
        val r = rel(jeu, cwd)
        if (r == null) {
            val s = liste(m, "sauvage")
            if (!normal(cwd).startsWith(jeu.home.path) && cwd !in s) {
                s.add(cwd)
                m.put("sauvage", JSONArray(s.takeLast(20)))
                avertirSauvage(jeu)
            }
            return
        }
        val v = liste(m, "visites")
        if (r !in v) {
            v.add(r)
            m.put("visites", JSONArray(v.takeLast(300)))
        }
    }

    fun avertirSauvage(jeu: Jeu) {
        val m = m(jeu)
        val now = System.currentTimeMillis()
        if (now - m.optLong("averti") > 600_000L) {
            m.put("averti", now)
            jeu.dire(t(Histoire.cle("carte.sauvage.dit")), 12)
        }
    }

    /** Une commande qui casse ou modifie, tapée hors de la maison du jeu : un petit rappel. */
    private fun prudence(jeu: Jeu, ligne: String, cwd: String?) {
        val mots = ligne.trim().split(Regex("\\s+"))
        if (mots.isEmpty() || mots[0].lowercase() !in PRUDENCE) return
        var hors = if (cwd != null) rel(jeu, cwd) == null else false
        for (x in mots.drop(1)) if ((x.startsWith("/") || x.startsWith("~")) && "terrain_terminagotchi" !in x) hors = true
        val m = m(jeu)
        val now = System.currentTimeMillis()
        if (hors && now - m.optLong("prudence") > 120_000L) {
            m.put("prudence", now)
            jeu.dire(t("carte.prudence.dit", "terrain" to "~/${jeu.terrain.name}"), 12)
        }
    }

    /** `ls -a`, `ls -la`, `ls -A`, `ls --all` : une commande qui montre les fichiers cachés. */
    fun voitCaches(morceau: String): Boolean {
        val mots = morceau.trim().split(Regex("\\s+"))
        if (mots.isEmpty() || mots[0].lowercase() !in LS) return false
        return mots.drop(1).any { w ->
            w.lowercase() in setOf("--all", "--almost-all", "/a") ||
                (w.startsWith("-") && !w.startsWith("--") && w.length <= 6 && w.drop(1).all { it.isLetter() } && ('a' in w || 'A' in w.drop(1)))
        }
    }

    /** Ce que la ligne apprend à la carte : `ls -a` (les passages secrets), `tree` (la carte d'un coin). */
    private fun noter(jeu: Jeu, ligne: String, cwd: String) {
        val m = m(jeu)
        for (morceau in ligne.trim().split(SEP_CMD)) {
            if (voitCaches(morceau)) m.put("ls_a", true)
            val mots = morceau.trim().split(Regex("\\s+"))
            if (mots.firstOrNull()?.lowercase() == "tree") {
                val cible = mots.drop(1).firstOrNull { !it.startsWith("-") }
                val d = when {
                    cible == null -> cwd
                    cible.startsWith("/") -> cible
                    cible.startsWith("~/") -> File(jeu.home, cible.substring(2)).path
                    else -> File(cwd, cible).path
                }
                val r = rel(jeu, d)
                val a = liste(m, "arbres")
                if (r != null && r !in a) { a.add(r); m.put("arbres", JSONArray(a.takeLast(40))) }
                if (mots.drop(1).any { it.startsWith("-") && 'a' in it.drop(1) }) m.put("ls_a", true)
            }
        }
    }

    /**
     * Après une commande tapée (ligne, null si c'est le tour périodique) : le dossier courant du terminal (cwd)
     * est visité. Renvoie les commandes tapées (pas collées) avec leur dossier courant.
     */
    fun suivre(jeu: Jeu, ligne: String?, colle: Boolean, cwd: File?): List<Pair<String, String?>> {
        val m = m(jeu)
        val cur = cwd?.path ?: ici(jeu) ?: jeu.home.path
        val apres = mutableListOf<Pair<String, String?>>()
        var change = false
        if (ligne != null && !colle && !Regles.estColle(ligne) && ligne.isNotBlank()) {
            visiter(jeu, cur)
            prudence(jeu, ligne, cur)
            noter(jeu, ligne, cur)
            change = ligne.trim().split(SEP_CMD).any { Regles.premierMot(it) in CHANGE }
            for (x in ligne.trim().split(Regex("\\s+")).drop(1)) {
                if (x.startsWith("/") && !x.startsWith(jeu.home.path) && File(x).exists()) {
                    avertirSauvage(jeu)                                   // regarder un fichier du système (lecture seule)
                    val s = liste(m, "sauvage")
                    val d = File(x).parent ?: "/"
                    if (d !in s) { s.add(d); m.put("sauvage", JSONArray(s.takeLast(20))) }
                    break
                }
            }
            apres.add(ligne.trim() to cur)
        }
        if (cwd != null) visiter(jeu, cwd.path)
        m.put("cwd", cur)
        if (change || !m.has("empreinte")) pousse(jeu)
        return apres
    }

    // ---------------------------------------------------------------- la carte a poussé
    /** Le dernier « la carte a poussé » (le terminal l'affiche une fois, puis le remet à null). */
    var dernierePousse: String? = null

    /** Les chemins du terrain (sans les cachés tant que `ls -a` n'est pas connu), sur PROFONDEUR niveaux. */
    fun empreinte(jeu: Jeu): Set<String> {
        val vus = linkedSetOf<String>()
        val caches = m(jeu).optBoolean("ls_a")
        fun tour(d: File, r: String, n: Int) {
            if (n > PROFONDEUR || vus.size > 600) return
            val es = d.listFiles() ?: return
            if (es.size > TROP_GRAND) return
            for (e in es) {
                if (e.name.startsWith(".") && !caches) continue
                val c = if (r.isEmpty()) e.name else "$r/${e.name}"
                val dossier = e.isDirectory
                vus.add(c + if (dossier) "/" else "")
                if (dossier && e.name !in IGNORES) tour(e, c, n + 1)
            }
        }
        if (jeu.terrain.isDirectory) tour(jeu.terrain, "", 1)
        return vus
    }

    /** Compare le terrain à la dernière empreinte : « 🗺 la carte a poussé : + parcelle_3/ » (journal et terminal). */
    fun pousse(jeu: Jeu): String? {
        val m = m(jeu)
        val neuve = empreinte(jeu)
        val vieille = m.optJSONArray("empreinte")?.let { a -> (0 until a.length()).map { a.getString(it) }.toSet() }
        m.put("empreinte", JSONArray(neuve.sorted().take(400)))
        if (vieille == null) return null
        val p = neuve - vieille
        val mo = vieille - neuve
        val plus = p.filter { x -> p.none { it != x && x.startsWith(it) } }.sorted()
        val moins = mo.filter { x -> mo.none { it != x && x.startsWith(it) } }.sorted()
        if (plus.isEmpty() && moins.isEmpty()) return null
        fun court(xs: List<String>, signe: String) = xs.take(3).map {
            "$signe " + it.trimEnd('/').substringAfterLast('/') + if (it.endsWith("/")) "/" else ""
        } + if (xs.size > 3) listOf("…") else emptyList()
        val quoi = (court(plus, "+") + court(moins, "−")).joinToString(" ")
        val msg = t(if (plus.isNotEmpty()) "carte.monde.pousse" else "carte.monde.retrecit", "quoi" to quoi)
        jeu.log(msg)
        dernierePousse = msg
        return msg
    }

    // ---------------------------------------------------------------- ce que l'enfant a découvert
    fun visitee(jeu: Jeu, p: String): Boolean = liste(m(jeu), "visites").any { it == p || it.startsWith("$p/") }

    /** Les familles des monstres sauvages présents (le dressage en cours). */
    private fun famillesSauvages(jeu: Jeu): List<String> {
        val d = jeu.module("dressage").optJSONObject("en_cours") ?: return emptyList()
        return listOfNotNull(Bestiaire.espece(d.optString("espece"))?.famille)
    }

    /** Les petits signes d'un lieu de l'histoire : ✓ réveillé, ▶ en cours, ★ quête, 🐾 monstres. */
    fun marques(jeu: Jeu, p: String): String {
        val sb = StringBuilder()
        val ch = Histoire.chapitreDePiece(p)
        if (ch != null && ch.id in Histoire.ailes(jeu)) sb.append("✓")
        else if (ch != null && Histoire.chap(jeu) == ch.id) sb.append("▶")
        if (Quetes.etoile(jeu, p)) sb.append("★")
        val fam = ch?.famille
        if (fam != null && fam in famillesSauvages(jeu)) sb.append("🐾")
        return sb.toString()
    }

    /** Une ligne de la carte (et de `tree`). */
    class Noeud(
        val rel: String, val nom: String, val prof: Int, val dossier: Boolean, val genre: String, val biome: String?,
        val brume: Boolean, val nouveau: Boolean, val branches: String, val suite: Int, val cle: String,
    ) {
        var ici = false
        var marques = ""
        var etiquette = ""
        /** la ligne du dossier parent (null pour le camp de base) */
        var parent: Noeud? = null
    }

    /** (genre, biome ou lieu de l'histoire) d'une entrée du terrain (r = chemin relatif). */
    fun genre(r: String, dossier: Boolean): Pair<String, String?> {
        if (r.isEmpty()) return "camp" to null
        val parts = r.split("/")
        val nom = parts.last()
        if (nom.startsWith(".")) return (if (dossier) "secret" else "secret_objet") to null
        val region = parts.indices.firstOrNull { it > 0 && parts[it - 1] == "biome" && parts[it] in BIOMES }?.let { parts[it] }
        if (dossier) {
            if (r in PIECES || r == "jardin") return "piece" to r
            if (r == "biome") return "porte" to null
            if (parts.size >= 2 && parts[parts.size - 2] == "biome" && nom in BIOMES) return "region" to nom
            if (Regex("parcelle[_-]?\\d*").matches(nom.lowercase())) return "parcelle" to region
            val bas = nom.lowercase()
            if (bas in setOf("camp", "nid", "base", "campement", "camp_de_base") || bas.startsWith("camp")) return "camp" to null
            return "lieu" to (region ?: BIOMES.keys.firstOrNull { it in bas })
        }
        val ext = if ('.' in nom.drop(1)) nom.substringAfterLast('.').lowercase() else ""
        return when (ext) {
            in SCRIPTS -> "recette"
            in IMAGES -> "image"
            in TEXTES -> "note"
            else -> "coffre"
        } to region
    }

    /** Le nom dessiné à côté de la tuile. */
    fun etiquette(n: Noeud): String {
        if (n.brume) return "???"
        return when (n.genre) {
            "suite" -> t("carte.monde.autres", "n" to n.suite)
            "camp" -> if (n.rel.isEmpty()) t("carte.monde.camp") else t("carte.monde.campement")
            "piece" -> nomPiece(n.biome ?: "")
            "region" -> t("carte.monde.region", "nom" to t("carte.biome.${n.biome}"))
            "secret_objet" -> t("carte.monde.secret_objet")
            "porte", "lieu", "parcelle", "secret", "note", "recette", "image", "coffre" -> t("carte.monde.${n.genre}")
            else -> n.nom
        }
    }

    /**
     * Le monde découvert, ligne par ligne, dans l'ordre de `tree`. marquer = true : ce qui est montré n'est plus
     * « nouveau » la fois suivante.
     */
    fun noeuds(jeu: Jeu, marquer: Boolean = false): List<Noeud> {
        val m = m(jeu)
        val visites = liste(m, "visites")
        val ouverts = hashSetOf("")
        for (v in visites) {
            val parts = if (v.isEmpty()) emptyList() else v.split("/")
            for (i in 0..parts.size) ouverts.add(parts.take(i).joinToString("/"))
        }
        val arbres = liste(m, "arbres")
        val montres = liste(m, "montres").toHashSet()
        val caches = m.optBoolean("ls_a")
        val vis = visites.toHashSet()
        val out = mutableListOf<Noeud>()
        fun ouvert(r: String) = r in ouverts || arbres.any { it == "" || r == it || r.startsWith("$it/") }

        fun ligne(r: String, nom: String, prof: Int, dossier: Boolean, branches: String, brume: Boolean, parent: Noeud?, suite: Int = 0): Noeud {
            val (g, b) = if (suite > 0) "suite" to null else genre(r, dossier)
            val cle = (if (brume) "~" else "") + r + if (dossier) "/" else ""
            val n = Noeud(r, nom, prof, dossier, g, b, brume, suite == 0 && cle !in montres, branches, suite, cle)
            n.parent = parent
            if (g == "piece" && b != null && b in PIECES) n.marques = if (brume) (if (Quetes.etoile(jeu, b)) "★" else "") else marques(jeu, b)
            n.etiquette = etiquette(n)
            out.add(n)
            return n
        }

        fun tour(d: File, r: String, prof: Int, avant: String, parent: Noeud) {
            val es = d.listFiles() ?: return
            if (es.size > TROP_GRAND) return
            var garde = es.sortedWith(compareBy({ it.name.trimStart('.').lowercase() }, { it.name })).mapNotNull { e ->
                val c = if (r.isEmpty()) e.name else "$r/${e.name}"
                val dossier = e.isDirectory
                when {
                    e.name.startsWith(".") && !caches && c !in vis -> null          // un passage secret : il faut `ls -a`
                    prof == 1 && dossier && e.name in PIECES && !Histoire.pieceOuverte(jeu, e.name) -> null   // pas encore posé
                    else -> Triple(e, c, dossier)
                }
            }
            var reste = 0
            if (garde.size > MAX_PAR_DOSSIER) {           // trop de choses : d'abord ce qu'on connaît, la brume ensuite
                fun rang(x: Triple<File, String, Boolean>): Int {
                    val (e, c, dossier) = x
                    if (dossier && (ouvert(c) || (prof == 1 && e.name in PIECES))) return 0
                    return if (e.name.startsWith(".")) 1 else if (!dossier) 2 else 3
                }
                val choix = garde.indices.sortedWith(compareBy({ rang(garde[it]) }, { it })).take(MAX_PAR_DOSSIER - 1).sorted()
                reste = garde.size - choix.size
                garde = choix.map { garde[it] }
            }
            for ((i, x) in garde.withIndex()) {
                if (out.size >= MAX_LIGNES) return
                val (e, c, dossier) = x
                val dernier = i == garde.size - 1 && reste == 0
                val dedans = dossier && ouvert(c)
                val brume = dossier && !dedans && !e.name.startsWith(".")         // un passage secret trouvé se voit
                val n = ligne(c, e.name, prof, dossier, avant + if (dernier) "└── " else "├── ", brume, parent)
                if (dedans && prof < PROFONDEUR && e.name !in IGNORES) tour(e, c, prof + 1, avant + if (dernier) "    " else "│   ", n)
            }
            if (reste > 0) ligne("$r/…", "…", prof, false, "$avant└── ", false, parent, suite = reste)
        }

        val racine = ligne("", ".", 0, true, "", false, null)
        if (jeu.terrain.isDirectory) tour(jeu.terrain, "", 1, "", racine)
        // ◉ : la ligne du dossier courant (ou de son parent le plus proche qui est sur la carte)
        rel(jeu, ici(jeu))?.let { rIci ->
            val par = out.filter { it.dossier }.associateBy { it.rel }
            var x = rIci
            while (x !in par && x.isNotEmpty()) x = if ('/' in x) x.substringBeforeLast('/') else ""
            par[x]?.ici = true
        }
        if (marquer) m.put("montres", JSONArray((liste(m, "montres") + out.filter { it.nouveau }.map { it.cle }).takeLast(800)))
        return out
    }

    /** Les commandes du monde déjà rencontrées (dans l'ordre où on les apprend) : textes avec `…` en vert. */
    fun legende(jeu: Jeu): List<String> {
        val vues = jeu.vus.map { it.lowercase() }.toSet()
        return LEGENDE.filter { (k, syn) -> (k == "ls_a" && m(jeu).optBoolean("ls_a")) || syn.any { it in vues } }
            .map { t("carte.monde.cmd.${it.first}") }
    }

    fun emoji(n: Noeud): String = when {
        n.brume -> EMOJIS.getValue("brume")
        n.genre == "piece" -> ICONES[n.biome] ?: "🌳"
        (n.genre == "region" || n.genre == "parcelle") && n.biome in BIOMES -> BIOMES.getValue(n.biome!!).emoji
        else -> EMOJIS[n.genre] ?: "🌳"
    }

    /** La ligne de `tree` (avec / après les dossiers, comme `tree -F`). */
    fun texteTree(n: Noeud): String = n.branches + when {
        n.genre == "suite" -> "… " + t("carte.monde.autres", "n" to n.suite)
        n.dossier && n.rel.isNotEmpty() -> n.nom + "/"
        else -> n.nom
    }

    /** Ce qui est écrit sous la carte : où on est, les signes, les commandes rencontrées, les secrets, les terres sauvages. */
    fun pied(jeu: Jeu): List<String> {
        val l = mutableListOf<String>()
        val ici = ici(jeu)
        val r = rel(jeu, ici)
        if (r != null) l.add("◉ " + t("carte.ici", "lieu" to if (r.isNotEmpty()) "~/${jeu.terrain.name}/$r" else "~/${jeu.terrain.name}"))
        else if (ici != null) l.add("◉ " + t("carte.dehors", "lieu" to (if (normal(ici).startsWith(jeu.home.path)) "~" + normal(ici).removePrefix(jeu.home.path) else ici)))
        l.add(t("carte.legende"))
        val leg = legende(jeu).ifEmpty { listOf(t("carte.monde.legende.rien")) }
        l.add(t("carte.monde.legende") + " " + leg.joinToString(" · "))
        val (trouves, total) = Quetes.secrets(jeu)
        l.add(t("carte.secrets", "n" to trouves, "total" to total))
        val s = liste(m(jeu), "sauvage")
        if (s.isNotEmpty()) l.add("${nomPiece("sauvage")} : " + Langue.raccourcir(s.takeLast(4).joinToString(", "), 60) + " " + t("carte.sauvage.lecture"))
        if (!Histoire.pieceOuverte(jeu, "vestibule")) l.add(t("carte.vide"))
        return l
    }

    /** En arabe et en ourdou, chaque ligne de tree reste de gauche à droite : marque LRM. */
    private const val LRM = "‎"

    /** La carte en texte : `tree` annoté (le dessin, lui, est fait par CarteVue). Marque ce qui est montré. */
    fun carte(jeu: Jeu): List<String> {
        val g = if (Langue.rtl) LRM else ""
        val l = mutableListOf("── 🗺 " + t("carte.monde.titre", "nom" to jeu.nom) + " ──", "")
        for (n in noeuds(jeu, marquer = true)) {
            if (n.genre == "suite") { l.add(g + texteTree(n)); continue }
            val lab = if (n.brume) "░░░░ ???" else emoji(n) + " " + n.etiquette
            var s = g + texteTree(n) + "  " + lab
            if (n.marques.isNotEmpty()) s += " " + n.marques
            if (n.ici) s += " ◉ " + t("carte.monde.ici")
            if (n.nouveau) s += " ✨ " + t("carte.monde.nouveau")
            l.add(s)
        }
        l.add("")
        l.addAll(pied(jeu))
        return l
    }

    /** Pour les tests : la carte en texte n'a pas de colonnes à aligner (le dessin est aligné par Carte.mettreEnPage). */
    fun verifierLargeur(lignes: List<String>): Set<Int> = setOf(0)
}
