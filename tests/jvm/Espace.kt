/*
 * Test JVM (hors téléphone) de l'espace de travail Android, comme pc/outils/test_espace.py :
 *   1. la vue déployée (Deploie.kt) et le cerveau (Cerveau.kt) donnent EXACTEMENT les vecteurs du PC
 *      (donnees/espace/vecteurs.json : blocs, chaînes de tuyaux, commandes sûres, tours du cerveau) ;
 *   2. les textes dans les 14 langues (aucune clé brute, des identifiants de code valides) ;
 *   3. une vraie partie (Noisette, une Glandouille, le Grenier) : l'espace (EspaceEtat) déploie la dernière commande,
 *      calcule ce qui passe dans le tuyau sans écrire la redirection, le cerveau choisit la pose, forcer un état ;
 *   4. les captures du téléphone : le dessin d'EspaceDessin.kt (le même que sur le téléphone) dans une image Java2D.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Espace.kt -d espace.jar
 *   java -cp <imitations>:<appli.jar>:espace.jar:kotlin-stdlib.jar EspaceKt app/src/main/assets [dossier des captures]
 */
import fr.terminagotchi.Cerveau
import fr.terminagotchi.Deploie
import fr.terminagotchi.EspaceDessin
import fr.terminagotchi.EspaceEtat
import fr.terminagotchi.Explo
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Poses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
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
import javax.imageio.ImageIO

class ActifsE(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilE(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsE(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okE = 0
var koE = 0

fun verifE(c: Boolean, m: String, silencieux: Boolean = false) {
    if (c) okE++ else koE++
    if (!c || !silencieux) println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Le pinceau Java2D : le même contrat que le Canvas du téléphone (EspaceVue.ToileCanvas). */
class ToileJava(val g: java.awt.Graphics2D, val assets: File) : Toile {
    private val images = HashMap<String, BufferedImage>()
    private var monde: BufferedImage? = null
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
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) {
        g.color = c(c); g.stroke = BasicStroke(ep); g.draw(Ellipse2D.Float(cx - r, cy - r, 2 * r, 2 * r))
    }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) {
        g.color = c(c)
        g.stroke = if (plein > 0) BasicStroke(ep, BasicStroke.CAP_BUTT, BasicStroke.JOIN_MITER, 10f, floatArrayOf(plein, vide),
            ((dec % (plein + vide)) + (plein + vide)) % (plein + vide)) else BasicStroke(ep)
        g.draw(Line2D.Float(x1, y1, x2, y2))
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
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float {
        g.font = police(taille, gras, mono)
        return g.fontMetrics.stringWidth(s).toFloat()
    }
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) {
        if (r <= 0) return
        val old = g.paint
        g.paint = RadialGradientPaint(cx, cy, r, floatArrayOf(0f, 1f), arrayOf(c(c), c(c and 0x00FFFFFF)))
        g.fill(Ellipse2D.Float(cx - r, cy - r, 2 * r, 2 * r))
        g.paint = old
    }
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float,
                       rot: Float, alpha: Float) {
        if (alpha <= 0.01f) return
        val im = images.getOrPut(c.cle) {
            BufferedImage(c.w, c.h, BufferedImage.TYPE_INT_ARGB).also { it.setRGB(0, 0, c.w, c.h, c.argb, 0, c.w) }
        }
        val old = g.transform
        val oldC = g.composite
        g.composite = java.awt.AlphaComposite.getInstance(java.awt.AlphaComposite.SRC_OVER, alpha.coerceIn(0f, 1f))
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
        g.composite = oldC
    }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) {
        val b = monde ?: ImageIO.read(File(assets, "intro/monde.jpg")).also { monde = it }
        val ech = maxOf(w / b.width, h / b.height)
        val sw = w / ech; val sh = h / ech
        val sx = ((b.width - sw) / 2).toInt(); val sy = ((b.height - sh) / 2).toInt()
        val oldClip = g.clip
        g.clip(RoundRectangle2D.Float(x, y, w, h, 2 * r, 2 * r))
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BICUBIC)
        g.drawImage(b, x.toInt(), y.toInt(), (x + w).toInt(), (y + h).toInt(), sx, sy, sx + sw.toInt(), sy + sh.toInt(), null)
        g.clip = oldClip
    }
}

