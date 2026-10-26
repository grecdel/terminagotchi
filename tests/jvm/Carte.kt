/*
 * Test JVM (hors téléphone) de la carte qui pousse (Maison.kt, Carte.kt), portage de pc/outils/test_carte.py :
 * le vrai terrain dessiné à côté de `tree`, la brume, « nouveau ! », les passages secrets après `ls -a`, `tree` qui
 * dévoile un coin, les régions de donnees/biomes.json, la légende des commandes rencontrées, la carte a poussé.
 * Le dessin passe par un Peintre Java (java.awt) : le test vérifie qu'il se fait dans les 14 langues et, avec un
 * dossier en 2e argument, enregistre les aperçus des 3 étapes (tel_1_eclos.png, tel_2_mkdir.png, tel_3_fin.png).
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Carte.kt -d carte.jar
 *   java -cp <imitations>:<appli.jar>:carte.jar:kotlin-stdlib.jar CarteKt app/src/main/assets [dossier des aperçus]
 */
import fr.terminagotchi.Carte
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Peintre
import fr.terminagotchi.Sprites
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import java.io.File

class ActifsC(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilC(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsC(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okC = 0
var koC = 0

fun verif(c: Boolean, m: String) {
    if (c) okC++ else koC++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuC: Jeu
val TC: File get() = jeuC.terrain

/** Le peintre des aperçus : java.awt, à l'échelle e (3 = un téléphone xxhdpi), polices DejaVu (comme le monospace d'Android). */
class PeintreAwt(val g: java.awt.Graphics2D, val jeu: Jeu?) : Peintre {
    private val polices = HashMap<String, Font>()
    private fun police(taille: Float, mono: Boolean, gras: Boolean): Font = polices.getOrPut("$taille$mono$gras") {
        Font(if (mono) "DejaVu Sans Mono" else "DejaVu Sans", if (gras) Font.BOLD else Font.PLAIN, 1).deriveFont(taille)
    }
    override fun rect(x: Float, y: Float, w: Float, h: Float, couleur: Int) {
        g.color = java.awt.Color(couleur, true)
        g.fill(java.awt.geom.Rectangle2D.Float(x, y, w, h))
    }
    override fun pixels(p: Carte.Pix, x: Float, y: Float, echelle: Float) {
        for (j in 0 until p.h) for (i in 0 until p.w) {
            val c = p.px[j * p.w + i]
            if ((c ushr 24) != 0) rect(x + i * echelle, y + j * echelle, echelle, echelle, c)
        }
    }
    override fun texte(s: String, x: Float, y: Float, taille: Float, couleur: Int, mono: Boolean, gras: Boolean) {
        g.font = police(taille, mono, gras)
        g.color = java.awt.Color(couleur, true)
        g.drawString(s, x, y)
    }
    override fun mesure(s: String, taille: Float, mono: Boolean, gras: Boolean): Float =
        g.getFontMetrics(police(taille, mono, gras)).stringWidth(s).toFloat()
    override fun creature(x: Float, y: Float, h: Float): Boolean {
        val j = jeu ?: return false
        val b = try { Sprites.bitmap(j, 1) } catch (e: Exception) { return false }
        val e = h / b.height
        for (yy in 0 until b.height) for (xx in 0 until b.width) {
            val c = b.getPixel(xx, yy)
            if ((c ushr 24) != 0) rect(x - b.width * e / 2 + xx * e, y - h + yy * e, e, e, c)
        }
        return true
    }
}

/** Dessine la carte comme CarteVue (largeur d'un téléphone : 392 dp) ; enregistre l'aperçu si un dossier est donné. */
fun dessiner(nom: String?, sortie: File?, largeur: Float = 392f): Carte.Taille {
    val ns = Maison.noeuds(jeuC, marquer = true)
    val nouveaux = ns.filter { it.nouveau }.map { it.cle }.toSet()
    val essai = BufferedImage(10, 10, BufferedImage.TYPE_INT_ARGB)
    val taille = Carte.dessiner(PeintreAwt(essai.createGraphics(), jeuC), Carte.titre(jeuC), ns, Maison.pied(jeuC), nouveaux, 0, largeur)
    if (sortie != null && nom != null) {
        val e = 3f
        val img = BufferedImage((taille.l * e).toInt(), (taille.h * e).toInt(), BufferedImage.TYPE_INT_ARGB)
        val g = img.createGraphics()
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON)
        g.scale(e.toDouble(), e.toDouble())
        Carte.dessiner(PeintreAwt(g, jeuC), Carte.titre(jeuC), ns, Maison.pied(jeuC), nouveaux, 0, largeur)
        javax.imageio.ImageIO.write(img, "png", File(sortie, "tel_$nom.png"))
        println("     aperçu : ${File(sortie, "tel_$nom.png")}")
    }
    return taille
}

/** L'enfant tape une ligne (déjà faite sur le terrain) depuis le dossier ou (relatif au terrain). */
fun tapeC(ligne: String, ou: String? = null) {
    jeuC.vus.add(ligne.trim().split(Regex("\\s+"))[0].lowercase())
    Maison.suivre(jeuC, ligne, false, if (ou != null) (if (ou.isEmpty()) TC else File(TC, ou)) else null)
}

fun ligneDe(ns: List<Maison.Noeud>, r: String) = ns.firstOrNull { it.rel == r }

fun main(args: Array<String>) {
    val assets = File(args[0])
    val sortie = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_carte_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilC(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuC = Jeu(app)
    jeuC.changerLangue("fr")
    jeuC.nom = "Pixel"
    val h = Histoire.h(jeuC)

    println("1. Les régions viennent de donnees/biomes.json")
    val bio = JSONObject(File(assets, "../../../../donnees/biomes.json").readText()).getJSONArray("types")
    val ids = (0 until bio.length()).map { bio.getJSONObject(it).getString("id") }
    verif(ids == Maison.BIOMES.keys.toList(), "les 9 types de biome, dans le même ordre")
    verif((0 until bio.length()).all { i ->
        val b = bio.getJSONObject(i); val c = b.getJSONObject("couleurs"); val m = Maison.BIOMES.getValue(b.getString("id"))
        fun hex(s: String) = (0xFF000000.toInt() or s.removePrefix("#").toInt(16))
        m.principale == hex(c.getString("principale")) && m.sombre == hex(c.getString("sombre")) && m.claire == hex(c.getString("claire"))
    }, "mêmes couleurs (principale, sombre, claire)")
    verif(Carte.ICONES.values.all { l -> l.all { r -> r.length == l[0].length } } && Maison.BIOMES.keys.all { it in Carte.ICONES },
        "chaque icône est un rectangle ; une icône par région")

    println("2. Juste éclos")
    File(TC, "vestibule").mkdirs()
    File(TC, "vestibule/oeuf_tout_chaud.txt").writeText("chaud\n")
    File(TC, "nid").mkdirs()
    File(TC, ".cachette").mkdirs()
    h.getJSONArray("faits").put("t0")
    h.put("chap", "reveil")
    tapeC("pwd", "")
    var ns = Maison.noeuds(jeuC)
    verif(ns[0].genre == "camp" && ns[0].ici, "le camp de base : tu es ici")
    verif(ligneDe(ns, "vestibule")!!.brume && ligneDe(ns, "vestibule")!!.etiquette == "???", "vestibule pas encore visité : brume")
    verif(ligneDe(ns, "nid") == null, "le nid pas encore posé : invisible")
    verif(ligneDe(ns, ".cachette") == null, "pas de passage secret avant `ls -a`")
    val t1 = dessiner("1_eclos", sortie)
    verif(t1.l >= 320f && t1.h > 100f, "le dessin se fait (${t1.l.toInt()}×${t1.h.toInt()} dp)")
    val c1 = Maison.carte(jeuC).joinToString("\n")
    verif("░░░░ ???" in c1 && "`pwd`" in c1 && "`mkdir`" !in c1, "texte : brume, légende avec pwd seulement")
    verif(Maison.noeuds(jeuC).none { it.nouveau }, "déjà montré : plus de « nouveau ! »")

    println("3. Après les leçons mkdir")
    h.put("ailes", JSONArray().put("reveil").put("nid"))
    h.put("chap", JSONObject.NULL)
    tapeC("cd vestibule", "vestibule")
    tapeC("cd ..", "")
    ns = Maison.noeuds(jeuC)
    verif(!ligneDe(ns, "vestibule")!!.brume && ligneDe(ns, "vestibule")!!.nouveau, "vestibule visité : dévoilé, nouveau")
    verif(ligneDe(ns, "vestibule/oeuf_tout_chaud.txt")?.genre == "note", "oeuf_tout_chaud.txt : une note")
    File(TC, "cabane").mkdirs()
    Maison.dernierePousse = null
    tapeC("mkdir cabane", "")
    verif(Maison.dernierePousse?.contains("+ cabane/") == true && jeuC.journal.any { "la carte a poussé" in it },
        "« 🗺 la carte a poussé : + cabane/ » (${Maison.dernierePousse})")
    tapeC("cd cabane", "cabane")
    File(TC, "cabane/lit.sh").writeText("echo zzz\n")
    File(TC, "cabane/photo.png").writeBytes(byteArrayOf(1))
    File(TC, "cabane/tresor.zip").writeBytes(byteArrayOf(1))
    tapeC("touch lit.sh photo.png tresor.zip", "cabane")
    ns = Maison.noeuds(jeuC)
    verif(listOf("lit.sh", "photo.png", "tresor.zip").map { ligneDe(ns, "cabane/$it")?.genre } == listOf("recette", "image", "coffre"),
        "objets : recette, carte postale, coffre")
    verif(ligneDe(ns, "cabane")!!.ici && !ns[0].ici, "◉ suit le dossier courant")
    verif(ligneDe(ns, "cabane")!!.branches == "├── " && ligneDe(ns, "cabane/tresor.zip")!!.branches == "│   └── ", "débuts de lignes de tree")
    File(TC, "cabane/photo.png").delete()
    tapeC("rm photo.png", "cabane")
    verif(Maison.dernierePousse?.contains("− photo.png") == true, "rm : la carte a rétréci")
    dessiner("2_mkdir", sortie)

    println("4. Fin de partie : régions, parcelles, passages secrets, tree")
    for (p in Maison.AILES) File(TC, p).mkdirs()
    for ((b, n) in listOf("feu" to 2, "eau" to 1, "plante" to 1)) for (i in 1..n) File(TC, "biome/$b/parcelle_$i").mkdirs()
    File(TC, "biome/feu/parcelle_1/braises.pierre").writeText("")
    File(TC, "grenier/.placard").mkdirs()
    File(TC, "grenier/lettre.txt").writeText("")
    tapeC("cd ~/terrain_terminagotchi/biome", "biome")
    ns = Maison.noeuds(jeuC)
    verif(ligneDe(ns, "biome")?.genre == "porte" && ligneDe(ns, "biome/feu")!!.brume, "la porte du Terminaworld ; régions dans la brume")
    tapeC("tree", "biome")
    ns = Maison.noeuds(jeuC)
    verif(!ligneDe(ns, "biome/feu")!!.brume && ligneDe(ns, "biome/feu/parcelle_2")?.genre == "parcelle", "`tree` dévoile régions et parcelles")
    verif(ligneDe(ns, "biome/feu")!!.etiquette == "région Feu" && ligneDe(ns, "biome/feu/parcelle_1")!!.biome == "feu",
        "région Feu ; ses parcelles en prennent la couleur")
    tapeC("ls -la", "")
    ns = Maison.noeuds(jeuC)
    verif(ligneDe(ns, ".cachette")?.genre == "secret" && ligneDe(ns, "grenier/.placard") == null,
        "après `ls -a` : .cachette (passage secret) ; grenier pas visité : le sien reste caché")
    tapeC("cd grenier", "grenier")
    h.put("chap", "grenier")
    ns = Maison.noeuds(jeuC)
    verif(ligneDe(ns, "grenier/.placard")?.genre == "secret" && "▶" in ligneDe(ns, "grenier")!!.marques, "grenier visité : .placard ; ▶ en cours")
    for (i in 0 until 20) File(TC, "cabane/caillou_$i.txt").writeText("")
    ns = Maison.noeuds(jeuC)
    verif(ns.count { it.genre == "suite" } == 1, "plus de ${Maison.MAX_PAR_DOSSIER} entrées : « + n autres »")
    for (i in 0 until 20) File(TC, "cabane/caillou_$i.txt").delete()
    tapeC("cd ~/terrain_terminagotchi/biome/feu/parcelle_1", "biome/feu/parcelle_1")
    Maison.noeuds(jeuC, marquer = true)
    File(TC, "biome/feu/parcelle_3").mkdirs()
    tapeC("mkdir ../parcelle_3", "biome/feu/parcelle_1")
    dessiner("3_fin", sortie)
    val c3 = Maison.carte(jeuC).joinToString("\n")
    verif("`ls -a`" in c3 && "`tree`" in c3 && "parcelle_3/" in c3, "légende : ls -a et tree ; parcelle_3 sur la carte")

    println("5. Les 14 langues")
    val casses = mutableListOf<String>()
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val tout = Maison.carte(jeuC).joinToString("\n")
        if (Regex("\\{[a-z_]+\\}|carte\\.[a-z]").containsMatchIn(tout)) casses.add("$code : texte à remplir")
        try { dessiner(null, null) } catch (e: Exception) { casses.add("$code : $e") }
    }
    Langue.definir("fr")
    verif(casses.isEmpty(), "14 langues : texte et dessin sans trou $casses")
    verif(t("carte.monde.titre", "nom" to "X").contains("Terminaworld"), "le monde s'appelle le Terminaworld")
    verif(Maison.m(jeuC).getJSONArray("montres").length() <= 800 && Maison.m(jeuC).getJSONArray("empreinte").length() <= 400,
        "la sauvegarde reste petite")

    println("\n$okC réussis, $koC échoués")
    System.exit(if (koC > 0) 1 else 0)
}
