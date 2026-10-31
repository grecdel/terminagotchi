package fr.terminagotchi

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/** Une surface de dessin (Canvas sur le téléphone, Java2D pour les captures des tests). Couleurs ARGB ; y du texte =
 *  milieu de la ligne ; ancre 'g' (gauche), 'c' (centre), 'd' (droite). */
interface Toile {
    fun rect(x: Float, y: Float, w: Float, h: Float, c: Int)
    fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float)
    fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int)
    fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float)
    fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float = 0f, vide: Float = 0f, dec: Float = 0f)
    fun poly(xs: FloatArray, ys: FloatArray, c: Int)
    fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean = false, ancre: Char = 'g', mono: Boolean = false)
    fun mesure(s: String, taille: Float, gras: Boolean = false, mono: Boolean = false): Float
    fun lueur(cx: Float, cy: Float, r: Float, c: Int)
    /** une image de la créature posée par ses pieds (ax, ay), à l'échelle e, déformée autour des pieds */
    fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float = 1f, sy: Float = 1f,
              rot: Float = 0f, alpha: Float = 1f)
    /** une illustration (« monde » : la carte du Terminaworld), recadrée pour remplir, coins arrondis */
    fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float)
}

/**
 * L'espace de travail sur le téléphone (maquette validée docs/maquettes/espace_travail_telephone.png) : l'île en
 * haut (la créature, son état, l'équipe en pastilles), les onglets Terminal · Carte · Cerveau · Équipe, puis la carte
 * de la créature (en direct, ses envies) et la vue déployée de la dernière commande ; le terminal (le vrai, celui de
 * TerminalActivity) est juste en dessous. Même dessin que le PC (pc/tg/espace_scene.py), en plus étroit.
 * Mode classe (grand écran) : tout est agrandi (zoom) ; sur un écran large, la créature et la vue déployée côte à côte.
 */
object EspaceDessin {
    const val FOND = 0xFF090B10.toInt()
    const val PANNEAU = 0xFF0F1118.toInt()
    const val PANNEAU2 = 0xFF141720.toInt()
    const val BORD = 0x16FFFFFF
    const val BORD_FORT = 0x2CFFFFFF
    const val TEXTE = 0xFFE9ECF2.toInt()
    const val DOUX = 0xFF8A93A6.toInt()
    const val PALE = 0xFF5C6476.toInt()
    const val VERT = 0xFF3DDC84.toInt()
    const val ORANGE = 0xFFFF9F43.toInt()
    const val JAUNE = 0xFFFFD54F.toInt()
    const val VIOLET = 0xFFB284FF.toInt()
    const val BLEU = 0xFF5FAFFF.toInt()
    const val CYAN = 0xFF4DD0E1.toInt()
    const val ROSE = 0xFFFF79C6.toInt()
    const val ROUGE = 0xFFFF5F6D.toInt()
    val COUL_ENVIES = mapOf("faim" to 0xFFFFA85C.toInt(), "jeu" to ROSE, "curiosite" to JAUNE, "explorer" to VERT,
        "sommeil" to VIOLET, "proprete" to CYAN)
    val COUL_STATUT = mapOf("mange" to VERT, "dort" to VIOLET, "pret" to BLEU, "faim" to ORANGE)
    val ONGLETS = listOf("terminal", "carte", "cerveau", "equipe")
    val LIEUX_CARTE = mapOf("salle_des_machines" to (0.16f to 0.10f), "tour" to (0.84f to 0.10f),
        "bibliotheque" to (0.10f to 0.36f), "coeur" to (0.50f to 0.29f), "atelier" to (0.84f to 0.36f),
        "cave" to (0.86f to 0.55f), "nid" to (0.50f to 0.47f), "vestibule" to (0.55f to 0.71f),
        "dortoir" to (0.85f to 0.80f), "grenier" to (0.27f to 0.74f))

    fun a(c: Int, alpha: Int) = (c and 0xFFFFFF) or (alpha.coerceIn(0, 255) shl 24)

    /** Un membre de l'équipe : son album, son nom, sa ligne, son statut (mange, dort, pret, faim), actif. */
    class Membre(val album: Poses.Album?, val nom: String, val sous: String, val statut: String, val actif: Boolean)

    /** Tout ce que le dessin montre (rempli par EspaceVue depuis le jeu, ou par les tests). */
    class Modele {
        var nom = ""
        var especeStade = ""
        var etat = "content"
        var gains = ""
        var lieuChip = ""
        var equipe = listOf<Membre>()
        var envies = listOf<Triple<String, String, Pair<Double, Boolean>>>()   // (nom, clé, (valeur, monte))
        var assiette = listOf<Pair<String, Boolean>>()
        var satiete = ""
        var album: Poses.Album? = null
        var anime: BureauVie.Anime? = null
        var mini = Triple("assis", 1f, 1f)
        var t = 0.0
        var bulle: String? = null
        var vue: Deploie.Vue? = null
        var onglet = "terminal"
        var cerveau: Cerveau.Vivant? = null
        var lieux = mapOf<String, Pair<String, String>>()   // pièce → (nom court, « reveille » | « en_cours » | « brume »)
        var ici: String? = null
        var iciNom = ""
        var cwd = ""
        var evenement: String? = null
        var zoom = 1f
        var classe = false
        // l'apparence (Apparence.kt) : thème, onglets et bandes déjà apparus, arrivées, rangement, options
        var theme: Apparence.Theme? = null
        var onglets = ONGLETS
        var bandes = listOf(Apparence.Bande("creature", "M"), Apparence.Bande("deploie", "M"))
        var envies_visibles = true
        var arrivees = mapOf<String, Double>()           // panneau → âge (secondes) de son arrivée
        var rangement = false
        var glisse: Pair<String, Float>? = null          // la bande tenue (appui long) et son y sous le doigt
        var caches = listOf<String>()
        var ordreOnglets = ONGLETS
        var dispo = "classique"
        var options = false
        var tout = false
        var mienne = false
    }

    /** Une zone qu'on peut toucher : (x, y, w, h, action). */
    class Zone(val x: Float, val y: Float, val w: Float, val h: Float, val action: String) {
        fun dedans(px: Float, py: Float) = px >= x && px <= x + w && py >= y && py <= y + h
    }

    /** La hauteur voulue (pixels) pour une largeur et une hauteur disponible : complet, ou plus compact. */
    fun hauteur(m: Modele, largeur: Float, dispo: Float, d: Float): Float {
        val z = d * m.zoom
        if (m.rangement || m.options) return max(300 * z, dispo)
        val large = largeur / z >= 700
        if (m.onglet == "terminal" && !large) {                     // les bandes choisies, à leur taille
            val tot = (76 + 54) * z + m.bandes.sumOf { ((if (it.id == "creature") 198 else 212) * Apparence.tailleFacteur(it.taille) + 12).toDouble() }.toFloat() * z
            return max((76 + 54 + 40) * z, min(tot, dispo))
        }
        val complet = when (m.onglet) {
            "terminal" -> if (large) 76 + 54 + 250 + 12 else 76 + 54 + 198 + 12 + 212 + 10
            else -> 76 + 54 + 430
        } * z
        if (complet <= dispo) return complet
        val compact = (76 + 54 + 212 + 10) * z
        if (m.onglet == "terminal" && compact <= dispo) return compact
        return max((76 + 54 + 150) * z, min(complet, dispo))
    }

