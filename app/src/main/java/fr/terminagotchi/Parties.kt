package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Les parties : plusieurs créatures rangées dans la maison, une seule « active » à la fois.
 *
 * Rangement (stockage privé de l'appli) :
 *   sauvegarde.json                    la partie ACTIVE (toujours au même endroit : widget, rappels,
 *                                      Doom et éditeur la lisent sans rien savoir des autres)
 *   parties/index.json                 {"active": "<id>", "ordre": ["<id>", …]}
 *   parties/partie_<id>.json           les parties rangées (même format que sauvegarde.json)
 *   parties/terrain_<id>/              le terrain de jeu rangé de chaque partie
 *
 * Choix du terrain : UN TERRAIN PAR PARTIE. Le terrain de la partie active est toujours
 * maison/terrain_terminagotchi (les leçons, le donjon, le CTF, le Doom et les repaires y vivent) ;
 * quand on change de partie, il est rangé dans parties/terrain_<id> et celui de l'autre partie
 * revient à sa place. Une nouvelle partie démarre donc sans terrain : la leçon « Construire mon nid »
 * se refait vraiment (rien n'est validé d'avance), et le sac du donjon reste à sa créature.
 *
 * Identifiant d'une partie : « 1 » pour la sauvegarde d'avant (c'est aussi la partie 1 du compte en
 * ligne, pour rester compatible), puis des identifiants au hasard (8 caractères hexadécimaux) :
 * deux appareils reliés au même compte ne mélangent jamais deux nouvelles parties.
 *
 * Rien n'est jamais effacé : une « nouvelle partie » range l'ancienne.
 */
object Parties {
    /** nombre maximum de parties sur l'appareil */
    const val MAX = 10
    /** ce qui suit le joueur d'une partie à l'autre : son compte (pas la progression de la partie) */
    private val IDENTITE = listOf("cle", "pseudo", "serveur", "parties_cache")

    class Resume(
        val id: String, val nom: String, val niveau: Int, val stade: Int, val forme: String?,
        val shiny: Boolean, val date: Long, val active: Boolean,
    ) {
        /** « Bébé », « Ado Hacker »… */
        val espece: String get() {
            val f = if (stade >= 2 && forme != null) " ${Regles.FORMES[forme] ?: ""}" else ""
            return (Regles.STADES[stade] + f).trim()
        }
        val icone: String get() = when (stade) { 0 -> "🥚"; 1 -> "🐣"; 2 -> "🐥"; else -> "🐲" }
    }

    private fun dossier(ctx: Context) = File(ctx.filesDir, "parties").apply { mkdirs() }
    private fun fIndex(ctx: Context) = File(dossier(ctx), "index.json")
    fun fichierActif(ctx: Context) = File(ctx.filesDir, "sauvegarde.json")
    private fun fichierRange(ctx: Context, id: String) = File(dossier(ctx), "partie_$id.json")
    private fun terrainActif(ctx: Context) = File(File(ctx.filesDir, "maison"), "terrain_terminagotchi")
    private fun terrainRange(ctx: Context, id: String) = File(dossier(ctx), "terrain_$id")

    private val verrou = Any()

    // ---------------------------------------------------------------- index
    private fun lireJson(f: File): JSONObject? = try {
        if (f.isFile) JSONObject(f.readText()) else null
    } catch (e: Exception) {
        null
    }

    private fun ecrire(f: File, o: JSONObject) {
        val tmp = File(f.parentFile, f.name + ".tmp")
        tmp.writeText(o.toString())
        if (!tmp.renameTo(f)) { f.writeText(o.toString()); tmp.delete() }
    }

    /** L'index, créé au premier passage : la sauvegarde d'avant devient la partie 1, active. */
    private fun index(ctx: Context): JSONObject {
        lireJson(fIndex(ctx))?.let { return it }
        val idx = JSONObject().put("active", "1").put("ordre", JSONArray())
        val s = lireJson(fichierActif(ctx))
        if (s != null && s.optString("nom").isNotEmpty()) {
            val id = s.optString("partie").ifEmpty { "1" }
            idx.put("active", id).put("ordre", JSONArray().put(id))
        }
        ecrire(fIndex(ctx), idx)
        return idx
    }

    private fun ordre(idx: JSONObject): MutableList<String> {
        val a = idx.optJSONArray("ordre") ?: JSONArray()
        return (0 until a.length()).map { a.getString(it) }.toMutableList()
    }

    /** Identifiant de la partie active. */
    fun active(ctx: Context): String = synchronized(verrou) { index(ctx).optString("active", "1") }

    /** Le fichier où une partie s'enregistre : sauvegarde.json si elle est active, sinon son rangement. */
    fun fichierDe(ctx: Context, id: String): File = synchronized(verrou) {
        if (index(ctx).optString("active", "1") == id) fichierActif(ctx) else fichierRange(ctx, id)
    }

    /** Y a-t-il au moins une créature (née) quelque part ? Sinon : premier lancement. */
    fun aucune(ctx: Context): Boolean = liste(ctx).none { it.nom.isNotEmpty() }

    // ---------------------------------------------------------------- liste
    private fun resume(o: JSONObject, id: String, active: Boolean, f: File): Resume {
        val xp = o.optInt("xp")
        val n = Regles.niveau(xp)
        val forme = if (o.has("forme") && !o.isNull("forme")) o.optString("forme") else null
        val date = o.optLong("maj").takeIf { it > 0 } ?: f.lastModified()
        return Resume(id, o.optString("nom"), n, Regles.stade(n), forme, o.optBoolean("shiny"), date, active)
    }

    /** Les parties de l'appareil, dans l'ordre de création (la partie active est marquée). */
    fun liste(ctx: Context): List<Resume> = synchronized(verrou) {
        val idx = index(ctx)
        val act = idx.optString("active", "1")
        val ids = ordre(idx)
        if (act !in ids) ids.add(act)
        ids.mapNotNull { id ->
            val f = if (id == act) fichierActif(ctx) else fichierRange(ctx, id)
            val o = lireJson(f) ?: return@mapNotNull null
            resume(o, id, id == act, f)
        }
    }

    fun pleine(ctx: Context) = liste(ctx).size >= MAX

    // ---------------------------------------------------------------- changer de partie
    private fun deplacer(de: File, vers: File): Boolean {
        if (!de.exists()) return true
        if (vers.exists()) return false          // jamais écraser : on laisse tout en place
        vers.parentFile?.mkdirs()
        return de.renameTo(vers)
    }

    /** Le compte du joueur (clé, pseudo…) passe dans la partie qui devient active. */
    private fun porterCompte(depuis: JSONObject?, vers: JSONObject) {
        val extra = vers.optJSONObject("extra") ?: JSONObject().also { vers.put("extra", it) }
        val c = extra.optJSONObject("compte") ?: JSONObject().also { extra.put("compte", it) }
        val source = depuis?.optJSONObject("extra")?.optJSONObject("compte") ?: JSONObject()
        val pseudo = source.optString("pseudo")
        val baseDe = baseDe(c)
        for (k in IDENTITE) if (source.has(k)) c.put(k, source.get(k)) else if (k != "serveur") c.remove(k)
        if (pseudo.isNotEmpty() && pseudo != baseDe) {
            // jamais synchronisée avec CE compte : tout ce qu'elle a gagné sera envoyé à sa première synchro
            c.remove("base")
            c.put("dernier", 0)
            c.put("base_de", pseudo)
        }
    }

    /** Le compte avec lequel la partie a été synchronisée la dernière fois (son « base » compte pour lui). */
    fun baseDe(c: JSONObject): String = c.optString("base_de").ifEmpty { if (c.has("base")) c.optString("pseudo") else "" }

    /**
     * Range la partie active (sauvegarde + terrain) et met `id` à sa place.
     * `nouvelle` : l'état de départ de la partie si elle n'existe pas encore (nouvelle partie, partie du compte).
     * Renvoie false si rien n'a bougé.
     */
    private fun basculer(ctx: Context, id: String, nouvelle: JSONObject?): Boolean = synchronized(verrou) {
        val idx = index(ctx)
        val act = idx.optString("active", "1")
        if (act == id) return false
        val ids = ordre(idx)
        val courant = lireJson(fichierActif(ctx))
        val arrivee = if (nouvelle != null) nouvelle else lireJson(fichierRange(ctx, id)) ?: return false
        // 1. ranger la partie active (sa sauvegarde, puis son terrain)
        if (courant != null && courant.optString("nom").isNotEmpty()) {
            if (fichierRange(ctx, act).exists()) return false
            courant.put("partie", act)
            ecrire(fichierRange(ctx, act), courant)
            if (act !in ids) ids.add(act)
            if (!deplacer(terrainActif(ctx), terrainRange(ctx, act))) {
                android.util.Log.w("TG", "terrain de la partie $act laissé en place")
            }
        } else {
            ids.remove(act)                      // un œuf qui n'avait pas encore de nom : rien à ranger
        }
        // 2. installer l'autre (sauvegarde puis terrain)
        arrivee.put("partie", id)
        porterCompte(courant, arrivee)
        ecrire(fichierActif(ctx), arrivee)
        if (nouvelle == null) fichierRange(ctx, id).delete()
        if (!terrainActif(ctx).exists()) deplacer(terrainRange(ctx, id), terrainActif(ctx))
        if (id !in ids) ids.add(id)
        idx.put("active", id).put("ordre", JSONArray(ids))
        ecrire(fIndex(ctx), idx)
        true
    }

    /** Charge une partie rangée sur l'appareil. */
    fun charger(ctx: Context, id: String): Boolean = basculer(ctx, id, null)

    private fun nouvelId(ctx: Context): String {
        val pris = liste(ctx).map { it.id }.toSet()
        while (true) {
            val id = (1..8).map { "0123456789abcdef".random() }.joinToString("")
            if (id !in pris && !fichierRange(ctx, id).exists() && !terrainRange(ctx, id).exists()) return id
        }
    }

    /** Une nouvelle partie : l'ancienne est rangée, un œuf tout neuf attend son nom. Renvoie son id (null si plein). */
    fun nouvelle(ctx: Context): String? {
        if (pleine(ctx)) return null
        val id = nouvelId(ctx)
        val o = JSONObject().put("nom", "").put("partie", id).put("maj", System.currentTimeMillis())
        return if (basculer(ctx, id, o)) id else null
    }

    /** Une partie du compte en ligne, pas encore sur cet appareil : elle arrive vide, la synchro la remplit. */
    fun depuisCompte(ctx: Context, id: String, nom: String): Boolean {
        if (pleine(ctx) || liste(ctx).any { it.id == id }) return false
        val o = JSONObject().put("nom", nom.ifEmpty { "?" }).put("partie", id).put("maj", System.currentTimeMillis())
        return basculer(ctx, id, o)
    }

    /** Se déconnecter : le compte est retiré de TOUTES les parties de l'appareil (l'adresse du site reste). */
    fun oublierCompte(ctx: Context) = synchronized(verrou) {
        val idx = index(ctx)
        val act = idx.optString("active", "1")
        for (id in ordre(idx) + act) {
            val f = if (id == act) fichierActif(ctx) else fichierRange(ctx, id)
            val o = lireJson(f) ?: continue
            val c = o.optJSONObject("extra")?.optJSONObject("compte") ?: continue
            baseDe(c).takeIf { it.isNotEmpty() }?.let { c.put("base_de", it) }
            for (k in IDENTITE) if (k != "serveur") c.remove(k)
            ecrire(f, o)
        }
    }
}
