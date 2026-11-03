/*
 * Test JVM du réveil du Terminaworld (Reveil.kt, CarteEtat.kt, CarteDessin.kt), portage de pc/outils/test_reveil.py :
 *   1. les vecteurs communs donnees/reveil/vecteurs.json : EXACTEMENT les mêmes résultats qu'en Python ;
 *   2. une vraie partie : chapitres → biomes, une nouvelle à la fois, le lieu secret et l'habitant du Port ;
 *   3. le dessin de la carte (fiche, livre, carnet) sans erreur, « Y aller » écrit la commande.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Reveil.kt -d tmp.jar
 *   java -cp <imitations>:<appli.jar>:tmp.jar:kotlin-stdlib.jar ReveilKt app/src/main/assets
 */
import fr.terminagotchi.CarteDessin
import fr.terminagotchi.CarteEtat
import fr.terminagotchi.EspaceDessin
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Poses
import fr.terminagotchi.Quetes
import fr.terminagotchi.Reveil
import fr.terminagotchi.Toile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsRv(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilRv(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsRv(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileRv : Toile {
    var n = 0
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { n++ }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { n++ }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { n++ }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { n++ }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { n++ }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { n++ }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { n++ }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float = s.length * taille * 0.55f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { n++ }
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) { n++ }
    override fun clip(x: Float, y: Float, w: Float, h: Float) {}
    override fun declip() {}
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { n++ }
}

var okRv = 0
var koRv = 0
fun verifierRv(c: Boolean, m: String) {
    if (c) okRv++ else koRv++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

fun lstRv(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun main(args: Array<String>) {
    val assets = File(args.getOrElse(0) { "app/src/main/assets" })
    val racine = assets.canonicalFile.parentFile.parentFile.parentFile.parentFile
    val app = AppareilRv(File(System.getProperty("java.io.tmpdir")), assets)
    Langue.init(app)
    Langue.definir("fr")
    Reveil.init(app)

    println("1. Les vecteurs communs (donnees/reveil/vecteurs.json)")
    val v = JSONObject(File(racine, "donnees/reveil/vecteurs.json").readText())
    var faux = 0
    val cal = v.getJSONArray("calcul")
    for (i in 0 until cal.length()) {
        val c = cal.getJSONObject(i); val e0 = c.getJSONObject("entree")
        val e = Reveil.calcul(lstRv(e0.getJSONArray("ailes")), e0.optString("oeuf"), lstRv(e0.getJSONArray("ouverts")),
            lstRv(e0.getJSONArray("allumes")), lstRv(e0.getJSONArray("etoiles")))
        val lx = c.getJSONObject("lieux")
        val lieuxOk = lx.keys().asSequence().all { k -> Math.abs((e.lieux[k] ?: -1.0) - lx.getDouble(k)) < 1e-9 } && lx.length() == e.lieux.size
        if (e.biomes != lstRv(c.getJSONArray("biomes")) || !lieuxOk || e.etoiles != lstRv(c.getJSONArray("etoiles")) ||
            Reveil.signature(e) != c.getString("signature")) { faux++; println("     calcul $i : ${e.biomes} ${Reveil.signature(e)}") }
        val d = Reveil.depuisSignature(c.getString("signature"))
        if (d.biomes.toSet() != e.biomes.toSet() || Reveil.signature(d) != c.getString("signature")) { faux++; println("     signature $i") }
    }
    verifierRv(faux == 0, "le réveil (${cal.length()} cas) : biomes, lieux, ★, signature ($faux faux)")
    faux = 0
    val ch = v.getJSONArray("chemin")
    for (i in 0 until ch.length()) {
        val c = ch.getJSONArray(i)
        val r = Reveil.cheminCd(if (c.isNull(0)) null else c.getString(0), c.getString(1))
        val att = if (c.isNull(2)) null else c.getString(2)
        if (r != att) { faux++; println("     chemin ${c} → $r") }
    }
    verifierRv(faux == 0, "« Y aller » : la même commande cd ($faux faux)")
    val mo = v.getJSONObject("moment"); val sa = v.getJSONObject("saison")
    verifierRv((0..23).all { Reveil.moment(it) == mo.getString("$it") }, "le moment de la journée, heure par heure")
    verifierRv((1..12).all { Reveil.saison(it) == sa.getString("$it") }, "la saison, mois par mois")
    val fn = v.getJSONObject("fnv")
    verifierRv(fn.keys().asSequence().all { Reveil.fnv(it) == fn.getLong(it) }, "le hasard FNV-1a (UTF-8)")
    faux = 0
    val ev = v.getJSONArray("evenement")
    for (i in 0 until ev.length()) {
        val c = ev.getJSONArray(i)
        val r = Reveil.evenementDuJour(c.getString(0), c.getString(1), lstRv(c.getJSONArray(2)), lstRv(c.getJSONArray(3)))
        if (r != (if (c.isNull(4)) null else c.getString(4))) { faux++; println("     événement $c → $r") }
    }
    verifierRv(faux == 0, "l'événement rare du jour ($faux faux)")
    faux = 0
    val me = v.getJSONArray("meteo")
    for (i in 0 until me.length()) {
        val c = me.getJSONObject(i)
        val cmds = c.getJSONArray("cmds").let { a -> (0 until a.length()).map { a.getJSONArray(it).getString(0) to a.getJSONArray(it).getDouble(1) } }
        val av = c.optJSONArray("avant")?.let { it.getString(0) to it.getDouble(1) }
        val r = Reveil.meteo(cmds, c.getDouble("t"), av)
        val s = c.getJSONArray("sortie")
        if (r.first != s.getString(0) || Math.abs(r.second - s.getDouble(1)) > 1e-9) { faux++; println("     météo $i → $r") }
    }
    verifierRv(faux == 0, "la météo de la carte ($faux faux)")
    faux = 0
    val qv = v.getJSONArray("quetes")
    val qk = Reveil.quetes().associateBy { it.id }
    for (i in 0 until qv.length()) {
        val q = qv.getJSONObject(i); val k = qk[q.getString("id")]
        if (k == null || k.piece != q.getString("piece") || k.sorte != q.getString("sorte") || k.fichier != q.getString("fichier") ||
            k.xp != q.getInt("xp") || k.apres != (if (q.isNull("apres")) null else q.optString("apres")) ||
            k.but.map { it[0].toString() } != lstRv(q.getJSONArray("buts"))) { faux++; println("     quête ${q.getString("id")}") }
    }
    verifierRv(faux == 0 && qk.size == qv.length(), "les ${qv.length()} quêtes du monde ($faux faux)")
    verifierRv(Quetes.QUETES.count { it.id.startsWith("m") && it.id.length == 3 } >= qv.length(), "elles rejoignent le journal des quêtes")

    println("2. Une vraie partie")
    val d = File(System.getProperty("java.io.tmpdir"), "tg_reveil_" + System.nanoTime()).apply { mkdirs() }
    val jeu = Jeu(AppareilRv(d, assets))
    jeu.changerLangue("fr")
    jeu.nom = "Noisette"
    jeu.extra.put("oeuf_type", "feu")
    val h = Histoire.h(jeu)
    Reveil.tick(jeu)
    verifierRv(Reveil.r(jeu).has("dit"), "une nouvelle partie : rien à dire, tout dort")
    h.getJSONArray("ailes").put("reveil")
    Reveil.tick(jeu)
    verifierRv(Reveil.r(jeu).getJSONObject("dit").getJSONArray("biomes").let { lstRv(it) } == listOf("racine"), "chapitre 1 fini : la Racine")
    h.getJSONArray("ailes").put("nid")
    Reveil.tick(jeu)
    val e = Reveil.etat(jeu)
    verifierRv(e.biomes.size >= 1 && e.biomes[0] == "racine", "chapitre 2 : ${e.biomes}")
    val avant = lstRv(Reveil.r(jeu).getJSONObject("dit").getJSONArray("biomes"))
    val l = h.getJSONArray("ailes"); l.remove(l.length() - 1)
    Reveil.tick(jeu)
    verifierRv(lstRv(Reveil.r(jeu).getJSONObject("dit").getJSONArray("biomes")) == avant, "jamais de retour en arrière")
    h.getJSONArray("ailes").put("nid")

    println("3. La carte du téléphone")
    val c = CarteEtat(jeu)
    var ecrit: String? = null
    c.ecrire = { ecrit = it }
    c.rafraichir(14, 7)
    verifierRv(c.m.photo.startsWith("reveil:") && c.m.lieux.size == Reveil.lieux().size, "le modèle : la photo mélangée, ${c.m.lieux.size} lieux")
    for (t in 0 until 200) c.tick(t * 0.1, true)
    val tl = ToileRv()
    var erreurs = 0
    for (a in listOf("rv:passer", "rv:lieu:carrefour", "rv:plus", "rv:livre", "rv:livre:1", "rv:carnet", "rv:fermer", "rv:zoom+", "rv:zoom-")) {
        c.toucher(a)
        try { CarteDessin.dessiner(tl, mutableListOf(), c.m, 0f, 0f, 400f, 600f, 1f) } catch (x: Exception) { erreurs++; println("     $a : $x") }
    }
    verifierRv(erreurs == 0 && tl.n > 100, "fiche, livre, carnet, zoom : dessinés sans erreur (${tl.n} traits)")
    val ouvert = c.m.lieux.firstOrNull { it.cmd != null }
    if (ouvert != null) {
        c.toucher("rv:aller:" + ouvert.id)
        verifierRv(ecrit == ouvert.cmd, "« Y aller » écrit la commande sans la lancer ($ecrit)")
    }
    c.glisser(50f, 20f, 400f)
    verifierRv(c.m.cx in 0f..1f && c.m.cy in 0f..1f, "un doigt fait glisser la carte")
    // l'image mélangée (sans Android) : vivant ≠ endormi
    val n = 8 * 6
    val viv = IntArray(n) { 0xFF00FF00.toInt() }; val dor = IntArray(n) { 0xFF404040.toInt() }
    val masques = Reveil.nomsMasques().associateWith { nom -> ByteArray(n) { if (nom == "b_racine") 255.toByte() else 0 } }
    val tout = Reveil.melanger(viv, dor, 8, 6, masques, 8, 6, Reveil.calcul(listOf("reveil"), "feu", emptyList(), emptyList(), emptyList()), null, null)
    val rien = Reveil.melanger(viv, dor, 8, 6, masques, 8, 6, Reveil.calcul(emptyList(), "feu", emptyList(), emptyList(), emptyList()), null, null)
    verifierRv(tout[0] == viv[0] && rien[0] == dor[0], "la carte mélangée : la Racine réveillée prend les couleurs du vivant")
    d.deleteRecursively()

    println("${if (koRv == 0) "✅" else "❌"} Réveil : $okRv réussis, $koRv échoués")
    if (koRv > 0) System.exit(1)
}
