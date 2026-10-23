package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.sqrt

class Etape(
    val dit: String,
    val cmd: String,
    val bravo: String,
    val re: Regex? = null,
    val fs: ((Jeu) -> Boolean)? = null,
    val astuce: String? = null,
)

class Lecon(val titre: String, val skill: String, val niveau: Int, val etapes: List<Etape>)

/** Règles communes : catégories, compétences, textes, piège anti copier-coller. */
object Regles {
    val STATS = listOf("Intelligence", "Agilité", "Force", "Endurance")
    val COURT = mapOf("Intelligence" to "INT", "Agilité" to "AGI", "Force" to "FOR", "Endurance" to "END")
    val COULEUR = mapOf("Intelligence" to 39, "Agilité" to 78, "Force" to 203, "Endurance" to 221)

    val CATEGORIES: Map<String, Set<String>> = mapOf(
        "Intelligence" to setOf("git", "python", "python3", "sh", "bash", "alias", "vi", "nano", "awk", "sed"),
        "Agilité" to setOf("ping", "curl", "wget", "ip", "ifconfig", "netstat", "nslookup", "am", "pm",
            "applis", "ouvre", "web", "carte", "appelle", "sms", "partage", "lampe", "vibre", "batterie", "dis",
            "reglages"),
        "Force" to setOf("top", "ps", "kill", "df", "du", "free", "uname", "whoami", "date", "id", "getprop",
            "dumpsys", "uptime"),
        "Endurance" to setOf("ls", "cd", "cp", "mv", "rm", "mkdir", "rmdir", "cat", "touch", "find", "grep",
            "head", "tail", "chmod", "pwd", "echo", "stat", "more", "less", "wc", "sort", "tree"),
    )

    val SKILLS: Map<String, Set<String>> = mapOf(
        "Boussole" to setOf("cd", "ls", "pwd"),
        "Bâtisseur" to setOf("mkdir", "touch", "echo"),
        "Inspecteur" to setOf("cat", "grep", "head", "tail", "find", "more", "less"),
        "Gardien" to setOf("chmod"),
        "Nettoyeur" to setOf("cp", "mv", "rm"),
    )

    val STADES = listOf("Œuf", "Bébé", "Ado", "Adulte")
    val FORMES = mapOf("Intelligence" to "Hacker", "Force" to "Titan", "Agilité" to "Éclair", "Endurance" to "Carapace")

    val TRAITS = mapOf(
        "curieux" to listOf("Qu'est-ce qu'il y a dans ce dossier ?", "Apprends-moi une nouvelle commande !",
            "Je me demande ce que fait « ls -l »…", "Et si on explorait un peu ?"),
        "farceur" to listOf("Et si on renommait tous tes fichiers ? Je plaisante !", "rm -rf ? Jamais de la vie, hihi.",
            "Tu tapes vite… pour un humain.", "J'ai caché un fichier quelque part. Ou pas."),
        "gourmand" to listOf("Une petite commande, juste une ?", "J'ai un creux de 512 octets.",
            "Miam, un « ls » bien frais.", "Les « grep » sont mes préférés, croustillants !"),
        "philosophe" to listOf("Sommes-nous tous dans le sous-dossier de quelqu'un ?",
            "Un fichier supprimé existe-t-il encore dans nos cœurs ?", "pwd… mais où suis-je VRAIMENT ?",
            "Le terminal est noir, mais l'avenir est clair."),
    )
    val FAIM = listOf("J'ai faim… tape quelque chose !", "Mon ventre fait « segmentation fault ».",
        "Même un petit « pwd » me ferait du bien…")
    val OEUF = listOf("…", "*toc toc*", "*l'œuf bouge un peu*", "*crac ?*")
    val COLLE = listOf("Hé ! Tu as collé du texte… tape-la toi-même, sinon ça ne rentre pas dans ma tête !",
        "Copier-coller détecté : ça n'a aucun goût. Avec tes doigts, s'il te plaît !",
        "Bien essayé ! Mais je ne mange que les commandes tapées à la main.")

