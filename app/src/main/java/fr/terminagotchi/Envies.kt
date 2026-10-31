package fr.terminagotchi

import org.json.JSONObject
import java.io.File
import java.util.Calendar
import kotlin.random.Random

/**
 * Les 6 envies de la créature (portage de pc/tg/envies.py : mêmes règles, mêmes seuils, mêmes textes).
 *
 *  🍎 faim       n'importe quelle commande la nourrit (Jeu.manger) ; elle descend 2 fois moins vite qu'avant
 *  🎮 jeu        defi, donjon, ctf (chasse au trésor), joue / devine, un combat, un dressage réussi
 *  📚 curiosité  une étape de leçon, une quête finie, une commande jamais goûtée, explique, cherche, --help
 *  🧭 explorer   entrer dans une pièce jamais visitée, une pièce secrète (quête « cachette »), ls -a ou find
 *                dans la maison du jeu
 *  😴 sommeil    elle fatigue en jouant (plus vite le soir) ; « sleep 10 » = une vraie sieste (le vrai shell, via
 *                Shell.kt ; animation « dort » ; au plus SIESTE_MAX_TEL secondes ici) ; elle se repose toute seule
 *                quand on ne joue pas. Le jeu ne propose JAMAIS de mettre le téléphone en veille.
 *  🧹 propreté   de la « poussière » (poussiere_1.tmp…) tombe avec le temps dans un placard caché du terrain de la
 *                partie active (terrain_terminagotchi/.cache/, voir Parties.kt : un terrain par partie) ; la jauge
 *                se calcule d'après les VRAIS fichiers .tmp. rm des .tmp du placard (ou rm -r .cache : le placard est
 *                recréé vide). Rien n'est jamais créé ni supprimé hors du terrain, ni avant que le terrain existe.
 *
 * Pas de mort ni de punition : une envie à zéro rend la créature triste (une) ou grognon (plusieurs).
 * Seuils : voir les constantes (les mêmes que sur PC, documentées dans envies.py) ; testés par tests/jvm/Envies.kt.
 * Sauvegarde : jeu.module("envies") (local, jamais envoyé au serveur).
 */
object Envies {
    val ENVIES = listOf("faim", "jeu", "curiosite", "explorer", "sommeil", "proprete")
    val ICONES = mapOf("faim" to "🍎", "jeu" to "🎮", "curiosite" to "📚", "explorer" to "🧭", "sommeil" to "😴", "proprete" to "🧹")
    val DEPART = mapOf("jeu" to 70.0, "curiosite" to 70.0, "explorer" to 70.0, "sommeil" to 90.0)
    const val MIGRATION = 60.0
    val PAR_COMMANDE = mapOf("jeu" to 0.7, "curiosite" to 0.6, "explorer" to 0.6, "sommeil" to 0.4)
    const val SOMMEIL_SOIR = 1.2
    val PAR_HEURE = mapOf("jeu" to 2.0, "curiosite" to 1.5, "explorer" to 1.5)
    const val PLANCHER_TEMPS = 25.0
    const val PAUSE = 600_000L
    const val REPOS_HEURE = 25.0
    const val SIESTE_PAR_SECONDE = 5.0
    const val SIESTE_MAX = 50.0
    const val SIESTE_CONSEIL = 10
    /** le shell du téléphone coupe une commande au bout de 20 s (Shell.kt) : une sieste plus longue est refusée */
    const val SIESTE_MAX_TEL = 15
    const val SOIR = 20
    const val MATIN = 7
    const val POUSSIERE_INTERVALLE = 45 * 60_000L
    const val POUSSIERE_MAX = 8
    const val SEUIL = 40.0
    /** = « affamée » (Satiete.FORME) */
    const val FAIM_URGENTE = 40.0
    const val SATISFAITE = 60.0
    /** un plaisir d'au moins 15 points sur l'envie du moment : merci (elle repart) */
    const val MERCI = 15.0
    const val PROCHES = 10.0
    const val MOMENT_DUREE = 15 * 60_000L
    const val RAPPEL_COMMANDES = 12
    const val RAPPEL_MINUTES = 5
    const val SOIR_MINUTES = 40
    const val XP_BAS = 2
    const val XP_MOMENT = 3
    const val XP_DELAI = 120_000L
    val GAINS = mapOf("nouvelle" to 10.0, "explique" to 20.0, "lecon" to 15.0, "quete" to 25.0, "lieu" to 15.0,
        "secret" to 40.0, "regarde" to 8.0, "defi" to 35.0, "combat" to 30.0, "dressage" to 40.0,
        "mini" to 15.0, "donjon" to 30.0, "ctf" to 40.0)
    const val CACHE = ".cache"

