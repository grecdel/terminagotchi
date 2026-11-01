package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.math.BigDecimal
import java.math.MathContext
import java.math.RoundingMode
import java.security.MessageDigest
import java.text.Normalizer
import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.pow

/**
 * 📡 La Tour des Ondes — la radio, LoRa et les réseaux maillés (docs/programme.md § 7.11), portage de pc/tg/ondes.py.
 *
 * Mêmes règles que sur PC (la fréquence tapée, la longueur d'onde et la réponse de l'enfant, le mur, les canaux Wi-Fi,
 * le résumé ANONYME d'une liste de réseaux, la règle du spectre, les bandes libres et les choix mélangés comme
 * random.shuffle de Python, la vallée et le plus petit SF, le temps d'émission LoRa, la règle du 1 %, le maillage du
 * Terminaworld avec ses nœuds coupés, la cible de la tempête, les antennes de la vue déployée) : vecteurs communs
 * donnees/ondes/vecteurs.json, vérifiés par tests/jvm/Ondes.kt.
 *
 * Écouter est libre, émettre est réglementé : l'appli n'émet JAMAIS. Sur le téléphone, l'appli n'a pas accès aux
 * radios (ni nmcli, ni rfkill, ni bluetoothctl, ni carte LoRa, ni radio logicielle) : ces étapes sont RACONTÉES
 * (`ondes canaux` montre un quartier d'exemple, `ondes radios` raconte les radios du téléphone). Aucun nom de réseau,
 * aucune adresse, aucun message tapé n'est enregistré ni envoyé.
 */
object Ondes {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("ondes.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    fun asciiBas(texte: String) = Normalizer.normalize(texte, Normalizer.Form.NFKD).filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }

    private val NOMS = mapOf("fm" to "fm", "radio" to "fm", "lora" to "lora", "gps" to "gps", "wifi" to "wifi24", "wi-fi" to "wifi24",
        "wifi24" to "wifi24", "wifi2" to "wifi24", "wifi5" to "wifi5", "5g" to "cinqg", "cinqg" to "cinqg", "4g" to "quatreg",
        "quatreg" to "quatreg", "bluetooth" to "bluetooth", "bt" to "bluetooth", "wifi6" to "wifi6")
    private val MULT = mapOf("" to 1L, "hz" to 1L, "k" to 1_000L, "khz" to 1_000L, "m" to 1_000_000L, "mhz" to 1_000_000L,
        "g" to 1_000_000_000L, "ghz" to 1_000_000_000L)

    fun hzTech(tid: String): Long? {
        val f = o("onde").optJSONObject("frequences")
        if (f != null && f.has(tid)) return f.getLong(tid)
        return objets(o("spectre"), "techs").firstOrNull { it.optString("id") == tid }?.getLong("hz")
    }

    /** Une fréquence tapée → (Hz, technologie ou null) : « lora », « wifi5 », « 868M », « 2.4G », « 2,4 GHz »… */
    fun frequenceDe(texte: String?): Pair<Long, String?>? {
        val s = asciiBas((texte ?: "").trim().lowercase()).replace(" ", "")
        NOMS[s]?.let { tid -> return (hzTech(tid) ?: return null) to tid }
        val m = Regex("(\\d+(?:[.,]\\d+)?)([a-z]*)").matchEntire(s) ?: return null
        val mult = MULT[m.groupValues[2]] ?: return null
        val v = m.groupValues[1].replace(",", ".").toDouble() * mult
        if (v < 1) return null
        return Math.rint(v).toLong() to null
    }

    fun longueurOnde(hz: Long): Double = donnees().optLong("vitesse", 300_000_000L).toDouble() / hz

    /** Comme le format « g » de Python (p chiffres significatifs, sans zéros inutiles). */
    fun g(x: Double, p: Int): String {
        if (x == 0.0) return "0"
        val b = BigDecimal(x).round(MathContext(p, RoundingMode.HALF_EVEN)).stripTrailingZeros()
        return b.toPlainString()
    }

    fun texteLongueur(m: Double): String = when {
        m >= 1000 -> "${g(m / 1000, 4)} km"
        m >= 1 -> "${g(m, 3)} m"
        m >= 0.01 -> "${g(m * 100, 3)} cm"
        else -> "${g(m * 1000, 3)} mm"
    }

    fun longueurOk(reponse: String?, hz: Long): Boolean {
        val m = Regex("^\\s*(\\d+(?:[.,]\\d+)?)\\s*([a-zA-Z]*)\\s*$").find(reponse ?: "") ?: return false
        val v = m.groupValues[1].replace(",", ".").toDouble()
        val x = when (m.groupValues[2].lowercase()) {
            "m", "metre", "metres", "meter", "meters" -> v
            "cm" -> v / 100
            "mm" -> v / 1000
            "" -> if (v < 2) v else v / 100
            else -> return false
        }
        val vrai = longueurOnde(hz)
        return abs(x - vrai) <= 0.05 * vrai
    }

    fun periodes(hz: Long): Double = max(1.0, 1 + 3 * log10(hz / 1e8))

    /** (amplitude, puissance) qui restent après db décibels, en pour cent (arrondis comme Python). */
    fun restantPc(db: Int): Pair<Int, Int> = Math.rint(100 * 10.0.pow(-db / 20.0)).toInt() to Math.rint(100 * 10.0.pow(-db / 10.0)).toInt()

    fun affaiblissement(matiere: String, tech: String, n: Int = 1): Int =
        (o("onde").optJSONObject("murs")?.optJSONObject(matiere)?.optInt(tech, 0) ?: 0) * n

    fun traverseLeMieux(matiere: String = "brique"): String {
        val m = o("onde").optJSONObject("murs")?.optJSONObject(matiere) ?: return "lora"
        return m.keys().asSequence().toList().minWith(compareBy<String>({ m.getInt(it) }, { it }))
    }

    fun canal(mhz: Int): Int? = when {
        mhz in 2412..2472 && (mhz - 2407) % 5 == 0 -> (mhz - 2407) / 5
        mhz == 2484 -> 14
        mhz in 5150..5895 && mhz % 5 == 0 -> (mhz - 5000) / 5
        mhz in 5925..7125 && (mhz - 5950) % 5 == 0 -> (mhz - 5950) / 5
        else -> null
    }

    fun bande(mhz: Int): String? = when (mhz) { in 2400..2500 -> "2,4"; in 5150..5895 -> "5"; in 5925..7125 -> "6"; else -> null }

    class Resume(val n: Int, val bandes: Map<String, Int>, val canaux: Map<Int, Int>)

    /** Les grandeurs ANONYMES d'une liste de réseaux : (nombre, par bande, par canal 2,4 GHz). Rien d'autre. */
    fun resumeWifi(freqs: List<Int>): Resume {
        val pb = LinkedHashMap<String, Int>(); val pc = sortedMapOf<Int, Int>()
        for (f in freqs) {
            val b = bande(f)
            if (b != null) pb[b] = (pb[b] ?: 0) + 1
            val c = canal(f)
            if (c != null && b == "2,4") pc[c] = (pc[c] ?: 0) + 1
        }
        return Resume(freqs.size, pb, pc)
    }

    fun reseauxOk(reponse: String?, vrai: Int): Boolean {
        val n = reponse?.trim()?.toIntOrNull() ?: return false
        return abs(n - vrai) <= max(2, vrai / 5)
    }

    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }
    private fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()
    const val LETTRES = "ABCDEF"

