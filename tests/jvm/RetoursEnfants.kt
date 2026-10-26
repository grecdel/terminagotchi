/*
 * Test JVM (hors téléphone) des retours des enfants de 7 ans, portage de pc/outils/test_retours_enfants.py
 * (dans « La Maison endormie ») :
 *   1. leçons (chapitres 1-2, puis la bibliothèque et la cave choisies librement) : « pome » au lieu de « pomme »
 *      → indice clair, la leçon attend la bonne commande ;
 *   2. terrain effacé (rm -rf) → bulle + bandeau avec la commande ; reconstruit → la leçon reprend au bon
 *      endroit (repas.txt remis) ; si l'enfant n'y arrive pas, le jeu reconstruit lui-même après 12 commandes ;
 *   3. premier dressage : un monstre courant et commun, 2 épreuves simples, indice « presque », tirage toujours
 *      vérifiable (graine, compteur) ; puis la difficulté monte avec les captures ;
 *   4. attirance : sur 1200 apparitions vérifiables, la famille attirée sort vraiment plus souvent (≈ 29 %, comme le PC) ;
 *   5. mini-combat : gagné (peur −40, une épreuve en moins), puis perdu (KO, repos, pas de mort).
 *
 * De vraies commandes sont lancées avec bash (HOME = la maison de l'appli), « cd » par Shell.kt comme dans l'appli,
 * puis le jeu fait le même tour qu'après une commande tapée dans le terminal (Tour.apresCommande, avec le dossier
 * courant du terminal).
 *
 * Il se compile avec kotlinc contre les classes de l'appli et des imitations d'android.* (qui ne sont pas
 * dans le dépôt), et se lance SANS être root (sinon chmod 444 n'empêche pas d'écrire) :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/RetoursEnfants.kt -d retours.jar
 *   java -cp <imitations>:<appli.jar>:retours.jar:kotlin-stdlib.jar RetoursEnfantsKt app/src/main/assets
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Combat
import fr.terminagotchi.Dressage
import fr.terminagotchi.Equipe
import fr.terminagotchi.Exemples
import fr.terminagotchi.Explique
import fr.terminagotchi.Explo
import fr.terminagotchi.Animations
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Recensement
import fr.terminagotchi.Regles
import fr.terminagotchi.Shell
import fr.terminagotchi.Terrain
import fr.terminagotchi.Tirage
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsR(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilR(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsR(a)
    override fun getApplicationContext(): android.content.Context = this
}

const val GRAINE = "9e3779b97f4a7c15f39cc0605cedc8341082276bf3a27251f86c6a11d0c18e95"   // factice, la même que sur PC
var ok = 0
var ko = 0

fun verifier(c: Boolean, m: String) {
    if (c) ok++ else ko++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeu: Jeu
lateinit var shell: Shell
val T: File get() = jeu.terrain

/** L'enfant tape une commande dans le terminal (ou : le dossier où elle est tapée, sinon là où il en est) :
 *  « cd » passe par Shell.kt comme dans l'appli, le reste s'exécute vraiment (bash), puis le jeu fait son tour. */
fun tape(cmd: String, ou: File? = null) {
    if (ou != null) shell.dossier = ou
    if (!shell.dossier.isDirectory) shell.dossier = jeu.home
    if (cmd.trim().split(" ")[0] == "cd") shell.executer(cmd)
    else {
        val pb = ProcessBuilder("bash", "-c", cmd).directory(shell.dossier).redirectErrorStream(true)
        pb.environment()["HOME"] = jeu.home.absolutePath
        val p = pb.start()
        p.inputStream.readBytes()
        p.waitFor()
    }
    Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
}

fun niveau(n: Int) { jeu.xp = maxOf(jeu.xp, 10 * (n - 1) * (n - 1)) }
fun lec(): Pair<String?, Int> = Histoire.leconCourante(jeu)?.id to jeu.etape

