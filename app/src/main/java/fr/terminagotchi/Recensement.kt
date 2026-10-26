package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Recensement : la même créature sur le téléphone et le PC.
 * Chaque appareil envoie ce qu'il a GAGNÉ depuis sa dernière synchro ; le serveur additionne
 * et renvoie la créature commune. Les appels réseau ne se font jamais sur l'écran (fil séparé).
 */
object Recensement {
    private const val INFO = "https://raw.githubusercontent.com/grecdel/terminagotchi-android/site-info/url.txt"
    const val APPAREIL = "android"
    private const val INTERVALLE = 60_000L

    @Volatile
    private var enCours = false
    /** la dernière synchro a apporté du nouveau (XP venue d'un autre appareil, badge) : on l'annonce */
    @Volatile var nouveau = false

    class Preparation(val cle: String, val serveurConnu: String, val charge: JSONObject, val snap: JSONObject)

    fun compte(jeu: Jeu): JSONObject = jeu.module("compte")

    fun aUnCompte(jeu: Jeu) = compte(jeu).optString("cle").isNotEmpty()

    // ---------------------------------------------------------------- réseau (hors de l'écran)
    fun requete(url: String, methode: String = "GET", corps: JSONObject? = null, cle: String? = null): JSONObject {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.requestMethod = methode
            c.connectTimeout = 10_000
            c.readTimeout = 15_000
            c.setRequestProperty("content-type", "application/json")
            c.setRequestProperty("user-agent", "terminagotchi-android")
            if (cle != null) c.setRequestProperty("authorization", "Bearer $cle")
            if (corps != null) {
                c.doOutput = true
                c.outputStream.use { it.write(corps.toString().toByteArray()) }
            }
            val flux = if (c.responseCode >= 400) c.errorStream else c.inputStream
            val texte = flux?.bufferedReader()?.use { it.readText() } ?: ""
            try {
                JSONObject(texte.ifEmpty { "{}" })
            } catch (e: Exception) {
                JSONObject().put("erreur", t("reca.err.illisible", "code" to c.responseCode))
            }
        } catch (e: Exception) {
            JSONObject().put("erreur", t("reca.err.connexion"))
        }
    }

    fun serveur(connu: String): String {
        if (connu.isNotEmpty()) return connu.trimEnd('/')
        return try {
            val c = URL(INFO).openConnection() as HttpURLConnection
            c.connectTimeout = 8000
            c.readTimeout = 8000
            val u = c.inputStream.bufferedReader().use { it.readText() }.trim()
            if (u.startsWith("https://") || u.startsWith("http://")) u.trimEnd('/') else ""
        } catch (e: Exception) {
            ""
        }
    }

    // ---------------------------------------------------------------- préparation et fusion (sur l'écran)
    private fun records(jeu: Jeu): JSONObject =
        jeu.module("defi").optJSONObject("records") ?: JSONObject().also { jeu.module("defi").put("records", it) }

    fun preparer(jeu: Jeu, forcer: Boolean): Preparation? {
        val c = compte(jeu)
        val cle = c.optString("cle")
        if (cle.isEmpty() || enCours) return null
        val maintenant = System.currentTimeMillis()
        if (!forcer && maintenant - c.optLong("dernier") < INTERVALLE) return null
        c.put("dernier", maintenant)
        val base = c.optJSONObject("base") ?: JSONObject()
        val baseStats = base.optJSONObject("stats") ?: JSONObject()
        val snap = JSONObject().put("xp", jeu.xp).put("total", jeu.total).put("colles", jeu.colles)
            .put("stats", JSONObject(jeu.stats.toMap()))
        val deltas = JSONObject()
            .put("xp", maxOf(0, jeu.xp - base.optInt("xp")))
            .put("total", maxOf(0, jeu.total - base.optInt("total")))
            .put("colles", maxOf(0, jeu.colles - base.optInt("colles")))
            .put("stats", JSONObject(Regles.STATS.associateWith { maxOf(0, (jeu.stats[it] ?: 0) - baseStats.optInt(it)) }))
        val charge = JSONObject()
            .put("appareil", APPAREIL)
            .put("partie", jeu.partie)
            .put("deltas", deltas)
            .put("vus", JSONArray(jeu.vus.toList().takeLast(3000)))
            .put("skills", JSONArray(jeu.skills))
            .put("collection", Explo.collection(jeu))
            .put("records", records(jeu))
            .put("captures", Explo.captures(jeu))
            .put("partage", c.optJSONObject("partage") ?: JSONObject().put("actif", false).put("date", 0))
            .put("valeurs", JSONObject()
                .put("nom", jeu.nom).put("nomDate", c.optLong("nomDate"))
                .put("trait", jeu.trait).put("forme", jeu.forme ?: JSONObject.NULL).put("shiny", jeu.shiny)
                .put("faim", jeu.faim).put("faimDate", c.optLong("repas")))
        // salle d'entraînement : compteurs gagnés ici, exercices à vérifier, records (Entrainement.kt)
        val (ent, snapEnt) = Entrainement.charge(jeu, base.optJSONObject("ent"))
        charge.put("entrainement", ent)
        snap.put("ent", snapEnt)
        enCours = true
        return Preparation(cle, c.optString("serveur"), charge, snap)
    }

    /** Fait l'appel réseau (à lancer hors de l'écran). Renvoie la réponse + l'adresse utilisée. */
    fun envoyer(p: Preparation): Pair<JSONObject, String> {
        val url = serveur(p.serveurConnu)
        if (url.isEmpty()) return JSONObject().put("erreur", t("reca.err.pas_en_ligne")) to ""
        // partie 1 (celle d'avant les parties multiples) : l'adresse d'origine ; les autres ont la leur,
        // qu'un site pas encore mis à jour refuse (au lieu de mélanger deux créatures)
        val partie = p.charge.optString("partie", "1")
        val route = if (partie == "1") "/api/sync" else "/api/sync/$partie"
        return requete("$url$route", "POST", p.charge, p.cle) to url
    }

    /** Recopie la créature commune, en gardant ce qui a été gagné ici PENDANT la synchro. */
    fun appliquer(jeu: Jeu, p: Preparation, r: JSONObject, url: String): String {
        enCours = false
        nouveau = false
        val srv = r.optJSONObject("etat") ?: return t("rec.sync.impossible", "erreur" to r.optString("erreur", t("rec.err.inconnue")))
        val c = compte(jeu)
        if (c.optString("serveur").isEmpty() && url.isNotEmpty()) c.put("serveur", url)
        val snap = p.snap
        val avant = jeu.xp
        jeu.xp = srv.optInt("xp") + (jeu.xp - snap.optInt("xp"))
        jeu.total = srv.optInt("total") + (jeu.total - snap.optInt("total"))
        jeu.colles = srv.optInt("colles") + (jeu.colles - snap.optInt("colles"))
        val srvStats = srv.optJSONObject("stats") ?: JSONObject()
        val snapStats = snap.getJSONObject("stats")
        for (s in Regles.STATS) jeu.stats[s] = srvStats.optInt(s) + ((jeu.stats[s] ?: 0) - snapStats.optInt(s))
        c.put("base", JSONObject().put("xp", srv.optInt("xp")).put("total", srv.optInt("total"))
            .put("colles", srv.optInt("colles")).put("stats", srvStats))
        srv.optJSONObject("entrainement")?.let { se ->      // (un site pas encore à jour n'en renvoie pas)
            val ent = p.charge.optJSONObject("entrainement")
            c.getJSONObject("base").put("ent", Entrainement.appliquer(jeu, se, snap.optJSONObject("ent") ?: JSONObject(),
                ent?.optJSONArray("runs") ?: JSONArray(), r.optJSONObject("entrainement")))
        }
        srv.optJSONArray("vus")?.let { a -> for (i in 0 until a.length()) jeu.vus.add(a.getString(i)) }
        srv.optJSONArray("skills")?.let { a ->
            for (i in 0 until a.length()) if (a.getString(i) !in jeu.skills) jeu.skills.add(a.getString(i))
        }
        val coll = Explo.collection(jeu)
        srv.optJSONObject("collection")?.let { o ->
            for (k in o.keys()) if (o.optInt(k) > coll.optInt(k)) coll.put(k, o.optInt(k))
        }
        val rec = records(jeu)
        srv.optJSONObject("records")?.let { o ->
            for (k in o.keys()) if (!rec.has(k) || o.optDouble(k) < rec.optDouble(k)) rec.put(k, o.optDouble(k))
        }
        val caps = Explo.captures(jeu)
        val connus = (0 until caps.length()).map { caps.getJSONObject(it).optString("id") }.toMutableSet()
        val parId = (0 until caps.length()).associateBy { caps.getJSONObject(it).optString("id") }
        srv.optJSONArray("captures")?.let { a ->
            for (i in 0 until a.length()) {
                val ind = a.getJSONObject(i)
                val ici = parId[ind.optString("id")]?.let { caps.getJSONObject(it) }
                if (ici != null) {                      // anti-triche : le verdict du serveur
                    if (ind.has("verifie")) ici.put("verifie", ind.optBoolean("verifie"))
                } else if (connus.add(ind.optString("id"))) caps.put(ind)
            }
        }
        Tirage.rangerGraines(jeu, r.optJSONArray("graines"))   // graines des prochains jours (jeu hors ligne)
        Bestiaire.migrer(jeu.extra)      // des captures d'avant le nouveau bestiaire ont pu revenir du serveur
        srv.optJSONObject("partage")?.let { pa ->
            if (pa.optLong("date") >= (c.optJSONObject("partage")?.optLong("date") ?: 0L)) c.put("partage", pa)
        }
        if (srv.has("shiny")) jeu.shiny = srv.optBoolean("shiny")
        val nom = srv.optString("nom")
        if (nom.isNotEmpty()) {
            jeu.nom = nom
            c.put("nomDate", srv.optLong("nomDate"))
        }
        srv.optString("trait").takeIf { it.isNotEmpty() }?.let { jeu.trait = it }
        if (!srv.isNull("forme")) srv.optString("forme").takeIf { it in Regles.STATS }?.let { jeu.forme = it }
        if (jeu.stade >= 2 && jeu.forme == null) jeu.forme = jeu.dominant()
        if (srv.optLong("faimDate") > c.optLong("repas")) {
            jeu.faim = srv.optDouble("faim", jeu.faim)
            c.put("repas", srv.optLong("faimDate"))
            jeu.dernierTick = System.currentTimeMillis()
        }
        val lignes = mutableListOf(t("reca.sync.ok", "pseudo" to c.optString("pseudo")))
        val gagne = jeu.xp - avant
        if (gagne > 0) {
            nouveau = true
            jeu.log(t("rec.sync.xp", "n" to gagne))
            lignes.add("   " + t("reca.sync.xp", "n" to gagne))
        }
        r.optJSONArray("badges")?.let { a ->
            for (i in 0 until a.length()) {
                val titre = a.getJSONObject(i).optString("titre")
                nouveau = true
                jeu.log(t("rec.badge.log", "titre" to titre))
                lignes.add(t("reca.badge.nouveau", "titre" to titre))
            }
        }
        return lignes.joinToString("\n")
    }

    fun abandonner() {
        enCours = false
    }

    /** Version d'un seul bloc, pour l'arrière-plan (Rappels) : à appeler hors de l'écran. */
    fun synchroniserBloquant(jeu: Jeu): String? {
        val p = preparer(jeu, forcer = false) ?: return null
        val (r, url) = envoyer(p)
        return appliquer(jeu, p, r, url)
    }

    fun enregistrer(jeu: Jeu, pseudo: String, cle: String, url: String) {
        val c = compte(jeu)
        c.put("cle", cle).put("pseudo", pseudo).put("serveur", url).put("dernier", 0)
        c.put("base", JSONObject().put("xp", 0).put("total", 0).put("colles", 0).put("stats", JSONObject()))
        jeu.log(t("rec.recense.log", "pseudo" to pseudo))
    }
}