    private val SLEEP = Regex("^\\s*sleep\\s+(\\d+(?:\\.\\d+)?)s?\\s*$", RegexOption.IGNORE_CASE)
    private val CURIEUX = Regex("^\\s*(explique|man|help|cherche)\\b|\\s--help\\b", RegexOption.IGNORE_CASE)
    private val REGARDE = Regex("^\\s*(ls\\s+-\\w*a|find\\b|tree\\b)", RegexOption.IGNORE_CASE)

    /** l'heure (remplaçable par un test) */
    var heure: () -> Int = { Calendar.getInstance().get(Calendar.HOUR_OF_DAY) }
    /** l'horloge en ms (remplaçable par un test) */
    var maintenant: () -> Long = { System.currentTimeMillis() }

    fun soir(): Boolean = heure().let { it >= SOIR || it < MATIN }

    /** L'état des envies, créé (ou complété) à la demande : une partie neuve part de DEPART, une ancienne de MIGRATION. */
    fun e(jeu: Jeu): JSONObject {
        val neuf = !jeu.extra.has("envies")
        val e = jeu.module("envies")
        val now = maintenant()
        if (neuf) {
            val neuve = jeu.total == 0 && jeu.xp == 0
            e.put("v", JSONObject().apply { DEPART.forEach { (k, v) -> put(k, if (neuve) v else MIGRATION) } })
        }
        val v = e.optJSONObject("v") ?: JSONObject().also { e.put("v", it) }
        for (k in DEPART.keys) if (!v.has(k)) v.put(k, MIGRATION)
        if (!e.has("t")) e.put("t", now)
        if (!e.has("poussiere_t")) e.put("poussiere_t", now)
        for (k in listOf("cmd_t", "rappel_t", "rappel_n", "soir_t")) if (!e.has(k)) e.put(k, 0L)
        if (!e.has("xp_t")) e.put("xp_t", JSONObject())
        return e
    }

    private fun v(jeu: Jeu) = e(jeu).getJSONObject("v")

    // ------------------------------------------------------------ la poussière (seulement dans le terrain)
    fun placard(jeu: Jeu) = File(jeu.terrain, CACHE)

    fun poussieres(jeu: Jeu): List<File> =
        placard(jeu).listFiles()?.filter { it.isFile && it.name.lowercase().endsWith(".tmp") }?.sortedBy { it.name } ?: emptyList()

    fun proprete(jeu: Jeu): Double =
        if (!jeu.terrain.isDirectory) 100.0 else maxOf(0.0, 100.0 - 100.0 * poussieres(jeu).size / POUSSIERE_MAX)

    private fun poserPoussiere(jeu: Jeu): Boolean {
        val t = jeu.terrain
        if (!t.isDirectory) return false
        val d = placard(jeu)
        return try {
            d.mkdir()
            if (d.canonicalFile.parentFile != t.canonicalFile) return false     // placard remplacé par un lien
            val noms = poussieres(jeu).map { it.name }.toSet()
            if (noms.size >= POUSSIERE_MAX) return false
            val i = (1..999).first { "poussiere_$it.tmp" !in noms }
            File(d, "poussiere_$i.tmp").writeText(t("env.poussiere.contenu") + "\n")
            true
        } catch (x: Exception) {
            false
        }
    }

    private fun poussiere(jeu: Jeu, e: JSONObject, now: Long) {
        if (!jeu.terrain.isDirectory) { e.put("poussiere_t", now); return }
        if (!placard(jeu).exists()) placard(jeu).mkdir()
        val n = (now - e.optLong("poussiere_t", now)) / POUSSIERE_INTERVALLE
        if (n <= 0) return
        e.put("poussiere_t", e.optLong("poussiere_t", now) + n * POUSSIERE_INTERVALLE)
        var posees = 0
        repeat(minOf(n, POUSSIERE_MAX.toLong()).toInt()) { if (poserPoussiere(jeu)) posees++ }
        if (posees > 0 && !e.optBoolean("premiere_poussiere")) {
            e.put("premiere_poussiere", true)
            jeu.dire(t("env.poussiere.premiere", "cmd" to "envies"), 12)
        }
    }

