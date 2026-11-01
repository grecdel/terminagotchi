/*
 * Test JVM du Poste de Contrôle (phase 5) sur Android, portage de pc/outils/test_controle.py :
 *   1. les vecteurs communs donnees/controle/vecteurs.json (les caisses et la plus lourde, les pourcentages et les jauges,
 *      le PATH, le carnet de bord et ses alertes, les réveils cron — champs, équivalences, prochaine sonnerie —, les
 *      familles mélangées comme random.shuffle de Python, la distribution, l'équipage, la vague et ses numéros simulés,
 *      le tableau de bord de la vue déployée) : EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. l'arbre du Carrefour : le Poste s'ouvre après les niveaux 0 à 6 (annoncé une fois), meublé ;
 *   3. la traversée ct0 → ct7 comme dans l'appli (tâches de fond, alias, journalctl, crontab, paquets, services et
 *      /etc/passwd racontés ; la vague SIMULÉE : controle ps, kill PID intercepté) ; le veilleur arrêté par erreur
 *      (expliqué, nouvelle vague) ; l'exploit « la vague » ; le pupitre ; rien hors du terrain ;
 *   4. les variantes réservées, le dessin (tableau, jauges, poste de repli) sur une toile d'essai ; la vue déployée.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Controle.kt -d ctl.jar
 *   java -cp <imitations>:<appli.jar>:ctl.jar:kotlin-stdlib.jar ControleKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Controle
import fr.terminagotchi.ControleDessin
import fr.terminagotchi.Deploie
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
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class ActifsCt(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilCt(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsCt(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileCt : Toile {
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

var okCt = 0
var koCt = 0
fun verifierCt(c: Boolean, m: String) {
    if (c) okCt++ else koCt++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuCt: Jeu
lateinit var shellCt: Shell
lateinit var cmdCt: Commandes

fun lstCt(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsCt(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }

fun bashCt(cmd: String, ou: File = shellCt.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuCt.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeCt(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellCt.executer(cmd)
    else {
        val interne = cmdCt.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashCt(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuCt, cmd, colle = false, rappel = false, hasard = false, cwd = shellCt.dossier, code = code)
    return sortie
}

fun lecCt(): Pair<String?, Int> = Histoire.leconCourante(jeuCt)?.id to jeuCt.etape

fun fichiersHorsCt(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_ct_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilCt(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuCt = Jeu(app)
    jeuCt.changerLangue("fr")
    jeuCt.nom = "Pixel"
    shellCt = Shell(jeuCt.home)
    cmdCt = Commandes(app, jeuCt, { shellCt.dossier })
    jeuCt.module("explo").put("ouverte", true)
    jeuCt.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/controle/vecteurs.json").readText())
    var ko = 0
    fun sha(b: ByteArray) = MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }
    for (x in objetsCt(v.getJSONArray("parties"))) {
        val g = x.getString("graine")
        val ca = (0 until x.getJSONArray("caisses").length()).map { x.getJSONArray("caisses").getJSONArray(it).let { a -> a.getString(0) to a.getInt(1) } }
        if (Controle.caisses(g) != ca || Controle.caisseLourde(g) != x.getString("lourde")) { ko++; println("    caisses $g → ${Controle.caisses(g)}") }
        if (sha(Controle.caisseOctets(g, Controle.caisseLourde(g))) != x.getString("sha_lourde")) { ko++; println("    octets $g") }
        if (Controle.journalLignes(g) != lstCt(x.getJSONArray("journal")) || Controle.nbAlertes(g) != x.getInt("alertes")) { ko++; println("    journal $g → ${Controle.journalLignes(g).take(3)}") }
        if (Controle.cronSituation(g).optString("id") != x.getString("cron")) { ko++; println("    cron $g") }
        val fa = (0 until x.getJSONArray("familles").length()).map { lstCt(x.getJSONArray("familles").getJSONArray(it)) }
        if (Controle.famillesCartes(g).map { listOf("${it.n}", it.id, it.rep) } != fa) { ko++; println("    familles $g → ${Controle.famillesCartes(g).map { it.id }}") }
        for (vg in objetsCt(x.getJSONArray("vagues"))) {
            val n = vg.getInt("n")
            val p = vg.getJSONObject("pids"); val pa = p.keys().asSequence().associateWith { p.getInt(it) }
            if (Controle.vagueSuspects(g, n) != lstCt(vg.getJSONArray("suspects")) || Controle.pidsSimules(g, n) != pa) { ko++; println("    vague $g $n → ${Controle.vagueSuspects(g, n)} ${Controle.pidsSimules(g, n)}") }
        }
    }
    verifierCt(ko == 0, "${v.getJSONArray("parties").length()} parties : caisses, la plus lourde, carnet de bord, alertes, réveil, familles, vagues")
    ko = 0
    for (x in objetsCt(v.getJSONArray("caisse_rep"))) if (Controle.caisseOk(x.getString("reponse"), x.getString("graine")) != x.getBoolean("ok")) { ko++; println("    caisse $x") }
    for (x in objetsCt(v.getJSONArray("pourcents"))) {
        val p = Controle.pourcentage(x.getLong("u"), x.getLong("t"))
        if (p != x.getInt("p") || Controle.jauge(p) != x.getString("jauge")) { ko++; println("    pourcentage $x → $p") }
    }
    for (x in objetsCt(v.getJSONArray("paths"))) if (Controle.pathOk(x.getString("reponse"), x.getString("path"), x.getBoolean("win")) != x.getBoolean("ok")) { ko++; println("    path $x") }
    verifierCt(ko == 0, "la caisse (avec ou sans .bin, le chemin), les pourcentages et les jauges, le compte du PATH")
    ko = 0
    for (x in objetsCt(v.getJSONArray("crons"))) {
        val c = Controle.cron(x.getString("ligne"))?.map { it.sorted() }
        val att = if (x.isNull("champs")) null else (0 until x.getJSONArray("champs").length()).map { i -> (0 until x.getJSONArray("champs").getJSONArray(i).length()).map { x.getJSONArray("champs").getJSONArray(i).getInt(it) } }
        if (c != att) { ko++; println("    cron ${x.getString("ligne")} → $c") }
    }
    val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")
    for (x in objetsCt(v.getJSONArray("prochaines"))) {
        val p = Controle.prochaine(x.getString("ligne"), LocalDateTime.parse(x.getString("depuis"), fmt))?.format(fmt)
        if (p != (if (x.isNull("prochaine")) null else x.getString("prochaine"))) { ko++; println("    prochaine ${x.getString("ligne")} ${x.getString("depuis")} → $p") }
    }
    for (x in objetsCt(v.getJSONArray("pareils"))) if (Controle.cronPareil(x.getString("a"), x.getString("b")) != x.getBoolean("pareil")) { ko++; println("    pareil $x") }
    for (x in objetsCt(v.getJSONArray("cron_rep"))) if (Controle.cronOk(x.getString("reponse"), x.getString("graine")) != x.getBoolean("ok")) { ko++; println("    cron_rep $x") }
    for (x in objetsCt(v.getJSONArray("crontabs"))) {
        val l = Controle.lignesCrontab(x.getString("texte")).map { listOf(it.first, "${it.second}") }
        val att = (0 until x.getJSONArray("lignes").length()).map { x.getJSONArray("lignes").getJSONArray(it).let { a -> listOf(a.getString(0), "${a.getBoolean(1)}") } }
        if (l != att) { ko++; println("    crontab $l") }
    }
    verifierCt(ko == 0, "cron : les 5 champs, */15, 1-5, dimanche 0 = 7, les lignes fausses, la prochaine sonnerie, la réponse de la partie")
    ko = 0
    for (x in objetsCt(v.getJSONArray("quiz"))) {
        val g = x.getString("graine")
        val (bon, justes) = Controle.quizJustes(Controle.famillesCartes(g), lstCt(x.getJSONArray("rep")), "dap")
        val att = (0 until x.getJSONArray("justes").length()).map { lstCt(x.getJSONArray("justes").getJSONArray(it)) }
        if (bon != x.getBoolean("ok") || justes.map { listOf("${it.n}", it.id) } != att) { ko++; println("    quiz $x") }
    }
    for (x in objetsCt(v.getJSONArray("distrib"))) {
        val o = x.getJSONObject("osr"); val osr = o.keys().asSequence().associateWith { o.getString(it) }
        if (Controle.osReleaseDe(x.getString("texte")) != osr || Controle.distributionOk(x.getString("reponse"), osr) != x.getBoolean("ok")) { ko++; println("    distribution ${x.getString("reponse")} $osr") }
    }
    for (x in objetsCt(v.getJSONArray("equipage"))) {
        val nom = x.getString("nom")
        val (txt, uid) = Controle.equipageAjoute(Controle.equipageTexte(), nom)
        val base = if (nom == "vigie") Controle.equipageAjoute(Controle.equipageAjoute(Controle.equipageTexte(), "mousse").first, "vigie") else txt to uid
        if (Controle.nomValide(nom) != x.getBoolean("valide") || base.first != x.getString("texte") || base.second != (if (x.isNull("uid")) null else x.getInt("uid")) ||
            Controle.nouveauxMembres(base.first) != lstCt(x.getJSONArray("nouveaux"))) { ko++; println("    équipage $nom → ${base.second}") }
    }
    for (x in objetsCt(v.getJSONArray("bilans"))) if (Controle.bilanVague(x.getJSONArray("suspects").length(), x.getBoolean("veilleur")) != x.getString("bilan")) { ko++; println("    bilan $x") }
    verifierCt(ko == 0, "les familles (d, a, p), la distribution dans /etc/os-release, l'équipage (UID suivant), le bilan d'une vague")
    ko = 0
    for (x in objetsCt(v.getJSONArray("tableau"))) {
        val k = Controle.tableauxDe(x.getString("ligne")).map { listOf(it.first, it.second) }
        val att = (0 until x.getJSONArray("tableaux").length()).map { lstCt(x.getJSONArray("tableaux").getJSONArray(it)) }
        val d = Deploie.tableaux(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.jauge, it.sens) }
        val datt = (0 until x.getJSONArray("deploie").length()).map { lstCt(x.getJSONArray("deploie").getJSONArray(it)) }
        if (k != att || d != datt) { ko++; println("    tableau ${x.getString("ligne")} → $k / $d (attendu $att / $datt)") }
    }
    verifierCt(ko == 0, "le tableau de bord : ps, kill, free, export, journalctl, crontab, systemctl, apt install… et la vue déployée")

    println("2. L'arbre du Carrefour : quand le Poste s'ouvre")
    val h = Histoire.h(jeuCt)
    verifierCt(!Histoire.ouvert(jeuCt, "controle"), "fermé au début : il manque ${Controle.manque(jeuCt)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque", "cave")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid", "bibliotheque", "cave")) h.getJSONArray("ailes").put(c)
    h.put("mondes_annonces", JSONArray(listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees")))
    h.put("annonce_attente", true)
    Histoire.tick(jeuCt, "ls", false, jeuCt.home, 0)
    verifierCt(Histoire.ouvert(jeuCt, "controle") && "controle" in lstCt(h.optJSONArray("mondes_annonces")) && !Controle.annonce(jeuCt),
        "les niveaux 0 à 6 faits : le Poste s'ouvre, annoncé une seule fois")
    val D = File(jeuCt.terrain, "controle")
    D.mkdirs()
    Histoire.tick(jeuCt, "ls", false, jeuCt.home, 0)
    verifierCt(File(D, "consignes_du_poste.txt").isFile && File(D, "sac_a_dos.sh").isFile && File(D, "reveils.crontab").isFile &&
        File(D, "equipage.txt").isFile && (File(D, "entrepot").list()?.size ?: 0) == 4, "le Poste est meublé (consignes, sac à dos, réveils, équipage, 4 caisses)")

    println("3. La traversée du Poste sur le téléphone")
    val avantFichiers = fichiersHorsCt(jeuCt.home, jeuCt.terrain)
    jeuCt.xp = 10 * 30 * 30
    tapeCt("cd ~/terrain_terminagotchi/controle")
    verifierCt(lecCt() == ("ct0" to 1), "entrer dans le Poste choisit le monde : ${lecCt()}")
    val gr = Histoire.graine(jeuCt)
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat consignes_du_poste.txt" },
        { "ps" }, { "echo $$" }, { "ls /proc/$$" }, { "head -3 /proc/$$/status" }, { "controle habitants" }, { "sleep 1" }, { "top -n 1 | head -5" },
        { "free -h" }, { "df -h ." }, { "du -sh entrepot/*" }, { "controle entrepot cartes_du_ciel" }, { "controle entrepot ${Controle.caisseLourde(gr)}" },
        { "uptime" }, { "nproc" }, { "controle jauges" },
        { "echo \$HOME" }, { "echo \$PATH | tr ':' '\\n'" }, { "controle path ${(System.getenv("PATH") ?: "").split(":").size}" }, { "which ls" },
        { "export COULEUR=bleu; sh -c 'echo \$COULEUR'" }, { "cat sac_a_dos.sh" }, { ". ./sac_a_dos.sh; echo \$POSTE" },
        { "controle journal" }, { "tail -n 5 carnet_de_bord.log" }, { "grep -c ALERTE carnet_de_bord.log" }, { "controle alertes 99" },
        { "controle alertes ${Controle.nbAlertes(gr)}" }, { "logcat -d -t 5" },
        { "controle reveils" }, { "cat reveils.crontab" }, { "controle cron 0 7 a b c" }, { "controle cron \"${Controle.cronSituation(gr).optString("rep")}\"" },
        { "echo \"*/15 * * * * echo RONDE >> ronde.log\" >> reveils.crontab" }, { "controle reveils" },
        { "getprop ro.build.version.release" }, { "controle distribution fedora" }, { "controle distribution android" }, { "controle familles" },
        { "controle familles " + Controle.famillesCartes(gr).joinToString(" ") { it.rep } }, { "controle installer" }, { "controle magasin" },
        { "controle services" }, { "controle useradd Lea" }, { "controle useradd lea" }, { "tail -2 equipage.txt" },
        { "controle alerte" }, { "controle ps" },
        { "kill " + Controle.vivants(jeuCt).first { it.second == Controle.VEILLEUR }.first }, { "controle tableau" }, { "controle alerte" },
        { "kill " + Controle.suspectsVivants(jeuCt).joinToString(" ") { "${it.first}" } }, { "controle tableau" },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = try { f() } catch (e: Exception) { "true" }
        val avant = lecCt()
        val s = tapeCt(c)
        sorties.putIfAbsent(c, s)
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecCt()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuCt, "controle")) break
    }
    verifierCt(Histoire.fini(jeuCt, "controle"), "le Poste est traversé jusqu'au bout (ct0 → ct7) : ${lecCt()}")
    verifierCt("✖" in (sorties["controle entrepot cartes_du_ciel"] ?: "✖") || Controle.caisseLourde(gr) == "cartes_du_ciel", "une caisse plus légère refusée")
    verifierCt("✖" in (sorties["controle distribution fedora"] ?: "") && "Android" in (sorties["controle distribution android"] ?: ""),
        "la distribution du téléphone : Android")
    verifierCt("✖" in (sorties["controle useradd Lea"] ?: "") && "lea:x:1001:1001::/home/lea:/bin/bash" in File(D, "equipage.txt").readText(),
        "l'équipage du Poste : « Lea » refusé (majuscule), lea prend l'UID 1001")
    verifierCt(sorties.entries.any { it.key == "controle tableau" && "veilleur" in it.value }, "le veilleur arrêté par erreur : le tableau le dit")
    val ex = Recompenses.etat(jeuCt).getJSONObject("exploits").keys().asSequence().toList()
    verifierCt("controle.vague" in ex, "l'exploit « la vague » ($ex)")
    verifierCt("pupitre" in lstCt(Quetes.q(jeuCt).optJSONArray("objets")), "récompense du monde : un pupitre à voyants")
    verifierCt(!File(D, "ronde.log").exists(), "aucun réveil n'a été lancé")
    val nouveaux = fichiersHorsCt(jeuCt.home, jeuCt.terrain) - avantFichiers
    verifierCt(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")
    val cmds = Controle.lecons(jeuCt).values.flatMap { it.etapes }.joinToString(" ") { it.cmd }
    verifierCt("sudo" !in cmds && !Regex("(dnf|apt|pm)\\s+install|systemctl\\s+(start|stop|restart)|crontab\\s+-e").containsMatchIn(cmds),
        "aucune étape n'utilise sudo, n'installe, n'arrête un service ni ne pose un vrai cron")

    println("4. Les variantes réservées, le dessin, la vue déployée")
    val j2 = Jeu(AppareilCt(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierCt(Recompenses.reservee(j2, "mecanique", "horlogrif") && Recompenses.reservee(j2, "neon", "parasouris") &&
        Recompenses.reservee(j2, "montagne", "pavegarde") && !Recompenses.reservee(jeuCt, "mecanique", "horlogrif") && Recompenses.faveur(jeuCt) != null,
        "les variantes réservées au Poste (horlogrif mécanique, parasouris néon, pavegarde montagne) : avant l'exploit non, après oui")
    val tl = ToileCt()
    ControleDessin.tableau(tl, Deploie.Tableau(0, "ps", "habitants", "lit"), 0.4, 0f, 0f, 400f, 96f, 1f)
    ControleDessin.tableau(tl, Deploie.Tableau(0, "kill", "habitants", "arrete"), 0.2, 0f, 0f, 400f, 96f, 1f)
    ControleDessin.tableau(tl, Deploie.Tableau(0, "sudo", "services", "change"), 0.1, 0f, 0f, 400f, 60f, 1f)
    ControleDessin.jauges(tl, listOf("mémoire" to 35, "disque" to 92), 0f, 0f, 300f, 100f, 1f)
    ControleDessin.poste(tl, 0.7, 0f, 0f, 400f, 225f, 1f)
    verifierCt(tl.n > 40 && tl.textes.any { "les habitants" in it } && tl.textes.any { "92 %" == it } && tl.textes.any { "⏰" == it },
        "le dessin : tableau de bord (lire, arrêter, changer), jauges, poste de repli (${tl.n} traits)")
    val vue = Deploie.vue("ps aux | grep fictif")!!
    verifierCt(vue.tableauDe(vue.blocs[0])?.jauge == "habitants" && vue.tableauDe(vue.blocs[0])?.sens == "lit",
        "la vue déployée sait que ps lit les habitants")

    println("\n$okCt réussis, $koCt échoués")
    kotlin.system.exitProcess(if (koCt == 0) 0 else 1)
}
