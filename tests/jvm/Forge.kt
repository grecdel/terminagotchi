/*
 * Test JVM de la Forge (phase 5) sur Android, portage de pc/outils/test_forge.py :
 *   1. les vecteurs communs donnees/forge/vecteurs.json : la recette de la cabane, la question des tours, le nom du jeu,
 *      les textes rendus sûrs, la photo d'exemple (métadonnées lues, retirées), des JPEG abîmés, des GIF, des WAV,
 *      l'atelier de la vue déployée, serpent.py et devinette.sh dans les 14 langues ;
 *   2. l'arbre du Carrefour : la Forge s'ouvre après le niveau 4 du tronc (annoncée une fois), meublée ;
 *   3. la traversée fo0 → fo7 comme dans l'appli (sh, la boîte et l'ouverture sur la même ligne, read par un tuyau, le
 *      serpent raconté, le robot qui joue à la devinette, le site servi PAR L'APPLI sur 127.0.0.1 et lu avec curl, la
 *      photo d'exemple lue et nettoyée) : les exploits, le jeu posé sur la carte, rien hors du terrain ;
 *   4. les variantes réservées, le dessin (le parchemin, le village, l'atelier de repli) sur une toile d'essai.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Forge.kt -d forge.jar
 *   java -cp <imitations>:<appli.jar>:forge.jar:kotlin-stdlib.jar ForgeKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Forge
import fr.terminagotchi.ForgeDessin
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Phare
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsFo(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilFo(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsFo(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileFo : Toile {
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

var okFo = 0
var koFo = 0
fun verifierFo(c: Boolean, m: String) {
    if (c) okFo++ else koFo++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuFo: Jeu
lateinit var shellFo: Shell
lateinit var cmdFo: Commandes

fun lstFo(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsFo(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }
fun b64(s: String): ByteArray = java.util.Base64.getDecoder().decode(s)

fun bashFo(cmd: String, ou: File = shellFo.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("sh", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuFo.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeFo(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellFo.executer(cmd)
    else {
        val interne = cmdFo.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashFo(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuFo, cmd, colle = false, rappel = false, hasard = false, cwd = shellFo.dossier, code = code)
    return sortie
}

fun lecFo(): Pair<String?, Int> = Histoire.leconCourante(jeuFo)?.id to jeuFo.etape

fun fichiersHorsFo(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_fo_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilFo(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuFo = Jeu(app)
    jeuFo.changerLangue("fr")
    jeuFo.nom = "Pixel"
    shellFo = Shell(jeuFo.home)
    cmdFo = Commandes(app, jeuFo, { shellFo.dossier })
    jeuFo.module("explo").put("ouverte", true)
    jeuFo.terrain.mkdirs()
    Phare.decalage = 7000 + (System.nanoTime() % 900).toInt()          // (ne pas gêner un vrai 8642 sur la machine des tests)

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/forge/vecteurs.json").readText())
    var ko = 0
    for (x in objetsFo(v.getJSONArray("recettes"))) {
        val e = Forge.recetteEtat(x.getString("texte"))
        val att = x.getJSONObject("etat")
        if (e.any { (k, b) -> att.getBoolean(k) != b } || Forge.recetteComplete(x.getString("texte")) != x.getBoolean("complete")) { ko++; println("    recette ${x.getString("texte").take(30)} : $e") }
    }
    for (x in objetsFo(v.getJSONArray("tours"))) {
        val (a, z) = Forge.toursQuestion(x.getString("graine"))
        if (a != x.getInt("a") || z != x.getInt("z") || Forge.toursReponse(a, z) != x.getInt("n")) { ko++; println("    tours ${x.getString("graine")} : $a $z") }
    }
    for (x in objetsFo(v.getJSONArray("noms"))) if (Forge.nomDuJeu(x.getString("texte")) != x.getString("nom")) { ko++; println("    nom « ${x.getString("texte")} » : « ${Forge.nomDuJeu(x.getString("texte"))} »") }
    for (x in objetsFo(v.getJSONArray("surs"))) if (Forge.sur(x.getString("texte")) != x.getString("sur")) { ko++; println("    sur ${x.getString("texte")}") }
    verifierFo(ko == 0, "la recette de la cabane, la question des tours, le nom du jeu, les textes rendus sûrs : identiques")
    ko = 0
    verifierFo(java.security.MessageDigest.getInstance("SHA-256").digest(Forge.photoOctets()).joinToString("") { "%02x".format(it) } == v.getString("photo_sha256"),
        "la photo d'exemple de forge.json est la même que sur PC")
    for (x in objetsFo(v.getJSONArray("photos"))) {
        val o = b64(x.getString("base64"))
        val seg = Forge.segmentsJpeg(o)
        val segOk = if (x.isNull("segments")) seg == null else seg?.size == x.getInt("segments")
        val ex = Forge.exifDe(o)
        val exOk = if (x.isNull("exif")) ex == null else ex?.map { listOf(it.first, it.second) } == (0 until x.getJSONArray("exif").length()).map { lstFo(x.getJSONArray("exif").getJSONArray(it)) }
        val sha = java.security.MessageDigest.getInstance("SHA-256").digest(Forge.sansExif(o)).joinToString("") { "%02x".format(it) }
        if (!segOk || !exOk || Forge.aExif(o) != x.getBoolean("a_exif") || sha != x.getString("sans_sha256")) { ko++; println("    photo ${x.getString("nom")} : $seg $ex") }
    }
    for (x in objetsFo(v.getJSONArray("gifs"))) if (Forge.imagesGif(b64(x.getString("base64"))) != x.getInt("images")) { ko++; println("    gif ${x.getInt("images")}") }
    for (x in objetsFo(v.getJSONArray("wavs"))) if (Forge.wavOk(b64(x.getString("base64"))) != x.getBoolean("ok")) { ko++; println("    wav") }
    verifierFo(ko == 0, "la photo (métadonnées lues, la même sans elles), les JPEG abîmés, les GIF et les WAV : identiques")
    ko = 0
    for (x in objetsFo(v.getJSONArray("atelier"))) {
        val l = x.getString("ligne")
        val a = Forge.forgesDe(l).map { listOf(it.outil, it.objet, it.de, it.vers) }
        val b = (0 until x.getJSONArray("forges").length()).map { lstFo(x.getJSONArray("forges").getJSONArray(it)) }
        val d1 = Deploie.forges(l).map { listOf("${it.seg}", it.cmd, it.outil, it.objet, it.de, it.vers) }
        val d2 = objetsFo(x.getJSONArray("deploie")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("objet"), it.getString("de"), it.getString("vers")) }
        if (a != b || d1 != d2) { ko++; println("    atelier « $l » : $a / $d1") }
    }
    verifierFo(ko == 0, "l'atelier de la vue déployée (quel objet pour quelle commande) : identique")
    ko = 0
    val textes = v.getJSONObject("textes")
    for (code in textes.keys()) {
        Langue.definir(code)
        val x = textes.getJSONObject(code)
        if (Forge.serpentPy() != x.getString("serpent")) { ko++; println("    serpent.py $code :\n${Forge.serpentPy()}≠\n${x.getString("serpent")}") }
        if (Forge.devinetteSh() != x.getString("devinette")) { ko++; println("    devinette.sh $code") }
    }
    Langue.definir("fr")
    verifierFo(ko == 0 && textes.length() == 14, "serpent.py et devinette.sh identiques dans les ${textes.length()} langues")

    println("2. L'arbre du Carrefour")
    verifierFo(!Histoire.ouvert(jeuFo, "forge"), "fermée au début (il manque ${Forge.manque(jeuFo)})")
    val h = Histoire.h(jeuFo)
    val faits = h.optJSONArray("faits") ?: JSONArray().also { h.put("faits", it) }
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    val ailes = h.optJSONArray("ailes") ?: JSONArray().also { h.put("ailes", it) }
    ailes.put("reveil"); ailes.put("nid")
    h.put("chap", "bibliotheque")
    val ann = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
    for (m in listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees")) ann.put(m)
    jeuFo.xp = 10 * 30 * 30
    tapeFo("ls")
    tapeFo("ls")
    verifierFo(Histoire.ouvert(jeuFo, "forge"), "le niveau 4 fait : la Forge s'ouvre")
    verifierFo("forge" in lstFo(Histoire.h(jeuFo).optJSONArray("mondes_annonces")), "annoncée une fois")
    val FD = Forge.dossier(jeuFo)
    verifierFo(File(FD, "enclume.txt").isFile && File(FD, Forge.CARNET).isFile, "la Forge est meublée (enclume, carnet)")
    verifierFo(t("hist.atelier.titre") == "La petite forge des Constructs", "§ 2.19 : l'ancien atelier des Constructs est « la petite forge »")
    val avant = fichiersHorsFo(jeuFo.home, jeuFo.terrain)

    println("3. La traversée, comme dans l'appli")
    tapeFo("cd ~/terrain_terminagotchi/forge")
    verifierFo(lecFo() == ("fo0" to 1), "entrer dans la Forge choisit le monde : ${lecFo()}")
    val sorties = LinkedHashMap<String, String>()
    val parcours: List<() -> String> = listOf(
        { "ls" }, { "cat enclume.txt" },
        { "forge recette" }, { "echo '#!/bin/sh' > cabane.sh" }, { "echo 'mkdir -p cabane' >> cabane.sh" },
        { "echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh" }, { "cat cabane.sh" }, { "sh cabane.sh" },
        { "forge boites" }, { "nom=Pixel; echo \"Bonjour \$nom\"" }, { "echo 'echo \"Bonjour \$1 !\"' > salut.sh" }, { "sh salut.sh Léa" },
        { "echo 'echo \"Tu as donné \$# prénoms.\"' >> salut.sh" }, { "sh salut.sh Léa Tom Sam" },
        { "echo 'read prenom' > question.sh && echo 'echo \"Salut \$prenom !\"' >> question.sh" }, { "echo Léa | sh question.sh" },
        { "forge aiguillage" }, { "ls fantome; echo \$?" }, { "forge code 1" }, { "if [ -f cabane/porte.txt ]; then echo \"La porte est là !\"; fi" },
        { "for i in 1 2 3; do echo \"Tour \$i\"; done" }, { "for i in \$(seq 1 10); do mkdir -p village/cabane_\$i; done" },
        { "ls village | wc -l" }, { "n=3; while [ \$n -gt 0 ]; do echo \$n; n=\$((n - 1)); done" },
        { Forge.toursQuestion(Histoire.graine(jeuFo)).let { (a, z) -> "forge tours ${Forge.toursReponse(a, z)}" } },
        { "forge serpent" }, { "cat serpent.py" }, { "forge erreur IndexError" }, { "doom" },
        { "forge jeu" }, { "cat mon_jeu/devinette.sh" }, { "seq 1 10 | sh mon_jeu/devinette.sh" },
        { "echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_\$s; done' > donjon.sh" }, { "sh donjon.sh" },
        { "echo \"Le trésor est ici !\" > mon_jeu/donjon/salle_3/tresor.txt" }, { "forge carte \"La grotte de Pixel\"" }, { "find mon_jeu" },
        { "forge site" }, { "echo '<h1>Bienvenue chez Pixel</h1>' > site/index.html" },
        { "echo '<p>Ici vit ma créature. Elle adore les cabanes.</p>' >> site/index.html" }, { "echo 'h1 { color: orange; }' > site/style.css" },
        { "echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html" }, { "cat site/index.html" },
        { "curl localhost:8642" }, { "forge serveur" }, { "curl localhost:8642" }, { "forge serveur stop" }, { "forge publier" },
        { "forge multimedia" }, { "ls multimedia" }, { "forge exif multimedia/photo_exemple.jpg" }, { "forge appareil Terminacam" },
        { "forge nettoie multimedia/photo_exemple.jpg" }, { "forge bilan" },
    )
    val vus = mutableListOf<String>()
    for (f in parcours) {
        val c = f()
        val a = lecFo()
        val s = tapeFo(c)
        sorties.putIfAbsent(c, s)
        vus.add("$a $c → ${lecFo()} ${s.take(70).replace("\n", "⏎")} ${jeuFo.indiceLecon ?: ""}")
        if (System.getenv("TG_DEBUG") != null) println("    · " + vus.last())
        if (Histoire.fini(jeuFo, "forge")) break
    }
    if (!Histoire.fini(jeuFo, "forge")) vus.takeLast(8).forEach { println("      $it") }
    verifierFo(Histoire.fini(jeuFo, "forge"), "la Forge est traversée jusqu'au bout (fo0 → fo7) ${lecFo()}")
    verifierFo(File(FD, "cabane/porte.txt").isFile && File(FD, "cabane/toit.txt").isFile, "sh cabane.sh : la cabane est bâtie")
    verifierFo(sorties["nom=Pixel; echo \"Bonjour \$nom\""]?.trim() == "Bonjour Pixel", "la boîte remplie et ouverte sur la même ligne : Bonjour Pixel")
    verifierFo(sorties["echo Léa | sh question.sh"]?.trim() == "Salut Léa !", "read reçoit sa réponse par un tuyau")
    verifierFo(sorties["ls village | wc -l"]?.trim() == "10", "le village : 10 cabanes en une boucle")
    verifierFo("Bravo" in (sorties["seq 1 10 | sh mon_jeu/devinette.sh"] ?: ""), "le robot (seq 1 10 |) trouve le nombre de la devinette")
    verifierFo("IndexError" in (sorties["forge serpent"] ?: ""), "le serpent est raconté : le Traceback que Python écrirait")
    verifierFo(sorties.entries.filter { it.key == "curl localhost:8642" }.isNotEmpty() && "Bienvenue chez Pixel" in (sorties.entries.last { it.key == "curl localhost:8642" }.value) ||
        vus.any { "curl localhost:8642" in it && "Bienvenue" in it }, "la lanterne de l'appli sert la page de l'enfant, curl la lit")
    verifierFo(Forge.portSite() !in Phare.actifs(), "puis la lanterne est éteinte")
    verifierFo("Terminacam" in (sorties["forge exif multimedia/photo_exemple.jpg"] ?: ""), "les métadonnées démasquées : Terminacam")
    verifierFo(Forge.photoPropre(jeuFo), "la photo d'exemple est nettoyée (plus d'Exif)")
    val ex = Recompenses.etat(jeuFo).getJSONObject("exploits").keys().asSequence().toList()
    verifierFo("forge.premier_coup" in ex && "forge.sans_indice" in ex, "les exploits « premier coup » et « sans indice » ($ex)")
    verifierFo("marteau_de_forge" in lstFo(Quetes.q(jeuFo).optJSONArray("objets")), "récompense du monde : le petit marteau de forge (posé, jamais porté)")
    val n = Maison.noeuds(jeuFo).firstOrNull { it.genre == "jeu" }
    verifierFo(n != null && "La grotte de Pixel" in n.etiquette && Maison.emoji(n) == "🎮", "le jeu de l'enfant est un nouveau lieu sur la carte : ${n?.etiquette}")
    verifierFo(fichiersHorsFo(jeuFo.home, jeuFo.terrain).filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet() ==
        avant.filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet(), "rien d'écrit hors du terrain")
    val dehors = File(dossier, "photo.jpg").apply { writeBytes(Forge.photoOctets()) }
    verifierFo(t("fo.exif.hors_terrain") in tapeFo("forge exif ${dehors.path}") && t("fo.exif.hors_terrain") in tapeFo("forge nettoie ${dehors.path}") &&
        Forge.aExif(dehors.readBytes()), "forge exif et forge nettoie refusent une photo hors du terrain")

    println("4. Les variantes réservées, le dessin")
    val j2 = Jeu(AppareilFo(File(dossier, "j2").apply { mkdirs() }, assets))
    val reserve = { e: String, vv: String -> Recompenses.reservee(j2, vv, e) }
    verifierFo(reserve("fondelin", "lave") && reserve("boulonnet", "neon") && reserve("tisonnier", "mecanique") && !reserve("fondelin", "volcan"),
        "fondelin:lave, boulonnet:neon, tisonnier:mecanique réservées avant l'exploit ; fondelin:volcan non")
    verifierFo(!Recompenses.reservee(jeuFo, "lave", "fondelin"), "… et libérées après l'exploit")
    val tl = ToileFo()
    ForgeDessin.forge(tl, Deploie.forges("sh cabane.sh")[0], 0.4, 0f, 0f, 320f, 96f, 1f)
    ForgeDessin.forge(tl, Deploie.forges("for i in 1 2 3; do echo \$i; done")[0], 0.4, 0f, 0f, 320f, 60f, 1f)
    ForgeDessin.forge(tl, Deploie.forges("python3 serpent.py")[0], 0.4, 0f, 0f, 320f, 96f, 1f)
    ForgeDessin.village(tl, 10, 0.6, 0f, 0f, 320f, 120f, 1f)
    ForgeDessin.atelier(tl, 0.3, 0f, 0f, 320f, 180f, 1f)
    verifierFo(tl.n > 60 && tl.textes.any { "parchemin" in it } && tl.textes.any { "🔥" in it }, "le dessin : le parchemin qui s'enflamme, le manège, le serpent, le village, l'atelier")

    println("\n$okFo réussis, $koFo échoués")
    kotlin.system.exitProcess(if (koFo == 0) 0 else 1)
}

fun t(cle: String, vararg p: Pair<String, Any?>) = fr.terminagotchi.t(cle, *p)
