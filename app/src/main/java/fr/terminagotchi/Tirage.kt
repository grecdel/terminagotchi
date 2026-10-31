package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Anti-triche : les apparitions tirées d'une « graine » signée par le serveur du recensement.
 * Portage exact de pc/tg/tirage.py (la spécification complète y est) ; vecteurs communs :
 * donnees/anti_triche/vecteurs.json. Tout est en entiers ; le générateur est un splitmix64
 * sur des Long (les débordements font le modulo 2^64, les décalages sont non signés).
 *
 * Avec une graine du jour en cache : tirage vérifiable (l'individu garde « graine » et « n »).
 * Sinon (pas de compte, longtemps hors ligne…) : tirage au hasard comme avant, « non vérifié » sur le site.
 */
object Tirage {
    const val MAX_APPARITIONS = 200
    /** La famille attirée (sa commande « attiree_par » vient d'être tapée) pèse 4 fois plus lourd au tirage 1. */
    const val ATTIRANCE = 4L
    private val POIDS_STADES = listOf(35L, 35L, 20L, 10L)
    /** Le glitch (tirage 13, À PART : compteur + 2^20) : 1 chance sur 4096 ; le gardien d'une boîte maîtrisée de la
     *  Citadelle, 1 chance sur 8 (comme pc/tg/tirage.py). */
    const val CHANCE_GLITCH = 4096
    const val CHANCE_GLITCH_GARDIEN = 8
    const val COMPTEUR_GLITCH = 1L shl 20

    class Hasard(valeur: String, compteur: Long) {
        private var etat: Long = java.lang.Long.parseUnsignedLong(valeur.substring(0, 16), 16) xor
            ((compteur + 1) * -0x2e4ab5cd2e6d12fdL)          // 0xD1B54A32D192ED03

        fun suivant(): Long {
            etat += -0x61c8864680b583ebL                       // 0x9E3779B97F4A7C15
            var z = etat
            z = (z xor (z ushr 30)) * -0x40a7b892e31b1a47L     // 0xBF58476D1CE4E5B9
            z = (z xor (z ushr 27)) * -0x6b2fb644ecceee15L     // 0x94D049BB133111EB
            return z xor (z ushr 31)
        }

        fun entier(n: Int): Int = java.lang.Long.remainderUnsigned(suivant(), n.toLong()).toInt()

        fun pondere(poids: List<Long>): Int {
            val r = entier(poids.sum().toInt())
            var cumul = 0L
            for ((i, p) in poids.withIndex()) {
                cumul += p
                if (r < cumul) return i
            }
            return poids.size - 1
        }
    }

    /** Note en dixièmes (0…1000), q en millièmes. */
    fun noteEntiere(e: Bestiaire.Espece, vid: String, q: Int, shiny: Boolean): Int {
        val p = Bestiaire.poidsNote
        fun poids(k: String, d: Long) = Math.round(p[k] ?: d.toDouble())
        val score = Math.round(Bestiaire.variante(e, vid).score * 1000)
        val n = 140 * poids("stats", 60) * q + 140 * poids("variante", 25) * score +
            10000 * poids("puissance", 15) * (e.puissance - 1) + 140000 * poids("bonus_shiny", 10) * (if (shiny) 1 else 0)
        return minOf(1000L, (n + 7000) / 14000).toInt()
    }

    fun rareteEntiere(e: Bestiaire.Espece, note10: Int): String {
        Bestiaire.speciales[e.id]?.let { return it }
        var nom = "commune"
        for ((seuil, palier) in Bestiaire.paliers) if (note10 >= Math.round(seuil * 10)) nom = palier
        return nom
    }

    class Resultat(val espece: Bestiaire.Espece, val champs: JSONObject)

    /** Poids de chaque espèce publique au tirage 1 (comme tirage.poids_especes en Python). */
    fun poidsEspeces(pub: List<Bestiaire.Espece>, attire: String? = null): List<Long> =
        pub.map { Math.round(Bestiaire.poidsFrequence[it.frequence] ?: 1.0) * (if (attire != null && it.famille == attire) ATTIRANCE else 1L) }

    /** Le tirage complet d'une apparition (mêmes champs, dans le même ordre, que le Python).
     *  attire : la famille attirée (ou null) ; elle ne change que le choix de l'espèce. */
    fun tirer(valeur: String, compteur: Long, abyssorPermis: Boolean = false, attire: String? = null): Resultat {
        val h = Hasard(valeur, compteur)
        val pub = Bestiaire.publiques()
        var e = pub[h.pondere(poidsEspeces(pub, attire))]
        var v = e.variantes[h.pondere(e.variantes.map { Math.round(it.chance * 10) })].id
        val shiny = h.entier(Bestiaire.chanceShiny) == 0
        if (h.entier(15) == 0 && abyssorPermis) {
            Bestiaire.espece("Abyssor")?.let { e = it; v = "classique" }
        }
        val q = h.entier(1001)
        val iv = LinkedHashMap<String, Int>()
        for (k in e.stats.keys) {
            val bruit = h.entier(161) + h.entier(161) + h.entier(161) - 240
            val x = 31 * (q + bruit)
            iv[k] = if (x <= 0) 0 else minOf(31, (x + 500) / 1000)
        }
        val marque = Bestiaire.marques[h.entier(Bestiaire.marques.size)]
        val humeur = Bestiaire.humeurs[h.entier(Bestiaire.humeurs.size)]
        val taille10 = (Math.round(e.tailleCm * 10) * (800 + h.entier(451)) + 500) / 1000
        val stade = Bestiaire.STADES[h.pondere(POIDS_STADES)]
        val teinte = 150 + h.entier(701)
        val note10 = noteEntiere(e, v, q, shiny)
        val nb = iv.size
        val st = JSONObject()
        for ((k, b) in e.stats) st.put(k, b + (iv[k] ?: 0) / 2)
        val champs = JSONObject()
            .put("espece", e.nom).put("variante", v).put("shiny", shiny)
            .put("marque", marque).put("humeur", humeur)
            .put("taille", taille10 / 10.0).put("qualite", q / 1000.0)
            .put("potentiel", (200 * iv.values.sum() + 31 * nb) / (62 * nb))
            .put("stats", st)
            .put("note", note10 / 10.0).put("rarete", rareteEntiere(e, note10))
            .put("stade", stade)
        if (shiny) champs.put("teinte", teinte / 1000.0)
        return Resultat(e, champs)
    }

    /** 13. L'individu (graine, compteur) est-il glitch ? gardien : c'est le gardien d'une boîte maîtrisée. */
    fun glitch(valeur: String, compteur: Long, gardien: Boolean = false): Boolean {
        val r = Hasard(valeur, COMPTEUR_GLITCH + compteur).entier(CHANCE_GLITCH)
        return if (gardien) r < CHANCE_GLITCH / CHANCE_GLITCH_GARDIEN else r == 0
    }

    /** Sans graine (tirage local, non vérifié) : mêmes chances. */
    fun glitchAuHasard(gardien: Boolean = false): Boolean {
        val r = kotlin.random.Random.nextInt(CHANCE_GLITCH)
        return if (gardien) r < CHANCE_GLITCH / CHANCE_GLITCH_GARDIEN else r == 0
    }

    /** La valeur de la graine d'un individu tiré d'une graine encore en cache, ou null. */
    fun valeurDe(jeu: Jeu, ind: JSONObject): String? {
        val gid = ind.optString("graine").ifEmpty { return null }
        if (!ind.has("n")) return null
        val v = Recensement.compte(jeu).optJSONObject("graines")?.optString(gid) ?: return null
        return v.takeIf { it.length >= 16 }
    }

    // ---------------------------------------------------------------- les graines en cache (module « compte »)
    private fun jour(decalageJours: Int = 0): String {
        val f = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT)
        return f.format(java.util.Date(System.currentTimeMillis() + decalageJours * 86_400_000L))
    }

    /** Garde les graines reçues du serveur (et oublie celles de plus de 2 jours). */
    fun rangerGraines(jeu: Jeu, graines: JSONArray?) {
        val c = Recensement.compte(jeu)
        val cache = c.optJSONObject("graines") ?: JSONObject().also { c.put("graines", it) }
        if (graines != null) for (i in 0 until graines.length()) {
            val g = graines.optJSONObject(i) ?: continue
            val id = g.optString("id"); val valeur = g.optString("valeur")
            if (id.isNotEmpty() && valeur.length >= 16) cache.put(id, valeur)
        }
        val limite = jour(-2)
        for (k in cache.keys().asSequence().toList()) if (k.substringBefore('.') < limite) {
            cache.remove(k)
            c.optJSONObject("apparitions")?.remove(k)
        }
    }

    /** Une apparition tirée de la graine du jour (vérifiable), ou null s'il n'y en a pas.
     *  attire : la famille attirée, gardée dans l'individu (« attire ») pour que le serveur refasse le tirage. */
    fun apparition(jeu: Jeu, abyssorPermis: Boolean, attire: String? = null): Pair<Bestiaire.Espece, JSONObject>? {
        val c = Recensement.compte(jeu)
        val cache = c.optJSONObject("graines") ?: return null
        val aujourdhui = jour()
        val id = cache.keys().asSequence().firstOrNull { it.substringBefore('.') == aujourdhui } ?: return null
        val valeur = cache.optString(id)
        if (valeur.length < 16) return null
        val compteurs = c.optJSONObject("apparitions") ?: JSONObject().also { c.put("apparitions", it) }
        val n = compteurs.optLong(id)
        if (n >= MAX_APPARITIONS) return null
        compteurs.put(id, n + 1)
        val t = tirer(valeur, n, abyssorPermis, attire)
        val vid = t.champs.getString("variante")
        val ind = Bestiaire.individu(t.espece, t.champs.getBoolean("shiny"), Bestiaire.variante(t.espece, vid).zone, vid)
        for (k in t.champs.keys().asSequence().toList()) ind.put(k, t.champs.get(k))
        ind.put("graine", id).put("n", n)
        if (attire != null) ind.put("attire", attire)
        return t.espece to ind
    }
}
