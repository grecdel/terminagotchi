package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar

/**
 * Le thème « créature » (maquettes validées le 3 novembre) : les mêmes règles que pc/tg/creature.py.
 *  11. humeurs du moment (curieux, fier, câlin, gourmand, enjoué, rêveur, surpris, bavard, en fête) ;
 *  12. goûts : plat préféré (attireePar), aliment préféré (type de l'espèce), goût secret — comptent double pour la faim ;
 *  16. album des stades (date, niveau, souvenir) et des fêtes ;
 *  17. éclosiversaire : 1, 2, 3, 6 mois puis chaque année, fêté à la visite suivante si on a manqué le jour ;
 *  18. envie mystère : une commande décrite sans être donnée, `indice` (3 au plus), « Plus tard » ;
 *  84. moment d'évolution (phases, passable au bout de 2 s, son("evolution") si le moteur de sons existe) ;
 *  85. promenade dans la carte de la créature (BureauVie), réglage « rester sur place ».
 * Les calculs purs ont des vecteurs communs avec Python (donnees/creature/vecteurs.json, tests/jvm/Creature.kt).
 * Sauvegarde : jeu.module("creature"), les mêmes clés que state["creature"] sur PC (secondes).
 */
object Creature {
    private var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null
    /** l'horloge en secondes (remplaçable par un test) */
    var maintenant: () -> Double = { System.currentTimeMillis() / 1000.0 }
    /** les messages à écrire dans le terminal sous la commande (Tour les reprend) */
    val aEcrire = mutableListOf<String>()

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("creature.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    /** (tests) les données lues d'un texte */
    fun chargerTexte(texte: String) { d = JSONObject(texte); chargeur = { texte } }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(a: JSONArray?): List<String> = a?.let { x -> (0 until x.length()).map { x.get(it).toString() } } ?: emptyList()
    private fun entiers(a: JSONArray?): List<Int> = a?.let { x -> (0 until x.length()).map { x.getInt(it) } } ?: emptyList()
    fun humeurs(): JSONObject = donnees().optJSONObject("humeurs") ?: JSONObject()
    fun infoHumeur(h: String): JSONObject = humeurs().optJSONObject(h) ?: JSONObject()
    fun devinettes(): List<JSONObject> = donnees().optJSONArray("devinettes")?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun parId(id: String?): JSONObject? = devinettes().firstOrNull { it.optString("id") == id }

    // ================================================================ calculs purs (les mêmes en Python)
    fun choisirHumeur(evts: Set<String>): String? = liste(donnees().optJSONArray("priorite")).firstOrNull { it in evts }

    fun humeurActive(h: JSONObject?, now: Double): String? {
        val k = h?.optString("h") ?: return null
        if (!humeurs().has(k)) return null
        val duree = if (k == "fete") donnees().optDouble("fete_duree", 600.0) else donnees().optDouble("humeur_duree", 180.0)
        val dt = now - h.optDouble("t", 0.0)
        return if (dt >= 0 && dt < duree) k else null
    }

    fun variete(derniers: List<String>, n: Int = donnees().optInt("variete", 4)): Boolean =
        derniers.size >= n && derniers.takeLast(n).toSet().size == n

    fun pauseCalin(dernier: Double, now: Double): Boolean = dernier > 0 && now - dernier >= donnees().optDouble("pause_calin", 1800.0)

    fun aliment(type: String?): String? = type?.let { donnees().optJSONObject("aliments")?.optString(it)?.ifEmpty { null } }

    fun goutSecret(graine: Long, plat: String?): String {
        val s = liste(donnees().optJSONArray("secrets")).filter { it != plat }
        return s[(graine % s.size).toInt()]
    }

    fun joursDuMois(a: Int, m: Int): Int = when (m) {
        2 -> if (a % 4 == 0 && (a % 100 != 0 || a % 400 == 0)) 29 else 28
        4, 6, 9, 11 -> 30
        else -> 31
    }

    fun ajouterMois(a: Int, m: Int, j: Int, n: Int): Triple<Int, Int, Int> {
        val k = m - 1 + n
        val a2 = a + Math.floorDiv(k, 12); val m2 = Math.floorMod(k, 12) + 1
        return Triple(a2, m2, minOf(j, joursDuMois(a2, m2)))
    }

    fun dateLocale(ts: Double): Triple<Int, Int, Int> {
        val c = Calendar.getInstance()
        c.timeInMillis = Math.round(ts * 1000)
        return Triple(c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH))
    }

