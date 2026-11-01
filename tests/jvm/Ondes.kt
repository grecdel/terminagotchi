/*
 * Test JVM de la Tour des Ondes (phase 5) sur Android, portage de pc/outils/test_ondes.py :
 *   1. les vecteurs communs donnees/ondes/vecteurs.json (fréquences tapées, longueur d'onde et réponse de l'enfant,
 *      mur, canaux et bandes Wi-Fi, résumé anonyme, règle, bandes libres et choix mélangés comme random.shuffle de
 *      Python, vallée et plus petit SF, temps d'émission LoRa, règle du 1 %, maillage avec nœuds coupés, cible de la
 *      tempête, antennes, vue déployée) : EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. l'arbre du Carrefour : la Tour s'ouvre après le Port P7 et la Salle des Machines M2 (annoncée une fois, dès la
 *      leçon finie) ;
 *   3. la traversée on0 → on10 comme dans l'appli (les radios racontées : canaux d'exemple, radios du téléphone,
 *      W5 et W6 racontés ; bc remplacé par le calcul en entiers), la tempête réussie (exploit « onde », une fois),
 *      l'antenne miniature ; rien hors du terrain ; aucun message tapé dans le carnet ;
 *   4. les variantes réservées, le dessin (onde, mur, spectre, vallée, maillage, antenne, tour de repli) sur une toile
 *      d'essai ; la vue déployée sait quel bloc touche quelle radio.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Ondes.kt -d ond.jar
 *   java -cp <imitations>:<appli.jar>:ond.jar:kotlin-stdlib.jar OndesKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Ondes
import fr.terminagotchi.OndesDessin
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsOn(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilOn(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsOn(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileOn : Toile {
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

var okOn = 0
var koOn = 0
fun verifierOn(c: Boolean, m: String) {
    if (c) okOn++ else koOn++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuOn: Jeu
lateinit var shellOn: Shell
lateinit var cmdOn: Commandes

fun lstOn(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun bashOn(cmd: String, ou: File = shellOn.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuOn.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeOn(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellOn.executer(cmd)
    else {
        val interne = cmdOn.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashOn(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuOn, cmd, colle = false, rappel = false, hasard = false, cwd = shellOn.dossier, code = code)
    return sortie
}

fun lecOn(): Pair<String?, Int> = Histoire.leconCourante(jeuOn)?.id to jeuOn.etape

fun fichiersHorsOn(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun chemin(a: JSONArray?): List<String>? = if (a == null) null else lstOn(a)

/** Trois coupures du chemin qui laissent passer le message (comme l'enfant qui lit mesh-route). */
fun tempeteOn(cible: String, coupes: List<String> = emptyList()): List<String>? {
    if (coupes.size == 3) return coupes
    val r = Ondes.route("camp", cible, coupes) ?: return null
    for (x in r.drop(1).dropLast(1)) if (Ondes.route("camp", cible, coupes + x) != null) tempeteOn(cible, coupes + x)?.let { return it }
    return null
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_on_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilOn(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuOn = Jeu(app)
    jeuOn.changerLangue("fr")
    jeuOn.nom = "Pixel"
    shellOn = Shell(jeuOn.home)
    cmdOn = Commandes(app, jeuOn, { shellOn.dossier })
    jeuOn.module("explo").put("ouverte", true)
    jeuOn.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/ondes/vecteurs.json").readText())
    var ko = 0
    val fr = v.getJSONArray("frequences")
    for (i in 0 until fr.length()) { val x = fr.getJSONObject(i)
        val k = Ondes.frequenceDe(x.getString("texte"))
        val att = if (x.isNull("resultat")) null else x.getJSONArray("resultat").let { it.getLong(0) to (if (it.isNull(1)) null else it.getString(1)) }
        if (k != att) { ko++; println("    fréquence $x → $k") } }
    verifierOn(ko == 0, "${fr.length()} fréquences tapées (lora, 868M, 2,4 GHz…)")
    ko = 0
    val lo = v.getJSONArray("longueurs")
    for (i in 0 until lo.length()) { val x = lo.getJSONObject(i); val hz = x.getLong("hz")
        if (Math.abs(Ondes.longueurOnde(hz) - x.getDouble("m")) > 1e-12 * x.getDouble("m") || Ondes.texteLongueur(Ondes.longueurOnde(hz)) != x.getString("texte") ||
            Math.abs(Ondes.periodes(hz) - x.getDouble("periodes")) > 1e-9) { ko++; println("    longueur $x → ${Ondes.texteLongueur(Ondes.longueurOnde(hz))}") } }
    verifierOn(ko == 0, "${lo.length()} longueurs d'onde (λ = v / f) et leur texte")
    ko = 0
    val lok = v.getJSONArray("longueur_ok")
    for (i in 0 until lok.length()) { val x = lok.getJSONObject(i)
        if (Ondes.longueurOk(x.getString("reponse"), 868_000_000L) != x.getBoolean("ok")) { ko++; println("    réponse $x") } }
    verifierOn(ko == 0, "${lok.length()} réponses de longueur d'onde jugées comme en Python")
    ko = 0
    val mu = v.getJSONArray("murs")
    for (i in 0 until mu.length()) { val x = mu.getJSONObject(i)
        val db = Ondes.affaiblissement(x.getString("matiere"), x.getString("tech"), x.getInt("n"))
        val (a1, p1) = Ondes.restantPc(db)
        if (db != x.getInt("db") || listOf(a1, p1) != (0..1).map { x.getJSONArray("restant").getInt(it) }) { ko++; println("    mur $x → $db $a1 $p1") } }
    verifierOn(ko == 0 && Ondes.traverseLeMieux() == v.getString("traverse"), "${mu.length()} murs : décibels et pour cent restants")
    ko = 0
    val ca = v.getJSONArray("canaux")
    for (i in 0 until ca.length()) { val x = ca.getJSONObject(i)
        if (Ondes.canal(x.getInt("mhz")) != (if (x.isNull("canal")) null else x.getInt("canal")) || Ondes.bande(x.getInt("mhz")) != (if (x.isNull("bande")) null else x.getString("bande"))) { ko++; println("    canal $x") } }
    verifierOn(ko == 0, "${ca.length()} canaux et bandes Wi-Fi")
    ko = 0
    val re = v.getJSONArray("resumes")
    for (i in 0 until re.length()) { val x = re.getJSONObject(i)
        val r = Ondes.resumeWifi((0 until x.getJSONArray("freqs").length()).map { x.getJSONArray("freqs").getInt(it) })
        val b = x.getJSONObject("bandes"); val c = x.getJSONObject("canaux")
        if (r.n != x.getInt("n") || r.bandes.keys != b.keys().asSequence().toSet() || r.bandes.any { it.value != b.getInt(it.key) } ||
            r.canaux.keys.map { "$it" }.toSet() != c.keys().asSequence().toSet() || r.canaux.any { it.value != c.getInt("${it.key}") }) { ko++; println("    résumé $x") } }
    val rs = v.getJSONArray("reseaux")
    for (i in 0 until rs.length()) { val x = rs.getJSONObject(i)
        if (Ondes.reseauxOk(x.getString("reponse"), x.getInt("vrai")) != x.getBoolean("ok")) { ko++; println("    réseaux $x") } }
    verifierOn(ko == 0, "${re.length()} résumés anonymes, ${rs.length()} nombres de réseaux")
    ko = 0
    val pa = v.getJSONArray("parties")
    for (i in 0 until pa.length()) { val x = pa.getJSONObject(i); val g = x.getString("graine")
        val rg = Ondes.regleCartes(g).map { listOf(it.first.toString(), it.second) }
        val rgA = (0 until x.getJSONArray("regle").length()).map { lstOn(x.getJSONArray("regle").getJSONArray(it)) }
        val li = Ondes.libreCartes(g).map { listOf("${it.first}", it.second, it.third) }
        val liA = (0 until x.getJSONArray("libre").length()).map { lstOn(x.getJSONArray("libre").getJSONArray(it)) }
        val ch = Ondes.choixCartes(g).map { listOf("${it.first}", it.second, it.third) }
        val chA = (0 until x.getJSONArray("choix").length()).map { lstOn(x.getJSONArray("choix").getJSONArray(it)) }
        if (rg != rgA || Ondes.regleReponse(g).map { "$it" } != lstOn(x.getJSONArray("regle_reponse")) || li != liA || ch != chA ||
            Ondes.valleeM(g) != x.getInt("vallee") || Ondes.sfMin(Ondes.valleeM(g)) != x.getInt("sf") || Ondes.defiCible(g) != x.getString("cible")) { ko++; println("    partie $g : $rg $li $ch") } }
    verifierOn(ko == 0, "${pa.length()} parties : règle, bandes, choix mélangés comme en Python ; vallée, SF, cible de la tempête")
    ko = 0
    val lr = v.getJSONArray("lora")
    for (i in 0 until lr.length()) { val x = lr.getJSONObject(i); val sf = x.getInt("sf"); val oc = x.getInt("octets")
        if (Ondes.dureeSymboleUs(sf) != x.getLong("symbole_us") || Ondes.symbolesMessage(sf, oc) != x.getInt("symboles") ||
            Ondes.tempsEmissionUs(sf, oc) != x.getLong("us") || Ondes.messagesHeure(sf, oc) != x.getLong("par_heure")) { ko++; println("    LoRa $x → ${Ondes.tempsEmissionUs(sf, oc)}") } }
    val po = v.getJSONArray("portees")
    for (i in 0 until po.length()) { val x = po.getJSONObject(i)
        if (Ondes.sfMin(x.getInt("distance")) != (if (x.isNull("sf")) null else x.getInt("sf"))) { ko++; println("    portée $x") } }
    val me = v.getJSONArray("messages")
    for (i in 0 until me.length()) { val x = me.getJSONObject(i)
        if (Ondes.messagesOk(x.getString("reponse"), x.getInt("sf")) != x.getBoolean("ok")) { ko++; println("    messages $x") } }
    verifierOn(ko == 0 && Ondes.budgetUs() == v.getLong("budget_us"), "${lr.length()} temps d'émission LoRa, ${po.length()} portées, ${me.length()} réponses (règle du 1 %)")
    ko = 0
    val ma = v.getJSONArray("maillage")
    for (i in 0 until ma.length()) { val x = ma.getJSONObject(i); val cs = lstOn(x.getJSONArray("coupes"))
        val ro = x.getJSONObject("routes"); val en = x.getJSONObject("envois"); val vo = x.getJSONObject("voisins")
        for (d in Ondes.noeuds()) {
            if (Ondes.route("camp", d, cs) != (if (ro.isNull(d)) null else lstOn(ro.getJSONArray(d)))) { ko++; println("    route $cs → $d : ${Ondes.route("camp", d, cs)}") }
            if (Ondes.voisins(d, cs) != lstOn(vo.getJSONArray(d))) { ko++; println("    voisins $cs $d") }
        }
        for (d in Ondes.noeuds() + "lune") { val e = Ondes.envoi(d, cs); val a = en.getJSONObject(d)
            if (e.ok != a.getBoolean("ok") || e.chemin != lstOn(a.getJSONArray("chemin")) || e.raison != a.getString("raison") || e.sauts != a.getInt("sauts")) { ko++; println("    envoi $cs $d") } }
        val ino = Ondes.inondation("camp", cs)
        val inoA = (0 until x.getJSONArray("inondation").length()).map { lstOn(x.getJSONArray("inondation").getJSONArray(it)) }
        if (ino != inoA) { ko++; println("    inondation $cs → $ino") } }
    verifierOn(ko == 0, "${ma.length()} maillages : chemins, voisins, inondation, envois avec des nœuds coupés")
    ko = 0
    val an = v.getJSONArray("antennes")
    for (i in 0 until an.length()) { val x = an.getJSONObject(i)
        val k = Ondes.antennesDe(x.getString("ligne")).map { listOf(it.first, it.second) }
        val att = (0 until x.getJSONArray("antennes").length()).map { lstOn(x.getJSONArray("antennes").getJSONArray(it)) }
        if (k != att) { ko++; println("    antennes ${x.getString("ligne")} → $k (attendu $att)") } }
    val de = v.getJSONArray("deploie")
    for (i in 0 until de.length()) { val x = de.getJSONObject(i)
        val k = Deploie.antennes(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.radio, it.sens) }
        val att = (0 until x.getJSONArray("antennes").length()).map { x.getJSONArray("antennes").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("radio"), it.getString("sens")) }
        if (k != att) { ko++; println("    vue déployée ${x.getString("ligne")} → $k (attendu $att)") } }
    verifierOn(ko == 0, "${an.length()} lignes : les antennes (lire, chercher, changer, écouter, émettre, simuler) et la vue déployée")

    println("2. L'arbre du Carrefour : quand la Tour s'ouvre")
    val h = Histoire.h(jeuOn)
    verifierOn(!Histoire.ouvert(jeuOn, "ondes"), "fermée au début : il manque ${Ondes.manque(jeuOn)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid", "bibliotheque")) h.getJSONArray("ailes").put(c)
    faits.put("port7")
    h.put("mondes_annonces", JSONArray(listOf("port", "crypte", "machinerie")))
    verifierOn(!Histoire.ouvert(jeuOn, "ondes") && Ondes.manque(jeuOn).any { "Des 0 et des 1" in it }, "le Port P7 sans la Salle M2 : fermée (${Ondes.manque(jeuOn)})")
    faits.put("sm3")
    h.put("annonce_attente", true)
    Histoire.tick(jeuOn, "ls", false, jeuOn.home, 0)
    verifierOn(Histoire.ouvert(jeuOn, "ondes") && "ondes" in lstOn(h.optJSONArray("mondes_annonces")) && !Ondes.annonce(jeuOn),
        "P7 et M2 faits : la Tour s'ouvre, annoncée une seule fois")
    verifierOn("sm3" in Ondes.leconsQuiOuvrent() && "port7" in Ondes.leconsQuiOuvrent(), "les leçons qui ouvrent la Tour l'annoncent dès qu'elles sont finies")
    val D = File(jeuOn.terrain, "ondes")
    D.mkdirs()
    Histoire.tick(jeuOn, "ls", false, jeuOn.home, 0)
    verifierOn(File(D, "plan_de_la_tour.txt").isFile && File(D, "capteurs_exemple.json").isFile, "la Tour est meublée (plan, capteurs d'exemple)")
    val capPy = "{\"time\": \"2026-11-01 08:00:02\", \"model\": \"Exemple-Thermo\", \"id\": 4021, \"channel\": 1, \"battery_ok\": 1, \"temperature_C\": 7.4, \"humidity\": 81}"
    verifierOn(Ondes.capteursTexte().lines().first() == capPy, "le fichier des capteurs est le même qu'en Python")

    println("3. La traversée de la Tour sur le téléphone")
    val avantFichiers = fichiersHorsOn(jeuOn.home, jeuOn.terrain)
    jeuOn.xp = 10 * 30 * 30
    tapeOn("cd ~/terrain_terminagotchi/ondes")
    verifierOn(lecOn() == ("on0" to 1), "entrer dans la Tour choisit le monde : ${lecOn()}")
    val gr = Histoire.graine(jeuOn)
    val cible = Ondes.defiCible(gr)
    val sol = tempeteOn(cible)!!
    val sf = Ondes.sfMin(Ondes.valleeM(gr))!!
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat plan_de_la_tour.txt" },
        { "ondes onde" }, { "ondes onde lora" }, { "echo \$((300000000 / 2400000))" }, { "ondes longueur 12" }, { "ondes longueur 34.6" },
        { "ondes mur" }, { "ondes traverse lora" },
        { "ondes canaux" }, { "ondes voisins" }, { "ondes radios" },
        { "ondes spectre" }, { "ondes regle" }, { "ondes regle " + Ondes.regleReponse(gr).joinToString(" ") },
        { "ondes libre" }, { "ondes libre " + Ondes.libreCartes(gr).joinToString(" ") { it.third } },
        { "ondes lora" }, { "echo \$((4096 * 1000000 / 125000))" }, { "ondes temps" }, { "ondes vallee" }, { "ondes vallee 7" }, { "ondes vallee $sf" },
        { "echo \$((3600 * 1 / 100))" }, { "ondes messages ${Ondes.messagesHeure(sf)}" },
        { "ondes passerelle" }, { "ondes maillage" }, { "ondes choix" }, { "ondes choix " + Ondes.choixCartes(gr).joinToString(" ") { it.third } },
        { "mesh-route" }, { "mesh-envoie feu \"bonjour\"" }, { "mesh-coupe roche" }, { "mesh-envoie feu \"bonjour\"" }, { "mesh-route feu" }, { "mesh-coupe -r" },
        { "ondes defi" }, { "mesh-coupe ${sol[0]}" }, { "mesh-coupe ${sol[1]}" }, { "mesh-coupe ${sol[2]}" }, { "mesh-envoie $cible \"SOS\"" },
        { "ondes adulte" }, { "ondes noeud" },
        { "ondes ecoute" }, { "ondes avions" }, { "cat capteurs_exemple.json" }, { "grep -o '\"temperature_C\": [-0-9.]*' capteurs_exemple.json" }, { "ondes anonyme" },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = f()
        val avant = lecOn()
        val s = tapeOn(c)
        sorties[c] = s
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecOn()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuOn, "ondes")) break
    }
    verifierOn(Histoire.fini(jeuOn, "ondes"), "la Tour est traversée jusqu'au bout (on0 → on10) : ${lecOn()}")
    verifierOn("125" in (sorties["echo \$((300000000 / 2400000))"] ?: "") && "✖" in (sorties["ondes longueur 12"] ?: ""), "λ du Wi-Fi : 125 mm ; 12 cm refusé pour LoRa")
    verifierOn("EXEMPLE" in (sorties["ondes canaux"] ?: ""), "les canaux du téléphone : un quartier d'exemple (rien n'est lu des voisins)")
    verifierOn("✔" in (sorties["mesh-envoie $cible \"SOS\""] ?: "") && "🌩" in (sorties["mesh-envoie $cible \"SOS\""] ?: ""), "la tempête : trois nœuds coupés, le SOS passe")
    val ex = Recompenses.etat(jeuOn).getJSONObject("exploits").keys().asSequence().toList()
    verifierOn("ondes.onde" in ex, "l'exploit « onde » ($ex)")
    verifierOn("antenne_miniature" in lstOn(Quetes.q(jeuOn).optJSONArray("objets")), "récompense du monde : une antenne miniature")
    val carnet = Ondes.carnet(jeuOn)
    verifierOn("bonjour" !in carnet && "SOS" !in carnet, "aucun message tapé n'est gardé dans le carnet")
    val nouveaux = fichiersHorsOn(jeuOn.home, jeuOn.terrain) - avantFichiers
    verifierOn(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")

    println("4. Les variantes réservées, le dessin, la vue déployée")
    val j2 = Jeu(AppareilOn(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierOn(Recompenses.reservee(j2, "orage", "zapiot") && Recompenses.reservee(j2, "orage", "ventouzar") &&
        !Recompenses.reservee(j2, "orage", "fulgurox") && !Recompenses.reservee(jeuOn, "orage", "zapiot"),
        "zapiot:orage et ventouzar:orage réservées avant l'exploit, libérées après ; fulgurox:orage non")
    val tl = ToileOn()
    OndesDessin.onde(tl, 868_000_000L, "lora", 0.3, 0f, 0f, 400f, 160f, 1f)
    OndesDessin.mur(tl, "beton", 2, 0.5, 0f, 0f, 400f, 240f, 1f)
    OndesDessin.spectre(tl, 0f, 0f, 400f, 260f, 1f, listOf("lora"))
    OndesDessin.vallee(tl, 11, 7000, 0.7, 0f, 0f, 400f, 200f, 1f)
    OndesDessin.maillage(tl, listOf("roche"), Ondes.route("camp", "feu", listOf("roche"))!!, 0.5, 0f, 0f, 400f, 260f, 1f)
    OndesDessin.antenne(tl, Deploie.Antenne(0, "nmcli", "wifi", "lit"), 0.4, 0f, 0f, 400f, 110f, 1f)
    OndesDessin.tour(tl, 0.3, 0f, 0f, 400f, 225f, 1f)
    verifierOn(tl.n > 300 && tl.textes.any { "LoRa" in it } && tl.textes.any { it == "λ" } && tl.textes.any { "feu" == it },
        "le dessin : onde, mur, spectre, vallée, maillage, antenne, tour (${tl.n} traits)")
    val vue = Deploie.vue("nmcli radio | head -1")!!
    verifierOn(vue.antenneDe(vue.blocs[0])?.radio == "wifi" && vue.antenneDe(vue.blocs[0])?.sens == "lit" && vue.antenneDe(vue.blocs[1]) == null,
        "la vue déployée sait que nmcli radio lit le Wi-Fi")

    println("\n$okOn réussis, $koOn échoués")
    kotlin.system.exitProcess(if (koOn == 0) 0 else 1)
}