    // Lettres cyrilliques identiques à l'œil : une commande affichée puis collée ne fonctionne pas.
    private val HOMO = mapOf('a' to 'а', 'c' to 'с', 'e' to 'е', 'o' to 'о', 'p' to 'р', 'x' to 'х',
        'y' to 'у', 'i' to 'і', 's' to 'ѕ', 'd' to 'ԁ', 'h' to 'һ', 'j' to 'ј')
    private val PIEGES: Set<Char> = HOMO.values.toSet() + '\u00a0'

    fun piege(cmd: String): String {
        val sb = StringBuilder()
        var fait = false
        for (c in cmd) {
            val h = HOMO[c]
            when {
                !fait && h != null -> { sb.append(h); fait = true }
                c == ' ' -> sb.append('\u00a0')
                else -> sb.append(c)
            }
        }
        return sb.toString()
    }

    fun estColle(l: String) = l.any { it in PIEGES }
    fun niveau(xp: Int) = sqrt(xp / 10.0).toInt() + 1
    fun stade(n: Int) = when {
        n < 2 -> 0
        n < 5 -> 1
        n < 10 -> 2
        else -> 3
    }

    fun premierMot(l: String): String =
        l.trim().split(Regex("\\s+")).firstOrNull()?.lowercase()?.substringAfterLast('/') ?: ""

    /** Le lexique : toutes les commandes utiles du terminal Android, avec leur explication. */
    val LEXIQUE: List<Triple<String, String, String>> = run {
        val f = "🗂 Fichiers et dossiers"
        val l = "🔎 Lire et chercher"
        val y = "⚙ Système"
        val t = "📱 Ton téléphone (commandes de l'appli)"
        val c = "🐾 Ta créature"
        listOf(
            Triple("pwd", "affiche le dossier où tu te trouves", f),
            Triple("ls", "liste le contenu (ls -a : avec les cachés, ls -l : les détails)", f),
            Triple("cd", "change de dossier (cd nom, cd .. pour remonter, cd ~ pour rentrer)", f),
            Triple("mkdir", "crée un dossier", f),
            Triple("touch", "crée un fichier vide", f),
            Triple("echo", "affiche un texte (echo texte > fichier : l'écrit dedans)", f),
            Triple("cp", "copie un fichier (cp -r : un dossier)", f),
            Triple("mv", "déplace ou renomme", f),
            Triple("rm", "supprime, sans corbeille ! (rm -r : un dossier)", f),
            Triple("rmdir", "supprime un dossier vide", f),
            Triple("chmod", "change les droits (chmod 444 : lecture seule)", f),
            Triple("cat", "affiche le contenu d'un fichier", l),
            Triple("head", "affiche le début d'un fichier", l),
            Triple("tail", "affiche la fin d'un fichier", l),
            Triple("grep", "cherche un mot dans un fichier", l),
            Triple("find", "trouve des fichiers par leur nom (find . -name \"*.txt\")", l),
            Triple("wc", "compte lignes, mots et caractères", l),
            Triple("sort", "trie les lignes d'un fichier", l),
            Triple("stat", "tous les détails d'un fichier", l),
            Triple("date", "la date et l'heure", y),
            Triple("whoami", "ton nom d'utilisateur (sur Android, celui de l'appli)", y),
            Triple("id", "ton identité et tes groupes", y),
            Triple("uptime", "depuis quand le téléphone est allumé", y),
            Triple("uname", "infos sur le système (uname -a : tout)", y),
            Triple("df", "espace libre sur le stockage (df -h : lisible)", y),
            Triple("du", "taille d'un dossier (du -sh dossier)", y),
            Triple("ps", "programmes en cours", y),
            Triple("ping", "teste la connexion (ping -c 3 example.com)", y),
            Triple("clear", "efface l'écran du terminal", y),
            Triple("applis", "liste tes applis (applis what : filtre)", t),
            Triple("ouvre", "lance une appli : ouvre whatsapp", t),
            Triple("web", "ouvre un site ou une recherche : web météo paris", t),
            Triple("carte", "cherche un lieu : carte tour eiffel", t),
            Triple("appelle", "prépare un appel (sans appeler) : appelle 0612345678", t),
            Triple("sms", "prépare un SMS : sms 0612345678 coucou", t),
            Triple("partage", "envoie un texte via l'appli de ton choix : partage salut !", t),
            Triple("lampe", "lampe torche : lampe on / lampe off", t),
            Triple("vibre", "fait vibrer : vibre 500", t),
            Triple("batterie", "niveau de batterie", t),
            Triple("dis", "le téléphone parle : dis bonjour", t),
            Triple("reglages", "ouvre les réglages : reglages wifi (bluetooth, son, ecran…)", t),
            Triple("caresse", "un câlin pour ta créature", c),
            Triple("danse", "elle danse pour toi", c),
            Triple("parle", "elle te dit ce qu'elle pense", c),
            Triple("joue", "pierre-feuille-ciseaux : joue pierre", c),
            Triple("devine", "devine son nombre (1 à 20) : devine 10", c),
            Triple("etat", "sa fiche complète", c),
            Triple("renomme", "change son nom : renomme Pixel", c),
        )
    }