    /** Dessine tout dans (0, 0, w, h) : renvoie les zones à toucher. */
    fun dessiner(tl0: Toile, m: Modele, w: Float, h: Float, d: Float): List<Zone> {
        val th = m.theme
        val tl = if (th == null || th.sombre) tl0 else ToileTheme(tl0, th)
        val z = d * m.zoom
        val Z = mutableListOf<Zone>()
        tl.rect(0f, 0f, w, h, FOND)
        if (m.rangement) { rangement(tl, Z, m, w, h, z); return Z }
        if (m.options) { options(tl, tl0, Z, m, w, h, z); return Z }
        val mx = 12 * z
        var y = 8 * z
        ile(tl, Z, m, mx, y, w - 2 * mx, 64 * z, z)
        y += 76 * z
        onglets(tl, Z, m, mx, y, w - 2 * mx, 44 * z, z)
        y += 54 * z
        val reste = h - y
        when (m.onglet) {
            "terminal" -> {
                val large = w / z >= 700
                if (!large) {
                    for (b in m.bandes) {
                        val hb = (if (b.id == "creature") 198 else 212) * Apparence.tailleFacteur(b.taille) * z
                        if (y + 40 * z > h) break
                        val hh = min(hb, h - y - 4 * z)
                        if (b.id == "creature") creature(tl, Z, m, mx, y, w - 2 * mx, hh, z) else deploie(tl, Z, m, mx, y, w - 2 * mx, hh, z)
                        Z.add(0, Zone(mx, y, w - 2 * mx, hh, "bande:" + b.id))   // sous les autres zones (appui long)
                        arrivee(tl, m, if (b.id == "creature") "envies" else "deploie", mx, y, w - 2 * mx, hh, z)
                        y += hh + 12 * z
                    }
                } else if (large) {
                    val cw = (w - 2 * mx - 12 * z) * 0.42f
                    creature(tl, Z, m, mx, y, cw, min(250 * z, reste - 4 * z), z)
                    deploie(tl, Z, m, mx + cw + 12 * z, y, w - 2 * mx - cw - 12 * z, min(250 * z, reste - 4 * z), z)
                } else if (reste >= (198 + 12 + 212) * z) {
                    creature(tl, Z, m, mx, y, w - 2 * mx, 198 * z, z)
                    y += 210 * z
                    deploie(tl, Z, m, mx, y, w - 2 * mx, min(212 * z, h - y - 4 * z), z)
                } else deploie(tl, Z, m, mx, y, w - 2 * mx, min(212 * z, reste - 4 * z), z)
            }
            "carte" -> carte(tl, Z, m, mx, y, w - 2 * mx, reste - 6 * z, z)
            "cerveau" -> cerveau(tl, Z, m, mx, y, w - 2 * mx, reste - 6 * z, z)
            else -> equipe(tl, Z, m, mx, y, w - 2 * mx, reste - 6 * z, z)
        }
        return Z
    }

    private fun court(tl: Toile, s: String, l: Float, taille: Float, mono: Boolean = false, gras: Boolean = false): String {
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

    private fun creatureImg(tl: Toile, al: Poses.Album, etat: String, k: Int, cx: Float, pieds: Float, haut: Float,
                            sx: Float = 1f, sy: Float = 1f) {
        val c = al.image(etat, k)
        var e = haut / max(1, al.ref)
        if (!al.lisse) e = max(1f, e.toInt().toFloat())
        tl.cadre(c, cx, pieds, e, false, al.lisse, sx, sy)
    }

    // ------------------------------------------------------------ l'île
    private fun ile(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val evt = m.evenement
        tl.rrect(x, y, w, h, h / 2, PANNEAU, if (evt != null) a(ROUGE, 160) else BORD_FORT, 1.2f * z)
        Z.add(Zone(x, y, w, h, "ile"))
        val r = h / 2 - 6 * z
        val cx = x + 6 * z + r
        tl.ellipse(cx, y + h / 2, r, r, PANNEAU2)
        tl.cercle(cx, y + h / 2, r, a(VERT, 150), 1.5f * z)
        m.album?.let { al -> creatureImg(tl, al, m.mini.first, (m.t * BureauVie.IPS).toInt(), cx, y + h - 9 * z, r * 1.5f, m.mini.second, m.mini.third) }
        val tx = cx + r + 12 * z
        val n = m.equipe.size.coerceAtMost(4)
        val pw = 38 * z
        val ex = x + w - 10 * z - n * (pw + 6 * z)
        if (evt != null) {
            tl.texte(court(tl, evt, x + w - tx - 12 * z, 14 * z, gras = true), tx, y + h / 2, 14 * z, TEXTE, true)
            arrivee(tl, m, "ile", x, y, w, h, z)
            return
        }
        tl.texte(court(tl, m.nom, ex - tx - 8 * z, 17 * z, gras = true), tx, y + h / 2 - 10 * z, 17 * z, TEXTE, true)
        val ce = Cerveau.COULEURS[m.etat]?.takeIf { m.etat != "content" } ?: VERT
        tl.ellipse(tx + 5 * z, y + h / 2 + 12 * z, 5 * z, 5 * z, ce)
        val en = Cerveau.nomEtat(m.etat)
        tl.texte(en, tx + 15 * z, y + h / 2 + 12 * z, 14 * z, ce)
        if (m.gains.isNotEmpty()) {
            val gx = tx + 19 * z + tl.mesure(en, 14 * z)
            tl.texte(court(tl, "· " + m.gains, ex - gx - 6 * z, 14 * z), gx, y + h / 2 + 12 * z, 14 * z, DOUX)
        }
        for ((i, mb) in m.equipe.take(4).withIndex()) {
            val bx = ex + i * (pw + 6 * z)
            val by = y + (h - pw) / 2
            tl.rrect(bx, by, pw, pw, 10 * z, PANNEAU2, if (mb.actif) a(VERT, 160) else BORD, 1.4f * z)
            mb.album?.let { creatureImg(tl, it, "assis", 0, bx + pw / 2, by + pw - 4 * z, pw * 0.72f) }
            tl.ellipse(bx + pw - 3 * z, by + 3 * z, 4.5f * z, 4.5f * z, COUL_STATUT[mb.statut] ?: BLEU)
            Z.add(Zone(bx, by, pw, pw, "equipe:$i"))
        }
        arrivee(tl, m, if ("equipe" in m.arrivees) "equipe" else "ile", x, y, w, h, z)
    }

    private fun onglets(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 14 * z, PANNEAU, BORD, 1f * z)
        val ow = (w - 8 * z) / m.onglets.size
        for ((i, o) in m.onglets.withIndex()) {
            val ox = x + 4 * z + i * ow
            if (o == m.onglet) tl.rrect(ox, y + 4 * z, ow, h - 8 * z, 11 * z, 0x1CFFFFFF, BORD_FORT, 1f * z)
            tl.texte(court(tl, t("esp.onglet.$o"), ow - 8 * z, 15 * z), ox + ow / 2, y + h / 2, 15 * z,
                if (o == m.onglet) TEXTE else DOUX, false, 'c')
            Z.add(Zone(ox, y, ow, h, "onglet:$o"))
        }
        val neuf = m.onglets.firstOrNull { (Apparence.d().getJSONObject("telephone").optJSONObject("onglet_de")?.optString(it, "") ?: "") in m.arrivees }
        if (neuf != null) arrivee(tl, m, Apparence.d().getJSONObject("telephone").getJSONObject("onglet_de").getString(neuf), x, y, w, h, z,
            t("esp.nouvel_onglet"))
    }

