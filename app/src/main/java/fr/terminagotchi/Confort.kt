package fr.terminagotchi

import org.json.JSONObject

/**
 * Lecture et confort (comme pc/tg/confort.py, vecteurs communs donnees/confort/vecteurs.json, test tests/jvm/Confort.kt) :
 * taille du texte (100 / 125 / 150 %), police « Lecture facile » (Andika, OFL, si assets/polices/Andika-Regular.ttf est
 * là ; sinon la police habituelle un peu plus grande et plus espacée), « Couleurs + formes » (■ ▲ ● ◆ ━ sur la vue
 * déployée ; auto : avec les thèmes Contraste élevé et Daltonien), mode calme (rien ne clignote ni ne secoue ; auto :
 * « Supprimer les animations » d'Android).
 * Sauvegarde : jeu.module("confort") = {taille, police, formes, calme, date} ; absents = auto. La police, les formes et
 * le calme suivent le recensement (le plus récent gagne) ; la taille reste propre au téléphone.
 */
object Confort {
    val TAILLES = listOf(100, 125, 150)
    val POLICES = listOf("normale", "facile")
    val FORMES = mapOf("commande" to "■", "option" to "▲", "argument" to "●", "chemin" to "◆", "tuyau" to "━",
        "redirection" to "▼", "lien" to "✚")
    val THEMES_FORMES = setOf("contraste", "daltonien")
    const val FACILE_TAILLE = 1.08f
    const val FACILE_ESPACE = 0.06f

    /** Ce que le téléphone demande déjà (TerminalActivity le remplit au démarrage). */
    @Volatile var echelleSysteme = 1.0
    @Volatile var moinsAnimations = false

    data class Reglages(val taille: Int, val police: String, val formes: Boolean, val calme: Boolean) {
        val zoom get() = taille / 100f
        val facile get() = police == "facile"
    }

    fun tailleDe(echelle: Double): Int = if (echelle < 1.12) 100 else if (echelle < 1.37) 125 else 150

    /** Le calcul pur (mêmes vecteurs que Python). */
    fun resoudre(c: JSONObject?, theme: String, echelle: Double, moins: Boolean): Reglages {
        val cc = c ?: JSONObject()
        val ta = cc.opt("taille").let { if (it is Number && it.toInt() in TAILLES && it.toDouble() == it.toInt().toDouble()) it.toInt() else tailleDe(echelle) }
        val po = cc.opt("police").let { if (it is String && it in POLICES) it else "normale" }
        val fo = cc.opt("formes").let { if (it is Boolean) it else theme in THEMES_FORMES }
        val ca = cc.opt("calme").let { if (it is Boolean) it else moins }
        return Reglages(ta, po, fo, ca)
    }

    fun tailleSuivante(taille: Int, sens: Int): Int {
        val i = TAILLES.indexOf(taille).coerceAtLeast(0)
        return TAILLES[(i + if (sens > 0) 1 else -1).coerceIn(0, TAILLES.size - 1)]
    }

    fun c(jeu: Jeu): JSONObject = jeu.module("confort")

    fun reglages(jeu: Jeu?): Reglages =
        if (jeu == null) resoudre(null, "sombre", echelleSysteme, moinsAnimations)
        else resoudre(c(jeu), Apparence.cleTheme(jeu), echelleSysteme, moinsAnimations)

    fun calme(jeu: Jeu?) = reglages(jeu).calme

    /** valeur null : auto. Renvoie false si la valeur n'est pas permise. */
    fun regler(jeu: Jeu, cle: String, valeur: Any?): Boolean {
        val ok = when (cle) {
            "taille" -> valeur == null || (valeur is Int && valeur in TAILLES)
            "police" -> valeur == null || (valeur is String && valeur in POLICES)
            "formes", "calme" -> valeur == null || valeur is Boolean
            else -> false
        }
        if (!ok) return false
        val c = c(jeu)
        if (valeur == null) c.remove(cle) else c.put(cle, valeur)
        if (cle != "taille") c.put("date", System.currentTimeMillis())
        activer(jeu)
        return true
    }

