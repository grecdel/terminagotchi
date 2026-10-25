package fr.terminagotchi

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/**
 * L'équipe : les bestioles dressées grandissent (bébé → enfant → ado → adulte → ancien) en gardant leur nom.
 * La bestiole active gagne de l'expérience à chaque commande tapée à la main. Portage de pc/tg/equipe.py.
 * Toutes les espèces s'animent (moteur AnimAuto) ; Abyssor garde ses animations faites main.
 */
object Equipe {
    val STADES = listOf("bebe", "enfant", "ado", "adulte", "ancien")
    private val NOM = mapOf("bebe" to "bébé", "enfant" to "enfant", "ado" to "ado", "adulte" to "adulte",
        "ancien" to "ancien", "finale" to "ancien")
    /** XP pour passer au stade suivant */
    val SEUILS = mapOf("bebe" to 100, "enfant" to 250, "ado" to 600, "adulte" to 1500)
    /** Abyssor (animations détaillées faites à la main) garde ses noms de stades d'origine */
    val STADES_ABYSSOR = mapOf("bebe" to "enfant", "enfant" to "enfant", "ado" to "ado", "adulte" to "adulte", "ancien" to "finale")
    val ANIMS = AnimAuto.ANIMS

    fun nomStade(s: String) = NOM[s] ?: s

    /** Le stade d'une bestiole (les anciennes sauvegardes disaient « finale »). */
    fun stade(ind: JSONObject): String {
        val s = ind.optString("stade", "bebe").ifEmpty { "bebe" }
        return if (s == "finale") "ancien" else s
    }

    fun active(jeu: Jeu): JSONObject? {
        val caps = Explo.captures(jeu)
        if (caps.length() == 0) return null
        val id = jeu.module("equipe").optString("active")
        for (i in 0 until caps.length()) if (caps.getJSONObject(i).optString("id") == id) return caps.getJSONObject(i)
        return caps.getJSONObject(caps.length() - 1)
    }

    /** Ajoute de l'expérience à une bestiole ; renvoie un message si elle évolue. */
    fun gagner(jeu: Jeu, ind: JSONObject, xp: Int): String? {
        ind.put("xp", ind.optInt("xp") + xp)
        val s = stade(ind)
        val seuil = SEUILS[s] ?: return null
        if (ind.optInt("xp") < seuil) return null
        val nouveau = STADES[STADES.indexOf(s) + 1]
        ind.put("stade", nouveau).put("xp", 0).put("evolue", System.currentTimeMillis())
        val nom = ind.optString("espece")
        jeu.log(Mots.accorder("🌟 {nom} évolue : {stade} !", "nom" to nom, "stade" to nomStade(nouveau)))
        jeu.dire(Mots.accorder("Oh ! {nom} brille… et devient {stade} ! Regarde : anime {nom_min} evolution",
            "nom" to nom, "stade" to nomStade(nouveau), "nom_min" to nom.lowercase()), 14)
        return Mots.accorder("🌟 {nom} devient {stade} ! (anime {nom} evolution)", "nom" to nom, "stade" to nomStade(nouveau))
    }

    /** Chaque commande tapée fait grandir la bestiole active. Renvoie un message si elle évolue. */
    fun apresCommande(jeu: Jeu, colle: Boolean): String? {
        if (colle) return null
        val ind = active(jeu) ?: return null
        return gagner(jeu, ind, 2)
    }

    fun texte(jeu: Jeu): String {
        val caps = Explo.captures(jeu)
        if (caps.length() == 0) return "Ta troupe est vide : joue avec ton familier, un monstre finira par apparaître !"
        val act = active(jeu)
        val sb = StringBuilder("🐾 Troupe de ${jeu.nom}\n")
        for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 12)) {
            val c = caps.getJSONObject(i)
            val e = Bestiaire.espece(c.optString("espece")) ?: continue
            val s = stade(c)
            val seuil = SEUILS[s]
            val r = Bestiaire.rareteDe(c)
            val v = c.optString("variante", "classique")
            sb.append(if (c.optString("id") == act?.optString("id")) "★ " else "   ")
                .append(Bestiaire.balise(c)).append(" ")
                .append(Bestiaire.nomAffiche(e, c.optBoolean("shiny"), r)).append(" · ${nomStade(s)}")
                .append(if (v != "classique") " · $v" else "").append(" · $r · ")
                .append(if (seuil != null) "${c.optInt("xp")}/$seuil XP" else "stade maximal")
                .append(if (Animations.dispo(e.id)) " · animé" else "").append("\n")
        }
        sb.append("\nChoisir l'active : troupe <nom> · la voir bouger : anime <nom> [animation]")
        return sb.toString()
    }

    fun choisir(jeu: Jeu, nom: String): String {
        val e = Bestiaire.espece(nom) ?: return Mots.accorder("Pas encore de « {nom} » dans ta troupe.", "nom" to nom)
        val caps = Explo.captures(jeu)
        for (i in caps.length() - 1 downTo 0) {
            val c = caps.getJSONObject(i)
            if (c.optString("espece") == e.nom) {
                jeu.module("equipe").put("active", c.optString("id"))
                return Mots.accorder("★ {nom} est maintenant ta bestiole active : elle grandit à chaque commande que tu tapes.",
                    "nom" to e.nom)
            }
        }
        return Mots.accorder("Pas encore de « {nom} » dans ta troupe.", "nom" to nom)
    }
}