    private fun avant(a: Triple<Int, Int, Int>, b: Triple<Int, Int, Int>): Boolean =
        compareValuesBy(a, b, { it.first }, { it.second }, { it.third }) < 0

    fun jalons(jusqua: Int = 1200): List<Int> = entiers(donnees().optJSONArray("fetes_mois")) + (12..jusqua step 12)

    /** [mois, en retard] de la fête à faire maintenant, ou null. */
    fun feteDue(eclosion: Double?, now: Double, faites: Collection<Int>): Pair<Int, Boolean>? {
        if (eclosion == null || eclosion <= 0 || now < eclosion) return null
        val e = dateLocale(eclosion)
        val auj = dateLocale(now)
        var due: Pair<Int, Triple<Int, Int, Int>>? = null
        for (m in jalons()) {
            val dd = ajouterMois(e.first, e.second, e.third, m)
            if (avant(auj, dd)) break
            due = m to dd
        }
        val x = due ?: return null
        if (x.first in faites) return null
        return x.first to avant(x.second, auj)
    }

    fun eligibles(vus: Collection<String>, win: Boolean = false): List<String> =
        devinettes().filter { dv -> liste(dv.optJSONArray("vu")).any { it in vus } && (!win || !dv.isNull("win")) }.map { it.getString("id") }

    fun peutProposer(chap1: Boolean, nJour: Int, active: Boolean, depuis: Int, moment: Boolean): Boolean =
        chap1 && !active && nJour < donnees().optInt("envies_par_jour", 2) && depuis >= donnees().optInt("envie_apres", 15) && !moment

    fun choisirDevinette(elig: List<String>, n: Long, derniere: String?): String? {
        if (elig.isEmpty()) return null
        val c = elig.filter { it != derniere }.ifEmpty { elig }
        return c[Math.floorMod(n, c.size.toLong()).toInt()]
    }

    fun trouve(id: String?, ligne: String?): Boolean {
        val dv = parId(id) ?: return false
        return Regex(dv.getString("re"), RegexOption.IGNORE_CASE).containsMatchIn(ligne ?: "")
    }

    fun phaseEvolution(t: Double): Pair<String, Double> {
        val e = donnees().optJSONObject("evolution") ?: JSONObject()
        var debut = 0.0
        for ((nom, k) in listOf("appel" to "appel", "transformation" to "transformation", "eclat" to "eclat")) {
            val duree = e.optDouble(k, 1.0)
            if (t < debut + duree) return nom to arrondi(maxOf(0.0, t - debut) / duree)
            debut += duree
        }
        return "fete" to arrondi(minOf(1.0, (t - debut) / e.optDouble("carte", 0.4)))
    }

    private fun arrondi(x: Double) = Math.round(x * 10000) / 10000.0

    fun peutPasser(t: Double): Boolean = t >= (donnees().optJSONObject("evolution")?.optDouble("passer", 2.0) ?: 2.0)

    fun pagesMigration(stades: List<String>, iActuel: Int): JSONObject =
        JSONObject().also { o -> stades.forEachIndexed { k, s -> if (k <= iActuel) o.put(s, JSONObject().put("avant", true)) } }

    fun numeroJour(ts: Double): Long {
        val (a, m, j) = dateLocale(ts)
        // le numéro du jour (comme date.toordinal() en Python : 1 = le 1er janvier de l'an 1)
        val y = a - 1
        var n = y * 365L + y / 4 - y / 100 + y / 400
        for (mm in 1 until m) n += joursDuMois(a, mm)
        return n + j
    }

    // ================================================================ l'état
    fun stadesCompagnon(): List<String> = liste(donnees().optJSONArray("album_stades_compagnon"))

    /** Le stade du compagnon en nom du bestiaire (« bebe », « ado », « adulte »), ou null (l'œuf). */
    fun stadeCompagnon(jeu: Jeu): String? = if (jeu.stade >= 1) Sprites.STADE_ESPECE[jeu.stade] else null