    fun regleCartes(graine: String): List<Pair<Char, String>> = LETTRES.toList().zip(melange(graine, "regle", liste(o("spectre"), "regle")))
    fun regleReponse(graine: String): List<Char> {
        val pos = regleCartes(graine).associate { it.second to it.first }
        val hz = objets(o("spectre"), "techs").associate { it.optString("id") to it.getLong("hz") }
        return liste(o("spectre"), "regle").sortedBy { hz[it] ?: 0L }.map { pos[it]!! }
    }

    fun libreCartes(graine: String): List<Triple<Int, String, String>> {
        val lib = objets(o("spectre"), "techs").associate { it.optString("id") to it.optString("libre") }
        return melange(graine, "libre", liste(o("spectre"), "libre")).mapIndexed { i, x -> Triple(i + 1, x, lib[x] ?: "r") }
    }

    fun choixCartes(graine: String): List<Triple<Int, String, String>> =
        melange(graine, "choix", objets(o("choix"), "situations")).mapIndexed { i, x -> Triple(i + 1, x.optString("id"), x.optString("rep")) }

    // ---------------------------------------------------------------- LoRa
    private val L get() = o("lora")
    fun dureeSymboleUs(sf: Int): Long = (1L shl sf) * 1_000_000L / L.optLong("bw", 125000)

    fun symbolesMessage(sf: Int, octets: Int? = null): Int {
        val pl = octets ?: L.optInt("octets", 10)
        val de = if (sf >= 11) 1 else 0
        val num = 8 * pl - 4 * sf + 28 + 16
        val den = 4 * (sf - 2 * de)
        return 8 + max(Math.floorDiv(-num, den).let { -it } * (L.optInt("cr", 1) + 4), 0)
    }

    fun tempsEmissionUs(sf: Int, octets: Int? = null): Long {
        val n = symbolesMessage(sf, octets)
        return (4L * L.optInt("preambule", 8) + 17 + 4L * n) * (1L shl sf) * 1_000_000L / (4L * L.optLong("bw", 125000))
    }

    fun porteeM(sf: Int): Int = L.optJSONObject("portee_m")?.optInt("$sf", 0) ?: 0
    fun valleeM(graine: String): Int { val v = L.optJSONArray("vallees_m") ?: JSONArray(); return v.getInt(tire(graine, "vallee", v.length())) }
    fun facteurs(): List<Int> = (L.optJSONArray("facteurs") ?: JSONArray()).let { a -> (0 until a.length()).map { a.getInt(it) } }
    fun sfMin(distance: Int): Int? = facteurs().firstOrNull { porteeM(it) >= distance }
    fun budgetUs(): Long = L.optLong("heure_s", 3600) * 1_000_000L * L.optLong("cycle_pour_mille", 10) / 1000
    fun messagesHeure(sf: Int, octets: Int? = null): Long = budgetUs() / tempsEmissionUs(sf, octets)
    fun messagesOk(reponse: String?, sf: Int): Boolean { val n = reponse?.trim()?.toLongOrNull() ?: return false; return abs(n - messagesHeure(sf)) <= 1 }

    // ---------------------------------------------------------------- le maillage du Terminaworld
    fun noeuds(): List<String> = Port.ids()
    fun liens(): List<Pair<String, String>> = Port.liens() +
        (o("maillage").optJSONArray("liens_radio") ?: JSONArray()).let { a -> (0 until a.length()).map { a.getJSONArray(it).let { l -> l.getString(0) to l.getString(1) } } }

    fun voisins(id: String, coupes: Collection<String> = emptyList()): List<String> {
        val out = mutableListOf<String>()
        for ((a, b) in liens()) {
            if (a == id && b !in coupes && b !in out) out.add(b)
            else if (b == id && a !in coupes && a !in out) out.add(a)
        }
        return out
    }

    fun route(depart: String, arrivee: String?, coupes: Collection<String> = emptyList()): List<String>? {
        if (arrivee == null || depart in coupes || arrivee in coupes) return null
        val avant = LinkedHashMap<String, String?>(); avant[depart] = null
        val file = ArrayDeque<String>().apply { add(depart) }
        while (file.isNotEmpty()) {
            val x = file.removeFirst()
            if (x == arrivee) {
                val c = mutableListOf(x)
                while (avant[c.last()] != null) c.add(avant[c.last()]!!)
                return c.reversed()
            }
            for (v in voisins(x, coupes)) if (v !in avant) { avant[v] = x; file.add(v) }
        }
        return null
    }

    fun inondation(depart: String, coupes: Collection<String> = emptyList()): List<List<String>> {
        val vus = mutableSetOf(depart)
        val vagues = mutableListOf(listOf(depart))
        while (true) {
            val suite = mutableListOf<String>()
            for (x in vagues.last()) for (v in voisins(x, coupes)) if (v !in vus) { vus.add(v); suite.add(v) }
            if (suite.isEmpty()) return vagues
            vagues.add(suite)
        }
    }

    fun defiCible(graine: String): String { val c = liste(o("maillage"), "cibles"); return c[tire(graine, "cible", c.size)] }
    fun sautsMax() = o("maillage").optInt("sauts_max", 7)
    fun coupesDefi() = o("maillage").optInt("coupes_defi", 3)

    class Envoi(val ok: Boolean, val chemin: List<String>, val raison: String, val sauts: Int)

    fun envoi(dest: String, coupes: Collection<String> = emptyList()): Envoi {
        if (dest !in noeuds()) return Envoi(false, emptyList(), "inconnu", 0)
        if (dest == "camp") return Envoi(false, listOf("camp"), "camp", 0)
        if (dest in coupes) return Envoi(false, emptyList(), "coupe", 0)
        val r = route("camp", dest, coupes) ?: return Envoi(false, emptyList(), "isole", 0)
        if (r.size - 1 > sautsMax()) return Envoi(false, r, "loin", r.size - 1)
        return Envoi(true, r, "arrive", r.size - 1)
    }

    // ---------------------------------------------------------------- les antennes (vue déployée, surveillance)
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")

