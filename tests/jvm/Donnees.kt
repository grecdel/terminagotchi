/*
 * Test JVM de la Salle des Données (phase 5) sur Android, portage de pc/outils/test_donnees.py :
 *   1. les vecteurs communs donnees/donnees/vecteurs.json : l'export CSV de collections d'essai (vides, minuscules, avec
 *      accents, shiny, variantes), chaque statistique, le nom mal écrit (toutes les espèces) et le carnet du soigneur dans
 *      les 14 langues, les instructions de collection.db, la mise en forme de sqlite3 (résultats typés du vrai moteur
 *      SQLite), le laboratoire de la vue déployée, et le PETIT AWK de l'appli contre la sortie du VRAI awk ;
 *   2. l'arbre du Carrefour : la Salle s'ouvre après le niveau 4 du tronc (annoncée une fois), meublée ;
 *   3. la traversée dn0 → dn6 comme dans l'appli (collection --csv, le petit awk, le petit sqlite3 — branché ici sur le
 *      SQLite de Python, sur le téléphone sur celui d'Android), sur une VRAIE collection de 7 bestioles ; l'exploit
 *      « une statistique juste » ; le boulier ; rien hors du terrain ; la base en lecture seule ;
 *   4. les variantes réservées, le dessin (labo, podium, laboratoire de repli) sur une toile d'essai.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Donnees.kt -d don.jar
 *   java -cp <imitations>:<appli.jar>:don.jar:kotlin-stdlib.jar DonneesKt app/src/main/assets
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Donnees
import fr.terminagotchi.DonneesAwk
import fr.terminagotchi.DonneesDessin
import fr.terminagotchi.DonneesSql
import fr.terminagotchi.Explo
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsDn(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilDn(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsDn(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileDn : Toile {
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

/** Le moteur SQLite des tests : celui de Python (le vrai SQLite), à la place de celui d'Android. */
object MoteurPython : DonneesSql.Moteur {
    private fun python(script: String, entree: String): String {
        val p = ProcessBuilder("python3", "-c", script).redirectErrorStream(true).start()
        p.outputStream.use { it.write(entree.toByteArray()) }
        val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
        p.waitFor()
        return s
    }
    override fun creer(f: File, instructions: List<Pair<String, List<Any?>>>): Boolean {
        val j = JSONArray(instructions.map { JSONArray().put(it.first).put(JSONArray(it.second)) })
        val s = python("import json,sqlite3,sys,os\nd=json.load(sys.stdin)\nf=sys.argv[1] if len(sys.argv)>1 else ''\n" +
            "p='${f.path}'\nos.path.exists(p) and os.remove(p)\nc=sqlite3.connect(p)\n" +
            "[c.execute(q,tuple(a)) for q,a in d]\nc.commit();c.close();print('ok')", j.toString())
        return s.trim() == "ok"
    }
    override fun requete(f: File, sql: String): DonneesSql.Resultat {
        val s = python("import json,sqlite3,sys\nq=sys.stdin.read()\n" +
            "try:\n c=sqlite3.connect('file:${f.path}?mode=ro',uri=True);cur=c.execute(q)\n" +
            " r=[[['null',None] if v is None else ['int',v] if isinstance(v,int) else ['real',v] if isinstance(v,float) else ['text',v] for v in l] for l in cur.fetchall()]\n" +
            " print(json.dumps({'c':[d[0] for d in cur.description or []],'r':r}))\nexcept Exception as e:\n print(json.dumps({'e':str(e)}))", sql)
        val o = JSONObject(s.trim())
        if (o.has("e")) throw DonneesSql.Erreur(o.getString("e"))
        return DonneesSql.Resultat(lstDn(o.getJSONArray("c")), (0 until o.getJSONArray("r").length()).map { typees(o.getJSONArray("r").getJSONArray(it)) })
    }
}

fun typees(a: JSONArray): List<Any?> = (0 until a.length()).map { i ->
    val x = a.getJSONArray(i)
    when (x.getString(0)) { "null" -> null; "int" -> x.getLong(1); "real" -> x.getDouble(1); else -> x.getString(1) }
}

