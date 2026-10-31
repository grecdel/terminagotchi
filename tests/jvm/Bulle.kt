/*
 * Test JVM (hors téléphone) de la bulle et de l'île Android (Poses.kt, BureauVie.kt), comme pc/outils/test_bureau.py :
 *   1. assets/poses.bin : les 27 bébés de départ × 12 poses, les mêmes octets qu'en Python (empreintes FNV),
 *      des ancres dans l'image, des couleurs opaques ou vides ;
 *   2. le comportement (marche, sommeil, réveil, batterie, repas, déplacer, ranger), les gestes (appui, double,
 *      triple, appui long, glisser vers le bas), le menu rond (7 boutons sans chevauchement), l'île et ses événements.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Bulle.kt -d bulle.jar
 *   java -cp <imitations>:<appli.jar>:bulle.jar:kotlin-stdlib.jar BulleKt app/src/main/assets
 */
import fr.terminagotchi.BureauVie
import fr.terminagotchi.Poses
import java.io.File

var okB = 0
var koB = 0

fun verifB(c: Boolean, m: String) {
    if (c) okB++ else koB++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun fnvB(v: IntArray, debut: Int): Long {
    var h = 0x811C9DC5L
    for (i in debut until v.size) h = ((h xor (v[i].toLong() and 0xFF)) * 0x01000193L) and 0xFFFFFFFFL
    return h
}

fun main(args: Array<String>) {
    val assets = File(args.getOrElse(0) { "app/src/main/assets" })
    println("Les poses dessinées (poses.bin)")
    verifB(Poses.lire(File(assets, "poses.bin").readBytes()), "poses.bin se lit")
    verifB(Poses.especes().size == 27, "27 bébés de départ (${Poses.especes().size})")
    val attendu = mapOf("braisillon" to 697930007L, "glandouille" to 566876390L, "lunacorne" to 2984212012L)
    for ((e, h) in attendu) {
        val (idx, pal) = Poses.indexees(e)!!
        var hh = 0x811C9DC5L
        for (n in Poses.NOMS) { val v = idx.getValue(n); for (i in 4 until v.size) hh = ((hh xor v[i].toLong()) * 0x01000193L) and 0xFFFFFFFFL }
        verifB(hh == h && pal.size == 48, "$e : mêmes octets qu'en Python (empreinte $hh)")
    }
    val g = Poses.indexees("glandouille")!!.first.getValue("assis")
    verifB(g[0] == 131 && g[1] == 127 && g[2] == 65 && g[3] == 127, "glandouille assis : 131 × 127, ancre (65, 127) comme en Python")
    var bons = true
    for (e in Poses.especes()) {
        val a = Poses.dessine(e) ?: run { bons = false; null } ?: continue
        for (etat in Poses.ETATS) for (c in a.images(etat)) {
            if (c.ax !in 0..c.w || c.ay !in 1..c.h || c.argb.any { it != 0 && (it ushr 24) != 255 }) bons = false
        }
        if (a.images("marche").size != 4 || !a.lisse || !a.dessine) bons = false
    }
    verifB(bons, "chaque espèce : 9 états, 4 images de marche, ancres dans l'image, pixels opaques ou vides")
    val sh = Poses.dessine("braisillon", 0.5)!!.image("assis", 0).argb
    verifB(!sh.contentEquals(Poses.dessine("braisillon")!!.image("assis", 0).argb), "shiny : la teinte change")

    println("Le comportement")
    var c = BureauVie.Creature(1000f, h = java.util.Random(3))
    var xmin = 1e9f; var xmax = -1f
    val etats = mutableSetOf<String>()
    repeat(3000) { c.tick(0.1, BureauVie.Signaux(1.0)); xmin = minOf(xmin, c.x); xmax = maxOf(xmax, c.x); etats.add(c.etat) }
    verifB(xmin >= 40f && xmax <= 960f, "elle marche sans sortir de l'écran")
    verifB("marche" in etats && "assis" in etats && "dort" !in etats, "elle marche et s'assoit ($etats)")
    c.tick(0.1, BureauVie.Signaux(c.sommeil + 1))
    verifB(c.etat == "dort", "longtemps sans commande : elle s'endort")
    c.reagir("mange")
    verifB(c.etat == "dort", "elle dort : pas de repas")
    c.tick(0.1, BureauVie.Signaux(0.5))
    verifB(c.etat == "etire", "une commande : elle se réveille en s'étirant")
    c = BureauVie.Creature(1000f, h = java.util.Random(4))
    var baille = false
    repeat(1300) { c.tick(0.1, BureauVie.Signaux(1.0, 9, false)); baille = baille || c.etat == "baille" }
    verifB(baille, "batterie faible : elle bâille")
    c = BureauVie.Creature(1000f, surPlace = true, h = java.util.Random(5))
    val x0 = c.x
    repeat(2000) { c.tick(0.1, BureauVie.Signaux(1.0)) }
    verifB(c.x == x0, "« rester sur place »")
    c.prendre(); c.deplacer(300f, 400f); c.tick(0.1)
    verifB(c.air == 400f && c.x == 300f, "appui long : elle suit le doigt")
    c.lacher(); repeat(30) { c.tick(0.05) }
    verifB(c.air == 0f, "lâchée : elle retombe en bas de l'écran")
    c.ranger()
    verifB(c.rangee && (c.x == c.bord || c.x == c.largeur - c.bord), "rangée dans un coin")
    repeat(500) { c.tick(0.1, BureauVie.Signaux(1.0)) }
    verifB(c.etat != "marche", "rangée : elle ne se promène plus")

    println("Les gestes")
    val ge = BureauVie.Gestes()
    fun appui(t: Double) { ge.appuyer(10f, 10f, t); ge.relacher(10f, 10f, t + 0.05) }
    appui(0.0)
    verifB(ge.attendre(0.1) == null && ge.attendre(0.5) == "appui", "un appui : le menu")
    appui(1.0); appui(1.2)
    verifB(ge.attendre(1.7) == "double", "double appui : un cœur")
    appui(2.0); appui(2.2); ge.appuyer(10f, 10f, 2.4)
    verifB(ge.relacher(10f, 10f, 2.45) == "triple", "triple appui : une phrase")
    ge.appuyer(10f, 10f, 3.0)
    verifB(!ge.tenir(3.2) && ge.tenir(3.5) && ge.bouger(200f, 10f, 3.6), "appui long : on la déplace")
    verifB(ge.relacher(200f, 10f, 3.7) == "glisse_fin", "fin du déplacement")
    ge.appuyer(10f, 10f, 5.0); ge.bouger(12f, 150f, 5.1)
    verifB(ge.relacher(12f, 150f, 5.15) == "ranger", "glisser vite vers le bas : la ranger")

    println("Le menu rond et l'île")
    val lib = BureauVie.MENU.associate { it.first to it.first.replaceFirstChar { ch -> ch.uppercase() } }
    for (x in listOf(30f, 540f, 1050f)) {
        val (b, _) = BureauVie.menuPositions(x, 700f, 76f, lib, 14f, 1080f, 760f, 120f)
        val chev = b.indices.any { i -> (i + 1 until b.size).any { j ->
            !(b[i].x + b[i].w <= b[j].x || b[j].x + b[j].w <= b[i].x || b[i].y + b[i].h <= b[j].y || b[j].y + b[j].h <= b[i].y) } }
        verifB(b.size == 7 && !chev && b.all { it.x >= 0 && it.x + it.w <= 1080 && it.y >= 0 }, "7 boutons dans l'écran, sans chevauchement (x = $x)")
        verifB(b.minByOrNull { it.y }!!.cle == "jouer", "« Jouer » en haut")
    }
    // un vrai téléphone : 393 dp de large, textes de 14 dp (× 2,75 pixels par dp)
    val k = 2.75f
    for (x in listOf(40f, 196f, 360f)) {
        val (b, _) = BureauVie.menuPositions(x * k, 380f * k, 56f * k, lib, 14f * k, 393f * k, 420f * k, 150f * k)
        val chev = b.indices.any { i -> (i + 1 until b.size).any { j ->
            !(b[i].x + b[i].w <= b[j].x || b[j].x + b[j].w <= b[i].x || b[i].y + b[i].h <= b[j].y || b[j].y + b[j].h <= b[i].y) } }
        verifB(!chev && b.all { it.x >= 0 && it.x + it.w <= 393 * k && it.y >= 0 }, "téléphone étroit : le menu tient dans l'écran (x = $x dp)")
    }
    val ile = BureauVie.Ile()
    ile.basculer(); repeat(20) { ile.tick(0.05) }
    verifB(ile.etat == "ouverte" && ile.ouverture == 1f, "un appui : l'île s'agrandit")
    ile.fermer(); repeat(20) { ile.tick(0.05) }
    verifB(ile.annoncer("Un monstre est apparu !") && ile.etat == "evenement", "un événement : elle s'ouvre toute seule")
    repeat(140) { ile.tick(0.05) }
    verifB(ile.etat == "repos", "puis se replie")
    ile.auto = false
    verifB(!ile.annoncer("x"), "ouverture automatique coupée")
    val a = BureauVie.Resume(3, 1, 2, 40.0, false)
    val ev = BureauVie.evenements(a, BureauVie.Resume(4, 1, 3, 20.0, true))
    verifB(ev == listOf("bur.ile.monstre", "bur.ile.etape", "bur.ile.envie_faim"), "événements du jeu : $ev")

    println("\n$okB réussis, $koB échoués")
    if (koB > 0) System.exit(1)
}
