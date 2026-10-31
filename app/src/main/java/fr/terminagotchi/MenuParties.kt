package fr.terminagotchi

import android.app.Activity
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Le menu des parties, en texte, dans le terminal (même rendu que pc/tg/accueil.py) :
 *
 *   ┌ Terminagotchi ┐
 *   1  continuer    Pixel · Bébé niv. 4
 *   2  nouvelle partie
 *   3  charger
 *   4  compte       (non connecté)
 *
 * On répond par le chiffre ou le mot, en français ou dans la langue choisie (clés part.mots.*), et « oui » se dit
 * dans n'importe laquelle des 14 langues (part.oui). Une autre commande ferme le menu et part au terminal.
 * Commandes utilisables à tout moment : parties · partie nouvelle · partie charger [n].
 * Les parties elles-mêmes sont rangées par Parties.kt.
 */
class MenuParties(
    private val act: Activity,
    private val jeu: Jeu,
    /** la partie active a changé : le terminal se recharge */
    private val apresChangement: () -> Unit,
    /** synchroniser la partie active (si un compte est relié) */
    private val synchroniser: () -> Unit,
    /** le texte de « compte » (état du compte et commandes) */
    private val texteCompte: () -> String,
    /** réponse qui arrive plus tard (liste du compte en ligne) */
    private val plusTard: (String) -> Unit,
) {
    /** null = menu fermé ; sinon "menu", "nouvelle" (oui/non) ou "charger" (un numéro) */
    var etat: String? = null
        private set

    /** les numéros de « charger » : (id de la partie, nom si elle vient du compte en ligne, sinon null) */
    private val choix = mutableListOf<Pair<String, String?>>()
    private val format = SimpleDateFormat("dd/MM HH:mm", Locale.FRANCE)

    val ouvert: Boolean get() = etat != null

    private fun espece(stade: Int, forme: String?) = Regles.espece(stade, forme)

    companion object {
        private fun norm(s: String) = java.text.Normalizer.normalize(s.trim().lowercase(), java.text.Normalizer.Form.NFC)

        /** Les mots acceptés pour une action du menu : ceux de la langue choisie, et toujours ceux du français. */
        fun mots(cle: String): Set<String> =
            (Langue.valeurs(cle, Langue.courante) + Langue.valeurs(cle, Langue.DEFAUT)).map { norm(it) }.toSet()

        /** « oui » dans n'importe laquelle des 14 langues (oui, yes, sí, ja, да, はい, 是, हाँ, نعم…). */
        fun oui(reponse: String): Boolean {
            val r = norm(reponse)
            return r.isNotEmpty() && Langue.LANGUES.keys.any { code -> Langue.valeurs("part.oui", code).any { norm(it) == r } }
        }

        /** « non » dans n'importe laquelle des 14 langues (v3, I14 : « non » n'est pas un nom d'œuf). */
        fun non(reponse: String): Boolean {
            val r = norm(reponse)
            return r.isNotEmpty() && Langue.LANGUES.keys.any { code -> Langue.valeurs("part.non", code).any { norm(it) == r } }
        }

        /** L'action du menu que désigne une réponse (chiffre ou mot) : continuer, nouvelle, charger, compte, ou null. */
        fun action(reponse: String): String? {
            val r = norm(reponse)
            return when {
                r == "" || r == "1" || r in mots("part.mots.continuer") -> "continuer"
                r == "2" || r in mots("part.mots.nouvelle") -> "nouvelle"
                r == "3" || r in mots("part.mots.charger") -> "charger"
                r == "4" || r in mots("part.mots.compte") -> "compte"
                else -> null
            }
        }
    }

    fun ouvrir(): String {
        etat = "menu"
        val c = Recensement.compte(jeu)
        val qui = if (jeu.existe) t("part.qui", "nom" to jeu.nom + (if (jeu.shiny) " ✨" else ""),
                "espece" to Regles.espece(jeu.stade, jeu.forme, jeu.especeCompagnon), "n" to jeu.niveau)
            else t("part.oeuf_sans_nom")
        val compte = if (Recensement.aUnCompte(jeu)) c.optString("pseudo") else t("part.non_connecte")
        return "┌ Terminagotchi ┐\n" +
            "1  " + t("part.m.continuer") + "    " + qui + "\n" +
            "2  " + t("part.m.nouvelle") + "\n" +
            "3  " + t("part.m.charger") + "\n" +
            "4  " + t("part.m.compte") + "       " + compte + "\n" +
            t("part.m.aide.tel")
    }

    /** Une ligne tapée pendant que le menu est ouvert. null : ce n'est pas pour le menu (il se ferme). */
    fun repondre(ligne: String): String? {
        val l = ligne.trim().lowercase()
        when (etat) {
            "menu" -> return when (action(l)) {
                "continuer" -> { etat = null; continuer() }
                "nouvelle" -> nouvelle()
                "charger" -> charger()
                "compte" -> { etat = null; texteCompte() }
                else -> { etat = null; null }
            }
            "nouvelle" -> {
                if (oui(l)) return creer()
                return t("part.n.rien") + "\n" + ouvrir()
            }
            "charger" -> {
                if (l.isEmpty() || norm(l) in mots("part.mots.retour")) return ouvrir()
                val n = l.toIntOrNull() ?: return null.also { etat = null }
                return choisir(n)
            }
        }
        return null
    }

    /** partie nouvelle · partie charger [n] · partie (= la liste) */
    fun commande(reste: String): String {
        val m = reste.trim().lowercase().split(Regex("\\s+")).filter { it.isNotEmpty() }
        return when (m.firstOrNull()) {
            "nouvelle" -> nouvelle()
            "charger", null, "liste" -> {
                val n = m.getOrNull(1)?.toIntOrNull()
                if (n == null) charger() else { lister(false); choisir(n) }
            }
            else -> t("part.aide.tel")
        }
    }

    private fun continuer(): String =
        if (jeu.existe) t("part.continuer", "nom" to jeu.nom) else "🥚 " + t("app.nom_creature")

    // ---------------------------------------------------------------- nouvelle partie
    private fun nouvelle(): String {
        if (!jeu.existe) { etat = null; return t("part.n.attend") }
        if (Parties.pleine(act)) {
            etat = "menu"
            return t("part.plein", "n" to Parties.MAX)
        }
        etat = "nouvelle"
        return t("part.n.confirmer", "nom" to jeu.nom) +
            "  " + t("part.oui_non")
    }

    private fun creer(): String {
        etat = null
        jeu.sauver()
        if (Parties.nouvelle(act) == null) return t("part.n.echec")
        jeu.recharger()
        apresChangement()
        return t("part.n.ok.tel")
    }

    // ---------------------------------------------------------------- charger
    private fun lister(avecCompte: Boolean): String {
        choix.clear()
        val sb = StringBuilder("┌ " + t("part.l.titre") + " ┐")
        for (r in Parties.liste(act)) {
            choix.add(r.id to null)
            sb.append("\n${choix.size}  " + t("part.l.ligne", "nom" to r.nom.ifEmpty { t("part.oeuf_sans_nom") },
                "espece" to r.espece, "n" to r.niveau, "date" to format.format(Date(r.date))))
            if (r.active) sb.append("  " + t("part.l.en_cours"))
        }
        if (avecCompte && Recensement.aUnCompte(jeu)) {
            // d'abord ce qu'on sait déjà (cache local, marche hors ligne), puis un coup d'œil rapide au site, en fond
            val cache = Recensement.compte(jeu).optJSONArray("parties_cache") ?: JSONArray()
            val deja = ajouterCompte(cache)
            sb.append(if (deja.isEmpty()) "\n☁ " + t("part.l.je_regarde") else "\n☁ " + t("part.l.sur_compte") + deja)
            rafraichirCompte()
        }
        return sb.toString()
    }

    private fun charger(): String {
        etat = "charger"
        return lister(true) + "\n" + t("part.l.numero")
    }

    /** Ajoute aux numéros les parties du compte qui ne sont pas encore listées ; renvoie leurs lignes. */
    private fun ajouterCompte(a: JSONArray): String {
        val sb = StringBuilder()
        val ici = choix.map { it.first }.toSet()
        for (i in 0 until a.length()) {
            val p = a.optJSONObject(i) ?: continue
            val id = p.optString("partie")
            if (id.isEmpty() || id in ici) continue
            val niv = p.optInt("niveau", 1)
            choix.add(id to p.optString("nom"))
            sb.append("\n${choix.size}  " + t("part.qui", "nom" to p.optString("nom"),
                "espece" to espece(Regles.stade(niv), if (p.isNull("forme")) null else p.optString("forme")), "n" to niv))
        }
        return sb.toString()
    }

    /** En fond, avec un délai court : la liste du compte en ligne (gardée en cache pour le hors-ligne). */
    private fun rafraichirCompte() {
        val c = Recensement.compte(jeu)
        val cle = c.optString("cle")
        val serveur = c.optString("serveur")
        Thread {
            val a = try {
                if (serveur.isEmpty()) null else {
                    val cx = java.net.URL("$serveur/api/parties").openConnection() as java.net.HttpURLConnection
                    cx.connectTimeout = 3000
                    cx.readTimeout = 4000
                    cx.setRequestProperty("authorization", "Bearer $cle")
                    cx.setRequestProperty("user-agent", "terminagotchi-android")
                    if (cx.responseCode != 200) null
                    else JSONObject(cx.inputStream.bufferedReader().use { it.readText() }).optJSONArray("parties")
                }
            } catch (e: Exception) {
                null
            }
            act.runOnUiThread {
                if (a != null && Recensement.compte(jeu).optString("cle") == cle) Recensement.compte(jeu).put("parties_cache", a)
                if (etat != "charger") return@runOnUiThread
                if (a == null) { plusTard("☁ " + t("part.l.hors_ligne.tel")); return@runOnUiThread }
                val nouvelles = ajouterCompte(a)
                if (nouvelles.isNotEmpty()) plusTard("☁ " + t("part.l.sur_compte") + nouvelles)
            }
        }.start()
    }

    private fun choisir(n: Int): String {
        val (id, duCompte) = choix.getOrNull(n - 1) ?: return t("part.l.pas_de_numero", "n" to n) + " " +
            t("part.l.tape_numero")
        etat = null
        if (id == jeu.partie) return continuer()
        jeu.sauver()
        val ok = if (duCompte != null) Parties.depuisCompte(act, id, duCompte) else Parties.charger(act, id)
        if (!ok) return if (Parties.pleine(act)) t("part.plein.court", "n" to Parties.MAX)
            else t("part.l.echec")
        jeu.recharger()
        apresChangement()
        if (Recensement.aUnCompte(jeu)) synchroniser()
        return if (duCompte != null) t("part.l.depuis_compte", "nom" to duCompte)
            else t("part.l.ok", "qui" to t("part.qui", "nom" to jeu.nom, "espece" to Regles.espece(jeu.stade, jeu.forme, jeu.especeCompagnon), "n" to jeu.niveau))
    }
}
