/*
 * Test JVM de l'introduction et du déblocage progressif (Intro.kt, IntroVue) : une NOUVELLE PARTIE comme dans l'appli
 * (le nom tapé : Intro.nouvellePartie), puis les commandes tapées une par une jusqu'à l'éclosion, sans XP offerte ;
 * l'écran « merci » ; la table de déblocage (assets/intro.json = donnees/intro.json, la même que sur PC) dans l'ordre
 * de l'histoire ; « pas encore » ; la migration des anciennes parties ; « debloquer tout » ; les images de l'œuf
 * identiques au PC (python3 pc/tg/intro.py) ; les régions gardées grisées sur la carte ; les 14 langues ; et les
 * dessins (Peintre) : avec un dossier en 2e argument, les aperçus PNG de chaque écran et de chaque animation.
 *
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Intro.kt -d intro.jar
 *   java -cp <imitations>:<appli.jar>:intro.jar:kotlin-stdlib.jar IntroKt app/src/main/assets [dossier des aperçus]
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Carte
import fr.terminagotchi.Commandes
import fr.terminagotchi.Explo
import fr.terminagotchi.Guide
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.Oeufs
import fr.terminagotchi.Parties
import fr.terminagotchi.Peintre
import fr.terminagotchi.Regles
import fr.terminagotchi.Scenes
import fr.terminagotchi.Shell
import fr.terminagotchi.Sprites
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import java.io.File

class ActifsI(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilI(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsI(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okI = 0
var koI = 0
fun verifier(c: Boolean, m: String) {
    if (c) okI++ else koI++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Le peintre des aperçus : java.awt, polices DejaVu (CJK : Noto), les caractères qu'aucune police n'a sont sautés. */
class PeintreI(val g: java.awt.Graphics2D, val jeu: Jeu?) : Peintre {
    private val polices = HashMap<String, Font>()
    private fun police(taille: Float, mono: Boolean, gras: Boolean, nom: String? = null): Font = polices.getOrPut("$taille$mono$gras$nom") {
        Font(nom ?: if (mono) "DejaVu Sans Mono" else "DejaVu Sans", if (gras) Font.BOLD else Font.PLAIN, 1).deriveFont(taille)
    }
    private fun pourTexte(s: String, taille: Float, mono: Boolean, gras: Boolean): Pair<Font, String> {
        val f = police(taille, mono, gras)
        if (f.canDisplayUpTo(s) == -1) return f to s
        val cjk = police(taille, false, gras, "Noto Sans CJK JP")
        val base = if (cjk.canDisplayUpTo(s.filter { it.code > 0x2E80 }) == -1 && s.any { it.code > 0x2E80 }) cjk else f
        return base to s.filter { base.canDisplay(it) || it.isSurrogate() && false }
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
    private val images = java.util.IdentityHashMap<Carte.Pix, Pair<BufferedImage, Int>>()
    override fun image(p: Carte.Pix, sx: Int, sy: Int, sw: Int, sh: Int, x: Float, y: Float, w: Float, h: Float, lisse: Boolean, version: Int) {
        val (b, v) = images[p] ?: (BufferedImage(p.w, p.h, BufferedImage.TYPE_INT_ARGB) to Int.MIN_VALUE)
        if (v != version) b.setRGB(0, 0, p.w, p.h, p.px, 0, p.w)
        images[p] = b to version
        val t = g.transform
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, if (lisse) RenderingHints.VALUE_INTERPOLATION_BILINEAR else RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR)
        g.translate(x.toDouble(), y.toDouble())
        g.scale((w / sw).toDouble(), (h / sh).toDouble())
        g.drawImage(b, 0, 0, sw, sh, sx, sy, sx + sw, sy + sh, null)
        g.transform = t
    }
    override fun lueur(x: Float, y: Float, r: Float, couleur: Int) {
        if (r <= 0f) return
        g.paint = java.awt.RadialGradientPaint(x, y, r, floatArrayOf(0f, 1f), arrayOf(java.awt.Color(couleur, true), java.awt.Color(couleur and 0xFFFFFF, true)))
        g.fill(java.awt.geom.Ellipse2D.Float(x - r, y - r, 2 * r, 2 * r))
    }
    override fun bebePix(): Carte.Pix? {
        val j = jeu ?: return null
        val f = System.getProperty("tg.portraits")?.let { File(it, j.extra.optString("espece_compagnon") + "/classique_bebe.png") }
        if (f != null && f.isFile) { val b = javax.imageio.ImageIO.read(f); return Carte.Pix(b.width, b.height, b.getRGB(0, 0, b.width, b.height, null, 0, b.width)) }
        val b = try { Sprites.bitmap(j, 8, st = 1) } catch (e: Exception) { return null }
        val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        return Carte.Pix(b.width, b.height, px)
    }
    override fun bebe(x: Float, y: Float, h: Float): Boolean {
        val j = jeu ?: return false
        // comme IntroVue : le portrait du bébé (assets/portraits, en .webp que java ne lit pas : une copie .png dans le
        // dossier -Dtg.portraits, si on l'a préparée), sinon son sprite du jeu
        val id = j.extra.optString("espece_compagnon")
        val f = System.getProperty("tg.portraits")?.let { File(it, "$id/classique_bebe.png") }
        if (f != null && f.isFile) {
            val b = javax.imageio.ImageIO.read(f)
            val w = h * b.width / b.height
            image(Carte.Pix(b.width, b.height, b.getRGB(0, 0, b.width, b.height, null, 0, b.width)), 0, 0, b.width, b.height, x - w / 2, y - h, w, h, false, 0)
            return true
        }
        val b = try { Sprites.bitmap(j, 8, st = 1) } catch (e: Exception) { return false }
        val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height)
        val w = h * b.width / b.height
        image(Carte.Pix(b.width, b.height, px), 0, 0, b.width, b.height, x - w / 2, y - h, w, h, false, 0)
        return true
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

/** Dessine un écran de l'intro (largeur d'un téléphone : 360 dp) ; l'enregistre si un nom et un dossier sont donnés. */
fun apercu(sortie: File?, nom: String?, jeu: Jeu?, dessin: (Peintre) -> Intro.Rendu): Intro.Rendu {
    val essai = BufferedImage(10, 10, BufferedImage.TYPE_INT_ARGB)
    val r = dessin(PeintreI(essai.createGraphics(), jeu))
    if (sortie != null && nom != null) {
        val e = 3f
        val img = BufferedImage((r.l * e).toInt(), (r.h * e).toInt(), BufferedImage.TYPE_INT_ARGB)
        val g = img.createGraphics()
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON)
        g.scale(e.toDouble(), e.toDouble())
        dessin(PeintreI(g, jeu))
        javax.imageio.ImageIO.write(img, "png", File(sortie, "$nom.png"))
    }
    return r
}

