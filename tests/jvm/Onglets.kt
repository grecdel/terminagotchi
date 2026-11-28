/*
 * Test JVM : les onglets du terminal de l'appli (Onglets.kt), plusieurs terminaux comme plusieurs fenêtres sur PC.
 *   1. ouvrir, choisir, fermer ; le dernier ne se ferme pas ; 4 au plus ; « Terminal 1, 2… » (numéro libre réutilisé) ;
 *   2. deux onglets indépendants : un cd dans l'un ne change pas l'autre (pwd, ls relatif, `cd -`, code de sortie) ;
 *   3. l'historique (↑ ↓) de chaque onglet est à lui ; un nouvel onglet part de l'historique de la partie ;
 *   4. la créature mange les commandes des deux onglets, et la leçon voit chaque commande avec le dossier de SON
 *      onglet (« ls dans la grande salle » ne compte pas dans un onglet resté au camp) ;
 *   5. une autre partie : chaque onglet revient au camp ; les textes des onglets existent dans les 14 langues ;
 *   6. le téléphone tourne / l'écran est recréé : Onglets.etat puis reprendre rend les mêmes onglets (dossier, cd -,
 *      code, historique, ligne à moitié tapée, onglet affiché), jamais un dossier hors du camp.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Onglets.kt -d onglets.jar
 *   java -cp <imitations>:<appli.jar>:onglets.jar:kotlin-stdlib.jar OngletsKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Onglets
import fr.terminagotchi.Racine
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import java.io.File

class ActifsO(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilO(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsO(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okO = 0
var koO = 0
fun verifO(c: Boolean, m: String) {
    if (c) okO++ else koO++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_onglets_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilO(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.historique.addAll(listOf("ls", "pwd"))
    val onglets = Onglets({ Shell(jeu.home).also { s -> s.journal = { jeu.journal.toList() } } }, { jeu.historique.toList() })
    val commandes = Commandes(app, jeu, { onglets.actif.shell.dossier })

    /** Ce que fait l'appli quand on tape une ligne dans l'onglet affiché : le shell de CET onglet, puis le tour de jeu
     *  avec SON dossier (TerminalActivity.valider → apresCommande). */
    fun tape(ligne: String): String {
        val o = onglets.actif
        o.noter(ligne)
        Maison.placer(jeu, o.shell.dossier)
        if (jeu.historique.lastOrNull() != ligne) jeu.historique.add(ligne)
        val interne = commandes.executer(ligne)
        val sortie = interne?.texte ?: o.shell.executer(ligne)
        Tour.apresCommande(jeu, ligne, colle = false, rappel = false, hasard = false, cwd = o.shell.dossier,
            code = if (interne != null) 0 else o.shell.code)
        return sortie
    }
    fun lecon() = (Histoire.leconCourante(jeu)?.id) to jeu.etape

    println("1. Ouvrir, choisir, fermer")
    val t1 = onglets.actif
    verifO(onglets.liste.size == 1 && t1.nom() == "Terminal 1", "au départ : un seul onglet, « ${t1.nom()} »")
    verifO(!onglets.fermer(), "le dernier onglet ne se ferme pas (exit referme alors le jeu, comme avant)")
    val t2 = onglets.ouvrir()!!
    verifO(onglets.actif === t2 && t2.nom() == "Terminal 2" && t2.shell !== t1.shell, "« + » : Terminal 2 s'ouvre, avec son propre shell, et devient l'onglet affiché")
    val t3 = onglets.ouvrir()!!
    val t4 = onglets.ouvrir()!!
    verifO(onglets.plein() && onglets.ouvrir() == null && onglets.liste.size == Onglets.MAX, "${Onglets.MAX} onglets au plus")
    verifO(onglets.fermer(t3) && onglets.actif === t4, "fermer un onglet qui n'est pas affiché : on reste où l'on est")
    verifO(onglets.fermer() && onglets.actif === t2, "fermer l'onglet affiché : on va sur son voisin de gauche")
    val t3b = onglets.ouvrir()!!
    verifO(t3b.nom() == "Terminal 3" && onglets.liste.map { it.numero } == listOf(1, 2, 3), "un nouvel onglet reprend le plus petit numéro libre, dans l'ordre")
    onglets.fermer(t3b)
    verifO(t2.historique == listOf("ls", "pwd"), "un nouvel onglet part de l'historique de la partie (comme un nouveau bash)")

    println("2. Deux onglets indépendants")
    jeu.terrain.mkdirs()
    File(jeu.terrain, "nid").mkdirs()
    File(jeu.terrain, "nid/lit.txt").writeText("doux\n")
    onglets.choisir(t1)
    tape("cd terrain_terminagotchi/nid")
    verifO(t1.shell.virtuel() == Racine.HOME + "/terrain_terminagotchi/nid", "Terminal 1 : cd terrain_terminagotchi/nid → ${t1.shell.chemin()}")
    verifO(t2.shell.virtuel() == Racine.HOME, "Terminal 2 n'a pas bougé : ${t2.shell.chemin()}")
    onglets.choisir(t2)
    verifO(tape("pwd").trim() == Racine.HOME, "pwd dans Terminal 2 : ${Racine.HOME}")
    verifO("lit.txt" !in tape("ls"), "ls dans Terminal 2 : le camp, pas le nid")
    onglets.choisir(t1)
    verifO("lit.txt" in tape("ls"), "ls dans Terminal 1 : le nid (lit.txt)")
    onglets.choisir(t2)
    tape("cd terrain_terminagotchi")
    tape("cd -")
    verifO(t2.shell.virtuel() == Racine.HOME, "cd - dans Terminal 2 revient où était Terminal 2 (le camp), pas dans le nid de Terminal 1")
    tape("cd n_existe_pas")
    verifO(t2.shell.code == 1 && t1.shell.code == 0, "un cd raté dans Terminal 2 : code 1 là, Terminal 1 garde son code 0")
    verifO(t1.shell.virtuel().endsWith("/nid"), "Terminal 1 est toujours dans le nid")

    println("3. Un historique par onglet")
    verifO(t1.historique.takeLast(2) == listOf("cd terrain_terminagotchi/nid", "ls") &&
        "cd n_existe_pas" !in t1.historique && "cd n_existe_pas" == t2.historique.last(),
        "↑ dans Terminal 1 rappelle ses lignes à lui, ↑ dans Terminal 2 les siennes")
    verifO(jeu.historique.containsAll(listOf("cd terrain_terminagotchi/nid", "cd n_existe_pas")), "l'historique de la partie garde les lignes des deux")

    println("4. La créature mange les commandes des deux onglets ; la leçon voit le dossier de chaque onglet")
    onglets.nouvellePartie(jeu.home)
    val total = jeu.total
    onglets.choisir(t1); tape("whoami")
    onglets.choisir(t2); tape("date")
    verifO(jeu.total == total + 2 && "whoami" in jeu.vus && "date" in jeu.vus, "whoami (Terminal 1) et date (Terminal 2) : deux commandes mangées (total ${jeu.total - total})")
    jeu.xp = maxOf(jeu.xp, 10)
    onglets.choisir(t1)
    for (c in listOf("pwd", "ls", "cd ~")) tape(c)
    verifO(lecon() == ("reveil1" to 0), "« Où suis-je ? » finie dans Terminal 1 → ${lecon()}")
    onglets.choisir(t2)
    tape("cd terrain_terminagotchi")
    verifO(lecon() == ("reveil1" to 1), "cd terrain_terminagotchi dans Terminal 2 : l'étape le voit (${lecon()})")
    onglets.choisir(t1)
    tape("ls"); tape("ls")
    verifO(lecon() == ("reveil1" to 1), "ls dans Terminal 1, resté au camp : « ls dans la grande salle » ne compte pas")
    onglets.choisir(t2)
    tape("ls"); tape("ls")
    verifO(lecon() == ("reveil1" to 2), "ls dans Terminal 2, dans la grande salle : l'étape est validée (${lecon()})")

    println("5. Les commandes en attente ; Ctrl+C")
    onglets.choisir(t1)
    verifO(t1.mettreDeCote("ls") && t1.mettreDeCote("pwd", colle = true) && t2.attente.isEmpty(),
        "pendant une commande, « ls » puis « pwd » sont mis de côté dans Terminal 1 (pas dans Terminal 2)")
    val a1 = t1.prochaineAttente()
    val a2 = t1.prochaineAttente()
    verifO(a1?.ligne == "ls" && a2?.ligne == "pwd" && a2.colle && t1.prochaineAttente() == null,
        "elles repartent dans l'ordre où elles ont été tapées, chacune entière (jamais « lspwd »)")
    repeat(Onglets.MAX_ATTENTE) { t1.mettreDeCote("echo $it") }
    verifO(!t1.mettreDeCote("echo de trop") && t1.attente.size == Onglets.MAX_ATTENTE, "${Onglets.MAX_ATTENTE} lignes en attente au plus")
    t1.attente.clear()
    val sh = t1.shell
    var sortieSieste = ""
    val debut = System.currentTimeMillis()
    val fil = Thread { sortieSieste = sh.executer("sleep 15") }
    fil.start()
    Thread.sleep(800)
    verifO(sh.interrompre(), "Ctrl+C pendant `sleep 15` : la commande est arrêtée")
    fil.join(10000)
    val duree = System.currentTimeMillis() - debut
    verifO(!fil.isAlive && duree < 8000 && sh.code == 130 && "^C" in sortieSieste,
        "elle s'arrête tout de suite (${duree} ms), code 130, « ^C » affiché")
    verifO(!sh.interrompre(), "Ctrl+C sans commande en cours : rien à arrêter")
    verifO(sh.executer("echo encore").trim() == "echo encore".removePrefix("echo ") && sh.code == 0 && !sh.interrompu,
        "la commande suivante marche normalement")

    println("6. Le téléphone tourne (ou l'écran est recréé) : les onglets restent")
    run {
        val home = jeu.home
        val nid = File(home, "terrain_terminagotchi/nid").apply { mkdirs() }
        val creer = { Shell(home) }
        val a = Onglets(creer, { listOf("ls") })
        a.actif.shell.dossier = nid
        a.actif.noter("cd terrain_terminagotchi/nid")
        val b = a.ouvrir()!!
        b.shell.dossier = File(home, "terrain_terminagotchi").canonicalFile
        b.shell.precedent = nid
        b.shell.code = 2
        b.brouillon = "cat rep"
        b.noter("pwd")
        val c = a.ouvrir()!!
        a.fermer(c)                                     // il reste Terminal 1 et Terminal 2, Terminal 2 affiché
        a.choisir(b)
        val texte = a.etat()
        val r = Onglets(creer, { listOf("ls") })
        verifO(r.reprendre(texte, home), "l'état gardé se relit")
        verifO(r.liste.map { it.numero } == listOf(1, 2) && r.actif.numero == 2, "les mêmes onglets reviennent (Terminal 1, Terminal 2), Terminal 2 affiché")
        val r1 = r.liste[0]; val r2 = r.liste[1]
        verifO(r1.shell.dossier == nid.canonicalFile && r2.shell.dossier == File(home, "terrain_terminagotchi").canonicalFile,
            "chaque onglet retrouve SON dossier")
        verifO(r2.shell.precedent == nid.canonicalFile && r2.shell.code == 2 && r2.brouillon == "cat rep",
            "et son `cd -`, son code de sortie, sa ligne à moitié tapée")
        verifO(r1.historique.last() == "cd terrain_terminagotchi/nid" && r2.historique.last() == "pwd" && r1.shell !== r2.shell,
            "et son historique ↑ ↓ ; chacun son shell")
        verifO(r2.shell.executer("pwd").trim().endsWith("terrain_terminagotchi"), "pwd après la rotation : le bon dossier")
        // un dossier effacé entre-temps, ou hors du camp : retour au camp
        val tmp = File(home, "terrain_terminagotchi/tmp_efface").apply { mkdirs() }
        a.actif.shell.dossier = tmp
        val t2 = a.etat()
        tmp.delete()
        val r3 = Onglets(creer); r3.reprendre(t2, home)
        verifO(r3.actif.shell.dossier == home, "un dossier qui n'existe plus : l'onglet revient au camp")
        val dehors = org.json.JSONObject(texte)
        dehors.getJSONArray("onglets").getJSONObject(0).put("dossier", "/").put("precedent", home.parentFile!!.path)
        val r4 = Onglets(creer); r4.reprendre(dehors.toString(), home)
        verifO(r4.liste[0].shell.dossier == home && r4.liste[0].shell.precedent == null, "un dossier hors du camp (/, les coulisses) : jamais repris")
        val r5 = Onglets(creer)
        verifO(!r5.reprendre("{abîmé", home) && !r5.reprendre(null, home) && r5.liste.size == 1, "un état abîmé ou absent : un seul onglet, comme au lancement")
        val trop = org.json.JSONObject().put("actif", 9).put("onglets", org.json.JSONArray((1..7).map { org.json.JSONObject().put("n", it) }))
        val r6 = Onglets(creer); r6.reprendre(trop.toString(), home)
        verifO(r6.liste.size == Onglets.MAX && r6.actif.numero == 1, "jamais plus de ${Onglets.MAX} onglets ; un onglet affiché inconnu : le premier")
        File(home, "terrain_terminagotchi").deleteRecursively()
    }

    println("7. Une autre partie ; les textes")
    onglets.nouvellePartie(jeu.home)
    verifO(onglets.liste.all { it.shell.dossier == jeu.home && it.shell.precedent == null && it.dernierDossier == null },
        "une autre partie : chaque onglet revient au camp de base")
    for (code in listOf("fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur")) {
        Langue.definir(code)
        val textes = listOf(t("ong.nom", "n" to 2), t("ong.ouvert", "nom" to "T2", "avant" to "T1"), t("ong.ferme", "nom" to "T2"),
            t("ong.max", "max" to 4), t("ong.occupe", "nom" to "T1"), t("ong.nouveau"), t("ong.fermer", "nom" to "T2"), t("ong.aide", "max" to 4), t("ong.attente", "cmd" to "ls"), t("ong.ctrlc", "n" to 2))
        verifO(textes.none { it.startsWith("ong.") || "{" in it } && "2" in textes[0], "$code : les textes des onglets (${textes[0]})")
    }
    Langue.definir("fr")

    dossier.deleteRecursively()
    println("\n$okO réussis, $koO échoués")
    if (koO > 0) kotlin.system.exitProcess(1)
}
