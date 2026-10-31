/*
 * Test JVM du Port (phase 5) sur Android, portage de pc/outils/test_port.py :
 *   1. les vecteurs communs donnees/port/vecteurs.json (routes, tables, guidage, course, noms, couches, gardien,
 *      sceaux mélangés comme random.shuffle de Python, annuaire, pages du phare, messagers de la vue déployée) donnent
 *      EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. les vrais petits serveurs de l'appli (le phare, la lanterne) et les commandes intégrées (curl, serveur, ss,
 *      nslookup, port …) : une vraie connexion TCP sur 127.0.0.1, rien ne sort du téléphone, rien n'est écrit hors du
 *      terrain, la lanterne ne sert que port/quai ;
 *   3. l'arbre du Carrefour : le Port s'ouvre après le nid et la bibliothèque, il est annoncé une fois ;
 *   4. la traversée du Port P0 à P11 comme dans l'appli (commandes du téléphone), les deux exploits (messager guidé,
 *      sceau vérifié) et les variantes réservées du Port ;
 *   5. la vue déployée : le messager d'une commande réseau (vecteurs, partie 1).
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Port.kt -d port.jar
 *   java -cp <imitations>:<appli.jar>:port.jar:kotlin-stdlib.jar PortKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Phare
import fr.terminagotchi.Port
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsPo(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilPo(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsPo(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okPo = 0
var koPo = 0
fun verifierPo(c: Boolean, m: String) {
    if (c) okPo++ else koPo++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuPo: Jeu
lateinit var shellPo: Shell
lateinit var cmdPo: Commandes

fun lst(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

/** Les outils du shell du téléphone (toybox : ifconfig, ping) absents de la machine de test : de petites doublures,
 *  seulement pour que la partie avance (leurs vraies sorties sont rejouées par pc/outils/rejeu_bash.py). */
var doublures: File? = null