    // ------------------------------------------------------------ l'arrivée d'un panneau (interface évolutive)
    const val ARRIVEE = 4.0

    /** Un panneau qui vient d'apparaître : un bord doré qui pulse puis s'efface, et la pastille « nouveau ». */
    fun arrivee(tl: Toile, m: Modele, pan: String, x: Float, y: Float, w: Float, h: Float, z: Float, texte: String = t("esp.nouveau")) {
        val age = m.arrivees[pan] ?: return
        val k = (1 - age / ARRIVEE).coerceIn(0.0, 1.0)
        if (k <= 0) return
        val pul = 0.6 + 0.4 * sin(age * 6)
        tl.rrect(x - 4 * z, y - 4 * z, w + 8 * z, h + 8 * z, 20 * z, null, a(JAUNE, (70 * k * pul).toInt()), 5 * z)
        tl.rrect(x - 1 * z, y - 1 * z, w + 2 * z, h + 2 * z, 17 * z, null, a(JAUNE, (235 * k).toInt()), 2 * z)
        if (age < ARRIVEE * 0.8) {
            val s = "✦ $texte"
            val tw = tl.mesure(s, 12 * z, true) + 20 * z
            tl.rrect(x + w - tw - 12 * z, y - 11 * z, tw, 22 * z, 11 * z, 0xFF1E1A0C.toInt(), JAUNE, 1 * z)
            tl.texte(s, x + w - 12 * z - tw / 2, y, 12 * z, JAUNE, true, 'c')
        }
    }

