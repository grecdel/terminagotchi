package fr.terminagotchi

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import java.io.File

/**
 * Les images d'« apprendre en jouant » sur le téléphone (Apprendre.kt) : les pictos 16 × 16 du carnet illustré (les
 * mêmes pixels qu'en Python : apprendre.json « pictos »), leur silhouette grise, la silhouette d'une bestiole pas encore
 * rencontrée (le tableau des rares), et le diplôme (PNG dans le terrain, « Enregistrer l'image », « Imprimer »).
 * Aucune image générée ni téléchargée : tout est dessiné ici.
 */
object ApprendreDessin {
    const val GRIS = 0xFF3A3A4C.toInt()
    private val cache = HashMap<String, Bitmap>()

    private fun hexa(s: String) = (0xFF000000L or s.removePrefix("#").toLong(16)).toInt()

    /** L'image 16 × 16 d'une commande (échelle : un pixel = echelle × echelle), en gris si elle n'a jamais été tapée. */
    fun picto(cmd: String, gris: Boolean = false, echelle: Int = 3): Bitmap? {
        val cle = "$cmd-$gris-$echelle"
        cache[cle]?.let { return it }
        val p = Apprendre.donnees().optJSONObject("pictos") ?: return null
        val rows = p.optJSONObject("images")?.optJSONArray(cmd) ?: return null
        val pal = p.getJSONObject("palette")
        val px = IntArray(16 * 16)
        for (y in 0 until 16) {
            val r = rows.getString(y)
            for (x in 0 until 16) {
                val ch = r[x]
                if (ch != '.') px[y * 16 + x] = if (gris) GRIS else hexa(pal.getString(ch.toString()))
            }
        }
        val b = Bitmap.createScaledBitmap(Bitmap.createBitmap(px, 16, 16, Bitmap.Config.ARGB_8888), 16 * echelle, 16 * echelle, false)
        cache[cle] = b
        return b
    }

    /** La silhouette d'une bestiole pas encore rencontrée (le vrai sprite, tout en gris). */
    fun ombre(e: Bestiaire.Espece, echelle: Int = 2): Bitmap {
        val img = Bestiaire.image(e)
        if (img == null) {
            val b = Bestiaire.bitmap(e, false, echelle)
            val w = b.width; val h = b.height
            val px = IntArray(w * h)
            b.getPixels(px, 0, w, 0, 0, w, h)
            for (i in px.indices) if (px[i] ushr 24 != 0) px[i] = GRIS
            return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
        }
        val n = maxOf(img.w, img.h)
        val px = IntArray(n * n)
        val ox = (n - img.w) / 2; val oy = n - img.h
        for (y in 0 until img.h) for (x in 0 until img.w) if ((img.octets[y * img.w + x].toInt() and 0xFF) != 0) px[(y + oy) * n + x + ox] = GRIS
        return Bitmap.createScaledBitmap(Bitmap.createBitmap(px, n, n, Bitmap.Config.ARGB_8888), n * echelle, n * echelle, false)
    }

    // ------------------------------------------------------------------ le diplôme (900 × 630, comme sur PC)
    const val W = 900
    const val H = 630

    fun diplome(jeu: Jeu, chap: String, now: Double = Apprendre.maintenant()): Bitmap {
        val c = Apprendre.contenuDiplome(jeu, chap, now)
        val b = Bitmap.createBitmap(W, H, Bitmap.Config.ARGB_8888)
        val cv = Canvas(b)
        val p = Paint().apply { isAntiAlias = false }
        val fond = 0xFFF6F0DE.toInt(); val encre = 0xFF282434.toInt(); val vert = 0xFF1F8A4C.toInt(); val or = 0xFFC99A2E.toInt()
        p.color = fond; cv.drawRect(0f, 0f, W.toFloat(), H.toFloat(), p)
        p.color = vert
        for (k in 0 until 3) {                                   // le cadre à circuits verts
            val m = (12 + k * 9).toFloat()
            cv.drawRect(m, m, W - m, m + 3, p); cv.drawRect(m, H - m - 3, W - m, H - m, p)
            cv.drawRect(m, m, m + 3, H - m, p); cv.drawRect(W - m - 3, m, W - m, H - m, p)
        }
        var x = 60
        while (x < W - 60) { cv.drawRect(x.toFloat(), 12f, x + 6f, 39f, p); cv.drawRect(x + 18f, H - 39f, x + 24f, H - 12f, p); x += 48 }
        val tp = Paint().apply { isAntiAlias = true; textAlign = Paint.Align.CENTER }
        fun texte(s: String, y: Float, taille: Float, coul: Int, gras: Boolean = false) {
            tp.textSize = taille; tp.color = coul; tp.isFakeBoldText = gras
            cv.drawText(s, W / 2f, y, tp)
        }
        texte("★ TERMINAGOTCHI ★", 80f, 22f, vert, true)
        texte(c.getValue("titre"), 140f, 54f, encre, true)
        texte(c.getValue("lieu"), 184f, 28f, or)
        val e = jeu.especeCompagnon?.let { Bestiaire.espece(it) }
        if (e != null) {                                         // la créature, en vrais pixels
            val bm = Bestiaire.bitmap(e, false, 1)
            val t = 150
            cv.drawBitmap(bm, Rect(0, 0, bm.width, bm.height), RectF(W / 2f - t / 2, 200f, W / 2f + t / 2, 200f + t), Paint().apply { isFilterBitmap = false })
        }
        texte(c.getValue("decerne"), 386f, 24f, encre)
        texte(c.getValue("nom"), 430f, 40f, encre, true)
        texte(c.getValue("cmds"), 472f, 24f, vert)
        p.color = encre; cv.drawRect(210f, 520f, W - 210f, 523f, p)     // la ligne vide : le prénom s'écrit à la main
        texte(c.getValue("ligne"), 548f, 18f, 0xFF787082.toInt())
        texte(c.getValue("mois"), 590f, 24f, encre)
        p.color = or; cv.drawRect(W - 132f, 450f, W - 60f, 522f, p)       // le sceau
        tp.textSize = 40f; tp.color = fond; cv.drawText("★", W - 96f, 500f, tp)
        return b
    }

