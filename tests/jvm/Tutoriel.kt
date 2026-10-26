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
 * Cause du blocage trouvée ainsi : à l'étape 3/3 (le lit), l'enfant encore « en mode mkdir » tape mkdir nid/lit.txt ;
 * lit.txt devient un DOSSIER, touch nid/lit.txt ne peut plus jamais réussir, et aucun indice ne le disait. Et
 * « touch lit.txt » dans la grande salle donnait un indice faux (« va dans le terrain » alors qu'on y est).
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
import org.json.JSONArray
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
    val faits = { p: Partie -> Histoire.faits(p.jeu) }

    println("1. Nouvelle partie, l'enfant tape tout dans l'ordre")
    var p = nouvellePartie("Pixel")
    reveil(p)
    verif(Histoire.fini(p.jeu, "reveil") && Histoire.chap(p.jeu) == "nid", "chapitre 1 fini : ${p.lecon()} niveau ${p.jeu.niveau}")
    p.suite("cd ..", "mkdir nid")
    verif(p.lecon() == ("nid0" to 2) && "(3/3)" in p.ecran() && "touch nid/lit.txt".replace(" ", "\u00a0") !in p.ecran(),
        "cd .., mkdir nid → ${p.lecon()} (3/3 à l'écran)")
    p.tape("touch nid/lit.txt")
    verif("nid0" in faits(p) && p.lecon() == ("debarras" to 0), "3/3 : le lit est posé, leçon finie, la suite démarre : ${p.lecon()}")
    verif(File(p.T, "vieille_cabane/planche_1.txt").isFile, "la vieille cabane pleine de planches est posée")
    p.tape("mkdir debarras")
    verif(p.lecon() == ("debarras" to 1), "mkdir debarras → ${p.lecon()}")
    p.tape("rm debarras")
    verif("pas un objet" in (p.jeu.indiceLecon ?: "") && "rmdir debarras" in (p.jeu.indiceLecon ?: "") && File(p.T, "debarras").isDirectory,
        "rm debarras échoue : indice « pièce, pas un objet : rmdir » (${p.jeu.indiceLecon})")
    p.tape("rmdir debarras")
    verif(!File(p.T, "debarras").exists() && p.lecon() == ("debarras" to 2), "rmdir debarras : la pièce vide est démolie → ${p.lecon()}")
    verif("depuis" in p.ecran(), "l'écran dit d'où taper rm -r vieille_cabane")
    p.tape("rmdir vieille_cabane")
    verif("broyeuse" in (p.jeu.indiceLecon ?: "") && File(p.T, "vieille_cabane").isDirectory, "rmdir sur la cabane pleine : refus expliqué (${p.jeu.indiceLecon})")
    p.tape("rm -r vieille_cabane")
    verif("debarras" in faits(p) && !File(p.T, "vieille_cabane").exists(), "rm -r : la broyeuse, leçon finie")
    suivreEcran(p) { Histoire.fini(p.jeu, "nid") }
    verif(Histoire.fini(p.jeu, "nid") && Histoire.chapitreCourant(p.jeu) == null && !File(p.T, "vieille_cabane").exists(),
        "chapitre 2 fini, la maison est libre (la cabane ne revient pas)")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")
    println(p.trace.joinToString("\n") { "     $it" })

    println("2. Le blocage du 3/3 : erreurs réalistes au lit")
    p = nouvellePartie("Mode mkdir")
    reveil(p)
    p.suite("cd ..", "mkdir nid", "mkdir nid/lit.txt")
    verif(p.lecon() == ("nid0" to 2) && "rmdir nid/lit.txt" in (p.jeu.indiceLecon ?: ""), "mkdir nid/lit.txt : indice clair (${p.jeu.indiceLecon})")
    p.tape("touch nid/lit.txt")
    verif(p.lecon() == ("nid0" to 2) && "rmdir nid/lit.txt" in (p.jeu.indiceLecon ?: "") + p.bulles(), "touch sur le dossier lit.txt : toujours l'indice")
    p.suite("rmdir nid/lit.txt", "touch nid/lit.txt")
    verif("nid0" in faits(p), "rmdir puis touch : débloqué, leçon finie")
    p = nouvellePartie("Sans chemin")
    reveil(p)
    p.suite("cd ..", "mkdir nid", "touch lit.txt")
    verif("touch nid/lit.txt" in (p.jeu.indiceLecon ?: "") && "cd ~/terrain" !in (p.jeu.indiceLecon ?: ""),
        "touch lit.txt dans la grande salle : l'indice donne la commande entière (${p.jeu.indiceLecon})")
    p.suite("cd nid", "touch nid/lit.txt")
    verif("grande salle" in (p.jeu.indiceLecon ?: ""), "touch nid/lit.txt depuis le nid : « depuis la grande salle » (${p.jeu.indiceLecon})")
    p.tape("touch lit.txt")
    verif("nid0" in faits(p), "touch lit.txt dans le nid : validé")
    p = nouvellePartie("Dans le nid")
    reveil(p)
    p.suite("cd ..", "mkdir nid", "cd nid", "mkdir lit.txt")
    verif("rmdir" in (p.jeu.indiceLecon ?: ""), "mkdir lit.txt dans le nid : indice rmdir (${p.jeu.indiceLecon})")
    p.suite("rmdir lit.txt", "touch lit.txt")
    verif("nid0" in faits(p), "débloqué")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")

    println("3. Variantes réalistes")
    p = nouvellePartie("Mauvais dossier")
    reveil(p)
    p.tape("mkdir nid")                                     // tapé dans le vestibule
    verif(p.lecon() == ("nid0" to 0), "mkdir nid dans le vestibule : on doit d'abord reculer (${p.lecon()})")
    p.tape("cd  ..  ")
    p.tape("mkdir Nid")
    verif(p.lecon() == ("nid0" to 1), "mkdir Nid : pas validé (${p.lecon()} 💡 ${p.jeu.indiceLecon})")
    p.suite("mkdir nid", "cd nid", "touch lit.txt")
    verif(p.lecon() == ("debarras" to 0), "touch lit.txt depuis le nid → ${p.lecon()}")
    p.suite("mkdir debarras", "rmdir debarras")              // dans le nid : accepté aussi
    verif(p.lecon() == ("debarras" to 2), "debarras créé puis démoli dans le nid → ${p.lecon()}")
    p.suite("cd ~/terrain_terminagotchi", "rm  -r   vieille_cabane")
    verif("debarras" in faits(p), "cd absolu, rm -r avec espaces en trop : leçon finie")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")
    p = nouvellePartie("Deja la")
    reveil(p)
    File(p.T, "nid").mkdirs()
    File(p.T, "debarras").mkdirs()
    p.tape("cd ..")
    verif(p.lecon() == ("nid0" to 2), "nid déjà là : passé tout seul (${p.lecon()})")
    p.tape("touch ~/terrain_terminagotchi/nid/lit.txt")
    verif(p.lecon() == ("debarras" to 1), "chemin absolu ; debarras déjà là → ${p.lecon()}")
    p.suite("rmdir debarras", "rm -rf vieille_cabane")
    verif("debarras" in faits(p), "rm -rf : leçon finie")
    verif(p.bloque == null, "jamais bloqué : ${p.bloque}")

    println("4. Parties : chaque nouvelle partie a son terrain, l'ancienne est rangée")
    val rangees = File(appT.filesDir, "parties").listFiles()!!.filter { it.name.startsWith("terrain_") }
    verif(rangees.size >= 2 && rangees.all { File(it, "nid").isDirectory }, "terrains rangés dans parties/ : ${rangees.map { it.name }}")
    p = nouvellePartie("Neuve")
    verif(!p.T.exists() && p.lecon() == ("t0" to 0), "la nouvelle partie démarre sans terrain, au début")
    reveil(p)
    p.suite("cd /", "cd ${p.T.path}", "mkdir nid")
    verif(p.lecon() == ("nid0" to 2), "cd absolu puis mkdir nid : ${p.lecon()}")

    println("5. Anciennes sauvegardes (v1, avant « Une pièce en trop »)")
    fun v1(nom: String, faitsV1: List<String>, etape: Int, ailes: List<String> = listOf("reveil")): Partie {
        val q = nouvellePartie(nom)
        reveil(q)
        q.suite("cd ..", "mkdir nid")
        val h = Histoire.h(q.jeu)
        h.put("v", 1).put("faits", JSONArray(faitsV1)).put("ailes", JSONArray(ailes)).put("chap", if ("nid" in ailes) JSONObject.NULL else "nid")
        q.jeu.etape = etape
        q.jeu.sauver()
        q.jeu.recharger()
        return q
    }
    p = v1("En plein lit", listOf("t0", "reveil1"), 2)
    p.tape("touch nid/lit.txt")
    verif(p.lecon() == ("debarras" to 0), "v1 en plein nid0 (3/3) : le lit finit la leçon, puis « Une pièce en trop » → ${p.lecon()}")
    p = v1("En plein repas", listOf("t0", "reveil1", "nid0"), 1)
    File(p.T, "nid/repas.txt").writeText("pomme\n")
    p.tape("ls")
    verif(p.lecon() == ("debarras" to 0) && Histoire.h(p.jeu).getJSONObject("pas").optInt("nid1", -1) == 1,
        "v1 en plein garde-manger (étape 2) : d'abord la pièce en trop, l'étape du repas est gardée → ${p.lecon()}")
    p.suite("mkdir debarras", "rmdir debarras", "rm -r vieille_cabane")
    verif(p.lecon() == ("nid1" to 1), "puis le garde-manger reprend à son étape → ${p.lecon()}")
    p = v1("Nid fini", listOf("t0", "reveil1", "nid0", "nid1"), 0, listOf("reveil", "nid"))
    p.tape("ls")
    verif(Histoire.fini(p.jeu, "nid") && "debarras" in faits(p) && Histoire.chapitreCourant(p.jeu) == null,
        "v1 chapitre 2 fini : rien à refaire (la leçon compte comme faite)")
    verif(Histoire.h(p.jeu).optInt("v") == 2, "sauvegarde passée en v2")

    println("6. Filet de sécurité : une leçon dont toutes les étapes sont faites se termine")
    p = nouvellePartie("Filet")
    reveil(p)
    p.suite("cd ..", "mkdir nid")
    p.jeu.etape = 99                                        // compteur abîmé (sauvegarde d'une autre version…)
    p.jeu.sauver(); p.jeu.recharger()
    p.tape("ls")
    verif("nid0" in faits(p) && p.lecon().first == "debarras" && "➜" in p.ecran(), "étape au-delà de la fin : leçon finie, la suite s'affiche (${p.lecon()})")
    Histoire.h(p.jeu).put("faits", JSONArray(listOf("t0", "reveil1", "nid0", "debarras", "nid1")))
    p.tape("ls")
    verif(Histoire.fini(p.jeu, "nid"), "toutes les leçons du chapitre faites : le chapitre se termine")

    println("\n$okT réussis, $koT échoués")
    System.exit(if (koT > 0) 1 else 0)
}
