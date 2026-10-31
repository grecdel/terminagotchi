/*
 * Test JVM de la Citadelle (phase 5) sur Android, portage de pc/outils/test_citadelle.py :
 *   1. les vecteurs communs donnees/citadelle/vecteurs.json (journal, chmod et umask, drapeaux, faux facteur mélangé
 *      comme random.shuffle de Python, entropie, inspecteur des boîtes, tableau de garde, cadenas de la vue déployée)
 *      donnent EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. les commandes intégrées du téléphone : openssl (même format que le vrai openssl : déchiffré par lui, et
 *      l'inverse), diff (même sortie que GNU diff), shuf, kill des processus fantômes ; rien hors du terrain ;
 *   3. l'arbre du Carrefour : la Citadelle s'ouvre après le nid, la bibliothèque et la cave ;
 *   4. la traversée cit0 → cit16 comme dans l'appli, les deux exploits, le bouclier, les variantes réservées ;
 *   5. le dessin (cadenas, plan, forteresse de repli) sur une toile d'essai, et des captures si un dossier est donné.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Citadelle.kt -d cit.jar
 *   java -cp <imitations>:<appli.jar>:cit.jar:kotlin-stdlib.jar CitadelleKt app/src/main/assets
 */
import fr.terminagotchi.Citadelle
import fr.terminagotchi.CitadelleDessin
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Phare
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsCi(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilCi(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsCi(a)
    override fun getApplicationContext(): android.content.Context = this
}

/** Une toile qui compte ce qu'on y dessine (le dessin ne plante pas, il dessine quelque chose). */
class ToileCi : Toile {
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

var okCi = 0
var koCi = 0
fun verifierCi(c: Boolean, m: String) {
    if (c) okCi++ else koCi++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuCi: Jeu
lateinit var shellCi: Shell
lateinit var cmdCi: Commandes

fun lstCi(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun bashCi(cmd: String, ou: File = shellCi.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuCi.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeCi(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellCi.executer(cmd)
    else {
        val interne = cmdCi.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashCi(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuCi, cmd, colle = false, rappel = false, hasard = false, cwd = shellCi.dossier, code = code)
    return sortie
}

fun lecCi(): Pair<String?, Int> = Histoire.leconCourante(jeuCi)?.id to jeuCi.etape

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val captures = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_cit_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilCi(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuCi = Jeu(app)
    jeuCi.changerLangue("fr")
    jeuCi.nom = "Pixel"
    shellCi = Shell(jeuCi.home)
    cmdCi = Commandes(app, jeuCi, { shellCi.dossier })
    jeuCi.module("explo").put("ouverte", true)
    jeuCi.terrain.mkdirs()
    Phare.decalage = 21000

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/citadelle/vecteurs.json").readText())
    verifierCi(Citadelle.journal() == lstCi(v.getJSONArray("journal")), "le journal du gardien (90 lignes identiques)")
    val ec = v.getJSONObject("echecs")
    verifierCi(Citadelle.echecs() == ec.keys().asSequence().associateWith { ec.getInt(it) }, "les échecs par adresse : ${Citadelle.echecs()}")
    var ko = 0
    val ch = v.getJSONArray("chmod")
    for (i in 0 until ch.length()) {
        val x = ch.getJSONObject(i)
        val m = Citadelle.chmodMode(x.getString("spec"), x.getInt("depart"), x.getInt("masque"))
        val att = if (x.isNull("mode")) null else x.getInt("mode")
        if (m != att) { ko++; println("    chmod $x → $m") }
    }
    verifierCi(ko == 0, "${ch.length()} chmod (octal et lettres, masques 022 et 077) identiques")
    ko = 0
    val um = v.getJSONArray("umask")
    for (i in 0 until um.length()) { val x = um.getJSONObject(i)
        if (Citadelle.umaskMode(x.getInt("masque")) != x.getInt("fichier") || Citadelle.umaskMode(x.getInt("masque"), true) != x.getInt("dossier")) ko++ }
    verifierCi(ko == 0, "${um.length()} masques umask identiques")
    ko = 0
    val dr = v.getJSONArray("drapeaux")
    for (i in 0 until dr.length()) { val x = dr.getJSONObject(i)
        if (Citadelle.drapeau(x.getString("graine"), x.getString("boite"), x.getString("genre")) != x.getString("drapeau")) ko++ }
    verifierCi(ko == 0, "${dr.length()} drapeaux identiques (SHA-256 de la graine)")
    ko = 0
    val fa = v.getJSONArray("facteur")
    for (i in 0 until fa.length()) { val x = fa.getJSONObject(i)
        val o = Citadelle.facteur(x.getString("graine")).map { listOf("${it.first}", it.second, "${it.third}") }
        val a = (0 until x.getJSONArray("ordre").length()).map { lstCi(x.getJSONArray("ordre").getJSONArray(it)) }
        if (o != a || Citadelle.bonsIndices(x.getString("graine")).map { "$it" } != lstCi(x.getJSONArray("bons"))) { ko++; println("    facteur $o / $a") } }
    verifierCi(ko == 0, "${fa.length()} graines : le faux facteur mélangé comme random.shuffle de Python")
    ko = 0
    val fo = v.getJSONArray("force")
    val forces = (0 until Citadelle.donnees().getJSONArray("force").length()).map { Citadelle.donnees().getJSONArray("force").getJSONObject(it) }
    for (i in 0 until fo.length()) { val x = fo.getJSONObject(i); val f = forces[i]
        val b = Citadelle.bits(f)
        if (Math.abs(b - x.getDouble("bits")) > 1e-6 || Math.abs(Citadelle.dureeEssais(b) - x.getDouble("duree")) > 1e-6 * Math.max(1.0, x.getDouble("duree"))) ko++ }
    verifierCi(ko == 0, "l'entropie et le temps d'essai des ${fo.length()} exemples")
    ko = 0
    val ins = v.getJSONArray("inspecteur")
    for (i in 0 until ins.length()) { val x = ins.getJSONObject(i)
        val mo = x.getJSONObject("modes"); val modes = mo.keys().asSequence().associateWith { if (mo.isNull(it)) null else mo.getInt(it) }
        val r = Citadelle.inspecter(Citadelle.boite(x.getString("boite"))!!, modes, x.getBoolean("rotation")).map { listOf(it.first, "${it.second}") }
        val a = (0 until x.getJSONArray("regles").length()).map { lstCi(x.getJSONArray("regles").getJSONArray(it)) }
        if (r != a) { ko++; println("    inspecteur $x → $r") } }
    verifierCi(ko == 0, "${ins.length()} inspections des boîtes identiques")
    ko = 0
    val dd = v.getJSONArray("droits")
    for (i in 0 until dd.length()) { val x = dd.getJSONObject(i)
        val k = Deploie.droits(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.mode, it.fichier, it.avant, it.apres, it.octal, "${it.suppose}") }
        val a = (0 until x.getJSONArray("droits").length()).map { x.getJSONArray("droits").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("mode"), it.getString("fichier"), it.getString("avant"),
                it.getString("apres"), it.getString("octal"), "${it.getBoolean("suppose")}") }
        if (k != a) { ko++; println("    droits ${x.getString("ligne")} → $k (attendu $a)") } }
    verifierCi(ko == 0, "${dd.length()} lignes : les cadenas de la vue déployée (chmod, umask)")
    ko = 0
    val ta = v.getJSONArray("tableau")
    for (i in 0 until ta.length()) { val x = ta.getJSONObject(i)
        val t = Citadelle.tableau(x.getInt("g"), x.getInt("p"), x.getInt("s")).map { listOf(it.first, "${it.second}", "${it.third}") }
        val a = (0 until x.getJSONArray("t").length()).map { lstCi(x.getJSONArray("t").getJSONArray(it)) }
        if (t != a) ko++ }
    verifierCi(ko == 0 && Citadelle.mots() == lstCi(v.getJSONArray("mots")), "le tableau de garde et les 128 mots")

    println("2. Les commandes intégrées du téléphone")
    val tmp = File(jeuCi.terrain, "essai").apply { mkdirs() }
    File(tmp, "l.txt").writeText("le secret de la créature\n")
    tapeCi("cd ~/terrain_terminagotchi/essai")
    val aOpenssl = ProcessBuilder("bash", "-c", "command -v openssl").start().waitFor() == 0
    cmdCi.executer("openssl enc -aes-256-cbc -pbkdf2 -in l.txt -out l.enc -pass pass:exemple")
    verifierCi(File(tmp, "l.enc").readBytes().copyOf(8).contentEquals("Salted__".toByteArray()), "openssl intégré : « Salted__ » + sel, comme le vrai")
    if (aOpenssl) {
        val (s, c) = bashCi("openssl enc -d -aes-256-cbc -pbkdf2 -in l.enc -pass pass:exemple", tmp)
        verifierCi(c == 0 && s == "le secret de la créature\n", "le VRAI openssl déchiffre ce que le téléphone a chiffré")
        bashCi("openssl enc -aes-256-cbc -pbkdf2 -in l.txt -out v.enc -pass pass:exemple", tmp)
        verifierCi(cmdCi.executer("openssl enc -d -aes-256-cbc -pbkdf2 -in v.enc -pass pass:exemple")!!.texte == "le secret de la créature\n",
            "le téléphone déchiffre ce que le vrai openssl a chiffré")
    }
    verifierCi("bad decrypt" in cmdCi.executer("openssl enc -d -aes-256-cbc -pbkdf2 -in l.enc -pass pass:mauvaise")!!.texte ||
        cmdCi.executer("openssl enc -d -aes-256-cbc -pbkdf2 -in l.enc -pass pass:mauvaise")!!.texte != "le secret de la créature\n",
        "mauvaise clé : refusé (bad decrypt)")
    verifierCi(cmdCi.executer("openssl enc -aes-256-cbc -pbkdf2 -in ../../../../etc/hostname -out x -pass pass:e")!!.texte.contains("essai").not() &&
        !File(tmp, "x").exists(), "openssl intégré : rien hors du terrain")
    File(tmp, "a").writeText("Bonjour\nLe capitaine\nFin\n"); File(tmp, "b").writeText("Bonjour\nLe capitaine URGENT\nclique ici\nFin\n")
    val (vrai, _) = bashCi("diff a b", tmp)
    verifierCi(cmdCi.executer("diff a b")!!.texte == vrai.trimEnd('\n'), "diff intégré = GNU diff : ${vrai.trim().replace("\n", " ⏎ ")}")
    File(tmp, "c").writeText("x\ny\n"); File(tmp, "d").writeText("x\n")
    verifierCi(cmdCi.executer("diff c d")!!.texte == bashCi("diff c d", tmp).first.trimEnd('\n') &&
        cmdCi.executer("diff d c")!!.texte == bashCi("diff d c", tmp).first.trimEnd('\n'), "diff intégré : lignes enlevées, lignes ajoutées")
    File(tmp, "m").writeText((1..20).joinToString("\n") + "\n")
    val sh = cmdCi.executer("shuf -n 4 m")!!.texte.split("\n")
    verifierCi(sh.size == 4 && sh.toSet().size == 4, "shuf -n 4 : quatre lignes différentes")
    verifierCi(cmdCi.executer("kill 99999") == null, "kill d'un autre numéro : part au vrai shell (rien de simulé)")

    println("3. L'arbre du Carrefour")
    val h = Histoire.h(jeuCi)
    verifierCi(!Histoire.ouvert(jeuCi, "citadelle") && Citadelle.manque(jeuCi).size == 3, "fermée au début : il manque ${Citadelle.manque(jeuCi)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque", "cave")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid", "bibliotheque")) h.getJSONArray("ailes").put(c)
    h.put("chap", "cave")
    h.put("mondes_annonces", JSONArray().put("port"))
    Histoire.tick(jeuCi, "ls", false, jeuCi.home, 0)
    verifierCi(Histoire.fini(jeuCi, "cave") && Histoire.ouvert(jeuCi, "citadelle"), "nid, bibliothèque et cave finis : la Citadelle s'ouvre")
    verifierCi("citadelle" in lstCi(h.optJSONArray("mondes_annonces")) && !Citadelle.annonce(jeuCi), "annoncée une seule fois")
    verifierCi(File(jeuCi.terrain, "citadelle/regle_d_or.txt").readText().contains("Pixel"), "la Citadelle est meublée")

    println("4. La traversée de la Citadelle sur le téléphone")
    jeuCi.xp = 10 * 30 * 30
    tapeCi("cd ~/terrain_terminagotchi/citadelle")
    verifierCi(lecCi() == ("cit0" to 1), "entrer dans la Citadelle choisit le monde : ${lecCi()}")
    val gr = Histoire.graine(jeuCi)
    val d = { b: String, g: String -> Citadelle.drapeau(gr, b, g) }
    val pids = { Citadelle.fictifsVivants(jeuCi).joinToString(" ") { "${it.first}" } }
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat regle_d_or.txt" },
        { "ls -l coffre.txt" }, { "chmod 600 coffre.txt" }, { "chmod u+x ronde.sh" },
        { "id" }, { "grep veilleurs groupes.txt" }, { "citadelle chown sentinelle:veilleurs tour_de_guet.txt" },
        { "umask" }, { "(umask 077; touch carnet_secret.txt)" }, { "citadelle masque 077" },
        { "tail -n 5 journaux/acces.log" }, { "grep -c ECHEC journaux/acces.log" },
        { "grep ECHEC journaux/acces.log | cut -d \" \" -f 4 | sort | uniq -c | sort -n" }, { "echo 203.0.113.66 > intrus.txt" },
        { "find . -name \"*.glitch\"" }, { "find . -newer repere.txt" }, { "find . -name \"*.glitch\" -delete" },
        { "cat cadeau.sh" }, { "grep rm cadeau.sh" }, { "chmod -x cadeau.sh" },
        { "citadelle ps" }, { "kill ${pids()}" }, { "citadelle tableau" },
        { "sha256sum tresor/carte.txt" }, { "sha256sum -c empreintes_tresor.sha256" }, { "echo couronne > altere.txt" },
        { "tar cf coffre_de_secours.tar parchemins" }, { "tar xf coffre_de_secours.tar" }, { "rm -f parchemins/*.verrou" },
        { "sha256sum -c parchemins.sha256" },
        { "cat lettre.txt" }, { "openssl enc -aes-256-cbc -pbkdf2 -in lettre.txt -out lettre.enc -pass pass:${Citadelle.PASSE}" },
        { "openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:${Citadelle.MAUVAISE}" },
        { "openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:${Citadelle.PASSE}" },
        { "diff vraie_lettre.txt lettre_du_facteur.txt" }, { "curl -s http://localhost:8042/courrier" }, { "citadelle facteur" },
        { "citadelle facteur " + Citadelle.bonsIndices(gr).joinToString(" ") },
        { "wc -l mots.txt" }, { "shuf -n 4 mots.txt" }, { "citadelle force" },
        { "citadelle boites" }, { "ls -la boites/enumeration" }, { "grep -r \"TG{\" boites/enumeration" },
        { "citadelle drapeau ${d("enumeration", "entree")}" }, { "citadelle drapeau ${d("enumeration", "donjon")}" },
        { "chmod o-rwx boites/enumeration/.cave_oubliee" }, { "citadelle inspecteur enumeration" },
        { "ls -l boites/droits" }, { "find boites/droits -perm -o+w" }, { "grep -r \"TG{\" boites/droits" },
        { "citadelle drapeau ${d("droits", "entree")}" }, { "citadelle drapeau ${d("droits", "donjon")}" },
        { "chmod o-rwx boites/droits/*" }, { "citadelle inspecteur droits" },
        { "ls -la boites/secrets" }, { "grep -r mot_de_passe boites/secrets" },
        { "citadelle drapeau ${d("secrets", "entree")}" }, { "citadelle drapeau ${d("secrets", "donjon")}" },
        { "rm boites/secrets/.historique_fictif" }, { "citadelle rotation secrets" }, { "citadelle inspecteur secrets" },
        { "ss -tln" }, { "citadelle vague" }, { "find . -name \"*.glitch\" -delete" }, { "kill ${pids()}" },
        { "chmod 600 secrets_du_pont_levis.txt" }, { "citadelle tableau" },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = f()
        val s = tapeCi(c)
        sorties[c] = s
        if (System.getenv("TG_DEBUG") != null) println("    · $c → ${lecCi()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuCi, "citadelle")) break
    }
    verifierCi(Histoire.fini(jeuCi, "citadelle"), "la Citadelle est défendue jusqu'au bout (cit0 → cit16) : ${lecCi()}")
    verifierCi("JAMAIS" in (sorties["curl -s http://localhost:8042/courrier"] ?: ""), "le pont curl : le phare du Port (dans l'appli) répond /courrier")
    verifierCi("Pixel" in (sorties["openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:${Citadelle.PASSE}"] ?: ""), "le coffre s'ouvre avec la clé d'exemple")
    val ex = Recompenses.etat(jeuCi).getJSONObject("exploits").keys().asSequence().toList()
    verifierCi(ex.containsAll(listOf("citadelle.boite", "citadelle.boite.droits", "citadelle.boite.secrets", "citadelle.vague")),
        "les exploits de la Citadelle : les trois boîtes maîtrisées et la grande vague")
    verifierCi(Recompenses.boitesMaitrisees(jeuCi) == listOf("enumeration", "droits", "secrets"), "les gardiens des trois boîtes sont rencontrables (glitch)")
    verifierCi("bouclier_miniature" in lstCi(fr.terminagotchi.Quetes.q(jeuCi).optJSONArray("objets")), "récompense du monde : un bouclier miniature")
    verifierCi(Citadelle.fictifsVivants(jeuCi).isEmpty(), "plus aucun processus fantôme")

    println("5. Les variantes Démons au tirage normal, le dessin")
    val j2 = Jeu(AppareilCi(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierCi(!Recompenses.reservee(j2, "arcane", "ricanombre") && !Recompenses.reservee(j2, "toxique", "sulfurette"),
        "ricanombre:arcane, sulfurette:toxique… au tirage normal (la récompense de la Citadelle : le glitch des gardiens)")
    Recompenses.exploit(j2, "citadelle.boite")
    verifierCi(Recompenses.gardienDe(j2, fr.terminagotchi.Bestiaire.espece("ricanombre")!!) == "enumeration", "après la boîte : son gardien, Ricanombre")
    val tl = ToileCi()
    CitadelleDessin.cadenas(tl, Deploie.droits("chmod 600 coffre.txt")[0], 0.8, 0f, 0f, 400f, 120f, 1f)
    CitadelleDessin.plan(tl, listOf("remparts/x.glitch"), 1, 0, 0.3, 0f, 0f, 400f, 300f, 1f)
    CitadelleDessin.forteresse(tl, 0.2, 0f, 0f, 400f, 225f, 1f)
    verifierCi(tl.n > 60 && tl.textes.any { "→ rw-------" in it }, "le dessin : cadenas, plan de garde, forteresse de repli (${tl.n} traits)")
    val vue = Deploie.vue("chmod 600 coffre.txt")!!
    verifierCi(vue.droitsDe(vue.blocs[0]) != null && vue.droitsDe(vue.blocs[1]) == null, "la vue déployée sait que le bloc chmod a ses cadenas")

    Phare.toutEteindre()
    println("\n$okCi réussis, $koCi échoués")
    kotlin.system.exitProcess(if (koCi == 0) 0 else 1)
}
