package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/**
 * La satiété (validée le 29 octobre) : pourquoi bien nourrir sa créature, sans mort ni corvée.
 * Portage de pc/tg/satiete.py (mêmes règles, mêmes seuils, mêmes textes ; calculs communs vérifiés par
 * donnees/satiete/vecteurs.json, voir tests/jvm/Satiete.kt).
 *
 *  1. Rythme : la faim ne baisse que de EVEIL h à COUCHER h (heure locale), 3 fois plus lentement qu'avant
 *     (2160 s d'éveil par point) ; Gardien ×2, Endurance jusqu'à ×2 (comme sur PC), talent du lien ×1.25.
 *     Mode vacances (commande `vacances`) : la faim est en pause.
 *  2. Quatre états : rassasiée (≥ 80), en forme (40-80), affamée (15-40), en veille (< 15) ; jamais de mort, jamais
 *     d'apprentissage bloqué ; la veille dure jusqu'à un repas complet (REVEIL_PLATS commandes différentes).
 *  3. Rassasiée : +20 % d'XP (commandes et leçons), dressage facilité, plus de rencontres, aura plus vive ;
 *     grandir demande aussi des jours soignés (JOURS_STADE) : l'XP en trop attend dans « reserve ».
 *  4. Affamée : −20 % d'XP sur les commandes (−40 % en veille ; jamais sur les leçons), pas de nouveau dressage ni
 *     de bonus de l'épreuve du jour, le guide grogne, l'aura pâlit.
 *  5. Aliments par famille, rendements décroissants, nouveau goût, petite assiette du jour (assiette complète).
 *  6. Jour soigné : un jour qui finit au moins en forme (même sans jouer) ; série de soins (un jour qui finit affamée
 *     retire un cran, jamais tout ; les vacances ne comptent ni pour ni contre), médailles.
 *  7. Longue absence : elle se repose dans son biome ; au retour, rien n'est perdu.
 * Sauvegarde : jeu.module("satiete") (local). Temps en secondes, dates locales AAAA-MM-JJ.
 */
object Satiete {
    const val SEC_PAR_POINT = 2160.0
    const val EVEIL = 7
    const val COUCHER = 21
    const val RASSASIEE = 80.0
    const val FORME = 40.0
    const val AFFAMEE = 15.0
    val ICONES_ETAT = mapOf("rassasiee" to "😋", "forme" to "🙂", "affamee" to "😟", "veille" to "💤", "repos" to "🌿")
    const val REVEIL_PLATS = 3
    const val REVEIL_FAIM = 40.0
    val XP_PCT = mapOf("rassasiee" to 20, "forme" to 0, "affamee" to -20, "veille" to -40, "repos" to 0)
    const val DRESSAGE_TEMPS = 15
    const val RENCONTRES = 1.25
    const val NOUVEAU = 8.0
    val PAR_FAMILLE = listOf(4.0, 3.0, 2.0, 2.0, 1.5)
    const val AUTRE = 2.0
    const val REPETEE = 0.5
    const val RATEE = 0.5
    const val ASSIETTE_FAIM = 10.0
    const val ASSIETTE_XP = 5
    const val JOUR_PLATS = 3
    const val JOUR_FAIM = 40.0
    val JOURS_STADE = mapOf(2 to 3, 3 to 7)
    val SEUIL_STADE = mapOf(2 to 160, 3 to 810)
    const val MIGRATION_JOURS = 3
    const val MIGRATION_FAIM = 50.0
    val SERIE_PALIERS = listOf(3, 7, 14, 30)
    val SERIE_XP = listOf(10, 15, 20, 30)
    const val LIEN_PHRASES = 3
    const val LIEN_REACTION = 7
    const val LIEN_TALENT = 30
    const val TALENT_LENT = 1.25
    const val ABSENCE_JOURS = 21
    const val RETOUR_FAIM = 60.0

