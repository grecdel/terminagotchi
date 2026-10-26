/*
 * Test JVM (hors téléphone) des auras de rareté (Aura.kt), portage de pc/outils/test_aura.py : l'échelle des
 * couleurs, la lueur qui suit la silhouette (dehors seulement), la respiration, les balises des listes (troupe,
 * collection) et le réglage du bouton ✨ rangé partie par partie.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Aura.kt -d aura.jar
 *   java -cp <imitations>:<appli.jar>:aura.jar:kotlin-stdlib.jar AuraKt app/src/main/assets
 */
import fr.terminagotchi.Aura
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Equipe
import fr.terminagotchi.Explo
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Parties
import fr.terminagotchi.t
import java.io.File

class ActifsA(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilA(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsA(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okA = 0
var koA = 0

fun verif(c: Boolean, m: String) {
    if (c) okA++ else koA++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_aura_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilA(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    var jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"

    println("L'échelle des auras")
    verif(Aura.ORDRE == listOf("commune", "peu commune", "rare", "épique", "légendaire", "mythique", "shiny"),
        "7 paliers : les 6 raretés, puis shiny (même ordre que le PC)")
    verif(Aura.ORDRE.dropLast(1).all { Aura.PALIERS.getValue(it).couleur == Bestiaire.COULEUR_RARETE[it] },
        "les couleurs sont celles des raretés (Bestiaire.COULEUR_RARETE)")
    val rayons = Aura.ORDRE.map { Aura.PALIERS.getValue(it).rayon }
    val forces = Aura.ORDRE.dropLast(1).map { Aura.PALIERS.getValue(it).force }
    verif(rayons == rayons.sorted() && forces == forces.sorted() && rayons[5] == 3, "plus c'est rare, plus l'aura est large et forte")
    verif(Aura.palierDe("rare", true) == "shiny" && Aura.palierDe("épique", false) == "épique" && Aura.palierDe("??", false) == "commune",
        "shiny passe avant la rareté ; rareté inconnue = commune")

    println("La lueur suit la silhouette")
    val w = 7; val h = 7
    val plein = BooleanArray(w * h) { val x = it % w; val y = it / w; x in 1..5 && y in 1..5 && !(x == 3 && y == 3) }
    val c = Aura.calque(w, h, plein, "légendaire")
    val r = c.r
    verif(c.largeur == w + 6 && c.hauteur == h + 6 && r == 3, "toile agrandie du rayon de chaque côté")
    verif((0 until w * h).filter { plein[it] }.all { c.px[(it / w + r) * c.largeur + it % w + r] == 0 }, "jamais d'aura SUR la bestiole")
    verif(c.px[(3 + r) * c.largeur + 3 + r] == 0, "un trou fermé à l'intérieur reste vide (dehors seulement)")
    val bord = c.px[(3 + r) * c.largeur + r]
    verif(bord != 0 && (bord ushr 24) > 150, "le bord extérieur brille fort")
    verif(c.px[0] == 0, "la lueur s'éteint en s'éloignant")
    fun nb(n: String) = Aura.calque(w, h, plein, n).px.count { it != 0 }
    verif(nb("peu commune") < nb("rare") && nb("rare") < nb("légendaire"), "les auras rares couvrent plus de pixels")
    val alphas = (0 until Aura.PHASES).map { ph -> Aura.calque(w, h, plein, "rare", ph).px.sumOf { it ushr 24 } }.toSet()
    verif(alphas.size > 4, "l'aura respire : elle change d'une image à l'autre")
    verif(Aura.calque(w, h, plein, "shiny", 3).px.filter { it != 0 }.map { it and 0xFFFFFF }.toSet().size > 6,
        "shiny : une lueur arc-en-ciel")

    println("Masque et dessin")
    val e = Bestiaire.espece("Braisillon")!!
    val bmp = Bestiaire.bitmap(e, false, 4, "adulte")
    val (mw, mh, mp) = Aura.masque(bmp, 4)
    val img = Bestiaire.image(e, "adulte")!!
    verif(mw == maxOf(img.w, img.h) && mh == mw && mp.count { it } == img.octets.count { it.toInt() != 0 },
        "le masque relu sur l'image agrandie = les pixels de la bestiole")
    val ent = Aura.entourer(bmp, 4, "rare", garder = true)
    verif(ent.width == bmp.width + 2 * 2 * 4 && ent.height == bmp.height + 16, "l'image entourée garde la bestiole et ajoute 2 pixels de lueur")
    verif(Aura.entourer(bmp, 4, "rare", garder = true) === ent, "les petites images des listes sont gardées en cache")

    println("Listes : troupe et collection")
    val caps = Explo.captures(jeu)
    for ((nom, rar, sh) in listOf(Triple("Braisillon", "légendaire", false), Triple("Pyrodrac", "commune", false), Triple("Ombrachne", "rare", true))) {
        val ind = Bestiaire.individu(Bestiaire.espece(nom)!!, sh)
        ind.put("rarete", rar).put("stade", "adulte")
        caps.put(ind)
    }
    val b0 = Bestiaire.balise(caps.getJSONObject(0))
    verif(b0.endsWith("~${Aura.code("légendaire")}¤"), "la balise d'une bestiole de la troupe porte son aura ($b0)")
    verif(Bestiaire.balise(caps.getJSONObject(2)).endsWith("~${Aura.code("shiny")}¤"), "shiny : aura arc-en-ciel dans la balise")
    verif(!Bestiaire.balise(caps.getJSONObject(0), aura = false).contains("~"), "aura = false : la balise sans aura")
    val troupe = Equipe.texte(jeu)
    verif(troupe.contains("~4¤") && troupe.contains(t("aura.legende")), "tg troupe : les auras et leur légende")
    verif(Explo.texteCollection(jeu).contains(t("aura.legende")), "collection : la légende des auras")
    val motif = Regex("¤([a-z0-9_]+)(?::([^:¤*+~]+))?(?::([a-z]+))?(?:\\*([0-9.]*))?(\\+)?(?:~([0-9]))?¤")
    val m = motif.find(Bestiaire.balise(caps.getJSONObject(2)))
    verif(m != null && Aura.deCode(m.groupValues[6].toIntOrNull()) == "shiny" && m.groups[4] != null,
        "le terminal de l'appli relit la balise (teinte shiny + aura)")

    println("Le bouton ✨ et les parties")
    verif(Aura.palierCompagnon(jeu) == (if (jeu.shiny) "shiny" else "commune"), "le compagnon : shiny ou commune")
    verif(Aura.active(jeu), "l'aura est affichée par défaut")
    verif(!Aura.basculer(jeu) && !Aura.active(jeu), "le bouton la cache")
    jeu.sauver()
    jeu.recharger()
    verif(!Aura.active(jeu), "le réglage est gardé dans la sauvegarde")
    val p1 = Parties.active(app)
    verif(Parties.nouvelle(app) != null, "nouvelle partie")
    jeu.recharger()
    verif(Aura.active(jeu), "nouvelle partie : l'aura est affichée (réglage propre à chaque partie)")
    verif(Parties.charger(app, p1), "retour à la première partie")
    jeu.recharger()
    verif(!Aura.active(jeu) && jeu.nom == "Pixel", "retour à la partie 1 : son aura reste cachée")

    println("\n$okA réussis, $koA échoués")
    if (koA > 0) System.exit(1)
}
