package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * L'apparence (mêmes règles que pc/tg/apparence.py, mêmes données : assets/apparence.json, copie de
 * donnees/apparence.json ; vecteurs communs donnees/apparence/vecteurs.json, test tests/jvm/Apparence.kt) :
 *  - les thèmes : chaque couleur du thème sombre a un rôle (neutres → rampe du thème, 8 accents → l'accent du thème
 *    le plus proche en teinte, ombres inchangées) ; le dessin reste écrit en couleurs du thème sombre et passe par
 *    couleur() au moment de dessiner (EspaceVue, bulle) ; les sprites ne changent jamais ;
 *  - l'interface évolutive : les panneaux et onglets de l'espace apparaissent avec l'histoire (table « panneaux »),
 *    une animation d'arrivée et une phrase ; « Tout afficher » (pour les grands, après une petite question) ;
 *  - la disposition du téléphone : l'ordre des bandes (créature, vue déployée), leur taille P / M / G, l'ordre
 *    des onglets, les bandes cachées ; dispositions toutes prêtes et « ma disposition ». La grille du PC est aussi
 *    là (rectDe) pour vérifier que les deux côtés calculent les mêmes rectangles.
 * Sauvegarde : jeu.module("apparence") = {theme, theme_date, vus, annonces, tout, tel: {bandes, onglets, caches,
 * nom}, mienne}. Le thème suit le recensement (le plus récent gagne) ; la disposition reste propre à l'appareil.
 */
