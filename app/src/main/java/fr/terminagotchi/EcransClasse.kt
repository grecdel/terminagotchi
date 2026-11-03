package fr.terminagotchi

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RadialGradient
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View
import fr.terminagotchi.EspaceDessin.BORD
import fr.terminagotchi.EspaceDessin.BORD_FORT
import fr.terminagotchi.EspaceDessin.CYAN
import fr.terminagotchi.EspaceDessin.DOUX
import fr.terminagotchi.EspaceDessin.FOND
import fr.terminagotchi.EspaceDessin.JAUNE
import fr.terminagotchi.EspaceDessin.PALE
import fr.terminagotchi.EspaceDessin.PANNEAU
import fr.terminagotchi.EspaceDessin.PANNEAU2
import fr.terminagotchi.EspaceDessin.ROSE
import fr.terminagotchi.EspaceDessin.TEXTE
import fr.terminagotchi.EspaceDessin.VERT
import fr.terminagotchi.EspaceDessin.VIOLET
import fr.terminagotchi.EspaceDessin.Zone
import fr.terminagotchi.EspaceDessin.a

/** Un pinceau Canvas simple (l'écran projecteur, la place de la classe, la carte de visite). */
class ToileSimple : Toile {
    var cv: Canvas? = null
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val pImg = Paint()
    private val r = RectF()
    private val bitmaps = HashMap<String, Bitmap>()

    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { p.style = Paint.Style.FILL; p.color = c; p.shader = null; cv?.drawRect(x, y, x + w, y + h, p) }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, rr: Float, fond: Int?, bord: Int?, ep: Float) {
        r.set(x, y, x + w, y + h); val ra = minOf(rr, w / 2, h / 2); p.shader = null
        if (fond != null) { p.style = Paint.Style.FILL; p.color = fond; cv?.drawRoundRect(r, ra, ra, p) }
        if (bord != null && ep > 0) { p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = bord; cv?.drawRoundRect(r, ra, ra, p) }
        p.style = Paint.Style.FILL
    }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { p.style = Paint.Style.FILL; p.color = c; p.shader = null; r.set(cx - rx, cy - ry, cx + rx, cy + ry); cv?.drawOval(r, p) }
    override fun cercle(cx: Float, cy: Float, rr: Float, c: Int, ep: Float) { p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = c; p.shader = null; cv?.drawCircle(cx, cy, rr, p); p.style = Paint.Style.FILL }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) {
        p.style = Paint.Style.STROKE; p.strokeWidth = ep; p.color = c; p.shader = null
        p.pathEffect = if (plein > 0) DashPathEffect(floatArrayOf(plein, vide), dec) else null
        cv?.drawLine(x1, y1, x2, y2, p); p.pathEffect = null; p.style = Paint.Style.FILL
    }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) {
        val ch = Path(); ch.moveTo(xs[0], ys[0]); for (i in 1 until xs.size) ch.lineTo(xs[i], ys[i]); ch.close()
        p.style = Paint.Style.FILL; p.color = c; p.shader = null; cv?.drawPath(ch, p)
    }
    private fun police(taille: Float, gras: Boolean, mono: Boolean) {
        p.textSize = taille; p.setLetterSpacing(0f)
        p.typeface = when { mono && gras -> Typeface.create(Typeface.MONOSPACE, Typeface.BOLD); mono -> Typeface.MONOSPACE; gras -> Typeface.DEFAULT_BOLD; else -> Typeface.DEFAULT }
    }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) {
        police(taille, gras, mono); p.style = Paint.Style.FILL; p.color = c; p.shader = null
        p.textAlign = when (ancre) { 'c' -> Paint.Align.CENTER; 'd' -> Paint.Align.RIGHT; else -> Paint.Align.LEFT }
        val fm = p.fontMetrics; cv?.drawText(s, x, y - (fm.ascent + fm.descent) / 2, p); p.textAlign = Paint.Align.LEFT
    }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean): Float { police(taille, gras, mono); return p.measureText(s) }
    override fun lueur(cx: Float, cy: Float, rr: Float, c: Int) {
        if (rr <= 0) return
        p.style = Paint.Style.FILL; p.shader = RadialGradient(cx, cy, rr, c, c and 0x00FFFFFF, Shader.TileMode.CLAMP); cv?.drawCircle(cx, cy, rr, p); p.shader = null
    }
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) {
        val b = bitmaps.getOrPut(c.cle) { if (bitmaps.size > 300) bitmaps.clear(); Bitmap.createBitmap(c.argb, c.w, c.h, Bitmap.Config.ARGB_8888) }
        val k = cv ?: return
        pImg.isFilterBitmap = lisse
        k.save(); k.translate(ax, ay); k.scale(if (miroir) -sx else sx, sy)
        k.drawBitmap(b, Rect(0, 0, c.w, c.h), RectF(-c.ax * e, -c.ay * e, (c.w - c.ax) * e, (c.h - c.ay) * e), pImg)
        k.restore()
    }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) {}
    override fun clip(x: Float, y: Float, w: Float, h: Float) { cv?.save(); cv?.clipRect(x, y, x + w, y + h) }
    override fun declip() { cv?.restore() }
}

