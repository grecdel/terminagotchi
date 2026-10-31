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

    /** {boîte: identifiant de l'espèce gardienne} (les 8 boîtes de la Citadelle, codées ou annoncées). */
    fun gardiens(): Map<String, String> {
        val out = LinkedHashMap<String, String>()
        val ms = mondes()
        for (i in 0 until ms.length()) {
            val g = ms.getJSONObject(i).optJSONObject("gardiens") ?: continue
            for (k in g.keys()) out[k] = g.getString(k)
        }
        return out
    }

    /** Les boîtes maîtrisées (leur exploit « gardien » est réussi). */
    fun boitesMaitrisees(jeu: Jeu): List<String> {
        val faits = etat(jeu).getJSONObject("exploits")
        val out = mutableListOf<String>()
        val ms = mondes()
        for (i in 0 until ms.length()) {
            val ex = ms.getJSONObject(i).optJSONArray("exploits") ?: continue
            for (k in 0 until ex.length()) {
                val x = ex.getJSONObject(k)
                if (x.optString("recompense") == "gardien" && x.optString("boite").isNotEmpty() && faits.has(x.optString("id"))) out.add(x.getString("boite"))
            }
        }
        return out
    }

    /** La boîte maîtrisée dont cette espèce est le gardien, ou null. */
    fun gardienDe(jeu: Jeu, e: Bestiaire.Espece): String? {
        val g = gardiens()
        return boitesMaitrisees(jeu).firstOrNull { g[it] == e.id }
    }

    /** Après le choix de l'apparition : le gardien d'une boîte maîtrisée le déclare (« gardien »), puis le glitch est
     *  tiré à part (Tirage.glitch, de la même graine ; au hasard sans graine). Renvoie le texte à dire, ou null. */
    fun marquerGlitch(jeu: Jeu, e: Bestiaire.Espece, ind: JSONObject): String? {
        val b = gardienDe(jeu, e)
        if (b != null) ind.put("gardien", b) else ind.remove("gardien")
        val v = Tirage.valeurDe(jeu, ind)
        val g = if (v != null) Tirage.glitch(v, ind.optLong("n"), b != null) else Tirage.glitchAuHasard(b != null)
        if (g) ind.put("glitch", true) else ind.remove("glitch")
        if (!g) return null
        return t(if (b != null) "recomp.glitch_gardien" else "recomp.glitch", "espece" to ind.optString("espece"))
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
        if (x.optString("recompense") == "gardien") {
            val b = x.optString("boite")
            val nom = Bestiaire.espece(gardiens()[b] ?: "")?.nom ?: (gardiens()[b] ?: "")
            return t("recomp.gardien", "boite" to t("cit.boite.$b"), "espece" to nom)
        }
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
    fun choisir(cands: List<Pair<Bestiaire.Espece, JSONObject>>, genre: String, types: List<String>, cible: String? = null): Int {
        if (genre == "gardien") return cands.indexOfFirst { it.first.id == cible }.coerceAtLeast(0)
        if (genre == "legendaire") return cands.indexOfFirst { rarete(it.second) == "légendaire" }.coerceAtLeast(0)
        val rare = cands.indexOfFirst { (e, c) -> c.optString("variante", "classique") != "classique" &&
            Guide.typeDe(e, c.optString("variante", "classique")) in types }
        if (rare >= 0) return rare
        return cands.indexOfFirst { (e, c) -> Guide.typeDe(e, c.optString("variante", "classique")) in types }.coerceAtLeast(0)
    }

    fun reussi(genre: String, types: List<String>, e: Bestiaire.Espece, c: JSONObject, cible: String? = null): Boolean =
        if (genre == "gardien") e.id == cible else if (genre == "legendaire") rarete(c) == "légendaire" else Guide.typeDe(e, c.optString("variante", "classique")) in types

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
                  attire: String? = null, cible: String? = null): Pair<Long, JSONObject> {
        val essais = conf().optInt("essais_$genre", 1)
        val cands = (0 until essais).map { k -> Tirage.tirer(valeur, n0 + k, abyssorPermis, attire).let { it.espece to it.champs } }
        val i = choisir(cands, genre, types, cible)
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
            val cible = if (genre == "gardien") m.optJSONObject("gardiens")?.optString(x.optString("boite"))?.ifEmpty { null } else null
            val essais = conf().optInt("essais_$genre", 1)
            while (cands.size < essais) cands.add(tirerUn() ?: break)
            val i = choisir(cands, genre, ty, cible)
            f.put("reste", f.optInt("reste") - 1)
            val fs = etat(jeu).getJSONArray("faveurs")
            val garder = JSONArray()
            for (k in 0 until fs.length()) if (fs.getJSONObject(k).optInt("reste") > 0) garder.put(fs.getJSONObject(k))
            etat(jeu).put("faveurs", garder)
            if (reussi(genre, ty, cands[i].first, cands[i].second, cible)) texte = t("recomp.rencontre", "exploit" to t(x.getString("nom")))
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
