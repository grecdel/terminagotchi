/*
 * Test JVM du tutoriel des constructions (« bloqué à 3/3 », retour d'un vrai téléphone) : une NOUVELLE PARTIE
 * (Parties.nouvelle, comme le menu de l'appli), puis les commandes tapées une par une, exactement comme un enfant,
 * SANS donner d'expérience en douce : pwd, ls, cd ~, la vieille porte, le nid (mkdir, touch), le garde-manger,
 * et la nouvelle leçon « une pièce en trop » (mkdir debarras, rmdir debarras, rm -r).
 *
 * Variantes réalistes : mkdir nid depuis le mauvais dossier, mkdir Nid, nid déjà là, cd relatif ou absolu, espaces en
 * trop, terrain d'une partie rangée (parties/terrain_<id>), ancienne sauvegarde (leçon nid0 sans les étapes rmdir),
 * rm debarras (refusé sur un dossier : indice « rmdir »).
 *
 * Après CHAQUE commande : si la leçon affiche n/n et que la dernière étape est faite, elle doit être finie ; l'écran
 * dit toujours la prochaine commande (➜). Même compilation que tests/jvm/Histoire.kt :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Tutoriel.kt -d tutoriel.jar
 *   java -cp <imitations>:<appli.jar>:tutoriel.jar:kotlin-stdlib.jar TutorielKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Parties
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import org.json.JSONObject
import java.io.File

class ActifsT(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilT(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsT(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okT = 0
var koT = 0
fun verif(c: Boolean, m: String) {
    if (c) okT++ else koT++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

class Partie(val app: AppareilT) {
    val jeu = Jeu(app)
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })
    val T: File get() = jeu.terrain
    val trace = mutableListOf<String>()
    var bloque: String? = null

    fun bash(cmd: String): String {
        val pb = ProcessBuilder("bash", "-c", cmd).directory(shell.dossier).redirectErrorStream(true)
        pb.environment()["HOME"] = jeu.home.absolutePath
        pb.environment()["LC_ALL"] = "C.UTF-8"
        val p = pb.start()
        val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
        p.waitFor()
        return s
    }

    fun lecon(): Pair<String?, Int> = Histoire.leconCourante(jeu)?.id to jeu.etape
    fun ecran() = jeu.texteLecon() ?: ""
    fun bulles() = (listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | ")

    /** L'enfant tape une commande ; après le tour, aucune leçon n'est « n/n faite mais pas finie ». */
    fun tape(cmd: String): String {
        val mot = cmd.trim().split(Regex("\\s+"))[0]
        var sortie = ""
        if (mot == "cd") sortie = shell.executer(cmd)
        else {
            val interne = commandes.executer(cmd)
            sortie = interne?.texte ?: bash(cmd)
        }
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
        Tour.periodique(jeu, shell.dossier)
        val c = Histoire.leconCourante(jeu)
        val ligne = "%-34s → %s %s".format(cmd, c?.id ?: Histoire.chap(jeu), c?.let { "${jeu.etape + 1}/${it.etapes.size}" } ?: "")
        trace.add(ligne)
        if (c != null && jeu.niveau >= c.niveau) {
            val e = c.etapes[jeu.etape]
            if (e.fs?.invoke(jeu) == true && bloque == null) bloque = "$ligne : étape « ${e.cmd} » déjà faite mais pas validée"
            if ("➜" !in ecran() && bloque == null) bloque = "$ligne : l'écran ne dit pas la prochaine commande"
        }
        return sortie
    }

    fun suite(vararg cmds: String) { for (c in cmds) tape(c) }
}

lateinit var appT: AppareilT

/** Une partie toute neuve, créée comme par le menu « nouvelle partie » (l'ancienne est rangée avec son terrain). */
fun nouvellePartie(nom: String): Partie {
    if (File(appT.filesDir, "sauvegarde.json").exists()) Parties.nouvelle(appT)
    val p = Partie(appT)
    p.jeu.changerLangue("fr")
    p.jeu.nom = nom
    p.jeu.module("explo").put("ouverte", true)
    p.jeu.sauver()
    return p
}

/** L'enfant lit l'écran et tape la commande montrée (➜) ; sans leçon à son niveau, il joue (ls). */
fun suivreEcran(p: Partie, max: Int = 40, fin: () -> Boolean) {
    var n = 0
    while (!fin() && n++ < max) p.tape(p.jeu.etapeCourante()?.cmd ?: "ls")
}

