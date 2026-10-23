package fr.terminagotchi

import android.app.Activity
import android.content.Context
import android.graphics.Paint
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.File
import java.util.concurrent.Executors
import kotlin.random.Random

/**
 * Le panneau qui « sort » du widget : créature en haut, terminal au milieu,
 * ligne de saisie en bas, juste au-dessus du clavier.
 */
class TerminalActivity : Activity() {
    private lateinit var jeu: Jeu
    private lateinit var shell: Shell
    private lateinit var creature: ImageView
    private lateinit var titre: TextView
    private lateinit var faim: TextView
    private lateinit var xp: TextView
    private lateinit var stats: TextView
    private lateinit var bulle: TextView
    private lateinit var lecon: TextView
    private lateinit var defile: ScrollView
    private lateinit var sortie: TextView
    private lateinit var invite: TextView
    private lateinit var saisie: EditText
    private lateinit var chemin: TextView
    private lateinit var contenu: LinearLayout

    private val handler = Handler(Looper.getMainLooper())
    private val exec = Executors.newSingleThreadExecutor()
    private var colle = false
    private var enCours = false
    private var frame = 0
    private var cligne = 0
    private var saut = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_terminal)
        window.setSoftInputMode(
            WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE or
                WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        )

        jeu = Jeu(this)
        shell = Shell(jeu.home)
        creature = findViewById(R.id.creature)
        titre = findViewById(R.id.titre)
        faim = findViewById(R.id.faim)
        xp = findViewById(R.id.xp)
        stats = findViewById(R.id.stats)
        bulle = findViewById(R.id.bulle)
        lecon = findViewById(R.id.lecon)
        defile = findViewById(R.id.defile)
        sortie = findViewById(R.id.sortie)
        invite = findViewById(R.id.invite)
        saisie = findViewById(R.id.saisie)

        findViewById<View>(R.id.fond).setOnClickListener { finish() }
        findViewById<View>(R.id.panneau).setOnClickListener { saisie.requestFocus() }
        findViewById<View>(R.id.fermer).setOnClickListener { finish() }
        findViewById<View>(R.id.envoyer).setOnClickListener { valider() }
        creerTouches()
        chemin = findViewById(R.id.chemin)
        contenu = findViewById(R.id.contenu)
        majObservatoire(null)

        // Anti copier-coller : un bloc de plusieurs caractères arrivé d'un coup = collage.
        // (Les suggestions du clavier sont désactivées sur ce champ, donc la frappe arrive lettre par lettre.)
        saisie.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                if (count - before >= 4) colle = true
            }
            override fun afterTextChanged(s: Editable?) {
                if (s.isNullOrEmpty()) colle = false
            }
        })
        saisie.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_SEND || actionId == EditorInfo.IME_ACTION_DONE ||
                (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)
            ) {
                valider()
                true
            } else false
        }

        jeu.tick()
        if (!jeu.existe) {
            ecrire("Un œuf est apparu sur ton écran !\nComment s'appelle ta créature ?")
        } else {
            jeu.parlerSiSilencieux()
            ecrire("Tape tes commandes ici : je les mange au fur et à mesure !\n« aide » pour l'aide.")
        }
        jeu.sauver()
        rafraichir()
        saisie.requestFocus()
        handler.postDelayed({
            (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager)
                .showSoftInput(saisie, InputMethodManager.SHOW_IMPLICIT)
        }, 200)
        animer()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        exec.shutdown()
        super.onDestroy()
    }

    /** Rangée de touches spéciales, difficiles à trouver sur un clavier de téléphone. */
    private fun creerTouches() {
        val rangee = findViewById<LinearLayout>(R.id.touches)
        val dp = resources.displayMetrics.density
        for (t in listOf("~", "/", "-", ".", "|", ">", ">>", "*", "\"", "'", "$", "&", "_", "=")) {
            val b = TextView(this)
            b.text = t
            b.textSize = 15f
            b.typeface = android.graphics.Typeface.MONOSPACE
            b.setTextColor(0xFFE6E6E6.toInt())
            b.gravity = Gravity.CENTER
            b.minWidth = (40 * dp).toInt()
            b.setPadding((10 * dp).toInt(), (6 * dp).toInt(), (10 * dp).toInt(), (6 * dp).toInt())
            b.setBackgroundResource(R.drawable.touche)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.marginEnd = (6 * dp).toInt()
            b.layoutParams = lp
            b.setOnClickListener {
                val debut = saisie.selectionStart.coerceAtLeast(0)
                for (c in t) {               // un caractère à la fois : ce n'est pas un collage
                    saisie.text.insert(saisie.selectionStart.coerceAtLeast(debut), c.toString())
                }
                saisie.requestFocus()
            }
            rangee.addView(b)
        }
    }

    // ------------------------------------------------------------ commandes
    private fun valider() {
        val ligne = saisie.text.toString().trim()
        val etaitColle = colle
        colle = false
        saisie.setText("")
        if (ligne.isEmpty() || enCours) return

        if (!jeu.existe) {
            jeu.nom = ligne.take(16)
            jeu.log("Un œuf est apparu… il a l'air ${jeu.trait}.")
            jeu.dire("*toc toc* … nourris-moi avec des commandes !", 10)
            jeu.sauver()
            WidgetCreature.majTous(this)
            ecrire("Bienvenue, ${jeu.nom} !\nSuis la leçon en rose juste au-dessus : tape la commande indiquée.")
            rafraichir()
            return
        }

        ecrire("${shell.chemin()} $ $ligne", 0xFF5FD787.toInt())
        when (Regles.premierMot(ligne)) {
            "clear" -> { sortie.text = ""; return }
            "quitter", "exit" -> { finish(); return }
            "aide" -> {
                ecrire("Ce terminal exécute de vraies commandes Android : ls, cd, mkdir, cat, grep, cp, mv, rm, ping…\n" +
                    "Chaque commande tapée me nourrit. Les commandes collées ne comptent pas !\n" +
                    "clear = effacer · quitter = fermer")
                return
            }
        }
        enCours = true
        invite.alpha = 0.4f
        exec.execute {
            val resultat = shell.executer(ligne)
            handler.post {
                if (resultat.isNotEmpty()) ecrire(resultat)
                val change = majObservatoire(ligne)
                if (resultat.isEmpty() && !change) {
                    ecrire("✓ Fait. (Pas de message = tout s'est bien passé.)", 0xFF9A9AB0.toInt())
                }
                jeu.tick()
                val mange = jeu.manger(ligne, etaitColle)
                jeu.leconTick(ligne, etaitColle)
                jeu.sauver()
                WidgetCreature.majTous(this)
                if (mange) saut = 4
                enCours = false
                invite.alpha = 1f
                rafraichir()
            }
        }
    }

    private fun ecrire(texte: String, couleur: Int? = null) {
        val s = SpannableString(texte)
        if (couleur != null) s.setSpan(ForegroundColorSpan(couleur), 0, s.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        if (sortie.length() > 0) sortie.append("\n")
        sortie.append(s)
        if (sortie.length() > 15000) sortie.text = sortie.text.subSequence(sortie.length() - 12000, sortie.length())
        defile.post { defile.scrollTo(0, sortie.bottom) }
    }

    // ------------------------------------------------------------ fenêtre d'observation
    private var dernierDossier: File? = null
    private var derniersNoms: Set<String> = emptySet()

    private fun icone(): String = when (jeu.stade) {
        0 -> "🥚"
        1 -> "🐣"
        2 -> "🐥"
        else -> "🐲"
    }

    private fun chip(texte: String, fond: Int, couleurTexte: Int, barre: Boolean = false) {
        val dp = resources.displayMetrics.density
        val t = TextView(this)
        t.text = texte
        t.textSize = 12f
        t.setTextColor(couleurTexte)
        val g = GradientDrawable()
        g.cornerRadius = 10 * dp
        g.setColor(fond)
        t.background = g
        t.setPadding((9 * dp).toInt(), (5 * dp).toInt(), (9 * dp).toInt(), (5 * dp).toInt())
        if (barre) t.paintFlags = t.paintFlags or Paint.STRIKE_THRU_TEXT_FLAG
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.marginEnd = (6 * dp).toInt()
        t.layoutParams = lp
        contenu.addView(t)
    }

    /**
     * Montre la « pièce » où l'on se trouve et ce qui vient de changer.
     * Renvoie true si quelque chose de visible a changé (pour savoir s'il faut dire « ✓ Fait »).
     */
    private fun majObservatoire(commande: String?): Boolean {
        val d = shell.dossier
        val elements = (d.listFiles()?.toList() ?: emptyList())
            .sortedWith(compareBy<File>({ !it.isDirectory }, { it.name.lowercase() }))
        val visibles = elements.filter { !it.name.startsWith(".") }
        val noms = elements.map { it.name }.toSet()
        val memePiece = d == dernierDossier
        val nouveaux = if (commande != null && memePiece) noms - derniersNoms else emptySet()
        val partis = if (commande != null && memePiece) derniersNoms - noms else emptySet()

        val morceaux = shell.chemin().removePrefix("~").split("/").filter { it.isNotEmpty() }
        val racine = if (shell.chemin().startsWith("~")) "🏠 maison" else "📂 /"
        chemin.text = (listOf(racine) + morceaux).joinToString(" › ") + "  " + icone()

        contenu.removeAllViews()
        for (f in visibles) {
            val nouveau = f.name in nouveaux
            val protege = f.isFile && !f.canWrite()
            val ico = (if (nouveau) "✨" else "") + (if (f.isDirectory) "📁 " else "📄 ") + (if (protege) "🔒" else "")
            when {
                nouveau -> chip(ico + f.name, 0xFF1F4D33.toInt(), 0xFF5FD787.toInt())
                f.isDirectory -> chip(ico + f.name, 0xFF2E3A5C.toInt(), 0xFFAFD7FF.toInt())
                else -> chip(ico + f.name, 0xFF2E2E48.toInt(), 0xFFE6E6E6.toInt())
            }
        }
        for (n in partis.filter { !it.startsWith(".") }) chip("🗑 $n", 0xFF4D1F25.toInt(), 0xFFFF5F5F.toInt(), barre = true)
        if (visibles.isEmpty() && partis.isEmpty()) chip("(dossier vide)", 0xFF26263A.toInt(), 0xFF9A9AB0.toInt())
        val caches = elements.size - visibles.size
        if (caches > 0) chip("+$caches caché(s) · ls -a", 0xFF26263A.toInt(), 0xFF9A9AB0.toInt())

        var change = false
        if (commande != null) {
            if (dernierDossier != null && !memePiece) {
                ecrire("🚶 Tu entres dans ${shell.chemin()}", 0xFFAF87FF.toInt())
                change = true
            } else if (Regles.premierMot(commande) == "cd") {
                ecrire("📍 Tu es déjà dans ${shell.chemin()}", 0xFFAF87FF.toInt())
                change = true
            }
            for (n in nouveaux.filter { !it.startsWith(".") }) {
                val dossier = File(d, n).isDirectory
                ecrire(if (dossier) "📁 Nouveau dossier : $n" else "📄 Nouveau fichier : $n", 0xFF5FD787.toInt())
                change = true
            }
            for (n in partis.filter { !it.startsWith(".") }) {
                ecrire("🗑 A disparu d'ici : $n", 0xFFFF5F5F.toInt())
                change = true
            }
        }
        dernierDossier = d
        derniersNoms = noms
        return change
    }

    // ------------------------------------------------------------ affichage
    private fun rafraichir() {
        titre.text = if (jeu.existe) jeu.titre() else "Œuf mystérieux"
        faim.text = jeu.texteFaim()
        xp.text = jeu.texteXp()
        stats.text = jeu.texteStats()
        invite.text = if (jeu.existe) "${shell.chemin()} $" else "nom ?"
        val b = jeu.bulleActive()
        bulle.visibility = if (b.isEmpty()) View.GONE else View.VISIBLE
        bulle.text = b
        val l = if (jeu.existe) jeu.texteLecon() else null
        lecon.visibility = if (l == null) View.GONE else View.VISIBLE
        lecon.text = l ?: ""
        creature.setImageBitmap(Sprites.bitmap(jeu, 12, cligne > 0))
    }

    private fun animer() {
        frame++
        val dp = resources.displayMetrics.density
        creature.translationY = when {
            saut > 0 -> { saut--; -10f * dp * (if (saut % 2 == 0) 1f else 0.6f) }
            frame % 2 == 0 -> -2f * dp
            else -> 0f
        }
        if (cligne > 0) {
            cligne--
            if (cligne == 0) creature.setImageBitmap(Sprites.bitmap(jeu, 12, false))
        } else if (Random.nextInt(12) == 0) {
            cligne = 1
            creature.setImageBitmap(Sprites.bitmap(jeu, 12, true))
        }
        if (frame % 12 == 0 && !enCours) {        // toutes les ~5 s : la faim, les bulles, les leçons « fichiers »
            jeu.tick()
            jeu.leconTick(null, false)
            if (Random.nextInt(4) == 0) jeu.parlerSiSilencieux()
            jeu.sauver()
            rafraichir()
        } else if (bulle.visibility == View.VISIBLE && jeu.bulleActive().isEmpty()) {
            rafraichir()
        }
        handler.postDelayed({ animer() }, 420)
    }
}
