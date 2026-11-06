/*
 * Test JVM (hors téléphone) du thème « créature » (Creature.kt, CreatureDessin.kt), portage de pc/outils/test_creature.py :
 *   1. les vecteurs partagés avec Python (donnees/creature/vecteurs.json) : humeurs, goûts, fêtes, devinettes,
 *      phases de l'évolution, plat et aliment de chaque espèce ;
 *   2. une vraie partie (Jeu, Tour.apresCommande) : plat préféré (double faim, pas d'XP en plus), humeurs du moment,
 *      album et moment d'évolution, éclosiversaire, envie mystère et ses indices ;
 *   3. le dessin (album, évolution, carte de l'espace avec humeur, fête et promenade) sans planter ; avec un 2e
 *      argument (un dossier), les captures du téléphone y sont écrites.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Creature.kt -d creature.jar
 *   java -cp <imitations>:<appli.jar>:creature.jar:kotlin-stdlib.jar CreatureKt app/src/main/assets [dossier]
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Creature
import fr.terminagotchi.CreatureDessin
import fr.terminagotchi.Envies
import fr.terminagotchi.EspaceDessin
import fr.terminagotchi.EspaceEtat
import fr.terminagotchi.Guide
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Poses
import fr.terminagotchi.Satiete
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.awt.BasicStroke
import java.awt.Color
import java.awt.Font
import java.awt.RadialGradientPaint
import java.awt.RenderingHints
import java.awt.geom.AffineTransform
import java.awt.geom.Ellipse2D
import java.awt.geom.Line2D
import java.awt.geom.Path2D
import java.awt.geom.RoundRectangle2D
import java.awt.image.BufferedImage
import java.io.File
import java.util.TimeZone
import javax.imageio.ImageIO

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

fun verifC(c: Boolean, m: String) {
    if (c) okC++ else koC++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Le pinceau Java2D (le même contrat que le Canvas du téléphone). */
class ToileJavaC(val g: java.awt.Graphics2D) : Toile {
    private val images = HashMap<String, BufferedImage>()
    private fun c(x: Int) = Color(x shr 16 and 255, x shr 8 and 255, x and 255, x ushr 24 and 255)
    private fun police(taille: Float, gras: Boolean, mono: Boolean): Font =
        Font(if (mono) "DejaVu Sans Mono" else "Inter", if (gras) Font.BOLD else Font.PLAIN, 1).deriveFont(taille)
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { g.color = c(c); g.fill(java.awt.geom.Rectangle2D.Float(x, y, w, h)) }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) {
        val ra = minOf(r, w / 2, h / 2) * 2
        val f = RoundRectangle2D.Float(x, y, w, h, ra, ra)
        if (fond != null) { g.color = c(fond); g.fill(f) }
        if (bord != null && ep > 0) { g.color = c(bord); g.stroke = BasicStroke(ep); g.draw(f) }
    }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { g.color = c(c); g.fill(Ellipse2D.Float(cx - rx, cy - ry, 2 * rx, 2 * ry)) }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { g.color = c(c); g.stroke = BasicStroke(ep); g.draw(Ellipse2D.Float(cx - r, cy - r, 2 * r, 2 * r)) }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) {
        g.color = c(c); g.stroke = BasicStroke(ep); g.draw(Line2D.Float(x1, y1, x2, y2))
    }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) {
        val p = Path2D.Float(); p.moveTo(xs[0], ys[0]); for (i in 1 until xs.size) p.lineTo(xs[i], ys[i]); p.closePath()
        g.color = c(c); g.fill(p)
    }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) {
        g.font = police(taille, gras, mono)
        val fm = g.fontMetrics
        val w = fm.stringWidth(s)
        val dx = when (ancre) { 'c' -> -w / 2f; 'd' -> -w.toFloat(); else -> 0f }
        g.color = c(c)
        g.drawString(s, x + dx, y + (fm.ascent - fm.descent) / 2f)
    }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float { g.font = police(taille, gras, mono); return g.fontMetrics.stringWidth(s).toFloat() }
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) {
        if (r <= 0) return
        val old = g.paint
        g.paint = RadialGradientPaint(cx, cy, r, floatArrayOf(0f, 1f), arrayOf(c(c), c(c and 0x00FFFFFF)))
        g.fill(Ellipse2D.Float(cx - r, cy - r, 2 * r, 2 * r))
        g.paint = old
    }
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) {
        if (alpha <= 0.01f) return
        val im = images.getOrPut(c.cle) { BufferedImage(c.w, c.h, BufferedImage.TYPE_INT_ARGB).also { it.setRGB(0, 0, c.w, c.h, c.argb, 0, c.w) } }
        val old = g.transform
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
            if (lisse) RenderingHints.VALUE_INTERPOLATION_BICUBIC else RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR)
        val t = AffineTransform(old)
        t.translate(ax.toDouble(), ay.toDouble())
        if (rot != 0f) t.rotate(Math.toRadians(-rot.toDouble()))
        t.scale((if (miroir) -sx else sx).toDouble() * e, sy.toDouble() * e)
        t.translate(-c.ax.toDouble(), -c.ay.toDouble())
        g.transform = t
        g.drawImage(im, 0, 0, null)
        g.transform = old
    }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { rect(x, y, w, h, 0xFF203020.toInt()) }
}

