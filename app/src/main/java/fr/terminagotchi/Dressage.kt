package fr.terminagotchi

import android.content.res.Resources
import android.graphics.Typeface
import android.graphics.drawable.BitmapDrawable
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.DynamicDrawableSpan
import android.text.style.ForegroundColorSpan
import android.text.style.ImageSpan
import android.text.style.RelativeSizeSpan
import android.text.style.StyleSpan
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import kotlin.random.Random

/**
 * Dressage (même règle que sur PC) : un monstre apparaît pendant qu'on joue avec son familier ;
 * pour gagner sa confiance il faut réussir une suite de vraies commandes avant la fin du temps.
 * Le jeu vérifie le RÉSULTAT (dossier créé, fichier trié, bonne réponse donnée avec echo…).
 * Étapes 1 et 2 toujours : l'examiner (cat sa fiche), trouver son repaire (find).
 *
 * Difficulté progressive (selon le nombre de bestioles déjà dressées, voir plafond(), comme sur PC) :
 *  - le tout premier dressage : 2 épreuves simples (lire sa fiche, puis une commande d'un seul mot ou presque :
 *    pas de boucle for, pas de guillemets imbriqués, pas de tuyau) ;
 *  - puis le nombre d'épreuves et leur niveau montent peu à peu, jusqu'aux règles normales (selon la rareté de
 *    l'individu) à partir de 12 bestioles dressées ; +1 minute tant que tu as moins de 5 bestioles.
 * Quand une épreuve est PRESQUE réussie (faute de frappe, fichier au mauvais endroit, script sans echo, boucle
 * for sans « ; »…), une bulle donne un indice clair (voir indice()).
 * Si tu as déjà une troupe, un mini-combat a lieu d'abord (voir Combat.kt).
 */
object Dressage {
    // la difficulté dépend de la rareté de L'INDIVIDU (ses stats, sa variante…), pas de l'espèce
    private val DUREE = mapOf("commune" to 90, "peu commune" to 120, "rare" to 180, "épique" to 210, "légendaire" to 240, "mythique" to 300)
    private val NB = mapOf("commune" to 2, "peu commune" to 3, "rare" to 4, "épique" to 5, "légendaire" to 6, "mythique" to 7)
    private val NIV = mapOf("commune" to 1, "peu commune" to 2, "rare" to 3, "épique" to 3, "légendaire" to 3, "mythique" to 3)
    val ULTIMES = setOf("légendaire", "mythique")
    private val MOTS = listOf("octet", "pixel", "bug", "shell", "noyau", "cache", "paquet", "script", "fichier", "chat",
        "nuage", "clef", "boucle", "signal", "tuyau", "racine")

    /** Contexte d'une épreuve : dossier du repaire, nom du monstre, données tirées au hasard. */
    class Ctx(val d: File, val nom: String, val x: JSONObject, val lignes: List<String>, val terrain: File)

    class Epreuve(
        val fam: String, val id: String, val niveau: Int, private val butCle: String, private val explicationCle: String,
        val exemple: String, val prep: ((Ctx) -> Unit)? = null, val ok: (Ctx) -> Boolean,
    ) {
        val cle get() = "$fam:$id"
        /** la mission et son explication, dans la langue choisie (clés ep.* et aide.*, communes avec le PC) : modèles à remplir */
        val but: String get() = Langue.modele(butCle)
        val explication: String get() = Langue.modele(explicationCle)
    }

    // ---------------------------------------------------------------- outils de vérification
    private fun tape(c: Ctx, motif: String) = Regex(motif, RegexOption.IGNORE_CASE).let { r -> c.lignes.any { r.containsMatchIn(it) } }
    private fun repond(c: Ctx, rep: Any) =
        Regex("^\\s*echo\\s+[\"']?" + Regex.escape(rep.toString()) + "[\"']?\\s*$", RegexOption.IGNORE_CASE).let { r -> c.lignes.any { r.matches(it) } }
    private fun lire(f: File) = if (f.isFile) f.readText() else null
    private fun lignesDe(f: File) = lire(f)?.lines()?.map { it.trimEnd('\r') }?.filter { it.isNotBlank() }
    private fun liste(x: JSONObject, k: String) = x.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()

    private fun prepLignes(c: Ctx) {
        if (c.x.has("croquettes")) return
        val mots = MOTS.shuffled().take(6)
        val l = List(Random.nextInt(8, 16)) { mots.random() }
        File(c.d, "croquettes.txt").writeText(l.joinToString("\n") + "\n")   // mots-données : ils restent tels quels
        c.x.put("croquettes", JSONArray(l))
    }
    private fun prepBug(c: Ctx) {
        if (c.x.has("bug")) return
        val n = Random.nextInt(2, 6)
        val l = (List(6) { "INFO " + t("dress.fichier.bug.info", "i" to it) } +
            List(n) { "ERROR " + t("dress.fichier.bug.erreur", "i" to it) }).shuffled()
        File(c.d, "bug.log").writeText(l.joinToString("\n") + "\n")
        c.x.put("bug", n)
    }
    private fun prepCollier(c: Ctx) {
        if (c.x.has("empreinte")) return
        val mot = MOTS.random() + Random.nextInt(10, 99)
        File(c.d, "collier.txt").writeText(mot)
        c.x.put("empreinte", MessageDigest.getInstance("SHA-256").digest(mot.toByteArray()).joinToString("") { "%02x".format(it) }.take(8))
    }
    private fun prepScores(c: Ctx) {
        if (c.x.has("scores")) return
        val s = (100..9999).shuffled().take(8)
        File(c.d, "scores.txt").writeText(s.joinToString("\n") + "\n")
        c.x.put("scores", JSONArray(s))
    }
    private fun prepCorrompu(c: Ctx) {
        if (c.x.has("phrase")) return
        val p = Langue.brutes("dress.fichier.corrompu").random()
        c.x.put("phrase", p)
        File(c.d, "corrompu.txt").writeText(p.reversed() + "\n")
    }
    private fun prepCri(c: Ctx) {
        if (c.x.has("cri")) return
        // en MAJUSCULES ASCII : la commande « tr A-Z a-z » doit pouvoir les chuchoter
        val p = Langue.brutes("dress.fichier.cri").random()
        c.x.put("cri", p)
        File(c.d, "cri.txt").writeText(p + "\n")
    }
    /** Personne d'autre que toi ne peut toucher la cage (chmod 600). */
    private fun cagePrivee(c: Ctx): Boolean {
        val f = File(c.d, "enclos/cage")
        if (!f.exists()) return false
        return try {
            val perms = java.nio.file.Files.getPosixFilePermissions(f.toPath())
            perms.none { it.name.startsWith("GROUP") || it.name.startsWith("OTHERS") }
        } catch (e: Exception) { false }
    }
    private fun plusFrequents(l: List<String>): List<String> {
        val n = l.groupingBy { it }.eachCount()
        val m = n.values.maxOrNull() ?: return emptyList()
        return n.filterValues { it == m }.keys.toList()
    }
    private fun scores(c: Ctx) = c.x.optJSONArray("scores")!!.let { a -> (0 until a.length()).map { a.getInt(it) } }

    private val CAT = "^\\s*(cat|less|more|head)\\b"

