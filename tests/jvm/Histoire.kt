/*
 * Test JVM (hors téléphone) de « La Maison endormie », portage de pc/outils/test_histoire.py : la même partie scriptée,
 * avec les commandes du téléphone.
 *
 * Comme le terminal de l'appli : « cd » est géré par Shell.kt (le vrai code de l'appli), les autres commandes sont lancées
 * avec bash dans le dossier courant (HOME = la maison de l'appli), puis le jeu fait le même tour qu'après une commande
 * tapée (Tour.apresCommande, avec le dossier courant du terminal). Les commandes du jeu (carte, quetes, aile) passent
 * par Commandes.kt, comme dans l'appli.
 *   1. chapitres 1-2 : la vieille porte, l'œuf, le nid, le repas ;
 *   2. liberté : on entre dans la cave (l'aile est choisie toute seule), sa famille est attirée (tirage toujours
 *      vérifiable), on la réveille, on change d'aile sans perdre l'étape atteinte ;
 *   3. une pièce secrète (ls -a, cd .placard_secret), une quête d'habitant (les chaussettes), le tableau des annonces
 *      (quêtes générées), la quête du jour, suivre une quête ;
 *   4. la carte (brouillard, ★, ◉, largeur des cases) et le journal ; les terres sauvages ; le carnet d'aventure ;
 *   5. le cœur s'ouvre à 5 ailes ; Abyssor (réponse comptée en direct) ;
 *   6. migration d'anciennes sauvegardes Android (tronc commun, branches de l'arbre, étape en cours) sans rien perdre ;
 *   7. rien n'est jamais écrit hors du terrain ; toutes les clés construites existent dans les 14 langues ;
 *      le hasard des quêtes est celui de Python (mêmes tirages que le PC pour une même graine).
 *
 * Il se compile avec kotlinc contre les classes de l'appli et des imitations d'android.* (qui ne sont pas dans le dépôt),
 * et se lance SANS pouvoir contourner les droits des fichiers (sinon chmod 444 n'empêche pas d'écrire) :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Histoire.kt -d histoire.jar
 *   java -cp <imitations>:<appli.jar>:histoire.jar:kotlin-stdlib.jar HistoireKt app/src/main/assets
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Commandes
import fr.terminagotchi.Dressage
import fr.terminagotchi.Explo
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Mots
import fr.terminagotchi.PyHasard
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recensement
import fr.terminagotchi.Shell
import fr.terminagotchi.Tirage
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsH(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilH(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsH(a)
    override fun getApplicationContext(): android.content.Context = this
}

const val GRAINE_H = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"   // factice, la même que sur PC
var nOk = 0
var nKo = 0

fun verifier(c: Boolean, m: String) {
    if (c) nOk++ else nKo++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeu: Jeu
lateinit var shell: Shell
lateinit var commandes: Commandes
val T: File get() = jeu.terrain

/** Lance une vraie commande avec bash dans un dossier ; renvoie sa sortie. */
fun bash(cmd: String, ou: File = shell.dossier): String {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeu.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    p.waitFor()
    return s
}

/** L'enfant tape une commande dans le terminal de l'appli, puis le jeu fait son tour. */
fun tape(cmd: String): String {
    var sortie = ""
    val interne = if (cmd.trim().split(" ")[0] == "cd") null else commandes.executer(cmd)
    when {
        cmd.trim().split(" ")[0] == "cd" -> shell.executer(cmd)     // « cd » : géré par l'appli (Shell.kt)
        interne != null -> sortie = interne.texte                   // carte, quetes, aile : commandes du jeu
        else -> sortie = bash(cmd)
    }
    Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
    return sortie
}

