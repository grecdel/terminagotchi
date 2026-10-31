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
    val attendu = mapOf("braisillon" to 369131043L, "glandouille" to 4025107268L, "lunacorne" to 1621314562L)
    for ((e, h) in attendu) {
        val (idx, pal) = Poses.indexees(e)!!
        var hh = 0x811C9DC5L
        for (v in idx.values) { for (i in 4 until v.size) hh = ((hh xor v[i].toLong()) * 0x01000193L) and 0xFFFFFFFFL }
        verifB(hh == h && pal.size == 48 && idx.size == 20, "$e : 20 poses (dont « cligne », la mâchoire, la bouche trouée, le coucou content), mêmes octets qu'en Python (empreinte $hh)")
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

    println("La vie dans chaque pose et les transitions")
    c = BureauVie.Creature(1000f, h = java.util.Random(8))
    c.changer("assis", 10.0); repeat(10) { c.tick(0.1, BureauVie.Signaux(1.0)) }
    val ys = (0 until 40).map { c.tick(0.1, BureauVie.Signaux(1.0)); BureauVie.animer(c).sy }
    verifB(ys.maxOrNull()!! - ys.minOrNull()!! > 0.02f, "assise : elle respire (sy de ${ys.minOrNull()} à ${ys.maxOrNull()})")
    c.clignerDans(-0.05)
    verifB(BureauVie.animer(c).etat == "cligne", "assise : elle cligne des yeux")
    c.changer("baille"); c.tick(0.05)
    var an = BureauVie.animer(c)
    verifB((an.ancien?.etat == "assis" || an.ancien?.etat == "cligne") && an.sy < 1f, "changement de pose : l'ancienne se tasse avant de laisser la place")
    repeat(3) { c.tick(0.05) }
    an = BureauVie.animer(c)
    verifB(an.ancien != null && an.opacite in 0.01f..0.99f, "puis un court fondu croisé")
    repeat(5) { c.tick(0.05) }
    verifB(BureauVie.animer(c).ancien == null, "transition finie en ${BureauVie.TRANSITION} s")
    c.dormir(); repeat(10) { c.tick(0.1) }
    an = BureauVie.animer(c)
    verifB(an.effets.count { it.genre == "z" } == 3 && !an.miroir, "dort : des « z » qui montent (et pas à l'envers)")
    c.changer("mange", 3.0); c.tick(0.3)
    verifB(BureauVie.animer(c).effets.any { it.genre == "miette" }, "mange : la miette arrive")
    repeat(28) { c.tick(0.1) }
    verifB(BureauVie.animer(c).effets.none { it.genre == "miette" }, "trois bouchées : la miette a disparu")
    c.changer("salut", 2.0); c.tick(0.6)
    val rots = (0 until 12).map { c.tick(0.05); BureauVie.animer(c).rot }
    verifB(rots.any { it > 2 } && rots.any { it < -2 }, "salut : elle se balance")
    val durees = (0 until 20).map { c.changer("etire"); c.duree }.toSet()
    verifB(durees.size > 10, "les durées changent un peu à chaque fois")

    println("La mâchoire : manger, parler")
    verifB(listOf(0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0).map { BureauVie.poseBouche(it) } ==
        listOf("assis", "assis", "bouche1", "bouche2", "bouche2", "bouche3", "bouche3"), "poseBouche : 0 fermée → 1 grande ouverte")
    // mêmes valeurs qu'en Python (bureau_vie.duree_parole, parole_niveau à 0 ; 0,3 ; 0,6 ; 0,9 s)
    val ref = listOf(
        Triple("Coucou, on joue ?", 1.24, listOf(0.0, 0.287, 0.9239, 0.0)),
        Triple("J'ai un peu faim… Tape `date` !", 2.17, listOf(0.0, 0.6929, 0.0, 0.0)),
        Triple("我很喜欢你哦。", 0.48, listOf(0.0, 0.287, 0.0, 0.0)),
        Triple("Привет!", 0.62, listOf(0.0, 0.287, 0.0, 0.0)))
    for ((ph, d, niv) in ref) {
        val calc = listOf(0, 3, 6, 9).map { Math.round(BureauVie.paroleNiveau(ph, it / 10.0) * 10000) / 10000.0 }
        verifB(Math.abs(BureauVie.dureeParole(ph) - d) < 1e-6 && calc == niv, "« $ph » : mêmes syllabes qu'en Python ($calc)")
    }
    val a13 = Poses.dessine("glandouille")!!
    verifB(listOf("bouche1", "bouche2", "bouche3").all { a13.images(it)[0].argb.contentEquals(a13.images("assis")[0].argb).not() }
        && a13.bouche != null, "glandouille : 3 ouvertures de bouche, et sa place")
    val rob = Poses.dessine("boulonnet")!!
    verifB(rob.bouche == null && rob.images("bouche3")[0].argb.contentEquals(rob.images("assis")[0].argb), "boulonnet (robot) : pas de bouche")
    c = BureauVie.Creature(1000f, h = java.util.Random(9))
    c.bouche = a13.bouche!!; c.levre = a13.levre; c.bordCorps = a13.bord
    verifB(a13.levre != null && a13.levre!! in 0.03f..0.3f && a13.bord in 0.2f..0.6f, "glandouille : largeur de bouche ${a13.levre}, bord ${a13.bord}")
    // bâiller : la pose dessinée, puis la mâchoire se referme (3 → 2 → 1 → fermée)
    c.changer("baille", 3.0)
    val suite = mutableListOf<String>()
    repeat(62) { c.tick(0.05); val e = BureauVie.animer(c).etat; if (suite.lastOrNull() != e) suite.add(e) }
    verifB(suite.filter { it.startsWith("bouche") || it == "assis" }.takeLast(4) == listOf("bouche3", "bouche2", "bouche1", "assis")
        && suite.last() in setOf("assis", "cligne"), "bâiller : la bouche se referme peu à peu, puis bouche fermée $suite")
    c.changer("mange", 3.4)
    val vus = mutableSetOf<String>()
    var ordre = true; var tMax = 0f
    repeat(68) {
        c.tick(0.05); val an2 = BureauVie.animer(c); vus.add(an2.etat)
        if (an2.fond != null && !an2.etat.startsWith("trou")) ordre = false
        an2.effets.filter { it.genre == "miette" }.forEach { tMax = maxOf(tMax, it.taille) }
    }
    verifB(vus.containsAll(listOf("assis", "trou3")) && "mange" !in vus && ordre,
        "manger : la miette passe derrière la lèvre (bouche ouverte dessous, pose trouée dessus) $vus")
    verifB(tMax > 0 && tMax < a13.levre!!, "la miette est plus petite que la bouche")
    verifB(listOf("trou1", "trou2", "trou3").all { t -> a13.images(t)[0].argb.count { (it ushr 24) == 0 } >
        a13.images("assis")[0].argb.count { (it ushr 24) == 0 } }, "les poses trouées : l'intérieur de la bouche est transparent")
    val r2 = BureauVie.Creature(1000f, h = java.util.Random(9)); r2.bordCorps = rob.bord
    r2.changer("mange", 3.4)
    var etinc = 0
    repeat(68) { r2.tick(0.05); if (BureauVie.animer(r2).effets.any { it.genre == "etincelle" }) etinc++ }
    verifB(etinc >= 3, "sans bouche (boulonnet) : la miette file derrière, une étincelle")
    // coucou : 2 ou 3 petits sauts, tassement, ombre, bouche contente, balancier
    val s3 = BureauVie.Creature(1000f, h = java.util.Random(4))
    s3.changer("salut", 2.8)
    val dys = mutableListOf<Float>(); val et3 = mutableSetOf<String>(); var syMin = 9f; var omMin = 9f; val rot3 = mutableListOf<Float>()
    repeat(56) { s3.tick(0.05); val a4 = BureauVie.animer(s3); dys.add(a4.dy); et3.add(a4.etat); syMin = minOf(syMin, a4.sy); omMin = minOf(omMin, a4.ombre); rot3.add(a4.rot) }
    val sauts = (1 until dys.size).count { dys[it] < -6 && dys[it - 1] >= -6 }
    verifB(sauts in 2..3 && dys.minOrNull()!! < -8, "coucou : $sauts petits sauts")
    verifB(syMin < 0.95f && omMin < 0.7f && "salut_ouvert" in et3 && rot3.any { it > 2 } && rot3.any { it < -2 },
        "tassement à l'atterrissage, ombre, bouche contente, balancier")
    verifB(!a13.images("salut_ouvert")[0].argb.contentEquals(a13.images("salut")[0].argb), "glandouille : le coucou bouche ouverte")
    c.changer("marche"); c.parler("Coucou, on joue ?")
    verifB(c.etat == "assis", "elle s'arrête de marcher pour parler")
    val bs = mutableSetOf<String>()
    repeat(24) { c.tick(0.05); bs.add(BureauVie.animer(c).etat) }
    verifB("bouche3" in bs || "bouche2" in bs, "elle parle : la mâchoire bouge ($bs)")
    verifB(BureauVie.miniVie(c, 0.0).first.let { it == "assis" || it.startsWith("bouche") }, "dans l'île, la mini-créature parle aussi")

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
