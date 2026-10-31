/*
 * Test JVM (hors téléphone) de la satiété (Satiete.kt), portage de pc/outils/test_satiete.py :
 *   1. les vecteurs partagés avec Python (donnees/satiete/vecteurs.json) : mêmes états, aliments, heures d'éveil, XP,
 *      série, éclat de l'aura, et le même scénario de 9 jours rejoué sur une vraie partie (Jeu) ;
 *   2. les 7 points validés (veille et repas complet, évolution qui attend sans rien perdre, vacances, assiette…) ;
 *   3. une simulation de 14 jours, trois rythmes de jeu (tous les jours, un jour sur deux, une semaine d'absence),
 *      avec une horloge simulée (Satiete.maintenant) et de vraies commandes mangées (Jeu.manger) ;
 *   4. les suites du rapport v3 côté téléphone (commandes « pas encore » sans XP, noms des lieux d'habitat).
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Satiete.kt -d satiete.jar
 *   java -cp <imitations>:<appli.jar>:satiete.jar:kotlin-stdlib.jar SatieteKt app/src/main/assets
 */
import fr.terminagotchi.Aura
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Regles
import fr.terminagotchi.Satiete
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.TimeZone

class ActifsS(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilS(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsS(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okS = 0
var koS = 0

fun verifierS(c: Boolean, m: String) {
    if (c) okS++ else koS++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var appS: AppareilS
lateinit var assetsS: File
var horlogeS = 0.0

/** Un instant du lundi 2 novembre 2026 (+ j jours) à h:mn (UTC). */
fun ts(j: Int, h: Int, mn: Int = 0) = 1793577600.0 + j * 86400 + h * 3600 + mn * 60

/** Une partie neuve (son propre dossier) : « Pixel », éclose. */
fun nouvellePartie(): Jeu {
    val d = File(System.getProperty("java.io.tmpdir"), "tg_satiete_" + System.nanoTime()).apply { mkdirs() }
    val a = AppareilS(d, assetsS)
    val j = Jeu(a)
    j.changerLangue("fr")
    j.nom = "Pixel"
    return j
}

fun liste(a: JSONArray) = (0 until a.length()).map { a.get(it) }

fun main(args: Array<String>) {
    TimeZone.setDefault(TimeZone.getTimeZone("UTC"))         // les vecteurs sont en heure UTC (comme le test Python)
    val assets = File(args[0])
    assetsS = assets
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_satiete_" + System.nanoTime()).apply { mkdirs() }
    appS = AppareilS(dossier, assets)
    Langue.init(appS)
    Langue.definir("fr")
    Satiete.maintenant = { horlogeS }
    horlogeS = ts(0, 16)
    val v = JSONObject(File("donnees/satiete/vecteurs.json").readText())

    println("1. Les vecteurs partagés avec Python (donnees/satiete/vecteurs.json)")
    fun tous(k: String, f: (JSONArray) -> Boolean): Pair<Boolean, String> {
        val a = v.getJSONArray(k)
        for (i in 0 until a.length()) if (!f(a.getJSONArray(i))) return false to a.getJSONArray(i).toString()
        return true to ""
    }
    var r = tous("etat") { Satiete.etatDe(it.getDouble(0), it.getBoolean(1)) == it.getString(2) }
    verifierS(r.first, "les 4 états ${r.second}")
    r = tous("famille") { (Satiete.famille(it.getString(0)) ?: "null") == (if (it.isNull(1)) "null" else it.getString(1)) }
    verifierS(r.first, "les familles de commandes (aliments) ${r.second}")
    r = tous("eveil") { Math.abs(Satiete.secondesEveil(it.getDouble(0), it.getDouble(1)) - it.getDouble(2)) < 1e-6 }
    verifierS(r.first, "les secondes d'éveil (7 h - 21 h) ${r.second}")
    r = tous("taux") { Math.abs(Satiete.taux(it.getBoolean(0), it.getInt(1), it.getInt(2)) - it.getDouble(3)) < 1e-9 }
    verifierS(r.first, "le rythme de la faim (Gardien, Endurance, lien) ${r.second}")
    r = tous("repas") { Satiete.valeurRepas(it.getBoolean(0), it.getBoolean(1), it.getBoolean(2), it.getInt(3), it.getBoolean(4)) == it.getDouble(5) }
    verifierS(r.first, "ce que nourrit une commande ${r.second}")
    r = tous("xp") { Satiete.xpAjuste(it.getInt(0), it.getString(1), it.getInt(2)) == (it.getInt(3) to it.getInt(4)) }
    verifierS(r.first, "l'XP ajustée (+20 %, −20 %, −40 %, restes) ${r.second}")
    r = tous("serie") { Satiete.serieManquee(it.getInt(0)) == it.getInt(1) && Satiete.palierSerie(it.getInt(0)) == it.getInt(2) }
    verifierS(r.first, "la série (un cran de moins, médailles) ${r.second}")
    r = tous("minuit") { Satiete.minuitApres(it.getDouble(0)) == it.getDouble(1) }
    verifierS(r.first, "le minuit suivant ${r.second}")
    r = tous("aura") { Aura.niveauSatiete(it.getInt(0), it.getInt(1), it.getBoolean(2)) == it.getInt(3) }
    verifierS(r.first, "l'éclat de l'aura selon l'état ${r.second}")

    val sc = v.getJSONObject("scenario")
    val pas = sc.getJSONArray("pas")
    val attendu = sc.getJSONArray("attendu")
    val jeu = nouvellePartie()
    val s = Satiete.s(jeu)
    jeu.faim = 70.0; jeu.dernierTick = (ts(0, 16) * 1000).toLong(); s.put("repas_t", ts(0, 16))
    var ecart: String? = null
    for (i in 0 until pas.length()) {
        val p = pas.getJSONArray(i)
        val now = ts(p.getInt(0), p.getInt(1), p.getInt(2))
        horlogeS = now
        if (p.getString(3) == "tick") Satiete.tick(jeu, now)
        else Satiete.repas(jeu, p.getString(4), p.getInt(5) == 1, p.getInt(6) == 1, p.getInt(7) == 1, now)
        val e = attendu.getJSONArray(i)
        val a = listOf(Math.round(jeu.faim * 1000) / 1000.0, Satiete.etatDe(jeu.faim, s.optBoolean("veille")), s.optInt("jours"),
            s.optInt("serie"), (0 until s.getJSONArray("assiette").length()).map { s.getJSONArray("assiette").getString(it) }.toSet().size, jeu.xp)
        val b = listOf(e.getDouble(0), e.getString(1), e.getInt(2), e.getInt(3), e.getInt(4), e.getInt(5))
        if (a != b && ecart == null) ecart = "pas $i : Kotlin $a, Python $b"
    }
    verifierS(ecart == null, "le scénario de 9 jours donne la même chose qu'en Python ${ecart ?: ""}")

    println("2. Les 7 points validés")
    val k = nouvellePartie()
    val sk = Satiete.s(k)
    horlogeS = ts(1, 9)
    k.faim = 80.0; k.dernierTick = (ts(1, 9) * 1000).toLong()
    Satiete.vacances(k, true)
    Satiete.tick(k, ts(6, 9))
    verifierS(k.faim == 80.0, "en vacances : la faim est en pause")
    Satiete.vacances(k, false)
    k.faim = 20.0
    Satiete.tick(k, ts(7, 20))
    verifierS(Satiete.etat(k) == "veille", "sous 15 : en veille (${"%.1f".format(k.faim)}), jamais morte")
    horlogeS = ts(8, 9)
    for (c in listOf("pwd", "pwd", "ls")) Satiete.repas(k, c, now = ts(8, 9))
    verifierS(sk.optBoolean("veille"), "2 commandes différentes ne suffisent pas")
    Satiete.repas(k, "date", now = ts(8, 9))
    verifierS(!sk.optBoolean("veille") && k.faim >= Satiete.REVEIL_FAIM, "3 commandes différentes : réveillée et en forme")
    k.faim = 90.0; k.xp = 150; sk.put("jours", 1)
    k.ajouterXp(30)
    verifierS(k.xp == 159 && sk.optInt("reserve") == 21, "pas assez de jours soignés : l'évolution attend (xp ${k.xp}, réserve ${sk.optInt("reserve")})")
    verifierS(Satiete.niveauAppris(k) == 5 && Satiete.plafond(k) == 4, "l'XP de côté compte, la leçon ne demande jamais plus")
    sk.put("jours", 3)
    Satiete.liberer(k)
    verifierS(k.xp == 180 && k.stade == 2, "3 jours soignés : elle grandit, rien n'est perdu (${k.xp})")
    k.faim = 30.0
    verifierS(Satiete.affamee(k) && Satiete.gagnerXp(k, 20, lecon = true) == 20, "affamée : une leçon ne perd jamais d'XP")
    verifierS(Satiete.xpAjuste(10, "affamee").first == 8, "affamée : −20 % sur les commandes")
    k.faim = 20.0
    val avant = k.faim
    for (i in 0 until 10) Satiete.repas(k, "ls", repetee = i > 0, now = ts(9, 10, i))
    val ls10 = k.faim - avant
    k.faim = 20.0
    for ((i, c) in listOf("pwd", "mkdir", "cat", "ping", "chmod").withIndex()) Satiete.repas(k, c, now = ts(9, 11, i))
    verifierS(ls10 < 10 && k.faim - 20.0 >= 15, "`ls` dix fois : +${"%.1f".format(ls10)} ; un repas varié : +${"%.1f".format(k.faim - 20)}")
    for ((i, c) in listOf("touch", "head", "curl", "id", "uptime", "lampe").withIndex()) Satiete.repas(k, c, now = ts(9, 12, i))
    verifierS(sk.optBoolean("complete") && Satiete.nbAssiette(k).let { true }, "les 6 familles : assiette complète")
    sk.put("repas_t", ts(9, 12)); k.faim = 0.0; sk.put("veille", true)
    verifierS(Satiete.absente(k, ts(40, 12)), "30 jours sans repas : elle se repose dans son biome")
    Satiete.repas(k, "ls", now = ts(40, 12))
    verifierS(!sk.optBoolean("veille") && k.faim >= Satiete.RETOUR_FAIM, "au retour, rien n'est perdu")

    println("3. Simulation de 14 jours (trois rythmes de jeu)")
    val cmds = listOf("pwd", "ls", "cd", "mkdir", "echo", "cat", "grep", "chmod", "cp", "mv", "date", "whoami", "ping", "head",
        "tail", "find", "wc", "sort", "touch", "rm", "df", "id", "uptime", "lampe", "batterie", "stat", "tree", "du", "rev", "ps")
    val rythmes = mapOf("tous les jours" to (0 until 14).toList(), "un jour sur deux" to (0 until 14 step 2).toList(),
        "une semaine d'absence" to listOf(0, 1, 2, 10, 11, 12, 13))
    val bilan = mutableMapOf<String, List<Triple<String, Int, Int>>>()
    for ((nom, jours) in rythmes) {
        val j = nouvellePartie()
        val sj = Satiete.s(j)
        horlogeS = ts(0, 16, 50); j.dernierTick = (horlogeS * 1000).toLong()
        var vue = 0
        var total = 0
        var perdu = false
        val lignes = mutableListOf<Triple<String, Int, Int>>()
        for (d in 0 until 14) {
            if (d !in jours) continue
            horlogeS = ts(d, 17); j.tick()
            val debut = Satiete.etat(j)
            for (n in 0 until 30) {                       // 20 minutes : une commande toutes les 40 s
                horlogeS = ts(d, 17) + 40.0 * n
                j.tick()
                val c = if (n % 3 == 0 && vue < cmds.size) cmds[vue++] else cmds[(n * 7 + d) % minOf(vue.coerceAtLeast(1), cmds.size)]
                j.manger(c, false)
                val t = j.xp + sj.optInt("reserve")
                if (t < total) perdu = true
                total = t
            }
            lignes.add(Triple(debut, sj.optInt("serie"), j.stade))
        }
        bilan[nom] = lignes
        verifierS(!perdu, "$nom : jamais d'XP perdue (réserve comprise)")
        verifierS(lignes.map { it.third } == lignes.map { it.third }.sorted(), "$nom : le stade ne baisse jamais ${lignes.map { it.third }}")
        println("     $nom : ${lignes.joinToString(" ") { "${it.first}/${it.second}" }}")
    }
    verifierS(bilan.getValue("tous les jours").all { it.first in setOf("forme", "rassasiee") }, "tous les jours : jamais affamée au début")
    verifierS(bilan.getValue("un jour sur deux").all { it.first in setOf("forme", "rassasiee") }, "un jour sur deux : en forme à chaque retour")
    verifierS(bilan.getValue("un jour sur deux").last().second >= 12, "un jour sur deux : la série continue (jours sans jeu finis en forme)")
    val retour = bilan.getValue("une semaine d'absence")[3]
    verifierS(retour.first in setOf("affamee", "veille") && retour.second >= 1, "une semaine d'absence : ${retour.first} au retour, série gardée en partie (${retour.second})")

    println("4. Suites du rapport v3 (téléphone)")
    val p = nouvellePartie()
    p.module("debloc").put("mode", "progressif").put("ouverts", JSONArray())
    val x0 = p.xp
    val bloque = Intro.bloque(p, "envies") != null
    p.manger("envies", false)
    verifierS(!bloque || p.xp == x0, "une commande « pas encore » ne donne pas d'XP (bloquée : $bloque)")
    verifierS(Maison.nomPiece("abyssal") == "Abysses" && Maison.nomPiece("mecanique") == "Atelier des engrenages",
        "les lieux d'habitat ont de vrais noms (Abysses, Atelier des engrenages)")
    for (code in listOf("en", "ja", "ar")) {
        Langue.definir(code)
        verifierS(Maison.nomPiece("mecanique") != "mecanique", "$code : mecanique → « ${Maison.nomPiece("mecanique")} »")
    }
    Langue.definir("fr")
    verifierS(Satiete.lignes(p).size >= 6, "l'écran de la satiété : état, effet, assiette, série, biome, vacances")

    println("\n$okS réussis, $koS échoués")
    kotlin.system.exitProcess(if (koS > 0) 1 else 0)
}
