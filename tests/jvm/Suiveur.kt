/*
 * Test JVM « l'élève qui suit les consignes » (portage de pc/outils/sim_suiveur.py), SANS aucune triche sur l'XP :
 * une NOUVELLE PARTIE, puis l'enfant tape exactement ce que l'écran affiche (➜ la commande de l'étape ; si la leçon
 * attend un niveau, une commande pas encore goûtée), et entre dans les ailes pour les choisir (cd ~/terrain…/<lieu>).
 * Les commandes passent par Commandes.kt (intégrées) ou Shell.kt (le shell de l'appli, dans le Terminaworld simulé de
 * Racine.kt : `cd /`, `ls /bin`, `cat /etc/hostname`), puis le tour du jeu.
 *
 * Vérifie (docs/programme.md §3) : les 10 chapitres finis sans blocage ; aucune commande « de remplissage » après le
 * réveil (G-04) ; l'exploration ne s'ouvre qu'après la mini-leçon des passages secrets (ls -a, G-05) ; les épreuves
 * des dressages qui arrivent n'exigent que des notions rencontrées (G-06) ; répéter une commande ne donne plus d'XP ;
 * « Voyage jusqu'à la Racine » et « Les lieux du gardien » faits dans le Terminaworld simulé, sans rien écrire dans
 * la Racine (G-33) ; chaque étape montrée a sa version « pour les grands » (G-32).
 * Les monstres qui apparaissent sont laissés de côté (abandon) : on mesure l'histoire.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Suiveur.kt -d suiveur.jar
 *   java -cp <imitations>:<appli.jar>:suiveur.jar:kotlin-stdlib.jar SuiveurKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Dressage
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Racine
import fr.terminagotchi.Maison
import fr.terminagotchi.Regles
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Vrai
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

/** Les commandes simples que l'enfant connaît pour nourrir l'œuf (comme les idées « J'ai encore faim » du PC). */
val REPAS = listOf("date", "whoami", "pwd", "ls", "echo coucou", "uptime", "hostname", "uname", "id", "df")

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_suiveur_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilS(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.sauver()
    val shell = Shell(jeu.home)
    val racineAvant = Racine.dossier(jeu.home).walkTopDown().filter { it.name != "terminaworld.log" }
        .associate { it.path to (if (it.isFile) it.readText() else "/") }
    val sansGrands = mutableListOf<String>()
    val sansVrai = mutableListOf<String>()
    val commandes = Commandes(app, jeu, { shell.dossier })
    var sortie = ""
    var code = 0

    fun tape(cmd: String) {
        val mot = cmd.trim().split(Regex("\\s+"))[0]
        if (mot == "cd") { val s = shell.executer(cmd); code = shell.code; if (code != 0) sortie = s }
        else {
            // le vrai shell de l'appli (Shell.kt), dans le Terminaworld simulé (Racine.kt) : / = la Racine, ~ = /home/explorateur
            val interne = commandes.executer(cmd)
            sortie = interne?.texte ?: shell.executer(cmd)
            code = if (interne != null) 0 else shell.code
            // sous la JVM, le shell est celui de l'ordinateur : les commandes propres au téléphone n'y sont pas (artefact)
            if (code == 127 && mot in setOf("getprop", "settings", "dumpsys", "cmd", "am", "pm")) code = 0
        }
        // « edite » ouvre l'éditeur de l'appli : l'enfant y change une ligne et enregistre (ce que fait l'écran d'édition)
        Regex("^edite\\s+(\\S+)").find(cmd.trim())?.let { m ->
            val f = File(shell.dossier, m.groupValues[1])
            if (f.isFile) f.writeText(if (f.name == "reglages.txt") f.readText().replace("vitesse = 4", "vitesse = 6")
                else f.readText().replaceFirst(".", "#"))
        }
        // le code de sortie est passé comme le fait l'écran (G-34 : une commande ratée ne valide rien)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier, code = code)
        Tour.periodique(jeu, shell.dossier)
    }
    val fausses = mutableListOf<String>()
    val echecsMontres = mutableListOf<String>()

    val stats = linkedMapOf<String, Int>()
    val remplissage = linkedMapOf<String, Int>()
    val trace = mutableListOf<String>()
    var bloque: String? = null
    var exploAvantSecrets: Boolean? = null
    val epreuvesInconnues = mutableSetOf<String>()
    var dressages = 0
    var suivi: Pair<String, Int>? = null
    val aile = Regex("(cd ~/terrain_terminagotchi[^\\s`)]*)")

    for (tour in 0 until 900) {
        // un monstre arrive : ses épreuves ne demandent que des notions déjà rencontrées (G-06), puis on le laisse
        if (exploAvantSecrets == null && jeu.module("explo").optBoolean("ouverte"))
            exploAvantSecrets = "secrets" !in Histoire.faits(jeu)
        jeu.module("dressage").optJSONObject("en_cours")?.let { d ->
            dressages++
            val notions = Dressage.rencontrees(jeu)
            val t = d.getJSONArray("taches")
            for (i in 0 until t.length()) if (!Dressage.connue(t.getString(i), notions)) epreuvesInconnues += t.getString(i)
            Dressage.abandonner(jeu)
        }
        val c = Histoire.leconCourante(jeu)
        if (c == null) {
            if (Histoire.fini(jeu, "coeur") || Histoire.chap(jeu) in listOf("reveil", "nid")) break
            val reste = Histoire.AILES.filter { !Histoire.fini(jeu, it) }
            val cid = if (reste.isEmpty()) "coeur" else reste[0]
            if (!Histoire.ouvert(jeu, cid)) { bloque = "aile $cid fermée"; break }
            tape("cd ~/terrain_terminagotchi/" + Histoire.PAR_CHAP[cid]!!.piece)
            if (Histoire.leconCourante(jeu) == null) { bloque = "entrer dans $cid ne la choisit pas"; break }
            continue
        }
        val chap = c.chap.id
        val cmd: String
        if (jeu.niveau < c.niveau) {
            cmd = REPAS.firstOrNull { Regles.premierMot(it) !in jeu.vus } ?: REPAS[0]
            remplissage[chap] = (remplissage[chap] ?: 0) + 1
        } else {
            val e = c.etapes[jeu.etape]
            if ("🧑 " !in (jeu.texteLecon() ?: "")) sansGrands += "${c.id}.${jeu.etape}"
            if ("💻" !in (jeu.texteLecon() ?: "") && Vrai.ligne(e.cmd) != null) sansVrai += "${c.id}.${jeu.etape}"   // G-10
            val vise = if (e.cmd.startsWith("echo ?")) e.cmd.replaceFirst("?", sortie.trim().split(Regex("\\s+")).lastOrNull() ?: "0")
                else e.cmd
            val m = aile.find((jeu.indiceLecon ?: "") + " " + (jeu.texteLecon() ?: "").lines().filter { "📁" in it }.joinToString(" "))
            val ici = (c.id to jeu.etape)
            if (m != null && !vise.startsWith("cd ") && suivi != ici &&
                File(m.groupValues[1].replace("~", jeu.home.absolutePath)).canonicalPath != shell.dossier.canonicalPath) {
                suivi = ici                                          // l'écran dit d'où la taper : il y va d'abord
                tape(m.groupValues[1])
                continue
            }
            cmd = vise
        }
        stats[chap] = (stats[chap] ?: 0) + 1
        trace += "$chap ${c.id} ${jeu.etape} $cmd"
        if (trace.size >= 4 && trace.takeLast(4).toSet().size == 1) {
            bloque = trace.last() + " (dossier ${shell.dossier}, indice ${jeu.indiceLecon})"
            break
        }
        val avantPas = Histoire.leconCourante(jeu)?.let { it.id to jeu.etape }
        tape(cmd)
        val so = sortie.lowercase()
        if (jeu.niveau >= c.niveau && ("no such file" in so || "cannot open" in so || "introuvable" in so))
            echecsMontres += "${avantPas} « $cmd » dans ${shell.virtuel()}"       // G-34 : la commande montrée échoue là
        val apresPas = Histoire.leconCourante(jeu)?.let { it.id to jeu.etape }
        if (avantPas != null && apresPas != avantPas && code != 0 &&
            c.etapes.getOrNull(avantPas.second)?.let { it.echoue || it.reseau } != true)
            fausses += "${avantPas} « $cmd » (code $code)"                         // G-34 : bravo pour une commande ratée
    }
    println("chapitres finis : ${Histoire.ailes(jeu)} · niveau ${jeu.niveau} · xp ${jeu.xp}")
    for ((k, v) in stats) println("   %-14s commandes %4d   dont remplissage %4d".format(k, v, remplissage[k] ?: 0))
    println("1. Le parcours complet, sans triche")
    for (cid in listOf("reveil", "nid", "grenier", "cave", "bibliotheque", "machines", "dortoir", "atelier", "tour", "coeur"))
        verifS(Histoire.fini(jeu, cid), "chapitre ${Histoire.PAR_CHAP[cid]!!.n} ($cid) fini")
    verifS(bloque == null, "aucun blocage (${bloque ?: "rien"})")
    verifS(remplissage.filterKeys { it != "reveil" }.values.sum() == 0, "aucune commande de remplissage après le réveil (G-04) : $remplissage")
    verifS((remplissage["reveil"] ?: 0) <= 4, "l'œuf : au plus 4 premières commandes (${remplissage["reveil"] ?: 0})")
    verifS(stats.values.sum() < 200, "parcours guidé en ${stats.values.sum()} commandes")
    println("1 bis. Validé sur le résultat (G-34)")
    verifS(fausses.isEmpty(), "aucune étape validée par une commande qui a échoué $fausses")
    verifS(echecsMontres.isEmpty(), "aucune commande montrée qui échoue là où l'enfant est $echecsMontres")
    println("2. ls -a avant les monstres (G-05), dressages (G-06)")
    verifS(exploAvantSecrets == false, "l'exploration ne s'ouvre qu'après la leçon des passages secrets")
    verifS(dressages >= 1 && epreuvesInconnues.isEmpty(), "$dressages dressage(s) en route : aucune épreuve aux notions inconnues $epreuvesInconnues")
    println("3. Le Terminaworld simulé (G-33), la version des grands (G-32)")
    val fa = Histoire.faits(jeu)
    verifS("racine" in fa && "gardien" in fa && fa.indexOf("racine") < fa.indexOf("nid0"),
        "« Voyage jusqu'à la Racine » au chapitre 1, « Les lieux du gardien » à la cave")
    verifS(trace.filter { " racine " in it }.map { it.substringAfterLast(" racine ").substringAfter(' ') } ==
        listOf("cd /", "ls", "pwd", "cd ~", "cd ${Racine.HOME}/terrain_terminagotchi/vestibule"),
        "la Racine : cd /, ls, pwd, cd ~, chemin absolu (${trace.filter { " racine " in it }})")
    val vus = Maison.monde(jeu).filter { it.genre == "systeme" && !it.brume }.mapNotNull { it.lieu }.toSet()
    verifS(vus.containsAll(listOf("regles", "armurerie", "archives")), "sur la carte : salle des règles, armurerie, archives dévoilées $vus")
    val racineApres = Racine.dossier(jeu.home).walkTopDown().filter { it.name != "terminaworld.log" }
        .associate { it.path to (if (it.isFile) it.readText() else "/") }
    verifS(racineApres == racineAvant, "rien n'a été écrit dans la Racine simulée (lecture seule)")
    verifS(sansGrands.isEmpty(), "chaque étape montrée a sa version des grands $sansGrands")
    verifS(sansVrai.isEmpty(), "chaque étape montrée a sa ligne « 💻 Dans un vrai terminal… » $sansVrai")
    println("4. Anti-remplissage")
    tape("date")
    val avant = jeu.xp
    repeat(5) { tape("date") }
    verifS(jeu.xp == avant, "5 × date : XP $avant → ${jeu.xp} (aucune XP pour la répétition)")
    println("\n$okS réussis, $koS échoués")
    if (koS > 0) println(trace.takeLast(15).joinToString("\n") { "     $it" })
    System.exit(if (koS > 0) 1 else 0)
}
