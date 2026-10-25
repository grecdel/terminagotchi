package fr.terminagotchi

import android.app.Activity
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
 * On répond par le chiffre ou le mot. Une autre commande ferme le menu et part au terminal.
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

    private fun espece(stade: Int, forme: String?) =
        Regles.STADES[stade] + if (stade >= 2 && forme != null) " ${Regles.FORMES[forme] ?: ""}" else ""

    fun ouvrir(): String {
        etat = "menu"
        val c = Recensement.compte(jeu)
        val qui = if (jeu.existe) "${jeu.nom}${if (jeu.shiny) " ✨" else ""} · ${espece(jeu.stade, jeu.forme)} niv. ${jeu.niveau}"
            else "(un œuf attend son nom)"
        val compte = if (Recensement.aUnCompte(jeu)) c.optString("pseudo") else "(non connecté)"
        return "┌ Terminagotchi ┐\n" +
            "1  continuer    $qui\n" +
            "2  nouvelle partie\n" +
            "3  charger\n" +
            "4  compte       $compte\n" +
            "(tape un chiffre ou le mot)"
    }

    /** Une ligne tapée pendant que le menu est ouvert. null : ce n'est pas pour le menu (il se ferme). */
    fun repondre(ligne: String): String? {
        val l = ligne.trim().lowercase()
        when (etat) {
            "menu" -> return when (l) {
                "1", "continuer", "c", "" -> { etat = null; continuer() }
                "2", "nouvelle", "nouvelle partie", "n" -> nouvelle()
                "3", "charger" -> charger()
                "4", "compte" -> { etat = null; texteCompte() }
                else -> { etat = null; null }
            }
            "nouvelle" -> {
                if (l in setOf("oui", "o", "yes", "y")) return creer()
                return "D'accord, on ne touche à rien.\n" + ouvrir()
            }
            "charger" -> {
                if (l.isEmpty() || l == "retour") return ouvrir()
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
            else -> "partie nouvelle · partie charger · partie charger 2 · parties (le menu)"
        }
    }

    private fun continuer(): String =
        if (jeu.existe) "▶ On continue avec ${jeu.nom} !" else "🥚 Comment s'appelle ta créature ?"

    // ---------------------------------------------------------------- nouvelle partie
    private fun nouvelle(): String {
        if (!jeu.existe) { etat = null; return "🥚 Un œuf tout neuf attend déjà son nom : comment s'appelle ta créature ?" }
        if (Parties.pleine(act)) {
            etat = "menu"
            return "Toutes les chambres de la maison sont occupées (${Parties.MAX} créatures). Continue avec l'une d'elles : charger."
        }
        etat = "nouvelle"
        return "${jeu.nom} va dormir dans sa chambre : rien n'est effacé, tu la retrouveras avec « charger ».\n" +
            "Un nouvel œuf ?  oui / non"
    }

    private fun creer(): String {
        etat = null
        jeu.sauver()
        if (Parties.nouvelle(act) == null) return "⚠ Je n'ai pas pu ranger la partie actuelle : rien n'a changé."
        jeu.recharger()
        apresChangement()
        return "🥚 Un œuf tout neuf est apparu !\nComment s'appelle ta nouvelle créature ?"
    }

    // ---------------------------------------------------------------- charger
    private fun lister(avecCompte: Boolean): String {
        choix.clear()
        val sb = StringBuilder("┌ parties ┐")
        for (r in Parties.liste(act)) {
            choix.add(r.id to null)
            sb.append("\n${choix.size}  ${r.nom.ifEmpty { "(œuf sans nom)" }} · ${r.espece} niv. ${r.niveau} · ${format.format(Date(r.date))}")
            if (r.active) sb.append("  ← en cours")
        }
        if (avecCompte && Recensement.aUnCompte(jeu)) {
            sb.append("\n☁ ton compte : je regarde…")
            listerCompte()
        }
        return sb.toString()
    }

    private fun charger(): String {
        etat = "charger"
        return lister(true) + "\nnuméro ? (Entrée = retour)"
    }

    /** Les parties du compte en ligne qui ne sont pas sur ce téléphone : elles s'ajoutent aux numéros. */
    private fun listerCompte() {
        val c = Recensement.compte(jeu)
        val cle = c.optString("cle")
        val connu = c.optString("serveur")
        Thread {
            val r = try {
                val url = Recensement.serveur(connu)
                if (url.isEmpty()) JSONObject().put("erreur", "site injoignable")
                else Recensement.requete("$url/api/parties", "GET", null, cle)
            } catch (e: Exception) {
                JSONObject().put("erreur", "pas de connexion")
            }
            act.runOnUiThread {
                if (etat != "charger") return@runOnUiThread
                val a = r.optJSONArray("parties")
                if (a == null) { plusTard("☁ ton compte : ${r.optString("erreur", "le site doit être mis à jour")}"); return@runOnUiThread }
                val ici = choix.map { it.first }.toSet()
                val sb = StringBuilder("☁ sur ton compte :")
                var n = 0
                for (i in 0 until a.length()) {
                    val p = a.getJSONObject(i)
                    val id = p.optString("partie")
                    if (id in ici) continue
                    val niv = p.optInt("niveau", 1)
                    choix.add(id to p.optString("nom"))
                    n++
                    sb.append("\n${choix.size}  ${p.optString("nom")} · ${espece(Regles.stade(niv), if (p.isNull("forme")) null else p.optString("forme"))} niv. $niv")
                }
                plusTard(if (n == 0) "☁ ton compte : rien de plus (tout est déjà ici)" else sb.toString())
            }
        }.start()
    }

    private fun choisir(n: Int): String {
        val (id, duCompte) = choix.getOrNull(n - 1) ?: return "Il n'y a pas de numéro $n. Tape un numéro de la liste (Entrée = retour)."
        etat = null
        if (id == jeu.partie) return continuer()
        jeu.sauver()
        val ok = if (duCompte != null) Parties.depuisCompte(act, id, duCompte) else Parties.charger(act, id)
        if (!ok) return if (Parties.pleine(act)) "Toutes les chambres sont occupées (${Parties.MAX} créatures)."
            else "⚠ Je n'ai pas pu ouvrir cette chambre : rien n'a changé."
        jeu.recharger()
        apresChangement()
        if (Recensement.aUnCompte(jeu)) synchroniser()
        return if (duCompte != null) "☁ $duCompte arrive de ton compte… synchronisation !"
            else "📂 Te revoilà avec ${jeu.nom} ! ${espece(jeu.stade, jeu.forme)} niv. ${jeu.niveau}"
    }
}