    // ------------------------------------------------------------ valeurs
    fun valeur(jeu: Jeu, nom: String): Double = when (nom) {
        "faim" -> jeu.faim
        "proprete" -> proprete(jeu)
        else -> v(jeu).optDouble(nom, MIGRATION)
    }

    fun valeurs(jeu: Jeu): Map<String, Double> = ENVIES.associateWith { valeur(jeu, it) }

    /** Ce qui se voit dans la sauvegarde : commandes goûtées, leçons, quêtes, pièces visitées. */
    fun compteurs(jeu: Jeu): Map<String, Int> {
        val q = Quetes.q(jeu)
        val finies = Quetes.liste(q, "finies")
        val secrets = finies.count { Quetes.PAR_ID[it]?.sorte == "cachette" }
        val lieux = Quetes.liste(Maison.m(jeu), "visites").filter { it.count { c -> c == '/' } <= 1 && !it.startsWith(CACHE) }.toSet()
        return mapOf("seen" to jeu.vus.size, "lecon" to Histoire.faits(jeu).size * 50 + jeu.etape,
            "quetes" to finies.size - secrets, "secrets" to secrets, "lieux" to lieux.size)
    }

    // ------------------------------------------------------------ ce qui fait plaisir
    /** Satisfait une envie (n points). La récompense : un peu d'XP, et un merci si c'était l'envie du moment. */
    fun gagner(jeu: Jeu, nom: String, n: Double) {
        val e = e(jeu)
        val avant = when (nom) {
            "faim" -> jeu.faim.also { jeu.faim = minOf(100.0, it + n) }
            "proprete" -> 0.0
            else -> v(jeu).optDouble(nom, MIGRATION).also { v(jeu).put(nom, minOf(100.0, it + n)) }
        }
        val duMoment = e.optJSONObject("moment")?.optString("e") == nom
        val now = maintenant()
        val xpT = e.getJSONObject("xp_t")
        if (avant < SATISFAITE && n >= 8 && now - xpT.optLong(nom, 0L) >= XP_DELAI) {
            xpT.put(nom, now)
            jeu.ajouterXp(XP_BAS + if (duMoment) XP_MOMENT else 0)
        }
        if (duMoment && (valeur(jeu, nom) >= SATISFAITE || n >= MERCI)) {
            e.remove("moment")
            jeu.dire(Regles.auHasard("env.merci.$nom"), 8)
            jeu.animer("content")
        }
    }

    /** Appelé par les jeux (défi, combat, dressage, donjon, ctf, joue, devine). */
    fun plaisir(jeu: Jeu, nom: String, cle: String) {
        if (jeu.existe) gagner(jeu, nom, GAINS[cle] ?: 0.0)
    }

    /** sleep N : une vraie sieste (déjà faite par le shell). Renvoie les points de sommeil gagnés. */
    fun sieste(jeu: Jeu, secondes: Double): Double {
        val n = minOf(SIESTE_MAX, maxOf(0.0, secondes) * SIESTE_PAR_SECONDE)
        if (n <= 0) return 0.0
        jeu.log(t("env.sieste.log", "s" to fmt(secondes), "n" to n.toInt()))
        jeu.animer("dort")
        gagner(jeu, "sommeil", n)
        return n
    }

    /** La durée d'un « sleep N » tapé (ou null si ce n'est pas une sieste). */
    fun dureeSieste(ligne: String): Double? = SLEEP.find(ligne)?.groupValues?.get(1)?.toDoubleOrNull()

    private fun fmt(x: Double) = if (x == Math.floor(x)) x.toLong().toString() else x.toString()

    /** l'enfant est dans la grande salle du terrain (là où « rm .cache/<…>.tmp » vise le bon placard) */
    private fun salle(jeu: Jeu): Boolean = Maison.rel(jeu, Maison.ici(jeu)) == ""

    private fun dansTerrain(jeu: Jeu): Boolean = Maison.rel(jeu, Maison.ici(jeu)) != null

