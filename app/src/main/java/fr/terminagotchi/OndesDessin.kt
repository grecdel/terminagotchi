package fr.terminagotchi

import kotlin.math.PI
import kotlin.math.log10
import kotlin.math.min
import kotlin.math.sin

/**
 * Le dessin de la Tour des Ondes (interface Toile d'EspaceDessin : mêmes thèmes, mêmes captures JVM), en attendant
 * les illustrations (§ 7.15 : B5, E5, E6) :
 *  - onde : l'onde dont on règle la fréquence (plus haute = vagues plus serrées), avec sa longueur d'onde ;
 *  - mur : trois ondes (LoRa, Wi-Fi 2,4 GHz, Wi-Fi 5 GHz) qui traversent un mur et s'affaiblissent, plus ou moins ;
 *  - spectre : la règle du spectre (échelle logarithmique de 10 MHz à 10 GHz), chaque technologie à sa place, bandes
 *    libres en vert ;
 *  - vallee : le petit message LoRa qui traverse la vallée (ou tombe au milieu si la portée est trop courte) ;
 *  - maillage : les nœuds du Terminaworld (positions du Port), les liens radio, les nœuds coupés, le chemin du message
 *    qui saute de nœud en nœud ;
 *  - antenne : l'antenne de la vue déployée (lire, écouter : l'onde arrive ; émettre, simuler : elle part) ;
 *  - tour : l'AFFICHAGE DE REPLI de l'illustration B5 (la tour sur la falaise au-dessus du port), formes simples.
 * L'appli n'émet jamais : tout est dessiné.
 */
object OndesDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)
    private fun p01(phase: Double) = ((phase % 1.0) + 1.0) % 1.0

    val COULEURS = mapOf("fm" to EspaceDessin.ROSE, "lora" to EspaceDessin.VIOLET, "quatreg" to EspaceDessin.BLEU, "gps" to EspaceDessin.JAUNE,
        "bluetooth" to 0xFF5F87FF.toInt(), "wifi24" to EspaceDessin.VERT, "cinqg" to EspaceDessin.CYAN, "wifi5" to EspaceDessin.ORANGE,
        "wifi6" to EspaceDessin.ROUGE, "wifi" to EspaceDessin.VERT, "toutes" to EspaceDessin.DOUX, "sdr" to EspaceDessin.JAUNE)

    /** Une vague sinusoïdale tracée par petits segments ; derrière le mur (colonne mur, 0-1), l'amplitude tombe à reste. */
    private fun vague(tl: Toile, per: Double, phase: Double, x: Float, y: Float, w: Float, h: Float, c: Int, ep: Float, mur: Float? = null, reste: Float = 1f) {
        val n = 120
        var px = x; var py = y + h / 2
        for (k in 0..n) {
            val u = k.toFloat() / n
            val amp = if (mur == null || u < mur) h / 2 * 0.9f else h / 2 * 0.9f * reste
            val nx = x + u * w
            val ny = y + h / 2 - (amp * sin(2 * PI * (per * u) - phase * 2 * PI)).toFloat()
            if (k > 0) tl.ligne(px, py, nx, ny, c, ep)
            px = nx; py = ny
        }
    }

    fun onde(tl: Toile, hz: Long, tid: String?, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[tid] ?: EspaceDessin.CYAN
        tl.rrect(x, y, w, h, 14 * z, a(c, 12), a(c, 110), 1.2f * z)
        val nom = tid?.let { t("on.tech.$it") } ?: "${hz / 1_000_000} MHz"
        tl.texte(nom, x + 14 * z, y + 16 * z, 13 * z, c, true)
        tl.texte(Ondes.texteLongueur(Ondes.longueurOnde(hz)), x + w - 14 * z, y + 16 * z, 12 * z, EspaceDessin.TEXTE, false, 'd', true)
        val per = Ondes.periodes(hz)
        vague(tl, per, phase, x + 14 * z, y + 30 * z, w - 28 * z, h - 54 * z, c, 2.4f * z)
        // la longueur d'une vague : une accolade sous la première
        val lx = x + 14 * z; val lw = (w - 28 * z) / per.toFloat()
        val ly = y + h - 16 * z
        tl.ligne(lx, ly, lx + lw, ly, EspaceDessin.TEXTE, 1.2f * z)
        tl.ligne(lx, ly - 4 * z, lx, ly + 4 * z, EspaceDessin.TEXTE, 1.2f * z); tl.ligne(lx + lw, ly - 4 * z, lx + lw, ly + 4 * z, EspaceDessin.TEXTE, 1.2f * z)
        tl.texte("λ", lx + lw / 2, ly - 8 * z, 12 * z, EspaceDessin.TEXTE, true, 'c')
    }

    fun mur(tl: Toile, matiere: String, n: Int, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.PALE, 14), a(EspaceDessin.PALE, 120), 1.2f * z)
        val techs = listOf("lora", "wifi24", "wifi5")
        val bande = (h - 16 * z) / techs.size
        val mx = 0.48f
        for ((i, tid) in techs.withIndex()) {
            val c = COULEURS[tid]!!
            val db = Ondes.affaiblissement(matiere, tid, n)
            val (amp, pui) = Ondes.restantPc(db)
            val by = y + 8 * z + i * bande
            tl.texte(t("on.tech.$tid"), x + 12 * z, by + 12 * z, 11.5f * z, c, true)
            tl.texte("−$db dB · $pui %", x + w - 12 * z, by + 12 * z, 11 * z, EspaceDessin.TEXTE, false, 'd', true)
            vague(tl, Ondes.periodes(Ondes.hzTech(tid) ?: 1L), phase, x + 12 * z, by + 20 * z, w - 24 * z, bande - 26 * z, c, 2 * z, mx, amp / 100f)
        }
        // le mur, en briques
        val wx = x + 12 * z + (w - 24 * z) * mx - 8 * z
        val bw = 16 * z
        var yy = y + 6 * z; var k = 0
        while (yy < y + h - 8 * z) {
            val hh = min(9 * z, y + h - 8 * z - yy)
            tl.rrect(wx + (if (k % 2 == 0) 0f else -3 * z), yy, bw, hh, 2 * z, 0xFF8D5A3B.toInt(), 0xFF3B2416.toInt(), 1 * z)
            yy += 10 * z; k++
        }
        tl.texte(t("on.matiere.$matiere") + " × $n", wx + bw / 2, y + h - 2 * z, 10 * z, EspaceDessin.DOUX, false, 'c')
    }

    fun spectre(tl: Toile, x: Float, y: Float, w: Float, h: Float, z: Float, surligne: Collection<String> = emptyList()) {
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.JAUNE, 10), a(EspaceDessin.JAUNE, 100), 1.2f * z)
        val gx = x + 18 * z; val gw = w - 36 * z
        val ry = y + h - 34 * z
        fun pos(hz: Double) = gx + ((log10(hz) - 7) / 3).toFloat().coerceIn(0f, 1f) * gw
        // l'arc-en-ciel de la règle
        val n = 60
        for (k in 0 until n) {
            val c = listOf(EspaceDessin.ROSE, EspaceDessin.VIOLET, EspaceDessin.BLEU, EspaceDessin.CYAN, EspaceDessin.VERT, EspaceDessin.JAUNE, EspaceDessin.ORANGE)[k * 7 / n]
            tl.rect(gx + gw * k / n, ry, gw / n + 1, 8 * z, a(c, 200))
        }
        for ((p, lab) in listOf(7 to "10 MHz", 8 to "100 MHz", 9 to "1 GHz", 10 to "10 GHz")) {
            val px = pos(Math.pow(10.0, p.toDouble()))
            tl.ligne(px, ry - 4 * z, px, ry + 12 * z, EspaceDessin.TEXTE, 1.4f * z)
            tl.texte(lab, px, ry + 22 * z, 10 * z, EspaceDessin.DOUX, false, if (p == 7) 'g' else if (p == 10) 'd' else 'c')
        }
        val techs = Ondes.donnees().optJSONObject("spectre")?.optJSONArray("techs") ?: return
        val l = (0 until techs.length()).map { techs.getJSONObject(it) }.sortedWith(compareBy({ it.getLong("hz") }, { it.optString("id") }))
        val rang = (ry - y - 24 * z) / l.size
        for ((i, x0) in l.withIndex()) {
            val id = x0.optString("id"); val c = COULEURS[id] ?: EspaceDessin.TEXTE
            val px = pos(x0.getLong("hz").toDouble())
            val ly = y + 16 * z + i * rang
            tl.ligne(px, ly + 4 * z, px, ry - 2 * z, a(c, if (id in surligne) 255 else 120), (if (id in surligne) 2.2f else 1.2f) * z, 3 * z, 3 * z)
            tl.cercle(px, ly + 2 * z, 4 * z, c, 2 * z)
            val libre = x0.optString("libre") == "l"
            val txt = t("on.tech.$id") + (if (libre) " ✓" else " ✗")
            val droite = px > gx + gw * 0.6f
            tl.texte(txt, px + (if (droite) -8 * z else 8 * z), ly + 2 * z, 10.5f * z, if (libre) EspaceDessin.VERT else c, id in surligne, if (droite) 'd' else 'g')
        }
    }

    fun vallee(tl: Toile, sf: Int, distance: Int, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VIOLET, 10), a(EspaceDessin.VIOLET, 100), 1.2f * z)
        val sol = y + h - 26 * z
        // les deux collines et la vallée
        val xs = floatArrayOf(x + 10 * z, x + 10 * z, x + w * 0.16f, x + w * 0.3f, x + w * 0.5f, x + w * 0.7f, x + w * 0.84f, x + w - 10 * z, x + w - 10 * z)
        val ys = floatArrayOf(sol + 16 * z, sol - h * 0.38f, sol - h * 0.4f, sol - h * 0.1f, sol + 6 * z, sol - h * 0.12f, sol - h * 0.42f, sol - h * 0.38f, sol + 16 * z)
        tl.poly(xs, ys, 0xFF2E5E3A.toInt())
        val t1 = x + w * 0.12f; val t2 = x + w * 0.88f; val ty = sol - h * 0.4f
        for (tx in listOf(t1, t2)) {
            tl.ligne(tx, ty, tx, ty - 34 * z, EspaceDessin.TEXTE, 2.4f * z)
            tl.cercle(tx, ty - 34 * z, 4 * z, EspaceDessin.VIOLET, 2 * z)
        }
        val po = Ondes.porteeM(sf)
        val arrive = po >= distance
        val bout = if (arrive) 1f else po.toFloat() / distance
        val u = min(q * 1.25, 1.0).toFloat() * bout
        // la trajectoire et les ondes LoRa (des chirps)
        val mx = t1 + (t2 - t1) * u
        val my = ty - 34 * z - (sin(PI * u) * h * 0.18).toFloat() + (if (!arrive && u >= bout - 0.01f) (q.toFloat() - 0.8f).coerceAtLeast(0f) * h * 1.5f else 0f)
        for (k in 1..3) tl.cercle(t1, ty - 34 * z, (10 + 10 * k) * z * ((q * 3 + k) % 1.0).toFloat(), a(EspaceDessin.VIOLET, 140 - 30 * k), 1.4f * z)
        tl.rrect(mx - 9 * z, my - 6 * z, 18 * z, 12 * z, 2 * z, EspaceDessin.TEXTE, EspaceDessin.VIOLET, 1.4f * z)
        tl.ligne(mx - 9 * z, my - 6 * z, mx, my + 1 * z, EspaceDessin.VIOLET, 1.2f * z); tl.ligne(mx + 9 * z, my - 6 * z, mx, my + 1 * z, EspaceDessin.VIOLET, 1.2f * z)
        if (arrive && u >= 0.99f) tl.lueur(t2, ty - 34 * z, 18 * z, a(EspaceDessin.VERT, 120))
        tl.texte("SF$sf · ${Ondes.g(po / 1000.0, 3)} km · ${Ondes.g(distance / 1000.0, 3)} km", x + w / 2, y + h - 10 * z, 11 * z,
            if (arrive) EspaceDessin.VERT else EspaceDessin.ROUGE, true, 'c', true)
    }

    fun maillage(tl: Toile, coupes: Collection<String>, chemin: List<String>, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VIOLET, 10), a(EspaceDessin.VIOLET, 100), 1.2f * z)
        val carte = Port.donnees().optJSONObject("carte") ?: return
        fun xy(id: String): Pair<Float, Float> { val p = carte.optJSONArray(id) ?: return x to y
            return x + 18 * z + p.getDouble(0).toFloat() * (w - 36 * z) to y + 18 * z + p.getDouble(1).toFloat() * (h - 40 * z) }
        val surChemin = chemin.zipWithNext().toSet()
        for ((a0, b0) in Ondes.liens()) {
            val (x1, y1) = xy(a0); val (x2, y2) = xy(b0)
            val coupe = a0 in coupes || b0 in coupes
            val vif = (a0 to b0) in surChemin || (b0 to a0) in surChemin
            tl.ligne(x1, y1, x2, y2, if (coupe) a(EspaceDessin.PALE, 70) else if (vif) EspaceDessin.VIOLET else a(EspaceDessin.DOUX, 140),
                (if (vif) 3f else 1.3f) * z, if (coupe) 4 * z else 0f, if (coupe) 4 * z else 0f)
        }
        for (id in Ondes.noeuds()) {
            val (px, py) = xy(id)
            val coupe = id in coupes
            val c = if (coupe) EspaceDessin.PALE else if (id in chemin) EspaceDessin.VIOLET else EspaceDessin.CYAN
            if (!coupe && id in chemin) tl.lueur(px, py, 16 * z, a(EspaceDessin.VIOLET, 90))
            tl.ellipse(px, py, 9 * z, 9 * z, if (coupe) 0xFF22283A.toInt() else a(c, 230))
            tl.cercle(px, py, 9 * z, if (coupe) EspaceDessin.ROUGE else EspaceDessin.TEXTE, 1.4f * z)
            if (coupe) { tl.ligne(px - 6 * z, py - 6 * z, px + 6 * z, py + 6 * z, EspaceDessin.ROUGE, 2 * z); tl.ligne(px + 6 * z, py - 6 * z, px - 6 * z, py + 6 * z, EspaceDessin.ROUGE, 2 * z) }
            tl.texte(id, px, py + 18 * z, 10 * z, if (coupe) EspaceDessin.PALE else EspaceDessin.TEXTE, id in chemin, 'c')
        }
        // le message qui saute de nœud en nœud
        if (chemin.size >= 2) {
            val seg = chemin.size - 1
            val u = q * seg
            val k = min(u.toInt(), seg - 1)
            val f = (u - k).toFloat()
            val (x1, y1) = xy(chemin[k]); val (x2, y2) = xy(chemin[k + 1])
            val mx = x1 + (x2 - x1) * f; val my = y1 + (y2 - y1) * f
            tl.lueur(mx, my, 14 * z, a(EspaceDessin.JAUNE, 140))
            tl.rrect(mx - 8 * z, my - 5.5f * z, 16 * z, 11 * z, 2 * z, EspaceDessin.TEXTE, EspaceDessin.JAUNE, 1.4f * z)
        }
    }

    /** L'antenne de la vue déployée : une petite tour, et l'onde de la radio qui part (émettre, simuler, chercher) ou
     *  qui arrive (lire, écouter). Le texte dit le sens (lecture seule, réception seulement…). */
    fun antenne(tl: Toile, an: Deploie.Antenne, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val c = COULEURS[an.radio] ?: EspaceDessin.CYAN
        tl.rrect(x, y, w, h, 14 * z, a(c, 10), a(c, 100), 1.2f * z)
        val tx = x + 30 * z; val base = y + h - 12 * z
        tl.poly(floatArrayOf(tx - 12 * z, tx, tx + 12 * z), floatArrayOf(base, y + 16 * z, base), a(EspaceDessin.PALE, 220))
        tl.cercle(tx, y + 16 * z, 4 * z, c, 2 * z)
        val tid = when (an.radio) { "wifi", "toutes" -> "wifi24"; "sdr" -> "fm"; else -> an.radio }
        val arrive = an.sens == "lit" || an.sens == "ecoute"
        vague(tl, Ondes.periodes(Ondes.hzTech(tid) ?: 2_400_000_000L), if (arrive) -phase else phase, tx + 20 * z, y + 14 * z, w - 70 * z, h - 40 * z, c, 2 * z)
        tl.texte(if (arrive) "←" else "→", x + w - 18 * z, y + h / 2 - 6 * z, 16 * z, c, true, 'c')
        tl.texte(t("on.radio.${an.radio}") + " · " + t("on.sens.${an.sens}"), x + w / 2 + 10 * z, y + h - 8 * z, 10.5f * z, EspaceDessin.TEXTE, false, 'c')
    }

    /** Le REPLI de l'illustration B5 : la tour sur la falaise au-dessus du port, ses antennes qui vibrent en couleurs. */
    fun tour(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val q = p01(phase)
        tl.rrect(x, y, w, h, 14 * z, 0xFF101830.toInt(), a(EspaceDessin.VIOLET, 120), 1.2f * z)
        // la mer et le port
        tl.rect(x + 2 * z, y + h * 0.72f, w - 4 * z, h * 0.28f - 2 * z, 0xFF16324F.toInt())
        for (k in 0 until 6) tl.ligne(x + w * (0.05f + 0.1f * k), y + h * 0.8f, x + w * (0.1f + 0.1f * k), y + h * 0.8f, a(EspaceDessin.CYAN, 120), 1.4f * z)
        tl.texte("⚓", x + w * 0.2f, y + h * 0.86f, 16 * z, EspaceDessin.TEXTE, false, 'c')
        // la falaise
        tl.poly(floatArrayOf(x + w * 0.45f, x + w * 0.55f, x + w * 0.98f, x + w * 0.98f), floatArrayOf(y + h * 0.98f, y + h * 0.55f, y + h * 0.5f, y + h * 0.98f), 0xFF4A3B2E.toInt())
        tl.poly(floatArrayOf(x + w * 0.55f, x + w * 0.98f, x + w * 0.98f, x + w * 0.58f), floatArrayOf(y + h * 0.55f, y + h * 0.5f, y + h * 0.54f, y + h * 0.59f), 0xFF3E8E4A.toInt())
        // la tour et ses antennes
        val tx = x + w * 0.76f; val tb = y + h * 0.52f; val th = h * 0.42f
        tl.poly(floatArrayOf(tx - 18 * z, tx - 6 * z, tx + 6 * z, tx + 18 * z), floatArrayOf(tb, tb - th, tb - th, tb), 0xFFB9C2D6.toInt())
        for (k in 1..4) tl.ligne(tx - 18 * z + k * 2.6f * z, tb - k * th / 5, tx + 18 * z - k * 2.6f * z, tb - k * th / 5, 0xFF6A738A.toInt(), 1.2f * z)
        val cols = listOf(EspaceDessin.ROSE, EspaceDessin.VIOLET, EspaceDessin.CYAN, EspaceDessin.VERT, EspaceDessin.JAUNE, EspaceDessin.ORANGE)
        for ((i, c) in cols.withIndex()) {
            val r = (14 + 12 * i) * z * (0.6f + 0.4f * ((q + i / 6.0) % 1.0).toFloat())
            tl.cercle(tx, tb - th, r, a(c, 200 - 25 * i), 1.6f * z)
        }
        tl.lueur(tx, tb - th, 14 * z, a(EspaceDessin.VIOLET, 160))
        // des étoiles
        for (k in 0 until 14) { val sx = x + w * ((k * 37 % 100) / 100f); val sy = y + h * ((k * 53 % 40) / 100f) + 6 * z
            tl.ellipse(sx, sy, 1.4f * z, 1.4f * z, a(EspaceDessin.TEXTE, (120 + 120 * sin(q * 6.28 + k)).toInt())) }
        // un petit messager LoRa qui part vers le large
        val u = q.toFloat()
        tl.texte("✉", tx - w * 0.6f * u, tb - th - 20 * z + (sin(u * 6.28) * 8 * z).toFloat(), 14 * z, a(EspaceDessin.JAUNE, (255 * (1 - u)).toInt()), false, 'c')
    }
}