/** Les dessins (Toile, coordonnées logiques) : l'écran projecteur 1600 × 900, la carte de visite 750 × 1050, la place. */
object EcransDessin {
    private fun couper(tl: Toile, s: String, l: Float, taille: Float): List<String> {
        val out = mutableListOf<String>()
        for (para in s.split("\n")) {
            var cour = ""
            for (mot in para.split(" ")) {
                val essai = if (cour.isEmpty()) mot else "$cour $mot"
                if (cour.isNotEmpty() && tl.mesure(essai, taille) > l) { out.add(cour); cour = mot } else cour = essai
            }
            out.add(cour)
        }
        return out
    }

    private fun court(tl: Toile, s: String, l: Float, taille: Float, mono: Boolean = false): String {
        if (tl.mesure(s, taille, false, mono) <= l) return s
        var x = s
        while (x.isNotEmpty() && tl.mesure("$x…", taille, false, mono) > l) x = x.dropLast(1)
        return "$x…"
    }

    private fun sansMarques(s: String) = s.replace("`", "")

    private fun creature(tl: Toile, al: Poses.Album?, k: Int, cx: Float, pieds: Float, haut: Float) {
        al ?: return
        var e = haut / maxOf(1, al.ref)
        if (!al.lisse) e = maxOf(1f, e.toInt().toFloat())
        tl.ellipse(cx, pieds + 4, al.image("assis", 0).w * e * 0.32f, 9f, 0x5A000000)
        tl.cadre(al.image("assis", k), cx, pieds, e, false, al.lisse)
    }

    private fun bulle(tl: Toile, x: Float, y: Float, w: Float, texte: String, taille: Float = 22f) {
        val lignes = couper(tl, texte, w - 40, taille).take(4)
        val h = 30 + taille * 1.35f * lignes.size
        tl.rrect(x, y, w, h, 16f, 0xFA161A24.toInt(), BORD_FORT, 1f)
        tl.poly(floatArrayOf(x + w * 0.62f, x + w * 0.70f, x + w * 0.74f), floatArrayOf(y + h, y + h + 22, y + h), 0xFA161A24.toInt())
        for ((i, l) in lignes.withIndex()) tl.texte(l, x + 20, y + 15 + taille * 0.67f + i * taille * 1.35f, taille, TEXTE)
    }

