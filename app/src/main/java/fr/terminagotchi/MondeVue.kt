package fr.terminagotchi

import org.json.JSONObject
import java.io.File
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * La vue du monde des biomes sur le téléphone (onglet « Monde », commande `monde`) : portée de pc/tg/monde.py.
 * Le relief vient de Monde.kt, les pixels de MondeDessin.kt ; ici : la caméra, l'équipe qui se promène, la liste et la
 * fiche (un panneau qui monte du bas : la fiche À LA PLACE de la liste, « ← Mes créatures » ; un toucher à côté la
 * referme), les étiquettes et les effets des commandes (Effets.kt : ce qui a VRAIMENT changé, 1 à 2 s, jamais bloquant).
 */
class MondeVue {
    class Info(val id: String, val nom: String, val type: String, val album: Poses.Album?, val stade: String,
               val guide: Boolean, val sous: String, val fiche: String, val rarete: String?, val shiny: Boolean)

    private class Crea(var info: Info) {
        var at: String? = null
        var seg: Triple<String, String, Double>? = null
        var chemin = ArrayDeque<String>()
        var etat = "idle"
        var jusqu = 0.0
        var face = 1
        val ph = Math.random() * 6
        var vol: DoubleArray? = null       // x0, y0, t0, durée
        var pop = 0.0
        var dit: Pair<String, Double>? = null
    }
    private class Part(var x: Double, var y: Double, val vx: Double, var vy: Double, val max: Double, val c: Int, val s: Double, val g: Double) { var v = 0.0 }
    private class Effet(val e: JSONObject, val t0: Double, val du: Double, val pts: List<DoubleArray>)

    var carte: Monde.Carte? = null
    private var signature = ""
    private var equipe = listOf<Info>()
    private var maison = LinkedHashMap<String, String>()
    private var refuge = listOf<String>()
    private val creas = LinkedHashMap<String, Crea>()
    private var ordre = listOf<Monde.Hex>()
    private var bords = mapOf<String, List<Triple<String, Int, Int>>>()
    private val morph = HashMap<String, Triple<Double, Double, Double>>()
    private val fantomes = mutableListOf<Pair<Monde.Hex, DoubleArray>>()
    private val effets = mutableListOf<Effet>()
    private val parts = mutableListOf<Part>()
    var cam = doubleArrayOf(0.0, 0.0, 2.0)
    private var but: DoubleArray? = null
    private var retour: DoubleArray? = null
    var manuel = false
    var iso: String? = null
    var sel: String? = null
    var feuille = false                    // le panneau du bas (liste ou fiche) est ouvert
    var cwd: String? = null
    var t = 0.0
    private var lu = -9.0
    private var aire = floatArrayOf(0f, 0f, 1f, 1f)
    private var aCadrer = false
    private var z0 = 1f

    // ------------------------------------------------------------ lire le jeu
    fun relire(terrain: File, eq: List<Info>, cwd: String?, forcer: Boolean = false): Boolean {
        this.cwd = cwd
        if (!forcer && t - lu < 2.0 && carte != null) return false
        lu = t
        val terr = try { Monde.lireTerrain(terrain) } catch (e: Exception) { LinkedHashMap() }
        val sig = terr.entries.joinToString(";") { (k, v) -> k + ":" + v.joinToString(",") { it.nom + "[" + it.objets.joinToString("|") + "]" } } +
            "#" + eq.joinToString(",") { it.id + "/" + it.type }
        equipe = eq
        if (sig == signature) { for (e in eq) creas[e.id]?.info = e; return false }
        signature = sig
        reconstruire(terr)
        return true
    }

    private fun reconstruire(terr: Map<String, List<Monde.ParcelleT>>) {
        val vieille = carte
        val anciens = HashMap<String, DoubleArray>()
        vieille?.hex?.values?.forEach { anciens[it.cle] = sommet(it) }
        val c = Monde.construire(terr)
        carte = c
        ordre = c.hex.values.sortedWith(compareBy({ Monde.solY(it.q, it.r) }, { it.q }))
        bords = c.parcelles.associate { p -> p.id to bordsDe(c, p) }
        for (h in c.hex.values) { val o = anciens[h.cle] ?: continue; val n = sommet(h)
            if (abs(o[0] - n[0]) > .5 || abs(o[1] - n[1]) > .5) morph[h.cle] = Triple(o[0], o[1], t) }
        if (vieille != null) for (h in vieille.hex.values) if (c.parCle[h.cle] == null) { val a = anciens.getValue(h.cle); fantomes.add(h to doubleArrayOf(a[0], a[1], t + h.d * .07)) }
        val avant = LinkedHashMap(maison)
        val (m, r) = Monde.placeCreatures(c, equipe.map { it.id to it.type })
        maison = m; refuge = r
        for (e in equipe) {
            val cr = creas.getOrPut(e.id) { Crea(e) }
            cr.info = e
            if (e.id in maison) { if (avant[e.id] != maison[e.id] || c.parCle[cr.at] == null) poser(cr, vieille != null) } else cr.at = null
        }
        creas.keys.retainAll(equipe.map { it.id }.toSet())
        if (vieille == null) aCadrer = true
    }

    private fun bordsDe(c: Monde.Carte, p: Monde.Parcelle): List<Triple<String, Int, Int>> {
        val out = mutableListOf<Triple<String, Int, Int>>()
        for (o in Monde.FLOWER) {
            val h = c.at(p.centre[0] + o[0], p.centre[1] + o[1]) ?: continue
            for ((i, d) in Monde.DIRS.withIndex()) {
                val n = c.at(h.q + d[0], h.r + d[1])
                if (n != null && n.parcelle == p.id) continue
                out.add(Triple(h.cle, Monde.DIR_EDGE[i][0], Monde.DIR_EDGE[i][1]))
            }
        }
        return out
    }

    // ------------------------------------------------------------ positions
    fun sommet(h: Monde.Hex): DoubleArray {
        var x = Monde.solX(h.q, h.r); var y = Monde.solY(h.q, h.r) - h.h * Monde.HZ
        val m = morph[h.cle]
        if (m != null) {
            val k = ((t - m.third) / .8).coerceIn(0.0, 1.0)
            if (k >= 1) morph.remove(h.cle) else { val e = ease(k); x = m.first + (x - m.first) * e; y = m.second + (y - m.second) * e }
        }
        return doubleArrayOf(x, y)
    }

    private fun hexDe(chemin: String?): Monde.Hex? {
        val c = carte ?: return null
        val p = (chemin ?: return null).split("/")
        if (p.size < 2 || p[0] != "biome") return null
        if (p.size == 2) { val ps = c.parcelles.firstOrNull { it.type == p[1] } ?: return null; return c.at(ps.centre[0], ps.centre[1]) }
        val par = c.par[p[1] + "/" + p[2]] ?: return null
        if (p.size >= 4) par.poses[p[3]]?.let { return c.at(par.centre[0] + it.oq, par.centre[1] + it.or_) }
        return c.at(par.centre[0], par.centre[1])
    }

    private fun pointDe(chemin: String?): DoubleArray = hexDe(chemin)?.let { sommet(it) } ?: milieu()

    private fun milieu(): DoubleArray {
        val hs = carte?.hex?.values ?: return doubleArrayOf(0.0, 0.0)
        if (hs.isEmpty()) return doubleArrayOf(0.0, 0.0)
        return doubleArrayOf(hs.sumOf { Monde.solX(it.q, it.r) } / hs.size, hs.sumOf { Monde.solY(it.q, it.r) } / hs.size - 20)
    }

    private fun ajuster(hs: Collection<Monde.Hex>, doux: Boolean, zmax: Double) {
        if (hs.isEmpty()) return
        var x0 = 1e9; var y0 = 1e9; var x1 = -1e9; var y1 = -1e9
        for (h in hs) { val x = Monde.solX(h.q, h.r); val y = Monde.solY(h.q, h.r)
            x0 = min(x0, x - Monde.HR); x1 = max(x1, x + Monde.HR)
            y0 = min(y0, y - h.h * Monde.HZ - Monde.HH - (if (h.scen != null || h.kind == "fleche") 30 else 0))
            y1 = max(y1, y - h.base * Monde.HZ + Monde.HH + h.pilier) }
        y0 -= 20
        val z = max(.5 * z0, min(aire[2] / (x1 - x0 + 16), (aire[3] - 40 * z0) / (y1 - y0 + 16)) * .95).coerceAtMost(zmax * z0)
        val b = doubleArrayOf((x0 + x1) / 2, (y0 + y1) / 2 + 14 / z, z)
        if (doux) but = b else { cam = b; but = null }
    }

    fun toutVoir(doux: Boolean = true) { manuel = false; carte?.let { ajuster(it.hex.values, doux, 3.2) } }
    private fun ecranX(x: Double) = (aire[0] + aire[2] / 2 + (x - cam[0]) * cam[2]).toFloat()
    private fun ecranY(y: Double) = (aire[1] + aire[3] / 2 + (y - cam[1]) * cam[2]).toFloat()
    private fun mondeX(sx: Float) = (sx - aire[0] - aire[2] / 2) / cam[2] + cam[0]
    private fun mondeY(sy: Float) = (sy - aire[1] - aire[3] / 2) / cam[2] + cam[1]

    // ------------------------------------------------------------ les créatures
    private fun peut(cr: Crea, h: Monde.Hex?): Boolean {
        if (h == null || h.region != cr.info.type || h.block) return false
        val p = carte?.par?.get(h.parcelle) ?: return true
        return p.poses.values.none { it.bloque && p.centre[0] + it.oq == h.q && p.centre[1] + it.or_ == h.r }
    }
    private fun pas(cr: Crea, a: Monde.Hex, b: Monde.Hex) = peut(cr, b) && abs(a.h - b.h) <= 2.9

    private fun poser(cr: Crea, arrivee: Boolean) {
        val c = carte ?: return
        val p = c.par[maison[cr.info.id]] ?: return
        val hs = Monde.FLOWER.mapNotNull { c.at(p.centre[0] + it[0], p.centre[1] + it[1]) }
        val ok = hs.filter { peut(cr, it) }.sortedBy { it.d }.ifEmpty { listOfNotNull(c.at(p.centre[0], p.centre[1])) }
        val h = ok[min(ok.size - 1, (Math.random() * min(3, ok.size)).toInt())]
        cr.at = h.cle; cr.seg = null; cr.chemin.clear(); cr.etat = "idle"; cr.jusqu = t + 1
        if (arrivee) { val s = sommet(h); cr.vol = doubleArrayOf(s[0], s[1] - 170, t + .6, 1.0) }
    }

    private fun penser(cr: Crea) {
        val c = carte ?: return
        val r = Math.random()
        if (r < .1) { cr.etat = "dort"; cr.jusqu = t + 4 + Math.random() * 5; return }
        if (r < .25) { cr.etat = "saute"; cr.jusqu = t + .9; return }
        if (r < .38) { cr.etat = "idle"; cr.jusqu = t + 1.5 + Math.random() * 2.5; return }
        val dep = c.parCle[cr.at] ?: return
        val prev = HashMap<String, String?>(); prev[dep.cle] = null
        val file = ArrayDeque<Pair<Monde.Hex, Int>>(); file.add(dep to 0)
        val out = mutableListOf<Pair<Monde.Hex, Int>>()
        while (file.isNotEmpty()) {
            val (h, d) = file.removeFirst(); out.add(h to d)
            if (d >= 6) continue
            for (dd in Monde.DIRS) { val n = c.at(h.q + dd[0], h.r + dd[1]) ?: continue
                if (n.cle in prev || !pas(cr, h, n)) continue
                prev[n.cle] = h.cle; file.add(n to d + 1) }
        }
        var cs = out.filter { it.second >= 2 }
        val chez = cs.filter { it.first.parcelle == maison[cr.info.id] }
        if (chez.isNotEmpty() && Math.random() < .65) cs = chez
        if (cs.isEmpty()) { cr.etat = "idle"; cr.jusqu = t + 2; return }
        var but: String? = cs[(Math.random() * cs.size).toInt()].first.cle
        val ch = ArrayDeque<String>()
        while (but != null && prev[but] != null) { ch.addFirst(but); but = prev[but] }
        cr.chemin = ch; cr.etat = "marche"; cr.jusqu = t + 20
    }

    private fun avancer(cr: Crea, dt: Double) {
        val c = carte ?: return
        if (c.parCle[cr.at] == null) { if (cr.info.id in maison) poser(cr, false); return }
        cr.vol?.let { v -> if (t >= v[2] + v[3]) { cr.vol = null; cr.pop = t + .6; val p = posCrea(cr); eclat(p[0], p[1], 3, 10) } else return }
        val s = cr.seg
        if (s != null) {
            val ha = c.parCle.getValue(s.first); val hb = c.parCle[s.second] ?: ha
            val k = s.third + dt * 1.3 / (1 + abs(hb.h - ha.h) * .15)
            if (k >= 1) { cr.at = s.second; cr.seg = null } else cr.seg = Triple(s.first, s.second, k)
        } else if (cr.etat == "marche") {
            if (cr.chemin.isEmpty()) { cr.etat = "idle"; cr.jusqu = t + 1 + Math.random() * 2; return }
            val n = cr.chemin.removeFirst()
            val ha = c.parCle.getValue(cr.at!!); val hb = c.parCle[n]
            if (hb == null || !pas(cr, ha, hb)) { cr.chemin.clear(); cr.etat = "idle"; cr.jusqu = t + .5; return }
            val xa = Monde.solX(ha.q, ha.r); val xb = Monde.solX(hb.q, hb.r)
            if (abs(xb - xa) > .1) cr.face = if (xb > xa) 1 else -1
            cr.seg = Triple(cr.at!!, n, 0.0)
        } else if (t > cr.jusqu) penser(cr)
    }