    // ------------------------------------------------------------ la créature et ses envies
    private fun creature(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, PANNEAU, BORD, 1f * z)
        tl.texte(court(tl, (m.nom + " · " + m.especeStade).uppercase(), w * 0.55f, 11.5f * z, gras = true), x + 16 * z,
            y + 22 * z, 11.5f * z, DOUX, true)
        if (m.lieuChip.isNotEmpty()) {
            val cw = tl.mesure(m.lieuChip, 12.5f * z) + 22 * z
            tl.rrect(x + w - 12 * z - cw, y + 10 * z, cw, 24 * z, 12 * z, a(VERT, 22), a(VERT, 130), 1f * z)
            tl.texte(m.lieuChip, x + w - 12 * z - cw / 2, y + 22 * z, 12.5f * z, VERT, false, 'c')
        }
        val bx = x + 12 * z; val by = y + 40 * z; val bw = min(w * 0.36f, 150 * z); val bh = h - 52 * z
        tl.rrect(bx, by, bw, bh, 12 * z, 0xFF0D1016.toInt(), BORD, 1f * z)
        val ce = Cerveau.COULEURS[m.etat]?.takeIf { m.etat != "content" } ?: VERT
        tl.lueur(bx + bw / 2, by + bh * 0.55f, bw * 0.55f, a(ce, 40))
        val al = m.album; val an = m.anime
        if (al != null && an != null) {
            val haut = min(bh * 0.7f, bw * 0.62f)
            var e = haut / max(1, al.ref)
            if (!al.lisse) e = max(1f, e.toInt().toFloat())
            val pieds = by + bh - 12 * z
            an.ancien?.let { v -> tl.cadre(al.image(v.etat, v.k), bx + bw / 2, pieds + an.dy * z, e, v.miroir, al.lisse, an.sx, an.sy, an.rot, v.opacite) }
            tl.cadre(al.image(an.etat, an.k), bx + bw / 2, pieds + an.dy * z, e, an.miroir, al.lisse, an.sx, an.sy, an.rot, an.opacite)
            val ref = al.images("assis")[0]
            for (f in an.effets) {
                val ex = bx + bw / 2 + (if (an.miroir) -1 else 1) * f.x * ref.w * e
                val ey = pieds + f.y * ref.h * e
                val et = max(7 * z, f.taille * ref.h * e)
                val alpha = (255 * f.opacite.coerceIn(0f, 1f)).toInt()
                when (f.genre) {
                    "z" -> tl.texte("z", ex, ey, et, a(0xFFBED7FF.toInt(), alpha), true, 'c')
                    "coeur" -> tl.texte("♥", ex, ey, et, a(0xFFFF5F8C.toInt(), alpha), true, 'c')
                    "miette" -> tl.ellipse(ex, ey, et / 2, et / 2.4f, a(0xFFE8B04A.toInt(), alpha))
                }
            }
            Z.add(Zone(bx, by, bw, bh, "creature"))
        }
        // les envies (quand elles sont apparues)
        if (!m.envies_visibles) return
        val gx = bx + bw + 14 * z
        val gw = x + w - 12 * z - gx
        val pas = min(26 * z, (bh - 4 * z) / max(1, m.envies.size))
        for ((i, e) in m.envies.withIndex()) {
            val yy = by + 10 * z + pas * i
            tl.texte(court(tl, e.first, gw * 0.42f, 14 * z), gx, yy, 14 * z, TEXTE)
            val barX = gx + gw * 0.45f; val barW = gw * 0.38f
            tl.rrect(barX, yy - 3 * z, barW, 6 * z, 3 * z, 0x14FFFFFF, null, 0f)
            tl.rrect(barX, yy - 3 * z, max(6 * z, barW * (e.third.first.coerceIn(0.0, 100.0) / 100).toFloat()), 6 * z, 3 * z,
                COUL_ENVIES[e.second] ?: VERT, null, 0f)
            val monte = e.third.second
            tl.texte("${e.third.first.toInt()}" + if (monte) "↑" else "", gx + gw, yy, 13 * z, if (monte) VERT else DOUX, monte, 'd', true)
        }
    }

    // ------------------------------------------------------------ la vue déployée
    private fun deploie(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, PANNEAU, BORD, 1f * z)
        Z.add(Zone(x, y, w, h, "dep:suivant"))
        tl.texte(t("esp.vue_deployee").substringBefore(" ·").uppercase(), x + 16 * z, y + 22 * z, 11.5f * z, DOUX, true)
        val v = m.vue
        if (v == null) {
            tl.texte(court(tl, t("esp.deploie_vide"), w - 32 * z, 13 * z), x + w / 2, y + h / 2, 13 * z, DOUX, false, 'c')
            return
        }
        val bl = v.blocs
        val ent = t("esp.etape", "k" to v.actif, "n" to bl.size) + " · " + t(if (v.auto) "esp.auto" else "esp.touche_avancer")
        tl.texte(court(tl, ent, w * 0.5f, 12.5f * z), x + w - 14 * z, y + 22 * z, 12.5f * z, DOUX, false, 'd')
        // les blocs (rapetissés pour tenir sur une rangée)
        var taille = 22 * z
        var gap = 10 * z
        fun total(tt: Float) = bl.sumOf { (tl.mesure(it.t, tt, true, true) + 18 * z).toDouble() }.toFloat() + gap * (bl.size - 1)
        while (taille > 10 * z && total(taille) > w - 28 * z) { taille -= 1 * z; gap = max(5 * z, gap - 0.5f * z) }
        var bx = x + 14 * z + max(0f, (w - 28 * z - total(taille)) / 2)
        val cy = y + 58 * z
        for (b in bl) {
            val bw = tl.mesure(b.t, taille, true, true) + 18 * z
            val col = Deploie.COULEURS.getValue(b.g)
            val actif = b.i == v.actif
            if (actif) for (k in 0 until 3) tl.rrect(bx - 2 * z - 2 * k * z, cy - 18 * z - 2 * z - 2 * k * z, bw + 4 * z + 4 * k * z,
                36 * z + 4 * z + 4 * k * z, (13 + 2 * k) * z, null, a(col, 70 - 20 * k), 2 * z)
            val fond = when { b.i < v.actif -> a(col, 22); actif -> a(col, 40); else -> 0x08FFFFFF }
            val bord = when { b.i < v.actif -> a(col, 170); actif -> col; else -> a(col, 60) }
            tl.rrect(bx, cy - 18 * z, bw, 36 * z, 11 * z, fond, bord, (if (actif) 2.5f else 1.2f) * z)
            tl.texte(b.t, bx + bw / 2, cy, taille, if (b.i <= v.actif) col else a(col, 110), true, 'c', true)
            val nx = bx + 3 * z; val ny = cy - 19 * z
            tl.ellipse(nx, ny, 9 * z, 9 * z, PANNEAU)
            tl.cercle(nx, ny, 9 * z, a(col, if (b.i <= v.actif) 230 else 90), 1.3f * z)
            tl.texte("${b.i}", nx, ny, 10 * z, if (b.i <= v.actif) TEXTE else DOUX, true, 'c')
            bx += bw + gap
        }
        // l'explication du bloc allumé
        val b = bl[v.actif - 1]
        val col = Deploie.COULEURS.getValue(b.g)
        val ey = cy + 32 * z
        val lignes = couper(tl, Deploie.longue(b, bl), w - 60 * z, 15 * z).take(2)
        val eh = 22 * z + 21 * z * lignes.size
        tl.rrect(x + 14 * z, ey, w - 28 * z, eh, 14 * z, a(col, 16), a(col, 120), 1.2f * z)
        for ((i, l) in lignes.withIndex()) {
            if (i == 0 && l.startsWith(b.t)) {
                tl.texte(b.t, x + 30 * z, ey + 21 * z, 15 * z, col, true)
                tl.texte(l.substring(b.t.length), x + 30 * z + tl.mesure(b.t, 15 * z, true), ey + 21 * z, 15 * z, TEXTE)
            } else tl.texte(l, x + 30 * z, ey + 21 * z + 21 * z * i, 15 * z, TEXTE)
        }
        // le flux : la sortie de la 1re commande, le tuyau animé, ce que garde la 2e
        val fy = ey + eh + 12 * z
        if (fy + 34 * z > y + h) return
        val msg = v.messagerDe(b)
        if (msg != null) PortDessin.messager(tl, msg, v.phase, x + 14 * z, fy, w - 28 * z, 34 * z, z)   // le Port
        else flux(tl, v, x + 14 * z, fy, w - 28 * z, 34 * z, z)
    }

    private fun flux(tl: Toile, v: Deploie.Vue, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val k = v.actif - 1
        val c = v.chaines.firstOrNull { k in it.debut..it.fin } ?: v.chaines.firstOrNull() ?: return
        val ci = v.chaines.indexOf(c)
        val s = v.sorties?.getOrNull(ci)
        val et = c.etapes
        val b = v.blocs[k]
        var j = et.indexOfLast { it.debut <= k }.coerceAtLeast(0)
        if (et.size >= 2) j = j.coerceAtMost(et.size - 2)
        val ea = et[j]
        val la = s?.getOrNull(j) ?: emptyList()
        val gauche = ea.cmd + " · " + t("esp.n_lignes", "n" to (if (s != null) la.size else "?"))
        val lw = min(w * 0.33f, tl.mesure(gauche, 12 * z, mono = true) + 24 * z)
        tl.rrect(x, y, lw, h, h / 2, 0x0AFFFFFF, BORD_FORT, 1f * z)
        tl.texte(court(tl, gauche, lw - 16 * z, 12 * z, true), x + lw / 2, y + h / 2, 12 * z, DOUX, false, 'c', true)
        if (et.size < 2 && c.redir == null) return
        val dest = if (et.size >= 2) et[j + 1].cmd + " → " + (s?.getOrNull(j + 1)?.size ?: "?") else "📄 " + (c.redir?.fichier ?: "")
        val rw = min(w * 0.3f, tl.mesure(dest, 13 * z, true, true) + 24 * z)
        val rx = x + w - rw
        val coulR = if (et.size >= 2) VERT else ROSE
        tl.rrect(rx, y, rw, h, h / 2, a(coulR, 18), a(coulR, 150), 1.2f * z)
        tl.texte(court(tl, dest, rw - 16 * z, 13 * z, true, true), rx + rw / 2, y + h / 2, 13 * z, coulR, true, 'c', true)
        // le tuyau
        val tx1 = x + lw + 10 * z; val tx2 = rx - 10 * z
        val tuyau = et.size >= 2
        val coul = if (tuyau) VIOLET else ROSE
        val vu = k > ea.fin
        tl.rrect(tx1, y, tx2 - tx1, h, h / 2, a(coul, if (vu) 18 else 6), if (vu) coul else a(coul, 70), 1.4f * z)
        val dec = ((v.t * 60) % 14).toFloat() * z
        tl.ligne(tx1 + 14 * z, y + h / 2, tx2 - 14 * z, y + h / 2, if (vu) coul else a(coul, 70), 1.5f * z, 6 * z, 6 * z, -dec)
        if (vu && la.isNotEmpty()) {
            val anime = b.g == "tuyau" || b.g == "redirection"
            val ligne = if (anime) la[((v.phase * la.size).toInt()) % la.size] else la.last()
            val pos = if (anime) ((v.phase * la.size) % 1.0).toFloat() else 0.5f
            val txt = court(tl, ligne, (tx2 - tx1) * 0.55f, 12 * z, true, true)
            val ew = tl.mesure(txt, 12 * z, true, true) + 18 * z
            val ex = tx1 + 10 * z + pos * max(0f, tx2 - tx1 - 20 * z - ew)
            tl.rrect(ex, y + 6 * z, ew, h - 12 * z, (h - 12 * z) / 2, 0xFF100E1E.toInt(), coul, 1.2f * z)
            tl.texte(txt, ex + ew / 2, y + h / 2, 12 * z, TEXTE, true, 'c', true)
        }
    }

    // ------------------------------------------------------------ la carte
    private fun carte(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, PANNEAU, BORD, 1f * z)
        val px = x + 8 * z; val py = y + 8 * z; val pw = w - 16 * z; val ph = h - 44 * z
        tl.photo("monde", px, py, pw, ph, 12 * z)
        val chemin = m.vue?.lieu?.second
        for ((p, pos) in LIEUX_CARTE) {
            val l = m.lieux[p] ?: continue
            if (p == m.ici) continue
            val lx = px + pos.first * pw; val ly = py + pos.second * ph
            val sym = when (l.second) { "reveille" -> "✓ "; "en_cours" -> "▶ "; else -> "" }
            val txt = sym + l.first
            val tw = tl.mesure(txt, 12 * z) + 16 * z
            tl.rrect(lx - tw / 2, ly - 11 * z, tw, 22 * z, 11 * z, 0xD90A0C12.toInt(), if (p == chemin) CYAN else BORD_FORT, 1.2f * z)
            tl.texte(txt, lx, ly, 12 * z, if (l.second == "reveille") VERT else if (l.second == "brume") DOUX else TEXTE, false, 'c')
        }
        val ici = m.ici
        val pos = if (ici != null) LIEUX_CARTE[ici] else null
        if (pos != null) {
            val lx = px + pos.first * pw; val ly = py + pos.second * ph
            val pul = (0.5 + 0.5 * sin(m.t * 3)).toFloat()
            tl.lueur(lx, ly, (34 + 8 * pul) * z, 0x46FFD54F)
            tl.cercle(lx, ly, (20 + 3 * pul) * z, JAUNE, 1.6f * z)
            tl.ellipse(lx, ly, 6 * z, 6 * z, JAUNE)
            val info = t("esp.tu_es_ici", "lieu" to m.iciNom)
            val bw = min(pw - 16 * z, max(tl.mesure(info, 13 * z, true), tl.mesure(m.cwd, 11 * z, mono = true)) + 36 * z)
            val bx = (lx - 30 * z).coerceIn(px + 8 * z, px + pw - bw - 8 * z)
            val by = min(ly + 30 * z, py + ph - 56 * z)
            tl.rrect(bx, by, bw, 48 * z, 10 * z, 0xE60A0C12.toInt(), a(JAUNE, 120), 1f * z)
            tl.ellipse(bx + 14 * z, by + 16 * z, 4.5f * z, 4.5f * z, JAUNE)
            tl.texte(court(tl, info, bw - 32 * z, 13 * z, gras = true), bx + 24 * z, by + 16 * z, 13 * z, TEXTE, true)
            tl.texte(court(tl, m.cwd, bw - 24 * z, 11 * z, true), bx + 14 * z, by + 34 * z, 11 * z, DOUX, false, 'g', true)
        }
        tl.texte(court(tl, "◉ " + t("esp.l.ici") + "   ▶ " + t("esp.l.en_cours") + "   ✓ " + t("esp.l.reveille"), w - 24 * z, 12 * z),
            x + 14 * z, y + h - 18 * z, 12 * z, DOUX)
    }

    // ------------------------------------------------------------ le cerveau
    private fun cerveau(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val cv = m.cerveau ?: return
        tl.rrect(x, y, w, h, 16 * z, PANNEAU, BORD, 1f * z)
        val code = Cerveau.texteProgramme(m.nom)
        val enCours = cv.ligneEnCours(m.t)
        val faites = cv.trace.lignes.map { it.first }.toSet()
        // la machine à états, en haut
        val mh = min(h * 0.42f, 210 * z)
        val mx = x + 10 * z; val my = y + 10 * z; val mw = w - 20 * z
        tl.rrect(mx, my, mw, mh, 12 * z, 0xFF0B0D13.toInt(), BORD, 1f * z)
        tl.texte(t("cerv.machine", "n" to Cerveau.ETATS.size), mx + 12 * z, my + 16 * z, 11 * z, DOUX)
        val places = Cerveau.PLACES.mapValues { (_, p) -> (mx + 24 * z + p.first * (mw - 48 * z)) to (my + 36 * z + p.second * (mh - 62 * z)) }
        for ((de, vers) in Cerveau.transitions()) {
            val (x1, y1) = places.getValue(de); val (x2, y2) = places.getValue(vers)
            val dx = x2 - x1; val dy = y2 - y1; val dist = max(1f, hypot(dx, dy))
            val nx = -dy / dist * 4 * z; val ny = dx / dist * 4 * z
            val ax1 = x1 + nx + dx * 16 * z / dist; val ay1 = y1 + ny + dy * 16 * z / dist
            val ax2 = x2 + nx - dx * 18 * z / dist; val ay2 = y2 + ny - dy * 18 * z / dist
            val prise = de == cv.trace.de && vers == cv.trace.vers && de != vers
            fleche(tl, ax1, ay1, ax2, ay2, if (prise) VERT else 0x82788296.toInt(), (if (prise) 2.2f else 1.1f) * z,
                if (prise) ((m.t * 40) % 12).toFloat() * z else -1f, z)
        }
        for ((e, p) in places) {
            val nom = Cerveau.nomEtat(e)
            val tw = tl.mesure(nom, 12 * z, mono = true) + 28 * z
            val actif = e == cv.etat
            if (actif) {
                tl.lueur(p.first, p.second, tw * 0.7f, a(VERT, 60))
                tl.rrect(p.first - tw / 2, p.second - 12 * z, tw, 24 * z, 12 * z, a(VERT, 40), VERT, 2 * z)
            } else tl.rrect(p.first - tw / 2, p.second - 12 * z, tw, 24 * z, 12 * z, 0xFF0E1016.toInt(), BORD_FORT, 1f * z)
            tl.ellipse(p.first - tw / 2 + 12 * z, p.second, 4 * z, 4 * z, Cerveau.COULEURS.getValue(e))
            tl.texte(nom, p.first - tw / 2 + 21 * z, p.second, 12 * z, if (actif) TEXTE else DOUX, actif, 'g', true)
            Z.add(Zone(p.first - tw / 2, p.second - 12 * z, tw, 24 * z, "forcer:$e"))
        }
        // le code, au milieu
        val cy0 = my + mh + 8 * z
        val ch = h - (cy0 - y) - 48 * z
        tl.rrect(mx, cy0, mw, ch, 12 * z, 0xFF0B0D13.toInt(), BORD, 1f * z)
        val pas = 17 * z
        val n = ((ch - 12 * z) / pas).toInt()
        val k = enCours?.first ?: 0
        val debut = (k - n / 2).coerceIn(0, max(0, code.size - n))
        for (i in debut until min(code.size, debut + n)) {
            val yy = cy0 + 12 * z + pas * (i - debut)
            if (i == enCours?.first) {
                val c = if (enCours.second == "faux") ROUGE else VERT
                tl.rect(mx + 1 * z, yy - pas / 2, mw - 2 * z, pas, a(c, 36))
                tl.rect(mx + 1 * z, yy - pas / 2, 3 * z, pas, c)
            }
            tl.texte("${i + 1}", mx + 24 * z, yy, 10.5f * z, PALE, false, 'd', true)
            val col = if (code[i].trim().startsWith("#")) 0xFF788296.toInt() else if (i in faites || i == enCours?.first) TEXTE else DOUX
            tl.texte(court(tl, code[i], mw - 42 * z, 12 * z, true), mx + 32 * z, yy, 12 * z, col, i == enCours?.first, 'g', true)
        }
        // forcer un état
        val fy = y + h - 22 * z
        var fx = x + 12 * z
        val place = w - 24 * z
        val besoin = Cerveau.ETATS.sumOf { (tl.mesure(Cerveau.nomEtat(it), 12 * z) + 34 * z).toDouble() }.toFloat() + 5 * z * 6
        val serre = min(1f, place / besoin)
        for (e in Cerveau.ETATS) {
            val nom = Cerveau.nomEtat(e)
            val on = cv.force == e
            val bw = (tl.mesure(nom, 12 * z) + 34 * z) * serre
            tl.rrect(fx, fy - 12 * z, bw, 24 * z, 12 * z, if (on) a(VERT, 34) else 0x08FFFFFF, if (on) VERT else BORD_FORT, 1f * z)
            tl.rrect(fx + 6 * z, fy - 5 * z, 16 * z, 10 * z, 5 * z, if (on) VERT else 0x1EFFFFFF, null, 0f)
            tl.ellipse(fx + (if (on) 17 else 11) * z, fy, 4 * z, 4 * z, TEXTE)
            tl.texte(court(tl, nom, bw - 28 * z, 12 * z * max(0.85f, serre)), fx + 26 * z, fy, 12 * z * max(0.85f, serre),
                if (on) TEXTE else DOUX, on)
            Z.add(Zone(fx, fy - 14 * z, bw, 28 * z, "forcer:$e"))
            fx += bw + 5 * z * serre
        }
    }

    private fun fleche(tl: Toile, x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, dec: Float, z: Float) {
        if (dec >= 0) tl.ligne(x1, y1, x2, y2, c, ep, 6 * z, 6 * z, -dec) else tl.ligne(x1, y1, x2, y2, c, ep)
        val an = atan2(y2 - y1, x2 - x1)
        val p = 7 * z
        tl.poly(floatArrayOf(x2, x2 - p * cos(an - 0.45f), x2 - p * cos(an + 0.45f)),
            floatArrayOf(y2, y2 - p * sin(an - 0.45f), y2 - p * sin(an + 0.45f)), c)
    }

    // ------------------------------------------------------------ l'équipe
    private fun equipe(tl: Toile, Z: MutableList<Zone>, m: Modele, x: Float, y: Float, w: Float, h: Float, z: Float) {
        tl.rrect(x, y, w, h, 16 * z, PANNEAU, BORD, 1f * z)
        tl.texte(t("esp.equipe").uppercase(), x + 16 * z, y + 22 * z, 11.5f * z, DOUX, true)
        var yy = y + 40 * z
        for ((i, mb) in m.equipe.withIndex()) {
            if (yy + 56 * z > y + h) break
            if (mb.actif) tl.rrect(x + 10 * z, yy, w - 20 * z, 56 * z, 12 * z, 0x0CFFFFFF, BORD_FORT, 1f * z)
            mb.album?.let { creatureImg(tl, it, "assis", 0, x + 40 * z, yy + 50 * z, 42 * z) }
            tl.texte(mb.nom, x + 72 * z, yy + 19 * z, 15 * z, TEXTE)
            tl.texte(court(tl, mb.sous, w - 180 * z, 12 * z), x + 72 * z, yy + 39 * z, 12 * z, PALE)
            val st = t("esp.statut." + mb.statut)
            tl.ellipse(x + w - 26 * z - tl.mesure(st, 13 * z), yy + 28 * z, 4 * z, 4 * z, COUL_STATUT[mb.statut] ?: BLEU)
            tl.texte(st, x + w - 18 * z, yy + 28 * z, 13 * z, DOUX, false, 'd')
            Z.add(Zone(x + 10 * z, yy, w - 20 * z, 56 * z, "equipe:$i"))
            yy += 62 * z
        }
    }
    // ------------------------------------------------------------ ranger mon espace (téléphone)
    private fun bouton(tl: Toile, Z: MutableList<Zone>, x: Float, y: Float, w: Float, s: String, action: String, z: Float,
                       c: Int = TEXTE, fond: Int? = null, bord: Int? = null, gras: Boolean = false) {
        tl.rrect(x, y, w, 36 * z, 11 * z, fond ?: 0x0EFFFFFF, bord ?: BORD_FORT, 1f * z)
        tl.texte(court(tl, s, w - 12 * z, 13.5f * z, gras = gras), x + w / 2, y + 18 * z, 13.5f * z, c, gras, 'c')
        Z.add(Zone(x, y, w, 36 * z, action))
    }

    private fun croix(tl: Toile, Z: MutableList<Zone>, cx: Float, cy: Float, action: String, z: Float) {
        tl.ellipse(cx, cy, 14 * z, 14 * z, 0xFF28161A.toInt())
        tl.cercle(cx, cy, 14 * z, a(ROUGE, 200), 1.2f * z)
        tl.texte("✕", cx, cy, 12 * z, ROUGE, true, 'c')
        Z.add(Zone(cx - 18 * z, cy - 18 * z, 36 * z, 36 * z, action))
    }

    /** Le mode rangement du téléphone : la liste des bandes (≡ pour les déplacer, taille P / M / G, ✕ pour les cacher),
     *  l'ordre des onglets, les bandes cachées, les dispositions toutes prêtes. Les bandes pas encore découvertes
     *  n'apparaissent pas. */
    fun rangement(tl: Toile, Z: MutableList<Zone>, m: Modele, w: Float, h: Float, z: Float) {
        val x = 14 * z; val lw = w - 28 * z
        tl.texte("✎ " + t("esp.rg.titre"), 20 * z, 26 * z, 21 * z, JAUNE, true)
        var y = 52 * z
        for (l in couper(tl, t("esp.rg.tel.aide"), w - 40 * z, 12.5f * z)) { tl.texte(l, 20 * z, y, 12.5f * z, DOUX); y += 17 * z }
        y += 6 * z
        fun ligne(nom: String, yy: Float, fond: Int, bord: Int) {
            tl.rrect(x, yy, lw, 56 * z, 14 * z, fond, bord, 1.2f * z)
        }
        ligne(t("esp.rg.ile"), y, PANNEAU, BORD)
        tl.texte(t("esp.rg.ile"), x + 16 * z, y + 28 * z, 14.5f * z, TEXTE, true)
        tl.texte(t("esp.rg.toujours"), x + lw - 14 * z, y + 28 * z, 11.5f * z, PALE, false, 'd')
        y += 66 * z
        val g = m.glisse
        for ((i, b) in m.bandes.withIndex()) {
            Z.add(Zone(x, y, lw, 56 * z, "rg:place:$i"))
            if (g?.first == b.id) { tl.rrect(x, y, lw, 56 * z, 14 * z, null, a(JAUNE, 120), 1.2f * z); y += 66 * z; continue }
            bandeRang(tl, Z, b, x, y, lw, z, false)
            y += 66 * z
        }
        if (g != null) m.bandes.firstOrNull { it.id == g.first }?.let { b ->
            tl.rrect(x + 10 * z, g.second - 22 * z, lw, 56 * z, 14 * z, 0x8C000000.toInt(), null, 0f)
            bandeRang(tl, mutableListOf(), b, x + 6 * z, g.second - 28 * z, lw, z, true)
        }
        // les onglets
        tl.texte(t("esp.rg.onglets").uppercase(), 20 * z, y + 6 * z, 11 * z, DOUX, true)
        y += 18 * z
        var ox = x
        for (o in m.ordreOnglets.filter { it in m.onglets }) {
            val lib = "≡ " + t("esp.onglet.$o")
            val ow = tl.mesure(lib, 13 * z) + 22 * z
            tl.rrect(ox, y, ow, 32 * z, 10 * z, PANNEAU, BORD_FORT, 1f * z)
            tl.texte(lib, ox + 11 * z, y + 16 * z, 13 * z, TEXTE)
            Z.add(Zone(ox, y, ow, 32 * z, "rg:onglet:$o"))
            ox += ow + 6 * z
        }
        y += 46 * z
        if (m.caches.isNotEmpty()) {
            tl.texte(t("esp.rg.cachees").uppercase(), 20 * z, y, 11 * z, DOUX, true)
            y += 12 * z
            var cx = x
            for (c in m.caches) {
                val lib = "+ " + t(if (c == "creature") "esp.dalle.direct" else "esp.dalle.deploie")
                val cw = tl.mesure(lib, 12.5f * z) + 24 * z
                bouton(tl, Z, cx, y, cw, lib, "rg:remettre:$c", z, VERT, a(VERT, 22), a(VERT, 120))
                cx += cw + 8 * z
            }
            y += 50 * z
        }
        tl.texte(t("app.opt.dispo").uppercase(), 20 * z, y, 11 * z, DOUX, true)
        y += 12 * z
        val noms = listOf("classique", "terminal_geant", "creature_centre") + (if (m.mienne) listOf("mienne") else emptyList())
        val pw = (lw - 6 * z * (noms.size - 1)) / noms.size
        for ((i, n) in noms.withIndex()) {
            val sel = n == m.dispo
            bouton(tl, Z, x + i * (pw + 6 * z), y, pw, t("app.dispo.$n"), "rg:dispo:$n", z, if (sel) JAUNE else TEXTE,
                if (sel) a(JAUNE, 30) else null, if (sel) a(JAUNE, 200) else null, sel)
        }
        y += 50 * z
        val bw = (lw - 8 * z) / 2
        bouton(tl, Z, x, y, bw, t("esp.rg.origine"), "rg:origine", z)
        bouton(tl, Z, x + bw + 8 * z, y, bw, t("esp.rg.fini"), "rg:fini", z, VERT, a(VERT, 40), a(VERT, 160), true)
        y += 44 * z
        bouton(tl, Z, x, y, lw, t("esp.rg.mienne"), "rg:mienne", z)
    }

    private fun bandeRang(tl: Toile, Z: MutableList<Zone>, b: Apparence.Bande, x: Float, y: Float, lw: Float, z: Float, tenue: Boolean) {
        tl.rrect(x, y, lw, 56 * z, 14 * z, if (tenue) PANNEAU2 else PANNEAU, if (tenue) a(JAUNE, 220) else BORD, (if (tenue) 1.6f else 1f) * z)
        tl.texte("≡", x + 20 * z, y + 28 * z, 20 * z, if (tenue) JAUNE else DOUX, true, 'c')
        Z.add(Zone(x, y, 44 * z, 56 * z, "rg:tenir:" + b.id))
        tl.texte(t(if (b.id == "creature") "esp.dalle.direct" else "esp.dalle.deploie"), x + 40 * z, y + 19 * z, 14.5f * z, TEXTE, true)
        tl.texte(t("esp.rg.taille"), x + 40 * z, y + 40 * z, 11 * z, PALE)
        val sx = x + 92 * z
        tl.rrect(sx, y + 29 * z, 108 * z, 24 * z, 8 * z, 0x08FFFFFF, BORD_FORT, 1f * z)
        for ((i, tt) in listOf("P", "M", "G").withIndex()) {
            val on = tt == b.taille
            val cx = sx + i * 36 * z
            if (on) tl.rrect(cx + 2 * z, y + 31 * z, 32 * z, 20 * z, 7 * z, a(JAUNE, 50), a(JAUNE, 200), 1f * z)
            tl.texte(tt, cx + 18 * z, y + 41 * z, 12 * z, if (on) JAUNE else DOUX, on, 'c')
            Z.add(Zone(cx, y + 26 * z, 36 * z, 30 * z, "rg:taille:${b.id}:$tt"))
        }
        croix(tl, Z, x + lw - 26 * z, y + 28 * z, "rg:cacher:" + b.id, z)
    }

    // ------------------------------------------------------------ les options (téléphone)
    /** La vignette d'un thème : un petit téléphone (île, carte, blocs, terminal) dans ses couleurs. */
    fun vignette(tl0: Toile, cle: String, x: Float, y: Float, w: Float, h: Float, z: Float) {
        val th = Apparence.Theme(cle)
        val tl = if (th.sombre) tl0 else ToileTheme(tl0, th)
        tl.rrect(x, y, w, h, 8 * z, FOND, BORD_FORT, 1f * z)
        tl.rrect(x + 4 * z, y + 4 * z, w - 8 * z, h * 0.12f, 6 * z, PANNEAU, BORD, 1f * z)
        tl.rrect(x + 4 * z, y + 8 * z + h * 0.12f, w - 8 * z, h * 0.3f, 6 * z, PANNEAU, BORD, 1f * z)
        for ((i, c) in listOf(0xFFFFA85C.toInt(), ROSE, JAUNE, VERT).withIndex())
            tl.rrect(x + w * 0.45f, y + 14 * z + h * 0.12f + i * 7 * z, w * 0.4f, 3 * z, 1f, c, null, 0f)
        tl.rrect(x + 4 * z, y + h * 0.46f, w - 8 * z, h * 0.18f, 5 * z, PANNEAU, BORD, 1f * z)
        var bx = x + 7 * z
        for ((c, lw) in listOf(VERT to 9, CYAN to 14, VIOLET to 4, VERT to 10)) {
            tl.rrect(bx, y + h * 0.46f + 3 * z, lw * z, h * 0.18f - 6 * z, 2 * z, a(c, 50), c, 0.8f * z); bx += (lw + 3) * z
        }
        tl.rrect(x + 4 * z, y + h * 0.66f, w - 8 * z, h * 0.34f - 4 * z, 5 * z, 0xFF0A0C11.toInt(), BORD, 1f * z)
        for (i in 0 until 2) tl.rrect(x + 9 * z, y + h * 0.66f + 5 * z + i * 6 * z, w * (0.6f - 0.15f * i), 2.5f * z, 1f, if (i == 1) VERT else TEXTE, null, 0f)
    }

    fun options(tl: Toile, tl0: Toile, Z: MutableList<Zone>, m: Modele, w: Float, h: Float, z: Float) {
        val x = 12 * z; val lw = w - 24 * z
        tl.texte("⚙ " + t("app.options.titre"), 20 * z, 26 * z, 21 * z, TEXTE, true)
        tl.texte("✕", w - 24 * z, 26 * z, 18 * z, DOUX, false, 'd')
        Z.add(Zone(w - 64 * z, 0f, 64 * z, 52 * z, "opt:fermer"))
        var y = 60 * z
        tl.texte(t("app.opt.apparence").uppercase(), 20 * z, y, 11.5f * z, DOUX, true)
        y += 12 * z
        tl.rrect(x, y, lw, 236 * z, 16 * z, PANNEAU, BORD, 1f * z)
        tl.texte(t("app.opt.theme"), x + 14 * z, y + 22 * z, 15 * z, TEXTE, true)
        tl.texte(t("app.theme." + (m.theme?.cle ?: "sombre")), x + lw - 14 * z, y + 22 * z, 13.5f * z, DOUX, false, 'd')
        val ordre = Apparence.ordre()
        val vw = (lw - 28 * z - 4 * 8 * z) / 5
        for ((i, cle) in ordre.withIndex()) {
            val col = i % 5; val lig = i / 5
            val vx = x + 14 * z + col * (vw + 8 * z); val vy = y + 40 * z + lig * 98 * z
            vignette(tl0, cle, vx, vy, vw, 70 * z, z)
            val sel = cle == (m.theme?.cle ?: "sombre")
            tl.rrect(vx - 3 * z, vy - 3 * z, vw + 6 * z, 76 * z, 10 * z, null, if (sel) a(JAUNE, 230) else BORD_FORT, (if (sel) 2f else 1f) * z)
            tl.texte(court(tl, t("app.theme.$cle").substringBefore(" ("), vw + 6 * z, 10.5f * z), vx + vw / 2, vy + 84 * z, 10.5f * z,
                if (sel) JAUNE else DOUX, sel, 'c')
            Z.add(Zone(vx - 3 * z, vy - 3 * z, vw + 6 * z, 94 * z, "opt:theme:$cle"))
        }
        y += 248 * z
        tl.texte(t("app.opt.dispo").uppercase(), 20 * z, y, 11.5f * z, DOUX, true)
        y += 12 * z
        val noms = listOf("classique", "terminal_geant", "creature_centre") + (if (m.mienne) listOf("mienne") else emptyList())
        val pw = (lw - 6 * z * (noms.size - 1)) / noms.size
        for ((i, n) in noms.withIndex()) {
            val sel = n == m.dispo
            bouton(tl, Z, x + i * (pw + 6 * z), y, pw, t("app.dispo.$n"), "opt:dispo:$n", z, if (sel) JAUNE else TEXTE,
                if (sel) a(JAUNE, 30) else null, if (sel) a(JAUNE, 200) else null, sel)
        }
        y += 46 * z
        bouton(tl, Z, x, y, lw, "✎ " + t("esp.rg.titre"), "opt:ranger", z, VERT, a(VERT, 26), a(VERT, 140))
        y += 56 * z
        tl.texte(t("app.opt.grands").uppercase(), 20 * z, y, 11.5f * z, JAUNE, true)
        y += 12 * z
        tl.rrect(x, y, lw, 100 * z, 16 * z, a(JAUNE, 12), a(JAUNE, 120), 1f * z)
        tl.texte(t("app.opt.tout"), x + 14 * z, y + 24 * z, 15 * z, TEXTE, true)
        val on = m.tout
        tl.rrect(x + lw - 58 * z, y + 13 * z, 44 * z, 22 * z, 11 * z, if (on) a(JAUNE, 70) else 0x14FFFFFF, if (on) a(JAUNE, 200) else BORD_FORT, 1f * z)
        tl.ellipse(x + lw - (if (on) 25 else 47) * z, y + 24 * z, 8 * z, 8 * z, if (on) JAUNE else DOUX)
        Z.add(Zone(x, y, lw, 46 * z, "opt:tout"))
        var yy = y + 50 * z
        for (l in couper(tl, t("app.opt.tout.aide"), lw - 28 * z, 12 * z).take(3)) { tl.texte(l, x + 14 * z, yy, 12 * z, DOUX); yy += 16 * z }
    }
}

