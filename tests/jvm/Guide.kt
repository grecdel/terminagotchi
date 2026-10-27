/*
 * Test JVM (hors téléphone) du guide, portage de pc/outils/test_guide.py : types des bestioles (biomes.json),
 * table des types, changer de guide, talents, régions gardées, combats à type, épreuve du jour, fatigue.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Guide.kt -d guide.jar
 *   java -cp <imitations>:<appli.jar>:guide.jar:kotlin-stdlib.jar GuideKt app/src/main/assets
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Combat
import fr.terminagotchi.Commandes
import fr.terminagotchi.Defis
import fr.terminagotchi.Entrainement
import fr.terminagotchi.Envies
import fr.terminagotchi.Equipe
import fr.terminagotchi.Explo
import fr.terminagotchi.Guide
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Parties
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsG(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilG(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsG(a)
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

fun bulles() = Vert.sansMarques((listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | "))
fun sans(s: String) = Vert.sansMarques(s)

fun especeDeType(ty: String): Bestiaire.Espece = Bestiaire.publiques().first { Guide.typeDe(it, "classique") == ty }

fun donner(ty: String): String {
    val e = especeDeType(ty)
    if ((0 until Explo.captures(jeu).length()).none { Explo.captures(jeu).getJSONObject(it).optString("espece") == e.nom }) {
        val ind = Bestiaire.individu(e, false, e.zone, "classique", 0.5).put("stade", "enfant").put("xp", 0)
        Explo.captures(jeu).put(ind)
    }
    return e.nom
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_guide_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilG(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    shell = Shell(jeu.home)
    jeu.module("explo").put("ouverte", true)
    Envies.heure = { 14 }
    Guide.nuit = { false }
    val cmds = Commandes(app, jeu, { shell.dossier })

    println("Les données des types")
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    verifier(File(assets, "biomes.json").readText() == File(depot, "donnees/biomes.json").readText(),
        "assets/biomes.json est la copie exacte de donnees/biomes.json")
    val d = JSONObject(File(assets, "biomes.json").readText())
    val parHabitat = HashMap<String, String>()
    val ts = d.getJSONArray("types")
    for (i in 0 until ts.length()) ts.getJSONObject(i).let { x -> val h = x.getJSONArray("habitats"); for (k in 0 until h.length()) parHabitat[h.getString(k)] = x.getString("id") }
    verifier((0 until ts.length()).map { ts.getJSONObject(it).getString("id") } == Guide.TYPES, "les 9 types, dans l'ordre de biomes.json")
    val faux = Bestiaire.publiques().flatMap { e -> e.variantes.map { v -> e to v.id } }.filter { (e, v) ->
        val attendu = if (v == "classique") d.getJSONObject("classique_par_espece").optString(e.id).ifEmpty { d.getJSONObject("classique_par_famille").optString(e.famille) }
            else parHabitat[v]
        Guide.typeDe(e, v) != attendu
    }
    verifier(faux.isEmpty(), "le type de chaque variante suit la règle de donnees/verifier_biomes.py (${faux.take(3).map { it.first.id + "/" + it.second }})")
    verifier(Guide.typeDe(Bestiaire.espece("abyssor")) in Guide.TYPES, "Abyssor a aussi un type")

    println("La table des types (la même que sur PC)")
    verifier(Guide.efficacite("eau", "feu") == 1.5 && Guide.efficacite("feu", "eau") == 0.67, "Eau > Feu (×1.5 / ×0.67)")
    verifier(Guide.efficacite("feu", "plante") == 1.5 && Guide.efficacite("plante", "eau") == 1.5, "Feu > Plante > Eau")
    verifier(Guide.efficacite("ciel", "eau") == 1.5 && Guide.efficacite("roche", "ciel") == 1.5, "Foudre > Eau, Roche > Foudre")
    verifier(Guide.efficacite("glace", "plante") == 1.5 && Guide.efficacite("machine", "glace") == 1.5 && Guide.efficacite("poison", "plante") == 1.5,
        "Glace > Plante, Machine > Glace, Poison > Plante")
    verifier(Guide.TYPES.all { a -> Guide.TYPES.all { b -> !(b in Guide.TABLE.getValue(a) && a in Guide.TABLE.getValue(b)) } }, "jamais fort l'un contre l'autre")
    verifier(Guide.TYPES.all { Guide.efficacite("ombre", it, false) == 1.0 && Guide.efficacite(it, "ombre") == 1.0 }, "l'Ombre est neutre le jour")
    verifier(Guide.TYPES.filter { it != "ombre" }.all { Guide.efficacite("ombre", it, true) == 1.5 }, "la nuit, l'Ombre est forte contre tous")
    verifier(Entrainement.FAMILLE_CMDS.keys.all { it in Guide.TALENTS.values } && Guide.TALENTS["ombre"] == "secrets", "chaque famille de la salle a un type ; Ombre : passages secrets")
    verifier(listOf(Guide.degats(1, 1.5), Guide.degats(2, 1.5), Guide.degats(3, 1.5), Guide.degats(1, 0.67), Guide.degats(2, 0.67), Guide.degats(3, 0.67)) == listOf(2, 3, 5, 1, 1, 2),
        "les cœurs : ×1.5 arrondi, ×0.67 au moins 1")
    verifier(Guide.typeDuJour(java.time.LocalDate.of(1970, 1, 1)) == "feu" && Guide.typeDuJour(java.time.LocalDate.of(1970, 1, 10)) == "feu",
        "le type du jour tourne sur les 9 types (comme sur PC)")

    println("Une ancienne partie : le compagnon est le guide")
    jeu.sauver()
    val f = Parties.fichierActif(app)
    val o = JSONObject(f.readText())
    o.getJSONObject("extra").remove("guide")
    o.remove("sceau")                       // une sauvegarde d'avant le sceau (Garde.kt)
    f.writeText(o.toString())
    jeu.recharger()
    verifier(Guide.actuel(jeu).id == "compagnon", "après migration, le guide est le compagnon")
    verifier(Guide.g(jeu).optString("type_c") == Guide.TYPES["Pixel".sumOf { it.code } % 9], "le compagnon reçoit un type (d'après son nom, comme sur PC)")
    verifier(Guide.typeCompagnonInitial("Zoé", "Force") == "feu", "un compagnon de forme Force est de type Feu")
    verifier(sans(cmds.executer("guide")!!.texte).contains("Ton guide"), "guide montre le guide")
    verifier(sans(cmds.executer("types")!!.texte).contains("est fort contre"), "types montre la table des types")

    println("Changer de guide")
    val plante = donner("plante")
    val feu = donner("feu")
    verifier(Guide.regionOuverte(jeu, "plante") && Guide.regionOuverte(jeu, "feu"), "les régions des types de l'équipe sont ouvertes")
    var r = sans(cmds.executer("equipe guide ${plante.lowercase()}")!!.texte)
    verifier(r.contains("🔄") && Guide.actuel(jeu).nom == plante, "equipe guide ${plante.lowercase()} : nouveau guide")
    verifier(Equipe.active(jeu)?.optString("id") == Guide.actuel(jeu).id, "le guide est aussi la bestiole active")
    verifier(r.contains("Bâtisseur"), "le message dit son talent")
    verifier(sans(cmds.executer("guide $plante")!!.texte).contains("déjà"), "même guide : « déjà ton guide »")
    verifier(sans(cmds.executer("guide licornix")!!.texte).contains("Je ne trouve pas"), "nom inconnu : message gentil")
    Equipe.choisir(jeu, feu)
    verifier(Guide.actuel(jeu).nom == feu, "troupe <nom> met aussi la bestiole en tête (guide)")
    r = sans(cmds.executer("equipe")!!.texte)
    verifier(r.contains("Guide") && r.contains("Feu"), "equipe (sans rien) : la troupe, avec le guide et les types")
    verifier(sans(cmds.executer("equipe epee_rouillee")!!.texte).isNotEmpty() && Guide.actuel(jeu).nom == feu, "equipe <objet> : toujours le donjon")
    Guide.choisir(jeu, "pixel")
    verifier(Guide.actuel(jeu).id == "compagnon", "on peut rendre la place au compagnon")

    println("Talents")
    Guide.choisir(jeu, plante)
    jeu.vus.addAll(listOf("mkdir", "touch", "date"))
    T.mkdirs()
    var xp0 = jeu.xp
    tape("date")
    val g1 = jeu.xp - xp0
    xp0 = jeu.xp
    tape("mkdir truc", T)
    verifier(jeu.xp - xp0 - g1 == 1, "guide Plante : +1 XP sur mkdir (pas sur date)")
    verifier(Guide.duTalent("plombier", "ls | wc -l") && Guide.duTalent("secrets", "ls -a") && Guide.duTalent("secrets", "cd .cachette") &&
        Guide.duTalent("cuisinier", "./recette.sh") && !Guide.duTalent("secrets", "cd ..") && Guide.duTalent("detective", "cd x && grep a b"),
        "les commandes de chaque talent sont reconnues")
    r = sans(Entrainement.commencer(jeu, "batisseur"))
    verifier(r.contains("te souffle"), "exercice Bâtisseur avec un guide Plante : une astuce de plus")
    xp0 = jeu.xp
    r = sans(Entrainement.reussir(jeu))
    val bonus = Regex("Talent de .*\\+(\\d+) XP").find(r)?.groupValues?.get(1)?.toInt() ?: 0
    val base = jeu.xp - xp0 - bonus
    verifier(bonus > 0 && bonus == maxOf(1, Math.ceil(base * 0.25).toInt()), "exercice réussi : +25 % d'XP arrondi au-dessus ($base → +$bonus)")
    Guide.choisir(jeu, feu)
    verifier(!sans(Entrainement.commencer(jeu, "batisseur")).contains("te souffle"), "avec un autre guide : pas d'astuce de talent")
    Entrainement.e(jeu).remove("cours")

    println("Régions gardées")
    File(T, "biome/glace").mkdirs()
    File(T, "biome/feu").mkdirs()
    jeu.bulle = ""; jeu.bulles.clear()
    tape("cd ${T.path}/biome/glace")
    verifier(bulles().contains("gardée"), "région Glace sans bestiole Glace : « gardée »")
    Guide.choisir(jeu, plante)
    jeu.bulle = ""; jeu.bulles.clear()
    tape("mkdir parcelle_9", File(T, "biome/feu"))
    verifier(bulles().contains("agrandir") && bulles().contains("guide ${feu.lowercase()}"), "agrandir la région Feu sans guide Feu : le dire, avec la commande")
    Guide.choisir(jeu, feu)
    verifier(Guide.peutAgrandir(jeu, "feu"), "avec un guide Feu, on peut l'agrandir")

    println("Combats à type")
    fun combatContre(tyMoi: String, tyLui: String): JSONObject {
        val moi = donner(tyMoi)
        Guide.choisir(jeu, moi)
        val lui = especeDeType(tyLui)
        val ind = Bestiaire.individu(lui, false, lui.zone, "classique", 0.5)
        jeu.module("dressage").put("en_cours", JSONObject().put("espece", lui.nom).put("rarete", "légendaire").put("variante", "classique")
            .put("ind", ind).put("taches", JSONArray()).put("faites", JSONArray()).put("mefiance", 100))
        Combat.preparer(jeu)
        Combat.de = { 0.0 }
        Combat.coup(jeu, "date")
        return jeu.module("dressage").getJSONObject("en_cours").getJSONObject("combat")
    }
    var cb = combatContre("eau", "feu")
    val lui = { c: JSONObject -> c.getJSONArray("lui").getInt(1) - c.getJSONArray("lui").getInt(0) }
    val journal = { c: JSONObject -> c.getJSONArray("journal").toString() }
    verifier(cb.getJSONArray("types").toString() == "[\"eau\",\"feu\"]" && lui(cb) == 2, "Eau contre Feu : un coup normal fait 2 cœurs")
    verifier(journal(cb).contains("super efficace"), "« C'est super efficace ! »")
    cb = combatContre("feu", "eau")
    verifier(lui(cb) == 1 && journal(cb).contains("pas très efficace"), "Feu contre Eau : au moins 1 cœur, « pas très efficace »")
    cb = combatContre("plante", "plante")
    verifier(lui(cb) == 1, "même type : ×1")
    jeu.module("dressage").remove("en_cours")

    println("Épreuve du jour")
    val ty = Guide.typeDuJour()
    val fort = Guide.fortsContre(ty)[0]
    Guide.choisir(jeu, donner(fort))
    xp0 = jeu.xp
    verifier(Guide.apresDefi(jeu) != null && jeu.xp - xp0 == Guide.BONUS_DEFI, "guide $fort contre le type du jour ($ty) : +5 XP")
    val faible = Guide.TYPES.first { it != "ombre" && Guide.efficacite(it, ty) <= 1 }
    Guide.choisir(jeu, donner(faible))
    verifier(Guide.apresDefi(jeu) == null, "un autre guide : pas de bonus (et pas de punition)")
    jeu.bulle = ""; jeu.bulles.clear()
    Defis.lancer(jeu)
    verifier(bulles().contains("Épreuve du jour"), "le défi éclair annonce le type du jour")
    jeu.module("defi").put("cmd", "")

    println("Fatigue et envies")
    Guide.choisir(jeu, plante)
    fun regler(fat: Double) {
        val g = Guide.g(jeu)
        g.getJSONObject("fatigue").put(g.optString("id"), fat)
        g.put("t", System.currentTimeMillis())
        val v = Envies.e(jeu).getJSONObject("v")
        v.put("sommeil", 80.0).put("jeu", 80.0)
        Envies.e(jeu).put("t", System.currentTimeMillis())
    }
    regler(0.0)
    repeat(10) { tape("date") }
    val s0 = Envies.valeur(jeu, "sommeil")
    val f0 = Guide.fatigue(jeu)
    regler(100.0)
    jeu.bulle = ""; jeu.bulles.clear()
    repeat(10) { tape("date") }
    val s1 = Envies.valeur(jeu, "sommeil")
    verifier(Math.abs(f0 - 10 * Guide.FATIGUE_COMMANDE) < 0.01, "10 commandes : le guide se fatigue de 5")
    verifier(s1 < s0 - 3, "un guide très fatigué use le sommeil plus vite ($s0 → $s1)")
    verifier(bulles().contains("bâille"), "fatigué : il le dit (et propose de changer de guide)")
    fun vieillir(ms: Long) { Guide.g(jeu).let { it.put("t", it.optLong("t") - ms).put("cmd_t", it.optLong("cmd_t") - ms) } }
    Guide.g(jeu).getJSONObject("fatigue").put("compagnon", 80.0)
    vieillir(3_600_000L)
    Guide.apresCommande(jeu, null, false)
    verifier(Guide.fatigue(jeu, "compagnon") <= 60.5, "sur le banc, on se repose (−20 par heure)")
    val fg = Guide.fatigue(jeu)
    vieillir(3_600_000L)
    Guide.apresCommande(jeu, null, false)
    verifier(Guide.fatigue(jeu) < fg, "le guide aussi se repose quand on ne joue pas")
    val g = Guide.g(jeu)
    for (m in Guide.membres(jeu)) g.getJSONObject("depuis").put(m.id, System.currentTimeMillis() - 3 * 24 * 3_600_000L)
    g.put("sortie_t", 0L).put("annonce", true)
    jeu.bulle = ""; jeu.bulles.clear()
    tape("date")
    verifier(sans(Guide.ecran(jeu)).contains("envie de sortir") && sans(Equipe.texte(jeu)).contains("envie de sortir"),
        "pas guide depuis 2 jours : 💭 envie de sortir")
    verifier(bulles().contains("sortir se promener"), "et une bulle gentille le propose")

    println("\n$ok réussis, $ko échoués")
    if (ko > 0) System.exit(1)
}