/**
 * Les animations des bestioles :
 *  - automatiques (AnimAuto, portage de pc/tg/anim_auto.py) pour les 150 espèces, à chaque stade et variante ;
 *  - faites main pour Abyssor (assets/anim/abyssor : gros pixels pixels.json, et version détaillée en .webp).
 */
object Animations {
    private var ctxApp: android.content.Context? = null
    private val index = HashMap<String, JSONObject?>()
    private val calculees = LinkedHashMap<String, AnimAuto.Anim>()

    fun init(ctx: android.content.Context) { ctxApp = ctx.applicationContext }

    private fun index(id: String): JSONObject? = index.getOrPut(id) {
        try { JSONObject(ctxApp!!.assets.open("anim/$id/index.json").bufferedReader().use { it.readText() }) } catch (e: Exception) { null }
    }

    /** Animations détaillées faites main (Abyssor) ? */
    fun dispo(id: String) = index(id) != null

    // ---- gros pixels faits main (48 px, comme dans le terminal PC)
    private val pixelsJson = HashMap<String, JSONObject?>()
    private fun pixelsDe(id: String): JSONObject? = pixelsJson.getOrPut(id) {
        try { JSONObject(ctxApp!!.assets.open("anim/$id/pixels.json").bufferedReader().use { it.readText() }) } catch (e: Exception) { null }
    }

    /** Images par seconde des animations faites main. */
    fun ips(id: String) = pixelsDe(id)?.optInt("ips", 8) ?: AnimAuto.IPS

    /** Les images en gros pixels d'une animation faite main, agrandies sans lissage. stade : noms du nouveau bestiaire. */
    fun pixels(id: String, stade: String, anim: String, echelle: Int = 5): List<Bitmap>? {
        val d = pixelsDe(id) ?: return null
        val anims = d.optJSONObject("anims") ?: return null
        val a = anims.optJSONObject(Equipe.STADES_ABYSSOR[stade] ?: stade)?.optJSONObject(anim)
            ?: anims.optJSONObject(stade)?.optJSONObject(anim) ?: return null
        val n = d.optInt("taille", 48)
        val pal = a.getJSONArray("palette").let { p -> IntArray(p.length() + 1) { if (it == 0) 0 else Bestiaire.hexa(p.getString(it - 1)) or 0xFF000000.toInt() } }
        val imgs = a.getJSONArray("images")
        return (0 until imgs.length()).map { k ->
            val brut = java.util.Base64.getDecoder().decode(imgs.getString(k))
            val octets = if (d.optString("format") == "zlib") Bestiaire.gonfler(brut, n * n) else brut
            val px = IntArray(n * n) { pal[octets[it].toInt() and 0xFF] }
            val b = Bitmap.createBitmap(px, n, n, Bitmap.Config.ARGB_8888)
            Bitmap.createScaledBitmap(b, n * echelle, n * echelle, false)
        }
    }

    /** La version détaillée faite main (pour les fiches d'Abyssor) : première image de l'animation au repos. */
    fun detaille(id: String, stade: String = "adulte"): Bitmap? = images(id, Equipe.STADES_ABYSSOR[stade] ?: stade, "statique")?.firstOrNull()

    fun images(id: String, stade: String, anim: String): List<Bitmap>? {
        val ix = index(id) ?: return null
        val n = ix.optJSONObject("anims")?.optJSONObject(stade)?.optInt(anim) ?: 0
        if (n == 0) return null
        val bande = try { ctxApp!!.assets.open("anim/$id/$stade/$anim.webp").use { BitmapFactory.decodeStream(it) } } catch (e: Exception) { null } ?: return null
        val t = bande.height
        return (0 until n).map { Bitmap.createBitmap(bande, it * t, 0, t, t) }
    }