    val EPREUVES: List<Epreuve> = listOf(
        // ---------------------------------------------------- rencontre (toujours en premier)
        Epreuve("Rencontre", "examiner", 1, "ep.rencontre.examiner",
            "aide.rencontre.examiner",
            "cat ~/terrain_terminagotchi/monstre_{nom_min}.txt") { c ->
            // le fichier s'appelle monstre_<nom sans accents> (Étincelot → monstre_etincelot.txt)
            tape(c, "$CAT.*monstre_(" + Regex.escape(Bestiaire.simple(c.nom)) + "|" + Regex.escape(c.nom.lowercase()) + ")") },
        Epreuve("Rencontre", "repaire", 1, "ep.rencontre.repaire",
            "aide.rencontre.repaire",
            "find ~/terrain_terminagotchi -name repaire_{nom_min}") { c -> tape(c, "^\\s*(find|ls)\\b.*repaire") },
        // ---------------------------------------------------- Fichiers
        Epreuve("Fichiers", "enclos", 1, "ep.fichiers.enclos",
            "aide.fichiers.enclos",
            "mkdir enclos") { c -> File(c.d, "enclos").isDirectory },
        Epreuve("Fichiers", "gamelle", 1, "ep.fichiers.gamelle",
            "aide.fichiers.gamelle", "touch enclos/gamelle") { c -> File(c.d, "enclos/gamelle").exists() },
        Epreuve("Fichiers", "doudou", 2, "ep.fichiers.doudou",
            "aide.fichiers.doudou",
            "mkdir -p enclos ; cp doudou.txt enclos/", { c -> File(c.d, "doudou.txt").writeText(t("dressa.fichier.doudou", "nom" to c.nom) + "\n") }) { c ->
            File(c.d, "doudou.txt").exists() && File(c.d, "enclos/doudou.txt").exists() },
        Epreuve("Fichiers", "renomme", 2, "ep.fichiers.renomme",
            "aide.fichiers.renomme", "mv vieux_nom.txt {nom_min}.txt",
            { c -> File(c.d, "vieux_nom.txt").writeText(t("dress.fichier.renomme") + "\n") }) { c ->
            !File(c.d, "vieux_nom.txt").exists() &&
                (File(c.d, Bestiaire.simple(c.nom) + ".txt").exists() || File(c.d, c.nom.lowercase() + ".txt").exists()) },
        Epreuve("Fichiers", "archive", 3, "epa.fichiers.archive",
            "aide.fichiers.archive",
            "tar -czf enclos.tar.gz enclos") { c -> listOf("enclos.tar.gz", "enclos.tgz", "enclos.tar").any { File(c.d, it).exists() } },
        // ---------------------------------------------------- Réseau
        Epreuve("Réseau", "ping", 1, "ep.reseau.ping",
            "aide.reseau.ping",
            "ping -c 3 localhost") { c -> tape(c, "^\\s*ping\\b.*(localhost|127\\.0\\.0\\.1)") },
        Epreuve("Réseau", "hote", 1, "ep.reseau.hote",
            "aide.reseau.hote",
            "hostname") { c -> tape(c, "^\\s*hostname\\b") },
        Epreuve("Réseau", "ip", 2, "ep.reseau.ip",
            "aide.reseau.ip",
            "ip a") { c -> tape(c, "^\\s*(ip\\s+(a|addr)|ifconfig)\\b") },
        // ---------------------------------------------------- Processus
        Epreuve("Processus", "ps", 1, "ep.processus.ps",
            "aidea.processus.ps",
            "ps -A") { c -> tape(c, "^\\s*(ps|top)\\b") },
        Epreuve("Processus", "heure", 1, "ep.processus.heure",
            "aide.processus.heure",
            "date") { c -> tape(c, "^\\s*date\\b") },
        // ---------------------------------------------------- Mémoire
        Epreuve("Mémoire", "place", 1, "ep.memoire.place",
            "aide.memoire.place",
            "df -h") { c -> tape(c, "^\\s*df\\b") },
        Epreuve("Mémoire", "ram", 1, "ep.memoire.ram",
            "aide.memoire.ram",
            "free -h") { c -> tape(c, "^\\s*free\\b") },
        Epreuve("Mémoire", "poids", 2, "ep.memoire.poids",
            "aide.memoire.poids",
            "du -sh ~/terrain_terminagotchi/nid") { c -> tape(c, "^\\s*du\\b") },
        Epreuve("Mémoire", "sac", 3, "ep.memoire.sac",
            "aide.memoire.sac",
            "ls sac | wc -l    puis    echo 7", { c ->
                val n = Random.nextInt(4, 10); File(c.d, "sac").mkdirs()
                for (i in 1..n) File(c.d, "sac/objet_$i").writeText("…"); c.x.put("sac", n) }) { c -> repond(c, c.x.optInt("sac")) },
        // ---------------------------------------------------- Sécurité
        Epreuve("Sécurité", "cage", 1, "ep.securite.cage",
            "aide.securite.cage",
            "mkdir -p enclos ; touch enclos/cage") { c -> File(c.d, "enclos/cage").exists() },
        Epreuve("Sécurité", "cachette", 1, "ep.securite.cachette",
            "aide.securite.cachette", "touch enclos/.secret") { c ->
            File(c.d, "enclos").listFiles()?.any { it.name.startsWith(".") && it.isFile } == true },
        Epreuve("Sécurité", "prive", 2, "ep.securite.prive",
            "aide.securite.prive",
            "chmod 600 enclos/cage") { c -> cagePrivee(c) },
        Epreuve("Sécurité", "empreinte", 3, "ep.securite.empreinte",
            "aide.securite.empreinte",
            "sha256sum collier.txt    puis    echo 1a2b3c4d", ::prepCollier) { c ->
            val r = Regex("^\\s*echo\\s+[\"']?([0-9a-f]{8,64})[\"']?\\s*$", RegexOption.IGNORE_CASE)
            c.lignes.any { l -> r.matchEntire(l)?.groupValues?.get(1)?.lowercase()?.startsWith(c.x.optString("empreinte")) == true } },
        // ---------------------------------------------------- Code
        Epreuve("Code", "chant", 1, "ep.code.chant",
            "aide.code.chant",
            "echo {nom} > chant.txt") { c -> lire(File(c.d, "chant.txt"))?.lowercase()?.contains(c.nom.lowercase()) == true },
        Epreuve("Code", "script", 2, "ep.code.script",
            "aide.code.script",
            "echo 'echo hop' > tour.sh ; chmod +x tour.sh") { c ->
            val f = File(c.d, "tour.sh"); lire(f)?.lowercase()?.contains("echo") == true && f.canExecute() },
        Epreuve("Code", "compte", 3, "ep.code.compte",
            "aide.code.compte",
            "for i in 1 2 3 4 5; do echo \$i; done > compte.txt") { c -> lignesDe(File(c.d, "compte.txt"))?.map { it.trim() } == listOf("1", "2", "3", "4", "5") },
        // ---------------------------------------------------- Matériel
        Epreuve("Matériel", "machine", 1, "ep.materiel.machine",
            "aide.materiel.machine",
            "uname -m") { c -> tape(c, "^\\s*uname\\b") },
        Epreuve("Matériel", "coeurs", 2, "ep.materiel.coeurs",
            "aide.materiel.coeurs", "nproc    puis    echo 8") { c ->
            repond(c, Runtime.getRuntime().availableProcessors()) },
        Epreuve("Matériel", "disques", 2, "ep.materiel.disques",
            "aidea.materiel.disques", "df") { c ->
            tape(c, "^\\s*(lsblk|df|fdisk\\s+-l)\\b") },
        // ---------------------------------------------------- Bugs
        Epreuve("Bugs", "erreurs", 1, "ep.bugs.erreurs",
            "aide.bugs.erreurs",
            "grep ERROR bug.log", ::prepBug) { c -> tape(c, "grep.*error") },
        Epreuve("Bugs", "combien", 2, "ep.bugs.combien",
            "aide.bugs.combien",
            "grep -c ERROR bug.log    puis    echo 3", ::prepBug) { c -> repond(c, c.x.optInt("bug")) },
        Epreuve("Bugs", "corrige", 3, "ep.bugs.corrige",
            "aide.bugs.corrige", "grep -v ERROR bug.log > corrige.log", ::prepBug) { c ->
            lignesDe(File(c.d, "corrige.log"))?.let { it.isNotEmpty() && it.none { l -> "ERROR" in l } } == true },
        // ---------------------------------------------------- Nuage
        Epreuve("Nuage", "nuage", 1, "ep.nuage.nuage",
            "aide.nuage.nuage", "mkdir nuage") { c -> File(c.d, "nuage").isDirectory },
        Epreuve("Nuage", "photos", 2, "ep.nuage.photos",
            "aide.nuage.photos", "touch nuage/photo1.jpg nuage/photo2.jpg nuage/photo3.jpg") { c ->
            (File(c.d, "nuage").listFiles()?.count { it.name.startsWith("photo") } ?: 0) >= 3 },
        Epreuve("Nuage", "copie", 3, "ep.nuage.copie",
            "aide.nuage.copie",
            "cp -r nuage nuage_copie") { c -> (File(c.d, "nuage_copie").listFiles()?.count { it.name.startsWith("photo") } ?: 0) >= 3 },
        // ---------------------------------------------------- Données
        Epreuve("Données", "debut", 1, "ep.donnees.debut",
            "aide.donnees.debut",
            "head croquettes.txt", ::prepLignes) { c -> tape(c, "^\\s*head\\b.*croquettes") },
        Epreuve("Données", "lignes", 2, "ep.donnees.lignes",
            "aide.donnees.lignes",
            "wc -l croquettes.txt    puis    echo 12", ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").size) },
        Epreuve("Données", "trie", 2, "ep.donnees.trie",
            "aide.donnees.trie",
            "sort croquettes.txt > trie.txt", ::prepLignes) { c -> lignesDe(File(c.d, "trie.txt")) == liste(c.x, "croquettes").sorted() },
        Epreuve("Données", "differentes", 3, "ep.donnees.differentes",
            "aide.donnees.differentes", "sort croquettes.txt | uniq | wc -l    puis    echo 5",
            ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").toSet().size) },
        // ---------------------------------------------------- Crypto
        Epreuve("Crypto", "lire", 1, "ep.crypto.lire",
            "aide.crypto.lire", "cat message.b64", { c ->
            val mot = MOTS.random(); c.x.put("secret", mot)
            File(c.d, "message.b64").writeText(android.util.Base64.encodeToString(mot.toByteArray(), android.util.Base64.NO_WRAP) + "\n") }) { c ->
            tape(c, "$CAT.*message") },
        Epreuve("Crypto", "decode", 2, "ep.crypto.decode",
            "aide.crypto.decode", "base64 -d message.b64    puis    echo motsecret", { c ->
            if (!c.x.has("secret")) { val mot = MOTS.random(); c.x.put("secret", mot)
                File(c.d, "message.b64").writeText(android.util.Base64.encodeToString(mot.toByteArray(), android.util.Base64.NO_WRAP) + "\n") } }) { c ->
            repond(c, c.x.optString("secret")) },
        // ---------------------------------------------------- IA
        Epreuve("IA", "bonjour", 1, "ep.ia.bonjour",
            "aide.ia.bonjour", "echo bonjour {nom}") { c ->
            tape(c, "^\\s*echo\\b.*" + Regex.escape(c.nom)) },
        Epreuve("IA", "chat", 2, "ep.ia.chat",
            "aide.ia.chat",
            "grep -c chat croquettes.txt    puis    echo 2", ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").count { "chat" in it }) },
        Epreuve("IA", "frequent", 3, "ep.ia.frequent",
            "aide.ia.frequent",
            "sort croquettes.txt | uniq -c | sort -n", ::prepLignes) { c -> plusFrequents(liste(c.x, "croquettes")).any { repond(c, it) } },
        // ---------------------------------------------------- Rétro
        Epreuve("Rétro", "calendrier", 1, "ep.retro.calendrier",
            "aide.retro.calendrier", "cal") { c -> tape(c, "^\\s*cal\\b") },
        Epreuve("Rétro", "record", 2, "ep.retro.record",
            "aide.retro.record", "sort -n scores.txt | tail -1    puis    echo 9876",
            ::prepScores) { c -> repond(c, scores(c).max()) },
        Epreuve("Rétro", "top3", 3, "ep.retro.top3",
            "aide.retro.top3", "sort -nr scores.txt | head -3 > top3.txt",
            ::prepScores) { c -> lignesDe(File(c.d, "top3.txt"))?.map { it.trim() } == scores(c).sortedDescending().take(3).map { it.toString() } },
        // ---------------------------------------------------- Glitch
        Epreuve("Glitch", "voir", 1, "ep.glitch.voir",
            "aide.crypto.lire", "cat corrompu.txt",
            ::prepCorrompu) { c -> tape(c, "$CAT.*corrompu") },
        Epreuve("Glitch", "repare", 2, "ep.glitch.repare",
            "aide.glitch.repare",
            "rev corrompu.txt > repare.txt", ::prepCorrompu) { c ->
            lire(File(c.d, "repare.txt"))?.trim() == c.x.optString("phrase") },
        Epreuve("Glitch", "chuchote", 3, "ep.glitch.chuchote",
            "aide.glitch.chuchote",
            "tr A-Z a-z < cri.txt > chuchote.txt", ::prepCri) { c ->
            lire(File(c.d, "chuchote.txt"))?.trim() == c.x.optString("cri").lowercase() },
        // ---------------------------------------------------- Système
        Epreuve("Système", "qui", 1, "ep.systeme.qui",
            "aide.systeme.qui",
            "whoami") { c -> tape(c, "^\\s*whoami\\b") },
        Epreuve("Système", "systeme", 1, "ep.systeme.systeme",
            "aide.systeme.systeme",
            "uname -a") { c -> tape(c, "^\\s*uname\\b") },
        Epreuve("Système", "alias", 2, "ep.systeme.alias",
            "aide.systeme.alias", "alias {nom_min}='echo GRRR'") { c -> tape(c, "^\\s*alias\\s+\\w+=") },
        Epreuve("Système", "variable", 3, "ep.systeme.variable",
            "aide.systeme.variable", "export BESTIOLE={nom}") { c ->
            tape(c, "^\\s*export\\s+BESTIOLE=") },
    )

    private fun parCle(k: String) = EPREUVES.first { it.cle == k }
    fun epreuve(k: String): Epreuve? = EPREUVES.firstOrNull { it.cle == k }

    /** Fin du dernier dressage, pour l'écran : le monstre joue « victoire » (capturé) ou « ko » (enfui). */
    @Volatile var finale: Pair<JSONObject, String>? = null

    // ---------------------------------------------------------------- état
    private fun etat(jeu: Jeu): JSONObject? = jeu.module("dressage").optJSONObject("en_cours")
    fun actif(jeu: Jeu) = etat(jeu) != null
    private fun repaire(nom: String) = "repaire_" + Bestiaire.espece(nom)!!.id
    fun fiche(jeu: Jeu, nom: String) = File(jeu.terrain, "monstre_${Bestiaire.espece(nom)!!.id}.txt")
    private fun ctx(jeu: Jeu, d: JSONObject): Ctx {
        val l = d.optJSONArray("lignes")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return Ctx(File(jeu.terrain, d.getString("zone") + "/" + repaire(d.getString("espece"))), d.getString("espece"),
            d.getJSONObject("x"), l, jeu.terrain)
    }

    /** Les stats du familier servent au dressage. */
    private fun bonusTemps(jeu: Jeu) = minOf(60, (jeu.stats["Agilité"] ?: 0) / 2)
    private fun bonusMefiance(jeu: Jeu) = minOf(30, (jeu.stats["Force"] ?: 0) / 2)
    private fun partExemple(jeu: Jeu) = 0.5 + minOf(0.4, (jeu.stats["Intelligence"] ?: 0) / 100.0)

    /** Le tout premier dressage : des épreuves d'une seule commande courte, dans cet ordre de préférence
     *  (pas de boucle for, pas de guillemets imbriqués, pas de tuyau |, pas de « ; »). */
    val SIMPLES = listOf("Système:qui", "Réseau:hote", "Processus:heure", "Matériel:machine", "Rétro:calendrier",
        "Système:systeme", "Mémoire:place", "Fichiers:enclos", "Nuage:nuage", "Crypto:lire", "Glitch:voir",
        "Données:debut", "Bugs:erreurs", "IA:bonjour", "Code:chant")
    /** (nombre de bestioles dressées en dessous duquel s'applique le plafond) → (épreuves de famille, niveau max) */
    val PALIERS = listOf(3 to (1 to 1), 5 to (2 to 1), 8 to (3 to 2), 12 to (4 to 3))
    /** secondes en plus tant que tu as moins de 5 bestioles */
    const val TEMPS_DEBUTANT = 60

    /** (épreuves de famille au plus, niveau au plus) selon le nombre de bestioles dressées, ou null. */
    fun plafond(nCaptures: Int?): Pair<Int, Int>? {
        if (nCaptures == null) return null
        for ((seuil, cap) in PALIERS) if (nCaptures < seuil) return cap
        return null
    }

    /**
     * G-06 : les notions qu'une épreuve demande (comme dressage.REQUIS sur PC). Une épreuve n'est tirée que si l'enfant
     * les a déjà rencontrées : chaque commande goûtée (jeu.vus), ou « opt:<clé> » = une option ou un symbole expliqué
     * après une leçon (Explique : opt:tuyau = |, opt:ecrase = >, opt:inverse = grep -v…). « a/b » : l'une ou l'autre.
     */
    val REQUIS: Map<String, List<String>> = mapOf(
        "Rencontre:examiner" to listOf("cat"), "Rencontre:repaire" to listOf("find"),
        "Fichiers:enclos" to listOf("mkdir"), "Fichiers:gamelle" to listOf("touch"), "Fichiers:doudou" to listOf("cp"),
        "Fichiers:renomme" to listOf("mv"), "Fichiers:archive" to listOf("tar"),
        "Réseau:ping" to listOf("ping"), "Réseau:hote" to listOf("hostname"), "Réseau:ip" to listOf("ip"),
        "Réseau:dns" to listOf("nslookup/dig/host"), "Réseau:page" to listOf("curl", "opt:output"),
        "Processus:ps" to listOf("ps"), "Processus:heure" to listOf("date"), "Processus:fond" to listOf("sleep", "jobs"),
        "Processus:jobs" to listOf("jobs"), "Processus:kill" to listOf("kill"),
        "Mémoire:place" to listOf("df"), "Mémoire:ram" to listOf("free"), "Mémoire:poids" to listOf("du"),
        "Mémoire:sac" to listOf("ls", "wc", "opt:tuyau"),
        "Sécurité:cage" to listOf("mkdir", "touch"), "Sécurité:cachette" to listOf("touch", "opt:all"),
        "Sécurité:prive" to listOf("chmod"), "Sécurité:empreinte" to listOf("sha256sum"),
        "Code:chant" to listOf("echo", "opt:ecrase"), "Code:script" to listOf("echo", "chmod", "opt:plusx"),
        "Code:compte" to listOf("for"),
        "Matériel:machine" to listOf("uname"), "Matériel:coeurs" to listOf("nproc"), "Matériel:disques" to listOf("lsblk/df"),
        "Bugs:erreurs" to listOf("grep"), "Bugs:combien" to listOf("grep"), "Bugs:corrige" to listOf("grep", "opt:inverse", "opt:ecrase"),
        "Nuage:nuage" to listOf("mkdir"), "Nuage:photos" to listOf("touch"), "Nuage:copie" to listOf("cp", "opt:recursif_cp"),
        "Données:debut" to listOf("head"), "Données:lignes" to listOf("wc"), "Données:trie" to listOf("sort", "opt:ecrase"),
        "Données:differentes" to listOf("sort", "uniq", "opt:tuyau"),
        "Crypto:lire" to listOf("cat"), "Crypto:decode" to listOf("base64"), "Crypto:empreinte" to listOf("sha256sum"),
        "IA:bonjour" to listOf("echo"), "IA:chat" to listOf("grep"), "IA:frequent" to listOf("sort", "uniq", "opt:tuyau"),
        "Rétro:calendrier" to listOf("cal"), "Rétro:record" to listOf("sort", "tail", "opt:tuyau"),
        "Rétro:top3" to listOf("sort", "head", "opt:tuyau", "opt:ecrase"),
        "Glitch:voir" to listOf("cat"), "Glitch:repare" to listOf("rev", "opt:ecrase"), "Glitch:chuchote" to listOf("tr"),
        "Système:qui" to listOf("whoami"), "Système:systeme" to listOf("uname"), "Système:alias" to listOf("alias"),
        "Système:variable" to listOf("export"),
    )
    /** les commandes voisines comptent pour la commande du tableau (comme dressage.SYNONYMES sur PC) */
    private val SYNONYMES = mapOf("less" to "cat", "more" to "cat", "top" to "ps", "ifconfig" to "ip", "md" to "mkdir")

    /** Les notions déjà rencontrées par l'enfant : commandes goûtées (+ leurs voisines) et options expliquées. */
    fun rencontrees(jeu: Jeu): Set<String> {
        val vues = jeu.vus.toMutableSet()
        vues += jeu.vus.mapNotNull { SYNONYMES[it] }
        jeu.module("explique").optJSONArray("vues")?.let { a -> for (i in 0 until a.length()) vues += "opt:" + a.getString(i) }
        return vues
    }

    /** L'épreuve ne demande que des notions déjà rencontrées (notions null : pas de filtre). */
    fun connue(cle: String, notions: Set<String>?): Boolean =
        notions == null || (REQUIS[cle] ?: emptyList()).all { tok -> tok.split("/").any { it in notions } }

    /** Les épreuves d'un dressage. nCaptures = bestioles déjà dressées (null : pas de plafond).
     *  notions = rencontrees(jeu) : seules les épreuves dont les notions sont connues (G-06 ; null : toutes). */
    fun choisirEpreuves(e: Bestiaire.Espece, premiere: Boolean, rarete: String, nCaptures: Int? = null,
                        notions: Set<String>? = null): List<Epreuve> {
        val rencontre = EPREUVES.filter { it.fam == "Rencontre" }
        if (nCaptures == 0) return listOf(rencontre[0]) + premiereEpreuve(e, notions)   // lire sa fiche + 1 épreuve simple
        val rc = rencontre.filterIndexed { i, x -> i == 0 || connue(x.cle, notions) }
        return rc + epreuvesFamille(e, premiere, rarete, plafond(nCaptures), notions).ifEmpty { premiereEpreuve(e, notions) }
    }

    private fun premiereEpreuve(e: Bestiaire.Espece, notions: Set<String>? = null): List<Epreuve> {
        val fams = e.epreuves.ifEmpty { listOf(e.famille) }
        val pool = fams.flatMap { f -> EPREUVES.filter { it.fam == f } }.associateBy { it.cle }
        for (k in SIMPLES) pool[k]?.let { if (connue(k, notions)) return listOf(it) }
        if (connue("Rencontre:repaire", notions)) return listOf(EPREUVES.filter { it.fam == "Rencontre" }[1])
        for (k in SIMPLES) if (connue(k, notions)) epreuve(k)?.let { return listOf(it) }   // une épreuve simple d'ailleurs
        return emptyList()
    }

    /** Les épreuves de la famille (e.epreuves : les commandes que cette famille aime), selon la rareté de l'individu. */
    private fun epreuvesFamille(e: Bestiaire.Espece, premiere: Boolean, rarete: String, cap: Pair<Int, Int>?,
                                notions: Set<String>? = null): List<Epreuve> {
        val fams = e.epreuves.ifEmpty { listOf(e.famille) }
        val pool = fams.flatMap { f -> EPREUVES.filter { it.fam == f && connue(it.cle, notions) } }
        var n = NB[rarete] ?: 2
        var nmax = NIV[rarete] ?: 1
        if (cap != null) { n = minOf(n, cap.first); nmax = minOf(nmax, cap.second) }   // débutant : moins d'épreuves, plus faciles
        val choix = if (rarete in ULTIMES && cap == null) {        // l'épreuve ultime : sa famille + des épreuves d'ailleurs
            val autres = EPREUVES.filter { it.fam !in fams && it.fam != "Rencontre" && it.niveau >= 2 && connue(it.cle, notions) }.shuffled()
            pool.sortedBy { it.niveau }.takeLast(3) + autres.take(3)
        } else {
            val ok = pool.filter { it.niveau <= nmax }.sortedBy { it.niveau }
            if (premiere) ok.take(n) else ok.shuffled().take(minOf(n, ok.size)).sortedBy { it.niveau }
        }
        return choix.distinctBy { it.id }    // pas deux fois la même épreuve
    }

    /** Un monstre vient d'apparaître : le dressage commence tout de suite. Renvoie false s'il t'ignore. */
    fun commencer(jeu: Jeu, e: Bestiaire.Espece, individu: JSONObject? = null): Boolean {
        val ind = individu ?: Bestiaire.individu(e, false, e.zone).put("stade", "bebe")
        val rar = Bestiaire.rareteDe(ind)
        val shiny = ind.optBoolean("shiny")
        val m = jeu.module("dressage")
        val jour = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
        val essais = m.optJSONObject("essais") ?: JSONObject().also { m.put("essais", it) }
        if (rar in ULTIMES && essais.optString(e.nom) == jour) {
            jeu.dire(t("dress.un_essai",
                "nom" to e.nom), 12)
            return false
        }
        val faites = m.optJSONArray("familles") ?: JSONArray().also { m.put("familles", it) }
        val premiere = (0 until faites.length()).none { faites.getString(it) == e.famille }
        val nCaps = Explo.captures(jeu).length()
        val taches = choisirEpreuves(e, premiere, rar, nCaps, rencontrees(jeu))
        val debutant = if (nCaps < 5) TEMPS_DEBUTANT else 0
        val zone = ind.optString("zone").ifEmpty { e.zone }
        val d = JSONObject().put("espece", e.nom).put("shiny", shiny).put("zone", zone)
            .put("taches", JSONArray(taches.map { it.cle })).put("faites", JSONArray()).put("lignes", JSONArray())
            .put("debut", System.currentTimeMillis()).put("x", JSONObject())
            .put("duree", if (premiere) 0 else (DUREE[rar] ?: 90) + bonusTemps(jeu) + debutant)
            .put("mefiance", 100 - bonusMefiance(jeu)).put("seconde", (jeu.stats["Endurance"] ?: 0) >= 20)
            .put("ind", ind).put("rarete", rar).put("variante", ind.optString("variante", "classique")).put("examine", false)
            .put("exemple_tout_de_suite", nCaps < 5)    // I10 : un débutant voit l'exemple tout de suite (pas d'attente)
        if (rar in ULTIMES) essais.put(e.nom, jour)
        m.put("en_cours", d)
        val c = ctx(jeu, d)
        c.d.mkdirs()
        for (t in taches) t.prep?.invoke(c)
        ecrireFiche(jeu, e, ind)
        val eclat = if (shiny) " ✨" else ""
        jeu.dire(if (premiere) t("dress.premiere", "nom" to e.nom, "eclat" to eclat, "famille" to e.famille)
            else t("dress.debut",
                "nom" to e.nom, "eclat" to eclat), 12)
        jeu.log(t("dress.commence.log", "nom" to e.nom, "n" to taches.size))
        Combat.preparer(jeu)                        // ta troupe affronte d'abord le monstre (si tu en as une)
        return true
    }

    /** La fiche du monstre, posée dans le terrain de jeu (cat pour la lire). */
    private fun ecrireFiche(jeu: Jeu, e: Bestiaire.Espece, ind: JSONObject) {
        val p = Mots.palier(jeu)
        val st = ind.optJSONObject("stats")?.let { o -> LinkedHashMap(o.keys().asSequence().associateWith { o.optInt(it) }) } ?: e.stats
        // les étiquettes sont alignées en colonnes d'écran (un caractère chinois ou japonais en prend 2)
        val etiquettes = listOf(t("dress.fiche.nom"), t("dress.fiche.numero"), t("dress.fiche.rarete"),
            t("dress.fiche.variante"), t("dress.fiche.age"), t("dress.fiche.famille"),
            Mots.terme("stats", p, true), t("dress.fiche.taille"))
        val n = etiquettes.maxOf { Langue.largeur(it) }
        fun ligne(i: Int, v: String) = "  " + Langue.ajuster(etiquettes[i], n) + " : " + v + "\n"
        fiche(jeu, e.nom).writeText(
            "══════════ " + t("dress.fiche.titre") + " ══════════\n" +
                ligne(0, e.nom + if (ind.optBoolean("shiny")) " ✨ " + t("dress.fiche.shiny") else "") +
                ligne(1, "#%03d".format(e.numero)) +
                ligne(2, t("dress.fiche.rarete.val", "rarete" to Bestiaire.nomRarete(Bestiaire.rareteDe(ind)),
                    "note" to (ind.opt("note") ?: "?"))) +
                ligne(3, ind.optString("variante", "classique")) +
                ligne(4, Equipe.nomStade(Equipe.stade(ind))) +
                ligne(5, e.famille) +
                ligne(6, Mots.texteStats(st, p)) +
                ligne(7, t("dress.fiche.taille.val", "cm" to e.tailleCm, "ko" to e.poidsKo)) + "\n" +
                "  « ${e.description} »\n  ${e.comportement}\n\n  " +
                t("dress.fiche.repaire",
                    "repaire" to repaire(e.nom), "terrain" to Mots.terme("terrain", p)) + "\n")
    }

    fun reste(jeu: Jeu): Int? {
        val d = etat(jeu) ?: return null
        val duree = d.optInt("duree")
        if (duree == 0) return null
        return maxOf(0, duree - ((System.currentTimeMillis() - d.optLong("debut")) / 1000).toInt())
    }

    private fun courante(d: JSONObject): Epreuve? {
        val faites = d.getJSONArray("faites").let { a -> (0 until a.length()).map { a.getString(it) }.toSet() }
        val t = d.getJSONArray("taches")
        return (0 until t.length()).map { t.getString(it) }.firstOrNull { it !in faites }?.let { parCle(it) }
    }

    /** Après chaque commande (ou périodiquement si ligne == null). Renvoie un message à afficher, ou null. */
    /** code : le code de sortie de la commande (null = inconnu) : une commande ratée ne compte pas (G-34). */
    fun verifier(jeu: Jeu, ligne: String?, colle: Boolean, code: Int? = null): String? {
        val d = etat(jeu) ?: return null
        if (Combat.enCours(jeu)) {                  // le combat d'abord : chaque commande tapée est un coup
            if (ligne != null && !colle && !Regles.estColle(ligne)) Combat.coup(jeu, ligne)
            return null
        }
        if (ligne != null && !colle && (code == null || code == 0)) {
            val l = d.getJSONArray("lignes")
            l.put(ligne)
            while (l.length() > 200) l.remove(0)
        }
        val c = ctx(jeu, d)
        var progres = false
        while (true) {
            val e = courante(d) ?: break
            val ok = try { e.ok(c) } catch (x: Exception) { false }
            if (!ok) break
            d.getJSONArray("faites").put(e.cle)
            if (e.cle == "Rencontre:examiner") d.put("examine", true)
            progres = true
        }
        if (courante(d) == null) return reussir(jeu, d)
        val r = reste(jeu)
        if (r != null && r <= 0) {
            if (d.optBoolean("seconde")) {
                d.put("seconde", false).put("duree", d.optInt("duree") + 60)
                jeu.dire(t("dress.seconde_chance",
                    "nom" to d.getString("espece")), 10)
            } else return echouer(jeu, d)
        }
        if (progres) {
            d.remove("indice")
            jeu.dire(Langue.auHasard("dress.progres", "nom" to d.getString("espece"),
                "n" to d.getJSONArray("faites").length(), "total" to d.getJSONArray("taches").length()), 6)
        } else if (ligne != null && !colle && !Regles.estColle(ligne)) {
            val conseil = indice(jeu, d, c, listOf(ligne))
            if (conseil != null && conseil != d.optString("indice")) {
                d.put("indice", conseil)
                jeu.dire("💡 $conseil", 12)
                jeu.animer("parle")
            }
        }
        return null
    }

    private fun reussir(jeu: Jeu, d: JSONObject): String {
        jeu.module("dressage").remove("en_cours")
        val e = Bestiaire.espece(d.getString("espece"))!!
        fiche(jeu, e.nom).delete()
        val shiny = d.optBoolean("shiny")
        val ind = d.optJSONObject("ind") ?: Bestiaire.individu(e, shiny, d.getString("zone"))
        val ecoule = (System.currentTimeMillis() - d.optLong("debut")) / 1000
        ind.put("dresse", ecoule)
        if (!ind.has("stade")) ind.put("stade", "bebe")
        ind.put("xp", 0)                                    // il grandira en gardant son nom
        if (shiny && !ind.has("teinte")) ind.put("teinte", Bestiaire.arrondi(Random.nextDouble(0.15, 0.85), 3))
        val rar = Bestiaire.rareteDe(ind)
        if (!ind.has("rarete")) ind.put("rarete", rar)
        Explo.captures(jeu).put(ind)
        Explo.collection(jeu).let { it.put(e.nom, it.optInt(e.nom) + 1) }
        jeu.module("equipe").put("active", ind.getString("id"))
        val fams = jeu.module("dressage").optJSONArray("familles") ?: JSONArray().also { jeu.module("dressage").put("familles", it) }
        if ((0 until fams.length()).none { fams.getString(it) == e.famille }) fams.put(e.famille)
        val titre = e.nom + if (shiny) " ✨ SHINY" else ""
        jeu.log(t("dress.reussi.log", "titre" to titre, "s" to ecoule, "rarete" to Bestiaire.nomRarete(rar)))
        jeu.dire(t("dressa.reussi.dit",
            "nom" to e.nom, "eclat" to (if (shiny) " ✨" else ""), "marque" to ind.optString("marque")), 14)
        jeu.animer("victoire")
        finale = ind to "victoire"
        val st = if (e.stat in jeu.stats) e.stat else Regles.STATS.random()
        jeu.stats[st] = (jeu.stats[st] ?: 0) + 2 + d.getJSONArray("taches").length()
        val duree = d.optInt("duree")
        val bonus = if (duree > 0 && duree - ecoule > duree / 2.0) 2 else 1
        jeu.ajouterXp((Bestiaire.XP[rar] ?: 15) * (if (shiny) 3 else 1) * bonus)
        Envies.plaisir(jeu, "jeu", "dressage")
        return "🎓 ${Explo.carte(ind)}\n" + t("dressa.rejoint", "nom" to e.nom)
    }

    private fun echouer(jeu: Jeu, d: JSONObject): String {
        jeu.module("dressage").remove("en_cours")
        fiche(jeu, d.getString("espece")).delete()
        jeu.log(t("dress.echec.log", "nom" to d.getString("espece")))
        jeu.animer("ko")
        d.optJSONObject("ind")?.let { finale = JSONObject(it.toString()).put("espece", d.getString("espece")).put("shiny", d.optBoolean("shiny")) to "ko" }
        return "💨 " + t("dress.echec.dit",
            "nom" to d.getString("espece"))
    }

    fun abandonner(jeu: Jeu): String {
        val d = etat(jeu) ?: return t("dressa.aucun")
        jeu.module("dressage").remove("en_cours")
        fiche(jeu, d.getString("espece")).delete()
        return t("dress.abandon.log", "nom" to d.getString("espece")) + "."
    }

    // ---------------------------------------------------------------- « presque ! » : des indices clairs
    // Quand l'épreuve en cours n'est pas réussie après une commande, on cherche si elle l'est PRESQUE :
    // un indice propre à l'épreuve, un fichier créé au mauvais endroit, ou une faute de frappe par rapport
    // à l'exemple (comme dressage.indice sur PC ; textes : clés « dress.indice.* »).
    private fun aTape(l: List<String>, motif: String) = Regex(motif, RegexOption.IGNORE_CASE).let { r -> l.any { r.containsMatchIn(it) } }

    private fun iScript(c: Ctx, l: List<String>): String? {
        val f = File(c.d, "tour.sh")
        val texte = lire(f) ?: return null
        if ("echo" !in texte.lowercase()) return t("dress.indice.script_echo", "fichier" to f.name)
        if (!f.canExecute()) return t("dress.indice.script_chmod", "fichier" to f.name)
        return null
    }

    private fun iCompte(c: Ctx, l: List<String>): String? {
        for (x in l) {
            val m = x.trim()
            if (Regex("^for\\s").containsMatchIn(m) && (";" !in m || !Regex("\\bdo\\b").containsMatchIn(m) || !Regex("\\bdone\\b").containsMatchIn(m)))
                return t("dress.indice.for")
        }
        return if (lignesDe(File(c.d, "compte.txt")) != null) t("dress.indice.compte") else null
    }

    private fun iChant(c: Ctx, l: List<String>) =
        if (lire(File(c.d, "chant.txt")) != null) t("dress.indice.chant", "nom" to c.nom) else null

    private fun iGamelle(c: Ctx, l: List<String>): String? {
        if (File(c.d, "gamelle").exists()) return t("dress.indice.dans_enclos", "fichier" to "gamelle")
        if (!File(c.d, "enclos").isDirectory && aTape(l, "enclos[/\\\\]gamelle")) return t("dress.indice.enclos_dabord")
        return null
    }

    private fun iDoudou(c: Ctx, l: List<String>): String? {
        if (File(c.d, "enclos/doudou.txt").exists() && !File(c.d, "doudou.txt").exists()) return t("dress.indice.cp_pas_mv")
        if (!File(c.d, "enclos").isDirectory && aTape(l, "^\\s*(cp|copy)\\b")) return t("dress.indice.enclos_dabord")
        return null
    }

    private fun iRenomme(c: Ctx, l: List<String>): String? {
        val nomMin = Bestiaire.espece(c.nom)?.id ?: Bestiaire.simple(c.nom)
        if (!File(c.d, "vieux_nom.txt").exists() && !File(c.d, "$nomMin.txt").exists() && !File(c.d, Bestiaire.simple(c.nom) + ".txt").exists())
            return t("dress.indice.nom_min", "nom_min" to nomMin)
        return null
    }

    private fun iDansEnclos(nom: String): (Ctx, List<String>) -> String? = { c, l ->
        if (File(c.d, nom).exists() && !File(c.d, "enclos/$nom").exists()) t("dress.indice.dans_enclos", "fichier" to nom)
        else if (!File(c.d, "enclos").isDirectory && aTape(l, "enclos[/\\\\]")) t("dress.indice.enclos_dabord")
        else null
    }

    private fun iCachette(c: Ctx, l: List<String>): String? {
        val enclos = File(c.d, "enclos")
        if (!enclos.isDirectory) return if (aTape(l, "enclos[/\\\\]")) t("dress.indice.enclos_dabord") else null
        if (enclos.listFiles()?.any { it.isFile && !it.name.startsWith(".") } == true && aTape(l, "^\\s*(touch|new-item)\\b"))
            return t("dress.indice.point")
        return null
    }

    private fun iPrive(c: Ctx, l: List<String>) = if (File(c.d, "enclos/cage").exists()) t("dress.indice.prive") else null

    private fun iNombre(c: Ctx, l: List<String>) =
        if (l.any { Regex("^\\s*(echo|write-output)\\s+[\"']?\\d+[\"']?\\s*$", RegexOption.IGNORE_CASE).matches(it) }) t("dress.indice.nombre") else null

    private fun iReponse(c: Ctx, l: List<String>) =
        if (l.any { Regex("^\\s*(echo|write-output)\\s+\\S", RegexOption.IGNORE_CASE).containsMatchIn(it) }) t("dress.indice.reponse") else null

    private fun iContenu(nom: String): (Ctx, List<String>) -> String? = { c, _ ->
        if (File(c.d, nom).exists()) t("dress.indice.fichier", "fichier" to nom) else null
    }

    private fun iPhotos(c: Ctx, l: List<String>): String? {
        val n = File(c.d, "nuage").listFiles()?.count { it.name.startsWith("photo") } ?: return null
        return if (n in 1..2) t("dress.indice.photos", "n" to n) else null
    }

    private val INDICES: Map<String, (Ctx, List<String>) -> String?> = mapOf(
        "Code:script" to ::iScript, "Code:compte" to ::iCompte, "Code:chant" to ::iChant,
        "Fichiers:gamelle" to ::iGamelle, "Fichiers:doudou" to ::iDoudou, "Fichiers:renomme" to ::iRenomme,
        "Sécurité:cage" to iDansEnclos("cage"), "Sécurité:cachette" to ::iCachette, "Sécurité:prive" to ::iPrive,
        "Mémoire:sac" to ::iNombre, "Matériel:coeurs" to ::iNombre, "Bugs:combien" to ::iNombre, "Données:lignes" to ::iNombre,
        "Données:differentes" to ::iNombre, "IA:chat" to ::iNombre, "Rétro:record" to ::iNombre,
        "Crypto:decode" to ::iReponse, "Sécurité:empreinte" to ::iReponse, "IA:frequent" to ::iReponse,
        "Données:trie" to iContenu("trie.txt"), "Rétro:top3" to iContenu("top3.txt"), "Bugs:corrige" to iContenu("corrige.log"),
        "Glitch:repare" to iContenu("repare.txt"), "Glitch:chuchote" to iContenu("chuchote.txt"),
        "Nuage:photos" to ::iPhotos,
    )

    /** ce que l'épreuve doit créer dans le repaire (pour repérer un fichier créé ailleurs) */
    private val ATTENDUS = mapOf("Fichiers:enclos" to "enclos", "Code:chant" to "chant.txt", "Code:script" to "tour.sh",
        "Code:compte" to "compte.txt", "Nuage:nuage" to "nuage", "Données:trie" to "trie.txt", "Rétro:top3" to "top3.txt",
        "Glitch:repare" to "repare.txt", "Glitch:chuchote" to "chuchote.txt", "Bugs:corrige" to "corrige.log",
        "Fichiers:archive" to "enclos.tar.gz", "Sécurité:cage" to "enclos")

    /** Le fichier attendu, trouvé hors du repaire (dans la maison ou le terrain), ou null. */
    private fun ailleurs(jeu: Jeu, c: Ctx, nom: String): File? {
        val ici = File(c.d, nom)
        if (ici.exists()) return null
        for (base in listOf(jeu.home, c.terrain, c.d.parentFile)) {
            val f = File(base, nom)
            if (f.exists()) return f
        }
        if (c.terrain.isDirectory) {
            val dernier = nom.split("/").last()
            val dans = c.d.absolutePath + File.separator
            return c.terrain.walkTopDown().firstOrNull { it.name == dernier && it != ici && !it.absolutePath.startsWith(dans) }
        }
        return null
    }

    /** L'exemple de l'épreuve, rempli (nom du monstre, vocabulaire du palier). */
    fun exemple(jeu: Jeu, ep: Epreuve, nom: String): String {
        val e = Bestiaire.espece(nom)
        return Mots.remplir(ep.exemple, Mots.termes(Mots.palier(jeu)) + mapOf("nom_min" to (e?.id ?: nom.lowercase()), "nom" to nom))
    }

    /** L'indice pour l'épreuve en cours quand elle est presque réussie, ou null. */
    private fun indice(jeu: Jeu, d: JSONObject, c: Ctx, lignes: List<String>): String? {
        val ep = courante(d) ?: return null
        try {
            INDICES[ep.cle]?.invoke(c, lignes)?.let { return it }
            val nom = ATTENDUS[ep.cle]
            if (nom != null && ailleurs(jeu, c, nom) != null)
                return t("dress.indice.mauvais_endroit", "fichier" to nom,
                    "cmd" to "cd ~/${jeu.terrain.name}/${d.getString("zone")}/${repaire(d.getString("espece"))}")
        } catch (x: Exception) {
            // fichier illisible : pas d'indice de ce côté
        }
        val ff = Indices.fauteDeFrappe(lignes, exemple(jeu, ep, d.getString("espece"))) ?: return null
        return t("dress.indice.faute", "tape" to ff.first, "attendu" to ff.second)
    }

    // ---------------------------------------------------------------- l'écran
    private val COUL_STAT = mapOf("PV" to 0xFFFF5F5F.toInt(), "ATK" to 0xFFFF8700.toInt(), "DEF" to 0xFF5FAFFF.toInt(),
        "VIT" to 0xFF87FF87.toInt(), "INT" to 0xFFAF87FF.toInt())

    private fun SpannableStringBuilder.texte(t: String, couleur: Int, gras: Boolean = false, taille: Float = 1f): SpannableStringBuilder {
        val a = length
        val (txt, cmds) = Vert.passages(t)                // `commande` : en vert par-dessus la couleur du texte
        append(txt)
        setSpan(ForegroundColorSpan(couleur), a, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        for ((x, y) in cmds) setSpan(ForegroundColorSpan(Vert.COULEUR), a + x, a + y, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        if (gras) setSpan(StyleSpan(Typeface.BOLD), a, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        if (taille != 1f) setSpan(RelativeSizeSpan(taille), a, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        return this
    }

    private fun couleurJauge(bien: Double) = when {
        bien > 0.66 -> 0xFF87FF87.toInt(); bien > 0.4 -> 0xFFFFFF5F.toInt(); bien > 0.2 -> 0xFFFF8700.toInt(); else -> 0xFFFF3030.toInt()
    }

    private fun SpannableStringBuilder.jauge(valeur: Double, inverse: Boolean): SpannableStringBuilder {
        val f = valeur.coerceIn(0.0, 1.0)
        val n = Math.round(f * 14).toInt()
        texte("█".repeat(n), couleurJauge(if (inverse) 1 - f else f))
        return texte("░".repeat(14 - n), 0xFF44445A.toInt())
    }

    private fun SpannableStringBuilder.coeurs(a: org.json.JSONArray): SpannableStringBuilder {
        val n = a.optInt(0); val maxi = a.optInt(1)
        texte("❤".repeat(maxOf(0, n)), 0xFFFF3030.toInt())
        return texte("♡".repeat(maxOf(0, maxi - n)), 0xFF585858.toInt())
    }

    /**
     * Le panneau affiché pendant un dressage : la carte du monstre, puis une seule étape.
     * Pendant le mini-combat : la bestiole de ta troupe à gauche (gauche = l'image en cours de son animation,
     * sinon son dessin), les cœurs des deux côtés, puis le tour, ce qui vient de se passer et les trois coups.
     */
    fun panneau(jeu: Jeu, res: Resources, gauche: android.graphics.Bitmap? = null): CharSequence? {
        val d = etat(jeu) ?: return null
        val e = Bestiaire.espece(d.getString("espece")) ?: return null
        val p = Mots.palier(jeu)
        val cb = if (Combat.enCours(jeu)) d.optJSONObject("combat") else null
        val bete = if (cb != null) Combat.ind(jeu) else null
        val eb = bete?.let { Bestiaire.espece(it.optString("espece")) }
        val sb = SpannableStringBuilder()
        sb.texte("⚔ " + t("dress.titre") + "\n", 0xFFFF5050.toInt(), true, 1.1f)
        // face-à-face : ton familier (ou la bestiole de ta troupe qui combat) à gauche, le monstre à droite
        val px = (72 * res.displayMetrics.density).toInt()
        fun image(b: android.graphics.Bitmap) {
            val a = sb.length
            sb.append("\uFFFC")
            val img = BitmapDrawable(res, b)
            img.setBounds(0, 0, px, px)
            sb.setSpan(ImageSpan(img, DynamicDrawableSpan.ALIGN_BOTTOM), a, a + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        if (bete != null && eb != null) {
            val sB = Equipe.stade(bete)
            image(gauche ?: (if (Animations.dispo(eb.id)) Animations.pixels(eb.id, sB, "statique", 3)?.firstOrNull() else null)
                ?: Bestiaire.bitmap(eb, bete.optBoolean("shiny"), 3, sB, bete.optString("variante", "classique"), bete.optDouble("teinte", 0.5)))
        } else image(gauche ?: Sprites.bitmap(jeu, 6, false))
        sb.texte("   VS   ", 0xFFFF5050.toInt(), true, 1.3f)
        val ind = d.optJSONObject("ind")
        val stadeM = ind?.let { Equipe.stade(it) } ?: "adulte"
        val shinyM = d.optBoolean("shiny")
        image((if (Animations.dispo(e.id)) Animations.pixels(e.id, stadeM, "statique", 3)?.firstOrNull() else null)
            ?: Bestiaire.bitmap(e, shinyM, 3, stadeM, d.optString("variante", "classique"), ind?.optDouble("teinte", 0.5) ?: 0.5))
        sb.append("\n")
        val COUL_FAM = mapOf("Intelligence" to 0xFF00AFFF.toInt(), "Agilité" to 0xFF5FD787.toInt(),
            "Force" to 0xFFFF5F5F.toInt(), "Endurance" to 0xFFFFD75F.toInt())
        val pc = if (p < 2) 0 else 2               // les cœurs : l'image seule, ou le vrai mot court
        if (bete != null && eb != null && cb != null) {
            val r = Bestiaire.rareteDe(bete)
            sb.texte("◀ " + Bestiaire.nomAffiche(eb, bete.optBoolean("shiny"), r) + " · " + Equipe.nomStade(Equipe.stade(bete)) + "  ", 0xFFFFFFFF.toInt(), true)
            val st = bete.optJSONObject("stats")?.let { o -> o.keys().asSequence().associateWith { o.optInt(it) } } ?: eb.stats
            for (k in listOf("ATK", "DEF", "VIT")) st[k]?.let { v -> sb.texte(Mots.nomStat(k, pc), COUL_STAT[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
            sb.texte(Mots.terme("pv", pc, true) + " ", 0xFFBCBCBC.toInt()).coeurs(cb.getJSONArray("moi")).append("\n")
        } else {
            sb.texte("◀ ${jeu.nom}  ", 0xFFFFFFFF.toInt(), true)
            for ((k, v) in jeu.stats) { sb.texte(Regles.court(k), COUL_FAM[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
            sb.append("\n")
        }
        val rar = d.optString("rarete").ifEmpty { "commune" }
        val examine = d.optBoolean("examine")
        sb.texte("▶ ${e.nom}${if (shinyM) " ✨" else ""}", if (examine) Bestiaire.COULEUR_RARETE[rar] ?: -1 else 0xFFFFFFFF.toInt(), true)
        sb.texte("  #%03d ".format(e.numero) + (if (examine) Bestiaire.nomRarete(rar) else t("dress.rarete_cachee")) + " · ${Equipe.nomStade(stadeM)}  ", 0xFF9090A8.toInt())
        val statsM = ind?.optJSONObject("stats")?.let { o -> LinkedHashMap(o.keys().asSequence().associateWith { o.optInt(it) }) } ?: e.stats
        if (examine || cb?.optBoolean("vu") == true) {
            for ((k, v) in statsM) { sb.texte(Mots.nomStat(k, p), COUL_STAT[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
            sb.append("\n")
        } else sb.texte(t("dress.stats_cachees", "stats" to Mots.terme("stats", p)) + "\n", 0xFF808098.toInt())
        val nTot = d.getJSONArray("taches").length()
        val nFait = d.getJSONArray("faites").length()
        val mef = d.optInt("mefiance", 100) * (1 - nFait.toDouble() / nTot)
        sb.texte(Mots.terme("mefiance", p) + " ", 0xFFFF87FF.toInt()).jauge(mef / 100, true).texte(" %.0f %%\n".format(mef), 0xFFE0E0F0.toInt())
        if (cb != null) {
            sb.texte(Mots.terme("pv", pc, true) + " ", 0xFFBCBCBC.toInt()).coeurs(cb.getJSONArray("lui")).append("\n")
            return combat(sb, cb)
        }
        // les étiquettes (Temps, Mission, Comment, Tape, Où) alignées en colonnes d'écran, quelle que soit la langue
        val et = listOf(t("dress.temps"), t("dress.col.mission"), t("dress.col.comment"),
            t("dress.col.tape"), t("dress.col.ou"), "💡 " + t("dress.col.indice"))
        val n = et.dropLast(1).maxOf { Langue.largeur(it) } + 2     // (l'étiquette de l'indice, rare, peut dépasser)
        fun col(i: Int) = Langue.ajuster(et[i], n)
        val r = reste(jeu)
        if (r == null) sb.texte(col(0) + t("dress.pas_de_chrono") + "\n", 0xFFAFAFFF.toInt())
        else sb.texte(col(0), 0xFFAFD7FF.toInt()).jauge(r.toDouble() / d.optInt("duree"), false).texte(" $r s\n", 0xFFE0E0F0.toInt())
        sb.texte(t("dress.etape", "n" to minOf(nFait + 1, nTot), "total" to nTot) + "  ", 0xFF9090A8.toInt())
        val cour = courante(d)
        val t = d.getJSONArray("taches")
        for (i in 0 until nTot) {
            val k = t.getString(i)
            if (i < nFait) sb.texte("● ", 0xFF87FF87.toInt()) else if (cour?.cle == k) sb.texte("◉ ", 0xFFFFFF5F.toInt()) else sb.texte("○ ", 0xFF555570.toInt())
        }
        sb.append("\n")
        val ep = cour ?: return sb
        val nom = e.nom
        val valeurs = Mots.termes(p) + mapOf("nom_min" to e.id, "nom" to nom)
        fun f(s: String) = Langue.remplir(s, valeurs)
        sb.texte("\n" + col(1), 0xFFFFFF5F.toInt(), true).texte(f(ep.but) + "\n", 0xFFFFFFFF.toInt(), true)
        sb.texte(col(2), 0xFF87D7FF.toInt(), true).texte(f(ep.explication) + "\n", 0xFFD0D0E0.toInt())
        val duree = d.optInt("duree")
        val montre = r == null || ep.fam == "Rencontre" || d.optBoolean("exemple_tout_de_suite") || r <= duree * (1 - partExemple(jeu))
        // P2-2 : le lieu et la commande sur la MÊME ligne (« cd ~/…/repaire_x puis mkdir enclos »)
        val dansRepaire = Maison.dans(jeu, Maison.ici(jeu), "${d.getString("zone")}/${repaire(nom)}")
        val montree = Regles.piege(Mots.remplir(ep.exemple, valeurs)).let { x ->
            if (ep.fam == "Rencontre" || dansRepaire) "`$x`"
            else t("comp.lecon.puis", "cd" to Regles.piege("cd ~/terrain_terminagotchi/${d.getString("zone")}/${repaire(nom)}"), "cmd" to x)
        }
        if (montre) sb.texte(col(3), 0xFF87FF87.toInt(), true).texte(montree + "\n", 0xFF87FF87.toInt())
        else sb.texte(col(3), 0xFF87FF87.toInt(), true)
            .texte(t("dressa.exemple_dans", "s" to r!! - (duree * (1 - partExemple(jeu))).toInt()) + "\n", 0xFF808098.toInt())
        d.optString("indice").ifEmpty { null }?.let { sb.texte(col(5).let { c -> if (c.endsWith(" ")) c else "$c " }, 0xFFFFAF00.toInt(), true).texte(it + "\n", 0xFFFFAF00.toInt()) }
        val ou = when (ep.cle) {
            "Rencontre:examiner" -> "~/terrain_terminagotchi"
            "Rencontre:repaire" -> t("dress.nimporte_ou")
            else -> "~/terrain_terminagotchi/${d.getString("zone")}/${repaire(nom)}"
        }
        sb.texte(col(4), 0xFFA0A0B8.toInt(), true).texte(ou, 0xFFA0A0B8.toInt())
        return sb
    }

    /** Le panneau du mini-combat : le tour, ce qui vient de se passer, les trois coups possibles. */
    private fun combat(sb: SpannableStringBuilder, cb: JSONObject): SpannableStringBuilder {
        sb.texte("\n⚔ " + t("dress.combat.titre", "n" to minOf(cb.optInt("tour") + 1, Combat.TOURS_MAX), "total" to Combat.TOURS_MAX) + "\n",
            0xFFFF5050.toInt(), true)
        val j = cb.optJSONArray("journal") ?: org.json.JSONArray()
        for (i in maxOf(0, j.length() - 3) until j.length()) sb.texte("» ", 0xFF808098.toInt()).texte(j.getString(i) + "\n", 0xFFE0E0F0.toInt())
        sb.texte("\n" + t("dress.combat.coups") + "\n", 0xFFFFFFFF.toInt())
        val special = cb.optString("special")
        val coups = mutableListOf<Triple<String, String, Int>>()
        if (special.isNotEmpty() && special !in Combat.OBSERVER) coups.add(Triple(special, t("dress.combat.special.aide"), 0xFFFF87FF.toInt()))
        coups.add(Triple("ls", t("dress.combat.observer.aide") + (if (special in Combat.OBSERVER) " · " + t("dress.combat.special.aide") else ""), 0xFF87D7FF.toInt()))
        coups.add(Triple(t("dress.combat.autre"), t("dress.combat.attaque.aide"), 0xFFBCBCBC.toInt()))
        val n = coups.maxOf { Langue.largeur(it.first) } + 2
        for ((k, coup) in coups.withIndex()) {
            val (c, expl, coul) = coup
            val mot = Langue.ajuster(c, n)
            sb.texte("  " + (if (k < coups.size - 1) "`" + Regles.piege(mot) + "`" else mot), coul, true).texte("→ $expl\n", 0xFFD0D0E0.toInt())
        }
        sb.texte(t("dress.combat.ensuite"), 0xFF808098.toInt())
        return sb
    }
}
