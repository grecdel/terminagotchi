package fr.terminagotchi

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.File

/** Éditeur de texte intégré, l'équivalent de « nano » : edite fichier.txt */
class EditeurActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val chemin = intent.getStringExtra("chemin") ?: run { finish(); return }
        val fichier = File(chemin)
        val dp = resources.displayMetrics.density

        val racine = LinearLayout(this)
        racine.orientation = LinearLayout.VERTICAL
        racine.setBackgroundColor(0xFF11111B.toInt())
        racine.setPadding((10 * dp).toInt(), (10 * dp).toInt(), (10 * dp).toInt(), (10 * dp).toInt())

        val titre = TextView(this)
        titre.text = "✏ ${fichier.name}" + if (fichier.exists()) "" else "  (nouveau fichier)"
        titre.setTextColor(0xFFFF87FF.toInt())
        titre.textSize = 16f
        titre.typeface = Typeface.DEFAULT_BOLD
        racine.addView(titre)

        val aide = TextView(this)
        aide.text = if (fichier.name == "carte.txt") Doom.LEGENDE else "Modifie le texte puis Enregistrer."
        aide.setTextColor(0xFF9A9AB0.toInt())
        aide.textSize = 12f
        racine.addView(aide)

        val zone = EditText(this)
        zone.setText(if (fichier.isFile) fichier.readText() else "")
        zone.typeface = Typeface.MONOSPACE
        zone.textSize = 15f
        zone.setTextColor(0xFFE6E6E6.toInt())
        zone.setBackgroundColor(0xFF1E1E2E.toInt())
        zone.gravity = Gravity.TOP or Gravity.START
        zone.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or
            InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        zone.setHorizontallyScrolling(true)
        zone.setPadding((8 * dp).toInt(), (8 * dp).toInt(), (8 * dp).toInt(), (8 * dp).toInt())
        val defile = ScrollView(this)
        defile.isFillViewport = true
        val defileH = HorizontalScrollView(this)
        defileH.isFillViewport = true
        defileH.addView(zone, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.MATCH_PARENT))
        defile.addView(defileH)
        val lpZone = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f)
        lpZone.topMargin = (8 * dp).toInt()
        racine.addView(defile, lpZone)

        val barre = LinearLayout(this)
        barre.orientation = LinearLayout.HORIZONTAL
        barre.gravity = Gravity.END
        fun bouton(t: String, action: () -> Unit) {
            val b = TextView(this)
            b.text = t
            b.textSize = 15f
            b.setTextColor(0xFFFFFFFF.toInt())
            b.setBackgroundResource(R.drawable.bouton)
            b.setPadding((16 * dp).toInt(), (10 * dp).toInt(), (16 * dp).toInt(), (10 * dp).toInt())
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.marginStart = (8 * dp).toInt()
            lp.topMargin = (8 * dp).toInt()
            b.layoutParams = lp
            b.setOnClickListener { action() }
            barre.addView(b)
        }
        bouton("Annuler") { finish() }
        bouton("💾 Enregistrer") {
            try {
                fichier.parentFile?.mkdirs()
                fichier.writeText(zone.text.toString())
                Toast.makeText(this, "Enregistré : ${fichier.name}", Toast.LENGTH_SHORT).show()
                finish()
            } catch (e: Exception) {
                Toast.makeText(this, "Impossible d'enregistrer : ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
        racine.addView(barre)
        setContentView(racine)
    }
}
