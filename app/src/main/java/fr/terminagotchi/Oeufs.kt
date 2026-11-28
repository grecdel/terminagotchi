package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Les œufs à type (portage de pc/tg/oeufs.py, mêmes règles, mêmes données) : 9 types de biome × 3 états (intact,
 * fissuré, éclosion). Données : assets/oeufs.json (copie exacte de donnees/oeufs/oeufs.json, fabriqué par
 * donnees/bestiaire2/generer_oeufs.py depuis les dessins donnees/oeufs/oeuf_<type>_<etat>.png).
 * Nouvelle partie (Intro.nouvellePartie) : l'œuf reçoit un type au hasard (extra « oeuf_type ») et le compagnon qui en
 * sort le MÊME (guide : type_c), et une ESPÈCE de départ de ce type (extra « espece_compagnon », liste fixe de
 * assets/depart.json, copie exacte de donnees/oeufs/depart.json) : le bébé qui sort de l'œuf, puis le compagnon du jeu
 * (Sprites.kt). Une partie d'avant (sans « espece_compagnon ») garde sa créature d'origine. Une ancienne partie garde le type de son compagnon ; son œuf est celui de ce type.
 * image() : l'œuf de l'intro, même calcul que oeufs.image (le test tests/jvm/Intro.kt compare les deux).
 */
object Oeufs {
    var chargeur: (() -> String?)? = null
    var chargeurDepart: (() -> String?)? = null
    var chargeurFin: (() -> String?)? = null
    @Volatile private var donnees: JSONObject? = null
    @Volatile private var departs: Map<String, List<String>>? = null

