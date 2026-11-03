package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.Normalizer

/**
 * Apprendre en jouant (idées cochées du 3 novembre, maquettes validées), portage de pc/tg/apprendre.py : bac à sable
 * (27), tableau des rares (46), maîtrise (43), révisions (24), commande du jour (29), énigmes de la semaine (44),
 * mini-énigmes d'erreur (23), carnet illustré (21, images dans ApprendreDessin.kt), mini-jeux (41), course (42), limite
 * de temps douce (49), sentier des marmottes (45), examen et diplôme (30). Mêmes règles et mêmes graines qu'en Python
 * (vecteurs communs donnees/apprendre/vecteurs.json, tests/jvm/Apprendre.kt). Sur le téléphone, les commandes
 * s'écrivent sans « tg » (bac-a-sable, carnet, jeux…) ; « tg carnet » marche aussi. Rien n'est envoyé.
 */
object Apprendre {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("apprendre.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()
    private fun lst(a: JSONArray?): List<String> = a?.let { x -> (0 until x.length()).map { x.get(it).toString() } } ?: emptyList()
    fun cmds(): List<String> = lst(donnees().optJSONArray("cmds"))

    const val VERT = 0xFFAFD787.toInt()
    /** les commandes que le joueur tape (sur le téléphone, sans « tg ») */
    val COMMANDES = setOf("bac-a-sable", "bac_a_sable", "souvenirs", "revisions", "révisions", "jour", "enigme", "énigme", "passe",
        "carnet", "jeux", "course", "examen", "maitrise", "maîtrise")

    // ================================================================ la spécification pure (vecteurs communs)
    /** FNV-1a 32 bits des octets UTF-8 (la graine du jour, de la semaine : la même pour tous, sans réseau). */
    fun fnv(texte: String): Long {
        var h = 0x811C9DC5L
        for (b in texte.toByteArray(Charsets.UTF_8)) h = ((h xor (b.toLong() and 0xFF)) * 0x01000193L) and 0xFFFFFFFFL
        return h
    }

    fun joursEntre(a: String, b: String): Int = try {
        java.time.temporal.ChronoUnit.DAYS.between(java.time.LocalDate.parse(a), java.time.LocalDate.parse(b)).toInt()
    } catch (e: Exception) { 0 }

    fun intervalle(etape: Int): Int {
        val iv = o("revision").optJSONArray("intervalles") ?: JSONArray("[1,3,7,14,30]")
        return iv.getInt(etape.coerceIn(0, iv.length() - 1))
    }

    /** La commande à rafraîchir aujourd'hui (la plus en retard ; à égalité, l'ordre du carnet), ou null. */
    fun revisionDue(vus: JSONObject, jour: String): String? {
        var best: String? = null
        var bv: Int? = null
        for (c in cmds()) {
            val v = vus.optJSONArray(c) ?: continue
            val retard = joursEntre(v.getString(0), jour) - intervalle(v.optInt(1))
            if (retard >= 0 && (bv == null || retard > bv)) { best = c; bv = retard }
        }
        return best
    }

    fun commandeDuJour(jour: String, connues: Set<String>): String {
        val pool = cmds().filter { it in connues }.toMutableList()
        cmds().firstOrNull { it !in connues }?.let { pool.add(it) }
        return if (pool.isEmpty()) cmds()[0] else pool[(fnv(jour) % pool.size).toInt()]
    }

    fun niveauMaitrise(m: JSONArray?, vue: Boolean): Int {
        if (m != null && m.optInt(2) != 0) return 3
        if (!vue) return 0
        return if (m != null && m.optInt(0) != 0) 2 else 1
    }

    /** (modèle, mot, nombre) de l'énigme de la semaine « 2026-W45 ». */
    fun enigme(semaine: String, connues: Set<String>): Triple<String, String, Int> {
        val e = o("enigmes")
        val mods = (0 until e.getJSONArray("modeles").length()).map { e.getJSONArray("modeles").getJSONObject(it) }
            .filter { it.getString("besoin") == "ls" || it.getString("besoin") in connues }.map { it.getString("id") }
        val mots = lst(e.getJSONArray("mots"))
        return Triple(mods[(fnv(semaine) % mods.size).toInt()], mots[(fnv("$semaine:mot") % mots.size).toInt()],
            3 + (fnv("$semaine:n") % 5).toInt())
    }

    fun etatTemps(secondes: Double, limite: Int?, baille: Int = 5, pause: Int = 60): String {
        val m = secondes / 60.0
        if (limite != null && limite > 0) return if (m >= limite) "dort" else if (m >= limite - baille) "baille" else "eveil"
        return if (m >= pause) "pause" else "eveil"
    }

    fun ajouterTemps(etat: JSONObject, now: Double, trou: Int = 300): JSONObject {
        val jour = jourDe(now)
        if (etat.optString("jour") != jour) {
            etat.put("jour", jour).put("s", 0.0).put("t", now).put("baille", false)
            return etat
        }
        val dt = now - etat.optDouble("t", now)
        if (dt > 0 && dt <= trou) etat.put("s", etat.optDouble("s", 0.0) + dt)
        etat.put("t", now)
        return etat
    }

    fun jourDe(ts: Double) = Satiete.jourDe(ts)
    fun maintenant() = System.currentTimeMillis() / 1000.0

    fun prochainReveil(ts: Double, heure: Int = 7): Double {
        val c = java.util.Calendar.getInstance().apply { timeInMillis = (ts * 1000).toLong() }
        val r = (c.clone() as java.util.Calendar).apply {
            set(java.util.Calendar.HOUR_OF_DAY, heure); set(java.util.Calendar.MINUTE, 0); set(java.util.Calendar.SECOND, 0); set(java.util.Calendar.MILLISECOND, 0)
        }
        if (!r.after(c)) r.add(java.util.Calendar.DAY_OF_MONTH, 1)
        return r.timeInMillis / 1000.0
    }

    fun semaine(ts: Double = maintenant()) = Entrainement.semaine((ts * 1000).toLong())

    // ================================================================ l'état (module « apprendre »)
    fun a(jeu: Jeu): JSONObject {
        val a = jeu.module("apprendre")
        for ((k, v) in listOf<Pair<String, Any>>("vus" to JSONObject(), "rev" to JSONObject(), "maitrise" to JSONObject(),
            "tampons" to JSONArray(), "enigmes" to JSONArray(), "eindices" to JSONObject(), "erreur_t" to 0.0, "jeux" to JSONObject(),
            "course" to false, "eclairs" to true, "temps" to JSONObject(), "bac_ici" to false, "sentier" to JSONArray(),
            "examen" to JSONObject(), "diplomes" to JSONArray())) if (!a.has(k)) a.put(k, v)
        return a
    }

    private fun ajouter(arr: JSONArray, v: String, max: Int = 1000) { arr.put(v); while (arr.length() > max) arr.remove(0) }

    fun dans(chemin: File?, dossier: File): Boolean {
        if (chemin == null) return false
        return try {
            val p = chemin.canonicalFile; val d = dossier.canonicalFile
            p == d || p.path.startsWith(d.path + File.separator)
        } catch (e: Exception) { false }
    }

    private fun lien(f: File) = try { java.nio.file.Files.isSymbolicLink(f.toPath()) } catch (e: Exception) { false }

    private fun ecrire(f: File, contenu: String) {
        f.parentFile?.mkdirs()
        if (lien(f)) return
        f.writeText(contenu)
    }

    /** Efface un dossier du jeu DANS le terrain (jamais un lien, jamais le terrain entier ni ailleurs). */
    fun vider(jeu: Jeu, d: File): Boolean {
        if (lien(d) || !dans(d, jeu.terrain) || d.canonicalFile == jeu.terrain.canonicalFile) return false
        if (d.exists()) d.walkBottomUp().onEnter { !lien(it) || it == d }.forEach { it.delete() }
        return true
    }

    private fun mots(ligne: String) = ligne.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
    private fun premier(ligne: String) = Regles.premierMot(ligne)
    private fun rel(jeu: Jeu, f: File) = "~/" + f.canonicalFile.relativeTo(jeu.home.canonicalFile).path

    // ================================================================ 27. le bac à sable
    fun dossierBac(jeu: Jeu) = File(jeu.terrain, o("bac").optString("dossier", "bac_a_sable"))

    fun preparerBac(jeu: Jeu, neuf: Boolean = false): File {
        val d = dossierBac(jeu)
        if (neuf) vider(jeu, d)
        d.mkdirs()
        val j = o("bac").getJSONObject("jouets")
        for (r in j.keys()) {
            val f = File(d, r)
            if (r.endsWith("/")) f.mkdirs() else if (!f.exists()) ecrire(f, t(j.getString(r), "cmd" to "bac-a-sable neuf") + "\n")
        }
        return d
    }

    fun commandeBac(jeu: Jeu, reste: String): String {
        val neuf = mots(reste).firstOrNull()?.lowercase() in setOf("neuf", "new", "reset")
        val d = preparerBac(jeu, neuf)
        return listOf("🏖 " + t("apr.bac.titre", "nom" to jeu.nom), "  " + t("apr.bac.regle"),
            "  " + t("apr.bac.aller", "cmd" to "cd ${rel(jeu, d)}"),
            "  " + if (neuf) t("apr.bac.neuf_ok") else t("apr.bac.neuf", "cmd" to "bac-a-sable neuf")).joinToString("\n")
    }

    /** Vrai si le tour ne compte rien : le bac à sable (cwd dedans) ou elle dort. Les messages vont dans msgs. */
    fun enPause(jeu: Jeu, cwd: File?, msgs: MutableList<Pair<String, Int>>): Boolean {
        val a = a(jeu)
        val bac = dans(cwd, dossierBac(jeu))
        if (bac && !a.optBoolean("bac_ici")) msgs.add("🏖 " + t("apr.bac.bandeau") to 0xFFFFD75F.toInt())
        a.put("bac_ici", bac)
        val tp = a.getJSONObject("temps")
        if (tp.optDouble("dort", 0.0) > 0 && !endormie(jeu)) {
            tp.put("dort", 0.0)
            msgs.add("☀ " + t("apr.temps.reveil", "nom" to jeu.nom) to VERT)
            jeu.dire(t("apr.temps.reveil", "nom" to jeu.nom), 10)
            jeu.animer("content")
        }
        return bac || endormie(jeu)
    }

    /** Pendant le bac à sable ou le sommeil : une commande jamais tapée devient « découverte », rien d'autre. */
    fun tourPause(jeu: Jeu, ligne: String, colle: Boolean, msgs: MutableList<Pair<String, Int>>) {
        if (colle) return
        val c = premier(ligne)
        val connue = c in cmds() || Regles.CATEGORIES.values.any { c in it }
        if (c.isNotEmpty() && connue) jeu.vus.add(c)
        if (endormie(jeu) && !a(jeu).optBoolean("bac_ici")) {
            jeu.animer("dort")
            msgs.add("💤 " + t("apr.temps.chut", "nom" to jeu.nom) to 0xFF9A9AB0.toInt())
        }
    }

    // ================================================================ 46. le tableau des rares
    fun indiceRare(e: Bestiaire.Espece): String {
        val c = e.attireePar
        return if (c in setOf("sudo", "su", "doas", "") || c !in cmds().toSet() + setOf("ps", "df", "free", "ping", "git", "rev"))
            t("apr.rares.tres_rarement") else t("apr.rares.attiree", "cmd" to c)
    }

    fun rares(page: Int): List<Bestiaire.Espece> {
        val r = if (page == 1) setOf("légendaire", "mythique") else setOf("rare")
        return Bestiaire.especes.filter { it.rarete in r && (!it.secrete || it.rarete == "mythique") }
    }

    fun ecranRares(jeu: Jeu, reste: String): String {
        val page = if (mots(reste).firstOrNull() in setOf("2", "rares", "rare")) 2 else 1
        val liste = rares(page)
        val col = Explo.collection(jeu)
        val vues = col.keys().asSequence().filter { col.optInt(it) > 0 }.toSet()
        val ok = { e: Bestiaire.Espece -> e.nom in vues || e.id in vues }
        val caps = Explo.captures(jeu)
        val shinies = (0 until caps.length()).map { caps.getJSONObject(it) }.filter { it.optBoolean("shiny") }
        val out = mutableListOf("✨ " + t(if (page == 1) "apr.rares.titre" else "apr.rares.titre2", "nom" to jeu.nom) +
            "  ${liste.count(ok)} / ${liste.size}   shiny : ${shinies.size}", "")
        for (rang in liste.chunked(3)) {
            out.add(rang.joinToString("   ") { if (ok(it)) Bestiaire.balise(it) else "¤ombre:${it.id}¤" })
            out.add(rang.joinToString("  ·  ") { if (ok(it)) "${it.nom} ✓" else "??? " + indiceRare(it) })
        }
        if (page == 1 && shinies.isNotEmpty()) {
            out.add("")
            out.add(t("apr.rares.shiny", "n" to shinies.size))
            out.add(shinies.takeLast(4).joinToString(" ") { Bestiaire.balise(it) })
        }
        out.add(t("apr.rares.pied", "cmd" to if (page == 1) "collection rares 2" else "collection rares"))
        return out.joinToString("\n")
    }

    // ================================================================ 43. la maîtrise
    fun noterUsage(jeu: Jeu, ligne: String, code: Int?, aide: Boolean): String? {
        val c = premier(ligne)
        if (c !in cmds() || (code != null && code != 0)) return null
        val ma = a(jeu).getJSONObject("maitrise")
        val m = ma.optJSONArray(c) ?: JSONArray("[0,0,0]").also { ma.put(c, it) }
        if (mots(ligne).drop(1).any { it.startsWith("-") && it.length > 1 && it != "--" }) m.put(0, 1)
        if (aide) return null
        m.put(1, m.optInt(1) + 1)
        if (m.optInt(1) >= o("maitrise").optInt("reussites", 5) && m.optInt(2) == 0) {
            m.put(2, 1)
            var msg = "🏅 " + t("apr.maitrise.or", "cmd" to c)
            jeu.log(msg)
            if (nbMaitrisees(jeu) == o("maitrise").optInt("titre", 10)) msg += " " + t("apr.maitrise.titre", "titre" to t("apr.titre.main_sure"))
            return msg
        }
        return null
    }

    fun nbMaitrisees(jeu: Jeu): Int {
        val ma = a(jeu).getJSONObject("maitrise")
        return ma.keys().asSequence().count { ma.optJSONArray(it)?.optInt(2) == 1 }
    }

    /** « ●●○ » (vert), « ●●◉ » doré : ‹#rrggbb|…› colore le texte (miseEnForme). */
    fun ronds(jeu: Jeu, c: String): String {
        val n = niveauMaitrise(a(jeu).getJSONObject("maitrise").optJSONArray(c), c in jeu.vus)
        if (n == 3) return "‹#ffd75f|●●◉›"
        return (if (n > 0) "‹#5fd787|" + "●".repeat(n) + "›" else "") + "○".repeat(3 - n)
    }

    fun lignesMaitrise(jeu: Jeu): String = listOf("🏅 " + t("apr.maitrise.titre_ecran"),
        "  " + cmds().take(10).joinToString("   ") { "$it ${ronds(jeu, it)}" },
        "  " + cmds().drop(10).joinToString("   ") { "$it ${ronds(jeu, it)}" },
        "  " + t("apr.maitrise.legende", "n" to o("maitrise").optInt("reussites", 5))).joinToString("\n")

    // ================================================================ 24. les révisions
    fun noterVu(jeu: Jeu, c: String, now: Double): String? {
        if (c !in cmds()) return null
        val a = a(jeu)
        val jour = jourDe(now)
        val vus = a.getJSONObject("vus")
        val v = vus.optJSONArray(c)
        val r = a.getJSONObject("rev")
        if (r.optString("jour") == jour && r.optString("cmd") == c && !r.optBoolean("fait")) {
            r.put("fait", true)
            val etape = (v?.optInt(1) ?: 0) + 1
            vus.put(c, JSONArray().put(jour).put(etape))
            val xp = o("revision").optInt("xp", 4)
            jeu.ajouterXp(xp)
            val msg = "🍃 " + t("apr.rev.fait", "xp" to xp, "n" to intervalle(etape))
            jeu.log(msg)
            return msg
        }
        vus.put(c, JSONArray().put(jour).put(v?.optInt(1) ?: 0))
        return null
    }

    fun inviterRevision(jeu: Jeu, now: Double) {
        val a = a(jeu)
        val jour = jourDe(now)
        if (a.getJSONObject("rev").optString("jour") == jour) return
        val c = revisionDue(a.getJSONObject("vus"), jour) ?: return
        if (Histoire.enPleineEtape(jeu)) return
        a.put("rev", JSONObject().put("jour", jour).put("cmd", c).put("fait", false))
        jeu.dire(t("apr.rev.invite", "cmd" to c, "xp" to o("revision").optInt("xp", 4)), 14)
    }

    fun imageCourte(c: String) = t("lex.$c.i", "opt" to "ls -a").substringBefore(" (")

    fun lignesSouvenirs(jeu: Jeu): String {
        val vus = a(jeu).getJSONObject("vus")
        val jour = jourDe(maintenant())
        val out = mutableListOf("🍃 " + t("apr.rev.titre") + "  " + t("apr.rev.sous_titre"))
        val liste = vus.keys().asSequence().filter { it in cmds() }.map { c ->
            val v = vus.getJSONArray(c); Triple(joursEntre(v.getString(0), jour) - intervalle(v.optInt(1)), c, v)
        }.sortedByDescending { it.first }.toList()
        if (liste.isEmpty()) out.add("  " + t("apr.rev.rien"))
        for ((retard, c, v) in liste.take(8)) {
            val n = joursEntre(v.getString(0), jour)
            val quand = if (n <= 0) t("apr.rev.aujourdhui") else t("apr.rev.il_y_a", "n" to n)
            val etat = if (retard >= 0) t("apr.rev.a_rafraichir") else t("apr.rev.prochain", "n" to maxOf(1, -retard))
            out.add("  🍂 `$c`  $quand · ${imageCourte(c)} · $etat")
        }
        out.add("  " + t("apr.rev.pied"))
        return out.joinToString("\n")
    }

    // ================================================================ 29. la commande du jour
    fun missionDuJour(jeu: Jeu, now: Double = maintenant()): Pair<String, String> {
        val jour = jourDe(now)
        return jour to commandeDuJour(jour, jeu.vus)
    }

    fun verifierJour(jeu: Jeu, ligne: String, code: Int?, now: Double): String? {
        if (code != null && code != 0) return null
        val a = a(jeu)
        val (jour, c) = missionDuJour(jeu, now)
        val tampons = a.getJSONArray("tampons")
        if (jour in lst(tampons)) return null
        val motif = o("jour").getJSONObject("missions").optString(c).ifEmpty { return null }
        if (!Regex(motif).containsMatchIn(ligne.trim())) return null
        ajouter(tampons, jour, 62)
        val xp = o("jour").optInt("xp", 8)
        jeu.ajouterXp(xp)
        val msg = "☀ " + t("apr.jour.fait", "cmd" to c, "xp" to xp)
        jeu.log(msg)
        jeu.animer("content")
        return msg
    }

    fun ecranJour(jeu: Jeu): String {
        val (jour, c) = missionDuJour(jeu)
        val ex = o("jour").getJSONObject("exemples").getString(c)
        val fait = jour in lst(a(jeu).getJSONArray("tampons"))
        val d = java.time.LocalDate.parse(jour)
        val out = mutableListOf("☀ " + t("apr.jour.titre", "date" to "%02d/%02d".format(d.dayOfMonth, d.monthValue)),
            "  " + t("apr.jour.mission", "cmd" to "`$ex`"), "  " + t("apr.jour.regle"),
            "  " + if (fait) "✓ " + t("apr.jour.deja") else t("apr.jour.recompense", "xp" to o("jour").optInt("xp", 8)), "")
        out.addAll(calendrier(lst(a(jeu).getJSONArray("tampons")).toSet(), d))
        return out.joinToString("\n")
    }

    /** Le mois en cours : ☀ les jours tamponnés (aucun total de « jours de suite »). */
    fun calendrier(tampons: Set<String>, d: java.time.LocalDate): List<String> {
        val out = mutableListOf(t("apr.jour.tampons", "mois" to t("apr.mois.${d.monthValue}"), "annee" to d.year))
        val premier = d.withDayOfMonth(1)
        var ligne = "   ".repeat(premier.dayOfWeek.value - 1)
        for (j in 1..d.lengthOfMonth()) {
            val k = "%04d-%02d-%02d".format(d.year, d.monthValue, j)
            ligne += if (k in tampons) " ☀ " else "%3d".format(j)
            if (premier.withDayOfMonth(j).dayOfWeek.value == 7) { out.add("  $ligne"); ligne = "" }
        }
        if (ligne.isNotEmpty()) out.add("  $ligne")
        return out
    }

    // ================================================================ 44. les énigmes de la semaine
    fun dossierEnigme(jeu: Jeu, sem: String) = File(jeu.terrain, "enigmes/semaine_" + sem.substringAfter("-W"))

    fun preparerEnigme(jeu: Jeu, sem: String): File {
        val (mod, mot, n) = enigme(sem, jeu.vus)
        val d = dossierEnigme(jeu, sem)
        if (!File(d, "lis-moi.txt").exists()) {
            d.mkdirs()
            ecrire(File(d, "lis-moi.txt"), t("apr.enigme.$mod.texte", "n" to n) + "\n")
            val noms = "abcdefg"
            when (mod) {
                "phare" -> { val vrai = (fnv("$sem:vrai") % n).toInt()
                    for (k in 0 until n) ecrire(File(d, "parchemin_${noms[k]}.txt"), (if (k == vrai) t("apr.enigme.phare.vrai", "mot" to mot) else t("apr.enigme.phare.faux")) + "\n") }
                "cache" -> { for (k in 0 until n) ecrire(File(d, "caillou_${k + 1}.txt"), t("apr.enigme.cache.caillou") + "\n")
                    ecrire(File(d, ".secret.txt"), t("apr.enigme.cache.secret", "mot" to mot) + "\n") }
                "profond" -> { var p = d
                    for (k in 0 until n) { p = File(p, "salle_${k + 1}"); p.mkdirs(); ecrire(File(p, "rien.txt"), t("apr.enigme.profond.rien") + "\n") }
                    ecrire(File(p, "coffre.txt"), t("apr.enigme.profond.coffre", "mot" to mot) + "\n") }
                "ordre" -> { val autres = lst(o("enigmes").getJSONArray("mots")).filter { it > mot }.take(n).ifEmpty { listOf("zebre") }
                    ecrire(File(d, "mots.txt"), (autres + mot).sortedBy { fnv(sem + it) }.joinToString("\n") + "\n") }
                "compte" -> for (k in 0 until n) ecrire(File(d, "cailloux/galet_${k + 1}.txt"), "·\n")
            }
        }
        val garder = o("enigmes").optInt("garder", 4)
        val base = File(jeu.terrain, "enigmes")
        if (base.isDirectory && !lien(base)) {
            val semaines = (0 until garder).map { semaine(maintenant() - 7 * 86400.0 * it).substringAfter("-W") }
            base.listFiles()?.filter { it.isDirectory && !lien(it) && it.name.startsWith("semaine_") && it.name.substring(8) !in semaines }
                ?.forEach { vider(jeu, it) }
        }
        return d
    }

    fun reponseEnigme(jeu: Jeu, sem: String): String {
        val (mod, mot, n) = enigme(sem, jeu.vus)
        return if (mod == "compte") "$n" else mot
    }

    private fun normal(s: String) = Normalizer.normalize(s, Normalizer.Form.NFKD).replace(Regex("\\p{M}"), "").trim().lowercase()

    fun commandeEnigme(jeu: Jeu, reste: String): String {
        val a = a(jeu)
        val sem = semaine()
        val (mod, _, n) = enigme(sem, jeu.vus)
        val d = preparerEnigme(jeu, sem)
        val m = mots(reste)
        val faites = a.getJSONArray("enigmes")
        if (m.firstOrNull()?.lowercase() in setOf("reponse", "réponse", "answer") && m.size > 1) {
            val prop = normal(m.drop(1).joinToString(" "))
            for (k in 0 until o("enigmes").optInt("garder", 4)) {
                val s = semaine(maintenant() - 7 * 86400.0 * k)
                if (s !in lst(faites) && normal(reponseEnigme(jeu, s)) == prop) {
                    ajouter(faites, s, 20)
                    val xp = o("enigmes").optInt("xp", 15)
                    jeu.ajouterXp(xp)
                    jeu.animer("victoire")
                    val msg = "🎉 " + t("apr.enigme.bravo", "xp" to xp, "n" to s.substringAfter("-W"))
                    jeu.log(msg)
                    return msg
                }
            }
            return "🤔 " + t("apr.enigme.pas_encore")
        }
        if (m.firstOrNull()?.lowercase() in setOf("indice", "hint")) {
            val ind = a.getJSONObject("eindices")
            val k = minOf(2, ind.optInt(sem) + 1)
            ind.put(sem, k)
            return "💡 " + t("apr.enigme.$mod.indice$k", "n" to n)
        }
        val out = mutableListOf("🧩 " + t("apr.enigme.titre", "n" to sem.substringAfter("-W")))
        if (sem in lst(faites)) out.add("  ✓ " + t("apr.enigme.resolue"))
        out.add("  " + t("apr.enigme.$mod.texte", "n" to n))
        out.add("  " + t("apr.enigme.aller", "cmd" to "cd ${rel(jeu, d)}"))
        out.add("  " + t("apr.enigme.repondre", "cmd" to "enigme reponse …", "indice" to "enigme indice"))
        val passees = lst(faites).takeLast(4).map { it.substringAfter("-W") }
        if (passees.isNotEmpty()) out.add("  " + t("apr.enigme.passees", "liste" to passees.joinToString(" · ") { "✓ $it" }))
        return out.joinToString("\n")
    }

    // ================================================================ 23. les erreurs en mini-énigmes
    private fun arg(ligne: String): String? = mots(ligne).drop(1).firstOrNull { !it.startsWith("-") }

    /** (type, cible) d'une erreur connue, devinée en regardant le terrain (jamais en lisant le message), ou null. */
    fun causeErreur(jeu: Jeu, ligne: String, cwd: File?): Pair<String, String>? {
        if (cwd == null) return null
        val c = premier(ligne)
        val a1 = arg(ligne) ?: return null
        if (ligne.any { it in "|;&<>*?$`" }) return null
        val p = if (a1.startsWith("~/")) File(jeu.home, a1.substring(2)) else if (a1.startsWith("/")) File(a1) else File(cwd, a1)
        val m = mots(ligne)
        return when (c) {
            "cd" -> if (!p.exists()) "lieu" to a1 else null
            "mkdir" -> if ("-p" !in m && p.exists()) "existe" to a1 else null
            "rm" -> if (m.drop(1).none { it.startsWith("-") && 'r' in it.lowercase() } && p.isDirectory) "rm_dossier" to a1 else null
            "cat", "head", "less", "tail", "more" -> if (p.isDirectory) "cat_dossier" to a1 else if (!p.exists()) "introuvable" to a1 else null
            "cp", "mv" -> if (!p.exists()) "introuvable" to a1 else null
            else -> null
        }
    }

    fun resolu(e: JSONObject, ligne: String, code: Int?): Boolean {
        if (code != null && code != 0) return false
        val c = premier(ligne)
        val m = mots(ligne)
        val cible = e.optString("cible").trimEnd('/')
        return when (e.optString("type")) {
            "lieu" -> c == "cd" || c == "mkdir"
            "existe" -> (c == "mkdir" && e.optString("cible") !in m) || (c == "cd" && cible in m.map { it.trimEnd('/') })
            "rm_dossier" -> c == "rmdir" || (c == "rm" && m.drop(1).any { it.startsWith("-") && 'r' in it.lowercase() })
            "cat_dossier" -> c in setOf("ls", "cd") && cible in m.map { it.trimEnd('/') }
            "introuvable" -> c == e.optString("cmd") || c in setOf("ls", "find")
            else -> false
        }
    }

    fun verifierErreur(jeu: Jeu, ligne: String, code: Int?, cwd: File?, now: Double): String? {
        val a = a(jeu)
        val e = a.optJSONObject("erreur")
        if (e != null) {
            if (resolu(e, ligne, code) && (premier(ligne) !in setOf("ls", "find") || e.optString("type") != "introuvable" || e.optInt("indice") >= 2)) {
                a.remove("erreur")
                val xp = o("erreurs").optInt("xp", 3)
                jeu.ajouterXp(xp)
                jeu.animer("content")
                return "🧩 " + t("apr.err.resolue", "xp" to xp)
            }
            if (e.optInt("indice") < 2) {
                e.put("indice", 2)
                return "💡 " + t("apr.err.${e.optString("type")}.indice2", "cible" to e.optString("cible"))
            }
            return null
        }
        if (code == null || code == 0 || !dans(cwd, jeu.terrain) || dans(cwd, dossierBac(jeu))) return null
        if (now - a.optDouble("erreur_t", 0.0) < o("erreurs").optInt("delai", 600)) return null
        if (Histoire.enPleineEtape(jeu)) return null
        val (typ, cible) = causeErreur(jeu, ligne, cwd) ?: return null
        a.put("erreur", JSONObject().put("type", typ).put("cible", cible).put("indice", 1).put("cmd", premier(ligne)))
        a.put("erreur_t", now)
        return "🧩 " + t("apr.err.$typ", "cible" to cible) + "\n   💡 " + t("apr.err.$typ.indice1", "cible" to cible) +
            "\n   " + t("apr.err.passe", "cmd" to "passe")
    }

    fun passer(jeu: Jeu): String { a(jeu).remove("erreur"); return t("apr.err.passee") }

    // ================================================================ 21. le dictionnaire illustré
    fun ecranCarnet(jeu: Jeu, reste: String): String {
        val liste = cmds()
        val parPage = 6
        val pages = (liste.size + parPage - 1) / parPage
        val page = (mots(reste).firstOrNull()?.toIntOrNull() ?: 1).coerceIn(1, pages)
        val out = mutableListOf("📖 " + t("apr.carnet.titre", "nom" to jeu.nom, "page" to page, "pages" to pages), "")
        for (c in liste.drop((page - 1) * parPage).take(parPage)) {
            val vu = c in jeu.vus
            out.add((if (vu) "¤picto:$c¤ " else "¤picto:$c:gris¤ ") + "`$c` " + ronds(jeu, c) + "  " +
                if (vu) imageCourte(c) else t("apr.carnet.a_decouvrir"))
        }
        out.add("")
        out.add(t("apr.carnet.legende", "cmd" to "carnet ${page % pages + 1}", "explique" to "explique cd"))
        return out.joinToString("\n")
    }

    // ================================================================ 41 / 42. les mini-jeux et la course
    fun dossierJeux(jeu: Jeu) = File(jeu.terrain, "jeux")
    val LABY = linkedMapOf("grotte" to listOf("salle_humide", "salle_seche"), "grotte/salle_humide" to listOf("impasse"),
        "grotte/salle_seche" to listOf("tunnel", "eboulis"), "grotte/salle_seche/tunnel" to listOf("salle_du_tresor"))
    const val LABY_TRESOR = "grotte/salle_seche/tunnel/salle_du_tresor"
    val FACTEUR = linkedMapOf("lettre_1.txt" to "chateau", "lettre_2.txt" to "moulin", "lettre_3.txt" to "phare", "lettre_4.txt" to "chateau")

    fun preparerJeu(jeu: Jeu, nom: String): File {
        val d = File(dossierJeux(jeu), nom)
        vider(jeu, d)
        d.mkdirs()
        when (nom) {
            "labyrinthe" -> {
                for ((p, enfants) in LABY) for (e in enfants) File(d, "$p/$e").mkdirs()
                ecrire(File(d, "grotte/salle_humide/impasse/note.txt"), t("apr.jeux.laby.impasse") + "\n")
                ecrire(File(d, "$LABY_TRESOR/tresor.txt"), t("apr.jeux.laby.tresor") + "\n")
                ecrire(File(d, "grotte/salle_seche/eboulis/note.txt"), t("apr.jeux.laby.eboulis") + "\n")
            }
            "taupes" -> { for (k in 1..5) ecrire(File(d, "taupe_$k.txt"), "( o.o )\n"); for (k in 1..3) ecrire(File(d, "fleur_$k.txt"), "✿\n") }
            "peche" -> { for (k in 1..4) ecrire(File(d, ".poisson_$k"), "><(((º>\n"); ecrire(File(d, "algue.txt"), "~\n"); ecrire(File(d, "bouee.txt"), "o\n") }
            "facteur" -> { for ((f, m) in FACTEUR) ecrire(File(d, f), t("apr.jeux.facteur.pour", "maison" to m) + "\n")
                for (m in FACTEUR.values.toSet()) File(d, m).mkdirs() }
        }
        return d
    }

    private fun fichiers(d: File, debut: String) = d.listFiles()?.count { it.name.startsWith(debut) } ?: 0

    fun jeuGagne(jeu: Jeu, nom: String, cwd: File?, ligne: String): Boolean {
        val d = File(dossierJeux(jeu), nom)
        return when (nom) {
            "labyrinthe" -> dans(cwd, File(d, LABY_TRESOR)) || (Regex("^cat\\s+.*tresor\\.txt").containsMatchIn(ligne.trim()) && dans(cwd, d))
            "taupes" -> d.isDirectory && fichiers(d, "taupe_") == 0 && fichiers(d, "fleur_") == 3
            "facteur" -> d.isDirectory && fichiers(d, "lettre_") == 0 && FACTEUR.all { (f, m) -> File(d, "$m/$f").exists() }
            else -> false
        }
    }

    fun carteLabyrinthe(jeu: Jeu): String {
        val j = a(jeu).getJSONObject("jeux")
        val vues = lst(j.optJSONArray("vues")).toSet()
        val tous = listOf("grotte") + LABY.flatMap { (k, v) -> v.map { "$k/$it" } }
        return tous.joinToString("\n") { p ->
            val m = if (p == j.optString("ici")) "◆" else if (p in vues) "✓" else "·"
            "   " + "  ".repeat(p.count { it == '/' }) + "$m " + (if (m == "·") "???" else p.substringAfterLast('/'))
        }
    }

    fun commandeJeux(jeu: Jeu, reste: String): String {
        val a = a(jeu)
        val j = a.getJSONObject("jeux")
        val noms = lst(o("jeux").getJSONArray("ordre"))
        val m = mots(reste)
        val course = a.optBoolean("course")
        val recs = j.optJSONObject("records") ?: JSONObject()
        if (m.isEmpty()) {
            val out = mutableListOf("🎮 " + t("apr.jeux.titre"))
            noms.forEachIndexed { k, n ->
                out.add("  ${k + 1}. " + t("apr.jeux.$n.nom") + "  " + t("apr.jeux.$n.court") +
                    if (course && recs.has(n)) "  👻 %.1f s".format(recs.optDouble(n)) else "")
            }
            out.add("  " + t("apr.jeux.pied", "cmd" to "jeux labyrinthe", "course" to "course oui"))
            return out.joinToString("\n")
        }
        var x = m[0].lowercase()
        if (x in setOf("reponse", "réponse") && m.size > 1) {
            if (j.optString("actif") != "peche") return t("apr.jeux.pas_de_peche")
            return if (m[1] == "4") gagner(jeu, "peche") else "🎣 " + t("apr.jeux.peche.encore")
        }
        if (x == "carte") return "🗺 " + t("apr.jeux.laby.nom") + "\n" + carteLabyrinthe(jeu)
        x.toIntOrNull()?.let { if (it in 1..noms.size) x = noms[it - 1] }
        if (x !in noms) return t("apr.jeux.inconnu", "liste" to noms.joinToString(", "))
        val d = preparerJeu(jeu, x)
        j.put("actif", x).put("debut", maintenant()).put("vues", JSONArray()).remove("ici")
        val out = mutableListOf("🎮 " + t("apr.jeux.$x.nom"), "  " + t("apr.jeux.$x.regle", "cmd" to "jeux reponse 3"),
            "  " + t("apr.jeux.aller", "cmd" to "cd ${rel(jeu, d)}"))
        if (course) out.add("  ⏱ " + if (recs.has(x)) t("apr.course.fantome", "s" to "%.1f".format(recs.optDouble(x))) else t("apr.course.premier"))
        return out.joinToString("\n")
    }

    fun gagner(jeu: Jeu, nom: String, now: Double = maintenant()): String {
        val a = a(jeu)
        val j = a.getJSONObject("jeux")
        j.remove("actif")
        var premiere = "🎉 " + t("apr.jeux.gagne", "jeu" to t("apr.jeux.$nom.nom"))
        val jour = jourDe(now)
        val xj = j.optJSONArray("xp_jour")?.takeIf { it.optString(0) == jour } ?: JSONArray().put(jour).put(0)
        if (xj.optInt(1) < o("jeux").optInt("plafond", 3)) {
            xj.put(1, xj.optInt(1) + 1)
            val xp = o("jeux").optInt("xp", 5)
            jeu.ajouterXp(xp)
            premiere += " +$xp XP"
        }
        j.put("xp_jour", xj)
        val out = mutableListOf(premiere)
        if (a.optBoolean("course") && j.has("debut")) {
            val dt = now - j.optDouble("debut")
            val recs = j.optJSONObject("records") ?: JSONObject().also { j.put("records", it) }
            val ancien = if (recs.has(nom)) recs.optDouble(nom) else null
            out.add("⏱ " + t("apr.course.temps", "s" to "%.1f".format(dt)) + "   " + when {
                ancien != null && dt < ancien -> "👻 " + t("apr.course.bat", "s" to "%.1f".format(ancien))
                ancien != null -> "👻 " + t("apr.course.fantome", "s" to "%.1f".format(ancien))
                else -> t("apr.course.premier_temps")
            })
            recs.put(nom, if (ancien == null) dt else minOf(ancien, dt))
        }
        jeu.animer("victoire")
        jeu.log(premiere)
        Envies.plaisir(jeu, "jeu", "defi")
        return out.joinToString("\n")
    }

    fun verifierJeux(jeu: Jeu, ligne: String, cwd: File?, now: Double): String? {
        val j = a(jeu).getJSONObject("jeux")
        val nom = j.optString("actif").ifEmpty { return null }
        val d = File(dossierJeux(jeu), nom)
        if (nom == "labyrinthe" && cwd != null && dans(cwd, d)) {
            val r = cwd.canonicalFile.relativeTo(d.canonicalFile).path
            if (r.isNotEmpty() && r != ".") {
                j.put("ici", r)
                val vues = j.optJSONArray("vues") ?: JSONArray().also { j.put("vues", it) }
                if (r !in lst(vues)) vues.put(r)
            }
        }
        if (nom == "taupes" && d.isDirectory && fichiers(d, "fleur_") < 3) return "🌸 " + t("apr.jeux.taupes.fleur", "cmd" to "jeux taupes")
        return if (jeuGagne(jeu, nom, cwd, ligne)) gagner(jeu, nom, now) else null
    }

    fun commandeCourse(jeu: Jeu, reste: String): String {
        val a = a(jeu)
        val m = mots(reste).map { it.lowercase() }
        val oui = setOf("oui", "on", "yes")
        if (m.firstOrNull() in setOf("eclairs", "éclairs", "defis", "défis")) {
            if (m.size > 1) a.put("eclairs", m[1] in oui)
            return t("apr.course.eclairs." + if (eclairs(jeu)) "on" else "off", "cmd" to "course eclairs " + if (eclairs(jeu)) "non" else "oui")
        }
        if (m.isNotEmpty()) a.put("course", m[0] in oui)
        return listOf("⏱ " + t("apr.course." + if (a.optBoolean("course")) "on" else "off"), "  " + t("apr.course.regle"),
            "  " + t("apr.course.eclairs." + if (eclairs(jeu)) "on" else "off", "cmd" to "course eclairs " + if (eclairs(jeu)) "non" else "oui")).joinToString("\n")
    }

    fun eclairs(jeu: Jeu) = a(jeu).optBoolean("eclairs", true)
    fun course(jeu: Jeu) = a(jeu).optBoolean("course")

    // ================================================================ 49. la limite de temps douce
    fun endormie(jeu: Jeu, now: Double = maintenant()) = now < a(jeu).getJSONObject("temps").optDouble("dort", 0.0)

    /** [début, fin] du sommeil (la faim ne baisse pas pendant : Satiete.baisser). */
    fun sommeil(jeu: Jeu): Pair<Double, Double> {
        val tp = jeu.module("apprendre").optJSONObject("temps") ?: return 0.0 to 0.0
        return tp.optDouble("dort_debut", 0.0) to tp.optDouble("dort", 0.0)
    }

    fun reglerTemps(jeu: Jeu, args: List<String>): String {
        val tp = a(jeu).getJSONObject("temps")
        val x = args.firstOrNull()?.lowercase()
        if (x in setOf("non", "off", "aucune", "none", "0")) { tp.remove("limite"); tp.put("dort", 0.0); return t("apr.temps.enleve") }
        val m = x?.toIntOrNull() ?: return if (tp.has("limite")) t("apr.temps.actuel", "n" to tp.optInt("limite")) else t("apr.temps.aucune", "cmd" to "parent temps 45")
        val v = m.coerceIn(10, 600)
        tp.put("limite", v)
        return "✓ " + t("apr.temps.ok", "nom" to jeu.nom, "n" to v, "cmd" to "parent temps non")
    }

    /** « parent temps 45 » : la question à poser (avec la phrase d'un adulte), ou la réponse directe. */
    fun questionParent(args: List<String>): String? =
        if (args.firstOrNull()?.lowercase() in setOf("temps", "time") && args.size > 1) t("apr.parent.question", "n" to args[1]) + "\n" + t("apr.parent.confirmer") else null

    fun phraseAdulte(rep: String) = normal(rep) == normal(t("apr.parent.phrase"))

    fun verifierTemps(jeu: Jeu, now: Double, msgs: MutableList<Pair<String, Int>>) {
        val tp = a(jeu).getJSONObject("temps")
        ajouterTemps(tp, now, o("temps").optInt("trou", 300))
        val lim = if (tp.has("limite")) tp.optInt("limite") else null
        val e = etatTemps(tp.optDouble("s", 0.0), lim, o("temps").optInt("baille", 5), o("temps").optInt("pause", 60))
        val nom = jeu.nom
        if (e == "baille" && !tp.optBoolean("baille")) {
            tp.put("baille", true); jeu.animer("dort")
            val m = "💤 " + t("apr.temps.baille", "nom" to nom); jeu.dire(m, 12); msgs.add(m to VERT)
        } else if (e == "dort" && !endormie(jeu, now) && tp.optString("dort_jour") != tp.optString("jour")) {
            tp.put("dort_jour", tp.optString("jour")).put("dort_debut", now).put("dort", prochainReveil(now, o("temps").optInt("reveil", 7)))
            jeu.animer("dort")
            val m = "🌙 " + t("apr.temps.dort", "nom" to nom); jeu.dire(m, 16); msgs.add(m to VERT)
        } else if (e == "pause" && tp.optString("pause_dite") != tp.optString("jour")) {
            tp.put("pause_dite", tp.optString("jour"))
            val m = "☕ " + t("apr.temps.pause", "nom" to nom); jeu.dire(m, 12); msgs.add(m to VERT)
        }
    }

    // ================================================================ 45. le sentier des marmottes
    fun sentierOuvert(jeu: Jeu) = try { Sommet.mondesAuPalier(jeu, 3).isNotEmpty() } catch (e: Exception) { false }
    fun dossierSentier(jeu: Jeu) = File(jeu.terrain, "sommet/sentier")

    fun preparerSentier(jeu: Jeu): File {
        val d = dossierSentier(jeu)
        d.mkdirs()
        if (!File(d, "inscriptions.txt").exists()) {
            ecrire(File(d, "inscriptions.txt"), (1..5).joinToString("\n") { t("apr.sentier.inscription.$it") } + "\n")
            ecrire(File(d, "sommet.txt"), t("apr.sentier.sommet_txt") + "\n")
            ecrire(File(d, "panneau.txt"), t("apr.sentier.panneau") + "\n")
            for (n in listOf("gris", "rond", "plat")) ecrire(File(d, "eboulis/$n.caillou"), "◍\n")
            ecrire(File(d, "eboulis/touffe_d_herbe.txt"), "\"\n")
        }
        return d
    }

    private fun etapes() = o("sentier").getJSONArray("etapes").let { a -> (0 until a.length()).map { a.getJSONObject(it) } }

    fun commandeSentier(jeu: Jeu): String {
        if (!sentierOuvert(jeu)) return "🐾 " + t("apr.sentier.ferme")
        val d = preparerSentier(jeu)
        val faits = lst(a(jeu).getJSONArray("sentier"))
        val out = mutableListOf("🐾 " + t("apr.sentier.titre"), "  " + t("apr.sentier.regle"), "  " + t("apr.sentier.aller", "cmd" to "cd ${rel(jeu, d)}"))
        etapes().forEachIndexed { k, e ->
            out.add("  " + (if (e.getString("id") in faits) "✓" else "○") + " S${k + 1} " + t("apr.sentier." + e.getString("id")) + "  `" + e.getString("cmd") + "`")
        }
        out.add("  " + t("apr.sentier.pied"))
        return out.joinToString("\n")
    }

    fun verifierSentier(jeu: Jeu, ligne: String, code: Int?, cwd: File?): String? {
        if ((code != null && code != 0) || cwd == null || !dans(cwd, dossierSentier(jeu))) return null
        val faits = a(jeu).getJSONArray("sentier")
        val et = etapes()
        val e = et.firstOrNull { it.getString("id") !in lst(faits) } ?: return null
        var ok = e.optString("motif").isNotEmpty() && Regex(e.getString("motif")).containsMatchIn(ligne.trim())
        if (e.optString("fs").isNotEmpty()) ok = File(dossierSentier(jeu), e.getString("fs").trimEnd('/')).isDirectory
        if (!ok) return null
        faits.put(e.getString("id"))
        val xp = o("sentier").optInt("xp", 5)
        jeu.ajouterXp(xp)
        val k = et.indexOf(e) + 1
        var msg = "🐾 " + t("apr.sentier.franchi", "n" to k, "xp" to xp)
        if (k == et.size) {
            val r = Recompenses.exploit(jeu, o("sentier").optString("exploit", "sommet.sentier"))
            msg += "\n🏔 " + t("apr.sentier.fin", "nom" to jeu.nom) + (r?.let { "\n$it" } ?: "")
            jeu.animer("victoire")
        } else msg += "  " + t("apr.sentier.suivant", "cmd" to et[k].getString("cmd"))
        jeu.log(msg.substringBefore("\n"))
        return msg
    }

    // ================================================================ 30. l'examen-aventure et le diplôme
    private fun examens() = o("examens")
    private fun sallesDe(chap: String) = lst(examens().getJSONObject("chapitres").optJSONArray(chap))

    fun examenDispo(jeu: Jeu): String? {
        val dipl = lst(a(jeu).getJSONArray("diplomes"))
        return examens().getJSONObject("chapitres").keys().asSequence().firstOrNull { Histoire.fini(jeu, it) && it !in dipl }
    }

    fun dossierExamen(jeu: Jeu) = File(jeu.terrain, "examen")

    fun preparerSalle(jeu: Jeu, chap: String, k: Int): File {
        val typ = sallesDe(chap)[k]
        val d = File(dossierExamen(jeu), "salle_${k + 1}")
        vider(jeu, d)
        d.mkdirs()
        ecrire(File(d, "plan.txt"), t("apr.exam.plan", "n" to k + 1, "mission" to t("apr.exam.salle.$typ")) + "\n")
        when (typ) {
            "cd" -> File(d, "passage").mkdirs()
            "ls_a" -> ecrire(File(d, ".cle_cachee"), "🗝\n")
            "cat" -> ecrire(File(d, "parchemin.txt"), t("apr.exam.parchemin") + "\n")
            "mv" -> { ecrire(File(d, "ours.txt"), "ʕ•ᴥ•ʔ\n"); File(d, "coffre").mkdirs() }
            "cp" -> ecrire(File(d, "carte.txt"), "🗺\n")
            "rm" -> ecrire(File(d, "caillou.txt"), "◍\n")
            "chmod" -> ecrire(File(d, "secret.txt"), "…\n")
            "head", "grep", "wc", "sort" -> ecrire(File(d, "livre.txt"), (1..6).joinToString("\n") { t("apr.exam.livre.$it") } + "\n")
            "find" -> ecrire(File(d, "a/b/c/petite.cle"), "🗝\n")
            "tree" -> File(d, "foret/arbre/branche").mkdirs()
        }
        return d
    }

    fun salleReussie(typ: String, ligne: String, code: Int?, d: File): Boolean {
        if (code != null && code != 0) return false
        val s = examens().getJSONObject("salles").getJSONObject(typ)
        var ok = s.optString("motif").isEmpty() || Regex(s.getString("motif")).containsMatchIn(ligne.trim())
        if (s.optString("fs").isNotEmpty()) {
            val p = File(d, s.getString("fs").trimEnd('/'))
            ok = if (s.getString("fs").endsWith("/")) p.isDirectory else p.exists()
        }
        if (s.optString("absent").isNotEmpty()) ok = ok && !File(d, s.getString("absent")).exists()
        return ok
    }

    fun commandeExamen(jeu: Jeu, reste: String): String {
        val a = a(jeu)
        val ex = a.getJSONObject("examen")
        val dipl = a.getJSONArray("diplomes")
        if (mots(reste).firstOrNull()?.lowercase() in setOf("diplome", "diplôme") && dipl.length() > 0) {
            a.put("montrer_diplome", dipl.getString(dipl.length() - 1))
            return "🎓 " + t("apr.exam.diplome_ecrit", "chemin" to "~/" + jeu.terrain.name + "/diplome_${dipl.getString(dipl.length() - 1)}.png")
        }
        if (ex.optString("chap").isEmpty()) {
            val c = examenDispo(jeu) ?: return "📜 " + t("apr.exam.aucun")
            ex.put("chap", c).put("salle", 0).put("essais", 0).put("debut", maintenant())
            preparerSalle(jeu, c, 0)
        }
        val c = ex.getString("chap")
        val k = ex.optInt("salle")
        val typ = sallesDe(c)[k]
        val d = File(dossierExamen(jeu), "salle_${k + 1}")
        if (!d.exists()) preparerSalle(jeu, c, k)
        return listOf("📜 " + t("apr.exam.titre", "chapitre" to Histoire.nomChapitre(c), "n" to k + 1), "  " + t("apr.exam.salle.$typ"),
            "  " + t("apr.exam.aller", "cmd" to "cd ${rel(jeu, d)}"), "  " + t("apr.exam.regle")).joinToString("\n")
    }

    fun verifierExamen(jeu: Jeu, ligne: String, code: Int?, cwd: File?, now: Double): String? {
        val a = a(jeu)
        val ex = a.getJSONObject("examen")
        val c = ex.optString("chap").ifEmpty { return null }
        if (premier(ligne) in setOf("tg", "examen")) return null
        val k = ex.optInt("salle")
        val salles = sallesDe(c)
        val typ = salles[k]
        val d = File(dossierExamen(jeu), "salle_${k + 1}")
        if (cwd != null && !dans(cwd, d)) return null
        val s = examens().getJSONObject("salles").getJSONObject(typ)
        val ok = if (s.optString("cwd").isNotEmpty()) cwd != null && dans(cwd, File(d, s.getString("cwd"))) && (code == null || code == 0)
            else salleReussie(typ, ligne, code, d)
        if (!ok) {
            ex.put("essais", ex.optInt("essais") + 1)
            return if (ex.optInt("essais") == examens().optInt("essais", 2)) "🧭 " + t("apr.exam.guide", "cmd" to s.getString("cmd")) else null
        }
        ex.put("essais", 0)
        if (k + 1 < salles.size) {
            ex.put("salle", k + 1)
            preparerSalle(jeu, c, k + 1)
            return "✓ " + t("apr.exam.franchie", "n" to k + 1, "cmd" to "cd ../salle_${k + 2}") + "\n   " + t("apr.exam.salle." + salles[k + 1])
        }
        a.getJSONArray("diplomes").put(c)
        val debut = ex.optDouble("debut", 0.0)
        a.put("examen", JSONObject())
        val xp = examens().optInt("xp", 20)
        jeu.ajouterXp(xp)
        jeu.animer("victoire")
        a.put("montrer_diplome", c)
        val chemin = try { ApprendreDessin.ecrireDiplome(jeu, c, now) } catch (e: Exception) { null }
        var msg = "🎓 " + t("apr.exam.fini", "xp" to xp) + "\n   " + t("apr.exam.diplome_ecrit", "chemin" to (chemin?.let { rel(jeu, it) } ?: "~/" + jeu.terrain.name + "/diplome_$c.png"))
        if (course(jeu) && debut > 0) msg += "\n   ⏱ " + t("apr.course.temps", "s" to "%.0f".format(now - debut))
        jeu.log(msg.substringBefore("\n"))
        return msg
    }

    /** Les textes du diplôme (communs au PC) : titre, lieu, « décerné à », nom de la créature, ligne vide, mois, commandes. */
    fun contenuDiplome(jeu: Jeu, chap: String, now: Double = maintenant()): Map<String, String> {
        val d = java.util.Calendar.getInstance().apply { timeInMillis = (now * 1000).toLong() }
        val salles = examens().getJSONObject("salles")
        val cm = sallesDe(chap).map { salles.getJSONObject(it).getString("cmd").substringBefore(" ") }.distinct()
        return mapOf("titre" to t("apr.diplome.titre"), "lieu" to Histoire.nomChapitre(chap), "decerne" to t("apr.diplome.decerne"),
            "nom" to jeu.nom, "ligne" to t("apr.diplome.ligne"), "mois" to t("apr.mois.${d.get(java.util.Calendar.MONTH) + 1}") + " ${d.get(java.util.Calendar.YEAR)}",
            "cmds" to cm.joinToString("  "))
    }

    /** Le diplôme à montrer (deux boutons : enregistrer, imprimer), une fois. */
    fun diplomeAMontrer(jeu: Jeu): String? {
        val a = a(jeu)
        val c = a.optString("montrer_diplome").ifEmpty { return null }
        a.remove("montrer_diplome")
        return c
    }

    // ================================================================ le tour de jeu (Tour.apresCommande)
    private val AIDES = setOf("aide", "help", "indice", "hint")

    fun tour(jeu: Jeu, ligne: String, colle: Boolean, cwd: File?, code: Int?, now: Double = maintenant()): List<Pair<String, Int>> {
        val msgs = mutableListOf<Pair<String, Int>>()
        if (ligne.isBlank()) return msgs
        val a = a(jeu)
        val c = premier(ligne)
        val ok = code == null || code == 0
        if (!colle) {
            for (m in listOf(noterUsage(jeu, ligne, code, a.optBoolean("aide_avant")),
                    if (ok) noterVu(jeu, c, now) else null,
                    verifierJour(jeu, ligne, code, now),
                    if (c != "tg") verifierErreur(jeu, ligne, code, cwd, now) else null,
                    verifierJeux(jeu, ligne, cwd, now),
                    verifierSentier(jeu, ligne, code, cwd),
                    verifierExamen(jeu, ligne, code, cwd, now))) {
                if (m != null) { msgs.add(m to VERT); jeu.dire(m.substringBefore("\n"), 10) }
            }
        }
        val mm = mots(ligne)
        a.put("aide_avant", colle || c in AIDES || (c == "tg" && mm.size > 1 && mm[1].lowercase() in AIDES))
        verifierTemps(jeu, now, msgs)
        inviterRevision(jeu, now)
        return msgs
    }

    // ================================================================ les commandes de l'appli (Commandes.executer)
    /** La réponse à une commande d'« apprendre en jouant » (sans « tg »), ou null si ce n'en est pas une. */
    fun commande(jeu: Jeu, ligne: String): String? {
        var m = mots(ligne)
        if (m.firstOrNull()?.lowercase() == "tg") m = m.drop(1)
        val cmd = m.firstOrNull()?.lowercase() ?: return null
        val reste = m.drop(1).joinToString(" ")
        val second = m.getOrNull(1)?.lowercase()
        val r = when {
            cmd == "collection" && second in setOf("rares", "rare") -> ecranRares(jeu, m.drop(2).joinToString(" "))
            cmd == "sommet" && second in setOf("sentier", "marmottes") -> commandeSentier(jeu)
            cmd !in COMMANDES -> return null
            !Intro.eclos(jeu) -> t("deb.pas_encore", "cmd" to cmd)
            cmd in setOf("bac-a-sable", "bac_a_sable") -> commandeBac(jeu, reste)
            cmd in setOf("souvenirs", "revisions", "révisions") -> lignesSouvenirs(jeu)
            cmd == "jour" -> ecranJour(jeu)
            cmd in setOf("enigme", "énigme") -> commandeEnigme(jeu, reste)
            cmd == "passe" -> passer(jeu)
            cmd == "carnet" -> ecranCarnet(jeu, reste)
            cmd == "jeux" -> commandeJeux(jeu, reste)
            cmd == "course" -> commandeCourse(jeu, reste)
            cmd == "examen" -> commandeExamen(jeu, reste)
            else -> lignesMaitrise(jeu)
        }
        return r
    }
}
