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
    private var ambiance = System.currentTimeMillis() + AMBIANCE

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_terminal)
        window.setSoftInputMode(
            WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE or
                WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        )

        jeu = Jeu(this)
        shell = Shell(jeu.home).also { s -> s.journal = { jeu.journal.toList() } }
        commandes = Commandes(this, jeu, { shell.dossier }) { texte, couleur ->
            if (texte.isNotEmpty()) ecrire(texte, couleur)
            rafraichir()
        }
        menu = MenuParties(this, jeu,
            apresChangement = {
                shell.dossier = jeu.home            // l'ancien terrain a été rangé avec son ancienne partie
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
        essais(intent)
        handler.postDelayed({ commandeExterne(intent) }, 400)      // une commande tapée dans l'île de la bulle
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission("android.permission.POST_NOTIFICATIONS") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        }
        creature = findViewById(R.id.creature)
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
        textesFixes()
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
        if (lanceur(intent) && !Parties.aucune(this)) {
            ecrire(menu.ouvrir(), Commandes.ROSE)       // lancé depuis l'icône : le menu des parties
        } else if (!jeu.existe) {
            ecrire(t("term.oeuf"))
            ecranIntro = 1                           // les écrans du début (Intro.kt), avant le nom de l'œuf
        } else {
            jeu.parlerSiSilencieux()
            ecrire(t("mini.accueil1") + "\n" + t("term.aide_pour_aide"))
        }
        jeu.sauver()
        rafraichir()
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

    override fun onPause() {
        super.onPause()
        ecranVisible = false                      // écran éteint ou appli cachée : la vie se met en pause
    }

    override fun onResume() {
        super.onResume()
        ecranVisible = true
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

    /** Complète le dernier mot : un nom de commande (1er mot) ou un fichier/dossier. */
    private fun completer() {
        val texte = saisie.text.toString()
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
                when {
                    brut != brut.lowercase() && Verif.collee(brut.lowercase()) == null && brut.lowercase() in Verif.MOTS_CONNUS ->
                        t("core.inconnue.casse", "cmd" to brut, "proche" to brut.lowercase())
                    colle != null -> t("core.inconnue.proche", "cmd" to brut, "proche" to colle)
                    // I9 : `pwd,` (une virgule collée) → pwd
                    brut.trimEnd(',', '.', ';', ':', '!', '?').let { it != brut && it.lowercase() in Verif.MOTS_CONNUS } ->
                        t("core.inconnue.proche", "cmd" to brut, "proche" to brut.trimEnd(',', '.', ';', ':', '!', '?'))
                    else -> t("term.err.inconnue", "cmd" to Regles.premierMot(ligne))
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

    private fun valider() {
        if (enCours) { android.util.Log.i("TG", "commande ignorée : une autre tourne encore"); return }
        val ligne = saisie.text.toString().trim()
        val etaitColle = colle
        colle = false
        val etaitRappel = rappel != null && ligne == rappel
        rappel = null
        posHisto = -1
        if (confirmerDeblocage) {                    // « debloquer tout » : oui / non (dans les 14 langues)
            confirmerDeblocage = false
            saisie.setText("")
            ecrire("> $ligne", 0xFF5FD787.toInt())
            if (MenuParties.oui(ligne)) {
                Intro.toutDebloquer(jeu)
                jeu.sauver()
                ecrire(t("deb.tout.ok"), Commandes.ROSE)
            } else ecrire(t("deb.tout.non"), Commandes.ROSE)
            rafraichir()
            return
        }
        if (!jeu.existe && nomPropose != null && ligne.isEmpty() && !menu.ouvert) {   // Entrée : le nom est confirmé
            naitre(nomPropose!!)
            return
        }
        if (!jeu.existe && ecranIntro > 0 && ligne.isEmpty() && !menu.ouvert) {   // Entrée : l'écran suivant
            actionIntro("suivant")
            return
        }
        if (jeu.existe && ligne.isEmpty() && Intro.aMontrer(jeu) != null) {     // Entrée : l'écran de présentation est lu
            actionIntro("ok")
            return
        }
        if (jeu.existe && ligne.isNotEmpty() && Intro.aMontrer(jeu) != null) Intro.lu(jeu)   // taper une commande le referme
        if (menu.ouvert && !enCours) {              // une réponse au menu des parties (rien n'est mangé)
            saisie.setText("")
            ecrire("> $ligne", 0xFF5FD787.toInt())
            val r = menu.repondre(ligne)
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
        saisie.setText("")
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
        when (Regles.premierMot(ligne)) {
            "clear" -> { sortie.text = ""; return }
            "quitter", "exit" -> { finish(); return }
            "parties" -> { ecrire(menu.ouvrir(), Commandes.ROSE); return }
            "langue" -> { ecrire(langue(ligne.trim().split(Regex("\\s+")).getOrNull(1)), Commandes.ROSE); return }
            "partie" -> { ecrire(menu.commande(ligne.substringAfter(' ', "")), Commandes.ROSE); rafraichir(); return }
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
                if (ligne.trim().split(Regex("\\s+")).getOrNull(1)?.lowercase() !in setOf("tout", "all")) {
                    ecrire(Histoire.aideLecon(jeu), Commandes.ROSE)
                    return
                }
                ecrire(t("term.aide", "ctf" to Mots.terme("ctf", Mots.palier(jeu), true)) + "\n" + t("term.aide.maison") + "\n" + t("env.aide.tel") + "\n" + t("ent.aide.tel"))
                return
            }
        }
        // Commandes intégrées (téléphone, créature) : réponse immédiate
        val interne = commandes.executer(ligne)
        if (interne != null) {
            // la carte qui pousse s'ouvre à la place de l'observatoire (le texte reste en secours)
            if (interne.carte && espace != null) { espace?.onglet("carte"); ecrire(interne.texte, interne.couleur, interne.petit) }
            else if (interne.carte && ouvrirCarte()) ecrire("🗺 " + Carte.titre(jeu), interne.couleur)
            else ecrire(interne.texte, interne.couleur, interne.petit)
            if (lexiqueVue.visibility == View.VISIBLE) basculerLexique()
            interne.aller?.let {
                shell.dossier = it
                majObservatoire(ligne)
            }
            try { apresCommande(ligne, etaitColle, etaitRappel) } catch (e: Exception) { android.util.Log.e("TG", "après « $ligne »", e) }
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

        enCours = true
        invite.alpha = 0.4f
        android.util.Log.i("TG", "commande : $ligne")
        exec.execute {
            val resultat = try { shell.executer(ligne) } catch (e: Exception) { android.util.Log.e("TG", "shell", e); t("term.erreur", "msg" to e.message) }
            handler.post {
                if (resultat.isNotEmpty()) ecrire(resultat)
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
                } catch (e: Exception) {
                    android.util.Log.e("TG", "après la commande « $ligne »", e)
                } finally {
                    enCours = false
                    invite.alpha = 1f
                }
            }
        }
    }

    /** L'œuf a son nom (confirmé) : la partie commence. */
    private fun naitre(nom: String) {
        nomPropose = null
        saisie.setText("")
        jeu.nom = nom
        jeu.shiny = false   // le compagnon ne naît jamais shiny (pas de rareté)
        Intro.nouvellePartie(jeu)              // l'œuf seul, sa liste de commandes ; le jeu s'ouvre petit à petit
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
        if (lanceur(intent) && !menu.ouvert && !Parties.aucune(this)) ecrire(menu.ouvrir(), Commandes.ROSE)
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
        jeu.sauver()
        WidgetCreature.majTous(this)
        if (mange) saut = maxOf(saut, 4)
        rafraichir()
        lancerAnimation()
        if (Recensement.aUnCompte(jeu) && Regles.premierMot(ligne) !in setOf("sync", "compte")) {
            commandes.sync(forcer = false, silencieux = true)
        }
    }

    /**
     * Mise en forme spéciale : ¤id:variante:stade*teinte+~n¤ = dessin d'une bestiole (voir Bestiaire.balise :
     * * = shiny avec sa teinte, + = grand portrait, ~n = aura de rareté), §texte§ = écriture arc-en-ciel (RGB).
     */
    private fun miseEnForme(texte: String, couleur: Int?): SpannableStringBuilder {
        val sb = SpannableStringBuilder()
        val motif = Regex("¤([a-z0-9_]+)(?::([^:¤*+~]+))?(?::([a-z]+))?(?:\\*([0-9.]*))?(\\+)?(?:~([0-9]))?¤|§([^§]*)§|`([^`\n]+)`")
        var i = 0
        for (m in motif.findAll(texte)) {
            sb.append(texte, i, m.range.first)
            if (m.groups[8] != null) {                    // `commande` : en vert (voir Vert.kt)
                val debut = sb.length
                sb.append(m.groupValues[8])
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
                    val petit = detail ?: Bestiaire.bitmap(e, shiny, 4, stade, vid, teinte)
                    val img = if (aura == null) petit else try { Aura.entourer(petit, 4, aura, garder = true) } catch (x: Exception) { petit }
                    val d = android.graphics.drawable.BitmapDrawable(resources, img)
                    if (detail != null && shiny) d.colorFilter = Bestiaire.filtreTeinte(teinte)
                    val px = ((if (detail != null) 160 else 40) * resources.displayMetrics.density).toInt()
                    d.setBounds(0, 0, px * img.width / maxOf(1, petit.width), px * img.height / maxOf(1, petit.height))
                    sb.setSpan(android.text.style.ImageSpan(d, android.text.style.DynamicDrawableSpan.ALIGN_BOTTOM),
                        debut, debut + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            } else {
                arcEnCiel(sb, m.groupValues[7])
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
        val mode = when {
            ecran -> "ecran"
            jeu.existe && Intro.enCours(jeu) -> "oeuf"
            carteIntro != null -> "carte"
            else -> null
        }
        if (mode == null) {
            introVue?.let { (it.parent as? LinearLayout)?.removeView(it) }
            introVue = null
            if (carteVue == null) obs.visibility = View.VISIBLE
            boiteSortie.visibility = View.VISIBLE
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
        Intro.hauteurMax = fondH / resources.displayMetrics.density - (if (mode == "ecran") 150f else 300f)
        when (mode) {
            "ecran" -> v.montrerEcran(ecranIntro.coerceIn(1, v.nbEcrans()))
            "oeuf" -> v.montrerOeuf()
            else -> v.montrerCarte(carteIntro!!)
        }
        obs.visibility = View.GONE
        boiteSortie.visibility = if (mode == "ecran") View.GONE else View.VISIBLE
    }

    /** Un bouton de l'intro (ou Entrée sur une ligne vide) : suivant, passer, ok. */
    private fun actionIntro(a: String) {
        when (a) {
            "suivant" -> if (!jeu.existe && ecranIntro > 0) ecranIntro = minOf(ecranIntro + 1, introVue?.nbEcrans() ?: 4)
            "passer" -> if (!jeu.existe && ecranIntro > 0) ecranIntro = introVue?.nbEcrans() ?: 4
            "ok" -> if (jeu.existe && Intro.aMontrer(jeu) != null) { Intro.lu(jeu); jeu.sauver() }
        }
        rafraichir()
        saisie.requestFocus()
    }

    // ------------------------------------------------------------ la carte qui pousse
    private var carteVue: CarteVue? = null
    private var espace: EspaceVue? = null

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
            panneau.setBackgroundColor(EspaceDessin.FOND)
            findViewById<View>(R.id.fond).setBackgroundColor(EspaceDessin.FOND)
            sortie.textSize = if (classe) 17f else 13f
            panneau.requestLayout()
            jeu.module("espace").put("ouvert", true).put("classe", classe)
            jeu.sauver()
            jeu.historique.lastOrNull()?.takeIf { Regles.premierMot(it) !in setOf("espace", "deploie", "cerveau") }?.let { v.deployer(it) }
            if (dire) ecrire(t("esp.tel.ouvert"), Commandes.ROSE)
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
        cadre.layoutParams = (cadre.layoutParams as LinearLayout.LayoutParams).also { it.height = (140 * d).toInt(); it.weight = 0f }
        panneau.layoutParams = (panneau.layoutParams as android.widget.FrameLayout.LayoutParams).also {
            it.height = android.widget.FrameLayout.LayoutParams.WRAP_CONTENT; val m = (8 * d).toInt(); it.setMargins(m, m, m, m)
        }
        panneau.setBackgroundResource(R.drawable.panneau)
        findViewById<View>(R.id.fond).setBackgroundColor(0x55000000)
        sortie.textSize = 12f
        jeu.module("espace").put("ouvert", false)
        jeu.sauver()
        ecrire(t("esp.tel.ferme"), Commandes.ROSE)
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
        val s = miseEnForme(texte, couleur)
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
            sb.append(if (pc) "🔒 " else if (goutee) "● " else "○ ")
            val debutCmd = sb.length
            sb.append(cmd)
            sb.setSpan(StyleSpan(Typeface.BOLD), debutCmd, sb.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
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
        titre.text = if (!jeu.existe) t("term.oeuf_mysterieux") else if (jeu.shiny) miseEnForme("§${jeu.titre()}§", null) else jeu.titre()
        // les 6 envies, puis l'état de la satiété et la petite assiette du jour (Satiete.kt)
        faim.text = if (jeu.existe) Envies.compact(jeu) + "  " + Envies.emoji(jeu) + "\n" + Satiete.ligneEtat(jeu) + "  🍽 " + Satiete.assiette(jeu)
            else jeu.texteFaim()
        xp.text = jeu.texteXp()
        // P2-5 : « INT AGI FOR END » n'apparaît qu'avec l'équipe (avant, c'est du jargon pour un enfant de 7 ans)
        stats.text = (if (Intro.ouvert(jeu, "equipe")) jeu.texteStats() else "") + if (Explo.captures(jeu).length() > 0 && Intro.ouvert(jeu, "equipe")) Guide.actuel(jeu).let { "  🧭 ${Guide.ICONES[it.type]} ${it.nom}" } else ""
        invite.text = if (::menu.isInitialized && menu.ouvert) ">" else if (jeu.existe) "${shell.chemin()} $" else t("term.invite_nom")
        val b = jeu.bulleActive()
        bulle.visibility = if (b.isEmpty()) View.GONE else View.VISIBLE
        bulle.text = Vert.rendre(b)
        val defi = Defis.actif(jeu)
        val panneau = Dressage.panneau(jeu, resources, imageCombat)
        // terrain effacé : le bandeau avec la commande à taper reste au-dessus de la leçon
        val l: CharSequence? = panneau ?: if (defi != null) t("app.defi", "cmd" to Regles.piege(defi), "s" to Defis.resteSecondes(jeu))
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
            lecon.maxHeight = maxOf((70 * dp).toInt(), fondH - entete - hBulle - hSortie - ((44 + 52 + 40) * dp).toInt())
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
        lexiqueBtn.visibility = if (jeu.existe && !oeuf && Intro.ouvert(jeu, "lexique")) View.VISIBLE else View.GONE
        majIntro()
        majBoutonAura()
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
            val cle = listOf(ind.optString("id"), Equipe.stade(ind), ind.optString("variante"), ind.optBoolean("shiny")).joinToString("|")
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

    private class VieEcran(val cle: String, val anim: AnimAuto.Anim, val echelle: Int, val teinte: Double?, val palier: String?)
    private var vieEcran: VieEcran? = null

    /** L'animation de vie de la créature de l'en-tête (le guide de l'équipe, ou le compagnon d'une espèce), ou null
     *  (l'œuf, la créature dessinée d'une ancienne partie, Abyssor et ses animations faites main). */
    private fun vieCourante(): VieEcran? = try { vieCalculee() } catch (e: Exception) { null }

    private fun vieCalculee(): VieEcran? {
        if (!::jeu.isInitialized || !jeu.existe || jeu.stade < 1) return null
        val ind = guideCapture()
        val cle: String
        if (ind != null) {
            cle = listOf("ind", ind.optString("id"), Equipe.stade(ind), ind.optString("variante"), ind.optBoolean("shiny")).joinToString("|")
            vieEcran?.takeIf { it.cle == cle }?.let { return it }
            val e = Bestiaire.espece(ind.optString("espece")) ?: return null
            if (Animations.dispo(e.id)) return null
            val a = Animations.auto(e, Equipe.stade(ind), ind.optString("variante", "classique"), "statique") ?: return null
            vieEcran = VieEcran(cle, Sprites.recadrer(a), 3, if (ind.optBoolean("shiny")) ind.optDouble("teinte", 0.5) else null,
                Aura.palierInd(ind))
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
                    creature.setImageBitmap(avecAura(AnimAuto.bitmap(v.anim, tic, v.echelle, v.teinte), v.echelle, v.palier, tic))
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
}
