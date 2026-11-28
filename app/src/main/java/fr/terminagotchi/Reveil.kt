package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Le réveil du Terminaworld, de biome en biome, et le monde de la carte (idées 31 à 39, 88), comme pc/tg/reveil.py.
 * Données : assets/reveil.json (copie de donnees/reveil/zones.json) ; vecteurs communs : donnees/reveil/vecteurs.json.
 * Les paysages suivent le fil de l'histoire (chapitre 1 → la Racine, 2 → le biome de l'œuf, chaque aile → son biome,
 * la Glace puis la Roche quand le biome est déjà réveillé, le Cœur → tout) ; les lieux suivent les mondes du
 * Carrefour (éteint, lanterne, allumé ; ★ au palier 3). Jamais de retour en arrière.
 * L'image de la carte : melanger() mélange le vivant et l'endormi avec les masques (EspaceVue la met en Bitmap).
 */
object Reveil {
    const val FERME = 0.0
    const val LANTERNE = 0.45
    const val ALLUME = 1.0
    const val NB_BIOMES = 9

    @Volatile var chargeur: (() -> String?)? = null
    private var z: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("reveil.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun zones(): JSONObject = z ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { z = it }

    private fun cles(o: JSONObject?): List<String> = o?.keys()?.asSequence()?.toList() ?: emptyList()
    private fun liste(a: JSONArray?): List<String> = a?.let { x -> (0 until x.length()).map { x.optString(it) } } ?: emptyList()
    fun biomes(): List<String> = cles(zones().optJSONObject("biomes"))
    fun lieux(): List<String> = cles(zones().optJSONObject("lieux"))
    fun lieu(l: String): JSONObject = zones().optJSONObject("lieux")?.optJSONObject(l) ?: JSONObject()
    fun taille(): Pair<Float, Float> = zones().optJSONArray("taille").let { (it?.optDouble(0, 1672.0) ?: 1672.0).toFloat() to (it?.optDouble(1, 941.0) ?: 941.0).toFloat() }
    fun coeur(b: String): Pair<Float, Float> {
        val c = zones().optJSONObject("biomes")?.optJSONObject(b)?.optJSONArray("coeur")
        val (w, h) = taille()
        return ((c?.optDouble(0) ?: 0.0).toFloat() / w) to ((c?.optDouble(1) ?: 0.0).toFloat() / h)
    }

    class Etat(val biomes: List<String>, val lieux: Map<String, Double>, val etoiles: List<String>)

    // ================================================================ les fonctions pures (vecteurs communs)
    fun calcul(ailes: List<String>, oeuf: String?, ouverts: Collection<String>, allumes: Collection<String>, etoiles: Collection<String>): Etat {
        val zz = zones()
        val bs = biomes()
        val ch = zz.optJSONObject("chapitres") ?: JSONObject()
        val remp = liste(zz.optJSONArray("remplacants"))
        val rev = mutableListOf<String>()
        for (a in ailes) {
            var cible: String? = if (ch.has(a)) ch.optString(a) else continue
            if (cible == "tout") { for (b in bs) if (b !in rev) rev.add(b); continue }
            if (cible == "oeuf") cible = if (oeuf in bs) oeuf else null
            if (cible == null) continue
            if (cible in rev) cible = remp.firstOrNull { it !in rev }
            if (cible != null) rev.add(cible)
        }
        val ls = LinkedHashMap<String, Double>()
        val eto = mutableListOf<String>()
        for (l in lieux()) {
            val d = lieu(l)
            val m = if (d.has("monde")) d.optString("monde") else null
            ls[l] = if (m == null) (if (l == "camp" || "reveil" in ailes) ALLUME else FERME)
                else if (m in allumes) ALLUME else if (m in ouverts) LANTERNE else FERME
            if (m != null && m in etoiles) eto.add(l)
        }
        return Etat(rev, ls, eto)
    }

    fun signature(e: Etat): String =
        biomes().joinToString("") { if (it in e.biomes) "1" else "0" } + "-" +
            lieux().joinToString("") { when (e.lieux[it]) { ALLUME -> "2"; LANTERNE -> "1"; else -> "0" } }

    fun depuisSignature(sig: String?): Etat {
        val bs = (sig ?: "").substringBefore('-')
        val ls = (sig ?: "").substringAfter('-', "")
        val b = biomes().filterIndexed { i, _ -> bs.getOrNull(i) == '1' }
        val l = LinkedHashMap<String, Double>()
        for ((i, x) in lieux().withIndex()) l[x] = when (ls.getOrNull(i)) { '2' -> ALLUME; '1' -> LANTERNE; else -> FERME }
        return Etat(b, l, emptyList())
    }

    /** La commande que « Y aller » écrit (sans la lancer). ici, cible : relatifs au terrain ; ici null = hors du terrain. */
    fun cheminCd(ici: String?, cible: String?): String? {
        val c = (cible ?: "").split("/").filter { it.isNotEmpty() }
        val complet = "cd ~/terrain_terminagotchi" + (if (c.isNotEmpty()) "/" + c.joinToString("/") else "")
        if (ici == null) return complet
        val i = ici.split("/").filter { it.isNotEmpty() }
        var n = 0
        while (n < minOf(i.size, c.size) && i[n] == c[n]) n++
        val monter = i.size - n
        val descendre = c.drop(n)
        if (monter == 0 && descendre.isEmpty()) return null
        if (monter + descendre.size <= 2) return "cd " + (List(monter) { ".." } + descendre).joinToString("/")
        return complet
    }

    fun moment(heure: Int): String {
        val ms = zones().optJSONObject("moments") ?: return "jour"
        for (nom in cles(ms)) {
            val a = ms.getJSONArray(nom).getInt(0); val b = ms.getJSONArray(nom).getInt(1)
            if (if (a < b) heure in a until b else (heure >= a || heure < b)) return nom
        }
        return "jour"
    }

    fun saison(mois: Int): String {
        val ss = zones().optJSONObject("saisons") ?: return "ete"
        for (nom in cles(ss)) { val a = ss.getJSONArray(nom); if ((0 until a.length()).any { a.getInt(it) == mois }) return nom }
        return "ete"
    }

    /** FNV-1a 32 bits (le même que reveil.fnv sur PC). */
    fun fnv(texte: String): Long {
        var h = 0x811C9DC5L
        for (o in texte.toByteArray(Charsets.UTF_8)) h = ((h xor (o.toLong() and 0xFF)) * 0x01000193L) and 0xFFFFFFFFL
        return h
    }

    fun evenements(): List<JSONObject> = zones().optJSONArray("evenements")?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()

    fun evenementDuJour(graine: String, jour: String, reveilles: Collection<String>, vus: Collection<String>): String? {
        val h = fnv("$graine:$jour")
        val k = maxOf(1, zones().optInt("evenement_chance", 3)).toLong()
        if (h % k != 0L) return null
        val cand = evenements().filter { it.optString("biome") in reveilles }
        if (cand.isEmpty()) return null
        val pool = cand.filter { it.optString("id") !in vus }.ifEmpty { cand }
        return pool[((h / k) % pool.size).toInt()].optString("id")
    }

    fun premierMot(ligne: String): String = Regex("^\\s*([^\\s|;&]+)").find(ligne)?.groupValues?.get(1)?.lowercase() ?: ""

    /** La météo de la carte (idée 88) : brume, arc, eclairs, pluie ou calme ; jamais plus d'un changement par minute. */
    fun meteo(cmds0: List<Pair<String, Double>>, maintenant: Double, avant: Pair<String, Double>?): Pair<String, Double> {
        val p = zones().optJSONObject("meteo") ?: JSONObject()
        val cmds = cmds0.takeLast(10)
        val recent = cmds.filter { maintenant - it.second <= p.optDouble("fenetre_s", 120.0) }.map { it.first }
        val reseau = liste(p.optJSONArray("reseau"))
        val m = when {
            cmds.isEmpty() || maintenant - cmds.last().second > p.optDouble("pause_s", 120.0) -> "brume"
            recent.any { '|' in it } -> "arc"
            recent.any { premierMot(it) in reseau } -> "eclairs"
            recent.size >= p.optInt("pluie_n", 5) -> "pluie"
            else -> "calme"
        }
        if (avant == null) return m to maintenant
        if (m != avant.first && maintenant - avant.second >= p.optDouble("garde_s", 60.0)) return m to maintenant
        return avant
    }

    fun evenementVisible(vuT: Double?, maintenant: Double) = vuT == null || maintenant - vuT < zones().optDouble("evenement_duree_s", 300.0)

    // ================================================================ la partie
    fun r(jeu: Jeu): JSONObject {
        val r = jeu.module("reveil")
        for (k in listOf("evts", "gardiens")) if (!r.has(k)) r.put(k, JSONArray())
        return r
    }

    private fun mondes(): Map<String, JSONObject> =
        Programme.donnees().optJSONArray("mondes")?.let { a -> (0 until a.length()).map { a.getJSONObject(it) }.associateBy { it.optString("id") } } ?: emptyMap()

    fun mondesEtats(jeu: Jeu): Triple<List<String>, List<String>, List<String>> {
        val faits = Histoire.faits(jeu).toSet()
        val ouv = mutableListOf<String>(); val allu = mutableListOf<String>(); val eto = mutableListOf<String>()
        val ms = mondes()
        for (l in lieux()) {
            val d = lieu(l)
            val mid = if (d.has("monde")) d.optString("monde") else continue
            val m = ms[mid] ?: continue
            val ch = d.optString("chapitre", mid)
            val fin = Histoire.fini(jeu, ch)
            val o = try { Histoire.ouvert(jeu, ch) } catch (e: Exception) { false }
            val ps = liste(m.optJSONArray("paliers"))
            if (o || fin) ouv.add(mid)
            if (fin || (ps.size > 1 && ps[1] in faits)) allu.add(mid)
            if (fin || (ps.size > 3 && ps[3] in faits)) eto.add(mid)
        }
        return Triple(ouv, allu, eto)
    }

    fun etat(jeu: Jeu): Etat {
        val (o, a, e) = mondesEtats(jeu)
        return calcul(Histoire.ailes(jeu), Oeufs.typeDe(jeu), o, a, e)
    }

    fun nbAllumes(e: Etat) = e.lieux.values.count { it == ALLUME }
    fun nbBiomes(e: Etat) = e.biomes.count { it != "racine" }
    fun nomBiome(b: String) = t("reveil.biome.$b")
    fun nomLieu(l: String) = t("reveil.lieu.$l")

    /** À chaque tour, après les quêtes : UNE nouvelle à la fois (biome, lieu, chemin, chapitre du livre). */
    fun tick(jeu: Jeu) {
        val e = try { etat(jeu) } catch (x: Exception) { return }
        val r = r(jeu)
        poserLivre(jeu)
        val dit = r.optJSONObject("dit")
        if (dit == null) {
            val o = JSONObject().put("biomes", JSONArray(e.biomes)).put("lieux", JSONObject(e.lieux as Map<*, *>))
            r.put("dit", o)
            if (nbBiomes(e) >= 1 || nbAllumes(e) > 2)
                jeu.dire(t("reveil.absence", "n" to nbBiomes(e), "total" to NB_BIOMES, "l" to nbAllumes(e), "lt" to e.lieux.size), 14)
            return
        }
        val db = dit.optJSONArray("biomes") ?: JSONArray().also { dit.put("biomes", it) }
        val faits = liste(db)
        for (b in e.biomes) if (b !in faits) {
            db.put(b)
            jeu.dire(if (b == "racine") t("reveil.racine.dit") else t("reveil.biome.dit", "biome" to nomBiome(b), "n" to nbBiomes(e), "total" to NB_BIOMES), 12)
            jeu.log(t("reveil.biome.log", "biome" to nomBiome(b)))
            return
        }
        val dl = dit.optJSONObject("lieux") ?: JSONObject().also { dit.put("lieux", it) }
        for ((l, v) in e.lieux) {
            val a = dl.optDouble(l, FERME)
            if (v > a) {
                dl.put(l, v)
                if (v == ALLUME && l != "camp" && l != "carrefour") jeu.dire(t("reveil.lieu.dit", "lieu" to nomLieu(l)), 10)
                else if (v == LANTERNE && zones().optJSONObject("chemins")?.has(l) == true) jeu.log(t("reveil.chemin.dit", "lieu" to nomLieu(l)))
                return
            }
        }
        val g = r.getJSONArray("gardiens")
        for (n in livreOuverts(jeu)) if (n.toString() !in liste(g)) {
            g.put(n.toString())
            jeu.dire(t("reveil.gardien.dit", "titre" to t("reveil.gardien.$n.titre")), 12)
            return
        }
    }

    // ---------------------------------------------------------------- le livre des gardiens (idée 37)
    fun gardiens(): List<Pair<String, String>> = zones().optJSONArray("gardiens")?.let { a -> (0 until a.length()).map { a.getJSONArray(it).let { x -> x.optString(0) to x.optString(1) } } } ?: emptyList()

    fun livreOuverts(jeu: Jeu): List<Int> = try {
        gardiens().withIndex().filter { (_, g) -> Citadelle.dansCarnet(jeu, "inspecteur", sujet = g.first) }.map { it.index + 1 }
    } catch (e: Exception) { emptyList() }

    fun fichierGardien(n: Int) = "temps/livre_des_gardiens/${n}_${gardiens()[n - 1].second}.txt"

    fun poserLivre(jeu: Jeu) {
        if (!(Histoire.ouvert(jeu, "temps") || Histoire.fini(jeu, "temps")) || !File(jeu.terrain, "temps").isDirectory) return
        for (n in livreOuverts(jeu)) {
            val f = File(jeu.terrain, fichierGardien(n))
            if (!f.exists()) try { f.parentFile?.mkdirs(); f.writeText(t("reveil.gardien.$n.titre") + "\n\n" + t("reveil.gardien.$n.texte") + "\n") } catch (e: Exception) { }
        }
    }

    // ---------------------------------------------------------------- les quêtes du monde (idées 33 et 35)
    fun quetesDonnees(): List<JSONObject> = zones().optJSONArray("quetes")?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()

    /** Les quêtes du monde au format de Quetes.kt (les mêmes que reveil.quetes() sur PC). */
    fun quetes(): List<Quetes.Quete> = quetesDonnees().map { q ->
        val but = (0 until (q.optJSONArray("but")?.length() ?: 0)).map { i ->
            val b = q.getJSONArray("but").getJSONArray(i)
            (0 until b.length()).map { k ->
                val v = b.get(k)
                when {
                    v is JSONObject && v.has("lignes") -> { j: Jeu -> Quetes.lignes(j, v.optString("lignes")) }
                    v is JSONObject && v.has("compte") -> { j: Jeu -> Quetes.compte(j, v.getJSONArray("compte").optString(0), v.getJSONArray("compte").optString(1)) }
                    else -> v
                }
            }
        }
        val pose = q.optJSONObject("pose")
        Quetes.Quete(q.optString("id"), q.optString("piece"), q.optString("sorte"), q.optString("fichier"), but, q.optInt("xp", 15),
            null, null, pose?.let { p -> { _: Jeu -> cles(p).associateWith { k -> p.optString(k) as Any } } },
            true, if (q.has("apres")) q.optString("apres") else null)
    }

    fun secretsCarte(jeu: Jeu): Pair<List<Triple<String, Float, Float>>, Pair<Int, Int>> {
        val finies = Quetes.liste(Quetes.q(jeu), "finies")
        val qs = quetesDonnees().filter { it.optString("sorte") in setOf("cachette", "tresor") }
        val tr = qs.filter { it.optString("id") in finies }.map { Triple(it.optString("id"), it.getJSONArray("pos").getDouble(0).toFloat(), it.getJSONArray("pos").getDouble(1).toFloat()) }
        return tr to (tr.size to qs.size)
    }

    class Habitant(val id: String, val espece: String, val x: Float, val y: Float, val piece: String, val besoin: Boolean,
                   val active: Boolean, val fichier: String, val xp: Int)

    fun habitantsCarte(jeu: Jeu): List<Habitant> {
        val q = Quetes.q(jeu)
        val poses = Quetes.liste(q, "poses"); val finies = Quetes.liste(q, "finies"); val actives = Quetes.liste(q, "actives")
        return quetesDonnees().filter { it.optString("sorte") == "habitant" && it.optString("id") in poses }.map {
            val id = it.optString("id")
            Habitant(id, it.optString("espece"), it.getJSONArray("pos").getDouble(0).toFloat(), it.getJSONArray("pos").getDouble(1).toFloat(),
                it.optString("piece"), id !in finies, id in actives, it.optString("fichier"), it.optInt("xp"))
        }
    }

    fun lieuDePiece(piece: String?): String? = lieux().firstOrNull { lieu(it).optString("piece", "") == piece && piece != null }

    class Lieu(val id: String, val etat: String, val x: Float, val y: Float, val nom: String, val biome: String, val etoile: Boolean,
               val palier: Int, val paliers: Int, val cmd: String?, val habitants: Int, val secrets: Pair<Int, Int>,
               val titre: String, val manque: String, val debut: String)

    fun lieuxCarte(jeu: Jeu, e: Etat, ici: String?): List<Lieu> {
        val ms = mondes()
        val faits = Histoire.faits(jeu).toSet()
        val hab = habitantsCarte(jeu)
        val finies = Quetes.liste(Quetes.q(jeu), "finies").toSet()
        val (w, h) = taille()
        return lieux().map { l ->
            val d = lieu(l)
            val v = e.lieux[l] ?: FERME
            val et = if (v == ALLUME) "allume" else if (v == LANTERNE) "ouvert" else "ferme"
            val el = d.getJSONArray("ellipse")
            val mid = if (d.has("monde")) d.optString("monde") else null
            val m = mid?.let { ms[it] }
            if (mid != null && m != null) {
                val ch = d.optString("chapitre", mid)
                val ps = liste(m.optJSONArray("paliers"))
                val fin = Histoire.fini(jeu, ch)
                val sec = quetesDonnees().filter { it.optString("piece") == d.optString("piece") && it.optString("sorte") in setOf("cachette", "tresor") }.map { it.optString("id") }
                Lieu(l, et, el.getDouble(0).toFloat() / w, el.getDouble(1).toFloat() / h, nomLieu(l), d.optString("biome"), l in e.etoiles,
                    if (fin) ps.size else ps.count { it in faits }, ps.size,
                    if (et == "ferme") null else cheminCd(ici, d.optString("piece")),
                    hab.count { it.piece == d.optString("piece") && it.besoin }, sec.count { it in finies } to sec.size,
                    t("hist.$ch.titre"), if (et == "ferme") (try { Histoire.mondeManque(jeu, ch).joinToString(", ") } catch (x: Exception) { "" }) else "",
                    t("hist.$ch.debut"))
            } else {
                val cmd = if (l == "carrefour") (if (et != "ferme") cheminCd(ici, "") else null)
                    else if (Histoire.pieceOuverte(jeu, "nid")) cheminCd(ici, "nid") else null
                Lieu(l, et, el.getDouble(0).toFloat() / w, el.getDouble(1).toFloat() / h, nomLieu(l), d.optString("biome"), false, 0, 0, cmd, 0,
                    0 to 0, nomLieu(l), "", t("reveil.lieu.$l.apprend"))
            }
        }
    }

    fun cheminsCarte(e: Etat): List<Triple<String, List<Pair<Float, Float>>, String>> {
        val ch = zones().optJSONObject("chemins") ?: return emptyList()
        val (w, h) = taille()
        return cles(ch).map { l ->
            val a = ch.getJSONArray(l)
            val v = e.lieux[l] ?: FERME
            Triple(l, (0 until a.length()).map { a.getJSONArray(it).getDouble(0).toFloat() / w to a.getJSONArray(it).getDouble(1).toFloat() / h },
                if (v == ALLUME) "allume" else if (v == LANTERNE) "ouvert" else "ferme")
        }
    }

    fun iciRel(jeu: Jeu): String? = Maison.rel(jeu, Maison.ici(jeu))

    // ---------------------------------------------------------------- l'événement rare du jour (idée 38)
    fun graine(jeu: Jeu) = Histoire.graine(jeu)

    fun jour(): String = java.text.SimpleDateFormat("yyyyMMdd", java.util.Locale.ROOT).format(java.util.Date())

    fun evenement(jeu: Jeu, maintenant: Double = System.currentTimeMillis() / 1000.0, jour: String = jour()): JSONObject? {
        val r = r(jeu)
        val rev = try { etat(jeu).biomes } catch (e: Exception) { return null }
        val ev = r.optJSONObject("evt")
        // l'événement du jour reste le même toute la journée (une fois vu, il entre dans le carnet)
        val eid = (if (ev != null && ev.optString("jour") == jour) ev.optString("id").ifEmpty { null } else null)
            ?: evenementDuJour(graine(jeu), jour, rev, liste(r.getJSONArray("evts"))) ?: return null
        val vuT = if (ev != null && ev.optString("jour") == jour && ev.optString("id") == eid) ev.optDouble("t") else null
        if (!evenementVisible(vuT, maintenant)) return null
        return evenements().first { it.optString("id") == eid }
    }

    fun noterEvenement(jeu: Jeu, eid: String, maintenant: Double = System.currentTimeMillis() / 1000.0, jour: String = jour()) {
        val r = r(jeu)
        val ev = r.optJSONObject("evt")
        if (ev == null || ev.optString("jour") != jour || ev.optString("id") != eid) r.put("evt", JSONObject().put("jour", jour).put("id", eid).put("t", maintenant))
        if (eid !in liste(r.getJSONArray("evts"))) {
            r.getJSONArray("evts").put(eid)
            Quetes.recompenser(jeu, souvenir = listOf("evenement", eid))
        }
    }

    fun noterCarte(jeu: Jeu, sig: String) { r(jeu).put("carte", sig) }

    // ================================================================ l'image de la carte
    /** Les noms des masques, dans l'ordre des bandes de intro/reveil_masques.png. */
    fun nomsMasques(): List<String> = biomes().map { "b_$it" } + lieux().map { "l_$it" } + listOf("lumieres", "feuillage")

    /** Le masque « réveillé » (0..255) de chaque pixel : Σ biomes réveillés, puis chaque lieu par-dessus. */
    fun alpha(m: Map<String, ByteArray>, n: Int, e: Etat): IntArray {
        val a = IntArray(n)
        for (b in e.biomes) { val x = m["b_$b"] ?: continue; for (i in 0 until n) a[i] = minOf(255, a[i] + (x[i].toInt() and 255)) }
        for ((l, v) in e.lieux) {
            val x = m["l_$l"] ?: continue
            val c = (v * 255).toInt()
            for (i in 0 until n) { val f = x[i].toInt() and 255; if (f != 0) a[i] = (a[i] * (255 - f) + c * f) / 255 }
        }
        return a
    }

    /** La carte mélangée (ARGB, w×h) : vivant v, endormi d, masques m (mw×mh, une valeur par pixel, agrandis au plus
     *  proche : leurs bords sont déjà adoucis), le moment et la saison. */
    fun melanger(v: IntArray, d: IntArray, w: Int, h: Int, m: Map<String, ByteArray>, mw: Int, mh: Int, e: Etat, quand: String?, sais: String?): IntArray {
        val a = alpha(m, mw * mh, e)
        val fe = m["feuillage"]; val lu = m["lumieres"]
        val out = IntArray(w * h)
        val fq = when (quand) { "matin" -> 0.3; "soir" -> 0.8; else -> 1.0 }
        for (y in 0 until h) {
            val my = minOf(mh - 1, y * mh / h) * mw
            for (x in 0 until w) {
                val i = y * w + x
                val j = my + minOf(mw - 1, x * mw / w)
                var p = v[i]
                if (fe != null && sais != null && sais != "ete") p = saisonPixel(p, fe[j].toInt() and 255, sais)
                val q = d[i]
                val k = a[j]
                var r = ((q shr 16 and 255) * (255 - k) + (p shr 16 and 255) * k) / 255
                var g = ((q shr 8 and 255) * (255 - k) + (p shr 8 and 255) * k) / 255
                var b = ((q and 255) * (255 - k) + (p and 255) * k) / 255
                if (quand != null && quand != "jour") {
                    val (tr, tg, tb) = momentPixel(r, g, b, quand)
                    val f = ((lu?.get(j)?.toInt() ?: 0) and 255) * fq
                    r = (tr + (r - tr) * f / 255).toInt(); g = (tg + (g - tg) * f / 255).toInt(); b = (tb + (b - tb) * f / 255).toInt()
                }
                out[i] = (0xFF shl 24) or (r.coerceIn(0, 255) shl 16) or (g.coerceIn(0, 255) shl 8) or b.coerceIn(0, 255)
            }
        }
        return out
    }

    /** Les images de la carte (téléphone et captures) : monde.jpg, dort.jpg (960×540) et les masques (une bande de
     *  480×270 par masque, l'une sous l'autre). image(« reveil:<signature>:<moment>:<saison> ») → ARGB w×h. */
    class Images(val v: IntArray, val d: IntArray, val w: Int, val h: Int, bande: IntArray, val mw: Int, bh: Int) {
        val mh = bh / maxOf(1, nomsMasques().size)
        val masques: Map<String, ByteArray> = nomsMasques().withIndex().associate { (k, n) ->
            n to ByteArray(mw * mh) { i -> (bande.getOrElse(k * mw * mh + i) { 0 } shr 16 and 255).toByte() }
        }
        fun image(nom: String): IntArray {
            val p = nom.split(":")
            return melanger(v, d, w, h, masques, mw, mh, depuisSignature(p.getOrNull(1)), p.getOrNull(2)?.ifEmpty { null }, p.getOrNull(3)?.ifEmpty { null })
        }
    }

    private fun momentPixel(r: Int, g: Int, b: Int, quand: String): Triple<Int, Int, Int> = when (quand) {
        "matin" -> Triple((r * 0.82 + 255 * 0.18).toInt(), (g * 0.82 + 205 * 0.18).toInt(), (b * 0.82 + 190 * 0.18).toInt())
        "soir" -> Triple((r * 0.82 * 0.84 + 255 * 0.16).toInt(), (g * 0.82 * 0.84 + 120 * 0.16).toInt(), (b * 0.82 * 0.84 + 60 * 0.16).toInt())
        else -> Triple((r * 0.36 * 0.62).toInt(), (g * 0.36 * 0.74).toInt(), minOf(255, (b * 0.36 * 1.25).toInt() + 14))
    }

    private fun saisonPixel(p: Int, f: Int, sais: String): Int {
        if (f == 0) return p
        val r = p shr 16 and 255; val g = p shr 8 and 255; val b = p and 255
        val l = (r * 299 + g * 587 + b * 114) / 1000
        val (cr, cg, cb, k) = when (sais) {
            "automne" -> listOf(minOf(255, (l * 1.6).toInt() + 50), (l * 0.9).toInt() + 10, (l * 0.25).toInt(), f * 85 / 100)
            "hiver" -> listOf(minOf(255, (l * 0.9).toInt() + 60), minOf(255, (l * 0.95).toInt() + 66), minOf(255, (l * 1.05).toInt() + 80), f * 55 / 100)
            else -> listOf(minOf(255, r + (r - l) / 8), minOf(255, g + (g - l) / 8), minOf(255, b + (b - l) / 8), f)
        }
        return (0xFF shl 24) or ((r + (cr - r) * k / 255) shl 16) or ((g + (cg - g) * k / 255) shl 8) or (b + (cb - b) * k / 255)
    }
}