    // ------------------------------------------------------------ le temps qui passe
    /** Usure lente et repos (appelé par Jeu.tick) ; la poussière tombe. */
    fun temps(jeu: Jeu) {
        if (!jeu.existe) return
        val e = e(jeu)
        val now = maintenant()
        val v = v(jeu)
        val t0 = e.optLong("t", now)
        val dt = (now - t0).coerceIn(0L, 7 * 24 * 3600_000L)
        if (dt > 0) {
            for ((k, parH) in PAR_HEURE) {
                val x = v.optDouble(k, MIGRATION)
                if (x > PLANCHER_TEMPS) v.put(k, maxOf(PLANCHER_TEMPS, x - parH * dt / 3600_000.0))
            }
            val debutRepos = maxOf(t0, e.optLong("cmd_t") + PAUSE)        // le repos commence 10 min après la dernière commande
            if (now > debutRepos) v.put("sommeil", minOf(100.0, v.optDouble("sommeil", MIGRATION) + REPOS_HEURE * (now - debutRepos) / 3600_000.0))
            e.put("t", now)
        }
        if (Intro.ouvert(jeu, "envies")) poussiere(jeu, e, now)
    }

    // ------------------------------------------------------------ l'envie du moment et la bulle
    private val REPAS = listOf("date", "whoami", "pwd", "ls", "uptime", "id", "df")

    /** La commande à proposer pour cette envie (sans danger, depuis là où est l'enfant). */
    fun suggestion(jeu: Jeu, nom: String): String {
        val terrain = "~/${jeu.terrain.name}"
        return when (nom) {
            "faim" -> (REPAS.filter { it !in jeu.vus }.take(2).ifEmpty { REPAS.take(2) }).random()
            "jeu" -> listOf("defi", "donjon", "ctf", "joue pierre").random()
            "curiosite" -> {
                val e = jeu.etapeCourante()
                if (e != null && Random.nextDouble() < 0.5) e.cmd
                else (listOf("cp", "mv", "ls", "grep", "rm", "find").map { "explique $it" } + "ls --help").random()
            }
            "explorer" -> {
                if (jeu.terrain.isDirectory) {
                    val neuves = Maison.PIECES.filter { Histoire.pieceOuverte(jeu, it) && File(jeu.terrain, it).isDirectory && !Maison.visitee(jeu, it) }
                    if (neuves.isNotEmpty()) "cd $terrain/${neuves.random()}"
                    else if (dansTerrain(jeu)) "ls -a" else "carte"
                } else "carte"
            }
            "sommeil" -> "sleep $SIESTE_CONSEIL"
            // propreté : seulement depuis la grande salle du terrain (rm .cache/*.tmp ailleurs viserait un autre placard !)
            else -> if (salle(jeu)) {
                if (poussieres(jeu).isNotEmpty()) listOf("ls -a", "ls .cache", "rm .cache/*.tmp").random() else "ls .cache"
            } else "cd $terrain"
        }
    }

    /** L'envie à mettre en avant (ou null) : la faim si elle est urgente, sinon la plus basse sous SEUIL, un peu au hasard. */
    fun choisir(jeu: Jeu): String? {
        val vals = valeurs(jeu).toMutableMap()
        if (!jeu.terrain.isDirectory) vals["proprete"] = 100.0
        if (vals.getValue("faim") < FAIM_URGENTE) return "faim"
        val basses = vals.filter { it.value < SEUIL && it.key != "faim" }
        if (basses.isEmpty()) return null
        val mini = basses.values.minOrNull()!!
        return basses.filter { it.value <= mini + PROCHES }.keys.sorted().random()
    }

    /** L'envie du moment, gardée stable jusqu'à être satisfaite ou MOMENT_DUREE. */
    fun moment(jeu: Jeu): JSONObject? {
        val e = e(jeu)
        val m = e.optJSONObject("moment")
        val now = maintenant()
        if (m != null) {
            val nom = m.optString("e")
            if (nom in ENVIES && valeur(jeu, nom) < SATISFAITE && now - m.optLong("t") < MOMENT_DUREE &&
                !(nom != "faim" && jeu.faim < FAIM_URGENTE)) {
                if (nom == "proprete" && m.optString("cmd").startsWith("cd ") == salle(jeu)) {
                    m.put("cmd", suggestion(jeu, nom))                  // l'enfant est arrivé (ou reparti) : la commande suit
                    m.put("texte", Langue.auHasard("env.dit.$nom", "cmd" to m.getString("cmd")))
                }
                return m
            }
        }
        val nom = choisir(jeu)
        if (nom == null) { e.remove("moment"); return null }
        val n = JSONObject().put("e", nom).put("cmd", suggestion(jeu, nom)).put("t", now)
        n.put("texte", Langue.auHasard("env.dit.$nom", "cmd" to n.getString("cmd")))
        e.put("moment", n)
        return n
    }

