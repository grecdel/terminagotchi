package fr.terminagotchi

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.os.Bundle
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import java.io.File
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.sqrt

/** Le Doom-like : un moteur « raycasting » (comme Doom/Wolfenstein) qui lit TON niveau et TES réglages. */
class DoomActivity : Activity() {
    private lateinit var vue: DoomVue

    @SuppressLint("ClickableViewAccessibility")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val jeu = Jeu(this)
        val d = Doom.preparer(jeu)
        vue = DoomVue(this, jeu, File(d, "carte.txt").readText(), Doom.lireReglages(File(d, "reglages.txt").readText()))

        val dp = resources.displayMetrics.density
        val racine = LinearLayout(this)
        racine.orientation = LinearLayout.VERTICAL
        racine.setBackgroundColor(0xFF0B0B12.toInt())
        racine.addView(vue, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))

        val commandes = LinearLayout(this)
        commandes.orientation = LinearLayout.HORIZONTAL
        commandes.gravity = Gravity.CENTER
        commandes.setPadding(0, (8 * dp).toInt(), 0, (16 * dp).toInt())
        fun bouton(texte: String, action: (Boolean) -> Unit): TextView {
            val b = TextView(this)
            b.text = texte
            b.textSize = 24f
            b.gravity = Gravity.CENTER
            b.setTextColor(Color.WHITE)
            b.setBackgroundResource(R.drawable.touche)
            val lp = LinearLayout.LayoutParams((64 * dp).toInt(), (64 * dp).toInt())
            lp.marginStart = (5 * dp).toInt()
            lp.marginEnd = (5 * dp).toInt()
            b.layoutParams = lp
            b.setOnTouchListener { _, e ->
                when (e.actionMasked) {
                    MotionEvent.ACTION_DOWN -> action(true)
                    MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> action(false)
                }
                true
            }
            return b
        }
        commandes.addView(bouton("⟲") { vue.gauche = it })
        commandes.addView(bouton("▲") { vue.avant = it })
        commandes.addView(bouton("▼") { vue.arriere = it })
        commandes.addView(bouton("⟳") { vue.droite = it })
        commandes.addView(bouton("🔥") { if (it) vue.tirer() })
        racine.addView(commandes)

        val cadre = FrameLayout(this)
        cadre.addView(racine)
        setContentView(cadre)
    }
}

class DoomVue(ctx: Context, private val jeu: Jeu, carteTexte: String, reglages: Map<String, String>) : View(ctx) {
    private class Ennemi(var x: Double, var y: Double, val couleur: Int, var pv: Int = 2)

    private val L = 200          // résolution interne (pixels)
    private val H = 125
    private val tampon = Bitmap.createBitmap(L, H, Bitmap.Config.ARGB_8888)
    private val pixels = IntArray(L * H)
    private val zbuf = DoubleArray(L)
    private val pinceau = Paint().apply { isFilterBitmap = false }
    private val texte = Paint().apply { color = Color.WHITE; textSize = 34f; isAntiAlias = true }
    private val portrait = Sprites.bitmap(jeu, 4)

    private val carte: List<String>
    private var px = 1.5
    private var py = 1.5
    private var dir = 0.0
    private var sortieX = -1
    private var sortieY = -1
    private val ennemis = mutableListOf<Ennemi>()

    private val vitesse = (reglages["vitesse"]?.toDoubleOrNull() ?: 4.0).coerceIn(1.0, 10.0)
    private val vitesseEnnemis = (reglages["vitesse_ennemis"]?.toDoubleOrNull() ?: 2.0).coerceIn(0.0, 10.0)
    private var vie = (reglages["vie"]?.toIntOrNull() ?: 5).coerceIn(1, 99)
    private val ciel = Doom.couleur(reglages["couleur_ciel"], 0xFF3A2A6A.toInt())
    private val sol = Doom.couleur(reglages["couleur_sol"], 0xFF505058.toInt())
    private val murs = Doom.couleur(reglages["couleur_murs"], 0xFF8A4030.toInt())