    val FAMILLES = listOf("reperer", "batir", "lire", "brancher", "proteger", "observer")
    val ICONES = mapOf("reperer" to "🧭", "batir" to "🧱", "lire" to "🔍", "brancher" to "🔌", "proteger" to "🔑", "observer" to "🔭")
    val CMDS: Map<String, Set<String>> = mapOf(
        "reperer" to setOf("pwd", "ls", "dir", "cd", "tree", "gci", "get-childitem", "set-location", "pushd", "popd", "carte"),
        "batir" to setOf("mkdir", "touch", "echo", "cp", "mv", "rm", "rmdir", "ln", "new-item", "copy", "move", "del", "ren",
            "copy-item", "move-item", "remove-item", "add-content", "nano", "vim", "vi", "nvim", "edite", "git",
            "python", "python3", "py", "sh", "bash", "zsh", "alias", "make", "printf", "for", "if", "while"),
        "lire" to setOf("cat", "head", "tail", "less", "more", "grep", "find", "wc", "sort", "uniq", "rev", "type", "diff",
            "get-content", "select-string", "man", "explique", "cherche", "awk", "sed", "cut", "file", "which"),
        "brancher" to setOf("ping", "curl", "curl.exe", "wget", "ssh", "scp", "ip", "ifconfig", "ipconfig", "netstat", "nslookup",
            "dig", "traceroute", "tracert", "tracepath", "mtr", "hostname", "test-connection", "invoke-webrequest",
            "iwr", "web", "applis", "ouvre", "appelle", "sms", "partage", "lampe", "vibre", "batterie", "dis",
            "reglages", "am", "pm"),
        "proteger" to setOf("chmod", "chown", "whoami", "id", "groups", "sudo", "umask", "attrib", "icacls", "get-acl", "passwd"),
        "observer" to setOf("date", "cal", "uptime", "df", "du", "free", "ps", "top", "htop", "btop", "uname", "kill", "killall",
            "history", "getprop", "dumpsys", "sleep", "jobs", "systeminfo", "tasklist", "get-process", "get-date",
            "stat", "lsblk", "env"),
    )
    private val PAR_CMD: Map<String, String> = CMDS.flatMap { (f, cs) -> cs.map { it to f } }.toMap()

    /** l'horloge en secondes (remplaçable par un test) */
    var maintenant: () -> Double = { System.currentTimeMillis() / 1000.0 }

    // ------------------------------------------------------------ calculs communs (les mêmes en Python)
    fun famille(cmd: String?): String? {
        val c = (cmd ?: "").lowercase()
        if (c.startsWith("termux-")) return "brancher"
        return PAR_CMD[c]
    }

    fun etatDe(faim: Double, veille: Boolean = false): String = when {
        veille || faim < AFFAMEE -> "veille"
        faim >= RASSASIEE -> "rassasiee"
        faim >= FORME -> "forme"
        else -> "affamee"
    }

