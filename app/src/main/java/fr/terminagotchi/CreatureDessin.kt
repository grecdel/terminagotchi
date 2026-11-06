package fr.terminagotchi

import org.json.JSONObject
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * Les dessins du thème « créature » sur le téléphone (maquettes validées le 3 novembre), sur une Toile (le Canvas du
 * téléphone, ou Java2D dans les tests) : le petit signe de l'humeur, les confettis et le gâteau de l'éclosiversaire,
 * le sol de la promenade (EspaceDessin, la carte de la créature), l'album des stades et le moment d'évolution en plein
 * écran (CreatureVue). Même dessin que le PC (pc/tg/espace_scene.py : pixels, glyphe, confettis, sol, evolution, album).
 */
object CreatureDessin {
    private fun d() = Creature.donnees()
    private fun hexa(s: String, alpha: Int = 255): Int = (alpha.coerceIn(0, 255) shl 24) or Integer.parseInt(s.substring(1), 16)
    private fun rangs(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()

    /** Un petit dessin en pixels (creature.json : glyphes, gâteau, décors), coin haut gauche en (x, y). */
    fun pixels(tl: Toile, r: List<String>, x: Float, y: Float, ech: Float, alpha: Int = 255) {
        val pal = d().optJSONObject("couleurs_glyphes") ?: return
        for ((j, ligne) in r.withIndex()) for ((i, ch) in ligne.withIndex()) {
            if (ch == '.' || !pal.has(ch.toString())) continue
            tl.rect(x + i * ech, y + j * ech, ech, ech, hexa(pal.getString(ch.toString()), alpha))
        }
    }

    fun glyphe(tl: Toile, nom: String?, cx: Float, haut: Float, ech: Float, t: Double) {
        if (nom == null) return
        val g = d().optJSONObject("glyphes") ?: return
        val flotte = (5 * sin(t * 2.4)).toFloat() * ech / 4
        if (nom == "etoiles" || nom == "coeurs") {
            val un = rangs(g, if (nom == "etoiles") "etoile" else "coeur")
            for ((k, p) in listOf(-1.1f to 0.25f, 1.0f to 0.05f, 0.55f to -0.35f).withIndex()) {
                val a = (255 * (0.55 + 0.45 * sin(t * 3 + k * 2))).toInt()
                pixels(tl, un, cx + p.first * 9 * ech - 2.5f * ech, haut + p.second * 12 * ech + flotte, ech, a)
            }
            return
        }
        if (!g.has(nom)) return
        val r = rangs(g, nom)
        pixels(tl, r, cx + 3 * ech, haut - r.size * ech + flotte, ech)
    }

    fun confettis(tl: Toile, x: Float, y: Float, w: Float, h: Float, t: Double, z: Float) {
        val cs = d().optJSONArray("confettis") ?: return
        for (k in 0 until 34) {
            val vx = ((k * 7919) % 997) / 997.0
            val v = 0.25 + ((k * 104729) % 89) / 89.0 * 0.5
            val yy = ((t * v * 0.35 + ((k * 31) % 53) / 53.0) % 1.0) * (h - 16 * z)
            val xx = x + 8 * z + vx * (w - 16 * z) + 5 * z * sin(t * 2 + k)
            tl.rect(xx.toFloat(), (y + 6 * z + yy).toFloat(), 4 * z, 4 * z, hexa(cs.getString(k % cs.length()), 230))
        }
    }

    fun gateau(tl: Toile, x: Float, pieds: Float, ech: Float) {
        val r = rangs(d().optJSONObject("glyphes"), "gateau")
        pixels(tl, r, x, pieds + ech / 2 - r.size * ech, ech)
    }

    /** 85 : le sol de son biome et quelques décors, sous ses pieds. */
    fun sol(tl: Toile, x: Float, w: Float, pieds: Float, type: String?, z: Float) {
        val sols = d().optJSONObject("sols") ?: return
        val s = sols.optJSONObject(type ?: "plante") ?: sols.optJSONObject("plante") ?: return
        tl.rect(x + 6 * z, pieds + 1 * z, w - 12 * z, 9 * z, hexa(s.getString("sol"), 150))
        tl.rect(x + 6 * z, pieds + 1 * z, w - 12 * z, 2 * z, hexa(s.getString("bord"), 200))
        val deco = rangs(s, "deco")
        val decors = d().optJSONObject("decors")
        for ((k, fx) in listOf(0.12f, 0.58f, 0.88f).withIndex()) {
            val r = rangs(decors, deco.getOrNull(k) ?: continue)
            pixels(tl, r, x + fx * w, pieds + 2 * z - r.size * 3 * z, 3 * z, 235)
        }
    }

    // ------------------------------------------------------------ 16. l'album (le téléphone : une grande carte, les autres en petit)
    class Page(val id: String, val nom: String, val date: String, val niv: String, val souv: String, val cadre: Poses.Cadre?,
               val atteint: Boolean, val actuel: Boolean)
    class AlbumModele(val titre: String, val eclos: String, val pages: List<Page>, val fetes: List<String>, var choisi: String?,
                      var salut: Double = -9.0)

    private val cadres = HashMap<String, Poses.Cadre?>()

    /** L'image d'un stade (ou sa silhouette grise), à partir des dessins du bestiaire. */
    fun cadreStade(e: Bestiaire.Espece, stade: String, atteint: Boolean, shiny: Boolean): Poses.Cadre? =
        cadres.getOrPut("${e.id}/$stade/$atteint/$shiny") {
            val img = Bestiaire.image(e, stade) ?: return@getOrPut null
            val pal = IntArray(img.palette.size) { (if (shiny) Bestiaire.decaler(img.palette[it], 0.5) else img.palette[it]) or 0xFF000000.toInt() }
            val px = IntArray(img.w * img.h) { p ->
                val o = img.octets[p].toInt() and 255
                if (o == 0 || o > pal.size) 0 else if (atteint) pal[o - 1] else 0xFF3A3E4A.toInt()
            }
            Poses.Cadre(img.w, img.h, px, img.w / 2, img.h, "album/${e.id}/$stade/$atteint/$shiny")
        }

    fun modeleAlbum(jeu: Jeu): AlbumModele {
        val c = Creature.c(jeu)
        val e = Creature.espece(jeu)
        val stades = Creature.stadesCompagnon()
        val actuel = Creature.stadeCompagnon(jeu)
        val ia = if (actuel == null) -1 else stades.indexOf(actuel)
        val pages = stades.mapIndexed { k, s ->
            val atteint = k <= ia
            val p = c.getJSONObject("album").optJSONObject(s) ?: JSONObject().put("avant", true)
            Page(s, Equipe.nomStade(s).replaceFirstChar { it.uppercase() },
                if (atteint) Creature.dateOu(p) else t("cr.album.bientot"),
                if (atteint && p.has("niv")) t("cr.album.niveau", "n" to p.optInt("niv")) else "",
                if (atteint) Creature.souvenir(p) else "",
                e?.let { cadreStade(it, s, atteint, jeu.shiny) }, atteint, s == actuel)
        }
        val pg = c.getJSONArray("pages")
        val fetes = (maxOf(0, pg.length() - 4) until pg.length()).map { "★ " + Creature.duree(pg.getJSONObject(it).optInt("m")) }
        return AlbumModele(t("cr.album.titre", "nom" to jeu.nom),
            if (c.optDouble("eclosion", 0.0) > 0) t("cr.album.eclos", "date" to Creature.dateTexte(c.getDouble("eclosion"))) else "",
            pages, fetes, actuel)
    }

    private fun court(tl: Toile, s: String, l: Float, taille: Float, gras: Boolean = false): String {
        if (tl.mesure(s, taille, gras) <= l) return s
        var x = s
        while (x.length > 1 && tl.mesure("$x…", taille, gras) > l) x = x.dropLast(1)
        return "$x…"
    }

    private fun poser(tl: Toile, c: Poses.Cadre?, cx: Float, pieds: Float, hauteur: Float, dy: Float = 0f) {
        c ?: return
        val e = max(1f, (hauteur / max(1, c.h)).toInt().toFloat())
        tl.cadre(c, cx, pieds + dy, e, false, false)
    }

    /** L'album en plein écran ; renvoie les zones (album:<stade>, album:salut, album:fermer). */
    fun album(tl: Toile, a: AlbumModele, w: Float, h: Float, z: Float, t: Double): List<EspaceDessin.Zone> {
        val Z = mutableListOf<EspaceDessin.Zone>()
        val E = EspaceDessin
        tl.rect(0f, 0f, w, h, 0xE6050609.toInt())
        val x = 14 * z; val lw = w - 28 * z
        val ch = min(h - 120 * z, 430 * z)
        val y = max(40 * z, (h - ch - 60 * z) / 2)
        tl.rrect(x, y, lw, ch + 60 * z, 18 * z, E.PANNEAU, E.BORD_FORT, 1f * z)
        Z.add(EspaceDessin.Zone(x, y, lw, ch + 60 * z, "album:cadre"))
        tl.texte(court(tl, a.titre.uppercase(), lw * 0.6f, 12 * z, true), x + 16 * z, y + 24 * z, 12 * z, E.DOUX, true)
        val n = a.pages.size
        val ia = a.pages.count { it.atteint }
        tl.texte(t("cr.album.compte", "k" to ia, "n" to n), x + lw - 52 * z, y + 24 * z, 12 * z, E.PALE, false, 'd')
        tl.texte("✕", x + lw - 18 * z, y + 24 * z, 17 * z, E.TEXTE, true, 'c')
        Z.add(EspaceDessin.Zone(x + lw - 44 * z, y, 44 * z, 46 * z, "album:fermer"))
        // la grande carte (le stade choisi), les autres en petit à droite
        val choisi = a.pages.firstOrNull { it.id == a.choisi } ?: a.pages.lastOrNull { it.atteint } ?: a.pages.first()
        val gx = x + 12 * z; val gy = y + 44 * z; val gw = lw * 0.6f; val gh = ch
        tl.rrect(gx, gy, gw, gh, 14 * z, 0xFF0D1016.toInt(), if (choisi.actuel) E.a(E.VERT, 170) else E.BORD, 1.5f * z)
        val pieds = gy + gh - 86 * z
        if (choisi.atteint) tl.lueur(gx + gw / 2, pieds - gh * 0.25f, gw * 0.5f, E.a(E.VERT, 30))
        val dy = if (t - a.salut < 1.6) (-abs(sin((t - a.salut) * 9)) * 16 * z).toFloat() else 0f
        poser(tl, choisi.cadre, gx + gw / 2, pieds, gh * 0.55f, dy)
        tl.texte(choisi.nom, gx + gw / 2, pieds + 26 * z, 19 * z, if (choisi.atteint) E.TEXTE else E.PALE, true, 'c')
        tl.texte(court(tl, choisi.date + (if (choisi.niv.isNotEmpty()) " · ${choisi.niv}" else ""), gw - 16 * z, 13 * z),
            gx + gw / 2, pieds + 50 * z, 13 * z, E.DOUX, false, 'c')
        if (choisi.souv.isNotEmpty()) tl.texte(court(tl, choisi.souv.replace("`", ""), gw - 16 * z, 13 * z), gx + gw / 2,
            pieds + 70 * z, 13 * z, E.ORANGE, false, 'c')
        Z.add(EspaceDessin.Zone(gx, gy, gw, gh, "album:salut"))
        val px = gx + gw + 10 * z; val pw = x + lw - 12 * z - px
        val autres = a.pages.filter { it !== choisi }
        val ph = min(84 * z, (gh - 8 * z * (autres.size - 1)) / max(1, autres.size))
        for ((i, p) in autres.withIndex()) {
            val py = gy + i * (ph + 8 * z)
            tl.rrect(px, py, pw, ph, 12 * z, 0xFF0D1016.toInt(), if (p.actuel) E.a(E.VERT, 150) else E.BORD, 1f * z)
            poser(tl, p.cadre, px + 26 * z, py + ph - 12 * z, ph * 0.62f)
            tl.texte(court(tl, p.nom, pw - 58 * z, 14 * z, true), px + 52 * z, py + ph / 2 - 9 * z, 14 * z,
                if (p.atteint) E.TEXTE else E.PALE, true)
            tl.texte(court(tl, p.date, pw - 58 * z, 11.5f * z), px + 52 * z, py + ph / 2 + 11 * z, 11.5f * z, E.DOUX)
            Z.add(EspaceDessin.Zone(px, py, pw, ph, "album:${p.id}"))
        }
        val by = y + ch + 50 * z
        val pied = if (a.fetes.isNotEmpty()) t("cr.album.fetes") + " " + a.fetes.joinToString("  ") else a.eclos
        tl.texte(court(tl, pied, lw - 24 * z, 12.5f * z), x + 16 * z, by, 12.5f * z, if (a.fetes.isNotEmpty()) E.ROSE else E.PALE)
        tl.texte(court(tl, t("cr.album.toucher"), lw - 24 * z, 11.5f * z), x + lw / 2, y + ch + 76 * z, 11.5f * z, E.PALE, false, 'c')
        return Z
    }

    // ------------------------------------------------------------ 84. le moment d'évolution (plein écran)
    class Evo(val nom: String, val forme: String, val avant: Poses.Album?, val cadres: List<Poses.Cadre>?, val apres: Poses.Album?,
              val ref: Int, val t0: Double)

    fun modeleEvo(jeu: Jeu, de: String?, t0: Double): Evo {
        val e = Creature.espece(jeu)
        val avant = try { e?.let { Poses.albumEspece(it, de ?: "bebe", jeu.shiny) } } catch (x: Exception) { null }
        val cadres = try { Poses.cadres(Sprites.animation(jeu, "evolution"), "evo/${jeu.especeCompagnon}/${jeu.stade}") } catch (x: Exception) { null }
        val apres = try { Poses.album(jeu) } catch (x: Exception) { null }
        val ref = e?.let { Bestiaire.image(it, Creature.stadeCompagnon(jeu) ?: "bebe")?.h } ?: 40
        return Evo(jeu.nom, Regles.espece(jeu.stade, jeu.forme, jeu.especeCompagnon), avant, cadres, apres, ref, t0)
    }

    fun evolution(tl: Toile, ev: Evo, w: Float, h: Float, z: Float, maintenant: Double) {
        val E = EspaceDessin
        val tt = maintenant - ev.t0
        val (ph, p) = Creature.phaseEvolution(tt)
        tl.rect(0f, 0f, w, h, 0xF2050609.toInt())
        val x = 14 * z; val lw = w - 28 * z
        val ch = min(h - 80 * z, 560 * z)
        val y = (h - ch) / 2
        tl.rrect(x, y, lw, ch, 22 * z, 0xFF0C0E14.toInt(), E.a(E.VERT, if (ph == "fete") 150 else 60), 2f * z)
        val cx = w / 2; val pieds = y + ch * 0.62f
        val haut = min(ch * 0.4f, lw * 0.55f)
        val e = max(1f, (haut / max(1, ev.ref)).toInt().toFloat())
        tl.lueur(cx, pieds - haut * 0.45f, lw * 0.5f, E.a(E.VERT, 28))
        when (ph) {
            "appel" -> {
                val g = java.util.Random(5)
                repeat(70) {
                    val x0 = x + g.nextFloat() * lw; val y0 = y + g.nextFloat() * ch; val v = 0.5f + g.nextFloat() * 0.5f
                    val q = min(1.0, p * v * 1.4).toFloat()
                    val s = (if (v > 0.8f) 4 else 3) * z
                    tl.rect(x0 + (cx - x0) * q, y0 + (pieds - haut * 0.45f - y0) * q, s, s, E.a(E.VERT, 200))
                }
                for (k in 0 until 7) {
                    val lx = cx - 120 * z + k * 40 * z
                    val hh = (60 + 40 * sin(tt * 5 + k)).toFloat() * z
                    val y0 = pieds - (((tt * 70 + k * 23) % 160).toFloat() * z)
                    tl.ligne(lx, y0, lx, y0 + hh, E.a(E.VERT, 90), 2 * z)
                }
                ev.avant?.let { al ->
                    var ea = haut / max(1, al.ref)
                    if (!al.lisse) ea = max(1f, ea.toInt().toFloat())
                    tl.cadre(al.image("assis", (tt * 8).toInt()), cx, pieds, ea, false, al.lisse)
                }
                tl.texte(t("cr.evo.brille", "nom" to ev.nom), cx, y + 50 * z, 20 * z, E.TEXTE, true, 'c')
            }
            "transformation", "eclat" -> {
                val cad = ev.cadres
                if (!cad.isNullOrEmpty()) {
                    val k = if (ph == "transformation") min(cad.size - 1, (p * cad.size).toInt()) else cad.size - 1
                    tl.cadre(cad[k], cx, pieds, e, false, false)
                }
                if (ph == "eclat") {
                    val a = (220 * (1 - p)).toInt()
                    tl.lueur(cx, pieds - haut * 0.45f, haut * (0.6f + 0.8f * p.toFloat()), (a shl 24) or 0xFFFFFF)
                    for (k in 0 until 8) {
                        val an = k * PI / 4
                        val r = haut * (0.5f + p.toFloat())
                        tl.ligne(cx, pieds - haut * 0.45f, cx + (cos(an) * r).toFloat(), pieds - haut * 0.45f + (sin(an) * r).toFloat(),
                            ((200 * (1 - p)).toInt() shl 24) or 0xFFF0B4, 3 * z)
                    }
                }
            }
            else -> {
                val k = (tt * 8).toInt()
                ev.apres?.let { al ->
                    var ea = haut / max(1, al.ref)
                    if (!al.lisse) ea = max(1f, ea.toInt().toFloat())
                    val saut = (abs(sin(tt * 6)) * 14 * z).toFloat()
                    tl.cadre(al.image("sursaut", k), cx, pieds - saut, ea, false, al.lisse)
                }
                for (i in 0 until 6) {
                    val an = i * PI / 3 + tt
                    pixels(tl, rangs(d().optJSONObject("glyphes"), "etoile"), cx + (cos(an) * haut * 0.75).toFloat() - 7 * z,
                        pieds - haut * 0.5f + (sin(an) * haut * 0.45).toFloat(), 3 * z, 230)
                }
                tl.texte(t("cr.evo.titre", "nom" to ev.nom), cx, pieds + 46 * z, 19 * z, E.DOUX, false, 'c')
                tl.texte(court(tl, ev.forme + " !", lw - 30 * z, 27 * z, true), cx, pieds + 82 * z, 27 * z, E.VERT, true, 'c')
                tl.texte("★ " + t("cr.evo.page"), cx, pieds + 118 * z, 14 * z, E.JAUNE, false, 'c')
                if (Creature.peutPasser(tt)) tl.texte(t("cr.evo.continuer.tel"), cx, y + ch - 22 * z, 13 * z, E.PALE, false, 'c')
            }
        }
    }
}
