package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Le mode classe sur le téléphone ou la tablette (idées 54, 55, 56, maquettes validées le 3 novembre) — comme
 * pc/tg/classe.py (les codes de séance), pc/tg/seance.py (la séance guidée, l'écran projecteur) et pc/tg/place.py
 * (la place de la classe, CLIENT seulement : c'est le poste de l'enseignant, un PC, qui la sert).
 * Vecteurs communs : donnees/classe/vecteurs.json (codes), vecteurs_seances.json, vecteurs_place.json ; test
 * tests/jvm/Classe.kt.
 */
object Classe {
    const val LETTRES = "ABCDEFGHJKMNPQRSTUVWXYZ"
    const val OPTIONS = "AGSV"

    fun controle(corps: String): Char {
        var s = 0L
        for ((i, c) in corps.withIndex()) s += (i + 1).toLong() * c.code
        return LETTRES[(s % LETTRES.length).toInt()]
    }

    fun fabriquer(n: Int, options: String = ""): String {
        val o = OPTIONS.filter { it in options.uppercase() }
        val corps = "%02d".format(n) + o
        return if (o.isEmpty()) "%02d-%c".format(n, controle(corps)) else "%02d-%s-%c".format(n, o, controle(corps))
    }

    /** (n, options) si le code est bon, sinon null. */
    fun lire(code: String?): Pair<Int, String>? {
        val brut = (code ?: "").filter { it.isLetterOrDigit() && it.code < 128 }.uppercase()
        val m = Regex("(\\d{2})([AGSV]*)([A-Z])").matchEntire(brut) ?: return null
        val (n, o, k) = m.destructured
        if (controle(n + o) != k[0]) return null
        if (OPTIONS.filter { it in o } != o) return null
        return n.toInt() to o
    }
}

/** La séance guidée (le déroulé de l'heure) et ce que montre l'écran projecteur. */
object Seances {
    var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    fun seance(n: Int): JSONObject? {
        val a = donnees().optJSONArray("seances") ?: return null
        for (i in 0 until a.length()) if (a.getJSONObject(i).optInt("n") == n) return a.getJSONObject(i)
        return null
    }

    fun numeros(): List<Int> { val a = donnees().optJSONArray("seances") ?: JSONArray(); return (0 until a.length()).map { a.getJSONObject(it).getInt("n") } }

    fun e(jeu: Jeu): JSONObject? = jeu.extra.optJSONObject("classe_seance")?.takeIf { seance(it.optInt("n")) != null }

    fun commencer(jeu: Jeu, n: Int): Boolean {
        if (seance(n) == null) return false
        jeu.extra.put("classe_seance", JSONObject().put("n", n).put("phase", 0).put("commande", JSONObject.NULL).put("vue", JSONObject.NULL))
        return true
    }

    fun agir(jeu: Jeu, quoi: String, arg: Int? = null): Boolean {
        val e = e(jeu) ?: return false
        val nb = seance(e.getInt("n"))!!.getJSONArray("phases").length()
        val k = e.optInt("phase")
        when (quoi) {
            "suivante" -> e.put("phase", minOf(nb - 1, k + 1)).put("vue", JSONObject.NULL)
            "precedente" -> e.put("phase", maxOf(0, k - 1)).put("vue", JSONObject.NULL)
            "phase" -> e.put("phase", ((arg ?: 1) - 1).coerceIn(0, nb - 1)).put("vue", JSONObject.NULL)
            "question", "trace" -> e.put("vue", if (e.optString("vue") == quoi) JSONObject.NULL else quoi)
            "commande" -> e.put("commande", !(modele(e)["commande_visible"] as Boolean))
            "fin" -> jeu.extra.remove("classe_seance")
            else -> return false
        }
        return true
    }

    /** Le modèle (mêmes vecteurs que seance.modele en Python). */
    fun modele(e: JSONObject): Map<String, Any> {
        val sd = seance(e.getInt("n"))!!
        val phases = sd.getJSONArray("phases")
        val k = e.optInt("phase").coerceIn(0, phases.length() - 1)
        val ph = phases.getJSONArray(k)
        val genre = ph.getString(0)
        val cmd = if (ph.length() > 2) ph.getString(2) else ""
        val code = sd.getString("code")
        val parts = code.split("-")
        val sansAide = parts.size == 3 && 'A' in parts[1]
        val visible = (e.opt("commande") as? Boolean) ?: !sansAide
        val vue = when (e.optString("vue")) { "question" -> "commun"; "trace" -> "trace"; else -> genre }
        val n = sd.getInt("n")
        fun nomPhase(p: JSONArray) = if (p.length() > 3 && p.getString(3).isNotEmpty()) t(p.getString(3)) else t("classe.phase." + p.getString(0))
        var duree = 0
        val liste = mutableListOf<List<Any>>()
        for (i in 0 until phases.length()) { val p = phases.getJSONArray(i); duree += p.getInt(1); liste.add(listOf(p.getString(0), p.getInt(1), nomPhase(p))) }
        return linkedMapOf("n" to n, "code" to code, "k" to k + 1, "total" to phases.length(), "genre" to genre, "vue" to vue,
            "minutes" to ph.getInt(1), "duree" to duree, "nom" to nomPhase(ph),
            "commande" to (if (visible) cmd else ""), "commande_cachee" to (cmd.isNotEmpty() && !visible), "commande_visible" to visible,
            "but" to t("seance.$n.but"), "question" to t("seance.$n.question"), "bulle" to t("seance.$n.bloque"),
            "piege" to t("seance.$n.piege"), "fini" to t("seance.$n.fini"), "trace" to Langue.liste("seance.$n.trace"),
            "phases" to liste)
    }

    fun chapitre(n: Int): String {
        val c = Histoire.CHAPITRES.firstOrNull { it.n == n } ?: return "$n"
        return t("esp.chapitre", "n" to n, "titre" to Histoire.nomChapitre(c.id))
    }

    fun plan(e: JSONObject): String {
        val m = modele(e)
        val out = mutableListOf(t("classe.seance.titre", "n" to m["n"], "chapitre" to chapitre(m["n"] as Int)) + "   " +
            t("classe.seance.duree", "minutes" to m["duree"], "code" to m["code"]), t("classe.seance.but", "but" to m["but"]), "")
        @Suppress("UNCHECKED_CAST")
        for ((i, p) in (m["phases"] as List<List<Any>>).withIndex()) {
            val marque = if (i + 1 < m["k"] as Int) "✓" else if (i + 1 == m["k"]) "▶" else " "
            out.add("$marque ${i + 1}  ${p[2]} · ${p[1]} min — " + t("classe.dire." + p[0], "code" to m["code"]))
            if (i + 1 == m["k"] && p[0] == "jeu") out.add("     " + t("classe.seance.attention", "piege" to m["piege"]))
        }
        out.add("")
        out.add(t("classe.seance.bloque", "bulle" to m["bulle"]))
        out.add(t("classe.seance.fini", "fini" to m["fini"]))
        if (m["commande_cachee"] == true) out.add(t("classe.seance.cachee"))
        out.add(t("classe.seance.tel"))
        return out.joinToString("\n")
    }

    fun liste(): String = (listOf(t("classe.seance.liste")) + numeros().map { n -> "  $n. ${chapitre(n)}  (${seance(n)?.optString("code")})" } +
        listOf(t("classe.seance.usage"))).joinToString("\n")

    /** `classe seance [N | suivante | precedente | phase K | question | trace | commande | fin | liste]` */
    fun commande(jeu: Jeu, args: List<String>): String {
        val a0 = args.firstOrNull()?.lowercase() ?: ""
        val mots = mapOf("suivante" to "suivante", "next" to "suivante", "precedente" to "precedente", "précédente" to "precedente",
            "prev" to "precedente", "question" to "question", "trace" to "trace", "commande" to "commande", "fin" to "fin", "end" to "fin", "phase" to "phase")
        if (a0 == "liste" || a0 == "list") return liste()
        a0.toIntOrNull()?.let { n ->
            if (!commencer(jeu, n)) return t("classe.seance.inconnue", "n" to n) + "\n" + liste()
            jeu.sauver(); return plan(e(jeu)!!)
        }
        mots[a0]?.let { q ->
            if (q == "phase" && args.getOrNull(1)?.toIntOrNull() == null) return t("classe.seance.usage")
            if (!agir(jeu, q, args.getOrNull(1)?.toIntOrNull())) return t("classe.seance.aucune") + "\n" + liste()
            jeu.sauver()
            return if (q == "fin") t("classe.seance.finie") else plan(e(jeu)!!)
        }
        return e(jeu)?.let { plan(it) } ?: liste()
    }
}

/** La place de la classe, vue d'un téléphone ou d'une tablette (client seulement ; mêmes règles que place.py). */
object Place {
    const val PORT = 47110
    const val PORT_ANNONCE = 47111
    val GESTES = listOf("coucou", "bravo", "danse")
    val SYMBOLES = listOf("☺", "★", "♪")
    val STADES = listOf("oeuf", "bebe", "ado", "adulte", "ancien")
    const val PAS_GESTE = 3000L
    private val ESPECE = Regex("^[a-z0-9_]{1,32}$")

    /** Une adresse IPv4 du réseau local (10, 172.16-31, 192.168) ou de l'appareil (127) ; tout le reste est refusé. */
    fun privee(ip: String?): Boolean {
        val m = Regex("(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})").matchEntire(ip ?: "") ?: return false
        val (a, b, c, d) = m.destructured.toList().map { it.toInt() }
        if (maxOf(a, b, c, d) > 255) return false
        return a == 10 || (a == 172 && b in 16..31) || (a == 192 && b == 168) || a == 127
    }

    fun cle(code: String?): String? {
        val d = Classe.lire(code) ?: return null
        if ('V' !in d.second) return null
        val h = java.security.MessageDigest.getInstance("SHA-256").digest(("terminagotchi-place:" + Classe.fabriquer(d.first, d.second)).toByteArray())
        return h.joinToString("") { "%02x".format(it) }.take(8)
    }

    fun profilValide(p: JSONObject?): JSONObject? {
        if (p == null) return null
        val e = p.opt("espece") as? String ?: return null
        val s = p.opt("stade") as? String ?: return null
        val n = p.opt("niveau")
        if (!ESPECE.matches(e) || s !in STADES || n !is Int || n !in 0..999) return null
        return JSONObject().put("espece", e).put("stade", s).put("niveau", n)
    }

    fun profil(jeu: Jeu): JSONObject {
        val st = jeu.stade
        val e = jeu.extra.optString("espece_compagnon").take(32)
        return JSONObject().put("espece", if (st == 0 || e.isEmpty()) "oeuf" else e)
            .put("stade", if (st == 0) "oeuf" else Sprites.STADE_ESPECE[st] ?: "adulte").put("niveau", minOf(999, jeu.niveau))
    }

    fun nomEspece(e: String) = if (e == "oeuf") t("classe.place.oeuf") else Bestiaire.espece(e)?.nom ?: "?"
    fun nomStade(s: String) = t(when (s) { "oeuf" -> "stade.0"; "bebe" -> "stade.1"; "ado" -> "stade.2"; "adulte" -> "stade.3"; else -> "stade_bestiole.ancien" })

    /** Une demande à la place (une ligne JSON, une ligne en réponse) ; null si elle ne répond pas. */
    fun demander(hote: String?, port: Int, req: JSONObject, delai: Int = 3000): JSONObject? {
        if (!privee(hote)) return null
        return try {
            java.net.Socket().use { s ->
                s.connect(java.net.InetSocketAddress(hote, port), delai)
                s.soTimeout = delai
                s.getOutputStream().write((req.toString() + "\n").toByteArray())
                val ligne = s.getInputStream().bufferedReader().readLine() ?: return null
                if (ligne.length > 64 * 1024) null else JSONObject(ligne)
            }
        } catch (e: Exception) { null }
    }

    /** L'annonce d'une place de cette clé sur le réseau local : (ip, port) ou null. */
    fun decouvrir(cle: String, delai: Int = 5000): Pair<String, Int>? = try {
        java.net.DatagramSocket(null).use { s ->
            s.reuseAddress = true
            s.bind(java.net.InetSocketAddress(PORT_ANNONCE))
            s.soTimeout = delai
            val fin = System.currentTimeMillis() + delai
            var r: Pair<String, Int>? = null
            while (r == null && System.currentTimeMillis() < fin) {
                val p = java.net.DatagramPacket(ByteArray(1024), 1024)
                try { s.receive(p) } catch (e: java.net.SocketTimeoutException) { break }
                val ip = p.address?.hostAddress ?: continue
                val a = try { JSONObject(String(p.data, 0, p.length)) } catch (e: Exception) { continue }
                if (a.optString("tg") == "place" && a.optString("cle") == cle && privee(ip) && a.opt("port") is Int) r = ip to a.getInt("port")
            }
            r
        }
    } catch (e: Exception) { null }

    class Poste(val poste: Int, val espece: String, val stade: String, val niveau: Int)

    /** La place vue de ce téléphone : rejointe, relue toutes les 2 s dans un fil à part (rien ne bloque l'écran). */
    class Client(code: String, val profil: JSONObject, var hote: String? = null, var port: Int = PORT) {
        val cle = cle(code)
        var jeton: String? = null
        var poste: Int? = null
        @Volatile var postes = listOf<Poste>()
        @Volatile var recus = listOf<Triple<Int, Int, Long>>()   // (geste, de, quand)
        @Volatile var etat = "cherche"
        @Volatile var message = ""
        private var dernierId = 0
        private var attends = 0L

        fun rejoindre(): Boolean {
            val k = cle ?: run { etat = "absente"; return false }
            if (hote == null) { val tr = decouvrir(k) ?: run { etat = "absente"; return false }; hote = tr.first; port = tr.second }
            val rep = demander(hote, port, JSONObject().put("cle", k).put("quoi", "entrer").put("profil", profil).put("jeton", jeton ?: JSONObject.NULL))
            if (rep == null || !rep.optBoolean("ok")) { etat = if (rep?.optString("erreur") == "fermee") "fermee" else "absente"; return false }
            poste = rep.getInt("poste"); jeton = rep.getString("jeton"); etat = "ici"
            return relire()
        }

        fun relire(): Boolean {
            val rep = demander(hote, port, JSONObject().put("cle", cle).put("quoi", "place").put("jeton", jeton).put("depuis", dernierId))
            if (rep == null || !rep.optBoolean("ok")) { etat = if (rep?.optString("erreur") == "fermee") "fermee" else "absente"; return false }
            etat = "ici"
            val ps = mutableListOf<Poste>()
            val a = rep.optJSONArray("postes") ?: JSONArray()
            for (i in 0 until a.length()) {
                val x = a.optJSONObject(i) ?: continue
                val p = profilValide(x) ?: continue
                if (x.opt("poste") !is Int) continue
                ps.add(Poste(x.getInt("poste"), p.getString("espece"), p.getString("stade"), p.getInt("niveau")))
            }
            postes = ps
            val r = recus.toMutableList()
            val rr = rep.optJSONArray("recus") ?: JSONArray()
            for (i in 0 until rr.length()) {
                val x = rr.optJSONObject(i) ?: continue
                val g = x.opt("g") as? Int ?: continue
                if (g !in 0..2 || x.opt("id") !is Int) continue
                r.add(Triple(g, x.optInt("de"), System.currentTimeMillis()))
                dernierId = maxOf(dernierId, x.getInt("id"))
            }
            recus = r.takeLast(6)
            return true
        }

        fun geste(a: Int, g: Int): Boolean {
            if (etat != "ici" || g !in 0..2 || System.currentTimeMillis() - attends < PAS_GESTE) return false
            attends = System.currentTimeMillis()
            val rep = demander(hote, port, JSONObject().put("cle", cle).put("quoi", "geste").put("jeton", jeton).put("a", a).put("g", g))
            return rep?.optBoolean("ok") == true
        }
    }
}

/** La carte de visite de la créature (idée 58) : le contenu (mêmes vecteurs que carte_visite.py). */
object CarteVisite {
    const val W = 750f
    const val H = 1050f

    fun preferes(compteurs: JSONObject?, ordre: List<String>, n: Int = 4): List<String> {
        val rang = ordre.withIndex().associate { it.value to it.index }
        val cles = compteurs?.keys()?.asSequence()?.filter { (compteurs.opt(it) as? Int ?: 0) > 0 }?.toList() ?: emptyList()
        if (cles.isEmpty()) return ordre.take(n)
        return cles.sortedWith(compareBy<String>({ -compteurs!!.getInt(it) }, { rang[it] ?: 1_000_000 }, { it })).take(n)
    }

    fun jours(ne: Long, maintenant: Long): Int = if (ne <= 0) 0 else maxOf(1, ((maintenant - ne) / 86400).toInt() + 1)

    fun contenu(jeu: Jeu, avecNom: Boolean): Map<String, Any> {
        val e = Bestiaire.espece(jeu.extra.optString("espece_compagnon"))
        val ne = jeu.extra.optLong("born")
        val titres = try { Entrainement.titres(jeu).take(3).map { it.texte to it.couleur } } catch (x: Exception) { emptyList() }
        return linkedMapOf("nom" to (if (avecNom) jeu.nom else ""), "espece" to (e?.nom ?: ""), "stade" to t("stade.${jeu.stade}"),
            "type" to (e?.famille ?: ""), "niveau" to jeu.niveau, "jours" to jours(ne, System.currentTimeMillis() / 1000),
            "commandes" to jeu.total, "gouts" to preferes(jeu.extra.optJSONObject("gouts"), jeu.vus.toList()),
            "eclos" to (if (ne > 0) java.text.SimpleDateFormat("dd/MM/yyyy", java.util.Locale.ROOT).format(java.util.Date(ne * 1000)) else ""),
            "titres" to titres)
    }
}
