/*
 * Test JVM (hors téléphone) des 6 envies, portage de pc/outils/test_envies.py : seuils, satisfaction de chacune,
 * poussière créée seulement dans le terrain de la partie active, sleep (le vrai shell, comme Shell.kt).
 *
 * Le jeu fait le même tour qu'après une commande tapée dans le terminal (Tour.apresCommande) ; le temps qui passe
 * est simulé en reculant les dates rangées dans la sauvegarde (module « envies »).
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Envies.kt -d envies.jar
 *   java -cp <imitations>:<appli.jar>:envies.jar:kotlin-stdlib.jar EnviesKt app/src/main/assets
 */
import fr.terminagotchi.Envies
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.NotifVie
import fr.terminagotchi.Parties
import fr.terminagotchi.Quetes
import fr.terminagotchi.Recherche
import fr.terminagotchi.Regles
import fr.terminagotchi.Shell
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsE(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilE(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsE(a)
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

/** L'enfant tape une commande : « cd » par Shell.kt, le reste vraiment (bash), puis le tour de jeu. */
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

/** Un tour de jeu sans commande (le temps qui passe, comme Tour.periodique). */
fun tour() { Tour.periodique(jeu, shell.dossier) }

fun e() = Envies.e(jeu)
fun v(k: String) = Envies.valeur(jeu, k)

/** Fixe des envies (et efface l'envie du moment) sans attendre. */
fun regler(vararg p: Pair<String, Double>) {
    val e = e()
    for ((k, x) in p) if (k == "faim") jeu.faim = x else e.getJSONObject("v").put(k, x)
    e.put("t", System.currentTimeMillis())
    e.remove("moment")
}

fun bulles() = Vert.sansMarques((listOf(jeu.bulle) + jeu.bulles.map { it.first }).joinToString(" | "))

fun proche(a: Double, b: Double, eps: Double = 0.05) = Math.abs(a - b) < eps

/** Les .tmp ou .cache apparus dans la maison de l'appli hors du terrain. */
fun horsTerrain(): List<File> = jeu.home.walkTopDown().filter {
    !it.path.startsWith(T.path) && (it.name == ".cache" || it.name.endsWith(".tmp"))
}.toList()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_envies_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilE(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    shell = Shell(jeu.home)
    jeu.module("explo").put("ouverte", true)
    Envies.heure = { 14 }                                  // le jour (le soir est testé à part)

    println("Une nouvelle partie")
    verifier(v("jeu") == 70.0 && v("curiosite") == 70.0 && v("explorer") == 70.0 && v("sommeil") == 90.0,
        "valeurs de départ (jeu, curiosité, exploration 70, sommeil 90)")
    verifier(v("proprete") == 100.0 && !T.exists(), "pas de terrain : propreté 100, rien n'est créé")

    println("Migration d'une ancienne sauvegarde")
    jeu.sauver()
    val f = Parties.fichierActif(app)
    val o = JSONObject(f.readText())
    o.getJSONObject("extra").remove("envies")
    o.put("total", 120).put("xp", 300)
    f.writeText(o.toString())
    jeu.recharger()
    jeu.tick()
    verifier(listOf("jeu", "curiosite", "explorer", "sommeil").all { proche(v(it), Envies.MIGRATION) },
        "les anciennes parties reçoivent des valeurs moyennes (${Envies.MIGRATION})")
    verifier(jeu.xp == 300 && jeu.total == 120 && jeu.nom == "Pixel", "rien d'autre n'est cassé (XP, total, nom)")

    println("Usure par commande et avec le temps")
    regler("jeu" to 80.0, "curiosite" to 80.0, "explorer" to 80.0, "sommeil" to 80.0, "faim" to 90.0)
    for (c in listOf("date", "whoami", "pwd", "date")) tape(c)
    verifier(proche(v("jeu"), 80 - 4 * 0.7) && proche(v("sommeil"), 80 - 4 * 0.4), "4 commandes : jeu −2.8, sommeil −1.6 (${v("jeu")}, ${v("sommeil")})")
    regler("jeu" to 30.0, "curiosite" to 80.0, "explorer" to 80.0, "sommeil" to 20.0)
    e().put("t", System.currentTimeMillis() - 3 * 3600_000L).put("cmd_t", System.currentTimeMillis() - 3 * 3600_000L)
    tour()
    verifier(proche(v("jeu"), Envies.PLANCHER_TEMPS), "le temps seul ne descend pas sous ${Envies.PLANCHER_TEMPS} (jeu ${v("jeu")})")
    verifier(proche(v("curiosite"), 80 - 3 * 1.5), "curiosité −1.5/h (${v("curiosite")})")
    verifier(proche(v("sommeil"), 20 + Envies.REPOS_HEURE * (3 - 1.0 / 6), 0.1), "sans jouer elle se repose toute seule (+25/h après 10 min : ${v("sommeil")})")
    jeu.faim = 50.0
    jeu.dernierTick = System.currentTimeMillis() - 7200_000L
    jeu.tick()
    verifier(proche(jeu.faim, 40.0, 0.1), "la faim descend 2 fois moins vite : −10 en 2 h (${jeu.faim})")

    println("Envie du moment et rappels espacés")
    regler("faim" to 90.0, "jeu" to 20.0, "curiosite" to 80.0, "explorer" to 80.0, "sommeil" to 80.0)
    val m = Envies.moment(jeu)
    verifier(m?.optString("e") == "jeu" && m.optString("cmd") in setOf("defi", "donjon", "ctf", "joue pierre"),
        "la plus basse sous ${Envies.SEUIL} : jeu → ${m?.optString("cmd")}")
    regler("faim" to 20.0, "jeu" to 10.0)
    verifier(Envies.moment(jeu)?.optString("e") == "faim", "la faim urgente (< 30) passe toujours devant")
    regler("faim" to 90.0, "jeu" to 80.0)
    verifier(Envies.moment(jeu) == null, "tout va bien : pas d'envie du moment")
    val vues = mutableSetOf<String>()
    repeat(40) { regler("faim" to 90.0, "jeu" to 30.0, "curiosite" to 35.0); vues.add(Envies.moment(jeu)!!.optString("e")) }
    verifier(vues == setOf("jeu", "curiosite"), "un peu de hasard entre les envies proches : $vues")
    regler("faim" to 90.0, "jeu" to 10.0, "curiosite" to 80.0)
    e().put("rappel_t", 0L).put("rappel_n", 0)
    jeu.bulle = ""; jeu.bulleFin = 0L; jeu.bulles.clear()
    repeat(11) { tape("date") }
    verifier(e().optLong("rappel_t") == 0L, "pas de rappel avant 12 commandes")
    tape("date")
    val tr = e().optLong("rappel_t")
    val texte = Envies.moment(jeu)?.optString("texte") ?: ""
    verifier(tr > 0 && "`" in texte && texte in (listOf(jeu.bulle) + jeu.bulles.map { it.first }),
        "au bout de 12 commandes : la bulle propose la commande, en vert ($texte)")
    repeat(14) { tape("date") }
    verifier(e().optLong("rappel_t") == tr, "12 commandes de plus, mais pas 5 minutes : pas de nouveau rappel")
    e().put("rappel_t", System.currentTimeMillis() - 5 * 60_000L - 1000)
    tape("date")
    verifier(e().optLong("rappel_t") > tr, "après 5 minutes et 12 commandes : un nouveau rappel")
    verifier(Envies.ENVIES.all { k -> Langue.liste("env.dit.$k").let { l -> l.size >= 5 && l.all { "`{cmd}`" in it } } },
        "au moins 5 phrases par envie, chacune avec la commande en vert")
    var langues = true
    for (code in listOf("fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur")) {
        val d = JSONObject(File(assets, "langues/$code.json").readText())
        if (!Envies.ENVIES.all { (d.optJSONArray("env.dit.$it")?.length() ?: 0) >= 5 }) langues = false
    }
    verifier(langues, "les 14 langues ont leurs phrases d'envies")

    println("Jeu 🎮")
    regler("jeu" to 20.0)
    e().put("moment", JSONObject().put("e", "jeu").put("cmd", "defi").put("t", System.currentTimeMillis()))
    jeu.bulle = ""; jeu.bulleFin = 0L; jeu.bulles.clear()
    val xp0 = jeu.xp
    jeu.module("defi").put("cmd", "pwd").put("debut", System.currentTimeMillis())
    tape("pwd")
    verifier(v("jeu") >= 20 + 35 - 1, "défi éclair réussi : jeu +35 (${v("jeu")})")
    verifier(jeu.xp >= xp0 + 10 + Envies.XP_BAS + Envies.XP_MOMENT, "récompense : l'XP du défi + l'XP de l'envie du moment")
    verifier(!e().has("moment") && Langue.liste("env.merci.jeu").any { it in bulles() }, "l'envie du moment satisfaite : un merci dans la bulle")
    for ((cle, n) in listOf("combat" to 30.0, "donjon" to 30.0, "ctf" to 40.0, "mini" to 15.0, "dressage" to 40.0)) {
        regler("jeu" to 10.0)
        Envies.plaisir(jeu, "jeu", cle)
        verifier(proche(v("jeu"), 10 + n), "$cle : jeu +$n")
    }

    println("Curiosité 📚")
    for (c in listOf("explique cp", "ls --help", "cherche copier")) {
        regler("curiosite" to 20.0)
        Envies.apresCommande(jeu, c, false)
        verifier(v("curiosite") >= 39.0, "$c : curiosité +20")
    }
    regler("curiosite" to 20.0)
    tape("uname")
    verifier(v("curiosite") >= 29.0, "une commande jamais goûtée : curiosité +10")
    regler("curiosite" to 20.0)
    jeu.etape = jeu.etape + 1
    Envies.apresCommande(jeu, null, true)
    jeu.etape = jeu.etape - 1
    verifier(v("curiosite") >= 34.0, "une étape de leçon : curiosité +15")

    println("Propreté 🧹 : la poussière")
    verifier(horsTerrain().isEmpty() && Envies.poussieres(jeu).isEmpty(), "pas encore de poussière, et aucun fichier hors du terrain")
    File(T, "vestibule").mkdirs()
    File(T, "nid").mkdirs()
    e().put("poussiere_t", System.currentTimeMillis() - 3 * Envies.POUSSIERE_INTERVALLE - 5000)
    jeu.bulle = ""; jeu.bulleFin = 0L; jeu.bulles.clear()
    tour()
    val ps = Envies.poussieres(jeu)
    verifier(ps.size == 3 && ps.all { it.parentFile == File(T, ".cache") }, "3 × 45 min : 3 fichiers dans .cache (${ps.map { it.name }})")
    verifier(proche(Envies.proprete(jeu), 100 - 3 * 12.5), "la jauge vient des vrais fichiers : ${Envies.proprete(jeu)}")
    verifier("Poussière" in ps[0].readText(), "chaque fichier dit ce qu'il est")
    verifier(".cache" in bulles() && "envies" in bulles(), "la première poussière : une bulle parle du placard caché et de « envies »")
    File(T, ".cache/poussiere_2.tmp").delete()
    verifier(proche(Envies.proprete(jeu), 75.0), "un fichier effacé à la main : la jauge remonte (75)")
    e().put("poussiere_t", System.currentTimeMillis() - 20 * Envies.POUSSIERE_INTERVALLE)
    tour()
    verifier(Envies.poussieres(jeu).size == Envies.POUSSIERE_MAX && Envies.proprete(jeu) == 0.0, "au plus ${Envies.POUSSIERE_MAX} fichiers : propreté 0")
    regler("faim" to 90.0, "jeu" to 80.0, "curiosite" to 80.0, "explorer" to 80.0, "sommeil" to 80.0)
    tape("cd ~")
    val mp = Envies.moment(jeu)!!
    verifier(mp.optString("e") == "proprete" && mp.optString("cmd") == "cd ~/terrain_terminagotchi",
        "depuis la maison, on propose d'abord d'aller dans le terrain (${mp.optString("cmd")})")
    tape("cd ~/terrain_terminagotchi")
    val m2 = Envies.moment(jeu)!!
    verifier(m2.optString("cmd") in setOf("ls -a", "ls .cache", "rm .cache/*.tmp"), "dans le terrain : ${m2.optString("cmd")}")
    tape("ls -a", T)
    tape("ls .cache", T)
    tape("find . -name \"*.tmp\"", T)
    val xp1 = jeu.xp
    tape("rm .cache/*.tmp", T)
    verifier(Envies.proprete(jeu) == 100.0 && File(T, ".cache").isDirectory, "rm .cache/*.tmp : tout propre, le placard reste")
    verifier(jeu.xp > xp1 && Langue.liste("env.merci.proprete").any { it in bulles() }, "satisfaite : XP et merci")
    tape("rm -r .cache", T)
    verifier(File(T, ".cache").isDirectory && Envies.poussieres(jeu).isEmpty(), "rm -r .cache : le jeu recrée le placard vide")
    verifier(horsTerrain().isEmpty(), "rien n'a été créé hors du terrain")
    val dehors = File(dossier, "dehors").apply { mkdirs() }
    File(T, ".cache").deleteRecursively()
    java.nio.file.Files.createSymbolicLink(File(T, ".cache").toPath(), dehors.toPath())
    e().put("poussiere_t", System.currentTimeMillis() - 2 * Envies.POUSSIERE_INTERVALLE)
    tour()
    verifier(dehors.listFiles()!!.isEmpty(), "un placard qui pointe ailleurs (lien) : aucun fichier écrit dehors")
    File(T, ".cache").delete()
    tour()

    println("Exploration 🧭")
    regler("explorer" to 20.0)
    tape("cd ~/terrain_terminagotchi/vestibule")
    verifier(v("explorer") >= 20 + 15 - 2, "une pièce jamais visitée : exploration +15 (${v("explorer")})")
    regler("explorer" to 20.0)
    tape("ls -a")
    verifier(v("explorer") >= 20 + 8 - 1, "ls -a dans la maison du jeu : exploration +8")
    regler("explorer" to 20.0)
    tape("cd ~")
    tape("ls -a")
    verifier(v("explorer") < 21, "ls -a hors de la maison du jeu : rien")
    regler("explorer" to 20.0)
    val q = Quetes.q(jeu)
    (q.optJSONArray("finies") ?: JSONArray().also { q.put("finies", it) }).put("q02")
    Envies.apresCommande(jeu, null, true)
    verifier(v("explorer") >= 59.0, "une pièce secrète trouvée (quête cachette) : exploration +40")

    println("Sommeil 😴")
    regler("sommeil" to 20.0, "faim" to 90.0, "jeu" to 80.0, "curiosite" to 80.0, "explorer" to 80.0)
    val t0 = System.currentTimeMillis()
    tape("sleep 1")
    verifier(System.currentTimeMillis() - t0 >= 1000, "sleep : une vraie pause du shell")
    verifier(proche(v("sommeil"), 20 - 0.4 + 5), "sleep 1 : +5 (${v("sommeil")})")
    regler("sommeil" to 20.0)
    jeu.anim = null
    Envies.apresCommande(jeu, "sleep 10", false)
    verifier(proche(v("sommeil"), 20 - 0.4 + 50), "sleep 10 : sommeil +50")
    verifier(jeu.anim?.first == "dort" && jeu.journal.any { "Sieste de 10 s" in it }, "animation « dort » et ligne de journal")
    verifier(Envies.dureeSieste("sleep 60")!! > Envies.SIESTE_MAX_TEL && Envies.dureeSieste("sleep 10") == 10.0,
        "une sieste plus longue que ${Envies.SIESTE_MAX_TEL} s est refusée par le terminal (le shell coupe à 20 s)")
    regler("sommeil" to 20.0)
    Envies.apresCommande(jeu, "sleep 100", false)
    verifier(v("sommeil") <= 20 + Envies.SIESTE_MAX, "une longue sieste rapporte au plus +50")
    val toutes = Envies.ENVIES.joinToString(" ") { Langue.liste("env.dit.$it").joinToString(" ") } + Langue.liste("env.soir").joinToString(" ")
    verifier(!Regex("suspend|shutdown|poweroff|hibernate|systemctl|veille|halt\\b", RegexOption.IGNORE_CASE).containsMatchIn(toutes),
        "aucune phrase ne propose de mettre en veille ou d'éteindre le téléphone")
    verifier(Envies.ENVIES.all { k -> (1..10).all { Envies.suggestion(jeu, k).split(" ")[0] !in setOf("reboot", "shutdown", "svc", "input", "am") } },
        "aucune suggestion n'éteint ni ne met en veille l'appareil")
    Envies.heure = { 21 }
    regler("sommeil" to 60.0)
    e().put("soir_t", 0L)
    jeu.bulle = ""; jeu.bulleFin = 0L; jeu.bulles.clear()
    tape("date")
    verifier(proche(v("sommeil"), 60 - Envies.SOMMEIL_SOIR), "le soir, elle fatigue plus vite (1.2 par commande)")
    verifier("bâille" in bulles() || "Il fait nuit" in bulles(), "le soir, elle bâille et propose d'arrêter (${bulles().take(70)})")
    val ts = e().optLong("soir_t")
    tape("date")
    verifier(e().optLong("soir_t") == ts, "un seul bâillement par 40 minutes")
    Envies.heure = { 14 }

    println("Humeur : les envies combinées, sans punition")
    regler("faim" to 90.0, "jeu" to 90.0, "curiosite" to 90.0, "explorer" to 90.0, "sommeil" to 90.0)
    verifier(Envies.humeurCle(jeu) == "humeur.joyeux", "tout est haut : joyeux")
    regler("jeu" to 0.0)
    verifier(Envies.humeurCle(jeu) == "humeur.triste" && jeu.humeur() == "triste", "une envie à zéro : triste")
    regler("curiosite" to 0.0)
    verifier(Envies.humeurCle(jeu) == "humeur.grognon", "deux envies à zéro : grognon")
    regler("faim" to 20.0)
    verifier(Envies.humeurCle(jeu) == "humeur.affame", "la faim reste la plus importante")
    regler("faim" to 0.0, "jeu" to 0.0, "curiosite" to 0.0, "explorer" to 0.0, "sommeil" to 0.0)
    tape("date")
    verifier(jeu.existe && jeu.faim > 0, "tout à zéro : elle mange, elle est toujours là")

    println("Affichage et aide")
    regler("faim" to 90.0, "jeu" to 10.0, "curiosite" to 50.0, "explorer" to 80.0, "sommeil" to 30.0)
    val c = Envies.compact(jeu)
    verifier(Envies.ICONES.values.all { it in c } && c.lines().size == 2, "les 6 envies en petit (2 lignes) : widget, en-tête, notification dépliée")
    val r = NotifVie.jauges(jeu)
    verifier(listOf("🎮", "😴", "📚").all { it in r } && "🍎" !in r && "⭐" in r, "notification réduite : les 3 plus basses et l'XP ($r)")
    verifier(NotifVie.phrase(jeu).startsWith("💭") || jeu.bulleActive().isNotEmpty(), "notification : l'envie du moment (${NotifVie.phrase(jeu)})")
    jeu.bulle = ""; jeu.bulleFin = 0L; jeu.bulles.clear()
    verifier(jeu.infoWidget().startsWith("💭") || jeu.etapeCourante() != null, "widget : l'envie du moment (${jeu.infoWidget()})")
    val ecran = Vert.sansMarques(Envies.ecran(jeu))
    verifier(Envies.ENVIES.all { Envies.nom(it) in ecran } && "rm .cache/*.tmp" in ecran && "sleep 10" in ecran && "Pour les grands" in ecran,
        "envies : l'état détaillé, et comment satisfaire chacune")
    verifier("envies" in Vert.sansMarques(t("env.aide.tel")), "aide mentionne envies")
    verifier(Regles.LEXIQUE.any { it.cmd == "envies" }, "le lexique mentionne envies")
    verifier("envies" in Recherche.chercher("envie"), "la recherche trouve envies")

    println("\n$ok réussis, $ko échoués")
    if (ko > 0) System.exit(1)
}
