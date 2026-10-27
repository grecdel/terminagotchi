/*
 * Test JVM des retours « pédagogie » des simulations d'enfants (portage de pc/outils/test_pedagogie.py) :
 * les étapes sont validées sur le RÉSULTAT (code de sortie du shell, dossier, majuscules), `cd -` et `cd x && ls`
 * marchent dans le terminal de l'appli, le lieu attendu est calculé et montré sur la ligne ➜, les indices donnent le
 * bon lieu, le nom de l'œuf est nettoyé, chaque étape a sa ligne « vrai terminal ».
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Pedagogie.kt -d pedagogie.jar
 *   java -cp <imitations>:<appli.jar>:pedagogie.jar:kotlin-stdlib.jar PedagogieKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Placement
import fr.terminagotchi.Racine
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Verif
import fr.terminagotchi.Vert
import fr.terminagotchi.Vrai
import java.io.File
import org.json.JSONArray

class ActifsP(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilP(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsP(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okP = 0
var koP = 0
fun verifP(c: Boolean, m: String) {
    if (c) okP++ else koP++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_peda_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilP(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    Intro.nouvellePartie(jeu)          // ce que fait l'écran quand le nom de l'œuf est confirmé
    jeu.sauver()
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })
    var sortie = ""
    fun tape(cmd: String) {
        val interne = commandes.executer(cmd)
        sortie = interne?.texte ?: shell.executer(cmd)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier,
            code = if (interne != null) 0 else shell.code)
    }
    fun lec() = Histoire.leconCourante(jeu)?.id to jeu.etape
    fun propre(s: String?) = Vert.sansMarques(s ?: "").replace('\u00a0', ' ')

    println("1. Le terminal de l'appli : code de sortie, cd -, cd x && ls")
    shell.executer("ls")
    verifP(shell.code == 0, "ls : code 0")
    shell.executer("ls dossier_qui_n_existe_pas")
    verifP(shell.code != 0, "ls d'un nom absent : code ≠ 0 (${shell.code})")
    shell.executer("PWD")
    verifP(shell.code != 0, "PWD (majuscules) : code ≠ 0")
    File(jeu.home, "a/b").mkdirs()
    shell.executer("cd a")
    shell.executer("cd b")
    val r = shell.executer("cd -")
    verifP(shell.virtuel().endsWith("/a") && shell.code == 0, "cd - : retour au lieu d'avant (${shell.virtuel()}, « $r »)")
    shell.executer("cd ~")
    val o = shell.executer("cd a && ls")
    verifP(shell.virtuel().endsWith("/a") && "b" in o, "cd a && ls : le cd compte, puis ls est lancé là (« $o »)")
    shell.executer("cd ~")
    shell.executer("cd nulle_part && ls")
    verifP(shell.code != 0 && !shell.virtuel().endsWith("/a"), "cd raté && ls : ls n'est pas lancé, code ≠ 0")
    shell.executer("cd ~")

    println("2. Verif : motifs, tuyaux, jokers, lieu attendu, fautes")
    verifP(Verif.collee("ls-a") == "ls -a" && Verif.collee("cd/") == "cd /" && Verif.collee("cdvestibule") == "cd vestibule",
        "fautes collées : ls-a → ls -a, cd/ → cd /, cdvestibule → cd vestibule")
    verifP(Regex(Verif.LS_L).containsMatchIn("ls -la ../nid") && Regex(Verif.LS_L).containsMatchIn("ls -l -a nid") &&
        !Regex(Verif.LS_L).containsMatchIn("ls -a nid"), "ls -la, ls -l -a acceptés ; ls -a n'est pas ls -l")
    verifP(Regex(Verif.LS_A).containsMatchIn("ls --all") && Regex(Verif.LS_A).containsMatchIn("ls -l -a"), "ls --all, ls -l -a = ls -a")
    verifP(Regex(Verif.ajoute("repas")).containsMatchIn("echo poire | tee -a nid/repas.txt") &&
        Regex(Verif.ajoute("journal")).containsMatchIn("echo x >> ./journal.txt"), "tee -a et >> ./journal.txt acceptés")
    verifP(Intro.nomPropre("\u001b[2JZoé‮") == "[2JZoé", "le nom de l'œuf perd ses caractères de contrôle")
    verifP(Vrai.ligne("ls -l nid")?.contains("vrai terminal") == true && Vrai.ligne("free -h")?.contains("macOS") == true &&
        Vrai.ligne("termux-toast x") == null, "« Dans un vrai terminal… » : pareil, variante macOS, rien pour Termux")

    println("3. L'œuf puis la leçon 1 : validées sur le résultat")
    tape("PWD")
    verifP(Intro.faits(jeu).isEmpty(), "PWD ne nourrit pas l'œuf")
    tape("pwd; ls")
    verifP(Intro.faits(jeu).size == 2, "pwd; ls : les deux comptent pour l'œuf (${Intro.faits(jeu)})")
    for (c in listOf("echo bonjour", "whoami")) tape(c)
    Intro.toutDebloquer(jeu)
    jeu.xp = maxOf(jeu.xp, 10)
    verifP(lec() == ("t0" to 0), "leçon 1, étape 1 (${lec()})")
    tape("PWD")
    verifP(lec() == ("t0" to 0), "PWD ne valide pas « pwd »")
    verifP("minuscules" in propre(jeu.indiceLecon), "… l'indice dit d'écrire en minuscules (${jeu.indiceLecon})")
    tape("pwd")
    tape("Ls")
    verifP(lec() == ("t0" to 1), "Ls ne valide pas « ls »")
    tape("ls")
    tape("cd ~")
    verifP(lec().first == "reveil1", "leçon 1 finie (${lec()})")
    tape("mkdir -p terrain_terminagotchi")
    tape("cd terrain_terminagotchi && ls")
    verifP(lec() == ("reveil1" to 2), "cd terrain_terminagotchi && ls : deux étapes d'un coup (${lec()})")

    println("4. La cave : le bon lieu, les variantes, le cadenas")
    val h = Histoire.h(jeu)
    h.put("ailes", JSONArray(listOf("reveil", "nid")))
    h.put("faits", JSONArray(listOf("t0", "reveil1", "racine", "nid0", "debarras", "nid1", "secrets", "grenier0", "t4", "cave0")))
    h.put("chap", "cave")
    jeu.etape = 0
    jeu.xp = 10 * 12 * 12
    File(jeu.terrain, "nid").mkdirs()
    File(jeu.terrain, "nid/repas.txt").writeText("pomme\n")
    File(jeu.terrain, "cave").mkdirs()
    tape("cd ~/terrain_terminagotchi/cave")
    verifP(lec() == ("t3" to 0), "la leçon des droits (${lec()})")
    val e = Histoire.leconCourante(jeu)!!.etapes[0]
    verifP(Verif.lieuAttendu(jeu, e) == "", "« ls -l nid » se tape depuis le carrefour (calculé)")
    val montre = propre(Verif.commandeMontree(jeu, e))
    verifP("~/terrain_terminagotchi" in montre && montre.indexOf("~/terrain") < montre.indexOf("-l nid"), "➜ depuis la cave : « $montre »")
    verifP("terrain_terminagotchi" in propre(jeu.texteLecon()) && "💻" in (jeu.texteLecon() ?: ""),
        "le panneau de la leçon a le 📁 calculé et la ligne 💻 vrai terminal")
    tape("ls -l nid")
    verifP(lec() == ("t3" to 0), "ls -l nid dans la cave (No such file) ne valide pas")
    verifP("Carrefour" in propre(jeu.indiceLecon) && "cd ~/terrain_terminagotchi" in propre(jeu.indiceLecon),
        "l'indice donne le BON lieu (${jeu.indiceLecon})")
    tape("ls -la ../nid")
    verifP(lec() == ("t3" to 1), "ls -la ../nid depuis la cave : accepté")
    tape("cd ..")
    tape("chmod 444 nid/repas.txt")
    tape("echo poire | tee -a nid/repas.txt")
    verifP(lec().first != "t3", "… | tee -a nid/repas.txt refusé par le cadenas : l'étape est faite (${lec()})")
    File(jeu.terrain, "nid/repas.txt").setWritable(true)

    println("5. Hugo : le test « je connais déjà » et le mode défi sans aide (G-13)")
    h.put("ailes", JSONArray()); h.put("faits", JSONArray()); h.put("chap", "reveil"); jeu.etape = 0
    jeu.module("placement").put("etat", ""); jeu.module("sansaide").put("on", false)
    shell.executer("cd ~")
    val debut = Placement.commande(jeu, emptyList())
    verifP(Placement.actif(jeu) && "4" in debut, "placement : le test commence")
    for (c in listOf("pwd", "cd /", "cd ~", "ls -la")) tape(c)
    verifP(Histoire.fini(jeu, "reveil") && Placement.sansAide(jeu), "4 défis réussis : chapitre 1 validé, mode sans aide (${Placement.etat(jeu)})")
    val e2 = Histoire.leconCourante(jeu)!!.etapes[jeu.etape]
    verifP("trouver" in propre(Verif.commandeMontree(jeu, e2)), "sans aide : la commande est cachée")
    val aide = propre(Histoire.aideLecon(jeu))
    verifP(e2.cmd.split(" ")[0] in aide && "trouver" !in propre(Verif.commandeMontree(jeu, e2)), "`aide` montre la commande, où la taper et pourquoi")
    Placement.commande(jeu, listOf("off"))
    verifP(!Placement.sansAide(jeu), "sansaide off : mode normal")
    verifP("copie" !in fr.terminagotchi.Quetes.modeles(20, jeu) || "t4" in Histoire.faits(jeu), "pas de quête « Photocopie » avant la leçon de cp")

    println("\n$okP réussis, $koP échoués")
    System.exit(if (koP > 0) 1 else 0)
}
