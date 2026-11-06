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
    /** les onglets du terminal (Onglets.kt) : chacun son shell, son dossier, son historique, son écran */
    private lateinit var onglets: Onglets
    /** le shell de l'onglet affiché */
    private val shell: Shell get() = onglets.actif.shell
    /** la rangée des onglets, au-dessus de l'écran du terminal */
    private lateinit var barreOnglets: LinearLayout
    private lateinit var commandes: Commandes
    private lateinit var menu: MenuParties
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
    // courte animation de la créature en cours (moteur AnimAuto) : images, position, date de la demande jouée
    private var lecture: List<android.graphics.Bitmap>? = null
    private var lectureK = 0
    private var lectureFin = 0
    private var animJouee = System.currentTimeMillis()   // on ne rejoue pas les événements d'avant l'ouverture
    // l'intro (Intro.kt, IntroVue) : l'écran du début montré (0 : aucun), la confirmation de « debloquer tout »
    private var ecranIntro = 0
    /** le nom proposé pour l'œuf, en attente de confirmation (« Ton œuf s'appellera … ? ») */
    private var nomPropose: String? = null
    private var introVue: IntroVue? = null
    private var confirmerDeblocage = false
    /** « parent temps 45 » : la phrase d'un adulte est attendue (Apprendre.kt, idée 49) */
    private var confirmerParent: List<String>? = null
    /** la question des grands avant « Tout afficher » (options de l'espace) : la réponse se tape ici */
    private var questionAdulte: Pair<String, String>? = null
    /** idée 76 : « bug » → la question des grands (« Tu es un adulte ? »), puis la carte du rapport (Signaler.kt) */
    private var questionBug: Pair<String, String>? = null
    private var carteBug: View? = null
    private var rapportBug: Pair<String, String>? = null
    private var puceBug: TextView? = null
    /** idée 74 : l'état du nuage de synchro montré (null : rien) */
    private var nuageMontre: String? = null
    private var ambiance = System.currentTimeMillis() + AMBIANCE

    // ------------------------------------------------------------ accueil et aide (AideDouce.kt, idées du 3 novembre)
    /** idée 1 : 1 = « Qui est avec toi ? », 2 = les conseils pour l'adulte, 0 = rien (avant les écrans de l'histoire) */
    private var ecranParent = 0
    private var choixParent: String? = null
    /** idée 6 : la carte « Pas de panique » (à la place de l'écran du terminal) */
    private var perduVue: IntroVue? = null
    private lateinit var perduBtn: TextView
    /** idée 4 : la bulle « Tape pwd ici, puis Entrée » et la flèche qui clignote dans la ligne de saisie */
    private lateinit var flecheBulle: TextView
    private lateinit var flecheVue: TextView
    /** idée 66 : la fin grisée, dessinée juste derrière la ligne de saisie */
    private lateinit var fantomeVue: TextView
    private var fantome = ""
    /** idée 5 : les touches de la rangée (rangée 1, ou la 2e après ⋯) ; idée 25 : le bouton 💡 Indice */
    private val touchesVues = mutableListOf<TextView>()
    private var deuxiemeRangee = false
    private lateinit var indiceBtn: TextView
    /** idée 79 : le menu du jeu en plein écran */
    private var menuVue: IntroVue? = null
    /** idée 69 : un clavier est branché (la rangée s'efface, les boutons se choisissent au clavier) */
    private var clavierBranche = false
    /** idée 2 : la cinématique du premier ls est en cours */
    private var lsAnim = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_terminal)
        window.setSoftInputMode(
            WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE or
                WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        )

        val repares = try { Sante.auDemarrage(this) } catch (e: Exception) { emptyList() }   // répare doucement (Sante.kt)
        garderLesPannes()                         // idée 76 : un plantage est noté (files/erreurs.log) pour `bug`
        jeu = Jeu(this)
        // lecture et confort (Confort.kt) : ce que le téléphone demande déjà (taille de police, animations coupées)
        Confort.echelleSysteme = resources.configuration.fontScale.toDouble()
        Confort.moinsAnimations = try {
            android.provider.Settings.Global.getFloat(contentResolver, android.provider.Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
        } catch (e: Exception) { false }
        Confort.activer(if (jeu.existe) jeu else null)
        Seances.chargeur = { try { assets.open("seances.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
        onglets = Onglets({ Shell(jeu.home).also { s -> s.journal = { jeu.journal.toList() } } }, { jeu.historique.toList() })
        // l'écran est recréé (mode sombre changé, appli arrêtée par le téléphone puis rouverte…) : les onglets reviennent
        // (tourner le téléphone ne recrée plus l'écran : android:configChanges dans le manifeste)
        val repris = jeu.existe && onglets.reprendre(savedInstanceState?.getString(ETAT_ONGLETS), jeu.home)
        if (repris) for (o in onglets.liste) savedInstanceState?.getCharSequence(ETAT_ECRAN + o.numero)?.let { o.ecran = it }
        commandes = Commandes(this, jeu, { shell.dossier }) { texte, couleur ->
            if (texte.isNotEmpty()) ecrire(texte, couleur)
            rafraichir()
        }
        menu = MenuParties(this, jeu,
            apresChangement = {
                onglets.nouvellePartie(jeu.home)    // l'ancien terrain a été rangé avec son ancienne partie (tous les onglets)
                animJouee = System.currentTimeMillis()
                ecranIntro = if (!jeu.existe) 1 else 0       // une nouvelle partie : les écrans du début
                WidgetCreature.majTous(this)
                if (::contenu.isInitialized) majObservatoire(null)
                rafraichir()
            },
            synchroniser = { commandes.sync(forcer = true) },
            texteCompte = { commandes.executer("compte")?.texte ?: "" },
            plusTard = { ecrire(it, Commandes.BLEU) })
        Rappels.programmer(this)
        if (!repris) {                 // un écran recréé ne rejoue pas ce que demandait son lancement
            essais(intent)
            handler.postDelayed({ commandeExterne(intent) }, 400)      // une commande tapée dans l'île de la bulle
        }
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission("android.permission.POST_NOTIFICATIONS") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        }
        creature = findViewById(R.id.creature)
        creature.setOnClickListener { montrerCreature("album") }      // 16 : toucher la créature ouvre son album
        creerBoutonAura()
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
        clavierBranche = clavierPhysique()
        textesFixes()
        creerTouches()
        creerBarreOnglets()
        creerAideDouce()
        chemin = findViewById(R.id.chemin)
        contenu = findViewById(R.id.contenu)
        chemin.setOnClickListener {               // idée 74 : toucher le nuage l'explique en une ligne
            Recensement.phraseNuage(jeu).takeIf { it.isNotEmpty() }?.let { ecrire(it, Commandes.BLEU) }
        }
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
            if (!clavierBranche && code in 29..54 && ev.action == KeyEvent.ACTION_DOWN && vraiClavier(ev)) {   // une lettre d'un vrai clavier
                clavierBranche = true
                ecrire("⌨ " + t("ad.k.efface"), 0xFF9A9AB0.toInt())
                rafraichir()
            }
            if (code == 31 && ev.isCtrlPressed) {      // Ctrl+C d'un clavier branché (31 : KEYCODE_C)
                if (ev.action == KeyEvent.ACTION_DOWN) ctrlC()
                true
            } else if (code == KeyEvent.KEYCODE_TAB) {  // idée 69 : Tab change de bouton (écrans dessinés), sinon complète
                if (ev.action == KeyEvent.ACTION_DOWN) {
                    val v = menuVue ?: perduVue ?: introVue?.takeIf { it.nbBoutons() > 0 && saisie.text.isEmpty() }
                    if (v != null && toutAuClavier()) v.focusSuivant(if (ev.isShiftPressed) -1 else 1)
                    else if (!accepterFantome()) completer()
                }
                true
            } else if (code == KeyEvent.KEYCODE_ESCAPE) {   // idée 69 : Échap passe ou ferme
                if (ev.action == KeyEvent.ACTION_DOWN) when {
                    perduVue != null -> fermerPerdu()
                    menuVue != null -> actionMenu("1")
                    lexiqueVue.visibility == View.VISIBLE -> basculerLexique()
                    !jeu.existe && ecranParent > 0 -> actionIntro(if (ecranParent == 1) "seul" else "parti")
                    !jeu.existe && ecranIntro > 0 -> actionIntro("passer")
                    jeu.existe && Intro.aMontrer(jeu) != null -> actionIntro("ok")
                }
                true
            } else if ((code == KeyEvent.KEYCODE_DPAD_UP || code == KeyEvent.KEYCODE_DPAD_DOWN) && menuVue != null) {
                if (ev.action == KeyEvent.ACTION_DOWN) menuVue?.focusSuivant(if (code == KeyEvent.KEYCODE_DPAD_UP) -1 else 1)
                true
            } else if (code == KeyEvent.KEYCODE_DPAD_RIGHT && fantome.isNotEmpty()) {   // idée 66 : → accepte la fin grisée
                if (ev.action == KeyEvent.ACTION_DOWN) accepterFantome()
                true
            } else if (code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_NUMPAD_ENTER) {
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
        if (repris) {
            montrerOnglet()                          // l'écran recréé reprend où il en était, onglet par onglet
        } else if (lanceur(intent) && !Parties.aucune(this)) {
            ouvrirMenu()                             // lancé depuis l'icône : le menu du jeu (idée 79)
        } else if (!jeu.existe) {
            ecrire(t("term.oeuf"))
            ecranIntro = 1                           // les écrans du début (Intro.kt), avant le nom de l'œuf
            if (Parties.aucune(this)) ecranParent = 1   // idée 1 : « Qui est avec toi ? », la toute première fois
        } else {
            jeu.parlerSiSilencieux()
            ecrire(t("mini.accueil1") + "\n" + t("term.aide_pour_aide"))
        }
        for (r in repares) ecrire(r, Commandes.BLEU)
        if (jeu.existe) AideDouce.retour(jeu)?.let { jeu.dire(it, 12); ecrire(it, Commandes.ROSE) }   // idée 9
        if (clavierBranche) ecrire("⌨ " + t("ad.k.efface"), 0xFF9A9AB0.toInt())
        if (!repris) panneDeLaDerniereFois()      // idée 76 : le jeu s'était fermé sur une panne
        jeu.sauver()
        rafraichir()
        majDisposition()                          // idée 75 : deux colonnes sur une tablette en paysage
        if (jeu.existe && jeu.module("espace").optBoolean("ouvert")) {      // l'espace de travail était ouvert
            handler.post { ouvrirEspace(jeu.module("espace").optBoolean("classe"), dire = false) }
        }
        saisie.requestFocus()
        handler.postDelayed({
            (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager)
                .showSoftInput(saisie, InputMethodManager.SHOW_IMPLICIT)
        }, 200)
        animer()
    }

    /**
     * Android va peut-être recréer l'écran : on garde les onglets (Onglets.etat) et le texte de chaque écran (avec ses
     * couleurs, la fin seulement : un écran trop long ne passerait pas).
     */
    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (!::onglets.isInitialized || !::sortie.isInitialized) return
        rangerOnglet()
        outState.putString(ETAT_ONGLETS, onglets.etat())
        for (o in onglets.liste) {
            val e = o.ecran
            outState.putCharSequence(ETAT_ECRAN + o.numero, if (e.length > ECRAN_GARDE) e.subSequence(e.length - ECRAN_GARDE, e.length) else e)
        }
    }

    /** Un clavier branché ou débranché (configChanges : l'écran n'est pas recréé) : idée 69, la rangée s'efface ou revient. */
    override fun onConfigurationChanged(c: android.content.res.Configuration) {
        super.onConfigurationChanged(c)
        val avant = clavierBranche
        clavierBranche = clavierPhysique()
        if (clavierBranche && !avant) ecrire("⌨ " + t("ad.k.efface"), 0xFF9A9AB0.toInt())
        if (::jeu.isInitialized) rafraichir()
        majDisposition()
    }

    override fun onPause() {
        super.onPause()
        ecranVisible = false                      // écran éteint ou appli cachée : la vie se met en pause
        SonsLecteur.pause()                       // et le son se tait (Sons.kt)
    }

    override fun onResume() {
        super.onResume()
        ecranVisible = true
        SonsLecteur.reprendre(this)
        if (::jeu.isInitialized) { Sons.courant = jeu; Sons.suivre(jeu, espace != null && espace?.classe != true) }
        Bulle.reprendre(this)                     // la permission « par-dessus les autres applis » vient d'être donnée
        if (!vieEnMarche) { vieEnMarche = true; handler.postDelayed({ pasVie() }, VIE_PAS) }
        if (::jeu.isInitialized && !enCours) {
            jeu.recharger()        // le Doom ou l'éditeur ont pu changer des choses
            vuNotif = NotifVie.modifie
            WidgetCreature.majTous(this)      // la notification en direct apparaît (ou se met à jour) à l'ouverture
            rafraichir()
            if (::commandes.isInitialized && Recensement.aUnCompte(jeu)) commandes.sync(forcer = false, silencieux = true)
            if (::contenu.isInitialized) majObservatoire(null)
        }
    }

    /** dernier changement fait depuis la notification (Nourrir, Caresser) déjà relu par le terminal */
    private var vuNotif = NotifVie.modifie

    /**
     * Le volet des notifications se referme : si un bouton de la notification a changé la créature pendant ce temps,
     * on relit la sauvegarde (sinon la prochaine commande l'écraserait avec l'ancien état).
     */
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && ::jeu.isInitialized && !enCours && NotifVie.modifie > vuNotif) {
            vuNotif = NotifVie.modifie
            jeu.recharger()
            rafraichir()
            lancerAnimation()
        }
    }

    /** Réponse à la demande de permission des notifications (au lancement, ou « notif on ») */
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (grantResults.isNotEmpty() && grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            WidgetCreature.majTous(this)
            if (requestCode == 2 && ::jeu.isInitialized) ecrire(t("notifs.vie.on", "nom" to jeu.nom), Commandes.ROSE)
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        exec.shutdown()
        commandes.fermer()
        super.onDestroy()
    }

    // ------------------------------------------------------------ la sauvegarde dans un fichier (Sauvegarde.kt)
    /** `sauvegarde exporter` / `sauvegarde importer` : le sélecteur de fichiers d'Android (aucune permission). */
    private fun sauvegarde(action: String?) {
        val i = when (action) {
            "exporter", "exporte", "export" -> android.content.Intent(android.content.Intent.ACTION_CREATE_DOCUMENT)
                .addCategory(android.content.Intent.CATEGORY_OPENABLE).setType("application/octet-stream")
                .putExtra(android.content.Intent.EXTRA_TITLE, Sauvegarde.nomDeFichier(jeu.nom))
            "importer", "importe", "import" -> android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(android.content.Intent.CATEGORY_OPENABLE).setType("*/*")
            else -> { ecrire(t("svg.aide.tel"), Commandes.ROSE); return }
        }
        try {
            startActivityForResult(i, if (i.action == android.content.Intent.ACTION_CREATE_DOCUMENT) REQ_EXPORTER else REQ_IMPORTER)
        } catch (e: Exception) {
            ecrire(t("svg.tel.erreur"), Commandes.ROSE)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_BUG) { enregistrerBug(if (resultCode == RESULT_OK) data?.data else null); return }
        if (requestCode != REQ_EXPORTER && requestCode != REQ_IMPORTER) return
        val uri = data?.data
        if (resultCode != RESULT_OK || uri == null || !jeu.existe) { ecrire(t("svg.tel.annule"), Commandes.ROSE); return }
        enCours = true
        // la partie est lue ou changée ici (fil de l'écran, comme chaque commande) ; seul le fichier passe par exec
        val export = if (requestCode == REQ_EXPORTER) try { Sauvegarde.fabriquer(this, jeu) } catch (e: Exception) { null } else null
        exec.execute {
            var octets: ByteArray? = null
            val ok = try {
                if (export != null) contentResolver.openOutputStream(uri, "wt")!!.use { it.write(export.first.toByteArray(Charsets.UTF_8)) }
                else if (requestCode == REQ_IMPORTER) octets = contentResolver.openInputStream(uri)!!.use { it.readBytes() }
                requestCode == REQ_IMPORTER || export != null
            } catch (e: Exception) {
                android.util.Log.w("TG", "sauvegarde : $e")
                false
            }
            handler.post {
                enCours = false
                val texte = when {
                    !ok -> t("svg.tel.erreur")
                    export != null -> {
                        val taille = export.first.toByteArray(Charsets.UTF_8).size
                        val nom = (try { java.net.URLDecoder.decode(uri.toString(), "UTF-8") } catch (e: Exception) { "" })
                            .substringAfterLast('/').substringAfterLast(':').takeIf { it.endsWith(Sauvegarde.EXTENSION) }
                            ?: Sauvegarde.nomDeFichier(jeu.nom)
                        t("svg.tel.exporte", "nom" to jeu.nom, "fichier" to nom,
                            "taille" to if (taille < 1 shl 20) "${maxOf(1, taille / 1024)} Ko" else "%.1f Mo".format(taille / 1048576.0)) +
                            (if (export.second > 0) "\n" + t("svg.laisses", "n" to export.second) else "")
                    }
                    (octets?.size ?: 0) > Sauvegarde.MAX_TOTAL * 2 -> t("svg.refus.illisible")
                    else -> {
                        val avant = jeu.partie
                        val r = Sauvegarde.importer(this, jeu, String(octets ?: ByteArray(0), Charsets.UTF_8))
                        if (jeu.partie != avant) {          // une partie de plus est arrivée : comme après le menu des parties
                            onglets.nouvellePartie(jeu.home)
                            animJouee = System.currentTimeMillis()
                            WidgetCreature.majTous(this)
                            majObservatoire(null)
                        }
                        r
                    }
                }
                ecrire(texte, Commandes.ROSE)
                rafraichir()
            }
        }
    }

    /** Rangée de touches spéciales, difficiles à trouver sur un clavier de téléphone. Idée 5 (3 novembre) : tout tient
     *  sur une ligne (↑ ⇥ ^C - / ~ | . > ⋯), ⋯ montre les autres (↓ >> * " ' $ & _ =), la touche du symbole que la
     *  leçon demande s'allume en vert ; idée 25 : le bouton 💡 Indice devant, quand la commande n'est pas donnée. */
    private fun creerTouches() {
        val rangee = findViewById<LinearLayout>(R.id.touches)
        val dp = resources.displayMetrics.density
        (rangee.parent as? android.widget.HorizontalScrollView)?.isFillViewport = true
        rangee.layoutParams = rangee.layoutParams.also { it.width = LinearLayout.LayoutParams.MATCH_PARENT }
        indiceBtn = TextView(this).apply {
            text = "💡 " + t("ad.ind.bouton")
            textSize = 13f
            setTextColor(0xFFFFD75F.toInt())
            gravity = Gravity.CENTER
            setPadding((6 * dp).toInt(), (6 * dp).toInt(), (6 * dp).toInt(), (6 * dp).toInt())
            setBackgroundResource(R.drawable.touche)
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).also { it.marginEnd = (4 * dp).toInt() }
            visibility = View.GONE
            isFocusable = false
            setOnClickListener { ecrire(AideDouce.texteDemandeIndice(jeu), 0xFFFFD75F.toInt()); jeu.sauver(); saisie.requestFocus() }
        }
        rangee.addView(indiceBtn)
        for (k in AideDouce.RANGEE1.indices) {
            val b = TextView(this)
            b.textSize = 15f
            b.typeface = android.graphics.Typeface.MONOSPACE
            b.setTextColor(0xFFE6E6E6.toInt())
            b.gravity = Gravity.CENTER
            b.minWidth = 0
            b.setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
            b.setBackgroundResource(R.drawable.touche)
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            lp.marginEnd = (4 * dp).toInt()
            b.layoutParams = lp
            b.setOnClickListener { touche(b.text.toString()) }
            b.isFocusable = false
            touchesVues.add(b)
            rangee.addView(b)
        }
        majTouches()
    }

    /** Une touche de la rangée : ↑ ↓ ⇥ ^C, ⋯ (l'autre rangée), sinon le symbole, un caractère à la fois. */
    private fun touche(t: String) {
        when (t) {
            "↑" -> { rappeler(-1); return }
            "↓" -> { rappeler(1); return }
            "⇥", "⇥ Tab" -> { if (!accepterFantome()) completer(); return }
            "^C" -> { ctrlC(); return }
            "⋯" -> { deuxiemeRangee = !deuxiemeRangee; majTouches(); return }
        }
        val debut = saisie.selectionStart.coerceAtLeast(0)
        for (c in t) {               // un caractère à la fois : ce n'est pas un collage
            saisie.text.insert(saisie.selectionStart.coerceAtLeast(debut), c.toString())
        }
        saisie.requestFocus()
    }

    /** Les libellés de la rangée affichée, la touche à allumer (idée 5) et le bouton 💡 (idée 25). */
    private fun majTouches() {
        if (touchesVues.isEmpty()) return
        val noms = if (deuxiemeRangee) AideDouce.RANGEE2 else AideDouce.RANGEE1
        val allumer = if (jeu.existe) AideDouce.toucheAAllumer(commandeAttendue(), saisie.text?.toString()) else null
        for ((k, b) in touchesVues.withIndex()) {
            val nom = noms[k]
            b.text = nom
            val vif = allumer != null && (nom == allumer || (nom == "⋯" && allumer == "⋯" && !deuxiemeRangee) ||
                (deuxiemeRangee && allumer == "⋯" && nom in AideDouce.SYMBOLES2 && commandeAttendue()?.contains(nom) == true))
            if (vif) {
                b.background = GradientDrawable().apply { setColor(0xFF1D3B2A.toInt()); setStroke((2 * resources.displayMetrics.density).toInt(), 0xFF5FD787.toInt()); cornerRadius = 8 * resources.displayMetrics.density }
                b.setTextColor(0xFF5FD787.toInt())
            } else {
                b.setBackgroundResource(R.drawable.touche)
                b.setTextColor(0xFFE6E6E6.toInt())
            }
        }
        if (::indiceBtn.isInitialized) indiceBtn.visibility = if (jeu.existe && AideDouce.cible(jeu) != null) View.VISIBLE else View.GONE
        // idée 69 : avec un clavier branché, la rangée s'efface (le vrai clavier a toutes les touches)
        val rangee = findViewById<LinearLayout>(R.id.touches)
        (rangee.parent as View).visibility = if (clavierBranche && toutAuClavier()) View.GONE else View.VISIBLE
    }

    /** La commande que l'enfant doit taper maintenant (la liste de l'œuf, ou l'étape de la leçon), ou null. */
    private fun commandeAttendue(): String? = try {
        if (!jeu.existe) null
        else if (Intro.enCours(jeu)) Intro.prochaine(jeu)?.let { Intro.commandeDe(it) }
        else Histoire.leconCourante(jeu)?.let { c -> if (jeu.niveau >= c.niveau) c.etapes[jeu.etape].let { e -> if (Placement.cache(jeu, e)) null else e.cmd } else null }
    } catch (e: Exception) { null }

    /** Un vrai clavier est branché (Configuration.keyboard = KEYBOARD_QWERTY, et pas caché). */
    private fun clavierPhysique(): Boolean = try {
        val c = resources.configuration
        c.javaClass.getField("keyboard").getInt(c) == 2 && c.javaClass.getField("hardKeyboardHidden").getInt(c) == 1
    } catch (e: Exception) { false }

    /** La touche vient d'un clavier branché (pas du clavier de l'écran, ni d'un robot de test : leur numéro est -1). */
    private fun vraiClavier(ev: KeyEvent): Boolean = try {
        (ev.javaClass.getMethod("getDeviceId").invoke(ev) as Int) > 0 &&
            ((ev.javaClass.getMethod("getFlags").invoke(ev) as Int) and 2) == 0
    } catch (e: Exception) { false }

    private fun indice(g: android.view.ViewGroup, v: View): Int {
        for (k in 0 until g.childCount) if (g.getChildAt(k) === v) return k
        return -1
    }

    /** Idée 69 : le mode « tout au clavier » (d'office avec un clavier branché ; `clavier off` l'enlève). */
    private fun toutAuClavier(): Boolean =
        if (jeu.existe && jeu.module("aide_douce").has("clavier")) jeu.module("aide_douce").optBoolean("clavier") else clavierBranche

    // ------------------------------------------------------------ accueil et aide (AideDouce.kt, idées du 3 novembre)
    /** Les petites vues de l'aide : le bouton 🧭 Perdu ? (6), la bulle et la flèche « tape ici » (4), la fin grisée (66). */
    private fun creerAideDouce() {
        val dp = resources.displayMetrics.density
        // 6. 🧭 Perdu ?, juste à côté de 📖 Lexique
        val tete = lexiqueBtn.parent as LinearLayout
        perduBtn = TextView(this).apply {
            text = t("ad.perdu.bouton")
            textSize = 12f
            setPadding((8 * dp).toInt(), (4 * dp).toInt(), (8 * dp).toInt(), (4 * dp).toInt())
            setBackgroundResource(R.drawable.touche)
            setTextColor(0xFF9A9AB0.toInt())
            isFocusable = false
            setOnClickListener { ouvrirPerdu() }
        }
        val lpP = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lpP.gravity = Gravity.TOP
        lpP.marginEnd = (4 * dp).toInt()
        tete.addView(perduBtn, indice(tete, lexiqueBtn) + 1, lpP)
        // 4. la bulle au-dessus de la ligne de saisie, et la flèche dans la ligne
        val ligne = saisie.parent as LinearLayout
        val panneau = ligne.parent as LinearLayout
        flecheBulle = TextView(this).apply {
            textSize = 14f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(0xFF1E1E2E.toInt())
            setBackgroundResource(R.drawable.bulle)
            setPadding((10 * dp).toInt(), (6 * dp).toInt(), (10 * dp).toInt(), (6 * dp).toInt())
            visibility = View.GONE
            isFocusable = false
        }
        val lpB = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lpB.gravity = Gravity.END
        lpB.topMargin = (6 * dp).toInt()
        panneau.addView(flecheBulle, indice(panneau, ligne), lpB)
        flecheVue = TextView(this).apply {
            text = "◀◀"
            textSize = 16f
            typeface = Typeface.MONOSPACE
            setTextColor(0xFF5FD787.toInt())
            visibility = View.GONE
            isFocusable = false
        }
        ligne.addView(flecheVue, indice(ligne, saisie) + 1)
        // 66. la fin grisée : un texte transparent (ce qui est tapé) puis la fin en gris, sous la ligne de saisie
        val i = indice(ligne, saisie)
        val lpS = saisie.layoutParams as LinearLayout.LayoutParams
        ligne.removeView(saisie)
        val cadre = android.widget.FrameLayout(this)
        fantomeVue = TextView(this).apply {
            typeface = Typeface.MONOSPACE
            textSize = 13f
            setPadding(0, 0, 0, 0)
            isFocusable = false
            gravity = saisie.gravity
        }
        cadre.addView(fantomeVue, android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.FrameLayout.LayoutParams.MATCH_PARENT))
        cadre.addView(saisie, android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT))
        ligne.addView(cadre, i, lpS)
        saisie.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(e: Editable?) {
                if (lsAnim) finirPremierLs()                 // une touche passe la cinématique du premier ls
                majFantome()
                majTouches()
            }
        })
    }

    /** Idée 66 : la fin grisée du mot en cours (seulement des noms qui existent ; jamais pendant un exercice). */
    private fun majFantome() {
        if (!::fantomeVue.isInitialized) return
        val texte = saisie.text?.toString() ?: ""
        fantome = if (!jeu.existe || menu.ouvert || texte.isEmpty() || texte.endsWith(" ") || saisie.selectionEnd != texte.length ||
            !AideDouce.fantomePermis(jeu)) "" else try { candidats(texte).let { (mot, c) -> AideDouce.fantome(mot, c) } } catch (e: Exception) { "" }
        if (fantome.isEmpty()) { fantomeVue.text = ""; return }
        val sb = SpannableStringBuilder(texte + fantome)
        sb.setSpan(ForegroundColorSpan(0x00000000), 0, texte.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        sb.setSpan(ForegroundColorSpan(0xFF5A5A78.toInt()), texte.length, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        fantomeVue.text = sb
    }

    /** Accepte la fin grisée (→ ou Tab) ; vrai si elle était là. */
    private fun accepterFantome(): Boolean {
        if (fantome.isEmpty()) return false
        remplacerSaisie((saisie.text?.toString() ?: "") + fantome)
        return true
    }

    /** Idée 4 : la flèche « tape ici », la bulle, la ligne de saisie qui s'allume ; idée 6 : le bouton Perdu. */
    private fun majAideDouce() {
        if (!::perduBtn.isInitialized) return
        val dp = resources.displayMetrics.density
        perduBtn.visibility = if (jeu.existe && menuVue == null) View.VISIBLE else View.GONE
        perduBtn.text = t("ad.perdu.bouton")                // dans la langue choisie (elle peut changer en jeu)
        if (::indiceBtn.isInitialized) indiceBtn.text = "💡 " + t("ad.ind.bouton")
        val a = AideDouce.a(jeu)
        val vif = jeu.existe && AideDouce.perduVif(a.optInt("erreurs"), AideDouce.depuis(jeu))
        if (vif) {
            perduBtn.background = GradientDrawable().apply { setColor(0xFF3A2F12.toInt()); setStroke((2 * dp).toInt(), 0xFFFFD75F.toInt()); cornerRadius = 8 * dp }
            perduBtn.setTextColor(0xFFFFD75F.toInt())
        } else {
            perduBtn.setBackgroundResource(R.drawable.touche)
            perduBtn.setTextColor(0xFF9A9AB0.toInt())
        }
        val cmd = AideDouce.flecheMaintenant(jeu)
        val ligne = (saisie.parent as View).parent as LinearLayout
        if (cmd != null && perduVue == null) {
            flecheBulle.text = Vert.rendre(if (cmd.isEmpty()) t("ad.fleche.tel0") else t("ad.fleche.tel", "cmd" to "`$cmd`"))
            flecheBulle.visibility = View.VISIBLE
            flecheVue.visibility = View.VISIBLE
            ligne.background = GradientDrawable().apply { setColor(0x00000000); setStroke((2 * dp).toInt(), 0xFF5FD787.toInt()); cornerRadius = 8 * dp }
        } else {
            flecheBulle.visibility = View.GONE
            flecheVue.visibility = View.GONE
            ligne.background = null
        }
    }

    // ------------------------------------------------------------ 79. le menu du jeu
    private fun ouvrirMenu() {
        menu.ouvrir()                                  // l'état du menu (les chiffres et les mots marchent aussi)
        val fond = findViewById<android.widget.FrameLayout>(R.id.fond)
        val v = menuVue ?: IntroVue(this, jeu, { imagePresentation() }) { actionMenu(it) }.also { nv ->
            nv.setBackgroundColor(0xFF07090D.toInt())
            fond.addView(nv, android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT))
            menuVue = nv
        }
        v.clavier = toutAuClavier()
        val h = (fond.height.takeIf { it > 0 } ?: resources.displayMetrics.heightPixels) / resources.displayMetrics.density
        v.montrerMenu(menu.texteQui(), menu.texteCompteCourt(), h)
        fond.post { v.montrerMenu(menu.texteQui(), menu.texteCompteCourt(), fond.height / resources.displayMetrics.density) }
        rafraichir()
    }

    private fun fermerMenuVue() {
        menuVue?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }
        menuVue = null
        rafraichir()
        saisie.requestFocus()
    }

    /** Un bouton du menu (ou Entrée) : Jouer, Nouvelle partie, Charger, Options, Aide, Quitter. */
    private fun actionMenu(a: String) {
        fermerMenuVue()
        if (a == "q") { menu.repondre("q"); finish(); return }
        menu.repondre(a)?.let { if (it.isNotEmpty()) ecrire(it, Commandes.ROSE) }
        rafraichir()
    }

    // ------------------------------------------------------------ 6. pas de panique
    private fun ouvrirPerdu() {
        if (!jeu.existe) return
        val boite = defile.parent as View
        val panneau = boite.parent as LinearLayout
        val v = perduVue ?: IntroVue(this, jeu, { imagePresentation() }) { a ->
            fermerPerdu()
            if (a == "camp") remplacerSaisie("cd ~")        // l'enfant voit la vraie commande, et c'est lui qui valide
        }.also { nv ->
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.topMargin = (8 * resources.displayMetrics.density).toInt()
            panneau.addView(nv, indice(panneau, boite), lp)
            perduVue = nv
        }
        v.clavier = toutAuClavier()
        v.montrerPerdu(AideDouce.infosPerdu(jeu, shell.dossier))
        jeu.sauver()
        boite.visibility = View.GONE
        majAideDouce()
    }

    private fun fermerPerdu() {
        perduVue?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }
        perduVue = null
        (defile.parent as View).visibility = View.VISIBLE
        rafraichir()
        saisie.requestFocus()
    }

    // ------------------------------------------------------------ 2. le premier ls
    /** Un balayage vert, puis les lieux et les objets se dessinent en pixels l'un après l'autre (2 à 3 s), puis
     *  « Waouh, j'y vois ! ». Une seule fois ; une touche la passe. */
    private fun premierLs(court: Boolean) {
        lsAnim = true
        val obs = chemin.parent as View
        obs.visibility = View.VISIBLE
        majObservatoire(null)
        chemin.text = t("ad.ls.scan")
        chemin.setTextColor(0xFF5FD787.toInt())
        val n = contenu.childCount
        for (k in 0 until n) contenu.getChildAt(k).alpha = 0f
        val total = (AideDouce.dureeLs(court) * 1000).toLong()
        val pas = total / maxOf(1, n * 4 + 2)
        val debut = if (court) 900L else 0L
        for (k in 0 until n) for (e in 1..4) handler.postDelayed({
            if (lsAnim && k < contenu.childCount) contenu.getChildAt(k).alpha = e / 4f
        }, debut + pas * (k * 4 + e))
        handler.postDelayed({ finirPremierLs() }, debut + total)
    }

    private fun finirPremierLs() {
        if (!lsAnim) return
        lsAnim = false
        for (k in 0 until contenu.childCount) contenu.getChildAt(k).alpha = 1f
        chemin.setTextColor(0xFFD7D7FF.toInt())
        majObservatoire(null)
        jeu.dire(t("ad.ls.waouh.tel"), 10)
        ecrire(t("ad.ls.waouh.tel"), Commandes.ROSE)
        rafraichir()
    }

    // ------------------------------------------------------------ onglets (plusieurs terminaux, Onglets.kt)
    /** La rangée des onglets (« Terminal 1 », « Terminal 2 »… et « + »), posée juste au-dessus de l'écran du terminal. */
    private fun creerBarreOnglets() {
        val dp = resources.displayMetrics.density
        val cadreSortie = defile.parent as View
        val panneau = cadreSortie.parent as LinearLayout
        var i = 0
        while (i < panneau.childCount && panneau.getChildAt(i) !== cadreSortie) i++
        val defileur = android.widget.HorizontalScrollView(this)
        defileur.setHorizontalScrollBarEnabled(false)
        defileur.isFocusable = false
        barreOnglets = LinearLayout(this)
        barreOnglets.orientation = LinearLayout.HORIZONTAL
        barreOnglets.gravity = Gravity.CENTER_VERTICAL
        defileur.addView(barreOnglets, android.widget.FrameLayout.LayoutParams(
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT, android.widget.FrameLayout.LayoutParams.WRAP_CONTENT))
        val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        lp.topMargin = (8 * dp).toInt()
        panneau.addView(defileur, i, lp)
        // l'écran du terminal colle à la rangée des onglets (l'onglet choisi a la même couleur que lui)
        // l'écran du terminal est le seul élément qui RÉTRÉCIT quand la place manque (clavier ouvert, onglets, leçon) :
        // la rangée de touches et la ligne de saisie restent toujours visibles (le poids ne joue que si ça déborde)
        (cadreSortie.layoutParams as LinearLayout.LayoutParams).let { it.topMargin = 0; it.weight = 1f }
        majOnglets()
    }

    /** Redessine la rangée des onglets : l'onglet affiché a la couleur de l'écran du terminal, les autres sont estompés. */
    private fun majOnglets() {
        if (!::barreOnglets.isInitialized) return
        val dp = resources.displayMetrics.density
        barreOnglets.removeAllViews()
        val plusieurs = onglets.liste.size > 1
        for (o in onglets.liste) {
            val choisi = o === onglets.actif
            val boite = LinearLayout(this)
            boite.orientation = LinearLayout.HORIZONTAL
            boite.gravity = Gravity.CENTER_VERTICAL
            boite.background = GradientDrawable().apply {
                setColor(if (choisi) 0xFF11111B.toInt() else 0xFF2E2E48.toInt())
                cornerRadius = 8 * dp
            }
            boite.setPadding((10 * dp).toInt(), (5 * dp).toInt(), ((if (plusieurs) 4 else 10) * dp).toInt(), (5 * dp).toInt())
            val nom = TextView(this)
            nom.text = ">_ " + o.nom()
            nom.textSize = 12f
            nom.typeface = Typeface.MONOSPACE
            nom.setTextColor(if (choisi) 0xFF5FD787.toInt() else 0xFF9A9AB0.toInt())
            if (choisi) nom.typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            boite.addView(nom)
            boite.setOnClickListener { choisirOnglet(o) }
            if (plusieurs) {                                  // la croix : seulement quand il en reste un autre
                val croix = TextView(this)
                croix.text = "✕"
                croix.textSize = 12f
                croix.setTextColor(0xFF9A9AB0.toInt())
                croix.setPadding((8 * dp).toInt(), 0, (6 * dp).toInt(), 0)
                croix.contentDescription = t("ong.fermer", "nom" to o.nom())
                croix.setOnClickListener { fermerOnglet(o) }
                croix.isFocusable = false
                boite.addView(croix)
            }
            boite.isFocusable = false
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.marginEnd = (6 * dp).toInt()
            barreOnglets.addView(boite, lp)
        }
        if (!onglets.plein()) {
            val plus = TextView(this)
            plus.text = "+"
            plus.textSize = 15f
            plus.typeface = Typeface.MONOSPACE
            plus.setTextColor(0xFFE6E6E6.toInt())
            plus.gravity = Gravity.CENTER
            plus.minWidth = (36 * dp).toInt()
            plus.setPadding((10 * dp).toInt(), (2 * dp).toInt(), (10 * dp).toInt(), (2 * dp).toInt())
            plus.setBackgroundResource(R.drawable.touche)
            plus.contentDescription = t("ong.nouveau")
            plus.setOnClickListener { ouvrirOnglet() }
            plus.isFocusable = false
            barreOnglets.addView(plus)
        }
    }

    /** Une commande tourne encore (une seule à la fois : le gardien des coulisses compare une seule photo, Garde.kt). */
    private fun ongletOccupe(): Boolean {
        if (!enCours) return false
        ecrire(t("ong.occupe", "nom" to onglets.actif.nom()), 0xFF9A9AB0.toInt())
        return true
    }

    /** Range l'écran et la ligne à moitié tapée de l'onglet qu'on quitte. */
    private fun rangerOnglet() {
        val o = onglets.actif
        o.ecran = SpannableStringBuilder(sortie.text)
        o.brouillon = saisie.text.toString()
    }

    /** Montre l'onglet actif : son écran, sa ligne à moitié tapée, sa pièce, son invite. */
    private fun montrerOnglet() {
        val o = onglets.actif
        sortie.text = o.ecran
        remplacerSaisie(o.brouillon)
        posHisto = -1
        rappel = null
        colle = false
        majObservatoire(null)
        majOnglets()
        rafraichir()
        defile.post { defile.scrollTo(0, sortie.bottom) }
        garderSaisie()
    }

    /** Après un changement d'onglet : la ligne de saisie garde le focus et le clavier reste ouvert. */
    private fun garderSaisie() {
        saisie.requestFocus()
        saisie.post {
            saisie.requestFocus()
            saisie.setSelection(saisie.text.length)
            (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager).showSoftInput(saisie, InputMethodManager.SHOW_IMPLICIT)
        }
    }

    /** « + », `terminal`, `tg terminal` : un terminal de plus (comme une fenêtre de plus sur PC). */
    private fun ouvrirOnglet() {
        if (ongletOccupe()) return
        if (onglets.plein()) {
            ecrire(t("ong.max", "max" to Onglets.MAX), 0xFFFFAF5F.toInt())
            return
        }
        val avant = onglets.actif
        rangerOnglet()
        val o = onglets.ouvrir() ?: return
        o.ecran = ""
        montrerOnglet()
        ecrire(t("ong.ouvert", "nom" to o.nom(), "avant" to avant.nom()), Commandes.ROSE)
    }

    private fun choisirOnglet(o: Onglet) {
        if (o === onglets.actif) { saisie.requestFocus(); return }
        if (ongletOccupe()) return
        rangerOnglet()
        onglets.choisir(o)
        montrerOnglet()
    }

    /** ✕ ou `exit` : ferme cet onglet. Faux si c'est le dernier (il ne se ferme pas). */
    private fun fermerOnglet(o: Onglet): Boolean {
        if (onglets.liste.size <= 1) return false
        if (ongletOccupe()) return true
        val etaitActif = o === onglets.actif
        if (!etaitActif) rangerOnglet()
        else o.brouillon = ""
        if (!onglets.fermer(o)) return false
        if (etaitActif) montrerOnglet() else { majOnglets(); garderSaisie() }
        ecrire(t("ong.ferme", "nom" to o.nom()), 0xFF9A9AB0.toInt())
        return true
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
        val h = onglets.actif.historique
        if (h.isEmpty()) {
            ecrire(t("term.historique_vide"), 0xFF9A9AB0.toInt())
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

    /** (le mot en cours, les noms possibles) : un nom de commande (1er mot) ou un fichier/dossier (« nid/ »). */
    private fun candidats(texte: String): Pair<String, List<String>> {
        val debutMot = texte.lastIndexOf(' ') + 1
        val mot = texte.substring(debutMot)
        val candidats: List<String>
        if (debutMot == 0) {
            candidats = Regles.LEXIQUE.map { it.cmd }.filter { it.startsWith(mot) }.distinct()
        } else {
            val dossierMot = mot.substringBeforeLast('/', "")
            val prefixe = mot.substringAfterLast('/')
            val base = when {           // les chemins du Terminaworld (Racine.kt) : / est la Racine simulée
                dossierMot.isEmpty() && mot.startsWith("/") -> Racine.reel(jeu.home, "/")
                dossierMot.isEmpty() -> shell.dossier
                dossierMot.startsWith("~") || dossierMot.startsWith("/") || dossierMot.startsWith("..") ->
                    Racine.reel(jeu.home, Racine.resoudre(shell.virtuel(), dossierMot))
                else -> File(shell.dossier, dossierMot)
            }
            val avant = if (mot.contains('/')) mot.substringBeforeLast('/') + "/" else ""
            candidats = (base.listFiles()?.toList() ?: emptyList())
                .filter { it.name.startsWith(prefixe) && (prefixe.startsWith(".") || !it.name.startsWith(".")) }
                .sortedBy { it.name }
                .map { avant + it.name + if (it.isDirectory) "/" else "" }
        }
        return mot to candidats
    }

    /** Complète le dernier mot : un nom de commande (1er mot) ou un fichier/dossier. */
    private fun completer() {
        val texte = saisie.text.toString()
        val debutMot = texte.lastIndexOf(' ') + 1
        val (mot, candidats) = candidats(texte)
        when {
            candidats.isEmpty() -> ecrire(t("term.tab_rien", "mot" to mot), 0xFF9A9AB0.toInt())
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
            "no such file" in s || "dossier introuvable" in s || (Regles.premierMot(ligne) == "cd" && s.isNotBlank() && shell.code != 0) ->   // I6 : `cd -` affiche le lieu
                t("term.err.introuvable")
            "permission denied" in s ->
                t("term.err.refuse")
            "read-only file system" in s -> t("term.err.lecture_seule")
            "not found" in s && Regles.premierMot(ligne).isNotEmpty() -> {
                jeu.animer("confus")
                // P2-10 : une faute collée (`cdvestibule`, `ls-a`, `cd/`) ou des majuscules (`PWD`) : la bonne commande
                val brut = ligne.trim().split(Regex("\\s+"))[0]
                val colle = Verif.collee(brut)
                val egal = Regex("^([A-Za-z_]\\w*)\\s+=").find(ligne.trim())?.groupValues?.get(1)
                when {
                    egal != null -> t("core.inconnue.egal", "cmd" to egal).also { Sons.marquer("erreur_presque") }   // nom = Pixel : des espaces autour du =
                    brut != brut.lowercase() && Verif.collee(brut.lowercase()) == null && brut.lowercase() in Verif.MOTS_CONNUS ->
                        t("core.inconnue.casse", "cmd" to brut, "proche" to brut.lowercase()).also { Sons.marquer("erreur_presque") }
                    colle != null -> t("core.inconnue.proche", "cmd" to brut, "proche" to colle).also { Sons.marquer("erreur_presque") }
                    // I9 : `pwd,` (une virgule collée) → pwd
                    brut.trimEnd(',', '.', ';', ':', '!', '?').let { it != brut && it.lowercase() in Verif.MOTS_CONNUS } ->
                        t("core.inconnue.proche", "cmd" to brut, "proche" to brut.trimEnd(',', '.', ';', ':', '!', '?')).also { Sons.marquer("erreur_presque") }
                    else -> t("term.err.inconnue", "cmd" to Regles.premierMot(ligne)).also { Sons.marquer("erreur_douce") }
                }
            }
            "file exists" in s -> t("term.err.existe")
            "is a directory" in s -> t("term.err.est_dossier")
            "not a directory" in s -> t("term.err.pas_dossier")
            "not empty" in s -> t("term.err.pas_vide")
            "missing" in s || "needs " in s || "usage:" in s ->
                t("term.err.manque")
            "unknown option" in s || "invalid option" in s || "bad option" in s ->
                t("term.err.option")
            "operation not permitted" in s -> t("term.err.interdit")
            else -> null
        }
    }

    /**
     * Entrée. Une commande tourne encore : la ligne tapée est mise de côté (dans CET onglet) et lancée juste après,
     * jamais collée à la suivante. attente : une ligne mise de côté qu'on lance maintenant (la saisie n'y est pour rien).
     */
    private fun valider(attente: Onglet.Attente? = null) {
        if (enCours) {
            val l = saisie.text.toString().trim()
            if (l.isEmpty()) return
            val o = onglets.actif
            if (o.mettreDeCote(l, colle, rappel != null && l == rappel)) {
                remplacerSaisie("")
                colle = false; rappel = null; posHisto = -1
                ecrire("⏳ " + t("ong.attente", "cmd" to l), 0xFF9A9AB0.toInt())
            } else ecrire(t("ong.occupe", "nom" to o.nom()), 0xFF9A9AB0.toInt())
            android.util.Log.i("TG", "mise de côté : $l")
            return
        }
        val ligne = attente?.ligne ?: saisie.text.toString().trim()
        val etaitColle = attente?.colle ?: colle
        val etaitRappel = attente?.rappel ?: (rappel != null && ligne == rappel)
        // une ligne mise de côté ne touche pas à ce que l'enfant est en train de taper
        fun vider() { if (attente == null) saisie.setText("") }
        if (attente == null) {
            colle = false
            rappel = null
            posHisto = -1
        }
        questionBug?.let { q ->                       // idée 76 : « Tu es un adulte ? » avant le rapport
            questionBug = null
            vider()
            ecrire("> $ligne", 0xFF5FD787.toInt())
            if (ligne.trim() == q.second) ouvrirCarteBug() else ecrire(t("bug.non"), Commandes.ROSE)
            return
        }
        questionAdulte?.let { q ->                    // « Tout afficher » : la réponse des grands
            questionAdulte = null
            vider()
            ecrire("> $ligne", 0xFF5FD787.toInt())
            if (ligne.trim() == q.second) {
                Apparence.toutAfficher(jeu, true)
                jeu.sauver()
                ecrire("🔓 " + t("app.tout.ok"), Commandes.ROSE)
                espace?.let { it.etat.apparence(it.maintenant()); it.requestLayout(); it.invalidate() }
            } else ecrire(t("app.tout.non"), Commandes.ROSE)
            return
        }
        confirmerParent?.let { args ->               // « parent temps 45 » : la phrase d'un adulte (comme debloquer)
            confirmerParent = null
            vider()
            ecrire("> $ligne", 0xFF5FD787.toInt())
            if (Apprendre.phraseAdulte(ligne)) { ecrire(Apprendre.reglerTemps(jeu, args.drop(1)), Commandes.ROSE); jeu.sauver() }
            else ecrire(t("apr.parent.non"), Commandes.ROSE)
            rafraichir()
            return
        }
        if (confirmerDeblocage) {                    // « debloquer tout » : oui / non (dans les 14 langues)
            confirmerDeblocage = false
            vider()
            ecrire("> $ligne", 0xFF5FD787.toInt())
            if (MenuParties.oui(ligne)) {
                Intro.toutDebloquer(jeu)
                jeu.sauver()
                ecrire(t("deb.tout.ok"), Commandes.ROSE)
            } else ecrire(t("deb.tout.non"), Commandes.ROSE)
            rafraichir()
            return
        }
        if (!jeu.existe && ecranParent > 0 && !menu.ouvert) {    // idée 1 : « Qui est avec toi ? » (1 ou 2, Entrée)
            vider()
            val r = ligne.trim().lowercase()
            actionIntro(when {
                ligne.isEmpty() -> introVue?.actionFocus() ?: if (ecranParent == 1) "seul" else "parti"
                ecranParent == 1 && (r == "2" || r in MenuParties.mots("ad.parent.mots_adulte")) -> "adulte"
                ecranParent == 1 -> "seul"
                else -> "parti"
            })
            return
        }
        if (menuVue != null && ligne.isEmpty() && attente == null) { actionMenu(menuVue?.actionFocus() ?: "1"); return }   // idée 79
        if (menuVue != null) fermerMenuVue()
        if (perduVue != null && attente == null) {             // idée 6 : Entrée ferme la carte (ou ramène au camp)
            val a = perduVue?.actionFocus()
            fermerPerdu()
            if (ligne.isEmpty()) { if (a == "camp") remplacerSaisie("cd ~"); return }
        }
        if (!jeu.existe && nomPropose != null && ligne.isEmpty() && !menu.ouvert) {   // Entrée : le nom est confirmé
            naitre(nomPropose!!)
            return
        }
        if (!jeu.existe && ecranIntro > 0 && ligne.isEmpty() && !menu.ouvert) {   // Entrée : l'écran suivant
            actionIntro(introVue?.actionFocus() ?: "suivant")
            return
        }
        if (jeu.existe && ligne.isEmpty() && Intro.aMontrer(jeu) != null) {     // Entrée : l'écran de présentation est lu
            actionIntro("ok")
            return
        }
        if (jeu.existe && ligne.isNotEmpty() && Intro.aMontrer(jeu) != null) {   // taper une commande le referme
            if (Intro.aMontrer(jeu) == "fermer") AideDouce.marquerFermer(jeu)
            Intro.lu(jeu)
        }
        if (menu.ouvert && !enCours) {              // une réponse au menu des parties (rien n'est mangé)
            vider()
            ecrire("> $ligne", 0xFF5FD787.toInt())
            val r = menu.repondre(ligne)
            if (menu.quitter) { menu.quitter = false; finish(); return }      // idée 79 : « q » / Quitter
            if (r != null) {
                ecrire(r, Commandes.ROSE)
                rafraichir()
                return
            }
            if (ligne.isEmpty()) return
        }
        if (ligne.isNotEmpty() && jeu.existe && jeu.historique.lastOrNull() != ligne) {
            jeu.historique.add(ligne)
            while (jeu.historique.size > 50) jeu.historique.removeAt(0)
        }
        if (jeu.existe) onglets.actif.noter(ligne)          // ↑ ↓ : l'historique de CET onglet
        vider()
        if (ligne.isEmpty() || enCours) return

        if (!jeu.existe) {
            // P1-6 : un mot tapé sur les premiers écrans fait passer à la suite (« jouer » n'est pas un nom) ; ensuite
            // le nom est demandé, puis confirmé (oui / Entrée), ou remplacé par un autre mot
            val nb = introVue?.nbEcrans() ?: 4
            if (ecranIntro in 1 until nb && nomPropose == null) { actionIntro("suivant"); return }
            val p = nomPropose
            if (p != null && MenuParties.non(ligne)) {          // v3 (I14) : « non » → on redemande le nom
                nomPropose = null
                ecrire("> $ligne", 0xFF5FD787.toInt())
                ecrire(t("intro.nom.tel"), Commandes.ROSE)
                return
            }
            if (p == null || !MenuParties.oui(ligne)) {
                nomPropose = Intro.nomPropre(ligne).ifEmpty { null }
                ecrire("> $ligne", 0xFF5FD787.toInt())
                nomPropose?.let { ecrire(t("intro.nom.confirme.tel", "nom" to it), Commandes.ROSE) } ?: ecrire(t("intro.nom.tel"), Commandes.ROSE)
                return
            }
            naitre(p)
            return
        }

        ecrire("${shell.chemin()} $ $ligne", 0xFF5FD787.toInt())
        AideDouce.demandeExplique(ligne)?.let {                 // idée 22 : `ls ?` ou `? ls` (jamais un repas)
            ecrire(AideDouce.ficheCourte(it), Commandes.ROSE)
            return
        }
        when (Regles.premierMot(ligne)) {
            "perdu" -> { ouvrirPerdu(); return }               // idée 6
            "indice" -> {                                      // idée 25 : 3 niveaux, rien n'est retiré
                ecrire(AideDouce.texteDemandeIndice(jeu), 0xFFFFD75F.toInt())
                jeu.sauver()
                rafraichir()
                return
            }
            "clavier" -> {                                     // idée 69 : tout au clavier (on / off)
                when (ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()) {
                    "on", "oui" -> jeu.module("aide_douce").put("clavier", true)
                    "off", "non" -> jeu.module("aide_douce").put("clavier", false)
                }
                jeu.sauver()
                ecrire(t("ad.k.etat", "etat" to t(if (toutAuClavier()) "app.on" else "app.off")), Commandes.ROSE)
                introVue?.clavier = toutAuClavier()
                rafraichir()
                return
            }
            "clear" -> { sortie.text = ""; return }
            "quitter" -> { finish(); return }
            // exit ferme l'onglet ; dans le dernier, il referme le jeu (comme avant les onglets)
            "exit", "logout" -> { if (!fermerOnglet(onglets.actif)) finish(); return }
            "terminal" -> if (ligne.trim().split(Regex("\\s+")).size == 1) { ouvrirOnglet(); return }   // comme `tg terminal` sur PC
            "tg" -> when (ligne.trim().split(Regex("\\s+")).drop(1)) {
                listOf("terminal") -> { ouvrirOnglet(); return }
                listOf("bug") -> { demanderBug(); return }          // comme `tg bug` sur PC
            }
            "bug", "signaler" -> { demanderBug(); return }          // idée 76 : un adulte relit et envoie lui-même
            "parties" -> { ecrire(menu.ouvrir(), Commandes.ROSE); return }
            "langue" -> { ecrire(langue(ligne.trim().split(Regex("\\s+")).getOrNull(1)), Commandes.ROSE); return }
            "partie" -> { ecrire(menu.commande(ligne.substringAfter(' ', "")), Commandes.ROSE); rafraichir(); return }
            "sauvegarde", "backup" -> { sauvegarde(ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()); return }
            "parent" -> {                             // pour les parents : une limite de temps douce (Apprendre.kt, idée 49)
                val args = ligne.trim().split(Regex("\\s+")).drop(1)
                val q = Apprendre.questionParent(args)
                if (q != null) { confirmerParent = args; ecrire(q, Commandes.ROSE) }
                else if (args.firstOrNull()?.lowercase() in setOf("temps", "time")) ecrire(Apprendre.reglerTemps(jeu, emptyList()), Commandes.ROSE)
                else ecrire(t("apr.parent.aide", "cmd" to "parent temps 45"), Commandes.ROSE)
                return
            }
            "debloquer" -> {                          // pour les parents et les tests : tout ouvrir (après confirmation)
                if (ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase() in setOf("tout", "all")) {
                    confirmerDeblocage = true
                    ecrire(t("deb.tout.question"), Commandes.ROSE)
                } else ecrire(t("deb.tout.non"), Commandes.ROSE)
                return
            }
            "espace" -> {                             // l'espace de travail (vue graphique au-dessus du terminal)
                val mot = ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()
                if (mot == "classe" || mot == "class") {
                    if (espace == null) ouvrirEspace(true) else espace?.classe = !(espace?.classe ?: false)
                    jeu.module("espace").put("classe", espace?.classe == true)
                    jeu.sauver()
                } else if (espace == null) ouvrirEspace(false) else fermerEspace()
                return
            }
            "theme", "thème" -> {                     // le thème (espace, bulle, couleurs du terminal)
                val mot = ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()
                if (mot != null && Apparence.choisirTheme(jeu, mot)) {
                    jeu.sauver()
                    themeEcran()
                    espace?.let { it.etat.apparence(it.maintenant()); it.invalidate() }
                    ecrire("🎨 " + t("app.theme.ok", "nom" to t("app.theme.$mot")), Commandes.ROSE)
                } else ecrire(t("app.theme.liste", "liste" to Apparence.ordre().joinToString(" ")), Commandes.ROSE)
                return
            }
            "classe" -> {                             // le mode classe : séance guidée, écran projecteur, place de la classe
                val mots = ligne.trim().split(Regex("\\s+")).drop(1)
                when (mots.firstOrNull()?.lowercase()) {
                    "seance", "séance" -> { ecrire(Seances.commande(jeu, mots.drop(1)), Commandes.ROSE); ecran?.invalidate(); return }
                    "tableau" -> { ouvrirEcran("tableau"); return }
                    "place" -> {
                        val code = mots.getOrNull(1)
                        if (code == null || Place.cle(code) == null) { ecrire(t("classe.place.code_tel"), Commandes.ROSE); return }
                        ouvrirEcran("place")
                        ecran?.client = Place.Client(Classe.lire(code)!!.let { Classe.fabriquer(it.first, it.second) }, Place.profil(jeu),
                            mots.getOrNull(2)?.takeIf { Place.privee(it) })
                        ecrire(t("classe.place.ouverte_tel"), Commandes.ROSE)
                        return
                    }
                    else -> { ecrire(t("classe.tel.aide"), Commandes.ROSE); return }
                }
            }
            "carte" -> if (ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase() in setOf("visite", "visit")) {
                ouvrirEcran("carte")
                if (ligne.contains("sansnom") || ligne.contains("sans-nom")) ecran?.avecNom = false
                return
            }
            "confort", "calme" -> {                   // lecture et confort : taille du texte, police, formes, mode calme
                val mots = ligne.trim().split(Regex("\\s+")).drop(1)
                ecrire(Confort.commande(jeu, if (Regles.premierMot(ligne) == "calme") listOf("calme") + mots.take(1) else mots), Commandes.ROSE)
                appliquerConfort()
                return
            }
            "options", "ranger" -> {                  // les options (thème, disposition, tout afficher), ranger l'espace
                if (espace == null) ouvrirEspace(false, dire = false)
                espace?.let {
                    if (Regles.premierMot(ligne) == "ranger") it.etat.rangement = true else it.etat.options = true
                    it.requestLayout(); it.invalidate()
                }
                return
            }
            "deploie", "déploie" -> {                 // la vue déployée d'une commande (sans la lancer)
                val reste = ligne.trim().substringAfter(' ', "").trim()
                val pas = reste.startsWith("--pas")
                val cmd = reste.removePrefix("--pas").trim().ifEmpty { espace?.modele?.vue?.ligne ?: jeu.historique.dropLast(1).lastOrNull() ?: "" }
                if (cmd.isEmpty()) { ecrire(t("dep.aide"), Commandes.ROSE); return }
                if (espace == null) ouvrirEspace(false, dire = false)
                espace?.onglet("terminal")
                espace?.deployer(cmd, auto = !pas)
                ecrire("▸ " + t("esp.deploie_ok"), 0xFFB284FF.toInt())
                return
            }
            "monde", "world" -> {                     // le monde des biomes (onglet Monde) ; monde effets tous|essentiels|aucun
                val mots = ligne.trim().split(Regex("\\s+")).map { it.lowercase() }
                if (mots.getOrNull(1) == "effets" && mots.getOrNull(2) in Effets.NIVEAUX) {
                    jeu.module("effets").put("niveau", mots[2]); jeu.sauver()
                    ecrire("✨ " + t("efx.regle", "niveau" to t("efx.niveau." + mots[2])), Commandes.ROSE)
                    return
                }
                if (espace == null) ouvrirEspace(false, dire = false)
                espace?.onglet("monde")
                espace?.etat?.relireMonde(true)
                ecrire("🗺 " + t("monde.titre"), Commandes.ROSE)
                return
            }
            "cerveau" -> {                            // le cerveau de ta créature (et forcer un état : cerveau dort)
                if (espace == null) ouvrirEspace(false, dire = false)
                espace?.onglet("cerveau")
                val etat = ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()
                if (etat != null) espace?.cerveau?.forcer(Cerveau.ETATS.firstOrNull { it == etat || Cerveau.nomEtat(it) == etat })
                return
            }
            "lexique" -> {                            // le carnet d'aventure (comme le bouton 📖)
                val non = Intro.bloque(jeu, "lexique")
                if (non != null) ecrire(non, 0xFFFFAF5F.toInt()) else if (lexiqueVue.visibility != View.VISIBLE) basculerLexique()
                return
            }
            "placement", "sansaide" -> {                  // G-13 : le test « je connais déjà », le mode défi sans aide
                val mots = ligne.trim().split(Regex("\\s+"))
                ecrire(Placement.commande(jeu, if (mots[0].lowercase() == "sansaide") mots.drop(1).ifEmpty { listOf("on") } else emptyList()),
                    Commandes.ROSE)
                jeu.sauver()
                rafraichir()
                return
            }
            "aide" -> {
                // P2-7 : coincé ? d'abord la leçon en cours, où la taper, la commande exacte et pourquoi (« aide tout » : la liste)
                val mot2 = ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase()
                if (mot2 in setOf("parents", "parent", "adulte")) { ecrire(AideDouce.conseilsParents(), Commandes.ROSE); return }   // idée 1
                if (mot2 !in setOf("tout", "all")) {
                    ecrire(Histoire.aideLecon(jeu), Commandes.ROSE)
                    return
                }
                ecrire(t("term.aide", "ctf" to Mots.terme("ctf", Mots.palier(jeu), true)) + "\n" + t("ong.aide", "max" to Onglets.MAX) + "\n" + t("term.aide.maison") + "\n" + t("env.aide.tel") + "\n" + t("cr.aide.tel") + "\n" + t("ent.aide.tel") + "\n\n" + t("app.licences"))
                return
            }
        }
        // plusieurs onglets : la commande part du dossier de CET onglet (pas de celui de la dernière commande d'un autre)
        Maison.placer(jeu, shell.dossier)
        // la photo du terrain avant la commande : ce qui change VRAIMENT se verra dans le monde des biomes (Effets.kt)
        val photoAvant = if (espace != null && espace?.etat?.niveauEffets() != "aucun") try { Effets.photo(jeu.terrain, shell.dossier) } catch (e: Exception) { null } else null
        // Commandes intégrées (téléphone, créature) : réponse immédiate
        val interne = commandes.executer(ligne)
        if (interne != null) {
            // la carte qui pousse s'ouvre à la place de l'observatoire (le texte reste en secours)
            if (interne.carte && espace != null) { espace?.onglet("carte"); ecrire(interne.texte, interne.couleur, interne.petit) }
            else if (interne.carte && ouvrirCarte()) ecrire("🗺 " + Carte.titre(jeu), interne.couleur)
            else ecrire(interne.texte, interne.couleur, interne.petit)
            if (Regles.premierMot(ligne) == "album" && ligne.trim().split(Regex("\\s+")).size == 1) montrerCreature("album")
            if (lexiqueVue.visibility == View.VISIBLE) basculerLexique()
            interne.aller?.let {
                shell.dossier = it
                majObservatoire(ligne)
            }
            if (interne.sonMenu) handler.post { reglagesSon() }
            try { apresCommande(ligne, etaitColle, etaitRappel) } catch (e: Exception) { android.util.Log.e("TG", "après « $ligne »", e) }
            try { espace?.effets(ligne, photoAvant, 0, interne.texte, shell.dossier) } catch (e: Exception) { android.util.Log.e("TG", "effets", e) }
            if (interne.saut > saut) saut = interne.saut
            return
        }

        // pendant un mini-combat, une commande absente du téléphone ou qui ne s'arrête pas seule (ping sans -c, git…)
        // compte comme un coup sans être lancée
        val mot = Regles.premierMot(ligne)
        if (Combat.enCours(jeu) && mot in Combat.SANS_SHELL) {
            ecrire(t("dressa.combat.coup", "cmd" to mot), 0xFF9A9AB0.toInt())
            try { apresCommande(ligne, etaitColle, etaitRappel, null) } catch (e: Exception) { android.util.Log.e("TG", "après « $ligne »", e) }
            return
        }

        // sleep N : une vraie sieste (le vrai shell la fait), avec l'animation « dort » ; le shell coupe à 20 s
        Envies.dureeSieste(ligne)?.let { s ->
            if (s > Envies.SIESTE_MAX_TEL) {
                ecrire(t("env.sieste.trop", "max" to Envies.SIESTE_MAX_TEL), 0xFFFFAF5F.toInt())
                return
            }
            ecrire(t("env.sieste.debut", "nom" to jeu.nom, "s" to (if (s == Math.floor(s)) s.toLong().toString() else s.toString())), 0xFF9A9AB0.toInt())
            jouerCreature("dort")
        }

        cacherPuceBug()                           // idée 76 : la ligne « Signaler ce souci » s'en va à la commande suivante
        enCours = true
        invite.alpha = 0.4f
        android.util.Log.i("TG", "commande : $ligne")
        exec.execute {
            var panne: Throwable? = null
            val resultat = try { shell.executer(ligne) } catch (e: Exception) { android.util.Log.e("TG", "shell", e); panne = e; t("term.erreur", "msg" to e.message) }
            handler.post {
                if (resultat.isNotEmpty()) ecrire(resultat)
                panne?.let { panneDuJeu(it, ligne, dire = false) }      // idée 76 : la ligne « 🐞 Signaler ce souci »
                // pendant l'œuf : une commande inconnue, et le petit tutoriel dit que ce n'est pas grave
                if (Intro.enCours(jeu) && "not found" in resultat.lowercase()) Intro.signalerErreur(jeu)
                // il manque quelque chose (mkdir tout seul…) : la commande à taper, en bulle et ici ; sinon l'explication de l'erreur
                (Exemples.apres(jeu, ligne, resultat) ?: expliquer(resultat, ligne))?.let { ecrire(it, 0xFFFFAF5F.toInt()) }
                val change = majObservatoire(ligne)
                if (lexiqueVue.visibility == View.VISIBLE) basculerLexique()
                if (resultat.isEmpty() && !change && shell.code == 0) {      // C3 : pas de « ✓ Fait » après un échec
                    ecrire(t("term.fait"), 0xFF9A9AB0.toInt())
                }
                try {
                    apresCommande(ligne, etaitColle, etaitRappel, shell.code)
                    espace?.effets(ligne, photoAvant, shell.code, resultat, shell.dossier)
                } catch (e: Exception) {
                    android.util.Log.e("TG", "après la commande « $ligne »", e)
                    panneDuJeu(e, ligne)
                } finally {
                    enCours = false
                    invite.alpha = 1f
                    handler.post { lancerAttente() }
                }
            }
        }
    }

    /**
     * Ctrl+C (la touche ^C, ou Ctrl+C sur un clavier branché) : arrête la commande qui tourne ET oublie les commandes
     * en attente de cet onglet ; sans commande en cours, efface la ligne tapée (comme dans un vrai terminal).
     */
    private fun ctrlC() {
        val o = onglets.actif
        val oubliees = o.attente.size
        o.attente.clear()
        val arretee = enCours && shell.interrompre()
        if (!arretee) {
            ecrire("${shell.chemin()} $ ${saisie.text}^C", 0xFF5FD787.toInt())
            remplacerSaisie("")
        }
        if (arretee || oubliees > 0) ecrire(t("ong.ctrlc", "n" to oubliees), 0xFF9A9AB0.toInt())
        colle = false; rappel = null; posHisto = -1
        saisie.requestFocus()
    }

    /** La commande d'avant a fini : la prochaine ligne mise de côté (dans l'onglet affiché) est lancée. */
    private fun lancerAttente() {
        if (enCours) return
        val a = onglets.actif.prochaineAttente() ?: return
        valider(a)
        if (!enCours) handler.post { lancerAttente() }        // une commande du jeu (immédiate) : la suivante tout de suite
    }

    /** L'œuf a son nom (confirmé) : la partie commence. */
    private fun naitre(nom: String) {
        nomPropose = null
        saisie.setText("")
        jeu.nom = nom
        jeu.shiny = false   // le compagnon ne naît jamais shiny (pas de rareté)
        Intro.nouvellePartie(jeu)              // l'œuf seul, sa liste de commandes ; le jeu s'ouvre petit à petit
        choixParent?.let { AideDouce.a(jeu).put("parent", it) }     // idée 1 : le choix reste sur l'appareil
        jeu.extra.put("born", System.currentTimeMillis() / 1000)      // la date d'éclosion (carte de visite)
        ecranIntro = 0
        jeu.log(t("app.oeuf_apparu", "trait" to Regles.nomTrait(jeu.trait)))
        jeu.dire(t("term.toc_toc"), 10)
        jeu.sauver()
        WidgetCreature.majTous(this)
        ecrire(t("intro.ou.tel") + "\n" + t("intro.astuce.0"), Commandes.ROSE)
        rafraichir()
    }

    private fun verrouillerFocus(v: View) {
        if (v !== saisie && v !is android.widget.EditText) {
            v.isFocusable = false
            v.isFocusableInTouchMode = false
        }
        if (v is android.view.ViewGroup) for (i in 0 until v.childCount) verrouillerFocus(v.getChildAt(i))
    }

    /** Lancé depuis l'icône de l'appli (pas depuis le widget ni une notification). */
    private fun lanceur(i: android.content.Intent?): Boolean =
        i?.action == android.content.Intent.ACTION_MAIN && i.hasCategory(android.content.Intent.CATEGORY_LAUNCHER)

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        if (lanceur(intent) && !menu.ouvert && !Parties.aucune(this)) ouvrirMenu()
        essais(intent)
        rafraichir()
        saisie.requestFocus()
        handler.postDelayed({ commandeExterne(intent) }, 200)
    }

    /** Une commande tapée dans le mini-terminal de l'île (BulleService) : lancée ici, comme si l'enfant l'avait tapée. */
    private fun commandeExterne(i: android.content.Intent?) {
        val c = i?.getStringExtra("tg_commande")?.trim() ?: return
        i.removeExtra("tg_commande")
        if (c.isEmpty() || !jeu.existe || enCours || menu.ouvert) return
        saisie.setText(c)
        valider()
    }

    /**
     * Réglages réservés aux tests automatiques (lancés par adb, impossibles depuis l'appli) :
     *   --es essai_dressage abyssor        fait apparaître ce monstre
     *   --es essai_equipe abyssor:adulte   donne une bestiole dressée à ce stade (bebe, enfant, ado, adulte, ancien)
     */
    private fun essais(i: android.content.Intent?) {
        if (i == null || !jeu.existe) return
        i.getStringExtra("essai_dressage")?.let { nom ->
            Bestiaire.espece(nom)?.let { e ->
                jeu.module("dressage").remove("en_cours")
                java.io.File(jeu.terrain, e.zone).mkdirs()
                Dressage.commencer(jeu, e)
            }
        }
        i.getStringExtra("essai_equipe")?.let { v ->
            val (nom, stade) = (v.split(":") + "enfant").let { it[0] to it[1] }
            Bestiaire.espece(nom)?.let { e ->
                val ind = Bestiaire.individu(e, false, e.zone).put("stade", if (stade == "finale") "ancien" else stade).put("xp", 0)
                Explo.captures(jeu).put(ind)
                Explo.collection(jeu).put(e.nom, Explo.collection(jeu).optInt(e.nom) + 1)
                jeu.module("equipe").put("active", ind.getString("id"))
            }
        }
        jeu.sauver()
    }

    /** code : le code de sortie (0 pour une commande du jeu, Shell.code pour le shell, null si inconnu). */
    private fun apresCommande(ligne: String, etaitColle: Boolean, etaitRappel: Boolean = false, code: Int? = 0) {
        val etapeAvant = jeu.lecon to jeu.etape
        val campAvant = Intro.enCours(jeu) && Intro.faits(jeu).isEmpty()
        val premierLs = !etaitColle && AideDouce.apresCommande(jeu, ligne, code == null || code == 0) == "premier_ls"
        val sonAvant = Sons.resume(jeu)
        // le tour de jeu (créature, terrain, leçons, défi, dressage et combat, troupe, attirance, monstres) : voir Tour.kt
        val tour = Tour.apresCommande(jeu, ligne, etaitColle, etaitRappel, cwd = shell.dossier, code = code)
        try {
            espace?.let { it.rafraichir(code); it.deployer(ligne) }
            // une étape de leçon réussie avec une commande composée : la ligne des blocs et l'astuce (comme sur PC)
            if ((jeu.lecon to jeu.etape) != etapeAvant && code == 0 && Deploie.composee(ligne)) {
                ecrire("▸ " + t("dep.recap") + " " + Deploie.compacte(Deploie.blocs(ligne)), 0xFFB284FF.toInt())
                ecrire("▸ " + t("dep.astuce", "cmd" to "deploie $ligne"), 0xFF9A9AB0.toInt())
            }
        } catch (e: Exception) { android.util.Log.e("TG", "espace", e) }
        val mange = tour.mange
        for ((m, c) in tour.messages) ecrire(m, c)
        Maison.dernierePousse?.let { ecrire(it, 0xFF9A9AB0.toInt()); Maison.dernierePousse = null }   // 🗺 la carte a poussé : + …
        carteVue?.rafraichir()
        if (tour.saut > saut) saut = tour.saut
        Donjon.verifier(jeu, shell.dossier, ligne)?.let { r ->
            ecrire(r.texte, 0xFFFFD787.toInt())
            r.aller?.let { shell.dossier = it; majObservatoire(null) }
        }
        // au plus un son de retour (Sons.kt, si les réglages le veulent) ; à la première éclosion : « Tu veux m'entendre ? »
        Sons.apresTour(jeu, sonAvant, Sons.resume(jeu), code)?.let { q -> handler.postDelayed({ demanderSon(q) }, 1500) }
        jeu.sauver()
        Apprendre.diplomeAMontrer(jeu)?.let { montrerDiplome(it) }   // l'examen réussi : le diplôme et ses deux boutons
        WidgetCreature.majTous(this)
        if (mange) saut = maxOf(saut, 4)
        rafraichir()
        lancerAnimation()
        if (premierLs) premierLs(court = campAvant && Intro.faits(jeu).isNotEmpty())   // idée 2 (après le camp, plus courte)
        if (Recensement.aUnCompte(jeu) && Regles.premierMot(ligne) !in setOf("sync", "compte")) {
            commandes.sync(forcer = false, silencieux = true)
        }
    }

    /** Le diplôme (idée 30) : l'image, « Enregistrer l'image » (dans les images du téléphone) et « Imprimer ». */
    private fun montrerDiplome(chap: String) {
        val b = try { ApprendreDessin.diplome(jeu, chap) } catch (e: Exception) { return }
        val iv = ImageView(this).apply { setImageBitmap(b); setAdjustViewBounds(true) }
        android.app.AlertDialog.Builder(this).setTitle("🎓 " + t("apr.diplome.titre")).setView(iv)
            .setPositiveButton(t("apr.tel.enregistrer")) { _, _ ->
                ecrire(if (ApprendreDessin.enregistrer(this, b, chap)) t("apr.tel.enregistre") else t("apr.exam.diplome_ecrit",
                    "chemin" to "~/${jeu.terrain.name}/diplome_$chap.png"), Commandes.ROSE)
            }
            .setNeutralButton(t("apr.tel.imprimer")) { _, _ -> try { ApprendreDessin.imprimer(this, b, chap) } catch (e: Exception) { android.util.Log.e("TG", "impression", e) } }
            .setNegativeButton("✕", null)
            .show()
    }

    /**
     * Mise en forme spéciale : ¤id:variante:stade*teinte+~n¤ = dessin d'une bestiole (voir Bestiaire.balise :
     * * = shiny avec sa teinte, + = grand portrait, ~n = aura de rareté, !graine = glitch), §texte§ = écriture
     * arc-en-ciel (RGB).
     */
    /** Un portrait peint d'une bestiole glitch : la teinte shiny cuite dans l'image d'abord, puis l'effet
     *  (un pixel de créature ≈ largeur / 48, comme sur le site). */
    private fun glitchPortrait(b: android.graphics.Bitmap, teinte: Double?, g: Glitch.Spec): android.graphics.Bitmap = try {
        val base = if (teinte == null) b else android.graphics.Bitmap.createBitmap(b.width, b.height, android.graphics.Bitmap.Config.ARGB_8888).also {
            android.graphics.Canvas(it).drawBitmap(b, 0f, 0f, android.graphics.Paint().apply { setColorFilter(Bestiaire.filtreTeinte(teinte)) })
        }
        Glitch.bitmap(base, g, maxOf(1, Math.round(b.width / 48f)))
    } catch (x: Exception) { b }

    private fun miseEnForme(texte: String, couleur: Int?): SpannableStringBuilder {
        val sb = SpannableStringBuilder()
        val motif = Regex("¤([a-z0-9_]+)(?::([^:¤*+~!]+))?(?::([a-z]+))?(?:\\*([0-9.]*))?(\\+)?(?:~([0-9]))?(?:!([0-9a-f]+))?¤|§([^§]*)§|`([^`\n]+)`|‹(#[0-9a-fA-F]{6})\\|([^›\n]+)›")
        var i = 0
        for (m in motif.findAll(texte)) {
            sb.append(texte, i, m.range.first)
            if (m.groups[10] != null) {                   // ‹#rrggbb|pseudo› : le pseudo coloré par un badge de la Guilde
                val debut = sb.length
                sb.append(m.groupValues[11])
                sb.setSpan(ForegroundColorSpan(android.graphics.Color.parseColor(m.groupValues[10])), debut, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                sb.setSpan(android.text.style.StyleSpan(android.graphics.Typeface.BOLD), debut, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            } else if (m.groups[9] != null) {             // `commande` : en vert (voir Vert.kt)
                val debut = sb.length
                sb.append(m.groupValues[9])
                sb.setSpan(ForegroundColorSpan(Vert.COULEUR), debut, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            } else if (m.groupValues[1] == "badge") {          // ¤badge:famille:grade~étoiles¤ (salle d'entraînement)
                val debut = sb.length
                sb.append("\uFFFC")
                val etoiles = m.groupValues[6].toIntOrNull()        // avec ~n : le badge complet (étoiles, galons)
                val d = android.graphics.drawable.BitmapDrawable(resources, Badges.bitmap(m.groupValues[2], m.groupValues[3], 4, etoiles))
                val dp = resources.displayMetrics.density
                if (etoiles == null) d.setBounds(0, 0, (28 * dp).toInt(), (28 * dp).toInt())
                else d.setBounds(0, 0, (36 * dp).toInt(), (56 * dp).toInt())
                sb.setSpan(android.text.style.ImageSpan(d, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM),
                    debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            } else if (m.groupValues[1] == "picto" || m.groupValues[1] == "ombre") {
                // ¤picto:cmd¤ / ¤picto:cmd:gris¤ : l'image du carnet illustré ; ¤ombre:id¤ : une bestiole pas encore rencontrée
                val bm = if (m.groupValues[1] == "picto") ApprendreDessin.picto(m.groupValues[2], m.groupValues[3] == "gris")
                    else Bestiaire.espece(m.groupValues[2])?.let { ApprendreDessin.ombre(it) }
                if (bm != null) {
                    val debut = sb.length
                    sb.append("\uFFFC")
                    val d = android.graphics.drawable.BitmapDrawable(resources, bm)
                    val px = ((if (m.groupValues[1] == "picto") 36 else 40) * resources.displayMetrics.density).toInt()
                    d.setBounds(0, 0, px, px * bm.height / maxOf(1, bm.width))
                    sb.setSpan(android.text.style.ImageSpan(d, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM), debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            } else if (m.groupValues[1].isNotEmpty()) {
                val e = Bestiaire.espece(m.groupValues[1])
                if (e != null) {
                    val debut = sb.length
                    sb.append("\uFFFC")
                    val vid = m.groupValues[2].ifEmpty { "classique" }
                    val stade = m.groupValues[3].ifEmpty { "adulte" }
                    val shiny = m.groups[4] != null
                    val teinte = m.groupValues[4].toDoubleOrNull() ?: 0.5
                    val grand = m.groupValues[5] == "+"
                    // grand : le portrait peint (ou la version détaillée faite main d'Abyssor)
                    val detail = if (!grand) null else Bestiaire.portrait(e, vid, stade)
                        ?: (if (Animations.dispo(e.id)) Animations.detaille(e.id, stade) else null)
                    // l'aura de rareté autour des petits dessins (troupe, collection) : la bestiole garde sa taille
                    val aura = if (detail == null) Aura.deCode(m.groupValues[6].toIntOrNull()) else null
                    // glitch (!graine) : l'effet au repos (style A), après la teinte shiny
                    val glitch = Glitch.repos(m.groupValues[7].ifEmpty { null })
                    val petit = detail?.let { if (glitch == null) it else glitchPortrait(it, if (shiny) teinte else null, glitch) }
                        ?: Bestiaire.bitmap(e, shiny, 4, stade, vid, teinte, glitch)
                    val img = if (aura == null) petit else try { Aura.entourer(petit, 4, aura, garder = true) } catch (x: Exception) { petit }
                    val d = android.graphics.drawable.BitmapDrawable(resources, img)
                    if (detail != null && shiny && glitch == null) d.colorFilter = Bestiaire.filtreTeinte(teinte)
                    val px = ((if (detail != null) 160 else 40) * resources.displayMetrics.density).toInt()
                    d.setBounds(0, 0, px * img.width / maxOf(1, petit.width), px * img.height / maxOf(1, petit.height))
                    sb.setSpan(android.text.style.ImageSpan(d, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM),
                        debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            } else {
                arcEnCiel(sb, m.groupValues[8])
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

    // ------------------------------------------------------------ l'intro (Intro.kt) : écrans du début, œuf, présentations
    /** Montre (ou retire) l'intro dessinée à la place de l'observatoire, selon où en est la partie. */
    private fun majIntro() {
        if (!::contenu.isInitialized) return
        val obs = chemin.parent as View
        val boiteSortie = defile.parent as View
        val ecran = !jeu.existe && ecranIntro > 0 && !menu.ouvert
        val carteIntro = if (jeu.existe) Intro.aMontrer(jeu) else null
        // idée 9 : la croix ✕ s'entoure de jaune pendant l'écran « Tu peux fermer quand tu veux »
        findViewById<TextView>(R.id.fermer).let { x ->
            if (carteIntro == "fermer") { x.background = GradientDrawable().apply { setColor(0); setStroke((3 * resources.displayMetrics.density).toInt(), 0xFFFFD75F.toInt()); cornerRadius = 8 * resources.displayMetrics.density }; x.setTextColor(0xFFFFD75F.toInt()) }
            else { x.background = null; x.setTextColor(0xFF9A9AB0.toInt()) }
        }
        val mode = when {
            !jeu.existe && ecranParent > 0 && !menu.ouvert -> "parent"
            ecran -> "ecran"
            jeu.existe && Intro.enCours(jeu) -> "oeuf"
            carteIntro != null -> "carte"
            else -> null
        }
        if (mode == null) {
            if (introVue != null) saisie.setHint(t("term.saisie"))
            introVue?.let { (it.parent as? LinearLayout)?.removeView(it) }
            introVue = null
            if (carteVue == null) obs.visibility = View.VISIBLE
            boiteSortie.visibility = if (perduVue != null) View.GONE else View.VISIBLE
            return
        }
        val v = introVue ?: run {
            val panneau = obs.parent as LinearLayout
            var i = 0
            while (i < panneau.childCount && panneau.getChildAt(i) !== obs) i++
            val nv = IntroVue(this, jeu, { imagePresentation() }) { actionIntro(it) }
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.topMargin = (8 * resources.displayMetrics.density).toInt()
            panneau.addView(nv, i, lp)
            introVue = nv
            nv
        }
        v.chemin = Racine.HOME              // ce que montre pwd au camp de base (le Terminaworld simulé, Racine.kt)
        // la place de l'intro au-dessus de l'invite (l'illustration rétrécit s'il le faut ; la sortie : 140 dp)
        val fondH = findViewById<View>(R.id.fond).height.takeIf { it > 0 } ?: resources.displayMetrics.heightPixels
        val dOnglets = if (::barreOnglets.isInitialized && (barreOnglets.parent as View).visibility == View.VISIBLE) 36f else 0f
        Intro.hauteurMax = fondH / resources.displayMetrics.density - (if (mode == "ecran" || mode == "parent") 150f else 300f) - dOnglets
        v.clavier = toutAuClavier()
        saisie.setHint(if (v.clavier) "⌨ " + t("ad.k.aide") else t("term.saisie"))     // idée 69 : les touches du clavier
        when (mode) {
            "parent" -> v.montrerParent(ecranParent)
            "ecran" -> v.montrerEcran(ecranIntro.coerceIn(1, v.nbEcrans()))
            "oeuf" -> v.montrerOeuf()
            else -> v.montrerCarte(carteIntro!!)
        }
        obs.visibility = if (lsAnim) View.VISIBLE else View.GONE      // idée 2 : la cinématique du premier ls se voit
        boiteSortie.visibility = if (mode == "ecran" || mode == "parent") View.GONE else View.VISIBLE
    }

    /** Un bouton de l'intro (ou Entrée sur une ligne vide) : suivant, passer, ok. */
    private fun actionIntro(a: String) {
        when (a) {
            "suivant" -> if (!jeu.existe && ecranIntro > 0) ecranIntro = minOf(ecranIntro + 1, introVue?.nbEcrans() ?: 4)
            "passer" -> if (!jeu.existe && ecranIntro > 0) ecranIntro = introVue?.nbEcrans() ?: 4
            "ok" -> if (jeu.existe && Intro.aMontrer(jeu) != null) {
                if (Intro.aMontrer(jeu) == "fermer") AideDouce.marquerFermer(jeu)    // idée 9 : « Te revoilà ! » au retour
                Intro.lu(jeu); jeu.sauver()
            }
            "seul" -> { choixParent = "seul"; ecranParent = 0 }       // idée 1
            "adulte" -> { choixParent = "adulte"; ecranParent = 2 }
            "parti" -> ecranParent = 0
        }
        rafraichir()
        saisie.requestFocus()
    }

    // ------------------------------------------------------------ la carte qui pousse
    private var carteVue: CarteVue? = null
    private var espace: EspaceVue? = null

    // ------------------------------------------------------------ le thème « créature » (3 nov., maquettes validées)
    /** l'album des stades ou le moment d'évolution, par-dessus l'écran (CreatureVue) */
    private var creatureVue: CreatureVue? = null
    /** la carte de l'envie mystère (18) : sa phrase, l'indice, « Un autre indice » et « Plus tard » ; pas de minuteur */
    private var envieBoite: LinearLayout? = null
    private var envieTexte: TextView? = null
    private var evoVue = System.currentTimeMillis() / 1000.0

    private fun montrerCreature(mode: String, de: String? = null) {
        if (!jeu.existe || Creature.stadeCompagnon(jeu) == null) return
        try {
            creatureVue?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }
            val fond = findViewById<android.widget.FrameLayout>(R.id.fond)
            val v = CreatureVue(this, jeu, mode, de) { vue ->
                (vue.parent as? android.view.ViewGroup)?.removeView(vue)
                if (creatureVue === vue) creatureVue = null
                saisie.requestFocus()
            }
            fond.addView(v, android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT))
            creatureVue = v
        } catch (e: Exception) { android.util.Log.e("TG", "créature $mode", e) }
    }

    /** 84 : une évolution vient d'arriver (Creature.stadeChange) : le moment en plein écran, une seule fois. */
    private fun evolutionRecente() {
        val ev = if (jeu.extra.has("creature")) jeu.module("creature").optJSONObject("evolution") else null
        val t = ev?.optDouble("t", 0.0) ?: return
        if (t <= evoVue || System.currentTimeMillis() / 1000.0 - t > 120) return
        evoVue = t
        montrerCreature("evolution", ev.optString("de").ifEmpty { null })
    }

    private fun majEnvie() {
        val e = if (jeu.existe) Creature.envie(jeu) else null
        if (e == null) { envieBoite?.visibility = View.GONE; return }
        val dp = resources.displayMetrics.density
        val boite = envieBoite ?: LinearLayout(this).also { b ->
            b.orientation = LinearLayout.VERTICAL
            b.setBackgroundResource(R.drawable.bulle)
            b.setPadding((10 * dp).toInt(), (8 * dp).toInt(), (10 * dp).toInt(), (8 * dp).toInt())
            val tx = TextView(this).apply { setTextColor(0xFF1E1E2E.toInt()); textSize = 13f }
            b.addView(tx)
            val rangee = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            fun bouton(lib: String, action: () -> Unit) = TextView(this).apply {
                text = lib; textSize = 13f; setTextColor(0xFFFFFFFF.toInt())
                setBackgroundResource(R.drawable.touche)
                setPadding((12 * dp).toInt(), (6 * dp).toInt(), (12 * dp).toInt(), (6 * dp).toInt())
                isFocusable = false
                setOnClickListener { action() }
            }
            rangee.addView(bouton(t("cr.envie.bouton.indice")) { ecrire(Creature.indice(jeu), Commandes.ROSE); jeu.sauver(); rafraichir() })
            rangee.addView(View(this), LinearLayout.LayoutParams((8 * dp).toInt(), 1))
            rangee.addView(bouton(t("cr.envie.bouton.plus_tard")) { ecrire(Creature.indice(jeu, "plus-tard"), Commandes.ROSE); jeu.sauver(); rafraichir() })
            b.addView(rangee, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT).also { it.topMargin = (6 * dp).toInt() })
            val pan = bulle.parent as LinearLayout
            var i = 0
            while (i < pan.childCount && pan.getChildAt(i) !== bulle) i++
            pan.addView(b, i + 1, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).also { it.topMargin = (6 * dp).toInt() })
            envieBoite = b; envieTexte = tx
        }
        val k = e.optInt("k")
        envieTexte?.text = "❓ " + t("cr.envie.titre") + " · " + t("cr.envie.presse") + "\n« " + Creature.texteDevinette(e.getString("id"), 0) + " »" +
            (if (k > 0) "\n" + t("cr.direct.indice", "k" to k) + " : " + Creature.texteDevinette(e.getString("id"), k) else "")
        boite.visibility = View.VISIBLE
    }

    /** L'espace de travail : la vue graphique (île, onglets, créature en direct, vue déployée, carte, cerveau, équipe)
     *  au-dessus du terminal, qui prend tout l'écran. Le terminal, les touches et la saisie restent les mêmes. */
    private fun ouvrirEspace(classe: Boolean, dire: Boolean = true) {
        if (espace != null || !jeu.existe) return
        try {
            val panneau = findViewById<LinearLayout>(R.id.panneau)
            fermerCarte()
            val v = EspaceVue(this, jeu, { shell.dossier }, { shell.chemin() })
            v.classe = classe
            panneau.addView(v, 0, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))
            espace = v
            panneau.getChildAt(1).visibility = View.GONE                    // l'en-tête (créature, titre, ✕)
            (chemin.parent as View).visibility = View.GONE                   // l'observatoire
            val cadre = defile.parent as View
            cadre.layoutParams = (cadre.layoutParams as LinearLayout.LayoutParams).also { it.height = 0; it.weight = 1f }
            panneau.layoutParams = (panneau.layoutParams as android.widget.FrameLayout.LayoutParams).also {
                it.height = android.widget.FrameLayout.LayoutParams.MATCH_PARENT; it.setMargins(0, 0, 0, 0)
            }
            v.ecrireCommande = { c ->                                       // « Y aller » : écrite, pas lancée
                saisie.setText(c)
                saisie.setSelection(c.length)
                saisie.requestFocus()
                ecrire(t("reveil.ecrite"), Commandes.JAUNE)
            }
            v.etat.ouvrirAlbum = { montrerCreature("album") }
            v.demanderQuestion = { q ->
                questionAdulte = v.etat.question
                v.etat.question = null
                ecrire("🔒 " + t("app.tout.question", "q" to q), Commandes.ROSE)
            }
            v.apresConfort = { appliquerConfort() }
            themeEcran()
            sortie.textSize = tailleTerminal(if (classe) 17f else 13f)
            panneau.requestLayout()
            jeu.module("espace").put("ouvert", true).put("classe", classe)
            jeu.sauver()
            jeu.historique.lastOrNull()?.takeIf { Regles.premierMot(it) !in setOf("espace", "deploie", "cerveau") }?.let { v.deployer(it) }
            Sons.suivre(jeu, !classe)
            if (dire) ecrire(t("esp.tel.ouvert"), Commandes.ROSE)
            majDisposition()
        } catch (e: Exception) {
            android.util.Log.e("TG", "espace", e)
        }
    }

    private fun fermerEspace() {
        val v = espace ?: return
        val panneau = findViewById<LinearLayout>(R.id.panneau)
        panneau.removeView(v)
        espace = null
        panneau.getChildAt(0).visibility = View.VISIBLE
        (chemin.parent as View).visibility = View.VISIBLE
        val d = resources.displayMetrics.density
        val cadre = defile.parent as View
        cadre.layoutParams = (cadre.layoutParams as LinearLayout.LayoutParams).also { it.height = (140 * d).toInt(); it.weight = 1f }
        panneau.layoutParams = (panneau.layoutParams as android.widget.FrameLayout.LayoutParams).also {
            it.height = android.widget.FrameLayout.LayoutParams.WRAP_CONTENT; val m = (8 * d).toInt(); it.setMargins(m, m, m, m)
        }
        panneau.setBackgroundResource(R.drawable.panneau)
        findViewById<View>(R.id.fond).setBackgroundColor(0x55000000)
        sortie.textSize = 12f
        jeu.module("espace").put("ouvert", false)
        jeu.sauver()
        Sons.suivre(jeu, false)
        ecrire(t("esp.tel.ferme"), Commandes.ROSE)
        majDisposition()
    }

    /** La première éclosion : la créature demande une fois « Tu veux m'entendre ? » (le jeu reste silencieux sinon). */
    private fun demanderSon(question: String) {
        try {
            android.app.AlertDialog.Builder(this).setTitle(t("son.question")).setMessage(Vert.rendre(question))
                .setPositiveButton(t("son.bouton.oui")) { _, _ -> ecrire(Sons.commande(jeu, "oui"), Commandes.ROSE); jeu.sauver() }
                .setNegativeButton(t("son.bouton.non")) { _, _ -> ecrire(Sons.commande(jeu, "non"), Commandes.ROSE); jeu.sauver() }
                .setCancelable(true).show()
        } catch (e: Exception) { ecrire(question, Commandes.ROSE) }
    }

    /** Réglages > Son (3 nov.) : l'interrupteur son oui / non, de vrais curseurs de volume (musique, cris, réussites)
     *  et « ce soir seulement » (SonsReglages.kt). */
    private fun reglagesSon() {
        try {
            val r = SonsReglages(this, jeu, resources.displayMetrics.density, { ecrire(it, Commandes.ROSE) }) {
                jeu.sauver()
                Sons.suivre(jeu, espace != null && espace?.classe != true)
            }
            val cadreSon = android.widget.ScrollView(this).apply { addView(r.boite) }
            android.app.AlertDialog.Builder(this).setTitle(t("son.reglages")).setView(cadreSon)
                .setPositiveButton("OK", null).show()
        } catch (e: Exception) { }
    }

    /** Ouvre (ou rafraîchit) la carte dessinée à la place de l'observatoire. Faux si elle n'a pas pu s'ouvrir. */
    private fun ouvrirCarte(): Boolean = try {
        carteVue?.rafraichir() ?: run {
            val obs = chemin.parent as View
            val panneau = obs.parent as LinearLayout
            var i = 0
            while (i < panneau.childCount && panneau.getChildAt(i) !== obs) i++
            val v = CarteVue(this, jeu, { Sprites.bitmap(jeu, 1) }) { fermerCarte() }
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, (250 * resources.displayMetrics.density).toInt())
            lp.topMargin = (8 * resources.displayMetrics.density).toInt()
            panneau.addView(v, i, lp)
            obs.visibility = View.GONE
            carteVue = v
        }
        true
    } catch (e: Exception) {
        android.util.Log.e("TG", "carte", e)
        false
    }

    private fun fermerCarte() {
        val v = carteVue ?: return
        (v.parent as? LinearLayout)?.removeView(v)
        (chemin.parent as View).visibility = View.VISIBLE
        carteVue = null
    }

    /** petit : en plus petit (la carte de la maison tient dans la largeur de l'écran). */
    private fun ecrire(texte: String, couleur: Int? = null, petit: Boolean = false) {
        val s = miseEnForme(texte, couleur?.let { Apparence.theme(jeu).texte(it) })
        if (petit) s.setSpan(android.text.style.RelativeSizeSpan(0.85f), 0, s.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        if (sortie.length() > 0) sortie.append("\n")
        sortie.append(s)
        if (sortie.length() > 15000) sortie.text = sortie.text.subSequence(sortie.length() - 12000, sortie.length())
        defile.post { defile.scrollTo(0, sortie.bottom) }
    }

    // ------------------------------------------------------------ langue
    /** Les textes de l'écran qui ne viennent pas du jeu (bouton du lexique, indice de la ligne de saisie). */
    private fun textesFixes() {
        lexiqueBtn.text = if (lexiqueVue.visibility == View.VISIBLE) t("term.btn.terminal") else t("term.btn.lexique")
        if (::auraBtn.isInitialized) auraBtn.contentDescription = t("aura.bouton")
        saisie.setHint(t("term.saisie"))
    }

    /** langue · langue xx : la liste des langues, ou changer de langue (enregistrée dans la sauvegarde). */
    private fun langue(code: String?): String {
        val liste = Langue.LANGUES.entries.joinToString("\n") { (k, v) -> "  langue $k   $v" + if (k == Langue.courante) "  ◀" else "" }
        if (code == null) return t("term.langue.actuelle", "langue" to (Langue.LANGUES[Langue.courante] ?: "")) + "\n" + liste
        val c = Langue.codeValide(code) ?: return t("app.langue.inconnue", "code" to code) + "\n" + liste
        jeu.changerLangue(c)
        jeu.sauver()
        Racine.preparer(jeu.home)                 // la salle des règles (/etc/motd…) parle la nouvelle langue
        textesFixes()
        WidgetCreature.majTous(this)
        if (lexiqueVue.visibility == View.VISIBLE) remplirLexique()
        rafraichir()
        return t("app.langue.ok", "langue" to (Langue.LANGUES[c] ?: c))
    }

    // ------------------------------------------------------------ lexique
    private fun basculerLexique() {
        if (lexiqueVue.visibility == View.VISIBLE) {
            lexiqueVue.visibility = View.GONE
            defile.visibility = View.VISIBLE
            lexiqueBtn.text = t("term.btn.lexique")
        } else {
            remplirLexique()
            lexiqueVue.visibility = View.VISIBLE
            defile.visibility = View.GONE
            lexiqueBtn.text = t("term.btn.terminal")
            lexiqueVue.scrollTo(0, 0)
        }
    }

    /**
     * Le carnet d'aventure : les commandes déjà goûtées en blanc (avec le moment de l'histoire où on les a apprises),
     * jamais tapées en gris, chacune avec un exemple prêt à taper (↳) ; puis les souvenirs (chapitres réveillés,
     * quêtes, titres, objets).
     */
    private fun remplirLexique() {
        val connues = Regles.LEXIQUE.count { it.cmd in jeu.vus && !it.pc }
        val palier = Mots.palier(jeu)
        val sb = SpannableStringBuilder()
        Histoire.h(jeu)
        val entete = t("lex.carnet.titre", "nom" to jeu.nom) + "\n" +
            t("term.lexique.entete", "n" to connues, "total" to Regles.LEXIQUE.size) + "\n" +
            "↳ " + t("lex.exemples.ou", "cmd" to "cd ~/${jeu.terrain.name}") + "\n" +
            "📖 " + t("lex.explique", "ex" to "explique rm") + "\n"
        Vert.ajouter(sb, entete)
        sb.setSpan(ForegroundColorSpan(0xFFFF87FF.toInt()), 0, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        var section = ""
        for (m in Regles.LEXIQUE) {
            val cmd = m.cmd
            val sec = m.section
            val desc = Regles.explication(m, palier)
            if (sec != section) {
                section = sec
                val d = sb.length
                sb.append("\n$sec\n")
                sb.setSpan(ForegroundColorSpan(0xFFAFAFFF.toInt()), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                sb.setSpan(StyleSpan(Typeface.BOLD), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            val pc = m.pc
            val goutee = cmd in jeu.vus && !pc
            val debut = sb.length
            val illustree = !pc && cmd in Apprendre.cmds()          // le carnet illustré (idée 21) : l'image 16 × 16
            val img = if (illustree) ApprendreDessin.picto(cmd, gris = !goutee) else null
            if (img != null) {
                val p0 = sb.length
                sb.append("\uFFFC ")
                val dr = android.graphics.drawable.BitmapDrawable(resources, img)
                val px = (36 * resources.displayMetrics.density).toInt()
                dr.setBounds(0, 0, px, px)
                sb.setSpan(android.text.style.ImageSpan(dr, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM), p0, p0 + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            } else sb.append(if (pc) "🔒 " else if (goutee) "● " else "○ ")
            val debutCmd = sb.length
            sb.append(cmd)
            sb.setSpan(StyleSpan(Typeface.BOLD), debutCmd, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            if (illustree) {                                        // la maîtrise (idée 43) : ●●◉
                val n = Apprendre.niveauMaitrise(Apprendre.a(jeu).getJSONObject("maitrise").optJSONArray(cmd), goutee)
                val r0 = sb.length
                sb.append(" " + if (n == 3) "●●◉" else "●".repeat(n) + "○".repeat(3 - n))
                sb.setSpan(ForegroundColorSpan(if (n == 3) 0xFFFFD75F.toInt() else 0xFF5FD787.toInt()), r0, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            Vert.ajouter(sb, "  $desc")
            val couleur = if (pc) 0xFF45455A.toInt() else if (goutee) 0xFFFFFFFF.toInt() else 0xFF6A6A85.toInt()
            sb.setSpan(ForegroundColorSpan(couleur), debut, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            // le moment de l'histoire où la commande a été apprise (carnet d'aventure)
            val moment = if (goutee) Histoire.quand(jeu, cmd) else ""
            if (moment.isNotEmpty()) {
                val d = sb.length
                sb.append(" · 📖 $moment")
                sb.setSpan(ForegroundColorSpan(0xFFFF87FF.toInt()), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            sb.append("\n")
            // un exemple prêt à taper (depuis le terrain de jeu), voir Exemples.kt
            Exemples.lexique(m)?.let { ex ->
                val e = sb.length
                Vert.ajouter(sb, "    ↳ " + t("lex.exemple", "ex" to ex) + "\n")
                sb.setSpan(ForegroundColorSpan(0xFF87AFD7.toInt()), e, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                if (!pc) {                                          // le bouton qui met l'exemple dans la ligne (sans le lancer)
                    val b0 = sb.length
                    sb.append("    [ ✎ " + t("apr.tel.mettre") + " ]\n")
                    sb.setSpan(object : android.text.style.ClickableSpan() {
                        override fun onClick(w: View) { basculerLexique(); remplacerSaisie(ex) }
                    }, b0 + 4, sb.length - 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    sb.setSpan(ForegroundColorSpan(0xFF5FD787.toInt()), b0, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
            // pour les grands, puis les options (-r = « récursif »…), voir Explique.kt
            if (!pc) {
                val e = sb.length
                Explique.grandCommande(cmd, m.technique)?.let { Vert.ajouter(sb, "    $it\n") }
                Explique.lignesOptions(cmd).forEachIndexed { k, o ->
                    Vert.ajouter(sb, "    " + (if (k == 0) t("lex.options") + " " else "") + o + "\n")
                }
                sb.setSpan(ForegroundColorSpan(0xFF9A9AB0.toInt()), e, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
        }
        // les lieux du Terminaworld (tout le système de fichiers) : image et, pour les grands, la réalité
        val dl = sb.length
        Vert.ajouter(sb, "\n" + Maison.lignesLieux().joinToString("\n") + "\n")
        sb.setSpan(ForegroundColorSpan(0xFFD7D7AF.toInt()), dl, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        val d = sb.length
        Vert.ajouter(sb, Histoire.souvenirs(jeu).joinToString("\n"))
        sb.setSpan(ForegroundColorSpan(0xFFAFAFFF.toInt()), d, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        // les couleurs de ligne ont été posées après : le vert des commandes repasse par-dessus
        for (sp in sb.getSpans(0, sb.length, ForegroundColorSpan::class.java)) {
            if (sp.foregroundColor == Vert.COULEUR) {
                val a = sb.getSpanStart(sp)
                val b = sb.getSpanEnd(sp)
                sb.removeSpan(sp)
                sb.setSpan(sp, a, b, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
        }
        lexiqueTexte.text = sb
        lexiqueTexte.movementMethod = android.text.method.LinkMovementMethod.getInstance()   // « Mettre dans la ligne »
    }

    // ------------------------------------------------------------ fenêtre d'observation
    /** la pièce et son contenu à la dernière commande, gardés par onglet (chaque terminal a son dossier) */
    private var dernierDossier: File?
        get() = onglets.actif.dernierDossier
        set(v) { onglets.actif.dernierDossier = v }
    private var derniersNoms: Set<String>
        get() = onglets.actif.derniersNoms
        set(v) { onglets.actif.derniersNoms = v }

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
        val racine = if (shell.chemin().startsWith("~")) t("term.maison") else "📂 /"
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
        if (visibles.isEmpty() && partis.isEmpty()) chip(t("term.dossier_vide"), 0xFF26263A.toInt(), 0xFF9A9AB0.toInt())
        val caches = elements.size - visibles.size
        if (caches > 0) chip(t("term.caches", "n" to caches), 0xFF26263A.toInt(), 0xFF9A9AB0.toInt())

        var change = false
        if (commande != null) {
            if (dernierDossier != null && !memePiece) {
                ecrire(t("term.porte", "chemin" to shell.chemin()), 0xFFAF87FF.toInt())
                change = true
            } else if (Regles.premierMot(commande) == "cd") {
                ecrire(t("term.deja_dans", "chemin" to shell.chemin()), 0xFFAF87FF.toInt())
                change = true
            }
            for (n in nouveaux.filter { !it.startsWith(".") }) {
                val dossier = File(d, n).isDirectory
                val p = Mots.palier(jeu)
                ecrire(if (dossier) t("term.apparu.dossier", "Quoi" to Mots.terme("un_dossier", p, true), "quoi" to Mots.terme("un_dossier", p), "n" to n)
                    else t("term.apparu.fichier", "Quoi" to Mots.terme("un_fichier", p, true), "quoi" to Mots.terme("un_fichier", p), "n" to n),
                    0xFF5FD787.toInt())
                change = true
            }
            for (n in partis.filter { !it.startsWith(".") }) {
                ecrire(t("term.disparu", "n" to n), 0xFFFF5F5F.toInt())
                change = true
            }
        }
        dernierDossier = d
        derniersNoms = noms
        return change
    }

    // ------------------------------------------------------------ affichage
    private fun rafraichir() {
        // (le nom de la créature n'est jamais coloré par un titre : c'est le PSEUDO qui l'est, voir Entrainement.pseudoColore)
        titre.text = if (!jeu.existe) t("term.oeuf_mysterieux") else if (jeu.shiny) miseEnForme("§${jeu.titre()}§", null) else jeu.titre()
        // les 6 envies, puis l'état de la satiété et la petite assiette du jour (Satiete.kt)
        faim.text = if (jeu.existe) Envies.compact(jeu) + "  " + Envies.emoji(jeu) + "\n" + Satiete.ligneEtat(jeu) + "  🍽 " + Satiete.assiette(jeu)
            else jeu.texteFaim()
        // 2 nov. : la barre bloquée (159/160) dit pourquoi, et pour combien de jours (en vert, juste dessous)
        val attente = if (jeu.existe) Satiete.ligneAttente(jeu) else ""
        xp.text = if (attente.isEmpty()) jeu.texteXp() else android.text.SpannableStringBuilder(jeu.texteXp() + "\n").apply {
            val d = length
            append(attente)
            setSpan(android.text.style.ForegroundColorSpan(0xFF72D88F.toInt()), d, length, android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        // P2-5 : « INT AGI FOR END » n'apparaît qu'avec l'équipe (avant, c'est du jargon pour un enfant de 7 ans)
        stats.text = (if (Intro.ouvert(jeu, "equipe")) jeu.texteStats() else "") + if (Explo.captures(jeu).length() > 0 && Intro.ouvert(jeu, "equipe")) Guide.actuel(jeu).let { "  🧭 ${Guide.ICONES[it.type]} ${it.nom}" } else ""
        invite.text = if (::menu.isInitialized && menu.ouvert) ">" else if (jeu.existe) "${shell.chemin()} $" else t("term.invite_nom")
        val b = jeu.bulleActive()
        bulle.visibility = if (b.isEmpty()) View.GONE else View.VISIBLE
        bulle.text = Vert.rendre(b)
        val defi = Defis.actif(jeu)
        val panneau = Dressage.panneau(jeu, resources, imageCombat)
        // terrain effacé : le bandeau avec la commande à taper reste au-dessus de la leçon
        val l: CharSequence? = panneau ?: if (defi != null) (if (Confort.calme(jeu)) t("conf.defi", "cmd" to Regles.piege(defi)) else t("app.defi", "cmd" to Regles.piege(defi), "s" to Defis.resteSecondes(jeu)))
            else if (jeu.existe && !Intro.enCours(jeu)) listOfNotNull(Terrain.bandeau(jeu), jeu.texteLecon()).joinToString("\n\n").ifEmpty { null } else null
        lecon.visibility = if (l == null) View.GONE else View.VISIBLE
        lecon.text = Vert.rendre(l ?: "")
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
            val hOnglets = if (::barreOnglets.isInitialized) (barreOnglets.parent as View).height + (8 * dp).toInt() else 0
            lecon.maxHeight = maxOf((70 * dp).toInt(), fondH - entete - hBulle - hSortie - hOnglets - ((44 + 52 + 40) * dp).toInt())
        } else lecon.maxHeight = Int.MAX_VALUE
        if (lecon.movementMethod == null) lecon.movementMethod = android.text.method.ScrollingMovementMethod()
        // rien d'autre que la ligne de saisie ne doit pouvoir prendre le focus (sinon ce qu'on tape part dans le vide)
        verrouillerFocus(findViewById(R.id.panneau))
        if (!saisie.hasFocus()) saisie.requestFocus()
        // pendant un dressage, le familier est déjà dans le face-à-face : on allège l'en-tête
        val vis = if (panneau != null) View.GONE else View.VISIBLE
        creature.visibility = vis; faim.visibility = vis; xp.visibility = vis; stats.visibility = vis
        if (::auraBtn.isInitialized) auraBtn.visibility = vis
        // l'intro : l'œuf seul (dessiné dans IntroVue) ; ensuite, chaque élément arrive avec sa présentation (Intro.kt)
        val oeuf = !jeu.existe || Intro.enCours(jeu)
        if (oeuf) { creature.visibility = View.GONE; faim.visibility = View.GONE; xp.visibility = View.GONE; stats.visibility = View.GONE }
        if (jeu.existe && !Intro.ouvert(jeu, "envies")) faim.visibility = View.GONE
        if (::auraBtn.isInitialized && (oeuf || !Intro.ouvert(jeu, "equipe"))) auraBtn.visibility = View.GONE
        (creature.parent as? View)?.visibility = if (oeuf) View.GONE else View.VISIBLE
        // les onglets du terminal : pas pendant l'œuf (un seul écran, le temps d'apprendre à taper), sauf s'il y en a déjà plusieurs
        if (::barreOnglets.isInitialized) (barreOnglets.parent as View).visibility = if (oeuf && onglets.liste.size == 1) View.GONE else View.VISIBLE
        lexiqueBtn.visibility = if (jeu.existe && !oeuf && Intro.ouvert(jeu, "lexique")) View.VISIBLE else View.GONE
        majNuage()
        majIntro()
        majAideDouce()
        majTouches()
        majBoutonAura()
        majEnvie()
        if (lecture == null) creature.setImageBitmap(imageCreature(cligne > 0))
    }

    // ------------------------------------------------------------ courtes animations de la créature
    /**
     * Joue la dernière animation demandée (jeu.animer), si elle est récente et pas encore jouée.
     * À la fin d'un dressage, c'est d'abord le monstre qui joue « victoire » (capturé) ou « ko » (enfui).
     */
    private fun lancerAnimation() {
        Combat.animTroupe?.let { (ind, nom) ->     // le mini-combat : la bestiole de la troupe attaque, gagne ou tombe KO
            Combat.animTroupe = null
            jouerTroupe(ind, nom)
        }
        Dressage.finale?.let { (ind, nom) ->
            Dressage.finale = null
            jeu.anim?.let { animJouee = maxOf(animJouee, it.second) }
            val r = try { Animations.pour(ind, nom, Equipe.stade(ind), 3) } catch (e: Exception) { null }
            if (r != null && r.first.isNotEmpty()) { demarrer(r.first, r.second, 2 * r.first.size); return }
        }
        evolutionRecente()                                    // 84 : le moment d'évolution en plein écran
        val a = jeu.anim ?: return
        if (a.second <= animJouee || System.currentTimeMillis() - a.second > 4000) return
        animJouee = a.second
        if (Intro.numeroAnim(a.first) > 0) {                 // l'œuf remue, brille, se fêle, éclot (IntroVue)
            if (a.first != "eclosion") majIntro()
            introVue?.jouer(a.first)
            return
        }
        jouerCreature(a.first)
    }

    // ------------------------------------------------------------ animations du mini-combat (dans le face-à-face)
    private var imageCombat: android.graphics.Bitmap? = null
    private var animCombat = 0                            // numéro de l'animation en cours (une seule boucle à la fois)

    /** La bestiole de la troupe joue une animation (moteur AnimAuto) à gauche du face-à-face ; après « ko », elle s'endort. */
    private fun jouerTroupe(ind: org.json.JSONObject, nom: String) {
        val r = try { Animations.pour(ind, nom, Equipe.stade(ind), 3) } catch (e: Exception) { null }
        if (r == null || r.first.isEmpty()) return
        val imgs = r.first
        val n = if (nom == "attaque" || nom == "dort") imgs.size else 2 * imgs.size
        if (!Dressage.actif(jeu)) { demarrer(imgs, r.second, n, 3, Aura.palierInd(ind)); return }     // plus de face-à-face : dans l'en-tête
        val numero = ++animCombat
        val pause = 1000L / maxOf(1, r.second)
        var k = 0
        fun pas() {
            if (numero != animCombat) return
            if (k >= n || !Dressage.actif(jeu)) {
                imageCombat = null
                if (nom == "ko" && Dressage.actif(jeu)) jouerTroupe(ind, "dort") else rafraichir()
                return
            }
            imageCombat = imgs[k % imgs.size]
            k++
            Dressage.panneau(jeu, resources, imageCombat)?.let { lecon.text = it }
            handler.postDelayed({ pas() }, pause)
        }
        pas()
    }

    /** La créature joue une animation automatique, courte (≈ 3 s) et sans bloquer la saisie. */
    private fun jouerCreature(nom: String) {
        if (!jeu.existe) return
        guideCapture()?.let { ind ->                 // le guide est une bestiole de l'équipe : c'est elle qui joue
            val r = try { Animations.pour(ind, nom, Equipe.stade(ind), 3) } catch (e: Exception) { null }
            if (r != null && r.first.isNotEmpty()) {
                val n = if (nom == "evolution") r.first.size else minOf(2 * r.first.size, maxOf(r.first.size, 3 * r.second))
                demarrer(r.first, r.second, n, 3, Aura.palierInd(ind))
            }
            return
        }
        val anim = try { Sprites.animation(jeu, nom) } catch (e: Exception) {
            android.util.Log.e("TG", "animation $nom", e); return
        }
        val e = if (jeu.especeCompagnon != null) 3 else 8         // une espèce du bestiaire : plus grande, pixels plus petits
        val imgs = AnimAuto.bitmaps(anim, e, null)
        if (imgs.isEmpty()) return
        val n = if (nom == "evolution") imgs.size else minOf(2 * imgs.size, maxOf(imgs.size, 3 * anim.ips))
        demarrer(imgs, anim.ips, n, e, Aura.palierCompagnon(jeu))
    }

    /** echelle, palier : pour dessiner l'aura de rareté autour des images (0 / null : sans aura). */
    private fun demarrer(imgs: List<android.graphics.Bitmap>, ips: Int, n: Int, echelle: Int = 0, palier: String? = null) {
        val deja = lecture != null
        lecture = imgs
        lectureK = 0
        lectureFin = n
        lectureEchelle = echelle
        lecturePalier = palier
        creature.setImageBitmap(avecAura(imgs[0], echelle, palier, 0))
        val pause = 1000L / maxOf(1, ips)
        if (!deja) handler.postDelayed({ pasAnimation(pause) }, pause)
    }

    private fun pasAnimation(pause: Long) {
        val imgs = lecture ?: return
        lectureK++
        if (lectureK >= lectureFin) {
            lecture = null
            creature.setImageBitmap(imageCreature(false))
            return
        }
        creature.setImageBitmap(avecAura(imgs[lectureK % imgs.size], lectureEchelle, lecturePalier, lectureK))
        handler.postDelayed({ pasAnimation(pause) }, pause)
    }

    /** Petites animations d'ambiance (comme sur PC) : sommeil la nuit, faim, sinon de temps en temps un geste. */
    private fun ambiance() {
        val now = System.currentTimeMillis()
        if (lecture != null || now < ambiance || !jeu.existe || Dressage.actif(jeu)) return
        ambiance = now + AMBIANCE
        val h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        when {
            h >= 21 || h < 7 || Satiete.etat(jeu) == "veille" -> jouerCreature("dort")   // la nuit, ou en veille
            Satiete.affamee(jeu) -> jouerCreature("affame")
            Random.nextDouble() < 0.3 -> jouerCreature(listOf("statique", "salut", "content").random())
        }
    }

    // ------------------------------------------------------------ aura de rareté (Aura.kt) autour de la créature
    private lateinit var auraBtn: TextView
    private var lectureEchelle = 0
    private var lecturePalier: String? = null

    private fun auraVisible() = jeu.existe && Aura.active(jeu)

    /** Le guide, s'il est une bestiole de l'équipe (sinon null : c'est le compagnon sorti de l'œuf). */
    private fun guideCapture(): org.json.JSONObject? =
        if (!jeu.existe || Explo.captures(jeu).length() == 0) null else try { Guide.actuel(jeu).ind } catch (e: Exception) { null }

    private var imageGuide: Pair<String, android.graphics.Bitmap>? = null

    /**
     * La créature de l'en-tête : le GUIDE actuel (la bestiole en tête de l'équipe, à son stade, dans sa variante, avec
     * son aura de rareté), sinon le compagnon sorti de l'œuf ; entourée de son aura si le réglage l'affiche (bouton ✨).
     */
    private fun imageCreature(cligne: Boolean): android.graphics.Bitmap {
        val ind = guideCapture()
        if (ind != null) {
            val cle = listOf(ind.optString("id"), Equipe.stade(ind), ind.optString("variante"), ind.optBoolean("shiny"),
                ind.optBoolean("glitch")).joinToString("|")
            val b = imageGuide?.takeIf { it.first == cle }?.second ?: try {
                Animations.pour(ind, "statique", Equipe.stade(ind), 3)?.first?.firstOrNull()
            } catch (e: Exception) { null }?.also { imageGuide = cle to it }
            if (b != null) return avecAura(b, 3, Aura.palierInd(ind), 2 * frame)
        }
        return avecAura(Sprites.bitmap(jeu, 12, cligne), Sprites.echelle(jeu, 12), if (jeu.existe) Aura.palierCompagnon(jeu) else null, 2 * frame)
    }

    /** Pour les écrans de présentation : la créature (ou son guide) en petit. */
    private fun imagePresentation(): android.graphics.Bitmap? = try {
        guideCapture()?.let { Animations.pour(it, "statique", Equipe.stade(it), 2)?.first?.firstOrNull() } ?: Sprites.bitmap(jeu, 1)
    } catch (e: Exception) { null }

    private fun avecAura(b: android.graphics.Bitmap, echelle: Int, palier: String?, phase: Int): android.graphics.Bitmap {
        if (palier == null || echelle <= 0 || !auraVisible()) return b
        return try { Aura.entourer(b, echelle, palier, phase, eclat = eclatAura()) } catch (e: Exception) { b }
    }

    // ------------------------------------------------------------ la vie au repos (Vie.kt) : 8 images par seconde
    private var ecranVisible = false
    private var vieEnMarche = false
    private var eclatGarde = Aura.ECLAT_NORMAL to 0L

    /** L'éclat de l'aura selon le soin (faim et envies), relu toutes les 2 secondes. */
    private fun eclatAura(): Int {
        val now = System.currentTimeMillis()
        if (now - eclatGarde.second > 2000) eclatGarde = (if (jeu.existe) Aura.eclat(jeu) else Aura.ECLAT_NORMAL) to now
        return eclatGarde.first
    }

    private class VieEcran(val cle: String, val anim: AnimAuto.Anim, val echelle: Int, val teinte: Double?, val palier: String?,
                           val glitch: String? = null)
    private var vieEcran: VieEcran? = null

    /** L'animation de vie de la créature de l'en-tête (le guide de l'équipe, ou le compagnon d'une espèce), ou null
     *  (l'œuf, la créature dessinée d'une ancienne partie, Abyssor et ses animations faites main). */
    private fun vieCourante(): VieEcran? = try { vieCalculee() } catch (e: Exception) { null }

    private fun vieCalculee(): VieEcran? {
        if (!::jeu.isInitialized || !jeu.existe || jeu.stade < 1) return null
        val ind = guideCapture()
        val cle: String
        if (ind != null) {
            cle = listOf("ind", ind.optString("id"), Equipe.stade(ind), ind.optString("variante"), ind.optBoolean("shiny"),
                ind.optBoolean("glitch")).joinToString("|")
            vieEcran?.takeIf { it.cle == cle }?.let { return it }
            val e = Bestiaire.espece(ind.optString("espece")) ?: return null
            if (Animations.dispo(e.id)) return null
            val a = Animations.auto(e, Equipe.stade(ind), ind.optString("variante", "classique"), "statique") ?: return null
            val g = Glitch.de(ind)
            vieEcran = VieEcran(cle, Sprites.recadrer(a, if (g != null) 2 else 0), 3,
                if (ind.optBoolean("shiny")) ind.optDouble("teinte", 0.5) else null, Aura.palierInd(ind), g)
        } else {
            if (jeu.especeCompagnon == null) return null
            cle = listOf("compagnon", jeu.especeCompagnon, jeu.stade, jeu.shiny).joinToString("|")
            vieEcran?.takeIf { it.cle == cle }?.let { return it }
            vieEcran = VieEcran(cle, Sprites.animation(jeu, "statique"), Sprites.echelle(jeu, 12), null, Aura.palierCompagnon(jeu))
        }
        return vieEcran
    }

    /** Une image de vie (clignement, respiration, ondulation, regard) prise sur l'horloge : si le téléphone est lent,
     *  on saute des images au lieu de ralentir ; en pause quand l'écran est éteint (onPause). */
    private fun pasVie() {
        if (!ecranVisible) { vieEnMarche = false; return }
        if (lecture == null && ::jeu.isInitialized && !Dressage.actif(jeu)) {
            try {
                vieCourante()?.let { v ->
                    val tic = (android.os.SystemClock.uptimeMillis() / VIE_PAS).toInt()
                    // glitch : style A au repos, un éclair C de temps en temps (l'horloge murale, comme sur PC)
                    creature.setImageBitmap(avecAura(AnimAuto.bitmap(v.anim, tic, v.echelle, v.teinte, Glitch.maintenant(v.glitch)),
                        v.echelle, v.palier, tic))
                }
            } catch (e: Exception) {
                android.util.Log.e("TG", "vie", e)
            }
        }
        handler.postDelayed({ pasVie() }, VIE_PAS)
    }

    /** Le petit bouton ✨ posé dans le coin de la créature : affiche ou cache son aura (réglage de la partie). */
    private fun creerBoutonAura() {
        val dp = resources.displayMetrics.density
        val parent = creature.parent as android.view.ViewGroup
        val lp = creature.layoutParams
        parent.removeView(creature)                         // la créature est le premier élément de l'en-tête
        val cadre = android.widget.FrameLayout(this)
        cadre.layoutParams = lp
        creature.layoutParams = android.widget.FrameLayout.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.MATCH_PARENT)
        cadre.addView(creature)
        auraBtn = TextView(this).apply {
            text = "✨"
            textSize = 11f
            gravity = Gravity.CENTER
            background = GradientDrawable().apply { setColor(0x55000000); cornerRadius = 11 * dp }
            layoutParams = android.widget.FrameLayout.LayoutParams((22 * dp).toInt(), (22 * dp).toInt(), Gravity.TOP or Gravity.END)
            contentDescription = t("aura.bouton")
            setOnClickListener { basculerAura() }
        }
        cadre.addView(auraBtn)
        parent.addView(cadre, 0)
        majBoutonAura()
    }

    private fun majBoutonAura() {
        if (::auraBtn.isInitialized) auraBtn.alpha = if (Aura.active(jeu)) 1f else 0.35f
    }

    private fun basculerAura() {
        val on = Aura.basculer(jeu)
        jeu.sauver()
        ecrire(if (on) t("aura.on") + "\n" + t("aura.legende") + "\n" + t("aura.soin") else t("aura.off"), Commandes.BLEU)
        rafraichir()
        saisie.requestFocus()
    }

    companion object {
        /** millisecondes entre deux petites animations d'ambiance */
        private const val AMBIANCE = 25_000L
        /** millisecondes entre deux images de vie au repos (8 images par seconde) */
        private const val VIE_PAS = 125L
        /** clés de ce qui est gardé quand l'écran est recréé (onSaveInstanceState) */
        private const val ETAT_ONGLETS = "tg_onglets"
        private const val ETAT_ECRAN = "tg_ecran_"
        /** caractères gardés de chaque écran de terminal (la fin) */
        private const val ECRAN_GARDE = 6000
        /** les deux sélecteurs de fichiers de `sauvegarde` */
        private const val REQ_EXPORTER = 41
        private const val REQ_IMPORTER = 42
        /** idée 76 : « Enregistrer » le rapport d'un souci */
        private const val REQ_BUG = 43
        @Volatile private var gardeInstallee = false
    }

    private fun animer() {
        frame++
        val dp = resources.displayMetrics.density
        creature.translationY = when {
            saut > 0 -> { saut--; -10f * dp * (if (saut % 2 == 0) 1f else 0.6f) }
            frame % 2 == 0 -> -2f * dp
            else -> 0f
        }
        if (lecture != null) {
            // une animation est en cours : pas de clignement
        } else if (ecranVisible && vieCourante() != null) {
            // la vie au repos (pasVie) s'occupe de la créature : clignements, respiration, aura
        } else if (cligne > 0) {
            cligne--
            if (cligne == 0) creature.setImageBitmap(imageCreature(false))
        } else if (Random.nextInt(12) == 0) {
            cligne = 1
            creature.setImageBitmap(imageCreature(true))
        } else if (auraVisible()) {
            creature.setImageBitmap(imageCreature(false))      // l'aura respire
        }
        if (frame % 12 == 0 && !enCours) {        // toutes les ~5 s : la faim, le terrain, les bulles, les leçons « fichiers »
            for ((m, c) in Tour.periodique(jeu, shell.dossier)) ecrire(m, c)
            Sons.suivre(jeu, espace != null && espace?.classe != true)     // la musique : seulement l'espace (Monde, Espace)
            if (Random.nextInt(4) == 0) jeu.parlerSiSilencieux()
            ambiance()
            jeu.sauver()
            rafraichir()
        } else if ((Defis.actif(jeu) != null || Dressage.actif(jeu)) && frame % 2 == 0) {
            if (Dressage.actif(jeu)) Dressage.verifier(jeu, null, false)?.let { ecrire(it, 0xFFFF87FF.toInt()) }
            rafraichir()                          // compte à rebours du défi ou du dressage
        } else if (bulle.visibility == View.VISIBLE && jeu.bulleActive().isEmpty()) {
            rafraichir()
        }
        lancerAnimation()
        handler.postDelayed({ animer() }, 420)
    }

    // ------------------------------------------------------------ les écrans du mode classe (EcransClasse.kt)
    private var ecran: EcranVue? = null

    private fun ouvrirEcran(genre: String) {
        fermerEcran()
        if (!jeu.existe) return
        val racine = findViewById<android.widget.FrameLayout>(R.id.fond) ?: return
        val v = EcranVue(this, jeu, genre) { a -> actionEcran(a) }
        racine.addView(v, android.view.ViewGroup.LayoutParams(android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.MATCH_PARENT))
        ecran = v
    }

    private fun fermerEcran() {
        val v = ecran ?: return
        (v.parent as? android.view.ViewGroup)?.removeView(v)
        ecran = null
    }

    private fun actionEcran(a: String) {
        when {
            a == "tab:fermer" || a == "place:fermer" || a == "carte:fermer" -> fermerEcran()
            a.startsWith("tab:") -> { Seances.agir(jeu, a.removePrefix("tab:")); jeu.sauver() }
            a == "carte:enregistrer" -> ecrire(enregistrerCarte()?.let { t("cv.enregistre") } ?: t("cv.echec"), Commandes.ROSE)
            a == "carte:partager" -> enregistrerCarte()?.let { uri ->
                try {
                    startActivity(android.content.Intent.createChooser(android.content.Intent(android.content.Intent.ACTION_SEND)
                        .setType("image/png").putExtra(android.content.Intent.EXTRA_STREAM, uri)
                        .addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION), t("cv.partager")))
                } catch (e: Exception) { ecrire(t("cv.echec"), Commandes.ROSE) }
            } ?: ecrire(t("cv.echec"), Commandes.ROSE)
        }
    }

    /** La carte de visite dans les images du téléphone (Images/Terminagotchi) ; rien n'est envoyé. */
    private fun enregistrerCarte(): android.net.Uri? = try {
        val b = ecran?.bitmapCarte() ?: throw IllegalStateException()
        val v = android.content.ContentValues()
        v.put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, "terminagotchi_carte_${System.currentTimeMillis() / 1000}.png")
        v.put(android.provider.MediaStore.MediaColumns.MIME_TYPE, "image/png")
        if (android.os.Build.VERSION.SDK_INT >= 29) v.put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/Terminagotchi")
        val uri = contentResolver.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v)
        uri?.let { u -> contentResolver.openOutputStream(u)?.use { b.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it) } }
        uri
    } catch (e: Exception) { null }

    /** La taille du texte du terminal avec le réglage « Taille du texte » (en sp : le téléphone l'agrandit déjà de sa
     *  « Taille de police » ; on ne garde que ce que le réglage du jeu ajoute). */
    private fun tailleTerminal(base: Float): Float {
        val r = Confort.reglages(if (jeu.existe) jeu else null)
        return base * r.zoom / Confort.echelleSysteme.toFloat().coerceAtLeast(0.5f)
    }

    /** Après un changement de confort : l'espace, le terminal et le mode calme suivent. */
    private fun appliquerConfort() {
        Confort.activer(jeu)
        espace?.let { sortie.textSize = tailleTerminal(if (it.classe) 17f else 13f); it.etat.confort(); it.requestLayout(); it.invalidate() }
    }

    // ------------------------------------------------------------ idée 74 : le nuage de synchro
    /** Seulement avec un compte, et seulement hors ligne ou pendant un envoi (« à jour » se lit avec `compte`). */
    private fun majNuage() {
        if (!::chemin.isInitialized) return
        val e = if (jeu.existe) Recensement.nuage(jeu) else null
        if (e?.first == nuageMontre) return
        nuageMontre = e?.first
        if (e == null) { chemin.setCompoundDrawables(null, null, null, null); return }
        val d = resources.displayMetrics.density
        val b = NuageDessin.pilule(e.first, t(if (e.first == "envoi") "rec.nuage.mot.envoi" else "rec.nuage.mot.hors"), d)
        val img = android.graphics.drawable.BitmapDrawable(resources, b)
        img.setBounds(0, 0, b.width, b.height)
        chemin.setCompoundDrawablePadding((6 * d).toInt())
        chemin.setCompoundDrawables(null, null, img, null)
    }

    // ------------------------------------------------------------ idée 75 : tablette en paysage
    /** Deux colonnes (PanneauDeux) seulement sur une tablette (≥ 600 dp de côté, 7 pouces) tournée en paysage, hors
     *  de l'espace de travail ; un téléphone tourné garde la mise en page habituelle. */
    private fun majDisposition() {
        if (!::sortie.isInitialized) return
        val p = findViewById<PanneauDeux>(R.id.panneau) ?: return
        val c = resources.configuration
        val deux = minOf(c.screenWidthDp, c.screenHeightDp) >= 600 &&
            c.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE && espace == null
        val dp = resources.displayMetrics.density
        p.ecart = (16 * dp).toInt()
        p.debutDroite = if (::barreOnglets.isInitialized) barreOnglets.parent as View else defile.parent as View
        if (p.deux == deux) return
        p.deux = deux
        if (espace == null) p.layoutParams = (p.layoutParams as android.widget.FrameLayout.LayoutParams).also {
            it.height = if (deux) android.widget.FrameLayout.LayoutParams.MATCH_PARENT else android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
        }
        p.requestLayout()
    }

    // ------------------------------------------------------------ idée 76 : signaler un souci
    /** Un plantage de l'appli est noté (files/erreurs.log), puis Android fait comme d'habitude. */
    private fun garderLesPannes() {
        if (gardeInstallee) return
        gardeInstallee = true
        val dossier = filesDir
        val avant = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { fil, e ->
            Signaler.noter(dossier, e, "")
            avant?.uncaughtException(fil, e)
        }
    }

    /** Une vraie panne du jeu (pas une commande de l'enfant qui échoue) : notée, puis la ligne à toucher. */
    private fun panneDuJeu(e: Throwable, ligne: String, dire: Boolean = true) {
        Signaler.noter(filesDir, e, ligne)
        Signaler.dernierePanne(filesDir)?.let { jeu.module("bug").put("vu", it[0]) }
        if (dire) ecrire(t("bug.tel.panne"), 0xFFFFAF5F.toInt())
        montrerPuceBug()
    }

    /** Au lancement : une panne notée que l'enfant n'a pas encore vue (l'appli s'était fermée dessus). */
    private fun panneDeLaDerniereFois() {
        val p = Signaler.dernierePanne(filesDir) ?: return
        val m = jeu.module("bug")
        if (m.optString("vu") == p[0]) return
        m.put("vu", p[0])
        if (!jeu.existe) return
        ecrire(t("bug.tel.avant"), 0xFFFFAF5F.toInt())
        montrerPuceBug()
    }

    /** « 🐞 Signaler ce souci » : une petite ligne à toucher, en bas de l'écran du terminal (jusqu'à la commande suivante). */
    private fun montrerPuceBug() {
        val dp = resources.displayMetrics.density
        val v = puceBug ?: TextView(this).also { tv ->
            tv.textSize = 13f
            tv.setTextColor(0xFFFF87FF.toInt())
            val g = GradientDrawable()
            g.cornerRadius = 8 * dp
            g.setColor(0xFF2E2E48.toInt())
            g.setStroke((1.5f * dp).toInt(), 0xFFFF87FF.toInt())
            tv.background = g
            tv.setPadding((10 * dp).toInt(), (5 * dp).toInt(), (10 * dp).toInt(), (5 * dp).toInt())
            tv.setOnClickListener { demanderBug() }
            val lp = android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM or Gravity.START)
            lp.setMargins((8 * dp).toInt(), 0, 0, (6 * dp).toInt())
            (defile.parent as android.widget.FrameLayout).addView(tv, lp)
            puceBug = tv
        }
        v.text = t("bug.tel.signaler")
        v.visibility = View.VISIBLE
        sortie.setPadding(sortie.paddingLeft, sortie.paddingTop, sortie.paddingRight, (8 * dp + 40 * dp).toInt())
        defile.post { defile.scrollTo(0, sortie.bottom) }
    }

    private fun cacherPuceBug() {
        val v = puceBug ?: return
        if (v.visibility == View.GONE) return
        v.visibility = View.GONE
        sortie.setPadding(sortie.paddingLeft, sortie.paddingTop, sortie.paddingRight, (8 * resources.displayMetrics.density).toInt())
    }

    /** `bug` : d'abord la question des grands. */
    private fun demanderBug() {
        cacherPuceBug()
        if (carteBug != null) return
        val q = Apparence.questionAdulte()
        questionBug = q
        ecrire(t("bug.titre") + "  " + t("bug.adulte"), Commandes.ROSE)
        ecrire("🔒 " + t("bug.question", "q" to q.first), Commandes.ROSE)
    }

    private fun champsBug(): Signaler.Champs {
        val c = resources.configuration
        val version = try { packageManager.getPackageInfo(packageName, 0).versionName ?: "?" } catch (e: Exception) { "?" }
        val appareil = "Android ${android.os.Build.VERSION.RELEASE} · " +
            t(if (minOf(c.screenWidthDp, c.screenHeightDp) >= 600) "bug.tel.tablette" else "bug.tel.telephone")
        val ecran = if (espace != null) t("bug.tel.espace")
            else t("bug.tel.ecran", "i" to onglets.liste.indexOf(onglets.actif) + 1, "n" to onglets.liste.size)
        val home = filesDir.parentFile?.absolutePath ?: filesDir.absolutePath
        return Signaler.champs(filesDir, version, appareil, ecran, home,
            listOf(jeu.nom, Recensement.compte(jeu).optString("pseudo")))
    }

    /** La carte : tout ce qui partirait, puis « Ouvrir la page », « Enregistrer », « Annuler ». */
    private fun ouvrirCarteBug() {
        if (carteBug != null) return
        val r = Signaler.rapport(champsBug(), Signaler.etiquettes())
        rapportBug = r
        val dp = resources.displayMetrics.density
        fun px(v: Int) = (v * dp).toInt()
        fun texte(s: String, taille: Float, couleur: Int, gras: Boolean = false) = TextView(this).also {
            it.text = s; it.textSize = taille; it.setTextColor(couleur)
            if (gras) it.setTypeface(Typeface.DEFAULT_BOLD)
        }
        val boite = LinearLayout(this)
        boite.orientation = LinearLayout.VERTICAL
        boite.setPadding(px(16), px(14), px(16), px(14))
        val fondCarte = GradientDrawable()
        fondCarte.cornerRadius = 14 * dp
        fondCarte.setColor(0xFF262640.toInt())
        fondCarte.setStroke(px(2), 0xFFFF87FF.toInt())
        boite.background = fondCarte
        fun ajouter(v: View, haut: Int = 8) {
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.topMargin = px(haut)
            boite.addView(v, lp)
        }
        ajouter(texte(t("bug.titre"), 19f, 0xFFFFFFFF.toInt(), gras = true), 0)
        ajouter(texte(t("bug.adulte"), 13f, 0xFFFFAF5F.toInt()), 4)
        ajouter(texte(t("bug.partira"), 13f, 0xFFE6E6E6.toInt(), gras = true), 10)
        val apercu = texte(r.first + "\n\n" + r.second, 11f, 0xFFE6E6E6.toInt())
        apercu.setTypeface(Typeface.MONOSPACE)
        apercu.setPadding(px(10), px(8), px(10), px(8))
        val fondApercu = GradientDrawable()
        fondApercu.cornerRadius = 8 * dp
        fondApercu.setColor(0xFF11111B.toInt())
        apercu.background = fondApercu
        ajouter(apercu, 6)
        ajouter(texte(t("bug.jamais"), 12f, 0xFF9A9AB0.toInt()), 10)
        val rangee = LinearLayout(this)
        rangee.orientation = LinearLayout.HORIZONTAL
        for ((cle, couleur, action) in listOf(
                Triple("bug.tel.ouvrir", 0xFF5FD787.toInt(), { ouvrirPageBug() }),
                Triple("bug.tel.fichier", 0xFF87AFFF.toInt(), { demanderFichierBug() }),
                Triple("bug.tel.annuler", 0xFF9A9AB0.toInt(), { fermerCarteBug(); ecrire(t("bug.annule"), Commandes.ROSE) }))) {
            val b = texte(t(cle), 13f, couleur, gras = true)
            b.gravity = Gravity.CENTER
            b.setPadding(px(6), px(10), px(6), px(10))
            val g = GradientDrawable()
            g.cornerRadius = 10 * dp
            g.setColor(0xFF2E2E48.toInt())
            g.setStroke(px(2), couleur)
            b.background = g
            b.setOnClickListener { action() }
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            lp.marginEnd = px(6)
            rangee.addView(b, lp)
        }
        ajouter(rangee, 12)
        ajouter(texte(t("bug.tel.note"), 11f, 0xFF9A9AB0.toInt()), 10)
        val defileur = ScrollView(this)
        defileur.isClickable = true                 // toucher la carte ne ferme pas le jeu (le fond, si)
        defileur.addView(boite)
        val lp = android.widget.FrameLayout.LayoutParams(android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP)
        lp.setMargins(px(14), px(30), px(14), px(14))
        findViewById<android.widget.FrameLayout>(R.id.fond).addView(defileur, lp)
        carteBug = defileur
    }

    private fun fermerCarteBug() {
        carteBug?.let { (it.parent as? android.view.ViewGroup)?.removeView(it) }
        carteBug = null
        saisie.requestFocus()
    }

    /** Le navigateur ouvre la page déjà remplie ; c'est l'adulte qui l'envoie (ou pas), avec son compte GitHub. */
    private fun ouvrirPageBug() {
        val r = rapportBug ?: return
        try {
            startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW,
                android.net.Uri.parse(Signaler.adresse(r.first, r.second))))
            fermerCarteBug()
            ecrire(t("bug.ouverte"), Commandes.ROSE)
        } catch (e: Exception) {
            ecrire(t("bug.tel.pas_navigateur"), Commandes.ROSE)
        }
    }

    private fun demanderFichierBug() {
        val i = android.content.Intent(android.content.Intent.ACTION_CREATE_DOCUMENT)
            .addCategory(android.content.Intent.CATEGORY_OPENABLE).setType("text/plain")
            .putExtra(android.content.Intent.EXTRA_TITLE, Signaler.FICHIER)
        try {
            startActivityForResult(i, REQ_BUG)
        } catch (e: Exception) {
            ecrire(t("bug.tel.erreur"), Commandes.ROSE)
        }
    }

    /** Le rapport écrit dans le fichier choisi par l'adulte (le jeu ne l'envoie nulle part). */
    private fun enregistrerBug(uri: android.net.Uri?) {
        val r = rapportBug
        if (uri == null || r == null) { ecrire(t("bug.annule"), Commandes.ROSE); return }
        fermerCarteBug()
        exec.execute {
            val ok = try {
                contentResolver.openOutputStream(uri, "wt")!!.use { it.write((r.first + "\n\n" + r.second + "\n").toByteArray(Charsets.UTF_8)) }
                true
            } catch (e: Exception) { false }
            handler.post {
                val nom = (try { java.net.URLDecoder.decode(uri.toString(), "UTF-8") } catch (e: Exception) { "" })
                    .substringAfterLast('/').substringAfterLast(':').ifEmpty { Signaler.FICHIER }
                ecrire(if (ok) t("bug.tel.ecrit", "fichier" to nom) else t("bug.tel.erreur"), Commandes.ROSE)
            }
        }
    }

    /** Le fond de l'espace dans la couleur du thème (le terminal en dessous garde son fond sombre). */
    private fun themeEcran() {
        if (espace == null) return
        val th = Apparence.theme(jeu)
        findViewById<LinearLayout>(R.id.panneau).setBackgroundColor(th.couleur(EspaceDessin.FOND))
        findViewById<View>(R.id.fond).setBackgroundColor(th.couleur(EspaceDessin.FOND))
    }
}