    fun barre(v: Double, max: Double, n: Int): String {
        val k = ((v / max) * n).toInt().coerceIn(0, n)
        return "▰".repeat(k) + "▱".repeat(n - k)
    }
}

/** L'état de la créature, sauvegardé en JSON dans le stockage privé de l'appli. */
class Jeu(ctx: Context) {
    val home: File = File(ctx.filesDir, "maison").apply { mkdirs() }
    val terrain: File get() = File(home, "terrain_terminagotchi")
    private val fichier = File(ctx.filesDir, "sauvegarde.json")

    var nom = ""
    var xp = 0
    var faim = 80.0
    var total = 0
    var dernierTick = System.currentTimeMillis()
    val stats = linkedMapOf<String, Int>().apply { Regles.STATS.forEach { put(it, 0) } }
    val vus = mutableSetOf<String>()
    val journal = mutableListOf<String>()
    val skills = mutableListOf<String>()
    var lecon = 0
    var etape = 0
    var forme: String? = null
    var trait = Regles.TRAITS.keys.random()
    var bulle = ""
    var bulleFin = 0L
    var colles = 0
    private val dernierJeu = mutableMapOf<String, Long>()

    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    val lecons: List<Lecon> = listOf(
        Lecon("Où suis-je ?", "Boussole", 1, listOf(
            Etape("Coucou ! Première question : où sommes-nous ?", "pwd",
                "pwd = « print working directory » : le dossier où tu te trouves.", re = r("^pwd\\b")),
            Etape("Regarde ce qu'il y a autour de nous.", "ls",
                "Voilà les fichiers et dossiers d'ici !", re = r("^ls\\b")),
            Etape("Rentrons à la maison (ton dossier perso).", "cd ~",
                "~ veut dire « mon dossier perso ». Tu sais naviguer !", re = r("^cd(\\s+~/?)?\\s*$"),
                astuce = "Le ~ est dans la rangée de touches au-dessus du clavier. (« cd » tout seul marche aussi !)"),
        )),
        Lecon("Construire mon nid", "Bâtisseur", 1, listOf(
            Etape("Il me faut un terrain de jeu. Crée-le depuis ton dossier perso.", "mkdir terrain_terminagotchi",
                "mkdir = « make directory » : créer un dossier.", fs = { it.terrain.isDirectory }),
            Etape("Entrons dedans.", "cd terrain_terminagotchi", "On est chez nous maintenant.",
                re = r("^cd\\s+.*terrain_terminagotchi")),
            Etape("Construis-moi un nid !", "mkdir nid", "Il est parfait, merci !",
                fs = { File(it.terrain, "nid").isDirectory }),
        )),
        Lecon("Le garde-manger", "Inspecteur", 1, listOf(
            Etape("J'ai faim… mets une pomme dans mon garde-manger.", "echo pomme > nid/repas.txt",
                "« > » envoie le texte dans un fichier (et l'écrase s'il existe !).",
                fs = { File(it.terrain, "nid/repas.txt").isFile }),
            Etape("Vérifie ce qu'il y a dedans.", "cat nid/repas.txt",
                "Toujours vérifier avant d'agir : réflexe de pro.", re = r("^(cat|more|less|head)\\b.*repas")),
            Etape("Cherche le mot « pomme » dans le fichier.", "grep pomme nid/repas.txt",
                "Chercher un mot dans des fichiers : super-pouvoir débloqué.", re = r("^grep\\b.*pomme")),
        )),
        Lecon("Le bouclier", "Gardien", 1, listOf(
            Etape("Qui a le droit de toucher à mon repas ?", "ls -l nid",
                "r = lire, w = écrire, x = exécuter.", re = r("^(ls\\s+-\\w*l|stat)\\b")),
            Etape("Protège-le pour que personne ne l'abîme !", "chmod 444 nid/repas.txt",
                "Bouclier activé : le fichier est en lecture seule.",
                fs = { val f = File(it.terrain, "nid/repas.txt"); f.isFile && !f.canWrite() }),
            Etape("Essaie d'y ajouter une poire, pour voir…", "echo poire >> nid/repas.txt",
                "Refusé ! « >> » ajoute à la fin, mais le bouclier tient.", re = r(">>.*repas")),
        )),
        Lecon("Grand ménage", "Nettoyeur", 1, listOf(
            Etape("Fais une copie de secours de mon repas.", "cp nid/repas.txt nid/secours.txt",
                "cp = copier. L'original ne bouge pas.", fs = { File(it.terrain, "nid/secours.txt").isFile }),
            Etape("Déplace la copie dans le terrain, sous le nom reserve.txt.", "mv nid/secours.txt reserve.txt",
                "mv sert à déplacer ET à renommer.", fs = { File(it.terrain, "reserve.txt").isFile }),
            Etape("On n'en a plus besoin : supprime-la.", "rm reserve.txt",
                "Attention : rm ne passe PAS par la corbeille. Vérifie toujours avant !",
                fs = { !File(it.terrain, "reserve.txt").exists() }),
        )),
    )