    /** L'écran projecteur (comme seance.scene en Python). Zones : tout l'écran → « suivante », les boutons du bas. */
    fun tableau(tl0: Toile, m: Map<String, Any>?, al: Poses.Album?, k: Int, th: Apparence.Theme?): List<Zone> {
        val tl = if (th == null || th.sombre) tl0 else ToileTheme(tl0, th)
        val W = 1600f; val H = 900f
        val Z = mutableListOf(Zone(0f, 0f, W, H, "tab:suivante"))
        tl.rect(0f, 0f, W, H, FOND)
        tl.rrect(24f, 26f, 40f, 40f, 11f, a(VERT, 30), a(VERT, 140), 1f)
        tl.texte(">_", 44f, 46f, 15f, VERT, true, 'c', true)
        tl.texte("Terminagotchi", 78f, 37f, 18f, TEXTE, true)
        tl.texte(t("classe.tableau.sous"), 78f, 60f, 13f, DOUX)
        if (m == null) {
            tl.texte(t("classe.tableau.attente"), W / 2, H / 2 - 30, 34f, TEXTE, true, 'c')
            tl.texte(t("classe.tableau.attente.tel"), W / 2, H / 2 + 30, 22f, DOUX, false, 'c', true)
            return Z
        }
        val ch = Seances.chapitre(m["n"] as Int)
        val cw = tl.mesure(ch, 18f, true) + 60
        tl.rrect(W / 2 - cw / 2, 26f, cw, 40f, 20f, PANNEAU, BORD_FORT, 1f)
        tl.texte(ch, W / 2, 46f, 18f, TEXTE, true, 'c')
        val ph = t("classe.tableau.phase", "k" to m["k"], "n" to m["total"], "nom" to m["nom"])
        val pw = tl.mesure(ph, 15f) + 30
        tl.rrect(W - 24 - pw, 34f, pw, 24f, 12f, 0xFF1E1A0C.toInt(), a(JAUNE, 90), 1f)
        tl.texte(ph, W - 24 - pw / 2, 46f, 15f, JAUNE, false, 'c')
        val but = sansMarques(m["but"] as String); val question = sansMarques(m["question"] as String); val bl = sansMarques(m["bulle"] as String)
        when (val vue = m["vue"] as String) {
            "trace" -> {
                tl.rrect(24f, 92f, W - 48, H - 150, 18f, PANNEAU, a(VERT, 140), 1.5f)
                tl.texte(t("classe.tableau.recopier").uppercase(), 54f, 128f, 15f, VERT, true)
                var yy = 182f
                @Suppress("UNCHECKED_CAST")
                for (l in m["trace"] as List<String>) {
                    // les passages `…` sont des commandes : en vert, à chasse fixe
                    var xx = 54f
                    for ((i, morceau) in l.split("`").withIndex()) {
                        if (morceau.isEmpty()) continue
                        val code = i % 2 == 1
                        for (mot in if (code) listOf(morceau) else morceau.split(" ").map { "$it " }) {
                            val w = tl.mesure(mot, 34f, code, code)
                            if (xx + w > W - 330) { xx = 54f; yy += 46f }
                            tl.texte(mot, xx, yy, 34f, if (code) VERT else TEXTE, code, 'g', code); xx += w
                        }
                    }
                    yy += 62f
                }
                creature(tl, al, k, W - 164, H - 88, 150f)
            }
            "commun", "bilan", "lancement" -> {
                tl.rrect(24f, 92f, W - 48, H - 150, 18f, if (vue == "commun") a(VIOLET, 14) else PANNEAU, if (vue == "commun") a(VIOLET, 150) else BORD_FORT, 1.5f)
                val titre = mapOf("commun" to "classe.tableau.oral", "bilan" to "classe.tableau.fin", "lancement" to "classe.tableau.but").getValue(vue)
                tl.texte(t(titre).uppercase(), 60f, 132f, 15f, if (vue == "commun") VIOLET else JAUNE, true)
                var yy = 222f
                when (vue) {
                    "commun" -> {
                        for (l in couper(tl, question, W - 568, 56f).take(4)) { tl.texte(l, 60f, yy, 56f, TEXTE, true); yy += 76 }
                        tl.texte(t("classe.tableau.oral.aide"), 60f, yy + 20, 22f, DOUX)
                        bulle(tl, W - 464, 172f, 400f, bl)
                    }
                    "lancement" -> {
                        yy = 202f
                        for (l in couper(tl, but, W - 568, 44f).take(3)) { tl.texte(l, 60f, yy, 44f, TEXTE, true); yy += 60 }
                        tl.texte(t("classe.tableau.taper"), 60f, yy + 40, 24f, DOUX)
                        tl.texte("tg", 60f, yy + 100, 40f, VERT, true, 'g', true)
                        tl.texte("tg classe code ${m["code"]} " + t("classe.tableau.pseudo"), 60f, yy + 160, 40f, VERT, true, 'g', true)
                        tl.texte(t("classe.tableau.pseudo.aide"), 60f, yy + 210, 20f, PALE)
                    }
                    else -> {
                        tl.texte(t("classe.tableau.bravo"), 60f, yy, 50f, TEXTE, true)
                        tl.texte(t("classe.tableau.bilan"), 60f, yy + 90, 26f, DOUX)
                        tl.texte("tg classe bilan fichier", 60f, yy + 160, 40f, VERT, true, 'g', true)
                        tl.texte("tg classe fin", 60f, yy + 220, 40f, VERT, true, 'g', true)
                    }
                }
                creature(tl, al, k, W - 264, H - 98, 250f)
            }
            else -> {
                tl.rrect(24f, 92f, 1036f, 546f, 18f, PANNEAU, BORD_FORT, 1f)
                tl.texte(t("classe.tableau.but").uppercase(), 54f, 128f, 14f, JAUNE, true)
                var yy = 176f
                for (l in couper(tl, but, 976f, 40f).take(3)) { tl.texte(l, 54f, yy, 40f, TEXTE, true); yy += 54 }
                yy += 30
                tl.texte(t("classe.tableau.commande").uppercase(), 54f, yy, 14f, VERT, true)
                tl.texte(t("classe.tableau.cachee.aide"), 1030f, yy, 14f, PALE, false, 'd')
                yy += 56
                val cmd = m["commande"] as String
                if (cmd.isNotEmpty()) {
                    val bls = Deploie.blocs(cmd)
                    var taille = 42f
                    while (taille > 22 && bls.sumOf { (tl.mesure(it.t, taille, true, true) + 34).toDouble() } + 22 * bls.size > 976) taille -= 2
                    var bx = 54f
                    for (b in bls) {
                        val col = Deploie.COULEURS.getValue(b.g)
                        val bw = tl.mesure(b.t, taille, true, true) + 34
                        tl.rrect(bx, yy - taille * 0.85f, bw, taille * 1.7f, 12f, a(col, 30), col, 2f)
                        tl.texte(b.t, bx + bw / 2, yy, taille, col, true, 'c', true)
                        if (Confort.reglages(null).formes) tl.texte(Confort.FORMES[b.g] ?: "●", bx + bw - 10, yy - taille * 0.85f, 14f, col, true, 'c')
                        tl.texte(Deploie.nomGenre(b.g).uppercase(), bx + bw / 2, yy + taille * 0.85f + 22, 13f, col, true, 'c')
                        tl.texte(court(tl, Deploie.courte(b, bls), maxOf(110f, bw + 20), 15f), bx + bw / 2, yy + taille * 0.85f + 44, 15f, DOUX, false, 'c')
                        bx += bw + 22
                    }
                } else tl.texte(t(if (m["commande_cachee"] == true) "classe.tableau.cachee" else "classe.tableau.sans_commande"), 54f, yy, 28f, DOUX)
                tl.rrect(1076f, 92f, W - 24 - 1076, 546f, 18f, PANNEAU, BORD_FORT, 1f)
                bulle(tl, 1100f, 118f, W - 24 - 1076 - 48, bl)
                creature(tl, al, k, 1076 + (W - 24 - 1076) / 2, 598f, 220f)
                tl.rrect(24f, 654f, W - 48, 172f, 18f, a(VIOLET, 14), a(VIOLET, 150), 1.5f)
                tl.texte(t("classe.tableau.oral").uppercase(), 54f, 686f, 14f, VIOLET, true)
                tl.texte(court(tl, question, W - 140, 40f), 54f, 740f, 40f, TEXTE, true)
                tl.texte(t("classe.tableau.oral.plus_tard"), 54f, 794f, 18f, DOUX)
            }
        }
        // les boutons (sur la tablette, à la place des touches du clavier)
        var bx = 24f
        for ((act, lib) in listOf("precedente" to "‹", "commande" to "c · " + t("classe.tableau.b.commande"),
                "question" to "o · " + t("classe.tableau.b.question"), "trace" to "t · " + t("classe.tableau.b.trace"), "fermer" to "✕")) {
            val bw = tl.mesure(lib, 15f) + 30
            tl.rrect(bx, H - 40, bw, 30f, 9f, 0x10FFFFFF, BORD_FORT, 1f)
            tl.texte(lib, bx + bw / 2, H - 25, 15f, DOUX, false, 'c')
            Z.add(Zone(bx, H - 42, bw, 34f, "tab:$act"))
            bx += bw + 10
        }
        tl.texte(t("classe.tableau.sans_minuteur"), W - 24, H - 25, 15f, PALE, false, 'd')
        return Z
    }