    // ---- animations automatiques
    /**
     * Calcule (et garde en cache) une animation automatique d'une bestiole. Pour « evolution », stade est le
     * stade d'arrivée : on part du stade précédent.
     */
    fun auto(e: Bestiaire.Espece, stade: String, vid: String, anim: String): AnimAuto.Anim? {
        val cle = "${e.id}/$vid/$stade/$anim"
        synchronized(calculees) { calculees[cle]?.let { return it } }
        val img = Bestiaire.image(e, stade, vid) ?: return null
        var de: AnimAuto.Sprite? = null
        val i = Equipe.STADES.indexOf(stade)
        if (anim == "evolution" && i > 0) de = Bestiaire.image(e, Equipe.STADES[i - 1], vid)
        val a = AnimAuto.images(img, anim, de)
        synchronized(calculees) {
            calculees[cle] = a
            while (calculees.size > 24) calculees.remove(calculees.keys.first())
        }
        return a
    }

    /** Les images d'une bestiole (individu) pour une animation : faites main pour Abyssor, automatiques sinon. */
    fun pour(ind: JSONObject, anim: String, stade: String, echelle: Int): Pair<List<Bitmap>, Int>? {
        val e = Bestiaire.espece(ind.optString("espece")) ?: return null
        val shiny = ind.optBoolean("shiny")
        val teinte = ind.optDouble("teinte", 0.5)
        if (dispo(e.id)) {
            val p = pixels(e.id, stade, anim, echelle) ?: return null
            return p to ips(e.id)
        }
        val a = auto(e, stade, ind.optString("variante", "classique"), anim) ?: return null
        return AnimAuto.bitmaps(a, echelle, if (shiny) teinte else null) to a.ips
    }

    /** anime <nom> [animation] : une petite fenêtre qui joue l'animation. */
    fun jouer(act: Activity, ind: JSONObject, animDemandee: String): String {
        val e = Bestiaire.espece(ind.optString("espece")) ?: return "Espèce inconnue."
        var stade = Equipe.stade(ind)
        val anim = animDemandee.lowercase().replace("é", "e").replace("è", "e").ifEmpty { "statique" }
        if (anim !in Equipe.ANIMS) return "Animations : " + Equipe.ANIMS.joinToString(", ")
        if (anim == "evolution") {                 // on rejoue l'évolution qui a mené au stade actuel
            val i = Equipe.STADES.indexOf(stade)
            if (i <= 0) return Mots.accorder("{nom} est encore bébé : pas encore d'évolution à revoir.", "nom" to e.nom)
            if (dispo(e.id)) stade = Equipe.STADES[i - 1]       // les animations faites main partent du stade d'avant
        }
        val (imgs, ips) = pour(ind, anim, stade, if (dispo(e.id)) 5 else 6) ?: return "Pas d'image pour $anim."
        if (imgs.isEmpty()) return "Pas d'image pour $anim."
        val dp = act.resources.displayMetrics.density
        val vue = ImageView(act).apply {
            layoutParams = LinearLayout.LayoutParams((260 * dp).toInt(), (260 * dp).toInt())
            scaleType = ImageView.ScaleType.FIT_CENTER
            if (ind.optBoolean("shiny") && dispo(e.id)) colorFilter = Bestiaire.filtreTeinte(ind.optDouble("teinte", 0.5))
        }
        vue.setImageBitmap(imgs[0])
        val r = Bestiaire.rareteDe(ind)
        val titre = TextView(act).apply {
            text = "${e.nom}${if (ind.optBoolean("shiny")) " ✨" else ""} · ${Equipe.nomStade(Equipe.stade(ind))} · $anim"
            setTextColor(Bestiaire.COULEUR_RARETE[r] ?: 0xFFFFAF00.toInt()); textSize = 15f; gravity = Gravity.CENTER
        }
        val boite = LinearLayout(act).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER
            setPadding((16 * dp).toInt(), (16 * dp).toInt(), (16 * dp).toInt(), (8 * dp).toInt())
            setBackgroundColor(0xFF14141E.toInt()); addView(titre); addView(vue)
        }
        val h = Handler(Looper.getMainLooper())
        var k = 0
        val tours = if (anim == "evolution") 1 else 3
        val pause = (1000L / maxOf(1, ips))
        val dlg = AlertDialog.Builder(act).setView(boite).setPositiveButton("OK", null).create()
        val pas = object : Runnable {
            override fun run() {
                if (!dlg.isShowing) return
                k++
                if (k >= imgs.size * tours) { if (anim != "evolution") k = 0 else return }
                vue.setImageBitmap(imgs[k % imgs.size])
                h.postDelayed(this, pause)
            }
        }
        dlg.setOnShowListener { h.postDelayed(pas, pause) }
        dlg.show()
        return if (anim == "evolution") Mots.accorder("▶ {nom} : nouvelle forme, {stade} !", "nom" to e.nom, "stade" to Equipe.nomStade(Equipe.stade(ind)))
        else "▶ ${e.nom} : $anim"
    }
}
