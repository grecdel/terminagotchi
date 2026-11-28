package fr.terminagotchi

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF

/**
 * Le petit nuage en pixels de la synchro (idée 74), dessiné en code (règle C : pixel art net) : une pilule posée au
 * bout du chemin, en haut à droite de la fenêtre d'observation. Orange barré « hors ligne », bleu avec une flèche
 * « envoi… ». Rien quand tout est à jour (Recensement.etatNuage).
 */
object NuageDessin {
    const val ORANGE = 0xFFFFAF5F.toInt()
    const val BLEU = 0xFF87AFFF.toInt()
    private const val FOND = 0xFF11111B.toInt()
    val FORME = listOf(
        "..XXXX......",
        ".XXXXXX.XX..",
        "XXXXXXXXXXXX",
        "XXXXXXXXXXXX",
        ".XXXXXXXXXX.")
    /** les pixels « creusés » dans le nuage : la barre (hors ligne) ou la flèche vers le haut (envoi) */
    val MARQUES = mapOf(
        "hors" to (2..5).map { it to it - 1 },
        "envoi" to listOf(6 to 1, 6 to 2, 6 to 3, 5 to 2, 7 to 2))

    fun couleur(etat: String) = if (etat == "envoi") BLEU else ORANGE

    /** Le nuage seul : 12 × 5 pixels du dessin, chacun de `px` pixels de l'écran. */
    fun nuage(c: Canvas, x: Float, y: Float, etat: String, px: Float) {
        val p = Paint()
        p.color = couleur(etat)
        for ((j, l) in FORME.withIndex()) for ((i, ch) in l.withIndex())
            if (ch == 'X') c.drawRect(x + i * px, y + j * px, x + (i + 1) * px, y + (j + 1) * px, p)
        p.color = FOND
        for ((i, j) in MARQUES[etat] ?: emptyList()) c.drawRect(x + i * px, y + j * px, x + (i + 1) * px, y + (j + 1) * px, p)
    }

    /** La pilule : cadre arrondi, le nuage, le mot (« hors ligne », « envoi… »). d : la densité de l'écran. */
    fun pilule(etat: String, mot: String, d: Float): Bitmap {
        val texte = Paint(Paint.ANTI_ALIAS_FLAG)
        texte.setTextSize(11 * d)
        texte.color = couleur(etat)
        texte.setFakeBoldText(true)
        val px = maxOf(1f, Math.round(2 * d).toFloat())
        val h = Math.round(22 * d)
        val w = Math.round(7 * d + 12 * px + 5 * d + texte.measureText(mot) + 8 * d)
        val b = Bitmap.createBitmap(maxOf(1, w), maxOf(1, h), Bitmap.Config.ARGB_8888)
        val c = Canvas(b)
        val cadre = Paint(Paint.ANTI_ALIAS_FLAG)
        cadre.color = FOND
        val r = RectF(d, d, w - d, h - d)
        c.drawRoundRect(r, 8 * d, 8 * d, cadre)
        cadre.setStyle(Paint.Style.STROKE)
        cadre.setStrokeWidth(1.5f * d)
        cadre.color = couleur(etat)
        c.drawRoundRect(r, 8 * d, 8 * d, cadre)
        nuage(c, 7 * d, (h - 5 * px) / 2f, etat, px)
        c.drawText(mot, 7 * d + 12 * px + 5 * d, h / 2f + 4 * d, texte)
        return b
    }
}
