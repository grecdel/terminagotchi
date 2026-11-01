/*
 * Test JVM de la Bibliothèque du Temps (phase 5) sur Android, portage de pc/outils/test_temps.py :
 *   1. les vecteurs communs donnees/temps/vecteurs.json, partie « spec » (la formule secrète, les photos du grimoire, les
 *      bornes de conflit, garder les deux histoires, les empreintes, la pellicule de la vue déployée) : EXACTEMENT les
 *      mêmes résultats qu'en Python ;
 *   2. le PETIT GIT du téléphone contre le VRAI git (partie « git » des vecteurs, faite par pc/outils/vecteurs_temps.py) :
 *      l'album de la leçon et le grimoire de trois parties, rejoués commande par commande à la même heure ; chaque sortie
 *      et chaque code de sortie doivent être identiques, et donc chaque empreinte ;
 *   3. l'arbre du Carrefour : la Bibliothèque s'ouvre après le niveau 4 du tronc (annoncée une fois), meublée ;
 *   4. la traversée tp0 → tp5 comme dans l'appli (git = le petit git, le reste au vrai shell), l'exploit « retrouver
 *      une version perdue » ; rien hors du terrain ; aucun push, aucun --global ;
 *   5. les variantes réservées, le dessin (pellicule, chemins, bibliothèque de repli), la vue déployée.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Temps.kt -d tmp.jar
 *   java -cp <imitations>:<appli.jar>:tmp.jar:kotlin-stdlib.jar TempsKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.PetitGit
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Temps
import fr.terminagotchi.TempsDessin
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsTp(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilTp(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsTp(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileTp : Toile {
    var n = 0
    val textes = mutableListOf<String>()
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { n++ }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { n++ }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { n++ }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { n++ }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { n++ }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { n++ }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { n++; textes.add(s) }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.6f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { n++ }
    override fun cadre(c: fr.terminagotchi.Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) { n++ }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { n++ }
}

var okTp = 0
var koTp = 0
fun verifierTp(c: Boolean, m: String) {
    if (c) okTp++ else koTp++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuTp: Jeu
lateinit var shellTp: Shell
lateinit var cmdTp: Commandes

fun lstTp(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsTp(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }

fun bashTp(cmd: String, ou: File = shellTp.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuTp.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    pb.environment()["PATH"] = "/usr/local/bin:/usr/bin:/bin"         // (pas de vrai git ici : celui du téléphone n'existe pas)
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeTp(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellTp.executer(cmd)
    else {
        val interne = cmdTp.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashTp(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuTp, cmd, colle = false, rappel = false, hasard = false, cwd = shellTp.dossier, code = code)
    return sortie
}

fun lecTp(): Pair<String?, Int> = Histoire.leconCourante(jeuTp)?.id to jeuTp.etape

fun fichiersHorsTp(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

/** rejoue un scénario des vecteurs (VRAI git) avec le petit git ; renvoie les écarts */
fun rejouerTp(pas: List<JSONObject>, racine: File, avant: (JSONObject) -> Unit = {}): List<String> {
    val ecarts = ArrayList<String>()
    val t = File(racine, "t")
    File(t, "temps").mkdirs()
    PetitGit.afficher = { p -> p.replace(t.path, "{R}") }
    for (x in pas) {
        avant(x)
        val ou = File(t, x.getString("ou"))
        when (x.getString("action")) {
            "git" -> {
                PetitGit.horloge = { x.getLong("date") to 0 }
                val r = PetitGit.executer(lstTp(x.getJSONArray("args")), ou, t)
                val att = x.getString("sortie").trimEnd('\n')
                if (r.texte.trimEnd('\n') != att || r.code != x.getInt("code"))
                    ecarts.add("git ${lstTp(x.getJSONArray("args")).joinToString(" ")} [${x.getString("ou")}]\n      petit (${r.code}) : ${r.texte.replace("\n", "⏎")}\n      vrai  (${x.getInt("code")}) : ${att.replace("\n", "⏎")}")
            }
            "ecrire" -> File(ou, x.getString("fichier")).let { if (x.getBoolean("ajout")) it.appendText(x.getString("texte")) else it.writeText(x.getString("texte")) }
            "lire" -> { val l = try { File(ou, x.getString("fichier")).readText() } catch (e: Exception) { "?" }
                if (l != x.getString("texte")) ecarts.add("lire ${x.getString("fichier")} : ${l.replace("\n", "⏎")} (vrai : ${x.getString("texte").replace("\n", "⏎")})") }
            "grimoire" -> { val e = Temps.poserGrimoireDans(File(t, "temps/grimoire"), t, x.getString("graine")); if (e != "git") ecarts.add("grimoire : $e") }
        }
    }
    return ecarts
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_tp_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilTp(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuTp = Jeu(app)
    jeuTp.changerLangue("fr")
    jeuTp.nom = "Pixel"
    shellTp = Shell(jeuTp.home)
    cmdTp = Commandes(app, jeuTp, { shellTp.dossier })
    jeuTp.module("explo").put("ouverte", true)
    jeuTp.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/temps/vecteurs.json").readText())
    val sp = v.getJSONObject("spec")
    var ko = 0
    for (x in objetsTp(sp.getJSONArray("parties"))) {
        val g = x.getString("graine")
        if (Temps.secret(g) != x.getInt("secret") || Temps.ligneSecrete(g) != x.getString("ligne")) { ko++; println("    secret $g → ${Temps.secret(g)}") }
        val ph = Temps.photos(g)
        val pa = objetsTp(x.getJSONArray("photos"))
        if (ph.size != pa.size || ph.zip(pa).any { (a, b) -> a.message != b.getString("message") || a.date != b.getLong("date") ||
                a.fichiers != b.getJSONObject("fichiers").let { f -> f.keys().asSequence().associateWith { f.getString(it) } } }) { ko++; println("    photos $g") }
        val fin = x.getJSONObject("final")
        if (Temps.grimoireFinal(g) != fin.keys().asSequence().associateWith { fin.getString(it) }) { ko++; println("    final $g") }
    }
    verifierTp(ko == 0, "${sp.getJSONArray("parties").length()} parties : la formule secrète, les 6 photos du grimoire (messages, dates, contenus)")
    ko = 0
    for (x in objetsTp(sp.getJSONArray("bornes"))) if (Temps.sansBornes(x.getString("texte")) != x.getBoolean("sans")) { ko++; println("    bornes ${x.getString("texte")}") }
    for (x in objetsTp(sp.getJSONArray("garde"))) if (Temps.gardeTout(x.getString("texte"), *lstTp(x.getJSONArray("versions")).toTypedArray()) != x.getBoolean("ok")) { ko++; println("    garde $x") }
    for (x in objetsTp(sp.getJSONArray("hashes"))) if (Temps.hashOk(x.getString("rep"), x.getString("juste")) != x.getBoolean("ok")) { ko++; println("    hash $x") }
    for (x in objetsTp(sp.getJSONArray("blobs"))) if (Temps.blobSha(x.getString("texte")) != x.getString("sha")) { ko++; println("    blob $x") }
    verifierTp(ko == 0, "les bornes de conflit, « garder les deux histoires », les réponses (empreintes), l'empreinte d'un blob")
    ko = 0
    for (x in objetsTp(sp.getJSONArray("pellicule"))) { val k = Temps.pelliculesDe(x.getString("ligne")).map { listOf(it.outil, it.de, it.vers) }
        val att = (0 until x.getJSONArray("pellicules").length()).map { lstTp(x.getJSONArray("pellicules").getJSONArray(it)) }
        if (k != att) { ko++; println("    pellicule ${x.getString("ligne")} → $k") } }
    for (x in objetsTp(sp.getJSONArray("deploie"))) { val k = Deploie.pellicules(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.outil, it.de, it.vers) }
        val att = objetsTp(x.getJSONArray("pellicules")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("de"), it.getString("vers")) }
        if (k != att) { ko++; println("    vue déployée ${x.getString("ligne")} → $k (attendu $att)") } }
    verifierTp(ko == 0, "la pellicule : git init, status, add, log, restore, switch, merge, pull, hash-object… et la vue déployée")

    println("2. Le petit git du téléphone contre le VRAI git (${v.optJSONObject("git")?.optString("version")})")
    val vg = v.getJSONObject("git")
    val ecarts = rejouerTp(objetsTp(vg.getJSONArray("album")), File(dossier, "album_vrai"))
    for (e in ecarts.take(8)) println("    ✖ $e")
    verifierTp(ecarts.isEmpty(), "l'album de la leçon : ${vg.getJSONArray("album").length()} pas (init, status, commit, log, diff, restore, switch, merge et son conflit, clone, pull, .gitignore, remote, cat-file, show…) identiques au vrai git")
    for (gx in objetsTp(vg.getJSONArray("grimoires"))) {
        val e2 = rejouerTp(objetsTp(gx.getJSONArray("pas")), File(dossier, "grim_" + gx.getString("graine").replace(":", "_")))
        for (e in e2.take(6)) println("    ✖ $e")
        verifierTp(e2.isEmpty(), "le grimoire de la partie ${gx.getString("graine")} : mêmes empreintes, log -S, show, checkout HASH~1 -- fichier, HEAD détachée")
    }
    PetitGit.horloge = { val ms = System.currentTimeMillis(); (ms / 1000) to 0 }

    println("3. L'arbre du Carrefour : quand la Bibliothèque s'ouvre")
    val h = Histoire.h(jeuTp)
    verifierTp(!Histoire.ouvert(jeuTp, "temps"), "fermée au début : il manque ${Temps.manque(jeuTp)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid", "bibliotheque")) h.getJSONArray("ailes").put(c)
    h.put("mondes_annonces", JSONArray(listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde", "observatoire", "donnees", "forge", "robots")))
    h.put("annonce_attente", true)
    Histoire.tick(jeuTp, "ls", false, jeuTp.home, 0)
    verifierTp(Histoire.ouvert(jeuTp, "temps") && "temps" in lstTp(h.optJSONArray("mondes_annonces")) && !Temps.annonce(jeuTp),
        "le niveau 4 fait : la Bibliothèque s'ouvre, annoncée une seule fois")
    val D = File(jeuTp.terrain, "temps")
    D.mkdirs()
    Histoire.tick(jeuTp, "ls", false, jeuTp.home, 0)
    verifierTp(File(D, "registre_du_temps.txt").isFile, "la Bibliothèque est meublée (le registre)")

    println("4. La traversée de la Bibliothèque sur le téléphone (le petit git)")
    val avantFichiers = fichiersHorsTp(jeuTp.home, jeuTp.terrain)
    jeuTp.xp = 10 * 30 * 30
    tapeTp("cd ~/terrain_terminagotchi/temps")
    verifierTp(lecTp() == ("tp0" to 1), "entrer dans la Bibliothèque choisit le monde : ${lecTp()}")
    val sorties = HashMap<String, String>()
    val passages = HashMap<String, Pair<String, String>>()
    fun perte() = Temps.hashPerte(jeuTp).take(7)
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat registre_du_temps.txt" },
        { "temps album" }, { "git init" }, { "git init -b main album" }, { "cd album" }, { "git config --global user.name \"Apprenti du Temps\"" },
        { "git config user.name \"Apprenti du Temps\"" }, { "git commit -m \"Jour 1\"" }, { "git config user.email \"apprenti@temps.invalid\"" },
        { "echo \"Jour 1\" > chronique.txt" }, { "git status" }, { "git add chronique.txt" }, { "git commit -m \"Jour 1\"" },
        { "temps grimoire" }, { "cd ~/terrain_terminagotchi/temps/grimoire" }, { "git log --oneline" }, { "echo \"gribouillis\" >> grimoire.txt" },
        { "git diff" }, { "git restore grimoire.txt" }, { "git log --oneline -S secret" }, { "git show ${perte()}" },
        { "temps perdu ${Temps.hashApparition(jeuTp).take(7)}" }, { "temps perdu ${perte()}" }, { "git checkout ${perte()}" }, { "git switch main" },
        { "git checkout ${perte()}~1 -- grimoire.txt" }, { "git commit -am \"Retrouve la formule secrete\"" },
        { "temps branches" }, { "cd ../album" }, { "git switch -c reve" }, { "echo \"Jour 2 : un reve\" >> chronique.txt" }, { "git commit -am \"Le reve\"" },
        { "git switch main" }, { "echo \"Jour 2 : une balade\" >> chronique.txt" }, { "git commit -am \"La balade\"" }, { "git merge reve" },
        { "cat chronique.txt" }, { Temps.SED }, { "git commit -am \"Reunit les deux histoires\"" }, { "git log --oneline --graph" },
        { "temps partage" }, { "git clone . ../copie_de_mon_ami" }, { "temps ami" }, { "git log --oneline" }, { "git pull" }, { "git pull ../copie_de_mon_ami" },
        { "echo \"*.tmp\" > .gitignore" }, { "touch brouillon.tmp" }, { "git status" }, { "cd ../copie_de_mon_ami" }, { "git push" }, { "git remote -v" },
        { "temps bateau" },
        { "temps empreintes" }, { "cd ~/terrain_terminagotchi/temps/empreintes" }, { "git hash-object mot.txt" }, { "printf 'blob 6\\0temps\\n' | sha1sum" },
        { "echo \"Temps\" > mot.txt" }, { "git hash-object mot.txt" }, { "cd ../album" }, { "git cat-file -p HEAD" }, { "cd ../empreintes" },
        { "find . -type f -newer repere.txt" }, { "temps bilan" },
    )
    for (f in etapes) {
        val c = f()
        val avant = lecTp()
        val s = tapeTp(c)
        sorties.putIfAbsent(c, s)
        passages.putIfAbsent(c, "$avant" to "${lecTp()}")
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecTp()} ${s.take(90).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuTp, "temps")) break
    }
    verifierTp(Histoire.fini(jeuTp, "temps"), "la Bibliothèque est traversée jusqu'au bout (tp0 → tp5) : ${lecTp()}")
    val album = PetitGit.ouvrir(File(D, "album"))!!
    verifierTp(album.cfg("user.name") == "Apprenti du Temps" && "petit git" !in (sorties["git config --global user.name \"Apprenti du Temps\""] ?: "x").lowercase().take(0) &&
        "--global" in (sorties["git config --global user.name \"Apprenti du Temps\""] ?: ""), "--global refusé (le petit git n'a pas de configuration globale) ; le nom d'exemple est dans l'album")
    verifierTp(vg.getJSONArray("album").let { al -> objetsTp(al).any { "Please tell me who you are" in it.optString("sortie") } } && ecarts.isEmpty(),
        "sans nom ni adresse, git refuse la photo : le même message que le vrai git (vecteurs)")
    verifierTp("(root-commit)" in (sorties.entries.lastOrNull { it.key == "git commit -m \"Jour 1\"" }?.value ?: "") || Temps.aCommit(jeuTp, "album"), "la première photo de l'album")
    verifierTp(Regex("^\\+gribouillis$", RegexOption.MULTILINE).containsMatchIn(sorties["git diff"] ?: ""), "git diff : + gribouillis")
    verifierTp((sorties["git log --oneline -S secret"] ?: "").lines().size == 2, "git log -S secret : deux photos")
    verifierTp("detached HEAD" in (sorties["git checkout ${perte()}"] ?: ""), "le voyage de tout l'album dans le passé (HEAD détachée), expliqué par git")
    val ex = Recompenses.etat(jeuTp).getJSONObject("exploits").keys().asSequence().toList()
    verifierTp("temps.version" in ex, "l'exploit « retrouver une version perdue » ($ex)")
    verifierTp("CONFLICT (content): Merge conflict in chronique.txt" in (sorties["git merge reve"] ?: ""), "le conflit de la fusion")
    verifierTp((sorties["git log --oneline --graph"] ?: "").lines().let { l -> l.size >= 6 && l[0].startsWith("*   ") && l[1] == "|\\  " && l.any { it == "|/  " } },
        "git log --graph dessine deux chemins qui se rejoignent :\n${sorties["git log --oneline --graph"]}")
    verifierTp("Fast-forward" in (sorties["git pull ../copie_de_mon_ami"] ?: "") && "tracking information" in (sorties["git pull"] ?: ""), "git pull : sans dire d'où, git l'explique ; depuis la copie : avance rapide")
    verifierTp("brouillon.tmp" !in (sorties["git status"] ?: "x").let { sorties.entries.last { it.key == "git status" }.value } , "brouillon.tmp est ignoré (.gitignore)")
    verifierTp(Regex("^origin\\t.*/temps/album(/\\.)? \\(fetch\\)$", RegexOption.MULTILINE).containsMatchIn(sorties["git remote -v"] ?: ""), "git remote -v : origin, l'album (${sorties["git remote -v"]})")
    verifierTp("eb51c8df438dd920beceb5c9ef1e691531fa8a2d" in (sorties["git hash-object mot.txt"] ?: "") &&
        PetitGit.executer(listOf("hash-object", "mot.txt"), File(D, "empreintes"), jeuTp.terrain).texte == "59b96ff1782835a2bc483e5f3332f1396b0abd1e",
        "git hash-object : la même empreinte que le vrai git (temps, puis Temps)")
    val sha1 = sorties["printf 'blob 6\\0temps\\n' | sha1sum"] ?: ""
    verifierTp(sha1.startsWith("eb51c8df438dd920beceb5c9ef1e691531fa8a2d") || sha1.isEmpty(), "sha1sum (le vrai shell) trouve la même empreinte : ${sha1.trim()}")
    verifierTp(Regex("^parent [0-9a-f]{40}$", RegexOption.MULTILINE).containsMatchIn(sorties["git cat-file -p HEAD"] ?: ""), "git cat-file -p HEAD : la photo garde l'empreinte de la précédente")
    verifierTp("./nouveau.txt" in (sorties["find . -type f -newer repere.txt"] ?: "") && "./mot.txt" in (sorties["find . -type f -newer repere.txt"] ?: "") &&
        "./ancien.txt" !in (sorties["find . -type f -newer repere.txt"] ?: ""), "find -newer (le pont de la Citadelle) : nouveau.txt et mot.txt")
    verifierTp("pendule" in lstTp(Quetes.q(jeuTp).optJSONArray("objets")), "récompense du monde : une pendule ancienne")
    verifierTp(File(D, "certificat_archiviste.txt").isFile, "le certificat d'Archiviste du Temps")
    verifierTp("push" in (sorties["git push"] ?: "") && PetitGit.ouvrir(File(D, "copie_de_mon_ami"))!!.remotes.getJSONObject("origin").optString("url").startsWith(jeuTp.terrain.path),
        "aucun push ; le seul « remote » est l'album du terrain")
    val nouveaux = fichiersHorsTp(jeuTp.home, jeuTp.terrain) - avantFichiers
    verifierTp(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")
    val cmds = Temps.lecons(jeuTp).values.flatMap { it.etapes }.joinToString(" ") { it.cmd }
    verifierTp("--global" !in cmds && "sudo" !in cmds && "push" !in cmds, "aucune étape n'utilise --global, sudo ni push")

    println("5. Les variantes réservées, le dessin, la vue déployée")
    val j2 = Jeu(AppareilTp(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierTp(Recompenses.reservee(j2, "soleil", "momiaou") && Recompenses.reservee(j2, "ruines", "galetard") && Recompenses.reservee(j2, "brume", "follanterne") &&
        !Recompenses.reservee(jeuTp, "soleil", "momiaou") && !Recompenses.reservee(j2, "classique", "momiaou"),
        "les variantes momiaou:soleil, galetard:ruines, follanterne:brume réservées jusqu'à l'exploit")
    val tl = ToileTp()
    TempsDessin.pellicule(tl, Deploie.PelliculeD(0, "git", "git commit", "objectif", "photo"), 0.4, 0f, 0f, 400f, 96f, 1f)
    TempsDessin.pellicule(tl, Deploie.PelliculeD(0, "git", "git log", "album", "pellicule"), 0.1, 0f, 0f, 300f, 60f, 1f)
    TempsDessin.chemins(tl, 0.7, 0f, 0f, 400f, 140f, 1f)
    TempsDessin.bibliotheque(tl, 0.3, 0f, 0f, 400f, 225f, 1f)
    verifierTp(tl.n > 80 && tl.textes.any { "git commit" in it } && tl.textes.any { it == "reve" }, "le dessin : pellicule, chemins, bibliothèque (${tl.n} traits)")
    val vue = Deploie.vue("git add chronique.txt && git commit -m 'Jour 1' | head -1")!!
    verifierTp(vue.pelliculeDe(vue.blocs.first { it.g == "commande" })?.vers == "objectif" && vue.blocs.none { it.g == "commande" && it.seg > 0 && vue.pelliculeDe(it)?.outil == "git commit" },
        "la vue déployée : git add pose devant l'objectif (git commit reste à l'établi de la Guilde)")

    println("\n$okTp réussis, $koTp échoués")
    kotlin.system.exitProcess(if (koTp == 0) 0 else 1)
}
