/*
 * Test JVM de l'apparence (Apparence.kt), comme pc/outils/test_apparence.py :
 *   1. les vecteurs communs (donnees/apparence/vecteurs.json) : la recoloration des 9 thèmes, les rectangles des
 *      dispositions du PC, les dispositions du téléphone, les onglets apparus — exactement comme en Python ;
 *   2. le contraste de chaque thème (texte, texte doux, blocs de la vue déployée) ;
 *   3. une vraie partie : le calendrier d'apparition (œuf, éclosion, t0, fin du chapitre 1, nid1, 1re capture, le
 *      tuyau du chapitre 5, la 1re recette), l'annonce, « Tout afficher », la migration d'une ancienne partie ;
 *   4. la disposition du téléphone (déplacer, tailler, cacher, remettre, ma disposition, origine), le dessin du mode
 *      rangement et des options (EspaceDessin), le thème indépendant de la disposition, l'étape du tuyau.
 *
 *   java -cp <imitations>:<appli.jar>:apparence.jar:kotlin-stdlib.jar ApparenceKt app/src/main/assets
 */
import fr.terminagotchi.Apparence
import fr.terminagotchi.EspaceDessin
import fr.terminagotchi.Explo
import fr.terminagotchi.Histoire
import fr.terminagotchi.Intro
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Poses
import fr.terminagotchi.Toile
import org.json.JSONArray
import org.json.JSONObject
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

fun verifA(c: Boolean, m: String, silencieux: Boolean = false) {
    if (c) okA++ else koA++
    if (!c || !silencieux) println((if (c) "  ✔ " else "  ✖ ") + m)
}

/** Une toile qui retient seulement les couleurs et les textes (pour vérifier le dessin sans écran). */
class ToileTrace : Toile {
    val couleurs = mutableListOf<Int>()
    val textes = mutableListOf<String>()
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { couleurs.add(c) }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { fond?.let { couleurs.add(it) } }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { couleurs.add(c) }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { couleurs.add(c) }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { couleurs.add(c) }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { couleurs.add(c) }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { textes.add(s); couleurs.add(c) }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.55f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { couleurs.add(c) }
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) {}
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { textes.add("photo:$nom") }
}

fun argb(a: JSONArray) = (a.getInt(3) shl 24) or (a.getInt(0) shl 16) or (a.getInt(1) shl 8) or a.getInt(2)

