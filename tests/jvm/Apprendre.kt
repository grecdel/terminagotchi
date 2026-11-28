/*
 * Test JVM d'« apprendre en jouant » (idées du 3 novembre) sur Android, portage de pc/outils/test_apprendre.py :
 *   1. les vecteurs communs donnees/apprendre/vecteurs.json (graine FNV, commande du jour, révisions, maîtrise, énigme
 *      de la semaine, limite de temps) : mêmes résultats qu'en Python ;
 *   2. chaque idée jouée comme dans l'appli (vraies commandes dans bash, dans le terrain ; Tour.apresCommande) ;
 *   3. les écrans dans les 14 langues, le diplôme dessiné (900 × 630), rien hors du terrain.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Apprendre.kt -d apprendre.jar
 *   java -cp <imitations>:<appli.jar>:apprendre.jar:kotlin-stdlib.jar ApprendreKt app/src/main/assets
 */
import fr.terminagotchi.Apprendre
import fr.terminagotchi.ApprendreDessin
import fr.terminagotchi.Commandes
import fr.terminagotchi.Entrainement
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Satiete
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsAp(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilAp(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsAp(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okAp = 0
var koAp = 0
fun verifierAp(c: Boolean, m: String) { if (c) { okAp++; println("  ✔ $m") } else { koAp++; println("  ✖ $m") } }
fun lstAp(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

lateinit var jeuAp: Jeu
lateinit var shellAp: Shell
lateinit var cmdAp: Commandes

/** Une commande comme dans l'appli : intégrée (Commandes), cd (Shell), sinon un vrai bash dans le dossier courant. */
fun tapeAp(cmd: String): Pair<String, String> {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") { shellAp.executer(cmd); code = shellAp.code }
    else {
        val interne = cmdAp.executer(cmd)
        if (interne != null) sortie = interne.texte
        else {
            val pb = ProcessBuilder(listOf("bash", "-c", cmd)).directory(shellAp.dossier).redirectErrorStream(true)
            pb.environment()["HOME"] = jeuAp.home.absolutePath
            pb.environment()["LC_ALL"] = "C.UTF-8"
            val p = pb.start(); p.outputStream.close()
            sortie = p.inputStream.readBytes().toString(Charsets.UTF_8); code = p.waitFor()
        }
    }
    val r = Tour.apresCommande(jeuAp, cmd, colle = false, rappel = false, hasard = false, cwd = shellAp.dossier, code = code)
    return sortie to r.messages.joinToString("\n") { it.first }
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_ap_" + System.nanoTime()).apply { mkdirs() }
    java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"))
    val app = AppareilAp(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuAp = Jeu(app)
    jeuAp.changerLangue("fr")
    jeuAp.nom = "Pixel"
    jeuAp.module("intro").put("etat", "fini")
    jeuAp.module("debloc").put("mode", "tout")
    jeuAp.vus.addAll(listOf("pwd", "ls", "cd", "cat"))
    shellAp = Shell(jeuAp.home)
    cmdAp = Commandes(app, jeuAp, { shellAp.dossier })
    val T = jeuAp.terrain
    T.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/apprendre/vecteurs.json").readText())
    fun tous(k: String, f: (JSONArray) -> Boolean): Pair<Boolean, String> {
        val a = v.getJSONArray(k)
        val faux = (0 until a.length()).map { a.getJSONArray(it) }.filterNot(f)
        return faux.isEmpty() to (faux.firstOrNull()?.toString()?.take(120) ?: "")
    }
    var r = tous("fnv") { Apprendre.fnv(it.getString(0)) == it.getLong(1) }
    verifierAp(r.first, "FNV-1a 32 bits (la graine du jour) ${r.second}")
    r = tous("jours_entre") { Apprendre.joursEntre(it.getString(0), it.getString(1)) == it.getInt(2) }
    verifierAp(r.first, "jours entre deux dates ${r.second}")
    r = tous("intervalle") { Apprendre.intervalle(it.getInt(0)) == it.getInt(1) }
    verifierAp(r.first, "intervalles des révisions 1, 3, 7, 14, 30 ${r.second}")
    r = tous("jour") { Apprendre.commandeDuJour(it.getString(0), lstAp(it.getJSONArray(1)).toSet()) == it.getString(2) }
    verifierAp(r.first, "la commande du jour (même graine pour tous) ${r.second}")
    r = tous("revision") { (Apprendre.revisionDue(it.getJSONObject(0), it.getString(1)) ?: "null") == (if (it.isNull(2)) "null" else it.getString(2)) }
    verifierAp(r.first, "la révision due ${r.second}")
    r = tous("maitrise") { Apprendre.niveauMaitrise(it.getJSONArray(0), it.getBoolean(1)) == it.getInt(2) }
    verifierAp(r.first, "les trois ronds de maîtrise ${r.second}")
    r = tous("enigme") { val e = Apprendre.enigme(it.getString(0), lstAp(it.getJSONArray(1)).toSet()); val x = it.getJSONArray(2)
        e.first == x.getString(0) && e.second == x.getString(1) && e.third == x.getInt(2) }
    verifierAp(r.first, "l'énigme de la semaine ${r.second}")
    r = tous("temps") { Apprendre.etatTemps(it.getDouble(0), if (it.isNull(1)) null else it.getInt(1)) == it.getString(2) }
    verifierAp(r.first, "la limite de temps douce (bâille, dort, pause) ${r.second}")
    verifierAp(File(depot, "pc/tg/apprendre.json").readText() == File(assets, "apprendre.json").readText(), "apprendre.json : PC et Android égaux")

    println("27. Le bac à sable")
    val o = tapeAp("bac-a-sable").first
    verifierAp("bac_a_sable" in o && File(T, "bac_a_sable/chateau/donjon.txt").exists(), "bac-a-sable : le dossier et ses jouets")
    shellAp.dossier = T
    val x0 = jeuAp.xp
    var (_, msg) = tapeAp("cd bac_a_sable")
    verifierAp("Bac à sable" in msg, "le bandeau en entrant")
    for (l in listOf("ls", "mkdir -p tour/haute", "head recette.txt", "sort recette.txt", "rm coffre.txt")) tapeAp(l)
    verifierAp(jeuAp.xp == x0 && "head" in jeuAp.vus && Apprendre.a(jeuAp).getJSONObject("maitrise").optJSONArray("head") == null,
        "rien ne compte (XP ${jeuAp.xp}), une commande nouvelle devient « découverte »")
    tapeAp("bac-a-sable neuf")
    verifierAp(File(T, "bac_a_sable/coffre.txt").exists(), "bac-a-sable neuf : tout revient")
    tapeAp("cd ..")
    verifierAp(!Apprendre.a(jeuAp).optBoolean("bac_ici"), "en sortant, le jeu compte de nouveau")

    println("46. Le tableau des rares")
    Explo_collection().put("Sylvarque", 1)
    val rr = tapeAp("collection rares").first
    verifierAp("1 / 11" in rr && "¤ombre:" in rr && "attirée par `chmod`" in rr && "se montre très rarement" in rr, "légendaires + Abyssor, silhouettes et indices")
    verifierAp("0 / 40" in tapeAp("collection rares 2").first, "page 2 : les 40 rares")

    println("43. La maîtrise")
    shellAp.dossier = T
    repeat(5) { tapeAp("ls -a") }
    val m = Apprendre.a(jeuAp).getJSONObject("maitrise").getJSONArray("ls")
    verifierAp(m.getInt(0) == 1 && m.getInt(2) == 1, "ls -a cinq fois : option + maîtrisée ($m)")
    verifierAp("●●◉" in Apprendre.lignesMaitrise(jeuAp) && "Maîtrise" in tapeAp("badges").first, "badges : la maîtrise des commandes")
    for (c in Apprendre.cmds().take(10)) Apprendre.a(jeuAp).getJSONObject("maitrise").put(c, JSONArray("[1,5,1]"))
    verifierAp(Entrainement.titres(jeuAp).any { it.id == "main_sure" }, "10 commandes maîtrisées : « Main sûre »")

    println("24. Les révisions")
    val a = Apprendre.a(jeuAp)
    a.getJSONObject("vus").put("head", JSONArray().put(Apprendre.jourDe(Apprendre.maintenant() - 9 * 86400)).put(0))
    a.put("rev", JSONObject())
    // (indépendant de la date : si la commande du jour tombe sur pwd, son bonus ne doit pas se mêler aux révisions ;
    //  la mission du jour est marquée faite ici, le § 29 la refait)
    val auj = Apprendre.jourDe(Apprendre.maintenant())
    a.put("tampons", JSONArray((lstAp(a.optJSONArray("tampons")) + auj).distinct()))
    tapeAp("pwd")
    verifierAp(a.getJSONObject("rev").optString("cmd") == "head", "une invitation (« Tu te souviens de head ? »)")
    File(T, "nid.txt").writeText("a\nb\nc\n")
    msg = tapeAp("head -n 2 nid.txt").second
    verifierAp("Souvenir rafraîchi" in msg && a.getJSONObject("vus").getJSONArray("head").getInt(1) == 1, "refaite : +4 XP, l'étape monte")
    verifierAp("Souvenirs à rafraîchir" in tapeAp("souvenirs").first, "souvenirs : la page")

    println("29. La commande du jour")
    val (jour, cmd) = Apprendre.missionDuJour(jeuAp)
    val ex = Apprendre.donnees().getJSONObject("jour").getJSONObject("exemples").getString(cmd)
    verifierAp(ex in tapeAp("jour").first, "jour : la mission ($cmd)")
    val dj = File(T, "jourtest").apply { mkdirs() }
    for (f in listOf("recette.txt", "pomme.txt", "poire.txt")) File(dj, f).writeText("miel\nsel\n")
    File(dj, "cabane").mkdirs()
    shellAp.dossier = dj
    // (une commande tapée plus haut peut déjà avoir réussi la mission du jour, selon la date : on repart à zéro)
    a.put("tampons", JSONArray(lstAp(a.optJSONArray("tampons")).filter { it != jour }))
    tapeAp(mapOf("rm" to "rm -i poire.txt < /dev/null; true", "less" to "less recette.txt < /dev/null").getOrDefault(cmd, ex))
    verifierAp(jour in lstAp(a.getJSONArray("tampons")) && "☀" in tapeAp("jour").first, "réussie : un tampon soleil dans le calendrier")

    println("44. L'énigme de la semaine")
    tapeAp("enigme")
    val sem = Apprendre.semaine()
    verifierAp(File(Apprendre.dossierEnigme(jeuAp, sem), "lis-moi.txt").exists(), "le dossier de la semaine est préparé")
    verifierAp("pas encore" in tapeAp("enigme reponse pas-ca").first, "mauvaise réponse : rien de perdu")
    verifierAp("Bravo" in tapeAp("enigme reponse " + Apprendre.reponseEnigme(jeuAp, sem)).first, "bonne réponse : +15 XP")

    println("23. Les erreurs en mini-énigmes")
    val de = File(T, "enigmes_erreur").apply { mkdirs() }
    File(de, "cabane").mkdirs(); File(de, "cabane/lettre.txt").writeText("Bonjour\n")
    shellAp.dossier = de
    a.put("erreur_t", 0.0)
    msg = tapeAp("cat lettre.txt").second
    if ("Petite énigme" !in msg) println("     (étape en cours : ${Histoire.enPleineEtape(jeuAp)})")
    verifierAp("Petite énigme" in msg || Histoire.enPleineEtape(jeuAp), "cat d'un fichier absent : l'énigme (sauf pendant une étape)")
    verifierAp(Apprendre.causeErreur(jeuAp, "mkdir cabane", de)?.first == "existe" && Apprendre.causeErreur(jeuAp, "rm cabane", de)?.first == "rm_dossier" &&
        Apprendre.causeErreur(jeuAp, "cd nulle_part", de)?.first == "lieu" && Apprendre.causeErreur(jeuAp, "cat cabane", de)?.first == "cat_dossier",
        "les 5 cas sont devinés en regardant le terrain")
    tapeAp("passe")

    println("21. Le carnet illustré")
    val c1 = tapeAp("carnet").first
    verifierAp("¤picto:pwd¤" in c1 && "page 1/4" in c1, "carnet : les images ¤picto¤ et la page 1/4")
    verifierAp("¤picto:chmod:gris¤" in tapeAp("tg carnet 4").first, "« tg carnet 4 » : la silhouette grise d'une commande pas tapée")
    val b = ApprendreDessin.picto("cd")
    verifierAp(b != null && b.width == 48, "l'image 16 × 16 (×3) se dessine")

    println("41 / 42. Les mini-jeux et la course")
    tapeAp("jeux labyrinthe")
    shellAp.dossier = File(T, "jeux/labyrinthe")
    tapeAp("cd grotte"); tapeAp("cd salle_humide/impasse"); tapeAp("cd ../..")
    msg = tapeAp("cd salle_seche/tunnel/salle_du_tresor").second
    verifierAp("Gagné" in msg, "labyrinthe : la salle du trésor")
    verifierAp("Mode course contre la montre : OUI" in tapeAp("course oui").first, "course oui")
    tapeAp("jeux taupes")
    shellAp.dossier = File(T, "jeux/taupes")
    msg = tapeAp("rm taupe_1.txt taupe_2.txt taupe_3.txt taupe_4.txt taupe_5.txt").second
    verifierAp("Gagné" in msg && "⏱" in msg, "taupes : gagné, avec le chrono et le fantôme")
    tapeAp("jeux peche")
    verifierAp("Gagné" in tapeAp("jeux reponse 4").first, "pêche : 4 poissons cachés")
    tapeAp("course eclairs non")
    verifierAp(!Apprendre.eclairs(jeuAp), "course eclairs non : plus de défis éclair surprises")
    tapeAp("course eclairs oui"); tapeAp("course non")

    println("49. La limite de temps douce")
    verifierAp(Apprendre.questionParent(listOf("temps", "45")) != null && Apprendre.phraseAdulte("oui je suis un adulte") && !Apprendre.phraseAdulte("non"),
        "parent temps 45 : la phrase d'un adulte est demandée")
    Apprendre.reglerTemps(jeuAp, listOf("45"))
    val tp = a.getJSONObject("temps")
    val now = Apprendre.maintenant()
    tp.put("jour", Apprendre.jourDe(now)).put("s", 45 * 60.0).put("t", now - 5)
    shellAp.dossier = T
    msg = tapeAp("pwd").second
    verifierAp(Apprendre.endormie(jeuAp) && "s'endort" in msg, "à 45 minutes : elle s'endort jusqu'à 7 h")
    val xp1 = jeuAp.xp
    msg = tapeAp("whoami").second
    verifierAp(jeuAp.xp == xp1 && "chut" in msg, "pendant le sommeil : rien ne nourrit ni ne donne d'XP")
    val (d0, d1) = Apprendre.sommeil(jeuAp)
    jeuAp.faim = 70.0; jeuAp.dernierTick = (d0 * 1000).toLong()
    Satiete.tick(jeuAp, minOf(d1, d0 + 3600))
    verifierAp(Math.abs(jeuAp.faim - 70.0) < 0.01, "la faim ne baisse pas pendant le sommeil (${jeuAp.faim})")
    Apprendre.reglerTemps(jeuAp, listOf("non"))
    verifierAp(!Apprendre.endormie(jeuAp), "parent temps non : elle se réveille")

    println("45. Le sentier des marmottes")
    verifierAp("palier 3" in tapeAp("sommet sentier").first, "fermé tant qu'aucun monde n'est au palier 3")
    val prog = JSONObject(File(assets, "programme.json").readText())
    val port = (0 until prog.getJSONArray("mondes").length()).map { prog.getJSONArray("mondes").getJSONObject(it) }.first { it.optJSONArray("paliers") != null }
    val faits = Histoire.h(jeuAp).optJSONArray("faits") ?: JSONArray().also { Histoire.h(jeuAp).put("faits", it) }
    lstAp(port.getJSONArray("paliers")).forEach { faits.put(it) }
    verifierAp(Apprendre.sentierOuvert(jeuAp) && "S7" in tapeAp("sommet sentier").first, "un monde au palier 3 : les 7 étapes")
    shellAp.dossier = Apprendre.dossierSentier(jeuAp)
    for (l in listOf("echo \"Bonjour le sommet\"", "mkdir bivouac", "grep marmotte inscriptions.txt", "find . -name \"*.caillou\"", "ls -l", "ls --help > /dev/null", "cat sommet.txt")) tapeAp(l)
    verifierAp(a.getJSONArray("sentier").length() == 7, "les 7 étapes franchies")
    verifierAp(Recompenses.exploitDef("sommet.sentier")?.second?.optString("recompense") == "variante", "l'exploit du sentier : une variante existante")

    println("30. L'examen et le diplôme")
    val ailes = Histoire.h(jeuAp).optJSONArray("ailes") ?: JSONArray().also { Histoire.h(jeuAp).put("ailes", it) }
    ailes.put("grenier")
    verifierAp("salle 1 sur 5" in tapeAp("examen").first, "examen : la forêt du Grenier, salle 1")
    shellAp.dossier = File(Apprendre.dossierExamen(jeuAp), "salle_1")
    tapeAp("ls"); msg = tapeAp("pwd").second
    verifierAp("guide te montre" in msg, "après 2 essais, le guide montre la commande")
    tapeAp("ls -R")
    shellAp.dossier = File(Apprendre.dossierExamen(jeuAp), "salle_2"); tapeAp("mv ours.txt coffre/")
    shellAp.dossier = File(Apprendre.dossierExamen(jeuAp), "salle_3"); tapeAp("cp carte.txt carte_copie.txt")
    shellAp.dossier = File(Apprendre.dossierExamen(jeuAp), "salle_4"); tapeAp("rm caillou.txt")
    shellAp.dossier = File(Apprendre.dossierExamen(jeuAp), "salle_5"); msg = tapeAp("ls").second
    verifierAp("Examen réussi" in msg && "grenier" in lstAp(a.getJSONArray("diplomes")), "5 salles : examen réussi")
    verifierAp(Apprendre.diplomeAMontrer(jeuAp) == "grenier" && Apprendre.diplomeAMontrer(jeuAp) == null, "le diplôme s'affiche une fois (deux boutons)")
    val dip = ApprendreDessin.diplome(jeuAp, "grenier")
    verifierAp(dip.width == 900 && dip.height == 630, "le diplôme est dessiné (900 × 630)")
    verifierAp(!a.toString().lowercase().contains("prenom"), "aucun prénom enregistré")

    println("50. Pas de série à perdre")
    verifierAp(Satiete.lignes(jeuAp).none { "de suite" in it } && Satiete.lignes(jeuAp).any { "jamais perdus" in it }, "« Jours bien nourrie : N au total… (jamais perdus) »")

    println("Les 14 langues")
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val bon = try {
            listOf("carnet", "jour", "collection rares", "souvenirs", "jeux", "course", "maitrise", "examen", "bac-a-sable").all { cmdAp.executer(it)?.texte?.isNotEmpty() == true }
                && Apprendre.contenuDiplome(jeuAp, "grenier").size == 7
        } catch (e: Exception) { println("    $code $e"); false }
        verifierAp(bon, "$code : les écrans s'affichent")
    }
    Langue.definir("fr")

    println("Sécurité")
    verifierAp(!Apprendre.vider(jeuAp, jeuAp.home) && !Apprendre.vider(jeuAp, T), "jamais le HOME ni le terrain entier")
    println("\n$okAp réussis, $koAp échoués")
    dossier.deleteRecursively()
    if (koAp > 0) System.exit(1)
}

fun Explo_collection(): JSONObject = fr.terminagotchi.Explo.collection(jeuAp)
