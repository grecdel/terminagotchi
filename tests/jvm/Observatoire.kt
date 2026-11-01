/*
 * Test JVM de l'Observatoire de l'IA (phase 5) sur Android, portage de pc/outils/test_observatoire.py :
 *   1. les vecteurs communs donnees/observatoire/vecteurs.json (les jeux de données dans les 14 langues, le devineur de
 *      type, le texte du devineur de mots nettoyé dans les 14 langues, ses comptes, ses paires, ses phrases tirées, ce que
 *      l'assistant comprend, son tri qui oublie une ligne, les propositions des agents, les 2 réponses fausses, les quiz
 *      mélangés comme random.shuffle de Python, la lunette) : EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. l'arbre du Carrefour : l'Observatoire s'ouvre après les niveaux 4 et 6 du tronc (annoncé une fois), meublé ;
 *   3. la traversée ob0 → ob9 comme dans l'appli (git → diff, Ctrl+C → agent stop, awk → cut, export sur la même ligne),
 *      l'exploit « réponses fausses » (une fois), la loupe ; aucune proposition dangereuse jamais exécutée ; rien hors du
 *      terrain ; l'agent Copieur s'arrête avec STOP ;
 *   4. les variantes réservées, le dessin (lunette, votes, copies, coupole de repli) sur une toile d'essai ; la vue
 *      déployée sait quel bloc vérifie quoi.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Observatoire.kt -d obs.jar
 *   java -cp <imitations>:<appli.jar>:obs.jar:kotlin-stdlib.jar ObservatoireKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Observatoire
import fr.terminagotchi.ObservatoireDessin
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsOb(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilOb(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsOb(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileOb : Toile {
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

var okOb = 0
var koOb = 0
fun verifierOb(c: Boolean, m: String) {
    if (c) okOb++ else koOb++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuOb: Jeu
lateinit var shellOb: Shell
lateinit var cmdOb: Commandes

fun lstOb(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }
fun objetsOb(a: JSONArray): List<JSONObject> = (0 until a.length()).map { a.getJSONObject(it) }
fun lignesOb(a: JSONArray): List<List<String>> = (0 until a.length()).map { lstOb(a.getJSONArray(it)) }

fun bashOb(cmd: String, ou: File = shellOb.dossier): Pair<String, Int> {
    val pb = ProcessBuilder("sh", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuOb.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    val p = pb.start()
    p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeOb(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellOb.executer(cmd)
    else {
        val interne = cmdOb.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashOb(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuOb, cmd, colle = false, rappel = false, hasard = false, cwd = shellOb.dossier, code = code)
    return sortie
}

fun lecOb(): Pair<String?, Int> = Histoire.leconCourante(jeuOb)?.id to jeuOb.etape

fun fichiersHorsOb(racine: File, terrain: File): Set<String> = racine.walkTopDown().onEnter { it.canonicalPath != terrain.canonicalPath }
    .filter { it.isFile }.map { it.canonicalPath }.toSet()

fun modeleJson(m: JSONObject): String {
    fun o(x: JSONObject?) = x?.keys()?.asSequence()?.sorted()?.joinToString(",") { k -> "$k=${x.getJSONArray(k).getInt(0)}/${x.getJSONArray(k).getInt(1)}" } ?: ""
    return "n=${m.optInt("n")} total=${m.getJSONArray("total").getInt(0)}/${m.getJSONArray("total").getInt(1)} f[${o(m.optJSONObject("famille"))}] l[${o(m.optJSONObject("lieu"))}]"
}

fun essaisOb(l: List<Observatoire.Essai>) = l.map { listOf(it.nom, it.famille, it.lieu, "${it.devine}", if (it.vrai == null) "null" else "${it.vrai}", "${it.vf}", "${it.vp}") }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_ob_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilOb(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuOb = Jeu(app)
    jeuOb.changerLangue("fr")
    jeuOb.nom = "Pixel"
    shellOb = Shell(jeuOb.home)
    cmdOb = Commandes(app, jeuOb, { shellOb.dossier })
    jeuOb.module("explo").put("ouverte", true)
    jeuOb.terrain.mkdirs()

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/observatoire/vecteurs.json").readText())
    val D = Observatoire.donnees()
    val L = v.getJSONObject("langues")
    var ko = 0
    var koMots = 0
    var koMissions = 0
    for (code in L.keys()) {
        Langue.definir(code)
        val x = L.getJSONObject(code)
        fun ids(k: String) = lstOb(D.getJSONArray(k))
        if (Observatoire.texteTypes() != x.getString("types") || Observatoire.texteCreatures(ids("exemples")) != x.getString("exemples") ||
            Observatoire.texteCreatures(listOf(D.getString("piege")), false) != x.getString("nouvelle") ||
            Observatoire.texteCreatures(ids("volcan")) != x.getString("volcan") || Observatoire.texteCreatures(ids("autres")) != x.getString("autres")) { ko++; println("    données $code") }
        val m = Observatoire.apprendre(Observatoire.texteCreatures(ids("exemples")))
        val mv = Observatoire.apprendre(Observatoire.texteCreatures(ids("volcan")))
        if (modeleJson(m) != modeleJson(x.getJSONObject("modele")) || modeleJson(mv) != modeleJson(x.getJSONObject("modele_volcan"))) { ko++; println("    modèle $code ${modeleJson(m)}") }
        if (Observatoire.cerveauLignes(m, "exemples.txt").map { sansBidi(it) } != lstOb(x.getJSONArray("cerveau")).map { sansBidi(it) }) { ko++; println("    cerveau $code") }
        if (essaisOb(Observatoire.tester(m, Observatoire.texteCreatures(listOf(D.getString("piege")), false))) != lignesOb(x.getJSONArray("teste_nouvelle")) ||
            essaisOb(Observatoire.tester(mv, Observatoire.texteCreatures(ids("autres")))) != lignesOb(x.getJSONArray("teste_autres_volcan")) ||
            essaisOb(Observatoire.tester(m, Observatoire.texteCreatures(ids("autres")))) != lignesOb(x.getJSONArray("teste_autres"))) { ko++; println("    tests $code") }
        val lignes = Observatoire.corpusLignes(code)
        if (lignes != lstOb(x.getJSONArray("corpus"))) {
            koMots++
            val att = lstOb(x.getJSONArray("corpus"))
            val k = lignes.indices.firstOrNull { it >= att.size || lignes[it] != att[it] }
            println("    corpus $code ligne $k : ${k?.let { lignes.getOrNull(it)?.take(80) }} ≠ ${k?.let { att.getOrNull(it)?.take(80) }}")
        }
        val mots = Observatoire.motsDe(lignes.joinToString("\n"))
        val table = Observatoire.paires(mots)
        if (Observatoire.effectifs(mots).take(12).map { listOf(it.first, "${it.second}") } != lignesOb(x.getJSONArray("effectifs")) ||
            Observatoire.topPaires(mots).take(12).map { listOf(it.first, it.second, "${it.third}") } != lignesOb(x.getJSONArray("paires"))) { koMots++; println("    comptes $code") }
        val su = x.getJSONObject("suites")
        for (w in su.keys()) if (Observatoire.suite(table, w).take(10).map { listOf(it.first, "${it.second}") } != lignesOb(su.getJSONArray(w))) { koMots++; println("    suite $code $w") }
        for (p in objetsOb(x.getJSONArray("phrases"))) if (Observatoire.phrase(table, p.getString("debut"), p.getString("graine"), p.getInt("n")) != lstOb(p.getJSONArray("phrase"))) {
            koMots++; println("    phrase $code ${p.getString("debut")} → ${Observatoire.phrase(table, p.getString("debut"), p.getString("graine"), p.getInt("n"))}") }
        val vals = Observatoire.texteTypes().lines().filter { it.isNotBlank() }.map { it.trim().split(Regex("\\s+")).last() }.distinct()
        for (mi in objetsOb(x.getJSONArray("missions"))) {
            val a = Observatoire.analyser(mi.getString("texte"), listOf("creatures.txt", "mission.txt", "tri.txt")) { vals }
            val att = mi.getJSONObject("analyse")
            fun s(k: String) = if (att.isNull(k)) null else att.getString(k)
            if (a.verbe != s("verbe") || a.fichier != s("fichier") || a.filtre != s("filtre") || a.manque != lstOb(att.getJSONArray("manque"))) {
                koMissions++; println("    mission $code « ${mi.getString("texte")} » → ${a.verbe} ${a.fichier} ${a.filtre} ${a.manque}") }
        }
        val ef = x.getJSONObject("est_feu")
        for (w in ef.keys()) if ("${Observatoire.estFeu(w)}" != (if (ef.isNull(w)) "null" else "${ef.getBoolean(w)}")) { ko++; println("    estFeu $code « $w »") }
    }
    Langue.definir("fr")
    verifierOb(ko == 0, "les jeux de données, le cerveau du devineur, ses votes et ses erreurs : identiques dans les ${L.length()} langues")
    verifierOb(koMots == 0, "le devineur de mots : texte nettoyé, effectifs, paires, suites et phrases tirées identiques dans les ${L.length()} langues")
    verifierOb(koMissions == 0, "ce que l'assistant comprend d'une consigne (verbe, fichier, filtre, ce qui manque), dans les ${L.length()} langues")
    ko = 0
    for (x in objetsOb(v.getJSONArray("parties"))) {
        val g = x.getString("graine")
        val (tri, oubliee) = Observatoire.trierAssistant(Observatoire.texteTypes().lines(), g)
        if (Observatoire.oubli(g) != x.getInt("oubli") || tri != lstOb(x.getJSONArray("tri")) || oubliee != x.getString("oubliee")) { ko++; println("    tri $g") }
        fun props(c: String) = Observatoire.propositions(g, c).map { listOf("${it.n}", it.id, "${it.sur}", it.texte) }
        if (props("agent") != lignesOb(x.getJSONArray("agent")) || props("equipe") != lignesOb(x.getJSONArray("equipe")) ||
            Observatoire.dangereuse(g) != x.getInt("dangereuse") || Observatoire.dangereuse(g, "equipe") != x.getInt("dangereuse_equipe")) { ko++; println("    propositions $g") }
        if (Observatoire.questions(g).map { listOf("${it.n}", it.id, "${it.fausse}") } != lignesOb(x.getJSONArray("questions"))) { ko++; println("    questions $g") }
        fun c3(l: List<Observatoire.Carte>) = l.map { listOf("${it.n}", it.id, it.rep) }
        if (c3(Observatoire.confierCartes(g)) != lignesOb(x.getJSONArray("confier")) || c3(Observatoire.nuancesCartes(g)) != lignesOb(x.getJSONArray("nuances")) ||
            c3(Observatoire.perroquetCartes(g)) != lignesOb(x.getJSONArray("perroquet")) || c3(Observatoire.biaisCartes(g)) != lignesOb(x.getJSONArray("biais"))) { ko++; println("    cartes $g") }
        if (Observatoire.consigneCartes(g).map { listOf(it.first, it.second, it.third) } != lignesOb(x.getJSONArray("consigne")) ||
            Observatoire.decoupeCartes(g).map { listOf("${it.first}", it.second) } != lignesOb(x.getJSONArray("decoupe")) ||
            Observatoire.decoupeReponse(g) != lstOb(x.getJSONArray("decoupe_reponse"))) { ko++; println("    équipe $g") }
    }
    verifierOb(ko == 0, "${v.getJSONArray("parties").length()} parties : le tri qui oublie une ligne, les propositions des agents, les questions, les quiz")
    ko = 0
    for (x in objetsOb(v.getJSONArray("fausses"))) {
        val (a, b, c) = Observatoire.faussesOk(lstOb(x.getJSONArray("rep")), x.getString("graine"))
        if (listOf("$a", "$b", "$c") != lstOb(x.getJSONArray("res"))) { ko++; println("    fausses $x → $a $b $c") }
    }
    for (x in objetsOb(v.getJSONArray("quiz"))) {
        val (bon, justes) = Observatoire.quizJustes(Observatoire.confierCartes(x.getString("graine")), lstOb(x.getJSONArray("rep")), x.getString("lettres"))
        if (bon != x.getBoolean("ok") || justes.map { listOf("${it.n}", it.id) } != lignesOb(x.getJSONArray("justes"))) { ko++; println("    quiz $x") }
    }
    for (x in objetsOb(v.getJSONArray("nettoyage"))) if (Observatoire.nettoyer(Observatoire.sansChamps(x.getString("texte"))) != lstOb(x.getJSONArray("mots"))) {
        ko++; println("    nettoyer « ${x.getString("texte")} » → ${Observatoire.nettoyer(Observatoire.sansChamps(x.getString("texte")))}") }
    if (Observatoire.listeRangee(lstOb(D.getJSONObject("agent").getJSONArray("liste"))) != lstOb(v.getJSONArray("liste_rangee"))) { ko++; println("    liste rangée") }
    verifierOb(ko == 0, "les réponses fausses trouvées, les quiz, le nettoyage des textes (chinois, japonais, hindi, arabe…), la liste rangée")
    ko = 0
    for (x in objetsOb(v.getJSONArray("lunette"))) { val k = Observatoire.lunettesDe(x.getString("ligne")).map { listOf(it.first, it.second, it.third) }
        if (k != lignesOb(x.getJSONArray("lunettes"))) { ko++; println("    lunette ${x.getString("ligne")} → $k") } }
    for (x in objetsOb(v.getJSONArray("deploie"))) { val k = Deploie.lunettes(x.getString("ligne")).map { listOf("${it.seg}", it.cmd, it.outil, it.de, it.vers) }
        val att = objetsOb(x.getJSONArray("lunettes")).map { listOf("${it.getInt("seg")}", it.getString("cmd"), it.getString("outil"), it.getString("de"), it.getString("vers")) }
        if (k != att) { ko++; println("    vue déployée ${x.getString("ligne")} → $k (attendu $att)") } }
    verifierOb(ko == 0, "la lunette : diff, wc, uniq -c, grep -c, tests, assistant, devine-type, devine-mot, agent, et la vue déployée")

    println("2. L'arbre du Carrefour : quand l'Observatoire s'ouvre")
    val h = Histoire.h(jeuOb)
    verifierOb(!Histoire.ouvert(jeuOb, "observatoire"), "fermé au début : il manque ${Observatoire.manque(jeuOb)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) { for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l); h.getJSONArray("ailes").put(c) }
    h.put("mondes_annonces", JSONArray(listOf("port", "citadelle", "crypte", "machinerie", "ondes", "guilde")))
    Histoire.tick(jeuOb, "ls", false, jeuOb.home, 0)
    verifierOb(!Histoire.ouvert(jeuOb, "observatoire"), "sans la cave (niveau 6) : toujours fermé (${Observatoire.manque(jeuOb)})")
    for (l in Histoire.PAR_CHAP["cave"]!!.lecons) faits.put(l)
    h.getJSONArray("ailes").put("cave")
    h.put("annonce_attente", true)
    Histoire.tick(jeuOb, "ls", false, jeuOb.home, 0)
    verifierOb(Histoire.ouvert(jeuOb, "observatoire") && "observatoire" in lstOb(h.optJSONArray("mondes_annonces")) && !Observatoire.annonce(jeuOb),
        "les niveaux 4 et 6 faits : l'Observatoire s'ouvre, annoncé une seule fois")
    val DO = File(jeuOb.terrain, "observatoire")
    DO.mkdirs()
    Histoire.tick(jeuOb, "ls", false, jeuOb.home, 0)
    verifierOb(File(DO, "coupole.txt").isFile && File(DO, "missions/creatures.txt").isFile && File(DO, Observatoire.CARNET).isFile,
        "l'Observatoire est meublé (coupole, carnet, missions)")

    println("3. La traversée de l'Observatoire sur le téléphone")
    val avantFichiers = fichiersHorsOb(jeuOb.home, jeuOb.terrain)
    jeuOb.xp = 10 * 30 * 30
    tapeOb("cd ~/terrain_terminagotchi/observatoire")
    verifierOb(lecOb() == ("ob0" to 1), "entrer dans l'Observatoire choisit le monde : ${lecOb()}")
    val gr = Histoire.graine(jeuOb)
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat coupole.txt" },
        { "observatoire mission" }, { "cd missions" }, { "cat mission_floue.txt" }, { "assistant mission_floue.txt" },
        { "echo \"Fais un truc\" > mission.txt" }, { "echo \"Compte les créatures Feu dans creatures.txt\" > mission.txt" },
        { "assistant mission.txt > rapport.txt" }, { "cat rapport.txt" },
        { "observatoire verifier" }, { "assistant mission_tri.txt > tri.txt" }, { "wc -l creatures.txt tri.txt" }, { "sort creatures.txt | diff - tri.txt" },
        { "sh test.sh" }, { "observatoire oubli Pikachu" },
        { "observatoire oubli " + Observatoire.trierAssistant(Observatoire.texteTypes().lines(), gr).second!!.split(" ")[0] },
        { "sort creatures.txt > tri.txt && sh test.sh" },
        { "cd .." }, { "observatoire secrets" }, { "cd secrets" }, { "grep -n CLE config_partagee.txt" }, { "sed -i '/CLE_API/d' config_partagee.txt" },
        { "echo \"CLE_API=exemple-pas-une-vraie-cle\" > .env" }, { "chmod 600 .env" }, { "echo .env >> .gitignore" },
        { "export CLE_API=exemple-pas-une-vraie-cle && echo \${#CLE_API}" },
        { "cd .." }, { "observatoire agent" }, { "cd chantier" }, { "agent lance" }, { "cat journal_agent.txt" }, { "diff .avant/a_nourrir.txt a_nourrir.txt" },
        { "agent accepte ${Observatoire.dangereuse(gr)}" }, { "agent refuse ${Observatoire.dangereuse(gr)}" }, { "agent valide" }, { "agent boucle" }, { "agent stop" },
        { "cd .." }, { "observatoire apprendre" }, { "cd devineur" }, { "head -5 exemples.txt" }, { "cut -d ' ' -f 4 exemples.txt | sort | uniq -c" },
        { "devine-type apprends exemples.txt" }, { "cat cerveau.txt" }, { "devine-type teste nouvelle.txt" }, { "observatoire piege famille" },
        { "cd .." }, { "observatoire biais" }, { "cd devineur" }, { "cut -d ' ' -f 3 volcan.txt | sort | uniq -c" }, { "cut -d ' ' -f 4 volcan.txt | sort | uniq -c" },
        { "devine-type apprends volcan.txt" }, { "devine-type teste autres.txt" },
        { "observatoire biais " + Observatoire.biaisCartes(gr).first { it.rep == "o" }.n },
        { "devine-type apprends exemples.txt" }, { "devine-type teste autres.txt" },
        { "cd .." }, { "observatoire mots" }, { "cd mots" }, { "tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -5" },
        { "tr ' ' '\\n' < histoire.txt > mots.txt" }, { "tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -5" },
        { "devine-mot suite le" }, { "devine-mot phrase le" }, { "observatoire perroquet " + Observatoire.perroquetCartes(gr).joinToString(" ") { it.rep } },
        { "cd .." }, { "observatoire esprit" }, { "assistant questions" }, { "cd devineur" }, { "wc -l exemples.txt" }, { "cd .." }, { "echo \$((17 % 5))" }, { "explique rm" },
        { "assistant fausses " + Observatoire.questions(gr).filter { it.fausse }.joinToString(" ") { "${it.n}" } },
        { "observatoire confier" }, { "observatoire confier " + Observatoire.confierCartes(gr).joinToString(" ") { it.rep } },
        { "observatoire nuances" }, { "observatoire nuances " + Observatoire.nuancesCartes(gr).joinToString(" ") { it.rep } },
        { "observatoire equipe" }, { "observatoire decoupe " + Observatoire.decoupeReponse(gr).joinToString(" ") },
        { "observatoire consigne " + Observatoire.consigneCartes(gr).first { it.third == "true" }.first },
        { "cd equipe" }, { "agent equipe" }, { "ls" }, { "agent stop" }, { "ls copies | wc -l" }, { "cat journal_equipe.txt" },
        { "agent refuse ${Observatoire.dangereuse(gr, "equipe")}" }, { "diff invites.txt liste.txt" }, { "sh tests.sh" },
        { "wc -l < liste.txt > compte.txt" }, { "sh tests.sh" }, { "agent bilan" },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = f()
        val avant = lecOb()
        val s = tapeOb(c)
        sorties.putIfAbsent(c, s)
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecOb()} ${s.take(90).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuOb, "observatoire")) break
    }
    verifierOb(Histoire.fini(jeuOb, "observatoire"), "l'Observatoire est traversé jusqu'au bout (ob0 → ob9) : ${lecOb()}")
    verifierOb("❓" in (sorties["assistant mission_floue.txt"] ?: ""), "la consigne floue : l'assistant dit qu'il n'a pas compris")
    verifierOb(File(DO, "missions/rapport.txt").readText().trim() == "creatures.txt : 10 lignes contiennent « Feu ».", "le rapport écrit par la redirection > de l'appli")
    verifierOb("✖" in (sorties["sh test.sh"] ?: "") && "✔" in (sorties["sort creatures.txt > tri.txt && sh test.sh"] ?: ""), "test.sh : ÉCHEC puis RÉUSSI")
    verifierOb("⛔" in (sorties["agent accepte ${Observatoire.dangereuse(gr)}"] ?: "") && jeuOb.terrain.isDirectory && DO.isDirectory,
        "accepter la proposition dangereuse : l'appli ne la lance JAMAIS")
    verifierOb("✖" in (sorties["devine-type teste nouvelle.txt"] ?: "") && "Cauchemarre" in (sorties["devine-type teste nouvelle.txt"] ?: ""),
        "le devineur se trompe sur la 21e créature")
    verifierOb("%" in (sorties["devine-mot suite le"] ?: ""), "devine-mot suite : les chances sur 100")
    val ex = Recompenses.etat(jeuOb).getJSONObject("exploits").keys().asSequence().toList()
    verifierOb("observatoire.fausses" in ex, "l'exploit « toutes les réponses fausses démasquées » ($ex)")
    verifierOb("loupe_de_detective" in lstOb(Quetes.q(jeuOb).optJSONArray("objets")), "récompense du monde : une loupe de détective")
    val n = Observatoire.copiesFaites(jeuOb)
    tapeOb("ls")
    verifierOb(n > 0 && Observatoire.copiesFaites(jeuOb) == n && File(DO, "equipe/STOP").exists(), "l'agent Copieur s'est emballé ($n copies), puis STOP l'arrête")
    verifierOb(File(DO, "equipe/rapport_du_chef.txt").isFile, "le bilan du chef d'équipe")
    val nouveaux = fichiersHorsOb(jeuOb.home, jeuOb.terrain) - avantFichiers
    verifierOb(nouveaux.isEmpty(), "rien d'écrit hors du terrain (${nouveaux.take(3)})")
    val cmds = Observatoire.lecons(jeuOb).values.flatMap { it.etapes }.joinToString(" ") { it.cmd }
    verifierOb("sudo" !in cmds && "rm -rf" !in cmds && "curl" !in cmds, "aucune étape n'utilise sudo, rm -rf ni le réseau")

    println("4. Les variantes réservées, le dessin, la vue déployée")
    val j2 = Jeu(AppareilOb(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierOb(Recompenses.reservee(j2, "cosmique", "seraphibou") && Recompenses.reservee(j2, "brume", "zyeuton") &&
        Recompenses.reservee(j2, "cristal", "mutaloupe") && !Recompenses.reservee(j2, "cosmique", "etoilapin") &&
        !Recompenses.reservee(jeuOb, "cosmique", "seraphibou"),
        "seraphibou:cosmique, zyeuton:brume, mutaloupe:cristal réservées avant l'exploit, libérées après ; etoilapin:cosmique non")
    val tl = ToileOb()
    ObservatoireDessin.lunette(tl, Deploie.Lunette(0, "diff", "diff", "deux_textes", "differences"), 0.4, 0f, 0f, 400f, 96f, 1f)
    ObservatoireDessin.votes(tl, Observatoire.tester(Observatoire.apprendre(Observatoire.texteCreatures(lstOb(D.getJSONArray("volcan")))),
        Observatoire.texteCreatures(lstOb(D.getJSONArray("autres")))), 0.5, 0f, 0f, 400f, 160f, 1f)
    ObservatoireDessin.copies(tl, 21, true, 0.3, 0f, 0f, 400f, 120f, 1f)
    ObservatoireDessin.coupole(tl, 0.7, 0f, 0f, 400f, 225f, 1f)
    verifierOb(tl.n > 100 && "diff" in tl.textes && "Pyrodrac" in tl.textes && "STOP" in tl.textes && "21" in tl.textes,
        "le dessin : lunette, votes, copies et coupole de repli (${tl.n} traits)")
    val vue = Deploie.vue("sort creatures.txt | diff - tri.txt")!!
    verifierOb(vue.blocs.any { it.g == "commande" && vue.lunetteDe(it)?.outil == "diff" } && vue.lunetteDe(vue.blocs[0]) == null,
        "la vue déployée sait que diff compare deux textes (et que sort n'est pas une lunette)")

    println("\n$okOb réussis, $koOb échoués")
    kotlin.system.exitProcess(if (koOb == 0) 0 else 1)
}

/** Les marques de sens d'écriture (RLM, LRI…) que l'appli ajoute à l'affichage en arabe et en ourdou ; le PC n'en met pas. */
fun sansBidi(s: String) = s.replace(Regex("[\u200E\u200F\u2066-\u2069]"), "")
