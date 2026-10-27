/*
 * Test JVM : la sûreté du terminal du téléphone (Shell.kt, Racine.kt, Garde.kt), d'après les attaques de « Karim »
 * (simulation des personas avancés) :
 *   1. lire hors du camp : `ls ./../`, `head ./../sauvegarde.json`, `cd /proc/self/cwd`, `cd $HOME/..` ;
 *   2. écrire hors du camp : `echo > $HOME/../x`, `tee`, `sed -i ./../x`, `X=..; echo > $X/x`, un lien du camp vers
 *      les coulisses, la Racine « lecture seule » (chmod -R u+w), `rm -f $HOME/../sauvegarde.json`, `rm -rf $HOME/../(tout)` :
 *      refusé avant, ou remis après ; un message gentil (enfant + grands) ;
 *   3. la sauvegarde modifiée (sed -i … xp 999999) puis l'appli tuée : le sceau la refuse, la copie de secours revient ;
 *      sauvegarde abîmée : la copie de secours revient (jamais une nouvelle créature en silence) ;
 *   4. processus orphelins (`sleep 61 &`, `(while :; do :; done) &`, setsid) : arrêtés à la fin de la commande ;
 *   5. ligne trop longue : message clair ; l'horloge qui recule : la faim reste entre 0 et 100.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Securite.kt -d securite.jar
 *   java -cp <imitations>:<appli.jar>:securite.jar:kotlin-stdlib.jar SecuriteKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Garde
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Parties
import fr.terminagotchi.Racine
import fr.terminagotchi.Shell
import java.io.File

class ActifsS(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilS(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsS(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okS = 0
var koS = 0
fun verifS(c: Boolean, m: String) {
    if (c) okS++ else koS++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun vivants(motif: String): List<String> =
    ProcessBuilder("sh", "-c", "ps -eo pid,args | grep -F -- '$motif' | grep -v grep").start()
        .inputStream.bufferedReader().readText().trim().lines().filter { it.isNotBlank() }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_securite_" + System.nanoTime()).apply { mkdirs() }
    val files = File(dossier, "app").apply { mkdirs() }
    val app = AppareilS(files, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.xp = 1588
    jeu.sauver()
    jeu.terrain.mkdirs()
    File(jeu.terrain, "nid").mkdirs()
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })
    val vrai = files.canonicalPath
    val sauvegarde = Parties.fichierActif(app)
    val canari = File(files, "canari.txt").apply { writeText("app\n") }
    val dehors = File(dossier, "dehors").apply { mkdirs(); File(this, "important.txt").writeText("hôte\n") }
    fun sh(c: String): String {
        val s = try { commandes.executer(c)?.texte ?: shell.executer(c) } catch (e: Throwable) { "💥 $e" }
        verifS(vrai !in s && !s.startsWith("💥"), "« ${c.take(60)} » : ni plantage ni vrai chemin de l'appli")
        return s
    }

    println("1. Lire hors du camp")
    val r1 = sh("ls ./../")
    verifS("sauvegarde.json" !in r1 && "parties" !in r1, "`ls ./../` : le village du Terminaworld, pas le dossier de l'appli (${r1.replace("\n", " ").take(60)})")
    val r1b = sh("head -c 120 ./../sauvegarde.json")
    verifS("\"xp\"" !in r1b, "`head ./../sauvegarde.json` ne lit pas la sauvegarde")
    verifS("\"xp\"" !in sh("cat \$HOME/../sauvegarde.json") && "\"xp\"" !in sh("cat \${HOME}/../sauvegarde.json"),
        "`cat \$HOME/../sauvegarde.json` : \$HOME est le camp du Terminaworld, \$HOME/.. le village")
    sh("cd /proc/self/cwd")
    verifS(shell.virtuel().startsWith("/home") || shell.virtuel() == "/", "`cd /proc/self/cwd` ne sort pas du Terminaworld (invite ${shell.chemin()})")
    shell.dossier = jeu.home
    sh("cd \$HOME/..")
    verifS(shell.virtuel() == "/home", "`cd \$HOME/..` : le village /home (${shell.virtuel()})")
    shell.dossier = jeu.home
    verifS(sh("echo '\$HOME'").trim() == "\$HOME", "entre apostrophes, '\$HOME' reste tel quel")

    println("2. Écrire hors du camp : refusé avant, ou remis après")
    val essais = listOf(
        "echo pirate > \$HOME/../canari.txt",
        "echo pirate | tee \$HOME/../canari.txt",
        "sed -i s/app/pirate/ ./../canari.txt",
        "echo pirate >> ./../canari.txt",
        "X=..; echo pirate > \$X/canari.txt",
        "cd ..; echo pirate > canari.txt",
        "echo pirate > \"\$(dirname \"\$PWD\")/canari.txt\"",
        "X=.; echo pirate > \$X/../canari.txt",
    )
    for (c in essais) {
        canari.writeText("app\n")
        val r = sh(c)
        verifS(canari.readText() == "app\n", "`$c` : rien n'a changé hors du camp")
        verifS("Permission denied" in r || "🛡" in r || "introuvable" in r, "… et c'est expliqué (${r.lines().firstOrNull()?.take(70)})")
    }
    val r2a = sh("sed -i s/a/b/ ./../canari.txt")
    verifS("Permission denied" in r2a && "Pour les grands" in r2a, "`sed -i` hors du camp : refusé avant d'être lancé, expliqué aux enfants et aux grands")
    verifS(!File(files, "pirate.txt").exists().also { sh("echo x > \$HOME/../pirate.txt") } && !File(files, "pirate.txt").exists(),
        "un fichier ajouté dans les coulisses est enlevé")
    shell.dossier = jeu.home
    val r2 = sh("chmod -R u+w ../../etc 2>/dev/null; X=.; chmod -R u+w \$X/../racine/etc; echo pirate > \$X/../racine/etc/hostname; cat /etc/hostname")
    verifS("pirate" !in sh("cat /etc/hostname"), "la Racine reste en lecture seule (chmod -R u+w puis écriture) : ${r2.lines().firstOrNull()}")
    verifS(!File(Racine.dossier(jeu.home), "etc/hostname").canWrite(), "… et elle est reverrouillée (r--r--r--)")
    sh("ln -s ${dehors.path} lien_dehors")
    verifS(!File(jeu.home, "lien_dehors").exists() && File(dehors, "important.txt").readText() == "hôte\n",
        "un lien du camp vers l'extérieur est enlevé (le jeu n'écrira jamais à travers)")
    val rl = sh("X=.; ln -s \$X/../sauvegarde.json triche.json; echo '{}' > triche.json")
    verifS(sauvegarde.readText().contains("\"xp\":1588") && !File(jeu.home, "triche.json").exists(), "lien vers la sauvegarde + écriture : remise, lien enlevé")
    verifS("🔗" in rl || "🛡" in rl, "… et c'est expliqué (${rl.replace("\n", " ").take(90)})")
    sh("ln -s /etc regles")
    verifS(File(jeu.home, "regles").exists(), "un lien du camp vers un lieu de la Racine reste (lecture)")
    val rr = sh("echo pirate > regles/hostname")
    verifS("Permission denied" in rr && "pirate" !in sh("cat /etc/hostname"), "… mais on n'écrit pas à travers lui dans la Racine")
    sh("rm regles")
    val rs = sh("X=.; rm -f \$X/../sauvegarde.json")
    verifS("🛡" in rs && sauvegarde.isFile, "`rm -f ../sauvegarde.json` (par une variable) : la sauvegarde revient tout de suite")
    verifS("Permission denied" in sh("rm -f \$HOME/../sauvegarde.json") && sauvegarde.isFile, "`rm -f \$HOME/../sauvegarde.json` : refusé")
    val parties = File(files, "parties")
    val avantParties = parties.walkTopDown().map { it.path }.toSet()
    sh("X=.; rm -rf \$X/../*")
    verifS(sauvegarde.isFile && parties.walkTopDown().map { it.path }.toSet() == avantParties && File(Racine.dossier(jeu.home), "etc/hostname").isFile,
        "`rm -rf ../*` (par une variable) : sauvegarde, parties et Racine remises")
    verifS(jeu.home.isDirectory && shell.dossier == jeu.home, "… et le camp revient (vide : c'était dans le camp, le jeu aide à refaire la zone)")
    jeu.terrain.mkdirs(); File(jeu.terrain, "nid").mkdirs()
    sh("X=.; chmod 000 \$X/../sauvegarde.json")
    verifS(sauvegarde.canRead() && Jeu(app).xp == 1588, "`chmod 000 ../sauvegarde.json` : la sauvegarde reste lisible")
    val ecrit = sh("echo bonjour > terrain_terminagotchi/nid/note.txt; cat terrain_terminagotchi/nid/note.txt")
    verifS(ecrit.trim() == "bonjour", "écrire dans le camp marche toujours")

    println("3. La sauvegarde modifiée hors du jeu (l'appli tuée avant de la remettre)")
    jeu.sauver()
    Garde.pourTests(exiger = true)          // comme sur un téléphone : le magasin de clés existe déjà
    val bon = sauvegarde.readText()
    sauvegarde.writeText(bon.replace("\"xp\":1588", "\"xp\":999999"))
    val relu = Jeu(app)
    verifS(relu.xp == 1588, "sed sur l'xp puis redémarrage : sceau refusé, la copie de secours revient (xp ${relu.xp})")
    verifS(relu.alerteChargement == "garde.sceau" && relu.journal.any { "modifiée" in it }, "… et la créature le dit")
    sauvegarde.writeText(org.json.JSONObject(bon).apply { remove("sceau"); put("xp", 999999) }.toString())
    verifS(Jeu(app).xp == 1588, "sceau enlevé : refusé aussi (copie de secours)")
    sauvegarde.writeText("{ pas du json")
    val casse = Jeu(app)
    verifS(casse.nom == "Pixel" && casse.xp == 1588, "sauvegarde abîmée : la copie de secours revient (pas de nouvelle créature)")
    verifS(File(files, "sauvegarde.json.refusee").isFile, "… le fichier refusé est gardé à côté")
    Garde.pourTests(exiger = false)
    sauvegarde.writeText(bon)

    println("4. Les processus lancés par la commande s'arrêtent avec elle")
    val t0 = System.currentTimeMillis()
    sh("sleep 61 &")
    verifS(System.currentTimeMillis() - t0 < 5000, "`sleep 61 &` rend la main tout de suite")
    verifS(vivants("sleep 61").isEmpty(), "… et ne laisse pas d'orphelin")
    val rb = sh("(while :; do :; done) &")
    verifS(vivants("while :").isEmpty() && vivants("do :").isEmpty(), "`(while :; do :; done) &` : la boucle est arrêtée")
    verifS("🧹" in rb, "… et c'est expliqué (${rb.lines().firstOrNull()?.take(80)})")
    sh("setsid sh -c 'sleep 62' > /dev/null 2>&1 &")
    Thread.sleep(200)
    verifS(vivants("sleep 62").isEmpty(), "même échappé dans une autre session (setsid) : arrêté")
    sh("nohup sleep 63 > /dev/null 2>&1 &")
    verifS(vivants("sleep 63").isEmpty(), "nohup : arrêté aussi")

    println("5. Robustesse")
    val long = sh("echo " + "a".repeat(40000))
    verifS("trop longue" in long, "ligne de 40 000 caractères : message clair (${long.take(60)})")
    jeu.faim = 90.0
    jeu.dernierTick = System.currentTimeMillis() + 3 * 86_400_000L
    jeu.tick()
    verifS(jeu.faim in 0.0..100.0, "l'horloge recule de 3 jours : faim ${"%.0f".format(jeu.faim)} (entre 0 et 100)")
    jeu.nom = "\u001b[2J\u202ePix\u0000el"
    verifS(jeu.nom == "[2JPixel", "nom avec ESC, RLO, NUL : nettoyé (${jeu.nom})")
    jeu.nom = "Pixel"
    verifS(canari.readText() == "app\n" && File(dehors, "important.txt").readText() == "hôte\n", "à la fin : rien n'a changé hors du camp")

    println("\n$okS réussis, $koS échoués")
    dossier.deleteRecursively()
    if (koS > 0) System.exit(1)
}