fun lisListe(a: JSONArray) = (0 until a.length()).map { a.get(it) }

fun vecteurs(racine: File) {
    println("Les vecteurs communs (donnees/espace/vecteurs.json)")
    val v = JSONObject(File(racine, "donnees/espace/vecteurs.json").readText())
    val existants = setOf("grenier", "fouillis", "parchemin", "vieux_carton")
    val dep = v.getJSONArray("deploie")
    var bons = 0
    for (i in 0 until dep.length()) {
        val d = dep.getJSONObject(i)
        val bl = Deploie.blocs(d.getString("ligne")) { it in existants }
        val attendu = d.getJSONArray("blocs")
        var ok = bl.size == attendu.length()
        for (k in bl.indices) {
            if (!ok) break
            val a = attendu.getJSONArray(k)
            val b = bl[k]
            ok = b.t == a.getString(0) && b.g == a.getString(1) && b.i == a.getInt(2) && b.seg == a.getInt(3) &&
                b.role == a.getString(4) && b.cmd == a.getString(5)
        }
        val ch = Deploie.chaines(bl)
        val ach = d.getJSONArray("chaines")
        ok = ok && ch.size == ach.length()
        for (k in ch.indices) {
            if (!ok) break
            val ac = ach.getJSONObject(k)
            val et = ac.getJSONArray("etapes")
            ok = ch[k].etapes.size == et.length() && ch[k].etapes.indices.all { j ->
                val e = et.getJSONArray(j)
                ch[k].etapes[j].cmd == e.getString(0) && ch[k].etapes[j].debut == e.getInt(1) &&
                    ch[k].etapes[j].fin == e.getInt(2) && ch[k].etapes[j].texte == e.getString(3)
            }
            val r = ch[k].redir
            ok = ok && if (ac.isNull("redir")) r == null else {
                val ar = ac.getJSONArray("redir")
                r != null && r.op == ar.getString(0) && r.fichier == ar.getString(1) && r.k == ar.getInt(2) && r.kOp == ar.getInt(3)
            }
            ok = ok && Deploie.sure(ch[k].etapes) == d.getJSONArray("sure").getBoolean(k)
        }
        verifE(ok, "découpage : ${d.getString("ligne")}", silencieux = true)
        if (ok) bons++
    }
    verifE(bons == dep.length(), "les ${dep.length()} commandes se découpent comme sur PC ($bons)")
    val cv = v.getJSONObject("cerveau")
    verifE(lisListe(cv.getJSONArray("programme")) == Cerveau.PROGRAMME, "le même programme du cerveau")
    val tr = cv.getJSONArray("transitions")
    verifE((0 until tr.length()).map { tr.getJSONArray(it).let { a -> a.getString(0) to a.getString(1) } } == Cerveau.transitions(),
        "les mêmes flèches de la machine à états")
    val seqs = cv.getJSONArray("sequences")
    for (i in 0 until seqs.length()) {
        val s = seqs.getJSONObject(i)
        val vv = Cerveau.Vivant(s.getString("depart"))
        val vo = s.getJSONObject("var")
        vv.v = vo.keys().asSequence().associateWith { vo.getInt(it) }
        val tours = s.getJSONArray("tours")
        var ok = true
        for (k in 0 until tours.length()) {
            val t = tours.getJSONObject(k)
            val f = if (t.isNull("force")) null else t.getString("force")
            if (f != null || vv.force != null) vv.forcer(f)
            val so = t.getJSONObject("signaux")
            val sig = so.keys().asSequence().associateWith { so.getBoolean(it) }
            val trc = vv.tour(sig, 0.0)
            val lignes = t.getJSONArray("lignes")
            val av = t.getJSONObject("var")
            ok = ok && trc.de == t.getString("de") && trc.vers == t.getString("vers") && vv.etat == t.getString("etat") &&
                trc.lignes.size == lignes.length() && trc.lignes.indices.all { j ->
                    lignes.getJSONArray(j).let { a -> a.getInt(0) == trc.lignes[j].first && a.getString(1) == trc.lignes[j].second }
                } && av.keys().asSequence().all { vv.v[it] == av.getInt(it) } &&
                (if (t.isNull("dit")) trc.dit == null else trc.dit == t.getString("dit"))
        }
        verifE(ok, "cerveau : la séquence ${i + 1} (${tours.length()} tours) comme sur PC")
    }
}

