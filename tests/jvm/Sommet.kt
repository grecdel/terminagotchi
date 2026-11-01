/*
 * Test JVM du Sommet (phase 5) sur Android, portage de pc/outils/test_sommet.py :
 *   1. les vecteurs communs donnees/sommet/vecteurs.json : le journal et ses réponses (14 langues), l'éboulis, la
 *      boussole, le CTF, les TEXTES EXACTS des scripts (bash et sh, 14 langues), le défi du jour, la cordée ;
 *   2. l'ouverture : 3 mondes au palier 3 (un monde ajouté plus tard compte), annoncée une fois, meublée ;
 *   3. la traversée som0 → som7 comme dans l'appli (sh au lieu de bash ; les étapes sans outil sur le téléphone sont
 *      cachées) : l'exploit « trois mondes maîtrisés », la faveur des légendaires, le piolet, rien hors du terrain ;
 *   4. le dessin (cordée, refuge de repli) sur une toile d'essai.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Sommet.kt -d som.jar
 *   java -cp <imitations>:<appli.jar>:som.jar:kotlin-stdlib.jar SommetKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Entrainement
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Programme
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Sommet
import fr.terminagotchi.SommetDessin
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsSo(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilSo(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsSo(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileSo : Toile {
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

var okSo = 0
var koSo = 0
fun verifierSo(c: Boolean, m: String) {
    if (c) okSo++ else koSo++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuSo: Jeu
lateinit var shellSo: Shell
lateinit var cmdSo: Commandes

fun lstSo(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
/** Le sh du téléphone est mksh (pipefail, getopts, trap) : ici mksh ou busybox sh s'ils sont là, sinon bash (dash n'a pas pipefail). */
val SH_SO: List<String> = listOf(listOf("mksh"), listOf("busybox", "sh"), listOf("bash")).first { c ->
    try { ProcessBuilder(c + listOf("-c", "set -o pipefail")).start().waitFor() == 0 } catch (e: Exception) { false } }

