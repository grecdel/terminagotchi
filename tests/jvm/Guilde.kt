/*
 * Test JVM de la Guilde des Bâtisseurs Libres (phase 5) sur Android, portage de pc/outils/test_guilde.py :
 *   1. les vecteurs communs donnees/guilde/vecteurs.json (les 4 libertés et « libre ou gratuit » mélangés comme
 *      random.shuffle de Python, les réponses, les licences et le catalogue, la faim, la faute volontaire et sa
 *      correction, le porte-clé, son trou et son volume, le STL du jeu et la lecture d'un STL texte ou binaire, la fausse
 *      image, le lsblk fictif et le bon disque, l'établi de la vue déployée) : EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. l'arbre du Carrefour : la Guilde s'ouvre après le niveau 4 du tronc (annoncée une fois), meublée ;
 *   3. la traversée gu0 → gu6 comme dans l'appli (git, gcc, OpenSCAD et lsblk racontés ; la copie faite d'extraits du
 *      vrai code ; la correction relue avec diff ; dd et sha256sum sur des FICHIERS), l'exploit « artisan » (une
 *      fois), la boîte à outils ; rien hors du terrain ; aucune écriture vers /dev ;
 *   4. les variantes réservées, le dessin (établi, libertés, porte-clé, clé, guilde de repli) sur une toile d'essai ; la
 *      vue déployée sait quel bloc transforme quoi.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Guilde.kt -d gui.jar
 *   java -cp <imitations>:<appli.jar>:gui.jar:kotlin-stdlib.jar GuildeKt app/src/main/assets
 */
import fr.terminagotchi.Badges
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Entrainement
import fr.terminagotchi.Guilde
import fr.terminagotchi.GuildeDessin
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
import java.security.MessageDigest

