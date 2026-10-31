package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * ⚓ Le Port — réseaux (docs/programme.md § 2.12 et § 7.2), portage de pc/tg/port.py.
 *
 * Le réseau simulé du Terminaworld (assets/port.json, copie de donnees/port.json) : chaque biome est une machine
 * (feu.terminaworld 127.42.0.2…), la Racine est le routeur, le camp de base est localhost. Mêmes règles que sur PC
 * (route, guidage d'un messager, course TCP / UDP, couches, gardien, sceaux) : vecteurs communs
 * donnees/port/vecteurs.json, vérifiés par tests/jvm/Port.kt.
 *
 * Sur le téléphone, le programme prévoit des commandes intégrées (Commandes.kt) qui restent DANS le téléphone :
 *  - `curl` : un vrai petit client HTTP (une vraie connexion TCP, la requête écrite telle qu'elle part, `-I`, `-s`,
 *    `-o`, `-v`), seulement vers 127.0.0.1 / localhost : le phare du port (8042) et ta lanterne (8000) ;
 *  - `serveur 8000` / `serveur stop` : ta lanterne, un vrai petit serveur HTTP attaché à 127.0.0.1 qui sert le
 *    dossier port/quai (jamais un autre dossier) ;
 *  - `nslookup` / `host` : l'annuaire du port et localhost, jamais Internet ;
 *  - `ss` : les portes que Terminagotchi a ouvertes (le phare, ta lanterne) ;
 *  - `port …` : la carte, l'annuaire, la route, le messager, les phares, la course, les couches, le gardien, les sceaux.
 * Un petit filtre comprend `| head -n N`, `| grep mot` et `| wc -l` après ces commandes (les tuyaux des leçons).
 * Le téléporteur ssh est raconté (⛔ sur le téléphone), la lanterne remplace python3 -m http.server.
 */
object Port {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("port.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    class Machine(val id: String, val adresse: String, val nom: String?, val icone: String, val role: String)

    fun machines(): List<Machine> {
        val a = donnees().optJSONArray("machines") ?: JSONArray()
        return (0 until a.length()).map { a.getJSONObject(it) }.map {
            Machine(it.getString("id"), it.getString("adresse"), it.optString("nom").ifEmpty { null }, it.optString("icone"), it.optString("role"))
        }
    }

    fun ids() = machines().map { it.id }
    fun machine(id: String?) = machines().firstOrNull { it.id == id }
    fun nomComplet(id: String): String = machine(id)?.let { it.nom ?: "$id.${donnees().optString("domaine")}" } ?: id

    /** feu, feu.terminaworld, 127.42.0.2, localhost, camp → l'identifiant de la machine, ou null. */
    fun chercher(nom: String?): String? {
        val n = (nom ?: "").trim().lowercase().trimEnd('.')
        for (m in machines()) if (n == m.id || n == m.adresse || n == nomComplet(m.id) || n == (m.nom ?: "\u0000")) return m.id
        return if (n == "127.0.0.1") "camp" else null
    }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    fun liens(): List<Pair<String, String>> {
        val a = donnees().optJSONArray("liens") ?: JSONArray()
        return (0 until a.length()).map { a.getJSONArray(it).let { l -> l.getString(0) to l.getString(1) } }
    }
    fun ttl() = donnees().optInt("ttl", 8)
    fun portPhare() = donnees().optJSONObject("phare")?.optInt("port", 8042) ?: 8042
    fun portSceau() = donnees().optJSONObject("phare")?.optInt("sceau", 8443) ?: 8443

    // ---------------------------------------------------------------- le réseau simulé (spécification pure)
    fun voisins(id: String, eteints: Collection<String> = emptyList()): List<String> = liens().mapNotNull { (a, b) ->
        when { a == id && b !in eteints -> b; b == id && a !in eteints -> a; else -> null }
    }

    fun relies(a: String, b: String) = liens().any { (x, y) -> (x == a && y == b) || (x == b && y == a) }

    /** Le chemin le plus court (en sauts), en évitant les phares éteints ; à égalité, l'ordre des liens décide. */
    fun route(depart: String, arrivee: String, eteints: Collection<String> = emptyList()): List<String>? {
        if (depart in eteints || arrivee in eteints) return null
        val avant = LinkedHashMap<String, String?>()
        avant[depart] = null
        val file = ArrayDeque<String>().apply { add(depart) }
        while (file.isNotEmpty()) {
            val x = file.removeFirst()
            if (x == arrivee) {
                val c = mutableListOf(x)
                while (avant[c.last()] != null) c.add(avant[c.last()]!!)
                return c.reversed()
            }
            for (v in voisins(x, eteints)) if (v !in avant) { avant[v] = x; file.add(v) }
        }
        return null
    }

    /** La table de routage d'une machine : (destination, passerelle, sauts). */
    fun table(id: String, eteints: Collection<String> = emptyList()): List<Triple<String, String, Int>> =
        ids().filter { it != id }.mapNotNull { d -> route(id, d, eteints)?.let { Triple(d, it[1], it.size - 1) } }

    class Guidage(val ok: Boolean, val sauts: List<String>, val raison: String, val ou: String?, val ttl: Int)

    /** Le messager suit le chemin donné par l'enfant (sans le camp) : arrive | inconnue | pas_relie | eteint | ttl | vide. */
    fun guider(chemin: List<String>, eteints: Collection<String> = emptyList(), depart: String = "camp", ttl0: Int? = null): Guidage {
        var ttl = ttl0 ?: ttl()
        var pas = chemin.map { chercher(it) ?: it }
        if (pas.isNotEmpty() && pas[0] == depart) pas = pas.drop(1)
        if (pas.isEmpty()) return Guidage(false, listOf(depart), "vide", null, ttl)
        var ici = depart
        val sauts = mutableListOf(depart)
        for (x in pas) {
            if (x !in ids()) return Guidage(false, sauts, "inconnue", x, ttl)
            if (!relies(ici, x)) return Guidage(false, sauts, "pas_relie", x, ttl)
            if (x in eteints) return Guidage(false, sauts, "eteint", x, ttl)
            if (ttl <= 0) return Guidage(false, sauts, "ttl", x, ttl)
            ttl--
            sauts.add(x)
            ici = x
        }
        return Guidage(true, sauts, "arrive", ici, ttl)
    }

    class Course(val tcpRecus: List<Int>, val tcpEnvois: Int, val renvoyes: List<Int>, val udpRecus: List<Int>, val perdus: List<Int>)

    /** La course TCP / UDP (P8), comme course() sur PC. */
    fun course(): Course {
        val c = donnees().optJSONObject("course") ?: JSONObject()
        val n = c.optInt("paquets", 6)
        val perdus = liste(c, "perdus").map { it.toInt() }
        val des = liste(c, "desordre").map { it.toInt() }
        val udp = (1..n).filter { it !in perdus }.toMutableList()
        if (des.size == 2 && des.all { it in udp }) {
            val a = udp.indexOf(des[0]); val b = udp.indexOf(des[1])
            val x = udp[a]; udp[a] = udp[b]; udp[b] = x
        }
        return Course((1..n).toList(), n + perdus.size, perdus, udp, perdus)
    }

    private val SANS_ACCENT = mapOf('é' to 'e', 'è' to 'e', 'ê' to 'e', 'à' to 'a', 'ç' to 'c', 'ô' to 'o', 'û' to 'u', 'î' to 'i')

    /** Les 4 couches dans l'ordre (application, transport, réseau, liaison), comme couches_ok() sur PC. */
    fun couchesOk(texte: String?): Boolean {
        val bas = (texte ?: "").lowercase().map { SANS_ACCENT[it] ?: it }.joinToString("")
        val syn = mapOf("internet" to "reseau", "network" to "reseau", "lien" to "liaison", "link" to "liaison", "physique" to "liaison",
            "liaisons" to "liaison")
        val couches = liste(donnees(), "couches")
        val mots = Regex("[a-zà-ÿ]+").findAll(bas).map { syn[it.value] ?: it.value }.filter { it in couches }.toList()
        return mots == couches
    }

    class Gardien(val box: String, val publique: String, val baux: List<Pair<String, String>>)

    fun gardien(): Gardien {
        val g = donnees().optJSONObject("gardien") ?: JSONObject()
        val base = g.optString("box").substringBeforeLast('.')
        val premier = g.optInt("premier", 23)
        return Gardien(g.optString("box"), g.optString("publique"), liste(g, "appareils").mapIndexed { i, a -> a to "$base.${premier + i}" })
    }

    /** Les 4 sceaux dans l'ordre de cette partie (même mélange que random.Random(f"sceaux:{graine}").shuffle). */
    fun sceaux(graine: String): List<Pair<Int, JSONObject>> {
        val a = donnees().optJSONArray("sceaux") ?: JSONArray()
        val l = (0 until a.length()).map { a.getJSONObject(it) }.toMutableList()
        PyHasard("sceaux:$graine").melanger(l)
        return l.mapIndexed { i, x -> (i + 1) to x }
    }

    fun vraiSceau(graine: String) = sceaux(graine).first { it.second.optString("raison") == "ok" }.first

    /** L'annuaire du port, au format de /etc/hosts. */
    fun annuaire(): List<String> = machines().map {
        if (it.id == "camp") "${it.adresse}\tlocalhost camp" else "${it.adresse}\t${nomComplet(it.id)} ${it.id}"
    }

    /** La réponse du phare à GET chemin : (code, corps). Rien d'autre que des pages fabriquées ici. */
    fun page(chemin: String?, hote: String? = null): Pair<Int, String> {
        var c = (chemin ?: "/").substringBefore('?').trim('/').lowercase()
        if (c.isEmpty() && hote != null) chercher(hote.substringBefore(':'))?.let { if (it != "camp") c = it }
        if (c.isEmpty()) {
            val l = mutableListOf(t("port.page.accueil"))
            for (m in machines()) l.add("/${m.id.padEnd(8)} ${m.icone} ${nomComplet(m.id)} (${m.adresse})")
            return 200 to l.joinToString("\n") + "\n"
        }
        if (c == "courrier")                        // la Citadelle (le faux facteur) : le vrai courrier du capitaine
            return 200 to t("cit.page.courrier") + "\n" + t("port.page.pied", "port" to portPhare()) + "\n"
        val id = chercher(c)
        if (id != null && id in liste(donnees(), "pages")) {
            val m = machine(id)!!
            return 200 to "${m.icone} ${nomComplet(id)} (${m.adresse})\n" + t("port.page.$id") + "\n" + t("port.page.pied", "port" to portPhare()) + "\n"
        }
        return 404 to t("port.page.404", "chemin" to "/$c") + "\n"
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour : quand le port s'ouvre
    private fun besoin(): List<String> {
        val P = Programme.donnees()
        val ms = P.optJSONArray("mondes") ?: JSONArray()
        val m = (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "port" } ?: return emptyList()
        val tronc = P.optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct()
    }

    /** Les prérequis du Port (programme.json : mondes → port → requis, traduits par « tronc » en chapitres). */
    fun ouvert(jeu: Jeu) = besoin().all { Histoire.fini(jeu, it) }
    fun manque(jeu: Jeu) = besoin().filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) }

    /** Le Port vient de s'ouvrir : la créature le dit une fois. */
    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "port" } || Histoire.fini(jeu, "port") || !ouvert(jeu)) return false
        deja.put("port")
        jeu.log(t("port.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "port.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet de bord
    fun etat(jeu: Jeu): JSONObject {
        val p = jeu.module("port")
        if (p.optJSONArray("eteints") == null) p.put("eteints", JSONArray())
        if (p.optJSONArray("releves") == null) p.put("releves", JSONArray())
        return p
    }

    fun eteints(jeu: Jeu): MutableList<String> = liste(etat(jeu), "eteints").toMutableList()
    private fun mettreEteints(jeu: Jeu, l: List<String>) { etat(jeu).put("eteints", JSONArray(l)) }

    const val CARNET = "carnet_de_bord.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "port")

    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }

    /** Un indice du Port (Histoire.indice), comme port.indice en Python : un trou « … » ou « ? » recopié, la liste
     *  relue (la règle), un messager perdu, un faux sceau (la dernière ligne [guide] ou [sceau] du carnet). */
    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if ("localhost" in e.cmd) for ((l, _) in tapees) {          // http://locahost:8042 : le tuyau | head cache l'erreur
            for (m in Regex("https?://([^/:\\s]+)").findAll(l)) {
                val hote = m.groupValues[1]
                if (hote != "localhost" && !hote.startsWith("127.")) return t("dress.indice.faute", "tape" to hote, "attendu" to "localhost")
            }
        }
        val eti = when {
            e.cmd.startsWith("port guide") -> "guide"
            e.cmd.startsWith("port sceau") -> "sceau"
            else -> return null
        }
        val lignes = tapees.map { it.first.trim() }.filter { Regex("^(tg\\s+)?port\\s+(guide|sceau)\\b").containsMatchIn(it) }
        if (lignes.isEmpty()) return null
        if (lignes.any { Regex("(…|\\.\\.\\.|\\?|<)").containsMatchIn(it) }) return t("port.indice.remplace")
        if (lignes.all { val m = it.split(Regex("\\s+")); m.size <= (if (m[0] == "tg") 3 else 2) })
            return t(if (eti == "guide") "port.guide.aide" else "port.sceau.aide")
        val der = carnet(jeu).lines().lastOrNull { it.startsWith("[$eti]") }
        if (der != null && Regex("\\((perdu|faux)\\)\\s*$").containsMatchIn(der)) return t("port.indice.$eti")
        return null
    }

    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok") =
        Regex("^\\[$etiquette].*\\b$mot\\b", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf(
        "port/panneau.txt" to t("port.meuble.panneau", "nom" to jeu.nom),
        "port/annuaire.txt" to annuaire().joinToString("\n"),
        "port/$CARNET" to t("port.meuble.carnet") + "\n",
        "port/quai/LISEZ_MOI.txt" to t("port.meuble.quai"),
        "port/teleporteur.txt" to t("port.meuble.teleporteur"))

    val LECONS_PHARE = setOf("port2", "port3", "port5", "port6", "port7", "port10", "port11")   // et celles juste avant (comme sur PC)

    /** Appelé par Histoire.meubler : le phare s'allume pour les leçons qui le visitent. */
    fun meubler(jeu: Jeu, lid: String?) {
        if (lid in LECONS_PHARE && dossier(jeu).isDirectory) Phare.allumer(portPhare(), Phare.Genre.PHARE, jeu)
    }

    // ---------------------------------------------------------------- les leçons
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir|gci|get-childitem)\\b"
    private const val LIRE = "^(cat|type|gc|get-content|less|more|head|tail)\\b"
    private const val CURL = "^(curl|curl\\.exe)\\b"
    private const val PORT = "^(tg\\s+)?port\\s+"

    private fun n(lid: String, i: Int, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  cree: String? = null, exploit: String? = null) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, cree, ou, exploit = exploit)

    private fun contient(rel: String, motif: String): (Jeu) -> Boolean = { j ->
        try { Regex(motif, RegexOption.IGNORE_CASE).containsMatchIn(File(j.terrain, rel).readText()) } catch (e: Exception) { false }
    }

    val IDS = (0..11).map { "port$it" }
    private const val U = "http://localhost:8042"

    /** Les leçons du Port sur le téléphone (mêmes clés que le PC ; « hista.portX.i » quand la commande diffère). */
    fun lecons(jeu: Jeu): Map<String, Lecon> = linkedMapOf(
        "port0" to Lecon("hist.port0.titre", null, 1, listOf(
            Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/port", "hist.entree.bravo", ici = "port", params = mapOf("piece" to "port")),
            n("port0", 1, "ls", re = LS, ou = "port"),
            n("port0", 2, "cat panneau.txt", re = "$LIRE.*panneau"),
        )),
        "port1" to Lecon("hist.port1.titre", null, 1, listOf(
            n("port1", 0, "hostname", re = "^hostname\\b"),
            n("port1", 1, "ifconfig", re = "^(ifconfig|ip\\s+(-\\d\\s+)?a(ddr)?\\b)"),
            n("port1", 2, "ping -c 3 localhost", re = "^ping\\b.*\\b(localhost|127\\.0\\.0\\.1)\\b"),
        )),
        "port2" to Lecon("hist.port2.titre", null, 1, listOf(
            n("port2", 0, "cat /etc/hosts", re = "^(cat|less|more|head)\\b.*hosts\\b"),
            n("port2", 1, "nslookup localhost", re = "^(nslookup|host|getent\\s+hosts)\\b.*localhost"),
            n("port2", 2, "grep feu annuaire.txt", re = "^(grep)\\b.*\\bfeu\\b.*annuaire"),
        )),
        "port3" to Lecon("hist.port3.titre", null, 1, listOf(
            n("port3", 0, "curl -I $U/", re = "$CURL.*(\\s-\\w*I\\b|\\s--head\\b).*(localhost|127\\.0\\.0\\.1):8042"),
            n("port3", 1, "curl -s $U/eau | head -n 3", re = "$CURL.*(localhost|127\\.0\\.0\\.1):8042/eau\\b.*\\|\\s*head\\b"),
            n("port3", 2, "curl -o colis.html $U/feu", fs = contient("port/colis.html", "feu\\.terminaworld"), cree = "port/colis.html"),
            n("port3", 3, "curl -I $U/volcan_perdu", re = "$CURL.*(\\s-\\w*I\\b|\\s--head\\b).*8042/(?!(eau|feu|glace|plante|roche|ciel|ombre|machine|poison|racine|camp)\\b)\\w"),
        )),
        // ⛔ pas de ssh sur le téléphone : le téléporteur est raconté
        "port4" to Lecon("hist.port4.titre", null, 1, listOf(
            n("port4", 0, "port teleporteur", re = "${PORT}t[eé]l[eé]porteur\\b"),
            n("port4", 1, "cat teleporteur.txt", re = "$LIRE.*teleporteur"),
        )),
        "port5" to Lecon("hist.port5.titre", null, 1, listOf(
            n("port5", 0, "echo \"Bienvenue sur mon quai\" > quai/index.html", fs = contient("port/quai/index.html", "\\S"), cree = "port/quai/index.html"),
            n("port5", 1, "serveur 8000", re = "^serveur\\s+8000\\b"),
            n("port5", 2, "curl http://localhost:8000", re = "$CURL.*(localhost|127\\.0\\.0\\.1):8000"),
            n("port5", 3, "serveur stop", re = "^serveur\\s+(stop|arret|off)\\b"),
        )),
        "port6" to Lecon("hist.port6.titre", null, 1, listOf(
            n("port6", 0, "curl -v $U/", re = "$CURL.*\\s-\\w*v\\b.*8042"),
            n("port6", 1, "port couches", re = "${PORT}couches\\b"),
            n("port6", 2, "echo \"application transport reseau liaison\" > couches.txt",
                fs = { j -> couchesOk(try { File(j.terrain, "port/couches.txt").readText() } catch (e: Exception) { "" }) }, cree = "port/couches.txt"),
        )),
        "port7" to Lecon("hist.port7.titre", null, 1, listOf(
            n("port7", 0, "ss -tln", re = "^ss\\s+-\\w*l"),
            n("port7", 1, "ss -tln | grep 8042", re = "^ss\\b.*\\|\\s*grep\\s+\\S*8042"),
            n("port7", 2, "port carte", re = "${PORT}carte\\b"),
        )),
        "port8" to Lecon("hist.port8.titre", null, 1, listOf(
            n("port8", 0, "ss -t", re = "^ss\\s+-\\w*t"),
            n("port8", 1, "ss -u", re = "^ss\\s+-\\w*u"),
            n("port8", 2, "port course", re = "${PORT}course\\b"),
        )),
        "port9" to Lecon("hist.port9.titre", null, 1, listOf(
            n("port9", 0, "port route", re = "${PORT}route\\b"),
            n("port9", 1, "ping -c 3 127.0.0.1", re = "^ping\\b.*127\\.0\\.0\\.1"),
            n("port9", 2, "port messager feu", re = "${PORT}messager\\s+\\S+"),
            n("port9", 3, "port eteins roche", re = "${PORT}[eé]teins\\s+roche\\b"),
            n("port9", 4, "port guide racine … feu", fs = { j -> dansCarnet(j, "guide") }, exploit = "port.messager"),
        )),
        "port10" to Lecon("hist.port10.titre", null, 1, listOf(
            n("port10", 2, "port gardien", re = "${PORT}gardien\\b"),
        )),
        "port11" to Lecon("hist.port11.titre", null, 1, listOf(
            n("port11", 2, "port sceau", re = "${PORT}sceau\\s*$"),
            n("port11", 3, "port sceau ?", fs = { j -> dansCarnet(j, "sceau") }, exploit = "port.sceau"),
        )),
    )

    // ---------------------------------------------------------------- les commandes du jeu : port …
    private fun ligneMachine(id: String, eteints: Collection<String>): String {
        val m = machine(id)!!
        val base = "${m.icone} ${nomComplet(id).padEnd(20)} ${m.adresse.padEnd(12)}"
        return if (id in eteints) "$base ✖ ${t("port.eteint")}" else base
    }

    fun carte(jeu: Jeu): List<String> {
        val e = eteints(jeu)
        val out = mutableListOf("⚓ " + t("port.carte.titre"), "")
        for (m in machines()) out.add("  " + ligneMachine(m.id, e) + " ⇄ " + voisins(m.id).joinToString(", "))
        out.add("")
        out.add("  " + t("port.carte.aide"))
        noter(jeu, "carte", t("port.carnet.carte", "n" to machines().size))
        return out
    }

    private fun animSaut(chemin: List<String>, ok: Boolean, ou: String?): List<String> {
        val m = chemin.map { x -> machine(x)?.let { "${it.icone} $x" } ?: x }
        var l = "  " + m.joinToString(" ─✉→ ")
        if (!ok && ou != null) l += " ─✖ $ou"
        val out = mutableListOf(l)
        if (ok) out.add("  " + m.reversed().joinToString(" ←✉─ ") + "  ↩ " + t("port.retour"))
        return out
    }

    fun messager(jeu: Jeu, dest: String): List<String> {
        val id = chercher(dest) ?: return listOf(t("port.inconnue", "nom" to dest), t("port.carte.aide"))
        val r = if (id == "camp") listOf("camp") else route("camp", id, eteints(jeu))
        if (r == null) {
            noter(jeu, "messager", "camp → $id : ${t("port.perdu")} (perdu)")
            return listOf("✉ " + t("port.messager.perdu", "dest" to nomComplet(id)), "  " + t("port.messager.pas_de_route"))
        }
        val out = mutableListOf("✉ " + t("port.messager.part", "dest" to nomComplet(id), "adresse" to machine(id)!!.adresse, "ttl" to ttl()))
        out += animSaut(r, true, null)
        out.add("  " + t("port.messager.arrive", "n" to r.size - 1, "ttl" to ttl() - (r.size - 1)))
        noter(jeu, "messager", "${r.joinToString(" → ")} : ${r.size - 1} ${t("port.sauts")} (ok)")
        val rel = (liste(etat(jeu), "releves") + r).distinct().sorted()
        etat(jeu).put("releves", JSONArray(rel))
        return out
    }

    fun eteindre(jeu: Jeu, nom: String?, allumer: Boolean = false): List<String> {
        if (allumer && nom == null) {
            mettreEteints(jeu, emptyList())
            noter(jeu, "phare", t("port.tous_allumes") + " (ok)")
            return listOf("💡 " + t("port.tous_allumes"))
        }
        val x = chercher(nom ?: "")
        if (x == null || x == "camp") return listOf(t("port.inconnue", "nom" to (nom ?: "?")))
        val e = eteints(jeu)
        if (allumer) {
            mettreEteints(jeu, e.filter { it != x })
            noter(jeu, "phare", "$x : ${t("port.allume")} (ok)")
            return listOf("💡 " + t("port.phare.allume", "nom" to x))
        }
        if (x !in e) e.add(x)
        mettreEteints(jeu, e)
        noter(jeu, "eteint", "$x (ok)")
        val autre = route("camp", "feu", e)
        return listOf("🌑 " + t("port.phare.eteint", "nom" to x), "  " + t(if (autre != null) "port.phare.detour" else "port.phare.coupe"))
    }

    fun guide(jeu: Jeu, chemin: List<String>): List<String> {
        var e = eteints(jeu)
        if (e.isEmpty()) { e = mutableListOf(donnees().optString("panne", "roche")); mettreEteints(jeu, e) }
        val g = guider(chemin, e)
        val out = animSaut(g.sauts, g.ok, g.ou).toMutableList()
        if (g.ok) {
            out.add(0, "✉ " + t("port.guide.ok", "dest" to nomComplet(g.sauts.last()), "n" to g.sauts.size - 1, "ttl" to g.ttl))
            noter(jeu, "guide", "${g.sauts.joinToString(" → ")} : ${t("port.sans_perte")} (ok)")
        } else {
            out.add(0, "✉ " + t("port.guide.${g.raison}", "ou" to (g.ou ?: ""), "ici" to g.sauts.last()))
            noter(jeu, "guide", "${g.sauts.joinToString(" → ")} ✖ ${g.ou ?: ""} (perdu)")
        }
        return out
    }

    fun lignesCourse(jeu: Jeu): List<String> {
        val c = course()
        noter(jeu, "course", "TCP " + c.tcpRecus.joinToString(" ") + " | UDP " + c.udpRecus.joinToString(" ") + " (ok)")
        return listOf("🏁 " + t("port.course.titre"), "",
            "  📨 TCP  " + c.tcpRecus.joinToString(" ") { "[$it]" } + "   " + t("port.course.tcp", "envois" to c.tcpEnvois, "renvoyes" to c.renvoyes.joinToString(", ")),
            "  📮 UDP  " + c.udpRecus.joinToString(" ") { "[$it]" } + "   " + t("port.course.udp", "perdus" to c.perdus.joinToString(", ")),
            "", "  " + t("port.course.morale"))
    }

    fun lignesCouches(jeu: Jeu): List<String> {
        val p = portPhare()
        val co = liste(donnees(), "couches")
        val contenu = mapOf("application" to "GET / HTTP/1.1 · Host: localhost:$p", "transport" to "TCP · port $p",
            "reseau" to "IP · 127.0.0.1 → 127.0.0.1", "liaison" to "lo (" + t("port.couches.boucle") + ")")
        val out = mutableListOf("✉ " + t("port.couches.titre"), "")
        co.forEachIndexed { i, c ->
            val pad = "  ".repeat(i)
            out.add("  $pad┌" + "─".repeat(30 - 2 * i) + "┐")
            out.add("  $pad│ " + t("port.couche.$c") + "  " + contenu[c])
        }
        out.add("")
        out.add("  " + t("port.couches.aide"))
        noter(jeu, "couches", co.joinToString(" > ") + " (ok)")
        return out
    }

    fun lignesGardien(jeu: Jeu): List<String> {
        val g = gardien()
        val out = mutableListOf("🏢 " + t("port.gardien.titre"), "", "  " + t("port.gardien.box", "box" to g.box))
        for ((a, adr) in g.baux) out.add("  📱 ${t("port.appareil.$a").padEnd(12)} → $adr  (DHCP)")
        out.add("  " + t("port.gardien.nat", "publique" to g.publique))
        out.add("")
        out.add("  " + t("port.gardien.limite"))
        noter(jeu, "gardien", "${g.box} : " + g.baux.joinToString(", ") { it.second } + " → ${g.publique} (ok)")
        return out
    }

    fun lignesSceau(jeu: Jeu, choix: String?): List<String> {
        val s = sceaux(Histoire.graine(jeu))
        if (choix == null) {
            val out = mutableListOf("🔏 " + t("port.sceau.titre"), "")
            for ((i, x) in s) out.add("  $i. " + t("port.sceau.ligne", "nom" to x.optString("nom"),
                "par" to t("port.sceau.par." + if (x.optString("signe_par") == "notaire") "notaire" else "lui"),
                "perime" to if (x.optString("raison") == "perime") t("port.sceau.perime") else ""))
            out.add("")
            out.add("  " + t("port.sceau.aide"))
            return out
        }
        val n = choix.trim().toIntOrNull() ?: return listOf(t("port.sceau.aide"))
        val x = s.firstOrNull { it.first == n }?.second ?: return listOf(t("port.sceau.aide"))
        if (x.optString("raison") == "ok") {
            noter(jeu, "sceau", "$n : ${t("port.sceau.verifie")} (ok)")
            return listOf("✔ " + t("port.sceau.ok"))
        }
        noter(jeu, "sceau", "$n : ${x.optString("raison")} (faux)")
        return listOf("✖ " + t("port.sceau.faux." + x.optString("raison")))
    }

    fun lignesAnnuaire(nom: String?): List<String> {
        if (nom == null) return listOf("📖 " + t("port.annuaire.titre")) + annuaire().map { "  $it" }
        val id = chercher(nom) ?: return listOf(t("port.annuaire.inconnu", "nom" to nom))
        return listOf("  ${nomComplet(id)} → ${machine(id)!!.adresse}")
    }

    fun lignesRoute(jeu: Jeu, nom: String?): List<String> {
        val x = chercher(nom ?: "camp") ?: "camp"
        val out = mutableListOf("🗺 " + t("port.route.titre", "nom" to nomComplet(x)))
        for ((d, via, n) in table(x, eteints(jeu)))
            out.add("  ${machine(d)!!.adresse.padEnd(12)} via ${machine(via)!!.adresse.padEnd(12)} ($via) $n ${t("port.sauts")}")
        return out
    }

    /** port [carte|annuaire|route|messager|eteins|rallume|guide|course|couches|gardien|sceau|teleporteur] */
    fun commande(jeu: Jeu, reste: String): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = (m.getOrNull(0) ?: "aide").lowercase().replace('é', 'e')
        val a = m.drop(1)
        val l = when (sous) {
            "carte" -> carte(jeu)
            "annuaire" -> lignesAnnuaire(a.getOrNull(0))
            "route" -> lignesRoute(jeu, a.getOrNull(0))
            "messager" -> if (a.isEmpty()) listOf(t("port.messager.aide")) else messager(jeu, a[0])
            "eteins", "eteindre" -> eteindre(jeu, a.getOrNull(0))
            "rallume", "allume" -> eteindre(jeu, a.getOrNull(0), allumer = true)
            "guide" -> if (a.isEmpty()) listOf(t("port.guide.aide")) else guide(jeu, a.filter { it != "…" && it != "..." })
            "course" -> lignesCourse(jeu)
            "couches" -> lignesCouches(jeu)
            "gardien" -> lignesGardien(jeu)
            "sceau" -> lignesSceau(jeu, a.getOrNull(0))
            "teleporteur" -> listOf(t("port.meuble.teleporteur"))
            else -> listOf("⚓ " + t("port.aide.titre")) + t("port.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }

    // ---------------------------------------------------------------- les commandes intégrées réseau (téléphone)
    /** Un petit filtre après une commande intégrée : | head -n N, | grep [-c] mot, | wc -l (les tuyaux des leçons). */
    fun filtrer(texte: String, tuyaux: List<String>): String {
        var lignes = texte.split("\n").let { if (it.lastOrNull() == "") it.dropLast(1) else it }
        for (p in tuyaux) {
            val m = p.trim().split(Regex("\\s+"))
            when (m.getOrNull(0)) {
                "head" -> { val n = Regex("-n\\s*(\\d+)|-(\\d+)").find(p)?.let { (it.groupValues[1].ifEmpty { it.groupValues[2] }).toInt() } ?: 10; lignes = lignes.take(n) }
                "grep" -> {
                    val compte = m.contains("-c")
                    val i = m.contains("-i")
                    val mot = m.drop(1).firstOrNull { !it.startsWith("-") }?.trim('"', '\'') ?: ""
                    val g = lignes.filter { if (i) it.contains(mot, ignoreCase = true) else it.contains(mot) }
                    lignes = if (compte) listOf(g.size.toString()) else g
                }
                "wc" -> lignes = listOf(lignes.size.toString())
                else -> return texte + "\n" + t("port.tel.tuyau", "cmd" to (m.getOrNull(0) ?: ""))
            }
        }
        return lignes.joinToString("\n")
    }

    /** Coupe « cmd … | head -n 3 » en (commande, [tuyaux]). */
    fun couper(ligne: String): Pair<String, List<String>> {
        val p = ligne.split("|")
        return p[0].trim() to p.drop(1).map { it.trim() }
    }

    private val pool = Executors.newCachedThreadPool { r -> Thread(r, "tg-port").apply { isDaemon = true } }

    /** Une vraie requête HTTP/1.1 sur une vraie connexion TCP à 127.0.0.1 (dans un fil à part : jamais sur le fil de
     *  l'écran). Renvoie (ce qui a été envoyé, réponse brute) ou null si personne n'écoute. */
    fun requete(port: Int, methode: String, chemin: String, hote: String): Pair<String, ByteArray>? {
        val envoi = "$methode $chemin HTTP/1.1\r\nHost: $hote:$port\r\nUser-Agent: curl-terminagotchi/1.0\r\nAccept: */*\r\nConnection: close\r\n\r\n"
        val f = pool.submit<ByteArray?> {
            try {
                Socket().use { s ->
                    s.connect(InetSocketAddress(InetAddress.getByName("127.0.0.1"), Phare.reel(port)), 2000)
                    s.soTimeout = 3000
                    s.getOutputStream().write(envoi.toByteArray(Charsets.US_ASCII))
                    s.getOutputStream().flush()
                    s.getInputStream().readBytes()
                }
            } catch (e: Exception) { null }
        }
        val r = try { f.get(4, TimeUnit.SECONDS) } catch (e: Exception) { null } ?: return null
        return envoi to r
    }

    /** curl intégré : -I, -s, -o fichier, -v, http://localhost:PORT/chemin. Rien ne sort du téléphone. */
    fun curl(jeu: Jeu, ligne: String, dossier: File): String {
        val (cmd, tuyaux) = couper(ligne)
        val m = cmd.split(Regex("\\s+")).drop(1)
        var tete = false; var verbeux = false; var sortieF: String? = null; var url: String? = null
        var i = 0
        while (i < m.size) {
            val x = m[i]
            when {
                x == "-o" || x == "--output" -> { sortieF = m.getOrNull(i + 1); i++ }
                x == "-I" || x == "--head" -> tete = true
                x == "-v" || x == "--verbose" -> verbeux = true
                x == "--cacert" -> i++
                x.startsWith("-") -> { if ('I' in x) tete = true; if ('v' in x) verbeux = true }
                else -> url = x
            }
            i++
        }
        if (url == null) return t("port.tel.curl.usage")
        val u = Regex("^(https?)://([^/:]+)(?::(\\d+))?(/.*)?$").find(url) ?: Regex("^()([^/:]+)(?::(\\d+))?(/.*)?$").find(url)
            ?: return t("port.tel.curl.usage")
        val (schema, hote, portS, chemin0) = u.destructured
        val local = hote == "localhost" || hote.startsWith("127.")
        if (!local) return t("port.tel.curl.dehors")
        if (schema == "https") return t("port.tel.curl.https")
        val port = portS.toIntOrNull() ?: 80
        val chemin = chemin0.ifEmpty { "/" }
        if (port == portPhare()) Phare.allumer(port, Phare.Genre.PHARE, jeu)
        val (envoi, brut) = requete(port, if (tete) "HEAD" else "GET", chemin, hote)
            ?: return t("port.tel.curl.injoignable", "hote" to hote, "port" to port)
        val texte = String(brut, Charsets.UTF_8)
        val sep = texte.indexOf("\r\n\r\n")
        val entetes = if (sep >= 0) texte.substring(0, sep) else texte
        val corps = if (sep >= 0) texte.substring(sep + 4) else ""
        val out = StringBuilder()
        if (verbeux) {
            out.append("*   Trying 127.0.0.1:$port...\n* Connected to $hote (127.0.0.1) port $port\n")
            for (l in envoi.trimEnd().split("\r\n")) out.append("> $l\n")
            out.append(">\n")
            for (l in entetes.split("\r\n")) out.append("< $l\n")
            out.append("<\n")
        }
        if (tete) out.append(entetes.replace("\r\n", "\n")).append("\n")
        else if (sortieF != null) {
            val f = File(dossier, sortieF).canonicalFile
            if (!f.path.startsWith(jeu.terrain.canonicalPath + "/")) return t("port.tel.curl.dehors")
            f.parentFile?.mkdirs()
            f.writeText(corps)
            out.append(t("port.tel.curl.ecrit", "fichier" to sortieF, "n" to corps.toByteArray().size))
        } else out.append(corps)
        return filtrer(out.toString(), tuyaux)
    }

    /** nslookup / host intégré : l'annuaire du port et localhost (jamais Internet). */
    fun nslookup(reste: String): String {
        val nom = reste.trim().split(Regex("\\s+")).firstOrNull { it.isNotEmpty() && !it.startsWith("-") }
            ?: return t("port.tel.nslookup.inconnu", "nom" to "?")
        val id = chercher(nom) ?: return t("port.tel.nslookup.inconnu", "nom" to nom)
        return t("port.tel.nslookup.reponse", "nom" to nom, "adresse" to machine(id)!!.adresse)
    }

    /** ss intégré : les portes que Terminagotchi a ouvertes dans le téléphone (-t, -u, -l, -n). */
    fun ss(ligne: String): String {
        val (cmd, tuyaux) = couper(ligne)
        val opts = cmd.split(Regex("\\s+")).drop(1).filter { it.startsWith("-") }.joinToString("")
        val udp = 'u' in opts && 't' !in opts
        val ecoute = 'l' in opts
        val out = mutableListOf("State  Recv-Q Send-Q Local Address:Port  Peer Address:Port")
        if (!udp && ecoute) for (p in Phare.actifs()) out.add("LISTEN 0      50     127.0.0.1:${p}      0.0.0.0:*")
        out.add(t("port.tel.ss.note"))
        return filtrer(out.joinToString("\n"), tuyaux)
    }

    /** serveur 8000 | serveur stop : ta lanterne (attachée à 127.0.0.1, elle sert seulement port/quai). */
    fun serveur(jeu: Jeu, reste: String): String {
        val m = reste.trim().lowercase()
        if (m in setOf("stop", "arret", "off")) {
            val l = Phare.actifs().filter { it != portPhare() }
            if (l.isEmpty()) return t("port.tel.serveur.aucun")
            l.forEach { Phare.eteindre(it) }
            return t("port.tel.serveur.eteint")
        }
        val p = m.toIntOrNull() ?: return t("port.tel.serveur.usage")
        if (p == portPhare() || p < 1024 || p > 65535) return t("port.tel.serveur.usage")
        if (p in Phare.actifs()) return t("port.tel.serveur.deja", "port" to p)
        return if (Phare.allumer(p, Phare.Genre.QUAI, jeu)) t("port.tel.serveur.allume", "port" to p)
        else t("port.tel.curl.injoignable", "hote" to "127.0.0.1", "port" to p)
    }
}

/**
 * Les vrais petits serveurs HTTP de l'appli, attachés à 127.0.0.1 (personne d'autre ne peut les joindre) :
 * le phare du port (des pages fabriquées par le jeu) et la lanterne de l'enfant (le dossier port/quai seulement).
 * Chacun s'éteint seul après 30 minutes sans visite. decalage : pour les tests JVM (ne pas gêner un vrai 8042).
 */
object Phare {
    enum class Genre { PHARE, QUAI }

    @Volatile var decalage = 0
    fun reel(port: Int) = port + decalage

    private class Serveur(val ss: ServerSocket, @Volatile var vu: Long)
    private val serveurs = java.util.concurrent.ConcurrentHashMap<Int, Serveur>()

    fun actifs(): List<Int> = serveurs.keys.sorted()

    fun allumer(port: Int, genre: Genre, jeu: Jeu): Boolean {
        if (serveurs.containsKey(port)) return true
        val ss = try { ServerSocket().apply { reuseAddress = true; bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), reel(port)), 50) } }
        catch (e: Exception) { return false }
        val s = Serveur(ss, System.currentTimeMillis())
        serveurs[port] = s
        val quai = File(jeu.terrain, "port/quai").canonicalFile
        Thread({
            ss.soTimeout = 2000
            while (!ss.isClosed) {
                val c = try { ss.accept() } catch (e: java.net.SocketTimeoutException) {
                    if (System.currentTimeMillis() - s.vu > 30 * 60 * 1000L) eteindre(port)
                    continue
                } catch (e: Exception) { break }
                s.vu = System.currentTimeMillis()
                Thread({ servir(c, genre, quai) }, "tg-phare-client").apply { isDaemon = true }.start()
            }
        }, "tg-phare-$port").apply { isDaemon = true }.start()
        return true
    }

    fun eteindre(port: Int) { serveurs.remove(port)?.let { try { it.ss.close() } catch (e: Exception) { } } }
    fun toutEteindre() { for (p in actifs()) eteindre(p) }

    private fun servir(c: Socket, genre: Genre, quai: File) {
        try {
            c.use { s ->
                s.soTimeout = 3000
                val ent = s.getInputStream().bufferedReader(Charsets.ISO_8859_1)
                val premiere = ent.readLine() ?: return
                while (true) { val l = ent.readLine() ?: break; if (l.isEmpty()) break }
                val (methode, chemin) = premiere.split(" ").let { (it.getOrNull(0) ?: "GET") to (it.getOrNull(1) ?: "/") }
                val (code, corps, type) = when (genre) {
                    Genre.PHARE -> Port.page(chemin).let { Triple(it.first, it.second.toByteArray(), "text/plain; charset=utf-8") }
                    Genre.QUAI -> fichier(quai, chemin)
                }
                val raison = if (code == 200) "OK" else "Not Found"
                val serveur = if (genre == Genre.PHARE) "PhareDuPort/1.0" else "Lanterne/1.0"
                val tete = "HTTP/1.1 $code $raison\r\nServer: $serveur\r\nContent-Type: $type\r\nContent-Length: ${corps.size}\r\nConnection: close\r\n\r\n"
                val o = s.getOutputStream()
                o.write(tete.toByteArray(Charsets.ISO_8859_1))
                if (methode != "HEAD") o.write(corps)
                o.flush()
            }
        } catch (e: Exception) { }
    }

    /** Un fichier de port/quai (index.html pour « / ») ; rien en dehors de ce dossier. */
    private fun fichier(quai: File, chemin: String): Triple<Int, ByteArray, String> {
        val c = java.net.URLDecoder.decode(chemin.substringBefore('?'), "UTF-8").trimStart('/')
        val f = File(quai, c.ifEmpty { "index.html" }).let { if (it.isDirectory) File(it, "index.html") else it }.canonicalFile
        if (!f.path.startsWith(quai.path + File.separator) || !f.isFile) return Triple(404, "404\n".toByteArray(), "text/plain")
        val type = if (f.name.endsWith(".html")) "text/html; charset=utf-8" else "text/plain; charset=utf-8"
        return Triple(200, f.readBytes(), type)
    }
}
