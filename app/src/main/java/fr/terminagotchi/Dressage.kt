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
    private val DUREE = mapOf("commune" to 90, "peu commune" to 120, "rare" to 180, "légendaire" to 240)
    private val NB = mapOf("commune" to 2, "peu commune" to 3, "rare" to 4, "légendaire" to 6)
    private val NIV = mapOf("commune" to 1, "peu commune" to 2, "rare" to 3, "légendaire" to 3)
    private val MOTS = listOf("octet", "pixel", "bug", "shell", "noyau", "cache", "paquet", "script", "fichier", "chat",
        "nuage", "clef", "boucle", "signal", "tuyau", "racine")

    /** Contexte d'une épreuve : dossier du repaire, nom du monstre, données tirées au hasard. */
    class Ctx(val d: File, val nom: String, val x: JSONObject, val lignes: List<String>, val terrain: File)

    class Epreuve(
        val fam: String, val id: String, val niveau: Int, val but: String, val explication: String,
        val exemple: String, val prep: ((Ctx) -> Unit)? = null, val ok: (Ctx) -> Boolean,
    ) { val cle get() = "$fam:$id" }

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
        File(c.d, "croquettes.txt").writeText(l.joinToString("\n") + "\n")
        c.x.put("croquettes", JSONArray(l))
    }
    private fun prepBug(c: Ctx) {
        if (c.x.has("bug")) return
        val n = Random.nextInt(2, 6)
        val l = (List(6) { "INFO tout va bien $it" } + List(n) { "ERROR la bestiole a mordu le câble $it" }).shuffled()
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
    private fun scores(c: Ctx) = c.x.optJSONArray("scores")!!.let { a -> (0 until a.length()).map { a.getInt(it) } }

    private val CAT = "^\\s*(cat|less|more|head)\\b"

    val EPREUVES: List<Epreuve> = listOf(
        // ---------------------------------------------------- rencontre (toujours en premier)
        Epreuve("Rencontre", "examiner", 1, "Examine-le : lis sa fiche pour voir ses stats.",
            "cat affiche le contenu d'un fichier. La fiche du monstre est dans ton terrain de jeu.",
            "cat ~/terrain_terminagotchi/monstre_{nom_min}.txt") { c -> tape(c, "$CAT.*monstre_" + Regex.escape(c.nom.lowercase())) },
        Epreuve("Rencontre", "repaire", 1, "D'où vient-il ? Trouve son repaire dans le terrain de jeu.",
            "find cherche un fichier ou un dossier par son nom, dans tous les sous-dossiers. Il affiche le chemin complet : c'est là que vit le monstre.",
            "find ~/terrain_terminagotchi -name repaire_{nom_min}") { c -> tape(c, "^\\s*(find|ls)\\b.*repaire") },
        // ---------------------------------------------------- Fichiers
        Epreuve("Fichiers", "enclos", 1, "Construis-moi un enclos : un dossier « enclos ».", "mkdir crée un dossier (« make directory »).",
            "mkdir enclos") { c -> File(c.d, "enclos").isDirectory },
        Epreuve("Fichiers", "gamelle", 1, "Pose une gamelle (un fichier « gamelle ») dans mon enclos.",
            "touch crée un fichier vide. Le / sépare le dossier du fichier.", "touch enclos/gamelle") { c -> File(c.d, "enclos/gamelle").exists() },
        Epreuve("Fichiers", "doudou", 2, "Copie mon doudou.txt dans l'enclos.", "cp copie un fichier : d'abord ce qu'on copie, puis où on le met.",
            "mkdir -p enclos ; cp doudou.txt enclos/", { c -> File(c.d, "doudou.txt").writeText("Le doudou de ${c.nom}.\n") }) { c ->
            File(c.d, "doudou.txt").exists() && File(c.d, "enclos/doudou.txt").exists() },
        Epreuve("Fichiers", "renomme", 2, "Renomme vieux_nom.txt avec mon nom en minuscules.",
            "mv déplace un fichier ; dans le même dossier, ça le renomme.", "mv vieux_nom.txt {nom_min}.txt",
            { c -> File(c.d, "vieux_nom.txt").writeText("Renomme-moi !\n") }) { c ->
            !File(c.d, "vieux_nom.txt").exists() && File(c.d, c.nom.lowercase() + ".txt").exists() },
        Epreuve("Fichiers", "archive", 3, "Range tout mon enclos dans une archive « enclos.tar.gz ».",
            "tar range un dossier entier dans un seul fichier compressé : c = créer, z = compresser, f = nom du fichier.",
            "tar -czf enclos.tar.gz enclos") { c -> listOf("enclos.tar.gz", "enclos.tgz", "enclos.tar").any { File(c.d, it).exists() } },
        // ---------------------------------------------------- Réseau
        Epreuve("Réseau", "ping", 1, "Envoie-moi un signal sur ta propre machine.",
            "ping envoie de petits messages et mesure s'ils reviennent. localhost = ta propre machine, -c 3 = 3 envois.",
            "ping -c 3 localhost") { c -> tape(c, "^\\s*ping\\b.*(localhost|127\\.0\\.0\\.1)") },
        Epreuve("Réseau", "hote", 1, "Dis-moi comment s'appelle ta machine.", "hostname affiche le nom de l'appareil sur le réseau.",
            "hostname") { c -> tape(c, "^\\s*hostname\\b") },
        Epreuve("Réseau", "ip", 2, "Montre-moi ton adresse IP.", "Chaque machine connectée a une adresse IP, comme une adresse postale.",
            "ip a") { c -> tape(c, "^\\s*(ip\\s+(a|addr)|ifconfig)\\b") },
        // ---------------------------------------------------- Processus
        Epreuve("Processus", "ps", 1, "Montre-moi les programmes qui tournent.", "Un processus = un programme qui tourne. ps les liste.",
            "ps -A") { c -> tape(c, "^\\s*(ps|top)\\b") },
        Epreuve("Processus", "heure", 1, "Quelle heure est-il ? Demande à la machine.", "date affiche la date et l'heure.",
            "date") { c -> tape(c, "^\\s*date\\b") },
        // ---------------------------------------------------- Mémoire
        Epreuve("Mémoire", "place", 1, "Combien de place reste-t-il ?", "df montre l'espace libre ; -h écrit les tailles lisiblement.",
            "df -h") { c -> tape(c, "^\\s*df\\b") },
        Epreuve("Mémoire", "ram", 1, "Et la mémoire vive, il en reste ?", "free montre la mémoire vive (RAM) utilisée et libre.",
            "free -h") { c -> tape(c, "^\\s*free\\b") },
        Epreuve("Mémoire", "sac", 3, "J'ai caché des objets dans mon sac/. Combien ? Réponds avec echo.",
            "ls sac liste le sac. Le | envoie le résultat à wc -l, qui compte les lignes. Puis réponds avec echo et le nombre.",
            "ls sac | wc -l    puis    echo 7", { c ->
                val n = Random.nextInt(4, 10); File(c.d, "sac").mkdirs()
                for (i in 1..n) File(c.d, "sac/objet_$i").writeText("…"); c.x.put("sac", n) }) { c -> repond(c, c.x.optInt("sac")) },
        // ---------------------------------------------------- Sécurité
        Epreuve("Sécurité", "cage", 1, "Fabrique-moi une cage : un fichier « cage » dans l'enclos.", "touch crée un fichier vide (mkdir -p crée l'enclos s'il manque).",
            "mkdir -p enclos ; touch enclos/cage") { c -> File(c.d, "enclos/cage").exists() },
        Epreuve("Sécurité", "cachette", 1, "Cache un fichier secret dans l'enclos (un nom qui commence par un point).",
            "Un fichier dont le nom commence par un point est caché : ls ne le montre pas, ls -a si.", "touch enclos/.secret") { c ->
            File(c.d, "enclos").listFiles()?.any { it.name.startsWith(".") && it.isFile } == true },
        Epreuve("Sécurité", "empreinte", 3, "Donne-moi l'empreinte de collier.txt (8 premiers caractères, avec echo).",
            "sha256sum calcule l'empreinte unique d'un fichier. Recopie les 8 premiers caractères avec echo.",
            "sha256sum collier.txt    puis    echo 1a2b3c4d", ::prepCollier) { c ->
            val r = Regex("^\\s*echo\\s+[\"']?([0-9a-f]{8,64})[\"']?\\s*$", RegexOption.IGNORE_CASE)
            c.lignes.any { l -> r.matchEntire(l)?.groupValues?.get(1)?.lowercase()?.startsWith(c.x.optString("empreinte")) == true } },
        // ---------------------------------------------------- Code
        Epreuve("Code", "chant", 1, "Écris mon nom dans un fichier « chant.txt ».", "echo affiche un texte ; le > l'envoie dans un fichier.",
            "echo {nom} > chant.txt") { c -> lire(File(c.d, "chant.txt"))?.lowercase()?.contains(c.nom.lowercase()) == true },
        Epreuve("Code", "compte", 3, "Écris les nombres de 1 à 5, un par ligne, dans compte.txt (avec une boucle !).",
            "Une boucle for répète une commande pour chaque valeur ; tout ce qui s'affiche va dans le fichier grâce au >.",
            "for i in 1 2 3 4 5; do echo \$i; done > compte.txt") { c -> lignesDe(File(c.d, "compte.txt"))?.map { it.trim() } == listOf("1", "2", "3", "4", "5") },
        // ---------------------------------------------------- Matériel
        Epreuve("Matériel", "machine", 1, "C'est quoi, comme machine ?", "uname -m donne le type de processeur (arm64, x86_64…).",
            "uname -m") { c -> tape(c, "^\\s*uname\\b") },
        Epreuve("Matériel", "coeurs", 2, "Combien de cœurs a ton processeur ? Réponds avec echo.",
            "nproc donne le nombre de cœurs du processeur. Réponds ensuite avec echo.", "nproc    puis    echo 8") { c ->
            repond(c, Runtime.getRuntime().availableProcessors()) },
        // ---------------------------------------------------- Bugs
        Epreuve("Bugs", "erreurs", 1, "Trouve les lignes ERROR dans bug.log.", "grep cherche un mot dans un fichier et affiche les lignes qui le contiennent.",
            "grep ERROR bug.log", ::prepBug) { c -> tape(c, "grep.*error") },
        Epreuve("Bugs", "combien", 2, "Combien d'erreurs dans bug.log ? Réponds avec echo.", "grep -c compte les lignes qui contiennent le mot.",
            "grep -c ERROR bug.log    puis    echo 3", ::prepBug) { c -> repond(c, c.x.optInt("bug")) },
        Epreuve("Bugs", "corrige", 3, "Fais-moi un corrige.log sans les lignes d'erreur.",
            "grep -v garde les lignes qui NE contiennent PAS le mot ; > les écrit dans un fichier.", "grep -v ERROR bug.log > corrige.log", ::prepBug) { c ->
            lignesDe(File(c.d, "corrige.log"))?.let { it.isNotEmpty() && it.none { l -> "ERROR" in l } } == true },
        // ---------------------------------------------------- Nuage
        Epreuve("Nuage", "nuage", 1, "Fais-moi un nuage : un dossier « nuage ».", "mkdir crée un dossier.", "mkdir nuage") { c -> File(c.d, "nuage").isDirectory },
        Epreuve("Nuage", "photos", 2, "Mets trois photos dedans (photo1.jpg, photo2.jpg, photo3.jpg).",
            "touch peut créer plusieurs fichiers d'un coup, écrits à la suite.", "touch nuage/photo1.jpg nuage/photo2.jpg nuage/photo3.jpg") { c ->
            (File(c.d, "nuage").listFiles()?.count { it.name.startsWith("photo") } ?: 0) >= 3 },
        Epreuve("Nuage", "copie", 3, "Sauvegarde tout le nuage dans « nuage_copie ».", "cp -r copie un dossier entier (r = récursif).",
            "cp -r nuage nuage_copie") { c -> (File(c.d, "nuage_copie").listFiles()?.count { it.name.startsWith("photo") } ?: 0) >= 3 },
        // ---------------------------------------------------- Données
        Epreuve("Données", "debut", 1, "Montre-moi le début de croquettes.txt.", "head affiche seulement les premières lignes d'un fichier.",
            "head croquettes.txt", ::prepLignes) { c -> tape(c, "^\\s*head\\b.*croquettes") },
        Epreuve("Données", "lignes", 2, "Combien de lignes dans croquettes.txt ? Réponds avec echo.", "wc -l compte les lignes d'un fichier.",
            "wc -l croquettes.txt    puis    echo 12", ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").size) },
        Epreuve("Données", "trie", 2, "Trie croquettes.txt dans trie.txt.", "sort trie les lignes ; > écrit le résultat dans un fichier.",
            "sort croquettes.txt > trie.txt", ::prepLignes) { c -> lignesDe(File(c.d, "trie.txt")) == liste(c.x, "croquettes").sorted() },
        Epreuve("Données", "differentes", 3, "Combien de sortes de croquettes différentes ? Réponds avec echo.",
            "sort trie, uniq enlève les doublons, wc -l compte ; les | enchaînent les trois.", "sort croquettes.txt | uniq | wc -l    puis    echo 5",
            ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").toSet().size) },
        // ---------------------------------------------------- Crypto
        Epreuve("Crypto", "lire", 1, "Lis mon message codé, message.b64.", "cat affiche le contenu d'un fichier.", "cat message.b64", { c ->
            val mot = MOTS.random(); c.x.put("secret", mot)
            File(c.d, "message.b64").writeText(android.util.Base64.encodeToString(mot.toByteArray(), android.util.Base64.NO_WRAP) + "\n") }) { c ->
            tape(c, "$CAT.*message") },
        Epreuve("Crypto", "decode", 2, "Décode message.b64 et dis-moi le mot secret avec echo.",
            "Le base64 transforme un texte en lettres codées ; base64 -d le décode.", "base64 -d message.b64    puis    echo motsecret", { c ->
            if (!c.x.has("secret")) { val mot = MOTS.random(); c.x.put("secret", mot)
                File(c.d, "message.b64").writeText(android.util.Base64.encodeToString(mot.toByteArray(), android.util.Base64.NO_WRAP) + "\n") } }) { c ->
            repond(c, c.x.optString("secret")) },
        // ---------------------------------------------------- IA
        Epreuve("IA", "bonjour", 1, "Dis-moi bonjour avec mon nom (avec echo).", "echo affiche le texte qu'on lui donne.", "echo bonjour {nom}") { c ->
            tape(c, "^\\s*echo\\b.*" + Regex.escape(c.nom)) },
        Epreuve("IA", "chat", 2, "Combien de lignes contiennent « chat » dans croquettes.txt ? (echo)", "grep -c compte les lignes qui contiennent un mot.",
            "grep -c chat croquettes.txt    puis    echo 2", ::prepLignes) { c -> repond(c, liste(c.x, "croquettes").count { "chat" in it }) },
        // ---------------------------------------------------- Rétro
        Epreuve("Rétro", "calendrier", 1, "Montre-moi le calendrier du mois.", "cal affiche le calendrier.", "cal") { c -> tape(c, "^\\s*cal\\b") },
        Epreuve("Rétro", "record", 2, "Quel est le meilleur score de scores.txt ? (echo)",
            "sort -n trie des nombres du plus petit au plus grand ; tail -1 garde le dernier.", "sort -n scores.txt | tail -1    puis    echo 9876",
            ::prepScores) { c -> repond(c, scores(c).max()) },
        Epreuve("Rétro", "top3", 3, "Écris les 3 meilleurs scores, du plus grand au plus petit, dans top3.txt.",
            "sort -nr trie du plus grand au plus petit ; head -3 garde les 3 premiers ; > écrit le fichier.", "sort -nr scores.txt | head -3 > top3.txt",
            ::prepScores) { c -> lignesDe(File(c.d, "top3.txt"))?.map { it.trim() } == scores(c).sortedDescending().take(3).map { it.toString() } },
        // ---------------------------------------------------- Glitch
        Epreuve("Glitch", "voir", 1, "Regarde corrompu.txt… mes mots sont à l'envers !", "cat affiche le contenu d'un fichier.", "cat corrompu.txt", { c ->
            if (!c.x.has("phrase")) { val p = listOf("je suis ton ami", "merci pour la gamelle", "on part en exploration").random()
                c.x.put("phrase", p); File(c.d, "corrompu.txt").writeText(p.reversed() + "\n") } }) { c -> tape(c, "$CAT.*corrompu") },
        Epreuve("Glitch", "repare", 2, "Remets corrompu.txt à l'endroit dans repare.txt.", "rev retourne chaque ligne ; > écrit le résultat.",
            "rev corrompu.txt > repare.txt", { c ->
            if (!c.x.has("phrase")) { val p = listOf("je suis ton ami", "merci pour la gamelle", "on part en exploration").random()
                c.x.put("phrase", p); File(c.d, "corrompu.txt").writeText(p.reversed() + "\n") } }) { c ->
            lire(File(c.d, "repare.txt"))?.trim() == c.x.optString("phrase") },
        // ---------------------------------------------------- Système
        Epreuve("Système", "qui", 1, "Qui es-tu ? Demande ton nom d'utilisateur.", "whoami (« qui suis-je ») affiche ton nom d'utilisateur.",
            "whoami") { c -> tape(c, "^\\s*whoami\\b") },
        Epreuve("Système", "systeme", 1, "Sur quel système vivons-nous ?", "uname -a affiche tout sur le système : nom, version, type de machine.",
            "uname -a") { c -> tape(c, "^\\s*uname\\b") },
        Epreuve("Système", "alias", 2, "Crée-moi une commande à mon nom avec alias.",
            "Un alias est un surnom : un mot court qui lance une commande plus longue.", "alias {nom_min}='echo GRRR'") { c -> tape(c, "^\\s*alias\\s+\\w+=") },
        Epreuve("Système", "variable", 3, "Crée une variable d'environnement BESTIOLE qui contient mon nom.",
            "Une variable d'environnement est une petite mémoire du terminal : un nom qui contient une valeur.", "export BESTIOLE={nom}") { c ->
            tape(c, "^\\s*export\\s+BESTIOLE=") },
    )

    private fun parCle(k: String) = EPREUVES.first { it.cle == k }

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

    fun commencer(jeu: Jeu, e: Bestiaire.Espece, shiny: Boolean) {
        val m = jeu.module("dressage")
        val faites = m.optJSONArray("familles") ?: JSONArray().also { m.put("familles", it) }
        val premiere = (0 until faites.length()).none { faites.getString(it) == e.famille }
        val pool = EPREUVES.filter { it.fam == e.famille && it.niveau <= (NIV[e.rarete] ?: 1) }.sortedBy { it.niveau }
        val n = NB[e.rarete] ?: 2
        val choix = if (e.rarete == "légendaire") {
            EPREUVES.filter { it.fam == e.famille }.sortedBy { it.niveau }.takeLast(3) +
                EPREUVES.filter { it.fam != e.famille && it.fam != "Rencontre" && it.niveau >= 2 }.shuffled().take(3)
        } else if (premiere) pool.take(n) else pool.shuffled().take(n).sortedBy { it.niveau }
        val taches = EPREUVES.filter { it.fam == "Rencontre" } + choix.distinctBy { it.cle }
        val d = JSONObject().put("espece", e.nom).put("shiny", shiny).put("zone", e.zone)
            .put("taches", JSONArray(taches.map { it.cle })).put("faites", JSONArray()).put("lignes", JSONArray())
            .put("debut", System.currentTimeMillis()).put("x", JSONObject())
            .put("duree", if (premiere) 0 else (DUREE[e.rarete] ?: 90) + bonusTemps(jeu))
            .put("mefiance", 100 - bonusMefiance(jeu)).put("seconde", (jeu.stats["Endurance"] ?: 0) >= 20)
        m.put("en_cours", d)
        val c = ctx(jeu, d)
        c.d.mkdirs()
        for (t in taches) t.prep?.invoke(c)
        fiche(jeu, e.nom).writeText(
            "══════════ FICHE DE MONSTRE ══════════\n  Nom     : ${e.nom}${if (shiny) " ✨ (shiny !)" else ""}\n" +
                "  Numéro  : #%03d\n".format(e.numero) + "  Rareté  : ${e.rarete}\n  Famille : ${e.famille}\n" +
                "  Stats   : " + e.stats.entries.joinToString("  ") { "${it.key} ${it.value}" } + "\n\n" +
                "  « ${e.description} »\n  ${e.comportement}\n\n" +
                "  Il vient d'un endroit appelé « ${repaire(e.nom)} »… quelque part dans le terrain de jeu.\n")
        jeu.log("⚔ Un ${e.nom} sauvage apparaît !")
        jeu.dire(if (premiere) "Un ${e.nom} sauvage ! Première rencontre avec la famille ${e.famille} : pas de chrono, je t'explique tout."
            else "Un ${e.nom} sauvage apparaît ! Gagne sa confiance avant la fin du temps.", 12)
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
                jeu.dire("Ton familier retient ${d.getString("espece")} ! Endurance : +60 s, vite !", 10)
            } else return echouer(jeu, d)
        }
        if (progres) {
            jeu.dire(listOf("Il remue la queue !", "Il s'approche un peu…", "Il a l'air impressionné !", "Il ronronne en binaire.").random() +
                " (${d.getJSONArray("faites").length()}/${d.getJSONArray("taches").length()})", 6)
        }
        return null
    }

    private fun reussir(jeu: Jeu, d: JSONObject): String {
        jeu.module("dressage").remove("en_cours")
        val e = Bestiaire.espece(d.getString("espece"))!!
        fiche(jeu, e.nom).delete()
        val shiny = d.optBoolean("shiny")
        val ind = Bestiaire.individu(e, shiny, d.getString("zone"))
            .put("dresse", (System.currentTimeMillis() - d.optLong("debut")) / 1000).put("stade", "enfant").put("xp", 0)
        if (shiny) ind.put("teinte", Math.round(Random.nextDouble(0.15, 0.85) * 1000) / 1000.0)
        Explo.captures(jeu).put(ind)
        Explo.collection(jeu).let { it.put(e.nom, it.optInt(e.nom) + 1) }
        jeu.module("equipe").put("active", ind.getString("id"))
        val fams = jeu.module("dressage").optJSONArray("familles") ?: JSONArray().also { jeu.module("dressage").put("familles", it) }
        if ((0 until fams.length()).none { fams.getString(it) == e.famille }) fams.put(e.famille)
        val st = if (e.stat in jeu.stats) e.stat else Regles.STATS.random()
        jeu.stats[st] = (jeu.stats[st] ?: 0) + 2 + d.getJSONArray("taches").length()
        jeu.ajouterXp((Bestiaire.XP[e.rarete] ?: 15) * if (shiny) 3 else 1)
        val titre = e.nom + if (shiny) " ✨ SHINY" else ""
        jeu.log("🎓 $titre dressé ! (${e.rarete})")
        jeu.dire("${e.nom} te fait confiance et rejoint ton équipe ! Signe particulier : ${ind.getString("marque")}.", 14)
        return "🎓 ${Explo.carte(ind)}\nIl rejoint ton équipe (tape « equipe »)."
    }

    private fun echouer(jeu: Jeu, d: JSONObject): String {
        jeu.module("dressage").remove("en_cours")
        fiche(jeu, d.getString("espece")).delete()
        jeu.log("💨 ${d.getString("espece")} s'est enfui…")
        return "💨 Trop tard ! ${d.getString("espece")} s'est enfui. Continue de jouer : il reviendra peut-être."
    }

    fun abandonner(jeu: Jeu): String {
        val d = etat(jeu) ?: return "Pas de dressage en cours."
        jeu.module("dressage").remove("en_cours")
        fiche(jeu, d.getString("espece")).delete()
        return "🏳 Dressage de ${d.getString("espece")} abandonné."
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
        val sb = SpannableStringBuilder()
        sb.texte("⚔ UN MONSTRE SAUVAGE !\n", 0xFFFF5050.toInt(), true, 1.1f)
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
        image(Bestiaire.bitmap(e, d.optBoolean("shiny"), 5))
        sb.append("\n")
        val COUL_FAM = mapOf("Intelligence" to 0xFF00AFFF.toInt(), "Agilité" to 0xFF5FD787.toInt(),
            "Force" to 0xFFFF5F5F.toInt(), "Endurance" to 0xFFFFD75F.toInt())
        sb.texte("◀ ${jeu.nom}  ", 0xFFFFFFFF.toInt(), true)
        for ((k, v) in jeu.stats) { sb.texte(k.take(3).uppercase(), COUL_FAM[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
        sb.append("\n")
        sb.texte("▶ ${e.nom}", Bestiaire.COULEUR_RARETE[e.rarete] ?: -1, true)
        sb.texte("  #%03d ${e.rarete}  ".format(e.numero), 0xFF9090A8.toInt())
        if (d.optBoolean("examine")) {
            for ((k, v) in e.stats) { sb.texte(k, COUL_STAT[k] ?: -1, true); sb.texte(" $v  ", 0xFFE0E0F0.toInt()) }
            sb.append("\n")
        } else sb.texte("stats ??? (examine-le)\n", 0xFF808098.toInt())
        val nTot = d.getJSONArray("taches").length()
        val nFait = d.getJSONArray("faites").length()
        val mef = d.optInt("mefiance", 100) * (1 - nFait.toDouble() / nTot)
        sb.texte("Méfiance ", 0xFFFF87FF.toInt()).jauge(mef / 100, true).texte(" %.0f %%\n".format(mef), 0xFFE0E0F0.toInt())
        val r = reste(jeu)
        if (r == null) sb.texte("Temps    pas de chrono : c'est une leçon\n", 0xFFAFAFFF.toInt())
        else sb.texte("Temps    ", 0xFFAFD7FF.toInt()).jauge(r.toDouble() / d.optInt("duree"), false).texte(" $r s\n", 0xFFE0E0F0.toInt())
        sb.texte("Étape ${minOf(nFait + 1, nTot)}/$nTot  ", 0xFF9090A8.toInt())
        val cour = courante(d)
        val t = d.getJSONArray("taches")
        for (i in 0 until nTot) {
            val k = t.getString(i)
            if (i < nFait) sb.texte("● ", 0xFF87FF87.toInt()) else if (cour?.cle == k) sb.texte("◉ ", 0xFFFFFF5F.toInt()) else sb.texte("○ ", 0xFF555570.toInt())
        }
        sb.append("\n")
        val ep = cour ?: return sb
        val nom = e.nom
        fun f(s: String) = s.replace("{nom_min}", e.id).replace("{nom}", nom)
        sb.texte("\nIl veut  ", 0xFFFFFF5F.toInt(), true).texte(f(ep.but) + "\n", 0xFFFFFFFF.toInt(), true)
        sb.texte("Comment  ", 0xFF87D7FF.toInt(), true).texte(ep.explication + "\n", 0xFFD0D0E0.toInt())
        val duree = d.optInt("duree")
        val montre = r == null || ep.fam == "Rencontre" || r <= duree * (1 - partExemple(jeu))
        if (montre) sb.texte("Tape     ", 0xFF87FF87.toInt(), true).texte(Regles.piege(f(ep.exemple)) + "\n", 0xFF87FF87.toInt())
        else sb.texte("Tape     ", 0xFF87FF87.toInt(), true)
            .texte("l'exemple s'affiche dans ${r!! - (duree * (1 - partExemple(jeu))).toInt()} s (cherche d'abord dans le Lexique)\n", 0xFF808098.toInt())
        val ou = when (ep.cle) {
            "Rencontre:examiner" -> "~/terrain_terminagotchi"
            "Rencontre:repaire" -> "n'importe où"
            else -> "~/terrain_terminagotchi/${d.getString("zone")}/${repaire(nom)}"
        }
        sb.texte("Où       ", 0xFFA0A0B8.toInt(), true).texte(ou, 0xFFA0A0B8.toInt())
        return sb
    }
}
