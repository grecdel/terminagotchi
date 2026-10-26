package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import kotlin.random.Random

/**
 * Mini-combat (portage de pc/tg/combat.py) : quand un monstre sauvage apparaît, une bestiole de ta
 * troupe l'affronte d'abord. Court (5 tours au plus), au tour par tour, et chaque coup est une VRAIE
 * commande tapée dans le terminal :
 *  - la commande de la famille de ta bestiole (« attiree_par » : chmod pour les Démons, ls pour les
 *    Sylvestres…) → attaque spéciale, 2 cœurs ;
 *  - ls → observer : tu vois ses stats, tu esquives son coup, et ton coup suivant touche à coup sûr (+1 cœur) ;
 *  - n'importe quelle autre commande → attaque, 1 cœur.
 * Gagner : le monstre a moins peur (méfiance −40), une épreuve de dressage en moins, l'exemple s'affiche tout
 * de suite. Perdre : pas de mort, la bestiole joue « ko » puis se repose 5 minutes (💤 dans la troupe).
 * Le dressage commence après. Le combat ne touche à aucun champ tiré de la graine (anti-triche).
 *
 * Sur le téléphone, quelques commandes ne marchent pas ou ne s'arrêtent pas seules (ping sans -c, git…) :
 * pendant un combat elles comptent comme un coup sans être lancées (SANS_SHELL, voir TerminalActivity).
 */
object Combat {
    const val TOURS_MAX = 5
    /** secondes de repos après un KO (le champ « repos » est en secondes, comme sur PC et sur le serveur) */
    const val REPOS = 300
    const val BAISSE_PEUR = 40
    val COEURS_MONSTRE = mapOf("commune" to 3, "peu commune" to 3, "rare" to 4, "épique" to 4, "légendaire" to 5, "mythique" to 5)
    val BONUS_STADE = mapOf("bebe" to 0, "enfant" to 0, "ado" to 1, "adulte" to 1, "ancien" to 2)
    val OBSERVER = setOf("ls", "dir", "gci", "get-childitem")
    /** commandes absentes du téléphone ou qui ne s'arrêtent pas seules : pendant un combat, le coup est joué sans les lancer */
    val SANS_SHELL = setOf("ping", "git", "top", "ssh", "python3", "nano", "apt", "sudo")

    /** le dé (remplaçable par un test) */
    var de: () -> Double = { Random.nextDouble() }

    /** L'animation qu'une bestiole de la troupe doit jouer (attaque, victoire, ko) : l'écran la joue puis l'efface. */
    @Volatile var animTroupe: Pair<JSONObject, String>? = null

    private fun maintenant() = System.currentTimeMillis() / 1000.0
    private fun borne(x: Double, a: Double, b: Double) = maxOf(a, minOf(b, x))

    fun repose(ind: JSONObject?) = ind != null && ind.optDouble("repos", 0.0) > maintenant()

    fun minutesDeRepos(ind: JSONObject) = maxOf(1, Math.round((ind.optDouble("repos", 0.0) - maintenant()) / 60).toInt())

    private fun dressage(jeu: Jeu): JSONObject? = jeu.module("dressage").optJSONObject("en_cours")

    /** La bestiole de la troupe qui combat : l'active si elle est reposée, sinon la plus récente reposée. */
    fun combattant(jeu: Jeu): JSONObject? {
        val act = Equipe.active(jeu)
        if (act != null && !repose(act) && Bestiaire.espece(act.optString("espece")) != null) return act
        val caps = Explo.captures(jeu)
        for (i in caps.length() - 1 downTo 0) {
            val c = caps.getJSONObject(i)
            if (!repose(c) && Bestiaire.espece(c.optString("espece")) != null) return c
        }
        return null
    }

    fun etat(jeu: Jeu): JSONObject? = dressage(jeu)?.optJSONObject("combat")

    /** La bestiole de la troupe qui combat en ce moment. */
    fun ind(jeu: Jeu): JSONObject? {
        val id = etat(jeu)?.optString("id") ?: return null
        val caps = Explo.captures(jeu)
        return (0 until caps.length()).map { caps.getJSONObject(it) }.firstOrNull { it.optString("id") == id }
    }

    fun enCours(jeu: Jeu): Boolean {
        val cb = etat(jeu) ?: return false
        return cb.isNull("fin") || cb.optString("fin").isEmpty()
    }

    /** Au début d'un dressage : le combat, si tu as une bestiole reposée dans ta troupe. */
    fun preparer(jeu: Jeu): Boolean {
        val d = dressage(jeu) ?: return false
        if (Explo.captures(jeu).length() == 0) return false
        val ind = combattant(jeu)
        if (ind == null) {
            jeu.dire(t("dress.combat.tous_repos"), 8)
            return false
        }
        val e = Bestiaire.espece(ind.optString("espece"))!!
        val moi = 3 + (BONUS_STADE[Equipe.stade(ind)] ?: 0)
        val lui = COEURS_MONSTRE[d.optString("rarete")] ?: 3
        val cb = JSONObject().put("id", ind.optString("id")).put("espece", e.nom).put("special", e.attireePar)
            .put("capacite", e.capacite).put("moi", JSONArray().put(moi).put(moi)).put("lui", JSONArray().put(lui).put(lui))
            .put("tour", 0).put("observe", false).put("vu", false).put("fin", "").put("journal", JSONArray())
        d.put("combat", cb)
        jeu.dire(t("dress.combat.debut", "nom" to e.nom, "monstre" to d.getString("espece"), "cmd" to e.attireePar), 12)
        return true
    }

    private fun anim(ind: JSONObject, nom: String) {
        animTroupe = JSONObject(ind.toString()) to nom
    }