fun bulles() = (listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | ")
fun niveau(n: Int) { jeu.xp = maxOf(jeu.xp, 10 * (n - 1) * (n - 1)) }
fun h(): JSONObject = Histoire.h(jeu)
fun liste(a: JSONArray?) = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }
fun faits() = Histoire.faits(jeu)
fun q(): JSONObject = Quetes.q(jeu)
fun ql(k: String) = Quetes.liste(q(), k)
fun lecon(): Pair<String?, Int> = (Histoire.leconCourante(jeu)?.id) to jeu.etape
fun ecran() = jeu.texteLecon() ?: ""
fun inclus(champs: JSONObject, ind: JSONObject) = champs.keys().asSequence().all { k -> ind.has(k) && ind.get(k).toString() == champs.get(k).toString() }

/** Les fichiers de la maison de l'appli hors du terrain de jeu. */
fun horsTerrain(): Set<String> = jeu.home.walkTopDown().onEnter { it != T }.filter { it.isFile }.map { it.path }.toSet()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_histoire_" + System.nanoTime()).apply { mkdirs() }
    // root (sans setpriv) passe outre chmod 444 : la leçon des droits ne se valide pas et tout le reste déraille
    File(dossier, "verrou_droits").let { v ->
        v.writeText("x"); v.setWritable(false, false)
        if (v.canWrite()) {
            System.err.println("Ce test doit se lancer SANS le droit de passer outre chmod (root : setpriv --bounding-set -dac_override,-dac_read_search java …)")
            kotlin.system.exitProcess(2)
        }
        v.setWritable(true); v.delete()
    }
    val app = AppareilH(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    shell = Shell(jeu.home)
    commandes = Commandes(app, jeu, { shell.dossier })
    // pas d'ouverture automatique de l'exploration : les monstres sont appelés exprès (Explo.spawn)
    jeu.module("explo").put("ouverte", true)
    val jour = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
    Tirage.rangerGraines(jeu, JSONArray().put(JSONObject().put("id", "$jour.abcdef123456").put("valeur", GRAINE_H)))
    val avant = horsTerrain()

    println("0. Le hasard de Python")
    val r1 = PyHasard("1:1700000000:gen:g1")
    verifier(listOf(r1.bits(32), r1.bits(32), r1.bits(32)) == listOf(702512010L, 2266221659L, 2858299735L),
        "Mersenne Twister et graine texte (SHA-512) : mêmes nombres que random.Random en Python")
    val r2 = PyHasard("1:1700000000:abyssor")
    val n2 = r2.randint(3, 6)
    verifier(n2 == 5 && r2.echantillon((0 until 7).toList(), n2) == listOf(6, 5, 0, 2, 4), "randint et sample comme en Python")
    val r3 = PyHasard("abcd1234:42:titres")
    val l3 = (0 until 8).toMutableList()
    r3.melanger(l3)
    verifier(l3 == listOf(1, 6, 0, 2, 5, 4, 3, 7) && r3.choix(listOf("a", "b", "c")) == "b" && r3.randrange(9) == 6 &&
        PyHasard("").bits(32) == 4124137760L, "shuffle, choice, randrange comme en Python")

    println("1. Chapitre 1 : le réveil")
    tape("date")
    verifier(Histoire.chap(jeu) == "reveil" && lecon() == ("t0" to 0), "nouvelle partie : chapitre 1, leçon ${lecon()}")
    verifier(!T.exists(), "pas encore de terrain (la vieille porte apparaît avec la leçon 2)")
    niveau(2)
    for (c in listOf("pwd", "ls", "cd ~")) tape(c)
    verifier(lecon() == ("reveil1" to 0), "« Où suis-je ? » finie → ${lecon()}")
    verifier(File(T, "vestibule/oeuf_tout_chaud.txt").isFile, "la vieille maison est là : vestibule/oeuf_tout_chaud.txt")
    verifier("Chapitre 1 · Le réveil" in ecran() && "Le vieux chemin" in ecran(), "l'écran montre le chapitre et la leçon")
    tape("cd terrain_terminagotchi")
    verifier(lecon() == ("reveil1" to 1), "cd terrain_terminagotchi : entré dans la grande salle (vu par le dossier courant)")
    tape("ls")
    tape("ls")
    verifier(lecon() == ("reveil1" to 2), "ls dans la grande salle")
    tape("cd vestibule")
    tape("ls")
    verifier(Histoire.fini(jeu, "reveil") && Histoire.chap(jeu) == "nid", "l'œuf est trouvé : chapitre 1 fini, chapitre 2")
    verifier("CRAC" in bulles(), "texte de fin du chapitre dit par la créature")
    verifier("veilleuse" in ql("objets"), "récompense du chapitre : une veilleuse")

    println("2. Chapitre 2 : le nid")
    niveau(3)
    tape("mkdir nid")
    verifier(lecon() == ("nid0" to 0) && "pas dans la bonne pièce" !in bulles(), "${lecon()} : il faut d'abord reculer")
    File(T, "vestibule/nid").delete()
    tape("cd ..")
    verifier(lecon() == ("nid0" to 1), "cd .. : retour dans la grande salle")
    tape("mkdir nid")
    tape("touch nid/lit.txt")
    verifier("nid0" in faits() && "Bâtisseur" in jeu.skills, "le nid et le lit (compétence Bâtisseur)")
    for (c in listOf("mkdir debarras", "rmdir debarras", "rm -r vieille_cabane")) tape(c)
    verifier("debarras" in faits() && !File(T, "vieille_cabane").exists(), "une pièce en trop : rmdir, puis la broyeuse rm -r")
    verifier(Explo.debloquee(jeu), "les monstres peuvent arriver")
    niveau(4)
    tape("echo pome > nid/repas.txt")
    verifier("pomme" in (jeu.indiceLecon ?: ""), "« pome » : l'indice de toujours marche dans l'histoire")
    tape("echo pomme > nid/repas.txt")
    tape("cat nid/repas.txt")
    verifier(Histoire.fini(jeu, "nid") && Histoire.chapitreCourant(jeu) == null, "chapitre 2 fini : aucune aile imposée")
    verifier("Quel lieu réveiller" in ecran(), "l'écran propose de choisir une aile")
    verifier(Maison.AILES.all { File(T, it).isDirectory } && !File(T, "coeur").exists() && File(T, "jardin").isDirectory,
        "les 7 portes des ailes sont posées, et le jardin du téléphone (pas encore le cœur)")

    println("3. Liberté : on entre dans la cave")
    niveau(5)
    tape("cd cave")
    verifier(Histoire.chap(jeu) == "cave" && lecon() == ("cave0" to 1), "entrer dans la cave la choisit (et l'entrée est validée) : ${lecon()}")
    verifier("Démons" in bulles(), "texte d'ouverture du chapitre (les Démons)")
    tape("whoami")
    tape("id")
    verifier(lecon() == ("t3" to 0), "whoami, id (pas de sudo sur le téléphone) → ${lecon()}")
    tape("ls -l nid")
    verifier(lecon() == ("t3" to 0) && "nid" in (jeu.indiceLecon ?: "") + bulles() || lecon() == ("t3" to 1),
        "ls -l nid depuis la cave : ${lecon()}")
    tape("cd ..")
    tape("ls -l nid")
    tape("chmod 444 nid/repas.txt")
    verifier(lecon() == ("t3" to 2), "chmod 444 : le cadenas est posé")
    verifier(Histoire.familleAttiree(jeu) == "Démons", "pendant la cave, les Démons sont attirés (chmod a été goûtée)")
    Recensement.compte(jeu).put("apparitions", JSONObject())
    val vus = mutableListOf<JSONObject>()
    for (i in 0 until 41) {
        val (_, v) = Explo.spawn(jeu)!!
        if (i == 0) Explo.captures(jeu).put(JSONObject(v.toString()).put("id", "essai"))   // (le tout premier monstre est à part)
        else vus.add(v)
        Dressage.abandonner(jeu)
    }
    val caps = Explo.captures(jeu)
    for (i in caps.length() - 1 downTo 0) if (caps.getJSONObject(i).optString("id") == "essai") caps.remove(i)
    verifier(vus.all { it.optString("attire") == "Démons" }, "chaque apparition déclare la famille attirée (champ attire)")
    verifier(vus.all { inclus(Tirage.tirer(GRAINE_H, it.getLong("n"), false, it.optString("attire").ifEmpty { null }).champs, it) },
        "et reste vérifiable : (graine, compteur, attire) refait exactement le même individu")
    val nDem = vus.count { Bestiaire.espece(it.getString("espece"))!!.famille == "Démons" }
    verifier(nDem >= 6, "les Démons sortent plus souvent : $nDem/40")
    tape("echo poire >> nid/repas.txt")
    verifier(Histoire.fini(jeu, "cave") && "gardien_des_cles" in ql("titres"), "la cave est réveillée : titre « Gardien des clés »")
    verifier(File(T, "nid/decorations/cadenas_dore.txt").isFile, "objet gagné : nid/decorations/cadenas_dore.txt")
    verifier(Histoire.familleAttiree(jeu) == null, "plus de chapitre en cours : plus d'attirance d'histoire")

    println("   … changer d'aile sans rien perdre")
    tape("cd grenier")
    verifier(Histoire.chap(jeu) == "grenier", "cd grenier : le grenier est choisi")
    tape("ls -R")
    verifier(lecon() == ("grenier0" to 2), "ls -R (pas de tree sur le téléphone) : le plan du grenier")
    println("  " + tape("aile tour"))
    verifier(Histoire.chap(jeu) == "tour" && h().getJSONObject("pas").optInt("grenier0", -1) == 2, "aile tour : l'étape du grenier est gardée")
    tape("cd ../tour")
    verifier(lecon() == ("tour0" to 1), "dans la tour")
    println("  " + tape("aile grenier"))
    tape("cd ../grenier")
    verifier(lecon() == ("grenier0" to 2) && h().getJSONObject("pas").optInt("tour0", -1) == 1, "retour au grenier : on reprend à l'ours")
    tape("mv fouillis/ours_en_peluche.txt ../nid/")
    verifier(lecon() == ("t4" to 0), "l'ours est au nid")

    println("4. Une pièce secrète")
    tape("cd ../vestibule")
    tape("cat lettre_de_bienvenue.txt")
    verifier("q01" in ql("actives"), "lire la lettre de bienvenue accepte la quête")
    tape("ls -a")
    tape("cd .placard_secret")
    verifier("q01" in ql("finies") && "q02" in ql("finies"), "cd .placard_secret : la pièce secrète est trouvée")
    verifier(Quetes.secrets(jeu).first == 1, "pièces secrètes : ${Quetes.secrets(jeu)}")
    verifier("fouineur" in ql("titres"), "titre « Fouineur »")

    println("5. Une quête d'habitant : les chaussettes de Mousseline")
    tape("cd ~/terrain_terminagotchi/grenier")
    tape("cat habitant_mousseline.txt")
    verifier("q11" in ql("actives"), "Mousseline demande un service")
    val trouvees = bash("find . -name \"chaussette*\"").split(Regex("\\s+")).filter { it.isNotEmpty() }
    verifier(trouvees.size == 3, "find trouve les 3 chaussettes (même dans un coin caché) : $trouvees")
    tape("find . -name \"chaussette*\"")
    for (c in trouvees) tape("mv $c panier/")
    verifier("q11" in ql("finies") && "pelote" in ql("objets"), "chaussettes rangées : quête finie, une pelote de laine")

    println("6. Le tableau des annonces, la quête du jour, suivre une quête")
    tape("cat ~/terrain_terminagotchi/vestibule/tableau_des_annonces.txt")
    val gen = ql("offertes")
    verifier(gen.size == 3 && gen.all { it in ql("actives") }, "3 quêtes générées acceptées : $gen")
    val jourId = q().optJSONObject("jour")?.optString("id")
    verifier(jourId != null && jourId in ql("actives"), "une quête du jour : $jourId")
    val g1 = q().getJSONObject("gen").getJSONObject(gen[0])
    val p = g1.getJSONObject("p")
    println("   modèle : ${g1.getString("m")} $p · ${Quetes.titre(jeu, gen[0])}")
    fun s(k: String) = p.optString(k)
    val faire = when (g1.getString("m")) {
        "perdu" -> "mv $(find ~/terrain_terminagotchi/${s("piece")} -name ${s("fichier")}) ~/terrain_terminagotchi/nid/"
        "construire" -> "mkdir ~/terrain_terminagotchi/${s("piece")}/${s("nom")}"
        "copie" -> "mkdir -p ~/terrain_terminagotchi/nid/copies && cp ~/terrain_terminagotchi/${s("piece")}/${s("fichier")} ~/terrain_terminagotchi/nid/copies/"
        "compter" -> "ls ~/terrain_terminagotchi/${s("piece")}/${s("tas")} | wc -l > ~/terrain_terminagotchi/nid/${s("reponse")}"
        "proteger" -> "chmod 444 ~/terrain_terminagotchi/${s("piece")}/${s("fichier")}"
        else -> "echo ${s("mot")} > ~/terrain_terminagotchi/nid/${s("reponse")}"
    }
    tape(faire)
    verifier(gen[0] in ql("finies"), "quête générée réussie (${g1.getString("m")})")
    verifier(ql("offertes").size == 3 && gen[0] !in ql("offertes"), "une nouvelle annonce la remplace")
    val num = Quetes.numerotees(jeu)
    println("  " + tape("quetes suivre ${num.indexOf(gen[1]) + 1}"))
    verifier(q().optString("suivie") == gen[1], "quetes suivre N")
    verifier("👣" in ecran(), "la quête suivie s'affiche sous la leçon")
    val varie = (0 until 30).map { Quetes.generer(jeu, "g$it", 5).first.toString() }.toSet()
    verifier(varie.size > 15, "le générateur varie (${varie.size} quêtes différentes sur 30)")
    val partie = jeu.partie
    val a1 = Quetes.generer(jeu, "g1", 5).first.toString() + Quetes.generer(jeu, "g2", 5).first.toString()
    jeu.partie = "abcd1234"
    val b1 = Quetes.generer(jeu, "g1", 5).first.toString() + Quetes.generer(jeu, "g2", 5).first.toString()
    jeu.partie = partie
    verifier(a1 != b1, "une autre partie a d'autres quêtes (graine par partie)")
    verifier(Quetes.modeles(12).containsAll(Quetes.modeles(5)) && Quetes.modeles(12).size > Quetes.modeles(5).size,
        "la difficulté des quêtes générées suit le niveau")

    println("7. La carte et le journal")
    tape("cat /proc/sys/kernel/hostname")
    verifier("terres sauvages" in bulles(), "lire /proc/sys/kernel/hostname : avertissement des terres sauvages (lecture seule)")
    val carte = tape("carte")
    println(carte.lines().joinToString("\n") { "     $it" })
    verifier("Grenier" in carte && "Cave" in carte && "Tour" in carte, "pièces visitées révélées")
    verifier("Dortoir" !in carte && "░░░░" in carte, "pièces jamais visitées dans le brouillard")
    verifier("◉" in carte && "★" in carte && "✓" in carte, "◉ tu es ici, ★ quêtes, ✓ réveillée")
    verifier("Terres sauvages" in carte, "les terres sauvages apparaissent sur la carte")
    verifier(Maison.verifierLargeur(Maison.carte(jeu)).size == 1, "toutes les lignes du plan ont la même largeur")
    val celeste = Bestiaire.publiques().first { it.famille == "Célestes" }
    Dressage.commencer(jeu, celeste)
    verifier("🐾" in Maison.carte(jeu).joinToString("\n"), "🐾 : un monstre Céleste est là (dans la tour, visitée)")
    Dressage.abandonner(jeu)
    val j = tape("quetes")
    println(j.lines().take(14).joinToString("\n") { "     $it" })
    verifier("Quête principale" in j && "Quêtes secondaires en cours" in j && "Terminées" in j, "le journal a ses 3 parties")
    verifier("1. " in j && "[du jour]" in j, "quêtes numérotées, quête du jour marquée")
    val lex = t("lex.carnet.titre", "nom" to jeu.nom) + "\n" + listOf("chmod", "pwd").joinToString("\n") { "$it · 📖 " + Histoire.quand(jeu, it) } +
        "\n" + Histoire.souvenirs(jeu).joinToString("\n")
    verifier("Carnet d'aventure" in lex && "chmod · 📖 La Cave" in lex && "pwd · 📖 Le réveil" in lex, "le carnet range chaque commande avec son chapitre")
    verifier("Gardien des clés" in lex && "Souvenirs" in lex, "les souvenirs (titres, objets) sont dans le carnet")

    println("8. Le cœur et Abyssor")
    verifier(!Histoire.ouvert(jeu, "coeur"), "le cœur est fermé (1 aile réveillée)")
    val ailes = h().getJSONArray("ailes")
    for (a in listOf("bibliotheque", "machines", "dortoir", "atelier")) ailes.put(a)
    tape("cd ~/terrain_terminagotchi")
    verifier(Histoire.ouvert(jeu, "coeur") && File(T, "coeur/message_brouille.txt").isFile, "5 ailes : le cœur s'ouvre (et ses meubles)")
    val brouille = File(T, "coeur/message_brouille.txt").readText()
    verifier("ihcto" !in brouille && bash("rev coeur/message_brouille.txt").startsWith("Le cœur"), "le message brouillé se lit avec rev")
    val fa = h().getJSONArray("faits")
    fa.put("coeur0"); fa.put("coeur1")
    Histoire.choisir(jeu, "coeur")
    jeu.xp = 10 * 11 * 11
    tape("cat coeur/.porte_secrete/abyssor_dort.txt")
    val n = Histoire.tracesAbyssor(jeu)
    val compte = bash("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l").trim()
    verifier(n in 3..6 && compte.toIntOrNull() == n, "Abyssor a laissé $n griffures (grep -rl | wc -l dit $compte)")
    tape("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l")
    tape("echo ${n + 1} > coeur/reponse.txt")
    verifier(lecon() == ("coeur2" to 2) && "nombre" in (jeu.indiceLecon ?: ""), "mauvais nombre : Abyssor secoue la tête")
    tape("grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l > coeur/reponse.txt")
    verifier(Histoire.fini(jeu, "coeur"), "bonne réponse : le cœur bat, le monde est réveillé")
    verifier("Le monde est réveillé" in ecran(), "écran de fin")

    println("9. Migration des anciennes sauvegardes Android")
    jeu.sauver()
    fun ancienne(lecon: Int, etape: Int, progres: Map<String, Int> = emptyMap(), active: String = "", vus: List<String> = emptyList()) {
        jeu.extra = JSONObject()
        jeu.lecon = lecon
        jeu.etape = etape
        jeu.vus.clear(); jeu.vus.addAll(vus)
        jeu.extra.put("arbre", JSONObject().put("progres", JSONObject(progres)).put("active", active))
        Histoire.migrer(jeu)
    }
    ancienne(5, 1, mapOf("telephone" to 1, "scripts" to 3), "telephone", listOf("ls", "lampe"))
    verifier(faits().containsAll(listOf("t0", "reveil1", "nid0", "nid1", "t3", "t4", "telephone0", "scripts0", "scripts1", "scripts2")),
        "tronc commun + branches → leçons faites dans les chapitres")
    verifier(Histoire.ailes(jeu).containsAll(listOf("reveil", "nid")) && Histoire.chap(jeu) == "telephone" && lecon() == ("telephone1" to 1),
        "branche Téléphone en cours (Le portier, étape 2) → le jardin du téléphone, même étape : ${Histoire.chap(jeu)} ${lecon()}")
    verifier(h().getJSONObject("carnet").optString("lampe") == "avant", "carnet : les commandes d'avant sont rangées « avant l'histoire »")
    ancienne(5, 2, mapOf("systeme" to 0), "systeme")
    verifier(Histoire.chap(jeu) == "dortoir" && "cave0" in faits() && lecon() == ("dortoir0" to 1),
        "branche Système en cours (ps) → whoami et id sont dans la cave, ps au dortoir : ${Histoire.chap(jeu)} ${lecon()}")
    ancienne(3, 1)
    verifier(Histoire.chap(jeu) == "cave" && h().getJSONObject("pas").optInt("t3", -1) == 1 && lecon() == ("cave0" to 0),
        "en pleine leçon des droits → la cave (l'étape chmod est gardée pour plus tard)")
    ancienne(2, 2)
    verifier(Histoire.chap(jeu) == null && "nid1" in faits() && h().getJSONObject("pas").optInt("biblio1", -1) == 0 &&
        Histoire.fini(jeu, "nid"), "grep en cours : le garde-manger est fini (le grep revient à la bibliothèque)")
    ancienne(1, 1)
    verifier(Histoire.chap(jeu) == "reveil" && lecon() == ("reveil1" to 0), "en train de construire le terrain → la vieille porte")
    ancienne(0, 0)
    verifier(lecon() == ("t0" to 0) && faits().isEmpty(), "toute nouvelle partie : rien de fait")
    // une vraie sauvegarde d'avant, dans le fichier : le premier tour de jeu la range
    jeu.recharger()
    jeu.extra.remove("histoire")
    jeu.extra.remove("quetes")
    jeu.lecon = 4
    jeu.etape = 2
    jeu.extra.put("arbre", JSONObject().put("progres", JSONObject().put("systeme", 2)).put("active", ""))
    jeu.sauver()
    jeu.recharger()
    tape("date")
    verifier(jeu.extra.optJSONObject("histoire") != null && "systeme1" in faits() && "dortoir0" in faits(),
        "sauvegarde d'avant lue depuis le fichier : rangée dans les chapitres au premier tour")
    verifier(Histoire.chap(jeu) == "grenier" && lecon() == ("grenier0" to 0) && h().getJSONObject("pas").optInt("t4", -1) == 2,
        "leçon « Grand ménage » en cours → le grenier, étape mv gardée : ${lecon()}")

    println("10. Terrain effacé, sécurité et langues")
    File(T, "grenier").deleteRecursively()
    tape("ls")
    verifier(File(T, "grenier/lettre_du_jardinier.txt").isFile && File(T, "grenier/fouillis").isDirectory,
        "grenier effacé : la porte, ses meubles et ses quêtes pas finies reviennent")
    val nouveaux = (horsTerrain() - avant).sorted()
    verifier(nouveaux.isEmpty(), "rien d'écrit hors du terrain ${nouveaux.take(3)}")
    val cles = mutableSetOf<String>()
    for (c in Histoire.CHAPITRES) for (x in listOf("titre", "court", "debut", "fin")) cles.add("hist.${c.id}.$x")
    for (c in Histoire.CHAPITRES) for (lid in c.lecons) {
        val l = jeu.catalogue[lid]!!
        cles.add(l.titreCle)
        for (e in l.etapes) { cles.add(e.ditCle); cles.add(e.bravoCle); e.astuceCle?.let { cles.add(it) } }
    }
    for (qq in Quetes.QUETES) { cles.add("qu.${qq.id}.titre"); cles.add("qu.${qq.id}.texte") }
    val objets = Quetes.QUETES.mapNotNull { it.objet } + Histoire.CHAPITRES.mapNotNull { it.objet } + Quetes.OBJETS_PERDUS
    for (o in objets) cles.add("qu.objet.$o")
    for (ti in Quetes.QUETES.mapNotNull { it.titre } + Histoire.CHAPITRES.mapNotNull { it.titre }) cles.add("qu.titre.$ti")
    for (m in Quetes.MODELES_FACILES + Quetes.MODELES_MOYENS + Quetes.MODELES_DURS) for (x in listOf("titre", "texte")) cles.add("qu.gen.$m.$x")
    for (pp in Maison.PIECES + listOf("grande_salle", "recoins", "sauvage", "jardin")) cles.add("carte.piece.$pp")
    for (sk in jeu.catalogue.values.mapNotNull { it.skill }) cles.add("skill.$sk")
    val manquantes = mutableMapOf<String, List<String>>()
    for (code in Langue.LANGUES.keys) {
        val d = JSONObject(File(assets, "langues/$code.json").readText())
        val m = cles.filter { !d.has(it) && !d.has(Histoire.cle(it)) }.sorted()
        if (m.isNotEmpty()) manquantes[code] = m
    }
    verifier(manquantes.isEmpty(), "${cles.size} clés construites présentes dans les 14 langues" +
        if (manquantes.isNotEmpty()) " — manquantes : ${manquantes.mapValues { it.value.take(3) }}" else "")
    for (code in listOf("fr", "en", "ja", "ar")) {
        Langue.definir(code)
        for (k in listOf("hist.coeur.debut", "qu.q11.texte", "hist.entree.dit", "hist.dortoir.debut", "hist.tour1.0.bravo", "qu.q41.texte")) {
            val cle = if (k == "hist.tour1.0.bravo") "hista.tour1.0.bravo" else k
            val x = Histoire.tx(cle, mapOf("piece" to "grenier"), 1)
            verifier("{" !in x, "$code : ${Histoire.cle(cle)} rempli sans accolade oubliée")
        }
        verifier("ABYSSOR" in t("hist.meuble.griffure") && "ABYSSOR" !in t("hist.meuble.abyssor"),
            "$code : ABYSSOR en majuscules sur les griffures seulement (l'énigme compte juste)")
        verifier(listOf("hist.libre.dit", "hist.aile.autre", "hist.fin.suite", "qu.acceptee.dit", "qu.tableau.pied").none {
            "tg " in t(Histoire.cle(it)) || "[a]" in t(Histoire.cle(it)) }, "$code : pas de « tg » ni de touche [a] dans les textes du téléphone")
    }
    // la carte, les ailes et le journal dans chaque langue (comme pc/outils/parcours.py) : rien à remplir, rien de cassé
    val resteParam = Regex("\\{[a-z_A-Z]+\\}")
    val resteCle = Regex("(^|\\s)(hist|hista|qu|qua|carte|cartea|lex|lexa)\\.[a-z_0-9]+(\\.[a-z_0-9]+)*(\\s|$)", RegexOption.MULTILINE)
    val casses = mutableListOf<String>()
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val c = Maison.carte(jeu)
        val tout = (c + Histoire.lignesAiles(jeu) + Quetes.journal(jeu) + Histoire.souvenirs(jeu)).joinToString("\n") + "\n" + (jeu.texteLecon() ?: "")
        if (Maison.verifierLargeur(c).size != 1) casses.add("$code : largeur ${Maison.verifierLargeur(c)}")
        resteParam.find(tout)?.let { casses.add("$code : ${it.value}") }
        resteCle.find(tout)?.let { casses.add("$code : ${it.value.trim()}") }
    }
    verifier(casses.isEmpty(), "carte, ailes, journal et carnet dans les 14 langues : cases alignées, rien à remplir $casses")
    Langue.definir("ar")
    println(Maison.carte(jeu).take(6).joinToString("\n") { "     $it" })
    Langue.definir("fr")

    println("\n$nOk réussis, $nKo échoués")
    System.exit(if (nKo > 0) 1 else 0)
}
