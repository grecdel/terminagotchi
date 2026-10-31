package fr.terminagotchi

import android.app.Activity
import android.app.AlertDialog
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.provider.Settings
import android.view.Gravity
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.FrameLayout
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * La bulle : la créature se promène par-dessus les autres applications (permission « Afficher par-dessus les autres
 * applications », demandée avec une explication), et l'île en haut de l'écran. Comme `tg bureau` sur PC.
 *
 *   appui           le petit menu rond (Jouer, Terminal, S'occuper, Carte, Équipe, Réglages, Ranger)
 *   double appui    un cœur ;   triple appui : une petite phrase
 *   appui long      la déplacer (elle retombe au bas de l'écran) ;   glisser vers le bas : la ranger dans un coin
 *   l'île           une pilule (faim, XP) ; un appui l'agrandit (elle parle, boutons, mini-terminal) ; elle s'ouvre
 *                   toute seule quelques secondes sur un événement du jeu (monstre, étape réussie, faim)
 *
 * Vie privée : la bulle ne voit RIEN des autres applications (ni l'écran, ni ce qui est tapé, ni l'appli ouverte) ;
 * elle relit seulement la sauvegarde du jeu (sans jamais l'écrire) et le niveau de la batterie.
 * Batterie : tout s'arrête quand l'écran est éteint (aucune image calculée), et reprend à l'allumage.
 */
class BulleService : Service() {
    companion object {
        const val CANAL = "bulle"
        const val ID = 4245
        const val ARRET = "fr.terminagotchi.bulle.ARRET"
        const val PREFS = "bulle"
        @Volatile var enMarche = false
        private const val PAS = 66L                      // ~15 images par seconde
        private const val RELIRE = 3000L                 // relire la sauvegarde toutes les 3 s
    }

    private lateinit var wm: WindowManager
    private lateinit var jeu: Jeu
    private val handler = Handler(Looper.getMainLooper())
    private var dens = 1f
    private var ecranL = 0
    private var ecranH = 0
    private var album: Poses.Album? = null
    private var cleAlbum = ""
    private lateinit var creature: BureauVie.Creature
    private val gestes = BureauVie.Gestes()
    private val ile = BureauVie.Ile()
    private var resume: BureauVie.Resume? = null
    private var dernierTotal = -1
    private var derniereCommande = SystemClock.elapsedRealtime()
    private var batterie: Int? = null
    private var enCharge = true
    private var actif = true
    private var tPrec = SystemClock.elapsedRealtime()
    private var tRelu = 0L
    private var phrase: Pair<String, Long>? = null
    private val flottants = mutableListOf<Triple<String, Long, Int>>()

    private var vueCreature: CreatureVue? = null
    private var pCreature: WindowManager.LayoutParams? = null
    private var vueMenu: MenuVue? = null
    private var vueIle: IleVue? = null
    private var pIle: WindowManager.LayoutParams? = null
    private val bitmaps = HashMap<String, Bitmap>()

    private val ecran = object : BroadcastReceiver() {
        override fun onReceive(c: Context, i: Intent) {
            when (i.action) {
                Intent.ACTION_SCREEN_OFF -> pause()
                Intent.ACTION_SCREEN_ON, Intent.ACTION_USER_PRESENT -> reprise()
            }
        }
    }

    private fun prefs() = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private fun dp(v: Float) = v * dens

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        premierPlan()                                   // toujours d'abord (Android l'exige dans les 5 secondes)
        if (!Settings.canDrawOverlays(this)) { stopSelf(); return }
        enMarche = true
        wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        dens = resources.displayMetrics.density
        ecranL = resources.displayMetrics.widthPixels
        ecranH = resources.displayMetrics.heightPixels
        jeu = Jeu(this)
        Poses.charger(this)
        val p = prefs()
        creature = BureauVie.Creature(ecranL.toFloat(), sommeil = 1200.0)
        reglerCreature()
        creature.bord = dp(36f)
        ile.auto = p.getBoolean("ile_auto", true)
        relire()
        ajouterFenetres()
        val f = IntentFilter(Intent.ACTION_SCREEN_OFF)
        f.addAction(Intent.ACTION_SCREEN_ON)
        f.addAction(Intent.ACTION_USER_PRESENT)
        registerReceiver(ecran, f)
        actif = (getSystemService(Context.POWER_SERVICE) as PowerManager).isInteractive
        if (actif) handler.post(boucle)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ARRET) { ranger(); return START_NOT_STICKY }
        return START_STICKY
    }

    override fun onDestroy() {
        enMarche = false
        handler.removeCallbacksAndMessages(null)
        try { unregisterReceiver(ecran) } catch (e: Exception) { }
        for (v in listOf(vueMenu, vueCreature, vueIle)) if (v != null) try { wm.removeView(v) } catch (e: Exception) { }
        vueMenu = null; vueCreature = null; vueIle = null
        super.onDestroy()
    }

    /** « La ranger » : la bulle s'arrête et ne revient pas toute seule. */
    fun ranger() {
        prefs().edit().putBoolean("voulue", false).apply()
        stopSelf()
    }

    // ------------------------------------------------------------ la notification (service au premier plan)
    private fun premierPlan() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CANAL) == null) {
            val c = NotificationChannel(CANAL, t("bulle.canal"), NotificationManager.IMPORTANCE_MIN)
            c.setShowBadge(false)
            c.enableVibration(false)
            nm.createNotificationChannel(c)
        }
        val ouvrir = PendingIntent.getActivity(this, 31,
            Intent(this, TerminalActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val arret = PendingIntent.getService(this, 32, Intent(this, BulleService::class.java).setAction(ARRET),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val nom = try { Jeu(this).nom } catch (e: Exception) { "" }
        val n = Notification.Builder(this, CANAL)
            .setSmallIcon(R.drawable.ic_notif)
            .setContentTitle(t("bulle.notif", "nom" to nom))
            .setContentText(t("bulle.notif.texte"))
            .setContentIntent(ouvrir)
            .addAction(0, t("bur.menu.ranger"), arret)
            .setOngoing(true)
            .setShowWhen(false)
            .build()
        if (Build.VERSION.SDK_INT >= 34) startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        else startForeground(ID, n)
    }

    // ------------------------------------------------------------ écran éteint : tout s'arrête
    private fun pause() {
        actif = false
        handler.removeCallbacks(boucle)
    }

    private fun reprise() {
        if (actif) return
        actif = true
        tPrec = SystemClock.elapsedRealtime()
        handler.removeCallbacks(boucle)
        handler.post(boucle)
    }

    private val boucle = object : Runnable {
        override fun run() {
            if (!actif) return
            try { image() } catch (e: Exception) { android.util.Log.w("TG", "bulle : $e") }
            handler.postDelayed(this, PAS)
        }
    }

    // ------------------------------------------------------------ le jeu (lu, jamais écrit)
    private fun reglerCreature() {
        val p = prefs()
        creature.vitesse = dp(BureauVie.VITESSES[p.getString("vitesse", "normale")] ?: 32f)
        creature.surPlace = p.getBoolean("sur_place", false)
    }

    private fun taille(): Float = dp(BureauVie.TAILLES[prefs().getString("taille", "moyenne")] ?: 76f)

    private fun relire() {
        try { jeu.recharger() } catch (e: Exception) { return }
        if (jeu.total != dernierTotal) {
            if (dernierTotal >= 0 && jeu.total > dernierTotal) {
                creature.reagir("mange")
                flottants.add(Triple(Langue.liste("bur.miam").randomOrNull() ?: "+", SystemClock.elapsedRealtime(), 0xFFFFD54F.toInt()))
            }
            dernierTotal = jeu.total
            derniereCommande = SystemClock.elapsedRealtime()
        }
        val r = BureauVie.Resume(jeu.total, jeu.lecon, jeu.etape, jeu.faim, jeu.module("dressage").has("en_cours"))
        for (cle in BureauVie.evenements(resume, r)) {
            if (prefs().getBoolean("ile", true) && ile.annoncer(t(cle)) && creature.etat != "dort") creature.parler(t(cle))
            break
        }
        resume = r
        try {
            val b = registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            if (b != null) {
                val niv = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1); val ech = b.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
                batterie = if (niv >= 0 && ech > 0) niv * 100 / ech else null
                enCharge = b.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0
            }
        } catch (e: Exception) { }
        val choix = prefs().getString("espece", "") ?: ""
        val cle = "${jeu.partie}|${jeu.extra.optString("espece_compagnon")}|${jeu.stade}|${jeu.shiny}|$choix"
        if (cle != cleAlbum || album == null) {
            cleAlbum = cle
            album = albumChoisi(choix) ?: try { Poses.album(jeu) } catch (e: Exception) { album }
            creature.bouche = album?.bouche ?: BureauVie.BOUCHE_DEFAUT
            bitmaps.clear()
            vueCreature?.let { majFenetreCreature() }
        }
    }

    private fun albumChoisi(id: String): Poses.Album? {
        if (id.isEmpty()) return null
        val caps = Explo.captures(jeu)
        for (i in 0 until caps.length()) {
            val c = caps.getJSONObject(i)
            if (c.optString("id") == id) {
                val e = Bestiaire.espece(c.optString("espece")) ?: return null
                return try { Poses.albumEspece(e, c.optString("stade", "bebe"), c.optBoolean("shiny")) } catch (x: Exception) { null }
            }
        }
        return null
    }

    // ------------------------------------------------------------ le temps
    private fun image() {
        val now = SystemClock.elapsedRealtime()
        val dt = (now - tPrec) / 1000.0
        tPrec = now
        if (now - tRelu > RELIRE) { tRelu = now; relire() }
        val inactif = (now - derniereCommande) / 1000.0
        creature.tick(dt, BureauVie.Signaux(inactif, batterie, enCharge))
        ile.tick(dt)
        gestes.tenir(now / 1000.0)
        gestes.attendre(now / 1000.0)?.let { geste(it) }
        flottants.removeAll { now - it.second > 1600 }
        placerCreature()
        vueCreature?.invalidate()
        vueMenu?.invalidate()
        vueIle?.let { majIle(); it.dessin.invalidate() }
    }

    // ------------------------------------------------------------ fenêtres
    private fun params(w: Int, h: Int, focus: Boolean = false): WindowManager.LayoutParams {
        var f = WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH
        if (!focus) f = f or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
        val p = WindowManager.LayoutParams(w, h, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY, f, PixelFormat.TRANSLUCENT)
        p.gravity = Gravity.TOP or Gravity.LEFT
        return p
    }

    private fun tailleFenetreCreature(): Pair<Int, Int> = (taille() * 3.2f).toInt() to (taille() * 2.7f).toInt()

    private fun ajouterFenetres() {
        val (w, h) = tailleFenetreCreature()
        val v = CreatureVue(this)
        val p = params(w, h)
        p.x = (creature.x - w / 2).toInt(); p.y = ecranH - h
        vueCreature = v; pCreature = p
        wm.addView(v, p)
        if (prefs().getBoolean("ile", true)) ajouterIle()
    }

    private fun majFenetreCreature() {
        val v = vueCreature ?: return
        val p = pCreature ?: return
        val (w, h) = tailleFenetreCreature()
        p.width = w; p.height = h
        try { wm.updateViewLayout(v, p) } catch (e: Exception) { }
    }

    private fun placerCreature() {
        val v = vueCreature ?: return
        val p = pCreature ?: return
        val nx = (creature.x - p.width / 2).toInt()
        val ny = (ecranH - p.height - creature.air).toInt()
        if (nx != p.x || ny != p.y) {
            p.x = nx; p.y = ny
            try { wm.updateViewLayout(v, p) } catch (e: Exception) { }
        }
    }

    private fun ajouterIle() {
        if (vueIle != null) return
        val v = IleVue(this)
        val p = params(dp(230f).toInt(), dp(44f).toInt())
        p.gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
        p.y = dp(6f).toInt()
        vueIle = v; pIle = p
        wm.addView(v, p)
    }

    private fun retirerIle() {
        vueIle?.let { try { wm.removeView(it) } catch (e: Exception) { } }
        vueIle = null; pIle = null
    }

    private var formeIle = ""

    private fun majIle() {
        val v = vueIle ?: return
        val p = pIle ?: return
        val forme = ile.etat
        if (forme == formeIle) return
        formeIle = forme
        when (forme) {
            "ouverte" -> { p.width = min(ecranL - dp(16f).toInt(), dp(560f).toInt()); p.height = dp(330f).toInt()
                p.flags = p.flags and WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE.inv() }
            "evenement" -> { p.width = min(ecranL - dp(16f).toInt(), dp(330f).toInt()); p.height = dp(46f).toInt()
                p.flags = p.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE }
            else -> { p.width = dp(230f).toInt(); p.height = dp(44f).toInt()
                p.flags = p.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE }
        }
        v.saisie.visibility = if (forme == "ouverte") View.VISIBLE else View.GONE
        try { wm.updateViewLayout(v, p) } catch (e: Exception) { }
    }

    private fun ouvrirMenu(panneau: Panneau? = null) {
        val m = vueMenu ?: MenuVue(this).also { nv ->
            val hz = min(ecranH, (taille() * 6.4f + dp(120f)).toInt())
            val p = params(ecranL, hz)
            p.y = ecranH - hz
            wm.addView(nv, p)
            vueMenu = nv
        }
        m.panneau = panneau
        m.invalidate()
    }

    private fun fermerMenu() {
        vueMenu?.let { try { wm.removeView(it) } catch (e: Exception) { } }
        vueMenu = null
    }

    // ------------------------------------------------------------ gestes et actions
    private fun geste(g: String) {
        when (g) {
            "appui" -> {
                if (creature.rangee) { creature.rangee = false; creature.reagir("etire"); return }
                if (vueMenu != null) fermerMenu() else { creature.reagir("sursaut"); ouvrirMenu() }
            }
            "double" -> { fermerMenu(); creature.reagir("coeur")
                flottants.add(Triple("♥", SystemClock.elapsedRealtime(), 0xFFFF5F6D.toInt())) }
            "triple" -> { fermerMenu(); dire(Langue.liste("bur.phrases").randomOrNull() ?: "") }
        }
    }

    /** Elle dit texte : une bulle, et sa bouche bouge au rythme des syllabes (assise). */
    private fun dire(texte: String, secondes: Double? = null) {
        val s = Vert.rendre(texte).toString()
        creature.changer("assis", BureauVie.dureeParole(s) + 0.8)
        creature.parler(s)
        phrase = s to SystemClock.elapsedRealtime() + ((secondes ?: maxOf(4.0, BureauVie.dureeParole(s) + 2.0)) * 1000).toLong()
    }

    private fun ouvrirJeu(commande: String? = null) {
        fermerMenu()
        val i = Intent(this, TerminalActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        if (commande != null) i.putExtra("tg_commande", commande)
        try { startActivity(i) } catch (e: Exception) { }
    }

    class Panneau(val titre: String, val lignes: List<Pair<String, String?>>)

    private fun action(a: String) {
        val p = prefs()
        fun oui(b: Boolean) = if (b) t("app.on") else t("app.off")
        when (a) {
            "jouer", "terminal" -> ouvrirJeu()
            "carte" -> ouvrirJeu("carte")
            "ranger" -> { fermerMenu(); ranger() }
            "soccuper" -> {
                val l = Envies.valeurs(jeu).map { (k, v) -> "${Envies.nom(k)}  " + "▰".repeat((v / 20).toInt().coerceIn(0, 5)) + "▱".repeat(5 - (v / 20).toInt().coerceIn(0, 5)) to null as String? }
                Envies.phrase(jeu)?.let { dire(it, 8.0) }
                ouvrirMenu(Panneau(t("bur.menu.soccuper"), l + ("♥ " + t("bur.caresser") to "caresser")))
            }
            "caresser" -> geste("double")
            "equipe" -> {
                val choix = p.getString("espece", "") ?: ""
                val l = mutableListOf<Pair<String, String?>>((if (choix.isEmpty()) "● " else "○ ") + jeu.nom to "equipe:")
                val caps = Explo.captures(jeu)
                for (i in maxOf(0, caps.length() - 6) until caps.length()) {
                    val c = caps.getJSONObject(i)
                    l.add((if (choix == c.optString("id")) "● " else "○ ") + c.optString("espece") to "equipe:" + c.optString("id"))
                }
                ouvrirMenu(Panneau(t("bur.equipe.titre"), l))
            }
            "reglages" -> {
                val l = listOf<Pair<String, String?>>(
                    t("bur.reg.taille", "v" to t("bur.reg.taille." + p.getString("taille", "moyenne"))) to "reg:taille",
                    t("bur.reg.vitesse", "v" to t("bur.reg.vitesse." + p.getString("vitesse", "normale"))) to "reg:vitesse",
                    t("bur.reg.sur_place", "v" to oui(p.getBoolean("sur_place", false))) to "reg:sur_place",
                    t("bur.reg.dormir") to "reg:dormir",
                    t("bur.reg.notifs", "v" to oui(NotifVie.voulue(this))) to "reg:notifs",
                    t("bur.reg.langue", "v" to Langue.courante) to "reg:langue",
                    t("bur.reg.ile", "v" to oui(p.getBoolean("ile", true))) to "reg:ile",
                    t("bur.reg.ile_auto", "v" to oui(p.getBoolean("ile_auto", true))) to "reg:ile_auto")
                ouvrirMenu(Panneau(t("bur.menu.reglages"), l))
            }
            else -> when {
                a.startsWith("equipe:") -> { p.edit().putString("espece", a.removePrefix("equipe:")).apply(); cleAlbum = ""; relire(); action("equipe") }
                a.startsWith("reg:") -> { regler(a.removePrefix("reg:")); if (a != "reg:dormir" && a != "reg:langue") action("reglages") }
            }
        }
    }

    private fun suivant(l: List<String>, v: String?): String = l[(l.indexOf(v) + 1).mod(l.size)]

    private fun regler(cle: String) {
        val p = prefs()
        val e = p.edit()
        when (cle) {
            "taille" -> e.putString("taille", suivant(BureauVie.TAILLES.keys.toList(), p.getString("taille", "moyenne")))
            "vitesse" -> e.putString("vitesse", suivant(BureauVie.VITESSES.keys.toList(), p.getString("vitesse", "normale")))
            "sur_place" -> e.putBoolean("sur_place", !p.getBoolean("sur_place", false))
            "ile" -> e.putBoolean("ile", !p.getBoolean("ile", true))
            "ile_auto" -> e.putBoolean("ile_auto", !p.getBoolean("ile_auto", true))
            "notifs" -> NotifVie.regler(this, !NotifVie.voulue(this))
            "dormir" -> { fermerMenu(); creature.dormir() }
            "langue" -> ouvrirJeu("langue")
        }
        e.apply()
        reglerCreature()
        ile.auto = p.getBoolean("ile_auto", true)
        if (p.getBoolean("ile", true)) ajouterIle() else retirerIle()
        if (cle == "taille") { bitmaps.clear(); majFenetreCreature() }
    }

    // ------------------------------------------------------------ dessin commun
    private fun bitmap(c: Poses.Cadre): Bitmap = bitmaps.getOrPut(c.cle) {
        if (bitmaps.size > 120) bitmaps.clear()
        Bitmap.createBitmap(c.argb, c.w, c.h, Bitmap.Config.ARGB_8888)
    }

    private val pinceau = Paint(Paint.ANTI_ALIAS_FLAG)
    private val pinceauImage = Paint()

    /** Dessine un cadre, son ancre (les pieds) en (ax, ay) écran, à l'échelle e, déformé autour des pieds (sx, sy,
     *  rot en degrés) et plus ou moins opaque : la déformation se fait à la résolution de l'écran (pas de gros pixel). */
    private fun dessinerCadre(cv: Canvas, c: Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean,
                              sx: Float = 1f, sy: Float = 1f, rot: Float = 0f, opacite: Float = 1f) {
        if (opacite <= 0.01f) return
        pinceauImage.isFilterBitmap = lisse
        pinceauImage.alpha = (255 * opacite.coerceIn(0f, 1f)).toInt()
        val b = bitmap(c)
        cv.save()
        cv.translate(ax, ay)
        if (rot != 0f) cv.rotate(-rot)
        cv.scale(if (miroir) -sx else sx, sy)
        cv.drawBitmap(b, Rect(0, 0, c.w, c.h), RectF(-c.ax * e, -c.ay * e, (c.w - c.ax) * e, (c.h - c.ay) * e), pinceauImage)
        cv.restore()
        pinceauImage.alpha = 255
    }

    private fun echelle(a: Poses.Album, h: Float): Float =
        if (a.lisse) min(max(h / dp(120f) * dens * 1.0f, 0.7f * h / a.ref), 1.35f * h / a.ref).let { if (it.isNaN()) 1f else it }
        else max(1, Math.round(h / a.ref)).toFloat()

    private fun pilule(cv: Canvas, r: RectF, fond: Int, bord: Int, rayon: Float = r.height() / 2) {
        pinceau.style = Paint.Style.FILL; pinceau.color = fond
        cv.drawRoundRect(r, rayon, rayon, pinceau)
        pinceau.style = Paint.Style.STROKE; pinceau.color = bord; pinceau.strokeWidth = dp(1f)
        cv.drawRoundRect(r, rayon, rayon, pinceau)
        pinceau.style = Paint.Style.FILL
    }

    private fun texte(cv: Canvas, s: String, x: Float, y: Float, taille: Float, couleur: Int, gras: Boolean = false,
                      align: Paint.Align = Paint.Align.LEFT, mono: Boolean = false) {
        pinceau.textSize = taille; pinceau.color = couleur; pinceau.textAlign = align
        pinceau.typeface = if (mono) Typeface.MONOSPACE else if (gras) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        cv.drawText(s, x, y + taille * 0.35f, pinceau)
    }

    // ------------------------------------------------------------ la créature
    inner class CreatureVue(ctx: Context) : View(ctx) {
        override fun onDraw(cv: Canvas) {
            val a = album ?: return
            val w = width.toFloat(); val h = height.toFloat()
            val haut = taille()
            val e = echelle(a, haut)
            val an = BureauVie.animer(creature)
            val c = a.image(an.etat, an.k)
            val sol = h - dp(6f)
            val ref = a.images("assis")[0]
            val om = an.ombre
            pinceau.color = Color.argb((70 * om).toInt(), 0, 0, 0)
            cv.drawOval(RectF(w / 2 - ref.w * e * 0.36f * om, sol - dp(3f) * om, w / 2 + ref.w * e * 0.36f * om, sol + dp(3f) * om), pinceau)
            val pied = sol + dp(an.dy)
            an.ancien?.let { v -> dessinerCadre(cv, a.image(v.etat, v.k), w / 2, pied, e, v.miroir, a.lisse, an.sx, an.sy, an.rot, v.opacite) }
            dessinerCadre(cv, c, w / 2, pied, e, an.miroir, a.lisse, an.sx, an.sy, an.rot, an.opacite)
            val lc = ref.w * e; val hc = ref.h * e
            for (f in an.effets) {                                       // « z », cœur, miette
                val ex = w / 2 + (if (an.miroir) -1 else 1) * f.x * lc; val ey = pied + f.y * hc; val et = max(dp(6f), f.taille * hc)
                val al = (255 * f.opacite.coerceIn(0f, 1f)).toInt()
                when (f.genre) {
                    "z" -> texte(cv, "z", ex, ey, et, Color.argb((al * 0.9f).toInt(), 190, 215, 255), true, Paint.Align.CENTER)
                    "coeur" -> texte(cv, "♥", ex, ey, et, Color.argb(al, 255, 95, 140), true, Paint.Align.CENTER)
                    "miette" -> {                                    // un petit biscuit : bord brun, cœur doré
                        val b = dp(1.5f)
                        pinceau.color = Color.argb(al, 74, 38, 18); cv.drawOval(RectF(ex - et / 2 - b, ey - et / 2.4f - b, ex + et / 2 + b, ey + et / 2.4f + b), pinceau)
                        pinceau.color = Color.argb(al, 246, 196, 92); cv.drawOval(RectF(ex - et / 2, ey - et / 2.4f, ex + et / 2, ey + et / 2.4f), pinceau)
                    }
                }
            }
            val now = SystemClock.elapsedRealtime()
            for ((s, t0, coul) in flottants) {
                val age = (now - t0) / 1000f
                texte(cv, s, w / 2 + ref.w * e * 0.4f, sol - ref.h * e - age * dp(24f), dp(14f),
                    Color.argb((255 * max(0f, 1 - age / 1.6f)).toInt(), Color.red(coul), Color.green(coul), Color.blue(coul)), true)
            }
            phrase?.let { (s, fin) ->
                if (now < fin && vueMenu == null) {
                    val tw = min(w - dp(8f), BureauVie.largeurTexte(s, dp(13f)) + dp(24f))
                    val r = RectF(w / 2 - tw / 2, dp(2f), w / 2 + tw / 2, dp(32f))
                    pilule(cv, r, 0xFAF5F0E6.toInt(), 0xFFC8BFAE.toInt(), dp(12f))
                    texte(cv, Langue.raccourcir(s, (tw / dp(7.5f)).toInt()), w / 2, r.centerY(), dp(13f), 0xFF1E1E2E.toInt(), align = Paint.Align.CENTER)
                }
            }
        }

        override fun onTouchEvent(ev: MotionEvent): Boolean {
            val t = ev.eventTime / 1000.0
            when (ev.actionMasked) {
                MotionEvent.ACTION_DOWN -> gestes.appuyer(ev.rawX, ev.rawY, t)
                MotionEvent.ACTION_MOVE -> {
                    gestes.tenir(t)
                    if (gestes.bouger(ev.rawX, ev.rawY, t)) {
                        if (!creature.porte) { creature.prendre(); fermerMenu() }
                        creature.deplacer(ev.rawX, max(0f, ecranH - ev.rawY - taille() * 0.4f))
                    }
                }
                MotionEvent.ACTION_UP -> when (gestes.relacher(ev.rawX, ev.rawY, t)) {
                    "glisse_fin" -> if (ev.rawY > ecranH - taille() * 0.8f) creature.ranger() else creature.lacher()
                    "ranger" -> { fermerMenu(); creature.ranger() }
                    "triple" -> geste("triple")
                }
                MotionEvent.ACTION_CANCEL -> if (creature.porte) creature.lacher()
            }
            return true
        }
    }

    // ------------------------------------------------------------ le menu rond et ses panneaux
    inner class MenuVue(ctx: Context) : View(ctx) {
        var panneau: Panneau? = null
        private var boutons: List<BureauVie.Bouton> = emptyList()
        private var lignes: List<Pair<RectF, String?>> = emptyList()

        override fun onDraw(cv: Canvas) {
            val a = album ?: return
            val w = width.toFloat(); val h = height.toFloat()
            val haut = (a.ref * echelle(a, taille()))
            val sol = h - dp(6f) - creature.air
            val pan = panneau
            if (pan == null) {
                val lib = BureauVie.MENU.associate { it.first to t("bur.menu." + it.first) }
                val (b, cercle) = BureauVie.menuPositions(creature.x, sol - haut / 2, haut, lib, dp(14f), w, h, dp(150f))
                boutons = b
                pinceau.style = Paint.Style.STROKE; pinceau.color = 0x1AFFFFFF; pinceau.strokeWidth = dp(1f)
                cv.drawOval(RectF(cercle[0] - cercle[2], cercle[1] - cercle[3], cercle[0] + cercle[2], cercle[1] + cercle[3]), pinceau)
                pinceau.style = Paint.Style.FILL
                for (bt in b) {
                    val r = RectF(bt.x, bt.y, bt.x + bt.w, bt.y + bt.h)
                    pilule(cv, r, 0xEC0E1018.toInt(), if (bt.cle == "jouer") 0xC83DDC84.toInt() else 0x1EFFFFFF)
                    texte(cv, bt.symbole, bt.x + bt.h / 2 + dp(2f), r.centerY(), dp(11f), 0xFF3DDC84.toInt(), true, Paint.Align.CENTER)
                    texte(cv, bt.libelle, bt.x + bt.h + dp(4f), r.centerY(), dp(14f), 0xFFE9ECF2.toInt(), true)
                }
                lignes = emptyList()
            } else {
                val pw = min(w - dp(16f), dp(320f))
                val ph = dp(48f) + dp(38f) * pan.lignes.size
                val px = (creature.x - pw / 2).coerceIn(dp(8f), w - pw - dp(8f))
                val py = max(dp(6f), sol - haut - ph - dp(14f))
                pilule(cv, RectF(px, py, px + pw, py + ph), 0xF516192A.toInt(), 0x1EFFFFFF, dp(14f))
                texte(cv, pan.titre, px + dp(16f), py + dp(24f), dp(15f), 0xFFE9ECF2.toInt(), true)
                lignes = pan.lignes.mapIndexed { i, (s, act) ->
                    val r = RectF(px + dp(10f), py + dp(46f) + dp(38f) * i, px + pw - dp(10f), py + dp(78f) + dp(38f) * i)
                    pilule(cv, r, 0x10FFFFFF, 0x00000000, dp(9f))
                    texte(cv, Langue.raccourcir(s, 34), r.left + dp(12f), r.centerY(), dp(13f), if (act != null) 0xFFE9ECF2.toInt() else 0xFF9AA3B5.toInt())
                    r to act
                }
                boutons = emptyList()
            }
        }

        override fun onTouchEvent(ev: MotionEvent): Boolean {
            if (ev.actionMasked == MotionEvent.ACTION_OUTSIDE) { fermerMenu(); return true }
            if (ev.actionMasked != MotionEvent.ACTION_UP) return true
            boutons.firstOrNull { it.touche(ev.x, ev.y) }?.let { action(it.cle); return true }
            lignes.firstOrNull { (r, act) -> act != null && ev.x in r.left..r.right && ev.y in r.top..r.bottom }?.let { action(it.second!!); return true }
            fermerMenu()
            return true
        }
    }

    // ------------------------------------------------------------ l'île
    inner class IleVue(ctx: Context) : FrameLayout(ctx) {
        val dessin = IleDessin(ctx)
        val saisie = EditText(ctx)

        init {
            addView(dessin, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
            val lp = FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, dp(40f).toInt(), Gravity.BOTTOM)
            lp.setMargins(dp(20f).toInt(), 0, dp(20f).toInt(), dp(64f).toInt())
            saisie.setSingleLine(true)
            saisie.setTypeface(Typeface.MONOSPACE)
            saisie.setTextColor(0xFFE9ECF2.toInt())
            saisie.setHintTextColor(0xFF7A8296.toInt())
            saisie.setHint(t("bur.ile.terminal"))
            saisie.setBackgroundColor(0xE6080A0E.toInt())
            saisie.setPadding(dp(12f).toInt(), 0, dp(12f).toInt(), 0)
            saisie.setImeOptions(EditorInfo.IME_ACTION_GO)
            saisie.setOnEditorActionListener { _, id, ev ->
                if (id == EditorInfo.IME_ACTION_GO || ev?.keyCode == KeyEvent.KEYCODE_ENTER) {
                    val l = saisie.text.toString().trim()
                    saisie.setText("")
                    if (l.isNotEmpty()) { ile.fermer(); ouvrirJeu(l) }
                    true
                } else false
            }
            saisie.visibility = View.GONE
            addView(saisie, lp)
        }
    }

    inner class IleDessin(ctx: Context) : View(ctx) {
        private var zones: List<Pair<RectF, String>> = emptyList()

        override fun onDraw(cv: Canvas) {
            val a = album ?: return
            val w = width.toFloat(); val h = height.toFloat()
            val now = SystemClock.elapsedRealtime() / 1000.0
            val evt = ile.etat == "evenement"
            val bord = if (evt) 0x96FF5F6D.toInt() else 0x1EFFFFFF
            pilule(cv, RectF(dp(1f), dp(1f), w - dp(1f), h - dp(1f)), 0xEC0E1018.toInt(), bord, if (ile.etat == "ouverte") dp(24f) else (h - dp(2f)) / 2)
            val (etatMini, msx, msy) = BureauVie.miniVie(creature, now)          // elle respire et cligne
            val c = a.image(etatMini, (now * BureauVie.IPS).toInt())
            val z = mutableListOf<Pair<RectF, String>>()
            if (ile.etat != "ouverte") {
                val e = (h - dp(10f)) / a.ref
                dessinerCadre(cv, c, dp(14f) + c.ax * e, h - dp(4f), e, false, a.lisse, msx, msy)
                var x = dp(22f) + c.w * e
                if (evt) texte(cv, Langue.raccourcir(ile.evenement ?: "", 30), x, h / 2, dp(14f), 0xFFE9ECF2.toInt())
                else for ((coul, s) in listOf(0xFFFF9F43.toInt() to t("bur.ile.faim", "n" to jeu.faim.toInt()),
                        0xFFFFD54F.toInt() to t("bur.ile.xp", "n" to xpPourcent()))) {
                    pinceau.color = coul; cv.drawCircle(x + dp(4f), h / 2, dp(4f), pinceau)
                    texte(cv, s, x + dp(12f), h / 2, dp(13f), 0xFF9AA3B5.toInt())
                    x += dp(22f) + BureauVie.largeurTexte(s, dp(13f))
                }
            } else {
                val e = dp(80f) / a.ref
                val eImg = if (a.lisse) e else max(1, (dp(80f) / a.ref).toInt()).toFloat()
                pilule(cv, RectF(dp(16f), dp(16f), dp(112f), dp(112f)), 0x10FFFFFF, 0x00000000, dp(16f))
                dessinerCadre(cv, c, dp(64f), dp(104f) - abs(sin(now * 3)).toFloat() * dp(3f), eImg, false, a.lisse, msx, msy)
                z.add(RectF(dp(16f), dp(16f), dp(112f), dp(112f)) to "creature")
                pinceau.color = 0xFF3DDC84.toInt(); cv.drawCircle(dp(130f), dp(28f), dp(4f), pinceau)
                texte(cv, jeu.nom, dp(140f), dp(28f), dp(14f), 0xFFE9ECF2.toInt(), true)
                texte(cv, jeu.humeur(), dp(148f) + BureauVie.largeurTexte(jeu.nom, dp(14f)), dp(28f), dp(12f), 0xFF9AA3B5.toInt())
                texte(cv, "×", w - dp(22f), dp(24f), dp(18f), 0xFF9AA3B5.toInt(), align = Paint.Align.CENTER)
                z.add(RectF(w - dp(44f), 0f, w, dp(44f)) to "fermer")
                val dit = (phrase?.takeIf { SystemClock.elapsedRealtime() < it.second }?.first
                    ?: jeu.bulleActive().takeIf { it.isNotEmpty() } ?: Envies.phrase(jeu) ?: "")
                var y = dp(56f)
                for (l in couper(Vert.rendre(dit).toString(), ((w - dp(150f)) / dp(9.5f)).toInt()).take(4)) {
                    texte(cv, l, dp(130f), y, dp(17f), 0xFFE9ECF2.toInt(), true); y += dp(24f)
                }
                val actions = listOf("jouer" to "▶ " + t("bur.menu.jouer"), "terminal" to ">_ " + t("bur.menu.terminal"),
                    "soccuper" to "♥ " + t("bur.ile.nourrir"), "carte" to "◉ " + t("bur.menu.carte"), "reglages" to "⚙ " + t("bur.menu.reglages"))
                val bw = (w - dp(40f) - dp(6f) * 4) / 5
                actions.forEachIndexed { i, (cle, lib) ->
                    val r = RectF(dp(20f) + i * (bw + dp(6f)), h - dp(52f), dp(20f) + i * (bw + dp(6f)) + bw, h - dp(16f))
                    pilule(cv, r, if (cle == "jouer") 0x2A3DDC84 else 0x0AFFFFFF, if (cle == "jouer") 0xC03DDC84.toInt() else 0x1EFFFFFF, dp(9f))
                    texte(cv, Langue.raccourcir(lib, (bw / dp(7f)).toInt()), r.centerX(), r.centerY(), dp(12f),
                        if (cle == "jouer") 0xFF3DDC84.toInt() else 0xFFE9ECF2.toInt(), align = Paint.Align.CENTER)
                    z.add(r to cle)
                }
            }
            zones = z
        }

        private fun couper(s: String, n: Int): List<String> {
            val out = mutableListOf<String>()
            for (para in s.split("\n")) {
                var cour = ""
                for (m in para.split(" ")) {
                    if (cour.isNotEmpty() && cour.length + 1 + m.length > maxOf(8, n)) { out.add(cour); cour = m }
                    else cour = if (cour.isEmpty()) m else "$cour $m"
                }
                out.add(cour)
            }
            return out
        }

        override fun onTouchEvent(ev: MotionEvent): Boolean {
            if (ev.actionMasked == MotionEvent.ACTION_OUTSIDE) { if (ile.etat == "ouverte") ile.fermer(); return true }
            if (ev.actionMasked != MotionEvent.ACTION_UP) return true
            if (ile.etat != "ouverte") { ile.basculer(); return true }
            val z = zones.firstOrNull { (r, _) -> ev.x in r.left..r.right && ev.y in r.top..r.bottom }?.second
            when (z) {
                null -> {}
                "fermer" -> ile.fermer()
                "creature" -> creature.reagir("coeur")
                "soccuper" -> Envies.phrase(jeu)?.let { dire(it, 10.0) }
                else -> { ile.fermer(); action(z) }
            }
            return true
        }
    }

    private fun xpPourcent(): Int {
        val n = jeu.niveau
        val lo = 10 * (n - 1) * (n - 1); val hi = 10 * n * n
        return (100 * (jeu.xp - lo) / maxOf(1, hi - lo)).coerceIn(0, 100)
    }
}

/**
 * La commande `bulle` du terminal (Commandes.kt) : la demande de permission expliquée à l'enfant (ou au parent),
 * puis la bulle qui démarre ou s'arrête.
 */
object Bulle {
    fun permise(ctx: Context): Boolean = Settings.canDrawOverlays(ctx)

    fun voulue(ctx: Context): Boolean = ctx.getSharedPreferences(BulleService.PREFS, Context.MODE_PRIVATE).getBoolean("voulue", false)

    fun demarrer(ctx: Context): Boolean {
        if (!permise(ctx)) return false
        ctx.getSharedPreferences(BulleService.PREFS, Context.MODE_PRIVATE).edit().putBoolean("voulue", true).apply()
        if (!BulleService.enMarche) try { ctx.startForegroundService(Intent(ctx, BulleService::class.java)) } catch (e: Exception) { return false }
        return true
    }

    fun arreter(ctx: Context) {
        ctx.getSharedPreferences(BulleService.PREFS, Context.MODE_PRIVATE).edit().putBoolean("voulue", false).apply()
        ctx.stopService(Intent(ctx, BulleService::class.java))
    }

    /** Au retour dans l'appli (après la page des réglages) : si la permission vient d'être donnée, la bulle part. */
    fun reprendre(ctx: Context) {
        if (voulue(ctx) && permise(ctx) && !BulleService.enMarche) demarrer(ctx)
    }

    /** L'explication, puis la page des réglages d'Android où l'on autorise Terminagotchi. */
    fun demander(act: Activity, nom: String) {
        act.getSharedPreferences(BulleService.PREFS, Context.MODE_PRIVATE).edit().putBoolean("voulue", true).apply()
        AlertDialog.Builder(act)
            .setTitle(t("bulle.permission.titre"))
            .setMessage(t("bulle.permission.texte", "nom" to nom))
            .setPositiveButton(t("bulle.permission.ok")) { _, _ ->
                try {
                    act.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + act.packageName)))
                } catch (e: Exception) {
                    act.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION))
                }
            }
            .setNegativeButton(t("bulle.permission.non")) { _, _ ->
                act.getSharedPreferences(BulleService.PREFS, Context.MODE_PRIVATE).edit().putBoolean("voulue", false).apply()
            }
            .show()
    }

    /** `bulle` (allumer / éteindre), `bulle on`, `bulle off` : le texte à écrire dans le terminal. */
    fun commande(act: Activity, jeu: Jeu, reste: String): String {
        val choix = reste.trim().lowercase()
        val allumer = when (choix) { "on", "oui" -> true; "off", "non" -> false; else -> !BulleService.enMarche }
        if (!allumer) { arreter(act); return t("bulle.rangee", "nom" to jeu.nom) }
        if (!permise(act)) { demander(act, jeu.nom); return t("bulle.permission.attente") }
        return if (demarrer(act)) t("bulle.lancee", "nom" to jeu.nom) else t("bulle.impossible")
    }
}