    /** La carte de visite (comme carte_visite.scene en Python), 750 × 1050. */
    fun carte(tl: Toile, c: Map<String, Any>, al: Poses.Album?) {
        val W = CarteVisite.W; val H = CarteVisite.H
        tl.rect(0f, 0f, W, H, 0xFF05070A.toInt())
        tl.rrect(18f, 18f, W - 36, H - 36, 26f, PANNEAU, a(VERT, 200), 3f)
        for (i in 0 until 14) {
            val x = 40f + (i * 53) % (W - 80); val y0 = H - 40 - (i * 37) % 260
            val dx = if (i % 2 == 1) 18f else -18f
            tl.ligne(x, H - 24, x, y0, a(VERT, 40), 1.4f); tl.ligne(x, y0, x + dx, y0 - 18, a(VERT, 40), 1.4f); tl.ellipse(x + dx, y0 - 18, 2.6f, 2.6f, a(VERT, 90))
        }
        tl.texte("T E R M I N A G O T C H I", W / 2, 62f, 15f, VERT, true, 'c')
        tl.rrect(70f, 92f, W - 140, 400f, 20f, 0xFF0D1016.toInt(), BORD_FORT, 1f)
        tl.lueur(W / 2, 92 + 400 * 0.58f, 200f, a(VERT, 34))
        creature(tl, al, 0, W / 2, 450f, 300f)
        var y = 562f
        val nom = c["nom"] as String
        if (nom.isNotEmpty()) { tl.texte(court(tl, nom, W - 120, 44f), W / 2, y, 44f, TEXTE, true, 'c'); y += 48 }
        tl.texte(court(tl, listOf(c["espece"], c["stade"], c["type"]).map { it as String }.filter { it.isNotEmpty() }.joinToString(" · "), W - 120, 19f), W / 2, y, 19f, DOUX, false, 'c')
        y += 52
        val cw = 180f; val gap = 18f; val x0 = W / 2 - (3 * cw + 2 * gap) / 2
        for ((i, v) in listOf(Triple(c["niveau"], "cv.niveau", JAUNE), Triple(c["jours"], "cv.jours", CYAN), Triple(c["commandes"], "cv.commandes", VERT)).withIndex()) {
            val xx = x0 + i * (cw + gap)
            tl.rrect(xx, y, cw, 86f, 14f, a(v.third, 20), a(v.third, 170), 1.5f)
            tl.texte("${v.first}", xx + cw / 2, y + 34, 30f, v.third, true, 'c')
            tl.texte(t(v.second), xx + cw / 2, y + 66, 14f, DOUX, false, 'c')
        }
        y += 124
        @Suppress("UNCHECKED_CAST")
        if ((c["gouts"] as List<String>).isNotEmpty()) tl.texte(t("cv.gouts"), 80f, y, 16f, TEXTE, true)
        var xx = 80 + tl.mesure(t("cv.gouts"), 16f, true) + 20
        @Suppress("UNCHECKED_CAST")
        for (g in c["gouts"] as List<String>) {
            val gw = tl.mesure(g, 16f, true, true) + 24
            if (xx + gw > W - 70) break
            tl.rrect(xx, y - 16, gw, 32f, 9f, a(VERT, 22), a(VERT, 160), 1.2f)
            tl.texte(g, xx + gw / 2, y, 16f, VERT, true, 'c', true)
            xx += gw + 10
        }
        y += 48
        @Suppress("UNCHECKED_CAST")
        val titres = c["titres"] as List<Pair<String, String>>
        if (titres.isNotEmpty()) {
            xx = 80f
            for ((txt, col) in titres) {
                val rgb = if (col == "arc" || col.length != 7) JAUNE else (0xFF000000.toInt() or col.substring(1).toInt(16))
                val s = court(tl, txt, 260f, 13f)
                val w = tl.mesure(s, 13f) + 30
                if (xx + w > W - 70) break
                tl.rrect(xx, y - 12, w, 24f, 12f, a(rgb, 26), a(rgb, 90), 1f)
                tl.ellipse(xx + 13, y, 3.5f, 3.5f, rgb)
                tl.texte(s, xx + 21, y, 13f, rgb)
                xx += w + 8
            }
            y += 40
        }
        val ec = c["eclos"] as String
        if (ec.isNotEmpty()) tl.texte(t("cv.eclos", "date" to ec), 80f, y, 15f, DOUX)
        tl.texte("terminagotchi · image CC BY-NC-SA 4.0", W / 2, H - 46, 13f, PALE, false, 'c')
    }