    init {
        charger()
    }

    val existe: Boolean get() = nom.isNotEmpty()
    val niveau: Int get() = Regles.niveau(xp)
    val stade: Int get() = Regles.stade(niveau)

    // ------------------------------------------------------------ sauvegarde
    private fun charger() {
        if (!fichier.exists()) return
        try {
            val o = JSONObject(fichier.readText())
            nom = o.optString("nom")
            xp = o.optInt("xp")
            faim = o.optDouble("faim", 80.0)
            total = o.optInt("total")
            dernierTick = o.optLong("dernierTick", dernierTick)
            o.optJSONObject("stats")?.let { s -> Regles.STATS.forEach { stats[it] = s.optInt(it) } }
            o.optJSONArray("vus")?.let { a -> for (i in 0 until a.length()) vus.add(a.getString(i)) }
            o.optJSONArray("journal")?.let { a -> for (i in 0 until a.length()) journal.add(a.getString(i)) }
            o.optJSONArray("skills")?.let { a -> for (i in 0 until a.length()) skills.add(a.getString(i)) }
            lecon = o.optInt("lecon")
            etape = o.optInt("etape")
            forme = if (o.has("forme") && !o.isNull("forme")) o.getString("forme") else null
            trait = o.optString("trait", trait)
            bulle = o.optString("bulle")
            bulleFin = o.optLong("bulleFin")
            colles = o.optInt("colles")
        } catch (e: Exception) {
            // sauvegarde illisible : on repart de zéro plutôt que de planter
        }
    }

