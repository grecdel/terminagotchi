package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Les mondes font apparaître des créatures (docs/programme.md § 7.6), portage de pc/tg/recompenses.py.
 * Un exploit donne des faveurs : le jeu essaie quelques compteurs de la graine et garde la première créature
 * qui convient (type du monde en variante rare, ou légendaire), sinon la première. Le tirage ne change pas :
 * chaque créature reste vérifiable par le serveur. Vecteurs communs : donnees/recompenses/vecteurs.json.
 */
object Recompenses {
    private val REPETABLES = setOf("entrainement.serie_parfaite")

    fun conf(): JSONObject = Programme.donnees().optJSONObject("recompenses") ?: JSONObject()
    fun mondes(): JSONArray = Programme.donnees().optJSONArray("mondes") ?: JSONArray()

    /** (monde, exploit) d'un identifiant d'exploit, ou null. */
    fun exploitDef(id: String?): Pair<JSONObject, JSONObject>? {
        if (id == null) return null
        val ms = mondes()
        for (i in 0 until ms.length()) {
            val m = ms.getJSONObject(i)
            val ex = m.optJSONArray("exploits") ?: continue
            for (k in 0 until ex.length()) if (ex.getJSONObject(k).optString("id") == id) return m to ex.getJSONObject(k)
        }
        return null
    }

    fun etat(jeu: Jeu): JSONObject {
        val r = jeu.module("recompenses")
        if (r.optJSONObject("exploits") == null) r.put("exploits", JSONObject())
        if (r.optJSONArray("faveurs") == null) r.put("faveurs", JSONArray())
        if (!r.has("serie")) r.put("serie", 0)
        return r
    }

    private fun types(m: JSONObject): List<String> = m.optJSONArray("types")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()

    fun exploit(jeu: Jeu, id: String, maintenant: Long = System.currentTimeMillis() / 1000): String? {
        val (_, x) = exploitDef(id) ?: return null
        val r = etat(jeu)
        val faits = r.getJSONObject("exploits")
        if (faits.has(id) && id !in REPETABLES) return null
        faits.put(id, maintenant)
        val n = conf().optInt("bonus_" + x.getString("recompense"), 1)
        r.getJSONArray("faveurs").put(JSONObject().put("exploit", id).put("reste", n))
        return t("recomp.exploit", "exploit" to t(x.getString("nom")), "n" to n)
    }

    fun faveur(jeu: Jeu): JSONObject? {
        val fs = etat(jeu).getJSONArray("faveurs")
        for (i in 0 until fs.length()) {
            val f = fs.getJSONObject(i)
            if (f.optInt("reste") > 0 && exploitDef(f.optString("exploit")) != null) return f
        }
        return null
    }

    private fun rarete(c: JSONObject): String = c.optString("rarete").ifEmpty { Bestiaire.rareteDe(c) }

    /** L'indice du candidat gardé parmi (espèce, champs), dans l'ordre des compteurs. */
    fun choisir(cands: List<Pair<Bestiaire.Espece, JSONObject>>, genre: String, types: List<String>): Int {
        if (genre == "legendaire") return cands.indexOfFirst { rarete(it.second) == "légendaire" }.coerceAtLeast(0)
        val rare = cands.indexOfFirst { (e, c) -> c.optString("variante", "classique") != "classique" &&
            Guide.typeDe(e, c.optString("variante", "classique")) in types }
        if (rare >= 0) return rare
        return cands.indexOfFirst { (e, c) -> Guide.typeDe(e, c.optString("variante", "classique")) in types }.coerceAtLeast(0)
    }

    fun reussi(genre: String, types: List<String>, e: Bestiaire.Espece, c: JSONObject): Boolean =
        if (genre == "legendaire") rarete(c) == "légendaire" else Guide.typeDe(e, c.optString("variante", "classique")) in types

    /** La variante est réservée par un monde dont aucun exploit n'est encore réussi : pour toutes les espèces
     *  (« orage ») ou pour une seule (« plumange:orage »). */
    fun reservee(jeu: Jeu, vid: String, eid: String = ""): Boolean {
        val faits = etat(jeu).getJSONObject("exploits")
        val ms = mondes()
        for (i in 0 until ms.length()) {
            val m = ms.getJSONObject(i)
            val res = m.optJSONArray("variantes_reservees") ?: continue
            if ((0 until res.length()).none { res.getString(it) == vid || res.getString(it) == "$eid:$vid" }) continue
            val ex = m.optJSONArray("exploits") ?: JSONArray()
            if ((0 until ex.length()).none { faits.has(ex.getJSONObject(it).optString("id")) }) return true
        }
        return false
    }

    /** Spécification pure (vecteurs communs) : le compteur gardé et son tirage. */
    fun favoriser(valeur: String, n0: Long, genre: String, types: List<String>, abyssorPermis: Boolean = false,
                  attire: String? = null): Pair<Long, JSONObject> {
        val essais = conf().optInt("essais_$genre", 1)
        val cands = (0 until essais).map { k -> Tirage.tirer(valeur, n0 + k, abyssorPermis, attire).let { it.espece to it.champs } }
        val i = choisir(cands, genre, types)
        return (n0 + i) to cands[i].second
    }

    /** Après le tirage normal : la faveur d'un exploit et les variantes réservées. Renvoie (apparition, texte ou null). */
    fun apparition(jeu: Jeu, premiere: Pair<Bestiaire.Espece, JSONObject>, tirerUn: () -> Pair<Bestiaire.Espece, JSONObject>?):
        Pair<Pair<Bestiaire.Espece, JSONObject>, String?> {
        val cands = mutableListOf(premiere)
        var texte: String? = null
        var r = premiere
        val f = faveur(jeu)
        if (f != null) {
            val (m, x) = exploitDef(f.getString("exploit"))!!
            val genre = x.getString("recompense")
            val ty = types(m)
            val essais = conf().optInt("essais_$genre", 1)
            while (cands.size < essais) cands.add(tirerUn() ?: break)
            val i = choisir(cands, genre, ty)
            f.put("reste", f.optInt("reste") - 1)
            val fs = etat(jeu).getJSONArray("faveurs")
            val garder = JSONArray()
            for (k in 0 until fs.length()) if (fs.getJSONObject(k).optInt("reste") > 0) garder.put(fs.getJSONObject(k))
            etat(jeu).put("faveurs", garder)
            if (reussi(genre, ty, cands[i].first, cands[i].second)) texte = t("recomp.rencontre", "exploit" to t(x.getString("nom")))
            r = cands[i]
        }
        repeat(4) {
            if (!reservee(jeu, r.second.optString("variante", "classique"), r.first.id)) return r to texte
            r = tirerUn() ?: return r to texte
        }
        return r to texte
    }

    /** Salle d'entraînement : 5 médailles d'or ou de diamant de suite = une série parfaite (exploit). */
    fun serie(jeu: Jeu, medaille: String): String? {
        val r = etat(jeu)
        r.put("serie", if (medaille == "or" || medaille == "diamant") r.optInt("serie") + 1 else 0)
        if (r.optInt("serie") >= conf().optInt("serie_parfaite", 5)) {
            r.put("serie", 0)
            return exploit(jeu, "entrainement.serie_parfaite")
        }
        return null
    }
}
