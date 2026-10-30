/*
 * Non-régression (Android, JVM hors téléphone) des problèmes trouvés par les simulations de joueurs, 2e passage
 * (docs/simulations/rapport_v2.md) :
 *   C1. chapitre 2, « Remonte d'un cran : cd .. » : depuis le camp, `aide` ne dit plus « c'est le bon endroit » ;
 *       l'indice et la commande montrée mènent d'abord au vestibule ; depuis le vestibule, `cd ..` valide ;
 *   C3. « Le tuyau » (chapitre 5) : les étapes de courses.txt se tapent dans la bibliothèque (un repaire ailleurs ne
 *       les valide plus) ; `cat courses.txt | grep …` sans résultat → « aucune ligne ne contient … » ;
 *   C4. chapitre 8 : `>> ~/tgrc` (sans le point) ne valide pas l'étape ; `>> ~/.tgrc` la valide ;
 *   I4. la ligne « 💻 Dans un vrai terminal… » ne ment plus pour les commandes de l'appli (doom, edite, getprop…).
 *
 * Même mise en route que RetoursEnfants.kt (vraies commandes avec bash, « cd » par Shell.kt, Tour.apresCommande) ;
 * se lance SANS être root :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/SimulationsV2.kt -d simv2.jar
 *   java -cp <imitations>:<appli.jar>:simv2.jar:kotlin-stdlib.jar SimulationsV2Kt app/src/main/assets
 */
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Racine
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
import fr.terminagotchi.Vrai
import java.io.File