    /** La phrase de l'envie du moment (la même tant que le moment dure), ou null. */
    fun phrase(jeu: Jeu): String? = moment(jeu)?.optString("texte")?.ifEmpty { null }

    private fun rappeler(jeu: Jeu, e: JSONObject, tapees: Int, now: Long) {
        e.put("rappel_n", e.optInt("rappel_n") + tapees)
        val m = moment(jeu)
        if (m != null && e.optInt("rappel_n") >= RAPPEL_COMMANDES && now - e.optLong("rappel_t") >= RAPPEL_MINUTES * 60_000L) {
            e.put("rappel_n", 0).put("rappel_t", now)
            m.put("texte", Langue.auHasard("env.dit.${m.getString("e")}", "cmd" to m.getString("cmd")))
            jeu.dire(m.getString("texte"), 12)
            jeu.animer(if (m.getString("e") == "sommeil") "dort" else "parle")
            return
        }
        if (tapees > 0 && soir() && now - e.optLong("soir_t") >= SOIR_MINUTES * 60_000L && v(jeu).optDouble("sommeil") < 70) {
            e.put("soir_t", now)
            jeu.dire(Regles.auHasard("env.soir"), 12)
            jeu.animer("dort")
        }
    }

    // ------------------------------------------------------------ le tour de jeu
    /** Après chaque commande tapée (Tour.apresCommande), après les leçons, les quêtes et les combats. */
    fun apresCommande(jeu: Jeu, ligne: String?, ignoree: Boolean) {
        if (!jeu.existe) return
        val e = e(jeu)
        val now = maintenant()
        temps(jeu)
        val tapee = ligne != null && !ignoree && Regles.premierMot(ligne).isNotEmpty()
        val v = v(jeu)
        if (tapee) {
            e.put("cmd_t", now)
            for ((k, n) in PAR_COMMANDE) {
                val usure = if (k == "sommeil" && soir()) SOMMEIL_SOIR else n
                v.put(k, maxOf(0.0, v.optDouble(k, MIGRATION) - usure))
            }
            val s = dureeSieste(ligne!!)
            if (s != null) sieste(jeu, s)
            else if (CURIEUX.containsMatchIn(ligne)) gagner(jeu, "curiosite", GAINS.getValue("explique"))
            if (REGARDE.containsMatchIn(ligne) && dansTerrain(jeu)) gagner(jeu, "explorer", GAINS.getValue("regarde"))
        }
        val c = compteurs(jeu)
        e.optJSONObject("vu")?.let { vu ->
            fun plus(k: String) = c.getValue(k) - vu.optInt(k, 0)
            if (plus("seen") > 0) gagner(jeu, "curiosite", minOf(2, plus("seen")) * GAINS.getValue("nouvelle"))
            if (plus("lecon") > 0) gagner(jeu, "curiosite", GAINS.getValue("lecon"))
            if (plus("quetes") > 0) gagner(jeu, "curiosite", GAINS.getValue("quete"))
            if (plus("secrets") > 0) gagner(jeu, "explorer", GAINS.getValue("secret"))
            if (plus("lieux") > 0) gagner(jeu, "explorer", minOf(2, plus("lieux")) * GAINS.getValue("lieu"))
        }
        e.put("vu", JSONObject(c))
        val m = e.optJSONObject("moment")
        if (m?.optString("e") == "faim" && jeu.faim >= SATISFAITE) {       // elle a bien mangé (Jeu.manger)
            e.remove("moment")
            jeu.dire(Regles.auHasard("env.merci.faim"), 8)
            jeu.animer("content")
        }
        val avant = if (e.has("propre_n")) e.optInt("propre_n") else null
        val n = poussieres(jeu).size
        if (avant != null && n < avant && tapee) {
            val duMoment = e.optJSONObject("moment")?.optString("e") == "proprete"
            if (n == 0 || duMoment) {
                gagner(jeu, "proprete", 100.0)
                if (!duMoment) {
                    jeu.dire(Regles.auHasard("env.merci.proprete"), 8)
                    jeu.animer("content")
                }
            }
        }
        e.put("propre_n", n)
        if (Intro.ouvert(jeu, "envies")) rappeler(jeu, e, if (tapee) 1 else 0, now)    // après leur présentation
    }