    private fun posCrea(cr: Crea): DoubleArray {
        val c = carte!!
        var x: Double; var y: Double; var d: Double
        val s = cr.seg
        if (s != null) {
            val ha = c.parCle.getValue(s.first); val hb = c.parCle[s.second] ?: ha
            val a = sommet(ha); val b = sommet(hb); val k = s.third; val ss = k * k * (3 - 2 * k)
            x = a[0] + (b[0] - a[0]) * k; y = a[1] + (b[1] - a[1]) * ss
            val dh = abs(hb.h - ha.h); if (dh > .4) y -= sin(k * PI) * min(9.0, dh * Monde.HZ * .6)
            d = max(Monde.solY(ha.q, ha.r), Monde.solY(hb.q, hb.r)) + .5
        } else {
            val h = c.parCle.getValue(cr.at!!); val p = sommet(h); x = p[0]; y = p[1]; d = Monde.solY(h.q, h.r) + .5
        }
        cr.vol?.let { v -> val q = ((t - v[2]) / v[3]).coerceIn(0.0, 1.0); x = v[0] + (x - v[0]) * q * q; y = v[1] + (y - v[1]) * q * q; d = 1e6 }
        return doubleArrayOf(x, y, d)
    }

    fun dire(texte: String, duree: Double = 5.0) {
        val cr = creas.values.firstOrNull { it.at != null && it.info.guide } ?: creas.values.firstOrNull { it.at != null }
        if (cr != null) cr.dit = texte to t + duree else bulle = texte to t + duree
    }
    private var bulle: Pair<String, Double>? = null

    private fun eclat(x: Double, y: Double, sorte: Int, n: Int) {
        val cols = when (sorte) { 0 -> listOf(0xFFFFFF, 0xE6E6E6, 0xCFD8DC); 1 -> listOf(0xFF5C8A, 0xFF8FB0)
            2 -> listOf(0xFF5F6D, 0xFFD54F, 0x3DDC84, 0x5FAFFF, 0xB284FF); else -> listOf(0xFFE066, 0xFFF6B0, 0xFFFFFF) }
        repeat(n) { val a = Math.random() * PI * 2; val s = 10 + Math.random() * 24
            parts.add(Part(x + (Math.random() - .5) * 8, y - 8 - Math.random() * 8, cos(a) * s, sin(a) * s * .6 - (if (sorte == 2) 30 else 8),
                .6 + Math.random() * .6, cols[(Math.random() * cols.size).toInt()], if (Math.random() < .5) 2.0 else 1.4, if (sorte == 2) 60.0 else 0.0)) }
    }

    // ------------------------------------------------------------ le temps
    fun tick(dt: Double) {
        t += dt
        but?.let { b -> val k = min(1.0, dt * 4); for (i in 0..2) cam[i] += (b[i] - cam[i]) * k
            if (abs(b[2] - cam[2]) < .01 && abs(b[0] - cam[0]) < .5 && abs(b[1] - cam[1]) < .5) { cam = b.copyOf(); but = null } }
        if (carte != null) for (cr in creas.values) if (cr.at != null) avancer(cr, dt)
        for (p in parts) { p.v += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += p.g * dt }
        parts.removeAll { it.v >= it.max }
        while (parts.size > 300) parts.removeAt(0)
        fantomes.removeAll { t - it.second[2] >= 1.0 }
        effets.removeAll { t - it.t0 >= it.du }
        if (retour != null && effets.isEmpty()) { if (!manuel) but = retour; retour = null }
    }

    // ------------------------------------------------------------ les effets
    fun preparer(evs: List<JSONObject>) {
        for (e in evs) {
            val ty = e.getString("type")
            if (ty in setOf("objet-", "dossier-", "deplace", "renomme", "cd")) e.put("_av", pointDe(e.optString(if (e.has("chemin")) "chemin" else "de")).joinToString(","))
            else if (ty == "groupe" && e.optString("sorte").endsWith("-")) {
                val ch = e.optJSONArray("chemins"); e.put("_avs", (0 until (ch?.length() ?: 0)).joinToString(";") { pointDe(ch!!.getString(it)).joinToString(",") })
            }
        }
    }

    private fun pt(s: String) = s.split(",").map { it.toDouble() }.toDoubleArray()

    fun lancer(evs: List<JSONObject>) {
        var d = 0.0
        var premier: DoubleArray? = null
        for (e in evs.take(12)) {
            val jok = e.getString("type") == "jokers"
            val ps = points(e)
            effets.add(Effet(e, t + d, if (jok) 1.1 else 1.8, ps))
            if (premier == null && ps.isNotEmpty()) premier = ps[0]
            d += if (jok) .55 else .3
        }
        val p = premier ?: return
        if (!manuel) {
            val sx = ecranX(p[0]); val sy = ecranY(p[1])
            if (!(sx > aire[0] + aire[2] * .15 && sx < aire[0] + aire[2] * .85 && sy > aire[1] + aire[3] * .15 && sy < aire[1] + aire[3] * .85)) {
                retour = retour ?: cam.copyOf(); but = doubleArrayOf(p[0], p[1], max(cam[2], 1.6 * z0))
            }
        }
    }

    private fun guidePt(): DoubleArray {
        val cr = creas.values.firstOrNull { it.at != null && it.info.guide } ?: creas.values.firstOrNull { it.at != null }
        return if (cr != null) posCrea(cr) else milieu()
    }

    private fun points(e: JSONObject): List<DoubleArray> {
        val ty = e.getString("type")
        if (e.has("_av")) { val a = pt(e.getString("_av")); return if (ty in setOf("deplace", "renomme", "cd")) listOf(a, pointDe(e.optString("vers"))) else listOf(a) }
        if (e.has("_avs") && e.getString("_avs").isNotEmpty()) return e.getString("_avs").split(";").map { pt(it) }
        val ch = e.optJSONArray("chemins")
        return when (ty) {
            "jokers", "find", "groupe" -> if (ch != null && ch.length() > 0) (0 until min(20, ch.length())).map { pointDe(ch.getString(it)) } else listOf(pointDe(e.optString("chemin")))
            "deplace", "renomme", "copie" -> listOf(pointDe(e.optString("de")), pointDe(e.optString("vers")))
            "cd" -> listOf(pointDe(e.optString("de")), pointDe(e.optString("vers")))
            "lucioles", "photo" -> listOf(guidePt())
            "messager" -> { val g = guidePt(); val c = e.optString("cible"); listOf(g, if (c in Monde.TYPES) pointDe("biome/$c") else doubleArrayOf(g[0] + 120, g[1] - 90)) }
            "tuyau" -> listOf(pointDe(if (!e.isNull("source") && e.has("source")) e.getString("source") else "biome/" + e.optString("region")))
            "caisse", "taille", "etoile", "rembobine" -> {
                val cs = mutableListOf<String>(); if (e.has("chemin") && !e.isNull("chemin")) cs.add(e.getString("chemin"))
                val l = e.optJSONArray("chemins") ?: e.optJSONArray("elements")
                if (l != null) for (i in 0 until l.length()) { val x = l.get(i); cs.add(if (x is org.json.JSONArray) x.optString(0) else x.toString()) }
                cs.take(9).map { if (hexDe(it) != null) pointDe(it) else guidePt() }.ifEmpty { listOf(guidePt()) }
            }
            "lien" -> { val a1 = if (hexDe(e.optString("chemin")) != null) pointDe(e.optString("chemin")) else guidePt()
                val c = if (e.isNull("cible")) null else e.optString("cible")
                listOf(a1, if (c != null && hexDe(c) != null) pointDe(c) else doubleArrayOf(a1[0] + 90, a1[1] - 70)) }
            in GUIDE2 -> { val c = if (e.has("chemin") && !e.isNull("chemin")) e.getString("chemin") else null
                listOf(if (c != null && hexDe(c) != null) pointDe(c) else guidePt()) }
            else -> listOf(pointDe(e.optString("chemin")))
        }
    }

    // ============================================================ le dessin
    fun dessiner(tl: Toile, Z: MutableList<EspaceDessin.Zone>, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val neuve = floatArrayOf(x, y, w, h)
        if ((abs(neuve[2] - aire[2]) > 40 || abs(neuve[3] - aire[3]) > 40) && !manuel) aCadrer = true
        aire = neuve; z0 = z
        if (aCadrer && carte != null) { aCadrer = false; toutVoir(false) }
        val c = carte
        tl.rrect(x, y, w, h, 12 * z, 0xFF0B1A26.toInt(), 0x22FFFFFF, 1 * z)
        if (c == null) return
        if (c.parcelles.isEmpty()) { vide(tl, z); return }
        tl.clip(x, y, w, h)
        monde(tl, Z, z)
        outils(tl, Z, z)
        panneau(tl, Z, z)
        tl.declip()
    }

    private fun vide(tl: Toile, z: Float) {
        val (x, y, w, h) = aire.toList()
        val ty = equipe.firstOrNull { it.guide }?.type ?: "plante"
        tl.texte(t("monde.vide"), x + w / 2, y + h / 2 - 26 * z, 15 * z, EspaceDessin.TEXTE, true, 'c')
        tl.texte(t("monde.vide_cmd"), x + w / 2, y + h / 2, 13 * z, EspaceDessin.DOUX, false, 'c')
        tl.rrect(x + w / 2 - 140 * z, y + h / 2 + 14 * z, 280 * z, 30 * z, 8 * z, 0xFF05060A.toInt(), 0x783DDC84, 1 * z)
        tl.texte("mkdir -p biome/$ty/parcelle_1", x + w / 2, y + h / 2 + 29 * z, 12.5f * z, EspaceDessin.VERT, false, 'c', true)
    }

    private fun ciel(tl: Toile) {
        val (x, y, w, h) = aire.toList()
        for (i in 0 until 10) { val k = i / 9.0
            val c = (0xFF shl 24) or ((124 + (191 - 124) * k).toInt() shl 16) or ((198 + (231 - 198) * k).toInt() shl 8) or (240 + (255 - 240) * k).toInt()
            tl.rect(x, y + h * i / 10, w, h / 10 + 1, c) }
        for (i in 0 until 3) { val cx = x + ((t * 6 * z0 + i * w * .4) % (w + 300)).toFloat() - 150; val cy = y + h * (.06f + i * .08f)
            for (q in listOf(intArrayOf(0, 2, 24, 4), intArrayOf(4, 0, 14, 3), intArrayOf(18, 1, 10, 4))) tl.rect(cx + q[0] * 2 * z0 / 2, cy + q[1] * z0, q[2] * z0, q[3] * z0, 0xBEFFFFFF.toInt()) }
    }

    private fun alphaIso(region: String?, between: List<String>?) = if (iso == null || region == iso || (between != null && iso in between)) 1f else .32f
    private fun a(c: Int, al: Int) = (c and 0xFFFFFF) or (al.coerceIn(0, 255) shl 24)

    private fun monde(tl: Toile, Z: MutableList<EspaceDessin.Zone>, z: Float) {
        val c = carte!!
        ciel(tl)
        Z.add(EspaceDessin.Zone(aire[0], aire[1], aire[2], aire[3], "monde:vue"))
        val x0w = mondeX(aire[0] - 40); val x1w = mondeX(aire[0] + aire[2] + 40)
        val y0w = mondeY(aire[1] - 60); val y1w = mondeY(aire[1] + aire[3] + 120)
        val tombe = HashMap<String, Double>(); val caches = HashSet<String>()
        for (ef in effets) { val age = t - ef.t0; val ty = ef.e.getString("type")
            if (ty == "dossier+" && age < 1.4) { val ps = ef.e.optJSONArray("parcelles")
                val l = if (ps != null && ps.length() > 0) (0 until ps.length()).map { ps.getString(it) } else listOf(ef.e.optString("chemin"))
                for (ch in l) { val p = ch.split("/"); if (p.size >= 3) tombe[p[1] + "/" + p[2]] = age } }
            if (ty in setOf("objet+", "copie", "deplace", "renomme") && age < .9) caches.add(ef.e.optString(if (ef.e.has("vers")) "vers" else "chemin")) }
        // les objets et les créatures, triés avec les hexagones (les falaises de devant cachent l'arrière)
        class Mob(val d: Double, val p: Monde.Parcelle?, val nom: String?, val pose: Monde.Pose?, val h: Monde.Hex?, val cr: Crea?)
        val mobs = mutableListOf<Mob>()
        for (p in c.parcelles) for ((nom, v) in p.poses) { val h = c.at(p.centre[0] + v.oq, p.centre[1] + v.or_) ?: continue
            mobs.add(Mob(Monde.solY(h.q, h.r) + .4, p, nom, v, h, null)) }
        for (cr in creas.values) if (cr.at != null && c.parCle[cr.at] != null) mobs.add(Mob(posCrea(cr)[2], null, null, null, null, cr))
        mobs.sortBy { it.d }
        var j = 0
        for (h in ordre) {
            val dh = Monde.solY(h.q, h.r)
            while (j < mobs.size && mobs[j].d < dh) { mobile(tl, Z, mobs[j].p, mobs[j].nom, mobs[j].pose, mobs[j].h, mobs[j].cr, caches, z); j++ }
            val hx = Monde.solX(h.q, h.r)
            if (hx < x0w || hx > x1w || dh - h.h * Monde.HZ > y1w || dh + 40 < y0w) continue
            hex(tl, h, tombe[h.parcelle], z)
        }
        while (j < mobs.size) { mobile(tl, Z, mobs[j].p, mobs[j].nom, mobs[j].pose, mobs[j].h, mobs[j].cr, caches, z); j++ }
        for ((h, f) in fantomes) { val age = max(0.0, t - f[2])
            tl.cadre(MondeDessin.sprite(h.kind, h.v, h.mur, h.pilier), ecranX(f[0]), ecranY(f[1] + age * age * 160), cam[2].toFloat(), false, false, 1f, 1f,
                (age * 25 * (if (h.q % 2 != 0) 1 else -1)).toFloat(), (1 - age).toFloat().coerceAtLeast(0f)) }
        contours(tl)
        for (p in parts) { val al = 1 - p.v / p.max
            tl.rect(ecranX(p.x), ecranY(p.y), (p.s * cam[2]).toFloat(), (p.s * cam[2]).toFloat(), a(p.c, (255 * al).toInt())) }
        for (ef in effets) if (t >= ef.t0) try { effet(tl, ef, t - ef.t0, z) } catch (e: Exception) { }
        etiquettes(tl, Z, z)
        bulles(tl, z)
    }

