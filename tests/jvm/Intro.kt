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
import fr.terminagotchi.Parties
import fr.terminagotchi.Peintre
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

    println("6. Les images de l'œuf : les mêmes qu'au PC (pc/tg/intro.py)")
    val combos = mutableListOf<Triple<Int, String, Int>>()
    for (n in 1..4) combos.addAll(Intro.reaction(n))
    for (f in 0..3) combos.add(Triple(f, "", 0))
    val py = ProcessBuilder("python3", "-c", "import json,sys;sys.path.insert(0,'${File(depot, "pc").path}');from tg import intro;" +
        "print(json.dumps([intro.image_oeuf(f,n,k) for f,n,k in json.loads(sys.argv[1])]))",
        JSONArray(combos.map { JSONArray().put(it.first).put(it.second).put(it.third) }).toString())
        .redirectErrorStream(true).start()
    val pyOut = py.inputStream.readBytes().toString(Charsets.UTF_8).trim()
    py.waitFor()
    val attendu = JSONArray(combos.map { c -> Intro.imageOeuf(c.first, c.second, c.third)?.let { JSONArray(it) } ?: JSONObject.NULL })
    verifier(try { JSONArray(pyOut).toString() == attendu.toString() } catch (e: Exception) { false },
        "${combos.size} images de l'œuf identiques sur PC et Android")
    val fel = (0..3).map { f -> Intro.imageOeuf(f)!!.sumOf { r -> r.count { it == 'f' } } }
    verifier(fel[0] == 0 && fel[0] < fel[1] && fel[1] < fel[2] && fel[2] < fel[3], "3 stades de fêlure : $fel")
    verifier(Intro.imageOeuf(3, "eclot", 7) == null, "fin de l'éclosion : la créature prend la place")

    println("7. Anciennes parties : rien ne se ferme")
    Parties.nouvelle(app)
    val v = PartieI(app)
    v.jeu.nom = "Vieux"
    verifier(Intro.fonctions().all { Intro.ouvert(v.jeu, it.id) } && Intro.eclos(v.jeu) && !Intro.enCours(v.jeu),
        "une partie sans « debloc » : tout est ouvert, pas d'œuf qui attend")
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

    println("10. Les 14 langues")
    for (code in Langue.LANGUES.keys) {
        Langue.definir(code)
        val textes = mutableListOf(Intro.texteListe(j), Intro.titreListe(j), Intro.astuce(j), Langue.t("intro.ou.tel"),
            Langue.t("intro.nom.tel"), Langue.t("intro.suivant"), Langue.t("intro.passer"), Langue.t("intro.ok.tel"),
            Intro.bloque(t.jeu.also { Intro.deb(it).put("mode", "progressif").put("ouverts", JSONArray()) }, "carte") ?: "")
        for (n in 1..4) textes += listOf(Langue.t("intro.e.titre.$n"), Langue.t("intro.e.texte.$n"))
        for (c in listOf("merci", "merci2") + ids.drop(1)) Intro.contenu(j, c, "/x").let { textes += it.first; textes += it.second }
        val bruts = textes.flatMap { cles(fr, it) }
        verifier(bruts.isEmpty() && textes.none { s -> s.lines().any { it.count { c -> c == '`' } % 2 == 1 } },
            "$code : intro, liste, merci et 11 écrans traduits" + if (bruts.isNotEmpty()) " ($bruts)" else "")
        // tout tient dans la largeur d'un téléphone (aucune ligne dessinée ne déborde)
        val r = listOf(apercu(null, null, j) { Intro.dessinerEcran(it, 3, 4, 360f) }, apercu(null, null, j) { Intro.dessinerOeuf(it, j, 360f) },
            apercu(null, null, j) { Intro.dessinerCarte(it, j, "merci", 360f) })
        verifier(r.all { it.h in 150f..900f }, "$code : écrans dessinés (${r.map { it.h.toInt() }} dp de haut)")
    }
    Langue.definir("fr")

    if (sortie != null) {
        println("11. Aperçus (Peintre → PNG) : $sortie")
        Parties.nouvelle(app)
        val d = PartieI(app)
        d.jeu.changerLangue("fr")
        d.jeu.nom = "Pixou"
        Intro.nouvellePartie(d.jeu)
        for (n in 1..4) apercu(sortie, "tel_1_intro_$n", d.jeu) { Intro.dessinerEcran(it, n, 4, 360f) }
        apercu(sortie, "tel_2_oeuf_liste", d.jeu) { Intro.dessinerOeuf(it, d.jeu, 360f) }
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
        apercu(sortie, "tel_8_ja_intro_3", d.jeu) { Intro.dessinerEcran(it, 3, 4, 360f) }
        Langue.definir("fr")
        verifier(File(sortie, "tel_5_merci.png").isFile, "aperçus écrits")
    }

    println("\n$okI vérifications réussies, $koI échouée(s)")
    if (koI > 0) System.exit(1)
}

/** Le texte sans les ` (comme à l'écran). */
fun Vert0(s: String) = s.replace("`", "")
