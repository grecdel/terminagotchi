/*
 * Test JVM : le Terminaworld = tout le système de fichiers, SIMULÉ dans le terminal du téléphone (Racine.kt, Shell.kt),
 * la carte qui part de la Racine (Maison.monde), et la version « pour les grands » de chaque étape (G-32).
 *
 *   - `pwd` au camp de base : /home/explorateur ; `cd /`, `ls`, `pwd` : la Racine et ses lieux ; `cd ~` : retour ;
 *     `cd ..` remonte au village puis à la Racine (et pas plus haut) ; chemins absolus et relatifs ;
 *   - la salle des règles (`cat /etc/hostname`), l'armurerie (`ls /bin`, avec un tuyau), les archives, /dev/null ;
 *   - lecture seule : mkdir, touch, rm, mv, chmod, > vers un lieu du système sont refusés (Permission denied, expliqué),
 *     rien n'est créé ni modifié ; écrire dans la zone d'aventure (ou copier depuis /etc vers elle) marche ;
 *   - la sortie ne montre jamais le vrai dossier de l'appli ;
 *   - la carte : la Racine en haut, les lieux du système dans la brume tant qu'ils ne sont pas visités, le chemin
 *     jusqu'au camp et à la zone d'aventure, ◉ sur le lieu visité, le panneau « Racine → … » ;
 *   - chaque étape de chaque chapitre a sa version des grands, dans les 14 langues ; les options aussi (palier 0).
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Racine.kt -d racine.jar
 *   java -cp <imitations>:<appli.jar>:racine.jar:kotlin-stdlib.jar RacineKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Explique
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Racine
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import java.io.File

class ActifsR(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilR(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsR(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okR = 0
var koR = 0
fun verifR(c: Boolean, m: String) {
    if (c) okR++ else koR++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Une photo de la Racine simulée : chemin → contenu (pour vérifier que rien n'y change). */