    private fun hex(tl: Toile, h: Monde.Hex, chute: Double?, z: Float) {
        val s = sommet(h)
        var oy = 0.0; var al = alphaIso(h.region, h.between)
        if (chute != null) { val k = ((chute - h.d * .12) / .5).coerceIn(0.0, 1.0); if (k <= 0) return; oy = (1 - easeBack(k)) * -60; al = min(al, k.toFloat()) }
        val fy = if (h.float != 0) sin(t * 1.1 + h.q * .7 + h.r) * 1.2 else 0.0
        val sc = if (h.float != 0) .84f else 1f
        val sx = ecranX(s[0]); val sy = ecranY(s[1] + oy + fy); val zz = cam[2].toFloat()
        tl.cadre(MondeDessin.sprite(h.kind, h.v, h.mur, h.pilier), sx, sy, zz * sc, false, false, 1f, 1f, 0f, al)
        if (al < 1 && chute == null) return
        when (h.kind) {
            "lave" -> { val g = .22 + .22 * sin(t * 3 - (h.flow ?: 0) * 1.4); tl.ellipse(sx, sy, (Monde.HR * .8 * zz).toFloat(), (Monde.HR * .5 * zz).toFloat(), a(0xFFE28A, (255 * g * al).toInt()))
                if (h.crater != 0) tl.lueur(sx, sy - 6 * zz, (Monde.HR * 2 * zz).toFloat(), a(0xFF7A1A, (60 + 25 * sin(t * 2.3)).toInt())) }
            "eau" -> for (i in 0 until 2) { val ph = (t * 1.1 + h.q * .37 + h.r * .61 + i * .5) % 2
                if (ph < 1) tl.rect(sx + (-6 + Math.floorMod(h.q * 7 + h.r * 3 + i * 9, 12)) * zz, sy + ((-3 + i * 4 + ph * 2) * zz).toFloat(), 3 * zz, zz, a(0xDCF5FF, (215 * (1 - ph)).toInt())) }
            "pont" -> for (kk in listOf(3, 0)) tl.rect(sx + (cos(kk * PI / 3) * Monde.HR * zz).toFloat() - zz, sy + (sin(kk * PI / 3) * Monde.HR * .62 * zz).toFloat() - 6 * zz, 2 * zz, 7 * zz, 0xFF5A381E.toInt())
        }
        val sc2 = h.scen
        if (sc2 != null) { val im = MondeDessin.decor(sc2.k)
            tl.ellipse(sx, sy + zz, (im.w * .3 * sc2.s * zz).toFloat(), (im.w * .11 * sc2.s * zz).toFloat(), a(0, (64 * al).toInt()))
            tl.cadre(im, sx, sy + 2 * zz, (zz * sc2.s).toFloat(), false, false, 1f, 1f, if (sc2.k in Monde.SCEN_BLOCK) (sin(t * 1.3 + h.q + h.r) * 1.2).toFloat() else 0f, al) }
    }

    private fun mobile(tl: Toile, Z: MutableList<EspaceDessin.Zone>, p: Monde.Parcelle?, nom: String?, v: Monde.Pose?, h: Monde.Hex?, cr: Crea?, caches: Set<String>, z: Float) {
        val zz = cam[2].toFloat()
        if (p != null && v != null && h != null) {
            val chemin = "biome/${p.id}/$nom"
            if (chemin in caches) return
            val s = sommet(h); val al = alphaIso(p.type, null); val im = MondeDessin.decor(v.k)
            val sx = ecranX(s[0]); val sy = ecranY(s[1])
            var rot = 0f
            for (ef in effets) { val age = t - ef.t0; if (age < 0 || age >= ef.du) continue
                val ch = ef.e.optJSONArray("chemins"); val vise = ef.e.optString("chemin") == chemin || (ch != null && (0 until ch.length()).any { ch.getString(it) == chemin })
                if (!vise) continue
                rot = (sin(age * 30) * 6 * max(0.0, 1 - age / 1.2)).toFloat()
                if (ef.e.getString("type") in setOf("jokers", "find")) tl.lueur(sx, sy - im.h * zz * .5f, 26 * zz, a(0xFFEC80, (150 * (1 - age / ef.du)).toInt())) }
            tl.ellipse(sx, sy + zz, im.w * .32f * zz, im.w * .12f * zz, a(0, (70 * al).toInt()))
            tl.cadre(im, sx, sy + 2 * zz, zz, false, false, 1f, 1f, rot, al)
            return
        }
        val c = cr ?: return
        val info = c.info
        val ps = posCrea(c); val al = alphaIso(info.type, null)
        val h0 = STADES[info.stade] ?: 36.0
        var bob = 0.0
        if (c.seg != null) bob = abs(sin(t * 9 + c.ph)) * 2
        if (c.etat == "saute" && c.seg == null) { val q = (1 - (c.jusqu - t) / .9).coerceIn(0.0, 1.0); bob = max(0.0, sin(min(q * 2, 1.0) * PI) * 9) }
        if (c.pop > t) bob += sin((1 - (c.pop - t) / .6) * PI) * 10
        c.vol?.let { vv -> bob += sin(((t - vv[2]) / vv[3]).coerceIn(0.0, 1.0) * PI) * 30 }
        val sx = ecranX(ps[0]); val sy = ecranY(ps[1])
        val on = carte?.parCle?.get(c.at)
        val eau = on != null && on.kind == "eau"
        tl.ellipse(sx, sy + zz, (max(5.0, h0 * .36) * zz).toFloat(), (max(2.0, h0 * .13) * zz).toFloat(), a(0, (76 * al).toInt()))
        if (sel == info.id) tl.cercle(sx, sy + zz, ((h0 * .5 + 5) * (1 + sin(t * 5) * .08) * zz).toFloat(), 0xFFFFE066.toInt(), 2 * z)
        val top = sy - ((bob - (if (eau) h0 * .28 else 0.0)) * zz).toFloat()
        val rc = RARETE[info.rarete] ?: (if (info.shiny) RARETE.getValue("épique") else null)
        if (rc != null) tl.lueur(sx, top - (h0 * .5 * zz).toFloat(), (h0 * .75 * zz).toFloat(), a(rc, ((90 + 50 * sin(t * 2.4 + c.ph)) * al).toInt()))
        val alb = info.album
        if (alb != null) {
            val etat = if (c.etat == "dort") "dort" else if (c.seg != null) "marche" else "assis"
            val k = if (etat == "marche") (t * 6).toInt() else 0
            val souffle = (if (c.etat == "dort") .94 + sin(t * 1.6) * .02 else 1 + sin(t * 2.2 + c.ph) * .018).toFloat()
            tl.cadre(alb.image(etat, k), sx, top, (h0 * zz / max(1, alb.ref)).toFloat(), c.face < 0, alb.lisse, 1f, souffle, 0f, al)
        } else tl.ellipse(sx, top - (h0 * .45 * zz).toFloat(), (h0 * .35 * zz).toFloat(), (h0 * .4 * zz).toFloat(), a(COUL[info.type] ?: 0x888888, (255 * al).toInt()))
        if (eau) tl.cercle(sx, sy, ((h0 * .45 + sin(t * 3) * 1.5) * zz).toFloat(), 0xC8E6F8FF.toInt(), 1 * z)
        if (sel == info.id) { val ay = top - ((h0 + 6 + sin(t * 6) * 2) * zz).toFloat()
            tl.poly(floatArrayOf(sx - 5 * zz, sx + 5 * zz, sx), floatArrayOf(ay, ay, ay + 5 * zz), 0xFFFFE066.toInt()) }
        Z.add(EspaceDessin.Zone(sx - (h0 * .5 * zz).toFloat() - 8 * z, top - (h0 * zz).toFloat() - 8 * z, (h0 * zz).toFloat() + 16 * z, (h0 * zz).toFloat() + 16 * z, "monde:crea:" + info.id))
    }

    private fun contours(tl: Toile) {
        val c = carte!!; val zz = cam[2].toFloat()
        val occ = maison.values.toSet()
        val cw = cwd
        val ici: List<String>? = if (cw != null && cw.startsWith("biome/")) { val p = cw.split("/")
            if (p.size >= 3) listOf(p[1] + "/" + p[2]) else c.parcelles.filter { it.type == p[1] }.map { it.id } } else null
        for ((pid, bs) in bords) {
            val (col, ep, pl) = when {
                ici != null && pid in ici -> Triple(0xFF3DFF7C.toInt(), 2f * z0, 6f * zz)
                pid !in occ && (iso == null || pid.startsWith("$iso/")) -> Triple(0x96FFF8DC.toInt(), 1.4f * z0, 2f * zz)
                else -> continue
            }
            for ((cle, k1, k2) in bs) { val h = c.parCle[cle] ?: continue; val s = sommet(h)
                val sx = ecranX(s[0]); val sy = ecranY(s[1])
                tl.ligne(sx + (cos(k1 * PI / 3) * Monde.HR * zz).toFloat(), sy + (sin(k1 * PI / 3) * Monde.HR * .62 * zz).toFloat(),
                    sx + (cos(k2 * PI / 3) * Monde.HR * zz).toFloat(), sy + (sin(k2 * PI / 3) * Monde.HR * .62 * zz).toFloat(), col, ep, pl, pl * .7f, -(t * 20 * zz).toFloat()) }
        }
    }

    private fun etiquettes(tl: Toile, Z: MutableList<EspaceDessin.Zone>, z: Float) {
        val c = carte!!; val zz = cam[2]
        val places = mutableListOf<FloatArray>()
        for (tid in Monde.TYPES) {
            val ps = c.parcelles.filter { it.type == tid }
            if (ps.isEmpty() || (iso != null && iso != tid)) continue
            val hs = ps.flatMap { p -> Monde.FLOWER.mapNotNull { c.at(p.centre[0] + it[0], p.centre[1] + it[1]) } }
            val top = hs.minByOrNull { Monde.solY(it.q, it.r) } ?: continue
            val xw = Monde.solX(top.q, top.r)
            val yw = hs.filter { abs(Monde.solX(it.q, it.r) - xw) < Monde.HR * 4 }.minOf { sommet(it)[1] - (if (it.scen != null) 24 else 0) } - 10
            val n = maison.values.count { it.startsWith("$tid/") }
            val att = equipe.count { it.type == tid && it.id in refuge }
            val txt = "${EMOJI[tid]} $tid/ $n/${ps.size}"
            val tw = tl.mesure(txt, 12 * z, true) + 18 * z + (if (att > 0) 26 * z else 0f)
            val bx = ecranX(xw) - tw / 2; var by = ecranY(yw) - 22 * z
            for (o in places) if (bx < o[0] + o[2] && bx + tw > o[0] && by < o[1] + o[3] && by + 22 * z > o[1]) by = o[1] - 24 * z
            places.add(floatArrayOf(bx, by, tw, 22 * z))
            val actif = cwd?.startsWith("biome/$tid") == true
            tl.rrect(bx, by, tw, 22 * z, 6 * z, if (actif) 0xEB05140A.toInt() else 0xC805090F.toInt(), if (actif) 0xFF3DFF7C.toInt() else a(COUL[tid] ?: 0x888888, 200), 1.2f * z)
            tl.texte(txt, bx + 9 * z, by + 11 * z, 12 * z, if (actif) 0xFF3DFF7C.toInt() else 0xFFE6F0FF.toInt(), true)
            if (att > 0) { tl.rrect(bx + tw - 28 * z, by + 3 * z, 22 * z, 16 * z, 5 * z, 0xFFFFD866.toInt(), null, 0f)
                tl.texte("+$att", bx + tw - 17 * z, by + 11 * z, 10.5f * z, 0xFF2B2416.toInt(), true, 'c') }
            Z.add(EspaceDessin.Zone(bx, by, tw, 22 * z, "monde:region:$tid"))
        }
        if (zz >= 1.4 * z0 || iso != null) for (p in c.parcelles) {
            if (iso != null && p.type != iso) continue
            val h = c.at(p.centre[0], p.centre[1]) ?: continue
            val s = sommet(h); val libre = p.id !in maison.values
            val txt = p.nom + if (libre) " · " + t("monde.libre") else ""
            val tw = tl.mesure(txt, 10.5f * z, false, true) + 10 * z
            val sx = ecranX(s[0]); val sy = ecranY(s[1])
            tl.rrect(sx - tw / 2, sy - 8 * z, tw, 16 * z, 4 * z, if (libre) 0xDCFFF8DC.toInt() else 0x9605090F.toInt(), null, 0f)
            tl.texte(txt, sx, sy, 10.5f * z, if (libre) 0xFF5A3A10.toInt() else 0xFFE6F0FF.toInt(), false, 'c', true)
        }
    }