/** Les bulles telles que l'enfant les lit (sans les backticks des commandes en vert, voir Vert.kt). */
fun bulles() = Vert.sansMarques((listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | "))

/** Les champs tirés de la graine sont tous dans l'individu, avec les mêmes valeurs. */
fun inclus(champs: JSONObject, ind: JSONObject) = champs.keys().asSequence().all { k -> ind.has(k) && ind.get(k).toString() == champs.get(k).toString() }

fun dressage(): JSONObject? = jeu.module("dressage").optJSONObject("en_cours")
fun liste(a: JSONArray?) = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_retours_" + System.nanoTime()).apply { mkdirs() }
    // root (sans setpriv) passe outre chmod 444 : la leçon des droits ne se valide pas et tout le reste déraille
    File(dossier, "verrou_droits").let { v ->
        v.writeText("x"); v.setWritable(false, false)
        if (v.canWrite()) {
            System.err.println("Ce test doit se lancer SANS le droit de passer outre chmod (root : setpriv --bounding-set -dac_override,-dac_read_search java …)")
            kotlin.system.exitProcess(2)
        }
        v.setWritable(true); v.delete()
    }
    val app = AppareilR(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    shell = Shell(jeu.home)
    // pas d'ouverture automatique de l'exploration pendant le test : les monstres sont appelés exprès (Explo.spawn)
    jeu.module("explo").put("ouverte", true)
    val jour = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
    Tirage.rangerGraines(jeu, JSONArray().put(JSONObject().put("id", "$jour.abcdef123456").put("valeur", GRAINE)))

    niveau(2)
    for (c in listOf("pwd", "ls", "cd ~")) tape(c)
    for (c in listOf("cd terrain_terminagotchi", "ls", "cd vestibule", "ls")) tape(c)     // chapitre 1 : la vieille porte, l'œuf
    niveau(3)
    for (c in listOf("cd ..", "mkdir nid", "touch nid/lit.txt",                          // chapitre 2 : le nid
            "mkdir debarras", "rmdir debarras", "rm -r vieille_cabane")) tape(c, T)        // et une pièce en trop
    verifier("nid0" in Histoire.faits(jeu) && "Bâtisseur" in jeu.skills, "chapitres 1-2 : terrain, œuf et nid construits")

    println("1. Leçons : un indice quand c'est presque ça")
    niveau(4)
    tape("echo pome > nid/repas.txt", T)
    verifier(lec() == ("nid1" to 0), "« pome » : la leçon attend encore la bonne commande")
    val il = jeu.indiceLecon ?: ""
    verifier("pome" in il && "pomme" in il, "indice : $il")
    verifier("💡 Presque" in (jeu.texteLecon() ?: ""), "l'indice s'affiche sous la leçon")
    tape("echo pomme > nid/repas.txt", T)
    verifier(lec() == ("nid1" to 1) && jeu.indiceLecon == null, "« pomme » : étape réussie, l'indice disparaît")
    tape("cat nid/repas.txt", T)
    tape("cat mot_secret.txt", T)                           // le point oublié : le passage secret reste caché
    verifier(lec() == ("secrets" to 0), "passages secrets : il faut d'abord les voir avec ls -a")
    for (c in listOf("ls -a", "cat .mot_secret.txt")) tape(c, T)
    verifier(Histoire.fini(jeu, "nid"), "chapitre 2 fini (avec les passages secrets) : la maison est libre")
    niveau(5)
    tape("cd bibliotheque", T)
    for (c in listOf("find . -name \"*abysses*\"", "cat etagere_c/coin_poussiereux/livre_des_abysses.txt")) tape(c, File(T, "bibliotheque"))
    verifier(lec() == ("biblio1" to 0), "la bibliothèque : le livre est retrouvé, on passe à la loupe")
    tape("cd ..")
    tape("grep pome nid/repas.txt", T)
    verifier(lec() == ("biblio1" to 0) && "« pome »" in (jeu.indiceLecon ?: ""), "grep pome : indice, pas de silence")
    tape("grep pomme nid/repas.txt", T)
    verifier(lec() == ("biblio1" to 1), "grep pomme : réussi")
    Histoire.choisir(jeu, "cave")                                          // on change d'aile (l'étape est gardée)
    tape("cd cave", T)
    for (c in listOf("whoami", "id", "cd ..")) tape(c)
    tape("ls -l nid", T)
    verifier(lec() == ("t3" to 1), "la cave (droits) : on en est à chmod 444 nid/repas.txt")
    tape("chmod 444 nid/repas.tx", T)
    verifier("repas.tx »" in (jeu.indiceLecon ?: ""), "chmod 444 nid/repas.tx : ${jeu.indiceLecon}")

    println("2. Terrain effacé")
    tape("rm -rf ~/terrain_terminagotchi")
    verifier(Terrain.perdu(jeu) == "mkdir -p ~/terrain_terminagotchi/nid", "détecté : la commande proposée est « ${Terrain.perdu(jeu)} »")
    verifier("mkdir -p ~/terrain_terminagotchi/nid" in bulles(), "une bulle claire donne la commande")
    val bandeau = Terrain.bandeau(jeu) ?: ""
    verifier("➜ mk" in Vert.sansMarques(bandeau) && "~/terrain_terminagotchi/nid" in bandeau, "le bandeau (avec la commande) reste sur l'écran principal")
    verifier(!Explo.debloquee(jeu), "pas de monstre tant que le nid n'existe pas")
    tape("mkdir -p ~/terrain_terminagotchi/nid")
    verifier(Terrain.perdu(jeu) == null && Terrain.bandeau(jeu) == null, "reconstruit : plus d'alerte")
    verifier(File(T, "nid/repas.txt").isFile, "repas.txt remis pour que la leçon continue")
    verifier(lec() == ("t3" to 1), "la leçon reprend au bon endroit (chmod 444)")
    verifier(File(T, "cave").isDirectory && File(T, "grenier").isDirectory, "les portes des ailes sont reposées")
    tape("chmod 444 nid/repas.txt", T)
    verifier(lec() == ("t3" to 2), "chmod 444 : réussi après la reconstruction")
    tape("rm -rf ~/terrain_terminagotchi")
    for (i in 0 until Terrain.AIDE_AUTO) tape(listOf("date", "whoami", "ls", "pwd")[i % 4])
    verifier(Terrain.perdu(jeu) == null && File(T, "nid/repas.txt").isFile,
        "l'enfant n'y arrive pas : reconstruit tout seul après ${Terrain.AIDE_AUTO} commandes")
    tape("echo poire >> nid/repas.txt", T)
    verifier(Histoire.fini(jeu, "cave"), "la cave est réveillée malgré deux effacements")
    tape("cd ~/terrain_terminagotchi/grenier")
    verifier(Histoire.chap(jeu) == "grenier", "entrer dans le grenier le choisit")
    tape("ls -R", File(T, "grenier"))
    tape("mv fouillis/ours_en_peluche.txt ../nid/", File(T, "grenier"))
    verifier(lec() == ("t4" to 0), "grenier (copie) : on commence (l'ours a été remis après l'effacement)")
    tape("cp nid/repas.txt nid/secours.txt", T)
    File(T, "nid/secours.txt").delete()
    tape("ls", T)
    verifier(jeu.etape == 0 && "étape d'avant" in bulles(), "secours.txt effacé avant le mv : on refait l'étape d'avant")
    for (c in listOf("cp nid/repas.txt nid/secours.txt", "mv nid/secours.txt reserve.txt", "rm reserve.txt")) tape(c, T)
    verifier(Histoire.fini(jeu, "grenier") && Histoire.chapitreCourant(jeu) == null, "le grenier est réveillé")

    println("3. Premier dressage facile")
    val r = Explo.spawn(jeu)
    val d = dressage()
    verifier(r != null && d != null, "un monstre apparaît")
    val e = Bestiaire.espece(d!!.getString("espece"))!!
    val ind = d.getJSONObject("ind")
    verifier(e.frequence == "souvent" && ind.optString("rarete") == "commune", "premier monstre : ${e.nom} (${e.frequence}, ${ind.optString("rarete")})")
    val taches = liste(d.getJSONArray("taches"))
    verifier(taches.size == 2 && taches[0] == "Rencontre:examiner" && taches[1] in Dressage.SIMPLES, "2 épreuves simples : $taches")
    verifier(d.optInt("duree") == 0 && !d.has("combat"), "pas de chrono, pas de combat (troupe vide)")
    val champs = Tirage.tirer(GRAINE, ind.getLong("n"), false, ind.optString("attire").ifEmpty { null }).champs
    verifier(inclus(champs, ind), "vérifiable : (graine, compteur ${ind.getLong("n")}) refait exactement le même individu")
    val nom = e.id
    tape("cat ~/terrain_terminagotchi/monstre_${nom.dropLast(1)}.txt")
    verifier("monstre_$nom.txt" in dressage()!!.optString("indice"), "faute dans le nom : ${dressage()!!.optString("indice")}")
    tape("cat ~/terrain_terminagotchi/monstre_$nom.txt")
    verifier(liste(dressage()!!.getJSONArray("faites")) == listOf("Rencontre:examiner"), "fiche lue : 1re épreuve réussie")
    val ex = Dressage.exemple(jeu, Dressage.epreuve(taches[1])!!, e.nom)
    val rep = File(T, d.getString("zone") + "/repaire_" + e.id)
    tape(ex.split("    ")[0], rep)
    verifier(dressage() == null && Explo.captures(jeu).length() == 1, "2e épreuve ($ex) : première bestiole dressée !")

    println("   … puis la difficulté monte avec les captures")
    val moy = (0 until 14).map { n -> Bestiaire.publiques().map { Dressage.choisirEpreuves(it, false, "rare", n).size }.average() }
    verifier(moy.zipWithNext().all { (a, b) -> a <= b + 1e-9 }, "épreuves par dressage : " + moy.joinToString(" → ") { "%.1f".format(it) })
    // (le tirage des épreuves est au hasard : le niveau le plus haut vu sur 20 dressages)
    val niv = listOf(1, 4, 6, 9, 13).map { n -> (0 until 20).maxOf { Dressage.choisirEpreuves(Bestiaire.espece("Braisillon")!!, false, "épique", n).drop(2).maxOf { it.niveau } } }
    verifier(niv == niv.sorted() && niv.first() == 1 && niv.last() == 3, "niveau max des épreuves (1, 4, 6, 9, 13 captures) : $niv")
    val grib = Bestiaire.espece("Gribouilleur") ?: Bestiaire.publiques()[0]
    val avecFor = (0 until 14).filter { n -> (0 until 20).any { Dressage.choisirEpreuves(grib, false, "rare", n).any { it.cle == "Code:compte" } } }
    verifier(avecFor.none { it < 8 }, "pas de boucle for avant 8 captures")
    verifier((0 until 20).all { Dressage.choisirEpreuves(Bestiaire.espece("Braisillon")!!, false, "rare", 13).none { it.fam == "Processus" && it.id !in setOf("ps", "heure") } },
        "Processus : seulement ps et date (pas d'épreuve en arrière-plan sur le téléphone)")

    println("4. Attirance")
    val N = 1200
    val pourcents = LinkedHashMap<String, Pair<Double, Double>>()
    var verifiables = true
    for (fam in listOf("Démons", "Célestes")) {
        val cmd = Bestiaire.familles()[fam]!!
        tape(if (cmd != "ping") cmd else "ping -c 1 127.0.0.1")
        fun tirages(attirer: Boolean): Int {
            var n = 0
            for (i in 0 until N) {
                if (i % 150 == 0) Recensement.compte(jeu).put("apparitions", JSONObject())
                if (attirer) Explo.attirer(jeu, cmd, false)
                val (esp, v) = Explo.spawn(jeu)!!
                if (esp.famille == fam) n++
                val ch = Tirage.tirer(GRAINE, v.getLong("n"), false, v.optString("attire").ifEmpty { null }).champs
                if (!inclus(ch, v)) verifiables = false
                Dressage.abandonner(jeu)
            }
            return n
        }
        val a = 100.0 * tirages(false) / N
        val b = 100.0 * tirages(true) / N
        pourcents[fam] = a to b
        verifier(b > 2 * a, "$fam ($cmd) : %.1f %% sans attirance → %.1f %% avec ($N apparitions vérifiables)".format(a, b))
    }
    verifier(verifiables, "chaque apparition se refait à l'identique avec (graine, compteur, famille attirée)")
    // le même calcul sur PC (pc/outils/test_retours_enfants.py, même graine) : 10.0 → 29.3 et 6.7 → 28.7
    verifier("%.1f→%.1f".format(pourcents["Démons"]!!.first, pourcents["Démons"]!!.second) == "10.0→29.3" &&
        "%.1f→%.1f".format(pourcents["Célestes"]!!.first, pourcents["Célestes"]!!.second) == "6.7→28.7",
        "mêmes pourcentages que sur PC (Démons 10.0 → 29.3, Célestes 6.7 → 28.7)")
    verifier("ping" in jeu.vus, "la commande d'attirance fait partie des commandes goûtées (le serveur le vérifie)")
    tape("chmod 600 /dev/null 2>/dev/null; true")
    verifier(Explo.attirance(jeu) == "Démons", "taper chmod attire les Démons")
    verifier("Démons" in Explo.texteCollection(jeu), "la collection montre l'attirance du moment")

    println("5. Mini-combat")
    fun nouveauMonstre() {
        Dressage.abandonner(jeu)
        Explo.spawn(jeu)
    }
    nouveauMonstre()
    var dd = dressage()!!
    val cb = dd.optJSONObject("combat")
    val bete0 = Explo.captures(jeu).getJSONObject(0)
    verifier(cb != null && cb.getString("id") == bete0.getString("id"), "${bete0.optString("espece")} (troupe) affronte ${dd.getString("espece")}")
    val ecran = Dressage.panneau(jeu, android.content.res.Resources()).toString()
    val special = cb!!.getString("special")
    verifier("COMBAT" in ecran && "VS" in ecran && special.drop(1) in ecran && "attaque spéciale" in ecran && "observer" in ecran,
        "l'écran montre le combat et les 3 coups")
    println(ecran.lines().joinToString("\n") { "     $it" })
    val tachesAvant = liste(dd.getJSONArray("taches"))
    val peur = dd.optInt("mefiance")
    Combat.de = { 0.0 }                                           // tout touche
    for (i in 0 until 5) {
        tape(special)
        if (!Combat.enCours(jeu)) break
    }
    dd = dressage()!!
    val fin = dd.getJSONObject("combat")
    verifier(fin.optString("fin") == "gagne" && fin.optInt("tour") <= 5, "combat gagné en ${fin.optInt("tour")} tours")
    verifier(dd.optInt("mefiance") == peur - Combat.BAISSE_PEUR, "la peur baisse : $peur → ${dd.optInt("mefiance")}")
    val fam = tachesAvant.filter { !it.startsWith("Rencontre:") }
    verifier(dd.getJSONArray("taches").length() == tachesAvant.size - (if (fam.size >= 2) 1 else 0),
        "épreuves : ${tachesAvant.size} → ${dd.getJSONArray("taches").length()}")
    verifier(Combat.animTroupe?.second == "victoire", "animation de victoire demandée")
    verifier(dd.getJSONArray("lignes").length() == 0 && dd.getJSONArray("faites").length() == 0,
        "le dressage commence après le combat (les coups ne comptent pas)")
    verifier("attaque spéciale" !in Dressage.panneau(jeu, android.content.res.Resources()).toString(), "après le combat : le panneau du dressage revient")

    nouveauMonstre()
    var k = 0
    val suite = listOf(0.99, 0.0)                                 // tu rates, le monstre touche
    Combat.de = { suite[k++ % suite.size] }
    for (i in 0 until 5) {
        tape("date")
        if (!Combat.enCours(jeu)) break
    }
    val cbp = dressage()!!.getJSONObject("combat")
    val caps = Explo.captures(jeu)
    val bete = (0 until caps.length()).map { caps.getJSONObject(it) }.firstOrNull { it.optString("id") == cbp.getString("id") }
    verifier(cbp.optString("fin") == "perdu" && cbp.getJSONArray("moi").getInt(0) == 0, "combat perdu en ${cbp.optInt("tour")} tours")
    verifier(bete != null && Combat.repose(bete), "pas de mort : la bestiole est toujours là et se repose")
    verifier(Combat.animTroupe?.second == "ko", "animation « ko » demandée")
    val anim = Animations.pour(bete!!, "ko", Equipe.stade(bete), 3)
    verifier(anim != null && anim.first.size > 1, "l'animation ko existe pour ${bete.optString("espece")} (${anim?.first?.size} images, AnimAuto)")
    verifier((Animations.pour(bete, "dort", Equipe.stade(bete), 3)?.first?.size ?: 0) > 1, "puis elle s'endort (animation « dort »)")
    verifier("💤" in Equipe.texte(jeu), "la troupe montre qu'elle se repose")
    nouveauMonstre()
    verifier(dressage()?.has("combat") == false && "se repose" in bulles(), "toute la troupe se repose : pas de combat")
    Combat.de = { kotlin.random.Random.nextDouble() }

    println("6. Il manque quelque chose après la commande (mkdir tout seul…)")
    /** Comme le terminal de l'appli : la commande tourne (entrée fermée), puis l'aide lit la ligne ET la sortie. */
    fun tapeSortie(cmd: String): String {
        val pb = ProcessBuilder("bash", "-c", cmd).directory(T).redirectErrorStream(true)
        pb.environment()["HOME"] = jeu.home.absolutePath
        val p = pb.start()
        p.outputStream.close()
        val sortie = p.inputStream.readBytes().toString(Charsets.UTF_8).trimEnd()
        p.waitFor()
        val aide = Exemples.apres(jeu, cmd, sortie)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = T)
        return aide ?: ""
    }
    fun viderBulles() { jeu.bulle = ""; jeu.bulles.clear() }
    viderBulles()
    val aideMkdir = tapeSortie("mkdir")
    verifier("Il manque le nom" in bulles() && "Essaie : mkdir " in bulles(), "mkdir seul → bulle : ${bulles()}")
    verifier("Essaie : mkdir " in Vert.sansMarques(aideMkdir), "… et la même aide écrite dans le terminal (sous la sortie)")
    viderBulles()
    tapeSortie("cp nid/repas.txt")
    verifier("DEUX noms" in bulles() && "cp nid/repas.txt copie.txt" in bulles(), "cp avec un seul nom → ${bulles()}")
    viderBulles()
    tapeSortie("mkdir cabane_test")
    tapeSortie("ls -l | grep repas")
    verifier("✍" !in bulles(), "commande complète (ou avec un tuyau) → pas d'aide")
    verifier(Exemples.texte(jeu, "mkdir a b", "mkdir: missing operand") != null, "la sortie « missing operand » suffit aussi")
    verifier(Exemples.texte(jeu, "nano", "sh: nano: not found") == null, "commande absente du téléphone → pas d'aide (le terminal le dit déjà)")
    for (c in listOf("mkdir", "touch", "cat", "cp", "mv", "rm", "rmdir", "grep", "chmod", "head", "tail", "wc", "find", "kill",
            "ping", "ssh", "curl", "nano", "less"))
        verifier(Exemples.manque(c) == c && Exemples.texte(jeu, c) != null, "$c seul : aide prévue")

    // les exemples du lexique marchent vraiment depuis le terrain de jeu (dans l'ordre du lexique)
    File(T, "nid/repas.txt").setWritable(true)                // la leçon des droits l'a mis sous cadenas
    val shellables = setOf("lex.ch.fichiers", "lex.ch.lire", "lex.ch.systeme")
    val lancees = Regles.LEXIQUE.filter { it.sectionCle in shellables }.mapNotNull { Exemples.lexique(it) }
        .flatMap { it.split(" · ") }.toMutableList()
    for (r in Exemples.REGLES.values) if (r.ex !in lancees) lancees.add(r.ex)
    val horsLigne = setOf("ping", "curl", "nslookup", "ssh", "kill", "nano", "git", "less")   // réseau, NUMÉRO, absentes du téléphone
    for (ex in lancees) {
        if (ex.split(" ")[0] in horsLigne) continue
        val pb = ProcessBuilder("bash", "-c", ex).directory(T).redirectErrorStream(true)
        pb.environment()["HOME"] = jeu.home.absolutePath
        val p = pb.start()
        p.outputStream.close()
        val sortie = p.inputStream.readBytes().toString(Charsets.UTF_8).trim()
        val code = p.waitFor()
        verifier(code == 0 && Exemples.manque(ex) == null, "exemple « $ex » : marche depuis le terrain" + if (code == 0) "" else " ✖ $sortie")
    }
    val lexMkdir = Regles.LEXIQUE.first { it.cmd == "mkdir" }
    verifier(Exemples.lexique(lexMkdir) == "mkdir cabane", "lexique : mkdir → ↳ exemple : mkdir cabane")
    verifier(Regles.LEXIQUE.filter { it.cmd == "carte" }.map { Exemples.lexique(it) } == listOf("carte tour eiffel", null),
        "carte (téléphone) → carte tour eiffel ; carte (la maison) : rien à ajouter")

    println("7. Les commandes à taper, en vert")
    viderBulles()
    tapeSortie("mkdir")
    val (lu, verts) = Vert.passages(jeu.bulle)
    verifier(verts.map { lu.substring(it.first, it.second) } == listOf("mkdir", "mkdir cabane"),
        "bulle « mkdir » : en vert ${verts.map { lu.substring(it.first, it.second) }}, le reste dans la couleur de la bulle")
    verifier("`" !in lu && lu.contains("Essaie : mkdir cabane"), "à l'écran, plus de backticks ; les caractères de la commande sont intacts")
    val lecon = jeu.texteLecon() ?: ""
    verifier(Vert.passages(lecon).second.isNotEmpty(), "la leçon montre sa commande (➜ …) en vert")
    val exLex = Vert.passages(t("lex.exemple", "ex" to "mkdir cabane"))
    verifier(exLex.second.size == 1 && exLex.first.substring(exLex.second[0].first, exLex.second[0].second) == "mkdir cabane",
        "lexique : « ${exLex.first} » avec mkdir cabane en vert")
    Langue.definir("ar")
    val ar = t("aide.manque.mkdir", "cmd" to "mkdir", "ex" to "mkdir cabane", "un_dossier" to "غرفة")
    val (arLu, arVerts) = Vert.passages(ar)
    verifier(arVerts.size == 2 && arVerts.all { (a, b) -> arLu[a] == '\u2066' && arLu[b - 1] == '\u2069' } &&
        arVerts.map { (a, b) -> arLu.substring(a + 1, b - 1) } == listOf("mkdir", "mkdir cabane"),
        "arabe : chaque commande verte est isolée de gauche à droite (LRI … PDI), sans changer ses caractères")
    Langue.definir("fr")

    println("8. Expliquer chaque commande et ses options (enfant, puis pour les grands)")
    val vuesOpt = jeu.module("explique").optJSONArray("vues")?.toString() ?: ""
    verifier("recursif_rm" in vuesOpt, "« rm -r vieille_cabane » réussi : le -r a été expliqué (et retenu)")
    verifier(Explique.options("ps aux | wc -l") == listOf("aux" to "aux", "|" to "tuyau", "-l" to "lignes"),
        "options repérées dans « ps aux | wc -l » : aux, |, -l")
    val ficheRm = Vert.sansMarques(Explique.fiche(jeu, "rm"))
    verifier("« récursif »" in ficheRm && "--recursive" in ficheRm && "Pour les grands" in ficheRm && "rmdir" in ficheRm,
        "explique rm : image, -r (« récursif » / --recursive), pour les grands, différences avec rmdir")
    verifier(Explique.fiche(jeu, "zorglub").contains("zorglub"), "explique d'une commande inconnue : un message clair")

    println("\n$ok réussis, $ko échoués")
    System.exit(if (ko > 0) 1 else 0)
}