fun langues() {
    println("Les textes dans les 14 langues")
    val lignes = listOf("cat lianes.txt | grep -i gland", "ls | grep a > liste.txt", "cd grenier && ls -la", "echo bonjour >> journal.txt",
        "rm -r vieux || echo rate", "wc -l < liste.txt", "head -n 3 repas.txt", "chmod +x miam.sh")
    var mauvais = 0
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        for (l in lignes) {
            val bl = Deploie.blocs(l)
            for (b in bl) { val x = Deploie.longue(b, bl); if (x.isEmpty() || "{" in x || "dep." in x) { mauvais++; println("     $code : $x") } }
        }
        val txt = Cerveau.texteProgramme("Noisette")
        if (txt.size != Cerveau.PROGRAMME.size) mauvais++
        for (x in Cerveau.IDS) if (!Regex("^[a-z_]+$").matches(Cerveau.ident(x))) { mauvais++; println("     $code : ${Cerveau.ident(x)}") }
        if (Cerveau.ETATS.map { Cerveau.ident(it) }.toSet().size != Cerveau.ETATS.size) mauvais++
        for (o in EspaceDessin.ONGLETS) if (Langue.t("esp.onglet.$o").startsWith("esp.")) mauvais++
    }
    Langue.definir("fr")
    verifE(mauvais == 0, "vue déployée, cerveau et onglets traduits partout ($mauvais problème(s))")
}

fun partie(assets: File): Jeu {
    val d = File(System.getProperty("java.io.tmpdir"), "tg_espace_" + System.nanoTime()).apply { mkdirs() }
    val jeu = Jeu(AppareilE(d, assets))
    jeu.changerLangue("fr")
    jeu.nom = "Noisette"
    jeu.xp = 108
    jeu.faim = 38.0
    jeu.extra.put("espece_compagnon", "glandouille")
    Intro.toutDebloquer(jeu)
    val T = jeu.terrain
    for (p in listOf("vestibule", "nid", "grenier/fouillis", "cave", "bibliotheque", "salle_des_machines", "dortoir", "atelier", "tour", "coeur"))
        File(T, p).mkdirs()
    File(T, "grenier/lianes.txt").writeText("Des lianes ont tout mélangé dans le grenier.\nUn Gland doré dort sous le vieux chêne.\n" +
        "Attention : les ronces piquent.\nune liane a enroulé un gland tombé.\n")
    File(T, "grenier/fragment_2.txt").writeText("…\n"); File(T, "grenier/griffure.txt").writeText("griffe\n")
    val h = Histoire.h(jeu)
    for (c in listOf("reveil", "nid", "cave")) h.getJSONArray("ailes").put(c)
    h.getJSONArray("faits").put("nid0")
    Histoire.choisir(jeu, "grenier", dit = false)
    val caps = Explo.captures(jeu)
    for ((e, n) in listOf("Gouttelin" to "Plic", "Zapiot" to "Zap", "Cailloute" to "Caillou"))
        caps.put(JSONObject().put("espece", e).put("nom", n).put("stade", "bebe"))
    Maison.m(jeu).put("cwd", File(T, "grenier").canonicalPath)
    Maison.m(jeu).put("visites", JSONArray(listOf("vestibule", "nid", "cave", "grenier")))
    return jeu
}