    private fun bulles(tl: Toile, z: Float) {
        for (cr in creas.values) { val d = cr.dit ?: continue; if (cr.at == null) continue
            if (t > d.second) { cr.dit = null; continue }
            val p = posCrea(cr); val h0 = STADES[cr.info.stade] ?: 36.0
            bulle(tl, d.first, ecranX(p[0]), ecranY(p[1] - h0 - 8), z) }
        val b = bulle
        if (b != null && t < b.second) bulle(tl, b.first, aire[0] + aire[2] / 2, aire[1] + aire[3] - 60 * z, z)
    }

    private fun couper(tl: Toile, s: String, l: Float, taille: Float): List<String> {
        val out = mutableListOf<String>(); var cour = ""
        for (mot in s.split(" ")) { val e = if (cour.isEmpty()) mot else "$cour $mot"
            if (cour.isNotEmpty() && tl.mesure(e, taille) > l) { out.add(cour); cour = mot } else cour = e }
        if (cour.isNotEmpty()) out.add(cour)
        return out
    }

    private fun bulle(tl: Toile, texte: String, sx: Float, sy: Float, z: Float) {
        val ls = couper(tl, texte, min(260 * z, aire[2] * .7f), 13 * z).take(4)
        val tw = ls.maxOf { tl.mesure(it, 13 * z) } + 20 * z; val bh = ls.size * 17 * z + 12 * z
        val bx = (sx - tw / 2).coerceIn(aire[0] + 6 * z, max(aire[0] + 6 * z, aire[0] + aire[2] - tw - 6 * z))
        val by = (sy - bh - 10 * z).coerceIn(aire[1] + 50 * z, max(aire[1] + 50 * z, aire[1] + aire[3] - bh - 50 * z))
        tl.rrect(bx - 2 * z, by - 2 * z, tw + 4 * z, bh + 4 * z, 8 * z, 0xFF000000.toInt(), null, 0f)
        tl.rrect(bx, by, tw, bh, 7 * z, 0xFFFFFBE8.toInt(), null, 0f)
        val tx = sx.coerceIn(bx + 10 * z, bx + tw - 10 * z)
        tl.poly(floatArrayOf(tx - 6 * z, tx + 6 * z, tx), floatArrayOf(by + bh, by + bh, by + bh + 8 * z), 0xFFFFFBE8.toInt())
        for ((i, l) in ls.withIndex()) tl.texte(l, bx + 10 * z, by + 14 * z + i * 17 * z, 13 * z, 0xFF2B2416.toInt())
    }

    private fun outils(tl: Toile, Z: MutableList<EspaceDessin.Zone>, z: Float) {
        var x = aire[0] + aire[2] - 8 * z; val y = aire[1] + 8 * z
        for (s in listOf("voir", "+", "−")) {
            x -= 40 * z
            tl.rrect(x, y, 36 * z, 36 * z, 9 * z, 0xC805090F.toInt(), 0x46FFFFFF, 1 * z)
            if (s == "voir") { tl.cercle(x + 18 * z, y + 18 * z, 7 * z, EspaceDessin.TEXTE, 1.6f * z)
                for (q in listOf(floatArrayOf(-12f, 0f, -8f, 0f), floatArrayOf(8f, 0f, 12f, 0f), floatArrayOf(0f, -12f, 0f, -8f), floatArrayOf(0f, 8f, 0f, 12f)))
                    tl.ligne(x + 18 * z + q[0] * z, y + 18 * z + q[1] * z, x + 18 * z + q[2] * z, y + 18 * z + q[3] * z, EspaceDessin.TEXTE, 1.6f * z) }
            else tl.texte(s, x + 18 * z, y + 18 * z, 18 * z, EspaceDessin.TEXTE, true, 'c')
            Z.add(EspaceDessin.Zone(x, y, 36 * z, 36 * z, when (s) { "voir" -> "monde:voir"; "+" -> "monde:plus"; else -> "monde:moins" }))
        }
        val i = iso
        if (i != null) {
            val ps = carte!!.parcelles.count { it.type == i }; val n = maison.values.count { it.startsWith("$i/") }
            tl.rrect(aire[0] + 8 * z, y, 96 * z, 36 * z, 9 * z, 0xFF0F2416.toInt(), 0xFF3DFF7C.toInt(), 1 * z)
            tl.texte(t("monde.retour_monde"), aire[0] + 56 * z, y + 18 * z, 13 * z, 0xFF3DFF7C.toInt(), false, 'c')
            Z.add(EspaceDessin.Zone(aire[0] + 8 * z, y, 96 * z, 36 * z, "monde:sortir"))
            tl.texte("${EMOJI[i]} " + Langue.ou("carte.biome.$i", i) + " · " + t("monde.region_n", "p" to ps, "c" to n), aire[0] + 112 * z, y + 18 * z, 12 * z, 0xFFE6F0FF.toInt(), true)
        }
    }

    // ------------------------------------------------------------ le panneau du bas : la liste ou la fiche
    private fun panneau(tl: Toile, Z: MutableList<EspaceDessin.Zone>, z: Float) {
        val (x, y, w, h) = aire.toList()
        val hp = if (feuille) min(h * .62f, 420 * z) else 0f
        val by = y + h - hp - 40 * z
        tl.rrect(x + 8 * z, by, w - 16 * z, 40 * z + hp, 14 * z, 0xF5131C24.toInt(), 0xFF26384A.toInt(), 1.5f * z)
        tl.rrect(x + w / 2 - 22 * z, by + 6 * z, 44 * z, 5 * z, 3 * z, 0xFF26384A.toInt(), null, 0f)
        val titre = if (sel != null && feuille) creas[sel!!]?.info?.nom ?: "" else t("monde.mes_creatures", "n" to equipe.size)
        tl.texte(titre + if (feuille) "  ▾" else "  ▴", x + w / 2, by + 24 * z, 13 * z, 0xFFFFD866.toInt(), true, 'c')
        Z.add(EspaceDessin.Zone(x + 8 * z, by, w - 16 * z, 40 * z + hp, "monde:panneau"))
        Z.add(EspaceDessin.Zone(x + 8 * z, by, w - 16 * z, 40 * z, "monde:poignee"))
        if (!feuille) return
        val r = floatArrayOf(x + 8 * z, by + 40 * z, w - 16 * z, hp)
        val s = sel
        if (s != null && creas[s] != null) fiche(tl, Z, r, creas.getValue(s).info, z) else liste(tl, Z, r, z)
    }

    private fun vignette(tl: Toile, e: Info, cx: Float, pieds: Float, haut: Float) {
        val al = e.album
        if (al != null) tl.cadre(al.image("assis", 0), cx, pieds, haut / max(1, al.ref), false, al.lisse)
        else tl.ellipse(cx, pieds - haut / 2, haut / 3, haut / 2.4f, a(COUL[e.type] ?: 0x888888, 255))
    }

    fun cmdAgrandir(tid: String): String {
        val n = carte?.parcelles?.count { it.type == tid } ?: 0
        return if (n > 0) "mkdir biome/$tid/parcelle_${n + 1}" else "mkdir -p biome/$tid/parcelle_1"
    }

    private fun liste(tl: Toile, Z: MutableList<EspaceDessin.Zone>, r: FloatArray, z: Float) {
        val (x, y, w, h) = r.toList()
        var yy = y + 4 * z
        val ref = equipe.filter { it.id in refuge }
        if (ref.isNotEmpty()) {
            val hb = 26 * z + 30 * z * min(3, ref.size)
            tl.rrect(x + 10 * z, yy, w - 20 * z, hb, 8 * z, 0xFF282414.toInt(), 0xC8A88C3C.toInt(), 1 * z)
            tl.texte("🏠 " + t("monde.refuge", "n" to ref.size), x + 20 * z, yy + 13 * z, 11.5f * z, 0xFFFFD866.toInt(), true)
            for ((i, e) in ref.take(3).withIndex()) { val ly = yy + 26 * z + 30 * z * i
                vignette(tl, e, x + 32 * z, ly + 26 * z, 24 * z)
                tl.texte(e.nom, x + 52 * z, ly + 14 * z, 12 * z, EspaceDessin.TEXTE)
                tl.texte(cmdAgrandir(e.type), x + w - 18 * z, ly + 14 * z, 10 * z, EspaceDessin.VERT, false, 'd', true)
                Z.add(EspaceDessin.Zone(x + 10 * z, ly, w - 20 * z, 28 * z, "monde:crea:" + e.id)) }
            yy += hb + 8 * z
        }
        val col = max(1, ((w - 20 * z) / (62 * z)).toInt())
        for (tid in Monde.TYPES) {
            val es = equipe.filter { it.type == tid }; val ps = carte?.parcelles?.count { it.type == tid } ?: 0
            if (es.isEmpty() && ps == 0) continue
            if (yy + 50 * z > y + h) break
            val n = es.count { it.id in maison }
            tl.rrect(x + 10 * z, yy, w - 20 * z, 22 * z, 11 * z, a(COUL[tid] ?: 0x888888, 60), a(COUL[tid] ?: 0x888888, 170), 1 * z)
            tl.texte("${EMOJI[tid]} " + Langue.ou("carte.biome.$tid", tid), x + 20 * z, yy + 11 * z, 12 * z, EspaceDessin.TEXTE, true)
            tl.texte("$n/$ps", x + w - 20 * z, yy + 11 * z, 11.5f * z, EspaceDessin.DOUX, false, 'd')
            Z.add(EspaceDessin.Zone(x + 10 * z, yy, w - 20 * z, 22 * z, "monde:region:$tid"))
            yy += 28 * z
            for ((i, e) in es.withIndex()) {
                val cx = x + 10 * z + (i % col) * 62 * z; val cy = yy + (i / col) * 60 * z
                if (cy + 56 * z > y + h) break
                val s = sel == e.id
                tl.rrect(cx + 2 * z, cy, 56 * z, 56 * z, 8 * z, if (s) 0x283DDC84 else 0xFF18242E.toInt(), if (s) 0xFF3DDC84.toInt() else if (e.id in refuge) 0xC8A88C3C.toInt() else 0xFF26384A.toInt(), 1.3f * z)
                vignette(tl, e, cx + 30 * z, cy + 39 * z, 30 * z)
                tl.texte(e.nom.take(8), cx + 30 * z, cy + 49 * z, 10 * z, EspaceDessin.TEXTE, false, 'c')
                Z.add(EspaceDessin.Zone(cx + 2 * z, cy, 56 * z, 56 * z, "monde:crea:" + e.id))
            }
            if (es.isNotEmpty()) yy += ((es.size + col - 1) / col) * 60 * z + 6 * z
        }
        if (yy + 30 * z < y + h) for ((i, l) in couper(tl, t("monde.toucher"), w - 30 * z, 11.5f * z).take(3).withIndex())
            tl.texte(l, x + 14 * z, yy + 12 * z + i * 15 * z, 11.5f * z, EspaceDessin.DOUX)
    }