    fun c(jeu: Jeu): JSONObject {
        val c = jeu.module("creature")
        if (!c.has("derniers")) c.put("derniers", JSONArray())
        if (!c.has("fetes")) c.put("fetes", JSONArray())
        if (!c.has("album")) c.put("album", JSONObject())
        if (!c.has("pages")) c.put("pages", JSONArray())
        if (!c.has("envies_jour")) c.put("envies_jour", JSONArray(listOf(0, 0)))
        if (!c.has("graine")) c.put("graine", kotlin.random.Random.nextInt(1 shl 30).toLong())
        val s = stadeCompagnon(jeu)
        if (s != null && c.optDouble("eclosion", 0.0) <= 0) c.put("eclosion", maintenant())   // une créature déjà éclose
        if (s != null && c.getJSONObject("album").length() == 0) c.put("album", pagesMigration(stadesCompagnon(), stadesCompagnon().indexOf(s)))
        return c
    }

    fun espece(jeu: Jeu): Bestiaire.Espece? = jeu.especeCompagnon?.let { Bestiaire.espece(it) }
    fun typeEspece(jeu: Jeu): String? = espece(jeu)?.let { Guide.typeDe(it) }
    fun plat(jeu: Jeu): String? = espece(jeu)?.attireePar?.ifEmpty { null }
    fun secret(jeu: Jeu): String? = if (espece(jeu) != null) goutSecret(c(jeu).optLong("graine"), plat(jeu)) else null

    /** Un petit son (synthèse en code) si le moteur de sons existe (thème « sons », un autre chantier) ; sinon rien. */
    /** Un petit son par le moteur de sons du jeu (Sons.kt : il respecte les réglages, silencieux par défaut). */
    fun son(nom: String, ctx: android.content.Context? = null): Boolean = try { Sons.son(nom, ctx) } catch (e: Throwable) { false }

    fun humeur(jeu: Jeu, now: Double = maintenant()): String? =
        if (!jeu.extra.has("creature")) null else humeurActive(jeu.module("creature").optJSONObject("humeur"), now)

    fun couleur(h: String): Int = (0xFF000000.toInt()) or Integer.parseInt(infoHumeur(h).optString("couleur", "#3ddc84").substring(1), 16)

    private fun direSiLibre(jeu: Jeu, texte: String, s: Int = 8) { if (jeu.bulleActive().isEmpty()) jeu.dire(texte, s) }

    fun poserHumeur(jeu: Jeu, h: String, now: Double = maintenant(), dire: Boolean = true) {
        val c = c(jeu)
        val avant = humeurActive(c.optJSONObject("humeur"), now)
        c.put("humeur", JSONObject().put("h", h).put("t", now))
        val a = infoHumeur(h).optString("anim", "")
        if (a.isNotEmpty() && a != "null") jeu.animer(a)
        if (dire && h != avant && h != "gourmand" && h != "fete") direSiLibre(jeu, Langue.auHasard("cr.humeur.$h.dit", "nom" to jeu.nom))
    }

    // ---------------------------------------------------------------- 12. les repas (Jeu.manger)
    fun apresRepas(jeu: Jeu, cmd: String, gain: Double): String {
        if (espece(jeu) == null || stadeCompagnon(jeu) == null) return ""
        val c = c(jeu)
        val p = plat(jeu); val s = secret(jeu)
        if ((cmd != p && cmd != s) || gain <= 0) return ""
        jeu.faim = minOf(100.0, jeu.faim + gain)
        c.put("_gourmand", true)
        if (cmd == p) {
            direSiLibre(jeu, t("cr.plat.dit", "cmd" to cmd))
            return t("cr.plat.journal")
        }
        if (!c.optBoolean("secret")) {
            c.put("secret", true)
            aEcrire.add(t("cr.secret.trouve", "cmd" to cmd, "nom" to jeu.nom))
            direSiLibre(jeu, t("cr.secret.dit", "cmd" to cmd))
        }
        return t("cr.secret.journal")
    }

    // ---------------------------------------------------------------- 16, 84. les stades (Jeu.ajouterXp)
    fun stadeChange(jeu: Jeu, ancien: Int, nouveau: Int) {
        val c = c(jeu)
        val now = maintenant()
        val v = Sprites.STADE_ESPECE[nouveau] ?: return
        if (ancien == 0) c.put("eclosion", now)
        val souv = if (v == "bebe" && jeu.vus.isNotEmpty()) JSONArray(listOf("cr.souv.premiere", jeu.vus.first()))
            else JSONArray(listOf("cr.souv.gouts", jeu.vus.size))
        c.getJSONObject("album").put(v, JSONObject().put("t", now).put("niv", jeu.niveau).put("s", souv))
        if (ancien >= 1) c.put("evolution", JSONObject().put("de", Sprites.STADE_ESPECE[ancien]).put("vers", v).put("t", now))
    }