fun bashPo(cmd: String, ou: File = shellPo.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    doublures?.let { pb.environment()["PATH"] = it.path + ":" + (System.getenv("PATH") ?: "/usr/bin:/bin") }
    pb.environment()["HOME"] = jeuPo.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

/** L'enfant tape une commande dans le terminal de l'appli, puis le jeu fait son tour (comme TerminalActivity). */
fun tapePo(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellPo.executer(cmd)
    else {
        val interne = cmdPo.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashPo(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuPo, cmd, colle = false, rappel = false, hasard = false, cwd = shellPo.dossier, code = code)
    return sortie
}

fun lecPo(): Pair<String?, Int> = Histoire.leconCourante(jeuPo)?.id to jeuPo.etape

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_port_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilPo(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuPo = Jeu(app)
    jeuPo.changerLangue("fr")
    jeuPo.nom = "Pixel"
    shellPo = Shell(jeuPo.home)
    cmdPo = Commandes(app, jeuPo, { shellPo.dossier })
    jeuPo.module("explo").put("ouverte", true)
    jeuPo.terrain.mkdirs()                       // le terrain existe déjà quand on arrive au Port
    doublures = File(dossier, "doublures").apply { mkdirs() }
    for ((outil, sortie) in mapOf("ifconfig" to "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n        inet 127.0.0.1  netmask 255.0.0.0",
        "ping" to "64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.03 ms\n3 packets transmitted, 3 received, 0% packet loss")) {
        if (ProcessBuilder("bash", "-c", "command -v $outil").start().waitFor() != 0)
            File(doublures, outil).apply { writeText("#!/bin/sh\ncat <<'FIN'\n${sortie.replace("\\n", "\n")}\nFIN\n"); setExecutable(true) }
    }
    Phare.decalage = 20000                       // les vrais serveurs sur 28042 / 28000 : un vrai 8042 n'est pas gêné

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/port/vecteurs.json").readText())
    var n = 0; var ko = 0
    val routes = v.getJSONArray("routes")
    for (i in 0 until routes.length()) {
        val r = routes.getJSONObject(i)
        val att = if (r.isNull("chemin")) null else lst(r.getJSONArray("chemin"))
        n++; if (Port.route(r.getString("de"), r.getString("vers"), lst(r.getJSONArray("eteints"))) != att) { ko++; println("    route ${r}") }
    }
    verifierPo(ko == 0, "$n routes identiques (plus court chemin, phares éteints, ordre des liens)")
    ko = 0
    val tables = v.getJSONArray("tables")
    for (i in 0 until tables.length()) {
        val x = tables.getJSONObject(i)
        val t = Port.table(x.getString("machine"), lst(x.getJSONArray("eteints"))).map { listOf(it.first, it.second, it.third.toString()) }
        val att = (0 until x.getJSONArray("table").length()).map { lst(x.getJSONArray("table").getJSONArray(it)) }
        if (t != att) { ko++; println("    table $x → $t") }
    }
    verifierPo(ko == 0, "${tables.length()} tables de routage identiques")
    ko = 0
    val guides = v.getJSONArray("guides")
    for (i in 0 until guides.length()) {
        val x = guides.getJSONObject(i)
        val g = Port.guider(lst(x.getJSONArray("chemin")), lst(x.getJSONArray("eteints")))
        if (g.ok != x.getBoolean("ok") || g.sauts != lst(x.getJSONArray("sauts")) || g.raison != x.getString("raison") ||
            g.ou != (if (x.isNull("ou")) null else x.getString("ou")) || g.ttl != x.getInt("ttl")) { ko++; println("    guide $x") }
    }
    verifierPo(ko == 0, "${guides.length()} messagers guidés : mêmes sauts, même raison, même TTL")
    val c = Port.course(); val vc = v.getJSONObject("course")
    verifierPo(c.tcpRecus.map { "$it" } == lst(vc.getJSONObject("tcp").getJSONArray("recus")) &&
        c.udpRecus.map { "$it" } == lst(vc.getJSONObject("udp").getJSONArray("recus")) &&
        c.tcpEnvois == vc.getJSONObject("tcp").getInt("envois"), "la course TCP / UDP : ${c.udpRecus}")
    ko = 0
    val noms = v.getJSONArray("noms")
    for (i in 0 until noms.length()) { val x = noms.getJSONObject(i); if (Port.chercher(x.getString("nom")) != (if (x.isNull("id")) null else x.getString("id"))) ko++ }
    val cou = v.getJSONArray("couches")
    for (i in 0 until cou.length()) { val x = cou.getJSONObject(i); if (Port.couchesOk(x.getString("texte")) != x.getBoolean("ok")) { ko++; println("    couches $x") } }
    verifierPo(ko == 0, "${noms.length()} noms et ${cou.length()} ordres de couches identiques")
    val g = Port.gardien(); val vg = v.getJSONObject("gardien")
    verifierPo(g.box == vg.getString("box") && g.publique == vg.getString("publique") &&
        g.baux.map { listOf(it.first, it.second) } == (0 until vg.getJSONArray("baux").length()).map { lst(vg.getJSONArray("baux").getJSONArray(it)) },
        "le gardien : ${g.baux}")
    ko = 0
    val sc = v.getJSONArray("sceaux")
    for (i in 0 until sc.length()) {
        val x = sc.getJSONObject(i)
        val ordre = Port.sceaux(x.getString("graine")).map { it.second.getString("raison") }
        if (ordre != lst(x.getJSONArray("ordre")) || Port.vraiSceau(x.getString("graine")) != x.getInt("vrai")) { ko++; println("    sceaux $x → $ordre") }
    }
    verifierPo(ko == 0, "${sc.length()} graines : les sceaux mélangés comme random.shuffle de Python")
    verifierPo(Port.annuaire() == lst(v.getJSONArray("annuaire")), "l'annuaire du port (format /etc/hosts)")
    ko = 0
    val pages = v.getJSONArray("pages")
    for (i in 0 until pages.length()) {
        val x = pages.getJSONObject(i)
        val (code, corps) = Port.page(x.getString("chemin"))
        if (code != x.getInt("code") || corps.split("\n")[0] != x.getString("premiere")) { ko++; println("    page $x → $code ${corps.split("\n")[0]}") }
    }
    verifierPo(ko == 0, "${pages.length()} pages du phare (codes et première ligne)")
    ko = 0
    val ms = v.getJSONArray("messagers")
    for (i in 0 until ms.length()) {
        val x = ms.getJSONObject(i)
        val m = Deploie.messager(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.dest, "${it.local}") }
        val a = (0 until x.getJSONArray("messagers").length()).map { x.getJSONArray("messagers").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("dest"), "${it.getBoolean("local")}") }
        if (m != a) { ko++; println("    messager ${x.getString("ligne")} → $m (attendu $a)") }
    }
    verifierPo(ko == 0, "${ms.length()} lignes : le messager de la vue déployée (destination, boucle locale ou dehors)")

    println("2. L'arbre du Carrefour : quand le Port s'ouvre")
    val h = Histoire.h(jeuPo)
    verifierPo(!Histoire.ouvert(jeuPo, "port") && "Le Port" in Histoire.choisir(jeuPo, "port", dit = false) &&
        Port.manque(jeuPo).size == 2, "fermé au début : il manque ${Port.manque(jeuPo)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid")) h.getJSONArray("ailes").put(c)
    h.put("chap", "bibliotheque")
    Histoire.tick(jeuPo, "ls", false, jeuPo.home, 0)        // le filet : le chapitre 5 fini se termine
    verifierPo(Histoire.fini(jeuPo, "bibliotheque") && Histoire.ouvert(jeuPo, "port"), "nid et bibliothèque finis : le Port s'ouvre")
    verifierPo(lst(h.optJSONArray("mondes_annonces")) == listOf("port") && !Port.annonce(jeuPo), "annoncé une seule fois")
    verifierPo(File(jeuPo.terrain, "port/annuaire.txt").isFile && File(jeuPo.terrain, "port/panneau.txt").readText().contains("Pixel"),
        "le port est meublé (panneau, annuaire, carnet de bord, quai, téléporteur)")
    verifierPo(Histoire.lignesAiles(jeuPo).any { "Le Port" in it }, "le menu des lieux montre le Port")

    println("3. La traversée du Port sur le téléphone")
    jeuPo.xp = 10 * 30 * 30                              // l'XP ne bloque pas (on teste le parcours, pas la faim)
    tapePo("cd ~/terrain_terminagotchi/port")
    verifierPo(lecPo() == ("port0" to 1), "entrer dans le port choisit le monde : ${lecPo()}")
    val etapes = linkedMapOf(
        "port0" to listOf("ls", "cat panneau.txt"),
        "port1" to listOf("hostname", "ifconfig", "ping -c 3 localhost"),
        "port2" to listOf("cat /etc/hosts", "nslookup localhost", "grep feu annuaire.txt"),
        "port3" to listOf("curl -I http://localhost:8042/", "curl -s http://localhost:8042/eau | head -n 3",
            "curl -o colis.html http://localhost:8042/feu", "curl -I http://localhost:8042/volcan_perdu"),
        "port4" to listOf("port teleporteur", "cat teleporteur.txt"),
        "port5" to listOf("echo \"Bienvenue sur mon quai\" > quai/index.html", "serveur 8000", "curl http://localhost:8000", "serveur stop"),
        "port6" to listOf("curl -v http://localhost:8042/", "port couches", "echo \"application transport reseau liaison\" > couches.txt"),
        "port7" to listOf("ss -tln", "ss -tln | grep 8042", "port carte"),
        "port8" to listOf("ss -t", "ss -u", "port course"),
        "port9" to listOf("port route", "ping -c 3 127.0.0.1", "port messager feu", "port eteins roche", "port guide racine roche feu",
            "port guide racine plante poison ombre machine feu"),
        "port10" to listOf("port gardien"),
        "port11" to listOf("port sceau", "port sceau ${(Port.vraiSceau(Histoire.graine(jeuPo)) % 4) + 1}",
            "port sceau ${Port.vraiSceau(Histoire.graine(jeuPo))}"),
    )
    val sorties = HashMap<String, String>()
    for ((lid, cmds) in etapes) for (c in cmds) {
        val s = tapePo(c)
        sorties[c] = s
        if (System.getenv("TG_DEBUG") != null) println("    · $c → ${lecPo()} « ${jeuPo.bulle} » ${s.take(80).replace("\n", " ⏎ ")}")
    }
    verifierPo(Histoire.fini(jeuPo, "port"), "le Port est réveillé jusqu'au bout (P0 → P11) : ${lecPo()} ${Histoire.faits(jeuPo).filter { it.startsWith("port") }}")
    verifierPo(sorties["curl -I http://localhost:8042/"]!!.startsWith("HTTP/1.1 200 OK") &&
        "Server: PhareDuPort/1.0" in sorties["curl -I http://localhost:8042/"]!!, "curl -I : une vraie réponse du phare (200 OK)")
    verifierPo(sorties["curl -s http://localhost:8042/eau | head -n 3"]!!.trimEnd().split("\n").size == 3 &&
        sorties["curl -s http://localhost:8042/eau | head -n 3"]!!.startsWith("💧 eau.terminaworld"), "le tuyau | head -n 3 garde 3 lignes")
    verifierPo(File(jeuPo.terrain, "port/colis.html").readText().contains("feu.terminaworld"), "curl -o : le colis est posé sur le quai")
    verifierPo(sorties["curl -I http://localhost:8042/volcan_perdu"]!!.startsWith("HTTP/1.1 404 Not Found"), "404 pour une page qui n'existe pas")
    verifierPo(sorties["curl http://localhost:8000"]!!.trim() == "Bienvenue sur mon quai", "la lanterne sert la page du quai")
    verifierPo("> GET / HTTP/1.1" in sorties["curl -v http://localhost:8042/"]!! && "< HTTP/1.1 200 OK" in sorties["curl -v http://localhost:8042/"]!!,
        "curl -v montre la vraie requête envoyée et la réponse")
    verifierPo("127.0.0.1:8042" in sorties["ss -tln | grep 8042"]!!, "ss : la porte du phare")
    verifierPo(Port.dansCarnet(jeuPo, "guide") && "port.messager" in Recompenses.etat(jeuPo).getJSONObject("exploits").keys().asSequence().toList(),
        "exploit : un messager guidé sans perte (après un premier essai perdu par la Roche éteinte)")
    verifierPo("port.sceau" in Recompenses.etat(jeuPo).getJSONObject("exploits").keys().asSequence().toList(), "exploit : le sceau vérifié")
    verifierPo("phare_miniature" in lst(fr.terminagotchi.Quetes.q(jeuPo).optJSONArray("objets")), "récompense du monde : un phare miniature")

    // les indices du Port (comme port.indice en Python) : un trou recopié, un messager perdu, un faux sceau, une faute
    val lec = Port.lecons(jeuPo)
    val toutes = lec.values.flatMap { it.etapes }
    val guideE = toutes.first { it.cmd.startsWith("port guide") }; val sceauE = toutes.first { it.cmd.startsWith("port sceau ") }
    val tuyau = toutes.first { it.cmd.startsWith("curl -s") }
    verifierPo(Port.indice(jeuPo, guideE, listOf("port guide racine … feu" to null)) == t("port.indice.remplace") &&
        Port.indice(jeuPo, sceauE, listOf("port sceau ?" to null)) == t("port.indice.remplace") &&
        Port.indice(jeuPo, sceauE, listOf("port sceau" to null)) == t("port.sceau.aide") &&
        Port.indice(jeuPo, tuyau, listOf("curl -s http://locahost:8042/eau | head -n 3" to null))!!.contains("locahost") &&
        Port.indice(jeuPo, tuyau, listOf("curl -s http://localhost:8042/eau | head -n 3" to null)) == null,
        "indices du Port : « … » et « ? » à remplir, la règle des sceaux, « locahost » caché par le tuyau")
    Port.noter(jeuPo, "guide", "camp → racine ✖ roche (perdu)")
    verifierPo(Port.indice(jeuPo, guideE, listOf("port guide racine roche feu" to null)) == t("port.indice.guide"), "un messager perdu : l'indice de la carte")

    println("4. Rien ne sort du téléphone, rien n'est écrit hors du terrain")
    verifierPo(Port.curl(jeuPo, "curl -I https://example.com", jeuPo.terrain).contains("localhost"), "curl vers Internet : refusé et expliqué")
    verifierPo(Port.curl(jeuPo, "curl -o ../../hors.txt http://localhost:8042/feu", File(jeuPo.terrain, "port")).contains("localhost") &&
        !File(jeuPo.home, "hors.txt").exists() && !File(jeuPo.home.parentFile, "hors.txt").exists(), "curl -o hors du terrain : refusé")
    verifierPo(Port.nslookup("example.com").startsWith("**"), "nslookup ne demande jamais à Internet")
    Port.serveur(jeuPo, "8000")
    val passe = Port.curl(jeuPo, "curl http://localhost:8000/../../save.json", jeuPo.terrain)
    verifierPo("404" in passe || passe.isBlank(), "la lanterne ne sert que port/quai (pas de ../)")
    Port.serveur(jeuPo, "stop")
    verifierPo(Port.serveur(jeuPo, "80").contains("serveur 8000") && Port.serveur(jeuPo, "8042").contains("serveur 8000"),
        "la lanterne refuse les portes du système (< 1024) et celle du phare")
    verifierPo(Phare.actifs().all { p -> try { java.net.Socket().use { s -> s.connect(java.net.InetSocketAddress(java.net.InetAddress.getByName("127.0.0.1"), Phare.reel(p)), 500) }; true } catch (e: Exception) { false } },
        "le phare écoute sur 127.0.0.1")

    println("5. Les variantes réservées du Port")
    val j2 = Jeu(AppareilPo(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierPo(Recompenses.reservee(j2, "orage", "plumange") && !Recompenses.reservee(j2, "orage", "lumignon") &&
        !Recompenses.reservee(j2, "nuage", "plumange"), "plumange:orage réservée (pour cette espèce seulement) tant qu'aucun exploit du Port")
    Recompenses.exploit(j2, "port.messager")
    verifierPo(!Recompenses.reservee(j2, "orage", "plumange") && !Recompenses.reservee(j2, "lagon", "tortunivers"), "après un exploit du Port : libérées")

    Phare.toutEteindre()
    println("\n$okPo réussis, $koPo échoués")
    kotlin.system.exitProcess(if (koPo == 0) 0 else 1)
}