object Apparence {
    var chargeur: (() -> String?)? = null
    @Volatile private var donnees: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("apparence.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun d(): JSONObject = donnees ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { if (it.has("themes")) donnees = it }

    private fun chaines(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

    fun ordre(): List<String> = chaines(d().optJSONArray("ordre")).ifEmpty { listOf("sombre") }

    // ================================================================ les thèmes
    val SOURCE = linkedMapOf("vert" to 0x3DDC84, "orange" to 0xFF9F43, "jaune" to 0xFFD54F, "violet" to 0xB284FF,
        "bleu" to 0x5FAFFF, "cyan" to 0x4DD0E1, "rose" to 0xFF79C6, "rouge" to 0xFF5F6D)
    private val RAMPE = listOf(0.0 to "fond", 25 / 510.0 to "fond", 27 / 510.0 to "terminal", 39 / 510.0 to "panneau",
        52 / 510.0 to "panneau2", 210 / 510.0 to "pale", 304 / 510.0 to "doux", 475 / 510.0 to "texte", 1.0 to "encre")
    private val NEUTRES = listOf("fond", "panneau", "panneau2", "terminal", "pale", "doux", "texte", "encre")

    fun hexa(s: String): Int = s.removePrefix("#").toInt(16) and 0xFFFFFF

    /** La teinte (0-1), comme colorsys.rgb_to_hsv et java.awt.Color.RGBtoHSB. */
    fun teinte(rgb: Int): Double {
        val r = (rgb shr 16 and 255) / 255.0; val g = (rgb shr 8 and 255) / 255.0; val b = (rgb and 255) / 255.0
        val mx = maxOf(r, g, b); val mn = minOf(r, g, b)
        if (mx == mn) return 0.0
        val d = mx - mn
        val h = when (mx) {
            r -> (g - b) / d
            g -> 2.0 + (b - r) / d
            else -> 4.0 + (r - g) / d
        } / 6.0
        return if (h < 0) h + 1 else h
    }

    private val HSRC = SOURCE.mapValues { teinte(it.value) }

    fun accentProche(rgb: Int): String {
        val h = teinte(rgb)
        return SOURCE.keys.minByOrNull { k -> val x = Math.abs(HSRC.getValue(k) - h); minOf(x, 1 - x) }!!
    }

    class Theme(val cle: String) {
        val clair: Boolean
        val r = HashMap<String, Int>()
        val acc = LinkedHashMap<String, Int>()
        val bord: Double
        val carte: Any?
        private val cache = HashMap<Int, Int>()

        init {
            val o = d().optJSONObject("themes")?.optJSONObject(cle) ?: JSONObject()
            clair = o.optBoolean("clair")
            for (k in NEUTRES) r[k] = hexa(o.optString(k, "#000000"))
            val a = o.optJSONObject("accents") ?: JSONObject()
            for (k in SOURCE.keys) acc[k] = hexa(a.optString(k, "#" + Integer.toHexString(SOURCE.getValue(k))))
            bord = o.optDouble("bord", 1.0)
            carte = if (o.isNull("teinte")) null else o.opt("teinte")
        }

        val sombre get() = cle == "sombre"

        private fun neutre(l: Double): Int {
            for (i in 0 until RAMPE.size - 1) {
                val (a, ra) = RAMPE[i]; val (b, rb) = RAMPE[i + 1]
                if (l <= b) {
                    val k = if (b == a) 0.0 else (l - a) / (b - a)
                    val ca = r.getValue(ra); val cb = r.getValue(rb)
                    fun m(s: Int) = Math.round((ca shr s and 255) + ((cb shr s and 255) - (ca shr s and 255)) * k).toInt()
                    return (m(16) shl 16) or (m(8) shl 8) or m(0)
                }
            }
            return r.getValue("encre")
        }

        /** Une couleur ARGB écrite pour le thème sombre → la même couleur dans ce thème (même règle qu'en Python). */
        fun couleur(c: Int): Int {
            if (sombre) return c
            cache[c]?.let { return it }
            var a = c ushr 24
            val rr = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
            val mx = maxOf(rr, g, b); val mn = minOf(rr, g, b)
            val out = if (a < 255 && mx < 6) c else {
                val l = (mx + mn) / 2.0 / 255
                val n = if ((mx - mn) / 255.0 < 0.2) {
                    if (a < 255 && l > 0.5) { a = minOf(255, (a * bord).toInt()); r.getValue("encre") } else neutre(l)
                } else acc.getValue(accentProche(c and 0xFFFFFF))
                (a shl 24) or (n and 0xFFFFFF)
            }
            cache[c] = out
            return out
        }

        /** Le texte du terminal : les thèmes sombres changent les couleurs vives ; les clairs gardent celles d'origine
         *  (le terminal du téléphone reste sombre, sauf dans l'espace où tout suit le thème). */
        fun texte(c: Int): Int {
            if (sombre || clair) return c
            val rr = c shr 16 and 255; val g = c shr 8 and 255; val b = c and 255
            if ((maxOf(rr, g, b) - minOf(rr, g, b)) / 255.0 < 0.2) return c
            return (c and 0xFF000000.toInt()) or acc.getValue(accentProche(c and 0xFFFFFF))
        }
    }

    @Volatile private var actif: Theme? = null

    fun a(jeu: Jeu): JSONObject {
        val o = jeu.extra.optJSONObject("apparence")
        if (o == null) {
            val n = JSONObject().put("vus", JSONArray()).put("annonces", JSONArray()).put("tout", false)
            jeu.extra.put("apparence", n)
            verifier(jeu, annoncer = false)
            return n
        }
        for (k in listOf("vus", "annonces")) if (!o.has(k)) o.put(k, JSONArray())
        return o
    }

    fun cleTheme(jeu: Jeu): String {
        val c = jeu.extra.optJSONObject("apparence")?.optString("theme", "sombre") ?: "sombre"
        return if (d().optJSONObject("themes")?.has(c) == true) c else "sombre"
    }

    fun theme(jeu: Jeu?): Theme {
        val cle = if (jeu == null || !jeu.existe) "sombre" else cleTheme(jeu)
        actif?.let { if (it.cle == cle) return it }
        return Theme(cle).also { actif = it }
    }

    fun choisirTheme(jeu: Jeu, cle: String): Boolean {
        if (d().optJSONObject("themes")?.has(cle) != true) return false
        a(jeu).put("theme", cle).put("theme_date", System.currentTimeMillis())
        return true
    }

    // ---------------------------------------------------------------- contraste (tests)
    fun luminance(c: Int): Double {
        fun lin(v: Int): Double { val x = v / 255.0; return if (x <= 0.03928) x / 12.92 else Math.pow((x + 0.055) / 1.055, 2.4) }
        return 0.2126 * lin(c shr 16 and 255) + 0.7152 * lin(c shr 8 and 255) + 0.0722 * lin(c and 255)
    }

    fun contraste(a: Int, b: Int): Double {
        val la = luminance(a); val lb = luminance(b)
        return (maxOf(la, lb) + 0.05) / (minOf(la, lb) + 0.05)
    }

    // ================================================================ l'interface évolutive
    fun ids(): List<String> {
        val p = d().optJSONArray("panneaux") ?: return emptyList()
        return (0 until p.length()).map { p.getJSONObject(it).getString("id") }
    }

    private fun ancienne(jeu: Jeu): Boolean {
        val o = jeu.extra.optJSONObject("debloc") ?: return true
        return o.optString("mode", "ancien") != "progressif"
    }

    fun condition(jeu: Jeu, q: JSONObject): Boolean {
        val q2 = JSONObject(q.toString())
        val une = chaines(q2.optJSONArray("une_lecon"))
        q2.remove("une_lecon")
        if (!Intro.condition(jeu, q2)) return false
        if (une.isNotEmpty()) {
            val faits = Histoire.faits(jeu)
            if (une.none { it in faits }) return false
        }
        return true
    }

    /** Les panneaux dont le moment est venu : notés pour toujours et, s'il le faut, annoncés. Renvoie les nouveaux. */
    fun verifier(jeu: Jeu, annoncer: Boolean = true): List<String> {
        if (!jeu.existe) return emptyList()
        val o = jeu.extra.optJSONObject("apparence") ?: return a(jeu).let { emptyList() }
        val vus = chaines(o.optJSONArray("vus")).toMutableList()
        val neufs = mutableListOf<String>()
        val anc = ancienne(jeu)
        val p = d().optJSONArray("panneaux") ?: JSONArray()
        for (i in 0 until p.length()) {
            val x = p.getJSONObject(i)
            val id = x.getString("id")
            if (id in vus) continue
            if (anc || condition(jeu, x.getJSONObject("quand"))) { vus.add(id); neufs.add(id) }
        }
        o.put("vus", JSONArray(vus))
        if (annoncer && !anc && neufs.isNotEmpty()) {
            val an = chaines(o.optJSONArray("annonces")).toMutableList()
            for (n in neufs) if (n !in an) an.add(n)
            o.put("annonces", JSONArray(an))
            jeu.dire(Langue.t("app.pan.${neufs.last()}.dit"), 10)
        }
        return neufs
    }

    fun visibles(jeu: Jeu?): Set<String> {
        val toujours = chaines(d().optJSONArray("toujours")).toSet()
        if (jeu == null || !jeu.existe) return ids().toSet() + toujours
        val o = a(jeu)
        if (o.optBoolean("tout")) return ids().toSet() + toujours
        return chaines(o.optJSONArray("vus")).toSet() + toujours
    }

    fun toutAfficher(jeu: Jeu, oui: Boolean) { a(jeu).put("tout", oui) }

    /** La petite question des grands avant « Tout afficher » : (question, réponse). */
    fun questionAdulte(r: java.util.Random = java.util.Random()): Pair<String, String> {
        val a = 12 + r.nextInt(8); val b = 13 + r.nextInt(7)
        return "$a × $b" to (a * b).toString()
    }

    /** Les annonces en attente (le panneau qui vient d'apparaître) : lues une fois par l'espace. */
    fun prendreAnnonces(jeu: Jeu): List<String> {
        val o = a(jeu)
        val l = chaines(o.optJSONArray("annonces"))
        o.put("annonces", JSONArray())
        return l
    }

    // ================================================================ la grille du PC (mêmes rectangles qu'en Python)
    fun rectDe(c: Int, r: Int, w: Int, h: Int): DoubleArray {
        val g = d().getJSONObject("grille")
        val e = g.getDouble("ecart")
        val sx = (g.getDouble("w") + e) / g.getInt("colonnes")
        val sy = (g.getDouble("h") + e) / g.getInt("rangees")
        fun r2(v: Double) = Math.round(v * 100) / 100.0
        return doubleArrayOf(r2(g.getDouble("x") + c * sx), r2(g.getDouble("y") + r * sy), r2(w * sx - e), r2(h * sy - e))
    }

    fun preset(nom: String): Map<String, IntArray> {
        val ds = d().getJSONObject("dispositions")
        val o = ds.optJSONObject(nom) ?: ds.getJSONObject("classique")
        return o.keys().asSequence().associateWith { k -> val a = o.getJSONArray(k); IntArray(4) { a.getInt(it) } }
    }

    // ================================================================ le téléphone
    class Bande(val id: String, val taille: String)

    fun bandesPreset(nom: String): List<Bande> {
        val ds = d().getJSONObject("telephone").getJSONObject("dispositions")
        val o = ds.optJSONObject(nom) ?: ds.getJSONObject("classique")
        val b = o.getJSONArray("bandes")
        return (0 until b.length()).map { val x = b.getJSONArray(it); Bande(x.getString(0), x.getString(1)) }
    }

    fun tailleFacteur(t: String): Float = d().getJSONObject("telephone").getJSONObject("tailles").optDouble(t, 1.0).toFloat()

    private fun tel(jeu: Jeu): JSONObject {
        val o = a(jeu)
        return o.optJSONObject("tel") ?: JSONObject().put("nom", "classique").also { o.put("tel", it) }
    }

    /** Les bandes de la partie (sans les cachées), dans l'ordre, avec leur taille. */
    fun bandes(jeu: Jeu?): List<Bande> {
        if (jeu == null || !jeu.existe) return bandesPreset("classique")
        val t = tel(jeu)
        val l = t.optJSONArray("bandes")?.let { a -> (0 until a.length()).map { val x = a.getJSONArray(it); Bande(x.getString(0), x.getString(1)) } }
            ?: bandesPreset(t.optString("nom", "classique"))
        val caches = chaines(t.optJSONArray("caches")).toSet()
        return l.filter { it.id !in caches }
    }

    fun nomDisposition(jeu: Jeu?): String = if (jeu == null || !jeu.existe) "classique" else tel(jeu).optString("nom", "classique")

    fun caches(jeu: Jeu): List<String> = chaines(tel(jeu).optJSONArray("caches"))

    private fun ecrire(jeu: Jeu, bandes: List<Bande>, caches: List<String>, nom: String = "perso") {
        val t = tel(jeu)
        t.put("nom", nom).put("bandes", JSONArray(bandes.map { JSONArray(listOf(it.id, it.taille)) })).put("caches", JSONArray(caches))
    }

    private fun toutesBandes(jeu: Jeu): MutableList<Bande> {
        val t = tel(jeu)
        return (t.optJSONArray("bandes")?.let { a -> (0 until a.length()).map { val x = a.getJSONArray(it); Bande(x.getString(0), x.getString(1)) } }
            ?: bandesPreset(t.optString("nom", "classique"))).toMutableList()
    }

    fun deplacer(jeu: Jeu, id: String, vers: Int) {
        val l = toutesBandes(jeu)
        val i = l.indexOfFirst { it.id == id }
        if (i < 0) return
        val b = l.removeAt(i)
        l.add(vers.coerceIn(0, l.size), b)
        ecrire(jeu, l, caches(jeu))
    }

    fun tailler(jeu: Jeu, id: String, taille: String) {
        ecrire(jeu, toutesBandes(jeu).map { if (it.id == id) Bande(it.id, taille) else it }, caches(jeu))
    }

    fun cacher(jeu: Jeu, id: String, oui: Boolean) {
        val l = toutesBandes(jeu)
        if (!oui && l.none { it.id == id }) l.add(Bande(id, "M"))
        val c = caches(jeu).toMutableList()
        if (oui) { if (id !in c) c.add(id) } else c.remove(id)
        ecrire(jeu, l, c)
    }

    fun choisirDisposition(jeu: Jeu, nom: String): Boolean {
        val o = a(jeu)
        if (nom == "mienne") {
            val m = o.optJSONObject("mienne") ?: return false
            o.put("tel", JSONObject(m.toString()).put("nom", "mienne"))
            return true
        }
        if (d().getJSONObject("telephone").getJSONObject("dispositions").optJSONObject(nom) == null) return false
        o.put("tel", JSONObject().put("nom", nom))
        return true
    }

    fun enregistrerMienne(jeu: Jeu) {
        val l = toutesBandes(jeu)
        val m = JSONObject().put("nom", "mienne").put("bandes", JSONArray(l.map { JSONArray(listOf(it.id, it.taille)) }))
            .put("caches", JSONArray(caches(jeu))).put("onglets", JSONArray(ordreOnglets(jeu)))
        a(jeu).put("mienne", m)
        a(jeu).put("tel", JSONObject(m.toString()))
    }

    fun origine(jeu: Jeu) { a(jeu).put("tel", JSONObject().put("nom", "classique")) }

    /** L'ordre des onglets choisi (sans tenir compte de ceux pas encore apparus). */
    fun ordreOnglets(jeu: Jeu?): List<String> {
        val base = chaines(d().getJSONObject("telephone").optJSONArray("onglets"))
        if (jeu == null || !jeu.existe) return base
        val o = chaines(tel(jeu).optJSONArray("onglets"))
        return o.filter { it in base } + base.filter { it !in o }
    }

    fun avancerOnglet(jeu: Jeu, o: String) {
        val l = ordreOnglets(jeu).toMutableList()
        val i = l.indexOf(o)
        if (i <= 0) return
        l.removeAt(i); l.add(i - 1, o)
        tel(jeu).put("onglets", JSONArray(l)).put("nom", "perso")
    }

    /** Les onglets du téléphone déjà apparus, dans l'ordre choisi (le terminal est toujours là). */
    fun onglets(jeu: Jeu?): List<String> = ongletsDe(visibles(jeu), ordreOnglets(jeu))

    /** Les onglets apparus pour ces panneaux vus, dans cet ordre choisi (même règle que onglets_telephone en Python). */
    fun ongletsDe(vus: Set<String>, ordre: List<String>): List<String> {
        val t = d().getJSONObject("telephone")
        val base = chaines(t.optJSONArray("onglets"))
        val o = ordre.filter { it in base } + base.filter { it !in ordre }
        val v = vus + chaines(d().optJSONArray("toujours"))
        val de = t.optJSONObject("onglet_de") ?: JSONObject()
        return o.filter { it == "terminal" || de.optString(it, it) in v }
    }
}
