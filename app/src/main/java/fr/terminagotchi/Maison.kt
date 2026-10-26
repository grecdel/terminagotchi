package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * La maison (portage de pc/tg/maison.py) : les pièces sont de vrais dossiers du terrain, la carte se dévoile en
 * les visitant.
 *
 *   ~/terrain_terminagotchi/            la grande salle
 *       vestibule/                      chapitre 1 (l'œuf)
 *       nid/                            chapitre 2
 *       grenier/ cave/ bibliotheque/ salle_des_machines/ dortoir/ atelier/ tour/   chapitres 3 à 9
 *       coeur/                          chapitre 10 (ouvert quand 5 ailes sont réveillées)
 *       jardin/                         le jardin du téléphone
 *       (plus des sous-pièces, des couloirs et des pièces secrètes « .cachette »)
 *
 * Où est l'enfant ? Sur le téléphone, c'est simple : le terminal de l'appli (Shell.kt) gère lui-même « cd », son
 * dossier courant est connu après chaque commande (Tour.apresCommande le reçoit). Le PC, lui, le devine par
 * l'invite du shell et en rejouant les « cd » de l'historique. Une pièce est « visitée » quand on y est vraiment
 * entré. La carte ne montre que celles-là.
 *
 * Terres sauvages : tout ce qui est hors de la maison de l'appli (/system, /proc…). On peut y regarder (lecture
 * seule), le jeu prévient : on ne touche à rien là-bas. Le jeu n'y écrit jamais rien.
 *
 * La carte : le même plan que sur PC (4 étages de 3 pièces, brouillard, ◉ ✓ ▶ ★ 🐾), mais des cases plus étroites
 * (l'écran du téléphone) : l'icône et les signes sur la 1re ligne, le nom de la pièce sur la 2e.
 */
object Maison {
    val AILES = listOf("grenier", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier", "tour")
    val PIECES = listOf("vestibule", "nid") + AILES + "coeur"
    val ICONES = mapOf("vestibule" to "🥚", "nid" to "🏠", "grenier" to "🌿", "cave" to "🔒", "bibliotheque" to "📚",
        "salle_des_machines" to "🔥", "dortoir" to "👻", "atelier" to "🔧", "tour" to "📡", "coeur" to "💜",
        "recoins" to "🚪", "sauvage" to "🌲", "jardin" to "📱")
    /** le plan : 4 étages de 3 pièces (le grenier et la tour en haut, la cave au sous-sol) */
    val PLAN = listOf(listOf("grenier", "bibliotheque", "tour"), listOf("dortoir", "coeur", "atelier"),
        listOf("vestibule", "nid", "salle_des_machines"), listOf("recoins", "cave", "sauvage"))
    /** colonnes d'une case de la carte (20 sur PC : l'écran du téléphone est plus étroit) */
    const val LARGE = 14
    val PRUDENCE = setOf("rm", "rmdir", "mv", "chmod", "chown", "del", "remove-item", "move-item", "ren")

    fun m(jeu: Jeu): JSONObject {
        val m = jeu.module("maison")
        for (k in listOf("visites", "sauvage")) if (!m.has(k)) m.put(k, JSONArray())
        if (!m.has("cwd")) m.put("cwd", JSONObject.NULL)
        if (!m.has("averti")) m.put("averti", 0L)
        if (!m.has("prudence")) m.put("prudence", 0L)
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

    /**
     * Après une commande tapée (ligne, null si c'est le tour périodique) : le dossier courant du terminal (cwd)
     * est visité. Renvoie les commandes tapées (pas collées) avec leur dossier courant.
     */
    fun suivre(jeu: Jeu, ligne: String?, colle: Boolean, cwd: File?): List<Pair<String, String?>> {
        val m = m(jeu)
        val cur = cwd?.path ?: ici(jeu) ?: jeu.home.path
        val apres = mutableListOf<Pair<String, String?>>()
        if (ligne != null && !colle && !Regles.estColle(ligne) && ligne.isNotBlank()) {
            visiter(jeu, cur)
            prudence(jeu, ligne, cur)
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
        return apres
    }

    // ---------------------------------------------------------------- la carte
    fun visitee(jeu: Jeu, p: String): Boolean = liste(m(jeu), "visites").any { it == p || it.startsWith("$p/") }

    /** Les familles des monstres sauvages présents (le dressage en cours). */
    private fun famillesSauvages(jeu: Jeu): List<String> {
        val d = jeu.module("dressage").optJSONObject("en_cours") ?: return emptyList()
        return listOfNotNull(Bestiaire.espece(d.optString("espece"))?.famille)
    }

    /** Les petits signes d'une pièce : ◉ tu es ici, ✓ réveillée, ▶ en cours, ★ quête, 🐾 monstres. */
    fun marques(jeu: Jeu, p: String): String {
        val sb = StringBuilder()
        if (pieceDe(jeu) == p) sb.append("◉")
        val ch = Histoire.chapitreDePiece(p)
        if (ch != null && ch.id in Histoire.ailes(jeu)) sb.append("✓")
        else if (ch != null && Histoire.chap(jeu) == ch.id) sb.append("▶")
        if (Quetes.etoile(jeu, p)) sb.append("★")
        val fam = ch?.famille
        if (fam != null && fam in famillesSauvages(jeu)) sb.append("🐾")
        return sb.toString()
    }

    /** Les autres dossiers visités (couloirs, repaires des monstres, donjon, jardin, pièces inventées). */
    private fun autres(jeu: Jeu): List<String> =
        liste(m(jeu), "visites").filter { it.isNotEmpty() }.map { it.split("/")[0] }.filter { it !in PIECES }.toSortedSet().toList()

    private fun brouillard() = "░".repeat(LARGE - 2)

    /** Deux lignes de texte pour une case du plan (l'icône et les signes, puis le nom). */
    private fun case(jeu: Jeu, p: String): Pair<String, String> {
        if (p == "recoins") {
            val a = autres(jeu)
            if (a.isEmpty()) return brouillard() to ""
            return "${ICONES[p]} " + t("carte.recoins.n", "n" to a.size) + (if (famillesSauvages(jeu).isNotEmpty()) " 🐾" else "") to nomPiece(p)
        }
        if (p == "sauvage") {
            if (liste(m(jeu), "sauvage").isEmpty()) return brouillard() to ""
            return "${ICONES[p]} ⚠" to nomPiece(p)
        }
        if (!Histoire.pieceOuverte(jeu, p)) return "" to ""
        if (!visitee(jeu, p)) return brouillard() to "?" + (if (p == "vestibule") "★" else "")
        return "${ICONES[p] ?: ""} " + marques(jeu, p) to nomPiece(p)
    }

    private fun ajuste(x: String) = Langue.ajuster(Langue.raccourcir(x.replace(RLM, ""), LARGE - 2), LARGE - 2)

    /** En arabe et en ourdou, chaque ligne du plan reste de gauche à droite (sinon les cases s'inversent) : marque LRM. */
    private const val RLM = "\u200F"
    private const val LRM = "\u200E"

    /** Le plan de la maison, avec le brouillard. */
    fun carte(jeu: Jeu): List<String> {
        val h = "─".repeat(LARGE)
        val l = mutableListOf("── 🗺 " + t("carte.titre", "nom" to jeu.nom) + " ──", "")
        val g = if (Langue.rtl) LRM else ""
        l.add("$g ┌" + listOf(h, h, h).joinToString("┬") + "┐")
        for ((i, rang) in PLAN.withIndex()) {
            val cases = rang.map { case(jeu, it) }
            for (k in 0..1) l.add("$g │" + cases.joinToString("│") { c -> " " + ajuste(if (k == 0) c.first else c.second) + " " } + "│")
            if (i < PLAN.size - 1) l.add("$g ├" + listOf(h, h, h).joinToString("┼") + "┤")
        }
        l.add("$g └" + listOf(h, h, h).joinToString("┴") + "┘")
        l.add(t("carte.legende"))
        l.add("")
        val ici = ici(jeu)
        val r = rel(jeu, ici)
        if (r != null) l.add("◉ " + t("carte.ici", "lieu" to if (r.isNotEmpty()) "~/${jeu.terrain.name}/$r" else "~/${jeu.terrain.name}"))
        else if (ici != null) l.add("◉ " + t("carte.dehors", "lieu" to (if (normal(ici).startsWith(jeu.home.path)) "~" + normal(ici).removePrefix(jeu.home.path) else ici)))
        val (trouves, total) = Quetes.secrets(jeu)
        l.add(t("carte.secrets", "n" to trouves, "total" to total))
        val sous = linkedMapOf<String, java.util.TreeSet<String>>()
        for (v in liste(m(jeu), "visites")) {
            if ("/" in v && v.split("/")[0] in PIECES) {
                val p = v.substringBefore("/")
                sous.getOrPut(p) { java.util.TreeSet() }.add(v.substringAfter("/").split("/")[0])
            }
        }
        for (p in PIECES) sous[p]?.let { l.add("  ${nomPiece(p)} : " + Langue.raccourcir(it.joinToString(", "), 60)) }
        val a = autres(jeu)
        if (a.isNotEmpty()) l.add("  ${nomPiece("recoins")} : " + Langue.raccourcir(a.joinToString(", "), 60))
        val s = liste(m(jeu), "sauvage")
        if (s.isNotEmpty()) l.add("  ${nomPiece("sauvage")} : " + Langue.raccourcir(s.takeLast(4).joinToString(", "), 60) + " " + t("carte.sauvage.lecture"))
        if (!Histoire.pieceOuverte(jeu, "vestibule")) l.add(t("carte.vide"))
        return l
    }

    /** Pour les tests : toutes les lignes du plan ont la même largeur à l'écran. */
    fun verifierLargeur(lignes: List<String>): Set<Int> =
        lignes.map { it.removePrefix(LRM) }.filter { it.startsWith(" │") || it.startsWith(" ┌") || it.startsWith(" ├") || it.startsWith(" └") }
            .map { Langue.largeur(it) }.toSet()
}