    /** Une bestiole de l'équipe change de stade (Equipe.gagner) : la date dans son album. */
    fun equipeEvolue(ind: JSONObject) {
        val a = ind.optJSONObject("album") ?: JSONObject().also { ind.put("album", it) }
        a.put(ind.optString("stade", "bebe").ifEmpty { "bebe" }, maintenant())
    }

    // ---------------------------------------------------------------- le tour de jeu (Tour.apresCommande)
    private val SLEEP = Regex("^\\s*(sleep|start-sleep)\\s+", RegexOption.IGNORE_CASE)
    private val BAVARD = Regex("^\\s*(?:tg\\s+)?(explique|man|help|get-help|cherche)\\b|\\s--help\\b", RegexOption.IGNORE_CASE)
    private val CACHE = Regex("^\\s*(ls\\s+-\\w*a|dir\\s+-force|gci\\s+-force|get-childitem\\b.*-force)", RegexOption.IGNORE_CASE)

    class Avant(val seen: Int, val lecon: Int)

    fun avant(jeu: Jeu): Avant = Avant(jeu.vus.size, try { Envies.compteurs(jeu)["lecon"] ?: 0 } catch (e: Exception) { 0 })

    private fun chap1(jeu: Jeu) = try { Histoire.fini(jeu, "reveil") } catch (e: Exception) { false }

    fun apresCommande(jeu: Jeu, ligne: String?, ignoree: Boolean, av: Avant?) {
        if (!jeu.existe || stadeCompagnon(jeu) == null) return
        val l = ligne ?: return
        if (ignoree || Regles.estColle(l) || Regles.premierMot(l).isEmpty()) return
        val c = c(jeu)
        val now = maintenant()
        val evts = HashSet<String>()
        val cpt = try { Envies.compteurs(jeu) } catch (e: Exception) { emptyMap() }
        if (av != null && jeu.vus.size > av.seen) evts.add("curieux")
        if (av != null && (cpt["lecon"] ?: 0) > av.lecon) evts.add("fier")
        if (pauseCalin(c.optDouble("derniere_t", 0.0), now)) evts.add("calin")
        if (c.optBoolean("_gourmand")) { c.remove("_gourmand"); evts.add("gourmand") }
        val derniers = (liste(c.optJSONArray("derniers")) + Regles.premierMot(l)).takeLast(8)
        c.put("derniers", JSONArray(derniers))
        if (variete(derniers)) evts.add("enjoue")
        if (SLEEP.containsMatchIn(l)) evts.add("reveur")
        if (CACHE.containsMatchIn(l) && Maison.rel(jeu, Maison.ici(jeu)) != null) evts.add("surpris")
        if (BAVARD.containsMatchIn(l)) evts.add("bavard")
        val jour = numeroJour(now)
        val faites = entiers(c.optJSONArray("fetes"))
        feteDue(c.optDouble("eclosion", 0.0), now, faites)?.let { (m, retard) -> feter(jeu, m, retard, now); evts.add("fete") }
        var h = choisirHumeur(evts)
        if (h == null && Envies.soir() && c.optLong("soir_jour") != jour) { c.put("soir_jour", jour); h = "reveur" }   // le soir, s'il ne se passe rien d'autre
        if (h != null && h != "fete") poserHumeur(jeu, h, now)
        c.put("derniere_t", now)
        envieTour(jeu, c, l, now)
    }

    fun duree(m: Int): String = when {
        m < 12 -> t("cr.duree.mois", "n" to m)
        m == 12 -> t("cr.duree.an", "n" to 1)
        else -> t("cr.duree.ans", "n" to m / 12)
    }

    fun dateTexte(ts: Double): String { val (a, m, j) = dateLocale(ts); return t("cr.date", "j" to j, "m" to m, "a" to a) }

    fun feter(jeu: Jeu, m: Int, retard: Boolean, now: Double = maintenant()) {
        val c = c(jeu)
        val faites = (entiers(c.optJSONArray("fetes")) + jalons().filter { it <= m }).toSortedSet()
        c.put("fetes", JSONArray(faites.toList()))
        c.put("fete", JSONObject().put("m", m).put("t", now))
        c.getJSONArray("pages").put(JSONObject().put("m", m).put("t", now))
        c.put("humeur", JSONObject().put("h", "fete").put("t", now))
        aEcrire.add(t(if (retard) "cr.fete.terminal.retard" else "cr.fete.terminal", "nom" to jeu.nom, "duree" to duree(m), "date" to dateTexte(c.optDouble("eclosion", now))))
        aEcrire.add(t("cr.fete.album.tel", "duree" to duree(m)))
        jeu.dire(t(if (retard) "cr.fete.retard" else "cr.fete.dit", "duree" to duree(m)), 12)
        jeu.animer("victoire")
        jeu.log(t("cr.fete.log", "nom" to jeu.nom, "duree" to duree(m)))
    }

