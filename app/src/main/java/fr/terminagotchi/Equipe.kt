package fr.terminagotchi

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/**
 * L'équipe : les bestioles dressées grandissent (enfant → ado → adulte → forme finale) en gardant leur nom.
 * La bestiole active gagne de l'expérience à chaque commande tapée à la main.
 * Les espèces qui ont un dessin complet (Abyssor pour l'instant) s'animent en haute qualité.
 */
object Equipe {
    val STADES = listOf("enfant", "ado", "adulte", "finale")
    private val NOM = mapOf("enfant" to "enfant", "ado" to "ado", "adulte" to "adulte", "finale" to "forme finale")
    private val SEUILS = mapOf("enfant" to 150, "ado" to 500, "adulte" to 1500)
    val ANIMS = listOf("statique", "mange", "attaque", "salut", "parle", "dort", "content", "affame", "confus",
        "colere", "victoire", "ko", "evolution")

    fun nomStade(s: String) = NOM[s] ?: s

    fun active(jeu: Jeu): JSONObject? {
        val caps = Explo.captures(jeu)
        if (caps.length() == 0) return null
        val id = jeu.module("equipe").optString("active")
        for (i in 0 until caps.length()) if (caps.getJSONObject(i).optString("id") == id) return caps.getJSONObject(i)
        return caps.getJSONObject(caps.length() - 1)
    }

    /** Chaque commande tapée fait grandir la bestiole active. Renvoie un message si elle évolue. */
    fun apresCommande(jeu: Jeu, colle: Boolean): String? {
        if (colle) return null
        val ind = active(jeu) ?: return null
        ind.put("xp", ind.optInt("xp") + 2)
        val s = ind.optString("stade", "enfant")
        val seuil = SEUILS[s] ?: return null
        if (ind.optInt("xp") < seuil) return null
        val nouveau = STADES[STADES.indexOf(s) + 1]
        ind.put("stade", nouveau).put("xp", 0).put("evolue", System.currentTimeMillis())
        val nom = ind.optString("espece")
        jeu.log("🌟 $nom évolue : ${nomStade(nouveau)} !")
        jeu.dire("Oh ! $nom brille… il évolue en ${nomStade(nouveau)} ! Regarde : anime $nom evolution", 14)
        return "🌟 $nom évolue en ${nomStade(nouveau)} ! (anime $nom evolution)"
    }

    fun texte(jeu: Jeu): String {
        val caps = Explo.captures(jeu)
        if (caps.length() == 0) return "Ton équipe est vide : joue avec ton familier, un monstre finira par apparaître !"
        val act = active(jeu)
        val sb = StringBuilder("🐾 Équipe de ${jeu.nom}\n")
        for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 12)) {
            val c = caps.getJSONObject(i)
            val e = Bestiaire.espece(c.optString("espece")) ?: continue
            val s = c.optString("stade", "enfant")
            val seuil = SEUILS[s]
            val titre = if (c.optBoolean("shiny") || e.rarete == "légendaire") "§${e.nom}§" else e.nom
            sb.append(if (c.optString("id") == act?.optString("id")) "★ " else "   ")
                .append("¤${e.id}${if (c.optBoolean("shiny")) "*" else ""}¤ $titre · ${nomStade(s)} · ")
                .append(if (seuil != null) "${c.optInt("xp")}/$seuil XP" else "stade maximal")
                .append(if (Animations.dispo(e.id)) " · animé" else "").append("\n")
        }
        sb.append("\nChoisir l'active : equipe <nom> · la voir bouger : anime <nom> [animation]")
        return sb.toString()
    }

    fun choisir(jeu: Jeu, nom: String): String {
        val e = Bestiaire.espece(nom) ?: return "Tu n'as pas encore dressé de « $nom »."
        val caps = Explo.captures(jeu)
        for (i in caps.length() - 1 downTo 0) {
            val c = caps.getJSONObject(i)
            if (c.optString("espece") == e.nom) {
                jeu.module("equipe").put("active", c.optString("id"))
                return "★ ${e.nom} est maintenant ta bestiole active : elle grandit à chaque commande que tu tapes."
            }
        }
        return "Tu n'as pas encore dressé de « $nom »."
    }
}

/** Lecture des animations détaillées (assets/anim/<espèce>/<stade>/<animation>.webp : une bande d'images). */
object Animations {
    private var ctxApp: android.content.Context? = null
    private val index = HashMap<String, JSONObject?>()

    fun init(ctx: android.content.Context) { ctxApp = ctx.applicationContext }