    fun sauver() {
        val o = JSONObject()
        o.put("nom", nom)
        o.put("xp", xp)
        o.put("faim", faim)
        o.put("total", total)
        o.put("dernierTick", dernierTick)
        o.put("stats", JSONObject(stats.toMap()))
        o.put("vus", JSONArray(vus.toList()))
        o.put("journal", JSONArray(journal))
        o.put("skills", JSONArray(skills))
        o.put("lecon", lecon)
        o.put("etape", etape)
        o.put("forme", forme ?: JSONObject.NULL)
        o.put("trait", trait)
        o.put("bulle", bulle)
        o.put("bulleFin", bulleFin)
        o.put("colles", colles)
        val tmp = File(fichier.parentFile, "sauvegarde.tmp")
        tmp.writeText(o.toString())
        tmp.renameTo(fichier)
    }

    // ------------------------------------------------------------ vie de la créature
    fun log(msg: String) {
        val heure = SimpleDateFormat("HH:mm", Locale.FRANCE).format(Date())
        journal.add("$heure $msg")
        while (journal.size > 6) journal.removeAt(0)
    }

    fun dire(texte: String, secondes: Int = 8) {
        bulle = texte
        bulleFin = System.currentTimeMillis() + secondes * 1000L
    }

    fun bulleActive(): String = if (System.currentTimeMillis() < bulleFin) bulle else ""

    fun dominant(): String =
        if (stats.values.all { it == 0 }) Regles.STATS.random() else stats.maxByOrNull { it.value }!!.key

    fun tick() {
        val now = System.currentTimeMillis()
        val rate = if ("Gardien" in skills) 720_000.0 else 360_000.0     // ms par point de faim
        faim = (faim - (now - dernierTick) / rate).coerceAtLeast(0.0)
        dernierTick = now
    }

    fun ajouterXp(n: Int) {
        val avant = niveau
        xp += n
        val apres = niveau
        if (apres <= avant) return
        if (Regles.stade(apres) > Regles.stade(avant)) {
            if (Regles.stade(apres) == 1) {
                log("✨ L'œuf a éclos !")
                dire("Bonjour le monde ! … C'est comme ça qu'on dit, non ?", 10)
            } else {
                if (forme == null) forme = dominant()
                log("✨ ÉVOLUTION → ${Regles.STADES[Regles.stade(apres)]} ${Regles.FORMES[forme ?: ""] ?: ""} !")
                dire("Waouh… je me sens différent !", 10)
            }
        } else {
            log("⬆ Niveau $apres !")
        }
        val l = leconCourante()
        if (l != null && l.niveau == apres) dire("J'ai quelque chose à t'apprendre !", 10)
    }

    /** Mange une commande. Renvoie false si elle a été refusée (collée). */
    fun manger(ligne: String, colle: Boolean): Boolean {
        if (colle || Regles.estColle(ligne)) {
            colles++
            log("✖ copier-coller détecté : pas de nourriture")
            dire(Regles.COLLE.random(), 10)
            return false
        }
        val cmd = Regles.premierMot(ligne)
        if (cmd.isEmpty()) return false
        total++
        var gain = 1
        var msg = "a mangé « $cmd »"
        val stat = Regles.CATEGORIES.entries.firstOrNull { cmd in it.value }?.key
        if (stat != null) {
            stats[stat] = (stats[stat] ?: 0) + 1
            gain += 1
            msg += " +${Regles.COURT[stat]}"
        }
        if (cmd in Commandes.CREATURE) {
            val maintenant = System.currentTimeMillis()
            if (maintenant - (dernierJeu[cmd] ?: 0L) < 60_000) {
                faim = (faim + 1).coerceAtMost(100.0)
                log("$msg (déjà joué il y a peu : pas d'XP)")
                return true
            }
            dernierJeu[cmd] = maintenant
        }
        if (vus.add(cmd)) {
            gain += 5
            msg += " ★ nouveau goût"
        }
        if (skills.any { Regles.SKILLS[it]?.contains(cmd) == true }) {
            gain *= 2
            msg += " ×2"
        }
        faim = (faim + 3).coerceAtMost(100.0)
        log(msg)
        ajouterXp(gain)
        return true
    }