class ActifsGu(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilGu(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsGu(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileGu : Toile {
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

var okGu = 0
var koGu = 0
fun verifierGu(c: Boolean, m: String) {
    if (c) okGu++ else koGu++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuGu: Jeu
lateinit var shellGu: Shell
lateinit var cmdGu: Commandes

fun lstGu(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun bashGu(cmd: String, ou: File = shellGu.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuGu.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeGu(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellGu.executer(cmd)
    else {
        val interne = cmdGu.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashGu(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuGu, cmd, colle = false, rappel = false, hasard = false, cwd = shellGu.dossier, code = code)
    return sortie
}

fun lecGu(): Pair<String?, Int> = Histoire.leconCourante(jeuGu)?.id to jeuGu.etape

fun fichiersHorsGu(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun objetsGu(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }
fun nombresGu(a: JSONArray): List<Double> = (0 until a.length()).map { a.getDouble(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_gu_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilGu(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuGu = Jeu(app)
    jeuGu.changerLangue("fr")
    jeuGu.nom = "Pixel"
    shellGu = Shell(jeuGu.home)
    cmdGu = Commandes(app, jeuGu, { shellGu.dossier })
    jeuGu.module("explo").put("ouverte", true)
    jeuGu.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/guilde/vecteurs.json").readText())
    var ko = 0
    for (x in objetsGu(v.getJSONArray("parties"))) {
        val g = x.getString("graine")
        fun cartes(c: List<Guilde.Carte>) = c.map { listOf("${it.n}", it.id, it.rep) }
        fun att(k: String) = (0 until x.getJSONArray(k).length()).map { lstGu(x.getJSONArray(k).getJSONArray(it)) }
        if (cartes(Guilde.libertesCartes(g)) != att("libertes")) { ko++; println("    libertés $g → ${cartes(Guilde.libertesCartes(g))}") }
        if (cartes(Guilde.gratuitCartes(g)) != att("gratuit")) { ko++; println("    gratuit $g") }
        val f = Guilde.faute(g); val fa = x.getJSONObject("faute")
        if (f.optInt("ligne") != fa.getInt("ligne") || f.optString("faux") != fa.getString("faux")) { ko++; println("    faute $g") }
        if (Guilde.texteContribution(g) != x.getString("texte_faux") || Guilde.texteContribution(g, true) != x.getString("texte_juste")) { ko++; println("    texte $g") }
        val p = Guilde.piece(g); val pa = x.getJSONObject("piece")
        if (p.longueur != pa.getInt("longueur") || p.largeur != pa.getInt("largeur") || p.epaisseur != pa.getInt("epaisseur") || p.trouX != pa.getInt("trou_x") ||
            p.trouY != pa.getInt("trou_y") || p.trouD != pa.getInt("trou_d") || Guilde.volume(g) != x.getInt("volume")) { ko++; println("    pièce $g") }
        val di = Guilde.disques(g).map { listOf(it.nom, it.taille, "${it.rm}", it.type, it.point) }
        val dia = objetsGu(x.getJSONArray("disques")).map { listOf(it.getString("nom"), it.getString("taille"), "${it.getInt("rm")}", it.getString("type"), it.getString("point")) }
        if (di != dia) { ko++; println("    disques $g → $di") }
        val (cn, cg) = Guilde.cleDisque(g)
        if (listOf(cn, "$cg") != lstGu(x.getJSONArray("cle"))) { ko++; println("    clé $g") }
    }
    verifierGu(ko == 0, "${v.getJSONArray("parties").length()} parties : libertés, gratuit, faute, textes, porte-clé, volume, lsblk fictif, clé")
    ko = 0
    for (x in objetsGu(v.getJSONArray("quiz"))) {
        val g = x.getString("graine"); val l = x.getString("lettres")
        val c = if (l == "0123") Guilde.libertesCartes(g) else Guilde.gratuitCartes(g)
        val (bon, justes) = Guilde.quizJustes(c, lstGu(x.getJSONArray("rep")), l)
        val att = (0 until x.getJSONArray("justes").length()).map { lstGu(x.getJSONArray("justes").getJSONArray(it)) }
        if (bon != x.getBoolean("ok") || justes.map { listOf("${it.n}", it.id) } != att) { ko++; println("    quiz $x → $bon ${justes.map { it.id }}") }
    }
    verifierGu(ko == 0, "${v.getJSONArray("quiz").length()} réponses aux quiz (bien formées, justes)")
    ko = 0
    for (x in objetsGu(v.getJSONArray("licences"))) { val k = Guilde.licenceDeTexte(x.getString("texte"))
        if (k != (if (x.isNull("famille")) null else x.getString("famille"))) { ko++; println("    licence ${x.getString("texte")} → $k") } }
    val vb = v.getJSONObject("badges")
    verifierGu(objetsGu(vb.getJSONArray("artisan")).all { Guilde.palierArtisan(it.getInt("lecons"), it.getBoolean("contribution")) == it.getInt("palier") } &&
        objetsGu(vb.getJSONArray("contributeur")).all { Guilde.palierContributeur(it.getInt("n")) == it.getInt("palier") } &&
        objetsGu(vb.getJSONArray("contributions")).all { Guilde.contributionsDe(if (it.isNull("pseudo")) null else it.getString("pseudo"), vb.getJSONArray("credits")) == it.getInt("n") },
        "badges de la Guilde : paliers Artisan et Contributeur, contributions retrouvées dans les crédits (identiques au PC)")
    fun empreinteGu(g: List<List<String?>>): String = MessageDigest.getInstance("SHA-256")
        .digest(g.joinToString("/") { l -> l.joinToString(",") { it ?: "" } }.toByteArray()).joinToString("") { "%02x".format(it) }
    verifierGu(objetsGu(vb.getJSONArray("ecussons")).all { empreinteGu(Badges.ecusson(it.getString("famille"), it.getString("echelon"), 0)) == it.getString("empreinte") },
        "les écussons Artisan (marteau) et Contributeur (cœur) identiques au pixel près")
    for (x in objetsGu(v.getJSONArray("catalogue"))) { val k = Guilde.licenceCatalogue(x.getString("nom"))
        if (k != (if (x.isNull("famille")) null else x.getString("famille")) || Guilde.genreLicence(k) != (if (x.isNull("genre")) null else x.getString("genre"))) { ko++; println("    catalogue $x → $k") } }
    verifierGu(ko == 0, "les licences reconnues dans un texte (LGPL avant GPL…) et le catalogue")
    ko = 0
    for (x in objetsGu(v.getJSONArray("faim"))) {
        val f = x.getJSONObject("fichiers"); val m = f.keys().asSequence().associateWith { f.getString(it) }
        if (Guilde.faimFichiers(m) != lstGu(x.getJSONArray("attendus"))) { ko++; println("    faim $m → ${Guilde.faimFichiers(m)}") } }
    for (x in objetsGu(v.getJSONArray("faim_reponses"))) if (Guilde.faimOk(x.getString("reponse"), lstGu(x.getJSONArray("attendus"))) != x.getBoolean("ok")) { ko++; println("    faim $x") }
    verifierGu(ko == 0, "le fichier où la créature décide qu'elle a faim, et les réponses (satiete, satiete.py, Satiété…)")
    ko = 0
    for (x in objetsGu(v.getJSONArray("corrections"))) if (Guilde.correctionOk(x.getString("texte"), x.getString("graine")) != x.getBoolean("ok")) { ko++; println("    correction ${x.getString("texte").take(30)}") }
    for (x in objetsGu(v.getJSONArray("trous"))) if (Guilde.trouOk(lstGu(x.getJSONArray("rep")), x.getString("graine")) != x.getBoolean("ok")) { ko++; println("    trou $x") }
    for (x in objetsGu(v.getJSONArray("volumes"))) if (Guilde.volumeOk(x.getString("reponse"), x.getString("graine")) != x.getBoolean("ok")) { ko++; println("    volume $x") }
    verifierGu(ko == 0, "la correction de la faute, le trou du porte-clé et son volume (mm³, cm³)")
    ko = 0
    fun infos(s: Guilde.Stl?, a: Any?): Boolean = if (a == null || a == JSONObject.NULL) s == null else { val o = a as JSONObject
        s != null && s.n == o.getInt("n") && s.binaire == o.getBoolean("binaire") && s.dims == nombresGu(o.getJSONArray("dims")) }
    for (x in objetsGu(v.getJSONArray("stl"))) {
        val t = Guilde.stlBoite(x.getInt("L"), x.getInt("l"), x.getInt("h"))
        if (t != x.getString("texte") || !infos(Guilde.stlInfos(t.toByteArray()), x.get("infos"))) { ko++; println("    stl ${x.getInt("L")}") } }
    fun deHex(h: String) = ByteArray(h.length / 2) { h.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
    val sb = v.getJSONObject("stl_binaire")
    if (!infos(Guilde.stlInfos(deHex(sb.getString("hex"))), sb.get("infos"))) { ko++; println("    stl binaire → ${Guilde.stlInfos(deHex(sb.getString("hex")))?.dims}") }
    for (x in objetsGu(v.getJSONArray("stl_mauvais"))) if (!infos(Guilde.stlInfos(deHex(x.getString("hex"))), x.opt("infos"))) { ko++; println("    stl mauvais ${x.getString("hex").take(20)}") }
    verifierGu(ko == 0, "le STL fait par le jeu (texte identique), lu en texte et en binaire, les fichiers illisibles")
    val im = v.getJSONObject("image")
    verifierGu(Guilde.imageOctets().size == im.getInt("octets") && Guilde.imageSha() == im.getString("sha256"), "la fausse image : 64 Kio, la même empreinte qu'en Python")
    ko = 0
    for (x in objetsGu(v.getJSONArray("disques"))) { val g = x.getString("graine"); val r = x.getString("reponse")
        if (Guilde.disqueOk(r, g) != x.getBoolean("ok") || Guilde.disqueErreur(r, g) != x.getString("erreur")) { ko++; println("    disque $x") } }
    val mm = v.getJSONObject("majmin")
    for (k in mm.keys()) if (Guilde.majmin(k) != mm.getString(k)) { ko++; println("    majmin $k → ${Guilde.majmin(k)}") }
    verifierGu(ko == 0, "le bon disque et pourquoi les autres sont faux (système, sauvegarde, partition)")
    ko = 0
    for (x in objetsGu(v.getJSONArray("etabli"))) { val k = Guilde.etablisDe(x.getString("ligne")).map { listOf(it.first, it.second, it.third) }
        val att = (0 until x.getJSONArray("etablis").length()).map { lstGu(x.getJSONArray("etablis").getJSONArray(it)) }
        if (k != att) { ko++; println("    établi ${x.getString("ligne")} → $k") } }
    for (x in objetsGu(v.getJSONArray("deploie"))) { val k = Deploie.etablis(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.outil, it.de, it.vers) }
        val att = objetsGu(x.getJSONArray("etablis")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("de"), it.getString("vers")) }
        if (k != att) { ko++; println("    vue déployée ${x.getString("ligne")} → $k (attendu $att)") } }
    verifierGu(ko == 0, "l'établi : gcc, make, openscad, dd, sha256sum, git clone / diff / commit, et la vue déployée")

    println("2. L'arbre du Carrefour : quand la Guilde s'ouvre")
    val h = Histoire.h(jeuGu)
    verifierGu(!Histoire.ouvert(jeuGu, "guilde"), "fermée au début : il manque ${Guilde.manque(jeuGu)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid", "bibliotheque")) h.getJSONArray("ailes").put(c)
    h.put("mondes_annonces", JSONArray(listOf("port", "citadelle", "crypte", "machinerie", "ondes")))
    h.put("annonce_attente", true)
    Histoire.tick(jeuGu, "ls", false, jeuGu.home, 0)
    verifierGu(Histoire.ouvert(jeuGu, "guilde") && "guilde" in lstGu(h.optJSONArray("mondes_annonces")) && !Guilde.annonce(jeuGu),
        "le niveau 4 fait : la Guilde s'ouvre, annoncée une seule fois")
    val D = File(jeuGu.terrain, "guilde")
    D.mkdirs()
    Histoire.tick(jeuGu, "ls", false, jeuGu.home, 0)
    verifierGu(File(D, "mur_des_plans.txt").isFile && File(D, "petit_projet/LICENSE").isFile && File(D, "atelier/bonjour.c").isFile &&
        File(D, "fabrique/porte_cle.scad").isFile, "la Guilde est meublée (mur des plans, petit projet, atelier, fabrique)")
    val credits = File(D, "CREDITS.txt").readText()
    verifierGu("@" !in credits && "vide" in credits, "les crédits : une structure prête, vide")

    println("3. La traversée de la Guilde sur le téléphone")
    val avantFichiers = fichiersHorsGu(jeuGu.home, jeuGu.terrain)
    jeuGu.xp = 10 * 30 * 30
    tapeGu("cd ~/terrain_terminagotchi/guilde")
    verifierGu(lecGu() == ("gu0" to 1), "entrer dans la Guilde choisit le monde : ${lecGu()}")
    val gr = Histoire.graine(jeuGu)
    val p = Guilde.piece(gr)
    val fa = Guilde.faute(gr)
    val (nomCle, _) = Guilde.cleDisque(gr)
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat mur_des_plans.txt" },
        { "guilde libertes" }, { "guilde libertes " + Guilde.libertesCartes(gr).joinToString(" ") { it.rep } }, { "cat petit_projet/LICENSE" },
        { "guilde licence licornesoft" }, { "guilde licence bash" }, { "guilde licence git" }, { "guilde licence python3" }, { "guilde licence gcc" }, { "guilde licence firefox" },
        { "guilde gratuit" }, { "guilde gratuit " + Guilde.gratuitCartes(gr).joinToString(" ") { it.rep } }, { "guilde licence terminagotchi" },
        { "guilde depot" }, { "guilde copie" }, { "ls -R code_du_jeu" }, { "grep -rl \"faim\" code_du_jeu/pc/tg" },
        { "grep -rn \"def etat_de\" code_du_jeu/pc/tg" }, { "guilde faim aura.py" }, { "guilde faim satiete" }, { "head -40 code_du_jeu/pc/tg/satiete.py" },
        { "head code_du_jeu/LICENSE" },
        { "cd atelier" }, { "guilde compiler" }, { "cat bonjour.c" }, { "guilde gcc" },
        { "cd .." }, { "guilde contribution" }, { "cd contribution" }, { "cat langues/fr.txt" },
        { "sed -i 's/${fa.optString("faux")}/${fa.optString("juste")}/' langues/fr.txt" }, { "diff .origine/fr.txt langues/fr.txt" }, { "guilde fusion" },
        { "cd ../fabrique" }, { "guilde piece" }, { "cat porte_cle.scad" }, { "guilde trou ${p.trouX} ${p.trouY}" }, { "guilde volume ${Guilde.volume(gr)}" },
        { "guilde stl" }, { "head -3 porte_cle.stl" },
        { "cd ../vieux_pc" }, { "guilde sauver" }, { "guilde cle" }, { "sha256sum ${Guilde.IMAGE}" }, { "sha256sum -c ${Guilde.IMAGE}.sha256" },
        { "guilde disques" }, { "guilde disque nvme0n1" }, { "guilde disque $nomCle" }, { "dd if=${Guilde.IMAGE} of=${Guilde.CLE} bs=64k" },
        { "sha256sum ${Guilde.IMAGE} ${Guilde.CLE}" }, { "guilde certificat" },
    )
    val sorties = HashMap<String, String>()
    val passages = HashMap<String, Pair<String, String>>()
    for (f in etapes) {
        val c = f()
        val avant = lecGu()
        val s = tapeGu(c)
        sorties.putIfAbsent(c, s)
        passages.putIfAbsent(c, "$avant" to "${lecGu()}")
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecGu()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuGu, "guilde")) break
    }
    verifierGu(Histoire.fini(jeuGu, "guilde"), "la Guilde est traversée jusqu'au bout (gu0 → gu6) : ${lecGu()}")
    verifierGu(Guilde.licencesTrouvees(jeuGu).size >= 5 && "?" in (sorties["guilde licence licornesoft"] ?: ""), "5 licences (catalogue) ; un logiciel inconnu n'est pas compté")
    val lt = sorties["guilde licence terminagotchi"] ?: ""
    verifierGu("GNU GPL" in lt && "GPL-3.0-or-later" in lt && "BY-NC-SA 4.0" in lt && passages["guilde licence terminagotchi"]?.second?.contains("gu2") == true,
        "G1 : la licence de Terminagotchi (code GPL, images CC BY-NC-SA), dernière étape du palier ${passages["guilde licence terminagotchi"]}")
    val lic = File(D, "code_du_jeu/LICENSE")
    verifierGu(lic.isFile && lic.readText().lines()[0].trim() == "GNU GENERAL PUBLIC LICENSE" && File(D, "code_du_jeu/LICENSE-images.md").isFile &&
        passages["head code_du_jeu/LICENSE"]?.second?.contains("gu3") == true,
        "G2 : la copie du téléphone contient LICENSE (la GPL v3) et LICENSE-images.md ; head LICENSE finit le palier ${passages["head code_du_jeu/LICENSE"]}")
    verifierGu("✖" in (sorties["guilde faim aura.py"] ?: "") && "def etat_de" in (sorties["guilde faim satiete"] ?: ""), "la faim : aura.py refusé, satiete accepté (extrait du vrai code)")
    verifierGu("> " in (sorties["diff .origine/fr.txt langues/fr.txt"] ?: "") && fa.optString("juste") in (sorties["diff .origine/fr.txt langues/fr.txt"] ?: ""),
        "diff montre la correction (< avant, > après)")
    val ex = Recompenses.etat(jeuGu).getJSONObject("exploits").keys().asSequence().toList()
    verifierGu("guilde.artisan" in ex, "l'exploit « artisan » ($ex)")
    verifierGu("boite_a_outils" in lstGu(Quetes.q(jeuGu).optJSONArray("objets")), "récompense du monde : une boîte à outils")
    verifierGu(Guilde.cleCopiee(jeuGu) && File(D, "vieux_pc/certificat_pc_sauve.txt").isFile, "la fausse clé copiée avec dd, vérifiée, le certificat")
    verifierGu("✖" in (sorties["guilde disque nvme0n1"] ?: ""), "le disque du système refusé")
    val sh = (sorties["sha256sum ${Guilde.IMAGE} ${Guilde.CLE}"] ?: "").lines().filter { it.isNotBlank() }.map { it.split(" ")[0] }.toSet()
    verifierGu(sh == setOf(Guilde.imageSha()), "sha256sum : deux empreintes identiques (celle du jeu)")
    val nouveaux = fichiersHorsGu(jeuGu.home, jeuGu.terrain) - avantFichiers
    verifierGu(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")
    val cmds = Guilde.lecons(jeuGu).values.flatMap { it.etapes }.joinToString(" ") { it.cmd }
    verifierGu("/dev/" !in cmds && "sudo" !in cmds && "push" !in cmds, "aucune étape ne vise /dev, n'utilise sudo, ne pousse")

    println("4. Les variantes réservées, le dessin, la vue déployée")
    val j2 = Jeu(AppareilGu(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierGu(!Recompenses.reservee(j2, "mecanique", "engrenaille") && !Recompenses.reservee(j2, "rouille", "rouillot") &&
        !Recompenses.reservee(j2, "champignonniere", "lampignon") && Recompenses.faveur(jeuGu) == null,
        "1er novembre : plus aucune variante réservée ni favorisée par la Guilde")
    val art = Guilde.artisan(jeuGu)
    verifierGu(art.echelon == "mega" && art.n == 7 && Guilde.titres(jeuGu).any { it.id == "artisan:mega" && it.couleur == "#ffaf5f" } &&
        Guilde.contributeur(jeuGu).echelon == null, "le badge « Artisan » Méga à la fin de la Guilde ; pas de Contributeur sans crédits")
    Entrainement.e(jeuGu).put("titre", "artisan:mega")
    verifierGu(Entrainement.couleurNom(jeuGu) == "#ffaf5f" && Guilde.lignesBadges(jeuGu).any { "¤badge:artisan:mega" in it } &&
        "¤badge:artisan" in Entrainement.ecranBadges(jeuGu), "le titre « Artisan Méga » colore le nom ; les badges dessinés (guilde badges, badges)")
    Entrainement.e(jeuGu).remove("titre")
    val tl = ToileGu()
    GuildeDessin.etabli(tl, Deploie.Etabli(0, "gcc", "gcc", "texte", "programme"), 0.4, 0f, 0f, 400f, 96f, 1f)
    GuildeDessin.libertes(tl, 0.3, 0f, 0f, 400f, 140f, 1f)
    GuildeDessin.piece(tl, p, 0.2, 0f, 0f, 400f, 200f, 1f)
    GuildeDessin.cle(tl, true, 0.5, 0f, 0f, 400f, 140f, 1f)
    GuildeDessin.cle(tl, false, 0.5, 0f, 0f, 400f, 140f, 1f)
    GuildeDessin.guilde(tl, 0.7, 0f, 0f, 400f, 225f, 1f)
    verifierGu(tl.n > 100 && tl.textes.any { "gcc" == it } && tl.textes.any { "(${p.trouX} ; ${p.trouY})" == it } && tl.textes.any { "=" == it },
        "le dessin : établi, libertés, porte-clé, clé, guilde (${tl.n} traits)")
    val vue = Deploie.vue("gcc bonjour.c -o bonjour | head -1")!!
    verifierGu(vue.etabliDe(vue.blocs[0])?.outil == "gcc" && vue.etabliDe(vue.blocs[0])?.vers == "programme" && vue.blocs.none { it.g == "commande" && it.seg > 0 && vue.etabliDe(it) != null },
        "la vue déployée sait que gcc fait d'un texte un programme")

    println("\n$okGu réussis, $koGu échoués")
    kotlin.system.exitProcess(if (koGu == 0) 0 else 1)
}
