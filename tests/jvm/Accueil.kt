/*
 * Test JVM de l'accueil et de l'aide (idées du 3 novembre) sur Android, portage de pc/outils/test_accueil.py :
 *   1. les vecteurs communs donnees/accueil/vecteurs.json (AideDouce.kt = pc/tg/aide_douce.py) ;
 *   2. la partie : la flèche, le premier ls, `ls ?`, les 3 niveaux d'indice, fermer et revenir, le menu ;
 *   3. les écrans dessinés (Peintre) : « Qui est avec toi ? », les conseils, « Pas de panique », le menu du jeu,
 *      l'écran « Tu peux fermer quand tu veux », l'anneau jaune du clavier ; avec un dossier en 2e argument, leurs PNG.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Accueil.kt -d acc.jar
 *   java -cp <imitations>:<appli.jar>:acc.jar:kotlin-stdlib.jar AccueilKt app/src/main/assets [dossier des aperçus]
 */
import fr.terminagotchi.AccueilDessin
import fr.terminagotchi.AideDouce
import fr.terminagotchi.Carte
import fr.terminagotchi.Commandes
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.MenuParties
import fr.terminagotchi.Peintre
import fr.terminagotchi.Programme
import fr.terminagotchi.Scenes
import fr.terminagotchi.Shell
import fr.terminagotchi.Sprites
import fr.terminagotchi.Tour
import fr.terminagotchi.t
import org.json.JSONArray
import org.json.JSONObject
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
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
fun verifierA(c: Boolean, m: String) {
    if (c) okA++ else koA++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

class PeintreA(val g: java.awt.Graphics2D, val jeu: Jeu?) : Peintre {
    private val polices = HashMap<String, Font>()
    private fun police(taille: Float, mono: Boolean, gras: Boolean, nom: String? = null): Font = polices.getOrPut("$taille$mono$gras$nom") {
        Font(nom ?: if (mono) "DejaVu Sans Mono" else "DejaVu Sans", if (gras) Font.BOLD else Font.PLAIN, 1).deriveFont(taille)
    }
    private fun pourTexte(s: String, taille: Float, mono: Boolean, gras: Boolean): Pair<Font, String> {
        val f = police(taille, mono, gras)
        if (f.canDisplayUpTo(s) == -1) return f to s
        val cjk = police(taille, false, gras, "Noto Sans CJK JP")
        val base = if (cjk.canDisplayUpTo(s.filter { it.code > 0x2E80 }) == -1 && s.any { it.code > 0x2E80 }) cjk else f
        return base to s.filter { base.canDisplay(it) }
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
        val (f, txt) = pourTexte(s, taille, mono, gras)
        g.font = f
        g.color = java.awt.Color(couleur, true)
        g.drawString(txt, x, y)
    }
    override fun mesure(s: String, taille: Float, mono: Boolean, gras: Boolean): Float {
        val (f, txt) = pourTexte(s, taille, mono, gras)
        return g.getFontMetrics(f).stringWidth(txt).toFloat()
    }
    override fun image(p: Carte.Pix, sx: Int, sy: Int, sw: Int, sh: Int, x: Float, y: Float, w: Float, h: Float, lisse: Boolean, version: Int) {
        val b = BufferedImage(p.w, p.h, BufferedImage.TYPE_INT_ARGB)
        b.setRGB(0, 0, p.w, p.h, p.px, 0, p.w)
        val t = g.transform
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, if (lisse) RenderingHints.VALUE_INTERPOLATION_BILINEAR else RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR)
        g.translate(x.toDouble(), y.toDouble())
        g.scale((w / sw).toDouble(), (h / sh).toDouble())
        g.drawImage(b, 0, 0, sw, sh, sx, sy, sx + sw, sy + sh, null)
        g.transform = t
    }
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

fun apercuA(sortie: File?, nom: String, jeu: Jeu?, focus: Int = -1, dessin: (Peintre) -> Intro.Rendu): Intro.Rendu {
    val essai = BufferedImage(10, 10, BufferedImage.TYPE_INT_ARGB)
    val r = dessin(PeintreA(essai.createGraphics(), jeu))
    if (sortie != null) {
        val e = 3f
        val img = BufferedImage((r.l * e).toInt(), (r.h * e).toInt(), BufferedImage.TYPE_INT_ARGB)
        val g = img.createGraphics()
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON)
        g.scale(e.toDouble(), e.toDouble())
        val p = PeintreA(g, jeu)
        val r2 = dessin(p)
        if (focus >= 0) AccueilDessin.anneau(p, r2, focus)
        javax.imageio.ImageIO.write(img, "png", File(sortie, "$nom.png"))
    }
    return r
}