    private fun fiche(tl: Toile, Z: MutableList<EspaceDessin.Zone>, r: FloatArray, e: Info, z: Float) {
        val (x, y, w, h) = r.toList()
        tl.rrect(x + 10 * z, y + 4 * z, 150 * z, 30 * z, 8 * z, 0xFF0F2416.toInt(), 0xFF3DFF7C.toInt(), 1 * z)
        tl.texte(t("monde.retour_liste"), x + 85 * z, y + 19 * z, 12.5f * z, 0xFF3DFF7C.toInt(), false, 'c')
        Z.add(EspaceDessin.Zone(x + 10 * z, y + 4 * z, 150 * z, 30 * z, "monde:liste_retour"))
        val iy = y + 44 * z
        tl.rrect(x + 14 * z, iy, 90 * z, 90 * z, 10 * z, 0xFF18242E.toInt(), 0xFF26384A.toInt(), 1.5f * z)
        RARETE[e.rarete]?.let { tl.lueur(x + 59 * z, iy + 50 * z, 44 * z, a(it, 90)) }
        vignette(tl, e, x + 59 * z, iy + 84 * z, 72 * z)
        val tx = x + 116 * z
        tl.texte(e.nom, tx, iy + 14 * z, 15 * z, EspaceDessin.TEXTE, true)
        tl.texte(e.sous, tx, iy + 34 * z, 11.5f * z, EspaceDessin.DOUX)
        e.rarete?.let { rr -> val c = RARETE[rr] ?: 0x9AA3AD; val txt = rr.uppercase() + if (e.shiny) " ✦ SHINY" else ""
            tl.rrect(tx, iy + 46 * z, tl.mesure(txt, 10 * z, true) + 14 * z, 18 * z, 4 * z, null, a(c, 255), 1.5f * z)
            tl.texte(txt, tx + 7 * z, iy + 55 * z, 10 * z, a(c, 255), true) }
        val nomT = Langue.ou("carte.biome.${e.type}", e.type)
        tl.rrect(tx, iy + 70 * z, tl.mesure(nomT, 11.5f * z) + 34 * z, 20 * z, 10 * z, a(COUL[e.type] ?: 0x888888, 70), a(COUL[e.type] ?: 0x888888, 200), 1 * z)
        tl.texte("${EMOJI[e.type]} $nomT", tx + 8 * z, iy + 80 * z, 11.5f * z, EspaceDessin.TEXTE)
        var yy = iy + 104 * z
        tl.rrect(x + 10 * z, yy, w - 20 * z, 54 * z, 8 * z, 0xFF18242E.toInt(), 0xFF26384A.toInt(), 1 * z)
        val m = maison[e.id]
        if (m != null) { tl.texte("✓ " + t("monde.habite"), x + 20 * z, yy + 16 * z, 12 * z, EspaceDessin.VERT)
            tl.texte("~/terrain_terminagotchi/biome/$m/", x + 20 * z, yy + 36 * z, 10.5f * z, EspaceDessin.TEXTE, false, 'g', true) }
        else { val n = carte?.parcelles?.count { it.type == e.type } ?: 0
            for ((i, l) in couper(tl, "⏳ " + t("monde.attend", "region" to nomT, "n" to n), w - 40 * z, 11 * z).take(2).withIndex())
                tl.texte(l, x + 20 * z, yy + 12 * z + i * 13 * z, 11 * z, 0xFFFFD866.toInt())
            tl.texte(cmdAgrandir(e.type), x + 20 * z, yy + 42 * z, 11 * z, EspaceDessin.VERT, false, 'g', true) }
        yy += 64 * z
        for (l in couper(tl, e.fiche, w - 30 * z, 12 * z)) { if (yy + 14 * z > y + h) break
            tl.texte(l, x + 15 * z, yy + 8 * z, 12 * z, EspaceDessin.DOUX); yy += 16 * z }
    }

    // ------------------------------------------------------------ les touchers
    /** Un toucher (a : l'action de la zone, ou « monde:vue » = à côté). Renvoie true s'il est pris. */
    fun toucher(a: String, x: Float = 0f, y: Float = 0f): Boolean {
        when {
            a == "monde:vue" -> {
                if (feuille || sel != null) { feuille = false; sel = null; return true }   // un toucher à côté : tout se referme
                if (iso != null) { sortir(); return true }
                val h = hexSous(x, y)
                if (h?.region != null) isoler(h.region!!)
                return true
            }
            a == "monde:panneau" -> return true
            a == "monde:poignee" -> { feuille = !feuille; if (!feuille) sel = null; return true }
            a.startsWith("monde:crea:") -> { val i = a.removePrefix("monde:crea:"); sel = if (sel == i && feuille) null else i; feuille = true
                creas[i]?.let { cr -> if (cr.at != null) { cr.pop = t + .6; val p = posCrea(cr); eclat(p[0], p[1] - 30, 1, 3) } }; return true }
            a == "monde:liste_retour" -> { sel = null; return true }
            a.startsWith("monde:region:") -> { isoler(a.removePrefix("monde:region:")); feuille = false; return true }
            a == "monde:sortir" -> { sortir(); return true }
            a == "monde:voir" -> { iso = null; toutVoir(); return true }
            a == "monde:plus" -> { zoomer(1); return true }
            a == "monde:moins" -> { zoomer(-1); return true }
        }
        return false
    }

    fun retour(): Boolean { if (sel != null || feuille) { sel = null; feuille = false; return true }; if (iso != null) { sortir(); return true }; return false }
    fun zoomer(sens: Int) { but = null; manuel = true; cam[2] = (cam[2] * (if (sens > 0) 1.3 else 1 / 1.3)).coerceIn(.5 * z0, 7.0 * z0) }
    fun glisser(dx: Float, dy: Float) { but = null; manuel = true; cam[0] -= dx / cam[2]; cam[1] -= dy / cam[2] }
    private fun isoler(tid: String) { val hs = carte?.hex?.values?.filter { it.region == tid } ?: return; if (hs.isEmpty()) return
        iso = tid; manuel = true; ajuster(hs, true, 3.4); but?.let { it[1] -= 26 * z0 / it[2] } }
    private fun sortir() { iso = null; toutVoir() }
    private fun hexSous(sx: Float, sy: Float): Monde.Hex? {
        val wx = mondeX(sx); val wy = mondeY(sy)
        for (h in ordre.asReversed()) { val s = sommet(h); val dx = wx - s[0]; val dy = wy - s[1]
            if (MondeDessin.hexInside(dx, dy) || (abs(dx) <= Monde.HR && dy > 0 && dy <= MondeDessin.hexBottom(dx) + h.mur)) return h }
        return null
    }

    // ------------------------------------------------------------ chaque effet (1 à 2 s)
    private fun etiquette(tl: Toile, txt: String, sx: Float, sy: Float, c: Int, fin: Double, monte: Boolean, age: Double, z: Float) {
        val yy = sy - (if (monte) (age * 26 * z).toFloat() else 0f)
        val tw = tl.mesure(txt, 12.5f * z, true) + 16 * z
        tl.rrect(sx - tw / 2, yy - 11 * z, tw, 22 * z, 6 * z, a(0x05090F, (220 * fin).toInt()), a(c, (255 * fin).toInt()), 1 * z)
        tl.texte(txt, sx, yy, 12.5f * z, a(c, (255 * fin).toInt()), true, 'c')
    }