    /** diplome_<chapitre>.png dans le terrain (jamais à travers un lien). */
    fun ecrireDiplome(jeu: Jeu, chap: String, now: Double = Apprendre.maintenant()): File {
        val f = File(jeu.terrain, "diplome_$chap.png")
        jeu.terrain.mkdirs()
        if (!java.nio.file.Files.isSymbolicLink(f.toPath())) f.outputStream().use { diplome(jeu, chap, now).compress(Bitmap.CompressFormat.PNG, 100, it) }
        return f
    }

    /** « Enregistrer l'image » : dans les images du téléphone (Pictures/Terminagotchi), sans aucune permission. */
    fun enregistrer(ctx: android.content.Context, b: Bitmap, chap: String): Boolean = try {
        val v = android.content.ContentValues()
        v.put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, "terminagotchi_diplome_$chap.png")
        v.put(android.provider.MediaStore.MediaColumns.MIME_TYPE, "image/png")
        v.put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/Terminagotchi")
        val r = ctx.contentResolver
        val u = r.insert(android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v)
        if (u == null) false else (r.openOutputStream(u)?.use { b.compress(Bitmap.CompressFormat.PNG, 100, it) } ?: false)
    } catch (e: Exception) { false }

    /** « Imprimer » : le menu d'impression du téléphone (une page A4 à l'italienne, le diplôme au centre). */
    fun imprimer(ctx: android.content.Context, b: Bitmap, chap: String) {
        val pm = ctx.getSystemService("print") as? android.print.PrintManager ?: return
        val adapt = object : android.print.PrintDocumentAdapter() {
            override fun onLayout(a: android.print.PrintAttributes?, n: android.print.PrintAttributes?, c: android.os.CancellationSignal?,
                                  cb: android.print.PrintDocumentAdapter.LayoutResultCallback, x: android.os.Bundle?) {
                cb.onLayoutFinished(android.print.PrintDocumentInfo.Builder("diplome_$chap.pdf")
                    .setContentType(android.print.PrintDocumentInfo.CONTENT_TYPE_PHOTO).setPageCount(1).build(), true)
            }

            override fun onWrite(p: Array<out android.print.PageRange>?, d: android.os.ParcelFileDescriptor, c: android.os.CancellationSignal?,
                                 cb: android.print.PrintDocumentAdapter.WriteResultCallback) {
                val doc = android.graphics.pdf.PdfDocument()
                val page = doc.startPage(android.graphics.pdf.PdfDocument.PageInfo.Builder(842, 595, 1).create())
                val w = 762f; val h = w * b.height / b.width
                page.canvas.drawBitmap(b, Rect(0, 0, b.width, b.height), RectF(40f, (595 - h) / 2, 40f + w, (595 + h) / 2), Paint())
                doc.finishPage(page)
                try {
                    java.io.FileOutputStream(d.fileDescriptor).use { doc.writeTo(it) }
                    cb.onWriteFinished(arrayOf(android.print.PageRange.ALL_PAGES))
                } catch (e: Exception) { cb.onWriteFailed(e.message) } finally { doc.close() }
            }
        }
        pm.print("Terminagotchi — diplome_$chap", adapt, android.print.PrintAttributes.Builder()
            .setMediaSize(android.print.PrintAttributes.MediaSize.ISO_A4.asLandscape()).build())
    }
}
