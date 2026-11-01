/*
 * Test JVM de la Salle des Rouages (phase 5) sur Android, portage de pc/outils/test_machines.py :
 *   1. les vecteurs communs donnees/machines/vecteurs.json (pièces interrogées, vue déployée, interrupteurs UTF-8,
 *      lettre du défi, unités, mémoire lue dans free, réveil, orchestre et boîtes mélangés comme random.shuffle de
 *      Python, besoin et drapeau de l'épreuve, machine montée, maison dans la maison, énergie) : EXACTEMENT les mêmes
 *      résultats qu'en Python ;
 *   2. les réponses calculées sur la même machine (cœurs, mémoire) ; `echo -n A | xxd -b` intégré = le vrai xxd -b ;
 *   3. l'arbre du Carrefour : la Salle s'ouvre après les niveaux 0 à 3 (annoncée une fois) ;
 *   4. la traversée sm0 → sm10 comme dans l'appli (beaucoup raconté : getprop, machines adulte / conteneur / vm),
 *      l'exploit « premier démarrage » (une seule fois), la carte mère miniature ; rien hors du terrain ;
 *   5. les variantes réservées, le dessin (ordinateur ouvert, interrupteurs, réveil, atelier, ferme, conteneur, salle de
 *      repli) sur une toile d'essai ; la vue déployée sait quel bloc allume quelle pièce.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Machines.kt -d mac.jar
 *   java -cp <imitations>:<appli.jar>:mac.jar:kotlin-stdlib.jar MachinesKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Machines
import fr.terminagotchi.MachinesDessin
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsMa(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilMa(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsMa(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileMa : Toile {
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

var okMa = 0
var koMa = 0
fun verifierMa(c: Boolean, m: String) {
    if (c) okMa++ else koMa++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuMa: Jeu
lateinit var shellMa: Shell
lateinit var cmdMa: Commandes
var cheminMa = System.getenv("PATH") ?: "/usr/bin:/bin"

fun lstMa(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun bashMa(cmd: String, ou: File = shellMa.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuMa.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    pb.environment()["PATH"] = cheminMa
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeMa(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellMa.executer(cmd)
    else {
        val interne = cmdMa.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashMa(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuMa, cmd, colle = false, rappel = false, hasard = false, cwd = shellMa.dossier, code = code)
    return sortie
}

fun lecMa(): Pair<String?, Int> = Histoire.leconCourante(jeuMa)?.id to jeuMa.etape

fun fichiersHors(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_mac_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilMa(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuMa = Jeu(app)
    jeuMa.changerLangue("fr")
    jeuMa.nom = "Pixel"
    shellMa = Shell(jeuMa.home)
    cmdMa = Commandes(app, jeuMa, { shellMa.dossier })
    jeuMa.module("explo").put("ouverte", true)
    jeuMa.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/machines/vecteurs.json").readText())
    var ko = 0
    val pi = v.getJSONArray("pieces")
    for (i in 0 until pi.length()) { val x = pi.getJSONObject(i)
        if (Machines.piecesDe(x.getString("ligne")) != lstMa(x.getJSONArray("pieces"))) { ko++; println("    pièces $x → ${Machines.piecesDe(x.getString("ligne"))}") } }
    verifierMa(ko == 0, "${pi.length()} lignes : les pièces interrogées (nproc → processeur, free → mémoire…)")
    ko = 0
    val de = v.getJSONArray("deploie")
    for (i in 0 until de.length()) { val x = de.getJSONObject(i)
        val k = Deploie.pieces(x.getString("ligne")).map { listOf("${it.seg}", it.cmd) + it.pieces }
        val att = (0 until x.getJSONArray("pieces").length()).map { x.getJSONArray("pieces").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("cmd")) + lstMa(it.getJSONArray("pieces")) }
        if (k != att) { ko++; println("    vue déployée ${x.getString("ligne")} → $k (attendu $att)") } }
    verifierMa(ko == 0, "${de.length()} lignes : la vue déployée sait quel bloc allume quelle pièce")
    ko = 0
    val it_ = v.getJSONArray("interrupteurs")
    for (i in 0 until it_.length()) { val x = it_.getJSONObject(i)
        val k = Machines.interrupteurs(x.getString("mot")).map { listOf(it.first) + it.second }
        val att = (0 until x.getJSONArray("octets").length()).map { x.getJSONArray("octets").getJSONArray(it) }.map { listOf(it.getString(0)) + lstMa(it.getJSONArray(1)) }
        if (k != att) { ko++; println("    interrupteurs ${x.getString("mot")} → $k") } }
    verifierMa(ko == 0, "${it_.length()} mots en interrupteurs (UTF-8 : é deux octets, 🐉 quatre)")
    ko = 0
    val le = v.getJSONArray("lettres")
    for (i in 0 until le.length()) { val x = le.getJSONObject(i)
        val l = Machines.lettreDefi(x.getString("nom"))
        if (l.toString() != x.getString("lettre") || Machines.bits(l.code) != x.getString("bits")) { ko++; println("    lettre $x → $l") } }
    verifierMa(ko == 0, "${le.length()} noms : la lettre du défi et ses bits")
    ko = 0
    val un = v.getJSONArray("unites")
    for (i in 0 until un.length()) { val x = un.getJSONObject(i)
        val u = Machines.unites(x.getLong("n"))
        if (listOf("ko", "kio", "mo", "mio", "go", "gio").any { Math.abs(u[it]!! - x.getDouble(it)) > 1e-9 * maxOf(1.0, x.getDouble(it)) }) { ko++; println("    unités $x → $u") } }
    verifierMa(ko == 0, "${un.length()} tailles en Ko / Kio, Mo / Mio, Go / Gio")
    ko = 0
    val me = v.getJSONArray("memoire")
    for (i in 0 until me.length()) { val x = me.getJSONObject(i)
        if (Machines.memoireOk(x.getString("reponse"), x.getLong("kio")) != x.getBoolean("ok")) { ko++; println("    mémoire $x") } }
    verifierMa(ko == 0, "${me.length()} réponses de mémoire jugées comme en Python")
    ko = 0
    val pa = v.getJSONArray("parties")
    for (i in 0 until pa.length()) { val x = pa.getJSONObject(i); val g = x.getString("graine")
        val rv = Machines.reveilCartes(g).map { listOf(it.first.toString(), it.second) }
        val rvA = (0 until x.getJSONArray("reveil").length()).map { lstMa(x.getJSONArray("reveil").getJSONArray(it)) }
        val or = Machines.orchestre(g).map { listOf("${it.first}", it.second, it.third.toString()) }
        val orA = (0 until x.getJSONArray("orchestre").length()).map { lstMa(x.getJSONArray("orchestre").getJSONArray(it)) }
        val ra = Machines.rangeBoites(g).map { listOf("${it.first}", it.second, it.third) }
        val raA = (0 until x.getJSONArray("range").length()).map { lstMa(x.getJSONArray("range").getJSONArray(it)) }
        if (rv != rvA || Machines.reveilReponse(g).map { it.toString() } != lstMa(x.getJSONArray("reponse")) || or != orA || ra != raA ||
            Machines.besoinEpreuve(g) != x.getString("besoin") || Machines.drapeau(g) != x.getString("drapeau")) { ko++; println("    partie $g : $rv $or $ra ${Machines.drapeau(g)}") } }
    verifierMa(ko == 0, "${pa.length()} parties : réveil, orchestre, boîtes mélangés comme en Python ; besoin et drapeau")
    ko = 0
    val mo = v.getJSONArray("montages")
    for (i in 0 until mo.length()) { val x = mo.getJSONObject(i)
        val r = Machines.montage(lstMa(x.getJSONArray("choix")), x.getString("besoin"))
        if (r.problemes != lstMa(x.getJSONArray("problemes")) || r.points != x.getInt("points") || r.watts != x.getInt("watts") ||
            r.fournit != x.getInt("fournit") || r.coeurs != x.getInt("coeurs") || r.gio != x.getInt("gio") || r.go != x.getInt("go")) { ko++; println("    montage $x → ${r.problemes}") } }
    verifierMa(ko == 0, "${mo.length()} machines montées : mêmes problèmes, points et watts")
    ko = 0
    val bo = v.getJSONArray("boites")
    for (i in 0 until bo.length()) { val x = bo.getJSONObject(i)
        val (vm, c) = Machines.boiteDe(x.getString("cpuinfo"), x.getString("cgroup"), x.getBoolean("dockerenv"), x.getBoolean("containerenv"))
        if (vm != x.getBoolean("vm") || c != (if (x.isNull("conteneur")) null else x.getString("conteneur"))) { ko++; println("    boîte $x") } }
    verifierMa(ko == 0, "${bo.length()} maisons dans la maison (hypervisor, docker, podman, cgroups)")
    ko = 0
    val en = v.getJSONArray("energie")
    for (i in 0 until en.length()) { val x = en.getJSONObject(i)
        val (wh, kwh) = Machines.energie(x.getInt("watts"), x.getInt("heures"))
        if (wh != x.getLong("wh") || Math.abs(kwh - x.getDouble("kwh")) > 1e-9) { ko++; println("    énergie $x") } }
    verifierMa(ko == 0, "${en.length()} calculs d'énergie")

    println("2. La même machine ; xxd -b intégré")
    val nproc = bashMa("nproc").first.trim().toIntOrNull()
    verifierMa(nproc != null && nproc in Machines.coeursJustes(), "nproc ($nproc) est une réponse juste pour l'appli (${Machines.coeursJustes()})")
    val total = bashMa("free -h | awk '/^Mem:/ {print \$2}'").first.trim()
    verifierMa(Machines.memoireOk(total, Machines.memoireKio()), "free -h dit $total : l'appli l'accepte")
    val vraiXxd = bashMa("command -v xxd >/dev/null && echo -n 'Zoé' | xxd -b").first.trimEnd()
    verifierMa(vraiXxd.isEmpty() || Machines.xxdB("echo -n 'Zoé' | xxd -b") == vraiXxd, "xxd -b intégré = le vrai xxd -b (${if (vraiXxd.isEmpty()) "xxd absent ici" else "comparé"})")
    verifierMa(Machines.xxdB("echo -n A | xxd -b")!!.trimEnd().let { it.startsWith("00000000: 01000001 ") && it.endsWith(" A") && "00100000" !in it } &&
        Machines.xxdB("printf 'Zoé' | xxd -b")!!.contains("11000011 10101001") && Machines.xxdB("ls | xxd -b") == null, "echo -n A | xxd -b → 01000001")

    println("3. L'arbre du Carrefour : quand la Salle s'ouvre")
    val h = Histoire.h(jeuMa)
    verifierMa(!Histoire.ouvert(jeuMa, "machinerie"), "fermée au début : il manque ${Machines.manque(jeuMa)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid")) h.getJSONArray("ailes").put(c)
    h.put("chap", "bibliotheque")
    h.put("mondes_annonces", JSONArray(listOf("port", "crypte")))
    Histoire.tick(jeuMa, "ls", false, jeuMa.home, 0)
    verifierMa(Histoire.ouvert(jeuMa, "machinerie") && "machinerie" in lstMa(h.optJSONArray("mondes_annonces")) && !Machines.annonce(jeuMa),
        "niveaux 0 à 3 finis : la Salle s'ouvre, annoncée une seule fois")
    val D = File(jeuMa.terrain, "machines")
    verifierMa(File(D, "plan_de_la_salle.txt").isFile && File(D, "photo.bin").length() == 1048576L && File(D, "ferme/loin").isDirectory,
        "la Salle est meublée (plan, photo de 1 Mio, ferme)")

    println("4. La traversée de la Salle sur le téléphone")
    val avantFichiers = fichiersHors(jeuMa.home, jeuMa.terrain)
    jeuMa.xp = 10 * 30 * 30
    tapeMa("cd ~/terrain_terminagotchi/machines")
    verifierMa(lecMa() == ("sm0" to 1), "entrer dans la Salle choisit le monde : ${lecMa()}")
    val gr = Histoire.graine(jeuMa)
    val k = Machines.memoireKio() ?: 0L
    val sols = mapOf("jouer" to "P2 C1 M2 S1 G1 A2", "dessiner" to "P2 C1 M2 S2 G0 A1", "serveur" to "P3 C2 M3 S3 G0 A2", "robot" to "P4 C3 M3 S1 G0 A1")
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat plan_de_la_salle.txt" },
        { "nproc" }, { "machines coeurs ${Machines.coeurs()}" }, { "free -h" }, { "machines memoire " + "%.1f".format(java.util.Locale.ROOT, k / 1048576.0) },
        { "df -h" }, { "machines ouvre" },
        { "head -5 /proc/cpuinfo" }, { "grep -c ^processor /proc/cpuinfo" }, { "getprop ro.product.model" },
        { "machines monte 1 P1 C1 M1 S1 G0 A1" },
        { "printf '%x\\n' 65" }, { "echo -n A | xxd -b" }, { "machines interrupteurs Zoé" },
        { "machines allume " + Machines.bits(Machines.lettreDefi(jeuMa.nom).code) }, { "wc -c photo.bin" }, { "machines unites" },
        { "uname -r" }, { "uptime" }, { "machines reveil" }, { "machines reveil " + Machines.reveilReponse(gr).joinToString(" ") },
        { "uname -srm" }, { "getprop ro.build.version.release" }, { "ps" }, { "which ls" }, { "machines orchestre" },
        { "machines orchestre " + Machines.orchestre(gr).joinToString(" ") { it.third.toString() } }, { "machines licences" },
        { "machines boite" }, { "machines range" }, { "machines range " + Machines.rangeBoites(gr).joinToString(" ") { it.third } },
        { "machines adulte" }, { "machines conteneur" }, { "machines vm" },
        { "df -h ." }, { "du -sh ." }, { "machines ferme" }, { "machines energie" },
        { "ls ferme" }, { "tar czf sauvegarde.tar.gz collection.txt" }, { "sha256sum sauvegarde.tar.gz > sauvegarde.sha256" },
        { "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/" }, { "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/" },
        { "machines panne" }, { "cd ferme/loin" }, { "sha256sum -c sauvegarde.sha256" }, { "tar xzf sauvegarde.tar.gz -C ../.." },
        { "cd ../.." }, { "machines monte" }, { "machines monte P3 C1 M2 S1 G0 A1" }, { "machines demarre" },
        { "machines monte " + sols[Machines.besoinEpreuve(gr)] }, { "machines demarre" }, { "machines drapeau " + Machines.drapeau(gr) },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = f()
        val avant = lecMa()
        val s = tapeMa(c)
        sorties[c] = s
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecMa()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuMa, "machinerie")) break
    }
    verifierMa(Histoire.fini(jeuMa, "machinerie"), "la Salle est traversée jusqu'au bout (sm0 → sm10) : ${lecMa()}")
    verifierMa("01000001" in (sorties["echo -n A | xxd -b"] ?: ""), "xxd -b du téléphone : 01000001")
    verifierMa("Zoé" !in Machines.carnet(jeuMa), "le prénom tapé reste sur l'écran (le carnet ne le garde pas)")
    verifierMa("sauvegarde.tar.gz: OK" in (sorties["sha256sum -c sauvegarde.sha256"] ?: ""), "la copie lointaine est intacte (OK)")
    val ex = Recompenses.etat(jeuMa).getJSONObject("exploits").keys().asSequence().toList()
    verifierMa("machines.premier_demarrage" !in ex, "un premier démarrage raté : pas d'exploit, même après une machine juste ($ex)")
    verifierMa("carte_mere_miniature" in lstMa(Quetes.q(jeuMa).optJSONArray("objets")), "récompense du monde : une carte mère miniature")
    val nouveaux = fichiersHors(jeuMa.home, jeuMa.terrain) - avantFichiers
    verifierMa(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")

    println("5. Les variantes réservées, le premier démarrage réussi, le dessin")
    val j2 = Jeu(AppareilMa(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierMa(Recompenses.reservee(j2, "mecanique", "chaudrogre") && Recompenses.reservee(j2, "desert", "golemmur") &&
        !Recompenses.reservee(j2, "mecanique", "boulonnet"), "chaudrogre:mecanique et golemmur:desert réservées ; boulonnet:mecanique non")
    j2.nom = "Lune"
    j2.terrain.mkdirs()
    File(j2.terrain, "machines").mkdirs()
    Machines.commande(j2, "monte", j2.terrain)
    Machines.commande(j2, "monte " + sols[Machines.besoinEpreuve(Histoire.graine(j2))], j2.terrain)
    val dem = Machines.commande(j2, "demarre", j2.terrain)
    verifierMa("✨" in dem && !Recompenses.reservee(j2, "mecanique", "chaudrogre"), "démarrée du premier coup : l'exploit, les variantes libérées")
    verifierMa("✨" !in Machines.commande(j2, "demarre", j2.terrain), "l'exploit ne se gagne qu'une fois")
    val tl = ToileMa()
    MachinesDessin.ordinateur(tl, listOf("processeur", "memoire"), 0.5, 0f, 0f, 400f, 240f, 1f)
    MachinesDessin.interrupteurs(tl, "Zoé", 0f, 0f, 400f, 200f, 1f)
    MachinesDessin.reveil(tl, 0.7, 0f, 0f, 400f, 240f, 1f)
    MachinesDessin.atelier(tl, listOf("P2", "C2", "M3", "S1", "G0", "A1"), "ecole", 0.5, 0f, 0f, 400f, 260f, 1f)
    MachinesDessin.ferme(tl, true, 0.8, 0f, 0f, 400f, 225f, 1f)
    MachinesDessin.conteneur(tl, 0.5, 0f, 0f, 400f, 200f, 1f)
    MachinesDessin.salle(tl, 0.3, 0f, 0f, 400f, 225f, 1f)
    verifierMa(tl.n > 200 && tl.textes.any { "processeur" in it } && tl.textes.any { it == "= 195" }, "le dessin : ordinateur, interrupteurs (é = 195 169), réveil, atelier, ferme, conteneur, salle (${tl.n} traits)")
    val vue = Deploie.vue("nproc | head -1")!!
    verifierMa(vue.piecesDe(vue.blocs[0])?.pieces == listOf("processeur") && vue.piecesDe(vue.blocs[1]) == null, "la vue déployée sait que nproc allume le processeur")

    println("\n$okMa réussis, $koMa échoués")
    kotlin.system.exitProcess(if (koMa == 0) 0 else 1)
}
