package fr.terminagotchi

import android.content.Context
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.Switch
import android.widget.TextView

/**
 * « Réglages du son » du téléphone (décision du 3 novembre) : l'interrupteur son oui / non, trois VRAIS curseurs de
 * volume (musique, cris, réussites) et le bouton « ce soir seulement ». Les règles restent dans Sons.kt (les mêmes
 * que `son …` dans le terminal, et que `tg son …` sur PC) ; ici, seulement la fenêtre.
 */
class SonsReglages(ctx: Context?, private val jeu: Jeu, dp: Float,
                   private val ecrire: (String) -> Unit, private val apres: () -> Unit) {
    val boite = LinearLayout(ctx)
    val interrupteur = Switch(ctx)
    val curseurs = LinkedHashMap<String, SeekBar>()
    private val libelles = HashMap<String, TextView>()
    val soir = Button(ctx)
    private val nuit = TextView(ctx)

    init {
        val p = (16 * dp).toInt()
        boite.orientation = LinearLayout.VERTICAL
        boite.setPadding(p, p, p, (8 * dp).toInt())
        boite.setBackgroundColor(FOND)
        interrupteur.textSize = 16f
        interrupteur.setTextColor(TEXTE)
        interrupteur.isChecked = Sons.reglages(jeu).optBoolean("on")
        interrupteur.setOnCheckedChangeListener { _, on ->
            if (on != Sons.reglages(jeu).optBoolean("on")) { ecrire(Sons.commande(jeu, if (on) "oui" else "non")); apres() }
            rafraichir()
        }
        boite.addView(interrupteur)
        for (cat in listOf("musique", "cris", "retours")) {
            val l = TextView(ctx).apply { textSize = 14f; setTextColor(TEXTE); setPadding(0, (14 * dp).toInt(), 0, 0) }
            val c = SeekBar(ctx).apply { max = 100; setKeyProgressIncrement(5); progress = Sons.valeurCurseur(jeu, cat) }
            c.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(s: SeekBar, v: Int, doigt: Boolean) { if (doigt) l.text = Sons.libelle(jeu, cat, v) }
                override fun onStartTrackingTouch(s: SeekBar) {}
                override fun onStopTrackingTouch(s: SeekBar) {
                    ecrire(Sons.curseur(jeu, cat, s.progress))
                    apres()
                    essai(cat)
                    rafraichir()
                }
            })
            libelles[cat] = l; curseurs[cat] = c
            boite.addView(l); boite.addView(c)
        }
        nuit.textSize = 13f; nuit.setTextColor(GRIS); nuit.setPadding(0, (14 * dp).toInt(), 0, (4 * dp).toInt())
        boite.addView(nuit)
        soir.text = Langue.t("son.bouton.soir")
        soir.setOnClickListener {                  // le jour, il le dit simplement (rien n'est coupé)
            val r = Sons.commande(jeu, "soir"); ecrire(r); apres(); rafraichir(); nuit.text = Vert.rendre(r) }
        boite.addView(soir)
        rafraichir()
    }

    /** Un petit son pour entendre le nouveau volume (la musique, elle, suit d'elle-même dans les vues Monde / Espace). */
    private fun essai(cat: String) {
        try {
            when (cat) {
                "cris" -> Sons.son(jeu, jeu.especeCompagnon?.let { Sons.nomCri(it) } ?: "reussite_petite")
                "retours" -> Sons.son(jeu, "reussite_petite")
            }
        } catch (e: Exception) { }
    }

    fun rafraichir() {
        val on = Sons.reglages(jeu).optBoolean("on")
        interrupteur.text = Sons.libelle(jeu, "on")
        if (interrupteur.isChecked != on) interrupteur.isChecked = on
        for ((cat, c) in curseurs) {
            val v = Sons.valeurCurseur(jeu, cat)
            if (c.progress != v) c.progress = v
            c.isEnabled = on
            libelles[cat]?.text = Sons.libelle(jeu, cat)
        }
        nuit.text = Vert.rendre(Sons.libelle(jeu, "soir"))
    }

    companion object {
        const val FOND = 0xFF14141E.toInt()
        const val TEXTE = 0xFFEEEEEE.toInt()
        const val GRIS = 0xFFAAAAAA.toInt()
    }
}