fun photo(d: File): Map<String, String> =
    d.walkTopDown().associate { it.path.removePrefix(d.path) to (if (it.isFile) it.readText() else "/") }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_racine_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilR(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    jeu.sauver()
    jeu.terrain.mkdirs()
    File(jeu.terrain, "vestibule").mkdirs()
    val shell = Shell(jeu.home)
    shell.journal = { jeu.journal.toList() }
    jeu.log("Pixel est sorti de l'œuf")
    val commandes = Commandes(app, jeu, { shell.dossier })
    val vrai = jeu.home.parentFile.path            // le vrai dossier de l'appli : jamais montré
    fun tape(cmd: String): String {
        val s = commandes.executer(cmd)?.texte ?: shell.executer(cmd)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
        verifR(vrai !in s, "« $cmd » ne montre pas le vrai dossier de l'appli")
        return s
    }

    println("1. Le camp de base et la Racine")
    verifR(tape("pwd") == Racine.HOME, "pwd au camp de base : ${Racine.HOME}")
    verifR(shell.chemin() == "~", "l'invite au camp : ~")
    tape("cd /")
    verifR(shell.chemin() == "/" && tape("pwd") == "/", "cd / : la Racine, pwd = /")
    val ls = tape("ls").lines().map { it.trim() }.toSet()
    verifR(ls.containsAll(listOf("bin", "dev", "etc", "home", "proc", "tmp", "usr", "var")), "ls à la Racine : bin dev etc home proc tmp usr var ($ls)")
    verifR(tape("ls /home").trim() == Racine.NOM, "ls /home : le village, avec ton camp (${Racine.NOM})")
    tape("cd ..")
    verifR(tape("pwd") == "/", "cd .. à la Racine : on reste à la Racine")
    tape("cd ~")
    verifR(shell.dossier.canonicalPath == jeu.home.canonicalPath && shell.chemin() == "~", "cd ~ : retour au camp de base (le dossier de l'appli)")
    tape("cd ..")
    verifR(tape("pwd") == "/home" && shell.chemin() == "/home", "cd .. depuis le camp : le village /home")
    tape("cd ..")
    verifR(tape("pwd") == "/", "cd .. depuis le village : la Racine")
    tape("cd ${Racine.HOME}/terrain_terminagotchi/vestibule")
    verifR(shell.dossier.canonicalPath == File(jeu.terrain, "vestibule").canonicalPath, "chemin absolu complet : /home/explorateur/terrain_terminagotchi/vestibule")
    verifR(tape("pwd") == "${Racine.HOME}/terrain_terminagotchi/vestibule" && shell.chemin() == "~/terrain_terminagotchi/vestibule",
        "pwd dans la zone d'aventure : le chemin complet depuis la Racine")
    tape("cd ../../..")
    verifR(tape("pwd") == "/home", "chemin relatif qui remonte : ../../.. depuis le vestibule = /home")
    tape("cd ~")
    verifR(tape("ls ..").trim() == Racine.NOM, "ls .. depuis le camp : le village")
    verifR(tape("echo ~").trim() == Racine.HOME, "echo ~ : ${Racine.HOME}")

    println("2. Les lieux du système (lecture seule)")
    verifR(tape("cat /etc/hostname").trim() == "terminaworld", "cat /etc/hostname : le nom du monde")
    val bin = tape("ls /bin").lines().map { it.trim() }
    verifR(listOf("ls", "cat", "grep", "mkdir", "chmod").all { it in bin }, "ls /bin : l'armurerie des commandes (${bin.size})")
    verifR((tape("ls /bin | wc -l").trim().toIntOrNull() ?: 0) == Racine.OUTILS.size, "ls /bin | wc -l : un tuyau marche aussi sur la Racine")
    verifR(tape("find /etc -name hostname").trim() == "/etc/hostname", "find /etc : les chemins du Terminaworld")
    verifR("terminaworld.log" in tape("ls /var/log"), "ls /var/log : les archives")
    verifR(tape("cat /var/log/terminaworld.log").isNotBlank(), "les archives contiennent le journal du jeu")
    verifR(tape("ls /dev").lines().map { it.trim() }.containsAll(listOf("null", "random")), "ls /dev : les portails")
    verifR(tape("echo coucou > /dev/null").isEmpty(), "echo … > /dev/null : le trou noir accepte tout")
    verifR(tape("cat /proc/version").isNotBlank(), "cat /proc/version : le miroir des habitants (le vrai /proc)")
    tape("cd /etc")
    verifR(shell.chemin() == "/etc" && tape("cat hostname").trim() == "terminaworld", "cd /etc puis cat hostname (chemin relatif)")
    verifR("Permission denied" !in tape("ls -l /etc/hostname") && "r--r--r--" in tape("ls -l /etc/hostname"), "ls -l /etc/hostname : r--r--r-- (lecture seule)")

    println("3. Regarder, pas toucher : le gardien dit non")
    val avant = photo(Racine.dossier(jeu.home))
    for (cmd in listOf("mkdir essai", "touch /etc/essai", "echo x > /etc/hostname", "echo x >> hostname", "rm /etc/hostname",
            "rm -r /", "rm -rf ~/../..", "mv /etc/hostname ~/", "chmod 777 /etc", "cp ~/x /bin/", "mkdir /home/autre", "touch ../tmp/x")) {
        val s = tape(cmd)
        verifR("Permission denied" in s && "gardien" in s && "Pour les grands" in s, "« $cmd » refusé, expliqué (enfant + grands)")
    }
    verifR(photo(Racine.dossier(jeu.home)) == avant, "la Racine n'a pas changé")
    verifR(jeu.home.isDirectory && File(jeu.terrain, "vestibule").isDirectory, "le camp de base est intact")
    tape("cd ~/terrain_terminagotchi")
    verifR(tape("cp /etc/hostname nom_du_monde.txt").isEmpty() && File(jeu.terrain, "nom_du_monde.txt").readText().trim() == "terminaworld",
        "copier depuis la salle des règles vers la zone d'aventure : permis")
    verifR(tape("mkdir cabane").isEmpty() && File(jeu.terrain, "cabane").isDirectory, "bâtir dans la zone d'aventure : permis")
    verifR(tape("ls /bin/ls").trim() == "/bin/ls", "ls /bin/ls : l'outil est rangé dans l'armurerie")

    println("4. La carte part de la Racine")
    tape("cd /")
    tape("cd /etc")
    val ns = Maison.monde(jeu, marquer = true)
    verifR(ns.first().lieu == "racine" && ns.first().nom == "/", "la 1re ligne : la Racine")
    val etc = ns.firstOrNull { it.abs == "/etc" }
    val bins = ns.firstOrNull { it.abs == "/bin" }
    verifR(etc != null && !etc.brume && etc.ici, "/etc visité : la salle des règles, ◉ tu es ici")
    verifR(bins != null && !bins.brume, "/bin visité (ls /bin) : plus dans la brume")
    verifR(ns.firstOrNull { it.abs == "/tmp" }?.brume == true, "/tmp jamais visité : dans la brume")
    val village = ns.indexOfFirst { it.lieu == "village" }
    val camp = ns.indexOfFirst { it.lieu == "camp" }
    val zone = ns.indexOfFirst { it.genre == "zone" }
    verifR(village in 1 until camp && camp < zone, "le chemin : la Racine → le village → ton camp → la zone d'aventure")
    verifR(ns[zone].prof == 3 && ns[zone].nom == "terrain_terminagotchi" && ns[zone].parent == ns[camp], "la zone d'aventure est sous le camp de base")
    verifR(ns.any { it.nom == "vestibule" && it.prof == 4 }, "les lieux de la zone d'aventure suivent, décalés")
    val pied = Maison.pied(jeu)
    verifR(pied.any { it.startsWith("◉") && "/etc" in it }, "le pied : tu es ici, /etc")
    verifR(pied.any { "la Racine → la salle des règles" in it }, "le pied : la Racine → la salle des règles")
    tape("cd ~/terrain_terminagotchi/vestibule")
    verifR(Maison.pied(jeu).any { "la Racine → le village → ton camp de base → la zone d'aventure" in it }, "le panneau du vestibule, lieu par lieu")
    verifR(Maison.carte(jeu).joinToString("\n").let { "la Racine" in it && "la salle des règles" in it }, "la carte en texte (tree annoté) part de la Racine")
    verifR(Maison.lignesLieux().size == 2 + 2 * Racine.CARNET.size, "le carnet des lieux : ${Racine.CARNET.size} lieux, image + pour les grands")

    println("5. La version des grands à chaque étape (G-32), dans les 14 langues")
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val manque = mutableListOf<String>()
        for (c in Histoire.CHAPITRES) for (lid in c.lecons) {
            val l = jeu.catalogue[lid] ?: run { manque += lid; null } ?: continue
            for ((i, e) in l.etapes.withIndex()) {
                val a = e.adulte
                val cle = Histoire.cle(e.adulteCle ?: e.ditCle.removeSuffix(".dit") + ".adulte")
                if (a == null || ".adulte" in a || a.length < 20 || Langue.valeurs(cle, code).isEmpty()) manque += "$lid.$i"
            }
        }
        verifR(manque.isEmpty(), "$code : toutes les étapes ont leur version des grands ${if (manque.isEmpty()) "" else manque}")
    }
    Langue.definir("fr")
    jeu.extra.optJSONObject("histoire")?.put("faits", org.json.JSONArray())
    verifR(Explique.phrases(jeu, "-r", "recursif_rm").size == 2, "les options : l'image ET la version des grands, dès le palier 0")
    verifR(Explique.options("cd /etc").any { it.second == "racine" }, "le / d'un chemin absolu est expliqué (la Racine)")
    val e = jeu.catalogue["racine"]!!.etapes
    verifR(e.map { it.cmd } == listOf("cd /", "ls", "pwd", "cd ~", "cd ${Racine.HOME}/terrain_terminagotchi/vestibule"),
        "la leçon « Voyage jusqu'à la Racine » : cd /, ls, pwd, cd ~, chemin absolu")
    verifR(jeu.catalogue["gardien"]!!.etapes.map { it.cmd }.all { it.split(" ").last().startsWith("/") }, "« Les lieux du gardien » : seulement des lectures")
    verifR(Histoire.CHAPITRES.first().lecons == listOf("t0", "reveil1", "racine"), "la Racine juste après la navigation de base (chapitre 1)")

    dossier.deleteRecursively()
    println()
    println("$okR réussis, $koR échoués")
    if (koR > 0) System.exit(1)
}
