/*
 * Test JVM (hors téléphone) de la salle d'entraînement, portage de pc/outils/test_entrainement.py : tirage commun
 * (donnees/entrainement/vecteurs.json), chaque exercice fait avec les vraies commandes (bash) dans la salle du terrain,
 * puis le tour de jeu (Tour.apresCommande) ; badges, grades (Bit → Giga), galons, étoiles, titres, Star de la semaine, synchro.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Entrainement.kt -d entrainement.jar
 *   java -cp <imitations>:<appli.jar>:entrainement.jar:kotlin-stdlib.jar EntrainementKt app/src/main/assets donnees/entrainement/vecteurs.json
 */
import fr.terminagotchi.Badges
import fr.terminagotchi.Entrainement
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
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

var ok = 0
var ko = 0

fun verifier(c: Boolean, m: String) {
    if (c) ok++ else ko++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeu: Jeu
lateinit var shell: Shell
val T: File get() = jeu.terrain
val S: File get() = Entrainement.salle(jeu)

fun bash(cmd: String, ou: File): String {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeu.home.absolutePath
    val p = pb.start()
    val out = p.inputStream.readBytes().toString(Charsets.UTF_8)
    p.waitFor()
    return out
}

/** L'enfant tape une commande dans la salle : « cd » par Shell.kt, le reste vraiment (bash), puis le tour de jeu. */
fun tape(cmd: String, ou: File = S): Tour.Resultat {
    shell.dossier = ou
    if (cmd.trim().startsWith("cd ")) shell.executer(cmd) else bash(cmd, ou)
    return Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
}

fun cours(): JSONObject? = Entrainement.e(jeu).optJSONObject("cours")

fun lancer(typ: String): Entrainement.Params {
    Entrainement.commencer(jeu, typImpose = typ)
    val c = cours()!!
    c.put("debut", c.getLong("debut") - 3000)
    return Entrainement.generer(typ, c.getString("v"), c.getLong("n"))
}

fun texte(s: String) = Vert.sansMarques(s)

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_entrainement_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilT(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    shell = Shell(jeu.home)

    println("Vecteurs communs (donnees/entrainement/vecteurs.json)")
    val v = JSONObject(File(args[1]).readText())
    val ex = v.getJSONArray("exercices")
    var pareils = 0
    val rates = mutableListOf<String>()
    for (i in 0 until ex.length()) {
        val x = ex.getJSONObject(i)
        val typ = x.getString("type")
        val p = Entrainement.generer(typ, x.getString("valeur"), x.getLong("k"))
        val rep = if (x.isNull("reponse")) null else x.getString("reponse")
        if (p.empreinte(typ) == x.getString("empreinte") && Entrainement.reponse(typ, p) == rep) pareils++
        else rates.add("$typ#${x.getLong("k")} : ${p.empreinte(typ)} ≠ ${x.getString("empreinte")}")
    }
    verifier(pareils == ex.length(), "$pareils/${ex.length()} exercices identiques au Python")
    rates.take(3).forEach { println("      $it") }
    val med = v.getJSONArray("medailles")
    verifier((0 until med.length()).all { med.getJSONObject(it).let { m -> Entrainement.medaille(m.getString("type"), m.getDouble("t")) == m.getString("medaille") } },
        "${med.length()} médailles identiques")
    val ech = v.getJSONArray("echelons")
    verifier((0 until ech.length()).all { ech.getJSONObject(it).let { m -> Badges.echelonDe(m.getInt("n"), m.getInt("or"), m.getInt("diamant")) == m.getInt("echelon") } },
        "grades identiques (Giga : une médaille d'or ; Téra : 3 de diamant)")
    verifier((0 until ech.length()).all { ech.getJSONObject(it).let { m -> Badges.etoilesDe(m.getInt("n"), m.getInt("echelon")) == m.getInt("etoiles") } },
        "étoiles identiques (au Téra : 150 / 200 / 300)")
    val ecu = v.getJSONArray("ecussons")
    fun empreinte(g: List<List<String?>>): String = java.security.MessageDigest.getInstance("SHA-256")
        .digest(g.joinToString("/") { l -> l.joinToString(",") { it ?: "" } }.toByteArray()).joinToString("") { "%02x".format(it) }
    verifier((0 until ecu.length()).all { ecu.getJSONObject(it).let { m ->
        empreinte(Badges.ecusson(if (m.isNull("famille")) null else m.getString("famille"),
            if (m.isNull("echelon")) null else m.getString("echelon"), m.getInt("etoiles"))) == m.getString("empreinte") } },
        "${ecu.length()} badges complets identiques au pixel près (galons, étoiles)")
    val px = Badges.ECHELONS.map { e -> Badges.galons(e).sumOf { l -> l.count { it != null } } }
    verifier(px == px.sorted() && px.toSet().size == 6, "les galons grandissent à chaque grade ($px)")
    verifier(Entrainement.migrerTitre("explorateur:argent") == "explorateur:kilo" && Entrainement.migrerTitre("touche") == "touche",
        "vieille sauvegarde : « Explorateur d'Argent » devient « Explorateur Kilo »")
    val sem = v.getJSONArray("semaines")
    verifier((0 until sem.length()).all { sem.getJSONObject(it).let { m -> Entrainement.semaine(m.getLong("t") * 1000) == m.getString("semaine") } },
        "semaines ISO identiques")
    verifier(Badges.grille("explorateur", "giga")[1][12] == "#ffffff" && Badges.grille(null, null)[0][3] == "#3a3a44",
        "les dessins des badges (étincelle du Giga, « ??? » gris)")

    println("Avant le terrain, avant les commandes")
    verifier("première leçon" in texte(Entrainement.commande(jeu, "", shell.dossier)), "pas de terrain : on continue la première leçon")
    File(T, "nid").mkdirs()
    File(T, "nid/lit.txt").writeText("doux\n")
    verifier("premières commandes" in texte(Entrainement.commande(jeu, "", shell.dossier)), "aucune commande connue : la salle attend gentiment")
    verifier(Regex("¤badge:cache:cache¤").findAll(Entrainement.ecranBadges(jeu)).count() == 8, "les 8 badges sont cachés (« ??? »)")

    println("Explorateur : le dossier courant")
    jeu.vus.add("cd")
    verifier(Entrainement.famillesOuvertes(jeu) == listOf("explorateur"), "cd tapé : seule la famille Explorateur s'ouvre")
    verifier("encore caché" in texte(Entrainement.commande(jeu, "batisseur", shell.dossier)), "une famille fermée reste cachée, sans reproche")
    val r0 = texte(Entrainement.commande(jeu, "", shell.dossier))
    verifier("Salle d'entraînement" in r0 && "salle_entrainement" in r0, "un exercice commence : " + r0.lines()[1].take(60))
    val c0 = cours()!!
    val p0 = Entrainement.generer(c0.getString("type"), c0.getString("v"), c0.getLong("n"))
    val cible = File(S, "${p0.pieces[p0.i]}/${p0.coins[p0.j]}")
    verifier(cible.isDirectory, "la salle est préparée dans le terrain")
    val xp0 = jeu.xp
    val res = tape("cd ${cible.absolutePath}")
    verifier(cours() == null && res.messages.any { "Bravo" in it.first }, "être dans la bonne pièce réussit l'exercice")
    verifier(Entrainement.fam(Entrainement.e(jeu), "explorateur").optInt("n") == 1 && jeu.xp > xp0, "1 réussite et de l'XP pour la créature")
    verifier(Entrainement.titreAffiche(jeu)?.texte == "Élève de la salle", "premier titre : « Élève de la salle »")
    verifier("Élève de la salle" in jeu.titre(), "le titre est à côté du nom dans l'en-tête")
    verifier(File(T, "nid/lit.txt").isFile, "rien n'est touché hors de la salle d'entraînement")

    println("Chaque exercice, pour de vrai")
    jeu.vus.addAll(listOf("ls", "mkdir", "touch", "cp", "mv", "rm", "rmdir", "cat", "head", "tail", "grep", "find", "echo", "wc", "sh", "chmod"))
    tape("echo a >> /dev/null | cat", S.parentFile)
    verifier(Entrainement.famillesOuvertes(jeu) == Badges.FAMILLES, "toutes les commandes connues (et > >> | repérés) : les 8 familles")
    for ((typ, ty) in Entrainement.TYPES) {
        val p = lancer(typ)
        if (ty.reponse) {
            val bon = Entrainement.reponse(typ, p)!!
            val sortie = bash(Entrainement.idees(typ, p).last(), S)
            verifier(bon in sortie.lowercase() || (typ == "det_grep" && "$bon.txt" in sortie) || typ == "det_find" && bon in sortie,
                "$typ : la commande d'idée montre la réponse ($bon)")
            val faux = texte(Entrainement.commande(jeu, "zzz", S))
            val r = texte(Entrainement.commande(jeu, bon + (if (typ == "det_grep") ".txt" else ""), S))
            verifier("Pas tout à fait" in faux && "Bravo" in r, "$typ : mauvaise réponse gentille, puis bonne réponse")
            continue
        }
        if (typ == "exp_chemin" || typ == "exp_cle") {
            tape("cd ${p.pieces[p.i]}/${p.coins[p.j]}", S)
        } else {
            val cmds = Entrainement.idees(typ, p) + (if (typ == "bat_objets") listOf("touch ${p.pieces[0]}/${p.objets[1]}.txt") else listOf())
            for (x in cmds.dropLast(1)) bash(x, S)
            verifier(cours() != null, "$typ : pas réussi avant la dernière commande")
            tape(cmds.last(), S)
        }
        verifier(cours() == null, "$typ (${ty.famille}) réussi avec ${Entrainement.idees(typ, p).joinToString(", ")}")
    }

    println("Pas de punition")
    val pr = lancer("net_rm")
    File(S, "${pr.pieces[0]}/${pr.objets[0]}.txt").delete()
    val oups = tape("ls")
    verifier(cours() != null && oups.messages.any { "pas grave" in it.first }, "l'objet à garder est effacé : un « oups » gentil")
    verifier("rangé" in texte(Entrainement.commande(jeu, "fin", S)) && cours() == null, "entrainement fin range l'exercice")
    val pc = lancer("lec_cat")
    verifier("collée" in texte(Entrainement.commande(jeu, "а" + pc.mots[0].drop(1), S)) && cours() != null,
        "une réponse collée (piégée) ne compte pas")
    Entrainement.commande(jeu, "fin", S)

    println("La salle reste dans le terrain")
    S.deleteRecursively()
    val dehors = File(dossier, "dehors").apply { mkdirs() }
    File(dehors, "precieux.txt").writeText("à garder")
    java.nio.file.Files.createSymbolicLink(S.toPath(), dehors.toPath())
    val r1 = texte(Entrainement.commencer(jeu, "batisseur"))
    verifier(File(dehors, "precieux.txt").isFile && "préparer" in r1, "une salle remplacée par un lien : on ne touche à rien")
    S.delete()

    println("Badges et échelons")
    fun regler(f: String, n: Int, ors: Int = 0) {
        Entrainement.fam(Entrainement.e(jeu), f).put("n", n).put("bronze", n - ors).put("argent", 0).put("or", ors).put("diamant", 0)
    }
    regler("batisseur", 4)
    lancer("bat_pieces")
    val pb = Entrainement.generer("bat_pieces", cours()!!.getString("v"), cours()!!.getLong("n"))
    bash("mkdir ${pb.pieces[0]}", S)
    val monte = tape("mkdir ${pb.pieces[1]}")
    verifier(Entrainement.echelon(Entrainement.e(jeu), "batisseur") == 1 && monte.messages.any { "¤badge:batisseur:octet~0¤" in it.first },
        "5e réussite : badge Bâtisseur en Octet (avec son image)")
    regler("nettoyeur", 50, 0)
    verifier(Entrainement.echelon(Entrainement.e(jeu), "nettoyeur") == 3, "50 réussites sans médaille d'or : encore Méga")
    regler("nettoyeur", 50, 1)
    verifier(Entrainement.echelon(Entrainement.e(jeu), "nettoyeur") == 4, "… avec une médaille d'or : Giga")
    val ecran = Entrainement.ecranBadges(jeu)
    verifier("¤badge:nettoyeur:giga~0¤" in ecran && "Giga ☆☆☆" in ecran && "Octet" in ecran && "50/100 → Téra" in ecran,
        "badges : une image complète, le grade et ses étoiles par famille")
    verifier(Entrainement.titreAffiche(jeu)?.texte == "Nettoyeur Giga", "le titre affiché est le plus beau : « Nettoyeur Giga »")
    verifier("`badges grades`" in ecran && "8 bits" in Entrainement.commandeBadges(jeu, "grades")
        && Regex("¤badge:explorateur:[a-z]+~0¤").findAll(Entrainement.commandeBadges(jeu, "grades")).count() == 6
        && "bibliothèque de films" in Entrainement.commandeBadges(jeu, "grades"),
        "badges grades : les 6 grades, leurs galons et ce qu'ils veulent dire")
    regler("cuisinier", 100, 1)
    verifier("💎 0/3" in Entrainement.ecranBadges(jeu), "100 réussites sans 3 médailles de diamant : encore Giga (💎 0/3)")
    Entrainement.fam(Entrainement.e(jeu), "cuisinier").put("diamant", 3)
    verifier(Entrainement.echelon(Entrainement.e(jeu), "cuisinier") == 5 && "¤badge:cuisinier:tera~0¤" in Entrainement.ecranBadges(jeu)
        && Entrainement.titres(jeu).any { it.texte == "Cuisinier Téra" }, "… avec 3 médailles de diamant : Téra (« Cuisinier Téra »)")
    regler("cuisinier", 0)
    regler("plombier", 9)
    verifier("¤badge:plombier:octet~1¤" in Entrainement.ecranBadges(jeu) && "9/15 → Kilo" in Entrainement.ecranBadges(jeu), "9 réussites : Octet ★☆☆, 9/15 → Kilo")
    regler("plombier", 0)
    val liste = texte(Entrainement.ecranTitres(jeu, null))
    val n = liste.lines().indexOfFirst { "Élève de la salle" in it }
    Entrainement.ecranTitres(jeu, n.toString())
    verifier(Entrainement.titreAffiche(jeu)?.texte == "Élève de la salle", "on choisit son titre (badges titre $n)")
    Entrainement.ecranTitres(jeu, "auto")
    verifier(Entrainement.titreAffiche(jeu)?.texte == "Nettoyeur Giga", "auto : le plus beau titre revient")
    for (f in Badges.FAMILLES) regler(f, 30, 1)
    verifier(Entrainement.titreAffiche(jeu)?.couleur == "arc" && "§« Légende de la salle »§" in Entrainement.ecranBadges(jeu),
        "8 familles en Méga : « Légende de la salle » (arc-en-ciel)")

    println("Star de la semaine (gardée une semaine)")
    Entrainement.e(jeu).put("hebdo", JSONObject().put("semaine", Entrainement.semainePrecedente()).put("familles", JSONArray().put("lecteur")))
    verifier(Entrainement.titres(jeu).any { it.id == "star:lecteur" }, "gagnée la semaine dernière : affichée cette semaine")
    Entrainement.e(jeu).put("hebdo", JSONObject().put("semaine", Entrainement.semaine(System.currentTimeMillis() - 14 * 86_400_000L))
        .put("familles", JSONArray().put("lecteur")))
    verifier(Entrainement.titres(jeu).none { it.id.startsWith("star:") }, "la semaine d'après, elle disparaît")

    println("Synchro")
    val (charge, snap) = Entrainement.charge(jeu, JSONObject().put("lecteur", JSONObject().put("n", 10)))
    verifier(charge.getJSONObject("deltas").getJSONObject("lecteur").getInt("n") == 20, "les compteurs partent en différence")
    val runs = charge.getJSONArray("runs")
    verifier(runs.length() > 15 && (0 until runs.length()).all { i -> listOf("id", "type", "g", "n", "t", "d", "e").all { runs.getJSONObject(i).has(it) } },
        "${runs.length()} exercices à vérifier (type, graine, compteur, temps, empreinte)")
    val typ = Entrainement.e(jeu).getJSONObject("records").keys().next()
    val tRec = Entrainement.e(jeu).getJSONObject("records").getJSONObject(typ).getDouble("t")
    val srv = JSONObject().put("familles", JSONObject().apply { for (f in Badges.FAMILLES) put(f, JSONObject().put("n", 100).put("or", 1)) })
        .put("records", JSONObject().put(typ, JSONObject().put("t", tRec).put("v", true)))
    Entrainement.appliquer(jeu, srv, snap, runs, JSONObject().put("compte", JSONObject().put("lecteur", 2)))
    verifier(Entrainement.fam(Entrainement.e(jeu), "lecteur").getInt("n") == 100 && Entrainement.e(jeu).getJSONArray("envoyer").length() == 0,
        "les compteurs communs reviennent, les exercices envoyés sont oubliés")
    verifier(Entrainement.e(jeu).getJSONObject("records").getJSONObject(typ).getBoolean("v"), "record vérifié par le site")
    verifier("2 fois" in Entrainement.ecranBadges(jeu) && "vérifié" in Entrainement.ecranRecords(jeu), "compteur des Stars et records")
    jeu.vus.remove("find")
    verifier(Entrainement.vert(jeu, "ls").startsWith("`") && !Entrainement.vert(jeu, "find . -name x").startsWith("`"),
        "en vert seulement les commandes déjà rencontrées")
    verifier(Langue.t("ent.aide.tel").startsWith("🏋"), "l'aide du téléphone parle de la salle d'entraînement")

    println()
    println("$ok réussis, $ko échoués")
    if (ko > 0) System.exit(1)
}
