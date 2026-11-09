/*
 * Test JVM de l'allègement du 9 novembre (variante B « terminal + mission ») sur Android, portage de
 * pc/outils/test_mission.py :
 *   1. les vecteurs communs donnees/mission/vecteurs.json (Mission.kt = pc/tg/mission.py ; Envies.emojiDe = envies.EMOJIS) ;
 *   2. une partie : la ligne 🎯 suit la leçon, le terrain effacé, le défi éclair ; le détail derrière le + garde tout
 *      (la commande, « Pour les grands », « Dans un vrai terminal ») ; UNE humeur ; 💭 quand une envie est forte ;
 *   3. les textes des boutons du menu ☰, de la fiche et des réglages existent dans les 14 langues.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Mission.kt -d mission.jar
 *   java -cp <imitations>:<appli.jar>:mission.jar:kotlin-stdlib.jar MissionKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Envies
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Mission
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import org.json.JSONObject
import java.io.File

class ActifsM(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilM(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsM(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okM = 0
var koM = 0
fun verifierM(c: Boolean, m: String) {
    if (c) okM++ else koM++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Sans les lettres sosies (anti copier-coller, Regles.piege) ni les backticks. */
fun platM(s: String?): String {
    var x = (s ?: "").replace("`", "")
    val homo = mapOf('a' to 'а', 'c' to 'с', 'e' to 'е', 'o' to 'о', 'p' to 'р', 'x' to 'х',
        'y' to 'у', 'i' to 'і', 's' to 'ѕ', 'd' to 'ԁ', 'h' to 'һ', 'j' to 'ј')      // = Regles.HOMO (privée)
    for ((a, b) in homo) x = x.replace(b.toString(), a.toString())
    return x.replace(' ', ' ')
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_mission_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilM(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    Intro.init(app)

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/mission/vecteurs.json").readText())
    val cas = v.getJSONArray("mission")
    var faux = 0
    for (i in 0 until cas.length()) {
        val c = cas.getJSONObject(i)
        val o = c.getJSONObject("v")
        val m = o.keys().asSequence().associateWith { k -> o.get(k) }
        val r = Mission.formater(c.getString("genre"), m)
        if (r != c.getString("ligne")) { faux++; println("    ≠ ${c.getString("genre")} : « $r » au lieu de « ${c.getString("ligne")} »") }
    }
    verifierM(faux == 0, "Mission.formater = mission.formater (${cas.length()} cas)")
    val em = v.getJSONObject("emojis")
    verifierM(em.keys().asSequence().all { Envies.emojiDe(it) == em.getString(it) } && Envies.emojiDe("???") == v.getString("inconnu"),
        "Envies.emojiDe = envies.EMOJIS (une seule humeur à l'écran)")

    println("2. Une partie")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    Intro.nouvellePartie(jeu)
    jeu.sauver()
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })
    fun tape(cmd: String, code: Int = 0) {
        commandes.executer(cmd)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier, code = code)
    }
    verifierM(Mission.ligne(jeu) == null || Intro.enCours(jeu), "pendant l'œuf : pas de ligne 🎯 (l'œuf a sa liste)")
    for (c in listOf("pwd", "ls", "echo bonjour", "whoami")) tape(c)
    if (Intro.enCours(jeu)) Commandes(app, jeu, { shell.dossier }).executer("debloquer tout")
    val c = Histoire.leconCourante(jeu)
    val m = Mission.ligne(jeu)
    verifierM(c != null && m != null && m.startsWith("🎯") && c.titre in m, "après l'éclosion : « ${platM(m)} »")
    if (c != null && jeu.niveau >= c.niveau) {
        val e = c.etapes[jeu.etape]
        verifierM(platM(m).contains(e.cmd.split(" ")[0]), "la commande de l'étape est sur la ligne 🎯")
        val d = Mission.detail(jeu)
        verifierM(platM(d).contains(e.cmd) && (e.adulte == null || "🧑" in d), "derrière le + : la commande et 🧑 « Pour les grands »")
    }
    jeu.module("defi").put("cmd", "whoami").put("debut", System.currentTimeMillis())
    verifierM(Mission.choisir(jeu)?.first == "defi" && "whoami" in platM(Mission.ligne(jeu)), "le défi éclair passe devant (bandeau compact)")
    jeu.module("defi").remove("cmd")
    verifierM(Envies.emoji(jeu).isNotEmpty(), "une seule humeur : ${Envies.emoji(jeu)}")
    verifierM(Envies.pensee(jeu) == (Envies.moment(jeu) != null || fr.terminagotchi.Creature.envie(jeu) != null), "💭 = une envie forte ou l'envie mystère")

    println("3. Les textes du téléphone (14 langues)")
    val cles = listOf("mis.tape", "mis.niveau", "mis.a_toi", "ui.fiche.titre", "ui.lecon.titre", "ui.lecon.vide", "ui.detail.dit",
        "ui.menu.titre", "ui.menu.pixel.sous", "ui.menu.carte", "ui.menu.carte.sous", "ui.menu.lecon.sous", "ui.menu.lexique",
        "ui.menu.lexique.sous", "ui.menu.perdu", "ui.menu.perdu.sous", "ui.menu.onglets", "ui.menu.onglets.sous",
        "ui.menu.reglages", "ui.menu.reglages.sous", "ui.fermer", "ui.fiche.envies", "ui.fiche.forces", "ui.fiche.album",
        "ui.fiche.aura", "ui.fiche.devinette", "ui.reg.titre", "ui.reg.pur", "ui.reg.pur.aide", "ui.reg.oui", "ui.reg.non",
        "ui.reg.son", "ui.reg.confort", "ui.reg.langue", "ui.pur.on", "ui.pur.off")
    val manque = mutableListOf<String>()
    for (f in File(assets, "langues").listFiles()!!.filter { it.name.endsWith(".json") }) {
        val d = JSONObject(f.readText())
        for (k in cles) if (d.optString(k).isEmpty()) manque.add("${f.nameWithoutExtension}:$k")
    }
    verifierM(manque.isEmpty(), "toutes les clés existent" + if (manque.isEmpty()) "" else " (manque : ${manque.take(5)})")
    verifierM(t("ui.menu.titre") == "Menu", "en français : « Menu »")

    println("\n$okM réussis, $koM ratés")
    dossier.deleteRecursively()
    if (koM > 0) System.exit(1)
}