class ActifsV2(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilV2(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsV2(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okV = 0
var koV = 0

fun verifierV(c: Boolean, m: String) {
    if (c) okV++ else koV++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuV: Jeu
lateinit var shellV: Shell
val TV: File get() = jeuV.terrain

/** Une commande tapée dans le terminal de l'appli (« cd » par Shell.kt, le reste avec bash), puis le tour du jeu. */
fun tapeV(cmd: String, ou: File? = null) {
    if (ou != null) shellV.dossier = ou
    if (!shellV.dossier.isDirectory) shellV.dossier = jeuV.home
    var code: Int? = 0
    if (cmd.trim().split(" ")[0] == "cd") { shellV.executer(cmd); code = shellV.code }
    else {
        val pb = ProcessBuilder("bash", "-c", cmd).directory(shellV.dossier).redirectErrorStream(true)
        pb.environment()["HOME"] = jeuV.home.absolutePath
        val p = pb.start()
        p.inputStream.readBytes()
        code = p.waitFor()
        if (code == 127) code = null
    }
    Tour.apresCommande(jeuV, cmd, colle = false, rappel = false, hasard = false, cwd = shellV.dossier, code = code)
}

fun niveauV(n: Int) { jeuV.xp = maxOf(jeuV.xp, 10 * (n - 1) * (n - 1)) }
fun lecV(): Pair<String?, Int> = Histoire.leconCourante(jeuV)?.id to jeuV.etape

/** Les leçons d'un chapitre faites jusqu'à `lecon` (exclue) : on commence directement là. */
fun allerA(chap: String, lecon: String) {
    Histoire.choisir(jeuV, chap, dit = false)
    val faits = Histoire.h(jeuV).getJSONArray("faits")
    val c = Histoire.CHAPITRES.first { it.id == chap }
    for (l in c.lecons.takeWhile { it != lecon }) if (l !in Histoire.faits(jeuV)) faits.put(l)
    jeuV.etape = 0
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_simv2_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilV2(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuV = Jeu(app)
    jeuV.changerLangue("fr")
    jeuV.nom = "Pixel"
    shellV = Shell(jeuV.home)
    jeuV.module("explo").put("ouverte", true)

    niveauV(2)
    for (c in listOf("pwd", "ls", "cd ~", "cd terrain_terminagotchi", "ls", "cd vestibule", "ls")) tapeV(c)
    for (c in listOf("cd /", "ls", "pwd", "cd ~", "cd ${Racine.HOME}/terrain_terminagotchi/vestibule")) tapeV(c)
    niveauV(3)

    println("C1. Chapitre 2 : remonter d'un cran jusqu'au carrefour")
    verifierV(lecV() == ("nid0" to 0), "étape « cd .. » : ${lecV()}")
    tapeV("cd ~")
    var a = Vert.sansMarques(Histoire.aideLecon(jeuV))
    verifierV("C'est le bon endroit" !in a && "terrain_terminagotchi/vestibule" in a, "depuis le camp, aide mène au vestibule : $a")
    tapeV("cd ..")
    verifierV(lecV() == ("nid0" to 0) && "cd ~/terrain_terminagotchi/vestibule" in (jeuV.indiceLecon ?: ""),
        "cd .. depuis le camp : l'indice dit de partir du vestibule (${jeuV.indiceLecon})")
    a = Vert.sansMarques(Histoire.aideLecon(jeuV))
    verifierV("C'est le bon endroit" !in a, "au village non plus, ce n'est pas « le bon endroit »")
    tapeV("cd ~/terrain_terminagotchi/vestibule")
    verifierV("C'est le bon endroit" in Vert.sansMarques(Histoire.aideLecon(jeuV)), "au vestibule : c'est le bon endroit")
    tapeV("cd ..")
    verifierV(lecV() == ("nid0" to 1), "cd .. depuis le vestibule : le carrefour, étape suivante (${lecV()})")
    for (c in listOf("mkdir nid", "touch nid/lit.txt", "mkdir debarras", "rmdir debarras", "rm -r vieille_cabane")) tapeV(c, TV)
    niveauV(4)
    for (c in listOf("echo pomme > nid/repas.txt", "cat nid/repas.txt", "ls -a", "cat .mot_secret.txt")) tapeV(c, TV)
    verifierV(Histoire.fini(jeuV, "nid"), "chapitre 2 fini")

    println("C3. Le tuyau : la liste de courses dans la bibliothèque")
    niveauV(10)
    val biblio = File(TV, "bibliotheque")
    allerA("bibliotheque", "tuyaux0")
    verifierV(lecV() == ("tuyaux0" to 0), "leçon « Le tuyau » : ${lecV()}")
    tapeV("cd ~/terrain_terminagotchi/bibliotheque")
    tapeV("ls | wc -l")
    File(TV, "grenier/repaire_test").mkdirs()
    tapeV("cd ~/terrain_terminagotchi/grenier/repaire_test")        // un dressage l'a emmené dans un repaire
    tapeV("echo banane > courses.txt")
    verifierV(lecV() == ("tuyaux0" to 1), "courses.txt créé dans un repaire : l'étape n'est pas validée (${lecV()})")
    verifierV("bibliotheque" in Vert.sansMarques(jeuV.texteLecon() ?: ""), "la leçon dit d'aller dans la bibliothèque")
    tapeV("cd ~/terrain_terminagotchi/bibliotheque")
    tapeV("echo banane > courses.txt")
    verifierV(lecV() == ("tuyaux0" to 2), "courses.txt dans la bibliothèque : réussi")
    tapeV("cd ~/terrain_terminagotchi/grenier/repaire_test")
    tapeV("echo pomme >> courses.txt")
    verifierV(lecV() == ("tuyaux0" to 2), "echo pomme >> courses.txt dans le repaire : pas validé")
    tapeV("cd ~/terrain_terminagotchi/bibliotheque")
    for (c in listOf("echo pomme >> courses.txt", "echo cerise >> courses.txt", "sort courses.txt")) tapeV(c, biblio)
    verifierV(lecV() == ("tuyaux1" to 0), "pomme, cerise, sort dans la bibliothèque : leçon suivante (${lecV()})")
    tapeV("cat courses.txt | grep fraise", biblio)
    val ind = Vert.sansMarques(jeuV.indiceLecon ?: "")
    verifierV(lecV() == ("tuyaux1" to 0) && "Aucune ligne" in ind && "cat courses.txt" in ind && "erreur" !in ind,
        "grep sans résultat : indice clair ($ind)")
    tapeV("cat courses.txt | grep pomme", biblio)
    verifierV(lecV() == ("tuyaux1" to 1), "cat courses.txt | grep pomme : réussi")

    println("C4. ~/.tgrc avec le point")
    allerA("atelier", "scripts1")
    File(TV, "nid/miam.sh").writeText("echo \"Miam !\"\n")
    verifierV(lecV() == ("scripts1" to 0), "leçon « Inventeur » : ${lecV()}")
    tapeV("echo 'miam() { echo \"Miam !\"; }' >> ~/tgrc")
    verifierV(lecV() == ("scripts1" to 0), "~/tgrc (sans le point) : l'étape n'est pas validée")
    tapeV("echo 'miam() { echo \"Miam !\"; }' >> ~/.tgrc")
    verifierV(lecV() == ("scripts1" to 1), "~/.tgrc : réussi (${lecV()})")

    println("I4. « 💻 Dans un vrai terminal »")
    verifierV(Vrai.ligne("doom") == null && Vrai.ligne("getprop ro.product.model") == null, "doom, getprop : pas de ligne 💻")
    verifierV("nano carte.txt" in (Vrai.ligne("edite carte.txt") ?: ""), "edite → nano : ${Vrai.ligne("edite carte.txt")}")
    verifierV(".bashrc" in (Vrai.ligne("echo 'x' >> ~/.tgrc") ?: ""), "~/.tgrc → ~/.bashrc")
    verifierV("\$HOME/terrain" in (Vrai.ligne("cd ${Racine.HOME}/terrain_terminagotchi/vestibule") ?: ""), "/home/explorateur → \$HOME")
    verifierV("marche pareil" in (Vrai.ligne("ls -l") ?: ""), "ls -l : marche pareil")

    println("\n$okV réussis, $koV ratés")
    kotlin.system.exitProcess(if (koV == 0) 0 else 1)
}