    fun antenneDe(morceau: String?): Pair<String, String>? {
        val m = (morceau ?: "").trim().replace(Regex("^(timeout\\s+\\S+\\s+)"), "")
        for (r in objets(o("antennes"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m)) return r.optString("radio") to r.optString("sens")
        return null
    }

    fun antennesDe(ligne: String?): List<Pair<String, String>> = (ligne ?: "").split(SEPARATEURS).mapNotNull { antenneDe(it) }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet de la tour
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("ondes")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        if (c.optJSONArray("coupes") == null) c.put("coupes", JSONArray())
        return c
    }

    private fun faits(jeu: Jeu) = liste(etat(jeu), "faits")
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in faits(jeu)) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }
    fun coupes(jeu: Jeu): List<String> = liste(etat(jeu), "coupes")
    private fun mettreCoupes(jeu: Jeu, l: List<String>) { etat(jeu).put("coupes", JSONArray(l)) }

    const val CARNET = "carnet_de_la_tour.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "ondes")
    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok") =
        Regex("^\\[$etiquette].*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))

    /** Les nœuds du chemin coupés depuis le dernier « ondes defi ». */
    fun defiCoupes(jeu: Jeu): Int {
        val txt = carnet(jeu)
        val i = txt.lastIndexOf("[defi_debut]")
        if (i < 0) return 0
        return Regex("^\\[defi_coupe].*\\(ok\\)\\s*$", RegexOption.MULTILINE).findAll(txt.substring(i)).count()
    }

    private fun ecrire(jeu: Jeu, rel: String, contenu: String) = Histoire.ecrire(jeu, "ondes/$rel", contenu, finLigne = false)

    /** Le fichier d'exemple de W6 : des lignes JSON comme celles de rtl_433 -F json, toutes FICTIVES (même texte qu'en Python). */
    fun capteursTexte(): String = objets(o("ciel"), "capteurs").joinToString("") { c ->
        "{" + c.keys().asSequence().joinToString(", ") { k -> "\"$k\": " + jsonValeur(c.get(k)) } + "}\n" }

    private fun jsonValeur(v: Any): String = when (v) {
        is String -> JSONObject.quote(v)
        is Double -> if (v == Math.floor(v) && !v.isInfinite()) "${v.toLong()}.0" else v.toString()
        else -> v.toString()
    }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf(
        "ondes/plan_de_la_tour.txt" to t("on.meuble.plan", "nom" to jeu.nom) + "\n",
        "ondes/$CARNET" to t("on.meuble.carnet") + "\n",
        "ondes/capteurs_exemple.json" to capteursTexte())

    val BESOINS = mapOf("on0" to listOf("plan_de_la_tour.txt"), "on10" to listOf("capteurs_exemple.json"))

    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val tous = meubles(jeu)
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) (tous["ondes/$r"] as? String)?.let { ecrire(jeu, r, it) }
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("on.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val ON = "^(tg\\s+)?ondes\\s+"
    private const val MESH = "^(tg\\s+)?(ondes\\s+)?mesh-"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  exploit: String? = null, reseau: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, reseau = reseau, exploit = exploit)

    val IDS = (0..10).map { "on$it" }

    /** Les leçons du téléphone : les mêmes paliers ; les radios de la vraie machine (nmcli, iw, rfkill, bluetoothctl,
     *  meshtastic, rtl_test) sont racontées ; bc est remplacé par le calcul en entiers du shell. */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "on0" to Lecon("hist.on0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/ondes", "hist.entree.bravo", ici = "ondes", params = mapOf("piece" to "ondes")),
                n("on0", 1, "ls", re = LS, ou = "ondes"),
                n("on0", 2, "cat plan_de_la_tour.txt", re = "$LIRE.*plan_de_la_tour"),
            )),
            "on1" to Lecon("hist.on1.titre", null, 1, listOf(
                n("on1", 0, "ondes onde", re = "${ON}onde\\s*$", ou = "ondes"),
                n("on1", 1, "ondes onde lora", re = "${ON}onde\\s+\\S"),
                n("on1", "t2", "echo \$((300000000 / 2400000))", re = "^echo\\s+\\$\\(\\(300000000\\b"),
                n("on1", 3, "ondes longueur ?", fs = carnetOk("longueur")),
                n("on1", 4, "ondes mur", re = "${ON}murs?\\b"),
                n("on1", 5, "ondes traverse ?", fs = carnetOk("traverse")),
            )),
            "on2" to Lecon("hist.on2.titre", null, 1, listOf(
                n("on2", 3, "ondes canaux", re = "${ON}canaux\\b", ou = "ondes"),
                n("on2", 4, "ondes voisins", re = "${ON}voisins\\b"),
            )),
            "on3" to Lecon("hist.on3.titre", null, 1, listOf(
                n("on3", 3, "ondes radios", re = "${ON}radios?\\b", ou = "ondes"),
            )),
            "on4" to Lecon("hist.on4.titre", null, 1, listOf(
                n("on4", 0, "ondes spectre", re = "${ON}spectre\\b", ou = "ondes"),
                n("on4", 1, "ondes regle", re = "${ON}r[eè]gle\\s*$"),
                n("on4", 2, "ondes regle ? ? ? ? ? ?", fs = carnetOk("regle")),
                n("on4", 3, "ondes libre", re = "${ON}libres?\\s*$"),
                n("on4", 4, "ondes libre ? ? ? ? ? ?", fs = carnetOk("libre")),
            )),
            "on5" to Lecon("hist.on5.titre", null, 1, listOf(
                n("on5", 0, "ondes lora", re = "${ON}lora\\b", ou = "ondes"),
                n("on5", "t1", "echo \$((4096 * 1000000 / 125000))", re = "^echo\\s+\\$\\(\\(4096\\b"),
                n("on5", 2, "ondes temps", re = "${ON}temps\\b"),
                n("on5", 3, "ondes vallee", re = "${ON}vall[eé]e\\s*$"),
                n("on5", 4, "ondes vallee ?", fs = carnetOk("vallee")),
                n("on5", "t5", "echo \$((3600 * 1 / 100))", re = "^echo\\s+\\$\\(\\(3600\\b"),
                n("on5", 6, "ondes messages ?", fs = carnetOk("messages")),
            )),
            "on6" to Lecon("hist.on6.titre", null, 1, listOf(
                n("on6", 0, "ondes passerelle", re = "${ON}passerelles?\\b", ou = "ondes"),
                n("on6", 1, "ondes maillage", re = "${ON}maillage\\b"),
                n("on6", 2, "ondes choix", re = "${ON}choix\\s*$"),
                n("on6", 3, "ondes choix ? ? ? ?", fs = carnetOk("choix")),
            )),
            "on7" to Lecon("hist.on7.titre", null, 1, listOf(
                n("on7", 0, "mesh-route", re = "${MESH}route\\b", ou = "ondes"),
                n("on7", 1, "mesh-envoie feu \"bonjour\"", fs = carnetOk("envoie")),
                n("on7", 2, "mesh-coupe roche", fs = carnetOk("coupe")),
                n("on7", 3, "mesh-envoie feu \"bonjour\"", fs = carnetOk("detour")),
                n("on7", 4, "mesh-route feu", re = "${MESH}route\\s+\\S"),
                n("on7", 5, "mesh-coupe -r", fs = carnetOk("rallume")),
            )),
            "on8" to Lecon("hist.on8.titre", null, 1, listOf(
                n("on8", 0, "ondes defi", re = "${ON}d[eé]fi\\b", ou = "ondes"),
                n("on8", 1, "mesh-coupe ?", fs = { j -> defiCoupes(j) >= coupesDefi() }),
                n("on8", 2, "mesh-envoie ? \"SOS\"", fs = carnetOk("defi"), exploit = "ondes.onde"),
            )),
            "on9" to Lecon("hist.on9.titre", null, 1, listOf(
                n("on9", 0, "ondes adulte", re = "${ON}adulte\\b", ou = "ondes"),
                n("on9", 5, "ondes noeud", re = "${ON}n(oe|œ)uds?\\b"),
            )),
            "on10" to Lecon("hist.on10.titre", null, 1, listOf(
                n("on10", 0, "ondes ecoute", re = "${ON}[eé]coute\\b", ou = "ondes"),
                n("on10", 3, "ondes avions", re = "${ON}avions?\\b"),
                n("on10", 4, "cat capteurs_exemple.json", re = "$LIRE.*capteurs_exemple"),
                n("on10", 5, "grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json", re = "^grep\\b.*temperature_C.*capteurs_exemple"),
                n("on10", 6, "ondes anonyme", re = "${ON}anonymes?\\b"),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "ondes" }
    }

    private fun besoin(): Pair<List<String>, List<String>> {
        val m = monde() ?: return emptyList<String>() to emptyList()
        val tronc = Programme.donnees().optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct() to liste(m, "requis_lecons")
    }

    fun ouvert(jeu: Jeu): Boolean {
        val (chaps, lecs) = besoin()
        if (chaps.isEmpty() && lecs.isEmpty()) return false
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.all { Histoire.fini(jeu, it) } && lecs.all { it in f }
    }

    fun manque(jeu: Jeu): List<String> {
        val (chaps, lecs) = besoin()
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) } +
            lecs.filter { it !in f }.map { l -> val ch = Histoire.chapitreDeLecon(l)
                Histoire.tx("hist.$l.titre") + " (" + (ch?.let { Histoire.nomChapitre(it.id) } ?: "?") + ")" }
    }

    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "ondes" } || Histoire.fini(jeu, "ondes") || !ouvert(jeu)) return false
        deja.put("ondes")
        jeu.log(t("on.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "on.ouvert.dit"), 18)
        return true
    }

    /** Les leçons qui ouvrent un monde (programme.json, « requis_lecons ») : annoncé dès la leçon finie. */
    fun leconsQuiOuvrent(): Set<String> {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return emptySet()
        return (0 until ms.length()).flatMap { liste(ms.getJSONObject(it), "requis_lecons") }.toSet()
    }

    // ---------------------------------------------------------------- les indices et la garde
    private val REPONSES = mapOf("ondes longueur ?" to "longueur", "ondes traverse ?" to "traverse", "ondes regle ? ? ? ? ? ?" to "regle",
        "ondes libre ? ? ? ? ? ?" to "libre", "ondes vallee ?" to "vallee", "ondes messages ?" to "messages", "ondes choix ? ? ? ?" to "choix")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("on.indice.sudo")
        if ("?" in e.cmd.split(" ") && lignes.filter { r(ON).containsMatchIn(it) || r(MESH).containsMatchIn(it) }.any { TROU.containsMatchIn(it) })
            return t("on.indice.trou")
        REPONSES[e.cmd]?.let { et ->
            val der = carnet(jeu).lines().lastOrNull { it.startsWith("[$et]") }
            if (der != null && !der.trimEnd().endsWith("(ok)")) return t("on.indice.$et")
        }
        if (les == "on8" && jeu.etape >= 1) {
            val der = carnet(jeu).lines().lastOrNull { it.startsWith("[defi_coupe]") || it.startsWith("[defi]") || it.startsWith("[defi_debut]") }
            if (der != null && der.trimEnd().endsWith("(isole)")) return t("on.indice.isole")
            if (der != null && der.trimEnd().endsWith("(hors)")) return t("on.indice.hors_chemin")
            if (jeu.etape == 2 && defiCoupes(jeu) < coupesDefi()) return t("on.indice.recoupe")
            if (jeu.etape == 1 && der != null && (der.startsWith("[defi_coupe]") || der.startsWith("[defi_debut]")))
                return t("on.indice.encore", "n" to defiCoupes(jeu), "total" to coupesDefi())
        }
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu : ondes …, mesh-…
    private fun grand(n: Long) = "%,d".format(java.util.Locale.ROOT, n).replace(",", " ")
    private fun hzTexte(hz: Long): String {
        for ((div, u) in listOf(1_000_000_000L to "GHz", 1_000_000L to "MHz", 1_000L to "kHz")) if (hz >= div) return g(hz.toDouble() / div, 6) + " " + u
        return "$hz Hz"
    }
    private fun icone(id: String) = Port.machine(id)?.icone ?: "?"
    fun ligneChemin(c: List<String>) = "  " + c.joinToString(" → ") { "${icone(it)} $it" }

    /** L'onde en caractères (pour l'écran étroit du téléphone, comme grille_onde sur PC). */
    fun grilleOnde(per: Double, largeur: Int = 30, hauteur: Int = 7, phase: Double = 0.0, mur: Int? = null, reste: Int = 100): List<String> {
        val A = (hauteur - 1) / 2.0
        val gr = Array(hauteur) { CharArray(largeur) { ' ' } }
        var avant: Int? = null
        for (x in 0 until largeur) {
            val a = if (mur == null || x < mur) A else A * reste / 100
            val y = A - a * kotlin.math.sin(2 * Math.PI * (per * x / largeur) - phase)
            val rr = Math.rint(y).toInt().coerceIn(0, hauteur - 1)
            val (de, jus) = if (avant == null || (mur != null && x == mur)) rr to rr else minOf(avant, rr) to maxOf(avant, rr)
            for (k in de..jus) if (k == rr || k != avant) gr[k][x] = '•'
            avant = rr
        }
        if (mur != null) for (rw in 0 until hauteur) { gr[rw][mur] = '▓'; if (mur + 1 < largeur) gr[rw][mur + 1] = '▓' }
        return gr.map { String(it) }
    }

    fun lignesOnde(jeu: Jeu, arg: String?): List<String> {
        val f = if (arg != null) frequenceDe(arg) else hzTech("wifi24")?.let { it to "wifi24" }
        if (f == null) return listOf(t("on.onde.aide"))
        val (hz, tid) = f
        val lam = longueurOnde(hz)
        noter(jeu, "onde", "${tid ?: hz} (ok)")
        return listOf("〰 " + t("on.onde.titre", "nom" to (tid?.let { t("on.tech.$it") } ?: hzTexte(hz))), "") + grilleOnde(periodes(hz)).map { "  $it" } +
            listOf("", "  " + t("on.onde.frequence", "f" to hzTexte(hz), "n" to grand(hz)), "  " + t("on.onde.longueur", "l" to texteLongueur(lam)),
                "  " + t("on.onde.calcul", "v" to "300 000 000", "f" to grand(hz), "l" to g(lam, 4)), "  " + t("on.onde.morale"), "  " + t("on.onde.aide"))
    }

    fun lignesLongueur(jeu: Jeu, arg: String?): List<String> {
        val hz = hzTech("lora") ?: 868_000_000L
        if (arg.isNullOrBlank()) return listOf(t("on.longueur.aide", "f" to hzTexte(hz)))
        return if (longueurOk(arg, hz)) { noter(jeu, "longueur", "$arg (ok)"); listOf("✔ " + t("on.longueur.ok", "l" to texteLongueur(longueurOnde(hz))), "  " + t("on.longueur.morale")) }
        else { noter(jeu, "longueur", "$arg (faux)"); listOf("✖ " + t("on.longueur.faux", "f" to hzTexte(hz))) }
    }

    fun lignesMur(jeu: Jeu, matiere0: String?, n0: Int): List<String> {
        val murs = o("onde").optJSONObject("murs") ?: JSONObject()
        val matiere = if (matiere0 != null && murs.has(matiere0)) matiere0 else "brique"
        val n = n0.coerceIn(1, 3)
        val out = mutableListOf("🧱 " + t("on.mur.titre", "matiere" to t("on.matiere.$matiere"), "n" to n), "")
        for (tid in listOf("lora", "wifi24", "wifi5")) {
            val db = affaiblissement(matiere, tid, n)
            val (amp, pui) = restantPc(db)
            out.add("  " + t("on.tech.$tid") + " : " + t("on.mur.perte", "db" to db, "amp" to amp, "pui" to pui))
            out += grilleOnde(periodes(hzTech(tid) ?: 1), 30, 5, 0.0, 15, amp).map { "  $it" }
        }
        noter(jeu, "mur", "$matiere $n (ok)")
        return out + listOf("", "  " + t("on.mur.morale"), "  " + t("on.mur.grands"), "  " + t("on.mur.aide"))
    }

    fun lignesTraverse(jeu: Jeu, arg: String?): List<String> {
        if (arg.isNullOrBlank()) return listOf(t("on.traverse.aide"))
        val tid = frequenceDe(arg)?.second
        return if (tid == traverseLeMieux()) { noter(jeu, "traverse", "$tid (ok)"); listOf("✔ " + t("on.traverse.ok"), "  " + t("on.traverse.morale")) }
        else { noter(jeu, "traverse", "${tid ?: "?"} (faux)"); listOf("✖ " + t("on.traverse.faux")) }
    }

    /** Sur le téléphone, pas de liste Wi-Fi accessible : un quartier d'EXEMPLE (fictif). */
    fun lignesCanaux(jeu: Jeu): List<String> {
        val ex = (donnees().optJSONArray("exemple_canaux") ?: JSONArray()).let { a -> (0 until a.length()).map { a.getInt(it) } }
        val rs = resumeWifi(ex)
        val out = mutableListOf("📶 " + t("on.canaux.titre"), "", "  " + t("on.canaux.exemple"),
            "  " + t("on.canaux.bandes", "n" to rs.n, "b24" to (rs.bandes["2,4"] ?: 0), "b5" to (rs.bandes["5"] ?: 0), "b6" to (rs.bandes["6"] ?: 0)), "")
        val haut = maxOf(1, rs.canaux.values.maxOrNull() ?: 1)
        for (niv in haut downTo 1) out.add("  " + (1..13).joinToString("") { c -> if ((rs.canaux[c] ?: 0) >= niv) "█ " else "  " })
        out.add("  " + (1..13).joinToString("") { "${it % 10} " })
        noter(jeu, "canaux", "exemple (ok)")
        return out + listOf("  " + t("on.canaux.axe"), "", "  " + t("on.canaux.morale"), "  " + t("on.canaux.grands"))
    }

    fun lignesVoisins(jeu: Jeu): List<String> { noter(jeu, "voisins", "lu (ok)"); return listOf("🔒 " + t("on.voisins.titre"), "") + t("on.voisins.texte").split("\n").map { "  $it" } }

    fun lignesRadios(jeu: Jeu): List<String> {
        noter(jeu, "radios", "raconte (ok)")
        return listOf("📻 " + t("on.radios.titre"), "", "  " + t("on.tel.radios"), "  " + t("on.tel.raconte", "outil" to "rfkill, nmcli, bluetoothctl"), "  " + t("on.radios.grands"))
    }

    fun lignesSpectre(jeu: Jeu): List<String> {
        noter(jeu, "spectre", "vu (ok)")
        val techs = objets(o("spectre"), "techs").sortedWith(compareBy({ it.getLong("hz") }, { it.optString("id") }))
        val l = 24
        fun pos(hz: Long) = Math.rint((log10(hz.toDouble()) - 7) / 3 * (l - 1)).toInt().coerceIn(0, l - 1)
        return listOf("🌈 " + t("on.spectre.titre"), "", "  10M    100M    1G     10G", "  ┼───────┼───────┼──────┼", "") +
            techs.map { x -> "  " + " ".repeat(pos(x.getLong("hz"))) + "▲ " + t("on.tech.${x.optString("id")}") + " (${x.optString("bande")}) " + (if (x.optString("libre") == "l") "✓" else "✗") } +
            listOf("", "  " + t("on.spectre.legende"), "  " + t("on.spectre.morale"), "  " + t("on.spectre.grands"))
    }

    fun lignesRegle(jeu: Jeu, rep: List<String>): List<String> {
        val gr = Histoire.graine(jeu)
        val cartes = regleCartes(gr)
        if (rep.isEmpty()) return listOf("📏 " + t("on.regle.titre"), "") + cartes.map { "  ${it.first}  " + t("on.tech.${it.second}") + " — " + t("on.usage.${it.second}") } + listOf("", "  " + t("on.regle.aide"))
        val rr = rep.map { it.uppercase().first() }
        val bon = regleReponse(gr)
        if (rr != bon) { noter(jeu, "regle", rr.joinToString(" ") + " (faux)"); return listOf("✖ " + t("on.regle.faux", "n" to rr.zip(bon).count { it.first == it.second }, "total" to bon.size)) }
        noter(jeu, "regle", rr.joinToString(" ") + " (ok)")
        val pos = cartes.toMap()
        val hz = objets(o("spectre"), "techs").associateBy { it.optString("id") }
        return listOf("✔ " + t("on.regle.ok"), "") + bon.map { "  ▲ $it " + t("on.tech.${pos[it]}") + " : " + (hz[pos[it]]?.optString("bande") ?: "") } + listOf("", "  " + t("on.regle.morale"))
    }

    private fun quiz(jeu: Jeu, et: String, cartes: List<Triple<Int, String, String>>, rep: List<String>, lettres: String, prefixe: String): List<String> {
        val rr = rep.map { it.lowercase().take(1) }
        if (rr.size != cartes.size || rr.any { it.isEmpty() || it[0] !in lettres }) return listOf(t("$prefixe.aide"))
        val justes = cartes.zip(rr).filter { it.first.third == it.second }.map { it.first }
        val out = mutableListOf<String>()
        if (justes.size == cartes.size) { noter(jeu, et, rr.joinToString(" ") + " (ok)"); out.add("✔ " + t("$prefixe.ok")) }
        else { noter(jeu, et, rr.joinToString(" ") + " (faux)"); out.add("✖ " + t("$prefixe.faux", "n" to justes.size, "total" to cartes.size)) }
        justes.forEach { out.add("  ✔ ${it.first}. " + t("$prefixe.${it.second}.pourquoi")) }
        return out
    }

    fun lignesLibre(jeu: Jeu, rep: List<String>): List<String> {
        val c = libreCartes(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("🔓 " + t("on.libre.titre"), "") + t("on.libre.regle").split("\n").map { "  $it" } + listOf("") +
            c.map { "  ${it.first}. " + t("on.tech.${it.second}") + " — " + t("on.usage.${it.second}") } + listOf("", "  " + t("on.libre.aide"))
        return quiz(jeu, "libre", c, rep, "lr", "on.libre")
    }

    fun lignesLora(jeu: Jeu): List<String> {
        noter(jeu, "lora", "vu (ok)")
        return listOf("🛰 " + t("on.lora.titre"), "", "   ╱│  ╱│  ╱│  ╱│", "  ╱ │ ╱ │ ╱ │ ╱ │", "") +
            listOf("chirp", "portee", "debit", "energie", "bande").map { "  • " + t("on.lora.$it") } + listOf("", "  " + t("on.lora.grands"))
    }

    fun lignesTemps(jeu: Jeu): List<String> {
        noter(jeu, "temps", "vu (ok)")
        return listOf("⏱ " + t("on.temps.titre", "octets" to L.optInt("octets", 10)), "", "  SF · " + t("on.temps.symbole") + " · " + t("on.temps.message") + " · " + t("on.temps.portee")) +
            facteurs().map { sf -> "  $sf · " + "%.3f".format(java.util.Locale.ROOT, dureeSymboleUs(sf) / 1000.0) + " ms · " +
                "%.1f".format(java.util.Locale.ROOT, tempsEmissionUs(sf) / 1000.0) + " ms · " + g(porteeM(sf) / 1000.0, 3) + " km" } +
            listOf("", "  " + t("on.temps.morale"), "  " + t("on.temps.grands"))
    }

    private fun ms(us: Long, dec: Int = 0) = "%.${dec}f".format(java.util.Locale.ROOT, us / 1000.0)

    fun dessinVallee(sf: Int, distance: Int, phase: Double = 1.0): List<String> {
        val l = 22
        val po = porteeM(sf)
        val arrive = po >= distance
        val bout = if (arrive) l - 1 else l * po / distance
        val pos = minOf(bout, (phase * bout).toInt())
        val ciel = CharArray(l) { if (it < pos) '·' else ' ' }
        ciel[minOf(pos, l - 1)] = if (arrive || phase < 1) '✉' else '✖'
        return listOf("  📡" + String(ciel) + "📡", "  ▲▁▂▃▅▆▇▆▅▃▂▁▂▃▅▇▅▃▂▁▁▁▲", "  " + t("on.vallee.mesure", "d" to g(distance / 1000.0, 3), "p" to g(po / 1000.0, 3)))
    }

    fun lignesVallee(jeu: Jeu, arg: String?): List<String> {
        val d = valleeM(Histoire.graine(jeu))
        if (arg.isNullOrBlank()) return listOf("⛰ " + t("on.vallee.titre", "d" to g(d / 1000.0, 3)), "") +
            facteurs().map { "  SF$it " + t("on.vallee.ligne", "p" to g(porteeM(it) / 1000.0, 3), "ms" to ms(tempsEmissionUs(it))) } + listOf("", "  " + t("on.vallee.aide"))
        val sf = arg.trim().replace(Regex("(?i)^sf"), "").toIntOrNull()
        if (sf == null || sf !in facteurs()) return listOf(t("on.vallee.aide"))
        val out = listOf("⛰ " + t("on.vallee.envoi", "sf" to sf), "") + dessinVallee(sf, d) + listOf("")
        val bon = sfMin(d)
        if (porteeM(sf) < d) { noter(jeu, "vallee", "SF$sf (court)"); return out + ("✖ " + t("on.vallee.court")) }
        if (sf != bon) { noter(jeu, "vallee", "SF$sf (lent)"); return out + ("✖ " + t("on.vallee.lent", "ms" to ms(tempsEmissionUs(sf)), "ms2" to ms(tempsEmissionUs(bon!!)))) }
        etat(jeu).put("sf", sf)
        noter(jeu, "vallee", "SF$sf (ok)")
        return out + ("✔ " + t("on.vallee.ok", "sf" to sf, "ms" to ms(tempsEmissionUs(sf))))
    }

    fun lignesMessages(jeu: Jeu, arg: String?): List<String> {
        val sf = etat(jeu).optInt("sf", 0).takeIf { it > 0 } ?: sfMin(valleeM(Histoire.graine(jeu))) ?: 12
        val us = tempsEmissionUs(sf)
        if (arg.isNullOrBlank()) return listOf(t("on.messages.aide", "sf" to sf, "ms" to ms(us, 1)))
        return if (messagesOk(arg, sf)) { noter(jeu, "messages", "SF$sf (ok)"); listOf("✔ " + t("on.messages.ok", "n" to messagesHeure(sf), "sf" to sf), "  " + t("on.messages.morale"), "  " + t("on.messages.grands")) }
        else { noter(jeu, "messages", "SF$sf (faux)"); listOf("✖ " + t("on.messages.faux", "ms" to ms(us, 1))) }
    }

    fun lignesPasserelle(jeu: Jeu): List<String> { noter(jeu, "passerelle", "vue (ok)")
        return listOf("🗼 " + t("on.passerelle.titre"), "", "  📟 📟 📟", "   ╲ │ ╱", "    🗼 ─ 🌐 ─ 🖥", "") + t("on.passerelle.texte").split("\n").map { "  $it" } + ("  " + t("on.passerelle.grands")) }

    fun lignesMaillage(jeu: Jeu): List<String> { noter(jeu, "maillage", "vu (ok)")
        return listOf("🕸 " + t("on.maillage.titre"), "", "  📟─📟─📟", "  │╲ │ ╱│", "  📟─📟─📟", "") + t("on.maillage.texte").split("\n").map { "  $it" } + ("  " + t("on.maillage.grands")) }

    fun lignesChoix(jeu: Jeu, rep: List<String>): List<String> {
        val c = choixCartes(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("🤔 " + t("on.choix.titre"), "") + c.map { "  ${it.first}. " + t("on.choix.${it.second}") } + listOf("", "  " + t("on.choix.aide"))
        return quiz(jeu, "choix", c, rep, "pm", "on.choix")
    }

    fun lignesRoute(jeu: Jeu, dest0: String?): List<String> {
        val cs = coupes(jeu)
        val dest = (dest0 ?: etat(jeu).optString("cible")).trim().lowercase().ifEmpty { null }
        if (dest != null && dest !in noeuds()) return listOf(t("on.mesh.inconnu", "nom" to dest), t("on.mesh.noeuds", "liste" to noeuds().joinToString(", ")))
        val sauts = HashMap<String, Int>(); inondation("camp", cs).forEachIndexed { i, v -> v.forEach { sauts[it] = i } }
        val out = mutableListOf("🕸 " + t("on.mesh.route.titre"), "")
        for (m in noeuds()) {
            if (m == "camp") continue
            out.add(when {
                m in cs -> "  ${icone(m)} $m ✖ " + t("on.mesh.coupe_court")
                m in sauts -> "  ${icone(m)} $m · " + t("on.mesh.sauts", "n" to sauts[m]!!) + " · " + t("on.mesh.par", "par" to route("camp", m, cs)!!.let { it[it.size - 2] })
                else -> "  ${icone(m)} $m ⚠ " + t("on.mesh.isole_court")
            })
        }
        if (dest != null) {
            out.add("")
            val ch = route("camp", dest, cs)
            if (ch != null) { out.add("  " + t("on.mesh.chemin", "dest" to dest, "n" to ch.size - 1)); out.add(ligneChemin(ch)) }
            else out.add("  " + t("on.mesh.isole", "dest" to dest))
        }
        noter(jeu, "route", "${dest ?: "-"} (ok)")
        return out + listOf("", "  " + t("on.mesh.aide"))
    }

    fun lignesEnvoie(jeu: Jeu, args: List<String>): List<String> {
        if (args.isEmpty()) return listOf(t("on.mesh.envoie.aide"))
        val cs = coupes(jeu)
        val dest = args[0].trim().lowercase()
        val message = args.drop(1).joinToString(" ").trim().trim('"', '\'').ifEmpty { "…" }
        val r = envoi(dest, cs)
        if (r.raison == "inconnu") return listOf(t("on.mesh.inconnu", "nom" to dest), t("on.mesh.noeuds", "liste" to noeuds().joinToString(", ")))
        if (r.raison == "camp") return listOf(t("on.mesh.camp"))
        val out = mutableListOf("✉ " + t("on.mesh.envoie.titre", "dest" to dest, "msg" to message.take(40)), "")
        for ((i, v) in inondation("camp", cs).withIndex()) {
            if (i == 0) continue
            out.add("  " + t("on.mesh.vague", "n" to i) + " " + v.joinToString(", ") { "${icone(it)} $it" })
            if (r.ok && dest in v) break
        }
        out.add("")
        val cible = etat(jeu).optString("cible").ifEmpty { null }
        val defi = cible != null && dest == cible
        if (!r.ok) {
            out.add("✖ " + t("on.mesh.rate.${r.raison}", "dest" to dest, "n" to r.sauts, "max" to sautsMax()))
            noter(jeu, "envoie", "$dest : ${r.raison} (perdu)")
            if (defi) noter(jeu, "defi", "$dest (isole)")
            return out
        }
        out += listOf(ligneChemin(r.chemin), "", "✔ " + t("on.mesh.arrive", "dest" to dest, "n" to r.sauts, "reste" to sautsMax() - r.sauts))
        noter(jeu, "envoie", r.chemin.joinToString(" → ") + " (ok)")      // le chemin seulement, jamais le message
        if (cs.isNotEmpty()) { out.add("  " + t("on.mesh.detour", "n" to cs.size)); noter(jeu, "detour", "${cs.size} ${t("on.mesh.coupes_mot")} (ok)") }
        if (defi) {
            val nb = defiCoupes(jeu)
            if (nb >= coupesDefi()) { noter(jeu, "defi", "$dest $nb (ok)"); out += listOf("", "🌩 " + t("on.defi.reussi", "n" to nb)) }
            else { noter(jeu, "defi", "$dest $nb (peu)"); out.add("  " + t("on.defi.pas_assez", "n" to nb, "total" to coupesDefi())) }
        }
        return out
    }

    fun lignesCoupe(jeu: Jeu, args: List<String>): List<String> {
        val cs = coupes(jeu).toMutableList()
        val a = args.map { it.lowercase() }
        if (a.isNotEmpty() && a[0] in listOf("-r", "--rallume", "rallume", "allume")) {
            val qui = a.getOrNull(1)
            if (qui != null) { mettreCoupes(jeu, cs.filter { it != qui }); noter(jeu, "rallume", "$qui (ok)"); return listOf("💡 " + t("on.mesh.rallume", "nom" to qui)) }
            mettreCoupes(jeu, emptyList()); noter(jeu, "rallume", "tous (ok)"); return listOf("💡 " + t("on.mesh.rallume_tout"))
        }
        if (a.isEmpty()) return if (cs.isEmpty()) listOf(t("on.mesh.coupe.aide")) else listOf(t("on.mesh.coupes", "liste" to cs.joinToString(", ")), t("on.mesh.coupe.aide"))
        val qui = a[0]
        if (qui !in noeuds()) return listOf(t("on.mesh.inconnu", "nom" to qui), t("on.mesh.noeuds", "liste" to noeuds().joinToString(", ")))
        if (qui == "camp") return listOf(t("on.mesh.camp_coupe"))
        val cible = etat(jeu).optString("cible").ifEmpty { null }
        if (cible != null && qui == cible) return listOf(t("on.defi.pas_cible", "cible" to cible))
        if (qui in cs) return listOf(t("on.mesh.deja", "nom" to qui))
        val avant = cible?.let { route("camp", it, cs) }
        cs.add(qui); mettreCoupes(jeu, cs)
        val out = mutableListOf("🌑 " + t("on.mesh.coupe", "nom" to qui))
        noter(jeu, "coupe", "$qui (ok)")
        if (cible != null) {
            val apres = route("camp", cible, cs)
            if (avant != null && qui in avant) {
                if (apres != null) {
                    noter(jeu, "defi_coupe", "$qui (ok)")
                    out += listOf("  " + t("on.defi.coupe_ok", "n" to defiCoupes(jeu), "total" to coupesDefi()),
                        "  " + t("on.mesh.nouveau", "dest" to cible, "n" to apres.size - 1), ligneChemin(apres))
                } else { noter(jeu, "defi_coupe", "$qui (isole)"); out.add("⚠ " + t("on.defi.isole", "dest" to cible)) }
            } else {
                noter(jeu, "defi_coupe", "$qui (hors)")
                out.add("  " + t("on.defi.hors_chemin", "nom" to qui, "dest" to cible))
                if (avant != null) out.add(ligneChemin(avant))
            }
        } else out.add("  " + t(if (route("camp", "feu", cs) != null) "on.mesh.autre_chemin" else "on.mesh.plus_de_chemin"))
        return out
    }

    fun lignesDefi(jeu: Jeu): List<String> {
        val cible = defiCible(Histoire.graine(jeu))
        etat(jeu).put("cible", cible)
        mettreCoupes(jeu, emptyList())
        noter(jeu, "defi_debut", "$cible (ok)")
        val r = route("camp", cible) ?: emptyList()
        return listOf("🌩 " + t("on.defi.titre"), "") + t("on.defi.regles", "dest" to cible, "n" to coupesDefi()).split("\n").map { "  $it" } +
            listOf("", "  " + t("on.mesh.chemin", "dest" to cible, "n" to r.size - 1), ligneChemin(r))
    }

    fun lignesAdulte(jeu: Jeu): List<String> {
        noter(jeu, "adulte", "lu (ok)")
        return listOf("🧑‍🔧 " + t("on.adulte.titre"), "") + t("on.adulte.regles", "mw" to L.optInt("puissance_mw", 25),
            "pc" to g(L.optInt("cycle_pour_mille", 10) / 10.0, 3)).split("\n").map { "  $it" } +
            listOf("", "  " + t("on.tel.raconte", "outil" to "meshtastic"))
    }

    fun lignesNoeud(jeu: Jeu): List<String> { noter(jeu, "noeud", "raconte (ok)")
        return listOf("📟 " + t("on.noeud.titre"), "") + (1..5).map { "  $it. " + t("on.noeud.etape$it") } + listOf("", "  " + t("on.noeud.classe"), "  " + t("on.noeud.grands")) }

    fun lignesEcoute(jeu: Jeu): List<String> { noter(jeu, "ecoute", "lu (ok)")
        return listOf("👂 " + t("on.ecoute.titre"), "") + t("on.ecoute.regles").split("\n").map { "  $it" } + listOf("fm", "meteo", "avions").map { "  • " + t("on.ecoute.$it") } +
            ("  " + t("on.tel.raconte", "outil" to "rtl_test, rtl_433, dump1090")) }

    fun lignesAvions(jeu: Jeu): List<String> { noter(jeu, "avions", "fictifs (ok)")
        return listOf("✈ " + t("on.avions.titre"), "") + objets(o("ciel"), "avions").mapIndexed { i, a ->
            "  " + t("on.avions.ligne", "n" to i + 1, "alt" to grand(a.optLong("altitude")), "v" to a.optInt("vitesse"), "cap" to a.optInt("cap")) } +
            listOf("", "  " + t("on.avions.prive"), "  " + t("on.avions.grands")) }

    fun lignesAnonyme(jeu: Jeu): List<String> { noter(jeu, "anonyme", "lu (ok)")
        return listOf("🕶 " + t("on.anonyme.titre"), "") + t("on.anonyme.texte").split("\n").map { "  $it" } }

    /** L'entrée de la Tour en caractères : le REPLI de l'illustration B5 (le dessin graphique est OndesDessin.tour). */
    val TOUR_DESSIN = listOf("     ╱╲  )))", "    ╱╲╱╲   )))", "     ││  ~~~", "    ╱██╲", "  ▁▂▅████▅▂▁ ⚓")

    /** ondes [plan|onde|longueur|mur|traverse|reseaux|canaux|voisins|radios|spectre|regle|libre|lora|temps|vallee|messages|
     *  passerelle|maillage|choix|defi|adulte|noeud|ecoute|avions|anonyme|mesh-route|mesh-envoie|mesh-coupe] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas((m.getOrNull(0) ?: "aide").lowercase()).replace("œ", "oe")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val l = when (sous) {
            "plan", "regles" -> TOUR_DESSIN + t("on.meuble.plan", "nom" to jeu.nom).split("\n")
            "onde" -> lignesOnde(jeu, a.joinToString(" ").ifEmpty { null })
            "longueur" -> lignesLongueur(jeu, a.joinToString(" ").ifEmpty { null })
            "mur", "murs" -> lignesMur(jeu, a.firstOrNull { it.toIntOrNull() == null }?.let { asciiBas(it.lowercase()) }, a.firstNotNullOfOrNull { it.toIntOrNull() } ?: 1)
            "traverse" -> lignesTraverse(jeu, a.getOrNull(0))
            "reseaux" -> { noter(jeu, "reseaux", "raconte (ok)"); listOf(t("on.reseaux.sans")) }
            "canaux" -> lignesCanaux(jeu)
            "voisins" -> lignesVoisins(jeu)
            "radios", "radio" -> lignesRadios(jeu)
            "spectre" -> lignesSpectre(jeu)
            "regle" -> lignesRegle(jeu, a)
            "libre", "libres" -> lignesLibre(jeu, a)
            "lora" -> lignesLora(jeu)
            "temps" -> lignesTemps(jeu)
            "vallee" -> lignesVallee(jeu, a.getOrNull(0))
            "messages" -> lignesMessages(jeu, a.getOrNull(0))
            "passerelle", "passerelles" -> lignesPasserelle(jeu)
            "maillage" -> lignesMaillage(jeu)
            "choix" -> lignesChoix(jeu, a)
            "defi" -> lignesDefi(jeu)
            "mesh-route" -> lignesRoute(jeu, a.getOrNull(0))
            "mesh-envoie" -> lignesEnvoie(jeu, a)
            "mesh-coupe" -> lignesCoupe(jeu, a)
            "adulte" -> lignesAdulte(jeu)
            "noeud", "noeuds" -> lignesNoeud(jeu)
            "ecoute" -> lignesEcoute(jeu)
            "avions", "avion" -> lignesAvions(jeu)
            "anonyme", "anonymes" -> lignesAnonyme(jeu)
            else -> TOUR_DESSIN + listOf("📡 " + t("on.aide.titre")) + t("on.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }
}
