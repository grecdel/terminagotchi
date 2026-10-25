package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

/**
 * La langue de l'interface (même système que pc/tg/langue.py) : 14 langues, le français par défaut.
 *
 *   t(clé, "nom" to valeur…)  le texte de la clé dans la langue choisie (repli sur le français si la clé manque),
 *                             avec les {params} remplis ; en français, l'élision se fait toute seule
 *                             (« de {nom} » + Inodin → « d'Inodin », voir Mots.remplir).
 *   Langue.liste(clé)         une liste de phrases (pour en tirer une au hasard).
 *   Langue.definir(code)      change la langue courante (commande « langue xx » du terminal).
 *   Langue.detecter()         la langue du téléphone (Locale), au premier lancement.
 *
 * Les textes sont dans assets/langues/xx.json. Les clés communes avec le PC (pc/tg/langues/xx.json) ont
 * le même nom et le même texte ; les autres sont propres à Android (téléphone, donjon, CTF, Doom, widget…).
 * Contrôle : python3 tests/langues_android.py
 * Les noms et descriptions des monstres (bestiaire.json) ne sont PAS traduits, ni les commandes à taper.
 *
 * Arabe et ourdou (de droite à gauche) : le TextView d'Android range les mots tout seul. Pour que les
 * commandes et le code restent lisibles de gauche à droite, chaque morceau de code latin est isolé
 * (marques LRI … PDI) et chaque ligne écrite en arabe commence par une marque RLM (voir bidi()).
 *
 * Largeur à l'écran : un caractère chinois ou japonais prend 2 colonnes (largeur(), ajuster()).
 */
object Langue {
    val LANGUES: Map<String, String> = linkedMapOf(
        "fr" to "Français", "en" to "English", "es" to "Español", "de" to "Deutsch", "it" to "Italiano",
        "pt" to "Português", "zh" to "中文", "ru" to "Русский", "ja" to "日本語", "hi" to "हिन्दी",
        "ar" to "العربية", "bn" to "বাংলা", "id" to "Bahasa Indonesia", "ur" to "اردو",
    )
    const val DEFAUT = "fr"
    val DROITE_A_GAUCHE = setOf("ar", "ur")

    @Volatile var courante: String = DEFAUT
        private set