/** pwd, ls, cd ~, puis la vieille porte et l'œuf : comme l'enfant, sans expérience offerte. */
fun reveil(p: Partie) {
    p.suite("pwd", "ls", "cd ~")
    suivreEcran(p) { Histoire.chap(p.jeu) == "nid" }
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_tutoriel_" + System.nanoTime()).apply { mkdirs() }
    appT = AppareilT(dossier, assets)
    Langue.init(appT)
    Langue.definir("fr")

    println("1. Nouvelle partie, l'enfant tape tout dans l'ordre")
    var p = nouvellePartie("Pixel")
    reveil(p)
    verif(Histoire.fini(p.jeu, "reveil") && Histoire.chap(p.jeu) == "nid", "chapitre 1 fini : ${p.lecon()} niveau ${p.jeu.niveau}")
    p.suite("cd ..", "mkdir nid")
    verif(p.lecon() == ("nid0" to 2), "cd .., mkdir nid → ${p.lecon()}")
    p.tape("touch nid/lit.txt")
    verif("nid0" !in Histoire.faits(p.jeu) && p.lecon() == ("nid0" to 3), "le lit est posé, la pièce en trop arrive : ${p.lecon()}")
    p.tape("mkdir debarras")
    verif(p.lecon() == ("nid0" to 4), "mkdir debarras → ${p.lecon()}")
    p.tape("rm debarras")
    verif("rmdir" in (p.jeu.indiceLecon ?: "") && File(p.T, "debarras").isDirectory, "rm debarras échoue : indice « rmdir » (${p.jeu.indiceLecon})")
    p.tape("rmdir debarras")
    verif(!File(p.T, "debarras").exists() && p.lecon() == ("nid0" to 5), "rmdir debarras : la pièce vide est démolie → ${p.lecon()}")
    p.suite("mkdir -p cabane/planche", "rm -r cabane")
    verif("nid0" in Histoire.faits(p.jeu) && "Bâtisseur" in p.jeu.skills, "rm -r cabane : la broyeuse, leçon finie (Bâtisseur)")
    var n = 0
    while (p.jeu.niveau < 4 && n++ < 10) p.tape("ls")
    p.suite("echo pomme > nid/repas.txt", "cat nid/repas.txt")
    verif(Histoire.fini(p.jeu, "nid") && Histoire.chapitreCourant(p.jeu) == null, "chapitre 2 fini, la maison est libre")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")
    println(p.trace.joinToString("\n") { "     $it" })

    println("2. Variantes réalistes")
    p = nouvellePartie("Mauvais dossier")
    reveil(p)
    p.tape("mkdir nid")                                     // tapé dans le vestibule
    verif(p.lecon() == ("nid0" to 0), "mkdir nid dans le vestibule : on doit d'abord reculer (${p.lecon()})")
    p.tape("cd ..")
    p.tape("mkdir Nid")
    verif(p.lecon().first == "nid0" && p.lecon().second == 1 && "nid" in (p.jeu.indiceLecon ?: "") + p.bulles(),
        "mkdir Nid : pas validé, indice (${p.jeu.indiceLecon})")
    p.tape("mkdir nid")
    verif(p.lecon() == ("nid0" to 2), "mkdir nid → ${p.lecon()}")
    p.tape("cd nid")
    p.tape("touch lit.txt")
    verif(p.lecon() == ("nid0" to 3), "touch lit.txt depuis le nid : le lit est dans le nid → ${p.lecon()}")
    p.tape("mkdir debarras")                                // dans le nid : accepté aussi
    p.tape("rmdir debarras")
    verif(p.lecon() == ("nid0" to 5), "debarras créé puis démoli dans le nid → ${p.lecon()}")
    p.suite("cd ~/terrain_terminagotchi", "mkdir cabane", "touch cabane/planche.txt", "rm  -r   cabane")
    verif("nid0" in Histoire.faits(p.jeu), "cd absolu, rm -r avec espaces en trop : leçon finie")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")

    p = nouvellePartie("Nid deja la")
    reveil(p)
    File(p.T, "nid").mkdirs()                               // le nid existe déjà (ancienne partie, autre essai…)
    p.suite("cd  ..  ")
    verif(p.lecon() == ("nid0" to 3) || p.lecon() == ("nid0" to 2), "cd .. avec espaces, nid déjà là : ${p.lecon()}")
    p.tape("touch ~/terrain_terminagotchi/nid/lit.txt")
    verif(p.lecon() == ("nid0" to 3), "touch en chemin absolu → ${p.lecon()}")
    File(p.T, "debarras").mkdirs()                          // debarras déjà là
    p.tape("ls")
    p.tape("rmdir debarras")
    verif(p.lecon() == ("nid0" to 5) || p.lecon() == ("nid0" to 4), "debarras déjà là puis rmdir : ${p.lecon()}")
    if (p.lecon() == ("nid0" to 4)) p.suite("mkdir debarras", "rmdir debarras")
    p.tape("rm -r cabane")
    verif(p.lecon() == ("nid0" to 5), "rm -r d'une pièce qui n'existe pas : rien de validé (${p.lecon()})")
    p.suite("mkdir cabane", "rm -rf cabane")
    verif("nid0" in Histoire.faits(p.jeu), "rm -rf : leçon finie")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")

    println("3. Parties : chaque nouvelle partie a son terrain, l'ancienne est rangée")
    val rangees = File(appT.filesDir, "parties").listFiles()!!.filter { it.name.startsWith("terrain_") }
    verif(rangees.size >= 2 && rangees.all { File(it, "nid").isDirectory }, "terrains rangés dans parties/ : ${rangees.map { it.name }}")
    p = nouvellePartie("Neuve")
    verif(!p.T.exists() && p.lecon() == ("t0" to 0), "la nouvelle partie démarre sans terrain, au début")
    reveil(p)
    p.suite("cd /", "cd ${p.T.path}", "mkdir nid")
    verif(p.lecon() == ("nid0" to 2), "cd absolu puis mkdir nid : ${p.lecon()}")

    println("4. Ancienne sauvegarde : nid0 commencé avant les étapes rmdir")
    p = nouvellePartie("Ancienne")
    reveil(p)
    p.suite("cd ..", "mkdir nid")
    val h = Histoire.h(p.jeu)
    h.put("v", 1)                                           // une sauvegarde d'avant : le lit était la 3e et dernière étape
    p.jeu.etape = 2
    p.jeu.sauver()
    p.jeu.recharger()
    p.tape("touch nid/lit.txt")
    verif(p.lecon() == ("nid0" to 3), "v1, étape 3/3 (le lit) : la suite (pièce en trop) s'affiche → ${p.lecon()}")
    p = nouvellePartie("Ancienne finie")
    reveil(p)
    p.suite("cd ..", "mkdir nid", "touch nid/lit.txt")
    Histoire.h(p.jeu).put("v", 1)
    Histoire.h(p.jeu).put("faits", org.json.JSONArray(listOf("t0", "reveil1", "nid0")))
    p.jeu.etape = 0
    p.jeu.sauver()
    p.jeu.recharger()
    p.tape("ls")
    verif(p.lecon().first == "nid1", "v1, nid0 déjà finie : on ne la refait pas → ${p.lecon()}")

    println("5. Filet de sécurité : une leçon dont toutes les étapes sont faites se termine")
    p = nouvellePartie("Filet")
    reveil(p)
    p.suite("cd ..", "mkdir nid", "touch nid/lit.txt", "mkdir debarras", "rmdir debarras")
    p.jeu.etape = 99                                        // compteur abîmé (sauvegarde, autre version…)
    p.tape("ls")
    verif(p.lecon().first == "nid0" && p.jeu.etape in 0..5 && "➜" in p.ecran(), "étape hors limites : ramenée dans la leçon (${p.lecon()})")
    p.jeu.etape = 5
    File(p.T, "cabane").mkdirs()
    p.tape("rm -r cabane")
    verif("nid0" in Histoire.faits(p.jeu) && p.lecon().first == "nid1", "dernière étape faite : leçon finie, la suite démarre")


    println("6. Erreurs réalistes au lit (étape 3)")
    for (essais in listOf(listOf("mkdir nid/lit.txt", "touch nid/lit.txt"), listOf("touch lit.txt", "cd ~/terrain_terminagotchi", "touch lit.txt"),
            listOf("cd nid", "mkdir lit.txt", "touch lit.txt"), listOf("cd nid", "touch nid/lit.txt"))) {
        p = nouvellePartie("Lit")
        reveil(p)
        p.suite("cd ..", "mkdir nid")
        for (c in essais) { p.tape(c); println("     $c → ${p.lecon()} 💡 ${p.jeu.indiceLecon} | ${p.bulles().take(160)}") }
    }
    println("\n$okT réussis, $koT échoués")
    System.exit(if (koT > 0) 1 else 0)
}
