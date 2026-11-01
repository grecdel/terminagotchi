/*
 * Test JVM de l'Atelier (phase 5) sur Android, portage de pc/outils/test_atelier.py :
 *   1. les vecteurs communs donnees/atelier/vecteurs.json : la physique du robot simulé (chaque arène, cinq cerveaux,
 *      24 pas), le verdict du défi, la grille dessinée, le moteur et la LED (UTF-8, UTF-16), l'arène, la porte, les
 *      situations et le réflexe de chaque partie, les réponses, ce que fait une commande au robot, la vue déployée ;
 *   2. l'arbre du Carrefour : l'Atelier s'ouvre après le niveau 4 du tronc (annoncé une fois), meublé ;
 *   3. la traversée at0 → at7 comme dans l'appli : la LED, le moteur, la grille, ET / OU / NON, la boucle de l'enfant
 *      DÉROULÉE PAR L'APPLI (le shell du téléphone ne connaît pas `atelier`) avec SON cerveau.sh lancé par le vrai sh,
 *      le défi raté (choc) puis réussi, l'exploit, le robot miniature, le téléphone robot de poche ; rien hors du
 *      terrain ; aucun vrai matériel ;
 *   4. le dessin (vue déployée) sur une toile d'essai.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Atelier.kt -d ate.jar
 *   java -cp <imitations>:<appli.jar>:ate.jar:kotlin-stdlib.jar AtelierKt app/src/main/assets
 */
