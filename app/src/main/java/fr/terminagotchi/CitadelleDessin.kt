package fr.terminagotchi

import kotlin.math.min
import kotlin.math.sin

/**
 * Le dessin de la Citadelle (interface Toile d'EspaceDessin, donc mêmes thèmes et mêmes captures JVM) :
 *  - cadenas : dans la vue déployée, un `chmod` ou un `umask` montre les trois rangées de cadenas (🙂 moi, 👥 mon club,
 *    🌍 les autres) × r w x ; d'abord comme avant, puis les clés qui changent s'allument (vert) ou s'éteignent ;
 *  - plan : le plan de la Citadelle (porte, cour, remparts, tours, cuisines, trésor, journaux, boîtes ; positions dans
 *    citadelle.json, « carte ») avec le tableau de garde (glitchs, processus fantômes, secrets ouverts) ;
 *  - forteresse : l'AFFICHAGE DE REPLI de l'illustration B3 (la Citadelle à remparts) tant que l'image n'existe pas :
 *    des remparts, deux tours, une porte et des glitchs qui rôdent, dessinés avec des rectangles (aucune image).
 */
object CitadelleDessin {
    private fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)

    private fun bit(t: String, k: Int) = t.getOrNull(k)?.let { it != '-' } ?: false

    /** Les cadenas d'un chmod / umask : trois groupes côte à côte (🙂 moi, 👥 mon club, 🌍 les autres) de trois cadenas
     *  r w x ; à mi-chemin (phase ≥ 0,45), le nouveau mode : les clés qui changent brillent (vert : donnée, rouge : reprise). */
    fun cadenas(tl: Toile, d: Deploie.Droits, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val p = ((phase % 1.0) + 1.0) % 1.0
        val apres = p >= 0.45
        tl.rrect(x, y, w, h, 14 * z, a(EspaceDessin.VERT, 10), a(EspaceDessin.VERT, 90), 1.2f * z)
        val titre = if (d.cmd == "chmod") "${d.fichier} : ${d.avant} → ${d.apres} (${d.octal})" else "umask ${d.mode} → ${d.apres} (${d.octal})"
        tl.texte(titre, x + w / 2, y + 13 * z, 11.5f * z, EspaceDessin.TEXTE, true, 'c', true)
        val noms = listOf("🙂 " + t("cit.qui.moi"), "👥 " + t("cit.qui.club"), "🌍 " + t("cit.qui.autres"))
        val gw = (w - 16 * z) / 3
        val avecNoms = h >= 60 * z                       // peu de place (une explication sur deux lignes) : les cadenas seuls
        val r = (if (avecNoms) min(11 * z, (h - 50 * z) / 2.4f) else min(9 * z, (h - 26 * z) / 2.4f)).coerceAtLeast(4 * z)
        val cy = if (avecNoms) y + h - r * 1.4f - 6 * z else y + 24 * z + (h - 24 * z) / 2
        for (k in 0 until 3) {
            val gx = x + 8 * z + gw * k
            if (avecNoms) tl.texte(noms[k], gx + gw / 2, y + 30 * z, 10.5f * z, EspaceDessin.DOUX, false, 'c')
            else if (k > 0) tl.ligne(gx, cy - r * 1.2f, gx, cy + r * 1.2f, a(EspaceDessin.DOUX, 80), 1 * z)
            for (j in 0 until 3) {
                val avantOn = bit(d.avant, 3 * k + j)
                val apresOn = bit(d.apres, 3 * k + j)
                val on = if (apres) apresOn else avantOn
                val change = apres && avantOn != apresOn
                val cx = gx + gw * (j + 0.5f) / 3
                val c = if (on) EspaceDessin.VERT else EspaceDessin.DOUX
                if (change) tl.lueur(cx, cy, r * 2.4f, a(if (on) EspaceDessin.VERT else EspaceDessin.ROUGE, 110))
                cadenas1(tl, cx, cy, r, c, on, z)
                tl.texte("rwx"[j].toString(), cx, cy + r * 0.3f, r * 1.0f, if (on) EspaceDessin.FOND else EspaceDessin.DOUX, true, 'c', true)
            }
        }
    }

    /** Un cadenas pixel : le corps et l'anse (ouverte quand la clé est donnée). */
    fun cadenas1(tl: Toile, cx: Float, cy: Float, r: Float, c: Int, ouvert: Boolean, z: Float) {
        tl.rrect(cx - r, cy - r * 0.35f, 2 * r, r * 1.3f, 3 * z, if (ouvert) c else a(c, 40), c, 1.4f * z)
        val dx = if (ouvert) r * 0.55f else 0f
        tl.ligne(cx - r * 0.55f + dx, cy - r * 0.35f, cx - r * 0.55f + dx, cy - r, c, 1.6f * z)
        tl.ligne(cx - r * 0.55f + dx, cy - r, cx + r * 0.55f + dx, cy - r, c, 1.6f * z)
        tl.ligne(cx + r * 0.55f + dx, cy - r, cx + r * 0.55f + dx, cy - (if (ouvert) r * 0.7f else r * 0.35f), c, 1.6f * z)
    }

    private fun pos(id: String): Pair<Float, Float> {
        val p = Citadelle.donnees().optJSONObject("carte")?.optJSONArray(id) ?: return 0.5f to 0.5f
        return p.getDouble(0).toFloat() to p.getDouble(1).toFloat()
    }

    /** Le plan de la Citadelle et son tableau de garde (glitchs : points rouges qui clignotent dans les lieux touchés). */
    fun plan(tl: Toile, glitchs: List<String>, processus: Int, secrets: Int, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, 0xFF101320.toInt(), a(EspaceDessin.CYAN, 90), 1.2f * z)
        val lieux = listOf("porte", "cour", "remparts", "tours", "cuisines", "tresor", "journaux", "boites")
        val mx = 40 * z; val my = 24 * z
        fun px(id: String) = x + mx + pos(id).first * (w - 2 * mx)
        fun py(id: String) = y + my + pos(id).second * (h - 2 * my - 30 * z)
        for (l in lieux) if (l != "cour") tl.ligne(px("cour"), py("cour"), px(l), py(l), a(EspaceDessin.CYAN, 80), 1.4f * z, 4 * z, 4 * z)
        val touches = glitchs.map { it.substringBefore('/') }.toSet()
        for (l in lieux) {
            val glitch = l in touches
            val c = if (glitch) EspaceDessin.ROUGE else EspaceDessin.CYAN
            val nom = Maison.ICONES["citadelle"] + " " + l
            val bw = tl.mesure(nom, 11.5f * z, true) + 16 * z
            if (glitch) tl.lueur(px(l), py(l), 22 * z, a(EspaceDessin.ROUGE, (80 + 60 * sin(phase * 6.28)).toInt()))
            tl.rrect(px(l) - bw / 2, py(l) - 11 * z, bw, 22 * z, 11 * z, 0xFF141826.toInt(), a(c, 210), 1.5f * z)
            tl.texte(nom, px(l), py(l), 11.5f * z, EspaceDessin.TEXTE, true, 'c')
        }
        val ind = Citadelle.tableau(glitchs.size, processus, secrets)
        var bx = x + 14 * z
        for ((nom, v, vert) in ind) {
            val s = (if (vert) "✔ " else "✖ ") + t("cit.tableau.$nom") + " " + v
            val bw = tl.mesure(s, 11 * z, true) + 18 * z
            tl.rrect(bx, y + h - 30 * z, bw, 22 * z, 11 * z, a(if (vert) EspaceDessin.VERT else EspaceDessin.ROUGE, 30),
                a(if (vert) EspaceDessin.VERT else EspaceDessin.ROUGE, 180), 1.2f * z)
            tl.texte(s, bx + bw / 2, y + h - 19 * z, 11 * z, EspaceDessin.TEXTE, true, 'c')
            bx += bw + 8 * z
        }
    }

    /** Le repli de l'illustration B3 : la forteresse dessinée (remparts crénelés, deux tours, la porte, des glitchs). */
    fun forteresse(tl: Toile, phase: Double, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rect(x, y, w, h, 0xFF141A33.toInt())
        tl.rect(x, y + h * 0.78f, w, h * 0.22f, 0xFF1F3B2A.toInt())
        val pierre = 0xFF6B7487.toInt(); val sombre = 0xFF464E60.toInt()
        val mx = x + w * 0.18f; val mw = w * 0.64f; val my = y + h * 0.42f; val mh = h * 0.38f
        tl.rect(mx, my, mw, mh, pierre)
        val cren = (mw / (14 * z)).toInt().coerceAtLeast(4)
        for (i in 0 until cren step 2) tl.rect(mx + i * mw / cren, my - 10 * z, mw / cren, 10 * z, pierre)
        for (tx in listOf(x + w * 0.10f, x + w * 0.74f)) {
            tl.rect(tx, y + h * 0.24f, w * 0.16f, h * 0.56f, sombre)
            for (i in 0 until 4 step 2) tl.rect(tx + i * w * 0.04f, y + h * 0.24f - 10 * z, w * 0.04f, 10 * z, sombre)
            tl.rect(tx + w * 0.065f, y + h * 0.36f, w * 0.03f, h * 0.06f, EspaceDessin.JAUNE)
        }
        tl.rrect(x + w * 0.45f, my + mh * 0.45f, w * 0.10f, mh * 0.55f, 12 * z, 0xFF2A1E14.toInt(), 0xFF8A6A3A.toInt(), 2 * z)
        tl.texte("🛡", x + w * 0.5f, my + mh * 0.22f, 22 * z, EspaceDessin.TEXTE, true, 'c')
        for (k in 0 until 5) {           // les glitchs qui rôdent au loin (des carrés qui clignotent)
            val gx = x + w * (0.06f + 0.2f * k) + 6 * z * sin(phase * 6.28 + k).toFloat()
            val gy = y + h * 0.86f + 4 * z * sin(phase * 9.0 + k * 2).toFloat()
            val al = (120 + 100 * sin(phase * 12 + k)).toInt()
            tl.rect(gx, gy, 6 * z, 6 * z, a(EspaceDessin.ROUGE, al)); tl.rect(gx + 7 * z, gy - 4 * z, 4 * z, 4 * z, a(EspaceDessin.VIOLET, al))
        }
        tl.texte(t("hist.citadelle.titre"), x + w / 2, y + h * 0.10f, 18 * z, EspaceDessin.TEXTE, true, 'c')
    }
}
