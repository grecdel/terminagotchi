package fr.terminagotchi

import android.app.Activity
import android.content.Context
import android.graphics.Paint
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.graphics.Typeface
import android.text.SpannableString
import android.text.SpannableStringBuilder
import android.text.style.StyleSpan
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
    private lateinit var commandes: Commandes
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
    private lateinit var lexiqueBtn: TextView
    private lateinit var lexiqueVue: ScrollView
    private lateinit var lexiqueTexte: TextView
    private lateinit var contenu: LinearLayout

    private val handler = Handler(Looper.getMainLooper())
    private val exec = Executors.newSingleThreadExecutor()
    private var colle = false
    private var programme = false        // texte inséré par l'appli (↑, Tab) : pas un collage
    private var rappel: String? = null   // commande rappelée avec ↑
    private var posHisto = -1
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
        commandes = Commandes(this, jeu, { shell.dossier }) { texte, couleur ->
            if (texte.isNotEmpty()) ecrire(texte, couleur)
            rafraichir()
        }
        Rappels.programmer(this)
        essais(intent)
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission("android.permission.POST_NOTIFICATIONS") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        }
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
        lexiqueBtn = findViewById(R.id.lexique_btn)
        lexiqueVue = findViewById(R.id.lexique_vue)
        lexiqueTexte = findViewById(R.id.lexique_texte)
        lexiqueBtn.setOnClickListener { basculerLexique() }
        creerTouches()
        chemin = findViewById(R.id.chemin)
        contenu = findViewById(R.id.contenu)
        majObservatoire(null)

        // Anti copier-coller : un bloc de plusieurs caractères arrivé d'un coup = collage.
        // (Les suggestions du clavier sont désactivées sur ce champ, donc la frappe arrive lettre par lettre.)
        saisie.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                if (!programme && count - before >= 4) colle = true
            }
            override fun afterTextChanged(s: Editable?) {
                if (s.isNullOrEmpty()) colle = false
            }
        })
        saisie.setOnEditorActionListener { _, actionId, event ->
            when {
                event != null && event.keyCode == KeyEvent.KEYCODE_ENTER -> {
                    // clavier physique : on valide à l'appui et on garde aussi le relâchement,
                    // sinon Android déplace le focus vers un autre élément de l'écran
                    if (event.action == KeyEvent.ACTION_DOWN) valider()
                    true
                }
                actionId == EditorInfo.IME_ACTION_SEND || actionId == EditorInfo.IME_ACTION_DONE -> {
                    valider()
                    true
                }
                else -> false
            }
        }
        saisie.setOnKeyListener { _, code, ev ->
            if (code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_NUMPAD_ENTER) {
                if (ev.action == KeyEvent.ACTION_UP) valider()
                true
            } else false
        }
        // Garde-fou : si la ligne de saisie perd le focus, elle le reprend aussitôt.
        saisie.setOnFocusChangeListener { _, aLeFocus ->
            if (!aLeFocus && hasWindowFocus()) saisie.post { saisie.requestFocus() }
        }
        // Seule la ligne de saisie peut avoir le focus : la touche Entrée ne « clique » jamais ailleurs.
        for (id in listOf(R.id.fond, R.id.panneau, R.id.fermer, R.id.envoyer, R.id.lexique_btn)) {
            findViewById<View>(id).isFocusable = false
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

    override fun onResume() {
        super.onResume()
        if (::jeu.isInitialized && !enCours) {
            jeu.recharger()        // le Doom ou l'éditeur ont pu changer des choses
            rafraichir()
            if (::commandes.isInitialized && Recensement.aUnCompte(jeu)) commandes.sync(forcer = false, silencieux = true)
            if (::contenu.isInitialized) majObservatoire(null)
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        exec.shutdown()
        commandes.fermer()
        super.onDestroy()
    }

    /** Rangée de touches spéciales, difficiles à trouver sur un clavier de téléphone. */
    private fun creerTouches() {
        val rangee = findViewById<LinearLayout>(R.id.touches)
        val dp = resources.displayMetrics.density
        for (t in listOf("↑", "↓", "⇥ Tab", "~", "/", "-", ".", "|", ">", ">>", "*", "\"", "'", "$", "&", "_", "=")) {
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
                when (t) {
                    "↑" -> { rappeler(-1); return@setOnClickListener }
                    "↓" -> { rappeler(1); return@setOnClickListener }
                    "⇥ Tab" -> { completer(); return@setOnClickListener }
                }
                val debut = saisie.selectionStart.coerceAtLeast(0)
                for (c in t) {               // un caractère à la fois : ce n'est pas un collage
                    saisie.text.insert(saisie.selectionStart.coerceAtLeast(debut), c.toString())
                }
                saisie.requestFocus()
            }
            b.isFocusable = false
            rangee.addView(b)
        }
    }

    // ------------------------------------------------------------ commandes
    // ------------------------------------------------------------ historique (↑ ↓) et complétion (Tab)
    private fun remplacerSaisie(texte: String) {
        programme = true
        saisie.setText(texte)
        saisie.setSelection(texte.length)
        programme = false
    }

    private fun rappeler(sens: Int) {
        val h = jeu.historique
        if (h.isEmpty()) {
            ecrire("(historique vide : tape d'abord une commande)", 0xFF9A9AB0.toInt())
            return
        }
        posHisto = (if (posHisto < 0) h.size else posHisto) + sens
        if (posHisto >= h.size) {
            posHisto = -1
            rappel = null
            remplacerSaisie("")
            return
        }
        posHisto = posHisto.coerceIn(0, h.size - 1)
        rappel = h[posHisto]
        remplacerSaisie(h[posHisto])
    }

    /** Complète le dernier mot : un nom de commande (1er mot) ou un fichier/dossier. */
    private fun completer() {
        val texte = saisie.text.toString()
        val debutMot = texte.lastIndexOf(' ') + 1
        val mot = texte.substring(debutMot)
        val candidats: List<String>
        if (debutMot == 0) {
            candidats = Regles.LEXIQUE.map { it.first }.filter { it.startsWith(mot) }.distinct()
        } else {
            val dossierMot = mot.substringBeforeLast('/', "")
            val prefixe = mot.substringAfterLast('/')
            val base = when {
                dossierMot.isEmpty() && mot.startsWith("/") -> File("/")
                dossierMot.isEmpty() -> shell.dossier
                dossierMot.startsWith("~") -> File(jeu.home, dossierMot.removePrefix("~").removePrefix("/"))
                dossierMot.startsWith("/") -> File(dossierMot)
                else -> File(shell.dossier, dossierMot)
            }
            val avant = if (mot.contains('/')) mot.substringBeforeLast('/') + "/" else ""
            candidats = (base.listFiles()?.toList() ?: emptyList())
                .filter { it.name.startsWith(prefixe) && (prefixe.startsWith(".") || !it.name.startsWith(".")) }
                .sortedBy { it.name }
                .map { avant + it.name + if (it.isDirectory) "/" else "" }
        }
        when {
            candidats.isEmpty() -> ecrire("(Tab : rien ne commence par « $mot » ici)", 0xFF9A9AB0.toInt())
            candidats.size == 1 -> {
                val fin = if (candidats[0].endsWith("/")) "" else " "
                remplacerSaisie(texte.substring(0, debutMot) + candidats[0] + fin)
            }
            else -> {
                val commun = candidats.reduce { a, b -> a.commonPrefixWith(b) }
                if (commun.length > mot.length) remplacerSaisie(texte.substring(0, debutMot) + commun)
                ecrire("Tab : " + candidats.joinToString("   "), 0xFFAFAFFF.toInt())
            }
        }
    }

    /** La créature traduit les messages d'erreur les plus courants. */
    private fun expliquer(sortie: String, ligne: String): String? {
        val s = sortie.lowercase()
        return when {
            "no such file" in s || "dossier introuvable" in s ->
                "🤔 Ce fichier ou dossier n'existe pas ici. Vérifie le nom avec ls (majuscules, accents, espaces) ou utilise Tab."
            "permission denied" in s ->
                "🔒 Accès refusé : soit le fichier est protégé (chmod), soit c'est une zone d'Android interdite à l'appli."
            "read-only file system" in s -> "🔒 Cette partie du téléphone est en lecture seule : on ne peut rien y écrire."
            "not found" in s && Regles.premierMot(ligne).isNotEmpty() ->
                "❓ Je ne connais pas la commande « ${Regles.premierMot(ligne)} ». Regarde dans 📖 Lexique (ou fais Tab)."
            "file exists" in s -> "📦 Ça existe déjà : choisis un autre nom, ou regarde avec ls."
            "is a directory" in s -> "📁 C'est un dossier, pas un fichier : utilise ls pour voir dedans (ou rm -r pour le supprimer)."
            "not a directory" in s -> "📄 C'est un fichier, pas un dossier : on ne peut pas entrer dedans."
            "not empty" in s -> "📦 Le dossier n'est pas vide : vide-le d'abord, ou utilise rm -r (prudence, c'est définitif)."
            "missing" in s || "needs " in s || "usage:" in s ->
                "✍ Il manque quelque chose après la commande. Regarde l'exemple dans 📖 Lexique."
            "unknown option" in s || "invalid option" in s || "bad option" in s ->
                "⚙ Option inconnue (ce qui commence par -). Vérifie l'orthographe dans 📖 Lexique."
            "operation not permitted" in s -> "⛔ Opération interdite par Android pour une appli."
            else -> null
        }
    }

    private fun valider() {
        if (enCours) { android.util.Log.i("TG", "commande ignorée : une autre tourne encore"); return }
        val ligne = saisie.text.toString().trim()
        val etaitColle = colle
        colle = false
        val etaitRappel = rappel != null && ligne == rappel
        rappel = null
        posHisto = -1
        if (ligne.isNotEmpty() && jeu.existe && jeu.historique.lastOrNull() != ligne) {
            jeu.historique.add(ligne)
            while (jeu.historique.size > 50) jeu.historique.removeAt(0)
        }
        saisie.setText("")
        if (ligne.isEmpty() || enCours) return

        if (!jeu.existe) {
            jeu.nom = ligne.take(16)
            jeu.shiny = Random.nextInt(64) == 0
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
                    "📱 Téléphone : ouvre, applis, web, carte, appelle, sms, partage, lampe, vibre, batterie, dis, reglages\n" +
                    "🐾 Avec moi : caresse, danse, parle, joue, devine, etat, renomme\n" +
                    "🎮 Jeux : donjon, plan, quetes, attaque, sac, equipe · ctf, drapeau, indice · doom, edite\n" +
                    "🌳 Progresser : arbre, collection, defi, cherche <ce que tu veux faire>\n" +
                    "🌍 En ligne : compte, compte creer Pseudo, compte code, compte lier CODE, sync\n" +
                    "Tout est expliqué dans 📖 Lexique. Chaque commande tapée me nourrit (pas les collées !).\n" +
                    "clear = effacer · quitter = fermer")
                return
            }
        }
        // Commandes intégrées (téléphone, créature) : réponse immédiate
        val interne = commandes.executer(ligne)
        if (interne != null) {
            ecrire(interne.texte, interne.couleur)
            if (lexiqueVue.visibility == View.VISIBLE) basculerLexique()
            interne.aller?.let {
                shell.dossier = it
                majObservatoire(ligne)
            }
            try { apresCommande(ligne, etaitColle, etaitRappel) } catch (e: Exception) { android.util.Log.e("TG", "après « $ligne »", e) }
            if (interne.saut > saut) saut = interne.saut
            return
        }

        enCours = true
        invite.alpha = 0.4f
        android.util.Log.i("TG", "commande : $ligne")
        exec.execute {
            val resultat = try { shell.executer(ligne) } catch (e: Exception) { android.util.Log.e("TG", "shell", e); "erreur : ${e.message}" }
            handler.post {
                if (resultat.isNotEmpty()) ecrire(resultat)
                expliquer(resultat, ligne)?.let { ecrire(it, 0xFFFFAF5F.toInt()) }
                val change = majObservatoire(ligne)
                if (lexiqueVue.visibility == View.VISIBLE) basculerLexique()
                if (resultat.isEmpty() && !change) {
                    ecrire("✓ Fait. (Pas de message = tout s'est bien passé.)", 0xFF9A9AB0.toInt())
                }
                try {
                    apresCommande(ligne, etaitColle, etaitRappel)
                } catch (e: Exception) {
                    android.util.Log.e("TG", "après la commande « $ligne »", e)
                } finally {
                    enCours = false
                    invite.alpha = 1f
                }
            }
        }
    }

    private fun verrouillerFocus(v: View) {
        if (v !== saisie && v !is android.widget.EditText) {
            v.isFocusable = false
            v.isFocusableInTouchMode = false
        }
        if (v is android.view.ViewGroup) for (i in 0 until v.childCount) verrouillerFocus(v.getChildAt(i))
    }

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        essais(intent)
        rafraichir()
        saisie.requestFocus()
    }

    /**
     * Réglages réservés aux tests automatiques (lancés par adb, impossibles depuis l'appli) :
     *   --es essai_dressage abyssor        fait apparaître ce monstre
     *   --es essai_equipe abyssor:adulte   donne une bestiole dressée à ce stade
     */
    private fun essais(i: android.content.Intent?) {
        if (i == null || !jeu.existe) return
        i.getStringExtra("essai_dressage")?.let { nom ->
            Bestiaire.espece(nom)?.let { e ->
                jeu.module("dressage").remove("en_cours")
                java.io.File(jeu.terrain, e.zone).mkdirs()
                Dressage.commencer(jeu, e, false)
            }
        }
        i.getStringExtra("essai_equipe")?.let { v ->
            val (nom, stade) = (v.split(":") + "enfant").let { it[0] to it[1] }
            Bestiaire.espece(nom)?.let { e ->
                val ind = Bestiaire.individu(e, false, e.zone).put("stade", stade).put("xp", 0)
                Explo.captures(jeu).put(ind)
                Explo.collection(jeu).put(e.nom, Explo.collection(jeu).optInt(e.nom) + 1)
                jeu.module("equipe").put("active", ind.getString("id"))
            }
        }
        jeu.sauver()
    }

    private fun apresCommande(ligne: String, etaitColle: Boolean, etaitRappel: Boolean = false) {
        jeu.tick()
        val mange = jeu.manger(ligne, etaitColle, etaitRappel)
        jeu.leconTick(ligne, etaitColle)
        if (!etaitColle && !etaitRappel) Defis.verifier(jeu, ligne)?.let { ecrire(it, 0xFFFFD75F.toInt()); saut = 8 }
        Explo.verifier(jeu)?.let { ecrire(it, 0xFFFF87FF.toInt()) }
        Dressage.verifier(jeu, ligne, etaitColle)?.let { ecrire(it, 0xFFFF87FF.toInt()); saut = 8 }
        Equipe.apresCommande(jeu, etaitColle || etaitRappel)?.let { ecrire(it, 0xFFFFAF00.toInt()) }
        if (!etaitColle && !etaitRappel && Explo.debloquee(jeu) && !Dressage.actif(jeu) && Random.nextInt(25) == 0) {
            Explo.spawn(jeu)                       // en jouant, un monstre peut surgir
        }
        Donjon.verifier(jeu, shell.dossier, ligne)?.let { r ->
            ecrire(r.texte, 0xFFFFD787.toInt())
            r.aller?.let { shell.dossier = it; majObservatoire(null) }
        }
        jeu.sauver()
        WidgetCreature.majTous(this)
        if (mange) saut = maxOf(saut, 4)
        rafraichir()
        if (Recensement.aUnCompte(jeu) && Regles.premierMot(ligne) !in setOf("sync", "compte")) {
            commandes.sync(forcer = false, silencieux = true)
        }
    }

    /**
     * Mise en forme spéciale : ¤id¤ / ¤id*¤ = dessin d'une bestiole (normale / shiny),
     * §texte§ = écriture arc-en-ciel (RGB).
     */
    private fun miseEnForme(texte: String, couleur: Int?): SpannableStringBuilder {
        val sb = SpannableStringBuilder()
        val motif = Regex("¤([a-z0-9]+)([*+]?)¤|§([^§]*)§")
        var i = 0
        for (m in motif.findAll(texte)) {
            sb.append(texte, i, m.range.first)
            if (m.groupValues[1].isNotEmpty()) {
                val e = Bestiaire.espece(m.groupValues[1])
                if (e != null) {
                    val debut = sb.length
                    sb.append("\uFFFC")
                    val detail = if (m.groupValues[2] == "+") Animations.detaille(e.id) else null
                    val d = android.graphics.drawable.BitmapDrawable(resources, detail ?: Bestiaire.bitmap(e, m.groupValues[2] == "*", 4))
                    val px = ((if (detail != null) 160 else 40) * resources.displayMetrics.density).toInt()
                    d.setBounds(0, 0, px, px)
                    sb.setSpan(android.text.style.ImageSpan(d, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM),
                        debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            } else {
                arcEnCiel(sb, m.groupValues[3])
            }
            i = m.range.last + 1
        }
        sb.append(texte, i, texte.length)
        if (couleur != null) {
            // la couleur de base ne recouvre pas l'arc-en-ciel déjà posé
            val base = ForegroundColorSpan(couleur)
            sb.setSpan(base, 0, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            for (sp in sb.getSpans(0, sb.length, ForegroundColorSpan::class.java)) {
                if (sp !== base) {
                    val a = sb.getSpanStart(sp)
                    val b = sb.getSpanEnd(sp)
                    sb.removeSpan(sp)
                    sb.setSpan(sp, a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
        }
        return sb
    }

    private fun arcEnCiel(sb: SpannableStringBuilder, t: String) {
        val n = t.length.coerceAtLeast(1)
        t.forEachIndexed { k, c ->
            val debut = sb.length
            sb.append(c)
            val coul = android.graphics.Color.HSVToColor(floatArrayOf(360f * k / (n + 4), 0.6f, 1f))
            sb.setSpan(ForegroundColorSpan(coul), debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }

    private fun ecrire(texte: String, couleur: Int? = null) {
        val s = miseEnForme(texte, couleur)
        if (sortie.length() > 0) sortie.append("\n")
        sortie.append(s)
        if (sortie.length() > 15000) sortie.text = sortie.text.subSequence(sortie.length() - 12000, sortie.length())
        defile.post { defile.scrollTo(0, sortie.bottom) }
    }

    // ------------------------------------------------------------ lexique
    private fun basculerLexique() {
        if (lexiqueVue.visibility == View.VISIBLE) {
            lexiqueVue.visibility = View.GONE
            defile.visibility = View.VISIBLE
            lexiqueBtn.text = "📖 Lexique"
        } else {
            remplirLexique()
            lexiqueVue.visibility = View.VISIBLE
            defile.visibility = View.GONE
            lexiqueBtn.text = "⌨ Terminal"
            lexiqueVue.scrollTo(0, 0)
        }
    }

    /** Commandes déjà goûtées en blanc, jamais tapées en gris. */
    private fun remplirLexique() {
        val connues = Regles.LEXIQUE.count { it.first in jeu.vus && !it.third.startsWith("💻") }
        val sb = SpannableStringBuilder()
        val entete = "Goûtées : $connues/${Regles.LEXIQUE.size}  ·  blanc = déjà tapée, gris = à découvrir\n"
        sb.append(entete)
        sb.setSpan(ForegroundColorSpan(0xFFFF87FF.toInt()), 0, entete.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        var section = ""
        for ((cmd, desc, sec) in Regles.LEXIQUE) {
            if (sec != section) {
                section = sec
                val d = sb.length
                sb.append("\n$sec\n")
                sb.setSpan(ForegroundColorSpan(0xFFAFAFFF.toInt()), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                sb.setSpan(StyleSpan(Typeface.BOLD), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            val pc = sec.startsWith("💻")
            val goutee = cmd in jeu.vus && !pc
            val debut = sb.length
            sb.append(if (pc) "🔒 " else if (goutee) "● " else "○ ")
            val debutCmd = sb.length
            sb.append(cmd)
            sb.setSpan(StyleSpan(Typeface.BOLD), debutCmd, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            sb.append("  $desc\n")
            val couleur = if (pc) 0xFF45455A.toInt() else if (goutee) 0xFFFFFFFF.toInt() else 0xFF6A6A85.toInt()
            sb.setSpan(ForegroundColorSpan(couleur), debut, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        lexiqueTexte.text = sb
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
            val type = when {
                f.isDirectory && f.name == "escalier" -> "🪜 "
                f.isDirectory && !f.canExecute() -> "🔒📁 "
                f.isDirectory -> "📁 "
                f.name.endsWith(".objet") -> "💎 "
                f.name == "LISEZMOI.txt" -> "📜 "
                else -> "📄 "
            }
            val ico = (if (nouveau) "✨" else "") + type + (if (protege) "🔒" else "")
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
        titre.text = if (!jeu.existe) "Œuf mystérieux" else if (jeu.shiny) miseEnForme("§${jeu.titre()}§", null) else jeu.titre()
        faim.text = jeu.texteFaim()
        xp.text = jeu.texteXp()
        stats.text = jeu.texteStats()
        invite.text = if (jeu.existe) "${shell.chemin()} $" else "nom ?"
        val b = jeu.bulleActive()
        bulle.visibility = if (b.isEmpty()) View.GONE else View.VISIBLE
        bulle.text = b
        val defi = Defis.actif(jeu)
        val panneau = Dressage.panneau(jeu, resources)
        val l: CharSequence? = panneau ?: if (defi != null) "⚡ DÉFI ÉCLAIR : tape « ${Regles.piege(defi)} » — ${Defis.resteSecondes(jeu)} s"
            else if (jeu.existe) jeu.texteLecon() else null
        lecon.visibility = if (l == null) View.GONE else View.VISIBLE
        lecon.text = l ?: ""
        // le panneau du dressage ne doit pas écraser la ligne de saisie (un champ sans hauteur ne peut plus recevoir
        // ce qu'on tape) : on cache la fenêtre d'observation, on réduit la sortie, et le panneau défile s'il est trop haut
        val dp = resources.displayMetrics.density
        val observatoire = chemin.parent as View
        val boiteSortie = defile.parent as View
        observatoire.visibility = if (panneau != null) View.GONE else View.VISIBLE
        val hSortie = ((if (panneau != null) 100 else 140) * dp).toInt()
        if (boiteSortie.layoutParams.height != hSortie) { boiteSortie.layoutParams.height = hSortie; boiteSortie.requestLayout() }
        if (panneau != null) {
            val fondH = findViewById<View>(R.id.fond).height.takeIf { it > 0 } ?: resources.displayMetrics.heightPixels
            val entete = (titre.parent.parent as View).height
            val hBulle = if (bulle.visibility == View.VISIBLE) bulle.height + (6 * dp).toInt() else 0
            lecon.maxHeight = maxOf((70 * dp).toInt(), fondH - entete - hBulle - hSortie - ((44 + 52 + 40) * dp).toInt())
        } else lecon.maxHeight = Int.MAX_VALUE
        if (lecon.movementMethod == null) lecon.movementMethod = android.text.method.ScrollingMovementMethod()
        // rien d'autre que la ligne de saisie ne doit pouvoir prendre le focus (sinon ce qu'on tape part dans le vide)
        verrouillerFocus(findViewById(R.id.panneau))
        if (!saisie.hasFocus()) saisie.requestFocus()
        // pendant un dressage, le familier est déjà dans le face-à-face : on allège l'en-tête
        val vis = if (panneau != null) View.GONE else View.VISIBLE
        creature.visibility = vis; faim.visibility = vis; xp.visibility = vis; stats.visibility = vis
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
            Defis.verifier(jeu, null)
            if (jeu.existe && jeu.stade >= 1 && Defis.actif(jeu) == null && !Dressage.actif(jeu) && Random.nextInt(60) == 0) Defis.lancer(jeu)
            Explo.verifier(jeu)?.let { ecrire(it, 0xFFFF87FF.toInt()) }
            Dressage.verifier(jeu, null, false)?.let { ecrire(it, 0xFFFF87FF.toInt()) }
            if (Random.nextInt(4) == 0) jeu.parlerSiSilencieux()
            jeu.sauver()
            rafraichir()
        } else if ((Defis.actif(jeu) != null || Dressage.actif(jeu)) && frame % 2 == 0) {
            if (Dressage.actif(jeu)) Dressage.verifier(jeu, null, false)?.let { ecrire(it, 0xFFFF87FF.toInt()) }
            rafraichir()                          // compte à rebours du défi ou du dressage
        } else if (bulle.visibility == View.VISIBLE && jeu.bulleActive().isEmpty()) {
            rafraichir()
        }
        handler.postDelayed({ animer() }, 420)
    }
}
