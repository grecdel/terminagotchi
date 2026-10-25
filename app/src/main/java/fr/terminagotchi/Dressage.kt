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
        val p = Regles.auHasard("dress.fichier.corrompu")
        c.x.put("phrase", p)
        File(c.d, "corrompu.txt").writeText(p.reversed() + "\n")
    }
    private fun prepCri(c: Ctx) {
        if (c.x.has("cri")) return
        // en MAJUSCULES ASCII : la commande « tr A-Z a-z » doit pouvoir les chuchoter
        val p = Regles.auHasard("dress.fichier.cri")
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

    /** Les épreuves de la famille (e.epreuves : les commandes que cette famille aime), selon la rareté de l'individu. */
    fun choisirEpreuves(e: Bestiaire.Espece, premiere: Boolean, rarete: String): List<Epreuve> {
        val fams = e.epreuves.ifEmpty { listOf(e.famille) }
        val pool = fams.flatMap { f -> EPREUVES.filter { it.fam == f } }
        val n = NB[rarete] ?: 2
        val choix = if (rarete in ULTIMES) {        // l'épreuve ultime : sa famille + des épreuves d'ailleurs
            val autres = EPREUVES.filter { it.fam !in fams && it.fam != "Rencontre" && it.niveau >= 2 }.shuffled()
            pool.sortedBy { it.niveau }.takeLast(3) + autres.take(3)
        } else {
            val ok = pool.filter { it.niveau <= (NIV[rarete] ?: 1) }.sortedBy { it.niveau }
            if (premiere) ok.take(n) else ok.shuffled().take(minOf(n, ok.size)).sortedBy { it.niveau }
        }
        return EPREUVES.filter { it.fam == "Rencontre" } + choix.distinctBy { it.id }    // pas deux fois la même épreuve
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
        val taches = choisirEpreuves(e, premiere, rar)
        val zone = ind.optString("zone").ifEmpty { e.zone }
        val d = JSONObject().put("espece", e.nom).put("shiny", shiny).put("zone", zone)
            .put("taches", JSONArray(taches.map { it.cle })).put("faites", JSONArray()).put("lignes", JSONArray())
            .put("debut", System.currentTimeMillis()).put("x", JSONObject())
            .put("duree", if (premiere) 0 else (DUREE[rar] ?: 90) + bonusTemps(jeu))
            .put("mefiance", 100 - bonusMefiance(jeu)).put("seconde", (jeu.stats["Endurance"] ?: 0) >= 20)
            .put("ind", ind).put("rarete", rar).put("variante", ind.optString("variante", "classique")).put("examine", false)
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
    fun verifier(jeu: Jeu, ligne: String?, colle: Boolean): String? {
        val d = etat(jeu) ?: return null
        if (ligne != null && !colle) {
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
            jeu.dire(Langue.auHasard("dress.progres", "nom" to d.getString("espece"),
                "n" to d.getJSONArray("faites").length(), "total" to d.getJSONArray("taches").length()), 6)
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

    // ---------------------------------------------------------------- l'écran
    private val COUL_STAT = mapOf("PV" to 0xFFFF5F5F.toInt(), "ATK" to 0xFFFF8700.toInt(), "DEF" to 0xFF5FAFFF.toInt(),
        "VIT" to 0xFF87FF87.toInt(), "INT" to 0xFFAF87FF.toInt())

    private fun SpannableStringBuilder.texte(t: String, couleur: Int, gras: Boolean = false, taille: Float = 1f): SpannableStringBuilder {
        val a = length
        append(t)
        setSpan(ForegroundColorSpan(couleur), a, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
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

    /** Le panneau affiché pendant un dressage : la carte du monstre, puis une seule étape. */
    fun panneau(jeu: Jeu, res: Resources): CharSequence? {
        val d = etat(jeu) ?: return null
        val e = Bestiaire.espece(d.getString("espece")) ?: return null
        val p = Mots.palier(jeu)
        val sb = SpannableStringBuilder()
        sb.texte("⚔ " + t("dress.titre") + "\n", 0xFFFF5050.toInt(), true, 1.1f)
        // face-à-face : ton familier à gauche, le monstre à droite
        val px = (72 * res.displayMetrics.density).toInt()
        fun image(b: android.graphics.Bitmap) {
            val a = sb.length
            sb.append("\uFFFC")
            val img = BitmapDrawable(res, b)
            img.setBounds(0, 0, px, px)
            sb.setSpan(ImageSpan(img, DynamicDrawableSpan.ALIGN_BOTTOM), a, a + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        image(Sprites.bitmap(jeu, 6, false))
        sb.texte("   VS   ", 0xFFFF5050.toInt(), true, 1.3f)
        val ind = d.optJSONObject("ind")
        val stadeM = ind?.let { Equipe.stade(it) } ?: "adulte"
        val shinyM = d.optBoolean("shiny")
        image((if (Animations.dispo(e.id)) Animations.pixels(e.id, stadeM, "statique", 3)?.firstOrNull() else null)
            ?: Bestiaire.bitmap(e, shinyM, 3, stadeM, d.optString("variante", "classique"), ind?.optDouble("teinte", 0.5) ?: 0.5))
        sb.append("\n")
        val COUL_FAM = mapOf("Intelligence" to 0xFF00AFFF.toInt(), "Agilité" to 0xFF5FD787.toInt(),
            "Force" to 0xFFFF5F5F.toInt(), "Endurance" to 0xFFFFD75F.toInt())
        sb.texte("◀ ${jeu.nom}  ", 0xFFFFFFFF.toInt(), true)
        for ((k, v) in jeu.stats) { sb.texte(Regles.court(k), COUL_FAM[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
        sb.append("\n")
        val rar = d.optString("rarete").ifEmpty { "commune" }
        val examine = d.optBoolean("examine")
        sb.texte("▶ ${e.nom}${if (shinyM) " ✨" else ""}", if (examine) Bestiaire.COULEUR_RARETE[rar] ?: -1 else 0xFFFFFFFF.toInt(), true)
        sb.texte("  #%03d ".format(e.numero) + (if (examine) Bestiaire.nomRarete(rar) else t("dress.rarete_cachee")) + " · ${Equipe.nomStade(stadeM)}  ", 0xFF9090A8.toInt())
        val statsM = ind?.optJSONObject("stats")?.let { o -> LinkedHashMap(o.keys().asSequence().associateWith { o.optInt(it) }) } ?: e.stats
        if (examine) {
            for ((k, v) in statsM) { sb.texte(Mots.nomStat(k, p), COUL_STAT[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
            sb.append("\n")
        } else sb.texte(t("dress.stats_cachees", "stats" to Mots.terme("stats", p)) + "\n", 0xFF808098.toInt())
        val nTot = d.getJSONArray("taches").length()
        val nFait = d.getJSONArray("faites").length()
        val mef = d.optInt("mefiance", 100) * (1 - nFait.toDouble() / nTot)
        sb.texte(Mots.terme("mefiance", p) + " ", 0xFFFF87FF.toInt()).jauge(mef / 100, true).texte(" %.0f %%\n".format(mef), 0xFFE0E0F0.toInt())
        // les étiquettes (Temps, Mission, Comment, Tape, Où) alignées en colonnes d'écran, quelle que soit la langue
        val et = listOf(t("dress.temps"), t("dress.col.mission"), t("dress.col.comment"),
            t("dress.col.tape"), t("dress.col.ou"))
        val n = et.maxOf { Langue.largeur(it) } + 2
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
        val montre = r == null || ep.fam == "Rencontre" || r <= duree * (1 - partExemple(jeu))
        if (montre) sb.texte(col(3), 0xFF87FF87.toInt(), true).texte(Regles.piege(Mots.remplir(ep.exemple, valeurs)) + "\n", 0xFF87FF87.toInt())
        else sb.texte(col(3), 0xFF87FF87.toInt(), true)
            .texte(t("dressa.exemple_dans", "s" to r!! - (duree * (1 - partExemple(jeu))).toInt()) + "\n", 0xFF808098.toInt())
        val ou = when (ep.cle) {
            "Rencontre:examiner" -> "~/terrain_terminagotchi"
            "Rencontre:repaire" -> t("dress.nimporte_ou")
            else -> "~/terrain_terminagotchi/${d.getString("zone")}/${repaire(nom)}"
        }
        sb.texte(col(4), 0xFFA0A0B8.toInt(), true).texte(ou, 0xFFA0A0B8.toInt())
        return sb
    }
}