    var gauche = false
    var droite = false
    var avant = false
    var arriere = false
    private var flash = 0
    private var touche = 0
    private var message = "Trouve la sortie verte !"
    private var messageFin = 0L
    private var fini = false
    private var tues = 0
    private var dernier = System.nanoTime()
    private var dernierCoup = 0L

    init {
        val lignes = carteTexte.lines().filter { it.isNotBlank() }
        carte = if (lignes.isEmpty()) listOf("###", "#C#", "###") else lignes
        // couleurs des ennemis : celles des bestioles capturées, sinon des couleurs par défaut
        val col = Explo.collection(jeu)
        val couleursBestioles = Explo.ESPECES.filter { col.optInt(it.nom) > 0 }.map { Sprites.x256(it.couleur) }
            .ifEmpty { listOf(0xFFFF5FAF.toInt(), 0xFF5FD7FF.toInt(), 0xFFFFD75F.toInt()) }
        for ((y, l) in carte.withIndex()) for ((x, c) in l.withIndex()) {
            when (c) {
                'C', 'c' -> { px = x + 0.5; py = y + 0.5 }
                'B', 'b' -> ennemis.add(Ennemi(x + 0.5, y + 0.5, couleursBestioles.random()))
                'X', 'x' -> { sortieX = x; sortieY = y }
            }
        }
        setBackgroundColor(Color.BLACK)
    }

    private fun mur(x: Int, y: Int): Boolean {
        if (y < 0 || y >= carte.size) return true
        val l = carte[y]
        if (x < 0 || x >= l.length) return true
        return l[x] == '#' || l[x] in '1'..'4'
    }

    private fun couleurMur(x: Int, y: Int): Int {
        val c = carte.getOrNull(y)?.getOrNull(x) ?: '#'
        return when (c) {
            '1' -> 0xFF3070C0.toInt()
            '2' -> 0xFF30A050.toInt()
            '3' -> 0xFFC0A030.toInt()
            '4' -> 0xFFA040A0.toInt()
            else -> murs
        }
    }

    private fun assombrir(c: Int, f: Double): Int {
        val k = f.coerceIn(0.15, 1.0)
        return Color.rgb((Color.red(c) * k).toInt(), (Color.green(c) * k).toInt(), (Color.blue(c) * k).toInt())
    }

    fun tirer() {
        if (fini) {
            (context as Activity).finish()
            return
        }
        flash = 3
        var cible: Ennemi? = null
        var meilleure = 99.0
        for (e in ennemis) {
            if (e.pv <= 0) continue
            val dx = e.x - px
            val dy = e.y - py
            val dist = hypot(dx, dy)
            var a = atan2(dy, dx) - dir
            while (a > Math.PI) a -= 2 * Math.PI
            while (a < -Math.PI) a += 2 * Math.PI
            if (abs(a) < 0.12 + 0.3 / dist && dist < 12 && dist < zbuf[L / 2] + 0.5 && dist < meilleure) {
                meilleure = dist
                cible = e
            }
        }
        if (cible != null) {
            cible.pv--
            if (cible.pv <= 0) {
                tues++
                dire("Bestiole neutralisée ! ($tues)")
            }
        }
    }

    private fun dire(m: String) {
        message = m
        messageFin = System.currentTimeMillis() + 2500
    }

    private fun maj(dt: Double) {
        if (fini) return
        val rot = 2.4 * dt
        if (gauche) dir -= rot
        if (droite) dir += rot
        val sens = (if (avant) 1.0 else 0.0) - (if (arriere) 1.0 else 0.0)
        val v = vitesse * 0.6 * dt * sens
        if (avant || arriere) {
            val nx = px + cos(dir) * v
            val ny = py + sin(dir) * v
            if (!mur(floor(nx).toInt(), floor(py).toInt())) px = nx
            if (!mur(floor(px).toInt(), floor(ny).toInt())) py = ny
        }
        val maintenant = System.currentTimeMillis()
        for (e in ennemis) {
            if (e.pv <= 0) continue
            val dx = px - e.x
            val dy = py - e.y
            val dist = hypot(dx, dy)
            if (dist < 8 && dist > 0.4) {
                val s = vitesseEnnemis * 0.35 * dt / dist
                val nx = e.x + dx * s
                val ny = e.y + dy * s
                if (!mur(floor(nx).toInt(), floor(e.y).toInt())) e.x = nx
                if (!mur(floor(e.x).toInt(), floor(ny).toInt())) e.y = ny
            }
            if (dist < 0.6 && maintenant - dernierCoup > 1000) {
                dernierCoup = maintenant
                vie--
                touche = 6
                dire("Aïe ! Il reste $vie vie(s)")
                if (vie <= 0) terminer(false)
            }
        }
        if (floor(px).toInt() == sortieX && floor(py).toInt() == sortieY) terminer(true)
    }