var okDn = 0
var koDn = 0
fun verifierDn(c: Boolean, m: String) {
    if (c) okDn++ else koDn++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuDn: Jeu
lateinit var shellDn: Shell
lateinit var cmdDn: Commandes

fun lstDn(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsDn(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }
fun rowsDn(a: JSONArray): List<Map<String, String>> = objetsDn(a).map { o -> o.keys().asSequence().associateWith { o.getString(it) } }

fun bashDn(cmd: String, ou: File = shellDn.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("sh", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuDn.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeDn(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellDn.executer(cmd)
    else {
        val interne = cmdDn.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashDn(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuDn, cmd, colle = false, rappel = false, hasard = false, cwd = shellDn.dossier, code = code)
    return sortie
}

fun lecDn(): Pair<String?, Int> = Histoire.leconCourante(jeuDn)?.id to jeuDn.etape

fun fichiersHorsDn(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun individuDn(nom: String, k: Int, shiny: Boolean = false): JSONObject {
    val e = Bestiaire.espece(nom)!!
    val st = JSONObject()
    for ((s, v) in e.stats) st.put(s, v + (k * 5) % 9)
    return JSONObject().put("id", "id$k").put("espece", e.nom).put("variante", "classique").put("shiny", shiny)
        .put("date", 1793534400000L - k * 86400000L).put("stats", st).put("marque", "étoile")
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_dn_" + System.nanoTime()).apply { mkdirs() }
    java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"))
    val app = AppareilDn(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuDn = Jeu(app)
    jeuDn.changerLangue("fr")
    jeuDn.nom = "Pixel"
    shellDn = Shell(jeuDn.home)
    cmdDn = Commandes(app, jeuDn, { shellDn.dossier })
    jeuDn.module("explo").put("ouverte", true)
    jeuDn.terrain.mkdirs()
    DonneesSql.moteur = MoteurPython

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/donnees/vecteurs.json").readText())
    var ko = 0
    val cols = v.getJSONObject("collections")
    for (nom in cols.keys()) {
        val x = cols.getJSONObject(nom)
        val rows = Donnees.lignesCollection(x.getJSONArray("captures"))
        val csv = Donnees.csvTexte(rows)
        if (csv != x.getString("csv")) { ko++; println("    csv $nom :\n$csv≠\n${x.getString("csv")}") }
        val r = Donnees.lireCsv(x.getString("csv"))
        fun eff(l: List<Pair<String, Int>>) = l.map { listOf(it.first, "${it.second}") }
        fun effV(k: String) = objetsDn(JSONArray()).let { (0 until x.getJSONArray(k).length()).map { lstDn(x.getJSONArray(k).getJSONArray(it)) } }
        val faits = listOf(
            "lignes" to (r.size == x.getInt("lignes")),
            "effectifs" to (eff(Donnees.effectifs(r.map { it["nom"]!! })) == effV("effectifs_noms") && eff(Donnees.effectifs(r.map { it["type"]!! })) == effV("effectifs_types")),
            "listes" to (Donnees.forcesTxt(r) == x.getString("forces") && Donnees.especesTxt(r) == x.getString("especes")),
            "top3" to (Donnees.top3(r).map { "$it" } == lstDn(x.getJSONArray("top3"))),
            "shiny" to (Donnees.nbShiny(r) == x.getInt("shiny") && Donnees.somme(r) == x.getInt("somme")),
            "moyenne" to (Donnees.moyenne(r) == x.getDouble("moyenne") && Donnees.nombreAwk(Donnees.moyenne(r)) == x.getString("moyenne_awk")),
            "medianes" to (Donnees.medianes(r) == (0 until x.getJSONArray("medianes").length()).map { x.getJSONArray("medianes").getDouble(it) }),
            "etendue" to (Donnees.etendue(r) == x.getInt("etendue") && Donnees.typesMajoritaires(r) == lstDn(x.getJSONArray("types_majoritaires"))),
            "faute" to ((Donnees.cibleFaute(r) ?: "") == x.optString("cible", "").let { if (x.isNull("cible")) "" else it } &&
                Donnees.carnetSoigneur(r).let { it[0] == x.getString("carnet_faux") && it[1] == x.getString("carnet_juste") && it[2] == x.getString("faute") }),
        )
        for ((k, ok) in faits) if (!ok) { ko++; println("    $nom : $k") }
        val base = Donnees.requetesBase(r).map { JSONArray().put(it.first).put(JSONArray(it.second)).toString() }
        val att = (0 until x.getJSONArray("base").length()).map { x.getJSONArray("base").getJSONArray(it).toString() }
        if (base != att) { ko++; println("    $nom : base ${base.firstOrNull { it !in att }}") }
    }
    verifierDn(ko == 0, "${cols.length()} collections (dont la collection de test) : le CSV, chaque statistique, le carnet du soigneur et collection.db identiques")
    ko = 0
    val r7 = Donnees.lireCsv(cols.getJSONObject("sept").getString("csv"))
    val carnets = v.getJSONObject("carnets")
    for (code in carnets.keys()) {
        Langue.definir(code)
        val c = Donnees.carnetSoigneur(r7)
        if (c[0] != carnets.getJSONObject(code).getString("faux") || c[1] != carnets.getJSONObject(code).getString("juste")) { ko++; println("    carnet $code :\n${c[1]}≠\n${carnets.getJSONObject(code).getString("juste")}") }
    }
    Langue.definir("fr")
    verifierDn(ko == 0, "le carnet du soigneur (et sa faute) identique dans les ${carnets.length()} langues")
    val tous = Bestiaire.especes.map { it.nom }.toSet()
    val fautes = v.getJSONObject("fautes")
    val mauvaises = fautes.keys().asSequence().filter { Donnees.faute(it, tous) != fautes.getString(it) }.toList()
    verifierDn(mauvaises.isEmpty() && fautes.length() == Bestiaire.especes.size, "le nom mal écrit, pour les ${fautes.length()} espèces : identique ${mauvaises.take(3)}")
    ko = 0
    for (x in objetsDn(v.getJSONArray("lire"))) if (Donnees.lireCsv(x.getString("texte")) != rowsDn(x.getJSONArray("lignes"))) { ko++; println("    lire ${x.getString("texte").take(40)}") }
    for (x in objetsDn(v.getJSONArray("nombres"))) {
        val d = x.getDouble("x")
        if (DonneesAwk.nombre(d) != x.getString("awk") || DonneesSql.valeur(d) != x.getString("sql")) { ko++; println("    nombre $d : ${DonneesAwk.nombre(d)} ${DonneesSql.valeur(d)} ≠ ${x.getString("awk")} ${x.getString("sql")}") }
    }
    for (x in objetsDn(v.getJSONArray("sql_valeurs"))) {
        val t = typees(JSONArray().put(x.getJSONArray("v")))[0]
        if (DonneesSql.valeur(t) != x.getString("sql")) { ko++; println("    valeur sql $t") }
    }
    for (x in objetsDn(v.getJSONArray("tables"))) if (DonneesSql.tablesTexte(lstDn(x.getJSONArray("noms"))) != x.getString("texte")) { ko++; println("    .tables") }
    for (x in objetsDn(v.getJSONArray("requetes"))) {
        val res = DonneesSql.Resultat(lstDn(x.getJSONArray("colonnes")), (0 until x.getJSONArray("resultat").length()).map { typees(x.getJSONArray("resultat").getJSONArray(it)) })
        if (DonneesSql.lignes(res).joinToString("\n") != x.getString("texte")) { ko++; println("    requête ${x.getString("sql")} : ${DonneesSql.lignes(res)}") }
    }
    verifierDn(ko == 0, "la lecture du tableau, les nombres d'awk (%.6g) et de sqlite3 (%!.15g), .tables et ${v.getJSONArray("requetes").length()} résultats de requêtes : identiques")
    ko = 0
    for (x in objetsDn(v.getJSONArray("labo"))) {
        val l = x.getString("ligne")
        val a = Donnees.labosDe(l).map { listOf(it.outil, it.instrument, it.de, it.vers) }
        val b = (0 until x.getJSONArray("labos").length()).map { lstDn(x.getJSONArray("labos").getJSONArray(it)) }
        val d1 = Deploie.labos(l).map { listOf("${it.seg}", it.cmd, it.outil, it.instrument, it.de, it.vers) }
        val d2 = objetsDn(x.getJSONArray("deploie")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("instrument"), it.getString("de"), it.getString("vers")) }
        if (a != b || d1 != d2) { ko++; println("    labo « $l » : $a / $d1") }
    }
    verifierDn(ko == 0, "le laboratoire de la vue déployée (quel instrument pour quelle commande) : identique")
    ko = 0
    val entrees = v.getJSONObject("awk_entrees")
    for (x in objetsDn(v.getJSONArray("awk"))) {
        val o = lstDn(x.getJSONArray("options"))
        val fs = if (o.isEmpty()) null else if (o[0] == "-F") o[1] else o[0].substring(2)
        val (s, _) = DonneesAwk.executer(x.getString("programme"), entrees.getString(x.getString("entree")), fs)
        if (s != x.getString("sortie")) { ko++; println("    awk ${x.getString("programme")} :\n$s≠\n${x.getString("sortie")}") }
    }
    verifierDn(ko == 0, "le petit awk de l'appli : ${v.getJSONArray("awk").length()} programmes, même sortie que le VRAI awk")
    val (err, codeErr) = DonneesAwk.executer("{print \$1", "a\n", ",")
    verifierDn(codeErr == 2 && err.startsWith("awk:"), "un programme awk mal écrit : un message d'erreur, pas un plantage ($err)")
    verifierDn(DonneesAwk.executer("{print 1/0}", "a\n", null).second == 2, "awk : la division par zéro est une erreur propre")

    println("2. L'arbre du Carrefour")
    verifierDn(!Histoire.ouvert(jeuDn, "donnees"), "fermée au début (il manque ${Donnees.manque(jeuDn)})")
    val h = Histoire.h(jeuDn)
    val faits = h.optJSONArray("faits") ?: JSONArray().also { h.put("faits", it) }
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    val ailes = h.optJSONArray("ailes") ?: JSONArray().also { h.put("ailes", it) }
    ailes.put("reveil"); ailes.put("nid")
    h.put("chap", "bibliotheque")
    val ann = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
    for (m in listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire")) ann.put(m)
    jeuDn.xp = 10 * 30 * 30
    val caps = Explo.captures(jeuDn)
    val sept = listOf("Gloupi", "Braisillon", "Gloupi", "Krillou", "Cailloute", "Plumange", "Tritonnet").withIndex().map { (k, n) -> individuDn(n, k, n == "Cailloute") }
    for (x in sept.take(2)) caps.put(x)          // une petite collection : 2 bestioles (le minimum de D1 : 3)
    // l'enfant est allé rencontrer et dresser des créatures : sa collection a maintenant n bestioles, il réexporte
    fun capturer(n: Int): String { while (caps.length() < n) caps.put(sept[caps.length()]); return "collection --csv > collection.csv" }
    tapeDn("ls")
    tapeDn("ls")
    verifierDn(Histoire.ouvert(jeuDn, "donnees"), "le niveau 4 fait : la Salle des Données s'ouvre")
    verifierDn("donnees" in lstDn(Histoire.h(jeuDn).optJSONArray("mondes_annonces")), "annoncée une fois")
    val DD = Donnees.dossier(jeuDn)
    verifierDn(File(DD, "laboratoire.txt").isFile && File(DD, Donnees.CARNET).isFile, "la Salle est meublée (laboratoire, carnet)")
    val avant = fichiersHorsDn(jeuDn.home, jeuDn.terrain)

    println("3. La traversée, comme dans l'appli (sa vraie collection de 7 bestioles)")
    tapeDn("cd ~/terrain_terminagotchi/donnees")
    verifierDn(lecDn() == ("dn0" to 1), "entrer dans la Salle choisit le monde : ${lecDn()}")
    val sorties = LinkedHashMap<String, String>()
    fun rows() = Donnees.lignesDuFichier(jeuDn) ?: emptyList()
    fun carnetDe() = Donnees.carnetSoigneur(rows())
    val parcours: List<() -> String> = listOf(
        { "ls" }, { "cat laboratoire.txt" }, { "collection --csv" }, { "collection --csv > collection.csv" }, { "ls" }, { capturer(4) },
        { "head -3 collection.csv" },
        { "wc -l collection.csv" }, { "donnees combien 3" }, { "donnees combien ${rows().size}" }, { "donnees trier" },
        { "sort especes.txt | uniq -c | sort -rn | head -3" }, { "sort -nr forces.txt | head -3 > top3.txt" },
        { "donnees colonnes" }, { "head -1 collection.csv | tr ',' '\\n'" }, { "cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c" },
        { "cut -d, -f10 collection.csv | grep -c 1" }, { "donnees shiny ${Donnees.nbShiny(rows())}" },
        { "cut -d, -f1 collection.csv > noms.txt && cut -d, -f2 collection.csv > types.txt" }, { "paste -d: noms.txt types.txt | head -5" },
        { "donnees copiste" }, { "cat carnet_du_soigneur.txt" }, { "sed 's/${carnetDe()[2]}/${carnetDe()[3]}/' carnet_du_soigneur.txt" },
        { "sed 's/${carnetDe()[2]}/${carnetDe()[3]}/g' carnet_du_soigneur.txt > carnet_corrige.txt" },
        { "diff carnet_du_soigneur.txt carnet_corrige.txt" }, { "sed -n '2,4p' carnet_corrige.txt" },
        { "sed -i 's/${carnetDe()[2]}/${carnetDe()[3]}/g' carnet_du_soigneur.txt" },
        { "donnees calcul" }, { capturer(7) }, { "donnees calcul" }, { "awk -F, 'NR<=5 {print \$1, \$4}' collection.csv" }, { "awk -F, 'NR>1 {s+=\$4} END {print s}' collection.csv" },
        { "awk -F, 'NR>1 {s+=\$4; n++} END {print s/n}' collection.csv" }, { "donnees moyenne 999" },
        { "donnees moyenne ${Math.round(Donnees.moyenne(rows()))}" }, { "cut -d, -f4 collection.csv | tail -n +2 | sort -n > attaques.txt" },
        { "donnees mediane ${Donnees.nombreAwk(Donnees.medianes(rows())[0])}" }, { "sed -n '1p;\$p' attaques.txt" },
        { "donnees etendue ${Donnees.etendue(rows())}" },
        { "donnees chaine" }, { "grep -E 'eau|glace' collection.csv" }, { "cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs echo" },
        { "mkdir -p enclos && cut -d, -f1 collection.csv | tail -n +2 | sort -u | sed 's|.*|enclos/&.txt|' | xargs touch" },
        { "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt" },
        { "awk -F, 'NR>1 {s+=\$4; n++} END {print \"moyenne\", s/n}' collection.csv >> rapport.txt" }, { "donnees bilan" },
        { "donnees base" }, { "sqlite3 collection.db .tables" }, { "sqlite3 collection.db \".schema creatures\"" },
        { "sqlite3 collection.db \"SELECT nom, attaque FROM creatures ORDER BY attaque DESC LIMIT 3;\"" },
        { "sqlite3 collection.db \"SELECT nom, variante FROM creatures WHERE type = 'eau';\"" },
        { "sqlite3 collection.db \"DELETE FROM creatures;\"" },
        { "sqlite3 collection.db \"SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;\"" },
        { "donnees sql ${Donnees.typesMajoritaires(rows())[0]}" },
        { "sqlite3 collection.db \"SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom LIMIT 5;\"" },
        { "sqlite3 collection.db \"SELECT AVG(attaque) FROM creatures;\"" },
    )
    val vus = mutableListOf<String>()
    val passages = mutableListOf<Triple<String, Any, Any>>()
    for (f in parcours) {
        val c = f()
        val a = lecDn()
        val s = tapeDn(c)
        sorties.putIfAbsent(c, s)
        passages.add(Triple(c, a, lecDn()))
        vus.add("$a $c → ${lecDn()} ${s.take(70).replace("\n", "⏎")}")
        if (System.getenv("TG_DEBUG") != null) println("    · " + vus.last())
        if (Histoire.fini(jeuDn, "donnees")) break
    }
    if (!Histoire.fini(jeuDn, "donnees")) vus.takeLast(8).forEach { println("      $it") }
    verifierDn(Histoire.fini(jeuDn, "donnees"), "la Salle des Données est traversée jusqu'au bout (dn0 → dn6) ${lecDn()}")
    val R = rows()
    verifierDn(R.size == 7 && R.all { "exemple" !in it }, "le tableau est SA collection (7 bestioles, aucune d'exemple)")
    val c0 = sorties["collection --csv"] ?: ""
    verifierDn(c0.startsWith("nom,type,famille,attaque") && "au moins 5" in c0 && "forêt" in c0,
        "collection --csv écrit le tableau ; avec 2 bestioles, il dit le minimum des exercices et où les rencontrer")
    val ex1 = passages.filter { it.first == "collection --csv > collection.csv" }
    val cal = passages.filter { it.first == "donnees calcul" }
    verifierDn(ex1[0].second == ex1[0].third && "${ex1[1].third}" != "${ex1[0].third}" && cal[0].second == cal[0].third && "${cal[1].third}" != "${cal[0].third}" &&
        "au moins 5" in (sorties["donnees calcul"] ?: "") && "tu en as 4" in (sorties["donnees calcul"] ?: ""),
        "D1 attend 3 créatures, D4 en attend 5 (« Il te faut au moins 5 créatures… », où aller) ; réexporté, ça passe ($ex1 $cal)")
    val faux = R.mapIndexed { i, r -> if (i == 0) r + ("attaque" to "99") else r }
    verifierDn(Donnees.saCollection(jeuDn, R) && !Donnees.saCollection(jeuDn, faux) && !Donnees.saCollection(jeuDn, R.dropLast(1)),
        "l'exploit ne se gagne que sur SA vraie collection (un tableau retouché à la main ne compte pas)")
    verifierDn(sorties["awk -F, 'NR>1 {s+=\$4; n++} END {print s/n}' collection.csv"]?.trim() == Donnees.nombreAwk(Donnees.moyenne(R)),
        "le petit awk calcule la moyenne (${Donnees.nombreAwk(Donnees.moyenne(R))})")
    verifierDn(sorties["sqlite3 collection.db .tables"]?.trim() == "creatures  especes", "sqlite3 .tables : creatures  especes")
    verifierDn((sorties["sqlite3 collection.db \"DELETE FROM creatures;\""] ?: "") == t("dn.tel.sqlite_lecture") && R.size == 7,
        "la base est en lecture seule : DELETE est refusé")
    verifierDn(sorties["sqlite3 collection.db \"SELECT AVG(attaque) FROM creatures;\""]?.trim() == DonneesSql.valeur(Donnees.moyenne(R)),
        "AVG(attaque) : la même moyenne qu'awk")
    val R4 = Donnees.lireCsv(Donnees.csvTexte(Donnees.lignesCollection(org.json.JSONArray(sept.take(4)))))   // (D1 à D3 : 4 bestioles)
    verifierDn(File(DD, "carnet_du_soigneur.txt").readText() == Donnees.carnetSoigneur(R4)[1], "le carnet corrigé sur place (sed -i)")
    val ex = Recompenses.etat(jeuDn).getJSONObject("exploits").keys().asSequence().toList()
    verifierDn("donnees.statistique" in ex, "l'exploit « une statistique juste sur ta collection » ($ex)")
    verifierDn("boulier" in lstDn(Quetes.q(jeuDn).optJSONArray("objets")), "récompense du monde : un boulier de savant (posé, jamais porté)")
    verifierDn(fichiersHorsDn(jeuDn.home, jeuDn.terrain).filter { !it.endsWith(".json") && "terminagotchi" !in it } .toSet() == avant.filter { !it.endsWith(".json") && "terminagotchi" !in it }.toSet(),
        "rien d'écrit hors du terrain")
    val csvTxt = File(DD, "collection.csv").readText()
    verifierDn(!csvTxt.contains("Pixel") && !csvTxt.contains("id0") && !csvTxt.contains("étoile"), "le CSV : ni nom de la créature, ni identifiant, ni marque")
    verifierDn(cmdDn.executer("awk -F, '{print \$1}' collection.csv | head -1") == null, "awk dans un tuyau : c'est le shell qui s'en occupe")

    println("4. Les variantes réservées, le dessin")
    val j2 = Jeu(AppareilDn(File(dossier, "j2").apply { mkdirs() }, assets))
    val reserve = { e: String, vv: String -> Recompenses.reservee(j2, vv, e) }
    verifierDn(reserve("nautiloque", "corail") && reserve("krillou", "aurore") && reserve("ondulame", "glace") && !reserve("krillou", "glace"),
        "nautiloque:corail, krillou:aurore, ondulame:glace réservées avant l'exploit ; krillou:glace non")
    verifierDn(!Recompenses.reservee(jeuDn, "aurore", "krillou"), "… et libérées après l'exploit")
    val tl = ToileDn()
    DonneesDessin.labo(tl, Deploie.labos("cut -d, -f2 collection.csv")[0], 0.4, 0f, 0f, 320f, 96f, 1f)
    DonneesDessin.podium(tl, listOf("Krillou" to 38, "Gloupi" to 36, "Cailloute" to 35), 0.5, 0f, 0f, 320f, 140f, 1f)
    DonneesDessin.laboratoire(tl, 0.3, 0f, 0f, 320f, 180f, 1f)
    verifierDn(tl.n > 40 && tl.textes.any { "ciseaux" in it }, "le dessin : l'instrument (les ciseaux de cut), le podium, le laboratoire de repli")

    println("\n$okDn réussis, $koDn échoués")
    kotlin.system.exitProcess(if (koDn == 0) 0 else 1)
}

fun t(cle: String, vararg p: Pair<String, Any?>) = fr.terminagotchi.t(cle, *p)