    /** La place de la classe sur le téléphone (en dp : z = densité). */
    fun place(tl: Toile, cl: Place.Client, albums: (String, String) -> Poses.Album?, w: Float, z: Float, t0: Double): List<Zone> {
        val Z = mutableListOf<Zone>()
        tl.rect(0f, 0f, w, 10000f, FOND)
        tl.texte("⌂ " + t("classe.place.titre"), 16 * z, 30 * z, 19 * z, TEXTE, true)
        tl.texte(t("classe.place.sous", "n" to cl.postes.size), 16 * z, 52 * z, 12 * z, DOUX)
        tl.texte("✕", w - 20 * z, 30 * z, 18 * z, DOUX, false, 'd')
        Z.add(Zone(w - 60 * z, 0f, 60 * z, 56 * z, "place:fermer"))
        if (cl.etat != "ici") {
            val k = when (cl.etat) { "cherche" -> "classe.place.cherche"; "fermee" -> "classe.place.fermee_ecran"; else -> "classe.place.absente_ecran" }
            for ((i, l) in couper(tl, t(k), w - 40 * z, 17 * z).withIndex()) tl.texte(l, w / 2, 160 * z + i * 24 * z, 17 * z, TEXTE, true, 'c')
            for ((i, l) in couper(tl, t("classe.place.absente.aide.tel"), w - 40 * z, 13 * z).withIndex()) tl.texte(l, w / 2, 230 * z + i * 18 * z, 13 * z, DOUX, false, 'c')
            return Z
        }
        val maintenant = System.currentTimeMillis()
        val bulle = cl.recus.lastOrNull()?.takeIf { maintenant - it.third < 8000 }?.let { Place.SYMBOLES[it.first] + " " + t("classe.geste." + Place.GESTES[it.first]) + " !" }
        val cw = (w - 16 * z * 2 - 10 * z) / 2
        val ch = 200 * z
        for ((i, p) in cl.postes.withIndex()) {
            val cx = 16 * z + (i % 2) * (cw + 10 * z); val cy = 70 * z + (i / 2) * (ch + 10 * z)
            val moi = p.poste == cl.poste
            tl.rrect(cx, cy, cw, ch, 14 * z, PANNEAU2, if (moi) a(JAUNE, 200) else BORD, (if (moi) 1.6f else 1f) * z)
            tl.texte(t("classe.place.poste", "n" to p.poste), cx + 12 * z, cy + 20 * z, 13 * z, if (moi) JAUNE else TEXTE, true)
            creature(tl, albums(p.espece, p.stade), (t0 * 8).toInt(), cx + cw / 2, cy + 120 * z, 84 * z)
            tl.texte(court(tl, Place.nomEspece(p.espece) + " · " + Place.nomStade(p.stade), cw - 20 * z, 11.5f * z), cx + 12 * z, cy + 142 * z, 11.5f * z, DOUX)
            if (moi) {
                tl.texte(t("classe.place.cest_toi"), cx + 12 * z, cy + 176 * z, 12.5f * z, JAUNE, true)
                if (bulle != null) {
                    val bw = tl.mesure(bulle, 12 * z, true) + 18 * z
                    tl.rrect(cx + cw - bw - 8 * z, cy + 30 * z, bw, 24 * z, 12 * z, 0xFF1E1A0C.toInt(), a(ROSE, 200), 1f * z)
                    tl.texte(bulle, cx + cw - bw / 2 - 8 * z, cy + 42 * z, 12 * z, ROSE, true, 'c')
                }
            } else {
                val gw = (cw - 24 * z - 12 * z) / 3
                for (g in 0 until 3) {
                    val bx = cx + 12 * z + g * (gw + 6 * z)
                    tl.rrect(bx, cy + ch - 40 * z, gw, 30 * z, 9 * z, 0x10FFFFFF, BORD_FORT, 1f * z)
                    tl.texte(Place.SYMBOLES[g], bx + gw / 2, cy + ch - 25 * z, 16 * z, TEXTE, false, 'c')
                    Z.add(Zone(bx, cy + ch - 42 * z, gw, 34 * z, "place:geste:${p.poste}:$g"))
                }
            }
        }
        val py = 70 * z + ((cl.postes.size + 1) / 2) * (ch + 10 * z) + 6 * z
        tl.rrect(16 * z, py, w - 32 * z, 76 * z, 12 * z, 0x0EFFFFFF, BORD, 1f * z)
        var yy = py + 20 * z
        for (l in couper(tl, t("classe.place.regle"), w - 60 * z, 12 * z).take(2)) { tl.texte(l, 28 * z, yy, 12 * z, TEXTE, true); yy += 17 * z }
        tl.texte(court(tl, if (cl.message.isNotEmpty()) cl.message else t("classe.place.regle2"), w - 60 * z, 11 * z), 28 * z, yy, 11 * z, DOUX)
        return Z
    }
}