fun liste(a: JSONArray): List<Any?> = (0 until a.length()).map { if (a.isNull(it)) null else a.get(it) }
fun chaines(a: JSONArray) = (0 until a.length()).map { a.getString(it) }
fun entiersC(a: JSONArray) = (0 until a.length()).map { a.getInt(it) }

fun capture(f: File, w: Int, h: Int, dessin: (Toile) -> Unit) {
    val im = BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB)
    val g = im.createGraphics()
    g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
    g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON)
    val tl = ToileJavaC(g)
    tl.rect(0f, 0f, w.toFloat(), h.toFloat(), EspaceDessin.FOND)
    dessin(tl)
    g.dispose()
    ImageIO.write(im, "png", f)
}

fun main(args: Array<String>) {
    TimeZone.setDefault(TimeZone.getTimeZone("UTC"))         // les vecteurs sont en heure UTC (comme le test Python)
    val assets = File(args[0])
    val racine = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val sortie = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_creature_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilC(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    Poses.lire(File(assets, "poses.bin").readBytes())
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    Envies.heure = { 14 }                                    // le jour (le soir : rêveur s'il ne se passe rien d'autre)

    println("1. Les vecteurs partagés avec Python (donnees/creature/vecteurs.json)")
    val v = JSONObject(File(racine, "donnees/creature/vecteurs.json").readText())
    fun tous(k: String, f: (JSONArray) -> Boolean): String? {
        val a = v.getJSONArray(k)
        for (i in 0 until a.length()) if (!f(a.getJSONArray(i))) return a.getJSONArray(i).toString()
        return null
    }
    fun opt(a: JSONArray, i: Int): String? = if (a.isNull(i)) null else a.getString(i)
    var e = tous("humeur") { Creature.choisirHumeur(chaines(it.getJSONArray(0)).toSet()) == opt(it, 1) }
    verifC(e == null, "la priorité des humeurs ${e ?: ""}")
    e = tous("active") { a ->
        val h = opt(a, 0)?.let { JSONObject().put("h", it).put("t", a.getDouble(1)) }
        Creature.humeurActive(h, a.getDouble(2)) == opt(a, 3)
    }
    verifC(e == null, "la durée d'une humeur du moment (3 min ; la fête 10 min) ${e ?: ""}")
    e = tous("variete") { Creature.variete(chaines(it.getJSONArray(0))) == it.getBoolean(1) }
    verifC(e == null, "enjoué : des commandes toutes différentes ${e ?: ""}")
    e = tous("calin") { Creature.pauseCalin(it.getDouble(0), it.getDouble(1)) == it.getBoolean(2) }
    verifC(e == null, "câlin : le retour après une pause ${e ?: ""}")
    e = tous("aliment") { Creature.aliment(it.getString(0)) == opt(it, 1) }
    verifC(e == null, "l'aliment préféré de chaque type ${e ?: ""}")
    e = tous("secret") { Creature.goutSecret(it.getLong(0), opt(it, 1)) == it.getString(2) }
    verifC(e == null, "le goût secret ${e ?: ""}")
    e = tous("mois") { a -> Creature.ajouterMois(a.getInt(0), a.getInt(1), a.getInt(2), a.getInt(3)).toList() == entiersC(a.getJSONArray(4)) }
    verifC(e == null, "ajouter des mois (le 31 devient le dernier jour) ${e ?: ""}")
    e = tous("fete") { a ->
        val r = Creature.feteDue(if (a.isNull(0)) null else a.getDouble(0), a.getDouble(1), entiersC(a.getJSONArray(2)))
        if (a.isNull(3)) r == null else r != null && r.first == a.getJSONArray(3).getInt(0) && r.second == a.getJSONArray(3).getBoolean(1)
    }
    verifC(e == null, "l'éclosiversaire (1, 2, 3, 6 mois, chaque année ; en retard à la visite suivante) ${e ?: ""}")
    e = tous("eligibles") { Creature.eligibles(chaines(it.getJSONArray(0)), it.getBoolean(1)) == chaines(it.getJSONArray(2)) }
    verifC(e == null, "les devinettes possibles (commandes déjà goûtées) ${e ?: ""}")
    e = tous("proposer") { Creature.peutProposer(it.getBoolean(0), it.getInt(1), it.getBoolean(2), it.getInt(3), it.getBoolean(4)) == it.getBoolean(5) }
    verifC(e == null, "quand une envie mystère arrive ${e ?: ""}")
    e = tous("devinette") { Creature.choisirDevinette(chaines(it.getJSONArray(0)), it.getLong(1), opt(it, 2)) == opt(it, 3) }
    verifC(e == null, "le choix de la devinette ${e ?: ""}")
    e = tous("trouve") { Creature.trouve(it.getString(0), it.getString(1)) == it.getBoolean(2) }
    verifC(e == null, "la commande trouvée (mêmes expressions) ${e ?: ""}")
    e = tous("phase") { a -> val p = Creature.phaseEvolution(a.getDouble(0))
        p.first == a.getJSONArray(1).getString(0) && Math.abs(p.second - a.getJSONArray(1).getDouble(1)) < 1e-9 && Creature.peutPasser(a.getDouble(0)) == a.getBoolean(2) }
    verifC(e == null, "les phases du moment d'évolution, passer au bout de 2 s ${e ?: ""}")
    e = tous("migration") { a -> Creature.pagesMigration(chaines(a.getJSONArray(0)), a.getInt(1)).toString() == a.getJSONObject(2).toString() }
    verifC(e == null, "l'album d'une créature déjà grande ${e ?: ""}")
    e = tous("jour") { a -> Creature.numeroJour(a.getDouble(0)) == a.getLong(1) && Creature.dateLocale(a.getDouble(0)).toList() == entiersC(a.getJSONArray(2)) }
    verifC(e == null, "les jours et les dates ${e ?: ""}")
    e = tous("especes") { a ->
        val sp = Bestiaire.espece(a.getString(0))
        sp != null && sp.attireePar == a.getString(1) && Guide.typeDe(sp) == a.getString(2) && Creature.aliment(Guide.typeDe(sp)) == a.getString(3)
    }
    verifC(e == null, "le plat, le type et l'aliment préférés de chaque espèce (${v.getJSONArray("especes").length()}) ${e ?: ""}")

    println("2. Une vraie partie")
    jeu.nom = "Noisette"
    Intro.toutDebloquer(jeu)
    jeu.extra.put("espece_compagnon", "glandouille")
    jeu.xp = 40
    for (c in listOf("pwd", "ls", "cd", "hostname", "uname", "id", "df", "uptime", "sleep")) jeu.vus.add(c)
    val c = Creature.c(jeu)
    c.put("graine", 9L)                                       // son goût secret : « head » (pas une commande de ce test)
    verifC(Creature.stadeCompagnon(jeu) == "bebe" && c.getJSONObject("album").optJSONObject("bebe")?.optBoolean("avant") == true,
        "une créature déjà éclose : « avant l'album »")
    val plat = Creature.plat(jeu)!!
    jeu.faim = 30.0
    jeu.manger(plat, false, false, 0)
    val gainPlat = jeu.faim - 30.0
    jeu.faim = 30.0
    jeu.vus.add("date")
    jeu.manger("date", false, false, 0)                       // une autre commande déjà goûtée (une autre famille)
    val gainAutre = jeu.faim - 30.0
    verifC(gainPlat > gainAutre + 0.5, "le plat préféré ($plat) nourrit deux fois plus (${gainPlat.toInt()} contre ${gainAutre.toInt()})")
    verifC(jeu.journal.any { "♥" in it }, "le journal le dit : ♥ son plat préféré")
    val shell = Shell(jeu.home)
    fun tape(l: String) { Tour.apresCommande(jeu, l, false, false, hasard = false, cwd = shell.dossier, code = 0) }
    jeu.faim = 70.0                                           // en forme (affamée, la santé passe d'abord)
    c.put("derniere_t", Creature.maintenant() - 3600)
    tape("hostname")
    verifC(Creature.humeur(jeu) == "calin", "un retour après une pause : câlin (${Creature.humeur(jeu)})")
    verifC(Envies.humeurCle(jeu) == "humeur.calin", "l'humeur du moment passe devant l'humeur habituelle")
    tape("whoami")
    verifC(Creature.humeur(jeu) == "curieux", "une commande jamais goûtée : curieux (${Creature.humeur(jeu)})")
    for (l in listOf("uname", "id", "df", "uptime")) tape(l)
    verifC(Creature.humeur(jeu) == "enjoue", "des commandes toutes différentes : enjoué (${Creature.humeur(jeu)})")
    tape("sleep 1")
    verifC(Creature.humeur(jeu) == "reveur", "sleep : rêveur (${Creature.humeur(jeu)})")
    c.getJSONObject("humeur").put("t", Creature.maintenant() - 200)
    verifC(Creature.humeur(jeu) == null, "au bout de 3 minutes, l'humeur habituelle revient")

    // 16, 84 : l'album et le moment d'évolution
    Satiete.s(jeu).put("jours", 99)
    jeu.xp = 155
    jeu.ajouterXp(10)
    verifC(Creature.stadeCompagnon(jeu) == "ado" && c.getJSONObject("album").optJSONObject("ado")?.has("t") == true,
        "grandir : une page datée dans l'album")
    verifC(c.optJSONObject("evolution")?.optString("vers") == "ado", "le moment d'évolution est demandé")
    val al = Creature.albumTexte(jeu)
    verifC("Ado" in al && "bientôt" in al && "avant l'album" in al, "album : les stades, « bientôt », « avant l'album »")

    // 17 : l'éclosiversaire
    c.put("eclosion", Creature.maintenant() - 31 * 86400.0)
    tape("pwd")
    verifC(entiersC(c.getJSONArray("fetes")) == listOf(1) && Creature.feteActive(jeu) && Creature.humeur(jeu) == "fete", "1 mois : la fête")
    tape("ls")
    verifC(c.getJSONArray("pages").length() == 1, "pas deux fois la même fête")

    // 18 : l'envie mystère
    Histoire.h(jeu).getJSONArray("ailes").put("reveil")
    c.put("depuis", 30)
    Envies.e(jeu).remove("moment")
    tape("pwd")
    val en = Creature.envie(jeu)
    verifC(en != null, "après le chapitre 1 : une envie mystère (${en?.optString("id")})")
    val r3 = (1..4).map { Creature.indice(jeu) }
    verifC("1 sur 3" in r3[0] && "3 sur 3" in r3[3], "3 indices au plus")
    verifC("plus tard" in Creature.indice(jeu, "plus-tard").lowercase() && Creature.envie(jeu) == null, "« plus tard » la range")
    verifC("pas d'envie" in Creature.indice(jeu), "sans envie : une phrase gentille")
    verifC("plat préféré" in Creature.gouts(jeu), "gouts : ce qu'elle aime")
    verifC(!Creature.son("evolution"), "son(« evolution ») : le moteur de sons, silencieux par défaut (aucune question posée)")

    println("3. Le dessin")
    val d = 1080f / 411f
    val a = CreatureDessin.modeleAlbum(jeu)
    verifC(a.pages.size == 3 && a.pages[1].atteint && !a.pages[2].atteint && a.pages[2].cadre != null, "album : 3 stades, le dernier en silhouette")
    val ev = CreatureDessin.modeleEvo(jeu, "bebe", 0.0)
    verifC(ev.cadres?.isNotEmpty() == true && ev.avant != null, "le moment d'évolution : l'animation du jeu (${ev.cadres?.size} images)")
    val etat = EspaceEtat(jeu, { shell.dossier }, { "~" })
    etat.rafraichir(null, 0.0)
    c.put("humeur", JSONObject().put("h", "surpris").put("t", Creature.maintenant()))
    etat.preparer(1.0)
    verifC(etat.modele.etatTexte == Langue.t("humeur.surpris") && etat.modele.glyphe == "exclam" && etat.modele.promenade != null,
        "la carte de la créature : humeur, glyphe, promenade")
    etat.toucher("opt:sur_place"); etat.preparer(1.1)
    verifC(etat.modele.surPlace && etat.modele.promenade == null, "le réglage « rester sur place »")
    etat.toucher("opt:sur_place"); etat.preparer(1.2)
    var ouvert = false
    etat.ouvrirAlbum = { ouvert = true }
    etat.toucher("album")
    verifC(ouvert, "le bouton « Album » de la carte de la créature")
    val dossierCaptures = sortie ?: File(dossier, "captures").apply { mkdirs() }
    capture(File(dossierCaptures, "tel_album.png"), 1080, 2340) { tl -> CreatureDessin.album(tl, a, 1080f, 2340f, d, 0.0) }
    for ((k, tt) in listOf(1.0, 2.7, 3.9, 5.5).withIndex())
        capture(File(dossierCaptures, "tel_evolution_$k.png"), 1080, 2340) { tl -> CreatureDessin.evolution(tl, ev, 1080f, 2340f, d, tt) }
    c.put("fete", JSONObject().put("m", 1).put("t", Creature.maintenant()))
    etat.preparer(2.0)
    capture(File(dossierCaptures, "tel_carte.png"), 1080, 1400) { tl ->
        EspaceDessin.dessiner(tl, etat.modele, 1080f, EspaceDessin.hauteur(etat.modele, 1080f, 1400f, d), d)
    }
    verifC(File(dossierCaptures, "tel_album.png").exists() && File(dossierCaptures, "tel_carte.png").exists(), "captures dessinées ($dossierCaptures)")
    println("$okC réussis, $koC échoués")
    if (koC > 0) System.exit(1)
}