/** Le pinceau d'un thème : chaque couleur (écrite pour le thème sombre) passe par Apparence.Theme.couleur ;
 *  les images de la créature ne changent pas ; la carte du monde demande sa version teintée (« monde:matrix »). */
class ToileTheme(private val t: Toile, private val th: Apparence.Theme) : Toile {
    private fun c(x: Int) = th.couleur(x)
    private fun n(x: Int?) = x?.let { th.couleur(it) }
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) = t.rect(x, y, w, h, c(c))
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) = t.rrect(x, y, w, h, r, n(fond), n(bord), ep)
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) = t.ellipse(cx, cy, rx, ry, c(c))
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) = t.cercle(cx, cy, r, c(c), ep)
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) =
        t.ligne(x1, y1, x2, y2, c(c), ep, plein, vide, dec)
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) = t.poly(xs, ys, c(c))
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) =
        t.texte(s, x, y, taille, c(c), gras, ancre, mono)
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = t.mesure(s, taille, gras, mono)
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) = t.lueur(cx, cy, r, c(c))
    override fun cadre(c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) =
        t.cadre(c, ax, ay, e, miroir, lisse, sx, sy, rot, alpha)
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) =
        t.photo(if (th.carte != null && ':' !in nom) "$nom:${th.cle}" else nom, x, y, w, h, r)
}