fun lst(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }
fun opt(o: JSONObject, k: String): String? = if (o.isNull(k)) null else o.getString(k)

fun main(args: Array<String>) {
    val assets = File(args[0])
    val sortie = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val depot = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_accueil_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilA(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    Scenes.chargeur = { nom -> File(assets, "intro/$nom.jpg").takeIf { it.isFile }?.let { javax.imageio.ImageIO.read(it) }?.let { b ->
        Carte.Pix(b.width, b.height, b.getRGB(0, 0, b.width, b.height, null, 0, b.width)) } }
    Intro.init(app)

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/accueil/vecteurs.json").readText())
    fun tous(nom: String, f: (JSONObject) -> Boolean): Boolean {
        val a = v.getJSONArray(nom)
        val faux = (0 until a.length()).map { a.getJSONObject(it) }.filter { !f(it) }
        faux.take(3).forEach { println("    ≠ $nom : $it") }
        return faux.isEmpty()
    }
    verifierA(tous("fleche") { AideDouce.fleche(it.getBoolean("intro"), it.getInt("reussies"), it.getDouble("depuis")) == it.getBoolean("ok") }, "la flèche « tape ici »")
    verifierA(tous("vif") { AideDouce.perduVif(it.getInt("erreurs"), it.getDouble("depuis")) == it.getBoolean("ok") }, "« Perdu ? » jaune vif")
    verifierA(tous("touche") { AideDouce.toucheAAllumer(it.getString("attendu"), it.getString("tape")) == opt(it, "touche") }, "la touche qui s'allume")
    verifierA(tous("symbole") { AideDouce.symboleNouveau(it.getString("attendu"), lst(it.getJSONArray("vus"))) == opt(it, "symbole") }, "le symbole à expliquer")
    verifierA(tous("explique") { AideDouce.demandeExplique(it.getString("ligne")) == opt(it, "nom") }, "`ls ?` / `? ls`")
    verifierA(tous("indice") { AideDouce.partiesIndice(it.getString("attendu")).let { p -> p["cmd"] == it.getString("cmd") && p["debut"] == it.getString("debut") && p["reponse"] == it.getString("reponse") } }, "les 3 niveaux d'indice")
    verifierA(tous("fantome") { AideDouce.fantome(it.getString("mot"), lst(it.getJSONArray("candidats"))) == it.getString("fin") }, "la fin grisée")
    verifierA(tous("tronc") { AideDouce.troncFini(lst(it.getJSONArray("ailes")), it.getJSONObject("tronc")) == it.getBoolean("fini") }, "la fin du tronc commun")
    verifierA(tous("duree_ls") { AideDouce.dureeLs(it.getBoolean("camp")) == it.getDouble("s") }, "la durée du premier ls")
    verifierA(tous("menu") { AideDouce.actionMenu(it.getString("r")) == opt(it, "action") }, "le menu (chiffres, q)")
    val rg = v.getJSONObject("rangees")
    verifierA(lst(rg.getJSONArray("r1")) == AideDouce.RANGEE1 && lst(rg.getJSONArray("r2")) == AideDouce.RANGEE2 &&
        lst(rg.getJSONArray("ordre")) == AideDouce.ORDRE_SYMBOLES, "les deux rangées de touches")

    println("2. Une partie")
    val jeu = Jeu(app)
    jeu.changerLangue("fr")
    jeu.nom = "Pixel"
    Intro.nouvellePartie(jeu)
    jeu.sauver()
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })
    fun tape(cmd: String, code: Int = 0): String? {
        val r = commandes.executer(cmd)?.texte
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier, code = code)
        return AideDouce.apresCommande(jeu, cmd, code == 0) ?: r
    }
    verifierA(AideDouce.flecheMaintenant(jeu) == "pwd", "la flèche montre la première commande de l'œuf (pwd)")
    verifierA(tape("ls") == "premier_ls", "le premier ls réussi : la cinématique")
    tape("pwd"); tape("echo bonjour")
    verifierA(AideDouce.flecheMaintenant(jeu) == null, "3 commandes réussies : la flèche s'en va")
    verifierA(tape("ls") != "premier_ls", "le premier ls ne revient jamais")
    tape("nexistepas", 127); tape("nexistepas", 127)
    verifierA(AideDouce.perduVif(AideDouce.a(jeu).optInt("erreurs"), 0.0), "2 erreurs de suite : « Perdu ? » jaune vif")
    tape("whoami")
    val f = AideDouce.ficheCourte("ls")
    verifierA("ls, en mots d'enfant" in f && "ls --help" in f && "explique ls" in f, "`ls ?` : la fiche courte")
    val ip = AideDouce.infosPerdu(jeu)
    verifierA(ip.first.isNotEmpty() && ip.second.isNotEmpty(), "« Pas de panique » : où es-tu, ta leçon (${ip.second.take(40)})")
    verifierA(AideDouce.texteDemandeIndice(jeu).startsWith("💡 " + t("ad.ind.rien").take(10)), "rien à deviner hors exercice")
    // la chasse au trésor (CTF du téléphone) : les mêmes 3 niveaux, rien n'est retiré
    File(jeu.terrain, "nid").mkdirs()
    fr.terminagotchi.Ctf.ouvrir(jeu, "nouveau")
    val ctf = fr.terminagotchi.Ctf.dossier(jeu)
    verifierA(AideDouce.cible(jeu, ctf)?.first == "ctf:01_cache" && AideDouce.cible(jeu, shell.dossier) == null,
        "chasse au trésor : à sa racine, la 1re épreuve pas encore trouvée ; ailleurs, rien")
    val meule = File(ctf, "02_meule")
    val niv = (1..4).map { AideDouce.texteDemandeIndice(jeu, meule) }
    val l3 = fr.terminagotchi.Langue.liste("ctf.meule.indices")
    verifierA((0..2).all { i -> "(${i + 1}/3)" in niv[i] && l3[i] in niv[i] } && "(3/3)" in niv[3] && t("ad.ind.rien_retire") in niv[2],
        "02_meule : coup de pouce, plus clair, la réponse (`grep TG journal.log`), rien n'est retiré")
    verifierA(fr.terminagotchi.Ctf.indice(jeu, "5").let { "(1/3)" in it && fr.terminagotchi.Langue.liste("ctf.code.indices")[0] in it } &&
        fr.terminagotchi.Ctf.indice(jeu, "9") == t("ctf.indice.hors", "n" to 7), "`indice 5` (écrit dans les LISEZMOI) : l'épreuve 5, niveau 1")
    val drap = Regex("TG\\{[^}]+\\}").find(File(meule, "journal.log").readText())!!.value
    val gagne = fr.terminagotchi.Ctf.valider(jeu, drap)
    verifierA("+40 XP" in gagne, "après les 3 indices, le trésor rapporte autant (+40 XP)")
    verifierA(AideDouce.cible(jeu, meule) == null, "épreuve trouvée : plus d'indice à donner")
    // fermer et revenir
    val h = Histoire.h(jeu)
    for (c in listOf("reveil", "nid", "bibliotheque", "cave")) h.put("ailes", h.optJSONArray("ailes").put(c))
    AideDouce.proposerFermer(jeu)
    val file = lst(Intro.deb(jeu).optJSONArray("file"))
    verifierA("fermer" in file, "fin du tronc commun : l'écran « fermer et revenir » attend son tour")
    AideDouce.marquerFermer(jeu)
    verifierA(AideDouce.retour(jeu) == t("ad.fermer.retour") && AideDouce.retour(jeu) == null, "au retour : « Te revoilà ! », une fois")
    verifierA(Intro.contenu(jeu, "fermer").second.any { "✕" in it }, "le téléphone dit : appuie sur ✕")
    // le menu
    val menu = MenuParties(app, jeu, apresChangement = {}, synchroniser = {}, texteCompte = { "(compte)" }, plusTard = {})
    val m = menu.ouvrir()
    verifierA(listOf("part.m.jouer", "part.m.options", "part.m.aide_menu", "part.m.quitter").all { t(it) in m }, "le menu : Jouer… Options, Aide, Quitter")
    verifierA(menu.repondre("4")?.contains("(compte)") == true, "Options : le compte y est")
    menu.ouvrir()
    verifierA(menu.repondre("5")?.contains(t("ad.parent.c1.t")) == true, "Aide : les conseils pour les parents")
    menu.ouvrir(); menu.repondre("q")
    verifierA(menu.quitter, "q : quitter")
    verifierA(MenuParties.action("aide") == "aide" && MenuParties.action("options") == "options", "les mots aussi")

    println("3. Les écrans dessinés")
    val l = 360f
    val p1 = apercuA(sortie, "tel_1_qui_est_avec_toi", null) { AccueilDessin.parent(it, 1, l) }
    verifierA(p1.boutons.map { it.action } == listOf("seul", "adulte"), "« Qui est avec toi ? » : seul / adulte")
    val p2 = apercuA(sortie, "tel_1_conseils", null) { AccueilDessin.parent(it, 2, l) }
    verifierA(p2.boutons.map { it.action } == listOf("parti") && p2.h > p1.h, "les 4 conseils, puis C'est parti")
    apercuA(sortie, "tel_69_clavier", null, focus = 0) { AccueilDessin.parent(it, 1, l, clavier = true) }
    val pp = apercuA(sortie, "tel_6_pas_de_panique", jeu) { AccueilDessin.perdu(it, ip, l) }
    verifierA(pp.boutons.map { it.action } == listOf("camp", "ok"), "« Pas de panique » : me ramener au camp / OK")
    val mv = apercuA(sortie, "tel_79_menu", jeu) { AccueilDessin.menu(it, l, 720f, menu.texteQui(), menu.texteCompteCourt(), 5000L) }
    verifierA(mv.boutons.map { it.action } == listOf("1", "2", "3", "4", "5", "q"), "le menu du jeu : 6 boutons")
    apercuA(sortie, "tel_79_menu_clavier", jeu, focus = 3) { AccueilDessin.menu(it, l, 720f, menu.texteQui(), menu.texteCompteCourt(), 5000L, clavier = true) }
    val fc = apercuA(sortie, "tel_9_fermer", jeu) { Intro.dessinerCarte(it, jeu, "fermer", l) }
    verifierA(fc.boutons.size == 1, "« Tu peux fermer quand tu veux » : Plus tard ▶")
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val r = apercuA(null, "x", jeu) { AccueilDessin.parent(it, 2, l) }
        if (r.h > 2000f) verifierA(false, "$code : les conseils tiennent")
    }
    Langue.definir("fr")
    verifierA(true, "les conseils se dessinent dans les 14 langues")

    println("\n$okA réussis, $koA ratés")
    kotlin.system.exitProcess(if (koA == 0) 0 else 1)
}