    private fun terminer(victoire: Boolean) {
        fini = true
        val j = Jeu(context)
        if (victoire) {
            val gain = 30 + tues * 5
            j.ajouterXp(gain)
            val m = j.module("doom")
            m.put("victoires", m.optInt("victoires") + 1)
            j.log("🎮 Niveau terminé ! +$gain XP")
            message = "🏆 VICTOIRE ! +$gain XP · touche 🔥 pour revenir"
        } else {
            j.log("🎮 Défaite au Doom…")
            message = "💀 Perdu… règle la vie dans reglages.txt ! (🔥 pour revenir)"
        }
        messageFin = Long.MAX_VALUE
        j.sauver()
    }

    private fun rendre() {
        // ciel et sol
        for (y in 0 until H) {
            val c = if (y < H / 2) assombrir(ciel, 0.6 + 0.4 * y / (H / 2.0))
            else assombrir(sol, 0.35 + 0.65 * (y - H / 2) / (H / 2.0))
            for (x in 0 until L) pixels[y * L + x] = c
        }
        val fov = 0.66
        val dX = cos(dir)
        val dY = sin(dir)
        val planX = -dY * fov
        val planY = dX * fov
        for (x in 0 until L) {
            val cam = 2.0 * x / L - 1
            val rx = dX + planX * cam
            val ry = dY + planY * cam
            var mx = floor(px).toInt()
            var my = floor(py).toInt()
            val ddx = if (rx == 0.0) 1e30 else abs(1 / rx)
            val ddy = if (ry == 0.0) 1e30 else abs(1 / ry)
            val sx: Int
            val sy: Int
            var sdx: Double
            var sdy: Double
            if (rx < 0) { sx = -1; sdx = (px - mx) * ddx } else { sx = 1; sdx = (mx + 1.0 - px) * ddx }
            if (ry < 0) { sy = -1; sdy = (py - my) * ddy } else { sy = 1; sdy = (my + 1.0 - py) * ddy }
            var cote = 0
            var n = 0
            while (n < 64) {
                if (sdx < sdy) { sdx += ddx; mx += sx; cote = 0 } else { sdy += ddy; my += sy; cote = 1 }
                if (mur(mx, my)) break
                n++
            }
            val dist = if (cote == 0) sdx - ddx else sdy - ddy
            zbuf[x] = dist
            val h = (H / dist.coerceAtLeast(0.05)).toInt()
            val y0 = (H / 2 - h / 2).coerceAtLeast(0)
            val y1 = (H / 2 + h / 2).coerceAtMost(H - 1)
            var c = assombrir(couleurMur(mx, my), 1.2 / (1 + dist * 0.25))
            if (cote == 1) c = assombrir(c, 0.75)
            val joint = assombrir(c, 0.7)
            val quart = (h / 4).coerceAtLeast(1)
            for (y in y0..y1) {
                // petites briques : une ligne plus sombre tous les quarts de mur
                pixels[y * L + x] = if (h > 8 && (y - (H / 2 - h / 2)) % quart == 0) joint else c
            }
        }
        // sprites : sortie + ennemis, du plus loin au plus proche
        val sprites = mutableListOf<Triple<Double, Double, Int>>()
        if (sortieX >= 0) sprites.add(Triple(sortieX + 0.5, sortieY + 0.5, -1))
        ennemis.filter { it.pv > 0 }.forEach { sprites.add(Triple(it.x, it.y, it.couleur)) }
        sprites.sortByDescending { (it.first - px) * (it.first - px) + (it.second - py) * (it.second - py) }
        val inv = 1.0 / (planX * dY - dX * planY)
        for ((sxp, syp, coul) in sprites) {
            val spx = sxp - px
            val spy = syp - py
            val tx = inv * (dY * spx - dX * spy)
            val ty = inv * (-planY * spx + planX * spy)
            if (ty <= 0.1) continue
            val ecranX = ((L / 2) * (1 + tx / ty)).toInt()
            val taille = (H / ty).toInt()
            val haut = if (coul == -1) taille else (taille * 0.7).toInt()
            val y0 = H / 2 + taille / 2 - haut
            for (sx in ecranX - haut / 2 until ecranX + haut / 2) {
                if (sx < 0 || sx >= L || ty >= zbuf[sx]) continue
                val u = (sx - (ecranX - haut / 2)).toDouble() / haut
                for (sy in y0 until y0 + haut) {
                    if (sy < 0 || sy >= H) continue
                    val v = (sy - y0).toDouble() / haut
                    val c = if (coul == -1) {
                        // portail de sortie : anneau vert lumineux
                        val r = sqrt((u - 0.5) * (u - 0.5) + (v - 0.5) * (v - 0.5))
                        if (r < 0.48 && r > 0.25) 0xFF5FFF87.toInt() else if (r <= 0.25) 0xFF1F6F3F.toInt() else 0
                    } else {
                        // bestiole : corps rond, deux yeux
                        val r = sqrt((u - 0.5) * (u - 0.5) + (v - 0.55) * (v - 0.55) * 1.3)
                        when {
                            r > 0.47 -> 0
                            (abs(u - 0.33) < 0.07 || abs(u - 0.67) < 0.07) && abs(v - 0.42) < 0.08 -> Color.BLACK
                            else -> coul
                        }
                    }
                    if (c != 0) pixels[sy * L + sx] = assombrir(c, 1.3 / (1 + ty * 0.2))
                }
            }
        }
        // viseur et tir
        val cx = L / 2
        val cy = H / 2
        for (k in -3..3) {
            if (k != 0) {
                pixels[cy * L + cx + k] = Color.WHITE
                pixels[(cy + k) * L + cx] = Color.WHITE
            }
        }
        if (flash > 0) {
            flash--
            for (y in H - 22 until H) for (x in cx - 10..cx + 10) pixels[y * L + x] = 0xFFFFD75F.toInt()
        }
        if (touche > 0) {
            touche--
            for (i in pixels.indices) pixels[i] = Color.rgb((Color.red(pixels[i]) + 80).coerceAtMost(255),
                Color.green(pixels[i]) / 2, Color.blue(pixels[i]) / 2)
        }
        tampon.setPixels(pixels, 0, L, 0, 0, L, H)
    }

    override fun onDraw(canvas: Canvas) {
        val t = System.nanoTime()
        val dt = ((t - dernier) / 1e9).coerceIn(0.0, 0.1)
        dernier = t
        maj(dt)
        rendre()
        val w = width
        val h = (w * H / L).coerceAtMost(height)
        val haut = (height - h) / 2
        canvas.drawBitmap(tampon, Rect(0, 0, L, H), Rect(0, haut, w, haut + h), pinceau)
        // HUD : portrait de la créature, vies, bestioles restantes
        val p = (w / 6)
        canvas.drawBitmap(portrait, Rect(0, 0, portrait.width, portrait.height), Rect(8, haut + h - p, 8 + p, haut + h), pinceau)
        val restants = ennemis.count { it.pv > 0 }
        canvas.drawText("❤ $vie   👾 $restants", (p + 20).toFloat(), (haut + h - 20).toFloat(), texte)
        if (System.currentTimeMillis() < messageFin || fini) {
            canvas.drawText(message, 20f, (haut + 50).toFloat(), texte)
        }
        postInvalidateOnAnimation()
    }
}