    private fun index(id: String): JSONObject? = index.getOrPut(id) {
        try { JSONObject(ctxApp!!.assets.open("anim/$id/index.json").bufferedReader().use { it.readText() }) } catch (e: Exception) { null }
    }

    fun dispo(id: String) = index(id) != null

    fun images(id: String, stade: String, anim: String): List<Bitmap>? {
        val ix = index(id) ?: return null
        val n = ix.optJSONObject("anims")?.optJSONObject(stade)?.optInt(anim) ?: 0
        if (n == 0) return null
        val bande = try { ctxApp!!.assets.open("anim/$id/$stade/$anim.webp").use { BitmapFactory.decodeStream(it) } } catch (e: Exception) { null } ?: return null
        val t = bande.height
        return (0 until n).map { Bitmap.createBitmap(bande, it * t, 0, t, t) }
    }

    /** Décalage de teinte pour les shiny (chaque individu a la sienne). */
    private fun filtreTeinte(tours: Double): ColorMatrixColorFilter {
        val a = Math.toRadians(tours * 360.0)
        val c = Math.cos(a).toFloat(); val s = Math.sin(a).toFloat()
        val lr = 0.213f; val lg = 0.715f; val lb = 0.072f
        val m = floatArrayOf(
            lr + c * (1 - lr) + s * (-lr), lg + c * (-lg) + s * (-lg), lb + c * (-lb) + s * (1 - lb), 0f, 0f,
            lr + c * (-lr) + s * 0.143f, lg + c * (1 - lg) + s * 0.140f, lb + c * (-lb) + s * (-0.283f), 0f, 0f,
            lr + c * (-lr) + s * (-(1 - lr)), lg + c * (-lg) + s * lg, lb + c * (1 - lb) + s * lb, 0f, 0f,
            0f, 0f, 0f, 1f, 0f)
        return ColorMatrixColorFilter(ColorMatrix(m))
    }

    /** anime <nom> [animation] : une petite fenêtre qui joue l'animation. */
    fun jouer(act: Activity, ind: JSONObject, animDemandee: String): String {
        val e = Bestiaire.espece(ind.optString("espece")) ?: return "Espèce inconnue."
        if (!dispo(e.id)) return "${e.nom} n'a pas encore d'animation détaillée."
        var stade = ind.optString("stade", "enfant")
        val anim = animDemandee.lowercase().replace("é", "e").replace("è", "e").ifEmpty { "statique" }
        if (anim !in Equipe.ANIMS) return "Animations : " + Equipe.ANIMS.joinToString(", ")
        if (anim == "evolution") {
            val i = Equipe.STADES.indexOf(stade)
            if (i <= 0) return "${e.nom} est encore enfant : il n'a pas encore évolué."
            stade = Equipe.STADES[i - 1]
        }
        val imgs = images(e.id, stade, anim) ?: return "Pas d'image pour $anim."
        val dp = act.resources.displayMetrics.density
        val vue = ImageView(act).apply {
            layoutParams = LinearLayout.LayoutParams((260 * dp).toInt(), (260 * dp).toInt())
            scaleType = ImageView.ScaleType.FIT_CENTER
            if (ind.optBoolean("shiny")) colorFilter = filtreTeinte(ind.optDouble("teinte", 0.5))
        }
        vue.setImageBitmap(imgs[0])
        val titre = TextView(act).apply {
            text = "${e.nom} · ${Equipe.nomStade(ind.optString("stade", "enfant"))} · $anim"
            setTextColor(0xFFFFAF00.toInt()); textSize = 15f; gravity = Gravity.CENTER
        }
        val boite = LinearLayout(act).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
            setPadding((16 * dp).toInt(), (16 * dp).toInt(), (16 * dp).toInt(), (8 * dp).toInt())
            setBackgroundColor(0xFF14141E.toInt()); addView(titre); addView(vue)
        }
        val h = Handler(Looper.getMainLooper())
        var k = 0
        val tours = if (anim == "evolution") 1 else 4
        val dlg = AlertDialog.Builder(act).setView(boite).setPositiveButton("OK", null).create()
        val pas = object : Runnable {
            override fun run() {
                if (!dlg.isShowing) return
                k++
                if (k >= imgs.size * tours) { if (anim != "evolution") k = 0 else return }
                vue.setImageBitmap(imgs[k % imgs.size])
                h.postDelayed(this, 100)
            }
        }
        dlg.setOnShowListener { h.postDelayed(pas, 100) }
        dlg.show()
        return "▶ ${e.nom} : $anim"
    }
}