    fun feteActive(jeu: Jeu, now: Double = maintenant()): Boolean {
        if (!jeu.extra.has("creature")) return false
        val f = jeu.module("creature").optJSONObject("fete") ?: return false
        val dt = now - f.optDouble("t", 0.0)
        return dt >= 0 && dt < donnees().optDouble("fete_duree", 600.0)
    }

    // ---------------------------------------------------------------- 18. l'envie mystère
    fun texteDevinette(id: String, k: Int): String = when {
        k <= 0 -> t("cr.dev.$id.d")
        k < 3 -> t("cr.dev.$id.i$k")
        else -> t("cr.envie.reponse", "cmd" to (parId(id)?.optString("cmd") ?: ""))
    }

    fun envie(jeu: Jeu): JSONObject? {
        if (!jeu.extra.has("creature")) return null
        val e = jeu.module("creature").optJSONObject("envie") ?: return null
        return if (parId(e.optString("id")) != null) e else null
    }

    private fun envieTour(jeu: Jeu, c: JSONObject, l: String, now: Double) {
        val e = envie(jeu)
        if (e != null) {
            if (trouve(e.optString("id"), l)) {
                c.remove("envie")
                c.put("gouts", c.optInt("gouts") + 1)
                c.put("depuis", 0)
                jeu.dire(t(if (e.optInt("k") == 0) "cr.envie.trouve_seul" else "cr.envie.trouve"), 10)
                aEcrire.add(t("cr.envie.trouve.terminal", "nom" to jeu.nom))
                jeu.animer("content")
            }
            return
        }
        c.put("depuis", c.optInt("depuis") + 1)
        val jour = numeroJour(now)
        val ej = c.optJSONArray("envies_jour") ?: JSONArray(listOf(0, 0))
        if (ej.optLong(0) != jour) c.put("envies_jour", JSONArray(listOf(jour, 0)))
        val nJour = c.getJSONArray("envies_jour").optInt(1)
        val moment = Envies.e(jeu).optJSONObject("moment") != null
        if (!peutProposer(chap1(jeu), nJour, false, c.optInt("depuis"), moment)) return
        val dv = choisirDevinette(eligibles(jeu.vus), jour + c.optInt("gouts"), c.optString("derniere_dev").ifEmpty { null }) ?: return
        c.put("envie", JSONObject().put("id", dv).put("k", 0).put("t", now))
        c.put("envies_jour", JSONArray(listOf(jour, nJour + 1)))
        c.put("depuis", 0)
        c.put("derniere_dev", dv)
        jeu.dire(t("cr.envie.annonce", "texte" to texteDevinette(dv, 0)), 14)
        aEcrire.add(t("cr.envie.terminal.tel", "texte" to texteDevinette(dv, 0)))
        jeu.animer("parle")
    }

    /** `indice [plus-tard]` : un indice de plus (3 au plus), ou ranger l'envie mystère. */
    fun indice(jeu: Jeu, arg: String? = null): String {
        val e = envie(jeu) ?: return t("cr.indice.aucune", "nom" to jeu.nom)
        if (arg != null && arg.lowercase().replace("_", "-") in setOf("plus-tard", "plustard", "later", "range", "ranger")) {
            jeu.module("creature").remove("envie")
            return t("cr.indice.plus_tard", "nom" to jeu.nom)
        }
        val k = minOf(3, e.optInt("k") + 1)
        e.put("k", k)
        return t("cr.indice.n", "k" to k, "texte" to texteDevinette(e.getString("id"), k))
    }

    fun ligneEnvie(jeu: Jeu): String? {
        val e = envie(jeu) ?: return null
        return t("cr.envie.ecran.tel", "texte" to texteDevinette(e.getString("id"), 0), "k" to e.optInt("k"))
    }