    fun init(ctx: android.content.Context) {
        val app = ctx.applicationContext ?: ctx
        if (chargeurDepart == null)
            chargeurDepart = { try { app.assets.open("depart.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
        if (chargeurFin == null)
            chargeurFin = { try { app.assets.open("oeufs_fins.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
        if (chargeur != null) return
        chargeur = { try { app.assets.open("oeufs.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    /** Type → ids des espèces de départ (depart.json, le même fichier sur PC). */
    fun departs(): Map<String, List<String>> = departs ?: run {
        val o = try { JSONObject(chargeurDepart?.invoke() ?: "{}").optJSONObject("depart") } catch (e: Exception) { null } ?: JSONObject()
        val m = o.keys().asSequence().associateWith { chaines(o.optJSONArray(it)) }
        if (m.isNotEmpty()) departs = m
        m
    }

    /** Une espèce de départ du type ty (son id), tirée au hasard dans la liste fixe (null : pas de liste). */
    fun especeDepart(ty: String, rnd: kotlin.random.Random = kotlin.random.Random): String? =
        (departs()[ty]?.ifEmpty { null } ?: departs().values.flatten().ifEmpty { null })?.random(rnd)

    fun d(): JSONObject = donnees ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { if (it.has("types")) donnees = it }

    private fun typesJ(): JSONObject = d().optJSONObject("types") ?: JSONObject()
    fun types(): List<String> = typesJ().let { j -> Guide.TYPES.filter { j.has(it) } }

    private fun chaines(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

    /** Une nouvelle partie : le type de l'œuf, le même pour le compagnon qui en sortira, et son espèce. */
    fun choisir(jeu: Jeu, ty: String? = null): String {
        val ts = types().ifEmpty { Guide.TYPES }
        val x = if (ty != null && ty in ts) ty else ts.random()
        jeu.extra.put("oeuf_type", x)
        especeDepart(x)?.let { jeu.extra.put("espece_compagnon", it) }
        Guide.g(jeu).put("type_c", x)
        return x
    }

    /** Le type de l'œuf d'une partie : celui du compagnon s'il en a un (anciennes parties), sinon celui tiré. */
    fun typeDe(jeu: Jeu): String {
        val ts = types()
        val c = jeu.extra.optJSONObject("guide")?.optString("type_c")
        if (c != null && c in ts) return c
        val o = jeu.extra.optString("oeuf_type")
        if (o in ts) return o
        return Guide.typeCompagnonInitial(jeu.nom, jeu.forme).takeIf { it in ts } ?: ts.firstOrNull() ?: "feu"
    }

    fun taille(nom: String = "grand"): Pair<Int, Int> =
        d().optJSONObject("tailles")?.optJSONArray(nom)?.let { it.getInt(0) to it.getInt(1) } ?: (26 to 26)

    private const val CHIFFRES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    private val palCache = HashMap<String, Map<Char, Int>>()

    private fun couleur(h: String): Int = (0xFF000000.toInt()) or h.removePrefix("#").toInt(16)

    /** Caractère → couleur ARGB : les couleurs du dessin, puis les effets (lueur du type, éclair blanc). */
    fun palette(ty: String): Map<Char, Int> = palCache.getOrPut(ty) {
        val x = typesJ().optJSONObject(ty) ?: return@getOrPut emptyMap()
        val m = HashMap<Char, Int>()
        val p = x.optJSONArray("palette") ?: JSONArray()
        for (k in 0 until p.length()) m[CHIFFRES[k]] = couleur(p.getString(k))
        val l = couleur(x.optString("lueur", "#ffd75f"))
        for (c in "fhy") m[c] = l
        d().optJSONObject("effets")?.let { e -> for (k in e.keys()) m[k[0]] = couleur(e.getString(k)) }
        m
    }

    /** L'œuf de l'écran principal, du widget, de la notification (cadre 18×16) : intact, puis fissuré. */
    fun petit(ty: String, fele: Int = 0): List<String> =
        chaines(typesJ().optJSONObject(ty)?.optJSONObject("petit")?.optJSONArray(if (fele >= 2) "fissure" else "intact"))

    /** Une image de l'œuf de l'intro (lignes de caractères). Même calcul que oeufs.image (PC). */
    fun image(ty0: String, fele: Int, nom: String = "", k: Int = 0): List<String>? {
        val ty = if (typesJ().has(ty0)) ty0 else types().firstOrNull() ?: return null
        val x = typesJ().getJSONObject(ty)
        val (W, H) = taille()
        if (nom == "eclot" && k >= 6) return null
        val etat = if (nom == "eclot" && k >= 3) "eclosion" else if (fele >= 2) "fissure" else "intact"
        val dx = when {
            nom == "remue" -> intArrayOf(0, -1, 0, 1)[k % 4]
            (nom == "craque" || nom == "eclot") && k < 2 -> intArrayOf(1, -1)[k % 2]
            else -> 0
        }
        val g = Array(H) { CharArray(W) { '.' } }
        for ((y, r) in chaines(x.getJSONObject("grand").optJSONArray(etat)).withIndex()) for ((xx, ch) in r.withIndex())
            if (ch != '.' && xx + dx in 0 until W) g[y][xx + dx] = ch
        val eclair = nom == "craque" && k % 2 == 0
        val feles = x.optJSONArray("feles") ?: JSONArray()
        val traits = when {
            etat == "eclosion" -> null
            fele == 1 || (fele == 2 && eclair) -> feles.optJSONArray(0)
            fele >= 3 -> feles.optJSONArray(1)
            else -> null
        }
        if (traits != null) for (q in 0 until traits.length()) {
            val pt = traits.getJSONArray(q)
            val xx = pt.getInt(0) + dx
            val y = pt.getInt(1)
            if (xx in 0 until W && g[y][xx] != '.') g[y][xx] = if (eclair) 'c' else 'f'
        }
        if (nom == "brille" && k % 2 == 0) {            // le contour luit
            val bord = mutableListOf<Pair<Int, Int>>()
            for (y in 0 until H) for (xx in 0 until W) if (g[y][xx] != '.' &&
                listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1).any { (a, b) -> xx + a !in 0 until W || y + b !in 0 until H || g[y + b][xx + a] == '.' })
                bord.add(xx to y)
            for ((xx, y) in bord) g[y][xx] = 'h'
        }
        if (nom == "brille" || (nom == "eclot" && k >= 3)) {   // des étincelles autour
            val pts = d().optJSONArray("etincelles")?.optJSONArray(k % 2) ?: JSONArray()
            for (q in 0 until pts.length()) {
                val pt = pts.getJSONArray(q)
                val px = pt.getInt(0); val py = pt.getInt(1)
                if (g[py][px] == '.') g[py][px] = 'y'
            }
        }
        return g.map { String(it) }
    }

    // ---------------------------------------------------------------- la version fine (écran de l'œuf d'Android)
    // assets/oeufs_fins.json (generer_oeufs.py) : les mêmes œufs, 4 fois plus détaillés (104×104, même cadrage que
    // « grand » : un pixel de image() = un carré de 4×4). Préparée pour l'écran de l'œuf ; pas encore affichée.
    @Volatile private var dFin: JSONObject? = null
    private val finCache = HashMap<String, IntArray>()

    fun dFin(): JSONObject = dFin ?: (try { JSONObject(chargeurFin?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { if (it.has("types")) dFin = it }

    fun aDesFins(): Boolean = dFin().has("types")

    /** Les indices de couleur d'un état (0 transparent, k+1 la couleur k de la palette fine), ou null. */
    private fun indicesFins(ty: String, etat: String): IntArray? = synchronized(finCache) {
        finCache["$ty/$etat"] ?: run {
            val x = dFin().optJSONObject("types")?.optJSONObject(ty) ?: return null
            val b = Bestiaire.gonfler(java.util.Base64.getDecoder().decode(x.optString(etat)))
            IntArray(b.size) { b[it].toInt() and 0xFF }.also { finCache["$ty/$etat"] = it }
        }
    }

    /**
     * Une image fine de l'œuf (ARGB, 104×104), même animation que image() : fele 0 à 3, nom remue / brille / craque /
     * eclot (null à la fin de l'éclosion : la créature prend la place). null si les données fines manquent.
     */
    fun fin(ty0: String, fele: Int, nom: String = "", k: Int = 0): Carte.Pix? {
        val types = dFin().optJSONObject("types") ?: return null
        val ty = if (types.has(ty0)) ty0 else types.keys().asSequence().firstOrNull() ?: return null
        val x = types.getJSONObject(ty)
        val t = dFin().optJSONArray("taille")
        val W = t?.optInt(0) ?: 104
        val H = t?.optInt(1) ?: 104
        val F = dFin().optInt("fin", 4)
        if (nom == "eclot" && k >= 6) return null
        val etat = if (nom == "eclot" && k >= 3) "eclosion" else if (fele >= 2) "fissure" else "intact"
        val src = indicesFins(ty, etat) ?: return null
        val pal = x.optJSONArray("palette") ?: JSONArray()
        val couleurs = IntArray(pal.length()) { couleur(pal.getString(it)) }
        val lueur = couleur(x.optString("lueur", "#ffd75f"))
        val blanc = couleur(dFin().optJSONObject("effets")?.optString("c") ?: "#ffffff")
        val dx = F * when {
            nom == "remue" -> intArrayOf(0, -1, 0, 1)[k % 4]
            (nom == "craque" || nom == "eclot") && k < 2 -> intArrayOf(1, -1)[k % 2]
            else -> 0
        }
        val px = IntArray(W * H)
        for (y in 0 until H) for (xx in 0 until W) {
            val v = src.getOrElse(y * W + xx) { 0 }
            if (v != 0 && xx + dx in 0 until W) px[y * W + xx + dx] = couleurs.getOrElse(v - 1) { 0 }
        }
        val eclair = nom == "craque" && k % 2 == 0
        val feles = x.optJSONArray("feles") ?: JSONArray()
        val traits = when {
            etat == "eclosion" -> null
            fele == 1 || (fele == 2 && eclair) -> feles.optJSONArray(0)
            fele >= 3 -> feles.optJSONArray(1)
            else -> null
        }
        if (traits != null) for (q in 0 until traits.length()) {
            val pt = traits.getJSONArray(q)
            val xx = pt.getInt(0) + dx
            val y = pt.getInt(1)
            if (xx in 0 until W && y in 0 until H && px[y * W + xx] != 0) px[y * W + xx] = if (eclair) blanc else lueur
        }
        if (nom == "brille" && k % 2 == 0) {            // le contour luit (2 pixels d'épaisseur)
            val bord = mutableListOf<Int>()
            for (y in 0 until H) for (xx in 0 until W) if (px[y * W + xx] != 0 &&
                (-2..2).any { a -> (-2..2).any { b -> Math.abs(a) + Math.abs(b) <= 2 &&
                    (xx + a !in 0 until W || y + b !in 0 until H || px[(y + b) * W + xx + a] == 0) } })
                bord.add(y * W + xx)
            for (i in bord) px[i] = lueur
        }
        if (nom == "brille" || (nom == "eclot" && k >= 3)) {   // des étincelles autour (de petites croix)
            val pts = dFin().optJSONArray("etincelles")?.optJSONArray(k % 2) ?: JSONArray()
            for (q in 0 until pts.length()) {
                val pt = pts.getJSONArray(q)
                val cx = pt.getInt(0); val cy = pt.getInt(1)
                for (d in -F / 2..F / 2) for ((a, b) in listOf(d to 0, 0 to d)) {
                    val xx = cx + a; val y = cy + b
                    if (xx in 0 until W && y in 0 until H && px[y * W + xx] == 0) px[y * W + xx] = if (d == 0) blanc else lueur
                }
            }
        }
        return Carte.Pix(W, H, px)
    }
}