    private fun effet(tl: Toile, ef: Effet, age: Double, z: Float) {
        val e = ef.e; val ty = e.getString("type"); val zz = cam[2].toFloat()
        val k = (age / ef.du).coerceIn(0.0, 1.0); val fin = 1 - k
        val pts = ef.pts
        val p0 = pts.firstOrNull()?.let { floatArrayOf(ecranX(it[0]), ecranY(it[1])) }
        val J = 0xFFD54F; val V = 0x3DDC84; val R = 0xFF5F6D; val C = 0x4DD0E1; val VI = 0xB284FF
        fun eti(txt: String, x: Float, y: Float, c: Int, monte: Boolean = true) = etiquette(tl, txt, x, y, c, fin, monte, age, z)
        when (ty) {
            "jokers" -> { for (p in pts) { val sx = ecranX(p[0]); val sy = ecranY(p[1])
                    tl.lueur(sx, sy - 10 * zz, 30 * zz, a(0xFFEC80, (170 * sin(k * PI)).toInt())); tl.cercle(sx, sy - 10 * zz, ((12 + 6 * k) * zz).toFloat(), a(0xFFE066, (255 * fin).toInt()), 1.6f * z) }
                p0?.let { eti("✱ " + e.optInt("n", pts.size), it[0], it[1] - 40 * zz, J) } }
            "dossier+" -> { if (age < .06) for (p in pts) eclat(p[0], p[1] - 40, 0, 16)
                p0?.let { eti("+ " + e.optString("chemin").substringAfterLast('/') + "/", it[0], it[1] - 30 * zz, V) } }
            "dossier-" -> { if (age < .06 && pts.isNotEmpty()) eclat(pts[0][0], pts[0][1], 0, 20)
                p0?.let { eti("− " + e.optString("chemin").substringAfterLast('/') + "/", it[0], it[1] - 30 * zz, R) } }
            "objet+" -> { val p = p0 ?: return
                val nom = e.optString("chemin").substringAfterLast('/')
                val im = MondeDessin.decor(Monde.deco(nom, if (e.isNull("region")) "plante" else e.optString("region", "plante")).first)
                val q = (age / .8).coerceIn(0.0, 1.0)
                val via = e.optString("via")
                var yy = p[1]
                when (via) {
                    "touch", "autre", "mkdir" -> { tl.rect(p[0] - 5 * zz, p[1] - 140 * zz, 10 * zz, 140 * zz, a(0xFFF6B0, (110 * sin(min(1.0, age / .6) * PI)).toInt()))
                        if (q < 1) yy = p[1] - ((1 - easeBack(q)) * 70 * zz).toFloat() }
                    "ecrire" -> for (i in 0 until 3) { val qq = (q * 1.3 - i * .12).coerceIn(0.0, 1.0)
                        tl.rect(aire[0] + 20 * z + (p[0] - aire[0] - 20 * z) * ease(qq).toFloat() - 8 * z, aire[1] + 20 * z + (p[1] - aire[1] - 50 * z) * ease(qq).toFloat(), 8 * zz, 2 * zz, a(0x5FAFFF, (255 * (1 - qq * .7)).toInt())) }
                    "messager" -> { pigeon(tl, p[0] + ((1 - q) * 140 * zz).toFloat(), p[1] - ((1 - q) * 110 * zz).toFloat() - 20 * zz, zz, age); yy = p[1] - ((1 - q) * 40 * zz).toFloat() }
                    else -> yy = p[1] - ((1 - easeBack(q)) * 50 * zz).toFloat()
                }
                if (q > .05) tl.cadre(im, p[0], yy + 2 * zz, zz * (q * 1.5).toFloat().coerceIn(.3f, 1f), false, false)
                if (age > .8) eti(t("efx.nouveau"), p[0], p[1] - (im.h + 8) * zz, V) }
            "objet-" -> { if (age < .06 && pts.isNotEmpty()) eclat(pts[0][0], pts[0][1] - 8, 2, 26); p0?.let { eti(t("efx.pas_corbeille"), it[0], it[1] - 30 * zz, R) } }
            "touche", "modifie" -> p0?.let { eti(if (ty == "touche") "🕒 " + t("efx.heure") else "✎", it[0], it[1] - 34 * zz, C, false) }
            "deplace", "renomme", "copie" -> { if (pts.size < 2) return
                val x0 = ecranX(pts[0][0]); val y0 = ecranY(pts[0][1]); val x1 = ecranX(pts[1][0]); val y1 = ecranY(pts[1][1])
                val q = (age / 1.0).coerceIn(0.0, 1.0)
                for (i in 0 until 12) { val a1 = i / 12.0; val b1 = (i + .5) / 12
                    tl.ligne((x0 + (x1 - x0) * a1).toFloat(), (y0 + (y1 - y0) * a1 - sin(a1 * PI) * 50 * zz).toFloat(), (x0 + (x1 - x0) * b1).toFloat(), (y0 + (y1 - y0) * b1 - sin(b1 * PI) * 50 * zz).toFloat(), a(J, (220 * fin).toInt()), 1.5f * z) }
                val vers = e.optString("vers"); val im = MondeDessin.decor(Monde.deco(vers.substringAfterLast('/'), vers.split("/").getOrElse(1) { "plante" }).first)
                val bx = (x0 + (x1 - x0) * ease(q)).toFloat(); val by = (y0 + (y1 - y0) * ease(q) - sin(q * PI) * 50 * zz).toFloat()
                if (ty == "copie") { tl.lueur(x0, y0 - 10 * zz, 40 * zz, a(0xFFFFFF, (220 * max(0.0, 1 - age * 3)).toInt())); tl.cadre(im, x0, y0 + 2 * zz, zz, false, false) }
                if (q < 1 || ty != "copie") tl.cadre(im, bx, by + 2 * zz, zz, false, false)
                if (ty == "renomme") eti(e.optString("de").substringAfterLast('/') + " → " + vers.substringAfterLast('/'), x1, y1 - 34 * zz, J, false)
                else if (ty == "copie") eti("⧉ " + t("efx.copie"), x1, y1 - 34 * zz, C) }
            "ecrit" -> { val p = p0 ?: return
                val ajoute = e.optString("mode") == ">>"
                if (!ajoute && age < .6) for (i in 0 until 3) tl.rect(p[0] - 8 * zz + i * 3, p[1] - 20 * zz - (age * 120).toFloat() - i * 10, 8 * zz, 1.6f * zz, a(R, (255 * (1 - age / .6)).toInt()))
                val q = ((age - (if (ajoute) 0.0 else .4)) / .7).coerceIn(0.0, 1.0)
                tl.rect(aire[0] + 20 * z + (p[0] - aire[0] - 20 * z) * ease(q).toFloat() - 8 * z, aire[1] + 20 * z + (p[1] - 20 * zz - aire[1] - 20 * z) * ease(q).toFloat(), 16 * z, 4 * z, a(0x5FAFFF, (255 * (1 - q * .5)).toInt()))
                eti(if (ajoute) "» " + t("efx.ajoute") else "> " + t("efx.efface"), p[0], p[1] - 40 * zz, if (ajoute) 0x5FAFFF else R, false) }
            "droits" -> { val p = p0 ?: return
                val av = e.optInt("avant"); val ap = e.optInt("apres"); val q = (age / .5).coerceIn(0.0, 1.0)
                val cy = p[1] - 16 * zz - ((1 - easeBack(q)) * 40 * zz).toFloat()
                tl.ellipse(p[0], cy, 30 * zz, 34 * zz, a(0xC8E6FF, (50 * fin + 20).toInt())); tl.cercle(p[0], cy, 30 * zz, a(0xDCF0FF, (200 * fin + 40).toInt()), 1.5f * z)
                for ((i, bit) in listOf(128, 16, 2).withIndex()) { val ouvert = ((if (age > .7) ap else av) and bit) != 0
                    cadenas(tl, p[0] + (i - 1) * 22 * zz, p[1] - 58 * zz, 6 * zz, if (ouvert) V else R, ouvert)
                    tl.texte(listOf("🙂", "👥", "🌍")[i], p[0] + (i - 1) * 22 * zz, p[1] - 72 * zz, 9 * z, EspaceDessin.TEXTE, false, 'c') } }
            "refus" -> { val p = p0 ?: floatArrayOf(aire[0] + aire[2] / 2, aire[1] + aire[3] / 2)
                val b = (abs(sin(age * 9)) * 14 * zz * fin).toFloat()
                when (e.optString("raison")) {
                    "droits" -> { cadenas(tl, p[0], p[1] - 30 * zz - b, 8 * zz, R, false); tl.cercle(p[0], p[1] - 16 * zz, 30 * zz, a(0xDCF0FF, (160 * fin).toInt()), 1.5f * z) }
                    "pas_vide" -> eti(t("efx.pas_vide"), p[0] + (sin(age * 40) * 4 * fin).toFloat(), p[1] - 30 * zz, J, false)
                    "existe" -> eti(t("efx.existe"), p[0], p[1] - 34 * zz, J, false)
                    else -> tl.texte("?", p[0], p[1] - 30 * zz - b, 26 * z, a(R, (255 * fin).toInt()), true, 'c')
                } }
            "cd" -> { if (pts.size < 2) return
                val x0 = ecranX(pts[0][0]); val y0 = ecranY(pts[0][1]); val x1 = ecranX(pts[1][0]); val y1 = ecranY(pts[1][1])
                val q = ease((age / .9).coerceIn(0.0, 1.0))
                val bx = (x0 + (x1 - x0) * q).toFloat(); val by = (y0 + (y1 - y0) * q - sin(q * PI) * 60 * zz).toFloat()
                tl.lueur(bx, by, 22 * zz, a(J, 120)); tl.ellipse(bx, by, 5 * zz, 5 * zz, a(J, 255)); tl.cercle(bx, by, ((11 + 3 * sin(age * 8)) * zz).toFloat(), a(J, 255), 1.6f * z)
                if (age > .9) eti("◉ " + t("efx.ici"), x1, y1 - 28 * zz, J, false) }
            "pwd" -> { val p = p0 ?: return
                val parts = (listOf("~", "terrain_terminagotchi") + e.optString("chemin").split("/").filter { it.isNotEmpty() }).takeLast(4)
                var xx = p[0] - parts.sumOf { (tl.mesure(it, 12 * z, false, true) + 26 * z).toDouble() }.toFloat() / 2
                for ((i, nom) in parts.withIndex()) { val q = ((age - i * .15) / .3).coerceIn(0.0, 1.0); if (q <= 0) break
                    val tw = tl.mesure(nom, 12 * z, false, true) + 14 * z
                    tl.rrect(xx, p[1] - 60 * zz - 11 * z, tw, 22 * z, 6 * z, a(0x05090F, (230 * q * fin + 20).toInt()), a(C, (255 * q * fin).toInt()), 1 * z)
                    tl.texte(nom, xx + tw / 2, p[1] - 60 * zz, 12 * z, a(C, (255 * q * fin).toInt()), false, 'c', true); xx += tw
                    if (i < parts.size - 1) { tl.texte("/", xx + 6 * z, p[1] - 60 * zz, 13 * z, a(VI, (255 * q * fin).toInt()), true, 'c', true); xx += 12 * z } } }
            "ls" -> { val c = carte!!; val ch = e.optString("chemin"); val h = hexDe(ch)
                val cible = mutableListOf<DoubleArray>()
                if (h != null) { val p = c.par[h.parcelle]
                    if (p != null && ch.count { it == '/' } >= 2) for (v in p.poses.values) c.at(p.centre[0] + v.oq, p.centre[1] + v.or_)?.let { cible.add(sommet(it)) }
                    else { val ty2 = ch.split("/").getOrNull(1); for (x in c.parcelles) if (ty2 == null || x.type == ty2) c.at(x.centre[0], x.centre[1])?.let { cible.add(sommet(it)) } } }
                for ((i, pt) in cible.take(16).withIndex()) { val q = ((age - i * .1) / .5).coerceIn(0.0, 1.0)
                    if (q > 0 && q < 1) tl.lueur(ecranX(pt[0]), ecranY(pt[1]) - 6 * zz, 28 * zz, a(0xFFFAD2, (150 * sin(q * PI)).toInt())) }
                val p = p0 ?: return
                if (e.optBoolean("caches")) { val w2 = 40 * zz * (1 - min(1.0, age / .8)).toFloat()
                    tl.rect(p[0] - 40 * zz, p[1] - 60 * zz, w2, 50 * zz, a(0x7846C8, (200 * fin).toInt())); tl.rect(p[0] + 40 * zz - w2, p[1] - 60 * zz, w2, 50 * zz, a(0x7846C8, (200 * fin).toInt()))
                    eti("👁 " + t("efx.caches"), p[0], p[1] - 70 * zz, VI, false) }
                else eti("ls · " + e.optInt("n", cible.size), p[0], p[1] - 40 * zz, 0xFFFAD2, false) }
            "find" -> { val c0 = pointDe(e.optString("chemin", "biome")).let { floatArrayOf(ecranX(it[0]), ecranY(it[1])) }
                val rmax = 260 * zz
                tl.cercle(c0[0], c0[1], (rmax * k).toFloat() + 5, a(C, (220 * fin).toInt()), 2 * z)
                if (e.optInt("n") > 0) for (p in pts) { val sx = ecranX(p[0]); val sy = ecranY(p[1])
                    if (Math.hypot((sx - c0[0]).toDouble(), (sy - c0[1]).toDouble()) <= rmax * k + 5) { tl.rect(sx - 1.5f, sy - 60 * zz, 3f, 50 * zz, a(C, (200 * fin).toInt())); tl.lueur(sx, sy - 6 * zz, 18 * zz, a(C, (160 * fin).toInt())) } }
                eti(if (e.optInt("n") > 0) t("efx.trouves", "n" to e.optInt("n")) else t("efx.rien_trouve"), c0[0], c0[1] - 50 * zz, C, false) }
            "lire" -> { val p = p0 ?: return
                val q = (age / .6).coerceIn(0.0, 1.0); val w2 = 150 * z; val h2 = (18 + 52 * ease(q)).toFloat() * z
                val bx = p[0] - w2 / 2; val by = p[1] - 50 * zz - h2
                tl.rrect(bx, by, w2, h2, 4 * z, a(0xF3E2B8, (255 * fin + 40).toInt().coerceAtMost(255)), 0xFF7B5534.toInt(), 1 * z)
                val ls = e.optJSONArray("lignes")
                if (ls != null) for (i in 0 until min(3, ls.length())) if (18 * z + i * 16 * z < h2) tl.texte(ls.getString(i).take(22), bx + 8 * z, by + 14 * z + i * 16 * z, 11 * z, a(0x3B2414, (255 * fin).toInt()), false, 'g', true) }
            "groupe" -> { val moins = e.optString("sorte").endsWith("-")
                if (age < .06) for (p in pts.take(6)) eclat(p[0], p[1], if (moins) 2 else 0, 10)
                p0?.let { eti((if (moins) "− " else "+ ") + e.optInt("n"), it[0], it[1] - 40 * zz, if (moins) R else V) } }
            "lucioles" -> { val p = p0 ?: return
                for (i in 0 until 5) { val an = t * 1.4 + i * 2 * PI / 5
                    var fx = p[0] + (cos(an) * 34 * zz).toFloat(); var fy = p[1] - 40 * zz + (sin(an * 1.3) * 14 * zz).toFloat()
                    if (e.optString("quoi") == "eteint" && i == 0 && e.optBoolean("ok")) { fy += (age * age * 60).toFloat(); tl.texte("z Z", fx + 8 * z, fy - 8 * z, 10 * z, a(0xFFFFFF, (255 * fin).toInt())) }
                    if (e.optString("quoi") == "part" && i == 0) { fx += (age * 140 * zz).toFloat(); fy -= (age * 80 * zz).toFloat() }
                    tl.lueur(fx, fy, 9 * zz, a(0xD9FF6B, (200 * fin).toInt())); tl.ellipse(fx, fy, 1.6f * zz, 1.6f * zz, a(0xF0FFB4, (255 * fin).toInt())) }
                if (!e.optBoolean("ok")) eti(t("efx.aucune_luciole"), p[0], p[1] - 70 * zz, J, false) }
            "messager" -> { if (pts.size < 2) return
                val x0 = ecranX(pts[0][0]); val y0 = ecranY(pts[0][1]); val x1 = ecranX(pts[1][0]); val y1 = ecranY(pts[1][1])
                val q = age / ef.du; val qq = if (q < .5) q * 2 else 2 - q * 2
                pigeon(tl, (x0 + (x1 - x0) * ease(qq)).toFloat(), (y0 - 40 * zz + (y1 - y0) * ease(qq) - sin(qq * PI) * 40 * zz).toFloat(), zz, age)
                if (q > .5) eti(if (e.optBoolean("ok")) t("efx.pong") else "? ? ?", x0, y0 - 70 * zz, if (e.optBoolean("ok")) V else R, false) }
            "photo" -> { if (age < .3) tl.rect(aire[0], aire[1], aire[2], aire[3], a(0xFFFFFF, (220 * (1 - age / .3)).toInt()))
                p0?.let { eti("📸 " + t("efx.photo"), it[0], it[1] - 60 * zz, 0xFFFFFF, false) } }
            "empreinte" -> { val p = p0 ?: return
                for (i in 0 until 5) tl.cercle(p[0], p[1] - 24 * zz, ((3 + i * 3) * zz * min(1.0, age / .4)).toFloat(), a(VI, (220 * fin).toInt()), 1.3f * z)
                eti("🔏 " + e.optString("cmd"), p[0], p[1] - 54 * zz, VI, false) }
            "tuyau" -> { val p = p0 ?: return
                val et = e.optJSONArray("etapes")?.let { j -> (0 until j.length()).map { j.getString(it) } } ?: emptyList()
                val tot = et.sumOf { (tl.mesure(it, 11 * z, true, true) + 30 * z).toDouble() }.toFloat()
                var xx = p[0] - tot / 2; val yy = p[1] - 80 * zz
                tl.rrect(xx - 8 * z, yy - 16 * z, tot + 16 * z, 32 * z, 8 * z, a(0x140C24, (230 * fin).toInt()), a(VI, (255 * fin).toInt()), 1 * z)
                for ((i, c) in et.withIndex()) { val tw = tl.mesure(c, 11 * z, true, true) + 14 * z; val on = (age * 4).toInt() % max(1, et.size) == i
                    tl.rrect(xx, yy - 10 * z, tw, 20 * z, 6 * z, a(VI, ((if (on) 140 else 60) * fin).toInt()), null, 0f)
                    tl.texte(c, xx + tw / 2, yy, 11 * z, a(0xFFFFFF, (255 * fin).toInt()), true, 'c', true); xx += tw
                    if (i < et.size - 1) { tl.texte("|", xx + 8 * z, yy, 12 * z, a(VI, (255 * fin).toInt()), true, 'c', true); xx += 16 * z } } }
            else -> effet2(tl, ef, age, z, fin) { s, x, y, c -> eti(s, x, y, c, false) }
        }
    }

    // ------------------------------------------------------------ les effets secondaires et ceux des mondes (monde.py _effet2)
    private fun octets(n: Long): String = when {
        n < 1024 -> t("efx.taille_o", "n" to n)
        n < 1024 * 1024 -> t("efx.taille_ko", "n" to max(1L, (n / 1024.0 + .5).toLong()))
        else -> t("efx.taille_mo", "n" to max(1L, (n / 1048576.0 + .5).toLong()))
    }