class PartieI(val app: AppareilI) {
    val jeu = Jeu(app)
    val shell = Shell(jeu.home)
    val commandes = Commandes(app, jeu, { shell.dossier })

    fun bash(cmd: String): String {
        val pb = ProcessBuilder("bash", "-c", cmd).directory(shell.dossier).redirectErrorStream(true)
        pb.environment()["HOME"] = jeu.home.absolutePath
        pb.environment()["LC_ALL"] = "C.UTF-8"
        val p = pb.start()
        val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
        p.waitFor()
        return s
    }

    /** L'enfant tape une commande dans l'appli (commande intégrée, sinon le shell), puis le tour de jeu. */
    fun tape(cmd: String): String {
        val mot = cmd.trim().split(Regex("\\s+"))[0]
        val sortie = if (mot == "cd") shell.executer(cmd) else commandes.executer(cmd)?.texte ?: bash(cmd)
        if (Intro.enCours(jeu) && "not found" in sortie.lowercase()) Intro.signalerErreur(jeu)
        Tour.apresCommande(jeu, cmd, colle = false, rappel = false, hasard = false, cwd = shell.dossier)
        Tour.periodique(jeu, shell.dossier)
        jeu.sauver()
        return sortie
    }
}

fun cles(fr: JSONObject, s: String): List<String> =
    Regex("\\b[a-z_]+(?:\\.[\\w-]+)+\\b").findAll(s).map { it.value }.filter { fr.has(it) }.toList()

