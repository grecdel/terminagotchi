/*
 * Test JVM (hors téléphone) des retours des enfants de 7 ans, portage de pc/outils/test_retours_enfants.py :
 *   1. leçons : « pome » au lieu de « pomme » → indice clair, la leçon attend la bonne commande ;
 *   2. terrain effacé (rm -rf) → bulle + bandeau avec la commande ; reconstruit → la leçon reprend au bon
 *      endroit (repas.txt remis) ; si l'enfant n'y arrive pas, le jeu reconstruit lui-même après 12 commandes ;
 *   3. premier dressage : un monstre courant et commun, 2 épreuves simples, indice « presque », tirage toujours
 *      vérifiable (graine, compteur) ; puis la difficulté monte avec les captures ;
 *   4. attirance : sur 1200 apparitions vérifiables, la famille attirée sort vraiment plus souvent (≈ 29 %, comme le PC) ;
 *   5. mini-combat : gagné (peur −40, une épreuve en moins), puis perdu (KO, repos, pas de mort).
 *
 * De vraies commandes sont lancées avec bash (HOME = la maison de l'appli), puis le jeu fait le même tour
 * qu'après une commande tapée dans le terminal de l'appli (Tour.apresCommande).
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
import fr.terminagotchi.Explo
import fr.terminagotchi.Animations
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Recensement
import fr.terminagotchi.Terrain
import fr.terminagotchi.Tirage
import fr.terminagotchi.Tour
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
val T: File get() = jeu.terrain

/** L'enfant tape une commande : elle s'exécute vraiment (bash), puis le jeu fait son tour. */
fun tape(cmd: String, ou: File = jeu.home) {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeu.home.absolutePath
    val p = pb.start()
    p.inputStream.readBytes()
    p.waitFor()
    Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false)
}

fun bulles() = (listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | ")

/** Les champs tirés de la graine sont tous dans l'individu, avec les mêmes valeurs. */
fun inclus(champs: JSONObject, ind: JSONObject) = champs.keys().asSequence().all { k -> ind.has(k) && ind.get(k).toString() == champs.get(k).toString() }

fun dressage(): JSONObject? = jeu.module("dressage").optJSONObject("en_cours")
fun liste(a: JSONArray?) = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_retours_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilR(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    // pas d'ouverture automatique de l'exploration pendant le test : les monstres sont appelés exprès (Explo.spawn)
    jeu.module("explo").put("ouverte", true)
    val jour = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
    Tirage.rangerGraines(jeu, JSONArray().put(JSONObject().put("id", "$jour.abcdef123456").put("valeur", GRAINE)))

    for (c in listOf("pwd", "ls", "cd ~")) tape(c)
    for (c in listOf("mkdir terrain_terminagotchi", "cd terrain_terminagotchi")) tape(c)
    tape("mkdir nid", T)
    verifier(jeu.lecon == 2 && "Bâtisseur" in jeu.skills, "tronc commun : leçon 1 finie (terrain et nid construits)")

    println("1. Leçons : un indice quand c'est presque ça")
    tape("echo pome > nid/repas.txt", T)
    verifier(jeu.lecon == 2 && jeu.etape == 0, "« pome » : la leçon attend encore la bonne commande")
    val il = jeu.indiceLecon ?: ""
    verifier("pome" in il && "pomme" in il, "indice : $il")
    verifier("💡 Presque" in (jeu.texteLecon() ?: ""), "l'indice s'affiche sous la leçon")
    tape("echo pomme > nid/repas.txt", T)
    verifier(jeu.etape == 1 && jeu.indiceLecon == null, "« pomme » : étape réussie, l'indice disparaît")
    tape("cat nid/repas.txt", T)
    tape("grep pome nid/repas.txt", T)
    verifier(jeu.etape == 2 && "« pome »" in (jeu.indiceLecon ?: ""), "grep pome : indice, pas de silence")
    tape("grep pomme nid/repas.txt", T)
    verifier(jeu.lecon == 3, "leçon 2 finie")
    tape("ls -l nid", T)
    verifier(jeu.lecon == 3 && jeu.etape == 1, "leçon 3 (droits) : on en est à chmod 444 nid/repas.txt")
    tape("chmod 444 nid/repas.tx", T)
    verifier("repas.tx »" in (jeu.indiceLecon ?: ""), "chmod 444 nid/repas.tx : ${jeu.indiceLecon}")

    println("2. Terrain effacé")
    tape("rm -rf ~/terrain_terminagotchi")
    verifier(Terrain.perdu(jeu) == "mkdir -p ~/terrain_terminagotchi/nid", "détecté : la commande proposée est « ${Terrain.perdu(jeu)} »")
    verifier("mkdir -p ~/terrain_terminagotchi/nid" in bulles(), "une bulle claire donne la commande")
    val bandeau = Terrain.bandeau(jeu) ?: ""
    verifier("➜ mk" in bandeau && "~/terrain_terminagotchi/nid" in bandeau, "le bandeau (avec la commande) reste sur l'écran principal")
    verifier(!Explo.debloquee(jeu), "pas de monstre tant que le nid n'existe pas")
    tape("mkdir -p ~/terrain_terminagotchi/nid")
    verifier(Terrain.perdu(jeu) == null && Terrain.bandeau(jeu) == null, "reconstruit : plus d'alerte")
    verifier(File(T, "nid/repas.txt").isFile, "repas.txt remis pour que la leçon continue")
    verifier(jeu.lecon == 3 && jeu.etape == 1, "la leçon reprend au bon endroit (chmod 444)")
    tape("chmod 444 nid/repas.txt", T)
    verifier(jeu.lecon == 3 && jeu.etape == 2, "chmod 444 : réussi après la reconstruction")
    tape("rm -rf ~/terrain_terminagotchi")
    for (i in 0 until Terrain.AIDE_AUTO) tape(listOf("date", "whoami", "ls", "pwd")[i % 4])
    verifier(Terrain.perdu(jeu) == null && File(T, "nid/repas.txt").isFile,
        "l'enfant n'y arrive pas : reconstruit tout seul après ${Terrain.AIDE_AUTO} commandes")
    tape("echo poire >> nid/repas.txt", T)
    verifier(jeu.lecon == 4, "leçon 3 finie malgré deux effacements")
    verifier(jeu.lecon == 4 && jeu.etape == 0, "leçon 4 (copie) : on commence")
    tape("cp nid/repas.txt nid/secours.txt", T)
    File(T, "nid/secours.txt").delete()
    tape("ls", T)
    verifier(jeu.etape == 0 && "étape d'avant" in bulles(), "secours.txt effacé avant le mv : on refait l'étape d'avant")
    for (c in listOf("cp nid/repas.txt nid/secours.txt", "mv nid/secours.txt reserve.txt", "rm reserve.txt")) tape(c, T)
    verifier(jeu.troncFini, "tronc commun fini")

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
    val niv = listOf(1, 4, 6, 9, 13).map { n -> Dressage.choisirEpreuves(Bestiaire.espece("Braisillon")!!, false, "épique", n).drop(2).maxOf { it.niveau } }
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

    println("\n$ok réussis, $ko échoués")
    System.exit(if (ko > 0) 1 else 0)
}