    private fun stats(o: JSONObject?, e: Bestiaire.Espece?): Map<String, Int> =
        o?.let { s -> s.keys().asSequence().associateWith { s.optInt(it) } } ?: e?.stats ?: emptyMap()

    /** Un coup : la commande tapée. Renvoie le résultat du combat s'il vient de finir (gagne, perdu, nul), sinon null. */
    fun coup(jeu: Jeu, ligne: String): String? {
        val d = dressage(jeu) ?: return null
        val cb = d.getJSONObject("combat")
        val ind = ind(jeu) ?: return finir(jeu, "nul")          // la bestiole n'est plus là : pas de combat
        val cmd = Regles.premierMot(ligne)
        val stT = stats(ind.optJSONObject("stats"), Bestiaire.espece(ind.optString("espece")))
        val stM = stats(d.optJSONObject("ind")?.optJSONObject("stats"), Bestiaire.espece(d.getString("espece")))
        val nom = cb.getString("espece")
        val monstre = d.getString("espece")
        val special = cb.optString("special")
        val moi = cb.getJSONArray("moi")
        val lui = cb.getJSONArray("lui")
        val journal = mutableListOf<String>()
        val observe = cmd in OBSERVER
        val estSpecial = special.isNotEmpty() && cmd == special
        if (observe && !estSpecial) {
            cb.put("observe", true).put("vu", true)
            journal.add(t("dress.combat.observe", "nom" to nom, "monstre" to monstre,
                "atk" to (stM["ATK"] ?: "?"), "def" to (stM["DEF"] ?: "?")))
        } else {
            val sur = cb.optBoolean("observe")
            cb.put("observe", observe)                         // ls chez les Sylvestres : attaque ET observe
            val p = borne(0.7 + ((stT["VIT"] ?: 30) - (stM["VIT"] ?: 30)) / 60.0, 0.45, 0.9)
            if (sur || de() < p) {
                val n = (if (estSpecial) 2 else 1) + (if (sur) 1 else 0)
                lui.put(0, maxOf(0, lui.getInt(0) - n))
                journal.add(if (estSpecial) t("dress.combat.special", "nom" to nom,
                    "capacite" to cb.optString("capacite").ifEmpty { cmd }, "n" to n)
                    else t("dress.combat.attaque", "nom" to nom, "n" to n))
                if (estSpecial) anim(ind, "attaque")
            } else journal.add(t("dress.combat.rate", "nom" to nom))
        }
        if (lui.getInt(0) > 0) {                               // le monstre répond
            if (observe) journal.add(t("dress.combat.esquive", "nom" to nom, "monstre" to monstre))
            else if (de() < borne(0.45 + ((stM["ATK"] ?: 30) - (stT["DEF"] ?: 30)) / 60.0, 0.2, 0.75)) {
                moi.put(0, maxOf(0, moi.getInt(0) - 1))
                journal.add(t("dress.combat.touche", "nom" to nom, "monstre" to monstre))
            } else journal.add(t("dress.combat.manque", "monstre" to monstre))
        }
        cb.put("tour", cb.optInt("tour") + 1)
        val j = cb.getJSONArray("journal")
        for (x in journal) j.put(x)
        while (j.length() > 4) j.remove(0)
        return when {
            lui.getInt(0) <= 0 -> finir(jeu, "gagne")
            moi.getInt(0) <= 0 -> finir(jeu, "perdu")
            cb.optInt("tour") >= TOURS_MAX -> finir(jeu, "nul")
            else -> null
        }
    }

    /** L'épreuve à retirer après une victoire : la plus difficile qui reste (il en reste toujours au moins une de sa famille). */
    private fun plusDure(d: JSONObject): String? {
        val taches = d.getJSONArray("taches").let { a -> (0 until a.length()).map { a.getString(it) } }
        val faites = d.getJSONArray("faites").let { a -> (0 until a.length()).map { a.getString(it) }.toSet() }
        val reste = taches.filter { it !in faites && !it.startsWith("Rencontre:") }
        if (reste.size < 2) return null
        return reste.maxWithOrNull(compareBy<String>({ Dressage.epreuve(it)?.niveau ?: 0 }, { taches.indexOf(it) }))
    }

    fun finir(jeu: Jeu, resultat: String): String {
        val d = dressage(jeu)!!
        val cb = d.getJSONObject("combat")
        cb.put("fin", resultat)
        val ind = ind(jeu)
        val nom = cb.getString("espece")
        when (resultat) {
            "gagne" -> {
                d.put("mefiance", maxOf(0, d.optInt("mefiance", 100) - BAISSE_PEUR))
                plusDure(d)?.let { f ->
                    val a = d.getJSONArray("taches")
                    for (i in 0 until a.length()) if (a.getString(i) == f) { a.remove(i); break }
                }
                d.put("exemple_tout_de_suite", true)
                if (ind != null) {
                    Equipe.gagner(jeu, ind, 20)
                    anim(ind, "victoire")
                }
                jeu.log(t("dress.combat.gagne.log", "nom" to nom, "monstre" to d.getString("espece")))
                jeu.dire(t("dress.combat.gagne", "monstre" to d.getString("espece")), 12)
            }
            "perdu" -> {
                if (ind != null) {
                    ind.put("repos", maintenant() + REPOS)
                    anim(ind, "ko")
                }
                jeu.log(t("dress.combat.perdu.log", "nom" to nom))
                jeu.dire(t("dress.combat.perdu", "nom" to nom), 12)
            }
            else -> jeu.dire(t("dress.combat.nul"), 10)
        }
        Envies.plaisir(jeu, "jeu", "combat")                  // gagné ou perdu : on a bien joué
        // le dressage commence maintenant : chrono à zéro, les commandes du combat ne comptent pas
        d.put("debut", System.currentTimeMillis())
        d.put("lignes", JSONArray())
        return resultat
    }
}