    fun activer(jeu: Jeu?) { Glitch.calme = calme(jeu) }

    /** Pour le recensement : (« facile,formes1,calme0 », date). */
    fun pourRecensement(jeu: Jeu): Pair<String, Long> {
        val c = c(jeu)
        val m = mutableListOf<String>()
        if (c.optString("police") == "facile") m.add("facile")
        for (k in listOf("formes", "calme")) (c.opt(k) as? Boolean)?.let { m.add(k + if (it) "1" else "0") }
        return m.joinToString(",") to c.optLong("date")
    }

    fun depuisRecensement(jeu: Jeu, texte: String?, date: Long): Boolean {
        val c = c(jeu)
        if (texte == null || date <= c.optLong("date") || texte.length > 40) return false
        val mots = texte.split(",").filter { it.isNotEmpty() }.toSet()
        if (!setOf("facile", "formes0", "formes1", "calme0", "calme1").containsAll(mots)) return false
        c.remove("police"); if ("facile" in mots) c.put("police", "facile")
        for (k in listOf("formes", "calme")) {
            c.remove(k)
            if ("${k}1" in mots) c.put(k, true) else if ("${k}0" in mots) c.put(k, false)
        }
        c.put("date", date)
        activer(jeu)
        return true
    }

    private val NOMS_TAILLE = mapOf("normal" to 100, "normale" to 100, "grand" to 125, "big" to 125, "large" to 125,
        "tresgrand" to 150, "très-grand" to 150, "tres-grand" to 150, "huge" to 150)
    private val MOTS = mapOf("oui" to true, "on" to true, "yes" to true, "1" to true, "non" to false, "off" to false,
        "no" to false, "0" to false)

    fun lignes(jeu: Jeu): String {
        val r = reglages(jeu)
        val c = c(jeu)
        fun auto(k: String) = if (c.has(k)) "" else " (" + t("conf.auto") + ")"
        fun oui(b: Boolean) = if (b) t("app.on") else t("app.off")
        return listOf("── " + t("conf.titre") + " ──",
            "  " + t("conf.taille") + " : " + t("conf.taille.${r.taille}") + auto("taille"),
            "  " + t("conf.police") + " : " + t("conf.police.${r.police}") + auto("police"),
            "  " + t("conf.formes") + " : " + oui(r.formes) + auto("formes"),
            "  " + t("conf.calme") + " : " + oui(r.calme) + auto("calme"),
            t("conf.aide.tel")).joinToString("\n")
    }

    /** `confort [taille 125 | police facile | formes oui | calme non | … auto]` */
    fun commande(jeu: Jeu, args: List<String>): String {
        if (args.size < 2) return lignes(jeu)
        var cle = args[0].lowercase()
        val v = args[1].lowercase()
        var ok = false
        var valeur: Any? = null
        when (cle) {
            "taille", "size", "texte" -> {
                cle = "taille"
                val n = v.trimEnd('%').toIntOrNull()
                if (v == "auto") ok = true
                else if (n != null && n in TAILLES) { valeur = n; ok = true }
                else NOMS_TAILLE[v.replace(" ", "")]?.let { valeur = it; ok = true }
            }
            "police", "font" -> {
                cle = "police"
                when (v) { "normale", "normal" -> { valeur = "normale"; ok = true }; "facile", "easy" -> { valeur = "facile"; ok = true }; "auto" -> ok = true }
            }
            "formes", "shapes", "calme", "calm" -> {
                cle = if (cle == "formes" || cle == "shapes") "formes" else "calme"
                if (v == "auto") ok = true else MOTS[v]?.let { valeur = it; ok = true }
            }
        }
        if (!ok || !regler(jeu, cle, valeur)) return t("conf.faux") + "\n" + lignes(jeu)
        jeu.sauver()
        return "✓ " + t("conf.ok") + "\n" + lignes(jeu)
    }
}