    private fun effet2(tl: Toile, ef: Effet, age: Double, z: Float, fin: Double, eti: (String, Float, Float, Int) -> Unit) {
        val e = ef.e; val ty = e.getString("type"); val zz = cam[2].toFloat()
        val pts = ef.pts.map { floatArrayOf(ecranX(it[0]), ecranY(it[1])) }
        val p0 = pts.firstOrNull() ?: return
        val x = p0[0]; val y = p0[1]; val al = (255 * fin).toInt()
        val J = 0xFFD54F; val V = 0x3DDC84; val R = 0xFF5F6D; val C = 0x4DD0E1; val VI = 0xB284FF; val OR = 0xFF9F43; val BOIS = 0xC9A26A
        fun n(k: String) = e.optInt(k)
        when (ty) {
            "caisse" -> { val quoi = e.optString("quoi")
                val ouvert = when (quoi) { "ferme" -> max(0.0, 1 - (age - 1.0) * 3); "ouvre", "voir" -> min(1.0, age * 3); else -> 0.0 }.toFloat()
                val s2 = if (quoi == "serre") (1 - .45 * ((age - .2) / .6).coerceIn(0.0, 1.0)).toFloat() else 1f
                for ((i, p) in pts.drop(1).take(8).withIndex()) {
                    val q = ((age - i * .12) / .8).coerceIn(0.0, 1.0)
                    val (sx, sy, tx, ty2) = if (quoi == "ouvre") listOf(x, y - 20 * zz, p[0], p[1]) else listOf(p[0], p[1], x, y - 20 * zz)
                    val bx = sx + (tx - sx) * ease(q).toFloat(); val by = sy + (ty2 - sy) * ease(q).toFloat() - (sin(q * PI) * 40 * zz).toFloat()
                    if (q > 0 && q < 1) { tl.lueur(bx, by - 6 * zz, 10 * zz, a(0xFFF6C8, 200)); tl.rect(bx - 3 * zz, by - 9 * zz, 6 * zz, 6 * zz, a(0xF3E2B8, 230)) }
                }
                caisse(tl, x, y - 6 * zz, 26 * zz * s2, ouvert, al)
                eti("📦 " + when (quoi) { "ferme" -> t("efx.caisse.ferme", "n" to n("n")); "ouvre" -> t("efx.caisse.ouvre", "n" to n("n"))
                    "serre" -> t("efx.caisse.serre"); else -> t("efx.caisse.voir", "n" to n("n")) }, x, y - 44 * zz, BOIS) }
            "lien" -> { val b = pts.getOrNull(1) ?: floatArrayOf(x + 90, y - 70)
                val q = (age / .8).coerceIn(0.0, 1.0); val mx = (x + b[0]) / 2; val my = min(y, b[1]) - 60 * zz
                val mort = e.optBoolean("mort"); val coul = if (mort) a(0x969CAA, al) else a(J, al)
                val nn = 14
                fun bez(u: Double, a0: Float, m: Float, b0: Float) = ((1 - u) * (1 - u) * a0 + 2 * (1 - u) * u * m + u * u * b0).toFloat()
                for (i in 0 until (nn * q).toInt()) {
                    if (mort && (i == nn / 2 || i == nn / 2 + 1)) continue
                    val u0 = i.toDouble() / nn; val u1 = (i + 1.0) / nn
                    val x0 = bez(u0, x, mx, b[0]); val y0 = bez(u0, y - 26 * zz, my, b[1] - 10 * zz); val x1 = bez(u1, x, mx, b[0]); val y1 = bez(u1, y - 26 * zz, my, b[1] - 10 * zz)
                    if (!mort) tl.ligne(x0, y0, x1, y1, a(J, (70 * fin).toInt()), 6 * z)
                    tl.ligne(x0, y0, x1, y1, coul, 2.2f * z)
                }
                tl.rect(x - 1.5f * zz, y - 26 * zz, 3 * zz, 22 * zz, a(0x8A5A30, al)); tl.rrect(x - 16 * zz, y - 34 * zz, 32 * zz, 11 * zz, 2 * zz, a(0xF1E3C0, al), a(0x5A381E, al), 1 * z)
                if (q >= 1 && !mort) tl.cercle(b[0], b[1] - 10 * zz, 14 * zz, a(J, al), 2 * z)
                val fin2 = if (mort) t("efx.lien_mort") else if (e.optBoolean("dehors")) t("efx.lien_dehors") else (if (e.isNull("cible")) "" else e.optString("cible")).substringAfterLast('/')
                eti("🔗 " + e.optString("chemin").substringAfterLast('/') + " → " + fin2, mx, my - 6 * zz, if (mort) 0x969CAA else J) }
            "taille" -> { val els = e.optJSONArray("elements") ?: return
                val vs = (0 until els.length()).map { els.getJSONArray(it).getLong(1) }
                val hm = max(1L, vs.maxOrNull() ?: 1L)
                for ((i, v) in vs.withIndex()) { val p = pts.getOrNull(i + 1) ?: p0
                    val h2 = ((14 + 70.0 * v / hm) * zz * ((age - i * .15) / .5).coerceIn(0.0, 1.0)).toFloat()
                    tl.rect(p[0] - 7 * zz, p[1] - 14 * zz - h2, 14 * zz, h2, a(OR, (225 * fin).toInt())); tl.rrect(p[0] - 7 * zz, p[1] - 14 * zz - h2, 14 * zz, h2, 1f, null, a(0x1E1E2E, al), 1 * z)
                    if (h2 > 2) eti(octets(v), p[0], p[1] - 26 * zz - h2, OR) } }
            "disque", "memoire" -> { val pc = if (e.isNull("pourcent")) null else e.optInt("pourcent")
                val f2 = ((pc ?: 0) / 100.0 * (age / .8).coerceIn(0.0, 1.0)).toFloat()
                val bx = x + 26 * zz; val by = y - 96 * zz; val bw = 34 * zz; val bh = 70 * zz
                if (ty == "disque") {
                    tl.rrect(bx, by, bw, bh, 6 * zz, a(0x141720, (235 * fin).toInt()), a(C, al), 2 * z)
                    tl.rect(bx + 3 * zz, by + bh - 3 * zz - (bh - 6 * zz) * f2, bw - 6 * zz, (bh - 6 * zz) * f2, a(C, (200 * fin).toInt()))
                    eti("💾 " + (if (pc != null) t("efx.disque", "p" to pc) else t("efx.disque_inconnu")), bx + bw / 2, by - 14 * zz, C)
                } else {
                    val bw2 = 76 * zz
                    tl.rect(bx - 4 * zz, by + 20 * zz, bw2 + 8 * zz, 46 * zz, a(0x6B4424, al)); tl.rect(bx, by + 24 * zz, bw2, 38 * zz, a(0x3A2A1A, al))
                    val cols = listOf(OR, C, VI, V)
                    for (i in 0 until 8) tl.rect(bx + 3 * zz + i * 9.2f * zz, by + 28 * zz + (i % 3) * 1.5f * zz, 7 * zz, 30 * zz - (i % 3) * 1.5f * zz,
                        if (i < Math.round(f2 * 8)) a(cols[i % 4], al) else a(0xFFFFFF, (30 * fin).toInt()))
                    eti("🧠 " + (if (pc != null) t("efx.memoire", "p" to pc) else t("efx.memoire_inconnu")), bx + bw2 / 2, by + 6 * zz, OR)
                } }
            "arbre" -> { val c = carte
                if (c != null) for ((i, p) in c.parcelles.withIndex()) { val q = ((age - .15 - (i % 2) * .35) / .5).coerceIn(0.0, 1.0)
                    if (q > 0 && q < 1) c.at(p.centre[0], p.centre[1])?.let { h -> val s0 = sommet(h); tl.lueur(ecranX(s0[0]), ecranY(s0[1]) - 8 * zz, 46 * zz, a(0xE8F0FC, (170 * sin(q * PI)).toInt())) } }
                if (age < 1.2) tl.rect(aire[0], aire[1], aire[2], aire[3], a(0xE8EEF8, (110 * (1 - age / 1.2)).toInt()))
                eti("🌳 " + t("efx.arbre", "d" to n("dossiers"), "f" to n("fichiers")), x, y - 70 * zz, 0x9FD8A0) }
            "lanternes" -> { val nb = n("n"); val k = max(1, min(8, if (nb > 0) nb else 1))
                for (i in 0 until k) { val lx = x + (i - (k - 1) / 2f) * 20 * zz; val ly = y - 70 * zz + (sin(i * 1.7) * 3 * zz).toFloat()
                    val on = nb > 0 && age > .15 + i * .12
                    if (on) tl.lueur(lx, ly, 16 * zz, a(0xFFD65A, (170 * fin).toInt()))
                    tl.rect(lx - .5f * zz, ly - 12 * zz, 1 * zz, 5 * zz, a(0x2B2F3A, al)); tl.rect(lx - 5 * zz, ly - 7 * zz, 10 * zz, 2 * zz, a(0x3A3F4C, al))
                    tl.rect(lx - 4 * zz, ly - 5 * zz, 8 * zz, 10 * zz, a(if (on) 0xFFD65A else 0x5A6070, al)) }
                eti("🏮 " + t("efx.lanternes", "n" to nb), x, y - 98 * zz, 0xFFD65A) }
            "reveil" -> { val r2 = (sin(age * 40) * 3 * zz * max(0.0, 1 - age)).toFloat(); val cx = x + 30 * zz + r2; val cy = y - 50 * zz
                tl.ellipse(cx - 9 * zz, cy - 10 * zz, 5 * zz, 5 * zz, a(0xE04848, al)); tl.ellipse(cx + 9 * zz, cy - 10 * zz, 5 * zz, 5 * zz, a(0xE04848, al))
                tl.ellipse(cx, cy, 13 * zz, 13 * zz, a(0xE04848, al)); tl.ellipse(cx, cy, 10 * zz, 10 * zz, a(0xFFF8E1, al))
                tl.ligne(cx, cy, cx, cy - 7 * zz, a(0x1E1E2E, al), 2 * z); tl.ligne(cx, cy, cx + 5 * zz, cy + 3 * zz, a(0x1E1E2E, al), 2 * z)
                if (age < 1.2) tl.texte("♪", cx + 18 * zz, cy - 14 * zz - (age * 10 * zz).toFloat(), 13 * z, a(J, al), true, 'c')
                eti("⏰ " + t("efx.reveil", "n" to n("n")), cx, cy - 30 * zz, J) }
            "journal" -> { val q = (age / .6).coerceIn(0.0, 1.0); val w2 = 92 * zz; val h2 = ((10 + 46 * ease(q)) * zz).toFloat()
                val bx = x - w2 / 2; val by = y - 60 * zz - h2
                tl.rrect(bx, by, w2, h2, 3f, a(0xF3E2B8, al), a(0x3B2A5A, al), 1.5f * z)
                for (i in 0 until min(5, (age * 6).toInt())) if ((8 + i * 9) * zz < h2) tl.rect(bx + 6 * zz, by + (6 + i * 9) * zz, w2 - 12 * zz - (i % 2) * 14 * zz, 2.5f * zz, a(0x5A4632, al))
                eti("📜 " + t("efx.journal", "n" to n("n")), x, by - 14 * zz, VI) }
            "etoile" -> { for ((i, p) in (pts.drop(1).take(8).ifEmpty { pts }).withIndex()) { val q = ((age - i * .1) / .4).coerceIn(0.0, 1.0)
                    etoile(tl, p[0], p[1] - 40 * zz - ((1 - ease(q)) * 30 * zz).toFloat(), 9 * zz, age * 2 + i, a(J, al)) }
                eti("★ " + t("efx.etoile"), x, y - 66 * zz, J) }
            "album" -> { val neuf = e.optString("quoi") == "neuf"; val k = if (neuf) 1 else max(1, min(4, n("n")))
                val cols = listOf(0x7CC6F0, 0x9FD8A0, 0x5AA63A, 0xC9A26A)
                for (i in 0 until k) { val q = ((age - i * .2) / .4).coerceIn(0.0, 1.0); if (q <= 0) continue
                    val cx = x + (i - (k - 1) / 2f) * 22 * zz; val cy = y - 66 * zz - i * 2 * zz; val aq = (255 * q * fin).toInt()
                    tl.rect(cx - 10 * zz, cy - 10 * zz, 20 * zz, 22 * zz, a(0xFBF7EE, aq)); tl.rect(cx - 8 * zz, cy - 8 * zz, 16 * zz, 13 * zz, a(if (neuf) 0xE6E2D8 else cols[i % 4], aq)) }
                eti("📚 " + (if (neuf) t("efx.album_neuf") else t("efx.album", "n" to n("n"))), x, y - 94 * zz, 0xFBF7EE) }
            "branche", "fusion" -> { val q = (age / .9).coerceIn(0.0, 1.0); val yy = y - 70 * zz
                tl.ligne(x - 50 * zz, yy, x + 50 * zz, yy, a(V, al), 3 * z)
                val bp = if (ty == "branche") (0..10).map { val u = it / 10.0; floatArrayOf((x - 30 * zz + 80 * zz * u * q).toFloat(), (yy - 26 * zz * sin(min(1.0, u * q * 2) * PI / 2)).toFloat()) }
                    else (0 until (11 * max(.1, q)).toInt()).map { val u = it / 10.0; floatArrayOf((x - 30 * zz + 70 * zz * u).toFloat(), (yy - 26 * zz * sin(u * PI) * (1 - .15 * q)).toFloat()) }
                for (i in 0 until bp.size - 1) tl.ligne(bp[i][0], bp[i][1], bp[i + 1][0], bp[i + 1][1], a(OR, al), 3 * z)
                for (dx in listOf(-40, -30, 40)) tl.ellipse(x + dx * zz, yy, 4 * zz, 4 * zz, a(0xFBF7EE, al))
                val ok = ty == "branche" || e.optBoolean("ok")
                if (ty == "fusion" && q >= 1) tl.cercle(x + 40 * zz, yy, 6 * zz, a(if (ok) J else R, al), 2 * z)
                val nm = e.optString("nom")
                val txt = if (ty == "branche") (if (e.optString("quoi") == "nouvelle") t("efx.branche", "nom" to nm) else t("efx.branche_change", "nom" to nm))
                    else if (ok) t("efx.fusion", "nom" to nm) else t("efx.conflit")
                eti("⑂ $txt", x, yy - 40 * zz, if (ok) OR else R) }
            "rembobine" -> { val s2 = sin((age / 1.6).coerceIn(0.0, 1.0) * PI)
                for (p in pts.drop(1).take(8).ifEmpty { pts }) { val a0 = -age * 5
                    for (j in 0 until 12) { val u0 = a0 + j / 12.0 * 5.3; val u1 = a0 + (j + 1) / 12.0 * 5.3
                        tl.ligne(p[0] + (cos(u0) * 22 * zz).toFloat(), p[1] - 16 * zz + (sin(u0) * 22 * zz * .8).toFloat(), p[0] + (cos(u1) * 22 * zz).toFloat(), p[1] - 16 * zz + (sin(u1) * 22 * zz * .8).toFloat(), a(0xFFF0C8, (255 * s2).toInt()), 3 * z) } }
                eti("↺ " + e.optString("chemin").substringAfterLast('/') + " · " + t("efx.rembobine"), x, y - 56 * zz, J) }
            "robot" -> { val q = (age / .8).coerceIn(0.0, 1.0); val quoi = e.optString("quoi"); val v = if (e.isNull("valeur")) "" else e.optString("valeur")
                val rx = x + 34 * zz + (if (quoi == "pas") (30 * zz * ease(q)).toFloat() else 0f); val ry = y - (if (quoi == "pas") (sin(q * PI) * 5 * zz).toFloat() else 0f)
                val led: Int? = when (quoi) { "led" -> if (v.trim() !in setOf("", "0") && age > .4) 0x3DFF7C else null; else -> 0x3DFF7C }
                robot(tl, rx, ry, 14 * zz, led, al, if (quoi == "pas" || quoi == "moteur") q * 8 else 0.0)
                if (quoi == "capteur" || quoi == "pas") for (i in 0 until 3) { val r2 = (age * 1.4 + i / 3.0) % 1
                    for (j in 0 until 6) { val u0 = -.5 + j / 6.0; val u1 = -.5 + (j + 1) / 6.0; val rr = (6 + r2 * 26) * zz
                        tl.ligne(rx + 10 * zz + (cos(u0) * rr).toFloat(), ry - 16 * zz + (sin(u0) * rr).toFloat(), rx + 10 * zz + (cos(u1) * rr).toFloat(), ry - 16 * zz + (sin(u1) * rr).toFloat(), a(C, (255 * (1 - r2) * fin).toInt()), 2 * z) } }
                val txt = when (quoi) { "led" -> "💡 " + (if (led != null) t("efx.robot.allume") else t("efx.robot.eteint")); "moteur" -> "⚙ " + t("efx.robot.moteur", "v" to v)
                    "capteur" -> "📡 " + t("efx.robot.capteur", "v" to v.ifEmpty { "?" }); else -> "➜ " + t("efx.robot.pas") }
                eti(txt, rx, ry - 42 * zz, if (quoi == "led") V else C) }
            "grimoire" -> { val o = min(1.0, age * 3).toFloat(); val bx = x + 30 * zz; val by = y - 70 * zz; val s2 = 20 * zz
                tl.rect(bx - s2 * o - 2 * zz, by - s2 * .7f - 2 * zz, 2 * s2 * o + 4 * zz, s2 * 1.4f + 4 * zz, a(0x5A2F6B, al))
                tl.rect(bx - s2 * o, by - s2 * .7f, s2 * o, s2 * 1.4f, a(0xF6EDD5, al)); tl.rect(bx, by - s2 * .7f, s2 * o, s2 * 1.4f, a(0xEFE2C0, al))
                for (i in 0 until 4) for (dx in listOf(-s2 * o + 3 * zz, 3 * zz)) tl.rect(bx + dx, by - s2 * .45f + i * s2 * .3f, s2 * o * .7f, 1.5f * zz, a(0xA89878, al))
                eti("📖 " + t("efx.grimoire", "mot" to e.optString("mot")), bx, by - s2 - 14 * zz, VI) }
            "loupe" -> { val q = (age / .9).coerceIn(0.0, 1.0); val lx = x - 20 * zz + (40 * zz * ease(q)).toFloat(); val ly = y - 60 * zz
                for (i in 0 until min(3, n("n"))) if (age > .3 + i * .25) tl.rect(x - 26 * zz, ly - 14 * zz + i * 9 * zz, 52 * zz, 5 * zz, a(R, (110 * fin).toInt()))
                tl.cercle(lx, ly, 11 * zz, a(0xC9D2DC, al), 2.5f * z); tl.ligne(lx + 8 * zz, ly + 8 * zz, lx + 16 * zz, ly + 16 * zz, a(0xC9D2DC, al), 4 * z)
                val ok = e.optBoolean("ok")
                eti("🔎 " + (if (ok) t("efx.loupe_ok") else t("efx.loupe", "n" to n("n"))), x, ly - 30 * zz, if (ok) V else R) }
            "filet" -> { val q = ease((age / .6).coerceIn(0.0, 1.0)).toFloat(); val w2 = 44 * zz * q; val yy = y + 6 * zz
                for (i in -4 until 4) { val x0 = x + i * w2 / 4; val x1 = x + (i + 1) * w2 / 4
                    tl.ligne(x0, yy - 3 * zz, x1, yy + 5 * zz, a(J, al), 1.3f * z); tl.ligne(x0, yy + 5 * zz, x1, yy - 3 * zz, a(J, al), 1.3f * z) }
                tl.rect(x - w2 - 2 * zz, yy - 10 * zz, 2 * zz, 18 * zz, a(0x8A5A30, al)); tl.rect(x + w2, yy - 10 * zz, 2 * zz, 18 * zz, a(0x8A5A30, al))
                val sg = e.optJSONArray("signaux")?.let { j -> (0 until j.length()).joinToString(" ") { j.getString(it) } } ?: ""
                eti("🪢 " + t("efx.filet") + " · " + sg, x, yy + 22 * zz, J) }
            "sablier" -> { if (age < .6) tl.rect(x - 4 * zz, y - 120 * zz, 8 * zz, 120 * zz, a(0xFFF6B0, (110 * sin(age / .6 * PI)).toInt()))
                sablier(tl, x + (if (e.isNull("chemin")) 34 * zz else 0f), y - 34 * zz, 11 * zz, (age / 1.8).coerceIn(0.0, 1.0).toFloat(), al)
                eti("⏳ " + e.optString("nom") + " · " + t("efx.sablier"), x, y - 60 * zz, BOIS) }
            "espion" -> { for (i in 0 until 6) { val u = (age * .9 + i / 6.0) % 1; val sx = x - 50 * zz + (u * 100 * zz).toFloat(); val sy = y - 56 * zz + (sin(u * 6) * 4 * zz).toFloat()
                    tl.rect(sx - 2 * zz, sy - 2 * zz, 4 * zz, 4 * zz, a(C, (255 * sin(u * PI) * fin).toInt())) }
                tl.cercle(x, y - 56 * zz, 12 * zz, a(C, al), 2.5f * z); tl.ligne(x + 9 * zz, y - 47 * zz, x + 16 * zz, y - 40 * zz, a(C, al), 4 * z)
                eti("🕵 " + t("efx.espion", "n" to n("n")), x, y - 84 * zz, C) }
        }
    }