    fun leconCourante(): Lecon? = if (lecon < lecons.size) lecons[lecon] else null

    fun etapeCourante(): Etape? {
        val l = leconCourante() ?: return null
        return if (niveau >= l.niveau) l.etapes[etape] else null
    }

    private fun avancer(l: Lecon): Boolean {
        val e = l.etapes[etape]
        log("✔ ${e.cmd}")
        dire(e.bravo, 12)
        etape++
        if (etape < l.etapes.size) {
            ajouterXp(5)
            return true
        }
        etape = 0
        lecon++
        if (l.skill !in skills) skills.add(l.skill)
        log("🎓 « ${l.titre} » finie → ${l.skill} !")
        ajouterXp(20)
        dire(if (lecon >= lecons.size)
            "Tronc commun terminé, bravo ! La suite (branche Android) arrive dans la prochaine version."
        else "Leçon finie ! J'ai appris « ${l.skill} » grâce à toi.", 14)
        return false
    }

    fun leconTick(ligne: String?, colle: Boolean) {
        val l = leconCourante() ?: return
        if (niveau < l.niveau) return
        val e = l.etapes[etape]
        if (ligne != null && !colle && !Regles.estColle(ligne) && e.re?.containsMatchIn(ligne.trim()) == true) {
            if (!avancer(l)) return
        }
        val l2 = leconCourante() ?: return
        if (l2 !== l || niveau < l2.niveau) return
        if (l2.etapes[etape].fs?.invoke(this) == true) avancer(l2)
    }

    fun parlerSiSilencieux() {
        if (bulleActive().isNotEmpty()) return
        when {
            stade == 0 -> dire(Regles.OEUF.random())
            faim < 30 -> dire(Regles.FAIM.random())
            else -> dire(Regles.TRAITS[trait]?.random() ?: "…")
        }
    }

    // ------------------------------------------------------------ textes affichés
    fun humeur() = when {
        faim >= 60 -> "repu"
        faim >= 30 -> "petit creux"
        faim > 0 -> "affamé !"
        else -> "NOURRIS-MOI…"
    }

    fun titre(): String {
        val fo = forme
        val f = if (stade >= 2 && fo != null) " ${Regles.FORMES[fo]}" else ""
        return "$nom · ${Regles.STADES[stade]}$f · niv. $niveau"
    }

    fun texteXp(): String {
        val lo = 10 * (niveau - 1) * (niveau - 1)
        val hi = 10 * niveau * niveau
        return "xp   ${Regles.barre((xp - lo).toDouble(), (hi - lo).toDouble(), 8)}  $xp/$hi"
    }

    fun texteFaim() = "faim ${Regles.barre(faim, 100.0, 8)}  ${humeur()}"

    fun texteStats() = Regles.STATS.joinToString("  ") { "${Regles.COURT[it]} ${stats[it]}" }

    fun texteLecon(): String? {
        val l = leconCourante() ?: return null
        if (niveau < l.niveau) {
            val manque = 10 * (l.niveau - 1) * (l.niveau - 1) - xp
            return "Prochaine leçon au niveau ${l.niveau} : il me manque $manque XP.\n" +
                "Nourris-moi avec des commandes jamais goûtées (📖 Lexique) !"
        }
        val e = l.etapes[etape]
        val astuce = if (e.astuce != null) "\n${e.astuce}" else ""
        return "${l.titre} (${etape + 1}/${l.etapes.size}) · ${e.dit}\n➜ ${Regles.piege(e.cmd)}$astuce"
    }

    fun infoWidget(): String {
        val b = bulleActive()
        if (b.isNotEmpty()) return "« $b »"
        val e = etapeCourante()
        if (e != null) return "Leçon ➜ ${Regles.piege(e.cmd)}"
        return journal.lastOrNull()?.drop(6) ?: "Touche le bouton pour me nourrir !"
    }
}
