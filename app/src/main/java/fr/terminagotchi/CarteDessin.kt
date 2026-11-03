package fr.terminagotchi

import org.json.JSONObject
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * La carte du Terminaworld dans l'onglet Carte du téléphone (idées 31 à 39, 88), le même dessin que la carte du PC
 * (pc/tg/carte_scene.py) : la carte mélangée vivant / endormi (Reveil.kt), la vague d'un biome qui se réveille, un
 * lieu qui s'allume, un chemin qui se dessine ; les lieux (vert allumé, jaune ouvert, gris « ? »), les chemins, les
 * lieux secrets trouvés, les habitants (« ! »), l'événement rare, la météo, les étoiles la nuit, la saison.
 * On touche un lieu → sa fiche : « ▶ Y aller » ÉCRIT la commande cd dans le terminal (l'enfant appuie sur Entrée),
 * « ? En savoir plus ». Boutons + et − pour zoomer, un doigt fait glisser la carte. Le livre des gardiens, le carnet.
 */
object CarteDessin {
    val VERT = EspaceDessin.VERT
    val JAUNE = EspaceDessin.JAUNE
    val TEXTE = EspaceDessin.TEXTE
    val DOUX = EspaceDessin.DOUX
    val PALE = EspaceDessin.PALE
    val CYAN = EspaceDessin.CYAN
    val GRIS = 0xFF969CAA.toInt()
    fun coul(et: String) = when (et) { "allume" -> VERT; "ouvert" -> JAUNE; else -> GRIS }
    private fun a(c: Int, al: Int) = EspaceDessin.a(c, al)
    private fun rgb(r: Int, g: Int, b: Int, al: Int = 255) = (al.coerceIn(0, 255) shl 24) or (r shl 16) or (g shl 8) or b

    class Anim(val type: String, val avant: String, val apres: String, val c: Pair<Float, Float>, val texte: String,
               val duree: Double, val lieu: String? = null, val pts: List<Pair<Float, Float>> = emptyList()) {
        var t0 = 0.0
    }

    class HabitantVu(val h: Reveil.Habitant, val nom: String, val texte: String, val album: Poses.Album?)

    class Modele {
        var photo = "reveil:"
        var anim: Anim? = null
        var p = 0f
        var lieux = listOf<Reveil.Lieu>()
        var chemins = listOf<Triple<String, List<Pair<Float, Float>>, String>>()
        var secrets: Pair<List<Triple<String, Float, Float>>, Pair<Int, Int>> = emptyList<Triple<String, Float, Float>>() to (0 to 0)
        var habitants = listOf<HabitantVu>()
        var evt: JSONObject? = null
        var meteo = "calme"
        var moment = "jour"
        var saison = "ete"
        var fiche: String? = null
        var plus = false
        var livre = false
        var livrePage: Int? = null
        var livreOuverts = listOf<Int>()
        var gardiens = listOf<Pair<String, String>>()
        var gardAlbums = mapOf<String, Poses.Album?>()
        var livreFichier = false
        var carnet = false
        var carnetVus = listOf<String>()
        var iciLieu: String? = null
        var iciPiece: Pair<Float, Float>? = null
        var iciNom = ""
        var enCours: Pair<String, Pair<Float, Float>>? = null
        var zoom = 1f
        var cx = 0.5f
        var cy = 0.5f
        var t = 0.0
    }

    /** La carte (960×540) zoomée et décalée dans la zone : fraction de l'image → point de l'écran. */
    class Repere(val x: Float, val y: Float, val w: Float, val h: Float, zoom: Float, cx: Float, cy: Float) {
        val r = max(w / 960f, h / 540f) * zoom
        val iw = 960f * r
        val ih = 540f * r
        val ix: Float = (x + w / 2 - cx * iw).coerceIn(x + w - iw, x)
        val iy: Float = (y + h / 2 - cy * ih).coerceIn(y + h - ih, y)
        fun p(fx: Float, fy: Float) = (ix + fx * iw) to (iy + fy * ih)
        fun dedans(px: Float, py: Float, m: Float = 0f) = px >= x + m && px <= x + w - m && py >= y + m && py <= y + h - m
    }

    private fun h(vararg a: Int): Float {
        var x = 0L
        for (v in a) x = (x * 1103515245L + v.toLong() * 2654435761L + 12345L) and 0xFFFFFFFFL
        x = x xor (x ushr 13)
        x = (x * 1274126177L) and 0xFFFFFFFFL
        return (x and 0xFFFFFF).toFloat() / 0x1000000
    }

    fun dessiner(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, EspaceDessin.PANNEAU, EspaceDessin.BORD, 1f * z)
        val px = x + 8 * z; val py = y + 8 * z; val pw = w - 16 * z
        val panneau = m.fiche != null || m.livre || m.carnet
        val ph = if (panneau) min(pw * 0.6f, h * 0.48f) else h - 44 * z
        val R = Repere(px, py, pw, ph, m.zoom, m.cx, m.cy)
        tl.clip(px, py, pw, ph)
        val an = m.anim
        if (an != null && an.type != "chemin") {
            tl.photo(an.avant, R.ix, R.iy, R.iw, R.ih, 0f)
            val (cx, cy) = R.p(an.c.first, an.c.second)
            val rmax = hypot(max(cx - px, px + pw - cx), max(cy - py, py + ph - cy))
            val rr = (if (an.type == "lieu") 90 * R.r else rmax) * min(1f, m.p * 1.15f)
            tl.photoCercle(an.apres, R.ix, R.iy, R.iw, R.ih, cx, cy, rr)
        } else tl.photo(m.photo, R.ix, R.iy, R.iw, R.ih, 0f)
        Z.add(EspaceDessin.Zone(px, py, pw, ph, "rv:carte"))
        decor(tl, m, R, z)
        chemins(tl, m, R, z)
        evenement(tl, m, R, z)
        secrets(tl, m, R, z)
        lieux(tl, Z, m, R, z)
        habitants(tl, Z, m, R, z)
        if (an != null) animation(tl, m, an, R, z)
        tl.declip()
        if (an != null) Z.add(EspaceDessin.Zone(px, py, pw, ph, "rv:passer"))
        // zoom
        if (an == null) for ((i, s) in listOf("+", "−").withIndex()) {
            val bx = px + pw - 44 * z; val by = py + 10 * z + i * 46 * z
            tl.rrect(bx, by, 36 * z, 36 * z, 10 * z, 0xE60A0C12.toInt(), EspaceDessin.BORD_FORT, 1f * z)
            tl.texte(s, bx + 18 * z, by + 18 * z, 20 * z, TEXTE, true, 'c')
            Z.add(EspaceDessin.Zone(bx, by, 36 * z, 36 * z, if (i == 0) "rv:zoom+" else "rv:zoom-"))
        }
        val by = py + ph + 8 * z
        val bh = y + h - by - 36 * z
        when {
            m.fiche?.startsWith("hab:") == true -> ficheHabitant(tl, Z, m, px, by, pw, bh, z)
            m.fiche != null -> fiche(tl, Z, m, px, by, pw, bh, z)
            m.livre -> livre(tl, Z, m, px, by, pw, bh, z)
            m.carnet -> carnet(tl, Z, m, px, by, pw, bh, z)
        }
        legende(tl, Z, m, x, y + h - 20 * z, w, z)
    }

    // ---------------------------------------------------------------- le décor
    private fun decor(tl: Toile, m: Modele, R: Repere, z: Float) {
        val t = m.t
        if (m.moment == "nuit") for (i in 0 until 70) {
            val (sx, sy) = R.p(h(i, 1), h(i, 2) * 0.42f)
            val al = (140 + 115 * (0.5 + 0.5 * sin(t * (1.3 + h(i, 3)) + i))).toInt()
            val s = (if (h(i, 4) < 0.7f) 2f else 3f) * z * 0.7f
            tl.rect(sx, sy, s, s, rgb(230, 235, 255, al))
        }
        val (n, c, vit) = when (m.saison) { "hiver" -> Triple(60, rgb(240, 245, 255, 210), 0.025); "printemps" -> Triple(26, rgb(255, 170, 210, 200), 0.018)
            "automne" -> Triple(22, rgb(255, 150, 60, 200), 0.02); else -> Triple(0, 0, 0.0) }
        for (i in 0 until n) {
            val fx = ((h(i, 5) + 0.02 * sin(t * 0.7 + i)) % 1.0).toFloat()
            val fy = ((h(i, 6) + t * (vit + 0.02 * h(i, 7))) % 1.0).toFloat()
            val (sx, sy) = R.p(fx, fy)
            tl.rect(sx, sy, 2.2f * z, 2.2f * z, c)
        }
        when (m.meteo) {
            "pluie" -> for (i in 0 until 90) {
                val (sx, sy) = R.p(h(i, 20), ((h(i, 21) + t * (0.25 + 0.2 * h(i, 22))) % 1.1 - 0.1).toFloat())
                for (j in 0 until 4) tl.rect(sx, sy + j * 4 * z, 2.2f * z, 2.2f * z, rgb(170, 255, 200, 60 + 45 * j))
            }
            "eclairs" -> {
                val o = m.lieux.firstOrNull { it.id == "ondes" }
                val ox = o?.x ?: 0.79f; val oy = o?.y ?: 0.09f
                for (k in 0 until 2) if ((t * 1.7 + k * 0.5) % 1.6 < 0.35) {
                    var ax = ox - 0.03f + 0.06f * k; var ay = 0f
                    for (j in 1 until 6) {
                        val bx = ax + if (j % 2 == 1) 0.012f else -0.016f; val byy = j * 0.045f
                        val p1 = R.p(ax, ay); val p2 = R.p(bx, byy)
                        tl.ligne(p1.first, p1.second, p2.first, p2.second, rgb(190, 220, 255, 200), 3 * z)
                        tl.ligne(p1.first, p1.second, p2.first, p2.second, rgb(255, 255, 255), 1.2f * z)
                        ax = bx; ay = byy
                    }
                }
                val (lx, ly) = R.p(ox, oy); tl.lueur(lx, ly, 60 * R.r, rgb(150, 200, 255, 60))
            }
            "arc" -> {
                val cf = m.lieux.firstOrNull { it.id == "carrefour" }
                val (cx, cy) = R.p(cf?.x ?: 0.5f, cf?.y ?: 0.49f)
                val cs = intArrayOf(rgb(255, 95, 109, 140), rgb(255, 159, 67, 140), rgb(255, 213, 79, 140), rgb(61, 220, 132, 140), rgb(95, 175, 255, 140), rgb(178, 132, 255, 140))
                for ((i, c2) in cs.withIndex()) {
                    val rr = (200 - i * 7) * R.r
                    var a0 = 180
                    while (a0 <= 360) {
                        val ax = cx + rr * cos(a0 * PI / 180).toFloat(); val ay = cy + rr * sin(a0 * PI / 180).toFloat() * 0.8f
                        tl.rect(ax - 1.5f * z, ay - 1.5f * z, 3 * z, 3 * z, c2); a0 += 4
                    }
                }
            }
            "brume" -> for (i in 0 until 9) {
                val (sx, sy) = R.p(((h(i, 30) + t * 0.008) % 1.2 - 0.1).toFloat(), 0.55f + 0.4f * h(i, 31))
                tl.ellipse(sx, sy, 130 * R.r, 26 * R.r, rgb(215, 222, 235, 34))
            }
        }
    }

    // ---------------------------------------------------------------- les chemins (idée 39)
    private fun chemins(tl: Toile, m: Modele, R: Repere, z: Float) {
        val an = m.anim
        for ((l, pts, et) in m.chemins) {
            if (an?.type == "chemin" && an.lieu == l) continue
            val ps = pts.map { R.p(it.first, it.second) }
            when (et) {
                "allume" -> {
                    for (i in 0 until ps.size - 1) tl.ligne(ps[i].first, ps[i].second, ps[i + 1].first, ps[i + 1].second, rgb(61, 220, 132, 150), 2f * z)
                    val lg = (0 until ps.size - 1).sumOf { hypot(ps[it + 1].first - ps[it].first, ps[it + 1].second - ps[it].second).toDouble() }
                    for (k in 0 until 3) {
                        var pos = (m.t * 40 * z + k * lg / 3) % max(1.0, lg)
                        for (i in 0 until ps.size - 1) {
                            val s = hypot(ps[i + 1].first - ps[i].first, ps[i + 1].second - ps[i].second).toDouble()
                            if (pos <= s) {
                                val f = (pos / max(1.0, s)).toFloat()
                                tl.rect(ps[i].first + (ps[i + 1].first - ps[i].first) * f - 1.5f * z, ps[i].second + (ps[i + 1].second - ps[i].second) * f - 1.5f * z, 3 * z, 3 * z, rgb(200, 255, 220))
                                break
                            }
                            pos -= s
                        }
                    }
                }
                "ouvert" -> for (i in 0 until ps.size - 1) tl.ligne(ps[i].first, ps[i].second, ps[i + 1].first, ps[i + 1].second, rgb(255, 213, 79, 170), 1.8f * z, 5 * z, 5 * z, 0f)
                else -> for (p in (if (ps.size > 2) ps.subList(1, ps.size - 1) else ps)) tl.rect(p.first - 1.2f * z, p.second - 1.2f * z, 2.4f * z, 2.4f * z, rgb(150, 156, 170, 120))
            }
        }
    }

    // ---------------------------------------------------------------- l'événement rare (idée 38)
    private fun evenement(tl: Toile, m: Modele, R: Repere, z: Float) {
        val e = m.evt ?: return
        val (W, H) = Reveil.taille()
        val (cx, cy) = R.p(e.optDouble("x").toFloat() / W, e.optDouble("y").toFloat() / H)
        val ca = e.optJSONArray("couleur")
        val c0 = if (ca != null) rgb(ca.getInt(0), ca.getInt(1), ca.getInt(2)) else VERT
        val t = m.t
        val k = e.optString("effet")
        when (k) {
            "aurore" -> for ((j, cc) in listOf(VERT to 0f, CYAN to 10f, EspaceDessin.VIOLET to 22f).withIndex()) for (i in 0 until 46) {
                val ax = cx - 120 * R.r + i * 5.2f * R.r
                val ay = cy - 40 * R.r + cc.second * R.r + 12 * R.r * sin(i / 5.0 + j + t * 0.8).toFloat()
                val hh = (50 + 20 * sin(i / 3.0 + j + t)).toFloat() * R.r
                tl.rect(ax, ay, 4 * R.r, hh, a(cc.first, (70 * sin(PI * i / 46)).toInt()))
            }
            "trainee" -> {
                val (x2, y2) = R.p(e.optDouble("x2").toFloat() / W, e.optDouble("y2").toFloat() / H)
                val f = ((t * 0.35) % 1.0).toFloat()
                val hx = cx + (x2 - cx) * f; val hy = cy + (y2 - cy) * f
                for (i in 0 until 18) {
                    val g = i / 18f
                    val q = (6 - 5 * g) * R.r
                    tl.rect(hx - (x2 - cx) * 0.25f * g - q / 2, hy - (y2 - cy) * 0.25f * g - q / 2, q, q, a(c0, (255 * (1 - g)).toInt()))
                }
                tl.lueur(hx, hy, 26 * R.r, a(c0, 160))
            }
            "baleine" -> {
                val bx = cx + 40 * R.r * sin(t * 0.4).toFloat(); val byy = cy + 5 * R.r * sin(t * 1.3).toFloat()
                val motif = listOf("..XXXXX....", ".XXXXXXXX.X", "XXOXXXXXXXX", "XXXXXXXXX.X", ".XXXXXXX...")
                val q = 4 * R.r
                for ((j, l) in motif.withIndex()) for ((i, ch) in l.withIndex()) if (ch != '.')
                    tl.rect(bx + (i - 5) * q, byy + (j - 2) * q, q, q, if (ch == 'O') rgb(20, 30, 60) else rgb(95, 175, 255, 235))
            }
            "ballon" -> {
                val bx = cx + 30 * R.r * sin(t * 0.3).toFloat(); val byy = cy - 10 * R.r * sin(t * 0.5).toFloat()
                tl.ellipse(bx, byy, 16 * R.r, 19 * R.r, a(c0, 240))
                tl.ellipse(bx - 5 * R.r, byy - 6 * R.r, 4 * R.r, 5 * R.r, rgb(255, 245, 200, 200))
                tl.rect(bx - 5 * R.r, byy + 24 * R.r, 10 * R.r, 7 * R.r, rgb(160, 110, 60))
            }
            else -> {
                for (i in 0 until 30) {
                    val (dx, dy) = when (k) {
                        "monte" -> ((h(i, 40) - 0.5f) * 90) to -((h(i, 41) * 80 + t * 30) % 80).toFloat()
                        "descend" -> ((h(i, 40) - 0.5f) * 140 + 8 * sin(t + i).toFloat()) to ((h(i, 41) * 90 + t * 18) % 90 - 30).toFloat()
                        "scintille" -> ((h(i, 40) - 0.5f) * 120) to ((h(i, 41) - 0.5f) * 70)
                        else -> ((h(i, 40) - 0.5f) * 120 + 10 * sin(t * 0.8 + i).toFloat()) to ((h(i, 41) - 0.5f) * 70 + 8 * cos(t * 0.6 + i * 1.7).toFloat())
                    }
                    val al = (120 + 135 * (0.5 + 0.5 * sin(t * 3 + i))).toInt()
                    val q = 3 * R.r
                    tl.rect(cx + dx * R.r, cy + dy * R.r, q, q, a(c0, al))
                }
                tl.lueur(cx, cy, 50 * R.r, a(c0, 40))
            }
        }
    }

    // ---------------------------------------------------------------- les lieux secrets trouvés (idée 33)
    private fun secrets(tl: Toile, m: Modele, R: Repere, z: Float) {
        val (W, H) = Reveil.taille()
        for ((_, sx, sy) in m.secrets.first) {
            val (px, py) = R.p(sx / W, sy / H)
            for (i in 0 until 5) {
                val an = m.t * 1.5 + i * 1.256
                tl.rect(px + 8 * z * cos(an).toFloat() - 1.2f * z, py + 8 * z * sin(an).toFloat() - 1.2f * z, 2.4f * z, 2.4f * z, rgb(61, 220, 132, 200))
            }
            tl.texte("★", px, py, 12 * z, JAUNE, true, 'c')
        }
    }

    // ---------------------------------------------------------------- les lieux (idée 32)
    private fun lieux(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, R: Repere, z: Float) {
        for (l in m.lieux) {
            val (px, py) = R.p(l.x, l.y)
            if (!R.dedans(px, py, 4 * z)) continue
            val c = coul(l.etat)
            if (l.id == m.iciLieu) {
                val pul = (0.5 + 0.5 * sin(m.t * 3)).toFloat()
                tl.lueur(px, py, (30 + 8 * pul) * z, 0x46FFD54F)
                tl.cercle(px, py, (16 + 3 * pul) * z, JAUNE, 1.6f * z)
            }
            if (l.etat == "ouvert") tl.lueur(px, py, 16 * z, a(JAUNE, (50 + 30 * sin(m.t * 2.2)).toInt()))
            tl.ellipse(px, py, 6 * z, 6 * z, 0xE60A0C12.toInt())
            tl.ellipse(px, py, 4.2f * z, 4.2f * z, c)
            val nom = if (l.etat != "ferme") l.nom else "?"
            val txt = (if (l.etat == "allume" && l.id != "camp" && l.id != "carrefour") "✓ " else "") + nom + if (l.etoile) " ★" else ""
            val tw = tl.mesure(txt, 11 * z) + 14 * z
            val ty = py - 16 * z
            tl.rrect(px - tw / 2, ty - 10 * z, tw, 20 * z, 10 * z, 0xD20A0C12.toInt(), if (l.id == m.fiche) a(c, 200) else EspaceDessin.BORD_FORT, 1f * z)
            tl.texte(txt, px, ty, 11 * z, if (l.etat == "allume") VERT else if (l.etat == "ouvert") TEXTE else DOUX, false, 'c')
            Z.add(EspaceDessin.Zone(px - max(tw / 2, 18 * z), ty - 12 * z, max(tw, 36 * z), 36 * z, "rv:lieu:" + l.id))
        }
        m.iciPiece?.let { (fx, fy) ->
            val (px, py) = R.p(fx, fy)
            val pul = (0.5 + 0.5 * sin(m.t * 3)).toFloat()
            tl.lueur(px, py, (34 + 8 * pul) * z, 0x46FFD54F)
            tl.cercle(px, py, (18 + 3 * pul) * z, JAUNE, 1.6f * z)
            tl.ellipse(px, py, 5 * z, 5 * z, JAUNE)
            val info = t("esp.tu_es_ici", "lieu" to m.iciNom)
            val bw = tl.mesure(info, 12 * z, true) + 26 * z
            val bx = (px - bw / 2).coerceIn(R.x + 6 * z, R.x + R.w - bw - 6 * z)
            val byy = min(py + 24 * z, R.y + R.h - 28 * z)
            tl.rrect(bx, byy, bw, 22 * z, 9 * z, 0xE60A0C12.toInt(), a(JAUNE, 120), 1f * z)
            tl.texte(info, bx + 13 * z, byy + 11 * z, 12 * z, TEXTE, true)
        }
        m.enCours?.let { (nom, pos) ->
            val (px, py) = R.p(pos.first, pos.second)
            val txt = "▶ $nom"
            val tw = tl.mesure(txt, 11 * z) + 16 * z
            tl.rrect(px - tw / 2, py - 11 * z, tw, 22 * z, 11 * z, 0xD70A0C12.toInt(), a(VERT, 120), 1f * z)
            tl.texte(txt, px, py, 11 * z, VERT, false, 'c')
        }
    }

    // ---------------------------------------------------------------- les habitants (idée 35)
    private fun habitants(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, R: Repere, z: Float) {
        val (W, H) = Reveil.taille()
        for (hv in m.habitants) {
            val hb = hv.h
            val (px, py) = R.p(hb.x / W, hb.y / H)
            if (!R.dedans(px, py, 10 * z)) continue
            val rr = 14 * z
            tl.ellipse(px, py, rr, rr, 0xEB0C0F18.toInt())
            tl.cercle(px, py, rr, if (hb.besoin) JAUNE else a(VERT, 160), 1.6f * z)
            hv.album?.let { al -> val cad = al.image("assis", 0); tl.cadre(cad, px, py + rr - 3 * z, 22 * z / max(1, al.ref), false, al.lisse) }
            if (hb.besoin) {
                val b = (3 * sin(m.t * 4)).toFloat() * z
                tl.ellipse(px + rr - 2 * z, py - rr + 1 * z + b, 6.5f * z, 6.5f * z, JAUNE)
                tl.texte("!", px + rr - 2 * z, py - rr + 1 * z + b, 10 * z, 0xFF141000.toInt(), true, 'c')
            }
            Z.add(EspaceDessin.Zone(px - rr, py - rr, 2 * rr, 2 * rr, "rv:hab:" + hb.id))
        }
    }

    // ---------------------------------------------------------------- les animations (idées 31 et 39)
    private fun animation(tl: Toile, m: Modele, an: Anim, R: Repere, z: Float) {
        val p = m.p
        when (an.type) {
            "biome", "resume" -> {
                val (cx, cy) = R.p(an.c.first, an.c.second)
                val rmax = hypot(max(cx - R.x, R.x + R.w - cx), max(cy - R.y, R.y + R.h - cy))
                val rr = rmax * min(1f, p * 1.15f)
                for (i in 0 until 40) {
                    val a0 = i * 0.157 + m.t
                    val sx = cx + rr * cos(a0).toFloat(); val sy = cy + rr * sin(a0).toFloat()
                    if (R.dedans(sx, sy)) tl.rect(sx - 1.5f * z, sy - 1.5f * z, 3 * z, 3 * z, rgb(120, 255, 170, (220 * (1 - p)).toInt()))
                }
            }
            "lieu" -> { val (cx, cy) = R.p(an.c.first, an.c.second); tl.lueur(cx, cy, 70 * R.r * (0.6f + p), rgb(255, 230, 150, (200 * (1 - p)).toInt())) }
            "chemin" -> {
                val ps = an.pts.map { R.p(it.first, it.second) }
                val lg = (0 until ps.size - 1).sumOf { hypot(ps[it + 1].first - ps[it].first, ps[it + 1].second - ps[it].second).toDouble() }
                var reste = lg * min(1f, p * 1.1f)
                for (i in 0 until ps.size - 1) {
                    val s = hypot(ps[i + 1].first - ps[i].first, ps[i + 1].second - ps[i].second).toDouble()
                    val f = min(1.0, reste / max(1.0, s))
                    val n = (s * f / (5 * z)).toInt()
                    for (k in 0 until n) {
                        val g = (k * 5 * z / max(1.0, s)).toFloat()
                        tl.rect(ps[i].first + (ps[i + 1].first - ps[i].first) * g - 1.5f * z, ps[i].second + (ps[i + 1].second - ps[i].second) * g - 1.5f * z, 3 * z, 3 * z, rgb(61, 220, 132, 230))
                    }
                    reste -= s
                    if (reste <= 0) break
                }
            }
        }
        if (an.texte.isNotEmpty()) {
            val tw = min(R.w - 20 * z, tl.mesure(an.texte, 13 * z, true) + 30 * z)
            val bx = R.x + (R.w - tw) / 2; val byy = R.y + R.h - 52 * z
            tl.rrect(bx, byy, tw, 42 * z, 12 * z, 0xE10A0C12.toInt(), a(VERT, 150), 1.4f * z)
            tl.texte(court(tl, an.texte, tw - 20 * z, 13 * z, true), R.x + R.w / 2, byy + 15 * z, 13 * z, TEXTE, true, 'c')
            tl.texte(t("reveil.anim.passer"), R.x + R.w / 2, byy + 31 * z, 10.5f * z, DOUX, false, 'c')
        }
    }

    // ---------------------------------------------------------------- les fiches
    private fun court(tl: Toile, s: String, l: Float, taille: Float, gras: Boolean = false, mono: Boolean = false): String {
        if (tl.mesure(s, taille, gras, mono) <= l) return s
        var x = s
        while (x.isNotEmpty() && tl.mesure("$x…", taille, gras, mono) > l) x = x.dropLast(1)
        return "$x…"
    }

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

    private fun sans(s: String) = s.replace("`", "")

    private fun etatTxt(l: Reveil.Lieu): String {
        var e = t("reveil.etat." + l.etat)
        if (l.paliers > 0 && l.etat != "ferme") e += " · " + t("reveil.palier", "i" to l.palier, "n" to l.paliers)
        return e
    }

    private fun cadrePanneau(tl: Toile, Z: MutableList<EspaceDessin.Zone>, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, 0xFF0F1219.toInt(), a(CYAN, 120), 1.2f * z)
        Z.add(EspaceDessin.Zone(x, y, w, h, "rv:rien"))
        tl.texte("✕", x + w - 18 * z, y + 18 * z, 15 * z, DOUX, true, 'c')
        Z.add(EspaceDessin.Zone(x + w - 40 * z, y, 40 * z, 40 * z, "rv:fermer"))
    }

    private fun bouton(tl: Toile, Z: MutableList<EspaceDessin.Zone>, x: Float, y: Float, w: Float, h: Float, txt: String, vert: Boolean, action: String, z: Float) {
        tl.rrect(x, y, w, h, 10 * z, if (vert) a(VERT, 50) else 0xFF0E1016.toInt(), if (vert) VERT else EspaceDessin.BORD_FORT, 1.4f * z)
        tl.texte(court(tl, txt, w - 12 * z, 14 * z, true), x + w / 2, y + h / 2, 14 * z, if (vert) VERT else TEXTE, true, 'c')
        Z.add(EspaceDessin.Zone(x, y, w, h, action))
    }

    private fun fiche(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val l = m.lieux.firstOrNull { it.id == m.fiche } ?: return
        cadrePanneau(tl, Z, x, y, w, h, z)
        val c = coul(l.etat)
        tl.texte(court(tl, if (l.etat != "ferme") l.titre else "?", w - 60 * z, 16 * z, true), x + 14 * z, y + 20 * z, 16 * z, TEXTE, true)
        val et = etatTxt(l)
        val ew = tl.mesure(et, 11.5f * z) + 26 * z
        tl.rrect(x + 14 * z, y + 36 * z, ew, 22 * z, 11 * z, a(c, 30), a(c, 120), 1f * z)
        tl.ellipse(x + 26 * z, y + 47 * z, 3.5f * z, 3.5f * z, c)
        tl.texte(et, x + 34 * z, y + 47 * z, 11.5f * z, c)
        tl.texte(t("reveil.fiche.biome", "biome" to t("reveil.biome." + l.biome)), x + ew + 24 * z, y + 47 * z, 11.5f * z, DOUX)
        var yy = y + 74 * z
        val txt = if (l.etat != "ferme") sans(l.debut) else t("reveil.fiche.ferme", "manque" to l.manque.ifEmpty { "…" })
        val max = if (m.plus) 9 else 3
        for (ln in couper(tl, txt, w - 28 * z, 12.5f * z).take(max)) {
            if (yy > y + h - 64 * z) break
            tl.texte(ln, x + 14 * z, yy, 12.5f * z, TEXTE); yy += 17 * z
        }
        val bits = mutableListOf<String>()
        if (l.habitants > 0) bits.add(t("reveil.fiche.habitants", "n" to l.habitants))
        if (l.secrets.second > 0) bits.add(t("reveil.fiche.secrets", "n" to l.secrets.first, "total" to l.secrets.second))
        if (bits.isNotEmpty()) tl.texte(court(tl, bits.joinToString("  ·  "), w - 28 * z, 11.5f * z), x + 14 * z, y + h - 56 * z, 11.5f * z, JAUNE)
        val bw = (w - 38 * z) / 2
        if (l.cmd != null) bouton(tl, Z, x + 14 * z, y + h - 44 * z, bw, 34 * z, t("reveil.aller"), true, "rv:aller:" + l.id, z)
        if (l.id == "temps" && m.plus) bouton(tl, Z, x + 24 * z + bw, y + h - 44 * z, bw, 34 * z, t("reveil.livre.bouton"), false, "rv:livre", z)
        else bouton(tl, Z, x + 24 * z + bw, y + h - 44 * z, bw, 34 * z, t("reveil.savoir"), false, "rv:plus", z)
    }

    private fun ficheHabitant(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val hv = m.habitants.firstOrNull { "hab:" + it.h.id == m.fiche } ?: return
        cadrePanneau(tl, Z, x, y, w, h, z)
        tl.ellipse(x + 40 * z, y + 40 * z, 26 * z, 26 * z, 0xFF141824.toInt())
        hv.album?.let { al -> tl.cadre(al.image("assis", 0), x + 40 * z, y + 62 * z, 40 * z / max(1, al.ref), false, al.lisse) }
        tl.texte(court(tl, hv.nom, w - 120 * z, 15 * z, true), x + 76 * z, y + 24 * z, 15 * z, TEXTE, true)
        val ch = if (hv.h.besoin) t("reveil.hab.besoin") else t("reveil.hab.merci", "nom" to hv.nom)
        val c = if (hv.h.besoin) JAUNE else VERT
        val cw = tl.mesure(ch, 11.5f * z) + 18 * z
        tl.rrect(x + 76 * z, y + 40 * z, cw, 22 * z, 11 * z, a(c, 30), a(c, 120), 1f * z)
        tl.texte(ch, x + 85 * z, y + 51 * z, 11.5f * z, c)
        var yy = y + 84 * z
        for (ln in couper(tl, sans(hv.texte), w - 28 * z, 12.5f * z).take(5)) {
            if (yy > y + h - 40 * z) break
            tl.texte(ln, x + 14 * z, yy, 12.5f * z, TEXTE); yy += 17 * z
        }
        if (hv.h.besoin) {
            tl.texte(court(tl, sans(if (hv.h.active) t("reveil.hab.en_cours") else t("reveil.hab.lire", "fichier" to hv.h.fichier)), w - 28 * z, 12 * z),
                x + 14 * z, y + h - 34 * z, 12 * z, CYAN)
            tl.texte(court(tl, t("reveil.hab.recompense", "xp" to hv.h.xp) + " · " + t("reveil.hab.attend"), w - 28 * z, 10.5f * z),
                x + 14 * z, y + h - 16 * z, 10.5f * z, DOUX)
        }
    }

    private fun livre(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        cadrePanneau(tl, Z, x, y, w, h, z)
        tl.texte(court(tl, "📖 " + t("reveil.livre.titre") + " · " + t("reveil.livre.compte", "n" to m.livreOuverts.size, "total" to m.gardiens.size), w - 50 * z, 13 * z, true),
            x + 14 * z, y + 20 * z, 13 * z, TEXTE, true)
        val n = m.livrePage
        if (n != null && n in m.livreOuverts) {
            tl.texte(court(tl, t("reveil.livre.chapitre", "n" to n, "total" to m.gardiens.size) + " · " + t("reveil.gardien.$n.titre"), w - 28 * z, 13 * z, true),
                x + 14 * z, y + 46 * z, 13 * z, JAUNE, true)
            var yy = y + 70 * z
            for (ln in couper(tl, t("reveil.gardien.$n.texte"), w - 28 * z, 12.5f * z)) {
                if (yy > y + h - 40 * z) break
                tl.texte(ln, x + 14 * z, yy, 12.5f * z, TEXTE); yy += 17 * z
            }
            if (m.livreFichier) tl.texte(court(tl, sans(t("reveil.livre.lire", "chemin" to "~/terrain_terminagotchi/" + Reveil.fichierGardien(n))), w - 70 * z, 10.5f * z, mono = true),
                x + 14 * z, y + h - 16 * z, 10.5f * z, CYAN, false, 'g', true)
            bouton(tl, Z, x + w - 54 * z, y + h - 40 * z, 44 * z, 32 * z, "◀", false, "rv:livre:0", z)
            return
        }
        val cw = (w - 28 * z) / 4
        for ((i, g) in m.gardiens.withIndex()) {
            val k = i + 1
            val cx = x + 14 * z + (i % 4) * cw; val cy = y + 40 * z + (i / 4) * 82 * z
            val ouvert = k in m.livreOuverts
            tl.rrect(cx, cy, cw - 8 * z, 74 * z, 10 * z, 0xFF12151E.toInt(), if (ouvert) a(JAUNE, 120) else EspaceDessin.BORD, 1f * z)
            val al = m.gardAlbums[g.second]
            if (ouvert && al != null) tl.cadre(al.image("assis", 0), cx + (cw - 8 * z) / 2, cy + 52 * z, 40 * z / max(1, al.ref), false, al.lisse)
            else { tl.ellipse(cx + (cw - 8 * z) / 2, cy + 34 * z, 15 * z, 18 * z, 0xFF282C38.toInt()); tl.texte("?", cx + (cw - 8 * z) / 2, cy + 34 * z, 14 * z, PALE, true, 'c') }
            tl.texte(t("reveil.livre.ch", "n" to k), cx + (cw - 8 * z) / 2, cy + 66 * z, 10.5f * z, if (ouvert) TEXTE else PALE, true, 'c')
            if (ouvert) Z.add(EspaceDessin.Zone(cx, cy, cw - 8 * z, 74 * z, "rv:livre:$k"))
        }
        var yy = y + 40 * z + 2 * 82 * z + 6 * z
        for (ln in couper(tl, t("reveil.livre.silhouette"), w - 28 * z, 11 * z).take(2)) { tl.texte(ln, x + 14 * z, yy, 11 * z, DOUX); yy += 15 * z }
    }

    private fun carnet(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        cadrePanneau(tl, Z, x, y, w, h, z)
        val evs = Reveil.evenements()
        tl.texte(court(tl, t("reveil.evt.carnet", "n" to m.carnetVus.size, "total" to evs.size), w - 50 * z, 13 * z, true), x + 14 * z, y + 20 * z, 13 * z, TEXTE, true)
        val cw = (w - 28 * z) / 3
        for ((i, e) in evs.withIndex()) {
            val cx = x + 14 * z + (i % 3) * cw; val cy = y + 38 * z + (i / 3) * 46 * z
            if (cy + 40 * z > y + h - 22 * z) break
            val vu = e.optString("id") in m.carnetVus
            tl.rrect(cx, cy, cw - 6 * z, 40 * z, 9 * z, 0xFF12151E.toInt(), if (vu) a(VERT, 120) else EspaceDessin.BORD, 1f * z)
            tl.texte(court(tl, if (vu) "★ " + t("reveil.evt." + e.optString("id")) else "?", cw - 20 * z, 11 * z, true), cx + 8 * z, cy + 13 * z, 11 * z, if (vu) TEXTE else PALE, true)
            tl.texte(court(tl, t("reveil.fiche.biome", "biome" to t("reveil.biome." + e.optString("biome"))), cw - 20 * z, 10 * z), cx + 8 * z, cy + 29 * z, 10 * z, DOUX)
        }
        tl.texte(court(tl, t("reveil.evt.jamais_rate"), w - 28 * z, 10.5f * z), x + 14 * z, y + h - 12 * z, 10.5f * z, DOUX)
    }

    private fun legende(tl: Toile, Z: MutableList<EspaceDessin.Zone>, m: Modele, x: Float, y: Float, w: Float, z: Float) {
        var xx = x + 14 * z
        for (et in listOf("allume", "ouvert", "ferme")) {
            tl.ellipse(xx + 4 * z, y, 4 * z, 4 * z, coul(et))
            tl.texte(t("reveil.etat.$et"), xx + 11 * z, y, 11 * z, DOUX)
            xx += tl.mesure(t("reveil.etat.$et"), 11 * z) + 22 * z
        }
        val (_, nt) = m.secrets
        for ((txt, act) in listOf("★ " + t("reveil.secrets.court", "n" to nt.first, "total" to nt.second) to null,
                "📖 " + t("reveil.livre.court", "n" to m.livreOuverts.size, "total" to m.gardiens.size) to "rv:livre",
                "✦ " + t("reveil.evt.court", "n" to m.carnetVus.size, "total" to Reveil.evenements().size) to "rv:carnet")) {
            val tw = tl.mesure(txt, 11 * z)
            if (xx + tw > x + w - 8 * z) break
            tl.texte(txt, xx, y, 11 * z, if (act == null) JAUNE else CYAN)
            if (act != null) Z.add(EspaceDessin.Zone(xx - 4 * z, y - 14 * z, tw + 8 * z, 28 * z, act))
            xx += tw + 14 * z
        }
    }
}