    private fun caisse(tl: Toile, x: Float, y: Float, s: Float, ouvert: Float, al: Int) {
        tl.rect(x - s / 2, y - s * .7f, s, s * .7f, a(0x8A5A30, al))
        for (k in 1..2) tl.rect(x - s / 2, y - s * .7f + k * s * .23f, s, max(1f, s * .04f), a(0x6B4424, al))
        val b = max(1f, s * .06f)
        tl.rect(x - s / 2, y - s * .7f, b, s * .7f, a(0xC9A26A, al)); tl.rect(x + s / 2 - b, y - s * .7f, b, s * .7f, a(0xC9A26A, al))
        val lev = ouvert * s * .45f
        tl.poly(floatArrayOf(x - s / 2, x + s / 2, x + s / 2, x - s / 2), floatArrayOf(y - s * .7f, y - s * .7f - lev, y - s * .86f - lev, y - s * .86f), a(0xA8743F, al))
    }

    private fun etoile(tl: Toile, x: Float, y: Float, r: Float, rot: Double, c: Int) {
        val xs = FloatArray(10); val ys = FloatArray(10)
        for (i in 0 until 10) { val rr = if (i % 2 == 0) r else r * .45f; xs[i] = x + (cos(rot + i * PI / 5) * rr).toFloat(); ys[i] = y + (sin(rot + i * PI / 5) * rr).toFloat() }
        tl.poly(xs, ys, c)
    }

    private fun robot(tl: Toile, x: Float, y: Float, s: Float, led: Int?, al: Int, roues: Double) {
        tl.rect(x - s * .6f, y - s * 1.1f, s * 1.2f, s * .8f, a(0x8A96A3, al)); tl.rect(x - s * .7f, y - s * .35f, s * 1.4f, s * .25f, a(0x5C6672, al))
        tl.rect(x - s * .35f, y - s * .95f, s * .22f, s * .22f, a(0x1E2430, al)); tl.rect(x + s * .13f, y - s * .95f, s * .22f, s * .22f, a(0x1E2430, al))
        tl.rect(x - s * .04f, y - s * 1.35f, s * .08f, s * .25f, a(0x2B2F3A, al))
        if (led != null) tl.lueur(x, y - s * 1.42f, s * .7f, a(led, (al * .8).toInt()))
        tl.ellipse(x, y - s * 1.42f, s * .13f, s * .13f, a(led ?: 0x3A3F4C, al))
        for (dx in listOf(-.45f, .45f)) { tl.ellipse(x + dx * s, y - s * .05f, s * .22f, s * .22f, a(0x1E1E2E, al))
            tl.ligne(x + dx * s - (sin(roues) * s * .18).toFloat(), y - s * .05f - (cos(roues) * s * .18).toFloat(), x + dx * s + (sin(roues) * s * .18).toFloat(), y - s * .05f + (cos(roues) * s * .18).toFloat(), a(0xC9D2DC, al), 1.5f) }
    }

    private fun sablier(tl: Toile, x: Float, y: Float, s: Float, k: Float, al: Int) {
        tl.rect(x - s * .6f, y - s, s * 1.2f, s * .15f, a(0xC9A26A, al)); tl.rect(x - s * .6f, y + s * .85f, s * 1.2f, s * .15f, a(0xC9A26A, al))
        tl.poly(floatArrayOf(x - s * .45f, x + s * .45f, x + s * .05f, x + s * .45f, x - s * .45f, x - s * .05f), floatArrayOf(y - s * .85f, y - s * .85f, y, y + s * .85f, y + s * .85f, y), a(0xDCF0FF, (al * .6).toInt()))
        val h = (1 - k) * s * .7f; tl.poly(floatArrayOf(x - h * .55f, x + h * .55f, x), floatArrayOf(y - h, y - h, y), a(0xFFD36B, al))
        val b = k * s * .7f; tl.poly(floatArrayOf(x - b * .6f, x + b * .6f, x), floatArrayOf(y + s * .85f, y + s * .85f, y + s * .85f - b), a(0xFFD36B, al))
    }

    private fun cadenas(tl: Toile, cx: Float, cy: Float, r: Float, c: Int, ouvert: Boolean) {
        tl.rrect(cx - r, cy - r * .2f, r * 2, r * 1.5f, r * .3f, a(c, 255), null, 0f)
        tl.cercle(cx + (if (ouvert) r * .5f else 0f), cy - r * .3f, r * .6f, a(c, 255), max(1f, r * .3f))
    }

    private fun pigeon(tl: Toile, x: Float, y: Float, z: Float, age: Double) {
        val f = sin(age * 18).toFloat()
        tl.ellipse(x, y, 6 * z, 3.5f * z, 0xFFF0F0F5.toInt()); tl.ellipse(x + 5 * z, y - 2 * z, 2.5f * z, 2.5f * z, 0xFFDCDCE6.toInt())
        tl.poly(floatArrayOf(x - 2 * z, x - 9 * z, x + 2 * z), floatArrayOf(y - z, y - 7 * z * f, y - 2 * z), 0xFFC8CDD7.toInt())
        tl.rect(x + 7 * z, y - 2.5f * z, 2 * z, z, 0xFFFFA03C.toInt())
    }

    companion object {
        val GUIDE2 = setOf("disque", "arbre", "memoire", "lanternes", "reveil", "journal", "album", "branche", "fusion",
            "robot", "grimoire", "loupe", "filet", "sablier", "espion")
        val STADES = mapOf("bebe" to 30.0, "enfant" to 36.0, "ado" to 42.0, "adulte" to 50.0, "ancien" to 52.0, "finale" to 52.0)
        val COUL = mapOf("feu" to 0xe8562a, "eau" to 0x2f7fc4, "glace" to 0x9fd8f2, "plante" to 0x5aa63a, "roche" to 0xc9a26a,
            "ciel" to 0xdfe9ff, "ombre" to 0x4b3a6b, "machine" to 0x8a96a3, "poison" to 0x6a8f2a)
        val EMOJI = mapOf("feu" to "🔥", "eau" to "💧", "glace" to "🧊", "plante" to "🌿", "roche" to "🗻", "ciel" to "⚡",
            "ombre" to "🌙", "machine" to "🔩", "poison" to "🧪")
        val RARETE = mapOf("peu commune" to 0x4ade80, "rare" to 0x38bdf8, "épique" to 0xc084fc, "légendaire" to 0xfbbf24, "mythique" to 0xff79c6)
        fun ease(p: Double) = if (p < .5) 2 * p * p else 1 - Math.pow(-2 * p + 2, 2.0) / 2
        fun easeBack(p: Double): Double { val c = 1.7; return 1 + (c + 1) * Math.pow(p - 1, 3.0) + c * Math.pow(p - 1, 2.0) }
    }
}
