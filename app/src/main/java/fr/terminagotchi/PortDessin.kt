package fr.terminagotchi

import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Le dessin du Port (interface Toile d'EspaceDessin, donc mêmes thèmes et mêmes captures JVM) :
 *  - messager : dans la vue déployée, une commande réseau (ping, curl, ssh, port messager…) envoie un messager qui
 *    part du camp vers sa destination puis revient avec la réponse ; une destination hors de la machine est en orange
 *    (« seulement avec un adulte ») ;
 *  - reseau : la carte du réseau du Terminaworld (les machines, leurs adresses, les phares allumés ou éteints, le
 *    chemin d'un messager qui avance), positions dans port.json (« carte »).
 * Repli propre : aucune image n'est nécessaire (tout est dessiné) ; l'illustration du Port (B4) viendra en fond.
 */
object PortDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)

    /** Le messager d'une commande réseau, sur une piste : ⛺ cmd ─ ─ ✉ ─ ─▶ 🏝 dest, puis le retour. */
    fun messager(tl: Toile, m: Deploie.Messager, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val coul = if (m.local) EspaceDessin.VIOLET else EspaceDessin.ORANGE
        val gauche = "⛺ ${m.cmd}"
        val lw = min(w * 0.3f, tl.mesure(gauche, 13 * z, true, true) + 24 * z)
        tl.rrect(x, y, lw, h, h / 2, a(EspaceDessin.VERT, 18), a(EspaceDessin.VERT, 150), 1.2f * z)
        tl.texte(gauche, x + lw / 2, y + h / 2, 13 * z, EspaceDessin.VERT, true, 'c', true)
        val droite = "🏝 ${m.dest}"
        val rw = min(w * 0.36f, tl.mesure(droite, 13 * z, true, true) + 24 * z)
        val rx = x + w - rw
        tl.rrect(rx, y, rw, h, h / 2, a(EspaceDessin.CYAN, 18), a(EspaceDessin.CYAN, 150), 1.2f * z)
        tl.texte(droite, rx + rw / 2, y + h / 2, 13 * z, EspaceDessin.CYAN, true, 'c', true)
        val tx1 = x + lw + 10 * z
        val tx2 = rx - 10 * z
        tl.rrect(tx1, y, tx2 - tx1, h, h / 2, a(coul, 10), a(coul, 110), 1.2f * z)
        val p = ((phase % 1.0) + 1.0) % 1.0
        val aller = p < 0.5
        val dec = ((p * 120) % 14).toFloat() * z * (if (aller) -1 else 1)
        tl.ligne(tx1 + 14 * z, y + h / 2, tx2 - 14 * z, y + h / 2, a(coul, 160), 1.5f * z, 6 * z, 6 * z, dec)
        val f = (if (aller) p * 2 else (1 - p) * 2).toFloat()
        val ew = 26 * z; val eh = 17 * z
        val ex = tx1 + 12 * z + f * max(0f, tx2 - tx1 - 24 * z - ew)
        enveloppe(tl, ex, y + (h - eh) / 2, ew, eh, coul, z)
        val note = if (aller) "→" else "↩"
        tl.texte(note, if (aller) tx2 - 18 * z else tx1 + 18 * z, y + h / 2, 13 * z, a(coul, 200), true, 'c')
    }

    /** Une enveloppe pixel (le messager) : un rectangle et son rabat en V. */
    fun enveloppe(tl: Toile, x: Float, y: Float, w: Float, h: Float, c: Int, z: Float) {
        tl.rrect(x, y, w, h, 3 * z, 0xFFF4F1E8.toInt(), c, 1.6f * z)
        tl.ligne(x + 2 * z, y + 2 * z, x + w / 2, y + h * 0.6f, c, 1.4f * z)
        tl.ligne(x + w - 2 * z, y + 2 * z, x + w / 2, y + h * 0.6f, c, 1.4f * z)
    }

    private fun pos(id: String): Pair<Float, Float> {
        val p = Port.donnees().optJSONObject("carte")?.optJSONArray(id) ?: return 0.5f to 0.5f
        return p.getDouble(0).toFloat() to p.getDouble(1).toFloat()
    }

    /** La carte du réseau : machines, adresses, phares (éteints en pointillés), et un messager sur le chemin. */
    fun reseau(tl: Toile, eteints: Collection<String>, chemin: List<String>?, phase: Double, x: Float, y: Float, w: Float, h: Float,
               z: Float, adresses: Boolean = true) {
        val mx = 46 * z; val my = 26 * z
        fun px(id: String) = x + mx + pos(id).first * (w - 2 * mx)
        fun py(id: String) = y + my + pos(id).second * (h - 2 * my)
        val surChemin = chemin?.zipWithNext()?.map { setOf(it.first, it.second) } ?: emptyList()
        for ((a1, b1) in Port.liens()) {
            val off = a1 in eteints || b1 in eteints
            val route = setOf(a1, b1) in surChemin
            val c = when { route -> EspaceDessin.VIOLET; off -> a(EspaceDessin.DOUX, 70); else -> a(EspaceDessin.CYAN, 120) }
            tl.ligne(px(a1), py(a1), px(b1), py(b1), c, (if (route) 3.2f else 1.6f) * z, if (off) 5 * z else 0f, if (off) 5 * z else 0f)
        }
        for (m in Port.machines()) {
            val off = m.id in eteints
            val cx = px(m.id); val cy = py(m.id)
            val coul = when { m.role == "camp" -> EspaceDessin.VERT; m.role == "routeur" -> 0xFFFFD54F.toInt(); off -> EspaceDessin.DOUX
                else -> EspaceDessin.CYAN }
            if (!off) tl.lueur(cx, cy, 20 * z, a(coul, 70))
            val nom = "${m.icone} ${m.id}"
            val bw = tl.mesure(nom, 12.5f * z, true) + 18 * z
            tl.rrect(cx - bw / 2, cy - 12 * z, bw, 24 * z, 12 * z, if (off) 0xFF1A1C24.toInt() else 0xFF141826.toInt(), a(coul, if (off) 90 else 220), 1.6f * z)
            tl.texte(nom, cx, cy, 12.5f * z, if (off) EspaceDessin.DOUX else EspaceDessin.TEXTE, true, 'c')
            if (adresses) tl.texte(if (off) "✖ " + m.adresse else m.adresse, cx, cy + 20 * z, 10.5f * z, a(coul, if (off) 120 else 200), false, 'c', true)
        }
        // le messager qui avance sur le chemin (aller puis retour)
        if (chemin != null && chemin.size >= 2) {
            val p = ((phase % 1.0) + 1.0) % 1.0
            val f = if (p < 0.5) p * 2 else (1 - p) * 2
            val pts = chemin.map { px(it) to py(it) }
            val seg = pts.zipWithNext().map { (u, v) -> sqrt(((v.first - u.first) * (v.first - u.first) + (v.second - u.second) * (v.second - u.second)).toDouble()) }
            var reste = f * seg.sum()
            var k = 0
            while (k < seg.size - 1 && reste > seg[k]) { reste -= seg[k]; k++ }
            val t = if (seg[k] > 0) (reste / seg[k]).toFloat().coerceIn(0f, 1f) else 0f
            val ex = pts[k].first + (pts[k + 1].first - pts[k].first) * t
            val ey = pts[k].second + (pts[k + 1].second - pts[k].second) * t
            enveloppe(tl, ex - 13 * z, ey - 30 * z, 26 * z, 17 * z, EspaceDessin.VIOLET, z)
        }
    }
}