fun capture(etat: EspaceEtat, assets: File, f: File, w: Int, h: Int, d: Float, terminal: List<Pair<String, Int>>) {
    val im = BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB)
    val g = im.createGraphics()
    g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
    g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON)
    val tl = ToileJava(g, assets)
    // la barre d'état du téléphone
    val bar = 34 * d
    tl.rect(0f, 0f, w.toFloat(), h.toFloat(), EspaceDessin.FOND)
    tl.texte("16:42", 22 * d, bar / 2 + 2 * d, 15 * d, EspaceDessin.TEXTE, true)
    tl.texte("5G  78 %", w - 22 * d, bar / 2 + 2 * d, 14 * d, EspaceDessin.TEXTE, true, 'd')
    // ce que dessine EspaceVue (le même code que sur le téléphone)
    val hv = EspaceDessin.hauteur(etat.modele, w.toFloat(), 2000 * d, d)
    g.translate(0.0, bar.toDouble())
    EspaceDessin.dessiner(tl, etat.modele, w.toFloat(), hv, d)
    g.translate(0.0, -bar.toDouble())
    // en dessous : le terminal de TerminalActivity (TextView, touches, saisie), simulé ici avec ses couleurs
    val ty = bar + hv + 4 * d
    val th = h - ty - 14 * d
    tl.rrect(12 * d, ty, w - 24 * d, th, 16 * d, 0xFF0A0C11.toInt(), EspaceDessin.BORD, 1 * d)
    var y = ty + 22 * d
    for ((l, c) in terminal) {
        if (y > ty + th - 70 * d) break
        tl.texte(l, 24 * d, y, 13.5f * d, c, false, 'g', true); y += 21 * d
    }
    tl.rect(24 * d + tl.mesure(terminal.last().first + " ", 13.5f * d, false, true), y - 21 * d - 8 * d, 8 * d, 16 * d, EspaceDessin.VERT)
    var kx = 22 * d
    for (k in listOf("Tab", "↑", "|", "-", "/", "~", ">", "⏎")) {
        val kw = (w - 44 * d - 7 * 6 * d) / 8
        tl.rrect(kx, ty + th - 52 * d, kw, 40 * d, 9 * d, if (k == "⏎") 0x283DDC84 else 0x10FFFFFF,
            if (k == "⏎") EspaceDessin.VERT else EspaceDessin.BORD_FORT, 1 * d)
        tl.texte(k, kx + kw / 2, ty + th - 32 * d, 15 * d, if (k == "⏎") EspaceDessin.VERT else EspaceDessin.TEXTE, true, 'c')
        kx += kw + 6 * d
    }
    tl.rrect(w / 2f - 60 * d, h - 8 * d, 120 * d, 4 * d, 2 * d, 0x66FFFFFF, null, 0f)
    g.dispose()
    ImageIO.write(im, "png", f)
}

