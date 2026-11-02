/*
 * Test JVM du monde des biomes et des effets des commandes (Monde.kt, Effets.kt), portage de pc/outils/test_monde.py
 * et pc/outils/test_effets.py :
 *   1. la génération commune : donnees/monde/vecteurs.json (hachage, hasard, décor, mondes entiers, créatures placées)
 *      donne EXACTEMENT le même monde qu'en Python et en JavaScript ;
 *   2. la spécification des effets : donnees/effets/vecteurs.json (48 commandes, PowerShell compris, rafales groupées,
 *      refus doux) donne exactement les mêmes événements et les mêmes explications ;
 *   3. la photo d'un vrai petit terrain (dossier temporaire) puis un vrai changement : l'effet suit ce qui a changé ;
 *   4. le dessin : chaque sorte de sol et chaque objet a un dessin, le monde se dessine sans erreur (ToileJava) ;
 *   5. le réglage « effets : tous / essentiels / aucun » et l'explication dite seulement 3 fois.
 *   java -cp <imitations>:<appli.jar>:monde.jar:kotlin-stdlib.jar MondeKt app/src/main/assets
 */
import fr.terminagotchi.Effets
import fr.terminagotchi.Monde
import fr.terminagotchi.MondeDessin
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ToileMonde : fr.terminagotchi.Toile {
    var n = 0
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { n++ }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { n++ }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { n++ }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { n++ }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { n++ }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { n++ }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { n++ }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.6f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { n++ }
    override fun cadre(c: fr.terminagotchi.Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) { n++ }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { n++ }
}

var echecs = 0
var oks = 0
fun ok(c: Boolean, m: String) { if (c) oks++ else { echecs++; println("  ✗ $m") } }

/** Une forme canonique (clés triées, nombres entiers sans « .0 ») pour comparer Python, Kotlin et JavaScript. */
fun canon(o: Any?): String = when (o) {
    null, JSONObject.NULL -> "null"
    is JSONObject -> o.keys().asSequence().toList().sorted().joinToString(",", "{", "}") { "\"$it\":" + canon(o.get(it)) }
    is JSONArray -> (0 until o.length()).joinToString(",", "[", "]") { canon(o.get(it)) }
    is Map<*, *> -> o.keys.map { it.toString() }.sorted().joinToString(",", "{", "}") { k -> "\"$k\":" + canon(o.entries.first { it.key.toString() == k }.value) }
    is List<*> -> o.joinToString(",", "[", "]") { canon(it) }
    is Pair<*, *> -> "[" + canon(o.first) + "," + canon(o.second) + "]"
    is IntArray -> o.joinToString(",", "[", "]")
    is Boolean -> o.toString()
    is Number -> { val d = o.toDouble(); if (d == Math.floor(d) && Math.abs(d) < 1e15) d.toLong().toString() else d.toString() }
    is String -> "\"" + o.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
    else -> "\"$o\""
}

fun resume(m: Monde.Carte): Map<String, Any?> {
    val hs = m.hex.values.sortedWith(compareBy({ it.q }, { it.r }))
    return mapOf(
        "parcelles" to m.parcelles.map { p ->
            listOf(p.id, p.m.toList(), p.volcan, p.poses.keys.sorted().associateWith { n -> val v = p.poses.getValue(n); listOf(listOf(v.oq, v.or_), v.k, v.bloque) })
        },
        "hex" to hs.map { h -> listOf(h.q, h.r, h.kind, h.h, h.v, h.region, h.mur, h.pilier, h.scen?.k, h.block) },
        "cordes" to m.cordes.map { listOf(it.first, it.second) })
}

fun terrainDe(o: JSONObject): LinkedHashMap<String, List<Monde.ParcelleT>> {
    val t = LinkedHashMap<String, List<Monde.ParcelleT>>()
    for (ty in Monde.TYPES) {
        val a = o.optJSONArray(ty) ?: continue
        t[ty] = (0 until a.length()).map { i -> val p = a.getJSONObject(i); val ob = p.getJSONArray("objets"); Monde.ParcelleT(p.getString("nom"), (0 until ob.length()).map { ob.getString(it) }) }
    }
    return t
}