fun shSo(cmd: String, ou: File = shellSo.dossier): Pair<String, Int> {
    val c = Regex("(^|&&\\s*|;\\s*)sh(?=\\s)").replace(cmd) { it.groupValues[1] + SH_SO.joinToString(" ") }
    val pb = ProcessBuilder(listOf("bash", "-c", c)).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuSo.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeSo(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellSo.executer(cmd)
    else {
        val interne = cmdSo.executer(cmd)
        if (interne != null) sortie = interne.texte
        else shSo(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuSo, cmd, colle = false, rappel = false, hasard = false, cwd = shellSo.dossier, code = code)
    return sortie
}

fun lecSo(): Pair<String?, Int> = Histoire.leconCourante(jeuSo)?.id to jeuSo.etape

fun fichiersHorsSo(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_so_" + System.nanoTime()).apply { mkdirs() }
    java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"))
    val app = AppareilSo(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuSo = Jeu(app)
    jeuSo.changerLangue("fr")
    jeuSo.nom = "Pixel"
    shellSo = Shell(jeuSo.home)
    cmdSo = Commandes(app, jeuSo, { shellSo.dossier })
    jeuSo.module("explo").put("ouverte", true)
    jeuSo.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/sommet/vecteurs.json").readText())
    var ko = 0
    val parties = v.getJSONArray("parties")
    for (i in 0 until parties.length()) {
        val p = parties.getJSONObject(i)
        val g = p.getString("graine")
        Langue.definir("fr")
        val eb = Sommet.eboulis(g)
        val ebV = p.getJSONObject("eboulis")
        if (eb.keys.toList() != ebV.keys().asSequence().toList() || eb.any { (k, x) -> ebV.getJSONArray(k).let { it.getString(0) != x.first || it.getInt(1) != x.second } }) { ko++; println("    $g éboulis") }
        val pl = p.getJSONArray("plus_lourds").let { a -> (0 until a.length()).map { a.getJSONArray(it).getInt(0) to a.getJSONArray(it).getString(1) } }
        if (Sommet.plusLourds(g) != pl || Sommet.plusLourde(g) != p.getString("plus_lourde") || Sommet.totalEboulis(g) != p.getInt("total")) { ko++; println("    $g plus lourds") }
        val (cap, pas) = Sommet.mission(g)
        if (listOf(cap, "$pas") != lstSo(p.getJSONArray("mission")) || Sommet.lieu(g, cap, pas) != p.getString("lieu")) { ko++; println("    $g mission") }
        if (Sommet.fragments(g) != lstSo(p.getJSONArray("fragments")) || Sommet.drapeau(g) != p.getString("drapeau")) { ko++; println("    $g fragments") }
        val L = p.getJSONObject("langues")
        for (code in L.keys()) {
            Langue.definir(code)
            val x = L.getJSONObject(code)
            val faits = listOf(
                "journal" to (Sommet.journalTexte(g) == x.getString("journal")),
                "reponses" to (Sommet.lignesDatees(g).size == x.getInt("lignes_datees") && Sommet.dates(g) == lstSo(x.getJSONArray("dates")) &&
                    Sommet.alertes(g) == lstSo(x.getJSONArray("alertes")) && Sommet.alertesPartout(g).size == x.getInt("alertes_partout")),
                "boussole" to (Sommet.scriptBoussole(g, "bash") == x.getJSONObject("boussole").getString("bash") &&
                    Sommet.scriptBoussole(g, "sh") == x.getJSONObject("boussole").getString("sh") && Sommet.aideBoussole() == x.getString("aide_boussole")),
                "ctf" to listOf("bash", "sh").all { sh -> val c = x.getJSONObject("ctf").getJSONObject(sh)
                    Sommet.fichiersCtf(g, sh).let { f -> f.keys.toList() == c.keys().asSequence().toList() && f.all { (k, t) -> t == c.getString(k) } } },
            )
            for ((k, ok) in faits) if (!ok) { ko++; println("    $g $code : $k") }
        }
    }
    val sc = v.getJSONObject("scripts")
    for (code in sc.keys()) {
        Langue.definir(code)
        for (sh in listOf("bash", "sh")) { val s = sc.getJSONObject(code).getJSONObject(sh)
            for (nom in s.keys()) if (Sommet.script(nom, sh) != s.getString(nom)) { ko++; println("    script $code $sh $nom :\n${Sommet.script(nom, sh)}≠\n${s.getString(nom)}") } }
    }
    Langue.definir("fr")
    verifierSo(ko == 0, "${parties.length()} parties : journal (14 langues), réponses, éboulis, boussole, CTF, et les ${sc.length()}×2×5 scripts identiques au Python")
    ko = 0
    for (x in (0 until v.getJSONArray("defis").length()).map { v.getJSONArray("defis").getJSONObject(it) })
        if (Sommet.defiTypes(x.getString("valeur"), lstSo(x.getJSONArray("possibles"))) != lstSo(x.getJSONArray("types"))) ko++
    verifierSo(ko == 0, "le défi du jour : mêmes exercices tirés de la graine du jour")
    ko = 0
    for (x in (0 until v.getJSONArray("cordee").length()).map { v.getJSONArray("cordee").getJSONObject(it) }) {
        val k = Deploie.cordees(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.outil, it.geste, it.de, it.vers) }
        val a = (0 until x.getJSONArray("cordees").length()).map { x.getJSONArray("cordees").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("geste"), it.getString("de"), it.getString("vers")) }
        if (k != a) { ko++; println("    cordée ${x.getString("ligne")} : $k ≠ $a") }
    }
    verifierSo(ko == 0, "la cordée de la vue déployée : mêmes gestes")

    println("2. L'ouverture : 3 mondes au palier 3")
    val h = Histoire.h(jeuSo)
    val faits = h.optJSONArray("faits") ?: JSONArray().also { h.put("faits", it) }
    val ailes = h.optJSONArray("ailes") ?: JSONArray().also { h.put("ailes", it) }
    for (c in listOf("reveil", "nid", "bibliotheque", "cave")) { for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l); ailes.put(c) }
    val ann = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
    for (m in listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees")) ann.put(m)
    h.remove("chap")
    jeuSo.xp = 10 * 30 * 30
    fun palier(c: String) { for (l in Histoire.PAR_CHAP[c]!!.lecons.take(4)) if (l !in lstSo(faits)) faits.put(l) }
    palier("port"); palier("citadelle")
    tapeSo("ls")
    verifierSo(!Histoire.ouvert(jeuSo, "sommet") && Sommet.mondesAuPalier(jeuSo).size == 2, "deux mondes au palier 3 : fermé (${Sommet.manque(jeuSo)})")
    val P = Programme.donnees().getJSONArray("mondes")
    P.put(JSONObject().put("id", "forge_test").put("chapitre", "port").put("paliers", JSONArray(listOf("port0", "port1", "port2", "port3"))))
    verifierSo(Sommet.mondesAuPalier(jeuSo).size == 3, "un monde ajouté plus tard à programme.json compte, sans rien changer au Sommet")
    P.remove(P.length() - 1)
    palier("machinerie")
    verifierSo("sm3" in Sommet.leconsQuiOuvrent(), "le palier 3 d'un monde annonce le Sommet dès la leçon finie")
    tapeSo("ls")
    verifierSo(Histoire.ouvert(jeuSo, "sommet"), "trois mondes au palier 3 : le Sommet s'ouvre")
    Histoire.annoncerMonde(jeuSo)
    verifierSo("sommet" in lstSo(Histoire.h(jeuSo).optJSONArray("mondes_annonces")), "annoncé une fois")
    tapeSo("ls")
    val SD = Sommet.dossier(jeuSo)
    verifierSo(File(SD, "refuge.txt").isFile && File(SD, Sommet.CARNET).isFile, "le refuge est meublé (règlement, carnet)")
    val avant = fichiersHorsSo(jeuSo.home, jeuSo.terrain)

    println("3. La traversée, comme dans l'appli (sh : ${SH_SO.joinToString(" ")})")
    tapeSo("cd ~/terrain_terminagotchi/sommet")
    verifierSo(lecSo() == ("som0" to 1), "entrer au Sommet choisit le monde : ${lecSo()}")
    val g = Sommet.graine(jeuSo)
    val (cap, pas) = Sommet.mission(g)
    val sorties = LinkedHashMap<String, String>()
    val parcours: List<() -> String> = listOf(
        { "ls" }, { "cat refuge.txt" },
        { "sommet fragile" }, { "cat fragile.sh" }, { "sh fragile.sh \"carnet de bord.txt\"" }, { "echo \$?" },
        { "sed -i '2i set -euo pipefail' fragile.sh" }, { "sh fragile.sh \"carnet de bord.txt\"; echo \$?" },
        { "sed -i 's/cp \$carnet/cp \"\$carnet\"/' fragile.sh" }, { "sh fragile.sh" }, { "sh fragile.sh \"carnet de bord.txt\"" },
        { "sommet bivouac" }, { "sh sale.sh" }, { "ls brouillon.*" }, { "cat bivouac.sh" }, { "sh bivouac.sh -n 3" },
        { "ls brouillon.* | wc -l" }, { "sh bivouac.sh -x" }, { "rm brouillon.*" },
        { "sommet journal" }, { "head -5 journal.log" }, { "grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l" },
        { "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l" }, { "sommet dates 1" }, { "sommet dates ${Sommet.dates(g).size}" },
        { "grep -cE 'ALERTE|ERREUR' journal.log" }, { "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt" },
        { "sommet alertes ${Sommet.alertes(g).size}" }, { "sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt" },
        { "sommet eboulis" }, { "find eboulis -type f" }, { "find eboulis -type f | xargs wc -c" },
        { "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6" }, { "sommet lourd ${Sommet.plusLourde(g)}" },
        { "echo \"pierres : \$(find eboulis -type f | wc -l)\"" },
        { "sommet casse" }, { "sh -n casse.sh" }, { "sommet ligne 8" }, { "sed -i '6s/\$/; then/' casse.sh" }, { "sh -n casse.sh && sh casse.sh" },
        { "sh boucle.sh" }, { "sh -x boucle.sh" }, { "sommet bug totl" }, { "sed -i 's/totl=/total=/' boucle.sh && sh boucle.sh" }, { "sommet strace" },
        { "sommet boussole" }, { "sh boussole.sh --help" }, { "sh boussole.sh -c $cap -p $pas" }, { "sommet arrivee ${Sommet.lieu(g, cap, pas)}" },
        { "grep --help | grep -- '-o'" },
        { "sommet ctf" }, { "grep -oE 'fragment1=[a-z]+' ctf/registre.log" }, { "find ctf -name '*.frag' -print0 | xargs -0 cat" },
        { "sh ctf/porte.sh --help" }, { "sh ctf/porte.sh -k ${Sommet.fragments(g)[0]}" }, { "sommet drapeau TG{a-b-c}" }, { "sommet drapeau ${Sommet.drapeau(g)}" },
        { "sommet defi" }, { "badges grades" }, { "sommet records" },
    )
    val vus = mutableListOf<Triple<Pair<String?, Int>, String, Pair<String?, Int>>>()
    for (f in parcours) {
        val c = f()
        val a = lecSo()
        val s = tapeSo(c)
        sorties.putIfAbsent(c, s)
        vus.add(Triple(a, c, lecSo()))
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $a → ${lecSo()} ${s.take(100).replace("\n", "⏎")}")
        if (Histoire.fini(jeuSo, "sommet")) break
    }
    if (!Histoire.fini(jeuSo, "sommet")) for (x in vus.takeLast(6)) println("      $x")
    verifierSo(Histoire.fini(jeuSo, "sommet"), "le Sommet est gravi jusqu'au bout (som0 → som7) ${lecSo()}")
    verifierSo("Sauvegarde réussie" in (sorties["sh fragile.sh \"carnet de bord.txt\""] ?: ""), "fragile.sh ment d'abord (sh du téléphone)")
    val d1 = vus.first { it.second == "sommet dates 1" }
    verifierSo(d1.first == d1.third, "une mauvaise réponse : l'étape attend")
    val ex = Recompenses.etat(jeuSo).getJSONObject("exploits")
    verifierSo(ex.has("sommet.trois_mondes") && Recompenses.faveur(jeuSo)?.optString("exploit") == "sommet.trois_mondes" &&
        Recompenses.faveur(jeuSo)?.optInt("reste") == 3, "exploit « trois mondes maîtrisés » : 3 rencontres de légendaires")
    verifierSo("piolet" in lstSo(Quetes.q(jeuSo).optJSONArray("objets")), "récompense du monde : un piolet de cordée (posé, jamais porté)")
    verifierSo("Temps :" in (sorties["sommet drapeau ${Sommet.drapeau(g)}"] ?: ""), "le chrono du CTF")
    val apres = fichiersHorsSo(jeuSo.home, jeuSo.terrain).filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet()
    verifierSo(apres == avant.filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet(), "rien d'écrit hors du terrain")
    verifierSo(SD.walkTopDown().filter { it.name.endsWith(".sh") }.all { val x = it.readText(); "sudo" !in x && "curl" !in x && "../" !in x && x.startsWith("#!/system/bin/sh") },
        "les scripts du téléphone : #!/system/bin/sh, ni sudo, ni réseau, ni chemin hors du dossier")
    Sommet.noterExercice(jeuSo, "exp_chemin", "or", "2026-11-01.abc")
    verifierSo(Sommet.defiFaits(jeuSo).has("exp_chemin"), "le défi du jour compte un exercice en or")
    val (types, _) = Sommet.defiDuJour(jeuSo)
    verifierSo(types.size == 3 && types.all { Entrainement.typePossible(jeuSo, it) }, "le défi du jour : 3 exercices possibles ($types)")

    println("4. Les légendaires et le dessin")
    val som = (0 until P.length()).map { P.getJSONObject(it) }.first { it.optString("id") == "sommet" }
    val leg = lstSo(som.getJSONArray("legendaires"))
    verifierSo(leg.size == 8 && "abyssor" !in leg, "le Sommet nomme 8 légendaires existantes")
    val tl = ToileSo()
    SommetDessin.cordee(tl, Deploie.cordees("bash -x boucle.sh")[0], 0.4, 0f, 0f, 320f, 96f, 1f)
    verifierSo(tl.n > 8 && tl.textes.any { "bash -x" in it }, "la cordée se dessine (${tl.n} traits)")
    val tl2 = ToileSo()
    SommetDessin.refuge(tl2, 0.3, 0f, 0f, 320f, 180f, 1f)
    verifierSo(tl2.n > 6, "le refuge de repli se dessine")

    println("\n$okSo ✔, $koSo ✖")
    if (koSo > 0) System.exit(1)
}