    // ------------------------------------------------------------ humeur et affichage
    /** L'humeur combine les envies : la faim d'abord (la santé), puis les envies à zéro, puis la moyenne. */
    fun humeurCle(jeu: Jeu): String {
        val vals = valeurs(jeu)
        val faim = vals.getValue("faim")
        when (Satiete.etat(jeu)) {
            "veille" -> return "sat.etat.veille"            // en veille (jamais de mort) : un repas complet la réveille
            "affamee" -> return "humeur.affame"
        }
        val zeros = vals.count { it.key != "faim" && it.value < 1 }
        return when {
            zeros >= 2 -> "humeur.grognon"
            zeros == 1 -> "humeur.triste"
            vals.values.sum() / vals.size >= 70 -> "humeur.joyeux"
            faim >= 60 -> "humeur.repu"
            else -> "humeur.creux"
        }
    }

    fun emoji(jeu: Jeu) = when (humeurCle(jeu)) {
        "humeur.joyeux" -> "😄"
        "humeur.repu" -> "😊"
        "humeur.creux" -> "🙂"
        "humeur.triste" -> "😢"
        "humeur.grognon" -> "😠"
        "humeur.affame" -> "😟"
        "sat.etat.veille" -> "💤"
        else -> "😵"
    }

    fun nom(envie: String) = t("env.nom.$envie")

    /** « 🍎▰▰▰▱ » : une jauge en petit. */
    fun jauge(jeu: Jeu, envie: String, n: Int = 4) = ICONES.getValue(envie) + Regles.barre(valeur(jeu, envie) + 100.0 / n / 2, 100.0, n)

    /** Les 6 jauges en petit, 3 par ligne. */
    fun compact(jeu: Jeu, n: Int = 4): String =
        ENVIES.chunked(3).joinToString("\n") { l -> l.joinToString(" ") { jauge(jeu, it, n) } }

    /** Les 3 plus basses (la vue réduite de la notification). */
    fun plusBasses(jeu: Jeu, n: Int = 4): String {
        val vals = valeurs(jeu)
        return ENVIES.sortedBy { vals.getValue(it) }.take(3).joinToString(" ") { jauge(jeu, it, n) }
    }

    fun comment(envie: String): String = when (envie) {
        "faim" -> t("env.comment.faim", "cmds" to "`date`, `ls`, `whoami`")
        "jeu" -> t("env.comment.jeu", "cmds" to "`defi`, `donjon`, `ctf`, `joue pierre`")
        "curiosite" -> t("env.comment.curiosite", "cmds" to "`explique cp`, `cherche`, `ls --help`")
        "explorer" -> t("env.comment.explorer", "cmds" to "`carte`", "lsa" to "`ls -a`")
        "sommeil" -> t("env.comment.sommeil", "cmd" to "`sleep $SIESTE_CONSEIL`")
        else -> t("env.comment.proprete", "aller" to "`cd ~/terrain_terminagotchi`",
            "voir" to "`ls -a`, `ls .cache`, `find . -name \"*.tmp\"`", "nettoyer" to "`rm .cache/*.tmp`")
    }

    /** La commande « envies » : l'état détaillé, et pour chaque envie comment la satisfaire. */
    fun ecran(jeu: Jeu): String {
        temps(jeu)
        val vals = valeurs(jeu)
        val lg = ENVIES.maxOf { nom(it).length }
        val out = mutableListOf(t("env.ecran.titre", "nom" to jeu.nom), "")
        for (k in ENVIES) {
            val x = vals.getValue(k)
            out.add("${ICONES[k]} ${Langue.ajuster(nom(k), lg)} ${Regles.barre(x + 5.0, 100.0, 10)} ${x.toInt().toString().padStart(3)}")
            out.add("   " + comment(k))
        }
        out.add("")
        val m = moment(jeu)
        out.add(if (m != null) t("env.ecran.moment", "icone" to ICONES[m.getString("e")], "envie" to nom(m.getString("e")), "cmd" to m.getString("cmd"))
            else t("env.ecran.aucune", "nom" to jeu.nom))
        out.add(t("env.ecran.humeur", "humeur" to "${emoji(jeu)} ${t(humeurCle(jeu))}"))
        out.add("")
        out.add(t("sat.ecran.titre"))                       // la satiété : état, assiette, série, vacances
        Satiete.lignes(jeu).forEach { out.add("  $it") }
        out.add("")
        out.add(t("env.cache.enfant", "lsa" to "`ls -a`"))
        out.add(t("env.cache.grands"))
        out.add("")
        out.add(t("env.ecran.pied", "nom" to jeu.nom))
        return out.joinToString("\n")
    }
}
