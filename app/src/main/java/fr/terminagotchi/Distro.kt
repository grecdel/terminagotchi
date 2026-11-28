package fr.terminagotchi

import org.json.JSONObject

/**
 * La distribution Linux pratiquée (28 nov., mêmes règles que pc/tg/distro.py, données : assets/distros.json).
 * Sur le téléphone, rien n'est à détecter (Android n'est pas une distribution) : « auto » garde le magasin raconté,
 * un choix (⚙ Réglages › 🐧, ou `distro fedora`) adapte les conseils et le magasin de paquets montrés par le jeu.
 * Sauvegarde : jeu.module("distro").choix.
 */
object Distro {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("distros.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    fun ordre(): List<String> = donnees().optJSONArray("ordre")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()

    fun choix(jeu: Jeu): String = jeu.module("distro").optString("choix", "auto").ifEmpty { "auto" }

    /** la distribution pratiquée, ou null (auto sur un téléphone) */
    fun courante(jeu: Jeu): String? = choix(jeu).takeIf { it != "auto" && donnees().optJSONObject("distros")?.has(it) == true }

    fun nom(cle: String?): String = cle?.let { donnees().optJSONObject("distros")?.optJSONObject(it)?.optString("nom") } ?: "?"

    /** le magasin de paquets d'une distribution : id, installer, maj, compte (ou null) */
    fun magasin(cle: String?): JSONObject? {
        val x = cle?.let { donnees().optJSONObject("distros")?.optJSONObject(it) } ?: return null
        val id = x.optString("magasin")
        val m = donnees().optJSONObject("magasins")?.optJSONObject(id) ?: return null
        return JSONObject(m.toString()).put("id", id)
    }

    fun installer(cle: String?, paquet: String): String? {
        val m = magasin(cle) ?: return null
        val p = m.optJSONObject("paquets")?.optString(paquet)?.ifEmpty { null } ?: paquet
        return m.optString("installer").replace("{p}", p)
    }

    /** le texte du réglage : « Fedora » ou « automatique (aucune) » */
    fun etat(jeu: Jeu): String = courante(jeu)?.let { nom(it) } ?: t("dist.auto_nom", "nom" to t("dist.aucune"))

    /** le réglage suivant, quand on touche la ligne des réglages : auto → ubuntu → … → opensuse → auto */
    fun suivante(jeu: Jeu): String {
        val o = listOf("auto") + ordre()
        val i = o.indexOf(choix(jeu))
        return changer(jeu, o[(i + 1) % o.size])
    }

    fun changer(jeu: Jeu, valeur: String): String {
        val v = valeur.trim().lowercase()
        val ds = donnees().optJSONObject("distros") ?: JSONObject()
        if (v == "auto") {
            jeu.module("distro").put("choix", "auto")
            return "🐧 " + t("dist.choisie", "nom" to t("dist.auto_nom", "nom" to t("dist.aucune")))
        }
        val trouve = ds.keys().asSequence().firstOrNull { c ->
            val x = ds.getJSONObject(c)
            val ids = x.optJSONArray("ids")
            v == c || v == x.optString("nom").lowercase() || (ids != null && (0 until ids.length()).any { ids.getString(it) == v })
        } ?: return t("dist.inconnue", "nom" to valeur, "liste" to (ordre() + "auto").joinToString(", "))
        jeu.module("distro").put("choix", trouve)
        return "🐧 " + t("dist.choisie", "nom" to nom(trouve))
    }

    fun ecran(jeu: Jeu): List<String> {
        val cle = courante(jeu)
        val l = mutableListOf("🐧 " + t("dist.titre", "nom" to (cle?.let { nom(it) } ?: t("dist.aucune"))))
        magasin(cle)?.let { m -> l.add("   " + t("dist.magasin", "magasin" to m.optString("id"), "cmd" to m.optString("installer").replace("{p}", "cowsay"))) }
        l.add("   " + t("dist.aide", "cmd" to "`distro fedora`", "cmd2" to "`distro auto`", "liste" to ordre().joinToString(", ")))
        return l
    }

    /** Le magasin de paquets raconté par le Poste de Contrôle : celui de la distribution choisie, sinon le texte général. */
    fun lignesMagasin(jeu: Jeu): List<String> {
        val cle = courante(jeu)
        val m = magasin(cle) ?: return listOf("  " + t("ct.magasin.raconte"))
        return listOf("  " + t("ct.magasin.le_tien", "magasin" to m.optString("id")) + " (" + nom(cle) + ")", "",
            "  " + t("ct.magasin.compter"), "    " + m.optString("compte"), "",
            "  " + t("ct.magasin.adulte"), "    " + m.optString("installer").replace("{p}", "cowsay"), "    " + m.optString("maj"))
    }
}