    // ---------------------------------------------------------------- 12, 16. les écrans du terminal
    fun gouts(jeu: Jeu): String {
        val out = mutableListOf(t("cr.gouts.titre", "nom" to jeu.nom), "")
        val e = espece(jeu) ?: return (out + t("cr.gouts.aucun", "nom" to jeu.nom)).joinToString("\n")
        out.add("♥ " + t("cr.gouts.plat", "cmd" to (plat(jeu) ?: "?"), "espece" to e.nom))
        aliment(typeEspece(jeu))?.let { out.add("★ " + t("cr.gouts.aliment", "aliment" to (Satiete.ICONES[it] ?: "") + " " + t("sat.famille.$it"))) }
        out.add("? " + if (c(jeu).optBoolean("secret")) t("cr.gouts.secret_trouve", "cmd" to (secret(jeu) ?: "?")) else t("cr.gouts.secret"))
        out.add("")
        out.add(t("cr.gouts.pied"))
        return out.joinToString("\n")
    }

    fun dateOu(p: JSONObject?): String =
        if (p == null || p.optBoolean("avant") || p.optDouble("t", 0.0) <= 0) t("cr.album.avant") else dateTexte(p.getDouble("t"))

    fun souvenir(p: JSONObject?): String {
        val s = p?.optJSONArray("s") ?: return ""
        val k = s.optString(0)
        return if (k == "cr.souv.premiere") t(k, "cmd" to s.opt(1)) else t(k, "n" to s.opt(1))
    }

    /** `album [nom]` dans le terminal du téléphone (la vue dessinée : CreatureVue). */
    fun albumTexte(jeu: Jeu, qui: String? = null): String {
        val c = c(jeu)
        if (!qui.isNullOrBlank()) {
            val caps = Explo.captures(jeu)
            val q = qui.lowercase()
            val ind = (0 until caps.length()).map { caps.getJSONObject(it) }
                .firstOrNull { q == it.optString("nom").lowercase() || q == it.optString("espece").lowercase() }
                ?: return t("cr.album.inconnu", "nom" to qui)
            val stades = liste(donnees().optJSONArray("album_stades_equipe"))
            val actuel = Equipe.stade(ind)
            val dates = ind.optJSONObject("album")
            val out = mutableListOf(t("cr.album.titre", "nom" to ind.optString("nom").ifEmpty { ind.optString("espece") }), "")
            for ((k, s) in stades.withIndex()) {
                out.add(if (k <= stades.indexOf(actuel)) "● ${Equipe.nomStade(s).replaceFirstChar { it.uppercase() }}  " +
                    (dates?.optDouble(s, 0.0)?.takeIf { it > 0 }?.let { dateTexte(it) } ?: t("cr.album.avant"))
                else "○ ${Equipe.nomStade(s).replaceFirstChar { it.uppercase() }} · ${t("cr.album.bientot")}")
            }
            return out.joinToString("\n")
        }
        val out = mutableListOf(t("cr.album.titre", "nom" to jeu.nom))
        if (c.optDouble("eclosion", 0.0) > 0) out.add(t("cr.album.eclos", "date" to dateTexte(c.getDouble("eclosion"))))
        out.add("")
        val actuel = stadeCompagnon(jeu) ?: return (out + t("cr.album.oeuf")).joinToString("\n")
        val stades = stadesCompagnon()
        for ((k, s) in stades.withIndex()) {
            val nomS = Equipe.nomStade(s).replaceFirstChar { it.uppercase() }
            if (k <= stades.indexOf(actuel)) {
                val p = c.getJSONObject("album").optJSONObject(s) ?: JSONObject().put("avant", true)
                val niv = if (p.has("niv")) t("cr.album.niveau", "n" to p.optInt("niv")) else ""
                val sv = souvenir(p)
                out.add("● $nomS  ${dateOu(p)}${if (niv.isNotEmpty()) " · $niv" else ""}${if (sv.isNotEmpty()) " · $sv" else ""}")
            } else out.add("○ $nomS · ${t("cr.album.bientot")}")
        }
        val pages = c.getJSONArray("pages")
        if (pages.length() > 0) {
            out.add("")
            out.add(t("cr.album.fetes") + " " + (maxOf(0, pages.length() - 6) until pages.length()).joinToString(" · ") {
                val p = pages.getJSONObject(it); "★ ${duree(p.optInt("m"))} (${dateTexte(p.optDouble("t"))})" })
        }
        if (c.optInt("gouts") > 0) out.add(t("cr.album.gouts", "n" to c.optInt("gouts")))
        out.add("")
        out.add(t("cr.album.pied.tel"))
        return out.joinToString("\n")
    }
}