fun main(args: Array<String>) {
    val depot = File(args.getOrElse(0) { "app/src/main/assets" }).absoluteFile.parentFile.parentFile.parentFile.parentFile
    println("1. La génération commune (Python = Kotlin = JavaScript)")
    val v = JSONObject(File(depot, "donnees/monde/vecteurs.json").readText())
    val hv = v.getJSONArray("hachage")
    for (i in 0 until hv.length()) { val x = hv.getJSONArray(i); ok(Monde.hachage(x.getString(0)) == x.getLong(1), "hachage ${x.getString(0)}") }
    val r = Monde.hasard(42); val ha = v.getJSONArray("hasard")
    for (i in 0 until ha.length()) { val y = r(); ok(y == ha.getDouble(i), "hasard $i : $y ≠ ${ha.getDouble(i)}") }
    val dv = v.getJSONArray("deco")
    for (i in 0 until dv.length()) {
        val x = dv.getJSONArray(i); val d = Monde.deco(x.getString(0), x.getString(1)); val att = x.getJSONArray(2)
        ok(d.first == att.getString(0) && (if (d.second) 1 else 0) == att.getInt(1), "deco ${x.getString(0)} : $d")
    }
    val mv = v.getJSONArray("mondes")
    for (i in 0 until mv.length()) {
        val x = mv.getJSONObject(i)
        val m = Monde.construire(terrainDe(x.getJSONObject("terrain")))
        val res = resume(m); val att = x.getJSONObject("monde")
        for (k in listOf("parcelles", "hex", "cordes")) {
            val a = canon(res[k]); val b = canon(att.get(k))
            if (a != b) { val ia = a.zip(b).indexOfFirst { it.first != it.second }; println("    $k : …${a.substring(maxOf(0, ia - 80), minOf(a.length, ia + 80))}\n    att …${b.substring(maxOf(0, ia - 80), minOf(b.length, ia + 80))}") }
            ok(a == b, "monde $i : $k")
        }
        val crs = listOf("plante", "feu", "feu", "feu", "eau", "glace", "ombre").mapIndexed { j, t -> "c$j" to t }
        val (maison, refuge) = Monde.placeCreatures(m, crs)
        ok(canon(maison) == canon(x.get("maison")) && canon(refuge) == canon(x.get("refuge")), "monde $i : créatures placées")
    }
    println("   ${mv.length()} mondes, $oks vérifications")

    println("2. Les effets des commandes (Python = Kotlin = JavaScript)")
    val ev = JSONArray(File(depot, "donnees/effets/vecteurs.json").readText())
    for (i in 0 until ev.length()) {
        val c = ev.getJSONObject(i)
        val res = Effets.evenements(c.getString("ligne"), Effets.photoDe(c.getJSONObject("avant")), Effets.photoDe(c.getJSONObject("apres")),
            if (c.isNull("code")) null else c.getInt("code"), c.optString("sortie"))
        val a = canon(res); val b = canon(c.getJSONArray("attendu"))
        if (a != b) println("    ${c.getString("ligne")}\n      $a\n      $b")
        ok(a == b, "effets : ${c.getString("ligne")}")
        ok(canon(res.map { Effets.cleDit(it) }) == canon(c.getJSONArray("dit")), "explication : ${c.getString("ligne")}")
    }
    println("   ${ev.length()} commandes")

    println("3. Une vraie photo avant / après")
    val tmp = File(System.getProperty("java.io.tmpdir"), "tg_monde_" + System.nanoTime()).also { it.mkdirs() }
    val ter = File(tmp, "terrain_terminagotchi"); File(ter, "biome/feu/parcelle_1").mkdirs()
    val av = Effets.photo(ter, File(ter, "biome"))
    File(ter, "biome/feu/parcelle_2").mkdirs()
    File(ter, "biome/feu/parcelle_1/geyser.pierre").writeText("pfff")
    val ap = Effets.photo(ter, File(ter, "biome"))
    val e1 = Effets.evenements("mkdir feu/parcelle_2 && touch feu/parcelle_1/geyser.pierre", av, ap, 0)
    ok(e1.any { it.getString("type") == "dossier+" && it.optBoolean("parcelle") }, "mkdir vu : $e1")
    ok(e1.any { it.getString("type") == "objet+" && it.getString("via") == "touch" }, "touch vu")
    val e2 = Effets.evenements("mkdir feu/parcelle_2", ap, ap, 1, "mkdir: cannot create directory 'feu/parcelle_2': File exists")
    ok(e2.size == 1 && e2[0].getString("type") == "refus" && e2[0].getString("raison") == "existe", "refus doux : $e2")
    ok(Effets.evenements("echo coucou", av, ap, 0).none { it.getString("type") == "objet+" && it.getString("cmd") == "echo" && it.getString("via") == "ecrire" }, "un effet ne ment jamais (echo ne crée rien)")
    val terr = Monde.lireTerrain(ter)
    ok(terr["feu"]?.map { it.nom } == listOf("parcelle_1", "parcelle_2"), "lireTerrain : ${terr["feu"]?.map { it.nom }}")
    ok(terr["feu"]!![0].objets == listOf("geyser.pierre"), "les objets de la parcelle")
    tmp.deleteRecursively()

    println("4. Le dessin")
    for (k in MondeDessin.SOLS) for (vv in 0 until 4) ok(MondeDessin.sprite(k, vv, 12, 0).argb.any { it != 0 }, "sol $k")
    for (k in MondeDessin.DECORS) ok(MondeDessin.decor(k).argb.any { it != 0 }, "décor $k")

    // les effets secondaires et ceux des mondes (2 novembre) : chaque sorte se dessine sans erreur, à chaque instant
    val tmp2 = File(System.getProperty("java.io.tmpdir"), "tg_monde2_" + System.nanoTime())
    val ter2 = File(tmp2, "terrain_terminagotchi")
    for (d in listOf("biome/plante/parcelle_1", "biome/plante/parcelle_2", "biome/feu/parcelle_1")) File(ter2, d).mkdirs()
    File(ter2, "biome/plante/parcelle_1/rose.fleur").writeText("rose")
    val vue = fr.terminagotchi.MondeVue()
    vue.relire(ter2, listOf(fr.terminagotchi.MondeVue.Info("g", "Glandouille", "plante", null, "bebe", true, "", "", null, false)), "biome")
    val nouveaux = setOf("caisse", "lien", "taille", "disque", "arbre", "memoire", "lanternes", "reveil", "journal", "etoile", "album",
        "branche", "fusion", "rembobine", "robot", "grimoire", "loupe", "filet", "sablier", "espion")
    val vus = HashSet<String>()
    for (i in 0 until ev.length()) {
        val att = ev.getJSONObject(i).getJSONArray("attendu")
        val lot = (0 until att.length()).map { att.getJSONObject(it) }.filter { it.getString("type") in nouveaux }
        if (lot.isEmpty()) continue
        lot.forEach { vus.add(it.getString("type")) }
        var dessine = 0
        try {
            vue.preparer(lot); vue.lancer(lot)
            for (pas in 0 until 12) {
                vue.tick(.18)
                val tl = ToileMonde(); vue.dessiner(tl, mutableListOf(), 0f, 0f, 900f, 600f, 1f); dessine += tl.n
            }
            ok(dessine > 0, "dessin : ${ev.getJSONObject(i).getString("ligne")}")
        } catch (x: Exception) { ok(false, "dessin : ${ev.getJSONObject(i).getString("ligne")} : $x") }
    }
    ok(vus == nouveaux, "toutes les sortes nouvelles sont dessinées (${nouveaux - vus})")
    tmp2.deleteRecursively()

    println("5. Réglage et explications")
    val evs = Effets.evenements("ps", av, av, 0)
    ok(Effets.filtrer(evs, "tous").size == 1 && Effets.filtrer(evs, "essentiels").isEmpty() && Effets.filtrer(evs, "aucun").isEmpty(), "réglage")
    val cpt = JSONObject()
    var dites = 0
    repeat(5) { val k = Effets.aDire(cpt, evs); if (k != null) { dites++; cpt.put(k, cpt.optInt(k) + 1) } }
    ok(dites == Effets.DITS_MAX, "l'explication n'est dite que ${Effets.DITS_MAX} fois ($dites)")

    println(if (echecs == 0) "✅ Monde et effets : $oks vérifications, tout est bon" else "❌ $echecs échec(s) sur ${oks + echecs}")
    if (echecs > 0) kotlin.system.exitProcess(1)
}