fun main(args: Array<String>) {
    val assets = File(args[0])
    val sortie = args.getOrNull(1)?.let { File(it).apply { mkdirs() } }
    val depot = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_intro_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilI(File(dossier, "app").apply { mkdirs() }, assets)
    Langue.init(app)
    Langue.definir("fr")
    Scenes.chargeur = { nom -> File(assets, "intro/$nom.jpg").takeIf { it.isFile }?.let { javax.imageio.ImageIO.read(it) }?.let { b ->
        Carte.Pix(b.width, b.height, b.getRGB(0, 0, b.width, b.height, null, 0, b.width)) } }
    Intro.init(app)
    val fr = JSONObject(File(assets, "langues/fr.json").readText())

    println("1. Les données : une seule source (donnees/intro.json), la même que sur PC")
    val src = File(depot, "donnees/intro.json").readText()
    verifier(File(assets, "intro.json").readText() == src, "assets/intro.json = donnees/intro.json")
    verifier(File(depot, "pc/tg/intro.json").readText() == src, "pc/tg/intro.json = donnees/intro.json")
    val ids = Intro.fonctions().map { it.id }
    verifier(ids.size == 12 && ids[0] == "histoire" && ids.toSet().size == 12, "12 fonctions : ${ids.joinToString(", ")}")
    verifier(Intro.fonctions().flatMap { it.commandes }.let { it.size == it.toSet().size }, "chaque commande appartient à une seule fonction")
    verifier(Intro.fonctions().filter { it.id != "histoire" }.all { fr.has("deb.${it.id}.titre") && fr.has("deb.${it.id}.texte") && it.cmdTel.isNotEmpty() },
        "chaque fonction a son titre, son texte et ses commandes Android")
    verifier(Intro.liste().map { it.id } == listOf("pwd", "ls", "echo", "whoami"), "la liste de l'œuf : pwd, ls, echo, whoami")
    verifier(Intro.liste().all { it.re.containsMatchIn(Intro.commandeDe(it)) }, "chaque commande montrée est reconnue")

    println("2. Nouvelle partie (comme le menu, puis le nom tapé) : l'œuf seul")
    Parties.nouvelle(app)
    val p = PartieI(app)
    p.jeu.changerLangue("fr")
    p.jeu.nom = "Pixou"
    Intro.nouvellePartie(p.jeu)          // ce que fait TerminalActivity quand le nom est tapé
    p.jeu.sauver()
    val j = p.jeu
    verifier(Intro.enCours(j) && Intro.fonctions().none { Intro.ouvert(j, it.id) }, "l'œuf attend, rien n'est ouvert")
    val liste = Vert0(Intro.texteListe(j))
    verifier(listOf("pwd", "ls", "echo bonjour", "whoami").all { it in liste } && liste.startsWith("➜"), "la liste : ➜ pwd, · ls, · echo bonjour, · whoami")
    verifier(Intro.astuce(j) == Langue.t("intro.astuce.0"), "1re astuce : taper la commande en vert, puis Entrée")
    for (c in listOf("carte", "envies", "quetes", "guide", "troupe", "entrainement", "badges", "compte", "donjon", "ctf", "explique", "defi", "notif")) {
        val r = p.commandes.executer(c)?.texte ?: ""
        verifier("pas encore" in r && "`$c`" in r, "« $c » : pas encore (jamais une erreur)")
    }
    verifier(Intro.bloque(j, "carte", "gare de lyon") == null, "« carte gare de lyon » (le plan de la ville) reste là")
    verifier(p.commandes.executer("equipe guide Pixou")?.texte?.contains("pas encore") == true, "« equipe guide » : pas encore")
    verifier(p.commandes.executer("caresse") != null && "pas encore" !in (p.commandes.executer("caresse")?.texte ?: ""),
        "les câlins à l'œuf restent possibles")

    println("3. Chaque bonne commande fait réagir l'œuf ; il n'éclot qu'à la fin de la liste")
    p.tape("ls")
    verifier(Intro.faits(j) == listOf("ls") && j.anim?.first == "oeuf_1", "ls : l'œuf remue et se fêle (oeuf_1)")
    verifier(j.stade == 0 && j.xp <= 9, "toujours un œuf (${j.xp} XP)")
    verifier(Intro.astuce(j) == Langue.t("intro.astuce.1"), "2e astuce : une erreur n'est pas grave")
    p.tape("blablabla")
    verifier(Intro.astuce(j) == Langue.t("intro.astuce.erreur"), "une commande inconnue : « ce n'est pas grave »")
    for (c in listOf("pwd", "date", "uname", "id", "df", "uptime")) p.tape(c)
    verifier(Intro.faits(j) == listOf("ls", "pwd") && j.xp <= 9 && j.niveau == 1, "plein de commandes : l'œuf garde 9 XP au plus (${j.xp})")
    verifier(Intro.astuce(j) == Langue.t("intro.astuce.2"), "3e astuce : ↑ rappelle la commande d'avant")
    p.tape("echo")
    verifier(Intro.faits(j).size == 2, "« echo » sans message ne compte pas")
    p.tape("whoami")
    verifier(j.anim?.first == "oeuf_3" && Intro.astuce(j) == Langue.t("intro.astuce.3"), "whoami : 3e fêlure ; 4e astuce : Tab complète")
    verifier(Histoire.leconCourante(j)?.id == "t0" && j.niveau < (Histoire.leconCourante(j)?.niveau ?: 0), "la leçon 1 attend l'éclosion")

    println("4. echo bonjour : l'éclosion et l'écran merci")
    p.tape("echo bonjour")
    verifier(Intro.eclos(j) && j.niveau == 2 && j.stade == 1, "l'œuf a éclos : bébé, niveau 2")
    verifier(j.anim?.first == "eclosion", "animation de l'éclosion")
    verifier(Intro.ouvert(j, "histoire") && Intro.aMontrer(j) == "merci", "l'histoire s'ouvre ; l'écran « merci » attend")
    verifier(Histoire.leconCourante(j)?.id == "t0" && j.etape == 0 && j.etapeCourante()?.cmd == "pwd",
        "la leçon 1 commence (pwd) : les commandes de l'œuf ne l'ont pas validée")
    val (titre, paras) = Intro.contenu(j, "merci", j.home.path)
    val merci = (listOf(titre) + paras).joinToString("\n")
    verifier("Pixou" in titre && Langue.t("intro.recap") in merci && "print working directory" in merci,
        "merci : la créature remercie et donne le vrai sens des commandes")
    Intro.lu(j)
    val ici = Intro.contenu(j, "merci2", j.home.path).second.joinToString("\n")
    verifier(j.home.path in ici && "pwd" in ici && Langue.t("hist.reveil.titre") in ici, "où on est (ce que pwd a montré) et la suite : le chapitre 1")
    Intro.lu(j)
    verifier(Intro.aMontrer(j) == null, "les deux écrans lus")

    println("5. La table de déblocage, dans l'ordre de l'histoire")
    val h = Histoire.h(j)
    fun etape(msg: String, attendu: String, fn: () -> Unit) {
        fn()
        Intro.verifier(j)
        val file = Intro.deb(j).getJSONArray("file")
        verifier(Intro.ouvert(j, attendu) && (0 until file.length()).any { file.getString(it) == attendu }, "$msg → $attendu")
        Intro.deb(j).put("file", JSONArray())
    }
    fun ajoute(k: String, v: String) { h.getJSONArray(k).put(v) }
    etape("leçon t0", "envies") { ajoute("faits", "t0") }
    verifier(j.journal.any { it.contains("✨") && it.contains(Langue.t("deb.envies.titre")) }, "une ligne ✨ Nouveau dans le journal")
    verifier("pas encore" !in (p.commandes.executer("envies")?.texte ?: ""), "« envies » répond maintenant")
    etape("chapitre 1", "carte") { ajoute("faits", "reveil1"); ajoute("ailes", "reveil") }
    etape("leçon debarras", "lexique") { ajoute("faits", "nid0"); ajoute("faits", "debarras") }
    etape("leçon nid1", "quetes") { ajoute("faits", "nid1") }
    etape("chapitre 2", "combats") { ajoute("ailes", "nid") }
    etape("niveau 4", "extras") { j.xp = 90 }
    val feu = Bestiaire.publiques().first { Guide.typeDe(it) == "feu" }
    etape("une bestiole dressée", "equipe") {
        Explo.captures(j).put(Bestiaire.individu(feu, false, feu.zone).put("stade", "enfant").put("xp", 0))
    }
    etape("niveau 6", "entrainement") { j.xp = 250 }
    etape("une aile", "compte") { ajoute("ailes", "grenier") }
    etape("deux ailes", "biomes") { ajoute("ailes", "cave") }
    etape("trois ailes", "donjon") { ajoute("ailes", "bibliotheque") }
    verifier(Intro.fonctions().all { Intro.ouvert(j, it.id) }, "tout est ouvert à la fin")
    val eq = Intro.contenu(j, "equipe").second.joinToString()
    verifier("`equipe`" in eq && "`guide <nom>`" in eq, "l'écran de l'équipe donne les commandes Android")

    println("6. Les images de l'œuf : les mêmes qu'au PC (pc/tg/intro.py), pour les 9 types")
    val combos = mutableListOf<Triple<Int, String, Int>>()
    for (n in 1..4) combos.addAll(Intro.reaction(n))
    for (f in 0..3) combos.add(Triple(f, "", 0))
    val tous = Guide.TYPES.flatMap { ty -> combos.map { ty to it } }
    val py = ProcessBuilder("python3", "-c", "import json,sys;sys.path.insert(0,'${File(depot, "pc").path}');from tg import intro;" +
        "print(json.dumps([intro.image_oeuf(f,n,k,ty) for ty,f,n,k in json.loads(sys.argv[1])]))",
        JSONArray(tous.map { (ty, c) -> JSONArray().put(ty).put(c.first).put(c.second).put(c.third) }).toString())
        .redirectErrorStream(true).start()
    val pyOut = py.inputStream.readBytes().toString(Charsets.UTF_8).trim()
    py.waitFor()
    val attendu = JSONArray(tous.map { (ty, c) -> Intro.imageOeuf(c.first, c.second, c.third, ty)?.let { JSONArray(it) } ?: JSONObject.NULL })
    verifier(try { JSONArray(pyOut).toString() == attendu.toString() } catch (e: Exception) { false },
        "${tous.size} images de l'œuf identiques sur PC et Android (${combos.size} par type × ${Guide.TYPES.size} types)")
    val pyPal = ProcessBuilder("python3", "-c", "import json,sys;sys.path.insert(0,'${File(depot, "pc").path}');from tg import oeufs;" +
        "print(json.dumps({t:{k:int(v[1:],16) for k,v in sorted(oeufs.palette(t).items())} for t in oeufs.types()}))").redirectErrorStream(true).start()
    val palPc = JSONObject(pyPal.inputStream.readBytes().toString(Charsets.UTF_8).trim())
    verifier(Guide.TYPES.all { ty -> Oeufs.palette(ty).all { (c, v) -> palPc.getJSONObject(ty).optInt(c.toString(), -1) == (v and 0xFFFFFF) } &&
        Oeufs.palette(ty).size == palPc.getJSONObject(ty).length() }, "les couleurs des 9 œufs : les mêmes qu'au PC")
    verifier(File(depot, "donnees/oeufs/oeufs.json").readText() == File(assets, "oeufs.json").readText(), "assets/oeufs.json = donnees/oeufs/oeufs.json")
    val fel = (0..3).map { f -> Intro.imageOeuf(f)!!.sumOf { r -> r.count { it == 'f' } } }
    verifier(fel[0] == 0 && fel[0] < fel[1] && fel[1] < fel[3] && (0..3).map { Intro.imageOeuf(it) }.toSet().size == 4,
        "3 stades de fêlure (intact, une fêlure qui luit, fissuré, une grande fêlure) : $fel")
    verifier(Intro.imageOeuf(3, "eclot", 7) == null, "fin de l'éclosion : la créature prend la place")
    verifier(Oeufs.typeDe(j) == Guide.g(j).optString("type_c") && j.extra.optString("oeuf_type") == Oeufs.typeDe(j),
        "nouvelle partie : un œuf ${Oeufs.typeDe(j)}, et le compagnon qui en sort est du même type")
    println("6b. Le bébé qui sort de l'œuf : une vraie espèce de départ (la même règle qu'au PC)")
    verifier(File(depot, "donnees/oeufs/depart.json").readText() == File(assets, "depart.json").readText(), "assets/depart.json = donnees/oeufs/depart.json")
    val pyDep = ProcessBuilder("python3", "-c", "import json,sys;sys.path.insert(0,'${File(depot, "pc").path}');from tg import oeufs;" +
        "print(json.dumps(oeufs.departs()))").redirectErrorStream(true).start()
    val depPc = JSONObject(pyDep.inputStream.readBytes().toString(Charsets.UTF_8).trim())
    verifier(Guide.TYPES.all { ty -> Oeufs.departs()[ty]?.size in 2..3 && Oeufs.departs()[ty] == (0 until depPc.getJSONArray(ty).length()).map { depPc.getJSONArray(ty).getString(it) } &&
        Oeufs.departs()[ty]!!.all { Bestiaire.espece(it)?.id == it && Guide.typeDe(Bestiaire.espece(it)) == ty } }, "les espèces de départ : les mêmes qu'au PC, 2 ou 3 par type, du bon type")
    verifier(j.especeCompagnon in Oeufs.departs()[Oeufs.typeDe(j)]!!, "nouvelle partie : un ${j.especeCompagnon} est sorti de l'œuf ${Oeufs.typeDe(j)}")
    val tirages = (1..300).map { val x = Jeu(app); x.extra = JSONObject(); Oeufs.choisir(x); x.extra.optString("oeuf_type") to x.especeCompagnon }
    verifier(tirages.all { (ty, e) -> e in Oeufs.departs()[ty]!! } && tirages.map { it.second }.toSet().size >= 20, "l'espèce est tirée au hasard dans la liste du type")
    val g = Jeu(app)
    g.extra = JSONObject().put("espece_compagnon", "gouttelin")
    val pySp = ProcessBuilder("python3", "-c", "import json,sys;sys.path.insert(0,'${File(depot, "pc").path}');from tg import sprites;" +
        "s={'espece_compagnon':'gouttelin','xp':10,'hunger':80,'stats':{}};" +
        "print(json.dumps([[sprites.get_sprite(s,k),{c:int(v[1:],16) for c,v in sprites.palette(s,st=k).items()}] for k in (1,2,3)]))").redirectErrorStream(true).start()
    val spPc = JSONArray(pySp.inputStream.readBytes().toString(Charsets.UTF_8).trim())
    verifier((1..3).all { k -> val a = spPc.getJSONArray(k - 1)
        Sprites.lignes(g, k) == (0 until a.getJSONArray(0).length()).map { a.getJSONArray(0).getString(it) } &&
        Sprites.couleurs(g, false, k).all { (c, v) -> a.getJSONObject(1).optInt(c.toString(), -1) == (v and 0xFFFFFF) } },
        "le compagnon Gouttelin : bébé, ado, adulte dessinés pixel par pixel comme au PC")
    verifier(Regles.espece(1, null, "gouttelin") == "Bébé Gouttelin" && Regles.espece(3, "Force", "gouttelin") == "Adulte Gouttelin",
        "son nom d'espèce : « Bébé Gouttelin », puis « Adulte Gouttelin »")
    g.xp = 10
    val bm = Sprites.bitmap(g, 12)
    verifier(bm.width <= 18 * 12 + 24 && bm.height <= 16 * 12 + 24 && Sprites.animation(g, "evolution").images.size > 4,
        "image du widget à la même taille qu'avant (${bm.width}×${bm.height}), animation d'évolution qui marche")
    verifier(Langue.t("intro.oeuf.titre", "type" to Guide.nomType("glace")) == "œuf Glace", "écran de l'œuf : « œuf Glace » (plus « un œuf mystérieux »)")

    println("6c. L'œuf fin (préparé pour l'écran de l'œuf, 4 fois plus détaillé)")
    verifier(Oeufs.aDesFins(), "assets/oeufs_fins.json se lit")
    var finOk = true
    for (ty in Guide.TYPES) for (c in combos) {
        val lo = Intro.imageOeuf(c.first, c.second, c.third, ty)
        val hi = Oeufs.fin(ty, c.first, c.second, c.third)
        if ((lo == null) != (hi == null)) finOk = false
        if (lo == null || hi == null) continue
        if (hi.w != 26 * 4 || hi.h != 26 * 4) finOk = false
        // même silhouette : un pixel de l'œuf « grand » = un carré 4×4 de l'œuf fin, plein à moitié au moins (± les bords)
        var pareil = 0; var total = 0
        for (y in 0 until 26) for (x in 0 until 26) {
            val plein = (0 until 16).count { hi.px[(y * 4 + it / 4) * hi.w + x * 4 + it % 4] != 0 } >= 8
            total++; if (plein == (lo[y][x] != '.')) pareil++
        }
        if (pareil < total * 0.88) finOk = false     // 92 à 99 % ; décalé d'un seul gros pixel : 77 à 86 %
    }
    verifier(finOk, "les ${Guide.TYPES.size * combos.size} images fines suivent l'œuf actuel (même silhouette, même animation)")
    verifier(Oeufs.fin("glace", 1, "remue", 1)!!.px.toList() != Oeufs.fin("glace", 1, "remue", 3)!!.px.toList() &&
        Oeufs.fin("glace", 1, "brille", 0)!!.px.toList() != Oeufs.fin("glace", 1)!!.px.toList() &&
        Oeufs.fin("glace", 2, "craque", 0)!!.px.toList() != Oeufs.fin("glace", 2, "craque", 1)!!.px.toList(),
        "l'œuf fin remue, brille, craque")
    val couleursFin = Oeufs.fin("machine", 0)!!.px.toSet().size
    verifier(couleursFin in 12..34, "palette limitée ($couleursFin couleurs), fichier léger (${File(assets, "oeufs_fins.json").length() / 1024} Ko)")

    println("7. Anciennes parties : rien ne se ferme")
    Parties.nouvelle(app)
    val v = PartieI(app)
    v.jeu.nom = "Vieux"
    verifier(Intro.fonctions().all { Intro.ouvert(v.jeu, it.id) } && Intro.eclos(v.jeu) && !Intro.enCours(v.jeu),
        "une partie sans « debloc » : tout est ouvert, pas d'œuf qui attend")
    Guide.g(v.jeu).put("type_c", "roche")
    verifier(Oeufs.typeDe(v.jeu) == "roche" && Sprites.lignes(v.jeu, 0) == Oeufs.petit("roche") && Guide.g(v.jeu).optString("type_c") == "roche",
        "une ancienne partie garde le type de son compagnon ; son œuf (écran principal, widget) est l'œuf de ce type")
    verifier(v.jeu.especeCompagnon == null && Sprites.lignes(v.jeu, 1)[1] == "....bbbb...." && Regles.espece(1, null, v.jeu.especeCompagnon) == Langue.t("stade.1"),
        "une partie d'avant (sans espèce) garde sa créature d'origine")
    Histoire.h(v.jeu).getJSONArray("faits").put("t0")
    Intro.verifier(v.jeu)
    verifier(Intro.deb(v.jeu).getJSONArray("file").length() == 0 && Intro.aMontrer(v.jeu) == null, "et jamais d'écran « nouveau » pour un ancien joueur")
    verifier(v.commandes.executer("carte")?.texte?.contains("🔒") == false, "« carte » répond")
    j.sauver()
    val relu = Jeu(app)
    verifier(Intro.ouvert(relu, "biomes") || relu.nom != "Pixou", "la sauvegarde garde le déblocage")

    println("8. « debloquer tout » (parents, tests)")
    Parties.nouvelle(app)
    val t = PartieI(app)
    t.jeu.nom = "Testeur"
    Intro.nouvellePartie(t.jeu)
    Intro.toutDebloquer(t.jeu)
    verifier(Intro.eclos(t.jeu) && t.jeu.niveau >= 2 && Intro.fonctions().all { Intro.ouvert(t.jeu, it.id) }, "l'œuf éclot, tout est ouvert")
    verifier(Intro.aMontrer(t.jeu) == "merci", "l'écran merci reste (il dit bonjour)")

    println("9. La carte grise les régions gardées (Guide.regionOuverte / Guide.peutAgrandir)")
    val x = Guide.TYPES.first { it !in Guide.typesEquipe(j) }
    File(j.terrain, "biome/$x/parcelle_1").mkdirs()
    File(j.terrain, "biome/feu").mkdirs()
    val m = Maison.m(j)
    m.put("visites", JSONArray(listOf("", "biome", "biome/$x", "biome/feu")))
    var ns = Maison.noeuds(j).associateBy { it.rel }
    verifier(ns["biome/$x"]?.garde == "fermee" && ns["biome/$x/parcelle_1"]?.garde == "fermee", "biome/$x : pas de bestiole $x → fermée")
    verifier(Guide.actuel(j).type == "feu" || ns["biome/feu"]?.garde == "visite", "biome/feu : une bestiole feu mais pas guide → visite")
    verifier(Carte.sol(ns.getValue("biome/$x")) == Carte.SOLS.getValue("brume"), "la région fermée est grise sur le dessin")
    verifier(Maison.carte(j).any { "🔒" in it && Guide.nomType(x) in it }, "la carte en texte dit 🔒 fermée")
    Guide.choisir(j, feu.nom)
    ns = Maison.noeuds(j).associateBy { it.rel }
    verifier(Guide.actuel(j).ind != null && ns["biome/feu"]?.garde == "", "le guide est feu : la région feu peut grandir")
    Guide.choisir(j, j.nom)

    println("9b. L'intro en images (Scenes.kt) : le camp endormi, le réveil, l'œuf « en téléchargement », l'éclosion")
    verifier(Scenes.disponible() && Scenes.image("monde") != null && Scenes.image("dort") != null, "les trois illustrations (assets/intro/*.jpg)")
    val campI = Scenes.image("camp")!!
    val dortI = Scenes.image("camp_dort")!!
    fun sat(px: IntArray) = px.indices.step(97).map { val c = px[it]; maxOf((c shr 16) and 255, (c shr 8) and 255, c and 255) - minOf((c shr 16) and 255, (c shr 8) and 255, c and 255) }.average()
    verifier(sat(dortI.px) < sat(campI.px) * 0.3, "le camp endormi : la même image désaturée et assombrie par le code")
    Parties.nouvelle(app)
    val s7 = PartieI(app).jeu.also { it.changerLangue("fr"); it.nom = "Noisette"; Intro.nouvellePartie(it) }
    verifier(Scenes.moment(s7, 5000L).phase == "dort", "avant la 1re commande : le camp dort")
    Intro.i(s7).put("faits", JSONArray(listOf("pwd"))).put("evt", JSONArray().put(1).put(1_000_000L)).put("eveil", 1_000_000L)
    val ph = listOf(200L, 2000L, 3300L, 3600L).map { Scenes.moment(s7, 1_000_000L + it).phase }
    verifier(ph == listOf("eveil", "eveil", "eveil", "telech"), "1re commande : le camp se réveille, puis l'œuf arrive ($ph)")
    val e1 = Scenes.eveil(0.3f)!!.px.copyOf()
    val e2 = Scenes.eveil(2.0f)!!.px.copyOf()
    verifier(sat(e1) < sat(e2) && sat(e2) <= sat(campI.px) * 1.05, "la couleur revient peu à peu derrière la lumière")
    verifier(Scenes.lumieres(1.0f).size >= 3, "des lumières remontent les câbles et l'arbre")
    val pc = listOf(3500L, 4000L, 5000L, 9000L).map { Math.round(Scenes.moment(s7, 1_000_000L + it).pct) }
    verifier(pc[0] < pc[1] && pc[1] < pc[2] && pc[2] == 37 && pc[3] == 37, "réception : 0 → 37 % après la 1re commande ($pc)")
    val gT = IntArray(10 * 20) { 0xFF010101.toInt() }
    val o = IntArray(gT.size)
    Scenes.telecharge(gT, 10, 20, 50f, 3, 1, o)
    verifier((0 until 80).all { o[it] == gT[it] } && (90 until 100).any { o[it] == Scenes.VERT || o[it] == Scenes.VERT_PALE } && (120 until 200).all { (o[it] ushr 24) < 255 },
        "l'œuf à 50 % : le haut reçu, la ligne en cours en vert, le bas en contour")
    verifier(Oeufs.aDesFins() && Scenes.oeuf(Oeufs.typeDe(s7), Scenes.moment(s7, 1_005_000L))?.second == 4, "l'écran de l'œuf utilise l'œuf fin (104×104)")
    Intro.i(s7).put("faits", JSONArray(listOf("pwd", "ls", "echo", "whoami"))).put("etat", "fini").put("evt", JSONArray().put(4).put(2_000_000L))
    val fins = listOf(300L, 900L, 1500L, 3000L, 5000L).map { Scenes.moment(s7, 2_000_000L + it).phase }
    verifier(fins == listOf("telech", "eclat", "eclot", "fondu", "ne"), "4e commande : 100 %, l'éclat, l'œuf se fêle et s'ouvre, le fondu digital, né ($fins)")
    val ks = (0 until 14).map { Scenes.moment(s7, 2_000_000L + 1250L + it * 100L).k }
    verifier(ks == ks.sorted() && ks.first() == 0 && ks.last() == Scenes.ECLOT.size - 1, "l'éclosion image par image : fêlures, tremblement, coquille ouverte")
    val bb = Carte.Pix(20, 20, IntArray(400) { 0xFF884422.toInt() })
    val vus = listOf(0.1f, 0.4f, 0.7f, 1f).map { f -> Scenes.fondu(bb, f, 0).px.count { (it ushr 24) == 255 } }
    verifier(vus[0] < vus[1] && vus[1] < vus[2] && vus[2] <= vus[3] && vus[3] == 400, "le bébé apparaît pixel par pixel ($vus)")
    verifier(Scenes.fondu(bb, 0.4f, 0).px.any { (it ushr 24) == 255 && ((it shr 8) and 255) > 200 }, "les pixels qui arrivent brillent en vert « matrix »")
    val nait = Langue.t("intro.merci.titre", "nom" to s7.nom)
    verifier(Intro.etape(s7, Scenes.moment(s7, 2_003_000L)).second != nait && Intro.etape(s7, Scenes.moment(s7, 2_005_000L)).second == nait,
        "« ${s7.nom} est né ! » arrive après l'apparition du bébé")
    verifier(Intro.prochaineImage(s7, "merci", 2_000_500L) != null && Intro.prochaineImage(s7, "merci", 2_060_000L) == null, "l'écran bouge pendant l'animation, puis s'arrête")

    println("10. Les 14 langues")
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val textes = mutableListOf(Intro.texteListe(j), Intro.titreListe(j), Intro.astuce(j), Langue.t("intro.ou.tel"),
            Langue.t("intro.nom.tel"), Langue.t("intro.suivant"), Langue.t("intro.passer"), Langue.t("intro.ok.tel"),
            Intro.bloque(t.jeu.also { Intro.deb(it).put("mode", "progressif").put("ouverts", JSONArray()) }, "carte") ?: "")
        for (n in 1..3) textes += listOf(Langue.t("intro.e.titre.$n"), Langue.t("intro.e.texte.$n"))
        for (k in listOf("e.texte.oeuf", "camp.dort", "eveil", "nourris")) textes += Langue.t("intro.$k")
        textes += Langue.t("intro.recoit", "pct" to 37) + Langue.t("intro.eclot", "n" to 4, "total" to 4)
        for (ty in Oeufs.types()) Intro.titreType(ty).let { (a, b) -> verifier(a.isNotEmpty() && b.isNotEmpty() && a != b, "$code : titre « $a »".take(60)) }
        for (c in listOf("merci", "merci2") + ids.drop(1)) Intro.contenu(j, c, "/x").let { textes += it.first; textes += it.second }
        val bruts = textes.flatMap { cles(fr, it) }
        verifier(bruts.isEmpty() && textes.none { s -> s.lines().any { it.count { c -> c == '`' } % 2 == 1 } },
            "$code : intro, liste, merci et 11 écrans traduits" + if (bruts.isNotEmpty()) " ($bruts)" else "")
        // tout tient dans la largeur d'un téléphone (aucune ligne dessinée ne déborde)
        val r = listOf(apercu(null, null, j) { Intro.dessinerEcran(it, 3, 3, 360f) }, apercu(null, null, j) { Intro.dessinerOeuf(it, j, 360f) },
            apercu(null, null, j) { Intro.dessinerCarte(it, j, "merci", 360f) }, apercu(null, null, j) { Intro.dessinerCarte(it, j, "merci2", 360f) })
        verifier(r.all { it.h in 150f..1100f }, "$code : écrans dessinés (${r.map { it.h.toInt() }} dp de haut)")
    }
    Langue.definir("fr")

    if (sortie != null) {
        println("11. Aperçus (Peintre → PNG) : $sortie")
        Parties.nouvelle(app)
        val d = PartieI(app)
        d.jeu.changerLangue("fr")
        d.jeu.nom = "Pixou"
        Intro.nouvellePartie(d.jeu)
        for (n in 1..3) apercu(sortie, "tel_1_intro_$n", d.jeu) { Intro.dessinerEcran(it, n, 3, 360f) }
        apercu(sortie, "tel_2_oeuf_liste", d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f) }
        run {                                    // le déroulé en images, instant par instant (étapes 3 à 5)
            val q = PartieI(app).jeu.also { it.changerLangue("fr"); it.nom = "Noisette"; Intro.nouvellePartie(it); Oeufs.choisir(it, "plante"); it.extra.put("espece_compagnon", "glandouille") }
            val T = 3_000_000L
            apercu(sortie, "scene_3_camp_dort", q) { Intro.dessinerOeuf(it, q, 360f, null, T) }
            Intro.i(q).put("faits", JSONArray(listOf("pwd"))).put("evt", JSONArray().put(1).put(T)).put("eveil", T)
            for (ms in listOf(400L, 1100L, 1800L, 2600L)) apercu(sortie, "scene_3_reveil_%04d".format(ms), q) { Intro.dessinerOeuf(it, q, 360f, null, T + ms) }
            for (ms in listOf(4200L, 6000L)) apercu(sortie, "scene_4_reception_%04d".format(ms), q) { Intro.dessinerOeuf(it, q, 360f, null, T + ms) }
            Intro.i(q).put("faits", JSONArray(listOf("pwd", "ls", "echo"))).put("evt", JSONArray().put(3).put(T + 20_000))
            apercu(sortie, "scene_4_reception_87", q) { Intro.dessinerOeuf(it, q, 360f, null, T + 25_000) }
            Intro.i(q).put("faits", JSONArray(listOf("pwd", "ls", "echo", "whoami"))).put("etat", "fini").put("evt", JSONArray().put(4).put(T + 30_000))
            q.xp = 10
            for (ms in listOf(300L, 900L, 1500L, 1900L, 2250L, 2700L, 3100L, 3500L, 3900L, 6000L))
                apercu(sortie, "scene_5_eclosion_%04d".format(ms), q) { Intro.dessinerCarte(it, q, "merci", 360f, "/home/lea", T + 30_000 + ms) }
            apercu(sortie, "scene_5_ici", q) { Intro.dessinerCarte(it, q, "merci2", 360f, "/home/lea", T + 40_000) }
            Intro.hauteurMax = 430f
            apercu(sortie, "scene_4_petit_ecran", q.also { Intro.i(it).put("etat", "oeuf").put("faits", JSONArray(listOf("pwd"))) }) { Intro.dessinerOeuf(it, q, 360f, null, T + 6000) }
            Intro.hauteurMax = 0f
        }
        for ((k, c) in listOf("ls", "pwd", "whoami").withIndex()) {
            val avant = Intro.faits(d.jeu).size
            d.tape(c)
            val n = Intro.faits(d.jeu).size
            apercu(sortie, "tel_3_fele_${k + 1}", d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f) }
            for ((i, f) in Intro.reaction(n).withIndex())
                apercu(sortie, "anim_oeuf_${n}_%02d".format(i), d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f, Intro.pixOeuf(f.first, f.second, f.third)) }
            verifier(n == avant + 1, "$c : fêlure ${n}")
        }
        val reac = Intro.reaction(4)
        val bebe = Sprites.bitmap(d.jeu.also { it.xp = 10 }, 1).let { b ->
            val px = IntArray(b.width * b.height); b.getPixels(px, 0, b.width, 0, 0, b.width, b.height); Carte.Pix(b.width, b.height, px)
        }
        d.jeu.xp = 9
        for ((i, f) in reac.withIndex())
            apercu(sortie, "anim_eclosion_%02d".format(i), d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f, Intro.pixOeuf(f.first, f.second, f.third) ?: bebe) }
        d.tape("echo bonjour")
        apercu(sortie, "tel_4_eclosion", d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f, bebe) }
        apercu(sortie, "tel_5_merci", d.jeu) { Intro.dessinerCarte(it, d.jeu, "merci", 360f, d.jeu.home.path) }
        apercu(sortie, "tel_6_ici", d.jeu) { Intro.dessinerCarte(it, d.jeu, "merci2", 360f, d.jeu.home.path) }
        apercu(sortie, "tel_7_nouveau_envies", d.jeu) { Intro.dessinerCarte(it, d.jeu, "envies", 360f) }
        apercu(sortie, "tel_7_nouveau_equipe", d.jeu) { Intro.dessinerCarte(it, d.jeu, "equipe", 360f) }
        Langue.definir("ja")
        apercu(sortie, "tel_8_ja_intro_3", d.jeu) { Intro.dessinerEcran(it, 3, 3, 360f) }
        Langue.definir("fr")
        verifier(File(sortie, "tel_5_merci.png").isFile, "aperçus écrits")
    }

    println("\n$okI vérifications réussies, $koI échouée(s)")
    if (koI > 0) System.exit(1)
}

/** Le texte sans les ` (comme à l'écran). */
fun Vert0(s: String) = s.replace("`", "")