import fr.terminagotchi.Atelier
import fr.terminagotchi.AtelierDessin
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsAt(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilAt(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsAt(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileAt : Toile {
    var n = 0
    val textes = mutableListOf<String>()
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { n++ }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { n++ }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { n++ }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { n++ }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { n++ }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { n++ }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { n++; textes.add(s) }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.6f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { n++ }
    override fun cadre(c: fr.terminagotchi.Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) { n++ }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { n++ }
}

var okAt = 0
var koAt = 0
fun verifierAt(c: Boolean, m: String) {
    if (c) okAt++ else koAt++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuAt: Jeu
lateinit var shellAt: Shell
lateinit var cmdAt: Commandes

fun lstAt(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsAt(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }

fun bashAt(cmd: String, ou: File = shellAt.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("sh", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuAt.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeAt(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellAt.executer(cmd)
    else if (mot in setOf("lampe", "vibre", "batterie")) sortie = "($mot : le vrai téléphone)"   // (pas de lampe ni de vibreur sous la JVM)
    else {
        val interne = cmdAt.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashAt(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuAt, cmd, colle = false, rappel = false, hasard = false, cwd = shellAt.dossier, code = code)
    return sortie
}

fun lecAt(): Pair<String?, Int> = Histoire.leconCourante(jeuAt)?.id to jeuAt.etape

fun fichiersHorsAt(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_at_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilAt(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuAt = Jeu(app)
    jeuAt.changerLangue("fr")
    jeuAt.nom = "Pixel"
    shellAt = Shell(jeuAt.home)
    cmdAt = Commandes(app, jeuAt, { shellAt.dossier })
    jeuAt.module("explo").put("ouverte", true)
    jeuAt.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/atelier/vecteurs.json").readText())
    val cerveaux = mapOf<String, (Int) -> String>("droite" to { d -> if (d < 10) "droite" else "avance" }, "gauche" to { d -> if (d < 10) "gauche" else "avance" },
        "fonce" to { _ -> "avance" }, "stop" to { d -> if (d < 10) "stop" else "avance" }, "zigzag" to { d -> if (d < 20) "gauche" else "avance" })
    var ko = 0
    for (x in objetsAt(v.getJSONArray("physique"))) {
        val cle = x.getString("arene")
        val f = cerveaux[x.getString("cerveau")]!!
        var r = Atelier.depart(cle)
        val g = Atelier.grille(cle)
        if (Atelier.distanceCm(g, r.x, r.y, r.d) != x.getInt("depart_cm")) { ko++; println("    départ $cle") }
        val pas = x.getJSONArray("pas")
        val vus = mutableSetOf(r.x to r.y)
        var chocs = 0
        for (k in 0 until pas.length()) {
            val (nv, ev) = Atelier.pasRobot(cle, r, f(Atelier.distanceCm(g, r.x, r.y, r.d)))
            r = nv
            val att = pas.getJSONArray(k)
            val d = Atelier.distanceCm(g, r.x, r.y, r.d)
            if (listOf("${r.x}", "${r.y}", r.d, ev, "$d") != lstAt(att)) { ko++; println("    $cle ${x.getString("cerveau")} pas $k : ${listOf(r.x, r.y, r.d, ev, d)} ≠ $att"); break }
            if (k < 20) { vus.add(r.x to r.y); if (ev == "choc") chocs++ }
        }
        if (Atelier.verdict(vus.size, chocs, 20) != x.getString("verdict")) { ko++; println("    verdict $cle ${x.getString("cerveau")}") }
    }
    for (x in objetsAt(v.getJSONArray("verdicts"))) if (Atelier.verdict(x.getInt("cases"), x.getInt("chocs"), x.getInt("pas")) != x.getString("v")) { ko++; println("    verdict $x") }
    verifierAt(ko == 0, "la physique du robot (${v.getJSONArray("physique").length()} parcours de 24 pas) et le verdict du défi : identiques")
    ko = 0
    for (x in objetsAt(v.getJSONArray("dessins"))) {
        val rr = x.getJSONObject("robot")
        val vus = (0 until x.getJSONArray("vus").length()).map { x.getJSONArray("vus").getJSONArray(it).let { p -> p.getInt(0) to p.getInt(1) } }
        val l = Atelier.dessinGrille(x.getString("arene"), Atelier.Robot(rr.getInt("x"), rr.getInt("y"), rr.getString("d")), vus, x.getBoolean("choc"))
        if (l != lstAt(x.getJSONArray("lignes"))) { ko++; println("    dessin :\n${l.joinToString("\n")}") }
    }
    verifierAt(ko == 0, "la grille dessinée (obstacles, cases visitées, flèche, choc) : identique")
    ko = 0
    for (x in objetsAt(v.getJSONArray("moteurs"))) if (Atelier.moteurDe(x.getString("texte")) != x.getString("moteur")) { ko++; println("    moteur « ${x.getString("texte")} »") }
    for (x in objetsAt(v.getJSONArray("leds"))) if (Atelier.ledDe(x.getString("texte")) != x.getString("led")) { ko++; println("    led « ${x.getString("texte")} »") }
    for (x in objetsAt(v.getJSONArray("octets"))) {
        val h = x.getString("hex")
        val b = ByteArray(h.length / 2) { h.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
        if (Atelier.lireValeur(b) != x.getString("valeur")) { ko++; println("    octets $h → ${Atelier.lireValeur(b)}") }
    }
    verifierAt(ko == 0, "ce que comprennent le moteur et la LED (UTF-8 et UTF-16 de PowerShell) : identique")
    ko = 0
    for (x in objetsAt(v.getJSONArray("parties"))) {
        val g = x.getString("graine")
        val ch = Atelier.choixCartes(g).map { listOf("${it.first}", it.second, it.third) }
        val chv = (0 until x.getJSONArray("choix").length()).map { lstAt(x.getJSONArray("choix").getJSONArray(it)) }
        val rf = Atelier.reflexe(g).let { listOf("${it.first}", "${it.second}", "${it.third}") }
        if (Atelier.areneDefi(g) != x.getInt("arene") || Atelier.porte(g) != x.getString("porte") || Atelier.tableVerite(Atelier.porte(g)) != lstAt(x.getJSONArray("table"))
            || ch != chv || rf != lstAt(x.getJSONArray("reflexe"))) { ko++; println("    partie $g") }
    }
    for (x in objetsAt(v.getJSONArray("chiffres"))) if (Atelier.chiffres(lstAt(x.getJSONArray("args"))) != lstAt(x.getJSONArray("chiffres"))) { ko++; println("    chiffres $x") }
    for (x in objetsAt(v.getJSONArray("portes"))) if (Atelier.porteDe(x.getString("mot")) != (if (x.isNull("porte")) null else x.getString("porte"))) { ko++; println("    porte $x") }
    for (x in objetsAt(v.getJSONArray("coords"))) if (Atelier.coordOk(x.getString("texte"), x.getInt("x"), x.getInt("y")) != x.getBoolean("ok")) { ko++; println("    coord $x") }
    for (x in objetsAt(v.getJSONArray("malins"))) if (Atelier.cerveauMalinOk(x.getString("texte")) != x.getBoolean("ok")) { ko++; println("    cerveau ${x.getString("texte").take(40)}") }
    verifierAt(ko == 0, "l'arène, la porte, les situations, le réflexe de ${v.getJSONArray("parties").length()} parties ; les réponses ; le cerveau malin : identiques")
    ko = 0
    for (x in objetsAt(v.getJSONArray("robots"))) {
        val a = Atelier.robotsDe(x.getString("ligne")).map { listOf(it.first, it.second) }
        if (a != (0 until x.getJSONArray("robots").length()).map { lstAt(x.getJSONArray("robots").getJSONArray(it)) }) { ko++; println("    robots « ${x.getString("ligne")} » : $a") }
    }
    for (x in objetsAt(v.getJSONArray("deploie"))) {
        val a = Deploie.robots(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.piece, it.sens) }
        val b = objetsAt(x.getJSONArray("robots")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("piece"), it.getString("sens")) }
        if (a != b) { ko++; println("    vue « ${x.getString("ligne")} » : $a ≠ $b") }
    }
    verifierAt(ko == 0, "ce que fait chaque commande au robot, et la vue déployée : identiques")

    println("2. L'arbre du Carrefour")
    verifierAt(!Histoire.ouvert(jeuAt, "robots"), "fermé au début (il manque ${Atelier.manque(jeuAt)})")
    val h = Histoire.h(jeuAt)
    val faits = h.optJSONArray("faits") ?: JSONArray().also { h.put("faits", it) }
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    val ailes = h.optJSONArray("ailes") ?: JSONArray().also { h.put("ailes", it) }
    ailes.put("reveil"); ailes.put("nid")
    h.put("chap", "bibliotheque")
    val ann = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
    for (m in listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees")) ann.put(m)
    jeuAt.xp = 10 * 30 * 30
    tapeAt("ls")
    tapeAt("ls")
    verifierAt(Histoire.ouvert(jeuAt, "robots"), "le niveau 4 fait : l'Atelier s'ouvre")
    verifierAt("robots" in lstAt(Histoire.h(jeuAt).optJSONArray("mondes_annonces")), "annoncé une fois")
    val DD = Atelier.dossier(jeuAt)
    verifierAt(File(DD, "plan_de_l_atelier.txt").isFile && File(DD, "cerveau_exemple.sh").isFile && File(DD, "robot/led").readText() == "0\n" &&
        File(DD, "robot/capteur_distance").readText() == "60\n", "l'Atelier est meublé (plan, cerveau d'exemple, LED éteinte, capteur 60 cm)")
    val avant = fichiersHorsAt(jeuAt.home, jeuAt.terrain)

    println("3. La traversée, comme dans l'appli")
    tapeAt("cd ~/terrain_terminagotchi/robots")
    verifierAt(lecAt() == ("at0" to 1), "entrer dans l'Atelier choisit le monde : ${lecAt()}")
    val sorties = LinkedHashMap<String, String>()
    fun g() = Histoire.graine(jeuAt)
    fun ecrire(texte: String): String { File(DD, "cerveau.sh").writeText(texte); return "cat cerveau.sh" }   // l'enfant écrit dans l'éditeur
    val parcours: List<() -> String> = listOf(
        { "ls" }, { "cat plan_de_l_atelier.txt" }, { "ls robot" }, { "cat robot/led" }, { "echo 2 > robot/led" }, { "echo 1 > robot/led" },
        { "atelier robot" }, { "echo 0 > robot/led" }, { "cat robot/capteur_distance" },
        { "atelier grille" }, { "echo avance > robot/moteur" }, { "atelier pas" }, { "atelier ou 1 2" },
        { "atelier ou ${Atelier.robot(jeuAt).x} ${Atelier.robot(jeuAt).y}" }, { "echo droite > robot/moteur" }, { "atelier pas" },
        { "atelier cases ${Atelier.capteur(jeuAt) / 10}" },
        { "atelier logique" }, { "[ 5 -lt 10 ] && echo vrai || echo faux" },
        { "d=\$(cat robot/capteur_distance); if [ \"\$d\" -lt 10 ]; then echo obstacle; else echo libre; fi" },
        { "atelier verite" }, { "atelier verite " + Atelier.tableVerite(Atelier.porte(g())).joinToString(" ") },
        { "atelier choix" }, { "atelier choix " + Atelier.choixCartes(g()).joinToString(" ") { it.third } },
        { "for i in 1 2 3; do cat robot/capteur_distance; sleep 1; done" }, { "cat cerveau_exemple.sh" }, { "cp cerveau_exemple.sh cerveau.sh" },
        { "atelier essai" }, { "for i in \$(seq 10); do sh cerveau.sh; atelier pas; done" },
        { "atelier aide-cerveau" }, { ecrire(Atelier.cerveauMalin().replace("-lt 10", "-lt 0")); "edite cerveau.sh" },
        { "atelier defi" }, { "for i in \$(seq 20); do sh cerveau.sh; atelier pas; done" },
        { ecrire(Atelier.cerveauMalin()) }, { "atelier defi" }, { "for i in \$(seq 20); do sh cerveau.sh; atelier pas; done" },
        { "atelier pi" }, { "atelier gpio" }, { "atelier autonome" }, { "tail -5 robot/journal.txt" },
        { "atelier embarque" }, { "atelier reflexe" }, { "atelier reflexe ${Atelier.reflexe(g()).third}" }, { "atelier arduino" },
        { "lampe on" }, { "vibre 300" }, { "batterie" }, { "atelier telephone" },
    )
    val vus = mutableListOf<String>()
    val passages = mutableListOf<Triple<String, Any, Any>>()
    for (f in parcours) {
        val c = f()
        val a = lecAt()
        val s = tapeAt(c)
        sorties.putIfAbsent(c, s)
        passages.add(Triple(c, a, lecAt()))
        vus.add("$a $c → ${lecAt()} ${s.take(90).replace("\n", "⏎")}")
        if (System.getenv("TG_DEBUG") != null) println("    · " + vus.last())
        if (Histoire.fini(jeuAt, "robots")) break
    }
    if (!Histoire.fini(jeuAt, "robots")) vus.takeLast(8).forEach { println("      $it") }
    verifierAt(Histoire.fini(jeuAt, "robots"), "l'Atelier est traversé jusqu'au bout (at0 → at7) ${lecAt()}")
    val p2 = passages.first { it.first == "echo 2 > robot/led" }
    verifierAt(p2.second == p2.third, "une LED à 2 : l'étape attend")
    verifierAt("💡" in (sorties["atelier robot"] ?: ""), "atelier robot : la LED allumée")
    val b10 = sorties["for i in \$(seq 10); do sh cerveau.sh; atelier pas; done"] ?: ""
    verifierAt("10." in b10 && "CHOC" in b10 && "je vois" in b10, "l'appli déroule la boucle : le vrai sh lance cerveau.sh, le cerveau d'exemple se cogne")
    val carnet = Atelier.carnet(jeuAt)
    val defis = Regex("^\\[defi] .*\\((\\w+)\\)$", RegexOption.MULTILINE).findAll(carnet).map { it.groupValues[1] }.toList()
    verifierAt(defis == listOf("choc", "ok"), "deux défis : le cerveau « trop tard » se cogne, le cerveau malin réussit $defis")
    val ex = Recompenses.etat(jeuAt).getJSONObject("exploits").keys().asSequence().toList()
    verifierAt("atelier.robot" in ex, "l'exploit « un robot qui évite tous les obstacles » ($ex)")
    verifierAt("robot_miniature" in lstAt(Quetes.q(jeuAt).optJSONArray("objets")), "récompense du monde : un robot miniature (posé, jamais porté)")
    val j = File(DD, "robot/journal.txt").readLines()
    verifierAt(j.size >= 50 && (sorties["tail -5 robot/journal.txt"] ?: "").trim().lines() == j.takeLast(5), "le journal du robot, et tail -5 (${j.size} pas)")
    verifierAt(Atelier.boucle(jeuAt, "for i in \$(seq 99); do sh cerveau.sh; atelier pas; done", DD)?.startsWith("✋") == true &&
        Atelier.boucle(jeuAt, "for i in 1 2 3; do echo x; done", DD) == null, "au plus ${Atelier.TOURS_MAX} tours d'un coup ; une boucle sans `atelier` part au vrai shell")
    verifierAt(fichiersHorsAt(jeuAt.home, jeuAt.terrain).filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet() ==
        avant.filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet(), "rien d'écrit hors du terrain")
    val src = File(depot, "app/src/main/java/fr/terminagotchi/Atelier.kt").readText()
    verifierAt(!Regex("UsbManager|SerialPort|BluetoothSocket|java\\.net|File\\(\"/dev|/sys/class/gpio").containsMatchIn(src.substringAfter("object Atelier")),
        "l'appli ne parle à aucun matériel (ni /dev/tty, ni USB, ni série, ni réseau)")

    println("4. Le dessin")
    val tl = ToileAt()
    for (rb in Deploie.robots("for i in \$(seq 20); do sh cerveau.sh; atelier pas; done") + Deploie.robots("echo 1 > robot/led"))
        for (ph in listOf(0.0, 0.5, 0.95)) AtelierDessin.robot(tl, rb, ph, 0f, 0f, 380f, 96f, 1f)
    verifierAt(tl.n > 30 && tl.textes.any { "LED" in it } && tl.textes.any { "🧠" in it }, "la vue déployée : le cerveau, les roues, la LED (${tl.n} formes)")

    println("\n$okAt réussis, $koAt échoués")
    if (koAt > 0) kotlin.system.exitProcess(1)
}