fun main(args: Array<String>) {
    val assets = File(args.getOrElse(0) { "app/src/main/assets" })
    val racine = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val sortie = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val app = AppareilE(File(System.getProperty("java.io.tmpdir")), assets)
    Langue.init(app)
    Langue.definir("fr")
    Poses.lire(File(assets, "poses.bin").readBytes())
    vecteurs(racine)
    langues()

    println("Une vraie partie dans l'espace de travail")
    val jeu = partie(assets)
    val shell = Shell(jeu.home).also { it.dossier = File(jeu.terrain, "grenier") }
    val e = EspaceEtat(jeu, { shell.dossier }, { shell.chemin() })
    e.rafraichir(null, 0.0)
    jeu.total += 1; jeu.faim = 40.0
    e.rafraichir(0, 0.1)
    val v = e.deployer("cat lianes.txt | grep -i gland")!!
    e.calculer(v)
    verifE(v.blocs.map { it.t } == listOf("cat", "lianes.txt", "|", "grep", "-i", "gland"), "la dernière commande en 6 blocs")
    verifE(v.sorties?.get(0)?.map { it.size } == listOf(4, 2), "4 lignes sortent de cat, grep en garde 2 (${v.sorties})")
    verifE(v.lieu?.second == "grenier", "lianes.txt est relié au Grenier sur la carte (${v.lieu})")
    val v2 = e.deployer("ls | grep a > liste.txt")!!
    e.calculer(v2)
    verifE(!File(jeu.terrain, "grenier/liste.txt").exists(), "la redirection n'est jamais écrite par deploie")
    verifE(v2.chaines[0].redir?.fichier == "liste.txt", "la redirection tombe dans liste.txt")
    var t = 1.0
    repeat(40) { e.tick(0.1, t); t += 0.1 }
    verifE(v2.actif > 1, "le mode automatique allume les blocs un par un (bloc ${v2.actif})")
    e.toucher("dep:suivant")
    verifE(!v2.auto, "toucher la vue : pas à pas")
    e.toucher("forcer:dort")
    repeat(30) { e.tick(0.1, t); t += 0.1 }
    verifE(e.cerveau.etat == "dort" && e.creature.etat == "dort", "forcer « dort » : sa branche, et la créature dort")
    e.toucher("forcer:dort")
    verifE(e.cerveau.force == null, "toucher encore : elle vit toute seule")
    verifE(e.toucher("onglet:cerveau") && e.modele.onglet == "cerveau", "les onglets")
    verifE(e.modele.envies.size == 6 && e.modele.equipe.size == 4 && e.modele.lieux.containsKey("grenier"),
        "le modèle : 6 envies, l'équipe de 4, les lieux de la carte")

    if (sortie != null) {
        println("Les captures du téléphone")
        val d = 1080f / 411f
        val term = listOf("…terminagotchi/grenier $ cat lianes.txt | grep -i" to EspaceDessin.TEXTE,
            "gland" to EspaceDessin.TEXTE, "Un Gland doré dort sous le vieux chêne." to 0xFFD0D0D0.toInt(),
            "une liane a enroulé un gland tombé." to 0xFFD0D0D0.toInt(), "▸ Noisette goûte : grep · faim +2" to EspaceDessin.VERT,
            "…terminagotchi/grenier $" to 0xFF5FD787.toInt())
        e.cerveau.forcer(null)
        e.modele.onglet = "terminal"
        val v3 = e.deployer("cat lianes.txt | grep -i gland", auto = false)!!
        e.calculer(v3)
        v3.actif = 4; v3.t = 0.3; v3.phase = 0.45
        e.cerveau.forcer("mange"); e.tourCerveau = -1e9
        e.tick(0.05, t); t += 0.05
        e.creature.changer("mange", 3.0)
        repeat(8) { e.tick(0.05, t); t += 0.05 }
        e.modele.gains = "faim +2"
        e.preparer(t)
        capture(e, assets, File(sortie, "espace_telephone.png"), 1080, 2340, d, term)
        e.modele.onglet = "cerveau"
        e.tourCerveau = -1e9; e.tick(0.05, t); e.preparer(t + 1.0)
        capture(e, assets, File(sortie, "espace_telephone_cerveau.png"), 1080, 2340, d, term)
        e.modele.onglet = "carte"; e.preparer(t)
        capture(e, assets, File(sortie, "espace_telephone_carte.png"), 1080, 2340, d, term)
        e.modele.onglet = "equipe"; e.preparer(t)
        capture(e, assets, File(sortie, "espace_telephone_equipe.png"), 1080, 2340, d, term)
        e.modele.onglet = "terminal"; e.classe = true; e.preparer(t)
        capture(e, assets, File(sortie, "espace_tablette_classe.png"), 2560, 1600, 2560f / 1280f, term)
        e.classe = false
        verifE(File(sortie, "espace_telephone.png").exists(), "captures écrites dans $sortie")
    }
    println("$okE réussis, $koE échoués")
    if (koE > 0) System.exit(1)
}