    /** Lit assets/langues/<code>.json (réglé par init ; les tests JVM lisent le dossier directement). */
    @Volatile var chargeur: ((String) -> String?)? = null
    private val textes = HashMap<String, JSONObject>()

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { code ->
            try { app.assets.open("langues/$code.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null }
        }
    }

    private fun charger(code: String): JSONObject = synchronized(textes) {
        textes.getOrPut(code) {
            try { chargeur?.invoke(code)?.let { JSONObject(it) } ?: JSONObject() } catch (e: Exception) { JSONObject() }
        }
    }

    /** Change la langue courante (code inconnu → français). */
    fun definir(code: String?): String {
        courante = codeValide(code) ?: DEFAUT
        return courante
    }

    /** « en », « EN », « pt_BR », « zh-Hans »… → le code connu, sinon null. */
    fun codeValide(code: String?): String? {
        val c = (code ?: "").trim().lowercase(Locale.ROOT).replace('-', '_').substringBefore('_')
        val k = when (c) { "in" -> "id"; else -> c }           // ancien code Java de l'indonésien
        return if (k in LANGUES) k else null
    }

    /** La langue du téléphone (premier lancement), sinon le français. */
    fun detecter(locale: Locale = Locale.getDefault()): String = codeValide(locale.language) ?: DEFAUT

    val rtl: Boolean get() = courante in DROITE_A_GAUCHE

    /** La valeur d'une clé (texte ou liste) dans la langue demandée, sinon en français, sinon null. */
    fun brut(cle: String, code: String = courante): Any? {
        val v = charger(code).opt(cle)
        if (v != null && v != JSONObject.NULL) return v
        if (code != DEFAUT) charger(DEFAUT).opt(cle)?.let { if (it != JSONObject.NULL) return it }
        return null
    }

    fun existe(cle: String) = brut(cle) != null

    /** Le modèle brut d'une clé (ni rempli ni mis en forme), pour le remplir plus tard avec remplir(). */
    fun modele(cle: String): String {
        val v = brut(cle) ?: return cle
        return if (v is JSONArray) v.optString(0) else v.toString()
    }

    /** Le texte d'une clé, traduit et rempli. Une clé inconnue s'affiche telle quelle. */
    fun t(cle: String, vararg params: Pair<String, Any?>): String {
        val v = brut(cle) ?: return cle
        val modele = if (v is JSONArray) v.optString(0) else v.toString()
        return remplir(modele, params.associate { it.first to (it.second?.toString() ?: "") })
    }

    /** t(), ou `defaut` si la clé n'existe pas (noms venus de la sauvegarde : compétences, stats…). */
    fun ou(cle: String, defaut: String, vararg params: Pair<String, Any?>): String =
        if (existe(cle)) t(cle, *params) else defaut

    /** Une liste de phrases (non remplies). */
    fun liste(cle: String): List<String> {
        val v = brut(cle) ?: return listOf(cle)
        if (v is JSONArray) return (0 until v.length()).map { bidi(v.optString(it)) }.ifEmpty { listOf(cle) }
        return listOf(bidi(v.toString()))
    }

    /** Les valeurs brutes d'une clé dans une langue précise (sans repli ni mise en forme) : mots acceptés au clavier… */
    fun valeurs(cle: String, code: String): List<String> {
        val v = charger(code).opt(cle) ?: return emptyList()
        return if (v is JSONArray) (0 until v.length()).map { v.optString(it) } else listOf(v.toString())
    }

    /** Les valeurs brutes dans la langue choisie, sinon en français : pour les données écrites dans des fichiers. */
    fun brutes(cle: String): List<String> = valeurs(cle, courante).ifEmpty { valeurs(cle, DEFAUT) }

    fun auHasard(cle: String, vararg params: Pair<String, Any?>): String {
        val v = brut(cle) ?: return cle
        val l = if (v is JSONArray) (0 until v.length()).map { v.optString(it) } else listOf(v.toString())
        return remplir(l.random(), params.associate { it.first to (it.second?.toString() ?: "") })
    }

    /** Remplit {params} (élision en français), puis prépare l'écriture de droite à gauche si besoin. */
    fun remplir(modele: String, v: Map<String, String>): String {
        val m = if (courante == DEFAUT) Mots.remplir(modele, v)
            else TROU.replace(modele) { r -> v[r.groupValues[1]] ?: v[r.groupValues[1].lowercase()] ?: r.value }
        return bidi(m.replace("{{", "{").replace("}}", "}"))
    }
    private val TROU = Regex("\\{(\\w+)\\}")

    // ---------------------------------------------------------------- droite à gauche (arabe, ourdou)
    private const val LRI = "⁦"
    private const val PDI = "⁩"
    private const val RLM = "‏"
    // un morceau de code : commence et finit par un caractère « de code », contient une lettre latine ou un chiffre
    private const val LAT = "A-Za-z0-9À-ÖØ-öø-ɏаседорхуіѕԁһј"
    private val CODE = Regex("[$LAT~./_\\-$\\[{\"'<>|&*#(@%]" +
        "(?:[\\x20-\\x7E …À-ÖØ-öø-ɏаседорхуіѕԁһј]*[$LAT/_}\\]\"'*…~>)%])?")
    private val LETTRE = Regex("[$LAT]")
    private val ARABE = Regex("[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
    private val BALISE = Regex("¤[^¤]*¤")

    /**
     * En arabe et en ourdou : isole chaque morceau de code latin (LRI … PDI) pour qu'il reste lisible de gauche
     * à droite au milieu de la phrase, et commence chaque ligne écrite en arabe par RLM (la ligne s'aligne à
     * droite même si elle commence par une commande). Ne touche pas aux balises de dessin ¤…¤.
     * Dans les autres langues, le texte ne change pas.
     */
    fun bidi(s: String): String {
        if (!rtl || !ARABE.containsMatchIn(s) || LRI in s) return s
        val sb = StringBuilder()
        var i = 0
        fun isoler(morceau: String) = CODE.replace(morceau) { m -> if (LETTRE.containsMatchIn(m.value)) LRI + m.value + PDI else m.value }
        for (b in BALISE.findAll(s)) {
            sb.append(isoler(s.substring(i, b.range.first))).append(b.value)
            i = b.range.last + 1
        }
        sb.append(isoler(s.substring(i)))
        return sb.toString().split("\n").joinToString("\n") { l -> if (ARABE.containsMatchIn(l) && !l.startsWith(RLM)) RLM + l else l }.replace(RLM + RLM, RLM)
    }

    // ---------------------------------------------------------------- largeur d'affichage
    /** Colonnes occupées par un caractère : 2 pour le chinois, le japonais, le coréen (et les émojis larges), 0 pour les marques. */
    fun largeurCar(cp: Int): Int {
        val type = Character.getType(cp)
        if (type == Character.NON_SPACING_MARK.toInt() || type == Character.ENCLOSING_MARK.toInt() || type == Character.FORMAT.toInt()) return 0
        return if ((cp in 0x1100..0x115F) || (cp in 0x2E80..0x303E) || (cp in 0x3041..0x33FF) || (cp in 0x3400..0x4DBF) ||
            (cp in 0x4E00..0x9FFF) || (cp in 0xA000..0xA4CF) || (cp in 0xAC00..0xD7A3) || (cp in 0xF900..0xFAFF) ||
            (cp in 0xFE30..0xFE4F) || (cp in 0xFF00..0xFF60) || (cp in 0xFFE0..0xFFE6) || (cp in 0x1F300..0x1F64F) ||
            (cp in 0x1F900..0x1F9FF) || (cp in 0x20000..0x3FFFD)) 2 else 1
    }

    /** Nombre de colonnes occupées à l'écran (CJK = 2 colonnes). */
    fun largeur(s: String): Int {
        var n = 0
        var i = 0
        while (i < s.length) { val cp = s.codePointAt(i); n += largeurCar(cp); i += Character.charCount(cp) }
        return n
    }

    /** Complète avec des espaces jusqu'à n colonnes. */
    fun ajuster(s: String, n: Int): String = s + " ".repeat(maxOf(0, n - largeur(s)))
}

/** Le texte d'une clé dans la langue choisie (voir Langue). */
fun t(cle: String, vararg params: Pair<String, Any?>): String = Langue.t(cle, *params)