/**
 * Un écran plein (au-dessus du terminal) pour le mode classe : « tableau » (l'écran projecteur, sur une tablette
 * branchée), « place » (la place de la classe), « carte » (la carte de visite, avec Enregistrer et Partager).
 */
class EcranVue(ctx: Context, private val jeu: Jeu, val genre: String, private val agir: (String) -> Unit) : View(ctx) {
    private val d = resources.displayMetrics.density
    private val toile = ToileSimple()
    private var zones: List<Zone> = emptyList()
    private var ech = floatArrayOf(1f, 0f, 0f)
    private val t0 = System.nanoTime()
    private var album: Poses.Album? = null
    private val albums = HashMap<String, Poses.Album?>()
    var client: Place.Client? = null
    var avecNom = true
    private var animer = false
    private var dernierRelu = 0L

    init {
        Poses.charger(ctx)
        album = try { Poses.album(jeu) } catch (e: Exception) { null }
        setBackgroundColor(FOND)
    }

    private val image = object : Runnable {
        override fun run() {
            if (!animer) return
            val cl = client
            if (cl != null && System.currentTimeMillis() - dernierRelu > 2000) {
                dernierRelu = System.currentTimeMillis()
                Thread { try { if (cl.poste == null) cl.rejoindre() else cl.relire() } catch (e: Exception) { cl.etat = "absente" }; post { invalidate() } }.start()
            }
            invalidate()
            postDelayed(this, if (genre == "carte") 1000L else 250L)
        }
    }