    fun jourDe(ts: Double): String = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date((ts * 1000).toLong()))

    /** Les secondes de [t0, t1] passées entre EVEIL h et COUCHER h (heure locale) : la faim ne baisse que là. */
    fun secondesEveil(t0: Double, t1: Double): Double {
        if (t1 <= t0) return 0.0
        var total = 0.0
        val c = Calendar.getInstance().apply { timeInMillis = (t0 * 1000).toLong() }
        val fin = jourDe(t1)
        var n = 0
        while (n < 400) {
            val j = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(c.time)
            val a = (c.clone() as Calendar).apply { set(Calendar.HOUR_OF_DAY, EVEIL); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }
            val b = (c.clone() as Calendar).apply { set(Calendar.HOUR_OF_DAY, COUCHER); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }
            val lo = maxOf(t0, a.timeInMillis / 1000.0)
            val hi = minOf(t1, b.timeInMillis / 1000.0)
            if (hi > lo) total += hi - lo
            if (j >= fin) break
            c.set(Calendar.HOUR_OF_DAY, 12)
            c.add(Calendar.DAY_OF_MONTH, 1)
            n++
        }
        return total
    }

    /** Secondes (d'éveil) par point de faim. */
    fun taux(gardien: Boolean = false, endurance: Int = 0, lien: Int = 0): Double {
        val r = SEC_PAR_POINT * (if (gardien) 2 else 1) * (1 + minOf(1.0, maxOf(0, endurance) / 100.0))
        return r * (if (lien >= LIEN_TALENT) TALENT_LENT else 1.0)
    }

    fun valeurRepas(nouvelle: Boolean, ratee: Boolean, repetee: Boolean, nFamille: Int, aFamille: Boolean = true): Double = when {
        ratee -> RATEE
        repetee -> REPETEE
        nouvelle -> NOUVEAU
        !aFamille -> AUTRE
        else -> PAR_FAMILLE[minOf(nFamille, PAR_FAMILLE.size - 1)]
    }

    /** (xp donnée, nouveau reste en centièmes) : +20 % rassasiée, −20 % affamée… sans rien perdre à l'arrondi. */
    fun xpAjuste(gain: Int, etat: String, reste: Int = 0): Pair<Int, Int> {
        if (gain <= 0) return gain to reste
        val total = gain * (100 + (XP_PCT[etat] ?: 0)) + reste
        return Math.floorDiv(total, 100) to Math.floorMod(total, 100)
    }

    fun palierSerie(serie: Int) = SERIE_PALIERS.count { serie >= it }

    /** Un jour manqué (fini affamée ou en veille) : la série perd UN cran, jamais tout. */
    fun serieManquee(serie: Int) = maxOf(0, serie - 1)

    /** Le début (00:00, heure locale) du jour qui suit l'instant ts. */
    fun minuitApres(ts: Double): Double {
        val c = Calendar.getInstance().apply { timeInMillis = (ts * 1000).toLong() }
        c.set(Calendar.HOUR_OF_DAY, 12); c.add(Calendar.DAY_OF_MONTH, 1)
        c.set(Calendar.HOUR_OF_DAY, 0); c.set(Calendar.MINUTE, 0); c.set(Calendar.SECOND, 0); c.set(Calendar.MILLISECOND, 0)
        return c.timeInMillis / 1000.0
    }

    fun joursPour(stade: Int) = JOURS_STADE[stade] ?: 0

    // ------------------------------------------------------------ l'état dans la sauvegarde
    private fun lst(s: JSONObject, k: String): MutableList<String> {
        val a = s.optJSONArray(k) ?: return mutableListOf()
        return (0 until a.length()).map { a.optString(it) }.toMutableList()
    }

    private fun put(s: JSONObject, k: String, l: List<String>) { s.put(k, JSONArray(l)) }

    /** L'état de la satiété, créé à la demande (une ancienne partie : MIGRATION_JOURS jours offerts, au moins en forme). */
    fun s(jeu: Jeu): JSONObject {
        val neuf = !jeu.extra.has("satiete")
        val s = jeu.module("satiete")
        if (neuf && !(jeu.total == 0 && jeu.xp == 0)) {
            s.put("jours", MIGRATION_JOURS)
            jeu.faim = maxOf(jeu.faim, MIGRATION_FAIM)
            jeu.dernierTick = System.currentTimeMillis()   // le temps passé avec l'ancienne règle ne compte pas deux fois
        }
        val now = maintenant()
        for ((k, v) in listOf<Pair<String, Any>>("jours" to 0, "serie" to 0, "meilleure" to 0, "medailles" to 0, "veille" to false,
            "vacances" to false, "jour" to "", "compte" to false, "complete" to false, "dernier" to "", "clos" to "",
            "reserve" to 0, "xp_reste" to 0, "prete_dit" to 0.0, "repas_t" to now, "reaction" to ""))
            if (!s.has(k)) s.put(k, v)
        for (k in listOf("reveil", "assiette", "plats")) if (!s.has(k)) s.put(k, JSONArray())
        return s
    }

    fun lien(jeu: Jeu) = s(jeu).optInt("jours")

    fun absente(jeu: Jeu, now: Double = maintenant()): Boolean {
        val s = s(jeu)
        return !s.optBoolean("vacances") && now - s.optDouble("repas_t", now) > ABSENCE_JOURS * 86400.0
    }

    /** « rassasiee », « forme », « affamee », « veille » (ou « repos » pendant une longue absence). */
    fun etat(jeu: Jeu): String = if (absente(jeu)) "repos" else etatDe(jeu.faim, s(jeu).optBoolean("veille"))

    fun affamee(jeu: Jeu) = etat(jeu) in setOf("affamee", "veille")
    fun rassasiee(jeu: Jeu) = etat(jeu) == "rassasiee"
    fun nomEtat(e: String) = t("sat.etat.$e")

    // ------------------------------------------------------------ le temps qui passe
    /** La faim baisse (heures d'éveil seulement, rien en vacances) ; la veille commence sous AFFAMEE. Chaque jour fini
     *  (même sans jouer, même téléphone éteint : on le recalcule) est jugé : soigné s'il finit au moins en forme.
     *  Renvoie une notification à montrer (ou null). Appelé par Jeu.tick. */
    fun tick(jeu: Jeu, now: Double = maintenant()): String? {
        val s = s(jeu)
        var t0 = jeu.dernierTick / 1000.0
        var notif: String? = null
        if (now > t0) {
            var n = 0
            while (jourDe(t0) < jourDe(now) && n < 60) {         // les jours finis depuis la dernière fois, un par un
                val fin = minuitApres(t0)
                baisser(jeu, s, t0, fin)?.let { notif = it }
                cloturer(jeu, s, jourDe(t0))
                t0 = fin; n++
            }
            baisser(jeu, s, maxOf(t0, now - 86400), now)?.let { notif = it }
        }
        jeu.dernierTick = (now * 1000).toLong()
        nouveauJour(s, now)
        return notif
    }

    private fun baisser(jeu: Jeu, s: JSONObject, t0: Double, t1: Double): String? {
        val avant = jeu.faim
        if (!s.optBoolean("vacances") && t1 > t0) {
            val r = taux("Gardien" in jeu.skills, jeu.stats["Endurance"] ?: 0, s.optInt("jours"))
            jeu.faim = (avant - secondesEveil(t0, t1) / r).coerceIn(0.0, 100.0)
        }
        val h = jeu.faim
        if (h < AFFAMEE && !s.optBoolean("veille")) {
            s.put("veille", true); put(s, "reveil", emptyList())
            return t("sat.notif.veille", "nom" to jeu.nom)
        }
        return if (avant >= FORME && h < FORME) t("core.notif.faim") else null
    }

    /** Le jour j est fini : soigné s'il a fini au moins en forme (sinon la série perd un cran) ; neutre en vacances. */
    private fun cloturer(jeu: Jeu, s: JSONObject, j: String) {
        val clos = s.optString("clos")
        if (clos.isNotEmpty() && clos >= j) return
        s.put("clos", j)
        if (s.optBoolean("vacances") || (s.optString("jour") == j && s.optBoolean("compte"))) return
        if (jeu.faim >= JOUR_FAIM && !s.optBoolean("veille")) compter(jeu, s, j)
        else s.put("serie", serieManquee(s.optInt("serie")))
    }

    private fun nouveauJour(s: JSONObject, now: Double) {
        val j = jourDe(now)
        if (s.optString("jour") != j) {
            s.put("jour", j); put(s, "assiette", emptyList()); put(s, "plats", emptyList())
            s.put("compte", false); s.put("complete", false)
        }
    }

    // ------------------------------------------------------------ les repas
    /** Une commande mangée : la faim monte selon l'aliment ; l'assiette, la veille, le jour soigné. Renvoie le gain. */
    fun repas(jeu: Jeu, cmd: String, nouvelle: Boolean = false, ratee: Boolean = false, repetee: Boolean = false,
              now: Double = maintenant()): Double {
        val s = s(jeu)
        nouveauJour(s, now)
        if (!ratee && now - s.optDouble("repas_t", now) > ABSENCE_JOURS * 86400.0 && !s.optBoolean("vacances")) {
            s.put("repas_t", now)                  // 7. longue absence : elle revient de son biome, rien n'est perdu
            s.put("veille", false)
            jeu.faim = maxOf(jeu.faim, RETOUR_FAIM)
            jeu.dire(t("sat.retour", "nom" to jeu.nom), 14)
            jeu.animer("content")
        }
        val f = famille(cmd)
        val assiette = lst(s, "assiette")
        val nF = if (f != null) assiette.count { it == f } else 0
        val gain = valeurRepas(nouvelle, ratee, repetee, nF, f != null)
        jeu.faim = minOf(100.0, jeu.faim + gain)
        if (ratee) return gain
        s.put("repas_t", now)
        if (f != null && !repetee) { assiette.add(f); put(s, "assiette", assiette) }
        val plats = lst(s, "plats")
        if (cmd !in plats) put(s, "plats", (plats + cmd).takeLast(30))
        if (f != null && !s.optBoolean("complete") && FAMILLES.all { it in assiette }) {
            s.put("complete", true)                // l'assiette complète : une fois par jour
            jeu.faim = minOf(100.0, jeu.faim + ASSIETTE_FAIM)
            jeu.dire(t("sat.assiette.complete", "nom" to jeu.nom), 10)
            jeu.ajouterXp(ASSIETTE_XP)
        }
        if (s.optBoolean("veille")) {
            val reveil = lst(s, "reveil")
            if (cmd !in reveil) reveil.add(cmd)
            if (reveil.size >= REVEIL_PLATS) {
                s.put("veille", false); put(s, "reveil", emptyList())
                jeu.faim = maxOf(jeu.faim, REVEIL_FAIM)
                jeu.dire(t("sat.reveil", "nom" to jeu.nom), 12)
                jeu.animer("content")
            } else {
                put(s, "reveil", reveil)
                jeu.dire(t("sat.veille.encore", "n" to REVEIL_PLATS - reveil.size), 8)
            }
        }
        jourSoigne(jeu, s)
        if (s.optInt("jours") >= LIEN_REACTION && s.optString("reaction") != s.optString("jour") && !s.optBoolean("veille")) {
            s.put("reaction", s.optString("jour"))  // le lien : un petit cœur au premier repas du jour
            jeu.dire(Langue.auHasard("sat.lien.coeur", "nom" to jeu.nom), 8)
        }
        return gain
    }

    /** Pendant le jeu, le jour compte dès JOUR_PLATS commandes différentes avec la faim au moins en forme. */
    private fun jourSoigne(jeu: Jeu, s: JSONObject) {
        if (s.optBoolean("compte") || s.optBoolean("veille") || lst(s, "plats").size < JOUR_PLATS || jeu.faim < JOUR_FAIM) return
        s.put("compte", true)
        compter(jeu, s, s.optString("jour"))
    }

    /** Un jour soigné de plus : la série, le lien, les médailles, l'évolution qui attendait. */
    private fun compter(jeu: Jeu, s: JSONObject, j: String) {
        s.put("jours", s.optInt("jours") + 1)
        val avant = palierSerie(s.optInt("serie"))
        s.put("serie", s.optInt("serie") + 1)
        s.put("meilleure", maxOf(s.optInt("meilleure"), s.optInt("serie")))
        s.put("dernier", j)
        val p = palierSerie(s.optInt("serie"))
        if (p > avant && p > s.optInt("medailles")) {
            s.put("medailles", p)
            val xp = SERIE_XP[p - 1]
            jeu.log("🎯 " + t("sat.serie.medaille", "n" to SERIE_PALIERS[p - 1], "xp" to xp))
            jeu.dire(t("sat.serie.medaille", "n" to SERIE_PALIERS[p - 1], "xp" to xp), 12)
            jeu.ajouterXp(xp)
        }
        if (s.optInt("jours") == LIEN_TALENT) jeu.dire(t("sat.lien.talent", "nom" to jeu.nom), 14)
        liberer(jeu)
    }

    // ------------------------------------------------------------ l'XP et l'évolution
    /** L'XP d'une commande ou d'une leçon (+20 % rassasiée, −20 % affamée ; une leçon n'en perd jamais). */
    fun gagnerXp(jeu: Jeu, n: Int, lecon: Boolean = false): Int {
        var x = n
        val e = etat(jeu)
        if (n > 0 && !Intro.retient(jeu) && !(lecon && (XP_PCT[e] ?: 0) < 0)) {
            val s = s(jeu)
            val (v, r) = xpAjuste(n, e, s.optInt("xp_reste"))
            x = v; s.put("xp_reste", r)
        }
        jeu.ajouterXp(x)
        return x
    }

    /** Appelé par Jeu.ajouterXp : l'XP s'arrête juste avant le seuil d'un stade sans assez de jours soignés. */
    fun retenir(jeu: Jeu, avant: Int): Boolean {
        val s = s(jeu)
        for ((st, seuil) in SEUIL_STADE) {
            if (avant < seuil && jeu.xp >= seuil && s.optInt("jours") < joursPour(st)) {
                s.put("reserve", s.optInt("reserve") + jeu.xp - (seuil - 1))
                jeu.xp = seuil - 1
                val now = maintenant()
                if (now - s.optDouble("prete_dit") > 3600) {
                    s.put("prete_dit", now)
                    jeu.dire(t("sat.prete", "nom" to jeu.nom, "n" to joursPour(st) - s.optInt("jours")), 14)
                }
                return true
            }
        }
        return false
    }

    /** Assez de jours soignés : l'XP mise de côté revient (et l'évolution a lieu). */
    fun liberer(jeu: Jeu) {
        val s = s(jeu)
        if (s.optInt("reserve") <= 0) return
        val st = SEUIL_STADE.entries.firstOrNull { jeu.xp == it.value - 1 }?.key
        if (st != null && s.optInt("jours") < joursPour(st)) return
        val r = s.optInt("reserve")
        s.put("reserve", 0)
        jeu.ajouterXp(r)
    }

    /** Le niveau en comptant l'XP mise de côté (les fonctions qui s'ouvrent : jamais bloquées). */
    fun niveauAppris(jeu: Jeu) = Regles.niveau(jeu.xp + s(jeu).optInt("reserve"))

    /** Le niveau demandé par une leçon ne dépasse jamais celui-ci. */
    fun plafond(jeu: Jeu) = if (s(jeu).optInt("reserve") > 0) jeu.niveau else 99

    fun prochaineEvolution(jeu: Jeu): Pair<Int, Int>? {
        val vise = jeu.stade + 1
        val n = JOURS_STADE[vise] ?: return null
        return vise to maxOf(0, n - s(jeu).optInt("jours"))
    }

    // ------------------------------------------------------------ vacances
    fun vacances(jeu: Jeu, on: Boolean? = null): String {
        val s = s(jeu)
        val v = on ?: !s.optBoolean("vacances")
        s.put("vacances", v)
        if (!v) s.put("repas_t", maxOf(s.optDouble("repas_t"), maintenant()))   // le retour n'est pas une longue absence
        return t(if (v) "sat.vacances.on" else "sat.vacances.off", "nom" to jeu.nom, "cmd" to "vacances")
    }

    // ------------------------------------------------------------ l'affichage
    fun assiette(jeu: Jeu): String {
        val s = s(jeu)
        if (s.optString("jour") != jourDe(maintenant())) return FAMILLES.joinToString(" ") { "·" }
        val a = lst(s, "assiette")
        return FAMILLES.joinToString(" ") { if (it in a) ICONES.getValue(it) else "·" }
    }

    fun nbAssiette(jeu: Jeu): Int {
        val s = s(jeu)
        return if (s.optString("jour") == jourDe(maintenant())) lst(s, "assiette").filter { it in FAMILLES }.toSet().size else 0
    }

    fun ligneAssiette(jeu: Jeu) = t("sat.assiette", "assiette" to assiette(jeu), "n" to nbAssiette(jeu), "total" to FAMILLES.size)

    fun ligneEtat(jeu: Jeu): String { val e = etat(jeu); return "${ICONES_ETAT.getValue(e)} ${nomEtat(e)}" }

    private val SURES = mapOf("reperer" to "pwd", "batir" to "echo miam", "lire" to "cat --help", "brancher" to "hostname",
        "proteger" to "whoami", "observer" to "date")

    fun suggestion(jeu: Jeu): Pair<String, String>? {
        val s = s(jeu)
        val a = if (s.optString("jour") == jourDe(maintenant())) lst(s, "assiette") else emptyList()
        val f = FAMILLES.firstOrNull { it !in a } ?: return null
        return f to SURES.getValue(f)
    }

    /** Le détail (dans l'écran « envies », et « satiete »). */
    fun lignes(jeu: Jeu): List<String> {
        val s = s(jeu)
        val e = etat(jeu)
        val out = mutableListOf(t("sat.ecran.etat", "etat" to ligneEtat(jeu), "faim" to jeu.faim.toInt()),
            t("sat.ecran.effet.$e"), ligneAssiette(jeu))
        suggestion(jeu)?.let { (f, cmd) ->
            out.add(t("sat.ecran.gouter", "icone" to ICONES[f], "famille" to t("sat.famille.$f"), "cmd" to cmd))
        }
        if (s.optBoolean("veille")) out.add(t("sat.veille.encore", "n" to REVEIL_PLATS - lst(s, "reveil").size))
        out.add(t("sat.ecran.serie", "n" to s.optInt("serie"), "meilleure" to s.optInt("meilleure"), "jours" to s.optInt("jours")))
        prochaineEvolution(jeu)?.let { if (it.second > 0) out.add(t("sat.ecran.grandir", "n" to it.second)) }
        out.add(t("sat.ecran.biome." + when (e) { "rassasiee" -> "fleuri"; "affamee", "veille" -> "fane"; else -> "normal" }))
        out.add(t("sat.ecran.vacances." + (if (s.optBoolean("vacances")) "on" else "off"), "cmd" to "vacances"))
        return out
    }
}