fun main(args: Array<String>) {
    val assets = File(args.getOrElse(0) { "app/src/main/assets" })
    val racine = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val app = AppareilA(File(System.getProperty("java.io.tmpdir")), assets)
    Langue.init(app)
    Langue.definir("fr")
    Intro.init(app)

    println("Les vecteurs communs (donnees/apparence/vecteurs.json)")
    val vec = JSONObject(File(racine, "donnees/apparence/vecteurs.json").readText())
    val coul = vec.getJSONObject("couleurs")
    var faux = 0
    for (cle in coul.keySet()) {
        val th = Apparence.Theme(cle)
        val l = coul.getJSONArray(cle)
        for (i in 0 until l.length()) {
            val p = l.getJSONArray(i)
            val obt = th.couleur(argb(p.getJSONArray(0)))
            if (obt != argb(p.getJSONArray(1))) { faux++; if (faux < 6) println("     $cle ${p.getJSONArray(0)} → ${Integer.toHexString(obt)} au lieu de ${p.getJSONArray(1)}") }
        }
    }
    verifA(faux == 0, "la recoloration des ${coul.length()} thèmes est identique au PC ($faux écart(s))")
    faux = 0
    val rects = vec.getJSONObject("rects")
    for (nom in rects.keySet()) {
        val pr = Apparence.preset(nom)
        val o = rects.getJSONObject(nom)
        for (k in o.keySet()) {
            val c = pr.getValue(k)
            val r = Apparence.rectDe(c[0], c[1], c[2], c[3])
            val att = o.getJSONArray(k)
            if ((0 until 4).any { Math.abs(r[it] - att.getDouble(it)) > 1e-9 }) faux++
        }
    }
    verifA(faux == 0, "les rectangles des dispositions du PC sont identiques ($faux écart(s))")
    val tel = vec.getJSONObject("telephone")
    verifA(tel.keySet().all { n -> Apparence.bandesPreset(n).map { listOf(it.id, it.taille) }.toString() ==
        (0 until tel.getJSONArray(n).length()).map { val x = tel.getJSONArray(n).getJSONArray(it); listOf(x.getString(0), x.getString(1)) }.toString() },
        "les dispositions du téléphone sont identiques")
    val ong = vec.getJSONArray("onglets")
    verifA((0 until ong.length()).all { i -> val o = ong.getJSONObject(i)
        Apparence.ongletsDe((0 until o.getJSONArray("vus").length()).map { o.getJSONArray("vus").getString(it) }.toSet(),
            (0 until o.getJSONArray("ordre").length()).map { o.getJSONArray("ordre").getString(it) }).toString() ==
            (0 until o.getJSONArray("onglets").length()).map { o.getJSONArray("onglets").getString(it) }.toString() },
        "les onglets apparus (et leur ordre) sont identiques")

    println("Le contraste de chaque thème")
    for (cle in Apparence.ordre()) {
        val th = Apparence.Theme(cle)
        for (f in listOf("panneau", "terminal", "panneau2")) {
            val F = th.r.getValue(f)
            verifA(Apparence.contraste(th.r.getValue("texte"), F) >= 4.5, "$cle : texte sur $f", true)
            verifA(Apparence.contraste(th.r.getValue("doux"), F) >= 3.0, "$cle : texte doux sur $f", true)
            for ((k, c) in th.acc) verifA(Apparence.contraste(c, F) >= 3.0, "$cle : bloc $k sur $f", true)
        }
        verifA(true, "$cle : contrastes vérifiés")
    }

    println("Une vraie partie : le calendrier d'apparition")
    val d = File(System.getProperty("java.io.tmpdir"), "tg_apparence_" + System.nanoTime()).apply { mkdirs() }
    val jeu = Jeu(AppareilA(d, assets))
    jeu.changerLangue("fr")
    jeu.nom = "Noisette"
    Intro.nouvellePartie(jeu)
    jeu.sauver()
    verifA(Apparence.visibles(jeu) == setOf("terminal", "direct"), "au tout début : l'œuf et l'invite (${Apparence.visibles(jeu)})")
    verifA(Apparence.onglets(jeu) == listOf("terminal"), "un seul onglet : Terminal")
    val h = Histoire.h(jeu)
    val etapes = listOf<Triple<String, () -> Unit, Set<String>>>(
        Triple("éclosion", { Intro.finir(jeu) }, setOf("ile")),
        Triple("leçon t0", { h.getJSONArray("faits").put("t0") }, setOf("explorateur", "envies")),
        Triple("fin du chapitre 1", { h.getJSONArray("ailes").put("reveil") }, setOf("carte")),
        Triple("leçon nid1", { h.getJSONArray("faits").put("nid1") }, setOf("deploie", "assiette")),
        Triple("1re créature dressée", { Explo.captures(jeu).put(JSONObject().put("espece", "Gouttelin").put("nom", "Plic")) }, setOf("equipe")),
        Triple("chapitre 5 (le tuyau)", { h.getJSONArray("faits").put("biblio1") }, setOf("tuyaux")),
        Triple("1re recette", { h.getJSONArray("faits").put("scripts0") }, setOf("cerveau")))
    for ((nom, f, att) in etapes) {
        val avant = Apparence.visibles(jeu)
        f()
        Intro.verifier(jeu)
        val apres = Apparence.visibles(jeu)
        verifA(apres - avant == att, "$nom : apparaissent $att (vu : ${apres - avant})")
        verifA(Apparence.prendreAnnonces(jeu).toSet() == att, "$nom : annoncés", true)
    }
    verifA(Apparence.onglets(jeu) == listOf("terminal", "carte", "cerveau", "equipe"), "complet : Terminal, Carte, Cerveau, Équipe")
    verifA((0 until h.getJSONArray("faits").length()).any { h.getJSONArray("faits").getString(it) == "biblio1" } && "tuyaux" in Apparence.visibles(jeu),
        "un panneau mérité le reste")

    println("« Tout afficher » et la migration")
    val jeu2 = Jeu(AppareilA(File(d, "b").apply { mkdirs() }, assets))
    jeu2.nom = "Classe"
    Intro.nouvellePartie(jeu2)
    val (q, rep) = Apparence.questionAdulte(java.util.Random(3))
    verifA(" × " in q && rep == q.split(" × ").let { (it[0].toInt() * it[1].toInt()).toString() }, "la question des grands : $q = $rep")
    Apparence.toutAfficher(jeu2, true)
    verifA(Apparence.visibles(jeu2).containsAll(Apparence.ids()), "Tout afficher : tout est là")
    verifA(!Intro.eclos(jeu2), "… sans changer la progression")
    Apparence.toutAfficher(jeu2, false)
    verifA(Apparence.visibles(jeu2) == setOf("terminal", "direct"), "réversible")
    val vieux = Jeu(AppareilA(File(d, "c").apply { mkdirs() }, assets))
    vieux.nom = "Ancien"
    vieux.extra.remove("debloc"); vieux.extra.remove("apparence")
    verifA(Apparence.cleTheme(vieux) == "sombre" && Apparence.nomDisposition(vieux) == "classique", "une ancienne partie : Sombre, Classique")
    verifA(Apparence.visibles(vieux).containsAll(Apparence.ids()) && Apparence.prendreAnnonces(vieux).isEmpty(),
        "une ancienne partie : tous ses panneaux, sans annonce")

    println("La disposition du téléphone")
    Apparence.tailler(jeu, "creature", "G")
    Apparence.deplacer(jeu, "deploie", 0)
    verifA(Apparence.bandes(jeu).map { it.id + it.taille } == listOf("deploieM", "creatureG"), "déplacer et tailler les bandes")
    Apparence.cacher(jeu, "creature", true)
    verifA(Apparence.bandes(jeu).map { it.id } == listOf("deploie") && Apparence.caches(jeu) == listOf("creature"), "cacher une bande")
    Apparence.enregistrerMienne(jeu)
    Apparence.choisirDisposition(jeu, "terminal_geant")
    verifA(Apparence.nomDisposition(jeu) == "terminal_geant" && Apparence.bandes(jeu).map { it.id } == listOf("deploie"), "Terminal géant")
    Apparence.choisirDisposition(jeu, "mienne")
    verifA(Apparence.caches(jeu) == listOf("creature"), "« Ma disposition » revient")
    Apparence.cacher(jeu, "creature", false)
    verifA(Apparence.bandes(jeu).any { it.id == "creature" }, "remettre une bande")
    Apparence.avancerOnglet(jeu, "equipe")
    verifA(Apparence.onglets(jeu) == listOf("terminal", "carte", "equipe", "cerveau"), "changer l'ordre des onglets")
    Apparence.origine(jeu)
    verifA(Apparence.bandes(jeu).map { it.id + it.taille } == listOf("creatureM", "deploieM"), "Disposition d'origine")
    Apparence.choisirTheme(jeu, "gameboy")
    Apparence.choisirDisposition(jeu, "creature_centre")
    verifA(Apparence.cleTheme(jeu) == "gameboy" && Apparence.nomDisposition(jeu) == "creature_centre", "thème et disposition indépendants")

    println("Le dessin (EspaceDessin)")
    val m = EspaceDessin.Modele()
    m.theme = Apparence.Theme("gameboy"); m.onglets = Apparence.onglets(jeu); m.bandes = Apparence.bandes(jeu)
    m.rangement = true; m.ordreOnglets = Apparence.ordreOnglets(jeu); m.caches = listOf("deploie")
    val tr = ToileTrace()
    val z = EspaceDessin.dessiner(tr, m, 1080f, 2000f, 2.6f).map { it.action }.toSet()
    verifA(z.containsAll(listOf("rg:tenir:creature", "rg:taille:creature:P", "rg:cacher:creature", "rg:remettre:deploie", "rg:fini",
        "rg:origine", "rg:mienne", "rg:dispo:terminal_geant")), "rangement : ≡, tailles P M G, ✕, bandes cachées, dispositions")
    verifA(tr.couleurs.none { it == EspaceDessin.FOND }, "le thème s'applique à tout le dessin")
    m.rangement = false; m.options = true
    val z2 = EspaceDessin.dessiner(ToileTrace(), m, 1080f, 2000f, 2.6f).map { it.action }.toSet()
    verifA(Apparence.ordre().all { "opt:theme:$it" in z2 } && "opt:tout" in z2 && "opt:ranger" in z2, "les options : 9 thèmes, Tout afficher, ranger")
    m.options = false; m.arrivees = mapOf("carte" to 0.5)
    val tr3 = ToileTrace()
    EspaceDessin.dessiner(tr3, m, 1080f, 2000f, 2.6f)
    verifA(tr3.textes.any { "nouvel onglet" in it }, "l'arrivée d'un onglet : « nouvel onglet »")

    println("Le premier tuyau (chapitre 5)")
    val kt = File(racine, "app/src/main/java/fr/terminagotchi/Histoire.kt").readText()
    verifA("n(\"biblio1\", 4, \"cat etagere_c/coin_poussiereux/livre_des_abysses.txt | grep Abyssor\"" in kt, "l'étape cat … | grep Abyssor")
    val rx = Regex("\\|\\s*(grep|select-string|sls|findstr)\\b.*abyssor", RegexOption.IGNORE_CASE)
    verifA(rx.containsMatchIn("cat etagere_c/coin_poussiereux/livre_des_abysses.txt | grep Abyssor") &&
        !rx.containsMatchIn("grep Abyssor livre.txt"), "il faut un vrai tuyau")
    for (code in listOf("fr", "en", "zh", "ar")) {
        Langue.definir(code)
        verifA(!Langue.t("hist.biblio1.4.dit").startsWith("hist.") && !Langue.t("app.pan.tuyaux.dit").startsWith("app."), "$code : textes", true)
    }
    Langue.definir("fr")
    println("$okA réussis, $koA échoués")
    if (koA > 0) System.exit(1)
}