    override fun onAttachedToWindow() { super.onAttachedToWindow(); animer = true; post(image) }
    override fun onDetachedFromWindow() { animer = false; removeCallbacks(image); super.onDetachedFromWindow() }

    private fun maintenant() = (System.nanoTime() - t0) / 1e9

    /** La carte de visite en image (pour l'enregistrer ou la partager). */
    fun bitmapCarte(): Bitmap {
        val b = Bitmap.createBitmap(CarteVisite.W.toInt(), CarteVisite.H.toInt(), Bitmap.Config.ARGB_8888)
        val tl = ToileSimple(); tl.cv = Canvas(b)
        EcransDessin.carte(tl, CarteVisite.contenu(jeu, avecNom), album)
        return b
    }

    override fun onDraw(cv: Canvas) {
        toile.cv = cv
        val w = width.toFloat(); val h = height.toFloat()
        when (genre) {
            "tableau" -> {
                val e = minOf(w / 1600f, h / 900f); val ox = (w - 1600 * e) / 2; val oy = (h - 900 * e) / 2
                ech = floatArrayOf(e, ox, oy)
                cv.save(); cv.translate(ox, oy); cv.scale(e, e)
                zones = EcransDessin.tableau(toile, Seances.e(jeu)?.let { Seances.modele(it) }, album, (maintenant() * 4).toInt(), Apparence.theme(jeu))
                cv.restore()
            }
            "place" -> {
                ech = floatArrayOf(1f, 0f, 0f)
                val cl = client ?: return
                zones = EcransDessin.place(toile, cl, { esp, st -> albums.getOrPut("$esp/$st") {
                    if (st == "oeuf") null else Bestiaire.espece(esp)?.let { try { Poses.albumEspece(it, st, false) } catch (x: Exception) { null } } } }, w, d, maintenant())
            }
            else -> {
                // la carte en haut, les boutons en dessous
                val zc = minOf((w - 32 * d) / CarteVisite.W, (h - 200 * d) / CarteVisite.H)
                val ox = (w - CarteVisite.W * zc) / 2; val oy = 56 * d
                toile.texte(t("cv.titre"), 16 * d, 28 * d, 18 * d, TEXTE, true)
                toile.texte("✕", w - 20 * d, 28 * d, 18 * d, DOUX, false, 'd')
                cv.save(); cv.translate(ox, oy); cv.scale(zc, zc)
                EcransDessin.carte(toile, CarteVisite.contenu(jeu, avecNom), album)
                cv.restore()
                var y = oy + CarteVisite.H * zc + 14 * d
                val Z = mutableListOf(Zone(w - 60 * d, 0f, 60 * d, 56 * d, "carte:fermer"))
                toile.rrect(16 * d, y, w - 32 * d, 40 * d, 12 * d, PANNEAU, BORD, 1f * d)
                toile.texte(t("cv.montrer_nom", "nom" to jeu.nom), 28 * d, y + 20 * d, 13 * d, TEXTE, true)
                toile.rrect(w - 76 * d, y + 9 * d, 44 * d, 22 * d, 11 * d, if (avecNom) a(JAUNE, 70) else 0x14FFFFFF, if (avecNom) a(JAUNE, 200) else BORD_FORT, 1f * d)
                toile.ellipse(w - (if (avecNom) 43 else 65) * d, y + 20 * d, 8 * d, 8 * d, if (avecNom) JAUNE else DOUX)
                Z.add(Zone(16 * d, y, w - 32 * d, 40 * d, "carte:nom"))
                y += 50 * d
                val bw = (w - 32 * d - 10 * d) / 2
                toile.rrect(16 * d, y, bw, 40 * d, 12 * d, a(VERT, 26), a(VERT, 160), 1f * d)
                toile.texte(t("cv.enregistrer"), 16 * d + bw / 2, y + 20 * d, 13 * d, VERT, true, 'c')
                Z.add(Zone(16 * d, y, bw, 40 * d, "carte:enregistrer"))
                toile.rrect(26 * d + bw, y, bw, 40 * d, 12 * d, PANNEAU, BORD_FORT, 1f * d)
                toile.texte(t("cv.partager"), 26 * d + bw * 1.5f, y + 20 * d, 13 * d, TEXTE, true, 'c')
                Z.add(Zone(26 * d + bw, y, bw, 40 * d, "carte:partager"))
                toile.texte(t("cv.partage.tel"), 16 * d, y + 58 * d, 11 * d, PALE)
                zones = Z
            }
        }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_UP) return true
        val x = (e.x - ech[1]) / ech[0]; val y = (e.y - ech[2]) / ech[0]
        val a = zones.lastOrNull { it.dedans(x, y) }?.action ?: return true
        when {
            a.startsWith("place:geste:") -> {
                val p = a.split(":"); val cl = client
                if (cl != null) Thread { val ok = cl.geste(p[2].toInt(), p[3].toInt()); cl.message = if (ok) "" else t("classe.place.attends"); post { invalidate() } }.start()
            }
            a == "carte:nom" -> avecNom = !avecNom
            else -> agir(a)
        }
        performClick()
        invalidate()
        return true
    }

    override fun performClick(): Boolean { super.performClick(); return true }
}
